import unittest
from causal_ledger import CausalEvent, CausalLedger


def event(event_id, sequence, state, previous_hash="GENESIS", parents=None, physical=False):
    return CausalEvent(event_id, sequence, sequence, "work_order", "builder", "action-1", state, "build a workshop", "village_square", parents or [], physical_effect=physical, previous_hash=previous_hash)


class CausalLedgerTests(unittest.TestCase):
    def test_correction_appends_without_advancing_or_rewriting_state(self):
        ledger = CausalLedger()
        first = ledger.append(event("e1", 1, "proposed"))
        original_hash = first.event_hash
        correction = event("e2", 2, "proposed", first.event_hash, ["e1"])
        correction.event_type = "evidence_correction"
        correction.evidence = [{"corrects_event_id": "e1", "belief": "The observation needs repeating."}]
        ledger.append(correction)
        self.assertEqual(original_hash, first.event_hash)
        self.assertTrue(ledger.verify())
        ledger.append(event("e3", 3, "accepted", correction.event_hash, ["e2"]))
        self.assertTrue(ledger.verify())

    def test_correction_cannot_mutate_physical_state_or_skip_state(self):
        for target_state, physical in (("accepted", False), ("proposed", True)):
            ledger = CausalLedger()
            first = ledger.append(event("e1", 1, "proposed"))
            correction = event("e2", 2, target_state, first.event_hash, ["e1"], physical)
            correction.event_type = "evidence_correction"
            correction.evidence = [{"corrects_event_id": "e1", "belief": "Correction"}]
            with self.assertRaises(ValueError):
                ledger.append(correction)

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

    def test_multi_party_action_can_collect_acceptances_before_work(self):
        ledger = CausalLedger()
        proposed = ledger.append(event("e1", 1, "proposed"))
        waiting = ledger.append(event("e2", 2, "awaiting_acceptances", proposed.event_hash, ["e1"]))
        ledger.append(event("e3", 3, "accepted", waiting.event_hash, ["e2"]))
        self.assertTrue(ledger.verify())

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
