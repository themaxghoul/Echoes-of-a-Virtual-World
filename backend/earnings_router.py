# ApexForge Collective - Earnings Ecosystem
# Real-world income generation through gameplay

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum
import uuid
import asyncio
import hashlib

earnings_router = APIRouter(prefix="/earnings", tags=["earnings"])

# ============ EARNINGS MODELS ============

class IncomeStreamType(str, Enum):
    MICRO_TASKS = "micro_tasks"
    DATA_LABELING = "data_labeling"
    TRANSCRIPTION = "transcription"
    SURVEYS = "surveys"
    CRYPTO_STAKING = "crypto_staking"
    COMPUTE_SHARE = "compute_share"
    AFFILIATE = "affiliate"
    CONTENT_CREATION = "content_creation"
    BLOCKCHAIN_SOLVE = "blockchain_solve"

class TaskDifficulty(str, Enum):
    EASY = "easy"          # $0.05-0.10 per task
    MEDIUM = "medium"      # $0.25-0.50 per task
    HARD = "hard"          # $1.00-2.00 per task
    EXPERT = "expert"      # $5.00-10.00 per task

class EarningsAccount(BaseModel):
    user_id: str
    total_earned_usd: float = 0.0
    available_balance_usd: float = 0.0
    pending_balance_usd: float = 0.0
    total_withdrawn_usd: float = 0.0
    crypto_balance: Dict[str, float] = Field(default_factory=dict)  # {ETH: 0.01, MATIC: 5.0}
    connected_wallets: List[str] = Field(default_factory=list)
    verified_18_plus: bool = False
    kyc_verified: bool = False
    geographic_eligible: bool = True
    income_streams_enabled: List[str] = Field(default_factory=list)
    hourly_rate_avg: float = 0.0
    tasks_completed: int = 0
    created_at: str = ""
    updated_at: str = ""

class MicroTask(BaseModel):
    task_id: str
    task_type: IncomeStreamType
    difficulty: TaskDifficulty
    title: str
    description: str
    instructions: List[str]
    reward_usd: float
    reward_crypto: Optional[Dict[str, float]] = None
    time_estimate_minutes: int
    deadline_minutes: int
    required_accuracy: float = 0.95
    data_payload: Optional[Dict[str, Any]] = None
    status: str = "available"  # available, in_progress, completed, expired
    assigned_to: Optional[str] = None
    created_at: str = ""

class TaskSubmission(BaseModel):
    task_id: str
    user_id: str
    submission_data: Dict[str, Any]
    time_taken_seconds: int

class WithdrawalRequest(BaseModel):
    user_id: str
    amount_usd: float
    method: str  # paypal, crypto, bank_transfer
    destination: str  # email, wallet address, or bank info

# ============ TASK TEMPLATES ============

