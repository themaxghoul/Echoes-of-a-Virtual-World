from fastapi import FastAPI, APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any, Set
import uuid
from datetime import datetime, timezone
from emergentintegrations.llm.chat import LlmChat, UserMessage
import httpx
import asyncio
import json
import bcrypt

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# LLM Setup
llm_key = os.environ.get('EMERGENT_LLM_KEY')

# News cache
news_cache = {
    "headlines": [],
    "last_updated": None,
    "cache_duration": 3600
}

# Active WebSocket connections per location
location_connections: Dict[str, Dict[str, WebSocket]] = {}

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============ Permission Levels & Rankings ============
PERMISSION_LEVELS = {
    "basic": {
        "level": 1,
        "abilities": ["explore", "talk", "trade", "view_quests"],
        "description": "Standard player abilities",
        "chat_access": ["local"]
    },
    "advanced": {
        "level": 2,
        "abilities": ["craft", "teach_ai", "create_quests", "mentor"],
        "description": "Experienced player abilities",
        "chat_access": ["local", "city"]
    },
    "admin": {
        "level": 3,
        "abilities": ["modify_world", "spawn_npcs", "manage_users", "allocate_resources"],
        "description": "Administrator abilities",
        "chat_access": ["local", "city", "state"]
    },
    "sirix_1": {
        "level": 999,
        "abilities": ["all", "immutable", "supreme_override"],
        "description": "Supreme authority - cannot be overwritten",
        "chat_access": ["local", "city", "state", "country", "global"]
    }
}

# Official Rankings (for government/leadership roles)
OFFICIAL_RANKINGS = {
    # City Level Officials
    "citizen": {"tier": "city", "rank": 1, "chat_access": ["local"], "title": "Citizen"},
    "merchant": {"tier": "city", "rank": 2, "chat_access": ["local", "city"], "title": "Merchant"},
    "guild_member": {"tier": "city", "rank": 3, "chat_access": ["local", "city"], "title": "Guild Member"},
    "guild_master": {"tier": "city", "rank": 4, "chat_access": ["local", "city"], "title": "Guild Master"},
    "city_council": {"tier": "city", "rank": 5, "chat_access": ["local", "city"], "title": "City Council"},
    "mayor": {"tier": "city", "rank": 6, "chat_access": ["local", "city", "state"], "title": "Mayor"},
    
    # State Level Officials
    "state_delegate": {"tier": "state", "rank": 7, "chat_access": ["local", "city", "state"], "title": "State Delegate"},
    "state_senator": {"tier": "state", "rank": 8, "chat_access": ["local", "city", "state"], "title": "State Senator"},
    "governor": {"tier": "state", "rank": 9, "chat_access": ["local", "city", "state", "country"], "title": "Governor"},
    
    # Country Level Officials
    "ambassador": {"tier": "country", "rank": 10, "chat_access": ["local", "city", "state", "country"], "title": "Ambassador"},
    "minister": {"tier": "country", "rank": 11, "chat_access": ["local", "city", "state", "country"], "title": "Minister"},
    "high_council": {"tier": "country", "rank": 12, "chat_access": ["local", "city", "state", "country", "global"], "title": "High Council"},
    "sovereign": {"tier": "country", "rank": 13, "chat_access": ["all"], "title": "Sovereign"},
}

# Standing system (reputation-based)
STANDING_LEVELS = [
    {"name": "Outcast", "min_rep": -1000, "max_rep": -100},
    {"name": "Distrusted", "min_rep": -99, "max_rep": -1},
    {"name": "Neutral", "min_rep": 0, "max_rep": 99},
    {"name": "Respected", "min_rep": 100, "max_rep": 499},
    {"name": "Honored", "min_rep": 500, "max_rep": 999},
    {"name": "Revered", "min_rep": 1000, "max_rep": 4999},
    {"name": "Exalted", "min_rep": 5000, "max_rep": 9999},
    {"name": "Legendary", "min_rep": 10000, "max_rep": 999999},
]

