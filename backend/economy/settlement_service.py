"""Authoritative bridge from public CU claims to private owner-compute quotes."""

from __future__ import annotations

from typing import Any

from .compute_sponsorship import ComputeSponsorshipStore, SettlementError
from .provider_adapters import (
    OpenAICostsNormalizer,
    ProviderCapabilityError,
    RecordedOfficialBillingAdapter,
)
from .public_ledger import project_public_cu_ledger, verify_public_chain


class SettlementService:
    """Resolve claims from the persistent world; never trust client-supplied value."""

    def __init__(
        self,
        store: ComputeSponsorshipStore,
        world_store: Any,
        provider_registry: Any,
        owner_subject: str,
    ):
        if not isinstance(owner_subject, str) or not owner_subject.strip():
            raise ValueError("owner_subject is required")
        self.store = store
        self.world_store = world_store
        self.provider_registry = provider_registry
        self.owner_subject = owner_subject.strip()

    def propose_allocation(
        self,
        operation_id: str,
        world_id: str,
        policy_id: str,
        public_claim_ids: list[str],
        now_ms: int,
    ) -> dict:
        """Quote only claim IDs that the server can resolve in a valid public chain."""
        if not isinstance(public_claim_ids, list) or not public_claim_ids:
            raise SettlementError("at least one public claim is required")
        if any(not isinstance(claim_id, str) or not claim_id.strip() for claim_id in public_claim_ids):
            raise SettlementError("public claim id is required")
        if len(set(public_claim_ids)) != len(public_claim_ids):
            raise SettlementError("public claim is duplicated")
        snapshot = self.world_store.snapshot(world_id)
        public_ledger = project_public_cu_ledger(snapshot)
        if not verify_public_chain(public_ledger):
            raise SettlementError("public CU ledger integrity is invalid")
        entries_by_id = {entry.get("entry_id"): entry for entry in public_ledger.get("entries", [])}
        claims = []
        for claim_id in public_claim_ids:
            entry = entries_by_id.get(claim_id)
            if entry is None:
                raise SettlementError("public claim is not eligible")
            if (
                entry.get("status") != "verified_provisional"
                or entry.get("spendable") is not False
                or entry.get("unit") != "CU-placeholder"
                or not entry.get("evidence_hash")
                or not entry.get("commission_hash")
            ):
                raise SettlementError("public claim is not eligible")
            claims.append(entry)
        return self.store.create_allocation(
            operation_id=operation_id,
            owner_subject=self.owner_subject,
            world_id=world_id,
            policy_id=policy_id,
            public_claims=claims,
            now_ms=now_ms,
        )

    def hold_allocation(self, operation_id: str, allocation_id: str, now_ms: int) -> dict:
        """Hold a server-resolved quote using the service-configured owner identity."""
        return self.store.hold_allocation(operation_id, allocation_id, self.owner_subject, now_ms)

    def approve_allocation(
        self,
        operation_id: str,
        allocation_id: str,
        approval_hash: str,
        expires_at_ms: int,
        now_ms: int,
    ) -> dict:
        """Record an explicit owner approval without accepting a caller-supplied subject."""
        return self.store.approve_allocation(
            operation_id, allocation_id, self.owner_subject, approval_hash, expires_at_ms, now_ms,
        )

    def cancel_allocation(self, operation_id: str, allocation_id: str, reason: str, now_ms: int) -> dict:
        """Cancel a pre-provider allocation as the configured owner."""
        return self.store.cancel_allocation(operation_id, allocation_id, self.owner_subject, reason, now_ms)

    def expire_due(self, operation_id: str, now_ms: int) -> list[dict]:
        """Expire due approvals; this has no caller-controlled identity."""
        return self.store.expire_due(operation_id, now_ms)

    def _provider(self, provider: str):
        if not isinstance(provider, str) or not provider.strip():
            raise ProviderCapabilityError("provider is required")
        if not isinstance(self.provider_registry, dict):
            raise ProviderCapabilityError("trusted provider registry is unavailable")
        adapter = self.provider_registry.get(provider.strip())
        if adapter is None or not callable(getattr(adapter, "capabilities", None)):
            raise ProviderCapabilityError("provider is not available from the trusted registry")
        capabilities = adapter.capabilities()
        if capabilities.provider != provider.strip():
            raise ProviderCapabilityError("provider registry capability identity is invalid")
        return adapter, capabilities

    def submit_allocation(self, operation_id: str, allocation_id: str, provider: str, now_ms: int) -> dict:
        """Persist one idempotent provider submission, then delegate without retry fan-out."""
        adapter, capabilities = self._provider(provider)
        if not capabilities.purchase:
            raise ProviderCapabilityError("provider does not support approved purchase submission")
        pending = self.store.begin_provider_submission(
            operation_id, allocation_id, self.owner_subject, capabilities.provider,
            capabilities.evidence_hash(), now_ms,
        )
        # A timeout intentionally propagates after provider_pending is durable.
        # The next call resolves and reuses this exact idempotency key.
        adapter.submit({
            "allocation_id": pending["allocation_id"],
            "beneficiary_class": "eov_owner_development",
            "quoted_funding_minor": pending["quoted_funding_minor"],
            "currency": self.store.get_allocation(allocation_id)["policy_snapshot"]["funding_currency"],
        }, pending["provider_operation_id"])
        return pending

    def record_provider_receipt(self, operation_id: str, allocation_id: str, payload: dict, now_ms: int) -> dict:
        """Record human-completed official billing evidence; this never spends funds."""
        receipt = RecordedOfficialBillingAdapter().normalize_receipt(payload)
        # The provider identity comes from persisted pending state.  The payload
        # may provide evidence but cannot select an enabled capability.
        allocation = self.store.get_allocation(allocation_id)
        if receipt["provider"] != allocation.get("provider"):
            raise SettlementError("provider receipt does not match the pending allocation")
        return self.store.confirm_provider_receipt(operation_id, allocation_id, self.owner_subject, receipt, now_ms)

    def reconcile_allocation(self, operation_id: str, allocation_id: str, payload: dict, now_ms: int) -> dict:
        """Normalize official costs and atomically capture only the attributable cost."""
        allocation = self.store.get_allocation(allocation_id)
        provider = allocation.get("provider")
        _, capabilities = self._provider(provider)
        if not capabilities.cost_read:
            raise ProviderCapabilityError("provider does not support official cost reconciliation")
        costs = OpenAICostsNormalizer.normalize(payload)
        return self.store.reconcile_provider_cost(operation_id, allocation_id, self.owner_subject, costs, now_ms)
