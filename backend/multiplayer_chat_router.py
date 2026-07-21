"""
Multiplayer Chat System Router
Real-time WebSocket chat with channels: Global, Region, Party, Whisper
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Set
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import asyncio
import uuid
import json
import logging
import os
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

multiplayer_chat_router = APIRouter(prefix="/chat", tags=["multiplayer-chat"])

# Database connection
_db = None

def get_chat_db():
    global _db
    if _db is None:
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        db_name = os.environ.get("DB_NAME", "ai_village_echoes")
        client = AsyncIOMotorClient(mongo_url)
        _db = client[db_name]
    return _db

# ============ Connection Manager ============

class ConnectionManager:
    """Manages WebSocket connections for real-time chat"""
    
    def __init__(self):
        # user_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        # user_id -> user info
        self.user_info: Dict[str, Dict] = {}
        # channel_id -> set of user_ids
        self.channel_members: Dict[str, Set[str]] = defaultdict(set)
        # party_id -> set of user_ids
        self.party_members: Dict[str, Set[str]] = defaultdict(set)
        # user_id -> region_id
        self.user_regions: Dict[str, str] = {}
        # user_id -> typing status
        self.typing_users: Dict[str, Dict] = {}
        
    async def connect(self, websocket: WebSocket, user_id: str, user_info: Dict):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        self.user_info[user_id] = user_info
        
        # Auto-join global channel
        self.channel_members["global"].add(user_id)
        
        # Broadcast presence
        await self.broadcast_presence(user_id, "online")
        
    async def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        
        # Clean up memberships
        for channel_id in list(self.channel_members.keys()):
            self.channel_members[channel_id].discard(user_id)
        
        for party_id in list(self.party_members.keys()):
            self.party_members[party_id].discard(user_id)
        
        if user_id in self.user_regions:
            del self.user_regions[user_id]
        
        if user_id in self.user_info:
            del self.user_info[user_id]
        
        if user_id in self.typing_users:
            del self.typing_users[user_id]
        
        # Broadcast offline
        await self.broadcast_presence(user_id, "offline")
    
    async def broadcast_presence(self, user_id: str, status: str):
        """Broadcast user presence to all connected users"""
        message = {
            "type": "presence",
            "user_id": user_id,
            "username": self.user_info.get(user_id, {}).get("username", "Unknown"),
            "display_name": self.user_info.get(user_id, {}).get("display_name", "Unknown"),
            "status": status,
            "region": self.user_regions.get(user_id),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await self.broadcast_to_channel("global", message, exclude_user=None)
    
    async def send_personal(self, user_id: str, message: Dict):
        """Send message to a specific user"""
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_json(message)
            except Exception as e:
                logger.error(f"Failed to send to {user_id}: {e}")
    
    async def broadcast_to_channel(self, channel_id: str, message: Dict, exclude_user: Optional[str] = None):
        """Broadcast message to all users in a channel"""
        members = self.channel_members.get(channel_id, set())
        for user_id in members:
            if user_id != exclude_user and user_id in self.active_connections:
                try:
                    await self.active_connections[user_id].send_json(message)
                except Exception as e:
                    logger.error(f"Failed to broadcast to {user_id}: {e}")
    
    async def broadcast_to_party(self, party_id: str, message: Dict, exclude_user: Optional[str] = None):
        """Broadcast message to party members"""
        members = self.party_members.get(party_id, set())
        for user_id in members:
            if user_id != exclude_user and user_id in self.active_connections:
                try:
                    await self.active_connections[user_id].send_json(message)
                except Exception as e:
                    logger.error(f"Failed to broadcast to party {user_id}: {e}")
    
    async def broadcast_to_region(self, region_id: str, message: Dict, exclude_user: Optional[str] = None):
        """Broadcast message to all users in a region"""
        for user_id, user_region in self.user_regions.items():
            if user_region == region_id and user_id != exclude_user:
                if user_id in self.active_connections:
                    try:
                        await self.active_connections[user_id].send_json(message)
                    except Exception as e:
                        logger.error(f"Failed to broadcast region to {user_id}: {e}")
    
    def get_online_users(self) -> List[Dict]:
        """Get list of online users"""
        return [
            {
                "user_id": uid,
                "username": info.get("username"),
                "display_name": info.get("display_name"),
                "region": self.user_regions.get(uid),
                "status": "online"
            }
            for uid, info in self.user_info.items()
        ]
    
    def get_users_in_region(self, region_id: str) -> List[Dict]:
        """Get users in a specific region"""
        return [
            {
                "user_id": uid,
                "username": self.user_info.get(uid, {}).get("username"),
                "display_name": self.user_info.get(uid, {}).get("display_name"),
                "status": "online"
            }
            for uid, region in self.user_regions.items()
            if region == region_id
        ]


# Global connection manager
manager = ConnectionManager()


# ============ Models ============

class ChatMessage(BaseModel):
    message_id: str = None
    channel: str  # global, region, party, whisper
    sender_id: str
    sender_username: str
    sender_display_name: str
    recipient_id: Optional[str] = None  # For whispers
    party_id: Optional[str] = None  # For party chat
    region_id: Optional[str] = None  # For region chat
    content: str
    message_type: str = "text"  # text, emote, system
    timestamp: str = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.message_id:
            self.message_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

class SendMessageRequest(BaseModel):
    channel: str  # global, region, party, whisper
    content: str
    recipient_id: Optional[str] = None  # For whispers
    party_id: Optional[str] = None
    region_id: Optional[str] = None
    message_type: str = "text"

class CreatePartyRequest(BaseModel):
    name: str
    max_members: int = 6

class PartyInviteRequest(BaseModel):
    party_id: str
    invitee_id: str

class BlockUserRequest(BaseModel):
    blocked_user_id: str


# ============ WebSocket Endpoint ============

@multiplayer_chat_router.websocket("/ws/{user_id}")
async def websocket_chat(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time chat"""
    db = get_chat_db()
    
    # Get user info
    user = await db.user_profiles.find_one({"id": user_id}, {"_id": 0})
    if not user:
        await websocket.close(code=4001, reason="User not found")
        return
    
    user_info = {
        "user_id": user_id,
        "username": user.get("username"),
        "display_name": user.get("display_name")
    }
    
    await manager.connect(websocket, user_id, user_info)
    
    # Send initial data
    await websocket.send_json({
        "type": "connected",
        "user_id": user_id,
        "online_users": manager.get_online_users()
    })
    
    try:
        while True:
            data = await websocket.receive_json()
            await handle_websocket_message(user_id, data, db)
    except WebSocketDisconnect:
        await manager.disconnect(user_id)
    except Exception as e:
        logger.error(f"WebSocket error for {user_id}: {e}")
        await manager.disconnect(user_id)


