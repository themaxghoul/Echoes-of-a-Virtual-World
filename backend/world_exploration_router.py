"""
World Seed & Exploration System
================================
Deterministic world generation from a single global seed.
All terrain, resources, and structures are consistent across:
- 2D Story Mode
- 2.5D Isometric View
- 3D Unity Client

The world only changes through player/NPC actions, never randomly.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
import os
import hashlib
import math

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

router = APIRouter(prefix="/api/world", tags=["World Exploration"])

# ============ GLOBAL SEED ============
# This seed determines ALL procedural generation
# Changing this would reset the entire world
GLOBAL_SEED = "AI_VILLAGE_THE_ECHOES_SEED_2026"
SEED_HASH = int(hashlib.sha256(GLOBAL_SEED.encode()).hexdigest()[:16], 16)

# ============ World Constants ============
CHUNK_SIZE = 64  # Each chunk is 64x64 units
REGION_SIZE = 16  # Each region contains 16x16 chunks
MAX_HEIGHT = 256
SEA_LEVEL = 64

# Biome types with their characteristics
BIOMES = {
    "plains": {
        "id": "plains",
        "name": "Verdant Plains",
        "base_height": 70,
        "height_variation": 8,
        "color_2d": "#7CCD7C",
        "color_iso": "#90EE90",
        "temperature": 0.6,
        "humidity": 0.5,
        "resources": ["timber", "clay", "herbs"],
        "danger_level": 1
    },
    "forest": {
        "id": "forest",
        "name": "Ancient Forest",
        "base_height": 75,
        "height_variation": 15,
        "color_2d": "#228B22",
        "color_iso": "#2E8B57",
        "temperature": 0.5,
        "humidity": 0.7,
        "resources": ["timber", "ancient_bark", "mushrooms", "herbs"],
        "danger_level": 2
    },
    "shadow_forest": {
        "id": "shadow_forest",
        "name": "Shadow Grove",
        "base_height": 80,
        "height_variation": 20,
        "color_2d": "#1a1a2e",
        "color_iso": "#2d2d44",
        "temperature": 0.3,
        "humidity": 0.8,
        "resources": ["shadow_essence", "void_obsidian", "ancient_bark"],
        "danger_level": 4
    },
    "mountains": {
        "id": "mountains",
        "name": "Iron Peaks",
        "base_height": 120,
        "height_variation": 50,
        "color_2d": "#696969",
        "color_iso": "#808080",
        "temperature": 0.2,
        "humidity": 0.3,
        "resources": ["iron_ore", "cobblestone", "mithril"],
        "danger_level": 3
    },
    "volcanic": {
        "id": "volcanic",
        "name": "Ember Wastes",
        "base_height": 90,
        "height_variation": 30,
        "color_2d": "#8B0000",
        "color_iso": "#A52A2A",
        "temperature": 0.9,
        "humidity": 0.1,
        "resources": ["obsiteite", "charcoal", "fire_essence"],
        "danger_level": 5
    },
    "desert": {
        "id": "desert",
        "name": "Shifting Sands",
        "base_height": 68,
        "height_variation": 5,
        "color_2d": "#F4D03F",
        "color_iso": "#DAA520",
        "temperature": 0.95,
        "humidity": 0.05,
        "resources": ["sand", "glass", "sunstone"],
        "danger_level": 2
    },
    "tundra": {
        "id": "tundra",
        "name": "Frozen Expanse",
        "base_height": 72,
        "height_variation": 10,
        "color_2d": "#E0FFFF",
        "color_iso": "#B0E0E6",
        "temperature": 0.1,
        "humidity": 0.4,
        "resources": ["ice", "frost_crystal", "moonpearl"],
        "danger_level": 3
    },
    "swamp": {
        "id": "swamp",
        "name": "Murky Marshes",
        "base_height": 62,
        "height_variation": 4,
        "color_2d": "#556B2F",
        "color_iso": "#6B8E23",
        "temperature": 0.6,
        "humidity": 0.95,
        "resources": ["clay", "herbs", "demon_ichor"],
        "danger_level": 3
    },
    "crystal_caves": {
        "id": "crystal_caves",
        "name": "Echo Caverns",
        "base_height": 40,
        "height_variation": 60,
        "color_2d": "#00CED1",
        "color_iso": "#40E0D0",
        "temperature": 0.4,
        "humidity": 0.6,
        "resources": ["echo_crystal", "mana_essence", "quicksilver"],
        "danger_level": 4
    },
    "ethereal": {
        "id": "ethereal",
        "name": "Outer Realms",
        "base_height": 100,
        "height_variation": 100,
        "color_2d": "#9400D3",
        "color_iso": "#8A2BE2",
        "temperature": 0.5,
        "humidity": 0.5,
        "resources": ["chaos_essence", "ether_silk", "adamantine"],
        "danger_level": 6
    }
}

# Direction vectors for exploration
DIRECTIONS = {
    "north": (0, 1),
    "south": (0, -1),
    "east": (1, 0),
    "west": (-1, 0),
    "northeast": (1, 1),
    "northwest": (-1, 1),
    "southeast": (1, -1),
    "southwest": (-1, -1)
}

# Starting location (The Hollow Square)
ORIGIN = {"x": 0, "y": 0, "z": 70}


# ============ Seeded Random Functions ============
def seeded_hash(x: int, y: int, layer: str = "") -> float:
    """Generate a deterministic value 0-1 for coordinates."""
    data = f"{GLOBAL_SEED}:{x}:{y}:{layer}"
    hash_val = int(hashlib.sha256(data.encode()).hexdigest()[:8], 16)
    return hash_val / 0xFFFFFFFF

def seeded_noise(x: float, y: float, scale: float = 1.0) -> float:
    """Simple seeded noise function for terrain generation."""
    # Grid coordinates
    x0, y0 = int(math.floor(x / scale)), int(math.floor(y / scale))
    x1, y1 = x0 + 1, y0 + 1
    
    # Interpolation weights
    sx = (x / scale) - x0
    sy = (y / scale) - y0
    
    # Corner values
    n00 = seeded_hash(x0, y0, "noise")
    n10 = seeded_hash(x1, y0, "noise")
    n01 = seeded_hash(x0, y1, "noise")
    n11 = seeded_hash(x1, y1, "noise")
    
    # Bilinear interpolation
    nx0 = n00 * (1 - sx) + n10 * sx
    nx1 = n01 * (1 - sx) + n11 * sx
    return nx0 * (1 - sy) + nx1 * sy

def octave_noise(x: float, y: float, octaves: int = 4, persistence: float = 0.5) -> float:
    """Multi-octave noise for more natural terrain."""
    total = 0.0
    frequency = 1.0
    amplitude = 1.0
    max_value = 0.0
    
    for _ in range(octaves):
        total += seeded_noise(x * frequency, y * frequency, 32.0) * amplitude
        max_value += amplitude
        amplitude *= persistence
        frequency *= 2.0
    
    return total / max_value


# ============ Terrain Generation ============
def get_biome_at(x: int, y: int) -> Dict:
    """Determine biome at world coordinates using seeded generation."""
    # Temperature and humidity from noise
    temp = octave_noise(x, y, 3, 0.5)
    humidity = octave_noise(x + 10000, y + 10000, 3, 0.5)
    
    # Special zones near origin
    dist_from_origin = math.sqrt(x*x + y*y)
    
    # The village area (origin) is always plains
    if dist_from_origin < 5:
        return BIOMES["plains"]
    
    # Shadow Grove to the northeast
    if x > 10 and y > 10 and seeded_hash(x // 10, y // 10, "shadow") > 0.7:
        return BIOMES["shadow_forest"]
    
    # Volcanic region to the south
    if y < -20 and seeded_hash(x // 15, y // 15, "volcanic") > 0.6:
        return BIOMES["volcanic"]
    
    # Ethereal zones at far distances
    if dist_from_origin > 100 and seeded_hash(x // 20, y // 20, "ethereal") > 0.85:
        return BIOMES["ethereal"]
    
    # Crystal caves underground (shown on surface as cave entrances)
    if seeded_hash(x, y, "caves") > 0.95:
        return BIOMES["crystal_caves"]
    
    # Default biome selection based on temp/humidity
    if temp < 0.25:
        return BIOMES["tundra"] if humidity < 0.5 else BIOMES["mountains"]
    elif temp < 0.5:
        return BIOMES["forest"] if humidity > 0.6 else BIOMES["plains"]
    elif temp < 0.75:
        if humidity > 0.8:
            return BIOMES["swamp"]
        elif humidity > 0.4:
            return BIOMES["forest"]
        else:
            return BIOMES["plains"]
    else:
        return BIOMES["desert"] if humidity < 0.3 else BIOMES["plains"]

def get_height_at(x: int, y: int) -> int:
    """Calculate terrain height at coordinates."""
    biome = get_biome_at(x, y)
    base = biome["base_height"]
    variation = biome["height_variation"]
    
    # Use multiple noise octaves for natural terrain
    noise_val = octave_noise(x, y, 4, 0.5)
    
    height = base + int((noise_val - 0.5) * 2 * variation)
    return max(1, min(MAX_HEIGHT - 1, height))

def get_tile_at(x: int, y: int) -> Dict:
    """Get complete tile data for coordinates."""
    biome = get_biome_at(x, y)
    height = get_height_at(x, y)
    
    # Determine tile features
    feature = None
    feature_seed = seeded_hash(x, y, "feature")
    
    if biome["id"] == "forest" and feature_seed > 0.7:
        feature = "tree"
    elif biome["id"] == "shadow_forest" and feature_seed > 0.6:
        feature = "twisted_tree" if feature_seed > 0.8 else "shadow_pool"
    elif biome["id"] == "mountains" and feature_seed > 0.85:
        feature = "ore_vein"
    elif biome["id"] == "crystal_caves" and feature_seed > 0.5:
        feature = "crystal_formation"
    elif biome["id"] == "volcanic" and feature_seed > 0.8:
        feature = "lava_pool"
    
    # Check for resource nodes
    resource = None
    if feature_seed > 0.9 and biome.get("resources"):
        import secrets
        resource_idx = int(seeded_hash(x, y, "resource_idx") * len(biome["resources"]))
        resource = biome["resources"][resource_idx % len(biome["resources"])]
    
    return {
        "x": x,
        "y": y,
        "z": height,
        "biome": biome["id"],
        "biome_name": biome["name"],
        "color_2d": biome["color_2d"],
        "color_iso": biome["color_iso"],
        "danger_level": biome["danger_level"],
        "feature": feature,
        "resource": resource,
        "is_passable": feature not in ["lava_pool", "shadow_pool"],
        "exploration_required": biome["danger_level"] >= 4
    }

def get_chunk(chunk_x: int, chunk_y: int) -> Dict:
    """Generate a full chunk of terrain data."""
    tiles = []
    base_x = chunk_x * CHUNK_SIZE
    base_y = chunk_y * CHUNK_SIZE
    
    for dy in range(CHUNK_SIZE):
        row = []
        for dx in range(CHUNK_SIZE):
            tile = get_tile_at(base_x + dx, base_y + dy)
            row.append(tile)
        tiles.append(row)
    
    # Calculate chunk metadata
    biome_counts = {}
    avg_height = 0
    total_tiles = CHUNK_SIZE * CHUNK_SIZE
    
    for row in tiles:
        for tile in row:
            biome_counts[tile["biome"]] = biome_counts.get(tile["biome"], 0) + 1
            avg_height += tile["z"]
    
    dominant_biome = max(biome_counts, key=biome_counts.get)
    
    return {
        "chunk_x": chunk_x,
        "chunk_y": chunk_y,
        "world_x": base_x,
        "world_y": base_y,
        "size": CHUNK_SIZE,
        "dominant_biome": dominant_biome,
        "biome_name": BIOMES[dominant_biome]["name"],
        "average_height": avg_height // total_tiles,
        "tiles": tiles
    }


# ============ Pydantic Models ============
class ExploreRequest(BaseModel):
    user_id: str
    direction: str = Field(..., description="Direction to explore: north, south, east, west, etc.")
    distance: int = Field(default=1, ge=1, le=10, description="How many tiles to move")

class TeleportRequest(BaseModel):
    user_id: str
    x: int
    y: int

class ClaimLandRequest(BaseModel):
    user_id: str
    x: int
    y: int
    name: Optional[str] = None


# ============ API Endpoints ============

@router.get("/seed")
async def get_world_seed():
    """Get the global world seed info (not the actual seed for security)."""
    return {
        "seed_id": hashlib.sha256(GLOBAL_SEED.encode()).hexdigest()[:16],
        "seed_name": "The Echoes",
        "version": "1.0",
        "chunk_size": CHUNK_SIZE,
        "region_size": REGION_SIZE,
        "origin": ORIGIN,
        "biome_count": len(BIOMES),
        "description": "A single deterministic world shared by all players across all game modes."
    }

@router.get("/biomes")
async def get_all_biomes():
    """Get all biome definitions for client rendering."""
    return {
        "biomes": BIOMES,
        "total": len(BIOMES)
    }

@router.get("/tile/{x}/{y}")
async def get_tile(x: int, y: int):
    """Get tile data at specific world coordinates."""
    tile = get_tile_at(x, y)
    
    # Check for player modifications
    modification = await db.world_modifications.find_one(
        {"x": x, "y": y},
        {"_id": 0}
    )
    
    if modification:
        tile["modified"] = True
        tile["modification"] = modification
        if modification.get("structure"):
            tile["structure"] = modification["structure"]
        if modification.get("owner_id"):
            tile["owner_id"] = modification["owner_id"]
            tile["owner_name"] = modification.get("owner_name")
    
    return tile

@router.get("/chunk/{chunk_x}/{chunk_y}")
async def get_chunk_data(chunk_x: int, chunk_y: int):
    """Get a full chunk of terrain for the client."""
    chunk = get_chunk(chunk_x, chunk_y)
    
    # Get modifications within this chunk
    base_x = chunk_x * CHUNK_SIZE
    base_y = chunk_y * CHUNK_SIZE
    
    modifications = await db.world_modifications.find({
        "x": {"$gte": base_x, "$lt": base_x + CHUNK_SIZE},
        "y": {"$gte": base_y, "$lt": base_y + CHUNK_SIZE}
    }, {"_id": 0}).to_list(length=None)
    
    chunk["modifications"] = modifications
    chunk["modification_count"] = len(modifications)
    
    return chunk

@router.get("/area/{x}/{y}/{radius}")
async def get_area(x: int, y: int, radius: int = 5):
    """Get tiles in a radius around a point (for local exploration view)."""
    if radius > 20:
        radius = 20
    
    tiles = []
    for dy in range(-radius, radius + 1):
        row = []
        for dx in range(-radius, radius + 1):
            tile = get_tile_at(x + dx, y + dy)
            row.append(tile)
        tiles.append(row)
    
    return {
        "center": {"x": x, "y": y},
        "radius": radius,
        "tiles": tiles,
        "size": radius * 2 + 1
    }

@router.get("/player/{user_id}/position")
async def get_player_position(user_id: str):
    """Get a player's current world position."""
    position = await db.player_positions.find_one(
        {"user_id": user_id},
        {"_id": 0}
    )
    
    if not position:
        # New player starts at origin
        position = {
            "user_id": user_id,
            "x": ORIGIN["x"],
            "y": ORIGIN["y"],
            "z": ORIGIN["z"],
            "facing": "north",
            "discovered_tiles": 1,
            "last_moved": datetime.now(timezone.utc).isoformat()
        }
        await db.player_positions.insert_one(position)
        # Remove _id added by MongoDB
        position.pop("_id", None)
    
    # Add current tile info
    tile = get_tile_at(position["x"], position["y"])
    position["current_tile"] = tile
    
    return position

