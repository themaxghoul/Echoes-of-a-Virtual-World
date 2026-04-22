# Task Marketplace Router - Human & Robot Integration for Dynamic Tasks
# Allows creation and completion of data labeling, AI training, creative, and QA tasks

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone
import uuid
import logging

task_marketplace_router = APIRouter(prefix="/task-marketplace", tags=["task-marketplace"])

logger = logging.getLogger(__name__)

# ============ Task Categories ============

TASK_CATEGORIES = {
    "data_labeling": {
        "name": "Data Labeling",
        "description": "Label images, text, or audio for AI training",
        "icon": "tag",
        "color": "#10B981",
        "base_pay_range": [0.01, 0.10],
        "skills_rewarded": ["investigation", "lore"]
    },
    "transcription": {
        "name": "Transcription",
        "description": "Convert audio or video to text",
        "icon": "file-text",
        "color": "#3B82F6",
        "base_pay_range": [0.05, 0.25],
        "skills_rewarded": ["languages", "lore"]
    },
    "content_moderation": {
        "name": "Content Moderation",
        "description": "Review and flag inappropriate content",
        "icon": "shield",
        "color": "#EF4444",
        "base_pay_range": [0.02, 0.15],
        "skills_rewarded": ["investigation", "diplomacy"]
    },
    "ai_training": {
        "name": "AI Training Feedback",
        "description": "Provide feedback to improve AI responses",
        "icon": "brain",
        "color": "#8B5CF6",
        "base_pay_range": [0.05, 0.50],
        "skills_rewarded": ["arcana", "lore"]
    },
    "quality_assurance": {
        "name": "Quality Assurance",
        "description": "Test features and report bugs",
        "icon": "check-circle",
        "color": "#F59E0B",
        "base_pay_range": [0.10, 0.75],
        "skills_rewarded": ["investigation", "tactics"]
    },
    "creative_writing": {
        "name": "Creative Writing",
        "description": "Write stories, dialogues, or descriptions",
        "icon": "feather",
        "color": "#EC4899",
        "base_pay_range": [0.25, 2.00],
        "skills_rewarded": ["lore", "charm", "languages"]
    },
    "creative_art": {
        "name": "Art & Design",
        "description": "Create visual assets, concepts, or designs",
        "icon": "palette",
        "color": "#F97316",
        "base_pay_range": [0.50, 5.00],
        "skills_rewarded": ["enchanting", "divination"]
    },
    "translation": {
        "name": "Translation",
        "description": "Translate content between languages",
        "icon": "globe",
        "color": "#06B6D4",
        "base_pay_range": [0.10, 1.00],
        "skills_rewarded": ["languages", "diplomacy"]
    },
    "research": {
        "name": "Research",
        "description": "Research topics and compile information",
        "icon": "search",
        "color": "#6366F1",
        "base_pay_range": [0.15, 1.50],
        "skills_rewarded": ["investigation", "lore", "arcana"]
    },
    "world_building": {
        "name": "World Building",
        "description": "Design locations, NPCs, or lore for the game",
        "icon": "map",
        "color": "#84CC16",
        "base_pay_range": [0.50, 3.00],
        "skills_rewarded": ["engineering", "lore", "leadership"]
    }
}

# Task difficulty levels
DIFFICULTY_LEVELS = {
    "trivial": {"multiplier": 0.5, "xp_bonus": 1},
    "easy": {"multiplier": 0.75, "xp_bonus": 2},
    "medium": {"multiplier": 1.0, "xp_bonus": 5},
    "hard": {"multiplier": 1.5, "xp_bonus": 10},
    "expert": {"multiplier": 2.0, "xp_bonus": 20},
    "legendary": {"multiplier": 3.0, "xp_bonus": 50}
}

# ============ Models ============

