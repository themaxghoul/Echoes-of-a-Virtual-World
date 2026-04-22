# Currency Tracker & AI Compute Marketplace
# Tracks VE$ value, real-world asset correlation, and AI compute purchasing

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone, timedelta
import uuid
import logging
import random

currency_compute_router = APIRouter(prefix="/economy", tags=["economy"])

logger = logging.getLogger(__name__)

# ============ VE$ Currency Configuration ============

VE_CONFIG = {
    "base_rate_usd": 1.0,  # 1 VE$ = 1 USD
    "min_rate": 0.95,
    "max_rate": 1.05,
    "volatility": 0.02,  # 2% max daily fluctuation
    "stabilization_target": 1.0
}

# ============ Compute Resource Tiers ============

COMPUTE_TIERS = {
    "basic": {
        "name": "Basic Cloud Compute",
        "description": "Entry-level cloud VM for simple tasks",
        "specs": {"vcpu": 2, "ram_gb": 4, "storage_gb": 50},
        "hourly_cost_ve": 0.05,
        "use_cases": ["Simple inference", "Data processing", "Testing"]
    },
    "standard": {
        "name": "Standard Compute",
        "description": "Balanced performance for most workloads",
        "specs": {"vcpu": 4, "ram_gb": 16, "storage_gb": 100},
        "hourly_cost_ve": 0.15,
        "use_cases": ["Model inference", "Training small models", "API hosting"]
    },
    "performance": {
        "name": "Performance Compute",
        "description": "High-performance computing",
        "specs": {"vcpu": 8, "ram_gb": 32, "storage_gb": 250},
        "hourly_cost_ve": 0.40,
        "use_cases": ["Large model inference", "Batch processing", "Multi-task"]
    },
    "gpu_basic": {
        "name": "Basic GPU Instance",
        "description": "Entry-level GPU for AI workloads",
        "specs": {"vcpu": 4, "ram_gb": 16, "gpu": "T4", "vram_gb": 16},
        "hourly_cost_ve": 0.50,
        "use_cases": ["Model training", "Image generation", "Video processing"]
    },
    "gpu_advanced": {
        "name": "Advanced GPU Instance",
        "description": "High-end GPU for intensive AI tasks",
        "specs": {"vcpu": 8, "ram_gb": 64, "gpu": "A100", "vram_gb": 40},
        "hourly_cost_ve": 2.00,
        "use_cases": ["Large model training", "Real-time inference", "Multi-model"]
    },
    "gpu_cluster": {
        "name": "GPU Cluster",
        "description": "Multi-GPU cluster for massive workloads",
        "specs": {"vcpu": 32, "ram_gb": 256, "gpu": "8x A100", "vram_gb": 320},
        "hourly_cost_ve": 12.00,
        "use_cases": ["Foundation model training", "Distributed computing", "Research"]
    }
}

# Hardware ownership options (build your own farm)
HARDWARE_PURCHASE = {
    "raspberry_pi": {
        "name": "Raspberry Pi 5",
        "description": "Entry-level personal compute node",
        "specs": {"cpu": "ARM Cortex-A76", "ram_gb": 8, "power_watts": 15},
        "one_time_cost_ve": 100,
        "monthly_yield_ve": 5,  # Passive income from network contribution
        "lifespan_months": 60
    },
    "mini_pc": {
        "name": "Mini PC Node",
        "description": "Compact compute node",
        "specs": {"cpu": "Intel N100", "ram_gb": 16, "power_watts": 35},
        "one_time_cost_ve": 300,
        "monthly_yield_ve": 15,
        "lifespan_months": 60
    },
    "workstation": {
        "name": "AI Workstation",
        "description": "Powerful personal AI computer",
        "specs": {"cpu": "Ryzen 9", "ram_gb": 64, "gpu": "RTX 4090", "power_watts": 450},
        "one_time_cost_ve": 3000,
        "monthly_yield_ve": 150,
        "lifespan_months": 48
    },
    "server_node": {
        "name": "Server Node",
        "description": "Enterprise-grade server",
        "specs": {"cpu": "Xeon", "ram_gb": 256, "gpu": "A6000", "power_watts": 800},
        "one_time_cost_ve": 8000,
        "monthly_yield_ve": 400,
        "lifespan_months": 60
    },
    "compute_rack": {
        "name": "Compute Rack (4 Nodes)",
        "description": "Full rack of compute nodes",
        "specs": {"nodes": 4, "total_gpu": "4x A100", "power_watts": 4000},
        "one_time_cost_ve": 50000,
        "monthly_yield_ve": 3000,
        "lifespan_months": 60
    }
}

# ============ Models ============

class CurrencySnapshot(BaseModel):
    snapshot_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ve_to_usd: float = 1.0
    circulating_supply: float = 0.0
    total_earned: float = 0.0
    total_withdrawn: float = 0.0
    active_compute_spend: float = 0.0
    market_sentiment: str = "stable"  # bullish, stable, bearish