@router.post("/explore")
async def explore_direction(request: ExploreRequest):
    """Move player in a direction, discovering new tiles."""
    if request.direction not in DIRECTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid direction. Valid: {list(DIRECTIONS.keys())}"
        )
    
    # Get current position
    position = await db.player_positions.find_one({"user_id": request.user_id})
    if not position:
        position = {"x": ORIGIN["x"], "y": ORIGIN["y"], "z": ORIGIN["z"]}
    
    dx, dy = DIRECTIONS[request.direction]
    new_x = position["x"] + (dx * request.distance)
    new_y = position["y"] + (dy * request.distance)
    
    # Get destination tile
    dest_tile = get_tile_at(new_x, new_y)
    
    # Check if passable
    if not dest_tile["is_passable"]:
        return {
            "success": False,
            "message": f"Cannot pass through {dest_tile.get('feature', 'obstacle')}",
            "blocked_by": dest_tile.get("feature"),
            "position": {"x": position["x"], "y": position["y"], "z": position["z"]}
        }
    
    # Update position
    new_z = dest_tile["z"]
    await db.player_positions.update_one(
        {"user_id": request.user_id},
        {
            "$set": {
                "x": new_x,
                "y": new_y,
                "z": new_z,
                "facing": request.direction,
                "last_moved": datetime.now(timezone.utc).isoformat()
            },
            "$inc": {"discovered_tiles": 1}
        },
        upsert=True
    )
    
    # Record discovery
    await db.tile_discoveries.update_one(
        {"user_id": request.user_id, "x": new_x, "y": new_y},
        {
            "$setOnInsert": {
                "user_id": request.user_id,
                "x": new_x,
                "y": new_y,
                "discovered_at": datetime.now(timezone.utc).isoformat(),
                "biome": dest_tile["biome"]
            }
        },
        upsert=True
    )
    
    # Get surrounding tiles for exploration view
    surroundings = []
    for dir_name, (ddx, ddy) in DIRECTIONS.items():
        adj_tile = get_tile_at(new_x + ddx, new_y + ddy)
        surroundings.append({
            "direction": dir_name,
            "tile": adj_tile
        })
    
    return {
        "success": True,
        "moved": {
            "from": {"x": position["x"], "y": position["y"]},
            "to": {"x": new_x, "y": new_y, "z": new_z},
            "direction": request.direction,
            "distance": request.distance
        },
        "current_tile": dest_tile,
        "surroundings": surroundings,
        "message": f"You travel {request.direction} into {dest_tile['biome_name']}."
    }