async def handle_websocket_message(user_id: str, data: Dict, db):
    """Handle incoming WebSocket messages"""
    msg_type = data.get("type")
    
    if msg_type == "message":
        await handle_chat_message(user_id, data, db)
    
    elif msg_type == "typing":
        await handle_typing(user_id, data)
    
    elif msg_type == "join_region":
        region_id = data.get("region_id")
        if region_id:
            old_region = manager.user_regions.get(user_id)
            manager.user_regions[user_id] = region_id
            manager.channel_members[f"region_{region_id}"].add(user_id)
            
            if old_region:
                manager.channel_members[f"region_{old_region}"].discard(user_id)
            
            # Notify region
            await manager.broadcast_to_region(region_id, {
                "type": "user_joined_region",
                "user_id": user_id,
                "username": manager.user_info.get(user_id, {}).get("username"),
                "display_name": manager.user_info.get(user_id, {}).get("display_name"),
                "region_id": region_id
            }, exclude_user=user_id)
    
    elif msg_type == "leave_region":
        old_region = manager.user_regions.get(user_id)
        if old_region:
            manager.channel_members[f"region_{old_region}"].discard(user_id)
            del manager.user_regions[user_id]
            
            await manager.broadcast_to_region(old_region, {
                "type": "user_left_region",
                "user_id": user_id,
                "region_id": old_region
            })
    
    elif msg_type == "get_online_users":
        await manager.send_personal(user_id, {
            "type": "online_users",
            "users": manager.get_online_users()
        })
    
    elif msg_type == "get_region_users":
        region_id = data.get("region_id")
        if region_id:
            await manager.send_personal(user_id, {
                "type": "region_users",
                "region_id": region_id,
                "users": manager.get_users_in_region(region_id)
            })


