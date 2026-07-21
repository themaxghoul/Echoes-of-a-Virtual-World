# Pixel Avatar System - designable 64x64 logo avatars (replaces profile pictures)

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone

avatar_router = APIRouter(prefix="/avatar", tags=["avatar"])

GRID_SIZE = 64
MAX_PIXELS = GRID_SIZE * GRID_SIZE  # 4096
MAX_PALETTE = 64
MAX_DATA_URL_BYTES = 60_000

def get_db():
    from server import db
    return db

# Base palette - free for everyone (32 colors)
BASE_PALETTE = [
    "#000000", "#1A1C2C", "#5D275D", "#B13E53", "#EF7D57", "#FFCD75", "#A7F070", "#38B764",
    "#257179", "#29366F", "#3B5DC9", "#41A6F6", "#73EFF7", "#F4F4F4", "#94B0C2", "#566C86",
    "#333C57", "#FFFFFF", "#8B4513", "#D2691E", "#F5DEB3", "#FFB6C1", "#DC143C", "#800000",
    "#2F4F4F", "#708090", "#4B0082", "#9370DB", "#FFD700", "#DAA520", "#556B2F", "#006400",
]

# Premium packs - unlocked via VE$ Boutique (item ids match cosmetics catalog)
PALETTE_PACKS = {
    "palette_neon": {"name": "Neon Pack", "colors": ["#FF10F0", "#00FFF7", "#39FF14", "#FF3C00", "#FFFF00", "#FF1493", "#00FF7F", "#7DF9FF"]},
    "palette_metallic": {"name": "Metallic Pack", "colors": ["#D4AF37", "#C0C0C0", "#B87333", "#E5E4E2", "#CD7F32", "#FFD700", "#A8A9AD", "#4C4C47"]},
    "palette_pastel": {"name": "Pastel Pack", "colors": ["#FFB3BA", "#FFDFBA", "#FFFFBA", "#BAFFC9", "#BAE1FF", "#E0BBE4", "#FEC8D8", "#D5F4E6"]},
    "palette_cosmic": {"name": "Cosmic Pack", "colors": ["#0B0B45", "#3D0066", "#7209B7", "#B5179E", "#F72585", "#4CC9F0", "#10002B", "#E0AAFF"]},
}

class AvatarSave(BaseModel):
    pixels: List[int]          # 4096 palette indices, -1 = transparent
    palette: List[str]         # hex colors used
    data_url: str              # rendered 64x64 PNG data URL

@avatar_router.get("/palettes")
async def get_palettes(user_id: Optional[str] = None):
    """Base palette + premium packs with ownership flags"""
    db = get_db()
    owned = []
    if user_id:
        doc = await db.user_cosmetics.find_one({"user_id": user_id}, {"_id": 0, "owned": 1})
        owned = (doc or {}).get("owned", [])
    
    packs = []
    for pack_id, pack in PALETTE_PACKS.items():
        packs.append({"pack_id": pack_id, "name": pack["name"], "colors": pack["colors"], "owned": pack_id in owned})
    
    return {"base_palette": BASE_PALETTE, "packs": packs, "grid_size": GRID_SIZE}

@avatar_router.get("/user/{user_id}")
async def get_avatar(user_id: str):
    """Get a user's pixel avatar + equipped frame"""
    db = get_db()
    user = await db.user_profiles.find_one({"id": user_id}, {"_id": 0, "pixel_avatar": 1, "display_name": 1, "username": 1})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    cos = await db.user_cosmetics.find_one({"user_id": user_id}, {"_id": 0, "equipped": 1})
    avatar = user.get("pixel_avatar") or {}
    
    return {
        "user_id": user_id,
        "has_avatar": bool(avatar.get("data_url")),
        "data_url": avatar.get("data_url"),
        "pixels": avatar.get("pixels"),
        "palette": avatar.get("palette"),
        "frame": (cos or {}).get("equipped", {}).get("frame"),
        "updated_at": avatar.get("updated_at")
    }

@avatar_router.put("/user/{user_id}")
async def save_avatar(user_id: str, data: AvatarSave):
    """Save a user's designed 64x64 pixel avatar"""
    db = get_db()
    
    if len(data.pixels) != MAX_PIXELS:
        raise HTTPException(status_code=400, detail=f"Pixels must be exactly {MAX_PIXELS} entries (64x64)")
    if len(data.palette) > MAX_PALETTE:
        raise HTTPException(status_code=400, detail=f"Palette limited to {MAX_PALETTE} colors")
    if not data.data_url.startswith("data:image/png;base64,"):
        raise HTTPException(status_code=400, detail="data_url must be a PNG data URL")
    if len(data.data_url) > MAX_DATA_URL_BYTES:
        raise HTTPException(status_code=400, detail="Avatar image too large")
    
    palette_len = len(data.palette)
    for idx in data.pixels:
        if idx < -1 or idx >= palette_len:
            raise HTTPException(status_code=400, detail="Pixel index out of palette range")
    
    user = await db.user_profiles.find_one({"id": user_id}, {"_id": 0, "id": 1})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.user_profiles.update_one(
        {"id": user_id},
        {"$set": {"pixel_avatar": {
            "pixels": data.pixels,
            "palette": data.palette,
            "data_url": data.data_url,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}}
    )
    return {"saved": True, "user_id": user_id}

@avatar_router.delete("/user/{user_id}")
async def clear_avatar(user_id: str):
    """Clear a user's pixel avatar"""
    db = get_db()
    await db.user_profiles.update_one({"id": user_id}, {"$unset": {"pixel_avatar": ""}})
    return {"cleared": True}
