# Data Analytics API & Task Factory
# Valuable data vector for companies + automated task pipeline

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone, timedelta
import uuid
import secrets

data_api_router = APIRouter(prefix="/data-api", tags=["data-api"])

# ============ Models ============

class TaskTemplate(BaseModel):
    name: str
    task_type: str  # labeling, classification, transcription, validation, survey
    description: str
    instructions: str
    payout_ve: float = 0.05
    time_limit_minutes: int = 10
    auto_repeat: bool = True
    repeat_interval_minutes: int = 60
    max_instances: int = 100

class CreateTaskBatch(BaseModel):
    template_id: str
    count: int = 10
    data_items: Optional[List[Dict[str, Any]]] = None

# ============ Database Helper ============

def get_db():
    from server import db
    return db

# ============ DATA API ENDPOINTS (For Companies) ============

@data_api_router.get("/analytics/summary")
async def get_analytics_summary(api_key: str = Query(..., description="Company API key")):
    """Master analytics endpoint - all data types aggregated"""
    db = get_db()
    
    # Verify API key (simple check - in production use proper auth)
    valid_key = await db.company_api_keys.find_one({"key": api_key, "active": True})
    if not valid_key:
        # Allow demo access with special key
        if api_key != "demo_analytics_key":
            raise HTTPException(status_code=401, detail="Invalid API key")
    
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)
    
    # Task Analytics
    total_tasks = await db.task_submissions.count_documents({})
    tasks_24h = await db.task_submissions.count_documents({"submitted_at": {"$gte": day_ago.isoformat()}})
    tasks_7d = await db.task_submissions.count_documents({"submitted_at": {"$gte": week_ago.isoformat()}})
    
    task_pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]
    task_by_status = {d["_id"]: d["count"] for d in await db.task_submissions.aggregate(task_pipeline).to_list(10)}
    
    # Player Engagement
    total_users = await db.user_profiles.count_documents({})
    active_24h = await db.user_profiles.count_documents({"last_login": {"$gte": day_ago.isoformat()}})
    
    # Economic Data
    wallet_pipeline = [
        {"$group": {"_id": None, "total_ve": {"$sum": "$balance_ve"}, "total_earned": {"$sum": "$total_earned"}}}
    ]
    econ = await db.entity_wallets.aggregate(wallet_pipeline).to_list(1)
    econ_data = econ[0] if econ else {"total_ve": 0, "total_earned": 0}
    
    # AI Training Data
    total_trained = await db.npc_skills.count_documents({})
    mastery_pipeline = [
        {"$group": {"_id": "$mastery_level", "count": {"$sum": 1}}}
    ]
    by_mastery = {d["_id"]: d["count"] for d in await db.npc_skills.aggregate(mastery_pipeline).to_list(10)}
    
    # NPC Services
    services_provided = await db.npc_service_history.count_documents({})
    
    return {
        "generated_at": now.isoformat(),
        "task_analytics": {
            "total_submissions": total_tasks,
            "last_24h": tasks_24h,
            "last_7d": tasks_7d,
            "by_status": task_by_status
        },
        "player_engagement": {
            "total_users": total_users,
            "active_24h": active_24h,
            "active_rate": round(active_24h / max(total_users, 1) * 100, 2)
        },
        "economic_data": {
            "total_ve_circulation": round(econ_data.get("total_ve", 0), 2),
            "total_ve_earned": round(econ_data.get("total_earned", 0), 2)
        },
        "ai_training": {
            "total_skills_trained": total_trained,
            "by_mastery_level": by_mastery
        },
        "npc_services": {
            "total_services_provided": services_provided
        }
    }

@data_api_router.get("/analytics/tasks")
async def get_task_analytics(api_key: str = Query(...), days: int = 7):
    """Detailed task analytics"""
    db = get_db()
    
    if api_key != "demo_analytics_key":
        valid = await db.company_api_keys.find_one({"key": api_key, "active": True})
        if not valid:
            raise HTTPException(status_code=401, detail="Invalid API key")
    
    since = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Task type distribution
    type_pipeline = [
        {"$group": {"_id": "$task_type", "count": {"$sum": 1}, "total_payout": {"$sum": "$payout"}}}
    ]
    by_type = await db.task_submissions.aggregate(type_pipeline).to_list(20)
    
    # Completion times
    time_pipeline = [
        {"$match": {"completion_time_seconds": {"$exists": True}}},
        {"$group": {"_id": "$task_type", "avg_time": {"$avg": "$completion_time_seconds"}}}
    ]
    avg_times = await db.task_submissions.aggregate(time_pipeline).to_list(20)
    
    # Factory tasks stats
    factory_tasks = await db.factory_tasks.count_documents({"active": True})
    factory_completed = await db.factory_task_instances.count_documents({"status": "completed"})
    
    return {
        "period_days": days,
        "by_task_type": by_type,
        "average_completion_times": avg_times,
        "task_factory": {
            "active_templates": factory_tasks,
            "instances_completed": factory_completed
        }
    }

