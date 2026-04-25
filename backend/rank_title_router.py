# Adventurer Rank & Title System
# AI-driven title assignment based on player achievements
# Rebirth system for star ranks

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone
import uuid
import logging
import random

rank_title_router = APIRouter(prefix="/ranks", tags=["ranks-titles"])

logger = logging.getLogger(__name__)

# ============ ADVENTURER RANKS ============
# F -> E -> D -> C -> B -> A -> S -> SS -> SSS -> ★1 -> ★2 -> ★∞

ADVENTURER_RANKS = {
    "F": {"name": "F Rank", "order": 0, "color": "#6B7280", "min_exp": 0, "title": "Novice"},
    "E": {"name": "E Rank", "order": 1, "color": "#9CA3AF", "min_exp": 100, "title": "Apprentice"},
    "D": {"name": "D Rank", "order": 2, "color": "#22C55E", "min_exp": 500, "title": "Journeyman"},
    "C": {"name": "C Rank", "order": 3, "color": "#3B82F6", "min_exp": 2000, "title": "Adventurer"},
    "B": {"name": "B Rank", "order": 4, "color": "#8B5CF6", "min_exp": 5000, "title": "Veteran"},
    "A": {"name": "A Rank", "order": 5, "color": "#F59E0B", "min_exp": 15000, "title": "Elite"},
    "S": {"name": "S Rank", "order": 6, "color": "#EF4444", "min_exp": 50000, "title": "Champion"},
    "SS": {"name": "SS Rank", "order": 7, "color": "#EC4899", "min_exp": 150000, "title": "Hero"},
    "SSS": {"name": "SSS Rank", "order": 8, "color": "#D946EF", "min_exp": 500000, "title": "Legend"},
    "STAR": {"name": "★ Rank", "order": 9, "color": "#FFD700", "min_exp": 1000000, "title": "Transcendent", "requires_rebirth": True}
}

# Star ranks have levels: ★1, ★2, ★3, etc.
# Each star level requires rebirth (achievement-based, not death)

# ============ TITLE CATEGORIES & BUFFS ============
# Max buff per title: 1000% (10x multiplier)

