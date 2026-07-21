# Universal Possession Ledger
# Logs ALL possessions regardless of inventory properties, concealment abilities, or special effects
# This is the authoritative record - nothing can be hidden from this system

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone
import uuid
import logging

possession_ledger_router = APIRouter(prefix="/ledger", tags=["possession-ledger"])

logger = logging.getLogger(__name__)

# Database connection
def get_db():
    from server import db
    return db

# ============ LEDGER ENTRY TYPES ============
POSSESSION_TYPES = {
    "item": "Physical items, equipment, consumables",
    "currency": "Gold, VE$, tokens, gems",
    "property": "Buildings, land, plots",
    "vehicle": "Mounts, ships, vehicles",
    "creature": "Pets, summons, companions",
    "spell": "Learned spells, abilities",
    "secret": "Hidden knowledge, passwords, keys",
    "contract": "Agreements, deeds, bonds",
    "soul_bound": "Items bound to entity's soul",
    "dimensional": "Items in pocket dimensions or storage",
    "concealed": "Items hidden by magic or abilities",
    "stolen": "Items acquired through theft",
    "cursed": "Cursed or corrupted items",
    "divine": "God-touched or blessed items",
    "void": "Items from the void/other dimensions"
}

# Concealment methods that this ledger bypasses
BYPASSED_CONCEALMENT = [
    "invisibility",
    "pocket_dimension",
    "shadow_storage",
    "soul_binding",
    "dimensional_pocket",
    "thieves_cant_hiding",
    "assassin_stash",
    "magical_concealment",
    "illusion_cover",
    "void_storage",
    "time_locked",
    "parallel_dimension",
    "dream_realm_storage",
    "spirit_realm_cache"
]

class PossessionEntry(BaseModel):
    entity_id: str
    entity_type: str = "player"  # player, npc, ai_villager, creature, building
    possession_type: str
    item_id: str
    item_name: str
    quantity: int = 1
    properties: Dict[str, Any] = Field(default_factory=dict)
    concealment_method: Optional[str] = None
    location: Optional[str] = None  # Where the item physically is
    acquired_method: str = "unknown"  # crafted, looted, traded, stolen, gifted, spawned
    acquired_from: Optional[str] = None
    acquired_at: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class TransferRecord(BaseModel):
    from_entity: str
    to_entity: str
    item_id: str
    quantity: int = 1
    transfer_type: str = "trade"  # trade, gift, theft, drop, loot, confiscate
    witnessed: bool = True
    concealed_transfer: bool = False

# ============ CORE LEDGER FUNCTIONS ============

