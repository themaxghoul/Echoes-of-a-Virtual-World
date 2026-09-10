import copy
import unittest

from action_engine import (
    ActionDefinition, ActionRequirements, ActionWorld, ActorContext, COMMUNAL_MEAL_PREPARATION, MEASUREMENT_TOOL_CALIBRATION,
    MECHANICAL_PUMP_REPAIR, SharedActionEngine, material_custody_transfer, site_resource_extraction,
)
from competency_engine import CompetencyProfile
from scenarios.living_workshop import WaterInstallationSpec, water_installation_repair
from society_engine import Agent, DecisionOption, decide_initiative, remember_perceived_event


def actor(actor_id="worker", kind="human", perspective="first_person", competence=0.2):
    profile = CompetencyProfile(actor_id)
    item = profile.get("measurement")
    item.theory = item.observation = item.procedure = item.embodied = item.reproducibility = competence
    return ActorContext(actor_id, kind, perspective, {"surface_detail", "instrumentation"}, 10, profile)


def world_for(actor_id="worker"):
    return ActionWorld(
        inventories={actor_id: {}}, communal_inventory={"reference_strip": 2},
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
        inventories={actor_id: {}}, communal_inventory={"raw_food": 3, "tested_water": 2, "fuel": 1},
        tools={"cooking_pot": {"condition": 0.9, "reserved_by": None}, "food_thermometer": {"condition": 0.9, "reserved_by": None}},
        stations={"communal_hearth": {"reserved_by": None}},
    )


def water_repair_world(actor_id, spec):
    return ActionWorld(
        inventories={actor_id: {}},
        communal_inventory={spec.seal_material: spec.seal_material_amount, spec.fastener_material: spec.fastener_amount},
        tools={
            spec.wrench_tool: {"condition": 0.9, "reserved_by": None},
            spec.calibrated_measure_tool: {"condition": 0.95, "reserved_by": None},
        },
        stations={spec.installation_site: {"reserved_by": None}},
    )


def water_measurement(flow_lpm=4.0, leak_rate_ml_min=240.0, contamination_index=0.36,
                      pressure_kpa=85.0, seal_alignment_mm=2.4):
    return {
        "flow_lpm": flow_lpm,
        "leak_rate_ml_min": leak_rate_ml_min,
        "contamination_index": contamination_index,
        "pressure_kpa": pressure_kpa,
        "seal_alignment_mm": seal_alignment_mm,
    }


