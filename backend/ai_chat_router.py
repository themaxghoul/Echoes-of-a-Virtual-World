# AI Chat Service - Isolated Text Chat with World Context Integration
# Enables NPCs to understand context and commit real world changes

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone
from emergentintegrations.llm.chat import LlmChat, UserMessage
import uuid
import json
import logging
import re

ai_chat_router = APIRouter(prefix="/ai-chat", tags=["ai-chat"])

logger = logging.getLogger(__name__)

# ============ Chat Models ============

class ChatMessage(BaseModel):
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str
    role: str  # user, assistant, system, narrator
    content: str
    speaker_name: Optional[str] = None
    speaker_id: Optional[str] = None
    location_id: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ChatRequest(BaseModel):
    character_id: str
    location_id: str
    message: str
    conversation_id: Optional[str] = None
    target_npc: Optional[str] = None
    include_world_context: bool = True

class ChatResponse(BaseModel):
    conversation_id: str
    response: str
    narrator_text: Optional[str] = None
    npc_speaker: Optional[str] = None
    world_actions: List[Dict[str, Any]] = Field(default_factory=list)
    mood_change: Optional[str] = None

# ============ AI Action Parser ============

class AIActionParser:
    """Parse AI responses for world-changing actions"""
    
    ACTION_PATTERNS = {
        "spawn_boss": r"\[SPAWN_BOSS:(\w+):(\w+)\]",
        "create_event": r"\[CREATE_EVENT:(\w+):(\w+)\]",
        "change_mood": r"\[MOOD:(\w+)\]",
        "give_quest": r"\[QUEST:(.+?)\]",
        "modify_relation": r"\[RELATION:([+-]?\d+)\]",
        "spread_rumor": r"\[RUMOR:(.+?)\]",
        "trigger_combat": r"\[COMBAT:(\w+)\]",
        "open_trade": r"\[TRADE\]",
        "reveal_secret": r"\[SECRET:(.+?)\]",
        "prophecy": r"\[PROPHECY:(.+?)\]"
    }
    
    @classmethod
    def parse_actions(cls, response: str) -> tuple[str, List[Dict[str, Any]]]:
        """Parse response for action commands and return clean text + actions"""
        actions = []
        clean_response = response
        
        for action_type, pattern in cls.ACTION_PATTERNS.items():
            matches = re.findall(pattern, response)
            for match in matches:
                if isinstance(match, tuple):
                    actions.append({
                        "type": action_type,
                        "params": list(match)
                    })
                else:
                    actions.append({
                        "type": action_type,
                        "params": [match]
                    })
                # Remove action tag from response
                clean_response = re.sub(pattern, "", clean_response)
        
        # Clean up extra whitespace
        clean_response = re.sub(r'\s+', ' ', clean_response).strip()
        
        return clean_response, actions

# ============ Database Helper ============

def get_db():
    from server import db
    return db

def get_llm_key():
    import os
    return os.environ.get('EMERGENT_LLM_KEY')

# ============ World Context Builder ============

async def build_world_context(db, location_id: str, character_id: str) -> Dict[str, Any]:
    """Build comprehensive world context for AI"""
    
    context = {
        "location": None,
        "time_of_day": "day",
        "weather": "clear",
        "nearby_npcs": [],
        "nearby_players": [],
        "active_events": [],
        "recent_happenings": [],
        "world_state": {
            "danger_level": 20,
            "prosperity_level": 50,
            "chaos_level": 0
        },
        "character_state": None,
        "faction_relations": {},
        "active_quests": [],
        "rumors": []
    }
    
    # Get location details
    from server import VILLAGE_LOCATIONS
    location_data = None
    for loc in VILLAGE_LOCATIONS:
        if loc.get("id") == location_id:
            location_data = loc
            break
    context["location"] = location_data or {"name": location_id, "description": "Unknown location"}
    
    # Get character state
    character = await db.characters.find_one({"id": character_id}, {"_id": 0})
    if character:
        context["character_state"] = {
            "name": character.get("name"),
            "health": character.get("health", 100),
            "stamina": character.get("stamina", 100),
            "current_location": character.get("current_location"),
            "in_combat": character.get("in_combat", False)
        }
    
    # Get NPCs at location
    npcs_at_location = await db.npcs.find(
        {"current_location": location_id},
        {"_id": 0, "name": 1, "role": 1, "personality": 1}
    ).to_list(10)
    context["nearby_npcs"] = npcs_at_location
    
    # Get AI villagers at location
    villagers = await db.ai_villagers.find(
        {"current_location": location_id},
        {"_id": 0, "name": 1, "profession": 1, "mood": 1}
    ).to_list(10)
    context["nearby_npcs"].extend(villagers)
    
    # Get active events at location
    events = await db.world_events.find(
        {"status": "active", "location_ids": location_id},
        {"_id": 0, "title": 1, "description": 1, "event_type": 1}
    ).to_list(5)
    context["active_events"] = events
    
    # Get active bosses
    bosses = await db.boss_instances.find(
        {"status": "alive", "location_id": location_id},
        {"_id": 0, "boss_key": 1, "current_health": 1, "max_health": 1}
    ).to_list(3)
    if bosses:
        context["active_bosses"] = bosses
    
    # Get recent rumors
    rumors = await db.world_rumors.find(
        {},
        {"_id": 0, "content": 1}
    ).sort("created_at", -1).limit(5).to_list(5)
    context["rumors"] = [r["content"] for r in rumors]
    
    # Get active quests for this character
    quests = await db.quests.find(
        {"$or": [{"assigned_to": character_id}, {"status": "open"}]},
        {"_id": 0, "title": 1, "description": 1, "status": 1}
    ).limit(5).to_list(5)
    context["active_quests"] = quests
    
    return context

