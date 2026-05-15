# NPC Services Router - Trained NPCs offer skill-based services
# When NPCs reach mastery levels, they can provide services back to players

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone, timedelta
import uuid
import logging
import secrets

npc_services_router = APIRouter(prefix="/npc-services", tags=["npc-services"])
logger = logging.getLogger(__name__)

# ============ Service Types by Skill Category ============

NPC_SERVICE_TYPES = {
    # Combat Services (require trained combat skills)
    "training_session": {
        "skill_category": "combat",
        "min_mastery": "journeyman",
        "name": "Combat Training Session",
        "description": "NPC trains player in combat techniques",
        "duration_minutes": 30,
        "base_cost_ve": 5.0,
        "player_xp_reward": 50,
        "cooldown_hours": 4
    },
    "sparring_match": {
        "skill_category": "combat",
        "min_mastery": "expert",
        "name": "Sparring Match",
        "description": "Practice combat against trained NPC",
        "duration_minutes": 15,
        "base_cost_ve": 3.0,
        "player_xp_reward": 30,
        "cooldown_hours": 2
    },
    "guard_duty": {
        "skill_category": "combat",
        "min_mastery": "apprentice",
        "name": "Guard Services",
        "description": "NPC guards player's structures/territory",
        "duration_minutes": 60,
        "base_cost_ve": 2.0,
        "passive_effect": "defense_boost",
        "cooldown_hours": 0
    },
    
    # Crafting Services (require trained crafting skills)
    "craft_weapon": {
        "skill_category": "crafting",
        "required_skill": "blacksmithing",
        "min_mastery": "journeyman",
        "name": "Forge Weapon",
        "description": "NPC crafts a weapon for the player",
        "duration_minutes": 45,
        "base_cost_ve": 15.0,
        "output": {"type": "weapon", "quality_bonus": 0.2},
        "cooldown_hours": 6
    },
    "craft_armor": {
        "skill_category": "crafting",
        "required_skill": "blacksmithing",
        "min_mastery": "expert",
        "name": "Forge Armor",
        "description": "NPC crafts armor for the player",
        "duration_minutes": 60,
        "base_cost_ve": 25.0,
        "output": {"type": "armor", "quality_bonus": 0.25},
        "cooldown_hours": 8
    },
    "brew_potion": {
        "skill_category": "crafting",
        "required_skill": "alchemy",
        "min_mastery": "apprentice",
        "name": "Brew Potion",
        "description": "NPC brews potions for the player",
        "duration_minutes": 20,
        "base_cost_ve": 8.0,
        "output": {"type": "potion", "quality_bonus": 0.15},
        "cooldown_hours": 2
    },
    "cook_meal": {
        "skill_category": "crafting",
        "required_skill": "cooking",
        "min_mastery": "student",
        "name": "Prepare Meal",
        "description": "NPC cooks a meal with buffs",
        "duration_minutes": 15,
        "base_cost_ve": 3.0,
        "output": {"type": "food", "buff_duration_minutes": 30},
        "cooldown_hours": 1
    },
    "repair_equipment": {
        "skill_category": "crafting",
        "required_skill": "blacksmithing",
        "min_mastery": "student",
        "name": "Repair Equipment",
        "description": "NPC repairs player's damaged equipment",
        "duration_minutes": 10,
        "base_cost_ve": 5.0,
        "effect": "full_repair",
        "cooldown_hours": 0
    },
    
    # Magic Services (require trained magic skills)
    "enchant_item": {
        "skill_category": "magic",
        "required_skill": "enchanting",
        "min_mastery": "expert",
        "name": "Enchant Item",
        "description": "NPC enchants player's equipment",
        "duration_minutes": 30,
        "base_cost_ve": 20.0,
        "output": {"type": "enchantment", "power_bonus": 0.3},
        "cooldown_hours": 12
    },
    "healing_service": {
        "skill_category": "magic",
        "required_skill": "healing",
        "min_mastery": "apprentice",
        "name": "Healing Service",
        "description": "NPC heals player's wounds",
        "duration_minutes": 5,
        "base_cost_ve": 2.0,
        "effect": "heal_full",
        "cooldown_hours": 1
    },
    "divination": {
        "skill_category": "magic",
        "required_skill": "divination",
        "min_mastery": "master",
        "name": "Fortune Reading",
        "description": "NPC reveals hidden knowledge or future events",
        "duration_minutes": 20,
        "base_cost_ve": 15.0,
        "output": {"type": "prophecy", "accuracy": 0.8},
        "cooldown_hours": 24
    },
    "buff_spell": {
        "skill_category": "magic",
        "min_mastery": "journeyman",
        "name": "Magical Buff",
        "description": "NPC casts beneficial spell on player",
        "duration_minutes": 5,
        "base_cost_ve": 5.0,
        "effect": "random_buff",
        "buff_duration_minutes": 60,
        "cooldown_hours": 2
    },
    
    # Social Services (require trained social skills)
    "trade_negotiation": {
        "skill_category": "social",
        "required_skill": "trade",
        "min_mastery": "journeyman",
        "name": "Trade Negotiation",
        "description": "NPC helps negotiate better prices",
        "duration_minutes": 15,
        "base_cost_ve": 3.0,
        "effect": "trade_discount",
        "discount_percent": 10,
        "cooldown_hours": 4
    },
    "diplomatic_aid": {
        "skill_category": "social",
        "required_skill": "diplomacy",
        "min_mastery": "expert",
        "name": "Diplomatic Assistance",
        "description": "NPC helps improve faction relations",
        "duration_minutes": 30,
        "base_cost_ve": 10.0,
        "effect": "reputation_boost",
        "rep_boost": 50,
        "cooldown_hours": 24
    },
    "charisma_lesson": {
        "skill_category": "social",
        "required_skill": "charm",
        "min_mastery": "master",
        "name": "Charisma Lesson",
        "description": "NPC teaches persuasion techniques",
        "duration_minutes": 45,
        "base_cost_ve": 12.0,
        "player_xp_reward": 75,
        "skill_boost": "charm",
        "cooldown_hours": 8
    },
    
    # Knowledge Services (require trained knowledge skills)
    "lore_teaching": {
        "skill_category": "knowledge",
        "required_skill": "lore",
        "min_mastery": "expert",
        "name": "Lore Lesson",
        "description": "NPC teaches world lore and history",
        "duration_minutes": 30,
        "base_cost_ve": 8.0,
        "player_xp_reward": 60,
        "reveals": "hidden_lore",
        "cooldown_hours": 6
    },
    "language_lesson": {
        "skill_category": "knowledge",
        "required_skill": "languages",
        "min_mastery": "journeyman",
        "name": "Language Lesson",
        "description": "NPC teaches new language skills",
        "duration_minutes": 45,
        "base_cost_ve": 10.0,
        "player_xp_reward": 50,
        "cooldown_hours": 8
    },
    "research_assistance": {
        "skill_category": "knowledge",
        "required_skill": "arcane_theory",
        "min_mastery": "master",
        "name": "Research Aid",
        "description": "NPC assists with magical research",
        "duration_minutes": 60,
        "base_cost_ve": 20.0,
        "effect": "discovery_boost",
        "boost_percent": 25,
        "cooldown_hours": 12
    },
    
    # Survival Services (require trained survival skills)
    "tracking_service": {
        "skill_category": "survival",
        "required_skill": "tracking",
        "min_mastery": "apprentice",
        "name": "Tracking Service",
        "description": "NPC tracks creature or person",
        "duration_minutes": 30,
        "base_cost_ve": 5.0,
        "effect": "locate_target",
        "cooldown_hours": 4
    },
    "gathering_expedition": {
        "skill_category": "survival",
        "required_skill": "herbalism",
        "min_mastery": "journeyman",
        "name": "Gathering Expedition",
        "description": "NPC gathers rare materials",
        "duration_minutes": 60,
        "base_cost_ve": 8.0,
        "output": {"type": "materials", "rarity": "rare"},
        "cooldown_hours": 6
    },
    "survival_training": {
        "skill_category": "survival",
        "required_skill": "survival",
        "min_mastery": "expert",
        "name": "Survival Training",
        "description": "NPC teaches wilderness survival",
        "duration_minutes": 45,
        "base_cost_ve": 10.0,
        "player_xp_reward": 55,
        "effect": "survival_buff",
        "cooldown_hours": 8
    }
}

