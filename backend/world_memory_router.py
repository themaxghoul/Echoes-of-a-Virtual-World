"""
World Memory System
====================
Global memories that persist across all players and represent world-changing events.
Unlike NPC delocalized memory, World Memories are events that impact the entire
virtual verse and are visible to all who seek them.

World Memories include:
- Major discoveries (First Discoveries)
- Territory claims and changes
- World events (demon invasions, natural disasters)
- Player achievements that affect the world
- NPC deaths or transformations
- Structural changes to locations
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

router = APIRouter(prefix="/api/world-memory", tags=["World Memory"])

# ============ World Memory Types ============
MEMORY_TYPES = {
    "first_discovery": {
        "name": "First Discovery",
        "description": "A new material, spell, or combination was discovered",
        "impact_level": "regional",
        "persistence": "permanent",
        "icon": "sparkles"
    },
    "territory_claim": {
        "name": "Territory Claim",
        "description": "A player claimed land in the world",
        "impact_level": "local",
        "persistence": "permanent",
        "icon": "flag"
    },
    "structure_built": {
        "name": "Structure Built",
        "description": "A building or structure was constructed",
        "impact_level": "local",
        "persistence": "permanent",
        "icon": "building"
    },
    "world_event": {
        "name": "World Event",
        "description": "A major event affected the world",
        "impact_level": "global",
        "persistence": "permanent",
        "icon": "globe"
    },
    "demon_invasion": {
        "name": "Demon Invasion",
        "description": "Demons attacked a location",
        "impact_level": "regional",
        "persistence": "temporary",
        "icon": "skull"
    },
    "npc_transformation": {
        "name": "NPC Transformation",
        "description": "An NPC underwent a significant change",
        "impact_level": "local",
        "persistence": "permanent",
        "icon": "user"
    },
    "player_achievement": {
        "name": "Player Achievement",
        "description": "A player achieved something world-affecting",
        "impact_level": "global",
        "persistence": "permanent",
        "icon": "trophy"
    },
    "alliance_formed": {
        "name": "Alliance Formed",
        "description": "A group or alliance was established",
        "impact_level": "regional",
        "persistence": "permanent",
        "icon": "users"
    },
    "battle_outcome": {
        "name": "Battle Outcome",
        "description": "A significant battle occurred",
        "impact_level": "regional",
        "persistence": "permanent",
        "icon": "swords"
    },
    "economic_shift": {
        "name": "Economic Shift",
        "description": "A change in the world economy",
        "impact_level": "global",
        "persistence": "temporary",
        "icon": "trending"
    }
}

# Impact levels determine visibility
IMPACT_LEVELS = {
    "local": {"radius": 10, "description": "Affects immediate area"},
    "regional": {"radius": 50, "description": "Affects the region"},
    "global": {"radius": -1, "description": "Affects the entire world"}  # -1 means infinite
}


# ============ Pydantic Models ============
class WorldMemoryCreate(BaseModel):
    memory_type: str = Field(..., description="Type of world memory")
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=10, max_length=2000)
    actor_id: str = Field(..., description="ID of entity that caused this memory")
    actor_name: str = Field(..., description="Name of the actor")
    actor_type: str = Field(default="player", description="player, npc, or system")
    location: Optional[Dict[str, int]] = Field(None, description="World coordinates {x, y}")
    location_name: Optional[str] = None
    affected_entities: List[str] = Field(default=[], description="IDs of affected entities")
    metadata: Optional[Dict[str, Any]] = None


class WorldMemoryQuery(BaseModel):
    location: Optional[Dict[str, int]] = None
    radius: Optional[int] = None
    memory_types: Optional[List[str]] = None
    actor_id: Optional[str] = None
    limit: int = Field(default=50, le=200)


# ============ API Endpoints ============

@router.get("/types")
async def get_memory_types():
    """Get all world memory types."""
    return {
        "memory_types": MEMORY_TYPES,
        "impact_levels": IMPACT_LEVELS
    }


@router.post("/record")
async def record_world_memory(memory: WorldMemoryCreate):
    """
    Record a new world memory.
    This is for events that impact the world and should be visible to all.
    """
    if memory.memory_type not in MEMORY_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid memory type. Valid: {list(MEMORY_TYPES.keys())}"
        )
    
    memory_type_info = MEMORY_TYPES[memory.memory_type]
    
    world_memory = {
        "memory_id": str(uuid.uuid4()),
        "memory_type": memory.memory_type,
        "type_name": memory_type_info["name"],
        "title": memory.title,
        "description": memory.description,
        "actor_id": memory.actor_id,
        "actor_name": memory.actor_name,
        "actor_type": memory.actor_type,
        "location": memory.location,
        "location_name": memory.location_name,
        "affected_entities": memory.affected_entities,
        "metadata": memory.metadata or {},
        "impact_level": memory_type_info["impact_level"],
        "persistence": memory_type_info["persistence"],
        "icon": memory_type_info["icon"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "witnesses": [],  # Players who have "seen" this memory
        "reactions": {}  # Player reactions to this memory
    }
    
    await db.world_memories.insert_one(world_memory)
    
    return {
        "success": True,
        "memory_id": world_memory["memory_id"],
        "impact_level": memory_type_info["impact_level"],
        "message": f"World memory recorded: {memory.title}"
    }


@router.get("/global")
async def get_global_memories(limit: int = 50, skip: int = 0):
    """
    Get global world memories visible to everyone.
    These are events that affected the entire world.
    """
    cursor = db.world_memories.find(
        {"impact_level": "global"},
        {"_id": 0}
    ).sort("created_at", -1).skip(skip).limit(limit)
    
    memories = await cursor.to_list(length=limit)
    total = await db.world_memories.count_documents({"impact_level": "global"})
    
    return {
        "memories": memories,
        "total": total,
        "returned": len(memories)
    }


@router.get("/at-location")
async def get_memories_at_location(x: int, y: int, radius: int = 20):
    """
    Get world memories visible at a specific location.
    Includes local, regional (if in range), and global memories.
    """
    import math
    
    # Global memories are always visible
    global_memories = await db.world_memories.find(
        {"impact_level": "global"},
        {"_id": 0}
    ).sort("created_at", -1).limit(20).to_list(20)
    
    # Regional and local memories based on distance
    all_located = await db.world_memories.find(
        {
            "impact_level": {"$in": ["regional", "local"]},
            "location": {"$exists": True}
        },
        {"_id": 0}
    ).sort("created_at", -1).limit(200).to_list(200)
    
    nearby_memories = []
    for mem in all_located:
        loc = mem.get("location")
        if not loc:
            continue
        
        distance = math.sqrt((loc.get("x", 0) - x)**2 + (loc.get("y", 0) - y)**2)
        impact_radius = IMPACT_LEVELS.get(mem["impact_level"], {}).get("radius", 10)
        
        if distance <= max(impact_radius, radius):
            mem["distance"] = round(distance, 1)
            nearby_memories.append(mem)
    
    # Sort by created_at
    nearby_memories.sort(key=lambda m: m.get("created_at", ""), reverse=True)
    
    return {
        "location": {"x": x, "y": y},
        "radius": radius,
        "global_memories": global_memories,
        "nearby_memories": nearby_memories[:50],
        "total_nearby": len(nearby_memories)
    }


@router.get("/chronicle")
async def get_world_chronicle(
    memory_type: Optional[str] = None,
    actor_type: Optional[str] = None,
    limit: int = 100
):
    """
    Get the world chronicle - a historical record of all world memories.
    This is the "history book" of the virtual verse.
    """
    query = {}
    if memory_type:
        query["memory_type"] = memory_type
    if actor_type:
        query["actor_type"] = actor_type
    
    cursor = db.world_memories.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).limit(limit)
    
    memories = await cursor.to_list(length=limit)
    
    # Group by date
    chronicle = {}
    for mem in memories:
        date = mem.get("created_at", "")[:10]  # YYYY-MM-DD
        if date not in chronicle:
            chronicle[date] = []
        chronicle[date].append(mem)
    
    return {
        "chronicle": chronicle,
        "total_entries": len(memories)
    }


@router.post("/witness/{memory_id}")
async def mark_as_witnessed(memory_id: str, user_id: str):
    """Mark that a user has witnessed/read a world memory."""
    result = await db.world_memories.update_one(
        {"memory_id": memory_id},
        {
            "$addToSet": {"witnesses": user_id}
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Memory not found")
    
    return {"success": True, "witnessed": True}


@router.post("/react/{memory_id}")
async def react_to_memory(memory_id: str, user_id: str, reaction: str):
    """Add a reaction to a world memory."""
    valid_reactions = ["awe", "fear", "joy", "sorrow", "anger", "neutral"]
    if reaction not in valid_reactions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid reaction. Valid: {valid_reactions}"
        )
    
    result = await db.world_memories.update_one(
        {"memory_id": memory_id},
        {
            "$set": {f"reactions.{user_id}": reaction}
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Memory not found")
    
    return {"success": True, "reaction": reaction}


@router.get("/search")
async def search_world_memories(
    query: str,
    limit: int = 30
):
    """Search world memories by title or description."""
    # Simple text search
    cursor = db.world_memories.find(
        {
            "$or": [
                {"title": {"$regex": query, "$options": "i"}},
                {"description": {"$regex": query, "$options": "i"}},
                {"actor_name": {"$regex": query, "$options": "i"}}
            ]
        },
        {"_id": 0}
    ).sort("created_at", -1).limit(limit)
    
    memories = await cursor.to_list(length=limit)
    
    return {
        "query": query,
        "results": memories,
        "count": len(memories)
    }


@router.get("/stats")
async def get_world_memory_stats():
    """Get statistics about world memories."""
    total = await db.world_memories.count_documents({})
    
    # By type
    pipeline = [
        {"$group": {"_id": "$memory_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    by_type = await db.world_memories.aggregate(pipeline).to_list(20)
    
    # By impact level
    global_count = await db.world_memories.count_documents({"impact_level": "global"})
    regional_count = await db.world_memories.count_documents({"impact_level": "regional"})
    local_count = await db.world_memories.count_documents({"impact_level": "local"})
    
    # By actor type
    player_count = await db.world_memories.count_documents({"actor_type": "player"})
    npc_count = await db.world_memories.count_documents({"actor_type": "npc"})
    system_count = await db.world_memories.count_documents({"actor_type": "system"})
    
    return {
        "total_memories": total,
        "by_type": {item["_id"]: item["count"] for item in by_type},
        "by_impact_level": {
            "global": global_count,
            "regional": regional_count,
            "local": local_count
        },
        "by_actor_type": {
            "player": player_count,
            "npc": npc_count,
            "system": system_count
        }
    }
