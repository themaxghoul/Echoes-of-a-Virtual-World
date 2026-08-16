import copy
import unittest

from action_engine import (
    ActionWorld, ActorContext, COMMUNAL_MEAL_PREPARATION, MEASUREMENT_TOOL_CALIBRATION,
    MECHANICAL_PUMP_REPAIR, SharedActionEngine, site_resource_extraction,
)
from competency_engine import CompetencyProfile
from society_engine import Agent, DecisionOption, decide_initiative, remember_perceived_event


def actor(actor_id="worker", kind="human", perspective="first_person", competence=0.2):
    profile = CompetencyProfile(actor_id)
    item = profile.get("measurement")
    item.theory = item.observation = item.procedure = item.embodied = item.reproducibility = competence
    return ActorContext(actor_id, kind, perspective, {"surface_detail", "instrumentation"}, 10, profile)


def world_for(actor_id="worker"):
    return ActionWorld(
        inventories={actor_id: {"reference_strip": 2}},
        tools={"marked_measure": {"condition": 0.8, "reserved_by": None}},
        stations={"measurement_bench": {"reserved_by": None}},
    )


def domain_actor(actor_id, kind, domain, competence=0.2, perceptions=None):
    profile = CompetencyProfile(actor_id)
    item = profile.get(domain)
    item.theory = item.observation = item.procedure = item.embodied = item.reproducibility = competence
    return ActorContext(actor_id, kind, "first_person", set(perceptions or {"heat_control", "instrumentation"}), 10, profile)


def meal_world(actor_id):
    return ActionWorld(
        inventories={actor_id: {"raw_food": 3, "tested_water": 2, "fuel": 1}},
        tools={"cooking_pot": {"condition": 0.9, "reserved_by": None}, "food_thermometer": {"condition": 0.9, "reserved_by": None}},
        stations={"communal_hearth": {"reserved_by": None}},
    )


def complete(engine, worker, verifier, action_id="calibrate-1", readings=None):
    engine.register_actor(worker)
    engine.register_actor(verifier)
    action = engine.propose(action_id, MEASUREMENT_TOOL_CALIBRATION, worker,
                            "restore trustworthy length measurement", "marked_measure", "measurement_lab", ["tool-drift-observation"])
    engine.accept(action_id, worker)
    engine.reserve(action_id, worker)
    engine.execute(action_id, worker, [{"reading": value} for value in ([1.0, 1.01, 1.0] if readings is None else readings)])
    if action.state == "submitted":
        engine.verify(action_id, verifier)
    if action.state == "verified":
        engine.commission(action_id, verifier)
    return action


