# Store Router - In-App Purchases with Stripe Integration
# Currency conversion (USD→VE$), preset amounts, compute subscriptions

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime, timezone
import uuid
import os
import logging

store_router = APIRouter(prefix="/store", tags=["store"])
logger = logging.getLogger(__name__)

# Get Stripe key from environment
STRIPE_API_KEY = os.environ.get('STRIPE_API_KEY')

# ============ Currency Conversion ============
# 1 USD = 1 VE$ (1:1 conversion)
EXCHANGE_RATE = 1.0

# Preset purchase amounts
PRESET_AMOUNTS = [
    {"id": "starter", "amount_usd": 5.00, "ve_received": 5.00, "bonus": 0, "label": "Starter Pack", "popular": False},
    {"id": "adventurer", "amount_usd": 10.00, "ve_received": 10.50, "bonus": 5, "label": "Adventurer Pack", "popular": False},
    {"id": "explorer", "amount_usd": 25.00, "ve_received": 27.50, "bonus": 10, "label": "Explorer Pack", "popular": True},
    {"id": "champion", "amount_usd": 50.00, "ve_received": 57.50, "bonus": 15, "label": "Champion Pack", "popular": False},
    {"id": "legend", "amount_usd": 100.00, "ve_received": 120.00, "bonus": 20, "label": "Legend Pack", "popular": False},
]

# ============ Compute Power Subscriptions ============
# Levels increase exponentially - each tier provides exponentially more compute
COMPUTE_SUBSCRIPTIONS = {
    "spark": {
        "name": "Spark",
        "tier": 1,
        "monthly_usd": 4.99,
        "compute_units": 100,
        "ai_program_slots": 1,
        "description": "Perfect for getting started with AI partners",
        "multiplier": 1.0
    },
    "flame": {
        "name": "Flame",
        "tier": 2,
        "monthly_usd": 9.99,
        "compute_units": 250,
        "ai_program_slots": 2,
        "description": "Run multiple AI programs simultaneously",
        "multiplier": 2.5
    },
    "inferno": {
        "name": "Inferno",
        "tier": 3,
        "monthly_usd": 19.99,
        "compute_units": 600,
        "ai_program_slots": 4,
        "description": "Serious AI automation power",
        "multiplier": 6.0
    },
    "nova": {
        "name": "Nova",
        "tier": 4,
        "monthly_usd": 39.99,
        "compute_units": 1500,
        "ai_program_slots": 8,
        "description": "Professional-grade compute capacity",
        "multiplier": 15.0
    },
    "supernova": {
        "name": "Supernova",
        "tier": 5,
        "monthly_usd": 79.99,
        "compute_units": 4000,
        "ai_program_slots": 16,
        "description": "Enterprise-level AI operations",
        "multiplier": 40.0
    },
    "cosmic": {
        "name": "Cosmic",
        "tier": 6,
        "monthly_usd": 149.99,
        "compute_units": 12000,
        "ai_program_slots": 32,
        "description": "Unlimited potential - cosmic scale compute",
        "multiplier": 120.0
    }
}