@router.post("/teleport")
async def teleport_player(request: TeleportRequest):
    """Teleport player to specific coordinates (if discovered or admin)."""
    # Check if player has discovered this tile
    discovery = await db.tile_discoveries.find_one({
        "user_id": request.user_id,
        "x": request.x,
        "y": request.y
    })
    
    # Check if admin
    user = await db.user_profiles.find_one({"id": request.user_id})
    is_admin = user and user.get("permission_level") == "sirix_1"
    
    if not discovery and not is_admin:
        raise HTTPException(
            status_code=403,
            detail="You can only teleport to previously discovered locations"
        )
    
    dest_tile = get_tile_at(request.x, request.y)
    
    await db.player_positions.update_one(
        {"user_id": request.user_id},
        {
            "$set": {
                "x": request.x,
                "y": request.y,
                "z": dest_tile["z"],
                "last_moved": datetime.now(timezone.utc).isoformat()
            }
        },
        upsert=True
    )
    
    return {
        "success": True,
        "teleported_to": {"x": request.x, "y": request.y, "z": dest_tile["z"]},
        "current_tile": dest_tile
    }

@router.get("/player/{user_id}/discoveries")
async def get_player_discoveries(user_id: str, limit: int = 100):
    """Get tiles discovered by a player."""
    cursor = db.tile_discoveries.find(
        {"user_id": user_id},
        {"_id": 0}
    ).sort("discovered_at", -1).limit(limit)
    
    discoveries = await cursor.to_list(length=limit)
    
    # Count by biome
    biome_counts = {}
    for d in discoveries:
        biome = d.get("biome", "unknown")
        biome_counts[biome] = biome_counts.get(biome, 0) + 1
    
    return {
        "user_id": user_id,
        "total_discovered": len(discoveries),
        "discoveries": discoveries,
        "biome_breakdown": biome_counts
    }

