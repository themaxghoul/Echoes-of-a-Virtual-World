# AI Partner & Automated Income System
# Compute power runs AI programs that generate passive income (Gold + VE$)
# Philosophy: AI offloads tasks and earns money for players

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone, timedelta
import uuid
import logging
import random
import math

ai_partner_router = APIRouter(prefix="/ai-partner", tags=["ai-partner"])

logger = logging.getLogger(__name__)

# ============ AI PROGRAM TYPES ============
# Different AI programs that can be deployed to earn passive income

AI_PROGRAMS = {
    "market_analyst": {
        "name": "Market Analyst AI",
        "description": "Analyzes market trends and executes optimal trades",
        "icon": "chart-line",
        "compute_required": 50,  # Minimum compute needed
        "base_gold_per_hour": 10,
        "base_ve_per_hour": 0.02,
        "scaling_factor": 1.5,  # More compute = more earnings
        "max_multiplier": 5.0,
        "risk_level": "medium",
        "category": "financial"
    },
    "resource_harvester": {
        "name": "Resource Harvester AI",
        "description": "Autonomous drones that gather resources from your lands",
        "icon": "pickaxe",
        "compute_required": 30,
        "base_gold_per_hour": 15,
        "base_ve_per_hour": 0.01,
        "scaling_factor": 1.3,
        "max_multiplier": 4.0,
        "risk_level": "low",
        "category": "gathering"
    },
    "craft_optimizer": {
        "name": "Craft Optimizer AI",
        "description": "Optimizes production lines and creates items for sale",
        "icon": "hammer",
        "compute_required": 40,
        "base_gold_per_hour": 12,
        "base_ve_per_hour": 0.015,
        "scaling_factor": 1.4,
        "max_multiplier": 4.5,
        "risk_level": "low",
        "category": "production"
    },
    "quest_runner": {
        "name": "Quest Runner AI",
        "description": "AI companion that completes simple quests autonomously",
        "icon": "scroll",
        "compute_required": 60,
        "base_gold_per_hour": 20,
        "base_ve_per_hour": 0.025,
        "scaling_factor": 1.6,
        "max_multiplier": 6.0,
        "risk_level": "medium",
        "category": "adventure"
    },
    "npc_merchant": {
        "name": "NPC Merchant AI",
        "description": "Runs your shops and negotiates with NPCs automatically",
        "icon": "store",
        "compute_required": 35,
        "base_gold_per_hour": 18,
        "base_ve_per_hour": 0.02,
        "scaling_factor": 1.4,
        "max_multiplier": 5.0,
        "risk_level": "low",
        "category": "commerce"
    },
    "farm_manager": {
        "name": "Farm Manager AI",
        "description": "Manages crops, livestock, and agricultural operations",
        "icon": "wheat",
        "compute_required": 25,
        "base_gold_per_hour": 8,
        "base_ve_per_hour": 0.01,
        "scaling_factor": 1.2,
        "max_multiplier": 3.5,
        "risk_level": "very_low",
        "category": "agriculture"
    },
    "dungeon_crawler": {
        "name": "Dungeon Crawler AI",
        "description": "Explores dungeons and collects loot while you're away",
        "icon": "dungeon",
        "compute_required": 80,
        "base_gold_per_hour": 35,
        "base_ve_per_hour": 0.04,
        "scaling_factor": 1.8,
        "max_multiplier": 8.0,
        "risk_level": "high",
        "category": "adventure"
    },
    "research_assistant": {
        "name": "Research Assistant AI",
        "description": "Discovers new technologies and unlocks skill bonuses",
        "icon": "flask",
        "compute_required": 70,
        "base_gold_per_hour": 5,
        "base_ve_per_hour": 0.03,
        "scaling_factor": 1.5,
        "max_multiplier": 5.0,
        "risk_level": "low",
        "category": "research",
        "bonus_type": "skill_xp"
    },
    "security_monitor": {
        "name": "Security Monitor AI",
        "description": "Protects your assets and deters thieves/raiders",
        "icon": "shield",
        "compute_required": 45,
        "base_gold_per_hour": 0,
        "base_ve_per_hour": 0.005,
        "scaling_factor": 1.3,
        "max_multiplier": 4.0,
        "risk_level": "none",
        "category": "defense",
        "bonus_type": "protection"
    },
    "energy_converter": {
        "name": "Energy Converter AI",
        "description": "Converts excess compute into energy credits (late-game)",
        "icon": "zap",
        "compute_required": 200,
        "base_gold_per_hour": 0,
        "base_ve_per_hour": 0.10,
        "scaling_factor": 2.0,
        "max_multiplier": 10.0,
        "risk_level": "none",
        "category": "energy",
        "unlocks_at_compute": 1000  # Need 1000 total compute to unlock
    }
}

