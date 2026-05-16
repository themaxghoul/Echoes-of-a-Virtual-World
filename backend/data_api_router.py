# Task Factory & Data API
# Structured task pipeline with validation and rewards

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone, timedelta
import uuid
import secrets

data_api_router = APIRouter(prefix="/data-api", tags=["data-api"])

# ============ Task Structure ============

DIFFICULTY_MULTIPLIERS = {
    "trivial": 0.5,
    "easy": 0.75,
    "medium": 1.0,
    "hard": 1.5,
    "expert": 2.0,
    "legendary": 3.0
}

VALIDATION_TYPES = {
    "auto": "System automatically validates based on rules",
    "consensus": "Multiple workers must agree",
    "review": "Human reviewer checks output",
    "ai_check": "AI validates the result",
    "checksum": "Output matches expected hash/format"
}

# ============ Models ============

class TaskTemplate(BaseModel):
    title: str = Field(..., description="Short, action-oriented title")
    objective: str = Field(..., description="What change must occur")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="Data, materials, context")
    process: List[str] = Field(default_factory=list, description="Steps or method")
    output: Dict[str, Any] = Field(default_factory=dict, description="Measurable, verifiable result spec")
    validation: Dict[str, Any] = Field(default_factory=lambda: {"type": "auto", "rules": []})
    reward_ve: float = Field(default=0.05, description="VE$ minted or transferred")
    difficulty: str = Field(default="medium")
    compute_cost: float = Field(default=0.0, description="If AI is involved")
    dependencies: List[str] = Field(default_factory=list, description="Task IDs or resources required")
    task_type: str = Field(default="general")
    time_limit_minutes: int = Field(default=30)
    auto_repeat: bool = Field(default=False)
    max_instances: int = Field(default=100)

class SubmitTaskRequest(BaseModel):
    worker_id: str
    output: Dict[str, Any]

class GenerateTasksRequest(BaseModel):
    template_id: str
    count: int = 10
    input_variants: Optional[List[Dict[str, Any]]] = None

# ============ Database Helper ============

def get_db():
    from server import db
    return db

# ============ TASK FACTORY ENDPOINTS ============

@data_api_router.post("/factory/template")
async def create_task_template(template: TaskTemplate, creator_id: str = "system"):
    """Create a structured task template"""
    db = get_db()
    
    if template.difficulty not in DIFFICULTY_MULTIPLIERS:
        raise HTTPException(status_code=400, detail=f"Invalid difficulty. Use: {list(DIFFICULTY_MULTIPLIERS.keys())}")
    
    adjusted_reward = template.reward_ve * DIFFICULTY_MULTIPLIERS[template.difficulty]
    
    template_doc = {
        "template_id": str(uuid.uuid4()),
        "creator_id": creator_id,
        "title": template.title,
        "objective": template.objective,
        "inputs": template.inputs,
        "process": template.process,
        "output": template.output,
        "validation": template.validation,
        "reward_ve": template.reward_ve,
        "adjusted_reward_ve": adjusted_reward,
        "difficulty": template.difficulty,
        "compute_cost": template.compute_cost,
        "dependencies": template.dependencies,
        "task_type": template.task_type,
        "time_limit_minutes": template.time_limit_minutes,
        "auto_repeat": template.auto_repeat,
        "max_instances": template.max_instances,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "active": True,
        "stats": {"instances_created": 0, "instances_completed": 0, "instances_failed": 0, "total_ve_paid": 0}
    }
    
    await db.factory_templates.insert_one(template_doc)
    return {"created": True, "template_id": template_doc["template_id"], "adjusted_reward_ve": adjusted_reward}

@data_api_router.get("/factory/templates")
async def list_templates(active_only: bool = True, task_type: Optional[str] = None):
    """List all task templates"""
    db = get_db()
    query = {"active": True} if active_only else {}
    if task_type:
        query["task_type"] = task_type
    templates = await db.factory_templates.find(query, {"_id": 0}).to_list(100)
    return {"templates": templates, "count": len(templates)}

