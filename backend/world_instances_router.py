# World Instances Router - Private Worlds & Shared Realms
# Manages Sirix-1 private world and shared story world instances

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone
import uuid
import logging

world_instances_router = APIRouter(prefix="/worlds", tags=["worlds"])

logger = logging.getLogger(__name__)

# ============ World Definitions ============

WORLD_TYPES = {
    "private": {
        "name": "Private Realm",
        "description": "A personal world instance only accessible by its owner",
        "max_npcs": 10,
        "allow_visitors": False,
        "persistent": True
    },
    "shared": {
        "name": "Shared Realm",
        "description": "A world instance accessible by multiple players and NPCs",
        "max_npcs": 50,
        "allow_visitors": True,
        "persistent": True
    },
    "story": {
        "name": "Story Realm",
        "description": "The main story world with original characters",
        "max_npcs": 100,
        "allow_visitors": True,
        "persistent": True
    },
    "instance": {
        "name": "Instanced Realm",
        "description": "Temporary world for specific events or quests",
        "max_npcs": 20,
        "allow_visitors": True,
        "persistent": False
    }
}

# Original Story Characters (NPCs that exist in the main story world)
STORY_CHARACTERS = [
    {"id": "elder_morvain", "name": "Elder Morvain", "role": "Village Elder", "location": "village_square"},
    {"id": "lyra_wanderer", "name": "Lyra the Wanderer", "role": "Explorer", "location": "village_square"},
    {"id": "oracle_veythra", "name": "Oracle Veythra", "role": "Seer", "location": "oracle_sanctum"},
    {"id": "kael_ironbrand", "name": "Kael Ironbrand", "role": "Blacksmith", "location": "the_forge"},
    {"id": "archivist_nyx", "name": "Archivist Nyx", "role": "Lorekeeper", "location": "ancient_library"},
    {"id": "innkeeper_mara", "name": "Innkeeper Mara", "role": "Tavern Owner", "location": "wanderers_rest"},
    {"id": "grove_keeper", "name": "The Grove Keeper", "role": "Forest Guardian", "location": "shadow_grove"},
    {"id": "sentinel_theron", "name": "Sentinel Theron", "role": "Watchtower Guard", "location": "watchtower"},
]

# ============ Models ============

class WorldInstance(BaseModel):
    world_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    world_type: str  # private, shared, story, instance
    name: str
    owner_id: Optional[str] = None  # For private worlds
    seed: int = Field(default_factory=lambda: __import__('random').randint(1, 999999999))
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_modified: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    allowed_users: List[str] = Field(default_factory=list)  # Empty = public (for non-private)
    banned_users: List[str] = Field(default_factory=list)
    npcs: List[str] = Field(default_factory=list)
    structures: List[Dict[str, Any]] = Field(default_factory=list)
    terrain_modifications: List[Dict[str, Any]] = Field(default_factory=list)
    events: List[Dict[str, Any]] = Field(default_factory=list)
    settings: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True

class CreateWorldRequest(BaseModel):
    world_type: str
    name: str
    owner_id: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None

class JoinWorldRequest(BaseModel):
    user_id: str
    character_id: str

class WorldModification(BaseModel):
    modifier_id: str
    modifier_type: str = "player"  # player or npc
    modification_type: str  # terrain, structure, event
    data: Dict[str, Any]

# ============ Database Helper ============

def get_db():
    from server import db
    return db

# ============ Sirix-1 Private World ============

SIRIX_WORLD_ID = "sirix-1-private-realm"

async def ensure_sirix_private_world(db):
    """Ensure Sirix-1's private world exists"""
    existing = await db.world_instances.find_one({"world_id": SIRIX_WORLD_ID}, {"_id": 0})
    
    if not existing:
        sirix_world = WorldInstance(
            world_id=SIRIX_WORLD_ID,
            world_type="private",
            name="Sirix-1's Private Realm",
            owner_id="sirix_1",
            seed=1,  # Fixed seed for consistency
            allowed_users=["sirix_1"],
            settings={
                "exclusive": True,
                "no_visitors": True,
                "owner_only": True,
                "description": "A realm closed off to all but Sirix-1"
            }
        )
        world_dict = sirix_world.dict()
        await db.world_instances.insert_one(world_dict)
        logger.info("Created Sirix-1 private world")
        # Remove _id after insert
        world_dict.pop("_id", None)
        return world_dict
    
    return existing

