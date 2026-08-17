"""Privacy-preserving, independently verifiable settlement receipts.

The public projection is a derivative of the private sponsorship ledger.  It
is never read back as authority: the store remains the source of truth.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .compute_sponsorship import ComputeSponsorshipStore


SCHEMA = "eov-public-compute-sponsorship/v1"
_HASH = re.compile(r"^sha256:[0-9a-f]{64}$")
_PUBLIC_REF = re.compile(r"^(?:allocation|policy|funding-receipt):[0-9a-f]{64}$")
_SUPPORTED_CURRENCY = "usd"
_PUBLIC_TOP_FIELDS = frozenset({
    "schema", "claims", "policies", "funding_receipts", "root_hash", "allocations", "totals", "head_hash",
})
_ALLOCATION_FIELDS = frozenset({
    "sequence", "allocation_ref", "beneficiary_class", "claim_refs", "policy", "eligible_cu_milli",
    "currency", "state", "provider", "funding", "lifecycle", "evidence", "previous_hash", "chain_hash",
})
_TRANSITIONS = {
    "proposed": {"funding_held", "cancelled"},
    "funding_held": {"owner_approved", "cancelled"},
    "owner_approved": {"provider_pending", "cancelled", "expired"},
    "provider_pending": {"provider_confirmed"},
    "provider_confirmed": {"reconciling"},
    "reconciling": {"reconciled", "reconciliation_exception"},
}


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _public_ref(kind: str, private_value: str) -> str:
    """Commit a non-personal internal identifier in its own public domain."""
    return f"{kind}:{hashlib.sha256(f'{SCHEMA}|{kind}|{private_value}'.encode('utf-8')).hexdigest()}"


def _chain_hash(previous_hash: str, allocation: dict) -> str:
    body = {key: value for key, value in allocation.items() if key != "chain_hash"}
    return _hash(previous_hash + "|" + _canonical(body))


def _root_hash(claims: list[dict], policies: list[dict], funding_receipts: list[dict]) -> str:
    static = {
        "schema": SCHEMA,
        "claims": claims,
        "policies": policies,
        "funding_receipts": funding_receipts,
    }
    return _hash(SCHEMA + "|" + _canonical(static))


def _require_hash(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _HASH.fullmatch(value):
        raise ValueError(f"{field} must be a sha256 commitment")
    return value


def _require_integer(value: Any, field: str, *, positive: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0 or (positive and value <= 0):
        raise ValueError(f"{field} must be a {'positive ' if positive else 'non-negative '}integer")
    return value


def _public_account(account_id: str, allocation_id: str, provider: str | None, currency: str) -> str:
    if account_id == f"reserve:available:{currency}":
        return "reserve:available"
    if account_id == f"reserve:held:{allocation_id}:{currency}":
        return "reserve:held"
    if provider and account_id == f"expense:provider:{provider}:{currency}":
        return "expense:provider"
    raise ValueError("settlement projection encountered a non-public allocation posting")


def project_public_settlement(store: ComputeSponsorshipStore) -> dict:
    """Create an allowlisted, deterministic public settlement projection."""
    if not isinstance(store, ComputeSponsorshipStore):
        raise TypeError("store must be a ComputeSponsorshipStore")
    if not store.audit_funding()["balanced"]:
        raise ValueError("public settlement refuses an unbalanced private ledger")
    records = store.export_settlement_projection_records()

    # Refuse a source ledger whose monetary operations are not balanced before
    # attempting to publish any derivative of it.
    operation_balances: dict[str, int] = {}
    for posting in records["postings"]:
        if posting["currency"] != _SUPPORTED_CURRENCY:
            raise ValueError("public settlement supports only usd")
        operation_balances[posting["operation_id"]] = operation_balances.get(posting["operation_id"], 0) + posting["delta_minor"]
    if any(balance != 0 for balance in operation_balances.values()):
        raise ValueError("public settlement refuses unbalanced private postings")

    policies_by_id: dict[str, dict] = {}
    public_policies = []
    for row in records["policies"]:
        policy = row["policy"]
        currency = policy.get("funding_currency")
        if currency != _SUPPORTED_CURRENCY:
            raise ValueError("public settlement supports only usd")
        formula = policy.get("cu_milli_per_funding_minor")
        _require_integer(formula, "policy formula", positive=True)
        public = {
            "policy_ref": _public_ref("policy", row["policy_id"]),
            "version": _require_integer(row["version"], "policy version", positive=True),
            "formula": {"cu_milli_per_funding_minor": formula},
            "currency": currency,
            "compliance_manifest_hash": _require_hash(policy.get("compliance_manifest_hash"), "compliance manifest"),
        }
        policies_by_id[row["policy_id"]] = public
        public_policies.append(public)
    public_policies.sort(key=lambda policy: policy["policy_ref"])

    commitments_by_allocation: dict[str, list[dict]] = {}
    public_claims_by_id: dict[str, dict] = {}
    for commitment in records["commitments"]:
        claim_id = commitment["claim_id"]
        if not isinstance(claim_id, str) or not claim_id.startswith("claim:"):
            raise ValueError("public settlement requires a public claim reference")
        if commitment["policy_id"] not in policies_by_id:
            raise ValueError("public settlement claim has no policy snapshot")
        public_claims_by_id.setdefault(claim_id, {"claim_ref": claim_id})
        commitments_by_allocation.setdefault(commitment["allocation_id"], []).append(commitment)
    public_claims = sorted(public_claims_by_id.values(), key=lambda claim: claim["claim_ref"])

    public_funding_receipts = []
    receipt_refs_by_currency: dict[str, list[str]] = {}
    for sequence, receipt in enumerate(
        sorted(records["funding_receipts"], key=lambda value: (value["received_at_ms"], value["operation_id"])), start=1
    ):
        if receipt["currency"] != _SUPPORTED_CURRENCY:
            raise ValueError("public settlement supports only usd")
        public_receipt = {
            "sequence": sequence,
            "receipt_ref": _public_ref("funding-receipt", receipt["operation_id"]),
            "amount_minor": _require_integer(receipt["amount_minor"], "funding receipt amount", positive=True),
            "currency": receipt["currency"],
            "evidence_hash": _require_hash(receipt["evidence_hash"], "funding receipt evidence"),
            "received_at_ms": _require_integer(receipt["received_at_ms"], "funding receipt timestamp"),
        }
        public_funding_receipts.append(public_receipt)
        receipt_refs_by_currency.setdefault(receipt["currency"], []).append(public_receipt["receipt_ref"])

    events_by_allocation: dict[str, list[dict]] = {}
    event_by_operation: dict[str, dict] = {}
    for event in records["events"]:
        events_by_allocation.setdefault(event["allocation_id"], []).append(event)
        event_by_operation[event["operation_id"]] = event
    receipts_by_allocation = {row["allocation_id"]: row["receipt_hash"] for row in records["provider_receipts"]}
    costs_by_allocation = {row["allocation_id"]: row["cost_hash"] for row in records["provider_costs"]}
    postings_by_allocation: dict[str, list[dict]] = {}
    for posting in records["postings"]:
        event = event_by_operation.get(posting["operation_id"])
        if event:
            postings_by_allocation.setdefault(event["allocation_id"], []).append(posting)

    allocation_rows = sorted(records["allocations"], key=lambda row: (row["created_at_ms"], row["allocation_id"]))
    public_allocations = []
    for sequence, allocation in enumerate(allocation_rows, start=1):
        policy = policies_by_id.get(allocation["policy_id"])
        snapshot = allocation["policy_snapshot"]
        if policy is None or allocation["policy_version"] != policy["version"]:
            raise ValueError("public settlement allocation has no matching policy snapshot")
        if snapshot.get("funding_currency") != policy["currency"] or snapshot.get("cu_milli_per_funding_minor") != policy["formula"]["cu_milli_per_funding_minor"]:
            raise ValueError("public settlement allocation policy snapshot is inconsistent")
        if allocation["beneficiary_class"] != "eov_owner_development":
            raise ValueError("public settlement beneficiary class is invalid")
        claim_commitments = commitments_by_allocation.get(allocation["allocation_id"], [])
        if not claim_commitments:
            raise ValueError("public settlement allocation is missing claim commitments")
        if any(item["policy_id"] != allocation["policy_id"] for item in claim_commitments):
            raise ValueError("public settlement claim policy link is invalid")
        claim_refs = sorted(item["claim_id"] for item in claim_commitments)
        if len(claim_refs) != len(set(claim_refs)):
            raise ValueError("public settlement allocation has duplicate claim commitments")

        source_events = sorted(events_by_allocation.get(allocation["allocation_id"], []), key=lambda event: event["sequence"])
        lifecycle_events = [
            {"state": event["target_state"], "occurred_at_ms": event["occurred_at_ms"]}
            for event in source_events
        ]
        capability_hash = next((event["capability_hash"] for event in source_events if event["capability_hash"]), None)
        receipt_hash = receipts_by_allocation.get(allocation["allocation_id"])
        cost_hash = costs_by_allocation.get(allocation["allocation_id"])
        state = allocation["state"]
        if state == "reconciled" and (not receipt_hash or not cost_hash or not capability_hash):
            raise ValueError("reconciled allocation requires provider receipt and cost evidence")
        if state == "reconciled" and allocation["actual_cost_effective_at_ms"] is None:
            raise ValueError("reconciled allocation requires provider effective time")

        currency = policy["currency"]
        public_postings = []
        for posting in sorted(
            postings_by_allocation.get(allocation["allocation_id"], []),
            key=lambda value: (value["occurred_at_ms"], value["account_id"], value["delta_minor"]),
        ):
            if posting["currency"] != currency:
                raise ValueError("allocation posting currency is invalid")
            public_postings.append({
                "account_ref": _public_account(posting["account_id"], allocation["allocation_id"], allocation["provider"], currency),
                "amount_minor": posting["delta_minor"],
                "occurred_at_ms": posting["occurred_at_ms"],
            })
        quoted = _require_integer(allocation["quoted_funding_minor"], "quoted funding", positive=True)
        held = quoted if state not in {"proposed", "cancelled"} or allocation["held_at_ms"] is not None else 0
        captured = sum(item["amount_minor"] for item in public_postings if item["account_ref"] == "expense:provider" and item["amount_minor"] > 0)
        released = sum(item["amount_minor"] for item in public_postings if item["account_ref"] == "reserve:available" and item["amount_minor"] > 0)
        public_allocations.append({
            "sequence": sequence,
            "allocation_ref": _public_ref("allocation", allocation["allocation_id"]),
            "beneficiary_class": "eov_owner_development",
            "claim_refs": claim_refs,
            "policy": {
                "policy_ref": policy["policy_ref"],
                "version": policy["version"],
                "formula": policy["formula"],
            },
            "eligible_cu_milli": _require_integer(allocation["eligible_cu_milli"], "eligible CU", positive=True),
            "currency": currency,
            "state": state,
            "provider": allocation["provider"],
            "funding": {
                "quoted_minor": quoted,
                "held_minor": held,
                "captured_minor": captured,
                "released_minor": released,
                "receipt_refs": list(receipt_refs_by_currency.get(currency, [])),
                "postings": public_postings,
            },
            "lifecycle": {
                "created_at_ms": allocation["created_at_ms"],
                "held_at_ms": allocation["held_at_ms"],
                "approved_at_ms": allocation["approved_at_ms"],
                "provider_pending_at_ms": allocation["provider_pending_at_ms"],
                "provider_confirmed_at_ms": allocation["provider_confirmed_at_ms"],
                "reconciled_at_ms": allocation["reconciled_at_ms"],
                "provider_effective_at_ms": allocation["actual_cost_effective_at_ms"],
                "events": lifecycle_events,
            },
            "evidence": {
                "approval_hash": allocation["approval_hash"],
                "provider_capability_hash": capability_hash,
                "provider_receipt_hash": receipt_hash,
                "cost_hash": cost_hash,
            },
            "previous_hash": "",
            "chain_hash": "",
        })

    root_hash = _root_hash(public_claims, public_policies, public_funding_receipts)
    previous_hash = root_hash
    for allocation in public_allocations:
        allocation["previous_hash"] = previous_hash
        allocation["chain_hash"] = _chain_hash(previous_hash, allocation)
        previous_hash = allocation["chain_hash"]
    totals = {
        "allocation_count": len(public_allocations),
        "claim_count": len(public_claims),
        "funding_receipt_count": len(public_funding_receipts),
        "eligible_cu_milli": sum(item["eligible_cu_milli"] for item in public_allocations),
        "quoted_minor": sum(item["funding"]["quoted_minor"] for item in public_allocations),
        "held_minor": sum(item["funding"]["held_minor"] for item in public_allocations),
        "captured_minor": sum(item["funding"]["captured_minor"] for item in public_allocations),
        "released_minor": sum(item["funding"]["released_minor"] for item in public_allocations),
        "posting_balance_minor": sum(
            posting["amount_minor"] for item in public_allocations for posting in item["funding"]["postings"]
        ),
    }
    projection = {
        "schema": SCHEMA,
        "claims": public_claims,
        "policies": public_policies,
        "funding_receipts": public_funding_receipts,
        "root_hash": root_hash,
        "allocations": public_allocations,
        "totals": totals,
        "head_hash": previous_hash,
    }
    if not verify_public_settlement_chain(projection):
        raise ValueError("public settlement refuses an invalid private lifecycle")
    return projection


def _verify_projection(projection: dict) -> None:
    if not isinstance(projection, dict) or set(projection) != _PUBLIC_TOP_FIELDS or projection.get("schema") != SCHEMA:
        raise ValueError("projection schema is invalid")
    claims = projection["claims"]
    policies = projection["policies"]
    funding_receipts = projection["funding_receipts"]
    allocations = projection["allocations"]
    if not all(isinstance(value, list) for value in (claims, policies, funding_receipts, allocations)):
        raise ValueError("projection collections are invalid")
    if projection["root_hash"] != _root_hash(claims, policies, funding_receipts):
        raise ValueError("projection root hash is invalid")

    claim_refs = set()
    for claim in claims:
        if not isinstance(claim, dict) or set(claim) != {"claim_ref"} or not isinstance(claim["claim_ref"], str) or not claim["claim_ref"].startswith("claim:"):
            raise ValueError("public claim allowlist is invalid")
        if claim["claim_ref"] in claim_refs:
            raise ValueError("public claim is duplicated")
        claim_refs.add(claim["claim_ref"])

    policies_by_ref = {}
    for policy in policies:
        if not isinstance(policy, dict) or set(policy) != {"policy_ref", "version", "formula", "currency", "compliance_manifest_hash"}:
            raise ValueError("public policy allowlist is invalid")
        if not isinstance(policy["policy_ref"], str) or not _PUBLIC_REF.fullmatch(policy["policy_ref"]):
            raise ValueError("public policy reference is invalid")
        if policy["policy_ref"] in policies_by_ref or policy["currency"] != _SUPPORTED_CURRENCY:
            raise ValueError("public policy is invalid")
        if set(policy["formula"]) != {"cu_milli_per_funding_minor"}:
            raise ValueError("public policy formula is invalid")
        _require_integer(policy["version"], "policy version", positive=True)
        _require_integer(policy["formula"]["cu_milli_per_funding_minor"], "policy formula", positive=True)
        _require_hash(policy["compliance_manifest_hash"], "policy compliance evidence")
        policies_by_ref[policy["policy_ref"]] = policy

    funding_refs = set()
    for sequence, receipt in enumerate(funding_receipts, start=1):
        if not isinstance(receipt, dict) or set(receipt) != {"sequence", "receipt_ref", "amount_minor", "currency", "evidence_hash", "received_at_ms"}:
            raise ValueError("public funding receipt allowlist is invalid")
        if receipt["sequence"] != sequence or receipt["currency"] != _SUPPORTED_CURRENCY or not isinstance(receipt["receipt_ref"], str) or not _PUBLIC_REF.fullmatch(receipt["receipt_ref"]):
            raise ValueError("public funding receipt is invalid")
        if receipt["receipt_ref"] in funding_refs:
            raise ValueError("public funding receipt is duplicated")
        funding_refs.add(receipt["receipt_ref"])
        _require_integer(receipt["amount_minor"], "funding receipt amount", positive=True)
        _require_integer(receipt["received_at_ms"], "funding receipt timestamp")
        _require_hash(receipt["evidence_hash"], "funding receipt evidence")

    previous_hash = projection["root_hash"]
    seen_allocations = set()
    used_claim_refs = set()
    sort_key = None
    computed = {"eligible_cu_milli": 0, "quoted_minor": 0, "held_minor": 0, "captured_minor": 0, "released_minor": 0, "posting_balance_minor": 0}
    for sequence, allocation in enumerate(allocations, start=1):
        if not isinstance(allocation, dict) or set(allocation) != _ALLOCATION_FIELDS:
            raise ValueError("public allocation allowlist is invalid")
        if allocation["sequence"] != sequence or allocation["previous_hash"] != previous_hash:
            raise ValueError("public allocation chain sequence is invalid")
        if not isinstance(allocation["allocation_ref"], str) or not _PUBLIC_REF.fullmatch(allocation["allocation_ref"]) or allocation["allocation_ref"] in seen_allocations:
            raise ValueError("public allocation reference is invalid")
        seen_allocations.add(allocation["allocation_ref"])
        if allocation["beneficiary_class"] != "eov_owner_development" or allocation["currency"] != _SUPPORTED_CURRENCY or allocation["state"] not in set(_TRANSITIONS) | {"reconciled", "reconciliation_exception", "cancelled", "expired"}:
            raise ValueError("public allocation identity or currency is invalid")
        if allocation["provider"] is not None and (
            not isinstance(allocation["provider"], str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", allocation["provider"])
        ):
            raise ValueError("public provider reference is invalid")
        if allocation["state"] in {"provider_pending", "provider_confirmed", "reconciling", "reconciled", "reconciliation_exception"} and allocation["provider"] is None:
            raise ValueError("provider lifecycle state requires a provider")
        if not isinstance(allocation["claim_refs"], list) or not allocation["claim_refs"] or set(allocation["claim_refs"]) - claim_refs or len(set(allocation["claim_refs"])) != len(allocation["claim_refs"]):
            raise ValueError("public allocation claim links are invalid")
        used_claim_refs.update(allocation["claim_refs"])
        policy = allocation["policy"]
        if not isinstance(policy, dict) or set(policy) != {"policy_ref", "version", "formula"} or policy["policy_ref"] not in policies_by_ref:
            raise ValueError("public allocation policy link is invalid")
        catalog_policy = policies_by_ref[policy["policy_ref"]]
        if policy["version"] != catalog_policy["version"] or policy["formula"] != catalog_policy["formula"]:
            raise ValueError("public allocation policy snapshot is invalid")
        _require_integer(allocation["eligible_cu_milli"], "eligible CU", positive=True)
        funding = allocation["funding"]
        if not isinstance(funding, dict) or set(funding) != {"quoted_minor", "held_minor", "captured_minor", "released_minor", "receipt_refs", "postings"}:
            raise ValueError("public funding allowlist is invalid")
        for field in ("quoted_minor", "held_minor", "captured_minor", "released_minor"):
            _require_integer(funding[field], field)
        if funding["quoted_minor"] <= 0 or not isinstance(funding["receipt_refs"], list) or set(funding["receipt_refs"]) - funding_refs:
            raise ValueError("public funding receipt links are invalid")
        if funding["held_minor"] and not funding["receipt_refs"]:
            raise ValueError("public held funding requires a receipted reserve")
        if not isinstance(funding["postings"], list):
            raise ValueError("public funding postings are invalid")
        posting_balance = 0
        held_postings = captured_postings = released_postings = 0
        for posting in funding["postings"]:
            if not isinstance(posting, dict) or set(posting) != {"account_ref", "amount_minor", "occurred_at_ms"}:
                raise ValueError("public posting allowlist is invalid")
            if posting["account_ref"] not in {"reserve:available", "reserve:held", "expense:provider"}:
                raise ValueError("public posting account is invalid")
            _require_integer(posting["occurred_at_ms"], "posting timestamp")
            if isinstance(posting["amount_minor"], bool) or not isinstance(posting["amount_minor"], int):
                raise ValueError("public posting amount is invalid")
            posting_balance += posting["amount_minor"]
            if posting["account_ref"] == "reserve:held" and posting["amount_minor"] > 0:
                held_postings += posting["amount_minor"]
            elif posting["account_ref"] == "expense:provider" and posting["amount_minor"] > 0:
                captured_postings += posting["amount_minor"]
            elif posting["account_ref"] == "reserve:available" and posting["amount_minor"] > 0:
                released_postings += posting["amount_minor"]
        if posting_balance != 0 or funding["held_minor"] != held_postings or funding["captured_minor"] != captured_postings or funding["released_minor"] != released_postings:
            raise ValueError("public funding postings are unbalanced")

        lifecycle = allocation["lifecycle"]
        if not isinstance(lifecycle, dict) or set(lifecycle) != {"created_at_ms", "held_at_ms", "approved_at_ms", "provider_pending_at_ms", "provider_confirmed_at_ms", "reconciled_at_ms", "provider_effective_at_ms", "events"}:
            raise ValueError("public lifecycle allowlist is invalid")
        for field in ("created_at_ms", "held_at_ms", "approved_at_ms", "provider_pending_at_ms", "provider_confirmed_at_ms", "reconciled_at_ms", "provider_effective_at_ms"):
            if lifecycle[field] is not None:
                _require_integer(lifecycle[field], field)
        key = (lifecycle["created_at_ms"], allocation["allocation_ref"])
        if sort_key is not None and key < sort_key:
            raise ValueError("public allocation order is invalid")
        sort_key = key
        current_state = "proposed"
        last_event_time = lifecycle["created_at_ms"]
        if not isinstance(lifecycle["events"], list):
            raise ValueError("public lifecycle events are invalid")
        for event in lifecycle["events"]:
            if not isinstance(event, dict) or set(event) != {"state", "occurred_at_ms"} or event["state"] not in _TRANSITIONS.get(current_state, set()):
                raise ValueError("public lifecycle transition is invalid")
            _require_integer(event["occurred_at_ms"], "lifecycle timestamp")
            if event["occurred_at_ms"] < last_event_time:
                raise ValueError("public lifecycle chronology is invalid")
            current_state = event["state"]
            last_event_time = event["occurred_at_ms"]
        if current_state != allocation["state"]:
            raise ValueError("public lifecycle state is invalid")
        evidence = allocation["evidence"]
        if not isinstance(evidence, dict) or set(evidence) != {"approval_hash", "provider_capability_hash", "provider_receipt_hash", "cost_hash"}:
            raise ValueError("public evidence allowlist is invalid")
        for value in evidence.values():
            if value is not None:
                _require_hash(value, "public evidence")
        if current_state == "reconciled":
            if not all(evidence.values()) or lifecycle["reconciled_at_ms"] is None or lifecycle["provider_effective_at_ms"] is None or lifecycle["provider_effective_at_ms"] > lifecycle["reconciled_at_ms"]:
                raise ValueError("reconciled receipt evidence is incomplete")
            if funding["captured_minor"] + funding["released_minor"] != funding["held_minor"]:
                raise ValueError("reconciled funding totals are invalid")
        calculated_hash = _chain_hash(previous_hash, allocation)
        if allocation["chain_hash"] != calculated_hash:
            raise ValueError("public allocation hash is invalid")
        previous_hash = calculated_hash
        computed["eligible_cu_milli"] += allocation["eligible_cu_milli"]
        computed["quoted_minor"] += funding["quoted_minor"]
        computed["held_minor"] += funding["held_minor"]
        computed["captured_minor"] += funding["captured_minor"]
        computed["released_minor"] += funding["released_minor"]
        computed["posting_balance_minor"] += posting_balance
    if used_claim_refs != claim_refs:
        raise ValueError("public claim set has broken allocation links")
    if projection["head_hash"] != previous_hash:
        raise ValueError("public settlement head hash is invalid")
    expected_totals = {
        "allocation_count": len(allocations),
        "claim_count": len(claims),
        "funding_receipt_count": len(funding_receipts),
        **computed,
    }
    if projection["totals"] != expected_totals or computed["posting_balance_minor"] != 0:
        raise ValueError("public settlement totals are invalid")


def verify_public_settlement_chain(projection: dict) -> bool:
    """Independently verify the public chain without accessing private state."""
    try:
        _verify_projection(projection)
    except (KeyError, TypeError, ValueError):
        return False
    return True