@data_api_router.get("/analytics/economy")
async def get_economy_analytics(api_key: str = Query(...)):
    """Economic flow data"""
    db = get_db()
    
    if api_key != "demo_analytics_key":
        valid = await db.company_api_keys.find_one({"key": api_key, "active": True})
        if not valid:
            raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Top earners (anonymized)
    earner_pipeline = [
        {"$sort": {"total_earned": -1}},
        {"$limit": 10},
        {"$project": {"_id": 0, "rank": {"$literal": 1}, "total_earned": 1}}
    ]
    top_earners = await db.entity_wallets.aggregate(earner_pipeline).to_list(10)
    for i, e in enumerate(top_earners):
        e["rank"] = i + 1
    
    # Transaction volume
    tx_pipeline = [
        {"$group": {"_id": "$type", "count": {"$sum": 1}, "volume": {"$sum": "$amount"}}}
    ]
    tx_by_type = await db.external_provider_transactions.aggregate(tx_pipeline).to_list(10)
    
    return {
        "top_earners_anonymized": top_earners,
        "transaction_volume_by_type": tx_by_type
    }

@data_api_router.get("/analytics/training")
async def get_training_analytics(api_key: str = Query(...)):
    """AI training progression data"""
    db = get_db()
    
    if api_key != "demo_analytics_key":
        valid = await db.company_api_keys.find_one({"key": api_key, "active": True})
        if not valid:
            raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Skills by category
    skill_pipeline = [
        {"$group": {"_id": "$skill_id", "trained_count": {"$sum": 1}, "avg_xp": {"$avg": "$xp"}}}
    ]
    by_skill = await db.npc_skills.aggregate(skill_pipeline).to_list(30)
    
    # Training activity
    recent = await db.npc_skills.find(
        {},
        {"_id": 0, "skill_id": 1, "mastery_level": 1, "xp": 1}
    ).sort("last_trained", -1).limit(20).to_list(20)
    
    return {
        "skills_distribution": by_skill,
        "recent_training_activity": recent
    }

@data_api_router.get("/export/csv")
async def export_data_csv(api_key: str = Query(...), data_type: str = "tasks"):
    """Export data as CSV-compatible JSON array"""
    db = get_db()
    
    if api_key != "demo_analytics_key":
        valid = await db.company_api_keys.find_one({"key": api_key, "active": True})
        if not valid:
            raise HTTPException(status_code=401, detail="Invalid API key")
    
    if data_type == "tasks":
        data = await db.task_submissions.find({}, {"_id": 0}).limit(1000).to_list(1000)
    elif data_type == "training":
        data = await db.npc_skills.find({}, {"_id": 0}).limit(1000).to_list(1000)
    elif data_type == "services":
        data = await db.npc_service_history.find({}, {"_id": 0}).limit(1000).to_list(1000)
    else:
        data = []
    
    return {"data_type": data_type, "count": len(data), "records": data}

# ============ TASK FACTORY ENDPOINTS ============

