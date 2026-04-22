# World Map Router - Top-down stylized map with consistent seed
# Multiplayer 3D environment altered only by player/AI interaction

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime, timezone
import uuid
import logging
import hashlib
import random

world_map_router = APIRouter(prefix="/world-map", tags=["world-map"])

logger = logging.getLogger(__name__)

# ============ Map Configuration ============

# Map regions based on consistent seed
MAP_REGIONS = {
    "village_square": {
        "name": "The Hollow Square",
        "position": (50, 50),  # Center of map
        "size": (20, 20),
        "terrain": "cobblestone",
        "color": "#8B7355",
        "connectedTo": ["oracle_sanctum", "the_forge", "ancient_library", "wanderers_rest"]
    },
    "oracle_sanctum": {
        "name": "Oracle's Sanctum",
        "position": (30, 30),
        "size": (15, 15),
        "terrain": "mystical_stone",
        "color": "#8B5CF6",
        "connectedTo": ["village_square", "shadow_grove"]
    },
    "the_forge": {
        "name": "The Ember Forge",
        "position": (70, 40),
        "size": (18, 14),
        "terrain": "volcanic",
        "color": "#F59E0B",
        "connectedTo": ["village_square", "watchtower"]
    },
    "ancient_library": {
        "name": "Ancient Library",
        "position": (40, 70),
        "size": (16, 16),
        "terrain": "marble",
        "color": "#6366F1",
        "connectedTo": ["village_square", "outer_realms"]
    },
    "wanderers_rest": {
        "name": "Wanderer's Rest",
        "position": (60, 65),
        "size": (14, 12),
        "terrain": "forest_clearing",
        "color": "#10B981",
        "connectedTo": ["village_square", "shadow_grove"]
    },
    "shadow_grove": {
        "name": "Shadow Grove",
        "position": (20, 60),
        "size": (22, 18),
        "terrain": "dark_forest",
        "color": "#374151",
        "connectedTo": ["oracle_sanctum", "wanderers_rest", "outer_realms"]
    },
    "watchtower": {
        "name": "The Watchtower",
        "position": (85, 25),
        "size": (10, 10),
        "terrain": "highland",
        "color": "#78716C",
        "connectedTo": ["the_forge", "outer_realms"]
    },
    "outer_realms": {
        "name": "Outer Realms",
        "position": (15, 85),
        "size": (25, 20),
        "terrain": "ethereal",
        "color": "#EC4899",
        "connectedTo": ["ancient_library", "shadow_grove", "watchtower"]
    }
}

# Terrain types for procedural generation
TERRAIN_TYPES = {
    "grass": {"color": "#4ADE80", "traversable": True, "speed_mod": 1.0},
    "forest": {"color": "#166534", "traversable": True, "speed_mod": 0.7},
    "dark_forest": {"color": "#1E3A2F", "traversable": True, "speed_mod": 0.5},
    "water": {"color": "#3B82F6", "traversable": False, "speed_mod": 0.0},
    "shallow_water": {"color": "#60A5FA", "traversable": True, "speed_mod": 0.4},
    "mountain": {"color": "#78716C", "traversable": False, "speed_mod": 0.0},
    "highland": {"color": "#A1A1AA", "traversable": True, "speed_mod": 0.8},
    "cobblestone": {"color": "#57534E", "traversable": True, "speed_mod": 1.2},
    "marble": {"color": "#E5E7EB", "traversable": True, "speed_mod": 1.1},
    "volcanic": {"color": "#B91C1C", "traversable": True, "speed_mod": 0.6},
    "mystical_stone": {"color": "#7C3AED", "traversable": True, "speed_mod": 1.0},
    "forest_clearing": {"color": "#6EE7B7", "traversable": True, "speed_mod": 1.0},
    "ethereal": {"color": "#F9A8D4", "traversable": True, "speed_mod": 1.5},
    "sand": {"color": "#FDE68A", "traversable": True, "speed_mod": 0.8},
    "snow": {"color": "#F1F5F9", "traversable": True, "speed_mod": 0.6},
}

