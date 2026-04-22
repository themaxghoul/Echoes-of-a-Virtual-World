# 2D Building System Router - Grid-based building for Story Mode
# Players can place structures, decorations, and functional buildings

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime, timezone
import uuid
import logging

building_system_router = APIRouter(prefix="/building", tags=["building"])

logger = logging.getLogger(__name__)

# ============ Building Definitions ============

BUILDING_CATEGORIES = {
    "basic_structures": {
        "name": "Basic Structures",
        "icon": "home",
        "color": "#8B5A2B",
        "items": {
            "wooden_house": {"name": "Wooden House", "size": [3, 3], "cost": 100, "materials": {"wood": 50, "stone": 10}},
            "stone_house": {"name": "Stone House", "size": [3, 3], "cost": 200, "materials": {"stone": 80, "wood": 20}},
            "cottage": {"name": "Cottage", "size": [2, 2], "cost": 75, "materials": {"wood": 30, "thatch": 20}},
            "tower": {"name": "Tower", "size": [2, 2], "cost": 300, "materials": {"stone": 100, "iron": 20}},
            "wall_segment": {"name": "Wall Segment", "size": [1, 1], "cost": 25, "materials": {"stone": 15}},
            "gate": {"name": "Gate", "size": [2, 1], "cost": 50, "materials": {"wood": 20, "iron": 10}},
            "bridge": {"name": "Bridge", "size": [3, 1], "cost": 60, "materials": {"wood": 40}},
        }
    },
    "functional_buildings": {
        "name": "Functional Buildings",
        "icon": "factory",
        "color": "#D97706",
        "items": {
            "forge": {"name": "Forge", "size": [3, 2], "cost": 250, "materials": {"stone": 60, "iron": 40}, "function": "crafting"},
            "farm": {"name": "Farm", "size": [4, 4], "cost": 150, "materials": {"wood": 30, "seeds": 50}, "function": "production"},
            "mine_entrance": {"name": "Mine Entrance", "size": [2, 2], "cost": 200, "materials": {"wood": 40, "stone": 30}, "function": "gathering"},
            "temple": {"name": "Temple", "size": [4, 3], "cost": 500, "materials": {"stone": 100, "gold": 50}, "function": "ritual"},
            "marketplace": {"name": "Marketplace", "size": [5, 4], "cost": 400, "materials": {"wood": 80, "cloth": 40}, "function": "trading"},
            "library": {"name": "Library", "size": [3, 3], "cost": 350, "materials": {"wood": 50, "paper": 100}, "function": "knowledge"},
            "barracks": {"name": "Barracks", "size": [4, 3], "cost": 300, "materials": {"wood": 60, "iron": 30}, "function": "military"},
            "tavern": {"name": "Tavern", "size": [3, 3], "cost": 200, "materials": {"wood": 50, "barrels": 20}, "function": "social"},
            "workshop": {"name": "Workshop", "size": [3, 2], "cost": 175, "materials": {"wood": 40, "tools": 20}, "function": "crafting"},
        }
    },
    "decorative": {
        "name": "Decorative",
        "icon": "flower",
        "color": "#10B981",
        "items": {
            "tree_oak": {"name": "Oak Tree", "size": [1, 1], "cost": 10, "materials": {"sapling": 1}},
            "tree_pine": {"name": "Pine Tree", "size": [1, 1], "cost": 10, "materials": {"sapling": 1}},
            "flower_bed": {"name": "Flower Bed", "size": [1, 1], "cost": 5, "materials": {"seeds": 5}},
            "fountain": {"name": "Fountain", "size": [2, 2], "cost": 150, "materials": {"stone": 50, "water_essence": 10}},
            "statue": {"name": "Statue", "size": [1, 1], "cost": 100, "materials": {"stone": 40}},
            "bench": {"name": "Bench", "size": [1, 1], "cost": 15, "materials": {"wood": 10}},
            "lamp_post": {"name": "Lamp Post", "size": [1, 1], "cost": 20, "materials": {"iron": 5, "glass": 5}},
            "well": {"name": "Well", "size": [1, 1], "cost": 50, "materials": {"stone": 30}},
            "signpost": {"name": "Signpost", "size": [1, 1], "cost": 10, "materials": {"wood": 5}},
        }
    },
    "paths": {
        "name": "Paths & Roads",
        "icon": "route",
        "color": "#6B7280",
        "items": {
            "dirt_path": {"name": "Dirt Path", "size": [1, 1], "cost": 2, "materials": {}},
            "stone_path": {"name": "Stone Path", "size": [1, 1], "cost": 5, "materials": {"stone": 2}},
            "cobblestone_road": {"name": "Cobblestone Road", "size": [1, 1], "cost": 8, "materials": {"stone": 5}},
            "wooden_boardwalk": {"name": "Wooden Boardwalk", "size": [1, 1], "cost": 6, "materials": {"wood": 3}},
        }
    },
    "special": {
        "name": "Special Structures",
        "icon": "sparkles",
        "color": "#8B5CF6",
        "items": {
            "portal": {"name": "Portal", "size": [2, 2], "cost": 1000, "materials": {"arcane_stone": 50, "essence": 100}, "function": "teleport"},
            "obelisk": {"name": "Ancient Obelisk", "size": [1, 1], "cost": 500, "materials": {"ancient_stone": 20}, "function": "buff"},
            "altar": {"name": "Altar", "size": [2, 1], "cost": 300, "materials": {"stone": 40, "gold": 20}, "function": "ritual"},
            "waypoint": {"name": "Waypoint", "size": [1, 1], "cost": 200, "materials": {"crystal": 10}, "function": "fast_travel"},
            "monument": {"name": "Monument", "size": [3, 3], "cost": 800, "materials": {"stone": 150, "gold": 30}, "function": "landmark"},
        }
    }
}

