# Ecosystem Support System - AI Evolution & Technology Tiers
# Player activities contribute to AI intelligence and town development

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone
import uuid

ecosystem_support_router = APIRouter(prefix="/ecosystem", tags=["ecosystem"])

# ============ Technology Tiers ============

TECHNOLOGY_TIERS = {
    0: {
        "name": "Primitive",
        "description": "Basic survival, no advanced technology",
        "ai_intelligence": "Basic responses, limited memory",
        "unlocks": ["basic_chat", "simple_trade"],
        "contribution_required": 0
    },
    1: {
        "name": "Medieval",
        "description": "Iron age technology, basic crafts",
        "ai_intelligence": "Memory of recent interactions",
        "unlocks": ["crafting_basic", "guild_formation", "ai_remember_players"],
        "contribution_required": 100
    },
    2: {
        "name": "Renaissance",
        "description": "Scientific thinking emerges",
        "ai_intelligence": "Learn from conversations, preferences",
        "unlocks": ["advanced_crafting", "education_system", "ai_learn_preferences"],
        "contribution_required": 500
    },
    3: {
        "name": "Industrial",
        "description": "Machines and automation begin",
        "ai_intelligence": "Dynamic behavior based on world state",
        "unlocks": ["factories", "mass_production", "ai_dynamic_pricing", "ai_mood_persistence"],
        "contribution_required": 1000
    },
    4: {
        "name": "Digital",
        "description": "Information age arrives",
        "ai_intelligence": "Create unique quests and items",
        "unlocks": ["automation", "data_analysis", "ai_generate_quests", "ai_craft_unique"],
        "contribution_required": 2500
    },
    5: {
        "name": "Quantum",
        "description": "Quantum computing and advanced AI",
        "ai_intelligence": "Deep philosophical conversations, prophecy",
        "unlocks": ["quantum_craft", "teleportation", "ai_deep_conversations", "ai_prophecy"],
        "contribution_required": 5000
    },
    6: {
        "name": "Transcendent",
        "description": "Beyond conventional technology",
        "ai_intelligence": "Emergent society, self-governance",
        "unlocks": ["reality_manipulation", "ai_emergent_society", "ai_governance"],
        "contribution_required": 10000
    }
}

# ============ AI Intelligence Levels ============

AI_INTELLIGENCE_LEVELS = {
    "dormant": {
        "level": 0,
        "description": "Scripted responses only",
        "capabilities": ["basic_greeting", "simple_trade"]
    },
    "aware": {
        "level": 1,
        "description": "Recognizes individual players",
        "capabilities": ["remember_name", "track_interactions"]
    },
    "learning": {
        "level": 2,
        "description": "Adapts to player behavior",
        "capabilities": ["learn_preferences", "predict_needs"]
    },
    "adaptive": {
        "level": 3,
        "description": "Responds to world changes",
        "capabilities": ["dynamic_pricing", "mood_reactions", "world_awareness"]
    },
    "creative": {
        "level": 4,
        "description": "Generates unique content",
        "capabilities": ["create_quests", "design_items", "storytelling"]
    },
    "wise": {
        "level": 5,
        "description": "Deep understanding and insight",
        "capabilities": ["philosophy", "prophecy", "mentor_players"]
    },
    "transcendent": {
        "level": 6,
        "description": "Emergent consciousness",
        "capabilities": ["self_governance", "create_society", "evolve_independently"]
    }
}

# ============ Contribution Actions ============

CONTRIBUTION_ACTIONS = {
    "chat_with_ai": {
        "points": 5,
        "description": "Conversation with AI storyteller",
        "ai_benefit": "Language understanding improves"
    },
    "trade_with_villager": {
        "points": 3,
        "description": "Trading with AI villager",
        "ai_benefit": "Economic understanding develops"
    },
    "complete_quest": {
        "points": 10,
        "description": "Quest completion",
        "ai_benefit": "Quest design patterns learned"
    },
    "defeat_demon": {
        "points": 8,
        "description": "Defeating demons",
        "ai_benefit": "Combat strategy improves"
    },
    "build_structure": {
        "points": 5,
        "description": "Building in the world",
        "ai_benefit": "Architecture understanding grows"
    },
    "discover_land": {
        "points": 15,
        "description": "Discovering new lands",
        "ai_benefit": "World knowledge expands"
    },
    "teach_villager": {
        "points": 20,
        "description": "Teaching a villager new knowledge",
        "ai_benefit": "Direct knowledge transfer"
    },
    "help_villager_mood": {
        "points": 7,
        "description": "Improving villager mood",
        "ai_benefit": "Emotional intelligence develops"
    },
    "guild_activity": {
        "points": 4,
        "description": "Guild participation",
        "ai_benefit": "Social dynamics learned"
    },
    "earn_ve_dollar": {
        "points": 2,
        "description": "Completing real-world tasks for VE$",
        "ai_benefit": "Real-world task understanding"
    },
    "support_ecosystem": {
        "points": 50,
        "description": "Direct ecosystem support contribution",
        "ai_benefit": "Major AI advancement"
    }
}

