"""Evidence-bearing scientific and practical competency progression."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


DOMAINS = {
    "measurement": {"kind": "foundation", "prerequisites": []},
    "mathematics": {"kind": "science", "prerequisites": ["measurement"]},
    "physics": {"kind": "science", "prerequisites": ["measurement", "mathematics"]},
    "chemistry": {"kind": "science", "prerequisites": ["measurement"]},
    "biology": {"kind": "science", "prerequisites": ["measurement"]},
    "materials_science": {"kind": "applied_science", "prerequisites": ["physics", "chemistry"]},
    "metallurgy": {"kind": "applied_science", "prerequisites": ["measurement"]},
    "mechanical_engineering": {"kind": "engineering", "prerequisites": ["physics", "materials_science"]},
    "mechanical_repair": {"kind": "craft", "prerequisites": ["measurement", "mechanical_engineering"]},
    "electrical_engineering": {"kind": "engineering", "prerequisites": ["physics", "mathematics"]},
    "civil_engineering": {"kind": "engineering", "prerequisites": ["physics", "materials_science"]},
    "agriculture": {"kind": "applied_science", "prerequisites": ["biology", "chemistry"]},
    "forestry": {"kind": "resource_practice", "prerequisites": ["biology", "measurement"]},
    "mining": {"kind": "resource_practice", "prerequisites": ["materials_science", "measurement"]},
    "harvesting": {"kind": "resource_practice", "prerequisites": ["agriculture", "measurement"]},
    "cooking": {"kind": "craft", "prerequisites": ["measurement"]},
    "food_safety": {"kind": "applied_science", "prerequisites": ["measurement", "biology", "chemistry"]},
    "smithing": {"kind": "craft", "prerequisites": ["measurement", "materials_science"]},
    "logistics": {"kind": "institutional", "prerequisites": ["measurement"]},
    "administration": {"kind": "institutional", "prerequisites": []},
}

DIRECT_ACTION_PERSPECTIVES = {"isometric", "first_person", "vr"}
TERMINAL_EVIDENCE_STATES = {"verified", "commissioned"}


def clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


@dataclass
class Competency:
    domain: str
    theory: float = 0.0
    observation: float = 0.0
    procedure: float = 0.0
    embodied: float = 0.0
    reproducibility: float = 0.0
    teaching: float = 0.0
    familiarity: float = 0.0
    evidence: List[str] = field(default_factory=list)

    @property
    def demonstrated(self) -> float:
        return min(self.theory, self.observation, self.procedure, max(self.embodied, self.reproducibility))


@dataclass(frozen=True)
class EvidenceRecord:
    action_id: str
    state: str
    identity: str


@dataclass
class CompetencyProfile:
    entity_id: str
    competencies: Dict[str, Competency] = field(default_factory=dict)
    evidence_records: Dict[str, EvidenceRecord] = field(default_factory=dict)

    def get(self, domain: str) -> Competency:
        if domain not in DOMAINS:
            raise ValueError("Unknown competency domain")
        return self.competencies.setdefault(domain, Competency(domain))


def register_evidence(profile: CompetencyProfile, evidence_id: str, action_id: str, state: str, identity: str) -> EvidenceRecord:
    """Register a causal evidence record for later verified-practice resolution."""
    record = EvidenceRecord(action_id=action_id, state=state, identity=identity)
    profile.evidence_records[evidence_id] = record
    return record


def missing_prerequisite_evidence(profile: CompetencyProfile, domain: str) -> List[str]:
    """Return direct prerequisites that lack demonstrated, traceable evidence."""
    if domain not in DOMAINS:
        raise ValueError("Unknown competency domain")
    return [
        name for name in DOMAINS[domain]["prerequisites"]
        if profile.get(name).demonstrated < 0.1 or not profile.get(name).evidence
    ]


def require_prerequisite_evidence(profile: CompetencyProfile, domain: str) -> None:
    missing = missing_prerequisite_evidence(profile, domain)
    if missing:
        raise ValueError(f"missing prerequisite evidence: {', '.join(missing)}")


def _record_verified_outcome(profile: CompetencyProfile, domain: str, action_id: str, quality: float) -> Competency:
    """Apply demonstrated competency after a caller has verified action evidence."""
    item = profile.get(domain)
    gain = clamp(quality) * 0.08
    item.theory = clamp(item.theory + gain * 0.6)
    item.observation = clamp(item.observation + gain)
    item.procedure = clamp(item.procedure + gain)
    item.embodied = clamp(item.embodied + gain)
    item.reproducibility = clamp(item.reproducibility + gain)
    item.evidence.append(f"demonstrated:{action_id}")
    return item


def record_demonstrated_outcome(profile: CompetencyProfile, domain: str, evidence_id: str, quality: float) -> Competency:
    """Compatibility adapter; it resolves registered action evidence before recording."""
    parts = evidence_id.split(":")
    if len(parts) != 4 or parts[0] != "verified-action" or parts[2] != "evidence":
        raise ValueError("record_demonstrated_outcome requires verified action evidence")
    _require_verified_evidence(profile, parts[1], [parts[3]])
    return _record_verified_outcome(profile, domain, parts[1], quality)


def _require_verified_evidence(profile: CompetencyProfile, action_id: str, evidence_ids: List[str]) -> None:
    if not evidence_ids:
        raise ValueError("verified practice requires at least one resolved evidence record")
    for evidence_id in evidence_ids:
        record = profile.evidence_records.get(evidence_id)
        if record is None:
            raise ValueError(f"evidence {evidence_id} does not resolve")
        if record.action_id != action_id:
            raise ValueError(f"evidence {evidence_id} does not match action {action_id}")
        if record.state not in TERMINAL_EVIDENCE_STATES:
            raise ValueError("evidence must be verified or commissioned")
        if not record.identity:
            raise ValueError("evidence identity is required")


def record_practice_evidence(
    profile: CompetencyProfile,
    domain: str,
    action_id: str,
    evidence_ids: List[str],
    verified: bool,
    quality: float,
) -> Competency:
    """Record an embodied action without treating unverified claims as competence."""
    evidence = [str(evidence_id) for evidence_id in evidence_ids]
    require_prerequisite_evidence(profile, domain)
    if verified:
        _require_verified_evidence(profile, action_id, evidence)
    item = profile.get(domain)
    item.evidence.extend(f"evidence:{evidence_id}" for evidence_id in evidence)
    if verified:
        item = _record_verified_outcome(profile, domain, action_id, quality)
        item.evidence.append(f"practice:{action_id}:verified")
        return item
    item.familiarity = clamp(item.familiarity + clamp(quality) * 0.1)
    item.evidence.append(f"practice:{action_id}:unverified")
    return item


def study(profile: CompetencyProfile, domain: str, source_id: str, source_quality: float) -> Competency:
    """Text and testimony can build theory, never embodied execution."""
    item = profile.get(domain)
    item.theory = clamp(item.theory + clamp(source_quality) * 0.1)
    item.evidence.append(f"studied:{source_id}")
    return item


def observe(profile: CompetencyProfile, domain: str, perspective: str, evidence_id: str, quality: float) -> Competency:
    if perspective == "story":
        raise ValueError("Story perspective receives reports, not direct physical observation")
    if perspective not in DIRECT_ACTION_PERSPECTIVES:
        raise ValueError("Unsupported perspective")
    item = profile.get(domain)
    perspective_factor = {"isometric": 0.65, "first_person": 1.0, "vr": 1.0}[perspective]
    item.observation = clamp(item.observation + clamp(quality) * 0.1 * perspective_factor)
    item.evidence.append(f"observed:{perspective}:{evidence_id}")
    return item


def practice(
    profile: CompetencyProfile,
    domain: str,
    perspective: str,
    action_id: str,
    verified: bool,
    evidence_ids: Optional[List[str]] = None,
) -> Competency:
    if perspective not in DIRECT_ACTION_PERSPECTIVES:
        raise ValueError("Direct practice requires an embodied or supervisory world view")
    item = record_practice_evidence(profile, domain, action_id, list(evidence_ids or []), verified, 1.0)
    if verified:
        item.embodied = clamp(item.embodied + 0.04 * {"isometric": 0.55, "first_person": 1.0, "vr": 1.0}[perspective])
    return item


def reproduce_experiment(profile: CompetencyProfile, domain: str, experiment_id: str, matched_result: bool) -> Competency:
    item = profile.get(domain)
    item.reproducibility = clamp(item.reproducibility + (0.12 if matched_result else 0.035))
    item.observation = clamp(item.observation + 0.05)
    item.evidence.append(f"experiment:{experiment_id}:{'matched' if matched_result else 'diverged'}")
    return item


def teach(teacher: CompetencyProfile, learner: CompetencyProfile, domain: str, lesson_id: str) -> Competency:
    source = teacher.get(domain)
    if source.demonstrated < 0.15:
        raise ValueError("Teacher has not demonstrated sufficient competence")
    target = learner.get(domain)
    transferable = min(source.theory, source.procedure, source.reproducibility)
    target.familiarity = min(source.demonstrated, clamp(target.familiarity + transferable * 0.12))
    target.evidence.append(f"lesson:{lesson_id}:teacher:{teacher.entity_id}:unverified")
    source.teaching = clamp(source.teaching + 0.025)
    return target


def can_attempt(profile: CompetencyProfile, domain: str, perspective: str) -> Dict[str, object]:
    if domain not in DOMAINS:
        raise ValueError("Unknown competency domain")
    missing = missing_prerequisite_evidence(profile, domain)
    return {
        "allowed": perspective in DIRECT_ACTION_PERSPECTIVES and not missing,
        "missing_prerequisites": missing,
        "indirect_only": perspective == "story",
    }
