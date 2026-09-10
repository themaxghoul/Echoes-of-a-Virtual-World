"""The setting-specific definitions for the Living Workshop water repair."""

from __future__ import annotations

from dataclasses import asdict, dataclass
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
            # Mechanical repair is the scenario capability; it is evidenced by
            # the existing mechanical-engineering competency record.
            competence_domain="mechanical_engineering",
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
    )
