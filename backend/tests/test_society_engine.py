import unittest

from society_engine import Agent, Knowledge, Observation, dependency_market, perceive, practice, priority, specialize, teach, tick_survival


class SocietyEngineTests(unittest.TestCase):
    def test_agents_begin_without_domain_knowledge(self):
        self.assertEqual(Agent("new-mind").knowledge, {})

    def test_perspective_limits_direct_discovery(self):
        agent = Agent("observer")
        perceive(agent, Observation("beam crack", "surface_detail", "first_person", 0.8, "beam-7"))
        with self.assertRaises(ValueError):
            perceive(agent, Observation("beam crack", "surface_detail", "isometric", 0.8, "beam-7"))

    def test_teaching_cannot_exceed_teacher_competence(self):
        teacher = Agent("mentor", knowledge={"metallurgy": Knowledge("metallurgy", 0.55, 0.8)})
        learner = Agent("learner")
        taught = teach(teacher, learner, "metallurgy", 1.0)
        self.assertLessEqual(taught.competence, 0.55)
        self.assertEqual(taught.provenance, ["taught_by:mentor"])

    def test_verified_practice_reproduces_knowledge(self):
        result = practice(Agent("researcher"), "coil winding", True)
        self.assertTrue(result.independently_reproduced)
        self.assertGreater(result.competence, 0)

    def test_survival_pressure_changes_priority_and_can_kill(self):
        agent = Agent("forager")
        agent.needs["nutrition"] = 0.02
        self.assertEqual(priority(agent), "secure:nutrition")
        tick_survival(agent)
        self.assertFalse(agent.alive)
        self.assertEqual(priority(agent), "archived")

    def test_specialization_creates_scarcity_and_dependency(self):
        smith, grower = Agent("smith"), Agent("grower")
        for _ in range(8):
            specialize(smith, "metallurgy", 1.0)
            specialize(grower, "agriculture", 1.0)
        grower.needs["shelter"] = 0.2
        market = dependency_market([smith, grower])
        self.assertIn("shelter", market["unmet_needs"])
        self.assertIn("metallurgy", market["scarce_specialties"])


if __name__ == "__main__":
    unittest.main()
