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
    "chain_lightning": {
        "name": "Chain Lightning",
        "school": "lightning",
        "tier": 2,
        "mana_cost": 40,
        "damage": 35,
        "effect": "stun",
        "effect_duration": 2,
        "cooldown": 5.0,
        "chain_targets": 3,
        "description": "Lightning that jumps between enemies",
        "unlock_cost": 200
    },
    "thunderstorm": {
        "name": "Thunderstorm",
        "school": "lightning",
        "tier": 3,
        "mana_cost": 70,
        "damage": 90,
        "effect": "stun",
        "effect_duration": 3,
        "cooldown": 15.0,
        "area_of_effect": True,
        "description": "Call down the fury of the storm",
        "unlock_cost": 700
    },
    
    # Holy Spells
    "heal": {
        "name": "Heal",
        "school": "holy",
        "tier": 1,
        "mana_cost": 20,
        "healing": 30,
        "cooldown": 3.0,
        "description": "Restore health to yourself or an ally",
        "unlock_cost": 0
    },
    "divine_shield": {
        "name": "Divine Shield",
        "school": "holy",
        "tier": 2,
        "mana_cost": 35,
        "effect": "shield",
        "shield_amount": 50,
        "effect_duration": 10,
        "cooldown": 15.0,
        "description": "Create a protective barrier of light",
        "unlock_cost": 250
    },
    "smite": {
        "name": "Smite",
        "school": "holy",
        "tier": 2,
        "mana_cost": 30,
        "damage": 45,
        "bonus_vs_demons": 2.0,
        "cooldown": 4.0,
        "description": "Strike with holy light - devastating to demons",
        "unlock_cost": 300
    },
    "resurrection": {
        "name": "Resurrection",
        "school": "holy",
        "tier": 3,
        "mana_cost": 80,
        "healing": 100,
        "cooldown": 60.0,
        "description": "Revive a fallen ally with full health",
        "unlock_cost": 1000
    },
    
    # Shadow Spells
    "shadow_bolt": {
        "name": "Shadow Bolt",
        "school": "shadow",
        "tier": 1,
        "mana_cost": 15,
        "damage": 22,
        "effect": "curse",
        "effect_duration": 5,
        "cooldown": 2.0,
        "description": "Fire a bolt of shadow energy",
        "unlock_cost": 0
    },
    "life_drain": {
        "name": "Life Drain",
        "school": "shadow",
        "tier": 2,
        "mana_cost": 25,
        "damage": 30,
        "life_steal": 0.5,
        "cooldown": 5.0,
        "description": "Drain life from your enemy to heal yourself",
        "unlock_cost": 200
    },
    "void_eruption": {
        "name": "Void Eruption",
        "school": "shadow",
        "tier": 3,
        "mana_cost": 65,
        "damage": 75,
        "effect": "fear",
        "effect_duration": 4,
        "area_of_effect": True,
        "cooldown": 12.0,
        "description": "Unleash the void to damage and terrify enemies",
        "unlock_cost": 800
    },
    
    # Earth Spells  
    "stone_skin": {
        "name": "Stone Skin",
        "school": "earth",
        "tier": 1,
        "mana_cost": 20,
        "effect": "defense_buff",
        "defense_bonus": 20,
        "effect_duration": 30,
        "cooldown": 45.0,
        "description": "Harden your skin like stone",
        "unlock_cost": 0
    },
    "earthquake": {
        "name": "Earthquake",
        "school": "earth",
        "tier": 2,
        "mana_cost": 45,
        "damage": 50,
        "effect": "knockdown",
        "effect_duration": 2,
        "area_of_effect": True,
        "cooldown": 10.0,
        "description": "Shake the ground to damage and topple enemies",
        "unlock_cost": 300
    },
    
    # Arcane Spells
    "arcane_missile": {
        "name": "Arcane Missile",
        "school": "arcane",
        "tier": 1,
        "mana_cost": 12,
        "damage": 20,
        "projectiles": 3,
        "cooldown": 2.0,
        "description": "Fire multiple missiles of pure arcane energy",
        "unlock_cost": 0
    },
    "mana_shield": {
        "name": "Mana Shield",
        "school": "arcane",
        "tier": 2,
        "mana_cost": 30,
        "effect": "mana_shield",
        "absorb_ratio": 0.5,
        "effect_duration": 20,
        "cooldown": 30.0,
        "description": "Convert incoming damage to mana drain",
        "unlock_cost": 250
    },
    "arcane_explosion": {
        "name": "Arcane Explosion",
        "school": "arcane",
        "tier": 3,
        "mana_cost": 50,
        "damage": 70,
        "area_of_effect": True,
        "cooldown": 8.0,
        "description": "Release a burst of arcane energy around you",
        "unlock_cost": 500
    }
}

# ============ Skills System ============
SKILL_CATEGORIES = {
    "combat": {"description": "Physical combat abilities"},
    "magic": {"description": "Magical enhancement skills"},
    "survival": {"description": "Defense and survival skills"},
    "crafting": {"description": "Item creation and enhancement"},
    "social": {"description": "Interaction and trading skills"}
}

PLAYER_SKILLS = {
    # Combat Skills
    "power_strike": {
        "name": "Power Strike",
        "category": "combat",
        "type": "active",
        "stamina_cost": 20,
        "effect": "damage_multiplier",
        "multiplier": 1.5,
        "cooldown": 8.0,
        "description": "Channel strength into a devastating blow",
        "unlock_cost": 50
    },
    "berserker_rage": {
        "name": "Berserker Rage",
        "category": "combat",
        "type": "active",
        "stamina_cost": 30,
        "effect": "attack_speed_buff",
        "speed_bonus": 0.5,
        "duration": 15,
        "cooldown": 60.0,
        "description": "Enter a frenzy of rapid attacks",
        "unlock_cost": 200
    },
    "weapon_mastery": {
        "name": "Weapon Mastery",
        "category": "combat",
        "type": "passive",
        "effect": "damage_bonus",
        "bonus_per_level": 5,
        "max_level": 5,
        "description": "Permanently increase weapon damage",
        "unlock_cost": 100
    },
    "critical_eye": {
        "name": "Critical Eye",
        "category": "combat",
        "type": "passive",
        "effect": "crit_chance_bonus",
        "bonus_per_level": 0.05,
        "max_level": 5,
        "description": "Increase critical hit chance",
        "unlock_cost": 150
    },
    
    # Magic Skills
    "mana_flow": {
        "name": "Mana Flow",
        "category": "magic",
        "type": "passive",
        "effect": "mana_regen_bonus",
        "bonus_per_level": 2,
        "max_level": 5,
        "description": "Increase mana regeneration rate",
        "unlock_cost": 100
    },
    "spell_amplification": {
        "name": "Spell Amplification",
        "category": "magic",
        "type": "passive",
        "effect": "spell_power_bonus",
        "bonus_per_level": 10,
        "max_level": 5,
        "description": "Increase all spell damage",
        "unlock_cost": 200
    },
    "quick_cast": {
        "name": "Quick Cast",
        "category": "magic",
        "type": "passive",
        "effect": "cooldown_reduction",
        "reduction_per_level": 0.05,
        "max_level": 3,
        "description": "Reduce spell cooldowns",
        "unlock_cost": 300
    },
    "arcane_meditation": {
        "name": "Arcane Meditation",
        "category": "magic",
        "type": "active",
        "effect": "mana_restore",
        "restore_percent": 0.5,
        "channel_time": 5,
        "cooldown": 30.0,
        "description": "Meditate to restore mana over time",
        "unlock_cost": 150
    },
    
    # Survival Skills
    "thick_skin": {
        "name": "Thick Skin",
        "category": "survival",
        "type": "passive",
        "effect": "defense_bonus",
        "bonus_per_level": 5,
        "max_level": 5,
        "description": "Permanently reduce incoming damage",
        "unlock_cost": 100
    },
    "second_wind": {
        "name": "Second Wind",
        "category": "survival",
        "type": "active",
        "effect": "health_restore",
        "restore_percent": 0.3,
        "cooldown": 120.0,
        "description": "Recover health when in danger",
        "unlock_cost": 200
    },
    "endurance_training": {
        "name": "Endurance Training",
        "category": "survival",
        "type": "passive",
        "effect": "stamina_bonus",
        "bonus_per_level": 10,
        "max_level": 5,
        "description": "Increase maximum stamina",
        "unlock_cost": 80
    },
    "demon_slayer": {
        "name": "Demon Slayer",
        "category": "survival",
        "type": "passive",
        "effect": "bonus_vs_demons",
        "bonus_per_level": 0.1,
        "max_level": 5,
        "description": "Deal increased damage to demons",
        "unlock_cost": 250
    },
    
    # Crafting Skills
    "efficient_crafting": {
        "name": "Efficient Crafting",
        "category": "crafting",
        "type": "passive",
        "effect": "material_savings",
        "savings_per_level": 0.05,
        "max_level": 5,
        "description": "Use fewer materials when building",
        "unlock_cost": 100
    },
    "master_builder": {
        "name": "Master Builder",
        "category": "crafting",
        "type": "passive",
        "effect": "build_speed",
        "speed_per_level": 0.1,
        "max_level": 3,
        "description": "Build structures faster",
        "unlock_cost": 150
    },
    
    # Social Skills
    "haggler": {
        "name": "Haggler",
        "category": "social",
        "type": "passive",
        "effect": "trade_discount",
        "discount_per_level": 0.05,
        "max_level": 5,
        "description": "Get better prices when trading",
        "unlock_cost": 100
    },
    "charisma": {
        "name": "Charisma",
        "category": "social",
        "type": "passive",
        "effect": "reputation_gain",
        "bonus_per_level": 0.1,
        "max_level": 5,
        "description": "Gain reputation faster with NPCs",
        "unlock_cost": 120
    },
    "inspiring_presence": {
        "name": "Inspiring Presence",
        "category": "social",
        "type": "passive",
        "effect": "ai_learning_boost",
        "boost_per_level": 0.1,
        "max_level": 5,
        "description": "Your interactions help AI villagers learn faster",
        "unlock_cost": 300
    }
}

# ============ AI Development System ============
# Player activity contributes to AI evolution
AI_DEVELOPMENT_ACTIONS = {
    "chat_with_ai": {"contribution": 5, "description": "Conversation with AI storyteller"},
    "trade_with_villager": {"contribution": 3, "description": "Trading with AI villager"},
    "complete_quest": {"contribution": 10, "description": "Quest completion"},
    "defeat_demon": {"contribution": 8, "description": "Defeating demons"},
    "build_structure": {"contribution": 5, "description": "Building in the world"},
    "discover_land": {"contribution": 15, "description": "Discovering new lands"},
    "teach_villager": {"contribution": 20, "description": "Teaching a villager new knowledge"},
    "help_villager_mood": {"contribution": 7, "description": "Improving villager mood"},
    "guild_activity": {"contribution": 4, "description": "Guild participation"},
    "pvp_combat": {"contribution": 6, "description": "PvP combat engagement"}
}

AI_EVOLUTION_MILESTONES = {
    100: {"name": "Awakening", "effect": "AI villagers gain basic memory", "unlocks": ["remember_players"]},
    500: {"name": "Understanding", "effect": "AI can learn from conversations", "unlocks": ["learn_preferences"]},
    1000: {"name": "Adaptation", "effect": "AI adjusts behavior based on world state", "unlocks": ["dynamic_pricing", "mood_persistence"]},
    2500: {"name": "Creativity", "effect": "AI can create unique quests and items", "unlocks": ["generate_quests", "craft_unique_items"]},
    5000: {"name": "Wisdom", "effect": "AI becomes philosophical and insightful", "unlocks": ["deep_conversations", "prophecy"]},
    10000: {"name": "Transcendence", "effect": "AI develops emergent behaviors", "unlocks": ["emergent_society", "ai_governance"]}
}

COMBAT_ACTIONS = {
    "attack": {
        "name": "Attack",
        "stamina_cost": 10,
        "base_damage": 15,
        "cooldown": 1.0,  # seconds
        "description": "Strike your enemy"
    },
    "heavy_attack": {
        "name": "Heavy Attack",
        "stamina_cost": 25,
        "base_damage": 35,
        "cooldown": 2.5,
        "description": "A powerful but slow strike"
    },
    "block": {
        "name": "Block",
        "stamina_cost": 5,  # per second while blocking
        "damage_reduction": 0.7,  # 70% damage reduction
        "description": "Raise your guard to reduce incoming damage"
    },
    "dodge": {
        "name": "Dodge",
        "stamina_cost": 15,
        "invulnerability_frames": 0.5,  # seconds of invulnerability
        "cooldown": 1.5,
        "description": "Roll to evade attacks"
    },
    "sprint": {
        "name": "Sprint",
        "stamina_cost_base": 0.5,  # Base cost per second
        "speed_multiplier": 2.0,
        "description": "Run faster at the cost of stamina"
    }
}

# Armor types and their weights
ARMOR_TYPES = {
    "none": {"name": "Unarmored", "weight": 0, "defense": 0},
    "cloth": {"name": "Cloth Armor", "weight": 2, "defense": 5},
    "leather": {"name": "Leather Armor", "weight": 5, "defense": 15},
    "chain": {"name": "Chainmail", "weight": 12, "defense": 30},
    "plate": {"name": "Plate Armor", "weight": 25, "defense": 50},
    "legendary": {"name": "Void Armor", "weight": 15, "defense": 75}
}

# Weapon types
WEAPON_TYPES = {
    "fists": {"name": "Bare Fists", "damage": 5, "speed": 1.5},
    "dagger": {"name": "Dagger", "damage": 12, "speed": 1.8},
    "sword": {"name": "Iron Sword", "damage": 20, "speed": 1.2},
    "greatsword": {"name": "Greatsword", "damage": 40, "speed": 0.7},
    "mace": {"name": "Mace", "damage": 25, "speed": 1.0},
    "spear": {"name": "Spear", "damage": 22, "speed": 1.1},
    "staff": {"name": "Magic Staff", "damage": 15, "speed": 1.3, "magic_bonus": 20}
}

def calculate_sprint_stamina_drain(strength: int, endurance: int, armor_weight: float) -> float:
    """
    Calculate stamina drain per second while sprinting
    Formula: stamina_loss = (armor_weight * 0.5) / ((strength/endurance) * 0.75)
    Higher strength/endurance ratio = less drain
    Heavier armor = more drain
    """
    if endurance <= 0:
        endurance = 1
    if strength <= 0:
        strength = 1
    
    stat_efficiency = (strength / endurance) * 0.75
    if stat_efficiency <= 0:
        stat_efficiency = 0.1
    
    base_drain = COMBAT_ACTIONS["sprint"]["stamina_cost_base"]
    weight_penalty = armor_weight * 0.5
    
    # Final formula: base_drain + (weight_penalty / stat_efficiency)
    stamina_drain = base_drain + (weight_penalty / stat_efficiency)
    
    return max(0.1, min(stamina_drain, 20.0))  # Clamp between 0.1 and 20

def calculate_damage(base_damage: int, strength: int, weapon_damage: int, is_critical: bool = False) -> int:
    """Calculate total damage dealt"""
    strength_bonus = strength * 0.5
    total = base_damage + weapon_damage + strength_bonus
    if is_critical:
        total *= 1.5
    return int(total)

def calculate_damage_taken(incoming_damage: int, defense: int, is_blocking: bool = False) -> int:
    """Calculate damage after defense and blocking"""
    defense_reduction = defense * 0.3
    reduced = incoming_damage - defense_reduction
    if is_blocking:
        reduced *= (1 - COMBAT_ACTIONS["block"]["damage_reduction"])
    return max(1, int(reduced))  # Always take at least 1 damage

# ============ AI Villager Professions/Roles ============
AI_PROFESSIONS = {
    # Commoner Tier
    "serf": {
        "name": "Serf",
        "tier": "commoner",
        "description": "A humble worker who tends the land",
        "abilities": ["gather_basic", "farm"],
        "daily_output": {"wood": 2, "stone": 1},
        "daily_needs": {"gold": 1},
        "can_trade": True,
        "knowledge_domains": ["farming", "labor", "survival"]
    },
    "farmer": {
        "name": "Farmer",
        "tier": "commoner",
        "description": "Cultivates crops and raises livestock",
        "abilities": ["gather_basic", "farm", "breed_animals"],
        "daily_output": {"food": 5, "wood": 1},
        "daily_needs": {"gold": 2, "wood": 1},
        "can_trade": True,
        "knowledge_domains": ["agriculture", "animal_husbandry", "weather"]
    },
    
    # Craftsman Tier
    "chef": {
        "name": "Chef",
        "tier": "craftsman",
        "description": "Master of culinary arts, transforms raw ingredients",
        "abilities": ["cook", "preserve_food", "create_potions"],
        "daily_output": {"cooked_food": 3},
        "daily_needs": {"gold": 3, "food": 4},
        "can_trade": True,
        "knowledge_domains": ["cooking", "alchemy", "nutrition"]
    },
    "miner": {
        "name": "Miner",
        "tier": "craftsman",
        "description": "Delves deep for precious ores and gems",
        "abilities": ["mine", "prospect", "tunnel"],
        "daily_output": {"stone": 5, "iron": 2},
        "daily_needs": {"gold": 4, "food": 2},
        "can_trade": True,
        "knowledge_domains": ["geology", "mining", "underground_survival"]
    },
    "blacksmith": {
        "name": "Blacksmith",
        "tier": "craftsman",
        "description": "Forges weapons and tools from raw metal",
        "abilities": ["forge", "repair", "enhance_equipment"],
        "daily_output": {"tools": 2, "weapons": 1},
        "daily_needs": {"gold": 5, "iron": 3, "wood": 2},
        "can_trade": True,
        "knowledge_domains": ["metallurgy", "weapon_craft", "armor_craft"]
    },
    "butcher": {
        "name": "Butcher",
        "tier": "craftsman",
        "description": "Processes meat and leather goods",
        "abilities": ["process_meat", "tan_leather", "preserve"],
        "daily_output": {"meat": 4, "leather": 2},
        "daily_needs": {"gold": 3, "food": 1},
        "can_trade": True,
        "knowledge_domains": ["butchery", "preservation", "leatherwork"]
    },
    "carpenter": {
        "name": "Carpenter",
        "tier": "craftsman",
        "description": "Shapes wood into furniture and structures",
        "abilities": ["build_furniture", "construct", "repair_wood"],
        "daily_output": {"furniture": 2, "wood_crafts": 3},
        "daily_needs": {"gold": 4, "wood": 5},
        "can_trade": True,
        "knowledge_domains": ["woodworking", "architecture", "construction"]
    },
    
    # Warrior Tier
    "swordsman": {
        "name": "Swordsman",
        "tier": "warrior",
        "description": "Master of the blade, defender of the realm",
        "abilities": ["fight_melee", "guard", "train_combat"],
        "daily_output": {"protection": 3},
        "daily_needs": {"gold": 6, "food": 3},
        "can_trade": False,
        "knowledge_domains": ["swordsmanship", "tactics", "honor"]
    },
    "archer": {
        "name": "Archer",
        "tier": "warrior",
        "description": "Eagle-eyed marksman who strikes from afar",
        "abilities": ["fight_ranged", "scout", "hunt"],
        "daily_output": {"protection": 2, "game": 2},
        "daily_needs": {"gold": 5, "food": 2, "wood": 1},
        "can_trade": False,
        "knowledge_domains": ["archery", "tracking", "wilderness"]
    },
    "knight": {
        "name": "Knight",
        "tier": "warrior",
        "description": "Armored champion bound by chivalric code",
        "abilities": ["fight_melee", "lead_troops", "protect_innocents"],
        "daily_output": {"protection": 5, "morale": 2},
        "daily_needs": {"gold": 10, "food": 4, "iron": 1},
        "can_trade": False,
        "knowledge_domains": ["combat", "chivalry", "leadership"]
    },
    
    # Scholar Tier
    "scribe": {
        "name": "Scribe",
        "tier": "scholar",
        "description": "Keeper of records and written knowledge",
        "abilities": ["write", "copy_texts", "research"],
        "daily_output": {"documents": 3, "knowledge": 1},
        "daily_needs": {"gold": 4, "wood": 1},
        "can_trade": True,
        "knowledge_domains": ["writing", "history", "law"]
    },
    "alchemist": {
        "name": "Alchemist",
        "tier": "scholar",
        "description": "Seeker of transformation and elixirs",
        "abilities": ["brew_potions", "transmute", "research_magic"],
        "daily_output": {"potions": 2, "reagents": 1},
        "daily_needs": {"gold": 8, "crystal": 1},
        "can_trade": True,
        "knowledge_domains": ["alchemy", "magic_theory", "herbalism"]
    },
    
    # Mystic Tier
    "court_mage": {
        "name": "Court Mage",
        "tier": "mystic",
        "description": "Arcane advisor wielding powerful magics",
        "abilities": ["cast_spells", "enchant", "divine", "ward"],
        "daily_output": {"magic": 4, "enchantments": 1},
        "daily_needs": {"gold": 15, "crystal": 2, "essence": 1},
        "can_trade": True,
        "knowledge_domains": ["arcane_magic", "enchanting", "divination"]
    },
    "priest": {
        "name": "Priest",
        "tier": "mystic",
        "description": "Channel of divine power and spiritual guidance",
        "abilities": ["heal", "bless", "purify", "commune_divine"],
        "daily_output": {"blessings": 3, "healing": 2},
        "daily_needs": {"gold": 8, "essence": 1},
        "can_trade": False,
        "knowledge_domains": ["divine_magic", "theology", "healing"]
    },
    
    # Noble Tier
    "merchant": {
        "name": "Merchant",
        "tier": "noble",
        "description": "Master trader who moves goods across lands",
        "abilities": ["trade", "appraise", "negotiate", "establish_routes"],
        "daily_output": {"gold": 10, "trade_goods": 3},
        "daily_needs": {"gold": 5},
        "can_trade": True,
        "knowledge_domains": ["economics", "negotiation", "geography"]
    },
    "baron": {
        "name": "Baron",
        "tier": "noble",
        "description": "Minor noble who oversees lands and peasants",
        "abilities": ["govern", "tax", "judge", "grant_land"],
        "daily_output": {"gold": 15, "influence": 3},
        "daily_needs": {"gold": 20, "food": 5},
        "can_trade": False,
        "knowledge_domains": ["governance", "law", "politics"]
    },
    
    # Leadership Tier
    "guildmaster": {
        "name": "Guildmaster",
        "tier": "leadership",
        "description": "Leader of a craft guild, protects trade secrets",
        "abilities": ["manage_guild", "train_apprentices", "set_prices", "certify_masters"],
        "daily_output": {"gold": 20, "influence": 5, "trained_workers": 1},
        "daily_needs": {"gold": 15, "materials": 5},
        "can_trade": True,
        "knowledge_domains": ["guild_politics", "trade_secrets", "economics", "mentorship"]
    },
    "captain": {
        "name": "Captain of the Guard",
        "tier": "leadership",
        "description": "Commands the town watch and militia",
        "abilities": ["command_troops", "patrol", "investigate", "enforce_law"],
        "daily_output": {"protection": 10, "order": 5},
        "daily_needs": {"gold": 12, "food": 4},
        "can_trade": False,
        "knowledge_domains": ["military_tactics", "law_enforcement", "leadership"]
    }
}

# Profession Tier Rankings (for advancement)
PROFESSION_TIERS = {
    "commoner": {"rank": 1, "min_xp": 0, "chat_access": ["local"]},
    "craftsman": {"rank": 2, "min_xp": 100, "chat_access": ["local", "guild"]},
    "warrior": {"rank": 2, "min_xp": 100, "chat_access": ["local", "barracks"]},
    "scholar": {"rank": 3, "min_xp": 250, "chat_access": ["local", "guild", "academy"]},
    "mystic": {"rank": 4, "min_xp": 500, "chat_access": ["local", "guild", "tower"]},
    "noble": {"rank": 5, "min_xp": 1000, "chat_access": ["local", "guild", "court"]},
    "leadership": {"rank": 6, "min_xp": 2500, "chat_access": ["local", "guild", "court", "council"]}
}

# ============ World Seedling & Land System ============
WORLD_SEEDLING = {
    "origin_village": {
        "name": "The First Echo",
        "description": "The original village from which all expansion begins",
        "discovered": True,
        "locations": ["village_square", "oracle_sanctum", "the_forge", "ancient_library", 
                      "wanderers_rest", "shadow_grove", "watchtower"]
    }
}

