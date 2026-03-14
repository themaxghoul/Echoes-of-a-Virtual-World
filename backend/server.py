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

# ============ Models ============

class UserProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    display_name: str
    permission_level: str = "basic"
    official_rank: str = "citizen"  # From OFFICIAL_RANKINGS
    reputation: int = 0  # For standing calculation
    resources: Dict[str, int] = Field(default_factory=lambda: {"gold": 100, "essence": 10, "artifacts": 0})
    xp: int = 0
    characters: List[str] = []
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
    learned_by: str = "system"  # who learned this - can be npc_id
    connections: List[str] = []
    strength: float = 1.0
    source_type: str = "player_interaction"  # player_interaction, ai_observation, world_data
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DataspaceEntryCreate(BaseModel):
    category: str
    key: str
    value: str
    learned_from: str
    connections: List[str] = []

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
    """Initialize the Sirix-1 supreme account if not exists"""
    existing = await db.user_profiles.find_one({"username": "sirix_1"})
    if not existing:
        sirix_profile = {
            "id": "sirix_1_supreme",
            "username": "sirix_1",
            "display_name": "Sirix-1",
            "permission_level": "sirix_1",
            "resources": {"gold": 999999, "essence": 999999, "artifacts": 999999},
            "xp": 999999,
            "characters": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_active": datetime.now(timezone.utc).isoformat(),
            "is_immutable": True
        }
        await db.user_profiles.insert_one(sirix_profile)
        logger.info("Sirix-1 supreme account initialized")

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
    logger.info("AI Village initialized with Sirix-1 and NPCs")

# ============ API Routes ============

@api_router.get("/")
async def root():
    return {"message": "Welcome to AI Village: The Echoes - Multiplayer Edition"}

# User Profile Routes
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
