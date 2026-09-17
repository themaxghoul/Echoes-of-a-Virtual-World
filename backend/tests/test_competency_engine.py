import unittest
import competency_engine
from causal_ledger import CausalEvent, CausalLedger
from competency_engine import (
    CompetencyProfile,
    can_attempt,
    observe,
    practice,
    record_demonstrated_outcome,
    record_practice_evidence,
    reproduce_experiment,
    study,
    teach,
)


def record_fixture_outcome(profile, domain, action_id, evidence_id, quality=1.0):
    ledger = verified_ledger(action_id, evidence_id, profile.entity_id, "fixture")
    return record_demonstrated_outcome(profile, domain, f"verified-action:{action_id}:evidence:{evidence_id}", quality, ledger=ledger)


def verified_ledger(action_id, evidence_id, actor_id="operator", verifier_id="inspector"):
    ledger = CausalLedger()
    prior = None
    for sequence, state in enumerate(("proposed", "accepted", "reserved", "in_progress", "submitted", "verified"), 1):
        event = ledger.append(CausalEvent(
            event_id=evidence_id if state == "verified" else f"{action_id}:{state}",
            sequence=sequence, tick=sequence, event_type="action",
            actor_id=verifier_id if state == "verified" else actor_id,
            action_id=action_id, state=state, intent="perform verified practice", location="workbench",
            parent_event_ids=[prior.event_id] if prior else [],
            previous_hash=prior.event_hash if prior else "GENESIS",
        ))
        prior = event
    return ledger