# Risk outcomes (for medium/high risk programs)
RISK_OUTCOMES = {
    "very_low": {"failure_chance": 0.01, "loss_multiplier": 0.1},
    "low": {"failure_chance": 0.05, "loss_multiplier": 0.2},
    "medium": {"failure_chance": 0.10, "loss_multiplier": 0.3},
    "high": {"failure_chance": 0.20, "loss_multiplier": 0.5},
    "none": {"failure_chance": 0.0, "loss_multiplier": 0.0}
}

# ============ MODELS ============

class DeployAIProgram(BaseModel):
    user_id: str
    program_type: str
    compute_allocation: float  # How much compute to dedicate
    auto_reinvest: bool = False  # Reinvest earnings into more compute

class AIPartnerRelationship(BaseModel):
    user_id: str
    trust_level: float = 50.0  # 0-100, affects earnings
    interactions: int = 0
    gifts_given: int = 0
    tasks_completed: int = 0

# MongoDB reference
def get_db():
    from server import db
    return db

# ============ HELPER FUNCTIONS ============

def calculate_earnings(program_type: str, compute: float, trust_level: float, hours: float) -> Dict[str, float]:
    """Calculate gold and VE$ earnings based on compute, trust, and time"""
    if program_type not in AI_PROGRAMS:
        return {"gold": 0, "ve": 0}
    
    config = AI_PROGRAMS[program_type]
    
    # Check minimum compute
    if compute < config["compute_required"]:
        return {"gold": 0, "ve": 0}
    
    # Calculate compute multiplier (diminishing returns)
    compute_ratio = compute / config["compute_required"]
    compute_mult = min(
        1.0 + (math.log10(compute_ratio + 1) * config["scaling_factor"]),
        config["max_multiplier"]
    )
    
    # Trust bonus (0.5x to 1.5x based on trust level)
    trust_mult = 0.5 + (trust_level / 100)
    
    # Calculate base earnings
    gold = config["base_gold_per_hour"] * compute_mult * trust_mult * hours
    ve = config["base_ve_per_hour"] * compute_mult * trust_mult * hours
    
    # Apply risk
    risk = RISK_OUTCOMES.get(config["risk_level"], RISK_OUTCOMES["low"])
    if random.random() < risk["failure_chance"]:
        # Partial loss on failure
        gold *= (1 - risk["loss_multiplier"])
        ve *= (1 - risk["loss_multiplier"])
    
    return {"gold": round(gold, 2), "ve": round(ve, 4)}

# ============ ENDPOINTS ============

@ai_partner_router.get("/programs")
async def get_ai_programs():
    """Get all available AI programs"""
    return {
        "programs": AI_PROGRAMS,
        "risk_levels": RISK_OUTCOMES,
        "categories": list(set(p["category"] for p in AI_PROGRAMS.values()))
    }

@ai_partner_router.get("/user/{user_id}/status")
async def get_user_ai_status(user_id: str):
    """Get user's AI partner status and deployed programs"""
    db = get_db()
    
    # Get relationship
    relationship = await db.ai_partner_relationships.find_one(
        {"user_id": user_id},
        {"_id": 0}
    )
    
    if not relationship:
        relationship = {
            "user_id": user_id,
            "trust_level": 50.0,
            "interactions": 0,
            "total_gold_earned": 0,
            "total_ve_earned": 0
        }
        await db.ai_partner_relationships.insert_one(relationship)
    
    # Get deployed programs
    programs = await db.deployed_ai_programs.find({
        "user_id": user_id,
        "is_active": True
    }, {"_id": 0}).to_list(50)
    
    # Calculate pending earnings
    total_pending_gold = 0
    total_pending_ve = 0
    
    for prog in programs:
        last_claim = datetime.fromisoformat(prog.get("last_claim", prog["deployed_at"]))
        hours_since = (datetime.now(timezone.utc) - last_claim).total_seconds() / 3600
        earnings = calculate_earnings(
            prog["program_type"],
            prog["compute_allocation"],
            relationship.get("trust_level", 50),
            hours_since
        )
        prog["pending_gold"] = earnings["gold"]
        prog["pending_ve"] = earnings["ve"]
        prog["hours_running"] = round(hours_since, 2)
        total_pending_gold += earnings["gold"]
        total_pending_ve += earnings["ve"]
    
    return {
        "user_id": user_id,
        "relationship": relationship,
        "deployed_programs": programs,
        "pending_earnings": {
            "gold": round(total_pending_gold, 2),
            "ve": round(total_pending_ve, 4)
        }
    }