TITLE_CATEGORIES = {
    "combat": {
        "name": "Combat Titles",
        "icon": "sword",
        "titles": {
            "monster_slayer": {
                "name": "Monster Slayer",
                "description": "Defeated 100 monsters",
                "requirement": {"monsters_killed": 100},
                "buffs": {"attack": 0.10, "critical_rate": 0.05},
                "rarity": "common"
            },
            "dragon_hunter": {
                "name": "Dragon Hunter",
                "description": "Defeated a dragon",
                "requirement": {"dragons_killed": 1},
                "buffs": {"attack": 0.25, "fire_resistance": 0.20},
                "rarity": "rare"
            },
            "berserker": {
                "name": "Berserker",
                "description": "Won 50 battles with less than 10% HP",
                "requirement": {"low_hp_victories": 50},
                "buffs": {"attack": 0.50, "defense": -0.10},
                "rarity": "epic"
            },
            "godslayer": {
                "name": "Godslayer",
                "description": "Defeated a divine being",
                "requirement": {"gods_defeated": 1},
                "buffs": {"all_stats": 1.00},  # 100% = 2x
                "rarity": "legendary"
            },
            "one_man_army": {
                "name": "One Man Army",
                "description": "Solo defeated 1000 enemies in a single session",
                "requirement": {"solo_kill_streak": 1000},
                "buffs": {"attack": 2.00, "defense": 1.50, "speed": 1.00},
                "rarity": "mythic"
            },
            "war_god": {
                "name": "War God",
                "description": "Achieved ★5 rank through combat achievements",
                "requirement": {"star_rank": 5, "primary_path": "combat"},
                "buffs": {"attack": 5.00, "critical_damage": 3.00},  # 500%, 300%
                "rarity": "transcendent"
            },
            "extinction_class": {
                "name": "Extinction Class",
                "description": "Single-handedly ended a war",
                "requirement": {"wars_ended_solo": 1},
                "buffs": {"all_stats": 10.00},  # Max 1000%
                "rarity": "unique"
            }
        }
    },
    "exploration": {
        "name": "Exploration Titles",
        "icon": "compass",
        "titles": {
            "wanderer": {
                "name": "Wanderer",
                "description": "Visited 10 different regions",
                "requirement": {"regions_visited": 10},
                "buffs": {"movement_speed": 0.10, "stamina_regen": 0.05},
                "rarity": "common"
            },
            "cartographer": {
                "name": "Cartographer",
                "description": "Mapped 50 areas",
                "requirement": {"areas_mapped": 50},
                "buffs": {"map_reveal": 0.50, "exp_gain": 0.10},
                "rarity": "rare"
            },
            "world_traveler": {
                "name": "World Traveler",
                "description": "Visited all regions",
                "requirement": {"all_regions": True},
                "buffs": {"movement_speed": 0.30, "encounter_rate": -0.20},
                "rarity": "epic"
            },
            "dimension_walker": {
                "name": "Dimension Walker",
                "description": "Traveled between dimensions",
                "requirement": {"dimensions_visited": 3},
                "buffs": {"teleport_cooldown": -0.50, "mana_regen": 0.30},
                "rarity": "legendary"
            },
            "cosmic_voyager": {
                "name": "Cosmic Voyager",
                "description": "Explored beyond the known universe",
                "requirement": {"cosmic_exploration": True},
                "buffs": {"all_stats": 2.00, "void_resistance": 5.00},
                "rarity": "mythic"
            }
        }
    },
    "wealth": {
        "name": "Wealth Titles",
        "icon": "coins",
        "titles": {
            "merchant": {
                "name": "Merchant",
                "description": "Completed 100 trades",
                "requirement": {"trades_completed": 100},
                "buffs": {"sell_price": 0.10, "buy_discount": 0.05},
                "rarity": "common"
            },
            "tycoon": {
                "name": "Tycoon",
                "description": "Accumulated 100,000 VE$",
                "requirement": {"total_earned": 100000},
                "buffs": {"income": 0.25, "investment_returns": 0.20},
                "rarity": "rare"
            },
            "mogul": {
                "name": "Mogul",
                "description": "Own 10 properties",
                "requirement": {"properties_owned": 10},
                "buffs": {"passive_income": 0.50, "property_value": 0.30},
                "rarity": "epic"
            },
            "economic_emperor": {
                "name": "Economic Emperor",
                "description": "Control 50% of regional trade",
                "requirement": {"trade_market_share": 0.50},
                "buffs": {"all_economic": 1.00, "influence": 0.50},
                "rarity": "legendary"
            },
            "infinite_wealth": {
                "name": "Infinite Wealth",
                "description": "Accumulated 10,000,000 VE$",
                "requirement": {"total_earned": 10000000},
                "buffs": {"income": 5.00, "all_stats": 1.00},
                "rarity": "mythic"
            }
        }
    },
    "social": {
        "name": "Social Titles",
        "icon": "users",
        "titles": {
            "friend_maker": {
                "name": "Friend Maker",
                "description": "Made 10 NPC friends",
                "requirement": {"npc_friends": 10},
                "buffs": {"reputation_gain": 0.15, "charisma": 0.10},
                "rarity": "common"
            },
            "diplomat": {
                "name": "Diplomat",
                "description": "Resolved 20 conflicts peacefully",
                "requirement": {"peaceful_resolutions": 20},
                "buffs": {"negotiation": 0.30, "faction_standing": 0.20},
                "rarity": "rare"
            },
            "beloved": {
                "name": "Beloved",
                "description": "Max reputation with 5 factions",
                "requirement": {"max_rep_factions": 5},
                "buffs": {"reputation_gain": 0.50, "quest_rewards": 0.25},
                "rarity": "epic"
            },
            "world_leader": {
                "name": "World Leader",
                "description": "Led a faction to victory",
                "requirement": {"faction_victories_as_leader": 1},
                "buffs": {"leadership": 1.00, "follower_stats": 0.50},
                "rarity": "legendary"
            },
            "universal_friend": {
                "name": "Universal Friend",
                "description": "Befriended every faction",
                "requirement": {"all_factions_friendly": True},
                "buffs": {"all_social": 2.00, "peace_aura": True},
                "rarity": "mythic"
            }
        }
    },
    "crafting": {
        "name": "Crafting Titles",
        "icon": "hammer",
        "titles": {
            "apprentice_crafter": {
                "name": "Apprentice Crafter",
                "description": "Crafted 50 items",
                "requirement": {"items_crafted": 50},
                "buffs": {"craft_speed": 0.10, "material_efficiency": 0.05},
                "rarity": "common"
            },
            "master_artisan": {
                "name": "Master Artisan",
                "description": "Crafted a masterwork item",
                "requirement": {"masterwork_created": 1},
                "buffs": {"craft_quality": 0.30, "rare_material_find": 0.20},
                "rarity": "rare"
            },
            "legendary_smith": {
                "name": "Legendary Smith",
                "description": "Forged a legendary weapon",
                "requirement": {"legendary_weapons_forged": 1},
                "buffs": {"weapon_craft": 1.00, "enchant_success": 0.50},
                "rarity": "epic"
            },
            "divine_artificer": {
                "name": "Divine Artificer",
                "description": "Created a divine artifact",
                "requirement": {"divine_artifacts_created": 1},
                "buffs": {"all_crafting": 2.00, "creation_mastery": 1.00},
                "rarity": "legendary"
            },
            "creator_god": {
                "name": "Creator God",
                "description": "Crafted an item that changed the world",
                "requirement": {"world_changing_creations": 1},
                "buffs": {"all_crafting": 5.00, "inspiration": 3.00},
                "rarity": "mythic"
            }
        }
    },
    "special": {
        "name": "Special Titles",
        "icon": "star",
        "titles": {
            "early_adopter": {
                "name": "Early Adopter",
                "description": "Joined during Early Access",
                "requirement": {"early_access": True},
                "buffs": {"exp_gain": 0.10, "special_access": True},
                "rarity": "limited"
            },
            "rebirth_initiate": {
                "name": "Rebirth Initiate",
                "description": "Completed first rebirth",
                "requirement": {"rebirths": 1},
                "buffs": {"all_stats": 0.50, "rebirth_bonus": 0.10},
                "rarity": "rare"
            },
            "phoenix": {
                "name": "Phoenix",
                "description": "Completed 10 rebirths",
                "requirement": {"rebirths": 10},
                "buffs": {"all_stats": 2.00, "rebirth_bonus": 0.50},
                "rarity": "legendary"
            },
            "eternal": {
                "name": "Eternal",
                "description": "Reached ★10 rank",
                "requirement": {"star_rank": 10},
                "buffs": {"all_stats": 5.00, "immortality": True},
                "rarity": "mythic"
            },
            "beyond_limits": {
                "name": "Beyond Limits",
                "description": "Exceeded theoretical maximum stats",
                "requirement": {"stats_beyond_cap": True},
                "buffs": {"all_stats": 10.00},  # Max 1000%
                "rarity": "unique"
            }
        }
    }
}