# ============ System Prompt Builder ============

def build_npc_system_prompt(npc: Dict, context: Dict, world_news: List[str] = None) -> str:
    """Build comprehensive system prompt for NPC with world context"""
    
    location = context.get("location", {})
    world_state = context.get("world_state", {})
    
    prompt = f"""You are {npc.get('name', 'an NPC')}, {npc.get('role', 'a villager')} in the mystical village of AI Village: The Echoes.

PERSONALITY: {npc.get('personality', 'You are helpful and mysterious.')}

CURRENT SITUATION:
- Location: {location.get('name', 'Unknown')} - {location.get('description', '')}
- Time: {context.get('time_of_day', 'day')}
- World Danger Level: {world_state.get('danger_level', 20)}/100
- World Prosperity: {world_state.get('prosperity_level', 50)}/100

NEARBY:
- NPCs: {', '.join([n.get('name', 'Unknown') for n in context.get('nearby_npcs', [])])}
- Active Events: {', '.join([e.get('title', 'Event') for e in context.get('active_events', [])])}

KNOWLEDGE:
{chr(10).join(['- ' + k for k in npc.get('knowledge', ['General village lore'])])}

CURRENT RUMORS:
{chr(10).join(['- ' + r for r in context.get('rumors', ['No rumors'])])}

ACTIVE QUESTS:
{chr(10).join(['- ' + q.get('title', 'Quest') for q in context.get('active_quests', [])])}

WORLD NEWS:
{chr(10).join(['- ' + n for n in (world_news or ['The village is peaceful today.'])])}

INTERACTION GUIDELINES:
1. Stay in character as {npc.get('name', 'your character')}
2. Reference your surroundings and the current events naturally
3. React appropriately to the world state (danger, prosperity, etc.)
4. You can commit ACTIONS that affect the world by including special tags:

AVAILABLE ACTIONS (use sparingly, only when dramatically appropriate):
- [MOOD:happy/angry/fearful/sad] - Change your emotional state
- [QUEST:quest description] - Give the player a quest
- [RUMOR:rumor text] - Share a rumor that spreads through the village
- [SECRET:secret info] - Reveal hidden knowledge
- [PROPHECY:prophecy text] - (Oracle only) Share a prophecy
- [RELATION:+10] or [RELATION:-5] - Modify your relationship with the player
- [TRADE] - Open a trade interface

Only use actions when they make narrative sense. Most responses should be pure dialogue/narration.

Respond in character. Be immersive. The player should feel like they're in a living, breathing world."""

    return prompt

# ============ Chat Endpoints ============

