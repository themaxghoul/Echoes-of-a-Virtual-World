# Player Direction & Introduction System
# Onboarding, player paths, and the Single Seed Virtual Verse

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone
import uuid
import logging

player_direction_router = APIRouter(prefix="/player-direction", tags=["player-direction"])

logger = logging.getLogger(__name__)

# ============ PLAYER PATHS/DIRECTIONS ============
# Different life paths players can choose in the Virtual Verse

PLAYER_PATHS = {
    "merchant_prince": {
        "name": "Merchant Prince",
        "description": "Master of commerce and trade. Build economic empires and control markets.",
        "icon": "coins",
        "color": "#F59E0B",
        "starting_bonuses": {
            "gold": 500,
            "reputation": {"merchants_guild": 100},
            "skills": ["bargaining", "appraisal"]
        },
        "recommended_for": "Players who enjoy economics, trading, and building wealth",
        "ai_partner_affinity": ["market_analyst", "npc_merchant"],
        "primary_stats": ["charisma", "intelligence"],
        "unlocks": ["market_stalls", "trade_routes", "bank_access"]
    },
    "warrior_champion": {
        "name": "Warrior Champion",
        "description": "Master of combat and glory. Lead armies and conquer challenges.",
        "icon": "sword",
        "color": "#EF4444",
        "starting_bonuses": {
            "gold": 200,
            "reputation": {"adventurers_league": 100},
            "skills": ["combat_basics", "weapon_proficiency"],
            "items": ["iron_sword", "leather_armor"]
        },
        "recommended_for": "Players who enjoy action, combat, and heroic quests",
        "ai_partner_affinity": ["dungeon_crawler", "security_monitor"],
        "primary_stats": ["strength", "constitution"],
        "unlocks": ["arena_access", "bounty_board", "military_quests"]
    },
    "arcane_scholar": {
        "name": "Arcane Scholar",
        "description": "Master of magic and knowledge. Unravel the mysteries of the universe.",
        "icon": "sparkles",
        "color": "#8B5CF6",
        "starting_bonuses": {
            "gold": 300,
            "reputation": {"mages_circle": 100},
            "skills": ["basic_magic", "lore"],
            "items": ["apprentice_staff", "spellbook"]
        },
        "recommended_for": "Players who enjoy magic, research, and discovery",
        "ai_partner_affinity": ["research_assistant", "quest_runner"],
        "primary_stats": ["intelligence", "wisdom"],
        "unlocks": ["arcane_library", "enchanting_table", "portal_network"]
    },
    "master_artisan": {
        "name": "Master Artisan",
        "description": "Creator of wonders. Craft legendary items and build magnificent structures.",
        "icon": "hammer",
        "color": "#F97316",
        "starting_bonuses": {
            "gold": 350,
            "reputation": {"craftsmen_union": 100},
            "skills": ["basic_crafting", "blueprint_reading"],
            "items": ["artisan_tools", "crafting_materials"]
        },
        "recommended_for": "Players who enjoy building, crafting, and creating",
        "ai_partner_affinity": ["craft_optimizer", "resource_harvester"],
        "primary_stats": ["dexterity", "intelligence"],
        "unlocks": ["workshop", "blueprint_market", "custom_designs"]
    },
    "nature_guardian": {
        "name": "Nature Guardian",
        "description": "Protector of the wild. Commune with nature and nurture the land.",
        "icon": "leaf",
        "color": "#22C55E",
        "starting_bonuses": {
            "gold": 250,
            "reputation": {"nature_wardens": 100},
            "skills": ["herbalism", "animal_handling"],
            "items": ["seeds_pack", "taming_whistle"]
        },
        "recommended_for": "Players who enjoy farming, animals, and environmental gameplay",
        "ai_partner_affinity": ["farm_manager", "resource_harvester"],
        "primary_stats": ["wisdom", "constitution"],
        "unlocks": ["grove_sanctuary", "beast_companions", "rare_seeds"]
    },
    "shadow_operative": {
        "name": "Shadow Operative",
        "description": "Master of secrets and stealth. Information is power.",
        "icon": "eye-off",
        "color": "#6B7280",
        "starting_bonuses": {
            "gold": 400,
            "reputation": {"shadow_network": 100},
            "skills": ["stealth", "lockpicking"],
            "items": ["shadow_cloak", "lockpicks"]
        },
        "recommended_for": "Players who enjoy stealth, intrigue, and information gathering",
        "ai_partner_affinity": ["quest_runner", "security_monitor"],
        "primary_stats": ["dexterity", "charisma"],
        "unlocks": ["black_market", "informant_network", "hidden_passages"]
    },
    "tech_pioneer": {
        "name": "Tech Pioneer",
        "description": "Master of AI and automation. Harness the power of computational intelligence.",
        "icon": "cpu",
        "color": "#06B6D4",
        "starting_bonuses": {
            "gold": 300,
            "compute_power": 100,
            "skills": ["programming", "ai_training"],
            "items": ["basic_compute_node"]
        },
        "recommended_for": "Players who enjoy automation, AI companions, and passive income",
        "ai_partner_affinity": ["market_analyst", "craft_optimizer", "research_assistant", "energy_converter"],
        "primary_stats": ["intelligence", "wisdom"],
        "unlocks": ["compute_farm", "ai_lab", "automation_blueprints"]
    },
    "free_spirit": {
        "name": "Free Spirit",
        "description": "Forge your own path. No predetermined destiny—only endless possibilities.",
        "icon": "compass",
        "color": "#EC4899",
        "starting_bonuses": {
            "gold": 300,
            "skills": ["adaptability"],
            "exploration_bonus": 1.5
        },
        "recommended_for": "Players who want complete freedom to explore all playstyles",
        "ai_partner_affinity": ["quest_runner"],
        "primary_stats": ["balanced"],
        "unlocks": ["all_basic_content"]
    }
}

