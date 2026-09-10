"""Evidence-bearing scientific and practical competency progression."""

from dataclasses import dataclass, field
from typing import Dict, List


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


@dataclass
class CompetencyProfile:
    entity_id: str
    competencies: Dict[str, Competency] = field(default_factory=dict)

    def get(self, domain: str) -> Competency:
        if domain not in DOMAINS:
            raise ValueError("Unknown competency domain")
        return self.competencies.setdefault(domain, Competency(domain))


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


def record_demonstrated_outcome(profile: CompetencyProfile, domain: str, evidence_id: str, quality: float) -> Competency:
    """Record reproducible task evidence across every component of competence.

    This is the only compatibility path for legacy "specialization" progress;
    labels and profession titles never call it without a completed outcome.
    """
    item = profile.get(domain)
    gain = clamp(quality) * 0.08
    item.theory = clamp(item.theory + gain * 0.6)
    item.observation = clamp(item.observation + gain)
    item.procedure = clamp(item.procedure + gain)
    item.embodied = clamp(item.embodied + gain)
    item.reproducibility = clamp(item.reproducibility + gain)
    item.evidence.append(f"demonstrated:{evidence_id}")
    return item


def record_practice_evidence(
    profile: CompetencyProfile,
    domain: str,
    action_id: str,
    evidence_ids: List[str],
    verified: bool,
    quality: float,
) -> Competency:
    """Record an embodied action without treating unverified claims as competence."""
    require_prerequisite_evidence(profile, domain)
    item = profile.get(domain)
    evidence = [str(evidence_id) for evidence_id in evidence_ids]
    item.evidence.extend(f"evidence:{evidence_id}" for evidence_id in evidence)
    if verified:
        item = record_demonstrated_outcome(profile, domain, action_id, quality)
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


def practice(profile: CompetencyProfile, domain: str, perspective: str, action_id: str, verified: bool) -> Competency:
    if perspective not in DIRECT_ACTION_PERSPECTIVES:
        raise ValueError("Direct practice requires an embodied or supervisory world view")
    require_prerequisite_evidence(profile, domain)
    profile.get(domain).evidence.append(f"practice-perspective:{perspective}")
    item = record_practice_evidence(profile, domain, action_id, [f"perspective:{perspective}"], verified, 1.0)
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
