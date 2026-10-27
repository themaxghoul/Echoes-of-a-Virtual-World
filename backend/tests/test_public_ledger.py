import json
import unittest

from economy.public_ledger import project_public_cu_ledger, verify_public_chain


class PublicCULedgerTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = {
            "world_id": "founders-settlement",
            "revision": 42,
            "tick": 120,
            "state": {
                "shared_actions": {
                    "records": {
                        "repair-by-private-player": {
                            "id": "repair-by-private-player",
                            "state": "commissioned",
                            "actor_id": "private-player-uuid",
                            "verifier_id": "mira",
                            "definition": {"action_type": "repair_pump"},
                        },
                    },
                    "ledger": [
                        {
                            "event_id": "repair-by-private-player:verified:6",
                            "action_id": "repair-by-private-player",
                            "state": "verified",
                            "tick": 118,
                            "event_hash": "verified-evidence-hash",
                        },
                        {
                            "event_id": "repair-by-private-player:commissioned:7",
                            "action_id": "repair-by-private-player",
                            "state": "commissioned",
                            "tick": 120,
                            "event_hash": "commissioned-event-hash",
                        },
                    ],
                    "valuation_claims": [
                        {
                            "action_id": "repair-by-private-player",
                            "actor_id": "private-player-uuid",
                            "amount_milli": 2500,
                            "spendable": False,
                            "evidence_event": "repair-by-private-player:verified:6",
                        },
                    ],
                },
            },
        }

    def test_projection_is_balanced_pseudonymous_and_nonspendable(self):
        ledger = project_public_cu_ledger(self.snapshot)

        self.assertEqual("eov-public-cu-ledger/v1", ledger["schema"])
        self.assertEqual("CU-placeholder", ledger["unit"])
        self.assertFalse(ledger["spendable"])
        self.assertEqual("disabled", ledger["external_settlement"])
        self.assertEqual(2500, ledger["totals"]["provisional_cu_milli"])
        self.assertEqual(0, sum(posting["amount_milli"] for posting in ledger["entries"][0]["postings"]))
        serialized = json.dumps(ledger, sort_keys=True)
        self.assertNotIn("private-player-uuid", serialized)
        self.assertNotIn("repair-by-private-player", serialized)
        self.assertIn("verified-evidence-hash", serialized)

    def test_projection_is_deterministic_and_tamper_evident(self):
        first = project_public_cu_ledger(self.snapshot)
        second = project_public_cu_ledger(self.snapshot)

        self.assertEqual(first, second)
        self.assertTrue(verify_public_chain(first))
        first["entries"][0]["amount_milli"] += 1
        self.assertFalse(verify_public_chain(first))

    def test_projection_fails_closed_for_unverified_or_spendable_claims(self):
        self.snapshot["state"]["shared_actions"]["valuation_claims"][0]["spendable"] = True
        with self.assertRaisesRegex(ValueError, "spendable claim"):
            project_public_cu_ledger(self.snapshot)


if __name__ == "__main__":
    unittest.main()
