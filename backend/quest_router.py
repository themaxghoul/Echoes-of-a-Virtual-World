# Quest System - Gold & Reputation Rewards
# Quests for story progression, reputation building, and gold earnings

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone, timedelta
import uuid
import logging
import random

quest_router = APIRouter(prefix="/quests", tags=["quests"])

logger = logging.getLogger(__name__)

# ============ QUEST CATEGORIES ============

QUEST_CATEGORIES = {
    "story": {
        "name": "Story Quests",
        "description": "Main storyline progression",
        "icon": "book",
        "color": "#F59E0B"
    },
    "faction": {
        "name": "Faction Quests",
        "description": "Build reputation with factions",
        "icon": "flag",
        "color": "#3B82F6"
    },
    "daily": {
        "name": "Daily Tasks",
        "description": "Repeatable daily quests",
        "icon": "calendar",
        "color": "#22C55E"
    },
    "exploration": {
        "name": "Exploration",
        "description": "Discover new areas and secrets",
        "icon": "compass",
        "color": "#8B5CF6"
    },
    "combat": {
        "name": "Combat Quests",
        "description": "Battle challenges and bounties",
        "icon": "sword",
        "color": "#EF4444"
    },
    "crafting": {
        "name": "Crafting Orders",
        "description": "Create items for NPCs",
        "icon": "hammer",
        "color": "#EC4899"
    },
    "social": {
        "name": "Social Quests",
        "description": "Help villagers and build relationships",
        "icon": "heart",
        "color": "#F472B6"
    }
}

# ============ FACTIONS ============

FACTIONS = {
    "merchants_guild": {
        "name": "Merchants Guild",
        "description": "Traders and economic powers",
        "icon": "coins",
        "color": "#F59E0B",
        "rep_tiers": {
            "hostile": {"min": -1000, "max": -100, "bonus": -0.5},
            "unfriendly": {"min": -100, "max": 0, "bonus": -0.2},
            "neutral": {"min": 0, "max": 500, "bonus": 0},
            "friendly": {"min": 500, "max": 2000, "bonus": 0.1},
            "honored": {"min": 2000, "max": 5000, "bonus": 0.2},
            "revered": {"min": 5000, "max": 10000, "bonus": 0.3},
            "exalted": {"min": 10000, "max": 999999, "bonus": 0.5}
        }
    },
    "adventurers_league": {
        "name": "Adventurers League",
        "description": "Heroes and explorers",
        "icon": "sword",
        "color": "#EF4444",
        "rep_tiers": {
            "hostile": {"min": -1000, "max": -100, "bonus": -0.5},
            "unfriendly": {"min": -100, "max": 0, "bonus": -0.2},
            "neutral": {"min": 0, "max": 500, "bonus": 0},
            "friendly": {"min": 500, "max": 2000, "bonus": 0.1},
            "honored": {"min": 2000, "max": 5000, "bonus": 0.2},
            "revered": {"min": 5000, "max": 10000, "bonus": 0.3},
            "exalted": {"min": 10000, "max": 999999, "bonus": 0.5}
        }
    },
    "mages_circle": {
        "name": "Mages Circle",
        "description": "Arcane scholars and spellcasters",
        "icon": "sparkles",
        "color": "#8B5CF6",
        "rep_tiers": {
            "hostile": {"min": -1000, "max": -100, "bonus": -0.5},
            "unfriendly": {"min": -100, "max": 0, "bonus": -0.2},
            "neutral": {"min": 0, "max": 500, "bonus": 0},
            "friendly": {"min": 500, "max": 2000, "bonus": 0.1},
            "honored": {"min": 2000, "max": 5000, "bonus": 0.2},
            "revered": {"min": 5000, "max": 10000, "bonus": 0.3},
            "exalted": {"min": 10000, "max": 999999, "bonus": 0.5}
        }
    },
    "craftsmen_union": {
        "name": "Craftsmen Union",
        "description": "Artisans and builders",
        "icon": "hammer",
        "color": "#F97316",
        "rep_tiers": {
            "hostile": {"min": -1000, "max": -100, "bonus": -0.5},
            "unfriendly": {"min": -100, "max": 0, "bonus": -0.2},
            "neutral": {"min": 0, "max": 500, "bonus": 0},
            "friendly": {"min": 500, "max": 2000, "bonus": 0.1},
            "honored": {"min": 2000, "max": 5000, "bonus": 0.2},
            "revered": {"min": 5000, "max": 10000, "bonus": 0.3},
            "exalted": {"min": 10000, "max": 999999, "bonus": 0.5}
        }
    },
    "nature_wardens": {
        "name": "Nature Wardens",
        "description": "Protectors of the wild",
        "icon": "leaf",
        "color": "#22C55E",
        "rep_tiers": {
            "hostile": {"min": -1000, "max": -100, "bonus": -0.5},
            "unfriendly": {"min": -100, "max": 0, "bonus": -0.2},
            "neutral": {"min": 0, "max": 500, "bonus": 0},
            "friendly": {"min": 500, "max": 2000, "bonus": 0.1},
            "honored": {"min": 2000, "max": 5000, "bonus": 0.2},
            "revered": {"min": 5000, "max": 10000, "bonus": 0.3},
            "exalted": {"min": 10000, "max": 999999, "bonus": 0.5}
        }
    },
    "shadow_network": {
        "name": "Shadow Network",
        "description": "Information brokers and rogues",
        "icon": "eye",
        "color": "#6B7280",
        "rep_tiers": {
            "hostile": {"min": -1000, "max": -100, "bonus": -0.5},
            "unfriendly": {"min": -100, "max": 0, "bonus": -0.2},
            "neutral": {"min": 0, "max": 500, "bonus": 0},
            "friendly": {"min": 500, "max": 2000, "bonus": 0.1},
            "honored": {"min": 2000, "max": 5000, "bonus": 0.2},
            "revered": {"min": 5000, "max": 10000, "bonus": 0.3},
            "exalted": {"min": 10000, "max": 999999, "bonus": 0.5}
        }
    }
}

