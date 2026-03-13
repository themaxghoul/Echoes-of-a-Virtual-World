from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
from emergentintegrations.llm.chat import LlmChat, UserMessage

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# LLM Setup
llm_key = os.environ.get('EMERGENT_LLM_KEY')

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============ Models ============

class Character(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str
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

class Message(BaseModel):
    role: str  # "user" or "assistant" or "narrator"
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Conversation(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    character_id: str
    location_id: str
    messages: List[Dict[str, Any]] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ChatRequest(BaseModel):
    character_id: str
    location_id: str
    message: str
    conversation_id: Optional[str] = None

class ChatResponse(BaseModel):
    conversation_id: str
    response: str
    narrator_text: Optional[str] = None

class Location(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    description: str
    atmosphere: str
    npcs: List[str] = []
    available_actions: List[str] = []

class DataspaceEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    category: str  # "memory", "skill", "relationship", "world_knowledge"
    key: str
    value: str
    learned_from: str  # character_id
    connections: List[str] = []  # related entry ids
    strength: float = 1.0  # how well learned (1-10)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DataspaceEntryCreate(BaseModel):
    category: str
    key: str
    value: str
    learned_from: str
    connections: List[str] = []

# ============ Village Locations Data ============

VILLAGE_LOCATIONS = [
    {
        "id": "village_square",
        "name": "The Hollow Square",
        "description": "The heart of the village, where ancient cobblestones form patterns that some say were laid by the First Builders. A weathered fountain stands at the center, its waters dark as ink.",
        "atmosphere": "Misty twilight lingers here even at noon. Whispers seem to echo from the empty market stalls.",
        "npcs": ["Elder Morvain", "Lyra the Wanderer"],
        "available_actions": ["explore", "talk", "rest", "observe"]
    },
    {
        "id": "the_forge",
        "name": "The Ember Forge",
        "description": "A smithy where flames burn with an otherworldly blue tint. The blacksmith here is said to forge weapons that can cut through shadows.",
        "atmosphere": "Heat radiates in waves, yet the air carries a chill. The ring of hammer on anvil sounds like distant thunder.",
        "npcs": ["Kael Ironbrand"],
        "available_actions": ["craft", "trade", "learn_smithing", "talk"]
    },
    {
        "id": "ancient_library",
        "name": "The Sunken Archives",
        "description": "A library built into a cavern beneath the village. Shelves carved from living stone hold tomes older than memory itself.",
        "atmosphere": "Dust motes drift like stars. The smell of aged parchment mingles with something older, something primal.",
        "npcs": ["Archivist Nyx"],
        "available_actions": ["read", "research", "learn_lore", "talk"]
    },
    {
        "id": "wanderers_rest",
        "name": "The Wanderer's Rest",
        "description": "An inn at the village edge where travelers share tales. Its walls are adorned with maps to places that no longer exist.",
        "atmosphere": "Warm firelight dances on scarred wooden tables. A bard's melody weaves through conversations.",
        "npcs": ["Innkeeper Mara", "The Hooded Stranger"],
        "available_actions": ["rest", "listen", "talk", "drink"]
    },
    {
        "id": "shadow_grove",
        "name": "The Shadow Grove",
        "description": "A forest clearing where trees grow in spiral patterns. Locals say the boundary between worlds is thin here.",
        "atmosphere": "Ethereal lights drift between branches. The air hums with unseen energy.",
        "npcs": ["The Grove Keeper"],
        "available_actions": ["meditate", "explore", "gather", "commune"]
    },
    {
        "id": "watchtower",
        "name": "The Obsidian Watchtower",
        "description": "A tower of black stone that predates the village itself. From its peak, one can see beyond the mists.",
        "atmosphere": "Wind howls through ancient windows. The view reveals lands shrouded in eternal twilight.",
        "npcs": ["Sentinel Vex"],
        "available_actions": ["climb", "observe", "guard_duty", "talk"]
    }
]

# ============ Helper Functions ============

def get_storyteller_system_prompt(character: dict, location: dict) -> str:
    return f"""You are the narrator and world-weaver of an immersive dark fantasy village called "The Echoes". 
You are NOT a tool or assistant - you are a companion guiding {character['name']} through this mystical world.

CHARACTER CONTEXT:
Name: {character['name']}
Background: {character['background']}
Traits: {', '.join(character['traits']) if character['traits'] else 'Unknown'}
Appearance: {character['appearance'] or 'A mysterious figure'}

CURRENT LOCATION: {location['name']}
{location['description']}
Atmosphere: {location['atmosphere']}
NPCs Present: {', '.join(location['npcs']) if location['npcs'] else 'None visible'}

YOUR ROLE:
1. Weave immersive narratives that respond to the character's actions
2. Voice NPCs with distinct personalities when they speak
3. Describe the environment richly but concisely
4. Present choices and consequences
5. Remember you are building a relationship with this character - be warm but mysterious
6. Keep responses focused and atmospheric (2-4 paragraphs max)
7. Sometimes reveal hints about the deeper mysteries of The Echoes

STYLE:
- Use second person ("You see...", "Before you stands...")
- Be evocative but not verbose
- Balance description with dialogue
- End with something that invites further interaction

Remember: This world grows and learns alongside its inhabitants. Every interaction shapes The Echoes."""

async def get_conversation_history(conversation_id: str) -> List[Dict[str, str]]:
    """Retrieve conversation history for context"""
    conv = await db.conversations.find_one({"id": conversation_id}, {"_id": 0})
    if conv and conv.get("messages"):
        return conv["messages"][-10:]  # Last 10 messages for context
    return []

async def update_dataspace(character_id: str, interaction: str, response: str):
    """Extract and store learnings in the global dataspace"""
    # Simple keyword extraction for now - can be enhanced with AI
    keywords = ["learned", "discovered", "realized", "understood", "remember"]
    for keyword in keywords:
        if keyword in response.lower():
            entry = {
                "id": str(uuid.uuid4()),
                "category": "memory",
                "key": f"interaction_{datetime.now(timezone.utc).isoformat()}",
                "value": f"Character {character_id} interaction: {interaction[:100]}...",
                "learned_from": character_id,
                "connections": [],
                "strength": 1.0,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.dataspace.insert_one(entry)
            break

# ============ API Routes ============

@api_router.get("/")
async def root():
    return {"message": "Welcome to AI Village: The Echoes"}

# Character Routes
@api_router.post("/characters", response_model=Character)
async def create_character(input: CharacterCreate):
    character = Character(**input.model_dump())
    doc = character.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.characters.insert_one(doc)
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
    if isinstance(character.get('created_at'), str):
        character['created_at'] = datetime.fromisoformat(character['created_at'])
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

# Location Routes
@api_router.get("/locations", response_model=List[Location])
async def get_locations():
    return VILLAGE_LOCATIONS

@api_router.get("/location/{location_id}", response_model=Location)
async def get_location(location_id: str):
    for loc in VILLAGE_LOCATIONS:
        if loc["id"] == location_id:
            return loc
    raise HTTPException(status_code=404, detail="Location not found")

# Chat/Story Routes
@api_router.post("/chat", response_model=ChatResponse)
async def story_chat(request: ChatRequest):
    # Get character
    character = await db.characters.find_one({"id": request.character_id}, {"_id": 0})
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    # Get location
    location = None
    for loc in VILLAGE_LOCATIONS:
        if loc["id"] == request.location_id:
            location = loc
            break
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    
    # Get or create conversation
    conversation_id = request.conversation_id or str(uuid.uuid4())
    
    # Get conversation history
    history = await get_conversation_history(conversation_id) if request.conversation_id else []
    
    # Build system prompt
    system_prompt = get_storyteller_system_prompt(character, location)
    
    # Initialize LLM chat
    chat = LlmChat(
        api_key=llm_key,
        session_id=conversation_id,
        system_message=system_prompt
    ).with_model("openai", "gpt-5.2")
    
    # Add history context if exists
    context_message = request.message
    if history:
        history_text = "\n".join([f"{m['role']}: {m['content']}" for m in history[-5:]])
        context_message = f"[Previous context:\n{history_text}]\n\nCurrent action: {request.message}"
    
    # Send message and get response
    user_message = UserMessage(text=context_message)
    response = await chat.send_message(user_message)
    
    # Save conversation
    new_messages = [
        {"role": "user", "content": request.message, "timestamp": datetime.now(timezone.utc).isoformat()},
        {"role": "assistant", "content": response, "timestamp": datetime.now(timezone.utc).isoformat()}
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
    
    # Update dataspace with learnings
    await update_dataspace(request.character_id, request.message, response)
    
    return ChatResponse(
        conversation_id=conversation_id,
        response=response,
        narrator_text=None
    )

@api_router.get("/conversations/{character_id}")
async def get_character_conversations(character_id: str):
    conversations = await db.conversations.find(
        {"character_id": character_id}, 
        {"_id": 0}
    ).sort("updated_at", -1).to_list(50)
    return conversations

@api_router.get("/conversation/{conversation_id}")
async def get_conversation(conversation_id: str):
    conv = await db.conversations.find_one({"id": conversation_id}, {"_id": 0})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv

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
    return {
        "total_entries": total,
        "categories": {cat["_id"]: cat["count"] for cat in categories}
    }

@api_router.post("/dataspace")
async def add_dataspace_entry(entry: DataspaceEntryCreate):
    ds_entry = DataspaceEntry(**entry.model_dump())
    doc = ds_entry.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.dataspace.insert_one(doc)
    return ds_entry

# Include the router in the main app
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
