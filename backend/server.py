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
    
    existing = await db.user_profiles.find_one({"username": "sirix_1"})
    if existing:
        # Update existing Sirix-1 with password
        await db.user_profiles.update_one(
            {"username": "sirix_1"},
            {"$set": {"hashed_password": hashed_password}}
        )
        logger.info("Sirix-1 supreme account password updated")
    else:
        sirix_profile = {
            "id": "sirix_1_supreme",
            "username": "sirix_1",
            "display_name": "Sirix-1",
            "hashed_password": hashed_password,
            "permission_level": "sirix_1",
            "official_rank": "sovereign",
            "reputation": 999999,
            "contribution_points": 999999,
            "resources": {"gold": 999999, "essence": 999999, "artifacts": 999999},
            "materials": {"wood": 9999, "stone": 9999, "iron": 9999, "crystal": 9999, "obsidian": 9999},
            "unlocked_schematics": list(SCHEMATICS.keys()),
            "xp": 999999,
            "characters": [],
            "character_model": {
                "body_color": "#FFD700",
                "accent_color": "#8B0000",
                "eye_color": "#FF4500",
                "body_type": "standard"
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_active": datetime.now(timezone.utc).isoformat(),
            "is_immutable": True
        }
        await db.user_profiles.insert_one(sirix_profile)
        logger.info("Sirix-1 supreme account initialized with password")

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
                message = {
                    "id": str(uuid.uuid4()),
                    "location_id": location_id,
                    "sender_id": user_id,
                    "sender_name": data.get("sender_name", username),
                    "sender_type": "player",
                    "content": data["content"],
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
