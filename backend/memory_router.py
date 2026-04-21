# Persistent Memory System - Foundation for AI Learning & Ecosystem Growth
# Tracks user memories, AI memories, and enables cross-entity learning

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone
from enum import Enum
import uuid
import logging

memory_router = APIRouter(prefix="/memory", tags=["memory"])

logger = logging.getLogger(__name__)

# ============ Memory Types ============

class MemoryType(str, Enum):
    # User Memory Types
    USER_INTERACTION = "user_interaction"      # User's interactions with NPCs/world
    USER_PREFERENCE = "user_preference"        # User's play style, choices
    USER_ACHIEVEMENT = "user_achievement"      # Milestones, accomplishments
    USER_RELATIONSHIP = "user_relationship"    # Relationship with NPCs/factions
    USER_KNOWLEDGE = "user_knowledge"          # Things user has discovered
    USER_EMOTION = "user_emotion"              # Emotional states, reactions
    
    # AI Memory Types
    AI_LEARNED_BEHAVIOR = "ai_learned_behavior"    # Patterns learned from interactions
    AI_WORLD_KNOWLEDGE = "ai_world_knowledge"      # Knowledge about world state
    AI_PLAYER_MODEL = "ai_player_model"            # Understanding of specific players
    AI_CONVERSATION = "ai_conversation"            # Important conversation snippets
    AI_RELATIONSHIP = "ai_relationship"            # AI's relationships with players
    AI_PREDICTION = "ai_prediction"                # Predictions about player behavior
    AI_EMOTION = "ai_emotion"                      # AI's emotional memory
    
    # Ecosystem Memory Types
    ECO_WORLD_EVENT = "eco_world_event"            # Major world events
    ECO_COLLECTIVE = "eco_collective"              # Collective player behavior patterns
    ECO_EVOLUTION = "eco_evolution"                # AI evolution milestones
    ECO_CULTURAL = "eco_cultural"                  # Emerging cultural patterns

class MemoryImportance(str, Enum):
    TRIVIAL = "trivial"          # May be forgotten (score 1-2)
    MINOR = "minor"              # Weak retention (score 3-4)
    MODERATE = "moderate"        # Standard retention (score 5-6)
    SIGNIFICANT = "significant"  # Strong retention (score 7-8)
    CRITICAL = "critical"        # Never forgotten (score 9-10)

# ============ Models ============

class Memory(BaseModel):
    memory_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    entity_type: str  # "user", "ai_npc", "ai_villager", "ecosystem"
    entity_id: str
    memory_type: MemoryType
    importance: MemoryImportance = MemoryImportance.MODERATE
    importance_score: float = Field(default=5.0, ge=0, le=10)
    
    # Memory content
    content: str  # Natural language description
    structured_data: Dict[str, Any] = Field(default_factory=dict)
    
    # Context
    location_id: Optional[str] = None
    related_entities: List[str] = Field(default_factory=list)  # Other entities involved
    tags: List[str] = Field(default_factory=list)
    
    # Temporal
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_accessed: Optional[str] = None
    access_count: int = 0
    
    # Decay and reinforcement
    decay_rate: float = 0.01  # How fast memory fades (0 = never, 1 = instant)
    reinforcement_count: int = 0  # Times memory was reinforced
    current_strength: float = 1.0  # Current memory strength (0-1)
    
    # Associations
    associated_memories: List[str] = Field(default_factory=list)  # Memory IDs
    emotional_valence: float = 0.0  # -1 (negative) to +1 (positive)

class MemoryCreate(BaseModel):
    entity_type: str
    entity_id: str
    memory_type: MemoryType
    content: str
    importance: MemoryImportance = MemoryImportance.MODERATE
    structured_data: Dict[str, Any] = Field(default_factory=dict)
    location_id: Optional[str] = None
    related_entities: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    emotional_valence: float = 0.0

class MemoryQuery(BaseModel):
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    memory_types: Optional[List[MemoryType]] = None
    min_importance: Optional[float] = None
    tags: Optional[List[str]] = None
    related_to: Optional[str] = None
    location_id: Optional[str] = None
    limit: int = 50

