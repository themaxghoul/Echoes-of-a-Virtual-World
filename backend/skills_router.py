# Skills & Titles System Router
# Dynamic skill development through actions + Title system with stat boosts

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone
import uuid
import logging
import random

skills_router = APIRouter(prefix="/skill-system", tags=["skill-system"])

logger = logging.getLogger(__name__)

# ============ Skill Definitions ============

SKILL_CATEGORIES = {
    "combat": {
        "name": "Combat",
        "color": "#EF4444",
        "skills": {
            "swordsmanship": {"name": "Swordsmanship", "description": "Melee weapon proficiency", "max_level": 100},
            "archery": {"name": "Archery", "description": "Ranged weapon accuracy", "max_level": 100},
            "defense": {"name": "Defense", "description": "Damage mitigation", "max_level": 100},
            "tactics": {"name": "Tactics", "description": "Combat strategy and positioning", "max_level": 100},
            "berserker": {"name": "Berserker", "description": "Rage-fueled attacks", "max_level": 50},
        }
    },
    "magic": {
        "name": "Magic",
        "color": "#8B5CF6",
        "skills": {
            "elemental": {"name": "Elemental Magic", "description": "Fire, water, earth, air manipulation", "max_level": 100},
            "healing": {"name": "Healing", "description": "Restoration and cure abilities", "max_level": 100},
            "enchanting": {"name": "Enchanting", "description": "Imbue items with magic", "max_level": 100},
            "divination": {"name": "Divination", "description": "See the future and hidden truths", "max_level": 75},
            "shadow": {"name": "Shadow Magic", "description": "Dark arts and illusions", "max_level": 50},
        }
    },
    "crafting": {
        "name": "Crafting",
        "color": "#F59E0B",
        "skills": {
            "blacksmithing": {"name": "Blacksmithing", "description": "Forge weapons and armor", "max_level": 100},
            "alchemy": {"name": "Alchemy", "description": "Create potions and elixirs", "max_level": 100},
            "woodworking": {"name": "Woodworking", "description": "Craft bows, staves, furniture", "max_level": 100},
            "tailoring": {"name": "Tailoring", "description": "Create cloth armor and clothing", "max_level": 100},
            "engineering": {"name": "Engineering", "description": "Build machines and structures", "max_level": 75},
        }
    },
    "gathering": {
        "name": "Gathering",
        "color": "#10B981",
        "skills": {
            "mining": {"name": "Mining", "description": "Extract ores and gems", "max_level": 100},
            "herbalism": {"name": "Herbalism", "description": "Collect plants and herbs", "max_level": 100},
            "hunting": {"name": "Hunting", "description": "Track and harvest creatures", "max_level": 100},
            "fishing": {"name": "Fishing", "description": "Catch aquatic life", "max_level": 100},
            "foraging": {"name": "Foraging", "description": "Find rare materials", "max_level": 75},
        }
    },
    "social": {
        "name": "Social",
        "color": "#3B82F6",
        "skills": {
            "diplomacy": {"name": "Diplomacy", "description": "Negotiate and persuade", "max_level": 100},
            "trading": {"name": "Trading", "description": "Better prices and deals", "max_level": 100},
            "leadership": {"name": "Leadership", "description": "Inspire and command others", "max_level": 100},
            "intimidation": {"name": "Intimidation", "description": "Coerce through fear", "max_level": 75},
            "charm": {"name": "Charm", "description": "Win hearts and minds", "max_level": 75},
        }
    },
    "knowledge": {
        "name": "Knowledge",
        "color": "#6366F1",
        "skills": {
            "lore": {"name": "Lore", "description": "World history and secrets", "max_level": 100},
            "languages": {"name": "Languages", "description": "Understand ancient tongues", "max_level": 100},
            "investigation": {"name": "Investigation", "description": "Uncover hidden clues", "max_level": 100},
            "arcana": {"name": "Arcana", "description": "Magical theory and artifacts", "max_level": 75},
            "nature": {"name": "Nature", "description": "Flora, fauna, and ecosystems", "max_level": 75},
        }
    }
}

