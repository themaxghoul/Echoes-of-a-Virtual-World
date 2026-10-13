# Crafting System — Minecraft/Terraria recipe structure with Sims-depth item specs.
# Materials come from user_profiles.materials; stations must be crafted first.

import uuid
import random
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from shared_db import db

crafting_router = APIRouter(prefix="/crafting", tags=["crafting"])
logger = logging.getLogger(__name__)

QUALITY_TIERS = [
    ("crude", 0.80, "Rough edges and uneven joints — functional, barely."),
    ("common", 1.00, "Solid everyday workmanship."),
    ("fine", 1.15, "Carefully finished with visible attention to detail."),
    ("superior", 1.35, "Exceptional craftsmanship — joints seamless, finish flawless."),
    ("masterwork", 1.60, "A once-in-a-career piece. Artisans will study this."),
]

RECIPES = {
    # ---- Stations (craft these to unlock advanced recipes) ----
    "workbench": {"name": "Workbench", "category": "station", "station": None,
                  "materials": {"wood": 12}, "base_durability": 200, "weight_kg": 34.0,
                  "desc": "Sturdy crafting surface. Unlocks workbench recipes."},
    "forge": {"name": "Ember Forge", "category": "station", "station": "workbench",
              "materials": {"stone": 16, "iron": 6}, "base_durability": 400, "weight_kg": 180.0,
              "desc": "High-heat metalworking station. Unlocks forge recipes."},
    "lab": {"name": "Field Laboratory", "category": "station", "station": "workbench",
            "materials": {"stone": 10, "iron": 8, "crystal": 3}, "base_durability": 300, "weight_kg": 95.0,
            "desc": "Scientific instrumentation bench. Unlocks experimental recipes."},
    # ---- Tools ----
    "wooden_hammer": {"name": "Wooden Hammer", "category": "tool", "station": None,
                      "materials": {"wood": 4}, "base_durability": 60, "weight_kg": 1.2,
                      "desc": "Basic builder's mallet."},
    "stone_pickaxe": {"name": "Stone Pickaxe", "category": "tool", "station": "workbench",
                      "materials": {"wood": 2, "stone": 6}, "base_durability": 110, "weight_kg": 2.8,
                      "desc": "Breaks rock, slowly but reliably."},
    "iron_chisel": {"name": "Iron Chisel Set", "category": "tool", "station": "forge",
                    "materials": {"iron": 3, "wood": 1}, "base_durability": 180, "weight_kg": 0.9,
                    "desc": "Precision carving instruments."},
    # ---- Furniture (Sims-style comfort specs) ----
    "oak_chair": {"name": "Oak Chair", "category": "furniture", "station": "workbench",
                  "materials": {"wood": 8}, "base_durability": 90, "weight_kg": 6.5,
                  "desc": "Hand-joined seat with a gentle recline."},
    "carved_table": {"name": "Carved Great Table", "category": "furniture", "station": "workbench",
                     "materials": {"wood": 14, "iron": 2}, "base_durability": 150, "weight_kg": 42.0,
                     "desc": "Seats eight. Carvings tell the village's founding story."},
    "crystal_lamp": {"name": "Crystal Resonance Lamp", "category": "furniture", "station": "forge",
                     "materials": {"crystal": 2, "iron": 3}, "base_durability": 120, "weight_kg": 3.1,
                     "desc": "Soft light that shifts hue with the day-night cycle."},
    # ---- Scientific instruments ----
    "alchemist_burner": {"name": "Alchemist's Burner", "category": "scientific", "station": "lab",
                         "materials": {"iron": 5, "crystal": 1}, "base_durability": 140, "weight_kg": 4.4,
                         "desc": "Controlled flame for reagent work. +precision experiments."},
    "resonance_scope": {"name": "Resonance Scope", "category": "scientific", "station": "lab",
                        "materials": {"crystal": 4, "iron": 6}, "base_durability": 160, "weight_kg": 7.8,
                        "desc": "Peers into quantum signatures of nearby matter."},
    "quantum_capacitor": {"name": "Quantum Capacitor", "category": "scientific", "station": "lab",
                          "materials": {"crystal": 8, "iron": 10}, "base_durability": 220, "weight_kg": 12.5,
                          "desc": "Stores extracted entropy. The pinnacle of field science."},
    # ---- Structure kits ----
    "reinforced_wall_kit": {"name": "Reinforced Wall Kit", "category": "structure", "station": "workbench",
                            "materials": {"stone": 20, "iron": 4}, "base_durability": 500, "weight_kg": 310.0,
                            "desc": "Prefab defensive wall section."},
    "observatory_dome_kit": {"name": "Observatory Dome Kit", "category": "structure", "station": "lab",
                             "materials": {"stone": 30, "iron": 12, "crystal": 6}, "base_durability": 800, "weight_kg": 540.0,
                             "desc": "Crowning glory for any scientific settlement."},
}


class CraftRequest(BaseModel):
    user_id: str
    recipe_id: str


