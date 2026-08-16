"""Canonical consequential-action kernel shared by human and AI actors.

The kernel owns structural behavior only. Scenario catalogs supply names, lore,
materials, recipes, and governments. Input devices and autonomous planners may
propose actions, but none bypass this state machine.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
from typing import Any, Dict, Iterable, List, Optional, Set
import copy
import json

from causal_ledger import CausalEvent, CausalLedger
from competency_engine import CompetencyProfile, practice


TERMINAL_STATES = {"refused", "cancelled", "rejected", "retired", "lost"}


@dataclass(frozen=True)
class ActionRequirements:
    materials: Dict[str, int] = field(default_factory=dict)
    tools: Dict[str, float] = field(default_factory=dict)  # minimum condition
    station: Optional[str] = None
    energy: int = 0
    competence_domain: Optional[str] = None
    minimum_competence: float = 0.0
    perception_channels: Set[str] = field(default_factory=set)
    duration_ticks: int = 1


@dataclass(frozen=True)
class ActionDefinition:
    action_type: str
    requirements: ActionRequirements
    output_item: Optional[str] = None
    output_amount: int = 0
    provisional_cu_milli: int = 0
    verification_tolerance: float = 0.0
    execution_model: str = "measurement_series"
    verification_threshold: float = 0.0
    verifier_competence_domain: Optional[str] = None
    minimum_verifier_competence: float = 0.0
    output_custody: str = "commissioned_store"


@dataclass
class ActorContext:
    actor_id: str
    actor_kind: str  # human or ai; intentionally not used to relax gates
    perspective: str
    perceptions: Set[str]
    energy: int
    competencies: CompetencyProfile
    memories: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ActionRecord:
    action_id: str
    definition: ActionDefinition
    actor_id: str
    intent: str
    target_id: str
    location: str
    observations: List[str]
    state: str = "proposed"
    proposed_tick: int = 0
    reserved_tick: Optional[int] = None
    submitted_tick: Optional[int] = None
    verifier_id: Optional[str] = None
    samples: List[Dict[str, float]] = field(default_factory=list)
    failure_reason: Optional[str] = None
    output: Dict[str, Any] = field(default_factory=dict)
    ledger_event_ids: List[str] = field(default_factory=list)


@dataclass
class ActionWorld:
    tick: int = 0
    inventories: Dict[str, Dict[str, int]] = field(default_factory=dict)
    tools: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    stations: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    reservations: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    actor_commitments: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    resource_sites: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    unverified_outputs: Dict[str, Dict[str, int]] = field(default_factory=dict)
    commissioned_outputs: Dict[str, Dict[str, int]] = field(default_factory=dict)
    valuation_accounts_milli: Dict[str, int] = field(default_factory=lambda: {"treasury": 0})
    valuation_claims: List[Dict[str, Any]] = field(default_factory=list)


class SharedActionEngine:
    def __init__(self, world: Optional[ActionWorld] = None, ledger: Optional[CausalLedger] = None):
        self.world = world or ActionWorld()
        self.ledger = ledger or CausalLedger()
        self.actions: Dict[str, ActionRecord] = {}

    def _event(self, action: ActionRecord, state: str, actor_id: str, *, inputs=None, outputs=None,
               evidence=None, physical=False) -> CausalEvent:
        prior = self.ledger.events[-1] if self.ledger.events else None
        parents = [action.ledger_event_ids[-1]] if action.ledger_event_ids else []
        event = CausalEvent(
            event_id=f"{action.action_id}:{len(action.ledger_event_ids) + 1}:{state}",
            sequence=len(self.ledger.events) + 1,
            tick=self.world.tick,
            event_type="shared_action",
            actor_id=actor_id,
            action_id=action.action_id,
            state=state,
            intent=action.intent,
            location=action.location,
            parent_event_ids=parents,
            inputs=copy.deepcopy(inputs or {}),
            outputs=copy.deepcopy(outputs or {}),
            evidence=copy.deepcopy(evidence or []),
            physical_effect=physical,
            previous_hash=prior.event_hash if prior else "GENESIS",
        )
        self.ledger.append(event)
        action.state = state
        action.ledger_event_ids.append(event.event_id)
        return event

    def propose(self, action_id: str, definition: ActionDefinition, actor: ActorContext, intent: str,
                target_id: str, location: str, observations: Iterable[str]) -> ActionRecord:
        if action_id in self.actions:
            raise ValueError("Action ID already exists")
        action = ActionRecord(action_id, definition, actor.actor_id, intent, target_id, location,
                              list(observations), proposed_tick=self.world.tick)
        self.actions[action_id] = action
        self._event(action, "proposed", actor.actor_id, evidence=[{"kind": "perception", "ids": action.observations}])
        return action

    def accept(self, action_id: str, actor: ActorContext, accepted: bool = True) -> ActionRecord:
        action = self.actions[action_id]
        if actor.actor_id != action.actor_id:
            raise PermissionError("Only the proposed actor may accept or refuse their labor")
        if action.state != "proposed":
            raise ValueError("Proposed action required")
        existing = self.world.actor_commitments.get(actor.actor_id)
        if accepted and existing and existing.get("action_id") != action_id:
            raise ValueError(f"actor already committed to {existing['action_id']}")
        if accepted:
            self.world.actor_commitments[actor.actor_id] = {"action_id": action_id, "since_tick": self.world.tick, "role": "performer"}
        else:
            self.world.actor_commitments.pop(actor.actor_id, None)
        self._event(action, "accepted" if accepted else "refused", actor.actor_id)
        return action

    def cancel(self, action_id: str, actor: ActorContext) -> ActionRecord:
        action = self.actions[action_id]
        if actor.actor_id != action.actor_id or action.state not in {"accepted", "reserved"}:
            raise ValueError("Participating actor with accepted or reserved work required")
        reservation = self.world.reservations.pop(action_id, None)
        if reservation:
            for tool_id in reservation.get("tools", []):
                if self.world.tools.get(tool_id, {}).get("reserved_by") == action_id:
                    self.world.tools[tool_id]["reserved_by"] = None
            station_id = reservation.get("station")
            if station_id and self.world.stations.get(station_id, {}).get("reserved_by") == action_id:
                self.world.stations[station_id]["reserved_by"] = None
            site_id = reservation.get("target_site")
            if site_id and self.world.resource_sites.get(site_id, {}).get("reserved_by") == action_id:
                self.world.resource_sites[site_id]["reserved_by"] = None
        self.world.actor_commitments.pop(actor.actor_id, None)
        self._event(action, "cancelled", actor.actor_id, evidence=[{"kind": "participant_cancellation"}])
        return action

    def reserve(self, action_id: str, actor: ActorContext) -> ActionRecord:
        action = self.actions[action_id]
        req = action.definition.requirements
        if action.state != "accepted" or actor.actor_id != action.actor_id:
            raise ValueError("Accepted actor action required")
        missing_perception = sorted(req.perception_channels - actor.perceptions)
        if missing_perception:
            raise ValueError(f"missing perception: {', '.join(missing_perception)}")
        competency = actor.competencies.get(req.competence_domain).demonstrated if req.competence_domain else 1.0
        if competency < req.minimum_competence:
            raise ValueError("insufficient demonstrated competence")
        inventory = self.world.inventories.setdefault(actor.actor_id, {})
        missing_materials = {name: amount - inventory.get(name, 0) for name, amount in req.materials.items() if inventory.get(name, 0) < amount}
        if missing_materials:
            raise ValueError(f"missing materials: {missing_materials}")
        for tool_id, condition in req.tools.items():
            tool = self.world.tools.get(tool_id)
            if not tool or tool.get("condition", 0) < condition or tool.get("reserved_by") not in {None, action_id}:
                raise ValueError(f"tool unavailable: {tool_id}")
        station = self.world.stations.get(req.station) if req.station else None
        if req.station and (not station or station.get("reserved_by") not in {None, action_id}):
            raise ValueError(f"station unavailable: {req.station}")
        if actor.energy < req.energy:
            raise ValueError("insufficient energy")
        target_site = self.world.resource_sites.get(action.target_id) if action.definition.execution_model == "finite_site_extraction" else None
        if target_site and (target_site.get("stock", 0) < action.definition.output_amount or target_site.get("reserved_by") not in {None, action_id}):
            raise ValueError("finite resource site unavailable")
        for tool_id in req.tools:
            self.world.tools[tool_id]["reserved_by"] = action_id
        if station is not None:
            station["reserved_by"] = action_id
        if target_site:
            target_site["reserved_by"] = action_id
        self.world.reservations[action_id] = {"materials": copy.deepcopy(req.materials), "tools": sorted(req.tools), "station": req.station, "target_site": action.target_id if target_site else None, "actor": actor.actor_id}
        action.reserved_tick = self.world.tick
        self._event(action, "reserved", actor.actor_id, inputs=self.world.reservations[action_id])
        return action

    def execute(self, action_id: str, actor: ActorContext, samples: List[Dict[str, float]]) -> ActionRecord:
        action = self.actions[action_id]
        req = action.definition.requirements
        if action.state != "reserved" or actor.actor_id != action.actor_id:
            raise ValueError("Reserved actor action required")
        self._event(action, "in_progress", actor.actor_id, evidence=[{"kind": "ordered_samples", "samples": samples}])
        self.world.tick += req.duration_ticks
        actor.energy -= req.energy
        inventory = self.world.inventories[actor.actor_id]
        for name, amount in req.materials.items():
            inventory[name] -= amount
        for tool_id in req.tools:
            self.world.tools[tool_id]["condition"] = max(0.0, self.world.tools[tool_id]["condition"] - 0.01)
            self.world.tools[tool_id]["reserved_by"] = None
        if req.station:
            self.world.stations[req.station]["reserved_by"] = None
        reservation = self.world.reservations.pop(action_id, None)
        if reservation and reservation.get("target_site") and self.world.resource_sites.get(reservation["target_site"], {}).get("reserved_by") == action_id:
            self.world.resource_sites[reservation["target_site"]]["reserved_by"] = None
        action.samples = copy.deepcopy(samples)
        if action.definition.execution_model == "thermal_batch":
            observations = [
                (float(sample["temperature_c"]), float(sample["duration_minutes"]))
                for sample in samples
                if isinstance(sample, dict)
                and isinstance(sample.get("temperature_c"), (int, float))
                and isinstance(sample.get("duration_minutes"), (int, float))
                and sample["duration_minutes"] > 0
            ]
            if not observations:
                action.failure_reason = "no measured thermal history"
                self._event(action, "failed", actor.actor_id, outputs={"reason": action.failure_reason}, physical=True)
                self.world.actor_commitments.pop(actor.actor_id, None)
                return action
            lethal_exposure = sum(max(0.0, temperature - 55.0) * minutes for temperature, minutes in observations)
            thermal_score = min(1.0, lethal_exposure / 300.0)
            scorch_exposure = sum(max(0.0, temperature - 100.0) * minutes for temperature, minutes in observations)
            quality = max(0.0, 1.0 - scorch_exposure / 300.0)
            safety = round(min(0.98, 0.52 + thermal_score * 0.46), 4)
            action.output = {
                "sample_count": len(observations), "safety": safety, "quality": round(quality, 4),
                "peak_temperature_c": round(max(item[0] for item in observations), 3),
                "heated_minutes": round(sum(item[1] for item in observations), 3),
            }
            execution_evidence = [{"kind": "thermal_history", "observations": [{"temperature_c": t, "duration_minutes": m} for t, m in observations]}]
        elif action.definition.execution_model == "condition_restoration":
            observations = [
                (float(sample["condition_before"]), float(sample["condition_after"]))
                for sample in samples if isinstance(sample, dict)
                and isinstance(sample.get("condition_before"), (int, float))
                and isinstance(sample.get("condition_after"), (int, float))
            ]
            if not observations:
                action.failure_reason = "no condition measurements"
                self._event(action, "failed", actor.actor_id, outputs={"reason": action.failure_reason}, physical=True)
                self.world.actor_commitments.pop(actor.actor_id, None)
                return action
            before = observations[0][0]
            tool_condition = self.world.tools[next(iter(req.tools))]["condition"] if req.tools else 1.0
            after = round(min(1.0, before + 0.62 * tool_condition), 4)
            action.output = {"condition_before": round(before, 4), "condition_after": after, "measured_samples": len(observations)}
            execution_evidence = [{"kind": "condition_restoration_record", "observations": [{"condition_before": a, "condition_after": b} for a, b in observations], "computed_condition_after": after}]
        elif action.definition.execution_model == "finite_site_extraction":
            observations = [(int(sample["stock_before"]), int(sample["observed_yield"])) for sample in samples if isinstance(sample, dict) and isinstance(sample.get("stock_before"), (int, float)) and isinstance(sample.get("observed_yield"), (int, float))]
            site = self.world.resource_sites.get(action.target_id)
            if not observations or not site or site.get("stock", 0) < action.definition.output_amount:
                action.failure_reason = "no conserved finite-site yield"
                self._event(action, "failed", actor.actor_id, outputs={"reason": action.failure_reason}, physical=False)
                self.world.actor_commitments.pop(actor.actor_id, None)
                return action
            before = int(site["stock"]); amount = action.definition.output_amount
            site["stock"] -= amount
            action.output = {"resource": action.definition.output_item, "yield": amount, "observed_yield": observations[0][1], "stock_before": before, "stock_after": int(site["stock"]), "conserved": before - int(site["stock"]) == amount}
            execution_evidence = [{"kind": "finite_site_stock_change", "site_id": action.target_id, "measurements": copy.deepcopy(action.output)}]
        else:
            readings = [sample.get("reading") for sample in samples if isinstance(sample.get("reading"), (int, float))]
            if not readings:
                action.failure_reason = "no measurable samples"
                self._event(action, "failed", actor.actor_id, outputs={"reason": action.failure_reason}, physical=True)
                self.world.actor_commitments.pop(actor.actor_id, None)
                return action
            spread = max(readings) - min(readings)
            action.output = {"sample_count": len(readings), "spread": round(spread, 6), "mean": round(sum(readings) / len(readings), 6)}
            execution_evidence = [{"kind": "measurement_series", "readings": readings}]
        if action.definition.output_item:
            self.world.unverified_outputs.setdefault(actor.actor_id, {})[action.definition.output_item] = action.definition.output_amount
        action.submitted_tick = self.world.tick
        self._event(action, "submitted", actor.actor_id, outputs=action.output, evidence=execution_evidence, physical=True)
        return action

    def verify(self, action_id: str, verifier: ActorContext) -> ActionRecord:
        action = self.actions[action_id]
        if action.state != "submitted":
            raise ValueError("Submitted action required")
        if verifier.actor_id == action.actor_id:
            raise ValueError("Verification must be independent")
        verifier_channel = "resource_detail" if action.definition.execution_model == "finite_site_extraction" else "instrumentation"
        if verifier_channel not in verifier.perceptions:
            raise ValueError(f"Verifier lacks {verifier_channel} perception")
        verifier_domain = action.definition.verifier_competence_domain
        if verifier_domain and verifier.competencies.get(verifier_domain).demonstrated < action.definition.minimum_verifier_competence:
            raise ValueError("Verifier lacks demonstrated competence")
        action.verifier_id = verifier.actor_id
        if action.definition.execution_model == "thermal_batch":
            passed = action.output.get("safety", 0.0) >= action.definition.verification_threshold
            verification_evidence = [{"kind": "independent_safety_check", "threshold": action.definition.verification_threshold, "observed_safety": action.output.get("safety")}]
        elif action.definition.execution_model == "condition_restoration":
            passed = action.output.get("condition_after", 0.0) >= action.definition.verification_threshold
            verification_evidence = [{"kind": "independent_condition_check", "threshold": action.definition.verification_threshold, "observed_condition": action.output.get("condition_after")}]
        elif action.definition.execution_model == "finite_site_extraction":
            passed = bool(action.output.get("conserved")) and action.output.get("yield") == action.output.get("observed_yield")
            verification_evidence = [{"kind": "independent_stock_and_yield_check", **copy.deepcopy(action.output)}]
        else:
            passed = action.output.get("spread", float("inf")) <= action.definition.verification_tolerance
            verification_evidence = [{"kind": "independent_check", "tolerance": action.definition.verification_tolerance, "observed_spread": action.output.get("spread")}]
        state = "verified" if passed else "needs_rework"
        event = self._event(action, state, verifier.actor_id, evidence=verification_evidence)
        if not passed:
            self.world.actor_commitments.pop(action.actor_id, None)
        if passed and action.definition.requirements.competence_domain:
            practice(self._actor_profile(action.actor_id), action.definition.requirements.competence_domain,
                     self._actor_perspective(action.actor_id), action.action_id, True)
        for participant_id in {action.actor_id, verifier.actor_id}:
            participant = self._actors.get(participant_id)
            if participant:
                participant.memories.append({
                    "event_id": event.event_id,
                    "belief": f"I {'performed' if participant_id == action.actor_id else 'inspected'} {action.intent}; review was {state}",
                    "confidence": 0.95 if participant_id == verifier.actor_id else 0.85,
                    "source": "perceived_causal_event",
                    "objective_hash": event.event_hash,
                })
        return action

    def commission(self, action_id: str, actor: ActorContext) -> ActionRecord:
        action = self.actions[action_id]
        if action.state != "verified":
            raise ValueError("Verified action required")
        if actor.actor_id != action.verifier_id:
            raise PermissionError("Only the independent verifier may release this output into trusted use")
        item = action.definition.output_item
        if item:
            amount = self.world.unverified_outputs.get(action.actor_id, {}).pop(item, 0)
            if action.definition.output_custody == "actor_inventory":
                inventory = self.world.inventories.setdefault(action.actor_id, {})
                inventory[item] = inventory.get(item, 0) + amount
            else:
                self.world.commissioned_outputs.setdefault(action.actor_id, {})[item] = self.world.commissioned_outputs.setdefault(action.actor_id, {}).get(item, 0) + amount
        value = action.definition.provisional_cu_milli
        if value:
            self.world.valuation_accounts_milli["treasury"] = self.world.valuation_accounts_milli.get("treasury", 0) - value
            self.world.valuation_accounts_milli[action.actor_id] = self.world.valuation_accounts_milli.get(action.actor_id, 0) + value
            self.world.valuation_claims.append({"action_id": action_id, "actor_id": action.actor_id, "amount_milli": value, "spendable": False, "evidence_event": action.ledger_event_ids[-1]})
        self._event(action, "commissioned", actor.actor_id, outputs={"item": item, "amount": action.definition.output_amount, "provisional_cu_milli": value}, physical=True)
        self.world.actor_commitments.pop(action.actor_id, None)
        return action

    def register_actor(self, actor: ActorContext) -> None:
        self.__dict__.setdefault("_actors", {})[actor.actor_id] = actor

    def _actor_profile(self, actor_id: str) -> CompetencyProfile:
        return self._actors[actor_id].competencies

    def _actor_perspective(self, actor_id: str) -> str:
        return self._actors[actor_id].perspective

    def remember_perceived(self, actor: ActorContext, event_ids: Iterable[str]) -> None:
        for event_id in event_ids:
            event = self.ledger.by_id[event_id]
            actor.memories.append({"event_id": event_id, "belief": f"I perceived {event.state}: {event.intent}", "confidence": 0.8, "source": "perceived_causal_event"})

    def digest(self) -> str:
        payload = {"world": asdict(self.world), "actions": {key: asdict(value) for key, value in sorted(self.actions.items())}, "ledger": [event.payload() | {"event_hash": event.event_hash} for event in self.ledger.events]}
        return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=sorted).encode()).hexdigest()


MEASUREMENT_TOOL_CALIBRATION = ActionDefinition(
    action_type="calibrate_measurement_tool",
    requirements=ActionRequirements(
        materials={"reference_strip": 1}, tools={"marked_measure": 0.35}, station="measurement_bench",
        energy=2, competence_domain="measurement", minimum_competence=0.1,
        perception_channels={"surface_detail", "instrumentation"}, duration_ticks=4,
    ),
    output_item="calibrated_measure",
    output_amount=1,
    provisional_cu_milli=4250,
    verification_tolerance=0.02,
    verifier_competence_domain="measurement",
    minimum_verifier_competence=0.1,
)


COMMUNAL_MEAL_PREPARATION = ActionDefinition(
    action_type="prepare_communal_meal",
    requirements=ActionRequirements(
        materials={"raw_food": 3, "tested_water": 2, "fuel": 1},
        tools={"cooking_pot": 0.5, "food_thermometer": 0.5}, station="communal_hearth",
        energy=4, competence_domain="cooking", minimum_competence=0.1,
        perception_channels={"heat_control", "instrumentation"}, duration_ticks=4,
    ),
    output_item="safe_meal_portion",
    output_amount=3,
    provisional_cu_milli=6000,
    execution_model="thermal_batch",
    verification_threshold=0.75,
    verifier_competence_domain="food_safety",
    minimum_verifier_competence=0.1,
)


MECHANICAL_PUMP_REPAIR = ActionDefinition(
    action_type="repair_mechanical_pump",
    requirements=ActionRequirements(
        materials={"timber": 1, "containers": 1},
        tools={"maintenance_wrench": 0.4}, station=None,
        energy=5, competence_domain="mechanical_engineering", minimum_competence=0.1,
        perception_channels={"mechanical_detail", "instrumentation"}, duration_ticks=6,
    ),
    output_item="serviced_pump",
    output_amount=1,
    provisional_cu_milli=7000,
    execution_model="condition_restoration",
    verification_threshold=0.8,
    verifier_competence_domain="measurement",
    minimum_verifier_competence=0.1,
)


def site_resource_extraction(resource: str, amount: int, tool: str, domain: str, energy: int) -> ActionDefinition:
    """Structural extraction definition; scenario catalogs choose its nouns."""
    return ActionDefinition(
        action_type="extract_site_resource",
        requirements=ActionRequirements(
            tools={tool: 0.35}, station=None, energy=energy,
            competence_domain=domain, minimum_competence=0.0,
            perception_channels={"resource_detail", "spatial_layout"}, duration_ticks=max(2, energy),
        ),
        output_item=resource, output_amount=amount,
        provisional_cu_milli=amount * 1500,
        execution_model="finite_site_extraction",
        verification_tolerance=0.0,
        verifier_competence_domain="measurement",
        minimum_verifier_competence=0.1,
        output_custody="actor_inventory",
    )