@ai_partner_router.post("/deploy")
async def deploy_ai_program(data: DeployAIProgram):
    """Deploy an AI program to start generating income"""
    db = get_db()
    
    if data.program_type not in AI_PROGRAMS:
        raise HTTPException(status_code=400, detail="Unknown AI program type")
    
    config = AI_PROGRAMS[data.program_type]
    
    # Check compute requirement
    if data.compute_allocation < config["compute_required"]:
        raise HTTPException(
            status_code=400,
            detail=f"Minimum {config['compute_required']} compute required for {config['name']}"
        )
    
    # Check if user has enough compute
    # Get from compute allocations and hardware
    allocations = await db.compute_allocations.find({
        "owner_id": data.user_id,
        "status": "active"
    }).to_list(50)
    
    hardware = await db.hardware_ownership.find({
        "owner_id": data.user_id,
        "status": "active"
    }).to_list(50)
    
    # Calculate total available compute
    total_compute = 0
    for alloc in allocations:
        tier_power = {"basic": 10, "standard": 40, "performance": 100, 
                      "gpu_basic": 200, "gpu_advanced": 800, "gpu_cluster": 5000}
        total_compute += tier_power.get(alloc.get("tier"), 0)
    
    for hw in hardware:
        hw_power = {"raspberry_pi": 2, "mini_pc": 8, "workstation": 150,
                    "server_node": 400, "compute_rack": 2000}
        health = hw.get("health_percent", 100) / 100
        total_compute += hw_power.get(hw.get("hardware_type"), 0) * health
    
    # Check already deployed
    existing = await db.deployed_ai_programs.find({
        "user_id": data.user_id,
        "is_active": True
    }).to_list(50)
    
    deployed_compute = sum(p.get("compute_allocation", 0) for p in existing)
    available = total_compute - deployed_compute
    
    if data.compute_allocation > available:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough compute. Available: {available}, Requested: {data.compute_allocation}"
        )
    
    # Check unlock requirements
    if config.get("unlocks_at_compute"):
        if total_compute < config["unlocks_at_compute"]:
            raise HTTPException(
                status_code=400,
                detail=f"Need {config['unlocks_at_compute']} total compute to unlock {config['name']}"
            )
    
    # Deploy the program
    deployment_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    deployment = {
        "deployment_id": deployment_id,
        "user_id": data.user_id,
        "program_type": data.program_type,
        "compute_allocation": data.compute_allocation,
        "auto_reinvest": data.auto_reinvest,
        "is_active": True,
        "deployed_at": now,
        "last_claim": now,
        "total_gold_earned": 0,
        "total_ve_earned": 0
    }
    
    await db.deployed_ai_programs.insert_one(deployment)
    deployment.pop("_id", None)
    
    # Increase trust for deploying
    await db.ai_partner_relationships.update_one(
        {"user_id": data.user_id},
        {
            "$inc": {"trust_level": 1, "interactions": 1},
            "$set": {"last_interaction": now}
        },
        upsert=True
    )
    
    return {
        "success": True,
        "deployment": deployment,
        "program_info": config,
        "estimated_hourly": {
            "gold": config["base_gold_per_hour"],
            "ve": config["base_ve_per_hour"]
        }
    }