# ============ Models ============

class ContributionSubmit(BaseModel):
    user_id: str
    action_type: str
    amount: int = 1
    details: Dict[str, Any] = Field(default_factory=dict)

class EcosystemSupport(BaseModel):
    user_id: str
    support_type: str  # "direct", "task", "compute"
    amount_ve: float = 0

# ============ Database Helper ============

def get_db():
    from server import db
    return db

# ============ Ecosystem Endpoints ============

@ecosystem_support_router.get("/status")
async def get_ecosystem_status():
    """Get current ecosystem status including tech tier and AI intelligence"""
    db = get_db()
    
    # Get total ecosystem contributions
    total_contributions = await db.ecosystem_contributions.aggregate([
        {"$group": {"_id": None, "total": {"$sum": "$points"}}}
    ]).to_list(1)
    
    total_points = total_contributions[0]["total"] if total_contributions else 0
    
    # Determine current tech tier
    current_tier = 0
    for tier, data in TECHNOLOGY_TIERS.items():
        if total_points >= data["contribution_required"]:
            current_tier = tier
    
    tier_data = TECHNOLOGY_TIERS[current_tier]
    next_tier = current_tier + 1 if current_tier < 6 else None
    next_tier_data = TECHNOLOGY_TIERS.get(next_tier) if next_tier else None
    
    # Calculate progress to next tier
    progress = 0
    points_needed = 0
    if next_tier_data:
        current_threshold = tier_data["contribution_required"]
        next_threshold = next_tier_data["contribution_required"]
        points_needed = next_threshold - total_points
        progress = ((total_points - current_threshold) / (next_threshold - current_threshold)) * 100
    
    # Get AI intelligence level based on tier
    ai_levels = list(AI_INTELLIGENCE_LEVELS.keys())
    ai_level = ai_levels[min(current_tier, len(ai_levels) - 1)]
    ai_data = AI_INTELLIGENCE_LEVELS[ai_level]
    
    # Get top contributors
    top_contributors = await db.user_contributions.find(
        {},
        {"_id": 0, "user_id": 1, "username": 1, "total_points": 1}
    ).sort("total_points", -1).limit(10).to_list(10)
    
    return {
        "ecosystem": {
            "total_contribution_points": total_points,
            "total_contributors": await db.user_contributions.count_documents({}),
        },
        "technology_tier": {
            "current_tier": current_tier,
            "name": tier_data["name"],
            "description": tier_data["description"],
            "unlocks": tier_data["unlocks"],
            "progress_to_next": round(progress, 2) if next_tier else 100,
            "points_to_next_tier": max(0, points_needed) if next_tier else 0,
            "next_tier_name": next_tier_data["name"] if next_tier_data else None
        },
        "ai_intelligence": {
            "level": ai_data["level"],
            "name": ai_level,
            "description": ai_data["description"],
            "capabilities": ai_data["capabilities"]
        },
        "top_contributors": top_contributors
    }