# ============ Building Materials ============
MATERIALS = {
    "wood": {
        "name": "Timber",
        "description": "Basic building material from the Shadow Grove",
        "strength": 20,
        "durability": 30,
        "rarity": "common",
        "gather_locations": ["shadow_grove", "wanderers_rest"],
        "color": "#8B4513"
    },
    "stone": {
        "name": "Cobblestone",
        "description": "Sturdy stone quarried from the village foundations",
        "strength": 50,
        "durability": 60,
        "rarity": "common",
        "gather_locations": ["village_square", "watchtower"],
        "color": "#696969"
    },
    "iron": {
        "name": "Forged Iron",
        "description": "Metal refined in the Ember Forge",
        "strength": 75,
        "durability": 50,
        "rarity": "uncommon",
        "gather_locations": ["the_forge"],
        "color": "#434343"
    },
    "crystal": {
        "name": "Echo Crystal",
        "description": "Mystical crystals from the Oracle's Sanctum",
        "strength": 40,
        "durability": 80,
        "rarity": "rare",
        "gather_locations": ["oracle_sanctum", "ancient_library"],
        "color": "#00CED1"
    },
    "obsidian": {
        "name": "Void Obsidian",
        "description": "The strongest material, found in the deepest shadows",
        "strength": 95,
        "durability": 90,
        "rarity": "legendary",
        "gather_locations": ["watchtower"],
        "color": "#1a1a2e"
    }
}

# ============ Day/Night Cycle System ============
# Uses APPROXIMATE location only (city/timezone level, never precise)
DAY_PHASES = {
    "dawn": {"start_hour": 5, "end_hour": 7, "description": "The first light pierces the darkness", "danger_level": 0.2},
    "morning": {"start_hour": 7, "end_hour": 12, "description": "The village stirs to life", "danger_level": 0.1},
    "afternoon": {"start_hour": 12, "end_hour": 17, "description": "The sun hangs high, commerce thrives", "danger_level": 0.1},
    "dusk": {"start_hour": 17, "end_hour": 20, "description": "Shadows lengthen, wise folk head indoors", "danger_level": 0.3},
    "night": {"start_hour": 20, "end_hour": 24, "description": "Darkness reigns, demons stir", "danger_level": 0.7},
    "witching_hour": {"start_hour": 0, "end_hour": 3, "description": "The veil between worlds thins", "danger_level": 1.0},
    "pre_dawn": {"start_hour": 3, "end_hour": 5, "description": "The deepest dark before dawn", "danger_level": 0.5}
}

# Timezone offsets for approximate location (city-level only)
LOCATION_TIMEZONES = {
    "default": 0,  # UTC
    # These are determined by approximate location, never precise coordinates
}