class Task(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    category: str
    title: str
    description: str
    instructions: str
    difficulty: str = "medium"
    base_reward: float  # VE$
    time_estimate_minutes: int = 10
    created_by: str  # user_id or "system" or NPC ID
    created_by_type: str = "system"  # system, player, npc, robot
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: Optional[str] = None
    max_completions: int = 1
    current_completions: int = 0
    required_skills: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    status: str = "open"  # open, in_progress, completed, expired, cancelled
    metadata: Dict[str, Any] = Field(default_factory=dict)

class TaskSubmission(BaseModel):
    submission_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    submitter_id: str
    submitter_type: str = "player"  # player, npc, robot
    submission_data: Dict[str, Any]
    submitted_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = "pending"  # pending, approved, rejected, needs_revision
    reward_paid: float = 0.0
    feedback: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None

class CreateTaskRequest(BaseModel):
    category: str
    title: str
    description: str
    instructions: str
    difficulty: str = "medium"
    base_reward: float
    time_estimate_minutes: int = 10
    max_completions: int = 1
    required_skills: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    expires_in_hours: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

class SubmitTaskRequest(BaseModel):
    task_id: str
    submitter_id: str
    submitter_type: str = "player"
    submission_data: Dict[str, Any]

class ReviewSubmissionRequest(BaseModel):
    submission_id: str
    reviewer_id: str
    status: str  # approved, rejected, needs_revision
    feedback: Optional[str] = None

# ============ Database Helper ============

def get_db():
    from server import db
    return db

# ============ Endpoints ============

@task_marketplace_router.get("/categories")
async def get_task_categories():
    """Get all task categories"""
    return {
        "categories": TASK_CATEGORIES,
        "difficulty_levels": DIFFICULTY_LEVELS
    }

@task_marketplace_router.post("/tasks/create")
async def create_task(data: CreateTaskRequest, creator_id: str, creator_type: str = "player"):
    """Create a new task (can be created by players, NPCs, or system)"""
    db = get_db()
    
    if data.category not in TASK_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category: {data.category}")
    
    if data.difficulty not in DIFFICULTY_LEVELS:
        raise HTTPException(status_code=400, detail=f"Invalid difficulty: {data.difficulty}")
    
    # Calculate actual reward with difficulty multiplier
    difficulty_mult = DIFFICULTY_LEVELS[data.difficulty]["multiplier"]
    
    expires_at = None
    if data.expires_in_hours:
        expires_at = (datetime.now(timezone.utc) + __import__('datetime').timedelta(hours=data.expires_in_hours)).isoformat()
    
    task = Task(
        category=data.category,
        title=data.title,
        description=data.description,
        instructions=data.instructions,
        difficulty=data.difficulty,
        base_reward=data.base_reward,
        time_estimate_minutes=data.time_estimate_minutes,
        created_by=creator_id,
        created_by_type=creator_type,
        expires_at=expires_at,
        max_completions=data.max_completions,
        required_skills=data.required_skills,
        tags=data.tags,
        metadata=data.metadata or {}
    )
    
    await db.marketplace_tasks.insert_one(task.dict())
    
    logger.info(f"Task created: {task.task_id} by {creator_type}/{creator_id}")
    
    return {
        "created": True,
        "task_id": task.task_id,
        "task": task.dict(),
        "effective_reward": data.base_reward * difficulty_mult
    }

@task_marketplace_router.get("/tasks")
async def list_tasks(
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    status: str = "open",
    created_by_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """List available tasks"""
    db = get_db()
    
    query = {"status": status}
    if category:
        query["category"] = category
    if difficulty:
        query["difficulty"] = difficulty
    if created_by_type:
        query["created_by_type"] = created_by_type
    
    tasks = await db.marketplace_tasks.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).skip(offset).limit(limit).to_list(limit)
    
    # Enrich with category info
    for task in tasks:
        cat_info = TASK_CATEGORIES.get(task.get("category"), {})
        task["category_info"] = cat_info
        task["effective_reward"] = task.get("base_reward", 0) * DIFFICULTY_LEVELS.get(task.get("difficulty", "medium"), {}).get("multiplier", 1)
    
    total = await db.marketplace_tasks.count_documents(query)
    
    return {
        "tasks": tasks,
        "total": total,
        "limit": limit,
        "offset": offset
    }

@task_marketplace_router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Get task details"""
    db = get_db()
    
    task = await db.marketplace_tasks.find_one({"task_id": task_id}, {"_id": 0})
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Get submissions count
    submissions = await db.task_submissions.count_documents({"task_id": task_id})
    
    cat_info = TASK_CATEGORIES.get(task.get("category"), {})
    task["category_info"] = cat_info
    task["effective_reward"] = task.get("base_reward", 0) * DIFFICULTY_LEVELS.get(task.get("difficulty", "medium"), {}).get("multiplier", 1)
    task["submissions_count"] = submissions
    
    return task

@task_marketplace_router.post("/tasks/submit")
async def submit_task(data: SubmitTaskRequest):
    """Submit a completed task"""
    db = get_db()
    
    task = await db.marketplace_tasks.find_one({"task_id": data.task_id})
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.get("status") != "open":
        raise HTTPException(status_code=400, detail="Task is not open for submissions")
    
    if task.get("current_completions", 0) >= task.get("max_completions", 1):
        raise HTTPException(status_code=400, detail="Task has reached maximum completions")
    
    # Check if submitter already submitted
    existing = await db.task_submissions.find_one({
        "task_id": data.task_id,
        "submitter_id": data.submitter_id
    })
    
    if existing:
        raise HTTPException(status_code=400, detail="You have already submitted this task")
    
    submission = TaskSubmission(
        task_id=data.task_id,
        submitter_id=data.submitter_id,
        submitter_type=data.submitter_type,
        submission_data=data.submission_data
    )
    
    await db.task_submissions.insert_one(submission.dict())
    
    # Update task
    await db.marketplace_tasks.update_one(
        {"task_id": data.task_id},
        {"$set": {"status": "in_progress"}}
    )
    
    return {
        "submitted": True,
        "submission_id": submission.submission_id,
        "status": "pending"
    }

@task_marketplace_router.post("/submissions/review")
async def review_submission(data: ReviewSubmissionRequest):
    """Review a task submission (approve/reject)"""
    db = get_db()
    
    submission = await db.task_submissions.find_one({"submission_id": data.submission_id})
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    if submission.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Submission already reviewed")
    
    task = await db.marketplace_tasks.find_one({"task_id": submission.get("task_id")})
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    reward_paid = 0.0
    
    if data.status == "approved":
        # Calculate reward
        base_reward = task.get("base_reward", 0)
        difficulty_mult = DIFFICULTY_LEVELS.get(task.get("difficulty", "medium"), {}).get("multiplier", 1)
        reward_paid = base_reward * difficulty_mult
        
        # Pay the submitter
        await db.entity_wallets.update_one(
            {"entity_id": submission.get("submitter_id")},
            {
                "$inc": {"balance_ve": reward_paid, "total_earned": reward_paid},
                "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
            },
            upsert=True
        )
        
        # Award skills
        category = task.get("category")
        cat_info = TASK_CATEGORIES.get(category, {})
        skills_rewarded = cat_info.get("skills_rewarded", [])
        xp_bonus = DIFFICULTY_LEVELS.get(task.get("difficulty", "medium"), {}).get("xp_bonus", 1)
        
        for skill in skills_rewarded:
            await db.entity_skills.update_one(
                {"entity_id": submission.get("submitter_id")},
                {"$inc": {f"skills.{skill}.xp": xp_bonus}},
                upsert=True
            )
        
        # Update task completion count
        new_completions = task.get("current_completions", 0) + 1
        task_status = "completed" if new_completions >= task.get("max_completions", 1) else "open"
        
        await db.marketplace_tasks.update_one(
            {"task_id": task.get("task_id")},
            {
                "$inc": {"current_completions": 1},
                "$set": {"status": task_status}
            }
        )
    
    # Update submission
    await db.task_submissions.update_one(
        {"submission_id": data.submission_id},
        {
            "$set": {
                "status": data.status,
                "feedback": data.feedback,
                "reviewed_by": data.reviewer_id,
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
                "reward_paid": reward_paid
            }
        }
    )
    
    return {
        "reviewed": True,
        "submission_id": data.submission_id,
        "status": data.status,
        "reward_paid": reward_paid
    }

@task_marketplace_router.get("/submissions/{submitter_id}")
async def get_submitter_history(submitter_id: str, status: Optional[str] = None, limit: int = 50):
    """Get submission history for a submitter"""
    db = get_db()
    
    query = {"submitter_id": submitter_id}
    if status:
        query["status"] = status
    
    submissions = await db.task_submissions.find(
        query,
        {"_id": 0}
    ).sort("submitted_at", -1).limit(limit).to_list(limit)
    
    # Enrich with task info
    for sub in submissions:
        task = await db.marketplace_tasks.find_one(
            {"task_id": sub.get("task_id")},
            {"_id": 0, "title": 1, "category": 1, "difficulty": 1}
        )
        if task:
            sub["task_info"] = task
    
    return {"submissions": submissions, "count": len(submissions)}

@task_marketplace_router.get("/stats")
async def get_marketplace_stats():
    """Get marketplace statistics"""
    db = get_db()
    
    # Task counts by status
    total_tasks = await db.marketplace_tasks.count_documents({})
    open_tasks = await db.marketplace_tasks.count_documents({"status": "open"})
    completed_tasks = await db.marketplace_tasks.count_documents({"status": "completed"})
    
    # Tasks by category
    pipeline = [
        {"$group": {"_id": "$category", "count": {"$sum": 1}}}
    ]
    by_category = await db.marketplace_tasks.aggregate(pipeline).to_list(20)
    
    # Total rewards paid
    pipeline = [
        {"$match": {"status": "approved"}},
        {"$group": {"_id": None, "total": {"$sum": "$reward_paid"}}}
    ]
    rewards = await db.task_submissions.aggregate(pipeline).to_list(1)
    total_rewards = rewards[0]["total"] if rewards else 0
    
    # Tasks by creator type
    pipeline = [
        {"$group": {"_id": "$created_by_type", "count": {"$sum": 1}}}
    ]
    by_creator = await db.marketplace_tasks.aggregate(pipeline).to_list(10)
    
    return {
        "total_tasks": total_tasks,
        "open_tasks": open_tasks,
        "completed_tasks": completed_tasks,
        "tasks_by_category": {c["_id"]: c["count"] for c in by_category},
        "tasks_by_creator_type": {c["_id"]: c["count"] for c in by_creator if c["_id"]},
        "total_rewards_paid": total_rewards
    }

@task_marketplace_router.post("/tasks/create-batch")
async def create_batch_tasks(tasks: List[CreateTaskRequest], creator_id: str, creator_type: str = "system"):
    """Create multiple tasks at once (for system/robot batch creation)"""
    db = get_db()
    
    created = []
    for task_data in tasks:
        try:
            result = await create_task(task_data, creator_id, creator_type)
            created.append(result["task_id"])
        except Exception as e:
            logger.error(f"Failed to create task: {e}")
    
    return {
        "created_count": len(created),
        "task_ids": created
    }

@task_marketplace_router.get("/tasks/for-entity/{entity_id}")
async def get_recommended_tasks(entity_id: str, entity_type: str = "player", limit: int = 20):
    """Get recommended tasks based on entity's skills"""
    db = get_db()
    
    # Get entity skills
    skills_doc = await db.entity_skills.find_one({"entity_id": entity_id})
    entity_skills = list(skills_doc.get("skills", {}).keys()) if skills_doc else []
    
    # Find tasks matching skills
    if entity_skills:
        query = {
            "status": "open",
            "$or": [
                {"required_skills": {"$in": entity_skills}},
                {"required_skills": {"$size": 0}}
            ]
        }
    else:
        query = {"status": "open", "required_skills": {"$size": 0}}
    
    tasks = await db.marketplace_tasks.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    # Enrich tasks
    for task in tasks:
        cat_info = TASK_CATEGORIES.get(task.get("category"), {})
        task["category_info"] = cat_info
        task["effective_reward"] = task.get("base_reward", 0) * DIFFICULTY_LEVELS.get(task.get("difficulty", "medium"), {}).get("multiplier", 1)
    
    return {"recommended_tasks": tasks, "count": len(tasks)}
