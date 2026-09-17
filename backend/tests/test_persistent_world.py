import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from causal_ledger import CausalEvent, CausalLedger
from persistent_world import (
    PersistentWorldStore,
    RevisionConflict,
    _directed_response_decision,
    migrate_state,
    _npc_reply,
    _process_proximity_speech,
    actor_event_view,
    actor_world_view,
)


class PersistentWorldTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "world.sqlite3"
        self.store = PersistentWorldStore(self.path)
        self.world = self.store.create_world(now_ms=1_000_000)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_observed_snapshot_records_token_derived_viewer_id(self):
        snapshot = self.store.snapshot()
        snapshot["state"]["players"]["server-bound-owner-uuid"] = {"is_owner": True, "permission_level": "sirix_1", "stats": {"health": 100}}
        observed = actor_world_view(snapshot, "server-bound-owner-uuid")
        self.assertEqual(observed["viewer_id"], "server-bound-owner-uuid")
        self.assertTrue(observed["viewer_is_owner"])

    def install_test_pump(self, actor="maintainer"):
        """Install an already validated finite unit so lifecycle tests can focus on field causality."""
        self.store.apply_action(self.world["world_id"], f"{actor}-join-tools", actor, {"type": "join", "location": [7, 8]}, now_ms=1_000_001)
        snapshot = self.store.snapshot()
        state = snapshot["state"]
        prediction = {"mechanical_advantage": 4.0, "predicted_liters_per_stroke": 4.241}
        state["research"]["designs"].append({
            "id": "design-maintenance", "name": "Lifecycle pump", "archetype": "lever_pump",
            "proposer": "fixture-engineer", "status": "validated", "prediction": prediction,
            "available_units": 1,
        })
        state["technology"]["validated_designs"].append("design-maintenance")
        state["technology"]["tool_catalog"]["design-maintenance"] = {
            "id": "design-maintenance", "archetype": "lever_pump", "prediction": prediction,
            "available_units": 1, "provenance": ["validated-design:design-maintenance"],
        }
        with self.store.transaction() as connection:
            connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(state), snapshot["world_id"]))
        for index, item in enumerate(["shovel", "bucket", "wrench"], 1):
            self.store.apply_action(self.world["world_id"], f"{actor}-checkout-{index}", actor, {"type": "interact_site", "site_id": "tool-counter", "operation": "checkout", "item": item}, now_ms=1_000_010 + index)
        self.store.apply_action(self.world["world_id"], f"{actor}-join-well", actor, {"type": "join", "location": [11, 12]}, now_ms=1_000_020)
        for index in range(3):
            self.store.apply_action(self.world["world_id"], f"{actor}-dig-{index}", actor, {"type": "interact_site", "site_id": "well-site", "operation": "dig"}, now_ms=1_000_021 + index)
        installed = self.store.apply_action(self.world["world_id"], f"{actor}-install-pump", actor, {"type": "interact_site", "site_id": "well-site", "operation": "install_pump", "design_id": "design-maintenance"}, now_ms=1_000_030)
        self.assertTrue(installed["result"]["accepted"])
        snapshot = self.store.snapshot()
        state = snapshot["state"]
        state["resource_sites"]["well-site"]["capacity"] = 100
        state["resource_sites"]["well-site"]["stock"] = 100
        with self.store.transaction() as connection:
            connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(state), snapshot["world_id"]))
        return actor

    def install_measurement_competence(self, entity_ids):
        snapshot = self.store.snapshot()
        state = snapshot["state"]
        for entity_id in entity_ids:
            entity = state["players"].get(entity_id) or state["npcs"].get(entity_id)
            entity.setdefault("competency_records", {})["measurement"] = {
                "demonstrated": 0.2, "provenance": [f"fixture:verified-measurement:{entity_id}"]
            }
            entity["location"] = [8, 6]
        with self.store.transaction() as connection:
            connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(state), snapshot["world_id"]))

    def run_durable_calibration(self, performer, verifier, prefix, now_ms):
        definition = "calibrate_measurement_tool"
        self.store.apply_action(self.world["world_id"], f"{prefix}-propose-command", performer, {
            "type": "shared_action", "operation": "propose", "shared_action_id": prefix,
            "action_type": definition, "intent": "restore trustworthy length measurement",
            "observations": ["marked measure drifted against the reference edge"],
        }, now_ms=now_ms)
        self.store.apply_action(self.world["world_id"], f"{prefix}-accept-command", performer, {
            "type": "shared_action", "operation": "accept", "shared_action_id": prefix,
        }, now_ms=now_ms + 1)
        reserved = self.store.apply_action(self.world["world_id"], f"{prefix}-reserve-command", performer, {
            "type": "shared_action", "operation": "reserve", "shared_action_id": prefix,
        }, now_ms=now_ms + 2)
        self.assertTrue(reserved["result"]["accepted"])
        self.store.apply_action(self.world["world_id"], f"{prefix}-execute-command", performer, {
            "type": "shared_action", "operation": "execute", "shared_action_id": prefix,
            "samples": [{"reading": 1.0}, {"reading": 1.01}, {"reading": 1.0}],
        }, now_ms=now_ms + 3)
        self.store.advance_due(now_ms=now_ms + 4 * 15_000, max_ticks=4)
        verified = self.store.apply_action(self.world["world_id"], f"{prefix}-verify-command", verifier, {
            "type": "shared_action", "operation": "verify", "shared_action_id": prefix,
        }, now_ms=now_ms + 4 * 15_000 + 1)
        self.assertEqual("verified", verified["result"]["record"]["state"])
        return self.store.apply_action(self.world["world_id"], f"{prefix}-commission-command", verifier, {
            "type": "shared_action", "operation": "commission", "shared_action_id": prefix,
        }, now_ms=now_ms + 4 * 15_000 + 2)

    def test_durable_shared_action_uses_identical_human_and_ai_rules_across_restart(self):
        self.store.apply_action(self.world["world_id"], "join-human-calibrator", "human-calibrator", {"type": "join", "location": [8, 6]}, now_ms=1_000_001)
        self.install_measurement_competence(["human-calibrator", "ada", "mira"])
        human_result = self.run_durable_calibration("human-calibrator", "mira", "human-calibration", 1_000_010)
        self.assertTrue(human_result["result"]["physical_change"])

        self.store.close()
        self.store = PersistentWorldStore(self.path)
        after_restart = self.store.snapshot()["state"]
        self.assertEqual("commissioned", after_restart["shared_actions"]["records"]["human-calibration"]["state"])
        self.assertEqual(1, after_restart["shared_actions"]["commissioned_outputs"]["human-calibrator"]["calibrated_measure"])

        ai_result = self.run_durable_calibration("ada", "human-calibrator", "ai-calibration", 1_100_010)
        self.assertEqual("commissioned", ai_result["result"]["record"]["state"])
        final = self.store.snapshot()["state"]
        self.assertEqual(2, 4 - final["resources"]["reference_strip"])
        self.assertEqual(0, sum(final["shared_actions"]["valuation_accounts_milli"].values()))
        self.assertTrue(all(not claim["spendable"] for claim in final["shared_actions"]["valuation_claims"]))
        self.assertTrue(any(memory.get("kind") == "subjective_causal_memory" for memory in final["npcs"]["ada"]["memories"]))
        self.assertGreater(final["npcs"]["ada"]["competency_records"]["measurement"]["demonstrated"], 0.2)
        self.assertTrue(CausalLedger([CausalEvent(**event) for event in final["shared_actions"]["ledger"]]).verify())

    def test_shared_action_competence_and_perception_gates_apply_equally(self):
        self.store.apply_action(self.world["world_id"], "join-untrained", "untrained-human", {"type": "join", "location": [8, 6]}, now_ms=1_000_001)
        for actor_id in ("untrained-human", "orin"):
            if actor_id == "orin":
                snapshot = self.store.snapshot(); state = snapshot["state"]; state["npcs"]["orin"]["location"] = [8, 6]
                with self.store.transaction() as connection:
                    connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(state), snapshot["world_id"]))
            action_id = f"untrained-{actor_id}"
            self.store.apply_action(self.world["world_id"], f"{action_id}-propose", actor_id, {"type": "shared_action", "operation": "propose", "shared_action_id": action_id, "action_type": "calibrate_measurement_tool", "observations": ["possible drift"]})
            self.store.apply_action(self.world["world_id"], f"{action_id}-accept", actor_id, {"type": "shared_action", "operation": "accept", "shared_action_id": action_id})
            rejected = self.store.apply_action(self.world["world_id"], f"{action_id}-reserve", actor_id, {"type": "shared_action", "operation": "reserve", "shared_action_id": action_id})
            self.assertFalse(rejected["result"]["accepted"])
            self.assertEqual("insufficient demonstrated competence", rejected["result"]["reason"])

    def test_actor_commitment_is_persistent_exclusive_and_cancellable_for_human_and_ai(self):
        self.store.apply_action(self.world["world_id"], "join-committed-human", "committed-human", {"type": "join", "location": [8, 6]}, now_ms=1_000_001)
        self.install_measurement_competence(["committed-human", "ada"])
        for actor_id in ("committed-human", "ada"):
            first, second = f"{actor_id}-first", f"{actor_id}-second"
            for action_id in (first, second):
                proposed = self.store.apply_action(self.world["world_id"], f"{action_id}-propose", actor_id, {
                    "type": "shared_action", "operation": "propose", "shared_action_id": action_id,
                    "action_type": "calibrate_measurement_tool", "observations": ["marked measure drift"],
                })
                self.assertTrue(proposed["result"]["accepted"])
            accepted = self.store.apply_action(self.world["world_id"], f"{first}-accept", actor_id, {"type": "shared_action", "operation": "accept", "shared_action_id": first})
            reserved = self.store.apply_action(self.world["world_id"], f"{first}-reserve", actor_id, {"type": "shared_action", "operation": "reserve", "shared_action_id": first})
            conflict = self.store.apply_action(self.world["world_id"], f"{second}-accept", actor_id, {"type": "shared_action", "operation": "accept", "shared_action_id": second})
            self.assertTrue(accepted["result"]["accepted"])
            self.assertTrue(reserved["result"]["accepted"])
            self.assertFalse(conflict["result"]["accepted"])
            self.assertIn(first, conflict["result"]["reason"])
            self.store.close(); self.store = PersistentWorldStore(self.path)
            persisted = self.store.snapshot()["state"]
            self.assertEqual(first, persisted["shared_actions"]["actor_commitments"][actor_id]["action_id"])
            cancelled = self.store.apply_action(self.world["world_id"], f"{first}-cancel", actor_id, {"type": "shared_action", "operation": "cancel", "shared_action_id": first})
            self.assertTrue(cancelled["result"]["accepted"])
            released = self.store.snapshot()["state"]["shared_actions"]
            self.assertNotIn(actor_id, released["actor_commitments"])
            self.assertIsNone(released["tools"]["marked_measure"]["reserved_by"])
            self.assertIsNone(released["stations"]["measurement_bench"]["reserved_by"])
            retried = self.store.apply_action(self.world["world_id"], f"{second}-retry", actor_id, {"type": "shared_action", "operation": "accept", "shared_action_id": second})
            self.assertTrue(retried["result"]["accepted"])
            self.store.apply_action(self.world["world_id"], f"{second}-cancel", actor_id, {"type": "shared_action", "operation": "cancel", "shared_action_id": second})

    def test_degraded_tool_generates_deterministic_need_driven_ai_proposal(self):
        self.install_measurement_competence(["ada"])
        advanced = self.store.advance_due(now_ms=1_000_000 + 15_000, max_ticks=1)["state"]
        demand = advanced["shared_actions"]["demands"][0]
        self.assertEqual("proposed", demand["status"])
        self.assertEqual("ada", demand["assigned_to"])
        record = advanced["shared_actions"]["records"][demand["action_id"]]
        self.assertEqual("ai", record["actor_kind"])
        self.assertEqual("proposed", record["state"])
        self.assertIn("condition", record["observations"][0])
        self.assertEqual(1, len(advanced["shared_actions"]["ledger"]))

    def test_runclock_completes_need_driven_ai_work_through_public_action_commands(self):
        initial_reference = self.store.snapshot()["state"]["resources"]["reference_strip"]
        completed = self.store.advance_due(now_ms=1_000_000 + 24 * 15_000, max_ticks=24)["state"]
        demand = completed["shared_actions"]["demands"][0]
        record = completed["shared_actions"]["records"][demand["action_id"]]
        self.assertEqual("resolved", demand["status"])
        self.assertEqual("commissioned", record["state"])
        self.assertEqual("ada", record["actor_id"])
        self.assertEqual("mira", record["verifier_id"])
        self.assertEqual(initial_reference - 1, completed["resources"]["reference_strip"])
        self.assertEqual(0, sum(completed["shared_actions"]["valuation_accounts_milli"].values()))
        self.assertFalse(completed["shared_actions"]["valuation_claims"][0]["spendable"])
        states = [event["state"] for event in completed["shared_actions"]["ledger"] if event["action_id"] == record["id"]]
        self.assertEqual(["proposed", "accepted", "reserved", "in_progress", "submitted", "verified", "commissioned"], states)
        transition_ticks = [event["tick"] for event in completed["shared_actions"]["ledger"] if event["action_id"] == record["id"]]
        self.assertEqual(sorted(transition_ticks), transition_ticks)
        self.assertGreater(len(set(transition_ticks)), 4)

    def test_human_communal_meal_uses_canonical_thermal_evidence_and_independent_review(self):
        self.store.apply_action(self.world["world_id"], "join-human-cook", "human-cook", {"type": "join", "location": [8, 7]}, now_ms=1_000_001)
        snapshot = self.store.snapshot(); state = snapshot["state"]
        state["places"]["communal_kitchen"]["status"] = "operational"
        state["resources"].update({"raw_food": 12, "tested_water": 6, "fuel": 4})
        state["players"]["human-cook"]["competency_records"]["cooking"] = {"demonstrated": 0.2, "provenance": ["fixture:verified-cooking-practice"]}
        state["npcs"]["imani"]["location"] = [8, 8]
        safe_before = state["resources"]["safe_meals"]
        inputs_before = {key: state["resources"][key] for key in ("raw_food", "tested_water", "fuel")}
        with self.store.transaction() as connection:
            connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(state), snapshot["world_id"]))
        action_id = "human-canonical-meal"
        for index, action in enumerate((
            {"type": "shared_action", "operation": "propose", "shared_action_id": action_id, "action_type": "prepare_communal_meal", "observations": ["safe meals are needed"], "intent": "prepare measured communal food"},
            {"type": "shared_action", "operation": "accept", "shared_action_id": action_id},
            {"type": "shared_action", "operation": "reserve", "shared_action_id": action_id},
            {"type": "shared_action", "operation": "execute", "shared_action_id": action_id, "samples": [{"temperature_c": 82, "duration_minutes": 15}]},
        )):
            result = self.store.apply_action(self.world["world_id"], f"human-meal-{index}", "human-cook", action, now_ms=1_000_010 + index)
            self.assertTrue(result["result"]["accepted"])
        self.store.advance_due(now_ms=1_000_010 + 4 * 15_000, max_ticks=4)
        verified = self.store.apply_action(self.world["world_id"], "human-meal-verify", "imani", {"type": "shared_action", "operation": "verify", "shared_action_id": action_id})
        self.assertEqual("verified", verified["result"]["record"]["state"])
        self.store.apply_action(self.world["world_id"], "human-meal-commission", "imani", {"type": "shared_action", "operation": "commission", "shared_action_id": action_id})
        final = self.store.snapshot()["state"]
        record = final["shared_actions"]["records"][action_id]
        self.assertEqual("commissioned", record["state"])
        self.assertGreaterEqual(record["output"]["safety"], 0.75)
        self.assertEqual(safe_before + 3, final["resources"]["safe_meals"])
        self.assertEqual({"raw_food": inputs_before["raw_food"] - 3, "tested_water": inputs_before["tested_water"] - 2, "fuel": inputs_before["fuel"] - 1}, {key: final["resources"][key] for key in inputs_before})
        self.assertEqual("accepted", final["cooking"]["meal_batches"][-1]["status"])
        self.assertEqual("imani", final["cooking"]["meal_batches"][-1]["inspector"])
        self.assertGreater(final["players"]["human-cook"]["competency_records"]["cooking"]["demonstrated"], 0.2)
        self.assertIn(record["ledger_event_ids"][-2], final["npcs"]["imani"]["competency_records"]["food_safety"]["provenance"])
        self.assertEqual(0, sum(final["shared_actions"]["valuation_accounts_milli"].values()))
        self.assertTrue(CausalLedger([CausalEvent(**event) for event in final["shared_actions"]["ledger"]]).verify())

    def test_measurement_apprenticeship_reproduces_specialists_through_verified_real_work(self):
        instructed = self.store.advance_due(now_ms=1_000_000 + 36 * 15_000, max_ticks=36)["state"]
        lesson = next(item for item in instructed["education"]["teaching_orders"] if item["domain"] == "measurement")
        self.assertEqual("completed", lesson["status"])
        self.assertEqual(0, instructed["npcs"][lesson["learner"]]["competency_records"]["measurement"]["demonstrated"])
        practice = next(item for item in instructed["education"]["practice_orders"] if item["domain"] == "measurement")
        self.assertEqual("awaiting_real_work", practice["status"])

        instructed["shared_actions"]["tools"]["marked_measure"]["condition"] = 0.6
        with self.store.transaction() as connection:
            connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(instructed), self.world["world_id"]))
        self.store.close(); self.store = PersistentWorldStore(self.path)
        practiced = self.store.advance_due(now_ms=1_000_000 + 72 * 15_000, max_ticks=36)["state"]
        practice = next(item for item in practiced["education"]["practice_orders"] if item["domain"] == "measurement")
        self.assertEqual("completed", practice["status"])
        action = practiced["shared_actions"]["records"][practice["verified_work_order_id"]]
        self.assertEqual(lesson["learner"], action["actor_id"])
        self.assertEqual(lesson["instructor"], action["supervisor_id"])
        self.assertNotEqual(action["supervisor_id"], action["verifier_id"])
        self.assertEqual("commissioned", action["state"])
        self.assertGreaterEqual(practiced["npcs"][lesson["learner"]]["competency_records"]["measurement"]["demonstrated"], 0.12)
        self.assertTrue(any(item["effect"].startswith(f"competency-demonstrated:{lesson['learner']}:measurement") for item in practiced["consequences"]))

    def test_shared_action_evidence_respects_actor_perspective_in_snapshots_and_events(self):
        self.store.apply_action(self.world["world_id"], "join-performer", "performer", {"type": "join", "location": [8, 6]}, now_ms=1_000_001)
        self.store.apply_action(self.world["world_id"], "join-observer", "observer", {"type": "join", "location": [0, 0]}, now_ms=1_000_002)
        self.install_measurement_competence(["performer"])
        self.store.apply_action(self.world["world_id"], "private-proposal-command", "performer", {
            "type": "shared_action", "operation": "propose", "shared_action_id": "private-proposal",
            "action_type": "calibrate_measurement_tool", "observations": ["private measured drift"],
        }, now_ms=1_000_003)

        snapshot = self.store.snapshot()
        remote = actor_world_view(snapshot, "observer")["state"]["shared_actions"]
        self.assertTrue(remote["records"]["private-proposal"]["private"])
        self.assertEqual([], remote["ledger"])
        raw_event = next(event for event in self.store.events(self.world["world_id"]) if event["payload"].get("record", {}).get("id") == "private-proposal")
        redacted = actor_event_view(raw_event, snapshot, "observer")
        self.assertEqual({"private": True, "action_id": "private-proposal", "state": "proposed"}, redacted["payload"])

        state = snapshot["state"]
        state["players"]["observer"]["location"] = [8, 6]
        with self.store.transaction() as connection:
            connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(state), snapshot["world_id"]))
        nearby_snapshot = self.store.snapshot()
        nearby = actor_world_view(nearby_snapshot, "observer")["state"]["shared_actions"]
        self.assertEqual(["private measured drift"], nearby["records"]["private-proposal"]["observations"])
        self.assertFalse(actor_event_view(raw_event, nearby_snapshot, "observer")["payload"].get("private", False))

    def test_owner_directive_is_reviewed_and_generates_institutional_action(self):
        with self.assertRaises(PermissionError):
            self.store.apply_action(
                self.world["world_id"], "forged-owner-directive", "impostor",
                {"type": "owner_directive", "directive": {"objective": "Change the world", "priority": "water"}},
                now_ms=1_000_000,
            )
        proposed = self.store.apply_owner_directive(
            self.world["world_id"], "owner-water-proposal", "owner-uuid",
            {"objective": "Establish dependable measured water access", "priority": "water", "evidence_required": ["survey", "water test"]},
            now_ms=1_000_001,
        )
        replayed = self.store.apply_owner_directive(
            self.world["world_id"], "owner-water-proposal", "owner-uuid",
            {"objective": "Establish dependable measured water access", "priority": "water", "evidence_required": ["survey", "water test"]},
            now_ms=1_000_002,
        )
        self.assertEqual(proposed, replayed)
        directive = self.store.snapshot()["state"]["institutions"]["governance"]["owner_directives"][0]
        self.assertEqual("pending_council_review", directive["status"])
        self.assertEqual("proposal_only", directive["authority_scope"])
        self.assertFalse(directive["physical_effect"])
        self.assertEqual("owner_directive", self.store.events(self.world["world_id"])[-2]["type"])

        self.store.close()
        self.store = PersistentWorldStore(self.path)
        reviewed = self.store.advance_due(now_ms=1_000_000 + 15_000, max_ticks=1)["state"]
        directive = reviewed["institutions"]["governance"]["owner_directives"][0]
        self.assertEqual("adopted", directive["status"])
        self.assertIn("measured water pressure", directive["decision_reason"])
        self.assertEqual("water", reviewed["institutions"]["council"]["endorsements"]["owner-directive:directive-1"])
        self.assertTrue(any(item["action"] == "owner_directive" for item in reviewed["causality"]["completed_reactions"]))
        self.assertTrue(any(event["type"] == "owner_directive_reviewed" for event in self.store.events(self.world["world_id"])))

        self.assertTrue(any(item["kind"] == "causal_reaction" and item["action"] == "owner_directive" for item in reviewed["institutions"]["council"]["knowledge"]))
        self.assertTrue(any(item["effect"].startswith("decision:reaction-") for item in reviewed["consequences"]))

    def test_unmeasurable_owner_directive_is_rejected_by_the_world(self):
        self.store.apply_owner_directive(
            self.world["world_id"], "owner-vague-proposal", "owner-uuid",
            {"objective": "Make everything better", "priority": "undefined_power", "evidence_required": []},
            now_ms=1_000_001,
        )
        reviewed = self.store.advance_due(now_ms=1_000_000 + 15_000, max_ticks=1)["state"]
        directive = reviewed["institutions"]["governance"]["owner_directives"][0]
        self.assertEqual("rejected", directive["status"])
        self.assertIn("measurable settlement priority", directive["decision_reason"])

    def test_owner_proposal_becomes_physical_history_then_changes_the_next_decision(self):
        self.store.apply_owner_directive(
            self.world["world_id"], "owner-water-history", "owner-uuid",
            {"objective": "Establish dependable tested water access", "priority": "water", "evidence_required": ["survey", "water test"]},
            now_ms=1_000_001,
        )
        commissioned = self.store.advance_due(now_ms=1_000_000 + 240 * 15_000, max_ticks=240)["state"]
        directive = commissioned["institutions"]["governance"]["owner_directives"][0]
        initiative = commissioned["institutions"]["council"]["current_initiative"]
        self.assertEqual("commissioned", directive["status"])
        self.assertEqual("civic-1-water", directive["initiative_id"])
        self.assertIn("owner-directive:directive-1", initiative["causal_sources"])
        self.assertIn("owner-directive:directive-1", initiative["reason"])

        self.store.close()
        self.store = PersistentWorldStore(self.path)
        completed = self.store.advance_due(now_ms=1_000_000 + 288 * 15_000, max_ticks=48)["state"]
        directive = completed["institutions"]["governance"]["owner_directives"][0]
        water_work = completed["institutions"]["council"]["completed_initiatives"][0]
        self.assertEqual("fulfilled", directive["status"])
        self.assertEqual("water", directive["world_change"])
        self.assertEqual("completed", water_work["status"])
        self.assertEqual("operational", completed["places"]["water_source"]["status"])
        self.assertGreater(completed["places"]["water_source"]["dependability"], 0.45)
        self.assertGreater(completed["resources"]["tested_water"], 0)
        performed_evidence = next(item for item in completed["evidence"] if item["change"] == "water initiative performed")
        self.assertIn("owner-directive:directive-1", performed_evidence["causal_sources"])
        self.assertTrue(any(item["kind"] == "verified_world_change" and item["initiative_id"] == "civic-1-water" for item in completed["institutions"]["council"]["knowledge"]))
        self.assertTrue(any(item["kind"] == "verified water public work" for item in completed["economy"]["claims"]))

        reconsidered = self.store.advance_due(now_ms=1_000_000 + 300 * 15_000, max_ticks=12)["state"]
        next_initiative = reconsidered["institutions"]["council"]["current_initiative"]
        latest_observation = next(item for item in reversed(reconsidered["institutions"]["council"]["knowledge"]) if item["kind"] == "settlement_pressures")
        self.assertIn("civic-1-water", latest_observation["prior_changes"])
        self.assertIn("completed-initiative:civic-1-water", latest_observation["sources"])
        self.assertIn("observation:council:300", next_initiative["causal_sources"])
        self.assertNotEqual("civic-1-water", next_initiative["id"])

    def test_owner_required_evidence_can_block_inspection_and_generate_recovery_work(self):
        self.store.apply_owner_directive(
            self.world["world_id"], "owner-water-special-evidence", "owner-uuid",
            {"objective": "Establish water access with an additional trace test", "priority": "water", "evidence_required": ["survey", "water test", "trace contaminant assay"]},
            now_ms=1_000_001,
        )
        blocked = self.store.advance_due(now_ms=1_000_000 + 288 * 15_000, max_ticks=288)["state"]
        initiative = blocked["institutions"]["council"]["current_initiative"]
        self.assertEqual("performed", initiative["status"])
        self.assertIn("trace contaminant assay", initiative["evidence_blocker"]["missing_evidence"])
        self.assertEqual("collect evidence for civic-1-water", blocked["npcs"]["mira"]["intention"])
        self.assertTrue(any(item["reason"] == "required inspection evidence unavailable" and not item["recovered"] for item in blocked["failures"]))

        recovered = self.store.advance_due(now_ms=1_000_000 + 300 * 15_000, max_ticks=12)["state"]
        self.assertIn("trace contaminant assay", recovered["institutions"]["council"]["current_initiative"]["evidence_tags"])
        self.assertTrue(any(item["reason"] == "required inspection evidence unavailable" and item["recovered"] for item in recovered["failures"]))
        self.assertTrue(any(event["type"] == "initiative_evidence_collected" for event in self.store.events(self.world["world_id"], limit=1000)))

        completed = self.store.advance_due(now_ms=1_000_000 + 312 * 15_000, max_ticks=12)["state"]
        self.assertEqual("fulfilled", completed["institutions"]["governance"]["owner_directives"][0]["status"])
        self.assertEqual("operational", completed["places"]["water_source"]["status"])

    def test_invalid_engineering_prediction_is_preserved_as_rejected_research(self):
        self.store.apply_action(self.world["world_id"], "inventor-join-lab", "inventor", {"type": "join", "location": [8, 7]}, now_ms=1_000_000)
        proposed = self.store.apply_action(self.world["world_id"], "invalid-pump-design", "inventor", {
            "type": "propose_invention", "archetype": "lever_pump", "name": "Impossible pump",
            "specification": {"effort_arm_m": 0.1, "load_arm_m": 1.0, "piston_diameter_m": 0.5, "stroke_m": 2.0, "efficiency": 1.4},
            "test_protocol": "Measure delivered water volume for ten complete strokes.", "knowledge_sources": ["inventor field notebook"],
        }, now_ms=1_000_001)
        self.assertTrue(proposed["result"]["accepted"])
        reviewed = self.store.advance_due(now_ms=1_000_000 + 6 * 15_000, max_ticks=6)["state"]
        design = reviewed["research"]["designs"][0]
        self.assertEqual("rejected", design["status"])
        self.assertFalse(design["review"]["accepted"])
        self.assertFalse(any(item["evidence"] == "validated-design:design-1" for item in reviewed["economy"]["claims"]))
        self.assertTrue(any(event["type"] == "design_rejected" for event in self.store.events(self.world["world_id"])))

    def test_reproduced_player_invention_changes_later_well_work(self):
        self.store.apply_action(self.world["world_id"], "pump-inventor-join", "inventor", {"type": "join", "location": [8, 7]}, now_ms=1_000_000)
        proposed = self.store.apply_action(self.world["world_id"], "lever-pump-proposal", "inventor", {
            "type": "propose_invention", "archetype": "lever_pump", "name": "Founders lever pump",
            "specification": {"effort_arm_m": 1.2, "load_arm_m": 0.3, "piston_diameter_m": 0.12, "stroke_m": 0.5, "efficiency": 0.75},
            "test_protocol": "Measure ten strokes into a graduated vessel and compare observed volume with the SI prediction.",
            "knowledge_sources": ["measured workshop sketch", "Ada's lever demonstration"],
        }, now_ms=1_000_001)
        self.assertTrue(proposed["result"]["accepted"])
        prototype = self.store.advance_due(now_ms=1_000_000 + 12 * 15_000, max_ticks=12)["state"]
        self.assertEqual("prototype_built", prototype["research"]["designs"][0]["status"])
        self.store.close()
        self.store = PersistentWorldStore(self.path)
        validated = self.store.advance_due(now_ms=1_000_000 + 24 * 15_000, max_ticks=12)["state"]
        design = validated["research"]["designs"][0]
        self.assertEqual("validated", design["status"])
        self.assertEqual(4.0, design["prediction"]["mechanical_advantage"])
        self.assertAlmostEqual(4.241, design["prediction"]["predicted_liters_per_stroke"], places=3)
        self.assertTrue(design["test_result"]["passed"])
        self.assertTrue(validated["research"]["reproductions"][0]["passed"])
        self.assertIn("design-1", validated["technology"]["validated_designs"])
        self.assertAlmostEqual(sum(validated["economy"]["accounts"].values()), 0)
        self.assertTrue(any(item["actor"] == "inventor" and item["kind"] == "validated engineering design" for item in validated["economy"]["claims"]))

        self.store.apply_action(self.world["world_id"], "pump-tools-position", "inventor", {"type": "join", "location": [7, 8]}, now_ms=1_360_001)
        for index, item in enumerate(["shovel", "bucket", "wrench"], 1):
            self.store.apply_action(self.world["world_id"], f"pump-tool-{index}-{item}", "inventor", {"type": "interact_site", "site_id": "tool-counter", "operation": "checkout", "item": item}, now_ms=1_360_001 + index)
        self.store.apply_action(self.world["world_id"], "pump-well-position", "inventor", {"type": "join", "location": [11, 12]}, now_ms=1_360_010)
        for index in range(3):
            dug = self.store.apply_action(self.world["world_id"], f"pump-dig-stage-{index}", "inventor", {"type": "interact_site", "site_id": "well-site", "operation": "dig"}, now_ms=1_360_011 + index)
            self.assertTrue(dug["result"]["accepted"])
        installed = self.store.apply_action(self.world["world_id"], "install-validated-pump", "inventor", {"type": "interact_site", "site_id": "well-site", "operation": "install_pump", "design_id": "design-1"}, now_ms=1_360_020)
        self.assertTrue(installed["result"]["accepted"])
        drawn = self.store.apply_action(self.world["world_id"], "pump-water-draw", "inventor", {"type": "interact_site", "site_id": "well-site", "operation": "draw_water"}, now_ms=1_360_021)
        self.assertTrue(drawn["result"]["accepted"])
        self.assertEqual(4, drawn["result"]["outputs"]["water"])
        self.assertEqual(1, drawn["result"]["outputs"]["technology_gain"])
        final = self.store.snapshot()["state"]
        self.assertEqual("design-1", final["resource_sites"]["well-site"]["installed_pump"]["design_id"])
        self.assertEqual(4, final["players"]["inventor"]["inventory"]["water"])
        self.assertTrue(any(item["cause"] == "validated-technology:design-1" and item["effect"].startswith("installed-tool:well-site") for item in final["consequences"]))

    def test_pump_use_degrades_output_opens_work_and_failure_survives_restart(self):
        actor = self.install_test_pump()
        yields = []
        for cycle in range(9):
            result = self.store.apply_action(self.world["world_id"], f"pump-cycle-{cycle}", actor, {"type": "interact_site", "site_id": "well-site", "operation": "draw_water"}, now_ms=1_000_100 + cycle)
            self.assertTrue(result["result"]["accepted"])
            yields.append(result["result"]["outputs"]["water"])
        worn = self.store.snapshot()["state"]
        pump = worn["resource_sites"]["well-site"]["installed_pump"]
        self.assertGreater(yields[0], yields[-1])
        self.assertEqual(9, pump["cycles"])
        self.assertEqual("failed", pump["status"])
        self.assertTrue(pump["maintenance_due"])
        self.assertEqual(1, len(worn["institutions"]["governance"]["maintenance_orders"]))
        self.assertTrue(any(item["effect"].startswith("technology-failed:well-site") for item in worn["consequences"]))

        self.store.close()
        self.store = PersistentWorldStore(self.path)
        persisted = self.store.snapshot()["state"]
        self.assertEqual("failed", persisted["resource_sites"]["well-site"]["installed_pump"]["status"])
        self.assertEqual("open", persisted["institutions"]["governance"]["maintenance_orders"][0]["status"])
        rejected = self.store.apply_action(self.world["world_id"], "draw-failed-pump", actor, {"type": "interact_site", "site_id": "well-site", "operation": "draw_water"}, now_ms=1_000_200)
        self.assertFalse(rejected["result"]["accepted"])

    def test_player_supplied_maintenance_recovers_failed_technology(self):
        actor = self.install_test_pump("player-repairer")
        for cycle in range(9):
            self.store.apply_action(self.world["world_id"], f"repair-wear-{cycle}", actor, {"type": "interact_site", "site_id": "well-site", "operation": "draw_water"}, now_ms=1_000_100 + cycle)
        snapshot = self.store.snapshot()
        state = snapshot["state"]
        state["players"][actor]["inventory"].update({"timber": 1, "containers": 1})
        with self.store.transaction() as connection:
            connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(state), snapshot["world_id"]))
        proposed = self.store.apply_action(self.world["world_id"], "player-maintain-pump", actor, {"type": "interact_site", "site_id": "well-site", "operation": "maintain_pump"}, now_ms=1_000_210)
        self.assertTrue(proposed["result"]["accepted"])
        recovered = self.store.snapshot()["state"]
        pump = recovered["resource_sites"]["well-site"]["installed_pump"]
        self.assertEqual("failed", pump["status"])
        action_id = recovered["institutions"]["governance"]["maintenance_orders"][0]["canonical_action_id"]
        self.assertEqual("proposed", recovered["shared_actions"]["records"][action_id]["state"])
        self.assertEqual(1, recovered["players"][actor]["inventory"]["timber"])
        self.assertEqual(1, recovered["players"][actor]["inventory"]["containers"])

    def test_observed_wear_generates_autonomous_assignment_and_verified_repair(self):
        actor = self.install_test_pump("field-user")
        for cycle in range(4):
            self.store.apply_action(self.world["world_id"], f"field-wear-{cycle}", actor, {"type": "interact_site", "site_id": "well-site", "operation": "draw_water"}, now_ms=1_000_100 + cycle)
        opened = self.store.snapshot()["state"]
        order = opened["institutions"]["governance"]["maintenance_orders"][0]
        self.assertEqual("open", order["status"])
        timber_before, containers_before = opened["resources"]["timber"], opened["resources"]["containers"]

        repaired = self.store.advance_due(now_ms=1_000_000 + 45 * 15_000, max_ticks=45)["state"]
        order = repaired["institutions"]["governance"]["maintenance_orders"][0]
        self.assertEqual("completed", order["status"])
        self.assertEqual("ada", order["assigned_to"])
        self.assertEqual("ada", order["completed_by"])
        self.assertEqual(timber_before - 1, repaired["resources"]["timber"])
        self.assertEqual(containers_before - 1, repaired["resources"]["containers"])
        self.assertTrue(any(memory["kind"] == "subjective_causal_memory" for memory in repaired["npcs"]["ada"]["memories"]))
        event_types = [event["type"] for event in self.store.events(self.world["world_id"])]
        self.assertIn("maintenance_assigned", event_types)
        self.assertIn("maintenance_completed", event_types)
        self.assertAlmostEqual(sum(repaired["shared_actions"]["valuation_accounts_milli"].values()), 0)

    def test_maintenance_shortage_drives_targeted_procurement_after_restart(self):
        actor = self.install_test_pump("shortage-user")
        snapshot = self.store.snapshot()
        state = snapshot["state"]
        state["resources"]["timber"] = 0
        state["resources"]["containers"] = 0
        with self.store.transaction() as connection:
            connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(state), snapshot["world_id"]))
        for cycle in range(4):
            self.store.apply_action(self.world["world_id"], f"shortage-wear-{cycle}", actor, {"type": "interact_site", "site_id": "well-site", "operation": "draw_water"}, now_ms=1_000_100 + cycle)
        blocked = self.store.advance_due(now_ms=1_000_000 + 35 * 15_000, max_ticks=35)["state"]
        order = blocked["institutions"]["governance"]["maintenance_orders"][0]
        self.assertEqual("open", order["status"])
        self.assertIn("containers", set(order["blockers"][0]["missing"]))

        self.store.close()
        self.store = PersistentWorldStore(self.path)
        recovered = self.store.advance_due(now_ms=1_000_000 + 135 * 15_000, max_ticks=100)["state"]
        order = recovered["institutions"]["governance"]["maintenance_orders"][0]
        self.assertEqual("completed", order["status"])
        self.assertEqual("commissioned", recovered["shared_actions"]["records"][order["canonical_action_id"]]["state"])
        self.assertIn("containers", [entry["resource"] for entry in order["procurement_history"]])
        self.assertTrue(all(entry["method"] == "maintenance shortage procurement" and entry["order_id"] == order["id"] for entry in order["procurement_history"]))
        self.assertTrue(order["blockers"])
        self.assertTrue(any(item["kind"] == "maintenance_procurement" and item["order_id"] == order["id"] for item in recovered["institutions"]["council"]["knowledge"]))
        self.assertTrue(any(item["cause"].startswith(f"procurement-demand:{order['id']}:") for item in recovered["consequences"]))
        self.assertAlmostEqual(sum(recovered["economy"]["accounts"].values()), 0)

    def test_regional_depletion_persists_then_regeneration_enables_repair(self):
        actor = self.install_test_pump("depletion-user")
        snapshot = self.store.snapshot()
        state = snapshot["state"]
        state["resources"]["timber"] = 0
        state["resources"]["containers"] = 1
        for region in state["environment"]["regions"].values():
            if "timber" in region.get("stocks", {}):
                region["stocks"]["timber"] = 0
        state["resource_sites"]["old-oak"]["stock"] = 0
        state["resource_sites"]["pine-stand"]["stock"] = 0
        with self.store.transaction() as connection:
            connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(state), snapshot["world_id"]))
        for cycle in range(4):
            self.store.apply_action(self.world["world_id"], f"depletion-wear-{cycle}", actor, {"type": "interact_site", "site_id": "well-site", "operation": "draw_water"}, now_ms=1_000_100 + cycle)
        depleted = self.store.advance_due(now_ms=1_000_000 + 25 * 15_000, max_ticks=25)["state"]
        order = depleted["institutions"]["governance"]["maintenance_orders"][0]
        self.assertEqual("open", order["status"])
        self.assertEqual("unresolved", order["depletion_notices"][0]["status"])
        self.assertEqual(0, order["depletion_notices"][0]["regional_remaining"])
        self.assertTrue(any(event["type"] == "material_procurement_blocked" for event in self.store.events(self.world["world_id"])))

        self.store.close()
        self.store = PersistentWorldStore(self.path)
        recovered = self.store.advance_due(now_ms=1_000_000 + 260 * 15_000, max_ticks=235)["state"]
        order = recovered["institutions"]["governance"]["maintenance_orders"][0]
        self.assertEqual("completed", order["status"])
        self.assertEqual("commissioned", recovered["shared_actions"]["records"][order["canonical_action_id"]]["state"])
        self.assertEqual("recovered", order["depletion_notices"][0]["status"])
        self.assertTrue(any(entry["resource"] == "timber" for entry in order["procurement_history"]))
        event_types = [event["type"] for event in self.store.events(self.world["world_id"])]
        self.assertIn("material_procurement_blocked", event_types)
        self.assertIn("maintenance_action_proposed", event_types)

    def test_player_water_delivery_is_tested_valued_and_consumed_after_restart(self):
        actor = self.install_test_pump("water-carrier")
        drawn = self.store.apply_action(self.world["world_id"], "carrier-draw-water", actor, {"type": "interact_site", "site_id": "well-site", "operation": "draw_water"}, now_ms=1_000_100)
        amount = drawn["result"]["outputs"]["water"]
        self.store.apply_action(self.world["world_id"], "carrier-enter-lab", actor, {"type": "join", "location": [8, 7]}, now_ms=1_000_101)
        submitted = self.store.apply_action(self.world["world_id"], "carrier-water-batch", actor, {"type": "submit_water_batch", "source_site": "well-site", "amount": amount}, now_ms=1_000_102)
        self.assertTrue(submitted["result"]["accepted"])
        self.assertEqual("awaiting_test", submitted["result"]["batch"]["status"])
        self.assertEqual(0, self.store.snapshot()["state"]["players"][actor]["inventory"]["water"])

        self.store.close()
        self.store = PersistentWorldStore(self.path)
        verified = self.store.advance_due(now_ms=1_000_000 + 2 * 15_000, max_ticks=2)["state"]
        batch = verified["water_system"]["batches"][0]
        self.assertEqual("verified", batch["status"])
        self.assertGreaterEqual(batch["safety"], 0.75)
        self.assertEqual(amount, verified["resources"]["tested_water"])
        claim = next(item for item in verified["economy"]["claims"] if item["kind"] == "verified safe-water delivery")
        self.assertEqual(actor, claim["actor"])
        self.assertEqual(amount * verified["economy"]["prices"]["tested_water"], claim["amount"])
        self.assertAlmostEqual(sum(verified["economy"]["accounts"].values()), 0)
        self.assertTrue(any(item["change"] == f"water batch {batch['id']} tested" and item["inspector"] == "mira" for item in verified["evidence"]))

        snapshot = self.store.snapshot()
        state = snapshot["state"]
        state["event"]["status"] = "completed"
        with self.store.transaction() as connection:
            connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(state), snapshot["world_id"]))

        consumed = self.store.advance_due(now_ms=1_000_000 + 12 * 15_000, max_ticks=10)["state"]
        consumption = consumed["water_system"]["consumption_history"][0]
        self.assertEqual(amount, consumption["amount"])
        self.assertEqual(0, consumed["resources"]["tested_water"])
        self.assertTrue(all(item["after"] > item["before"] for item in consumption["recipients"]))
        self.assertTrue(any(event["type"] == "communal_water_consumed" for event in self.store.events(self.world["world_id"])))

    def test_worn_pump_water_can_fail_independent_safety_review(self):
        actor = self.install_test_pump("worn-water-carrier")
        final_draw = None
        for cycle in range(8):
            final_draw = self.store.apply_action(self.world["world_id"], f"worn-water-{cycle}", actor, {"type": "interact_site", "site_id": "well-site", "operation": "draw_water"}, now_ms=1_000_100 + cycle)
        amount = final_draw["result"]["outputs"]["water"]
        self.store.apply_action(self.world["world_id"], "worn-carrier-lab", actor, {"type": "join", "location": [8, 7]}, now_ms=1_000_120)
        submitted = self.store.apply_action(self.world["world_id"], "worn-water-batch", actor, {"type": "submit_water_batch", "source_site": "well-site", "amount": amount}, now_ms=1_000_121)
        self.assertTrue(submitted["result"]["accepted"])
        reviewed = self.store.advance_due(now_ms=1_000_000 + 2 * 15_000, max_ticks=2)["state"]
        batch = reviewed["water_system"]["batches"][0]
        self.assertEqual("rejected", batch["status"])
        self.assertLess(batch["safety"], 0.75)
        self.assertEqual(0, reviewed["resources"]["tested_water"])
        self.assertFalse(any(item["kind"] == "verified safe-water delivery" for item in reviewed["economy"]["claims"]))
        self.assertTrue(any(item["effect"].startswith("unsafe-water-rejected:") for item in reviewed["consequences"]))

    def test_hydration_shortage_creates_spatial_autonomous_water_work_across_restart(self):
        self.install_test_pump("water-observer")
        snapshot = self.store.snapshot()
        state = snapshot["state"]
        state["event"]["status"] = "completed"
        for npc in state["npcs"].values():
            npc["needs"]["hydration"] = 72
        state["npcs"]["rae"]["needs"]["hydration"] = 39
        with self.store.transaction() as connection:
            connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(state), snapshot["world_id"]))
        proposed = self.store.advance_due(now_ms=1_000_000 + 12 * 15_000, max_ticks=12)["state"]
        order = proposed["water_system"]["work_orders"][0]
        self.assertEqual("proposed", order["status"])
        self.assertEqual("rae", proposed["water_system"]["shortages"][0]["affected"][0])

        self.store.close()
        self.store = PersistentWorldStore(self.path)
        completed = self.store.advance_due(now_ms=1_000_000 + 45 * 15_000, max_ticks=33)["state"]
        order = completed["water_system"]["work_orders"][0]
        self.assertEqual("completed", order["status"])
        self.assertEqual("emil", order["collector"])
        batch = next(item for item in completed["water_system"]["batches"] if item["id"] == order["batch_id"])
        self.assertEqual("verified", batch["status"])
        self.assertEqual(order["id"], batch["work_order_id"])
        self.assertTrue(any(memory["kind"] == "completed_work" and order["id"] in memory["text"] for memory in completed["npcs"]["emil"]["memories"]))
        self.assertGreater(completed["npcs"]["rae"]["needs"]["hydration"], 39)
        event_types = [event["type"] for event in self.store.events(self.world["world_id"])]
        self.assertIn("water_work_proposed", event_types)
        self.assertIn("water_worker_moved", event_types)
        self.assertIn("water_collected", event_types)
        self.assertIn("water_delivered_to_lab", event_types)
        self.assertIn("water_work_completed", event_types)

    def test_rejected_autonomous_batch_causes_maintenance_then_safe_retry(self):
        self.install_test_pump("quality-observer")
        snapshot = self.store.snapshot()
        state = snapshot["state"]
        state["event"]["status"] = "completed"
        for npc in state["npcs"].values():
            npc["needs"]["hydration"] = 72
        state["npcs"]["rae"]["needs"]["hydration"] = 39
        state["resource_sites"]["well-site"]["installed_pump"]["condition"] = 0.44
        with self.store.transaction() as connection:
            connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(state), snapshot["world_id"]))
        resolved = self.store.advance_due(now_ms=1_000_000 + 160 * 15_000, max_ticks=160)["state"]
        order = resolved["water_system"]["work_orders"][0]
        self.assertEqual("completed", order["status"])
        related = [batch for batch in resolved["water_system"]["batches"] if batch.get("work_order_id") == order["id"]]
        self.assertGreaterEqual(len(related), 2)
        self.assertEqual("rejected", related[0]["status"])
        self.assertEqual("verified", related[-1]["status"])
        maintenance = resolved["institutions"]["governance"]["maintenance_orders"][0]
        self.assertEqual("completed", maintenance["status"])
        self.assertLess(related[0]["safety"], 0.75)
        self.assertGreaterEqual(related[-1]["safety"], 0.75)
        self.assertTrue(any(item["status"] == "blocked_quality" for item in order["history"]))
        self.assertTrue(any(item["cause"].startswith("rejected-water:") or item["cause"].startswith("autonomous-wear:") for item in resolved["consequences"]))

    def test_hungry_npc_walks_to_kitchen_and_consumes_finite_meal_after_restart(self):
        snapshot = self.store.snapshot()
        state = snapshot["state"]
        state["event"]["status"] = "completed"
        state["resources"]["safe_meals"] = 1
        state["npcs"]["lena"]["needs"]["nutrition"] = 20
        with self.store.transaction() as connection:
            connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(state), snapshot["world_id"]))
        moving = self.store.advance_due(now_ms=1_000_000 + 2 * 15_000, max_ticks=2)["state"]
        self.assertEqual("eat", moving["npcs"]["lena"]["survival_activity"]["kind"])
        self.assertEqual("active", moving["npcs"]["lena"]["survival_activity"]["status"])
        self.assertTrue(any(event["type"] == "survival_movement" and event["actor_id"] == "lena" for event in self.store.events(self.world["world_id"])))

        self.store.close()
        self.store = PersistentWorldStore(self.path)
        fed = self.store.advance_due(now_ms=1_000_000 + 8 * 15_000, max_ticks=6)["state"]
        self.assertEqual("completed", fed["npcs"]["lena"]["survival_activity"]["status"])
        self.assertGreater(fed["npcs"]["lena"]["needs"]["nutrition"], 20)
        self.assertEqual(0, fed["resources"]["safe_meals"])
        self.assertEqual("lena", fed["survival"]["meal_history"][0]["npc_id"])
        self.assertTrue(any(item["change"] == "safe meal consumed by lena" for item in fed["evidence"]))
        self.assertTrue(any(event["type"] == "meal_consumed" and event["actor_id"] == "lena" for event in self.store.events(self.world["world_id"])))

    def test_meal_depletion_becomes_persistent_food_pressure(self):
        snapshot = self.store.snapshot()
        state = snapshot["state"]
        state["event"]["status"] = "completed"
        state["resources"]["safe_meals"] = 0
        state["npcs"]["lena"]["needs"]["nutrition"] = 20
        with self.store.transaction() as connection:
            connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(state), snapshot["world_id"]))
        hungry = self.store.advance_due(now_ms=1_000_000 + 1 * 15_000, max_ticks=1)["state"]
        shortage = hungry["survival"]["shortages"][0]
        self.assertEqual("safe_meal", shortage["kind"])
        self.assertEqual("unresolved", shortage["status"])
        self.assertIn("lena", shortage["affected"])
        self.assertEqual("food", hungry["institutions"]["council"]["endorsements"][f"survival:{shortage['id']}"])
        self.assertTrue(any(item["effect"] == f"food-shortage:{shortage['id']}" for item in hungry["consequences"]))

    def test_exhausted_water_worker_recovers_then_resumes_persistent_order(self):
        self.install_test_pump("fatigue-observer")
        snapshot = self.store.snapshot()
        state = snapshot["state"]
        state["event"]["status"] = "completed"
        for npc in state["npcs"].values():
            npc["needs"]["hydration"] = 72
            npc["needs"]["nutrition"] = 72
        state["npcs"]["rae"]["needs"]["hydration"] = 39
        state["npcs"]["emil"]["needs"]["rest"] = 19
        shortage = {"tick": 0, "tested_water": 0, "affected": ["rae"], "status": "unresolved", "work_order_id": "water-work-1"}
        order = {"id": "water-work-1", "status": "proposed", "created_tick": 0, "shortage_tick": 0, "collector": "emil", "tester": "mira", "source_site": "well-site", "target_amount": 3, "batch_id": None, "history": [{"tick": 0, "status": "proposed", "cause": "hydration-shortage:0"}]}
        state["water_system"]["shortages"].append(shortage)
        state["water_system"]["work_orders"].append(order)
        with self.store.transaction() as connection:
            connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(state), snapshot["world_id"]))
        blocked = self.store.advance_due(now_ms=1_000_000 + 2 * 15_000, max_ticks=2)["state"]
        self.assertEqual("blocked_worker", blocked["water_system"]["work_orders"][0]["status"])
        self.assertTrue(any(event["type"] == "survival_movement" and event["actor_id"] == "emil" for event in self.store.events(self.world["world_id"])))

        self.store.close()
        self.store = PersistentWorldStore(self.path)
        resumed = self.store.advance_due(now_ms=1_000_000 + 60 * 15_000, max_ticks=58)["state"]
        order = resumed["water_system"]["work_orders"][0]
        self.assertEqual("completed", order["status"])
        self.assertTrue(any(item.get("cause") == "collector recovered" for item in order["history"]))
        self.assertTrue(any(item["status"] == "recovered" and item["npc_id"] == "emil" for item in resumed["survival"]["rest_history"]))
        self.assertTrue(any(memory["text"] == "Recovered enough rest to resume chosen work." for memory in resumed["npcs"]["emil"]["memories"]))

    def test_meal_shortage_commissions_autonomous_cooking_and_feeds_resident_after_restart(self):
        snapshot = self.store.snapshot()
        state = snapshot["state"]
        state["event"]["status"] = "completed"
        state["places"]["communal_kitchen"]["status"] = "operational"
        state["resources"].update({"safe_meals": 0, "raw_food": 10, "tested_water": 5, "fuel": 5})
        for npc in state["npcs"].values():
            npc["needs"]["nutrition"] = 72
            npc["needs"]["rest"] = 72
        state["npcs"]["rae"]["needs"]["nutrition"] = 20
        with self.store.transaction() as connection:
            connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(state), snapshot["world_id"]))
        proposed = self.store.advance_due(now_ms=1_000_000 + 1 * 15_000, max_ticks=1)["state"]
        order = proposed["cooking"]["work_orders"][0]
        self.assertEqual("proposed", order["status"])
        self.assertEqual("rae", proposed["survival"]["shortages"][0]["affected"][0])

        self.store.close()
        self.store = PersistentWorldStore(self.path)
        completed = self.store.advance_due(now_ms=1_000_000 + 24 * 15_000, max_ticks=23)["state"]
        order = completed["cooking"]["work_orders"][0]
        self.assertEqual("completed", order["status"])
        batch = completed["cooking"]["meal_batches"][0]
        self.assertEqual("accepted", batch["status"])
        self.assertEqual("imani", batch["inspector"])
        self.assertGreater(completed["npcs"]["rae"]["needs"]["nutrition"], 20)
        self.assertTrue(any(item["npc_id"] == "rae" for item in completed["survival"]["meal_history"]))
        self.assertTrue(any(item["actor_id"] == "lena" and not item["spendable"] for item in completed["shared_actions"]["valuation_claims"]))
        self.assertEqual(0, sum(completed["shared_actions"]["valuation_accounts_milli"].values()))
        self.assertTrue(any(recipe["name"] == batch["recipe"] for recipe in completed["culture"]["recipes"]))
        event_types = [event["type"] for event in self.store.events(self.world["world_id"])]
        self.assertIn("cooking_worker_moved", event_types)
        self.assertIn("meal_preparation_started", event_types)
        self.assertIn("cooking_inspector_moved", event_types)
        self.assertIn("cooking_work_completed", event_types)

    def test_cooking_input_shortage_recovers_through_finite_procurement(self):
        snapshot = self.store.snapshot()
        state = snapshot["state"]
        state["event"]["status"] = "completed"
        state["places"]["communal_kitchen"]["status"] = "operational"
        state["resources"].update({"safe_meals": 0, "raw_food": 0, "tested_water": 5, "fuel": 5})
        for npc in state["npcs"].values():
            npc["needs"]["nutrition"] = 72
            npc["needs"]["rest"] = 72
        state["npcs"]["rae"]["needs"]["nutrition"] = 20
        with self.store.transaction() as connection:
            connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(state), snapshot["world_id"]))
        blocked = self.store.advance_due(now_ms=1_000_000 + 3 * 15_000, max_ticks=3)["state"]
        order = blocked["cooking"]["work_orders"][0]
        self.assertEqual("blocked_inputs", order["status"])
        self.assertEqual(3, order["missing"]["raw_food"])

        self.store.close()
        self.store = PersistentWorldStore(self.path)
        recovered = self.store.advance_due(now_ms=1_000_000 + 36 * 15_000, max_ticks=33)["state"]
        order = recovered["cooking"]["work_orders"][0]
        self.assertEqual("completed", order["status"])
        self.assertTrue(any(item.get("cause") == "required ingredients delivered" for item in order["history"]))
        self.assertTrue(any(item.get("resource") == "raw_food" and item["actor"] == "orin" for item in recovered["environment"]["extraction_history"]))
        self.assertTrue(any(item["cause"].startswith(f"communal-cooking-work:{order['id']}") and item["effect"].startswith("cooking-input-shortage:") for item in recovered["consequences"]))

    def test_residents_consume_traceable_meal_batches_in_expiry_order(self):
        snapshot = self.store.snapshot()
        state = snapshot["state"]
        state["event"]["status"] = "completed"
        state["places"]["communal_kitchen"]["status"] = "operational"
        state["resources"]["safe_meals"] = 2
        state["cooking"]["meal_batches"] = [
            {"id": "meal-batch-later", "status": "accepted", "portions": 1, "remaining_portions": 1, "expires_tick": 20, "preservation": "none"},
            {"id": "meal-batch-first", "status": "accepted", "portions": 1, "remaining_portions": 1, "expires_tick": 10, "preservation": "none"},
        ]
        for npc in state["npcs"].values():
            npc["needs"]["nutrition"] = 72
        state["npcs"]["lena"]["needs"]["nutrition"] = 20
        state["npcs"]["lena"]["location"] = [8, 7]
        with self.store.transaction() as connection:
            connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(state), snapshot["world_id"]))
        consumed = self.store.advance_due(now_ms=1_000_000 + 1 * 15_000, max_ticks=1)["state"]
        first = next(item for item in consumed["cooking"]["meal_batches"] if item["id"] == "meal-batch-first")
        later = next(item for item in consumed["cooking"]["meal_batches"] if item["id"] == "meal-batch-later")
        self.assertEqual("consumed", first["status"])
        self.assertEqual(1, later["remaining_portions"])
        self.assertEqual("meal-batch-first", consumed["survival"]["meal_history"][0]["meal_batch_id"])
        evidence = next(item for item in consumed["evidence"] if item["change"] == "safe meal consumed by lena")
        self.assertEqual("meal-batch-first", evidence["inputs"]["meal_batch"])

    def test_expired_meal_batch_becomes_waste_and_commissions_replacement_after_restart(self):
        snapshot = self.store.snapshot()
        state = snapshot["state"]
        state["event"]["status"] = "completed"
        state["places"]["communal_kitchen"]["status"] = "operational"
        state["resources"].update({"safe_meals": 3, "raw_food": 6, "tested_water": 3, "fuel": 2})
        state["cooking"]["meal_batches"] = [{
            "id": "meal-batch-expiring", "status": "accepted", "portions": 3, "remaining_portions": 3,
            "expires_tick": 1, "preservation": "none", "inspected_tick": 0,
        }]
        for npc in state["npcs"].values():
            npc["needs"]["nutrition"] = 72
        state["npcs"]["rae"]["needs"]["nutrition"] = 20
        with self.store.transaction() as connection:
            connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(state), snapshot["world_id"]))
        self.store.close()
        self.store = PersistentWorldStore(self.path)
        spoiled = self.store.advance_due(now_ms=1_000_000 + 1 * 15_000, max_ticks=1)["state"]
        batch = spoiled["cooking"]["meal_batches"][0]
        self.assertEqual("spoiled", batch["status"])
        self.assertEqual(3, spoiled["cooking"]["waste_portions"])
        self.assertEqual(0, spoiled["resources"]["safe_meals"])
        self.assertEqual("proposed", spoiled["cooking"]["work_orders"][0]["status"])
        self.assertEqual("meal-batch-expiring", spoiled["cooking"]["spoilage_history"][0]["batch_id"])
        self.assertTrue(any(item["kind"] == "food_waste" and item["batch_id"] == batch["id"] for item in spoiled["institutions"]["council"]["knowledge"]))
        self.assertTrue(any(item["cause"] == f"meal-batch-expired:{batch['id']}" and item["effect"] == "safe-meals-lost:3" for item in spoiled["consequences"]))
        event_types = [event["type"] for event in self.store.events(self.world["world_id"])]
        self.assertIn("meal_batch_spoiled", event_types)
        self.assertIn("cooking_work_proposed", event_types)

    def test_recorded_food_waste_validates_preservation_practice_after_restart(self):
        snapshot = self.store.snapshot()
        state = snapshot["state"]
        state["event"]["status"] = "completed"
        state["cooking"]["waste_portions"] = 3
        state["cooking"]["spoilage_history"] = [{"tick": 0, "batch_id": "meal-batch-lost", "lost_portions": 3}]
        state["resources"].update({"raw_food": 4, "fuel": 3, "containers": 2})
        with self.store.transaction() as connection:
            connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(state), snapshot["world_id"]))
        proposed = self.store.advance_due(now_ms=1_000_000 + 1 * 15_000, max_ticks=1)["state"]
        self.assertEqual("proposed", proposed["cooking"]["preservation_program"]["status"])
        self.store.close()
        self.store = PersistentWorldStore(self.path)
        validated = self.store.advance_due(now_ms=1_000_000 + 6 * 15_000, max_ticks=5)["state"]
        program = validated["cooking"]["preservation_program"]
        self.assertEqual("active", program["status"])
        self.assertEqual(24, program["shelf_life_gain_ticks"])
        self.assertEqual("imani", program["tested_by"])
        self.assertTrue(any(item["kind"] == "validated food-preservation practice" for item in validated["economy"]["claims"]))
        self.assertAlmostEqual(sum(validated["economy"]["accounts"].values()), 0)
        self.assertTrue(any(item["effect"] == "cooking-practice-active:drying:+24-ticks" for item in validated["consequences"]))
        self.assertTrue(any(item["name"] == "Measured drying practice" for item in validated["culture"]["traditions"]))

    def test_preservation_trial_input_blocker_recovers_through_material_economy(self):
        snapshot = self.store.snapshot()
        state = snapshot["state"]
        state["event"]["status"] = "completed"
        state["cooking"]["waste_portions"] = 3
        state["cooking"]["spoilage_history"] = [{"tick": 0, "batch_id": "meal-batch-lost", "lost_portions": 3}]
        state["resources"].update({"raw_food": 4, "fuel": 3, "containers": 0})
        with self.store.transaction() as connection:
            connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(state), snapshot["world_id"]))
        blocked = self.store.advance_due(now_ms=1_000_000 + 2 * 15_000, max_ticks=2)["state"]
        self.assertEqual("blocked_inputs", blocked["cooking"]["preservation_program"]["status"])
        self.assertEqual(1, blocked["cooking"]["preservation_program"]["missing"]["containers"])
        recovered = self.store.advance_due(now_ms=1_000_000 + 20 * 15_000, max_ticks=18)["state"]
        self.assertEqual("active", recovered["cooking"]["preservation_program"]["status"])
        self.assertTrue(any(item.get("resource") == "containers" and item["actor"] == "orin" for item in recovered["environment"]["extraction_history"]))
        self.assertTrue(any(item["status"] == "blocked_inputs" for item in recovered["cooking"]["preservation_program"]["history"]))

    def test_validated_preservation_changes_future_cooking_inputs_and_shelf_life(self):
        snapshot = self.store.snapshot()
        state = snapshot["state"]
        state["event"]["status"] = "completed"
        state["places"]["communal_kitchen"]["status"] = "operational"
        state["resources"].update({"safe_meals": 0, "raw_food": 10, "tested_water": 5, "fuel": 5, "containers": 2})
        state["cooking"]["preservation_program"].update({"status": "active", "passed": True, "shelf_life_gain_ticks": 24, "tested_tick": 0, "tested_by": "imani"})
        for npc in state["npcs"].values():
            npc["needs"]["nutrition"] = 72
            npc["needs"]["rest"] = 72
        state["npcs"]["rae"]["needs"]["nutrition"] = 20
        with self.store.transaction() as connection:
            connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(state), snapshot["world_id"]))
        completed = self.store.advance_due(now_ms=1_000_000 + 24 * 15_000, max_ticks=24)["state"]
        order = completed["cooking"]["work_orders"][0]
        batch = completed["cooking"]["meal_batches"][0]
        self.assertEqual("drying", order["preservation"])
        self.assertEqual(1, order["required_inputs"]["containers"])
        self.assertEqual(2, order["required_inputs"]["fuel"])
        self.assertEqual("drying", batch["preservation"])
        self.assertEqual(56, batch["shelf_life_ticks"])
        self.assertEqual(56, batch["expires_tick"] - batch["inspected_tick"])

    def test_committed_action_projects_once_and_reaction_survives_restart(self):
        joined = self.store.apply_action(self.world["world_id"], "join-causal", "traveler", {"type": "join", "location": [8, 5]}, now_ms=1_000_000)
        projected = self.store.snapshot()["state"]["causality"]
        self.assertEqual(1, len(projected["pending_reactions"]))
        self.assertEqual("join", projected["pending_reactions"][0]["action"])
        self.store.process_causal_events(self.world["world_id"], now_ms=1_000_001)
        self.assertEqual(1, len(self.store.snapshot()["state"]["causality"]["pending_reactions"]))
        self.store.close()
        self.store = PersistentWorldStore(self.path)
        reacted = self.store.advance_due(now_ms=1_000_000 + 15_000, max_ticks=1)["state"]
        self.assertEqual(0, len(reacted["causality"]["pending_reactions"]))
        self.assertEqual(1, len(reacted["causality"]["completed_reactions"]))
        self.assertTrue(any(item["cause"].startswith("world-event:") and item["effect"].startswith("decision:reaction-") for item in reacted["consequences"]))

    def test_exploration_discovers_finite_material_sources(self):
        self.store.apply_action(self.world["world_id"], "join-explorer", "explorer", {"type": "join", "location": [0, 8]}, now_ms=1_000_000)
        traveled = self.store.apply_action(self.world["world_id"], "travel-north", "explorer", {"type": "explore_region", "region": "north_woods"}, now_ms=1_000_001)
        self.assertTrue(traveled["result"]["accepted"])
        gathered = self.store.apply_action(self.world["world_id"], "gather-timber", "explorer", {"type": "gather_material", "resource": "timber", "amount": 2}, now_ms=1_000_002)
        self.assertTrue(gathered["result"]["accepted"])
        state = self.store.snapshot()["state"]
        self.assertIn("north_woods", state["players"]["explorer"]["discovered_regions"])
        self.assertEqual(2, state["players"]["explorer"]["inventory"]["timber"])
        self.assertEqual(118, state["environment"]["regions"]["north_woods"]["stocks"]["timber"])
        self.assertEqual("explorer", state["environment"]["extraction_history"][-1]["actor"])
        self.assertGreater(state["economy"]["prices"]["timber"], 3.0)
        self.assertEqual(118, state["economy"]["market_signals"]["timber"]["remaining"])

    def test_shortage_changes_npc_procurement_and_provisional_value(self):
        snapshot = self.store.snapshot()
        state = snapshot["state"]
        state["resources"]["timber"] = 0
        with self.store.transaction() as connection:
            connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(state), snapshot["world_id"]))
        advanced = self.store.advance_due(now_ms=1_000_000 + 12 * 15_000, max_ticks=12)["state"]
        self.assertEqual(3, advanced["resources"]["timber"])
        self.assertEqual("orin", advanced["environment"]["extraction_history"][-1]["actor"])
        self.assertEqual("dev", advanced["environment"]["extraction_history"][-1]["verified_by"])
        self.assertIn("deliver timber", advanced["npcs"]["orin"]["intention"])
        self.assertTrue(any(item["kind"] == "material_procurement" and item["resource"] == "timber" for item in advanced["institutions"]["council"]["knowledge"]))
        claim = next(item for item in advanced["economy"]["claims"] if item["kind"] == "verified timber procurement")
        self.assertEqual("provisional", claim["status"])
        self.assertAlmostEqual(sum(advanced["economy"]["accounts"].values()), 0)

    def test_proximity_speech_gets_persistent_reply_and_private_audibility(self):
        joined = self.store.apply_action(self.world["world_id"], "join-speaker", "speaker", {"type": "join", "location": [9, 7]}, now_ms=1_000_000)
        spoken = self.store.apply_action(self.world["world_id"], "say-hello", "speaker", {"type": "speak", "content": "Hello, can you help with resources?", "target_id": "ada"}, expected_revision=joined["revision"], now_ms=1_000_001)
        self.assertTrue(spoken["result"]["accepted"])
        self.assertGreaterEqual(len(spoken["result"]["replies"]), 1)
        self.assertEqual("ada", spoken["result"]["replies"][0]["speaker_id"])
        self.assertTrue(all(reply.get("response_to") for reply in spoken["result"]["replies"]))
        self.assertFalse(any("won't stop choosing" in reply["content"] for reply in spoken["result"]["replies"]))
        snapshot = self.store.snapshot()
        self.assertTrue(any(message["kind"] == "reply" for message in actor_world_view(snapshot, "speaker")["state"]["communications"]["messages"]))
        self.assertFalse(actor_world_view(snapshot, "unrelated")["state"]["communications"]["messages"])
        advanced = self.store.advance_due(now_ms=1_000_000 + 8 * 15_000, max_ticks=8)["state"]
        self.assertTrue(any(message["kind"] == "autonomous" for message in advanced["communications"]["messages"]))

    def test_off_shift_work_reason_does_not_replace_social_dialogue(self):
        snapshot = self.store.snapshot()
        ada = snapshot["state"]["npcs"]["ada"]
        ada["intention"] = "rest"
        ada["reason"] = "The scheduled shift ended."

        reply = _npc_reply(ada, "I would like to socialize and share an idea with you.", snapshot["state"], "speaker")

        self.assertNotEqual("The scheduled shift ended.", reply)
        self.assertNotIn("scheduled shift ended", reply.lower())
        self.assertNotIn("trying to rest", reply.lower())
        self.assertTrue(any(word in reply.lower() for word in ("talk", "listen", "conversation")))

    def test_off_shift_resident_has_more_social_availability_than_busy_resident(self):
        snapshot = self.store.snapshot()
        resident = snapshot["state"]["npcs"]["ada"]
        resident["needs"].update({"nutrition": 80, "hydration": 80, "rest": 80, "belonging": 50})
        resident["energy"] = 80
        resident["relationships"]["speaker"] = {"trust": 0.5}
        off_shift = {**resident, "intention": "rest", "reason": "The scheduled shift ended."}
        busy = {**resident, "intention": "inspect water", "reason": "A safety inspection is underway."}

        available = _directed_response_decision(off_shift, "speaker", "Can we talk?", 12, 1)
        occupied = _directed_response_decision(busy, "speaker", "Can we talk?", 12, 1)

        self.assertGreater(available["probability"], occupied["probability"])
        self.assertGreater(available["factors"].get("social_availability", 0), 0)

    def test_directed_speech_always_receives_acknowledgement_when_elaboration_is_declined(self):
        joined = self.store.apply_action(
            self.world["world_id"], "join-acknowledgement", "speaker",
            {"type": "join", "location": [9, 7]}, now_ms=1_000_000,
        )
        state = self.store.snapshot()["state"]
        ada = state["npcs"]["ada"]
        content = next(
            candidate
            for index in range(1000)
            if not _directed_response_decision(
                ada, "speaker", candidate := f"Please acknowledge this message {index}",
                state["clock"]["tick"], 1,
            )["elaborated"]
        )

        spoken = self.store.apply_action(
            self.world["world_id"], "say-acknowledgement", "speaker",
            {"type": "speak", "content": content, "target_id": "ada"},
            expected_revision=joined["revision"], now_ms=1_000_001,
        )

        decision = spoken["result"]["response_decisions"][0]
        self.assertTrue(decision["responded"])
        self.assertFalse(decision["elaborated"])
        self.assertEqual("acknowledgement", decision["response_mode"])
        self.assertEqual(1, len(spoken["result"]["replies"]))
        self.assertIn("heard", spoken["result"]["replies"][0]["content"].lower())
        self.assertNotIn("directly influence", spoken["result"]["replies"][0]["content"].lower())
        self.assertNotIn("respond or ignore", spoken["result"]["replies"][0]["content"].lower())

    def test_autonomous_conversation_rotates_social_attention_and_restores_belonging(self):
        state = self.store.snapshot()["state"]
        for index, npc in enumerate(state["npcs"].values()):
            npc["location"] = [30 + (index % 6) * 5, 30 + (index // 6) * 5]
            npc["needs"]["belonging"] = 80
        state["npcs"]["ada"].update({"location": [8, 8], "intention": "rest", "reason": "The scheduled shift ended."})
        state["npcs"]["orin"].update({"location": [8, 9], "intention": "inspect stores", "reason": "Food reserves are low."})
        state["npcs"]["ada"]["needs"]["belonging"] = 10
        state["npcs"]["orin"]["needs"]["belonging"] = 11

        first = _process_proximity_speech(state, 8)
        second = _process_proximity_speech(state, 16)

        self.assertEqual("ada", first[0]["actor_id"])
        self.assertEqual("orin", second[0]["actor_id"])
        self.assertGreater(state["npcs"]["ada"]["needs"]["belonging"], 10)
        self.assertGreater(state["npcs"]["orin"]["needs"]["belonging"], 11)
        self.assertNotIn("scheduled shift ended", first[0]["payload"]["content"].lower())
        self.assertNotEqual(first[0]["payload"]["content"], second[0]["payload"]["content"])

    def test_autonomous_conversation_rotates_even_when_belonging_is_skewed(self):
        state = self.store.snapshot()["state"]
        for index, npc in enumerate(state["npcs"].values()):
            npc["location"] = [30 + (index % 6) * 5, 30 + (index // 6) * 5]
        for npc_id, belonging in (("ada", 1), ("orin", 50), ("mira", 95)):
            state["npcs"][npc_id]["location"] = [8, 8]
            state["npcs"][npc_id]["needs"]["belonging"] = belonging

        speakers = [
            _process_proximity_speech(state, tick)[0]["actor_id"]
            for tick in (8, 16, 24)
        ]

        self.assertEqual(["ada", "orin", "mira"], speakers)

    def test_autonomous_social_memory_retains_only_the_recent_bounded_window(self):
        state = self.store.snapshot()["state"]
        for index, npc in enumerate(state["npcs"].values()):
            npc["location"] = [30 + (index % 6) * 5, 30 + (index // 6) * 5]
        state["npcs"]["ada"]["location"] = [8, 8]
        state["npcs"]["orin"]["location"] = [8, 9]
        state["npcs"]["ada"]["memories"] = [
            {"tick": tick, "kind": "social_exchange", "text": f"old-{tick}"}
            for tick in range(250)
        ]
        state["npcs"]["ada"]["memories"].insert(0, {
            "tick": 1, "kind": "witnessed_conduct", "conduct_id": "conduct-1",
            "text": "Saw a contested taking and have not reported it yet.",
        })

        _process_proximity_speech(state, 256)
        migrate_state(state)

        memories = state["npcs"]["ada"]["memories"]
        self.assertEqual(251, len(memories))
        self.assertEqual(250, sum(memory.get("kind") == "social_exchange" for memory in memories))
        self.assertNotEqual("old-0", next(memory["text"] for memory in memories if memory.get("kind") == "social_exchange"))
        self.assertEqual(256, memories[-1]["tick"])
        self.assertTrue(any(memory.get("kind") == "witnessed_conduct" for memory in memories))

    def test_directed_non_english_speech_considers_only_the_nearby_target(self):
        joined = self.store.apply_action(self.world["world_id"], "join-directed", "speaker", {"type": "join", "location": [9, 7]}, now_ms=1_000_000)
        spoken = self.store.apply_action(
            self.world["world_id"], "say-directed-spanish", "speaker",
            {"type": "speak", "content": "Hola Ada, ¿puedes hablar conmigo?", "target_id": "ada"},
            expected_revision=joined["revision"], now_ms=1_000_001,
        )

        decision = spoken["result"]["response_decisions"][0]
        self.assertEqual("ada", decision["resident_id"])
        self.assertTrue(decision["eligible"])
        self.assertEqual("best_effort", decision["language_support"])
        self.assertGreater(decision["probability"], 0)
        self.assertLess(decision["probability"], 1)
        self.assertTrue(all(reply["speaker_id"] == "ada" for reply in spoken["result"]["replies"]))
        self.assertTrue(any(memory.get("actor") == "speaker" for memory in self.store.snapshot()["state"]["npcs"]["ada"]["memories"]))

    def test_witnessed_discourse_accumulates_into_later_council_action_without_direct_physical_change(self):
        snapshot = self.store.snapshot()
        state = snapshot["state"]
        state["event"]["status"] = "completed"
        original_places = json.loads(json.dumps(state["places"]))
        with self.store.transaction() as connection:
            connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(state), snapshot["world_id"]))
        self.store.apply_action(snapshot["world_id"], "discourse-join", "organizer", {"type": "join", "location": [8, 5]}, now_ms=1_000_000)

        for index in range(6):
            self.store.apply_action(
                snapshot["world_id"], f"storage-concern-{index}", "organizer",
                {"type": "speak", "content": "We should discuss storage before provisions spoil."},
                now_ms=1_000_001 + index * 15_000,
            )
            if index < 5:
                self.store.advance_due(now_ms=1_000_000 + (index + 1) * 15_000, max_ticks=1)

        discussed = self.store.advance_due(now_ms=1_000_000 + 6 * 15_000, max_ticks=1)["state"]
        self.assertEqual(original_places, discussed["places"])
        self.assertIsNone(discussed["institutions"]["council"]["current_initiative"])
        self.assertEqual(6, len(discussed["communications"]["public_discourse"]["claims"]))
        self.assertEqual(2, len(discussed["communications"]["public_discourse"]["escalations"]))
        self.assertEqual(40.0, discussed["institutions"]["council"]["public_pressure"]["storage"])

        self.store.close()
        self.store = PersistentWorldStore(self.path)
        decided = self.store.advance_due(now_ms=1_000_000 + 12 * 15_000, max_ticks=6)["state"]
        initiative = decided["institutions"]["council"]["current_initiative"]
        self.assertEqual("storage", initiative["priority"])
        self.assertTrue(any(source.startswith("discourse:") for source in initiative["causal_sources"]))
        self.assertTrue(any(item["kind"] == "witnessed_public_discourse" for item in decided["institutions"]["council"]["knowledge"]))
        self.assertTrue(any(item["effect"] == "council-pressure:storage:+20" for item in decided["consequences"]))

    def test_same_tick_speech_repetition_is_one_civic_claim(self):
        self.store.apply_action(self.world["world_id"], "spam-join", "speaker", {"type": "join", "location": [8, 5]}, now_ms=1_000_000)
        for index in range(3):
            result = self.store.apply_action(
                self.world["world_id"], f"same-tick-{index}", "speaker",
                {"type": "speak", "content": "The water supply deserves discussion."}, now_ms=1_000_001 + index,
            )
            self.assertFalse(result["result"]["physical_change"])
        discourse = self.store.snapshot()["state"]["communications"]["public_discourse"]
        self.assertEqual(1, len(discourse["claims"]))
        self.assertFalse(discourse["escalations"])

    def test_npcs_originate_witness_share_and_act_on_civic_information_without_a_player(self):
        snapshot = self.store.snapshot()
        seeded = snapshot["state"]
        seeded["event"]["status"] = "completed"
        seeded["institutions"]["council"]["completed_initiatives"].append({
            "id": "civic-history", "priority": "water", "status": "completed",
            "causal_sources": [], "required_evidence": [], "evidence_tags": [],
        })
        with self.store.transaction() as connection:
            connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(seeded), self.world["world_id"]))
        advanced = self.store.advance_due(now_ms=1_000_000 + 25 * 15_000, max_ticks=25)["state"]
        self.assertFalse(advanced["players"])
        discourse = advanced["communications"]["public_discourse"]
        self.assertEqual(3, len(discourse["claims"]))
        self.assertEqual(1, len(discourse["escalations"]))
        escalation = discourse["escalations"][0]
        self.assertEqual("sanitation", escalation["priority"])
        self.assertTrue(all(speaker in advanced["npcs"] for speaker in escalation["speakers"]))
        self.assertGreaterEqual(len(escalation["witnesses"]), 2)
        self.assertTrue(any(memory.get("kind") == "overheard_discourse" for npc in advanced["npcs"].values() for memory in npc["memories"]))
        self.assertTrue(any(item["kind"] == "witnessed_public_discourse" for item in advanced["institutions"]["council"]["knowledge"]))

        advanced["institutions"]["council"]["current_initiative"] = None
        with self.store.transaction() as connection:
            connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(advanced), self.world["world_id"]))
        decided = self.store.advance_due(now_ms=1_000_000 + 26 * 15_000, max_ticks=1)["state"]
        self.assertTrue(any(npc["intention"] == "discuss sanitation concern with neighbors" for npc in decided["npcs"].values()))
        self.assertTrue(any(item["effect"] == "council-pressure:sanitation:+20" for item in decided["consequences"]))

    def test_authoritative_site_checkout_extraction_and_idempotent_restart(self):
        joined = self.store.apply_action(self.world["world_id"], "site-join", "worker", {"type": "join", "location": [8, 9]}, now_ms=1_000_000)
        checkout = self.store.apply_action(self.world["world_id"], "axe-checkout", "worker", {"type": "interact_site", "site_id": "tool-counter", "operation": "checkout", "item": "axe"}, expected_revision=joined["revision"], now_ms=1_000_001)
        self.assertTrue(checkout["result"]["accepted"])
        self.assertEqual("completed", checkout["result"]["status"])
        self.assertEqual("actor_inventory", checkout["result"]["custody"])
        self.assertEqual({"axe": 1}, checkout["result"]["inventory_delta"])
        repositioned = self.store.apply_action(self.world["world_id"], "boundary-position", "worker", {"type": "join", "location": [0, 8]}, expected_revision=checkout["revision"], now_ms=1_000_002)
        traveled = self.store.apply_action(self.world["world_id"], "woods-expedition", "worker", {"type": "explore_region", "region": "north_woods"}, expected_revision=repositioned["revision"], now_ms=1_000_003)
        chopped = self.store.apply_action(self.world["world_id"], "chop-oak-once", "worker", {"type": "interact_site", "site_id": "old-oak", "operation": "chop"}, expected_revision=traveled["revision"], now_ms=1_000_004)
        replayed = self.store.apply_action(self.world["world_id"], "chop-oak-once", "worker", {"type": "interact_site", "site_id": "old-oak", "operation": "chop"}, now_ms=1_000_005)
        self.assertEqual(chopped, replayed)
        self.assertEqual("proposal_recorded", chopped["result"]["status"])
        self.assertEqual("none", chopped["result"]["custody"])
        self.assertEqual({}, chopped["result"]["inventory_delta"])
        self.assertIn("accept", chopped["result"]["next_step"])
        action_id = chopped["result"]["outputs"]["canonical_action_id"]
        proposed = self.store.snapshot(); state = proposed["state"]
        self.assertEqual(10, state["resource_sites"]["old-oak"]["stock"])
        self.assertEqual(0, state["players"]["worker"]["inventory"].get("timber", 0))
        state["npcs"]["mira"]["location"] = [8, 9]; state["npcs"]["mira"]["current_region"] = "north_woods"
        with self.store.transaction() as connection:
            connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(state), proposed["world_id"]))
        accepted = self.store.apply_action(self.world["world_id"], "extract-accept", "worker", {"type": "shared_action", "operation": "accept", "shared_action_id": action_id})
        reserved = self.store.apply_action(self.world["world_id"], "extract-reserve", "worker", {"type": "shared_action", "operation": "reserve", "shared_action_id": action_id})
        self.assertTrue(accepted["result"]["accepted"]); self.assertTrue(reserved["result"]["accepted"])
        self.store.apply_action(self.world["world_id"], "extract-execute", "worker", {"type": "shared_action", "operation": "execute", "shared_action_id": action_id, "samples": [{"stock_before": 10, "observed_yield": 2}]})
        self.store.advance_due(now_ms=1_000_000 + 4 * 15_000, max_ticks=4)
        submitted = self.store.snapshot()["state"]
        self.assertEqual(8, submitted["resource_sites"]["old-oak"]["stock"])
        self.assertEqual(0, submitted["players"]["worker"]["inventory"].get("timber", 0))
        submitted["npcs"]["mira"]["location"] = [8, 9]; submitted["npcs"]["mira"]["current_region"] = "north_woods"
        with self.store.transaction() as connection:
            connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(submitted), self.world["world_id"]))
        self.store.apply_action(self.world["world_id"], "extract-verify", "mira", {"type": "shared_action", "operation": "verify", "shared_action_id": action_id})
        self.store.apply_action(self.world["world_id"], "extract-commission", "mira", {"type": "shared_action", "operation": "commission", "shared_action_id": action_id})
        self.assertEqual(2, self.store.snapshot()["state"]["players"]["worker"]["inventory"]["timber"])
        self.store.close()
        self.store = PersistentWorldStore(self.path)
        reopened = self.store.snapshot()["state"]
        self.assertEqual(8, reopened["resource_sites"]["old-oak"]["stock"])
        self.assertEqual("worker", reopened["resource_sites"]["old-oak"]["history"][-1]["actor"])

    def test_local_tree_depletion_creates_blocked_then_verified_spatial_stewardship_across_restart(self):
        snapshot = self.store.snapshot()
        state = snapshot["state"]
        state["event"]["status"] = "completed"
        state["resource_sites"]["old-oak"]["stock"] = 2
        state["environment"]["regions"]["north_woods"]["stocks"]["timber"] = 112
        state["resources"]["tested_water"] = 0
        for npc in state["npcs"].values():
            npc["needs"].update({"nutrition": 85, "hydration": 85, "rest": 85})
        with self.store.transaction() as connection:
            connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(state), snapshot["world_id"]))
        proposed = self.store.advance_due(now_ms=1_000_000 + 3 * 15_000, max_ticks=3)["state"]
        order = proposed["environment"]["stewardship_orders"][0]
        self.assertEqual("blocked_inputs", order["status"])
        self.assertEqual({"tested_water": 2}, order["blockers"][-1]["missing"])
        self.assertEqual(2, proposed["resource_sites"]["old-oak"]["stock"])
        contract = proposed["economy"]["work_contracts"][0]
        self.assertEqual("accepted", contract["status"])
        self.assertEqual(["proposed", "countered", "accepted"], [item["status"] for item in contract["history"]])
        self.assertFalse(contract["spendable"])

        proposed["resources"]["tested_water"] = 4
        with self.store.transaction() as connection:
            connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(proposed), snapshot["world_id"]))
        self.store.close()
        self.store = PersistentWorldStore(self.path)
        completed = self.store.advance_due(now_ms=1_000_000 + 40 * 15_000, max_ticks=38)["state"]
        order = completed["environment"]["stewardship_orders"][0]
        self.assertEqual("completed", order["status"])
        self.assertEqual(4, order["restored_amount"])
        self.assertEqual(6, completed["resource_sites"]["old-oak"]["stock"])
        self.assertEqual(116, completed["environment"]["regions"]["north_woods"]["stocks"]["timber"])
        self.assertTrue(all(blocker["status"] == "recovered" for blocker in order["blockers"]))
        self.assertEqual("settlement", completed["npcs"]["cal"]["current_region"])
        self.assertEqual("settlement", completed["npcs"]["mira"]["current_region"])
        self.assertTrue(any(item["change"].startswith("reforestation recovery verified") for item in completed["evidence"]))
        self.assertTrue(any(item["kind"] == "verified ecological restoration labor" for item in completed["economy"]["claims"]))
        contract = completed["economy"]["work_contracts"][0]
        self.assertEqual("settled_provisional", contract["status"])
        self.assertEqual(4, contract["outcome"]["verified_restored_units"])
        labor_claim = next(item for item in completed["economy"]["claims"] if item["kind"] == "verified ecological restoration labor")
        self.assertEqual(contract["id"], labor_claim["contract_id"])
        self.assertEqual(contract["agreed"][order["worker"]], labor_claim["amount"])
        self.assertFalse(labor_claim["spendable"])
        self.assertTrue(any(item["effect"].startswith("local-stock-restored:old-oak:+4") for item in completed["consequences"]))
        self.assertTrue(any(memory["kind"] == "completed_work" and order["id"] in memory["text"] for memory in completed["npcs"]["cal"]["memories"]))
        completed = self.store.advance_due(now_ms=1_000_000 + 56 * 15_000, max_ticks=16)["state"]
        lesson = next(item for item in completed["education"]["teaching_orders"] if item["domain"] == "environmental_stewardship")
        self.assertEqual("completed", lesson["status"])
        self.assertEqual("cal", lesson["instructor"])
        self.assertEqual("rae", lesson["learner"])
        self.assertEqual(0, lesson["demonstration"]["after"])
        self.assertTrue(lesson["learning"]["requires_verified_practice"])
        self.assertEqual(0, completed["npcs"]["rae"]["competency_records"]["environmental_stewardship"]["demonstrated"])
        environmental_practice = next(item for item in completed["education"]["practice_orders"] if item["domain"] == "environmental_stewardship")
        self.assertEqual("awaiting_real_work", environmental_practice["status"])
        self.assertFalse(any(item["kind"] == "verified competency demonstration" and item["actor"] == "rae" for item in completed["economy"]["claims"]))
        instruction_record = completed["shared_actions"]["records"][lesson["canonical_action_id"]]
        instruction_states = [event["state"] for event in completed["shared_actions"]["ledger"] if event["action_id"] == instruction_record["id"]]
        self.assertEqual(["proposed", "awaiting_acceptances", "accepted", "reserved", "in_progress", "submitted", "verified", "commissioned"], instruction_states)
        self.assertEqual({"cal": "accepted", "rae": "accepted"}, lesson["consent"])
        self.assertTrue(any("still need verified practice" in memory["text"] for memory in completed["npcs"]["rae"]["memories"]))
        self.assertFalse(any(claim["action_id"] == instruction_record["id"] for claim in completed["shared_actions"]["valuation_claims"]))

        completed["resource_sites"]["pine-stand"]["stock"] = 2
        completed["environment"]["regions"]["north_woods"]["stocks"]["timber"] -= 6
        completed["resources"]["tested_water"] = 4
        completed["npcs"]["cal"]["needs"]["rest"] = 80
        completed["npcs"]["rae"]["needs"].update({"nutrition": 80, "hydration": 80, "rest": 80})
        with self.store.transaction() as connection:
            connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(completed), snapshot["world_id"]))
        self.store.close()
        self.store = PersistentWorldStore(self.path)
        reassigned = self.store.advance_due(now_ms=1_000_000 + 57 * 15_000, max_ticks=1)["state"]
        second_order = reassigned["environment"]["stewardship_orders"][1]
        self.assertEqual("pine-stand", second_order["site_id"])
        self.assertEqual("rae", second_order["worker"])
        self.assertEqual("cal", second_order["supervisor"])
        practiced = self.store.advance_due(now_ms=1_000_000 + 100 * 15_000, max_ticks=43)["state"]
        practice = next(item for item in practiced["education"]["practice_orders"] if item["domain"] == "environmental_stewardship")
        self.assertEqual("completed", practice["status"])
        self.assertGreaterEqual(practiced["npcs"]["rae"]["competency_records"]["environmental_stewardship"]["demonstrated"], 0.3)
        self.assertTrue(any(item["effect"].startswith("competency-demonstrated:rae:environmental_stewardship") for item in practiced["consequences"]))

    def test_concurrent_site_actions_cannot_extract_the_same_revision_twice(self):
        joined = self.store.apply_action(self.world["world_id"], "race-join", "racer", {"type": "join", "location": [8, 9]}, now_ms=1_000_000)
        checkout = self.store.apply_action(self.world["world_id"], "race-axe", "racer", {"type": "interact_site", "site_id": "tool-counter", "operation": "checkout", "item": "axe"}, expected_revision=joined["revision"], now_ms=1_000_001)
        boundary = self.store.apply_action(self.world["world_id"], "race-boundary", "racer", {"type": "join", "location": [0, 8]}, expected_revision=checkout["revision"], now_ms=1_000_002)
        traveled = self.store.apply_action(self.world["world_id"], "race-travel", "racer", {"type": "explore_region", "region": "north_woods"}, expected_revision=boundary["revision"], now_ms=1_000_003)

        def chop(action_id):
            worker_store = PersistentWorldStore(self.path)
            try:
                return worker_store.apply_action(self.world["world_id"], action_id, "racer", {"type": "interact_site", "site_id": "old-oak", "operation": "chop"}, expected_revision=traveled["revision"], now_ms=1_000_004)
            except RevisionConflict:
                return None
            finally:
                worker_store.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(chop, ["race-chop-a", "race-chop-b"]))
        self.assertEqual(1, sum(result is not None for result in results))
        snapshot = self.store.snapshot()["state"]
        self.assertEqual(10, snapshot["resource_sites"]["old-oak"]["stock"])
        self.assertEqual(1, sum(record["definition"]["action_type"] == "extract_site_resource" for record in snapshot["shared_actions"]["records"].values()))

    def test_measured_shortage_generates_autonomous_finite_extraction_but_not_teleporting_deposit(self):
        snapshot = self.store.snapshot(); state = snapshot["state"]
        state["resources"]["timber"] = 0
        site_before = state["resource_sites"]["old-oak"]["stock"] + state["resource_sites"]["pine-stand"]["stock"]
        regional_before = state["environment"]["regions"]["north_woods"]["stocks"]["timber"]
        with self.store.transaction() as connection:
            connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(state), snapshot["world_id"]))
        final = self.store.advance_due(now_ms=1_000_000 + 60 * 15_000, max_ticks=60)["state"]
        demand = next(item for item in final["shared_actions"]["demands"] if item["id"] == "need:finite-extraction:timber")
        action = final["shared_actions"]["records"][demand["action_id"]]
        self.assertEqual("commissioned", action["state"])
        self.assertEqual("awaiting_transport", demand["status"])
        self.assertEqual(action["definition"]["output_amount"], final["npcs"]["cal"]["inventory"]["timber"])
        site_after = final["resource_sites"]["old-oak"]["stock"] + final["resource_sites"]["pine-stand"]["stock"]
        self.assertEqual(action["definition"]["output_amount"], site_before - site_after)
        # Natural regeneration or legacy communal procurement may occur later,
        # but the canonical action's regional ledger remains exactly conserved.
        self.assertEqual(action["output"]["yield"], action["output"]["regional_before"] - action["output"]["regional_after"])
        self.assertLessEqual(action["output"]["regional_after"], regional_before)
        self.assertEqual(0, sum(final["shared_actions"]["valuation_accounts_milli"].values()))
        self.assertFalse(final["shared_actions"]["valuation_claims"][-1]["spendable"])

    def test_authoritative_farm_matures_from_runclock(self):
        joined = self.store.apply_action(self.world["world_id"], "farmer-join", "farmer", {"type": "join", "location": [7, 9]}, now_ms=1_000_000)
        tools = self.store.apply_action(self.world["world_id"], "farm-tools", "farmer", {"type": "interact_site", "site_id": "tool-counter", "operation": "checkout", "item": "farm_tools"}, expected_revision=joined["revision"], now_ms=1_000_001)
        seed = self.store.apply_action(self.world["world_id"], "farm-seed", "farmer", {"type": "interact_site", "site_id": "tool-counter", "operation": "checkout", "item": "seed"}, expected_revision=tools["revision"], now_ms=1_000_002)
        at_plot = self.store.apply_action(self.world["world_id"], "farm-position", "farmer", {"type": "join", "location": [3, 12]}, expected_revision=seed["revision"], now_ms=1_000_003)
        tilled = self.store.apply_action(self.world["world_id"], "till-plot", "farmer", {"type": "interact_site", "site_id": "farm-plot", "operation": "till"}, expected_revision=at_plot["revision"], now_ms=1_000_004)
        sowed = self.store.apply_action(self.world["world_id"], "sow-plot", "farmer", {"type": "interact_site", "site_id": "farm-plot", "operation": "sow"}, expected_revision=tilled["revision"], now_ms=1_000_005)
        self.assertEqual({"seed": -1}, sowed["result"]["inventory_delta"])
        self.assertEqual("growing", self.store.snapshot()["state"]["resource_sites"]["farm-plot"]["stage"])
        ripe = self.store.advance_due(now_ms=1_000_000 + 12 * 15_000, max_ticks=12)["state"]["resource_sites"]["farm-plot"]
        self.assertEqual("ripe", ripe["stage"])
        self.assertEqual(12, ripe["stock"])

    def test_founding_table_seeds_a_twelve_adult_community(self):
        state = self.world["state"]
        self.assertEqual(len(state["npcs"]), 12)
        self.assertEqual(state["event"]["id"], "founding-table")
        self.assertIn("water_source", state["places"])
        self.assertIn("communal_kitchen", state["places"])
        self.assertIn("unclaimed_land", state["places"])

    def test_runclock_is_durable_and_bounded(self):
        advanced = self.store.advance_due(now_ms=1_000_000 + 500 * 15_000, max_ticks=240)
        self.assertEqual(advanced["tick"], 240)
        self.assertEqual(advanced["advanced_ticks"], 240)
        self.assertEqual(advanced["catchup_remaining"], 260)
        reopened_store = PersistentWorldStore(self.path)
        reopened = reopened_store.snapshot()
        self.assertEqual(reopened["tick"], 240)
        reopened_store.close()
        continued = self.store.advance_due(now_ms=1_000_000 + 500 * 15_000, max_ticks=240)
        self.assertEqual(continued["tick"], 480)

    def test_action_is_idempotent_and_revision_checked(self):
        action = {"type": "publish_order", "priority": "communal_kitchen", "terms": {"inspection": True}}
        first = self.store.apply_action(self.world["world_id"], "action-0001", "sirix_1", action, expected_revision=1, now_ms=1_000_001)
        duplicate = self.store.apply_action(self.world["world_id"], "action-0001", "sirix_1", action, expected_revision=1, now_ms=1_000_002)
        self.assertEqual(first, duplicate)
        self.assertEqual(len(self.store.snapshot()["state"]["event"]["competing_orders"]), 1)
        with self.assertRaises(RevisionConflict):
            self.store.apply_action(self.world["world_id"], "action-0002", "other", action, expected_revision=1)

    def test_only_one_runclock_owner_holds_a_live_lease(self):
        self.assertTrue(self.store.acquire_lease(self.world["world_id"], "server-a", 1_000_000))
        self.assertFalse(self.store.acquire_lease(self.world["world_id"], "server-b", 1_000_001))
        self.assertTrue(self.store.acquire_lease(self.world["world_id"], "server-b", 1_006_000))

    def test_events_replay_after_a_cursor(self):
        self.store.advance_due(now_ms=1_000_000 + 12 * 15_000)
        events = self.store.events(self.world["world_id"])
        self.assertTrue(events)
        cursor = events[0]["sequence"]
        later = self.store.events(self.world["world_id"], after=cursor)
        self.assertTrue(all(event["sequence"] > cursor for event in later))

    def test_founding_table_progresses_without_a_player_and_creates_a_meal(self):
        completed = self.store.advance_due(now_ms=1_000_000 + 240 * 15_000, max_ticks=240)
        state = completed["state"]
        self.assertEqual(state["event"]["status"], "completed")
        self.assertTrue(state["food"]["meal_history"])
        meal = state["food"]["meal_history"][0]
        self.assertGreaterEqual(meal["safety"], 0.75)
        self.assertTrue(any(record.get("inspector") == "imani" for record in state["evidence"]))
        self.assertTrue(state["economy"]["claims"])
        self.assertAlmostEqual(sum(state["economy"]["accounts"].values()), 0)
        self.assertTrue(all(npc["memories"] for npc in state["npcs"].values()))

    def test_completed_history_recursively_creates_and_resolves_new_work(self):
        progressed = self.store.advance_due(now_ms=1_000_000 + 420 * 15_000, max_ticks=420)
        state = progressed["state"]
        completed = state["institutions"]["council"]["completed_initiatives"]
        self.assertGreaterEqual(len(completed), 2)
        self.assertTrue(state["institutions"]["council"]["knowledge"])
        self.assertTrue(any(item["cause"].startswith("observation:council") and item["effect"].startswith("initiative:") for item in state["consequences"]))
        self.assertTrue(any(item["cause"].startswith("initiative:") and item["effect"].startswith("world-change:") for item in state["consequences"]))
        self.assertNotEqual(completed[0]["priority"], completed[1]["priority"])
        worker = completed[0]["priority"]
        self.assertTrue(any(worker in memory["text"] for npc in state["npcs"].values() for memory in npc["memories"] if memory["kind"] == "completed_work"))

    def test_player_input_changes_a_later_institutional_decision(self):
        self.store.advance_due(now_ms=1_000_000 + 239 * 15_000, max_ticks=239)
        snapshot = self.store.snapshot()
        result = self.store.apply_action(snapshot["world_id"], "endorse-0001", "citizen-1", {"type": "endorse_priority", "priority": "water"}, expected_revision=snapshot["revision"], now_ms=4_600_001)
        self.assertTrue(result["result"]["accepted"])
        decided = self.store.advance_due(now_ms=1_000_000 + 240 * 15_000, max_ticks=1)
        self.assertEqual(decided["state"]["institutions"]["council"]["current_initiative"]["priority"], "water")
        self.assertTrue(any(item["cause"] == "player-endorsement:citizen-1" for item in decided["state"]["consequences"]))

    def test_old_world_state_is_migrated_without_losing_history(self):
        connection = self.store._connection()
        state = self.world["state"]
        state.pop("institutions")
        state.pop("consequences")
        state["schema"] = 1
        import json
        connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(state), self.world["world_id"]))
        migrated = self.store.snapshot()["state"]
        self.assertEqual(migrated["schema"], 31)
        self.assertIn("council", migrated["institutions"])
        self.assertEqual(migrated["event"]["id"], "founding-table")

    def test_shortage_generates_procurement_and_prevents_or_recovers_blocked_work(self):
        progressed = self.store.advance_due(now_ms=1_000_000 + 600 * 15_000, max_ticks=600)
        state = progressed["state"]
        self.assertTrue(state["environment"]["extraction_history"])
        extraction = next(item for item in state["environment"]["extraction_history"] if item.get("resource") == "stone" or "stone" in item.get("outputs", {}))
        self.assertEqual("orin", extraction["actor"])
        self.assertTrue(any(item["effect"].startswith("verified-procurement:stone") or item["effect"].startswith("procurement:") for item in state["consequences"]))
        self.assertTrue(state["institutions"]["council"]["completed_initiatives"])

    def test_witnessed_conduct_becomes_memory_report_finding_and_bounty(self):
        joined = self.store.apply_action(self.world["world_id"], "join-offender", "player-1", {"type": "join", "location": [8, 5]}, expected_revision=1)
        taken = self.store.apply_action(self.world["world_id"], "take-stone", "player-1", {"type": "misappropriate_resource", "resource": "stone", "amount": 2}, expected_revision=joined["revision"])
        self.assertGreater(taken["result"]["witness_count"], 0)
        immediate = self.store.snapshot()["state"]
        self.assertEqual(immediate["players"]["player-1"]["reputation"], 0)
        self.assertFalse(immediate["institutions"]["justice"]["reports"])
        reported = self.store.advance_due(now_ms=1_000_000 + 2 * 15_000, max_ticks=2)["state"]
        self.assertTrue(reported["institutions"]["justice"]["reports"])
        self.assertEqual(reported["institutions"]["justice"]["cases"][0]["status"], "investigating")
        decided = self.store.advance_due(now_ms=1_000_000 + 8 * 15_000, max_ticks=6)["state"]
        self.assertEqual(decided["institutions"]["justice"]["cases"][0]["status"], "restitution_due")
        self.assertEqual(decided["players"]["player-1"]["reputation"], -8)
        escalated = self.store.advance_due(now_ms=1_000_000 + 34 * 15_000, max_ticks=26)["state"]
        self.assertEqual(escalated["institutions"]["justice"]["cases"][0]["status"], "bounty_active")
        self.assertEqual(escalated["institutions"]["justice"]["bounties"][0]["provisional_reward"], 6.0)
        self.assertIn("locate player-1", escalated["npcs"]["orin"]["intention"])

    def test_restitution_restores_stock_closes_case_and_cancels_escalation(self):
        joined = self.store.apply_action(self.world["world_id"], "join-returner", "player-1", {"type": "join", "location": [8, 5]}, expected_revision=1)
        self.store.apply_action(self.world["world_id"], "take-tools", "player-1", {"type": "misappropriate_resource", "resource": "tools", "amount": 1}, expected_revision=joined["revision"])
        decided = self.store.advance_due(now_ms=1_000_000 + 8 * 15_000, max_ticks=8)
        case = decided["state"]["institutions"]["justice"]["cases"][0]
        returned = self.store.apply_action(self.world["world_id"], "return-tools", "player-1", {"type": "return_resource", "case_id": case["id"], "resource": "tools", "amount": 1}, expected_revision=decided["revision"])
        self.assertEqual(returned["result"]["case_status"], "closed_restituted")
        state = self.store.snapshot()["state"]
        self.assertEqual(state["resources"]["tools"], 12)
        self.assertEqual(state["players"]["player-1"]["reputation"], -4)
        self.assertTrue(any(item["effect"] == f"case-closed:{case['id']}" for item in state["consequences"]))

    def test_unwitnessed_conduct_does_not_create_institutional_knowledge(self):
        joined = self.store.apply_action(self.world["world_id"], "join-remote", "player-1", {"type": "join", "location": [18, 18]}, expected_revision=1)
        taken = self.store.apply_action(self.world["world_id"], "take-remote", "player-1", {"type": "misappropriate_resource", "resource": "stone", "amount": 1}, expected_revision=joined["revision"])
        self.assertEqual(taken["result"]["witness_count"], 0)
        state = self.store.advance_due(now_ms=1_000_000 + 20 * 15_000, max_ticks=20)["state"]
        self.assertFalse(state["institutions"]["justice"]["reports"])
        self.assertFalse(state["institutions"]["justice"]["cases"])

    def test_world_view_keeps_private_memories_and_other_inventories_private(self):
        joined = self.store.apply_action(self.world["world_id"], "join-private", "player-1", {"type": "join", "location": [8, 5]}, expected_revision=1)
        self.store.apply_action(self.world["world_id"], "take-private", "player-1", {"type": "misappropriate_resource", "resource": "stone", "amount": 1}, expected_revision=joined["revision"])
        self.store.advance_due(now_ms=1_000_000 + 3 * 15_000, max_ticks=3)
        snapshot = self.store.snapshot()
        accused_view = actor_world_view(snapshot, "player-1")
        other_view = actor_world_view(snapshot, "player-2")
        self.assertTrue(accused_view["state"]["institutions"]["justice"]["reports"])
        self.assertFalse(other_view["state"]["institutions"]["justice"]["reports"])
        self.assertNotIn("inventory", other_view["state"]["players"]["player-1"])
        self.assertTrue(all(memory["kind"] != "witnessed_conduct" for npc in other_view["state"]["npcs"].values() for memory in npc["memories"]))
        self.assertTrue(all("witnesses" not in item for item in other_view["state"]["consequences"]))

    def test_npc_accepts_bounty_makes_contact_and_earns_only_after_recovery(self):
        joined = self.store.apply_action(self.world["world_id"], "join-npc-recovery", "player-1", {"type": "join", "location": [8, 5]}, expected_revision=1)
        self.store.apply_action(self.world["world_id"], "take-npc-recovery", "player-1", {"type": "misappropriate_resource", "resource": "stone", "amount": 2}, expected_revision=joined["revision"])
        escalated = self.store.advance_due(now_ms=1_000_000 + 34 * 15_000, max_ticks=34)
        bounty = escalated["state"]["institutions"]["justice"]["bounties"][0]
        self.assertIsNone(bounty["assignee"])
        contacted = self.store.advance_due(now_ms=1_000_000 + 42 * 15_000, max_ticks=8)
        bounty = contacted["state"]["institutions"]["justice"]["bounties"][0]
        self.assertEqual(bounty["assignee"], {"id": "orin", "kind": "npc", "accepted_tick": bounty["created_tick"] + 2})
        self.assertIsNotNone(bounty["contact"])
        self.assertFalse(any(claim["kind"] == "verified public recovery" for claim in contacted["state"]["economy"]["claims"]))
        case = contacted["state"]["institutions"]["justice"]["cases"][0]
        returned = self.store.apply_action(self.world["world_id"], "return-after-contact", "player-1", {"type": "return_resource", "case_id": case["id"], "resource": "stone", "amount": 2}, expected_revision=contacted["revision"])
        self.assertTrue(returned["result"]["accepted"])
        state = self.store.snapshot()["state"]
        self.assertEqual(state["institutions"]["justice"]["bounties"][0]["status"], "completed_recovery")
        self.assertTrue(any(claim["actor"] == "orin" and claim["kind"] == "verified public recovery" and claim["amount"] == 6.0 for claim in state["economy"]["claims"]))
        self.assertAlmostEqual(sum(state["economy"]["accounts"].values()), 0)

    def test_player_and_npc_have_equal_bounty_terms_and_contact_is_required(self):
        offender_join = self.store.apply_action(self.world["world_id"], "join-player-recovery", "offender", {"type": "join", "location": [8, 5]}, expected_revision=1)
        self.store.apply_action(self.world["world_id"], "take-player-recovery", "offender", {"type": "misappropriate_resource", "resource": "tools", "amount": 1}, expected_revision=offender_join["revision"])
        escalated = self.store.advance_due(now_ms=1_000_000 + 34 * 15_000, max_ticks=34)
        bounty = escalated["state"]["institutions"]["justice"]["bounties"][0]
        premature = self.store.apply_action(self.world["world_id"], "remote-return", "offender", {"type": "return_resource", "case_id": bounty["case_id"], "resource": "tools", "amount": 1}, expected_revision=escalated["revision"])
        self.assertFalse(premature["result"]["accepted"])
        guard_join = self.store.apply_action(self.world["world_id"], "join-guard", "guard-player", {"type": "join", "location": [8, 6]}, expected_revision=premature["revision"])
        accepted = self.store.apply_action(self.world["world_id"], "accept-player-bounty", "guard-player", {"type": "accept_bounty", "bounty_id": bounty["id"]}, expected_revision=guard_join["revision"])
        self.assertEqual(accepted["result"]["provisional_reward"], bounty["provisional_reward"])
        moved = self.store.apply_action(self.world["world_id"], "guard-move", "guard-player", {"type": "move", "location": [8, 5]}, expected_revision=accepted["revision"])
        contact = self.store.apply_action(self.world["world_id"], "guard-contact", "guard-player", {"type": "request_restitution", "bounty_id": bounty["id"]}, expected_revision=moved["revision"])
        self.assertTrue(contact["result"]["accepted"])
        returned = self.store.apply_action(self.world["world_id"], "guarded-return", "offender", {"type": "return_resource", "case_id": bounty["case_id"], "resource": "tools", "amount": 1}, expected_revision=contact["revision"])
        self.assertTrue(returned["result"]["accepted"])
        state = self.store.snapshot()["state"]
        self.assertTrue(any(claim["actor"] == "guard-player" and claim["kind"] == "verified public recovery" and claim["amount"] == 6.0 for claim in state["economy"]["claims"]))

    def test_substantiated_history_causes_deliberation_then_new_access_policy(self):
        joined = self.store.apply_action(self.world["world_id"], "join-policy-cause", "player-1", {"type": "join", "location": [8, 5]}, expected_revision=1)
        self.store.apply_action(self.world["world_id"], "take-policy-cause", "player-1", {"type": "misappropriate_resource", "resource": "stone", "amount": 1}, expected_revision=joined["revision"])
        proposed = self.store.advance_due(now_ms=1_000_000 + 12 * 15_000, max_ticks=12)["state"]
        access = proposed["institutions"]["governance"]["resource_access"]
        self.assertEqual(access["mode"], "open_stores")
        self.assertEqual(access["proposal"]["status"], "proposed")
        self.assertTrue(any(item["cause"].startswith("substantiated-cases:") and item["effect"].startswith("policy-proposal:") for item in proposed["consequences"]))
        enacted = self.store.advance_due(now_ms=1_000_000 + 24 * 15_000, max_ticks=12)["state"]
        self.assertEqual(enacted["institutions"]["governance"]["resource_access"]["mode"], "recorded_checkout")
        self.assertTrue(any(item["effect"] == "world-rule:recorded_checkout" for item in enacted["consequences"]))

    def test_recorded_checkout_changes_inventory_and_on_time_return_builds_trust(self):
        offender = self.store.apply_action(self.world["world_id"], "join-policy-seed", "offender", {"type": "join", "location": [8, 5]}, expected_revision=1)
        self.store.apply_action(self.world["world_id"], "take-policy-seed", "offender", {"type": "misappropriate_resource", "resource": "stone", "amount": 1}, expected_revision=offender["revision"])
        enacted = self.store.advance_due(now_ms=1_000_000 + 24 * 15_000, max_ticks=24)
        borrower = self.store.apply_action(self.world["world_id"], "join-borrower", "borrower", {"type": "join", "location": [8, 5]}, expected_revision=enacted["revision"])
        checked = self.store.apply_action(self.world["world_id"], "checkout-tools", "borrower", {"type": "checkout_resource", "resource": "tools", "amount": 2, "purpose": "repair measuring equipment"}, expected_revision=borrower["revision"])
        checkout = checked["result"]["checkout"]
        self.assertEqual(self.store.snapshot()["state"]["players"]["borrower"]["inventory"]["tools"], 2)
        returned = self.store.apply_action(self.world["world_id"], "return-checkout-tools", "borrower", {"type": "return_checkout", "checkout_id": checkout["id"], "resource": "tools", "amount": 2}, expected_revision=checked["revision"])
        self.assertEqual(returned["result"]["status"], "returned_on_time")
        state = self.store.snapshot()["state"]
        self.assertEqual(state["players"]["borrower"]["reputation"], 1)
        self.assertGreater(state["npcs"]["dev"]["relationships"]["borrower"]["trust"], 0.5)
        self.assertEqual(state["resources"]["tools"], 12)

    def test_overdue_checkout_changes_future_access_and_return_recovers_it(self):
        offender = self.store.apply_action(self.world["world_id"], "join-overdue-seed", "offender", {"type": "join", "location": [8, 5]}, expected_revision=1)
        self.store.apply_action(self.world["world_id"], "take-overdue-seed", "offender", {"type": "misappropriate_resource", "resource": "stone", "amount": 1}, expected_revision=offender["revision"])
        enacted = self.store.advance_due(now_ms=1_000_000 + 24 * 15_000, max_ticks=24)
        borrower = self.store.apply_action(self.world["world_id"], "join-overdue-borrower", "borrower", {"type": "join", "location": [8, 5]}, expected_revision=enacted["revision"])
        checked = self.store.apply_action(self.world["world_id"], "checkout-overdue-tools", "borrower", {"type": "checkout_resource", "resource": "tools", "amount": 1}, expected_revision=borrower["revision"])
        checkout = checked["result"]["checkout"]
        overdue = self.store.advance_due(now_ms=1_000_000 + 73 * 15_000, max_ticks=49)
        state = overdue["state"]
        self.assertEqual(next(item for item in state["institutions"]["governance"]["checkouts"] if item["id"] == checkout["id"])["status"], "overdue")
        self.assertEqual(state["players"]["borrower"]["reputation"], -2)
        denied = self.store.apply_action(self.world["world_id"], "checkout-while-overdue", "borrower", {"type": "checkout_resource", "resource": "tools", "amount": 1}, expected_revision=overdue["revision"])
        self.assertFalse(denied["result"]["accepted"])
        returned = self.store.apply_action(self.world["world_id"], "return-overdue-tools", "borrower", {"type": "return_checkout", "checkout_id": checkout["id"], "resource": "tools", "amount": 1}, expected_revision=denied["revision"])
        self.assertEqual(returned["result"]["status"], "returned_after_followup")
        reopened = self.store.apply_action(self.world["world_id"], "checkout-after-recovery", "borrower", {"type": "checkout_resource", "resource": "tools", "amount": 1}, expected_revision=returned["revision"])
        self.assertTrue(reopened["result"]["accepted"])

    def test_relationship_history_causes_explained_refusal_and_supervised_trust_recovery_across_restart(self):
        snapshot = self.store.snapshot()
        state = snapshot["state"]
        state["institutions"]["governance"]["resource_access"]["mode"] = "recorded_checkout"
        state["npcs"]["dev"]["relationships"]["borrower"] = {
            "trust": 0.25, "history": [{"tick": 0, "cause": "prior-custody-failure", "change": -0.25}],
        }
        with self.store.transaction() as connection:
            connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(state), snapshot["world_id"]))
        joined = self.store.apply_action(snapshot["world_id"], "relationship-join", "borrower", {"type": "join", "location": [8, 5]})
        denied = self.store.apply_action(snapshot["world_id"], "ordinary-refused", "borrower", {"type": "checkout_resource", "resource": "tools", "amount": 1}, expected_revision=joined["revision"])
        self.assertFalse(denied["result"]["accepted"])
        self.assertEqual("request_supervised_checkout", denied["result"]["recovery_option"])
        self.assertEqual("recoverable", denied["result"]["refusal"]["status"])
        self.assertTrue(any(item["effect"].startswith("cooperation-refused:") for item in self.store.snapshot()["state"]["consequences"]))

        self.store.close()
        self.store = PersistentWorldStore(self.path)
        supervised = self.store.apply_action(snapshot["world_id"], "supervised-issued", "borrower", {"type": "request_supervised_checkout", "resource": "tools", "amount": 1}, now_ms=1_000_010)
        self.assertTrue(supervised["result"]["accepted"])
        self.assertTrue(supervised["result"]["checkout"]["supervised"])
        returned = self.store.apply_action(snapshot["world_id"], "supervised-returned", "borrower", {"type": "return_checkout", "checkout_id": supervised["result"]["checkout"]["id"], "resource": "tools", "amount": 1}, expected_revision=supervised["revision"])
        self.assertEqual("returned_on_time", returned["result"]["status"])
        recovered = self.store.snapshot()["state"]
        self.assertGreaterEqual(recovered["npcs"]["dev"]["relationships"]["borrower"]["trust"], 0.35)
        self.assertEqual("resolved", recovered["institutions"]["governance"]["access_refusals"][0]["status"])
        self.assertTrue(any(item["effect"].startswith("trust-recovered:borrower:") for item in recovered["consequences"]))
        ordinary = self.store.apply_action(snapshot["world_id"], "ordinary-restored", "borrower", {"type": "checkout_resource", "resource": "tools", "amount": 2}, expected_revision=returned["revision"])
        self.assertTrue(ordinary["result"]["accepted"])

        repositioned = self.store.apply_action(snapshot["world_id"], "ask-dev-position", "borrower", {"type": "join", "location": [11, 5]}, expected_revision=ordinary["revision"])
        revision = repositioned["revision"]
        dev_reply = None
        for attempt in range(1, 21):
            spoken = self.store.apply_action(
                snapshot["world_id"], f"ask-dev-trust-{attempt}", "borrower",
                {"type": "speak", "content": f"Can I borrow a tool through checkout? Attempt {attempt}", "target_id": "dev"},
                expected_revision=revision,
            )
            revision = spoken["revision"]
            dev_reply = next((reply for reply in spoken["result"]["replies"] if reply["speaker_id"] == "dev"), None)
            if dev_reply:
                break
        self.assertIsNotNone(dev_reply, "deterministic directed-response sequence should eventually allow Dev to answer")
        self.assertIn("trust 0.37", dev_reply["content"])

    def test_frontier_migration_is_bounded_and_private_observations_hide_substrate(self):
        joined = self.store.apply_action(self.world["world_id"], "frontier-alice-join", "alice", {"type": "join", "location": [8, 9]}, expected_revision=1)

        observed = self.store.observed_snapshot(self.world["world_id"], "alice")

        self.assertEqual(31, observed["state"]["schema"])
        self.assertEqual(64, observed["state"]["frontier"]["size"])
        self.assertTrue(observed["state"]["observed_tiles"])
        self.assertTrue(all("substrate" not in tile for tile in observed["state"]["observed_tiles"].values()))
        self.assertNotIn("discoveries", observed["state"])
        self.assertGreater(joined["revision"], 1)

    def test_routed_travel_persists_and_discovers_land_only_for_the_traveler(self):
        alice = self.store.apply_action(self.world["world_id"], "route-alice-join", "alice", {"type": "join", "location": [8, 9]}, expected_revision=1)
        bob = self.store.apply_action(self.world["world_id"], "route-bob-join", "bob", {"type": "join", "location": [8, 9]}, expected_revision=alice["revision"])
        routed = self.store.apply_action(self.world["world_id"], "route-alice-outward", "alice", {"type": "travel_route", "destination": [12, 12]}, expected_revision=bob["revision"], now_ms=1_000_010)

        self.assertTrue(routed["result"]["accepted"])
        self.assertGreater(len(routed["result"]["route"]), 1)
        advanced = self.store.advance_due(now_ms=1_000_000 + 12 * 15_000, max_ticks=12)
        self.assertEqual([12, 12], advanced["state"]["players"]["alice"]["location"])

        alice_view = self.store.observed_snapshot(self.world["world_id"], "alice")
        bob_view = self.store.observed_snapshot(self.world["world_id"], "bob")
        self.assertGreater(len(alice_view["state"]["observed_tiles"]), len(bob_view["state"]["observed_tiles"]))
        self.assertNotIn("12,16", bob_view["state"]["observed_tiles"])

        self.store.close()
        self.store = PersistentWorldStore(self.path)
        reopened = self.store.observed_snapshot(self.world["world_id"], "alice")
        self.assertEqual([12, 12], reopened["state"]["players"]["alice"]["location"])
        self.assertIn("12,16", reopened["state"]["observed_tiles"])

    def test_travel_action_id_is_idempotent_and_unknown_destination_is_rejected(self):
        joined = self.store.apply_action(self.world["world_id"], "idempotent-route-join", "traveler", {"type": "join", "location": [8, 9]}, expected_revision=1)
        first = self.store.apply_action(self.world["world_id"], "idempotent-route-command", "traveler", {"type": "travel_route", "destination": [12, 12]}, expected_revision=joined["revision"])
        duplicate = self.store.apply_action(self.world["world_id"], "idempotent-route-command", "traveler", {"type": "travel_route", "destination": [12, 12]}, expected_revision=joined["revision"])

        self.assertEqual(first, duplicate)
        rejected = self.store.apply_action(self.world["world_id"], "unknown-route-command", "traveler", {"type": "travel_route", "destination": [40, 40]}, expected_revision=first["revision"])
        self.assertFalse(rejected["result"]["accepted"])
        self.assertEqual("destination_unknown", rejected["result"]["reason"])

    def test_approach_site_chooses_the_lowest_cost_reachable_adjacent_tile(self):
        joined = self.store.apply_action(self.world["world_id"], "approach-join", "traveler", {"type": "join", "location": [4, 5]}, expected_revision=1)
        snapshot = self.store.snapshot()
        state = snapshot["state"]
        state["resource_sites"]["well-site"]["location"] = [7, 5]
        state["discoveries"]["traveler"] = {
            f"{x},{y}": {"observed_tick": 0}
            for x in range(3, 11)
            for y in range(2, 9)
        }
        state["terrain_modifications"].update({
            "7,5": {"passable": False},
            "5,5": {"passable": False},
            "6,4": {"passable": False},
            "6,6": {"passable": False},
        })
        with self.store.transaction() as connection:
            connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(state), snapshot["world_id"]))

        approached = self.store.apply_action(
            self.world["world_id"], "approach-well", "traveler",
            {"type": "approach_site", "site_id": "well-site"},
            expected_revision=joined["revision"],
        )

        self.assertTrue(approached["result"]["accepted"])
        self.assertNotEqual([6, 5], approached["result"]["destination"])
        self.assertIn(approached["result"]["destination"], [[8, 5], [7, 4], [7, 6]])
        self.assertGreater(len(approached["result"]["route"]), 1)

    def test_approach_route_preserves_remote_region_until_site_interaction(self):
        joined = self.store.apply_action(self.world["world_id"], "remote-join", "traveler", {"type": "join", "location": [8, 9]}, expected_revision=1)
        checkout = self.store.apply_action(self.world["world_id"], "remote-axe", "traveler", {"type": "interact_site", "site_id": "tool-counter", "operation": "checkout", "item": "axe"}, expected_revision=joined["revision"])
        boundary = self.store.apply_action(self.world["world_id"], "remote-boundary", "traveler", {"type": "join", "location": [0, 8]}, expected_revision=checkout["revision"])
        explored = self.store.apply_action(self.world["world_id"], "remote-explore", "traveler", {"type": "explore_region", "region": "north_woods"}, expected_revision=boundary["revision"])
        approached = self.store.apply_action(self.world["world_id"], "remote-approach", "traveler", {"type": "approach_site", "site_id": "pine-stand"}, expected_revision=explored["revision"], now_ms=1_000_001)

        self.assertTrue(approached["result"]["accepted"])
        advanced = self.store.advance_due(now_ms=1_000_000 + 15_000, max_ticks=1)
        self.assertEqual("north_woods", advanced["state"]["players"]["traveler"]["current_region"])

        chopped = self.store.apply_action(self.world["world_id"], "remote-chop", "traveler", {"type": "interact_site", "site_id": "pine-stand", "operation": "chop"})
        self.assertTrue(chopped["result"]["accepted"])
        self.assertEqual("proposal_recorded", chopped["result"]["status"])

    def test_frontier_excavation_uses_verified_shared_action_and_preserves_actor_custody(self):
        joined = self.store.apply_action(self.world["world_id"], "excavator-join", "excavator", {"type": "join", "location": [9, 9]}, expected_revision=1)
        inspector_joined = self.store.apply_action(self.world["world_id"], "inspector-join", "inspector", {"type": "join", "location": [9, 10]}, expected_revision=joined["revision"])
        snapshot = self.store.snapshot()
        state = snapshot["state"]
        state["players"]["excavator"]["equipment"]["shovel"] = {"condition": 0.9, "reserved_by": None, "provenance": "test-checkout"}
        state["players"]["excavator"]["inventory"]["shovel"] = 1
        state["players"]["excavator"]["competency_records"]["excavation"] = {"demonstrated": 0.2, "provenance": ["test-practice"]}
        state["players"]["inspector"]["competency_records"]["measurement"] = {"demonstrated": 0.2, "provenance": ["test-verification"]}
        with self.store.transaction() as connection:
            connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(state), snapshot["world_id"]))

        surveyed = self.store.apply_action(self.world["world_id"], "survey-excavation-tile", "excavator", {"type": "survey_frontier", "location": [9, 9]}, expected_revision=inspector_joined["revision"])
        proposed = self.store.apply_action(self.world["world_id"], "propose-excavation-tile", "excavator", {"type": "propose_frontier_extraction", "location": [9, 9], "mode": "excavate"}, expected_revision=surveyed["revision"])
        action_id = proposed["result"]["canonical_action_id"]
        self.assertTrue(proposed["result"]["accepted"])
        for index, operation in enumerate(("accept", "reserve"), 1):
            result = self.store.apply_action(self.world["world_id"], f"excavation-{operation}", "excavator", {"type": "shared_action", "operation": operation, "shared_action_id": action_id}, now_ms=1_000_010 + index)
            self.assertTrue(result["result"]["accepted"])
        executed = self.store.apply_action(self.world["world_id"], "excavation-execute", "excavator", {"type": "shared_action", "operation": "execute", "shared_action_id": action_id, "samples": [{"stock_before": proposed["result"]["stock"], "observed_yield": 1}]}, now_ms=1_000_020)
        self.assertTrue(executed["result"]["accepted"])
        self.store.advance_due(now_ms=1_000_000 + 8 * 15_000, max_ticks=8)
        verified = self.store.apply_action(self.world["world_id"], "excavation-verify", "inspector", {"type": "shared_action", "operation": "verify", "shared_action_id": action_id})
        self.assertTrue(verified["result"]["accepted"], verified["result"])
        commissioned = self.store.apply_action(self.world["world_id"], "excavation-commission", "inspector", {"type": "shared_action", "operation": "commission", "shared_action_id": action_id}, expected_revision=verified["revision"])
        self.assertTrue(commissioned["result"]["accepted"], commissioned["result"])

        final = commissioned["result"]["record"]
        material = final["definition"]["output_item"]
        state = self.store.snapshot()["state"]
        self.assertEqual("commissioned", final["state"])
        self.assertEqual(1, state["players"]["excavator"]["inventory"][material])
        self.assertEqual(40, state["terrain_modifications"]["9,9"]["excavation_depth_cm"])
        self.assertFalse(state["shared_actions"]["valuation_claims"][-1]["spendable"])

    def test_deposit_and_plot_preparation_require_physical_custody_and_survey(self):
        joined = self.store.apply_action(self.world["world_id"], "builder-join", "builder", {"type": "join", "location": [10, 10]}, expected_revision=1)
        denied = self.store.apply_action(self.world["world_id"], "prepare-unsurveyed", "builder", {"type": "prepare_frontier_plot", "location": [10, 10]}, expected_revision=joined["revision"])
        self.assertFalse(denied["result"]["accepted"])

        snapshot = self.store.snapshot()
        state = snapshot["state"]
        state["players"]["builder"]["inventory"].update({"shovel": 1, "stone": 2})
        state["players"]["builder"]["equipment"]["shovel"] = {"condition": 0.9, "reserved_by": None, "provenance": "test-checkout"}
        with self.store.transaction() as connection:
            connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(state), snapshot["world_id"]))
        surveyed = self.store.apply_action(self.world["world_id"], "survey-build-tile", "builder", {"type": "survey_frontier", "location": [10, 10]})
        prepared = self.store.apply_action(self.world["world_id"], "prepare-surveyed", "builder", {"type": "prepare_frontier_plot", "location": [10, 10]}, expected_revision=surveyed["revision"])
        self.assertTrue(prepared["result"]["accepted"])
        self.assertTrue(self.store.snapshot()["state"]["terrain_modifications"]["10,10"]["prepared_foundation"])

        moved = self.store.apply_action(self.world["world_id"], "builder-at-warehouse", "builder", {"type": "join", "location": [5, 11]}, expected_revision=prepared["revision"])
        inspector = self.store.apply_action(self.world["world_id"], "receiver-at-warehouse", "receiver", {"type": "join", "location": [5, 10]}, expected_revision=moved["revision"])
        snapshot = self.store.snapshot()
        state = snapshot["state"]
        state["players"]["receiver"]["competency_records"]["measurement"] = {"demonstrated": 0.2, "provenance": ["verified-receiving-practice"]}
        with self.store.transaction() as connection:
            connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(state), snapshot["world_id"]))
        proposed = self.store.apply_action(self.world["world_id"], "deposit-builder-stone", "builder", {"type": "deposit_material", "resource": "stone", "amount": 1}, expected_revision=inspector["revision"])
        action_id = proposed["result"]["canonical_action_id"]
        self.assertTrue(proposed["result"]["accepted"])
        self.assertEqual(1, self.store.snapshot()["state"]["players"]["builder"]["inventory"]["stone"])
        for operation in ("accept", "reserve"):
            transitioned = self.store.apply_action(self.world["world_id"], f"deposit-{operation}", "builder", {"type": "shared_action", "operation": operation, "shared_action_id": action_id})
            self.assertTrue(transitioned["result"]["accepted"])
        self.store.apply_action(self.world["world_id"], "deposit-execute", "builder", {"type": "shared_action", "operation": "execute", "shared_action_id": action_id, "samples": [{"custody_before": 1, "observed_amount": 1}]})
        self.store.advance_due(now_ms=1_000_000 + 5 * 15_000, max_ticks=5)
        verified = self.store.apply_action(self.world["world_id"], "deposit-verify", "receiver", {"type": "shared_action", "operation": "verify", "shared_action_id": action_id})
        self.assertTrue(verified["result"]["accepted"], verified["result"])
        deposited = self.store.apply_action(self.world["world_id"], "deposit-commission", "receiver", {"type": "shared_action", "operation": "commission", "shared_action_id": action_id}, expected_revision=verified["revision"])
        self.assertEqual("commissioned", deposited["result"]["record"]["state"])
        state = self.store.snapshot()["state"]
        self.assertEqual(0, state["players"]["builder"]["inventory"]["stone"])
        self.assertEqual(25, state["resources"]["stone"])
        self.assertFalse(state["shared_actions"]["valuation_claims"][-1]["spendable"])

    def test_creator_privileges_are_redacted_and_operator_amendments_are_separately_audited(self):
        joined = self.store.apply_action(self.world["world_id"], "sirix-embodied-join", "owner-uuid", {"type": "join", "location": [8, 9]}, expected_revision=1)
        snapshot = self.store.snapshot()
        state = snapshot["state"]
        state["players"]["owner-uuid"].update({"username": "sirix_1", "is_owner": True, "permission_level": "sirix_1", "abilities": ["all"], "stats": {"authority": 999}})
        with self.store.transaction() as connection:
            connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(state), snapshot["world_id"]))

        ordinary_view = self.store.observed_snapshot(self.world["world_id"], "observer")
        creator = ordinary_view["state"]["players"]["owner-uuid"]
        self.assertNotIn("is_owner", creator)
        self.assertNotIn("permission_level", creator)
        self.assertNotIn("abilities", creator)
        self.assertEqual({"authority": None}, creator["stats"])

        with self.assertRaises(PermissionError):
            self.store.apply_action(self.world["world_id"], "forged-operator-action", "sirix_1", {"type": "operator_amendment", "operation": "pause_world", "confirmed": True})
        amended = self.store.apply_operator_amendment(self.world["world_id"], "operator-pause-world", "owner-uuid", {"operation": "pause_world", "reason": "safe Alpha 33 maintenance", "confirmation": "CONFIRM WORLD AMENDMENT"}, expected_revision=joined["revision"])
        self.assertTrue(amended["result"]["accepted"])
        state = self.store.snapshot()["state"]
        self.assertTrue(state["clock"]["paused"])
        self.assertEqual("owner-uuid", state["operator_audit"][-1]["principal"])
        self.assertEqual("operator_amendment", state["operator_audit"][-1]["plane"])


if __name__ == "__main__":
    unittest.main()