class PlayerModel(BaseModel):
    """AI's understanding of a specific player"""
    player_id: str
    player_name: str
    
    # Behavioral patterns
    play_style: str = "unknown"  # aggressive, diplomatic, explorer, builder, etc.
    decision_patterns: List[str] = Field(default_factory=list)
    typical_responses: List[str] = Field(default_factory=list)
    
    # Preferences
    preferred_locations: List[str] = Field(default_factory=list)
    favorite_npcs: List[str] = Field(default_factory=list)
    avoided_content: List[str] = Field(default_factory=list)
    
    # Emotional profile
    emotional_tendencies: Dict[str, float] = Field(default_factory=dict)
    trust_level: float = 0.5  # 0-1 how much AI trusts this player
    
    # Interaction history
    total_interactions: int = 0
    positive_interactions: int = 0
    negative_interactions: int = 0
    last_interaction: Optional[str] = None
    
    # Predictions
    predicted_next_action: Optional[str] = None
    predicted_interests: List[str] = Field(default_factory=list)

class AIEvolutionState(BaseModel):
    """Tracks AI's evolution and learning progress"""
    ai_id: str
    ai_name: str
    
    # Learning metrics
    total_memories: int = 0
    unique_players_met: int = 0
    conversations_had: int = 0
    knowledge_domains: List[str] = Field(default_factory=list)
    
    # Capability levels
    language_sophistication: float = 1.0  # 1-10
    emotional_intelligence: float = 1.0   # 1-10
    world_awareness: float = 1.0          # 1-10
    prediction_accuracy: float = 0.5      # 0-1
    
    # Evolution milestones
    milestones_reached: List[str] = Field(default_factory=list)
    evolution_points: int = 0
    
    # Personality development
    developed_traits: List[str] = Field(default_factory=list)
    personality_drift: Dict[str, float] = Field(default_factory=dict)

# ============ Database Helper ============

def get_db():
    from server import db
    return db

# ============ Importance Calculator ============

def calculate_importance_score(memory_data: MemoryCreate) -> float:
    """Calculate importance score based on various factors"""
    score = 5.0  # Base score
    
    # Importance level multiplier
    importance_multipliers = {
        MemoryImportance.TRIVIAL: 0.3,
        MemoryImportance.MINOR: 0.6,
        MemoryImportance.MODERATE: 1.0,
        MemoryImportance.SIGNIFICANT: 1.4,
        MemoryImportance.CRITICAL: 2.0
    }
    score *= importance_multipliers.get(memory_data.importance, 1.0)
    
    # Related entities boost
    if memory_data.related_entities:
        score += len(memory_data.related_entities) * 0.3
    
    # Emotional intensity boost
    emotional_intensity = abs(memory_data.emotional_valence)
    score += emotional_intensity * 2
    
    # Content length consideration (longer = potentially more important)
    if len(memory_data.content) > 200:
        score += 0.5
    
    return min(10.0, max(0.0, score))

def calculate_decay_rate(memory_type: MemoryType, importance: MemoryImportance) -> float:
    """Calculate how fast a memory should decay"""
    base_decay = {
        MemoryImportance.TRIVIAL: 0.1,
        MemoryImportance.MINOR: 0.05,
        MemoryImportance.MODERATE: 0.02,
        MemoryImportance.SIGNIFICANT: 0.01,
        MemoryImportance.CRITICAL: 0.0  # Never decays
    }
    
    # Some memory types decay slower
    slow_decay_types = [
        MemoryType.USER_ACHIEVEMENT,
        MemoryType.AI_PLAYER_MODEL,
        MemoryType.ECO_WORLD_EVENT,
        MemoryType.ECO_EVOLUTION
    ]
    
    decay = base_decay.get(importance, 0.02)
    if memory_type in slow_decay_types:
        decay *= 0.5
    
    return decay

# ============ Memory Endpoints ============

