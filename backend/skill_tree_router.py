"""
Skill Tree System Router
Active skills for actions, passive skills from titles
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import uuid
import os
from motor.motor_asyncio import AsyncIOMotorClient

skill_tree_router = APIRouter(prefix="/skill-trees", tags=["skill-trees"])

# Database connection
_db = None

def get_skill_db():
    global _db
    if _db is None:
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        db_name = os.environ.get("DB_NAME", "ai_village_echoes")
        client = AsyncIOMotorClient(mongo_url)
        _db = client[db_name]
    return _db

# ============ Skill Tree Definitions ============

SKILL_TREES = {
    "combat": {
        "name": "Combat Mastery",
        "description": "Skills for defeating enemies and protecting allies",
        "icon": "swords",
        "color": "#EF4444",
        "tiers": {
            1: {
                "power_strike": {
                    "name": "Power Strike",
                    "type": "active",
                    "description": "Deal 150% weapon damage to a single target",
                    "cooldown_seconds": 8,
                    "resource_cost": {"stamina": 15},
                    "effects": {"damage_multiplier": 1.5},
                    "unlocks_at_skill_level": 1
                },
                "defensive_stance": {
                    "name": "Defensive Stance",
                    "type": "active",
                    "description": "Reduce incoming damage by 30% for 10 seconds",
                    "cooldown_seconds": 30,
                    "resource_cost": {"stamina": 20},
                    "effects": {"damage_reduction": 0.3, "duration": 10},
                    "unlocks_at_skill_level": 1
                }
            },
            2: {
                "whirlwind": {
                    "name": "Whirlwind",
                    "type": "active",
                    "description": "Deal 100% weapon damage to all nearby enemies",
                    "cooldown_seconds": 15,
                    "resource_cost": {"stamina": 30},
                    "effects": {"damage_multiplier": 1.0, "aoe_radius": 5},
                    "unlocks_at_skill_level": 10,
                    "requires": ["power_strike"]
                },
                "battle_cry": {
                    "name": "Battle Cry",
                    "type": "active",
                    "description": "Increase party damage by 15% for 20 seconds",
                    "cooldown_seconds": 60,
                    "resource_cost": {"stamina": 25},
                    "effects": {"party_damage_boost": 0.15, "duration": 20},
                    "unlocks_at_skill_level": 10,
                    "requires": ["defensive_stance"]
                }
            },
            3: {
                "executioner": {
                    "name": "Executioner",
                    "type": "active",
                    "description": "Deal 300% damage to enemies below 30% health",
                    "cooldown_seconds": 45,
                    "resource_cost": {"stamina": 40},
                    "effects": {"damage_multiplier": 3.0, "health_threshold": 0.3},
                    "unlocks_at_skill_level": 25,
                    "requires": ["whirlwind"]
                },
                "iron_will": {
                    "name": "Iron Will",
                    "type": "passive",
                    "description": "Permanently increase max health by 10%",
                    "effects": {"max_health_bonus": 0.1},
                    "unlocks_at_skill_level": 25,
                    "requires": ["battle_cry"]
                }
            },
            4: {
                "berserker_rage": {
                    "name": "Berserker Rage",
                    "type": "active",
                    "description": "Enter rage mode: +50% damage, +30% attack speed, -20% defense for 15s",
                    "cooldown_seconds": 120,
                    "resource_cost": {"stamina": 50, "health": 10},
                    "effects": {"damage_boost": 0.5, "attack_speed": 0.3, "defense_penalty": -0.2, "duration": 15},
                    "unlocks_at_skill_level": 50,
                    "requires": ["executioner", "iron_will"]
                }
            }
        }
    },
    "magic": {
        "name": "Arcane Arts",
        "description": "Harness mystical energies to cast powerful spells",
        "icon": "sparkles",
        "color": "#8B5CF6",
        "tiers": {
            1: {
                "arcane_bolt": {
                    "name": "Arcane Bolt",
                    "type": "active",
                    "description": "Launch a bolt of arcane energy dealing magic damage",
                    "cooldown_seconds": 3,
                    "resource_cost": {"mana": 10},
                    "effects": {"magic_damage": 50},
                    "unlocks_at_skill_level": 1
                },
                "mana_shield": {
                    "name": "Mana Shield",
                    "type": "active",
                    "description": "Create a shield that absorbs damage using mana",
                    "cooldown_seconds": 20,
                    "resource_cost": {"mana": 30},
                    "effects": {"shield_strength": 100, "duration": 15},
                    "unlocks_at_skill_level": 1
                }
            },
            2: {
                "chain_lightning": {
                    "name": "Chain Lightning",
                    "type": "active",
                    "description": "Lightning that jumps between up to 4 targets",
                    "cooldown_seconds": 12,
                    "resource_cost": {"mana": 35},
                    "effects": {"magic_damage": 80, "chain_targets": 4, "chain_damage_reduction": 0.2},
                    "unlocks_at_skill_level": 10,
                    "requires": ["arcane_bolt"]
                },
                "teleport": {
                    "name": "Teleport",
                    "type": "active",
                    "description": "Instantly teleport a short distance",
                    "cooldown_seconds": 15,
                    "resource_cost": {"mana": 25},
                    "effects": {"teleport_range": 20},
                    "unlocks_at_skill_level": 10,
                    "requires": ["mana_shield"]
                }
            },
            3: {
                "meteor_strike": {
                    "name": "Meteor Strike",
                    "type": "active",
                    "description": "Call down a meteor dealing massive AoE damage",
                    "cooldown_seconds": 60,
                    "resource_cost": {"mana": 80},
                    "effects": {"magic_damage": 300, "aoe_radius": 10, "burn_damage": 20},
                    "unlocks_at_skill_level": 25,
                    "requires": ["chain_lightning"]
                },
                "arcane_mastery": {
                    "name": "Arcane Mastery",
                    "type": "passive",
                    "description": "Increase all magic damage by 15%",
                    "effects": {"magic_damage_bonus": 0.15},
                    "unlocks_at_skill_level": 25,
                    "requires": ["teleport"]
                }
            },
            4: {
                "time_stop": {
                    "name": "Time Stop",
                    "type": "active",
                    "description": "Freeze time for all enemies for 5 seconds",
                    "cooldown_seconds": 180,
                    "resource_cost": {"mana": 100},
                    "effects": {"freeze_duration": 5, "aoe_radius": 15},
                    "unlocks_at_skill_level": 50,
                    "requires": ["meteor_strike", "arcane_mastery"]
                }
            }
        }
    },
    "crafting": {
        "name": "Master Craftsman",
        "description": "Create powerful items and equipment",
        "icon": "hammer",
        "color": "#F59E0B",
        "tiers": {
            1: {
                "basic_smithing": {
                    "name": "Basic Smithing",
                    "type": "passive",
                    "description": "Craft basic weapons and tools",
                    "effects": {"unlocks_recipes": ["iron_sword", "iron_pickaxe", "iron_axe"]},
                    "unlocks_at_skill_level": 1
                },
                "salvage": {
                    "name": "Salvage",
                    "type": "active",
                    "description": "Break down items for 50% of their materials",
                    "cooldown_seconds": 0,
                    "resource_cost": {},
                    "effects": {"salvage_rate": 0.5},
                    "unlocks_at_skill_level": 1
                }
            },
            2: {
                "efficient_crafting": {
                    "name": "Efficient Crafting",
                    "type": "passive",
                    "description": "Reduce material costs by 15%",
                    "effects": {"material_cost_reduction": 0.15},
                    "unlocks_at_skill_level": 10,
                    "requires": ["basic_smithing"]
                },
                "quality_boost": {
                    "name": "Quality Boost",
                    "type": "passive",
                    "description": "10% chance to craft at higher quality",
                    "effects": {"quality_upgrade_chance": 0.1},
                    "unlocks_at_skill_level": 10,
                    "requires": ["salvage"]
                }
            },
            3: {
                "master_smith": {
                    "name": "Master Smith",
                    "type": "passive",
                    "description": "Craft legendary weapons. +25% weapon stats",
                    "effects": {"unlocks_legendary": True, "weapon_stat_bonus": 0.25},
                    "unlocks_at_skill_level": 25,
                    "requires": ["efficient_crafting", "quality_boost"]
                }
            },
            4: {
                "legendary_enchanter": {
                    "name": "Legendary Enchanter",
                    "type": "passive",
                    "description": "Add magical properties to any crafted item",
                    "effects": {"enchantment_slots": 2, "enchant_power_bonus": 0.3},
                    "unlocks_at_skill_level": 50,
                    "requires": ["master_smith"]
                }
            }
        }
    },
    "social": {
        "name": "Silver Tongue",
        "description": "Influence NPCs and players through charisma",
        "icon": "message-circle",
        "color": "#EC4899",
        "tiers": {
            1: {
                "persuasion": {
                    "name": "Persuasion",
                    "type": "passive",
                    "description": "5% better prices when trading",
                    "effects": {"trade_discount": 0.05},
                    "unlocks_at_skill_level": 1
                },
                "gather_intel": {
                    "name": "Gather Intel",
                    "type": "active",
                    "description": "Learn hidden information from NPCs",
                    "cooldown_seconds": 300,
                    "resource_cost": {"gold": 10},
                    "effects": {"reveals_secrets": True},
                    "unlocks_at_skill_level": 1
                }
            },
            2: {
                "haggle": {
                    "name": "Haggle",
                    "type": "active",
                    "description": "Attempt to reduce a price by up to 20%",
                    "cooldown_seconds": 60,
                    "resource_cost": {},
                    "effects": {"max_discount": 0.2, "success_chance": 0.7},
                    "unlocks_at_skill_level": 10,
                    "requires": ["persuasion"]
                },
                "inspire": {
                    "name": "Inspire",
                    "type": "active",
                    "description": "Boost party morale, +10% all stats for 60s",
                    "cooldown_seconds": 300,
                    "resource_cost": {},
                    "effects": {"party_stat_boost": 0.1, "duration": 60},
                    "unlocks_at_skill_level": 10,
                    "requires": ["gather_intel"]
                }
            },
            3: {
                "silver_tongue": {
                    "name": "Silver Tongue",
                    "type": "passive",
                    "description": "Unlock special dialogue options. +15% reputation gains",
                    "effects": {"special_dialogues": True, "reputation_bonus": 0.15},
                    "unlocks_at_skill_level": 25,
                    "requires": ["haggle", "inspire"]
                }
            },
            4: {
                "diplomat": {
                    "name": "Master Diplomat",
                    "type": "passive",
                    "description": "Prevent faction wars. Access to all faction vendors",
                    "effects": {"faction_peace": True, "all_faction_access": True},
                    "unlocks_at_skill_level": 50,
                    "requires": ["silver_tongue"]
                }
            }
        }
    },
    "survival": {
        "name": "Wilderness Expert",
        "description": "Thrive in harsh environments and find hidden resources",
        "icon": "compass",
        "color": "#22C55E",
        "tiers": {
            1: {
                "foraging": {
                    "name": "Foraging",
                    "type": "passive",
                    "description": "Find herbs and food in the wild",
                    "effects": {"forage_chance": 0.3, "forage_quality": 1.0},
                    "unlocks_at_skill_level": 1
                },
                "tracking": {
                    "name": "Tracking",
                    "type": "active",
                    "description": "Reveal nearby creatures and resources on map",
                    "cooldown_seconds": 30,
                    "resource_cost": {},
                    "effects": {"tracking_radius": 50, "duration": 60},
                    "unlocks_at_skill_level": 1
                }
            },
            2: {
                "camouflage": {
                    "name": "Camouflage",
                    "type": "active",
                    "description": "Become invisible to creatures for 20 seconds",
                    "cooldown_seconds": 60,
                    "resource_cost": {"stamina": 20},
                    "effects": {"stealth_duration": 20},
                    "unlocks_at_skill_level": 10,
                    "requires": ["foraging"]
                },
                "trap_setting": {
                    "name": "Trap Setting",
                    "type": "active",
                    "description": "Place a trap that damages and slows enemies",
                    "cooldown_seconds": 45,
                    "resource_cost": {"materials": 5},
                    "effects": {"trap_damage": 100, "slow_percent": 0.5},
                    "unlocks_at_skill_level": 10,
                    "requires": ["tracking"]
                }
            },
            3: {
                "master_hunter": {
                    "name": "Master Hunter",
                    "type": "passive",
                    "description": "+50% damage to creatures. Double loot drops",
                    "effects": {"creature_damage_bonus": 0.5, "loot_multiplier": 2.0},
                    "unlocks_at_skill_level": 25,
                    "requires": ["camouflage", "trap_setting"]
                }
            },
            4: {
                "one_with_nature": {
                    "name": "One With Nature",
                    "type": "passive",
                    "description": "Creatures don't attack unless provoked. Tame wild beasts",
                    "effects": {"passive_creatures": True, "can_tame": True},
                    "unlocks_at_skill_level": 50,
                    "requires": ["master_hunter"]
                }
            }
        }
    }
}

# ============ Title Passive Skills ============

TITLE_PASSIVES = {
    "newcomer": {
        "title_name": "Newcomer",
        "passives": [
            {"name": "Fresh Start", "description": "+10% XP gain for first 10 levels", "effect": {"xp_bonus": 0.1, "max_level": 10}}
        ]
    },
    "explorer": {
        "title_name": "Explorer",
        "passives": [
            {"name": "Wanderer's Pace", "description": "+5% movement speed", "effect": {"movement_speed": 0.05}},
            {"name": "Discovery Bonus", "description": "+20% exploration XP", "effect": {"exploration_xp_bonus": 0.2}}
        ]
    },
    "hero": {
        "title_name": "Hero of the Village",
        "passives": [
            {"name": "Heroic Presence", "description": "+10% party damage when leader", "effect": {"party_damage_when_leader": 0.1}},
            {"name": "Villager's Friend", "description": "+15% reputation with all factions", "effect": {"reputation_bonus": 0.15}}
        ]
    },
    "champion": {
        "title_name": "Champion",
        "passives": [
            {"name": "Champion's Might", "description": "+15% damage, +10% defense", "effect": {"damage_bonus": 0.15, "defense_bonus": 0.1}},
            {"name": "Indomitable", "description": "50% chance to survive fatal blow with 1 HP", "effect": {"death_save_chance": 0.5}}
        ]
    },
    "legend": {
        "title_name": "Living Legend",
        "passives": [
            {"name": "Legendary Aura", "description": "+20% all stats", "effect": {"all_stats_bonus": 0.2}},
            {"name": "Inspiring Presence", "description": "Party members gain +10% XP", "effect": {"party_xp_bonus": 0.1}},
            {"name": "Fame", "description": "NPCs offer special quests and items", "effect": {"special_npc_access": True}}
        ]
    },
    "wealthy": {
        "title_name": "Wealthy Merchant",
        "passives": [
            {"name": "Golden Touch", "description": "+25% gold from all sources", "effect": {"gold_bonus": 0.25}},
            {"name": "Market Mastery", "description": "Access to exclusive items", "effect": {"exclusive_shop_access": True}}
        ]
    },
    "master_crafter": {
        "title_name": "Master Crafter",
        "passives": [
            {"name": "Artisan's Touch", "description": "+30% crafting speed", "effect": {"crafting_speed": 0.3}},
            {"name": "Material Efficiency", "description": "20% chance to not consume materials", "effect": {"material_save_chance": 0.2}}
        ]
    },
    "shadow_walker": {
        "title_name": "Shadow Walker",
        "passives": [
            {"name": "Cloak of Shadows", "description": "+30% stealth effectiveness", "effect": {"stealth_bonus": 0.3}},
            {"name": "Silent Steps", "description": "No movement sound", "effect": {"silent_movement": True}}
        ]
    },
    "dragon_slayer": {
        "title_name": "Dragon Slayer",
        "passives": [
            {"name": "Dragon's Bane", "description": "+50% damage to dragons and bosses", "effect": {"boss_damage_bonus": 0.5}},
            {"name": "Fearless", "description": "Immune to fear effects", "effect": {"fear_immunity": True}}
        ]
    },
    "transcendent": {
        "title_name": "Transcendent",
        "passives": [
            {"name": "Beyond Mortality", "description": "+50% all stats, +100% XP", "effect": {"all_stats_bonus": 0.5, "xp_bonus": 1.0}},
            {"name": "Reality Bender", "description": "Access to transcendent abilities", "effect": {"transcendent_skills": True}},
            {"name": "Immortal Legacy", "description": "Death penalties reduced by 90%", "effect": {"death_penalty_reduction": 0.9}}
        ]
    }
}


# ============ Models ============

class UnlockSkillRequest(BaseModel):
    skill_tree: str
    skill_id: str

class UseActiveSkillRequest(BaseModel):
    skill_tree: str
    skill_id: str
    target_id: Optional[str] = None


# ============ Endpoints ============

@skill_tree_router.get("/trees")
async def get_skill_trees():
    """Get all skill trees with their skills"""
    return {
        "skill_trees": SKILL_TREES,
        "total_trees": len(SKILL_TREES),
        "total_skills": sum(
            sum(len(tier) for tier in tree["tiers"].values())
            for tree in SKILL_TREES.values()
        )
    }


@skill_tree_router.get("/trees/{tree_id}")
async def get_skill_tree(tree_id: str):
    """Get a specific skill tree"""
    if tree_id not in SKILL_TREES:
        raise HTTPException(status_code=404, detail="Skill tree not found")
    
    return SKILL_TREES[tree_id]


@skill_tree_router.get("/player/{player_id}")
async def get_player_skills(player_id: str):
    """Get player's unlocked skills and progress"""
    db = get_skill_db()
    
    # Get player skill data
    skill_data = await db.player_skill_trees.find_one(
        {"player_id": player_id},
        {"_id": 0}
    )
    
    if not skill_data:
        # Initialize with empty skills
        skill_data = {
            "player_id": player_id,
            "skill_points": 5,
            "total_points_earned": 5,
            "unlocked_skills": {},  # tree_id -> [skill_ids]
            "skill_cooldowns": {},  # skill_id -> cooldown_ends_at
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.player_skill_trees.insert_one(skill_data.copy())
    
    # Get player's titles for passives
    player = await db.user_profiles.find_one({"id": player_id}, {"_id": 0})
    player_titles = player.get("titles", []) if player else []
    
    # Collect title passives
    active_passives = []
    for title_id in player_titles:
        if title_id in TITLE_PASSIVES:
            active_passives.extend(TITLE_PASSIVES[title_id]["passives"])
    
    return {
        **skill_data,
        "title_passives": active_passives,
        "skill_trees": SKILL_TREES
    }


@skill_tree_router.post("/unlock")
async def unlock_skill(request: UnlockSkillRequest, player_id: str = Query(...)):
    """Unlock a skill in a skill tree"""
    db = get_skill_db()
    
    if request.skill_tree not in SKILL_TREES:
        raise HTTPException(status_code=404, detail="Skill tree not found")
    
    tree = SKILL_TREES[request.skill_tree]
    
    # Find the skill
    skill = None
    skill_tier = None
    for tier_num, tier_skills in tree["tiers"].items():
        if request.skill_id in tier_skills:
            skill = tier_skills[request.skill_id]
            skill_tier = int(tier_num)
            break
    
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    # Get player data
    skill_data = await db.player_skill_trees.find_one({"player_id": player_id}, {"_id": 0})
    if not skill_data:
        raise HTTPException(status_code=404, detail="Player skill data not found")
    
    # Check if already unlocked
    unlocked = skill_data.get("unlocked_skills", {})
    if request.skill_id in unlocked.get(request.skill_tree, []):
        raise HTTPException(status_code=400, detail="Skill already unlocked")
    
    # Check skill points
    if skill_data.get("skill_points", 0) < 1:
        raise HTTPException(status_code=400, detail="Not enough skill points")
    
    # Check requirements
    requires = skill.get("requires", [])
    for req in requires:
        if req not in unlocked.get(request.skill_tree, []):
            raise HTTPException(status_code=400, detail=f"Requires skill: {req}")
    
    # Check skill level requirement
    player_skills = await db.entity_skills.find_one({"entity_id": player_id}, {"_id": 0})
    base_skill_name = {
        "combat": "melee_combat",
        "magic": "arcana",
        "crafting": "engineering",
        "social": "charm",
        "survival": "survival"
    }.get(request.skill_tree, "melee_combat")
    
    skill_level = player_skills.get("skills", {}).get(base_skill_name, {}).get("level", 1) if player_skills else 1
    
    if skill_level < skill.get("unlocks_at_skill_level", 1):
        raise HTTPException(
            status_code=400, 
            detail=f"Requires {base_skill_name} level {skill.get('unlocks_at_skill_level')}"
        )
    
    # Unlock the skill
    if request.skill_tree not in unlocked:
        unlocked[request.skill_tree] = []
    unlocked[request.skill_tree].append(request.skill_id)
    
    await db.player_skill_trees.update_one(
        {"player_id": player_id},
        {
            "$set": {"unlocked_skills": unlocked},
            "$inc": {"skill_points": -1}
        }
    )
    
    return {
        "unlocked": True,
        "skill_id": request.skill_id,
        "skill_name": skill["name"],
        "remaining_points": skill_data["skill_points"] - 1
    }


@skill_tree_router.post("/use")
async def use_active_skill(request: UseActiveSkillRequest, player_id: str = Query(...)):
    """Use an active skill"""
    db = get_skill_db()
    
    if request.skill_tree not in SKILL_TREES:
        raise HTTPException(status_code=404, detail="Skill tree not found")
    
    tree = SKILL_TREES[request.skill_tree]
    
    # Find the skill
    skill = None
    for tier_skills in tree["tiers"].values():
        if request.skill_id in tier_skills:
            skill = tier_skills[request.skill_id]
            break
    
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    if skill["type"] != "active":
        raise HTTPException(status_code=400, detail="Not an active skill")
    
    # Check if unlocked
    skill_data = await db.player_skill_trees.find_one({"player_id": player_id}, {"_id": 0})
    if not skill_data:
        raise HTTPException(status_code=404, detail="Player skill data not found")
    
    unlocked = skill_data.get("unlocked_skills", {})
    if request.skill_id not in unlocked.get(request.skill_tree, []):
        raise HTTPException(status_code=400, detail="Skill not unlocked")
    
    # Check cooldown
    cooldowns = skill_data.get("skill_cooldowns", {})
    if request.skill_id in cooldowns:
        cooldown_end = datetime.fromisoformat(cooldowns[request.skill_id])
        if datetime.now(timezone.utc) < cooldown_end:
            remaining = (cooldown_end - datetime.now(timezone.utc)).total_seconds()
            raise HTTPException(status_code=400, detail=f"Skill on cooldown ({int(remaining)}s remaining)")
    
    # Set new cooldown
    cooldown_seconds = skill.get("cooldown_seconds", 0)
    if cooldown_seconds > 0:
        cooldown_end = datetime.now(timezone.utc) + __import__('datetime').timedelta(seconds=cooldown_seconds)
        cooldowns[request.skill_id] = cooldown_end.isoformat()
        
        await db.player_skill_trees.update_one(
            {"player_id": player_id},
            {"$set": {"skill_cooldowns": cooldowns}}
        )
    
    return {
        "used": True,
        "skill_id": request.skill_id,
        "skill_name": skill["name"],
        "effects": skill.get("effects", {}),
        "cooldown_seconds": cooldown_seconds,
        "target_id": request.target_id
    }


@skill_tree_router.get("/title-passives")
async def get_all_title_passives():
    """Get all title passive skills"""
    return {
        "title_passives": TITLE_PASSIVES,
        "total_titles": len(TITLE_PASSIVES)
    }


@skill_tree_router.get("/title-passives/{title_id}")
async def get_title_passives(title_id: str):
    """Get passives for a specific title"""
    if title_id not in TITLE_PASSIVES:
        raise HTTPException(status_code=404, detail="Title not found")
    
    return TITLE_PASSIVES[title_id]


@skill_tree_router.post("/award-points")
async def award_skill_points(player_id: str = Query(...), points: int = Query(..., ge=1, le=10)):
    """Award skill points to a player (admin/system use)"""
    db = get_skill_db()
    
    result = await db.player_skill_trees.update_one(
        {"player_id": player_id},
        {
            "$inc": {"skill_points": points, "total_points_earned": points}
        },
        upsert=True
    )
    
    return {"awarded": points, "player_id": player_id}


@skill_tree_router.get("/active-effects/{player_id}")
async def get_active_effects(player_id: str):
    """Get all active passive effects for a player"""
    db = get_skill_db()
    
    # Get unlocked skills
    skill_data = await db.player_skill_trees.find_one({"player_id": player_id}, {"_id": 0})
    unlocked = skill_data.get("unlocked_skills", {}) if skill_data else {}
    
    # Get player titles
    player = await db.user_profiles.find_one({"id": player_id}, {"_id": 0})
    player_titles = player.get("titles", []) if player else []
    
    # Collect all passive effects
    passive_effects = []
    
    # From skill trees
    for tree_id, skill_ids in unlocked.items():
        if tree_id in SKILL_TREES:
            tree = SKILL_TREES[tree_id]
            for tier_skills in tree["tiers"].values():
                for skill_id, skill in tier_skills.items():
                    if skill_id in skill_ids and skill["type"] == "passive":
                        passive_effects.append({
                            "source": f"skill:{tree_id}:{skill_id}",
                            "name": skill["name"],
                            "effects": skill.get("effects", {})
                        })
    
    # From titles
    for title_id in player_titles:
        if title_id in TITLE_PASSIVES:
            for passive in TITLE_PASSIVES[title_id]["passives"]:
                passive_effects.append({
                    "source": f"title:{title_id}",
                    "name": passive["name"],
                    "effects": passive.get("effect", {})
                })
    
    # Calculate combined bonuses
    combined = {}
    for effect in passive_effects:
        for key, value in effect.get("effects", {}).items():
            if isinstance(value, (int, float)):
                combined[key] = combined.get(key, 0) + value
            else:
                combined[key] = value
    
    return {
        "passive_effects": passive_effects,
        "combined_bonuses": combined,
        "total_passives": len(passive_effects)
    }