# ============ Title Definitions ============

TITLES = {
    # Combat Titles
    "novice_warrior": {"name": "Novice Warrior", "category": "combat", "requirement": {"skill": "swordsmanship", "level": 10}, "boosts": {"strength": 2, "endurance": 1}},
    "blade_dancer": {"name": "Blade Dancer", "category": "combat", "requirement": {"skill": "swordsmanship", "level": 50}, "boosts": {"strength": 5, "agility": 3, "endurance": 2}},
    "sword_saint": {"name": "Sword Saint", "category": "combat", "requirement": {"skill": "swordsmanship", "level": 100}, "boosts": {"strength": 10, "agility": 5, "endurance": 5, "wisdom": 3}},
    "marksman": {"name": "Marksman", "category": "combat", "requirement": {"skill": "archery", "level": 50}, "boosts": {"agility": 5, "perception": 5}},
    "legendary_archer": {"name": "Legendary Archer", "category": "combat", "requirement": {"skill": "archery", "level": 100}, "boosts": {"agility": 10, "perception": 10, "luck": 3}},
    "iron_wall": {"name": "Iron Wall", "category": "combat", "requirement": {"skill": "defense", "level": 75}, "boosts": {"endurance": 10, "strength": 3}},
    
    # Magic Titles
    "apprentice_mage": {"name": "Apprentice Mage", "category": "magic", "requirement": {"skill": "elemental", "level": 10}, "boosts": {"intelligence": 2, "wisdom": 1}},
    "elementalist": {"name": "Elementalist", "category": "magic", "requirement": {"skill": "elemental", "level": 50}, "boosts": {"intelligence": 5, "wisdom": 3}},
    "archmage": {"name": "Archmage", "category": "magic", "requirement": {"skill": "elemental", "level": 100}, "boosts": {"intelligence": 10, "wisdom": 8, "mana": 50}},
    "healer": {"name": "Healer", "category": "magic", "requirement": {"skill": "healing", "level": 30}, "boosts": {"wisdom": 5, "charisma": 2}},
    "divine_healer": {"name": "Divine Healer", "category": "magic", "requirement": {"skill": "healing", "level": 100}, "boosts": {"wisdom": 10, "charisma": 5, "luck": 5}},
    "shadow_walker": {"name": "Shadow Walker", "category": "magic", "requirement": {"skill": "shadow", "level": 50}, "boosts": {"agility": 5, "perception": 5, "stealth": 10}},
    
    # Crafting Titles
    "apprentice_smith": {"name": "Apprentice Smith", "category": "crafting", "requirement": {"skill": "blacksmithing", "level": 10}, "boosts": {"strength": 1, "endurance": 1}},
    "master_smith": {"name": "Master Smith", "category": "crafting", "requirement": {"skill": "blacksmithing", "level": 75}, "boosts": {"strength": 5, "crafting_bonus": 15}},
    "legendary_forger": {"name": "Legendary Forger", "category": "crafting", "requirement": {"skill": "blacksmithing", "level": 100}, "boosts": {"strength": 8, "crafting_bonus": 30, "reputation": 10}},
    "alchemist": {"name": "Alchemist", "category": "crafting", "requirement": {"skill": "alchemy", "level": 50}, "boosts": {"intelligence": 5, "potion_bonus": 20}},
    "grand_alchemist": {"name": "Grand Alchemist", "category": "crafting", "requirement": {"skill": "alchemy", "level": 100}, "boosts": {"intelligence": 10, "wisdom": 5, "potion_bonus": 50}},
    "architect": {"name": "Architect", "category": "crafting", "requirement": {"skill": "engineering", "level": 50}, "boosts": {"intelligence": 5, "building_bonus": 25}},
    
    # Social Titles
    "silver_tongue": {"name": "Silver Tongue", "category": "social", "requirement": {"skill": "diplomacy", "level": 30}, "boosts": {"charisma": 5}},
    "ambassador": {"name": "Ambassador", "category": "social", "requirement": {"skill": "diplomacy", "level": 75}, "boosts": {"charisma": 10, "reputation": 15}},
    "merchant_prince": {"name": "Merchant Prince", "category": "social", "requirement": {"skill": "trading", "level": 75}, "boosts": {"charisma": 5, "trade_bonus": 25, "luck": 3}},
    "warlord": {"name": "Warlord", "category": "social", "requirement": {"skill": "leadership", "level": 75}, "boosts": {"strength": 5, "charisma": 8, "command_bonus": 20}},
    
    # Knowledge Titles
    "scholar": {"name": "Scholar", "category": "knowledge", "requirement": {"skill": "lore", "level": 30}, "boosts": {"intelligence": 3, "wisdom": 2}},
    "sage": {"name": "Sage", "category": "knowledge", "requirement": {"skill": "lore", "level": 75}, "boosts": {"intelligence": 8, "wisdom": 8}},
    "omniscient": {"name": "The Omniscient", "category": "knowledge", "requirement": {"skill": "lore", "level": 100}, "boosts": {"intelligence": 15, "wisdom": 15, "perception": 10}},
    "linguist": {"name": "Linguist", "category": "knowledge", "requirement": {"skill": "languages", "level": 50}, "boosts": {"intelligence": 5, "charisma": 3}},
    
    # Special Titles (Achievement-based)
    "pioneer": {"name": "Pioneer", "category": "special", "requirement": {"action": "first_building", "count": 1}, "boosts": {"reputation": 5, "building_bonus": 10}},
    "world_shaper": {"name": "World Shaper", "category": "special", "requirement": {"action": "world_edits", "count": 100}, "boosts": {"all_stats": 3, "building_bonus": 25}},
    "peacemaker": {"name": "Peacemaker", "category": "special", "requirement": {"action": "conflicts_resolved", "count": 10}, "boosts": {"charisma": 10, "reputation": 20}},
    "wealth_creator": {"name": "Wealth Creator", "category": "special", "requirement": {"action": "ve_earned", "count": 1000}, "boosts": {"luck": 5, "trade_bonus": 15}},
    "transcendent": {"name": "Transcendent", "category": "special", "requirement": {"action": "max_skills", "count": 5}, "boosts": {"all_stats": 10}},
}

