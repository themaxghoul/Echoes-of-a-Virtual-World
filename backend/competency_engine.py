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
    item = profile.get(domain)
    gain = 0.1 if verified else 0.025
    item.procedure = clamp(item.procedure + gain)
    item.embodied = clamp(item.embodied + gain * ({"isometric": 0.55, "first_person": 1.0, "vr": 1.0}[perspective]))
    # Performing a task exposes observable consequences and, when verified,
    # connects procedure back to a bounded explanation. It cannot substitute
    # for study, but it must allow demonstrated ability to grow from evidence.
    item.observation = clamp(item.observation + gain * (0.4 if verified else 0.15))
    item.theory = clamp(item.theory + gain * (0.2 if verified else 0.05))
    if verified:
        item.reproducibility = clamp(item.reproducibility + 0.08)
    item.evidence.append(f"practice:{perspective}:{action_id}:{'verified' if verified else 'unverified'}")
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
    target.theory = min(source.theory, clamp(target.theory + transferable * 0.08))
    target.procedure = min(source.procedure, clamp(target.procedure + transferable * 0.04))
    target.evidence.append(f"lesson:{lesson_id}:teacher:{teacher.entity_id}")
    source.teaching = clamp(source.teaching + 0.025)
    return target


def can_attempt(profile: CompetencyProfile, domain: str, perspective: str) -> Dict[str, object]:
    if domain not in DOMAINS:
        raise ValueError("Unknown competency domain")
    missing = [name for name in DOMAINS[domain]["prerequisites"] if profile.get(name).demonstrated < 0.1]
    return {
        "allowed": perspective in DIRECT_ACTION_PERSPECTIVES and not missing,
        "missing_prerequisites": missing,
        "indirect_only": perspective == "story",
    }