# ============ Biblical Demon System ============
BIBLICAL_DEMONS = {
    # Lesser Demons - Common encounters
    "imp": {
        "name": "Tormenting Imp",
        "rank": "lesser",
        "description": "A small, cackling fiend that delights in petty cruelty",
        "health": 30,
        "damage": 5,
        "abilities": ["scratch", "taunt", "flee"],
        "drops": {"essence": 5, "gold": 2},
        "spawn_phases": ["night", "witching_hour"],
        "weakness": "holy_water",
        "biblical_origin": "Servants of greater demons"
    },
    "shade": {
        "name": "Wandering Shade",
        "rank": "lesser",
        "description": "A shadow given malevolent form, it drains hope",
        "health": 25,
        "damage": 8,
        "abilities": ["life_drain", "fear", "phase"],
        "drops": {"essence": 8, "crystal": 1},
        "spawn_phases": ["night", "witching_hour", "pre_dawn"],
        "weakness": "light",
        "biblical_origin": "Lost souls bound to darkness"
    },
    
    # Standard Demons
    "legion_soldier": {
        "name": "Soldier of Legion",
        "rank": "standard",
        "description": "One of many, speaking with a thousand voices",
        "health": 80,
        "damage": 15,
        "abilities": ["swarm_strike", "possess", "multiply"],
        "drops": {"essence": 20, "gold": 15, "iron": 2},
        "spawn_phases": ["night", "witching_hour"],
        "weakness": "exorcism",
        "biblical_origin": "Mark 5:9 - 'My name is Legion, for we are many'"
    },
    "tempter": {
        "name": "Whispering Tempter",
        "rank": "standard",
        "description": "Offers forbidden knowledge at terrible cost",
        "health": 50,
        "damage": 10,
        "abilities": ["corrupt", "bargain", "illusion", "charm"],
        "drops": {"essence": 25, "crystal": 2},
        "spawn_phases": ["dusk", "night", "witching_hour"],
        "weakness": "truth",
        "biblical_origin": "Genesis 3 - The serpent's legacy"
    },
    
    # Greater Demons
    "asmodeus_spawn": {
        "name": "Spawn of Asmodeus",
        "rank": "greater",
        "description": "A creature of wrath and destruction",
        "health": 200,
        "damage": 35,
        "abilities": ["hellfire", "rage", "summon_lesser"],
        "drops": {"essence": 50, "gold": 40, "obsidian": 3},
        "spawn_phases": ["witching_hour"],
        "weakness": "prayer",
        "biblical_origin": "Book of Tobit - King of Demons"
    },
    "mammon_collector": {
        "name": "Collector of Mammon",
        "rank": "greater",
        "description": "Seeks to corrupt through greed and avarice",
        "health": 150,
        "damage": 20,
        "abilities": ["gold_curse", "debt_bind", "material_decay"],
        "drops": {"gold": 100, "essence": 30},
        "spawn_phases": ["night", "witching_hour"],
        "weakness": "generosity",
        "biblical_origin": "Matthew 6:24 - You cannot serve both God and Mammon"
    },
    "belphegor_sloth": {
        "name": "Herald of Belphegor",
        "rank": "greater",
        "description": "Induces despair and lethargy in all who gaze upon it",
        "health": 180,
        "damage": 15,
        "abilities": ["sleep", "despair_aura", "time_slow", "apathy"],
        "drops": {"essence": 45, "crystal": 5},
        "spawn_phases": ["pre_dawn", "witching_hour"],
        "weakness": "determination",
        "biblical_origin": "Associated with sloth and discoveries"
    },
    
    # Arch Demons - Rare, devastating encounters
    "beelzebub_avatar": {
        "name": "Avatar of Beelzebub",
        "rank": "arch",
        "description": "Lord of Flies, Prince of Demons - a fragment of his terrible power",
        "health": 500,
        "damage": 60,
        "abilities": ["plague_swarm", "corruption_absolute", "summon_legion", "fly_storm"],
        "drops": {"essence": 150, "obsidian": 10, "artifacts": 1},
        "spawn_phases": ["witching_hour"],
        "spawn_chance": 0.05,  # 5% chance during witching hour
        "weakness": "sacred_artifact",
        "biblical_origin": "2 Kings 1:2 - Lord of Ekron"
    },
    "abaddon_destroyer": {
        "name": "Abaddon the Destroyer",
        "rank": "arch",
        "description": "The angel of the abyss, bringing destruction",
        "health": 666,
        "damage": 80,
        "abilities": ["apocalypse_breath", "reality_tear", "summon_locusts", "void_gate"],
        "drops": {"essence": 200, "obsidian": 15, "artifacts": 2},
        "spawn_phases": ["witching_hour"],
        "spawn_chance": 0.02,  # 2% chance
        "weakness": "divine_intervention",
        "biblical_origin": "Revelation 9:11 - King of the bottomless pit"
    }
}

# Infestation levels affect spawn rates
INFESTATION_LEVELS = {
    "clear": {"multiplier": 0.5, "description": "The area feels peaceful"},
    "stirring": {"multiplier": 1.0, "description": "Something dark lurks nearby"},
    "infested": {"multiplier": 2.0, "description": "Demons roam freely here"},
    "overrun": {"multiplier": 3.0, "description": "Hell has claimed this place"},
    "hellmouth": {"multiplier": 5.0, "description": "A portal to the abyss has opened"}
}

# ============ Guild System ============
GUILD_RANKS = {
    "initiate": {"level": 1, "permissions": ["view_guild", "guild_chat"], "title": "Initiate"},
    "member": {"level": 2, "permissions": ["view_guild", "guild_chat", "use_guild_storage"], "title": "Member"},
    "veteran": {"level": 3, "permissions": ["view_guild", "guild_chat", "use_guild_storage", "invite_members"], "title": "Veteran"},
    "officer": {"level": 4, "permissions": ["view_guild", "guild_chat", "use_guild_storage", "invite_members", "kick_members", "manage_storage"], "title": "Officer"},
    "leader": {"level": 5, "permissions": ["all"], "title": "Guild Leader"}
}

GUILD_TYPES = {
    "trade": {"focus": "commerce", "bonuses": {"gold_gain": 1.2, "trade_discount": 0.9}},
    "combat": {"focus": "fighting", "bonuses": {"damage": 1.15, "defense": 1.1}},
    "crafting": {"focus": "creation", "bonuses": {"craft_speed": 1.25, "material_efficiency": 0.85}},
    "exploration": {"focus": "discovery", "bonuses": {"travel_speed": 1.3, "discovery_chance": 1.2}},
    "mystical": {"focus": "magic", "bonuses": {"essence_gain": 1.25, "spell_power": 1.15}}
}

