# AI Skill Training Router - Student to Master Progression
# NPCs and AI entities can be trained by players in any skill

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone
import uuid
import logging

ai_training_router = APIRouter(prefix="/ai-training", tags=["ai-training"])
logger = logging.getLogger(__name__)

# Skill mastery levels - Student to Master
MASTERY_LEVELS = {
    "novice": {"level": 1, "xp_required": 0, "description": "Just beginning to learn", "efficiency": 0.2},
    "student": {"level": 2, "xp_required": 100, "description": "Learning the basics", "efficiency": 0.4},
    "apprentice": {"level": 3, "xp_required": 300, "description": "Gaining competence", "efficiency": 0.6},
    "journeyman": {"level": 4, "xp_required": 600, "description": "Proficient practitioner", "efficiency": 0.75},
    "expert": {"level": 5, "xp_required": 1000, "description": "Highly skilled", "efficiency": 0.85},
    "master": {"level": 6, "xp_required": 2000, "description": "Mastery achieved", "efficiency": 0.95},
    "grandmaster": {"level": 7, "xp_required": 5000, "description": "Legendary mastery", "efficiency": 1.0}
}

# Skills that can be trained
TRAINABLE_SKILLS = {
    # Combat Skills
    "swordsmanship": {"category": "combat", "base_difficulty": 1.0, "related": ["tactics", "defense"]},
    "archery": {"category": "combat", "base_difficulty": 0.9, "related": ["tracking", "survival"]},
    "defense": {"category": "combat", "base_difficulty": 0.8, "related": ["swordsmanship", "armor_craft"]},
    "tactics": {"category": "combat", "base_difficulty": 1.2, "related": ["leadership", "swordsmanship"]},
    
    # Crafting Skills
    "blacksmithing": {"category": "crafting", "base_difficulty": 1.1, "related": ["mining", "metallurgy"]},
    "carpentry": {"category": "crafting", "base_difficulty": 0.8, "related": ["woodworking", "architecture"]},
    "alchemy": {"category": "crafting", "base_difficulty": 1.3, "related": ["herbalism", "magic_theory"]},
    "cooking": {"category": "crafting", "base_difficulty": 0.6, "related": ["herbalism", "preservation"]},
    "tailoring": {"category": "crafting", "base_difficulty": 0.7, "related": ["trade", "design"]},
    
    # Magic Skills
    "fire_magic": {"category": "magic", "base_difficulty": 1.0, "related": ["arcane_theory", "elemental_control"]},
    "ice_magic": {"category": "magic", "base_difficulty": 1.0, "related": ["arcane_theory", "elemental_control"]},
    "healing": {"category": "magic", "base_difficulty": 1.2, "related": ["divine_magic", "herbalism"]},
    "enchanting": {"category": "magic", "base_difficulty": 1.4, "related": ["arcane_theory", "metallurgy"]},
    "divination": {"category": "magic", "base_difficulty": 1.5, "related": ["arcane_theory", "wisdom"]},
    
    # Social Skills
    "diplomacy": {"category": "social", "base_difficulty": 0.9, "related": ["charm", "languages"]},
    "trade": {"category": "social", "base_difficulty": 0.7, "related": ["negotiation", "economics"]},
    "leadership": {"category": "social", "base_difficulty": 1.3, "related": ["tactics", "diplomacy"]},
    "charm": {"category": "social", "base_difficulty": 0.8, "related": ["diplomacy", "performance"]},
    
    # Knowledge Skills
    "lore": {"category": "knowledge", "base_difficulty": 0.6, "related": ["languages", "history"]},
    "history": {"category": "knowledge", "base_difficulty": 0.5, "related": ["lore", "archaeology"]},
    "languages": {"category": "knowledge", "base_difficulty": 0.9, "related": ["diplomacy", "lore"]},
    "arcane_theory": {"category": "knowledge", "base_difficulty": 1.2, "related": ["alchemy", "enchanting"]},
    
    # Survival Skills
    "tracking": {"category": "survival", "base_difficulty": 0.8, "related": ["archery", "herbalism"]},
    "herbalism": {"category": "survival", "base_difficulty": 0.7, "related": ["alchemy", "cooking"]},
    "survival": {"category": "survival", "base_difficulty": 0.6, "related": ["tracking", "hunting"]},
    "hunting": {"category": "survival", "base_difficulty": 0.8, "related": ["archery", "tracking"]}
}

# Training activities and their XP contribution
TRAINING_ACTIVITIES = {
    "observe_player": {"xp": 2, "description": "Watching player perform skill"},
    "assist_player": {"xp": 5, "description": "Assisting player with task"},
    "practice_alone": {"xp": 3, "description": "Independent practice"},
    "receive_lesson": {"xp": 10, "description": "Direct teaching from player"},
    "complete_task": {"xp": 8, "description": "Successfully completing related task"},
    "fail_and_learn": {"xp": 4, "description": "Learning from failure"},
    "study_materials": {"xp": 3, "description": "Studying texts or materials"},
    "teach_others": {"xp": 15, "description": "Teaching skill to another (requires Journeyman+)"}
}

