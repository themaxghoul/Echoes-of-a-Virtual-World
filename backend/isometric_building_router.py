# 2D Isometric Building System - Topographic View with Prefabs
# Plot-based system with size tiers and prefab structures

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone
import uuid
import logging

isometric_building_router = APIRouter(prefix="/isometric-building", tags=["isometric-building"])

logger = logging.getLogger(__name__)

# ============ PLOT SIZE TIERS ============
PLOT_SIZES = {
    "small": {
        "name": "Small Plot",
        "dimensions": [4, 4],  # 4x4 tiles
        "cost": 500,
        "description": "Compact plot for basic structures",
        "max_buildings": 1,
        "color": "#4ADE80"
    },
    "medium": {
        "name": "Medium Plot",
        "dimensions": [6, 6],  # 6x6 tiles
        "cost": 1500,
        "description": "Standard plot for most purposes",
        "max_buildings": 3,
        "color": "#60A5FA"
    },
    "large": {
        "name": "Large Plot",
        "dimensions": [8, 8],  # 8x8 tiles
        "cost": 4000,
        "description": "Expansive plot for major developments",
        "max_buildings": 6,
        "color": "#F59E0B"
    }
}

# ============ BUILDING PREFABS BY CATEGORY ============
BUILDING_PREFABS = {
    "residential": {
        "name": "Residential",
        "description": "Housing for villagers and players",
        "icon": "home",
        "color": "#8B5CF6",
        "plot_sizes": ["small", "medium", "large"],
        "prefabs": {
            "cottage": {
                "name": "Cottage",
                "description": "Cozy small home for 1-2 residents",
                "size": [2, 2],
                "cost": 200,
                "capacity": 2,
                "income_per_day": 5,
                "sprite_variants": 4,
                "requires_plot": "small"
            },
            "townhouse": {
                "name": "Townhouse",
                "description": "Multi-story urban dwelling",
                "size": [3, 2],
                "cost": 450,
                "capacity": 4,
                "income_per_day": 12,
                "sprite_variants": 5,
                "requires_plot": "small"
            },
            "manor": {
                "name": "Manor",
                "description": "Stately home with gardens",
                "size": [4, 4],
                "cost": 1200,
                "capacity": 8,
                "income_per_day": 30,
                "sprite_variants": 4,
                "requires_plot": "medium"
            },
            "apartment_complex": {
                "name": "Apartment Complex",
                "description": "High-density housing",
                "size": [5, 4],
                "cost": 2500,
                "capacity": 20,
                "income_per_day": 60,
                "sprite_variants": 6,
                "requires_plot": "medium"
            },
            "villa": {
                "name": "Villa",
                "description": "Luxurious estate",
                "size": [6, 5],
                "cost": 5000,
                "capacity": 12,
                "income_per_day": 100,
                "sprite_variants": 4,
                "requires_plot": "large"
            },
            "palace": {
                "name": "Palace",
                "description": "Royal residence",
                "size": [8, 6],
                "cost": 15000,
                "capacity": 30,
                "income_per_day": 250,
                "sprite_variants": 4,
                "requires_plot": "large"
            }
        }
    },
    "commercial": {
        "name": "Commercial",
        "description": "Shops, markets, and trade buildings",
        "icon": "store",
        "color": "#F59E0B",
        "plot_sizes": ["small", "medium", "large"],
        "prefabs": {
            "market_stall": {
                "name": "Market Stall",
                "description": "Basic trading post",
                "size": [2, 1],
                "cost": 100,
                "trade_slots": 3,
                "income_per_day": 8,
                "sprite_variants": 6,
                "requires_plot": "small"
            },
            "general_store": {
                "name": "General Store",
                "description": "Sells everyday goods",
                "size": [3, 2],
                "cost": 400,
                "trade_slots": 8,
                "income_per_day": 20,
                "sprite_variants": 5,
                "requires_plot": "small"
            },
            "tavern": {
                "name": "Tavern",
                "description": "Rest, food, and rumors",
                "size": [4, 3],
                "cost": 800,
                "services": ["rest", "food", "quests"],
                "income_per_day": 35,
                "sprite_variants": 5,
                "requires_plot": "medium"
            },
            "bank": {
                "name": "Bank",
                "description": "Secure storage and loans",
                "size": [4, 3],
                "cost": 2000,
                "services": ["storage", "loans", "exchange"],
                "income_per_day": 75,
                "sprite_variants": 4,
                "requires_plot": "medium"
            },
            "grand_bazaar": {
                "name": "Grand Bazaar",
                "description": "Large marketplace complex",
                "size": [6, 5],
                "cost": 5000,
                "trade_slots": 25,
                "income_per_day": 150,
                "sprite_variants": 4,
                "requires_plot": "large"
            },
            "auction_house": {
                "name": "Auction House",
                "description": "Rare item trading venue",
                "size": [5, 4],
                "cost": 8000,
                "services": ["auctions", "appraisal", "rare_items"],
                "income_per_day": 200,
                "sprite_variants": 4,
                "requires_plot": "large"
            }
        }
    },
    "industrial": {
        "name": "Industrial",
        "description": "Crafting and production facilities",
        "icon": "factory",
        "color": "#EF4444",
        "plot_sizes": ["small", "medium", "large"],
        "prefabs": {
            "smithy": {
                "name": "Smithy",
                "description": "Basic metal working",
                "size": [3, 2],
                "cost": 350,
                "production_type": "weapons_armor",
                "production_rate": 1.0,
                "sprite_variants": 5,
                "requires_plot": "small"
            },
            "carpentry": {
                "name": "Carpentry Workshop",
                "description": "Wood crafting",
                "size": [3, 2],
                "cost": 300,
                "production_type": "furniture_tools",
                "production_rate": 1.0,
                "sprite_variants": 5,
                "requires_plot": "small"
            },
            "alchemy_lab": {
                "name": "Alchemy Lab",
                "description": "Potions and reagents",
                "size": [3, 3],
                "cost": 600,
                "production_type": "potions",
                "production_rate": 1.2,
                "sprite_variants": 4,
                "requires_plot": "medium"
            },
            "foundry": {
                "name": "Foundry",
                "description": "Advanced metalworking",
                "size": [5, 4],
                "cost": 2000,
                "production_type": "advanced_metals",
                "production_rate": 2.0,
                "sprite_variants": 5,
                "requires_plot": "medium"
            },
            "enchanting_tower": {
                "name": "Enchanting Tower",
                "description": "Magical item creation",
                "size": [3, 3],
                "cost": 3500,
                "production_type": "enchantments",
                "production_rate": 0.5,
                "sprite_variants": 4,
                "requires_plot": "medium"
            },
            "manufacturing_plant": {
                "name": "Manufacturing Plant",
                "description": "Mass production facility",
                "size": [7, 5],
                "cost": 10000,
                "production_type": "all",
                "production_rate": 5.0,
                "sprite_variants": 4,
                "requires_plot": "large"
            }
        }
    },
    "agricultural": {
        "name": "Agricultural",
        "description": "Farms and food production",
        "icon": "wheat",
        "color": "#22C55E",
        "plot_sizes": ["small", "medium", "large"],
        "prefabs": {
            "vegetable_garden": {
                "name": "Vegetable Garden",
                "description": "Basic food production",
                "size": [3, 3],
                "cost": 150,
                "crop_type": "vegetables",
                "yield_per_harvest": 10,
                "sprite_variants": 6,
                "requires_plot": "small"
            },
            "orchard": {
                "name": "Orchard",
                "description": "Fruit trees",
                "size": [4, 3],
                "cost": 400,
                "crop_type": "fruits",
                "yield_per_harvest": 15,
                "sprite_variants": 5,
                "requires_plot": "small"
            },
            "grain_farm": {
                "name": "Grain Farm",
                "description": "Wheat and grain production",
                "size": [5, 4],
                "cost": 800,
                "crop_type": "grains",
                "yield_per_harvest": 30,
                "sprite_variants": 5,
                "requires_plot": "medium"
            },
            "livestock_pen": {
                "name": "Livestock Pen",
                "description": "Animal husbandry",
                "size": [5, 5],
                "cost": 1200,
                "animal_capacity": 10,
                "yield_per_harvest": 20,
                "sprite_variants": 4,
                "requires_plot": "medium"
            },
            "vineyard": {
                "name": "Vineyard",
                "description": "Wine grape cultivation",
                "size": [6, 4],
                "cost": 2000,
                "crop_type": "grapes",
                "yield_per_harvest": 25,
                "sprite_variants": 4,
                "requires_plot": "medium"
            },
            "mega_farm": {
                "name": "Mega Farm",
                "description": "Industrial agriculture",
                "size": [8, 6],
                "cost": 8000,
                "crop_type": "all",
                "yield_per_harvest": 100,
                "sprite_variants": 4,
                "requires_plot": "large"
            }
        }
    },
    "civic": {
        "name": "Civic",
        "description": "Community and public buildings",
        "icon": "landmark",
        "color": "#3B82F6",
        "plot_sizes": ["small", "medium", "large"],
        "prefabs": {
            "well": {
                "name": "Well",
                "description": "Water source",
                "size": [1, 1],
                "cost": 50,
                "radius_effect": 5,
                "sprite_variants": 4,
                "requires_plot": "small"
            },
            "shrine": {
                "name": "Shrine",
                "description": "Small place of worship",
                "size": [2, 2],
                "cost": 200,
                "blessing_type": "minor",
                "sprite_variants": 6,
                "requires_plot": "small"
            },
            "guard_post": {
                "name": "Guard Post",
                "description": "Security station",
                "size": [2, 2],
                "cost": 300,
                "defense_rating": 10,
                "sprite_variants": 5,
                "requires_plot": "small"
            },
            "town_hall": {
                "name": "Town Hall",
                "description": "Administrative center",
                "size": [4, 3],
                "cost": 1500,
                "admin_bonus": 0.2,
                "sprite_variants": 4,
                "requires_plot": "medium"
            },
            "temple": {
                "name": "Temple",
                "description": "Major religious building",
                "size": [5, 4],
                "cost": 3000,
                "blessing_type": "major",
                "sprite_variants": 5,
                "requires_plot": "medium"
            },
            "colosseum": {
                "name": "Colosseum",
                "description": "Entertainment arena",
                "size": [8, 8],
                "cost": 20000,
                "entertainment_value": 100,
                "sprite_variants": 4,
                "requires_plot": "large"
            }
        }
    }
}