# ============ Action to Skill Mapping ============

ACTION_SKILL_GAINS = {
    # Combat actions
    "attack_melee": {"skill": "swordsmanship", "xp_range": (1, 5)},
    "attack_ranged": {"skill": "archery", "xp_range": (1, 5)},
    "block": {"skill": "defense", "xp_range": (1, 3)},
    "dodge": {"skill": "defense", "xp_range": (1, 3)},
    "victory_combat": {"skill": "tactics", "xp_range": (5, 15)},
    
    # Magic actions
    "cast_elemental": {"skill": "elemental", "xp_range": (2, 8)},
    "cast_heal": {"skill": "healing", "xp_range": (3, 10)},
    "enchant_item": {"skill": "enchanting", "xp_range": (5, 15)},
    "divine_future": {"skill": "divination", "xp_range": (5, 20)},
    
    # Crafting actions
    "forge_item": {"skill": "blacksmithing", "xp_range": (3, 10)},
    "brew_potion": {"skill": "alchemy", "xp_range": (3, 10)},
    "craft_wood": {"skill": "woodworking", "xp_range": (2, 8)},
    "sew_item": {"skill": "tailoring", "xp_range": (2, 8)},
    "build_structure": {"skill": "engineering", "xp_range": (10, 30)},
    
    # Gathering actions
    "mine_ore": {"skill": "mining", "xp_range": (1, 5)},
    "gather_herb": {"skill": "herbalism", "xp_range": (1, 5)},
    "hunt_creature": {"skill": "hunting", "xp_range": (2, 8)},
    "catch_fish": {"skill": "fishing", "xp_range": (1, 5)},
    
    # Social actions
    "negotiate": {"skill": "diplomacy", "xp_range": (2, 8)},
    "trade": {"skill": "trading", "xp_range": (1, 5)},
    "lead_group": {"skill": "leadership", "xp_range": (3, 10)},
    "convince": {"skill": "charm", "xp_range": (2, 8)},
    
    # Knowledge actions
    "read_book": {"skill": "lore", "xp_range": (2, 10)},
    "translate": {"skill": "languages", "xp_range": (3, 12)},
    "investigate": {"skill": "investigation", "xp_range": (2, 8)},
    "study_magic": {"skill": "arcana", "xp_range": (3, 10)},
    
    # Conversation actions (for AI-to-AI and player chat)
    "conversation": {"skill": "charm", "xp_range": (1, 3)},
    "deep_conversation": {"skill": "diplomacy", "xp_range": (2, 5)},
}