# ============ Civilization Structures ============
# Essential buildings for starting and maintaining civilization
CIVILIZATION_STRUCTURES = {
    # Essentials - Starting Structures
    "campfire": {
        "name": "Campfire",
        "category": "essential",
        "description": "A warm gathering spot. The first step to civilization.",
        "cost_ve": 5,
        "cost_usd": 5,
        "defense": 0,
        "capacity": 4,
        "production": {"warmth": 1},
        "icon": "flame"
    },
    "shelter": {
        "name": "Basic Shelter",
        "category": "essential",
        "description": "Protection from the elements. A roof over your head.",
        "cost_ve": 25,
        "cost_usd": 25,
        "defense": 5,
        "capacity": 2,
        "production": {},
        "icon": "home"
    },
    "well": {
        "name": "Village Well",
        "category": "essential",
        "description": "Clean water for your people. Essential for survival.",
        "cost_ve": 50,
        "cost_usd": 50,
        "defense": 0,
        "capacity": 0,
        "production": {"water": 10},
        "icon": "droplet"
    },
    
    # Defense - Gates and Walls
    "wooden_palisade": {
        "name": "Wooden Palisade",
        "category": "defense",
        "description": "Simple wooden barrier. Keeps wild beasts at bay.",
        "cost_ve": 30,
        "cost_usd": 30,
        "defense": 10,
        "capacity": 0,
        "production": {},
        "icon": "fence"
    },
    "wooden_gate": {
        "name": "Wooden Gate",
        "category": "defense",
        "description": "Entry point through palisades. Guards needed.",
        "cost_ve": 75,
        "cost_usd": 75,
        "defense": 15,
        "capacity": 2,
        "production": {},
        "icon": "door-open"
    },
    "stone_wall": {
        "name": "Stone Wall",
        "category": "defense",
        "description": "Sturdy fortification. Demons think twice before approaching.",
        "cost_ve": 150,
        "cost_usd": 150,
        "defense": 40,
        "capacity": 0,
        "production": {},
        "icon": "brick"
    },
    "iron_gate": {
        "name": "Iron Gate",
        "category": "defense",
        "description": "Formidable entrance. Only the worthy may pass.",
        "cost_ve": 300,
        "cost_usd": 300,
        "defense": 60,
        "capacity": 4,
        "production": {},
        "icon": "shield"
    },
    "watchtower": {
        "name": "Watchtower",
        "category": "defense",
        "description": "Eyes on the horizon. Spot threats before they arrive.",
        "cost_ve": 200,
        "cost_usd": 200,
        "defense": 25,
        "capacity": 2,
        "production": {"vision": 5},
        "icon": "eye"
    },
    "guard_post": {
        "name": "Guard Post",
        "category": "defense",
        "description": "Station for guards at gate entrances. Defense, not patrol.",
        "cost_ve": 100,
        "cost_usd": 100,
        "defense": 20,
        "capacity": 3,
        "production": {},
        "icon": "shield-check"
    },
    
    # Production
    "farm": {
        "name": "Small Farm",
        "category": "production",
        "description": "Grow food for your people. Self-sufficiency begins here.",
        "cost_ve": 100,
        "cost_usd": 100,
        "defense": 0,
        "capacity": 2,
        "production": {"food": 5},
        "icon": "wheat"
    },
    "workshop": {
        "name": "Craftsman Workshop",
        "category": "production",
        "description": "Where tools and goods are made. Craft your future.",
        "cost_ve": 200,
        "cost_usd": 200,
        "defense": 0,
        "capacity": 4,
        "production": {"tools": 2},
        "icon": "hammer"
    },
    "forge": {
        "name": "Iron Forge",
        "category": "production",
        "description": "Transform ore into weapons and armor. Fire and steel.",
        "cost_ve": 350,
        "cost_usd": 350,
        "defense": 0,
        "capacity": 3,
        "production": {"iron_goods": 2},
        "icon": "anvil"
    },
    
    # Community
    "gathering_hall": {
        "name": "Gathering Hall",
        "category": "community",
        "description": "Where the village meets. Decisions are made here.",
        "cost_ve": 250,
        "cost_usd": 250,
        "defense": 5,
        "capacity": 20,
        "production": {"morale": 2},
        "icon": "users"
    },
    "tavern": {
        "name": "Tavern",
        "category": "community",
        "description": "Rest, stories, and warm food. The heart of any settlement.",
        "cost_ve": 175,
        "cost_usd": 175,
        "defense": 0,
        "capacity": 15,
        "production": {"morale": 3, "gold": 1},
        "icon": "beer"
    },
    "temple": {
        "name": "Small Temple",
        "category": "community",
        "description": "A place of worship and blessing. Protection from darkness.",
        "cost_ve": 400,
        "cost_usd": 400,
        "defense": 10,
        "capacity": 10,
        "production": {"blessing": 1},
        "icon": "church"
    }
}

# ============ Models ============

class CurrencyConversionRequest(BaseModel):
    user_id: str
    amount_usd: float = Field(..., ge=1.0, description="Amount in USD to convert")
    origin_url: str

class PresetPurchaseRequest(BaseModel):
    user_id: str
    preset_id: str
    origin_url: str

class ComputeSubscriptionRequest(BaseModel):
    user_id: str
    subscription_tier: str
    origin_url: str

class StructurePurchaseRequest(BaseModel):
    user_id: str
    structure_id: str
    payment_method: str = "ve"  # "ve" or "usd"
    origin_url: Optional[str] = None

# ============ Database Helper ============

def get_db():
    from server import db
    return db

# ============ Stripe Helper ============