# High-value task templates that can earn $5-10/hr
TASK_TEMPLATES = {
    # Data Labeling - $0.50-2.00 per task, 2-5 min each = $6-24/hr
    "image_classification": {
        "type": IncomeStreamType.DATA_LABELING,
        "difficulty": TaskDifficulty.MEDIUM,
        "title": "Artifact Classification",
        "description": "Classify images into categories for AI training",
        "instructions": [
            "View the displayed image carefully",
            "Select all applicable categories",
            "Rate your confidence level",
            "Submit within the time limit"
        ],
        "reward_usd": 0.50,
        "time_estimate_minutes": 3,
        "deadline_minutes": 10
    },
    "text_annotation": {
        "type": IncomeStreamType.DATA_LABELING,
        "difficulty": TaskDifficulty.MEDIUM,
        "title": "Ancient Text Annotation",
        "description": "Highlight and label entities in text passages",
        "instructions": [
            "Read the text passage carefully",
            "Highlight all named entities (people, places, organizations)",
            "Label each entity with the correct type",
            "Verify your annotations"
        ],
        "reward_usd": 0.75,
        "time_estimate_minutes": 5,
        "deadline_minutes": 15
    },
    "sentiment_analysis": {
        "type": IncomeStreamType.DATA_LABELING,
        "difficulty": TaskDifficulty.EASY,
        "title": "Mood Detection",
        "description": "Analyze sentiment in text samples",
        "instructions": [
            "Read the text sample",
            "Determine the overall sentiment (positive/negative/neutral)",
            "Rate the intensity (1-5)",
            "Identify key emotional phrases"
        ],
        "reward_usd": 0.25,
        "time_estimate_minutes": 2,
        "deadline_minutes": 5
    },
    
    # Transcription - $1.00-5.00 per task, 5-15 min = $4-20/hr
    "audio_transcription": {
        "type": IncomeStreamType.TRANSCRIPTION,
        "difficulty": TaskDifficulty.HARD,
        "title": "Oracle Recording Transcription",
        "description": "Transcribe audio recordings to text",
        "instructions": [
            "Listen to the audio clip carefully",
            "Type out exactly what you hear",
            "Include timestamps for speaker changes",
            "Mark unclear sections with [inaudible]"
        ],
        "reward_usd": 2.00,
        "time_estimate_minutes": 10,
        "deadline_minutes": 30
    },
    "video_captioning": {
        "type": IncomeStreamType.TRANSCRIPTION,
        "difficulty": TaskDifficulty.HARD,
        "title": "Vision Captioning",
        "description": "Add captions to video segments",
        "instructions": [
            "Watch the video segment",
            "Create accurate timed captions",
            "Sync captions with speech",
            "Include sound descriptions [music], [applause]"
        ],
        "reward_usd": 3.00,
        "time_estimate_minutes": 15,
        "deadline_minutes": 45
    },
    
    # Surveys - $1.00-5.00 per survey, 5-20 min = $3-15/hr
    "market_research": {
        "type": IncomeStreamType.SURVEYS,
        "difficulty": TaskDifficulty.MEDIUM,
        "title": "Oracle Consultation",
        "description": "Share opinions on products and services",
        "instructions": [
            "Answer all questions honestly",
            "Provide detailed responses where requested",
            "Complete the entire survey",
            "Quality checks are included"
        ],
        "reward_usd": 2.50,
        "time_estimate_minutes": 15,
        "deadline_minutes": 30
    },
    
    # Content Review - $0.50-1.50 per task, 3-5 min = $6-18/hr
    "content_moderation": {
        "type": IncomeStreamType.MICRO_TASKS,
        "difficulty": TaskDifficulty.MEDIUM,
        "title": "Guardian Duty",
        "description": "Review content for policy compliance",
        "instructions": [
            "Review the content item",
            "Check against provided guidelines",
            "Flag any violations",
            "Provide reasoning for your decision"
        ],
        "reward_usd": 0.75,
        "time_estimate_minutes": 4,
        "deadline_minutes": 10
    },
    
    # Expert Tasks - $5-15 per task, 30-60 min = $5-15/hr
    "document_review": {
        "type": IncomeStreamType.DATA_LABELING,
        "difficulty": TaskDifficulty.EXPERT,
        "title": "Scroll Analysis",
        "description": "Review and extract data from complex documents",
        "instructions": [
            "Analyze the document structure",
            "Extract all requested data fields",
            "Verify accuracy of extraction",
            "Flag any anomalies"
        ],
        "reward_usd": 8.00,
        "time_estimate_minutes": 45,
        "deadline_minutes": 90
    },
    "code_review": {
        "type": IncomeStreamType.MICRO_TASKS,
        "difficulty": TaskDifficulty.EXPERT,
        "title": "Spell Verification",
        "description": "Review code for bugs and improvements",
        "instructions": [
            "Read through the code carefully",
            "Identify any bugs or issues",
            "Suggest improvements",
            "Rate code quality"
        ],
        "reward_usd": 10.00,
        "time_estimate_minutes": 30,
        "deadline_minutes": 60
    },
    
    # Blockchain Tasks - Variable rewards
    "hash_verification": {
        "type": IncomeStreamType.BLOCKCHAIN_SOLVE,
        "difficulty": TaskDifficulty.MEDIUM,
        "title": "Cryptographic Puzzle",
        "description": "Verify blockchain transactions",
        "instructions": [
            "Review the transaction data",
            "Verify the hash matches",
            "Confirm transaction validity",
            "Submit verification"
        ],
        "reward_usd": 0.10,
        "reward_crypto": {"MATIC": 0.05},
        "time_estimate_minutes": 1,
        "deadline_minutes": 5
    }
}

# Geographic restrictions
RESTRICTED_REGIONS = [
    "CU",  # Cuba
    "IR",  # Iran
    "KP",  # North Korea
    "SY",  # Syria
    "RU",  # Russia (sanctions)
    "BY",  # Belarus
]