class ComputeAllocation(BaseModel):
    allocation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    owner_id: str
    owner_type: str  # player or npc (AI)
    tier: str
    status: str = "active"  # active, paused, terminated
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    hours_used: float = 0.0
    total_cost: float = 0.0
    purpose: Optional[str] = None
    auto_renew: bool = True

class HardwareOwnership(BaseModel):
    ownership_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    owner_id: str
    owner_type: str
    hardware_type: str
    purchased_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = "active"  # active, degraded, retired
    health_percent: int = 100
    total_yield: float = 0.0
    last_yield_at: Optional[str] = None

class PurchaseComputeRequest(BaseModel):
    owner_id: str
    owner_type: str = "player"
    tier: str
    hours: float = 1.0
    purpose: Optional[str] = None

class PurchaseHardwareRequest(BaseModel):
    owner_id: str
    owner_type: str = "player"
    hardware_type: str

class TradeRequest(BaseModel):
    from_entity: str
    to_entity: str
    amount_ve: float
    asset_type: Optional[str] = None  # compute_hours, hardware, currency

# ============ Database Helper ============

def get_db():
    from server import db
    return db

# ============ Currency Rate Calculation ============

async def calculate_current_rate(db) -> float:
    """Calculate current VE$/USD rate based on market factors"""
    # Get recent activity
    now = datetime.now(timezone.utc)
    one_day_ago = (now - timedelta(days=1)).isoformat()
    
    # Get supply/demand indicators
    earned_today = await db.earning_events.count_documents({"timestamp": {"$gte": one_day_ago}})
    withdrawn_today = await db.ve_withdrawals.count_documents({"requested_at": {"$gte": one_day_ago}})
    
    # Simple supply/demand ratio
    if earned_today > 0:
        demand_ratio = withdrawn_today / earned_today
    else:
        demand_ratio = 0.5
    
    # Calculate rate adjustment
    base_rate = VE_CONFIG["base_rate_usd"]
    volatility = VE_CONFIG["volatility"]
    
    # More withdrawals = higher demand = rate goes up slightly
    adjustment = (demand_ratio - 0.5) * volatility
    
    # Stabilization toward target
    current_rate = base_rate + adjustment
    target = VE_CONFIG["stabilization_target"]
    current_rate = current_rate * 0.9 + target * 0.1  # 10% pull toward target
    
    # Clamp to bounds
    current_rate = max(VE_CONFIG["min_rate"], min(VE_CONFIG["max_rate"], current_rate))
    
    return round(current_rate, 4)

# ============ Endpoints ============

@currency_compute_router.get("/ve/rate")
async def get_current_rate():
    """Get current VE$/USD exchange rate"""
    db = get_db()
    
    rate = await calculate_current_rate(db)
    
    # Get 24h stats
    now = datetime.now(timezone.utc)
    one_day_ago = (now - timedelta(days=1)).isoformat()
    
    pipeline = [
        {"$group": {"_id": None, "total": {"$sum": "$balance_ve"}}}
    ]
    supply = await db.entity_wallets.aggregate(pipeline).to_list(1)
    circulating = supply[0]["total"] if supply else 0
    
    return {
        "ve_to_usd": rate,
        "usd_to_ve": round(1 / rate, 4),
        "circulating_supply_ve": circulating,
        "market_cap_usd": circulating * rate,
        "stability_target": VE_CONFIG["stabilization_target"],
        "timestamp": now.isoformat()
    }

@currency_compute_router.get("/ve/history")
async def get_rate_history(days: int = 7):
    """Get historical VE$ rate data"""
    db = get_db()
    
    # Get snapshots
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    snapshots = await db.currency_snapshots.find(
        {"timestamp": {"$gte": cutoff}},
        {"_id": 0}
    ).sort("timestamp", 1).to_list(1000)
    
    return {
        "history": snapshots,
        "days": days,
        "data_points": len(snapshots)
    }

@currency_compute_router.get("/compute/tiers")
async def get_compute_tiers():
    """Get available compute tiers"""
    return {
        "cloud_compute": COMPUTE_TIERS,
        "hardware_purchase": HARDWARE_PURCHASE
    }