@data_api_router.get("/factory/template/{template_id}")
async def get_template(template_id: str):
    """Get single template details"""
    db = get_db()
    template = await db.factory_templates.find_one({"template_id": template_id}, {"_id": 0})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template

@data_api_router.post("/factory/generate")
async def generate_tasks(data: GenerateTasksRequest):
    """Generate task instances from template"""
    db = get_db()
    
    template = await db.factory_templates.find_one({"template_id": data.template_id})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    for dep_id in template.get("dependencies", []):
        dep = await db.factory_templates.find_one({"template_id": dep_id})
        if dep and dep.get("stats", {}).get("instances_completed", 0) == 0:
            raise HTTPException(status_code=400, detail=f"Dependency {dep_id} has no completions")
    
    instances = []
    for i in range(data.count):
        task_inputs = template.get("inputs", {}).copy()
        if data.input_variants and i < len(data.input_variants):
            task_inputs.update(data.input_variants[i])
        
        instances.append({
            "instance_id": str(uuid.uuid4()),
            "template_id": data.template_id,
            "title": f"{template['title']} #{i+1}",
            "objective": template["objective"],
            "inputs": task_inputs,
            "process": template.get("process", []),
            "output_spec": template.get("output", {}),
            "validation": template.get("validation", {"type": "auto"}),
            "reward_ve": template.get("adjusted_reward_ve", template.get("reward_ve", 0.05)),
            "difficulty": template.get("difficulty", "medium"),
            "compute_cost": template.get("compute_cost", 0),
            "dependencies": template.get("dependencies", []),
            "time_limit_minutes": template.get("time_limit_minutes", 30),
            "status": "available",
            "claimed_by": None,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    if instances:
        await db.factory_task_instances.insert_many(instances)
        await db.factory_templates.update_one(
            {"template_id": data.template_id},
            {"$inc": {"stats.instances_created": len(instances)}}
        )
    
    return {"generated": len(instances), "template_id": data.template_id, "instance_ids": [i["instance_id"] for i in instances]}

@data_api_router.get("/factory/tasks")
async def get_available_tasks(status: str = "available", difficulty: Optional[str] = None, limit: int = 50):
    """Get tasks from the factory"""
    db = get_db()
    query = {"status": status}
    if difficulty:
        query["difficulty"] = difficulty
    tasks = await db.factory_task_instances.find(query, {"_id": 0}).limit(limit).to_list(limit)
    return {"tasks": tasks, "count": len(tasks)}

@data_api_router.get("/factory/task/{instance_id}")
async def get_task(instance_id: str):
    """Get single task instance"""
    db = get_db()
    task = await db.factory_task_instances.find_one({"instance_id": instance_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@data_api_router.post("/factory/task/{instance_id}/claim")
async def claim_task(instance_id: str, worker_id: str):
    """Worker claims a task"""
    db = get_db()
    
    task = await db.factory_task_instances.find_one({"instance_id": instance_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task["status"] != "available":
        raise HTTPException(status_code=400, detail=f"Task not available (status: {task['status']})")
    
    if task.get("compute_cost", 0) > 0:
        wallet = await db.entity_wallets.find_one({"entity_id": worker_id})
        if (wallet.get("compute_balance", 0) if wallet else 0) < task["compute_cost"]:
            raise HTTPException(status_code=400, detail=f"Insufficient compute. Need: {task['compute_cost']}")
    
    await db.factory_task_instances.update_one(
        {"instance_id": instance_id},
        {"$set": {"status": "claimed", "claimed_by": worker_id, "claimed_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"claimed": True, "instance_id": instance_id, "title": task["title"], "objective": task["objective"],
            "inputs": task["inputs"], "process": task["process"], "output_spec": task["output_spec"]}

@data_api_router.post("/factory/task/{instance_id}/submit")
async def submit_task(instance_id: str, data: SubmitTaskRequest):
    """Submit task output for validation"""
    db = get_db()
    
    task = await db.factory_task_instances.find_one({"instance_id": instance_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task["status"] != "claimed":
        raise HTTPException(status_code=400, detail="Task not claimed")
    if task.get("claimed_by") != data.worker_id:
        raise HTTPException(status_code=403, detail="Not your task")
    
    if task.get("compute_cost", 0) > 0:
        await db.entity_wallets.update_one({"entity_id": data.worker_id}, {"$inc": {"compute_balance": -task["compute_cost"]}})
    
    validation_result = await validate_output(task, data.output)
    new_status = "completed" if validation_result["passed"] else "failed"
    
    await db.factory_task_instances.update_one(
        {"instance_id": instance_id},
        {"$set": {"status": new_status, "submitted_output": data.output, "submitted_at": datetime.now(timezone.utc).isoformat(),
                  "validation_result": validation_result, "completed_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    reward_paid = 0
    if validation_result["passed"]:
        reward_paid = task.get("reward_ve", 0)
        await db.entity_wallets.update_one(
            {"entity_id": data.worker_id},
            {"$inc": {"balance_ve": reward_paid, "total_earned": reward_paid}, "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}},
            upsert=True
        )
        await db.factory_templates.update_one({"template_id": task["template_id"]}, {"$inc": {"stats.instances_completed": 1, "stats.total_ve_paid": reward_paid}})
    else:
        await db.factory_templates.update_one({"template_id": task["template_id"]}, {"$inc": {"stats.instances_failed": 1}})
    
    return {"submitted": True, "status": new_status, "validation": validation_result, "reward_ve": reward_paid}

async def validate_output(task: dict, output: dict) -> dict:
    """Validate task output against spec"""
    validation_config = task.get("validation", {"type": "auto"})
    output_spec = task.get("output_spec", {})
    
    result = {"passed": True, "type": validation_config.get("type", "auto"), "checks": [], "timestamp": datetime.now(timezone.utc).isoformat()}
    
    for field in output_spec.get("required_fields", []):
        if field not in output:
            result["passed"] = False
            result["checks"].append({"field": field, "status": "missing"})
        else:
            result["checks"].append({"field": field, "status": "present"})
    
    for field, expected_type in output_spec.get("field_types", {}).items():
        if field in output:
            actual = type(output[field]).__name__
            if expected_type == "array":
                expected_type = "list"
            if actual != expected_type:
                result["passed"] = False
                result["checks"].append({"field": field, "status": "wrong_type", "expected": expected_type, "got": actual})
    
    for field, constraint in output_spec.get("constraints", {}).items():
        if field in output:
            val = output[field]
            if "min" in constraint and val < constraint["min"]:
                result["passed"] = False
                result["checks"].append({"field": field, "status": "below_min"})
            if "max" in constraint and val > constraint["max"]:
                result["passed"] = False
                result["checks"].append({"field": field, "status": "above_max"})
            if "min_length" in constraint and len(val) < constraint["min_length"]:
                result["passed"] = False
                result["checks"].append({"field": field, "status": "too_short"})
    
    for rule in validation_config.get("rules", []):
        if rule.get("type") == "not_empty":
            field = rule.get("field")
            if field and (field not in output or not output[field]):
                result["passed"] = False
                result["checks"].append({"rule": "not_empty", "field": field, "status": "failed"})
    
    return result

@data_api_router.get("/factory/stats")
async def get_factory_stats():
    """Get Task Factory statistics"""
    db = get_db()
    
    total_templates = await db.factory_templates.count_documents({})
    active_templates = await db.factory_templates.count_documents({"active": True})
    
    by_status = {d["_id"]: d["count"] for d in await db.factory_task_instances.aggregate([{"$group": {"_id": "$status", "count": {"$sum": 1}}}]).to_list(10)}
    by_difficulty = {d["_id"]: d["count"] for d in await db.factory_task_instances.aggregate([{"$group": {"_id": "$difficulty", "count": {"$sum": 1}}}]).to_list(10)}
    
    payouts = await db.factory_task_instances.aggregate([{"$match": {"status": "completed"}}, {"$group": {"_id": None, "total": {"$sum": "$reward_ve"}}}]).to_list(1)
    
    return {
        "templates": {"total": total_templates, "active": active_templates},
        "instances": {"by_status": by_status, "by_difficulty": by_difficulty, "total": sum(by_status.values()) if by_status else 0},
        "economics": {"total_ve_paid": round(payouts[0]["total"], 4) if payouts else 0, "difficulty_multipliers": DIFFICULTY_MULTIPLIERS}
    }

# ============ DATA API ENDPOINTS ============

@data_api_router.get("/analytics/summary")
async def get_analytics_summary(api_key: str = Query(...)):
    """Master analytics endpoint"""
    db = get_db()
    
    if api_key != "demo_analytics_key":
        valid = await db.company_api_keys.find_one({"key": api_key, "active": True})
        if not valid:
            raise HTTPException(status_code=401, detail="Invalid API key")
    
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(days=1)
    
    factory_stats = await get_factory_stats()
    total_users = await db.user_profiles.count_documents({})
    active_24h = await db.user_profiles.count_documents({"last_login": {"$gte": day_ago.isoformat()}})
    
    econ = await db.entity_wallets.aggregate([{"$group": {"_id": None, "total_ve": {"$sum": "$balance_ve"}, "total_earned": {"$sum": "$total_earned"}}}]).to_list(1)
    econ_data = econ[0] if econ else {"total_ve": 0, "total_earned": 0}
    
    total_trained = await db.npc_skills.count_documents({})
    by_mastery = {d["_id"]: d["count"] for d in await db.npc_skills.aggregate([{"$group": {"_id": "$mastery_level", "count": {"$sum": 1}}}]).to_list(10)}
    services_provided = await db.npc_service_history.count_documents({})
    
    return {
        "generated_at": now.isoformat(),
        "task_factory": factory_stats,
        "player_engagement": {"total_users": total_users, "active_24h": active_24h},
        "economic_data": {"total_ve_circulation": round(econ_data.get("total_ve", 0), 2), "total_ve_earned": round(econ_data.get("total_earned", 0), 2)},
        "ai_training": {"total_skills_trained": total_trained, "by_mastery_level": by_mastery},
        "npc_services": {"total_services_provided": services_provided}
    }

@data_api_router.get("/export")
async def export_data(api_key: str = Query(...), data_type: str = "tasks"):
    """Export data as JSON"""
    db = get_db()
    
    if api_key != "demo_analytics_key":
        valid = await db.company_api_keys.find_one({"key": api_key, "active": True})
        if not valid:
            raise HTTPException(status_code=401, detail="Invalid API key")
    
    collections = {"tasks": "factory_task_instances", "templates": "factory_templates", "training": "npc_skills", "services": "npc_service_history"}
    coll = collections.get(data_type)
    data = await db[coll].find({}, {"_id": 0}).limit(1000).to_list(1000) if coll else []
    return {"data_type": data_type, "count": len(data), "records": data}

@data_api_router.post("/keys/create")
async def create_api_key(company_name: str, admin_id: str = "sirix_1_supreme"):
    """Create API key for a company"""
    db = get_db()
    if admin_id != "sirix_1_supreme":
        raise HTTPException(status_code=403, detail="Admin only")
    key = f"dapi_{secrets.token_urlsafe(24)}"
    await db.company_api_keys.insert_one({"key": key, "company_name": company_name, "created_at": datetime.now(timezone.utc).isoformat(), "active": True})
    return {"key": key, "company": company_name}
