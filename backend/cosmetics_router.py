# VE$ Boutique - Cosmetics, Boosts & Avatar Spotlight
# Gives VE$ real spending appeal: frames, name colors, titles, boosts, palette packs

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, timedelta

cosmetics_router = APIRouter(prefix="/cosmetics", tags=["cosmetics"])

def get_db():
    from server import db
    return db

# ============ Catalog ============

CATALOG = {
    # Avatar Frames (rendered around pixel avatar everywhere)
    "frame_bronze": {"category": "frame", "name": "Bronze Ring", "price": 75, "rarity": "common", "description": "A sturdy bronze ring around your avatar"},
    "frame_silver": {"category": "frame", "name": "Silver Ring", "price": 150, "rarity": "uncommon", "description": "Polished silver ring"},
    "frame_neon": {"category": "frame", "name": "Neon Glow", "price": 300, "rarity": "rare", "description": "Cyan neon glow that pulses with energy"},
    "frame_gold": {"category": "frame", "name": "Gilded Aurum", "price": 600, "rarity": "epic", "description": "Animated golden shimmer"},
    "frame_ember": {"category": "frame", "name": "Emberforge", "price": 900, "rarity": "epic", "description": "Burning ember aura"},
    "frame_prismatic": {"category": "frame", "name": "Prismatic Legend", "price": 1500, "rarity": "legendary", "description": "Animated rainbow border - the ultimate flex"},
    # Premium Name Colors (chat + profile)
    "color_neon_pink": {"category": "name_color", "name": "Neon Pink", "price": 100, "rarity": "rare", "hex": "#FF10F0", "color_key": "neon_pink"},
    "color_electric_cyan": {"category": "name_color", "name": "Electric Cyan", "price": 100, "rarity": "rare", "hex": "#00FFF7", "color_key": "electric_cyan"},
    "color_toxic_green": {"category": "name_color", "name": "Toxic Green", "price": 100, "rarity": "rare", "hex": "#39FF14", "color_key": "toxic_green"},
    "color_blood_orange": {"category": "name_color", "name": "Blood Orange", "price": 100, "rarity": "rare", "hex": "#FF3C00", "color_key": "blood_orange"},
    "color_void_purple": {"category": "name_color", "name": "Void Purple", "price": 100, "rarity": "rare", "hex": "#7B2FFF", "color_key": "void_purple"},
    "color_white_gold": {"category": "name_color", "name": "White Gold", "price": 200, "rarity": "epic", "hex": "#FFF3C2", "color_key": "white_gold"},
    # Titles (shown next to name)
    "title_pioneer": {"category": "title", "name": "Pioneer", "price": 50, "rarity": "common", "title_text": "Pioneer"},
    "title_forgemaster": {"category": "title", "name": "Forgemaster", "price": 200, "rarity": "uncommon", "title_text": "Forgemaster"},
    "title_tycoon": {"category": "title", "name": "Tycoon", "price": 400, "rarity": "rare", "title_text": "Tycoon"},
    "title_echo_lord": {"category": "title", "name": "Echo Lord", "price": 800, "rarity": "epic", "title_text": "Echo Lord"},
    "title_transcendent": {"category": "title", "name": "Transcendent", "price": 2000, "rarity": "legendary", "title_text": "Transcendent"},
    # Boosts (consumable, timed)
    "boost_task_reward": {"category": "boost", "name": "Forge Surge", "price": 250, "rarity": "rare", "boost_type": "task_reward", "multiplier": 1.5, "duration_hours": 24, "description": "+50% VE$ on all factory task rewards for 24h"},
    "boost_training_xp": {"category": "boost", "name": "Mind Amplifier", "price": 200, "rarity": "rare", "boost_type": "training_xp", "multiplier": 2.0, "duration_hours": 24, "description": "2x XP on all AI training for 24h"},
    # Avatar Palette Packs (unlock colors in Avatar Studio)
    "palette_neon": {"category": "palette", "name": "Neon Pack", "price": 120, "rarity": "rare", "description": "8 electric neon colors"},
    "palette_metallic": {"category": "palette", "name": "Metallic Pack", "price": 180, "rarity": "rare", "description": "8 gold, silver & chrome tones"},
    "palette_pastel": {"category": "palette", "name": "Pastel Pack", "price": 100, "rarity": "uncommon", "description": "8 soft pastel shades"},
    "palette_cosmic": {"category": "palette", "name": "Cosmic Pack", "price": 250, "rarity": "epic", "description": "8 deep-space nebula colors"},
    # Spotlight (consumable)
    "spotlight_24h": {"category": "spotlight", "name": "Avatar Spotlight", "price": 100, "rarity": "rare", "duration_hours": 24, "description": "Feature your avatar in the public Hall of Echoes for 24h"},
}

