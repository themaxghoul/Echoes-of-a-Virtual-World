# Bounty Board Router - Exclusive Non-Automatable Tasks
# These bounties require player presence and cannot be completed by AI Partners

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone, timedelta
import uuid
import logging

bounty_board_router = APIRouter(prefix="/bounty-board", tags=["bounty-board"])

logger = logging.getLogger(__name__)

def get_db():
    from server import db
    return db

# ============ EXCLUSIVE BOUNTY TYPES ============
# These tasks CANNOT be automated - require animate entity presence

BOUNTY_TYPES = {
    "rescue_mission": {
        "name": "Rescue Mission",
        "description": "Save NPCs from dangerous situations",
        "ve_multiplier": 1.5,
        "requires_presence": True,
        "min_difficulty": "medium",
        "skills_required": ["combat", "navigation", "first_aid"]
    },
    "scout_uncharted": {
        "name": "Scout Uncharted Territory",
        "description": "Explore unmapped regions and report findings",
        "ve_multiplier": 1.3,
        "requires_presence": True,
        "min_difficulty": "easy",
        "skills_required": ["navigation", "cartography", "survival"]
    },
    "dangerous_recon": {
        "name": "Dangerous Recon",
        "description": "Infiltrate hostile areas and gather intelligence",
        "ve_multiplier": 1.8,
        "requires_presence": True,
        "min_difficulty": "hard",
        "skills_required": ["stealth", "observation", "combat"]
    },
    "host_meeting": {
        "name": "Diplomatic Meeting",
        "description": "Organize and host multi-faction diplomatic events",
        "ve_multiplier": 1.2,
        "requires_presence": True,
        "min_difficulty": "medium",
        "skills_required": ["diplomacy", "leadership", "negotiation"]
    },
    "artifact_recovery": {
        "name": "Artifact Recovery",
        "description": "Retrieve rare and dangerous items from dungeons",
        "ve_multiplier": 1.6,
        "requires_presence": True,
        "min_difficulty": "hard",
        "skills_required": ["combat", "lockpicking", "arcane_knowledge"]
    },
    "monster_bounty": {
        "name": "Monster Bounty",
        "description": "Hunt specific creatures terrorizing regions",
        "ve_multiplier": 1.4,
        "requires_presence": True,
        "min_difficulty": "medium",
        "skills_required": ["combat", "tracking", "monster_lore"]
    },
    "trade_route": {
        "name": "Trade Route Establishment",
        "description": "Personally negotiate new commerce paths",
        "ve_multiplier": 1.25,
        "requires_presence": True,
        "min_difficulty": "medium",
        "skills_required": ["negotiation", "economics", "navigation"]
    },
    "first_discovery": {
        "name": "First Discovery",
        "description": "Test untested elements, materials, or spell combinations",
        "ve_multiplier": 2.0,
        "requires_presence": True,
        "min_difficulty": "expert",
        "skills_required": ["arcane_knowledge", "alchemy", "research"],
        "special": "pioneer_bonus",
        "royalty_percent": 5  # First discoverer gets 5% royalty on future uses
    }
}

DIFFICULTY_REWARDS = {
    "trivial": {"gold_base": 50, "ve_base": 0.005, "xp": 10},
    "easy": {"gold_base": 100, "ve_base": 0.01, "xp": 25},
    "medium": {"gold_base": 250, "ve_base": 0.025, "xp": 50},
    "hard": {"gold_base": 500, "ve_base": 0.05, "xp": 100},
    "expert": {"gold_base": 1000, "ve_base": 0.10, "xp": 200},
    "legendary": {"gold_base": 2500, "ve_base": 0.25, "xp": 500}
}

class CreateBountyRequest(BaseModel):
    bounty_type: str
    title: str
    description: str
    location: str
    difficulty: str = "medium"
    gold_reward: Optional[int] = None  # Auto-calculated if not provided
    ve_reward: Optional[float] = None
    time_limit_hours: int = 72
    max_acceptors: int = 1
    requirements: Dict[str, Any] = Field(default_factory=dict)
    posted_by: str = "Anonymous"

class AcceptBountyRequest(BaseModel):
    bounty_id: str
    user_id: str

