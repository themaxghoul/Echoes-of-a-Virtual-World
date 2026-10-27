import json
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from economy import (
    ComputeSponsorshipStore,
    SettlementError,
    SettlementIdempotencyConflict,
    SettlementInsufficientFunds,
    SettlementTransitionError,
)


class ComputeSponsorshipFundingTests(unittest.TestCase):
    VALID_EVIDENCE_HASH = "sha256:" + ("a" * 64)
    VALID_OWNER_SIGNATURE = "sha256:" + ("b" * 64)
    VALID_COMPLIANCE_MANIFEST = "sha256:" + ("c" * 64)
    VALID_PROVIDER_CAPABILITY = "sha256:" + ("d" * 64)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = ComputeSponsorshipStore(Path(self.temp.name) / "settlement.sqlite3")

    def tearDown(self):
        self.temp.cleanup()

    def test_receipted_external_funding_is_balanced_and_cu_cannot_fund_reserve(self):
        result = self.store.record_funding(
            "fund-1", "owner-uuid", 2_500, "usd", "owner_capital",
            self.VALID_EVIDENCE_HASH, 1_000,
        )
        self.assertEqual(2_500, result["amount_minor"])
        self.assertEqual(2_500, self.store.funding_balance())
        self.assertTrue(self.store.audit_funding()["balanced"])
        with self.assertRaisesRegex(ValueError, "CU cannot fund"):
            self.store.record_funding("fund-cu", "owner-uuid", 10, "usd", "CU-placeholder", self.VALID_EVIDENCE_HASH, 1_001)

    def test_funding_receipt_replay_is_exact_and_conflicting_reuse_fails(self):
        first = self.store.record_funding("fund-1", "owner-uuid", 500, "usd", "grant", self.VALID_EVIDENCE_HASH, 1_000)
        self.assertEqual(first, self.store.record_funding("fund-1", "owner-uuid", 500, "usd", "grant", self.VALID_EVIDENCE_HASH, 1_000))
        with self.assertRaises(SettlementIdempotencyConflict):
            self.store.record_funding("fund-1", "owner-uuid", 600, "usd", "grant", self.VALID_EVIDENCE_HASH, 1_000)

    def test_in_memory_store_keeps_schema_for_its_lifetime(self):
        store = ComputeSponsorshipStore(":memory:")
        result = store.record_funding(
            "memory-1", "owner-uuid", 125, "usd", "grant",
            self.VALID_EVIDENCE_HASH, 2_000,
        )
        self.assertEqual(125, result["amount_minor"])
        self.assertEqual(125, store.funding_balance())
        self.assertTrue(store.audit_funding()["balanced"])
        store.close()

    def test_task3_approved_allocation_schema_rebuilds_and_can_enter_provider_pending(self):
        database_path = Path(self.temp.name) / "task3-approved.sqlite3"
        self._write_task3_approved_fixture(database_path)
        migrated = ComputeSponsorshipStore(database_path)
        try:
            transitioned = migrated.begin_provider_submission(
                "legacy-provider-submit", "allocation:legacy-task3", "owner-uuid", "test-provider",
                self.VALID_PROVIDER_CAPABILITY, 2_500,
            )
            self.assertEqual("provider_pending", transitioned["state"])
            connection = migrated._connect()
            try:
                allocation_sql = connection.execute(
                    "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'settlement_allocations'"
                ).fetchone()["sql"]
                index_names = {row["name"] for row in connection.execute("PRAGMA index_list(settlement_allocations)")}
                self.assertEqual(1, connection.execute("SELECT COUNT(*) FROM settlement_allocations").fetchone()[0])
            finally:
                migrated._release(connection)
            self.assertIn("provider_pending', 'provider_confirmed'", allocation_sql)
            self.assertIn("idx_legacy_alloc_owner", index_names)
        finally:
            migrated.close()

    def test_duplicate_legacy_provider_transactions_fail_before_receipt_table_is_replaced(self):
        database_path = Path(self.temp.name) / "legacy-duplicate-receipts.sqlite3"
        prepared = ComputeSponsorshipStore(database_path)
        prepared.close()
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
            for receipt_id in ("legacy-receipt-1", "legacy-receipt-2"):
                connection.execute(
                    "INSERT INTO settlement_provider_receipts VALUES (?, ?, ?, ?, ?, ?)",
                    ("test-provider", receipt_id, "allocation:legacy", json.dumps({"provider_transaction_id": "same-transaction"}), self.VALID_EVIDENCE_HASH, 2_400),
                )
            connection.commit()
        finally:
            connection.close()
        with self.assertRaisesRegex(SettlementTransitionError, "duplicate legacy provider transaction"):
            ComputeSponsorshipStore(database_path)
        connection = sqlite3.connect(database_path)
        try:
            columns = {row[1] for row in connection.execute("PRAGMA table_info(settlement_provider_receipts)")}
            count = connection.execute("SELECT COUNT(*) FROM settlement_provider_receipts").fetchone()[0]
        finally:
            connection.close()
        self.assertIn("receipt_id", columns)
        self.assertNotIn("receipt_id_commitment", columns)
        self.assertEqual(2, count)

    def test_evidence_hash_must_be_canonical_lowercase_sha256(self):
        invalid_hashes = (
            "sha256:" + ("a" * 63),
            "sha256:" + ("A" * 64),
            "sha512:" + ("a" * 64),
            "a" * 64,
        )
        for index, evidence_hash in enumerate(invalid_hashes):
            with self.subTest(evidence_hash=evidence_hash):
                with self.assertRaisesRegex(ValueError, "evidence_hash must be sha256 followed by 64 lowercase hexadecimal characters"):
                    self.store.record_funding(
                        "invalid-" + str(index), "owner-uuid", 1,
                        "usd", "grant", evidence_hash, 3_000,
                    )

    def test_policy_lifecycle_requires_signed_compliant_funded_policy_evidence(self):
        policy = {
            "policy_id": "calibration-v1",
            "version": 1,
            "effective_from_ms": 1_000,
            "effective_to_ms": None,
            "eligible_action_types": ["calibrate_measurement_tool"],
            "evidence_requirements": ["verified_causal_evidence"],
            "cu_milli_per_funding_minor": 1_000,
            "min_claim_cu_milli": 1,
            "max_claim_cu_milli": 10_000,
            "program_cap_minor": 1_000,
            "period_cap_minor": 1_000,
            "period_ms": 1_000,
            "beneficiary_class": "eov_owner_development",
            "funding_source_class": "owner_capital",
            "funding_currency": "usd",
            "compliance_manifest_hash": self.VALID_COMPLIANCE_MANIFEST,
        }
        created = self.store.create_policy("policy-create-1", "owner-uuid", policy, 1_500)
        policy["cu_milli_per_funding_minor"] = 500
        self.assertEqual(1_000, self.store.get_policy(created["policy_id"])["policy"]["cu_milli_per_funding_minor"])
        self.store.record_funding("fund-policy-1", "owner-uuid", 1_000, "usd", "owner_capital", self.VALID_EVIDENCE_HASH, 1_900)

        allocation_evidence = {
            "owner_signature": self.VALID_OWNER_SIGNATURE,
            "compliance_manifest_hash": self.VALID_COMPLIANCE_MANIFEST,
            "funded_program_cap_minor": 1_000,
        }
        activated = self.store.activate_policy(
            "policy-activate-1", "owner-uuid", created["policy_id"],
            "allocation_active", allocation_evidence, 2_000,
        )
        self.assertEqual("allocation_active", activated["state"])
        with self.assertRaisesRegex(SettlementTransitionError, "provider capability"):
            self.store.activate_policy(
                "policy-activate-2", "owner-uuid", created["policy_id"],
                "settlement_active", allocation_evidence, 2_001,
            )
        settlement_evidence = {
            **allocation_evidence,
            "provider_capability_hash": self.VALID_PROVIDER_CAPABILITY,
        }
        self.assertEqual(
            "settlement_active",
            self.store.activate_policy(
                "policy-activate-3", "owner-uuid", created["policy_id"],
                "settlement_active", settlement_evidence, 2_002,
            )["state"],
        )

    def test_allocation_activation_requires_receipted_same_currency_reserve(self):
        policy = self._policy("reserve-backed-v1", 1, program_cap_minor=500, period_cap_minor=500)
        created = self.store.create_policy("policy-reserve-create", "owner-uuid", policy, 1_500)
        evidence = {
            "owner_signature": self.VALID_OWNER_SIGNATURE,
            "compliance_manifest_hash": self.VALID_COMPLIANCE_MANIFEST,
            "funded_program_cap_minor": 500,
        }
        with self.assertRaises(SettlementInsufficientFunds):
            self.store.activate_policy("policy-reserve-zero", "owner-uuid", created["policy_id"], "allocation_active", evidence, 2_000)
        self.store.record_funding("fund-eur", "owner-uuid", 500, "eur", "owner_capital", self.VALID_EVIDENCE_HASH, 2_001)
        with self.assertRaises(SettlementInsufficientFunds):
            self.store.activate_policy("policy-reserve-wrong-currency", "owner-uuid", created["policy_id"], "allocation_active", evidence, 2_002)
        self.store.record_funding("fund-usd", "owner-uuid", 500, "usd", "owner_capital", self.VALID_EVIDENCE_HASH, 2_003)
        activated = self.store.activate_policy("policy-reserve-backed", "owner-uuid", created["policy_id"], "allocation_active", evidence, 2_004)
        self.assertEqual("usd", activated["reserve_snapshot"]["currency"])
        self.assertEqual(500, activated["reserve_snapshot"]["available_balance_minor"])
        self.assertEqual(["fund-usd"], [item["operation_id"] for item in activated["reserve_snapshot"]["receipts"]])

    def test_activation_reconstructs_reserve_as_of_its_timestamp_and_replays_exactly(self):
        policy = self._policy("as-of-reserve-v1", 1, program_cap_minor=500, period_cap_minor=500)
        created = self.store.create_policy("policy-as-of-create", "owner-uuid", policy, 1_500)
        evidence = {
            "owner_signature": self.VALID_OWNER_SIGNATURE,
            "compliance_manifest_hash": self.VALID_COMPLIANCE_MANIFEST,
        }
        self.store.record_funding("fund-future", "owner-uuid", 500, "usd", "owner_capital", self.VALID_EVIDENCE_HASH, 3_000)
        with self.assertRaises(SettlementInsufficientFunds):
            self.store.activate_policy("policy-as-of-too-early", "owner-uuid", created["policy_id"], "allocation_active", evidence, 2_000)
        self.store.record_funding("fund-early", "owner-uuid", 500, "usd", "owner_capital", self.VALID_EVIDENCE_HASH, 1_900)
        activated = self.store.activate_policy("policy-as-of-active", "owner-uuid", created["policy_id"], "allocation_active", evidence, 2_000)
        self.assertEqual(500, activated["reserve_snapshot"]["available_balance_minor"])
        self.assertEqual(["fund-early"], [item["operation_id"] for item in activated["reserve_snapshot"]["receipts"]])
        self.assertEqual(
            activated,
            self.store.activate_policy("policy-as-of-active", "owner-uuid", created["policy_id"], "allocation_active", evidence, 2_000),
        )

    def test_activation_time_must_follow_policy_approval_and_prior_transition(self):
        policy = self._policy("ordered-activation-v1", 1)
        policy["effective_from_ms"] = 2_000
        created = self.store.create_policy("policy-ordered-create", "owner-uuid", policy, 2_100)
        self.store.record_funding("fund-ordered", "owner-uuid", 1_000, "usd", "owner_capital", self.VALID_EVIDENCE_HASH, 2_000)
        evidence = {
            "owner_signature": self.VALID_OWNER_SIGNATURE,
            "compliance_manifest_hash": self.VALID_COMPLIANCE_MANIFEST,
        }
        with self.assertRaisesRegex(SettlementTransitionError, "approval"):
            self.store.activate_policy("policy-before-approval", "owner-uuid", created["policy_id"], "allocation_active", evidence, 2_050)
        self.store.activate_policy("policy-ordered-active", "owner-uuid", created["policy_id"], "allocation_active", evidence, 2_200)
        with self.assertRaisesRegex(SettlementTransitionError, "chronology"):
            self.store.activate_policy("policy-out-of-order-settlement", "owner-uuid", created["policy_id"], "settlement_active", {
                "provider_capability_hash": self.VALID_PROVIDER_CAPABILITY,
            }, 2_100)

    def test_legacy_active_policy_without_new_authorization_fields_fails_closed_for_quotes(self):
        policy = self._policy("legacy-active-v1", 1)
        created = self.store.create_policy("policy-legacy-create", "owner-uuid", policy, 1_000)
        self.store.record_funding("fund-legacy", "owner-uuid", 1_000, "usd", "owner_capital", self.VALID_EVIDENCE_HASH, 1_100)
        self.store.activate_policy("policy-legacy-active", "owner-uuid", created["policy_id"], "allocation_active", {
            "owner_signature": self.VALID_OWNER_SIGNATURE,
            "compliance_manifest_hash": self.VALID_COMPLIANCE_MANIFEST,
        }, 1_200)
        legacy_policy = self.store.get_policy(created["policy_id"])["policy"]
        legacy_policy.pop("funding_currency")
        legacy_policy.pop("period_ms")
        connection = sqlite3.connect(self.store.database_path)
        try:
            connection.execute(
                "UPDATE settlement_policies SET policy_json = ? WHERE policy_id = ?",
                (json.dumps(legacy_policy, sort_keys=True, separators=(",", ":")), created["policy_id"]),
            )
            connection.commit()
        finally:
            connection.close()
        with self.assertRaisesRegex(SettlementTransitionError, "new policy version"):
            self.store.create_allocation("legacy-quote", "owner-uuid", "world-1", created["policy_id"], [self._public_claim("claim:legacy")], 2_100)

    def test_policy_rejects_unknown_evidence_requirements(self):
        policy = self._policy("unknown-evidence-v1", 1)
        policy["evidence_requirements"] = ["invented_claim_attestation"]
        with self.assertRaisesRegex(ValueError, "unsupported evidence requirement"):
            self.store.create_policy("policy-unknown-evidence", "owner-uuid", policy, 1_500)

    def test_settlement_activation_appends_evidence_without_replacing_prior_facts(self):
        policy = self._policy("evidence-history-v1", 1)
        created = self.store.create_policy("policy-evidence-create", "owner-uuid", policy, 1_500)
        self.store.record_funding("fund-evidence", "owner-uuid", 1_000, "usd", "owner_capital", self.VALID_EVIDENCE_HASH, 1_900)
        allocation_evidence = {
            "owner_signature": self.VALID_OWNER_SIGNATURE,
            "compliance_manifest_hash": self.VALID_COMPLIANCE_MANIFEST,
            "funded_program_cap_minor": 1_000,
        }
        self.store.activate_policy("policy-evidence-allocation", "owner-uuid", created["policy_id"], "allocation_active", allocation_evidence, 2_000)
        provider_evidence = {
            "owner_signature": "sha256:" + ("e" * 64),
            "provider_capability_hash": self.VALID_PROVIDER_CAPABILITY,
        }
        self.store.activate_policy("policy-evidence-settlement", "owner-uuid", created["policy_id"], "settlement_active", provider_evidence, 2_001)
        transitions = self.store.get_policy(created["policy_id"])["activation_events"]
        self.assertEqual(self.VALID_OWNER_SIGNATURE, transitions[0]["evidence"]["owner_signature"])
        self.assertNotIn("owner_signature", transitions[1]["evidence"])
        self.assertEqual(self.VALID_PROVIDER_CAPABILITY, transitions[1]["evidence"]["provider_capability_hash"])

    def test_period_cap_applies_within_a_deterministic_policy_period(self):
        policy = self._policy("period-cap-v1", 1, program_cap_minor=10, period_cap_minor=2)
        created = self.store.create_policy("policy-period-create", "owner-uuid", policy, 1_000)
        self.store.record_funding("fund-period", "owner-uuid", 10, "usd", "owner_capital", self.VALID_EVIDENCE_HASH, 1_100)
        self.store.activate_policy("policy-period-active", "owner-uuid", created["policy_id"], "allocation_active", {
            "owner_signature": self.VALID_OWNER_SIGNATURE,
            "compliance_manifest_hash": self.VALID_COMPLIANCE_MANIFEST,
            "funded_program_cap_minor": 10,
        }, 1_200)
        self.store.create_allocation("period-one", "owner-uuid", "world-1", created["policy_id"], [self._public_claim("claim:period-one")], 2_100)
        with self.assertRaisesRegex(SettlementError, "period cap"):
            self.store.create_allocation("period-two", "owner-uuid", "world-1", created["policy_id"], [self._public_claim("claim:period-two")], 2_200)
        later = self.store.create_allocation("period-three", "owner-uuid", "world-1", created["policy_id"], [self._public_claim("claim:period-three")], 3_100)
        self.assertEqual(3_000, later["period_start_ms"])

    def test_independent_verifier_requirement_rejects_unverifiable_public_claim(self):
        policy = self._policy("independent-verifier-v1", 1)
        policy["evidence_requirements"] = ["independent_verifier"]
        created = self.store.create_policy("policy-independent-create", "owner-uuid", policy, 1_000)
        self.store.record_funding("fund-independent", "owner-uuid", 1_000, "usd", "owner_capital", self.VALID_EVIDENCE_HASH, 1_100)
        self.store.activate_policy("policy-independent-active", "owner-uuid", created["policy_id"], "allocation_active", {
            "owner_signature": self.VALID_OWNER_SIGNATURE,
            "compliance_manifest_hash": self.VALID_COMPLIANCE_MANIFEST,
            "funded_program_cap_minor": 1_000,
        }, 1_200)
        claim = self._public_claim("claim:not-independent")
        claim["verifier_ref"] = claim["contributor_ref"]
        with self.assertRaisesRegex(SettlementError, "evidence requirements"):
            self.store.create_allocation("independent-quote", "owner-uuid", "world-1", created["policy_id"], [claim], 2_100)

    def test_hold_approval_and_cancel_conserve_funds_and_are_exactly_replayable(self):
        allocation = self._proposed_allocation("lifecycle-quote", quoted_funding_minor=200)

        held = self.store.hold_allocation("hold-1", allocation["allocation_id"], "owner-uuid", 2_200)
        self.assertEqual("funding_held", held["state"])
        self.assertEqual(800, self.store.funding_balance("reserve:available"))
        self.assertEqual(200, self.store.funding_balance(f"reserve:held:{allocation['allocation_id']}"))
        self.assertEqual(held, self.store.hold_allocation("hold-1", allocation["allocation_id"], "owner-uuid", 2_200))
        with self.assertRaises(SettlementIdempotencyConflict):
            self.store.hold_allocation("hold-1", allocation["allocation_id"], "owner-uuid", 2_201)

        approval_hash = "sha256:" + ("e" * 64)
        approved = self.store.approve_allocation(
            "approve-1", allocation["allocation_id"], "owner-uuid", approval_hash, 9_000, 2_300,
        )
        self.assertEqual("owner_approved", approved["state"])
        self.assertEqual(approval_hash, approved["approval_hash"])
        self.assertEqual(
            approved,
            self.store.approve_allocation(
                "approve-1", allocation["allocation_id"], "owner-uuid", approval_hash, 9_000, 2_300,
            ),
        )
        cancelled = self.store.cancel_allocation(
            "cancel-1", allocation["allocation_id"], "owner-uuid", "provider unavailable", 2_400,
        )
        self.assertEqual("cancelled", cancelled["state"])
        self.assertEqual(1_000, self.store.funding_balance("reserve:available"))
        self.assertEqual(0, self.store.funding_balance(f"reserve:held:{allocation['allocation_id']}"))
        self.assertTrue(self.store.audit_funding()["balanced"])
        self.assertEqual(
            cancelled,
            self.store.cancel_allocation(
                "cancel-1", allocation["allocation_id"], "owner-uuid", "provider unavailable", 2_400,
            ),
        )
        self.assertEqual(
            ["allocation_held", "owner_approved", "allocation_cancelled"],
            [event["event_type"] for event in self.store.get_allocation(allocation["allocation_id"])["events"]],
        )

    def test_hold_rejects_insufficient_shared_reserve_without_partial_postings(self):
        self.store.record_funding("shared-fund", "owner-uuid", 1_000, "usd", "owner_capital", self.VALID_EVIDENCE_HASH, 1_900)
        first = self._proposed_allocation("first-quote", quoted_funding_minor=600, fund_reserve=False, version=1)
        second = self._proposed_allocation("second-quote", quoted_funding_minor=600, fund_reserve=False, version=2)
        self.store.hold_allocation("first-hold", first["allocation_id"], "owner-uuid", 2_200)

        with self.assertRaises(SettlementInsufficientFunds):
            self.store.hold_allocation("second-hold", second["allocation_id"], "owner-uuid", 2_201)

        self.assertEqual("proposed", self.store.get_allocation(second["allocation_id"])["state"])
        self.assertEqual(400, self.store.funding_balance("reserve:available"))
        self.assertEqual(0, self.store.funding_balance(f"reserve:held:{second['allocation_id']}"))
        self.assertTrue(self.store.audit_funding()["balanced"])

    def test_hold_uses_only_the_allocation_policy_currency(self):
        self.store.record_funding("eur-fund", "owner-uuid", 1_000, "eur", "owner_capital", self.VALID_EVIDENCE_HASH, 1_900)
        self.store.record_funding("usd-fund", "owner-uuid", 200, "usd", "owner_capital", self.VALID_EVIDENCE_HASH, 1_900)
        allocation = self._proposed_allocation(
            "currency-quote", quoted_funding_minor=200, fund_reserve=False, version=1,
        )

        self.store.hold_allocation("currency-hold", allocation["allocation_id"], "owner-uuid", 2_200)

        self.assertEqual(0, self.store.funding_balance("reserve:available", "usd"))
        self.assertEqual(200, self.store.funding_balance(f"reserve:held:{allocation['allocation_id']}", "usd"))
        self.assertEqual(1_000, self.store.funding_balance("reserve:available", "eur"))

    def test_owner_approval_validates_hash_expiry_owner_and_transition(self):
        allocation = self._proposed_allocation("approval-quote", quoted_funding_minor=200)
        with self.assertRaisesRegex(SettlementTransitionError, "owner subject"):
            self.store.hold_allocation("wrong-owner", allocation["allocation_id"], "not-owner", 2_200)
        with self.assertRaisesRegex(SettlementTransitionError, "transition"):
            self.store.approve_allocation(
                "approve-proposed", allocation["allocation_id"], "owner-uuid", self.VALID_EVIDENCE_HASH, 9_000, 2_200,
            )
        self.store.hold_allocation("approval-hold", allocation["allocation_id"], "owner-uuid", 2_200)
        with self.assertRaisesRegex(ValueError, "approval_hash"):
            self.store.approve_allocation("bad-hash", allocation["allocation_id"], "owner-uuid", "sha256:approval", 9_000, 2_201)
        with self.assertRaisesRegex(ValueError, "expires_at_ms"):
            self.store.approve_allocation(
                "bad-expiry", allocation["allocation_id"], "owner-uuid", self.VALID_EVIDENCE_HASH, 2_201, 2_201,
            )
        approved = self.store.approve_allocation(
            "approve-ok", allocation["allocation_id"], "owner-uuid", self.VALID_EVIDENCE_HASH, 9_000, 2_202,
        )
        with self.assertRaisesRegex(SettlementTransitionError, "transition"):
            self.store.hold_allocation("reversed-hold", allocation["allocation_id"], "owner-uuid", 2_203)
        self.assertEqual("owner_approved", approved["state"])

    def test_cancellation_cannot_reverse_hold_or_approval_chronology(self):
        allocation = self._proposed_allocation("cancel-chronology", quoted_funding_minor=200)
        self.store.hold_allocation("cancel-chronology-hold", allocation["allocation_id"], "owner-uuid", 2_200)
        self.store.approve_allocation(
            "cancel-chronology-approve", allocation["allocation_id"], "owner-uuid", self.VALID_EVIDENCE_HASH, 2_500, 2_300,
        )

        with self.assertRaisesRegex(SettlementTransitionError, "chronology"):
            self.store.cancel_allocation("cancel-before-approval", allocation["allocation_id"], "owner-uuid", "late decision", 2_250)
        with self.assertRaisesRegex(SettlementTransitionError, "expired"):
            self.store.cancel_allocation("cancel-after-expiry", allocation["allocation_id"], "owner-uuid", "late decision", 2_500)

        cancelled = self.store.cancel_allocation(
            "cancel-in-window", allocation["allocation_id"], "owner-uuid", "provider unavailable", 2_400,
        )
        self.assertEqual("cancelled", cancelled["state"])

    def test_hold_cannot_spend_a_future_dated_reserve_receipt(self):
        self.store.record_funding("temporal-fund", "owner-uuid", 200, "usd", "owner_capital", self.VALID_EVIDENCE_HASH, 1_900)
        first = self._proposed_allocation("temporal-first", quoted_funding_minor=200, fund_reserve=False, version=1)
        second = self._proposed_allocation("temporal-second", quoted_funding_minor=200, fund_reserve=False, version=2)
        self.store.hold_allocation("temporal-first-hold", first["allocation_id"], "owner-uuid", 2_200)
        self.store.record_funding("temporal-future-fund", "owner-uuid", 200, "usd", "owner_capital", self.VALID_EVIDENCE_HASH, 3_000)

        with self.assertRaises(SettlementInsufficientFunds):
            self.store.hold_allocation("temporal-second-hold", second["allocation_id"], "owner-uuid", 2_300)

        self.assertEqual("proposed", self.store.get_allocation(second["allocation_id"])["state"])

    def test_expiry_releases_claims_once_and_reserve_as_of_respects_hold_and_release(self):
        claim = self._public_claim("claim:expires")
        claim["amount_milli"] = 200
        allocation = self._proposed_allocation(
            "expiry-quote", quoted_funding_minor=200, claim=claim, program_cap_minor=400,
        )
        self.store.hold_allocation("expiry-hold", allocation["allocation_id"], "owner-uuid", 2_200)
        self.store.approve_allocation(
            "expiry-approve", allocation["allocation_id"], "owner-uuid", self.VALID_EVIDENCE_HASH, 2_300, 2_201,
        )
        expired = self.store.expire_due("expiry-sweep", 2_300)
        self.assertEqual(["expired"], [item["state"] for item in expired])
        self.assertEqual(1_000, self.store.funding_balance("reserve:available"))
        self.assertEqual(expired, self.store.expire_due("expiry-sweep", 2_300))
        with self.assertRaises(SettlementIdempotencyConflict):
            self.store.expire_due("expiry-sweep", 2_301)
        reallocated = self.store.create_allocation(
            "expiry-requote", "owner-uuid", "world-1", allocation["policy_id"], [claim], 2_301,
        )
        self.assertEqual("proposed", reallocated["state"])

        policy = self.store.get_policy(allocation["policy_id"])["policy"]
        connection = self.store._connect()
        try:
            held_snapshot = self.store._reserve_snapshot(connection, "owner-uuid", policy, 2_250)
            released_snapshot = self.store._reserve_snapshot(connection, "owner-uuid", policy, 2_300)
        finally:
            self.store._release(connection)
        self.assertEqual(800, held_snapshot["available_balance_minor"])
        self.assertEqual(1_000, released_snapshot["available_balance_minor"])

    def test_concurrent_holds_against_one_reserve_allow_only_one_winner(self):
        self.store.record_funding("concurrent-fund", "owner-uuid", 1_000, "usd", "owner_capital", self.VALID_EVIDENCE_HASH, 1_900)
        first = self._proposed_allocation("concurrent-first", quoted_funding_minor=600, fund_reserve=False, version=1)
        second = self._proposed_allocation("concurrent-second", quoted_funding_minor=600, fund_reserve=False, version=2)

        def hold(operation_id, allocation_id):
            try:
                return self.store.hold_allocation(operation_id, allocation_id, "owner-uuid", 2_200)["state"]
            except SettlementInsufficientFunds:
                return "insufficient"

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(
                lambda item: hold(*item),
                [("concurrent-hold-1", first["allocation_id"]), ("concurrent-hold-2", second["allocation_id"])],
            ))
        self.assertEqual(["funding_held", "insufficient"], sorted(outcomes))
        self.assertEqual(400, self.store.funding_balance("reserve:available"))
        self.assertTrue(self.store.audit_funding()["balanced"])

    def _policy(self, policy_id, version, program_cap_minor=1_000, period_cap_minor=1_000):
        return {
            "policy_id": policy_id,
            "version": version,
            "effective_from_ms": 1_000,
            "effective_to_ms": None,
            "eligible_action_types": ["calibrate_measurement_tool"],
            "evidence_requirements": ["verified_causal_evidence"],
            "cu_milli_per_funding_minor": 1_000,
            "min_claim_cu_milli": 1,
            "max_claim_cu_milli": 10_000,
            "program_cap_minor": program_cap_minor,
            "period_cap_minor": period_cap_minor,
            "period_ms": 1_000,
            "beneficiary_class": "eov_owner_development",
            "funding_source_class": "owner_capital",
            "funding_currency": "usd",
            "compliance_manifest_hash": self.VALID_COMPLIANCE_MANIFEST,
        }

    def _write_task3_approved_fixture(self, database_path):
        policy = self._policy("legacy-policy", 1)
        connection = sqlite3.connect(database_path)
        try:
            connection.executescript(
                """CREATE TABLE settlement_operations (
                    operation_id TEXT PRIMARY KEY, request_hash TEXT NOT NULL, result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE settlement_policies (
                    policy_id TEXT PRIMARY KEY, version INTEGER NOT NULL UNIQUE, owner_subject TEXT NOT NULL,
                    policy_json TEXT NOT NULL, policy_hash TEXT NOT NULL, state TEXT NOT NULL,
                    approved_at_ms INTEGER NOT NULL, activation_evidence_json TEXT, activated_at_ms INTEGER
                );
                CREATE TABLE settlement_allocations (
                    allocation_id TEXT PRIMARY KEY, operation_id TEXT NOT NULL UNIQUE,
                    owner_subject TEXT NOT NULL, beneficiary_class TEXT NOT NULL, policy_id TEXT NOT NULL,
                    policy_version INTEGER NOT NULL, policy_snapshot_json TEXT NOT NULL, world_id TEXT NOT NULL,
                    public_claim_ids_json TEXT NOT NULL, eligible_cu_milli INTEGER NOT NULL,
                    quoted_funding_minor INTEGER NOT NULL, period_start_ms INTEGER NOT NULL DEFAULT 0,
                    state TEXT NOT NULL, created_at_ms INTEGER NOT NULL, held_at_ms INTEGER,
                    approval_hash TEXT, approved_at_ms INTEGER, expires_at_ms INTEGER,
                    cancelled_at_ms INTEGER, expired_at_ms INTEGER,
                    FOREIGN KEY(operation_id) REFERENCES settlement_operations(operation_id),
                    FOREIGN KEY(policy_id) REFERENCES settlement_policies(policy_id),
                    CHECK(beneficiary_class = 'eov_owner_development'),
                    CHECK(state IN ('proposed', 'funding_held', 'owner_approved', 'cancelled', 'expired')),
                    CHECK(typeof(policy_version) = 'integer' AND policy_version > 0),
                    CHECK(typeof(eligible_cu_milli) = 'integer' AND eligible_cu_milli > 0),
                    CHECK(typeof(quoted_funding_minor) = 'integer' AND quoted_funding_minor > 0),
                    CHECK(typeof(period_start_ms) = 'integer' AND period_start_ms >= 0),
                    CHECK(typeof(created_at_ms) = 'integer' AND created_at_ms >= 0)
                );
                CREATE INDEX idx_legacy_alloc_owner ON settlement_allocations(owner_subject);"""
            )
            connection.execute("INSERT INTO settlement_operations(operation_id, request_hash, result_json) VALUES (?, ?, ?)", ("legacy-allocation", "legacy", "{}"))
            connection.execute(
                "INSERT INTO settlement_policies VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("legacy-policy", 1, "owner-uuid", json.dumps(policy), "legacy-policy-hash", "settlement_active", 1_500, None, 2_000),
            )
            connection.execute(
                "INSERT INTO settlement_allocations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("allocation:legacy-task3", "legacy-allocation", "owner-uuid", "eov_owner_development", "legacy-policy", 1,
                 json.dumps(policy), "world-1", json.dumps(["claim:legacy"]), 4_000, 4, 2_000,
                 "owner_approved", 2_100, 2_200, self.VALID_EVIDENCE_HASH, 2_300, 9_000, None, None),
            )
            connection.commit()
        finally:
            connection.close()

    def _proposed_allocation(
        self,
        operation_id,
        quoted_funding_minor,
        *,
        fund_reserve=True,
        version=1,
        claim=None,
        program_cap_minor=None,
    ):
        program_cap_minor = program_cap_minor or max(quoted_funding_minor, 1)
        policy = self._policy(
            f"hold-policy-{operation_id}", version,
            program_cap_minor=program_cap_minor,
            period_cap_minor=program_cap_minor,
        )
        policy["cu_milli_per_funding_minor"] = 1
        policy["max_claim_cu_milli"] = max(quoted_funding_minor, 1)
        created = self.store.create_policy(f"{operation_id}-policy", "owner-uuid", policy, 1_500)
        if fund_reserve:
            self.store.record_funding(
                f"{operation_id}-fund", "owner-uuid", 1_000, "usd", "owner_capital", self.VALID_EVIDENCE_HASH, 1_900,
            )
        self.store.activate_policy(
            f"{operation_id}-activate", "owner-uuid", created["policy_id"], "allocation_active",
            {
                "owner_signature": self.VALID_OWNER_SIGNATURE,
                "compliance_manifest_hash": self.VALID_COMPLIANCE_MANIFEST,
                "funded_program_cap_minor": program_cap_minor,
            },
            2_000,
        )
        claim = dict(claim or self._public_claim(f"claim:{operation_id}"))
        claim["amount_milli"] = quoted_funding_minor
        return self.store.create_allocation(
            operation_id, "owner-uuid", "world-1", created["policy_id"], [claim], 2_100,
        )

    @staticmethod
    def _public_claim(claim_id):
        return {
            "entry_id": claim_id,
            "status": "verified_provisional",
            "spendable": False,
            "unit": "CU-placeholder",
            "action_type": "calibrate_measurement_tool",
            "amount_milli": 2_500,
            "evidence_hash": "verified-event-hash",
            "commission_hash": "commissioned-event-hash",
            "contributor_ref": "contributor:one",
            "verifier_ref": "verifier:two",
        }


if __name__ == "__main__":
    unittest.main()