async def ensure_story_world(db):
    """Ensure the main story world exists with original characters"""
    story_world_id = "main-story-realm"
    existing = await db.world_instances.find_one({"world_id": story_world_id}, {"_id": 0})
    
    if not existing:
        story_world = WorldInstance(
            world_id=story_world_id,
            world_type="story",
            name="The Echoes - Story Realm",
            seed=42,  # Fixed seed for consistency
            npcs=[char["id"] for char in STORY_CHARACTERS],
            settings={
                "main_story": True,
                "description": "The original story world where players can meet the founding characters"
            }
        )
        world_dict = story_world.dict()
        await db.world_instances.insert_one(world_dict)
        logger.info("Created main story world")
        # Remove _id after insert
        world_dict.pop("_id", None)
        return world_dict
    
    return existing

# ============ Endpoints ============

@world_instances_router.get("/types")
async def get_world_types():
    """Get available world types"""
    return {
        "types": WORLD_TYPES,
        "story_characters": STORY_CHARACTERS
    }

@world_instances_router.post("/create")
async def create_world(data: CreateWorldRequest):
    """Create a new world instance"""
    db = get_db()
    
    if data.world_type not in WORLD_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid world type: {data.world_type}")
    
    # Private worlds require owner
    if data.world_type == "private" and not data.owner_id:
        raise HTTPException(status_code=400, detail="Private worlds require an owner_id")
    
    world = WorldInstance(
        world_type=data.world_type,
        name=data.name,
        owner_id=data.owner_id,
        allowed_users=[data.owner_id] if data.world_type == "private" and data.owner_id else [],
        settings=data.settings or {}
    )
    
    await db.world_instances.insert_one(world.dict())
    
    return {
        "created": True,
        "world_id": world.world_id,
        "world": world.dict()
    }

@world_instances_router.get("/list")
async def list_worlds(world_type: Optional[str] = None, user_id: Optional[str] = None):
    """List available worlds"""
    db = get_db()
    
    # Ensure special worlds exist
    await ensure_sirix_private_world(db)
    await ensure_story_world(db)
    
    query = {"is_active": True}
    if world_type:
        query["world_type"] = world_type
    
    worlds = await db.world_instances.find(query, {"_id": 0}).to_list(100)
    
    # Filter based on access if user_id provided
    if user_id:
        accessible = []
        for world in worlds:
            # Private worlds - only owner
            if world.get("world_type") == "private":
                if world.get("owner_id") == user_id or user_id in world.get("allowed_users", []):
                    accessible.append(world)
            # Banned check
            elif user_id not in world.get("banned_users", []):
                accessible.append(world)
        worlds = accessible
    
    return {"worlds": worlds, "count": len(worlds)}

@world_instances_router.get("/{world_id}")
async def get_world(world_id: str, user_id: Optional[str] = None):
    """Get world details"""
    db = get_db()
    
    world = await db.world_instances.find_one({"world_id": world_id}, {"_id": 0})
    
    if not world:
        raise HTTPException(status_code=404, detail="World not found")
    
    # Access check
    if world.get("world_type") == "private":
        if user_id and user_id != world.get("owner_id") and user_id not in world.get("allowed_users", []):
            raise HTTPException(status_code=403, detail="Access denied to private world")
    
    # Get NPCs in this world
    npc_ids = world.get("npcs", [])
    npcs = []
    if npc_ids:
        npcs = await db.ai_villagers.find(
            {"villager_id": {"$in": npc_ids}},
            {"_id": 0}
        ).to_list(100)
    
    # Get structures
    structures = await db.world_structures.find(
        {"world_id": world_id},
        {"_id": 0}
    ).to_list(100)
    
    return {
        "world": world,
        "npcs": npcs,
        "structures": structures,
        "can_modify": user_id == world.get("owner_id") if world.get("world_type") == "private" else True
    }

@world_instances_router.post("/{world_id}/join")
async def join_world(world_id: str, data: JoinWorldRequest):
    """Join a world instance"""
    db = get_db()
    
    world = await db.world_instances.find_one({"world_id": world_id})
    
    if not world:
        raise HTTPException(status_code=404, detail="World not found")
    
    # Access check
    if world.get("world_type") == "private":
        if data.user_id != world.get("owner_id") and data.user_id not in world.get("allowed_users", []):
            raise HTTPException(status_code=403, detail="Access denied to private world")
    
    if data.user_id in world.get("banned_users", []):
        raise HTTPException(status_code=403, detail="You are banned from this world")
    
    # Track player in world
    await db.world_players.update_one(
        {"world_id": world_id, "user_id": data.user_id},
        {
            "$set": {
                "character_id": data.character_id,
                "joined_at": datetime.now(timezone.utc).isoformat(),
                "is_online": True
            }
        },
        upsert=True
    )
    
    return {
        "joined": True,
        "world_id": world_id,
        "world_name": world.get("name"),
        "seed": world.get("seed")
    }

