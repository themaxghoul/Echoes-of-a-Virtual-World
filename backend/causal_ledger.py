"""Append-only causal event ledger with deterministic lineage and integrity checks."""

from dataclasses import asdict, dataclass, field
from hashlib import sha256
from typing import Any, Dict, List, Optional
import json


ACTION_TRANSITIONS = {
    "proposed": {"accepted", "refused"},
    "accepted": {"reserved", "cancelled"},
    "reserved": {"in_progress", "cancelled"},
    "in_progress": {"interrupted", "failed", "submitted"},
    "interrupted": {"in_progress", "cancelled"},
    "failed": {"proposed", "retired"},
    "submitted": {"verified", "rejected", "needs_rework"},
    "needs_rework": {"reserved", "retired"},
    "rejected": {"retired"},
    "verified": {"commissioned"},
    "commissioned": {"maintained", "degraded", "retired", "lost"},
    "maintained": {"commissioned", "degraded", "retired", "lost"},
    "degraded": {"maintained", "retired", "lost"},
    "refused": set(), "cancelled": set(), "retired": set(), "lost": set(),
}


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


@dataclass
class CausalEvent:
    event_id: str
    sequence: int
    tick: int
    event_type: str
    actor_id: str
    action_id: str
    state: str
    intent: str
    location: str
    parent_event_ids: List[str] = field(default_factory=list)
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    physical_effect: bool = False
    previous_hash: str = "GENESIS"
    event_hash: str = ""

    def payload(self) -> Dict[str, Any]:
        value = asdict(self)
        value.pop("event_hash", None)
        return value

    def calculate_hash(self) -> str:
        return sha256(canonical(self.payload()).encode("utf-8")).hexdigest()


class CausalLedger:
    def __init__(self, events: Optional[List[CausalEvent]] = None):
        self.events: List[CausalEvent] = events or []
        self.by_id = {event.event_id: event for event in self.events}

    def append(self, event: CausalEvent) -> CausalEvent:
        if event.event_id in self.by_id:
            raise ValueError("Duplicate causal event ID")
        if event.sequence != len(self.events) + 1:
            raise ValueError("Causal sequence must be contiguous")
        if any(parent not in self.by_id for parent in event.parent_event_ids):
            raise ValueError("Every parent cause must already exist")
        previous = self.events[-1] if self.events else None
        expected_previous = previous.event_hash if previous else "GENESIS"
        if event.previous_hash != expected_previous:
            raise ValueError("Previous hash does not match ledger head")
        action_history = [item for item in self.events if item.action_id == event.action_id]
        if action_history:
            prior_state = action_history[-1].state
            if event.state not in ACTION_TRANSITIONS.get(prior_state, set()):
                raise ValueError(f"Invalid action transition: {prior_state} -> {event.state}")
            if action_history[-1].event_id not in event.parent_event_ids:
                raise ValueError("A state transition must cite the prior action event")
        elif event.state != "proposed":
            raise ValueError("An action lineage must begin as proposed")
        if event.physical_effect and event.state not in {"submitted", "verified", "commissioned", "maintained", "degraded", "failed", "lost"}:
            raise ValueError("Physical effects cannot occur before work is performed")
        event.event_hash = event.calculate_hash()
        self.events.append(event)
        self.by_id[event.event_id] = event
        return event

    def ancestors(self, event_id: str) -> List[CausalEvent]:
        if event_id not in self.by_id:
            raise KeyError(event_id)
        visited, ordered = set(), []
        def visit(current_id: str):
            for parent_id in self.by_id[current_id].parent_event_ids:
                if parent_id not in visited:
                    visit(parent_id)
                    visited.add(parent_id)
                    ordered.append(self.by_id[parent_id])
        visit(event_id)
        return ordered

    def verify(self) -> bool:
        previous_hash = "GENESIS"
        for sequence, event in enumerate(self.events, 1):
            if event.sequence != sequence or event.previous_hash != previous_hash or event.event_hash != event.calculate_hash():
                return False
            if any(parent not in self.by_id for parent in event.parent_event_ids):
                return False
            previous_hash = event.event_hash
        return True
