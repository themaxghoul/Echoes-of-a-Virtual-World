import unittest
from causal_ledger import CausalEvent, CausalLedger


def event(event_id, sequence, state, previous_hash="GENESIS", parents=None, physical=False):
    return CausalEvent(event_id, sequence, sequence, "work_order", "builder", "action-1", state, "build a workshop", "village_square", parents or [], physical_effect=physical, previous_hash=previous_hash)


class CausalLedgerTests(unittest.TestCase):
    def test_valid_lineage_and_integrity(self):
        ledger = CausalLedger()
        first = ledger.append(event("e1", 1, "proposed"))
        second = ledger.append(event("e2", 2, "accepted", first.event_hash, ["e1"]))
        self.assertTrue(ledger.verify())
        self.assertEqual([item.event_id for item in ledger.ancestors("e2")], ["e1"])

    def test_missing_parent_is_rejected(self):
        with self.assertRaises(ValueError):
            CausalLedger().append(event("e1", 1, "proposed", parents=["missing"]))

    def test_lineage_cannot_skip_proposal(self):
        with self.assertRaises(ValueError):
            CausalLedger().append(event("e1", 1, "in_progress"))

    def test_invalid_transition_is_rejected(self):
        ledger = CausalLedger()
        first = ledger.append(event("e1", 1, "proposed"))
        with self.assertRaises(ValueError):
            ledger.append(event("e2", 2, "commissioned", first.event_hash, ["e1"]))

    def test_physical_effect_cannot_precede_execution(self):
        with self.assertRaises(ValueError):
            CausalLedger().append(event("e1", 1, "proposed", physical=True))

    def test_tampering_breaks_integrity(self):
        ledger = CausalLedger()
        ledger.append(event("e1", 1, "proposed"))
        ledger.events[0].intent = "rewritten history"
        self.assertFalse(ledger.verify())


if __name__ == "__main__":
    unittest.main()