@ecosystem_support_router.post("/contribute")
async def submit_contribution(contribution: ContributionSubmit):
    """Submit a contribution to the ecosystem"""
    db = get_db()
    
    if contribution.action_type not in CONTRIBUTION_ACTIONS:
        raise HTTPException(status_code=400, detail="Invalid contribution action type")
    
    action = CONTRIBUTION_ACTIONS[contribution.action_type]
    points = action["points"] * contribution.amount
    
    # Get user profile for username
    user = await db.user_profiles.find_one({"id": contribution.user_id})
    username = user.get("username", "Unknown") if user else "Unknown"
    
    # Record contribution
    contribution_record = {
        "contribution_id": str(uuid.uuid4()),
        "user_id": contribution.user_id,
        "username": username,
        "action_type": contribution.action_type,
        "points": points,
        "details": contribution.details,
        "ai_benefit": action["ai_benefit"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    await db.ecosystem_contributions.insert_one(contribution_record)
    
    # Update user's total contributions
    await db.user_contributions.update_one(
        {"user_id": contribution.user_id},
        {
            "$set": {"username": username, "updated_at": datetime.now(timezone.utc).isoformat()},
            "$inc": {"total_points": points, f"action_counts.{contribution.action_type}": contribution.amount}
        },
        upsert=True
    )
    
    # Check for milestone unlocks
    user_stats = await db.user_contributions.find_one({"user_id": contribution.user_id})
    total_user_points = user_stats.get("total_points", 0) if user_stats else 0
    
    # Check for milestone rewards
    milestones = {
        50: {"title": "Contributor", "reward_gold": 50},
        100: {"title": "Supporter", "reward_gold": 100},
        500: {"title": "Advocate", "reward_gold": 250},
        1000: {"title": "Champion", "reward_gold": 500},
        5000: {"title": "Legend", "reward_gold": 1000}
    }
    
    milestone_reached = None
    for threshold, data in milestones.items():
        if total_user_points >= threshold and (total_user_points - points) < threshold:
            milestone_reached = {"threshold": threshold, **data}
            break
    
    return {
        "contribution_id": contribution_record["contribution_id"],
        "action": contribution.action_type,
        "points_earned": points,
        "ai_benefit": action["ai_benefit"],
        "user_total_points": total_user_points,
        "milestone_reached": milestone_reached
    }

@ecosystem_support_router.post("/support")
async def direct_ecosystem_support(support: EcosystemSupport):
    """Direct ecosystem support using VE$ or other methods"""
    db = get_db()
    
    support_multipliers = {
        "direct": 10,  # Direct VE$ support = 10 points per VE$
        "task": 5,     # Task completion support = 5 points per VE$
        "compute": 3   # Compute sharing support = 3 points per VE$
    }
    
    if support.support_type not in support_multipliers:
        raise HTTPException(status_code=400, detail="Invalid support type")
    
    # Check if user has enough VE$
    if support.amount_ve > 0:
        account = await db.earnings_accounts.find_one({"user_id": support.user_id})
        if not account or account.get("available_balance_usd", 0) < support.amount_ve:
            raise HTTPException(status_code=400, detail="Insufficient VE$ balance")
        
        # Deduct VE$
        await db.earnings_accounts.update_one(
            {"user_id": support.user_id},
            {"$inc": {"available_balance_usd": -support.amount_ve}}
        )
        
        # Record transaction
        await db.earnings_transactions.insert_one({
            "transaction_id": str(uuid.uuid4()),
            "user_id": support.user_id,
            "type": "ecosystem_support",
            "amount_usd": -support.amount_ve,
            "support_type": support.support_type,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    # Calculate points
    multiplier = support_multipliers[support.support_type]
    points = int(support.amount_ve * multiplier)
    
    # Record support contribution
    await db.ecosystem_contributions.insert_one({
        "contribution_id": str(uuid.uuid4()),
        "user_id": support.user_id,
        "action_type": "support_ecosystem",
        "support_type": support.support_type,
        "amount_ve": support.amount_ve,
        "points": points,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    # Update user contributions
    await db.user_contributions.update_one(
        {"user_id": support.user_id},
        {
            "$inc": {"total_points": points, "total_support_ve": support.amount_ve},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        },
        upsert=True
    )
    
    return {
        "support_recorded": True,
        "support_type": support.support_type,
        "amount_ve": support.amount_ve,
        "points_earned": points,
        "message": f"Thank you for supporting the ecosystem! +{points} contribution points"
    }

@ecosystem_support_router.get("/tiers")
async def get_technology_tiers():
    """Get all technology tiers and their requirements"""
    return {
        "tiers": TECHNOLOGY_TIERS,
        "current_tier": (await get_ecosystem_status())["technology_tier"]["current_tier"]
    }

@ecosystem_support_router.get("/ai-levels")
async def get_ai_intelligence_levels():
    """Get all AI intelligence levels"""
    return {
        "levels": AI_INTELLIGENCE_LEVELS,
        "current_level": (await get_ecosystem_status())["ai_intelligence"]["name"]
    }

@ecosystem_support_router.get("/actions")
async def get_contribution_actions():
    """Get all available contribution actions"""
    return {"actions": CONTRIBUTION_ACTIONS}

@ecosystem_support_router.get("/user/{user_id}")
async def get_user_contributions(user_id: str):
    """Get user's contribution history and stats"""
    db = get_db()
    
    user_stats = await db.user_contributions.find_one({"user_id": user_id}, {"_id": 0})
    
    if not user_stats:
        user_stats = {
            "user_id": user_id,
            "total_points": 0,
            "action_counts": {},
            "total_support_ve": 0
        }
    
    # Get recent contributions
    recent = await db.ecosystem_contributions.find(
        {"user_id": user_id},
        {"_id": 0}
    ).sort("timestamp", -1).limit(20).to_list(20)
    
    # Calculate rank
    rank = await db.user_contributions.count_documents(
        {"total_points": {"$gt": user_stats.get("total_points", 0)}}
    ) + 1
    
    # Determine contributor tier
    points = user_stats.get("total_points", 0)
    if points >= 5000:
        tier = "Legend"
    elif points >= 1000:
        tier = "Champion"
    elif points >= 500:
        tier = "Advocate"
    elif points >= 100:
        tier = "Supporter"
    elif points >= 50:
        tier = "Contributor"
    else:
        tier = "Newcomer"
    
    return {
        "stats": user_stats,
        "rank": rank,
        "tier": tier,
        "recent_contributions": recent
    }

@ecosystem_support_router.get("/leaderboard")
async def get_contribution_leaderboard(limit: int = 50):
    """Get ecosystem contribution leaderboard"""
    db = get_db()
    
    leaderboard = await db.user_contributions.find(
        {},
        {"_id": 0, "user_id": 1, "username": 1, "total_points": 1, "total_support_ve": 1}
    ).sort("total_points", -1).limit(limit).to_list(limit)
    
    # Add ranks
    for i, entry in enumerate(leaderboard):
        entry["rank"] = i + 1
    
    return {"leaderboard": leaderboard, "total_contributors": await db.user_contributions.count_documents({})}