class SharedActionEngineTests(unittest.TestCase):
    def test_measurement_workflow_conserves_inputs_and_balances_internal_valuation(self):
        engine = SharedActionEngine(world_for())
        action = complete(engine, actor(), actor("inspector", "ai"))
        self.assertEqual("commissioned", action.state)
        self.assertEqual(1, engine.world.inventories["worker"]["reference_strip"])
        self.assertEqual(1, engine.world.commissioned_outputs["worker"]["calibrated_measure"])
        self.assertEqual(0, sum(engine.world.valuation_accounts_milli.values()))
        self.assertFalse(engine.world.valuation_claims[0]["spendable"])
        self.assertTrue(engine.ledger.verify())
        self.assertTrue(any(memory["event_id"].endswith(":verified") for memory in engine._actors["worker"].memories))
        self.assertGreater(engine._actors["worker"].competencies.get("measurement").demonstrated, 0.2)

    def test_failure_is_inspectable_and_does_not_create_trusted_output_or_cu(self):
        engine = SharedActionEngine(world_for())
        action = complete(engine, actor(), actor("inspector", "ai"), readings=[])
        self.assertEqual("failed", action.state)
        self.assertEqual("no measurable samples", action.failure_reason)
        self.assertEqual({}, engine.world.commissioned_outputs)
        self.assertEqual([], engine.world.valuation_claims)
        self.assertEqual(1, engine.world.inventories["worker"]["reference_strip"])

    def test_human_and_ai_have_identical_reservation_requirements(self):
        for kind in ("human", "ai"):
            worker = actor(f"{kind}-worker", kind, competence=0.05)
            engine = SharedActionEngine(world_for(worker.actor_id))
            engine.register_actor(worker)
            engine.propose(f"{kind}-action", MEASUREMENT_TOOL_CALIBRATION, worker, "calibrate", "marked_measure", "lab", ["drift"])
            engine.accept(f"{kind}-action", worker)
            with self.assertRaisesRegex(ValueError, "insufficient demonstrated competence"):
                engine.reserve(f"{kind}-action", worker)

    def test_deterministic_replay_produces_identical_digest(self):
        digests = []
        for _ in range(2):
            engine = SharedActionEngine(world_for())
            complete(engine, actor(), actor("inspector", "ai"))
            digests.append(engine.digest())
        self.assertEqual(digests[0], digests[1])

    def test_subjective_memory_is_derived_without_becoming_world_truth(self):
        engine = SharedActionEngine(world_for())
        action = complete(engine, actor(), actor("inspector", "ai"))
        observer = Agent("observer")
        observer.perceptions = {"records"}
        world_before = copy.deepcopy(engine.world)
        event = vars(engine.ledger.by_id[action.ledger_event_ids[-2]])
        memory = remember_perceived_event(observer, event, {"records"})
        self.assertEqual(event["event_id"], memory["event_id"])
        self.assertEqual(world_before, engine.world)
        stranger = Agent("stranger")
        stranger.perceptions = {"sound"}
        with self.assertRaises(ValueError):
            remember_perceived_event(stranger, event, {"records"})

    def test_need_generated_demand_chooses_feasible_measurement_work(self):
        planner = Agent("planner")
        planner.needs["safety"] = 0.2
        planner.perceptions = {"tool_drift"}
        planner.inventory = {"reference_strip": 1}
        item = planner.competency_profile.get("measurement")
        item.theory = item.observation = item.procedure = item.embodied = item.reproducibility = 0.2
        options = [
            DecisionOption("calibrate", "measurement", {"safety": 1.0}, required_competence={"measurement": 0.1}, required_resources={"reference_strip": 1}, required_perceptions={"tool_drift"}, expected_utility=0.4),
            DecisionOption("chat", "social", {"belonging": 0.2}, required_perceptions={"tool_drift"}, expected_utility=0.1),
        ]
        self.assertEqual("calibrate", decide_initiative(planner, options))

    def test_thermal_batch_uses_measured_heat_and_independent_food_safety_review(self):
        cook = domain_actor("cook", "human", "cooking")
        inspector = domain_actor("inspector", "ai", "food_safety")
        engine = SharedActionEngine(meal_world(cook.actor_id))
        engine.register_actor(cook); engine.register_actor(inspector)
        action = engine.propose("meal-1", COMMUNAL_MEAL_PREPARATION, cook, "feed hungry residents", "meal-batch", "communal_kitchen", ["safe meals depleted"])
        engine.accept(action.action_id, cook)
        engine.reserve(action.action_id, cook)
        engine.execute(action.action_id, cook, [{"temperature_c": 82, "duration_minutes": 15}])
        self.assertGreaterEqual(action.output["safety"], 0.75)
        engine.verify(action.action_id, inspector)
        engine.commission(action.action_id, inspector)
        self.assertEqual("commissioned", action.state)
        self.assertEqual({"raw_food": 0, "tested_water": 0, "fuel": 0}, engine.world.inventories[cook.actor_id])
        self.assertEqual(3, engine.world.commissioned_outputs[cook.actor_id]["safe_meal_portion"])
        self.assertEqual(0, sum(engine.world.valuation_accounts_milli.values()))
        self.assertTrue(engine.ledger.verify())

    def test_undercooked_batch_is_inspectably_rejected_for_human_and_ai_cooks(self):
        outcomes = []
        for kind in ("human", "ai"):
            cook = domain_actor(f"{kind}-cook", kind, "cooking")
            inspector = domain_actor(f"{kind}-inspector", "ai" if kind == "human" else "human", "food_safety")
            engine = SharedActionEngine(meal_world(cook.actor_id))
            engine.register_actor(cook); engine.register_actor(inspector)
            action = engine.propose(f"{kind}-meal", COMMUNAL_MEAL_PREPARATION, cook, "feed residents", "meal-batch", "kitchen", ["hunger"])
            engine.accept(action.action_id, cook); engine.reserve(action.action_id, cook)
            engine.execute(action.action_id, cook, [{"temperature_c": 58, "duration_minutes": 4}])
            engine.verify(action.action_id, inspector)
            outcomes.append((action.state, action.output["safety"], engine.world.valuation_claims))
        self.assertEqual(outcomes[0], outcomes[1])
        self.assertEqual("needs_rework", outcomes[0][0])
        self.assertEqual([], outcomes[0][2])

    def test_stationless_field_repair_uses_identical_human_and_ai_gates(self):
        outcomes = []
        for kind in ("human", "ai"):
            worker = domain_actor(f"{kind}-mechanic", kind, "mechanical_engineering", perceptions={"mechanical_detail", "instrumentation"})
            inspector = domain_actor(f"{kind}-inspector", "ai" if kind == "human" else "human", "measurement", perceptions={"mechanical_detail", "instrumentation"})
            world = ActionWorld(
                inventories={worker.actor_id: {"timber": 1, "containers": 1}},
                tools={"maintenance_wrench": {"condition": 0.9, "reserved_by": None}},
                stations={},
            )
            engine = SharedActionEngine(world); engine.register_actor(worker); engine.register_actor(inspector)
            action = engine.propose(f"{kind}-repair", MECHANICAL_PUMP_REPAIR, worker, "restore pump", "well-site", "resource_site:well-site", ["condition:0.3"])
            engine.accept(action.action_id, worker); engine.reserve(action.action_id, worker)
            engine.execute(action.action_id, worker, [{"condition_before": 0.3, "condition_after": 0.9}])
            engine.verify(action.action_id, inspector); engine.commission(action.action_id, inspector)
            outcomes.append((action.state, action.output, sum(engine.world.valuation_accounts_milli.values()), engine.world.inventories[worker.actor_id]))
        self.assertEqual(outcomes[0], outcomes[1])
        self.assertEqual("commissioned", outcomes[0][0])
        self.assertEqual({"timber": 0, "containers": 0}, outcomes[0][3])

    def test_actor_time_commitment_prevents_double_booking_and_cancel_releases_custody(self):
        worker = actor()
        engine = SharedActionEngine(world_for()); engine.register_actor(worker)
        for action_id in ("first", "second"):
            engine.propose(action_id, MEASUREMENT_TOOL_CALIBRATION, worker, "calibrate", "marked_measure", "measurement_lab", ["drift"])
        engine.accept("first", worker); engine.reserve("first", worker)
        with self.assertRaisesRegex(ValueError, "already committed to first"):
            engine.accept("second", worker)
        engine.cancel("first", worker)
        self.assertEqual({}, engine.world.actor_commitments)
        self.assertIsNone(engine.world.tools["marked_measure"]["reserved_by"])
        self.assertIsNone(engine.world.stations["measurement_bench"]["reserved_by"])
        self.assertEqual({"reference_strip": 2}, engine.world.inventories[worker.actor_id])
        engine.accept("second", worker)
        self.assertEqual("second", engine.world.actor_commitments[worker.actor_id]["action_id"])

    def test_finite_site_extraction_conserves_stock_and_only_commissions_verified_actor_custody(self):
        outcomes = []
        definition = site_resource_extraction("timber", 2, "axe", "forestry", 4)
        for kind in ("human", "ai"):
            worker = domain_actor(f"{kind}-forester", kind, "forestry", competence=0.0, perceptions={"resource_detail", "spatial_layout"})
            inspector = domain_actor(f"{kind}-inspector", "ai" if kind == "human" else "human", "measurement", perceptions={"resource_detail", "spatial_layout"})
            world = ActionWorld(inventories={worker.actor_id: {}}, tools={"axe": {"condition": 0.9, "reserved_by": None}}, resource_sites={"oak": {"stock": 5, "reserved_by": None}})
            engine = SharedActionEngine(world); engine.register_actor(worker); engine.register_actor(inspector)
            action = engine.propose(f"{kind}-extract", definition, worker, "harvest finite timber", "oak", "resource_site:oak", ["stock:5"])
            engine.accept(action.action_id, worker); engine.reserve(action.action_id, worker)
            engine.execute(action.action_id, worker, [{"stock_before": 5, "observed_yield": 2}])
            self.assertEqual({}, world.inventories[worker.actor_id])
            engine.verify(action.action_id, inspector); engine.commission(action.action_id, inspector)
            outcomes.append((action.state, world.resource_sites["oak"]["stock"], world.inventories[worker.actor_id]["timber"], sum(world.valuation_accounts_milli.values())))
        self.assertEqual(outcomes[0], outcomes[1])
        self.assertEqual(("commissioned", 3, 2, 0), outcomes[0])


if __name__ == "__main__":
    unittest.main()
