import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from economy.compute_sponsorship import ComputeSponsorshipStore
from economy.provider_adapters import RecordedOfficialBillingAdapter
from economy.settlement_projection import (
    Ed25519SettlementPublisher,
    canonical_publication_bytes,
    project_public_settlement,
    verify_public_settlement_chain,
)


class PublicSettlementProjectionTests(unittest.TestCase):
    """The verifier must reject a validly rehashed but semantically false receipt."""

    OWNER = "owner-uuid-PRIVATE-IDENTITY"
    PRIVATE_WORLD = "private-world-memory-DO-NOT-PUBLISH"
    PROVIDER_SECRET = "openai-admin-key-DO-NOT-PUBLISH"

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = ComputeSponsorshipStore(Path(self.temp.name) / "settlement.sqlite3")
        self.publisher = Ed25519SettlementPublisher("test-publisher", Ed25519PrivateKey.generate())
        self.trusted_publishers = {self.publisher.key_id: self.publisher.public_key}
        self._create_reconciled_allocation()
        self.projection = project_public_settlement(self.store, self.publisher)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_public_projection_links_reconciled_claim_policy_funding_and_receipt_without_private_identity(self):
        projection = self.projection

        self.assertEqual("eov-public-compute-sponsorship/v1", projection["schema"])
        self.assertTrue(verify_public_settlement_chain(projection, self.trusted_publishers))
        self.assertEqual(0, projection["totals"]["posting_balance_minor"])
        self.assertEqual("eov_owner_development", projection["allocations"][0]["beneficiary_class"])
        self.assertEqual(2, projection["allocations"][0]["funding"]["captured_minor"])
        self.assertEqual(1, projection["allocations"][0]["funding"]["released_minor"])
        self.assertEqual(3_000, projection["allocations"][0]["eligible_cu_milli"])
        self.assertEqual(1_700, projection["allocations"][0]["lifecycle"]["provider_effective_at_ms"])

        self.assertEqual(
            {"schema", "claims", "policies", "funding_receipts", "reserve_proof", "root_hash", "allocations", "totals", "head_hash", "publication"},
            set(projection),
        )
        self.assertEqual(
            {
                "sequence", "allocation_ref", "beneficiary_class", "claim_refs", "policy",
                "eligible_cu_milli", "currency", "state", "provider", "funding", "lifecycle", "evidence",
                "previous_hash", "chain_hash",
            },
            set(projection["allocations"][0]),
        )
        self.assertEqual(
            {"quoted_minor", "held_minor", "captured_minor", "released_minor", "hold_sequence", "postings"},
            set(projection["allocations"][0]["funding"]),
        )
        self.assertEqual(
            {"policy_ref", "version", "formula", "currency", "compliance_manifest_hash"},
            set(projection["policies"][0]),
        )

        serialized = json.dumps(projection, sort_keys=True)
        for private_value in (
            self.OWNER,
            self.PRIVATE_WORLD,
            self.PROVIDER_SECRET,
            "raw-provider-receipt-id",
            "raw-provider-transaction-id",
            "eov:allocation:",
        ):
            self.assertNotIn(private_value, serialized)
        self.assertIn("sha256:" + ("8" * 64), serialized)

    def test_projection_is_byte_for_byte_deterministic_for_the_same_store_state(self):
        first = project_public_settlement(self.store, self.publisher)
        second = project_public_settlement(self.store, self.publisher)

        self.assertEqual(
            json.dumps(first, sort_keys=True, separators=(",", ":")),
            json.dumps(second, sort_keys=True, separators=(",", ":")),
        )

    def test_verifier_rejects_tampering_unknown_private_fields_and_chain_reordering(self):
        tampered = copy.deepcopy(self.projection)
        tampered["allocations"][0]["funding"]["captured_minor"] = 3
        self._resign(tampered)
        self.assertFalse(verify_public_settlement_chain(tampered, self.trusted_publishers))

        leaked = copy.deepcopy(self.projection)
        leaked["allocations"][0]["owner_subject"] = self.OWNER
        self._resign(leaked)
        self.assertFalse(verify_public_settlement_chain(leaked, self.trusted_publishers))

        reordered = self._two_allocation_projection()
        reordered["allocations"].reverse()
        self.assertFalse(verify_public_settlement_chain(reordered, self.trusted_publishers))

    def test_verifier_rejects_deleted_duplicate_and_broken_claim_policy_or_receipt_links(self):
        for mutate in (
            lambda value: value["allocations"].pop(),
            lambda value: value["allocations"].append(copy.deepcopy(value["allocations"][0])),
            lambda value: value["allocations"][0]["claim_refs"].__setitem__(0, "claim:missing"),
            lambda value: value["allocations"][0]["policy"].__setitem__("policy_ref", "policy:missing"),
            lambda value: value["allocations"][0]["evidence"].__setitem__("provider_receipt_hash", None),
        ):
            with self.subTest(mutate=mutate):
                malformed = copy.deepcopy(self.projection)
                mutate(malformed)
                self._resign(malformed)
                self.assertFalse(verify_public_settlement_chain(malformed, self.trusted_publishers))

    def test_verifier_rejects_invalid_transition_imbalanced_postings_and_unsupported_currency(self):
        for mutate in (
            lambda value: value["allocations"][0]["lifecycle"]["events"].__setitem__(2, {
                "state": "reconciled", "occurred_at_ms": 1_600,
            }),
            lambda value: value["allocations"][0]["funding"]["postings"][0].__setitem__("amount_minor", 99),
            lambda value: value["allocations"][0].__setitem__("currency", "eur"),
            lambda value: value["allocations"][0]["evidence"].__setitem__("cost_hash", None),
        ):
            with self.subTest(mutate=mutate):
                malformed = copy.deepcopy(self.projection)
                mutate(malformed)
                self._resign(malformed)
                self.assertFalse(verify_public_settlement_chain(malformed, self.trusted_publishers))

    def test_publication_requires_an_external_trusted_key_and_rejects_rehashed_deletion(self):
        with self.assertRaisesRegex(ValueError, "publisher"):
            project_public_settlement(self.store, None)
        self.assertFalse(verify_public_settlement_chain(self.projection, {}))

        deleted = copy.deepcopy(self.projection)
        deleted["allocations"].pop()
        attacker = Ed25519SettlementPublisher("attacker", Ed25519PrivateKey.generate())
        self._resign(deleted, attacker)
        self.assertFalse(verify_public_settlement_chain(deleted, self.trusted_publishers))

        for field in ("root_hash", "head_hash", "totals"):
            with self.subTest(field=field):
                tampered = copy.deepcopy(self.projection)
                if field == "totals":
                    tampered[field]["quoted_minor"] += 1
                else:
                    tampered[field] = "sha256:" + ("f" * 64)
                self._resign(tampered, attacker)
                self.assertFalse(verify_public_settlement_chain(tampered, self.trusted_publishers))

    def test_persisted_opaque_references_survive_restart_and_do_not_derive_from_private_values(self):
        first = self.projection
        self.store.close()
        self.store = ComputeSponsorshipStore(Path(self.temp.name) / "settlement.sqlite3")
        second = project_public_settlement(self.store, self.publisher)
        self.assertEqual(first["allocations"][0]["allocation_ref"], second["allocations"][0]["allocation_ref"])
        self.assertEqual(first["policies"][0]["policy_ref"], second["policies"][0]["policy_ref"])
        self.assertEqual(first["funding_receipts"][0]["receipt_ref"], second["funding_receipts"][0]["receipt_ref"])
        serialized = json.dumps(second, sort_keys=True)
        for private_value in (self.OWNER, self.PRIVATE_WORLD, "private-policy-id-not-public", "fund-private"):
            self.assertNotIn(private_value, serialized)
        self.assertNotEqual(
            hashlib.sha256(f"eov-public-compute-sponsorship/v1|allocation|allocation-private".encode()).hexdigest(),
            second["allocations"][0]["allocation_ref"].split(":", 1)[1],
        )

    def test_verifier_rejects_cross_allocation_claim_duplication_after_authorized_resign(self):
        duplicate = copy.deepcopy(self.projection)
        duplicate["allocations"][1]["claim_refs"] = list(duplicate["allocations"][0]["claim_refs"])
        self._resign(duplicate)
        self.assertFalse(verify_public_settlement_chain(duplicate, self.trusted_publishers))

    def test_reserve_proof_binds_receipts_to_holds_before_they_are_used(self):
        self.assertFalse(any("receipt_refs" in allocation["funding"] for allocation in self.projection["allocations"]))
        proof = self.projection["reserve_proof"]
        self.assertEqual([item["sequence"] for item in proof], sorted(item["sequence"] for item in proof))
        self.assertTrue(any(item["kind"] == "receipt_credit" for item in proof))
        self.assertTrue(any(item["kind"] == "hold" for item in proof))

        future_credit = copy.deepcopy(self.projection)
        credit = next(item for item in future_credit["reserve_proof"] if item["kind"] == "receipt_credit")
        credit["occurred_at_ms"] = 9_999
        self._resign(future_credit)
        self.assertFalse(verify_public_settlement_chain(future_credit, self.trusted_publishers))

    def test_verifier_rejects_reordering_lifecycle_timestamp_mismatch_and_unknown_provider_after_authorized_resign(self):
        for mutate in (
            lambda value: value["claims"].reverse(),
            lambda value: value["policies"].reverse(),
            lambda value: value["funding_receipts"].reverse(),
            lambda value: value["reserve_proof"].reverse(),
            lambda value: value["allocations"][0]["lifecycle"].__setitem__("held_at_ms", 1_401),
            lambda value: value["allocations"][0].__setitem__("provider", "sk-live-private-secret"),
        ):
            with self.subTest(mutate=mutate):
                malformed = copy.deepcopy(self.projection)
                mutate(malformed)
                self._resign(malformed)
                self.assertFalse(verify_public_settlement_chain(malformed, self.trusted_publishers))

    def _create_reconciled_allocation(self):
        hash_for = lambda digit: "sha256:" + (digit * 64)
        self.store.record_funding(
            "fund-private", self.OWNER, 10, "usd", "owner_capital", hash_for("8"), 1_000,
        )
        self.store.record_funding(
            "fund-private-second", self.OWNER, 1, "usd", "owner_capital", hash_for("7"), 1_050,
        )
        policy = {
            "policy_id": "private-policy-id-not-public",
            "version": 1,
            "effective_from_ms": 1_000,
            "effective_to_ms": None,
            "eligible_action_types": ["calibrate_measurement_tool"],
            "evidence_requirements": [
                "verified_causal_evidence", "commissioned_action", "independent_verifier",
            ],
            "cu_milli_per_funding_minor": 1_000,
            "min_claim_cu_milli": 1_000,
            "max_claim_cu_milli": 5_000,
            "program_cap_minor": 10,
            "period_cap_minor": 10,
            "period_ms": 10_000,
            "beneficiary_class": "eov_owner_development",
            "funding_source_class": "owner_capital",
            "funding_currency": "usd",
            "compliance_manifest_hash": hash_for("1"),
        }
        self.store.create_policy("policy-private", self.OWNER, policy, 1_100)
        self.store.create_policy("policy-private-second", self.OWNER, {**policy, "policy_id": "private-policy-id-not-public-second", "version": 2}, 1_101)
        self.store.activate_policy("policy-allocate", self.OWNER, policy["policy_id"], "allocation_active", {
            "compliance_manifest_hash": hash_for("1"), "owner_signature": hash_for("2"),
        }, 1_200)
        self.store.activate_policy("policy-settle", self.OWNER, policy["policy_id"], "settlement_active", {
            "provider_capability_hash": hash_for("3"),
        }, 1_250)
        allocation = self.store.create_allocation(
            "allocation-private", self.OWNER, self.PRIVATE_WORLD, policy["policy_id"], [{
                "entry_id": "claim:public-verified-ref",
                "status": "verified_provisional",
                "spendable": False,
                "unit": "CU-placeholder",
                "action_type": "calibrate_measurement_tool",
                "amount_milli": 3_000,
                "evidence_hash": hash_for("4"),
                "commission_hash": hash_for("5"),
                "contributor_ref": "contributor:public-a",
                "verifier_ref": "verifier:public-b",
            }], 1_300,
        )
        self.store.hold_allocation("hold-private", allocation["allocation_id"], self.OWNER, 1_400)
        self.store.approve_allocation(
            "approve-private", allocation["allocation_id"], self.OWNER, hash_for("6"), 9_000, 1_500,
        )
        pending = self.store.begin_provider_submission(
            "submit-private", allocation["allocation_id"], self.OWNER, "test-provider", hash_for("7"), 1_600,
        )
        receipt = RecordedOfficialBillingAdapter().normalize_receipt({
            "provider": "test-provider",
            "receipt_id": "raw-provider-receipt-id",
            "provider_transaction_id": "raw-provider-transaction-id",
            "provider_operation_id": pending["provider_operation_id"],
            "amount_minor": 3,
            "currency": "usd",
            "completed_at_ms": 1_610,
            "evidence_hash": hash_for("9"),
            "human_completed": True,
        })
        self.store.confirm_provider_receipt(
            "receipt-private", allocation["allocation_id"], self.OWNER, receipt, 1_620,
        )
        self.store.reconcile_provider_cost("cost-private", allocation["allocation_id"], self.OWNER, [{
            "provider_operation_id": pending["provider_operation_id"],
            "amount_minor": 2,
            "currency": "usd",
            "start_time_ms": 1_600,
            "end_time_ms": 1_700,
            "record_commitment": hash_for("a"),
        }], 1_800)
        second = self.store.create_allocation(
            "allocation-private-second", self.OWNER, self.PRIVATE_WORLD, policy["policy_id"], [{
                "entry_id": "claim:public-verified-ref-second",
                "status": "verified_provisional",
                "spendable": False,
                "unit": "CU-placeholder",
                "action_type": "calibrate_measurement_tool",
                "amount_milli": 3_000,
                "evidence_hash": hash_for("b"),
                "commission_hash": hash_for("c"),
                "contributor_ref": "contributor:public-c",
                "verifier_ref": "verifier:public-d",
            }], 2_000,
        )
        self.store.hold_allocation("hold-private-second", second["allocation_id"], self.OWNER, 2_100)
        self.store.approve_allocation(
            "approve-private-second", second["allocation_id"], self.OWNER, hash_for("d"), 9_000, 2_200,
        )
        pending_second = self.store.begin_provider_submission(
            "submit-private-second", second["allocation_id"], self.OWNER, "test-provider", hash_for("e"), 2_300,
        )
        second_receipt = RecordedOfficialBillingAdapter().normalize_receipt({
            "provider": "test-provider",
            "receipt_id": "raw-provider-receipt-id-second",
            "provider_transaction_id": "raw-provider-transaction-id-second",
            "provider_operation_id": pending_second["provider_operation_id"],
            "amount_minor": 3,
            "currency": "usd",
            "completed_at_ms": 2_310,
            "evidence_hash": hash_for("f"),
            "human_completed": True,
        })
        self.store.confirm_provider_receipt(
            "receipt-private-second", second["allocation_id"], self.OWNER, second_receipt, 2_320,
        )
        self.store.reconcile_provider_cost("cost-private-second", second["allocation_id"], self.OWNER, [{
            "provider_operation_id": pending_second["provider_operation_id"],
            "amount_minor": 2,
            "currency": "usd",
            "start_time_ms": 2_300,
            "end_time_ms": 2_400,
            "record_commitment": hash_for("0"),
        }], 2_500)

    def _two_allocation_projection(self):
        return copy.deepcopy(self.projection)

    def _resign(self, projection, publisher=None):
        self._rechain(projection)
        publisher = publisher or self.publisher
        projection["publication"] = {
            "algorithm": "ed25519",
            "key_id": publisher.key_id,
            "signature": publisher.sign(canonical_publication_bytes(projection)),
        }

    @staticmethod
    def _rechain(projection):
        static = {
            "schema": projection["schema"],
            "claims": projection["claims"],
            "policies": projection["policies"],
            "funding_receipts": projection["funding_receipts"],
            "reserve_proof": projection["reserve_proof"],
        }
        projection["root_hash"] = "sha256:" + hashlib.sha256(
            (projection["schema"] + "|" + json.dumps(static, sort_keys=True, separators=(",", ":"))).encode("utf-8")
        ).hexdigest()
        previous_hash = projection["root_hash"]
        for sequence, allocation in enumerate(projection["allocations"], start=1):
            allocation["sequence"] = sequence
            allocation["previous_hash"] = previous_hash
            body = {key: value for key, value in allocation.items() if key != "chain_hash"}
            allocation["chain_hash"] = "sha256:" + hashlib.sha256(
                (previous_hash + "|" + json.dumps(body, sort_keys=True, separators=(",", ":"))).encode("utf-8")
            ).hexdigest()
            previous_hash = allocation["chain_hash"]
        projection["head_hash"] = previous_hash


if __name__ == "__main__":
    unittest.main()