# ============ QUEST TEMPLATES ============

QUEST_TEMPLATES = {
    # Daily Quests
    "gather_resources": {
        "category": "daily",
        "name": "Daily Gathering",
        "description": "Collect 10 resources from the wilds",
        "objectives": [{"type": "collect", "target": "any_resource", "count": 10}],
        "rewards": {"gold": 50, "exp": 25},
        "rep_reward": {"faction": None, "amount": 10},
        "time_limit_hours": 24,
        "repeatable": True,
        "cooldown_hours": 20
    },
    "defeat_monsters": {
        "category": "daily",
        "name": "Monster Hunt",
        "description": "Defeat 5 monsters threatening the village",
        "objectives": [{"type": "kill", "target": "any_monster", "count": 5}],
        "rewards": {"gold": 75, "exp": 40},
        "rep_reward": {"faction": "adventurers_league", "amount": 15},
        "time_limit_hours": 24,
        "repeatable": True,
        "cooldown_hours": 20
    },
    "help_villager": {
        "category": "social",
        "name": "Helping Hand",
        "description": "Assist a villager with their daily tasks",
        "objectives": [{"type": "interact", "target": "npc", "count": 1}],
        "rewards": {"gold": 30, "exp": 15},
        "rep_reward": {"faction": None, "amount": 20},
        "time_limit_hours": 24,
        "repeatable": True,
        "cooldown_hours": 20
    },
    
    # Faction Quests
    "merchant_delivery": {
        "category": "faction",
        "name": "Trade Route Delivery",
        "description": "Deliver goods to a distant merchant",
        "objectives": [{"type": "deliver", "target": "trade_goods", "destination": "merchant"}],
        "rewards": {"gold": 150, "exp": 50},
        "rep_reward": {"faction": "merchants_guild", "amount": 50},
        "time_limit_hours": 48,
        "repeatable": True,
        "cooldown_hours": 24
    },
    "bounty_hunt": {
        "category": "combat",
        "name": "Bounty: Dangerous Beast",
        "description": "Hunt down a dangerous creature terrorizing travelers",
        "objectives": [{"type": "kill", "target": "boss_monster", "count": 1}],
        "rewards": {"gold": 300, "exp": 100},
        "rep_reward": {"faction": "adventurers_league", "amount": 75},
        "time_limit_hours": 72,
        "repeatable": True,
        "cooldown_hours": 48
    },
    "magical_research": {
        "category": "faction",
        "name": "Arcane Research",
        "description": "Collect magical components for the Mages Circle",
        "objectives": [{"type": "collect", "target": "magical_component", "count": 5}],
        "rewards": {"gold": 200, "exp": 75},
        "rep_reward": {"faction": "mages_circle", "amount": 60},
        "time_limit_hours": 48,
        "repeatable": True,
        "cooldown_hours": 24
    },
    "craft_order": {
        "category": "crafting",
        "name": "Craftsmen Order",
        "description": "Fulfill a crafting order for the union",
        "objectives": [{"type": "craft", "target": "requested_item", "count": 3}],
        "rewards": {"gold": 175, "exp": 60},
        "rep_reward": {"faction": "craftsmen_union", "amount": 45},
        "time_limit_hours": 36,
        "repeatable": True,
        "cooldown_hours": 24
    },
    "nature_protection": {
        "category": "faction",
        "name": "Protect the Grove",
        "description": "Clear invasive creatures from a sacred grove",
        "objectives": [{"type": "clear_area", "target": "sacred_grove", "count": 1}],
        "rewards": {"gold": 125, "exp": 55},
        "rep_reward": {"faction": "nature_wardens", "amount": 55},
        "time_limit_hours": 48,
        "repeatable": True,
        "cooldown_hours": 24
    },
    
    # Exploration Quests
    "discover_location": {
        "category": "exploration",
        "name": "Uncharted Territory",
        "description": "Discover a new location on the map",
        "objectives": [{"type": "discover", "target": "new_location", "count": 1}],
        "rewards": {"gold": 100, "exp": 80},
        "rep_reward": {"faction": "adventurers_league", "amount": 30},
        "time_limit_hours": None,
        "repeatable": False,
        "cooldown_hours": None
    },
    "treasure_hunt": {
        "category": "exploration",
        "name": "Hidden Treasure",
        "description": "Find a hidden treasure chest",
        "objectives": [{"type": "find", "target": "treasure_chest", "count": 1}],
        "rewards": {"gold": 250, "exp": 40, "item": "random_rare"},
        "rep_reward": {"faction": None, "amount": 25},
        "time_limit_hours": None,
        "repeatable": True,
        "cooldown_hours": 48
    },
    
    # Story Quests (examples)
    "introduction_quest": {
        "category": "story",
        "name": "Welcome to the Village",
        "description": "Meet the village elder and learn about your new home",
        "objectives": [
            {"type": "interact", "target": "village_elder", "count": 1},
            {"type": "visit", "target": "village_center", "count": 1}
        ],
        "rewards": {"gold": 100, "exp": 50, "item": "starter_pack"},
        "rep_reward": {"faction": None, "amount": 50},
        "time_limit_hours": None,
        "repeatable": False,
        "is_intro": True,
        "next_quest": "first_steps"
    },
    "first_steps": {
        "category": "story",
        "name": "First Steps",
        "description": "Establish yourself in the village",
        "objectives": [
            {"type": "build", "target": "first_building", "count": 1},
            {"type": "earn", "target": "gold", "count": 100}
        ],
        "rewards": {"gold": 200, "exp": 100},
        "rep_reward": {"faction": "craftsmen_union", "amount": 25},
        "time_limit_hours": None,
        "repeatable": False,
        "prerequisite": "introduction_quest",
        "next_quest": "growing_influence"
    }
}