@currency_compute_router.post("/compute/allocate")
async def allocate_compute(data: PurchaseComputeRequest):
    """Allocate cloud compute resources"""
    db = get_db()
    
    if data.tier not in COMPUTE_TIERS:
        raise HTTPException(status_code=400, detail=f"Unknown tier: {data.tier}")
    
    tier = COMPUTE_TIERS[data.tier]
    total_cost = tier["hourly_cost_ve"] * data.hours
    
    # Check balance
    wallet = await db.entity_wallets.find_one({"entity_id": data.owner_id})
    balance = wallet.get("balance_ve", 0) if wallet else 0
    
    if balance < total_cost:
        raise HTTPException(status_code=400, detail=f"Insufficient funds (need {total_cost} VE$)")
    
    # Deduct cost
    await db.entity_wallets.update_one(
        {"entity_id": data.owner_id},
        {"$inc": {"balance_ve": -total_cost}}
    )
    
    # Create allocation
    allocation = ComputeAllocation(
        owner_id=data.owner_id,
        owner_type=data.owner_type,
        tier=data.tier,
        hours_used=data.hours,
        total_cost=total_cost,
        purpose=data.purpose
    )
    
    await db.compute_allocations.insert_one(allocation.dict())
    
    logger.info(f"Compute allocated: {data.tier} for {data.hours}h to {data.owner_type}/{data.owner_id}")
    
    return {
        "allocated": True,
        "allocation_id": allocation.allocation_id,
        "tier": data.tier,
        "hours": data.hours,
        "cost_ve": total_cost,
        "specs": tier["specs"]
    }

@currency_compute_router.post("/hardware/purchase")
async def purchase_hardware(data: PurchaseHardwareRequest):
    """Purchase hardware for self-computing farm"""
    db = get_db()
    
    if data.hardware_type not in HARDWARE_PURCHASE:
        raise HTTPException(status_code=400, detail=f"Unknown hardware: {data.hardware_type}")
    
    hardware = HARDWARE_PURCHASE[data.hardware_type]
    cost = hardware["one_time_cost_ve"]
    
    # Check balance
    wallet = await db.entity_wallets.find_one({"entity_id": data.owner_id})
    balance = wallet.get("balance_ve", 0) if wallet else 0
    
    if balance < cost:
        raise HTTPException(status_code=400, detail=f"Insufficient funds (need {cost} VE$)")
    
    # Deduct cost
    await db.entity_wallets.update_one(
        {"entity_id": data.owner_id},
        {"$inc": {"balance_ve": -cost}}
    )
    
    # Create ownership
    ownership = HardwareOwnership(
        owner_id=data.owner_id,
        owner_type=data.owner_type,
        hardware_type=data.hardware_type
    )
    
    await db.hardware_ownership.insert_one(ownership.dict())
    
    logger.info(f"Hardware purchased: {data.hardware_type} by {data.owner_type}/{data.owner_id}")
    
    return {
        "purchased": True,
        "ownership_id": ownership.ownership_id,
        "hardware": data.hardware_type,
        "cost_ve": cost,
        "specs": hardware["specs"],
        "monthly_yield_ve": hardware["monthly_yield_ve"],
        "lifespan_months": hardware["lifespan_months"]
    }

@currency_compute_router.get("/hardware/owned/{owner_id}")
async def get_owned_hardware(owner_id: str):
    """Get hardware owned by an entity"""
    db = get_db()
    
    hardware = await db.hardware_ownership.find(
        {"owner_id": owner_id, "status": {"$ne": "retired"}},
        {"_id": 0}
    ).to_list(100)
    
    # Calculate total yield
    total_monthly_yield = 0
    for h in hardware:
        hw_type = h.get("hardware_type")
        if hw_type in HARDWARE_PURCHASE:
            health = h.get("health_percent", 100) / 100
            total_monthly_yield += HARDWARE_PURCHASE[hw_type]["monthly_yield_ve"] * health
    
    return {
        "hardware": hardware,
        "count": len(hardware),
        "total_monthly_yield_ve": total_monthly_yield
    }

