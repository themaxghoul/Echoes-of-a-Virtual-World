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
                CREATE INDEX IF NOT EXISTS idx_settlement_postings_operation
                    ON settlement_postings(operation_id);
                CREATE INDEX IF NOT EXISTS idx_settlement_postings_account
                    ON settlement_postings(account_id);
                """
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
