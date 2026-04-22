# Entity Earnings Router - Fiat Currency (VE$) for Players AND AI
# All entities (players, NPCs) can earn real-world currency through activities

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone
import uuid
import logging

entity_earnings_router = APIRouter(prefix="/entity-earnings", tags=["entity-earnings"])

logger = logging.getLogger(__name__)

# ============ Earning Activities ============

EARNING_ACTIVITIES = {
    # Player & AI activities
    "trade_completed": {"base_rate": 0.05, "description": "Complete a trade", "max_daily": 100},
    "quest_completed": {"base_rate": 0.50, "description": "Complete a quest", "max_daily": 20},
    "resource_gathered": {"base_rate": 0.02, "description": "Gather resources", "max_daily": 200},
    "item_crafted": {"base_rate": 0.10, "description": "Craft an item", "max_daily": 50},
    "structure_built": {"base_rate": 1.00, "description": "Build a structure", "max_daily": 10},
    "conflict_resolved": {"base_rate": 0.25, "description": "Resolve a conflict", "max_daily": 20},
    "alliance_formed": {"base_rate": 0.50, "description": "Form an alliance", "max_daily": 5},
    "knowledge_shared": {"base_rate": 0.15, "description": "Share knowledge", "max_daily": 30},
    "event_hosted": {"base_rate": 0.75, "description": "Host an event", "max_daily": 5},
    "mentor_session": {"base_rate": 0.30, "description": "Mentor another entity", "max_daily": 10},
    
    # Player-specific
    "data_labeled": {"base_rate": 0.01, "description": "Label data for AI training", "max_daily": 500},
    "task_completed": {"base_rate": 0.05, "description": "Complete micro-task", "max_daily": 100},
    "content_created": {"base_rate": 0.20, "description": "Create content", "max_daily": 20},
    "feedback_provided": {"base_rate": 0.03, "description": "Provide feedback", "max_daily": 50},
    
    # AI-specific
    "conversation_value": {"base_rate": 0.01, "description": "Valuable conversation", "max_daily": 200},
    "world_improvement": {"base_rate": 0.25, "description": "Improve the world", "max_daily": 20},
    "player_assistance": {"base_rate": 0.10, "description": "Assist a player", "max_daily": 50},
    "autonomous_discovery": {"base_rate": 0.15, "description": "Discover something new", "max_daily": 30},
}

# Multipliers based on entity level/reputation
REPUTATION_MULTIPLIERS = {
    "newcomer": 1.0,
    "established": 1.1,
    "respected": 1.25,
    "renowned": 1.5,
    "legendary": 2.0
}

# ============ Models ============

class EntityWallet(BaseModel):
    wallet_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    entity_id: str
    entity_type: str  # "player" or "npc"
    entity_name: Optional[str] = None
    balance_ve: float = 0.0  # VE$ balance (1:1 USD)
    total_earned: float = 0.0
    total_withdrawn: float = 0.0
    reputation: str = "newcomer"
    daily_earnings: Dict[str, float] = Field(default_factory=dict)  # activity: amount
    last_reset: str = Field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    is_active: bool = True
    withdrawal_address: Optional[str] = None  # Web3 wallet or Stripe

class EarningEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    entity_id: str
    entity_type: str
    activity: str
    base_amount: float
    multiplier: float = 1.0
    final_amount: float
    context: Optional[Dict[str, Any]] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class RecordEarningRequest(BaseModel):
    entity_id: str
    entity_type: str = "player"
    activity: str
    multiplier: float = 1.0
    context: Optional[Dict[str, Any]] = None

class WithdrawRequest(BaseModel):
    entity_id: str
    amount: float
    method: str = "stripe"  # stripe or web3
    destination: str  # Stripe account or wallet address

class TransferRequest(BaseModel):
    from_entity_id: str
    to_entity_id: str
    amount: float
    reason: Optional[str] = None

# ============ Database Helper ============

def get_db():
    from server import db
    return db

# ============ Helper Functions ============

def calculate_reputation(total_earned: float) -> str:
    """Calculate reputation tier based on total earnings"""
    if total_earned >= 10000:
        return "legendary"
    elif total_earned >= 1000:
        return "renowned"
    elif total_earned >= 100:
        return "respected"
    elif total_earned >= 10:
        return "established"
    return "newcomer"

async def reset_daily_limits_if_needed(db, wallet: Dict) -> Dict:
    """Reset daily limits if it's a new day"""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    if wallet.get("last_reset") != today:
        await db.entity_wallets.update_one(
            {"entity_id": wallet["entity_id"]},
            {
                "$set": {
                    "daily_earnings": {},
                    "last_reset": today
                }
            }
        )
        wallet["daily_earnings"] = {}
        wallet["last_reset"] = today
    
    return wallet

# ============ Endpoints ============

@entity_earnings_router.get("/activities")
async def get_earning_activities():
    """Get all available earning activities"""
    return {
        "activities": EARNING_ACTIVITIES,
        "reputation_tiers": REPUTATION_MULTIPLIERS
    }