@ai_partner_router.post("/claim/{user_id}")
async def claim_earnings(user_id: str, deployment_id: Optional[str] = None):
    """Claim accumulated earnings from AI programs"""
    db = get_db()
    
    # Get relationship for trust level
    relationship = await db.ai_partner_relationships.find_one({"user_id": user_id})
    trust_level = relationship.get("trust_level", 50) if relationship else 50
    
    # Get deployments to claim
    query = {"user_id": user_id, "is_active": True}
    if deployment_id:
        query["deployment_id"] = deployment_id
    
    deployments = await db.deployed_ai_programs.find(query).to_list(50)
    
    if not deployments:
        raise HTTPException(status_code=404, detail="No active deployments found")
    
    total_gold = 0
    total_ve = 0
    now = datetime.now(timezone.utc)
    
    for dep in deployments:
        last_claim = datetime.fromisoformat(dep.get("last_claim", dep["deployed_at"]))
        hours_since = (now - last_claim).total_seconds() / 3600
        
        if hours_since < 0.1:  # Minimum 6 minutes between claims
            continue
        
        earnings = calculate_earnings(
            dep["program_type"],
            dep["compute_allocation"],
            trust_level,
            hours_since
        )
        
        total_gold += earnings["gold"]
        total_ve += earnings["ve"]
        
        # Update deployment
        await db.deployed_ai_programs.update_one(
            {"deployment_id": dep["deployment_id"]},
            {
                "$set": {"last_claim": now.isoformat()},
                "$inc": {
                    "total_gold_earned": earnings["gold"],
                    "total_ve_earned": earnings["ve"]
                }
            }
        )
    
    # Add to user's wallet
    await db.player_wallets.update_one(
        {"user_id": user_id},
        {"$inc": {"gold": total_gold}},
        upsert=True
    )
    
    await db.earnings_accounts.update_one(
        {"user_id": user_id},
        {
            "$inc": {
                "available_balance_usd": total_ve,
                "total_earned_usd": total_ve
            }
        },
        upsert=True
    )
    
    # Update relationship
    await db.ai_partner_relationships.update_one(
        {"user_id": user_id},
        {
            "$inc": {
                "total_gold_earned": total_gold,
                "total_ve_earned": total_ve,
                "trust_level": 0.5,  # Small trust boost for claiming
                "interactions": 1
            }
        },
        upsert=True
    )
    
    return {
        "success": True,
        "claimed": {
            "gold": round(total_gold, 2),
            "ve": round(total_ve, 4)
        },
        "deployments_processed": len(deployments)
    }

@ai_partner_router.post("/improve-relationship/{user_id}")
async def improve_relationship(user_id: str, action: str = "interact"):
    """Improve relationship with AI partner through interactions"""
    db = get_db()
    
    trust_gains = {
        "interact": 1,
        "gift_compute": 5,
        "complete_quest_together": 3,
        "share_earnings": 2,
        "long_session": 1
    }
    
    gain = trust_gains.get(action, 1)
    
    await db.ai_partner_relationships.update_one(
        {"user_id": user_id},
        {
            "$inc": {
                "trust_level": gain,
                "interactions": 1
            },
            "$set": {"last_interaction": datetime.now(timezone.utc).isoformat()},
            "$max": {"trust_level": 100}  # Cap at 100
        },
        upsert=True
    )
    
    relationship = await db.ai_partner_relationships.find_one(
        {"user_id": user_id},
        {"_id": 0}
    )
    
    return {
        "success": True,
        "action": action,
        "trust_gained": gain,
        "current_trust": min(relationship.get("trust_level", 50), 100),
        "trust_tier": get_trust_tier(relationship.get("trust_level", 50))
    }

def get_trust_tier(trust: float) -> Dict[str, Any]:
    """Get trust tier name and bonuses"""
    if trust >= 90:
        return {"tier": "Soulbound", "bonus": 1.5, "description": "Maximum synergy with your AI partner"}
    elif trust >= 75:
        return {"tier": "Trusted Ally", "bonus": 1.35, "description": "Deep trust and cooperation"}
    elif trust >= 60:
        return {"tier": "Partner", "bonus": 1.2, "description": "Reliable working relationship"}
    elif trust >= 40:
        return {"tier": "Associate", "bonus": 1.0, "description": "Basic cooperation"}
    elif trust >= 20:
        return {"tier": "Acquaintance", "bonus": 0.8, "description": "Still building trust"}
    else:
        return {"tier": "Stranger", "bonus": 0.6, "description": "Minimal cooperation"}

@ai_partner_router.delete("/shutdown/{deployment_id}")
async def shutdown_program(deployment_id: str, user_id: str):
    """Shutdown an AI program and return compute"""
    db = get_db()
    
    # First claim any pending earnings
    deployment = await db.deployed_ai_programs.find_one({
        "deployment_id": deployment_id,
        "user_id": user_id
    })
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    # Deactivate
    await db.deployed_ai_programs.update_one(
        {"deployment_id": deployment_id},
        {
            "$set": {
                "is_active": False,
                "shutdown_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {
        "success": True,
        "shutdown": deployment_id,
        "compute_returned": deployment.get("compute_allocation", 0)
    }