# Grid settings
GRID_SIZE = 100  # 100x100 grid per region
CELL_SIZE = 32  # pixels per cell for rendering

# ============ Models ============

class PlacedBuilding(BaseModel):
    building_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    building_type: str  # e.g., "wooden_house"
    category: str
    name: str
    position: Tuple[int, int]  # Grid position (x, y)
    size: Tuple[int, int]  # Width x Height in grid cells
    rotation: int = 0  # 0, 90, 180, 270 degrees
    world_id: str
    region_id: str
    owner_id: str
    owner_type: str = "player"  # player or npc
    placed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    health: int = 100
    is_functional: bool = True
    function: Optional[str] = None
    custom_name: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class BuildingGrid(BaseModel):
    grid_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    world_id: str
    region_id: str
    size: Tuple[int, int] = (GRID_SIZE, GRID_SIZE)
    buildings: List[str] = Field(default_factory=list)  # Building IDs
    terrain: Dict[str, str] = Field(default_factory=dict)  # "x,y": terrain_type
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_modified: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class PlaceBuildingRequest(BaseModel):
    building_type: str
    position: Tuple[int, int]
    rotation: int = 0
    world_id: str
    region_id: str
    custom_name: Optional[str] = None

class MoveBuildingRequest(BaseModel):
    building_id: str
    new_position: Tuple[int, int]
    new_rotation: Optional[int] = None

# ============ Database Helper ============

def get_db():
    from server import db
    return db

# ============ Helper Functions ============

def get_building_info(building_type: str):
    """Get building info from type"""
    for cat_id, category in BUILDING_CATEGORIES.items():
        if building_type in category["items"]:
            item = category["items"][building_type]
            return {**item, "category": cat_id, "type": building_type}
    return None

async def check_collision(db, world_id: str, region_id: str, position: Tuple[int, int], size: Tuple[int, int], exclude_id: str = None):
    """Check if a position collides with existing buildings"""
    x, y = position
    w, h = size
    
    # Get all buildings in region
    buildings = await db.placed_buildings.find({
        "world_id": world_id,
        "region_id": region_id
    }).to_list(500)
    
    for building in buildings:
        if exclude_id and building.get("building_id") == exclude_id:
            continue
        
        bx, by = building.get("position", (0, 0))
        bw, bh = building.get("size", (1, 1))
        
        # Check overlap
        if not (x + w <= bx or x >= bx + bw or y + h <= by or y >= by + bh):
            return True, building.get("name", "Unknown")
    
    return False, None

