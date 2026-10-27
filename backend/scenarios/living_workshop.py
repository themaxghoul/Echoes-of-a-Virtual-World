"""The setting-specific definitions for the Living Workshop water repair."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Any

from action_engine import ActionDefinition, ActionRequirements


@dataclass(frozen=True)
class WaterInstallationSpec:
    """Inspectable recipe and acceptance tolerances for one water installation."""

    installation_site: str = "settlement-water-installation"
    seal_material: str = "seal_material"
    seal_material_amount: int = 2
    fastener_material: str = "fasteners"
    fastener_amount: int = 4
    wrench_tool: str = "maintenance_wrench"
    calibrated_measure_tool: str = "calibrated_measure"
    energy: int = 5
    duration_ticks: int = 6
    minimum_competence: float = 0.1
    minimum_flow_lpm: float = 12.0
    maximum_leak_rate_ml_min: float = 20.0
    maximum_contamination_index: float = 0.1
    minimum_pressure_kpa: float = 160.0
    maximum_seal_alignment_mm: float = 0.5
    deterministic_seed: str = "living-workshop-water-repair-v1"


WATER_MEASUREMENT_FIELDS = (
    "flow_lpm", "leak_rate_ml_min", "contamination_index", "pressure_kpa", "seal_alignment_mm",
)


def _water_measurements(samples: list[dict[str, Any]]) -> list[dict[str, float]]:
    return [
        {name: float(sample[name]) for name in WATER_MEASUREMENT_FIELDS}
        for sample in samples
        if isinstance(sample, dict)
        and all(isinstance(sample.get(name), (int, float)) for name in WATER_MEASUREMENT_FIELDS)
    ]


def evaluate_water_installation_repair(context: dict[str, Any]) -> dict[str, Any]:
    """Evaluate water-repair evidence; the engine only owns lifecycle and custody."""
    observations = _water_measurements(context["samples"])
    materials = context["materials"]
    if not observations:
        return {
            "succeeded": False,
            "failure_reason": "no complete pre-repair measurements",
            "output": {},
            "evidence": [{"kind": "incomplete_water_repair_measurements"}],
            "material_disposition": {},
        }
    parameters = context["specification"]
    seed_digest = sha256(f"{context['action_id']}{parameters['deterministic_seed']}".encode()).hexdigest()
    deterministic_fraction = int(seed_digest[:16], 16) / float(0xFFFFFFFFFFFFFFFF)
    tool_condition = min(context["tool_conditions"].values()) if context["tool_conditions"] else 1.0
    pre_measurement = observations[0]
    diagnosis_signal = sum((
        min(1.0, pre_measurement["flow_lpm"] / parameters["minimum_flow_lpm"]),
        min(1.0, parameters["maximum_leak_rate_ml_min"] / max(1.0, pre_measurement["leak_rate_ml_min"])),
        min(1.0, parameters["maximum_contamination_index"] / max(0.0001, pre_measurement["contamination_index"])),
        min(1.0, pre_measurement["pressure_kpa"] / parameters["minimum_pressure_kpa"]),
        min(1.0, parameters["maximum_seal_alignment_mm"] / max(0.0001, pre_measurement["seal_alignment_mm"])),
    )) / len(WATER_MEASUREMENT_FIELDS)
    repair_quality = round(min(1.0, 0.2 + context["demonstrated_competence"] * 0.4 + tool_condition * 0.25 + deterministic_fraction * 0.1 + (1.0 - diagnosis_signal) * 0.05), 6)
    disposition = {
        name: {"installed": amount, "recovered": 0, "damaged": 0, "waste": 0}
        for name, amount in materials.items()
    }
    return {
        "succeeded": True,
        "output": {"pre_repair_measurements": observations, "repair_quality": repair_quality},
        "evidence": [{
            "kind": "water_installation_repair_execution",
            "pre_repair_measurements": observations,
            "deterministic_inputs": {
                "competence": round(context["demonstrated_competence"], 6),
                "tool_condition": round(tool_condition, 6),
                "tolerances": parameters,
                "action_seed_hash": seed_digest,
            },
        }],
        "material_disposition": disposition,
    }


def verify_water_installation_repair(context: dict[str, Any]) -> dict[str, Any]:
    """Independently compare post-repair water samples to scenario tolerances."""
    post_repair_samples = _water_measurements(context["samples"])
    if not post_repair_samples:
        raise ValueError("complete independent post-repair measurements required")
    observed = post_repair_samples[0]
    parameters = context["specification"]
    tolerance_comparison = {
        "flow_lpm": {"observed": observed["flow_lpm"], "minimum": parameters["minimum_flow_lpm"], "passed": observed["flow_lpm"] >= parameters["minimum_flow_lpm"]},
        "leak_rate_ml_min": {"observed": observed["leak_rate_ml_min"], "maximum": parameters["maximum_leak_rate_ml_min"], "passed": observed["leak_rate_ml_min"] <= parameters["maximum_leak_rate_ml_min"]},
        "contamination_index": {"observed": observed["contamination_index"], "maximum": parameters["maximum_contamination_index"], "passed": observed["contamination_index"] <= parameters["maximum_contamination_index"]},
        "pressure_kpa": {"observed": observed["pressure_kpa"], "minimum": parameters["minimum_pressure_kpa"], "passed": observed["pressure_kpa"] >= parameters["minimum_pressure_kpa"]},
        "seal_alignment_mm": {"observed": observed["seal_alignment_mm"], "maximum": parameters["maximum_seal_alignment_mm"], "passed": observed["seal_alignment_mm"] <= parameters["maximum_seal_alignment_mm"]},
    }
    passed = all(item["passed"] for item in tolerance_comparison.values())
    verification = {
        "post_repair_samples": post_repair_samples,
        "tolerance_comparison": tolerance_comparison,
    }
    return {
        "passed": passed,
        "verification": verification,
        "evidence": [{
            "kind": "independent_water_repair_check",
            "verification": verification,
            "material_reconciliation": context["material_reconciliation"],
        }],
    }


def living_workshop_seed() -> dict[str, object]:
    """Return scenario data, not mutable world state or a parallel simulation model."""
    spec = WaterInstallationSpec()
    return {
        "installations": {
            "water": {
                "id": spec.installation_site,
                "location": spec.installation_site,
                "measurement_tolerances": {
                    "minimum_flow_lpm": spec.minimum_flow_lpm,
                    "maximum_leak_rate_ml_min": spec.maximum_leak_rate_ml_min,
                    "maximum_contamination_index": spec.maximum_contamination_index,
                    "minimum_pressure_kpa": spec.minimum_pressure_kpa,
                    "maximum_seal_alignment_mm": spec.maximum_seal_alignment_mm,
                },
            }
        },
        "water_repair_spec": asdict(spec),
    }


def water_installation_repair(spec: WaterInstallationSpec) -> ActionDefinition:
    """Build the canonical repair action; the shared kernel owns its lifecycle."""
    return ActionDefinition(
        action_type="repair_water_installation",
        requirements=ActionRequirements(
            materials={
                spec.seal_material: spec.seal_material_amount,
                spec.fastener_material: spec.fastener_amount,
            },
            tools={spec.wrench_tool: 0.4, spec.calibrated_measure_tool: 0.7},
            station=spec.installation_site,
            energy=spec.energy,
            competence_domain="mechanical_repair",
            minimum_competence=spec.minimum_competence,
            perception_channels={"spatial_layout", "instrumentation"},
            duration_ticks=spec.duration_ticks,
        ),
        output_item="repaired_water_installation",
        output_amount=1,
        provisional_cu_milli=7000,
        execution_model="water_installation_repair",
        verifier_competence_domain="measurement",
        minimum_verifier_competence=0.1,
        input_custody="communal_store",
        execution_parameters={
            "minimum_flow_lpm": spec.minimum_flow_lpm,
            "maximum_leak_rate_ml_min": spec.maximum_leak_rate_ml_min,
            "maximum_contamination_index": spec.maximum_contamination_index,
            "minimum_pressure_kpa": spec.minimum_pressure_kpa,
            "maximum_seal_alignment_mm": spec.maximum_seal_alignment_mm,
            "deterministic_seed": spec.deterministic_seed,
        },
        execution_evaluator=evaluate_water_installation_repair,
        verification_evaluator=verify_water_installation_repair,
    )