# Mastery level requirements (from ai_training_router)
MASTERY_REQUIREMENTS = {
    "novice": 1,
    "student": 2,
    "apprentice": 3,
    "journeyman": 4,
    "expert": 5,
    "master": 6,
    "grandmaster": 7
}

# Quality multipliers based on NPC mastery
QUALITY_MULTIPLIERS = {
    "novice": 0.5,
    "student": 0.7,
    "apprentice": 0.85,
    "journeyman": 1.0,
    "expert": 1.15,
    "master": 1.3,
    "grandmaster": 1.5
}

# ============ Models ============

class RequestServiceRequest(BaseModel):
    player_id: str
    npc_id: str
    service_type: str
    payment_method: str = "ve"  # "ve" or "gold"
    custom_params: Optional[Dict[str, Any]] = None

class ServiceResult(BaseModel):
    service_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    service_type: str
    npc_id: str
    player_id: str
    status: str  # "in_progress", "completed", "failed"
    quality_rating: float
    cost_paid: float
    output: Optional[Dict[str, Any]] = None
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None

# ============ Database Helper ============

def get_db():
    from server import db
    return db

# ============ Helper Functions ============

def get_mastery_level_num(mastery_name: str) -> int:
    """Convert mastery name to numeric level"""
    return MASTERY_REQUIREMENTS.get(mastery_name, 0)