# ============ Endpoints ============

@building_system_router.get("/catalog")
async def get_building_catalog():
    """Get all available buildings"""
    return {
        "categories": BUILDING_CATEGORIES,
        "grid_size": GRID_SIZE,
        "cell_size": CELL_SIZE
    }

@building_system_router.get("/grid/{world_id}/{region_id}")
async def get_region_grid(world_id: str, region_id: str):
    """Get the building grid for a region"""
    db = get_db()
    
    grid = await db.building_grids.find_one(
        {"world_id": world_id, "region_id": region_id},
        {"_id": 0}
    )
    
    if not grid:
        # Create new grid
        grid = BuildingGrid(world_id=world_id, region_id=region_id).dict()
        await db.building_grids.insert_one(grid)
    
    # Get all buildings
    buildings = await db.placed_buildings.find(
        {"world_id": world_id, "region_id": region_id},
        {"_id": 0}
    ).to_list(500)
    
    return {
        "grid": grid,
        "buildings": buildings,
        "grid_size": GRID_SIZE
    }

@building_system_router.post("/place")
async def place_building(data: PlaceBuildingRequest, owner_id: str, owner_type: str = "player"):
    """Place a building on the grid"""
    db = get_db()
    
    # Get building info
    building_info = get_building_info(data.building_type)
    if not building_info:
        raise HTTPException(status_code=400, detail=f"Unknown building type: {data.building_type}")
    
    # Check bounds
    x, y = data.position
    w, h = building_info["size"]
    
    if x < 0 or y < 0 or x + w > GRID_SIZE or y + h > GRID_SIZE:
        raise HTTPException(status_code=400, detail="Building out of bounds")
    
    # Check collision
    collision, collision_name = await check_collision(db, data.world_id, data.region_id, data.position, tuple(building_info["size"]))
    if collision:
        raise HTTPException(status_code=400, detail=f"Collision with {collision_name}")
    
    # Check resources (simplified - just check cost)
    wallet = await db.entity_wallets.find_one({"entity_id": owner_id})
    balance = wallet.get("balance_ve", 0) if wallet else 0
    cost = building_info.get("cost", 0)
    
    if balance < cost:
        raise HTTPException(status_code=400, detail=f"Insufficient funds (need {cost} VE$)")
    
    # Deduct cost
    if cost > 0:
        await db.entity_wallets.update_one(
            {"entity_id": owner_id},
            {"$inc": {"balance_ve": -cost}}
        )
    
    # Create building
    building = PlacedBuilding(
        building_type=data.building_type,
        category=building_info["category"],
        name=building_info["name"],
        position=data.position,
        size=tuple(building_info["size"]),
        rotation=data.rotation,
        world_id=data.world_id,
        region_id=data.region_id,
        owner_id=owner_id,
        owner_type=owner_type,
        function=building_info.get("function"),
        custom_name=data.custom_name
    )
    
    await db.placed_buildings.insert_one(building.dict())
    
    # Update grid
    await db.building_grids.update_one(
        {"world_id": data.world_id, "region_id": data.region_id},
        {
            "$push": {"buildings": building.building_id},
            "$set": {"last_modified": datetime.now(timezone.utc).isoformat()}
        },
        upsert=True
    )
    
    # Award building skill XP
    await db.entity_skills.update_one(
        {"entity_id": owner_id, "entity_type": owner_type},
        {"$inc": {"skills.engineering.xp": 10, "total_skill_points": 10}},
        upsert=True
    )
    
    # Record world change
    await db.world_changes.insert_one({
        "change_id": str(uuid.uuid4()),
        "initiator_id": owner_id,
        "initiator_type": owner_type,
        "action": "build_structure",
        "location": data.region_id,
        "details": {"building_type": data.building_type, "position": data.position},
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "placed": True,
        "building_id": building.building_id,
        "building": building.dict(),
        "cost_paid": cost
    }

@building_system_router.post("/move")
async def move_building(data: MoveBuildingRequest, owner_id: str):
    """Move an existing building"""
    db = get_db()
    
    building = await db.placed_buildings.find_one({"building_id": data.building_id})
    
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    
    if building.get("owner_id") != owner_id:
        raise HTTPException(status_code=403, detail="Not your building")
    
    # Check bounds
    x, y = data.new_position
    w, h = building.get("size", (1, 1))
    
    if x < 0 or y < 0 or x + w > GRID_SIZE or y + h > GRID_SIZE:
        raise HTTPException(status_code=400, detail="Position out of bounds")
    
    # Check collision (exclude self)
    collision, collision_name = await check_collision(
        db, 
        building.get("world_id"), 
        building.get("region_id"), 
        data.new_position, 
        tuple(building.get("size", (1, 1))),
        exclude_id=data.building_id
    )
    if collision:
        raise HTTPException(status_code=400, detail=f"Collision with {collision_name}")
    
    # Update position
    update = {"position": data.new_position}
    if data.new_rotation is not None:
        update["rotation"] = data.new_rotation
    
    await db.placed_buildings.update_one(
        {"building_id": data.building_id},
        {"$set": update}
    )
    
    return {"moved": True, "building_id": data.building_id, "new_position": data.new_position}

@building_system_router.delete("/{building_id}")
async def demolish_building(building_id: str, owner_id: str):
    """Demolish a building"""
    db = get_db()
    
    building = await db.placed_buildings.find_one({"building_id": building_id})
    
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    
    if building.get("owner_id") != owner_id:
        raise HTTPException(status_code=403, detail="Not your building")
    
    # Get building info for partial refund
    building_info = get_building_info(building.get("building_type"))
    refund = int(building_info.get("cost", 0) * 0.5) if building_info else 0
    
    # Refund partial cost
    if refund > 0:
        await db.entity_wallets.update_one(
            {"entity_id": owner_id},
            {"$inc": {"balance_ve": refund}}
        )
    
    # Remove building
    await db.placed_buildings.delete_one({"building_id": building_id})
    
    # Update grid
    await db.building_grids.update_one(
        {"world_id": building.get("world_id"), "region_id": building.get("region_id")},
        {
            "$pull": {"buildings": building_id},
            "$set": {"last_modified": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    return {"demolished": True, "building_id": building_id, "refund": refund}

@building_system_router.get("/owned/{owner_id}")
async def get_owned_buildings(owner_id: str, world_id: Optional[str] = None):
    """Get all buildings owned by an entity"""
    db = get_db()
    
    query = {"owner_id": owner_id}
    if world_id:
        query["world_id"] = world_id
    
    buildings = await db.placed_buildings.find(query, {"_id": 0}).to_list(500)
    
    return {"buildings": buildings, "count": len(buildings)}

@building_system_router.get("/stats/{world_id}")
async def get_building_stats(world_id: str):
    """Get building statistics for a world"""
    db = get_db()
    
    total = await db.placed_buildings.count_documents({"world_id": world_id})
    
    # By category
    pipeline = [
        {"$match": {"world_id": world_id}},
        {"$group": {"_id": "$category", "count": {"$sum": 1}}}
    ]
    by_category = await db.placed_buildings.aggregate(pipeline).to_list(10)
    
    # By owner type
    pipeline = [
        {"$match": {"world_id": world_id}},
        {"$group": {"_id": "$owner_type", "count": {"$sum": 1}}}
    ]
    by_owner = await db.placed_buildings.aggregate(pipeline).to_list(10)
    
    return {
        "total_buildings": total,
        "by_category": {c["_id"]: c["count"] for c in by_category if c["_id"]},
        "by_owner_type": {o["_id"]: o["count"] for o in by_owner if o["_id"]}
    }