# ============ AI Emotional Memory System ============
AI_MOODS = {
    "joyful": {"modifier": 1.3, "trade_bonus": 0.9, "will_help": True, "dialogue_tone": "warm and welcoming"},
    "content": {"modifier": 1.1, "trade_bonus": 0.95, "will_help": True, "dialogue_tone": "pleasant"},
    "neutral": {"modifier": 1.0, "trade_bonus": 1.0, "will_help": True, "dialogue_tone": "professional"},
    "annoyed": {"modifier": 0.9, "trade_bonus": 1.1, "will_help": True, "dialogue_tone": "curt and impatient"},
    "angry": {"modifier": 0.7, "trade_bonus": 1.3, "will_help": False, "dialogue_tone": "hostile"},
    "furious": {"modifier": 0.5, "trade_bonus": 1.5, "will_help": False, "dialogue_tone": "refusing service"},
    "fearful": {"modifier": 0.8, "trade_bonus": 1.0, "will_help": False, "dialogue_tone": "nervous and evasive"},
    "grieving": {"modifier": 0.6, "trade_bonus": 1.0, "will_help": False, "dialogue_tone": "sorrowful"},
    "inspired": {"modifier": 1.4, "trade_bonus": 0.85, "will_help": True, "dialogue_tone": "enthusiastic"}
}

# Events that affect AI mood
MOOD_EVENTS = {
    "positive_trade": {"mood_change": 5, "description": "Completed a fair trade"},
    "generous_tip": {"mood_change": 15, "description": "Received generosity"},
    "friendly_chat": {"mood_change": 10, "description": "Had a pleasant conversation"},
    "helped_quest": {"mood_change": 20, "description": "Received help with a task"},
    "gift_received": {"mood_change": 25, "description": "Received a gift"},
    "insult": {"mood_change": -20, "description": "Was insulted"},
    "theft_attempt": {"mood_change": -40, "description": "Someone tried to steal"},
    "property_damage": {"mood_change": -50, "description": "Property was damaged"},
    "violence": {"mood_change": -60, "description": "Was attacked or threatened"},
    "betrayal": {"mood_change": -80, "description": "Was betrayed"},
    "witnessed_demon": {"mood_change": -30, "description": "Witnessed demon attack"},
    "saved_from_demon": {"mood_change": 40, "description": "Was saved from demons"}
}

# ============ Combat & Stats System ============
# Player combat stats and stamina system
# Stamina equation: stamina_loss_per_second = (armor_weight * 0.5) * (1 / (strength * 0.75 / endurance))
# Simplified: higher strength + endurance = less stamina drain, heavier armor = more drain

BASE_STATS = {
    "health": 100,
    "max_health": 100,
    "stamina": 100,
    "max_stamina": 100,
    "mana": 50,           # Magic resource for spells
    "max_mana": 50,
    "strength": 10,       # Affects damage and stamina efficiency
    "endurance": 10,      # Affects stamina recovery and drain reduction
    "agility": 10,        # Affects dodge chance and movement speed
    "vitality": 10,       # Affects max health
    "intelligence": 10,   # Affects mana pool and spell power
    "wisdom": 10,         # Affects mana regen and spell efficiency
    "armor_weight": 0,    # Weight of equipped armor
    "damage_bonus": 0,
    "defense_bonus": 0,
    "spell_power": 0
}

# ============ Magic Spells System ============
SPELL_SCHOOLS = {
    "fire": {"color": "#FF4500", "description": "Destructive flames that burn enemies"},
    "ice": {"color": "#00CED1", "description": "Freezing cold that slows and damages"},
    "lightning": {"color": "#FFD700", "description": "Swift electrical attacks"},
    "holy": {"color": "#FFFFFF", "description": "Divine light that heals and purifies"},
    "shadow": {"color": "#4B0082", "description": "Dark magic that drains and corrupts"},
    "earth": {"color": "#8B4513", "description": "Solid defense and crushing force"},
    "arcane": {"color": "#9932CC", "description": "Pure magical energy"}
}