class CompleteBountyRequest(BaseModel):
    bounty_id: str
    user_id: str
    proof_data: Dict[str, Any] = Field(default_factory=dict)
    completion_notes: Optional[str] = None

class VerifyPresenceRequest(BaseModel):
    bounty_id: str
    user_id: str
    verification_method: str  # "location", "action", "witness", "artifact"
    verification_data: Dict[str, Any]

# ============ ENDPOINTS ============

@bounty_board_router.get("/types")
async def get_bounty_types():
    """Get all exclusive bounty types"""
    return {
        "types": BOUNTY_TYPES,
        "difficulties": DIFFICULTY_REWARDS,
        "note": "All bounties require animate entity presence - cannot be automated"
    }

@bounty_board_router.post("/create")
async def create_bounty(data: CreateBountyRequest):
    """Create a new exclusive bounty"""
    db = get_db()
    
    if data.bounty_type not in BOUNTY_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid bounty type: {data.bounty_type}")
    
    if data.difficulty not in DIFFICULTY_REWARDS:
        raise HTTPException(status_code=400, detail=f"Invalid difficulty: {data.difficulty}")
    
    bounty_config = BOUNTY_TYPES[data.bounty_type]
    difficulty_config = DIFFICULTY_REWARDS[data.difficulty]
    
    # Calculate rewards
    gold_reward = data.gold_reward or int(difficulty_config["gold_base"] * (1 + (hash(data.title) % 50) / 100))
    ve_reward = data.ve_reward or round(difficulty_config["ve_base"] * bounty_config["ve_multiplier"], 4)
    
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=data.time_limit_hours * 2)  # Board expiry is 2x time limit
    
    bounty_id = f"bnty_{str(uuid.uuid4())[:8]}"
    
    bounty = {
        "bounty_id": bounty_id,
        "type": data.bounty_type,
        "type_info": bounty_config,
        "title": data.title,
        "description": data.description,
        "location": data.location,
        "difficulty": data.difficulty,
        "gold_reward": gold_reward,
        "ve_reward": ve_reward,
        "xp_reward": difficulty_config["xp"],
        "time_limit_hours": data.time_limit_hours,
        "max_acceptors": data.max_acceptors,
        "current_acceptors": 0,
        "requirements": data.requirements,
        "skills_required": bounty_config.get("skills_required", []),
        "posted_by": data.posted_by,
        "posted_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "status": "open",
        "exclusive": True,
        "requires_presence": bounty_config["requires_presence"],
        "accepted_by": [],
        "completed_by": [],
        "first_discovery": data.bounty_type == "first_discovery"
    }
    
    await db.bounty_board.insert_one(bounty)
    bounty.pop("_id", None)
    
    logger.info(f"Bounty created: {bounty_id} - {data.title}")
    
    return {
        "created": True,
        "bounty_id": bounty_id,
        "bounty": bounty
    }

@bounty_board_router.get("/available")
async def get_available_bounties(
    bounty_type: Optional[str] = None,
    difficulty: Optional[str] = None,
    min_gold: Optional[int] = None,
    limit: int = 50
):
    """Get all available bounties on the board"""
    db = get_db()
    
    query = {"status": "open"}
    
    if bounty_type:
        query["type"] = bounty_type
    if difficulty:
        query["difficulty"] = difficulty
    if min_gold:
        query["gold_reward"] = {"$gte": min_gold}
    
    bounties = await db.bounty_board.find(
        query,
        {"_id": 0}
    ).sort("posted_at", -1).limit(limit).to_list(limit)
    
    return {
        "bounties": bounties,
        "count": len(bounties),
        "types_available": list(set(b["type"] for b in bounties))
    }