# ============ Models ============

class EntitySkills(BaseModel):
    entity_id: str
    entity_type: str  # "player" or "npc"
    skills: Dict[str, Dict[str, Any]] = Field(default_factory=dict)  # skill_id: {level, xp, actions}
    total_skill_points: int = 0
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class EntityTitles(BaseModel):
    entity_id: str
    entity_type: str
    unlocked_titles: List[str] = Field(default_factory=list)
    active_title: Optional[str] = None
    title_history: List[Dict[str, Any]] = Field(default_factory=list)

class SkillAction(BaseModel):
    entity_id: str
    entity_type: str = "player"
    action: str
    context: Optional[Dict[str, Any]] = None

class SetActiveTitle(BaseModel):
    entity_id: str
    title_id: str

# ============ Database Helper ============

def get_db():
    from server import db
    return db

# ============ Helper Functions ============

def calculate_level(xp: int) -> int:
    """Calculate skill level from XP (exponential curve)"""
    level = 1
    xp_needed = 100
    total_xp = 0
    while total_xp + xp_needed <= xp and level < 100:
        total_xp += xp_needed
        level += 1
        xp_needed = int(xp_needed * 1.15)  # 15% more XP per level
    return level

def xp_for_next_level(current_level: int) -> int:
    """Calculate XP needed for next level"""
    xp_needed = 100
    for _ in range(current_level - 1):
        xp_needed = int(xp_needed * 1.15)
    return xp_needed

def calculate_stat_boosts(titles: List[str]) -> Dict[str, int]:
    """Calculate total stat boosts from all active titles"""
    boosts = {}
    for title_id in titles:
        if title_id in TITLES:
            title_boosts = TITLES[title_id].get("boosts", {})
            for stat, value in title_boosts.items():
                boosts[stat] = boosts.get(stat, 0) + value
    return boosts

# ============ Endpoints ============

@skills_router.get("/catalog")
async def get_skills_catalog():
    """Get all available skills and categories"""
    return {
        "categories": SKILL_CATEGORIES,
        "action_mappings": ACTION_SKILL_GAINS,
        "total_skills": sum(len(cat["skills"]) for cat in SKILL_CATEGORIES.values())
    }

@skills_router.get("/titles/catalog")
async def get_titles_catalog():
    """Get all available titles"""
    return {
        "titles": TITLES,
        "total_titles": len(TITLES)
    }