async def _get_materials(user_id: str):
    profile = await db.user_profiles.find_one(
        {"id": user_id}, {"_id": 0, "materials": 1, "is_transcendent": 1}
    ) or {}
    transcendent = bool(profile.get("is_transcendent"))
    raw = profile.get("materials", {}) or {}
    # Transcendent accounts (Sirix-1) have immeasurable resources — treat as infinite
    if transcendent:
        return {k: 999999 for k in (raw.keys() or ["wood", "stone", "iron", "crystal", "obsidian"])}, True
    # Defensive: coerce None values to 0 (seed data may contain None)
    return {k: (v if isinstance(v, (int, float)) else 0) for k, v in raw.items()}, False


async def _owned_stations(user_id: str) -> set:
    rows = await db.crafted_items.find(
        {"owner_id": user_id, "category": "station"}, {"_id": 0, "recipe_id": 1}
    ).to_list(50)
    return {r["recipe_id"] for r in rows}


@crafting_router.get("/recipes/{user_id}")
async def list_recipes(user_id: str):
    materials, transcendent = await _get_materials(user_id)
    stations = await _owned_stations(user_id)
    out = []
    for rid, r in RECIPES.items():
        missing = {} if transcendent else {m: need - materials.get(m, 0) for m, need in r["materials"].items() if materials.get(m, 0) < need}
        station_ok = r["station"] is None or r["station"] in stations
        out.append({
            "recipe_id": rid,
            **{k: r[k] for k in ("name", "category", "station", "materials", "base_durability", "weight_kg", "desc")},
            "craftable": not missing and station_ok,
            "missing_materials": missing,
            "station_owned": station_ok,
        })
    return {"recipes": out, "player_materials": materials, "stations_owned": sorted(stations), "transcendent": transcendent}


@crafting_router.post("/craft")
async def craft(req: CraftRequest):
    recipe = RECIPES.get(req.recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Unknown recipe")
    materials, transcendent = await _get_materials(req.user_id)
    missing = {} if transcendent else {m: need - materials.get(m, 0) for m, need in recipe["materials"].items() if materials.get(m, 0) < need}
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing materials: {missing}")
    if recipe["station"] and recipe["station"] not in await _owned_stations(req.user_id):
        raise HTTPException(status_code=400, detail=f"Requires a {RECIPES[recipe['station']]['name']} — craft one first")

    # Deduct materials (transcendent accounts have infinite resources — no deduction)
    new_materials = dict(materials)
    if not transcendent:
        for m, need in recipe["materials"].items():
            new_materials[m] = materials[m] - need
        await db.user_profiles.update_one({"id": req.user_id}, {"$set": {"materials": new_materials}})

    # Quality roll — surplus materials improve odds (Sims-style craftsmanship variance)
    surplus = sum(materials.get(m, 0) / max(need, 1) for m, need in recipe["materials"].items()) / len(recipe["materials"])
    bonus = min(0.25, (surplus - 1) * 0.04)
    roll = random.random() + bonus
    if roll < 0.15: tier = QUALITY_TIERS[0]
    elif roll < 0.60: tier = QUALITY_TIERS[1]
    elif roll < 0.85: tier = QUALITY_TIERS[2]
    elif roll < 0.97: tier = QUALITY_TIERS[3]
    else: tier = QUALITY_TIERS[4]
    quality, mult, flavor = tier

    item = {
        "item_id": str(uuid.uuid4()),
        "recipe_id": req.recipe_id,
        "owner_id": req.user_id,
        "name": recipe["name"],
        "category": recipe["category"],
        "quality": quality,
        "specs": {
            "durability": round(recipe["base_durability"] * mult * random.uniform(0.95, 1.05)),
            "max_durability": round(recipe["base_durability"] * mult * 1.05),
            "weight_kg": round(recipe["weight_kg"] * random.uniform(0.97, 1.03), 2),
            "aesthetics": round(min(10, 3 + mult * 3 + random.uniform(0, 1.5)), 1),
            "utility": round(min(10, 4 + mult * 2.5 + random.uniform(0, 1.0)), 1),
            "comfort": round(min(10, 2 + mult * 3 + random.uniform(0, 2)), 1) if recipe["category"] == "furniture" else None,
            "precision": round(min(10, 3 + mult * 3 + random.uniform(0, 1.2)), 1) if recipe["category"] == "scientific" else None,
            "material_composition": recipe["materials"],
        },
        "flavor": flavor,
        "crafted_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.crafted_items.insert_one(dict(item))

    # Infrastructure creation feeds the hybrid economy (XR spatial work)
    mining = None
    try:
        from hybrid_economy_router import record_contribution
        mining = await record_contribution(req.user_id, "xr_spatial", 8.0, source="crafting",
                                           meta={"recipe": req.recipe_id, "quality": quality})
    except Exception as e:
        logger.debug(f"Crafting economy yield skipped: {e}")

    return {"crafted": True, "item": item, "materials_remaining": new_materials, "economy_yield": mining}


@crafting_router.get("/items/{user_id}")
async def crafted_items(user_id: str, limit: int = 100):
    items = await db.crafted_items.find({"owner_id": user_id}, {"_id": 0}) \
        .sort("crafted_at", -1).to_list(min(limit, 200))
    return {"items": items, "count": len(items)}
