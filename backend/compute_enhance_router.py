# Compute Enhancement System
# Applies purchased compute power to enhance AI/robotic/mechanical process speed and efficiency

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone, timedelta
import uuid
import logging
import math

compute_enhance_router = APIRouter(prefix="/compute-enhance", tags=["compute-enhancement"])

logger = logging.getLogger(__name__)

# ============ PROCESS TYPES ============
# Categories of processes that can be enhanced with compute power

PROCESS_TYPES = {
    "ai_npc": {
        "name": "AI NPC Processing",
        "description": "Enhances NPC decision-making, dialogue, and autonomous behavior",
        "icon": "brain",
        "base_speed": 1.0,
        "max_efficiency_multiplier": 10.0,  # Up to 10x faster
        "compute_scaling": "logarithmic",  # More compute = diminishing returns
        "compatible_tiers": ["basic", "standard", "performance", "gpu_basic", "gpu_advanced", "gpu_cluster"]
    },
    "crafting": {
        "name": "Automated Crafting",
        "description": "Speeds up production lines and crafting queues",
        "icon": "hammer",
        "base_speed": 1.0,
        "max_efficiency_multiplier": 5.0,
        "compute_scaling": "linear",
        "compatible_tiers": ["basic", "standard", "performance"]
    },
    "farming": {
        "name": "Agricultural Automation",
        "description": "Robotic farming, harvesting, and crop management",
        "icon": "wheat",
        "base_speed": 1.0,
        "max_efficiency_multiplier": 4.0,
        "compute_scaling": "linear",
        "compatible_tiers": ["basic", "standard", "performance"]
    },
    "mining": {
        "name": "Mining Operations",
        "description": "Automated mining drones and extraction systems",
        "icon": "pickaxe",
        "base_speed": 1.0,
        "max_efficiency_multiplier": 6.0,
        "compute_scaling": "linear",
        "compatible_tiers": ["basic", "standard", "performance", "gpu_basic"]
    },
    "research": {
        "name": "Research & Development",
        "description": "AI-assisted research, skill tree unlocks, and discovery",
        "icon": "microscope",
        "base_speed": 1.0,
        "max_efficiency_multiplier": 8.0,
        "compute_scaling": "logarithmic",
        "compatible_tiers": ["standard", "performance", "gpu_basic", "gpu_advanced", "gpu_cluster"]
    },
    "trading_bot": {
        "name": "Trading Algorithms",
        "description": "AI trading bots and market analysis",
        "icon": "chart",
        "base_speed": 1.0,
        "max_efficiency_multiplier": 3.0,
        "compute_scaling": "sqrt",
        "compatible_tiers": ["standard", "performance", "gpu_basic", "gpu_advanced"]
    },
    "defense_systems": {
        "name": "Defense Systems",
        "description": "Automated turrets, patrol drones, and security AI",
        "icon": "shield",
        "base_speed": 1.0,
        "max_efficiency_multiplier": 5.0,
        "compute_scaling": "linear",
        "compatible_tiers": ["basic", "standard", "performance", "gpu_basic"]
    },
    "transportation": {
        "name": "Autonomous Transport",
        "description": "Self-driving vehicles, cargo drones, and logistics",
        "icon": "truck",
        "base_speed": 1.0,
        "max_efficiency_multiplier": 4.0,
        "compute_scaling": "linear",
        "compatible_tiers": ["basic", "standard", "performance"]
    },
    "building": {
        "name": "Construction Automation",
        "description": "Robotic builders and construction drones",
        "icon": "building",
        "base_speed": 1.0,
        "max_efficiency_multiplier": 5.0,
        "compute_scaling": "linear",
        "compatible_tiers": ["basic", "standard", "performance", "gpu_basic"]
    },
    "world_simulation": {
        "name": "World Simulation",
        "description": "Environmental simulation, weather, ecosystem AI",
        "icon": "globe",
        "base_speed": 1.0,
        "max_efficiency_multiplier": 10.0,
        "compute_scaling": "logarithmic",
        "compatible_tiers": ["performance", "gpu_basic", "gpu_advanced", "gpu_cluster"]
    }
}

