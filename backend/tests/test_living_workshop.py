import json
import copy
import unittest

from causal_ledger import CausalEvent, CausalLedger
from persistent_world import (
    _process_living_workshop,
    _process_shared_actions,
    _process_teaching,
    _advance_autonomous_shared_actions,
    _advance_travel_routes,
    actor_event_view,
    actor_world_view,
    apply_shared_action_command,
    apply_player_action,
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
    def negotiated_state(self, actor_id="ada"):
        state = self.workshop_state()
        water = state["installations"]["water"]
        water["condition"] = 0.75
        state["npcs"]["ada"]["competency_records"]["mechanical_repair"] = {"demonstrated": 0.3, "provenance": ["fixture:verified-repair"]}
        state["npcs"]["orin"]["location"] = list(state["npcs"]["ada"]["location"])
        if actor_id not in state["npcs"]:
            player = self.add_player(state, actor_id, state["npcs"]["ada"]["location"], measurement=0.3)
            player["competency_records"]["mechanical_repair"] = {"demonstrated": 0.3, "provenance": ["fixture:verified-practice"]}
        _process_living_workshop(state, 1)
        order = state["living_workshop"]["work_orders"][0]
        return state, order

    def respond(self, state, order, actor_id="ada", accepted=True, reason=""):
        return apply_player_action(state, actor_id, {"type": "respond_work_order", "work_order_id": order["id"], "accepted": accepted, "reason": reason})

    def reserve_repair(self, state, order, actor_id="ada"):
        accepted = self.respond(state, order, actor_id)
        self.assertTrue(accepted["accepted"], accepted)
        action_id = order["canonical_action_id"]
        routed = apply_shared_action_command(state, actor_id, {"operation": "route", "shared_action_id": action_id})
        self.assertTrue(routed["accepted"], routed)
        reserved = apply_shared_action_command(state, actor_id, {"operation": "reserve", "shared_action_id": action_id})
        self.assertTrue(reserved["accepted"], reserved)
        return action_id

    def test_worker_can_refuse_and_another_actor_can_accept_same_order(self):
        state, order = self.negotiated_state()
        refused = self.respond(state, order, "orin", False, "risk exceeds my demonstrated competence")
        self.assertTrue(refused["accepted"], refused)
        history = copy.deepcopy(order["negotiations"])
        self.assertEqual("refused", refused["status"])
        accepted = self.respond(state, order)
        self.assertTrue(accepted["accepted"], accepted)
        self.assertEqual("ada", accepted["assigned_actor_id"])
        self.assertEqual(history, order["negotiations"][:len(history)])
        self.assertEqual("risk exceeds my demonstrated competence", history[-1]["reason"])
        self.assertEqual(order["canonical_action_id"], order["terms"]["canonical_action_id"])

    def test_player_acceptance_uses_same_commitment_and_canonical_actor(self):
        state, order = self.negotiated_state("player-worker")
        result = self.respond(state, order, "player-worker")
        self.assertTrue(result["accepted"], result)
        record = state["shared_actions"]["records"][order["canonical_action_id"]]
        self.assertEqual("player-worker", record["actor_id"])
        self.assertEqual("human", record["actor_kind"])
        self.assertEqual("accepted", record["state"])
        self.assertEqual(record["id"], state["shared_actions"]["actor_commitments"]["player-worker"]["action_id"])

    def test_negotiation_terms_and_responses_are_append_only(self):
        state, order = self.negotiated_state()
        for explanation in ["work after rest", "work after delivery"]:
            result = apply_player_action(state, "ada", {"type": "negotiate_work_order", "work_order_id": order["id"], "terms": {"note": explanation}})
            self.assertTrue(result["accepted"], result)
        self.assertEqual(["work after rest", "work after delivery"], [entry["terms"]["note"] for entry in order["negotiations"] if entry["kind"] == "proposal"])
        self.assertTrue(self.respond(state, order)["accepted"])
        frozen = copy.deepcopy(order["terms"])
        denied = apply_player_action(state, "orin", {"type": "negotiate_work_order", "work_order_id": order["id"], "terms": {"note": "override"}})
        self.assertFalse(denied["accepted"])
        self.assertEqual(frozen, order["terms"])

    def test_reservation_expiry_releases_all_resources_without_consumption(self):
        state, order = self.negotiated_state()
        action_id = self.reserve_repair(state, order)
        before = copy.deepcopy(state["resources"])
        reservation = state["shared_actions"]["reservations"][action_id]
        self.assertEqual("settlement-water-installation", reservation["site"])
        self.assertEqual("ada", reservation["actor_time"]["actor_id"])
        _process_shared_actions(state, reservation["expires_tick"])
        self.assertNotIn(action_id, state["shared_actions"]["reservations"])
        self.assertNotIn("ada", state["shared_actions"]["actor_commitments"])
        self.assertIsNone(state["shared_actions"]["tools"]["maintenance_wrench"]["reserved_by"])
        self.assertIsNone(state["shared_actions"]["stations"]["settlement-water-installation"]["reserved_by"])
        self.assertIsNone(state["installations"]["water"].get("reserved_by"))
        self.assertEqual(before, state["resources"])
        self.assertEqual("reservation_expired", order["blockers"][-1]["code"])

    def test_material_reservations_prevent_double_booking_without_debiting_stock(self):
        state, order = self.negotiated_state()
        state["resources"]["seal_material"] = 2
        action_id = self.reserve_repair(state, order)
        orin = state["npcs"]["orin"]
        orin["competency_records"]["measurement"] = {"demonstrated": 0.3, "provenance": ["fixture:verified-measurement"]}
        orin["location"] = list(state["places"]["measurement_lab"]["location"])
        proposal = apply_shared_action_command(state, "orin", {"operation": "propose", "shared_action_id": "other-material-user", "action_type": "calibrate_measurement_tool", "observations": ["tool drift"]})
        self.assertTrue(proposal["accepted"], proposal)
        second = state["shared_actions"]["records"]["other-material-user"]
        second["definition"]["requirements"]["materials"] = {"seal_material": 1}
        self.assertTrue(apply_shared_action_command(state, "orin", {"operation": "accept", "shared_action_id": second["id"]})["accepted"])
        result = apply_shared_action_command(state, "orin", {"operation": "reserve", "shared_action_id": second["id"]})
        self.assertFalse(result["accepted"])
        self.assertIn("materials", result["reason"])
        self.assertEqual(2, state["resources"]["seal_material"])
        self.assertTrue(apply_shared_action_command(state, "ada", {"operation": "cancel", "shared_action_id": action_id})["accepted"])
        self.assertTrue(apply_shared_action_command(state, "orin", {"operation": "reserve", "shared_action_id": second["id"]})["accepted"])

    def test_shortage_and_fatigue_stop_then_retry_after_supply_and_rest(self):
        for blocker in ["seal_material", "energy", "calibrated_measure", "competence"]:
            with self.subTest(blocker=blocker):
                state, order = self.negotiated_state()
                self.assertTrue(self.respond(state, order)["accepted"])
                if blocker == "seal_material":
                    state["resources"]["seal_material"] = 0
                elif blocker == "energy":
                    state["npcs"]["ada"]["energy"] = 0
                elif blocker == "competence":
                    state["npcs"]["ada"]["competency_records"]["mechanical_repair"]["demonstrated"] = 0
                else:
                    state["shared_actions"]["tools"][blocker]["condition"] = 0.1
                action_id = order["canonical_action_id"]
                result = apply_shared_action_command(state, "ada", {"operation": "reserve", "shared_action_id": action_id})
                self.assertFalse(result["accepted"])
                self.assertTrue(order["blockers"])
                self.assertNotIn("ada", state["shared_actions"]["actor_commitments"])
                self.assertTrue(order["recovery_options"])
                state["resources"]["seal_material"] = 4
                state["npcs"]["ada"]["energy"] = 80
                state["npcs"]["ada"]["competency_records"]["mechanical_repair"]["demonstrated"] = 0.3
                state["shared_actions"]["tools"]["calibrated_measure"]["condition"] = 0.9
                retry = apply_shared_action_command(state, "ada", {"operation": "reserve", "shared_action_id": action_id})
                self.assertTrue(retry["accepted"], retry)

    def test_execution_requires_approved_route_and_advances_one_segment_per_tick(self):
        state, order = self.negotiated_state()
        self.assertTrue(self.respond(state, order)["accepted"])
        actor = state["npcs"]["ada"]
        actor["location"] = [7, 8]
        action_id = order["canonical_action_id"]
        result = apply_shared_action_command(state, "ada", {"operation": "route", "shared_action_id": action_id})
        self.assertTrue(result["accepted"], result)
        route = actor["route"]
        self.assertGreater(len(route["path"]), 1)
        self.assertEqual([7, 8], actor["location"])
        _advance_travel_routes(state, 2)
        self.assertEqual(route["path"][1], actor["location"])
        _advance_travel_routes(state, 2)
        self.assertEqual(route["path"][1], actor["location"])
        for tick in range(3, 50):
            _advance_travel_routes(state, tick)
        self.assertEqual("arrived", route["status"])
        self.assertTrue(apply_shared_action_command(state, "ada", {"operation": "reserve", "shared_action_id": action_id})["accepted"])
        actor["route"] = None
        self.assertFalse(apply_shared_action_command(state, "ada", {"operation": "execute", "shared_action_id": action_id})["accepted"])

    def test_interrupted_execution_preserves_materials_and_consumed_time(self):
        state, order = self.negotiated_state()
        action_id = self.reserve_repair(state, order)
        self.assertTrue(apply_shared_action_command(state, "ada", {"operation": "execute", "shared_action_id": action_id})["accepted"])
        state["npcs"]["ada"]["energy"] = 0
        before = copy.deepcopy(state["resources"])
        _process_shared_actions(state, 2)
        record = state["shared_actions"]["records"][action_id]
        self.assertEqual("failed", record["state"])
        self.assertGreater(record["consumed_ticks"], 0)
        self.assertEqual(before, state["resources"])
        self.assertEqual({}, record["material_disposition"])
        self.assertNotIn(action_id, state["shared_actions"]["reservations"])
        state["npcs"]["ada"]["energy"] = 80
        self.assertTrue(self.respond(state, order)["accepted"])
        self.assertEqual("accepted", record["state"])
        self.assertGreater(record["consumed_ticks"], 0)

    def test_autonomous_worker_accepts_and_reports_missing_independent_verifier(self):
        state, order = self.negotiated_state()
        for actor_id, entity in state["npcs"].items():
            if actor_id != "ada":
                entity["competency_records"]["measurement"] = {"demonstrated": 0, "provenance": []}
        for tick in range(2, 18):
            state["clock"]["tick"] = tick
            _advance_travel_routes(state, tick)
            _process_shared_actions(state, tick)
            _advance_autonomous_shared_actions(state, tick)
        self.assertEqual("ada", order["assigned_actor_id"])
        self.assertEqual("submitted", state["shared_actions"]["records"][order["canonical_action_id"]]["state"])
        self.assertEqual("independent_verifier_unavailable", order["blockers"][-1]["code"])
        self.assertEqual(0.75 - 0.00025, state["installations"]["water"]["condition"])

    def test_rest_is_timed_and_allows_human_and_ai_to_retry(self):
        for actor_id in ("ada", "player-worker"):
            with self.subTest(actor_id=actor_id):
                state, order = self.negotiated_state(actor_id)
                self.assertTrue(self.respond(state, order, actor_id)["accepted"])
                actor = state["npcs"].get(actor_id) or state["players"][actor_id]
                actor["energy"] = 0
                action_id = order["canonical_action_id"]
                stopped = apply_shared_action_command(state, actor_id, {"operation": "reserve", "shared_action_id": action_id})
                self.assertFalse(stopped["accepted"])
                rested = apply_shared_action_command(state, actor_id, {"operation": "rest", "shared_action_id": action_id})
                self.assertTrue(rested["accepted"], rested)
                self.assertEqual(0, actor["energy"])
                _process_shared_actions(state, 1)
                self.assertEqual(2, actor["energy"])
                _process_shared_actions(state, 1)
                self.assertEqual(2, actor["energy"])
                for tick in range(2, 7):
                    _process_shared_actions(state, tick)
                self.assertTrue(apply_shared_action_command(state, actor_id, {"operation": "reserve", "shared_action_id": action_id})["accepted"])

    def test_cancel_in_progress_releases_resources_and_preserves_elapsed_work(self):
        state, order = self.negotiated_state()
        action_id = self.reserve_repair(state, order)
        self.assertTrue(apply_shared_action_command(state, "ada", {"operation": "execute", "shared_action_id": action_id})["accepted"])
        state["clock"]["tick"] = 2
        result = apply_shared_action_command(state, "ada", {"operation": "cancel", "shared_action_id": action_id})
        self.assertTrue(result["accepted"], result)
        self.assertEqual("cancelled", state["shared_actions"]["records"][action_id]["state"])
        self.assertEqual(2, state["shared_actions"]["records"][action_id]["consumed_ticks"])
        self.assertNotIn(action_id, state["shared_actions"]["reservations"])
        self.assertNotIn("ada", state["shared_actions"]["actor_commitments"])
        self.assertTrue(self.respond(state, order)["accepted"])
        self.assertNotEqual(action_id, order["canonical_action_id"])

    def test_spurious_execute_retry_cannot_release_running_work_resources(self):
        state, order = self.negotiated_state()
        action_id = self.reserve_repair(state, order)
        command = {"operation": "execute", "shared_action_id": action_id}
        self.assertTrue(apply_shared_action_command(state, "ada", command)["accepted"])
        rejected = apply_shared_action_command(state, "ada", command)
        self.assertFalse(rejected["accepted"])
        self.assertIn(action_id, state["shared_actions"]["reservations"])
        self.assertEqual("in_progress", state["shared_actions"]["records"][action_id]["state"])

    def test_spurious_reserve_retry_does_not_cancel_existing_reservation(self):
        state, order = self.negotiated_state()
        action_id = self.reserve_repair(state, order)
        rejected = apply_shared_action_command(state, "ada", {"operation": "reserve", "shared_action_id": action_id})
        self.assertFalse(rejected["accepted"])
        self.assertIn(action_id, state["shared_actions"]["reservations"])
        self.assertEqual("reserved", state["shared_actions"]["records"][action_id]["state"])

    def test_missing_material_during_execution_cannot_create_negative_stock(self):
        state, order = self.negotiated_state()
        action_id = self.reserve_repair(state, order)
        self.assertTrue(apply_shared_action_command(state, "ada", {"operation": "execute", "shared_action_id": action_id})["accepted"])
        state["resources"]["seal_material"] = 0
        _process_shared_actions(state, 1)
        self.assertEqual("failed", state["shared_actions"]["records"][action_id]["state"])
        self.assertEqual(0, state["resources"]["seal_material"])
        self.assertIsNone(state["installations"]["water"].get("reserved_by"))

    def test_abandoned_acceptance_expires_and_keeps_negotiation_history(self):
        state, order = self.negotiated_state()
        self.assertTrue(self.respond(state, order)["accepted"])
        history = copy.deepcopy(order["negotiations"])
        _process_shared_actions(state, 25)
        self.assertNotIn("ada", state["shared_actions"]["actor_commitments"])
        self.assertEqual("cancelled", state["shared_actions"]["records"][order["canonical_action_id"]]["state"])
        self.assertEqual(history, order["negotiations"])

    def test_negotiation_history_and_recovery_are_visible_only_to_participants(self):
        state, order = self.negotiated_state()
        self.assertTrue(self.respond(state, order, "orin", False, "my personal refusal reason")["accepted"])
        self.assertTrue(self.respond(state, order)["accepted"])
        state["resources"]["seal_material"] = 0
        apply_shared_action_command(state, "ada", {"operation": "reserve", "shared_action_id": order["canonical_action_id"]})
        snapshot = {"world_id": "fixture", "revision": 1, "tick": 1, "state": state}
        participant = actor_world_view(snapshot, "orin")["state"]["living_workshop"]["work_orders"][0]
        unrelated = actor_world_view(snapshot, "distant-viewer")["state"]["living_workshop"]["work_orders"][0]
        self.assertIn("negotiations", participant)
        self.assertEqual("my personal refusal reason", participant["negotiations"][0]["reason"])
        self.assertNotIn("negotiations", unrelated)
        self.assertNotIn("recovery_options", unrelated)
        worker = actor_world_view(snapshot, "ada")["state"]["living_workshop"]["work_orders"][0]
        self.assertEqual("request_supplies", worker["recovery_options"][0]["action"])

    def test_normalized_command_ids_cannot_bypass_water_route_gate(self):
        state, order = self.negotiated_state()
        action_id = self.reserve_repair(state, order)
        state["npcs"]["ada"]["route"] = None
        result = apply_shared_action_command(state, "ada", {"operation": " execute ", "shared_action_id": f" {action_id} "})
        self.assertFalse(result["accepted"], result)
        self.assertIn("route", result["reason"])

    def test_renegotiate_after_failure_can_assign_another_worker_and_preserve_terms(self):
        state, order = self.negotiated_state()
        action_id = self.reserve_repair(state, order)
        accepted_history = copy.deepcopy(order["negotiations"])
        apply_shared_action_command(state, "ada", {"operation": "execute", "shared_action_id": action_id})
        state["npcs"]["ada"]["energy"] = 0
        _process_shared_actions(state, 1)
        renegotiated = apply_player_action(state, "ada", {"type": "negotiate_work_order", "work_order_id": order["id"], "terms": {"note": "seek replacement while I rest"}})
        self.assertTrue(renegotiated["accepted"], renegotiated)
        replacement = self.respond(state, order, "orin")
        self.assertTrue(replacement["accepted"], replacement)
        self.assertEqual("orin", order["assigned_actor_id"])
        self.assertEqual(accepted_history, order["negotiations"][:len(accepted_history)])

    def test_recovery_rescoring_uses_actor_personality_and_explains_components(self):
        scores = []
        for curiosity in (0.0, 1.0):
            state, order = self.negotiated_state()
            state["npcs"]["ada"]["personality"] = {"curiosity": curiosity}
            self.assertTrue(self.respond(state, order)["accepted"])
            state["resources"]["seal_material"] = 0
            apply_shared_action_command(state, "ada", {"operation": "reserve", "shared_action_id": order["canonical_action_id"]})
            option = next(item for item in order["recovery_options"] if item["action"] == "seek_instruction")
            self.assertIn("components", option)
            scores.append(option["score"])
        self.assertGreater(scores[1], scores[0])

    def test_autonomous_supply_recovery_dispatches_a_durable_request(self):
        state, order = self.negotiated_state()
        self.assertTrue(self.respond(state, order)["accepted"])
        state["resources"]["seal_material"] = 0
        action_id = order["canonical_action_id"]
        self.assertTrue(apply_shared_action_command(state, "ada", {"operation": "route", "shared_action_id": action_id})["accepted"])
        self.assertFalse(apply_shared_action_command(state, "ada", {"operation": "reserve", "shared_action_id": action_id})["accepted"])

        emitted = _advance_autonomous_shared_actions(state, 2)

        requests = [item for item in state["shared_actions"]["demands"] if item.get("kind") == "water_repair_supply"]
        self.assertEqual(1, len(requests))
        request = requests[0]
        self.assertEqual("ada", request["requester_id"])
        self.assertEqual(action_id, request["canonical_action_id"])
        self.assertEqual({"seal_material": 2}, request["materials"])
        self.assertEqual("requested", request["status"])
        self.assertEqual("request_supplies", emitted[0]["payload"]["operation"])
        self.assertTrue(emitted[0]["payload"]["accepted"])

        _advance_autonomous_shared_actions(state, 3)
        requests = [item for item in state["shared_actions"]["demands"] if item.get("kind") == "water_repair_supply"]
        self.assertEqual(1, len(requests))

    def test_supply_recovery_is_fulfilled_and_repair_resumes_without_manual_state_repair(self):
        state, order = self.negotiated_state()
        self.assertTrue(self.respond(state, order)["accepted"])
        state["resources"]["seal_material"] = 0
        state["npcs"]["dev"]["inventory"]["seal_material"] = 2
        action_id = order["canonical_action_id"]
        self.assertTrue(apply_shared_action_command(state, "ada", {"operation": "route", "shared_action_id": action_id})["accepted"])
        self.assertFalse(apply_shared_action_command(state, "ada", {"operation": "reserve", "shared_action_id": action_id})["accepted"])

        for tick in range(2, 6):
            state["clock"]["tick"] = tick
            _advance_autonomous_shared_actions(state, tick)

        request = next(item for item in state["shared_actions"]["demands"] if item.get("kind") == "water_repair_supply")
        self.assertEqual("completed", request["status"])
        self.assertEqual([{"supplier_id": "dev", "materials": {"seal_material": 2}}], request["transfers"])
        self.assertEqual(0, state["npcs"]["dev"]["inventory"]["seal_material"])
        self.assertEqual(2, state["resources"]["seal_material"])
        self.assertEqual("completed", order["recovery_history"][-1]["status"])
        self.assertEqual("reserved", state["shared_actions"]["records"][action_id]["state"])
        transfer_events = [event for event in state["shared_actions"]["ledger"] if any(item.get("kind") == "water_repair_supply_transfer" for item in event.get("evidence", []))]
        self.assertEqual(1, len(transfer_events))
        transfer_event = transfer_events[0]
        self.assertEqual("dev", transfer_event["actor_id"])
        self.assertTrue(transfer_event["physical_effect"])

    def test_gathering_and_instruction_recovery_dispatch_real_requests(self):
        for recovery_action, demand_kind in (
            ("gather", "water_repair_gathering"),
            ("seek_instruction", "water_repair_instruction"),
        ):
            with self.subTest(recovery_action=recovery_action):
                state, order = self.negotiated_state()
                self.assertTrue(self.respond(state, order)["accepted"])
                state["resources"]["seal_material"] = 0
                action_id = order["canonical_action_id"]
                self.assertTrue(apply_shared_action_command(state, "ada", {"operation": "route", "shared_action_id": action_id})["accepted"])
                self.assertFalse(apply_shared_action_command(state, "ada", {"operation": "reserve", "shared_action_id": action_id})["accepted"])

                result = apply_shared_action_command(state, "ada", {"operation": recovery_action, "shared_action_id": action_id})

                self.assertTrue(result["accepted"], result)
                requests = [item for item in state["shared_actions"]["demands"] if item.get("kind") == demand_kind]
                self.assertEqual(1, len(requests))
                self.assertEqual(action_id, requests[0]["canonical_action_id"])
                self.assertEqual("ada", requests[0]["requester_id"])
                if recovery_action == "gather":
                    self.assertEqual({"seal_material": 2}, requests[0]["materials"])
                else:
                    self.assertEqual("mechanical_repair", requests[0]["domain"])
                    snapshot = {"world_id": "fixture", "revision": 1, "tick": 1, "state": state}
                    participant = next(item for item in actor_world_view(snapshot, "ada")["state"]["shared_actions"]["demands"] if item["id"] == requests[0]["id"])
                    unrelated = next(item for item in actor_world_view(snapshot, "distant-viewer")["state"]["shared_actions"]["demands"] if item["id"] == requests[0]["id"])
                    self.assertEqual("mechanical_repair", participant["domain"])
                    self.assertTrue(unrelated.get("private", False))
                    self.assertNotIn("domain", unrelated)
                    self.assertNotIn("requester_id", unrelated)
                    recovery_event = {"type": "shared_action_recovery", "actor_id": "ada", "payload": result}
                    participant_event = actor_event_view(recovery_event, snapshot, "ada")
                    unrelated_event = actor_event_view(recovery_event, snapshot, "distant-viewer")
                    self.assertEqual("mechanical_repair", participant_event["payload"]["request"]["domain"])
                    self.assertTrue(unrelated_event["payload"]["request"].get("private", False))
                    self.assertNotIn("domain", unrelated_event["payload"]["request"])
                    self.assertNotIn("requester_id", unrelated_event["payload"]["request"])

    def test_gathering_recovery_consumes_bounded_stock_and_resumes_repair(self):
        state, order = self.negotiated_state()
        self.assertTrue(self.respond(state, order)["accepted"])
        state["resources"]["seal_material"] = 0
        cache = state["resource_sites"]["tool-counter"]
        cache["stock"]["seal_material"] = 2
        action_id = order["canonical_action_id"]
        self.assertTrue(apply_shared_action_command(state, "ada", {"operation": "route", "shared_action_id": action_id})["accepted"])
        self.assertFalse(apply_shared_action_command(state, "ada", {"operation": "reserve", "shared_action_id": action_id})["accepted"])
        requested = apply_shared_action_command(state, "ada", {"operation": "gather", "shared_action_id": action_id})
        self.assertTrue(requested["accepted"], requested)

        for tick in range(2, 5):
            state["clock"]["tick"] = tick
            _advance_autonomous_shared_actions(state, tick)

        request = next(item for item in state["shared_actions"]["demands"] if item.get("kind") == "water_repair_gathering")
        self.assertEqual("completed", request["status"])
        self.assertEqual({"seal_material": 2}, request["gathered"])
        self.assertEqual(0, cache["stock"]["seal_material"])
        self.assertEqual(2, state["resources"]["seal_material"])
        self.assertEqual(action_id, cache["history"][-1]["canonical_action_id"])
        self.assertEqual("reserved", state["shared_actions"]["records"][action_id]["state"])
        gathering_events = [event for event in state["shared_actions"]["ledger"] if any(item.get("kind") == "water_repair_recovery_gathering" for item in event.get("evidence", []))]
        self.assertEqual(1, len(gathering_events))
        gathering_event = gathering_events[0]
        self.assertEqual("ada", gathering_event["actor_id"])
        self.assertTrue(gathering_event["physical_effect"])

    def test_instruction_recovery_completes_instruction_and_resumes_supervised_repair(self):
        state, order = self.negotiated_state()
        self.assertTrue(self.respond(state, order)["accepted"])
        state["npcs"]["ada"]["competency_records"]["mechanical_repair"] = {"demonstrated": 0.0, "provenance": []}
        state["npcs"]["orin"]["competency_records"]["mechanical_repair"] = {"demonstrated": 0.3, "provenance": ["fixture:orin-verified-repair"]}
        action_id = order["canonical_action_id"]
        self.assertTrue(apply_shared_action_command(state, "ada", {"operation": "route", "shared_action_id": action_id})["accepted"])
        self.assertFalse(apply_shared_action_command(state, "ada", {"operation": "reserve", "shared_action_id": action_id})["accepted"])
        requested = apply_shared_action_command(state, "ada", {"operation": "seek_instruction", "shared_action_id": action_id})
        self.assertTrue(requested["accepted"], requested)

        for tick in range(2, 80):
            state["clock"]["tick"] = tick
            _advance_travel_routes(state, tick)
            _process_shared_actions(state, tick)
            _advance_autonomous_shared_actions(state, tick)
            _process_teaching(state, tick)
            if state["shared_actions"]["records"][action_id]["state"] == "reserved":
                break

        request = next(item for item in state["shared_actions"]["demands"] if item.get("kind") == "water_repair_instruction")
        self.assertEqual("completed", request["status"])
        lesson = next(item for item in state["education"]["teaching_orders"] if item["id"] == request["teaching_order_id"])
        self.assertEqual("completed", lesson["status"])
        practice = next(item for item in state["education"]["practice_orders"] if item["source_instruction_id"] == lesson["id"])
        self.assertEqual("assigned_real_work", practice["status"])
        self.assertEqual(action_id, practice["work_order_id"])
        self.assertEqual(practice["id"], state["shared_actions"]["records"][action_id]["practice_order_id"])
        self.assertEqual("reserved", state["shared_actions"]["records"][action_id]["state"])

    def test_renegotiation_and_abandonment_recovery_change_workflow_state(self):
        for recovery_action, expected_status, fresh_consent in (
            ("renegotiate", "negotiating", False),
            ("abandon", "abandoned", True),
        ):
            with self.subTest(recovery_action=recovery_action):
                state, order = self.negotiated_state()
                self.assertTrue(self.respond(state, order)["accepted"])
                state["resources"]["seal_material"] = 0
                action_id = order["canonical_action_id"]
                self.assertTrue(apply_shared_action_command(state, "ada", {"operation": "route", "shared_action_id": action_id})["accepted"])
                self.assertFalse(apply_shared_action_command(state, "ada", {"operation": "reserve", "shared_action_id": action_id})["accepted"])

                result = apply_shared_action_command(state, "ada", {"operation": recovery_action, "shared_action_id": action_id})

                self.assertTrue(result["accepted"], result)
                self.assertEqual(expected_status, order["status"])
                self.assertIsNone(order["assigned_actor_id"])
                self.assertEqual(fresh_consent, order["requires_fresh_consent"])
                self.assertEqual("cancelled", state["shared_actions"]["records"][action_id]["state"])
                self.assertEqual(recovery_action, order["recovery_history"][-1]["action"])
                if recovery_action == "renegotiate":
                    self.assertEqual("proposal", order["negotiations"][-1]["kind"])
                    state["clock"]["tick"] = 2
                    _advance_autonomous_shared_actions(state, 2)
                    self.assertEqual("completed", order["recovery_history"][-1]["status"])
                    self.assertIsNotNone(order["assigned_actor_id"])
                else:
                    self.assertEqual("completed", order["recovery_history"][-1]["status"])
                    self.assertEqual("abandoned", order["recovery_history"][-1]["outcome"])
                    for tick in range(2, 5):
                        _advance_autonomous_shared_actions(state, tick)
                    self.assertEqual("abandoned", order["status"])
                    self.assertIsNone(order["assigned_actor_id"])

    def test_autonomous_rest_recovery_finishes_before_retrying_work(self):
        state, order = self.negotiated_state()
        self.assertTrue(self.respond(state, order)["accepted"])
        action_id = order["canonical_action_id"]
        self.assertTrue(apply_shared_action_command(state, "ada", {"operation": "route", "shared_action_id": action_id})["accepted"])
        state["npcs"]["ada"]["energy"] = 0
        self.assertFalse(apply_shared_action_command(state, "ada", {"operation": "reserve", "shared_action_id": action_id})["accepted"])

        state["clock"]["tick"] = 2
        recovered = _advance_autonomous_shared_actions(state, 2)
        self.assertEqual("rest", recovered[0]["payload"]["operation"])
        for tick in range(3, 10):
            state["clock"]["tick"] = tick
            _process_shared_actions(state, tick)
            _advance_autonomous_shared_actions(state, tick)

        self.assertNotIn("workshop_rest", state["npcs"]["ada"])
        self.assertEqual("reserved", state["shared_actions"]["records"][action_id]["state"])
        self.assertEqual("completed", order["recovery_history"][-1]["status"])

    def test_shared_water_execution_records_and_events_preserve_symptom_channels(self):
        state, order = self.negotiated_state()
        location = state["npcs"]["ada"]["location"]
        self.add_player(state, "untrained-observer", location)
        self.add_player(state, "trained-observer", location, measurement=0.3)
        state["installations"]["water"]["contamination_index"] = 0.5
        _process_living_workshop(state, 2)
        action_id = self.reserve_repair(state, order)
        executed = apply_shared_action_command(state, "ada", {"operation": "execute", "shared_action_id": action_id})
        self.assertTrue(executed["accepted"])
        emitted = _process_shared_actions(state, 6)
        before = copy.deepcopy(state)
        snapshot = {"world_id": "fixture", "revision": 1, "tick": 6, "state": state}
        for viewer_id in ("untrained-observer", "trained-observer"):
            projected = actor_world_view(snapshot, viewer_id)["state"]["shared_actions"]
            record = projected["records"][action_id]
            events = [actor_event_view({"type": "player_action", "payload": executed}, snapshot, viewer_id), *[actor_event_view(event, snapshot, viewer_id) for event in emitted]]
            samples = [record["samples"][0], record["output"]["pre_repair_measurements"][0], projected["ledger"][-1]["evidence"][0]["pre_repair_measurements"][0], events[0]["payload"]["record"]["samples"][0], events[-1]["payload"]["event"]["outputs"]["pre_repair_measurements"][0]]
            for sample in samples:
                self.assertIn("flow_lpm", sample)
                if viewer_id == "untrained-observer":
                    self.assertNotIn("pressure_kpa", sample)
                    self.assertNotIn("contamination_index", sample)
                else:
                    self.assertIn("pressure_kpa", sample)
                    self.assertIn("contamination_index", sample)
        self.assertEqual(before, state)

    def test_water_sample_channels_require_permission_for_that_exact_measurement(self):
        state = self.workshop_state()
        water = state["installations"]["water"]
        water["condition"] = 0.75
        state["npcs"]["ada"]["competency_records"]["mechanical_repair"] = {"demonstrated": 0.3, "provenance": ["fixture:verified-repair"]}
        location = state["places"][water["location"]]["location"]
        viewer = self.add_player(state, "intermittent-observer", location)
        _process_living_workshop(state, 1)
        first_measurement_id = state["living_workshop"]["measurements"][-1]["id"]
        viewer["location"] = [0, 0]
        _process_living_workshop(state, 2)
        second_measurement_id = state["living_workshop"]["measurements"][-1]["id"]
        viewer["location"] = list(location)
        order = state["living_workshop"]["work_orders"][0]
        action_id = self.reserve_repair(state, order)
        executed = apply_shared_action_command(state, "ada", {"operation": "execute", "shared_action_id": action_id})
        self.assertTrue(executed["accepted"], executed)
        _process_shared_actions(state, 6)

        snapshot = {"world_id": "fixture", "revision": 1, "tick": 6, "state": state}
        view = actor_world_view(snapshot, "intermittent-observer")["state"]
        visible_measurements = {item["id"] for item in view["living_workshop"]["measurements"]}
        self.assertIn(first_measurement_id, visible_measurements)
        self.assertNotIn(second_measurement_id, visible_measurements)
        projected = view["shared_actions"]["records"][action_id]
        self.assertEqual([], projected["sample_measurement_ids"])
        self.assertNotIn("flow_lpm", projected["samples"][0])
        self.assertNotIn("flow_lpm", projected["output"]["pre_repair_measurements"][0])

    def test_deliberate_cancellation_stays_cancelled_through_autonomous_ticks(self):
        state, order = self.negotiated_state()
        action_id = self.reserve_repair(state, order)
        cancelled = apply_shared_action_command(state, "ada", {"operation": "cancel", "shared_action_id": action_id})
        self.assertTrue(cancelled["accepted"])
        history = copy.deepcopy(order["negotiations"])
        for tick in range(1, 5):
            _advance_autonomous_shared_actions(state, tick)
        self.assertEqual("cancelled", order["status"])
        self.assertIsNone(order["assigned_actor_id"])
        self.assertEqual(action_id, order["canonical_action_id"])
        self.assertEqual(history, order["negotiations"])
        self.assertNotIn("ada", state["shared_actions"]["actor_commitments"])
        self.assertTrue(self.respond(state, order)["accepted"])
        self.assertEqual("ada", order["assigned_actor_id"])

    def test_human_and_ai_submitted_work_share_verifier_shortage_gate(self):
        for actor_id in ("ada", "player-worker"):
            with self.subTest(actor_id=actor_id):
                state, order = self.negotiated_state(actor_id)
                action_id = self.reserve_repair(state, order, actor_id)
                for entity in state["npcs"].values():
                    entity["competency_records"]["measurement"] = {"demonstrated": 0, "provenance": []}
                self.assertTrue(apply_shared_action_command(state, actor_id, {"operation": "execute", "shared_action_id": action_id})["accepted"])
                _process_shared_actions(state, 6)
                _advance_autonomous_shared_actions(state, 7)
                self.assertEqual("blocked", order["status"])
                self.assertEqual("independent_verifier_unavailable", order["blockers"][-1]["code"])
                self.assertNotIn(actor_id, state["shared_actions"]["actor_commitments"])
                self.assertEqual("submitted", state["shared_actions"]["records"][action_id]["state"])
                recovery = apply_shared_action_command(state, actor_id, {"operation": "renegotiate", "shared_action_id": action_id})
                self.assertTrue(recovery["accepted"], recovery)
                request = next(item for item in state["shared_actions"]["demands"] if item.get("kind") == "water_repair_verifier")
                self.assertEqual(actor_id, request["requester_id"])
                self.assertEqual(action_id, request["canonical_action_id"])
                self.assertEqual("measurement", request["domain"])
                self.assertEqual("awaiting_verifier", order["status"])

    def test_verifier_recovery_rechecks_candidates_after_their_other_work_ends(self):
        state, order = self.negotiated_state()
        verifier = self.add_player(state, "player-verifier", state["places"]["measurement_lab"]["location"], measurement=0.3)
        busy_id = "verifier-existing-work"
        proposed = apply_shared_action_command(state, verifier["id"], {
            "operation": "propose", "shared_action_id": busy_id,
            "action_type": "calibrate_measurement_tool", "observations": ["visible drift"],
        })
        self.assertTrue(proposed["accepted"], proposed)
        self.assertTrue(apply_shared_action_command(state, verifier["id"], {"operation": "accept", "shared_action_id": busy_id})["accepted"])
        action_id = self.reserve_repair(state, order)
        for entity in state["npcs"].values():
            entity["competency_records"]["measurement"] = {"demonstrated": 0, "provenance": []}
        self.assertTrue(apply_shared_action_command(state, "ada", {"operation": "execute", "shared_action_id": action_id})["accepted"])
        _process_shared_actions(state, 6)
        _advance_autonomous_shared_actions(state, 7)
        self.assertEqual("independent_verifier_unavailable", order["blockers"][-1]["code"])
        self.assertTrue(apply_shared_action_command(state, "ada", {"operation": "renegotiate", "shared_action_id": action_id})["accepted"])

        self.assertTrue(apply_shared_action_command(state, verifier["id"], {"operation": "cancel", "shared_action_id": busy_id})["accepted"])
        for tick in (8, 9):
            state["clock"]["tick"] = tick
            _advance_autonomous_shared_actions(state, tick)

        request = next(item for item in state["shared_actions"]["demands"] if item.get("kind") == "water_repair_verifier")
        self.assertEqual("completed", request["status"])
        self.assertEqual("player-verifier", order["verifier_id"])
        self.assertEqual("awaiting_verifier_consent", order["status"])

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

    def test_mixed_measurement_does_not_authorize_outcome_from_an_unseen_channel(self):
        state = self.workshop_state()
        location = state["places"][state["installations"]["water"]["location"]]["location"]
        local_untrained = self.add_player(state, "local-untrained", location)
        local_untrained["needs"].update({"hydration": 100.0, "safety": 100.0})
        state["installations"]["water"].update({"condition": 0.75, "contamination_index": 0.2})

        _process_living_workshop(state, 1)

        measurement = state["living_workshop"]["measurements"][0]
        self.assertIn("declining_flow", measurement["symptoms"])
        self.assertIn("unsafe_quality", measurement["symptoms"])
        self.assertIn("unsafe_quality", measurement["perceived_symptoms"]["ada"])
        self.assertEqual(["declining_flow"], measurement["perceived_symptoms"]["local-untrained"])
        self.assertEqual("ada", state["living_workshop"]["demands"][0]["proposer_id"])
        outcome = {
            "tick": 1,
            "kind": "inspection_follow_up",
            "actor_id": "ada",
            "symptoms": ["declining_flow", "unsafe_quality"],
            "perceived_evidence_ids": [measurement["id"]],
            "reason": "declining_flow is visible, but unsafe_quality requires instrument follow-up",
        }
        state["living_workshop"]["recent_outcomes"].append(outcome)
        snapshot = {"world_id": "fixture", "revision": 1, "tick": 1, "state": state}

        authorized = actor_world_view(snapshot, "ada")["state"]["living_workshop"]["recent_outcomes"][0]
        untrained = actor_world_view(snapshot, "local-untrained")["state"]["living_workshop"]["recent_outcomes"][0]

        self.assertEqual(outcome, authorized)
        self.assertTrue(untrained["private"])
        self.assertNotIn("symptoms", untrained)
        self.assertNotIn("reason", untrained)
        self.assertNotIn("perceived_evidence_ids", untrained)

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
