"""Deterministic foundations for bounded-knowledge autonomous societies."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import math


PERSPECTIVES = {
    "story": {"channels": {"testimony", "records", "language"}, "range": "reported", "embodiment": 0.1},
    "isometric": {"channels": {"spatial_layout", "construction", "traffic", "resource_flow"}, "range": "local_overview", "embodiment": 0.4},
    "first_person": {"channels": {"surface_detail", "sound", "tool_use", "line_of_sight"}, "range": "embodied_local", "embodiment": 0.8},
    "vr": {"channels": {"stereo_depth", "gesture", "dexterity", "body_position"}, "range": "embodied_local", "embodiment": 1.0, "status": "backlog"},
}

NEED_DECAY = {"nutrition": 0.025, "rest": 0.018, "shelter": 0.006, "safety": 0.009, "belonging": 0.007, "purpose": 0.005}
SPECIALTY_CAPACITY = 3.0


@dataclass
class Knowledge:
    topic: str
    competence: float = 0.0
    confidence: float = 0.0
    provenance: List[str] = field(default_factory=list)
    independently_reproduced: bool = False


@dataclass
class Agent:
    agent_id: str
    needs: Dict[str, float] = field(default_factory=lambda: {name: 0.7 for name in NEED_DECAY})
    knowledge: Dict[str, Knowledge] = field(default_factory=dict)
    specialties: Dict[str, float] = field(default_factory=dict)
    relationships: Dict[str, float] = field(default_factory=dict)
    inventory: Dict[str, float] = field(default_factory=dict)
    alive: bool = True
    age_ticks: int = 0

    def specialty_load(self) -> float:
        return sum(level ** 1.5 for level in self.specialties.values())


@dataclass
class Observation:
    topic: str
    channel: str
    perspective: str
    evidence_strength: float
    source_id: str


def clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def tick_survival(agent: Agent, event: Optional[Dict[str, float]] = None) -> Agent:
    """Advance needs. Events alter pressures but do not inject knowledge."""
    if not agent.alive:
        return agent
    event = event or {}
    for need, decay in NEED_DECAY.items():
        pressure = max(0.0, event.get(need, 1.0))
        agent.needs[need] = clamp(agent.needs.get(need, 0.5) - decay * pressure)
    agent.age_ticks += 1
    if agent.needs["nutrition"] <= 0 or agent.needs["safety"] <= 0:
        agent.alive = False
    return agent


def satisfy_need(agent: Agent, need: str, amount: float, resource: Optional[str] = None, cost: float = 0) -> bool:
    if not agent.alive or need not in agent.needs:
        return False
    if resource and agent.inventory.get(resource, 0) < cost:
        return False
    if resource:
        agent.inventory[resource] -= cost
    agent.needs[need] = clamp(agent.needs[need] + max(0.0, amount))
    return True


def perceive(agent: Agent, observation: Observation) -> Knowledge:
    rules = PERSPECTIVES.get(observation.perspective)
    if not rules or observation.channel not in rules["channels"]:
        raise ValueError("The selected perspective cannot directly perceive that channel")
    record = agent.knowledge.setdefault(observation.topic, Knowledge(topic=observation.topic))
    gain = clamp(observation.evidence_strength) * (0.08 + rules["embodiment"] * 0.12)
    record.competence = clamp(record.competence + gain)
    record.confidence = clamp(record.confidence + gain * 0.8)
    record.provenance.append(f"observed:{observation.perspective}:{observation.source_id}")
    return record


def teach(teacher: Agent, learner: Agent, topic: str, teaching_quality: float = 0.5) -> Knowledge:
    if not teacher.alive or not learner.alive:
        raise ValueError("Only living agents can participate in teaching")
    source = teacher.knowledge.get(topic)
    if not source or source.competence < 0.2:
        raise ValueError("Teacher lacks sufficient acquired competence")
    target = learner.knowledge.setdefault(topic, Knowledge(topic=topic))
    fidelity = clamp(teaching_quality) * source.competence * source.confidence
    target.competence = min(source.competence, clamp(target.competence + fidelity * 0.18))
    target.confidence = clamp(target.confidence + fidelity * 0.12)
    target.provenance.append(f"taught_by:{teacher.agent_id}")
    return target


def practice(agent: Agent, topic: str, verified_outcome: bool) -> Knowledge:
    if not agent.alive:
        raise ValueError("Dead agents cannot practice")
    record = agent.knowledge.setdefault(topic, Knowledge(topic=topic))
    gain = 0.12 if verified_outcome else 0.025
    record.competence = clamp(record.competence + gain)
    record.confidence = clamp(record.confidence + (0.1 if verified_outcome else 0.01))
    record.provenance.append("practice:verified" if verified_outcome else "practice:unverified")
    if verified_outcome:
        record.independently_reproduced = True
    return record


def specialize(agent: Agent, specialty: str, effort: float) -> float:
    """Specialization has a nonlinear cognitive budget to preserve economic diversity."""
    current = agent.specialties.get(specialty, 0.0)
    available = max(0.0, SPECIALTY_CAPACITY - agent.specialty_load())
    gain = min(max(0.0, effort) * 0.08, available / max(1.0, math.sqrt(current + 0.1)))
    agent.specialties[specialty] = clamp(current + gain)
    return agent.specialties[specialty]


def priority(agent: Agent) -> str:
    if not agent.alive:
        return "archived"
    need, value = min(agent.needs.items(), key=lambda item: item[1])
    if value < 0.35:
        return f"secure:{need}"
    if agent.specialties:
        return f"practice:{max(agent.specialties, key=agent.specialties.get)}"
    return "observe_and_learn"


def dependency_market(agents: List[Agent]) -> Dict[str, List[str]]:
    """Expose unmet needs and scarce specialties without minting value from speech."""
    needs = sorted({need for agent in agents if agent.alive for need, level in agent.needs.items() if level < 0.45})
    supply: Dict[str, int] = {}
    for agent in agents:
        if agent.alive:
            for specialty, level in agent.specialties.items():
                if level >= 0.35:
                    supply[specialty] = supply.get(specialty, 0) + 1
    scarce = sorted(name for name, count in supply.items() if count <= 1)
    return {"unmet_needs": needs, "scarce_specialties": scarce}