def can_provide_service(npc_mastery: str, required_mastery: str) -> bool:
    """Check if NPC has sufficient mastery for service"""
    npc_level = get_mastery_level_num(npc_mastery)
    required_level = get_mastery_level_num(required_mastery)
    return npc_level >= required_level

def calculate_service_quality(npc_mastery: str, service_config: dict) -> float:
    """Calculate service quality based on NPC mastery"""
    base_quality = QUALITY_MULTIPLIERS.get(npc_mastery, 1.0)
    # Add some randomness
    variance = secrets.randbelow(20) / 100  # 0-0.19 variance
    return min(base_quality + variance, 2.0)

def calculate_service_cost(service_config: dict, npc_mastery: str) -> float:
    """Calculate cost based on service and NPC skill level"""
    base_cost = service_config.get("base_cost_ve", 0)
    # Higher mastery NPCs charge more (premium service)
    mastery_mult = QUALITY_MULTIPLIERS.get(npc_mastery, 1.0)
    return base_cost * (0.8 + mastery_mult * 0.3)

# ============ Endpoints ============

@npc_services_router.get("/types")
async def get_service_types():
    """Get all available NPC service types"""
    return {
        "services": NPC_SERVICE_TYPES,
        "mastery_requirements": MASTERY_REQUIREMENTS,
        "quality_multipliers": QUALITY_MULTIPLIERS
    }

@npc_services_router.get("/npc/{npc_id}/available")
async def get_npc_available_services(npc_id: str):
    """Get services an NPC can provide based on their trained skills"""
    db = get_db()
    
    # Get NPC's trained skills
    skills = await db.npc_skills.find(
        {"entity_id": npc_id},
        {"_id": 0}
    ).to_list(100)
    
    if not skills:
        return {
            "npc_id": npc_id,
            "available_services": [],
            "message": "NPC has no trained skills yet"
        }
    
    # Build skill lookup
    skill_levels = {}
    for skill in skills:
        skill_id = skill.get("skill_id")
        mastery = skill.get("mastery_level", "novice")
        skill_levels[skill_id] = mastery
    
    # Find matching services
    available_services = []
    
    for service_id, service_config in NPC_SERVICE_TYPES.items():
        required_skill = service_config.get("required_skill")
        skill_category = service_config.get("skill_category")
        min_mastery = service_config.get("min_mastery", "novice")
        
        # Check if NPC has required skill at required level
        matching_skills = []
        
        if required_skill:
            # Specific skill required
            if required_skill in skill_levels:
                if can_provide_service(skill_levels[required_skill], min_mastery):
                    matching_skills.append(required_skill)
        else:
            # Any skill in category works
            from ai_training_router import TRAINABLE_SKILLS
            for skill_id, skill_info in TRAINABLE_SKILLS.items():
                if skill_info.get("category") == skill_category:
                    if skill_id in skill_levels:
                        if can_provide_service(skill_levels[skill_id], min_mastery):
                            matching_skills.append(skill_id)
        
        if matching_skills:
            # Get best skill level for cost/quality calculation
            best_mastery = max(
                (skill_levels.get(s, "novice") for s in matching_skills),
                key=get_mastery_level_num
            )
            
            cost = calculate_service_cost(service_config, best_mastery)
            quality = QUALITY_MULTIPLIERS.get(best_mastery, 1.0)
            
            available_services.append({
                "service_id": service_id,
                "name": service_config["name"],
                "description": service_config["description"],
                "category": skill_category,
                "npc_mastery": best_mastery,
                "quality_rating": quality,
                "cost_ve": round(cost, 2),
                "duration_minutes": service_config["duration_minutes"],
                "cooldown_hours": service_config.get("cooldown_hours", 0),
                "matching_skills": matching_skills
            })
    
    return {
        "npc_id": npc_id,
        "skill_count": len(skills),
        "available_services": available_services,
        "total_services": len(available_services)
    }