SUPPORTED_REGIONS = [
    "US", "CA", "GB", "DE", "FR", "AU", "JP", "KR", "SG", "NL", "SE", "NO", "DK", "FI",
    "IE", "NZ", "CH", "AT", "BE", "IT", "ES", "PT", "PL", "CZ", "HU", "RO", "BG", "HR",
    "SK", "SI", "LT", "LV", "EE", "MT", "CY", "LU", "MX", "BR", "AR", "CL", "CO", "PE",
    "IN", "PH", "TH", "MY", "ID", "VN", "ZA", "NG", "KE", "GH", "EG", "MA", "TN"
]

# Supported cryptocurrencies
SUPPORTED_CRYPTO = {
    "ETH": {"name": "Ethereum", "network": "mainnet", "min_withdrawal": 0.01},
    "MATIC": {"name": "Polygon", "network": "polygon", "min_withdrawal": 10.0},
    "USDC": {"name": "USD Coin", "network": "polygon", "min_withdrawal": 10.0},
    "USDT": {"name": "Tether", "network": "polygon", "min_withdrawal": 10.0},
}

# ============ EARNINGS ENDPOINTS ============

def get_db():
    """Get database reference - imported from main server"""
    from server import db
    return db

@earnings_router.post("/account/create")
async def create_earnings_account(user_id: str):
    """Create an earnings account for a user"""
    db = get_db()
    
    existing = await db.earnings_accounts.find_one({"user_id": user_id})
    if existing:
        raise HTTPException(status_code=400, detail="Earnings account already exists")
    
    account = EarningsAccount(
        user_id=user_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        updated_at=datetime.now(timezone.utc).isoformat()
    )
    
    await db.earnings_accounts.insert_one(account.dict())
    
    return {"account_created": True, "user_id": user_id}

@earnings_router.get("/account/{user_id}")
async def get_earnings_account(user_id: str):
    """Get user's earnings account"""
    db = get_db()
    
    account = await db.earnings_accounts.find_one({"user_id": user_id}, {"_id": 0})
    if not account:
        # Auto-create if not exists
        account = EarningsAccount(
            user_id=user_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat()
        ).dict()
        await db.earnings_accounts.insert_one(account)
    
    return account

