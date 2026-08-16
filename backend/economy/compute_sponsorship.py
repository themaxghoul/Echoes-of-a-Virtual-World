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
                    FOREIGN KEY(operation_id) REFERENCES settlement_operations(operation_id),
                    FOREIGN KEY(account_id) REFERENCES settlement_accounts(account_id),
                    CHECK(typeof(delta_minor) = 'integer')
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
                    FOREIGN KEY(operation_id) REFERENCES settlement_operations(operation_id),
                    FOREIGN KEY(policy_id) REFERENCES settlement_policies(policy_id),
                    CHECK(beneficiary_class = 'eov_owner_development'),
                    CHECK(state = 'proposed'),
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
                CREATE INDEX IF NOT EXISTS idx_settlement_postings_operation
                    ON settlement_postings(operation_id);
                CREATE INDEX IF NOT EXISTS idx_settlement_postings_account
                    ON settlement_postings(account_id);
                CREATE INDEX IF NOT EXISTS idx_settlement_allocations_policy
                    ON settlement_allocations(policy_id);
                CREATE INDEX IF NOT EXISTS idx_settlement_claim_commitments_allocation
                    ON settlement_claim_commitments(allocation_id);
                CREATE INDEX IF NOT EXISTS idx_settlement_policy_activation_events_policy
                    ON settlement_policy_activation_events(policy_id, sequence);
                """
            )
            allocation_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(settlement_allocations)")
            }
            if "period_start_ms" not in allocation_columns:
                connection.execute(
                    "ALTER TABLE settlement_allocations ADD COLUMN period_start_ms INTEGER NOT NULL DEFAULT 0"
                )
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
            """SELECT COALESCE(SUM(amount_minor), 0) AS balance_minor
            FROM funding_receipts WHERE currency = ? AND received_at_ms <= ?""",
            (currency, as_of_ms),
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
            return {
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
            }
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
                "INSERT INTO settlement_postings(operation_id, account_id, currency, delta_minor, evidence_hash) VALUES (?, ?, ?, ?, ?)",
                [
                    (values["operation_id"], contra, currency, -values["amount_minor"], values["evidence_hash"]),
                    (values["operation_id"], reserve, currency, values["amount_minor"], values["evidence_hash"]),
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