RARITY_COLORS = {
    "common": "#9CA3AF",
    "rare": "#3B82F6",
    "epic": "#8B5CF6",
    "legendary": "#F59E0B",
    "mythic": "#EF4444",
    "transcendent": "#EC4899",
    "unique": "#FFD700",
    "limited": "#22C55E"
}

# ============ MODELS ============

class RankProgress(BaseModel):
    user_id: str
    experience_gained: int

class RebirthRequest(BaseModel):
    user_id: str
    achievement_proof: Optional[Dict[str, Any]] = None

class TitleClaim(BaseModel):
    user_id: str
    title_category: str
    title_id: str

# MongoDB reference
def get_db():
    from server import db
    return db

# ============ HELPER FUNCTIONS ============

def calculate_rank(experience: int, rebirths: int = 0) -> Dict[str, Any]:
    """Calculate adventurer rank based on experience and rebirths"""
    if rebirths > 0:
        # Star ranks
        star_level = rebirths
        return {
            "rank": "STAR",
            "star_level": star_level,
            "display": f"★{star_level}",
            "name": f"★{star_level} Rank",
            "color": "#FFD700",
            "title": "Transcendent" if star_level < 5 else "Ascendant" if star_level < 10 else "Eternal"
        }
    
    # Normal ranks
    current_rank = "F"
    for rank_key, rank_data in ADVENTURER_RANKS.items():
        if rank_key == "STAR":
            continue
        if experience >= rank_data["min_exp"]:
            current_rank = rank_key
    
    rank_data = ADVENTURER_RANKS[current_rank]
    return {
        "rank": current_rank,
        "star_level": 0,
        "display": current_rank,
        "name": rank_data["name"],
        "color": rank_data["color"],
        "title": rank_data["title"]
    }

