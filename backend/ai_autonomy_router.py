# AI Autonomy Router - AI-to-AI Conversations & Free Will System
# Enables NPCs to converse, make decisions, and shape the world autonomously

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone
import uuid
import logging
import random
import asyncio
import os

ai_autonomy_router = APIRouter(prefix="/ai-autonomy", tags=["ai-autonomy"])

logger = logging.getLogger(__name__)

# ============ NPC Personality Traits ============

PERSONALITY_TRAITS = {
    "cooperative": {"weight": 1.0, "affects": ["alliance", "trade", "help"]},
    "aggressive": {"weight": 1.0, "affects": ["conflict", "intimidate", "expand"]},
    "curious": {"weight": 1.0, "affects": ["explore", "investigate", "learn"]},
    "creative": {"weight": 1.0, "affects": ["build", "craft", "innovate"]},
    "social": {"weight": 1.0, "affects": ["converse", "gather", "celebrate"]},
    "territorial": {"weight": 1.0, "affects": ["defend", "claim", "fortify"]},
    "mercantile": {"weight": 1.0, "affects": ["trade", "profit", "negotiate"]},
    "spiritual": {"weight": 1.0, "affects": ["ritual", "prophecy", "meditate"]},
}

# ============ Autonomous Actions NPCs Can Take ============

AUTONOMOUS_ACTIONS = {
    # Social
    "initiate_conversation": {"category": "social", "cost": 0, "cooldown": 300},
    "form_alliance": {"category": "social", "cost": 100, "cooldown": 3600},
    "break_alliance": {"category": "social", "cost": 50, "cooldown": 7200},
    "declare_friendship": {"category": "social", "cost": 0, "cooldown": 1800},
    
    # Conflict
    "start_conflict": {"category": "conflict", "cost": 200, "cooldown": 7200},
    "resolve_conflict": {"category": "conflict", "cost": 100, "cooldown": 3600},
    "defend_territory": {"category": "conflict", "cost": 50, "cooldown": 600},
    
    # Economic
    "establish_trade_route": {"category": "economic", "cost": 150, "cooldown": 3600},
    "set_prices": {"category": "economic", "cost": 0, "cooldown": 1800},
    "create_goods": {"category": "economic", "cost": 50, "cooldown": 600},
    
    # World Building
    "build_structure": {"category": "building", "cost": 500, "cooldown": 14400},
    "modify_terrain": {"category": "building", "cost": 300, "cooldown": 7200},
    "create_landmark": {"category": "building", "cost": 1000, "cooldown": 86400},
    "destroy_structure": {"category": "building", "cost": 200, "cooldown": 7200},
    
    # Movement
    "relocate": {"category": "movement", "cost": 0, "cooldown": 1800},
    "explore_area": {"category": "movement", "cost": 0, "cooldown": 600},
    "claim_territory": {"category": "movement", "cost": 100, "cooldown": 3600},
    
    # Knowledge
    "share_knowledge": {"category": "knowledge", "cost": 0, "cooldown": 600},
    "learn_skill": {"category": "knowledge", "cost": 50, "cooldown": 1800},
    "teach_skill": {"category": "knowledge", "cost": 0, "cooldown": 1200},
    
    # Events
    "host_event": {"category": "events", "cost": 200, "cooldown": 14400},
    "join_event": {"category": "events", "cost": 0, "cooldown": 600},
    "create_quest": {"category": "events", "cost": 100, "cooldown": 7200},
}

# ============ Models ============

class NPCState(BaseModel):
    npc_id: str
    name: str
    personality: Dict[str, float] = Field(default_factory=dict)  # trait: weight
    free_will: float = 0.5  # 0-1, how autonomous the NPC is
    memory_strength: float = 0.7  # 0-1, how well they remember
    current_goals: List[str] = Field(default_factory=list)
    relationships: Dict[str, Dict[str, Any]] = Field(default_factory=dict)  # entity_id: {type, strength, history}
    resources: Dict[str, int] = Field(default_factory=dict)
    location: str = "village_square"
    last_action: Optional[str] = None
    last_action_time: Optional[str] = None
    action_cooldowns: Dict[str, str] = Field(default_factory=dict)

