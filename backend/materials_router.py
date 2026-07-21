"""
Extended Materials & Components System
=======================================
Additional crafting materials, components, and rare ingredients
for the AI Village building and crafting ecosystem.
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

router = APIRouter(prefix="/api/materials", tags=["Materials & Components"])

# ============ Extended Materials Catalog ============
MATERIALS = {
    # Basic Materials
    "timber": {
        "id": "timber",
        "name": "Timber",
        "description": "Basic building wood from the Shadow Grove",
        "category": "basic",
        "strength": 20,
        "durability": 30,
        "rarity": "common",
        "base_cost": 5,
        "gather_locations": ["shadow_grove", "wanderers_rest"],
        "color": "#8B4513",
        "weight": 2.0
    },
    "cobblestone": {
        "id": "cobblestone",
        "name": "Cobblestone",
        "description": "Sturdy stone quarried from village foundations",
        "category": "basic",
        "strength": 50,
        "durability": 60,
        "rarity": "common",
        "base_cost": 8,
        "gather_locations": ["village_square", "watchtower"],
        "color": "#696969",
        "weight": 4.0
    },
    "clay": {
        "id": "clay",
        "name": "Clay",
        "description": "Malleable earth for pottery and bricks",
        "category": "basic",
        "strength": 15,
        "durability": 25,
        "rarity": "common",
        "base_cost": 3,
        "gather_locations": ["wanderers_rest", "shadow_grove"],
        "color": "#B87333",
        "weight": 3.0
    },
    "sand": {
        "id": "sand",
        "name": "Sand",
        "description": "Fine particles for glass and mortar",
        "category": "basic",
        "strength": 5,
        "durability": 10,
        "rarity": "common",
        "base_cost": 2,
        "gather_locations": ["outer_realms"],
        "color": "#F4D03F",
        "weight": 2.5
    },
    
    # Metal Materials
    "iron_ore": {
        "id": "iron_ore",
        "name": "Iron Ore",
        "description": "Raw iron extracted from the Ember Forge mines",
        "category": "metal",
        "strength": 60,
        "durability": 50,
        "rarity": "uncommon",
        "base_cost": 15,
        "gather_locations": ["the_forge"],
        "color": "#434343",
        "weight": 5.0,
        "requires_processing": True,
        "processed_into": "forged_iron"
    },
    "forged_iron": {
        "id": "forged_iron",
        "name": "Forged Iron",
        "description": "Refined iron ready for construction",
        "category": "metal",
        "strength": 75,
        "durability": 65,
        "rarity": "uncommon",
        "base_cost": 30,
        "gather_locations": [],
        "color": "#555555",
        "weight": 4.0,
        "crafted_from": {"iron_ore": 2, "charcoal": 1}
    },
    "steel": {
        "id": "steel",
        "name": "Steel",
        "description": "Hardened metal alloy of exceptional quality",
        "category": "metal",
        "strength": 90,
        "durability": 85,
        "rarity": "rare",
        "base_cost": 75,
        "gather_locations": [],
        "color": "#71797E",
        "weight": 4.5,
        "crafted_from": {"forged_iron": 2, "carbon_dust": 1}
    },
    "mithril": {
        "id": "mithril",
        "name": "Mithril",
        "description": "Legendary lightweight metal with magical properties",
        "category": "metal",
        "strength": 120,
        "durability": 95,
        "rarity": "legendary",
        "base_cost": 500,
        "gather_locations": ["outer_realms"],
        "color": "#C0C0C0",
        "weight": 1.5,
        "magical_properties": {"weight_reduction": 0.5, "magic_conductivity": 1.5}
    },
    "adamantine": {
        "id": "adamantine",
        "name": "Adamantine",
        "description": "The hardest known material, nearly indestructible",
        "category": "metal",
        "strength": 150,
        "durability": 100,
        "rarity": "mythic",
        "base_cost": 2000,
        "gather_locations": ["outer_realms"],
        "color": "#1C1C1C",
        "weight": 8.0,
        "magical_properties": {"damage_reduction": 0.25}
    },
    
    # Crystals & Gems
    "echo_crystal": {
        "id": "echo_crystal",
        "name": "Echo Crystal",
        "description": "Mystical crystals resonating with ancient power",
        "category": "crystal",
        "strength": 40,
        "durability": 80,
        "rarity": "rare",
        "base_cost": 100,
        "gather_locations": ["oracle_sanctum", "ancient_library"],
        "color": "#00CED1",
        "weight": 0.5,
        "magical_properties": {"mana_storage": 50, "spell_amplification": 1.1}
    },
    "void_obsidian": {
        "id": "void_obsidian",
        "name": "Void Obsidian",
        "description": "Black glass from the deepest shadows",
        "category": "crystal",
        "strength": 95,
        "durability": 90,
        "rarity": "legendary",
        "base_cost": 300,
        "gather_locations": ["watchtower"],
        "color": "#1a1a2e",
        "weight": 3.0,
        "magical_properties": {"shadow_affinity": 2.0, "demon_resistance": 0.5}
    },
    "sunstone": {
        "id": "sunstone",
        "name": "Sunstone",
        "description": "A warm gem that glows with inner light",
        "category": "crystal",
        "strength": 35,
        "durability": 60,
        "rarity": "rare",
        "base_cost": 150,
        "gather_locations": ["village_square"],
        "color": "#FFD700",
        "weight": 0.3,
        "magical_properties": {"light_generation": True, "holy_damage": 1.2}
    },
    "moonpearl": {
        "id": "moonpearl",
        "name": "Moonpearl",
        "description": "Iridescent pearl that shifts with lunar phases",
        "category": "crystal",
        "strength": 20,
        "durability": 70,
        "rarity": "rare",
        "base_cost": 200,
        "gather_locations": ["oracle_sanctum"],
        "color": "#E6E6FA",
        "weight": 0.2,
        "magical_properties": {"divination_bonus": 1.3, "night_vision": True}
    },
    "bloodstone": {
        "id": "bloodstone",
        "name": "Bloodstone",
        "description": "Dark red gem pulsing with life energy",
        "category": "crystal",
        "strength": 45,
        "durability": 55,
        "rarity": "epic",
        "base_cost": 350,
        "gather_locations": ["shadow_grove"],
        "color": "#8B0000",
        "weight": 0.4,
        "magical_properties": {"life_steal": 0.05, "blood_magic": 1.5}
    },
    
    # Organic Materials
    "ancient_bark": {
        "id": "ancient_bark",
        "name": "Ancient Bark",
        "description": "Bark from millennium-old trees with natural enchantments",
        "category": "organic",
        "strength": 30,
        "durability": 45,
        "rarity": "uncommon",
        "base_cost": 25,
        "gather_locations": ["shadow_grove"],
        "color": "#3D2914",
        "weight": 1.5,
        "magical_properties": {"nature_affinity": 1.2}
    },
    "ether_silk": {
        "id": "ether_silk",
        "name": "Ether Silk",
        "description": "Threads spun from ethereal plane essence",
        "category": "organic",
        "strength": 15,
        "durability": 40,
        "rarity": "rare",
        "base_cost": 180,
        "gather_locations": ["outer_realms"],
        "color": "#E0FFFF",
        "weight": 0.1,
        "magical_properties": {"magic_resistance": 0.15, "lightweight": True}
    },
    "dragon_scale": {
        "id": "dragon_scale",
        "name": "Dragon Scale",
        "description": "Shed scale from ancient dragons",
        "category": "organic",
        "strength": 110,
        "durability": 95,
        "rarity": "legendary",
        "base_cost": 800,
        "gather_locations": [],
        "color": "#228B22",
        "weight": 2.0,
        "magical_properties": {"fire_immunity": True, "fear_aura": True},
        "drop_source": "dragons"
    },
    "phoenix_feather": {
        "id": "phoenix_feather",
        "name": "Phoenix Feather",
        "description": "Flame-touched feather that never burns",
        "category": "organic",
        "strength": 10,
        "durability": 100,
        "rarity": "mythic",
        "base_cost": 1500,
        "gather_locations": [],
        "color": "#FF4500",
        "weight": 0.05,
        "magical_properties": {"rebirth_chance": 0.1, "fire_immunity": True},
        "drop_source": "phoenix"
    },
    
    # Magical Essences
    "mana_essence": {
        "id": "mana_essence",
        "name": "Mana Essence",
        "description": "Concentrated magical energy",
        "category": "essence",
        "strength": 0,
        "durability": 0,
        "rarity": "uncommon",
        "base_cost": 50,
        "gather_locations": ["oracle_sanctum", "ancient_library"],
        "color": "#9400D3",
        "weight": 0.0,
        "magical_properties": {"mana_restore": 25}
    },
    "shadow_essence": {
        "id": "shadow_essence",
        "name": "Shadow Essence",
        "description": "Darkness given physical form",
        "category": "essence",
        "strength": 0,
        "durability": 0,
        "rarity": "rare",
        "base_cost": 120,
        "gather_locations": ["shadow_grove"],
        "color": "#2F2F4F",
        "weight": 0.0,
        "magical_properties": {"stealth_bonus": 1.3, "shadow_magic": 1.2}
    },
    "holy_essence": {
        "id": "holy_essence",
        "name": "Holy Essence",
        "description": "Divine light condensed into pure form",
        "category": "essence",
        "strength": 0,
        "durability": 0,
        "rarity": "epic",
        "base_cost": 250,
        "gather_locations": ["oracle_sanctum"],
        "color": "#FFFFFF",
        "weight": 0.0,
        "magical_properties": {"demon_damage": 2.0, "healing_boost": 1.5}
    },
    "chaos_essence": {
        "id": "chaos_essence",
        "name": "Chaos Essence",
        "description": "Unstable energy from the void between worlds",
        "category": "essence",
        "strength": 0,
        "durability": 0,
        "rarity": "mythic",
        "base_cost": 600,
        "gather_locations": ["outer_realms"],
        "color": "#FF00FF",
        "weight": 0.0,
        "magical_properties": {"random_effect": True, "chaos_magic": 2.0},
        "volatile": True
    },
    
    # Alchemical Components
    "charcoal": {
        "id": "charcoal",
        "name": "Charcoal",
        "description": "Burned wood for fuel and smelting",
        "category": "alchemical",
        "strength": 5,
        "durability": 5,
        "rarity": "common",
        "base_cost": 4,
        "gather_locations": ["the_forge"],
        "color": "#36454F",
        "weight": 0.5,
        "crafted_from": {"timber": 2}
    },
    "carbon_dust": {
        "id": "carbon_dust",
        "name": "Carbon Dust",
        "description": "Fine powder for steel making",
        "category": "alchemical",
        "strength": 0,
        "durability": 0,
        "rarity": "uncommon",
        "base_cost": 20,
        "gather_locations": [],
        "color": "#1C1C1C",
        "weight": 0.1,
        "crafted_from": {"charcoal": 5}
    },
    "philosophers_salt": {
        "id": "philosophers_salt",
        "name": "Philosopher's Salt",
        "description": "Purified salt for transmutation",
        "category": "alchemical",
        "strength": 0,
        "durability": 0,
        "rarity": "rare",
        "base_cost": 80,
        "gather_locations": [],
        "color": "#FAFAD2",
        "weight": 0.2,
        "crafted_from": {"sand": 10, "mana_essence": 1}
    },
    "quicksilver": {
        "id": "quicksilver",
        "name": "Quicksilver",
        "description": "Liquid metal for enchanting",
        "category": "alchemical",
        "strength": 0,
        "durability": 0,
        "rarity": "rare",
        "base_cost": 100,
        "gather_locations": ["the_forge"],
        "color": "#C0C0C0",
        "weight": 1.0,
        "magical_properties": {"enchanting_bonus": 1.25}
    },
    "demon_ichor": {
        "id": "demon_ichor",
        "name": "Demon Ichor",
        "description": "Black blood of demons, extremely dangerous",
        "category": "alchemical",
        "strength": 0,
        "durability": 0,
        "rarity": "epic",
        "base_cost": 400,
        "gather_locations": [],
        "color": "#301934",
        "weight": 0.5,
        "magical_properties": {"corruption": 0.1, "dark_magic": 1.8},
        "drop_source": "demons",
        "volatile": True
    }
}

# ============ Building Components ============
COMPONENTS = {
    # Structural Components
    "wooden_beam": {
        "id": "wooden_beam",
        "name": "Wooden Beam",
        "description": "Support beam for buildings",
        "category": "structural",
        "crafting_recipe": {"timber": 4},
        "crafting_skill": "engineering",
        "min_skill_level": 1,
        "produces": 2,
        "base_cost": 15
    },
    "stone_block": {
        "id": "stone_block",
        "name": "Stone Block",
        "description": "Carved stone for walls and foundations",
        "category": "structural",
        "crafting_recipe": {"cobblestone": 4},
        "crafting_skill": "engineering",
        "min_skill_level": 1,
        "produces": 2,
        "base_cost": 20
    },
    "brick": {
        "id": "brick",
        "name": "Brick",
        "description": "Fired clay brick",
        "category": "structural",
        "crafting_recipe": {"clay": 2, "charcoal": 1},
        "crafting_skill": "engineering",
        "min_skill_level": 2,
        "produces": 4,
        "base_cost": 12
    },
    "glass_pane": {
        "id": "glass_pane",
        "name": "Glass Pane",
        "description": "Clear glass for windows",
        "category": "structural",
        "crafting_recipe": {"sand": 4, "charcoal": 2},
        "crafting_skill": "engineering",
        "min_skill_level": 3,
        "produces": 2,
        "base_cost": 25
    },
    "iron_nail": {
        "id": "iron_nail",
        "name": "Iron Nail",
        "description": "Fasteners for construction",
        "category": "structural",
        "crafting_recipe": {"forged_iron": 1},
        "crafting_skill": "smithing",
        "min_skill_level": 1,
        "produces": 20,
        "base_cost": 5
    },
    "steel_beam": {
        "id": "steel_beam",
        "name": "Steel Beam",
        "description": "Reinforced support for large structures",
        "category": "structural",
        "crafting_recipe": {"steel": 3},
        "crafting_skill": "smithing",
        "min_skill_level": 5,
        "produces": 1,
        "base_cost": 250
    },
    
    # Magical Components
    "rune_stone": {
        "id": "rune_stone",
        "name": "Rune Stone",
        "description": "Stone inscribed with magical runes",
        "category": "magical",
        "crafting_recipe": {"cobblestone": 2, "mana_essence": 1},
        "crafting_skill": "enchanting",
        "min_skill_level": 3,
        "produces": 1,
        "base_cost": 100,
        "magical_properties": {"mana_storage": 20}
    },
    "ward_crystal": {
        "id": "ward_crystal",
        "name": "Ward Crystal",
        "description": "Defensive crystal that repels evil",
        "category": "magical",
        "crafting_recipe": {"echo_crystal": 1, "holy_essence": 1},
        "crafting_skill": "enchanting",
        "min_skill_level": 5,
        "produces": 1,
        "base_cost": 400,
        "magical_properties": {"demon_ward": True, "protection_radius": 10}
    },
    "mana_conduit": {
        "id": "mana_conduit",
        "name": "Mana Conduit",
        "description": "Channels magical energy through structures",
        "category": "magical",
        "crafting_recipe": {"forged_iron": 2, "echo_crystal": 2, "quicksilver": 1},
        "crafting_skill": "enchanting",
        "min_skill_level": 7,
        "produces": 1,
        "base_cost": 500,
        "magical_properties": {"mana_transfer": 5}
    },
    "shadow_anchor": {
        "id": "shadow_anchor",
        "name": "Shadow Anchor",
        "description": "Binds shadow magic to a location",
        "category": "magical",
        "crafting_recipe": {"void_obsidian": 2, "shadow_essence": 2},
        "crafting_skill": "enchanting",
        "min_skill_level": 8,
        "produces": 1,
        "base_cost": 700,
        "magical_properties": {"shadow_binding": True, "concealment": 1.5}
    },
    
    # Decorative Components
    "ornate_tile": {
        "id": "ornate_tile",
        "name": "Ornate Tile",
        "description": "Decorated floor tile",
        "category": "decorative",
        "crafting_recipe": {"clay": 4, "sand": 2},
        "crafting_skill": "artistry",
        "min_skill_level": 2,
        "produces": 6,
        "base_cost": 18
    },
    "stained_glass": {
        "id": "stained_glass",
        "name": "Stained Glass",
        "description": "Colorful decorative window",
        "category": "decorative",
        "crafting_recipe": {"glass_pane": 2, "mana_essence": 1},
        "crafting_skill": "artistry",
        "min_skill_level": 5,
        "produces": 1,
        "base_cost": 120
    },
    "gold_trim": {
        "id": "gold_trim",
        "name": "Gold Trim",
        "description": "Luxurious golden decoration",
        "category": "decorative",
        "crafting_recipe": {"sunstone": 1},
        "crafting_skill": "artistry",
        "min_skill_level": 6,
        "produces": 4,
        "base_cost": 200
    },
    
    # Mechanical Components
    "gear": {
        "id": "gear",
        "name": "Gear",
        "description": "Mechanical cog for machinery",
        "category": "mechanical",
        "crafting_recipe": {"forged_iron": 2},
        "crafting_skill": "engineering",
        "min_skill_level": 4,
        "produces": 3,
        "base_cost": 40
    },
    "spring": {
        "id": "spring",
        "name": "Spring",
        "description": "Coiled metal for mechanisms",
        "category": "mechanical",
        "crafting_recipe": {"steel": 1},
        "crafting_skill": "engineering",
        "min_skill_level": 5,
        "produces": 2,
        "base_cost": 50
    },
    "clockwork_core": {
        "id": "clockwork_core",
        "name": "Clockwork Core",
        "description": "Complex mechanism for automatons",
        "category": "mechanical",
        "crafting_recipe": {"gear": 10, "spring": 5, "mithril": 1},
        "crafting_skill": "engineering",
        "min_skill_level": 9,
        "produces": 1,
        "base_cost": 1500,
        "magical_properties": {"automation": True}
    }
}

# ============ Material Rarity Colors ============
RARITY_COLORS = {
    "common": "#FFFFFF",
    "uncommon": "#1EFF00",
    "rare": "#0070DD",
    "epic": "#A335EE",
    "legendary": "#FF8000",
    "mythic": "#FF0000"
}


# ============ API Endpoints ============

@router.get("/list")
async def list_all_materials():
    """Get all available materials."""
    return {
        "materials": MATERIALS,
        "total": len(MATERIALS),
        "categories": list(set(m["category"] for m in MATERIALS.values())),
        "rarity_colors": RARITY_COLORS
    }


@router.get("/components")
async def list_all_components():
    """Get all craftable components."""
    return {
        "components": COMPONENTS,
        "total": len(COMPONENTS),
        "categories": list(set(c["category"] for c in COMPONENTS.values()))
    }


@router.get("/{material_id}")
async def get_material(material_id: str):
    """Get details of a specific material."""
    if material_id not in MATERIALS:
        raise HTTPException(status_code=404, detail="Material not found")
    return MATERIALS[material_id]


@router.get("/component/{component_id}")
async def get_component(component_id: str):
    """Get details of a specific component."""
    if component_id not in COMPONENTS:
        raise HTTPException(status_code=404, detail="Component not found")
    return COMPONENTS[component_id]


@router.get("/by-location/{location_id}")
async def get_materials_by_location(location_id: str):
    """Get all materials that can be gathered at a location."""
    available = [
        m for m in MATERIALS.values()
        if location_id in m.get("gather_locations", [])
    ]
    return {
        "location_id": location_id,
        "materials": available,
        "count": len(available)
    }


@router.get("/by-rarity/{rarity}")
async def get_materials_by_rarity(rarity: str):
    """Get all materials of a specific rarity."""
    if rarity not in RARITY_COLORS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid rarity. Valid: {list(RARITY_COLORS.keys())}"
        )
    
    matching = [m for m in MATERIALS.values() if m.get("rarity") == rarity]
    return {
        "rarity": rarity,
        "color": RARITY_COLORS[rarity],
        "materials": matching,
        "count": len(matching)
    }


@router.get("/crafting-tree/{material_id}")
async def get_crafting_tree(material_id: str):
    """Get the full crafting tree for a material or component."""
    def build_tree(item_id: str, depth: int = 0) -> Dict:
        if depth > 10:  # Prevent infinite loops
            return {"id": item_id, "error": "Max depth reached"}
        
        # Check materials first
        if item_id in MATERIALS:
            mat = MATERIALS[item_id]
            result = {
                "id": item_id,
                "name": mat["name"],
                "type": "material",
                "rarity": mat.get("rarity"),
                "base_cost": mat.get("base_cost", 0)
            }
            
            if "crafted_from" in mat:
                result["requires"] = [
                    {
                        "item": build_tree(req_id, depth + 1),
                        "quantity": qty
                    }
                    for req_id, qty in mat["crafted_from"].items()
                ]
            elif mat.get("gather_locations"):
                result["source"] = "gatherable"
                result["locations"] = mat["gather_locations"]
            elif mat.get("drop_source"):
                result["source"] = "drop"
                result["drop_from"] = mat["drop_source"]
            
            return result
        
        # Check components
        if item_id in COMPONENTS:
            comp = COMPONENTS[item_id]
            return {
                "id": item_id,
                "name": comp["name"],
                "type": "component",
                "category": comp.get("category"),
                "skill_required": comp.get("crafting_skill"),
                "min_level": comp.get("min_skill_level"),
                "produces": comp.get("produces", 1),
                "requires": [
                    {
                        "item": build_tree(req_id, depth + 1),
                        "quantity": qty
                    }
                    for req_id, qty in comp.get("crafting_recipe", {}).items()
                ]
            }
        
        return {"id": item_id, "error": "Not found"}
    
    tree = build_tree(material_id)
    return {"crafting_tree": tree}


class GatherRequest(BaseModel):
    user_id: str
    material_id: str
    location_id: str
    quantity: int = Field(default=1, ge=1, le=100)


@router.post("/gather")
async def gather_material(request: GatherRequest):
    """Attempt to gather a material at a location."""
    if request.material_id not in MATERIALS:
        raise HTTPException(status_code=404, detail="Material not found")
    
    material = MATERIALS[request.material_id]
    
    if request.location_id not in material.get("gather_locations", []):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot gather {material['name']} at this location"
        )
    
    # Add to user inventory
    inventory_update = {
        "$inc": {f"materials.{request.material_id}": request.quantity}
    }
    
    await db.user_inventories.update_one(
        {"user_id": request.user_id},
        inventory_update,
        upsert=True
    )
    
    return {
        "success": True,
        "gathered": {
            "material": material["name"],
            "quantity": request.quantity,
            "rarity": material["rarity"]
        },
        "message": f"Gathered {request.quantity}x {material['name']}"
    }


class CraftRequest(BaseModel):
    user_id: str
    component_id: str
    quantity: int = Field(default=1, ge=1, le=10)


@router.post("/craft")
async def craft_component(request: CraftRequest):
    """Craft a component from materials."""
    if request.component_id not in COMPONENTS:
        raise HTTPException(status_code=404, detail="Component not found")
    
    component = COMPONENTS[request.component_id]
    recipe = component.get("crafting_recipe", {})
    
    # Check user inventory
    inventory = await db.user_inventories.find_one(
        {"user_id": request.user_id},
        {"_id": 0}
    )
    
    if not inventory:
        raise HTTPException(status_code=400, detail="No inventory found")
    
    user_materials = inventory.get("materials", {})
    
    # Check if user has required materials
    missing = []
    for mat_id, qty_needed in recipe.items():
        total_needed = qty_needed * request.quantity
        have = user_materials.get(mat_id, 0)
        if have < total_needed:
            mat_name = MATERIALS.get(mat_id, {}).get("name", mat_id)
            missing.append(f"{mat_name}: need {total_needed}, have {have}")
    
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing materials: {', '.join(missing)}"
        )
    
    # Deduct materials and add component
    updates = {}
    for mat_id, qty_needed in recipe.items():
        updates[f"materials.{mat_id}"] = -(qty_needed * request.quantity)
    
    produced = component.get("produces", 1) * request.quantity
    updates[f"components.{request.component_id}"] = produced
    
    await db.user_inventories.update_one(
        {"user_id": request.user_id},
        {"$inc": updates}
    )
    
    return {
        "success": True,
        "crafted": {
            "component": component["name"],
            "quantity": produced
        },
        "materials_used": {
            MATERIALS.get(m, {}).get("name", m): q * request.quantity
            for m, q in recipe.items()
        }
    }


@router.get("/inventory/{user_id}")
async def get_user_inventory(user_id: str):
    """Get a user's material and component inventory."""
    inventory = await db.user_inventories.find_one(
        {"user_id": user_id},
        {"_id": 0}
    )
    
    if not inventory:
        return {"user_id": user_id, "materials": {}, "components": {}}
    
    # Enrich with material/component details
    materials = {}
    for mat_id, qty in inventory.get("materials", {}).items():
        if mat_id in MATERIALS:
            materials[mat_id] = {
                **MATERIALS[mat_id],
                "quantity": qty
            }
    
    components = {}
    for comp_id, qty in inventory.get("components", {}).items():
        if comp_id in COMPONENTS:
            components[comp_id] = {
                **COMPONENTS[comp_id],
                "quantity": qty
            }
    
    return {
        "user_id": user_id,
        "materials": materials,
        "components": components,
        "total_materials": sum(inventory.get("materials", {}).values()),
        "total_components": sum(inventory.get("components", {}).values())
    }
