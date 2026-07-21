"""
Discovery Lab System
====================
Handles material/spell experimentation with First Discovery tracking.
First Discoverers receive permanent credit, bonus VE$, and royalties.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import os
import uuid
import hashlib
import secrets

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

router = APIRouter(prefix="/api/discovery", tags=["Discovery Lab"])

# ============ Experiment Types ============
EXPERIMENT_TYPES = {
    "material_fusion": {
        "name": "Material Fusion",
        "description": "Combine materials to create new compounds",
        "base_success_rate": 0.4,
        "ve_bonus_multiplier": 1.0
    },
    "spell_synthesis": {
        "name": "Spell Synthesis",
        "description": "Merge spell essences to forge new magic",
        "base_success_rate": 0.3,
        "ve_bonus_multiplier": 1.5
    },
    "enchantment_binding": {
        "name": "Enchantment Binding",
        "description": "Bind magical properties to items",
        "base_success_rate": 0.35,
        "ve_bonus_multiplier": 1.25
    }
}

# First Discovery rewards
FIRST_DISCOVERY_REWARDS = {
    "ve_bonus": 50.0,  # Base VE$ bonus
    "xp_bonus": 500,   # Base XP bonus
    "royalty_rate": 0.01  # 1% of all future uses
}


def generate_combination_hash(ingredients: List[str], experiment_type: str) -> str:
    """Generate a unique hash for a combination of ingredients."""
    sorted_ingredients = sorted(ingredients)
    combo_string = f"{experiment_type}:{':'.join(sorted_ingredients)}"
    return hashlib.sha256(combo_string.encode()).hexdigest()[:16]


class ExperimentRequest(BaseModel):
    user_id: str = Field(..., description="User performing the experiment")
    user_name: str = Field(..., description="Display name of user")
    experiment_type: str = Field(..., description="Type of experiment")
    experiment_name: str = Field(default="", description="Optional name for the experiment")
    ingredients: List[str] = Field(..., description="List of material/component IDs")


class DiscoveryResult(BaseModel):
    success: bool
    is_first_discovery: bool = False
    discovery_name: Optional[str] = None
    discovery_id: Optional[str] = None
    rewards: Optional[Dict[str, Any]] = None
    message: str = ""


# ============ API Endpoints ============

@router.get("/types")
async def get_experiment_types():
    """Get all experiment types and their properties."""
    return {
        "experiment_types": EXPERIMENT_TYPES,
        "first_discovery_rewards": FIRST_DISCOVERY_REWARDS
    }


@router.post("/experiment")
async def run_experiment(request: ExperimentRequest):
    """
    Run an experiment with the given ingredients.
    First discoveries are tracked and rewarded.
    """
    import random
    
    if request.experiment_type not in EXPERIMENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid experiment type. Valid: {list(EXPERIMENT_TYPES.keys())}"
        )
    
    if len(request.ingredients) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 ingredients")
    
    if len(request.ingredients) > 4:
        raise HTTPException(status_code=400, detail="Maximum 4 ingredients")
    
    exp_type = EXPERIMENT_TYPES[request.experiment_type]
    combo_hash = generate_combination_hash(request.ingredients, request.experiment_type)
    
    # Check if this combination has been discovered before
    existing = await db.discoveries.find_one({"combo_hash": combo_hash})
    is_first_discovery = existing is None
    
    # Calculate success rate (first attempts have slightly lower rate)
    base_rate = exp_type["base_success_rate"]
    if is_first_discovery:
        success_rate = base_rate * 0.8  # 20% harder for first attempts
    else:
        success_rate = base_rate * 1.2  # 20% easier for known combinations
    
    # Roll for success - using secrets for better randomness
    success = secrets.randbelow(1000) / 1000.0 < success_rate
    
    if not success:
        # Record failed attempt
        await db.experiment_attempts.insert_one({
            "attempt_id": str(uuid.uuid4()),
            "user_id": request.user_id,
            "experiment_type": request.experiment_type,
            "ingredients": request.ingredients,
            "combo_hash": combo_hash,
            "success": False,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return DiscoveryResult(
            success=False,
            message="The experiment failed. The ingredients didn't combine properly."
        )
    
    # Experiment succeeded!
    discovery_id = str(uuid.uuid4())
    discovery_name = request.experiment_name or f"Discovery #{discovery_id[:8]}"
    
    rewards = {}
    
    if is_first_discovery:
        # FIRST DISCOVERY! 
        ve_bonus = FIRST_DISCOVERY_REWARDS["ve_bonus"] * exp_type["ve_bonus_multiplier"]
        xp_bonus = FIRST_DISCOVERY_REWARDS["xp_bonus"]
        
        # Record the discovery
        discovery_record = {
            "discovery_id": discovery_id,
            "combo_hash": combo_hash,
            "name": discovery_name,
            "experiment_type": request.experiment_type,
            "ingredients": request.ingredients,
            "discoverer_id": request.user_id,
            "discoverer_name": request.user_name,
            "first_discovered": datetime.now(timezone.utc).isoformat(),
            "times_reproduced": 0,
            "royalty_rate": FIRST_DISCOVERY_REWARDS["royalty_rate"],
            "total_royalties_earned": 0.0
        }
        await db.discoveries.insert_one(discovery_record)
        
        # Award VE$ to discoverer
        await db.earnings_transactions.insert_one({
            "transaction_id": str(uuid.uuid4()),
            "user_id": request.user_id,
            "amount": ve_bonus,
            "type": "first_discovery",
            "description": f"First Discovery: {discovery_name}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Update user earnings
        await db.user_profiles.update_one(
            {"id": request.user_id},
            {"$inc": {"ve_balance": ve_bonus, "total_earned": ve_bonus}}
        )
        
        rewards = {
            "ve_bonus": ve_bonus,
            "xp": xp_bonus,
            "royalty_rate": f"{FIRST_DISCOVERY_REWARDS['royalty_rate'] * 100}%"
        }
    else:
        # Known discovery - give smaller reward, pay royalty to original discoverer
        xp_bonus = 50
        ve_earned = 5.0
        royalty = ve_earned * existing.get("royalty_rate", 0.01)
        
        # Update discovery reproduction count
        await db.discoveries.update_one(
            {"combo_hash": combo_hash},
            {
                "$inc": {
                    "times_reproduced": 1,
                    "total_royalties_earned": royalty
                }
            }
        )
        
        # Pay royalty to original discoverer
        if existing.get("discoverer_id"):
            await db.earnings_transactions.insert_one({
                "transaction_id": str(uuid.uuid4()),
                "user_id": existing["discoverer_id"],
                "amount": royalty,
                "type": "discovery_royalty",
                "description": f"Royalty from {discovery_name} reproduction",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            await db.user_profiles.update_one(
                {"id": existing["discoverer_id"]},
                {"$inc": {"ve_balance": royalty, "total_earned": royalty}}
            )
        
        discovery_name = existing.get("name", discovery_name)
        rewards = {"xp": xp_bonus, "ve_earned": ve_earned}
    
    # Record successful attempt
    await db.experiment_attempts.insert_one({
        "attempt_id": str(uuid.uuid4()),
        "user_id": request.user_id,
        "experiment_type": request.experiment_type,
        "experiment_name": discovery_name,
        "ingredients": request.ingredients,
        "combo_hash": combo_hash,
        "success": True,
        "is_first_discovery": is_first_discovery,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return DiscoveryResult(
        success=True,
        is_first_discovery=is_first_discovery,
        discovery_name=discovery_name,
        discovery_id=discovery_id if is_first_discovery else existing.get("discovery_id"),
        rewards=rewards,
        message="First discovery! You are the pioneer!" if is_first_discovery else "Experiment successful!"
    )


@router.get("/recent")
async def get_recent_discoveries(limit: int = 20):
    """Get recent world discoveries."""
    cursor = db.discoveries.find(
        {},
        {"_id": 0, "combo_hash": 0}
    ).sort("first_discovered", -1).limit(limit)
    
    discoveries = await cursor.to_list(length=limit)
    
    # Add time ago
    now = datetime.now(timezone.utc)
    for d in discoveries:
        if d.get("first_discovered"):
            try:
                disc_time = datetime.fromisoformat(d["first_discovered"].replace("Z", "+00:00"))
                delta = now - disc_time
                if delta.days > 0:
                    d["time_ago"] = f"{delta.days}d ago"
                elif delta.seconds > 3600:
                    d["time_ago"] = f"{delta.seconds // 3600}h ago"
                else:
                    d["time_ago"] = f"{delta.seconds // 60}m ago"
            except:
                d["time_ago"] = "Recently"
        
        d["discoverer"] = d.get("discoverer_name", "Unknown")
        d["type"] = EXPERIMENT_TYPES.get(d.get("experiment_type", ""), {}).get("name", d.get("experiment_type"))
        d["name"] = d.get("name", "Unknown Discovery")
    
    return {"discoveries": discoveries}


@router.get("/user/{user_id}")
async def get_user_discoveries(user_id: str):
    """Get all discoveries by a specific user."""
    cursor = db.discoveries.find(
        {"discoverer_id": user_id},
        {"_id": 0, "combo_hash": 0}
    ).sort("first_discovered", -1)
    
    discoveries = await cursor.to_list(length=100)
    
    for d in discoveries:
        d["is_first"] = True  # All in this list are first discoveries
        d["type"] = EXPERIMENT_TYPES.get(d.get("experiment_type", ""), {}).get("name", d.get("experiment_type"))
        d["name"] = d.get("name", "Unknown Discovery")
    
    # Also get successful reproductions
    repro_cursor = db.experiment_attempts.find(
        {"user_id": user_id, "success": True, "is_first_discovery": False},
        {"_id": 0}
    ).sort("timestamp", -1).limit(50)
    
    reproductions = await repro_cursor.to_list(length=50)
    
    return {
        "discoveries": discoveries,
        "total_first_discoveries": len(discoveries),
        "reproductions": reproductions
    }


@router.get("/check/{combo_hash}")
async def check_if_discovered(combo_hash: str):
    """Check if a specific combination has been discovered."""
    existing = await db.discoveries.find_one(
        {"combo_hash": combo_hash},
        {"_id": 0}
    )
    
    if existing:
        return {
            "discovered": True,
            "discoverer": existing.get("discoverer_name"),
            "name": existing.get("name"),
            "times_reproduced": existing.get("times_reproduced", 0)
        }
    
    return {"discovered": False}


@router.get("/stats")
async def get_discovery_stats():
    """Get overall discovery statistics."""
    total_discoveries = await db.discoveries.count_documents({})
    total_attempts = await db.experiment_attempts.count_documents({})
    successful_attempts = await db.experiment_attempts.count_documents({"success": True})
    
    # Top discoverers
    pipeline = [
        {"$group": {"_id": "$discoverer_id", "name": {"$first": "$discoverer_name"}, "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    top_discoverers = await db.discoveries.aggregate(pipeline).to_list(length=10)
    
    return {
        "total_discoveries": total_discoveries,
        "total_attempts": total_attempts,
        "successful_attempts": successful_attempts,
        "success_rate": round(successful_attempts / max(total_attempts, 1) * 100, 1),
        "top_discoverers": [
            {"name": d.get("name", "Unknown"), "discoveries": d["count"]}
            for d in top_discoverers
        ]
    }