# ============ MODELS ============

class QuestAccept(BaseModel):
    user_id: str
    quest_template: str

class QuestProgress(BaseModel):
    user_id: str
    quest_id: str
    objective_index: int
    progress: int

class QuestComplete(BaseModel):
    user_id: str
    quest_id: str

# MongoDB reference
def get_db():
    from server import db
    return db

# ============ HELPER FUNCTIONS ============

def get_reputation_tier(faction_id: str, rep_amount: int) -> Dict[str, Any]:
    """Get the reputation tier for a faction"""
    if faction_id not in FACTIONS:
        return {"tier": "neutral", "bonus": 0}
    
    tiers = FACTIONS[faction_id]["rep_tiers"]
    for tier_name, tier_data in tiers.items():
        if tier_data["min"] <= rep_amount < tier_data["max"]:
            return {"tier": tier_name, "bonus": tier_data["bonus"], **tier_data}
    
    return {"tier": "neutral", "bonus": 0}

# ============ ENDPOINTS ============

@quest_router.get("/categories")
async def get_quest_categories():
    """Get all quest categories"""
    return {"categories": QUEST_CATEGORIES}

@quest_router.get("/factions")
async def get_factions():
    """Get all factions"""
    return {"factions": FACTIONS}

@quest_router.get("/available/{user_id}")
async def get_available_quests(user_id: str):
    """Get quests available to a user"""
    db = get_db()
    
    # Get user's completed quests
    completed = await db.completed_quests.find({
        "user_id": user_id
    }).to_list(500)
    
    completed_templates = {c["quest_template"] for c in completed}
    
    # Get active quests
    active = await db.active_quests.find({
        "user_id": user_id,
        "status": "active"
    }, {"_id": 0}).to_list(50)
    
    active_templates = {a["quest_template"] for a in active}
    
    # Get cooldowns
    cooldowns = await db.quest_cooldowns.find({
        "user_id": user_id,
        "available_at": {"$gt": datetime.now(timezone.utc).isoformat()}
    }).to_list(100)
    
    on_cooldown = {c["quest_template"] for c in cooldowns}
    
    # Filter available quests
    available = []
    for template_id, template in QUEST_TEMPLATES.items():
        # Skip if on cooldown
        if template_id in on_cooldown:
            continue
        
        # Skip if non-repeatable and completed
        if not template.get("repeatable", False) and template_id in completed_templates:
            continue
        
        # Skip if already active
        if template_id in active_templates:
            continue
        
        # Check prerequisites
        prereq = template.get("prerequisite")
        if prereq and prereq not in completed_templates:
            continue
        
        available.append({
            "template_id": template_id,
            **template
        })
    
    return {
        "user_id": user_id,
        "available_quests": available,
        "active_quests": active,
        "total_available": len(available)
    }