@npc_services_router.post("/request")
async def request_service(data: RequestServiceRequest):
    """Player requests a service from trained NPC"""
    db = get_db()
    
    # Validate service type
    if data.service_type not in NPC_SERVICE_TYPES:
        raise HTTPException(status_code=400, detail=f"Unknown service: {data.service_type}")
    
    service_config = NPC_SERVICE_TYPES[data.service_type]
    
    # Check if NPC can provide this service
    available = await get_npc_available_services(data.npc_id)
    matching = [s for s in available["available_services"] if s["service_id"] == data.service_type]
    
    if not matching:
        raise HTTPException(
            status_code=400, 
            detail="NPC cannot provide this service. Required skill mastery not met."
        )
    
    service_info = matching[0]
    cost = service_info["cost_ve"]
    
    # Check cooldown
    last_service = await db.npc_service_history.find_one(
        {
            "npc_id": data.npc_id,
            "player_id": data.player_id,
            "service_type": data.service_type,
            "status": "completed"
        },
        sort=[("completed_at", -1)]
    )
    
    if last_service:
        cooldown_hours = service_config.get("cooldown_hours", 0)
        if cooldown_hours > 0:
            last_time = datetime.fromisoformat(last_service["completed_at"].replace("Z", "+00:00"))
            cooldown_end = last_time + timedelta(hours=cooldown_hours)
            if datetime.now(timezone.utc) < cooldown_end:
                remaining = (cooldown_end - datetime.now(timezone.utc)).total_seconds() / 3600
                raise HTTPException(
                    status_code=400,
                    detail=f"Service on cooldown. Available in {remaining:.1f} hours."
                )
    
    # Check player balance
    if data.payment_method == "ve":
        wallet = await db.entity_wallets.find_one({"entity_id": data.player_id})
        balance = wallet.get("balance_ve", 0) if wallet else 0
        if balance < cost:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient VE$ balance. Have: {balance:.2f}, Need: {cost:.2f}"
            )
        
        # Deduct payment
        await db.entity_wallets.update_one(
            {"entity_id": data.player_id},
            {"$inc": {"balance_ve": -cost}}
        )
        
        # Pay NPC
        await db.entity_wallets.update_one(
            {"entity_id": data.npc_id},
            {
                "$inc": {"balance_ve": cost * 0.9, "total_earned": cost * 0.9},
                "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
            },
            upsert=True
        )
    else:
        # Gold payment (convert from resources)
        profile = await db.user_profiles.find_one({"id": data.player_id})
        gold = profile.get("resources", {}).get("gold", 0) if profile else 0
        gold_cost = int(cost * 10)  # 1 VE$ = 10 gold
        
        if gold < gold_cost:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient gold. Have: {gold}, Need: {gold_cost}"
            )
        
        await db.user_profiles.update_one(
            {"id": data.player_id},
            {"$inc": {"resources.gold": -gold_cost}}
        )
    
    # Calculate quality
    quality = calculate_service_quality(service_info["npc_mastery"], service_config)
    
    # Generate service output based on type
    output = generate_service_output(data.service_type, service_config, quality, data.custom_params)
    
    # Create service record
    service_result = ServiceResult(
        service_type=data.service_type,
        npc_id=data.npc_id,
        player_id=data.player_id,
        status="completed",
        quality_rating=quality,
        cost_paid=cost,
        output=output,
        completed_at=datetime.now(timezone.utc).isoformat()
    )
    
    await db.npc_service_history.insert_one(service_result.dict())
    
    # Apply service effects
    await apply_service_effects(db, data.player_id, service_config, output, quality)
    
    # Award XP to NPC for providing service
    await award_npc_service_xp(db, data.npc_id, data.service_type, service_config)
    
    return {
        "success": True,
        "service_id": service_result.service_id,
        "service_type": data.service_type,
        "quality_rating": round(quality, 2),
        "cost_paid": round(cost, 2),
        "output": output,
        "npc_id": data.npc_id
    }