# ============ Models ============

class WorldMap(BaseModel):
    map_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    world_id: str
    seed: int
    width: int = 100
    height: int = 100
    regions: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    terrain_grid: Dict[str, str] = Field(default_factory=dict)  # "x,y": terrain_type
    roads: List[Dict[str, Any]] = Field(default_factory=list)
    points_of_interest: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_modified: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class MapEntity(BaseModel):
    entity_id: str
    entity_type: str  # player, npc, creature
    entity_name: str
    position: Tuple[float, float]
    region_id: str
    facing: float = 0.0  # Direction in degrees
    status: str = "idle"  # idle, moving, interacting, combat
    visible: bool = True
    last_update: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class MapModification(BaseModel):
    mod_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    world_id: str
    modifier_id: str
    modifier_type: str
    mod_type: str  # terrain, road, poi, structure
    position: Tuple[int, int]
    data: Dict[str, Any]
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    reverted: bool = False

class UpdatePositionRequest(BaseModel):
    entity_id: str
    entity_type: str
    position: Tuple[float, float]
    region_id: str
    facing: Optional[float] = None

class ModifyTerrainRequest(BaseModel):
    position: Tuple[int, int]
    terrain_type: str
    radius: int = 1

# ============ Database Helper ============

def get_db():
    from server import db
    return db

# ============ Helper Functions ============

def generate_terrain_grid(seed: int, width: int, height: int) -> Dict[str, str]:
    """Generate terrain using seeded random for consistency"""
    rng = random.Random(seed)
    grid = {}
    
    # Base terrain is grass
    for x in range(width):
        for y in range(height):
            # Use noise-like generation
            noise_val = rng.random()
            
            if noise_val < 0.05:
                terrain = "water"
            elif noise_val < 0.15:
                terrain = "forest"
            elif noise_val < 0.20:
                terrain = "mountain"
            elif noise_val < 0.25:
                terrain = "sand"
            else:
                terrain = "grass"
            
            grid[f"{x},{y}"] = terrain
    
    # Apply region-specific terrain
    for region_id, region_data in MAP_REGIONS.items():
        rx, ry = region_data["position"]
        rw, rh = region_data["size"]
        region_terrain = region_data["terrain"]
        
        for x in range(max(0, rx), min(width, rx + rw)):
            for y in range(max(0, ry), min(height, ry + rh)):
                grid[f"{x},{y}"] = region_terrain
    
    return grid

def generate_roads(regions: Dict) -> List[Dict]:
    """Generate roads connecting regions"""
    roads = []
    
    for region_id, region_data in regions.items():
        start_pos = region_data["position"]
        
        for connected_id in region_data.get("connectedTo", []):
            if connected_id in regions:
                end_region = regions[connected_id]
                end_pos = end_region["position"]
                
                # Only add road once (alphabetical order)
                if region_id < connected_id:
                    roads.append({
                        "road_id": f"road_{region_id}_{connected_id}",
                        "from_region": region_id,
                        "to_region": connected_id,
                        "from_pos": start_pos,
                        "to_pos": end_pos,
                        "width": 2,
                        "type": "cobblestone"
                    })
    
    return roads

# ============ Endpoints ============

@world_map_router.get("/config")
async def get_map_config():
    """Get map configuration constants"""
    return {
        "regions": MAP_REGIONS,
        "terrain_types": TERRAIN_TYPES,
        "default_size": {"width": 100, "height": 100}
    }