def calculate_total_buffs(titles: List[Dict]) -> Dict[str, float]:
    """Calculate combined buffs from all titles, capped at 1000% (10.0)"""
    total_buffs = {}
    
    for title in titles:
        buffs = title.get("buffs", {})
        for buff_name, buff_value in buffs.items():
            if buff_name not in total_buffs:
                total_buffs[buff_name] = 0.0
            total_buffs[buff_name] += buff_value
    
    # Cap all buffs at 1000% (10.0)
    for buff_name in total_buffs:
        if isinstance(total_buffs[buff_name], (int, float)):
            total_buffs[buff_name] = min(total_buffs[buff_name], 10.0)
    
    return total_buffs

async def check_title_eligibility(user_id: str, category: str, title_id: str, db) -> bool:
    """Check if a user meets the requirements for a title"""
    if category not in TITLE_CATEGORIES:
        return False
    
    if title_id not in TITLE_CATEGORIES[category]["titles"]:
        return False
    
    title = TITLE_CATEGORIES[category]["titles"][title_id]
    requirements = title.get("requirement", {})
    
    # Get player stats
    player_stats = await db.player_achievement_stats.find_one({"user_id": user_id}) or {}
    
    for req_key, req_value in requirements.items():
        player_value = player_stats.get(req_key, 0)
        
        if isinstance(req_value, bool):
            if player_value != req_value:
                return False
        elif isinstance(req_value, (int, float)):
            if player_value < req_value:
                return False
    
    return True

# ============ ENDPOINTS ============

@rank_title_router.get("/ranks")
async def get_all_ranks():
    """Get all adventurer ranks"""
    return {
        "ranks": ADVENTURER_RANKS,
        "progression": ["F", "E", "D", "C", "B", "A", "S", "SS", "SSS", "★"],
        "note": "Star ranks (★) require rebirth and can go infinitely (★1, ★2, ★3, ...)"
    }

@rank_title_router.get("/titles")
async def get_all_titles():
    """Get all available titles"""
    return {
        "categories": TITLE_CATEGORIES,
        "rarity_colors": RARITY_COLORS,
        "max_buff": "1000% (10x multiplier)"
    }

