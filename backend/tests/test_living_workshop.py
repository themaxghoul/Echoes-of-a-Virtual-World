import json
import unittest

from causal_ledger import CausalEvent, CausalLedger
from persistent_world import (
    _process_living_workshop,
    actor_event_view,
    actor_world_view,
    apply_shared_action_command,
    founding_table_seed,
    migrate_state,
    reduce_world_tick,
)


def alpha34_fixture_state():
    state = migrate_state(founding_table_seed(123_456))
    state["schema"] = 31
    state.pop("installations", None)
    state.pop("living_workshop", None)
    state["places"].pop("settlement-water-installation", None)
    state["resources"].pop("seal_material", None)
    state["resources"].pop("fasteners", None)
    state["shared_actions"]["tools"].pop("calibrated_measure", None)
    state["shared_actions"]["stations"].pop("settlement-water-installation", None)
    state["clock"].update({"tick": 73, "minute": 913})
    state["discoveries"]["ada"] = {
        "9,7": {"level": "surface", "discovered_tick": 7},
        "10,7": {"level": "surveyed", "discovered_tick": 12},
    }
    state["npcs"]["ada"]["inventory"]["seal_material"] = 3
    ledger = CausalLedger()
    event = ledger.append(CausalEvent(
        event_id="alpha34-history:1:proposed",
        sequence=1,
        tick=72,
        event_type="shared_action",
        actor_id="ada",
        action_id="alpha34-history",
        state="proposed",
        intent="preserve historical work",
        location="measurement_lab",
        evidence=[{"kind": "historical_fixture"}],
    ))
    state["shared_actions"]["ledger"].append(vars(event).copy())
    return state


