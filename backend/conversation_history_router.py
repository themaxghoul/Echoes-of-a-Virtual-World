# Conversation History Router - Chat Logs & Resume Feature
# Allows players to review past dialogues and resume conversations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone
import uuid
import logging

conversation_history_router = APIRouter(prefix="/conversations", tags=["conversations"])

logger = logging.getLogger(__name__)

# ============ Models ============

class ConversationMessage(BaseModel):
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: str  # user, assistant, narrator, system
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Optional[Dict[str, Any]] = None  # Extra data like mood, actions, etc.

class Conversation(BaseModel):
    conversation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    player_id: str
    character_id: str  # Player's character
    npc_id: Optional[str] = None
    npc_name: Optional[str] = None
    location_id: str
    location_name: str
    messages: List[ConversationMessage] = Field(default_factory=list)
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_message_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    message_count: int = 0
    is_active: bool = True
    session_date: str = Field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    tags: List[str] = Field(default_factory=list)
    summary: Optional[str] = None  # AI-generated summary of conversation

class ConversationCreate(BaseModel):
    player_id: str
    character_id: str
    npc_id: Optional[str] = None
    npc_name: Optional[str] = None
    location_id: str
    location_name: str

class MessageAdd(BaseModel):
    role: str
    content: str
    metadata: Optional[Dict[str, Any]] = None

class ConversationResume(BaseModel):
    conversation_id: str
    player_id: str

# ============ Database Helper ============

def get_db():
    from server import db
    return db

# ============ Endpoints ============

@conversation_history_router.post("/create")
async def create_conversation(data: ConversationCreate):
    """Create a new conversation session"""
    db = get_db()
    
    conversation = Conversation(
        player_id=data.player_id,
        character_id=data.character_id,
        npc_id=data.npc_id,
        npc_name=data.npc_name,
        location_id=data.location_id,
        location_name=data.location_name
    )
    
    await db.conversation_history.insert_one(conversation.dict())
    
    return {
        "created": True,
        "conversation_id": conversation.conversation_id,
        "conversation": conversation.dict()
    }

@conversation_history_router.post("/{conversation_id}/message")
async def add_message(conversation_id: str, message: MessageAdd):
    """Add a message to a conversation"""
    db = get_db()
    
    conversation = await db.conversation_history.find_one({"conversation_id": conversation_id})
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    new_message = ConversationMessage(
        role=message.role,
        content=message.content,
        metadata=message.metadata
    )
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.conversation_history.update_one(
        {"conversation_id": conversation_id},
        {
            "$push": {"messages": new_message.dict()},
            "$inc": {"message_count": 1},
            "$set": {
                "last_message_at": now,
                "is_active": True
            }
        }
    )
    
    return {
        "added": True,
        "message_id": new_message.message_id,
        "timestamp": new_message.timestamp
    }

@conversation_history_router.post("/{conversation_id}/messages/bulk")
async def add_messages_bulk(conversation_id: str, messages: List[MessageAdd]):
    """Add multiple messages to a conversation at once"""
    db = get_db()
    
    conversation = await db.conversation_history.find_one({"conversation_id": conversation_id})
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    new_messages = [
        ConversationMessage(
            role=m.role,
            content=m.content,
            metadata=m.metadata
        ).dict() for m in messages
    ]
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.conversation_history.update_one(
        {"conversation_id": conversation_id},
        {
            "$push": {"messages": {"$each": new_messages}},
            "$inc": {"message_count": len(messages)},
            "$set": {
                "last_message_at": now,
                "is_active": True
            }
        }
    )
    
    return {
        "added": True,
        "count": len(messages)
    }

