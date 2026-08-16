import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from economy import ComputeSponsorshipStore, SettlementError, SettlementIdempotencyConflict
from economy.public_ledger import project_public_cu_ledger
from economy.settlement_service import SettlementService
from economy.provider_adapters import ProviderCapabilities, ProviderCapabilityError
from persistent_world import PersistentWorldStore


class SettlementServiceTests(unittest.TestCase):
    VALID_OWNER_SIGNATURE = "sha256:" + ("b" * 64)
    VALID_COMPLIANCE_MANIFEST = "sha256:" + ("c" * 64)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = ComputeSponsorshipStore(root / "settlement.sqlite3")
        self.world_store = PersistentWorldStore(root / "world.sqlite3")
        self.world = self.world_store.create_world(now_ms=1_000_000)
        self.world_id = self.world["world_id"]
        self.service = SettlementService(self.store, self.world_store, provider_registry={}, owner_subject="owner-uuid")
        self.claim_id = self._run_world_until_verified_calibration_claim()
        self.policy_id = self._create_allocation_policy("policy-1", version=1, cu_milli_per_funding_minor=1_000)["policy_id"]
        self.valid_allocation_evidence = {
            "owner_signature": self.VALID_OWNER_SIGNATURE,
            "compliance_manifest_hash": self.VALID_COMPLIANCE_MANIFEST,
            "funded_program_cap_minor": 1_000,
        }
        self.store.record_funding(
            "fund-policy", "owner-uuid", 1_000, "usd", "owner_capital",
            "sha256:" + ("a" * 64), 1_900,
        )
        self.store.activate_policy(
            "activate-1", "owner-uuid", self.policy_id, "allocation_active",
            self.valid_allocation_evidence, 2_000,
        )

    def tearDown(self):
        self.world_store.close()
        self.store.close()
        self.temp.cleanup()

    def _create_allocation_policy(self, operation_id, version, cu_milli_per_funding_minor):
        return self.store.create_policy(operation_id, "owner-uuid", {
            "policy_id": f"calibration-v{version}",
            "version": version,
            "effective_from_ms": 1_000,
            "effective_to_ms": None,
            "eligible_action_types": ["calibrate_measurement_tool"],
            "evidence_requirements": ["verified_causal_evidence"],
            "cu_milli_per_funding_minor": cu_milli_per_funding_minor,
            "min_claim_cu_milli": 1,
            "max_claim_cu_milli": 10_000,
            "program_cap_minor": 1_000,
            "period_cap_minor": 1_000,
            "period_ms": 1_000,
            "beneficiary_class": "eov_owner_development",
            "funding_source_class": "owner_capital",
            "funding_currency": "usd",
            "compliance_manifest_hash": self.VALID_COMPLIANCE_MANIFEST,
        }, 1_500)

    def _run_world_until_verified_calibration_claim(self, action_id="calibration-claim"):
        previous_claim_ids = {
            entry["entry_id"] for entry in project_public_cu_ledger(self.world_store.snapshot(self.world_id))["entries"]
        }
        self.world_store.apply_action(self.world_id, "calibrator-join", "calibrator", {"type": "join", "location": [8, 6]}, now_ms=1_000_001)
        snapshot = self.world_store.snapshot(self.world_id)
        state = snapshot["state"]
        state["players"]["calibrator"]["competency_records"]["measurement"] = {
            "demonstrated": 0.2, "provenance": ["fixture:verified-measurement:calibrator"],
        }
        state["npcs"]["mira"]["location"] = [8, 6]
        with self.world_store.transaction() as connection:
            connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(state), self.world_id))
        for suffix, action, now_ms in (
            ("propose", {"type": "shared_action", "operation": "propose", "shared_action_id": action_id, "action_type": "calibrate_measurement_tool", "intent": "restore trustworthy length measurement", "observations": ["marked measure drifted against the reference edge"]}, 1_000_010),
            ("accept", {"type": "shared_action", "operation": "accept", "shared_action_id": action_id}, 1_000_011),
            ("reserve", {"type": "shared_action", "operation": "reserve", "shared_action_id": action_id}, 1_000_012),
            ("execute", {"type": "shared_action", "operation": "execute", "shared_action_id": action_id, "samples": [{"reading": 1.0}, {"reading": 1.01}, {"reading": 1.0}]}, 1_000_013),
        ):
            self.world_store.apply_action(self.world_id, f"{action_id}-{suffix}", "calibrator", action, now_ms=now_ms)
        self.world_store.advance_due(now_ms=1_060_010, max_ticks=4)
        self.world_store.apply_action(self.world_id, f"{action_id}-verify", "mira", {"type": "shared_action", "operation": "verify", "shared_action_id": action_id}, now_ms=1_060_011)
        self.world_store.apply_action(self.world_id, f"{action_id}-commission", "mira", {"type": "shared_action", "operation": "commission", "shared_action_id": action_id}, now_ms=1_060_012)
        ledger = project_public_cu_ledger(self.world_store.snapshot(self.world_id))
        return next(entry["entry_id"] for entry in ledger["entries"] if entry["entry_id"] not in previous_claim_ids)

    def test_policy_quotes_with_integer_round_down_and_never_revalues_history(self):
        quote = self.service.propose_allocation("quote-1", self.world_id, self.policy_id, [self.claim_id], 2_100)
        self.assertEqual(4, quote["quoted_funding_minor"])
        self._create_allocation_policy("policy-2", version=2, cu_milli_per_funding_minor=500)
        persisted = self.store.get_allocation(quote["allocation_id"])
        self.assertEqual(4, persisted["quoted_funding_minor"])
        self.assertEqual(1_000, persisted["policy_snapshot"]["cu_milli_per_funding_minor"])

    def test_proposal_resolves_claims_server_side_and_rejects_unknown_or_reused_claims(self):
        with self.assertRaisesRegex(SettlementError, "not eligible"):
            self.service.propose_allocation("quote-unknown", self.world_id, self.policy_id, ["claim:unknown"], 2_100)
        allocation = self.service.propose_allocation("quote-1", self.world_id, self.policy_id, [self.claim_id], 2_100)
        self.assertEqual("proposed", allocation["state"])
        self.assertEqual("eov_owner_development", allocation["beneficiary_class"])
        with self.assertRaisesRegex(SettlementError, "already committed"):
            self.service.propose_allocation("quote-2", self.world_id, self.policy_id, [self.claim_id], 2_101)

    def test_lifecycle_wrappers_derive_the_configured_owner_subject(self):
        allocation = self.service.propose_allocation("quote-lifecycle", self.world_id, self.policy_id, [self.claim_id], 2_100)
        held = self.service.hold_allocation("hold-lifecycle", allocation["allocation_id"], 2_200)
        self.assertEqual("funding_held", held["state"])
        approved = self.service.approve_allocation(
            "approve-lifecycle", allocation["allocation_id"], "sha256:" + ("e" * 64), 9_000, 2_300,
        )
        self.assertEqual("owner_approved", approved["state"])
        cancelled = self.service.cancel_allocation(
            "cancel-lifecycle", allocation["allocation_id"], "provider unavailable", 2_400,
        )
        self.assertEqual("cancelled", cancelled["state"])

    def test_provider_lifecycle_replays_an_ambiguous_timeout_and_reconciles_below_hold(self):
        provider = _FakeCapableProvider(timeout_once=True)
        self.service.provider_registry = {"test-provider": provider}
        self._activate_settlement_policy()
        allocation = self.service.propose_allocation("provider-quote", self.world_id, self.policy_id, [self.claim_id], 2_100)
        self.service.hold_allocation("provider-hold", allocation["allocation_id"], 2_200)
        self.service.approve_allocation("provider-approval", allocation["allocation_id"], "sha256:" + ("d" * 64), 9_000, 2_300)
        with self.assertRaises(TimeoutError):
            self.service.submit_allocation("provider-submit-1", allocation["allocation_id"], "test-provider", 2_400)
        pending = self.store.get_allocation(allocation["allocation_id"])
        self.assertEqual("provider_pending", pending["state"])
        submitted = self.service.submit_allocation("provider-submit-2", allocation["allocation_id"], "test-provider", 2_401)
        self.assertEqual("provider_pending", submitted["state"])
        self.assertEqual(1, len(set(provider.operation_ids)))
        confirmed = self.service.record_provider_receipt("provider-receipt", allocation["allocation_id"], {
            "provider": "test-provider", "receipt_id": "receipt-1", "provider_transaction_id": "txn-1",
            "provider_operation_id": submitted["provider_operation_id"],
            "amount_minor": 4, "currency": "usd", "completed_at_ms": 2_402,
            "evidence_hash": "sha256:" + ("e" * 64), "human_completed": True,
        }, 2_403)
        self.assertEqual("provider_confirmed", confirmed["state"])
        with self.assertRaises(SettlementIdempotencyConflict):
            self.service.record_provider_receipt("provider-receipt-conflict", allocation["allocation_id"], {
                "provider": "test-provider", "receipt_id": "receipt-1", "provider_transaction_id": "txn-1",
                "provider_operation_id": submitted["provider_operation_id"],
                "amount_minor": 4, "currency": "usd", "completed_at_ms": 2_402,
                "evidence_hash": "sha256:" + ("f" * 64), "human_completed": True,
            }, 2_403)
        reconciled = self.service.reconcile_allocation("provider-reconcile", allocation["allocation_id"], {
            "data": [{"object": "organization.costs.result", "amount": {"value": "0.02", "currency": "usd"},
                      "start_time": 3, "end_time": 3,
                      "metadata": {"eov_provider_operation_id": submitted["provider_operation_id"]}}]
        }, 3_500)
        self.assertEqual("reconciled", reconciled["state"])
        self.assertEqual(2, self.store.funding_balance("expense:provider:test-provider"))
        self.assertEqual(998, self.store.funding_balance("reserve:available"))
        self.assertEqual(0, self.store.funding_balance(f"reserve:held:{allocation['allocation_id']}"))
        self.assertEqual(reconciled, self.service.reconcile_allocation("provider-reconcile", allocation["allocation_id"], {
            "data": [{"object": "organization.costs.result", "amount": {"value": "0.02", "currency": "usd"},
                      "start_time": 3, "end_time": 3,
                      "metadata": {"eov_provider_operation_id": submitted["provider_operation_id"]}}]
        }, 3_500))

    def test_provider_submission_rejects_expired_approval_and_above_hold_cost_is_reviewable(self):
        provider = _FakeCapableProvider()
        self.service.provider_registry = {"test-provider": provider}
        self._activate_settlement_policy()
        allocation = self.service.propose_allocation("cap-quote", self.world_id, self.policy_id, [self.claim_id], 2_100)
        self.service.hold_allocation("cap-hold", allocation["allocation_id"], 2_200)
        self.service.approve_allocation("cap-approval", allocation["allocation_id"], "sha256:" + ("f" * 64), 2_401, 2_300)
        with self.assertRaisesRegex(Exception, "expired"):
            self.service.submit_allocation("cap-expired", allocation["allocation_id"], "test-provider", 2_401)
        self.service.expire_due("cap-expire", 2_401)

        allocation = self.service.propose_allocation("above-quote", self.world_id, self.policy_id, [self.claim_id], 2_410)
        self.service.hold_allocation("above-hold", allocation["allocation_id"], 2_420)
        self.service.approve_allocation("above-approval", allocation["allocation_id"], "sha256:" + ("1" * 64), 9_000, 2_430)
        submitted = self.service.submit_allocation("above-submit", allocation["allocation_id"], "test-provider", 2_440)
        self.service.record_provider_receipt("above-receipt", allocation["allocation_id"], {
            "provider": "test-provider", "receipt_id": "receipt-above", "provider_transaction_id": "txn-above",
            "provider_operation_id": submitted["provider_operation_id"],
            "amount_minor": 4, "currency": "usd", "completed_at_ms": 2_441,
            "evidence_hash": "sha256:" + ("2" * 64), "human_completed": True,
        }, 2_442)
        exception = self.service.reconcile_allocation("above-reconcile", allocation["allocation_id"], {
            "data": [{"object": "organization.costs.result", "amount": {"value": "10.00", "currency": "usd"},
                      "start_time": 3, "end_time": 3,
                      "metadata": {"eov_provider_operation_id": submitted["provider_operation_id"]}}]
        }, 3_500)
        self.assertEqual("reconciliation_exception", exception["state"])
        self.assertEqual(4, self.store.funding_balance(f"reserve:held:{allocation['allocation_id']}"))
        self.assertEqual(0, self.store.funding_balance("expense:provider:test-provider"))

    def test_reconciliation_at_the_approved_hold_captures_without_a_release(self):
        self.service.provider_registry = {"test-provider": _FakeCapableProvider()}
        self._activate_settlement_policy()
        allocation = self.service.propose_allocation("exact-quote", self.world_id, self.policy_id, [self.claim_id], 2_100)
        self.service.hold_allocation("exact-hold", allocation["allocation_id"], 2_200)
        self.service.approve_allocation("exact-approval", allocation["allocation_id"], "sha256:" + ("3" * 64), 9_000, 2_300)
        submitted = self.service.submit_allocation("exact-submit", allocation["allocation_id"], "test-provider", 2_400)
        self.service.record_provider_receipt("exact-receipt", allocation["allocation_id"], {
            "provider": "test-provider", "receipt_id": "receipt-exact", "provider_transaction_id": "txn-exact",
            "provider_operation_id": submitted["provider_operation_id"],
            "amount_minor": 4, "currency": "usd", "completed_at_ms": 2_401,
            "evidence_hash": "sha256:" + ("4" * 64), "human_completed": True,
        }, 2_402)
        reconciled = self.service.reconcile_allocation("exact-reconcile", allocation["allocation_id"], {
            "data": [{"object": "organization.costs.result", "amount": {"value": "0.04", "currency": "usd"},
                      "start_time": 3, "end_time": 3,
                      "metadata": {"eov_provider_operation_id": submitted["provider_operation_id"]}}]
        }, 3_500)
        self.assertEqual("reconciled", reconciled["state"])
        self.assertEqual(996, self.store.funding_balance("reserve:available"))
        self.assertEqual(4, self.store.funding_balance("expense:provider:test-provider"))
        self.assertEqual(0, self.store.funding_balance(f"reserve:held:{allocation['allocation_id']}"))

    def test_receipts_bind_to_the_pending_operation_and_commit_external_identifiers(self):
        self.service.provider_registry = {"test-provider": _FakeCapableProvider()}
        self._activate_settlement_policy()
        first = self._pending_provider_allocation("receipt-first", self.claim_id, 2_100)
        second_claim = self._secondary_claim("receipt-second-claim")
        second = self._pending_provider_allocation("receipt-second", second_claim, 2_500)
        with self.assertRaisesRegex(SettlementError, "pending allocation"):
            self.service.record_provider_receipt("wrong-operation", first["allocation_id"], self._receipt(
                first, "receipt-wrong", "txn-wrong", provider_operation_id=second["provider_operation_id"],
            ), 2_450)
        self.service.record_provider_receipt("receipt-first", first["allocation_id"], self._receipt(first, "receipt-first", "shared-txn"), 2_450)
        with self.assertRaises(SettlementIdempotencyConflict):
            self.service.record_provider_receipt("receipt-reused-transaction", second["allocation_id"], self._receipt(second, "receipt-second", "shared-txn"), 2_850)
        connection = self.store._connect()
        try:
            retained = connection.execute("SELECT receipt_json FROM settlement_provider_receipts").fetchone()["receipt_json"]
        finally:
            self.store._release(connection)
        self.assertNotIn("receipt-first", retained)
        self.assertNotIn("shared-txn", retained)

    def test_duplicate_cost_records_fail_without_capture_and_cannot_cross_allocations(self):
        self.service.provider_registry = {"test-provider": _FakeCapableProvider()}
        self._activate_settlement_policy()
        first = self._confirmed_provider_allocation("cost-first", self.claim_id, 2_100)
        duplicate = self._cost(first, "cost-duplicate")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.service.reconcile_allocation("duplicate-list", first["allocation_id"], {"data": [duplicate, duplicate]}, 3_500)
        self.assertEqual("provider_confirmed", self.store.get_allocation(first["allocation_id"])["state"])
        self.service.reconcile_allocation("cost-first-reconcile", first["allocation_id"], {"data": [duplicate]}, 3_500)

        second_claim = self._secondary_claim("cost-second-claim")
        second = self._confirmed_provider_allocation("cost-second", second_claim, 4_100)
        reused = self._cost(second, "cost-duplicate", seconds=5)
        with self.assertRaises(SettlementIdempotencyConflict):
            self.service.reconcile_allocation("cost-reused", second["allocation_id"], {"data": [reused]}, 5_500)
        self.assertEqual("provider_confirmed", self.store.get_allocation(second["allocation_id"])["state"])

    def test_cost_capture_uses_official_effective_time_but_releases_only_when_recorded(self):
        self.service.provider_registry = {"test-provider": _FakeCapableProvider()}
        self._activate_settlement_policy()
        allocation = self._confirmed_provider_allocation("bitemporal", self.claim_id, 2_100)
        self.service.reconcile_allocation("bitemporal-reconcile", allocation["allocation_id"], {
            "data": [self._cost(allocation, "bitemporal-cost")]
        }, 3_500)
        persisted = self.store.get_allocation(allocation["allocation_id"])
        self.assertEqual(3_000, persisted["actual_cost_effective_at_ms"])
        self.assertEqual(3_500, persisted["reconciled_at_ms"])
        connection = self.store._connect()
        try:
            postings = connection.execute(
                "SELECT account_id, delta_minor, occurred_at_ms FROM settlement_postings WHERE operation_id = ? ORDER BY sequence",
                ("bitemporal-reconcile",),
            ).fetchall()
        finally:
            self.store._release(connection)
        self.assertEqual(
            [(f"reserve:held:{allocation['allocation_id']}:usd", -2, 3_000),
             ("expense:provider:test-provider:usd", 2, 3_000),
             (f"reserve:held:{allocation['allocation_id']}:usd", -2, 3_500),
             ("reserve:available:usd", 2, 3_500)],
            [(row["account_id"], row["delta_minor"], row["occurred_at_ms"]) for row in postings],
        )

    def test_legacy_receipt_table_migrates_to_committed_provider_wide_identifiers(self):
        database_path = Path(self.temp.name) / "legacy-receipts.sqlite3"
        legacy = ComputeSponsorshipStore(database_path)
        legacy.close()
        connection = sqlite3.connect(database_path)
        try:
            connection.execute("DROP TABLE settlement_provider_receipts")
            connection.execute(
                """CREATE TABLE settlement_provider_receipts (
                    provider TEXT NOT NULL, receipt_id TEXT NOT NULL, allocation_id TEXT NOT NULL,
                    receipt_json TEXT NOT NULL, receipt_hash TEXT NOT NULL, recorded_at_ms INTEGER NOT NULL,
                    PRIMARY KEY(provider, receipt_id)
                )"""
            )
            connection.commit()
        finally:
            connection.close()
        migrated = ComputeSponsorshipStore(database_path)
        try:
            connection = migrated._connect()
            try:
                columns = {row["name"] for row in connection.execute("PRAGMA table_info(settlement_provider_receipts)")}
                indexes = connection.execute("PRAGMA index_list(settlement_provider_receipts)").fetchall()
            finally:
                migrated._release(connection)
            self.assertIn("receipt_id_commitment", columns)
            self.assertIn("provider_transaction_id_commitment", columns)
            self.assertGreaterEqual(len(indexes), 2)
        finally:
            migrated.close()

    def _pending_provider_allocation(self, prefix, claim_id, now_ms):
        if isinstance(claim_id, str):
            allocation = self.service.propose_allocation(f"{prefix}-quote", self.world_id, self.policy_id, [claim_id], now_ms)
        else:
            allocation = self.store.create_allocation(
                f"{prefix}-quote", "owner-uuid", self.world_id, self.policy_id, [claim_id], now_ms,
            )
        self.service.hold_allocation(f"{prefix}-hold", allocation["allocation_id"], now_ms + 10)
        self.service.approve_allocation(f"{prefix}-approval", allocation["allocation_id"], "sha256:" + ("5" * 64), 9_000, now_ms + 20)
        return self.service.submit_allocation(f"{prefix}-submit", allocation["allocation_id"], "test-provider", now_ms + 30)

    def _confirmed_provider_allocation(self, prefix, claim_id, now_ms):
        submitted = self._pending_provider_allocation(prefix, claim_id, now_ms)
        self.service.record_provider_receipt(f"{prefix}-receipt", submitted["allocation_id"], self._receipt(submitted, f"{prefix}-receipt", f"{prefix}-transaction", completed_at_ms=now_ms + 35), now_ms + 40)
        return submitted

    @staticmethod
    def _receipt(submitted, receipt_id, transaction_id, provider_operation_id=None, completed_at_ms=2_401):
        return {
            "provider": "test-provider", "receipt_id": receipt_id, "provider_transaction_id": transaction_id,
            "provider_operation_id": provider_operation_id or submitted["provider_operation_id"],
            "amount_minor": 4, "currency": "usd", "completed_at_ms": completed_at_ms,
            "evidence_hash": "sha256:" + ("6" * 64), "human_completed": True,
        }

    @staticmethod
    def _cost(submitted, record_id, seconds=3):
        return {"id": record_id, "object": "organization.costs.result", "amount": {"value": "0.02", "currency": "usd"},
                "start_time": seconds, "end_time": seconds,
                "metadata": {"eov_provider_operation_id": submitted["provider_operation_id"]}}

    @staticmethod
    def _secondary_claim(claim_id):
        return {
            "entry_id": claim_id, "status": "verified_provisional", "spendable": False,
            "unit": "CU-placeholder", "action_type": "calibrate_measurement_tool", "amount_milli": 4_000,
            "evidence_hash": "verified-event-hash", "commission_hash": "commissioned-event-hash",
            "contributor_ref": "contributor:secondary", "verifier_ref": "verifier:secondary",
        }

    def _activate_settlement_policy(self):
        self.store.activate_policy("activate-settlement", "owner-uuid", self.policy_id, "settlement_active", {
            "provider_capability_hash": "sha256:" + ("a" * 64),
        }, 2_050)


class _FakeCapableProvider:
    def __init__(self, timeout_once=False):
        self.timeout_once = timeout_once
        self.operation_ids = []

    def capabilities(self):
        return ProviderCapabilities("test-provider", purchase=True, credit_transfer=False, usage_read=True, cost_read=True)

    def submit(self, allocation, provider_operation_id):
        self.operation_ids.append(provider_operation_id)
        if self.timeout_once:
            self.timeout_once = False
            raise TimeoutError("provider response is ambiguous")
        return {"status": "pending", "provider_operation_id": provider_operation_id}


if __name__ == "__main__":
    unittest.main()