# ============ MODELS ============

class PlotPurchase(BaseModel):
    user_id: str
    plot_size: str  # small, medium, large
    position_x: int
    position_y: int
    name: Optional[str] = None

class BuildingPlacement(BaseModel):
    user_id: str
    plot_id: str
    category: str
    prefab_id: str
    variant: int = 0  # sprite variant
    position_x: int  # relative to plot
    position_y: int
    rotation: int = 0  # 0, 90, 180, 270

class PlotUpgrade(BaseModel):
    user_id: str
    plot_id: str
    target_size: str  # medium or large

# MongoDB reference
def get_db():
    from server import db
    return db

# ============ ENDPOINTS ============

@isometric_building_router.get("/plot-sizes")
async def get_plot_sizes():
    """Get available plot size tiers"""
    return {
        "plot_sizes": PLOT_SIZES,
        "count": len(PLOT_SIZES)
    }

@isometric_building_router.get("/prefabs")
async def get_all_prefabs():
    """Get all building prefabs organized by category"""
    return {
        "categories": BUILDING_PREFABS,
        "total_prefabs": sum(len(cat["prefabs"]) for cat in BUILDING_PREFABS.values())
    }

@isometric_building_router.get("/prefabs/{category}")
async def get_category_prefabs(category: str):
    """Get prefabs for a specific category"""
    if category not in BUILDING_PREFABS:
        raise HTTPException(status_code=404, detail=f"Category not found: {category}")
    
    return {
        "category": category,
        **BUILDING_PREFABS[category]
    }