@bounty_board_router.post("/accept")
async def accept_bounty(data: AcceptBountyRequest):
    """Accept a bounty - begins the timer"""
    db = get_db()
    
    bounty = await db.bounty_board.find_one({"bounty_id": data.bounty_id})
    if not bounty:
        raise HTTPException(status_code=404, detail="Bounty not found")
    
    if bounty["status"] != "open":
        raise HTTPException(status_code=400, detail="Bounty is not available")
    
    if data.user_id in bounty.get("accepted_by", []):
        raise HTTPException(status_code=400, detail="You have already accepted this bounty")
    
    if bounty["current_acceptors"] >= bounty["max_acceptors"]:
        raise HTTPException(status_code=400, detail="Maximum acceptors reached")
    
    now = datetime.now(timezone.utc)
    deadline = now + timedelta(hours=bounty["time_limit_hours"])
    
    # Create acceptance record
    acceptance = {
        "acceptance_id": str(uuid.uuid4()),
        "bounty_id": data.bounty_id,
        "user_id": data.user_id,
        "accepted_at": now.isoformat(),
        "deadline": deadline.isoformat(),
        "status": "active",
        "presence_verified": False,
        "presence_verifications": []
    }
    
    await db.bounty_acceptances.insert_one(acceptance)
    
    # Update bounty
    new_status = "in_progress" if bounty["current_acceptors"] + 1 >= bounty["max_acceptors"] else "open"
    
    await db.bounty_board.update_one(
        {"bounty_id": data.bounty_id},
        {
            "$push": {"accepted_by": data.user_id},
            "$inc": {"current_acceptors": 1},
            "$set": {"status": new_status}
        }
    )
    
    logger.info(f"Bounty accepted: {data.bounty_id} by {data.user_id}")
    
    return {
        "accepted": True,
        "bounty_id": data.bounty_id,
        "acceptance_id": acceptance["acceptance_id"],
        "deadline": deadline.isoformat(),
        "time_remaining_hours": bounty["time_limit_hours"],
        "requires_presence": bounty["requires_presence"],
        "warning": "This bounty requires your physical presence. AI Partners cannot complete it."
    }

@bounty_board_router.post("/verify-presence")
async def verify_presence(data: VerifyPresenceRequest):
    """Verify that a player is present for the bounty (anti-automation check)"""
    db = get_db()
    
    acceptance = await db.bounty_acceptances.find_one({
        "bounty_id": data.bounty_id,
        "user_id": data.user_id,
        "status": "active"
    })
    
    if not acceptance:
        raise HTTPException(status_code=404, detail="No active acceptance found")
    
    verification_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    verification = {
        "verification_id": verification_id,
        "method": data.verification_method,
        "data": data.verification_data,
        "timestamp": now.isoformat(),
        "valid": True  # In production, this would have actual verification logic
    }
    
    await db.bounty_acceptances.update_one(
        {"acceptance_id": acceptance["acceptance_id"]},
        {
            "$push": {"presence_verifications": verification},
            "$set": {"presence_verified": True, "last_verified": now.isoformat()}
        }
    )
    
    return {
        "verified": True,
        "verification_id": verification_id,
        "method": data.verification_method,
        "message": "Presence confirmed. You may continue the bounty."
    }

