"""Central release gate for EoV's simulation-only economic scope."""

from __future__ import annotations

from dataclasses import dataclass


REAL_VALUE_PATH_PREFIXES = (
    "/api/payments", "/api/earnings", "/api/entity-earnings", "/api/ecosystem-support",
)


@dataclass(frozen=True)
class EconomyPolicy:
    mode: str = "simulation"

    def __post_init__(self) -> None:
        normalized = self.mode.strip().lower()
        if normalized not in {"simulation", "shadow"}:
            raise RuntimeError("Real-value economy modes are disabled; economy mode must be simulation or shadow")
        object.__setattr__(self, "mode", normalized)

    def blocks_path(self, path: str) -> bool:
        return path.startswith(REAL_VALUE_PATH_PREFIXES)

    def status(self, actor_id: str) -> dict:
        return {
            "mode": self.mode,
            "real_value_enabled": False,
            "spendable_cu": False,
            "provider_calls_enabled": False,
            "legacy_mutations": "quarantined",
            "actor_id": actor_id,
        }