# ============ Models ============

class TrainEntityRequest(BaseModel):
    trainer_id: str  # Player who is training
    entity_id: str   # NPC or AI being trained
    entity_type: str = "npc"  # "npc" or "ai_partner"
    skill_id: str
    activity: str    # From TRAINING_ACTIVITIES
    duration_minutes: int = 5
    context: Optional[str] = None  # Additional context about the training

class GetSkillProgressRequest(BaseModel):
    entity_id: str
    entity_type: str = "npc"

# ============ Database Helper ============

def get_db():
    from server import db
    return db

def get_mastery_level(xp: int) -> dict:
    """Get mastery level info based on XP"""
    current_level = "novice"
    for level_name, level_info in MASTERY_LEVELS.items():
        if xp >= level_info["xp_required"]:
            current_level = level_name
    return {"name": current_level, **MASTERY_LEVELS[current_level]}

def calculate_xp_gain(base_xp: int, skill_difficulty: float, trainer_skill_level: int = 1) -> int:
    """Calculate actual XP gain based on difficulty and trainer skill"""
    # Better trainers teach more effectively
    trainer_bonus = 1.0 + (trainer_skill_level * 0.1)
    # Harder skills give slightly more XP
    difficulty_bonus = skill_difficulty
    return int(base_xp * trainer_bonus * difficulty_bonus)

# ============ Endpoints ============

