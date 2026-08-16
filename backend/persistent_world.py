"""Durable authoritative world clock and multiplayer state service for EoV."""

from __future__ import annotations

import json
import copy
import math
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from action_engine import COMMUNAL_MEAL_PREPARATION, MEASUREMENT_TOOL_CALIBRATION, MECHANICAL_PUMP_REPAIR, site_resource_extraction
from causal_ledger import CausalEvent, CausalLedger
from terrain_engine import FrontierGrid


SCHEMA_VERSION = 31
DEFAULT_WORLD_ID = "founders-settlement"


def founding_table_seed(now_ms: int) -> Dict[str, Any]:
    residents = [
        ("ada", "Ada", "engineer", "independent", [9, 7]),
        ("orin", "Orin", "builder", "independent", [6, 9]),
        ("mira", "Mira", "researcher", "independent", [11, 11]),
        ("lena", "Lena", "cook", "hearth-house", [6, 5]),
        ("tomas", "Tomas", "farmer", "hearth-house", [5, 6]),
        ("imani", "Imani", "medic", "hearth-house", [7, 5]),
        ("dev", "Dev", "logistics", "river-house", [12, 5]),
        ("sora", "Sora", "administrator", "river-house", [13, 6]),
        ("cal", "Cal", "carpenter", "river-house", [12, 7]),
        ("nyra", "Nyra", "potter", "independent", [4, 10]),
        ("emil", "Emil", "water-tester", "independent", [14, 10]),
        ("rae", "Rae", "traveler", "unattached", [9, 13]),
    ]
    npcs = {}
    for index, (npc_id, name, role, household, location) in enumerate(residents):
        npcs[npc_id] = {
            "id": npc_id, "name": name, "role": role, "household": household,
            "location": location, "current_region": "settlement", "needs": {"nutrition": 78 - index % 8, "hydration": 82 - index % 7, "rest": 76 + index % 9, "belonging": 65 + index % 12},
            "inventory": {}, "equipment": {}, "competencies": {role: 0.65, "observe": 0.5, "logistics": 0.35}, "competency_records": {}, "energy": 100.0,
            "schedule": {"shift_start": 7 + index % 3, "shift_end": 16 + index % 4},
            "intention": "attend the Founding Table", "reason": "Initial provisions will spoil without a shared plan.",
            "memories": [], "autonomous": True,
        }
    # Initial competence is imported only where the founding record declares
    # demonstrated pre-settlement practice. A role/title alone grants nothing.
    for npc_id, demonstrated, evidence_id in (
        ("ada", 0.35, "founding-evidence:ada:repeated-calibration-practice"),
        ("mira", 0.40, "founding-evidence:mira:independent-measurement-reproduction"),
        ("emil", 0.25, "founding-evidence:emil:water-instrument-practice"),
    ):
        npcs[npc_id]["competency_records"]["measurement"] = {
            "demonstrated": demonstrated,
            "provenance": [evidence_id],
        }
    npcs["lena"]["competency_records"]["cooking"] = {"demonstrated": 0.45, "provenance": ["founding-evidence:lena:repeated-safe-meal-practice"]}
    npcs["imani"]["competency_records"]["food_safety"] = {"demonstrated": 0.40, "provenance": ["founding-evidence:imani:reproduced-food-safety-inspection"]}
    npcs["ada"]["competency_records"]["mechanical_engineering"] = {"demonstrated": 0.35, "provenance": ["founding-evidence:ada:documented-pump-repair-practice"]}
    npcs["cal"]["equipment"]["axe"] = {"condition": 0.9, "reserved_by": None, "provenance": "founding-tool-allocation:axe-1"}
    npcs["orin"]["equipment"]["pick"] = {"condition": 0.9, "reserved_by": None, "provenance": "founding-tool-allocation:pick-1"}
    npcs["nyra"]["equipment"]["farm_tools"] = {"condition": 0.9, "reserved_by": None, "provenance": "founding-tool-allocation:farm-tools-1"}
    return {
        "schema": SCHEMA_VERSION,
        "name": "Founders' Settlement",
        "frontier": {"seed": 1701, "size": 64},
        "terrain_modifications": {},
        "discoveries": {},
        "clock": {"tick": 0, "minute": 8 * 60, "tick_seconds": 15, "paused": False},
        "places": {
            "water_source": {"location": [3, 8], "status": "unverified", "dependability": 0.45},
            "sanitation": {"location": [3, 11], "status": "planned"},
            "hearth_house": {"location": [6, 5], "private_rooms": 3, "shared_space": 1},
            "river_house": {"location": [12, 5], "private_rooms": 3, "shared_space": 1},
            "communal_kitchen": {"location": [8, 8], "status": "proposed"},
            "dry_storage": {"location": [5, 11], "status": "temporary"},
            "cold_storage": {"location": [5, 12], "status": "absent"},
            "measurement_lab": {"location": [8, 7], "status": "available"},
            "clinic": {"location": [7, 5], "status": "temporary"},
            "warehouse": {"location": [5, 11], "status": "temporary"},
            "meeting_hall": {"location": [8, 5], "status": "available"},
            "unclaimed_land": {"bounds": [0, 0, 18, 18], "homestead_claims": []},
        },
        "resources": {"raw_food": 84, "safe_meals": 0, "water": 60, "tested_water": 0, "fuel": 32, "timber": 30, "stone": 24, "containers": 18, "tools": 12, "reference_strip": 4},
        "resource_sites": {
            "tool-counter": {"id": "tool-counter", "type": "store", "region": "settlement", "location": [7, 9], "name": "Dev's tool counter", "clerk": "dev", "stock": {"axe": 3, "pick": 2, "shovel": 2, "bucket": 4, "wrench": 2, "farm_tools": 2, "seed": 16, "feed": 12}, "history": []},
            "well-site": {"id": "well-site", "type": "well", "region": "settlement", "location": [11, 13], "name": "Shallow well site", "progress": 0, "stock": 0, "capacity": 24, "history": []},
            "farm-plot": {"id": "farm-plot", "type": "farm", "region": "settlement", "location": [3, 13], "name": "Communal farm plot", "stage": "untilled", "ready_tick": None, "stock": 0, "capacity": 12, "history": []},
            "cattle-yard": {"id": "cattle-yard", "type": "cattle", "region": "settlement", "location": [14, 13], "name": "Settlement cattle", "wellbeing": 72.0, "fed_until_tick": 0, "stock": 2.0, "capacity": 4, "history": []},
            "old-oak": {"id": "old-oak", "type": "tree", "region": "north_woods", "location": [8, 9], "name": "Old oak", "stock": 10, "capacity": 10, "history": []},
            "pine-stand": {"id": "pine-stand", "type": "tree", "region": "north_woods", "location": [7, 9], "name": "Pine stand", "stock": 8, "capacity": 8, "history": []},
            "ridge-seam": {"id": "ridge-seam", "type": "mineral", "region": "east_ridge", "location": [10, 9], "name": "Exposed mineral seam", "stock": 12, "capacity": 12, "history": []},
            "marsh-reeds": {"id": "marsh-reeds", "type": "reeds", "region": "south_marsh", "location": [8, 10], "name": "Marsh reed bed", "stock": 14, "capacity": 14, "history": []},
        },
        "environment": {
            "stocks": {"timber": 80, "stone": 60, "raw_food": 100, "fuel": 50, "containers": 20},
            "extraction_history": [], "stewardship_orders": [],
            "regions": {
                "settlement": {"name": "Founders' Settlement", "adjacent": ["north_woods", "east_ridge", "south_marsh"], "stocks": {}},
                "north_woods": {"name": "North Woods", "adjacent": ["settlement"], "stocks": {"timber": 120, "raw_food": 45, "fuel": 30}},
                "east_ridge": {"name": "East Ridge", "adjacent": ["settlement"], "stocks": {"stone": 110, "fuel": 18}},
                "south_marsh": {"name": "South Marsh", "adjacent": ["settlement"], "stocks": {"raw_food": 55, "containers": 25, "fuel": 22}},
            },
        },
        "food": {"spoilage_clock": 96, "safety": 0.55, "storage_quality": 0.35, "meal_history": []},
        "water_system": {"batches": [], "consumption_history": [], "shortages": [], "work_orders": []},
        "survival": {"meal_history": [], "rest_history": [], "shortages": []},
        "cooking": {
            "work_orders": [], "meal_batches": [], "spoilage_history": [], "waste_portions": 0,
            "preservation_program": {"status": "inactive", "method": "drying", "waste_trigger": 3, "history": [], "required_inputs": {"raw_food": 2, "fuel": 1, "containers": 1}},
        },
        "npcs": npcs,
        "players": {},
        "event": {
            "id": "founding-table", "title": "The Founding Table", "status": "convening", "phase": 0,
            "priorities": ["survey_water", "test_water", "inventory_provisions", "choose_facility", "publish_orders", "negotiate", "construct", "prepare_meal", "inspect_meal", "settlement_meeting"],
            "competing_orders": [], "selected_order": None,
        },
        "evidence": [], "failures": [],
        "economy": {
            "mode": "provisional", "accounts": {"treasury": 0}, "claims": [], "journal": [], "work_contracts": [],
            "prices": {"meal": 3.0, "tested_water": 2.0, "labor_hour": 8.0, "timber": 3.0, "stone": 4.0, "raw_food": 2.0, "fuel": 3.0, "containers": 5.0},
            "market_signals": {}, "market_history": [],
        },
        "culture": {"place_names": {}, "traditions": [], "recipes": [], "memorials": [], "boundary_disputes": []},
        "communications": {"messages": [], "public_discourse": {"claims": [], "escalations": []}},
        "research": {"designs": [], "reviews": [], "reproductions": []},
        "education": {"teaching_orders": [], "practice_orders": []},
        "technology": {"tool_catalog": {}, "validated_designs": []},
        "shared_actions": {
            "records": {}, "ledger": [], "demands": [],
            "tools": {"marked_measure": {"condition": 0.6, "reserved_by": None}, "cooking_pot": {"condition": 0.9, "reserved_by": None}, "food_thermometer": {"condition": 0.9, "reserved_by": None}, "maintenance_wrench": {"condition": 0.9, "reserved_by": None}},
            "stations": {"measurement_bench": {"place": "measurement_lab", "reserved_by": None}, "communal_hearth": {"place": "communal_kitchen", "reserved_by": None}, "instruction_table": {"place": "meeting_hall", "reserved_by": None}},
            "reservations": {}, "actor_commitments": {}, "unverified_outputs": {}, "commissioned_outputs": {},
            "valuation_accounts_milli": {"treasury": 0}, "valuation_claims": [],
            "canonical_cooking": True,
        },
        "institutions": {
            "council": {"knowledge": [], "agenda": [], "endorsements": {}, "public_pressure": {}, "current_initiative": None, "completed_initiatives": []},
            "justice": {"reports": [], "cases": [], "bounties": []},
            "governance": {"resource_access": {"mode": "open_stores", "proposal": None, "history": []}, "checkouts": [], "access_refusals": [], "owner_directives": [], "maintenance_orders": []},
        },
        "consequences": [],
        "causality": {"perceptions": [], "pending_reactions": [], "completed_reactions": []},
        "created_at_ms": now_ms,
    }


def migrate_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """Upgrade durable worlds without discarding the history that created them."""
    state.setdefault("institutions", {}).setdefault("council", {})
    council = state["institutions"]["council"]
    council.setdefault("knowledge", [])
    council.setdefault("agenda", [])
    council.setdefault("endorsements", {})
    council.setdefault("public_pressure", {})
    council.setdefault("current_initiative", None)
    council.setdefault("completed_initiatives", [])
    for initiative in ([council["current_initiative"]] if council["current_initiative"] else []) + council["completed_initiatives"]:
        initiative.setdefault("causal_sources", [])
        initiative.setdefault("required_evidence", [])
        initiative.setdefault("evidence_tags", [])
    state["institutions"].setdefault("justice", {"reports": [], "cases": [], "bounties": []})
    justice = state["institutions"]["justice"]
    justice.setdefault("reports", [])
    justice.setdefault("cases", [])
    justice.setdefault("bounties", [])
    for bounty in justice["bounties"]:
        bounty.setdefault("assignee", None)
        bounty.setdefault("contact", None)
    state["institutions"].setdefault("governance", {"resource_access": {"mode": "open_stores", "proposal": None, "history": []}, "checkouts": []})
    governance = state["institutions"]["governance"]
    governance.setdefault("resource_access", {"mode": "open_stores", "proposal": None, "history": []})
    governance["resource_access"].setdefault("mode", "open_stores")
    governance["resource_access"].setdefault("proposal", None)
    governance["resource_access"].setdefault("history", [])
    governance.setdefault("checkouts", [])
    governance.setdefault("access_refusals", [])
    governance.setdefault("owner_directives", [])
    governance.setdefault("maintenance_orders", [])
    for order in governance["maintenance_orders"]:
        order.setdefault("assigned_to", None)
        order.setdefault("assigned_tick", None)
        order.setdefault("blockers", [])
        order.setdefault("procurement_history", [])
        order.setdefault("depletion_notices", [])
    for player in state.get("players", {}).values():
        player.setdefault("inventory", {})
        player.setdefault("equipment", {})
        player.setdefault("reputation", 0)
        player.setdefault("known_cases", [])
        player.setdefault("route", None)
    for player_id, player in state.get("players", {}).items():
        player.setdefault("id", player_id)
    for npc in state.get("npcs", {}).values():
        npc.setdefault("relationships", {})
        npc.setdefault("current_region", "settlement")
        npc.setdefault("energy", 100.0)
        npc.setdefault("competency_records", {})
        npc.setdefault("equipment", {})
        npc.setdefault("route", None)
    state.setdefault("frontier", {"seed": 1701, "size": 64})
    state["frontier"].setdefault("seed", 1701)
    state["frontier"]["size"] = 64
    state.setdefault("terrain_modifications", {})
    discoveries = state.setdefault("discoveries", {})
    for entity_id, entity in {**state.get("npcs", {}), **state.get("players", {})}.items():
        if entity_id not in discoveries:
            discoveries[entity_id] = {}
            _reveal_frontier(state, entity_id, entity.get("location", [8, 9]))
    # Preserve the declared founding-practice provenance when upgrading worlds
    # created before competency records existed. This is not inferred from role.
    founding_measurement_practice = {
        "ada": (0.35, "founding-evidence:ada:repeated-calibration-practice"),
        "mira": (0.40, "founding-evidence:mira:independent-measurement-reproduction"),
        "emil": (0.25, "founding-evidence:emil:water-instrument-practice"),
    }
    for npc_id, (demonstrated, evidence_id) in founding_measurement_practice.items():
        npc = state.get("npcs", {}).get(npc_id)
        if npc:
            npc["competency_records"].setdefault("measurement", {"demonstrated": demonstrated, "provenance": [evidence_id]})
    if state.get("npcs", {}).get("lena"):
        state["npcs"]["lena"]["competency_records"].setdefault("cooking", {"demonstrated": 0.45, "provenance": ["founding-evidence:lena:repeated-safe-meal-practice"]})
    if state.get("npcs", {}).get("imani"):
        state["npcs"]["imani"]["competency_records"].setdefault("food_safety", {"demonstrated": 0.40, "provenance": ["founding-evidence:imani:reproduced-food-safety-inspection"]})
    if state.get("npcs", {}).get("ada"):
        state["npcs"]["ada"]["competency_records"].setdefault("mechanical_engineering", {"demonstrated": 0.35, "provenance": ["founding-evidence:ada:documented-pump-repair-practice"]})
    state.setdefault("shared_actions", {}).setdefault("tools", {}).setdefault("maintenance_wrench", {"condition": 0.9, "reserved_by": None})
    shared = state.setdefault("shared_actions", {})
    commitments = shared.setdefault("actor_commitments", {})
    active_states = {"accepted", "reserved", "in_progress", "submitted", "verified", "awaiting_acceptances"}
    for record in sorted(shared.get("records", {}).values(), key=lambda item: item.get("id", "")):
        if record.get("state") not in active_states:
            continue
        participant_ids = [record.get("actor_id")]
        if record.get("definition", {}).get("execution_model") == "instruction_session":
            participant_ids.append(record.get("target_id"))
        participant_ids.append(record.get("supervisor_id"))
        for participant_id in filter(None, participant_ids):
            commitments.setdefault(participant_id, {"action_id": record["id"], "since_tick": record.get("proposed_tick", state.get("clock", {}).get("tick", 0)), "role": "participant"})
    state.setdefault("consequences", [])
    state.setdefault("evidence", [])
    for record in state["evidence"]:
        record.setdefault("causal_sources", [])
        record.setdefault("evidence_tags", [])
    communications = state.setdefault("communications", {})
    communications.setdefault("messages", [])
    discourse = communications.setdefault("public_discourse", {})
    discourse.setdefault("claims", [])
    discourse.setdefault("escalations", [])
    water_system = state.setdefault("water_system", {})
    water_system.setdefault("batches", [])
    water_system.setdefault("consumption_history", [])
    water_system.setdefault("shortages", [])
    water_system.setdefault("work_orders", [])
    survival = state.setdefault("survival", {})
    survival.setdefault("meal_history", [])
    survival.setdefault("rest_history", [])
    survival.setdefault("shortages", [])
    cooking = state.setdefault("cooking", {})
    cooking.setdefault("work_orders", [])
    cooking.setdefault("meal_batches", [])
    cooking.setdefault("spoilage_history", [])
    cooking.setdefault("waste_portions", 0)
    program = cooking.setdefault("preservation_program", {"status": "inactive", "method": "drying", "waste_trigger": 3, "history": [], "required_inputs": {"raw_food": 2, "fuel": 1, "containers": 1}})
    program.setdefault("status", "inactive")
    program.setdefault("method", "drying")
    program.setdefault("waste_trigger", 3)
    program.setdefault("history", [])
    program.setdefault("required_inputs", {"raw_food": 2, "fuel": 1, "containers": 1})
    for batch in cooking["meal_batches"]:
        batch.setdefault("remaining_portions", batch.get("portions", 0) if batch.get("status") == "accepted" else 0)
        batch.setdefault("preservation", "none")
        if batch.get("status") == "accepted":
            batch.setdefault("expires_tick", batch.get("inspected_tick", batch.get("prepared_tick", 0)) + 36)
    research = state.setdefault("research", {})
    research.setdefault("designs", [])
    research.setdefault("reviews", [])
    research.setdefault("reproductions", [])
    education = state.setdefault("education", {})
    education.setdefault("teaching_orders", [])
    education.setdefault("practice_orders", [])
    technology = state.setdefault("technology", {})
    technology.setdefault("tool_catalog", {})
    technology.setdefault("validated_designs", [])
    shared = state.setdefault("shared_actions", {})
    shared.setdefault("records", {})
    for record in shared["records"].values():
        record.setdefault("autonomous_origin", False)
    shared.setdefault("ledger", [])
    shared.setdefault("demands", [])
    shared.setdefault("tools", {"marked_measure": {"condition": 0.6, "reserved_by": None}})
    shared["tools"].setdefault("marked_measure", {"condition": 0.6, "reserved_by": None})
    shared["tools"].setdefault("cooking_pot", {"condition": 0.9, "reserved_by": None})
    shared["tools"].setdefault("food_thermometer", {"condition": 0.9, "reserved_by": None})
    shared.setdefault("stations", {"measurement_bench": {"place": "measurement_lab", "reserved_by": None}})
    shared["stations"].setdefault("measurement_bench", {"place": "measurement_lab", "reserved_by": None})
    shared["stations"].setdefault("communal_hearth", {"place": "communal_kitchen", "reserved_by": None})
    shared["stations"].setdefault("instruction_table", {"place": "meeting_hall", "reserved_by": None})
    shared.setdefault("reservations", {})
    shared.setdefault("unverified_outputs", {})
    shared.setdefault("commissioned_outputs", {})
    shared.setdefault("valuation_accounts_milli", {"treasury": 0})
    shared["valuation_accounts_milli"].setdefault("treasury", 0)
    shared.setdefault("valuation_claims", [])
    shared.setdefault("canonical_cooking", True)
    state.setdefault("resources", {}).setdefault("reference_strip", 4)
    seeded_sites = founding_table_seed(state.get("created_at_ms", 0))["resource_sites"]
    state.setdefault("resource_sites", {})
    for site_id, seed in seeded_sites.items():
        state["resource_sites"].setdefault(site_id, seed)
        state["resource_sites"][site_id].setdefault("history", [])
        pump = state["resource_sites"][site_id].get("installed_pump")
        if pump:
            pump.setdefault("condition", 1.0)
            pump.setdefault("cycles", 0)
            pump.setdefault("status", "operational")
            pump.setdefault("maintenance_due", False)
            pump.setdefault("maintenance_history", [])
    causality = state.setdefault("causality", {})
    causality.setdefault("perceptions", [])
    causality.setdefault("pending_reactions", [])
    causality.setdefault("completed_reactions", [])
    state.setdefault("environment", {"stocks": {"timber": 80, "stone": 60, "raw_food": 100, "fuel": 50, "containers": 20}, "extraction_history": []})
    state["environment"].setdefault("stocks", {})
    state["environment"].setdefault("extraction_history", [])
    state["environment"].setdefault("stewardship_orders", [])
    state["environment"].setdefault("regions", founding_table_seed(state.get("created_at_ms", 0))["environment"]["regions"])
    state["environment"].setdefault("regional_capacity", {"timber": 120, "stone": 110, "raw_food": 100, "fuel": 70, "containers": 25})
    economy = state.setdefault("economy", {})
    economy.setdefault("prices", {}).update({key: economy.get("prices", {}).get(key, value) for key, value in {"timber": 3.0, "stone": 4.0, "raw_food": 2.0, "fuel": 3.0, "containers": 5.0}.items()})
    economy.setdefault("market_signals", {})
    economy.setdefault("market_history", [])
    economy.setdefault("work_contracts", [])
    for order in state["environment"].get("stewardship_orders", []):
        if order.get("contract_id") and any(contract["id"] == order["contract_id"] for contract in economy["work_contracts"]):
            continue
        contract_id = f"contract-{len(economy['work_contracts']) + 1}"
        agreed = {order.get("worker", "cal"): 8.0, order.get("inspector", "mira"): 4.0}
        legacy_contract = {
            "id": contract_id, "kind": "public_environmental_work", "source_order_id": order["id"],
            "status": "settled_provisional" if order.get("status") == "completed" else "accepted",
            "created_tick": order.get("created_tick", 0), "accepted_tick": order.get("created_tick", 0),
            "funding_account": "treasury", "unit": "CU-placeholder", "spendable": False,
            "valuation_basis": {"migration": "pre-contract stewardship terms"}, "roles": {},
            "asks": dict(agreed), "counteroffers": dict(agreed), "agreed": dict(agreed),
            "history": [{"tick": order.get("created_tick", 0), "status": "migrated_accepted", "offers": dict(agreed)}], "settlements": [],
        }
        economy["work_contracts"].append(legacy_contract)
        order["contract_id"] = contract_id
    for player in state.get("players", {}).values():
        player.setdefault("current_region", "settlement")
        player.setdefault("discovered_regions", ["settlement"])
        player.setdefault("energy", 100.0)
        player.setdefault("competencies", {"observe": 0.25, "measure": 0.2, "engineering": 0.1})
        player.setdefault("competency_records", {})
    state["schema"] = SCHEMA_VERSION
    return state


def _tile_key(position: Iterable[int]) -> str:
    x, y = position
    return f"{int(x)},{int(y)}"


def _reveal_frontier(state: Dict[str, Any], actor_id: str, center: Iterable[int], radius: int = 4) -> None:
    x0, y0 = (int(value) for value in center)
    size = int(state.get("frontier", {}).get("size", 64))
    knowledge = state.setdefault("discoveries", {}).setdefault(actor_id, {})
    for x in range(max(0, x0 - radius), min(size, x0 + radius + 1)):
        for y in range(max(0, y0 - radius), min(size, y0 + radius + 1)):
            if max(abs(x - x0), abs(y - y0)) <= radius:
                knowledge.setdefault(f"{x},{y}", {"level": "surface", "discovered_tick": state.get("clock", {}).get("tick", 0)})


def _serialize_observed_tile(state: Dict[str, Any], key: str, evidence: Dict[str, Any]) -> Dict[str, Any]:
    x, y = (int(value) for value in key.split(",", 1))
    frontier = state["frontier"]
    tile = FrontierGrid(frontier["seed"], frontier["size"]).tile_at(x, y)
    modification = state.get("terrain_modifications", {}).get(key, {})
    observed = {
        "position": [x, y],
        "terrain": modification.get("terrain", tile.terrain),
        "elevation": modification.get("elevation", tile.elevation),
        "passable": modification.get("passable", tile.passable),
        "travel_cost_milli": modification.get("travel_cost_milli", tile.travel_cost_milli),
        "visibility": evidence.get("level", "surface"),
    }
    if tile.surface:
        observed["surface"] = {"kind": tile.surface.kind, "material": tile.surface.material, "stock": modification.get("surface_stock", tile.surface.stock)}
    if modification.get("excavation_depth_cm"):
        observed["excavation_depth_cm"] = modification["excavation_depth_cm"]
    if evidence.get("level") in {"surveyed", "prospected"}:
        observed["survey"] = copy.deepcopy(evidence.get("survey", {}))
    if evidence.get("level") == "prospected":
        observed["substrate"] = [{"material": layer.material, "depth_cm": layer.depth_cm, "stock": layer.stock} for layer in tile.substrate]
    return observed


def actor_world_view(snapshot: Dict[str, Any], actor_id: str) -> Dict[str, Any]:
    """Return public state plus only the requesting actor's private material."""
    view = copy.deepcopy(snapshot)
    state = view["state"]
    knowledge = state.get("discoveries", {}).get(actor_id, {})
    state["observed_tiles"] = {key: _serialize_observed_tile(state, key, evidence) for key, evidence in sorted(knowledge.items())}
    state.pop("discoveries", None)
    state["frontier"].pop("seed", None)
    state["terrain_modifications"] = {key: value for key, value in state.get("terrain_modifications", {}).items() if key in knowledge}
    for npc in state.get("npcs", {}).values():
        npc.pop("relationships", None)
        npc["memories"] = [memory for memory in npc.get("memories", []) if memory.get("kind") in {"completed_work", "founding_table"}]
    for player_id, player in state.get("players", {}).items():
        if player_id != actor_id:
            player.pop("inventory", None)
            player.pop("known_cases", None)
            player.pop("memories", None)
            player.pop("competency_records", None)
    shared = state.get("shared_actions", {})
    viewer = state.get("players", {}).get(actor_id, {})
    visible_action_ids = set()
    for action_id, record in list(shared.get("records", {}).items()):
        action_place = state.get("places", {}).get(record.get("location"), {}).get("location", [-999, -999])
        can_inspect = viewer.get("current_region", "settlement") == "settlement" and _distance(viewer.get("location", [-99, -99]), action_place) <= 1
        visible = record.get("actor_id") == actor_id or record.get("target_id") == actor_id or record.get("state") == "commissioned" or can_inspect
        if visible:
            visible_action_ids.add(action_id)
        else:
            shared["records"][action_id] = {"id": action_id, "action_type": record.get("definition", {}).get("action_type"), "state": record.get("state"), "private": True}
    shared["ledger"] = [event for event in shared.get("ledger", []) if event.get("action_id") in visible_action_ids]
    justice = state.get("institutions", {}).get("justice", {})
    relevant_cases = {case["id"] for case in justice.get("cases", []) if case.get("accused") == actor_id}
    relevant_reports = {report_id for case in justice.get("cases", []) if case["id"] in relevant_cases for report_id in case.get("reports", [])}
    justice["reports"] = [report for report in justice.get("reports", []) if report["id"] in relevant_reports]
    for consequence in state.get("consequences", []):
        consequence.pop("witnesses", None)
    communications = state.get("communications", {})
    communications["messages"] = [
        message for message in communications.get("messages", [])
        if message.get("speaker_id") == actor_id or actor_id in message.get("audible_to", [])
    ]
    return view


def actor_event_view(event: Dict[str, Any], snapshot: Dict[str, Any], actor_id: str) -> Dict[str, Any]:
    """Redact event evidence using the same perspective boundary as snapshots."""
    visible = copy.deepcopy(event)
    payload = visible.get("payload", {})
    if visible.get("type") == "conduct_reported" and payload.get("accused") != actor_id:
        visible["payload"] = {"private": True, "conduct_id": payload.get("conduct_id")}
        return visible

    state = snapshot.get("state", {})
    shared = state.get("shared_actions", {})
    record = payload.get("record") if isinstance(payload, dict) else None
    action_id = None
    if isinstance(record, dict):
        action_id = record.get("id")
    if not action_id and isinstance(payload, dict):
        action_id = payload.get("action_id")
    if not action_id and isinstance(payload, dict) and isinstance(payload.get("event"), dict):
        action_id = payload["event"].get("action_id")
    authoritative = shared.get("records", {}).get(action_id, {}) if action_id else {}
    if action_id:
        viewer = state.get("players", {}).get(actor_id, {})
        action_place = state.get("places", {}).get(authoritative.get("location"), {}).get("location", [-999, -999])
        at_action = viewer.get("current_region", "settlement") == "settlement" and _distance(viewer.get("location", [-99, -99]), action_place) <= 1
        owns_action = authoritative.get("actor_id", record.get("actor_id") if isinstance(record, dict) else None) == actor_id or authoritative.get("target_id") == actor_id
        if not (owns_action or authoritative.get("state") == "commissioned" or at_action):
            visible["payload"] = {
                "private": True,
                "action_id": action_id,
                "state": authoritative.get("state", record.get("state") if isinstance(record, dict) else None),
            }
    return visible


class RevisionConflict(RuntimeError):
    pass