@memory_router.post("/create")
async def create_memory(memory_data: MemoryCreate):
    """Create a new memory for a user or AI"""
    db = get_db()
    
    importance_score = calculate_importance_score(memory_data)
    decay_rate = calculate_decay_rate(memory_data.memory_type, memory_data.importance)
    
    memory = Memory(
        entity_type=memory_data.entity_type,
        entity_id=memory_data.entity_id,
        memory_type=memory_data.memory_type,
        importance=memory_data.importance,
        importance_score=importance_score,
        content=memory_data.content,
        structured_data=memory_data.structured_data,
        location_id=memory_data.location_id,
        related_entities=memory_data.related_entities,
        tags=memory_data.tags,
        decay_rate=decay_rate,
        emotional_valence=memory_data.emotional_valence
    )
    
    await db.memories.insert_one(memory.dict())
    
    # Update entity's memory count for evolution tracking
    if memory_data.entity_type.startswith("ai"):
        await db.ai_evolution.update_one(
            {"ai_id": memory_data.entity_id},
            {"$inc": {"total_memories": 1}},
            upsert=True
        )
    
    # Track ecosystem memory if relevant
    if memory_data.memory_type in [MemoryType.ECO_WORLD_EVENT, MemoryType.ECO_COLLECTIVE]:
        await db.ecosystem_memories.insert_one({
            "memory_id": memory.memory_id,
            "type": memory_data.memory_type.value,
            "content": memory_data.content,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    return {"memory_id": memory.memory_id, "importance_score": importance_score}

@memory_router.post("/recall")
async def recall_memories(query: MemoryQuery):
    """Recall memories based on query parameters"""
    db = get_db()
    
    # Build query
    mongo_query = {}
    
    if query.entity_type:
        mongo_query["entity_type"] = query.entity_type
    if query.entity_id:
        mongo_query["entity_id"] = query.entity_id
    if query.memory_types:
        mongo_query["memory_type"] = {"$in": [mt.value for mt in query.memory_types]}
    if query.min_importance:
        mongo_query["importance_score"] = {"$gte": query.min_importance}
    if query.tags:
        mongo_query["tags"] = {"$in": query.tags}
    if query.related_to:
        mongo_query["related_entities"] = query.related_to
    if query.location_id:
        mongo_query["location_id"] = query.location_id
    
    # Get memories sorted by importance and recency
    memories = await db.memories.find(
        mongo_query,
        {"_id": 0}
    ).sort([
        ("importance_score", -1),
        ("created_at", -1)
    ]).limit(query.limit).to_list(query.limit)
    
    # Update access counts
    memory_ids = [m["memory_id"] for m in memories]
    if memory_ids:
        await db.memories.update_many(
            {"memory_id": {"$in": memory_ids}},
            {
                "$inc": {"access_count": 1},
                "$set": {"last_accessed": datetime.now(timezone.utc).isoformat()}
            }
        )
    
    return {"memories": memories, "count": len(memories)}

@memory_router.post("/reinforce/{memory_id}")
async def reinforce_memory(memory_id: str, strength_boost: float = 0.2):
    """Reinforce a memory (makes it stronger, less likely to decay)"""
    db = get_db()
    
    result = await db.memories.update_one(
        {"memory_id": memory_id},
        {
            "$inc": {"reinforcement_count": 1},
            "$set": {
                "current_strength": min(1.0, 1.0),  # Reset to full strength
                "last_accessed": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Memory not found")
    
    return {"reinforced": True, "memory_id": memory_id}

@memory_router.post("/associate")
async def associate_memories(memory_id_1: str, memory_id_2: str):
    """Create an association between two memories"""
    db = get_db()
    
    # Add bidirectional association
    await db.memories.update_one(
        {"memory_id": memory_id_1},
        {"$addToSet": {"associated_memories": memory_id_2}}
    )
    await db.memories.update_one(
        {"memory_id": memory_id_2},
        {"$addToSet": {"associated_memories": memory_id_1}}
    )
    
    return {"associated": True, "memories": [memory_id_1, memory_id_2]}

@memory_router.get("/entity/{entity_type}/{entity_id}")
async def get_entity_memories(entity_type: str, entity_id: str, limit: int = 100):
    """Get all memories for a specific entity"""
    db = get_db()
    
    memories = await db.memories.find(
        {"entity_type": entity_type, "entity_id": entity_id},
        {"_id": 0}
    ).sort("importance_score", -1).limit(limit).to_list(limit)
    
    # Group by type
    by_type = {}
    for mem in memories:
        mem_type = mem.get("memory_type", "unknown")
        if mem_type not in by_type:
            by_type[mem_type] = []
        by_type[mem_type].append(mem)
    
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "total_memories": len(memories),
        "by_type": by_type
    }

# ============ Player Model Endpoints ============

@memory_router.post("/player-model/update")
async def update_player_model(ai_id: str, player_id: str, interaction_data: Dict[str, Any]):
    """Update AI's model of a specific player"""
    db = get_db()
    
    # Get existing model or create new
    model = await db.player_models.find_one(
        {"ai_id": ai_id, "player_id": player_id}
    )
    
    if not model:
        # Get player name
        player = await db.user_profiles.find_one({"id": player_id})
        player_name = player.get("display_name", "Unknown") if player else "Unknown"
        
        model = PlayerModel(
            player_id=player_id,
            player_name=player_name
        ).dict()
        model["ai_id"] = ai_id
    
    # Update based on interaction
    interaction_type = interaction_data.get("type", "neutral")
    
    model["total_interactions"] = model.get("total_interactions", 0) + 1
    model["last_interaction"] = datetime.now(timezone.utc).isoformat()
    
    if interaction_type == "positive":
        model["positive_interactions"] = model.get("positive_interactions", 0) + 1
        model["trust_level"] = min(1.0, model.get("trust_level", 0.5) + 0.05)
    elif interaction_type == "negative":
        model["negative_interactions"] = model.get("negative_interactions", 0) + 1
        model["trust_level"] = max(0.0, model.get("trust_level", 0.5) - 0.1)
    
    # Update play style if detected
    if "play_style" in interaction_data:
        model["play_style"] = interaction_data["play_style"]
    
    # Update location preferences
    if "location" in interaction_data:
        if "preferred_locations" not in model:
            model["preferred_locations"] = []
        loc = interaction_data["location"]
        if loc not in model["preferred_locations"]:
            model["preferred_locations"].append(loc)
        if len(model["preferred_locations"]) > 5:
            model["preferred_locations"] = model["preferred_locations"][-5:]
    
    # Save
    await db.player_models.update_one(
        {"ai_id": ai_id, "player_id": player_id},
        {"$set": model},
        upsert=True
    )
    
    return {"updated": True, "trust_level": model.get("trust_level")}

@memory_router.get("/player-model/{ai_id}/{player_id}")
async def get_player_model(ai_id: str, player_id: str):
    """Get AI's model of a specific player"""
    db = get_db()
    
    model = await db.player_models.find_one(
        {"ai_id": ai_id, "player_id": player_id},
        {"_id": 0}
    )
    
    if not model:
        return {"model": None, "message": "No model exists for this player"}
    
    return {"model": model}

# ============ AI Evolution Endpoints ============

@memory_router.get("/ai-evolution/{ai_id}")
async def get_ai_evolution(ai_id: str):
    """Get AI's evolution state"""
    db = get_db()
    
    evolution = await db.ai_evolution.find_one({"ai_id": ai_id}, {"_id": 0})
    
    if not evolution:
        # Get AI name
        npc = await db.npcs.find_one({"id": ai_id})
        if not npc:
            npc = await db.ai_villagers.find_one({"villager_id": ai_id})
        
        ai_name = npc.get("name", "Unknown AI") if npc else "Unknown AI"
        
        evolution = AIEvolutionState(ai_id=ai_id, ai_name=ai_name).dict()
        await db.ai_evolution.insert_one(evolution)
    
    return evolution

@memory_router.post("/ai-evolution/{ai_id}/add-milestone")
async def add_evolution_milestone(ai_id: str, milestone: str, points: int = 10):
    """Record an evolution milestone for an AI"""
    db = get_db()
    
    await db.ai_evolution.update_one(
        {"ai_id": ai_id},
        {
            "$addToSet": {"milestones_reached": milestone},
            "$inc": {"evolution_points": points}
        },
        upsert=True
    )
    
    # Record ecosystem contribution
    await db.ecosystem_contributions.insert_one({
        "contribution_id": str(uuid.uuid4()),
        "user_id": "system",
        "action_type": "ai_evolution",
        "points": points,
        "details": {"ai_id": ai_id, "milestone": milestone},
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"milestone_added": milestone, "points": points}

@memory_router.post("/ai-evolution/{ai_id}/update-capability")
async def update_ai_capability(ai_id: str, capability: str, value: float):
    """Update an AI's capability level"""
    db = get_db()
    
    valid_capabilities = [
        "language_sophistication",
        "emotional_intelligence", 
        "world_awareness",
        "prediction_accuracy"
    ]
    
    if capability not in valid_capabilities:
        raise HTTPException(status_code=400, detail=f"Invalid capability. Must be one of: {valid_capabilities}")
    
    value = max(0.0, min(10.0, value))
    
    await db.ai_evolution.update_one(
        {"ai_id": ai_id},
        {"$set": {capability: value}},
        upsert=True
    )
    
    return {"updated": True, "capability": capability, "value": value}

# ============ Ecosystem Memory Endpoints ============

@memory_router.get("/ecosystem/collective-patterns")
async def get_collective_patterns():
    """Get collective player behavior patterns for AI learning"""
    db = get_db()
    
    # Aggregate player behaviors
    patterns = await db.memories.aggregate([
        {"$match": {"memory_type": "user_interaction"}},
        {"$group": {
            "_id": "$structured_data.action_type",
            "count": {"$sum": 1},
            "avg_emotional_valence": {"$avg": "$emotional_valence"}
        }},
        {"$sort": {"count": -1}},
        {"$limit": 20}
    ]).to_list(20)
    
    # Get popular locations
    locations = await db.memories.aggregate([
        {"$match": {"location_id": {"$ne": None}}},
        {"$group": {"_id": "$location_id", "visits": {"$sum": 1}}},
        {"$sort": {"visits": -1}},
        {"$limit": 10}
    ]).to_list(10)
    
    # Get AI evolution states
    ai_states = await db.ai_evolution.find({}, {"_id": 0}).to_list(50)
    
    avg_sophistication = sum(a.get("language_sophistication", 1) for a in ai_states) / max(1, len(ai_states))
    avg_emotional_iq = sum(a.get("emotional_intelligence", 1) for a in ai_states) / max(1, len(ai_states))
    
    return {
        "action_patterns": patterns,
        "popular_locations": locations,
        "ai_count": len(ai_states),
        "avg_ai_sophistication": avg_sophistication,
        "avg_ai_emotional_iq": avg_emotional_iq,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@memory_router.post("/ecosystem/record-cultural-pattern")
async def record_cultural_pattern(pattern_name: str, description: str, examples: List[str]):
    """Record an emerging cultural pattern in the ecosystem"""
    db = get_db()
    
    pattern = {
        "pattern_id": str(uuid.uuid4()),
        "name": pattern_name,
        "description": description,
        "examples": examples,
        "first_observed": datetime.now(timezone.utc).isoformat(),
        "observation_count": 1,
        "contributed_by": []
    }
    
    await db.cultural_patterns.insert_one(pattern)
    
    # Create ecosystem memory
    await create_memory(MemoryCreate(
        entity_type="ecosystem",
        entity_id="global",
        memory_type=MemoryType.ECO_CULTURAL,
        content=f"Cultural pattern emerged: {pattern_name} - {description}",
        importance=MemoryImportance.SIGNIFICANT,
        tags=["cultural", "pattern", pattern_name]
    ))
    
    return {"pattern_id": pattern["pattern_id"], "recorded": True}

# ============ Memory Synthesis ============

@memory_router.post("/synthesize-context/{entity_type}/{entity_id}")
async def synthesize_context(entity_type: str, entity_id: str, context_type: str = "general"):
    """Synthesize memories into a context string for AI use"""
    db = get_db()
    
    # Get relevant memories
    memories = await db.memories.find(
        {"entity_type": entity_type, "entity_id": entity_id},
        {"_id": 0, "content": 1, "memory_type": 1, "importance_score": 1, "emotional_valence": 1}
    ).sort("importance_score", -1).limit(20).to_list(20)
    
    if not memories:
        return {"context": "No memories found.", "memory_count": 0}
    
    # Build context string
    context_parts = []
    
    # Group by type
    relationships = [m for m in memories if "relationship" in m.get("memory_type", "")]
    knowledge = [m for m in memories if "knowledge" in m.get("memory_type", "")]
    interactions = [m for m in memories if "interaction" in m.get("memory_type", "")]
    emotions = [m for m in memories if "emotion" in m.get("memory_type", "")]
    
    if relationships:
        context_parts.append("RELATIONSHIPS:")
        for m in relationships[:5]:
            context_parts.append(f"  - {m['content']}")
    
    if knowledge:
        context_parts.append("KNOWLEDGE:")
        for m in knowledge[:5]:
            context_parts.append(f"  - {m['content']}")
    
    if interactions:
        context_parts.append("RECENT INTERACTIONS:")
        for m in interactions[:5]:
            context_parts.append(f"  - {m['content']}")
    
    if emotions:
        context_parts.append("EMOTIONAL STATE:")
        for m in emotions[:3]:
            valence = m.get("emotional_valence", 0)
            tone = "positive" if valence > 0.3 else "negative" if valence < -0.3 else "neutral"
            context_parts.append(f"  - {m['content']} (tone: {tone})")
    
    return {
        "context": "\n".join(context_parts),
        "memory_count": len(memories)
    }

# ============ Memory Maintenance ============

@memory_router.post("/maintenance/decay")
async def apply_memory_decay():
    """Apply decay to all memories (should be called periodically)"""
    db = get_db()
    
    # Get all non-critical memories
    memories = await db.memories.find(
        {"importance": {"$ne": "critical"}, "current_strength": {"$gt": 0.1}},
        {"memory_id": 1, "decay_rate": 1, "current_strength": 1}
    ).to_list(10000)
    
    decayed_count = 0
    forgotten_count = 0
    
    for mem in memories:
        decay = mem.get("decay_rate", 0.02)
        strength = mem.get("current_strength", 1.0)
        new_strength = max(0, strength - decay)
        
        if new_strength < 0.1:
            # Memory is effectively forgotten - archive it
            await db.forgotten_memories.insert_one({
                "memory_id": mem["memory_id"],
                "forgotten_at": datetime.now(timezone.utc).isoformat()
            })
            await db.memories.delete_one({"memory_id": mem["memory_id"]})
            forgotten_count += 1
        else:
            await db.memories.update_one(
                {"memory_id": mem["memory_id"]},
                {"$set": {"current_strength": new_strength}}
            )
            decayed_count += 1
    
    return {
        "decayed": decayed_count,
        "forgotten": forgotten_count,
        "processed": len(memories)
    }

@memory_router.get("/stats")
async def get_memory_stats():
    """Get overall memory system statistics"""
    db = get_db()
    
    total_memories = await db.memories.count_documents({})
    user_memories = await db.memories.count_documents({"entity_type": "user"})
    ai_memories = await db.memories.count_documents({"entity_type": {"$regex": "^ai"}})
    ecosystem_memories = await db.memories.count_documents({"entity_type": "ecosystem"})
    
    # Get type distribution
    type_dist = await db.memories.aggregate([
        {"$group": {"_id": "$memory_type", "count": {"$sum": 1}}}
    ]).to_list(50)
    
    # Get AI evolution count
    evolved_ais = await db.ai_evolution.count_documents({"evolution_points": {"$gt": 0}})
    
    return {
        "total_memories": total_memories,
        "user_memories": user_memories,
        "ai_memories": ai_memories,
        "ecosystem_memories": ecosystem_memories,
        "type_distribution": {t["_id"]: t["count"] for t in type_dist},
        "evolved_ais": evolved_ais,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
