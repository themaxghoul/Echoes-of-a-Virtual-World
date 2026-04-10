# Stripe Payout Router - Real Money Withdrawals for VE$ earnings
# Uses emergentintegrations Stripe library

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime, timezone
from dotenv import load_dotenv
import os
import uuid
import logging

load_dotenv()

stripe_payout_router = APIRouter(prefix="/payments", tags=["payments"])

# Get Stripe API key from environment
STRIPE_API_KEY = os.environ.get('STRIPE_API_KEY')

# Payout packages (server-defined to prevent manipulation)
PAYOUT_PACKAGES = {
    "micro": {"min_amount": 1.00, "fee": 0.25, "description": "Micro payout ($1+)"},
    "small": {"min_amount": 5.00, "fee": 0.25, "description": "Small payout ($5+)"},
    "medium": {"min_amount": 10.00, "fee": 0.25, "description": "Medium payout ($10+)"},
    "large": {"min_amount": 25.00, "fee": 0.25, "description": "Large payout ($25+)"},
    "xlarge": {"min_amount": 50.00, "fee": 0.25, "description": "XL payout ($50+)"},
}

# Fixed withdrawal fee
WITHDRAWAL_FEE = 0.25

# ============ Models ============

class WithdrawalInitiate(BaseModel):
    user_id: str
    amount: float = Field(..., ge=1.0, description="Amount in USD to withdraw (minimum $1.00)")
    method: str = "stripe"  # stripe, crypto
    origin_url: str

class DepositInitiate(BaseModel):
    user_id: str
    amount: float = Field(..., ge=1.0)
    origin_url: str
    payment_methods: List[str] = Field(default=["card"])

class PaymentStatusCheck(BaseModel):
    session_id: str

# ============ Database Helper ============

def get_db():
    from server import db
    return db

# ============ Withdrawal Endpoints ============

@stripe_payout_router.get("/packages")
async def get_payout_packages():
    """Get available payout packages and fee structure"""
    return {
        "packages": PAYOUT_PACKAGES,
        "withdrawal_fee": WITHDRAWAL_FEE,
        "minimum_withdrawal": 1.00,
        "supported_methods": ["stripe", "crypto"],
        "processing_time": "1-3 business days"
    }

