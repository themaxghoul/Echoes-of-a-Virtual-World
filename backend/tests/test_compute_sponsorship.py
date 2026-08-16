import json
import sqlite3
import tempfile
import unittest
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