@conversation_history_router.get("/player/{player_id}")
async def get_player_conversations(
    player_id: str,
    group_by: str = "npc",  # npc or session
    limit: int = 50,
    offset: int = 0
):
    """Get all conversations for a player, grouped by NPC or session"""
    db = get_db()
    
    # Get all conversations for player
    conversations = await db.conversation_history.find(
        {"player_id": player_id},
        {"_id": 0}
    ).sort("last_message_at", -1).to_list(500)  # Get all, we'll group in memory
    
    if group_by == "npc":
        # Group by NPC
        grouped = {}
        for conv in conversations:
            npc_key = conv.get("npc_id") or conv.get("npc_name") or "unknown"
            npc_name = conv.get("npc_name") or "Unknown NPC"
            
            if npc_key not in grouped:
                grouped[npc_key] = {
                    "npc_id": conv.get("npc_id"),
                    "npc_name": npc_name,
                    "conversations": [],
                    "total_messages": 0,
                    "last_interaction": conv.get("last_message_at")
                }
            
            # Get preview (last message)
            last_msg = conv.get("messages", [])[-1] if conv.get("messages") else None
            
            grouped[npc_key]["conversations"].append({
                "conversation_id": conv["conversation_id"],
                "location_name": conv.get("location_name"),
                "started_at": conv.get("started_at"),
                "last_message_at": conv.get("last_message_at"),
                "message_count": conv.get("message_count", 0),
                "preview": last_msg.get("content", "")[:100] if last_msg else "",
                "is_active": conv.get("is_active", False)
            })
            grouped[npc_key]["total_messages"] += conv.get("message_count", 0)
        
        # Convert to list and sort by last interaction
        result = sorted(grouped.values(), key=lambda x: x["last_interaction"] or "", reverse=True)
        
        return {
            "group_by": "npc",
            "groups": result[offset:offset+limit],
            "total_npcs": len(result),
            "total_conversations": len(conversations)
        }
    
    else:  # group by session/date
        grouped = {}
        for conv in conversations:
            session_date = conv.get("session_date") or conv.get("started_at", "")[:10]
            
            if session_date not in grouped:
                grouped[session_date] = {
                    "date": session_date,
                    "conversations": [],
                    "total_messages": 0
                }
            
            # Get preview
            last_msg = conv.get("messages", [])[-1] if conv.get("messages") else None
            
            grouped[session_date]["conversations"].append({
                "conversation_id": conv["conversation_id"],
                "npc_name": conv.get("npc_name"),
                "location_name": conv.get("location_name"),
                "started_at": conv.get("started_at"),
                "last_message_at": conv.get("last_message_at"),
                "message_count": conv.get("message_count", 0),
                "preview": last_msg.get("content", "")[:100] if last_msg else "",
                "is_active": conv.get("is_active", False)
            })
            grouped[session_date]["total_messages"] += conv.get("message_count", 0)
        
        # Sort by date descending
        result = sorted(grouped.values(), key=lambda x: x["date"], reverse=True)
        
        return {
            "group_by": "session",
            "groups": result[offset:offset+limit],
            "total_sessions": len(result),
            "total_conversations": len(conversations)
        }