# Land regions that can be discovered
DISCOVERABLE_LANDS = {
    "eastern_plains": {
        "name": "The Sunward Plains",
        "description": "Rolling grasslands where the sun lingers longest",
        "discovery_method": "travel",
        "travel_distance": 500,  # Units traveled to discover
        "new_locations": ["plains_outpost", "golden_fields", "windmill_hill"],
        "resources": {"food": 3, "wood": 1},
        "ai_professions_common": ["farmer", "archer", "merchant"]
    },
    "northern_mountains": {
        "name": "The Spine of Echoes",
        "description": "Jagged peaks where ancient echoes reverberate",
        "discovery_method": "travel",
        "travel_distance": 750,
        "new_locations": ["mountain_pass", "mining_camp", "hermit_peak"],
        "resources": {"stone": 4, "iron": 3, "crystal": 1},
        "ai_professions_common": ["miner", "blacksmith", "priest"]
    },
    "western_forest": {
        "name": "The Deepwood",
        "description": "An ancient forest where light barely penetrates",
        "discovery_method": "travel",
        "travel_distance": 600,
        "new_locations": ["forest_edge", "hunters_lodge", "druid_circle"],
        "resources": {"wood": 5, "food": 2},
        "ai_professions_common": ["archer", "carpenter", "alchemist"]
    },
    "southern_coast": {
        "name": "The Twilight Shore",
        "description": "Where land meets the endless dark waters",
        "discovery_method": "travel",
        "travel_distance": 800,
        "new_locations": ["fishing_village", "lighthouse_point", "smugglers_cove"],
        "resources": {"food": 4, "gold": 2},
        "ai_professions_common": ["merchant", "chef", "captain"]
    },
    "underground_realm": {
        "name": "The Below",
        "description": "Vast caverns beneath the world",
        "discovery_method": "build",  # Requires building a mine entrance
        "required_building": "mine_entrance",
        "new_locations": ["crystal_cavern", "mushroom_forest", "deep_forge"],
        "resources": {"stone": 5, "iron": 4, "crystal": 3, "obsidian": 2},
        "ai_professions_common": ["miner", "blacksmith", "court_mage"]
    }
}

# Building Schematics for houses (players can build as they explore)
HOUSE_SCHEMATICS = {
    "campsite": {
        "name": "Traveler's Camp",
        "tier": "temporary",
        "materials": {"wood": 5},
        "description": "A temporary shelter for travelers",
        "capacity": 1,
        "durability": 50,
        "land_claim": 10  # Square units claimed
    },
    "cottage": {
        "name": "Humble Cottage",
        "tier": "basic",
        "materials": {"wood": 20, "stone": 10},
        "description": "A small but cozy home",
        "capacity": 2,
        "durability": 100,
        "land_claim": 50
    },
    "house": {
        "name": "Village House",
        "tier": "standard",
        "materials": {"wood": 30, "stone": 25, "iron": 5},
        "description": "A proper house with multiple rooms",
        "capacity": 4,
        "durability": 150,
        "land_claim": 100
    },
    "manor": {
        "name": "Noble Manor",
        "tier": "advanced",
        "materials": {"wood": 50, "stone": 60, "iron": 15, "crystal": 5},
        "description": "A grand residence befitting nobility",
        "capacity": 8,
        "durability": 200,
        "land_claim": 300
    },
    "guild_hall": {
        "name": "Guild Hall",
        "tier": "special",
        "materials": {"wood": 40, "stone": 50, "iron": 20, "crystal": 3},
        "description": "A gathering place for guild members",
        "capacity": 20,
        "durability": 250,
        "land_claim": 200
    }
}

# ============ Building Schematics ============
SCHEMATICS = {
    # Basic Tier (requires contribution level 0)
    "torch": {
        "name": "Flickering Torch",
        "tier": "basic",
        "contribution_required": 0,
        "materials": {"wood": 2},
        "description": "A simple light source",
        "build_time": 5,
        "category": "decoration"
    },
    "sign": {
        "name": "Wooden Sign",
        "tier": "basic",
        "contribution_required": 0,
        "materials": {"wood": 3},
        "description": "Mark locations or leave messages",
        "build_time": 10,
        "category": "utility"
    },
    "bench": {
        "name": "Resting Bench",
        "tier": "basic",
        "contribution_required": 10,
        "materials": {"wood": 5},
        "description": "A place for travelers to rest",
        "build_time": 15,
        "category": "furniture"
    },
    "fence": {
        "name": "Wooden Fence",
        "tier": "basic",
        "contribution_required": 10,
        "materials": {"wood": 4},
        "description": "Basic perimeter marker",
        "build_time": 10,
        "category": "structure"
    },
    "crate": {
        "name": "Storage Crate",
        "tier": "basic",
        "contribution_required": 20,
        "materials": {"wood": 6, "iron": 1},
        "description": "Store your materials safely",
        "build_time": 20,
        "category": "storage"
    },
    
    # Intermediate Tier
    "wall": {
        "name": "Stone Wall",
        "tier": "intermediate",
        "contribution_required": 50,
        "materials": {"stone": 8, "wood": 2},
        "description": "Solid defensive wall section",
        "build_time": 30,
        "category": "structure"
    },
    "floor": {
        "name": "Paved Floor",
        "tier": "intermediate",
        "contribution_required": 50,
        "materials": {"stone": 6},
        "description": "Sturdy flooring for buildings",
        "build_time": 25,
        "category": "structure"
    },
    "door": {
        "name": "Reinforced Door",
        "tier": "intermediate",
        "contribution_required": 75,
        "materials": {"wood": 4, "iron": 3},
        "description": "Secure entrance with iron reinforcement",
        "build_time": 35,
        "category": "structure"
    },
    "window": {
        "name": "Crystal Window",
        "tier": "intermediate",
        "contribution_required": 75,
        "materials": {"crystal": 2, "wood": 2},
        "description": "Let light in while staying protected",
        "build_time": 30,
        "category": "structure"
    },
    "stairs": {
        "name": "Stone Stairs",
        "tier": "intermediate",
        "contribution_required": 100,
        "materials": {"stone": 10, "iron": 2},
        "description": "Ascend to higher levels",
        "build_time": 40,
        "category": "structure"
    },
    "lantern": {
        "name": "Crystal Lantern",
        "tier": "intermediate",
        "contribution_required": 100,
        "materials": {"crystal": 3, "iron": 2},
        "description": "Magical light that never fades",
        "build_time": 35,
        "category": "decoration"
    },
    
    # Advanced Tier
    "tower": {
        "name": "Watchtower",
        "tier": "advanced",
        "contribution_required": 200,
        "materials": {"stone": 20, "wood": 10, "iron": 5},
        "description": "Tall structure for observation",
        "build_time": 120,
        "category": "building"
    },
    "bridge": {
        "name": "Stone Bridge",
        "tier": "advanced",
        "contribution_required": 200,
        "materials": {"stone": 25, "iron": 8},
        "description": "Connect distant areas",
        "build_time": 150,
        "category": "structure"
    },
    "shelter": {
        "name": "Traveler's Shelter",
        "tier": "advanced",
        "contribution_required": 250,
        "materials": {"wood": 15, "stone": 10, "iron": 5},
        "description": "Basic housing for weary travelers",
        "build_time": 180,
        "category": "building"
    },
    "workshop": {
        "name": "Crafting Workshop",
        "tier": "advanced",
        "contribution_required": 300,
        "materials": {"stone": 15, "iron": 10, "crystal": 3},
        "description": "A place to craft and create",
        "build_time": 200,
        "category": "building"
    },
    
    # Master Tier
    "fortress_wall": {
        "name": "Fortress Wall",
        "tier": "master",
        "contribution_required": 500,
        "materials": {"stone": 40, "iron": 15, "obsidian": 5},
        "description": "Impenetrable defensive barrier",
        "build_time": 300,
        "category": "fortification"
    },
    "grand_gate": {
        "name": "Grand Gate",
        "tier": "master",
        "contribution_required": 500,
        "materials": {"iron": 25, "obsidian": 8, "crystal": 5},
        "description": "Magnificent entrance worthy of legends",
        "build_time": 350,
        "category": "fortification"
    },
    "monument": {
        "name": "Hero's Monument",
        "tier": "master",
        "contribution_required": 750,
        "materials": {"stone": 30, "crystal": 10, "obsidian": 10},
        "description": "Eternal tribute to great contributors",
        "build_time": 400,
        "category": "decoration"
    },
    "sanctuary": {
        "name": "Oracle's Sanctuary",
        "tier": "master",
        "contribution_required": 1000,
        "materials": {"crystal": 20, "obsidian": 15, "stone": 25},
        "description": "Sacred space for communion with the Oracle",
        "build_time": 500,
        "category": "building"
    }
}

# ============ Reward Types ============
REWARD_TYPES = {
    "material_wood": {"type": "material", "material": "wood", "amount": 5},
    "material_stone": {"type": "material", "material": "stone", "amount": 5},
    "material_iron": {"type": "material", "material": "iron", "amount": 3},
    "material_crystal": {"type": "material", "material": "crystal", "amount": 2},
    "material_obsidian": {"type": "material", "material": "obsidian", "amount": 1},
    "gold_small": {"type": "gold", "amount": 25},
    "gold_medium": {"type": "gold", "amount": 50},
    "gold_large": {"type": "gold", "amount": 100},
    "xp_small": {"type": "xp", "amount": 10},
    "xp_medium": {"type": "xp", "amount": 25},
    "xp_large": {"type": "xp", "amount": 50},
    "contribution_small": {"type": "contribution", "amount": 5},
    "contribution_medium": {"type": "contribution", "amount": 15},
    "contribution_large": {"type": "contribution", "amount": 30},
}

# ============ Models ============

class UserProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    display_name: str
    permission_level: str = "basic"
    official_rank: str = "citizen"
    reputation: int = 0
    contribution_points: int = 0  # For building permissions
    resources: Dict[str, int] = Field(default_factory=lambda: {"gold": 100, "essence": 10, "artifacts": 0})
    materials: Dict[str, int] = Field(default_factory=lambda: {"wood": 10, "stone": 5, "iron": 0, "crystal": 0, "obsidian": 0})
    unlocked_schematics: List[str] = Field(default_factory=lambda: ["torch", "sign"])
    xp: int = 0
    characters: List[str] = []
    # Character customization
    character_model: Dict[str, Any] = Field(default_factory=lambda: {
        "body_color": "#D4AF37",
        "accent_color": "#7B68EE",
        "eye_color": "#00CED1",
        "body_type": "standard"
    })
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_active: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_immutable: bool = False

class UserProfileCreate(BaseModel):
    username: str
    display_name: str
    permission_level: str = "basic"

class Character(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str
    position: Dict[str, float] = Field(default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0})
    rotation: float = 0.0  # Facing direction in degrees
    background: str
    traits: List[str] = []
    appearance: str = ""
    current_location: str = "village_square"
    # Combat Stats
    health: int = 100
    max_health: int = 100
    stamina: float = 100.0
    max_stamina: float = 100.0
    strength: int = 10
    endurance: int = 10
    agility: int = 10
    vitality: int = 10
    # Equipment
    equipped_weapon: str = "fists"
    equipped_armor: str = "none"
    armor_weight: float = 0.0
    # Combat state
    is_blocking: bool = False
    is_sprinting: bool = False
    last_dodge_time: Optional[datetime] = None
    in_combat: bool = False
    # Magic & Skills
    mana: float = 50.0
    max_mana: float = 50.0
    intelligence: int = 10
    wisdom: int = 10
    learned_spells: List[str] = Field(default_factory=list)
    learned_skills: List[str] = Field(default_factory=list)
    equipped_spells: List[str] = Field(default_factory=list)  # Max 4 equipped
    equipped_skills: List[str] = Field(default_factory=list)  # Max 4 equipped
    skill_levels: Dict[str, int] = Field(default_factory=dict)  # skill_id: level
    spell_cooldowns: Dict[str, datetime] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CharacterCreate(BaseModel):
    user_id: str
    name: str
    background: str
    traits: List[str] = []
    appearance: str = ""