async def handle_chat_message(user_id: str, data: Dict, db):
    """Handle chat message sending"""
    channel = data.get("channel", "global")
    content = data.get("content", "").strip()
    
    if not content or len(content) > 1000:
        return
    
    user_info = manager.user_info.get(user_id, {})
    
    # Check if user is blocked by recipient (for whispers)
    recipient_id = data.get("recipient_id")
    if channel == "whisper" and recipient_id:
        block = await db.chat_blocks.find_one({
            "blocker_id": recipient_id,
            "blocked_id": user_id
        })
        if block:
            await manager.send_personal(user_id, {
                "type": "error",
                "message": "This user has blocked you"
            })
            return
    
    message = ChatMessage(
        channel=channel,
        sender_id=user_id,
        sender_username=user_info.get("username", "Unknown"),
        sender_display_name=user_info.get("display_name", "Unknown"),
        recipient_id=recipient_id,
        party_id=data.get("party_id"),
        region_id=data.get("region_id") or manager.user_regions.get(user_id),
        content=content,
        message_type=data.get("message_type", "text")
    )
    
    # Store message in database
    msg_dict = message.dict()
    await db.chat_messages.insert_one(msg_dict.copy())
    
    # Build broadcast message
    broadcast_msg = {
        "type": "message",
        **msg_dict
    }
    
    # Route message to appropriate channel
    if channel == "global":
        await manager.broadcast_to_channel("global", broadcast_msg)
    
    elif channel == "region":
        region_id = message.region_id
        if region_id:
            await manager.broadcast_to_region(region_id, broadcast_msg)
    
    elif channel == "party":
        party_id = message.party_id
        if party_id:
            await manager.broadcast_to_party(party_id, broadcast_msg)
    
    elif channel == "whisper":
        if recipient_id:
            # Send to recipient
            await manager.send_personal(recipient_id, broadcast_msg)
            # Echo back to sender
            await manager.send_personal(user_id, broadcast_msg)


async def handle_typing(user_id: str, data: Dict):
    """Handle typing indicator"""
    channel = data.get("channel", "global")
    is_typing = data.get("is_typing", False)
    user_info = manager.user_info.get(user_id, {})
    
    typing_msg = {
        "type": "typing",
        "user_id": user_id,
        "username": user_info.get("username"),
        "display_name": user_info.get("display_name"),
        "channel": channel,
        "is_typing": is_typing
    }
    
    if channel == "global":
        await manager.broadcast_to_channel("global", typing_msg, exclude_user=user_id)
    elif channel == "region":
        region_id = manager.user_regions.get(user_id)
        if region_id:
            await manager.broadcast_to_region(region_id, typing_msg, exclude_user=user_id)
    elif channel == "party":
        party_id = data.get("party_id")
        if party_id:
            await manager.broadcast_to_party(party_id, typing_msg, exclude_user=user_id)
    elif channel == "whisper":
        recipient_id = data.get("recipient_id")
        if recipient_id:
            await manager.send_personal(recipient_id, typing_msg)


# ============ REST Endpoints ============

@multiplayer_chat_router.get("/online")
async def get_online_users():
    """Get list of online users"""
    return {
        "online_count": len(manager.active_connections),
        "users": manager.get_online_users()
    }