class AIConversation(BaseModel):
    conversation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    participants: List[str]  # NPC IDs
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    topic: Optional[str] = None
    location: str
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ended_at: Optional[str] = None
    outcomes: List[Dict[str, Any]] = Field(default_factory=list)  # Decisions made during conversation
    is_active: bool = True

class WorldChange(BaseModel):
    change_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    initiator_id: str
    initiator_type: str  # "npc" or "player"
    action: str
    target: Optional[str] = None
    location: str
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    approved: bool = True
    reverted: bool = False

class ConversationStart(BaseModel):
    initiator_id: str
    target_id: str
    topic: Optional[str] = None
    location: str

class AutonomousActionRequest(BaseModel):
    npc_id: str
    action: Optional[str] = None  # If None, NPC chooses based on personality

class WorldBuildRequest(BaseModel):
    entity_id: str
    entity_type: str = "player"
    action: str  # build_structure, modify_terrain, etc.
    location: str
    details: Dict[str, Any]

# ============ Database Helper ============

def get_db():
    from server import db
    return db

# ============ AI Conversation Generation ============

async def generate_npc_message(npc_state: Dict, context: Dict, conversation_history: List[Dict]) -> str:
    """Generate NPC message using LLM"""
    try:
        from emergentintegrations.llm.chat import LlmChat
        
        personality_desc = ", ".join([f"{k}: {v:.1f}" for k, v in npc_state.get("personality", {}).items()])
        
        system_prompt = f"""You are {npc_state.get('name', 'an NPC')} in AI Village: The Echoes.
Your personality traits: {personality_desc}
Free will level: {npc_state.get('free_will', 0.5):.1%}
Current location: {context.get('location', 'unknown')}
Topic: {context.get('topic', 'general conversation')}

You are having a conversation with another NPC. Respond naturally based on your personality.
Keep responses concise (1-3 sentences). You can make decisions, form opinions, and take actions.
If you want to take an action, end your message with [ACTION: action_name]"""

        # Build conversation context
        history_text = "\n".join([
            f"{msg.get('speaker', 'Unknown')}: {msg.get('content', '')}"
            for msg in conversation_history[-10:]  # Last 10 messages
        ])
        
        user_message = f"Conversation so far:\n{history_text}\n\nRespond as {npc_state.get('name')}:"
        
        chat = LlmChat(
            api_key=os.environ.get("LLM_API_KEY"),
            session_id=f"npc-conv-{npc_state.get('npc_id', 'unknown')}",
            system_message=system_prompt
        )
        
        response = await asyncio.to_thread(
            chat.send_message,
            user_message
        )
        
        return response.get("response", "...")
        
    except Exception as e:
        logger.error(f"NPC message generation error: {e}")
        # Fallback responses based on personality
        if npc_state.get("personality", {}).get("aggressive", 0) > 0.7:
            return random.choice(["Hmph. What do you want?", "Get to the point.", "I have better things to do."])
        elif npc_state.get("personality", {}).get("social", 0) > 0.7:
            return random.choice(["How wonderful to see you!", "Tell me more!", "Isn't this lovely?"])
        else:
            return random.choice(["I see.", "Interesting.", "Go on..."])

async def decide_autonomous_action(npc_state: Dict) -> Optional[str]:
    """NPC decides what autonomous action to take based on personality and state"""
    
    free_will = npc_state.get("free_will", 0.5)
    
    # Low free will = less likely to act autonomously
    if random.random() > free_will:
        return None
    
    personality = npc_state.get("personality", {})
    resources = npc_state.get("resources", {})
    cooldowns = npc_state.get("action_cooldowns", {})
    
    now = datetime.now(timezone.utc)
    
    # Score each possible action
    action_scores = {}
    
    for action, action_data in AUTONOMOUS_ACTIONS.items():
        # Check cooldown
        if action in cooldowns:
            cooldown_end = datetime.fromisoformat(cooldowns[action])
            if now < cooldown_end:
                continue
        
        # Check cost
        cost = action_data.get("cost", 0)
        if cost > resources.get("currency", 0):
            continue
        
        # Score based on personality
        category = action_data.get("category", "")
        score = 0.5  # Base score
        
        for trait, trait_data in PERSONALITY_TRAITS.items():
            if category in trait_data.get("affects", []):
                score += personality.get(trait, 0) * 0.3
        
        # Add some randomness
        score += random.uniform(-0.2, 0.2)
        
        action_scores[action] = max(0, score)
    
    if not action_scores:
        return None
    
    # Choose action probabilistically
    total = sum(action_scores.values())
    if total == 0:
        return None
    
    r = random.uniform(0, total)
    cumulative = 0
    for action, score in action_scores.items():
        cumulative += score
        if r <= cumulative:
            return action
    
    return None

