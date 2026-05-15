# External Micro-Task Provider Integration Router
# Real webhooks and callbacks for external task provider connections
# Supports Toloka, MTurk, Scale AI, Hive, Appen, and custom webhooks

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone
import uuid
import logging
import hmac
import hashlib
import os

external_providers_router = APIRouter(prefix="/external-providers", tags=["external-providers"])
logger = logging.getLogger(__name__)

# ============ Provider Webhook Secrets ============
# Each provider can have its own webhook secret for signature verification
WEBHOOK_SECRETS = {
    "toloka": os.environ.get("TOLOKA_WEBHOOK_SECRET", ""),
    "mturk": os.environ.get("MTURK_WEBHOOK_SECRET", ""),
    "scale_ai": os.environ.get("SCALE_WEBHOOK_SECRET", ""),
    "hive": os.environ.get("HIVE_WEBHOOK_SECRET", ""),
    "appen": os.environ.get("APPEN_WEBHOOK_SECRET", ""),
    "custom": os.environ.get("CUSTOM_WEBHOOK_SECRET", ""),
}

# ============ Provider Event Types ============
PROVIDER_EVENT_TYPES = {
    "task_available": {"description": "New task batch available", "action": "fetch_tasks"},
    "task_approved": {"description": "Task submission approved", "action": "credit_worker"},
    "task_rejected": {"description": "Task submission rejected", "action": "notify_worker"},
    "task_expired": {"description": "Task expired without completion", "action": "cleanup"},
    "payment_processed": {"description": "Payment processed by provider", "action": "update_earnings"},
    "account_update": {"description": "Account status changed", "action": "sync_account"},
    "quality_alert": {"description": "Worker quality flagged", "action": "review_worker"},
    "batch_complete": {"description": "Batch of tasks completed", "action": "process_batch"},
}

# ============ Models ============

class ProviderWebhookEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    provider: str
    event_type: str
    payload: Dict[str, Any]
    received_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    processed: bool = False
    processed_at: Optional[str] = None

class RegisterWebhookRequest(BaseModel):
    provider: str
    callback_url: str
    event_types: List[str] = ["task_available", "task_approved", "task_rejected"]
    secret: Optional[str] = None

class ExternalTaskMapping(BaseModel):
    external_task_id: str
    provider: str
    internal_task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_type: str
    payout: float
    worker_id: Optional[str] = None
    status: str = "available"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class SyncTasksRequest(BaseModel):
    provider: str
    task_type: Optional[str] = None
    limit: int = 50

# ============ Database Helper ============

def get_db():
    from server import db
    return db

# ============ Webhook Signature Verification ============

def verify_webhook_signature(provider: str, payload: bytes, signature: str) -> bool:
    """Verify webhook signature from provider"""
    secret = WEBHOOK_SECRETS.get(provider, "")
    if not secret:
        logger.warning(f"No webhook secret configured for {provider}")
        return True  # Allow if no secret configured (development mode)
    
    # Standard HMAC-SHA256 verification
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature.lower())

# ============ Background Task Processing ============