class LivingWorkshopTests(unittest.TestCase):
    def workshop_state(self):
        state = migrate_state(founding_table_seed(123_456))
        location = state["places"][state["installations"]["water"]["location"]]["location"]
        for npc in state["npcs"].values():
            npc["location"] = [0, 0]
        state["npcs"]["ada"]["location"] = list(location)
        return state

    def repair_records(self, state):
        return [
            record for record in state["shared_actions"]["records"].values()
            if record["definition"]["action_type"] == "repair_water_installation"
        ]

    def add_player(self, state, player_id, location, *, region="settlement", measurement=0.0):
        state["players"][player_id] = {
            "id": player_id,
            "name": player_id,
            "location": list(location),
            "current_region": region,
            "needs": {"hydration": 65.0, "safety": 70.0},
            "inventory": {},
            "equipment": {},
            "competency_records": ({
                "measurement": {"demonstrated": measurement, "provenance": [f"fixture:{player_id}:measurement"]}
            } if measurement else {}),
            "relationships": {},
            "memories": [],
            "energy": 100.0,
        }
        return state["players"][player_id]

    def test_alpha34_save_migrates_living_workshop_without_losing_history(self):
        before = alpha34_fixture_state()
        self.assertEqual(31, before["schema"])
        self.assertNotIn("installations", before)
        self.assertNotIn("living_workshop", before)
        self.assertNotIn("settlement-water-installation", before["places"])
        self.assertNotIn("calibrated_measure", before["shared_actions"]["tools"])
        self.assertTrue(CausalLedger([CausalEvent(**event) for event in before["shared_actions"]["ledger"]]).verify())
        expected = {
            "clock": json.loads(json.dumps(before["clock"])),
            "discoveries": json.loads(json.dumps(before["discoveries"])),
            "npcs": json.loads(json.dumps(before["npcs"])),
            "resources": json.loads(json.dumps(before["resources"])),
            "ledger": json.loads(json.dumps(before["shared_actions"]["ledger"])),
        }

        after = migrate_state(before)

        self.assertEqual(32, after["schema"])
        self.assertEqual(expected["clock"], after["clock"])
        self.assertEqual(expected["discoveries"], after["discoveries"])
        self.assertEqual(expected["npcs"], after["npcs"])
        self.assertEqual(expected["resources"]["water"], after["resources"]["water"])
        self.assertEqual(expected["ledger"], after["shared_actions"]["ledger"])
        self.assertIn("water", after["installations"])
        water = after["installations"]["water"]
        self.assertIn("condition", water)
        self.assertIn("service_capacity_liters", water)
        self.assertIn("remaining_service_liters", water)
        self.assertIn("measurement_history", water)
        self.assertIn("maintenance_interval_ticks", water)
        self.assertNotIn("diagnosis", water)
        self.assertEqual([], after["living_workshop"]["demands"])
        self.assertEqual([], after["living_workshop"]["work_orders"])
        self.assertEqual([], after["living_workshop"]["measurements"])
        self.assertEqual([], after["living_workshop"]["recent_outcomes"])

    def test_declining_flow_creates_one_idempotent_evidence_backed_demand_and_action(self):
        state = self.workshop_state()
        water = state["installations"]["water"]
        water["condition"] = 0.75

        first_events = _process_living_workshop(state, 1)
        second_events = _process_living_workshop(state, 2)

        self.assertTrue(any(event["type"] == "living_workshop_demand_created" for event in first_events))
        self.assertFalse(any(event["type"] == "living_workshop_demand_created" for event in second_events))
        self.assertEqual(1, len(state["living_workshop"]["demands"]))
        self.assertEqual(1, len(state["living_workshop"]["work_orders"]))
        self.assertEqual(1, len(self.repair_records(state)))
        demand = state["living_workshop"]["demands"][0]
        order = state["living_workshop"]["work_orders"][0]
        action = self.repair_records(state)[0]
        evidence_ids = demand["perceived_evidence_ids"]
        self.assertEqual(evidence_ids, order["perceived_evidence_ids"])
        self.assertEqual(evidence_ids, action["perceived_evidence_ids"])
        self.assertEqual(evidence_ids, action["observations"])
        self.assertEqual(order["canonical_action_id"], action["id"])
        self.assertIn("components", order["decision_explanation"])
        self.assertIn("total", order["decision_explanation"])
        self.assertIn("declining_flow", demand["symptoms"])
        projected = json.dumps({"demand": demand, "order": order, "observations": action["observations"]})
        self.assertNotIn("condition", projected)
        self.assertNotIn("diagnosis", projected)

    def test_unsafe_quality_creates_demand_from_local_instrument_evidence(self):
        state = self.workshop_state()
        water = state["installations"]["water"]
        water["condition"] = 1.0
        water["contamination_index"] = 0.2

        _process_living_workshop(state, 1)

        self.assertEqual(1, len(state["living_workshop"]["demands"]))
        demand = state["living_workshop"]["demands"][0]
        self.assertIn("unsafe_quality", demand["symptoms"])
        evidence = state["living_workshop"]["measurements"][-1]
        self.assertIn(demand["proposer_id"], evidence["perceived_by"])
        self.assertEqual([evidence["id"]], demand["perceived_evidence_ids"])

    def test_visible_flow_does_not_reveal_unmeasured_quality_to_an_untrained_observer(self):
        state = self.workshop_state()
        location = state["places"][state["installations"]["water"]["location"]]["location"]
        state["npcs"]["ada"]["location"] = [0, 0]
        state["npcs"]["orin"]["location"] = list(location)
        state["installations"]["water"].update({"condition": 0.75, "contamination_index": 0.2})

        _process_living_workshop(state, 1)

        demand = state["living_workshop"]["demands"][0]
        self.assertEqual("orin", demand["proposer_id"])
        self.assertIn("declining_flow", demand["symptoms"])
        self.assertNotIn("unsafe_quality", demand["symptoms"])
        self.assertNotIn("low_pressure", demand["symptoms"])

    def test_actor_views_redact_hidden_installation_state_and_unperceived_measurements(self):
        state = self.workshop_state()
        location = state["places"][state["installations"]["water"]["location"]]["location"]
        state["npcs"]["ada"]["location"] = [0, 0]
        self.add_player(state, "local-untrained", location)
        self.add_player(state, "distant-observer", [0, 0])
        state["installations"]["water"].update({"condition": 0.75, "contamination_index": 0.2})
        events = _process_living_workshop(state, 1)
        measurement_event = next(event for event in events if event["type"] == "living_workshop_measurement")
        snapshot = {"world_id": "fixture", "revision": 1, "tick": 1, "state": state}

        distant = actor_world_view(snapshot, "distant-observer")["state"]
        local = actor_world_view(snapshot, "local-untrained")["state"]
        distant_event = actor_event_view(measurement_event, snapshot, "distant-observer")
        local_event = actor_event_view(measurement_event, snapshot, "local-untrained")

        self.assertEqual({
            "id": "settlement-water-installation",
            "location": "settlement-water-installation",
            "region": "settlement",
        }, distant["installations"]["water"])
        self.assertEqual([], distant["living_workshop"]["measurements"])
        self.assertTrue(distant_event["payload"]["private"])
        self.assertNotIn("values", distant_event["payload"])
        self.assertEqual(["declining_flow"], local["living_workshop"]["measurements"][0]["symptoms"])
        self.assertEqual({"flow_lpm"}, set(local["living_workshop"]["measurements"][0]["values"]))
        self.assertNotIn("perceived_by", local["living_workshop"]["measurements"][0])
        self.assertEqual(["declining_flow"], local_event["payload"]["symptoms"])
        self.assertEqual({"flow_lpm"}, set(local_event["payload"]["values"]))

    def test_derived_demand_views_follow_the_viewers_measurement_channels(self):
        state = self.workshop_state()
        location = state["places"][state["installations"]["water"]["location"]]["location"]
        self.add_player(state, "local-untrained", location)
        self.add_player(state, "distant-untrained", [0, 0])
        state["installations"]["water"].update({"condition": 1.0, "contamination_index": 0.2})

        events = _process_living_workshop(state, 1)
        demand_event = next(event for event in events if event["type"] == "living_workshop_demand_created")
        demand = state["living_workshop"]["demands"][0]
        evidence_id = demand["perceived_evidence_ids"][0]
        self.assertEqual("ada", demand["proposer_id"])
        self.assertEqual(["unsafe_quality"], demand["symptoms"])
        state["living_workshop"]["recent_outcomes"].append({
            "tick": 1,
            "kind": "inspection_follow_up",
            "actor_id": "ada",
            "perceived_evidence_ids": [evidence_id],
            "reason": "unsafe_quality requires another instrument reading",
        })
        snapshot = {"world_id": "fixture", "revision": 1, "tick": 1, "state": state}

        authorized_snapshot = actor_world_view(snapshot, "ada")
        authorized_event = actor_event_view(demand_event, snapshot, "ada")
        authorized_workshop = authorized_snapshot["state"]["living_workshop"]
        authorized_projection = json.dumps({
            "living_workshop": authorized_workshop,
            "event": authorized_event,
        })
        self.assertEqual(["unsafe_quality"], authorized_workshop["demands"][0]["symptoms"])
        self.assertEqual([evidence_id], authorized_workshop["work_orders"][0]["perceived_evidence_ids"])
        self.assertEqual([evidence_id], authorized_workshop["recent_outcomes"][0]["perceived_evidence_ids"])
        self.assertEqual([evidence_id], authorized_event["payload"]["perceived_evidence_ids"])
        self.assertIn("unsafe_quality", authorized_projection)
        self.assertIn(evidence_id, authorized_projection)
        for viewer_id in ("local-untrained", "distant-untrained"):
            hidden_snapshot = actor_world_view(snapshot, viewer_id)
            hidden_event = actor_event_view(demand_event, snapshot, viewer_id)
            hidden_workshop = hidden_snapshot["state"]["living_workshop"]
            hidden_projection = json.dumps({
                "living_workshop": hidden_workshop,
                "event": hidden_event,
            })
            self.assertTrue(hidden_workshop["demands"][0]["private"])
            self.assertTrue(hidden_workshop["work_orders"][0]["private"])
            self.assertTrue(hidden_workshop["recent_outcomes"][0]["private"])
            self.assertNotIn("unsafe_quality", hidden_projection)
            self.assertNotIn(evidence_id, hidden_projection)
            self.assertTrue(hidden_event["payload"]["private"])

    def test_same_coordinates_in_another_region_do_not_create_direct_perception(self):
        state = self.workshop_state()
        location = state["places"][state["installations"]["water"]["location"]]["location"]
        state["npcs"]["ada"]["location"] = list(location)
        state["npcs"]["ada"]["current_region"] = "east_ridge"
        state["installations"]["water"]["condition"] = 0.75

        _process_living_workshop(state, 1)

        measurement = state["living_workshop"]["measurements"][0]
        self.assertEqual([], measurement["perceived_by"])
        self.assertEqual([], state["living_workshop"]["demands"])

    def test_repair_command_rejects_unowned_or_forged_measurement_evidence(self):
        state = self.workshop_state()
        for npc in state["npcs"].values():
            npc["location"] = [0, 0]
        state["installations"]["water"]["condition"] = 0.75
        _process_living_workshop(state, 1)
        measurement = state["living_workshop"]["measurements"][0]
        measurement["credible_recipients"] = ["orin"]
        target_id = state["installations"]["water"]["id"]

        forged = apply_shared_action_command(state, "orin", {
            "operation": "propose",
            "shared_action_id": "forged-water-repair",
            "action_type": "repair_water_installation",
            "target_id": target_id,
            "observations": ["invented low flow"],
            "perceived_evidence_ids": ["invented-measurement"],
        })
        unowned = apply_shared_action_command(state, "ada", {
            "operation": "propose",
            "shared_action_id": "unowned-water-repair",
            "action_type": "repair_water_installation",
            "target_id": target_id,
            "observations": [measurement["id"]],
            "perceived_evidence_ids": [measurement["id"]],
        })

        self.assertFalse(forged["accepted"])
        self.assertIn("perceived measurement evidence", forged["reason"])
        self.assertFalse(unowned["accepted"])
        self.assertIn("perceived measurement evidence", unowned["reason"])
        self.assertEqual([], self.repair_records(state))

    def test_repair_command_normalizes_evidence_and_deduplicates_installation_across_ids(self):
        state = self.workshop_state()
        for npc in state["npcs"].values():
            npc["location"] = [0, 0]
        state["installations"]["water"]["condition"] = 0.75
        _process_living_workshop(state, 1)
        measurement = state["living_workshop"]["measurements"][0]
        measurement["credible_recipients"] = ["ada", "orin"]
        target_id = state["installations"]["water"]["id"]
        first = apply_shared_action_command(state, "ada", {
            "operation": "propose",
            "shared_action_id": "first-water-repair",
            "action_type": "repair_water_installation",
            "target_id": target_id,
            "observations": [measurement["id"]],
            "perceived_evidence_ids": [measurement["id"]],
        })
        duplicate = apply_shared_action_command(state, "orin", {
            "operation": "propose",
            "shared_action_id": "second-water-repair",
            "action_type": "repair_water_installation",
            "target_id": target_id,
            "observations": [measurement["id"]],
            "perceived_evidence_ids": [measurement["id"]],
        })

        self.assertTrue(first["accepted"])
        self.assertEqual([measurement["id"]], first["record"]["observations"])
        self.assertFalse(duplicate["accepted"])
        self.assertEqual("first-water-repair", duplicate["existing_action_id"])
        self.assertEqual(1, len(self.repair_records(state)))

    def test_processor_reconciles_a_precreated_canonical_repair_record(self):
        state = self.workshop_state()
        for npc in state["npcs"].values():
            npc["location"] = [0, 0]
        state["installations"]["water"]["condition"] = 0.75
        _process_living_workshop(state, 1)
        measurement = state["living_workshop"]["measurements"][0]
        measurement["credible_recipients"] = ["ada"]
        target_id = state["installations"]["water"]["id"]
        precreated = apply_shared_action_command(state, "ada", {
            "operation": "propose",
            "shared_action_id": "precreated-water-repair",
            "action_type": "repair_water_installation",
            "target_id": target_id,
            "observations": [measurement["id"]],
            "perceived_evidence_ids": [measurement["id"]],
        })
        self.assertTrue(precreated["accepted"])

        _process_living_workshop(state, 2)

        self.assertEqual(1, len(state["living_workshop"]["demands"]))
        self.assertEqual(1, len(state["living_workshop"]["work_orders"]))
        self.assertEqual("precreated-water-repair", state["living_workshop"]["work_orders"][0]["canonical_action_id"])
        self.assertEqual(1, len(self.repair_records(state)))

    def test_healthy_water_creates_measurement_but_no_demand(self):
        state = self.workshop_state()
        state["installations"]["water"].update({"condition": 1.0, "contamination_index": 0.02})
        service_before = state["installations"]["water"]["remaining_service_liters"]

        _process_living_workshop(state, 1)

        self.assertLess(state["installations"]["water"]["condition"], 1.0)
        self.assertLess(state["installations"]["water"]["remaining_service_liters"], service_before)
        self.assertEqual(1, len(state["living_workshop"]["measurements"]))
        self.assertEqual([], state["living_workshop"]["measurements"][0]["symptoms"])
        self.assertEqual([], state["living_workshop"]["demands"])
        self.assertEqual([], state["living_workshop"]["work_orders"])
        self.assertEqual([], self.repair_records(state))

    def test_hidden_symptom_waits_for_perception_or_credible_evidence(self):
        state = self.workshop_state()
        for npc in state["npcs"].values():
            npc["location"] = [0, 0]
        state["installations"]["water"]["condition"] = 0.75

        _process_living_workshop(state, 1)

        self.assertEqual([], state["living_workshop"]["demands"])
        hidden_measurement = state["living_workshop"]["measurements"][-1]
        self.assertEqual([], hidden_measurement["perceived_by"])
        hidden_measurement["credible_recipients"] = ["ada"]

        _process_living_workshop(state, 2)

        self.assertEqual(1, len(state["living_workshop"]["demands"]))
        demand = state["living_workshop"]["demands"][0]
        self.assertEqual("ada", demand["proposer_id"])
        self.assertIn(hidden_measurement["id"], demand["perceived_evidence_ids"])

    def test_legacy_water_maintenance_does_not_open_a_second_work_order(self):
        state = self.workshop_state()
        water = state["installations"]["water"]
        water["condition"] = 0.75
        state["resource_sites"][water["id"]] = {
            "id": water["id"],
            "type": "well",
            "name": "legacy projection of workshop water",
            "region": "settlement",
            "location": list(state["places"][water["location"]]["location"]),
            "progress": 0,
            "stock": 0,
            "capacity": 24,
            "history": [],
            "installed_pump": {
                "design_id": "legacy-workshop-water",
                "installed_by": "ada",
                "condition": 0.5,
                "cycles": 12,
                "status": "operational",
                "maintenance_due": True,
                "maintenance_history": [],
            },
        }
        state["institutions"]["governance"]["maintenance_orders"].append({
            "id": "legacy-water-maintenance",
            "site_id": water["id"],
            "technology_id": "legacy-workshop-water",
            "opened_tick": 0,
            "status": "open",
            "condition": 0.5,
            "cycles": 12,
            "cause": "legacy adapter",
            "required_inputs": {},
            "required_tool": "wrench",
            "assigned_to": None,
            "assigned_tick": None,
            "blockers": [],
            "procurement_history": [],
            "depletion_notices": [],
        })

        reduce_world_tick(state, 1)

        repair_records = [
            record for record in state["shared_actions"]["records"].values()
            if record["definition"]["action_type"] in {"repair_water_installation", "repair_mechanical_pump"}
        ]
        self.assertEqual(["repair_water_installation"], [record["definition"]["action_type"] for record in repair_records])
        self.assertEqual(1, len(state["living_workshop"]["work_orders"]))
        legacy = state["institutions"]["governance"]["maintenance_orders"][0]
        self.assertEqual("projected_to_living_workshop", legacy["status"])
        self.assertEqual(state["living_workshop"]["work_orders"][0]["canonical_action_id"], legacy["canonical_action_id"])


if __name__ == "__main__":
    unittest.main()
