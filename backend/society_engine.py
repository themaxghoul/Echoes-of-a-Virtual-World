"""Deterministic foundations for bounded-knowledge autonomous societies."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from competency_engine import CompetencyProfile


PERSPECTIVES = {
    "story": {"channels": {"testimony", "records", "language"}, "range": "reported", "embodiment": 0.1},
    "isometric": {"channels": {"spatial_layout", "construction", "traffic", "resource_flow"}, "range": "local_overview", "embodiment": 0.4},
    "first_person": {"channels": {"surface_detail", "sound", "tool_use", "line_of_sight"}, "range": "embodied_local", "embodiment": 0.8},
    "vr": {"channels": {"stereo_depth", "gesture", "dexterity", "body_position"}, "range": "embodied_local", "embodiment": 1.0, "status": "backlog"},
}

NEED_DECAY = {"nutrition": 0.025, "rest": 0.018, "shelter": 0.006, "safety": 0.009, "belonging": 0.007, "purpose": 0.005}


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
    competency_profile: CompetencyProfile = field(init=False)
    relationships: Dict[str, float] = field(default_factory=dict)
    inventory: Dict[str, float] = field(default_factory=dict)
    personality: Dict[str, float] = field(default_factory=dict)
    goals: List[str] = field(default_factory=list)
    perceptions: Set[str] = field(default_factory=set)
    memories: List[Dict[str, Any]] = field(default_factory=list)
    alive: bool = True
    age_ticks: int = 0

    def __post_init__(self):
        self.competency_profile = CompetencyProfile(self.agent_id)

    @property
    def specialties(self) -> Dict[str, float]:
        """Compatibility projection; demonstrated competency is authoritative."""
        return {name: item.demonstrated for name, item in self.competency_profile.competencies.items() if item.demonstrated > 0}

    def specialty_load(self) -> float:
        return sum(level ** 1.5 for level in self.specialties.values())


@dataclass
class Observation:
    topic: str
    channel: str
    perspective: str
    evidence_strength: float
    source_id: str


@dataclass(frozen=True)
class DecisionOption:
    action_id: str
    category: str
    addressed_needs: Dict[str, float] = field(default_factory=dict)
    goal_tags: Set[str] = field(default_factory=set)
    required_competence: Dict[str, float] = field(default_factory=dict)
    required_resources: Dict[str, float] = field(default_factory=dict)
    risk: float = 0.0
    expected_utility: float = 0.0
    required_perceptions: Set[str] = field(default_factory=set)
    relationship_target: Optional[str] = None


PERSONALITY_TRAITS = ("diligence", "sociability", "caution", "curiosity", "cooperation")
LEGACY_PERSONALITY_TRAITS = {
    "cooperative": "cooperation",
    "aggressive": "caution",
    "curious": "curiosity",
    "creative": "curiosity",
    "social": "sociability",
    "territorial": "caution",
    "mercantile": "diligence",
    "spiritual": "cooperation",
}
PERSONALITY_CATEGORY_WEIGHTS = {
    "diligence": {"construction": 0.35, "craft": 0.4, "design": 0.4, "logistics": 0.3, "trade": 0.2},
    "sociability": {"social": 0.45, "coordination": 0.35, "trade": 0.2},
    "caution": {"conflict": 0.2, "defense": 0.4, "stewardship": 0.25, "care": 0.1},
    "curiosity": {"exploration": 0.4, "knowledge": 0.4, "measurement": 0.35},
    "cooperation": {"social": 0.35, "care": 0.4, "public_work": 0.3, "coordination": 0.2, "ritual": 0.35},
}
KNOWN_ACTION_CATEGORIES = frozenset(category for weights in PERSONALITY_CATEGORY_WEIGHTS.values() for category in weights)


def normalize_personality(personality: Dict[str, float]) -> Dict[str, float]:
    """Project legacy labels into the only five personality decision factors."""
    normalized = {trait: 0.0 for trait in PERSONALITY_TRAITS}
    for trait, value in personality.items():
        target = LEGACY_PERSONALITY_TRAITS.get(trait, trait)
        if target not in normalized:
            raise ValueError(f"Unknown personality trait: {trait}")
        normalized[target] = clamp(normalized[target] + value)
    return normalized


@dataclass(frozen=True)
class DecisionContext:
    perceived_needs: Dict[str, float] = field(default_factory=dict)
    goals: Set[str] = field(default_factory=set)
    relationships: Dict[str, float] = field(default_factory=dict)
    resources: Dict[str, float] = field(default_factory=dict)
    risks: Dict[str, float] = field(default_factory=dict)
    obligations: Dict[str, float] = field(default_factory=dict)
    personality: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        object.__setattr__(self, "personality", normalize_personality(self.personality))


def decision_context(*, authoritative_only: Optional[Dict[str, float]] = None, **kwargs: Any) -> DecisionContext:
    """Build subjective decision inputs; authoritative-only facts are intentionally discarded."""
    del authoritative_only
    return DecisionContext(**kwargs)


@dataclass(frozen=True)
class DecisionScore:
    need: float
    goal: float
    competence: float
    relationship: float
    resource: float
    risk: float
    utility: float
    obligation: float
    personality: Dict[str, float]

    @property
    def components(self) -> Dict[str, float]:
        return {
            "need": self.need,
            "goal": self.goal,
            "competence": self.competence,
            "relationship": self.relationship,
            "resource": self.resource,
            "risk": self.risk,
            "utility": self.utility,
            "obligation": self.obligation,
            "personality": sum(self.personality.values()),
        }

    @property
    def total(self) -> float:
        return sum(self.components.values())


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
    """Legacy read-only adapter; specialization projects demonstrated evidence."""
    del effort
    return agent.competency_profile.get(specialty).demonstrated


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


def score_option(agent: Agent, option: DecisionOption, context: DecisionContext) -> DecisionScore:
    """Score a proposal from explicit, perceived inputs with an inspectable breakdown."""
    if option.category not in KNOWN_ACTION_CATEGORIES:
        raise ValueError(f"Unknown action category: {option.category}")
    need = sum((1.0 - context.perceived_needs.get(name, 1.0)) * weight for name, weight in option.addressed_needs.items())
    goal = 0.25 * len(context.goals.intersection(option.goal_tags))
    competence = sum(
        max(0.0, agent.competency_profile.get(domain).demonstrated - minimum)
        for domain, minimum in option.required_competence.items()
    )
    relationship = context.relationships.get(option.relationship_target, 0.0) * 0.15 if option.relationship_target else 0.0
    resource = -sum(max(0.0, amount - context.resources.get(item, 0.0)) for item, amount in option.required_resources.items())
    risk = -clamp(context.risks.get(option.action_id, context.risks.get(option.category, option.risk)))
    obligation = context.obligations.get(option.action_id, context.obligations.get(option.category, 0.0))
    personality = {
        trait: context.personality[trait] * PERSONALITY_CATEGORY_WEIGHTS[trait].get(option.category, 0.0)
        for trait in PERSONALITY_TRAITS
    }
    return DecisionScore(
        need=need,
        goal=goal,
        competence=competence,
        relationship=relationship,
        resource=resource,
        risk=risk,
        utility=option.expected_utility,
        obligation=obligation,
        personality=personality,
    )


def decide_initiative(agent: Agent, options: List[DecisionOption]) -> Optional[str]:
    """Select the highest-scoring feasible proposal using the explicit decision scorer."""
    context = DecisionContext(
        perceived_needs=dict(agent.needs),
        goals=set(agent.goals),
        relationships=dict(agent.relationships),
        resources=dict(agent.inventory),
        personality=dict(agent.personality),
    )
    scored = []
    for option in options:
        if not option.required_perceptions.issubset(agent.perceptions):
            continue
        if any(context.resources.get(item, 0) < amount for item, amount in option.required_resources.items()):
            continue
        if any(agent.competency_profile.get(domain).demonstrated < level for domain, level in option.required_competence.items()):
            continue
        scored.append((round(score_option(agent, option, context).total, 8), option.action_id))
    return max(scored, key=lambda item: (item[0], item[1]))[1] if scored else None


def remember_perceived_event(agent: Agent, event: Dict[str, Any], perceived_channels: Set[str]) -> Dict[str, Any]:
    """Create subjective belief from a causal event without mutating truth."""
    if not perceived_channels.intersection(agent.perceptions):
        raise ValueError("Agent did not perceive this event")
    evidence = event.get("evidence", [])
    confidence = min(0.95, 0.45 + 0.1 * len(evidence) + (0.2 if event.get("state") == "verified" else 0.0))
    memory = {
        "event_id": event["event_id"],
        "belief": f"{event.get('actor_id', 'someone')} {event.get('state', 'acted')}: {event.get('intent', '')}",
        "confidence": confidence,
        "perceived_channels": sorted(perceived_channels.intersection(agent.perceptions)),
        "objective_hash": event.get("event_hash"),
    }
    agent.memories.append(memory)
    return memory
