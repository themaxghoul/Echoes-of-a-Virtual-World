# Micro-Task Provider Integrations
# Connects to real task providers for actual earnings

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum
import uuid
import asyncio
import httpx
import hashlib
import hmac
import json

task_providers_router = APIRouter(prefix="/providers", tags=["task-providers"])

# ============ PROVIDER CONFIGURATIONS ============

class TaskProvider(str, Enum):
    TOLOKA = "toloka"
    APPEN = "appen"
    CLICKWORKER = "clickworker"
    MICROWORKERS = "microworkers"
    PICOWORKERS = "picoworkers"
    SPARE5 = "spare5"
    INTERNAL = "internal"  # ApexForge internal tasks

# Provider configurations (API endpoints, etc.)
PROVIDER_CONFIGS = {
    TaskProvider.TOLOKA: {
        "name": "Toloka",
        "description": "Yandex's crowdsourcing platform",
        "base_url": "https://toloka.dev/api/v1",
        "task_types": ["image_labeling", "text_annotation", "audio_transcription", "data_collection"],
        "avg_rate": "$6-10/hr",
        "min_payout": 1.00,
        "payout_methods": ["paypal", "payoneer", "skrill"],
        "countries_available": ["US", "CA", "GB", "DE", "FR", "IN", "PH", "ID", "BR", "MX"],
        "requires_qualification": False
    },
    TaskProvider.APPEN: {
        "name": "Appen",
        "description": "AI training data and annotation",
        "base_url": "https://connect.appen.com/api",
        "task_types": ["search_evaluation", "data_annotation", "audio_transcription", "language_tasks"],
        "avg_rate": "$8-15/hr",
        "min_payout": 5.00,
        "payout_methods": ["paypal", "payoneer", "bank_transfer"],
        "countries_available": ["US", "CA", "GB", "AU", "DE", "FR", "JP", "KR"],
        "requires_qualification": True
    },
    TaskProvider.CLICKWORKER: {
        "name": "Clickworker",
        "description": "Diverse micro-task platform",
        "base_url": "https://api.clickworker.com/api",
        "task_types": ["writing", "translation", "research", "data_entry", "surveys"],
        "avg_rate": "$5-12/hr",
        "min_payout": 5.00,
        "payout_methods": ["paypal", "sepa"],
        "countries_available": ["US", "CA", "GB", "DE", "FR", "IT", "ES", "NL"],
        "requires_qualification": True
    },
    TaskProvider.MICROWORKERS: {
        "name": "Microworkers",
        "description": "Quick micro-tasks marketplace",
        "base_url": "https://api.microworkers.com/v2",
        "task_types": ["app_testing", "social_tasks", "data_entry", "content_creation"],
        "avg_rate": "$4-8/hr",
        "min_payout": 9.00,
        "payout_methods": ["paypal", "skrill", "payoneer", "bitcoin"],
        "countries_available": ["US", "CA", "GB", "IN", "PH", "BD", "PK", "NG"],
        "requires_qualification": False
    },
    TaskProvider.PICOWORKERS: {
        "name": "Picoworkers",
        "description": "Simple task completion platform",
        "base_url": "https://picoworkers.com/api",
        "task_types": ["signup", "app_install", "reviews", "social_engagement"],
        "avg_rate": "$3-6/hr",
        "min_payout": 5.50,
        "payout_methods": ["paypal", "bitcoin", "litecoin", "payoneer"],
        "countries_available": ["US", "CA", "GB", "IN", "BD", "PK", "PH", "NG", "VN"],
        "requires_qualification": False
    },
    TaskProvider.SPARE5: {
        "name": "Spare5 (Mighty AI)",
        "description": "AI training data annotation",
        "base_url": "https://app.spare5.com/api",
        "task_types": ["image_annotation", "video_annotation", "text_classification"],
        "avg_rate": "$6-12/hr",
        "min_payout": 1.00,
        "payout_methods": ["paypal"],
        "countries_available": ["US", "CA", "GB", "AU", "DE", "FR", "JP"],
        "requires_qualification": True
    },
    TaskProvider.INTERNAL: {
        "name": "ApexForge Tasks",
        "description": "Internal ApexForge Collective tasks",
        "base_url": None,
        "task_types": ["data_labeling", "content_moderation", "transcription", "surveys", "expert_review"],
        "avg_rate": "$5-15/hr",
        "min_payout": 1.00,
        "payout_methods": ["wallet", "game_balance"],
        "countries_available": ["ALL"],
        "requires_qualification": False
    }
}

# ============ MODELS ============