@possession_ledger_router.post("/record")
async def record_possession(entry: PossessionEntry):
    """
    Record a possession in the universal ledger.
    This bypasses ALL concealment - nothing is hidden from the ledger.
    """
    db = get_db()
    
    ledger_entry = {
        "ledger_id": str(uuid.uuid4()),
        "entity_id": entry.entity_id,
        "entity_type": entry.entity_type,
        "possession_type": entry.possession_type,
        "item_id": entry.item_id,
        "item_name": entry.item_name,
        "quantity": entry.quantity,
        "properties": entry.properties,
        "concealment_method": entry.concealment_method,
        "concealment_bypassed": entry.concealment_method in BYPASSED_CONCEALMENT if entry.concealment_method else False,
        "location": entry.location,
        "acquired_method": entry.acquired_method,
        "acquired_from": entry.acquired_from,
        "acquired_at": entry.acquired_at or datetime.now(timezone.utc).isoformat(),
        "metadata": entry.metadata,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "last_verified": datetime.now(timezone.utc).isoformat(),
        "status": "active"
    }
    
    # Check for existing entry and update or insert
    existing = await db.universal_possession_ledger.find_one({
        "entity_id": entry.entity_id,
        "item_id": entry.item_id
    })
    
    if existing:
        # Update quantity
        await db.universal_possession_ledger.update_one(
            {"ledger_id": existing["ledger_id"]},
            {
                "$inc": {"quantity": entry.quantity},
                "$set": {"last_verified": datetime.now(timezone.utc).isoformat()}
            }
        )
        ledger_entry["ledger_id"] = existing["ledger_id"]
        ledger_entry["quantity"] = existing["quantity"] + entry.quantity
    else:
        await db.universal_possession_ledger.insert_one(ledger_entry)
    
    # Log to audit trail
    await db.ledger_audit_trail.insert_one({
        "audit_id": str(uuid.uuid4()),
        "action": "record",
        "ledger_id": ledger_entry["ledger_id"],
        "entity_id": entry.entity_id,
        "item_id": entry.item_id,
        "item_name": entry.item_name,
        "quantity": entry.quantity,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    logger.info(f"Ledger recorded: {entry.entity_id} possesses {entry.quantity}x {entry.item_name}")
    
    return {
        "recorded": True,
        "ledger_id": ledger_entry["ledger_id"],
        "concealment_bypassed": ledger_entry["concealment_bypassed"]
    }

@possession_ledger_router.post("/transfer")
async def record_transfer(transfer: TransferRecord):
    """
    Record a transfer between entities. Tracks even concealed transfers.
    """
    db = get_db()
    
    # Find the possession in ledger
    from_entry = await db.universal_possession_ledger.find_one({
        "entity_id": transfer.from_entity,
        "item_id": transfer.item_id,
        "status": "active"
    })
    
    if not from_entry:
        raise HTTPException(status_code=404, detail="Possession not found in ledger")
    
    if from_entry["quantity"] < transfer.quantity:
        raise HTTPException(status_code=400, detail="Insufficient quantity")
    
    transfer_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    # Reduce from source
    new_quantity = from_entry["quantity"] - transfer.quantity
    if new_quantity <= 0:
        await db.universal_possession_ledger.update_one(
            {"ledger_id": from_entry["ledger_id"]},
            {"$set": {"status": "transferred", "quantity": 0, "transferred_at": now}}
        )
    else:
        await db.universal_possession_ledger.update_one(
            {"ledger_id": from_entry["ledger_id"]},
            {"$set": {"quantity": new_quantity, "last_verified": now}}
        )
    
    # Add to destination
    to_entry = await db.universal_possession_ledger.find_one({
        "entity_id": transfer.to_entity,
        "item_id": transfer.item_id,
        "status": "active"
    })
    
    if to_entry:
        await db.universal_possession_ledger.update_one(
            {"ledger_id": to_entry["ledger_id"]},
            {"$inc": {"quantity": transfer.quantity}, "$set": {"last_verified": now}}
        )
    else:
        new_entry = {
            "ledger_id": str(uuid.uuid4()),
            "entity_id": transfer.to_entity,
            "entity_type": "unknown",  # Will be updated
            "possession_type": from_entry["possession_type"],
            "item_id": transfer.item_id,
            "item_name": from_entry["item_name"],
            "quantity": transfer.quantity,
            "properties": from_entry["properties"],
            "concealment_method": None,
            "location": None,
            "acquired_method": transfer.transfer_type,
            "acquired_from": transfer.from_entity,
            "acquired_at": now,
            "metadata": {"transfer_id": transfer_id},
            "recorded_at": now,
            "last_verified": now,
            "status": "active"
        }
        await db.universal_possession_ledger.insert_one(new_entry)
    
    # Record transfer in history
    transfer_record = {
        "transfer_id": transfer_id,
        "from_entity": transfer.from_entity,
        "to_entity": transfer.to_entity,
        "item_id": transfer.item_id,
        "item_name": from_entry["item_name"],
        "quantity": transfer.quantity,
        "transfer_type": transfer.transfer_type,
        "witnessed": transfer.witnessed,
        "concealed_transfer": transfer.concealed_transfer,
        "timestamp": now
    }
    await db.possession_transfer_history.insert_one(transfer_record)
    
    # Audit trail
    await db.ledger_audit_trail.insert_one({
        "audit_id": str(uuid.uuid4()),
        "action": "transfer",
        "transfer_id": transfer_id,
        "from_entity": transfer.from_entity,
        "to_entity": transfer.to_entity,
        "item_id": transfer.item_id,
        "quantity": transfer.quantity,
        "concealed": transfer.concealed_transfer,
        "timestamp": now
    })
    
    logger.info(f"Transfer recorded: {transfer.quantity}x {from_entry['item_name']} from {transfer.from_entity} to {transfer.to_entity}")
    
    return {
        "transferred": True,
        "transfer_id": transfer_id,
        "concealed_transfer_logged": transfer.concealed_transfer
    }

@possession_ledger_router.get("/entity/{entity_id}")
async def get_entity_possessions(entity_id: str, include_concealed: bool = True):
    """
    Get ALL possessions for an entity - including concealed items.
    This is the authoritative truth regardless of in-game visibility.
    """
    db = get_db()
    
    query = {"entity_id": entity_id, "status": "active"}
    
    possessions = await db.universal_possession_ledger.find(
        query,
        {"_id": 0}
    ).to_list(1000)
    
    # Categorize
    categorized = {ptype: [] for ptype in POSSESSION_TYPES}
    concealed_count = 0
    total_value = 0
    
    for item in possessions:
        ptype = item.get("possession_type", "item")
        if ptype in categorized:
            categorized[ptype].append(item)
        else:
            categorized["item"].append(item)
        
        if item.get("concealment_method"):
            concealed_count += 1
        
        # Estimate value if available
        if "value" in item.get("properties", {}):
            total_value += item["properties"]["value"] * item.get("quantity", 1)
    
    return {
        "entity_id": entity_id,
        "total_possessions": len(possessions),
        "concealed_items": concealed_count,
        "estimated_total_value": total_value,
        "possessions_by_type": {k: v for k, v in categorized.items() if v},
        "all_possessions": possessions if include_concealed else [p for p in possessions if not p.get("concealment_method")],
        "ledger_note": "This ledger bypasses ALL concealment methods. Nothing is hidden."
    }

@possession_ledger_router.get("/item/{item_id}/history")
async def get_item_history(item_id: str):
    """
    Get complete ownership history of an item across all entities.
    """
    db = get_db()
    
    # Get all ledger entries for this item
    entries = await db.universal_possession_ledger.find(
        {"item_id": item_id},
        {"_id": 0}
    ).sort("recorded_at", 1).to_list(100)
    
    # Get transfer history
    transfers = await db.possession_transfer_history.find(
        {"item_id": item_id},
        {"_id": 0}
    ).sort("timestamp", 1).to_list(100)
    
    # Current holder
    current = next((e for e in entries if e.get("status") == "active" and e.get("quantity", 0) > 0), None)
    
    return {
        "item_id": item_id,
        "current_holder": current["entity_id"] if current else "unknown",
        "current_quantity": current["quantity"] if current else 0,
        "ownership_history": entries,
        "transfer_history": transfers,
        "total_transfers": len(transfers)
    }

@possession_ledger_router.get("/search")
async def search_possessions(
    item_name: Optional[str] = None,
    possession_type: Optional[str] = None,
    concealment_method: Optional[str] = None,
    min_quantity: int = 1,
    limit: int = 100
):
    """
    Search the universal ledger for possessions matching criteria.
    """
    db = get_db()
    
    query = {"status": "active", "quantity": {"$gte": min_quantity}}
    
    if item_name:
        query["item_name"] = {"$regex": item_name, "$options": "i"}
    if possession_type:
        query["possession_type"] = possession_type
    if concealment_method:
        query["concealment_method"] = concealment_method
    
    results = await db.universal_possession_ledger.find(
        query,
        {"_id": 0}
    ).limit(limit).to_list(limit)
    
    return {
        "results": results,
        "count": len(results),
        "search_criteria": {
            "item_name": item_name,
            "possession_type": possession_type,
            "concealment_method": concealment_method,
            "min_quantity": min_quantity
        }
    }

@possession_ledger_router.get("/concealed")
async def get_all_concealed_possessions(limit: int = 100):
    """
    Get all possessions that have concealment methods applied.
    This reveals everything that entities are trying to hide.
    """
    db = get_db()
    
    concealed = await db.universal_possession_ledger.find(
        {"concealment_method": {"$ne": None}, "status": "active"},
        {"_id": 0}
    ).limit(limit).to_list(limit)
    
    # Group by concealment method
    by_method = {}
    for item in concealed:
        method = item.get("concealment_method", "unknown")
        if method not in by_method:
            by_method[method] = []
        by_method[method].append(item)
    
    return {
        "total_concealed": len(concealed),
        "by_concealment_method": by_method,
        "bypassed_methods": BYPASSED_CONCEALMENT,
        "note": "The Universal Ledger sees ALL. Concealment is merely a social construct."
    }

@possession_ledger_router.get("/audit-trail")
async def get_audit_trail(
    entity_id: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100
):
    """
    Get the audit trail of all ledger actions.
    """
    db = get_db()
    
    query = {}
    if entity_id:
        query["$or"] = [
            {"entity_id": entity_id},
            {"from_entity": entity_id},
            {"to_entity": entity_id}
        ]
    if action:
        query["action"] = action
    
    trail = await db.ledger_audit_trail.find(
        query,
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    
    return {
        "audit_trail": trail,
        "count": len(trail)
    }

@possession_ledger_router.get("/stats")
async def get_ledger_stats():
    """
    Get overall statistics from the universal ledger.
    """
    db = get_db()
    
    total_entries = await db.universal_possession_ledger.count_documents({"status": "active"})
    total_concealed = await db.universal_possession_ledger.count_documents({
        "status": "active",
        "concealment_method": {"$ne": None}
    })
    total_transfers = await db.possession_transfer_history.count_documents({})
    
    # By type
    pipeline = [
        {"$match": {"status": "active"}},
        {"$group": {"_id": "$possession_type", "count": {"$sum": 1}, "total_quantity": {"$sum": "$quantity"}}}
    ]
    by_type = await db.universal_possession_ledger.aggregate(pipeline).to_list(20)
    
    # By entity type
    pipeline = [
        {"$match": {"status": "active"}},
        {"$group": {"_id": "$entity_type", "count": {"$sum": 1}}}
    ]
    by_entity = await db.universal_possession_ledger.aggregate(pipeline).to_list(10)
    
    return {
        "total_ledger_entries": total_entries,
        "total_concealed_items": total_concealed,
        "total_transfers_recorded": total_transfers,
        "entries_by_type": {b["_id"]: {"count": b["count"], "quantity": b["total_quantity"]} for b in by_type if b["_id"]},
        "entries_by_entity_type": {b["_id"]: b["count"] for b in by_entity if b["_id"]},
        "concealment_bypass_rate": "100%",
        "ledger_integrity": "absolute"
    }

@possession_ledger_router.delete("/remove/{ledger_id}")
async def remove_possession(ledger_id: str, reason: str = "destroyed"):
    """
    Remove a possession from an entity (destroyed, consumed, etc.)
    """
    db = get_db()
    
    entry = await db.universal_possession_ledger.find_one({"ledger_id": ledger_id})
    if not entry:
        raise HTTPException(status_code=404, detail="Ledger entry not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.universal_possession_ledger.update_one(
        {"ledger_id": ledger_id},
        {"$set": {"status": reason, "removed_at": now}}
    )
    
    # Audit trail
    await db.ledger_audit_trail.insert_one({
        "audit_id": str(uuid.uuid4()),
        "action": "remove",
        "ledger_id": ledger_id,
        "entity_id": entry["entity_id"],
        "item_id": entry["item_id"],
        "item_name": entry["item_name"],
        "reason": reason,
        "timestamp": now
    })
    
    return {
        "removed": True,
        "ledger_id": ledger_id,
        "reason": reason
    }