# ============ SINGLE SEED VIRTUAL VERSE ============
# The unified world that all players share

VIRTUAL_VERSE_INFO = {
    "name": "The Virtual Verse",
    "description": "A single, persistent world seed shared by all players. Every action shapes reality.",
    "current_scale": "1x Earth",
    "target_scale": "4x Earth",
    "scale_progression": [
        {"name": "Genesis", "size": "0.1x", "compute_required": 0, "unlocked": True},
        {"name": "Expansion", "size": "0.5x", "compute_required": 10000, "unlocked": False},
        {"name": "Continents", "size": "1x", "compute_required": 100000, "unlocked": False},
        {"name": "Megaverse", "size": "2x", "compute_required": 1000000, "unlocked": False},
        {"name": "Infinite Realm", "size": "4x", "compute_required": 10000000, "unlocked": False}
    ],
    "features": [
        "Persistent world state across all players",
        "AI NPCs with evolving memories",
        "Player-built structures visible to everyone",
        "Dynamic economy affected by all players",
        "Seasonal events and world changes",
        "Compute power expands world territory",
        "Energy conversion at massive scale"
    ],
    "energy_conversion_info": {
        "description": "At 4x Earth scale, accumulated compute power converts to real energy efficiency",
        "threshold_compute": 10000000,
        "conversion_rate": "1M compute = sustainable energy for 1000 households",
        "goal": "Transform computational power into real-world positive impact"
    }
}

# ============ INTRODUCTION STEPS ============

INTRO_STEPS = [
    {
        "step": 1,
        "title": "Welcome to the Virtual Verse",
        "content": "You've arrived in a world where AI and humans work together. This isn't just a game—it's a glimpse into a future where technology serves humanity.",
        "action": "acknowledge",
        "skippable": False
    },
    {
        "step": 2,
        "title": "Choose Your Path",
        "content": "Your journey begins with a choice. Each path offers unique advantages, but you're never locked in. The Virtual Verse rewards those who adapt.",
        "action": "select_path",
        "skippable": False
    },
    {
        "step": 3,
        "title": "Meet Your AI Partner",
        "content": "Your AI companion will help you earn income while you're away. The better your relationship, the more effective they become. Trust is earned, not given.",
        "action": "meet_ai",
        "skippable": True
    },
    {
        "step": 4,
        "title": "The Economy",
        "content": "Gold is for the game world. VE$ has real value. AI programs you deploy generate both. The line between virtual and real wealth blurs here.",
        "action": "learn_economy",
        "skippable": True
    },
    {
        "step": 5,
        "title": "Building Your Legacy",
        "content": "Plots, buildings, and structures you create persist in the shared world. Others will see what you build. Make it count.",
        "action": "learn_building",
        "skippable": True
    },
    {
        "step": 6,
        "title": "The Greater Purpose",
        "content": "Every computation matters. As our collective compute grows, so does the Virtual Verse. At scale, this power transforms into real-world energy solutions.",
        "action": "learn_purpose",
        "skippable": True
    },
    {
        "step": 7,
        "title": "Begin Your Journey",
        "content": "The Virtual Verse awaits. Will you trade, fight, craft, or explore? The choice is yours, but remember—your AI partner is always working for you.",
        "action": "complete",
        "skippable": False
    }
]