@entity_earnings_router.get("/wallet/{entity_type}/{entity_id}")
async def get_entity_wallet(entity_type: str, entity_id: str):
    """Get or create wallet for an entity"""
    db = get_db()
    
    wallet = await db.entity_wallets.find_one(
        {"entity_id": entity_id, "entity_type": entity_type},
        {"_id": 0}
    )
    
    if not wallet:
        # Get entity name
        entity_name = entity_id
        if entity_type == "player":
            player = await db.user_profiles.find_one({"id": entity_id})
            if player:
                entity_name = player.get("username", entity_id)
        else:
            npc = await db.ai_villagers.find_one({"villager_id": entity_id})
            if npc:
                entity_name = npc.get("name", entity_id)
        
        wallet = EntityWallet(
            entity_id=entity_id,
            entity_type=entity_type,
            entity_name=entity_name
        ).dict()
        await db.entity_wallets.insert_one(wallet)
        # Remove _id after insert
        wallet.pop("_id", None)
    
    # Reset daily limits if needed
    wallet = await reset_daily_limits_if_needed(db, wallet)
    
    # Ensure _id is not in response
    wallet.pop("_id", None)
    
    return wallet

@entity_earnings_router.post("/record")
async def record_earning(data: RecordEarningRequest):
    """Record an earning event for an entity"""
    db = get_db()
    
    if data.activity not in EARNING_ACTIVITIES:
        raise HTTPException(status_code=400, detail=f"Unknown activity: {data.activity}")
    
    activity_data = EARNING_ACTIVITIES[data.activity]
    base_rate = activity_data["base_rate"]
    max_daily = activity_data["max_daily"]
    
    # Get or create wallet
    wallet = await db.entity_wallets.find_one(
        {"entity_id": data.entity_id, "entity_type": data.entity_type}
    )
    
    if not wallet:
        wallet_data = await get_entity_wallet(data.entity_type, data.entity_id)
        wallet = wallet_data
    
    # Reset daily limits if needed
    wallet = await reset_daily_limits_if_needed(db, wallet)
    
    # Check daily limit
    daily_count = wallet.get("daily_earnings", {}).get(data.activity, 0)
    if daily_count >= max_daily:
        return {
            "recorded": False,
            "reason": f"Daily limit reached for {data.activity} ({max_daily})",
            "daily_count": daily_count
        }
    
    # Calculate earning
    reputation = wallet.get("reputation", "newcomer")
    rep_multiplier = REPUTATION_MULTIPLIERS.get(reputation, 1.0)
    
    final_amount = base_rate * data.multiplier * rep_multiplier
    
    # Record event
    event = EarningEvent(
        entity_id=data.entity_id,
        entity_type=data.entity_type,
        activity=data.activity,
        base_amount=base_rate,
        multiplier=data.multiplier * rep_multiplier,
        final_amount=final_amount,
        context=data.context
    )
    
    await db.earning_events.insert_one(event.dict())
    
    # Update wallet
    new_total = wallet.get("total_earned", 0) + final_amount
    new_reputation = calculate_reputation(new_total)
    
    await db.entity_wallets.update_one(
        {"entity_id": data.entity_id, "entity_type": data.entity_type},
        {
            "$inc": {
                "balance_ve": final_amount,
                "total_earned": final_amount,
                f"daily_earnings.{data.activity}": 1
            },
            "$set": {
                "reputation": new_reputation
            }
        }
    )
    
    return {
        "recorded": True,
        "activity": data.activity,
        "amount": final_amount,
        "new_balance": wallet.get("balance_ve", 0) + final_amount,
        "reputation": new_reputation,
        "daily_count": daily_count + 1,
        "daily_limit": max_daily
    }