@skills_router.get("/entity/{entity_type}/{entity_id}")
async def get_entity_skills(entity_type: str, entity_id: str):
    """Get skills for an entity (player or NPC)"""
    db = get_db()
    
    skills_doc = await db.entity_skills.find_one(
        {"entity_id": entity_id, "entity_type": entity_type},
        {"_id": 0}
    )
    
    if not skills_doc:
        # Initialize skills for new entity
        skills_doc = EntitySkills(entity_id=entity_id, entity_type=entity_type).dict()
        await db.entity_skills.insert_one(skills_doc)
    
    # Enrich with category info
    enriched_skills = {}
    for skill_id, skill_data in skills_doc.get("skills", {}).items():
        # Find category
        for cat_id, category in SKILL_CATEGORIES.items():
            if skill_id in category["skills"]:
                enriched_skills[skill_id] = {
                    **skill_data,
                    **category["skills"][skill_id],
                    "category": cat_id,
                    "category_name": category["name"],
                    "color": category["color"]
                }
                break
    
    return {
        "entity_id": entity_id,
        "entity_type": entity_type,
        "skills": enriched_skills,
        "total_skill_points": skills_doc.get("total_skill_points", 0)
    }

@skills_router.get("/entity/{entity_type}/{entity_id}/titles")
async def get_entity_titles(entity_type: str, entity_id: str):
    """Get titles for an entity"""
    db = get_db()
    
    titles_doc = await db.entity_titles.find_one(
        {"entity_id": entity_id, "entity_type": entity_type},
        {"_id": 0}
    )
    
    if not titles_doc:
        titles_doc = EntityTitles(entity_id=entity_id, entity_type=entity_type).dict()
        await db.entity_titles.insert_one(titles_doc)
    
    # Get skill data to check for newly unlockable titles
    skills_doc = await db.entity_skills.find_one(
        {"entity_id": entity_id, "entity_type": entity_type}
    )
    
    # Check for titles that should be unlocked
    unlocked = titles_doc.get("unlocked_titles", [])
    newly_unlocked = []
    
    if skills_doc:
        for title_id, title_data in TITLES.items():
            if title_id not in unlocked:
                req = title_data.get("requirement", {})
                if "skill" in req:
                    skill_id = req["skill"]
                    required_level = req.get("level", 0)
                    skill_info = skills_doc.get("skills", {}).get(skill_id, {})
                    current_level = skill_info.get("level", 0)
                    if current_level >= required_level:
                        newly_unlocked.append(title_id)
    
    # Save newly unlocked titles
    if newly_unlocked:
        unlocked.extend(newly_unlocked)
        await db.entity_titles.update_one(
            {"entity_id": entity_id, "entity_type": entity_type},
            {"$set": {"unlocked_titles": unlocked}}
        )
    
    # Calculate stat boosts from active title
    active_title = titles_doc.get("active_title")
    stat_boosts = calculate_stat_boosts([active_title] if active_title else [])
    
    return {
        "entity_id": entity_id,
        "entity_type": entity_type,
        "unlocked_titles": unlocked,
        "active_title": active_title,
        "active_title_info": TITLES.get(active_title) if active_title else None,
        "stat_boosts": stat_boosts,
        "newly_unlocked": newly_unlocked,
        "total_unlocked": len(unlocked)
    }

