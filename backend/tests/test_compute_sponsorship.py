import tempfile
import unittest
from pathlib import Path

from economy import (
    ComputeSponsorshipStore,
    SettlementIdempotencyConflict,
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
            "beneficiary_class": "eov_owner_development",
            "funding_source_class": "owner_capital",
            "compliance_manifest_hash": self.VALID_COMPLIANCE_MANIFEST,
        }
        created = self.store.create_policy("policy-create-1", "owner-uuid", policy, 1_500)
        policy["cu_milli_per_funding_minor"] = 500
        self.assertEqual(1_000, self.store.get_policy(created["policy_id"])["policy"]["cu_milli_per_funding_minor"])

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


if __name__ == "__main__":
    unittest.main()