@quest_router.post("/accept")
async def accept_quest(data: QuestAccept):
    """Accept a quest"""
    db = get_db()
    
    if data.quest_template not in QUEST_TEMPLATES:
        raise HTTPException(status_code=404, detail="Quest not found")
    
    template = QUEST_TEMPLATES[data.quest_template]
    
    # Check if already active
    existing = await db.active_quests.find_one({
        "user_id": data.user_id,
        "quest_template": data.quest_template,
        "status": "active"
    })
    
    if existing:
        raise HTTPException(status_code=400, detail="Quest already active")
    
    # Check cooldown
    cooldown = await db.quest_cooldowns.find_one({
        "user_id": data.user_id,
        "quest_template": data.quest_template,
        "available_at": {"$gt": datetime.now(timezone.utc).isoformat()}
    })
    
    if cooldown:
        raise HTTPException(status_code=400, detail="Quest on cooldown")
    
    # Create active quest
    quest_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    expires_at = None
    if template.get("time_limit_hours"):
        expires_at = (now + timedelta(hours=template["time_limit_hours"])).isoformat()
    
    quest = {
        "quest_id": quest_id,
        "user_id": data.user_id,
        "quest_template": data.quest_template,
        "name": template["name"],
        "category": template["category"],
        "objectives": [
            {**obj, "current": 0, "completed": False}
            for obj in template["objectives"]
        ],
        "rewards": template["rewards"],
        "rep_reward": template.get("rep_reward"),
        "status": "active",
        "accepted_at": now.isoformat(),
        "expires_at": expires_at
    }
    
    await db.active_quests.insert_one(quest)
    quest.pop("_id", None)
    
    return {
        "success": True,
        "quest": quest
    }

@quest_router.post("/progress")
async def update_quest_progress(data: QuestProgress):
    """Update progress on a quest objective"""
    db = get_db()
    
    quest = await db.active_quests.find_one({
        "quest_id": data.quest_id,
        "user_id": data.user_id,
        "status": "active"
    })
    
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")
    
    if data.objective_index >= len(quest["objectives"]):
        raise HTTPException(status_code=400, detail="Invalid objective index")
    
    # Update progress
    objective = quest["objectives"][data.objective_index]
    new_progress = min(data.progress, objective.get("count", 1))
    completed = new_progress >= objective.get("count", 1)
    
    await db.active_quests.update_one(
        {"quest_id": data.quest_id},
        {
            "$set": {
                f"objectives.{data.objective_index}.current": new_progress,
                f"objectives.{data.objective_index}.completed": completed
            }
        }
    )
    
    # Check if all objectives complete
    updated_quest = await db.active_quests.find_one({"quest_id": data.quest_id})
    all_complete = all(obj.get("completed", False) for obj in updated_quest["objectives"])
    
    return {
        "quest_id": data.quest_id,
        "objective_index": data.objective_index,
        "progress": new_progress,
        "objective_completed": completed,
        "quest_ready_to_complete": all_complete
    }