@bounty_board_router.post("/complete")
async def complete_bounty(data: CompleteBountyRequest):
    """Submit bounty completion - requires presence verification"""
    db = get_db()
    
    bounty = await db.bounty_board.find_one({"bounty_id": data.bounty_id})
    if not bounty:
        raise HTTPException(status_code=404, detail="Bounty not found")
    
    acceptance = await db.bounty_acceptances.find_one({
        "bounty_id": data.bounty_id,
        "user_id": data.user_id,
        "status": "active"
    })
    
    if not acceptance:
        raise HTTPException(status_code=400, detail="You have not accepted this bounty")
    
    # Check presence verification
    if bounty["requires_presence"] and not acceptance.get("presence_verified"):
        raise HTTPException(
            status_code=400, 
            detail="Presence verification required. This bounty cannot be completed remotely."
        )
    
    now = datetime.now(timezone.utc)
    
    # Check deadline
    deadline = datetime.fromisoformat(acceptance["deadline"].replace("Z", "+00:00"))
    if now > deadline:
        await db.bounty_acceptances.update_one(
            {"acceptance_id": acceptance["acceptance_id"]},
            {"$set": {"status": "expired"}}
        )
        raise HTTPException(status_code=400, detail="Bounty deadline has passed")
    
    # Award rewards
    gold_reward = bounty["gold_reward"]
    ve_reward = bounty["ve_reward"]
    xp_reward = bounty["xp_reward"]
    
    # First discovery bonus
    pioneer_bonus = {}
    if bounty.get("first_discovery"):
        pioneer_bonus = {
            "pioneer_title": True,
            "royalty_percent": BOUNTY_TYPES["first_discovery"]["royalty_percent"],
            "discovery_credit": True
        }
        ve_reward *= 1.5  # 50% bonus for first discovery
    
    # Update player wallet
    await db.entity_wallets.update_one(
        {"entity_id": data.user_id},
        {
            "$inc": {
                "gold": gold_reward,
                "balance_ve": ve_reward,
                "bounties_completed": 1
            }
        },
        upsert=True
    )
    
    # Record completion
    completion = {
        "completion_id": str(uuid.uuid4()),
        "bounty_id": data.bounty_id,
        "user_id": data.user_id,
        "completed_at": now.isoformat(),
        "time_taken_hours": (now - datetime.fromisoformat(acceptance["accepted_at"].replace("Z", "+00:00"))).total_seconds() / 3600,
        "gold_earned": gold_reward,
        "ve_earned": ve_reward,
        "xp_earned": xp_reward,
        "proof_data": data.proof_data,
        "notes": data.completion_notes,
        "pioneer_bonus": pioneer_bonus
    }
    
    await db.bounty_completions.insert_one(completion)
    
    # Update acceptance
    await db.bounty_acceptances.update_one(
        {"acceptance_id": acceptance["acceptance_id"]},
        {"$set": {"status": "completed", "completed_at": now.isoformat()}}
    )
    
    # Update bounty
    await db.bounty_board.update_one(
        {"bounty_id": data.bounty_id},
        {
            "$push": {"completed_by": data.user_id},
            "$set": {"status": "completed" if len(bounty.get("completed_by", [])) + 1 >= bounty["max_acceptors"] else bounty["status"]}
        }
    )
    
    logger.info(f"Bounty completed: {data.bounty_id} by {data.user_id}")
    
    return {
        "completed": True,
        "bounty_id": data.bounty_id,
        "rewards": {
            "gold": gold_reward,
            "ve": ve_reward,
            "xp": xp_reward
        },
        "pioneer_bonus": pioneer_bonus if pioneer_bonus else None,
        "completion_id": completion["completion_id"]
    }

@bounty_board_router.get("/my-bounties/{user_id}")
async def get_my_bounties(user_id: str):
    """Get bounties accepted/completed by a user"""
    db = get_db()
    
    # Active bounties
    active_acceptances = await db.bounty_acceptances.find(
        {"user_id": user_id, "status": "active"},
        {"_id": 0}
    ).to_list(50)
    
    active_bounty_ids = [a["bounty_id"] for a in active_acceptances]
    active_bounties = []
    if active_bounty_ids:
        active_bounties = await db.bounty_board.find(
            {"bounty_id": {"$in": active_bounty_ids}},
            {"_id": 0}
        ).to_list(50)
    
    # Completed bounties
    completed = await db.bounty_completions.find(
        {"user_id": user_id},
        {"_id": 0}
    ).sort("completed_at", -1).limit(20).to_list(20)
    
    # Stats
    total_gold = sum(c["gold_earned"] for c in completed)
    total_ve = sum(c["ve_earned"] for c in completed)
    
    return {
        "active": active_bounties,
        "active_acceptances": active_acceptances,
        "completed": completed,
        "stats": {
            "total_completed": len(completed),
            "total_gold_earned": total_gold,
            "total_ve_earned": total_ve
        }
    }

@bounty_board_router.get("/stats")
async def get_bounty_board_stats():
    """Get overall bounty board statistics"""
    db = get_db()
    
    total_bounties = await db.bounty_board.count_documents({})
    open_bounties = await db.bounty_board.count_documents({"status": "open"})
    completed_bounties = await db.bounty_completions.count_documents({})
    
    # By type
    pipeline = [
        {"$group": {"_id": "$type", "count": {"$sum": 1}}}
    ]
    by_type = await db.bounty_board.aggregate(pipeline).to_list(20)
    
    # Total rewards paid
    reward_pipeline = [
        {"$group": {
            "_id": None,
            "total_gold": {"$sum": "$gold_earned"},
            "total_ve": {"$sum": "$ve_earned"}
        }}
    ]
    rewards = await db.bounty_completions.aggregate(reward_pipeline).to_list(1)
    
    return {
        "total_bounties_posted": total_bounties,
        "open_bounties": open_bounties,
        "completed_bounties": completed_bounties,
        "bounties_by_type": {b["_id"]: b["count"] for b in by_type if b["_id"]},
        "total_rewards_paid": {
            "gold": rewards[0]["total_gold"] if rewards else 0,
            "ve": rewards[0]["total_ve"] if rewards else 0
        },
        "exclusive_types": list(BOUNTY_TYPES.keys())
    }