@router.post("/claim")
async def claim_land(request: ClaimLandRequest):
    """Claim a tile of land for building."""
    tile = get_tile_at(request.x, request.y)
    
    # Check if already claimed
    existing = await db.world_modifications.find_one({
        "x": request.x,
        "y": request.y,
        "owner_id": {"$exists": True}
    })
    
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"This land is already claimed by {existing.get('owner_name', 'another player')}"
        )
    
    # Check if player discovered this tile
    discovery = await db.tile_discoveries.find_one({
        "user_id": request.user_id,
        "x": request.x,
        "y": request.y
    })
    
    if not discovery:
        raise HTTPException(
            status_code=403,
            detail="You must discover land before claiming it"
        )
    
    # Get user info
    user = await db.user_profiles.find_one({"id": request.user_id})
    
    # Record claim
    claim = {
        "x": request.x,
        "y": request.y,
        "owner_id": request.user_id,
        "owner_name": user.get("display_name") if user else request.user_id,
        "claim_name": request.name or f"Plot ({request.x}, {request.y})",
        "claimed_at": datetime.now(timezone.utc).isoformat(),
        "biome": tile["biome"],
        "structure": None
    }
    
    await db.world_modifications.update_one(
        {"x": request.x, "y": request.y},
        {"$set": claim},
        upsert=True
    )
    
    return {
        "success": True,
        "claim": claim,
        "message": f"You have claimed this {tile['biome_name']} tile!"
    }