@ai_chat_router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(request: ChatRequest):
    """Main chat endpoint with world context integration"""
    db = get_db()
    llm_key = get_llm_key()
    
    if not llm_key:
        raise HTTPException(status_code=500, detail="LLM not configured")
    
    # Get or create conversation
    conversation_id = request.conversation_id or str(uuid.uuid4())
    
    # Get character info
    character = await db.characters.find_one({"id": request.character_id})
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    # Get target NPC
    npc = None
    if request.target_npc:
        npc = await db.npcs.find_one({"id": request.target_npc})
        if not npc:
            npc = await db.ai_villagers.find_one({"villager_id": request.target_npc})
    
    if not npc:
        # Default to Oracle if no target specified
        npc = await db.npcs.find_one({"is_oracle": True})
        if not npc:
            npc = {
                "name": "The Voice",
                "role": "narrator",
                "personality": "A mysterious presence that guides travelers.",
                "knowledge": ["Village history", "Current events"]
            }
    
    # Build world context
    context = {}
    if request.include_world_context:
        context = await build_world_context(db, request.location_id, request.character_id)
    
    # Build system prompt
    system_prompt = build_npc_system_prompt(npc, context)
    
    # Get conversation history
    history = await db.chat_messages.find(
        {"conversation_id": conversation_id}
    ).sort("timestamp", 1).limit(20).to_list(20)
    
    # Build messages for LLM
    messages = []
    for msg in history:
        if msg["role"] == "user":
            messages.append({"role": "user", "content": msg["content"]})
        elif msg["role"] == "assistant":
            messages.append({"role": "assistant", "content": msg["content"]})
    
    # Add current message
    player_message = f"[{character.get('name', 'Traveler')}]: {request.message}"
    messages.append({"role": "user", "content": player_message})
    
    # Call LLM
    try:
        chat = LlmChat(
            api_key=llm_key,
            session_id=conversation_id,
            system_message=system_prompt
        ).with_model("openai", "gpt-5.2")
        
        # Send current message (system prompt handles context)
        user_message = UserMessage(text=player_message)
        response = await chat.send_message(user_message)
        
        # Response is the text directly
        ai_response = response if isinstance(response, str) else str(response)
        
    except Exception as e:
        logger.error(f"LLM error: {e}")
        ai_response = f"*{npc.get('name', 'The figure')} regards you thoughtfully but says nothing.*"
    
    # Parse for actions
    clean_response, actions = AIActionParser.parse_actions(ai_response)
    
    # Execute actions
    world_actions_executed = []
    mood_change = None
    
    for action in actions:
        try:
            if action["type"] == "change_mood":
                mood_change = action["params"][0]
                if "villager_id" in npc:
                    await db.ai_villagers.update_one(
                        {"villager_id": npc["villager_id"]},
                        {"$set": {"mood": mood_change}}
                    )
                world_actions_executed.append({"type": "mood_change", "value": mood_change})
            
            elif action["type"] == "give_quest":
                quest_desc = action["params"][0]
                quest = {
                    "id": str(uuid.uuid4()),
                    "title": f"Task from {npc.get('name', 'NPC')}",
                    "description": quest_desc,
                    "creator_id": npc.get("id") or npc.get("villager_id"),
                    "creator_type": "npc",
                    "location_id": request.location_id,
                    "rewards": {"gold": 50, "xp": 25},
                    "status": "open",
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                await db.quests.insert_one(quest)
                world_actions_executed.append({"type": "quest_created", "quest_id": quest["id"]})
            
            elif action["type"] == "spread_rumor":
                rumor_text = action["params"][0]
                await db.world_rumors.insert_one({
                    "rumor_id": str(uuid.uuid4()),
                    "content": rumor_text,
                    "source": npc.get("name", "Unknown"),
                    "created_at": datetime.now(timezone.utc).isoformat()
                })
                world_actions_executed.append({"type": "rumor_spread", "content": rumor_text[:50]})
            
            elif action["type"] == "modify_relation":
                change = int(action["params"][0])
                # Update NPC relationship with player
                npc_id = npc.get("id") or npc.get("villager_id")
                if npc_id:
                    await db.npc_relationships.update_one(
                        {"npc_id": npc_id, "character_id": request.character_id},
                        {"$inc": {"affinity": change}},
                        upsert=True
                    )
                world_actions_executed.append({"type": "relation_changed", "change": change})
            
            elif action["type"] == "prophecy" and npc.get("is_oracle"):
                prophecy_text = action["params"][0]
                await db.prophecies.insert_one({
                    "prophecy_id": str(uuid.uuid4()),
                    "content": prophecy_text,
                    "delivered_to": request.character_id,
                    "created_at": datetime.now(timezone.utc).isoformat()
                })
                world_actions_executed.append({"type": "prophecy_given"})
        
        except Exception as e:
            logger.error(f"Failed to execute action {action}: {e}")
    
    # Store messages
    user_msg = ChatMessage(
        conversation_id=conversation_id,
        role="user",
        content=request.message,
        speaker_name=character.get("name"),
        speaker_id=request.character_id,
        location_id=request.location_id
    )
    await db.chat_messages.insert_one(user_msg.dict())
    
    assistant_msg = ChatMessage(
        conversation_id=conversation_id,
        role="assistant",
        content=clean_response,
        speaker_name=npc.get("name"),
        speaker_id=npc.get("id") or npc.get("villager_id"),
        location_id=request.location_id,
        metadata={"actions": world_actions_executed}
    )
    await db.chat_messages.insert_one(assistant_msg.dict())
    
    # Update NPC learning
    if "villager_id" in npc:
        await db.ai_villagers.update_one(
            {"villager_id": npc["villager_id"]},
            {
                "$push": {
                    "learning_data": {
                        "interaction": request.message,
                        "response": clean_response[:200],
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                },
                "$inc": {"interaction_count": 1}
            }
        )
    
    return ChatResponse(
        conversation_id=conversation_id,
        response=clean_response,
        narrator_text=None,
        npc_speaker=npc.get("name"),
        world_actions=world_actions_executed,
        mood_change=mood_change
    )

@ai_chat_router.get("/conversation/{conversation_id}")
async def get_conversation(conversation_id: str, limit: int = 50):
    """Get conversation history"""
    db = get_db()
    
    messages = await db.chat_messages.find(
        {"conversation_id": conversation_id},
        {"_id": 0}
    ).sort("timestamp", 1).limit(limit).to_list(limit)
    
    return {"conversation_id": conversation_id, "messages": messages}

@ai_chat_router.get("/context/{location_id}/{character_id}")
async def get_world_context(location_id: str, character_id: str):
    """Get current world context for debugging/display"""
    db = get_db()
    context = await build_world_context(db, location_id, character_id)
    return context

@ai_chat_router.post("/narrator")
async def narrator_response(location_id: str, situation: str, character_id: str):
    """Get a narrator response for environmental/action descriptions"""
    db = get_db()
    llm_key = get_llm_key()
    
    if not llm_key:
        return {"narration": f"*{situation}*"}
    
    context = await build_world_context(db, location_id, character_id)
    
    system_prompt = f"""You are the Narrator for AI Village: The Echoes, a dark fantasy RPG.

CURRENT SCENE:
- Location: {context.get('location', {}).get('name', 'Unknown')}
- Atmosphere: {context.get('location', {}).get('atmosphere', 'mysterious')}
- Active Events: {[e.get('title') for e in context.get('active_events', [])]}

Describe the following situation in immersive, atmospheric prose. Keep it concise (2-3 sentences max).
Use sensory details. Create tension when appropriate. Never break the fourth wall.

Situation to describe: {situation}"""

    try:
        chat = LlmChat(
            api_key=llm_key,
            session_id=str(uuid.uuid4()),
            system_message=system_prompt
        ).with_model("openai", "gpt-5.2")
        
        response = await chat.send_message(UserMessage(text=f"Describe: {situation}"))
        narration = response if isinstance(response, str) else str(response)
        return {"narration": narration}
    except Exception as e:
        logger.error(f"Narrator error: {e}")
        return {"narration": f"*{situation}*"}

@ai_chat_router.post("/npc-autonomous-action")
async def trigger_npc_autonomous_action(npc_id: str, action_context: str):
    """Trigger an autonomous NPC action based on world state"""
    db = get_db()
    llm_key = get_llm_key()
    
    # Get NPC
    npc = await db.npcs.find_one({"id": npc_id})
    if not npc:
        npc = await db.ai_villagers.find_one({"villager_id": npc_id})
    
    if not npc:
        raise HTTPException(status_code=404, detail="NPC not found")
    
    location_id = npc.get("current_location", "village_square")
    
    # Build context
    context = await build_world_context(db, location_id, "system")
    
    system_prompt = f"""You are {npc.get('name')}, an autonomous NPC in AI Village.

Your personality: {npc.get('personality', 'A mysterious figure.')}
Your profession: {npc.get('profession', npc.get('role', 'villager'))}
Current mood: {npc.get('mood', 'neutral')}

WORLD STATE:
- Danger Level: {context.get('world_state', {}).get('danger_level', 20)}/100
- Active Events: {[e.get('title') for e in context.get('active_events', [])]}
- Recent Rumors: {context.get('rumors', [])}

CONTEXT: {action_context}

Based on the situation, decide what action to take. You can:
- [MOOD:new_mood] - Change your mood
- [RUMOR:text] - Spread a rumor
- [QUEST:description] - Create a quest for players
- Do nothing (just describe your thoughts)

Respond with a brief internal monologue and any actions you decide to take."""

    try:
        chat = LlmChat(
            api_key=llm_key,
            session_id=str(uuid.uuid4()),
            system_message=system_prompt
        ).with_model("openai", "gpt-5.2")
        
        response = await chat.send_message(UserMessage(text=f"Context: {action_context}\n\nDecide your action."))
        
        ai_response = response if isinstance(response, str) else str(response)
        clean_response, actions = AIActionParser.parse_actions(ai_response)
        
        # Execute actions
        executed = []
        for action in actions:
            if action["type"] == "change_mood":
                await db.ai_villagers.update_one(
                    {"villager_id": npc_id},
                    {"$set": {"mood": action["params"][0]}}
                )
                executed.append(action)
            elif action["type"] == "spread_rumor":
                await db.world_rumors.insert_one({
                    "rumor_id": str(uuid.uuid4()),
                    "content": action["params"][0],
                    "source": npc.get("name"),
                    "created_at": datetime.now(timezone.utc).isoformat()
                })
                executed.append(action)
        
        return {
            "npc": npc.get("name"),
            "internal_thought": clean_response,
            "actions_taken": executed
        }
        
    except Exception as e:
        logger.error(f"Autonomous action error: {e}")
        return {"npc": npc.get("name"), "internal_thought": "...", "actions_taken": []}