@bounty_board_router.post("/seed-bounties")
async def seed_sample_bounties():
    """Seed the bounty board with sample bounties for testing"""
    sample_bounties = [
        {
            "bounty_type": "rescue_mission",
            "title": "The Lost Merchant's Daughter",
            "description": "A merchant's daughter has gone missing in the Shadowfen Marshes. Last seen near the abandoned watchtower. Time is of the essence.",
            "location": "Shadowfen Marshes",
            "difficulty": "hard",
            "gold_reward": 500,
            "ve_reward": 0.05,
            "time_limit_hours": 48,
            "posted_by": "Merchant Guild"
        },
        {
            "bounty_type": "scout_uncharted",
            "title": "Map the Crystal Caverns",
            "description": "The Cartographer's Society needs detailed maps of the newly discovered Crystal Caverns beneath Mount Solara. Beware of the cave-dwelling creatures.",
            "location": "Mount Solara",
            "difficulty": "medium",
            "gold_reward": 300,
            "ve_reward": 0.03,
            "time_limit_hours": 72,
            "posted_by": "Cartographer's Society"
        },
        {
            "bounty_type": "monster_bounty",
            "title": "The Crimson Wyrm",
            "description": "A deadly wyrm has been terrorizing the eastern farmlands, destroying crops and livestock. Bring proof of its demise.",
            "location": "Eastern Farmlands",
            "difficulty": "legendary",
            "gold_reward": 1500,
            "ve_reward": 0.15,
            "time_limit_hours": 168,
            "posted_by": "Royal Guard"
        },
        {
            "bounty_type": "first_discovery",
            "title": "Synthesize Void Essence",
            "description": "The Arcane Council seeks a brave soul to attempt the first synthesis of Void Essence using the new lunar fragments. This has never been done before.",
            "location": "Arcane Tower",
            "difficulty": "expert",
            "gold_reward": 800,
            "ve_reward": 0.25,
            "time_limit_hours": 24,
            "posted_by": "Arcane Council"
        },
        {
            "bounty_type": "host_meeting",
            "title": "The Trilateral Summit",
            "description": "Organize and host a peace summit between the Forest Wardens, Mining Consortium, and River Folk. Tensions are high.",
            "location": "Neutral Grounds",
            "difficulty": "medium",
            "gold_reward": 400,
            "ve_reward": 0.04,
            "time_limit_hours": 96,
            "posted_by": "Council of Elders"
        },
        {
            "bounty_type": "dangerous_recon",
            "title": "The Obsidian Fortress",
            "description": "Infiltrate the Obsidian Fortress and gather intelligence on the Shadow Legion's movements. Do not engage - observe only.",
            "location": "Obsidian Fortress",
            "difficulty": "legendary",
            "gold_reward": 2000,
            "ve_reward": 0.20,
            "time_limit_hours": 72,
            "posted_by": "Shadow Network"
        },
        {
            "bounty_type": "artifact_recovery",
            "title": "The Sunken Crown",
            "description": "The Crown of the Last King lies at the bottom of Lake Echoes. Retrieve it before the cultists do.",
            "location": "Lake Echoes",
            "difficulty": "hard",
            "gold_reward": 750,
            "ve_reward": 0.08,
            "time_limit_hours": 48,
            "posted_by": "Royal Archives"
        }
    ]
    
    created = []
    for bounty_data in sample_bounties:
        req = CreateBountyRequest(**bounty_data)
        result = await create_bounty(req)
        created.append(result["bounty_id"])
    
    return {
        "seeded": True,
        "bounties_created": len(created),
        "bounty_ids": created
    }