@world_map_router.get("/{world_id}")
async def get_world_map(world_id: str):
    """Get or generate the world map"""
    db = get_db()
    
    # Get world seed
    world = await db.world_instances.find_one({"world_id": world_id})
    if not world:
        raise HTTPException(status_code=404, detail="World not found")
    
    seed = world.get("seed", 42)
    
    # Check for existing map
    world_map = await db.world_maps.find_one({"world_id": world_id}, {"_id": 0})
    
    if not world_map:
        # Generate new map
        terrain_grid = generate_terrain_grid(seed, 100, 100)
        roads = generate_roads(MAP_REGIONS)
        
        world_map = WorldMap(
            world_id=world_id,
            seed=seed,
            regions=MAP_REGIONS,
            terrain_grid=terrain_grid,
            roads=roads
        ).dict()
        
        await db.world_maps.insert_one(world_map)
    
    # Get any modifications
    modifications = await db.map_modifications.find(
        {"world_id": world_id, "reverted": False},
        {"_id": 0}
    ).to_list(500)
    
    # Apply modifications to terrain
    for mod in modifications:
        if mod.get("mod_type") == "terrain":
            pos = mod.get("position", (0, 0))
            terrain = mod.get("data", {}).get("terrain_type", "grass")
            world_map["terrain_grid"][f"{pos[0]},{pos[1]}"] = terrain
    
    return world_map

@world_map_router.get("/{world_id}/entities")
async def get_map_entities(world_id: str, region_id: Optional[str] = None):
    """Get all entities on the map"""
    db = get_db()
    
    query = {"world_id": world_id, "visible": True}
    if region_id:
        query["region_id"] = region_id
    
    entities = await db.map_entities.find(query, {"_id": 0}).to_list(500)
    
    return {"entities": entities, "count": len(entities)}

@world_map_router.post("/{world_id}/entities/update")
async def update_entity_position(world_id: str, data: UpdatePositionRequest):
    """Update an entity's position on the map"""
    db = get_db()
    
    update_data = {
        "position": data.position,
        "region_id": data.region_id,
        "last_update": datetime.now(timezone.utc).isoformat()
    }
    
    if data.facing is not None:
        update_data["facing"] = data.facing
    
    result = await db.map_entities.update_one(
        {"world_id": world_id, "entity_id": data.entity_id},
        {"$set": update_data},
        upsert=True
    )
    
    return {"updated": True, "entity_id": data.entity_id, "position": data.position}

