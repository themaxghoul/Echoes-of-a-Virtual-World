# Unity Offload Router - Bridge between web and Unity client
# Handles session management, state sync, and cross-platform play

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone
import uuid
import logging
import os

unity_router = APIRouter(prefix="/unity", tags=["unity"])

logger = logging.getLogger(__name__)

# ============ Models ============

class UnitySession(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    player_id: str
    character_id: str
    token: str = Field(default_factory=lambda: str(uuid.uuid4()).replace('-', ''))
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: Optional[str] = None
    last_sync: Optional[str] = None
    unity_version: Optional[str] = None
    platform: Optional[str] = None  # windows, mac, linux, webgl
    state: str = "created"  # created, connected, playing, disconnected

class UnityStateSync(BaseModel):
    session_id: str
    character_state: Optional[Dict[str, Any]] = None
    inventory_state: Optional[Dict[str, Any]] = None
    world_position: Optional[Dict[str, float]] = None
    quest_progress: Optional[Dict[str, Any]] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class UnityDownloadInfo(BaseModel):
    windows: Optional[str] = None
    mac: Optional[str] = None
    linux: Optional[str] = None
    webgl: Optional[str] = None
    version: str = "1.0.0"
    release_date: str = "2026-04-22"
    changelog: List[str] = []

# ============ In-Memory Storage (for now) ============
# In production, use MongoDB collections

active_sessions: Dict[str, UnitySession] = {}
session_states: Dict[str, UnityStateSync] = {}

# ============ Database Helper ============

def get_db():
    from server import db
    return db

# ============ Endpoints ============

@unity_router.get("/config")
async def get_unity_config():
    """Get Unity server configuration"""
    return {
        "server_url": os.environ.get("UNITY_SERVER_URL", "wss://unity.aivillage.io"),
        "api_version": "1.0",
        "supported_platforms": ["windows", "mac", "linux", "webgl"],
        "min_unity_version": "2022.3",
        "features": {
            "cross_platform_sync": True,
            "real_time_chat": True,
            "3d_combat": True,
            "voice_chat": False,  # Coming soon
            "vr_support": False   # Coming soon
        },
        "sync_interval_ms": 5000,
        "heartbeat_interval_ms": 30000
    }

@unity_router.get("/downloads")
async def get_download_links():
    """Get Unity client download links"""
    return {
        "windows": "https://aivillage.itch.io/echoes-unity",
        "mac": "https://aivillage.itch.io/echoes-unity",
        "linux": "https://aivillage.itch.io/echoes-unity",
        "webgl": None,  # WebGL version coming soon
        "version": "1.0.0-beta",
        "release_date": "2026-04-22",
        "changelog": [
            "Initial beta release",
            "Full 3D village exploration",
            "Real-time NPC interactions",
            "Cross-platform character sync",
            "Combat system with AI enemies"
        ],
        "requirements": {
            "windows": {"os": "Windows 10+", "ram": "8GB", "gpu": "DirectX 11 compatible"},
            "mac": {"os": "macOS 10.15+", "ram": "8GB", "gpu": "Metal compatible"},
            "linux": {"os": "Ubuntu 20.04+", "ram": "8GB", "gpu": "Vulkan compatible"}
        }
    }

@unity_router.post("/session")
async def create_unity_session(player_id: str, character_id: str):
    """Create a new Unity session for cross-platform play"""
    db = get_db()
    
    # Verify player exists
    player = await db.user_profiles.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Verify character exists
    character = await db.characters.find_one({"id": character_id})
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    # Create session
    session = UnitySession(
        player_id=player_id,
        character_id=character_id
    )
    
    # Store in memory and DB
    active_sessions[session.session_id] = session
    
    await db.unity_sessions.insert_one(session.dict())
    
    logger.info(f"Unity session created for player {player_id}: {session.session_id}")
    
    return {
        "session_id": session.session_id,
        "token": session.token,
        "expires_in": 86400,  # 24 hours
        "connect_url": f"wss://unity.aivillage.io/connect?token={session.token}"
    }

@unity_router.post("/session/{session_id}/connect")
async def connect_unity_session(session_id: str, platform: str = "windows", unity_version: str = "2022.3"):
    """Mark a Unity session as connected"""
    db = get_db()
    
    session = active_sessions.get(session_id)
    if not session:
        # Try to load from DB
        session_data = await db.unity_sessions.find_one({"session_id": session_id})
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        session = UnitySession(**{k: v for k, v in session_data.items() if k != '_id'})
        active_sessions[session_id] = session
    
    session.state = "connected"
    session.platform = platform
    session.unity_version = unity_version
    session.last_sync = datetime.now(timezone.utc).isoformat()
    
    await db.unity_sessions.update_one(
        {"session_id": session_id},
        {"$set": {
            "state": "connected",
            "platform": platform,
            "unity_version": unity_version,
            "last_sync": session.last_sync
        }}
    )
    
    return {"connected": True, "session": session.dict()}

@unity_router.post("/session/{session_id}/disconnect")
async def disconnect_unity_session(session_id: str):
    """Mark a Unity session as disconnected"""
    db = get_db()
    
    if session_id in active_sessions:
        session = active_sessions[session_id]
        session.state = "disconnected"
    
    await db.unity_sessions.update_one(
        {"session_id": session_id},
        {"$set": {"state": "disconnected", "disconnected_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"disconnected": True}

@unity_router.get("/session/{session_id}/state")
async def get_session_state(session_id: str):
    """Get the current state for a Unity session"""
    db = get_db()
    
    session = active_sessions.get(session_id)
    if not session:
        session_data = await db.unity_sessions.find_one({"session_id": session_id}, {"_id": 0})
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        session = UnitySession(**session_data)
    
    # Get character state
    character = await db.characters.find_one({"id": session.character_id}, {"_id": 0})
    
    # Get inventory
    inventory = await db.inventories.find_one({"character_id": session.character_id}, {"_id": 0})
    
    # Get active quests
    quests = await db.character_quests.find(
        {"character_id": session.character_id, "status": "active"},
        {"_id": 0}
    ).to_list(20)
    
    return {
        "session_id": session_id,
        "state": session.state,
        "character": character,
        "inventory": inventory.get("items", []) if inventory else [],
        "active_quests": quests,
        "last_sync": session.last_sync
    }

@unity_router.post("/sync")
async def sync_unity_state(sync_data: UnityStateSync):
    """Sync state from Unity client to server"""
    db = get_db()
    
    session = active_sessions.get(sync_data.session_id)
    if not session:
        session_data = await db.unity_sessions.find_one({"session_id": sync_data.session_id})
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        session = UnitySession(**{k: v for k, v in session_data.items() if k != '_id'})
        active_sessions[sync_data.session_id] = session
    
    # Update character state if provided
    if sync_data.character_state:
        await db.characters.update_one(
            {"id": session.character_id},
            {"$set": {
                "health": sync_data.character_state.get("health"),
                "stamina": sync_data.character_state.get("stamina"),
                "experience": sync_data.character_state.get("experience"),
                "level": sync_data.character_state.get("level"),
                "last_unity_sync": sync_data.timestamp
            }}
        )
    
    # Update position if provided
    if sync_data.world_position:
        await db.characters.update_one(
            {"id": session.character_id},
            {"$set": {
                "unity_position": sync_data.world_position,
                "current_location": sync_data.world_position.get("location_id", "village_square")
            }}
        )
    
    # Update inventory if provided
    if sync_data.inventory_state:
        await db.inventories.update_one(
            {"character_id": session.character_id},
            {"$set": {"items": sync_data.inventory_state.get("items", []), "last_sync": sync_data.timestamp}},
            upsert=True
        )
    
    # Update quest progress if provided
    if sync_data.quest_progress:
        for quest_id, progress in sync_data.quest_progress.items():
            await db.character_quests.update_one(
                {"character_id": session.character_id, "quest_id": quest_id},
                {"$set": {"progress": progress, "last_update": sync_data.timestamp}}
            )
    
    # Update session last sync
    session.last_sync = sync_data.timestamp
    await db.unity_sessions.update_one(
        {"session_id": sync_data.session_id},
        {"$set": {"last_sync": sync_data.timestamp}}
    )
    
    # Store sync state
    session_states[sync_data.session_id] = sync_data
    
    return {
        "synced": True,
        "timestamp": sync_data.timestamp,
        "session_state": session.state
    }

@unity_router.get("/active-sessions/{player_id}")
async def get_player_active_sessions(player_id: str):
    """Get all active Unity sessions for a player"""
    db = get_db()
    
    sessions = await db.unity_sessions.find(
        {"player_id": player_id, "state": {"$in": ["created", "connected", "playing"]}},
        {"_id": 0}
    ).to_list(10)
    
    return {"sessions": sessions, "count": len(sessions)}

@unity_router.post("/heartbeat/{session_id}")
async def unity_heartbeat(session_id: str):
    """Keep-alive heartbeat from Unity client"""
    db = get_db()
    
    now = datetime.now(timezone.utc).isoformat()
    
    if session_id in active_sessions:
        active_sessions[session_id].last_sync = now
    
    await db.unity_sessions.update_one(
        {"session_id": session_id},
        {"$set": {"last_heartbeat": now}}
    )
    
    return {"alive": True, "timestamp": now}

@unity_router.get("/stats")
async def get_unity_stats():
    """Get Unity platform statistics"""
    db = get_db()
    
    # Count active sessions
    active_count = await db.unity_sessions.count_documents({"state": {"$in": ["connected", "playing"]}})
    
    # Count by platform
    platform_stats = await db.unity_sessions.aggregate([
        {"$match": {"state": {"$in": ["connected", "playing"]}}},
        {"$group": {"_id": "$platform", "count": {"$sum": 1}}}
    ]).to_list(10)
    
    return {
        "active_sessions": active_count,
        "platforms": {p["_id"]: p["count"] for p in platform_stats if p["_id"]},
        "total_sessions_ever": await db.unity_sessions.count_documents({}),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