# Compute power values for each tier (arbitrary units for calculation)
COMPUTE_POWER = {
    "basic": 10,
    "standard": 40,
    "performance": 100,
    "gpu_basic": 200,
    "gpu_advanced": 800,
    "gpu_cluster": 5000
}

# Hardware compute contributions (from owned hardware)
HARDWARE_COMPUTE = {
    "raspberry_pi": 2,
    "mini_pc": 8,
    "workstation": 150,
    "server_node": 400,
    "compute_rack": 2000
}

# ============ MODELS ============

class ProcessAllocation(BaseModel):
    user_id: str
    process_type: str
    compute_tier: Optional[str] = None  # If using rented compute
    hardware_ids: Optional[List[str]] = None  # If using owned hardware
    priority: int = 1  # 1-10, higher = more resources

class ProcessStatus(BaseModel):
    process_id: str
    user_id: str
    process_type: str
    allocated_compute: float
    efficiency_multiplier: float
    is_active: bool
    created_at: str
    last_updated: str

# MongoDB reference
def get_db():
    from server import db
    return db

# ============ HELPER FUNCTIONS ============

def calculate_efficiency_multiplier(process_type: str, compute_power: float) -> float:
    """
    Calculate efficiency multiplier based on compute power and process type.
    Returns multiplier between 1.0 and max_efficiency_multiplier.
    """
    if process_type not in PROCESS_TYPES:
        return 1.0
    
    config = PROCESS_TYPES[process_type]
    max_mult = config["max_efficiency_multiplier"]
    scaling = config["compute_scaling"]
    
    if compute_power <= 0:
        return 1.0
    
    # Different scaling functions
    if scaling == "linear":
        # Linear: efficiency grows proportionally
        # 100 compute = 2x, 500 compute = max
        raw_mult = 1.0 + (compute_power / 250)
    elif scaling == "logarithmic":
        # Logarithmic: diminishing returns
        # Good for AI processes where more compute helps but plateaus
        raw_mult = 1.0 + (math.log10(compute_power + 1) * 2)
    elif scaling == "sqrt":
        # Square root: moderate diminishing returns
        raw_mult = 1.0 + (math.sqrt(compute_power) / 5)
    else:
        raw_mult = 1.0 + (compute_power / 500)
    
    # Cap at max multiplier
    return min(raw_mult, max_mult)

def calculate_total_compute(allocations: List[Dict], owned_hardware: List[Dict]) -> float:
    """Calculate total available compute from allocations and hardware"""
    total = 0.0
    
    # From rented compute tiers
    for alloc in allocations:
        if alloc.get("status") == "active":
            tier = alloc.get("tier")
            if tier in COMPUTE_POWER:
                total += COMPUTE_POWER[tier]
    
    # From owned hardware
    for hw in owned_hardware:
        if hw.get("status") == "active":
            hw_type = hw.get("hardware_type")
            if hw_type in HARDWARE_COMPUTE:
                # Factor in hardware health
                health = hw.get("health_percent", 100) / 100
                total += HARDWARE_COMPUTE[hw_type] * health
    
    return total

# ============ ENDPOINTS ============

@compute_enhance_router.get("/process-types")
async def get_process_types():
    """Get all process types that can be enhanced with compute"""
    return {
        "process_types": PROCESS_TYPES,
        "compute_power_tiers": COMPUTE_POWER,
        "hardware_compute": HARDWARE_COMPUTE
    }