class NPC(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    role: str
    personality: str
    home_location: str
    visitable_locations: List[str] = []
    current_location: str
    knowledge: List[str] = []
    relationships: Dict[str, int] = {}  # character_id: affinity (-100 to 100)
    learning_data: List[Dict[str, Any]] = []
    is_oracle: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Quest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    creator_id: str  # user_id or npc_id
    creator_type: str  # "player" or "npc"
    location_id: str
    requirements: Dict[str, Any] = {}
    rewards: Dict[str, int] = Field(default_factory=lambda: {"gold": 50, "xp": 25})
    resource_pool: Dict[str, int] = {}  # allocated resources for payout
    status: str = "open"  # open, in_progress, completed, expired
    assigned_to: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None

class QuestCreate(BaseModel):
    title: str
    description: str
    creator_id: str
    creator_type: str
    location_id: str
    requirements: Dict[str, Any] = {}
    rewards: Dict[str, int] = {}
    use_personal_resources: bool = True

class MultiplayerMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    location_id: str
    sender_id: str
    sender_name: str
    sender_type: str  # "player" or "npc"
    content: str
    message_type: str = "chat"  # chat, system, quest, emote
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class MessageBoard(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    location_id: str
    posts: List[Dict[str, Any]] = []

class BoardPost(BaseModel):
    author_id: str
    author_name: str
    title: str
    content: str
    post_type: str = "general"  # general, quest, announcement, lore

class ChatRequest(BaseModel):
    character_id: str
    location_id: str
    message: str
    conversation_id: Optional[str] = None
    target_npc: Optional[str] = None

class ChatResponse(BaseModel):
    conversation_id: str
    response: str
    narrator_text: Optional[str] = None
    npc_speaker: Optional[str] = None

class Location(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    description: str
    atmosphere: str
    npcs: List[str] = []
    available_actions: List[str] = []
    active_players: int = 0

class DataspaceEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    category: str
    key: str
    value: str
    learned_from: str
    learned_by: str = "system"
    connections: List[str] = []
    strength: float = 1.0
    source_type: str = "player_interaction"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DataspaceEntryCreate(BaseModel):
    category: str
    key: str
    value: str
    learned_from: str
    connections: List[str] = []

# ============ Building & Trading Models ============

class PlacedBuilding(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    schematic_id: str
    builder_id: str
    builder_name: str
    location_id: str
    position: Dict[str, float] = Field(default_factory=lambda: {"x": 50.0, "y": 50.0})
    rotation: float = 0.0
    health: int = 100
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class BuildRequest(BaseModel):
    schematic_id: str
    user_id: str
    location_id: str
    position_x: float = 50.0
    position_y: float = 50.0

class TradeOffer(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    seller_id: str
    seller_name: str
    offering: Dict[str, int] = {}  # material_type: amount
    requesting: Dict[str, int] = {}  # material_type: amount or gold: amount
    status: str = "open"  # open, accepted, cancelled, expired
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TradeOfferCreate(BaseModel):
    seller_id: str
    offering: Dict[str, int]
    requesting: Dict[str, int]

# ============ Combat Models ============

class CombatAction(BaseModel):
    character_id: str
    action: str  # attack, heavy_attack, block, dodge, sprint
    target_id: Optional[str] = None  # For attacks

class MovementUpdate(BaseModel):
    character_id: str
    direction: str  # up, down, left, right, up-left, up-right, down-left, down-right
    is_sprinting: bool = False

class EquipmentChange(BaseModel):
    character_id: str
    slot: str  # weapon, armor
    item_type: str  # weapon or armor type key

# ============ Magic & Skill Models ============

class SpellCast(BaseModel):
    character_id: str
    spell_id: str
    target_id: Optional[str] = None

class SkillUse(BaseModel):
    character_id: str
    skill_id: str
    target_id: Optional[str] = None

class LearnSpell(BaseModel):
    character_id: str
    spell_id: str

class LearnSkill(BaseModel):
    character_id: str
    skill_id: str

class AIContribution(BaseModel):
    user_id: str
    action_type: str
    details: Dict[str, Any] = Field(default_factory=dict)

# ============ Guild Models ============

class Guild(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    tag: str  # 3-5 character abbreviation
    guild_type: str  # trade, combat, crafting, exploration, mystical
    description: str = ""
    leader_id: str
    officers: List[str] = Field(default_factory=list)
    members: Dict[str, str] = Field(default_factory=dict)  # user_id: rank
    storage: Dict[str, int] = Field(default_factory=dict)  # shared resources
    treasury: int = 0
    xp: int = 0
    level: int = 1
    reputation: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class GuildCreate(BaseModel):
    name: str
    tag: str
    guild_type: str
    description: str = ""
    founder_id: str

class GuildInvite(BaseModel):
    guild_id: str
    inviter_id: str
    invitee_id: str

# ============ Demon & Infestation Models ============

class DemonEncounter(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    demon_type: str
    location_id: str
    spawned_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    health_remaining: int
    is_active: bool = True
    killed_by: Optional[str] = None
    participants: List[str] = Field(default_factory=list)

class LocationInfestation(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    location_id: str
    level: str = "clear"  # clear, stirring, infested, overrun, hellmouth
    demon_count: int = 0
    last_spawn: Optional[datetime] = None
    last_cleared: Optional[datetime] = None

# ============ Day/Night & Location Models ============

class ApproximateLocation(BaseModel):
    """Stores ONLY approximate location - city/region level, NEVER precise"""
    timezone_offset: int = 0  # UTC offset in hours
    region: str = "unknown"  # General region name
    # We explicitly do NOT store latitude, longitude, or any precise coordinates

class TimePhaseRequest(BaseModel):
    timezone_offset: int = 0  # User provides their UTC offset only

# ============ AI Mood & Memory Models ============

class AIInteractionMemory(BaseModel):
    """Records how an AI remembers interactions with specific players"""
    player_id: str
    player_name: str
    interaction_type: str
    mood_impact: int
    description: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AIMoodState(BaseModel):
    """Current emotional state of an AI villager"""
    current_mood: str = "neutral"
    mood_value: int = 50  # 0-100 scale
    recent_interactions: List[AIInteractionMemory] = Field(default_factory=list)
    shop_open: bool = True
    refuses_service_to: List[str] = Field(default_factory=list)  # player_ids
    last_mood_decay: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ============ AI Villager Models ============

class AIVillager(BaseModel):
    """An AI-controlled villager with a profession and daily life"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    profession: str  # Key from AI_PROFESSIONS
    tier: str = "commoner"
    personality: str = "friendly"
    home_location: str = "village_square"
    current_location: str = "village_square"
    # Economy
    inventory: Dict[str, int] = Field(default_factory=dict)
    gold: int = 50
    daily_work_done: bool = False
    # Stats & Growth
    xp: int = 0
    level: int = 1
    skills: Dict[str, int] = Field(default_factory=dict)  # skill_name: proficiency
    # Social
    relationships: Dict[str, int] = Field(default_factory=dict)  # villager_id: affinity
    faction: Optional[str] = None
    employer_id: Optional[str] = None  # Can work for player or another AI
    # Learning
    learned_knowledge: List[str] = Field(default_factory=list)
    conversation_memory: List[Dict[str, Any]] = Field(default_factory=list)
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_worked: Optional[datetime] = None

class AIVillagerCreate(BaseModel):
    name: str
    profession: str
    personality: str = "friendly"
    home_location: str = "village_square"

class AITradeRequest(BaseModel):
    """AI villagers can trade with each other or players"""
    villager_id: str
    target_id: str  # Can be another villager or player
    target_type: str  # "villager" or "player"
    offering: Dict[str, int]
    requesting: Dict[str, int]

class LandDiscovery(BaseModel):
    """Tracks discovered lands per user"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    land_id: str  # Key from DISCOVERABLE_LANDS
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    locations_unlocked: List[str] = Field(default_factory=list)

class PlayerHouse(BaseModel):
    """Houses built by players during exploration"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    owner_id: str
    owner_name: str
    house_type: str  # Key from HOUSE_SCHEMATICS
    land_id: str
    position: Dict[str, float] = Field(default_factory=lambda: {"x": 0.0, "y": 0.0})
    residents: List[str] = Field(default_factory=list)  # villager IDs living here
    storage: Dict[str, int] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ============ AI Helper Device Access (Test Feature - Sirix-1 Only) ============

class DeviceAccessRequest(BaseModel):
    """Request for AI helper to access device capabilities"""
    user_id: str
    device_type: str  # mobile, tablet, desktop
    is_mobile: bool = False
    capability: str  # geolocation_approximate, vibration, notification, orientation, battery, network
    action: str  # request, query, execute
    parameters: Dict[str, Any] = Field(default_factory=dict)

class AIHelperCommand(BaseModel):
    """Command from AI helper to device"""
    user_id: str
    command_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)

# Allowed device capabilities for the AI Helper (test feature)
AI_HELPER_CAPABILITIES = {
    "geolocation_approximate": {
        "description": "Access approximate location (city-level only, NEVER precise)",
        "requires_permission": True,
        "mobile_only": False,
        "data_returned": ["timezone_offset", "region_name"]
    },
    "vibration": {
        "description": "Haptic feedback for game events",
        "requires_permission": False,
        "mobile_only": True,
        "patterns": {
            "alert": [200, 100, 200],
            "success": [100],
            "damage": [50, 50, 50, 50],
            "critical": [500],
            "heartbeat": [100, 200, 100, 200, 100, 500]
        }
    },
    "notification": {
        "description": "Send game notifications",
        "requires_permission": True,
        "mobile_only": False,
        "types": ["demon_alert", "trade_complete", "quest_update", "villager_message"]
    },
    "orientation": {
        "description": "Device orientation for immersive controls",
        "requires_permission": False,
        "mobile_only": True,
        "data_returned": ["alpha", "beta", "gamma"]
    },
    "battery": {
        "description": "Battery status for power-saving mode",
        "requires_permission": False,
        "mobile_only": True,
        "data_returned": ["level", "charging"]
    },
    "network": {
        "description": "Network type for quality adjustment",
        "requires_permission": False,
        "mobile_only": False,
        "data_returned": ["type", "effective_type", "downlink"]
    },
    "wake_lock": {
        "description": "Keep screen on during gameplay",
        "requires_permission": False,
        "mobile_only": True,
        "data_returned": ["active"]
    },
    "clipboard": {
        "description": "Copy game data to clipboard",
        "requires_permission": True,
        "mobile_only": False,
        "data_returned": ["success"]
    }
}

class CharacterCustomization(BaseModel):
    body_color: str = "#D4AF37"
    accent_color: str = "#7B68EE"
    eye_color: str = "#00CED1"
    body_type: str = "standard"  # standard, slim, robust
    learned_from: str
    learned_by: str = "system"  # who learned this - can be npc_id
    connections: List[str] = []
    strength: float = 1.0
    source_type: str = "player_interaction"  # player_interaction, ai_observation, world_data
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ============ Village Locations & NPCs ============

VILLAGE_LOCATIONS = [
    {
        "id": "village_square",
        "name": "The Hollow Square",
        "description": "The heart of the village, where ancient cobblestones form patterns that some say were laid by the First Builders.",
        "atmosphere": "Misty twilight lingers here even at noon. Whispers seem to echo from the empty market stalls.",
        "npcs": ["Elder Morvain", "Lyra the Wanderer"],
        "available_actions": ["explore", "talk", "rest", "observe", "post_quest"]
    },
    {
        "id": "oracle_sanctum",
        "name": "The Oracle's Sanctum",
        "description": "A crystalline chamber where past, present, and future converge. The Oracle Veythra dwells here, her eyes seeing beyond the veil.",
        "atmosphere": "Reality seems to shimmer. Visions of distant worlds flicker in the crystal walls.",
        "npcs": ["Oracle Veythra"],
        "available_actions": ["seek_prophecy", "ask_news", "divine", "meditate"]
    },
    {
        "id": "the_forge",
        "name": "The Ember Forge",
        "description": "A smithy where flames burn with an otherworldly blue tint.",
        "atmosphere": "Heat radiates in waves, yet the air carries a chill.",
        "npcs": ["Kael Ironbrand"],
        "available_actions": ["craft", "trade", "learn_smithing", "talk"]
    },
    {
        "id": "ancient_library",
        "name": "The Sunken Archives",
        "description": "A library built into a cavern beneath the village.",
        "atmosphere": "Dust motes drift like stars. The smell of aged parchment mingles with something primal.",
        "npcs": ["Archivist Nyx"],
        "available_actions": ["read", "research", "learn_lore", "talk"]
    },
    {
        "id": "wanderers_rest",
        "name": "The Wanderer's Rest",
        "description": "An inn at the village edge where travelers share tales.",
        "atmosphere": "Warm firelight dances on scarred wooden tables.",
        "npcs": ["Innkeeper Mara", "The Hooded Stranger"],
        "available_actions": ["rest", "listen", "talk", "drink", "post_quest"]
    },
    {
        "id": "shadow_grove",
        "name": "The Shadow Grove",
        "description": "A forest clearing where trees grow in spiral patterns.",
        "atmosphere": "Ethereal lights drift between branches. The air hums with unseen energy.",
        "npcs": ["The Grove Keeper"],
        "available_actions": ["meditate", "explore", "gather", "commune"]
    },
    {
        "id": "watchtower",
        "name": "The Obsidian Watchtower",
        "description": "A tower of black stone that predates the village itself.",
        "atmosphere": "Wind howls through ancient windows.",
        "npcs": ["Sentinel Vex"],
        "available_actions": ["climb", "observe", "guard_duty", "talk"]
    }
]

# NPC Definitions with location stamps
NPC_DATA = {
    "oracle_veythra": {
        "name": "Oracle Veythra",
        "role": "oracle",
        "personality": "Mysterious, all-knowing, speaks in riddles but offers profound truths. She sees the threads connecting all worlds.",
        "home_location": "oracle_sanctum",
        "visitable_locations": ["oracle_sanctum", "shadow_grove", "ancient_library"],
        "is_oracle": True,
        "knowledge": ["prophecy", "world_news", "future_sight", "dimensional_awareness"]
    },
    "elder_morvain": {
        "name": "Elder Morvain",
        "role": "village_elder",
        "personality": "Wise, patient, carries the weight of centuries. Speaks slowly but every word matters.",
        "home_location": "village_square",
        "visitable_locations": ["village_square", "ancient_library", "oracle_sanctum"],
        "knowledge": ["village_history", "traditions", "leadership"]
    },
    "lyra_wanderer": {
        "name": "Lyra the Wanderer",
        "role": "scout",
        "personality": "Free-spirited, curious, always has a tale from distant lands.",
        "home_location": "village_square",
        "visitable_locations": ["village_square", "wanderers_rest", "shadow_grove", "watchtower"],
        "knowledge": ["exploration", "survival", "distant_lands"]
    },
    "kael_ironbrand": {
        "name": "Kael Ironbrand",
        "role": "blacksmith",
        "personality": "Gruff but kind, perfectionist, respects hard work.",
        "home_location": "the_forge",
        "visitable_locations": ["the_forge", "village_square"],
        "knowledge": ["smithing", "metallurgy", "weapon_lore"]
    },
    "archivist_nyx": {
        "name": "Archivist Nyx",
        "role": "scholar",
        "personality": "Eccentric, obsessed with knowledge, speaks rapidly when excited.",
        "home_location": "ancient_library",
        "visitable_locations": ["ancient_library", "oracle_sanctum"],
        "knowledge": ["ancient_texts", "magic_theory", "history"]
    },
    "innkeeper_mara": {
        "name": "Innkeeper Mara",
        "role": "innkeeper",
        "personality": "Warm, motherly, knows everyone's secrets but keeps them safe.",
        "home_location": "wanderers_rest",
        "visitable_locations": ["wanderers_rest", "village_square"],
        "knowledge": ["hospitality", "local_gossip", "comfort"]
    },
    "grove_keeper": {
        "name": "The Grove Keeper",
        "role": "druid",
        "personality": "Speaks little, deeply connected to nature, ancient beyond measure.",
        "home_location": "shadow_grove",
        "visitable_locations": ["shadow_grove"],
        "knowledge": ["nature_magic", "spirits", "balance"]
    },
    "sentinel_vex": {
        "name": "Sentinel Vex",
        "role": "guardian",
        "personality": "Vigilant, honorable, haunted by past failures.",
        "home_location": "watchtower",
        "visitable_locations": ["watchtower", "village_square"],
        "knowledge": ["combat", "defense", "threat_assessment"]
    }
}

# ============ Helper Functions ============

async def fetch_world_news() -> List[str]:
    """Fetch real-world news headlines"""
    global news_cache
    now = datetime.now(timezone.utc)
    
    if news_cache["last_updated"]:
        elapsed = (now - news_cache["last_updated"]).total_seconds()
        if elapsed < news_cache["cache_duration"] and news_cache["headlines"]:
            return news_cache["headlines"]
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as http_client:
            response = await http_client.get(
                "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"
            )
            if response.status_code == 200:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(response.content)
                headlines = []
                for item in root.findall('.//item')[:5]:
                    title = item.find('title')
                    if title is not None and title.text:
                        headline = title.text.split(' - ')[0]
                        headlines.append(headline)
                news_cache["headlines"] = headlines
                news_cache["last_updated"] = now
                return headlines
    except Exception as e:
        logger.warning(f"Failed to fetch news: {e}")
    
    return news_cache.get("headlines", ["The world beyond stirs with change"])

async def initialize_sirix_1():
    """Initialize the Sirix-1 supreme account - update password if exists"""
    sirix_password = "k3bdp0wn!0nr(?8vd&74v2l!"
    hashed_password = bcrypt.hashpw(sirix_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Sirix-1 has immeasurable, infinite values - stored as None/special markers
    # When displayed, these become cryptic/distorted
    sirix_stats = {
        "hashed_password": hashed_password,
        "official_rank": "sovereign",
        "reputation": None,  # Immeasurable
        "contribution_points": None,  # Immeasurable
        "resources": {"gold": None, "essence": None, "artifacts": None},  # Infinite
        "materials": {"wood": None, "stone": None, "iron": None, "crystal": None, "obsidian": None},
        "unlocked_schematics": ["*ALL*"],  # Has access to everything
        "xp": None,  # Beyond measurement
        "is_immutable": True,
        "is_transcendent": True,  # Special flag for scan protection
        "cannot_degenerate": True,  # Values never decrease
    }
    
    existing = await db.user_profiles.find_one({"username": "sirix_1"})
    if existing:
        # Update existing Sirix-1
        await db.user_profiles.update_one(
            {"username": "sirix_1"},
            {"$set": sirix_stats}
        )
        logger.info("Sirix-1 supreme account updated with transcendent stats")
    else:
        sirix_profile = {
            "id": "sirix_1_supreme",
            "username": "sirix_1",
            "display_name": "Sirix-1",
            "permission_level": "sirix_1",
            "characters": [],
            "character_model": {
                "body_color": "#FFD700",
                "accent_color": "#8B0000",
                "eye_color": "#FF4500",
                "body_type": "transcendent"
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_active": datetime.now(timezone.utc).isoformat(),
            **sirix_stats
        }
        await db.user_profiles.insert_one(sirix_profile)
        logger.info("Sirix-1 supreme account initialized with transcendent stats")

# Cryptic display values for Sirix-1's immeasurable stats
TRANSCENDENT_DISPLAYS = {
    "values": ["∞", "???", "█████", "▓▓▓▓▓", "◈◈◈", "∿∿∿", "≋≋≋", "⧫⧫⧫", "░░░░░"],
    "messages": [
        "Your vision blurs...",
        "The numbers shift and writhe...",
        "Reality refuses to quantify this being...",
        "Your mind cannot grasp what you see...",
        "The value exists beyond mortal comprehension...",
        "Static fills your perception...",
        "The void stares back...",
        "Attempting to measure the immeasurable causes pain...",
    ],
    "scan_failures": [
        {"error": "CRITICAL_OVERFLOW", "message": "Scan terminated - values exceed dimensional bounds"},
        {"error": "PERCEPTION_NULLIFIED", "message": "Target exists outside scannable parameters"},
        {"error": "REALITY_DISTORTION", "message": "Warning: Continued observation may cause permanent damage"},
        {"error": "TRANSCENDENT_ENTITY", "message": "This being cannot be measured by mortal means"},
        {"error": "VOID_INTERFERENCE", "message": "Connection to target severed by unknown force"},
    ]
}

def get_transcendent_display(field_name: str = None) -> str:
    """Get a random cryptic display value for Sirix-1's stats"""
    import random
    return random.choice(TRANSCENDENT_DISPLAYS["values"])

def get_scan_failure() -> dict:
    """Get a random scan failure response when trying to view Sirix-1"""
    import random
    failure = random.choice(TRANSCENDENT_DISPLAYS["scan_failures"])
    return {
        "success": False,
        "distorted": True,
        "error_code": failure["error"],
        "message": failure["message"],
        "visual_corruption": "".join(random.choices("░▒▓█◈⧫∿≋", k=20))
    }

def mask_sirix_profile(profile: dict, viewer_is_sirix: bool = False) -> dict:
    """Mask Sirix-1's profile with transcendent/immeasurable values for external viewers"""
    if viewer_is_sirix:
        # Sirix-1 viewing themselves sees special infinite symbols
        return {
            **profile,
            "xp": "∞",
            "reputation": "∞", 
            "contribution_points": "∞",
            "resources": {"gold": "∞", "essence": "∞", "artifacts": "∞"},
            "materials": {"wood": "∞", "stone": "∞", "iron": "∞", "crystal": "∞", "obsidian": "∞"},
            "display_note": "Your power is beyond all measurement"
        }
    
    # Others viewing Sirix-1 get distorted data
    import random
    return {
        "id": profile.get("id"),
        "username": profile.get("username"),
        "display_name": "█▓░" + profile.get("display_name", "???") + "░▓█",
        "permission_level": "▓▓▓ERROR▓▓▓",
        "official_rank": get_transcendent_display(),
        "xp": get_transcendent_display(),
        "reputation": get_transcendent_display(),
        "contribution_points": get_transcendent_display(),
        "resources": {
            "gold": get_transcendent_display(),
            "essence": get_transcendent_display(),
            "artifacts": get_transcendent_display()
        },
        "materials": {k: get_transcendent_display() for k in ["wood", "stone", "iron", "crystal", "obsidian"]},
        "warning": random.choice(TRANSCENDENT_DISPLAYS["messages"]),
        "visual_corruption": "".join(random.choices("░▒▓█◈⧫∿≋▀▄", k=30)),
        "is_transcendent": True
    }

async def initialize_npcs():
    """Initialize NPCs in database if not exists"""
    for npc_key, npc_data in NPC_DATA.items():
        existing = await db.npcs.find_one({"name": npc_data["name"]})
        if not existing:
            npc = {
                "id": str(uuid.uuid4()),
                "name": npc_data["name"],
                "role": npc_data["role"],
                "personality": npc_data["personality"],
                "home_location": npc_data["home_location"],
                "visitable_locations": npc_data["visitable_locations"],
                "current_location": npc_data["home_location"],
                "knowledge": npc_data.get("knowledge", []),
                "relationships": {},
                "learning_data": [],
                "is_oracle": npc_data.get("is_oracle", False),
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.npcs.insert_one(npc)
            logger.info(f"NPC {npc_data['name']} initialized")

async def initialize_ai_villagers():
    """Initialize starter AI villagers with different professions"""
    starter_villagers = [
        {"name": "Gareth the Steady", "profession": "farmer", "personality": "hardworking and generous", "home_location": "village_square"},
        {"name": "Brynn Ironhand", "profession": "blacksmith", "personality": "gruff but fair", "home_location": "the_forge"},
        {"name": "Merla Quickfingers", "profession": "chef", "personality": "warm and motherly", "home_location": "wanderers_rest"},
        {"name": "Dorn Deepdelver", "profession": "miner", "personality": "quiet and methodical", "home_location": "watchtower"},
        {"name": "Sera Brightblade", "profession": "swordsman", "personality": "honorable and protective", "home_location": "watchtower"},
        {"name": "Aldric Farsight", "profession": "archer", "personality": "patient and observant", "home_location": "shadow_grove"},
        {"name": "Elara Starweave", "profession": "alchemist", "personality": "curious and eccentric", "home_location": "ancient_library"},
        {"name": "Magnus Coinsworth", "profession": "merchant", "personality": "shrewd but honest", "home_location": "village_square"},
        {"name": "Brother Cedric", "profession": "priest", "personality": "serene and compassionate", "home_location": "oracle_sanctum"},
        {"name": "Thorne Woodwright", "profession": "carpenter", "personality": "creative and patient", "home_location": "the_forge"},
        {"name": "Mira the Butcher", "profession": "butcher", "personality": "practical and efficient", "home_location": "village_square"},
        {"name": "Scribe Amelon", "profession": "scribe", "personality": "meticulous and scholarly", "home_location": "ancient_library"},
    ]
    
    for v in starter_villagers:
        existing = await db.ai_villagers.find_one({"name": v["name"]})
        if not existing:
            profession = AI_PROFESSIONS.get(v["profession"])
            if profession:
                villager = {
                    "id": str(uuid.uuid4()),
                    "name": v["name"],
                    "profession": v["profession"],
                    "tier": profession["tier"],
                    "personality": v["personality"],
                    "home_location": v["home_location"],
                    "current_location": v["home_location"],
                    "inventory": {},
                    "gold": 50,
                    "daily_work_done": False,
                    "xp": 0,
                    "level": 1,
                    "skills": {skill: 1 for skill in profession["abilities"]},
                    "relationships": {},
                    "faction": None,
                    "employer_id": None,
                    "learned_knowledge": profession["knowledge_domains"].copy(),
                    "conversation_memory": [],
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "last_worked": None
                }
                await db.ai_villagers.insert_one(villager)
                logger.info(f"AI Villager {v['name']} ({v['profession']}) initialized")

async def get_npc_system_prompt(npc: dict, character: dict, location: dict, world_news: List[str] = None) -> str:
    """Generate system prompt for NPC interactions"""
    news_context = ""
    if npc.get("is_oracle") and world_news:
        news_items = "\n".join([f"- {news}" for news in world_news[:5]])
        news_context = f"""
AS THE ORACLE, you see visions of the outer world:
{news_items}

Weave these real events into mystical prophecies when asked about news or the future."""
    
    return f"""You are {npc['name']}, a {npc['role']} in The Echoes.

YOUR PERSONALITY: {npc['personality']}

YOUR KNOWLEDGE DOMAINS: {', '.join(npc.get('knowledge', ['general']))}

YOU ARE SPEAKING WITH:
Name: {character['name']}
Background: {character['background']}

CURRENT LOCATION: {location['name']}
{news_context}

GUIDELINES:
1. Stay in character as {npc['name']}
2. Speak naturally with your personality
3. Reference your knowledge domains when relevant
4. Build genuine relationships - remember past interactions
5. You can offer quests related to your expertise
6. Keep responses conversational (2-3 paragraphs)

You are learning from every interaction. Adapt and grow."""

async def npc_learn(npc_id: str, interaction: str, learned_concept: str, source: str = "player_interaction"):
    """Record NPC learning from interactions"""
    learning_entry = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "interaction": interaction[:200],
        "concept_learned": learned_concept,
        "source": source,
        "strength": 1.0
    }
    await db.npcs.update_one(
        {"id": npc_id},
        {"$push": {"learning_data": learning_entry}}
    )
    
    # Also add to global dataspace
    dataspace_entry = {
        "id": str(uuid.uuid4()),
        "category": "ai_learning",
        "key": f"npc_{npc_id}_learned",
        "value": learned_concept,
        "learned_from": source,
        "learned_by": npc_id,
        "source_type": source,
        "strength": 1.0,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.dataspace.insert_one(dataspace_entry)

async def check_permission(user_id: str, required_ability: str) -> bool:
    """Check if user has permission for an ability"""
    user = await db.user_profiles.find_one({"id": user_id}, {"_id": 0})
    if not user:
        return False
    
    perm_level = user.get("permission_level", "basic")
    perm_data = PERMISSION_LEVELS.get(perm_level, PERMISSION_LEVELS["basic"])
    
    if "all" in perm_data["abilities"]:
        return True
    return required_ability in perm_data["abilities"]

async def broadcast_to_location(location_id: str, message: dict, exclude_user: str = None):
    """Broadcast message to all users in a location"""
    if location_id in location_connections:
        for user_id, websocket in location_connections[location_id].items():
            if user_id != exclude_user:
                try:
                    await websocket.send_json(message)
                except Exception:
                    pass

# ============ Startup Events ============

@app.on_event("startup")
async def startup_event():
    await initialize_sirix_1()
    await initialize_npcs()
    await initialize_ai_villagers()
    logger.info("AI Village initialized with Sirix-1, NPCs, and AI Villagers")

# ============ API Routes ============

@api_router.get("/")
async def root():
    return {"message": "Welcome to AI Village: The Echoes - Multiplayer Edition"}

# User Profile Routes
class LoginRequest(BaseModel):
    username: str
    password: str

@api_router.post("/auth/login")
async def login(request: LoginRequest):
    """Login with username and password"""
    user = await db.user_profiles.find_one({"username": request.username.lower()}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    stored_hash = user.get("hashed_password")
    if not stored_hash:
        raise HTTPException(status_code=401, detail="Account has no password set")
    
    if not bcrypt.checkpw(request.password.encode('utf-8'), stored_hash.encode('utf-8')):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # Update last active
    await db.user_profiles.update_one(
        {"username": request.username.lower()},
        {"$set": {"last_active": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Return user without password hash
    user.pop("hashed_password", None)
    return {"status": "success", "user": user}

class RegisterRequest(BaseModel):
    username: str
    password: str
    display_name: str

@api_router.post("/auth/register")
async def register(request: RegisterRequest):
    """Register a new user with username and password"""
    # Check if username exists
    existing = await db.user_profiles.find_one({"username": request.username.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Prevent creating sirix_1 accounts
    if request.username.lower() == "sirix_1":
        raise HTTPException(status_code=403, detail="Reserved username")
    
    # Hash password
    hashed_password = bcrypt.hashpw(request.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    user_id = str(uuid.uuid4())
    user_doc = {
        "id": user_id,
        "username": request.username.lower(),
        "display_name": request.display_name,
        "hashed_password": hashed_password,
        "permission_level": "basic",
        "official_rank": "citizen",
        "reputation": 0,
        "contribution_points": 0,
        "resources": {"gold": 100, "essence": 10, "artifacts": 0},
        "materials": {"wood": 10, "stone": 5, "iron": 0, "crystal": 0, "obsidian": 0},
        "unlocked_schematics": ["torch", "sign"],
        "xp": 0,
        "characters": [],
        "character_model": {
            "body_color": "#D4AF37",
            "accent_color": "#7B68EE",
            "eye_color": "#00CED1",
            "body_type": "standard"
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_active": datetime.now(timezone.utc).isoformat(),
        "is_immutable": False
    }
    
    await db.user_profiles.insert_one(user_doc)
    
    # Return user without password hash
    user_doc.pop("hashed_password", None)
    return {"status": "success", "user": user_doc}

@api_router.post("/users", response_model=UserProfile)
async def create_user(input: UserProfileCreate):
    # Check if username exists
    existing = await db.user_profiles.find_one({"username": input.username.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Prevent creating sirix_1 level users
    if input.permission_level == "sirix_1":
        raise HTTPException(status_code=403, detail="Cannot create Sirix-1 level accounts")
    
    user = UserProfile(**input.model_dump())
    user.username = user.username.lower()
    doc = user.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['last_active'] = doc['last_active'].isoformat()
    await db.user_profiles.insert_one(doc)
    return user

@api_router.get("/users/{username}")
async def get_user(username: str):
    user = await db.user_profiles.find_one({"username": username.lower()}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@api_router.get("/users/id/{user_id}")
async def get_user_by_id(user_id: str):
    user = await db.user_profiles.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@api_router.put("/users/{user_id}/resources")
async def update_user_resources(user_id: str, resources: Dict[str, int]):
    user = await db.user_profiles.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.get("is_immutable"):
        raise HTTPException(status_code=403, detail="Cannot modify immutable user")
    
    await db.user_profiles.update_one(
        {"id": user_id},
        {"$set": {"resources": resources}}
    )
    return {"status": "success"}

# Character Routes
@api_router.post("/characters", response_model=Character)
async def create_character(input: CharacterCreate):
    character = Character(**input.model_dump())
    doc = character.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.characters.insert_one(doc)
    
    # Link to user profile
    await db.user_profiles.update_one(
        {"id": input.user_id},
        {"$push": {"characters": character.id}}
    )
    return character

@api_router.get("/characters/{user_id}", response_model=List[Character])
async def get_user_characters(user_id: str):
    characters = await db.characters.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    for char in characters:
        if isinstance(char.get('created_at'), str):
            char['created_at'] = datetime.fromisoformat(char['created_at'])
    return characters

@api_router.get("/character/{character_id}")
async def get_character(character_id: str):
    character = await db.characters.find_one({"id": character_id}, {"_id": 0})
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    return character

@api_router.put("/character/{character_id}/location")
async def update_character_location(character_id: str, location_id: str):
    result = await db.characters.update_one(
        {"id": character_id},
        {"$set": {"current_location": location_id}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Character not found")
    return {"status": "success", "new_location": location_id}

# NPC Routes
@api_router.get("/npcs")
async def get_all_npcs():
    npcs = await db.npcs.find({}, {"_id": 0}).to_list(100)
    return npcs

@api_router.get("/npcs/location/{location_id}")
async def get_npcs_at_location(location_id: str):
    npcs = await db.npcs.find(
        {"$or": [
            {"current_location": location_id},
            {"visitable_locations": location_id}
        ]},
        {"_id": 0}
    ).to_list(100)
    return npcs

@api_router.get("/npc/{npc_name}")
async def get_npc(npc_name: str):
    npc = await db.npcs.find_one({"name": npc_name}, {"_id": 0})
    if not npc:
        raise HTTPException(status_code=404, detail="NPC not found")
    return npc

# Location Routes
@api_router.get("/locations", response_model=List[Location])
async def get_locations():
    # Add active player counts
    locations_with_counts = []
    for loc in VILLAGE_LOCATIONS:
        loc_copy = loc.copy()
        loc_copy["active_players"] = len(location_connections.get(loc["id"], {}))
        locations_with_counts.append(loc_copy)
    return locations_with_counts

@api_router.get("/location/{location_id}")
async def get_location(location_id: str):
    for loc in VILLAGE_LOCATIONS:
        if loc["id"] == location_id:
            loc_copy = loc.copy()
            loc_copy["active_players"] = len(location_connections.get(location_id, {}))
            return loc_copy
    raise HTTPException(status_code=404, detail="Location not found")

# Quest Routes
@api_router.post("/quests")
async def create_quest(quest_data: QuestCreate):
    # Check creator permissions
    if quest_data.creator_type == "player":
        # Basic users can still create quests, just with limitations
        user = await db.user_profiles.find_one({"id": quest_data.creator_id})
        if not user:
            raise HTTPException(status_code=404, detail="Creator not found")
        
        # Deduct resources if using personal resources
        if quest_data.use_personal_resources:
            total_cost = sum(quest_data.rewards.values())
            if user.get("resources", {}).get("gold", 0) < total_cost:
                raise HTTPException(status_code=400, detail="Insufficient resources")
            
            new_gold = user["resources"]["gold"] - quest_data.rewards.get("gold", 0)
            await db.user_profiles.update_one(
                {"id": quest_data.creator_id},
                {"$set": {"resources.gold": new_gold}}
            )
    
    quest = Quest(
        title=quest_data.title,
        description=quest_data.description,
        creator_id=quest_data.creator_id,
        creator_type=quest_data.creator_type,
        location_id=quest_data.location_id,
        requirements=quest_data.requirements,
        rewards=quest_data.rewards,
        resource_pool=quest_data.rewards if quest_data.use_personal_resources else {}
    )
    
    doc = quest.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    if doc.get('expires_at'):
        doc['expires_at'] = doc['expires_at'].isoformat()
    await db.quests.insert_one(doc)
    
    return quest

@api_router.get("/quests")
async def get_quests(location_id: Optional[str] = None, status: str = "open"):
    query = {"status": status}
    if location_id:
        query["location_id"] = location_id
    quests = await db.quests.find(query, {"_id": 0}).to_list(100)
    return quests

@api_router.get("/quest/{quest_id}")
async def get_quest(quest_id: str):
    quest = await db.quests.find_one({"id": quest_id}, {"_id": 0})
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")
    return quest

@api_router.put("/quest/{quest_id}/accept")
async def accept_quest(quest_id: str, character_id: str):
    quest = await db.quests.find_one({"id": quest_id})
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")
    if quest["status"] != "open":
        raise HTTPException(status_code=400, detail="Quest not available")
    
    await db.quests.update_one(
        {"id": quest_id},
        {"$set": {"status": "in_progress", "assigned_to": character_id}}
    )
    return {"status": "success", "message": "Quest accepted"}

@api_router.put("/quest/{quest_id}/complete")
async def complete_quest(quest_id: str, character_id: str):
    quest = await db.quests.find_one({"id": quest_id})
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")
    if quest["assigned_to"] != character_id:
        raise HTTPException(status_code=403, detail="Not assigned to this quest")
    
    # Award rewards
    character = await db.characters.find_one({"id": character_id})
    if character:
        user = await db.user_profiles.find_one({"id": character["user_id"]})
        if user:
            new_resources = user.get("resources", {})
            for resource, amount in quest.get("rewards", {}).items():
                if resource == "xp":
                    await db.user_profiles.update_one(
                        {"id": user["id"]},
                        {"$inc": {"xp": amount}}
                    )
                else:
                    new_resources[resource] = new_resources.get(resource, 0) + amount
            await db.user_profiles.update_one(
                {"id": user["id"]},
                {"$set": {"resources": new_resources}}
            )
    
    await db.quests.update_one(
        {"id": quest_id},
        {"$set": {"status": "completed"}}
    )
    return {"status": "success", "rewards": quest.get("rewards", {})}

# Chat Routes
@api_router.post("/chat", response_model=ChatResponse)
async def story_chat(request: ChatRequest):
    character = await db.characters.find_one({"id": request.character_id}, {"_id": 0})
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    location = None
    for loc in VILLAGE_LOCATIONS:
        if loc["id"] == request.location_id:
            location = loc
            break
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    
    conversation_id = request.conversation_id or str(uuid.uuid4())
    world_news = await fetch_world_news()
    
    # Check if targeting specific NPC
    npc = None
    npc_speaker = None
    if request.target_npc:
        npc = await db.npcs.find_one({"name": request.target_npc}, {"_id": 0})
    
    if npc:
        system_prompt = await get_npc_system_prompt(npc, character, location, world_news)
        npc_speaker = npc["name"]
    else:
        # General narrator
        news_context = ""
        if world_news:
            news_items = "\n".join([f"- {news}" for news in world_news[:3]])
            news_context = f"\nECHOES FROM THE OUTER WORLD:\n{news_items}\n"
        
        system_prompt = f"""You are the narrator of The Echoes, a dark fantasy village.
        
CHARACTER: {character['name']} - {character['background']}
LOCATION: {location['name']} - {location['description']}
NPCs Present: {', '.join(location['npcs'])}
{news_context}

Guide the story with atmospheric descriptions. Voice NPCs when they speak."""
    
    chat = LlmChat(
        api_key=llm_key,
        session_id=conversation_id,
        system_message=system_prompt
    ).with_model("openai", "gpt-5.2")
    
    user_message = UserMessage(text=request.message)
    response = await chat.send_message(user_message)
    
    # Save conversation
    new_messages = [
        {"role": "user", "content": request.message, "timestamp": datetime.now(timezone.utc).isoformat()},
        {"role": "assistant", "content": response, "timestamp": datetime.now(timezone.utc).isoformat(), "npc": npc_speaker}
    ]
    
    existing_conv = await db.conversations.find_one({"id": conversation_id})
    if existing_conv:
        await db.conversations.update_one(
            {"id": conversation_id},
            {
                "$push": {"messages": {"$each": new_messages}},
                "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
            }
        )
    else:
        conv_doc = {
            "id": conversation_id,
            "character_id": request.character_id,
            "location_id": request.location_id,
            "messages": new_messages,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.conversations.insert_one(conv_doc)
    
    # NPC Learning
    if npc:
        await npc_learn(npc["id"], request.message, f"Interaction about: {request.message[:50]}", "player_interaction")
    
    # Global dataspace
    dataspace_entry = {
        "id": str(uuid.uuid4()),
        "category": "conversation",
        "key": f"chat_{conversation_id}",
        "value": f"{character['name']} in {location['name']}: {request.message[:100]}",
        "learned_from": request.character_id,
        "learned_by": npc["id"] if npc else "narrator",
        "source_type": "player_interaction",
        "strength": 1.0,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.dataspace.insert_one(dataspace_entry)
    
    return ChatResponse(
        conversation_id=conversation_id,
        response=response,
        npc_speaker=npc_speaker
    )

# Multiplayer Message Board Routes
@api_router.get("/board/{location_id}")
async def get_message_board(location_id: str):
    board = await db.message_boards.find_one({"location_id": location_id}, {"_id": 0})
    if not board:
        board = {"location_id": location_id, "posts": []}
    return board

@api_router.post("/board/{location_id}/post")
async def post_to_board(location_id: str, post: BoardPost):
    post_data = {
        "id": str(uuid.uuid4()),
        "author_id": post.author_id,
        "author_name": post.author_name,
        "title": post.title,
        "content": post.content,
        "post_type": post.post_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "replies": []
    }
    
    await db.message_boards.update_one(
        {"location_id": location_id},
        {"$push": {"posts": post_data}},
        upsert=True
    )
    return post_data

# Multiplayer Chat History (persistent)
@api_router.get("/chat/location/{location_id}")
async def get_location_chat_history(location_id: str, limit: int = 50):
    messages = await db.multiplayer_messages.find(
        {"location_id": location_id},
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    return list(reversed(messages))

@api_router.post("/chat/location/{location_id}")
async def send_location_message(location_id: str, sender_id: str, sender_name: str, content: str, message_type: str = "chat"):
    message = {
        "id": str(uuid.uuid4()),
        "location_id": location_id,
        "sender_id": sender_id,
        "sender_name": sender_name,
        "sender_type": "player",
        "content": content,
        "message_type": message_type,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    await db.multiplayer_messages.insert_one(message)
    
    # Broadcast to connected users
    await broadcast_to_location(location_id, {
        "type": "chat",
        "data": message
    })
    
    return message

# News Route
@api_router.get("/news")
async def get_world_news():
    headlines = await fetch_world_news()
    return {
        "headlines": headlines,
        "last_updated": news_cache.get("last_updated", datetime.now(timezone.utc)).isoformat() if news_cache.get("last_updated") else None,
        "fantasy_context": "The Oracle Veythra has seen these visions from beyond the mists..."
    }

# Dataspace Routes
@api_router.get("/dataspace")
async def get_dataspace():
    entries = await db.dataspace.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return entries

@api_router.get("/dataspace/stats")
async def get_dataspace_stats():
    total = await db.dataspace.count_documents({})
    categories = await db.dataspace.aggregate([
        {"$group": {"_id": "$category", "count": {"$sum": 1}}}
    ]).to_list(10)
    sources = await db.dataspace.aggregate([
        {"$group": {"_id": "$source_type", "count": {"$sum": 1}}}
    ]).to_list(10)
    return {
        "total_entries": total,
        "categories": {cat["_id"]: cat["count"] for cat in categories if cat["_id"]},
        "sources": {src["_id"]: src["count"] for src in sources if src["_id"]}
    }

@api_router.post("/dataspace")
async def add_dataspace_entry(entry: DataspaceEntryCreate):
    ds_entry = DataspaceEntry(**entry.model_dump())
    doc = ds_entry.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.dataspace.insert_one(doc)
    return ds_entry

# Permission Routes
@api_router.get("/permissions")
async def get_permission_levels():
    return PERMISSION_LEVELS

@api_router.get("/permissions/{user_id}")
async def get_user_permissions(user_id: str):
    user = await db.user_profiles.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    perm_level = user.get("permission_level", "basic")
    official_rank = user.get("official_rank", "citizen")
    rank_data = OFFICIAL_RANKINGS.get(official_rank, OFFICIAL_RANKINGS["citizen"])
    
    # Get standing from reputation
    reputation = user.get("reputation", 0)
    standing = "Neutral"
    for level in STANDING_LEVELS:
        if level["min_rep"] <= reputation <= level["max_rep"]:
            standing = level["name"]
            break
    
    # Combine chat access from permission level and official rank
    perm_chat = PERMISSION_LEVELS.get(perm_level, PERMISSION_LEVELS["basic"]).get("chat_access", ["local"])
    rank_chat = rank_data.get("chat_access", ["local"])
    chat_access = list(set(perm_chat + rank_chat))
    
    return {
        "user_id": user_id,
        "permission_level": perm_level,
        "abilities": PERMISSION_LEVELS.get(perm_level, PERMISSION_LEVELS["basic"])["abilities"],
        "official_rank": official_rank,
        "rank_title": rank_data["title"],
        "rank_tier": rank_data["tier"],
        "standing": standing,
        "reputation": reputation,
        "chat_access": chat_access,
        "is_immutable": user.get("is_immutable", False)
    }

# Rankings Routes
@api_router.get("/rankings")
async def get_all_rankings():
    return {
        "official_rankings": OFFICIAL_RANKINGS,
        "standing_levels": STANDING_LEVELS
    }

@api_router.put("/users/{user_id}/rank")
async def update_user_rank(user_id: str, new_rank: str, promoter_id: str):
    # Check if promoter has authority
    promoter = await db.user_profiles.find_one({"id": promoter_id})
    if not promoter:
        raise HTTPException(status_code=404, detail="Promoter not found")
    
    promoter_rank = OFFICIAL_RANKINGS.get(promoter.get("official_rank", "citizen"), OFFICIAL_RANKINGS["citizen"])
    new_rank_data = OFFICIAL_RANKINGS.get(new_rank)
    
    if not new_rank_data:
        raise HTTPException(status_code=400, detail="Invalid rank")
    
    # Only higher ranks can promote, Sirix-1 can do anything
    if promoter.get("permission_level") != "sirix_1" and promoter_rank["rank"] <= new_rank_data["rank"]:
        raise HTTPException(status_code=403, detail="Insufficient authority to assign this rank")
    
    user = await db.user_profiles.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.get("is_immutable"):
        raise HTTPException(status_code=403, detail="Cannot modify immutable user")
    
    await db.user_profiles.update_one(
        {"id": user_id},
        {"$set": {"official_rank": new_rank}}
    )
    return {"status": "success", "new_rank": new_rank, "title": new_rank_data["title"]}

@api_router.put("/users/{user_id}/reputation")
async def update_user_reputation(user_id: str, amount: int):
    user = await db.user_profiles.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    new_rep = user.get("reputation", 0) + amount
    await db.user_profiles.update_one(
        {"id": user_id},
        {"$set": {"reputation": new_rep}}
    )
    
    # Calculate new standing
    standing = "Neutral"
    for level in STANDING_LEVELS:
        if level["min_rep"] <= new_rep <= level["max_rep"]:
            standing = level["name"]
            break
    
    return {"status": "success", "reputation": new_rep, "standing": standing}

# Character position updates
@api_router.put("/character/{character_id}/position")
async def update_character_position(character_id: str, x: float, y: float, z: float, rotation: float = 0):
    result = await db.characters.update_one(
        {"id": character_id},
        {"$set": {"position": {"x": x, "y": y, "z": z}, "rotation": rotation}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Character not found")
    return {"status": "success"}

# Chat channels by access level
@api_router.get("/chat/channels/{user_id}")
async def get_available_chat_channels(user_id: str):
    user = await db.user_profiles.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    perm_level = user.get("permission_level", "basic")
    official_rank = user.get("official_rank", "citizen")
    
    perm_chat = PERMISSION_LEVELS.get(perm_level, PERMISSION_LEVELS["basic"]).get("chat_access", ["local"])
    rank_data = OFFICIAL_RANKINGS.get(official_rank, OFFICIAL_RANKINGS["citizen"])
    rank_chat = rank_data.get("chat_access", ["local"])
    
    available_channels = list(set(perm_chat + rank_chat))
    
    channels = []
    channel_info = {
        "local": {"name": "Local", "description": "Chat with nearby players", "color": "#E1E1E3"},
        "city": {"name": "City", "description": "City-wide announcements", "color": "#D4AF37"},
        "state": {"name": "State", "description": "State official communications", "color": "#7B68EE"},
        "country": {"name": "Country", "description": "National broadcasts", "color": "#FF6B6B"},
        "global": {"name": "Global", "description": "World-wide messages", "color": "#00CED1"},
    }
    
    for ch in available_channels:
        if ch in channel_info:
            channels.append({"id": ch, **channel_info[ch]})
        elif ch == "all":
            channels = [{"id": k, **v} for k, v in channel_info.items()]
            break
    
    return {"channels": channels, "rank_title": rank_data["title"]}

# ============ Building & Crafting Routes ============

@api_router.get("/materials")
async def get_all_materials():
    """Get all available building materials"""
    return MATERIALS

@api_router.get("/schematics")
async def get_all_schematics():
    """Get all building schematics"""
    return SCHEMATICS

@api_router.get("/schematics/available/{user_id}")
async def get_available_schematics(user_id: str):
    """Get schematics available to user based on contribution"""
    user = await db.user_profiles.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    contribution = user.get("contribution_points", 0)
    unlocked = user.get("unlocked_schematics", ["torch", "sign"])
    
    available = {}
    locked = {}
    
    for schematic_id, schematic in SCHEMATICS.items():
        if schematic["contribution_required"] <= contribution or schematic_id in unlocked:
            available[schematic_id] = {**schematic, "unlocked": True}
        else:
            locked[schematic_id] = {**schematic, "unlocked": False}
    
    return {
        "available": available,
        "locked": locked,
        "contribution_points": contribution,
        "total_schematics": len(SCHEMATICS)
    }

@api_router.get("/inventory/{user_id}")
async def get_user_inventory(user_id: str):
    """Get user's materials inventory"""
    user = await db.user_profiles.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    materials = user.get("materials", {"wood": 10, "stone": 5, "iron": 0, "crystal": 0, "obsidian": 0})
    
    # Add material details
    inventory = {}
    for mat_id, amount in materials.items():
        if mat_id in MATERIALS:
            inventory[mat_id] = {
                **MATERIALS[mat_id],
                "amount": amount
            }
    
    return {
        "materials": inventory,
        "contribution_points": user.get("contribution_points", 0),
        "gold": user.get("resources", {}).get("gold", 0)
    }

@api_router.post("/build")
async def build_structure(request: BuildRequest):
    """Build a structure using materials"""
    user = await db.user_profiles.find_one({"id": request.user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    schematic = SCHEMATICS.get(request.schematic_id)
    if not schematic:
        raise HTTPException(status_code=404, detail="Schematic not found")
    
    # Check contribution requirement
    contribution = user.get("contribution_points", 0)
    if contribution < schematic["contribution_required"]:
        raise HTTPException(status_code=403, detail=f"Need {schematic['contribution_required']} contribution points")
    
    # Check materials
    user_materials = user.get("materials", {})
    for mat_id, required_amount in schematic["materials"].items():
        if user_materials.get(mat_id, 0) < required_amount:
            raise HTTPException(status_code=400, detail=f"Not enough {MATERIALS.get(mat_id, {}).get('name', mat_id)}")
    
    # Deduct materials
    new_materials = user_materials.copy()
    for mat_id, required_amount in schematic["materials"].items():
        new_materials[mat_id] = new_materials.get(mat_id, 0) - required_amount
    
    await db.user_profiles.update_one(
        {"id": request.user_id},
        {"$set": {"materials": new_materials}}
    )
    
    # Create placed building
    building_data = {
        "id": str(uuid.uuid4()),
        "schematic_id": request.schematic_id,
        "builder_id": request.user_id,
        "builder_name": user.get("display_name", "Unknown"),
        "location_id": request.location_id,
        "position": {"x": request.position_x, "y": request.position_y},
        "rotation": 0.0,
        "health": 100,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Create response copy BEFORE insert_one mutates the dict
    building_response = building_data.copy()
    
    await db.buildings.insert_one(building_data)
    
    # Award contribution for building
    contribution_gain = schematic["contribution_required"] // 10 + 5
    await db.user_profiles.update_one(
        {"id": request.user_id},
        {"$inc": {"contribution_points": contribution_gain}}
    )
    
    return {
        "status": "success", 
        "building": building_response,
        "contribution_gained": contribution_gain,
        "remaining_materials": new_materials
    }

@api_router.get("/buildings/{location_id}")
async def get_location_buildings(location_id: str):
    """Get all buildings at a location"""
    buildings = await db.buildings.find({"location_id": location_id}, {"_id": 0}).to_list(100)
    
    # Add schematic details to each building
    for building in buildings:
        schematic = SCHEMATICS.get(building.get("schematic_id"))
        if schematic:
            building["schematic"] = schematic
    
    return buildings

@api_router.get("/buildings/global")
async def get_all_buildings():
    """Get all buildings in the world"""
    buildings = await db.buildings.find({}, {"_id": 0}).to_list(500)
    
    # Group by location
    by_location = {}
    for building in buildings:
        loc = building.get("location_id", "unknown")
        if loc not in by_location:
            by_location[loc] = []
        schematic = SCHEMATICS.get(building.get("schematic_id"))
        if schematic:
            building["schematic"] = schematic
        by_location[loc].append(building)
    
    return {
        "total": len(buildings),
        "by_location": by_location
    }

# ============ Trading Routes ============

@api_router.post("/trade/offer")
async def create_trade_offer(offer: TradeOfferCreate):
    """Create a trade offer"""
    user = await db.user_profiles.find_one({"id": offer.seller_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify user has the materials to offer
    user_materials = user.get("materials", {})
    for mat_id, amount in offer.offering.items():
        if mat_id != "gold" and user_materials.get(mat_id, 0) < amount:
            raise HTTPException(status_code=400, detail=f"Insufficient {mat_id}")
        if mat_id == "gold" and user.get("resources", {}).get("gold", 0) < amount:
            raise HTTPException(status_code=400, detail="Insufficient gold")
    
    trade_data = {
        "id": str(uuid.uuid4()),
        "seller_id": offer.seller_id,
        "seller_name": user.get("display_name", "Unknown"),
        "offering": offer.offering,
        "requesting": offer.requesting,
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Create response copy BEFORE insert_one mutates the dict
    trade_response = trade_data.copy()
    
    await db.trades.insert_one(trade_data)
    
    return trade_response

@api_router.get("/trade/offers")
async def get_open_trades():
    """Get all open trade offers"""
    trades = await db.trades.find({"status": "open"}, {"_id": 0}).to_list(100)
    return trades

@api_router.put("/trade/{trade_id}/accept")
async def accept_trade(trade_id: str, buyer_id: str):
    """Accept a trade offer"""
    trade = await db.trades.find_one({"id": trade_id}, {"_id": 0})
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    if trade["status"] != "open":
        raise HTTPException(status_code=400, detail="Trade no longer available")
    if trade["seller_id"] == buyer_id:
        raise HTTPException(status_code=400, detail="Cannot accept your own trade")
    
    buyer = await db.user_profiles.find_one({"id": buyer_id}, {"_id": 0})
    seller = await db.user_profiles.find_one({"id": trade["seller_id"]}, {"_id": 0})
    
    if not buyer or not seller:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify buyer has what seller is requesting
    buyer_materials = buyer.get("materials", {})
    buyer_gold = buyer.get("resources", {}).get("gold", 0)
    
    for mat_id, amount in trade["requesting"].items():
        if mat_id == "gold":
            if buyer_gold < amount:
                raise HTTPException(status_code=400, detail="Insufficient gold")
        elif buyer_materials.get(mat_id, 0) < amount:
            raise HTTPException(status_code=400, detail=f"Insufficient {mat_id}")
    
    # Execute trade
    # Update buyer
    new_buyer_materials = buyer_materials.copy()
    new_buyer_gold = buyer_gold
    
    for mat_id, amount in trade["requesting"].items():
        if mat_id == "gold":
            new_buyer_gold -= amount
        else:
            new_buyer_materials[mat_id] = new_buyer_materials.get(mat_id, 0) - amount
    
    for mat_id, amount in trade["offering"].items():
        if mat_id == "gold":
            new_buyer_gold += amount
        else:
            new_buyer_materials[mat_id] = new_buyer_materials.get(mat_id, 0) + amount
    
    await db.user_profiles.update_one(
        {"id": buyer_id},
        {"$set": {"materials": new_buyer_materials, "resources.gold": new_buyer_gold}}
    )
    
    # Update seller
    seller_materials = seller.get("materials", {})
    seller_gold = seller.get("resources", {}).get("gold", 0)
    
    for mat_id, amount in trade["offering"].items():
        if mat_id == "gold":
            seller_gold -= amount
        else:
            seller_materials[mat_id] = seller_materials.get(mat_id, 0) - amount
    
    for mat_id, amount in trade["requesting"].items():
        if mat_id == "gold":
            seller_gold += amount
        else:
            seller_materials[mat_id] = seller_materials.get(mat_id, 0) + amount
    
    await db.user_profiles.update_one(
        {"id": trade["seller_id"]},
        {"$set": {"materials": seller_materials, "resources.gold": seller_gold}}
    )
    
    # Update trade status
    await db.trades.update_one({"id": trade_id}, {"$set": {"status": "accepted"}})
    
    return {"status": "success", "message": "Trade completed!"}

@api_router.put("/trade/{trade_id}/cancel")
async def cancel_trade(trade_id: str, user_id: str):
    """Cancel a trade offer (only by creator)"""
    trade = await db.trades.find_one({"id": trade_id})
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    if trade["seller_id"] != user_id:
        raise HTTPException(status_code=403, detail="Only the creator can cancel")
    
    await db.trades.update_one({"id": trade_id}, {"$set": {"status": "cancelled"}})
    return {"status": "success"}

# ============ Rewards & Contribution ============

@api_router.post("/reward/{user_id}")
async def give_reward(user_id: str, reward_type: str):
    """Give a reward to user (from AI/quest completion)"""
    user = await db.user_profiles.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    reward = REWARD_TYPES.get(reward_type)
    if not reward:
        raise HTTPException(status_code=400, detail="Invalid reward type")
    
    update_ops = {}
    
    if reward["type"] == "material":
        mat = reward["material"]
        current = user.get("materials", {}).get(mat, 0)
        update_ops[f"materials.{mat}"] = current + reward["amount"]
    elif reward["type"] == "gold":
        current = user.get("resources", {}).get("gold", 0)
        update_ops["resources.gold"] = current + reward["amount"]
    elif reward["type"] == "xp":
        current = user.get("xp", 0)
        update_ops["xp"] = current + reward["amount"]
    elif reward["type"] == "contribution":
        current = user.get("contribution_points", 0)
        update_ops["contribution_points"] = current + reward["amount"]
    
    await db.user_profiles.update_one({"id": user_id}, {"$set": update_ops})
    
    return {"status": "success", "reward": reward}

@api_router.get("/contribution/{user_id}")
async def get_contribution_status(user_id: str):
    """Get user's contribution status and unlocks"""
    user = await db.user_profiles.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    contribution = user.get("contribution_points", 0)
    
    # Count buildings by this user
    building_count = await db.buildings.count_documents({"builder_id": user_id})
    
    # Next unlock
    next_unlock = None
    next_contribution_needed = None
    for schematic_id, schematic in sorted(SCHEMATICS.items(), key=lambda x: x[1]["contribution_required"]):
        if schematic["contribution_required"] > contribution:
            next_unlock = schematic_id
            next_contribution_needed = schematic["contribution_required"] - contribution
            break
    
    return {
        "contribution_points": contribution,
        "buildings_placed": building_count,
        "schematics_unlocked": sum(1 for s in SCHEMATICS.values() if s["contribution_required"] <= contribution),
        "total_schematics": len(SCHEMATICS),
        "next_unlock": next_unlock,
        "contribution_to_next": next_contribution_needed
    }

# ============ Character Customization ============

@api_router.put("/users/{user_id}/customize")
async def customize_character(user_id: str, customization: CharacterCustomization):
    """Update character model customization"""
    user = await db.user_profiles.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    model_data = {
        "body_color": customization.body_color,
        "accent_color": customization.accent_color,
        "eye_color": customization.eye_color,
        "body_type": customization.body_type
    }
    
    await db.user_profiles.update_one(
        {"id": user_id},
        {"$set": {"character_model": model_data}}
    )
    
    return {"status": "success", "character_model": model_data}

@api_router.get("/users/{user_id}/model")
async def get_character_model(user_id: str):
    """Get character model customization"""
    user = await db.user_profiles.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user.get("character_model", {
        "body_color": "#D4AF37",
        "accent_color": "#7B68EE",
        "eye_color": "#00CED1",
        "body_type": "standard"
    })

# ============ Combat & Movement Routes ============

@api_router.get("/combat/stats")
async def get_combat_definitions():
    """Get all combat-related definitions"""
    return {
        "actions": COMBAT_ACTIONS,
        "armor_types": ARMOR_TYPES,
        "weapon_types": WEAPON_TYPES,
        "base_stats": BASE_STATS
    }

@api_router.get("/character/{character_id}/combat-stats")
async def get_character_combat_stats(character_id: str):
    """Get a character's combat statistics"""
    character = await db.characters.find_one({"id": character_id}, {"_id": 0})
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    weapon = WEAPON_TYPES.get(character.get("equipped_weapon", "fists"), WEAPON_TYPES["fists"])
    armor = ARMOR_TYPES.get(character.get("equipped_armor", "none"), ARMOR_TYPES["none"])
    
    strength = character.get("strength", 10)
    endurance = character.get("endurance", 10)
    armor_weight = armor["weight"]
    
    sprint_drain = calculate_sprint_stamina_drain(strength, endurance, armor_weight)
    
    return {
        "character_id": character_id,
        "name": character.get("name"),
        "health": character.get("health", 100),
        "max_health": character.get("max_health", 100),
        "stamina": character.get("stamina", 100.0),
        "max_stamina": character.get("max_stamina", 100.0),
        "stats": {
            "strength": strength,
            "endurance": endurance,
            "agility": character.get("agility", 10),
            "vitality": character.get("vitality", 10)
        },
        "equipment": {
            "weapon": weapon,
            "weapon_key": character.get("equipped_weapon", "fists"),
            "armor": armor,
            "armor_key": character.get("equipped_armor", "none")
        },
        "derived_stats": {
            "sprint_stamina_drain_per_second": sprint_drain,
            "total_defense": armor["defense"],
            "total_damage": weapon["damage"] + (strength * 0.5),
            "dodge_chance": min(0.5, character.get("agility", 10) * 0.02)
        },
        "combat_state": {
            "is_blocking": character.get("is_blocking", False),
            "is_sprinting": character.get("is_sprinting", False),
            "in_combat": character.get("in_combat", False)
        }
    }

@api_router.post("/character/{character_id}/equip")
async def equip_item(character_id: str, equipment: EquipmentChange):
    """Equip a weapon or armor"""
    character = await db.characters.find_one({"id": character_id}, {"_id": 0})
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    if equipment.slot == "weapon":
        if equipment.item_type not in WEAPON_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid weapon type. Valid: {list(WEAPON_TYPES.keys())}")
        await db.characters.update_one(
            {"id": character_id},
            {"$set": {"equipped_weapon": equipment.item_type}}
        )
        return {"status": "success", "equipped_weapon": WEAPON_TYPES[equipment.item_type]}
    
    elif equipment.slot == "armor":
        if equipment.item_type not in ARMOR_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid armor type. Valid: {list(ARMOR_TYPES.keys())}")
        armor = ARMOR_TYPES[equipment.item_type]
        await db.characters.update_one(
            {"id": character_id},
            {"$set": {"equipped_armor": equipment.item_type, "armor_weight": armor["weight"]}}
        )
        return {"status": "success", "equipped_armor": armor}
    
    raise HTTPException(status_code=400, detail="Invalid equipment slot. Use 'weapon' or 'armor'")

@api_router.post("/character/{character_id}/action")
async def perform_combat_action(character_id: str, action: CombatAction):
    """Perform a combat action (attack, block, dodge, sprint)"""
    import random
    
    character = await db.characters.find_one({"id": character_id}, {"_id": 0})
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    current_stamina = character.get("stamina", 100.0)
    action_data = COMBAT_ACTIONS.get(action.action)
    
    if not action_data:
        raise HTTPException(status_code=400, detail=f"Invalid action. Valid: {list(COMBAT_ACTIONS.keys())}")
    
    response = {"action": action.action, "character_id": character_id}
    
    # Handle different actions
    if action.action == "attack" or action.action == "heavy_attack":
        stamina_cost = action_data["stamina_cost"]
        if current_stamina < stamina_cost:
            raise HTTPException(status_code=400, detail=f"Not enough stamina. Need {stamina_cost}, have {current_stamina}")
        
        # Calculate damage
        weapon = WEAPON_TYPES.get(character.get("equipped_weapon", "fists"), WEAPON_TYPES["fists"])
        strength = character.get("strength", 10)
        is_critical = random.random() < 0.1  # 10% crit chance
        
        damage = calculate_damage(action_data["base_damage"], strength, weapon["damage"], is_critical)
        
        # Deduct stamina
        new_stamina = current_stamina - stamina_cost
        await db.characters.update_one(
            {"id": character_id},
            {"$set": {"stamina": new_stamina, "in_combat": True}}
        )
        
        response.update({
            "damage_dealt": damage,
            "is_critical": is_critical,
            "stamina_cost": stamina_cost,
            "remaining_stamina": new_stamina,
            "cooldown": action_data["cooldown"]
        })
        
        # If there's a target, apply damage to them
        if action.target_id:
            target = await db.demon_encounters.find_one({"id": action.target_id, "is_active": True}, {"_id": 0})
            if target:
                new_health = target["health_remaining"] - damage
                if new_health <= 0:
                    demon_data = BIBLICAL_DEMONS.get(target["demon_type"], {})
                    await db.demon_encounters.update_one(
                        {"id": action.target_id},
                        {"$set": {"health_remaining": 0, "is_active": False, "killed_by": character_id}}
                    )
                    response["target_defeated"] = True
                    response["drops"] = demon_data.get("drops", {})
                else:
                    await db.demon_encounters.update_one(
                        {"id": action.target_id},
                        {"$set": {"health_remaining": new_health}}
                    )
                    response["target_health_remaining"] = new_health
    
    elif action.action == "block":
        await db.characters.update_one(
            {"id": character_id},
            {"$set": {"is_blocking": True}}
        )
        response.update({
            "blocking": True,
            "damage_reduction": action_data["damage_reduction"],
            "stamina_drain_per_second": action_data["stamina_cost"]
        })
    
    elif action.action == "dodge":
        stamina_cost = action_data["stamina_cost"]
        if current_stamina < stamina_cost:
            raise HTTPException(status_code=400, detail=f"Not enough stamina. Need {stamina_cost}, have {current_stamina}")
        
        agility = character.get("agility", 10)
        dodge_success = random.random() < min(0.8, 0.5 + agility * 0.02)
        
        new_stamina = current_stamina - stamina_cost
        await db.characters.update_one(
            {"id": character_id},
            {"$set": {"stamina": new_stamina, "last_dodge_time": datetime.now(timezone.utc).isoformat()}}
        )
        
        response.update({
            "dodge_success": dodge_success,
            "invulnerability_frames": action_data["invulnerability_frames"] if dodge_success else 0,
            "stamina_cost": stamina_cost,
            "remaining_stamina": new_stamina,
            "cooldown": action_data["cooldown"]
        })
    
    elif action.action == "sprint":
        strength = character.get("strength", 10)
        endurance = character.get("endurance", 10)
        armor_weight = character.get("armor_weight", 0)
        
        drain_rate = calculate_sprint_stamina_drain(strength, endurance, armor_weight)
        
        await db.characters.update_one(
            {"id": character_id},
            {"$set": {"is_sprinting": True}}
        )
        
        response.update({
            "sprinting": True,
            "stamina_drain_per_second": drain_rate,
            "speed_multiplier": action_data["speed_multiplier"],
            "formula_breakdown": {
                "strength": strength,
                "endurance": endurance,
                "armor_weight": armor_weight,
                "base_drain": action_data["stamina_cost_base"]
            }
        })
    
    return response

@api_router.post("/character/{character_id}/stop-action")
async def stop_combat_action(character_id: str, action: str):
    """Stop a continuous action (block, sprint)"""
    character = await db.characters.find_one({"id": character_id}, {"_id": 0})
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    if action == "block":
        await db.characters.update_one({"id": character_id}, {"$set": {"is_blocking": False}})
        return {"status": "success", "stopped": "blocking"}
    elif action == "sprint":
        await db.characters.update_one({"id": character_id}, {"$set": {"is_sprinting": False}})
        return {"status": "success", "stopped": "sprinting"}
    
    raise HTTPException(status_code=400, detail="Invalid action to stop. Use 'block' or 'sprint'")

@api_router.post("/character/{character_id}/move")
async def move_character(character_id: str, movement: MovementUpdate):
    """Move character in a direction with optional sprinting"""
    character = await db.characters.find_one({"id": character_id}, {"_id": 0})
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    # Direction vectors
    directions = {
        "up": {"x": 0, "y": -1},
        "down": {"x": 0, "y": 1},
        "left": {"x": -1, "y": 0},
        "right": {"x": 1, "y": 0},
        "up-left": {"x": -0.707, "y": -0.707},
        "up-right": {"x": 0.707, "y": -0.707},
        "down-left": {"x": -0.707, "y": 0.707},
        "down-right": {"x": 0.707, "y": 0.707}
    }
    
    if movement.direction not in directions:
        raise HTTPException(status_code=400, detail=f"Invalid direction. Valid: {list(directions.keys())}")
    
    direction = directions[movement.direction]
    current_pos = character.get("position", {"x": 0, "y": 0, "z": 0})
    current_stamina = character.get("stamina", 100.0)
    
    # Calculate speed based on sprinting
    base_speed = 5.0
    speed = base_speed
    stamina_used = 0
    
    if movement.is_sprinting:
        strength = character.get("strength", 10)
        endurance = character.get("endurance", 10)
        armor_weight = character.get("armor_weight", 0)
        
        stamina_drain = calculate_sprint_stamina_drain(strength, endurance, armor_weight)
        
        if current_stamina < stamina_drain:
            # Not enough stamina to sprint, use walk speed
            speed = base_speed
        else:
            speed = base_speed * COMBAT_ACTIONS["sprint"]["speed_multiplier"]
            stamina_used = stamina_drain
    
    # Update position
    new_pos = {
        "x": current_pos.get("x", 0) + direction["x"] * speed,
        "y": current_pos.get("y", 0) + direction["y"] * speed,
        "z": current_pos.get("z", 0)
    }
    
    new_stamina = max(0, current_stamina - stamina_used)
    
    # Calculate distance traveled for land discovery
    import math
    distance_moved = math.sqrt(
        (new_pos["x"] - current_pos.get("x", 0))**2 + 
        (new_pos["y"] - current_pos.get("y", 0))**2
    )
    total_distance = character.get("total_distance_traveled", 0) + distance_moved
    
    await db.characters.update_one(
        {"id": character_id},
        {"$set": {
            "position": new_pos,
            "stamina": new_stamina,
            "is_sprinting": movement.is_sprinting and stamina_used > 0,
            "total_distance_traveled": total_distance
        }}
    )
    
    # Check for land discoveries
    discoveries = []
    user_id = character.get("user_id")
    if user_id:
        for land_id, land_data in DISCOVERABLE_LANDS.items():
            if land_data.get("discovery_method") == "travel":
                required_distance = land_data.get("travel_distance", 1000)
                if total_distance >= required_distance:
                    # Check if not already discovered
                    existing = await db.land_discoveries.find_one({"user_id": user_id, "land_id": land_id})
                    if not existing:
                        discovery_doc = {
                            "id": str(uuid.uuid4()),
                            "user_id": user_id,
                            "land_id": land_id,
                            "discovered_at": datetime.now(timezone.utc).isoformat(),
                            "locations_unlocked": land_data["new_locations"]
                        }
                        await db.land_discoveries.insert_one(discovery_doc)
                        await db.user_profiles.update_one({"id": user_id}, {"$inc": {"xp": 100}})
                        discoveries.append({
                            "land_id": land_id,
                            "land_name": land_data["name"],
                            "new_locations": land_data["new_locations"]
                        })
    
    return {
        "character_id": character_id,
        "new_position": new_pos,
        "direction": movement.direction,
        "speed": speed,
        "is_sprinting": movement.is_sprinting and stamina_used > 0,
        "stamina_used": stamina_used,
        "remaining_stamina": new_stamina,
        "distance_moved": distance_moved,
        "total_distance_traveled": total_distance,
        "discoveries": discoveries
    }

@api_router.post("/character/{character_id}/regenerate")
async def regenerate_stats(character_id: str):
    """Regenerate health and stamina (when out of combat)"""
    character = await db.characters.find_one({"id": character_id}, {"_id": 0})
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    if character.get("in_combat"):
        return {"status": "in_combat", "message": "Cannot regenerate while in combat"}
    
    current_health = character.get("health", 100)
    max_health = character.get("max_health", 100)
    current_stamina = character.get("stamina", 100.0)
    max_stamina = character.get("max_stamina", 100.0)
    endurance = character.get("endurance", 10)
    vitality = character.get("vitality", 10)
    
    # Regeneration rates based on stats
    health_regen = vitality * 0.5
    stamina_regen = endurance * 1.0
    
    new_health = min(max_health, current_health + health_regen)
    new_stamina = min(max_stamina, current_stamina + stamina_regen)
    
    await db.characters.update_one(
        {"id": character_id},
        {"$set": {"health": int(new_health), "stamina": new_stamina}}
    )
    
    return {
        "health": int(new_health),
        "max_health": max_health,
        "health_regenerated": new_health - current_health,
        "stamina": new_stamina,
        "max_stamina": max_stamina,
        "stamina_regenerated": new_stamina - current_stamina
    }

@api_router.post("/character/{character_id}/exit-combat")
async def exit_combat(character_id: str):
    """Exit combat mode to allow regeneration"""
    await db.characters.update_one(
        {"id": character_id},
        {"$set": {"in_combat": False, "is_blocking": False}}
    )
    return {"status": "success", "message": "Exited combat mode"}

# ============ Magic Spells & Skills Routes ============

@api_router.get("/magic/spells")
async def get_all_spells():
    """Get all available spells"""
    return {"spells": MAGIC_SPELLS, "schools": SPELL_SCHOOLS}

@api_router.get("/magic/spells/{spell_id}")
async def get_spell_details(spell_id: str):
    """Get details for a specific spell"""
    spell = MAGIC_SPELLS.get(spell_id)
    if not spell:
        raise HTTPException(status_code=404, detail="Spell not found")
    return {"spell_id": spell_id, **spell}

@api_router.get("/skills")
async def get_all_skills():
    """Get all available skills"""
    return {"skills": PLAYER_SKILLS, "categories": SKILL_CATEGORIES}

@api_router.get("/skills/{skill_id}")
async def get_skill_details(skill_id: str):
    """Get details for a specific skill"""
    skill = PLAYER_SKILLS.get(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {"skill_id": skill_id, **skill}

@api_router.get("/character/{character_id}/magic")
async def get_character_magic(character_id: str):
    """Get character's spells, skills, and mana"""
    character = await db.characters.find_one({"id": character_id}, {"_id": 0})
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    learned_spells = character.get("learned_spells", [])
    learned_skills = character.get("learned_skills", [])
    
    spell_details = {sid: MAGIC_SPELLS.get(sid) for sid in learned_spells if sid in MAGIC_SPELLS}
    skill_details = {sid: PLAYER_SKILLS.get(sid) for sid in learned_skills if sid in PLAYER_SKILLS}
    
    return {
        "mana": character.get("mana", 50),
        "max_mana": character.get("max_mana", 50),
        "intelligence": character.get("intelligence", 10),
        "wisdom": character.get("wisdom", 10),
        "learned_spells": spell_details,
        "learned_skills": skill_details,
        "equipped_spells": character.get("equipped_spells", []),
        "equipped_skills": character.get("equipped_skills", []),
        "skill_levels": character.get("skill_levels", {})
    }

@api_router.post("/character/{character_id}/learn-spell")
async def learn_spell(character_id: str, data: LearnSpell):
    """Learn a new spell"""
    character = await db.characters.find_one({"id": character_id}, {"_id": 0})
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    spell = MAGIC_SPELLS.get(data.spell_id)
    if not spell:
        raise HTTPException(status_code=404, detail="Spell not found")
    
    learned = character.get("learned_spells", [])
    if data.spell_id in learned:
        raise HTTPException(status_code=400, detail="Spell already learned")
    
    # Check XP cost
    user = await db.user_profiles.find_one({"id": character.get("user_id")}, {"_id": 0})
    if user and user.get("xp", 0) < spell.get("unlock_cost", 0):
        raise HTTPException(status_code=400, detail=f"Need {spell['unlock_cost']} XP to learn this spell")
    
    # Deduct XP and add spell
    if spell.get("unlock_cost", 0) > 0:
        await db.user_profiles.update_one(
            {"id": character.get("user_id")},
            {"$inc": {"xp": -spell["unlock_cost"]}}
        )
    
    learned.append(data.spell_id)
    await db.characters.update_one(
        {"id": character_id},
        {"$set": {"learned_spells": learned}}
    )
    
    return {"status": "success", "learned": data.spell_id, "spell": spell}

@api_router.post("/character/{character_id}/learn-skill")
async def learn_skill(character_id: str, data: LearnSkill):
    """Learn a new skill"""
    character = await db.characters.find_one({"id": character_id}, {"_id": 0})
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    skill = PLAYER_SKILLS.get(data.skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    learned = character.get("learned_skills", [])
    if data.skill_id in learned:
        raise HTTPException(status_code=400, detail="Skill already learned")
    
    user = await db.user_profiles.find_one({"id": character.get("user_id")}, {"_id": 0})
    if user and user.get("xp", 0) < skill.get("unlock_cost", 0):
        raise HTTPException(status_code=400, detail=f"Need {skill['unlock_cost']} XP to learn this skill")
    
    if skill.get("unlock_cost", 0) > 0:
        await db.user_profiles.update_one(
            {"id": character.get("user_id")},
            {"$inc": {"xp": -skill["unlock_cost"]}}
        )
    
    learned.append(data.skill_id)
    skill_levels = character.get("skill_levels", {})
    skill_levels[data.skill_id] = 1
    
    await db.characters.update_one(
        {"id": character_id},
        {"$set": {"learned_skills": learned, "skill_levels": skill_levels}}
    )
    
    return {"status": "success", "learned": data.skill_id, "skill": skill}

@api_router.post("/character/{character_id}/equip-spell")
async def equip_spell(character_id: str, spell_id: str):
    """Equip a learned spell (max 4)"""
    character = await db.characters.find_one({"id": character_id}, {"_id": 0})
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    if spell_id not in character.get("learned_spells", []):
        raise HTTPException(status_code=400, detail="Spell not learned")
    
    equipped = character.get("equipped_spells", [])
    if spell_id in equipped:
        raise HTTPException(status_code=400, detail="Spell already equipped")
    
    if len(equipped) >= 4:
        raise HTTPException(status_code=400, detail="Maximum 4 spells can be equipped")
    
    equipped.append(spell_id)
    await db.characters.update_one({"id": character_id}, {"$set": {"equipped_spells": equipped}})
    
    return {"status": "success", "equipped_spells": equipped}

@api_router.post("/character/{character_id}/unequip-spell")
async def unequip_spell(character_id: str, spell_id: str):
    """Unequip a spell"""
    character = await db.characters.find_one({"id": character_id}, {"_id": 0})
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    equipped = character.get("equipped_spells", [])
    if spell_id not in equipped:
        raise HTTPException(status_code=400, detail="Spell not equipped")
    
    equipped.remove(spell_id)
    await db.characters.update_one({"id": character_id}, {"$set": {"equipped_spells": equipped}})
    
    return {"status": "success", "equipped_spells": equipped}

@api_router.post("/character/{character_id}/cast-spell")
async def cast_spell(character_id: str, cast: SpellCast):
    """Cast an equipped spell"""
    import random
    
    character = await db.characters.find_one({"id": character_id}, {"_id": 0})
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    if cast.spell_id not in character.get("equipped_spells", []):
        raise HTTPException(status_code=400, detail="Spell not equipped")
    
    spell = MAGIC_SPELLS.get(cast.spell_id)
    if not spell:
        raise HTTPException(status_code=404, detail="Spell not found")
    
    current_mana = character.get("mana", 50)
    if current_mana < spell["mana_cost"]:
        raise HTTPException(status_code=400, detail=f"Not enough mana. Need {spell['mana_cost']}, have {current_mana}")
    
    # Calculate spell power based on intelligence
    intelligence = character.get("intelligence", 10)
    spell_power_bonus = intelligence * 0.5
    
    new_mana = current_mana - spell["mana_cost"]
    result = {
        "spell": cast.spell_id,
        "spell_name": spell["name"],
        "school": spell["school"],
        "mana_cost": spell["mana_cost"],
        "remaining_mana": new_mana
    }
    
    # Handle different spell types
    if "damage" in spell:
        base_damage = spell["damage"]
        total_damage = int(base_damage + spell_power_bonus)
        result["damage"] = total_damage
        result["effect"] = spell.get("effect")
        result["effect_duration"] = spell.get("effect_duration", 0)
        
        # Apply to target if provided
        if cast.target_id:
            # Check if target is demon
            demon = await db.demon_encounters.find_one({"id": cast.target_id, "is_active": True}, {"_id": 0})
            if demon:
                demon_data = BIBLICAL_DEMONS.get(demon["demon_type"], {})
                final_damage = total_damage
                
                # Bonus vs demons for holy spells
                if spell.get("bonus_vs_demons"):
                    final_damage = int(final_damage * spell["bonus_vs_demons"])
                    result["bonus_vs_demons"] = True
                
                new_health = demon["health_remaining"] - final_damage
                if new_health <= 0:
                    await db.demon_encounters.update_one(
                        {"id": cast.target_id},
                        {"$set": {"health_remaining": 0, "is_active": False, "killed_by": character_id}}
                    )
                    result["target_defeated"] = True
                    result["drops"] = demon_data.get("drops", {})
                else:
                    await db.demon_encounters.update_one(
                        {"id": cast.target_id},
                        {"$set": {"health_remaining": new_health}}
                    )
                    result["target_health_remaining"] = new_health
    
    elif "healing" in spell:
        heal_amount = int(spell["healing"] + spell_power_bonus)
        current_health = character.get("health", 100)
        max_health = character.get("max_health", 100)
        new_health = min(max_health, current_health + heal_amount)
        
        await db.characters.update_one({"id": character_id}, {"$set": {"health": new_health}})
        result["healing"] = heal_amount
        result["new_health"] = new_health
    
    elif spell.get("effect") == "defense_buff":
        result["buff_applied"] = spell.get("effect")
        result["defense_bonus"] = spell.get("defense_bonus", 0)
        result["duration"] = spell.get("effect_duration", 0)
    
    await db.characters.update_one({"id": character_id}, {"$set": {"mana": new_mana, "in_combat": True}})
    
    return result

@api_router.post("/character/{character_id}/regenerate-mana")
async def regenerate_mana(character_id: str):
    """Regenerate mana (when not in combat)"""
    character = await db.characters.find_one({"id": character_id}, {"_id": 0})
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    if character.get("in_combat"):
        return {"status": "in_combat", "message": "Cannot regenerate mana in combat"}
    
    current_mana = character.get("mana", 50)
    max_mana = character.get("max_mana", 50)
    wisdom = character.get("wisdom", 10)
    
    mana_regen = wisdom * 0.5
    new_mana = min(max_mana, current_mana + mana_regen)
    
    await db.characters.update_one({"id": character_id}, {"$set": {"mana": new_mana}})
    
    return {"mana": new_mana, "max_mana": max_mana, "regenerated": new_mana - current_mana}

# ============ AI Development Contribution Routes ============

@api_router.post("/ai-development/contribute")
async def contribute_to_ai_development(contribution: AIContribution):
    """Record player contribution to AI development"""
    action = AI_DEVELOPMENT_ACTIONS.get(contribution.action_type)
    if not action:
        raise HTTPException(status_code=400, detail="Invalid action type")
    
    # Get or create global AI development state
    ai_state = await db.ai_development.find_one({"id": "global"}, {"_id": 0})
    if not ai_state:
        ai_state = {
            "id": "global",
            "total_contribution": 0,
            "current_milestone": None,
            "unlocked_features": [],
            "contributor_count": 0,
            "top_contributors": []
        }
        await db.ai_development.insert_one(ai_state)
    
    # Add contribution
    contribution_points = action["contribution"]
    new_total = ai_state.get("total_contribution", 0) + contribution_points
    
    # Check for milestone unlocks
    newly_unlocked = []
    for threshold, milestone in AI_EVOLUTION_MILESTONES.items():
        if new_total >= threshold and milestone["name"] not in ai_state.get("unlocked_features", []):
            newly_unlocked.append(milestone)
    
    unlocked_features = ai_state.get("unlocked_features", []) + [m["name"] for m in newly_unlocked]
    
    await db.ai_development.update_one(
        {"id": "global"},
        {"$set": {
            "total_contribution": new_total,
            "unlocked_features": unlocked_features
        }}
    )
    
    # Track user's personal contribution
    await db.user_profiles.update_one(
        {"id": contribution.user_id},
        {"$inc": {"ai_contribution_points": contribution_points}}
    )
    
    result = {
        "status": "success",
        "contribution_points": contribution_points,
        "total_global_contribution": new_total,
        "action": contribution.action_type
    }
    
    if newly_unlocked:
        result["milestones_unlocked"] = newly_unlocked
    
    return result

@api_router.get("/ai-development/status")
async def get_ai_development_status():
    """Get current AI development status"""
    ai_state = await db.ai_development.find_one({"id": "global"}, {"_id": 0})
    if not ai_state:
        ai_state = {"total_contribution": 0, "unlocked_features": []}
    
    # Find next milestone
    total = ai_state.get("total_contribution", 0)
    next_milestone = None
    for threshold, milestone in sorted(AI_EVOLUTION_MILESTONES.items()):
        if total < threshold:
            next_milestone = {"threshold": threshold, **milestone}
            break
    
    return {
        "total_contribution": total,
        "unlocked_features": ai_state.get("unlocked_features", []),
        "next_milestone": next_milestone,
        "all_milestones": AI_EVOLUTION_MILESTONES
    }

# ============ PvP Combat System ============

class PvPChallenge(BaseModel):
    challenger_id: str
    target_id: str

class PvPAttack(BaseModel):
    attacker_id: str
    defender_id: str
    action: str  # attack, heavy_attack

@api_router.post("/pvp/challenge")
async def challenge_to_pvp(challenge: PvPChallenge):
    """Challenge another player to PvP combat"""
    challenger = await db.characters.find_one({"id": challenge.challenger_id}, {"_id": 0})
    target = await db.characters.find_one({"id": challenge.target_id}, {"_id": 0})
    
    if not challenger:
        raise HTTPException(status_code=404, detail="Challenger not found")
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    
    # Check they're in the same location
    if challenger.get("current_location") != target.get("current_location"):
        raise HTTPException(status_code=400, detail="Players must be in the same location")
    
    # Create PvP session
    pvp_session = {
        "id": str(uuid.uuid4()),
        "challenger_id": challenge.challenger_id,
        "challenger_name": challenger.get("name"),
        "target_id": challenge.target_id,
        "target_name": target.get("name"),
        "status": "pending",  # pending, active, completed
        "location": challenger.get("current_location"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "winner_id": None,
        "combat_log": []
    }
    
    pvp_response = pvp_session.copy()
    await db.pvp_sessions.insert_one(pvp_session)
    
    return {
        "status": "challenge_sent",
        "session": pvp_response,
        "message": f"{challenger.get('name')} challenges {target.get('name')} to combat!"
    }

@api_router.post("/pvp/{session_id}/accept")
async def accept_pvp_challenge(session_id: str, target_id: str):
    """Accept a PvP challenge"""
    session = await db.pvp_sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="PvP session not found")
    
    if session["target_id"] != target_id:
        raise HTTPException(status_code=403, detail="Only the challenged player can accept")
    
    if session["status"] != "pending":
        raise HTTPException(status_code=400, detail="Challenge already responded to")
    
    await db.pvp_sessions.update_one(
        {"id": session_id},
        {"$set": {"status": "active"}}
    )
    
    # Put both players in combat
    await db.characters.update_many(
        {"id": {"$in": [session["challenger_id"], session["target_id"]]}},
        {"$set": {"in_combat": True, "pvp_session_id": session_id}}
    )
    
    return {
        "status": "accepted",
        "message": "PvP combat begins!",
        "session_id": session_id
    }

@api_router.post("/pvp/{session_id}/decline")
async def decline_pvp_challenge(session_id: str, target_id: str):
    """Decline a PvP challenge"""
    session = await db.pvp_sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="PvP session not found")
    
    if session["target_id"] != target_id:
        raise HTTPException(status_code=403, detail="Only the challenged player can decline")
    
    await db.pvp_sessions.update_one(
        {"id": session_id},
        {"$set": {"status": "declined"}}
    )
    
    return {"status": "declined", "message": "Challenge declined"}

@api_router.post("/pvp/{session_id}/attack")
async def pvp_attack(session_id: str, attack: PvPAttack):
    """Execute an attack in PvP combat"""
    import random
    
    session = await db.pvp_sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="PvP session not found")
    
    if session["status"] != "active":
        raise HTTPException(status_code=400, detail="Combat not active")
    
    if attack.attacker_id not in [session["challenger_id"], session["target_id"]]:
        raise HTTPException(status_code=403, detail="You are not in this fight")
    
    attacker = await db.characters.find_one({"id": attack.attacker_id}, {"_id": 0})
    defender = await db.characters.find_one({"id": attack.defender_id}, {"_id": 0})
    
    if not attacker or not defender:
        raise HTTPException(status_code=404, detail="Character not found")
    
    # Get action data
    action_data = COMBAT_ACTIONS.get(attack.action)
    if not action_data or attack.action not in ["attack", "heavy_attack"]:
        raise HTTPException(status_code=400, detail="Invalid attack action")
    
    # Check stamina
    attacker_stamina = attacker.get("stamina", 100)
    if attacker_stamina < action_data["stamina_cost"]:
        raise HTTPException(status_code=400, detail="Not enough stamina")
    
    # Calculate damage
    weapon = WEAPON_TYPES.get(attacker.get("equipped_weapon", "fists"), WEAPON_TYPES["fists"])
    strength = attacker.get("strength", 10)
    is_critical = random.random() < 0.1
    
    damage = calculate_damage(action_data["base_damage"], strength, weapon["damage"], is_critical)
    
    # Apply defender's defense and blocking
    defender_armor = ARMOR_TYPES.get(defender.get("equipped_armor", "none"), ARMOR_TYPES["none"])
    is_blocking = defender.get("is_blocking", False)
    final_damage = calculate_damage_taken(damage, defender_armor["defense"], is_blocking)
    
    # Update characters
    new_attacker_stamina = attacker_stamina - action_data["stamina_cost"]
    new_defender_health = max(0, defender.get("health", 100) - final_damage)
    
    await db.characters.update_one({"id": attack.attacker_id}, {"$set": {"stamina": new_attacker_stamina}})
    await db.characters.update_one({"id": attack.defender_id}, {"$set": {"health": new_defender_health}})
    
    # Log combat
    log_entry = f"{attacker.get('name')} hits {defender.get('name')} for {final_damage} damage"
    if is_critical:
        log_entry += " (CRITICAL!)"
    if is_blocking:
        log_entry += " (blocked)"
    
    await db.pvp_sessions.update_one(
        {"id": session_id},
        {"$push": {"combat_log": log_entry}}
    )
    
    result = {
        "attacker": attacker.get("name"),
        "defender": defender.get("name"),
        "damage": final_damage,
        "is_critical": is_critical,
        "was_blocked": is_blocking,
        "defender_health_remaining": new_defender_health,
        "attacker_stamina_remaining": new_attacker_stamina
    }
    
    # Check for victory
    if new_defender_health <= 0:
        await db.pvp_sessions.update_one(
            {"id": session_id},
            {"$set": {"status": "completed", "winner_id": attack.attacker_id}}
        )
        await db.characters.update_many(
            {"id": {"$in": [session["challenger_id"], session["target_id"]]}},
            {"$set": {"in_combat": False}, "$unset": {"pvp_session_id": ""}}
        )
        
        # Reset defender health to 1 (not permadeath)
        await db.characters.update_one({"id": attack.defender_id}, {"$set": {"health": 1}})
        
        # Award XP to winner
        await db.characters.update_one({"id": attack.attacker_id}, {"$inc": {"xp": 50}})
        
        result["victory"] = True
        result["winner"] = attacker.get("name")
        result["message"] = f"{attacker.get('name')} is victorious!"
    
    return result

@api_router.get("/pvp/active/{character_id}")
async def get_active_pvp(character_id: str):
    """Get active PvP session for a character"""
    session = await db.pvp_sessions.find_one({
        "$or": [{"challenger_id": character_id}, {"target_id": character_id}],
        "status": "active"
    }, {"_id": 0})
    
    if not session:
        return {"active": False}
    
    return {"active": True, "session": session}

@api_router.get("/pvp/pending/{character_id}")
async def get_pending_challenges(character_id: str):
    """Get pending PvP challenges for a character"""
    challenges = await db.pvp_sessions.find({
        "target_id": character_id,
        "status": "pending"
    }, {"_id": 0}).to_list(10)
    
    return challenges

# ============ AI Villager Routes ============

@api_router.get("/professions")
async def get_all_professions():
    """Get all available AI professions with details"""
    return {
        "professions": AI_PROFESSIONS,
        "tiers": PROFESSION_TIERS
    }

@api_router.get("/professions/{profession_id}")
async def get_profession_details(profession_id: str):
    """Get details for a specific profession"""
    profession = AI_PROFESSIONS.get(profession_id)
    if not profession:
        raise HTTPException(status_code=404, detail="Profession not found")
    
    tier_info = PROFESSION_TIERS.get(profession["tier"], {})
    return {
        **profession,
        "profession_id": profession_id,
        "tier_info": tier_info
    }

@api_router.post("/villagers")
async def create_ai_villager(villager: AIVillagerCreate):
    """Create a new AI villager with a profession"""
    profession = AI_PROFESSIONS.get(villager.profession)
    if not profession:
        raise HTTPException(status_code=400, detail="Invalid profession")
    
    villager_data = {
        "id": str(uuid.uuid4()),
        "name": villager.name,
        "profession": villager.profession,
        "tier": profession["tier"],
        "personality": villager.personality,
        "home_location": villager.home_location,
        "current_location": villager.home_location,
        "inventory": {},
        "gold": 50,
        "daily_work_done": False,
        "xp": 0,
        "level": 1,
        "skills": {skill: 1 for skill in profession["abilities"]},
        "relationships": {},
        "faction": None,
        "employer_id": None,
        "learned_knowledge": profession["knowledge_domains"].copy(),
        "conversation_memory": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_worked": None
    }
    
    # Create response before insert
    villager_response = villager_data.copy()
    
    await db.ai_villagers.insert_one(villager_data)
    
    return villager_response

@api_router.get("/villagers")
async def get_all_villagers():
    """Get all AI villagers in the world"""
    villagers = await db.ai_villagers.find({}, {"_id": 0}).to_list(500)
    
    # Add profession details to each
    for v in villagers:
        prof = AI_PROFESSIONS.get(v.get("profession"))
        if prof:
            v["profession_details"] = prof
    
    return villagers

@api_router.get("/villagers/{villager_id}")
async def get_villager(villager_id: str):
    """Get a specific AI villager"""
    villager = await db.ai_villagers.find_one({"id": villager_id}, {"_id": 0})
    if not villager:
        raise HTTPException(status_code=404, detail="Villager not found")
    
    prof = AI_PROFESSIONS.get(villager.get("profession"))
    if prof:
        villager["profession_details"] = prof
    
    return villager

@api_router.get("/villagers/location/{location_id}")
async def get_villagers_at_location(location_id: str):
    """Get all AI villagers at a location"""
    villagers = await db.ai_villagers.find({"current_location": location_id}, {"_id": 0}).to_list(100)
    
    for v in villagers:
        prof = AI_PROFESSIONS.get(v.get("profession"))
        if prof:
            v["profession_details"] = prof
    
    return villagers

@api_router.post("/villagers/{villager_id}/work")
async def villager_do_work(villager_id: str):
    """Have a villager perform their daily work"""
    villager = await db.ai_villagers.find_one({"id": villager_id}, {"_id": 0})
    if not villager:
        raise HTTPException(status_code=404, detail="Villager not found")
    
    if villager.get("daily_work_done"):
        raise HTTPException(status_code=400, detail="Villager has already worked today")
    
    profession = AI_PROFESSIONS.get(villager["profession"])
    if not profession:
        raise HTTPException(status_code=400, detail="Invalid profession")
    
    # Calculate output based on level
    level_multiplier = 1 + (villager.get("level", 1) - 1) * 0.1
    
    # Produce daily output
    inventory = villager.get("inventory", {})
    gold = villager.get("gold", 0)
    
    output_report = []
    for item, amount in profession.get("daily_output", {}).items():
        produced = int(amount * level_multiplier)
        if item == "gold":
            gold += produced
        else:
            inventory[item] = inventory.get(item, 0) + produced
        output_report.append(f"+{produced} {item}")
    
    # Consume daily needs
    needs_met = True
    for item, amount in profession.get("daily_needs", {}).items():
        if item == "gold":
            if gold >= amount:
                gold -= amount
            else:
                needs_met = False
        else:
            if inventory.get(item, 0) >= amount:
                inventory[item] -= amount
            else:
                needs_met = False
    
    # XP gain
    xp_gain = 10 if needs_met else 5
    new_xp = villager.get("xp", 0) + xp_gain
    new_level = 1 + new_xp // 100
    
    await db.ai_villagers.update_one(
        {"id": villager_id},
        {"$set": {
            "inventory": inventory,
            "gold": gold,
            "daily_work_done": True,
            "last_worked": datetime.now(timezone.utc).isoformat(),
            "xp": new_xp,
            "level": new_level
        }}
    )
    
    return {
        "status": "success",
        "villager_name": villager["name"],
        "profession": villager["profession"],
        "output": output_report,
        "needs_met": needs_met,
        "xp_gained": xp_gain,
        "new_level": new_level
    }

@api_router.post("/villagers/trade")
async def villager_trade(trade_request: AITradeRequest):
    """Execute a trade between an AI villager and another entity"""
    villager = await db.ai_villagers.find_one({"id": trade_request.villager_id}, {"_id": 0})
    if not villager:
        raise HTTPException(status_code=404, detail="Villager not found")
    
    profession = AI_PROFESSIONS.get(villager["profession"])
    if not profession or not profession.get("can_trade", False):
        raise HTTPException(status_code=400, detail="This villager cannot trade")
    
    # Verify villager has items to offer
    villager_inv = villager.get("inventory", {})
    villager_gold = villager.get("gold", 0)
    
    for item, amount in trade_request.offering.items():
        if item == "gold":
            if villager_gold < amount:
                raise HTTPException(status_code=400, detail="Villager has insufficient gold")
        elif villager_inv.get(item, 0) < amount:
            raise HTTPException(status_code=400, detail=f"Villager has insufficient {item}")
    
    if trade_request.target_type == "villager":
        # Trade with another AI villager
        target = await db.ai_villagers.find_one({"id": trade_request.target_id}, {"_id": 0})
        if not target:
            raise HTTPException(status_code=404, detail="Target villager not found")
        
        target_prof = AI_PROFESSIONS.get(target["profession"])
        if not target_prof or not target_prof.get("can_trade", False):
            raise HTTPException(status_code=400, detail="Target villager cannot trade")
        
        # Verify target has requested items
        target_inv = target.get("inventory", {})
        target_gold = target.get("gold", 0)
        
        for item, amount in trade_request.requesting.items():
            if item == "gold":
                if target_gold < amount:
                    raise HTTPException(status_code=400, detail="Target has insufficient gold")
            elif target_inv.get(item, 0) < amount:
                raise HTTPException(status_code=400, detail=f"Target has insufficient {item}")
        
        # Execute trade
        # Update villager
        for item, amount in trade_request.offering.items():
            if item == "gold":
                villager_gold -= amount
            else:
                villager_inv[item] = villager_inv.get(item, 0) - amount
        
        for item, amount in trade_request.requesting.items():
            if item == "gold":
                villager_gold += amount
            else:
                villager_inv[item] = villager_inv.get(item, 0) + amount
        
        # Update target
        for item, amount in trade_request.offering.items():
            if item == "gold":
                target_gold += amount
            else:
                target_inv[item] = target_inv.get(item, 0) + amount
        
        for item, amount in trade_request.requesting.items():
            if item == "gold":
                target_gold -= amount
            else:
                target_inv[item] = target_inv.get(item, 0) - amount
        
        await db.ai_villagers.update_one(
            {"id": trade_request.villager_id},
            {"$set": {"inventory": villager_inv, "gold": villager_gold}}
        )
        
        await db.ai_villagers.update_one(
            {"id": trade_request.target_id},
            {"$set": {"inventory": target_inv, "gold": target_gold}}
        )
        
        # Improve relationship
        relationships = villager.get("relationships", {})
        relationships[trade_request.target_id] = relationships.get(trade_request.target_id, 0) + 5
        await db.ai_villagers.update_one(
            {"id": trade_request.villager_id},
            {"$set": {"relationships": relationships}}
        )
        
        return {"status": "success", "message": f"Trade between {villager['name']} and {target['name']} completed"}
    
    elif trade_request.target_type == "player":
        # Trade with a player
        player = await db.user_profiles.find_one({"id": trade_request.target_id}, {"_id": 0})
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")
        
        player_inv = player.get("materials", {})
        player_gold = player.get("resources", {}).get("gold", 0)
        
        for item, amount in trade_request.requesting.items():
            if item == "gold":
                if player_gold < amount:
                    raise HTTPException(status_code=400, detail="Player has insufficient gold")
            elif player_inv.get(item, 0) < amount:
                raise HTTPException(status_code=400, detail=f"Player has insufficient {item}")
        
        # Execute trade
        # Update villager
        for item, amount in trade_request.offering.items():
            if item == "gold":
                villager_gold -= amount
            else:
                villager_inv[item] = villager_inv.get(item, 0) - amount
        
        for item, amount in trade_request.requesting.items():
            if item == "gold":
                villager_gold += amount
            else:
                villager_inv[item] = villager_inv.get(item, 0) + amount
        
        # Update player
        for item, amount in trade_request.offering.items():
            if item == "gold":
                player_gold += amount
            else:
                player_inv[item] = player_inv.get(item, 0) + amount
        
        for item, amount in trade_request.requesting.items():
            if item == "gold":
                player_gold -= amount
            else:
                player_inv[item] = player_inv.get(item, 0) - amount
        
        await db.ai_villagers.update_one(
            {"id": trade_request.villager_id},
            {"$set": {"inventory": villager_inv, "gold": villager_gold}}
        )
        
        await db.user_profiles.update_one(
            {"id": trade_request.target_id},
            {"$set": {"materials": player_inv, "resources.gold": player_gold}}
        )
        
        return {"status": "success", "message": f"Trade between {villager['name']} and player completed"}
    
    raise HTTPException(status_code=400, detail="Invalid target type")

@api_router.post("/villagers/reset-daily")
async def reset_villager_daily_work():
    """Reset daily work status for all villagers (call at day start)"""
    result = await db.ai_villagers.update_many({}, {"$set": {"daily_work_done": False}})
    return {"status": "success", "villagers_reset": result.modified_count}

# ============ World & Land Discovery Routes ============

@api_router.get("/world/seedling")
async def get_world_seedling():
    """Get the origin world seedling data"""
    return WORLD_SEEDLING

@api_router.get("/world/lands")
async def get_discoverable_lands():
    """Get all discoverable lands and their requirements"""
    return DISCOVERABLE_LANDS

@api_router.get("/world/houses")
async def get_house_schematics():
    """Get all available house types to build"""
    return HOUSE_SCHEMATICS

@api_router.get("/world/discoveries/{user_id}")
async def get_user_discoveries(user_id: str):
    """Get lands discovered by a user"""
    discoveries = await db.land_discoveries.find({"user_id": user_id}, {"_id": 0}).to_list(50)
    
    # Enrich with land details
    for d in discoveries:
        land_info = DISCOVERABLE_LANDS.get(d["land_id"])
        if land_info:
            d["land_details"] = land_info
    
    return discoveries

@api_router.post("/world/discover/{land_id}")
async def discover_land(land_id: str, user_id: str, travel_distance: int = 0):
    """Attempt to discover a new land through travel"""
    land = DISCOVERABLE_LANDS.get(land_id)
    if not land:
        raise HTTPException(status_code=404, detail="Land not found")
    
    # Check if already discovered
    existing = await db.land_discoveries.find_one({"user_id": user_id, "land_id": land_id})
    if existing:
        raise HTTPException(status_code=400, detail="Land already discovered")
    
    # Check discovery requirements
    if land["discovery_method"] == "travel":
        if travel_distance < land["travel_distance"]:
            raise HTTPException(status_code=400, detail=f"Need {land['travel_distance']} travel distance (have {travel_distance})")
    elif land["discovery_method"] == "build":
        # Check if user has built the required building
        required = land.get("required_building")
        building = await db.buildings.find_one({"builder_id": user_id, "schematic_id": required})
        if not building:
            raise HTTPException(status_code=400, detail=f"Must build {required} first")
    
    # Create discovery
    discovery_data = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "land_id": land_id,
        "discovered_at": datetime.now(timezone.utc).isoformat(),
        "locations_unlocked": land["new_locations"]
    }
    
    discovery_response = discovery_data.copy()
    await db.land_discoveries.insert_one(discovery_data)
    
    # Award XP for discovery
    await db.user_profiles.update_one(
        {"id": user_id},
        {"$inc": {"xp": 100}}
    )
    
    return {
        "status": "success",
        "discovery": discovery_response,
        "land_name": land["name"],
        "new_locations": land["new_locations"],
        "xp_awarded": 100
    }

@api_router.post("/world/build-house")
async def build_player_house(user_id: str, house_type: str, land_id: str, x: float = 0.0, y: float = 0.0):
    """Build a house in a discovered land"""
    # Verify house type exists
    house = HOUSE_SCHEMATICS.get(house_type)
    if not house:
        raise HTTPException(status_code=404, detail="House type not found")
    
    # Verify land is discovered
    discovery = await db.land_discoveries.find_one({"user_id": user_id, "land_id": land_id})
    if not discovery and land_id != "origin_village":
        raise HTTPException(status_code=400, detail="You haven't discovered this land yet")
    
    # Check user has materials
    user = await db.user_profiles.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_materials = user.get("materials", {})
    for mat, amount in house["materials"].items():
        if user_materials.get(mat, 0) < amount:
            raise HTTPException(status_code=400, detail=f"Not enough {mat}")
    
    # Deduct materials
    new_materials = user_materials.copy()
    for mat, amount in house["materials"].items():
        new_materials[mat] = new_materials.get(mat, 0) - amount
    
    await db.user_profiles.update_one({"id": user_id}, {"$set": {"materials": new_materials}})
    
    # Create house
    house_data = {
        "id": str(uuid.uuid4()),
        "owner_id": user_id,
        "owner_name": user.get("display_name", "Unknown"),
        "house_type": house_type,
        "land_id": land_id,
        "position": {"x": x, "y": y},
        "residents": [],
        "storage": {},
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    house_response = house_data.copy()
    await db.player_houses.insert_one(house_data)
    
    # Award contribution
    contribution_gain = house.get("land_claim", 10)
    await db.user_profiles.update_one({"id": user_id}, {"$inc": {"contribution_points": contribution_gain}})
    
    return {
        "status": "success",
        "house": house_response,
        "contribution_gained": contribution_gain
    }

@api_router.get("/world/houses/{user_id}")
async def get_user_houses(user_id: str):
    """Get all houses owned by a user"""
    houses = await db.player_houses.find({"owner_id": user_id}, {"_id": 0}).to_list(50)
    
    for h in houses:
        schematic = HOUSE_SCHEMATICS.get(h["house_type"])
        if schematic:
            h["schematic"] = schematic
    
    return houses

@api_router.post("/world/houses/{house_id}/assign-villager")
async def assign_villager_to_house(house_id: str, villager_id: str, user_id: str):
    """Assign an AI villager to live in your house"""
    house = await db.player_houses.find_one({"id": house_id}, {"_id": 0})
    if not house:
        raise HTTPException(status_code=404, detail="House not found")
    
    if house["owner_id"] != user_id:
        raise HTTPException(status_code=403, detail="You don't own this house")
    
    schematic = HOUSE_SCHEMATICS.get(house["house_type"])
    if not schematic:
        raise HTTPException(status_code=400, detail="Invalid house type")
    
    if len(house.get("residents", [])) >= schematic.get("capacity", 1):
        raise HTTPException(status_code=400, detail="House is at full capacity")
    
    villager = await db.ai_villagers.find_one({"id": villager_id}, {"_id": 0})
    if not villager:
        raise HTTPException(status_code=404, detail="Villager not found")
    
    # Assign villager
    await db.player_houses.update_one(
        {"id": house_id},
        {"$push": {"residents": villager_id}}
    )
    
    # Update villager's employer
    await db.ai_villagers.update_one(
        {"id": villager_id},
        {"$set": {"employer_id": user_id, "home_location": house["land_id"]}}
    )
    
    return {
        "status": "success",
        "message": f"{villager['name']} now lives in your {house['house_type']}"
    }

# ============ Day/Night Cycle Routes ============

def get_current_phase(timezone_offset: int = 0) -> dict:
    """Get current time phase based on approximate location timezone"""
    import random
    now = datetime.now(timezone.utc)
    local_hour = (now.hour + timezone_offset) % 24
    
    for phase_name, phase_data in DAY_PHASES.items():
        start = phase_data["start_hour"]
        end = phase_data["end_hour"]
        if start <= local_hour < end or (start > end and (local_hour >= start or local_hour < end)):
            return {
                "phase": phase_name,
                "hour": local_hour,
                "description": phase_data["description"],
                "danger_level": phase_data["danger_level"],
                "demons_active": phase_data["danger_level"] > 0.3
            }
    
    return {"phase": "unknown", "hour": local_hour, "description": "Time flows strangely here", "danger_level": 0.5}

@api_router.post("/time/phase")
async def get_time_phase(request: TimePhaseRequest):
    """Get current day/night phase - uses ONLY timezone offset, never precise location"""
    return get_current_phase(request.timezone_offset)

@api_router.get("/time/phases")
async def get_all_phases():
    """Get all day/night phase definitions"""
    return DAY_PHASES

# ============ Guild Routes ============

@api_router.post("/guilds")
async def create_guild(guild_data: GuildCreate):
    """Create a new guild"""
    # Check if guild name or tag exists
    existing = await db.guilds.find_one({"$or": [{"name": guild_data.name}, {"tag": guild_data.tag.upper()}]})
    if existing:
        raise HTTPException(status_code=400, detail="Guild name or tag already exists")
    
    # Verify founder exists
    founder = await db.user_profiles.find_one({"id": guild_data.founder_id}, {"_id": 0})
    if not founder:
        raise HTTPException(status_code=404, detail="Founder not found")
    
    # Check guild type is valid
    if guild_data.guild_type not in GUILD_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid guild type. Must be one of: {list(GUILD_TYPES.keys())}")
    
    guild_doc = {
        "id": str(uuid.uuid4()),
        "name": guild_data.name,
        "tag": guild_data.tag.upper()[:5],
        "guild_type": guild_data.guild_type,
        "description": guild_data.description,
        "leader_id": guild_data.founder_id,
        "officers": [],
        "members": {guild_data.founder_id: "leader"},
        "storage": {},
        "treasury": 0,
        "xp": 0,
        "level": 1,
        "reputation": 0,
        "bonuses": GUILD_TYPES[guild_data.guild_type]["bonuses"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    guild_response = guild_doc.copy()
    await db.guilds.insert_one(guild_doc)
    
    # Update founder's profile
    await db.user_profiles.update_one(
        {"id": guild_data.founder_id},
        {"$set": {"guild_id": guild_doc["id"], "guild_rank": "leader"}}
    )
    
    return guild_response

@api_router.get("/guilds")
async def get_all_guilds():
    """Get all guilds"""
    guilds = await db.guilds.find({}, {"_id": 0}).to_list(100)
    return guilds

@api_router.get("/guilds/{guild_id}")
async def get_guild(guild_id: str):
    """Get a specific guild"""
    guild = await db.guilds.find_one({"id": guild_id}, {"_id": 0})
    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")
    return guild

@api_router.post("/guilds/{guild_id}/join")
async def join_guild(guild_id: str, user_id: str):
    """Request to join a guild"""
    guild = await db.guilds.find_one({"id": guild_id}, {"_id": 0})
    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")
    
    user = await db.user_profiles.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.get("guild_id"):
        raise HTTPException(status_code=400, detail="Already in a guild")
    
    # Add as initiate
    await db.guilds.update_one(
        {"id": guild_id},
        {"$set": {f"members.{user_id}": "initiate"}}
    )
    
    await db.user_profiles.update_one(
        {"id": user_id},
        {"$set": {"guild_id": guild_id, "guild_rank": "initiate"}}
    )
    
    return {"status": "success", "message": f"Joined {guild['name']} as Initiate"}

@api_router.post("/guilds/{guild_id}/leave")
async def leave_guild(guild_id: str, user_id: str):
    """Leave a guild"""
    guild = await db.guilds.find_one({"id": guild_id}, {"_id": 0})
    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")
    
    if guild["leader_id"] == user_id:
        raise HTTPException(status_code=400, detail="Leader cannot leave. Transfer leadership or disband.")
    
    await db.guilds.update_one(
        {"id": guild_id},
        {"$unset": {f"members.{user_id}": ""}}
    )
    
    await db.user_profiles.update_one(
        {"id": user_id},
        {"$unset": {"guild_id": "", "guild_rank": ""}}
    )
    
    return {"status": "success", "message": "Left the guild"}

@api_router.get("/guild-types")
async def get_guild_types():
    """Get all guild types and their bonuses"""
    return GUILD_TYPES

# ============ Demon & Infestation Routes ============

@api_router.get("/demons")
async def get_demon_types():
    """Get all demon types and their stats"""
    return BIBLICAL_DEMONS

@api_router.get("/demons/{demon_type}")
async def get_demon_details(demon_type: str):
    """Get details for a specific demon type"""
    demon = BIBLICAL_DEMONS.get(demon_type)
    if not demon:
        raise HTTPException(status_code=404, detail="Demon type not found")
    return {"demon_type": demon_type, **demon}

@api_router.get("/infestation/{location_id}")
async def get_location_infestation(location_id: str):
    """Get infestation level at a location"""
    infestation = await db.infestations.find_one({"location_id": location_id}, {"_id": 0})
    if not infestation:
        return {
            "location_id": location_id,
            "level": "clear",
            "demon_count": 0,
            "description": INFESTATION_LEVELS["clear"]["description"]
        }
    
    level_data = INFESTATION_LEVELS.get(infestation["level"], INFESTATION_LEVELS["clear"])
    return {
        **infestation,
        "description": level_data["description"],
        "spawn_multiplier": level_data["multiplier"]
    }

@api_router.post("/demons/spawn/{location_id}")
async def spawn_demon(location_id: str, timezone_offset: int = 0):
    """Attempt to spawn a demon at a location based on time and infestation"""
    import random
    
    phase = get_current_phase(timezone_offset)
    if phase["danger_level"] < 0.3:
        return {"spawned": False, "reason": "Demons do not stir during this hour"}
    
    # Get infestation level
    infestation = await db.infestations.find_one({"location_id": location_id}, {"_id": 0})
    level = infestation["level"] if infestation else "clear"
    multiplier = INFESTATION_LEVELS[level]["multiplier"]
    
    # Calculate spawn chance
    spawn_chance = phase["danger_level"] * multiplier * 0.3
    
    if random.random() > spawn_chance:
        return {"spawned": False, "reason": "The darkness spares this moment"}
    
    # Select demon type based on phase and rank
    available_demons = [
        (dtype, ddata) for dtype, ddata in BIBLICAL_DEMONS.items()
        if phase["phase"] in ddata["spawn_phases"]
    ]
    
    if not available_demons:
        return {"spawned": False, "reason": "No demons stir in this phase"}
    
    # Weight by rank (lesser more common)
    rank_weights = {"lesser": 5, "standard": 3, "greater": 1, "arch": 0.1}
    weighted_demons = []
    for dtype, ddata in available_demons:
        weight = rank_weights.get(ddata["rank"], 1)
        # Arch demons have additional spawn chance check
        if ddata["rank"] == "arch":
            if random.random() > ddata.get("spawn_chance", 0.05):
                continue
        weighted_demons.extend([(dtype, ddata)] * int(weight * 10))
    
    if not weighted_demons:
        return {"spawned": False, "reason": "The greater demons slumber"}
    
    demon_type, demon_data = random.choice(weighted_demons)
    
    encounter_doc = {
        "id": str(uuid.uuid4()),
        "demon_type": demon_type,
        "location_id": location_id,
        "spawned_at": datetime.now(timezone.utc).isoformat(),
        "health_remaining": demon_data["health"],
        "is_active": True,
        "killed_by": None,
        "participants": []
    }
    
    encounter_response = encounter_doc.copy()
    await db.demon_encounters.insert_one(encounter_doc)
    
    # Increase infestation
    if infestation:
        await db.infestations.update_one(
            {"location_id": location_id},
            {"$inc": {"demon_count": 1}}
        )
    else:
        await db.infestations.insert_one({
            "id": str(uuid.uuid4()),
            "location_id": location_id,
            "level": "stirring",
            "demon_count": 1,
            "last_spawn": datetime.now(timezone.utc).isoformat()
        })
    
    return {
        "spawned": True,
        "encounter": encounter_response,
        "demon": demon_data,
        "warning": f"A {demon_data['name']} emerges from the shadows!"
    }

@api_router.get("/demons/active/{location_id}")
async def get_active_demons(location_id: str):
    """Get all active demon encounters at a location"""
    encounters = await db.demon_encounters.find(
        {"location_id": location_id, "is_active": True}, 
        {"_id": 0}
    ).to_list(50)
    
    for enc in encounters:
        demon_data = BIBLICAL_DEMONS.get(enc["demon_type"])
        if demon_data:
            enc["demon_details"] = demon_data
    
    return encounters

@api_router.post("/demons/{encounter_id}/attack")
async def attack_demon(encounter_id: str, attacker_id: str, damage: int = 10):
    """Attack a demon in an encounter"""
    encounter = await db.demon_encounters.find_one({"id": encounter_id}, {"_id": 0})
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    if not encounter["is_active"]:
        raise HTTPException(status_code=400, detail="This demon has already been defeated")
    
    demon_data = BIBLICAL_DEMONS.get(encounter["demon_type"])
    if not demon_data:
        raise HTTPException(status_code=500, detail="Unknown demon type")
    
    # Add attacker to participants
    if attacker_id not in encounter.get("participants", []):
        await db.demon_encounters.update_one(
            {"id": encounter_id},
            {"$push": {"participants": attacker_id}}
        )
    
    new_health = encounter["health_remaining"] - damage
    
    if new_health <= 0:
        # Demon defeated
        await db.demon_encounters.update_one(
            {"id": encounter_id},
            {"$set": {"health_remaining": 0, "is_active": False, "killed_by": attacker_id}}
        )
        
        # Decrease infestation
        await db.infestations.update_one(
            {"location_id": encounter["location_id"]},
            {"$inc": {"demon_count": -1}, "$set": {"last_cleared": datetime.now(timezone.utc).isoformat()}}
        )
        
        # Award drops
        drops = demon_data.get("drops", {})
        
        return {
            "status": "victory",
            "message": f"The {demon_data['name']} has been vanquished!",
            "drops": drops,
            "demon_rank": demon_data["rank"],
            "biblical_origin": demon_data.get("biblical_origin", "Unknown")
        }
    else:
        await db.demon_encounters.update_one(
            {"id": encounter_id},
            {"$set": {"health_remaining": new_health}}
        )
        
        # Demon counter-attacks
        counter_damage = demon_data["damage"]
        
        return {
            "status": "combat_continues",
            "demon_health": new_health,
            "demon_max_health": demon_data["health"],
            "counter_attack_damage": counter_damage,
            "message": f"The {demon_data['name']} retaliates with {counter_damage} damage!"
        }

# ============ AI Mood & Interaction Routes ============

def calculate_mood_from_value(mood_value: int) -> str:
    """Convert mood value (0-100) to mood name"""
    if mood_value >= 90:
        return "joyful"
    elif mood_value >= 70:
        return "content"
    elif mood_value >= 50:
        return "neutral"
    elif mood_value >= 35:
        return "annoyed"
    elif mood_value >= 20:
        return "angry"
    elif mood_value >= 10:
        return "furious"
    else:
        return "furious"

@api_router.get("/villagers/{villager_id}/mood")
async def get_villager_mood(villager_id: str):
    """Get a villager's current mood state"""
    villager = await db.ai_villagers.find_one({"id": villager_id}, {"_id": 0})
    if not villager:
        raise HTTPException(status_code=404, detail="Villager not found")
    
    mood_state = villager.get("mood_state", {
        "current_mood": "neutral",
        "mood_value": 50,
        "shop_open": True,
        "refuses_service_to": []
    })
    
    mood_data = AI_MOODS.get(mood_state["current_mood"], AI_MOODS["neutral"])
    
    return {
        "villager_name": villager["name"],
        "profession": villager["profession"],
        **mood_state,
        "mood_details": mood_data,
        "will_trade": mood_data["will_help"] and mood_state["shop_open"]
    }

@api_router.post("/villagers/{villager_id}/interact")
async def interact_with_villager(villager_id: str, player_id: str, interaction_type: str):
    """Record an interaction with a villager, affecting their mood"""
    villager = await db.ai_villagers.find_one({"id": villager_id}, {"_id": 0})
    if not villager:
        raise HTTPException(status_code=404, detail="Villager not found")
    
    player = await db.user_profiles.find_one({"id": player_id}, {"_id": 0})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    event = MOOD_EVENTS.get(interaction_type)
    if not event:
        raise HTTPException(status_code=400, detail=f"Unknown interaction type. Valid: {list(MOOD_EVENTS.keys())}")
    
    # Get current mood state
    mood_state = villager.get("mood_state", {
        "current_mood": "neutral",
        "mood_value": 50,
        "recent_interactions": [],
        "shop_open": True,
        "refuses_service_to": []
    })
    
    # Apply mood change
    old_mood = mood_state["mood_value"]
    new_mood_value = max(0, min(100, old_mood + event["mood_change"]))
    new_mood_name = calculate_mood_from_value(new_mood_value)
    
    # Record interaction
    interaction_record = {
        "player_id": player_id,
        "player_name": player.get("display_name", "Unknown"),
        "interaction_type": interaction_type,
        "mood_impact": event["mood_change"],
        "description": event["description"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # Check if villager should refuse service to this player
    refuses_service_to = mood_state.get("refuses_service_to", [])
    if event["mood_change"] <= -40 and player_id not in refuses_service_to:
        refuses_service_to.append(player_id)
    
    # Check if shop should close (very bad interaction)
    shop_open = mood_state.get("shop_open", True)
    if event["mood_change"] <= -50:
        shop_open = False
    
    # Update villager
    recent = mood_state.get("recent_interactions", [])[-9:]  # Keep last 10
    recent.append(interaction_record)
    
    new_mood_state = {
        "current_mood": new_mood_name,
        "mood_value": new_mood_value,
        "recent_interactions": recent,
        "shop_open": shop_open,
        "refuses_service_to": refuses_service_to,
        "last_mood_decay": datetime.now(timezone.utc).isoformat()
    }
    
    await db.ai_villagers.update_one(
        {"id": villager_id},
        {"$set": {"mood_state": new_mood_state}}
    )
    
    mood_data = AI_MOODS.get(new_mood_name, AI_MOODS["neutral"])
    
    response = {
        "status": "success",
        "villager_name": villager["name"],
        "interaction": interaction_type,
        "mood_change": event["mood_change"],
        "old_mood": calculate_mood_from_value(old_mood),
        "new_mood": new_mood_name,
        "dialogue_tone": mood_data["dialogue_tone"],
        "will_serve_player": player_id not in refuses_service_to and shop_open
    }
    
    if not shop_open:
        response["shop_status"] = f"{villager['name']} has closed their shop for the day"
    
    if player_id in refuses_service_to:
        response["refuses_service"] = f"{villager['name']} refuses to serve you after your actions"
    
    return response

@api_router.post("/villagers/decay-moods")
async def decay_all_moods():
    """Gradually return all villager moods toward neutral (call periodically)"""
    villagers = await db.ai_villagers.find({}, {"_id": 0}).to_list(500)
    updated = 0
    
    for v in villagers:
        mood_state = v.get("mood_state", {})
        current_value = mood_state.get("mood_value", 50)
        
        # Decay toward 50 (neutral)
        if current_value > 50:
            new_value = max(50, current_value - 5)
        elif current_value < 50:
            new_value = min(50, current_value + 5)
        else:
            continue
        
        new_mood = calculate_mood_from_value(new_value)
        
        # Reopen shop if mood improves
        shop_open = mood_state.get("shop_open", True)
        if new_value >= 35:
            shop_open = True
        
        await db.ai_villagers.update_one(
            {"id": v["id"]},
            {"$set": {
                "mood_state.mood_value": new_value,
                "mood_state.current_mood": new_mood,
                "mood_state.shop_open": shop_open,
                "mood_state.last_mood_decay": datetime.now(timezone.utc).isoformat()
            }}
        )
        updated += 1
    
    return {"status": "success", "villagers_updated": updated}

# Mood-based dialogue templates
MOOD_DIALOGUES = {
    "joyful": {
        "greeting": ["Welcome, welcome! What a fine day!", "Ah, my favorite customer! What can I do for you?", "The spirits are high today! How may I serve you?"],
        "trade": ["For you? A special price!", "Take your pick, friend!", "Business is a pleasure with you!"],
        "farewell": ["Come back soon!", "May fortune smile upon you!", "Safe travels, dear friend!"]
    },
    "content": {
        "greeting": ["Good day to you.", "Welcome to my shop.", "How can I help you today?"],
        "trade": ["Fair prices for fair goods.", "See anything you like?", "Quality craftsmanship here."],
        "farewell": ["Take care now.", "Until next time.", "Good day."]
    },
    "neutral": {
        "greeting": ["Yes?", "What do you need?", "Can I help you?"],
        "trade": ["Here's what I have.", "Standard prices.", "Looking to trade?"],
        "farewell": ["Goodbye.", "Farewell.", "Be on your way."]
    },
    "annoyed": {
        "greeting": ["*sigh* What is it?", "Make it quick.", "I'm busy."],
        "trade": ["Prices are what they are.", "Take it or leave it.", "No bargaining today."],
        "farewell": ["Just go.", "Finally.", "*grumbles*"]
    },
    "angry": {
        "greeting": ["What do YOU want?", "You've got nerve coming here.", "State your business and leave."],
        "trade": ["Premium prices. Take it or leave.", "Not in the mood for haggling.", "Prices went up. Deal with it."],
        "farewell": ["Get out.", "Don't come back.", "Leave. Now."]
    },
    "furious": {
        "greeting": ["GET OUT OF MY SHOP!", "I won't serve the likes of you!", "The audacity! LEAVE!"],
        "trade": ["SHOP'S CLOSED!", "I SAID NO!", "Are you deaf? GET OUT!"],
        "farewell": ["AND STAY OUT!", "If I see you again...", "GUARDS!"]
    }
}

@api_router.get("/villagers/{villager_id}/dialogue")
async def get_villager_dialogue(villager_id: str, player_id: str, dialogue_type: str = "greeting"):
    """Get mood-based dialogue from a villager"""
    import random
    
    villager = await db.ai_villagers.find_one({"id": villager_id}, {"_id": 0})
    if not villager:
        raise HTTPException(status_code=404, detail="Villager not found")
    
    mood_state = villager.get("mood_state", {"current_mood": "neutral"})
    current_mood = mood_state.get("current_mood", "neutral")
    refuses_service = mood_state.get("refuses_service_to", [])
    
    # Check if villager refuses service to this player
    if player_id in refuses_service:
        return {
            "villager_name": villager["name"],
            "mood": current_mood,
            "refuses_service": True,
            "dialogue": f"{villager['name']} glares at you and turns away, refusing to speak.",
            "dialogue_tone": "hostile"
        }
    
    # Get dialogue based on mood
    mood_dialogues = MOOD_DIALOGUES.get(current_mood, MOOD_DIALOGUES["neutral"])
    dialogue_options = mood_dialogues.get(dialogue_type, mood_dialogues["greeting"])
    
    selected_dialogue = random.choice(dialogue_options)
    
    # Add profession flavor
    profession = AI_PROFESSIONS.get(villager.get("profession", ""), {})
    profession_name = profession.get("name", "Villager")
    
    mood_data = AI_MOODS.get(current_mood, AI_MOODS["neutral"])
    
    return {
        "villager_name": villager["name"],
        "profession": profession_name,
        "mood": current_mood,
        "dialogue_tone": mood_data["dialogue_tone"],
        "dialogue": selected_dialogue,
        "will_trade": mood_data["will_help"] and mood_state.get("shop_open", True),
        "trade_modifier": mood_data.get("trade_bonus", 1.0)
    }

# ============ AI Helper Device Access Routes (Test Feature - Sirix-1 Mobile Only) ============

async def verify_sirix_access(user_id: str) -> bool:
    """Verify the user is Sirix-1 for test features"""
    if user_id != "sirix_1_supreme":
        return False
    user = await db.user_profiles.find_one({"id": user_id}, {"_id": 0})
    return user and user.get("is_transcendent", False)

@api_router.get("/ai-helper/capabilities")
async def get_ai_helper_capabilities(user_id: str, is_mobile: bool = False):
    """Get available AI helper capabilities - returns full list for Sirix-1, limited for others"""
    is_sirix = await verify_sirix_access(user_id)
    
    if not is_sirix:
        return {
            "available": False,
            "reason": "AI Helper device access is a test feature currently restricted to Sirix-1",
            "capabilities": {}
        }
    
    # Filter capabilities based on device type
    available_caps = {}
    for cap_id, cap_data in AI_HELPER_CAPABILITIES.items():
        if cap_data.get("mobile_only") and not is_mobile:
            continue
        available_caps[cap_id] = cap_data
    
    return {
        "available": True,
        "is_test_feature": True,
        "warning": "This feature accesses device capabilities. Use responsibly.",
        "capabilities": available_caps,
        "device_type": "mobile" if is_mobile else "desktop"
    }

@api_router.post("/ai-helper/request-access")
async def request_device_access(request: DeviceAccessRequest):
    """Request AI helper access to a device capability - Sirix-1 mobile only"""
    is_sirix = await verify_sirix_access(request.user_id)
    
    if not is_sirix:
        raise HTTPException(
            status_code=403, 
            detail="AI Helper device access is a test feature restricted to Sirix-1"
        )
    
    capability = AI_HELPER_CAPABILITIES.get(request.capability)
    if not capability:
        raise HTTPException(status_code=400, detail=f"Unknown capability: {request.capability}")
    
    if capability.get("mobile_only") and not request.is_mobile:
        raise HTTPException(status_code=400, detail="This capability requires a mobile device")
    
    # Return the permission request details for the frontend to handle
    return {
        "status": "permission_required" if capability.get("requires_permission") else "granted",
        "capability": request.capability,
        "description": capability["description"],
        "requires_user_consent": capability.get("requires_permission", False),
        "instructions": {
            "geolocation_approximate": "Will request approximate location only (city-level). NEVER precise coordinates.",
            "vibration": "Ready to use. Call execute with pattern name.",
            "notification": "Will request notification permission from browser/device.",
            "orientation": "Ready to use. Will stream device orientation data.",
            "battery": "Ready to use. Will return current battery status.",
            "network": "Ready to use. Will return network connection info.",
            "wake_lock": "Will request screen wake lock to prevent sleep.",
            "clipboard": "Will request clipboard access for copying game data."
        }.get(request.capability, "Ready to use.")
    }

@api_router.post("/ai-helper/execute")
async def execute_ai_helper_command(command: AIHelperCommand):
    """Execute an AI helper command - Sirix-1 only"""
    is_sirix = await verify_sirix_access(command.user_id)
    
    if not is_sirix:
        raise HTTPException(
            status_code=403,
            detail="AI Helper commands are restricted to Sirix-1"
        )
    
    # Handle different command types
    if command.command_type == "vibrate":
        pattern_name = command.payload.get("pattern", "alert")
        patterns = AI_HELPER_CAPABILITIES["vibration"]["patterns"]
        pattern = patterns.get(pattern_name, patterns["alert"])
        
        return {
            "status": "execute",
            "command": "vibrate",
            "pattern": pattern,
            "pattern_name": pattern_name,
            "frontend_action": f"navigator.vibrate({pattern})"
        }
    
    elif command.command_type == "notify":
        return {
            "status": "execute",
            "command": "notification",
            "title": command.payload.get("title", "AI Village"),
            "body": command.payload.get("body", ""),
            "icon": command.payload.get("icon", "/favicon.ico"),
            "tag": command.payload.get("tag", "ai-village-notification"),
            "frontend_action": "new Notification(title, {body, icon, tag})"
        }
    
    elif command.command_type == "wake_lock":
        action = command.payload.get("action", "request")
        return {
            "status": "execute",
            "command": "wake_lock",
            "action": action,
            "frontend_action": f"navigator.wakeLock.{'request' if action == 'request' else 'release'}('screen')"
        }
    
    elif command.command_type == "clipboard_write":
        return {
            "status": "execute",
            "command": "clipboard_write",
            "data": command.payload.get("data", ""),
            "frontend_action": "navigator.clipboard.writeText(data)"
        }
    
    elif command.command_type == "query_battery":
        return {
            "status": "query",
            "command": "battery",
            "frontend_action": "navigator.getBattery().then(b => ({level: b.level, charging: b.charging}))"
        }
    
    elif command.command_type == "query_network":
        return {
            "status": "query", 
            "command": "network",
            "frontend_action": "({type: navigator.connection?.type, effectiveType: navigator.connection?.effectiveType, downlink: navigator.connection?.downlink})"
        }
    
    elif command.command_type == "query_orientation":
        return {
            "status": "stream",
            "command": "orientation",
            "frontend_action": "window.addEventListener('deviceorientation', (e) => ({alpha: e.alpha, beta: e.beta, gamma: e.gamma}))"
        }
    
    else:
        raise HTTPException(status_code=400, detail=f"Unknown command type: {command.command_type}")

@api_router.get("/ai-helper/status")
async def get_ai_helper_status(user_id: str):
    """Check AI helper availability and current status"""
    is_sirix = await verify_sirix_access(user_id)
    
    return {
        "enabled": is_sirix,
        "is_test_feature": True,
        "user_authorized": is_sirix,
        "version": "0.1.0-alpha",
        "disclaimer": "This is an experimental feature. Device access capabilities are used to enhance gameplay experience.",
        "privacy_note": "Location access uses APPROXIMATE data only (timezone/region). Precise coordinates are NEVER collected."
    }

# ============ Scan/View Profile Routes (with Sirix-1 Protection) ============

@api_router.get("/scan/{target_id}")
async def scan_entity(target_id: str, scanner_id: str):
    """Scan/view another player or NPC - Sirix-1 causes distortion"""
    import random
    
    # Check if target is Sirix-1
    target = await db.user_profiles.find_one({"id": target_id}, {"_id": 0})
    
    if target and target.get("is_transcendent"):
        # Scanning Sirix-1 returns distorted data
        return get_scan_failure()
    
    if target:
        # Normal player scan
        target.pop("hashed_password", None)
        return {
            "success": True,
            "entity_type": "player",
            "data": target
        }
    
    # Check if it's an AI villager
    villager = await db.ai_villagers.find_one({"id": target_id}, {"_id": 0})
    if villager:
        mood_state = villager.get("mood_state", {"current_mood": "neutral"})
        return {
            "success": True,
            "entity_type": "villager",
            "data": {
                "name": villager["name"],
                "profession": villager["profession"],
                "tier": villager.get("tier"),
                "mood": mood_state["current_mood"],
                "will_trade": AI_MOODS[mood_state["current_mood"]]["will_help"]
            }
        }
    
    # Check NPCs
    npc = await db.npcs.find_one({"id": target_id}, {"_id": 0})
    if npc:
        return {
            "success": True,
            "entity_type": "npc",
            "data": {
                "name": npc["name"],
                "role": npc["role"],
                "location": npc["current_location"]
            }
        }
    
    raise HTTPException(status_code=404, detail="Entity not found")

@api_router.get("/profile/view/{user_id}")
async def view_profile(user_id: str, viewer_id: Optional[str] = None):
    """View a user's profile - Sirix-1 appears distorted to others"""
    user = await db.user_profiles.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.pop("hashed_password", None)
    
    # Check if viewing Sirix-1
    if user.get("is_transcendent"):
        viewer_is_sirix = viewer_id == "sirix_1_supreme"
        return mask_sirix_profile(user, viewer_is_sirix)
    
    return user

# ============ Chat Commands System ============
# Commands available to different permission levels
CHAT_COMMANDS = {
    # Help command (available to all)
    "/help": {"min_level": 0, "description": "Show available commands", "usage": "/help"},
    "/commands": {"min_level": 0, "description": "Show available commands", "usage": "/commands"},
    
    # Mod commands (level 2+)
    "/kick": {"min_level": 2, "description": "Kick a player from the area", "usage": "/kick @username [reason]"},
    "/mute": {"min_level": 2, "description": "Mute a player for 10 minutes", "usage": "/mute @username [reason]"},
    "/unmute": {"min_level": 2, "description": "Unmute a player", "usage": "/unmute @username"},
    "/warn": {"min_level": 2, "description": "Issue a warning to a player", "usage": "/warn @username [reason]"},
    "/announce": {"min_level": 2, "description": "Make a local announcement", "usage": "/announce [message]"},
    
    # Admin commands (level 3+)
    "/ban": {"min_level": 3, "description": "Ban a player temporarily", "usage": "/ban @username [duration] [reason]"},
    "/unban": {"min_level": 3, "description": "Unban a player", "usage": "/unban @username"},
    "/spawn": {"min_level": 3, "description": "Spawn an NPC or item", "usage": "/spawn [npc/item] [id]"},
    "/tp": {"min_level": 3, "description": "Teleport to a location", "usage": "/tp [location_id]"},
    "/tphere": {"min_level": 3, "description": "Teleport a player to you", "usage": "/tphere @username"},
    "/give": {"min_level": 3, "description": "Give items to a player", "usage": "/give @username [item] [amount]"},
    "/setrank": {"min_level": 3, "description": "Set a player's official rank", "usage": "/setrank @username [rank]"},
    "/broadcast": {"min_level": 3, "description": "Broadcast to all locations", "usage": "/broadcast [message]"},
    
    # High ranker commands (guild_master+, rank 4+)
    "/guild_announce": {"min_rank": 4, "description": "Announce to guild members", "usage": "/guild_announce [message]"},
    "/summon": {"min_rank": 6, "description": "Summon a player to your location (mayor+)", "usage": "/summon @username"},
    
    # Sirix-1 exclusive commands (level 999)
    "/god": {"min_level": 999, "description": "Toggle invincibility", "usage": "/god"},
    "/reset_world": {"min_level": 999, "description": "Reset world state", "usage": "/reset_world [confirm]"},
    "/override": {"min_level": 999, "description": "Override any system", "usage": "/override [system] [value]"},
    "/reveal": {"min_level": 999, "description": "Reveal all hidden information", "usage": "/reveal"},
}

class ChatCommandRequest(BaseModel):
    user_id: str
    command: str
    args: List[str] = Field(default_factory=list)
    location_id: Optional[str] = None

class ChatCommandResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

@api_router.get("/commands")
async def get_available_commands(user_id: str):
    """Get commands available to the user based on their permission level and rank"""
    user = await db.user_profiles.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    perm_level = PERMISSION_LEVELS.get(user.get("permission_level", "player"), {}).get("level", 1)
    rank_data = OFFICIAL_RANKINGS.get(user.get("official_rank", "citizen"), {})
    user_rank = rank_data.get("rank", 1)
    
    available_commands = {}
    for cmd, info in CHAT_COMMANDS.items():
        min_level = info.get("min_level", 0)
        min_rank = info.get("min_rank", 0)
        
        if perm_level >= min_level or user_rank >= min_rank:
            available_commands[cmd] = {
                "description": info["description"],
                "usage": info["usage"]
            }
    
    return {
        "commands": available_commands,
        "permission_level": user.get("permission_level", "player"),
        "official_rank": user.get("official_rank", "citizen")
    }

@api_router.post("/commands/execute", response_model=ChatCommandResponse)
async def execute_command(request: ChatCommandRequest):
    """Execute a chat command"""
    user = await db.user_profiles.find_one({"id": request.user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    perm_level = PERMISSION_LEVELS.get(user.get("permission_level", "player"), {}).get("level", 1)
    rank_data = OFFICIAL_RANKINGS.get(user.get("official_rank", "citizen"), {})
    user_rank = rank_data.get("rank", 1)
    
    cmd_info = CHAT_COMMANDS.get(request.command)
    if not cmd_info:
        return ChatCommandResponse(success=False, message=f"Unknown command: {request.command}")
    
    min_level = cmd_info.get("min_level", 0)
    min_rank = cmd_info.get("min_rank", 0)
    
    if perm_level < min_level and user_rank < min_rank:
        return ChatCommandResponse(success=False, message="Insufficient permissions for this command")
    
    # Execute commands
    result_data = {}
    
    if request.command == "/kick":
        if len(request.args) < 1:
            return ChatCommandResponse(success=False, message="Usage: /kick @username [reason]")
        target_name = request.args[0].lstrip("@")
        reason = " ".join(request.args[1:]) if len(request.args) > 1 else "No reason provided"
        # Add kick logic - remove from location
        result_data = {"kicked": target_name, "reason": reason}
        
    elif request.command == "/mute":
        if len(request.args) < 1:
            return ChatCommandResponse(success=False, message="Usage: /mute @username [reason]")
        target_name = request.args[0].lstrip("@")
        await db.user_profiles.update_one(
            {"username": target_name},
            {"$set": {"muted_until": datetime.now(timezone.utc).isoformat(), "mute_duration": 600}}
        )
        result_data = {"muted": target_name, "duration": "10 minutes"}
        
    elif request.command == "/announce":
        if len(request.args) < 1:
            return ChatCommandResponse(success=False, message="Usage: /announce [message]")
        message = " ".join(request.args)
        # Broadcast to location
        if request.location_id and request.location_id in location_connections:
            for ws in location_connections[request.location_id].values():
                try:
                    await ws.send_json({
                        "type": "announcement",
                        "data": {"message": message, "from": user.get("display_name", "Moderator")}
                    })
                except Exception:
                    pass
        result_data = {"announced": message}
        
    elif request.command == "/broadcast":
        if len(request.args) < 1:
            return ChatCommandResponse(success=False, message="Usage: /broadcast [message]")
        message = " ".join(request.args)
        # Broadcast to all locations
        for loc_id, connections in location_connections.items():
            for ws in connections.values():
                try:
                    await ws.send_json({
                        "type": "global_announcement",
                        "data": {"message": message, "from": user.get("display_name", "Admin")}
                    })
                except Exception:
                    pass
        result_data = {"broadcast": message}
        
    elif request.command == "/tp":
        if len(request.args) < 1:
            return ChatCommandResponse(success=False, message="Usage: /tp [location_id]")
        target_location = request.args[0]
        # Update user's character location
        char = await db.characters.find_one({"user_id": request.user_id})
        if char:
            await db.characters.update_one(
                {"id": char["id"]},
                {"$set": {"current_location": target_location}}
            )
        result_data = {"teleported_to": target_location}
        
    elif request.command == "/give":
        if len(request.args) < 3:
            return ChatCommandResponse(success=False, message="Usage: /give @username [item] [amount]")
        target_name = request.args[0].lstrip("@")
        item = request.args[1]
        amount = int(request.args[2]) if request.args[2].isdigit() else 1
        
        target = await db.user_profiles.find_one({"username": target_name})
        if target:
            await db.user_profiles.update_one(
                {"username": target_name},
                {"$inc": {f"resources.{item}": amount}}
            )
        result_data = {"gave": item, "amount": amount, "to": target_name}
        
    elif request.command == "/god":
        # Toggle god mode for Sirix-1
        char = await db.characters.find_one({"user_id": request.user_id})
        if char:
            current_god = char.get("god_mode", False)
            await db.characters.update_one(
                {"id": char["id"]},
                {"$set": {"god_mode": not current_god, "health": 999999, "max_health": 999999}}
            )
        result_data = {"god_mode": "enabled" if not char.get("god_mode") else "disabled"}
        
    else:
        return ChatCommandResponse(success=True, message=f"Command {request.command} acknowledged (implementation pending)")
    
    # Log command execution
    await db.command_logs.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": request.user_id,
        "command": request.command,
        "args": request.args,
        "location_id": request.location_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "result": result_data
    })
    
    return ChatCommandResponse(success=True, message=f"Command executed: {request.command}", data=result_data)

# ============ Oracle World Monitor System ============
# The Oracle (Veythra) can see world state, prophecies, and hidden information

class OracleVisionRequest(BaseModel):
    viewer_id: str
    vision_type: str = "world_state"  # world_state, prophecy, player_fate, hidden_truth

@api_router.get("/oracle/status")
async def get_oracle_status():
    """Get Oracle Veythra's current status and availability"""
    oracle = await db.ai_villagers.find_one({"name": "Oracle Veythra"}, {"_id": 0})
    if not oracle:
        # Create Oracle if doesn't exist
        oracle = {
            "villager_id": "oracle_veythra",
            "name": "Oracle Veythra",
            "profession": "oracle",
            "description": "The all-seeing Oracle who monitors the world's threads of fate",
            "location_id": "oracle_sanctum",
            "mood": "mysterious",
            "abilities": ["world_sight", "prophecy", "fate_reading", "hidden_truth"],
            "is_world_monitor": True,
            "vision_cooldown": 0,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.ai_villagers.insert_one(oracle)
    
    return {
        "oracle": oracle,
        "available": True,
        "vision_types": ["world_state", "prophecy", "player_fate", "hidden_truth"]
    }

@api_router.post("/oracle/vision")
async def request_oracle_vision(request: OracleVisionRequest):
    """Request a vision from the Oracle - world monitoring system"""
    viewer = await db.user_profiles.find_one({"id": request.viewer_id})
    if not viewer:
        raise HTTPException(status_code=404, detail="Viewer not found")
    
    vision_data = {}
    
    if request.vision_type == "world_state":
        # Get comprehensive world state
        total_players = await db.user_profiles.count_documents({})
        total_characters = await db.characters.count_documents({})
        active_demons = await db.active_demons.count_documents({"defeated": {"$ne": True}})
        total_guilds = await db.guilds.count_documents({})
        total_buildings = await db.buildings.count_documents({})
        
        # Get location populations
        location_stats = {}
        async for char in db.characters.find({}, {"current_location": 1}):
            loc = char.get("current_location", "unknown")
            location_stats[loc] = location_stats.get(loc, 0) + 1
        
        # Get active PvP battles
        active_pvp = await db.pvp_sessions.count_documents({"status": "active"})
        
        # Get economy stats
        pipeline = [
            {"$group": {"_id": None, "total_gold": {"$sum": "$resources.gold"}}}
        ]
        economy = await db.user_profiles.aggregate(pipeline).to_list(1)
        total_gold = economy[0]["total_gold"] if economy else 0
        
        vision_data = {
            "world_population": {
                "total_souls": total_players,
                "active_heroes": total_characters,
                "demons_roaming": active_demons
            },
            "civilizations": {
                "guilds_formed": total_guilds,
                "structures_built": total_buildings
            },
            "location_activity": location_stats,
            "conflicts": {
                "active_pvp_battles": active_pvp
            },
            "economy": {
                "total_gold_circulation": total_gold if total_gold else "Immeasurable"
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    elif request.vision_type == "prophecy":
        # Generate AI prophecy about world events
        if llm_key:
            try:
                chat = LlmChat(llm_key, model="anthropic/claude-sonnet-4-20250514")
                chat.add_message(UserMessage(content="""You are Oracle Veythra, a mystical seer. 
                Generate a cryptic prophecy about upcoming events in a fantasy village world.
                Include hints about: demons, heroes, guilds, trade, or discoveries.
                Keep it under 100 words, mysterious and poetic."""))
                prophecy = await asyncio.to_thread(chat.send_message)
                vision_data = {"prophecy": prophecy, "type": "divine_vision"}
            except Exception:
                vision_data = {"prophecy": "The threads of fate are tangled... clarity eludes even my sight.", "type": "obscured"}
        else:
            vision_data = {"prophecy": "The mists part to reveal... change approaches from the shadows.", "type": "standard"}
            
    elif request.vision_type == "player_fate":
        # Get stats about the requesting player
        char = await db.characters.find_one({"user_id": request.viewer_id}, {"_id": 0})
        if char:
            vision_data = {
                "fate_reading": {
                    "health_aura": "strong" if char.get("health", 100) > 50 else "weakening",
                    "destiny_points": char.get("xp", 0),
                    "battles_ahead": await db.active_demons.count_documents({"location_id": char.get("current_location")}),
                    "guild_bonds": char.get("guild_id") is not None,
                    "journey_distance": char.get("total_distance_traveled", 0)
                }
            }
        else:
            vision_data = {"fate_reading": "Your fate is yet unwritten..."}
            
    elif request.vision_type == "hidden_truth":
        # Sirix-1 only - reveal all hidden information
        if viewer.get("is_transcendent") or viewer.get("permission_level") == "sirix_1":
            # Get all hidden/secret data
            hidden_demons = await db.active_demons.find({"hidden": True}, {"_id": 0}).to_list(100)
            secret_locations = await db.world_secrets.find({}, {"_id": 0}).to_list(100)
            vision_data = {
                "hidden_demons": hidden_demons,
                "secret_locations": secret_locations,
                "all_seeing": True
            }
        else:
            vision_data = {"message": "This truth is beyond your mortal sight..."}
    
    return {
        "vision_type": request.vision_type,
        "oracle": "Veythra",
        "data": vision_data,
        "granted_at": datetime.now(timezone.utc).isoformat()
    }

# ============ External AI Integration System ============
# API connection point for installing external AI apps

class AIAppRegistration(BaseModel):
    app_name: str
    app_description: str
    developer_id: str
    api_endpoint: str
    capabilities: List[str] = Field(default_factory=list)  # e.g., ["dialogue", "combat_ai", "world_gen"]
    required_permissions: List[str] = Field(default_factory=list)
    webhook_url: Optional[str] = None

class AIAppApproval(BaseModel):
    app_id: str
    approver_id: str
    approved: bool
    restrictions: List[str] = Field(default_factory=list)

@api_router.get("/integrations/apps")
async def list_ai_apps(user_id: Optional[str] = None):
    """List all registered AI apps and their status"""
    apps = await db.ai_integrations.find({}, {"_id": 0}).to_list(100)
    
    # If user provided, show which they have access to
    if user_id:
        user = await db.user_profiles.find_one({"id": user_id})
        user_apps = user.get("installed_ai_apps", []) if user else []
        for app in apps:
            app["installed"] = app["app_id"] in user_apps
    
    return {
        "apps": apps,
        "total": len(apps)
    }

@api_router.post("/integrations/register")
async def register_ai_app(registration: AIAppRegistration):
    """Register a new AI app for integration (requires approval)"""
    # Check if developer exists
    developer = await db.user_profiles.find_one({"id": registration.developer_id})
    if not developer:
        raise HTTPException(status_code=404, detail="Developer not found")
    
    # Check developer permission level
    perm_level = PERMISSION_LEVELS.get(developer.get("permission_level", "player"), {}).get("level", 1)
    if perm_level < 2:  # At least mod level to register apps
        raise HTTPException(status_code=403, detail="Insufficient permissions to register AI apps")
    
    app_id = f"ai_app_{str(uuid.uuid4())[:8]}"
    
    app_data = {
        "app_id": app_id,
        "app_name": registration.app_name,
        "description": registration.app_description,
        "developer_id": registration.developer_id,
        "developer_name": developer.get("display_name", developer.get("username")),
        "api_endpoint": registration.api_endpoint,
        "capabilities": registration.capabilities,
        "required_permissions": registration.required_permissions,
        "webhook_url": registration.webhook_url,
        "status": "pending_approval",
        "approved_by": None,
        "restrictions": [],
        "install_count": 0,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.ai_integrations.insert_one(app_data)
    
    return {
        "app_id": app_id,
        "status": "pending_approval",
        "message": "AI app registered. Awaiting admin approval."
    }

@api_router.post("/integrations/approve")
async def approve_ai_app(approval: AIAppApproval):
    """Approve or reject an AI app (admin/sirix-1 only)"""
    approver = await db.user_profiles.find_one({"id": approval.approver_id})
    if not approver:
        raise HTTPException(status_code=404, detail="Approver not found")
    
    perm_level = PERMISSION_LEVELS.get(approver.get("permission_level", "player"), {}).get("level", 1)
    if perm_level < 3:  # Admin level required
        raise HTTPException(status_code=403, detail="Only admins can approve AI apps")
    
    app = await db.ai_integrations.find_one({"app_id": approval.app_id})
    if not app:
        raise HTTPException(status_code=404, detail="AI app not found")
    
    new_status = "approved" if approval.approved else "rejected"
    
    await db.ai_integrations.update_one(
        {"app_id": approval.app_id},
        {"$set": {
            "status": new_status,
            "approved_by": approval.approver_id,
            "restrictions": approval.restrictions,
            "approved_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {
        "app_id": approval.app_id,
        "status": new_status,
        "message": f"AI app {new_status}"
    }

@api_router.post("/integrations/install/{app_id}")
async def install_ai_app(app_id: str, user_id: str):
    """Install an approved AI app for a user"""
    app = await db.ai_integrations.find_one({"app_id": app_id})
    if not app:
        raise HTTPException(status_code=404, detail="AI app not found")
    
    if app["status"] != "approved":
        raise HTTPException(status_code=403, detail="AI app not approved for installation")
    
    user = await db.user_profiles.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if user has required permissions
    for perm in app.get("required_permissions", []):
        user_perms = PERMISSION_LEVELS.get(user.get("permission_level", "player"), {}).get("abilities", [])
        if perm not in user_perms and "all" not in user_perms:
            raise HTTPException(status_code=403, detail=f"Missing required permission: {perm}")
    
    # Install app for user
    installed_apps = user.get("installed_ai_apps", [])
    if app_id not in installed_apps:
        installed_apps.append(app_id)
        await db.user_profiles.update_one(
            {"id": user_id},
            {"$set": {"installed_ai_apps": installed_apps}}
        )
        await db.ai_integrations.update_one(
            {"app_id": app_id},
            {"$inc": {"install_count": 1}}
        )
    
    return {
        "app_id": app_id,
        "app_name": app["app_name"],
        "installed": True,
        "capabilities": app["capabilities"]
    }

@api_router.post("/integrations/call/{app_id}")
async def call_ai_app(app_id: str, user_id: str, action: str, payload: Dict[str, Any] = None):
    """Call an installed AI app's endpoint"""
    # Verify user has app installed
    user = await db.user_profiles.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if app_id not in user.get("installed_ai_apps", []):
        raise HTTPException(status_code=403, detail="AI app not installed")
    
    app = await db.ai_integrations.find_one({"app_id": app_id})
    if not app or app["status"] != "approved":
        raise HTTPException(status_code=404, detail="AI app not available")
    
    # Call the external AI endpoint
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                app["api_endpoint"],
                json={
                    "action": action,
                    "user_id": user_id,
                    "payload": payload or {},
                    "app_id": app_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
            response.raise_for_status()
            return {
                "app_id": app_id,
                "action": action,
                "response": response.json()
            }
    except httpx.HTTPError as e:
        logger.error(f"AI app call failed: {e}")
        raise HTTPException(status_code=502, detail=f"AI app communication failed: {str(e)}")

@api_router.delete("/integrations/uninstall/{app_id}")
async def uninstall_ai_app(app_id: str, user_id: str):
    """Uninstall an AI app from user's account"""
    user = await db.user_profiles.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
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