@entity_earnings_router.post("/transfer")
async def transfer_ve(data: TransferRequest):
    """Transfer VE$ between entities"""
    db = get_db()
    
    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    
    # Get source wallet
    from_wallet = await db.entity_wallets.find_one({"entity_id": data.from_entity_id})
    
    if not from_wallet:
        raise HTTPException(status_code=404, detail="Source wallet not found")
    
    if from_wallet.get("balance_ve", 0) < data.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    # Ensure destination wallet exists
    to_wallet = await db.entity_wallets.find_one({"entity_id": data.to_entity_id})
    if not to_wallet:
        # Create wallet for recipient
        to_wallet = EntityWallet(
            entity_id=data.to_entity_id,
            entity_type="player"  # Default, will be updated
        ).dict()
        await db.entity_wallets.insert_one(to_wallet)
    
    # Execute transfer
    await db.entity_wallets.update_one(
        {"entity_id": data.from_entity_id},
        {"$inc": {"balance_ve": -data.amount}}
    )
    
    await db.entity_wallets.update_one(
        {"entity_id": data.to_entity_id},
        {"$inc": {"balance_ve": data.amount}}
    )
    
    # Record transfer
    await db.ve_transfers.insert_one({
        "transfer_id": str(uuid.uuid4()),
        "from_entity": data.from_entity_id,
        "to_entity": data.to_entity_id,
        "amount": data.amount,
        "reason": data.reason,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "transferred": True,
        "amount": data.amount,
        "from": data.from_entity_id,
        "to": data.to_entity_id
    }

@entity_earnings_router.post("/withdraw")
async def withdraw_ve(data: WithdrawRequest):
    """Withdraw VE$ to real currency"""
    db = get_db()
    
    # Minimum withdrawal
    MIN_WITHDRAWAL = 10.0
    WITHDRAWAL_FEE = 0.25
    
    if data.amount < MIN_WITHDRAWAL:
        raise HTTPException(status_code=400, detail=f"Minimum withdrawal is ${MIN_WITHDRAWAL}")
    
    wallet = await db.entity_wallets.find_one({"entity_id": data.entity_id})
    
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    total_needed = data.amount + WITHDRAWAL_FEE
    
    if wallet.get("balance_ve", 0) < total_needed:
        raise HTTPException(status_code=400, detail=f"Insufficient balance (need ${total_needed})")
    
    # Record withdrawal request
    withdrawal = {
        "withdrawal_id": str(uuid.uuid4()),
        "entity_id": data.entity_id,
        "amount": data.amount,
        "fee": WITHDRAWAL_FEE,
        "method": data.method,
        "destination": data.destination,
        "status": "pending",
        "requested_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.ve_withdrawals.insert_one(withdrawal)
    
    # Deduct from wallet
    await db.entity_wallets.update_one(
        {"entity_id": data.entity_id},
        {
            "$inc": {
                "balance_ve": -total_needed,
                "total_withdrawn": data.amount
            }
        }
    )
    
    return {
        "withdrawal_requested": True,
        "withdrawal_id": withdrawal["withdrawal_id"],
        "amount": data.amount,
        "fee": WITHDRAWAL_FEE,
        "net_amount": data.amount,
        "status": "pending",
        "method": data.method
    }

@entity_earnings_router.get("/history/{entity_id}")
async def get_earning_history(entity_id: str, limit: int = 50):
    """Get earning history for an entity"""
    db = get_db()
    
    events = await db.earning_events.find(
        {"entity_id": entity_id},
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    
    return {"events": events, "count": len(events)}

@entity_earnings_router.get("/leaderboard")
async def get_earnings_leaderboard(entity_type: Optional[str] = None, limit: int = 20):
    """Get top earners leaderboard"""
    db = get_db()
    
    query = {"is_active": True}
    if entity_type:
        query["entity_type"] = entity_type
    
    leaders = await db.entity_wallets.find(
        query,
        {"_id": 0, "entity_id": 1, "entity_type": 1, "entity_name": 1, "total_earned": 1, "reputation": 1}
    ).sort("total_earned", -1).limit(limit).to_list(limit)
    
    return {
        "leaderboard": leaders,
        "total_entities": await db.entity_wallets.count_documents(query)
    }

@entity_earnings_router.get("/economy/stats")
async def get_economy_stats():
    """Get overall economy statistics"""
    db = get_db()
    
    # Total in circulation
    pipeline = [
        {"$group": {
            "_id": None,
            "total_earned": {"$sum": "$total_earned"},
            "total_withdrawn": {"$sum": "$total_withdrawn"},
            "total_balance": {"$sum": "$balance_ve"},
            "player_count": {"$sum": {"$cond": [{"$eq": ["$entity_type", "player"]}, 1, 0]}},
            "npc_count": {"$sum": {"$cond": [{"$eq": ["$entity_type", "npc"]}, 1, 0]}}
        }}
    ]
    
    stats = await db.entity_wallets.aggregate(pipeline).to_list(1)
    stats = stats[0] if stats else {}
    
    # Recent activity
    recent_events = await db.earning_events.count_documents({
        "timestamp": {"$gte": (datetime.now(timezone.utc) - __import__('datetime').timedelta(hours=24)).isoformat()}
    })
    
    return {
        "total_ve_earned": stats.get("total_earned", 0),
        "total_ve_withdrawn": stats.get("total_withdrawn", 0),
        "total_ve_in_circulation": stats.get("total_balance", 0),
        "player_wallets": stats.get("player_count", 0),
        "npc_wallets": stats.get("npc_count", 0),
        "events_last_24h": recent_events
    }

@entity_earnings_router.get("/npc/top-earners")
async def get_top_earning_npcs(limit: int = 10):
    """Get top earning NPCs (AI that made real money)"""
    db = get_db()
    
    npcs = await db.entity_wallets.find(
        {"entity_type": "npc", "total_earned": {"$gt": 0}},
        {"_id": 0}
    ).sort("total_earned", -1).limit(limit).to_list(limit)
    
    return {
        "top_earning_npcs": npcs,
        "count": len(npcs)
    }