@compute_enhance_router.get("/user/{user_id}/compute-status")
async def get_user_compute_status(user_id: str):
    """Get user's total compute power and current allocations"""
    db = get_db()
    
    # Get rented compute allocations
    allocations = await db.compute_allocations.find({
        "owner_id": user_id,
        "status": "active"
    }, {"_id": 0}).to_list(50)
    
    # Get owned hardware
    hardware = await db.hardware_ownership.find({
        "owner_id": user_id,
        "status": "active"
    }, {"_id": 0}).to_list(50)
    
    # Get process allocations
    process_allocs = await db.process_compute_allocations.find({
        "user_id": user_id,
        "is_active": True
    }, {"_id": 0}).to_list(50)
    
    # Calculate totals
    total_compute = calculate_total_compute(allocations, hardware)
    allocated_compute = sum(p.get("allocated_compute", 0) for p in process_allocs)
    available_compute = max(0, total_compute - allocated_compute)
    
    return {
        "user_id": user_id,
        "total_compute_power": round(total_compute, 2),
        "allocated_compute": round(allocated_compute, 2),
        "available_compute": round(available_compute, 2),
        "rented_tiers": [{"tier": a["tier"], "hours_remaining": a.get("hours_remaining", 0)} for a in allocations],
        "owned_hardware": [{"type": h["hardware_type"], "health": h.get("health_percent", 100)} for h in hardware],
        "active_processes": len(process_allocs)
    }

@compute_enhance_router.post("/allocate")
async def allocate_compute_to_process(data: ProcessAllocation):
    """Allocate compute power to a process for enhancement"""
    db = get_db()
    
    if data.process_type not in PROCESS_TYPES:
        raise HTTPException(status_code=400, detail=f"Unknown process type: {data.process_type}")
    
    process_config = PROCESS_TYPES[data.process_type]
    
    # Calculate available compute
    allocations = await db.compute_allocations.find({
        "owner_id": data.user_id,
        "status": "active"
    }).to_list(50)
    
    hardware = await db.hardware_ownership.find({
        "owner_id": data.user_id,
        "status": "active"
    }).to_list(50)
    
    existing_allocs = await db.process_compute_allocations.find({
        "user_id": data.user_id,
        "is_active": True
    }).to_list(50)
    
    total_compute = calculate_total_compute(allocations, hardware)
    already_allocated = sum(p.get("allocated_compute", 0) for p in existing_allocs)
    available = total_compute - already_allocated
    
    if available <= 0:
        raise HTTPException(
            status_code=400, 
            detail="No compute power available. Purchase compute or hardware first."
        )
    
    # Calculate compute to allocate based on priority
    # Higher priority = more of available compute
    priority_factor = data.priority / 10
    compute_to_allocate = available * priority_factor
    
    # Check tier compatibility
    if data.compute_tier:
        if data.compute_tier not in process_config["compatible_tiers"]:
            raise HTTPException(
                status_code=400,
                detail=f"Tier {data.compute_tier} not compatible with {data.process_type}"
            )
        compute_to_allocate = min(compute_to_allocate, COMPUTE_POWER.get(data.compute_tier, 0))
    
    # Calculate efficiency multiplier
    efficiency = calculate_efficiency_multiplier(data.process_type, compute_to_allocate)
    
    # Create or update allocation
    process_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    allocation_doc = {
        "process_id": process_id,
        "user_id": data.user_id,
        "process_type": data.process_type,
        "allocated_compute": compute_to_allocate,
        "efficiency_multiplier": round(efficiency, 2),
        "priority": data.priority,
        "compute_tier": data.compute_tier,
        "hardware_ids": data.hardware_ids,
        "is_active": True,
        "created_at": now,
        "last_updated": now
    }
    
    await db.process_compute_allocations.insert_one(allocation_doc)
    allocation_doc.pop("_id", None)
    
    return {
        "success": True,
        "allocation": allocation_doc,
        "process_name": process_config["name"],
        "speed_boost": f"{efficiency:.1f}x faster",
        "remaining_compute": round(available - compute_to_allocate, 2)
    }

@compute_enhance_router.get("/user/{user_id}/processes")
async def get_user_processes(user_id: str):
    """Get all compute-enhanced processes for a user"""
    db = get_db()
    
    processes = await db.process_compute_allocations.find({
        "user_id": user_id,
        "is_active": True
    }, {"_id": 0}).to_list(100)
    
    # Enrich with process type info
    enriched = []
    for proc in processes:
        ptype = proc.get("process_type")
        if ptype in PROCESS_TYPES:
            enriched.append({
                **proc,
                "process_info": PROCESS_TYPES[ptype]
            })
        else:
            enriched.append(proc)
    
    return {
        "user_id": user_id,
        "processes": enriched,
        "total_count": len(enriched)
    }