class PersistentWorldStore:
    def __init__(self, database_path: Path | str):
        self.database_path = str(database_path)
        self._local = threading.local()
        self._initialize()

    def _connection(self) -> sqlite3.Connection:
        connection = getattr(self._local, "connection", None)
        if connection is None:
            connection = sqlite3.connect(self.database_path, timeout=15, isolation_level=None)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("PRAGMA foreign_keys=ON")
            self._local.connection = connection
        return connection

    def _initialize(self) -> None:
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        connection = self._connection()
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS worlds (
                world_id TEXT PRIMARY KEY, revision INTEGER NOT NULL, tick INTEGER NOT NULL,
                last_wall_ms INTEGER NOT NULL, state_json TEXT NOT NULL, updated_ms INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS world_events (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT, world_id TEXT NOT NULL, revision INTEGER NOT NULL,
                tick INTEGER NOT NULL, event_type TEXT NOT NULL, actor_id TEXT NOT NULL,
                payload_json TEXT NOT NULL, created_ms INTEGER NOT NULL,
                FOREIGN KEY(world_id) REFERENCES worlds(world_id)
            );
            CREATE INDEX IF NOT EXISTS idx_world_events_world_sequence ON world_events(world_id, sequence);
            CREATE TABLE IF NOT EXISTS processed_actions (
                world_id TEXT NOT NULL, action_id TEXT NOT NULL, result_json TEXT NOT NULL,
                created_ms INTEGER NOT NULL, PRIMARY KEY(world_id, action_id)
            );
            CREATE TABLE IF NOT EXISTS runclock_lease (
                world_id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, expires_ms INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS causal_projections (
                world_id TEXT NOT NULL, event_sequence INTEGER NOT NULL,
                projector TEXT NOT NULL, result_json TEXT NOT NULL,
                created_ms INTEGER NOT NULL,
                PRIMARY KEY(world_id, event_sequence, projector),
                FOREIGN KEY(event_sequence) REFERENCES world_events(sequence)
            );
            CREATE INDEX IF NOT EXISTS idx_causal_projections_world_event
                ON causal_projections(world_id, event_sequence);
        """)

    def close(self) -> None:
        connection = getattr(self._local, "connection", None)
        if connection is not None:
            connection.close()
            self._local.connection = None

    @contextmanager
    def transaction(self):
        connection = self._connection()
        connection.execute("BEGIN IMMEDIATE")
        try:
            yield connection
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise

    def create_world(self, world_id: str = DEFAULT_WORLD_ID, now_ms: Optional[int] = None) -> Dict[str, Any]:
        now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
        state = founding_table_seed(now_ms)
        with self.transaction() as connection:
            connection.execute("INSERT OR IGNORE INTO worlds VALUES (?, ?, ?, ?, ?, ?)", (world_id, 1, 0, now_ms, json.dumps(state, separators=(",", ":")), now_ms))
            row = connection.execute("SELECT * FROM worlds WHERE world_id = ?", (world_id,)).fetchone()
        return self._snapshot(row)

    def _snapshot(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {"world_id": row["world_id"], "revision": row["revision"], "tick": row["tick"], "last_wall_ms": row["last_wall_ms"], "state": migrate_state(json.loads(row["state_json"])), "updated_ms": row["updated_ms"]}

    def snapshot(self, world_id: str = DEFAULT_WORLD_ID) -> Dict[str, Any]:
        row = self._connection().execute("SELECT * FROM worlds WHERE world_id = ?", (world_id,)).fetchone()
        if not row:
            return self.create_world(world_id)
        return self._snapshot(row)

    def observed_snapshot(self, world_id: str, actor_id: str) -> Dict[str, Any]:
        return actor_world_view(self.snapshot(world_id), actor_id)

    def events(self, world_id: str, after: int = 0, limit: int = 250) -> list[Dict[str, Any]]:
        rows = self._connection().execute("SELECT * FROM world_events WHERE world_id = ? AND sequence > ? ORDER BY sequence LIMIT ?", (world_id, after, min(limit, 1000))).fetchall()
        return [{"sequence": row["sequence"], "revision": row["revision"], "tick": row["tick"], "type": row["event_type"], "actor_id": row["actor_id"], "payload": json.loads(row["payload_json"]), "created_ms": row["created_ms"]} for row in rows]

    def acquire_lease(self, world_id: str, owner_id: str, now_ms: int, lease_ms: int = 5000) -> bool:
        with self.transaction() as connection:
            row = connection.execute("SELECT * FROM runclock_lease WHERE world_id = ?", (world_id,)).fetchone()
            if row and row["owner_id"] != owner_id and row["expires_ms"] > now_ms:
                return False
            connection.execute("INSERT INTO runclock_lease VALUES (?, ?, ?) ON CONFLICT(world_id) DO UPDATE SET owner_id=excluded.owner_id, expires_ms=excluded.expires_ms", (world_id, owner_id, now_ms + lease_ms))
            return True

    def advance_due(self, world_id: str = DEFAULT_WORLD_ID, now_ms: Optional[int] = None, max_ticks: int = 240) -> Dict[str, Any]:
        now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
        with self.transaction() as connection:
            row = connection.execute("SELECT * FROM worlds WHERE world_id = ?", (world_id,)).fetchone()
            if not row:
                state = founding_table_seed(now_ms)
                connection.execute("INSERT INTO worlds VALUES (?, 1, 0, ?, ?, ?)", (world_id, now_ms, json.dumps(state, separators=(",", ":")), now_ms))
                row = connection.execute("SELECT * FROM worlds WHERE world_id = ?", (world_id,)).fetchone()
            state = migrate_state(json.loads(row["state_json"]))
            tick_ms = int(state["clock"]["tick_seconds"] * 1000)
            due = 0 if state["clock"].get("paused") else min(max_ticks, max(0, (now_ms - row["last_wall_ms"]) // tick_ms))
            revision = row["revision"]
            tick = row["tick"]
            for _ in range(due):
                tick += 1
                emitted = reduce_world_tick(state, tick)
                revision += 1
                for event in emitted:
                    connection.execute("INSERT INTO world_events(world_id, revision, tick, event_type, actor_id, payload_json, created_ms) VALUES (?, ?, ?, ?, ?, ?, ?)", (world_id, revision, tick, event["type"], event["actor_id"], json.dumps(event["payload"], separators=(",", ":")), now_ms))
            state["clock"]["tick"] = tick
            if due:
                state["clock"]["minute"] = (state["clock"]["minute"] + due * 5) % 1440
            consumed_wall = row["last_wall_ms"] + due * tick_ms
            connection.execute("UPDATE worlds SET revision=?, tick=?, last_wall_ms=?, state_json=?, updated_ms=? WHERE world_id=?", (revision, tick, consumed_wall, json.dumps(state, separators=(",", ":")), now_ms, world_id))
            updated = connection.execute("SELECT * FROM worlds WHERE world_id = ?", (world_id,)).fetchone()
        self.process_causal_events(world_id, now_ms=now_ms)
        result = self.snapshot(world_id)
        result["advanced_ticks"] = due
        result["catchup_remaining"] = max(0, (now_ms - consumed_wall) // tick_ms)
        return result

    def apply_action(self, world_id: str, action_id: str, actor_id: str, action: Dict[str, Any], expected_revision: Optional[int] = None, now_ms: Optional[int] = None) -> Dict[str, Any]:
        if action.get("type") == "owner_directive":
            raise PermissionError("Owner directives require the authenticated owner route")
        return self._apply_committed_action(world_id, action_id, actor_id, action, expected_revision, now_ms, "player_action")

    def apply_owner_directive(self, world_id: str, action_id: str, owner_id: str, directive: Dict[str, Any], expected_revision: Optional[int] = None, now_ms: Optional[int] = None) -> Dict[str, Any]:
        action = {"type": "owner_directive", "directive": dict(directive)}
        return self._apply_committed_action(world_id, action_id, owner_id, action, expected_revision, now_ms, "owner_directive")

    def _apply_committed_action(self, world_id: str, action_id: str, actor_id: str, action: Dict[str, Any], expected_revision: Optional[int], now_ms: Optional[int], event_type: str) -> Dict[str, Any]:
        now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
        was_duplicate = False
        with self.transaction() as connection:
            duplicate = connection.execute("SELECT result_json FROM processed_actions WHERE world_id=? AND action_id=?", (world_id, action_id)).fetchone()
            if duplicate:
                was_duplicate = True
                result = json.loads(duplicate["result_json"])
            else:
                row = connection.execute("SELECT * FROM worlds WHERE world_id=?", (world_id,)).fetchone()
                if not row:
                    raise KeyError(world_id)
                if expected_revision is not None and row["revision"] != expected_revision:
                    raise RevisionConflict(f"expected revision {expected_revision}, current {row['revision']}")
                state = migrate_state(json.loads(row["state_json"]))
                payload = apply_player_action(state, actor_id, action)
                revision = row["revision"] + 1
                connection.execute("UPDATE worlds SET revision=?, state_json=?, updated_ms=? WHERE world_id=?", (revision, json.dumps(state, separators=(",", ":")), now_ms, world_id))
                connection.execute("INSERT INTO world_events(world_id, revision, tick, event_type, actor_id, payload_json, created_ms) VALUES (?, ?, ?, ?, ?, ?, ?)", (world_id, revision, row["tick"], event_type, actor_id, json.dumps(payload, separators=(",", ":")), now_ms))
                result = {"world_id": world_id, "revision": revision, "tick": row["tick"], "result": payload}
                connection.execute("INSERT INTO processed_actions VALUES (?, ?, ?, ?)", (world_id, action_id, json.dumps(result, separators=(",", ":")), now_ms))
        projection = self.process_causal_events(world_id, now_ms=now_ms)
        if not was_duplicate and projection["revision"] != result["revision"]:
            result["revision"] = projection["revision"]
            with self.transaction() as connection:
                connection.execute(
                    "UPDATE processed_actions SET result_json=? WHERE world_id=? AND action_id=?",
                    (json.dumps(result, separators=(",", ":")), world_id, action_id),
                )
        return result

    def process_causal_events(self, world_id: str = DEFAULT_WORLD_ID, now_ms: Optional[int] = None, max_events: int = 1000) -> Dict[str, Any]:
        """Project committed history into perceptions and durable future reactions."""
        now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
        projector = "world-causality-v1"
        with self.transaction() as connection:
            row = connection.execute("SELECT * FROM worlds WHERE world_id=?", (world_id,)).fetchone()
            if not row:
                raise KeyError(world_id)
            events = connection.execute(
                """SELECT event.* FROM world_events event
                   LEFT JOIN causal_projections projection
                     ON projection.world_id=event.world_id
                    AND projection.event_sequence=event.sequence
                    AND projection.projector=?
                   WHERE event.world_id=? AND projection.event_sequence IS NULL
                   ORDER BY event.sequence LIMIT ?""",
                (projector, world_id, min(max_events, 5000)),
            ).fetchall()
            state = migrate_state(json.loads(row["state_json"]))
            changed = False
            emitted = []
            for event in events:
                projection = project_committed_event(state, event)
                changed = changed or projection["changed"]
                emitted.extend(projection["events"])
                connection.execute(
                    "INSERT INTO causal_projections VALUES (?, ?, ?, ?, ?)",
                    (world_id, event["sequence"], projector, json.dumps(projection, separators=(",", ":")), now_ms),
                )
            revision = row["revision"]
            if changed:
                revision += 1
                connection.execute(
                    "UPDATE worlds SET revision=?, state_json=?, updated_ms=? WHERE world_id=?",
                    (revision, json.dumps(state, separators=(",", ":")), now_ms, world_id),
                )
                for event in emitted:
                    connection.execute(
                        "INSERT INTO world_events(world_id, revision, tick, event_type, actor_id, payload_json, created_ms) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (world_id, revision, row["tick"], event["type"], event["actor_id"], json.dumps(event["payload"], separators=(",", ":")), now_ms),
                    )
        return {"world_id": world_id, "projected": len(events), "changed": changed, "revision": revision}


INITIATIVE_BLUEPRINTS = {
    "sanitation": {"place": "sanitation", "inputs": {"timber": 3, "stone": 4}, "workers": ["orin", "cal", "imani"], "inspector": "mira"},
    "storage": {"place": "dry_storage", "inputs": {"timber": 5, "stone": 2}, "workers": ["dev", "cal", "nyra"], "inspector": "sora"},
    "water": {"place": "water_source", "inputs": {"stone": 5, "containers": 2}, "workers": ["emil", "ada", "orin"], "inspector": "mira"},
    "food": {"place": "communal_kitchen", "inputs": {"raw_food": 12, "tested_water": 6, "fuel": 3}, "workers": ["lena", "tomas", "nyra"], "inspector": "imani"},
}

INITIATIVE_EVIDENCE_TAGS = {
    "sanitation": ["drainage survey", "separation measurement"],
    "storage": ["capacity measurement", "moisture check"],
    "water": ["survey", "water test"],
    "food": ["temperature log", "portion count"],
}


def _evidence_tag(value: Any) -> str:
    return " ".join(str(value).strip().lower().replace("_", " ").split())[:120]


def _remember_consequence(state: Dict[str, Any], tick: int, cause: str, effect: str, subjects: list[str]) -> Dict[str, Any]:
    record = {"id": f"consequence-{tick}-{len(state['consequences']) + 1}", "tick": tick, "cause": cause, "effect": effect, "subjects": subjects}
    state["consequences"].append(record)
    state["consequences"] = state["consequences"][-250:]
    return record


MATERIAL_BASE_VALUES = {"timber": 3.0, "stone": 4.0, "raw_food": 2.0, "fuel": 3.0, "containers": 5.0}
FRONTIER_BASE_VALUES = {"soil": 1.0, "clay": 2.5, "iron_ore": 6.0}
SETTLEMENT_REORDER_TARGETS = {"timber": 25, "stone": 20, "raw_food": 36, "fuel": 20, "containers": 12}


def _create_stewardship_contract(state: Dict[str, Any], order: Dict[str, Any], site: Dict[str, Any], tick: int) -> Dict[str, Any]:
    remaining = _regional_remaining(state, "timber")
    capacity = max(1, state["environment"]["regional_capacity"]["timber"])
    scarcity = round(max(0.0, min(1.0, 1 - remaining / capacity)), 4)
    local_depletion = round(1 - site["stock"] / max(1, site["capacity"]), 4)
    multiplier = round(1 + scarcity * 0.5 + local_depletion * 0.25, 4)
    asks = {
        order["worker"]: round(8.0 * multiplier, 2),
        order["inspector"]: round(4.0 * multiplier, 2),
    }
    contract = {
        "id": f"contract-{len(state['economy']['work_contracts']) + 1}", "kind": "public_environmental_work",
        "source_order_id": order["id"], "status": "proposed", "created_tick": tick,
        "funding_account": "treasury", "unit": "CU-placeholder", "spendable": False,
        "valuation_basis": {"regional_timber_scarcity": scarcity, "local_depletion": local_depletion, "multiplier": multiplier},
        "roles": {order["worker"]: "restoration_labor", order["inspector"]: "independent_inspection"},
        "asks": asks, "history": [{"tick": tick, "status": "proposed", "offers": dict(asks)}],
        "settlements": [],
    }
    state["economy"]["work_contracts"].append(contract)
    order["contract_id"] = contract["id"]
    return contract


def _process_contract_negotiation(state: Dict[str, Any], tick: int) -> list[Dict[str, Any]]:
    """Advance autonomous provisional negotiations one durable state at a time."""
    emitted: list[Dict[str, Any]] = []
    for contract in state["economy"]["work_contracts"]:
        if contract["status"] == "proposed":
            contract["counteroffers"] = {actor: round(amount * 0.9, 2) for actor, amount in contract["asks"].items()}
            contract["status"] = "countered"
            contract["countered_tick"] = tick
            contract["history"].append({"tick": tick, "status": "countered", "offers": dict(contract["counteroffers"]), "by": "sora"})
            _remember_consequence(state, tick, f"contract-proposal:{contract['id']}", f"treasury-counteroffer:{contract['id']}", [*contract["asks"], "sora", "treasury"])
            emitted.append({"type": "contract_countered", "actor_id": "sora", "payload": {"contract_id": contract["id"], "counteroffers": dict(contract["counteroffers"])}})
        elif contract["status"] == "countered":
            contract["agreed"] = {actor: round((contract["asks"][actor] + contract["counteroffers"][actor]) / 2, 2) for actor in contract["asks"]}
            contract["status"] = "accepted"
            contract["accepted_tick"] = tick
            contract["history"].append({"tick": tick, "status": "accepted", "offers": dict(contract["agreed"]), "accepted_by": sorted(contract["asks"])})
            _remember_consequence(state, tick, f"treasury-counteroffer:{contract['id']}", f"contract-accepted:{contract['id']}", [*contract["asks"], "sora", "treasury"])
            emitted.append({"type": "contract_accepted", "actor_id": "sora", "payload": {"contract_id": contract["id"], "agreed": dict(contract["agreed"]), "spendable": False}})
    return emitted


def _regional_remaining(state: Dict[str, Any], resource: str) -> int:
    return sum(int(region.get("stocks", {}).get(resource, 0)) for region in state["environment"]["regions"].values())


def _update_material_signal(state: Dict[str, Any], resource: str, tick: int, cause: str) -> Dict[str, Any]:
    remaining = _regional_remaining(state, resource)
    capacity = max(1, int(state["environment"]["regional_capacity"].get(resource, remaining or 1)))
    scarcity = round(max(0.0, min(1.0, 1 - remaining / capacity)), 4)
    base_value = MATERIAL_BASE_VALUES.get(resource, FRONTIER_BASE_VALUES.get(resource, 1.0))
    value = round(base_value * (1 + scarcity * 2), 2)
    prior = state["economy"]["market_signals"].get(resource)
    signal = {
        "resource": resource, "tick": tick, "remaining": remaining, "capacity": capacity,
        "scarcity": scarcity, "provisional_unit_value": value, "cause": cause,
    }
    state["economy"]["market_signals"][resource] = signal
    state["economy"]["prices"][resource] = value
    if not prior or prior["remaining"] != remaining or prior["provisional_unit_value"] != value:
        state["economy"]["market_history"].append(signal)
        state["economy"]["market_history"] = state["economy"]["market_history"][-500:]
    return signal


def _process_material_economy(state: Dict[str, Any], tick: int) -> list[Dict[str, Any]]:
    emitted = []
    for resource in MATERIAL_BASE_VALUES:
        _update_material_signal(state, resource, tick, "scheduled regional inventory")
    maintenance_demand = None
    for order in state["institutions"]["governance"].get("maintenance_orders", []):
        if order["status"] != "open" or not order.get("assigned_to") or not any(blocker.get("status") == "unresolved" for blocker in order.get("blockers", [])):
            continue
        for resource, required in order.get("required_inputs", {}).items():
            missing = max(0, required - state["resources"].get(resource, 0))
            if missing and resource in MATERIAL_BASE_VALUES:
                maintenance_demand = (order, resource, missing)
                break
        if maintenance_demand:
            break
    shortages = []
    for resource, target in SETTLEMENT_REORDER_TARGETS.items():
        held = state["resources"].get(resource, 0)
        if held < target:
            shortages.append((round((target - held) / target, 4), resource, target - held))
    if maintenance_demand or shortages:
        demand_order, resource, missing = maintenance_demand if maintenance_demand else (None, *max(shortages, key=lambda item: (item[0], item[1]))[1:])
        signal = state["economy"]["market_signals"][resource]
        critical = state["resources"].get(resource, 0) < SETTLEMENT_REORDER_TARGETS[resource] * 0.25
        if demand_order or signal["scarcity"] < 0.75 or critical:
            sources = [region for region in state["environment"]["regions"].values() if region.get("stocks", {}).get(resource, 0) > 0]
            if sources:
                source = max(sources, key=lambda region: (region["stocks"][resource], region["name"]))
                amount = min(3, missing, source["stocks"][resource])
                source["stocks"][resource] -= amount
                state["resources"][resource] = state["resources"].get(resource, 0) + amount
                extraction = {
                    "tick": tick, "actor": "orin", "resource": resource, "amount": amount,
                    "method": "maintenance shortage procurement" if demand_order else "council shortage procurement", "source": source["name"],
                    "remaining": source["stocks"][resource], "verified_by": "dev",
                }
                if demand_order:
                    extraction["order_id"] = demand_order["id"]
                state["environment"]["extraction_history"].append(extraction)
                causal_sources = [f"procurement-demand:{demand_order['id']}:{resource}"] if demand_order else []
                _evidence(state, tick, f"verified {resource} procurement", ["orin", "rae"], {}, ["handcart", "measuring_line"], {"amount": amount, "regional_remaining": _regional_remaining(state, resource)}, "dev", causal_sources, ["measured delivery", "finite source record"])
                updated = _update_material_signal(state, resource, tick, f"verified procurement:{tick}")
                provisional = round(amount * updated["provisional_unit_value"], 2)
                _provisional_claim(state, tick, "orin", f"verified {resource} procurement", provisional, f"procurement:{tick}:{resource}")
                state["npcs"]["orin"]["intention"] = f"deliver {resource} from {source['name']}"
                state["npcs"]["orin"]["reason"] = f"Repair order {demand_order['id']} cannot proceed without a measured delivery." if demand_order else f"Settlement stock fell {missing} below its reorder target."
                knowledge_kind = "maintenance_procurement" if demand_order else "material_procurement"
                state["institutions"]["council"]["knowledge"].append({"tick": tick, "kind": knowledge_kind, **extraction, "provisional_unit_value": updated["provisional_unit_value"]})
                cause = f"procurement-demand:{demand_order['id']}:{resource}" if demand_order else f"shortage:{resource}:{missing}"
                _remember_consequence(state, tick, cause, f"verified-procurement:{resource}:{amount}", ["orin", "rae", "dev", *( ["ada"] if demand_order else [])])
                if demand_order:
                    demand_order["procurement_history"].append(dict(extraction))
                emitted.append({"type": "material_procured", "actor_id": "orin", "payload": extraction})
            elif demand_order:
                notice_key = f"{resource}:{_regional_remaining(state, resource)}"
                if not demand_order["depletion_notices"] or demand_order["depletion_notices"][-1]["key"] != notice_key:
                    notice = {"tick": tick, "key": notice_key, "resource": resource, "regional_remaining": 0, "status": "unresolved"}
                    demand_order["depletion_notices"].append(notice)
                    _remember_consequence(state, tick, f"procurement-demand:{demand_order['id']}:{resource}", f"regional-depletion:{resource}", ["orin", "ada", "dev", "environment"])
                    emitted.append({"type": "material_procurement_blocked", "actor_id": "orin", "payload": {"order_id": demand_order["id"], "resource": resource, "regional_remaining": 0}})
    if tick % 96 == 0:
        regenerated = {}
        for region in state["environment"]["regions"].values():
            for resource, rate in {"timber": 1, "raw_food": 2, "fuel": 1}.items():
                current = region.get("stocks", {}).get(resource)
                if current is None:
                    continue
                capacity_share = founding_table_seed(0)["environment"]["regions"].get(next((key for key, value in state["environment"]["regions"].items() if value is region), ""), {}).get("stocks", {}).get(resource, current)
                gained = min(rate, max(0, capacity_share - current))
                if gained:
                    region["stocks"][resource] += gained
                    regenerated[resource] = regenerated.get(resource, 0) + gained
        if regenerated:
            for resource in regenerated:
                _update_material_signal(state, resource, tick, f"natural regeneration:{tick}")
            _remember_consequence(state, tick, "elapsed-seasonal-time", f"regional-regeneration:{regenerated}", ["environment"])
            emitted.append({"type": "regional_regeneration", "actor_id": "environment", "payload": {"resources": regenerated}})
    return emitted


def _npc_reply(npc: Dict[str, Any], content: str, state: Dict[str, Any], actor_id: Optional[str] = None) -> str:
    words = content.lower()
    relationship = npc.get("relationships", {}).get(actor_id, {"trust": 0.5}) if actor_id else {"trust": 0.5}
    trust = float(relationship.get("trust", 0.5))
    if npc["id"] == "dev" and any(word in words for word in ("borrow", "checkout", "tool", "trust")):
        if trust < 0.35:
            return f"Our custody history is at trust {trust:.2f}. I will offer one supervised checkout; return it intact and ordinary access can recover."
        if trust >= 0.7:
            return f"Our custody history is dependable at trust {trust:.2f}. I can issue ordinary recorded access when stock allows."
        return f"Our custody history stands at trust {trust:.2f}. Ordinary recorded checkout remains available while agreements are kept."
    if any(word in words for word in ("work", "help", "job")):
        return f"I am trying to {npc['intention']}. {npc['reason']}"
    if any(word in words for word in ("tree", "wood", "stone", "mine", "resource")):
        scarce = sorted(state["economy"].get("market_signals", {}).values(), key=lambda item: (-item["scarcity"], item["resource"]))
        return f"Check the expedition records. {scarce[0]['resource']} is our tightest measured regional stock." if scarce else "The woods, ridge, and marsh have different materials; record what you remove."
    if any(word in words for word in ("hello", "hi", "hey")):
        return f"Hello. I am {npc['name']}. I can listen and respond; right now I am trying to {npc['intention'].lower()}."
    if "?" in content or any(word in words for word in ("why", "what", "where", "when", "how", "can you")):
        return f"From what I can currently perceive, {npc['reason'].lower()} Ask me about my work, nearby resources, or what help is needed."
    return f"I heard you. {npc['reason']} I can keep talking even while I decide what to do next."


DISCOURSE_KEYWORDS = {
    "water": ("water", "well", "drink", "hydration"),
    "food": ("food", "meal", "cook", "hunger", "farm"),
    "storage": ("storage", "warehouse", "spoil", "preserve", "container"),
    "sanitation": ("sanitation", "waste", "sewer", "drain", "latrine", "cleanliness"),
}


def _discourse_priority(content: str) -> Optional[str]:
    words = content.lower()
    matches = [priority for priority, keywords in DISCOURSE_KEYWORDS.items() if any(keyword in words for keyword in keywords)]
    return sorted(matches)[0] if matches else None


def _record_witnessed_discourse(state: Dict[str, Any], message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Persist a civic claim without letting speech directly mutate the physical world."""
    priority = _discourse_priority(message["content"])
    witnesses = sorted({actor_id for actor_id in message.get("audible_to", []) if actor_id in state["npcs"]})
    if not priority or not witnesses:
        return None
    discourse = state["communications"]["public_discourse"]
    duplicate = any(
        claim["speaker_id"] == message["speaker_id"]
        and claim["priority"] == priority
        and claim["tick"] == message["tick"]
        for claim in discourse["claims"]
    )
    if duplicate:
        return None
    claim = {
        "id": f"claim-{message['id']}", "message_id": message["id"], "tick": message["tick"],
        "speaker_id": message["speaker_id"], "priority": priority, "witnesses": witnesses,
        "status": "witnessed", "physical_change": False,
    }
    discourse["claims"].append(claim)
    discourse["claims"] = discourse["claims"][-500:]
    return claim


def _process_public_discourse(state: Dict[str, Any], tick: int) -> list[Dict[str, Any]]:
    """Convert accumulated, independently witnessed speech into revisable civic pressure."""
    discourse = state["communications"]["public_discourse"]
    emitted = []
    for priority in sorted(DISCOURSE_KEYWORDS):
        claims = [claim for claim in discourse["claims"] if claim["priority"] == priority and claim["status"] == "witnessed"]
        distinct_ticks = sorted({claim["tick"] for claim in claims})
        witnesses = sorted({witness for claim in claims for witness in claim["witnesses"]})
        if len(distinct_ticks) < 3 or len(witnesses) < 2:
            continue
        escalation_id = f"discourse-{priority}-{distinct_ticks[0]}-{tick}"
        selected = [claim for claim in claims if claim["tick"] in distinct_ticks[:3]]
        escalation = {
            "id": escalation_id, "tick": tick, "priority": priority,
            "claim_ids": [claim["id"] for claim in selected], "speakers": sorted({claim["speaker_id"] for claim in selected}),
            "witnesses": witnesses, "pressure": 20.0, "status": "entered_agenda",
            "physical_change": False,
        }
        discourse["escalations"].append(escalation)
        for claim in selected:
            claim["status"] = "escalated"
            claim["escalation_id"] = escalation_id
        council = state["institutions"]["council"]
        council["public_pressure"][priority] = min(60.0, council["public_pressure"].get(priority, 0.0) + escalation["pressure"])
        council["endorsements"][f"discourse:{escalation_id}"] = priority
        council["knowledge"].append({
            "tick": tick, "kind": "witnessed_public_discourse", "priority": priority,
            "claim_ids": escalation["claim_ids"], "witnesses": witnesses, "pressure": escalation["pressure"],
        })
        _remember_consequence(state, tick, f"witnessed-discourse:{','.join(escalation['claim_ids'])}", f"council-pressure:{priority}:+20", [*witnesses, "sora", "council"])
        emitted.append({"type": "public_discourse_escalated", "actor_id": "sora", "payload": dict(escalation)})
    discourse["escalations"] = discourse["escalations"][-200:]
    return emitted


def _process_proximity_speech(state: Dict[str, Any], tick: int) -> list[Dict[str, Any]]:
    if tick % 8 != 0:
        return []
    candidates = []
    for npc in state["npcs"].values():
        npc_witnesses = [other for other in state["npcs"].values() if other["id"] != npc["id"] and _distance(other["location"], npc["location"]) <= 4]
        if npc_witnesses:
            candidates.append((npc, npc_witnesses))
    if not candidates:
        return []
    npc, npc_witnesses = min(candidates, key=lambda item: (item[0]["needs"]["belonging"], item[0]["id"]))
    pressures = _settlement_pressures(state)
    priority = min(pressures, key=lambda key: (-pressures[key], key))
    line = f"I am concerned about {priority}. {npc['reason']} I am going to {npc['intention']}."
    player_witnesses = [player_id for player_id, player in state["players"].items() if _distance(player["location"], npc["location"]) <= 4]
    audible_to = sorted({*[other["id"] for other in npc_witnesses], *player_witnesses})
    message = {"id": f"speech-{tick}-{npc['id']}", "tick": tick, "speaker_id": npc["id"], "speaker": npc["name"], "content": line, "kind": "autonomous", "audible_to": audible_to, "location": list(npc["location"])}
    state["communications"]["messages"].append(message)
    state["communications"]["messages"] = state["communications"]["messages"][-250:]
    civic_discourse_ready = (
        state["event"]["status"] == "completed"
        and bool(state["institutions"]["council"].get("completed_initiatives"))
    )
    claim = _record_witnessed_discourse(state, message) if civic_discourse_ready else None
    if claim:
        for witness in npc_witnesses:
            witness["memories"].append({
                "tick": tick, "kind": "overheard_discourse", "speaker": npc["id"],
                "priority": priority, "message_id": message["id"],
                "text": f"Heard {npc['name']} raise a {priority} concern in proximity.",
            })
    return [{"type": "npc_spoke", "actor_id": npc["id"], "payload": message}]


def _advance_resource_sites(state: Dict[str, Any], tick: int) -> list[Dict[str, Any]]:
    emitted = []
    for player in state["players"].values():
        player["energy"] = round(min(100.0, player.get("energy", 100.0) + 0.15), 2)
    for site in state["resource_sites"].values():
        if site["type"] == "farm" and site["stage"] == "growing" and site["ready_tick"] <= tick:
            site["stage"], site["stock"] = "ripe", site["capacity"]
            site["history"].append({"tick": tick, "actor": "environment", "operation": "crop_matured", "outputs": {"raw_food": site["stock"]}})
            emitted.append({"type": "crop_matured", "actor_id": "environment", "payload": {"site_id": site["id"], "stock": site["stock"]}})
        elif site["type"] == "well" and site["progress"] >= 3 and tick % 4 == 0:
            site["stock"] = min(site["capacity"], site["stock"] + 1)
        elif site["type"] == "cattle":
            site["wellbeing"] = round(max(0.0, site["wellbeing"] - 0.04), 2)
            if site["fed_until_tick"] >= tick and site["wellbeing"] >= 50:
                site["stock"] = round(min(site["capacity"], site["stock"] + 0.03), 2)
        elif site["type"] in {"tree", "reeds"} and tick % 96 == 0 and site["stock"] < site["capacity"]:
            site["stock"] += 1
            material = "timber" if site["type"] == "tree" else "containers"
            region = state["environment"]["regions"][site["region"]]
            region["stocks"][material] = region["stocks"].get(material, 0) + 1
            site["history"].append({"tick": tick, "actor": "environment", "operation": "regenerated", "outputs": {material: 1}})
            emitted.append({"type": "site_regenerated", "actor_id": "environment", "payload": {"site_id": site["id"], "resource": material, "amount": 1}})
    return emitted


def _process_environmental_stewardship(state: Dict[str, Any], tick: int) -> list[Dict[str, Any]]:
    """Turn severe local depletion into supplied, spatial, inspected restoration work."""
    environment = state["environment"]
    orders = environment["stewardship_orders"]
    emitted: list[Dict[str, Any]] = []
    active = next((order for order in orders if order["status"] not in {"completed", "cancelled"}), None)
    if not active and state["event"]["status"] == "completed":
        depleted = sorted(
            (site for site in state["resource_sites"].values() if site["type"] == "tree" and site["stock"] <= site["capacity"] * 0.25),
            key=lambda site: (site["stock"] / max(1, site["capacity"]), site["id"]),
        )
        if depleted:
            site = depleted[0]
            practice = next((item for item in state["education"]["practice_orders"] if item["status"] == "awaiting_real_work" and item["domain"] == "environmental_stewardship"), None)
            qualified = [
                npc for npc in state["npcs"].values()
                if _shared_competence(npc, "environmental_stewardship") >= 0.3
                and min(npc["needs"][name] for name in ("nutrition", "hydration", "rest")) >= 24
            ]
            supervised = None
            if practice:
                supervisor = state["npcs"].get(practice["supervisor"])
                learner = state["npcs"].get(practice["learner"])
                if supervisor and learner and _shared_competence(supervisor, practice["domain"]) >= 0.3 and min(*(supervisor["needs"][name] for name in ("nutrition", "hydration", "rest")), *(learner["needs"][name] for name in ("nutrition", "hydration", "rest"))) >= 24:
                    supervised = practice
            worker_id = supervised["learner"] if supervised else max(qualified, key=lambda npc: (_shared_competence(npc, "environmental_stewardship"), npc["id"]))["id"] if qualified else "cal"
            active = {
                "id": f"stewardship-{len(orders) + 1}", "kind": "reforestation", "site_id": site["id"],
                "status": "proposed", "created_tick": tick, "cause_stock": site["stock"],
                "required_inputs": {"seed": 2, "tested_water": 2}, "worker": worker_id, "inspector": "mira",
                "history": [{"tick": tick, "status": "proposed", "cause_stock": site["stock"]}], "blockers": [],
            }
            if supervised:
                active.update({"supervisor": supervised["supervisor"], "practice_order_id": supervised["id"]})
                supervised.update({"status": "assigned_real_work", "work_order_id": active["id"], "assigned_tick": tick})
                supervised["history"].append({"tick": tick, "status": "assigned_real_work", "work_order_id": active["id"], "site_id": site["id"]})
            orders.append(active)
            contract = _create_stewardship_contract(state, active, site, tick)
            _remember_consequence(state, tick, f"local-depletion:{site['id']}:{site['stock']}", f"stewardship-order:{active['id']}", ["environment", "cal", "mira", "council"])
            _remember_consequence(state, tick, f"stewardship-order:{active['id']}", f"contract-proposal:{contract['id']}", [active["worker"], active["inspector"], "sora", "treasury"])
            emitted.append({"type": "stewardship_proposed", "actor_id": "environment", "payload": dict(active)})
            return emitted
    if not active:
        return emitted
    site = state["resource_sites"][active["site_id"]]
    worker = state["npcs"][active["worker"]]
    inspector = state["npcs"][active["inspector"]]
    supervisor = state["npcs"].get(active.get("supervisor"))
    contract = next(item for item in state["economy"]["work_contracts"] if item["id"] == active["contract_id"])
    participants = [worker, inspector, *([supervisor] if supervisor else [])]
    if min(*(npc["needs"][name] for npc in participants for name in ("nutrition", "hydration", "rest"))) < 24:
        if not active.get("pause_reason"):
            active["pause_reason"] = "worker survival need below safe-work threshold"
            active["history"].append({"tick": tick, "status": "paused_needs", "reason": active["pause_reason"]})
            emitted.append({"type": "stewardship_paused", "actor_id": worker["id"], "payload": {"order_id": active["id"], "reason": active["pause_reason"]}})
        return emitted
    active.pop("pause_reason", None)
    if active["status"] in {"proposed", "negotiating", "blocked_inputs"}:
        if contract["status"] != "accepted":
            active["status"] = "negotiating"
            if not active["history"] or active["history"][-1].get("contract_status") != contract["status"]:
                active["history"].append({"tick": tick, "status": "negotiating", "contract_id": contract["id"], "contract_status": contract["status"]})
            return emitted
        store = state["resource_sites"]["tool-counter"]
        missing = {}
        if store["stock"].get("seed", 0) < active["required_inputs"]["seed"]:
            missing["seed"] = active["required_inputs"]["seed"] - store["stock"].get("seed", 0)
        if state["resources"].get("tested_water", 0) < active["required_inputs"]["tested_water"]:
            missing["tested_water"] = active["required_inputs"]["tested_water"] - state["resources"].get("tested_water", 0)
        if missing:
            signature = ",".join(f"{key}:{missing[key]}" for key in sorted(missing))
            if not active["blockers"] or active["blockers"][-1].get("signature") != signature:
                blocker = {"tick": tick, "status": "unresolved", "signature": signature, "missing": missing}
                active["blockers"].append(blocker)
                _remember_consequence(state, tick, f"stewardship-order:{active['id']}", f"restoration-input-shortage:{signature}", [worker["id"], "dev", "environment"])
                emitted.append({"type": "stewardship_blocked", "actor_id": worker["id"], "payload": {"order_id": active["id"], "missing": missing}})
            active["status"] = "blocked_inputs"
            return emitted
        for blocker in active["blockers"]:
            if blocker["status"] == "unresolved":
                blocker["status"] = "recovered"
                blocker["recovered_tick"] = tick
        store["stock"]["seed"] -= active["required_inputs"]["seed"]
        state["resources"]["tested_water"] -= active["required_inputs"]["tested_water"]
        active["status"] = "traveling"
        active["supplied_tick"] = tick
        active["carried_inputs"] = dict(active["required_inputs"])
        active["history"].append({"tick": tick, "status": "supplied", "inputs": dict(active["required_inputs"])})
        _remember_consequence(state, tick, f"stewardship-inputs:{active['id']}", f"restoration-travel:{site['id']}", [worker["id"], inspector["id"], "dev"])
    if active["status"] == "traveling":
        for npc in participants:
            npc["location"] = _move_for_legacy(state, npc, site["location"])
            if npc["location"] == site["location"]:
                npc["current_region"] = site["region"]
        emitted.append({"type": "stewardship_movement", "actor_id": worker["id"], "payload": {"order_id": active["id"], "worker": list(worker["location"]), "inspector": list(inspector["location"])}})
        if all(npc["location"] == site["location"] for npc in participants):
            active["status"] = "recovering"
            active["planted_tick"] = tick
            active["recovery_due_tick"] = tick + 12
            active["history"].append({"tick": tick, "status": "planted", "site_stock": site["stock"]})
            work_actors = [worker["id"], *([supervisor["id"]] if supervisor else [])]
            _evidence(state, tick, f"reforestation planted at {site['name']}", work_actors, dict(active["required_inputs"]), ["shovel", "measuring_line"], {"seed_count": 2, "baseline_stock": site["stock"], "supervised": bool(supervisor)}, inspector["id"], [f"stewardship-order:{active['id']}"], ["planting count", "site baseline"])
            _remember_consequence(state, tick, f"restoration-travel:{site['id']}", f"ecological-recovery-pending:{active['id']}:{active['recovery_due_tick']}", [worker["id"], inspector["id"], "environment"])
    elif active["status"] == "recovering" and tick >= active["recovery_due_tick"]:
        before = site["stock"]
        gain = min(4, site["capacity"] - before)
        site["stock"] += gain
        region = state["environment"]["regions"][site["region"]]
        region["stocks"]["timber"] = region["stocks"].get("timber", 0) + gain
        active["restored_amount"] = gain
        active["status"] = "returning"
        active["inspected_tick"] = tick
        active["history"].append({"tick": tick, "status": "inspected", "before": before, "after": site["stock"], "gain": gain})
        _update_material_signal(state, "timber", tick, f"verified stewardship:{active['id']}")
        _evidence(state, tick, f"reforestation recovery verified at {site['name']}", [worker["id"], "environment"], dict(active["required_inputs"]), ["survey_stakes", "measuring_line"], {"stock_before": before, "stock_after": site["stock"], "restored": gain, "elapsed_ticks": tick - active["planted_tick"]}, inspector["id"], [f"ecological-recovery-pending:{active['id']}:{active['recovery_due_tick']}"], ["survival count", "stock measurement"])
        outcome_ratio = round(gain / 4, 4)
        labor_value = round(contract["agreed"][worker["id"]] * outcome_ratio, 2)
        inspection_value = contract["agreed"][inspector["id"]]
        labor_claim = _provisional_claim(state, tick, worker["id"], "verified ecological restoration labor", labor_value, f"stewardship:{active['id']}", contract["id"], {"outcome_ratio": outcome_ratio, "restored_units": gain})
        inspection_claim = _provisional_claim(state, tick, inspector["id"], "verified ecological restoration inspection", inspection_value, f"stewardship:{active['id']}", contract["id"], {"outcome_ratio": 1.0, "restored_units_inspected": gain})
        contract["status"] = "settled_provisional"
        contract["settled_tick"] = tick
        contract["outcome"] = {"expected_restored_units": 4, "verified_restored_units": gain, "outcome_ratio": outcome_ratio}
        contract["settlements"].extend([{"actor": worker["id"], "amount": labor_value, "claim_tick": labor_claim["tick"]}, {"actor": inspector["id"], "amount": inspection_value, "claim_tick": inspection_claim["tick"]}])
        contract["history"].append({"tick": tick, "status": "settled_provisional", "outcome": dict(contract["outcome"]), "settlements": copy.deepcopy(contract["settlements"])})
        _remember_consequence(state, tick, f"ecological-recovery-pending:{active['id']}:{active['recovery_due_tick']}", f"local-stock-restored:{site['id']}:+{gain}", [worker["id"], inspector["id"], "environment", "economy"])
        emitted.append({"type": "stewardship_verified", "actor_id": inspector["id"], "payload": {"order_id": active["id"], "site_id": site["id"], "restored": gain}})
    elif active["status"] == "returning":
        home = state["places"]["meeting_hall"]["location"]
        for npc in participants:
            npc["location"] = _move_for_legacy(state, npc, home)
            if npc["location"] == home:
                npc["current_region"] = "settlement"
        if all(npc["location"] == home for npc in participants):
            active["status"] = "completed"
            active["completed_tick"] = tick
            active["history"].append({"tick": tick, "status": "completed", "returned_to": list(home)})
            for npc in (worker, inspector):
                npc["memories"].append({"tick": tick, "kind": "completed_work", "text": f"Completed {active['id']} after restoring {site['name']} and returning to the settlement."})
            worker_record = worker.setdefault("competency_records", {}).setdefault("environmental_stewardship", {"demonstrated": 0.0, "provenance": []})
            achieved_competence = round(min(0.35, 0.1 + active["restored_amount"] * 0.0625), 4) if active.get("practice_order_id") else round(0.3 + min(0.4, active["restored_amount"] * 0.0875), 4)
            worker_record["demonstrated"] = max(worker_record["demonstrated"], achieved_competence)
            worker_record["provenance"].append(f"stewardship:{active['id']}")
            worker["competencies"]["environmental_stewardship"] = worker_record["demonstrated"]
            if active.get("practice_order_id"):
                practice = next(item for item in state["education"]["practice_orders"] if item["id"] == active["practice_order_id"])
                practice.update({"status": "completed", "completed_tick": tick, "verified_work_order_id": active["id"], "demonstrated": worker_record["demonstrated"], "evidence": f"stewardship:{active['id']}"})
                practice["history"].append({"tick": tick, "status": "completed", "demonstrated": worker_record["demonstrated"], "evidence": practice["evidence"]})
                _remember_consequence(state, tick, f"instruction-recorded:{worker['id']}:environmental_stewardship:practice-required", f"competency-demonstrated:{worker['id']}:environmental_stewardship:{worker_record['demonstrated']}", [worker["id"], active["supervisor"], inspector["id"]])
                emitted.append({"type": "supervised_practice_completed", "actor_id": worker["id"], "payload": {"practice_order_id": practice["id"], "work_order_id": active["id"], "demonstrated": worker_record["demonstrated"]}})
            inspector_record = inspector.setdefault("competency_records", {}).setdefault("ecological_inspection", {"demonstrated": 0.0, "provenance": []})
            inspector_record["demonstrated"] = max(inspector_record["demonstrated"], 0.7)
            inspector_record["provenance"].append(f"stewardship-inspection:{active['id']}")
            inspector["competencies"]["ecological_inspection"] = inspector_record["demonstrated"]
            lesson = _create_instruction_opportunity(state, tick, "environmental_stewardship", worker["id"], f"stewardship:{active['id']}", active["id"])
            if lesson:
                emitted.append({"type": "teaching_proposed", "actor_id": worker["id"], "payload": dict(lesson)})
            _remember_consequence(state, tick, f"local-stock-restored:{site['id']}:+{active['restored_amount']}", f"stewardship-completed:{active['id']}", [worker["id"], inspector["id"], "settlement"])
            emitted.append({"type": "stewardship_completed", "actor_id": worker["id"], "payload": {"order_id": active["id"], "site_id": site["id"]}})
    return emitted


def _create_instruction_opportunity(state: Dict[str, Any], tick: int, domain: str, teacher_id: str,
                                    source_evidence: str, source_order_id: str) -> Optional[Dict[str, Any]]:
    """Project verified work into a reusable, consented instruction action."""
    teacher = _shared_entity(state, teacher_id)
    if not teacher or _shared_competence(teacher, domain) < 0.15:
        return None
    provenance = teacher.get("competency_records", {}).get(domain, {}).get("provenance", [])
    if source_evidence not in provenance:
        return None
    if any(order.get("source_evidence") == source_evidence for order in state["education"]["teaching_orders"]):
        return None
    obligated = {(order["learner"], order["domain"]) for order in state["education"]["practice_orders"] if order["status"] not in {"completed", "cancelled"}}
    candidates = [npc for npc in state["npcs"].values() if npc["id"] != teacher_id and _shared_competence(npc, domain) < 0.1 and (npc["id"], domain) not in obligated]
    if not candidates:
        return None
    learner = min(candidates, key=lambda npc: (_shared_competence(npc, domain), npc["id"] != "rae", npc["id"]))
    lesson_id = f"teaching-{len(state['education']['teaching_orders']) + 1}"
    lesson = {
        "id": lesson_id, "domain": domain, "status": "proposed", "created_tick": tick,
        "instructor": teacher_id, "learner": learner["id"], "source_order_id": source_order_id,
        "source_evidence": source_evidence, "required_ticks": 4,
        "history": [{"tick": tick, "status": "proposed"}],
        "consent": {teacher_id: "proposed", learner["id"]: "pending"}, "canonical_action_id": lesson_id,
    }
    state["education"]["teaching_orders"].append(lesson)
    instruction_record = {
        "id": lesson_id, "definition": {
            "action_type": "conduct_instruction_session", "execution_model": "instruction_session",
            "requirements": {"materials": {}, "tools": {}, "station": "instruction_table", "energy": 1,
                             "competence_domain": domain, "minimum_competence": 0.15,
                             "perception_channels": ["language", "records"], "duration_ticks": lesson["required_ticks"]},
            "output_item": "instruction_record", "output_amount": 1, "provisional_cu_milli": 0,
            "verification_tolerance": 0.0, "verification_threshold": 0.0,
            "verifier_competence_domain": None, "minimum_verifier_competence": 0.0,
        },
        "actor_id": teacher_id, "actor_kind": "human" if teacher_id in state["players"] else "ai",
        "intent": f"teach {domain} from reproduced evidence", "target_id": learner["id"],
        "location": "meeting_hall", "observations": [source_evidence], "state": "proposed",
        "proposed_tick": tick, "ledger_event_ids": [], "samples": [], "output": {},
        "failure_reason": None, "verifier_id": None, "autonomous_origin": False,
    }
    state["shared_actions"]["records"][lesson_id] = instruction_record
    _append_shared_action_event(state, instruction_record, "proposed", teacher_id, evidence=[{"kind": "verified_source_record", "id": source_evidence}])
    _remember_consequence(state, tick, f"verified-work:{source_evidence}", f"teaching-order:{lesson_id}", [teacher_id, learner["id"]])
    return lesson


def _process_teaching(state: Dict[str, Any], tick: int) -> list[Dict[str, Any]]:
    """Transfer bounded knowledge while reserving expertise for later practice."""
    order = next((item for item in state["education"]["teaching_orders"] if item["status"] not in {"completed", "cancelled"}), None)
    if not order:
        return []
    instructor = _shared_entity(state, order["instructor"])
    learner = _shared_entity(state, order["learner"])
    record = state["shared_actions"]["records"].get(order.get("canonical_action_id"))
    if not record:
        order["status"] = "cancelled"
        order.setdefault("history", []).append({"tick": tick, "status": "cancelled", "reason": "canonical instruction record missing"})
        return [{"type": "teaching_cancelled", "actor_id": instructor["id"], "payload": {"order_id": order["id"], "reason": "canonical instruction record missing"}}]
    emitted: list[Dict[str, Any]] = []
    def participation_capacity(entity):
        return min(entity.get("needs", {}).get(name, 100) for name in ("nutrition", "hydration", "rest")) if "needs" in entity else entity.get("energy", 100)
    safe = min(participation_capacity(instructor), participation_capacity(learner)) >= 24
    if not safe:
        if order["status"] != "paused_needs":
            order["resume_status"] = order["status"]
            order["status"] = "paused_needs"
            order["history"].append({"tick": tick, "status": "paused_needs"})
            emitted.append({"type": "teaching_paused", "actor_id": instructor["id"], "payload": {"order_id": order["id"], "reason": "survival need below safe teaching threshold"}})
        return emitted
    if order["status"] == "paused_needs":
        order["status"] = order.pop("resume_status", "proposed")
        order["history"].append({"tick": tick, "status": "resumed"})
    meeting = state["places"]["meeting_hall"]["location"]
    if order["status"] == "proposed":
        if tick <= order["created_tick"]:
            return emitted
        if instructor["id"] in state["players"]:
            return emitted
        result = apply_shared_action_command(state, instructor["id"], {"operation": "instructor_accept", "shared_action_id": record["id"]})
        if not result.get("accepted"):
            return [{"type": "teaching_blocked", "actor_id": instructor["id"], "payload": {"order_id": order["id"], "reason": result.get("reason")}}]
        emitted.append({"type": "teaching_consent_requested", "actor_id": instructor["id"], "payload": {"order_id": order["id"], "learner": learner["id"]}})
        return emitted
    if order["status"] == "awaiting_learner_consent":
        source_visible = order["source_evidence"] in instructor.get("competency_records", {}).get(order["domain"], {}).get("provenance", [])
        if not source_visible:
            order["status"] = "blocked_evidence"
            order["history"].append({"tick": tick, "status": order["status"], "reason": "instructor lacks source provenance"})
            return [{"type": "teaching_blocked", "actor_id": instructor["id"], "payload": {"order_id": order["id"], "reason": "instructor lacks source provenance"}}]
        order["consent_decision"] = {"tick": tick, "basis": "survival needs safe; verified source is available; learner has an unresolved competence gap"}
        result = apply_shared_action_command(state, learner["id"], {"operation": "learner_accept", "shared_action_id": record["id"]})
        if not result.get("accepted"):
            return [{"type": "teaching_blocked", "actor_id": learner["id"], "payload": {"order_id": order["id"], "reason": result.get("reason")}}]
        order["history"][-1]["decision_basis"] = order["consent_decision"]["basis"]
        emitted.append({"type": "teaching_accepted", "actor_id": learner["id"], "payload": {"order_id": order["id"], "decision_basis": order["consent_decision"]["basis"]}})
        return emitted
    if order["status"] in {"accepted", "blocked_access"}:
        for npc in (instructor, learner):
            if npc["id"] in state["npcs"]:
                npc["location"] = _move_for_legacy(state, npc, meeting, owner_action_id=record["id"])
            if npc["location"] == meeting:
                npc["current_region"] = "settlement"
        if instructor["location"] != meeting or learner["location"] != meeting:
            emitted.append({"type": "teaching_movement", "actor_id": learner["id"], "payload": {"order_id": order["id"], "instructor": list(instructor["location"]), "learner": list(learner["location"])}})
            return emitted
        result = apply_shared_action_command(state, instructor["id"], {"operation": "reserve", "shared_action_id": record["id"]})
        if not result.get("accepted"):
            order["status"] = "blocked_access"
            order["history"].append({"tick": tick, "status": order["status"], "reason": result.get("reason")})
            return [{"type": "teaching_blocked", "actor_id": instructor["id"], "payload": {"order_id": order["id"], "reason": result.get("reason")}}]
        order["status"] = "instruction_ready"
        order["history"].append({"tick": tick, "status": order["status"], "location": list(meeting)})
        return [{"type": "teaching_resources_reserved", "actor_id": instructor["id"], "payload": {"order_id": order["id"], "station": "instruction_table"}}]
    if order["status"] == "instruction_ready":
        result = apply_shared_action_command(state, instructor["id"], {"operation": "execute", "shared_action_id": record["id"], "samples": [{"source_event_id": order["source_evidence"], "claim": f"Methods and limits demonstrated for {order['domain']}"}]})
        if not result.get("accepted"):
            return [{"type": "teaching_blocked", "actor_id": instructor["id"], "payload": {"order_id": order["id"], "reason": result.get("reason")}}]
        order["status"] = "instruction"
        order["started_tick"] = tick
        order["demonstration_due_tick"] = record["execution_due_tick"]
        order["history"].append({"tick": tick, "status": "instruction", "location": list(meeting), "source_evidence": order["source_evidence"]})
        _remember_consequence(state, tick, f"teaching-order:{order['id']}", f"instruction-started:{order['domain']}:{order['learner']}", [instructor["id"], learner["id"]])
        emitted.append({"type": "teaching_started", "actor_id": instructor["id"], "payload": dict(order)})
        return emitted
    if order["status"] == "instruction" and record["state"] == "submitted":
        result = apply_shared_action_command(state, learner["id"], {"operation": "verify", "shared_action_id": record["id"]})
        if result.get("accepted"):
            order["status"] = "acknowledged"
            order["history"].append({"tick": tick, "status": order["status"], "actor": learner["id"]})
            emitted.append({"type": "teaching_acknowledged", "actor_id": learner["id"], "payload": {"order_id": order["id"]}})
        return emitted
    if order["status"] == "acknowledged" and record["state"] == "verified":
        result = apply_shared_action_command(state, learner["id"], {"operation": "commission", "shared_action_id": record["id"]})
        if not result.get("accepted"):
            return [{"type": "teaching_blocked", "actor_id": learner["id"], "payload": {"order_id": order["id"], "reason": result.get("reason")}}]
        learning = record["output"]["learning"]
        order["status"] = "completed"
        order["completed_tick"] = tick
        order["demonstration"] = {"before": learning["demonstrated_before"], "after": learning["demonstrated_after"], "passed": False}
        order["learning"] = copy.deepcopy(learning)
        order["history"].append({"tick": tick, "status": "instruction_completed", "learning": copy.deepcopy(learning)})
        practice = {"id": f"practice-{len(state['education']['practice_orders']) + 1}", "status": "awaiting_real_work", "domain": order["domain"], "learner": learner["id"], "supervisor": instructor["id"], "source_instruction_id": order["id"], "created_tick": tick, "history": [{"tick": tick, "status": "awaiting_real_work"}]}
        state["education"]["practice_orders"].append(practice)
        _remember_consequence(state, tick, f"instruction-started:{order['domain']}:{learner['id']}", f"instruction-recorded:{learner['id']}:{order['domain']}:practice-required", [instructor["id"], learner["id"]])
        emitted.append({"type": "instruction_completed", "actor_id": learner["id"], "payload": {"order_id": order["id"], "learning": learning, "practice_order_id": practice["id"]}})
    return emitted


def evaluate_lever_pump(specification: Dict[str, Any]) -> Dict[str, float]:
    """Evaluate a simple lever-driven piston pump using declared SI dimensions."""
    effort_arm = float(specification["effort_arm_m"])
    load_arm = float(specification["load_arm_m"])
    diameter = float(specification["piston_diameter_m"])
    stroke = float(specification["stroke_m"])
    efficiency = float(specification["efficiency"])
    values = [effort_arm, load_arm, diameter, stroke, efficiency]
    if not all(math.isfinite(value) and value > 0 for value in values):
        raise ValueError("all dimensions and efficiency must be finite positive values")
    if not (0.3 <= efficiency <= 0.95):
        raise ValueError("declared efficiency must be between 0.30 and 0.95")
    mechanical_advantage = effort_arm / load_arm
    swept_volume_m3 = math.pi * (diameter / 2) ** 2 * stroke
    delivered_liters = swept_volume_m3 * 1000 * efficiency
    if not (1.2 <= mechanical_advantage <= 8.0):
        raise ValueError("lever mechanical advantage must be between 1.2 and 8.0")
    if not (0.2 <= delivered_liters <= 8.0):
        raise ValueError("predicted delivered volume must be between 0.2 and 8.0 liters per stroke")
    return {
        "mechanical_advantage": round(mechanical_advantage, 4),
        "swept_volume_m3": round(swept_volume_m3, 6),
        "predicted_liters_per_stroke": round(delivered_liters, 3),
        "declared_efficiency": round(efficiency, 4),
    }


def _process_research(state: Dict[str, Any], tick: int) -> list[Dict[str, Any]]:
    if tick % 6 != 0:
        return []
    emitted: list[Dict[str, Any]] = []
    for design in state["research"]["designs"]:
        if design["status"] in {"rejected", "validated"}:
            continue
        if design["status"] == "proposed":
            try:
                prediction = evaluate_lever_pump(design["specification"])
            except (KeyError, TypeError, ValueError) as exc:
                design["status"] = "rejected"
                design["review"] = {"tick": tick, "reviewer": "mira", "accepted": False, "reason": str(exc)}
                state["research"]["reviews"].append({"design_id": design["id"], **design["review"]})
                state["npcs"]["mira"]["memories"].append({"tick": tick, "kind": "completed_work", "text": f"Rejected {design['id']}: {exc}."})
                emitted.append({"type": "design_rejected", "actor_id": "mira", "payload": {"id": design["id"], "reason": str(exc)}})
                continue
            design["prediction"] = prediction
            design["status"] = "reviewed"
            design["review"] = {"tick": tick, "reviewer": "mira", "accepted": True, "units": "SI", "prediction": prediction}
            state["research"]["reviews"].append({"design_id": design["id"], **design["review"]})
            _remember_consequence(state, tick, f"design-proposal:{design['id']}", f"peer-review:{design['id']}", [design["proposer"], "mira"])
            emitted.append({"type": "design_peer_reviewed", "actor_id": "mira", "payload": {"id": design["id"], "prediction": prediction}})
        elif design["status"] == "reviewed":
            required = design["prototype_inputs"]
            missing = {name: amount - state["resources"].get(name, 0) for name, amount in required.items() if state["resources"].get(name, 0) < amount}
            if missing:
                design["blocker"] = {"tick": tick, "reason": "prototype materials unavailable", "missing": missing}
                state["npcs"]["ada"]["intention"] = f"source prototype materials for {design['id']}"
                state["npcs"]["ada"]["reason"] = f"Research is blocked by {missing}."
                emitted.append({"type": "design_blocked", "actor_id": "ada", "payload": {"id": design["id"], "missing": missing}})
                continue
            for material, amount in required.items():
                state["resources"][material] -= amount
            design["status"] = "prototype_built"
            design["prototype_tick"] = tick
            design["prototype_id"] = f"prototype-{design['id']}"
            design.pop("blocker", None)
            _evidence(state, tick, f"prototype assembled for {design['id']}", ["ada", design["proposer"]], required, ["saw", "wrench", "caliper"], design["prediction"], "mira", [f"design:{design['id']}"], ["dimensional inspection"])
            _remember_consequence(state, tick, f"peer-review:{design['id']}", f"prototype:{design['prototype_id']}", ["ada", design["proposer"]])
            emitted.append({"type": "prototype_built", "actor_id": "ada", "payload": {"id": design["id"], "prototype_id": design["prototype_id"], "inputs": required}})
        elif design["status"] == "prototype_built":
            predicted = design["prediction"]["predicted_liters_per_stroke"]
            observed = round(predicted * 0.92, 3)
            error = round(abs(observed - predicted) / predicted, 4)
            design["test_result"] = {"tick": tick, "tester": "mira", "observed_liters_per_stroke": observed, "relative_error": error, "passed": error <= 0.15}
            design["status"] = "tested" if design["test_result"]["passed"] else "rejected"
            _evidence(state, tick, f"prototype flow test for {design['id']}", ["mira"], {"prototype": design["prototype_id"]}, ["graduated vessel", "timer", "caliper"], design["test_result"], "mira", [f"prototype:{design['prototype_id']}"], ["flow test"])
            emitted.append({"type": "prototype_tested", "actor_id": "mira", "payload": {"id": design["id"], **design["test_result"]}})
        elif design["status"] == "tested":
            reproduction_inputs = {name: max(1, amount // 2) for name, amount in design["prototype_inputs"].items()}
            missing = {name: amount - state["resources"].get(name, 0) for name, amount in reproduction_inputs.items() if state["resources"].get(name, 0) < amount}
            if missing:
                emitted.append({"type": "reproduction_blocked", "actor_id": "emil", "payload": {"id": design["id"], "missing": missing}})
                continue
            for material, amount in reproduction_inputs.items():
                state["resources"][material] -= amount
            observed = round(design["prediction"]["predicted_liters_per_stroke"] * 0.95, 3)
            relative_error = round(abs(observed - design["prediction"]["predicted_liters_per_stroke"]) / design["prediction"]["predicted_liters_per_stroke"], 4)
            reproduction = {"tick": tick, "design_id": design["id"], "reproducer": "emil", "observed_liters_per_stroke": observed, "relative_error": relative_error, "passed": relative_error <= 0.15}
            state["research"]["reproductions"].append(reproduction)
            if not reproduction["passed"]:
                design["status"] = "rejected"
                emitted.append({"type": "reproduction_failed", "actor_id": "emil", "payload": reproduction})
                continue
            design["status"] = "validated"
            design["validated_tick"] = tick
            design["available_units"] = 1
            state["technology"]["validated_designs"].append(design["id"])
            state["technology"]["tool_catalog"][design["id"]] = {
                "id": design["id"], "name": design["name"], "archetype": design["archetype"],
                "prediction": dict(design["prediction"]), "validated_tick": tick, "available_units": 1,
                "provenance": [f"design:{design['id']}", f"prototype:{design['prototype_id']}", f"reproduction:{design['id']}:{tick}"],
            }
            _evidence(state, tick, f"independent reproduction of {design['id']}", ["emil"], reproduction_inputs, ["wrench", "caliper", "graduated vessel"], reproduction, "mira", [f"prototype:{design['prototype_id']}"], ["independent reproduction"])
            for actor, kind, amount in [(design["proposer"], "validated engineering design", 16.0), ("mira", "peer review and prototype test", 8.0), ("ada", "precision prototype assembly", 9.0), ("emil", "independent research reproduction", 10.0)]:
                _provisional_claim(state, tick, actor, kind, amount, f"validated-design:{design['id']}")
            _remember_consequence(state, tick, f"prototype-test:{design['id']}", f"validated-technology:{design['id']}", [design["proposer"], "mira", "ada", "emil"])
            emitted.append({"type": "technology_validated", "actor_id": "emil", "payload": {"id": design["id"], "reproduction": reproduction}})
    return emitted


def project_committed_event(state: Dict[str, Any], event: sqlite3.Row) -> Dict[str, Any]:
    """Deterministically turn committed player information into future action."""
    if event["event_type"] not in {"player_action", "owner_directive"}:
        return {"changed": False, "events": []}
    payload = json.loads(event["payload_json"])
    if not payload.get("accepted"):
        return {"changed": False, "events": []}
    reaction_id = f"reaction-{event['sequence']}"
    causality = state["causality"]
    if any(item["id"] == reaction_id for item in causality["pending_reactions"] + causality["completed_reactions"]):
        return {"changed": False, "events": []}
    actor_id = event["actor_id"]
    player = state["players"].get(actor_id, {})
    location = player.get("location", [8, 5])
    if player.get("current_region", "settlement") != "settlement":
        return {"changed": False, "events": []}
    observer = min(
        state["npcs"].values(),
        key=lambda npc: (_distance(npc["location"], location), npc["id"]),
    )
    action_type = payload.get("type", "world action")
    perception = {
        "id": f"perception-{event['sequence']}", "source_sequence": event["sequence"],
        "tick": event["tick"], "observer": observer["id"], "actor": actor_id,
        "action": action_type, "physical": bool(payload.get("physical_change")),
    }
    causality["perceptions"].append(perception)
    causality["perceptions"] = causality["perceptions"][-500:]
    observer["memories"].append({
        "tick": event["tick"], "kind": "causal_observation", "source_sequence": event["sequence"],
        "text": f"Observed {actor_id} perform {action_type}; its consequences require assessment.",
    })
    reaction = {
        "id": reaction_id, "source_sequence": event["sequence"], "status": "pending",
        "observer": observer["id"], "actor": actor_id, "action": action_type,
        "physical": bool(payload.get("physical_change")), "planned_tick": state["clock"]["tick"],
        "execute_after_tick": state["clock"]["tick"] + 1,
    }
    if action_type == "owner_directive":
        reaction["directive"] = payload.get("directive", {})
    causality["pending_reactions"].append(reaction)
    observer["intention"] = f"assess {action_type} by {actor_id}"
    observer["reason"] = f"Committed world event {event['sequence']} changed shared history."
    return {
        "changed": True,
        "events": [{"type": "reaction_planned", "actor_id": observer["id"], "payload": dict(reaction)}],
    }


def _execute_pending_reactions(state: Dict[str, Any], tick: int) -> list[Dict[str, Any]]:
    emitted = []
    pending = []
    for reaction in state["causality"]["pending_reactions"]:
        if reaction["execute_after_tick"] > tick:
            pending.append(reaction)
            continue
        observer = state["npcs"][reaction["observer"]]
        actor = state["players"].get(reaction["actor"])
        origin = list(observer["location"])
        if reaction["physical"] and actor:
            observer["location"] = _move_for_legacy(state, observer, actor["location"])
        reaction["status"] = "completed"
        reaction["completed_tick"] = tick
        reaction["result"] = {"from": origin, "to": list(observer["location"]), "recorded": True}
        if reaction["action"] == "owner_directive":
            directive = reaction.get("directive", {})
            record = next((item for item in state["institutions"]["governance"]["owner_directives"] if item["id"] == directive.get("id")), None)
            priority = directive.get("priority")
            pressures = _settlement_pressures(state)
            if record and priority in INITIATIVE_BLUEPRINTS:
                record["status"] = "adopted"
                record["reviewed_tick"] = tick
                record["reviewed_by"] = observer["id"]
                record["decision_reason"] = f"Council evidence measured {priority} pressure at {pressures[priority]:.2f}; the proposal entered the public agenda."
                state["institutions"]["council"]["endorsements"][f"owner-directive:{record['id']}"] = priority
            elif record:
                record["status"] = "rejected"
                record["reviewed_tick"] = tick
                record["reviewed_by"] = observer["id"]
                record["decision_reason"] = "The proposal did not identify a measurable settlement priority."
            reaction["result"]["institutional_decision"] = record["status"] if record else "unresolved"
            reaction["result"]["directive_id"] = directive.get("id")
        state["causality"]["completed_reactions"].append(reaction)
        observer["memories"].append({
            "tick": tick, "kind": "completed_reaction", "source_sequence": reaction["source_sequence"],
            "text": f"Assessed {reaction['action']} by {reaction['actor']} and recorded the result.",
        })
        state["institutions"]["council"]["knowledge"].append({
            "tick": tick, "kind": "causal_reaction", "reaction_id": reaction["id"],
            "source_sequence": reaction["source_sequence"], "observer": observer["id"],
            "actor": reaction["actor"], "action": reaction["action"],
        })
        _remember_consequence(state, tick, f"world-event:{reaction['source_sequence']}", f"decision:{reaction['id']}", [observer["id"], reaction["actor"]])
        emitted.append({"type": "reaction_completed", "actor_id": observer["id"], "payload": dict(reaction)})
        if reaction["action"] == "owner_directive":
            emitted.append({"type": "owner_directive_reviewed", "actor_id": observer["id"], "payload": dict(reaction["result"])})
    state["causality"]["pending_reactions"] = pending
    state["causality"]["completed_reactions"] = state["causality"]["completed_reactions"][-500:]
    return emitted


def _settlement_pressures(state: Dict[str, Any]) -> Dict[str, float]:
    population = max(1, len(state["npcs"]))
    hungry = sum(npc["needs"]["nutrition"] < 40 for npc in state["npcs"].values())
    thirsty = sum(npc["needs"]["hydration"] < 40 for npc in state["npcs"].values())
    pressures = {
        "sanitation": 95.0 if state["places"]["sanitation"].get("status") != "operational" else 4.0,
        "storage": (75.0 if state["places"]["dry_storage"].get("status") != "operational" else 5.0) + max(0, 50 - state["food"]["spoilage_clock"]),
        "water": (100 - state["places"]["water_source"].get("dependability", 0) * 100) + thirsty / population * 70 + max(0, population * 2 - state["resources"]["tested_water"]),
        "food": hungry / population * 80 + max(0, population - state["resources"]["safe_meals"]) * 3,
    }
    for priority in state["institutions"]["council"].get("endorsements", {}).values():
        if priority in pressures:
            pressures[priority] += 60
    return pressures


def _observe_and_decide(state: Dict[str, Any], tick: int) -> list[Dict[str, Any]]:
    council = state["institutions"]["council"]
    pressures = _settlement_pressures(state)
    measured_pressures = dict(pressures)
    for priority, public_pressure in council.get("public_pressure", {}).items():
        if priority in pressures:
            pressures[priority] = round(pressures[priority] + public_pressure, 2)
    prior_changes = [item["id"] for item in council["completed_initiatives"][-4:]]
    observation = {
        "tick": tick, "kind": "settlement_pressures",
        "facts": {key: round(value, 2) for key, value in pressures.items()},
        "measured_facts": {key: round(value, 2) for key, value in measured_pressures.items()},
        "public_pressure": dict(council.get("public_pressure", {})),
        "sources": ["needs", "resources", "facilities", "witnessed_public_discourse"] + [f"completed-initiative:{item}" for item in prior_changes],
        "prior_changes": prior_changes,
    }
    council["knowledge"].append(observation)
    council["knowledge"] = council["knowledge"][-120:]
    ranked = sorted(pressures, key=lambda key: (-pressures[key], key))
    council["agenda"] = [{"priority": key, "pressure": round(pressures[key], 2)} for key in ranked]
    emitted = [{"type": "institution_observed", "actor_id": "council", "payload": observation}]
    if council["current_initiative"] is None:
        priority = ranked[0]
        sequence = len(council["completed_initiatives"]) + 1
        supporting_endorsements = sorted(actor for actor, endorsed in council["endorsements"].items() if endorsed == priority)
        causal_sources = [f"observation:council:{tick}"] + supporting_endorsements
        required_evidence: list[str] = []
        for endorsement in supporting_endorsements:
            if not endorsement.startswith("owner-directive:"):
                continue
            directive_id = endorsement.split(":", 1)[1]
            record = next((item for item in state["institutions"]["governance"]["owner_directives"] if item["id"] == directive_id), None)
            for requirement in (record or {}).get("evidence_required", []):
                normalized = _evidence_tag(requirement)
                if normalized and normalized not in required_evidence:
                    required_evidence.append(normalized)
        support_text = f" Supported by {', '.join(supporting_endorsements)}." if supporting_endorsements else ""
        council["current_initiative"] = {
            "id": f"civic-{sequence}-{priority}", "priority": priority, "status": "proposed", "created_tick": tick,
            "reason": f"Council evidence ranked {priority} pressure at {pressures[priority]:.2f}.{support_text}", "attempts": 0,
            "causal_sources": causal_sources,
            "required_evidence": required_evidence,
        }
        for endorsement in supporting_endorsements:
            if not endorsement.startswith("owner-directive:"):
                continue
            directive_id = endorsement.split(":", 1)[1]
            record = next((item for item in state["institutions"]["governance"]["owner_directives"] if item["id"] == directive_id), None)
            if record:
                record["status"] = "commissioned"
                record["initiative_id"] = council["current_initiative"]["id"]
                record["commissioned_tick"] = tick
        council["endorsements"] = {actor: endorsed for actor, endorsed in council["endorsements"].items() if endorsed != priority}
        council["public_pressure"][priority] = max(0.0, council.get("public_pressure", {}).get(priority, 0.0) - 20.0)
        _remember_consequence(state, tick, f"observation:council:{tick}", f"initiative:{council['current_initiative']['id']}", ["council"])
        for endorsement in supporting_endorsements:
            _remember_consequence(state, tick, endorsement, f"initiative:{council['current_initiative']['id']}", ["council"])
        emitted.append({"type": "initiative_proposed", "actor_id": "council", "payload": dict(council["current_initiative"])})
    return emitted


def _advance_civic_initiative(state: Dict[str, Any], tick: int) -> list[Dict[str, Any]]:
    council = state["institutions"]["council"]
    initiative = council.get("current_initiative")
    if not initiative:
        return []
    blueprint = INITIATIVE_BLUEPRINTS[initiative["priority"]]
    emitted: list[Dict[str, Any]] = []
    initiative["attempts"] += 1
    if initiative["status"] == "proposed":
        initiative["status"] = "accepted"
        initiative["accepted_tick"] = tick
        emitted.append({"type": "initiative_accepted", "actor_id": "council", "payload": {"id": initiative["id"], "reason": initiative["reason"]}})
    elif initiative["status"] == "accepted":
        missing = {name: amount - state["resources"].get(name, 0) for name, amount in blueprint["inputs"].items() if state["resources"].get(name, 0) < amount}
        if missing:
            failure = {"tick": tick, "action": initiative["id"], "reason": "required inputs unavailable", "missing": missing, "recovered": False}
            state["failures"].append(failure)
            initiative["blocker"] = failure
            _remember_consequence(state, tick, f"shortage:{','.join(sorted(missing))}", f"blocked:{initiative['id']}", blueprint["workers"])
            emitted.append({"type": "initiative_blocked", "actor_id": blueprint["workers"][0], "payload": failure})
            gathered: Dict[str, int] = {}
            for name, shortage in missing.items():
                available = state["environment"]["stocks"].get(name, 0)
                amount = min(shortage, available, 3)
                if amount > 0:
                    state["environment"]["stocks"][name] -= amount
                    state["resources"][name] = state["resources"].get(name, 0) + amount
                    gathered[name] = amount
            if gathered:
                extraction = {"tick": tick, "initiative": initiative["id"], "actor": "orin", "outputs": gathered, "method": "surveyed local gathering", "remaining_stocks": {name: state["environment"]["stocks"].get(name, 0) for name in gathered}}
                state["environment"]["extraction_history"].append(extraction)
                _evidence(state, tick, "shortage-driven material procurement", ["orin", "rae"], {}, ["handcart", "pick", "measuring_line"], gathered, "dev")
                _remember_consequence(state, tick, f"blocked:{initiative['id']}", f"procurement:{tick}", ["orin", "rae", "dev"])
                emitted.append({"type": "procurement_performed", "actor_id": "orin", "payload": extraction})
            return emitted
        for name, amount in blueprint["inputs"].items():
            state["resources"][name] -= amount
        initiative["status"] = "supplied"
        initiative["inputs"] = dict(blueprint["inputs"])
        if initiative.pop("blocker", None):
            for failure in reversed(state["failures"]):
                if failure["action"] == initiative["id"] and not failure["recovered"]:
                    failure["recovered"], failure["recovered_tick"] = True, tick
                    break
        emitted.append({"type": "initiative_supplied", "actor_id": "dev", "payload": {"id": initiative["id"], "inputs": initiative["inputs"]}})
    elif initiative["status"] == "supplied":
        initiative["status"] = "performed"
        initiative["performed_tick"] = tick
        initiative["evidence_tags"] = [_evidence_tag(item) for item in INITIATIVE_EVIDENCE_TAGS[initiative["priority"]]]
        _evidence(state, tick, f"{initiative['priority']} initiative performed", blueprint["workers"], initiative["inputs"], ["handcart", "hammer", "measuring_line"], {"completion": 1.0, "uncertainty": 0.06}, None, initiative.get("causal_sources"), initiative["evidence_tags"])
        emitted.append({"type": "initiative_performed", "actor_id": blueprint["workers"][0], "payload": {"id": initiative["id"], "workers": blueprint["workers"]}})
    elif initiative["status"] == "performed":
        missing_evidence = [item for item in initiative.get("required_evidence", []) if item not in initiative.get("evidence_tags", [])]
        if missing_evidence and not initiative.get("evidence_blocker"):
            failure = {"tick": tick, "action": initiative["id"], "reason": "required inspection evidence unavailable", "missing_evidence": missing_evidence, "recovered": False}
            state["failures"].append(failure)
            initiative["evidence_blocker"] = failure
            inspector = state["npcs"][blueprint["inspector"]]
            inspector["intention"] = f"collect evidence for {initiative['id']}"
            inspector["reason"] = f"Inspection requires: {', '.join(missing_evidence)}."
            _remember_consequence(state, tick, f"missing-evidence:{initiative['id']}", f"inspection-blocked:{initiative['id']}", [blueprint["inspector"]])
            emitted.append({"type": "inspection_rejected", "actor_id": blueprint["inspector"], "payload": dict(failure)})
            return emitted
        if missing_evidence:
            initiative["evidence_tags"].extend(item for item in missing_evidence if item not in initiative["evidence_tags"])
            _evidence(state, tick, f"supplemental evidence for {initiative['id']}", [blueprint["inspector"]], {}, ["measurement kit", "field notebook"], {"requirements_observed": len(missing_evidence)}, blueprint["inspector"], initiative.get("causal_sources"), missing_evidence)
            for failure in reversed(state["failures"]):
                if failure["action"] == initiative["id"] and failure["reason"] == "required inspection evidence unavailable" and not failure["recovered"]:
                    failure["recovered"] = True
                    failure["recovered_tick"] = tick
                    break
            initiative.pop("evidence_blocker", None)
            _remember_consequence(state, tick, f"inspection-blocked:{initiative['id']}", f"evidence-collected:{initiative['id']}", [blueprint["inspector"]])
            emitted.append({"type": "initiative_evidence_collected", "actor_id": blueprint["inspector"], "payload": {"id": initiative["id"], "evidence_tags": missing_evidence}})
            return emitted
        initiative["status"] = "completed"
        initiative["completed_tick"] = tick
        state["evidence"][-1]["inspector"] = blueprint["inspector"]
        priority = initiative["priority"]
        if priority == "sanitation":
            state["places"]["sanitation"]["status"] = "operational"
            state["places"]["water_source"]["dependability"] = min(1, state["places"]["water_source"].get("dependability", 0) + 0.12)
        elif priority == "storage":
            state["places"]["dry_storage"]["status"] = "operational"
            state["food"]["storage_quality"] = min(1, state["food"]["storage_quality"] + 0.35)
            state["food"]["spoilage_clock"] += 48
        elif priority == "water":
            state["places"]["water_source"]["status"] = "operational"
            state["places"]["water_source"]["dependability"] = min(1, state["places"]["water_source"].get("dependability", 0) + 0.22)
            state["resources"]["tested_water"] += 12
        elif priority == "food":
            state["resources"]["safe_meals"] += 14
            state["food"]["meal_history"].append({"tick": tick, "name": "Council provision meal", "portions": 14, "safety": 0.84, "inputs": initiative["inputs"]})
        for actor in blueprint["workers"]:
            state["npcs"][actor]["memories"].append({"tick": tick, "kind": "completed_work", "text": f"Completed {initiative['id']}; its effects entered settlement history."})
            _provisional_claim(state, tick, actor, f"verified {priority} public work", 8.0, f"initiative:{initiative['id']}")
        council["completed_initiatives"].append(dict(initiative))
        for source in initiative.get("causal_sources", []):
            if not source.startswith("owner-directive:"):
                continue
            directive_id = source.split(":", 1)[1]
            record = next((item for item in state["institutions"]["governance"]["owner_directives"] if item["id"] == directive_id), None)
            if record:
                record["status"] = "fulfilled"
                record["fulfilled_tick"] = tick
                record["world_change"] = priority
        council["knowledge"].append({
            "tick": tick, "kind": "verified_world_change", "initiative_id": initiative["id"],
            "priority": priority, "causal_sources": list(initiative.get("causal_sources", [])),
            "postconditions": {
                "place": blueprint["place"], "status": state["places"][blueprint["place"]].get("status"),
                "water_dependability": state["places"]["water_source"].get("dependability"),
                "tested_water": state["resources"].get("tested_water"), "safe_meals": state["resources"].get("safe_meals"),
                "storage_quality": state["food"].get("storage_quality"),
            },
        })
        council["current_initiative"] = None
        _remember_consequence(state, tick, f"initiative:{initiative['id']}", f"world-change:{priority}", blueprint["workers"] + [blueprint["inspector"]])
        emitted.append({"type": "initiative_completed", "actor_id": blueprint["inspector"], "payload": {"id": initiative["id"], "changed": priority, "causal_sources": list(initiative.get("causal_sources", []))}})
    return emitted


def _distance(first: list[int], second: list[int]) -> int:
    return abs(first[0] - second[0]) + abs(first[1] - second[1])


def _move_toward(origin: list[int], target: list[int]) -> list[int]:
    moved = list(origin)
    if moved[0] != target[0]:
        moved[0] += 1 if target[0] > moved[0] else -1
    elif moved[1] != target[1]:
        moved[1] += 1 if target[1] > moved[1] else -1
    return moved


def _relationship(state: Dict[str, Any], npc_id: str, actor_id: str) -> Dict[str, Any]:
    return state["npcs"][npc_id]["relationships"].setdefault(actor_id, {"trust": 0.5, "history": []})


def _adjust_trust(state: Dict[str, Any], npc_id: str, actor_id: str, change: float, cause: str, tick: int) -> float:
    relationship = _relationship(state, npc_id, actor_id)
    before = float(relationship["trust"])
    after = round(max(0.0, min(1.0, before + change)), 4)
    relationship["trust"] = after
    relationship["history"].append({"tick": tick, "cause": cause, "before": before, "change": round(after - before, 4), "after": after})
    relationship["history"] = relationship["history"][-100:]
    return after


def _process_justice(state: Dict[str, Any], tick: int) -> list[Dict[str, Any]]:
    """Turn private observations into reports, findings, and recoverable consequences."""
    justice = state["institutions"]["justice"]
    emitted: list[Dict[str, Any]] = []
    reported_conduct = {report["conduct_id"] for report in justice["reports"]}
    for npc in state["npcs"].values():
        for memory in npc["memories"]:
            if memory.get("kind") != "witnessed_conduct" or memory.get("reported") or tick < memory["tick"] + 2:
                continue
            memory["reported"] = True
            report = {
                "id": f"report-{len(justice['reports']) + 1}", "conduct_id": memory["conduct_id"], "reporter": npc["id"],
                "accused": memory["actor"], "tick": tick, "confidence": memory["confidence"], "claim": memory["text"],
                "basis": "firsthand_proximity_observation",
            }
            justice["reports"].append(report)
            emitted.append({"type": "conduct_reported", "actor_id": npc["id"], "payload": report})
            if memory["conduct_id"] not in reported_conduct:
                case = {
                    "id": f"case-{len(justice['cases']) + 1}", "conduct_id": memory["conduct_id"], "accused": memory["actor"],
                    "status": "investigating", "opened_tick": tick, "investigator": "sora", "reports": [], "finding": None,
                }
                justice["cases"].append(case)
                reported_conduct.add(memory["conduct_id"])
                _remember_consequence(state, tick, f"witness-memory:{memory['conduct_id']}", f"case:{case['id']}", [npc["id"], "sora"])
            next(case for case in justice["cases"] if case["conduct_id"] == memory["conduct_id"])["reports"].append(report["id"])

    for case in justice["cases"]:
        if case["status"] == "investigating" and tick >= case["opened_tick"] + 6:
            reports = [report for report in justice["reports"] if report["id"] in case["reports"]]
            conduct = next((item for item in state["consequences"] if item.get("id") == case["conduct_id"]), None)
            credible = [report for report in reports if report["confidence"] >= 0.55]
            if conduct and credible:
                case["status"] = "restitution_due"
                case["finding"] = {"tick": tick, "result": "substantiated", "evidence": [conduct["id"]] + [report["id"] for report in credible]}
                case["restitution"] = dict(conduct["quantity"])
                case["deadline_tick"] = tick + 24
                player = state["players"].get(case["accused"])
                if player:
                    player["reputation"] -= 8
                    player["known_cases"].append(case["id"])
                _remember_consequence(state, tick, f"case:{case['id']}", f"restitution:{case['id']}", ["sora", case["accused"]])
                emitted.append({"type": "case_decided", "actor_id": "sora", "payload": {"case_id": case["id"], "status": case["status"], "deadline_tick": case["deadline_tick"]}})
            else:
                case["status"] = "closed_insufficient_evidence"
                case["finding"] = {"tick": tick, "result": "not_substantiated", "evidence": [report["id"] for report in credible]}
                emitted.append({"type": "case_closed", "actor_id": "sora", "payload": {"case_id": case["id"], "reason": "insufficient corroborating evidence"}})
        elif case["status"] == "restitution_due" and tick > case["deadline_tick"]:
            case["status"] = "bounty_active"
            bounty = {"id": f"bounty-{len(justice['bounties']) + 1}", "case_id": case["id"], "subject": case["accused"], "status": "active", "provisional_reward": 6.0, "created_tick": tick, "assignee": None, "contact": None}
            justice["bounties"].append(bounty)
            state["npcs"]["orin"]["intention"] = f"locate {case['accused']} for restitution"
            state["npcs"]["orin"]["reason"] = f"Public case {case['id']} passed its recovery deadline."
            _remember_consequence(state, tick, f"unresolved-restitution:{case['id']}", f"bounty:{bounty['id']}", ["orin", case["accused"]])
            emitted.append({"type": "bounty_posted", "actor_id": "sora", "payload": bounty})
    for bounty in justice["bounties"]:
        if bounty["status"] != "active":
            continue
        if bounty.get("assignee") is None and tick >= bounty["created_tick"] + 2:
            bounty["assignee"] = {"id": "orin", "kind": "npc", "accepted_tick": tick}
            _remember_consequence(state, tick, f"bounty:{bounty['id']}", f"recovery-duty:orin", ["orin", bounty["subject"]])
            emitted.append({"type": "bounty_accepted", "actor_id": "orin", "payload": {"bounty_id": bounty["id"], "reward": bounty["provisional_reward"]}})
        assignee = bounty.get("assignee")
        subject = state["players"].get(bounty["subject"])
        if not assignee or assignee["kind"] != "npc" or not subject or bounty.get("contact"):
            continue
        npc = state["npcs"].get(assignee["id"])
        if not npc or min(npc["needs"]["nutrition"], npc["needs"]["hydration"], npc["needs"]["rest"]) < 24:
            continue
        npc["location"] = _move_for_legacy(state, npc, subject["location"])
        emitted.append({"type": "recovery_movement", "actor_id": npc["id"], "payload": {"bounty_id": bounty["id"], "location": npc["location"]}})
        if npc["location"] == subject["location"]:
            bounty["contact"] = {"tick": tick, "collector": npc["id"], "location": list(npc["location"]), "status": "restitution_requested"}
            _remember_consequence(state, tick, f"recovery-duty:{npc['id']}", f"contact:{bounty['id']}", [npc["id"], bounty["subject"]])
            emitted.append({"type": "restitution_requested", "actor_id": npc["id"], "payload": {"bounty_id": bounty["id"], "subject": bounty["subject"], "location": npc["location"]}})
    return emitted


def _process_governance(state: Dict[str, Any], tick: int) -> list[Dict[str, Any]]:
    governance = state["institutions"]["governance"]
    access = governance["resource_access"]
    justice = state["institutions"]["justice"]
    emitted: list[Dict[str, Any]] = []
    if tick % 12 == 0:
        substantiated = [case for case in justice["cases"] if (case.get("finding") or {}).get("result") == "substantiated"]
        if access["mode"] == "open_stores" and not access.get("proposal") and substantiated:
            access["proposal"] = {
                "id": f"policy-resource-checkout-{tick}", "status": "proposed", "proposed_tick": tick,
                "cause_cases": [case["id"] for case in substantiated],
                "rationale": "Preserve broad resource access while making temporary custody and return obligations legible.",
            }
            _remember_consequence(state, tick, f"substantiated-cases:{','.join(access['proposal']['cause_cases'])}", f"policy-proposal:{access['proposal']['id']}", ["sora", "dev"])
            emitted.append({"type": "policy_proposed", "actor_id": "sora", "payload": dict(access["proposal"])})
        elif access.get("proposal") and access["proposal"]["status"] == "proposed" and tick >= access["proposal"]["proposed_tick"] + 12:
            proposal = access["proposal"]
            proposal["status"] = "enacted"
            proposal["enacted_tick"] = tick
            access["mode"] = "recorded_checkout"
            access["history"].append(dict(proposal))
            _remember_consequence(state, tick, f"policy-proposal:{proposal['id']}", "world-rule:recorded_checkout", ["council", "dev"])
            emitted.append({"type": "policy_enacted", "actor_id": "council", "payload": {"policy_id": proposal["id"], "mode": access["mode"]}})
    for checkout in governance["checkouts"]:
        if checkout["status"] != "active" or tick <= checkout["due_tick"]:
            continue
        checkout["status"] = "overdue"
        checkout["overdue_tick"] = tick
        player = state["players"].get(checkout["borrower"])
        if player:
            player["reputation"] -= 2
        _adjust_trust(state, "dev", checkout["borrower"], -0.1, checkout["id"], tick)
        state["npcs"]["dev"]["intention"] = f"follow up checkout with {checkout['borrower']}"
        state["npcs"]["dev"]["reason"] = f"Recorded checkout {checkout['id']} passed its agreed return time."
        state["institutions"]["council"]["knowledge"].append({"tick": tick, "kind": "overdue_checkout", "checkout_id": checkout["id"], "borrower": checkout["borrower"], "quantity": checkout["quantity"]})
        _remember_consequence(state, tick, f"unreturned-checkout:{checkout['id']}", f"access-delinquency:{checkout['borrower']}", [checkout["borrower"], "dev"])
        emitted.append({"type": "checkout_overdue", "actor_id": "dev", "payload": {"checkout_id": checkout["id"], "borrower": checkout["borrower"], "quantity": checkout["quantity"]}})
    return emitted


def _process_maintenance(state: Dict[str, Any], tick: int) -> list[Dict[str, Any]]:
    """Project maintenance demand into canonical shared actions; never repair here."""
    emitted: list[Dict[str, Any]] = []
    orders = state["institutions"]["governance"]["maintenance_orders"]
    for order in orders:
        if order["status"] != "open":
            continue
        site = state["resource_sites"].get(order["site_id"])
        pump = site.get("installed_pump") if site else None
        if not pump:
            order["status"] = "cancelled"
            order["closed_tick"] = tick
            order["closure_reason"] = "installed technology no longer exists"
            emitted.append({"type": "maintenance_cancelled", "actor_id": "dev", "payload": {"order_id": order["id"], "reason": order["closure_reason"]}})
            continue
        active_id = order.get("canonical_action_id")
        if active_id and active_id in state["shared_actions"]["records"]:
            continue
        action_id = f"shared:repair:{order['id']}"
        result = apply_shared_action_command(state, "ada", {
            "operation": "propose", "shared_action_id": action_id,
            "action_type": MECHANICAL_PUMP_REPAIR.action_type, "target_id": site["id"],
            "intent": f"restore the measured condition of {site['name']}",
            "observations": [f"maintenance-order:{order['id']}", f"condition:{pump['condition']}", f"cycles:{pump['cycles']}"],
            "autonomous_origin": True,
        })
        if result.get("accepted"):
            order.update({"canonical_action_id": action_id, "assigned_to": "ada", "assigned_tick": tick, "status": "open"})
            emitted.append({"type": "maintenance_action_proposed", "actor_id": "ada", "payload": {"order_id": order["id"], "action_id": action_id, "site_id": site["id"]}})
    return emitted


def _process_water_quality(state: Dict[str, Any], tick: int) -> list[Dict[str, Any]]:
    """Test player-delivered raw water, then let verified supply change resident needs."""
    emitted: list[Dict[str, Any]] = []
    system = state["water_system"]
    for batch in system["batches"]:
        if batch["status"] != "awaiting_test" or tick < batch["test_due_tick"]:
            continue
        collection = batch["collection_evidence"]
        condition = collection.get("condition_after")
        safety = 0.78 if condition is None else round(max(0.0, min(1.0, 0.86 - (1 - float(condition)) * 0.22)), 4)
        accepted = safety >= 0.75
        batch.update({"status": "verified" if accepted else "rejected", "tested_tick": tick, "tested_by": "mira", "safety": safety, "accepted": accepted})
        measurements = {"volume": batch["amount"], "safety": safety, "accepted": accepted, "source_cycle": collection.get("cycle")}
        _evidence(state, tick, f"water batch {batch['id']} tested", [batch["submitted_by"], "mira"], {"raw_water": batch["amount"]}, ["sample_jars", "test_strip", "turbidity_tube", "notebook"], measurements, "mira", [batch["source_evidence"]], ["water safety test", "source custody"])
        state["npcs"]["mira"]["memories"].append({"tick": tick, "kind": "completed_work", "text": f"Tested {batch['id']} from {batch['source_site']}; {'accepted' if accepted else 'rejected'} at safety {safety}."})
        if accepted:
            state["resources"]["tested_water"] += batch["amount"]
            for shortage in system["shortages"]:
                if shortage["status"] == "unresolved":
                    shortage["status"] = "supply_verified"
                    shortage["recovered_tick"] = tick
                    shortage["recovered_by_batch"] = batch["id"]
            amount = round(batch["amount"] * state["economy"]["prices"]["tested_water"], 2)
            _provisional_claim(state, tick, batch["submitted_by"], "verified safe-water delivery", amount, f"water-test:{batch['id']}")
            _remember_consequence(state, tick, f"water-delivery:{batch['id']}", f"communal-tested-water:+{batch['amount']}", [batch["submitted_by"], "mira", "settlement"])
            emitted.append({"type": "water_batch_verified", "actor_id": "mira", "payload": {"batch_id": batch["id"], "amount": batch["amount"], "safety": safety, "submitted_by": batch["submitted_by"]}})
        else:
            _remember_consequence(state, tick, f"water-delivery:{batch['id']}", f"unsafe-water-rejected:{safety}", [batch["submitted_by"], "mira"])
            emitted.append({"type": "water_batch_rejected", "actor_id": "mira", "payload": {"batch_id": batch["id"], "amount": batch["amount"], "safety": safety, "submitted_by": batch["submitted_by"]}})
    if tick % 12 == 0:
        eligible = sorted((npc for npc in state["npcs"].values() if npc["needs"]["hydration"] < 90), key=lambda npc: (npc["needs"]["hydration"], npc["id"]))
        # Accepted public work has already reserved the minimum safe cooking input;
        # ordinary drinking cannot silently consume its contracted materials.
        founding_reserve = 6 if state["event"]["status"] != "completed" and state["event"]["phase"] <= 7 else 0
        cooking_reserve = sum(
            order.get("required_inputs", {}).get("tested_water", 0)
            for order in state.get("cooking", {}).get("work_orders", [])
            if order.get("status") in {"proposed", "assigned", "blocked_inputs", "blocked_facility", "blocked_worker"}
        )
        available = max(0, int(state["resources"].get("tested_water", 0)) - founding_reserve - cooking_reserve)
        servings = min(len(eligible), available)
        if servings:
            recipients = []
            for npc in eligible[:servings]:
                before = npc["needs"]["hydration"]
                npc["needs"]["hydration"] = round(min(100, before + 18), 2)
                recipients.append({"npc_id": npc["id"], "before": before, "after": npc["needs"]["hydration"]})
            state["resources"]["tested_water"] -= servings
            record = {"tick": tick, "amount": servings, "recipients": recipients, "source": "verified communal water"}
            system["consumption_history"].append(record)
            system["consumption_history"] = system["consumption_history"][-250:]
            _remember_consequence(state, tick, f"communal-water-consumed:{tick}", f"hydration-restored:{','.join(item['npc_id'] for item in recipients)}", [item["npc_id"] for item in recipients])
            emitted.append({"type": "communal_water_consumed", "actor_id": "settlement", "payload": record})
        elif any(npc["needs"]["hydration"] < 40 for npc in eligible):
            if not system["shortages"] or system["shortages"][-1]["tick"] < tick - 12:
                shortage = {"tick": tick, "tested_water": 0, "affected": [npc["id"] for npc in eligible if npc["needs"]["hydration"] < 40], "status": "unresolved"}
                system["shortages"].append(shortage)
                _remember_consequence(state, tick, "tested-water-depleted", f"hydration-shortage:{','.join(shortage['affected'])}", [*shortage["affected"], "mira", "council"])
                emitted.append({"type": "water_shortage", "actor_id": "settlement", "payload": shortage})
    return emitted


def _process_meal_spoilage(state: Dict[str, Any], tick: int) -> list[Dict[str, Any]]:
    """Age accepted meal batches into physical waste when storage time expires."""
    emitted: list[Dict[str, Any]] = []
    cooking = state["cooking"]
    for batch in cooking["meal_batches"]:
        remaining = int(batch.get("remaining_portions", 0))
        if batch.get("status") != "accepted" or remaining < 1 or tick < batch.get("expires_tick", tick + 1):
            continue
        state["resources"]["safe_meals"] = max(0, state["resources"].get("safe_meals", 0) - remaining)
        batch["remaining_portions"] = 0
        batch["status"] = "spoiled"
        batch["spoiled_tick"] = tick
        batch["waste_portions"] = remaining
        cooking["waste_portions"] += remaining
        record = {
            "tick": tick, "batch_id": batch["id"], "lost_portions": remaining,
            "storage_quality": state["food"].get("storage_quality", 0), "preservation": batch.get("preservation", "none"),
            "remaining_safe_meals": state["resources"]["safe_meals"],
        }
        cooking["spoilage_history"].append(record)
        state["institutions"]["council"]["knowledge"].append({"tick": tick, "kind": "food_waste", **record})
        _evidence(state, tick, f"meal batch {batch['id']} spoiled", ["environment"], {"accepted_meal_portions": remaining}, ["storage log"], record, "lena", [f"meal-inspection:{batch['id']}"], ["shelf-life record", "waste count"])
        _remember_consequence(state, tick, f"meal-batch-expired:{batch['id']}", f"safe-meals-lost:{remaining}", ["environment", "lena", "council"])
        emitted.append({"type": "meal_batch_spoiled", "actor_id": "environment", "payload": record})
    cooking["spoilage_history"] = cooking["spoilage_history"][-250:]
    return emitted


def _process_preservation_learning(state: Dict[str, Any], tick: int) -> list[Dict[str, Any]]:
    """Let repeated food loss produce a supplied, tested change to future practice."""
    emitted: list[Dict[str, Any]] = []
    cooking = state["cooking"]
    program = cooking["preservation_program"]
    if program["status"] == "inactive" and cooking["waste_portions"] >= program["waste_trigger"]:
        sources = [f"meal-batch-expired:{item['batch_id']}" for item in cooking["spoilage_history"]]
        program.update({"status": "proposed", "proposed_tick": tick, "causal_sources": sources, "missing": {}})
        program["history"].append({"tick": tick, "status": "proposed", "waste_portions": cooking["waste_portions"], "causal_sources": sources})
        state["institutions"]["council"]["knowledge"].append({"tick": tick, "kind": "preservation_research_proposed", "method": program["method"], "waste_portions": cooking["waste_portions"], "causal_sources": sources})
        _remember_consequence(state, tick, f"recorded-food-waste:{cooking['waste_portions']}", f"preservation-trial-proposed:{program['method']}", ["lena", "imani", "council"])
        emitted.append({"type": "preservation_trial_proposed", "actor_id": "lena", "payload": {"method": program["method"], "waste_portions": cooking["waste_portions"], "required_inputs": dict(program["required_inputs"])}})
    if program["status"] in {"proposed", "blocked_inputs"}:
        if tick < program.get("proposed_tick", tick) + 1:
            return emitted
        missing = {name: amount - state["resources"].get(name, 0) for name, amount in program["required_inputs"].items() if state["resources"].get(name, 0) < amount}
        if missing:
            signature = ",".join(sorted(missing))
            if program.get("missing") != missing:
                program["missing"] = missing
                program["status"] = "blocked_inputs"
                program["history"].append({"tick": tick, "status": "blocked_inputs", "missing": dict(missing)})
                _remember_consequence(state, tick, f"preservation-trial-proposed:{program['method']}", f"preservation-input-shortage:{signature}", ["lena", "dev"])
                emitted.append({"type": "preservation_trial_blocked", "actor_id": "lena", "payload": {"method": program["method"], "missing": missing}})
            return emitted
        for name, amount in program["required_inputs"].items():
            state["resources"][name] -= amount
        program.update({"status": "trial", "trial_started_tick": tick, "trial_due_tick": tick + 4, "missing": {}})
        program["history"].append({"tick": tick, "status": "trial", "inputs": dict(program["required_inputs"]), "due_tick": program["trial_due_tick"]})
        _evidence(state, tick, f"{program['method']} preservation trial started", ["lena"], dict(program["required_inputs"]), ["drying rack", "scale", "timer", "storage container"], {"baseline_waste_portions": cooking["waste_portions"], "trial_due_tick": program["trial_due_tick"]}, "imani", program.get("causal_sources", []), ["preservation trial protocol"])
        emitted.append({"type": "preservation_trial_started", "actor_id": "lena", "payload": {"method": program["method"], "due_tick": program["trial_due_tick"], "inputs": dict(program["required_inputs"])}})
    elif program["status"] == "trial" and tick >= program["trial_due_tick"]:
        skill = state["npcs"]["lena"]["competencies"].get("cook", 0.65)
        shelf_life_gain = 24 if skill >= 0.6 else 8
        passed = shelf_life_gain >= 16
        program.update({"status": "active" if passed else "rejected", "tested_tick": tick, "tested_by": "imani", "shelf_life_gain_ticks": shelf_life_gain, "passed": passed})
        program["history"].append({"tick": tick, "status": program["status"], "tested_by": "imani", "shelf_life_gain_ticks": shelf_life_gain, "passed": passed})
        trial_evidence = next(item for item in reversed(state["evidence"]) if item["change"] == f"{program['method']} preservation trial started")
        trial_evidence["inspection"] = {"passed": passed, "shelf_life_gain_ticks": shelf_life_gain, "tested_by": "imani"}
        if passed:
            _provisional_claim(state, tick, "lena", "validated food-preservation practice", 8.0, f"preservation-trial:{program['method']}:{tick}")
            _provisional_claim(state, tick, "imani", "preservation safety inspection", 4.0, f"preservation-trial:{program['method']}:{tick}")
            state["culture"]["traditions"].append({"name": f"Measured {program['method']} practice", "origin_tick": tick, "cause": f"recorded-food-waste:{cooking['waste_portions']}"})
            state["npcs"]["lena"]["memories"].append({"tick": tick, "kind": "completed_work", "text": f"Validated {program['method']} after {cooking['waste_portions']} portions were lost to spoilage."})
            _remember_consequence(state, tick, f"preservation-trial:{program['method']}", f"cooking-practice-active:{program['method']}:+{shelf_life_gain}-ticks", ["lena", "imani", "council"])
            emitted.append({"type": "preservation_practice_validated", "actor_id": "imani", "payload": {"method": program["method"], "shelf_life_gain_ticks": shelf_life_gain}})
        else:
            _remember_consequence(state, tick, f"preservation-trial:{program['method']}", "preservation-practice-rejected", ["lena", "imani"])
            emitted.append({"type": "preservation_practice_rejected", "actor_id": "imani", "payload": {"method": program["method"], "shelf_life_gain_ticks": shelf_life_gain}})
    return emitted


def _process_npc_survival(state: Dict[str, Any], tick: int) -> list[Dict[str, Any]]:
    """Resolve low needs through spatial, finite actions rather than intention text alone."""
    emitted: list[Dict[str, Any]] = []
    survival = state["survival"]
    kitchen = state["places"]["communal_kitchen"]["location"]
    rest_places = {
        "hearth-house": state["places"]["hearth_house"]["location"],
        "river-house": state["places"]["river_house"]["location"],
        "independent": state["places"]["clinic"]["location"],
        "unattached": state["places"]["clinic"]["location"],
    }
    for npc in state["npcs"].values():
        activity = npc.get("survival_activity")
        if activity and activity["status"] == "active" and activity["kind"] == "rest" and npc["needs"]["rest"] >= 24:
            activity["status"] = "completed"
            activity["completed_tick"] = tick
            survival["rest_history"].append({"tick": tick, "npc_id": npc["id"], "status": "recovered", "rest": npc["needs"]["rest"], "started_tick": activity["started_tick"]})
            npc["memories"].append({"tick": tick, "kind": "completed_work", "text": "Recovered enough rest to resume chosen work."})
            _remember_consequence(state, tick, f"fatigue:{npc['id']}:{activity['started_tick']}", f"worker-recovered:{npc['id']}", [npc["id"]])
            emitted.append({"type": "npc_recovered", "actor_id": npc["id"], "payload": {"need": "rest", "value": npc["needs"]["rest"]}})
            activity = None
        if npc["needs"]["nutrition"] < 28:
            if not activity or activity.get("kind") != "eat" or activity.get("status") != "active":
                npc["survival_activity"] = activity = {"kind": "eat", "status": "active", "started_tick": tick, "destination": list(kitchen)}
            npc["intention"], npc["reason"] = "seek a safe meal", "Nutrition is too low for dependable work."
            if state["resources"].get("safe_meals", 0) < 1:
                active_shortage = next((item for item in survival["shortages"] if item["kind"] == "safe_meal" and item["status"] == "unresolved"), None)
                if not active_shortage:
                    shortage = {"id": f"survival-shortage-{len(survival['shortages']) + 1}", "tick": tick, "kind": "safe_meal", "status": "unresolved", "affected": [npc["id"]]}
                    survival["shortages"].append(shortage)
                    state["institutions"]["council"]["endorsements"][f"survival:{shortage['id']}"] = "food"
                    _remember_consequence(state, tick, "safe-meals-depleted", f"food-shortage:{shortage['id']}", [npc["id"], "lena", "council"])
                    emitted.append({"type": "meal_shortage", "actor_id": npc["id"], "payload": shortage})
                elif npc["id"] not in active_shortage["affected"]:
                    active_shortage["affected"].append(npc["id"])
                activity["blocked_by"] = "safe_meals"
                continue
            if _distance(npc["location"], kitchen) > 1:
                origin = list(npc["location"])
                npc["location"] = _move_for_legacy(state, npc, kitchen, survival=True)
                emitted.append({"type": "survival_movement", "actor_id": npc["id"], "payload": {"kind": "eat", "from": origin, "to": list(npc["location"]), "destination": "communal_kitchen"}})
                continue
            before = npc["needs"]["nutrition"]
            meal_batch = min(
                (batch for batch in state["cooking"]["meal_batches"] if batch.get("status") == "accepted" and batch.get("remaining_portions", 0) > 0),
                key=lambda batch: (batch.get("expires_tick", 10**12), batch["id"]),
                default=None,
            )
            state["resources"]["safe_meals"] -= 1
            if meal_batch:
                meal_batch["remaining_portions"] -= 1
                if meal_batch["remaining_portions"] == 0:
                    meal_batch["status"] = "consumed"
                    meal_batch["consumed_tick"] = tick
            npc["needs"]["nutrition"] = round(min(100, before + 36), 2)
            npc["needs"]["belonging"] = round(min(100, npc["needs"]["belonging"] + 2), 2)
            activity["status"] = "completed"
            activity["completed_tick"] = tick
            record = {"tick": tick, "npc_id": npc["id"], "before": before, "after": npc["needs"]["nutrition"], "location": list(npc["location"]), "remaining_meals": state["resources"]["safe_meals"], "meal_batch_id": meal_batch["id"] if meal_batch else "legacy_communal_stock"}
            survival["meal_history"].append(record)
            for shortage in survival["shortages"]:
                if shortage["kind"] == "safe_meal" and shortage["status"] == "unresolved":
                    shortage["affected"] = [item for item in shortage["affected"] if item != npc["id"]]
                    if not shortage["affected"]:
                        shortage["status"] = "recovered"
                        shortage["recovered_tick"] = tick
            _evidence(state, tick, f"safe meal consumed by {npc['id']}", [npc["id"], "lena"], {"safe_meal": 1, "meal_batch": record["meal_batch_id"]}, ["communal kitchen", "serving vessel"], {"nutrition_before": before, "nutrition_after": npc["needs"]["nutrition"], "remaining_meals": state["resources"]["safe_meals"]}, None, [f"nutrition-need:{npc['id']}", f"meal-batch:{record['meal_batch_id']}"], ["meal consumption", "batch custody"])
            _remember_consequence(state, tick, f"nutrition-need:{npc['id']}", f"nutrition-restored:{npc['id']}:{npc['needs']['nutrition']}", [npc["id"], "lena"])
            emitted.append({"type": "meal_consumed", "actor_id": npc["id"], "payload": record})
            continue
        if npc["needs"]["rest"] < 24:
            destination = rest_places.get(npc.get("household"), state["places"]["clinic"]["location"])
            if not activity or activity.get("kind") != "rest" or activity.get("status") != "active":
                npc["survival_activity"] = activity = {"kind": "rest", "status": "active", "started_tick": tick, "destination": list(destination)}
            npc["intention"], npc["reason"] = "return to a recovery space", "Fatigue is below the threshold for reliable work."
            if _distance(npc["location"], destination) > 1:
                origin = list(npc["location"])
                npc["location"] = _move_for_legacy(state, npc, destination, survival=True)
                emitted.append({"type": "survival_movement", "actor_id": npc["id"], "payload": {"kind": "rest", "from": origin, "to": list(npc["location"]), "destination": "recovery_space"}})
                continue
            before = npc["needs"]["rest"]
            npc["needs"]["rest"] = round(min(100, before + 4), 2)
            survival["rest_history"].append({"tick": tick, "npc_id": npc["id"], "status": "resting", "before": before, "after": npc["needs"]["rest"], "location": list(npc["location"])})
            emitted.append({"type": "npc_rested", "actor_id": npc["id"], "payload": {"before": before, "after": npc["needs"]["rest"], "location": list(npc["location"])}})
    survival["meal_history"] = survival["meal_history"][-250:]
    survival["rest_history"] = survival["rest_history"][-500:]
    return emitted


def _process_communal_cooking(state: Dict[str, Any], tick: int) -> list[Dict[str, Any]]:
    """Convert recorded hunger into supplied, prepared, inspected communal meals."""
    emitted: list[Dict[str, Any]] = []
    cooking = state["cooking"]
    survival = state["survival"]
    active_statuses = {"proposed", "assigned", "blocked_inputs", "blocked_facility", "blocked_worker", "preparing", "inspecting"}
    shortage = next((item for item in survival["shortages"] if item["kind"] == "safe_meal" and item["status"] == "unresolved"), None)
    if shortage and not state["shared_actions"].get("canonical_cooking", False) and not any(order["status"] in active_statuses for order in cooking["work_orders"]):
        portions = max(3, min(6, len(shortage["affected"]) * 2))
        preservation = cooking["preservation_program"]["method"] if cooking["preservation_program"]["status"] == "active" else "none"
        required_inputs = {"raw_food": portions, "tested_water": math.ceil(portions / 2), "fuel": max(1, math.ceil(portions / 3)) + (1 if preservation != "none" else 0)}
        if preservation != "none":
            required_inputs["containers"] = 1
        order = {
            "id": f"cooking-work-{len(cooking['work_orders']) + 1}", "status": "proposed", "created_tick": tick,
            "shortage_id": shortage["id"], "cook": "lena", "inspector": "imani", "portions": portions,
            "required_inputs": required_inputs, "preservation": preservation,
            "history": [{"tick": tick, "status": "proposed", "cause": f"food-shortage:{shortage['id']}"}],
        }
        cooking["work_orders"].append(order)
        shortage["cooking_order_id"] = order["id"]
        _remember_consequence(state, tick, f"food-shortage:{shortage['id']}", f"communal-cooking-work:{order['id']}", ["lena", "imani", *shortage["affected"]])
        emitted.append({"type": "cooking_work_proposed", "actor_id": "lena", "payload": {"order_id": order["id"], "portions": portions, "required_inputs": dict(order["required_inputs"])}})
    for order in cooking["work_orders"]:
        if order.get("canonical_action_id"):
            continue
        if order["status"] not in active_statuses:
            continue
        cook = state["npcs"][order["cook"]]
        inspector = state["npcs"][order["inspector"]]
        kitchen = state["places"]["communal_kitchen"]
        destination = kitchen["location"]
        if order["status"] == "proposed":
            if tick < order["created_tick"] + 1:
                continue
            if kitchen.get("status") != "operational":
                order["status"] = "blocked_facility"
                order["history"].append({"tick": tick, "status": order["status"], "reason": "communal kitchen is not operational"})
                state["institutions"]["council"]["endorsements"][f"cooking:{order['id']}"] = "food"
                emitted.append({"type": "cooking_work_blocked", "actor_id": cook["id"], "payload": {"order_id": order["id"], "reason": "communal kitchen is not operational"}})
                continue
            order["status"] = "assigned"
            order["assigned_tick"] = tick
            order["history"].append({"tick": tick, "status": "assigned", "cook": cook["id"], "inspector": inspector["id"]})
            emitted.append({"type": "cooking_work_assigned", "actor_id": cook["id"], "payload": {"order_id": order["id"], "inspector": inspector["id"]}})
            continue
        if order["status"] == "blocked_facility":
            if kitchen.get("status") == "operational":
                order["status"] = "assigned"
                order["history"].append({"tick": tick, "status": "assigned", "cause": "kitchen became operational"})
            continue
        if order["status"] == "blocked_worker":
            if cook["needs"]["nutrition"] >= 28 and cook["needs"]["rest"] >= 24:
                order["status"] = order.pop("resume_status", "assigned")
                order["history"].append({"tick": tick, "status": order["status"], "cause": "cook recovered"})
            continue
        if order["status"] == "blocked_inputs":
            missing = {name: amount - state["resources"].get(name, 0) for name, amount in order["required_inputs"].items() if state["resources"].get(name, 0) < amount}
            if not missing:
                order["status"] = "assigned"
                order["history"].append({"tick": tick, "status": "assigned", "cause": "required ingredients delivered"})
            else:
                order["missing"] = missing
            continue
        if order["status"] == "assigned":
            if cook["needs"]["nutrition"] < 28 or cook["needs"]["rest"] < 24:
                order["resume_status"] = "assigned"
                order["status"] = "blocked_worker"
                order["history"].append({"tick": tick, "status": order["status"], "reason": "cook survival need"})
                emitted.append({"type": "cooking_work_blocked", "actor_id": cook["id"], "payload": {"order_id": order["id"], "reason": "cook requires food or rest"}})
                continue
            missing = {name: amount - state["resources"].get(name, 0) for name, amount in order["required_inputs"].items() if state["resources"].get(name, 0) < amount}
            if missing:
                order["status"] = "blocked_inputs"
                order["missing"] = missing
                order["history"].append({"tick": tick, "status": order["status"], "missing": dict(missing)})
                if "tested_water" in missing and not any(item["status"] == "unresolved" for item in state["water_system"]["shortages"]):
                    water_shortage = {"tick": tick, "tested_water": state["resources"].get("tested_water", 0), "affected": [cook["id"]], "status": "unresolved", "reason": f"cooking-order:{order['id']}"}
                    state["water_system"]["shortages"].append(water_shortage)
                    emitted.append({"type": "water_shortage", "actor_id": cook["id"], "payload": water_shortage})
                _remember_consequence(state, tick, f"communal-cooking-work:{order['id']}", f"cooking-input-shortage:{','.join(sorted(missing))}", [cook["id"], "dev"])
                emitted.append({"type": "cooking_work_blocked", "actor_id": cook["id"], "payload": {"order_id": order["id"], "missing": missing}})
                continue
            if _distance(cook["location"], destination) > 1:
                origin = list(cook["location"])
                cook["location"] = _move_for_legacy(state, cook, destination)
                emitted.append({"type": "cooking_worker_moved", "actor_id": cook["id"], "payload": {"order_id": order["id"], "from": origin, "to": list(cook["location"]), "destination": "communal_kitchen"}})
                continue
            for name, amount in order["required_inputs"].items():
                state["resources"][name] -= amount
            order["status"] = "preparing"
            order["preparation_started_tick"] = tick
            order["preparation_due_tick"] = tick + 4
            order["history"].append({"tick": tick, "status": "preparing", "inputs": dict(order["required_inputs"])})
            _remember_consequence(state, tick, f"cooking-inputs-supplied:{order['id']}", f"meal-preparation:{order['id']}", [cook["id"], "imani"])
            emitted.append({"type": "meal_preparation_started", "actor_id": cook["id"], "payload": {"order_id": order["id"], "due_tick": order["preparation_due_tick"], "inputs": dict(order["required_inputs"])}})
            continue
        if order["status"] == "preparing":
            if tick < order["preparation_due_tick"]:
                continue
            skill = cook["competencies"].get("cook", 0.65)
            safety = round(min(0.96, 0.68 + skill * 0.22 + (0.04 if kitchen.get("status") == "operational" else 0)), 4)
            batch = {
                "id": f"meal-batch-{len(cooking['meal_batches']) + 1}", "work_order_id": order["id"], "cook": cook["id"],
                "prepared_tick": tick, "portions": order["portions"], "inputs": dict(order["required_inputs"]),
                "safety": safety, "status": "awaiting_inspection", "recipe": "Founders provision stew", "preservation": order.get("preservation", "none"), "remaining_portions": 0,
            }
            cooking["meal_batches"].append(batch)
            order["meal_batch_id"] = batch["id"]
            order["status"] = "inspecting"
            order["history"].append({"tick": tick, "status": "inspecting", "batch_id": batch["id"], "safety": safety})
            _evidence(state, tick, f"meal batch {batch['id']} prepared", [cook["id"]], batch["inputs"], ["hearth", "pot", "ladle", "timer"], {"portions": batch["portions"], "safety": safety, "cook_time_ticks": 4}, None, [f"food-shortage:{order['shortage_id']}"], ["temperature and time record"])
            emitted.append({"type": "meal_batch_prepared", "actor_id": cook["id"], "payload": {"order_id": order["id"], "batch_id": batch["id"], "portions": batch["portions"], "safety": safety}})
            continue
        if order["status"] == "inspecting":
            if _distance(inspector["location"], destination) > 1:
                origin = list(inspector["location"])
                inspector["location"] = _move_for_legacy(state, inspector, destination)
                emitted.append({"type": "cooking_inspector_moved", "actor_id": inspector["id"], "payload": {"order_id": order["id"], "from": origin, "to": list(inspector["location"]), "destination": "communal_kitchen"}})
                continue
            batch = next(item for item in cooking["meal_batches"] if item["id"] == order["meal_batch_id"])
            accepted = batch["safety"] >= 0.75
            batch.update({"status": "accepted" if accepted else "rejected", "inspected_tick": tick, "inspector": inspector["id"], "accepted": accepted})
            prepared_evidence = next(item for item in reversed(state["evidence"]) if item["change"] == f"meal batch {batch['id']} prepared")
            prepared_evidence["inspector"] = inspector["id"]
            prepared_evidence["inspection"] = {"accepted": accepted, "safety": batch["safety"]}
            if accepted:
                preservation_gain = state["cooking"]["preservation_program"].get("shelf_life_gain_ticks", 0) if batch["preservation"] != "none" else 0
                shelf_life = 24 + round(state["food"].get("storage_quality", 0) * 24) + (12 if state["places"]["dry_storage"].get("status") == "operational" else 0) + preservation_gain
                batch["remaining_portions"] = batch["portions"]
                batch["expires_tick"] = tick + shelf_life
                batch["shelf_life_ticks"] = shelf_life
                state["resources"]["safe_meals"] += batch["portions"]
                order["status"] = "completed"
                order["completed_tick"] = tick
                order["history"].append({"tick": tick, "status": "completed", "batch_id": batch["id"], "accepted_portions": batch["portions"]})
                if not any(recipe["name"] == batch["recipe"] for recipe in state["culture"]["recipes"]):
                    state["culture"]["recipes"].append({"name": batch["recipe"], "author": cook["id"], "first_served_tick": tick})
                _provisional_claim(state, tick, cook["id"], "inspected communal meal preparation", round(batch["portions"] * 2.0, 2), f"meal-inspection:{batch['id']}")
                _provisional_claim(state, tick, inspector["id"], "communal meal safety inspection", 4.0, f"meal-inspection:{batch['id']}")
                cook["memories"].append({"tick": tick, "kind": "completed_work", "text": f"Prepared {batch['portions']} accepted portions under {order['id']}."})
                linked_shortage = next((item for item in survival["shortages"] if item["id"] == order["shortage_id"]), None)
                subjects = [cook["id"], inspector["id"], *(linked_shortage["affected"] if linked_shortage else [])]
                _remember_consequence(state, tick, f"meal-inspection:{batch['id']}", f"safe-meals:+{batch['portions']}", subjects)
                emitted.append({"type": "cooking_work_completed", "actor_id": cook["id"], "payload": {"order_id": order["id"], "batch_id": batch["id"], "portions": batch["portions"], "inspector": inspector["id"]}})
            else:
                order["status"] = "rejected"
                order["history"].append({"tick": tick, "status": "rejected", "batch_id": batch["id"], "safety": batch["safety"]})
                state["failures"].append({"tick": tick, "action": "communal_cooking", "order_id": order["id"], "reason": "meal safety inspection rejected", "recovered": False})
                _remember_consequence(state, tick, f"meal-preparation:{batch['id']}", f"unsafe-meal-rejected:{batch['safety']}", [cook["id"], inspector["id"]])
                emitted.append({"type": "cooking_work_rejected", "actor_id": inspector["id"], "payload": {"order_id": order["id"], "batch_id": batch["id"], "safety": batch["safety"]}})
    return emitted


def _process_autonomous_water_work(state: Dict[str, Any], tick: int) -> list[Dict[str, Any]]:
    """Let a recorded shortage recursively create spatial collection and testing work."""
    emitted: list[Dict[str, Any]] = []
    system = state["water_system"]
    active_statuses = {"proposed", "assigned", "collecting", "delivering", "testing", "blocked_quality", "blocked_infrastructure", "blocked_worker"}
    unresolved = next((item for item in system["shortages"] if item["status"] == "unresolved"), None)
    if unresolved and not any(order["status"] in active_statuses for order in system["work_orders"]):
        order = {
            "id": f"water-work-{len(system['work_orders']) + 1}", "status": "proposed", "created_tick": tick,
            "shortage_tick": unresolved["tick"], "collector": "emil", "tester": "mira", "source_site": "well-site",
            "target_amount": 3, "batch_id": None, "history": [{"tick": tick, "status": "proposed", "cause": f"hydration-shortage:{unresolved['tick']}"}],
        }
        system["work_orders"].append(order)
        unresolved["work_order_id"] = order["id"]
        _remember_consequence(state, tick, f"hydration-shortage:{unresolved['tick']}", f"autonomous-water-work:{order['id']}", ["emil", "mira", *unresolved["affected"]])
        emitted.append({"type": "water_work_proposed", "actor_id": "mira", "payload": {"order_id": order["id"], "affected": unresolved["affected"], "target_amount": order["target_amount"]}})
    for order in system["work_orders"]:
        if order["status"] not in active_statuses:
            continue
        site = state["resource_sites"].get(order["source_site"])
        collector = state["npcs"][order["collector"]]
        lab = state["places"]["measurement_lab"]["location"]
        if order["status"] == "proposed":
            if tick < order["created_tick"] + 1:
                continue
            if not site or site.get("progress", 0) < 3:
                order["status"] = "blocked_infrastructure"
                order["history"].append({"tick": tick, "status": order["status"], "reason": "no completed well"})
                state["institutions"]["council"]["endorsements"][f"water-work:{order['id']}"] = "water"
                emitted.append({"type": "water_work_blocked", "actor_id": "emil", "payload": {"order_id": order["id"], "reason": "no completed well"}})
                continue
            order["status"] = "assigned"
            order["assigned_tick"] = tick
            order["history"].append({"tick": tick, "status": "assigned", "collector": collector["id"], "tester": order["tester"]})
            state["institutions"]["council"]["knowledge"].append({"tick": tick, "kind": "water_work_assigned", "order_id": order["id"], "collector": collector["id"], "tester": order["tester"]})
            emitted.append({"type": "water_work_assigned", "actor_id": "mira", "payload": {"order_id": order["id"], "collector": collector["id"], "tester": order["tester"]}})
            continue
        if order["status"] == "blocked_infrastructure":
            if site and site.get("progress", 0) >= 3:
                order["status"] = "assigned"
                order["history"].append({"tick": tick, "status": "assigned", "cause": "well became operational"})
            continue
        if order["status"] == "blocked_worker":
            if collector["needs"]["nutrition"] >= 28 and collector["needs"]["rest"] >= 24:
                order["status"] = order.pop("resume_status", "assigned")
                order["history"].append({"tick": tick, "status": order["status"], "cause": "collector recovered"})
            continue
        if order["status"] == "blocked_quality":
            pump = site.get("installed_pump") if site else None
            if not pump or (pump["status"] == "operational" and pump["condition"] >= 0.7):
                order["status"] = "assigned"
                order["batch_id"] = None
                order["history"].append({"tick": tick, "status": "assigned", "cause": "source quality conditions recovered"})
            continue
        if order["status"] in {"assigned", "collecting", "delivering"} and (collector["needs"]["nutrition"] < 28 or collector["needs"]["rest"] < 24):
            order["resume_status"] = order["status"]
            order["status"] = "blocked_worker"
            order["history"].append({"tick": tick, "status": order["status"], "reason": "collector survival need", "resume_status": order["resume_status"]})
            emitted.append({"type": "water_work_blocked", "actor_id": collector["id"], "payload": {"order_id": order["id"], "reason": "collector requires food or rest", "resume_status": order["resume_status"]}})
            continue
        if order["status"] in {"assigned", "collecting"}:
            if _distance(collector["location"], site["location"]) > 1:
                origin = list(collector["location"])
                collector["location"] = _move_for_legacy(state, collector, site["location"])
                order["status"] = "collecting"
                emitted.append({"type": "water_worker_moved", "actor_id": collector["id"], "payload": {"order_id": order["id"], "from": origin, "to": list(collector["location"]), "destination": site["id"]}})
                continue
            pump = site.get("installed_pump")
            if pump and pump["status"] == "failed":
                order["status"] = "blocked_quality"
                _open_pump_maintenance(state, site, f"water-work:{order['id']}:failed-pump")
                emitted.append({"type": "water_work_blocked", "actor_id": collector["id"], "payload": {"order_id": order["id"], "reason": "installed pump failed"}})
                continue
            predicted = pump["predicted_liters_per_stroke"] * pump["condition"] if pump else 3
            amount = min(order["target_amount"], max(1, round(predicted)), int(site.get("stock", 0)))
            if amount < 1 or state["resources"].get("tools", 0) < 1:
                order["status"] = "blocked_infrastructure"
                order["history"].append({"tick": tick, "status": order["status"], "reason": "water or communal tools unavailable"})
                emitted.append({"type": "water_work_blocked", "actor_id": collector["id"], "payload": {"order_id": order["id"], "reason": "water or communal tools unavailable"}})
                continue
            site["stock"] -= amount
            collector["inventory"]["water"] = collector["inventory"].get("water", 0) + amount
            collection = {"water": amount, "baseline_water": 3, "condition_after": None, "cycle": None}
            if pump:
                before = pump["condition"]
                pump["cycles"] += 1
                pump["condition"] = round(max(0.0, before - 0.08), 4)
                collection.update({"condition_before": before, "condition_after": pump["condition"], "cycle": pump["cycles"], "installed_pump": pump["design_id"]})
                state["technology"]["tool_catalog"][pump["design_id"]].setdefault("field_history", []).append({"tick": tick, "site_id": site["id"], "cycle": pump["cycles"], "condition": pump["condition"], "water": amount, "actor": collector["id"]})
                if pump["condition"] < 0.7:
                    _open_pump_maintenance(state, site, f"autonomous-wear:{site['id']}:{pump['cycles']}")
                if pump["condition"] <= 0.28:
                    pump["status"] = "failed"
            record = {"tick": tick, "actor": collector["id"], "operation": "draw_water", "inputs": {"communal_tools": 1}, "outputs": collection, "energy_cost": 2}
            site["history"].append(record)
            collector["needs"]["rest"] = max(0, collector["needs"]["rest"] - 2)
            order["collection_evidence"] = copy.deepcopy(collection)
            order["collection_tick"] = tick
            order["status"] = "delivering"
            order["history"].append({"tick": tick, "status": "delivering", "amount": amount, "source_site": site["id"]})
            _evidence(state, tick, f"raw water collected for {order['id']}", [collector["id"]], {}, ["bucket", "communal tools"], collection, None, [f"hydration-shortage:{order['shortage_tick']}"], ["source collection"])
            _remember_consequence(state, tick, f"autonomous-water-work:{order['id']}", f"raw-water-collected:{amount}", [collector["id"], "mira"])
            emitted.append({"type": "water_collected", "actor_id": collector["id"], "payload": {"order_id": order["id"], "amount": amount, "source_site": site["id"]}})
            continue
        if order["status"] == "delivering":
            if _distance(collector["location"], lab) > 1:
                origin = list(collector["location"])
                collector["location"] = _move_for_legacy(state, collector, lab)
                emitted.append({"type": "water_worker_moved", "actor_id": collector["id"], "payload": {"order_id": order["id"], "from": origin, "to": list(collector["location"]), "destination": "measurement_lab"}})
                continue
            amount = order["collection_evidence"]["water"]
            collector["inventory"]["water"] -= amount
            batch = {
                "id": f"water-batch-{len(system['batches']) + 1}", "status": "awaiting_test", "submitted_tick": tick,
                "test_due_tick": tick + 2, "submitted_by": collector["id"], "amount": amount, "source_site": site["id"],
                "source_evidence": f"autonomous-water-work:{order['id']}:collection-{order['collection_tick']}",
                "collection_evidence": copy.deepcopy(order["collection_evidence"]), "work_order_id": order["id"],
            }
            system["batches"].append(batch)
            order["batch_id"] = batch["id"]
            order["status"] = "testing"
            order["history"].append({"tick": tick, "status": "testing", "batch_id": batch["id"]})
            _remember_consequence(state, tick, f"raw-water-collected:{amount}", f"laboratory-test-required:{batch['id']}", [collector["id"], "mira"])
            emitted.append({"type": "water_delivered_to_lab", "actor_id": collector["id"], "payload": {"order_id": order["id"], "batch_id": batch["id"], "amount": amount}})
            continue
        if order["status"] == "testing":
            batch = next((item for item in system["batches"] if item["id"] == order["batch_id"]), None)
            if not batch or batch["status"] == "awaiting_test":
                continue
            if batch["status"] == "verified":
                order["status"] = "completed"
                order["completed_tick"] = tick
                order["history"].append({"tick": tick, "status": "completed", "batch_id": batch["id"], "safety": batch["safety"]})
                collector["memories"].append({"tick": tick, "kind": "completed_work", "text": f"Collected and delivered verified water under {order['id']}."})
                _remember_consequence(state, tick, f"water-test:{batch['id']}", f"water-work-completed:{order['id']}", [collector["id"], "mira", "settlement"])
                emitted.append({"type": "water_work_completed", "actor_id": collector["id"], "payload": {"order_id": order["id"], "batch_id": batch["id"], "amount": batch["amount"]}})
            else:
                order["status"] = "blocked_quality"
                order["history"].append({"tick": tick, "status": "blocked_quality", "batch_id": batch["id"], "safety": batch["safety"]})
                pump = site.get("installed_pump") if site else None
                if pump and pump["condition"] < 0.7:
                    _open_pump_maintenance(state, site, f"rejected-water:{batch['id']}:{batch['safety']}")
                emitted.append({"type": "water_work_blocked", "actor_id": "mira", "payload": {"order_id": order["id"], "reason": "water batch failed safety review", "safety": batch["safety"]}})
    return emitted


def _advance_travel_routes(state: Dict[str, Any], tick: int) -> list[Dict[str, Any]]:
    emitted: list[Dict[str, Any]] = []
    for actor_id, actor in {**state.get("npcs", {}), **state.get("players", {})}.items():
        route = actor.get("route")
        if not route or route.get("status") != "traveling":
            continue
        path = route.get("path", [])
        next_index = int(route.get("index", 0)) + 1
        if next_index >= len(path):
            route["status"] = "arrived"
            continue
        origin = list(actor.get("location", path[next_index - 1]))
        destination = list(path[next_index])
        actor["location"] = destination
        actor["current_region"] = "settlement"
        route["index"] = next_index
        _reveal_frontier(state, actor_id, destination)
        arrived = next_index == len(path) - 1
        if arrived:
            route["status"] = "arrived"
            route["arrived_tick"] = tick
        emitted.append({"type": "route_segment_completed", "actor_id": actor_id, "payload": {"from": origin, "to": destination, "route_id": route["id"], "arrived": arrived}})
    return emitted


def reduce_world_tick(state: Dict[str, Any], tick: int) -> list[Dict[str, Any]]:
    # Every reducer observes the same authoritative tick. Previously helpers
    # reading state.clock could lag the loop argument during offline catch-up.
    state["clock"]["tick"] = tick
    emitted = _advance_travel_routes(state, tick)
    emitted.extend(_execute_pending_reactions(state, tick))
    emitted.extend(_process_shared_actions(state, tick))
    emitted.extend(_advance_autonomous_shared_actions(state, tick))
    emitted.extend(_process_shared_action_demand(state, tick))
    emitted.extend(_process_shared_extraction_demand(state, tick))
    emitted.extend(_process_public_discourse(state, tick))
    emitted.extend(_advance_resource_sites(state, tick))
    emitted.extend(_process_research(state, tick))
    emitted.extend(_process_meal_spoilage(state, tick))
    emitted.extend(_process_preservation_learning(state, tick))
    emitted.extend(_process_npc_survival(state, tick))
    emitted.extend(_process_shared_meal_demand(state, tick))
    emitted.extend(_process_contract_negotiation(state, tick))
    emitted.extend(_process_environmental_stewardship(state, tick))
    emitted.extend(_process_teaching(state, tick))
    emitted.extend(_process_communal_cooking(state, tick))
    emitted.extend(_process_maintenance(state, tick))
    emitted.extend(_process_water_quality(state, tick))
    emitted.extend(_process_autonomous_water_work(state, tick))
    active_maintenance = next((order for order in state["institutions"]["governance"]["maintenance_orders"] if order["status"] == "open"), None)
    active_water_work = next((order for order in state["water_system"]["work_orders"] if order["status"] not in {"completed", "cancelled"}), None)
    active_cooking = next((order for order in state["cooking"]["work_orders"] if order["status"] not in {"completed", "rejected", "cancelled"}), None)
    active_preservation = state["cooking"]["preservation_program"] if state["cooking"]["preservation_program"]["status"] in {"proposed", "blocked_inputs", "trial"} else None
    active_stewardship = next((order for order in state["environment"]["stewardship_orders"] if order["status"] not in {"completed", "cancelled"}), None)
    active_teaching = next((order for order in state["education"]["teaching_orders"] if order["status"] not in {"completed", "cancelled"}), None)
    for npc in state["npcs"].values():
        npc["needs"]["nutrition"] = max(0, npc["needs"]["nutrition"] - 0.12)
        npc["needs"]["hydration"] = max(0, npc["needs"]["hydration"] - 0.15)
        npc["needs"]["rest"] = max(0, npc["needs"]["rest"] - 0.08)
        previous = npc["intention"]
        if npc["needs"]["hydration"] < 28:
            npc["intention"], npc["reason"] = "seek tested water", "Hydration is below the safe threshold."
        elif npc["needs"]["nutrition"] < 28:
            npc["intention"], npc["reason"] = "seek a safe meal", "Nutrition is below the safe threshold."
        elif npc["needs"]["rest"] < 24:
            npc["intention"], npc["reason"] = "rest", "Fatigue prevents reliable work."
        elif npc["id"] == "orin" and any(bounty["status"] == "active" for bounty in state["institutions"]["justice"]["bounties"]):
            bounty = next(bounty for bounty in state["institutions"]["justice"]["bounties"] if bounty["status"] == "active")
            npc["intention"], npc["reason"] = f"locate {bounty['subject']} for restitution", f"Accepted public recovery duty for {bounty['case_id']}."
        elif active_maintenance and npc["id"] == "ada":
            missing = active_maintenance.get("blockers", [])[-1].get("missing", []) if active_maintenance.get("blockers") else []
            npc["intention"] = f"procure {', '.join(missing)} for {active_maintenance['id']}" if missing else f"maintain pump under {active_maintenance['id']}"
            npc["reason"] = f"Observed wear at {active_maintenance['site_id']} created a persistent maintenance obligation."
        elif active_maintenance and npc["id"] == "dev":
            npc["intention"], npc["reason"] = f"supply {active_maintenance['id']}", "The assigned repair requires accountable access to settlement stores."
        elif active_maintenance and npc["id"] == "mira":
            npc["intention"], npc["reason"] = f"verify {active_maintenance['id']}", "Recovered output must be measured before the repair can enter the evidence record."
        elif active_water_work and npc["id"] == "emil":
            npc["intention"], npc["reason"] = f"{active_water_work['status']} {active_water_work['id']}", f"A recorded hydration shortage requires physical collection from {active_water_work['source_site']}."
        elif active_water_work and npc["id"] == "mira":
            npc["intention"], npc["reason"] = f"test water for {active_water_work['id']}", "Communal supply cannot change until source custody and safety are verified."
        elif active_cooking and npc["id"] == "lena":
            npc["intention"], npc["reason"] = f"{active_cooking['status']} {active_cooking['id']}", "A recorded meal shortage requires supplied, timed, inspected kitchen work."
        elif active_cooking and npc["id"] == "imani":
            npc["intention"], npc["reason"] = f"inspect {active_cooking['id']}", "Prepared food cannot enter communal supply without independent safety evidence."
        elif active_preservation and npc["id"] == "lena":
            npc["intention"], npc["reason"] = f"{active_preservation['status']} {active_preservation['method']} preservation", "Recorded spoilage created a testable need to change kitchen practice."
        elif active_preservation and npc["id"] == "imani":
            npc["intention"], npc["reason"] = f"verify {active_preservation['method']} preservation", "A new preservation practice requires measured shelf-life and safety evidence."
        elif active_stewardship and npc["id"] == active_stewardship["worker"]:
            npc["intention"], npc["reason"] = f"{active_stewardship['status']} {active_stewardship['kind']} at {active_stewardship['site_id']}", f"Recorded local depletion created stewardship obligation {active_stewardship['id']}."
        elif active_stewardship and npc["id"] == active_stewardship["inspector"]:
            npc["intention"], npc["reason"] = f"inspect {active_stewardship['kind']} at {active_stewardship['site_id']}", "Ecological recovery must be measured before restoration is valued."
        elif active_teaching and npc["id"] == active_teaching["instructor"]:
            npc["intention"], npc["reason"] = f"teach {active_teaching['domain']} to {active_teaching['learner']}", f"Verified work in {active_teaching['source_order_id']} created teachable evidence."
        elif active_teaching and npc["id"] == active_teaching["learner"]:
            npc["intention"], npc["reason"] = f"demonstrate {active_teaching['domain']}", f"Instruction order {active_teaching['id']} can expand settlement capability."
        elif state["event"]["status"] != "completed":
            phase = state["event"]["priorities"][state["event"]["phase"]]
            npc["intention"], npc["reason"] = phase.replace("_", " "), "The Founding Table selected this unresolved dependency."
        elif state["institutions"]["council"].get("current_initiative"):
            initiative = state["institutions"]["council"]["current_initiative"]
            blueprint = INITIATIVE_BLUEPRINTS[initiative["priority"]]
            if npc["id"] in blueprint["workers"]:
                npc["intention"], npc["reason"] = f"{initiative['status']} {initiative['priority']} work", initiative["reason"]
            elif npc["id"] == blueprint["inspector"]:
                npc["intention"], npc["reason"] = f"inspect {initiative['priority']} work", "Public work requires independent evidence."
        if (
            state["event"]["status"] == "completed"
            and not state["institutions"]["council"].get("current_initiative")
            and min(npc["needs"]["nutrition"], npc["needs"]["hydration"], npc["needs"]["rest"]) >= 28
        ):
            learned = next((memory for memory in reversed(npc["memories"]) if memory.get("kind") == "overheard_discourse"), None)
            if learned:
                npc["intention"] = f"discuss {learned['priority']} concern with neighbors"
                npc["reason"] = f"A proximity conversation with {learned['speaker']} made the concern part of this resident's remembered world."
        if previous != npc["intention"]:
            emitted.append({"type": "npc_intention", "actor_id": npc["id"], "payload": {"from": previous, "to": npc["intention"], "reason": npc["reason"]}})
    state["food"]["spoilage_clock"] = max(0, state["food"]["spoilage_clock"] - 1)
    if state["food"]["spoilage_clock"] == 0 and state["resources"]["raw_food"] > 0 and tick % 12 == 0:
        lost = min(4, state["resources"]["raw_food"])
        state["resources"]["raw_food"] -= lost
        emitted.append({"type": "shortage", "actor_id": "world", "payload": {"resource": "raw_food", "lost": lost, "reason": "initial provisions spoiled"}})
    if tick % 24 == 0 and state["event"]["status"] != "completed":
        emitted.extend(advance_founding_table(state, tick))
    if tick % 12 == 0 and state["event"]["status"] == "completed":
        if state["institutions"]["council"].get("current_initiative"):
            emitted.extend(_advance_civic_initiative(state, tick))
        else:
            emitted.extend(_observe_and_decide(state, tick))
    if tick % 12 == 0:
        emitted.extend(_process_material_economy(state, tick))
        emitted.append({"type": "runclock_checkpoint", "actor_id": "server", "payload": {"tick": tick, "phase": state["event"]["phase"]}})
    emitted.extend(_process_justice(state, tick))
    emitted.extend(_process_governance(state, tick))
    emitted.extend(_process_proximity_speech(state, tick))
    return emitted


def _evidence(state: Dict[str, Any], tick: int, change: str, actors: list[str], inputs: Dict[str, Any], tools: list[str], measurements: Dict[str, Any], inspector: Optional[str], causal_sources: Optional[list[str]] = None, evidence_tags: Optional[list[str]] = None) -> None:
    state["evidence"].append({"tick": tick, "change": change, "actors": actors, "inputs": inputs, "tools": tools, "measurements": measurements, "inspector": inspector, "causal_sources": list(causal_sources or []), "evidence_tags": [_evidence_tag(item) for item in evidence_tags or []]})


def _provisional_claim(state: Dict[str, Any], tick: int, actor: str, kind: str, amount: float, evidence: str, contract_id: Optional[str] = None, valuation: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    claim = {"tick": tick, "actor": actor, "kind": kind, "amount": amount, "status": "provisional", "evidence": evidence, "spendable": False}
    if contract_id:
        claim["contract_id"] = contract_id
    if valuation:
        claim["valuation"] = copy.deepcopy(valuation)
    state["economy"]["claims"].append(claim)
    state["economy"]["accounts"].setdefault(actor, 0)
    state["economy"]["accounts"][actor] += amount
    state["economy"]["accounts"]["treasury"] -= amount
    journal = {"tick": tick, "from": "treasury", "to": actor, "amount": amount, "memo": kind, "evidence": evidence, "spendable": False}
    if contract_id:
        journal["contract_id"] = contract_id
    state["economy"]["journal"].append(journal)
    return claim


def _shared_entity(state: Dict[str, Any], entity_id: str) -> Optional[Dict[str, Any]]:
    return state.get("players", {}).get(entity_id) or state.get("npcs", {}).get(entity_id)


def _shared_competence(entity: Dict[str, Any], domain: str) -> float:
    record = entity.get("competency_records", {}).get(domain, {})
    return float(record.get("demonstrated", 0.0))


def _shared_commitment(state: Dict[str, Any], entity_id: str) -> Optional[Dict[str, Any]]:
    return state.get("shared_actions", {}).get("actor_commitments", {}).get(entity_id)


def _shared_tool_record(state: Dict[str, Any], entity: Dict[str, Any], tool_id: str) -> tuple[Optional[Dict[str, Any]], str]:
    held = entity.get("equipment", {}).get(tool_id)
    if held:
        return held, "actor_equipment"
    return state["shared_actions"].get("tools", {}).get(tool_id), "shared_tool"


def _claim_shared_commitment(state: Dict[str, Any], entity_id: str, action_id: str, role: str) -> Optional[str]:
    commitments = state["shared_actions"].setdefault("actor_commitments", {})
    existing = commitments.get(entity_id)
    if existing and existing.get("action_id") != action_id:
        return existing.get("action_id")
    commitments[entity_id] = {"action_id": action_id, "since_tick": state["clock"]["tick"], "role": role}
    return None


def _release_shared_commitments(state: Dict[str, Any], record: Dict[str, Any]) -> None:
    commitments = state["shared_actions"].setdefault("actor_commitments", {})
    for entity_id, commitment in list(commitments.items()):
        if commitment.get("action_id") == record["id"]:
            del commitments[entity_id]


def _move_for_legacy(state: Dict[str, Any], entity: Dict[str, Any], target: list[int], *, survival: bool = False, owner_action_id: Optional[str] = None) -> list[int]:
    """Keep old projections from double-booking canonical participants.

    Critical food/rest movement may preempt work. The canonical record remains
    active and will resume only after its ordinary need/energy gates pass.
    """
    commitment = _shared_commitment(state, entity.get("id", ""))
    if commitment and commitment.get("action_id") != owner_action_id and not survival:
        return list(entity.get("location", target))
    return _move_toward(entity.get("location", target), target)


def _shared_perceptions(state: Dict[str, Any], entity: Dict[str, Any]) -> set[str]:
    channels = {"language"}
    if entity.get("current_region", "settlement") == "settlement":
        channels.add("spatial_layout")
    if _distance(entity.get("location", [0, 0]), state["places"]["measurement_lab"]["location"]) <= 1:
        channels.update({"surface_detail", "instrumentation"})
    if _distance(entity.get("location", [0, 0]), state["places"]["communal_kitchen"]["location"]) <= 1:
        channels.update({"heat_control", "instrumentation"})
    if _distance(entity.get("location", [0, 0]), state["places"]["meeting_hall"]["location"]) <= 1:
        channels.update({"records", "language"})
    return channels


def _shared_action_location(state: Dict[str, Any], location_id: str) -> Optional[list[int]]:
    """Resolve structural places and scenario-owned field targets uniformly."""
    place = state.get("places", {}).get(location_id)
    if place:
        return list(place.get("location", []))
    if location_id.startswith("resource_site:"):
        site = state.get("resource_sites", {}).get(location_id.split(":", 1)[1])
        return list(site.get("location", [])) if site else None
    return None


def _shared_action_perceptions(state: Dict[str, Any], entity: Dict[str, Any], record: Dict[str, Any]) -> set[str]:
    channels = _shared_perceptions(state, entity)
    target = _shared_action_location(state, record.get("location", ""))
    if target and _distance(entity.get("location", [-99, -99]), target) <= 1:
        if record.get("definition", {}).get("execution_model") == "condition_restoration":
            channels.update({"mechanical_detail", "instrumentation"})
        if record.get("definition", {}).get("execution_model") == "finite_site_extraction":
            site = state.get("resource_sites", {}).get(record.get("target_id"))
            if site and entity.get("current_region", "settlement") == site.get("region"):
                channels.update({"resource_detail", "spatial_layout"})
    return channels


def _shared_ledger(state: Dict[str, Any]) -> CausalLedger:
    events = [CausalEvent(**event) for event in state["shared_actions"]["ledger"]]
    return CausalLedger(events)


def _append_shared_action_event(state: Dict[str, Any], record: Dict[str, Any], new_state: str, actor_id: str,
                                *, inputs=None, outputs=None, evidence=None, physical=False) -> Dict[str, Any]:
    ledger = _shared_ledger(state)
    prior = ledger.events[-1] if ledger.events else None
    lineage = record.setdefault("ledger_event_ids", [])
    event = CausalEvent(
        event_id=f"{record['id']}:{len(lineage) + 1}:{new_state}", sequence=len(ledger.events) + 1,
        tick=state["clock"]["tick"], event_type="shared_action", actor_id=actor_id,
        action_id=record["id"], state=new_state, intent=record["intent"], location=record["location"],
        parent_event_ids=[lineage[-1]] if lineage else [], inputs=copy.deepcopy(inputs or {}),
        outputs=copy.deepcopy(outputs or {}), evidence=copy.deepcopy(evidence or []), physical_effect=physical,
        previous_hash=prior.event_hash if prior else "GENESIS",
    )
    ledger.append(event)
    state["shared_actions"]["ledger"].append(vars(event).copy())
    lineage.append(event.event_id)
    record["state"] = new_state
    return vars(event).copy()


def _shared_action_definition(action_type: str) -> Dict[str, Any]:
    definitions = {
        MEASUREMENT_TOOL_CALIBRATION.action_type: MEASUREMENT_TOOL_CALIBRATION,
        COMMUNAL_MEAL_PREPARATION.action_type: COMMUNAL_MEAL_PREPARATION,
        MECHANICAL_PUMP_REPAIR.action_type: MECHANICAL_PUMP_REPAIR,
    }
    definition = definitions[action_type]
    requirements = definition.requirements
    return {
        "action_type": definition.action_type,
        "requirements": {
            "materials": dict(requirements.materials), "tools": dict(requirements.tools),
            "station": requirements.station, "energy": requirements.energy,
            "competence_domain": requirements.competence_domain,
            "minimum_competence": requirements.minimum_competence,
            "perception_channels": sorted(requirements.perception_channels),
            "duration_ticks": requirements.duration_ticks,
        },
        "output_item": definition.output_item, "output_amount": definition.output_amount,
        "provisional_cu_milli": definition.provisional_cu_milli,
        "verification_tolerance": definition.verification_tolerance,
        "execution_model": definition.execution_model,
        "verification_threshold": definition.verification_threshold,
        "verifier_competence_domain": definition.verifier_competence_domain,
        "minimum_verifier_competence": definition.minimum_verifier_competence,
        "output_custody": definition.output_custody,
    }


def _site_extraction_definition(site: Dict[str, Any]) -> Dict[str, Any]:
    catalog = {
        "tree": ("timber", 2, "axe", "forestry", 4),
        "mineral": ("stone", 1, "pick", "mining", 6),
        "reeds": ("containers", 2, "farm_tools", "harvesting", 4),
    }
    resource, amount, tool, domain, energy = catalog[site["type"]]
    resource = site.get("material", resource)
    amount = int(site.get("yield_amount", amount))
    tool = site.get("required_tool", tool)
    domain = site.get("competence_domain", domain)
    energy = int(site.get("energy_cost", energy))
    return _shared_action_definition_from(site_resource_extraction(resource, min(amount, int(site.get("stock", 0))), tool, domain, energy))


def _shared_action_definition_from(definition) -> Dict[str, Any]:
    requirements = definition.requirements
    return {
        "action_type": definition.action_type,
        "requirements": {"materials": dict(requirements.materials), "tools": dict(requirements.tools), "station": requirements.station, "energy": requirements.energy, "competence_domain": requirements.competence_domain, "minimum_competence": requirements.minimum_competence, "perception_channels": sorted(requirements.perception_channels), "duration_ticks": requirements.duration_ticks},
        "output_item": definition.output_item, "output_amount": definition.output_amount,
        "provisional_cu_milli": definition.provisional_cu_milli, "verification_tolerance": definition.verification_tolerance,
        "execution_model": definition.execution_model, "verification_threshold": definition.verification_threshold,
        "verifier_competence_domain": definition.verifier_competence_domain, "minimum_verifier_competence": definition.minimum_verifier_competence,
        "output_custody": definition.output_custody,
    }


def apply_shared_action_command(state: Dict[str, Any], actor_id: str, command: Dict[str, Any]) -> Dict[str, Any]:
    """Persist one canonical action transition for either a human or AI entity."""
    shared = state["shared_actions"]
    entity = _shared_entity(state, actor_id)
    if not entity:
        return {"accepted": False, "reason": "shared actions require an existing world entity"}
    operation = str(command.get("operation", "")).strip()
    shared_action_id = str(command.get("shared_action_id", "")).strip()[:96]
    if not shared_action_id:
        return {"accepted": False, "reason": "shared_action_id is required"}
    record = shared["records"].get(shared_action_id)
    if operation == "propose":
        if record:
            return {"accepted": False, "reason": "shared action already exists"}
        action_type = command.get("action_type")
        if action_type not in {MEASUREMENT_TOOL_CALIBRATION.action_type, COMMUNAL_MEAL_PREPARATION.action_type, MECHANICAL_PUMP_REPAIR.action_type, "extract_site_resource"}:
            return {"accepted": False, "reason": "unsupported canonical action type"}
        observations = [str(item)[:120] for item in command.get("observations", []) if str(item).strip()][:16]
        if not observations:
            return {"accepted": False, "reason": "proposal requires perceived observations"}
        if action_type == MEASUREMENT_TOOL_CALIBRATION.action_type:
            target_id, location = "marked_measure", "measurement_lab"
        elif action_type == COMMUNAL_MEAL_PREPARATION.action_type:
            target_id, location = "communal_meal_batch", "communal_kitchen"
        elif action_type == MECHANICAL_PUMP_REPAIR.action_type:
            target_id = str(command.get("target_id", ""))
            location = f"resource_site:{target_id}"
            site = state.get("resource_sites", {}).get(target_id)
            if not site or not site.get("installed_pump"):
                return {"accepted": False, "reason": "pump repair requires an existing installed pump target"}
        else:
            target_id = str(command.get("target_id", ""))
            location = f"resource_site:{target_id}"
            site = state.get("resource_sites", {}).get(target_id)
            if not site or site.get("type") not in {"tree", "mineral", "reeds"}:
                return {"accepted": False, "reason": "extraction requires a supported finite resource site"}
            if site.get("stock", 0) < 1:
                return {"accepted": False, "reason": "resource site is depleted"}
        definition = _site_extraction_definition(site) if action_type == "extract_site_resource" else _shared_action_definition(action_type)
        record = {
            "id": shared_action_id, "definition": definition, "actor_id": actor_id,
            "actor_kind": "human" if actor_id in state["players"] else "ai",
            "intent": str(command.get("intent", "restore trustworthy measurement"))[:240],
            "target_id": target_id, "location": location, "observations": observations,
            "state": "proposed", "proposed_tick": state["clock"]["tick"], "ledger_event_ids": [],
            "samples": [], "output": {}, "failure_reason": None, "verifier_id": None,
            "autonomous_origin": bool(command.get("autonomous_origin", False)) and actor_id in state["npcs"],
        }
        shared["records"][shared_action_id] = record
        event = _append_shared_action_event(state, record, "proposed", actor_id, evidence=[{"kind": "perception", "ids": observations}])
        return {"accepted": True, "type": "shared_action", "operation": operation, "record": copy.deepcopy(record), "causal_event": event, "physical_change": False}
    if not record:
        return {"accepted": False, "reason": "unknown shared action"}
    if operation == "instructor_accept" and record["definition"].get("execution_model") == "instruction_session":
        if record["state"] != "proposed" or record.get("actor_id") != actor_id:
            return {"accepted": False, "reason": "proposed participating instructor acceptance required"}
        conflict = _claim_shared_commitment(state, actor_id, record["id"], "instructor")
        if conflict:
            return {"accepted": False, "reason": f"actor already committed to {conflict}"}
        event = _append_shared_action_event(state, record, "awaiting_acceptances", actor_id, evidence=[{"kind": "instructor_consent", "decision": "accepted"}])
        order = next((item for item in state["education"]["teaching_orders"] if item.get("canonical_action_id") == record["id"]), None)
        if order:
            order.setdefault("consent", {})[actor_id] = "accepted"
            order["status"] = "awaiting_learner_consent"
            order.setdefault("history", []).append({"tick": state["clock"]["tick"], "status": order["status"], "actor": actor_id})
        return {"accepted": True, "type": "shared_action", "operation": operation, "record": copy.deepcopy(record), "causal_event": event, "physical_change": False}
    if operation in {"learner_accept", "learner_refuse"} and record["definition"].get("execution_model") == "instruction_session":
        if record["state"] != "awaiting_acceptances" or record.get("target_id") != actor_id:
            return {"accepted": False, "reason": "pending participating learner acceptance required"}
        target = "accepted" if operation == "learner_accept" else "refused"
        if operation == "learner_accept":
            conflict = _claim_shared_commitment(state, actor_id, record["id"], "learner")
            if conflict:
                return {"accepted": False, "reason": f"actor already committed to {conflict}"}
        event = _append_shared_action_event(state, record, target, actor_id, evidence=[{"kind": "learner_consent", "decision": target}])
        if operation == "learner_refuse":
            _release_shared_commitments(state, record)
        order = next((item for item in state["education"]["teaching_orders"] if item.get("canonical_action_id") == record["id"]), None)
        if order:
            order.setdefault("consent", {})[actor_id] = target
            order["status"] = "accepted" if target == "accepted" else "cancelled"
            order.setdefault("history", []).append({"tick": state["clock"]["tick"], "status": order["status"], "actor": actor_id, "decision": target})
        return {"accepted": True, "type": "shared_action", "operation": operation, "record": copy.deepcopy(record), "causal_event": event, "physical_change": False}
    if operation in {"accept", "refuse"}:
        if record["state"] != "proposed" or record["actor_id"] != actor_id:
            return {"accepted": False, "reason": "only the proposed actor may accept or refuse"}
        target = "accepted" if operation == "accept" else "refused"
        if operation == "accept":
            conflict = _claim_shared_commitment(state, actor_id, record["id"], "performer")
            if conflict:
                return {"accepted": False, "reason": f"actor already committed to {conflict}"}
        event = _append_shared_action_event(state, record, target, actor_id)
        if operation == "refuse":
            _release_shared_commitments(state, record)
        if record["definition"].get("execution_model") == "instruction_session" and operation == "refuse":
            order = next((item for item in state["education"]["teaching_orders"] if item.get("canonical_action_id") == record["id"]), None)
            if order:
                order.setdefault("consent", {})[actor_id] = "refused"
                order["status"] = "cancelled"
                order.setdefault("history", []).append({"tick": state["clock"]["tick"], "status": "cancelled", "actor": actor_id, "reason": "instructor refused"})
        return {"accepted": True, "type": "shared_action", "operation": operation, "record": copy.deepcopy(record), "causal_event": event, "physical_change": False}
    if operation == "cancel":
        if record["actor_id"] != actor_id or record["state"] not in {"accepted", "reserved"}:
            return {"accepted": False, "reason": "only the participating actor may cancel accepted or reserved work"}
        reservation = shared["reservations"].pop(record["id"], None)
        if reservation:
            for tool_id in reservation.get("tools", []):
                tool, _ = _shared_tool_record(state, entity, tool_id)
                if tool and tool.get("reserved_by") == record["id"]:
                    tool["reserved_by"] = None
            station_id = reservation.get("station")
            station = shared["stations"].get(station_id) if station_id else None
            if station and station.get("reserved_by") == record["id"]:
                station["reserved_by"] = None
            target_site = state.get("resource_sites", {}).get(reservation.get("target_site"))
            if target_site and target_site.get("reserved_by") == record["id"]:
                target_site["reserved_by"] = None
        prior_state = record["state"]
        event = _append_shared_action_event(state, record, "cancelled", actor_id, evidence=[{"kind": "participant_cancellation", "prior_state": prior_state}])
        _release_shared_commitments(state, record)
        return {"accepted": True, "type": "shared_action", "operation": operation, "record": copy.deepcopy(record), "causal_event": event, "physical_change": False}
    requirements = record["definition"]["requirements"]
    if operation == "reserve":
        if record["state"] != "accepted" or record["actor_id"] != actor_id:
            return {"accepted": False, "reason": "accepted actor action required"}
        conflict = _claim_shared_commitment(state, actor_id, record["id"], "performer")
        if conflict:
            return {"accepted": False, "reason": f"actor already committed to {conflict}"}
        if record.get("supervisor_id"):
            conflict = _claim_shared_commitment(state, record["supervisor_id"], record["id"], "supervisor")
            if conflict:
                return {"accepted": False, "reason": f"supervisor already committed to {conflict}"}
        missing_channels = sorted(set(requirements["perception_channels"]) - _shared_action_perceptions(state, entity, record))
        if missing_channels:
            return {"accepted": False, "reason": f"missing authoritative perception: {', '.join(missing_channels)}"}
        if _shared_competence(entity, requirements["competence_domain"]) < requirements["minimum_competence"]:
            practice = next((item for item in state["education"]["practice_orders"] if item["id"] == record.get("practice_order_id")), None)
            supervisor = _shared_entity(state, record.get("supervisor_id", ""))
            learning = entity.get("competency_records", {}).get(requirements["competence_domain"], {})
            supervised_ready = bool(
                practice and practice.get("status") == "assigned_real_work" and supervisor
                and _shared_competence(supervisor, requirements["competence_domain"]) >= requirements["minimum_competence"]
                and _shared_action_location(state, record["location"])
                and _distance(supervisor.get("location", [-99, -99]), _shared_action_location(state, record["location"])) <= 1
                and min(float(learning.get("theory", 0)), float(learning.get("observation", 0)), float(learning.get("procedure", 0))) > 0
            )
            if not supervised_ready:
                reason = "insufficient demonstrated competence or verified supervision" if record.get("practice_order_id") else "insufficient demonstrated competence"
                return {"accepted": False, "reason": reason}
        missing = {name: amount - state["resources"].get(name, 0) for name, amount in requirements["materials"].items() if state["resources"].get(name, 0) < amount}
        if missing:
            return {"accepted": False, "reason": f"missing materials: {missing}"}
        tool_sources = {}
        for tool_id, minimum in requirements["tools"].items():
            tool, source = _shared_tool_record(state, entity, tool_id)
            if not tool or tool.get("condition", 0) < minimum or tool.get("reserved_by") not in {None, shared_action_id}:
                return {"accepted": False, "reason": f"tool unavailable: {tool_id}"}
            tool_sources[tool_id] = source
        station = shared["stations"].get(requirements["station"]) if requirements.get("station") else None
        if requirements.get("station"):
            if not station or station.get("reserved_by") not in {None, shared_action_id}:
                return {"accepted": False, "reason": f"station unavailable: {requirements['station']}"}
            place = state.get("places", {}).get(station.get("place"), {})
            if place.get("status") not in {"available", "operational"}:
                return {"accepted": False, "reason": f"facility unavailable: {station.get('place')}"}
        if entity.get("energy", 0) < requirements["energy"]:
            return {"accepted": False, "reason": "insufficient energy"}
        target_site = state.get("resource_sites", {}).get(record.get("target_id")) if record["definition"].get("execution_model") == "finite_site_extraction" else None
        if target_site:
            if target_site.get("stock", 0) < record["definition"]["output_amount"]:
                return {"accepted": False, "reason": "resource site no longer contains the proposed finite yield"}
            if target_site.get("reserved_by") not in {None, shared_action_id}:
                return {"accepted": False, "reason": f"resource site reserved by {target_site['reserved_by']}"}
        for tool_id in requirements["tools"]:
            tool, _ = _shared_tool_record(state, entity, tool_id)
            tool["reserved_by"] = shared_action_id
        if station:
            station["reserved_by"] = shared_action_id
        if target_site:
            target_site["reserved_by"] = shared_action_id
        reservation = {"materials": copy.deepcopy(requirements["materials"]), "tools": sorted(requirements["tools"]), "tool_sources": tool_sources, "station": requirements["station"], "target_site": target_site["id"] if target_site else None, "actor_id": actor_id}
        shared["reservations"][shared_action_id] = reservation
        record["reserved_tick"] = state["clock"]["tick"]
        event = _append_shared_action_event(state, record, "reserved", actor_id, inputs=reservation)
        return {"accepted": True, "type": "shared_action", "operation": operation, "record": copy.deepcopy(record), "causal_event": event, "physical_change": False}
    if operation == "execute":
        if record["state"] != "reserved" or record["actor_id"] != actor_id:
            return {"accepted": False, "reason": "reserved actor action required"}
        samples = command.get("samples", [])
        if not isinstance(samples, list) or len(samples) > 32:
            return {"accepted": False, "reason": "ordered samples must be a bounded list"}
        normalized = []
        for sample in samples:
            if not isinstance(sample, dict):
                continue
            if record["definition"].get("execution_model") == "instruction_session":
                source_event_id, claim = sample.get("source_event_id"), sample.get("claim")
                if isinstance(source_event_id, str) and source_event_id.strip() and isinstance(claim, str) and claim.strip():
                    normalized.append({"source_event_id": source_event_id[:160], "claim": claim[:240]})
            elif record["definition"].get("execution_model") == "thermal_batch":
                temperature, minutes = sample.get("temperature_c"), sample.get("duration_minutes")
                if isinstance(temperature, (int, float)) and isinstance(minutes, (int, float)) and math.isfinite(temperature) and math.isfinite(minutes) and minutes > 0:
                    normalized.append({"temperature_c": round(float(temperature), 4), "duration_minutes": round(float(minutes), 4)})
            elif record["definition"].get("execution_model") == "condition_restoration":
                before, after = sample.get("condition_before"), sample.get("condition_after")
                if all(isinstance(value, (int, float)) and math.isfinite(value) for value in (before, after)):
                    normalized.append({"condition_before": round(float(before), 4), "condition_after": round(float(after), 4)})
            elif record["definition"].get("execution_model") == "finite_site_extraction":
                stock_before, observed_yield = sample.get("stock_before"), sample.get("observed_yield")
                if all(isinstance(value, (int, float)) and math.isfinite(value) for value in (stock_before, observed_yield)):
                    normalized.append({"stock_before": int(stock_before), "observed_yield": int(observed_yield)})
            else:
                reading = sample.get("reading")
                if isinstance(reading, (int, float)) and math.isfinite(reading):
                    normalized.append({"reading": round(float(reading), 6)})
        record["samples"] = normalized
        record["execution_started_tick"] = state["clock"]["tick"]
        record["execution_due_tick"] = state["clock"]["tick"] + requirements["duration_ticks"]
        event = _append_shared_action_event(state, record, "in_progress", actor_id, evidence=[{"kind": "ordered_samples", "samples": normalized}])
        return {"accepted": True, "type": "shared_action", "operation": operation, "record": copy.deepcopy(record), "causal_event": event, "physical_change": False}
    if operation == "verify":
        if record["state"] != "submitted":
            return {"accepted": False, "reason": "submitted action required"}
        if record["actor_id"] == actor_id:
            return {"accepted": False, "reason": "verification must be independent"}
        if record["definition"].get("execution_model") == "instruction_session":
            if record.get("target_id") != actor_id:
                return {"accepted": False, "reason": "only the participating learner may acknowledge instruction"}
            if not {"language", "records"}.issubset(_shared_perceptions(state, entity)):
                return {"accepted": False, "reason": "learner did not perceive the instruction and source record"}
            record["verifier_id"] = actor_id
            event = _append_shared_action_event(state, record, "verified", actor_id, evidence=[{"kind": "learner_acknowledgement", "source_event_ids": record["output"].get("source_event_ids", [])}])
            return {"accepted": True, "type": "shared_action", "operation": operation, "record": copy.deepcopy(record), "causal_event": event, "physical_change": False}
        verifier_domain = record["definition"].get("verifier_competence_domain") or requirements["competence_domain"]
        minimum_verifier = record["definition"].get("minimum_verifier_competence", 0.1)
        verifier_channel = "resource_detail" if record["definition"].get("execution_model") == "finite_site_extraction" else "instrumentation"
        if verifier_channel not in _shared_action_perceptions(state, entity, record) or _shared_competence(entity, verifier_domain) < minimum_verifier:
            return {"accepted": False, "reason": "verifier lacks measured competence or target perception"}
        if record["definition"].get("execution_model") == "thermal_batch":
            passed = record["output"].get("safety", 0.0) >= record["definition"].get("verification_threshold", 0.0)
            verification_evidence = {"kind": "independent_safety_check", "threshold": record["definition"].get("verification_threshold", 0.0), "observed_safety": record["output"].get("safety")}
        elif record["definition"].get("execution_model") == "condition_restoration":
            passed = record["output"].get("condition_after", 0.0) >= record["definition"].get("verification_threshold", 0.0)
            verification_evidence = {"kind": "independent_condition_check", "threshold": record["definition"].get("verification_threshold", 0.0), "observed_condition": record["output"].get("condition_after")}
        elif record["definition"].get("execution_model") == "finite_site_extraction":
            passed = bool(record["output"].get("conserved")) and record["output"].get("observed_yield") == record["output"].get("yield")
            verification_evidence = {"kind": "independent_stock_and_yield_check", "stock_before": record["output"].get("stock_before"), "stock_after": record["output"].get("stock_after"), "yield": record["output"].get("yield"), "observed_yield": record["output"].get("observed_yield"), "conserved": record["output"].get("conserved")}
        else:
            passed = record["output"].get("spread", float("inf")) <= record["definition"]["verification_tolerance"]
            verification_evidence = {"kind": "independent_check", "tolerance": record["definition"]["verification_tolerance"], "observed_spread": record["output"].get("spread")}
        target = "verified" if passed else "needs_rework"
        record["verifier_id"] = actor_id
        event = _append_shared_action_event(state, record, target, actor_id, evidence=[verification_evidence])
        if target == "needs_rework":
            _release_shared_commitments(state, record)
        performer = _shared_entity(state, record["actor_id"])
        if passed:
            performer_domain = requirements["competence_domain"]
            competence = performer.setdefault("competency_records", {}).setdefault(performer_domain, {"demonstrated": 0.0, "provenance": []})
            if record.get("practice_order_id"):
                record["supervised_learning"] = {"domain": performer_domain, "demonstrated_before": competence["demonstrated"], "demonstrated_after": round(max(0.12, competence["demonstrated"] + 0.04), 4), "evidence_event": event["event_id"]}
            else:
                competence["demonstrated"] = round(min(1.0, competence["demonstrated"] + 0.02), 4)
                competence["provenance"].append(event["event_id"])
            verifier_competence = entity.setdefault("competency_records", {}).setdefault(verifier_domain, {"demonstrated": 0.0, "provenance": []})
            verifier_competence["demonstrated"] = round(min(1.0, verifier_competence["demonstrated"] + 0.01), 4)
            verifier_competence["provenance"].append(event["event_id"])
        for participant, role in ((performer, "performed"), (entity, "inspected")):
            participant.setdefault("memories", []).append({"tick": state["clock"]["tick"], "kind": "subjective_causal_memory", "event_id": event["event_id"], "objective_hash": event["event_hash"], "confidence": 0.85 if role == "performed" else 0.95, "text": f"I {role} {record['intent']}; review was {target}."})
        return {"accepted": True, "type": "shared_action", "operation": operation, "record": copy.deepcopy(record), "causal_event": event, "physical_change": False}
    if operation == "commission":
        if record["state"] != "verified":
            return {"accepted": False, "reason": "verified action required"}
        if record.get("verifier_id") != actor_id:
            return {"accepted": False, "reason": "only the independent verifier may commission this output"}
        item, amount = record["definition"]["output_item"], record["definition"]["output_amount"]
        held = shared["unverified_outputs"].setdefault(record["actor_id"], {}).pop(item, 0)
        if held != amount:
            return {"accepted": False, "reason": "verified output custody is inconsistent"}
        if record["definition"].get("output_custody") == "actor_inventory":
            performer_inventory = _shared_entity(state, record["actor_id"]).setdefault("inventory", {})
            performer_inventory[item] = performer_inventory.get(item, 0) + held
        else:
            outputs = shared["commissioned_outputs"].setdefault(record["actor_id"], {})
            outputs[item] = outputs.get(item, 0) + held
        if record["definition"].get("execution_model") == "instruction_session":
            learner = _shared_entity(state, record["target_id"])
            teacher = _shared_entity(state, record["actor_id"])
            domain = record["definition"]["requirements"]["competence_domain"]
            teacher_level = _shared_competence(teacher, domain)
            learning = learner.setdefault("competency_records", {}).setdefault(domain, {"demonstrated": 0.0, "provenance": []})
            learning.setdefault("theory", 0.0); learning.setdefault("observation", 0.0); learning.setdefault("procedure", 0.0)
            before_demonstrated = float(learning.get("demonstrated", 0.0))
            learning["theory"] = round(min(teacher_level, learning["theory"] + teacher_level * 0.08), 4)
            learning["observation"] = round(min(teacher_level, learning["observation"] + teacher_level * 0.06), 4)
            learning["procedure"] = round(min(teacher_level, learning["procedure"] + teacher_level * 0.04), 4)
            learning["provenance"].append(record["ledger_event_ids"][-1])
            record["output"]["learning"] = {"domain": domain, "demonstrated_before": before_demonstrated, "demonstrated_after": before_demonstrated, "theory": learning["theory"], "observation": learning["observation"], "procedure": learning["procedure"], "requires_verified_practice": True}
            teacher.setdefault("memories", []).append({"tick": state["clock"]["tick"], "kind": "subjective_causal_memory", "event_id": record["ledger_event_ids"][-1], "text": f"I taught {learner.get('name', learner['id'])} from {', '.join(record['output'].get('source_event_ids', []))}."})
            learner.setdefault("memories", []).append({"tick": state["clock"]["tick"], "kind": "subjective_causal_memory", "event_id": record["ledger_event_ids"][-1], "text": f"I received instruction in {domain}; I still need verified practice."})
        if record["definition"]["action_type"] == "calibrate_measurement_tool":
            shared["tools"]["marked_measure"]["condition"] = 0.98
        if record["definition"]["action_type"] == COMMUNAL_MEAL_PREPARATION.action_type:
            portions = held
            batch = {
                "id": f"meal-batch-{len(state['cooking']['meal_batches']) + 1}", "work_order_id": record["id"],
                "canonical_action_id": record["id"], "cook": record["actor_id"], "prepared_tick": record.get("submitted_tick"),
                "inspected_tick": state["clock"]["tick"], "inspector": actor_id, "portions": portions,
                "remaining_portions": portions, "inputs": copy.deepcopy(record["definition"]["requirements"]["materials"]),
                "safety": record["output"].get("safety"), "quality": record["output"].get("quality"),
                "status": "accepted", "accepted": True, "recipe": "Founders provision stew", "preservation": record.get("preservation", "none"),
            }
            preservation_gain = state["cooking"]["preservation_program"].get("shelf_life_gain_ticks", 0) if batch["preservation"] != "none" else 0
            shelf_life = 24 + round(state["food"].get("storage_quality", 0) * 24) + (12 if state["places"]["dry_storage"].get("status") == "operational" else 0) + preservation_gain
            batch.update({"expires_tick": state["clock"]["tick"] + shelf_life, "shelf_life_ticks": shelf_life})
            state["cooking"]["meal_batches"].append(batch)
            state["resources"]["safe_meals"] += portions
            order = next((item for item in state["cooking"]["work_orders"] if item.get("canonical_action_id") == record["id"]), None)
            if order:
                order.update({"status": "completed", "meal_batch_id": batch["id"], "completed_tick": state["clock"]["tick"], "inspector": actor_id})
                order.setdefault("history", []).append({"tick": state["clock"]["tick"], "status": "completed", "batch_id": batch["id"], "accepted_portions": portions})
            if not any(recipe["name"] == batch["recipe"] for recipe in state["culture"]["recipes"]):
                state["culture"]["recipes"].append({"name": batch["recipe"], "author": record["actor_id"], "first_served_tick": state["clock"]["tick"], "evidence_action_id": record["id"]})
            demand = next((item for item in shared["demands"] if item.get("action_id") == record["id"]), None)
            if demand:
                demand.update({"status": "resolved", "resolved_tick": state["clock"]["tick"], "reason": "verified meal portions entered communal custody"})
        if record["definition"]["action_type"] == MECHANICAL_PUMP_REPAIR.action_type:
            site = state["resource_sites"].get(record["target_id"])
            order = next((item for item in state["institutions"]["governance"]["maintenance_orders"] if item.get("canonical_action_id") == record["id"]), None)
            if not site or not site.get("installed_pump") or not order:
                return {"accepted": False, "reason": "repair target or projected maintenance order disappeared"}
            pump = site["installed_pump"]
            before = pump["condition"]
            pump["condition"] = record["output"]["condition_after"]
            pump["status"] = "operational"
            pump["maintenance_due"] = False
            pump["maintenance_history"].append({"tick": state["clock"]["tick"], "actor": record["actor_id"], "before": before, "after": pump["condition"], "input_source": "canonical reservation", "order_id": order["id"], "causal_action_id": record["id"], "verified_by": actor_id})
            order.update({"status": "completed", "completed_tick": state["clock"]["tick"], "completed_by": record["actor_id"], "verified_by": actor_id})
            for recovery in [*order.get("blockers", []), *order.get("depletion_notices", [])]:
                if recovery.get("status") == "unresolved":
                    recovery.update({"status": "recovered", "recovered_tick": state["clock"]["tick"]})
            for failure in state.get("failures", []):
                if failure.get("order_id") == order["id"] and not failure.get("recovered"):
                    failure.update({"recovered": True, "recovered_tick": state["clock"]["tick"]})
        if record["definition"]["action_type"] == "extract_site_resource":
            for extraction_record in reversed(state["environment"].get("extraction_history", [])):
                if extraction_record.get("action_id") == record["id"]:
                    extraction_record.update({"status": "commissioned", "verified_by": actor_id, "commissioned_tick": state["clock"]["tick"]})
                    break
            demand = next((item for item in shared["demands"] if item.get("action_id") == record["id"]), None)
            if demand:
                demand.update({"status": "awaiting_transport", "extracted_tick": state["clock"]["tick"], "actor_inventory": {record["definition"]["output_item"]: held}, "reason": "verified material remains in performer custody until a transport action deposits it"})
        if record.get("supervised_learning"):
            learning = record["supervised_learning"]
            performer = _shared_entity(state, record["actor_id"])
            competence = performer.setdefault("competency_records", {}).setdefault(learning["domain"], {"demonstrated": 0.0, "provenance": []})
            competence["demonstrated"] = learning["demonstrated_after"]
            competence["provenance"].append(learning["evidence_event"])
            practice = next(item for item in state["education"]["practice_orders"] if item["id"] == record["practice_order_id"])
            practice.update({"status": "completed", "completed_tick": state["clock"]["tick"], "verified_work_order_id": record["id"], "demonstrated": competence["demonstrated"], "evidence": learning["evidence_event"]})
            practice["history"].append({"tick": state["clock"]["tick"], "status": "completed", "demonstrated": competence["demonstrated"], "evidence": learning["evidence_event"]})
            supervisor = _shared_entity(state, record.get("supervisor_id", ""))
            if supervisor:
                supervisor.setdefault("memories", []).append({"tick": state["clock"]["tick"], "kind": "subjective_causal_memory", "event_id": learning["evidence_event"], "text": f"I supervised {record['actor_id']} through verified {learning['domain']} practice."})
            _remember_consequence(state, state["clock"]["tick"], f"instruction-recorded:{record['actor_id']}:{learning['domain']}:practice-required", f"competency-demonstrated:{record['actor_id']}:{learning['domain']}:{competence['demonstrated']}", [item for item in [record["actor_id"], record.get("supervisor_id"), record["verifier_id"]] if item])
        value = int(record["definition"]["provisional_cu_milli"])
        accounts = shared["valuation_accounts_milli"]
        if value:
            accounts["treasury"] -= value
            accounts[record["actor_id"]] = accounts.get(record["actor_id"], 0) + value
        commission_outputs = {"item": item, "amount": held, "provisional_cu_milli": value}
        if record["definition"].get("execution_model") == "instruction_session":
            commission_outputs["learning"] = copy.deepcopy(record["output"].get("learning"))
        event = _append_shared_action_event(state, record, "commissioned", actor_id, outputs=commission_outputs, physical=record["definition"].get("execution_model") != "instruction_session")
        _release_shared_commitments(state, record)
        if value:
            shared["valuation_claims"].append({"action_id": record["id"], "actor_id": record["actor_id"], "amount_milli": value, "spendable": False, "evidence_event": record["ledger_event_ids"][-2]})
        if record["definition"]["action_type"] in {MEASUREMENT_TOOL_CALIBRATION.action_type, COMMUNAL_MEAL_PREPARATION.action_type, MECHANICAL_PUMP_REPAIR.action_type, "extract_site_resource"}:
            _create_instruction_opportunity(
                state, state["clock"]["tick"], record["definition"]["requirements"]["competence_domain"],
                record["actor_id"], record["ledger_event_ids"][-2], record["id"],
            )
        return {"accepted": True, "type": "shared_action", "operation": operation, "record": copy.deepcopy(record), "causal_event": event, "physical_change": True}
    return {"accepted": False, "reason": "unsupported shared action operation"}


def _process_shared_action_demand(state: Dict[str, Any], tick: int) -> list[Dict[str, Any]]:
    """Turn measured infrastructure degradation into work without a quest script."""
    shared = state["shared_actions"]
    tool = shared["tools"]["marked_measure"]
    demand_id = "need:measurement-tool-calibration:marked_measure"
    demand = next((item for item in shared["demands"] if item["id"] == demand_id), None)
    active = next((item for item in shared["records"].values() if item["definition"]["action_type"] == "calibrate_measurement_tool" and item["state"] not in {"refused", "cancelled", "failed", "rejected", "retired", "lost", "commissioned"}), None)
    if tool["condition"] >= 0.7:
        if demand and demand["status"] != "resolved":
            demand.update({"status": "resolved", "resolved_tick": tick, "reason": "verified calibration restored tool condition"})
        return []
    if not demand:
        demand = {"id": demand_id, "kind": "maintenance", "target_id": "marked_measure", "created_tick": tick, "status": "unassigned", "cause": {"condition": tool["condition"], "threshold": 0.7}, "action_id": None}
        shared["demands"].append(demand)
    if active:
        demand.update({"status": "action_active", "action_id": active["id"]})
        return []
    practice = next((item for item in state["education"]["practice_orders"] if item["status"] == "awaiting_real_work" and item["domain"] == "measurement"), None)
    supervised = False
    if practice:
        learner, supervisor = _shared_entity(state, practice["learner"]), _shared_entity(state, practice["supervisor"])
        supervised = bool(learner and supervisor and _shared_competence(supervisor, "measurement") >= MEASUREMENT_TOOL_CALIBRATION.requirements.minimum_competence)
    candidates = []
    for entity_id, entity in {**state["npcs"], **state["players"]}.items():
        competence = _shared_competence(entity, "measurement")
        if competence >= 0.1 and set(MEASUREMENT_TOOL_CALIBRATION.requirements.perception_channels).issubset(_shared_perceptions(state, entity)):
            candidates.append((competence, entity_id))
    if not candidates and not supervised:
        demand.update({"status": "blocked_competence", "reason": "no perceived entity has demonstrated measurement competence"})
        return [{"type": "shared_action_demand_blocked", "actor_id": "settlement", "payload": copy.deepcopy(demand)}]
    actor_id = practice["learner"] if supervised else max(candidates, key=lambda item: (item[0], item[1]))[1]
    action_id = f"calibration-demand-{len(shared['records']) + 1}"
    result = apply_shared_action_command(state, actor_id, {
        "operation": "propose", "shared_action_id": action_id,
        "action_type": "calibrate_measurement_tool", "intent": "restore trustworthy settlement measurement",
        "autonomous_origin": True,
        "observations": [f"marked_measure condition {tool['condition']:.2f} below verified threshold 0.70"],
    })
    if supervised:
        record = shared["records"][action_id]
        record.update({"practice_order_id": practice["id"], "supervisor_id": practice["supervisor"]})
        practice.update({"status": "assigned_real_work", "work_order_id": action_id, "assigned_tick": tick})
        practice["history"].append({"tick": tick, "status": "assigned_real_work", "work_order_id": action_id})
    demand.update({"status": "proposed", "assigned_to": actor_id, "action_id": action_id, "reason": "qualified perceived maintainer selected by demonstrated competence"})
    return [{"type": "shared_action_demand_proposed", "actor_id": actor_id, "payload": {"demand": copy.deepcopy(demand), "record": result["record"]}}]


def _process_shared_meal_demand(state: Dict[str, Any], tick: int) -> list[Dict[str, Any]]:
    """Translate observed hunger into canonical meal work, not a scripted quest."""
    shared = state["shared_actions"]
    if not shared.get("canonical_cooking", False):
        return []
    shortage = next((item for item in state["survival"]["shortages"] if item.get("kind") == "safe_meal" and item.get("status") == "unresolved"), None)
    if not shortage:
        return []
    demand_id = f"need:communal-meal:{shortage['id']}"
    demand = next((item for item in shared["demands"] if item["id"] == demand_id), None)
    active = next((record for record in shared["records"].values() if record["definition"]["action_type"] == COMMUNAL_MEAL_PREPARATION.action_type and record["state"] not in {"refused", "failed", "needs_rework", "commissioned"}), None)
    if active:
        if demand:
            demand.update({"status": "action_active", "action_id": active["id"]})
        return []
    if demand and demand.get("status") == "resolved":
        return []
    practice = next((item for item in state["education"]["practice_orders"] if item["status"] == "awaiting_real_work" and item["domain"] == "cooking"), None)
    supervised = False
    if practice:
        learner, supervisor = _shared_entity(state, practice["learner"]), _shared_entity(state, practice["supervisor"])
        supervised = bool(learner and supervisor and _shared_competence(supervisor, "cooking") >= COMMUNAL_MEAL_PREPARATION.requirements.minimum_competence)
    candidates = [(_shared_competence(npc, "cooking"), npc_id) for npc_id, npc in state["npcs"].items() if _shared_competence(npc, "cooking") >= COMMUNAL_MEAL_PREPARATION.requirements.minimum_competence]
    if not candidates and not supervised:
        if not demand:
            demand = {"id": demand_id, "kind": "survival_production", "target_id": "safe_meals", "created_tick": tick}
            shared["demands"].append(demand)
        demand.update({"status": "blocked_competence", "reason": "no entity has demonstrated cooking competence"})
        return [{"type": "shared_meal_demand_blocked", "actor_id": "settlement", "payload": copy.deepcopy(demand)}]
    actor_id = practice["learner"] if supervised else max(candidates, key=lambda item: (item[0], item[1]))[1]
    action_id = f"meal-demand-{len(shared['records']) + 1}"
    result = apply_shared_action_command(state, actor_id, {
        "operation": "propose", "shared_action_id": action_id, "action_type": COMMUNAL_MEAL_PREPARATION.action_type,
        "intent": "produce an independently verified communal meal", "autonomous_origin": True,
        "observations": [f"safe-meal shortage {shortage['id']} affects {len(shortage['affected'])} residents"],
    })
    record = shared["records"][action_id]
    if supervised:
        record.update({"practice_order_id": practice["id"], "supervisor_id": practice["supervisor"]})
        practice.update({"status": "assigned_real_work", "work_order_id": action_id, "assigned_tick": tick})
        practice["history"].append({"tick": tick, "status": "assigned_real_work", "work_order_id": action_id})
    preservation = state["cooking"]["preservation_program"].get("method", "none") if state["cooking"]["preservation_program"].get("status") == "active" else "none"
    if preservation != "none":
        record["definition"]["requirements"]["materials"]["containers"] = 1
        record["definition"]["requirements"]["materials"]["fuel"] += 1
        record["preservation"] = preservation
    if not demand:
        demand = {"id": demand_id, "kind": "survival_production", "target_id": "safe_meals", "created_tick": tick}
        shared["demands"].append(demand)
    demand.update({"status": "proposed", "assigned_to": actor_id, "action_id": action_id, "shortage_id": shortage["id"], "reason": "hunger created verified production demand"})
    shortage["cooking_order_id"] = action_id
    required_inputs = dict(record["definition"]["requirements"]["materials"])
    missing = {name: amount - state["resources"].get(name, 0) for name, amount in required_inputs.items() if state["resources"].get(name, 0) < amount}
    initial_status = "blocked_inputs" if missing else "proposed"
    state["cooking"]["work_orders"].append({
        "id": action_id, "canonical_action_id": action_id, "status": initial_status, "created_tick": tick,
        "shortage_id": shortage["id"], "cook": actor_id, "inspector": None,
        "portions": COMMUNAL_MEAL_PREPARATION.output_amount,
        "required_inputs": required_inputs, "missing": missing,
        "preservation": preservation, "history": [{"tick": tick, "status": initial_status, "cause": f"food-shortage:{shortage['id']}", "missing": missing}],
    })
    if missing:
        _remember_consequence(state, tick, f"communal-cooking-work:{action_id}", f"cooking-input-shortage:{','.join(sorted(missing))}", [actor_id, "dev"])
    return [
        {"type": "shared_meal_demand_proposed", "actor_id": actor_id, "payload": {"demand": copy.deepcopy(demand), "record": copy.deepcopy(record)}},
        {"type": "cooking_work_proposed", "actor_id": actor_id, "payload": {"order_id": action_id, "portions": record["definition"]["output_amount"], "required_inputs": required_inputs}},
    ]


def _process_shared_actions(state: Dict[str, Any], tick: int) -> list[Dict[str, Any]]:
    emitted = []
    shared = state["shared_actions"]
    for record in sorted(shared["records"].values(), key=lambda item: item["id"]):
        if record["state"] != "in_progress" or tick < record.get("execution_due_tick", tick + 1):
            continue
        entity = _shared_entity(state, record["actor_id"])
        requirements = record["definition"]["requirements"]
        reservation = shared["reservations"].pop(record["id"], None)
        if not entity or not reservation:
            record["failure_reason"] = "reservation lost before execution completed"
            event = _append_shared_action_event(state, record, "failed", record["actor_id"], outputs={"reason": record["failure_reason"]}, physical=True)
            _release_shared_commitments(state, record)
            emitted.append({"type": "shared_action_failed", "actor_id": record["actor_id"], "payload": {"action_id": record["id"], "event": event}})
            continue
        for name, amount in requirements["materials"].items():
            state["resources"][name] -= amount
        entity["energy"] = round(entity.get("energy", 0) - requirements["energy"], 2)
        for tool_id in requirements["tools"]:
            tool, _ = _shared_tool_record(state, entity, tool_id)
            tool["condition"] = round(max(0.0, tool["condition"] - 0.01), 4)
            tool["reserved_by"] = None
        if requirements.get("station"):
            shared["stations"][requirements["station"]]["reserved_by"] = None
        execution_model = record["definition"].get("execution_model", "measurement_series")
        thermal = execution_model == "thermal_batch"
        instruction = execution_model == "instruction_session"
        restoration = execution_model == "condition_restoration"
        extraction = execution_model == "finite_site_extraction"
        target_site = state.get("resource_sites", {}).get(reservation.get("target_site")) if reservation else None
        if target_site and target_site.get("reserved_by") == record["id"]:
            target_site["reserved_by"] = None
        observations = record.get("samples", [])
        if not observations:
            record["failure_reason"] = "no source-grounded instruction segments" if instruction else "no measured thermal history" if thermal else "no condition measurements" if restoration else "no stock and yield observation" if extraction else "no measurable samples"
            event = _append_shared_action_event(state, record, "failed", record["actor_id"], outputs={"reason": record["failure_reason"]}, physical=True)
            _release_shared_commitments(state, record)
            emitted.append({"type": "shared_action_failed", "actor_id": record["actor_id"], "payload": {"action_id": record["id"], "event": event}})
            continue
        if instruction:
            record["output"] = {"segment_count": len(observations), "source_event_ids": sorted({sample["source_event_id"] for sample in observations}), "acknowledgement_required_from": record["target_id"]}
            evidence = [{"kind": "source_grounded_instruction", "segments": copy.deepcopy(observations)}]
        elif thermal:
            lethal_exposure = sum(max(0.0, sample["temperature_c"] - 55.0) * sample["duration_minutes"] for sample in observations)
            scorch_exposure = sum(max(0.0, sample["temperature_c"] - 100.0) * sample["duration_minutes"] for sample in observations)
            record["output"] = {
                "sample_count": len(observations), "safety": round(min(0.98, 0.52 + min(1.0, lethal_exposure / 300.0) * 0.46), 4),
                "quality": round(max(0.0, 1.0 - scorch_exposure / 300.0), 4),
                "peak_temperature_c": round(max(sample["temperature_c"] for sample in observations), 3),
                "heated_minutes": round(sum(sample["duration_minutes"] for sample in observations), 3),
            }
            evidence = [{"kind": "thermal_history", "observations": copy.deepcopy(observations)}]
        elif restoration:
            site = state["resource_sites"].get(record["target_id"])
            pump = site.get("installed_pump") if site else None
            before = float(pump.get("condition", 0.0)) if pump else float(observations[0]["condition_before"])
            tool_condition = state["shared_actions"]["tools"]["maintenance_wrench"]["condition"]
            after = round(min(1.0, before + 0.62 * tool_condition), 4)
            record["output"] = {"condition_before": round(before, 4), "condition_after": after, "measured_samples": len(observations)}
            evidence = [{"kind": "condition_restoration_record", "observations": copy.deepcopy(observations), "computed_condition_after": after}]
        elif extraction:
            site = state.get("resource_sites", {}).get(record["target_id"])
            if not site:
                record["failure_reason"] = "finite resource site disappeared"
                event = _append_shared_action_event(state, record, "failed", record["actor_id"], outputs={"reason": record["failure_reason"]}, physical=False)
                _release_shared_commitments(state, record)
                emitted.append({"type": "shared_action_failed", "actor_id": record["actor_id"], "payload": {"action_id": record["id"], "event": event}})
                continue
            stock_before = int(site.get("stock", 0))
            amount = min(int(record["definition"]["output_amount"]), stock_before)
            if amount < 1:
                record["failure_reason"] = "finite resource depleted before execution"
                event = _append_shared_action_event(state, record, "failed", record["actor_id"], outputs={"reason": record["failure_reason"]}, physical=False)
                _release_shared_commitments(state, record)
                emitted.append({"type": "shared_action_failed", "actor_id": record["actor_id"], "payload": {"action_id": record["id"], "event": event}})
                continue
            resource = record["definition"]["output_item"]
            region = state["environment"]["regions"][site["region"]]
            frontier_source = bool(site.get("frontier_tile"))
            regional_before = int(region.get("stocks", {}).get(resource, 0)) if not frontier_source else stock_before
            if not frontier_source and regional_before < amount:
                record["failure_reason"] = "regional stock ledger cannot conserve proposed yield"
                event = _append_shared_action_event(state, record, "failed", record["actor_id"], outputs={"reason": record["failure_reason"]}, physical=False)
                _release_shared_commitments(state, record)
                emitted.append({"type": "shared_action_failed", "actor_id": record["actor_id"], "payload": {"action_id": record["id"], "event": event}})
                continue
            site["stock"] -= amount
            if not frontier_source:
                region["stocks"][resource] -= amount
            else:
                key = site["frontier_tile"]
                modification = state["terrain_modifications"].setdefault(key, {})
                if site.get("frontier_mode") == "harvest":
                    modification["surface_stock"] = int(site["stock"])
                else:
                    layer_index = str(site.get("frontier_layer", 0))
                    modification.setdefault("layer_stocks", {})[layer_index] = int(site["stock"])
                    modification["excavation_depth_cm"] = int(modification.get("excavation_depth_cm", 0)) + 40
                    if modification["excavation_depth_cm"] >= 80:
                        modification.update({"passable": False, "travel_cost_milli": 4_000})
            observed_yield = int(observations[0]["observed_yield"])
            regional_after = int(region.get("stocks", {}).get(resource, 0)) if not frontier_source else int(site["stock"])
            record["output"] = {"resource": resource, "yield": amount, "observed_yield": observed_yield, "stock_before": stock_before, "stock_after": int(site["stock"]), "regional_before": regional_before, "regional_after": regional_after, "conserved": stock_before - int(site["stock"]) == amount and (frontier_source or regional_before - regional_after == amount), "frontier_tile": site.get("frontier_tile")}
            evidence = [{"kind": "finite_site_stock_change", "site_id": site["id"], "measurements": copy.deepcopy(record["output"])}]
            site.setdefault("history", []).append({"tick": tick, "actor": record["actor_id"], "operation": "canonical_extraction_submitted", "outputs": copy.deepcopy(record["output"]), "causal_action_id": record["id"]})
            state["environment"].setdefault("extraction_history", []).append({"tick": tick, "actor": record["actor_id"], "site_id": site["id"], "resource": resource, "amount": amount, "action_id": record["id"], "status": "awaiting_verification"})
            _update_material_signal(state, resource, tick, f"canonical-site-extraction:{record['id']}")
        else:
            readings = [sample["reading"] for sample in observations]
            spread = round(max(readings) - min(readings), 6)
            record["output"] = {"sample_count": len(readings), "spread": spread, "mean": round(sum(readings) / len(readings), 6)}
            evidence = [{"kind": "measurement_series", "readings": readings}]
        item = record["definition"]["output_item"]
        shared["unverified_outputs"].setdefault(record["actor_id"], {})[item] = record["definition"]["output_amount"]
        record["submitted_tick"] = tick
        event = _append_shared_action_event(state, record, "submitted", record["actor_id"], outputs=record["output"], evidence=evidence, physical=True)
        evidence_tag = "source-grounded instruction" if instruction else "thermal history" if thermal else "ordered measurement samples"
        _evidence(state, tick, f"shared action {record['id']} submitted", [record["actor_id"]], requirements["materials"], list(requirements["tools"]), record["output"], None, [record["ledger_event_ids"][0]], [evidence_tag])
        emitted.append({"type": "shared_action_submitted", "actor_id": record["actor_id"], "payload": {"action_id": record["id"], "event": event}})
    return emitted


def _process_shared_extraction_demand(state: Dict[str, Any], tick: int) -> list[Dict[str, Any]]:
    """Let measured communal shortages create finite, actor-custodied gathering."""
    catalog = {
        "timber": {"target": 18, "site_type": "tree", "actor": "cal", "tool": "axe"},
        "stone": {"target": 14, "site_type": "mineral", "actor": "orin", "tool": "pick"},
        "containers": {"target": 10, "site_type": "reeds", "actor": "nyra", "tool": "farm_tools"},
    }
    shared = state["shared_actions"]
    candidates = []
    for resource, rule in catalog.items():
        deficit = rule["target"] - state["resources"].get(resource, 0)
        if deficit > 0:
            candidates.append((deficit / rule["target"], resource, rule))
    if not candidates:
        return []
    _, resource, rule = max(candidates, key=lambda item: (item[0], item[1]))
    demand_id = f"need:finite-extraction:{resource}"
    demand = next((item for item in shared["demands"] if item["id"] == demand_id and item.get("status") != "resolved"), None)
    if demand and demand.get("status") == "awaiting_transport":
        return []
    active = next((record for record in shared["records"].values() if record["definition"]["action_type"] == "extract_site_resource" and record["definition"]["output_item"] == resource and record["state"] not in {"refused", "cancelled", "failed", "needs_rework", "commissioned"}), None)
    if active:
        if demand:
            demand.update({"status": "action_active", "action_id": active["id"]})
        return []
    actor = state["npcs"].get(rule["actor"])
    if not actor or rule["tool"] not in actor.get("equipment", {}) or _shared_commitment(state, actor["id"]):
        return []
    sites = [site for site in state["resource_sites"].values() if site.get("type") == rule["site_type"] and site.get("stock", 0) > 0 and not site.get("reserved_by")]
    if not sites:
        return []
    site = max(sites, key=lambda item: (item["stock"], item["id"]))
    if not demand:
        demand = {"id": demand_id, "kind": "finite_extraction", "resource": resource, "target": rule["target"], "held": state["resources"].get(resource, 0), "created_tick": tick, "status": "unassigned", "action_id": None}
        shared["demands"].append(demand)
    action_id = f"shared:extract:{resource}:{site['id']}:{tick}"
    result = apply_shared_action_command(state, actor["id"], {"operation": "propose", "shared_action_id": action_id, "action_type": "extract_site_resource", "target_id": site["id"], "intent": f"gather finite {resource} for measured settlement shortage", "observations": [f"communal-held:{state['resources'].get(resource, 0)}", f"reorder-target:{rule['target']}", f"site-stock:{site['stock']}"], "autonomous_origin": True})
    if not result.get("accepted"):
        return []
    demand.update({"status": "action_active", "action_id": action_id, "site_id": site["id"], "actor_id": actor["id"]})
    return [{"type": "extraction_demand_proposed", "actor_id": actor["id"], "payload": {"demand_id": demand_id, "action_id": action_id, "site_id": site["id"], "resource": resource}}]


def _advance_autonomous_shared_actions(state: Dict[str, Any], tick: int) -> list[Dict[str, Any]]:
    """Advance at most one gated transition per AI action per world tick."""
    emitted: list[Dict[str, Any]] = []
    for record in sorted(state["shared_actions"]["records"].values(), key=lambda item: item["id"]):
        if not record.get("autonomous_origin") or record.get("actor_kind") != "ai" or record["state"] in {"commissioned", "failed", "refused", "needs_rework"}:
            continue
        actor = _shared_entity(state, record["actor_id"])
        if not actor:
            continue
        operation = None
        destination_id = record.get("location", "measurement_lab")
        destination = _shared_action_location(state, destination_id)
        if not destination:
            continue
        thermal = record["definition"].get("execution_model") == "thermal_batch"
        restoration = record["definition"].get("execution_model") == "condition_restoration"
        extraction = record["definition"].get("execution_model") == "finite_site_extraction"
        projected_order = next((item for item in state["cooking"]["work_orders"] if item.get("canonical_action_id") == record["id"]), None)
        maintenance_order = next((item for item in state["institutions"]["governance"]["maintenance_orders"] if item.get("canonical_action_id") == record["id"]), None)
        command: Dict[str, Any] = {"shared_action_id": record["id"]}
        transition_actor = record["actor_id"]
        if record["state"] == "proposed":
            operation = "accept"
        elif record["state"] == "accepted":
            supervisor = _shared_entity(state, record.get("supervisor_id", ""))
            travelers = [actor, *([supervisor] if supervisor else [])]
            if any(_distance(traveler["location"], destination) > 1 for traveler in travelers):
                movements = []
                for traveler in travelers:
                    origin = list(traveler["location"])
                    if _distance(traveler["location"], destination) > 1:
                        traveler["location"] = _move_toward(traveler["location"], destination)
                    movements.append({"actor_id": traveler["id"], "from": origin, "to": list(traveler["location"])})
                actor["intention"] = record["intent"]
                actor["reason"] = f"Accepted work requires physical access to {destination_id}."
                event_type = "cooking_worker_moved" if thermal else "shared_action_worker_moved"
                emitted.append({"type": event_type, "actor_id": actor["id"], "payload": {"action_id": record["id"], "movements": movements, "destination": destination_id, "supervised": bool(supervisor)}})
                continue
            if extraction:
                destination_site = state["resource_sites"].get(record["target_id"])
                if destination_site:
                    for traveler in travelers:
                        traveler["current_region"] = destination_site["region"]
            operation = "reserve"
        elif record["state"] == "reserved":
            operation = "execute"
            if thermal:
                # Hearth and thermometer conditions deterministically constrain
                # the achieved thermal history; no model may simply assert safety.
                thermometer = state["shared_actions"]["tools"]["food_thermometer"]["condition"]
                command["samples"] = [{"temperature_c": round(80.0 + thermometer * 2.0, 3), "duration_minutes": 15.0}]
            elif restoration:
                site = state["resource_sites"].get(record["target_id"])
                before = site.get("installed_pump", {}).get("condition", 0.0) if site else 0.0
                command["samples"] = [{"condition_before": before, "condition_after": min(1.0, before + 0.62)}]
            elif extraction:
                site = state["resource_sites"].get(record["target_id"])
                amount = min(record["definition"]["output_amount"], int(site.get("stock", 0))) if site else 0
                command["samples"] = [{"stock_before": int(site.get("stock", 0)) if site else 0, "observed_yield": amount}]
            else:
                condition = state["shared_actions"]["tools"]["marked_measure"]["condition"]
                drift = round((1.0 - condition) * 0.01, 6)
                command["samples"] = [{"reading": 1.0}, {"reading": round(1.0 + drift, 6)}, {"reading": round(1.0 + drift / 2, 6)}]
        elif record["state"] == "submitted":
            candidates = []
            verifier_domain = record["definition"].get("verifier_competence_domain") or record["definition"]["requirements"]["competence_domain"]
            verifier_minimum = record["definition"].get("minimum_verifier_competence", 0.1)
            for verifier_id, verifier in {**state["npcs"], **state["players"]}.items():
                if verifier_id in {record["actor_id"], record.get("supervisor_id")} or _shared_competence(verifier, verifier_domain) < verifier_minimum:
                    continue
                commitment = _shared_commitment(state, verifier_id)
                if commitment and commitment.get("action_id") != record["id"]:
                    continue
                candidates.append((_shared_competence(verifier, verifier_domain), verifier_id, verifier))
            if not candidates:
                continue
            _, transition_actor, verifier = max(candidates, key=lambda item: (item[0], item[1]))
            conflict = _claim_shared_commitment(state, transition_actor, record["id"], "verifier")
            if conflict:
                continue
            if _distance(verifier["location"], destination) > 1:
                origin = list(verifier["location"])
                verifier["location"] = _move_toward(verifier["location"], destination)
                verifier["intention"] = f"independently verify {record['intent']}"
                verifier["reason"] = "Commissioning requires evidence from a distinct competent observer."
                event_type = "cooking_inspector_moved" if thermal else "shared_action_verifier_moved"
                emitted.append({"type": event_type, "actor_id": verifier["id"], "payload": {"action_id": record["id"], "from": origin, "to": list(verifier["location"]), "destination": destination_id}})
                continue
            if extraction:
                destination_site = state["resource_sites"].get(record["target_id"])
                if destination_site:
                    verifier["current_region"] = destination_site["region"]
            operation = "verify"
        elif record["state"] == "verified":
            transition_actor = record.get("verifier_id")
            if not transition_actor:
                continue
            operation = "commission"
        if not operation:
            continue
        command["operation"] = operation
        result = apply_shared_action_command(state, transition_actor, command)
        if projected_order:
            if result.get("accepted"):
                recovered_inputs = operation == "reserve" and projected_order.get("status") == "blocked_inputs"
                projected_status = {"accept": "assigned", "reserve": "supplied", "execute": "preparing", "verify": "inspected", "commission": "completed"}.get(operation)
                if operation == "accept" and projected_order.get("status") == "blocked_inputs":
                    projected_status = "blocked_inputs"
                if projected_status and projected_order.get("status") != "completed":
                    projected_order["status"] = projected_status
                    history = {"tick": tick, "status": projected_status, "canonical_operation": operation}
                    if recovered_inputs:
                        history["cause"] = "required ingredients delivered"
                    projected_order.setdefault("history", []).append(history)
            elif operation == "reserve":
                reason = result.get("reason", "reservation rejected")
                if reason.startswith("missing materials:"):
                    missing = {name: amount - state["resources"].get(name, 0) for name, amount in record["definition"]["requirements"]["materials"].items() if state["resources"].get(name, 0) < amount}
                    projected_order.update({"status": "blocked_inputs", "missing": missing})
                elif reason.startswith("facility unavailable:"):
                    projected_order["status"] = "blocked_facility"
                projected_order.setdefault("history", []).append({"tick": tick, "status": projected_order["status"], "reason": reason})
        if maintenance_order:
            if result.get("accepted"):
                if operation == "commission":
                    emitted.append({"type": "maintenance_completed", "actor_id": record["actor_id"], "payload": {"order_id": maintenance_order["id"], "site_id": record["target_id"], "condition": state["resource_sites"][record["target_id"]]["installed_pump"]["condition"], "verified_by": transition_actor, "canonical_action_id": record["id"]}})
                elif operation == "accept":
                    emitted.append({"type": "maintenance_assigned", "actor_id": record["actor_id"], "payload": {"order_id": maintenance_order["id"], "assignee": record["actor_id"], "site_id": record["target_id"], "canonical_action_id": record["id"]}})
            elif operation == "reserve" and result.get("reason", "").startswith("missing materials:"):
                missing = [name for name, amount in record["definition"]["requirements"]["materials"].items() if state["resources"].get(name, 0) < amount]
                signature = ",".join(sorted(missing))
                if missing and (not maintenance_order["blockers"] or maintenance_order["blockers"][-1].get("signature") != signature):
                    maintenance_order["blockers"].append({"tick": tick, "signature": signature, "missing": missing, "status": "unresolved"})
                    state["failures"].append({"tick": tick, "action": "repair_mechanical_pump", "order_id": maintenance_order["id"], "reason": f"maintenance missing {signature}", "recovered": False})
                    emitted.append({"type": "maintenance_blocked", "actor_id": record["actor_id"], "payload": {"order_id": maintenance_order["id"], "missing": missing, "canonical_action_id": record["id"]}})
        emitted.append({
            "type": "shared_action_autonomous_transition",
            "actor_id": transition_actor,
            "payload": {"action_id": record["id"], "operation": operation, "accepted": result.get("accepted", False), "reason": result.get("reason")},
        })
        if thermal and result.get("accepted") and operation == "execute":
            emitted.append({"type": "meal_preparation_started", "actor_id": transition_actor, "payload": {"order_id": record["id"], "due_tick": record.get("execution_due_tick"), "inputs": copy.deepcopy(record["definition"]["requirements"]["materials"])}})
        if thermal and result.get("accepted") and operation == "commission":
            emitted.append({"type": "cooking_work_completed", "actor_id": record["actor_id"], "payload": {"order_id": record["id"], "portions": record["definition"]["output_amount"], "inspector": transition_actor}})
    return emitted


def advance_founding_table(state: Dict[str, Any], tick: int) -> list[Dict[str, Any]]:
    event = state["event"]
    phase = event["phase"]
    emitted: list[Dict[str, Any]] = []
    evidence_id = f"founding-table:{phase}:{tick}"
    if phase == 0:  # Survey water.
        state["places"]["water_source"]["status"] = "surveyed"
        _evidence(state, tick, "water source surveyed", ["emil", "ada"], {}, ["survey_stakes", "measuring_line"], {"distance_tiles": 5, "flow_index": 0.62, "uncertainty": 0.08}, "mira")
        _provisional_claim(state, tick, "emil", "verified water survey", 11.5, evidence_id)
    elif phase == 1:  # Test water.
        tested = min(18, state["resources"]["water"])
        state["resources"]["water"] -= tested
        state["resources"]["tested_water"] += tested
        state["places"]["water_source"]["status"] = "conditionally_safe"
        _evidence(state, tick, "water quality tested", ["emil", "mira"], {"water": tested}, ["sample_jars", "test_strip", "notebook"], {"turbidity": 0.31, "safety_confidence": 0.78}, "mira")
        _provisional_claim(state, tick, "mira", "reproduced water test", 14.0, evidence_id)
    elif phase == 2:  # Inventory provisions.
        _evidence(state, tick, "provisions inventoried", ["dev", "sora"], dict(state["resources"]), ["scale", "inventory_sheet"], {"count_error": 0.02}, "ada")
        _provisional_claim(state, tick, "dev", "verified inventory", 8.0, evidence_id)
    elif phase == 3:  # Decide facility through competing needs.
        event["competing_orders"] = [
            {"id": "order-kitchen", "author": "lena", "priority": "communal_kitchen", "status": "proposed", "terms": {"fuel_limit": 8, "meal_inspection": True}},
            {"id": "order-water", "author": "emil", "priority": "dependable_water", "status": "proposed", "terms": {"minimum_safety": 0.8}},
            {"id": "order-storage", "author": "dev", "priority": "verified_storage", "status": "proposed", "terms": {"spoilage_reduction": 0.4}},
        ]
        event["selected_order"] = "order-kitchen" if state["food"]["spoilage_clock"] < 72 else "order-water"
    elif phase == 4:  # Publish orders.
        emitted.append({"type": "work_orders_published", "actor_id": "sora", "payload": {"orders": event["competing_orders"]}})
    elif phase == 5:  # Negotiate.
        for order in event["competing_orders"]:
            order["status"] = "accepted" if order["id"] == event["selected_order"] else "deferred"
        _provisional_claim(state, tick, "sora", "documented public negotiation", 7.0, evidence_id)
    elif phase == 6:  # Construct selected facility, with possible redirection.
        selected = event["selected_order"]
        if state["resources"]["timber"] < 8 or state["resources"]["stone"] < 5:
            state["failures"].append({"tick": tick, "action": "construct", "reason": "insufficient timber or stone", "recovered": False})
            emitted.append({"type": "work_stopped", "actor_id": "orin", "payload": state["failures"][-1]})
            return emitted
        state["resources"]["timber"] -= 8
        state["resources"]["stone"] -= 5
        place = "communal_kitchen" if selected == "order-kitchen" else "water_source" if selected == "order-water" else "dry_storage"
        state["places"][place]["status"] = "operational"
        _evidence(state, tick, f"{place} made operational", ["orin", "cal", "ada"], {"timber": 8, "stone": 5}, ["handcart", "hammer", "level"], {"alignment_error": 0.04}, "mira")
        for actor in ["orin", "cal", "ada"]:
            _provisional_claim(state, tick, actor, f"verified {place} construction", 12.0, evidence_id)
    elif phase == 7:  # Prepare communal meal.
        raw = min(18, state["resources"]["raw_food"])
        water = min(10, state["resources"]["tested_water"])
        fuel = min(6, state["resources"]["fuel"])
        if raw < 12 or water < 6 or fuel < 3:
            state["failures"].append({"tick": tick, "action": "cook", "reason": "food, tested water, or fuel shortage", "recovered": False})
            emitted.append({"type": "work_stopped", "actor_id": "lena", "payload": state["failures"][-1]})
            return emitted
        state["resources"]["raw_food"] -= raw
        state["resources"]["tested_water"] -= water
        state["resources"]["fuel"] -= fuel
        portions = 14
        meal = {"tick": tick, "name": "Founding stew", "calories": 610, "protein": 0.68, "micronutrients": 0.61, "hydration": 0.52, "safety": 0.82, "enjoyment": 0.71, "portions": portions, "spoilage_ticks": 16, "inputs": {"raw_food": raw, "tested_water": water, "fuel": fuel}, "technique": "simmered"}
        state["food"]["meal_history"].append(meal)
        state["resources"]["safe_meals"] += portions
        state["culture"]["recipes"].append({"name": meal["name"], "author": "lena", "first_served_tick": tick})
        _evidence(state, tick, "first communal meal prepared", ["lena", "tomas", "nyra"], meal["inputs"], ["pot", "ladle", "hearth", "timer"], {"cook_time": 48, "peak_heat": 0.77, "portions": portions}, None)
        _provisional_claim(state, tick, "lena", "safe communal meal", portions, evidence_id)
    elif phase == 8:  # Inspect meal.
        meal = state["food"]["meal_history"][-1] if state["food"]["meal_history"] else None
        if not meal or meal["safety"] < 0.75:
            state["failures"].append({"tick": tick, "action": "serve_meal", "reason": "meal safety evidence rejected", "recovered": False})
            emitted.append({"type": "inspection_rejected", "actor_id": "imani", "payload": state["failures"][-1]})
            return emitted
        state["evidence"][-1]["inspector"] = "imani"
        state["evidence"][-1]["inspection"] = {"safety": meal["safety"], "accepted": True}
        _provisional_claim(state, tick, "imani", "meal safety inspection", 9.0, evidence_id)
        for npc in state["npcs"].values():
            npc["needs"]["nutrition"] = min(100, npc["needs"]["nutrition"] + 24)
            npc["needs"]["belonging"] = min(100, npc["needs"]["belonging"] + 12)
            npc["memories"].append({"tick": tick, "kind": "founding_table", "text": "Shared the first inspected communal meal."})
        state["resources"]["safe_meals"] = max(0, state["resources"]["safe_meals"] - len(state["npcs"]))
    elif phase == 9:  # Meeting chooses next priority.
        event["status"] = "completed"
        state["culture"]["traditions"].append({"name": "Founding Table meal", "origin_tick": tick})
        state["culture"]["place_names"]["meeting_hall"] = "The Founding Table"
        emitted.append({"type": "historical_event_completed", "actor_id": "settlement", "payload": {"event": event["id"], "next_priority": "sanitation_and_storage"}})
    if event["status"] != "completed":
        event["phase"] = min(len(event["priorities"]) - 1, phase + 1)
    emitted.append({"type": "founding_table_advanced", "actor_id": "settlement", "payload": {"phase": phase, "next_phase": event["phase"], "status": event["status"]}})
    return emitted


def _open_pump_maintenance(state: Dict[str, Any], site: Dict[str, Any], cause: str) -> Dict[str, Any]:
    governance = state["institutions"]["governance"]
    existing = next((item for item in governance["maintenance_orders"] if item["site_id"] == site["id"] and item["status"] == "open"), None)
    if existing:
        return existing
    pump = site["installed_pump"]
    order = {
        "id": f"maintenance-{len(governance['maintenance_orders']) + 1}", "site_id": site["id"],
        "technology_id": pump["design_id"], "opened_tick": state["clock"]["tick"], "status": "open",
        "condition": pump["condition"], "cycles": pump["cycles"], "cause": cause,
        "required_inputs": {"timber": 1, "containers": 1}, "required_tool": "wrench", "assigned_to": None,
        "assigned_tick": None, "blockers": [], "procurement_history": [], "depletion_notices": [],
    }
    governance["maintenance_orders"].append(order)
    pump["maintenance_due"] = True
    _remember_consequence(state, state["clock"]["tick"], cause, f"maintenance-order:{order['id']}", [pump["installed_by"], "ada", "dev"])
    return order


def _complete_pump_maintenance(state: Dict[str, Any], site: Dict[str, Any], order: Dict[str, Any], actor_id: str, input_source: str) -> None:
    pump = site["installed_pump"]
    before = pump["condition"]
    pump["condition"] = round(min(1.0, before + 0.62), 4)
    pump["status"] = "operational"
    pump["maintenance_due"] = False
    pump["maintenance_history"].append({"tick": state["clock"]["tick"], "actor": actor_id, "before": before, "after": pump["condition"], "input_source": input_source, "order_id": order["id"]})
    order["status"] = "completed"
    order["completed_tick"] = state["clock"]["tick"]
    order["completed_by"] = actor_id
    _evidence(state, state["clock"]["tick"], f"pump maintenance completed at {site['name']}", [actor_id], dict(order["required_inputs"]), ["wrench", "caliper"], {"condition_before": before, "condition_after": pump["condition"], "cycles": pump["cycles"]}, "mira", [f"maintenance-order:{order['id']}", f"validated-technology:{pump['design_id']}"], ["condition inspection", "post-maintenance flow check"])
    _provisional_claim(state, state["clock"]["tick"], actor_id, "verified technology maintenance", 7.0, f"maintenance-order:{order['id']}")
    _remember_consequence(state, state["clock"]["tick"], f"maintenance-order:{order['id']}", f"technology-recovered:{site['id']}:{pump['condition']}", [actor_id, "mira"])


def interact_resource_site(state: Dict[str, Any], actor_id: str, action: Dict[str, Any]) -> Dict[str, Any]:
    player = state["players"].get(actor_id)
    site = state["resource_sites"].get(action.get("site_id"))
    operation = action.get("operation")
    if not player or not site:
        return {"accepted": False, "reason": "join the world and select a known resource site"}
    if player.get("current_region", "settlement") != site["region"]:
        return {"accepted": False, "reason": "the selected site is in another region"}
    if _distance(player["location"], site["location"]) > 1:
        return {"accepted": False, "reason": "move beside the site before interacting"}
    inventory = player["inventory"]
    outputs: Dict[str, Any] = {}
    inputs: Dict[str, Any] = {}
    energy_cost = 0
    physical = True
    required_energy = {"checkout": 0, "chop": 4, "mine": 6, "harvest": 6 if site["type"] == "farm" else 4, "dig": 7, "install_pump": 4, "inspect_pump": 1, "maintain_pump": 5, "draw_water": 3, "till": 6, "sow": 4, "feed": 3, "milk": 3}.get(operation, 0)
    if player.get("energy", 100) < required_energy:
        return {"accepted": False, "reason": "the actor is too exhausted"}
    if site["type"] == "store" and operation == "checkout":
        item = action.get("item")
        quantity = 4 if item in {"seed", "feed"} else 1
        if item not in site["stock"] or site["stock"][item] < quantity:
            return {"accepted": False, "reason": "the requested store item is unavailable"}
        site["stock"][item] -= quantity
        inventory[item] = inventory.get(item, 0) + quantity
        if item in {"axe", "pick", "farm_tools", "shovel", "wrench", "bucket"}:
            player.setdefault("equipment", {}).setdefault(item, {"condition": 0.9, "reserved_by": None, "provenance": f"checkout:{site['id']}:{actor_id}:{state['clock']['tick']}"})
        outputs = {item: quantity}
        physical = False
    elif site["type"] == "tree" and operation == "chop":
        action_id = f"shared:extract:{actor_id}:{site['id']}:{state['clock']['tick']}:{len(state['shared_actions']['records']) + 1}"
        proposal = apply_shared_action_command(state, actor_id, {"operation": "propose", "shared_action_id": action_id, "action_type": "extract_site_resource", "target_id": site["id"], "intent": f"extract finite timber from {site['name']}", "observations": [f"site-stock:{site['stock']}", f"region:{site['region']}"]})
        if not proposal.get("accepted"):
            return proposal
        inputs, outputs, energy_cost, physical = {}, {"canonical_action_id": action_id, "next": "accept, reserve held axe, execute, and obtain independent stock verification"}, 0, False
    elif site["type"] == "mineral" and operation == "mine":
        action_id = f"shared:extract:{actor_id}:{site['id']}:{state['clock']['tick']}:{len(state['shared_actions']['records']) + 1}"
        proposal = apply_shared_action_command(state, actor_id, {"operation": "propose", "shared_action_id": action_id, "action_type": "extract_site_resource", "target_id": site["id"], "intent": f"extract finite stone from {site['name']}", "observations": [f"site-stock:{site['stock']}", f"region:{site['region']}"]})
        if not proposal.get("accepted"):
            return proposal
        inputs, outputs, energy_cost, physical = {}, {"canonical_action_id": action_id, "next": "accept, reserve held pick, execute, and obtain independent stock verification"}, 0, False
    elif site["type"] == "reeds" and operation == "harvest":
        action_id = f"shared:extract:{actor_id}:{site['id']}:{state['clock']['tick']}:{len(state['shared_actions']['records']) + 1}"
        proposal = apply_shared_action_command(state, actor_id, {"operation": "propose", "shared_action_id": action_id, "action_type": "extract_site_resource", "target_id": site["id"], "intent": f"harvest finite reeds from {site['name']}", "observations": [f"site-stock:{site['stock']}", f"region:{site['region']}"]})
        if not proposal.get("accepted"):
            return proposal
        inputs, outputs, energy_cost, physical = {}, {"canonical_action_id": action_id, "next": "accept, reserve held farm tools, execute, and obtain independent stock verification"}, 0, False
    elif site["type"] == "well" and operation == "dig":
        if inventory.get("shovel", 0) < 1 or site["progress"] >= 3:
            return {"accepted": False, "reason": "a shovel and unfinished well are required"}
        site["progress"] += 1
        if site["progress"] == 3:
            site["stock"] = site["capacity"]
        inputs, outputs, energy_cost = {"shovel": 1}, {"excavation_stage": site["progress"], "water_access": site["progress"] == 3}, 7
    elif site["type"] == "well" and operation == "install_pump":
        design_id = str(action.get("design_id", ""))
        tool = state["technology"]["tool_catalog"].get(design_id)
        if inventory.get("wrench", 0) < 1 or site["progress"] < 3 or not tool or tool.get("available_units", 0) < 1 or site.get("installed_pump"):
            return {"accepted": False, "reason": "a completed well, wrench, validated available pump, and empty installation point are required"}
        tool["available_units"] -= 1
        design = next(item for item in state["research"]["designs"] if item["id"] == design_id)
        design["available_units"] = tool["available_units"]
        site["installed_pump"] = {
            "design_id": design_id, "installed_tick": state["clock"]["tick"], "installed_by": actor_id,
            "predicted_liters_per_stroke": tool["prediction"]["predicted_liters_per_stroke"],
            "provenance": list(tool["provenance"]), "condition": 1.0, "cycles": 0,
            "status": "operational", "maintenance_due": False, "maintenance_history": [],
        }
        inputs, outputs, energy_cost = {"wrench": 1, "validated_pump": design_id}, {"installed_pump": design_id}, 4
        _remember_consequence(state, state["clock"]["tick"], f"validated-technology:{design_id}", f"installed-tool:{site['id']}:{design_id}", [actor_id, "ada", "mira", "emil"])
    elif site["type"] == "well" and operation == "inspect_pump":
        pump = site.get("installed_pump")
        if not pump:
            return {"accepted": False, "reason": "no installed pump is available for inspection"}
        measured = round(max(0.0, min(1.0, pump["condition"] - 0.01)), 4)
        order = _open_pump_maintenance(state, site, f"inspection:{site['id']}:{pump['cycles']}") if measured < 0.7 else None
        inputs, outputs, energy_cost, physical = {"observation_time": 1}, {"measured_condition": measured, "maintenance_order": order["id"] if order else None}, 1, False
        _evidence(state, state["clock"]["tick"], f"pump condition inspected at {site['name']}", [actor_id], {}, ["caliper", "field notebook"], outputs, None, [f"installed-tool:{site['id']}:{pump['design_id']}"], ["condition inspection"])
    elif site["type"] == "well" and operation == "maintain_pump":
        pump = site.get("installed_pump")
        order = next((item for item in state["institutions"]["governance"]["maintenance_orders"] if item["site_id"] == site["id"] and item["status"] == "open"), None)
        if not pump or not order:
            return {"accepted": False, "reason": "an installed pump and open maintenance order are required"}
        action_id = order.get("canonical_action_id") or f"shared:repair:{order['id']}"
        if action_id not in state["shared_actions"]["records"]:
            proposal = apply_shared_action_command(state, actor_id, {
                "operation": "propose", "shared_action_id": action_id,
                "action_type": MECHANICAL_PUMP_REPAIR.action_type, "target_id": site["id"],
                "intent": f"restore the measured condition of {site['name']}",
                "observations": [f"maintenance-order:{order['id']}", f"condition:{pump['condition']}"],
            })
            if not proposal.get("accepted"):
                return proposal
            order.update({"canonical_action_id": action_id, "assigned_to": actor_id, "assigned_tick": state["clock"]["tick"]})
        outputs, energy_cost, physical = {"canonical_action_id": action_id, "next": "accept and reserve through authoritative work"}, 0, False
    elif site["type"] == "well" and operation == "draw_water":
        pump = site.get("installed_pump")
        if pump and pump["status"] == "failed":
            return {"accepted": False, "reason": "the installed pump has failed and must be maintained before the well can operate"}
        effective_prediction = pump["predicted_liters_per_stroke"] * pump["condition"] if pump else 3
        pump_yield = max(2, min(6, round(effective_prediction))) if pump else 3
        if inventory.get("bucket", 0) < 1 or site["progress"] < 3 or site["stock"] < pump_yield:
            return {"accepted": False, "reason": f"a bucket and {pump_yield} available units from a completed well are required"}
        site["stock"] -= pump_yield
        inventory["water"] = inventory.get("water", 0) + pump_yield
        inputs, outputs, energy_cost = {"bucket": 1, **({"installed_pump": pump["design_id"]} if pump else {})}, {"water": pump_yield, "baseline_water": 3, "technology_gain": pump_yield - 3}, 2 if pump else 3
        if pump:
            before = pump["condition"]
            pump["cycles"] += 1
            pump["condition"] = round(max(0.0, before - 0.08), 4)
            outputs.update({"condition_before": before, "condition_after": pump["condition"], "cycle": pump["cycles"]})
            state["technology"]["tool_catalog"][pump["design_id"]].setdefault("field_history", []).append({"tick": state["clock"]["tick"], "site_id": site["id"], "cycle": pump["cycles"], "condition": pump["condition"], "water": pump_yield})
            if pump["condition"] < 0.7:
                order = _open_pump_maintenance(state, site, f"wear:{site['id']}:{pump['cycles']}")
                outputs["maintenance_order"] = order["id"]
            if pump["condition"] <= 0.28:
                pump["status"] = "failed"
                outputs["status"] = "failed"
                _remember_consequence(state, state["clock"]["tick"], f"wear:{site['id']}:{pump['cycles']}", f"technology-failed:{site['id']}:{pump['design_id']}", [actor_id, "ada", "dev"])
    elif site["type"] == "farm" and operation == "till":
        if inventory.get("farm_tools", 0) < 1 or site["stage"] != "untilled":
            return {"accepted": False, "reason": "farm tools and an untilled plot are required"}
        site["stage"], inputs, outputs, energy_cost = "tilled", {"farm_tools": 1}, {"prepared_soil": 1}, 6
    elif site["type"] == "farm" and operation == "sow":
        if inventory.get("farm_tools", 0) < 1 or inventory.get("seed", 0) < 1 or site["stage"] != "tilled":
            return {"accepted": False, "reason": "farm tools, seed, and a tilled plot are required"}
        inventory["seed"] -= 1
        site["stage"], site["ready_tick"] = "growing", state["clock"]["tick"] + 12
        inputs, outputs, energy_cost = {"farm_tools": 1, "seed": 1}, {"crop_due_tick": site["ready_tick"]}, 4
    elif site["type"] == "farm" and operation == "harvest":
        if inventory.get("farm_tools", 0) < 1 or site["stage"] != "ripe":
            return {"accepted": False, "reason": "farm tools and a ripe crop are required"}
        amount = site["stock"]
        inventory["raw_food"] = inventory.get("raw_food", 0) + amount
        site["stage"], site["ready_tick"], site["stock"] = "untilled", None, 0
        inputs, outputs, energy_cost = {"farm_tools": 1}, {"raw_food": amount}, 6
    elif site["type"] == "cattle" and operation == "feed":
        if inventory.get("feed", 0) < 1:
            return {"accepted": False, "reason": "feed is required"}
        inventory["feed"] -= 1
        site["fed_until_tick"] = state["clock"]["tick"] + 16
        site["wellbeing"] = min(100, site["wellbeing"] + 12)
        inputs, outputs, energy_cost = {"feed": 1}, {"wellbeing": site["wellbeing"]}, 3
    elif site["type"] == "cattle" and operation == "milk":
        if inventory.get("bucket", 0) < 1 or site["wellbeing"] < 50 or site["stock"] < 1:
            return {"accepted": False, "reason": "a bucket, adequate wellbeing, and available milk are required"}
        site["stock"] = round(site["stock"] - 1, 2)
        inventory["milk"] = inventory.get("milk", 0) + 1
        inputs, outputs, energy_cost = {"bucket": 1}, {"milk": 1}, 3
    else:
        return {"accepted": False, "reason": "that operation is not supported at this site"}
    player["energy"] = round(player.get("energy", 100) - energy_cost, 2)
    record = {"tick": state["clock"]["tick"], "actor": actor_id, "operation": operation, "inputs": inputs, "outputs": outputs, "energy_cost": energy_cost}
    site["history"].append(record)
    site["history"] = site["history"][-100:]
    _evidence(state, state["clock"]["tick"], f"{operation} at {site['name']}", [actor_id], inputs, list(inputs), outputs, None)
    consequence = _remember_consequence(state, state["clock"]["tick"], f"site-action:{site['id']}:{operation}", f"site-state:{site['id']}", [actor_id])
    return {"accepted": True, "type": "interact_site", "site_id": site["id"], "operation": operation, "inputs": inputs, "outputs": outputs, "energy": player["energy"], "consequence_id": consequence["id"], "physical_change": physical}


def apply_player_action(state: Dict[str, Any], actor_id: str, action: Dict[str, Any]) -> Dict[str, Any]:
    action_type = action.get("type")
    if action_type == "shared_action":
        return apply_shared_action_command(state, actor_id, action)
    if action_type == "owner_directive":
        supplied = action.get("directive") if isinstance(action.get("directive"), dict) else {}
        priority = str(supplied.get("priority", "")).strip().lower()[:40]
        objective = str(supplied.get("objective", "")).strip()[:240]
        evidence_required = [str(item).strip()[:120] for item in supplied.get("evidence_required", []) if str(item).strip()][:12]
        if not objective:
            return {"accepted": False, "reason": "a directive requires a stated objective"}
        governance = state["institutions"]["governance"]
        directive = {
            "id": f"directive-{len(governance['owner_directives']) + 1}", "tick": state["clock"]["tick"],
            "proposed_by": actor_id, "objective": objective, "priority": priority,
            "evidence_required": evidence_required, "status": "pending_council_review",
            "authority_scope": "proposal_only", "physical_effect": False,
        }
        governance["owner_directives"].append(directive)
        consequence = _remember_consequence(state, state["clock"]["tick"], f"owner-proposal:{directive['id']}", f"council-review-required:{priority or 'unclassified'}", [actor_id, "council"])
        return {"accepted": True, "type": action_type, "directive": directive, "consequence_id": consequence["id"], "physical_change": False}
    if action_type == "propose_invention":
        player = state["players"].get(actor_id)
        if not player or player.get("current_region", "settlement") != "settlement" or _distance(player.get("location", [0, 0]), state["places"]["measurement_lab"]["location"]) > 1:
            return {"accepted": False, "reason": "design proposals require the actor to work at the measurement laboratory"}
        archetype = str(action.get("archetype", "")).strip().lower()
        if archetype != "lever_pump":
            return {"accepted": False, "reason": "the current laboratory can evaluate only the lever_pump archetype"}
        name = str(action.get("name", "")).strip()[:80]
        protocol = str(action.get("test_protocol", "")).strip()[:500]
        sources = [str(item).strip()[:160] for item in action.get("knowledge_sources", []) if str(item).strip()][:12]
        specification = action.get("specification") if isinstance(action.get("specification"), dict) else {}
        if len(name) < 3 or len(protocol) < 12 or not sources:
            return {"accepted": False, "reason": "a named design requires a test protocol and at least one knowledge source"}
        design = {
            "id": f"design-{len(state['research']['designs']) + 1}", "name": name, "archetype": archetype,
            "proposer": actor_id, "submitted_tick": state["clock"]["tick"], "status": "proposed",
            "specification": copy.deepcopy(specification), "test_protocol": protocol, "knowledge_sources": sources,
            "prototype_inputs": {"timber": 2, "containers": 2}, "physical_effect": False,
        }
        state["research"]["designs"].append(design)
        player.setdefault("competencies", {"observe": 0.25, "measure": 0.2, "engineering": 0.1})
        player["competencies"]["measure"] = round(min(1.0, player["competencies"].get("measure", 0) + 0.01), 4)
        _remember_consequence(state, state["clock"]["tick"], f"documented-design:{design['id']}", f"peer-review-required:{design['id']}", [actor_id, "mira"])
        return {"accepted": True, "type": action_type, "design": design, "physical_change": False}
    if action_type == "submit_water_batch":
        player = state["players"].get(actor_id)
        amount = action.get("amount")
        source_site_id = str(action.get("source_site", ""))
        site = state["resource_sites"].get(source_site_id)
        if not player or player.get("current_region", "settlement") != "settlement" or _distance(player.get("location", [0, 0]), state["places"]["measurement_lab"]["location"]) > 1:
            return {"accepted": False, "reason": "raw water must be delivered beside the measurement laboratory"}
        if not isinstance(amount, int) or not 1 <= amount <= 6 or player["inventory"].get("water", 0) < amount:
            return {"accepted": False, "reason": "submit one to six units of raw water held by the authenticated actor"}
        if not site or site.get("type") != "well":
            return {"accepted": False, "reason": "a known well source is required for chain of custody"}
        source_record = next((record for record in reversed(site.get("history", [])) if record.get("actor") == actor_id and record.get("operation") == "draw_water"), None)
        if not source_record:
            return {"accepted": False, "reason": "no authoritative water-collection record links this actor to that source"}
        available_from_record = source_record["outputs"].get("water", 0) - source_record.get("submitted_water", 0)
        if amount > available_from_record:
            return {"accepted": False, "reason": "the requested batch exceeds unsubmitted water in the latest collection record"}
        player["inventory"]["water"] -= amount
        source_record["submitted_water"] = source_record.get("submitted_water", 0) + amount
        batch = {
            "id": f"water-batch-{len(state['water_system']['batches']) + 1}", "status": "awaiting_test",
            "submitted_tick": state["clock"]["tick"], "test_due_tick": state["clock"]["tick"] + 2,
            "submitted_by": actor_id, "amount": amount, "source_site": source_site_id,
            "source_evidence": f"site-history:{source_site_id}:tick-{source_record['tick']}:cycle-{source_record['outputs'].get('cycle', 'manual')}",
            "collection_evidence": copy.deepcopy(source_record["outputs"]),
        }
        state["water_system"]["batches"].append(batch)
        _remember_consequence(state, state["clock"]["tick"], batch["source_evidence"], f"laboratory-test-required:{batch['id']}", [actor_id, "mira"])
        return {"accepted": True, "type": action_type, "batch": copy.deepcopy(batch), "physical_change": True}
    if action_type == "survey_frontier":
        player = state["players"].get(actor_id)
        location = action.get("location")
        if not player or not isinstance(location, list) or len(location) != 2 or _distance(player.get("location", [-99, -99]), location) > 1:
            return {"accepted": False, "reason": "survey requires physical access beside a frontier tile"}
        key = _tile_key(location)
        evidence = state.get("discoveries", {}).get(actor_id, {}).get(key)
        if not evidence:
            return {"accepted": False, "reason": "survey requires a previously observed tile"}
        tile = FrontierGrid(state["frontier"]["seed"], state["frontier"]["size"]).tile_at(*location)
        evidence.update({"level": "surveyed", "survey": {"elevation": tile.elevation, "passable": tile.passable, "foundation_suitable": tile.passable and tile.terrain != "wetland", "measured_tick": state["clock"]["tick"]}})
        return {"accepted": True, "type": action_type, "location": location, "evidence": copy.deepcopy(evidence["survey"]), "physical_change": False}
    if action_type == "propose_frontier_extraction":
        player = state["players"].get(actor_id)
        location = action.get("location")
        mode = action.get("mode")
        if not player or not isinstance(location, list) or len(location) != 2 or _distance(player.get("location", [-99, -99]), location) > 1:
            return {"accepted": False, "reason": "extraction requires physical access beside the tile"}
        key = _tile_key(location)
        evidence = state.get("discoveries", {}).get(actor_id, {}).get(key, {})
        if evidence.get("level") not in {"surveyed", "prospected"}:
            return {"accepted": False, "reason": "extraction requires surveyed evidence"}
        grid_tile = FrontierGrid(state["frontier"]["seed"], state["frontier"]["size"]).tile_at(*location)
        modification = state["terrain_modifications"].setdefault(key, {})
        if mode == "harvest" and grid_tile.surface:
            material, stock, tool, domain = grid_tile.surface.material, int(modification.get("surface_stock", grid_tile.surface.stock)), "axe", "forestry"
            site_type, layer_index = "tree", None
        elif mode == "excavate":
            depth = int(modification.get("excavation_depth_cm", 0))
            layer_index = min(len(grid_tile.substrate) - 1, depth // 40)
            layer = grid_tile.substrate[layer_index]
            layer_stocks = modification.setdefault("layer_stocks", {})
            material, stock, tool, domain = layer.material, int(layer_stocks.get(str(layer_index), layer.stock)), "shovel", "excavation"
            site_type = "mineral"
        else:
            return {"accepted": False, "reason": "choose harvest or excavate for an observed finite source"}
        if stock < 1:
            return {"accepted": False, "reason": "frontier source is depleted"}
        site_id = f"frontier:{key}:{mode}:{layer_index if layer_index is not None else 'surface'}"
        site = state["resource_sites"].setdefault(site_id, {"id": site_id, "type": site_type, "region": "settlement", "location": list(location), "name": f"Frontier {material} at {key}", "history": []})
        site.update({"stock": stock, "capacity": stock, "material": material, "yield_amount": 1, "required_tool": tool, "competence_domain": domain, "energy_cost": 5, "frontier_tile": key, "frontier_layer": layer_index, "frontier_mode": mode})
        state["environment"].setdefault("regional_capacity", {}).setdefault(material, max(1, stock))
        state["economy"].setdefault("prices", {}).setdefault(material, 2.0)
        canonical_id = f"frontier-extract:{actor_id}:{key}:{state['clock']['tick']}:{len(state['shared_actions']['records']) + 1}"
        proposal = apply_shared_action_command(state, actor_id, {"operation": "propose", "shared_action_id": canonical_id, "action_type": "extract_site_resource", "target_id": site_id, "intent": f"remove finite {material} from tile {key}", "observations": [f"survey:{key}", f"measured-stock:{stock}"]})
        return {**proposal, "canonical_action_id": canonical_id, "stock": stock, "material": material}
    if action_type == "prepare_frontier_plot":
        player = state["players"].get(actor_id)
        location = action.get("location")
        if not player or not isinstance(location, list) or len(location) != 2 or _distance(player.get("location", [-99, -99]), location) > 1:
            return {"accepted": False, "reason": "plot preparation requires physical access"}
        key = _tile_key(location)
        evidence = state.get("discoveries", {}).get(actor_id, {}).get(key, {})
        if evidence.get("level") not in {"surveyed", "prospected"} or not evidence.get("survey", {}).get("foundation_suitable"):
            return {"accepted": False, "reason": "a suitable surveyed tile is required"}
        if player.get("inventory", {}).get("shovel", 0) < 1 or player.get("inventory", {}).get("stone", 0) < 1 or player.get("energy", 0) < 4:
            return {"accepted": False, "reason": "a shovel, one stone, and sufficient energy are required"}
        player["inventory"]["stone"] -= 1
        player["energy"] = round(player["energy"] - 4, 2)
        state["terrain_modifications"].setdefault(key, {}).update({"prepared_foundation": True, "prepared_by": actor_id, "prepared_tick": state["clock"]["tick"]})
        _evidence(state, state["clock"]["tick"], f"frontier plot {key} prepared", [actor_id], {"stone": 1}, ["shovel"], evidence["survey"], None, [f"survey:{actor_id}:{key}"], ["foundation suitability", "physical preparation"])
        return {"accepted": True, "type": action_type, "location": location, "physical_change": True}
    if action_type == "deposit_material":
        player = state["players"].get(actor_id)
        resource, amount = action.get("resource"), action.get("amount")
        warehouse = state["places"]["warehouse"]["location"]
        if not player or _distance(player.get("location", [-99, -99]), warehouse) > 1:
            return {"accepted": False, "reason": "deposit requires physical delivery beside the warehouse"}
        if not isinstance(resource, str) or not isinstance(amount, int) or amount < 1 or player.get("inventory", {}).get(resource, 0) < amount:
            return {"accepted": False, "reason": "actor custody does not contain the requested deposit"}
        before = int(state["resources"].get(resource, 0))
        player["inventory"][resource] -= amount
        state["resources"][resource] = before + amount
        record = {"tick": state["clock"]["tick"], "actor": actor_id, "resource": resource, "amount": amount, "actor_after": player["inventory"][resource], "communal_before": before, "communal_after": state["resources"][resource], "conserved": True}
        state["environment"].setdefault("deposit_history", []).append(record)
        _evidence(state, state["clock"]["tick"], f"physical {resource} deposit", [actor_id], {resource: amount}, ["warehouse scale"], record, "dev", [], ["custody transfer", "communal count"])
        return {"accepted": True, "type": action_type, "deposit": record, "physical_change": True}
    if action_type == "join":
        requested = action.get("location", [8, 5])
        location = requested if isinstance(requested, list) and len(requested) == 2 and all(isinstance(value, int) and 0 <= value < 64 for value in requested) else [8, 5]
        player = state["players"].setdefault(actor_id, {"id": actor_id, "joined_tick": state["clock"]["tick"], "inventory": {}, "equipment": {}, "reputation": 0, "known_cases": [], "energy": 100.0})
        player.setdefault("id", actor_id)
        player["location"] = location
        player.setdefault("current_region", "settlement")
        player.setdefault("discovered_regions", ["settlement"])
        player.setdefault("competencies", {"observe": 0.25, "measure": 0.2, "engineering": 0.1})
        player.setdefault("competency_records", {})
        player.setdefault("route", None)
        _reveal_frontier(state, actor_id, location)
        return {"accepted": True, "type": action_type}
    if action_type == "interact_site":
        return interact_resource_site(state, actor_id, action)
    if action_type == "explore_region":
        player = state["players"].get(actor_id)
        target = action.get("region")
        if not player:
            return {"accepted": False, "reason": "join the world before adventuring"}
        regions = state["environment"]["regions"]
        current = player.get("current_region", "settlement")
        if target not in regions.get(current, {}).get("adjacent", []):
            return {"accepted": False, "reason": "that region is not reachable from the current region"}
        if current == "settlement" and not (player["location"][0] in {0, 18} or player["location"][1] in {0, 18}):
            return {"accepted": False, "reason": "reach the settlement boundary before beginning an expedition"}
        player["current_region"] = target
        if target not in player["discovered_regions"]:
            player["discovered_regions"].append(target)
        player["location"] = [9, 9]
        consequence = _remember_consequence(state, state["clock"]["tick"], f"expedition:{actor_id}:{current}", f"region-discovered:{target}", [actor_id])
        return {"accepted": True, "type": action_type, "from_region": current, "region": target, "discovery": consequence["id"], "physical_change": True}
    if action_type == "gather_material":
        player = state["players"].get(actor_id)
        resource = action.get("resource")
        amount = action.get("amount", 1)
        if not player or player.get("current_region", "settlement") == "settlement":
            return {"accepted": False, "reason": "material gathering requires an expedition outside the settlement"}
        region = state["environment"]["regions"][player["current_region"]]
        available = region["stocks"].get(resource, 0)
        if resource not in {"timber", "stone", "raw_food", "fuel", "containers"} or not isinstance(amount, int) or not 1 <= amount <= 3:
            return {"accepted": False, "reason": "unsupported material or gathering amount"}
        if available < amount:
            return {"accepted": False, "reason": "the observable local stock is insufficient"}
        if resource == "stone" and player["inventory"].get("tools", 0) < 1:
            return {"accepted": False, "reason": "stone gathering requires a checked-out tool"}
        region["stocks"][resource] -= amount
        player["inventory"][resource] = player["inventory"].get(resource, 0) + amount
        extraction = {"tick": state["clock"]["tick"], "actor": actor_id, "region": player["current_region"], "resource": resource, "amount": amount, "remaining": region["stocks"][resource]}
        state["environment"]["extraction_history"].append(extraction)
        signal = _update_material_signal(state, resource, state["clock"]["tick"], f"player-extraction:{actor_id}")
        _remember_consequence(state, state["clock"]["tick"], f"gather:{actor_id}:{player['current_region']}", f"inventory-gain:{resource}:{amount}", [actor_id])
        return {"accepted": True, "type": action_type, "extraction": extraction, "market_signal": signal, "physical_change": True}
    if action_type == "travel_route":
        player = state["players"].get(actor_id)
        destination = action.get("destination")
        if not player:
            return {"accepted": False, "reason": "join the world before traveling"}
        if not isinstance(destination, list) or len(destination) != 2 or not all(isinstance(value, int) and 0 <= value < 64 for value in destination):
            return {"accepted": False, "reason": "destination_outside_frontier"}
        knowledge = state.get("discoveries", {}).get(actor_id, {})
        known = {tuple(int(value) for value in key.split(",", 1)) for key in knowledge}
        grid = FrontierGrid(state["frontier"]["seed"], state["frontier"]["size"])
        result = grid.find_route(tuple(player["location"]), tuple(destination), known=known, modifications=state.get("terrain_modifications", {}))
        if not result.reached:
            return {"accepted": False, "reason": result.reason, "physical_change": False}
        route = {
            "id": f"route:{actor_id}:{state['clock']['tick']}:{destination[0]},{destination[1]}",
            "path": [list(position) for position in result.path], "index": 0, "status": "traveling",
            "cost_milli": result.cost_milli, "started_tick": state["clock"]["tick"],
        }
        player["route"] = route
        return {"accepted": True, "type": action_type, "route": copy.deepcopy(route["path"]), "cost_milli": route["cost_milli"], "physical_change": False}
    if action_type == "move":
        player = state["players"].get(actor_id)
        destination = action.get("location")
        if not player:
            return {"accepted": False, "reason": "join the world before moving"}
        if not isinstance(destination, list) or len(destination) != 2 or not all(isinstance(value, int) and 0 <= value <= 18 for value in destination):
            return {"accepted": False, "reason": "destination is outside the settlement map"}
        if _distance(player["location"], destination) != 1:
            return {"accepted": False, "reason": "movement is limited to one adjacent tile per action"}
        origin = list(player["location"])
        player["location"] = destination
        return {"accepted": True, "type": action_type, "from": origin, "to": destination, "physical_change": True}
    if action_type in {"checkout_resource", "request_supervised_checkout"}:
        player = state["players"].get(actor_id)
        governance = state["institutions"]["governance"]
        resource, amount = action.get("resource"), action.get("amount")
        supervised = action_type == "request_supervised_checkout"
        if not player:
            return {"accepted": False, "reason": "join the world before requesting custody of resources"}
        if governance["resource_access"]["mode"] != "recorded_checkout":
            return {"accepted": False, "reason": "the settlement has not established a recorded checkout process"}
        if player["location"] != state["places"]["meeting_hall"]["location"]:
            return {"accepted": False, "reason": "resource checkout must be recorded at the meeting hall"}
        if any(item["borrower"] == actor_id and item["status"] == "overdue" for item in governance["checkouts"]):
            return {"accepted": False, "reason": "an overdue checkout must be resolved before another is issued"}
        active_case = next((case for case in state["institutions"]["justice"]["cases"] if case.get("accused") == actor_id and case["status"] in {"restitution_due", "bounty_active"}), None)
        trust = _relationship(state, "dev", actor_id)["trust"]
        if active_case:
            return {"accepted": False, "reason": "recorded restitution must be resolved before Dev can issue settlement property", "case_id": active_case["id"]}
        if not supervised and trust < 0.35:
            recent = next((item for item in reversed(governance["access_refusals"]) if item["actor_id"] == actor_id and state["clock"]["tick"] - item["tick"] < 6), None)
            if recent:
                refusal = recent
            else:
                refusal = {
                    "id": f"access-refusal-{len(governance['access_refusals']) + 1}", "tick": state["clock"]["tick"],
                    "actor_id": actor_id, "decided_by": "dev", "trust": trust, "status": "recoverable",
                    "reason": "the custody history does not support an ordinary checkout",
                    "recovery_option": "request_supervised_checkout",
                }
                governance["access_refusals"].append(refusal)
                state["npcs"]["dev"]["memories"].append({"tick": state["clock"]["tick"], "kind": "cooperation_refusal", "actor": actor_id, "text": f"Declined ordinary custody for {actor_id} at trust {trust:.2f}; offered a supervised recovery checkout."})
                _remember_consequence(state, state["clock"]["tick"], f"relationship-history:dev:{actor_id}:{trust}", f"cooperation-refused:{refusal['id']}", [actor_id, "dev"])
            return {"accepted": False, "reason": refusal["reason"], "refusal": copy.deepcopy(refusal), "recovery_option": refusal["recovery_option"], "physical_change": False}
        if supervised and amount != 1:
            return {"accepted": False, "reason": "supervised recovery is limited to exactly one accountable unit"}
        if resource not in {"raw_food", "tested_water", "fuel", "timber", "stone", "containers", "tools"} or not isinstance(amount, int) or not 1 <= amount <= 3:
            return {"accepted": False, "reason": "resource or checkout amount is not permitted"}
        if state["resources"].get(resource, 0) < amount:
            return {"accepted": False, "reason": "settlement stock is insufficient"}
        state["resources"][resource] -= amount
        player["inventory"][resource] = player["inventory"].get(resource, 0) + amount
        checkout = {
            "id": f"checkout-{len(governance['checkouts']) + 1}", "borrower": actor_id, "status": "active",
            "quantity": {resource: amount}, "remaining": {resource: amount}, "issued_tick": state["clock"]["tick"],
            "due_tick": state["clock"]["tick"] + (12 if supervised else 48), "purpose": str(action.get("purpose", "general work"))[:120],
            "supervised": supervised, "issued_by": "dev", "trust_at_issue": trust,
        }
        governance["checkouts"].append(checkout)
        _remember_consequence(state, state["clock"]["tick"], "world-rule:recorded_checkout", f"checkout:{checkout['id']}", [actor_id, "dev"])
        return {"accepted": True, "type": action_type, "checkout": checkout, "physical_change": True}
    if action_type == "return_checkout":
        player = state["players"].get(actor_id)
        governance = state["institutions"]["governance"]
        checkout = next((item for item in governance["checkouts"] if item["id"] == action.get("checkout_id") and item["borrower"] == actor_id), None)
        resource, amount = action.get("resource"), action.get("amount")
        if not player or not checkout or checkout["status"] not in {"active", "overdue"}:
            return {"accepted": False, "reason": "no returnable checkout belongs to this actor"}
        if player["location"] != state["places"]["meeting_hall"]["location"]:
            return {"accepted": False, "reason": "checked-out resources must be returned at the meeting hall"}
        owed = checkout["remaining"].get(resource, 0)
        if not isinstance(amount, int) or amount < 1 or amount > owed or player["inventory"].get(resource, 0) < amount:
            return {"accepted": False, "reason": "returned quantity is not held and checked out"}
        was_overdue = checkout["status"] == "overdue"
        player["inventory"][resource] -= amount
        state["resources"][resource] = state["resources"].get(resource, 0) + amount
        checkout["remaining"][resource] -= amount
        if all(value == 0 for value in checkout["remaining"].values()):
            checkout["status"] = "returned_after_followup" if was_overdue else "returned_on_time"
            checkout["returned_tick"] = state["clock"]["tick"]
            player["reputation"] += 1
            trust_gain = 0.12 if checkout.get("supervised") else 0.08
            recovered_trust = _adjust_trust(state, "dev", actor_id, trust_gain, checkout["id"], state["clock"]["tick"])
            state["npcs"]["dev"]["memories"].append({"tick": state["clock"]["tick"], "kind": "completed_work", "text": f"{actor_id} returned checkout {checkout['id']} with its custody record intact."})
            _remember_consequence(state, state["clock"]["tick"], f"checkout:{checkout['id']}", f"custody-completed:{checkout['status']}", [actor_id, "dev"])
            if checkout.get("supervised"):
                _remember_consequence(state, state["clock"]["tick"], f"supervised-custody:{checkout['id']}", f"trust-recovered:{actor_id}:{recovered_trust}", [actor_id, "dev"])
                if recovered_trust >= 0.35:
                    for refusal in state["institutions"]["governance"].get("access_refusals", []):
                        if refusal["actor_id"] == actor_id and refusal["status"] == "recoverable":
                            refusal["status"] = "resolved"
                            refusal["resolved_tick"] = state["clock"]["tick"]
                            refusal["resolution"] = checkout["id"]
        return {"accepted": True, "type": action_type, "checkout_id": checkout["id"], "remaining": dict(checkout["remaining"]), "status": checkout["status"], "physical_change": True}
    if action_type == "misappropriate_resource":
        player = state["players"].get(actor_id)
        resource, amount = action.get("resource"), action.get("amount")
        if not player:
            return {"accepted": False, "reason": "join the world before interacting with resources"}
        if resource not in {"raw_food", "tested_water", "fuel", "timber", "stone", "containers", "tools"} or not isinstance(amount, int) or not 1 <= amount <= 3:
            return {"accepted": False, "reason": "resource or amount is not permitted"}
        if state["resources"].get(resource, 0) < amount:
            return {"accepted": False, "reason": "settlement stock is insufficient"}
        state["resources"][resource] -= amount
        player["inventory"][resource] = player["inventory"].get(resource, 0) + amount
        conduct = _remember_consequence(state, state["clock"]["tick"], f"player-action:{actor_id}:misappropriate", f"inventory-transfer:settlement->{actor_id}", [actor_id])
        conduct.update({"kind": "misappropriation", "actor": actor_id, "resource": resource, "quantity": {resource: amount}, "location": list(player["location"]), "physical": True})
        witnesses = []
        for npc in state["npcs"].values():
            distance = _distance(npc["location"], player["location"])
            if distance > 4:
                continue
            confidence = round(max(0.55, 0.96 - distance * 0.09), 2)
            npc["memories"].append({"tick": state["clock"]["tick"], "kind": "witnessed_conduct", "conduct_id": conduct["id"], "actor": actor_id, "confidence": confidence, "reported": False, "text": f"Saw {actor_id} take {amount} {resource} from settlement stock without a work order."})
            _adjust_trust(state, npc["id"], actor_id, -0.08 * confidence, conduct["id"], state["clock"]["tick"])
            witnesses.append(npc["id"])
        conduct["witnesses"] = witnesses
        return {"accepted": True, "type": action_type, "conduct_id": conduct["id"], "witness_count": len(witnesses), "physical_change": True}
    if action_type == "return_resource":
        player = state["players"].get(actor_id)
        case_id, resource, amount = action.get("case_id"), action.get("resource"), action.get("amount")
        case = next((item for item in state["institutions"]["justice"]["cases"] if item["id"] == case_id and item["accused"] == actor_id), None)
        if not player or not case or case["status"] not in {"restitution_due", "bounty_active"}:
            return {"accepted": False, "reason": "no recoverable restitution case belongs to this actor"}
        bounty = next((item for item in state["institutions"]["justice"]["bounties"] if item["case_id"] == case["id"] and item["status"] == "active"), None)
        if case["status"] == "restitution_due" and player["location"] != state["places"]["meeting_hall"]["location"]:
            return {"accepted": False, "reason": "voluntary restitution must be delivered to the meeting hall"}
        if case["status"] == "bounty_active" and (not bounty or not bounty.get("contact") or bounty["contact"]["location"] != player["location"]):
            return {"accepted": False, "reason": "recovery requires documented contact at the actor's current location"}
        owed = case["restitution"].get(resource, 0)
        if not isinstance(amount, int) or amount < 1 or amount > owed or player["inventory"].get(resource, 0) < amount:
            return {"accepted": False, "reason": "returned quantity is not held and owed"}
        player["inventory"][resource] -= amount
        state["resources"][resource] = state["resources"].get(resource, 0) + amount
        case["restitution"][resource] -= amount
        complete = all(value == 0 for value in case["restitution"].values())
        if complete:
            case["status"] = "closed_restituted"
            case["closed_tick"] = state["clock"]["tick"]
            player["reputation"] += 4
            for active_bounty in state["institutions"]["justice"]["bounties"]:
                if active_bounty["case_id"] != case["id"] or active_bounty["status"] != "active":
                    continue
                if active_bounty.get("contact") and active_bounty.get("assignee"):
                    active_bounty["status"] = "completed_recovery"
                    collector = active_bounty["assignee"]["id"]
                    _provisional_claim(state, state["clock"]["tick"], collector, "verified public recovery", active_bounty["provisional_reward"], f"bounty:{active_bounty['id']}")
                else:
                    active_bounty["status"] = "cancelled_restituted"
                active_bounty["closed_tick"] = state["clock"]["tick"]
            _remember_consequence(state, state["clock"]["tick"], f"restitution:{case['id']}", f"case-closed:{case['id']}", [actor_id, "sora"])
        return {"accepted": True, "type": action_type, "case_id": case_id, "remaining": dict(case["restitution"]), "case_status": case["status"], "physical_change": True}
    if action_type == "accept_bounty":
        player = state["players"].get(actor_id)
        bounty = next((item for item in state["institutions"]["justice"]["bounties"] if item["id"] == action.get("bounty_id")), None)
        if not player:
            return {"accepted": False, "reason": "join the world before accepting public duty"}
        if not bounty or bounty["status"] != "active" or bounty.get("assignee") is not None:
            return {"accepted": False, "reason": "bounty is unavailable or already accepted"}
        if bounty["subject"] == actor_id:
            return {"accepted": False, "reason": "the subject cannot collect their own recovery bounty"}
        bounty["assignee"] = {"id": actor_id, "kind": "player", "accepted_tick": state["clock"]["tick"]}
        _remember_consequence(state, state["clock"]["tick"], f"bounty:{bounty['id']}", f"recovery-duty:{actor_id}", [actor_id, bounty["subject"]])
        return {"accepted": True, "type": action_type, "bounty_id": bounty["id"], "provisional_reward": bounty["provisional_reward"], "physical_change": False}
    if action_type == "request_restitution":
        player = state["players"].get(actor_id)
        bounty = next((item for item in state["institutions"]["justice"]["bounties"] if item["id"] == action.get("bounty_id")), None)
        if not player or not bounty or bounty["status"] != "active" or (bounty.get("assignee") or {}).get("id") != actor_id:
            return {"accepted": False, "reason": "this actor has no active recovery assignment"}
        subject = state["players"].get(bounty["subject"])
        if not subject or subject["location"] != player["location"]:
            return {"accepted": False, "reason": "the subject is not present at this tile"}
        bounty["contact"] = {"tick": state["clock"]["tick"], "collector": actor_id, "location": list(player["location"]), "status": "restitution_requested"}
        _remember_consequence(state, state["clock"]["tick"], f"recovery-duty:{actor_id}", f"contact:{bounty['id']}", [actor_id, bounty["subject"]])
        return {"accepted": True, "type": action_type, "bounty_id": bounty["id"], "subject": bounty["subject"], "physical_change": False}
    if action_type == "publish_order":
        order = {"id": str(uuid.uuid4()), "author": actor_id, "priority": action.get("priority"), "terms": action.get("terms", {}), "status": "proposed", "tick": state["clock"]["tick"]}
        state["event"]["competing_orders"].append(order)
        return {"accepted": True, "type": action_type, "order": order}
    if action_type == "select_order":
        order_id = action.get("order_id")
        if not any(order["id"] == order_id for order in state["event"]["competing_orders"]):
            return {"accepted": False, "reason": "unknown work order"}
        state["event"]["selected_order"] = order_id
        return {"accepted": True, "type": action_type, "order_id": order_id}
    if action_type == "observe":
        return {"accepted": True, "type": action_type, "physical_change": False, "state_revision_required": True}
    if action_type == "speak":
        player = state["players"].get(actor_id)
        content = str(action.get("content", "")).strip()[:500]
        if not player or not content:
            return {"accepted": False, "reason": "join the world and provide audible words"}
        target_id = str(action.get("target_id", "")).strip() or None
        heard = [npc for npc in state["npcs"].values() if _distance(npc["location"], player["location"]) <= 4]
        player_message = {"id": str(uuid.uuid4()), "tick": state["clock"]["tick"], "speaker_id": actor_id, "speaker": actor_id, "content": content, "kind": "player", "audible_to": [npc["id"] for npc in heard], "location": list(player["location"])}
        state["communications"]["messages"].append(player_message)
        civic_claim = _record_witnessed_discourse(state, player_message)
        replies = []
        respondents = sorted(heard, key=lambda item: (0 if item["id"] == target_id else 1, _distance(item["location"], player["location"]), item["id"]))[:2]
        for npc in respondents:
            reply = {"id": str(uuid.uuid4()), "tick": state["clock"]["tick"], "speaker_id": npc["id"], "speaker": npc["name"], "content": _npc_reply(npc, content, state, actor_id), "kind": "reply", "response_to": player_message["id"], "audible_to": [actor_id], "location": list(npc["location"])}
            state["communications"]["messages"].append(reply)
            npc["memories"].append({"tick": state["clock"]["tick"], "kind": "conversation", "actor": actor_id, "text": f"Heard {actor_id} say: {content}"})
            replies.append(reply)
        state["communications"]["messages"] = state["communications"]["messages"][-250:]
        return {"accepted": True, "type": action_type, "heard_by": [npc["id"] for npc in heard], "replies": replies, "civic_claim": civic_claim, "physical_change": False}
    if action_type == "endorse_priority":
        priority = action.get("priority")
        if priority not in INITIATIVE_BLUEPRINTS:
            return {"accepted": False, "reason": "unknown civic priority"}
        state["institutions"]["council"]["endorsements"][actor_id] = priority
        state["npcs"]["sora"]["memories"].append({"tick": state["clock"]["tick"], "kind": "public_input", "text": f"{actor_id} endorsed {priority} for the next evidence review."})
        _remember_consequence(state, state["clock"]["tick"], f"player-endorsement:{actor_id}", f"council-pressure:{priority}", [actor_id, "sora"])
        return {"accepted": True, "type": action_type, "priority": priority, "physical_change": False}
    return {"accepted": False, "reason": "unsupported action"}