@multiplayer_chat_router.get("/history/{channel}")
async def get_chat_history(
    channel: str,
    region_id: Optional[str] = None,
    party_id: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 50
):
    """Get chat history for a channel"""
    db = get_chat_db()
    
    query = {"channel": channel}
    
    if channel == "region" and region_id:
        query["region_id"] = region_id
    elif channel == "party" and party_id:
        query["party_id"] = party_id
    elif channel == "whisper" and user_id:
        # Get whispers where user is sender or recipient
        query = {
            "channel": "whisper",
            "$or": [
                {"sender_id": user_id},
                {"recipient_id": user_id}
            ]
        }
    
    messages = await db.chat_messages.find(
        query,
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    
    messages.reverse()  # Return in chronological order
    
    return {
        "channel": channel,
        "messages": messages,
        "count": len(messages)
    }


@multiplayer_chat_router.get("/whispers/{user_id}/conversations")
async def get_whisper_conversations(user_id: str):
    """Get list of users the player has whispered with"""
    db = get_chat_db()
    
    # Get unique conversation partners
    pipeline = [
        {
            "$match": {
                "channel": "whisper",
                "$or": [
                    {"sender_id": user_id},
                    {"recipient_id": user_id}
                ]
            }
        },
        {
            "$project": {
                "partner_id": {
                    "$cond": {
                        "if": {"$eq": ["$sender_id", user_id]},
                        "then": "$recipient_id",
                        "else": "$sender_id"
                    }
                },
                "timestamp": 1
            }
        },
        {
            "$group": {
                "_id": "$partner_id",
                "last_message": {"$max": "$timestamp"}
            }
        },
        {"$sort": {"last_message": -1}},
        {"$limit": 20}
    ]
    
    conversations = await db.chat_messages.aggregate(pipeline).to_list(20)
    
    # Get user info for partners
    partner_ids = [c["_id"] for c in conversations]
    partners = await db.user_profiles.find(
        {"id": {"$in": partner_ids}},
        {"_id": 0, "id": 1, "username": 1, "display_name": 1}
    ).to_list(20)
    
    partner_map = {p["id"]: p for p in partners}
    
    result = []
    for conv in conversations:
        partner = partner_map.get(conv["_id"], {})
        result.append({
            "partner_id": conv["_id"],
            "partner_username": partner.get("username"),
            "partner_display_name": partner.get("display_name"),
            "last_message": conv["last_message"],
            "is_online": conv["_id"] in manager.active_connections
        })
    
    return {"conversations": result}


# ============ Party System ============

@multiplayer_chat_router.post("/party/create")
async def create_party(request: CreatePartyRequest, creator_id: str = Query(...)):
    """Create a new party"""
    db = get_chat_db()
    
    party_id = str(uuid.uuid4())
    
    party = {
        "party_id": party_id,
        "name": request.name,
        "leader_id": creator_id,
        "members": [creator_id],
        "max_members": request.max_members,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.parties.insert_one(party.copy())
    
    # Add to connection manager
    manager.party_members[party_id].add(creator_id)
    
    return {
        "party_id": party_id,
        "name": request.name,
        "members": [creator_id]
    }


@multiplayer_chat_router.post("/party/invite")
async def invite_to_party(request: PartyInviteRequest, inviter_id: str = Query(...)):
    """Invite a user to party"""
    db = get_chat_db()
    
    party = await db.parties.find_one({"party_id": request.party_id}, {"_id": 0})
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    
    if inviter_id != party["leader_id"] and inviter_id not in party["members"]:
        raise HTTPException(status_code=403, detail="Not a party member")
    
    if len(party["members"]) >= party["max_members"]:
        raise HTTPException(status_code=400, detail="Party is full")
    
    # Send invite to invitee
    await manager.send_personal(request.invitee_id, {
        "type": "party_invite",
        "party_id": request.party_id,
        "party_name": party["name"],
        "inviter_id": inviter_id,
        "inviter_name": manager.user_info.get(inviter_id, {}).get("display_name", "Unknown")
    })
    
    return {"status": "invite_sent"}


@multiplayer_chat_router.post("/party/{party_id}/join")
async def join_party(party_id: str, user_id: str = Query(...)):
    """Join a party"""
    db = get_chat_db()
    
    party = await db.parties.find_one({"party_id": party_id}, {"_id": 0})
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    
    if user_id in party["members"]:
        raise HTTPException(status_code=400, detail="Already in party")
    
    if len(party["members"]) >= party["max_members"]:
        raise HTTPException(status_code=400, detail="Party is full")
    
    # Add to party
    await db.parties.update_one(
        {"party_id": party_id},
        {"$push": {"members": user_id}}
    )
    
    manager.party_members[party_id].add(user_id)
    
    # Notify party members
    await manager.broadcast_to_party(party_id, {
        "type": "party_member_joined",
        "user_id": user_id,
        "display_name": manager.user_info.get(user_id, {}).get("display_name", "Unknown")
    })
    
    return {"status": "joined", "party_id": party_id}


@multiplayer_chat_router.post("/party/{party_id}/leave")
async def leave_party(party_id: str, user_id: str = Query(...)):
    """Leave a party"""
    db = get_chat_db()
    
    party = await db.parties.find_one({"party_id": party_id}, {"_id": 0})
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    
    if user_id not in party["members"]:
        raise HTTPException(status_code=400, detail="Not in party")
    
    # Remove from party
    await db.parties.update_one(
        {"party_id": party_id},
        {"$pull": {"members": user_id}}
    )
    
    manager.party_members[party_id].discard(user_id)
    
    # Notify party members
    await manager.broadcast_to_party(party_id, {
        "type": "party_member_left",
        "user_id": user_id
    })
    
    # If leader leaves, disband or transfer leadership
    if user_id == party["leader_id"]:
        remaining = [m for m in party["members"] if m != user_id]
        if remaining:
            # Transfer leadership
            new_leader = remaining[0]
            await db.parties.update_one(
                {"party_id": party_id},
                {"$set": {"leader_id": new_leader}}
            )
            await manager.broadcast_to_party(party_id, {
                "type": "party_leader_changed",
                "new_leader_id": new_leader
            })
        else:
            # Disband party
            await db.parties.delete_one({"party_id": party_id})
    
    return {"status": "left"}


@multiplayer_chat_router.get("/party/{party_id}")
async def get_party_info(party_id: str):
    """Get party information"""
    db = get_chat_db()
    
    party = await db.parties.find_one({"party_id": party_id}, {"_id": 0})
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    
    # Get member info
    members = await db.user_profiles.find(
        {"id": {"$in": party["members"]}},
        {"_id": 0, "id": 1, "username": 1, "display_name": 1}
    ).to_list(10)
    
    member_info = []
    for m in members:
        member_info.append({
            **m,
            "is_online": m["id"] in manager.active_connections,
            "is_leader": m["id"] == party["leader_id"]
        })
    
    return {
        **party,
        "member_info": member_info
    }


# ============ Block System ============

@multiplayer_chat_router.post("/block")
async def block_user(request: BlockUserRequest, user_id: str = Query(...)):
    """Block a user"""
    db = get_chat_db()
    
    await db.chat_blocks.update_one(
        {"blocker_id": user_id, "blocked_id": request.blocked_user_id},
        {"$set": {
            "blocker_id": user_id,
            "blocked_id": request.blocked_user_id,
            "blocked_at": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )
    
    return {"status": "blocked", "blocked_id": request.blocked_user_id}


@multiplayer_chat_router.delete("/block/{blocked_user_id}")
async def unblock_user(blocked_user_id: str, user_id: str = Query(...)):
    """Unblock a user"""
    db = get_chat_db()
    
    await db.chat_blocks.delete_one({
        "blocker_id": user_id,
        "blocked_id": blocked_user_id
    })
    
    return {"status": "unblocked", "blocked_id": blocked_user_id}


@multiplayer_chat_router.get("/blocks/{user_id}")
async def get_blocked_users(user_id: str):
    """Get list of blocked users"""
    db = get_chat_db()
    
    blocks = await db.chat_blocks.find(
        {"blocker_id": user_id},
        {"_id": 0}
    ).to_list(100)
    
    blocked_ids = [b["blocked_id"] for b in blocks]
    
    # Get user info
    users = await db.user_profiles.find(
        {"id": {"$in": blocked_ids}},
        {"_id": 0, "id": 1, "username": 1, "display_name": 1}
    ).to_list(100)
    
    return {"blocked_users": users}


# ============ Stats ============

@multiplayer_chat_router.get("/stats")
async def get_chat_stats():
    """Get chat statistics"""
    db = get_chat_db()
    
    # Count messages by channel (last 24h)
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    
    pipeline = [
        {"$match": {"timestamp": {"$gte": since}}},
        {"$group": {"_id": "$channel", "count": {"$sum": 1}}}
    ]
    
    channel_stats = await db.chat_messages.aggregate(pipeline).to_list(10)
    
    return {
        "online_users": len(manager.active_connections),
        "messages_24h": {s["_id"]: s["count"] for s in channel_stats},
        "active_parties": len([p for p in manager.party_members.values() if p]),
        "regions_with_players": len(set(manager.user_regions.values()))
    }
