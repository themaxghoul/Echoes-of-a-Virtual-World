"""Atomic, integer, double-entry ledger for non-spendable EoV simulation value."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any, Dict, Iterable


class LedgerError(RuntimeError):
    pass


class InsufficientFunds(LedgerError):
    pass


class IdempotencyConflict(LedgerError):
    pass


class SimulationLedger:
    """Transactional shadow ledger; it has no deposit, withdrawal, or provider API."""

    def __init__(self, database_path: Path | str, allow_negative: Iterable[str] = ("treasury",)):
        self.database_path = str(database_path)
        self.allow_negative = frozenset(allow_negative)
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS simulation_accounts (
                    account_id TEXT PRIMARY KEY, balance_units INTEGER NOT NULL DEFAULT 0,
                    CHECK(typeof(balance_units) = 'integer')
                );
                CREATE TABLE IF NOT EXISTS simulation_operations (
                    operation_id TEXT PRIMARY KEY, request_hash TEXT NOT NULL,
                    result_json TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS simulation_postings (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT, operation_id TEXT NOT NULL,
                    account_id TEXT NOT NULL, delta_units INTEGER NOT NULL, evidence TEXT NOT NULL,
                    FOREIGN KEY(operation_id) REFERENCES simulation_operations(operation_id),
                    FOREIGN KEY(account_id) REFERENCES simulation_accounts(account_id),
                    CHECK(typeof(delta_units) = 'integer')
                );
                CREATE INDEX IF NOT EXISTS idx_sim_postings_operation ON simulation_postings(operation_id);
                CREATE INDEX IF NOT EXISTS idx_sim_postings_account ON simulation_postings(account_id);
            """)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    @staticmethod
    def _hash_request(source: str, destination: str, units: int, evidence: str) -> str:
        canonical = json.dumps({"source": source, "destination": destination, "units": units, "evidence": evidence}, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()

    def open_account(self, account_id: str) -> None:
        if not account_id:
            raise ValueError("account_id is required")
        with closing(self._connect()) as connection:
            connection.execute("INSERT OR IGNORE INTO simulation_accounts(account_id) VALUES (?)", (account_id,))

    def transfer(self, operation_id: str, source: str, destination: str, units: int, evidence: str) -> Dict[str, Any]:
        if not operation_id or not source or not destination or source == destination:
            raise ValueError("operation, distinct source, and destination are required")
        if isinstance(units, bool) or not isinstance(units, int) or units <= 0:
            raise ValueError("units must be a positive integer")
        if not evidence:
            raise ValueError("evidence is required")
        request_hash = self._hash_request(source, destination, units, evidence)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            prior = connection.execute("SELECT request_hash, result_json FROM simulation_operations WHERE operation_id=?", (operation_id,)).fetchone()
            if prior:
                if prior["request_hash"] != request_hash:
                    raise IdempotencyConflict("operation_id was already used for different economic intent")
                connection.execute("COMMIT")
                return json.loads(prior["result_json"])
            connection.execute("INSERT OR IGNORE INTO simulation_accounts(account_id) VALUES (?)", (source,))
            connection.execute("INSERT OR IGNORE INTO simulation_accounts(account_id) VALUES (?)", (destination,))
            if source in self.allow_negative:
                connection.execute("UPDATE simulation_accounts SET balance_units=balance_units-? WHERE account_id=?", (units, source))
            else:
                updated = connection.execute("UPDATE simulation_accounts SET balance_units=balance_units-? WHERE account_id=? AND balance_units>=?", (units, source, units))
                if updated.rowcount != 1:
                    raise InsufficientFunds(f"account {source} cannot fund {units} units")
            connection.execute("UPDATE simulation_accounts SET balance_units=balance_units+? WHERE account_id=?", (units, destination))
            result = {"operation_id": operation_id, "source": source, "destination": destination, "units": units, "evidence": evidence, "mode": "simulation", "spendable": False}
            connection.execute("INSERT INTO simulation_operations(operation_id, request_hash, result_json) VALUES (?, ?, ?)", (operation_id, request_hash, json.dumps(result, separators=(",", ":"))))
            connection.executemany("INSERT INTO simulation_postings(operation_id, account_id, delta_units, evidence) VALUES (?, ?, ?, ?)", [(operation_id, source, -units, evidence), (operation_id, destination, units, evidence)])
            connection.execute("COMMIT")
            return result
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    def balance(self, account_id: str) -> int:
        with closing(self._connect()) as connection:
            row = connection.execute("SELECT balance_units FROM simulation_accounts WHERE account_id=?", (account_id,)).fetchone()
            return int(row["balance_units"]) if row else 0

    def audit(self) -> Dict[str, Any]:
        with closing(self._connect()) as connection:
            account_total = connection.execute("SELECT COALESCE(SUM(balance_units), 0) AS total FROM simulation_accounts").fetchone()["total"]
            unbalanced = connection.execute("SELECT operation_id, SUM(delta_units) AS total FROM simulation_postings GROUP BY operation_id HAVING total != 0").fetchall()
            drift = connection.execute("""
                SELECT a.account_id, a.balance_units, COALESCE(SUM(p.delta_units), 0) AS posted
                FROM simulation_accounts a LEFT JOIN simulation_postings p ON p.account_id=a.account_id
                GROUP BY a.account_id HAVING a.balance_units != posted
            """).fetchall()
            return {"balanced": account_total == 0 and not unbalanced and not drift, "account_total": account_total, "unbalanced_operations": [row["operation_id"] for row in unbalanced], "drift_accounts": [row["account_id"] for row in drift]}