@currency_compute_router.post("/hardware/{ownership_id}/collect-yield")
async def collect_hardware_yield(ownership_id: str):
    """Collect passive yield from owned hardware"""
    db = get_db()
    
    ownership = await db.hardware_ownership.find_one({"ownership_id": ownership_id})
    
    if not ownership:
        raise HTTPException(status_code=404, detail="Hardware not found")
    
    if ownership.get("status") == "retired":
        raise HTTPException(status_code=400, detail="Hardware is retired")
    
    hw_type = ownership.get("hardware_type")
    if hw_type not in HARDWARE_PURCHASE:
        raise HTTPException(status_code=400, detail="Unknown hardware type")
    
    hardware = HARDWARE_PURCHASE[hw_type]
    
    # Calculate yield based on time since last collection
    last_yield = ownership.get("last_yield_at")
    if last_yield:
        last_time = datetime.fromisoformat(last_yield.replace('Z', '+00:00'))
    else:
        last_time = datetime.fromisoformat(ownership.get("purchased_at").replace('Z', '+00:00'))
    
    now = datetime.now(timezone.utc)
    hours_elapsed = (now - last_time).total_seconds() / 3600
    
    # Minimum 1 hour between collections
    if hours_elapsed < 1:
        raise HTTPException(status_code=400, detail="Must wait at least 1 hour between collections")
    
    # Calculate yield (pro-rated monthly)
    health = ownership.get("health_percent", 100) / 100
    monthly_yield = hardware["monthly_yield_ve"] * health
    hourly_yield = monthly_yield / (30 * 24)
    yield_amount = min(hours_elapsed * hourly_yield, monthly_yield)  # Cap at monthly
    
    # Degrade health slightly (hardware wears out)
    health_loss = min(1, hours_elapsed / (hardware["lifespan_months"] * 30 * 24) * 100)
    new_health = max(0, ownership.get("health_percent", 100) - health_loss)
    
    status = "active" if new_health > 20 else "degraded" if new_health > 0 else "retired"
    
    # Update ownership
    await db.hardware_ownership.update_one(
        {"ownership_id": ownership_id},
        {
            "$set": {
                "last_yield_at": now.isoformat(),
                "health_percent": int(new_health),
                "status": status
            },
            "$inc": {"total_yield": yield_amount}
        }
    )
    
    # Credit yield
    await db.entity_wallets.update_one(
        {"entity_id": ownership.get("owner_id")},
        {
            "$inc": {"balance_ve": yield_amount, "total_earned": yield_amount}
        },
        upsert=True
    )
    
    return {
        "collected": True,
        "yield_ve": round(yield_amount, 4),
        "hours_elapsed": round(hours_elapsed, 2),
        "new_health_percent": int(new_health),
        "status": status
    }

@currency_compute_router.get("/compute/active/{owner_id}")
async def get_active_compute(owner_id: str):
    """Get active compute allocations for an entity"""
    db = get_db()
    
    allocations = await db.compute_allocations.find(
        {"owner_id": owner_id, "status": "active"},
        {"_id": 0}
    ).to_list(100)
    
    # Calculate total spend
    total_spend = sum(a.get("total_cost", 0) for a in allocations)
    
    return {
        "allocations": allocations,
        "count": len(allocations),
        "total_spend_ve": total_spend
    }

@currency_compute_router.get("/ai/top-investors")
async def get_top_ai_investors(limit: int = 20):
    """Get AI entities with highest compute investment"""
    db = get_db()
    
    # Hardware owners
    pipeline = [
        {"$match": {"owner_type": "npc"}},
        {"$group": {"_id": "$owner_id", "hardware_count": {"$sum": 1}, "total_yield": {"$sum": "$total_yield"}}},
        {"$sort": {"total_yield": -1}},
        {"$limit": limit}
    ]
    
    hw_investors = await db.hardware_ownership.aggregate(pipeline).to_list(limit)
    
    # Compute allocators
    pipeline = [
        {"$match": {"owner_type": "npc"}},
        {"$group": {"_id": "$owner_id", "total_spend": {"$sum": "$total_cost"}}},
        {"$sort": {"total_spend": -1}},
        {"$limit": limit}
    ]
    
    compute_spenders = await db.compute_allocations.aggregate(pipeline).to_list(limit)
    
    return {
        "top_hardware_owners": hw_investors,
        "top_compute_spenders": compute_spenders
    }

@currency_compute_router.get("/stats/overview")
async def get_economy_overview():
    """Get comprehensive economy statistics"""
    db = get_db()
    
    # Currency stats
    rate = await calculate_current_rate(db)
    
    pipeline = [
        {"$group": {"_id": None, "total_balance": {"$sum": "$balance_ve"}, "total_earned": {"$sum": "$total_earned"}}}
    ]
    wallet_stats = await db.entity_wallets.aggregate(pipeline).to_list(1)
    wallet_stats = wallet_stats[0] if wallet_stats else {}
    
    # Compute stats
    active_allocations = await db.compute_allocations.count_documents({"status": "active"})
    total_hardware = await db.hardware_ownership.count_documents({"status": {"$ne": "retired"}})
    
    pipeline = [
        {"$group": {"_id": None, "total": {"$sum": "$total_cost"}}}
    ]
    compute_spend = await db.compute_allocations.aggregate(pipeline).to_list(1)
    
    pipeline = [
        {"$group": {"_id": None, "total": {"$sum": "$total_yield"}}}
    ]
    hardware_yield = await db.hardware_ownership.aggregate(pipeline).to_list(1)
    
    return {
        "currency": {
            "ve_to_usd": rate,
            "circulating_supply": wallet_stats.get("total_balance", 0),
            "total_earned_ever": wallet_stats.get("total_earned", 0)
        },
        "compute": {
            "active_allocations": active_allocations,
            "total_hardware_units": total_hardware,
            "total_compute_spend_ve": compute_spend[0]["total"] if compute_spend else 0,
            "total_hardware_yield_ve": hardware_yield[0]["total"] if hardware_yield else 0
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