@isometric_building_router.post("/plot/purchase")
async def purchase_plot(data: PlotPurchase):
    """Purchase a new plot of land"""
    db = get_db()
    
    if data.plot_size not in PLOT_SIZES:
        raise HTTPException(status_code=400, detail="Invalid plot size")
    
    plot_config = PLOT_SIZES[data.plot_size]
    cost = plot_config["cost"]
    
    # Check user balance
    user_account = await db.earnings_accounts.find_one({"user_id": data.user_id})
    balance = user_account.get("available_balance_usd", 0) if user_account else 0
    
    if balance < cost:
        raise HTTPException(
            status_code=400, 
            detail=f"Insufficient funds. Need VE${cost}, have VE${balance}"
        )
    
    # Check for overlapping plots
    dims = plot_config["dimensions"]
    # Note: Overlapping check reserved for future use
    # overlapping = await db.player_plots.find_one({...})
    
    # Create plot
    plot_id = str(uuid.uuid4())
    plot_doc = {
        "plot_id": plot_id,
        "user_id": data.user_id,
        "plot_size": data.plot_size,
        "name": data.name or f"{plot_config['name']} #{plot_id[:6]}",
        "position_x": data.position_x,
        "position_y": data.position_y,
        "dimensions": dims,
        "buildings": [],
        "max_buildings": plot_config["max_buildings"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "upgraded_from": None
    }
    
    await db.player_plots.insert_one(plot_doc)
    
    # Deduct cost
    await db.earnings_accounts.update_one(
        {"user_id": data.user_id},
        {"$inc": {"available_balance_usd": -cost}}
    )
    
    plot_doc.pop("_id", None)
    return {
        "success": True,
        "plot": plot_doc,
        "cost_paid": cost,
        "remaining_balance": balance - cost
    }

@isometric_building_router.get("/plots/{user_id}")
async def get_user_plots(user_id: str):
    """Get all plots owned by a user"""
    db = get_db()
    
    plots = await db.player_plots.find(
        {"user_id": user_id},
        {"_id": 0}
    ).to_list(100)
    
    # Calculate total stats
    total_buildings = sum(len(p.get("buildings", [])) for p in plots)
    total_income = 0
    
    for plot in plots:
        for building in plot.get("buildings", []):
            prefab = BUILDING_PREFABS.get(building.get("category"), {}).get("prefabs", {}).get(building.get("prefab_id"), {})
            total_income += prefab.get("income_per_day", 0)
    
    return {
        "user_id": user_id,
        "plots": plots,
        "total_plots": len(plots),
        "total_buildings": total_buildings,
        "estimated_daily_income": total_income
    }

@isometric_building_router.get("/plot/{plot_id}")
async def get_plot_details(plot_id: str):
    """Get detailed info about a specific plot"""
    db = get_db()
    
    plot = await db.player_plots.find_one({"plot_id": plot_id}, {"_id": 0})
    if not plot:
        raise HTTPException(status_code=404, detail="Plot not found")
    
    # Enrich building data
    enriched_buildings = []
    for building in plot.get("buildings", []):
        cat = BUILDING_PREFABS.get(building.get("category"), {})
        prefab = cat.get("prefabs", {}).get(building.get("prefab_id"), {})
        enriched_buildings.append({
            **building,
            "prefab_data": prefab
        })
    
    plot["buildings"] = enriched_buildings
    plot["size_config"] = PLOT_SIZES.get(plot.get("plot_size"), {})
    
    return plot

@isometric_building_router.post("/building/place")
async def place_building(data: BuildingPlacement):
    """Place a building prefab on a plot"""
    db = get_db()
    
    # Validate category and prefab
    if data.category not in BUILDING_PREFABS:
        raise HTTPException(status_code=400, detail="Invalid category")
    
    prefabs = BUILDING_PREFABS[data.category]["prefabs"]
    if data.prefab_id not in prefabs:
        raise HTTPException(status_code=400, detail="Invalid prefab")
    
    prefab = prefabs[data.prefab_id]
    
    # Get plot
    plot = await db.player_plots.find_one({"plot_id": data.plot_id, "user_id": data.user_id})
    if not plot:
        raise HTTPException(status_code=404, detail="Plot not found")
    
    # Check plot size requirement
    if prefab.get("requires_plot"):
        plot_sizes = ["small", "medium", "large"]
        required_idx = plot_sizes.index(prefab["requires_plot"])
        current_idx = plot_sizes.index(plot["plot_size"])
        if current_idx < required_idx:
            raise HTTPException(
                status_code=400,
                detail=f"Building requires {prefab['requires_plot']} plot or larger"
            )
    
    # Check max buildings
    if len(plot.get("buildings", [])) >= plot.get("max_buildings", 1):
        raise HTTPException(
            status_code=400,
            detail=f"Plot has reached maximum buildings ({plot.get('max_buildings')})"
        )
    
    # Check building cost
    cost = prefab.get("cost", 0)
    user_account = await db.earnings_accounts.find_one({"user_id": data.user_id})
    balance = user_account.get("available_balance_usd", 0) if user_account else 0
    
    if balance < cost:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient funds. Need VE${cost}, have VE${balance}"
        )
    
    # Create building entry
    building_id = str(uuid.uuid4())
    building = {
        "building_id": building_id,
        "category": data.category,
        "prefab_id": data.prefab_id,
        "variant": min(data.variant, prefab.get("sprite_variants", 1) - 1),
        "position_x": data.position_x,
        "position_y": data.position_y,
        "rotation": data.rotation,
        "placed_at": datetime.now(timezone.utc).isoformat(),
        "level": 1
    }
    
    # Add to plot
    await db.player_plots.update_one(
        {"plot_id": data.plot_id},
        {"$push": {"buildings": building}}
    )
    
    # Deduct cost
    await db.earnings_accounts.update_one(
        {"user_id": data.user_id},
        {"$inc": {"available_balance_usd": -cost}}
    )
    
    return {
        "success": True,
        "building": building,
        "prefab_data": prefab,
        "cost_paid": cost,
        "remaining_balance": balance - cost
    }