@quest_router.post("/complete")
async def complete_quest(data: QuestComplete):
    """Complete a quest and claim rewards"""
    db = get_db()
    
    quest = await db.active_quests.find_one({
        "quest_id": data.quest_id,
        "user_id": data.user_id,
        "status": "active"
    })
    
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")
    
    # Check all objectives complete
    all_complete = all(obj.get("completed", False) for obj in quest["objectives"])
    if not all_complete:
        raise HTTPException(status_code=400, detail="Not all objectives completed")
    
    now = datetime.now(timezone.utc)
    rewards = quest["rewards"]
    rep_reward = quest.get("rep_reward")
    
    # Award gold
    gold_earned = rewards.get("gold", 0)
    await db.player_wallets.update_one(
        {"user_id": data.user_id},
        {"$inc": {"gold": gold_earned}},
        upsert=True
    )
    
    # Award exp
    exp_earned = rewards.get("exp", 0)
    await db.player_ranks.update_one(
        {"user_id": data.user_id},
        {"$inc": {"experience": exp_earned}},
        upsert=True
    )
    
    # Award reputation
    rep_awarded = None
    if rep_reward and rep_reward.get("amount"):
        faction_id = rep_reward.get("faction")
        rep_amount = rep_reward["amount"]
        
        if faction_id:
            await db.player_reputation.update_one(
                {"user_id": data.user_id, "faction_id": faction_id},
                {"$inc": {"reputation": rep_amount}},
                upsert=True
            )
            rep_awarded = {"faction": faction_id, "amount": rep_amount}
        else:
            # General reputation
            await db.player_achievement_stats.update_one(
                {"user_id": data.user_id},
                {"$inc": {"general_reputation": rep_amount}},
                upsert=True
            )
            rep_awarded = {"type": "general", "amount": rep_amount}
    
    # Mark quest complete
    await db.active_quests.update_one(
        {"quest_id": data.quest_id},
        {
            "$set": {
                "status": "completed",
                "completed_at": now.isoformat()
            }
        }
    )
    
    # Add to completed quests
    await db.completed_quests.insert_one({
        "user_id": data.user_id,
        "quest_id": data.quest_id,
        "quest_template": quest["quest_template"],
        "completed_at": now.isoformat()
    })
    
    # Set cooldown if applicable
    template = QUEST_TEMPLATES.get(quest["quest_template"], {})
    if template.get("cooldown_hours"):
        await db.quest_cooldowns.update_one(
            {"user_id": data.user_id, "quest_template": quest["quest_template"]},
            {
                "$set": {
                    "available_at": (now + timedelta(hours=template["cooldown_hours"])).isoformat()
                }
            },
            upsert=True
        )
    
    return {
        "success": True,
        "quest_id": data.quest_id,
        "rewards_claimed": {
            "gold": gold_earned,
            "exp": exp_earned,
            "reputation": rep_awarded,
            "item": rewards.get("item")
        },
        "next_quest": template.get("next_quest")
    }

@quest_router.get("/reputation/{user_id}")
async def get_user_reputation(user_id: str):
    """Get user's reputation with all factions"""
    db = get_db()
    
    reps = await db.player_reputation.find(
        {"user_id": user_id},
        {"_id": 0}
    ).to_list(20)
    
    rep_data = {}
    for rep in reps:
        faction_id = rep["faction_id"]
        amount = rep.get("reputation", 0)
        tier_info = get_reputation_tier(faction_id, amount)
        
        rep_data[faction_id] = {
            "faction_name": FACTIONS.get(faction_id, {}).get("name", faction_id),
            "reputation": amount,
            **tier_info
        }
    
    # Add factions not yet encountered
    for faction_id in FACTIONS:
        if faction_id not in rep_data:
            rep_data[faction_id] = {
                "faction_name": FACTIONS[faction_id]["name"],
                "reputation": 0,
                **get_reputation_tier(faction_id, 0)
            }
    
    return {
        "user_id": user_id,
        "factions": rep_data
    }

@quest_router.get("/wallet/{user_id}")
async def get_user_wallet(user_id: str):
    """Get user's gold wallet"""
    db = get_db()
    
    wallet = await db.player_wallets.find_one(
        {"user_id": user_id},
        {"_id": 0}
    )
    
    if not wallet:
        wallet = {"user_id": user_id, "gold": 0}
    
    return wallet
