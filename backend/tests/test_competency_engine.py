import unittest
from competency_engine import CompetencyProfile, can_attempt, observe, practice, reproduce_experiment, study, teach


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


if __name__ == "__main__": unittest.main()