@earnings_router.post("/account/{user_id}/verify-age")
async def verify_age(user_id: str, birth_date: str, consent_given: bool):
    """Verify user is 18+ for earnings eligibility"""
    db = get_db()
    
    if not consent_given:
        raise HTTPException(status_code=400, detail="Consent required")
    
    # Calculate age
    birth = datetime.fromisoformat(birth_date)
    today = datetime.now(timezone.utc)
    age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
    
    if age < 18:
        raise HTTPException(status_code=403, detail="Must be 18+ to participate in earnings")
    
    await db.earnings_accounts.update_one(
        {"user_id": user_id},
        {"$set": {
            "verified_18_plus": True,
            "age_verified_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"verified": True, "age": age}

@earnings_router.post("/account/{user_id}/verify-region")
async def verify_region(user_id: str, country_code: str):
    """Verify user's geographic eligibility"""
    db = get_db()
    
    if country_code.upper() in RESTRICTED_REGIONS:
        await db.earnings_accounts.update_one(
            {"user_id": user_id},
            {"$set": {
                "geographic_eligible": False,
                "country_code": country_code.upper(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        raise HTTPException(status_code=403, detail="Earnings not available in your region")
    
    eligible = country_code.upper() in SUPPORTED_REGIONS
    
    await db.earnings_accounts.update_one(
        {"user_id": user_id},
        {"$set": {
            "geographic_eligible": eligible,
            "country_code": country_code.upper(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"eligible": eligible, "country": country_code.upper()}

@earnings_router.get("/tasks/available")
async def get_available_tasks(user_id: str, task_type: Optional[str] = None, limit: int = 20):
    """Get available tasks for a user"""
    db = get_db()
    
    # Check eligibility
    account = await db.earnings_accounts.find_one({"user_id": user_id})
    if not account:
        raise HTTPException(status_code=404, detail="Earnings account not found")
    
    if not account.get("verified_18_plus"):
        raise HTTPException(status_code=403, detail="Age verification required")
    
    if not account.get("geographic_eligible", True):
        raise HTTPException(status_code=403, detail="Not eligible in your region")
    
    # Build query
    query = {"status": "available"}
    if task_type:
        query["task_type"] = task_type
    
    tasks = await db.micro_tasks.find(query, {"_id": 0}).limit(limit).to_list(limit)
    
    # If no tasks in DB, generate from templates
    if not tasks:
        tasks = await generate_tasks_from_templates(10)
    
    return {"tasks": tasks, "count": len(tasks)}

async def generate_tasks_from_templates(count: int = 10) -> List[dict]:
    """Generate tasks from templates"""
    db = get_db()
    
    generated = []
    templates = list(TASK_TEMPLATES.values())
    
    for i in range(count):
        template = templates[i % len(templates)]
        task = MicroTask(
            task_id=str(uuid.uuid4()),
            task_type=template["type"],
            difficulty=template["difficulty"],
            title=template["title"],
            description=template["description"],
            instructions=template["instructions"],
            reward_usd=template["reward_usd"],
            reward_crypto=template.get("reward_crypto"),
            time_estimate_minutes=template["time_estimate_minutes"],
            deadline_minutes=template["deadline_minutes"],
            status="available",
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
        await db.micro_tasks.insert_one(task.dict())
        generated.append(task.dict())
    
    return generated

@earnings_router.post("/tasks/{task_id}/accept")
async def accept_task(task_id: str, user_id: str):
    """Accept a task to work on"""
    db = get_db()
    
    task = await db.micro_tasks.find_one({"task_id": task_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task["status"] != "available":
        raise HTTPException(status_code=400, detail="Task not available")
    
    # Assign task to user
    deadline = datetime.now(timezone.utc).timestamp() + (task["deadline_minutes"] * 60)
    
    await db.micro_tasks.update_one(
        {"task_id": task_id},
        {"$set": {
            "status": "in_progress",
            "assigned_to": user_id,
            "assigned_at": datetime.now(timezone.utc).isoformat(),
            "deadline_timestamp": deadline
        }}
    )
    
    return {
        "task_id": task_id,
        "accepted": True,
        "deadline_timestamp": deadline,
        "deadline_minutes": task["deadline_minutes"]
    }

@earnings_router.post("/tasks/{task_id}/submit")
async def submit_task(task_id: str, submission: TaskSubmission):
    """Submit a completed task"""
    db = get_db()
    
    task = await db.micro_tasks.find_one({"task_id": task_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task["assigned_to"] != submission.user_id:
        raise HTTPException(status_code=403, detail="Task not assigned to you")
    
    # Check deadline
    if datetime.now(timezone.utc).timestamp() > task.get("deadline_timestamp", float('inf')):
        await db.micro_tasks.update_one(
            {"task_id": task_id},
            {"$set": {"status": "expired"}}
        )
        raise HTTPException(status_code=400, detail="Task deadline expired")
    
    # Store submission for review
    submission_record = {
        "submission_id": str(uuid.uuid4()),
        "task_id": task_id,
        "user_id": submission.user_id,
        "submission_data": submission.submission_data,
        "time_taken_seconds": submission.time_taken_seconds,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending_review",
        "reward_usd": task["reward_usd"],
        "reward_crypto": task.get("reward_crypto")
    }
    
    await db.task_submissions.insert_one(submission_record)
    
    # Auto-approve for now (in production, this would go through review)
    await process_task_completion(submission.user_id, task_id, task["reward_usd"], task.get("reward_crypto"))
    
    return {
        "submission_id": submission_record["submission_id"],
        "submitted": True,
        "reward_usd": task["reward_usd"],
        "reward_crypto": task.get("reward_crypto"),
        "status": "approved"
    }

async def process_task_completion(user_id: str, task_id: str, reward_usd: float, reward_crypto: Optional[dict] = None):
    """Process completed task and credit earnings"""
    db = get_db()
    
    # Update task status
    await db.micro_tasks.update_one(
        {"task_id": task_id},
        {"$set": {"status": "completed"}}
    )
    
    # Credit earnings
    update = {
        "$inc": {
            "total_earned_usd": reward_usd,
            "available_balance_usd": reward_usd,
            "tasks_completed": 1
        },
        "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
    }
    
    if reward_crypto:
        for crypto, amount in reward_crypto.items():
            update["$inc"][f"crypto_balance.{crypto}"] = amount
    
    await db.earnings_accounts.update_one({"user_id": user_id}, update)
    
    # Record transaction
    await db.earnings_transactions.insert_one({
        "transaction_id": str(uuid.uuid4()),
        "user_id": user_id,
        "type": "task_completion",
        "task_id": task_id,
        "amount_usd": reward_usd,
        "crypto_amounts": reward_crypto,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

@earnings_router.get("/stats/{user_id}")
async def get_earnings_stats(user_id: str):
    """Get detailed earnings statistics"""
    db = get_db()
    
    account = await db.earnings_accounts.find_one({"user_id": user_id}, {"_id": 0})
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Calculate hourly rate
    transactions = await db.earnings_transactions.find({"user_id": user_id}).to_list(1000)
    
    total_time_minutes = 0
    total_earned = 0
    
    for tx in transactions:
        total_earned += tx.get("amount_usd", 0)
        # Estimate time from task type
        total_time_minutes += 5  # Average
    
    hourly_rate = (total_earned / (total_time_minutes / 60)) if total_time_minutes > 0 else 0
    
    return {
        "account": account,
        "hourly_rate_avg": round(hourly_rate, 2),
        "total_transactions": len(transactions),
        "supported_crypto": SUPPORTED_CRYPTO,
        "withdrawal_methods": ["paypal", "crypto", "bank_transfer"]
    }

@earnings_router.post("/withdraw")
async def request_withdrawal(request: WithdrawalRequest):
    """Request a withdrawal of earnings"""
    db = get_db()
    
    account = await db.earnings_accounts.find_one({"user_id": request.user_id})
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    if not account.get("kyc_verified") and request.amount_usd > 100:
        raise HTTPException(status_code=403, detail="KYC verification required for withdrawals over $100")
    
    # Fixed withdrawal fee - $0.25 to keep the game running
    WITHDRAWAL_FEE = 0.25
    total_deduction = request.amount_usd + WITHDRAWAL_FEE
    
    if total_deduction > account.get("available_balance_usd", 0):
        raise HTTPException(status_code=400, detail=f"Insufficient balance. Need ${total_deduction} (${request.amount_usd} + ${WITHDRAWAL_FEE} fee)")
    
    # Minimum withdrawals
    min_withdrawal = 1.0  # $1 minimum
    if request.amount_usd < min_withdrawal:
        raise HTTPException(status_code=400, detail=f"Minimum withdrawal is ${min_withdrawal}")
    
    # Create withdrawal request
    withdrawal = {
        "withdrawal_id": str(uuid.uuid4()),
        "user_id": request.user_id,
        "amount_usd": request.amount_usd,
        "fee_usd": WITHDRAWAL_FEE,
        "total_deducted": total_deduction,
        "method": request.method,
        "destination": request.destination,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.withdrawal_requests.insert_one(withdrawal)
    
    # Update balance
    await db.earnings_accounts.update_one(
        {"user_id": request.user_id},
        {
            "$inc": {
                "available_balance_usd": -total_deduction,
                "pending_balance_usd": request.amount_usd,
                "total_fees_paid": WITHDRAWAL_FEE
            },
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    # Record fee transaction for game operations
    await db.earnings_transactions.insert_one({
        "transaction_id": str(uuid.uuid4()),
        "user_id": "apexforge_operations",
        "type": "withdrawal_fee",
        "source_user": request.user_id,
        "amount_usd": WITHDRAWAL_FEE,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "withdrawal_id": withdrawal["withdrawal_id"],
        "amount_requested": request.amount_usd,
        "fee": WITHDRAWAL_FEE,
        "total_deducted": total_deduction,
        "method": request.method,
        "status": "pending",
        "estimated_processing": "1-3 business days"
    }

class WithdrawalDestination(BaseModel):
    user_id: str
    withdrawal_id: str
    destination_type: str  # "wallet", "game_balance", "split"
    wallet_address: Optional[str] = None
    wallet_percentage: float = 100.0  # If split, % to wallet
    
@earnings_router.post("/withdraw/set-destination")
async def set_withdrawal_destination(dest: WithdrawalDestination):
    """Set where withdrawal funds should go before processing"""
    db = get_db()
    
    withdrawal = await db.withdrawal_requests.find_one({
        "withdrawal_id": dest.withdrawal_id,
        "user_id": dest.user_id
    })
    
    if not withdrawal:
        raise HTTPException(status_code=404, detail="Withdrawal not found")
    
    if withdrawal["status"] != "pending":
        raise HTTPException(status_code=400, detail="Withdrawal already processed")
    
    # Validate destination
    if dest.destination_type == "wallet" and not dest.wallet_address:
        raise HTTPException(status_code=400, detail="Wallet address required")
    
    if dest.destination_type == "split":
        if dest.wallet_percentage < 0 or dest.wallet_percentage > 100:
            raise HTTPException(status_code=400, detail="Wallet percentage must be 0-100")
    
    await db.withdrawal_requests.update_one(
        {"withdrawal_id": dest.withdrawal_id},
        {"$set": {
            "destination_type": dest.destination_type,
            "wallet_address": dest.wallet_address,
            "wallet_percentage": dest.wallet_percentage,
            "game_balance_percentage": 100 - dest.wallet_percentage if dest.destination_type == "split" else 0,
            "destination_confirmed": True,
            "destination_confirmed_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {
        "withdrawal_id": dest.withdrawal_id,
        "destination_type": dest.destination_type,
        "wallet_address": dest.wallet_address if dest.destination_type in ["wallet", "split"] else None,
        "wallet_percentage": dest.wallet_percentage if dest.destination_type == "split" else (100 if dest.destination_type == "wallet" else 0),
        "game_balance_percentage": 100 - dest.wallet_percentage if dest.destination_type == "split" else (100 if dest.destination_type == "game_balance" else 0),
        "confirmed": True
    }

@earnings_router.get("/withdraw/preview/{user_id}")
async def preview_withdrawal(user_id: str, amount: float):
    """Preview withdrawal with fee breakdown before confirming"""
    db = get_db()
    
    account = await db.earnings_accounts.find_one({"user_id": user_id})
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    WITHDRAWAL_FEE = 0.25
    total_deduction = amount + WITHDRAWAL_FEE
    
    return {
        "amount_requested": amount,
        "withdrawal_fee": WITHDRAWAL_FEE,
        "fee_purpose": "Supports game operations and infrastructure",
        "total_deduction": total_deduction,
        "available_balance": account.get("available_balance_usd", 0),
        "remaining_after_withdrawal": max(0, account.get("available_balance_usd", 0) - total_deduction),
        "can_withdraw": account.get("available_balance_usd", 0) >= total_deduction,
        "destination_options": [
            {"type": "wallet", "description": "Send to connected crypto wallet"},
            {"type": "game_balance", "description": "Keep in game for purchases/upgrades"},
            {"type": "split", "description": "Split between wallet and game balance"}
        ],
        "connected_wallets": account.get("connected_wallets", [])
    }

@earnings_router.get("/income-streams")
async def get_income_streams():
    """Get all available income streams and their details"""
    return {
        "streams": {
            "micro_tasks": {
                "name": "Micro Tasks",
                "description": "Quick tasks like data labeling, content review",
                "avg_hourly_rate": "$6-12/hr",
                "requirements": ["18+", "Geographic eligibility"],
                "game_integration": "Task Board in Guild Hall"
            },
            "transcription": {
                "name": "Transcription",
                "description": "Convert audio/video to text",
                "avg_hourly_rate": "$8-15/hr",
                "requirements": ["18+", "Good typing speed", "Headphones"],
                "game_integration": "Oracle's Transcription Quests"
            },
            "data_labeling": {
                "name": "Data Labeling",
                "description": "Annotate images, text, and videos for AI training",
                "avg_hourly_rate": "$6-12/hr",
                "requirements": ["18+", "Attention to detail"],
                "game_integration": "Archivist's Cataloging System"
            },
            "surveys": {
                "name": "Market Research",
                "description": "Share opinions on products and services",
                "avg_hourly_rate": "$5-10/hr",
                "requirements": ["18+", "Honest responses"],
                "game_integration": "Oracle Consultations"
            },
            "compute_share": {
                "name": "Compute Sharing",
                "description": "Share unused device resources",
                "avg_hourly_rate": "$1-5/hr (passive)",
                "requirements": ["Opt-in consent", "Device with spare resources"],
                "game_integration": "Crystal Network Contribution"
            },
            "affiliate": {
                "name": "Affiliate Marketing",
                "description": "Earn from referrals and recommendations",
                "avg_hourly_rate": "Variable (commission-based)",
                "requirements": ["Share genuine recommendations"],
                "game_integration": "Merchant Guild Partnerships"
            },
            "crypto_staking": {
                "name": "Crypto Staking",
                "description": "Earn rewards by staking supported tokens",
                "avg_hourly_rate": "Variable (APY-based)",
                "requirements": ["Connected wallet", "Token holdings"],
                "game_integration": "Treasury Vault Staking"
            },
            "blockchain_solve": {
                "name": "Blockchain Verification",
                "description": "Verify transactions and solve cryptographic puzzles",
                "avg_hourly_rate": "$3-8/hr + crypto rewards",
                "requirements": ["18+", "Basic crypto knowledge"],
                "game_integration": "Cryptomancer's Challenges"
            }
        },
        "supported_crypto": SUPPORTED_CRYPTO,
        "supported_regions": SUPPORTED_REGIONS,
        "restricted_regions": RESTRICTED_REGIONS
    }

@earnings_router.post("/wallet/connect")
async def connect_wallet(user_id: str, wallet_address: str, network: str = "polygon"):
    """Connect a crypto wallet to earnings account"""
    db = get_db()
    
    # Validate wallet address format (basic check)
    if not wallet_address.startswith("0x") or len(wallet_address) != 42:
        raise HTTPException(status_code=400, detail="Invalid wallet address format")
    
    await db.earnings_accounts.update_one(
        {"user_id": user_id},
        {
            "$addToSet": {"connected_wallets": wallet_address},
            "$set": {
                "primary_wallet": wallet_address,
                "wallet_network": network,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {
        "wallet_connected": True,
        "address": wallet_address,
        "network": network
    }



# ============ REAL EARNINGS TRACKING ============

class WithdrawalPreferences(BaseModel):
    user_id: str
    default_method: str = "game_balance"  # crypto, game_balance
    default_wallet: Optional[str] = None
    wallet_percentage: int = 100  # percentage to send to wallet
    auto_withdraw_threshold: Optional[float] = None  # auto-withdraw when balance reaches this
    
@earnings_router.get("/history/{user_id}")
async def get_earnings_history(user_id: str, days: int = 30, limit: int = 100):
    """Get detailed earnings history with daily/weekly breakdowns"""
    db = get_db()
    
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)
    
    # Get all transactions in date range
    transactions = await db.earnings_transactions.find({
        "user_id": user_id,
        "timestamp": {"$gte": start_date.isoformat()}
    }).sort("timestamp", -1).to_list(limit)
    
    # Also get RT task session earnings
    rt_sessions = await db.rt_task_sessions.find({
        "worker_id": user_id,
        "started_at": {"$gte": start_date.isoformat()}
    }).to_list(500)
    
    # Calculate daily earnings
    daily_earnings = {}
    today = now.date()
    week_start = today - timedelta(days=today.weekday())
    
    today_total = 0.0
    week_total = 0.0
    
    for tx in transactions:
        tx_date = datetime.fromisoformat(tx["timestamp"].replace("Z", "+00:00")).date()
        date_key = tx_date.isoformat()
        
        amount = tx.get("amount_usd", 0)
        if date_key not in daily_earnings:
            daily_earnings[date_key] = {"total": 0, "tasks": 0, "sources": {}}
        
        daily_earnings[date_key]["total"] += amount
        daily_earnings[date_key]["tasks"] += 1
        
        source = tx.get("type", "unknown")
        daily_earnings[date_key]["sources"][source] = daily_earnings[date_key]["sources"].get(source, 0) + amount
        
        if tx_date == today:
            today_total += amount
        if tx_date >= week_start:
            week_total += amount
    
    # Add RT session earnings
    for session in rt_sessions:
        session_date = datetime.fromisoformat(session["started_at"].replace("Z", "+00:00")).date()
        date_key = session_date.isoformat()
        
        amount = session.get("earnings", 0)
        tasks_done = session.get("tasks_completed", 0)
        
        if date_key not in daily_earnings:
            daily_earnings[date_key] = {"total": 0, "tasks": 0, "sources": {}}
        
        daily_earnings[date_key]["total"] += amount
        daily_earnings[date_key]["tasks"] += tasks_done
        daily_earnings[date_key]["sources"]["rt_tasks"] = daily_earnings[date_key]["sources"].get("rt_tasks", 0) + amount
        
        if session_date == today:
            today_total += amount
        if session_date >= week_start:
            week_total += amount
    
    # Get account for totals
    account = await db.earnings_accounts.find_one({"user_id": user_id}, {"_id": 0})
    
    return {
        "user_id": user_id,
        "today_earned": round(today_total, 2),
        "week_earned": round(week_total, 2),
        "daily_breakdown": daily_earnings,
        "total_earned": account.get("total_earned_usd", 0) if account else 0,
        "available_balance": account.get("available_balance_usd", 0) if account else 0,
        "tasks_completed": account.get("tasks_completed", 0) if account else 0,
        "transaction_count": len(transactions),
        "rt_session_count": len(rt_sessions)
    }

@earnings_router.get("/preferences/{user_id}")
async def get_withdrawal_preferences(user_id: str):
    """Get user's withdrawal preferences"""
    db = get_db()
    
    prefs = await db.withdrawal_preferences.find_one({"user_id": user_id}, {"_id": 0})
    
    if not prefs:
        # Return defaults
        return {
            "user_id": user_id,
            "default_method": "game_balance",
            "default_wallet": None,
            "wallet_percentage": 100,
            "auto_withdraw_threshold": None,
            "is_default": True
        }
    
    return {**prefs, "is_default": False}

@earnings_router.put("/preferences/{user_id}")
async def update_withdrawal_preferences(user_id: str, prefs: WithdrawalPreferences):
    """Update user's withdrawal preferences for permanent credit transfer settings"""
    db = get_db()
    
    # Verify user exists
    account = await db.earnings_accounts.find_one({"user_id": user_id})
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Validate wallet if provided
    if prefs.default_wallet and prefs.default_method == "crypto":
        if not prefs.default_wallet.startswith("0x") or len(prefs.default_wallet) != 42:
            raise HTTPException(status_code=400, detail="Invalid wallet address format")
    
    # Update or insert preferences
    pref_data = {
        "user_id": user_id,
        "default_method": prefs.default_method,
        "default_wallet": prefs.default_wallet,
        "wallet_percentage": min(100, max(0, prefs.wallet_percentage)),
        "auto_withdraw_threshold": prefs.auto_withdraw_threshold,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.withdrawal_preferences.update_one(
        {"user_id": user_id},
        {"$set": pref_data},
        upsert=True
    )
    
    return {"updated": True, "preferences": pref_data}

@earnings_router.post("/sync-rt-earnings")
async def sync_realtime_task_earnings(user_id: str, session_id: str, amount: float, tasks_count: int):
    """Sync earnings from real-time task sessions to main earnings account"""
    db = get_db()
    
    if amount <= 0:
        return {"synced": False, "reason": "No earnings to sync"}
    
    # Update earnings account
    await db.earnings_accounts.update_one(
        {"user_id": user_id},
        {
            "$inc": {
                "total_earned_usd": amount,
                "available_balance_usd": amount,
                "tasks_completed": tasks_count
            },
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        },
        upsert=True
    )
    
    # Record transaction
    await db.earnings_transactions.insert_one({
        "transaction_id": str(uuid.uuid4()),
        "user_id": user_id,
        "type": "rt_task_sync",
        "session_id": session_id,
        "amount_usd": amount,
        "tasks_count": tasks_count,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    # Check auto-withdraw threshold
    prefs = await db.withdrawal_preferences.find_one({"user_id": user_id})
    if prefs and prefs.get("auto_withdraw_threshold"):
        account = await db.earnings_accounts.find_one({"user_id": user_id})
        if account and account.get("available_balance_usd", 0) >= prefs["auto_withdraw_threshold"]:
            # Return flag to trigger auto-withdrawal
            return {
                "synced": True,
                "amount": amount,
                "tasks": tasks_count,
                "auto_withdraw_triggered": True,
                "threshold": prefs["auto_withdraw_threshold"]
            }
    
    return {"synced": True, "amount": amount, "tasks": tasks_count, "auto_withdraw_triggered": False}

@earnings_router.get("/task-history/{user_id}")
async def get_task_history(user_id: str, limit: int = 50):
    """Get recent completed task history"""
    db = get_db()
    
    # Get from earnings transactions
    transactions = await db.earnings_transactions.find({
        "user_id": user_id,
        "type": {"$in": ["task_completion", "rt_task_sync", "rt_task_completion"]}
    }).sort("timestamp", -1).to_list(limit)
    
    # Get from RT task completions
    rt_completions = await db.rt_task_completions.find({
        "worker_id": user_id
    }).sort("completed_at", -1).to_list(limit)
    
    # Merge and format
    history = []
    
    for tx in transactions:
        tx.pop("_id", None)
        history.append({
            "id": tx.get("transaction_id"),
            "type": tx.get("type"),
            "amount": tx.get("amount_usd", 0),
            "timestamp": tx.get("timestamp"),
            "task_id": tx.get("task_id"),
            "session_id": tx.get("session_id"),
            "source": "earnings"
        })
    
    for rt in rt_completions:
        rt.pop("_id", None)
        history.append({
            "id": rt.get("completion_id", str(uuid.uuid4())),
            "type": "rt_task",
            "amount": rt.get("payout", 0),
            "timestamp": rt.get("completed_at"),
            "task_id": rt.get("task_id"),
            "task_type": rt.get("task_type"),
            "source": "rt_tasks"
        })
    
    # Sort by timestamp
    history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    return {
        "user_id": user_id,
        "history": history[:limit],
        "total_count": len(history)
    }