async def create_stripe_checkout(amount_usd: float, user_id: str, origin_url: str, metadata: Dict, description: str = "AI Village Purchase"):
    """Create a Stripe checkout session"""
    if not STRIPE_API_KEY:
        raise HTTPException(status_code=500, detail="Payment system not configured")
    
    try:
        from emergentintegrations.payments.stripe.checkout import (
            StripeCheckout, CheckoutSessionRequest
        )
    except ImportError:
        raise HTTPException(status_code=500, detail="Stripe integration not available")
    
    success_url = f"{origin_url}/earnings?session_id={{CHECKOUT_SESSION_ID}}&status=success&type=purchase"
    cancel_url = f"{origin_url}/store?status=cancelled"
    
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url="")
    
    checkout_request = CheckoutSessionRequest(
        amount=float(amount_usd),
        currency="usd",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "user_id": user_id,
            "type": "store_purchase",
            "description": description,
            **metadata
        },
        payment_methods=["card"]
    )
    
    return await stripe_checkout.create_checkout_session(checkout_request)

# ============ Endpoints ============

@store_router.get("/status")
async def get_store_status():
    """Check if store and purchases are enabled"""
    stripe_configured = bool(STRIPE_API_KEY and STRIPE_API_KEY.startswith('sk_'))
    return {
        "enabled": True,
        "stripe_configured": stripe_configured,
        "exchange_rate": EXCHANGE_RATE,
        "currency_symbol": "VE$",
        "message": None if stripe_configured else "USD purchases temporarily unavailable"
    }

@store_router.get("/presets")
async def get_preset_amounts():
    """Get available preset purchase amounts"""
    return {
        "presets": PRESET_AMOUNTS,
        "exchange_rate": EXCHANGE_RATE,
        "bonus_info": "Higher purchases unlock bonus VE$!"
    }

@store_router.get("/compute-subscriptions")
async def get_compute_subscriptions():
    """Get compute power subscription tiers"""
    return {
        "subscriptions": COMPUTE_SUBSCRIPTIONS,
        "scaling_info": "Compute power scales exponentially with each tier"
    }