@rank_title_router.get("/player/{user_id}")
async def get_player_rank_data(user_id: str):
    """Get player's rank, titles, and buffs"""
    db = get_db()
    
    # Get player rank data
    rank_data = await db.player_ranks.find_one({"user_id": user_id})
    
    if not rank_data:
        # Initialize new player
        rank_data = {
            "user_id": user_id,
            "experience": 0,
            "rebirths": 0,
            "titles_earned": [],
            "active_title": None,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.player_ranks.insert_one(rank_data)
    
    rank_data.pop("_id", None)
    
    # Calculate current rank
    current_rank = calculate_rank(rank_data.get("experience", 0), rank_data.get("rebirths", 0))
    
    # Get titles with full data
    titles_earned = []
    for title_ref in rank_data.get("titles_earned", []):
        cat = title_ref.get("category")
        tid = title_ref.get("title_id")
        if cat in TITLE_CATEGORIES and tid in TITLE_CATEGORIES[cat]["titles"]:
            title_data = TITLE_CATEGORIES[cat]["titles"][tid]
            titles_earned.append({
                **title_ref,
                **title_data,
                "category_name": TITLE_CATEGORIES[cat]["name"],
                "rarity_color": RARITY_COLORS.get(title_data.get("rarity", "common"))
            })
    
    # Calculate total buffs
    total_buffs = calculate_total_buffs(titles_earned)
    
    return {
        "user_id": user_id,
        "rank": current_rank,
        "experience": rank_data.get("experience", 0),
        "rebirths": rank_data.get("rebirths", 0),
        "titles_earned": titles_earned,
        "titles_count": len(titles_earned),
        "active_title": rank_data.get("active_title"),
        "total_buffs": total_buffs,
        "next_rank": get_next_rank_requirements(rank_data.get("experience", 0), rank_data.get("rebirths", 0))
    }

def get_next_rank_requirements(exp: int, rebirths: int) -> Optional[Dict]:
    """Get requirements for next rank"""
    if rebirths > 0:
        return {
            "next_rank": f"★{rebirths + 1}",
            "requirement": "Complete another rebirth through achievement"
        }
    
    for rank_key, rank_data in ADVENTURER_RANKS.items():
        if rank_key == "STAR":
            continue
        if rank_data["min_exp"] > exp:
            return {
                "next_rank": rank_key,
                "exp_required": rank_data["min_exp"],
                "exp_needed": rank_data["min_exp"] - exp
            }
    
    # At SSS, next is rebirth
    return {
        "next_rank": "★1",
        "requirement": "Achieve rebirth through major accomplishment"
    }

@rank_title_router.post("/experience/add")
async def add_experience(data: RankProgress):
    """Add experience to player rank"""
    db = get_db()
    
    await db.player_ranks.update_one(
        {"user_id": data.user_id},
        {
            "$inc": {"experience": data.experience_gained},
            "$set": {"last_exp_gain": datetime.now(timezone.utc).isoformat()}
        },
        upsert=True
    )
    
    # Get updated data
    rank_data = await db.player_ranks.find_one({"user_id": data.user_id})
    new_exp = rank_data.get("experience", 0)
    rebirths = rank_data.get("rebirths", 0)
    
    current_rank = calculate_rank(new_exp, rebirths)
    
    return {
        "experience_added": data.experience_gained,
        "total_experience": new_exp,
        "current_rank": current_rank
    }

@rank_title_router.post("/rebirth")
async def perform_rebirth(data: RebirthRequest):
    """Perform rebirth - ascend to star ranks through achievement"""
    db = get_db()
    
    rank_data = await db.player_ranks.find_one({"user_id": data.user_id})
    if not rank_data:
        raise HTTPException(status_code=404, detail="Player not found")
    
    current_exp = rank_data.get("experience", 0)
    current_rebirths = rank_data.get("rebirths", 0)
    
    # Check if eligible for rebirth
    if current_rebirths == 0:
        # First rebirth requires SSS rank (1,000,000 exp)
        if current_exp < 1000000:
            raise HTTPException(
                status_code=400,
                detail="Must reach SSS rank (1,000,000 exp) for first rebirth"
            )
    else:
        # Subsequent rebirths require achievements
        achievement_stats = await db.player_achievement_stats.find_one({"user_id": data.user_id}) or {}
        required_achievements = current_rebirths * 5  # More achievements needed each time
        
        total_achievements = sum(1 for v in achievement_stats.values() if isinstance(v, bool) and v)
        total_achievements += sum(1 for v in achievement_stats.values() if isinstance(v, int) and v >= 100)
        
        if total_achievements < required_achievements:
            raise HTTPException(
                status_code=400,
                detail=f"Need {required_achievements} major achievements for rebirth. Have: {total_achievements}"
            )
    
    # Perform rebirth
    new_rebirths = current_rebirths + 1
    
    await db.player_ranks.update_one(
        {"user_id": data.user_id},
        {
            "$set": {
                "rebirths": new_rebirths,
                "experience": 0,  # Reset exp but keep titles
                "last_rebirth": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Award rebirth title
    rebirth_title = {
        "category": "special",
        "title_id": "rebirth_initiate" if new_rebirths == 1 else "phoenix" if new_rebirths >= 10 else None,
        "earned_at": datetime.now(timezone.utc).isoformat()
    }
    
    if rebirth_title["title_id"]:
        await db.player_ranks.update_one(
            {"user_id": data.user_id},
            {"$addToSet": {"titles_earned": rebirth_title}}
        )
    
    new_rank = calculate_rank(0, new_rebirths)
    
    return {
        "success": True,
        "rebirths": new_rebirths,
        "new_rank": new_rank,
        "message": f"Reborn as ★{new_rebirths}! Your journey begins anew with greater power."
    }

@rank_title_router.post("/title/claim")
async def claim_title(data: TitleClaim):
    """Claim a title if requirements are met"""
    db = get_db()
    
    # Check eligibility
    eligible = await check_title_eligibility(data.user_id, data.title_category, data.title_id, db)
    
    if not eligible:
        raise HTTPException(status_code=400, detail="Requirements not met for this title")
    
    # Check if already earned
    rank_data = await db.player_ranks.find_one({"user_id": data.user_id})
    existing_titles = rank_data.get("titles_earned", []) if rank_data else []
    
    already_has = any(
        t.get("category") == data.title_category and t.get("title_id") == data.title_id
        for t in existing_titles
    )
    
    if already_has:
        raise HTTPException(status_code=400, detail="Title already earned")
    
    # Award title
    title_entry = {
        "category": data.title_category,
        "title_id": data.title_id,
        "earned_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.player_ranks.update_one(
        {"user_id": data.user_id},
        {"$push": {"titles_earned": title_entry}},
        upsert=True
    )
    
    title_data = TITLE_CATEGORIES[data.title_category]["titles"][data.title_id]
    
    return {
        "success": True,
        "title_earned": {
            **title_entry,
            **title_data,
            "rarity_color": RARITY_COLORS.get(title_data.get("rarity", "common"))
        }
    }

@rank_title_router.put("/title/active")
async def set_active_title(user_id: str, category: str, title_id: str):
    """Set the active display title"""
    db = get_db()
    
    rank_data = await db.player_ranks.find_one({"user_id": user_id})
    if not rank_data:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Check if player has this title
    has_title = any(
        t.get("category") == category and t.get("title_id") == title_id
        for t in rank_data.get("titles_earned", [])
    )
    
    if not has_title:
        raise HTTPException(status_code=400, detail="You don't have this title")
    
    await db.player_ranks.update_one(
        {"user_id": user_id},
        {"$set": {"active_title": {"category": category, "title_id": title_id}}}
    )
    
    title_data = TITLE_CATEGORIES[category]["titles"][title_id]
    
    return {
        "success": True,
        "active_title": {
            "category": category,
            "title_id": title_id,
            **title_data
        }
    }

@rank_title_router.get("/leaderboard")
async def get_rank_leaderboard(limit: int = 50):
    """Get top ranked players"""
    db = get_db()
    
    # Sort by rebirths first, then experience
    top_players = await db.player_ranks.find(
        {},
        {"_id": 0, "user_id": 1, "experience": 1, "rebirths": 1, "active_title": 1}
    ).sort([("rebirths", -1), ("experience", -1)]).to_list(limit)
    
    leaderboard = []
    for i, player in enumerate(top_players):
        rank = calculate_rank(player.get("experience", 0), player.get("rebirths", 0))
        leaderboard.append({
            "position": i + 1,
            "user_id": player["user_id"],
            "rank": rank,
            "experience": player.get("experience", 0),
            "rebirths": player.get("rebirths", 0),
            "active_title": player.get("active_title")
        })
    
    return {
        "leaderboard": leaderboard,
        "total_players": await db.player_ranks.count_documents({})
    }

@rank_title_router.post("/achievement/record")
async def record_achievement(user_id: str, achievement_type: str, value: Any):
    """Record an achievement stat for title tracking"""
    db = get_db()
    
    await db.player_achievement_stats.update_one(
        {"user_id": user_id},
        {
            "$set": {achievement_type: value, "updated_at": datetime.now(timezone.utc).isoformat()},
        },
        upsert=True
    )
    
    return {"recorded": True, "achievement_type": achievement_type, "value": value}

@rank_title_router.get("/achievements/{user_id}")
async def get_player_achievements(user_id: str):
    """Get all recorded achievements for a player"""
    db = get_db()
    
    achievements = await db.player_achievement_stats.find_one({"user_id": user_id}, {"_id": 0})
    
    return {
        "user_id": user_id,
        "achievements": achievements or {}
    }


# ============ AUTO-AWARD TITLE SYSTEM ============
# Automatically check and award titles based on player achievements

ACHIEVEMENT_TRIGGERS = {
    # Combat achievements
    "monsters_killed": {"category": "combat", "titles": ["monster_slayer"]},
    "dragons_killed": {"category": "combat", "titles": ["dragon_hunter"]},
    "low_hp_victories": {"category": "combat", "titles": ["berserker"]},
    "gods_defeated": {"category": "combat", "titles": ["godslayer"]},
    "solo_kill_streak": {"category": "combat", "titles": ["one_man_army"]},
    "wars_ended_solo": {"category": "combat", "titles": ["extinction_class"]},
    
    # Exploration achievements
    "regions_visited": {"category": "exploration", "titles": ["wanderer", "cartographer"]},
    "dungeons_cleared": {"category": "exploration", "titles": ["dungeon_delver"]},
    "continents_discovered": {"category": "exploration", "titles": ["world_walker"]},
    "secret_areas_found": {"category": "exploration", "titles": ["seeker_of_secrets"]},
    
    # Economy achievements
    "gold_earned": {"category": "economy", "titles": ["gold_digger", "millionaire", "economic_titan"]},
    "trades_completed": {"category": "economy", "titles": ["trader", "merchant_king"]},
    "ve_earned": {"category": "economy", "titles": ["crypto_pioneer"]},
    
    # Social achievements
    "npcs_befriended": {"category": "social", "titles": ["friendly_face", "beloved"]},
    "quests_completed": {"category": "social", "titles": ["quest_master"]},
    "factions_maxed": {"category": "social", "titles": ["diplomat"]},
    "ai_trust_maxed": {"category": "social", "titles": ["soulbound_partner"]},
    
    # Crafting achievements
    "items_crafted": {"category": "crafting", "titles": ["artisan", "master_craftsman"]},
    "legendary_items_crafted": {"category": "crafting", "titles": ["legendary_smith"]},
    "buildings_constructed": {"category": "crafting", "titles": ["architect"]},
    
    # Task achievements
    "tasks_completed": {"category": "economy", "titles": ["task_master"]},
    "perfect_ratings": {"category": "economy", "titles": ["perfectionist"]}
}

@rank_title_router.post("/achievement/trigger")
async def trigger_achievement_check(user_id: str, achievement_type: str, new_value: int):
    """
    Triggered when a player performs an action. Checks if any titles should be awarded.
    This endpoint should be called by other systems when achievements occur.
    """
    db = get_db()
    
    # Record the achievement
    await db.player_achievement_stats.update_one(
        {"user_id": user_id},
        {
            "$set": {achievement_type: new_value, "updated_at": datetime.now(timezone.utc).isoformat()},
        },
        upsert=True
    )
    
    # Check if this achievement type triggers any titles
    if achievement_type not in ACHIEVEMENT_TRIGGERS:
        return {"checked": True, "new_titles": []}
    
    trigger_info = ACHIEVEMENT_TRIGGERS[achievement_type]
    category = trigger_info["category"]
    potential_titles = trigger_info["titles"]
    
    # Get player's current achievements and titles
    achievements = await db.player_achievement_stats.find_one({"user_id": user_id}) or {}
    rank_data = await db.player_ranks.find_one({"user_id": user_id})
    
    if not rank_data:
        # Initialize player rank data
        rank_data = {
            "user_id": user_id,
            "experience": 0,
            "rebirths": 0,
            "titles_earned": [],
            "active_title": None,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.player_ranks.insert_one(rank_data)
        rank_data = await db.player_ranks.find_one({"user_id": user_id})
    
    earned_title_ids = {t.get("title_id") for t in rank_data.get("titles_earned", [])}
    new_titles = []
    
    # Check each potential title
    for title_id in potential_titles:
        if title_id in earned_title_ids:
            continue  # Already has this title
        
        if category not in TITLE_CATEGORIES:
            continue
            
        if title_id not in TITLE_CATEGORIES[category]["titles"]:
            continue
        
        title_data = TITLE_CATEGORIES[category]["titles"][title_id]
        requirements = title_data.get("requirement", {})
        
        # Check if all requirements are met
        requirements_met = True
        for req_key, req_value in requirements.items():
            player_value = achievements.get(req_key, 0)
            if isinstance(req_value, (int, float)):
                if player_value < req_value:
                    requirements_met = False
                    break
            elif player_value != req_value:
                requirements_met = False
                break
        
        if requirements_met:
            # Award the title!
            new_title_entry = {
                "category": category,
                "title_id": title_id,
                "earned_at": datetime.now(timezone.utc).isoformat(),
                "name": title_data["name"],
                "rarity": title_data.get("rarity", "common")
            }
            
            await db.player_ranks.update_one(
                {"user_id": user_id},
                {"$push": {"titles_earned": new_title_entry}}
            )
            
            # Calculate total buff after earning title (capped at 1000%)
            new_titles.append({
                **new_title_entry,
                "buffs": title_data.get("buffs", {}),
                "description": title_data.get("description")
            })
            
            logger.info(f"Player {user_id} earned title: {title_data['name']}")
    
    return {
        "checked": True,
        "achievement_type": achievement_type,
        "new_value": new_value,
        "new_titles": new_titles,
        "total_new_titles": len(new_titles)
    }

@rank_title_router.get("/buffs/{user_id}")
async def get_player_total_buffs(user_id: str):
    """
    Calculate total buffs from all earned titles.
    Buffs are capped at 1000% (10x) per stat.
    """
    db = get_db()
    
    rank_data = await db.player_ranks.find_one({"user_id": user_id})
    if not rank_data:
        return {"user_id": user_id, "buffs": {}, "capped_buffs": {}}
    
    # Aggregate all buffs
    total_buffs = {}
    
    for title_entry in rank_data.get("titles_earned", []):
        category = title_entry.get("category")
        title_id = title_entry.get("title_id")
        
        if category in TITLE_CATEGORIES and title_id in TITLE_CATEGORIES[category]["titles"]:
            title_data = TITLE_CATEGORIES[category]["titles"][title_id]
            for buff_type, buff_value in title_data.get("buffs", {}).items():
                total_buffs[buff_type] = total_buffs.get(buff_type, 0) + buff_value
    
    # Cap buffs at 1000% (10.0)
    MAX_BUFF = 10.0  # 1000%
    capped_buffs = {k: min(v, MAX_BUFF) for k, v in total_buffs.items()}
    
    # Check for any capped values
    capped_stats = [k for k, v in total_buffs.items() if v > MAX_BUFF]
    
    return {
        "user_id": user_id,
        "raw_buffs": total_buffs,
        "capped_buffs": capped_buffs,
        "max_buff_cap": "1000%",
        "stats_at_cap": capped_stats,
        "title_count": len(rank_data.get("titles_earned", []))
    }

@rank_title_router.post("/xp/award")
async def award_experience(user_id: str, xp_amount: int, source: str = "gameplay"):
    """
    Award XP to a player and check for rank-up.
    Called by various game systems when XP should be awarded.
    """
    db = get_db()
    
    rank_data = await db.player_ranks.find_one({"user_id": user_id})
    if not rank_data:
        rank_data = {
            "user_id": user_id,
            "experience": 0,
            "rebirths": 0,
            "titles_earned": [],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.player_ranks.insert_one(rank_data)
    
    old_exp = rank_data.get("experience", 0)
    new_exp = old_exp + xp_amount
    rebirths = rank_data.get("rebirths", 0)
    
    old_rank = calculate_rank(old_exp, rebirths)
    new_rank = calculate_rank(new_exp, rebirths)
    
    await db.player_ranks.update_one(
        {"user_id": user_id},
        {"$set": {"experience": new_exp, "last_xp_source": source, "last_xp_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    ranked_up = old_rank != new_rank
    
    return {
        "user_id": user_id,
        "xp_awarded": xp_amount,
        "source": source,
        "old_experience": old_exp,
        "new_experience": new_exp,
        "old_rank": old_rank,
        "new_rank": new_rank,
        "ranked_up": ranked_up
    }