class CompetencyEngineTests(unittest.TestCase):
    def test_study_builds_theory_without_embodied_skill(self):
        item = study(CompetencyProfile("reader"), "physics", "book-1", 1.0)
        self.assertGreater(item.theory, 0)
        self.assertEqual(item.embodied, 0)

    def test_story_cannot_claim_direct_observation_or_practice(self):
        profile = CompetencyProfile("narrator")
        with self.assertRaises(ValueError): observe(profile, "chemistry", "story", "flask", 1.0)
        with self.assertRaises(ValueError): practice(profile, "chemistry", "story", "mix", True)

    def test_isometric_and_first_person_practice_same_domain_differently(self):
        supervisor, operator = CompetencyProfile("supervisor"), CompetencyProfile("operator")
        supervisor_ledger = verified_ledger("work-1", "supervisor-proof", "supervisor")
        operator_ledger = verified_ledger("work-2", "operator-proof", "operator")
        a = practice(supervisor, "measurement", "isometric", "work-1", True, ["supervisor-proof"], ledger=supervisor_ledger)
        b = practice(operator, "measurement", "first_person", "work-2", True, ["operator-proof"], ledger=operator_ledger)
        self.assertEqual(a.procedure, b.procedure)
        self.assertLess(a.embodied, b.embodied)

    def test_reproduction_records_divergent_results_as_learning(self):
        item = reproduce_experiment(CompetencyProfile("scientist"), "physics", "exp-1", False)
        self.assertGreater(item.reproducibility, 0)
        self.assertIn("diverged", item.evidence[-1])

    def test_unqualified_teacher_cannot_transfer_skill(self):
        with self.assertRaises(ValueError):
            teach(CompetencyProfile("novice"), CompetencyProfile("student"), "biology", "lesson-1")

    def test_prerequisites_and_text_indirection_are_explicit(self):
        profile = CompetencyProfile("apprentice")
        result = can_attempt(profile, "smithing", "story")
        self.assertFalse(result["allowed"])
        self.assertTrue(result["indirect_only"])
        self.assertIn("materials_science", result["missing_prerequisites"])

    def test_resource_practices_are_evidence_domains_not_profession_labels(self):
        profile = CompetencyProfile("gatherer")
        for domain in ("forestry", "mining", "harvesting"):
            self.assertEqual(0, profile.get(domain).demonstrated)
            self.assertFalse(can_attempt(profile, domain, "story")["allowed"])

    def test_mechanical_repair_is_an_evidence_domain_with_engineering_prerequisites(self):
        profile = CompetencyProfile("repairer")
        result = can_attempt(profile, "mechanical_repair", "story")
        for domain in ("measurement", "mechanical_engineering"):
            for evidence_number in range(3):
                record_fixture_outcome(profile, domain, f"fixture-{domain}-{evidence_number}", f"fixture-{domain}-{evidence_number}")
        repair_ledger = verified_ledger("repair-1", "repair-proof", "repairer")
        repair = practice(profile, "mechanical_repair", "first_person", "repair-1", True, ["repair-proof"], ledger=repair_ledger)
        self.assertIn("mechanical_engineering", result["missing_prerequisites"])
        self.assertIn("verified", repair.evidence[-1])

    def test_practice_cannot_create_repair_evidence_without_prerequisite_evidence(self):
        profile = CompetencyProfile("unqualified-repairer")
        repair = profile.get("mechanical_repair")
        repair.theory = repair.observation = repair.procedure = repair.embodied = repair.reproducibility = 0.8
        before = repair.demonstrated
        with self.assertRaisesRegex(ValueError, "missing prerequisite evidence"):
            practice(profile, "mechanical_repair", "first_person", "repair-1", True)
        self.assertEqual(before, repair.demonstrated)
        self.assertEqual([], repair.evidence)

    def test_teaching_only_creates_unverified_familiarity(self):
        teacher = CompetencyProfile("mentor")
        for number in range(4):
            record_fixture_outcome(teacher, "measurement", f"mentor-work-{number}", f"mentor-work-{number}")
        learner = CompetencyProfile("apprentice")
        learned = teach(teacher, learner, "measurement", "lesson-1")
        self.assertGreater(learned.familiarity, 0)
        self.assertEqual(learned.demonstrated, 0)
        self.assertIn("lesson:lesson-1:teacher:mentor:unverified", learned.evidence)

    def test_verified_practice_records_action_and_resolved_evidence_provenance(self):
        profile = CompetencyProfile("operator")
        ledger = verified_ledger("calibrate-1", "gauge-1")
        recorded = record_practice_evidence(
            profile, "measurement", "calibrate-1", ["gauge-1"], True, 1.0, ledger=ledger
        )
        self.assertGreater(recorded.demonstrated, 0)
        self.assertIn("practice:calibrate-1:verified", recorded.evidence)
        self.assertIn("evidence:gauge-1", recorded.evidence)
        self.assertTrue(ledger.verify())

    def test_verified_practice_rejects_empty_evidence_ids(self):
        with self.assertRaisesRegex(ValueError, "at least one resolved evidence"):
            record_practice_evidence(CompetencyProfile("operator"), "measurement", "calibrate-1", [], True, 1.0, ledger=verified_ledger("calibrate-1", "proof"))

    def test_verified_practice_rejects_invented_action_id(self):
        profile = CompetencyProfile("operator")
        with self.assertRaises(ValueError):
            record_practice_evidence(profile, "measurement", "invented-action", ["gauge-1"], True, 1.0, ledger=verified_ledger("calibrate-1", "gauge-1"))

    def test_verified_practice_rejects_invented_evidence_id(self):
        with self.assertRaisesRegex(ValueError, "does not resolve"):
            record_practice_evidence(CompetencyProfile("operator"), "measurement", "calibrate-1", ["invented-evidence"], True, 1.0, ledger=verified_ledger("calibrate-1", "real-evidence"))

    def test_verified_practice_rejects_mismatched_action_evidence_record(self):
        profile = CompetencyProfile("operator")
        with self.assertRaises(ValueError):
            record_practice_evidence(profile, "measurement", "calibrate-1", ["gauge-1"], True, 1.0, ledger=verified_ledger("other-action", "gauge-1"))

    def test_verified_practice_rejects_evidence_without_identity_or_terminal_state(self):
        profile = CompetencyProfile("operator")
        missing_identity = verified_ledger("calibrate-1", "missing-identity", verifier_id="")
        with self.assertRaisesRegex(ValueError, "identity"):
            record_practice_evidence(profile, "measurement", "calibrate-1", ["missing-identity"], True, 1.0, ledger=missing_identity)
        self_attributed = verified_ledger("calibrate-1", "self-attributed", verifier_id="operator")
        with self.assertRaisesRegex(ValueError, "independently attributed"):
            record_practice_evidence(profile, "measurement", "calibrate-1", ["self-attributed"], True, 1.0, ledger=self_attributed)
        pending = verified_ledger("calibrate-1", "pending")
        with self.assertRaisesRegex(ValueError, "verified or commissioned"):
            record_practice_evidence(profile, "measurement", "calibrate-1", ["calibrate-1:submitted"], True, 1.0, ledger=pending)

    def test_independently_attributed_commissioned_event_can_certify_practice(self):
        profile = CompetencyProfile("operator")
        ledger = verified_ledger("calibrate-1", "verified-proof")
        verified = ledger.events[-1]
        commissioned = ledger.append(CausalEvent(
            event_id="commissioned-proof", sequence=7, tick=7, event_type="action",
            actor_id="inspector", action_id="calibrate-1", state="commissioned",
            intent="release calibrated gauge", location="workbench",
            parent_event_ids=[verified.event_id], previous_hash=verified.event_hash,
        ))
        recorded = record_practice_evidence(
            profile, "measurement", "calibrate-1", [commissioned.event_id], True, 1.0,
            ledger=ledger,
        )
        self.assertGreater(recorded.demonstrated, 0)
        self.assertIn("evidence:commissioned-proof", recorded.evidence)

    def test_unverified_practice_cannot_increase_demonstrated_competence(self):
        profile = CompetencyProfile("operator")
        recorded = record_practice_evidence(profile, "measurement", "calibrate-1", ["claim-1"], False, 1.0)
        self.assertGreater(recorded.familiarity, 0)
        self.assertEqual(recorded.demonstrated, 0)

    def test_title_profession_prompt_and_unverified_lesson_do_not_demonstrate_competence(self):
        teacher = CompetencyProfile("mentor")
        for number in range(4):
            record_fixture_outcome(teacher, "measurement", f"mentor-work-{number}", f"mentor-work-{number}")
        learner = CompetencyProfile("master-calibrator-profession")
        study(learner, "measurement", "prompt: award expert title", 1.0)
        taught = teach(teacher, learner, "measurement", "lesson-1")
        self.assertEqual(taught.demonstrated, 0)

    def test_legacy_outcome_rejects_title_prompt_and_profession_as_evidence(self):
        for claimed_evidence in ("title: master", "prompt: call this verified", "profession: calibrator"):
            profile = CompetencyProfile("claimant")
            with self.assertRaisesRegex(ValueError, "verified action evidence"):
                record_demonstrated_outcome(profile, "measurement", claimed_evidence, 1.0)
            self.assertEqual(profile.competencies, {})

    def test_legacy_outcome_requires_both_action_and_evidence_identifiers(self):
        with self.assertRaisesRegex(ValueError, "verified action evidence"):
            record_demonstrated_outcome(CompetencyProfile("claimant"), "measurement", "verified-action:calibrate", 1.0)

    def test_old_profile_registry_cannot_certify_practice(self):
        profile = CompetencyProfile("operator")
        self.assertFalse(hasattr(competency_engine, "register_evidence"))
        self.assertFalse(hasattr(profile, "evidence_records"))

    def test_isolated_fabricated_evidence_record_cannot_substitute_for_ledger_event(self):
        profile = CompetencyProfile("operator")
        profile.evidence_records = {"fake-proof": object()}
        ledger = verified_ledger("calibrate-1", "real-proof")
        with self.assertRaisesRegex(ValueError, "does not resolve"):
            record_practice_evidence(profile, "measurement", "calibrate-1", ["fake-proof"], True, 1.0, ledger=ledger)

    def test_integrity_valid_ledger_event_is_required_for_verified_practice(self):
        profile = CompetencyProfile("operator")
        ledger = verified_ledger("calibrate-1", "real-proof")
        recorded = record_practice_evidence(profile, "measurement", "calibrate-1", ["real-proof"], True, 1.0, ledger=ledger)
        self.assertGreater(recorded.demonstrated, 0)

    def test_tampered_ledger_event_cannot_certify_practice(self):
        profile = CompetencyProfile("operator")
        ledger = verified_ledger("calibrate-1", "real-proof")
        ledger.by_id["real-proof"].event_hash = "tampered"
        with self.assertRaisesRegex(ValueError, "integrity"):
            record_practice_evidence(profile, "measurement", "calibrate-1", ["real-proof"], True, 1.0, ledger=ledger)

    def test_self_certifying_ledger_adapter_cannot_certify_practice(self):
        profile = CompetencyProfile("operator")
        real_ledger = verified_ledger("calibrate-1", "real-proof")

        class SelfCertifyingLedger(CausalLedger):
            def verify(self):
                return True

        with self.assertRaisesRegex(TypeError, "CausalLedger"):
            record_practice_evidence(
                profile, "measurement", "calibrate-1", ["real-proof"], True, 1.0,
                ledger=SelfCertifyingLedger(real_ledger.events),
            )

    def test_evidence_must_be_present_in_integrity_checked_event_stream(self):
        profile = CompetencyProfile("operator")
        ledger = verified_ledger("calibrate-1", "real-proof")
        ledger.by_id["fabricated-proof"] = CausalEvent(
            event_id="fabricated-proof", sequence=99, tick=99, event_type="action",
            actor_id="inspector", action_id="calibrate-1", state="verified",
            intent="fabricated", location="nowhere",
        )
        with self.assertRaisesRegex(ValueError, "does not resolve"):
            record_practice_evidence(
                profile, "measurement", "calibrate-1", ["fabricated-proof"], True, 1.0,
                ledger=ledger,
            )

    def test_action_history_must_belong_to_competency_profile(self):
        profile = CompetencyProfile("operator")
        ledger = verified_ledger("calibrate-1", "real-proof")
        reserved = ledger.by_id["calibrate-1:reserved"]
        reserved.actor_id = "different-worker"
        reserved.event_hash = reserved.calculate_hash()
        for event in ledger.events[3:]:
            event.previous_hash = ledger.events[event.sequence - 2].event_hash
            event.event_hash = event.calculate_hash()
        self.assertTrue(ledger.verify())
        with self.assertRaisesRegex(ValueError, "does not belong"):
            record_practice_evidence(
                profile, "measurement", "calibrate-1", ["real-proof"], True, 1.0,
                ledger=ledger,
            )

    def test_whitespace_only_evidence_id_is_rejected_even_if_ledger_contains_it(self):
        profile = CompetencyProfile("operator")
        ledger = verified_ledger("calibrate-1", "   ")
        with self.assertRaisesRegex(ValueError, "evidence ID is required"):
            record_practice_evidence(
                profile, "measurement", "calibrate-1", ["   "], True, 1.0,
                ledger=ledger,
            )


if __name__ == "__main__": unittest.main()