@conversation_history_router.get("/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get full conversation with all messages"""
    db = get_db()
    
    conversation = await db.conversation_history.find_one(
        {"conversation_id": conversation_id},
        {"_id": 0}
    )
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {"conversation": conversation}

@conversation_history_router.get("/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    limit: int = 100,
    before_message_id: Optional[str] = None
):
    """Get messages from a conversation with pagination"""
    db = get_db()
    
    conversation = await db.conversation_history.find_one(
        {"conversation_id": conversation_id},
        {"_id": 0, "messages": 1, "message_count": 1}
    )
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = conversation.get("messages", [])
    
    # If before_message_id provided, get messages before that
    if before_message_id:
        idx = next((i for i, m in enumerate(messages) if m["message_id"] == before_message_id), len(messages))
        messages = messages[max(0, idx - limit):idx]
    else:
        # Get last N messages
        messages = messages[-limit:] if len(messages) > limit else messages
    
    return {
        "messages": messages,
        "total_count": conversation.get("message_count", 0),
        "returned_count": len(messages),
        "has_more": len(messages) < conversation.get("message_count", 0)
    }

@conversation_history_router.post("/resume")
async def resume_conversation(data: ConversationResume):
    """Resume a previous conversation - returns context for continuing"""
    db = get_db()
    
    conversation = await db.conversation_history.find_one(
        {"conversation_id": data.conversation_id, "player_id": data.player_id},
        {"_id": 0}
    )
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Mark as active
    await db.conversation_history.update_one(
        {"conversation_id": data.conversation_id},
        {"$set": {"is_active": True}}
    )
    
    # Get last N messages for context
    messages = conversation.get("messages", [])
    context_messages = messages[-20:]  # Last 20 messages for context
    
    return {
        "resumed": True,
        "conversation_id": conversation["conversation_id"],
        "npc_id": conversation.get("npc_id"),
        "npc_name": conversation.get("npc_name"),
        "location_id": conversation.get("location_id"),
        "location_name": conversation.get("location_name"),
        "context_messages": context_messages,
        "total_messages": len(messages),
        "last_message_at": conversation.get("last_message_at"),
        "can_continue": True
    }

@conversation_history_router.post("/{conversation_id}/end")
async def end_conversation(conversation_id: str):
    """Mark a conversation as ended/inactive"""
    db = get_db()
    
    result = await db.conversation_history.update_one(
        {"conversation_id": conversation_id},
        {"$set": {
            "is_active": False,
            "ended_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {"ended": True, "conversation_id": conversation_id}

@conversation_history_router.get("/player/{player_id}/search")
async def search_conversations(
    player_id: str,
    query: str,
    limit: int = 20
):
    """Search through conversation messages"""
    db = get_db()
    
    # Search in messages content
    conversations = await db.conversation_history.find(
        {
            "player_id": player_id,
            "messages.content": {"$regex": query, "$options": "i"}
        },
        {"_id": 0}
    ).limit(limit).to_list(limit)
    
    results = []
    for conv in conversations:
        # Find matching messages
        matching_messages = [
            m for m in conv.get("messages", [])
            if query.lower() in m.get("content", "").lower()
        ]
        
        results.append({
            "conversation_id": conv["conversation_id"],
            "npc_name": conv.get("npc_name"),
            "location_name": conv.get("location_name"),
            "last_message_at": conv.get("last_message_at"),
            "matching_messages": matching_messages[:5],  # First 5 matches
            "total_matches": len(matching_messages)
        })
    
    return {
        "query": query,
        "results": results,
        "total_results": len(results)
    }

@conversation_history_router.get("/player/{player_id}/stats")
async def get_conversation_stats(player_id: str):
    """Get conversation statistics for a player"""
    db = get_db()
    
    pipeline = [
        {"$match": {"player_id": player_id}},
        {"$group": {
            "_id": None,
            "total_conversations": {"$sum": 1},
            "total_messages": {"$sum": "$message_count"},
            "unique_npcs": {"$addToSet": "$npc_name"},
            "unique_locations": {"$addToSet": "$location_name"},
            "first_conversation": {"$min": "$started_at"},
            "last_conversation": {"$max": "$last_message_at"}
        }}
    ]
    
    stats = await db.conversation_history.aggregate(pipeline).to_list(1)
    
    if stats:
        stats = stats[0]
        stats["unique_npcs"] = [n for n in stats.get("unique_npcs", []) if n]
        stats["unique_locations"] = [l for l in stats.get("unique_locations", []) if l]
        stats["unique_npcs_count"] = len(stats["unique_npcs"])
        stats["unique_locations_count"] = len(stats["unique_locations"])
        del stats["_id"]
    else:
        stats = {
            "total_conversations": 0,
            "total_messages": 0,
            "unique_npcs": [],
            "unique_locations": [],
            "unique_npcs_count": 0,
            "unique_locations_count": 0
        }
    
    return stats

@conversation_history_router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str, player_id: str):
    """Delete a conversation (soft delete - marks as deleted)"""
    db = get_db()
    
    result = await db.conversation_history.update_one(
        {"conversation_id": conversation_id, "player_id": player_id},
        {"$set": {
            "deleted": True,
            "deleted_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {"deleted": True, "conversation_id": conversation_id}