CONSUMABLE_CATEGORIES = {"boost", "spotlight"}

# ============ Models ============

class PurchaseRequest(BaseModel):
    user_id: str
    item_id: str

class EquipRequest(BaseModel):
    user_id: str
    item_id: str  # "none" to unequip a frame

# ============ Helpers ============

async def get_boost_multiplier(db, user_id: str, boost_type: str) -> float:
    """Return active boost multiplier for a user (1.0 if none). Importable by other routers."""
    now = datetime.now(timezone.utc).isoformat()
    boost = await db.active_boosts.find_one({
        "user_id": user_id, "boost_type": boost_type, "expires_at": {"$gt": now}
    })
    return boost.get("multiplier", 1.0) if boost else 1.0

async def _get_wallet_balance(db, user_id: str) -> float:
    wallet = await db.entity_wallets.find_one({"entity_id": user_id})
    return wallet.get("balance_ve", 0) if wallet else 0

async def _deduct_ve(db, user_id: str, amount: float):
    await db.entity_wallets.update_one(
        {"entity_id": user_id},
        {"$inc": {"balance_ve": -amount}, "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}}
    )

async def _get_cosmetics_doc(db, user_id: str) -> dict:
    doc = await db.user_cosmetics.find_one({"user_id": user_id}, {"_id": 0})
    return doc or {"user_id": user_id, "owned": [], "equipped": {"frame": None, "name_color": None, "title": None}}

# ============ Endpoints ============

@cosmetics_router.get("/wallet/{user_id}")
async def get_ve_wallet(user_id: str):
    """Get user's VE$ balance"""
    db = get_db()
    return {"user_id": user_id, "balance_ve": round(await _get_wallet_balance(db, user_id), 2)}

@cosmetics_router.get("/catalog")
async def get_catalog(user_id: Optional[str] = None):
    """Full boutique catalog with ownership flags"""
    db = get_db()
    owned, equipped = [], {}
    if user_id:
        doc = await _get_cosmetics_doc(db, user_id)
        owned = doc.get("owned", [])
        equipped = doc.get("equipped", {})
    
    items = []
    for item_id, item in CATALOG.items():
        items.append({
            "item_id": item_id, **item,
            "owned": item_id in owned,
            "equipped": item_id in equipped.values() if equipped else False,
            "consumable": item["category"] in CONSUMABLE_CATEGORIES
        })
    
    balance = await _get_wallet_balance(db, user_id) if user_id else 0
    return {"items": items, "balance_ve": round(balance, 2), "equipped": equipped}

@cosmetics_router.get("/owned/{user_id}")
async def get_owned(user_id: str):
    """Owned cosmetics, equipped state and active boosts"""
    db = get_db()
    doc = await _get_cosmetics_doc(db, user_id)
    now = datetime.now(timezone.utc).isoformat()
    boosts = await db.active_boosts.find(
        {"user_id": user_id, "expires_at": {"$gt": now}}, {"_id": 0}
    ).to_list(20)
    return {"user_id": user_id, "owned": doc.get("owned", []), "equipped": doc.get("equipped", {}), "active_boosts": boosts}

@cosmetics_router.post("/purchase")
async def purchase_item(data: PurchaseRequest):
    """Purchase a cosmetic, boost or spotlight with VE$"""
    db = get_db()
    item = CATALOG.get(data.item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    doc = await _get_cosmetics_doc(db, data.user_id)
    is_consumable = item["category"] in CONSUMABLE_CATEGORIES
    
    if not is_consumable and data.item_id in doc.get("owned", []):
        raise HTTPException(status_code=400, detail="Already owned")
    
    balance = await _get_wallet_balance(db, data.user_id)
    if balance < item["price"]:
        raise HTTPException(status_code=400, detail=f"Insufficient VE$. Need {item['price']}, have {round(balance, 2)}")
    
    now = datetime.now(timezone.utc)
    await _deduct_ve(db, data.user_id, item["price"])
    
    result = {"purchased": True, "item_id": data.item_id, "name": item["name"], "spent_ve": item["price"],
              "new_balance": round(balance - item["price"], 2)}
    
    if item["category"] == "boost":
        expires = now + timedelta(hours=item["duration_hours"])
        await db.active_boosts.insert_one({
            "user_id": data.user_id, "boost_type": item["boost_type"], "multiplier": item["multiplier"],
            "item_id": data.item_id, "activated_at": now.isoformat(), "expires_at": expires.isoformat()
        })
        result["boost_active_until"] = expires.isoformat()
    elif item["category"] == "spotlight":
        user = await db.user_profiles.find_one({"id": data.user_id}, {"_id": 0, "pixel_avatar": 1, "display_name": 1, "username": 1})
        if not user or not user.get("pixel_avatar", {}).get("data_url"):
            # refund - can't spotlight without an avatar
            await db.entity_wallets.update_one({"entity_id": data.user_id}, {"$inc": {"balance_ve": item["price"]}})
            raise HTTPException(status_code=400, detail="Design your pixel avatar first in the Avatar Studio")
        expires = now + timedelta(hours=item["duration_hours"])
        await db.avatar_spotlights.insert_one({
            "user_id": data.user_id, "display_name": user.get("display_name", user.get("username")),
            "featured_at": now.isoformat(), "expires_at": expires.isoformat()
        })
        result["spotlight_until"] = expires.isoformat()
    else:
        await db.user_cosmetics.update_one(
            {"user_id": data.user_id},
            {"$addToSet": {"owned": data.item_id}, "$setOnInsert": {"equipped": {"frame": None, "name_color": None, "title": None}}},
            upsert=True
        )
    
    # purchase ledger
    await db.cosmetic_purchases.insert_one({
        "user_id": data.user_id, "item_id": data.item_id, "price_ve": item["price"],
        "category": item["category"], "purchased_at": now.isoformat()
    })
    return result

@cosmetics_router.post("/equip")
async def equip_item(data: EquipRequest):
    """Equip an owned cosmetic (frame, name color or title)"""
    db = get_db()
    
    # Unequip frame
    if data.item_id.startswith("none:"):
        slot = data.item_id.split(":")[1]
        if slot not in ("frame", "name_color", "title"):
            raise HTTPException(status_code=400, detail="Invalid slot")
        await db.user_cosmetics.update_one({"user_id": data.user_id}, {"$set": {f"equipped.{slot}": None}}, upsert=True)
        if slot == "name_color":
            await db.user_profiles.update_one({"id": data.user_id}, {"$set": {"chat_color": "default"}})
        return {"equipped": False, "slot": slot}
    
    item = CATALOG.get(data.item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if item["category"] not in ("frame", "name_color", "title"):
        raise HTTPException(status_code=400, detail="Item is not equippable")
    
    doc = await _get_cosmetics_doc(db, data.user_id)
    if data.item_id not in doc.get("owned", []):
        raise HTTPException(status_code=403, detail="You don't own this item")
    
    slot = item["category"]
    await db.user_cosmetics.update_one(
        {"user_id": data.user_id}, {"$set": {f"equipped.{slot}": data.item_id}}, upsert=True
    )
    
    # Apply side effects to profile
    if slot == "name_color":
        await db.user_profiles.update_one({"id": data.user_id}, {"$set": {"chat_color": item["color_key"]}})
    elif slot == "title":
        await db.user_profiles.update_one({"id": data.user_id}, {"$set": {"title_display": item["title_text"]}})
    
    return {"equipped": True, "slot": slot, "item_id": data.item_id, "name": item["name"]}

@cosmetics_router.get("/spotlight")
async def get_spotlight():
    """Hall of Echoes - currently featured avatars"""
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    spots = await db.avatar_spotlights.find({"expires_at": {"$gt": now}}, {"_id": 0}).sort("featured_at", -1).to_list(24)
    
    # attach avatars + frames
    featured = []
    for spot in spots:
        user = await db.user_profiles.find_one({"id": spot["user_id"]}, {"_id": 0, "pixel_avatar": 1, "display_name": 1, "title_display": 1, "chat_color": 1})
        if not user or not user.get("pixel_avatar", {}).get("data_url"):
            continue
        cos = await db.user_cosmetics.find_one({"user_id": spot["user_id"]}, {"_id": 0, "equipped": 1})
        featured.append({
            "user_id": spot["user_id"],
            "display_name": user.get("display_name") or spot.get("display_name"),
            "title_display": user.get("title_display"),
            "data_url": user["pixel_avatar"]["data_url"],
            "frame": (cos or {}).get("equipped", {}).get("frame"),
            "expires_at": spot["expires_at"]
        })
    return {"featured": featured, "count": len(featured)}