@isometric_building_router.delete("/building/{plot_id}/{building_id}")
async def remove_building(plot_id: str, building_id: str, user_id: str):
    """Remove a building from a plot (partial refund)"""
    db = get_db()
    
    plot = await db.player_plots.find_one({"plot_id": plot_id, "user_id": user_id})
    if not plot:
        raise HTTPException(status_code=404, detail="Plot not found")
    
    # Find building
    building = next((b for b in plot.get("buildings", []) if b["building_id"] == building_id), None)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    
    # Calculate refund (50%)
    prefab = BUILDING_PREFABS.get(building["category"], {}).get("prefabs", {}).get(building["prefab_id"], {})
    refund = prefab.get("cost", 0) * 0.5
    
    # Remove building
    await db.player_plots.update_one(
        {"plot_id": plot_id},
        {"$pull": {"buildings": {"building_id": building_id}}}
    )
    
    # Add refund
    await db.earnings_accounts.update_one(
        {"user_id": user_id},
        {"$inc": {"available_balance_usd": refund}}
    )
    
    return {
        "success": True,
        "removed": building_id,
        "refund": refund
    }

@isometric_building_router.post("/plot/upgrade")
async def upgrade_plot(data: PlotUpgrade):
    """Upgrade a plot to a larger size"""
    db = get_db()
    
    plot = await db.player_plots.find_one({"plot_id": data.plot_id, "user_id": data.user_id})
    if not plot:
        raise HTTPException(status_code=404, detail="Plot not found")
    
    current_size = plot["plot_size"]
    sizes = ["small", "medium", "large"]
    
    if data.target_size not in sizes:
        raise HTTPException(status_code=400, detail="Invalid target size")
    
    current_idx = sizes.index(current_size)
    target_idx = sizes.index(data.target_size)
    
    if target_idx <= current_idx:
        raise HTTPException(status_code=400, detail="Can only upgrade to larger size")
    
    # Calculate upgrade cost (difference in base costs)
    current_cost = PLOT_SIZES[current_size]["cost"]
    target_cost = PLOT_SIZES[data.target_size]["cost"]
    upgrade_cost = target_cost - current_cost
    
    # Check balance
    user_account = await db.earnings_accounts.find_one({"user_id": data.user_id})
    balance = user_account.get("available_balance_usd", 0) if user_account else 0
    
    if balance < upgrade_cost:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient funds. Need VE${upgrade_cost}, have VE${balance}"
        )
    
    # Upgrade plot
    new_config = PLOT_SIZES[data.target_size]
    await db.player_plots.update_one(
        {"plot_id": data.plot_id},
        {
            "$set": {
                "plot_size": data.target_size,
                "dimensions": new_config["dimensions"],
                "max_buildings": new_config["max_buildings"],
                "upgraded_from": current_size,
                "upgraded_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Deduct cost
    await db.earnings_accounts.update_one(
        {"user_id": data.user_id},
        {"$inc": {"available_balance_usd": -upgrade_cost}}
    )
    
    return {
        "success": True,
        "plot_id": data.plot_id,
        "previous_size": current_size,
        "new_size": data.target_size,
        "upgrade_cost": upgrade_cost,
        "remaining_balance": balance - upgrade_cost
    }

@isometric_building_router.get("/world-grid/{user_id}")
async def get_world_grid(user_id: str, center_x: int = 0, center_y: int = 0, radius: int = 20):
    """Get the world grid around a center point for rendering"""
    db = get_db()
    
    # Get all plots in view range
    plots = await db.player_plots.find({
        "user_id": user_id,
        "position_x": {"$gte": center_x - radius, "$lte": center_x + radius},
        "position_y": {"$gte": center_y - radius, "$lte": center_y + radius}
    }, {"_id": 0}).to_list(100)
    
    # Create grid data
    grid_data = {
        "center": {"x": center_x, "y": center_y},
        "radius": radius,
        "plots": plots,
        "terrain": []  # Can add terrain features later
    }
    
    return grid_data

@isometric_building_router.get("/stats/{user_id}")
async def get_building_stats(user_id: str):
    """Get building statistics for a user"""
    db = get_db()
    
    plots = await db.player_plots.find({"user_id": user_id}).to_list(100)
    
    stats = {
        "total_plots": len(plots),
        "plots_by_size": {"small": 0, "medium": 0, "large": 0},
        "total_buildings": 0,
        "buildings_by_category": {},
        "total_value": 0,
        "daily_income": 0
    }
    
    for plot in plots:
        stats["plots_by_size"][plot.get("plot_size", "small")] += 1
        stats["total_value"] += PLOT_SIZES.get(plot.get("plot_size", "small"), {}).get("cost", 0)
        
        for building in plot.get("buildings", []):
            stats["total_buildings"] += 1
            cat = building.get("category", "unknown")
            stats["buildings_by_category"][cat] = stats["buildings_by_category"].get(cat, 0) + 1
            
            prefab = BUILDING_PREFABS.get(cat, {}).get("prefabs", {}).get(building.get("prefab_id"), {})
            stats["total_value"] += prefab.get("cost", 0)
            stats["daily_income"] += prefab.get("income_per_day", 0)
    
    return stats