@compute_enhance_router.put("/process/{process_id}/adjust")
async def adjust_process_compute(process_id: str, user_id: str, new_priority: int = 5):
    """Adjust compute allocation for a process"""
    db = get_db()
    
    process = await db.process_compute_allocations.find_one({
        "process_id": process_id,
        "user_id": user_id
    })
    
    if not process:
        raise HTTPException(status_code=404, detail="Process allocation not found")
    
    # Recalculate with new priority
    allocations = await db.compute_allocations.find({
        "owner_id": user_id,
        "status": "active"
    }).to_list(50)
    
    hardware = await db.hardware_ownership.find({
        "owner_id": user_id,
        "status": "active"
    }).to_list(50)
    
    other_allocs = await db.process_compute_allocations.find({
        "user_id": user_id,
        "is_active": True,
        "process_id": {"$ne": process_id}
    }).to_list(50)
    
    total_compute = calculate_total_compute(allocations, hardware)
    other_allocated = sum(p.get("allocated_compute", 0) for p in other_allocs)
    available = total_compute - other_allocated
    
    new_priority = max(1, min(10, new_priority))
    priority_factor = new_priority / 10
    new_compute = available * priority_factor
    
    new_efficiency = calculate_efficiency_multiplier(process["process_type"], new_compute)
    
    await db.process_compute_allocations.update_one(
        {"process_id": process_id},
        {
            "$set": {
                "allocated_compute": new_compute,
                "efficiency_multiplier": round(new_efficiency, 2),
                "priority": new_priority,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {
        "success": True,
        "process_id": process_id,
        "new_compute": round(new_compute, 2),
        "new_efficiency": f"{new_efficiency:.1f}x",
        "priority": new_priority
    }

@compute_enhance_router.delete("/process/{process_id}")
async def deallocate_process(process_id: str, user_id: str):
    """Remove compute allocation from a process"""
    db = get_db()
    
    result = await db.process_compute_allocations.update_one(
        {"process_id": process_id, "user_id": user_id},
        {
            "$set": {
                "is_active": False,
                "deallocated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Process allocation not found")
    
    return {"success": True, "deallocated": process_id}

@compute_enhance_router.get("/efficiency-preview")
async def preview_efficiency(process_type: str, compute_power: float):
    """Preview efficiency multiplier for a given compute power"""
    if process_type not in PROCESS_TYPES:
        raise HTTPException(status_code=400, detail="Unknown process type")
    
    config = PROCESS_TYPES[process_type]
    efficiency = calculate_efficiency_multiplier(process_type, compute_power)
    
    return {
        "process_type": process_type,
        "process_name": config["name"],
        "compute_power": compute_power,
        "efficiency_multiplier": round(efficiency, 2),
        "max_possible": config["max_efficiency_multiplier"],
        "scaling_type": config["compute_scaling"],
        "description": f"Tasks complete {efficiency:.1f}x faster"
    }

@compute_enhance_router.get("/recommended/{user_id}")
async def get_recommended_allocations(user_id: str):
    """Get recommended compute allocations based on user's activities"""
    db = get_db()
    
    # Get user's buildings
    plots = await db.player_plots.find({"user_id": user_id}).to_list(50)
    buildings = []
    for plot in plots:
        buildings.extend(plot.get("buildings", []))
    
    # Get user stats
    stats = await db.player_achievement_stats.find_one({"user_id": user_id}) or {}
    
    recommendations = []
    
    # Check for farming buildings
    farm_count = sum(1 for b in buildings if b.get("category") == "agricultural")
    if farm_count > 0:
        recommendations.append({
            "process_type": "farming",
            "reason": f"You have {farm_count} agricultural buildings",
            "suggested_priority": min(farm_count + 2, 8),
            "expected_boost": "Up to 4x harvest speed"
        })
    
    # Check for industrial buildings
    industrial_count = sum(1 for b in buildings if b.get("category") == "industrial")
    if industrial_count > 0:
        recommendations.append({
            "process_type": "crafting",
            "reason": f"You have {industrial_count} industrial buildings",
            "suggested_priority": min(industrial_count + 3, 9),
            "expected_boost": "Up to 5x crafting speed"
        })
    
    # Check for trading activity
    if stats.get("trades_completed", 0) > 10:
        recommendations.append({
            "process_type": "trading_bot",
            "reason": "Active trader detected",
            "suggested_priority": 6,
            "expected_boost": "Up to 3x trade analysis speed"
        })
    
    # Always recommend AI NPC if they have NPCs
    npc_friends = stats.get("npc_friends", 0)
    if npc_friends > 0:
        recommendations.append({
            "process_type": "ai_npc",
            "reason": f"Enhance {npc_friends} NPC interactions",
            "suggested_priority": 7,
            "expected_boost": "Up to 10x faster NPC responses"
        })
    
    # Building construction
    if len(plots) > 0:
        recommendations.append({
            "process_type": "building",
            "reason": "Accelerate construction projects",
            "suggested_priority": 5,
            "expected_boost": "Up to 5x build speed"
        })
    
    return {
        "user_id": user_id,
        "recommendations": recommendations,
        "total_recommendations": len(recommendations)
    }

@compute_enhance_router.post("/auto-optimize/{user_id}")
async def auto_optimize_allocations(user_id: str):
    """Automatically optimize compute allocations across all processes"""
    db = get_db()
    
    # Get available compute
    allocations = await db.compute_allocations.find({
        "owner_id": user_id,
        "status": "active"
    }).to_list(50)
    
    hardware = await db.hardware_ownership.find({
        "owner_id": user_id,
        "status": "active"
    }).to_list(50)
    
    total_compute = calculate_total_compute(allocations, hardware)
    
    if total_compute <= 0:
        raise HTTPException(status_code=400, detail="No compute power available")
    
    # Get current active processes
    current_processes = await db.process_compute_allocations.find({
        "user_id": user_id,
        "is_active": True
    }).to_list(100)
    
    if not current_processes:
        return {
            "optimized": False,
            "reason": "No active processes to optimize"
        }
    
    # Distribute compute based on priority weights
    total_priority = sum(p.get("priority", 5) for p in current_processes)
    
    optimized = []
    for proc in current_processes:
        priority = proc.get("priority", 5)
        share = (priority / total_priority) * total_compute
        efficiency = calculate_efficiency_multiplier(proc["process_type"], share)
        
        await db.process_compute_allocations.update_one(
            {"process_id": proc["process_id"]},
            {
                "$set": {
                    "allocated_compute": round(share, 2),
                    "efficiency_multiplier": round(efficiency, 2),
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        optimized.append({
            "process_type": proc["process_type"],
            "old_compute": proc.get("allocated_compute", 0),
            "new_compute": round(share, 2),
            "new_efficiency": f"{efficiency:.1f}x"
        })
    
    return {
        "optimized": True,
        "total_compute": round(total_compute, 2),
        "processes_updated": len(optimized),
        "details": optimized
    }

@compute_enhance_router.get("/active-bonuses/{user_id}")
async def get_active_bonuses(user_id: str):
    """Get all active efficiency bonuses for gameplay use"""
    db = get_db()
    
    processes = await db.process_compute_allocations.find({
        "user_id": user_id,
        "is_active": True
    }, {"_id": 0}).to_list(100)
    
    bonuses = {}
    for proc in processes:
        ptype = proc["process_type"]
        bonuses[ptype] = {
            "multiplier": proc.get("efficiency_multiplier", 1.0),
            "compute_allocated": proc.get("allocated_compute", 0),
            "process_name": PROCESS_TYPES.get(ptype, {}).get("name", ptype)
        }
    
    return {
        "user_id": user_id,
        "bonuses": bonuses,
        "total_enhanced_processes": len(bonuses)
    }
