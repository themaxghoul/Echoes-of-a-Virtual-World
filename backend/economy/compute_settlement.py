"""Hard gate between provisional CU evidence and externally funded compute."""

from __future__ import annotations

from typing import Any, Dict


class SettlementUnavailable(RuntimeError):
    """Raised when a caller attempts external settlement before every gate passes."""


REQUIRED_EVIDENCE = (
    "provider_purchase_capability",
    "federal_legal_review",
    "state_legal_reviews",
    "tax_review",
    "labor_review",
    "privacy_review",
    "money_transmission_review",
    "external_funding_receipt",
    "human_spend_approval",
)


def _present(manifest: Dict[str, Any], field: str) -> bool:
    value = manifest.get(field)
    if field == "provider_purchase_capability":
        return value is True
    if field == "state_legal_reviews":
        return isinstance(value, dict) and bool(value) and all(value.values())
    return isinstance(value, str) and bool(value.strip())


def evaluate_compute_settlement(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate evidence; never infer funding from CU or an environment flag."""
    blockers = [field for field in REQUIRED_EVIDENCE if not _present(manifest, field)]
    return {
        "schema": "eov-compute-settlement-readiness/v1",
        "provider": str(manifest.get("provider", "unselected")),
        "status": "ready_for_human_execution" if not blockers else "blocked",
        "blockers": blockers,
        "cu_spendable": False,
        "automatic_execution": False,
        "funding_basis": "external_receipted_funds_only",
        "note": "Verified CU may support allocation decisions but is not money, provider credit, or proof of funds.",
    }


def require_compute_settlement(manifest: Dict[str, Any]) -> Dict[str, Any]:
    status = evaluate_compute_settlement(manifest)
    if status["blockers"]:
        raise SettlementUnavailable(f"compute settlement blocked by: {', '.join(status['blockers'])}")
    return status