@world_instances_router.post("/{world_id}/leave")
async def leave_world(world_id: str, user_id: str):
    """Leave a world instance"""
    db = get_db()
    
    await db.world_players.update_one(
        {"world_id": world_id, "user_id": user_id},
        {"$set": {"is_online": False, "left_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"left": True, "world_id": world_id}

@world_instances_router.get("/{world_id}/players")
async def get_world_players(world_id: str, online_only: bool = False):
    """Get players in a world"""
    db = get_db()
    
    query = {"world_id": world_id}
    if online_only:
        query["is_online"] = True
    
    players = await db.world_players.find(query, {"_id": 0}).to_list(100)
    
    return {"players": players, "count": len(players)}

@world_instances_router.post("/{world_id}/modify")
async def modify_world(world_id: str, mod: WorldModification):
    """Apply a modification to the world (terrain, structure, event)"""
    db = get_db()
    
    world = await db.world_instances.find_one({"world_id": world_id})
    
    if not world:
        raise HTTPException(status_code=404, detail="World not found")
    
    # Check permissions
    if world.get("world_type") == "private" and mod.modifier_id != world.get("owner_id"):
        raise HTTPException(status_code=403, detail="Only owner can modify private world")
    
    modification = {
        "mod_id": str(uuid.uuid4()),
        "modifier_id": mod.modifier_id,
        "modifier_type": mod.modifier_type,
        "type": mod.modification_type,
        "data": mod.data,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # Apply modification based on type
    if mod.modification_type == "terrain":
        await db.world_instances.update_one(
            {"world_id": world_id},
            {
                "$push": {"terrain_modifications": modification},
                "$set": {"last_modified": datetime.now(timezone.utc).isoformat()}
            }
        )
    elif mod.modification_type == "structure":
        # Add to world_structures collection
        structure = {
            "structure_id": str(uuid.uuid4()),
            "world_id": world_id,
            **mod.data,
            "builder_id": mod.modifier_id,
            "builder_type": mod.modifier_type,
            "built_at": datetime.now(timezone.utc).isoformat()
        }
        await db.world_structures.insert_one(structure)
        await db.world_instances.update_one(
            {"world_id": world_id},
            {"$push": {"structures": structure}}
        )
    elif mod.modification_type == "event":
        await db.world_instances.update_one(
            {"world_id": world_id},
            {"$push": {"events": modification}}
        )
    
    return {
        "modified": True,
        "world_id": world_id,
        "modification": modification
    }

@world_instances_router.get("/sirix-1/realm")
async def get_sirix_private_realm(user_id: str):
    """Get Sirix-1's private realm (only accessible by sirix_1)"""
    db = get_db()
    
    if user_id != "sirix_1":
        raise HTTPException(status_code=403, detail="This realm is closed to all but Sirix-1")
    
    world = await ensure_sirix_private_world(db)
    
    return {
        "world": world,
        "exclusive": True,
        "message": "Welcome to your private realm, Sirix-1"
    }

@world_instances_router.get("/story/main")
async def get_main_story_world():
    """Get the main story world with original characters"""
    db = get_db()
    
    world = await ensure_story_world(db)
    
    return {
        "world": world,
        "original_characters": STORY_CHARACTERS,
        "description": "The founding realm of The Echoes where the original story unfolds"
    }

@world_instances_router.post("/{world_id}/npc/add")
async def add_npc_to_world(world_id: str, npc_id: str, owner_id: str):
    """Add an NPC to a world"""
    db = get_db()
    
    world = await db.world_instances.find_one({"world_id": world_id})
    
    if not world:
        raise HTTPException(status_code=404, detail="World not found")
    
    if world.get("world_type") == "private" and owner_id != world.get("owner_id"):
        raise HTTPException(status_code=403, detail="Only owner can add NPCs to private world")
    
    # Check NPC limit
    world_type_data = WORLD_TYPES.get(world.get("world_type"), {})
    max_npcs = world_type_data.get("max_npcs", 10)
    
    if len(world.get("npcs", [])) >= max_npcs:
        raise HTTPException(status_code=400, detail=f"World has reached NPC limit ({max_npcs})")
    
    await db.world_instances.update_one(
        {"world_id": world_id},
        {"$addToSet": {"npcs": npc_id}}
    )
    
    return {"added": True, "world_id": world_id, "npc_id": npc_id}

@world_instances_router.get("/{world_id}/seed")
async def get_world_seed(world_id: str):
    """Get the consistent seed for a world (for 3D generation)"""
    db = get_db()
    
    world = await db.world_instances.find_one({"world_id": world_id}, {"_id": 0, "seed": 1, "name": 1})
    
    if not world:
        raise HTTPException(status_code=404, detail="World not found")
    
    return {
        "world_id": world_id,
        "seed": world.get("seed"),
        "name": world.get("name")
    }
