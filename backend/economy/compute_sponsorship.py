"""Externally funded reserve for owner-sponsored compute settlement.

This store is deliberately separate from :mod:`economy.ledger`: CU and other
simulation values never enter this reserve.  Every ingress is a receipted,
integer, double-entry transaction from the external-receipts contra account.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict


class SettlementError(RuntimeError):
    """Base class for reserve settlement failures."""


class SettlementIdempotencyConflict(SettlementError):
    """An operation id was reused for a different funding intent."""


class SettlementInsufficientFunds(SettlementError):
    """A reserve account cannot cover a requested settlement."""


class SettlementTransitionError(SettlementError):
    """A settlement operation attempted an invalid state transition."""


_CU_SOURCE = re.compile(r"(?:^|[^a-z0-9])cu(?:$|[^a-z0-9])")
_EVIDENCE_HASH = re.compile(r"^sha256:[0-9a-f]{64}$")
_SUPPORTED_EVIDENCE_REQUIREMENTS = frozenset({
    "verified_causal_evidence",
    "commissioned_action",
    "independent_verifier",
})
_ALLOCATION_TRANSITIONS = {
    "hold": {"proposed": "funding_held"},
    "approve": {"funding_held": "owner_approved"},
    "cancel": {
        "proposed": "cancelled",
        "funding_held": "cancelled",
        "owner_approved": "cancelled",
    },
    "expire": {"owner_approved": "expired"},
    "provider_submit": {"owner_approved": "provider_pending", "provider_pending": "provider_pending"},
    "provider_confirm": {"provider_pending": "provider_confirmed"},
    "reconcile_start": {"provider_confirmed": "reconciling"},
    "reconcile_complete": {"reconciling": "reconciled"},
    "reconcile_exception": {"reconciling": "reconciliation_exception"},
}


class ComputeSponsorshipStore:
    """Transactional store for receipted external funding.

    Account ids are qualified with their currency (for example,
    ``reserve:available:usd``), which prevents balances in different
    currencies from being mixed accidentally.
    """

    def __init__(self, database_path: Path | str):
        self.database_path = str(database_path)
        self._memory_connection: sqlite3.Connection | None = None
        self._closed = False
        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        connection = self._connect()
        try:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS settlement_operations (
                    operation_id TEXT PRIMARY KEY,
                    request_hash TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS settlement_accounts (
                    account_id TEXT PRIMARY KEY,
                    currency TEXT NOT NULL,
                    balance_minor INTEGER NOT NULL DEFAULT 0,
                    CHECK(typeof(balance_minor) = 'integer')
                );
                CREATE TABLE IF NOT EXISTS settlement_postings (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_id TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    delta_minor INTEGER NOT NULL,
                    evidence_hash TEXT NOT NULL,
                    occurred_at_ms INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY(operation_id) REFERENCES settlement_operations(operation_id),
                    FOREIGN KEY(account_id) REFERENCES settlement_accounts(account_id),
                    CHECK(typeof(delta_minor) = 'integer'),
                    CHECK(typeof(occurred_at_ms) = 'integer' AND occurred_at_ms >= 0)
                );
                CREATE TABLE IF NOT EXISTS funding_receipts (
                    operation_id TEXT PRIMARY KEY,
                    owner_subject TEXT NOT NULL,
                    amount_minor INTEGER NOT NULL,
                    currency TEXT NOT NULL,
                    source_class TEXT NOT NULL,
                    evidence_hash TEXT NOT NULL,
                    received_at_ms INTEGER NOT NULL,
                    FOREIGN KEY(operation_id) REFERENCES settlement_operations(operation_id),
                    CHECK(typeof(amount_minor) = 'integer' AND amount_minor > 0),
                    CHECK(typeof(received_at_ms) = 'integer')
                );
                CREATE TABLE IF NOT EXISTS settlement_policies (
                    policy_id TEXT PRIMARY KEY,
                    version INTEGER NOT NULL UNIQUE,
                    owner_subject TEXT NOT NULL,
                    policy_json TEXT NOT NULL,
                    policy_hash TEXT NOT NULL,
                    state TEXT NOT NULL,
                    approved_at_ms INTEGER NOT NULL,
                    activation_evidence_json TEXT,
                    activated_at_ms INTEGER,
                    FOREIGN KEY(policy_id) REFERENCES settlement_policies(policy_id),
                    CHECK(state IN ('draft', 'allocation_active', 'settlement_active')),
                    CHECK(typeof(version) = 'integer' AND version > 0),
                    CHECK(typeof(approved_at_ms) = 'integer' AND approved_at_ms >= 0),
                    CHECK(activated_at_ms IS NULL OR (typeof(activated_at_ms) = 'integer' AND activated_at_ms >= 0))
                );
                CREATE TABLE IF NOT EXISTS settlement_allocations (
                    allocation_id TEXT PRIMARY KEY,
                    operation_id TEXT NOT NULL UNIQUE,
                    owner_subject TEXT NOT NULL,
                    beneficiary_class TEXT NOT NULL,
                    policy_id TEXT NOT NULL,
                    policy_version INTEGER NOT NULL,
                    policy_snapshot_json TEXT NOT NULL,
                    world_id TEXT NOT NULL,
                    public_claim_ids_json TEXT NOT NULL,
                    eligible_cu_milli INTEGER NOT NULL,
                    quoted_funding_minor INTEGER NOT NULL,
                    period_start_ms INTEGER NOT NULL DEFAULT 0,
                    state TEXT NOT NULL,
                    created_at_ms INTEGER NOT NULL,
                    held_at_ms INTEGER,
                    approval_hash TEXT,
                    approved_at_ms INTEGER,
                    expires_at_ms INTEGER,
                    cancelled_at_ms INTEGER,
                    expired_at_ms INTEGER,
                    provider TEXT,
                    provider_operation_id TEXT,
                    provider_pending_at_ms INTEGER,
                    provider_confirmed_at_ms INTEGER,
                    reconciled_at_ms INTEGER,
                    actual_cost_minor INTEGER,
                    actual_cost_effective_at_ms INTEGER,
                    FOREIGN KEY(operation_id) REFERENCES settlement_operations(operation_id),
                    FOREIGN KEY(policy_id) REFERENCES settlement_policies(policy_id),
                    CHECK(beneficiary_class = 'eov_owner_development'),
                    CHECK(state IN ('proposed', 'funding_held', 'owner_approved', 'provider_pending', 'provider_confirmed', 'reconciling', 'reconciled', 'reconciliation_exception', 'cancelled', 'expired')),
                    CHECK(typeof(policy_version) = 'integer' AND policy_version > 0),
                    CHECK(typeof(eligible_cu_milli) = 'integer' AND eligible_cu_milli > 0),
                    CHECK(typeof(quoted_funding_minor) = 'integer' AND quoted_funding_minor > 0),
                    CHECK(typeof(period_start_ms) = 'integer' AND period_start_ms >= 0),
                    CHECK(typeof(created_at_ms) = 'integer' AND created_at_ms >= 0)
                );
                CREATE TABLE IF NOT EXISTS settlement_claim_commitments (
                    claim_id TEXT PRIMARY KEY,
                    allocation_id TEXT NOT NULL,
                    policy_id TEXT NOT NULL,
                    committed_at_ms INTEGER NOT NULL,
                    FOREIGN KEY(allocation_id) REFERENCES settlement_allocations(allocation_id),
                    FOREIGN KEY(policy_id) REFERENCES settlement_policies(policy_id),
                    CHECK(typeof(committed_at_ms) = 'integer' AND committed_at_ms >= 0)
                );
                CREATE TABLE IF NOT EXISTS settlement_policy_activation_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_id TEXT NOT NULL UNIQUE,
                    policy_id TEXT NOT NULL,
                    from_state TEXT NOT NULL,
                    target_state TEXT NOT NULL,
                    evidence_json TEXT NOT NULL,
                    reserve_snapshot_json TEXT,
                    activated_at_ms INTEGER NOT NULL,
                    FOREIGN KEY(operation_id) REFERENCES settlement_operations(operation_id),
                    FOREIGN KEY(policy_id) REFERENCES settlement_policies(policy_id),
                    CHECK(from_state IN ('draft', 'allocation_active')),
                    CHECK(target_state IN ('allocation_active', 'settlement_active')),
                    CHECK(typeof(activated_at_ms) = 'integer' AND activated_at_ms >= 0)
                );
                CREATE TABLE IF NOT EXISTS settlement_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_id TEXT NOT NULL,
                    allocation_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    from_state TEXT NOT NULL,
                    target_state TEXT NOT NULL,
                    evidence_json TEXT NOT NULL,
                    occurred_at_ms INTEGER NOT NULL,
                    FOREIGN KEY(operation_id) REFERENCES settlement_operations(operation_id),
                    FOREIGN KEY(allocation_id) REFERENCES settlement_allocations(allocation_id),
                    CHECK(event_type IN ('allocation_held', 'owner_approved', 'provider_submitted', 'provider_confirmed', 'reconciliation_started', 'allocation_reconciled', 'reconciliation_exception', 'allocation_cancelled', 'allocation_expired')),
                    CHECK(typeof(occurred_at_ms) = 'integer' AND occurred_at_ms >= 0)
                );
                CREATE INDEX IF NOT EXISTS idx_settlement_postings_operation
                    ON settlement_postings(operation_id);
                CREATE INDEX IF NOT EXISTS idx_settlement_postings_account
                    ON settlement_postings(account_id);
                CREATE INDEX IF NOT EXISTS idx_settlement_postings_as_of
                    ON settlement_postings(account_id, occurred_at_ms);
                CREATE INDEX IF NOT EXISTS idx_settlement_allocations_policy
                    ON settlement_allocations(policy_id);
                CREATE INDEX IF NOT EXISTS idx_settlement_claim_commitments_allocation
                    ON settlement_claim_commitments(allocation_id);
                CREATE INDEX IF NOT EXISTS idx_settlement_policy_activation_events_policy
                    ON settlement_policy_activation_events(policy_id, sequence);
                CREATE INDEX IF NOT EXISTS idx_settlement_events_allocation
                    ON settlement_events(allocation_id, sequence);
                CREATE TABLE IF NOT EXISTS settlement_provider_receipts (
                    provider TEXT NOT NULL,
                    receipt_id_commitment TEXT NOT NULL,
                    provider_transaction_id_commitment TEXT NOT NULL,
                    provider_operation_id_commitment TEXT NOT NULL,
                    allocation_id TEXT NOT NULL,
                    receipt_json TEXT NOT NULL,
                    receipt_hash TEXT NOT NULL,
                    recorded_at_ms INTEGER NOT NULL,
                    PRIMARY KEY(provider, receipt_id_commitment),
                    UNIQUE(provider, provider_transaction_id_commitment),
                    FOREIGN KEY(allocation_id) REFERENCES settlement_allocations(allocation_id),
                    CHECK(typeof(recorded_at_ms) = 'integer' AND recorded_at_ms >= 0)
                );
                CREATE TABLE IF NOT EXISTS settlement_provider_costs (
                    allocation_id TEXT NOT NULL,
                    cost_hash TEXT NOT NULL,
                    cost_json TEXT NOT NULL,
                    recorded_at_ms INTEGER NOT NULL,
                    PRIMARY KEY(allocation_id, cost_hash),
                    FOREIGN KEY(allocation_id) REFERENCES settlement_allocations(allocation_id),
                    CHECK(typeof(recorded_at_ms) = 'integer' AND recorded_at_ms >= 0)
                );
                CREATE TABLE IF NOT EXISTS settlement_provider_cost_records (
                    provider TEXT NOT NULL,
                    record_commitment TEXT NOT NULL,
                    allocation_id TEXT NOT NULL,
                    cost_hash TEXT NOT NULL,
                    effective_at_ms INTEGER NOT NULL,
                    recorded_at_ms INTEGER NOT NULL,
                    PRIMARY KEY(provider, record_commitment),
                    FOREIGN KEY(allocation_id) REFERENCES settlement_allocations(allocation_id),
                    CHECK(typeof(effective_at_ms) = 'integer' AND effective_at_ms >= 0),
                    CHECK(typeof(recorded_at_ms) = 'integer' AND recorded_at_ms >= 0)
                );
                """
            )
            posting_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(settlement_postings)")
            }
            if "occurred_at_ms" not in posting_columns:
                connection.execute(
                    "ALTER TABLE settlement_postings ADD COLUMN occurred_at_ms INTEGER NOT NULL DEFAULT 0"
                )
            connection.execute(
                """UPDATE settlement_postings
                SET occurred_at_ms = (
                    SELECT received_at_ms FROM funding_receipts
                    WHERE funding_receipts.operation_id = settlement_postings.operation_id
                )
                WHERE occurred_at_ms = 0
                  AND operation_id IN (SELECT operation_id FROM funding_receipts)"""
            )
            allocation_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(settlement_allocations)")
            }
            if "period_start_ms" not in allocation_columns:
                connection.execute(
                    "ALTER TABLE settlement_allocations ADD COLUMN period_start_ms INTEGER NOT NULL DEFAULT 0"
                )
            for column in (
                "held_at_ms", "approval_hash", "approved_at_ms", "expires_at_ms",
                "cancelled_at_ms", "expired_at_ms", "provider", "provider_operation_id",
                "provider_pending_at_ms", "provider_confirmed_at_ms", "reconciled_at_ms", "actual_cost_minor",
                "actual_cost_effective_at_ms",
            ):
                if column not in allocation_columns:
                    connection.execute(f"ALTER TABLE settlement_allocations ADD COLUMN {column}")
            allocation_sql = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'settlement_allocations'"
            ).fetchone()["sql"]
            if "provider_pending" not in allocation_sql:
                connection.execute("PRAGMA foreign_keys=OFF")
                connection.execute(
                    """CREATE TABLE settlement_allocations_v4 AS
                    SELECT * FROM settlement_allocations"""
                )
                connection.execute("DROP TABLE settlement_allocations")
                connection.execute(
                    """CREATE TABLE settlement_allocations (
                        allocation_id TEXT PRIMARY KEY, operation_id TEXT NOT NULL UNIQUE,
                        owner_subject TEXT NOT NULL, beneficiary_class TEXT NOT NULL, policy_id TEXT NOT NULL,
                        policy_version INTEGER NOT NULL, policy_snapshot_json TEXT NOT NULL, world_id TEXT NOT NULL,
                        public_claim_ids_json TEXT NOT NULL, eligible_cu_milli INTEGER NOT NULL,
                        quoted_funding_minor INTEGER NOT NULL, period_start_ms INTEGER NOT NULL DEFAULT 0,
                        state TEXT NOT NULL, created_at_ms INTEGER NOT NULL, held_at_ms INTEGER,
                        approval_hash TEXT, approved_at_ms INTEGER, expires_at_ms INTEGER,
                        cancelled_at_ms INTEGER, expired_at_ms INTEGER,
                        provider TEXT, provider_operation_id TEXT, provider_pending_at_ms INTEGER,
                        provider_confirmed_at_ms INTEGER, reconciled_at_ms INTEGER, actual_cost_minor INTEGER,
                        FOREIGN KEY(operation_id) REFERENCES settlement_operations(operation_id),
                        FOREIGN KEY(policy_id) REFERENCES settlement_policies(policy_id),
                        CHECK(beneficiary_class = 'eov_owner_development'),
                        CHECK(state IN ('proposed', 'funding_held', 'owner_approved', 'provider_pending', 'provider_confirmed', 'reconciling', 'reconciled', 'reconciliation_exception', 'cancelled', 'expired')),
                        CHECK(typeof(policy_version) = 'integer' AND policy_version > 0),
                        CHECK(typeof(eligible_cu_milli) = 'integer' AND eligible_cu_milli > 0),
                        CHECK(typeof(quoted_funding_minor) = 'integer' AND quoted_funding_minor > 0),
                        CHECK(typeof(period_start_ms) = 'integer' AND period_start_ms >= 0),
                        CHECK(typeof(created_at_ms) = 'integer' AND created_at_ms >= 0)
                    )"""
                )
                connection.execute("INSERT INTO settlement_allocations SELECT * FROM settlement_allocations_v4")
                connection.execute("DROP TABLE settlement_allocations_v4")
                connection.execute("PRAGMA foreign_keys=ON")
            connection.execute(
                """CREATE UNIQUE INDEX IF NOT EXISTS idx_allocation_provider_operation
                ON settlement_allocations(provider, provider_operation_id)
                WHERE provider_operation_id IS NOT NULL"""
            )
            events_sql = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'settlement_events'"
            ).fetchone()["sql"]
            if "provider_submitted" not in events_sql:
                connection.execute("PRAGMA foreign_keys=OFF")
                connection.execute("CREATE TABLE settlement_events_v4 AS SELECT * FROM settlement_events")
                connection.execute("DROP TABLE settlement_events")
                connection.execute(
                    """CREATE TABLE settlement_events (
                        sequence INTEGER PRIMARY KEY AUTOINCREMENT, operation_id TEXT NOT NULL,
                        allocation_id TEXT NOT NULL, event_type TEXT NOT NULL, from_state TEXT NOT NULL,
                        target_state TEXT NOT NULL, evidence_json TEXT NOT NULL, occurred_at_ms INTEGER NOT NULL,
                        FOREIGN KEY(operation_id) REFERENCES settlement_operations(operation_id),
                        FOREIGN KEY(allocation_id) REFERENCES settlement_allocations(allocation_id),
                        CHECK(event_type IN ('allocation_held', 'owner_approved', 'provider_submitted', 'provider_confirmed', 'reconciliation_started', 'allocation_reconciled', 'reconciliation_exception', 'allocation_cancelled', 'allocation_expired')),
                        CHECK(typeof(occurred_at_ms) = 'integer' AND occurred_at_ms >= 0)
                    )"""
                )
                connection.execute("INSERT INTO settlement_events SELECT * FROM settlement_events_v4")
                connection.execute("DROP TABLE settlement_events_v4")
                connection.execute("CREATE INDEX IF NOT EXISTS idx_settlement_events_allocation ON settlement_events(allocation_id, sequence)")
                connection.execute("PRAGMA foreign_keys=ON")
            receipt_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(settlement_provider_receipts)")
            }
            if "receipt_id_commitment" not in receipt_columns:
                legacy_receipts = connection.execute("SELECT * FROM settlement_provider_receipts").fetchall()
                connection.execute("PRAGMA foreign_keys=OFF")
                connection.execute("DROP TABLE settlement_provider_receipts")
                connection.execute(
                    """CREATE TABLE settlement_provider_receipts (
                        provider TEXT NOT NULL, receipt_id_commitment TEXT NOT NULL,
                        provider_transaction_id_commitment TEXT NOT NULL,
                        provider_operation_id_commitment TEXT NOT NULL, allocation_id TEXT NOT NULL,
                        receipt_json TEXT NOT NULL, receipt_hash TEXT NOT NULL, recorded_at_ms INTEGER NOT NULL,
                        PRIMARY KEY(provider, receipt_id_commitment),
                        UNIQUE(provider, provider_transaction_id_commitment),
                        FOREIGN KEY(allocation_id) REFERENCES settlement_allocations(allocation_id),
                        CHECK(typeof(recorded_at_ms) = 'integer' AND recorded_at_ms >= 0)
                    )"""
                )
                for legacy in legacy_receipts:
                    legacy_payload = json.loads(legacy["receipt_json"])
                    operation = connection.execute(
                        "SELECT provider_operation_id FROM settlement_allocations WHERE allocation_id = ?",
                        (legacy["allocation_id"],),
                    ).fetchone()
                    if not operation or not operation["provider_operation_id"]:
                        raise SettlementTransitionError("legacy provider receipt lacks an allocation operation binding")
                    receipt_id_commitment = "sha256:" + hashlib.sha256(
                        f"receipt:{legacy['receipt_id']}".encode("utf-8")
                    ).hexdigest()
                    transaction_commitment = "sha256:" + hashlib.sha256(
                        f"transaction:{legacy_payload.get('provider_transaction_id', legacy['receipt_id'])}".encode("utf-8")
                    ).hexdigest()
                    operation_commitment = "sha256:" + hashlib.sha256(
                        f"operation:{operation['provider_operation_id']}".encode("utf-8")
                    ).hexdigest()
                    receipt_json = self._canonical_json({
                        "provider": legacy["provider"], "receipt_id_commitment": receipt_id_commitment,
                        "provider_transaction_id_commitment": transaction_commitment,
                        "provider_operation_id_commitment": operation_commitment,
                        "legacy_receipt_hash": legacy["receipt_hash"],
                    })
                    receipt_hash = "sha256:" + hashlib.sha256(receipt_json.encode("utf-8")).hexdigest()
                    connection.execute(
                        """INSERT INTO settlement_provider_receipts(
                            provider, receipt_id_commitment, provider_transaction_id_commitment,
                            provider_operation_id_commitment, allocation_id, receipt_json, receipt_hash, recorded_at_ms
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (legacy["provider"], receipt_id_commitment, transaction_commitment,
                         operation_commitment, legacy["allocation_id"], receipt_json, receipt_hash,
                         legacy["recorded_at_ms"]),
                    )
                connection.execute("PRAGMA foreign_keys=ON")
        finally:
            self._release(connection)

    def _connect(self) -> sqlite3.Connection:
        if self._closed:
            raise SettlementTransitionError("settlement store is closed")
        if self.database_path == ":memory:" and self._memory_connection is not None:
            return self._memory_connection
        connection = sqlite3.connect(self.database_path, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA foreign_keys=ON")
        if self.database_path == ":memory:":
            self._memory_connection = connection
        return connection

    def _release(self, connection: sqlite3.Connection) -> None:
        if connection is not self._memory_connection:
            connection.close()

    def close(self) -> None:
        """Close the store and its lifetime-scoped in-memory connection."""
        if self._memory_connection is not None:
            self._memory_connection.close()
            self._memory_connection = None
        self._closed = True

    @staticmethod
    def _account_id(account: str, currency: str) -> str:
        return f"{account}:{currency}"

    @staticmethod
    def _require_text(value: str, field: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} is required")
        return value.strip()

    @classmethod
    def _normalize_inputs(
        cls,
        operation_id: str,
        owner_subject: str,
        amount_minor: int,
        currency: str,
        source_class: str,
        evidence_hash: str,
        received_at_ms: int,
    ) -> Dict[str, Any]:
        operation_id = cls._require_text(operation_id, "operation_id")
        owner_subject = cls._require_text(owner_subject, "owner_subject")
        currency = cls._require_text(currency, "currency").lower()
        source_class = cls._require_text(source_class, "source_class")
        evidence_hash = cls._require_text(evidence_hash, "evidence_hash")
        if not _EVIDENCE_HASH.fullmatch(evidence_hash):
            raise ValueError("evidence_hash must be sha256 followed by 64 lowercase hexadecimal characters")
        if isinstance(amount_minor, bool) or not isinstance(amount_minor, int) or amount_minor <= 0:
            raise ValueError("amount_minor must be a positive integer")
        if isinstance(received_at_ms, bool) or not isinstance(received_at_ms, int) or received_at_ms < 0:
            raise ValueError("received_at_ms must be a non-negative integer")
        if _CU_SOURCE.search(source_class.lower()) or "compute unit" in source_class.lower() or "compute_unit" in source_class.lower() or "compute-unit" in source_class.lower():
            raise ValueError("CU cannot fund the external settlement reserve")
        return {
            "operation_id": operation_id,
            "owner_subject": owner_subject,
            "amount_minor": amount_minor,
            "currency": currency,
            "source_class": source_class,
            "evidence_hash": evidence_hash,
            "received_at_ms": received_at_ms,
        }

    @staticmethod
    def _hash_request(values: Dict[str, Any]) -> str:
        canonical = json.dumps(values, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _canonical_json(value: Any) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    @classmethod
    def _require_non_negative_integer(cls, value: int, field: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{field} must be a non-negative integer")
        return value

    @classmethod
    def _require_positive_integer(cls, value: int, field: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{field} must be a positive integer")
        return value

    @classmethod
    def _require_evidence_hash(cls, value: str, field: str) -> str:
        value = cls._require_text(value, field)
        if not _EVIDENCE_HASH.fullmatch(value):
            raise ValueError(f"{field} must be sha256 followed by 64 lowercase hexadecimal characters")
        return value

    @classmethod
    def _normalize_policy(cls, policy: dict) -> Dict[str, Any]:
        if not isinstance(policy, dict):
            raise ValueError("policy must be an object")
        normalized = {
            "policy_id": cls._require_text(policy.get("policy_id"), "policy_id"),
            "version": cls._require_positive_integer(policy.get("version"), "version"),
            "effective_from_ms": cls._require_non_negative_integer(policy.get("effective_from_ms"), "effective_from_ms"),
            "effective_to_ms": policy.get("effective_to_ms"),
            "eligible_action_types": policy.get("eligible_action_types"),
            "evidence_requirements": policy.get("evidence_requirements"),
            "cu_milli_per_funding_minor": cls._require_positive_integer(
                policy.get("cu_milli_per_funding_minor"), "cu_milli_per_funding_minor"
            ),
            "min_claim_cu_milli": cls._require_positive_integer(policy.get("min_claim_cu_milli"), "min_claim_cu_milli"),
            "max_claim_cu_milli": cls._require_positive_integer(policy.get("max_claim_cu_milli"), "max_claim_cu_milli"),
            "program_cap_minor": cls._require_positive_integer(policy.get("program_cap_minor"), "program_cap_minor"),
            "period_cap_minor": cls._require_positive_integer(policy.get("period_cap_minor"), "period_cap_minor"),
            "period_ms": cls._require_positive_integer(policy.get("period_ms"), "period_ms"),
            "beneficiary_class": cls._require_text(policy.get("beneficiary_class"), "beneficiary_class"),
            "funding_source_class": cls._require_text(policy.get("funding_source_class"), "funding_source_class"),
            "funding_currency": cls._require_text(policy.get("funding_currency"), "funding_currency").lower(),
            "compliance_manifest_hash": cls._require_evidence_hash(
                policy.get("compliance_manifest_hash"), "compliance_manifest_hash"
            ),
        }
        if normalized["effective_to_ms"] is not None:
            normalized["effective_to_ms"] = cls._require_non_negative_integer(
                normalized["effective_to_ms"], "effective_to_ms"
            )
            if normalized["effective_to_ms"] < normalized["effective_from_ms"]:
                raise ValueError("effective_to_ms must not precede effective_from_ms")
        for field in ("eligible_action_types", "evidence_requirements"):
            values = normalized[field]
            if not isinstance(values, list) or not values:
                raise ValueError(f"{field} must be a non-empty list")
            normalized[field] = [cls._require_text(value, field) for value in values]
            if len(set(normalized[field])) != len(normalized[field]):
                raise ValueError(f"{field} must not contain duplicates")
        unknown_requirements = set(normalized["evidence_requirements"]) - _SUPPORTED_EVIDENCE_REQUIREMENTS
        if unknown_requirements:
            raise ValueError("unsupported evidence requirement")
        if normalized["min_claim_cu_milli"] > normalized["max_claim_cu_milli"]:
            raise ValueError("min_claim_cu_milli must not exceed max_claim_cu_milli")
        if normalized["period_cap_minor"] > normalized["program_cap_minor"]:
            raise ValueError("period_cap_minor must not exceed program_cap_minor")
        if normalized["beneficiary_class"] != "eov_owner_development":
            raise ValueError("beneficiary_class must be eov_owner_development")
        source_class = normalized["funding_source_class"].lower()
        if _CU_SOURCE.search(source_class) or "compute unit" in source_class or "compute_unit" in source_class or "compute-unit" in source_class:
            raise ValueError("CU cannot fund the external settlement reserve")
        return normalized

    @staticmethod
    def _claim_meets_evidence_requirements(claim: Dict[str, Any], requirements: list[str]) -> bool:
        for requirement in requirements:
            if requirement == "verified_causal_evidence":
                if claim.get("status") != "verified_provisional" or not claim.get("evidence_hash"):
                    return False
            elif requirement == "commissioned_action":
                if not claim.get("commission_hash"):
                    return False
            elif requirement == "independent_verifier":
                contributor = claim.get("contributor_ref")
                verifier = claim.get("verifier_ref")
                if not contributor or not verifier or contributor == verifier:
                    return False
            else:
                return False
        return True

    def _reserve_snapshot(
        self,
        connection: sqlite3.Connection,
        owner_subject: str,
        policy: Dict[str, Any],
        as_of_ms: int,
    ) -> Dict[str, Any]:
        currency = policy["funding_currency"]
        available = connection.execute(
            """SELECT COALESCE(SUM(delta_minor), 0) AS balance_minor
            FROM settlement_postings WHERE account_id = ? AND occurred_at_ms <= ?""",
            (self._account_id("reserve:available", currency), as_of_ms),
        ).fetchone()
        available_balance = int(available["balance_minor"])
        receipts = connection.execute(
            """SELECT operation_id, amount_minor, evidence_hash, received_at_ms
            FROM funding_receipts
            WHERE owner_subject = ? AND currency = ? AND source_class = ? AND received_at_ms <= ?
            ORDER BY received_at_ms, operation_id""",
            (owner_subject, currency, policy["funding_source_class"], as_of_ms),
        ).fetchall()
        receipt_rows = [
            {
                "operation_id": row["operation_id"],
                "amount_minor": int(row["amount_minor"]),
                "evidence_hash": row["evidence_hash"],
                "received_at_ms": int(row["received_at_ms"]),
            }
            for row in receipts
        ]
        return {
            "currency": currency,
            "as_of_ms": as_of_ms,
            "available_balance_minor": available_balance,
            "receipted_minor": sum(item["amount_minor"] for item in receipt_rows),
            "required_program_cap_minor": policy["program_cap_minor"],
            "receipts": receipt_rows,
        }

    @classmethod
    def _require_current_policy_runtime_fields(cls, policy: Dict[str, Any]) -> None:
        period_ms = policy.get("period_ms")
        if (
            not isinstance(policy.get("funding_currency"), str)
            or not policy["funding_currency"].strip()
            or isinstance(period_ms, bool)
            or not isinstance(period_ms, int)
            or period_ms <= 0
        ):
            raise SettlementTransitionError(
                "legacy policy lacks required authorization facts; create a new policy version"
            )

    @classmethod
    def _policy_from_row(cls, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "policy_id": row["policy_id"],
            "version": int(row["version"]),
            "owner_subject": row["owner_subject"],
            "policy": json.loads(row["policy_json"]),
            "policy_hash": row["policy_hash"],
            "state": row["state"],
            "approved_at_ms": int(row["approved_at_ms"]),
            "activation_evidence": json.loads(row["activation_evidence_json"])
            if row["activation_evidence_json"] else None,
            "activated_at_ms": int(row["activated_at_ms"])
            if row["activated_at_ms"] is not None else None,
        }

    def create_policy(
        self,
        operation_id: str,
        owner_subject: str,
        policy: dict,
        approved_at_ms: int,
    ) -> Dict[str, Any]:
        """Persist one immutable, owner-authorized conversion-policy version."""
        values = {
            "operation_id": self._require_text(operation_id, "operation_id"),
            "owner_subject": self._require_text(owner_subject, "owner_subject"),
            "policy": self._normalize_policy(policy),
            "approved_at_ms": self._require_non_negative_integer(approved_at_ms, "approved_at_ms"),
        }
        request_hash = self._hash_request(values)
        policy_json = self._canonical_json(values["policy"])
        policy_hash = hashlib.sha256(policy_json.encode("utf-8")).hexdigest()
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            prior = connection.execute(
                "SELECT request_hash, result_json FROM settlement_operations WHERE operation_id = ?",
                (values["operation_id"],),
            ).fetchone()
            if prior:
                if prior["request_hash"] != request_hash:
                    raise SettlementIdempotencyConflict("operation_id was already used for different settlement intent")
                connection.execute("COMMIT")
                return json.loads(prior["result_json"])
            existing = connection.execute(
                "SELECT policy_id FROM settlement_policies WHERE policy_id = ? OR version = ?",
                (values["policy"]["policy_id"], values["policy"]["version"]),
            ).fetchone()
            if existing:
                raise SettlementTransitionError("policy id and version are immutable")
            result = {
                "operation_id": values["operation_id"],
                "policy_id": values["policy"]["policy_id"],
                "version": values["policy"]["version"],
                "owner_subject": values["owner_subject"],
                "policy": values["policy"],
                "policy_hash": policy_hash,
                "state": "draft",
                "approved_at_ms": values["approved_at_ms"],
            }
            connection.execute(
                "INSERT INTO settlement_operations(operation_id, request_hash, result_json) VALUES (?, ?, ?)",
                (values["operation_id"], request_hash, self._canonical_json(result)),
            )
            connection.execute(
                """INSERT INTO settlement_policies(
                    policy_id, version, owner_subject, policy_json, policy_hash, state, approved_at_ms
                ) VALUES (?, ?, ?, ?, ?, 'draft', ?)""",
                (
                    values["policy"]["policy_id"], values["policy"]["version"], values["owner_subject"],
                    policy_json, policy_hash, values["approved_at_ms"],
                ),
            )
            connection.execute("COMMIT")
            return result
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            self._release(connection)

    def get_policy(self, policy_id: str) -> Dict[str, Any]:
        policy_id = self._require_text(policy_id, "policy_id")
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM settlement_policies WHERE policy_id = ?", (policy_id,)
            ).fetchone()
            if not row:
                raise SettlementError("policy does not exist")
            policy = self._policy_from_row(row)
            events = connection.execute(
                """SELECT sequence, operation_id, from_state, target_state, evidence_json,
                          reserve_snapshot_json, activated_at_ms
                FROM settlement_policy_activation_events WHERE policy_id = ? ORDER BY sequence""",
                (policy_id,),
            ).fetchall()
            policy["activation_events"] = [
                {
                    "sequence": int(event["sequence"]),
                    "operation_id": event["operation_id"],
                    "from_state": event["from_state"],
                    "target_state": event["target_state"],
                    "evidence": json.loads(event["evidence_json"]),
                    "reserve_snapshot": json.loads(event["reserve_snapshot_json"])
                    if event["reserve_snapshot_json"] else None,
                    "activated_at_ms": int(event["activated_at_ms"]),
                }
                for event in events
            ]
            return policy
        finally:
            self._release(connection)

    def activate_policy(
        self,
        operation_id: str,
        owner_subject: str,
        policy_id: str,
        target_state: str,
        evidence: dict,
        activated_at_ms: int,
    ) -> Dict[str, Any]:
        if not isinstance(evidence, dict):
            raise ValueError("evidence must be an object")
        values = {
            "operation_id": self._require_text(operation_id, "operation_id"),
            "owner_subject": self._require_text(owner_subject, "owner_subject"),
            "policy_id": self._require_text(policy_id, "policy_id"),
            "target_state": self._require_text(target_state, "target_state"),
            "evidence": json.loads(self._canonical_json(evidence)),
            "activated_at_ms": self._require_non_negative_integer(activated_at_ms, "activated_at_ms"),
        }
        if values["target_state"] not in {"allocation_active", "settlement_active"}:
            raise SettlementTransitionError("policy target state is invalid")
        request_hash = self._hash_request(values)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            prior = connection.execute(
                "SELECT request_hash, result_json FROM settlement_operations WHERE operation_id = ?",
                (values["operation_id"],),
            ).fetchone()
            if prior:
                if prior["request_hash"] != request_hash:
                    raise SettlementIdempotencyConflict("operation_id was already used for different settlement intent")
                connection.execute("COMMIT")
                return json.loads(prior["result_json"])
            row = connection.execute(
                "SELECT * FROM settlement_policies WHERE policy_id = ?", (values["policy_id"],)
            ).fetchone()
            if not row:
                raise SettlementError("policy does not exist")
            stored = self._policy_from_row(row)
            if stored["owner_subject"] != values["owner_subject"]:
                raise SettlementTransitionError("policy owner subject does not match")
            policy = stored["policy"]
            self._require_current_policy_runtime_fields(policy)
            if values["activated_at_ms"] < stored["approved_at_ms"]:
                raise SettlementTransitionError("policy activation cannot precede approval")
            if values["activated_at_ms"] < policy["effective_from_ms"] or (
                policy["effective_to_ms"] is not None
                and values["activated_at_ms"] > policy["effective_to_ms"]
            ):
                raise SettlementTransitionError("policy is not effective at the activation time")
            evidence = values["evidence"]
            reserve_snapshot = None
            if stored["state"] == "draft" and values["target_state"] == "allocation_active":
                if policy["cu_milli_per_funding_minor"] <= 0 or policy["program_cap_minor"] <= 0:
                    raise SettlementTransitionError("policy requires a positive rate and funded program cap")
                if evidence.get("compliance_manifest_hash") != policy["compliance_manifest_hash"]:
                    raise SettlementTransitionError("policy requires the approved compliance manifest")
                activation_evidence = {
                    "compliance_manifest_hash": self._require_evidence_hash(
                        evidence.get("compliance_manifest_hash"), "compliance_manifest_hash"
                    ),
                    "owner_signature": self._require_evidence_hash(
                        evidence.get("owner_signature"), "owner_signature"
                    ),
                }
                reserve_snapshot = self._reserve_snapshot(
                    connection, values["owner_subject"], policy, values["activated_at_ms"]
                )
                if (
                    reserve_snapshot["available_balance_minor"] < policy["program_cap_minor"]
                    or reserve_snapshot["receipted_minor"] < policy["program_cap_minor"]
                ):
                    raise SettlementInsufficientFunds("receipted reserve cannot fund the policy program cap")
            elif stored["state"] == "allocation_active" and values["target_state"] == "settlement_active":
                if values["activated_at_ms"] < stored["activated_at_ms"]:
                    raise SettlementTransitionError("policy activation chronology is invalid")
                try:
                    activation_evidence = {"provider_capability_hash": self._require_evidence_hash(
                        evidence.get("provider_capability_hash"), "provider_capability_hash"
                    )}
                except ValueError as error:
                    raise SettlementTransitionError(
                        "policy requires provider capability evidence"
                    ) from error
            else:
                raise SettlementTransitionError("invalid policy lifecycle transition")
            result = {
                "operation_id": values["operation_id"],
                "policy_id": stored["policy_id"],
                "version": stored["version"],
                "owner_subject": stored["owner_subject"],
                "state": values["target_state"],
                "evidence": activation_evidence,
                "reserve_snapshot": reserve_snapshot,
                "activated_at_ms": values["activated_at_ms"],
            }
            connection.execute(
                "INSERT INTO settlement_operations(operation_id, request_hash, result_json) VALUES (?, ?, ?)",
                (values["operation_id"], request_hash, self._canonical_json(result)),
            )
            connection.execute(
                """INSERT INTO settlement_policy_activation_events(
                    operation_id, policy_id, from_state, target_state, evidence_json,
                    reserve_snapshot_json, activated_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    values["operation_id"], stored["policy_id"], stored["state"],
                    values["target_state"], self._canonical_json(activation_evidence),
                    self._canonical_json(reserve_snapshot) if reserve_snapshot else None,
                    values["activated_at_ms"],
                ),
            )
            if values["target_state"] == "allocation_active":
                connection.execute(
                    """UPDATE settlement_policies
                    SET state = ?, activation_evidence_json = ?, activated_at_ms = ?
                    WHERE policy_id = ?""",
                    (values["target_state"], self._canonical_json(activation_evidence), values["activated_at_ms"], stored["policy_id"]),
                )
            else:
                connection.execute(
                    "UPDATE settlement_policies SET state = ? WHERE policy_id = ?",
                    (values["target_state"], stored["policy_id"]),
                )
            connection.execute("COMMIT")
            return result
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            self._release(connection)

    def create_allocation(
        self,
        operation_id: str,
        owner_subject: str,
        world_id: str,
        policy_id: str,
        public_claims: list[dict],
        now_ms: int,
    ) -> Dict[str, Any]:
        """Commit server-resolved public CU claims to an immutable proposed quote."""
        if not isinstance(public_claims, list) or not public_claims:
            raise SettlementError("at least one public claim is required")
        values = {
            "operation_id": self._require_text(operation_id, "operation_id"),
            "owner_subject": self._require_text(owner_subject, "owner_subject"),
            "world_id": self._require_text(world_id, "world_id"),
            "policy_id": self._require_text(policy_id, "policy_id"),
            "public_claims": json.loads(self._canonical_json(public_claims)),
            "now_ms": self._require_non_negative_integer(now_ms, "now_ms"),
        }
        request_hash = self._hash_request(values)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            prior = connection.execute(
                "SELECT request_hash, result_json FROM settlement_operations WHERE operation_id = ?",
                (values["operation_id"],),
            ).fetchone()
            if prior:
                if prior["request_hash"] != request_hash:
                    raise SettlementIdempotencyConflict("operation_id was already used for different settlement intent")
                connection.execute("COMMIT")
                return json.loads(prior["result_json"])
            row = connection.execute(
                "SELECT * FROM settlement_policies WHERE policy_id = ?", (values["policy_id"],)
            ).fetchone()
            if not row:
                raise SettlementError("policy does not exist")
            stored = self._policy_from_row(row)
            policy = stored["policy"]
            self._require_current_policy_runtime_fields(policy)
            if stored["owner_subject"] != values["owner_subject"]:
                raise SettlementTransitionError("policy owner subject does not match")
            if stored["state"] not in {"allocation_active", "settlement_active"}:
                raise SettlementTransitionError("policy is not active for allocations")
            if values["now_ms"] < policy["effective_from_ms"] or (
                policy["effective_to_ms"] is not None and values["now_ms"] > policy["effective_to_ms"]
            ):
                raise SettlementTransitionError("policy is not effective at the proposal time")
            claim_ids = []
            eligible_cu_milli = 0
            for claim in values["public_claims"]:
                if not isinstance(claim, dict):
                    raise SettlementError("public claim is not eligible")
                claim_id = self._require_text(claim.get("entry_id"), "public claim id")
                amount = self._require_positive_integer(claim.get("amount_milli"), "public claim amount_milli")
                if claim_id in claim_ids:
                    raise SettlementError("public claim is duplicated")
                if claim.get("status") != "verified_provisional" or claim.get("spendable") is not False:
                    raise SettlementError("public claim is not eligible")
                if claim.get("unit") != "CU-placeholder" or claim.get("action_type") not in policy["eligible_action_types"]:
                    raise SettlementError("public claim is not eligible")
                if not claim.get("evidence_hash") or not claim.get("commission_hash"):
                    raise SettlementError("public claim is not eligible")
                if not self._claim_meets_evidence_requirements(
                    claim, policy["evidence_requirements"]
                ):
                    raise SettlementError("public claim does not satisfy policy evidence requirements")
                if amount < policy["min_claim_cu_milli"] or amount > policy["max_claim_cu_milli"]:
                    raise SettlementError("public claim is outside the policy allocation range")
                committed = connection.execute(
                    "SELECT allocation_id FROM settlement_claim_commitments WHERE claim_id = ?", (claim_id,)
                ).fetchone()
                if committed:
                    raise SettlementError("public claim is already committed")
                claim_ids.append(claim_id)
                eligible_cu_milli += amount
            quoted_funding_minor = eligible_cu_milli // policy["cu_milli_per_funding_minor"]
            if quoted_funding_minor <= 0:
                raise SettlementError("public claims do not quote a positive funding amount")
            program_total = connection.execute(
                "SELECT COALESCE(SUM(quoted_funding_minor), 0) AS total FROM settlement_allocations WHERE policy_id = ?",
                (stored["policy_id"],),
            ).fetchone()["total"]
            if int(program_total) + quoted_funding_minor > policy["program_cap_minor"]:
                raise SettlementError("policy program cap would be exceeded")
            period_start_ms = policy["effective_from_ms"] + (
                (values["now_ms"] - policy["effective_from_ms"]) // policy["period_ms"]
            ) * policy["period_ms"]
            period_total = connection.execute(
                """SELECT COALESCE(SUM(quoted_funding_minor), 0) AS total
                FROM settlement_allocations WHERE policy_id = ? AND period_start_ms = ?""",
                (stored["policy_id"], period_start_ms),
            ).fetchone()["total"]
            if int(period_total) + quoted_funding_minor > policy["period_cap_minor"]:
                raise SettlementError("policy period cap would be exceeded")
            allocation_id = "allocation:" + hashlib.sha256(
                f"{values['operation_id']}|{stored['policy_id']}|{values['world_id']}".encode("utf-8")
            ).hexdigest()[:32]
            result = {
                "allocation_id": allocation_id,
                "operation_id": values["operation_id"],
                "owner_subject": values["owner_subject"],
                "beneficiary_class": "eov_owner_development",
                "policy_id": stored["policy_id"],
                "policy_version": stored["version"],
                "policy_snapshot": policy,
                "world_id": values["world_id"],
                "public_claim_ids": claim_ids,
                "eligible_cu_milli": eligible_cu_milli,
                "quoted_funding_minor": quoted_funding_minor,
                "period_start_ms": period_start_ms,
                "state": "proposed",
                "created_at_ms": values["now_ms"],
            }
            connection.execute(
                "INSERT INTO settlement_operations(operation_id, request_hash, result_json) VALUES (?, ?, ?)",
                (values["operation_id"], request_hash, self._canonical_json(result)),
            )
            connection.execute(
                """INSERT INTO settlement_allocations(
                    allocation_id, operation_id, owner_subject, beneficiary_class, policy_id, policy_version,
                    policy_snapshot_json, world_id, public_claim_ids_json, eligible_cu_milli,
                    quoted_funding_minor, period_start_ms, state, created_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'proposed', ?)""",
                (
                    allocation_id, values["operation_id"], values["owner_subject"], "eov_owner_development",
                    stored["policy_id"], stored["version"], self._canonical_json(policy), values["world_id"],
                    self._canonical_json(claim_ids), eligible_cu_milli, quoted_funding_minor, period_start_ms,
                    values["now_ms"],
                ),
            )
            connection.executemany(
                "INSERT INTO settlement_claim_commitments(claim_id, allocation_id, policy_id, committed_at_ms) VALUES (?, ?, ?, ?)",
                [(claim_id, allocation_id, stored["policy_id"], values["now_ms"]) for claim_id in claim_ids],
            )
            connection.execute("COMMIT")
            return result
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            self._release(connection)

    def get_allocation(self, allocation_id: str) -> Dict[str, Any]:
        allocation_id = self._require_text(allocation_id, "allocation_id")
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM settlement_allocations WHERE allocation_id = ?", (allocation_id,)
            ).fetchone()
            if not row:
                raise SettlementError("allocation does not exist")
            allocation = {
                "allocation_id": row["allocation_id"],
                "operation_id": row["operation_id"],
                "owner_subject": row["owner_subject"],
                "beneficiary_class": row["beneficiary_class"],
                "policy_id": row["policy_id"],
                "policy_version": int(row["policy_version"]),
                "policy_snapshot": json.loads(row["policy_snapshot_json"]),
                "world_id": row["world_id"],
                "public_claim_ids": json.loads(row["public_claim_ids_json"]),
                "eligible_cu_milli": int(row["eligible_cu_milli"]),
                "quoted_funding_minor": int(row["quoted_funding_minor"]),
                "period_start_ms": int(row["period_start_ms"]),
                "state": row["state"],
                "created_at_ms": int(row["created_at_ms"]),
                "held_at_ms": int(row["held_at_ms"]) if row["held_at_ms"] is not None else None,
                "approval_hash": row["approval_hash"],
                "approved_at_ms": int(row["approved_at_ms"]) if row["approved_at_ms"] is not None else None,
                "expires_at_ms": int(row["expires_at_ms"]) if row["expires_at_ms"] is not None else None,
                "cancelled_at_ms": int(row["cancelled_at_ms"]) if row["cancelled_at_ms"] is not None else None,
                "expired_at_ms": int(row["expired_at_ms"]) if row["expired_at_ms"] is not None else None,
                "provider": row["provider"],
                "provider_operation_id": row["provider_operation_id"],
                "provider_pending_at_ms": int(row["provider_pending_at_ms"]) if row["provider_pending_at_ms"] is not None else None,
                "provider_confirmed_at_ms": int(row["provider_confirmed_at_ms"]) if row["provider_confirmed_at_ms"] is not None else None,
                "reconciled_at_ms": int(row["reconciled_at_ms"]) if row["reconciled_at_ms"] is not None else None,
                "actual_cost_minor": int(row["actual_cost_minor"]) if row["actual_cost_minor"] is not None else None,
                "actual_cost_effective_at_ms": int(row["actual_cost_effective_at_ms"]) if row["actual_cost_effective_at_ms"] is not None else None,
            }
            events = connection.execute(
                """SELECT sequence, operation_id, event_type, from_state, target_state, evidence_json, occurred_at_ms
                FROM settlement_events WHERE allocation_id = ? ORDER BY sequence""",
                (allocation_id,),
            ).fetchall()
            allocation["events"] = [
                {
                    "sequence": int(event["sequence"]),
                    "operation_id": event["operation_id"],
                    "event_type": event["event_type"],
                    "from_state": event["from_state"],
                    "target_state": event["target_state"],
                    "evidence": json.loads(event["evidence_json"]),
                    "occurred_at_ms": int(event["occurred_at_ms"]),
                }
                for event in events
            ]
            return allocation
        finally:
            self._release(connection)

    @staticmethod
    def _allocation_lifecycle_result(
        row: sqlite3.Row,
        operation_id: str,
        state: str,
        now_ms: int,
        **extra: Any,
    ) -> Dict[str, Any]:
        result = {
            "operation_id": operation_id,
            "allocation_id": row["allocation_id"],
            "owner_subject": row["owner_subject"],
            "beneficiary_class": "eov_owner_development",
            "quoted_funding_minor": int(row["quoted_funding_minor"]),
            "state": state,
            "occurred_at_ms": now_ms,
        }
        result.update(extra)
        return result

    @classmethod
    def _require_allocation_owner(cls, row: sqlite3.Row, owner_subject: str) -> None:
        if row["owner_subject"] != owner_subject:
            raise SettlementTransitionError("allocation owner subject does not match")

    @classmethod
    def _allocation_currency(cls, row: sqlite3.Row) -> str:
        policy = json.loads(row["policy_snapshot_json"])
        cls._require_current_policy_runtime_fields(policy)
        return policy["funding_currency"]

    @classmethod
    def _append_lifecycle_event(
        cls,
        connection: sqlite3.Connection,
        operation_id: str,
        allocation_id: str,
        event_type: str,
        from_state: str,
        target_state: str,
        evidence: Dict[str, Any],
        now_ms: int,
    ) -> None:
        connection.execute(
            """INSERT INTO settlement_events(
                operation_id, allocation_id, event_type, from_state, target_state, evidence_json, occurred_at_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                operation_id, allocation_id, event_type, from_state, target_state,
                cls._canonical_json(evidence), now_ms,
            ),
        )

    @staticmethod
    def _require_lifecycle_transition(current_state: str, action: str) -> str:
        target = _ALLOCATION_TRANSITIONS[action].get(current_state)
        if target is None:
            raise SettlementTransitionError(
                f"allocation transition to {_ALLOCATION_TRANSITIONS[action].values()} is invalid"
            )
        return target

    @classmethod
    def _move_reserve(
        cls,
        connection: sqlite3.Connection,
        operation_id: str,
        source_account: str,
        destination_account: str,
        currency: str,
        amount_minor: int,
        evidence_hash: str,
        now_ms: int,
    ) -> None:
        source = connection.execute(
            "SELECT balance_minor FROM settlement_accounts WHERE account_id = ?", (source_account,)
        ).fetchone()
        as_of = connection.execute(
            """SELECT COALESCE(SUM(delta_minor), 0) AS balance_minor
            FROM settlement_postings WHERE account_id = ? AND occurred_at_ms <= ?""",
            (source_account, now_ms),
        ).fetchone()
        if (
            source is None
            or int(source["balance_minor"]) < amount_minor
            or int(as_of["balance_minor"]) < amount_minor
        ):
            raise SettlementInsufficientFunds("reserve:available cannot cover the allocation hold")
        connection.executemany(
            "INSERT OR IGNORE INTO settlement_accounts(account_id, currency) VALUES (?, ?)",
            [(source_account, currency), (destination_account, currency)],
        )
        connection.execute(
            "UPDATE settlement_accounts SET balance_minor = balance_minor - ? WHERE account_id = ?",
            (amount_minor, source_account),
        )
        connection.execute(
            "UPDATE settlement_accounts SET balance_minor = balance_minor + ? WHERE account_id = ?",
            (amount_minor, destination_account),
        )
        connection.executemany(
            """INSERT INTO settlement_postings(
                operation_id, account_id, currency, delta_minor, evidence_hash, occurred_at_ms
            ) VALUES (?, ?, ?, ?, ?, ?)""",
            [
                (operation_id, source_account, currency, -amount_minor, evidence_hash, now_ms),
                (operation_id, destination_account, currency, amount_minor, evidence_hash, now_ms),
            ],
        )

    def hold_allocation(
        self, operation_id: str, allocation_id: str, owner_subject: str, now_ms: int,
    ) -> Dict[str, Any]:
        """Move a quoted allocation into a same-currency, allocation-specific reserve hold."""
        values = {
            "operation_id": self._require_text(operation_id, "operation_id"),
            "allocation_id": self._require_text(allocation_id, "allocation_id"),
            "owner_subject": self._require_text(owner_subject, "owner_subject"),
            "now_ms": self._require_non_negative_integer(now_ms, "now_ms"),
        }
        request_hash = self._hash_request(values)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            prior = connection.execute(
                "SELECT request_hash, result_json FROM settlement_operations WHERE operation_id = ?",
                (values["operation_id"],),
            ).fetchone()
            if prior:
                if prior["request_hash"] != request_hash:
                    raise SettlementIdempotencyConflict("operation_id was already used for different settlement intent")
                connection.execute("COMMIT")
                return json.loads(prior["result_json"])
            row = connection.execute(
                "SELECT * FROM settlement_allocations WHERE allocation_id = ?", (values["allocation_id"],)
            ).fetchone()
            if not row:
                raise SettlementError("allocation does not exist")
            self._require_allocation_owner(row, values["owner_subject"])
            self._require_lifecycle_transition(row["state"], "hold")
            if values["now_ms"] < int(row["created_at_ms"]):
                raise SettlementTransitionError("allocation hold chronology is invalid")
            currency = self._allocation_currency(row)
            available = self._account_id("reserve:available", currency)
            held = self._account_id(f"reserve:held:{row['allocation_id']}", currency)
            amount = int(row["quoted_funding_minor"])
            evidence_hash = json.loads(row["policy_snapshot_json"])["compliance_manifest_hash"]
            result = self._allocation_lifecycle_result(
                row, values["operation_id"], "funding_held", values["now_ms"],
                currency=currency, source_account=available, destination_account=held,
            )
            connection.execute(
                "INSERT INTO settlement_operations(operation_id, request_hash, result_json) VALUES (?, ?, ?)",
                (values["operation_id"], request_hash, self._canonical_json(result)),
            )
            self._move_reserve(
                connection, values["operation_id"], available, held, currency, amount,
                evidence_hash, values["now_ms"],
            )
            connection.execute(
                "UPDATE settlement_allocations SET state = 'funding_held', held_at_ms = ? WHERE allocation_id = ?",
                (values["now_ms"], row["allocation_id"]),
            )
            self._append_lifecycle_event(
                connection, values["operation_id"], row["allocation_id"], "allocation_held",
                "proposed", "funding_held", {"funding_evidence_hash": evidence_hash}, values["now_ms"],
            )
            connection.execute("COMMIT")
            return result
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            self._release(connection)

    def approve_allocation(
        self,
        operation_id: str,
        allocation_id: str,
        owner_subject: str,
        approval_hash: str,
        expires_at_ms: int,
        now_ms: int,
    ) -> Dict[str, Any]:
        """Record the owner's explicit approval of an already-held exact quote."""
        values = {
            "operation_id": self._require_text(operation_id, "operation_id"),
            "allocation_id": self._require_text(allocation_id, "allocation_id"),
            "owner_subject": self._require_text(owner_subject, "owner_subject"),
            "approval_hash": self._require_evidence_hash(approval_hash, "approval_hash"),
            "expires_at_ms": self._require_non_negative_integer(expires_at_ms, "expires_at_ms"),
            "now_ms": self._require_non_negative_integer(now_ms, "now_ms"),
        }
        if values["expires_at_ms"] <= values["now_ms"]:
            raise ValueError("expires_at_ms must be later than now_ms")
        request_hash = self._hash_request(values)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            prior = connection.execute(
                "SELECT request_hash, result_json FROM settlement_operations WHERE operation_id = ?",
                (values["operation_id"],),
            ).fetchone()
            if prior:
                if prior["request_hash"] != request_hash:
                    raise SettlementIdempotencyConflict("operation_id was already used for different settlement intent")
                connection.execute("COMMIT")
                return json.loads(prior["result_json"])
            row = connection.execute(
                "SELECT * FROM settlement_allocations WHERE allocation_id = ?", (values["allocation_id"],)
            ).fetchone()
            if not row:
                raise SettlementError("allocation does not exist")
            self._require_allocation_owner(row, values["owner_subject"])
            self._require_lifecycle_transition(row["state"], "approve")
            if values["now_ms"] < int(row["held_at_ms"]):
                raise SettlementTransitionError("allocation approval chronology is invalid")
            result = self._allocation_lifecycle_result(
                row, values["operation_id"], "owner_approved", values["now_ms"],
                approval_hash=values["approval_hash"], expires_at_ms=values["expires_at_ms"],
            )
            connection.execute(
                "INSERT INTO settlement_operations(operation_id, request_hash, result_json) VALUES (?, ?, ?)",
                (values["operation_id"], request_hash, self._canonical_json(result)),
            )
            connection.execute(
                """UPDATE settlement_allocations
                SET state = 'owner_approved', approval_hash = ?, approved_at_ms = ?, expires_at_ms = ?
                WHERE allocation_id = ?""",
                (values["approval_hash"], values["now_ms"], values["expires_at_ms"], row["allocation_id"]),
            )
            self._append_lifecycle_event(
                connection, values["operation_id"], row["allocation_id"], "owner_approved",
                "funding_held", "owner_approved", {
                    "approval_hash": values["approval_hash"], "expires_at_ms": values["expires_at_ms"],
                }, values["now_ms"],
            )
            connection.execute("COMMIT")
            return result
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            self._release(connection)

    def cancel_allocation(
        self, operation_id: str, allocation_id: str, owner_subject: str, reason: str, now_ms: int,
    ) -> Dict[str, Any]:
        """Cancel a pre-provider allocation and release any held reserve exactly once."""
        values = {
            "operation_id": self._require_text(operation_id, "operation_id"),
            "allocation_id": self._require_text(allocation_id, "allocation_id"),
            "owner_subject": self._require_text(owner_subject, "owner_subject"),
            "reason": self._require_text(reason, "reason"),
            "now_ms": self._require_non_negative_integer(now_ms, "now_ms"),
        }
        request_hash = self._hash_request(values)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            prior = connection.execute(
                "SELECT request_hash, result_json FROM settlement_operations WHERE operation_id = ?",
                (values["operation_id"],),
            ).fetchone()
            if prior:
                if prior["request_hash"] != request_hash:
                    raise SettlementIdempotencyConflict("operation_id was already used for different settlement intent")
                connection.execute("COMMIT")
                return json.loads(prior["result_json"])
            row = connection.execute(
                "SELECT * FROM settlement_allocations WHERE allocation_id = ?", (values["allocation_id"],)
            ).fetchone()
            if not row:
                raise SettlementError("allocation does not exist")
            self._require_allocation_owner(row, values["owner_subject"])
            self._require_lifecycle_transition(row["state"], "cancel")
            if values["now_ms"] < int(row["created_at_ms"]):
                raise SettlementTransitionError("allocation cancellation chronology is invalid")
            if row["state"] == "funding_held" and values["now_ms"] < int(row["held_at_ms"]):
                raise SettlementTransitionError("allocation cancellation chronology is invalid")
            if row["state"] == "owner_approved":
                if values["now_ms"] < int(row["approved_at_ms"]):
                    raise SettlementTransitionError("allocation cancellation chronology is invalid")
                if values["now_ms"] >= int(row["expires_at_ms"]):
                    raise SettlementTransitionError("allocation approval is expired; use expire_due")
            currency = self._allocation_currency(row)
            result = self._allocation_lifecycle_result(
                row, values["operation_id"], "cancelled", values["now_ms"], reason=values["reason"],
            )
            connection.execute(
                "INSERT INTO settlement_operations(operation_id, request_hash, result_json) VALUES (?, ?, ?)",
                (values["operation_id"], request_hash, self._canonical_json(result)),
            )
            if row["state"] in {"funding_held", "owner_approved"}:
                held = self._account_id(f"reserve:held:{row['allocation_id']}", currency)
                available = self._account_id("reserve:available", currency)
                self._move_reserve(
                    connection, values["operation_id"], held, available, currency,
                    int(row["quoted_funding_minor"]), row["approval_hash"] or json.loads(row["policy_snapshot_json"])["compliance_manifest_hash"],
                    values["now_ms"],
                )
            connection.execute(
                "DELETE FROM settlement_claim_commitments WHERE allocation_id = ?", (row["allocation_id"],)
            )
            connection.execute(
                "UPDATE settlement_allocations SET state = 'cancelled', cancelled_at_ms = ? WHERE allocation_id = ?",
                (values["now_ms"], row["allocation_id"]),
            )
            self._append_lifecycle_event(
                connection, values["operation_id"], row["allocation_id"], "allocation_cancelled",
                row["state"], "cancelled", {"reason": values["reason"]}, values["now_ms"],
            )
            connection.execute("COMMIT")
            return result
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            self._release(connection)

    def expire_due(self, operation_id: str, now_ms: int) -> list[Dict[str, Any]]:
        """Deterministically expire all due owner approvals in one transaction."""
        values = {
            "operation_id": self._require_text(operation_id, "operation_id"),
            "now_ms": self._require_non_negative_integer(now_ms, "now_ms"),
        }
        request_hash = self._hash_request(values)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            prior = connection.execute(
                "SELECT request_hash, result_json FROM settlement_operations WHERE operation_id = ?",
                (values["operation_id"],),
            ).fetchone()
            if prior:
                if prior["request_hash"] != request_hash:
                    raise SettlementIdempotencyConflict("operation_id was already used for different settlement intent")
                connection.execute("COMMIT")
                return json.loads(prior["result_json"])
            rows = connection.execute(
                """SELECT * FROM settlement_allocations
                WHERE state = 'owner_approved' AND expires_at_ms <= ?
                ORDER BY allocation_id""",
                (values["now_ms"],),
            ).fetchall()
            results = []
            connection.execute(
                "INSERT INTO settlement_operations(operation_id, request_hash, result_json) VALUES (?, ?, ?)",
                (values["operation_id"], request_hash, self._canonical_json(results)),
            )
            for row in rows:
                self._require_lifecycle_transition(row["state"], "expire")
                currency = self._allocation_currency(row)
                held = self._account_id(f"reserve:held:{row['allocation_id']}", currency)
                available = self._account_id("reserve:available", currency)
                self._move_reserve(
                    connection, values["operation_id"], held, available, currency,
                    int(row["quoted_funding_minor"]), row["approval_hash"], values["now_ms"],
                )
                connection.execute(
                    "DELETE FROM settlement_claim_commitments WHERE allocation_id = ?", (row["allocation_id"],)
                )
                connection.execute(
                    "UPDATE settlement_allocations SET state = 'expired', expired_at_ms = ? WHERE allocation_id = ?",
                    (values["now_ms"], row["allocation_id"]),
                )
                self._append_lifecycle_event(
                    connection, values["operation_id"], row["allocation_id"], "allocation_expired",
                    "owner_approved", "expired", {"approval_hash": row["approval_hash"]}, values["now_ms"],
                )
                results.append(self._allocation_lifecycle_result(
                    row, values["operation_id"], "expired", values["now_ms"],
                    approval_hash=row["approval_hash"], expires_at_ms=int(row["expires_at_ms"]),
                ))
            connection.execute(
                "UPDATE settlement_operations SET result_json = ? WHERE operation_id = ?",
                (self._canonical_json(results), values["operation_id"]),
            )
            connection.execute("COMMIT")
            return results
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            self._release(connection)

    def begin_provider_submission(
        self, operation_id: str, allocation_id: str, owner_subject: str,
        provider: str, capability_hash: str, now_ms: int,
    ) -> Dict[str, Any]:
        """Persist one provider operation before an adapter can be contacted."""
        values = {
            "operation_id": self._require_text(operation_id, "operation_id"),
            "allocation_id": self._require_text(allocation_id, "allocation_id"),
            "owner_subject": self._require_text(owner_subject, "owner_subject"),
            "provider": self._require_text(provider, "provider"),
            "capability_hash": self._require_evidence_hash(capability_hash, "capability_hash"),
            "now_ms": self._require_non_negative_integer(now_ms, "now_ms"),
        }
        request_hash = self._hash_request(values)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            prior = connection.execute("SELECT request_hash, result_json FROM settlement_operations WHERE operation_id = ?", (values["operation_id"],)).fetchone()
            if prior:
                if prior["request_hash"] != request_hash:
                    raise SettlementIdempotencyConflict("operation_id was already used for different settlement intent")
                connection.execute("COMMIT")
                return json.loads(prior["result_json"])
            row = connection.execute("SELECT * FROM settlement_allocations WHERE allocation_id = ?", (values["allocation_id"],)).fetchone()
            if not row:
                raise SettlementError("allocation does not exist")
            self._require_allocation_owner(row, values["owner_subject"])
            policy = connection.execute("SELECT state FROM settlement_policies WHERE policy_id = ?", (row["policy_id"],)).fetchone()
            if not policy or policy["state"] != "settlement_active":
                raise SettlementTransitionError("settlement_active policy is required before provider submission")
            if row["state"] == "owner_approved":
                if values["now_ms"] >= int(row["expires_at_ms"]):
                    raise SettlementTransitionError("owner approval has expired")
                if values["now_ms"] < int(row["approved_at_ms"]):
                    raise SettlementTransitionError("provider submission chronology is invalid")
                provider_operation_id = "eov:" + row["allocation_id"]
                result = self._allocation_lifecycle_result(row, values["operation_id"], "provider_pending", values["now_ms"], provider=values["provider"], provider_operation_id=provider_operation_id)
                connection.execute("INSERT INTO settlement_operations(operation_id, request_hash, result_json) VALUES (?, ?, ?)", (values["operation_id"], request_hash, self._canonical_json(result)))
                connection.execute("UPDATE settlement_allocations SET state = 'provider_pending', provider = ?, provider_operation_id = ?, provider_pending_at_ms = ? WHERE allocation_id = ?", (values["provider"], provider_operation_id, values["now_ms"], row["allocation_id"]))
                self._append_lifecycle_event(connection, values["operation_id"], row["allocation_id"], "provider_submitted", "owner_approved", "provider_pending", {"provider": values["provider"], "provider_operation_id": provider_operation_id, "capability_hash": values["capability_hash"]}, values["now_ms"])
                connection.execute("COMMIT")
                return result
            if row["state"] == "provider_pending" and row["provider"] == values["provider"]:
                result = self._allocation_lifecycle_result(row, values["operation_id"], "provider_pending", values["now_ms"], provider=row["provider"], provider_operation_id=row["provider_operation_id"])
                connection.execute("INSERT INTO settlement_operations(operation_id, request_hash, result_json) VALUES (?, ?, ?)", (values["operation_id"], request_hash, self._canonical_json(result)))
                connection.execute("COMMIT")
                return result
            raise SettlementTransitionError("allocation transition to provider_pending is invalid")
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            self._release(connection)

    def confirm_provider_receipt(self, operation_id: str, allocation_id: str, owner_subject: str, receipt: dict, now_ms: int) -> Dict[str, Any]:
        """Attach canonical, completed billing evidence to exactly one pending allocation."""
        values = {"operation_id": self._require_text(operation_id, "operation_id"), "allocation_id": self._require_text(allocation_id, "allocation_id"), "owner_subject": self._require_text(owner_subject, "owner_subject"), "receipt": receipt, "now_ms": self._require_non_negative_integer(now_ms, "now_ms")}
        if not isinstance(receipt, dict):
            raise ValueError("receipt must be an object")
        request_hash = self._hash_request(values)
        receipt_json = self._canonical_json(receipt)
        receipt_hash = "sha256:" + hashlib.sha256(receipt_json.encode("utf-8")).hexdigest()
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            prior = connection.execute("SELECT request_hash, result_json FROM settlement_operations WHERE operation_id = ?", (values["operation_id"],)).fetchone()
            if prior:
                if prior["request_hash"] != request_hash:
                    raise SettlementIdempotencyConflict("operation_id was already used for different settlement intent")
                connection.execute("COMMIT")
                return json.loads(prior["result_json"])
            row = connection.execute("SELECT * FROM settlement_allocations WHERE allocation_id = ?", (values["allocation_id"],)).fetchone()
            if not row:
                raise SettlementError("allocation does not exist")
            self._require_allocation_owner(row, values["owner_subject"])
            expected_operation_commitment = "sha256:" + hashlib.sha256(
                f"operation:{row['provider_operation_id']}".encode("utf-8")
            ).hexdigest()
            if receipt.get("provider_operation_id_commitment") != expected_operation_commitment:
                raise SettlementTransitionError("provider receipt does not match the pending allocation operation")
            existing = connection.execute(
                """SELECT allocation_id, receipt_hash FROM settlement_provider_receipts
                WHERE provider = ? AND (
                    receipt_id_commitment = ? OR provider_transaction_id_commitment = ?
                )""",
                (receipt["provider"], receipt["receipt_id_commitment"], receipt["provider_transaction_id_commitment"]),
            ).fetchone()
            if existing:
                if existing["allocation_id"] != row["allocation_id"] or existing["receipt_hash"] != receipt_hash:
                    raise SettlementIdempotencyConflict("provider receipt is already bound to another allocation or payload")
                result = self._allocation_lifecycle_result(row, values["operation_id"], row["state"], values["now_ms"], provider=row["provider"], provider_operation_id=row["provider_operation_id"], receipt_hash=receipt_hash)
                connection.execute("INSERT INTO settlement_operations(operation_id, request_hash, result_json) VALUES (?, ?, ?)", (values["operation_id"], request_hash, self._canonical_json(result)))
                connection.execute("COMMIT")
                return result
            self._require_lifecycle_transition(row["state"], "provider_confirm")
            if receipt["provider"] != row["provider"] or receipt["currency"] != self._allocation_currency(row):
                raise SettlementTransitionError("provider receipt does not match allocation provider or currency")
            if receipt["completed_at_ms"] < int(row["provider_pending_at_ms"]) or receipt["completed_at_ms"] > values["now_ms"]:
                raise SettlementTransitionError("provider receipt chronology is invalid")
            result = self._allocation_lifecycle_result(row, values["operation_id"], "provider_confirmed", values["now_ms"], provider=row["provider"], provider_operation_id=row["provider_operation_id"], receipt_hash=receipt_hash)
            connection.execute("INSERT INTO settlement_operations(operation_id, request_hash, result_json) VALUES (?, ?, ?)", (values["operation_id"], request_hash, self._canonical_json(result)))
            connection.execute(
                """INSERT INTO settlement_provider_receipts(
                    provider, receipt_id_commitment, provider_transaction_id_commitment,
                    provider_operation_id_commitment, allocation_id, receipt_json, receipt_hash, recorded_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (receipt["provider"], receipt["receipt_id_commitment"], receipt["provider_transaction_id_commitment"],
                 receipt["provider_operation_id_commitment"], row["allocation_id"], receipt_json, receipt_hash,
                 values["now_ms"]),
            )
            connection.execute("UPDATE settlement_allocations SET state = 'provider_confirmed', provider_confirmed_at_ms = ? WHERE allocation_id = ?", (values["now_ms"], row["allocation_id"]))
            self._append_lifecycle_event(connection, values["operation_id"], row["allocation_id"], "provider_confirmed", "provider_pending", "provider_confirmed", {"receipt_hash": receipt_hash, "provider": row["provider"]}, values["now_ms"])
            connection.execute("COMMIT")
            return result
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            self._release(connection)

    def reconcile_provider_cost(self, operation_id: str, allocation_id: str, owner_subject: str, costs: list[dict], now_ms: int) -> Dict[str, Any]:
        """Atomically capture actual cost or record a no-overdraft exception."""
        values = {"operation_id": self._require_text(operation_id, "operation_id"), "allocation_id": self._require_text(allocation_id, "allocation_id"), "owner_subject": self._require_text(owner_subject, "owner_subject"), "costs": costs, "now_ms": self._require_non_negative_integer(now_ms, "now_ms")}
        if not isinstance(costs, list) or not costs:
            raise ValueError("at least one normalized provider cost is required")
        request_hash = self._hash_request(values)
        cost_json = self._canonical_json(costs)
        cost_hash = "sha256:" + hashlib.sha256(cost_json.encode("utf-8")).hexdigest()
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            prior = connection.execute("SELECT request_hash, result_json FROM settlement_operations WHERE operation_id = ?", (values["operation_id"],)).fetchone()
            if prior:
                if prior["request_hash"] != request_hash:
                    raise SettlementIdempotencyConflict("operation_id was already used for different settlement intent")
                connection.execute("COMMIT")
                return json.loads(prior["result_json"])
            row = connection.execute("SELECT * FROM settlement_allocations WHERE allocation_id = ?", (values["allocation_id"],)).fetchone()
            if not row:
                raise SettlementError("allocation does not exist")
            self._require_allocation_owner(row, values["owner_subject"])
            self._require_lifecycle_transition(row["state"], "reconcile_start")
            currency = self._allocation_currency(row)
            total = 0
            effective_at_ms = 0
            record_commitments = set()
            for cost in costs:
                if not isinstance(cost, dict) or cost.get("provider_operation_id") != row["provider_operation_id"] or cost.get("currency") != currency:
                    raise SettlementTransitionError("provider cost cannot be attributed to this allocation")
                amount = cost.get("amount_minor")
                if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
                    raise ValueError("provider cost amount_minor must be a non-negative integer")
                record_commitment = cost.get("record_commitment")
                if not isinstance(record_commitment, str) or not _EVIDENCE_HASH.fullmatch(record_commitment):
                    raise ValueError("provider cost requires a stable record commitment")
                if record_commitment in record_commitments:
                    raise SettlementIdempotencyConflict("provider cost record is duplicated in one reconciliation")
                record_commitments.add(record_commitment)
                if cost.get("start_time_ms") < int(row["provider_pending_at_ms"]) or cost.get("end_time_ms") < cost.get("start_time_ms") or cost.get("end_time_ms") > values["now_ms"]:
                    raise SettlementTransitionError("provider cost chronology is invalid")
                existing_record = connection.execute(
                    "SELECT allocation_id FROM settlement_provider_cost_records WHERE provider = ? AND record_commitment = ?",
                    (row["provider"], record_commitment),
                ).fetchone()
                if existing_record:
                    raise SettlementIdempotencyConflict("provider cost record is already bound to an allocation")
                total += amount
                effective_at_ms = max(effective_at_ms, int(cost["end_time_ms"]))
            connection.execute("INSERT INTO settlement_operations(operation_id, request_hash, result_json) VALUES (?, ?, ?)", (values["operation_id"], request_hash, "{}"))
            connection.execute("INSERT INTO settlement_provider_costs(allocation_id, cost_hash, cost_json, recorded_at_ms) VALUES (?, ?, ?, ?)", (row["allocation_id"], cost_hash, cost_json, values["now_ms"]))
            connection.executemany(
                """INSERT INTO settlement_provider_cost_records(
                    provider, record_commitment, allocation_id, cost_hash, effective_at_ms, recorded_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?)""",
                [(row["provider"], cost["record_commitment"], row["allocation_id"], cost_hash,
                  cost["end_time_ms"], values["now_ms"]) for cost in costs],
            )
            self._append_lifecycle_event(connection, values["operation_id"], row["allocation_id"], "reconciliation_started", "provider_confirmed", "reconciling", {"cost_hash": cost_hash}, values["now_ms"])
            held = int(row["quoted_funding_minor"])
            if total > held:
                result = self._allocation_lifecycle_result(row, values["operation_id"], "reconciliation_exception", values["now_ms"], provider=row["provider"], actual_cost_minor=total, actual_cost_effective_at_ms=effective_at_ms, cost_hash=cost_hash)
                connection.execute("UPDATE settlement_allocations SET state = 'reconciliation_exception', actual_cost_minor = ?, actual_cost_effective_at_ms = ? WHERE allocation_id = ?", (total, effective_at_ms, row["allocation_id"]))
                self._append_lifecycle_event(connection, values["operation_id"], row["allocation_id"], "reconciliation_exception", "reconciling", "reconciliation_exception", {"cost_hash": cost_hash, "actual_cost_minor": total, "actual_cost_effective_at_ms": effective_at_ms}, values["now_ms"])
            else:
                held_account = self._account_id(f"reserve:held:{row['allocation_id']}", currency)
                expense = self._account_id(f"expense:provider:{row['provider']}", currency)
                available = self._account_id("reserve:available", currency)
                evidence_hash = cost_hash
                for cost in costs:
                    if cost["amount_minor"]:
                        self._move_reserve(
                            connection, values["operation_id"], held_account, expense, currency,
                            cost["amount_minor"], evidence_hash, cost["end_time_ms"],
                        )
                if held - total:
                    self._move_reserve(connection, values["operation_id"], held_account, available, currency, held - total, evidence_hash, values["now_ms"])
                result = self._allocation_lifecycle_result(row, values["operation_id"], "reconciled", values["now_ms"], provider=row["provider"], actual_cost_minor=total, actual_cost_effective_at_ms=effective_at_ms, cost_hash=cost_hash)
                connection.execute("UPDATE settlement_allocations SET state = 'reconciled', actual_cost_minor = ?, actual_cost_effective_at_ms = ?, reconciled_at_ms = ? WHERE allocation_id = ?", (total, effective_at_ms, values["now_ms"], row["allocation_id"]))
                self._append_lifecycle_event(connection, values["operation_id"], row["allocation_id"], "allocation_reconciled", "reconciling", "reconciled", {"cost_hash": cost_hash, "actual_cost_minor": total, "actual_cost_effective_at_ms": effective_at_ms}, values["now_ms"])
            connection.execute("UPDATE settlement_operations SET result_json = ? WHERE operation_id = ?", (self._canonical_json(result), values["operation_id"]))
            connection.execute("COMMIT")
            return result
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            self._release(connection)

    def record_funding(
        self,
        operation_id: str,
        owner_subject: str,
        amount_minor: int,
        currency: str,
        source_class: str,
        evidence_hash: str,
        received_at_ms: int,
    ) -> Dict[str, Any]:
        values = self._normalize_inputs(
            operation_id, owner_subject, amount_minor, currency,
            source_class, evidence_hash, received_at_ms,
        )
        request_hash = self._hash_request(values)
        currency = values["currency"]
        contra = self._account_id("external-receipts", currency)
        reserve = self._account_id("reserve:available", currency)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            prior = connection.execute(
                "SELECT request_hash, result_json FROM settlement_operations WHERE operation_id = ?",
                (values["operation_id"],),
            ).fetchone()
            if prior:
                if prior["request_hash"] != request_hash:
                    raise SettlementIdempotencyConflict(
                        "operation_id was already used for different funding intent"
                    )
                connection.execute("COMMIT")
                return json.loads(prior["result_json"])

            connection.executemany(
                "INSERT OR IGNORE INTO settlement_accounts(account_id, currency) VALUES (?, ?)",
                [(contra, currency), (reserve, currency)],
            )
            # The contra account is the one and only account permitted to go
            # negative.  The reserve therefore always reflects real receipts.
            connection.execute(
                "UPDATE settlement_accounts SET balance_minor = balance_minor - ? WHERE account_id = ?",
                (values["amount_minor"], contra),
            )
            connection.execute(
                "UPDATE settlement_accounts SET balance_minor = balance_minor + ? WHERE account_id = ?",
                (values["amount_minor"], reserve),
            )
            result = {
                "operation_id": values["operation_id"],
                "owner_subject": values["owner_subject"],
                "amount_minor": values["amount_minor"],
                "currency": currency,
                "source_class": values["source_class"],
                "evidence_hash": values["evidence_hash"],
                "received_at_ms": values["received_at_ms"],
                "source_account": contra,
                "destination_account": reserve,
                "funding_basis": "external_receipt",
                "spendable": True,
            }
            connection.execute(
                "INSERT INTO settlement_operations(operation_id, request_hash, result_json) VALUES (?, ?, ?)",
                (values["operation_id"], request_hash, json.dumps(result, sort_keys=True, separators=(",", ":"))),
            )
            connection.execute(
                "INSERT INTO funding_receipts(operation_id, owner_subject, amount_minor, currency, source_class, evidence_hash, received_at_ms) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (values["operation_id"], values["owner_subject"], values["amount_minor"], currency, values["source_class"], values["evidence_hash"], values["received_at_ms"]),
            )
            connection.executemany(
                """INSERT INTO settlement_postings(
                    operation_id, account_id, currency, delta_minor, evidence_hash, occurred_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?)""",
                [
                    (values["operation_id"], contra, currency, -values["amount_minor"], values["evidence_hash"], values["received_at_ms"]),
                    (values["operation_id"], reserve, currency, values["amount_minor"], values["evidence_hash"], values["received_at_ms"]),
                ],
            )
            connection.execute("COMMIT")
            return result
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            self._release(connection)

    def funding_balance(self, account: str = "reserve:available", currency: str = "usd") -> int:
        account = self._require_text(account, "account")
        currency = self._require_text(currency, "currency").lower()
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT balance_minor FROM settlement_accounts WHERE account_id = ?",
                (self._account_id(account, currency),),
            ).fetchone()
            return int(row["balance_minor"]) if row else 0
        finally:
            self._release(connection)

    def audit_funding(self) -> Dict[str, Any]:
        connection = self._connect()
        try:
            account_total = connection.execute(
                "SELECT COALESCE(SUM(balance_minor), 0) AS total FROM settlement_accounts"
            ).fetchone()["total"]
            unbalanced = connection.execute(
                "SELECT operation_id, SUM(delta_minor) AS total FROM settlement_postings GROUP BY operation_id HAVING total != 0"
            ).fetchall()
            drift = connection.execute(
                """
                SELECT a.account_id, a.balance_minor, COALESCE(SUM(p.delta_minor), 0) AS posted
                FROM settlement_accounts a LEFT JOIN settlement_postings p ON p.account_id = a.account_id
                GROUP BY a.account_id HAVING a.balance_minor != posted
                """
            ).fetchall()
            invalid_negative = connection.execute(
                "SELECT account_id FROM settlement_accounts WHERE balance_minor < 0 AND account_id NOT LIKE 'external-receipts:%'"
            ).fetchall()
            receipts = connection.execute("SELECT COUNT(*) AS count FROM funding_receipts").fetchone()["count"]
            return {
                "balanced": account_total == 0 and not unbalanced and not drift and not invalid_negative,
                "account_total": account_total,
                "unbalanced_operations": [row["operation_id"] for row in unbalanced],
                "drift_accounts": [row["account_id"] for row in drift],
                "invalid_negative_accounts": [row["account_id"] for row in invalid_negative],
                "funding_receipts": receipts,
            }
        finally:
            self._release(connection)
