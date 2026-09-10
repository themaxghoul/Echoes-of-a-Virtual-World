import unittest
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
        a = practice(supervisor, "measurement", "isometric", "work-1", True)
        b = practice(operator, "measurement", "first_person", "work-2", True)
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
                record_demonstrated_outcome(profile, domain, f"fixture:{domain}:{evidence_number}", 1.0)
        repair = practice(profile, "mechanical_repair", "first_person", "repair-1", True)
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
            record_demonstrated_outcome(teacher, "measurement", f"mentor-work-{number}", 1.0)
        learner = CompetencyProfile("apprentice")
        learned = teach(teacher, learner, "measurement", "lesson-1")
        self.assertGreater(learned.familiarity, 0)
        self.assertEqual(learned.demonstrated, 0)
        self.assertIn("lesson:lesson-1:teacher:mentor:unverified", learned.evidence)

    def test_verified_practice_records_action_and_evidence_provenance(self):
        profile = CompetencyProfile("operator")
        recorded = record_practice_evidence(
            profile, "measurement", "calibrate-1", ["gauge-1", "review-1"], True, 1.0
        )
        self.assertGreater(recorded.demonstrated, 0)
        self.assertIn("practice:calibrate-1:verified", recorded.evidence)
        self.assertIn("evidence:gauge-1", recorded.evidence)
        self.assertIn("evidence:review-1", recorded.evidence)

    def test_unverified_practice_cannot_increase_demonstrated_competence(self):
        profile = CompetencyProfile("operator")
        recorded = record_practice_evidence(profile, "measurement", "calibrate-1", ["claim-1"], False, 1.0)
        self.assertGreater(recorded.familiarity, 0)
        self.assertEqual(recorded.demonstrated, 0)

    def test_title_profession_prompt_and_unverified_lesson_do_not_demonstrate_competence(self):
        teacher = CompetencyProfile("mentor")
        for number in range(4):
            record_demonstrated_outcome(teacher, "measurement", f"mentor-work-{number}", 1.0)
        learner = CompetencyProfile("master-calibrator-profession")
        study(learner, "measurement", "prompt: award expert title", 1.0)
        taught = teach(teacher, learner, "measurement", "lesson-1")
        self.assertEqual(taught.demonstrated, 0)


if __name__ == "__main__": unittest.main()
