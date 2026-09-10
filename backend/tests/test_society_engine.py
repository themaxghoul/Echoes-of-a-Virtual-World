import unittest

from competency_engine import record_demonstrated_outcome, register_evidence

from society_engine import (
    Agent,
    DecisionContext,
    DecisionOption,
    Knowledge,
    Observation,
    decision_context,
    decide_initiative,
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
        self.assertEqual(taught.provenance, ["taught_by:mentor:unverified"])

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
            register_evidence(smith.competency_profile, "smith-work", "smith-work", "verified", "fixture")
            register_evidence(grower.competency_profile, "grow-work", "grow-work", "verified", "fixture")
            record_demonstrated_outcome(smith.competency_profile, "metallurgy", "verified-action:smith-work:evidence:smith-work", 1.0)
            record_demonstrated_outcome(grower.competency_profile, "agriculture", "verified-action:grow-work:evidence:grow-work", 1.0)
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

    def test_option_risk_and_utility_metadata_cannot_change_perceived_score(self):
        ada = Agent("ada")
        context = decision_context(risks={"repair-pump": 0.2}, utilities={"repair-pump": 0.3})
        safe_metadata = DecisionOption("repair-pump", "craft", risk=0.0, expected_utility=0.0)
        hidden_metadata = DecisionOption("repair-pump", "craft", risk=1.0, expected_utility=1.0)
        self.assertEqual(score_option(ada, safe_metadata, context), score_option(ada, hidden_metadata, context))

    def test_legacy_teaching_and_unverified_practice_only_create_familiarity(self):
        teacher = Agent("mentor", knowledge={"metallurgy": Knowledge("metallurgy", 0.55, 0.8)})
        learner = Agent("learner")
        taught = teach(teacher, learner, "metallurgy", 1.0)
        practiced = practice(Agent("trainee"), "coil winding", False)
        self.assertEqual(taught.competence, 0)
        self.assertGreater(taught.familiarity, 0)
        self.assertEqual(practiced.competence, 0)
        self.assertGreater(practiced.familiarity, 0)

    def test_unknown_categories_are_rejected_before_feasibility_filters(self):
        agent = Agent("ada")
        hidden = DecisionOption("unknown", "unmapped-category", required_perceptions={"unseen"})
        with self.assertRaisesRegex(ValueError, "Unknown action category"):
            decide_initiative(agent, [hidden])

    def test_specialize_does_not_create_an_empty_competency_record(self):
        agent = Agent("ada")
        self.assertEqual(specialize(agent, "measurement", 1.0), 0)
        self.assertEqual(agent.competency_profile.competencies, {})


if __name__ == "__main__":
    unittest.main()