MAGIC_SPELLS = {
    # Fire Spells
    "fireball": {
        "name": "Fireball",
        "school": "fire",
        "tier": 1,
        "mana_cost": 15,
        "damage": 25,
        "effect": "burn",
        "effect_duration": 3,
        "cooldown": 2.0,
        "description": "Hurl a ball of fire at your enemy",
        "unlock_cost": 0  # Starting spell
    },
    "flame_wave": {
        "name": "Flame Wave",
        "school": "fire",
        "tier": 2,
        "mana_cost": 30,
        "damage": 40,
        "effect": "burn",
        "effect_duration": 5,
        "cooldown": 4.0,
        "area_of_effect": True,
        "description": "Release a wave of flames hitting all nearby enemies",
        "unlock_cost": 100
    },
    "inferno": {
        "name": "Inferno",
        "school": "fire",
        "tier": 3,
        "mana_cost": 60,
        "damage": 80,
        "effect": "burn",
        "effect_duration": 8,
        "cooldown": 10.0,
        "area_of_effect": True,
        "description": "Summon a devastating pillar of fire",
        "unlock_cost": 500
    },
    
    # Ice Spells
    "ice_shard": {
        "name": "Ice Shard",
        "school": "ice",
        "tier": 1,
        "mana_cost": 12,
        "damage": 20,
        "effect": "slow",
        "effect_duration": 4,
        "cooldown": 1.5,
        "description": "Launch a sharp shard of ice",
        "unlock_cost": 0
    },
    "frost_nova": {
        "name": "Frost Nova",
        "school": "ice",
        "tier": 2,
        "mana_cost": 35,
        "damage": 30,
        "effect": "freeze",
        "effect_duration": 3,
        "cooldown": 6.0,
        "area_of_effect": True,
        "description": "Freeze all enemies around you",
        "unlock_cost": 150
    },
    "blizzard": {
        "name": "Blizzard",
        "school": "ice",
        "tier": 3,
        "mana_cost": 55,
        "damage": 60,
        "effect": "freeze",
        "effect_duration": 6,
        "cooldown": 12.0,
        "area_of_effect": True,
        "description": "Call down a devastating blizzard",
        "unlock_cost": 600
    },
    
    # Lightning Spells
    "spark": {
        "name": "Spark",
        "school": "lightning",
        "tier": 1,
        "mana_cost": 10,
        "damage": 18,
        "effect": "stun",
        "effect_duration": 1,
        "cooldown": 1.0,
        "description": "A quick jolt of electricity",
        "unlock_cost": 0
    },
    "chain_lightning": {…58686 tokens truncated…d")
    
    installed_apps = user.get("installed_ai_apps", [])
    if app_id in installed_apps:
        installed_apps.remove(app_id)
        await db.user_profiles.update_one(
            {"id": user_id},
            {"$set": {"installed_ai_apps": installed_apps}}
        )
        await db.ai_integrations.update_one(
            {"app_id": app_id},
            {"$inc": {"install_count": -1}}
        )
    
    return {"app_id": app_id, "uninstalled": True}

# ============ Notification System ============
class NotificationCreate(BaseModel):
    user_id: str
    title: str
    message: str
    notification_type: str = "system"  # message, guild, combat, gift, system

@api_router.get("/notifications/{user_id}")
async def get_notifications(user_id: str, limit: int = 50):
    """Get notifications for a user"""
    notifications = await db.notifications.find(
        {"user_id": user_id},
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    
    unread_count = await db.notifications.count_documents({
        "user_id": user_id,
        "read": False
    })
    
    return {
        "notifications": notifications,
        "unread_count": unread_count
    }

@api_router.post("/notifications")
async def create_notification(notification: NotificationCreate):
    """Create a notification for a user"""
    notif_data = {
        "id": str(uuid.uuid4()),
        "user_id": notification.user_id,
        "title": notification.title,
        "message": notification.message,
        "type": notification.notification_type,
        "read": False,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    await db.notifications.insert_one(notif_data)
    return {"notification_id": notif_data["id"], "created": True}

@api_router.put("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str):
    """Mark a notification as read"""
    await db.notifications.update_one(
        {"id": notification_id},
        {"$set": {"read": True}}
    )
    return {"notification_id": notification_id, "read": True}

@api_router.delete("/notifications/{notification_id}")
async def delete_notification(notification_id: str):
    """Delete a notification"""
    await db.notifications.delete_one({"id": notification_id})
    return {"notification_id": notification_id, "deleted": True}

# ============ Location-Based Discovery System ============
class LocationDiscoveryRequest(BaseModel):
    user_id: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    use_simulation: bool = False

@api_router.post("/discovery/check")
async def check_location_discovery(request: LocationDiscoveryRequest):
    """Check if user can discover new areas based on location"""
    user = await db.user_profiles.find_one({"id": request.user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    discovered_locations = user.get("discovered_locations", ["village_square"])
    character = await db.characters.find_one({"user_id": request.user_id})
    
    # All available locations
    all_locations = [
        "village_square", "the_forge", "oracle_sanctum", 
        "ancient_library", "wanderers_rest", "shadow_grove", "watchtower"
    ]
    
    undiscovered = [loc for loc in all_locations if loc not in discovered_locations]
    
    if not undiscovered:
        return {
            "discovered": False,
            "message": "All areas have been discovered!",
            "total_discovered": len(discovered_locations)
        }
    
    # Check if Sirix-1 (has access to all)
    if user.get("is_transcendent") or user.get("permission_level") == "sirix_1":
        return {
            "discovered": False,
            "all_accessible": True,
            "accessible_locations": all_locations,
            "message": "Transcendent being - all areas accessible"
        }
    
    discovery_chance = 0.0
    discovery_method = ""
    
    # Real GPS-based discovery
    if request.latitude is not None and request.longitude is not None:
        # Calculate "exploration factor" based on GPS movement
        last_coords = user.get("last_gps_coords", {"lat": 0, "lng": 0})
        
        if last_coords["lat"] != 0:
            # Calculate rough distance moved (simplified)
            lat_diff = abs(request.latitude - last_coords["lat"])
            lng_diff = abs(request.longitude - last_coords["lng"])
            distance_factor = (lat_diff + lng_diff) * 111000  # Rough meters
            
            # More movement = higher discovery chance
            if distance_factor > 100:  # Moved at least 100m
                discovery_chance = min(0.5, distance_factor / 1000)
                discovery_method = "gps_exploration"
        
        # Update last coordinates
        await db.user_profiles.update_one(
            {"id": request.user_id},
            {"$set": {"last_gps_coords": {"lat": request.latitude, "lng": request.longitude}}}
        )
    
    # Simulated exploration based on in-game distance
    if request.use_simulation or discovery_chance == 0:
        travel_distance = character.get("total_distance_traveled", 0) if character else 0
        conversations = user.get("conversation_count", 0)
        
        # Base chance from exploration
        discovery_chance = min(0.3, (travel_distance / 500) * 0.1 + (conversations / 20) * 0.1)
        discovery_method = "simulated_exploration"
    
    # Roll for discovery
    import random
    if random.random() < discovery_chance and undiscovered:
        new_location = random.choice(undiscovered)
        discovered_locations.append(new_location)
        
        await db.user_profiles.update_one(
            {"id": request.user_id},
            {"$set": {"discovered_locations": discovered_locations}}
        )
        
        # Create notification
        await db.notifications.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": request.user_id,
            "title": "New Area Discovered!",
            "message": f"You have discovered {new_location.replace('_', ' ').title()}!",
            "type": "system",
            "read": False,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return {
            "discovered": True,
            "new_location": new_location,
            "location_name": new_location.replace("_", " ").title(),
            "method": discovery_method,
            "total_discovered": len(discovered_locations)
        }
    
    return {
        "discovered": False,
        "discovery_chance": round(discovery_chance * 100, 1),
        "undiscovered_count": len(undiscovered),
        "method": discovery_method,
        "message": "Keep exploring to discover new areas!"
    }

@api_router.get("/discovery/locations/{user_id}")
async def get_discovered_locations(user_id: str):
    """Get all discovered locations for a user"""
    user = await db.user_profiles.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    all_locations = [
        {"id": "village_square", "name": "Village Square", "theme": "realistic"},
        {"id": "the_forge", "name": "The Ember Forge", "theme": "realistic"},
        {"id": "oracle_sanctum", "name": "Oracle's Sanctum", "theme": "matrix"},
        {"id": "ancient_library", "name": "Ancient Library", "theme": "realistic"},
        {"id": "wanderers_rest", "name": "Wanderer's Rest", "theme": "realistic"},
        {"id": "shadow_grove", "name": "Shadow Grove", "theme": "matrix"},
        {"id": "watchtower", "name": "The Watchtower", "theme": "realistic"},
    ]
    
    discovered = user.get("discovered_locations", ["village_square"])
    is_transcendent = user.get("is_transcendent") or user.get("permission_level") == "sirix_1"
    
    result = []
    for loc in all_locations:
        result.append({
            **loc,
            "discovered": loc["id"] in discovered or is_transcendent,
            "accessible": loc["id"] in discovered or is_transcendent
        })
    
    return {
        "locations": result,
        "discovered_count": len(discovered) if not is_transcendent else len(all_locations),
        "total_count": len(all_locations),
        "all_accessible": is_transcendent
    }

# WebSocket for real-time multiplayer
@app.websocket("/ws/{location_id}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, location_id: str, user_id: str):
    await websocket.accept()
    
    if location_id not in location_connections:
        location_connections[location_id] = {}
    location_connections[location_id][user_id] = websocket
    
    # Notify others
    user = await db.user_profiles.find_one({"id": user_id})
    username = user.get("display_name", "Unknown") if user else "Unknown"
    
    await broadcast_to_location(location_id, {
        "type": "user_joined",
        "data": {"user_id": user_id, "username": username}
    }, exclude_user=user_id)
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data["type"] == "chat":
                content = data.get("content", "").strip()
                
                # Check for /commands
                if content.startswith("/"):
                    parts = content.split()
                    command = parts[0].lower()
                    args = parts[1:] if len(parts) > 1 else []
                    
                    # Process command
                    cmd_info = CHAT_COMMANDS.get(command)
                    if cmd_info:
                        perm_level = PERMISSION_LEVELS.get(user.get("permission_level", "player"), {}).get("level", 1) if user else 1
                        rank_data = OFFICIAL_RANKINGS.get(user.get("official_rank", "citizen"), {}) if user else {}
                        user_rank = rank_data.get("rank", 1)
                        
                        min_level = cmd_info.get("min_level", 0)
                        min_rank = cmd_info.get("min_rank", 0)
                        
                        if perm_level >= min_level or user_rank >= min_rank:
                            # Execute command via API internally
                            from fastapi.testclient import TestClient
                            result = await execute_command(ChatCommandRequest(
                                user_id=user_id,
                                command=command,
                                args=args,
                                location_id=location_id
                            ))
                            
                            # Send result back to user only
                            await websocket.send_json({
                                "type": "command_result",
                                "data": {
                                    "command": command,
                                    "success": result.success,
                                    "message": result.message,
                                    "result": result.data
                                }
                            })
                        else:
                            await websocket.send_json({
                                "type": "command_result",
                                "data": {
                                    "command": command,
                                    "success": False,
                                    "message": "Insufficient permissions"
                                }
                            })
                    else:
                        # Unknown command - show help
                        await websocket.send_json({
                            "type": "command_result",
                            "data": {
                                "command": command,
                                "success": False,
                                "message": f"Unknown command: {command}. Type /help for available commands."
                            }
                        })
                else:
                    # Regular chat message
                    message = {
                        "id": str(uuid.uuid4()),
                        "location_id": location_id,
                        "sender_id": user_id,
                        "sender_name": data.get("sender_name", username),
                        "sender_type": "player",
                        "content": content,
                        "message_type": data.get("message_type", "chat"),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    await db.multiplayer_messages.insert_one(message)
                    await broadcast_to_location(location_id, {"type": "chat", "data": message})
            
            elif data["type"] == "emote":
                await broadcast_to_location(location_id, {
                    "type": "emote",
                    "data": {"user_id": user_id, "username": username, "emote": data["emote"]}
                })
    
    except WebSocketDisconnect:
        if location_id in location_connections and user_id in location_connections[location_id]:
            del location_connections[location_id][user_id]
        await broadcast_to_location(location_id, {
            "type": "user_left",
            "data": {"user_id": user_id, "username": username}
        })

# Include router
app.include_router(api_router)

# Include earnings router
try:
    from earnings_router import earnings_router
    app.include_router(earnings_router, prefix="/api")
    logging.info("Earnings router loaded successfully")
except ImportError as e:
    logging.warning(f"Could not load earnings router: {e}")

# Include NPC gaming router
try:
    from npc_gaming_router import npc_gaming_router
    app.include_router(npc_gaming_router, prefix="/api")
    logging.info("NPC Gaming router loaded successfully")
except ImportError as e:
    logging.warning(f"Could not load NPC gaming router: {e}")

# Include task providers router
try:
    from task_providers_router import task_providers_router
    app.include_router(task_providers_router, prefix="/api")
    logging.info("Task providers router loaded successfully")
except ImportError as e:
    logging.warning(f"Could not load task providers router: {e}")

# Include Stripe payout router
try:
    from stripe_payout_router import stripe_payout_router
    app.include_router(stripe_payout_router, prefix="/api")
    logging.info("Stripe payout router loaded successfully")
except ImportError as e:
    logging.warning(f"Could not load Stripe payout router: {e}")

# Include ecosystem support router
try:
    from ecosystem_support_router import ecosystem_support_router
    app.include_router(ecosystem_support_router, prefix="/api")
    logging.info("Ecosystem support router loaded successfully")
except ImportError as e:
    logging.warning(f"Could not load ecosystem support router: {e}")

# Include World Engine router (Dynamic Events, Bosses, Diplomacy)
try:
    from world_engine_router import world_engine_router
    app.include_router(world_engine_router, prefix="/api")
    logging.info("World Engine router loaded successfully")
except ImportError as e:
    logging.warning(f"Could not load World Engine router: {e}")

# Include AI Chat router (Isolated Chat System)
try:
    from ai_chat_router import ai_chat_router
    app.include_router(ai_chat_router, prefix="/api")
    logging.info("AI Chat router loaded successfully")
except ImportError as e:
    logging.warning(f"Could not load AI Chat router: {e}")

# Include Memory System router (Persistent Memory for Users & AI)
try:
    from memory_router import memory_router
    app.include_router(memory_router, prefix="/api")
    logging.info("Memory System router loaded successfully")
except ImportError as e:
    logging.warning(f"Could not load Memory System router: {e}")

# Include Jobs & Career System router
try:
    from jobs_router import jobs_router
    app.include_router(jobs_router, prefix="/api")
    logging.info("Jobs & Career router loaded successfully")
except ImportError as e:
    logging.warning(f"Could not load Jobs router: {e}")

# Include Unity Offload router (Cross-platform Unity support)
try:
    from unity_router import unity_router
    app.include_router(unity_router, prefix="/api")
    logging.info("Unity Offload router loaded successfully")
except ImportError as e:
    logging.warning(f"Could not load Unity router: {e}")

# Include Conversation History router (Chat Logs & Resume)
try:
    from conversation_history_router import conversation_history_router
    app.include_router(conversation_history_router, prefix="/api")
    logging.info("Conversation History router loaded successfully")
except ImportError as e:
    logging.warning(f"Could not load Conversation History router: {e}")

# Include Skills & Titles router
try:
    from skills_router import skills_router
    app.include_router(skills_router, prefix="/api")
    logging.info("Skills & Titles router loaded successfully")
except ImportError as e:
    logging.warning(f"Could not load Skills router: {e}")

# Include AI Autonomy router (AI-to-AI conversations, free will)
try:
    from ai_autonomy_router import ai_autonomy_router
    app.include_router(ai_autonomy_router, prefix="/api")
    logging.info("AI Autonomy router loaded successfully")
except ImportError as e:
    logging.warning(f"Could not load AI Autonomy router: {e}")

# Include World Instances router (Private worlds, Sirix-1 realm)
try:
    from world_instances_router import world_instances_router
    app.include_router(world_instances_router, prefix="/api")
    logging.info("World Instances router loaded successfully")
except ImportError as e:
    logging.warning(f"Could not load World Instances router: {e}")

# Include Entity Earnings router (VE$ for players AND AI)
try:
    from entity_earnings_router import entity_earnings_router
    app.include_router(entity_earnings_router, prefix="/api")
    logging.info("Entity Earnings router loaded successfully")
except ImportError as e:
    logging.warning(f"Could not load Entity Earnings router: {e}")

# Include Task Marketplace router (Human & Robot task integration)
try:
    from task_marketplace_router import task_marketplace_router
    app.include_router(task_marketplace_router, prefix="/api")
    logging.info("Task Marketplace router loaded successfully")
except ImportError as e:
    logging.warning(f"Could not load Task Marketplace router: {e}")

# Include Building System router (2D grid-based building)
try:
    from building_system_router import building_system_router
    app.include_router(building_system_router, prefix="/api")
    logging.info("Building System router loaded successfully")
except ImportError as e:
    logging.warning(f"Could not load Building System router: {e}")

# Include World Map router (Top-down stylized map)
try:
    from world_map_router import world_map_router
    app.include_router(world_map_router, prefix="/api")
    logging.info("World Map router loaded successfully")
except ImportError as e:
    logging.warning(f"Could not load World Map router: {e}")

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
