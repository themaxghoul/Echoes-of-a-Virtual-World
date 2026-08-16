"""Authoritative bridge from public CU claims to private owner-compute quotes."""

from __future__ import annotations

from typing import Any

from .compute_sponsorship import ComputeSponsorshipStore, SettlementError
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
