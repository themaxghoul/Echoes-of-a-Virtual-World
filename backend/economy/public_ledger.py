"""Privacy-preserving public projection of verified provisional CU claims."""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Dict


SCHEMA = "eov-public-cu-ledger/v1"
UNIT = "CU-placeholder"


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _public_ref(world_id: str, kind: str, private_value: str) -> str:
    return f"{kind}:{_digest(f'{world_id}|{kind}|{private_value}')[:24]}"


def _canonical(value: Dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _entry_chain_hash(previous_hash: str, entry: Dict[str, Any]) -> str:
    payload = {key: value for key, value in entry.items() if key != "chain_hash"}
    return _digest(f"{previous_hash}|{_canonical(payload)}")


def project_public_cu_ledger(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """Publish proof of provisional value without identities or private world state."""
    world_id = str(snapshot["world_id"])
    shared = snapshot.get("state", {}).get("shared_actions", {})
    records = shared.get("records", {})
    events = {event.get("event_id"): event for event in shared.get("ledger", [])}
    claims = shared.get("valuation_claims", [])
    entries = []
    previous_hash = _digest(f"{SCHEMA}|{world_id}|genesis")

    for sequence, claim in enumerate(claims, start=1):
        if claim.get("spendable") is not False:
            raise ValueError("public ledger refuses a spendable claim")
        amount = int(claim.get("amount_milli", 0))
        if amount <= 0:
            raise ValueError("public ledger requires a positive provisional valuation")
        action_id = str(claim.get("action_id", ""))
        record = records.get(action_id)
        if not record or record.get("state") != "commissioned":
            raise ValueError("public ledger requires a commissioned action record")
        if record.get("actor_id") != claim.get("actor_id"):
            raise ValueError("public ledger actor custody does not match the claim")
        evidence = events.get(claim.get("evidence_event"))
        if not evidence or evidence.get("state") != "verified" or not evidence.get("event_hash"):
            raise ValueError("public ledger requires verified hashed evidence")
        commissioned = next(
            (
                event for event in shared.get("ledger", [])
                if event.get("action_id") == action_id and event.get("state") == "commissioned"
            ),
            None,
        )
        if not commissioned or not commissioned.get("event_hash"):
            raise ValueError("public ledger requires a hashed commission event")

        contributor_ref = _public_ref(world_id, "contributor", str(claim["actor_id"]))
        entry = {
            "sequence": sequence,
            "entry_id": _public_ref(world_id, "claim", f"{action_id}|{claim['evidence_event']}|{amount}"),
            "action_ref": _public_ref(world_id, "action", action_id),
            "action_type": str(record.get("definition", {}).get("action_type", "unknown")),
            "status": "verified_provisional",
            "tick_verified": int(evidence.get("tick", 0)),
            "tick_commissioned": int(commissioned.get("tick", 0)),
            "contributor_ref": contributor_ref,
            "verifier_ref": _public_ref(world_id, "verifier", str(record.get("verifier_id", "unknown"))),
            "amount_milli": amount,
            "unit": UNIT,
            "spendable": False,
            "evidence_hash": str(evidence["event_hash"]),
            "commission_hash": str(commissioned["event_hash"]),
            "postings": [
                {"account_ref": "treasury:public-works", "amount_milli": -amount},
                {"account_ref": contributor_ref, "amount_milli": amount},
            ],
            "previous_hash": previous_hash,
        }
        entry["chain_hash"] = _entry_chain_hash(previous_hash, entry)
        previous_hash = entry["chain_hash"]
        entries.append(entry)

    return {
        "schema": SCHEMA,
        "world_ref": _public_ref(world_id, "world", world_id),
        "revision": int(snapshot.get("revision", 0)),
        "tick": int(snapshot.get("tick", 0)),
        "unit": UNIT,
        "spendable": False,
        "external_settlement": "disabled",
        "privacy": "pseudonymous-public-projection",
        "entries": entries,
        "totals": {
            "entry_count": len(entries),
            "provisional_cu_milli": sum(entry["amount_milli"] for entry in entries),
            "posting_balance_milli": sum(posting["amount_milli"] for entry in entries for posting in entry["postings"]),
        },
        "head_hash": previous_hash,
    }


def verify_public_chain(ledger: Dict[str, Any]) -> bool:
    if ledger.get("schema") != SCHEMA or ledger.get("spendable") is not False:
        return False
    entries = copy.deepcopy(ledger.get("entries", []))
    if any(sum(posting.get("amount_milli", 0) for posting in entry.get("postings", [])) != 0 for entry in entries):
        return False
    world_ref = str(ledger.get("world_ref", ""))
    if not world_ref.startswith("world:"):
        return False
    # The first stored previous hash is the public genesis commitment. Later
    # entries must link exactly; a verifier need not know the private world id.
    previous_hash = entries[0].get("previous_hash") if entries else ledger.get("head_hash")
    for expected_sequence, entry in enumerate(entries, start=1):
        if entry.get("sequence") != expected_sequence or entry.get("previous_hash") != previous_hash:
            return False
        calculated = _entry_chain_hash(previous_hash, entry)
        if entry.get("chain_hash") != calculated:
            return False
        previous_hash = calculated
    return previous_hash == ledger.get("head_hash")
