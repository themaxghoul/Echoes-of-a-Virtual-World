"""
NPC Memory Delocalization System
================================
Memory is NOT centralized. NPCs only recall events they:
1. Personally witnessed (were present at the location during the event)
2. Received evidence of (through items, documents, or other NPCs)

Memory states are written to individual NPC state properties when they encounter
incidents through witnessing or evidence transfer.

This creates organic information flow where:
- Gossip spreads through NPC-to-NPC conversations
- Players can manipulate information by controlling evidence
- Secrets can remain hidden unless witnesses talk
- False information can spread if evidence is fabricated
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
import os
import uuid

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

router = APIRouter(prefix="/api/npc-memory", tags=["NPC Memory Delocalization"])

# ============ Memory Event Types ============
MEMORY_EVENT_TYPES = {
    "witnessed_action": {
        "description": "NPC was physically present and saw the action",
        "reliability": 1.0,  # 100% accurate
        "decay_rate": 0.001  # Very slow decay for witnessed events
    },
    "heard_rumor": {
        "description": "NPC heard about this from another NPC",
        "reliability": 0.7,  # 70% accurate, may contain distortions
        "decay_rate": 0.01  # Rumors fade faster
    },
    "received_evidence": {
        "description": "NPC received physical evidence (item, document)",
        "reliability": 0.9,  # 90% accurate - evidence-based
        "decay_rate": 0.002  # Slow decay, evidence persists
    },
    "fabricated_info": {
        "description": "Information was intentionally planted/fabricated",
        "reliability": 0.0,  # False information
        "decay_rate": 0.005  # Moderate decay
    },
    "confession": {
        "description": "Someone confessed this action directly",
        "reliability": 0.95,  # High accuracy
        "decay_rate": 0.003
    },
    "deduced": {
        "description": "NPC logically deduced this from other knowledge",
        "reliability": 0.6,  # May be incorrect deduction
        "decay_rate": 0.008
    }
}

# ============ Evidence Types ============
EVIDENCE_TYPES = {
    "physical_item": {
        "description": "A tangible object proving the event",
        "transfer_reliability_loss": 0.05,  # 5% reliability loss per transfer
        "can_be_destroyed": True
    },
    "written_document": {
        "description": "A letter, note, or formal document",
        "transfer_reliability_loss": 0.02,
        "can_be_destroyed": True,
        "can_be_copied": True
    },
    "magical_imprint": {
        "description": "Magical trace left by the event",
        "transfer_reliability_loss": 0.10,
        "can_be_destroyed": False,  # Cannot be destroyed, fades naturally
        "decay_rate": 0.02
    },
    "witness_testimony": {
        "description": "Verbal account from another entity",
        "transfer_reliability_loss": 0.15,  # High loss - telephone game effect
        "can_be_destroyed": False
    },
    "divine_revelation": {
        "description": "Oracle or divine knowledge",
        "transfer_reliability_loss": 0.0,  # Perfect information
        "can_be_destroyed": False,
        "requires_oracle": True
    }
}

# ============ Memory Propagation Rules ============
PROPAGATION_RULES = {
    "gossip_chance": 0.3,  # 30% chance NPC shares memory in conversation
    "gossip_reliability_loss": 0.1,  # 10% reliability loss per gossip
    "max_propagation_hops": 5,  # Memory degrades after 5 transfers
    "merchant_gossip_bonus": 0.2,  # Merchants 20% more likely to spread info
    "innkeeper_gossip_bonus": 0.4,  # Innkeepers 40% more likely
    "hermit_gossip_penalty": -0.25  # Hermits less likely to share
}


# ============ Pydantic Models ============
class MemoryEventCreate(BaseModel):
    event_type: str = Field(..., description="Type of event that occurred")
    actor_id: str = Field(..., description="ID of entity who performed the action")
    actor_name: str = Field(..., description="Name of the actor")
    action: str = Field(..., description="What action was performed")
    target_id: Optional[str] = Field(None, description="ID of target entity if any")
    target_name: Optional[str] = Field(None, description="Name of target")
    location_id: str = Field(..., description="Where the event occurred")
    location_name: str = Field(..., description="Name of the location")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional event details")
    witnesses: List[str] = Field(default=[], description="List of NPC IDs who witnessed")


class MemoryTransfer(BaseModel):
    memory_id: str = Field(..., description="ID of the memory to transfer")
    source_npc_id: str = Field(..., description="NPC sharing the memory")
    target_npc_id: str = Field(..., description="NPC receiving the memory")
    transfer_type: str = Field(..., description="How memory is transferred: gossip, evidence, confession")
    evidence_id: Optional[str] = Field(None, description="ID of evidence item if applicable")


class EvidenceCreate(BaseModel):
    evidence_type: str = Field(..., description="Type of evidence")
    linked_memory_id: str = Field(..., description="Memory this evidence relates to")
    description: str = Field(..., description="Description of the evidence")
    current_holder_id: str = Field(..., description="Who currently possesses this evidence")
    current_holder_type: str = Field(default="npc", description="npc, player, or location")


class NPCMemoryQuery(BaseModel):
    npc_id: str = Field(..., description="NPC to query memories for")
    query_type: str = Field(default="all", description="all, witnessed, rumors, evidence_based")
    about_entity_id: Optional[str] = Field(None, description="Filter memories about specific entity")
    min_reliability: float = Field(default=0.0, description="Minimum reliability threshold")


# ============ API Endpoints ============

@router.get("/event-types")
async def get_event_types():
    """Get all memory event types and their properties."""
    return {
        "event_types": MEMORY_EVENT_TYPES,
        "evidence_types": EVIDENCE_TYPES,
        "propagation_rules": PROPAGATION_RULES
    }


@router.post("/event/record")
async def record_memory_event(event: MemoryEventCreate):
    """
    Record an event that occurred in the world.
    This automatically creates memories for all witness NPCs.
    """
    event_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc)
    
    # Create the world event record
    world_event = {
        "event_id": event_id,
        "event_type": event.event_type,
        "actor_id": event.actor_id,
        "actor_name": event.actor_name,
        "action": event.action,
        "target_id": event.target_id,
        "target_name": event.target_name,
        "location_id": event.location_id,
        "location_name": event.location_name,
        "details": event.details or {},
        "timestamp": timestamp.isoformat(),
        "witnesses": event.witnesses
    }
    
    await db.world_events.insert_one(world_event)
    
    # Create individual memory entries for each witness
    memories_created = []
    for npc_id in event.witnesses:
        memory = {
            "memory_id": str(uuid.uuid4()),
            "npc_id": npc_id,
            "source_event_id": event_id,
            "memory_type": "witnessed_action",
            "actor_id": event.actor_id,
            "actor_name": event.actor_name,
            "action": event.action,
            "target_id": event.target_id,
            "target_name": event.target_name,
            "location_id": event.location_id,
            "location_name": event.location_name,
            "details": event.details or {},
            "reliability": MEMORY_EVENT_TYPES["witnessed_action"]["reliability"],
            "decay_rate": MEMORY_EVENT_TYPES["witnessed_action"]["decay_rate"],
            "acquired_timestamp": timestamp.isoformat(),
            "propagation_hops": 0,
            "source_chain": [],  # Empty for witnessed events
            "evidence_ids": []
        }
        await db.npc_memories.insert_one(memory)
        memories_created.append({"npc_id": npc_id, "memory_id": memory["memory_id"]})
    
    return {
        "success": True,
        "event_id": event_id,
        "witnesses_count": len(event.witnesses),
        "memories_created": memories_created,
        "message": f"Event recorded. {len(event.witnesses)} NPCs witnessed and will remember."
    }


@router.post("/transfer")
async def transfer_memory(transfer: MemoryTransfer):
    """
    Transfer a memory from one NPC to another.
    Reliability decreases based on transfer type.
    """
    # Get the source memory
    source_memory = await db.npc_memories.find_one({
        "memory_id": transfer.memory_id,
        "npc_id": transfer.source_npc_id
    })
    
    if not source_memory:
        raise HTTPException(status_code=404, detail="Memory not found for source NPC")
    
    # Check if target already has this memory
    existing = await db.npc_memories.find_one({
        "npc_id": transfer.target_npc_id,
        "source_event_id": source_memory["source_event_id"]
    })
    
    if existing:
        # Update existing memory if new one is more reliable
        if source_memory["reliability"] > existing["reliability"]:
            await db.npc_memories.update_one(
                {"memory_id": existing["memory_id"]},
                {"$set": {"reliability": source_memory["reliability"] * 0.95}}  # Slight loss even on update
            )
            return {
                "success": True,
                "message": "Existing memory updated with more reliable information",
                "new_reliability": source_memory["reliability"] * 0.95
            }
        return {
            "success": False,
            "message": "Target NPC already has more reliable memory of this event"
        }
    
    # Calculate reliability loss based on transfer type
    reliability_loss = PROPAGATION_RULES["gossip_reliability_loss"]
    memory_type = "heard_rumor"
    
    if transfer.transfer_type == "evidence":
        memory_type = "received_evidence"
        reliability_loss = EVIDENCE_TYPES.get(
            "physical_item", {}
        ).get("transfer_reliability_loss", 0.05)
    elif transfer.transfer_type == "confession":
        memory_type = "confession"
        reliability_loss = 0.05
    
    # Check propagation limit
    propagation_hops = source_memory.get("propagation_hops", 0) + 1
    if propagation_hops > PROPAGATION_RULES["max_propagation_hops"]:
        return {
            "success": False,
            "message": "Memory too degraded to transfer reliably. Information lost to time."
        }
    
    new_reliability = max(0.1, source_memory["reliability"] - reliability_loss)
    
    # Create new memory for target NPC
    new_memory = {
        "memory_id": str(uuid.uuid4()),
        "npc_id": transfer.target_npc_id,
        "source_event_id": source_memory["source_event_id"],
        "memory_type": memory_type,
        "actor_id": source_memory["actor_id"],
        "actor_name": source_memory["actor_name"],
        "action": source_memory["action"],
        "target_id": source_memory.get("target_id"),
        "target_name": source_memory.get("target_name"),
        "location_id": source_memory["location_id"],
        "location_name": source_memory["location_name"],
        "details": source_memory.get("details", {}),
        "reliability": new_reliability,
        "decay_rate": MEMORY_EVENT_TYPES[memory_type]["decay_rate"],
        "acquired_timestamp": datetime.now(timezone.utc).isoformat(),
        "propagation_hops": propagation_hops,
        "source_chain": source_memory.get("source_chain", []) + [transfer.source_npc_id],
        "evidence_ids": [transfer.evidence_id] if transfer.evidence_id else []
    }
    
    await db.npc_memories.insert_one(new_memory)
    
    return {
        "success": True,
        "memory_id": new_memory["memory_id"],
        "transfer_type": transfer.transfer_type,
        "reliability": new_reliability,
        "propagation_hops": propagation_hops,
        "message": f"Memory transferred via {transfer.transfer_type}. Reliability: {new_reliability:.0%}"
    }


@router.get("/npc/{npc_id}/memories")
async def get_npc_memories(
    npc_id: str,
    min_reliability: float = 0.0,
    about_entity: Optional[str] = None,
    memory_type: Optional[str] = None
):
    """
    Get all memories an NPC has access to.
    This is the ONLY way to access what an NPC "knows".
    """
    query = {"npc_id": npc_id, "reliability": {"$gte": min_reliability}}
    
    if about_entity:
        query["$or"] = [
            {"actor_id": about_entity},
            {"target_id": about_entity}
        ]
    
    if memory_type:
        query["memory_type"] = memory_type
    
    cursor = db.npc_memories.find(query, {"_id": 0})
    memories = await cursor.to_list(length=None)
    
    # Sort by reliability (most reliable first), then by timestamp
    memories.sort(key=lambda m: (-m.get("reliability", 0), m.get("acquired_timestamp", "")))
    
    return {
        "npc_id": npc_id,
        "total_memories": len(memories),
        "memories": memories,
        "reliability_summary": {
            "witnessed": len([m for m in memories if m.get("memory_type") == "witnessed_action"]),
            "rumors": len([m for m in memories if m.get("memory_type") == "heard_rumor"]),
            "evidence_based": len([m for m in memories if m.get("memory_type") == "received_evidence"]),
            "confessions": len([m for m in memories if m.get("memory_type") == "confession"]),
            "deductions": len([m for m in memories if m.get("memory_type") == "deduced"])
        }
    }


@router.get("/npc/{npc_id}/knows-about/{entity_id}")
async def check_npc_knowledge(npc_id: str, entity_id: str):
    """
    Check what a specific NPC knows about a specific entity.
    Returns structured knowledge with reliability scores.
    """
    cursor = db.npc_memories.find({
        "npc_id": npc_id,
        "$or": [
            {"actor_id": entity_id},
            {"target_id": entity_id}
        ]
    }, {"_id": 0})
    
    memories = await cursor.to_list(length=None)
    
    if not memories:
        return {
            "npc_id": npc_id,
            "about_entity": entity_id,
            "knows_anything": False,
            "message": "This NPC has no knowledge of the specified entity."
        }
    
    # Categorize knowledge
    knowledge = {
        "actions_performed": [],  # Things entity did
        "actions_received": [],   # Things done to entity
        "locations_seen": set(),
        "most_reliable_memory": None,
        "total_memories": len(memories)
    }
    
    highest_reliability = 0
    for memory in memories:
        rel = memory.get("reliability", 0)
        if rel > highest_reliability:
            highest_reliability = rel
            knowledge["most_reliable_memory"] = memory
        
        if memory.get("actor_id") == entity_id:
            knowledge["actions_performed"].append({
                "action": memory.get("action"),
                "target": memory.get("target_name"),
                "reliability": rel,
                "source": memory.get("memory_type")
            })
        else:
            knowledge["actions_received"].append({
                "action": memory.get("action"),
                "actor": memory.get("actor_name"),
                "reliability": rel,
                "source": memory.get("memory_type")
            })
        
        knowledge["locations_seen"].add(memory.get("location_name"))
    
    knowledge["locations_seen"] = list(knowledge["locations_seen"])
    
    return {
        "npc_id": npc_id,
        "about_entity": entity_id,
        "knows_anything": True,
        "knowledge": knowledge
    }


@router.post("/evidence/create")
async def create_evidence(evidence: EvidenceCreate):
    """
    Create physical evidence that can be transferred between entities.
    Evidence can prove or support memories.
    """
    if evidence.evidence_type not in EVIDENCE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid evidence type. Valid types: {list(EVIDENCE_TYPES.keys())}"
        )
    
    evidence_data = {
        "evidence_id": str(uuid.uuid4()),
        "evidence_type": evidence.evidence_type,
        "linked_memory_id": evidence.linked_memory_id,
        "description": evidence.description,
        "current_holder_id": evidence.current_holder_id,
        "current_holder_type": evidence.current_holder_type,
        "properties": EVIDENCE_TYPES[evidence.evidence_type],
        "created_timestamp": datetime.now(timezone.utc).isoformat(),
        "transfer_history": [{
            "holder_id": evidence.current_holder_id,
            "holder_type": evidence.current_holder_type,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }],
        "destroyed": False
    }
    
    await db.memory_evidence.insert_one(evidence_data)
    
    return {
        "success": True,
        "evidence_id": evidence_data["evidence_id"],
        "evidence_type": evidence.evidence_type,
        "message": f"Evidence created and held by {evidence.current_holder_id}"
    }


@router.post("/evidence/{evidence_id}/transfer")
async def transfer_evidence(evidence_id: str, new_holder_id: str, new_holder_type: str = "npc"):
    """
    Transfer evidence to a new holder.
    This can trigger memory creation if the evidence links to an unknown event.
    """
    evidence = await db.memory_evidence.find_one({"evidence_id": evidence_id})
    
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    
    if evidence.get("destroyed"):
        raise HTTPException(status_code=400, detail="This evidence has been destroyed")
    
    # Record transfer
    transfer_record = {
        "holder_id": new_holder_id,
        "holder_type": new_holder_type,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    await db.memory_evidence.update_one(
        {"evidence_id": evidence_id},
        {
            "$set": {
                "current_holder_id": new_holder_id,
                "current_holder_type": new_holder_type
            },
            "$push": {"transfer_history": transfer_record}
        }
    )
    
    # If holder is NPC, potentially create/update memory based on evidence
    if new_holder_type == "npc":
        linked_memory_id = evidence.get("linked_memory_id")
        if linked_memory_id:
            # Check if NPC already has this memory
            existing = await db.npc_memories.find_one({
                "npc_id": new_holder_id,
                "memory_id": linked_memory_id
            })
            
            if not existing:
                # Find original event
                original_memory = await db.npc_memories.find_one({"memory_id": linked_memory_id})
                if original_memory:
                    # Create evidence-based memory for the new holder
                    new_memory = {
                        "memory_id": str(uuid.uuid4()),
                        "npc_id": new_holder_id,
                        "source_event_id": original_memory.get("source_event_id"),
                        "memory_type": "received_evidence",
                        "actor_id": original_memory.get("actor_id"),
                        "actor_name": original_memory.get("actor_name"),
                        "action": original_memory.get("action"),
                        "target_id": original_memory.get("target_id"),
                        "target_name": original_memory.get("target_name"),
                        "location_id": original_memory.get("location_id"),
                        "location_name": original_memory.get("location_name"),
                        "details": original_memory.get("details", {}),
                        "reliability": MEMORY_EVENT_TYPES["received_evidence"]["reliability"],
                        "decay_rate": MEMORY_EVENT_TYPES["received_evidence"]["decay_rate"],
                        "acquired_timestamp": datetime.now(timezone.utc).isoformat(),
                        "propagation_hops": 0,
                        "source_chain": [],
                        "evidence_ids": [evidence_id]
                    }
                    await db.npc_memories.insert_one(new_memory)
                    
                    return {
                        "success": True,
                        "evidence_id": evidence_id,
                        "new_holder": new_holder_id,
                        "memory_created": True,
                        "new_memory_id": new_memory["memory_id"],
                        "message": "Evidence transferred. NPC now has knowledge of the linked event."
                    }
    
    return {
        "success": True,
        "evidence_id": evidence_id,
        "new_holder": new_holder_id,
        "memory_created": False
    }


@router.delete("/evidence/{evidence_id}/destroy")
async def destroy_evidence(evidence_id: str, destroyer_id: str):
    """
    Destroy evidence. Only the current holder can destroy it.
    Some evidence types cannot be destroyed.
    """
    evidence = await db.memory_evidence.find_one({"evidence_id": evidence_id})
    
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    
    if evidence.get("current_holder_id") != destroyer_id:
        raise HTTPException(status_code=403, detail="Only the current holder can destroy evidence")
    
    if not evidence.get("properties", {}).get("can_be_destroyed", True):
        raise HTTPException(
            status_code=400,
            detail=f"This type of evidence ({evidence['evidence_type']}) cannot be destroyed"
        )
    
    await db.memory_evidence.update_one(
        {"evidence_id": evidence_id},
        {
            "$set": {
                "destroyed": True,
                "destroyed_by": destroyer_id,
                "destroyed_timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {
        "success": True,
        "evidence_id": evidence_id,
        "message": "Evidence has been destroyed. Existing memories remain but are harder to verify."
    }


@router.post("/gossip/simulate")
async def simulate_gossip_round(location_id: str):
    """
    Simulate a round of gossip at a location.
    NPCs present may share memories with each other based on propagation rules.
    """
    import random
    
    # Get NPCs at this location (simplified - would need actual NPC tracking)
    # For now, query NPCs who have memories about this location
    cursor = db.npc_memories.find({"location_id": location_id}, {"npc_id": 1})
    npc_docs = await cursor.to_list(length=None)
    npcs_at_location = list(set(doc["npc_id"] for doc in npc_docs))
    
    if len(npcs_at_location) < 2:
        return {
            "success": True,
            "message": "Not enough NPCs present for gossip",
            "transfers": []
        }
    
    transfers = []
    
    for npc_id in npcs_at_location:
        # Check gossip chance
        if random.random() > PROPAGATION_RULES["gossip_chance"]:
            continue
        
        # Get a random memory to share
        memories = await db.npc_memories.find(
            {"npc_id": npc_id, "reliability": {"$gte": 0.3}}
        ).to_list(length=10)
        
        if not memories:
            continue
        
        memory_to_share = random.choice(memories)
        
        # Pick random recipient
        other_npcs = [n for n in npcs_at_location if n != npc_id]
        if not other_npcs:
            continue
        
        target_npc = random.choice(other_npcs)
        
        # Attempt transfer
        transfer_result = await transfer_memory(MemoryTransfer(
            memory_id=memory_to_share["memory_id"],
            source_npc_id=npc_id,
            target_npc_id=target_npc,
            transfer_type="gossip"
        ))
        
        if transfer_result.get("success"):
            transfers.append({
                "from": npc_id,
                "to": target_npc,
                "about": memory_to_share.get("action"),
                "reliability": transfer_result.get("reliability")
            })
    
    return {
        "success": True,
        "location_id": location_id,
        "npcs_present": len(npcs_at_location),
        "transfers": transfers,
        "message": f"Gossip round complete. {len(transfers)} memories spread."
    }


@router.get("/stats")
async def get_memory_system_stats():
    """Get overall statistics about the delocalized memory system."""
    total_events = await db.world_events.count_documents({})
    total_memories = await db.npc_memories.count_documents({})
    total_evidence = await db.memory_evidence.count_documents({"destroyed": {"$ne": True}})
    
    # Memory type breakdown
    witnessed = await db.npc_memories.count_documents({"memory_type": "witnessed_action"})
    rumors = await db.npc_memories.count_documents({"memory_type": "heard_rumor"})
    evidence_based = await db.npc_memories.count_documents({"memory_type": "received_evidence"})
    
    # Average reliability
    pipeline = [
        {"$group": {"_id": None, "avg_reliability": {"$avg": "$reliability"}}}
    ]
    result = await db.npc_memories.aggregate(pipeline).to_list(1)
    avg_reliability = result[0]["avg_reliability"] if result else 0
    
    return {
        "total_world_events": total_events,
        "total_npc_memories": total_memories,
        "active_evidence": total_evidence,
        "memory_breakdown": {
            "witnessed": witnessed,
            "rumors": rumors,
            "evidence_based": evidence_based
        },
        "average_reliability": round(avg_reliability, 2),
        "system_description": "Memory is delocalized - NPCs only know what they witnessed or learned through evidence/gossip."
    }
