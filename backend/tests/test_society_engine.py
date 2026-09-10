import unittest

from competency_engine import record_demonstrated_outcome

from society_engine import (
    Agent,
    DecisionContext,
    DecisionOption,
    Knowledge,
    Observation,
    decision_context,
    dependency_market,
    perceive,
    practice,
    priority,
    score_option,
    specialize,
    teach,
    tick_survival,
)


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

    def test_specialization_projects_demonstrated_evidence_into_scarcity_and_dependency(self):
        smith, grower = Agent("smith"), Agent("grower")
        for _ in range(8):
            record_demonstrated_outcome(smith.competency_profile, "metallurgy", "smith-work", 1.0)
            record_demonstrated_outcome(grower.competency_profile, "agriculture", "grow-work", 1.0)
        before = dict(smith.specialties)
        self.assertEqual(specialize(smith, "metallurgy", 1.0), before["metallurgy"])
        self.assertEqual(smith.specialties, before)
        grower.needs["shelter"] = 0.2
        market = dependency_market([smith, grower])
        self.assertIn("shelter", market["unmet_needs"])
        self.assertIn("metallurgy", market["scarce_specialties"])

    def test_unperceived_water_failure_does_not_change_decision_score(self):
        ada = Agent("ada")
        repair = DecisionOption("repair-pump", "craft", addressed_needs={"hydration": 1.0})
        visible = decision_context(perceived_needs={"hydration": 0.8})
        hidden = decision_context(
            perceived_needs={"hydration": 0.8}, authoritative_only={"pump_failure": 1.0}
        )
        self.assertEqual(score_option(ada, repair, visible), score_option(ada, repair, hidden))

    def test_personality_components_name_real_decision_factors(self):
        ada = Agent("ada")
        repair = DecisionOption("repair-pump", "craft")
        score = score_option(ada, repair, decision_context())
        self.assertEqual(
            set(score.personality),
            {"diligence", "sociability", "caution", "curiosity", "cooperation"},
        )

    def test_legacy_personality_is_normalized_to_defined_traits(self):
        ada = Agent("ada", personality={"cooperative": 0.7, "social": 0.4})
        context = DecisionContext(personality=ada.personality)
        self.assertEqual(context.personality["cooperation"], 0.7)
        self.assertEqual(context.personality["sociability"], 0.4)
        self.assertNotIn("cooperative", context.personality)

    def test_unknown_action_category_modifier_is_rejected(self):
        ada = Agent("ada")
        unexplained = DecisionOption("do-unknown", "unmapped-category")
        with self.assertRaisesRegex(ValueError, "Unknown action category"):
            score_option(ada, unexplained, decision_context())

    def test_decision_score_has_complete_named_breakdown(self):
        ada = Agent("ada")
        option = DecisionOption("repair-pump", "craft")
        score = score_option(ada, option, decision_context())
        self.assertEqual(
            set(score.components),
            {"need", "goal", "competence", "relationship", "resource", "risk", "utility", "obligation", "personality"},
        )


if __name__ == "__main__":
    unittest.main()