@ai_training_router.get("/skills")
async def get_trainable_skills():
    """Get all skills that can be trained"""
    by_category = {}
    for skill_id, skill in TRAINABLE_SKILLS.items():
        cat = skill["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append({"id": skill_id, **skill})
    
    return {
        "skills": TRAINABLE_SKILLS,
        "by_category": by_category,
        "categories": ["combat", "crafting", "magic", "social", "knowledge", "survival"],
        "mastery_levels": MASTERY_LEVELS
    }

@ai_training_router.get("/activities")
async def get_training_activities():
    """Get available training activities"""
    return {
        "activities": TRAINING_ACTIVITIES,
        "tip": "Different activities provide different XP amounts. Teaching others provides the most XP but requires Journeyman level."
    }

@ai_training_router.post("/train")
async def train_entity(request: TrainEntityRequest):
    """Train an NPC or AI partner in a skill"""
    db = get_db()
    
    # Validate skill
    if request.skill_id not in TRAINABLE_SKILLS:
        raise HTTPException(status_code=400, detail=f"Unknown skill: {request.skill_id}")
    
    # Validate activity
    if request.activity not in TRAINING_ACTIVITIES:
        raise HTTPException(status_code=400, detail=f"Unknown activity: {request.activity}")
    
    skill_info = TRAINABLE_SKILLS[request.skill_id]
    activity_info = TRAINING_ACTIVITIES[request.activity]
    
    # Get entity's current skill progress
    collection = "npc_skills" if request.entity_type == "npc" else "ai_partner_skills"
    
    skill_record = await db[collection].find_one({
        "entity_id": request.entity_id,
        "skill_id": request.skill_id
    })
    
    current_xp = skill_record.get("xp", 0) if skill_record else 0
    current_level = get_mastery_level(current_xp)
    
    # Check if teaching others requires minimum level
    if request.activity == "teach_others" and current_level["level"] < 4:
        raise HTTPException(
            status_code=400, 
            detail="Entity must be at least Journeyman level to teach others"
        )
    
    # Calculate XP gain
    base_xp = activity_info["xp"] * request.duration_minutes
    xp_gain = calculate_xp_gain(base_xp, skill_info["base_difficulty"])
    
    new_xp = current_xp + xp_gain
    new_level = get_mastery_level(new_xp)
    level_up = new_level["level"] > current_level["level"]
    
    # Update skill record
    training_log = {
        "trainer_id": request.trainer_id,
        "activity": request.activity,
        "xp_gained": xp_gain,
        "context": request.context,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    if skill_record:
        await db[collection].update_one(
            {"entity_id": request.entity_id, "skill_id": request.skill_id},
            {
                "$set": {
                    "xp": new_xp,
                    "mastery_level": new_level["name"],
                    "efficiency": new_level["efficiency"],
                    "last_trained": datetime.now(timezone.utc).isoformat()
                },
                "$push": {"training_log": {"$each": [training_log], "$slice": -50}}
            }
        )
    else:
        await db[collection].insert_one({
            "entity_id": request.entity_id,
            "skill_id": request.skill_id,
            "skill_name": request.skill_id.replace("_", " ").title(),
            "xp": new_xp,
            "mastery_level": new_level["name"],
            "efficiency": new_level["efficiency"],
            "first_trained": datetime.now(timezone.utc).isoformat(),
            "last_trained": datetime.now(timezone.utc).isoformat(),
            "training_log": [training_log]
        })
    
    # Award related skill XP (smaller amount)
    related_xp = xp_gain // 4
    for related_skill in skill_info.get("related", []):
        if related_skill in TRAINABLE_SKILLS:
            related_record = await db[collection].find_one({
                "entity_id": request.entity_id,
                "skill_id": related_skill
            })
            if related_record:
                await db[collection].update_one(
                    {"entity_id": request.entity_id, "skill_id": related_skill},
                    {"$inc": {"xp": related_xp}}
                )
    
    # Update entity's overall training stats
    entity_collection = "npcs" if request.entity_type == "npc" else "ai_partners"
    await db[entity_collection].update_one(
        {"id": request.entity_id},
        {
            "$inc": {"total_training_sessions": 1, "total_xp_earned": xp_gain},
            "$set": {"last_trained": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    response = {
        "success": True,
        "skill": request.skill_id,
        "activity": request.activity,
        "xp_gained": xp_gain,
        "total_xp": new_xp,
        "previous_level": current_level["name"],
        "current_level": new_level["name"],
        "efficiency": new_level["efficiency"],
        "level_up": level_up
    }
    
    if level_up:
        response["level_up_message"] = f"Congratulations! The entity has advanced to {new_level['name']} in {request.skill_id.replace('_', ' ').title()}!"
    
    return response

@ai_training_router.get("/entity/{entity_id}/skills")
async def get_entity_skills(entity_id: str, entity_type: str = "npc"):
    """Get all skills for an entity"""
    db = get_db()
    
    collection = "npc_skills" if entity_type == "npc" else "ai_partner_skills"
    
    skills = await db[collection].find(
        {"entity_id": entity_id},
        {"_id": 0}
    ).to_list(100)
    
    # Group by category
    by_category = {}
    for skill in skills:
        skill_info = TRAINABLE_SKILLS.get(skill["skill_id"], {})
        cat = skill_info.get("category", "other")
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(skill)
    
    # Calculate overall mastery
    total_xp = sum(s.get("xp", 0) for s in skills)
    master_skills = [s for s in skills if s.get("mastery_level") == "master" or s.get("mastery_level") == "grandmaster"]
    
    return {
        "entity_id": entity_id,
        "skills": skills,
        "by_category": by_category,
        "total_skills": len(skills),
        "total_xp": total_xp,
        "master_skills_count": len(master_skills),
        "overall_rating": "Master Artisan" if len(master_skills) >= 3 else "Skilled" if total_xp > 1000 else "Learning"
    }

@ai_training_router.get("/entity/{entity_id}/skill/{skill_id}")
async def get_entity_skill_detail(entity_id: str, skill_id: str, entity_type: str = "npc"):
    """Get detailed skill info for an entity"""
    db = get_db()
    
    if skill_id not in TRAINABLE_SKILLS:
        raise HTTPException(status_code=400, detail=f"Unknown skill: {skill_id}")
    
    collection = "npc_skills" if entity_type == "npc" else "ai_partner_skills"
    
    skill = await db[collection].find_one(
        {"entity_id": entity_id, "skill_id": skill_id},
        {"_id": 0}
    )
    
    if not skill:
        # Return empty skill
        return {
            "entity_id": entity_id,
            "skill_id": skill_id,
            "skill_name": skill_id.replace("_", " ").title(),
            "xp": 0,
            "mastery_level": "novice",
            "efficiency": 0.2,
            "training_log": [],
            "has_started": False
        }
    
    skill["has_started"] = True
    skill["xp_to_next_level"] = 0
    
    # Calculate XP to next level
    current_level_info = MASTERY_LEVELS.get(skill.get("mastery_level", "novice"))
    current_level_num = current_level_info["level"]
    
    for level_name, level_info in MASTERY_LEVELS.items():
        if level_info["level"] == current_level_num + 1:
            skill["xp_to_next_level"] = level_info["xp_required"] - skill.get("xp", 0)
            skill["next_level"] = level_name
            break
    
    return skill

@ai_training_router.get("/leaderboard/{skill_id}")
async def get_skill_leaderboard(skill_id: str, entity_type: str = "npc", limit: int = 10):
    """Get leaderboard for a specific skill"""
    db = get_db()
    
    if skill_id not in TRAINABLE_SKILLS:
        raise HTTPException(status_code=400, detail=f"Unknown skill: {skill_id}")
    
    collection = "npc_skills" if entity_type == "npc" else "ai_partner_skills"
    
    top_entities = await db[collection].find(
        {"skill_id": skill_id},
        {"_id": 0}
    ).sort("xp", -1).limit(limit).to_list(limit)
    
    # Enrich with entity names
    entity_collection = "npcs" if entity_type == "npc" else "ai_partners"
    for entry in top_entities:
        entity = await db[entity_collection].find_one({"id": entry["entity_id"]}, {"_id": 0, "name": 1})
        entry["entity_name"] = entity.get("name", "Unknown") if entity else "Unknown"
    
    return {
        "skill_id": skill_id,
        "skill_name": skill_id.replace("_", " ").title(),
        "leaderboard": top_entities
    }