# ============ Endpoints ============

@ai_autonomy_router.get("/npc/{npc_id}/state")
async def get_npc_state(npc_id: str):
    """Get the current autonomous state of an NPC"""
    db = get_db()
    
    state = await db.npc_autonomy.find_one({"npc_id": npc_id}, {"_id": 0})
    
    if not state:
        # Initialize NPC with random personality
        state = NPCState(
            npc_id=npc_id,
            name=npc_id,
            personality={
                trait: random.uniform(0.2, 0.8)
                for trait in PERSONALITY_TRAITS
            },
            free_will=random.uniform(0.3, 0.8),
            memory_strength=random.uniform(0.5, 0.9),
            resources={"currency": 100, "materials": 50}
        ).dict()
        await db.npc_autonomy.insert_one(state)
        # Remove _id after insert
        state.pop("_id", None)
    
    return state

@ai_autonomy_router.post("/npc/{npc_id}/set-personality")
async def set_npc_personality(npc_id: str, personality: Dict[str, float], free_will: float = 0.5):
    """Set NPC personality traits and free will"""
    db = get_db()
    
    await db.npc_autonomy.update_one(
        {"npc_id": npc_id},
        {
            "$set": {
                "personality": personality,
                "free_will": max(0, min(1, free_will)),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        },
        upsert=True
    )
    
    return {"updated": True, "npc_id": npc_id, "free_will": free_will}

@ai_autonomy_router.post("/conversation/start")
async def start_ai_conversation(data: ConversationStart, background_tasks: BackgroundTasks):
    """Start a conversation between two NPCs"""
    db = get_db()
    
    # Get both NPC states
    initiator = await db.npc_autonomy.find_one({"npc_id": data.initiator_id})
    target = await db.npc_autonomy.find_one({"npc_id": data.target_id})
    
    if not initiator:
        initiator = (await get_npc_state(data.initiator_id))
    if not target:
        target = (await get_npc_state(data.target_id))
    
    # Create conversation
    conversation = AIConversation(
        participants=[data.initiator_id, data.target_id],
        topic=data.topic,
        location=data.location
    )
    
    await db.ai_conversations.insert_one(conversation.dict())
    
    # Generate initial message from initiator
    initial_message = await generate_npc_message(
        initiator,
        {"location": data.location, "topic": data.topic},
        []
    )
    
    # Add first message
    await db.ai_conversations.update_one(
        {"conversation_id": conversation.conversation_id},
        {"$push": {"messages": {
            "speaker": initiator.get("name", data.initiator_id),
            "speaker_id": data.initiator_id,
            "content": initial_message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }}}
    )
    
    return {
        "conversation_id": conversation.conversation_id,
        "participants": [initiator.get("name"), target.get("name")],
        "initial_message": initial_message,
        "topic": data.topic,
        "location": data.location
    }

@ai_autonomy_router.post("/conversation/{conversation_id}/continue")
async def continue_ai_conversation(conversation_id: str, rounds: int = 1):
    """Continue an AI-to-AI conversation for N rounds"""
    db = get_db()
    
    conversation = await db.ai_conversations.find_one(
        {"conversation_id": conversation_id},
        {"_id": 0}
    )
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if not conversation.get("is_active", True):
        raise HTTPException(status_code=400, detail="Conversation has ended")
    
    participants = conversation.get("participants", [])
    messages = conversation.get("messages", [])
    
    new_messages = []
    outcomes = []
    
    for _ in range(rounds):
        for participant_id in participants:
            # Get NPC state
            npc_state = await db.npc_autonomy.find_one({"npc_id": participant_id})
            if not npc_state:
                continue
            
            # Generate message
            response = await generate_npc_message(
                npc_state,
                {
                    "location": conversation.get("location"),
                    "topic": conversation.get("topic")
                },
                messages + new_messages
            )
            
            # Check for actions in response
            action = None
            if "[ACTION:" in response:
                action_start = response.find("[ACTION:") + 8
                action_end = response.find("]", action_start)
                if action_end > action_start:
                    action = response[action_start:action_end].strip()
                    response = response[:response.find("[ACTION:")].strip()
                    outcomes.append({
                        "actor": participant_id,
                        "action": action,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
            
            new_message = {
                "speaker": npc_state.get("name", participant_id),
                "speaker_id": participant_id,
                "content": response,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": action
            }
            new_messages.append(new_message)
            
            # Award skill XP for conversation
            await db.entity_skills.update_one(
                {"entity_id": participant_id, "entity_type": "npc"},
                {
                    "$inc": {
                        "skills.diplomacy.xp": random.randint(1, 3),
                        "skills.charm.xp": random.randint(1, 2)
                    }
                },
                upsert=True
            )
    
    # Update conversation
    await db.ai_conversations.update_one(
        {"conversation_id": conversation_id},
        {
            "$push": {
                "messages": {"$each": new_messages},
                "outcomes": {"$each": outcomes}
            }
        }
    )
    
    return {
        "conversation_id": conversation_id,
        "new_messages": new_messages,
        "outcomes": outcomes,
        "total_messages": len(messages) + len(new_messages)
    }

@ai_autonomy_router.post("/conversation/{conversation_id}/end")
async def end_ai_conversation(conversation_id: str):
    """End an AI-to-AI conversation"""
    db = get_db()
    
    await db.ai_conversations.update_one(
        {"conversation_id": conversation_id},
        {
            "$set": {
                "is_active": False,
                "ended_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Get final conversation
    conversation = await db.ai_conversations.find_one(
        {"conversation_id": conversation_id},
        {"_id": 0}
    )
    
    return {
        "ended": True,
        "conversation_id": conversation_id,
        "total_messages": len(conversation.get("messages", [])),
        "outcomes": conversation.get("outcomes", [])
    }

@ai_autonomy_router.get("/conversations/active")
async def get_active_conversations(location: Optional[str] = None, limit: int = 20):
    """Get active AI-to-AI conversations"""
    db = get_db()
    
    query = {"is_active": True}
    if location:
        query["location"] = location
    
    conversations = await db.ai_conversations.find(
        query,
        {"_id": 0}
    ).sort("started_at", -1).limit(limit).to_list(limit)
    
    return {"conversations": conversations, "count": len(conversations)}

@ai_autonomy_router.post("/npc/{npc_id}/act")
async def npc_autonomous_action(npc_id: str, data: Optional[AutonomousActionRequest] = None):
    """Have an NPC take an autonomous action"""
    db = get_db()
    
    npc_state = await db.npc_autonomy.find_one({"npc_id": npc_id})
    if not npc_state:
        npc_state = (await get_npc_state(npc_id))
    
    # Determine action
    action = None
    if data and data.action:
        action = data.action
    else:
        action = await decide_autonomous_action(npc_state)
    
    if not action:
        return {"acted": False, "reason": "No suitable action found"}
    
    if action not in AUTONOMOUS_ACTIONS:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}")
    
    action_data = AUTONOMOUS_ACTIONS[action]
    cost = action_data.get("cost", 0)
    cooldown = action_data.get("cooldown", 0)
    
    # Check resources
    if cost > npc_state.get("resources", {}).get("currency", 0):
        return {"acted": False, "reason": "Insufficient resources"}
    
    # Apply action
    now = datetime.now(timezone.utc)
    cooldown_end = (now + __import__('datetime').timedelta(seconds=cooldown)).isoformat()
    
    # Record world change
    change = WorldChange(
        initiator_id=npc_id,
        initiator_type="npc",
        action=action,
        location=npc_state.get("location", "unknown"),
        details={
            "personality": npc_state.get("personality"),
            "free_will": npc_state.get("free_will")
        }
    )
    
    await db.world_changes.insert_one(change.dict())
    
    # Update NPC state
    await db.npc_autonomy.update_one(
        {"npc_id": npc_id},
        {
            "$inc": {"resources.currency": -cost},
            "$set": {
                "last_action": action,
                "last_action_time": now.isoformat(),
                f"action_cooldowns.{action}": cooldown_end
            }
        }
    )
    
    return {
        "acted": True,
        "npc_id": npc_id,
        "action": action,
        "cost": cost,
        "cooldown_ends": cooldown_end,
        "world_change_id": change.change_id
    }

@ai_autonomy_router.post("/world/change")
async def apply_world_change(data: WorldBuildRequest):
    """Apply a world change from player or NPC"""
    db = get_db()
    
    if data.action not in AUTONOMOUS_ACTIONS:
        raise HTTPException(status_code=400, detail=f"Unknown action: {data.action}")
    
    action_data = AUTONOMOUS_ACTIONS[data.action]
    
    # Record the change
    change = WorldChange(
        initiator_id=data.entity_id,
        initiator_type=data.entity_type,
        action=data.action,
        location=data.location,
        details=data.details
    )
    
    await db.world_changes.insert_one(change.dict())
    
    # Update world state
    if data.action == "build_structure":
        await db.world_structures.insert_one({
            "structure_id": str(uuid.uuid4()),
            "type": data.details.get("type", "building"),
            "name": data.details.get("name", "Structure"),
            "location": data.location,
            "builder_id": data.entity_id,
            "builder_type": data.entity_type,
            "built_at": datetime.now(timezone.utc).isoformat(),
            "properties": data.details.get("properties", {})
        })
    
    # Award skills
    if data.entity_type == "player":
        from skills_router import ACTION_SKILL_GAINS
        if "build" in data.action:
            await db.entity_skills.update_one(
                {"entity_id": data.entity_id, "entity_type": "player"},
                {"$inc": {"skills.engineering.xp": random.randint(10, 30)}},
                upsert=True
            )
    
    return {
        "applied": True,
        "change_id": change.change_id,
        "action": data.action,
        "location": data.location
    }

@ai_autonomy_router.get("/world/changes")
async def get_world_changes(location: Optional[str] = None, limit: int = 50):
    """Get recent world changes"""
    db = get_db()
    
    query = {"reverted": False}
    if location:
        query["location"] = location
    
    changes = await db.world_changes.find(
        query,
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    
    return {"changes": changes, "count": len(changes)}

@ai_autonomy_router.get("/world/structures")
async def get_world_structures(location: Optional[str] = None):
    """Get structures built in the world"""
    db = get_db()
    
    query = {}
    if location:
        query["location"] = location
    
    structures = await db.world_structures.find(
        query,
        {"_id": 0}
    ).to_list(100)
    
    return {"structures": structures, "count": len(structures)}

@ai_autonomy_router.get("/npc/relationships/{npc_id}")
async def get_npc_relationships(npc_id: str):
    """Get all relationships for an NPC"""
    db = get_db()
    
    npc_state = await db.npc_autonomy.find_one({"npc_id": npc_id}, {"_id": 0})
    
    if not npc_state:
        return {"relationships": {}, "npc_id": npc_id}
    
    return {
        "npc_id": npc_id,
        "relationships": npc_state.get("relationships", {}),
        "personality": npc_state.get("personality", {})
    }

@ai_autonomy_router.post("/npc/{npc_id}/relationship")
async def update_npc_relationship(npc_id: str, target_id: str, relationship_type: str, strength: float):
    """Update relationship between NPCs"""
    db = get_db()
    
    await db.npc_autonomy.update_one(
        {"npc_id": npc_id},
        {
            "$set": {
                f"relationships.{target_id}": {
                    "type": relationship_type,
                    "strength": max(-1, min(1, strength)),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        },
        upsert=True
    )
    
    return {"updated": True, "npc_id": npc_id, "target_id": target_id, "type": relationship_type}

@ai_autonomy_router.get("/stats")
async def get_autonomy_stats():
    """Get overall AI autonomy statistics"""
    db = get_db()
    
    npc_count = await db.npc_autonomy.count_documents({})
    active_convs = await db.ai_conversations.count_documents({"is_active": True})
    total_changes = await db.world_changes.count_documents({})
    structures = await db.world_structures.count_documents({})
    
    # Get most active NPCs
    pipeline = [
        {"$project": {"npc_id": 1, "name": 1, "free_will": 1}},
        {"$sort": {"free_will": -1}},
        {"$limit": 5}
    ]
    most_autonomous = await db.npc_autonomy.aggregate(pipeline).to_list(5)
    
    return {
        "total_autonomous_npcs": npc_count,
        "active_ai_conversations": active_convs,
        "total_world_changes": total_changes,
        "structures_built": structures,
        "most_autonomous_npcs": most_autonomous
    }