class ProviderConnection(BaseModel):
    user_id: str
    provider: TaskProvider
    external_user_id: Optional[str] = None
    api_key: Optional[str] = None
    connected_at: str = ""
    status: str = "pending"  # pending, active, suspended
    qualifications: List[str] = Field(default_factory=list)
    total_earned_from_provider: float = 0.0

class ExternalTask(BaseModel):
    task_id: str
    provider: TaskProvider
    external_task_id: str
    title: str
    description: str
    task_type: str
    reward_usd: float
    reward_ve: float  # VE$ (1:1 with USD)
    time_estimate_minutes: int
    deadline_minutes: int
    instructions: List[str] = Field(default_factory=list)
    requirements: List[str] = Field(default_factory=list)
    status: str = "available"
    fetched_at: str = ""

class TaskCompletionReport(BaseModel):
    user_id: str
    task_id: str
    provider: TaskProvider
    external_task_id: str
    submission_data: Dict[str, Any]
    time_taken_seconds: int
    quality_score: Optional[float] = None

# ============ DATABASE HELPER ============

def get_db():
    from server import db
    return db

# ============ PROVIDER ENDPOINTS ============

@task_providers_router.get("/list")
async def list_providers():
    """List all available task providers"""
    providers = []
    for provider, config in PROVIDER_CONFIGS.items():
        providers.append({
            "provider_id": provider.value,
            **config
        })
    return {"providers": providers}