# ============ MODELS ============

class PathSelection(BaseModel):
    user_id: str
    path_id: str
    skip_intro: bool = False

class IntroProgress(BaseModel):
    user_id: str
    step: int
    action_completed: bool = True

# MongoDB reference
def get_db():
    from server import db
    return db

# ============ ENDPOINTS ============

@player_direction_router.get("/paths")
async def get_all_paths():
    """Get all available player paths"""
    return {
        "paths": PLAYER_PATHS,
        "total_paths": len(PLAYER_PATHS)
    }

@player_direction_router.get("/path/{path_id}")
async def get_path_details(path_id: str):
    """Get details for a specific path"""
    if path_id not in PLAYER_PATHS:
        raise HTTPException(status_code=404, detail="Path not found")
    
    return {
        "path_id": path_id,
        **PLAYER_PATHS[path_id]
    }

@player_direction_router.get("/virtual-verse")
async def get_virtual_verse_info():
    """Get information about the Virtual Verse"""
    db = get_db()
    
    # Get global compute stats
    total_compute = await db.compute_allocations.aggregate([
        {"$match": {"status": "active"}},
        {"$group": {"_id": None, "total": {"$sum": "$compute_power"}}}
    ]).to_list(1)
    
    global_compute = total_compute[0]["total"] if total_compute else 0
    
    # Determine current scale
    current_scale = "Genesis"
    for scale in VIRTUAL_VERSE_INFO["scale_progression"]:
        if global_compute >= scale["compute_required"]:
            current_scale = scale["name"]
    
    return {
        **VIRTUAL_VERSE_INFO,
        "global_compute": global_compute,
        "current_unlocked_scale": current_scale
    }

@player_direction_router.get("/intro-steps")
async def get_intro_steps():
    """Get all introduction steps"""
    return {
        "steps": INTRO_STEPS,
        "total_steps": len(INTRO_STEPS),
        "skippable_count": sum(1 for s in INTRO_STEPS if s.get("skippable", False))
    }

@player_direction_router.get("/user/{user_id}/status")
async def get_user_direction_status(user_id: str):
    """Get user's current path, intro progress, etc."""
    db = get_db()
    
    status = await db.player_direction.find_one(
        {"user_id": user_id},
        {"_id": 0}
    )
    
    if not status:
        return {
            "user_id": user_id,
            "has_chosen_path": False,
            "intro_completed": False,
            "intro_step": 1,
            "path": None
        }
    
    return status

@player_direction_router.post("/select-path")
async def select_path(data: PathSelection):
    """Select a player path and optionally skip intro"""
    db = get_db()
    
    if data.path_id not in PLAYER_PATHS:
        raise HTTPException(status_code=400, detail="Invalid path")
    
    path = PLAYER_PATHS[data.path_id]
    now = datetime.now(timezone.utc).isoformat()
    
    # Create or update player direction
    direction_data = {
        "user_id": data.user_id,
        "path_id": data.path_id,
        "path_name": path["name"],
        "has_chosen_path": True,
        "intro_completed": data.skip_intro,
        "intro_step": 7 if data.skip_intro else 2,
        "selected_at": now,
        "intro_skipped": data.skip_intro
    }
    
    await db.player_direction.update_one(
        {"user_id": data.user_id},
        {"$set": direction_data},
        upsert=True
    )
    
    # Apply starting bonuses
    bonuses = path.get("starting_bonuses", {})
    
    # Gold bonus
    if bonuses.get("gold"):
        await db.player_wallets.update_one(
            {"user_id": data.user_id},
            {"$inc": {"gold": bonuses["gold"]}},
            upsert=True
        )
    
    # Compute bonus (for Tech Pioneer)
    if bonuses.get("compute_power"):
        await db.compute_allocations.insert_one({
            "allocation_id": str(uuid.uuid4()),
            "owner_id": data.user_id,
            "owner_type": "player",
            "tier": "basic",
            "status": "active",
            "compute_power": bonuses["compute_power"],
            "started_at": now,
            "source": "path_bonus"
        })
    
    # Reputation bonuses
    if bonuses.get("reputation"):
        for faction_id, rep_amount in bonuses["reputation"].items():
            await db.player_reputation.update_one(
                {"user_id": data.user_id, "faction_id": faction_id},
                {"$inc": {"reputation": rep_amount}},
                upsert=True
            )
    
    # Skills
    if bonuses.get("skills"):
        for skill in bonuses["skills"]:
            await db.player_skills.update_one(
                {"user_id": data.user_id, "skill_id": skill},
                {"$set": {"level": 1, "unlocked": True, "unlocked_at": now}},
                upsert=True
            )
    
    # Record path selection for achievements
    await db.player_achievement_stats.update_one(
        {"user_id": data.user_id},
        {
            "$set": {
                "chosen_path": data.path_id,
                "path_chosen_at": now
            }
        },
        upsert=True
    )
    
    return {
        "success": True,
        "path_selected": data.path_id,
        "path_name": path["name"],
        "bonuses_applied": bonuses,
        "intro_skipped": data.skip_intro,
        "next_step": "Begin playing!" if data.skip_intro else "Continue introduction"
    }