@world_map_router.post("/{world_id}/terrain/modify")
async def modify_terrain(world_id: str, data: ModifyTerrainRequest, modifier_id: str, modifier_type: str = "player"):
    """Modify terrain on the map (player/AI action)"""
    db = get_db()
    
    if data.terrain_type not in TERRAIN_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid terrain type: {data.terrain_type}")
    
    # Record modification
    mod = MapModification(
        world_id=world_id,
        modifier_id=modifier_id,
        modifier_type=modifier_type,
        mod_type="terrain",
        position=data.position,
        data={"terrain_type": data.terrain_type, "radius": data.radius}
    )
    
    await db.map_modifications.insert_one(mod.dict())
    
    # Update map
    await db.world_maps.update_one(
        {"world_id": world_id},
        {
            "$set": {
                f"terrain_grid.{data.position[0]},{data.position[1]}": data.terrain_type,
                "last_modified": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # If radius > 1, apply to surrounding cells
    if data.radius > 1:
        for dx in range(-data.radius + 1, data.radius):
            for dy in range(-data.radius + 1, data.radius):
                if dx == 0 and dy == 0:
                    continue
                x, y = data.position[0] + dx, data.position[1] + dy
                if 0 <= x < 100 and 0 <= y < 100:
                    await db.world_maps.update_one(
                        {"world_id": world_id},
                        {"$set": {f"terrain_grid.{x},{y}": data.terrain_type}}
                    )
    
    # Record world change
    await db.world_changes.insert_one({
        "change_id": str(uuid.uuid4()),
        "initiator_id": modifier_id,
        "initiator_type": modifier_type,
        "action": "modify_terrain",
        "location": f"{data.position[0]},{data.position[1]}",
        "details": {"terrain_type": data.terrain_type},
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "modified": True,
        "mod_id": mod.mod_id,
        "position": data.position,
        "terrain_type": data.terrain_type
    }

@world_map_router.get("/{world_id}/region/{region_id}")
async def get_region_details(world_id: str, region_id: str):
    """Get detailed info about a specific region"""
    db = get_db()
    
    if region_id not in MAP_REGIONS:
        raise HTTPException(status_code=404, detail="Region not found")
    
    region = MAP_REGIONS[region_id]
    
    # Get entities in region
    entities = await db.map_entities.find(
        {"world_id": world_id, "region_id": region_id},
        {"_id": 0}
    ).to_list(100)
    
    # Get buildings in region
    buildings = await db.placed_buildings.find(
        {"world_id": world_id, "region_id": region_id},
        {"_id": 0}
    ).to_list(100)
    
    # Get NPCs at this location
    npcs = await db.ai_villagers.find(
        {"location": region_id},
        {"_id": 0, "villager_id": 1, "name": 1, "role": 1}
    ).to_list(20)
    
    return {
        "region_id": region_id,
        "region": region,
        "entities": entities,
        "buildings": buildings,
        "npcs": npcs,
        "entity_count": len(entities),
        "building_count": len(buildings)
    }

@world_map_router.get("/{world_id}/modifications")
async def get_map_modifications(world_id: str, limit: int = 100):
    """Get history of map modifications"""
    db = get_db()
    
    mods = await db.map_modifications.find(
        {"world_id": world_id},
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    
    return {"modifications": mods, "count": len(mods)}

@world_map_router.post("/{world_id}/poi/add")
async def add_point_of_interest(
    world_id: str, 
    name: str, 
    position: Tuple[int, int], 
    poi_type: str,
    description: str,
    creator_id: str,
    creator_type: str = "player"
):
    """Add a point of interest to the map"""
    db = get_db()
    
    poi = {
        "poi_id": str(uuid.uuid4()),
        "name": name,
        "position": position,
        "type": poi_type,
        "description": description,
        "created_by": creator_id,
        "created_by_type": creator_type,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "visible": True
    }
    
    await db.world_maps.update_one(
        {"world_id": world_id},
        {"$push": {"points_of_interest": poi}}
    )
    
    return {"added": True, "poi": poi}

@world_map_router.get("/{world_id}/export")
async def export_map_for_engine(world_id: str, format: str = "json"):
    """Export map data for 3D engine consumption"""
    db = get_db()
    
    world_map = await db.world_maps.find_one({"world_id": world_id}, {"_id": 0})
    
    if not world_map:
        raise HTTPException(status_code=404, detail="Map not found")
    
    # Format for engine
    export_data = {
        "version": "1.0",
        "world_id": world_id,
        "seed": world_map.get("seed"),
        "dimensions": {"width": world_map.get("width", 100), "height": world_map.get("height", 100)},
        "regions": world_map.get("regions", {}),
        "terrain_types": TERRAIN_TYPES,
        "roads": world_map.get("roads", []),
        "points_of_interest": world_map.get("points_of_interest", []),
        "export_timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # Optionally include full terrain grid (can be large)
    if format == "full":
        export_data["terrain_grid"] = world_map.get("terrain_grid", {})
    
    return export_data

@world_map_router.get("/{world_id}/stats")
async def get_map_stats(world_id: str):
    """Get statistics about the map"""
    db = get_db()
    
    entities_count = await db.map_entities.count_documents({"world_id": world_id})
    buildings_count = await db.placed_buildings.count_documents({"world_id": world_id})
    modifications_count = await db.map_modifications.count_documents({"world_id": world_id, "reverted": False})
    
    # Entities by region
    pipeline = [
        {"$match": {"world_id": world_id}},
        {"$group": {"_id": "$region_id", "count": {"$sum": 1}}}
    ]
    by_region = await db.map_entities.aggregate(pipeline).to_list(20)
    
    return {
        "total_entities": entities_count,
        "total_buildings": buildings_count,
        "total_modifications": modifications_count,
        "entities_by_region": {r["_id"]: r["count"] for r in by_region if r["_id"]}
    }