@stripe_payout_router.post("/withdraw/initiate")
async def initiate_withdrawal(request: WithdrawalInitiate):
    """Initiate a withdrawal from VE$ balance to real USD"""
    db = get_db()
    
    # Check user earnings account
    account = await db.earnings_accounts.find_one({"user_id": request.user_id})
    if not account:
        raise HTTPException(status_code=404, detail="Earnings account not found")
    
    available_balance = account.get("available_balance_usd", 0)
    total_deduction = request.amount + WITHDRAWAL_FEE
    
    if total_deduction > available_balance:
        raise HTTPException(
            status_code=400, 
            detail=f"Insufficient balance. Need ${total_deduction:.2f} (${request.amount:.2f} + ${WITHDRAWAL_FEE} fee). Available: ${available_balance:.2f}"
        )
    
    if request.amount < 1.00:
        raise HTTPException(status_code=400, detail="Minimum withdrawal is $1.00")
    
    # Check KYC for large withdrawals
    if request.amount > 100 and not account.get("kyc_verified"):
        raise HTTPException(status_code=403, detail="KYC verification required for withdrawals over $100")
    
    # Create withdrawal record
    withdrawal_id = str(uuid.uuid4())
    
    withdrawal_record = {
        "withdrawal_id": withdrawal_id,
        "user_id": request.user_id,
        "amount_usd": request.amount,
        "fee_usd": WITHDRAWAL_FEE,
        "total_deducted": total_deduction,
        "method": request.method,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "origin_url": request.origin_url
    }
    
    await db.withdrawal_requests.insert_one(withdrawal_record)
    
    # Deduct from balance immediately (pending state)
    await db.earnings_accounts.update_one(
        {"user_id": request.user_id},
        {
            "$inc": {
                "available_balance_usd": -total_deduction,
                "pending_balance_usd": request.amount
            },
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    # Record fee transaction
    await db.earnings_transactions.insert_one({
        "transaction_id": str(uuid.uuid4()),
        "user_id": "apexforge_operations",
        "type": "withdrawal_fee",
        "source_user": request.user_id,
        "amount_usd": WITHDRAWAL_FEE,
        "withdrawal_id": withdrawal_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "withdrawal_id": withdrawal_id,
        "amount_requested": request.amount,
        "fee": WITHDRAWAL_FEE,
        "total_deducted": total_deduction,
        "status": "pending",
        "estimated_processing": "1-3 business days",
        "message": f"Withdrawal of ${request.amount:.2f} initiated successfully"
    }

@stripe_payout_router.get("/withdraw/status/{withdrawal_id}")
async def get_withdrawal_status(withdrawal_id: str, user_id: str):
    """Check status of a withdrawal request"""
    db = get_db()
    
    withdrawal = await db.withdrawal_requests.find_one(
        {"withdrawal_id": withdrawal_id, "user_id": user_id},
        {"_id": 0}
    )
    
    if not withdrawal:
        raise HTTPException(status_code=404, detail="Withdrawal not found")
    
    return withdrawal

@stripe_payout_router.get("/withdraw/history/{user_id}")
async def get_withdrawal_history(user_id: str, limit: int = 20):
    """Get user's withdrawal history"""
    db = get_db()
    
    withdrawals = await db.withdrawal_requests.find(
        {"user_id": user_id},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {"withdrawals": withdrawals, "count": len(withdrawals)}

# ============ Deposit Endpoints (Buy VE$) ============

@stripe_payout_router.post("/deposit/checkout")
async def create_deposit_checkout(request: DepositInitiate, http_request: Request):
    """Create Stripe checkout session to deposit/buy VE$"""
    if not STRIPE_API_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    db = get_db()
    
    try:
        from emergentintegrations.payments.stripe.checkout import (
            StripeCheckout, CheckoutSessionRequest
        )
    except ImportError:
        raise HTTPException(status_code=500, detail="Stripe integration not available")
    
    # Build URLs from provided origin
    success_url = f"{request.origin_url}/earnings?session_id={{CHECKOUT_SESSION_ID}}&status=success"
    cancel_url = f"{request.origin_url}/earnings?status=cancelled"
    
    # Initialize Stripe
    host_url = str(http_request.base_url).rstrip('/')
    webhook_url = f"{host_url}/api/payments/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    
    # Create checkout session
    checkout_request = CheckoutSessionRequest(
        amount=float(request.amount),
        currency="usd",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "user_id": request.user_id,
            "type": "ve_deposit",
            "amount_ve": str(request.amount)
        },
        payment_methods=request.payment_methods
    )
    
    try:
        session = await stripe_checkout.create_checkout_session(checkout_request)
    except Exception as e:
        logging.error(f"Stripe checkout error: {e}")
        raise HTTPException(status_code=500, detail=f"Payment service error: {str(e)}")
    
    # Record pending transaction
    transaction_record = {
        "transaction_id": str(uuid.uuid4()),
        "session_id": session.session_id,
        "user_id": request.user_id,
        "type": "deposit",
        "amount_usd": request.amount,
        "amount_ve": request.amount,
        "currency": "usd",
        "payment_status": "pending",
        "status": "initiated",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.payment_transactions.insert_one(transaction_record)
    
    return {
        "checkout_url": session.url,
        "session_id": session.session_id,
        "amount": request.amount,
        "currency": "usd"
    }

@stripe_payout_router.get("/deposit/status/{session_id}")
async def check_deposit_status(session_id: str):
    """Check status of a deposit/checkout session"""
    if not STRIPE_API_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    db = get_db()
    
    # Check if already processed
    existing = await db.payment_transactions.find_one({"session_id": session_id})
    if existing and existing.get("payment_status") == "paid":
        return {
            "status": "complete",
            "payment_status": "paid",
            "amount_ve": existing.get("amount_ve"),
            "message": "VE$ already credited to your account"
        }
    
    try:
        from emergentintegrations.payments.stripe.checkout import StripeCheckout
        stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url="")
        
        checkout_status = await stripe_checkout.get_checkout_status(session_id)
    except Exception as e:
        logging.error(f"Stripe status check error: {e}")
        raise HTTPException(status_code=500, detail=f"Payment service error: {str(e)}")
    
    # Process successful payment
    if checkout_status.payment_status == "paid" and existing:
        user_id = existing.get("user_id")
        amount_ve = existing.get("amount_ve", 0)
        
        # Prevent double-processing
        if existing.get("payment_status") != "paid":
            # Credit VE$ to user account
            await db.earnings_accounts.update_one(
                {"user_id": user_id},
                {
                    "$inc": {"available_balance_usd": amount_ve},
                    "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
                },
                upsert=True
            )
            
            # Update transaction record
            await db.payment_transactions.update_one(
                {"session_id": session_id},
                {"$set": {
                    "payment_status": "paid",
                    "status": "complete",
                    "completed_at": datetime.now(timezone.utc).isoformat()
                }}
            )
            
            # Record earnings transaction
            await db.earnings_transactions.insert_one({
                "transaction_id": str(uuid.uuid4()),
                "user_id": user_id,
                "type": "deposit",
                "amount_usd": amount_ve,
                "amount_ve": amount_ve,
                "stripe_session": session_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
    
    # Update failed/expired status
    elif checkout_status.status in ["expired", "failed"]:
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": {
                "payment_status": checkout_status.payment_status,
                "status": checkout_status.status,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
    
    return {
        "status": checkout_status.status,
        "payment_status": checkout_status.payment_status,
        "amount_total": checkout_status.amount_total,
        "currency": checkout_status.currency
    }

@stripe_payout_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events"""
    if not STRIPE_API_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    db = get_db()
    
    try:
        from emergentintegrations.payments.stripe.checkout import StripeCheckout
        
        body = await request.body()
        signature = request.headers.get("Stripe-Signature")
        
        stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url="")
        webhook_response = await stripe_checkout.handle_webhook(body, signature)
        
        # Process webhook event
        if webhook_response.payment_status == "paid":
            session_id = webhook_response.session_id
            
            # Find the transaction
            transaction = await db.payment_transactions.find_one({"session_id": session_id})
            
            if transaction and transaction.get("payment_status") != "paid":
                user_id = transaction.get("user_id")
                amount_ve = transaction.get("amount_ve", 0)
                
                # Credit VE$ to user
                await db.earnings_accounts.update_one(
                    {"user_id": user_id},
                    {
                        "$inc": {"available_balance_usd": amount_ve},
                        "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
                    },
                    upsert=True
                )
                
                # Update transaction
                await db.payment_transactions.update_one(
                    {"session_id": session_id},
                    {"$set": {
                        "payment_status": "paid",
                        "status": "complete",
                        "completed_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
        
        return {"status": "received", "event_type": webhook_response.event_type}
        
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return {"status": "error", "detail": str(e)}

# ============ Balance & Transaction Endpoints ============

@stripe_payout_router.get("/balance/{user_id}")
async def get_user_balance(user_id: str):
    """Get user's VE$ balance and transaction summary"""
    db = get_db()
    
    account = await db.earnings_accounts.find_one({"user_id": user_id}, {"_id": 0})
    
    if not account:
        # Create default account
        account = {
            "user_id": user_id,
            "total_earned_usd": 0.0,
            "available_balance_usd": 0.0,
            "pending_balance_usd": 0.0,
            "total_withdrawn_usd": 0.0,
            "tasks_completed": 0,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.earnings_accounts.insert_one(account)
    
    # Get recent transactions
    recent_txs = await db.earnings_transactions.find(
        {"user_id": user_id},
        {"_id": 0}
    ).sort("timestamp", -1).limit(5).to_list(5)
    
    return {
        "balance": {
            "available_ve": account.get("available_balance_usd", 0),
            "pending_ve": account.get("pending_balance_usd", 0),
            "total_earned_ve": account.get("total_earned_usd", 0),
            "total_withdrawn_ve": account.get("total_withdrawn_usd", 0)
        },
        "usd_equivalent": {
            "available": account.get("available_balance_usd", 0),
            "pending": account.get("pending_balance_usd", 0)
        },
        "exchange_rate": "1 VE$ = $1.00 USD",
        "tasks_completed": account.get("tasks_completed", 0),
        "recent_transactions": recent_txs
    }

@stripe_payout_router.get("/transactions/{user_id}")
async def get_user_transactions(user_id: str, limit: int = 50, offset: int = 0):
    """Get user's full transaction history"""
    db = get_db()
    
    transactions = await db.earnings_transactions.find(
        {"user_id": user_id},
        {"_id": 0}
    ).sort("timestamp", -1).skip(offset).limit(limit).to_list(limit)
    
    total = await db.earnings_transactions.count_documents({"user_id": user_id})
    
    return {
        "transactions": transactions,
        "total": total,
        "limit": limit,
        "offset": offset
    }