@router.get("/claims/{user_id}")
async def get_user_claims(user_id: str):
    """Get all land claims for a user."""
    claims = await db.world_modifications.find(
        {"owner_id": user_id},
        {"_id": 0}
    ).to_list(length=100)
    
    return {
        "user_id": user_id,
        "total_claims": len(claims),
        "claims": claims
    }

@router.post("/modify")
async def modify_tile(
    user_id: str,
    x: int,
    y: int,
    modification_type: str,
    data: Dict[str, Any]
):
    """Apply a modification to a tile (building, terraforming, etc.)."""
    # Check ownership
    existing = await db.world_modifications.find_one({"x": x, "y": y})
    
    if existing and existing.get("owner_id") != user_id:
        # Check if admin
        user = await db.user_profiles.find_one({"id": user_id})
        if not user or user.get("permission_level") != "sirix_1":
            raise HTTPException(
                status_code=403,
                detail="You do not own this land"
            )
    
    # Record modification
    modification = {
        "x": x,
        "y": y,
        "modification_type": modification_type,
        "data": data,
        "modified_by": user_id,
        "modified_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.world_modifications.update_one(
        {"x": x, "y": y},
        {"$set": modification},
        upsert=True
    )
    
    # Record in world history (for NPC memory system)
    await db.world_events.insert_one({
        "event_type": "tile_modification",
        "x": x,
        "y": y,
        "modification_type": modification_type,
        "actor_id": user_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "success": True,
        "modification": modification
    }

@router.get("/stats")
async def get_world_stats():
    """Get global world statistics."""
    total_discoveries = await db.tile_discoveries.count_documents({})
    total_claims = await db.world_modifications.count_documents({"owner_id": {"$exists": True}})
    total_modifications = await db.world_modifications.count_documents({})
    
    # Most explored biomes
    pipeline = [
        {"$group": {"_id": "$biome", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]
    top_biomes = await db.tile_discoveries.aggregate(pipeline).to_list(5)
    
    return {
        "world_seed_id": hashlib.sha256(GLOBAL_SEED.encode()).hexdigest()[:16],
        "total_tile_discoveries": total_discoveries,
        "total_land_claims": total_claims,
        "total_modifications": total_modifications,
        "top_explored_biomes": [
            {"biome": b["_id"], "discoveries": b["count"]}
            for b in top_biomes
        ],
        "chunk_size": CHUNK_SIZE,
        "biome_count": len(BIOMES)
    }