def generate_service_output(service_type: str, config: dict, quality: float, custom_params: dict = None) -> Dict[str, Any]:
    """Generate output based on service type and quality"""
    output = {
        "service_type": service_type,
        "quality": quality,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    if "output" in config:
        base_output = config["output"].copy()
        
        if base_output.get("type") == "weapon":
            damage_bonus = int(10 * quality * base_output.get("quality_bonus", 0.2))
            output["item"] = {
                "type": "weapon",
                "name": f"NPC-Forged Blade (Quality: {int(quality*100)}%)",
                "damage_bonus": damage_bonus,
                "durability": int(100 * quality)
            }
        
        elif base_output.get("type") == "armor":
            defense_bonus = int(15 * quality * base_output.get("quality_bonus", 0.25))
            output["item"] = {
                "type": "armor",
                "name": f"NPC-Forged Armor (Quality: {int(quality*100)}%)",
                "defense_bonus": defense_bonus,
                "durability": int(100 * quality)
            }
        
        elif base_output.get("type") == "potion":
            output["item"] = {
                "type": "potion",
                "name": "Alchemist's Brew",
                "potency": quality,
                "effect": secrets.choice(["health", "mana", "stamina", "speed"])
            }
        
        elif base_output.get("type") == "food":
            buff_duration = int(config.get("buff_duration_minutes", 30) * quality)
            output["item"] = {
                "type": "food",
                "name": "Cooked Meal",
                "buff_type": secrets.choice(["strength", "agility", "intelligence"]),
                "buff_amount": int(5 * quality),
                "duration_minutes": buff_duration
            }
        
        elif base_output.get("type") == "enchantment":
            output["enchantment"] = {
                "power": int(10 * quality * base_output.get("power_bonus", 0.3)),
                "type": secrets.choice(["fire", "ice", "lightning", "shadow", "holy"]),
                "duration_uses": int(50 * quality)
            }
        
        elif base_output.get("type") == "prophecy":
            output["prophecy"] = {
                "accuracy": base_output.get("accuracy", 0.8) * quality,
                "revealed": "A glimpse of the future awaits..."
            }
        
        elif base_output.get("type") == "materials":
            output["materials"] = {
                "count": int(3 * quality),
                "rarity": base_output.get("rarity", "common"),
                "types": ["herb", "ore", "crystal"][:int(quality * 3)]
            }
    
    # XP rewards
    if "player_xp_reward" in config:
        output["xp_awarded"] = int(config["player_xp_reward"] * quality)
    
    # Effect-based outputs
    effect = config.get("effect")
    if effect == "heal_full":
        output["healing"] = {"amount": "full", "quality_mult": quality}
    elif effect == "random_buff":
        output["buff"] = {
            "type": secrets.choice(["strength", "speed", "defense", "mana_regen"]),
            "amount": int(10 * quality),
            "duration_minutes": config.get("buff_duration_minutes", 60)
        }
    elif effect == "trade_discount":
        output["discount"] = {
            "percent": int(config.get("discount_percent", 10) * quality),
            "duration_hours": 4
        }
    elif effect == "reputation_boost":
        output["reputation"] = {
            "amount": int(config.get("rep_boost", 50) * quality)
        }
    
    return output

async def apply_service_effects(db, player_id: str, config: dict, output: dict, quality: float):
    """Apply service effects to player"""
    
    # Award XP
    if "xp_awarded" in output:
        await db.user_profiles.update_one(
            {"id": player_id},
            {"$inc": {"xp": output["xp_awarded"]}}
        )
    
    # Apply buffs
    if "buff" in output:
        buff = output["buff"]
        expires = datetime.now(timezone.utc) + timedelta(minutes=buff["duration_minutes"])
        await db.active_buffs.insert_one({
            "player_id": player_id,
            "buff_type": buff["type"],
            "amount": buff["amount"],
            "source": "npc_service",
            "expires_at": expires.isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    # Apply healing
    if "healing" in output and output["healing"]["amount"] == "full":
        await db.characters.update_one(
            {"user_id": player_id},
            {"$set": {"health": 100, "mana": 100, "stamina": 100}}
        )
    
    # Apply trade discount
    if "discount" in output:
        expires = datetime.now(timezone.utc) + timedelta(hours=output["discount"]["duration_hours"])
        await db.active_discounts.insert_one({
            "player_id": player_id,
            "discount_percent": output["discount"]["percent"],
            "source": "npc_service",
            "expires_at": expires.isoformat()
        })
    
    # Apply reputation boost
    if "reputation" in output:
        await db.user_profiles.update_one(
            {"id": player_id},
            {"$inc": {"reputation": output["reputation"]["amount"]}}
        )

async def award_npc_service_xp(db, npc_id: str, service_type: str, config: dict):
    """Award XP to NPC for providing service"""
    service_xp = 15  # Base XP for providing service
    
    required_skill = config.get("required_skill")
    
    # Award XP to related skill(s)
    if required_skill:
        await db.npc_skills.update_one(
            {"entity_id": npc_id, "skill_id": required_skill},
            {
                "$inc": {"xp": service_xp},
                "$set": {"last_service": datetime.now(timezone.utc).isoformat()}
            }
        )
    
    # Update NPC service stats
    await db.npcs.update_one(
        {"id": npc_id},
        {
            "$inc": {"services_provided": 1, "service_xp": service_xp},
            "$set": {"last_service_at": datetime.now(timezone.utc).isoformat()}
        }
    )

@npc_services_router.get("/history/{player_id}")
async def get_player_service_history(player_id: str, limit: int = 50):
    """Get player's service history"""
    db = get_db()
    
    history = await db.npc_service_history.find(
        {"player_id": player_id},
        {"_id": 0}
    ).sort("completed_at", -1).limit(limit).to_list(limit)
    
    total_spent = sum(h.get("cost_paid", 0) for h in history)
    
    return {
        "player_id": player_id,
        "history": history,
        "total_services": len(history),
        "total_spent": round(total_spent, 2)
    }

@npc_services_router.get("/npc/{npc_id}/stats")
async def get_npc_service_stats(npc_id: str):
    """Get NPC's service provision statistics"""
    db = get_db()
    
    # Service counts by type
    pipeline = [
        {"$match": {"npc_id": npc_id, "status": "completed"}},
        {"$group": {"_id": "$service_type", "count": {"$sum": 1}, "revenue": {"$sum": "$cost_paid"}}}
    ]
    by_type = await db.npc_service_history.aggregate(pipeline).to_list(50)
    
    # Total stats
    total_services = sum(t["count"] for t in by_type)
    total_revenue = sum(t["revenue"] for t in by_type)
    
    # Average quality
    pipeline = [
        {"$match": {"npc_id": npc_id, "status": "completed"}},
        {"$group": {"_id": None, "avg_quality": {"$avg": "$quality_rating"}}}
    ]
    quality = await db.npc_service_history.aggregate(pipeline).to_list(1)
    avg_quality = quality[0]["avg_quality"] if quality else 0
    
    return {
        "npc_id": npc_id,
        "total_services": total_services,
        "total_revenue": round(total_revenue, 2),
        "average_quality": round(avg_quality, 2),
        "by_service_type": {t["_id"]: {"count": t["count"], "revenue": round(t["revenue"], 2)} for t in by_type}
    }

@npc_services_router.get("/leaderboard")
async def get_service_provider_leaderboard(limit: int = 20):
    """Get top NPCs by services provided"""
    db = get_db()
    
    pipeline = [
        {"$match": {"status": "completed"}},
        {"$group": {
            "_id": "$npc_id",
            "services": {"$sum": 1},
            "revenue": {"$sum": "$cost_paid"},
            "avg_quality": {"$avg": "$quality_rating"}
        }},
        {"$sort": {"revenue": -1}},
        {"$limit": limit}
    ]
    
    leaders = await db.npc_service_history.aggregate(pipeline).to_list(limit)
    
    # Get NPC names
    for entry in leaders:
        npc = await db.npcs.find_one({"id": entry["_id"]}, {"name": 1})
        entry["npc_name"] = npc.get("name", "Unknown") if npc else "Unknown"
        entry["avg_quality"] = round(entry["avg_quality"], 2)
        entry["revenue"] = round(entry["revenue"], 2)
    
    return {
        "leaderboard": leaders,
        "metric": "revenue"
    }

@npc_services_router.get("/categories")
async def get_service_categories():
    """Get services organized by category"""
    categories = {}
    
    for service_id, config in NPC_SERVICE_TYPES.items():
        category = config.get("skill_category")
        if category not in categories:
            categories[category] = []
        
        categories[category].append({
            "service_id": service_id,
            "name": config["name"],
            "description": config["description"],
            "min_mastery": config.get("min_mastery", "novice"),
            "required_skill": config.get("required_skill"),
            "base_cost_ve": config.get("base_cost_ve", 0),
            "duration_minutes": config.get("duration_minutes", 0),
            "cooldown_hours": config.get("cooldown_hours", 0)
        })
    
    return {
        "categories": categories,
        "category_list": list(categories.keys()),
        "total_services": len(NPC_SERVICE_TYPES)
    }