@store_router.get("/structures")
async def get_civilization_structures():
    """Get available civilization structures for purchase"""
    # Group by category
    by_category = {}
    for struct_id, struct in CIVILIZATION_STRUCTURES.items():
        cat = struct["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append({"id": struct_id, **struct})
    
    return {
        "structures": CIVILIZATION_STRUCTURES,
        "by_category": by_category,
        "categories": ["essential", "defense", "production", "community"],
        "philosophy": "At small civilization sizes, guards defend gates rather than patrol streets. Build walls first, worry about police later."
    }

@store_router.post("/convert-currency")
async def convert_currency(request: CurrencyConversionRequest):
    """Convert USD to VE$ (creates Stripe checkout)"""
    db = get_db()
    
    if request.amount_usd < 1:
        raise HTTPException(status_code=400, detail="Minimum purchase is $1.00")
    
    ve_amount = request.amount_usd * EXCHANGE_RATE
    
    try:
        session = await create_stripe_checkout(
            amount_usd=request.amount_usd,
            user_id=request.user_id,
            origin_url=request.origin_url,
            metadata={
                "purchase_type": "currency_conversion",
                "ve_amount": str(ve_amount)
            },
            description=f"VE${ve_amount:.2f} Currency Purchase"
        )
        
        # Record pending transaction
        await db.store_transactions.insert_one({
            "transaction_id": str(uuid.uuid4()),
            "session_id": session.session_id,
            "user_id": request.user_id,
            "type": "currency_conversion",
            "amount_usd": request.amount_usd,
            "ve_amount": ve_amount,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        return {
            "checkout_url": session.url,
            "session_id": session.session_id,
            "amount_usd": request.amount_usd,
            "ve_received": ve_amount,
            "exchange_rate": EXCHANGE_RATE
        }
    except Exception as e:
        logger.error(f"Stripe checkout error: {e}")
        raise HTTPException(status_code=500, detail=f"Payment service error: {str(e)}")

@store_router.post("/purchase-preset")
async def purchase_preset(request: PresetPurchaseRequest):
    """Purchase a preset VE$ package"""
    db = get_db()
    
    preset = next((p for p in PRESET_AMOUNTS if p["id"] == request.preset_id), None)
    if not preset:
        raise HTTPException(status_code=400, detail=f"Unknown preset: {request.preset_id}")
    
    try:
        session = await create_stripe_checkout(
            amount_usd=preset["amount_usd"],
            user_id=request.user_id,
            origin_url=request.origin_url,
            metadata={
                "purchase_type": "preset",
                "preset_id": request.preset_id,
                "ve_amount": str(preset["ve_received"]),
                "bonus_percent": str(preset["bonus"])
            },
            description=f"{preset['label']} - VE${preset['ve_received']:.2f}"
        )
        
        await db.store_transactions.insert_one({
            "transaction_id": str(uuid.uuid4()),
            "session_id": session.session_id,
            "user_id": request.user_id,
            "type": "preset_purchase",
            "preset_id": request.preset_id,
            "amount_usd": preset["amount_usd"],
            "ve_amount": preset["ve_received"],
            "bonus_percent": preset["bonus"],
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        return {
            "checkout_url": session.url,
            "session_id": session.session_id,
            "preset": preset
        }
    except Exception as e:
        logger.error(f"Preset purchase error: {e}")
        raise HTTPException(status_code=500, detail=f"Payment service error: {str(e)}")

@store_router.post("/subscribe-compute")
async def subscribe_compute(request: ComputeSubscriptionRequest):
    """Subscribe to a compute power tier"""
    db = get_db()
    
    if request.subscription_tier not in COMPUTE_SUBSCRIPTIONS:
        raise HTTPException(status_code=400, detail=f"Unknown subscription tier: {request.subscription_tier}")
    
    sub = COMPUTE_SUBSCRIPTIONS[request.subscription_tier]
    
    try:
        session = await create_stripe_checkout(
            amount_usd=sub["monthly_usd"],
            user_id=request.user_id,
            origin_url=request.origin_url,
            metadata={
                "purchase_type": "compute_subscription",
                "subscription_tier": request.subscription_tier,
                "compute_units": str(sub["compute_units"]),
                "ai_slots": str(sub["ai_program_slots"])
            },
            description=f"{sub['name']} Compute - {sub['compute_units']} units/month"
        )
        
        await db.store_transactions.insert_one({
            "transaction_id": str(uuid.uuid4()),
            "session_id": session.session_id,
            "user_id": request.user_id,
            "type": "compute_subscription",
            "subscription_tier": request.subscription_tier,
            "amount_usd": sub["monthly_usd"],
            "compute_units": sub["compute_units"],
            "ai_slots": sub["ai_program_slots"],
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        return {
            "checkout_url": session.url,
            "session_id": session.session_id,
            "subscription": sub
        }
    except Exception as e:
        logger.error(f"Compute subscription error: {e}")
        raise HTTPException(status_code=500, detail=f"Payment service error: {str(e)}")

@store_router.post("/purchase-structure")
async def purchase_structure(request: StructurePurchaseRequest):
    """Purchase a civilization structure with VE$ or USD"""
    db = get_db()
    
    if request.structure_id not in CIVILIZATION_STRUCTURES:
        raise HTTPException(status_code=400, detail=f"Unknown structure: {request.structure_id}")
    
    structure = CIVILIZATION_STRUCTURES[request.structure_id]
    
    if request.payment_method == "ve":
        # Pay with VE$
        account = await db.earnings_accounts.find_one({"user_id": request.user_id})
        balance = account.get("available_balance_usd", 0) if account else 0
        
        if balance < structure["cost_ve"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Insufficient VE$ balance. Need {structure['cost_ve']}, have {balance:.2f}"
            )
        
        # Deduct VE$
        await db.earnings_accounts.update_one(
            {"user_id": request.user_id},
            {"$inc": {"available_balance_usd": -structure["cost_ve"]}}
        )
        
        # Grant structure
        purchase_id = str(uuid.uuid4())
        await db.owned_structures.insert_one({
            "purchase_id": purchase_id,
            "user_id": request.user_id,
            "structure_id": request.structure_id,
            "structure_name": structure["name"],
            "paid_with": "ve",
            "amount_paid": structure["cost_ve"],
            "placed": False,
            "purchased_at": datetime.now(timezone.utc).isoformat()
        })
        
        return {
            "success": True,
            "purchase_id": purchase_id,
            "structure": structure,
            "message": f"You've acquired {structure['name']}! Place it in your settlement."
        }
    
    else:
        # Pay with USD via Stripe
        if not request.origin_url:
            raise HTTPException(status_code=400, detail="origin_url required for USD purchases")
        
        try:
            session = await create_stripe_checkout(
                amount_usd=structure["cost_usd"],
                user_id=request.user_id,
                origin_url=request.origin_url,
                metadata={
                    "purchase_type": "structure",
                    "structure_id": request.structure_id
                },
                description=f"Structure: {structure['name']}"
            )
            
            await db.store_transactions.insert_one({
                "transaction_id": str(uuid.uuid4()),
                "session_id": session.session_id,
                "user_id": request.user_id,
                "type": "structure_purchase",
                "structure_id": request.structure_id,
                "amount_usd": structure["cost_usd"],
                "status": "pending",
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            
            return {
                "checkout_url": session.url,
                "session_id": session.session_id,
                "structure": structure
            }
        except Exception as e:
            logger.error(f"Structure purchase error: {e}")
            raise HTTPException(status_code=500, detail=f"Payment service error: {str(e)}")

@store_router.get("/my-structures/{user_id}")
async def get_owned_structures(user_id: str):
    """Get all structures owned by user"""
    db = get_db()
    
    structures = await db.owned_structures.find(
        {"user_id": user_id},
        {"_id": 0}
    ).to_list(100)
    
    # Group by placed/unplaced
    placed = [s for s in structures if s.get("placed")]
    unplaced = [s for s in structures if not s.get("placed")]
    
    return {
        "owned": structures,
        "placed": placed,
        "unplaced": unplaced,
        "total_count": len(structures)
    }

@store_router.get("/transaction/{session_id}")
async def check_transaction(session_id: str):
    """Check status of a store transaction"""
    db = get_db()
    
    transaction = await db.store_transactions.find_one(
        {"session_id": session_id},
        {"_id": 0}
    )
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # If already processed
    if transaction.get("status") == "completed":
        return {
            "status": "completed",
            "transaction": transaction
        }
    
    # Check with Stripe
    if STRIPE_API_KEY:
        try:
            from emergentintegrations.payments.stripe.checkout import StripeCheckout
            stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url="")
            checkout_status = await stripe_checkout.get_checkout_status(session_id)
            
            if checkout_status.payment_status == "paid":
                # Process the purchase
                user_id = transaction.get("user_id")
                purchase_type = transaction.get("type")
                
                if purchase_type == "currency_conversion" or purchase_type == "preset_purchase":
                    # Credit VE$
                    ve_amount = transaction.get("ve_amount", 0)
                    await db.earnings_accounts.update_one(
                        {"user_id": user_id},
                        {"$inc": {"available_balance_usd": ve_amount}},
                        upsert=True
                    )
                    
                elif purchase_type == "compute_subscription":
                    # Add compute subscription
                    await db.user_subscriptions.update_one(
                        {"user_id": user_id},
                        {
                            "$set": {
                                "compute_tier": transaction.get("subscription_tier"),
                                "compute_units": transaction.get("compute_units"),
                                "ai_slots": transaction.get("ai_slots"),
                                "renewed_at": datetime.now(timezone.utc).isoformat(),
                                "expires_at": None  # Monthly renewal
                            }
                        },
                        upsert=True
                    )
                    
                elif purchase_type == "structure_purchase":
                    # Grant structure
                    await db.owned_structures.insert_one({
                        "purchase_id": str(uuid.uuid4()),
                        "user_id": user_id,
                        "structure_id": transaction.get("structure_id"),
                        "structure_name": CIVILIZATION_STRUCTURES.get(transaction.get("structure_id"), {}).get("name", "Unknown"),
                        "paid_with": "usd",
                        "amount_paid": transaction.get("amount_usd"),
                        "placed": False,
                        "purchased_at": datetime.now(timezone.utc).isoformat()
                    })
                
                # Mark transaction complete
                await db.store_transactions.update_one(
                    {"session_id": session_id},
                    {"$set": {
                        "status": "completed",
                        "completed_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
                
                return {
                    "status": "completed",
                    "message": "Purchase successful!",
                    "transaction": transaction
                }
            
            return {
                "status": checkout_status.status,
                "payment_status": checkout_status.payment_status
            }
            
        except Exception as e:
            logger.error(f"Status check error: {e}")
            return {"status": "pending", "error": str(e)}
    
    return {"status": transaction.get("status", "pending")}

@store_router.get("/user/{user_id}/subscription")
async def get_user_subscription(user_id: str):
    """Get user's current compute subscription"""
    db = get_db()
    
    subscription = await db.user_subscriptions.find_one(
        {"user_id": user_id},
        {"_id": 0}
    )
    
    if not subscription:
        return {
            "active": False,
            "tier": None,
            "compute_units": 0,
            "ai_slots": 0
        }
    
    tier_info = COMPUTE_SUBSCRIPTIONS.get(subscription.get("compute_tier"), {})
    
    return {
        "active": True,
        "tier": subscription.get("compute_tier"),
        "tier_name": tier_info.get("name", "Unknown"),
        "compute_units": subscription.get("compute_units", 0),
        "ai_slots": subscription.get("ai_slots", 0),
        "renewed_at": subscription.get("renewed_at"),
        "multiplier": tier_info.get("multiplier", 1.0)
    }