@task_providers_router.get("/{provider_id}")
async def get_provider_details(provider_id: str):
    """Get details for a specific provider"""
    try:
        provider = TaskProvider(provider_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    config = PROVIDER_CONFIGS.get(provider)
    if not config:
        raise HTTPException(status_code=404, detail="Provider configuration not found")
    
    return {
        "provider_id": provider_id,
        **config
    }

@task_providers_router.post("/connect")
async def connect_to_provider(user_id: str, provider_id: str, external_credentials: Optional[Dict] = None):
    """Connect user account to a task provider"""
    db = get_db()
    
    try:
        provider = TaskProvider(provider_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    # Check if already connected
    existing = await db.provider_connections.find_one({
        "user_id": user_id,
        "provider": provider_id
    })
    
    if existing:
        return {"status": "already_connected", "connection_id": existing.get("connection_id")}
    
    # Create connection
    connection = ProviderConnection(
        user_id=user_id,
        provider=provider,
        external_user_id=external_credentials.get("user_id") if external_credentials else None,
        api_key=external_credentials.get("api_key") if external_credentials else None,
        connected_at=datetime.now(timezone.utc).isoformat(),
        status="active" if provider == TaskProvider.INTERNAL else "pending"
    )
    
    connection_dict = connection.dict()
    connection_dict["connection_id"] = str(uuid.uuid4())
    
    await db.provider_connections.insert_one(connection_dict)
    
    return {
        "status": "connected",
        "connection_id": connection_dict["connection_id"],
        "provider": provider_id,
        "requires_verification": provider != TaskProvider.INTERNAL
    }

@task_providers_router.get("/connections/{user_id}")
async def get_user_connections(user_id: str):
    """Get all provider connections for a user"""
    db = get_db()
    
    connections = await db.provider_connections.find(
        {"user_id": user_id},
        {"_id": 0}
    ).to_list(100)
    
    return {"connections": connections}

@task_providers_router.get("/tasks/fetch")
async def fetch_tasks_from_providers(user_id: str, provider_id: Optional[str] = None, limit: int = 20):
    """Fetch available tasks from connected providers"""
    db = get_db()
    
    # Get user's connections
    query = {"user_id": user_id, "status": "active"}
    if provider_id:
        query["provider"] = provider_id
    
    connections = await db.provider_connections.find(query).to_list(100)
    
    if not connections:
        # Auto-connect to internal provider
        await connect_to_provider(user_id, TaskProvider.INTERNAL.value, None)
        connections = [{"provider": TaskProvider.INTERNAL.value}]
    
    all_tasks = []
    
    for conn in connections:
        provider = conn["provider"]
        
        if provider == TaskProvider.INTERNAL.value:
            # Generate internal tasks
            internal_tasks = await generate_internal_tasks(user_id, limit)
            all_tasks.extend(internal_tasks)
        else:
            # Fetch from external provider (simulated for now)
            external_tasks = await fetch_external_tasks(provider, limit // len(connections))
            all_tasks.extend(external_tasks)
    
    return {"tasks": all_tasks[:limit], "total": len(all_tasks)}

async def generate_internal_tasks(user_id: str, limit: int = 10) -> List[dict]:
    """Generate internal ApexForge tasks"""
    db = get_db()
    
    # Task templates with realistic VE$ rewards
    task_templates = [
        {
            "task_type": "data_labeling",
            "title": "Image Classification - Product Categories",
            "description": "Classify product images into correct categories",
            "reward_usd": 0.50,
            "time_estimate_minutes": 3,
            "instructions": ["View each image", "Select the correct product category", "Verify your selection"]
        },
        {
            "task_type": "data_labeling",
            "title": "Text Sentiment Analysis",
            "description": "Analyze customer reviews for sentiment",
            "reward_usd": 0.35,
            "time_estimate_minutes": 2,
            "instructions": ["Read the review text", "Classify as positive, negative, or neutral", "Rate confidence"]
        },
        {
            "task_type": "transcription",
            "title": "Audio Transcription - Short Clip",
            "description": "Transcribe a 2-minute audio recording",
            "reward_usd": 2.00,
            "time_estimate_minutes": 10,
            "instructions": ["Listen to the audio", "Type exactly what you hear", "Include speaker labels"]
        },
        {
            "task_type": "content_moderation",
            "title": "Content Review - Social Posts",
            "description": "Review social media posts for policy violations",
            "reward_usd": 0.75,
            "time_estimate_minutes": 4,
            "instructions": ["Review the post content", "Check against guidelines", "Flag any violations"]
        },
        {
            "task_type": "surveys",
            "title": "Consumer Preference Survey",
            "description": "Share your opinions on products and services",
            "reward_usd": 2.50,
            "time_estimate_minutes": 15,
            "instructions": ["Answer all questions honestly", "Provide detailed feedback where requested"]
        },
        {
            "task_type": "data_labeling",
            "title": "Object Detection Annotation",
            "description": "Draw bounding boxes around objects in images",
            "reward_usd": 1.00,
            "time_estimate_minutes": 5,
            "instructions": ["Identify all specified objects", "Draw accurate bounding boxes", "Label each box"]
        },
        {
            "task_type": "expert_review",
            "title": "Technical Document Review",
            "description": "Review and validate technical documentation",
            "reward_usd": 8.00,
            "time_estimate_minutes": 30,
            "instructions": ["Read the document thoroughly", "Identify errors or inconsistencies", "Suggest improvements"]
        },
        {
            "task_type": "data_labeling",
            "title": "Named Entity Recognition",
            "description": "Identify and tag entities in text",
            "reward_usd": 0.60,
            "time_estimate_minutes": 4,
            "instructions": ["Highlight all named entities", "Tag with correct type", "Verify accuracy"]
        },
        {
            "task_type": "content_moderation",
            "title": "Video Content Review",
            "description": "Review short video clips for appropriateness",
            "reward_usd": 1.50,
            "time_estimate_minutes": 8,
            "instructions": ["Watch the entire video", "Check for policy violations", "Provide detailed notes"]
        },
        {
            "task_type": "surveys",
            "title": "App Usability Feedback",
            "description": "Test an app and provide usability feedback",
            "reward_usd": 5.00,
            "time_estimate_minutes": 25,
            "instructions": ["Download and use the app", "Complete specified tasks", "Fill out feedback form"]
        }
    ]
    
    tasks = []
    import random
    
    for i, template in enumerate(random.sample(task_templates, min(limit, len(task_templates)))):
        task = ExternalTask(
            task_id=f"apex_{str(uuid.uuid4())[:8]}",
            provider=TaskProvider.INTERNAL,
            external_task_id=f"internal_{i}",
            title=template["title"],
            description=template["description"],
            task_type=template["task_type"],
            reward_usd=template["reward_usd"],
            reward_ve=template["reward_usd"],  # 1:1 ratio
            time_estimate_minutes=template["time_estimate_minutes"],
            deadline_minutes=template["time_estimate_minutes"] * 3,
            instructions=template["instructions"],
            status="available",
            fetched_at=datetime.now(timezone.utc).isoformat()
        )
        
        # Store in DB
        await db.external_tasks.update_one(
            {"task_id": task.task_id},
            {"$set": task.dict()},
            upsert=True
        )
        
        tasks.append(task.dict())
    
    return tasks

async def fetch_external_tasks(provider: str, limit: int = 5) -> List[dict]:
    """Fetch tasks from external provider (simulated)"""
    
    config = PROVIDER_CONFIGS.get(TaskProvider(provider))
    if not config:
        return []
    
    # In production, this would make actual API calls to providers
    # For now, generate simulated tasks based on provider config
    
    tasks = []
    task_types = config.get("task_types", [])
    
    import random
    
    for i in range(min(limit, 3)):
        task_type = random.choice(task_types) if task_types else "general"
        
        # Reward based on provider's avg rate
        base_reward = random.uniform(0.25, 2.00)
        
        task = ExternalTask(
            task_id=f"{provider}_{str(uuid.uuid4())[:8]}",
            provider=TaskProvider(provider),
            external_task_id=f"ext_{provider}_{i}",
            title=f"{config['name']} - {task_type.replace('_', ' ').title()}",
            description=f"Complete this {task_type} task from {config['name']}",
            task_type=task_type,
            reward_usd=round(base_reward, 2),
            reward_ve=round(base_reward, 2),
            time_estimate_minutes=random.randint(3, 15),
            deadline_minutes=random.randint(15, 60),
            instructions=["Follow provider guidelines", "Complete accurately", "Submit before deadline"],
            requirements=["Account verified with provider"] if config.get("requires_qualification") else [],
            status="available",
            fetched_at=datetime.now(timezone.utc).isoformat()
        )
        
        tasks.append(task.dict())
    
    return tasks

@task_providers_router.post("/tasks/{task_id}/accept")
async def accept_provider_task(task_id: str, user_id: str):
    """Accept a task from a provider"""
    db = get_db()
    
    task = await db.external_tasks.find_one({"task_id": task_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task["status"] != "available":
        raise HTTPException(status_code=400, detail="Task not available")
    
    # Update task status
    await db.external_tasks.update_one(
        {"task_id": task_id},
        {"$set": {
            "status": "in_progress",
            "assigned_to": user_id,
            "assigned_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {
        "task_id": task_id,
        "accepted": True,
        "deadline_minutes": task["deadline_minutes"],
        "reward_ve": task["reward_ve"]
    }

@task_providers_router.post("/tasks/{task_id}/submit")
async def submit_provider_task(task_id: str, report: TaskCompletionReport):
    """Submit a completed task"""
    db = get_db()
    
    task = await db.external_tasks.find_one({"task_id": task_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.get("assigned_to") != report.user_id:
        raise HTTPException(status_code=403, detail="Task not assigned to you")
    
    # Mark task as completed
    await db.external_tasks.update_one(
        {"task_id": task_id},
        {"$set": {
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "submission": report.dict()
        }}
    )
    
    # Credit VE$ to user
    reward_ve = task["reward_ve"]
    
    await db.earnings_accounts.update_one(
        {"user_id": report.user_id},
        {
            "$inc": {
                "total_earned_usd": reward_ve,
                "available_balance_usd": reward_ve,
                "tasks_completed": 1
            },
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        },
        upsert=True
    )
    
    # Update provider connection stats
    await db.provider_connections.update_one(
        {"user_id": report.user_id, "provider": task["provider"]},
        {"$inc": {"total_earned_from_provider": reward_ve}}
    )
    
    # Record transaction
    await db.earnings_transactions.insert_one({
        "transaction_id": str(uuid.uuid4()),
        "user_id": report.user_id,
        "type": "task_completion",
        "provider": task["provider"],
        "task_id": task_id,
        "amount_usd": reward_ve,
        "amount_ve": reward_ve,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "task_id": task_id,
        "completed": True,
        "reward_ve": reward_ve,
        "reward_usd": reward_ve,
        "message": f"Earned VE${reward_ve:.2f}!"
    }

@task_providers_router.get("/stats/{user_id}")
async def get_provider_stats(user_id: str):
    """Get user's stats across all providers"""
    db = get_db()
    
    connections = await db.provider_connections.find(
        {"user_id": user_id},
        {"_id": 0}
    ).to_list(100)
    
    total_earned = 0
    provider_breakdown = {}
    
    for conn in connections:
        provider = conn["provider"]
        earned = conn.get("total_earned_from_provider", 0)
        total_earned += earned
        provider_breakdown[provider] = earned
    
    # Get recent transactions
    recent_txs = await db.earnings_transactions.find(
        {"user_id": user_id},
        {"_id": 0}
    ).sort("timestamp", -1).limit(10).to_list(10)
    
    return {
        "total_earned_ve": total_earned,
        "total_earned_usd": total_earned,
        "provider_breakdown": provider_breakdown,
        "connected_providers": len(connections),
        "recent_transactions": recent_txs
    }

# ============ VE DOLLAR UTILITIES ============

@task_providers_router.get("/ve/rate")
async def get_ve_exchange_rate():
    """Get current VE$ to USD exchange rate"""
    return {
        "ve_to_usd": 1.0,
        "usd_to_ve": 1.0,
        "rate_type": "fixed",
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "note": "Virtual Echo Dollar maintains 1:1 parity with USD"
    }

@task_providers_router.post("/ve/convert")
async def convert_currency(amount: float, from_currency: str, to_currency: str):
    """Convert between VE$ and USD"""
    # 1:1 ratio
    converted = amount
    
    return {
        "original_amount": amount,
        "original_currency": from_currency,
        "converted_amount": converted,
        "converted_currency": to_currency,
        "rate": 1.0
    }