@player_direction_router.post("/intro/progress")
async def update_intro_progress(data: IntroProgress):
    """Update introduction progress"""
    db = get_db()
    
    if data.step < 1 or data.step > len(INTRO_STEPS):
        raise HTTPException(status_code=400, detail="Invalid step")
    
    step_info = INTRO_STEPS[data.step - 1]
    next_step = data.step + 1 if data.step < len(INTRO_STEPS) else data.step
    completed = data.step >= len(INTRO_STEPS)
    
    await db.player_direction.update_one(
        {"user_id": data.user_id},
        {
            "$set": {
                "intro_step": next_step,
                "intro_completed": completed,
                f"intro_step_{data.step}_completed": True,
                "last_intro_update": datetime.now(timezone.utc).isoformat()
            }
        },
        upsert=True
    )
    
    return {
        "step_completed": data.step,
        "next_step": next_step if not completed else None,
        "intro_completed": completed,
        "step_info": step_info
    }

@player_direction_router.post("/intro/skip")
async def skip_intro(user_id: str):
    """Skip remaining introduction steps"""
    db = get_db()
    
    await db.player_direction.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "intro_completed": True,
                "intro_skipped": True,
                "intro_step": len(INTRO_STEPS),
                "skipped_at": datetime.now(timezone.utc).isoformat()
            }
        },
        upsert=True
    )
    
    return {
        "success": True,
        "intro_skipped": True,
        "message": "Introduction skipped. You can review tutorials anytime from the menu."
    }

@player_direction_router.get("/compute-scale")
async def get_compute_scale_status():
    """Get current compute scale and progress toward expansion"""
    db = get_db()
    
    # Sum all active compute
    pipeline = [
        {"$match": {"status": "active"}},
        {"$group": {"_id": None, "total": {"$sum": "$compute_power"}}}
    ]
    
    compute_result = await db.compute_allocations.aggregate(pipeline).to_list(1)
    total_compute = compute_result[0]["total"] if compute_result else 0
    
    # Find current and next scale
    scales = VIRTUAL_VERSE_INFO["scale_progression"]
    current_scale = scales[0]
    next_scale = None
    
    for i, scale in enumerate(scales):
        if total_compute >= scale["compute_required"]:
            current_scale = scale
            if i + 1 < len(scales):
                next_scale = scales[i + 1]
    
    progress_to_next = 0
    if next_scale:
        needed = next_scale["compute_required"] - current_scale["compute_required"]
        current_progress = total_compute - current_scale["compute_required"]
        progress_to_next = min(100, (current_progress / needed) * 100) if needed > 0 else 100
    
    return {
        "global_compute": total_compute,
        "current_scale": current_scale,
        "next_scale": next_scale,
        "progress_percent": round(progress_to_next, 2),
        "energy_threshold_reached": total_compute >= VIRTUAL_VERSE_INFO["energy_conversion_info"]["threshold_compute"],
        "energy_conversion_info": VIRTUAL_VERSE_INFO["energy_conversion_info"]
    }
