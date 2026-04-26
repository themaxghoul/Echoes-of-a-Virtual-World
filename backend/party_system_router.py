"""
Unified Party System
====================
Party system that supports both players AND AI NPCs.
Parties can explore together, share proximity chat, and combine abilities.
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
import os
import uuid
import json

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

router = APIRouter(prefix="/api/party", tags=["Party System"])

# Party configuration
MAX_PARTY_SIZE = 6
NPC_PARTY_LIMIT = 3  # Max NPCs per party

# Party roles
PARTY_ROLES = {
    "leader": {
        "name": "Leader",
        "permissions": ["invite", "kick", "promote", "disband", "set_destination"],
        "icon": "crown"
    },
    "officer": {
        "name": "Officer",
        "permissions": ["invite", "kick"],
        "icon": "shield"
    },
    "member": {
        "name": "Member",
        "permissions": [],
        "icon": "user"
    },
    "npc_companion": {
        "name": "NPC Companion",
        "permissions": [],
        "icon": "bot"
    }
}

# Active party connections for real-time chat
party_connections: Dict[str, Dict[str, WebSocket]] = {}


# ============ Pydantic Models ============
class CreatePartyRequest(BaseModel):
    leader_id: str
    leader_name: str
    party_name: Optional[str] = None
    is_open: bool = Field(default=True, description="Can others request to join?")


class InviteRequest(BaseModel):
    party_id: str
    inviter_id: str
    invitee_id: str
    invitee_name: str
    invitee_type: str = Field(default="player", description="player or npc")


class JoinPartyRequest(BaseModel):
    party_id: str
    member_id: str
    member_name: str
    member_type: str = Field(default="player", description="player or npc")


class PartyChatMessage(BaseModel):
    party_id: str
    sender_id: str
    sender_name: str
    sender_type: str = Field(default="player", description="player or npc")
    message: str
    is_proximity: bool = Field(default=False, description="Is this proximity chat?")


# ============ Helper Functions ============
async def get_party(party_id: str):
    """Get party by ID."""
    return await db.parties.find_one({"party_id": party_id}, {"_id": 0})


async def get_member_party(member_id: str):
    """Get the party a member belongs to."""
    return await db.parties.find_one(
        {"members.member_id": member_id, "disbanded": {"$ne": True}},
        {"_id": 0}
    )


async def broadcast_to_party(party_id: str, message: dict, exclude_id: str = None):
    """Broadcast a message to all party members via WebSocket."""
    if party_id in party_connections:
        for member_id, ws in party_connections[party_id].items():
            if member_id != exclude_id:
                try:
                    await ws.send_json(message)
                except Exception:
                    pass


# ============ API Endpoints ============

@router.get("/roles")
async def get_party_roles():
    """Get all party roles and their permissions."""
    return {
        "roles": PARTY_ROLES,
        "max_party_size": MAX_PARTY_SIZE,
        "max_npcs": NPC_PARTY_LIMIT
    }


@router.get("/stats")
async def get_party_system_stats():
    """Get party system statistics."""
    active_parties = await db.parties.count_documents({"disbanded": {"$ne": True}})
    total_parties = await db.parties.count_documents({})
    
    # Count members
    pipeline = [
        {"$match": {"disbanded": {"$ne": True}}},
        {"$unwind": "$members"},
        {"$group": {"_id": "$members.type", "count": {"$sum": 1}}}
    ]
    member_counts = await db.parties.aggregate(pipeline).to_list(10)
    
    return {
        "active_parties": active_parties,
        "total_parties_created": total_parties,
        "member_breakdown": {item["_id"]: item["count"] for item in member_counts},
        "max_party_size": MAX_PARTY_SIZE,
        "max_npcs_per_party": NPC_PARTY_LIMIT
    }


@router.post("/create")
async def create_party(request: CreatePartyRequest):
    """Create a new party."""
    # Check if leader is already in a party
    existing = await get_member_party(request.leader_id)
    if existing:
        raise HTTPException(
            status_code=409,
            detail="You are already in a party. Leave first."
        )
    
    party_id = str(uuid.uuid4())[:8]
    party_name = request.party_name or f"{request.leader_name}'s Party"
    
    party = {
        "party_id": party_id,
        "name": party_name,
        "leader_id": request.leader_id,
        "leader_name": request.leader_name,
        "members": [{
            "member_id": request.leader_id,
            "name": request.leader_name,
            "type": "player",
            "role": "leader",
            "joined_at": datetime.now(timezone.utc).isoformat()
        }],
        "is_open": request.is_open,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "disbanded": False,
        "pending_invites": [],
        "chat_history": [],
        "shared_location": None,
        "party_stats": {
            "battles_won": 0,
            "dungeons_cleared": 0,
            "total_xp_earned": 0
        }
    }
    
    await db.parties.insert_one(party)
    
    return {
        "success": True,
        "party_id": party_id,
        "name": party_name,
        "message": f"Party '{party_name}' created!"
    }


@router.post("/invite")
async def invite_to_party(request: InviteRequest):
    """Invite a player or NPC to the party."""
    party = await get_party(request.party_id)
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    
    # Check inviter permissions
    inviter = next((m for m in party["members"] if m["member_id"] == request.inviter_id), None)
    if not inviter:
        raise HTTPException(status_code=403, detail="You are not in this party")
    
    inviter_role = PARTY_ROLES.get(inviter.get("role", "member"), {})
    if "invite" not in inviter_role.get("permissions", []):
        raise HTTPException(status_code=403, detail="You don't have permission to invite")
    
    # Check party size
    if len(party["members"]) >= MAX_PARTY_SIZE:
        raise HTTPException(status_code=400, detail="Party is full")
    
    # Check NPC limit
    if request.invitee_type == "npc":
        npc_count = sum(1 for m in party["members"] if m.get("type") == "npc")
        if npc_count >= NPC_PARTY_LIMIT:
            raise HTTPException(status_code=400, detail=f"Party can have max {NPC_PARTY_LIMIT} NPCs")
    
    # Check if already invited or member
    if any(m["member_id"] == request.invitee_id for m in party["members"]):
        raise HTTPException(status_code=409, detail="Already in party")
    
    if any(i["invitee_id"] == request.invitee_id for i in party.get("pending_invites", [])):
        raise HTTPException(status_code=409, detail="Already invited")
    
    # For NPCs, auto-join (they don't decline)
    if request.invitee_type == "npc":
        new_member = {
            "member_id": request.invitee_id,
            "name": request.invitee_name,
            "type": "npc",
            "role": "npc_companion",
            "joined_at": datetime.now(timezone.utc).isoformat(),
            "invited_by": request.inviter_id
        }
        
        await db.parties.update_one(
            {"party_id": request.party_id},
            {"$push": {"members": new_member}}
        )
        
        # Notify party
        await broadcast_to_party(request.party_id, {
            "type": "member_joined",
            "member": new_member,
            "message": f"{request.invitee_name} (NPC) joined the party!"
        })
        
        return {
            "success": True,
            "auto_joined": True,
            "message": f"{request.invitee_name} joined the party!"
        }
    
    # For players, add to pending invites
    invite = {
        "invite_id": str(uuid.uuid4()),
        "invitee_id": request.invitee_id,
        "invitee_name": request.invitee_name,
        "inviter_id": request.inviter_id,
        "inviter_name": inviter["name"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.parties.update_one(
        {"party_id": request.party_id},
        {"$push": {"pending_invites": invite}}
    )
    
    # Store invite for the player
    await db.party_invites.insert_one({
        "invite_id": invite["invite_id"],
        "party_id": request.party_id,
        "party_name": party["name"],
        **invite
    })
    
    return {
        "success": True,
        "invite_id": invite["invite_id"],
        "message": f"Invitation sent to {request.invitee_name}"
    }


@router.post("/join")
async def join_party(request: JoinPartyRequest):
    """Join a party (accept invite or join open party)."""
    party = await get_party(request.party_id)
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    
    if party.get("disbanded"):
        raise HTTPException(status_code=400, detail="Party has been disbanded")
    
    # Check if already in a party
    existing = await get_member_party(request.member_id)
    if existing:
        raise HTTPException(status_code=409, detail="You are already in a party")
    
    # Check if full
    if len(party["members"]) >= MAX_PARTY_SIZE:
        raise HTTPException(status_code=400, detail="Party is full")
    
    # Check invite or open party
    invite = next(
        (i for i in party.get("pending_invites", []) if i["invitee_id"] == request.member_id),
        None
    )
    
    if not invite and not party.get("is_open"):
        raise HTTPException(status_code=403, detail="This party is invite-only")
    
    # Add member
    role = "npc_companion" if request.member_type == "npc" else "member"
    new_member = {
        "member_id": request.member_id,
        "name": request.member_name,
        "type": request.member_type,
        "role": role,
        "joined_at": datetime.now(timezone.utc).isoformat()
    }
    
    update = {"$push": {"members": new_member}}
    if invite:
        update["$pull"] = {"pending_invites": {"invitee_id": request.member_id}}
    
    await db.parties.update_one({"party_id": request.party_id}, update)
    
    # Remove invite document
    if invite:
        await db.party_invites.delete_one({"invitee_id": request.member_id, "party_id": request.party_id})
    
    # Notify party
    await broadcast_to_party(request.party_id, {
        "type": "member_joined",
        "member": new_member,
        "message": f"{request.member_name} joined the party!"
    })
    
    return {
        "success": True,
        "party_id": request.party_id,
        "party_name": party["name"],
        "role": role,
        "message": f"Joined {party['name']}!"
    }


@router.post("/leave/{party_id}")
async def leave_party(party_id: str, member_id: str):
    """Leave a party."""
    party = await get_party(party_id)
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    
    member = next((m for m in party["members"] if m["member_id"] == member_id), None)
    if not member:
        raise HTTPException(status_code=404, detail="You are not in this party")
    
    # If leader leaves, promote someone or disband
    if member["role"] == "leader":
        remaining = [m for m in party["members"] if m["member_id"] != member_id and m["type"] == "player"]
        
        if remaining:
            # Promote first player member
            new_leader = remaining[0]
            await db.parties.update_one(
                {"party_id": party_id, "members.member_id": new_leader["member_id"]},
                {"$set": {"members.$.role": "leader", "leader_id": new_leader["member_id"], "leader_name": new_leader["name"]}}
            )
        else:
            # Disband party (only NPCs left)
            await db.parties.update_one(
                {"party_id": party_id},
                {"$set": {"disbanded": True, "disbanded_at": datetime.now(timezone.utc).isoformat()}}
            )
            return {"success": True, "disbanded": True, "message": "Party disbanded"}
    
    # Remove member
    await db.parties.update_one(
        {"party_id": party_id},
        {"$pull": {"members": {"member_id": member_id}}}
    )
    
    # Notify party
    await broadcast_to_party(party_id, {
        "type": "member_left",
        "member_id": member_id,
        "member_name": member["name"],
        "message": f"{member['name']} left the party"
    }, exclude_id=member_id)
    
    return {"success": True, "message": "Left the party"}


@router.get("/{party_id}")
async def get_party_info(party_id: str):
    """Get party information."""
    party = await get_party(party_id)
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    
    return party


@router.get("/my-party/{member_id}")
async def get_my_party(member_id: str):
    """Get the party a member belongs to."""
    party = await get_member_party(member_id)
    if not party:
        return {"in_party": False, "party": None}
    
    return {"in_party": True, "party": party}


@router.get("/invites/{user_id}")
async def get_pending_invites(user_id: str):
    """Get pending party invites for a user."""
    invites = await db.party_invites.find(
        {"invitee_id": user_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(20)
    
    return {"invites": invites, "count": len(invites)}


@router.post("/chat")
async def send_party_chat(message: PartyChatMessage):
    """Send a message to party chat (works for players AND NPCs)."""
    party = await get_party(message.party_id)
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    
    # Verify sender is in party
    member = next((m for m in party["members"] if m["member_id"] == message.sender_id), None)
    if not member:
        raise HTTPException(status_code=403, detail="Not a party member")
    
    chat_message = {
        "message_id": str(uuid.uuid4()),
        "sender_id": message.sender_id,
        "sender_name": message.sender_name,
        "sender_type": message.sender_type,
        "message": message.message,
        "is_proximity": message.is_proximity,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # Store in party chat history (last 100 messages)
    await db.parties.update_one(
        {"party_id": message.party_id},
        {
            "$push": {
                "chat_history": {
                    "$each": [chat_message],
                    "$slice": -100  # Keep last 100 messages
                }
            }
        }
    )
    
    # Broadcast to connected members
    await broadcast_to_party(message.party_id, {
        "type": "chat_message",
        **chat_message
    })
    
    return {"success": True, "message_id": chat_message["message_id"]}


@router.get("/chat/{party_id}")
async def get_party_chat_history(party_id: str, limit: int = 50):
    """Get party chat history."""
    party = await get_party(party_id)
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    
    history = party.get("chat_history", [])
    return {
        "party_id": party_id,
        "messages": history[-limit:],
        "total": len(history)
    }


# ============ WebSocket for Real-time Party Chat ============
@router.websocket("/ws/{party_id}/{member_id}")
async def party_chat_websocket(websocket: WebSocket, party_id: str, member_id: str):
    """WebSocket connection for real-time party chat."""
    await websocket.accept()
    
    # Verify membership
    party = await get_party(party_id)
    if not party:
        await websocket.close(code=4004)
        return
    
    member = next((m for m in party["members"] if m["member_id"] == member_id), None)
    if not member:
        await websocket.close(code=4003)
        return
    
    # Add to connections
    if party_id not in party_connections:
        party_connections[party_id] = {}
    party_connections[party_id][member_id] = websocket
    
    try:
        # Notify others
        await broadcast_to_party(party_id, {
            "type": "member_online",
            "member_id": member_id,
            "member_name": member["name"]
        }, exclude_id=member_id)
        
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            
            if msg.get("type") == "chat":
                chat_message = {
                    "type": "chat_message",
                    "message_id": str(uuid.uuid4()),
                    "sender_id": member_id,
                    "sender_name": member["name"],
                    "sender_type": member.get("type", "player"),
                    "message": msg.get("message", ""),
                    "is_proximity": msg.get("is_proximity", False),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                # Store and broadcast
                await db.parties.update_one(
                    {"party_id": party_id},
                    {"$push": {"chat_history": {"$each": [chat_message], "$slice": -100}}}
                )
                
                await broadcast_to_party(party_id, chat_message)
            
            elif msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
        pass
    finally:
        # Remove from connections
        if party_id in party_connections and member_id in party_connections[party_id]:
            del party_connections[party_id][member_id]
            if not party_connections[party_id]:
                del party_connections[party_id]
        
        # Notify others
        await broadcast_to_party(party_id, {
            "type": "member_offline",
            "member_id": member_id,
            "member_name": member["name"]
        })