async def process_webhook_event(event: ProviderWebhookEvent):
    """Process webhook event in background"""
    db = get_db()
    
    try:
        event_info = PROVIDER_EVENT_TYPES.get(event.event_type, {})
        action = event_info.get("action", "log")
        
        if action == "credit_worker":
            await handle_task_approved(event)
        elif action == "notify_worker":
            await handle_task_rejected(event)
        elif action == "fetch_tasks":
            await handle_tasks_available(event)
        elif action == "update_earnings":
            await handle_payment_processed(event)
        elif action == "process_batch":
            await handle_batch_complete(event)
        
        # Mark event as processed
        await db.webhook_events.update_one(
            {"event_id": event.event_id},
            {"$set": {"processed": True, "processed_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        logger.info(f"Processed webhook event {event.event_id} - {event.event_type}")
        
    except Exception as e:
        logger.error(f"Error processing webhook event {event.event_id}: {e}")
        await db.webhook_events.update_one(
            {"event_id": event.event_id},
            {"$set": {"error": str(e)}}
        )

async def handle_task_approved(event: ProviderWebhookEvent):
    """Handle approved task - credit worker"""
    db = get_db()
    payload = event.payload
    
    external_task_id = payload.get("task_id") or payload.get("assignment_id") or payload.get("submission_id")
    payout = float(payload.get("payout", 0) or payload.get("reward", 0) or payload.get("amount", 0))
    worker_external_id = payload.get("worker_id") or payload.get("user_id")
    
    # Find task mapping
    mapping = await db.external_task_mappings.find_one({"external_task_id": external_task_id})
    
    if mapping:
        worker_id = mapping.get("worker_id") or worker_external_id
        
        # Credit worker
        if worker_id and payout > 0:
            await db.entity_wallets.update_one(
                {"entity_id": worker_id},
                {
                    "$inc": {"balance_ve": payout, "total_earned": payout},
                    "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
                },
                upsert=True
            )
            
            # Record transaction
            await db.external_provider_transactions.insert_one({
                "transaction_id": str(uuid.uuid4()),
                "provider": event.provider,
                "external_task_id": external_task_id,
                "internal_task_id": mapping.get("internal_task_id"),
                "worker_id": worker_id,
                "amount": payout,
                "type": "task_approved",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            # Update mapping status
            await db.external_task_mappings.update_one(
                {"external_task_id": external_task_id},
                {"$set": {"status": "approved", "paid": True, "paid_at": datetime.now(timezone.utc).isoformat()}}
            )
            
            logger.info(f"Credited {payout} VE$ to {worker_id} for task {external_task_id}")

async def handle_task_rejected(event: ProviderWebhookEvent):
    """Handle rejected task - notify worker"""
    db = get_db()
    payload = event.payload
    
    external_task_id = payload.get("task_id") or payload.get("assignment_id")
    reason = payload.get("reason", "Quality did not meet requirements")
    
    mapping = await db.external_task_mappings.find_one({"external_task_id": external_task_id})
    
    if mapping:
        worker_id = mapping.get("worker_id")
        
        # Create notification
        if worker_id:
            await db.worker_notifications.insert_one({
                "notification_id": str(uuid.uuid4()),
                "worker_id": worker_id,
                "type": "task_rejected",
                "provider": event.provider,
                "task_id": external_task_id,
                "message": f"Task rejected: {reason}",
                "read": False,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
        
        # Update mapping
        await db.external_task_mappings.update_one(
            {"external_task_id": external_task_id},
            {"$set": {"status": "rejected", "rejection_reason": reason}}
        )

async def handle_tasks_available(event: ProviderWebhookEvent):
    """Handle new tasks available notification"""
    db = get_db()
    payload = event.payload
    
    task_count = payload.get("count", 0) or payload.get("available_tasks", 0)
    task_type = payload.get("task_type", "general")
    
    # Record availability notification
    await db.provider_availability.update_one(
        {"provider": event.provider},
        {
            "$set": {
                "last_notification": datetime.now(timezone.utc).isoformat(),
                "available_count": task_count,
                "last_task_type": task_type
            }
        },
        upsert=True
    )
    
    logger.info(f"Provider {event.provider} has {task_count} tasks available ({task_type})")

async def handle_payment_processed(event: ProviderWebhookEvent):
    """Handle payment processed by provider"""
    db = get_db()
    payload = event.payload
    
    payment_id = payload.get("payment_id") or payload.get("transaction_id")
    amount = float(payload.get("amount", 0))
    currency = payload.get("currency", "USD")
    
    # Record payment
    await db.provider_payments.insert_one({
        "payment_id": payment_id,
        "provider": event.provider,
        "amount": amount,
        "currency": currency,
        "status": "processed",
        "payload": payload,
        "processed_at": datetime.now(timezone.utc).isoformat()
    })

async def handle_batch_complete(event: ProviderWebhookEvent):
    """Handle batch completion"""
    db = get_db()
    payload = event.payload
    
    batch_id = payload.get("batch_id") or payload.get("project_id")
    completed_count = payload.get("completed_count", 0)
    total_payout = float(payload.get("total_payout", 0))
    
    # Update batch record
    await db.provider_batches.update_one(
        {"batch_id": batch_id, "provider": event.provider},
        {
            "$set": {
                "status": "complete",
                "completed_count": completed_count,
                "total_payout": total_payout,
                "completed_at": datetime.now(timezone.utc).isoformat()
            }
        },
        upsert=True
    )

# ============ Webhook Endpoints ============

@external_providers_router.post("/webhook/{provider}")
async def receive_webhook(provider: str, request: Request, background_tasks: BackgroundTasks):
    """
    Generic webhook endpoint for external task providers.
    Each provider sends notifications here when tasks are approved/rejected/etc.
    """
    db = get_db()
    
    if provider not in WEBHOOK_SECRETS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
    
    body = await request.body()
    
    # Verify signature if secret is configured
    signature = request.headers.get("X-Webhook-Signature") or \
                request.headers.get("X-Signature") or \
                request.headers.get("Authorization", "").replace("Bearer ", "")
    
    if WEBHOOK_SECRETS.get(provider) and not verify_webhook_signature(provider, body, signature):
        logger.warning(f"Invalid webhook signature from {provider}")
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    try:
        import json
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        payload = {"raw": body.decode(errors="replace")}
    
    # Determine event type from payload
    event_type = payload.get("event_type") or \
                 payload.get("type") or \
                 payload.get("EventType") or \
                 payload.get("action") or \
                 "unknown"
    
    # Map provider-specific event types
    event_type_mapping = {
        # Toloka
        "ASSIGNMENT_ACCEPTED": "task_approved",
        "ASSIGNMENT_REJECTED": "task_rejected",
        "POOL_OPENED": "task_available",
        # MTurk
        "AssignmentApproved": "task_approved",
        "AssignmentRejected": "task_rejected",
        "HITReviewable": "batch_complete",
        # Scale AI
        "task_completed": "task_approved",
        "task_failed": "task_rejected",
        # Generic
        "approved": "task_approved",
        "rejected": "task_rejected",
        "completed": "task_approved",
        "available": "task_available",
    }
    
    normalized_event_type = event_type_mapping.get(event_type, event_type)
    
    # Create event record
    event = ProviderWebhookEvent(
        provider=provider,
        event_type=normalized_event_type,
        payload=payload
    )
    
    # Store event
    await db.webhook_events.insert_one(event.dict())
    
    # Process in background
    background_tasks.add_task(process_webhook_event, event)
    
    logger.info(f"Received webhook from {provider}: {normalized_event_type}")
    
    return {"received": True, "event_id": event.event_id, "event_type": normalized_event_type}

@external_providers_router.post("/webhook/toloka")
async def toloka_webhook(request: Request, background_tasks: BackgroundTasks):
    """Toloka-specific webhook endpoint"""
    return await receive_webhook("toloka", request, background_tasks)

@external_providers_router.post("/webhook/mturk")
async def mturk_webhook(request: Request, background_tasks: BackgroundTasks):
    """MTurk SNS notification endpoint"""
    db = get_db()
    
    body = await request.body()
    
    try:
        import json
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    # Handle SNS subscription confirmation
    if payload.get("Type") == "SubscriptionConfirmation":
        subscribe_url = payload.get("SubscribeURL")
        if subscribe_url:
            import httpx
            async with httpx.AsyncClient() as client:
                await client.get(subscribe_url)
            return {"confirmed": True}
    
    # Handle notification
    if payload.get("Type") == "Notification":
        message = json.loads(payload.get("Message", "{}"))
        event_type = message.get("EventType", "unknown")
        
        event = ProviderWebhookEvent(
            provider="mturk",
            event_type=event_type.lower().replace("assignment", "task_"),
            payload=message
        )
        
        await db.webhook_events.insert_one(event.dict())
        background_tasks.add_task(process_webhook_event, event)
    
    return {"received": True}

@external_providers_router.post("/webhook/scale")
async def scale_webhook(request: Request, background_tasks: BackgroundTasks):
    """Scale AI webhook endpoint"""
    return await receive_webhook("scale_ai", request, background_tasks)

@external_providers_router.post("/webhook/hive")
async def hive_webhook(request: Request, background_tasks: BackgroundTasks):
    """Hive webhook endpoint"""
    return await receive_webhook("hive", request, background_tasks)

@external_providers_router.post("/webhook/appen")
async def appen_webhook(request: Request, background_tasks: BackgroundTasks):
    """Appen webhook endpoint"""
    return await receive_webhook("appen", request, background_tasks)

# ============ Task Mapping Endpoints ============

@external_providers_router.post("/tasks/map")
async def map_external_task(
    external_task_id: str,
    provider: str,
    task_type: str,
    payout: float,
    worker_id: Optional[str] = None
):
    """Map an external task to internal tracking"""
    db = get_db()
    
    mapping = ExternalTaskMapping(
        external_task_id=external_task_id,
        provider=provider,
        task_type=task_type,
        payout=payout,
        worker_id=worker_id
    )
    
    await db.external_task_mappings.insert_one(mapping.dict())
    
    return {
        "mapped": True,
        "internal_task_id": mapping.internal_task_id,
        "external_task_id": external_task_id
    }

@external_providers_router.post("/tasks/claim")
async def claim_external_task(
    external_task_id: str,
    worker_id: str
):
    """Worker claims an external task"""
    db = get_db()
    
    result = await db.external_task_mappings.update_one(
        {"external_task_id": external_task_id, "status": "available"},
        {
            "$set": {
                "worker_id": worker_id,
                "status": "claimed",
                "claimed_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=400, detail="Task not available or already claimed")
    
    return {"claimed": True, "worker_id": worker_id}

@external_providers_router.post("/tasks/submit")
async def submit_external_task(
    external_task_id: str,
    worker_id: str,
    response: Dict[str, Any]
):
    """Submit response to external task"""
    db = get_db()
    
    mapping = await db.external_task_mappings.find_one({"external_task_id": external_task_id})
    
    if not mapping:
        raise HTTPException(status_code=404, detail="Task mapping not found")
    
    if mapping.get("worker_id") != worker_id:
        raise HTTPException(status_code=403, detail="Task not claimed by this worker")
    
    # Update mapping with submission
    await db.external_task_mappings.update_one(
        {"external_task_id": external_task_id},
        {
            "$set": {
                "status": "submitted",
                "response": response,
                "submitted_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Record submission
    await db.external_task_submissions.insert_one({
        "submission_id": str(uuid.uuid4()),
        "external_task_id": external_task_id,
        "internal_task_id": mapping.get("internal_task_id"),
        "provider": mapping.get("provider"),
        "worker_id": worker_id,
        "response": response,
        "status": "pending_review",
        "submitted_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "submitted": True,
        "external_task_id": external_task_id,
        "status": "pending_review"
    }

# ============ Provider Sync Endpoints ============

@external_providers_router.post("/sync/tasks")
async def sync_external_tasks(data: SyncTasksRequest):
    """Manually sync tasks from external provider"""
    db = get_db()
    
    try:
        from task_providers import get_provider_manager
        manager = get_provider_manager()
        
        if not manager.get_active_providers():
            return {
                "synced": False,
                "message": "No providers configured",
                "tasks": []
            }
        
        tasks = await manager.fetch_tasks_by_provider(
            data.provider, 
            data.task_type, 
            data.limit
        )
        
        # Map fetched tasks
        mapped_count = 0
        for task in tasks:
            existing = await db.external_task_mappings.find_one({
                "external_task_id": task.task_id
            })
            
            if not existing:
                mapping = ExternalTaskMapping(
                    external_task_id=task.task_id,
                    provider=task.provider,
                    task_type=task.task_type,
                    payout=task.payout
                )
                await db.external_task_mappings.insert_one(mapping.dict())
                mapped_count += 1
        
        return {
            "synced": True,
            "provider": data.provider,
            "fetched_count": len(tasks),
            "new_mapped": mapped_count
        }
        
    except ImportError:
        return {"synced": False, "message": "Task providers module not available"}
    except Exception as e:
        logger.error(f"Error syncing tasks: {e}")
        return {"synced": False, "error": str(e)}

@external_providers_router.get("/status")
async def get_external_providers_status():
    """Get status of external provider integrations"""
    db = get_db()
    
    # Check configured webhooks
    configured_secrets = {k: bool(v) for k, v in WEBHOOK_SECRETS.items()}
    
    # Recent webhook events
    recent_events = await db.webhook_events.find(
        {},
        {"_id": 0, "event_id": 1, "provider": 1, "event_type": 1, "processed": 1, "received_at": 1}
    ).sort("received_at", -1).limit(10).to_list(10)
    
    # Provider availability
    availability = await db.provider_availability.find({}, {"_id": 0}).to_list(10)
    
    # Task mapping stats
    pipeline = [
        {"$group": {
            "_id": {"provider": "$provider", "status": "$status"},
            "count": {"$sum": 1}
        }}
    ]
    mapping_stats = await db.external_task_mappings.aggregate(pipeline).to_list(50)
    
    return {
        "webhook_secrets_configured": configured_secrets,
        "supported_event_types": list(PROVIDER_EVENT_TYPES.keys()),
        "recent_events": recent_events,
        "provider_availability": availability,
        "task_mapping_stats": mapping_stats
    }

@external_providers_router.get("/events")
async def get_webhook_events(
    provider: Optional[str] = None,
    event_type: Optional[str] = None,
    processed: Optional[bool] = None,
    limit: int = 50
):
    """Get webhook events with optional filters"""
    db = get_db()
    
    query = {}
    if provider:
        query["provider"] = provider
    if event_type:
        query["event_type"] = event_type
    if processed is not None:
        query["processed"] = processed
    
    events = await db.webhook_events.find(
        query,
        {"_id": 0}
    ).sort("received_at", -1).limit(limit).to_list(limit)
    
    return {"events": events, "count": len(events)}

@external_providers_router.get("/transactions/{worker_id}")
async def get_worker_external_transactions(worker_id: str, limit: int = 50):
    """Get external provider transactions for a worker"""
    db = get_db()
    
    transactions = await db.external_provider_transactions.find(
        {"worker_id": worker_id},
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    
    total = sum(t.get("amount", 0) for t in transactions)
    
    return {
        "worker_id": worker_id,
        "transactions": transactions,
        "total_earned": total,
        "count": len(transactions)
    }

@external_providers_router.get("/notifications/{worker_id}")
async def get_worker_notifications(worker_id: str, unread_only: bool = False, limit: int = 50):
    """Get notifications for a worker"""
    db = get_db()
    
    query = {"worker_id": worker_id}
    if unread_only:
        query["read"] = False
    
    notifications = await db.worker_notifications.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {"notifications": notifications, "count": len(notifications)}

@external_providers_router.post("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str):
    """Mark notification as read"""
    db = get_db()
    
    result = await db.worker_notifications.update_one(
        {"notification_id": notification_id},
        {"$set": {"read": True, "read_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"marked_read": result.modified_count > 0}