def run_water_repair_to_submission(worker, samples=None):
    spec = WaterInstallationSpec()
    engine = SharedActionEngine(water_repair_world(worker.actor_id, spec))
    engine.register_actor(worker)
    action = engine.propose(
        f"{worker.actor_id}-water-repair", water_installation_repair(spec), worker,
        "restore safe water service", spec.installation_site, spec.installation_site,
        ["measured-low-flow", "measured-leak"],
    )
    engine.accept(action.action_id, worker)
    engine.reserve(action.action_id, worker)
    engine.execute(action.action_id, worker, [water_measurement()] if samples is None else samples)
    reconciliation = action.material_reconciliation
    return {
        "engine": engine,
        "action": action,
        "before": sum(item["before"] for item in reconciliation.values()),
        "consumed": sum(item["consumed"] for item in reconciliation.values()),
        "after": sum(item["after"] for item in reconciliation.values()),
        "installed": sum(item["installed"] for item in reconciliation.values()),
        "waste": sum(item["waste"] for item in reconciliation.values()),
        "recovered": sum(item["recovered"] for item in reconciliation.values()),
        "duration_ticks": action.completed_tick - action.accepted_tick,
        "state": action.state,
    }


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
    def test_scenario_evaluators_use_the_generic_execution_and_verification_lifecycle(self):
        def execute_evaluator(context):
            return {
                "succeeded": bool(context["samples"]),
                "output": {"observed_sample_count": len(context["samples"])},
                "evidence": [{"kind": "scenario_execution", "sample_count": len(context["samples"])}],
                "material_disposition": {},
            }

        def verify_evaluator(context):
            return {
                "passed": context["output"]["observed_sample_count"] == 1 and context["samples"] == [{"independent": 1.0}],
                "state": "rejected",
                "verification": {"independent_sample_count": len(context["samples"])},
                "evidence": [{"kind": "scenario_verification"}],
            }

        definition = ActionDefinition(
            action_type="scenario_evaluated_action",
            requirements=ActionRequirements(energy=1, perception_channels={"instrumentation"}),
            execution_evaluator=execute_evaluator,
            verification_evaluator=verify_evaluator,
        )
        worker, inspector = actor(), actor("inspector", "ai")
        engine = SharedActionEngine(ActionWorld(inventories={worker.actor_id: {}}))
        engine.register_actor(worker); engine.register_actor(inspector)
        action = engine.propose("scenario-evaluator", definition, worker, "record an observation", "target", "lab", ["observation"])
        engine.accept(action.action_id, worker); engine.reserve(action.action_id, worker)
        engine.execute(action.action_id, worker, [{"recorded": 1.0}])
        engine.verify(action.action_id, inspector, [{"independent": 1.0}])
        self.assertEqual("verified", action.state)
        self.assertEqual(1, action.output["observed_sample_count"])
        self.assertEqual(1, action.verification["independent_sample_count"])

    def test_measurement_workflow_conserves_inputs_and_balances_internal_valuation(self):
        engine = SharedActionEngine(world_for())
        action = complete(engine, actor(), actor("inspector", "ai"))
        self.assertEqual("commissioned", action.state)
        self.assertEqual(1, engine.world.communal_inventory["reference_strip"])
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
        self.assertEqual(1, engine.world.communal_inventory["reference_strip"])

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
        self.assertEqual({"raw_food": 0, "tested_water": 0, "fuel": 0}, engine.world.communal_inventory)
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
                inventories={worker.actor_id: {}}, communal_inventory={"timber": 1, "containers": 1},
                tools={"maintenance_wrench": {"condition": 0.9, "reserved_by": None}},
                stations={},
            )
            engine = SharedActionEngine(world); engine.register_actor(worker); engine.register_actor(inspector)
            action = engine.propose(f"{kind}-repair", MECHANICAL_PUMP_REPAIR, worker, "restore pump", "well-site", "resource_site:well-site", ["condition:0.3"])
            engine.accept(action.action_id, worker); engine.reserve(action.action_id, worker)
            engine.execute(action.action_id, worker, [{"condition_before": 0.3, "condition_after": 0.9}])
            engine.verify(action.action_id, inspector); engine.commission(action.action_id, inspector)
            outcomes.append((action.state, action.output, sum(engine.world.valuation_accounts_milli.values()), engine.world.communal_inventory))
        self.assertEqual(outcomes[0], outcomes[1])
        self.assertEqual("commissioned", outcomes[0][0])
        self.assertEqual({"timber": 0, "containers": 0}, outcomes[0][3])

    def test_water_repair_has_identical_human_and_ai_requirements(self):
        outcomes = []
        for kind in ("human", "ai"):
            worker = domain_actor(
                f"{kind}-worker", kind, "mechanical_repair",
                perceptions={"spatial_layout", "instrumentation"},
            )
            outcomes.append(run_water_repair_to_submission(worker))
        self.assertEqual(outcomes[0]["consumed"], outcomes[1]["consumed"])
        self.assertEqual(outcomes[0]["duration_ticks"], outcomes[1]["duration_ticks"])
        self.assertEqual(outcomes[0]["state"], "submitted")

    def test_water_repair_requires_mechanical_repair_evidence_not_engineering_proxy(self):
        worker = domain_actor(
            "engineer", "human", "mechanical_engineering",
            perceptions={"spatial_layout", "instrumentation"},
        )
        spec = WaterInstallationSpec()
        engine = SharedActionEngine(water_repair_world(worker.actor_id, spec))
        engine.register_actor(worker)
        action = engine.propose(
            "repair-domain", water_installation_repair(spec), worker,
            "restore safe water service", spec.installation_site, spec.installation_site,
            ["measured-low-flow"],
        )
        engine.accept(action.action_id, worker)
        with self.assertRaisesRegex(ValueError, "insufficient demonstrated competence"):
            engine.reserve(action.action_id, worker)

    def test_repair_material_reconciliation_balances(self):
        record = run_water_repair_to_submission(
            domain_actor("worker", "human", "mechanical_repair", perceptions={"spatial_layout", "instrumentation"})
        )
        self.assertEqual(record["before"] - record["consumed"], record["after"])
        self.assertEqual(record["consumed"], record["installed"] + record["waste"] + record["recovered"])

    def test_water_repair_without_pre_measurements_preserves_unused_materials(self):
        record = run_water_repair_to_submission(
            domain_actor("worker", "human", "mechanical_repair", perceptions={"spatial_layout", "instrumentation"}),
            samples=[],
        )
        self.assertEqual("failed", record["state"])
        self.assertEqual(record["before"], record["after"])
        self.assertEqual(0, record["consumed"])
        self.assertEqual({"seal_material": 2, "fasteners": 4}, record["engine"].world.communal_inventory)
        self.assertTrue(record["action"].material_reconciliation)

    def test_water_repair_records_lifecycle_ticks_and_is_deterministic_from_pre_measurements(self):
        worker = domain_actor("worker", "human", "mechanical_repair", perceptions={"spatial_layout", "instrumentation"})
        first = run_water_repair_to_submission(worker)
        replay_worker = domain_actor("worker", "human", "mechanical_repair", perceptions={"spatial_layout", "instrumentation"})
        second = run_water_repair_to_submission(replay_worker)
        self.assertEqual(first["action"].accepted_tick, 0)
        self.assertEqual(first["action"].completed_tick, first["action"].definition.requirements.duration_ticks)
        self.assertEqual(first["action"].output, second["action"].output)
        self.assertEqual(first["engine"].digest(), second["engine"].digest())

    def test_water_repair_verification_uses_independent_post_repair_measurements(self):
        worker = domain_actor("worker", "human", "mechanical_repair", perceptions={"spatial_layout", "instrumentation"})
        record = run_water_repair_to_submission(worker)
        inspector = domain_actor("inspector", "ai", "measurement", perceptions={"instrumentation"})
        engine = record["engine"]
        engine.register_actor(inspector)
        engine.verify(record["action"].action_id, inspector, [water_measurement(flow_lpm=1.0, leak_rate_ml_min=300.0)])
        self.assertEqual("rejected", record["action"].state)
        self.assertEqual("rejected", record["action"].verification["state"])
        self.assertIn("material_reconciliation", engine.ledger.events[-1].evidence[0])

    def test_water_repair_verification_accepts_post_repair_measurements_at_tolerance(self):
        worker = domain_actor("worker", "human", "mechanical_repair", perceptions={"spatial_layout", "instrumentation"})
        record = run_water_repair_to_submission(worker)
        inspector = domain_actor("inspector", "ai", "measurement", perceptions={"instrumentation"})
        engine = record["engine"]
        engine.register_actor(inspector)
        engine.verify(record["action"].action_id, inspector, [water_measurement(
            flow_lpm=12.0, leak_rate_ml_min=20.0, contamination_index=0.1,
            pressure_kpa=160.0, seal_alignment_mm=0.5,
        )])
        self.assertEqual("verified", record["action"].state)
        self.assertTrue(all(item["passed"] for item in record["action"].verification["tolerance_comparison"].values()))

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
        self.assertEqual({"reference_strip": 2}, engine.world.communal_inventory)
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

    def test_verified_material_deposit_conserves_actor_and_communal_custody_for_human_and_ai(self):
        outcomes = []
        definition = material_custody_transfer("stone", 1)
        for kind in ("human", "ai"):
            worker = domain_actor(f"{kind}-carrier", kind, "logistics", perceptions={"resource_detail", "spatial_layout"})
            inspector = domain_actor(f"{kind}-receiver", "ai" if kind == "human" else "human", "measurement", perceptions={"resource_detail", "spatial_layout"})
            world = ActionWorld(inventories={worker.actor_id: {"stone": 2}}, communal_inventory={"stone": 24})
            engine = SharedActionEngine(world); engine.register_actor(worker); engine.register_actor(inspector)
            action = engine.propose(f"{kind}-deposit", definition, worker, "deposit measured stone", "stone", "warehouse", ["actor-custody:stone:2"])
            engine.accept(action.action_id, worker); engine.reserve(action.action_id, worker)
            self.assertEqual(2, world.inventories[worker.actor_id]["stone"])
            engine.execute(action.action_id, worker, [{"custody_before": 2, "observed_amount": 1}])
            self.assertEqual(1, world.inventories[worker.actor_id]["stone"])
            self.assertEqual(24, world.communal_inventory["stone"])
            engine.verify(action.action_id, inspector); engine.commission(action.action_id, inspector)
            outcomes.append((action.state, world.inventories[worker.actor_id]["stone"], world.communal_inventory["stone"], sum(world.valuation_accounts_milli.values()), world.valuation_claims[0]["spendable"]))
        self.assertEqual(outcomes[0], outcomes[1])
        self.assertEqual(("commissioned", 1, 25, 0, False), outcomes[0])

    def test_cancelled_material_deposit_releases_reservation_without_moving_material(self):
        worker = domain_actor("carrier", "human", "logistics", perceptions={"resource_detail", "spatial_layout"})
        world = ActionWorld(inventories={worker.actor_id: {"timber": 3}}, communal_inventory={"timber": 10})
        engine = SharedActionEngine(world); engine.register_actor(worker)
        action = engine.propose("deposit-cancel", material_custody_transfer("timber", 2), worker, "deposit timber", "timber", "warehouse", ["actor-custody:timber:3"])
        engine.accept(action.action_id, worker); engine.reserve(action.action_id, worker); engine.cancel(action.action_id, worker)
        self.assertEqual({"timber": 3}, world.inventories[worker.actor_id])
        self.assertEqual({"timber": 10}, world.communal_inventory)


if __name__ == "__main__":
    unittest.main()