@data_api_router.post("/factory/template")
async def create_task_template(template: TaskTemplate, creator_id: str = "system"):
    """Create a reusable task template"""
    db = get_db()
    
    template_doc = {
        "template_id": str(uuid.uuid4()),
        "creator_id": creator_id,
        **template.dict(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "active": True,
        "instances_created": 0,
        "instances_completed": 0
    }
    
    await db.factory_templates.insert_one(template_doc)
    
    return {"created": True, "template_id": template_doc["template_id"]}

@data_api_router.get("/factory/templates")
async def list_task_templates(active_only: bool = True):
    """List all task templates"""
    db = get_db()
    
    query = {"active": True} if active_only else {}
    templates = await db.factory_templates.find(query, {"_id": 0}).to_list(100)
    
    return {"templates": templates, "count": len(templates)}

@data_api_router.post("/factory/generate")
async def generate_tasks_from_template(data: CreateTaskBatch):
    """Generate task instances from a template"""
    db = get_db()
    
    template = await db.factory_templates.find_one({"template_id": data.template_id})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    instances = []
    for i in range(data.count):
        instance = {
            "instance_id": str(uuid.uuid4()),
            "template_id": data.template_id,
            "task_type": template["task_type"],
            "name": f"{template['name']} #{i+1}",
            "description": template["description"],
            "instructions": template["instructions"],
            "payout_ve": template["payout_ve"],
            "time_limit_minutes": template["time_limit_minutes"],
            "data": data.data_items[i] if data.data_items and i < len(data.data_items) else None,
            "status": "available",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "claimed_by": None,
            "completed_at": None
        }
        instances.append(instance)
    
    if instances:
        await db.factory_task_instances.insert_many(instances)
        await db.factory_templates.update_one(
            {"template_id": data.template_id},
            {"$inc": {"instances_created": len(instances)}}
        )
    
    return {
        "generated": len(instances),
        "template_id": data.template_id,
        "instance_ids": [i["instance_id"] for i in instances]
    }

@data_api_router.get("/factory/tasks")
async def get_available_factory_tasks(task_type: Optional[str] = None, limit: int = 50):
    """Get available tasks from the factory"""
    db = get_db()
    
    query = {"status": "available"}
    if task_type:
        query["task_type"] = task_type
    
    tasks = await db.factory_task_instances.find(
        query,
        {"_id": 0}
    ).limit(limit).to_list(limit)
    
    return {"tasks": tasks, "count": len(tasks)}

@data_api_router.post("/factory/tasks/{instance_id}/claim")
async def claim_factory_task(instance_id: str, worker_id: str):
    """Worker claims a factory task"""
    db = get_db()
    
    result = await db.factory_task_instances.update_one(
        {"instance_id": instance_id, "status": "available"},
        {
            "$set": {
                "status": "claimed",
                "claimed_by": worker_id,
                "claimed_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=400, detail="Task not available")
    
    return {"claimed": True, "instance_id": instance_id}

@data_api_router.post("/factory/tasks/{instance_id}/complete")
async def complete_factory_task(instance_id: str, worker_id: str, response: Dict[str, Any]):
    """Complete a factory task"""
    db = get_db()
    
    task = await db.factory_task_instances.find_one({"instance_id": instance_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.get("claimed_by") != worker_id:
        raise HTTPException(status_code=403, detail="Task not claimed by this worker")
    
    payout = task.get("payout_ve", 0.05)
    
    # Update task
    await db.factory_task_instances.update_one(
        {"instance_id": instance_id},
        {
            "$set": {
                "status": "completed",
                "response": response,
                "completed_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Update template stats
    await db.factory_templates.update_one(
        {"template_id": task.get("template_id")},
        {"$inc": {"instances_completed": 1}}
    )
    
    # Pay worker
    await db.entity_wallets.update_one(
        {"entity_id": worker_id},
        {
            "$inc": {"balance_ve": payout, "total_earned": payout},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        },
        upsert=True
    )
    
    return {"completed": True, "payout_ve": payout}

@data_api_router.get("/factory/stats")
async def get_factory_stats():
    """Get Task Factory statistics"""
    db = get_db()
    
    total_templates = await db.factory_templates.count_documents({})
    active_templates = await db.factory_templates.count_documents({"active": True})
    
    total_instances = await db.factory_task_instances.count_documents({})
    available = await db.factory_task_instances.count_documents({"status": "available"})
    claimed = await db.factory_task_instances.count_documents({"status": "claimed"})
    completed = await db.factory_task_instances.count_documents({"status": "completed"})
    
    # Payout stats
    payout_pipeline = [
        {"$match": {"status": "completed"}},
        {"$group": {"_id": None, "total": {"$sum": "$payout_ve"}}}
    ]
    payouts = await db.factory_task_instances.aggregate(payout_pipeline).to_list(1)
    total_paid = payouts[0]["total"] if payouts else 0
    
    return {
        "templates": {"total": total_templates, "active": active_templates},
        "instances": {
            "total": total_instances,
            "available": available,
            "claimed": claimed,
            "completed": completed
        },
        "total_ve_paid": round(total_paid, 2)
    }

# ============ API KEY MANAGEMENT ============

@data_api_router.post("/keys/create")
async def create_api_key(company_name: str, admin_id: str = "sirix_1_supreme"):
    """Create API key for a company (admin only)"""
    db = get_db()
    
    # Simple admin check
    if admin_id != "sirix_1_supreme":
        raise HTTPException(status_code=403, detail="Admin only")
    
    key = f"dapi_{secrets.token_urlsafe(24)}"
    
    await db.company_api_keys.insert_one({
        "key": key,
        "company_name": company_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "active": True,
        "requests": 0
    })
    
    return {"key": key, "company": company_name}

@data_api_router.get("/keys/list")
async def list_api_keys(admin_id: str = "sirix_1_supreme"):
    """List all API keys (admin only)"""
    db = get_db()
    
    if admin_id != "sirix_1_supreme":
        raise HTTPException(status_code=403, detail="Admin only")
    
    keys = await db.company_api_keys.find({}, {"_id": 0}).to_list(100)
    return {"keys": keys}