@skills_router.post("/action")
async def perform_skill_action(action_data: SkillAction):
    """Perform an action that grants skill XP"""
    db = get_db()
    
    action = action_data.action
    if action not in ACTION_SKILL_GAINS:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}")
    
    skill_gain = ACTION_SKILL_GAINS[action]
    skill_id = skill_gain["skill"]
    xp_min, xp_max = skill_gain["xp_range"]
    xp_gained = random.randint(xp_min, xp_max)
    
    # Bonus XP from context (e.g., difficulty, quality)
    if action_data.context:
        difficulty = action_data.context.get("difficulty", 1.0)
        xp_gained = int(xp_gained * difficulty)
    
    # Get or create skills document
    skills_doc = await db.entity_skills.find_one(
        {"entity_id": action_data.entity_id, "entity_type": action_data.entity_type}
    )
    
    if not skills_doc:
        skills_doc = EntitySkills(
            entity_id=action_data.entity_id, 
            entity_type=action_data.entity_type
        ).dict()
        await db.entity_skills.insert_one(skills_doc)
    
    # Update skill
    current_skills = skills_doc.get("skills", {})
    if skill_id not in current_skills:
        current_skills[skill_id] = {"xp": 0, "level": 1, "actions": 0}
    
    old_level = current_skills[skill_id]["level"]
    current_skills[skill_id]["xp"] += xp_gained
    current_skills[skill_id]["actions"] += 1
    new_level = calculate_level(current_skills[skill_id]["xp"])
    current_skills[skill_id]["level"] = new_level
    
    level_up = new_level > old_level
    
    # Update database
    await db.entity_skills.update_one(
        {"entity_id": action_data.entity_id, "entity_type": action_data.entity_type},
        {
            "$set": {
                "skills": current_skills,
                "updated_at": datetime.now(timezone.utc).isoformat()
            },
            "$inc": {"total_skill_points": xp_gained}
        }
    )
    
    # Check for new titles
    new_titles = []
    for title_id, title_data in TITLES.items():
        req = title_data.get("requirement", {})
        if req.get("skill") == skill_id and req.get("level", 0) == new_level:
            # Check if already unlocked
            titles_doc = await db.entity_titles.find_one(
                {"entity_id": action_data.entity_id, "entity_type": action_data.entity_type}
            )
            if titles_doc and title_id not in titles_doc.get("unlocked_titles", []):
                new_titles.append(title_id)
                await db.entity_titles.update_one(
                    {"entity_id": action_data.entity_id, "entity_type": action_data.entity_type},
                    {"$push": {"unlocked_titles": title_id}},
                    upsert=True
                )
    
    return {
        "action": action,
        "skill": skill_id,
        "xp_gained": xp_gained,
        "new_xp": current_skills[skill_id]["xp"],
        "old_level": old_level,
        "new_level": new_level,
        "level_up": level_up,
        "xp_to_next": xp_for_next_level(new_level),
        "new_titles": new_titles
    }

@skills_router.post("/titles/set-active")
async def set_active_title(data: SetActiveTitle):
    """Set the active title for an entity"""
    db = get_db()
    
    # Verify title is unlocked
    titles_doc = await db.entity_titles.find_one(
        {"entity_id": data.entity_id}
    )
    
    if not titles_doc:
        raise HTTPException(status_code=404, detail="Entity has no titles")
    
    if data.title_id not in titles_doc.get("unlocked_titles", []):
        raise HTTPException(status_code=400, detail="Title not unlocked")
    
    if data.title_id not in TITLES:
        raise HTTPException(status_code=400, detail="Invalid title")
    
    await db.entity_titles.update_one(
        {"entity_id": data.entity_id},
        {
            "$set": {"active_title": data.title_id},
            "$push": {"title_history": {
                "title": data.title_id,
                "set_at": datetime.now(timezone.utc).isoformat()
            }}
        }
    )
    
    title_info = TITLES[data.title_id]
    
    return {
        "active_title": data.title_id,
        "title_info": title_info,
        "stat_boosts": title_info.get("boosts", {})
    }

@skills_router.get("/leaderboard/{skill_id}")
async def get_skill_leaderboard(skill_id: str, limit: int = 20):
    """Get leaderboard for a specific skill"""
    db = get_db()
    
    pipeline = [
        {"$match": {f"skills.{skill_id}": {"$exists": True}}},
        {"$project": {
            "_id": 0,
            "entity_id": 1,
            "entity_type": 1,
            "skill_level": f"$skills.{skill_id}.level",
            "skill_xp": f"$skills.{skill_id}.xp"
        }},
        {"$sort": {"skill_level": -1, "skill_xp": -1}},
        {"$limit": limit}
    ]
    
    leaders = await db.entity_skills.aggregate(pipeline).to_list(limit)
    
    return {
        "skill_id": skill_id,
        "leaderboard": leaders
    }
