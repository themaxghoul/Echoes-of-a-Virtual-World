import json
import tempfile
import unittest
from pathlib import Path

from economy import ComputeSponsorshipStore, SettlementError
from economy.public_ledger import project_public_cu_ledger
from economy.settlement_service import SettlementService
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
            "beneficiary_class": "eov_owner_development",
            "funding_source_class": "owner_capital",
            "compliance_manifest_hash": self.VALID_COMPLIANCE_MANIFEST,
        }, 1_500)

    def _run_world_until_verified_calibration_claim(self):
        self.world_store.apply_action(self.world_id, "calibrator-join", "calibrator", {"type": "join", "location": [8, 6]}, now_ms=1_000_001)
        snapshot = self.world_store.snapshot(self.world_id)
        state = snapshot["state"]
        state["players"]["calibrator"]["competency_records"]["measurement"] = {
            "demonstrated": 0.2, "provenance": ["fixture:verified-measurement:calibrator"],
        }
        state["npcs"]["mira"]["location"] = [8, 6]
        with self.world_store.transaction() as connection:
            connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(state), self.world_id))
        action_id = "calibration-claim"
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
        return ledger["entries"][0]["entry_id"]

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


if __name__ == "__main__":
    unittest.main()
