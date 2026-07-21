"""
Field Ops Router — Real-world task discovery system.

DoorDash Tasks.app-style ops:
- Photo capture (storefront, menu, shelf, signage)
- Voice recording (multilingual speech for AI training)
- Short video capture (everyday actions for embodied AI training)

Features:
- Upfront pay shown
- Geo-fenced bonus when worker is on-site
- AI vision quality check on photo submissions (Claude Sonnet 4.6)
- Heuristic quality check on audio/video (size, duration, MIME)
- Auto-pay when score passes AND reward < VE$5 threshold
- Human review queue for high-value ops
- Cross-platform: relies on standard MediaDevices / Geolocation APIs
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
import os
import math
import uuid
import base64
import logging
import asyncio

logger = logging.getLogger(__name__)

field_ops_router = APIRouter(prefix="/field-ops", tags=["field-ops"])

# ---------------- Constants ----------------

HUMAN_REVIEW_THRESHOLD_VE = 5.0          # ops paying >= this go to human review
GEO_BONUS_MULTIPLIER = 1.20               # +20% VE$ if worker on-site at submission
MAX_MEDIA_BYTES = 6 * 1024 * 1024         # 6MB per submission cap (base64 inflated)
DEFAULT_LOCK_MINUTES = 30                 # acceptance lock TTL
AUTO_PAY_MIN_SCORE = 0.65                 # AI quality score required for auto-pay

OP_TYPES = {
    "photo": {
        "label": "Photo Capture",
        "icon": "camera",
        "description": "Snap a real-world photo on location.",
        "accepted_mime": ["image/jpeg", "image/png", "image/webp"],
    },
    "voice": {
        "label": "Voice Recording",
        "icon": "mic",
        "description": "Record speech for AI language training.",
        "accepted_mime": ["audio/webm", "audio/mp4", "audio/mpeg", "audio/ogg", "audio/wav"],
    },
    "video": {
        "label": "Short Video",
        "icon": "video",
        "description": "Film a short clip of an everyday action.",
        "accepted_mime": ["video/webm", "video/mp4"],
    },
}

# Seed ops library — operators can extend via POST /create later
SEED_OPS: List[Dict[str, Any]] = [
    # ---- PHOTO ops
    {
        "op_id": "seed_storefront_verify",
        "type": "photo",
        "title": "Storefront Verification",
        "summary": "Snap a clear, well-lit photo of a business entrance with visible signage.",
        "instructions": [
            "Stand 3-5 meters back from the entrance.",
            "Capture full storefront including the business name/logo.",
            "Avoid blurry shots and ensure good lighting.",
        ],
        "base_reward_ve": 1.25,
        "duration_minutes_estimate": 5,
        "geo_required": True,
        "category": "verification",
        "difficulty": "easy",
    },
    {
        "op_id": "seed_menu_capture",
        "type": "photo",
        "title": "Restaurant Menu Documentation",
        "summary": "Photograph a restaurant's printed or posted menu with all items legible.",
        "instructions": [
            "Hold the camera steady, parallel to the menu.",
            "Make sure prices and items are readable when zoomed in.",
            "Capture the whole menu page.",
        ],
        "base_reward_ve": 2.00,
        "duration_minutes_estimate": 7,
        "geo_required": True,
        "category": "documentation",
        "difficulty": "easy",
    },
    {
        "op_id": "seed_shelf_planogram",
        "type": "photo",
        "title": "Retail Shelf Planogram",
        "summary": "Document a product shelf section with clearly visible products and pricing.",
        "instructions": [
            "Center the shelf in frame.",
            "Capture price labels and product faces.",
            "Avoid people in the shot.",
        ],
        "base_reward_ve": 1.75,
        "duration_minutes_estimate": 6,
        "geo_required": True,
        "category": "documentation",
        "difficulty": "easy",
    },
    {
        "op_id": "seed_signage_capture",
        "type": "photo",
        "title": "Public Signage Photo",
        "summary": "Capture a clear photo of a street sign, transit sign, or public notice.",
        "instructions": [
            "Frame the entire sign.",
            "Ensure text is readable and not obstructed.",
        ],
        "base_reward_ve": 0.75,
        "duration_minutes_estimate": 3,
        "geo_required": False,
        "category": "training_data",
        "difficulty": "easy",
    },
    {
        "op_id": "seed_high_value_inventory",
        "type": "photo",
        "title": "Inventory Walkthrough Series",
        "summary": "Capture 4-quadrant coverage of a retail aisle — high value, human reviewed.",
        "instructions": [
            "Submit a single representative image of an aisle.",
            "Make sure the aisle layout, brand, and product density are clearly visible.",
        ],
        "base_reward_ve": 7.50,
        "duration_minutes_estimate": 12,
        "geo_required": True,
        "category": "documentation",
        "difficulty": "medium",
    },
    # ---- VOICE ops
    {
        "op_id": "seed_voice_phrase_en",
        "type": "voice",
        "title": "Speak Phrase — English",
        "summary": "Read the provided phrase out loud in clear English.",
        "instructions": [
            "Find a quiet location.",
            "Read the phrase naturally, not robotically.",
            "Keep the recording between 5 and 15 seconds.",
        ],
        "prompt_text": "I would like to order the daily special with extra hot sauce, please.",
        "base_reward_ve": 0.60,
        "duration_minutes_estimate": 3,
        "geo_required": False,
        "category": "training_data",
        "difficulty": "easy",
    },
    {
        "op_id": "seed_voice_phrase_native",
        "type": "voice",
        "title": "Speak Phrase — Your Native Language",
        "summary": "Translate the phrase into your native language and speak it naturally.",
        "instructions": [
            "Translate accurately, keep the meaning intact.",
            "Record in a quiet space.",
            "Mention your language at the start (e.g. 'Tagalog: ...').",
        ],
        "prompt_text": "Please leave the package by the front door if no one answers.",
        "base_reward_ve": 1.25,
        "duration_minutes_estimate": 4,
        "geo_required": False,
        "category": "training_data",
        "difficulty": "easy",
    },
    {
        "op_id": "seed_voice_ambient",
        "type": "voice",
        "title": "Ambient Soundscape",
        "summary": "Record 20-30 seconds of ambient sound from a real environment (cafe, street, transit).",
        "instructions": [
            "Stay still while recording.",
            "Do not speak during the recording.",
            "Name the environment in your submission notes.",
        ],
        "base_reward_ve": 0.85,
        "duration_minutes_estimate": 4,
        "geo_required": False,
        "category": "training_data",
        "difficulty": "easy",
    },
    # ---- VIDEO ops
    {
        "op_id": "seed_video_pour_drink",
        "type": "video",
        "title": "Everyday Action — Pour a Drink",
        "summary": "Film a 5-10 second clip of yourself pouring a drink from a container into a cup.",
        "instructions": [
            "Hold the phone steady, landscape orientation preferred.",
            "Show hands clearly throughout the motion.",
            "Keep clip under 12 seconds.",
        ],
        "base_reward_ve": 1.50,
        "duration_minutes_estimate": 4,
        "geo_required": False,
        "category": "training_data",
        "difficulty": "easy",
    },
    {
        "op_id": "seed_video_open_door",
        "type": "video",
        "title": "Everyday Action — Open a Door",
        "summary": "Film yourself opening a door (push or pull). Used for embodied AI training.",
        "instructions": [
            "Approach the door, grasp the handle, open it, walk through.",
            "Keep camera angle stable from chest height.",
        ],
        "base_reward_ve": 1.50,
        "duration_minutes_estimate": 4,
        "geo_required": False,
        "category": "training_data",
        "difficulty": "easy",
    },
    {
        "op_id": "seed_video_premium_room_tour",
        "type": "video",
        "title": "Property Room Walkthrough — Premium",
        "summary": "Slow 360 walkthrough of a single room. Premium reward, human reviewed.",
        "instructions": [
            "Walk slowly along the walls of one room.",
            "Show all four walls and the floor.",
            "Keep clip between 15 and 30 seconds.",
        ],
        "base_reward_ve": 6.50,
        "duration_minutes_estimate": 10,
        "geo_required": True,
        "category": "documentation",
        "difficulty": "medium",
    },
]

# ---------------- Models ----------------

class AcceptOpRequest(BaseModel):
    user_id: str
    op_id: str

class SubmitOpRequest(BaseModel):
    user_id: str
    submission_id: str  # returned from accept
    media_base64: str   # data URI or raw base64
    mime_type: str
    duration_ms: Optional[int] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    notes: Optional[str] = None

class ReviewSubmissionRequest(BaseModel):
    reviewer_id: str
    submission_id: str
    decision: str  # "approve" | "reject"
    feedback: Optional[str] = None

class CreateOpRequest(BaseModel):
    op_id: Optional[str] = None
    type: str
    title: str
    summary: str
    instructions: List[str] = Field(default_factory=list)
    base_reward_ve: float
    duration_minutes_estimate: int = 5
    geo_required: bool = False
    target_lat: Optional[float] = None
    target_lng: Optional[float] = None
    geo_radius_m: int = 150
    category: str = "training_data"
    difficulty: str = "easy"
    prompt_text: Optional[str] = None

# ---------------- Helpers ----------------

def get_db():
    from server import db
    return db

def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _decode_data_url(data_url: str) -> bytes:
    if "," in data_url:
        data_url = data_url.split(",", 1)[1]
    try:
        return base64.b64decode(data_url, validate=False)
    except Exception:
        return b""

async def _ensure_seeded(db):
    """Idempotent seed of starter ops library."""
    count = await db.field_ops_library.count_documents({})
    if count > 0:
        return
    docs = []
    for spec in SEED_OPS:
        docs.append({
            **spec,
            "target_lat": None,
            "target_lng": None,
            "geo_radius_m": 150,
            "created_at": _now_iso(),
            "active": True,
        })
    if docs:
        await db.field_ops_library.insert_many(docs)
        logger.info(f"Field Ops: seeded {len(docs)} ops")

async def _credit_worker(db, user_id: str, amount_ve: float, source: str, ref: str):
    """Pay worker VE$ (with Forge Surge boost applied)."""
    from cosmetics_router import get_boost_multiplier
    multiplier = await get_boost_multiplier(db, user_id, "task_reward")
    boosted = round(amount_ve * multiplier, 4)
    await db.entity_wallets.update_one(
        {"entity_id": user_id},
        {
            "$inc": {"balance_ve": boosted, "total_earned": boosted},
            "$set": {"updated_at": _now_iso()},
        },
        upsert=True,
    )
    await db.earnings_transactions.insert_one({
        "transaction_id": str(uuid.uuid4()),
        "user_id": user_id,
        "amount_ve": boosted,
        "source": source,
        "reference_id": ref,
        "created_at": _now_iso(),
        "boost_multiplier": multiplier,
    })
    return boosted, multiplier > 1.0

async def _ai_check_photo(media_b64: str, mime: str, op: dict) -> Dict[str, Any]:
    """Claude Sonnet vision-based quality check. Falls back to lightweight heuristic if LLM unavailable."""
    raw = _decode_data_url(media_b64)
    size = len(raw)
    if size < 3000:
        return {"score": 0.0, "reason": "Image too small / corrupt", "method": "heuristic"}

    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        # Fallback heuristic — accept if size is reasonable
        score = min(1.0, size / 80000.0)
        return {"score": round(score, 2), "reason": "Heuristic pass (no LLM)", "method": "heuristic-size"}

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
        chat = LlmChat(
            api_key=api_key,
            session_id=f"field-ops-{uuid.uuid4().hex[:8]}",
            system_message=(
                "You are a strict quality reviewer for crowd-sourced AI training photos. "
                "Score images 0.0-1.0 on: (a) clarity/focus, (b) framing match to the brief, "
                "(c) absence of obstructions. Respond ONLY with compact JSON: "
                '{"score": <float>, "reason": "<short reason>"}'
            ),
        ).with_model("anthropic", "claude-sonnet-4-6")

        # Strip data: prefix
        clean_b64 = media_b64.split(",", 1)[1] if "," in media_b64 else media_b64
        img = ImageContent(image_base64=clean_b64)
        brief = f"BRIEF: {op['title']} — {op['summary']}\nINSTRUCTIONS: {' | '.join(op.get('instructions', []))}"
        msg = UserMessage(text=brief + "\n\nScore this image against the brief.", file_contents=[img])

        # Non-streaming for one-shot evaluation
        resp = await asyncio.wait_for(chat.send_message(msg), timeout=25.0)
        text = (resp or "").strip()
        import json as _json
        # Extract JSON from possible markdown fence
        if "```" in text:
            text = text.split("```")[1].lstrip("json").strip()
        try:
            parsed = _json.loads(text)
            score = float(parsed.get("score", 0))
            reason = parsed.get("reason", "ok")
        except Exception:
            score, reason = 0.7, "LLM returned non-JSON; defaulted"
        return {"score": max(0.0, min(1.0, score)), "reason": reason, "method": "claude-sonnet-4-6"}
    except asyncio.TimeoutError:
        return {"score": 0.6, "reason": "LLM timeout; provisional pass", "method": "timeout-fallback"}
    except Exception as e:
        logger.warning(f"Field Ops AI check failed: {e}")
        return {"score": 0.6, "reason": f"AI check error ({type(e).__name__}); provisional pass", "method": "error-fallback"}

def _heuristic_check_audio(size_bytes: int, duration_ms: Optional[int], mime: str) -> Dict[str, Any]:
    if mime not in OP_TYPES["voice"]["accepted_mime"]:
        return {"score": 0.0, "reason": f"Unsupported audio MIME {mime}", "method": "heuristic"}
    if size_bytes < 3000:
        return {"score": 0.0, "reason": "Recording too short / empty", "method": "heuristic"}
    if duration_ms is not None:
        if duration_ms < 2000:
            return {"score": 0.1, "reason": "Recording shorter than 2 seconds", "method": "heuristic"}
        if duration_ms > 60000:
            return {"score": 0.5, "reason": "Recording over 60 seconds — may be excessive", "method": "heuristic"}
    return {"score": 0.85, "reason": "Audio passes size/duration heuristics", "method": "heuristic"}

def _heuristic_check_video(size_bytes: int, duration_ms: Optional[int], mime: str) -> Dict[str, Any]:
    if mime not in OP_TYPES["video"]["accepted_mime"]:
        return {"score": 0.0, "reason": f"Unsupported video MIME {mime}", "method": "heuristic"}
    if size_bytes < 20000:
        return {"score": 0.0, "reason": "Video too small / empty", "method": "heuristic"}
    if duration_ms is not None:
        if duration_ms < 3000:
            return {"score": 0.2, "reason": "Video shorter than 3 seconds", "method": "heuristic"}
        if duration_ms > 45000:
            return {"score": 0.55, "reason": "Video over 45 seconds — may exceed brief", "method": "heuristic"}
    return {"score": 0.85, "reason": "Video passes size/duration heuristics", "method": "heuristic"}

# ---------------- Endpoints ----------------

@field_ops_router.get("/types")
async def list_op_types():
    """Return the 3 op types and their accepted MIMEs."""
    return {"types": OP_TYPES, "auto_pay_threshold_ve": HUMAN_REVIEW_THRESHOLD_VE,
            "geo_bonus_multiplier": GEO_BONUS_MULTIPLIER, "auto_pay_min_score": AUTO_PAY_MIN_SCORE}

@field_ops_router.post("/seed")
async def seed_library():
    """Idempotently seed the starter ops library (admin)."""
    db = get_db()
    await _ensure_seeded(db)
    total = await db.field_ops_library.count_documents({})
    return {"seeded": True, "total_ops": total}

@field_ops_router.get("/available")
async def list_available_ops(
    user_id: Optional[str] = None,
    lat: Optional[float] = Query(None),
    lng: Optional[float] = Query(None),
    op_type: Optional[str] = Query(None, alias="type"),
):
    """List active ops. Distance calculated when caller sends lat/lng."""
    db = get_db()
    await _ensure_seeded(db)

    q: Dict[str, Any] = {"active": True}
    if op_type:
        q["type"] = op_type
    ops = await db.field_ops_library.find(q, {"_id": 0}).to_list(200)

    # Active locks for this user (so we can show "you've accepted this")
    my_active = set()
    if user_id:
        active = await db.field_ops_submissions.find(
            {"user_id": user_id, "status": {"$in": ["accepted", "in_progress"]}},
            {"op_id": 1, "_id": 0},
        ).to_list(200)
        my_active = {s["op_id"] for s in active}

    enriched = []
    for op in ops:
        item = dict(op)
        item["upfront_ve"] = round(op["base_reward_ve"], 2)
        item["geo_bonus_ve"] = round(op["base_reward_ve"] * (GEO_BONUS_MULTIPLIER - 1.0), 2) if op.get("geo_required") else 0.0
        item["review_mode"] = "human" if op["base_reward_ve"] >= HUMAN_REVIEW_THRESHOLD_VE else "auto"
        item["accepted_by_me"] = op["op_id"] in my_active
        if lat is not None and lng is not None and op.get("target_lat") is not None and op.get("target_lng") is not None:
            item["distance_m"] = round(haversine_m(lat, lng, op["target_lat"], op["target_lng"]))
        else:
            item["distance_m"] = None
        enriched.append(item)

    # Sort: accepted-by-me first, then by distance asc, then reward desc
    enriched.sort(key=lambda o: (
        0 if o["accepted_by_me"] else 1,
        o["distance_m"] if o["distance_m"] is not None else 10**9,
        -o["base_reward_ve"],
    ))
    return {"ops": enriched, "count": len(enriched)}

@field_ops_router.post("/create")
async def create_op(data: CreateOpRequest):
    """Create a new op (admin / experimenters)."""
    db = get_db()
    if data.type not in OP_TYPES:
        raise HTTPException(status_code=400, detail=f"Unknown type {data.type}")
    op_id = data.op_id or f"op_{uuid.uuid4().hex[:10]}"
    doc = {
        "op_id": op_id,
        "type": data.type,
        "title": data.title,
        "summary": data.summary,
        "instructions": data.instructions,
        "base_reward_ve": float(data.base_reward_ve),
        "duration_minutes_estimate": data.duration_minutes_estimate,
        "geo_required": data.geo_required,
        "target_lat": data.target_lat,
        "target_lng": data.target_lng,
        "geo_radius_m": data.geo_radius_m,
        "category": data.category,
        "difficulty": data.difficulty,
        "prompt_text": data.prompt_text,
        "active": True,
        "created_at": _now_iso(),
    }
    await db.field_ops_library.insert_one(doc)
    doc.pop("_id", None)
    return {"created": True, "op": doc}

@field_ops_router.post("/accept")
async def accept_op(data: AcceptOpRequest):
    """Lock an op for this worker for 30 minutes."""
    db = get_db()
    op = await db.field_ops_library.find_one({"op_id": data.op_id, "active": True}, {"_id": 0})
    if not op:
        raise HTTPException(status_code=404, detail="Op not found or inactive")

    # one active acceptance per user per op
    existing = await db.field_ops_submissions.find_one({
        "user_id": data.user_id, "op_id": data.op_id,
        "status": {"$in": ["accepted", "in_progress"]},
    })
    if existing:
        return {"accepted": True, "submission_id": existing["submission_id"], "already_locked": True}

    submission_id = f"sub_{uuid.uuid4().hex[:12]}"
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=DEFAULT_LOCK_MINUTES)).isoformat()
    await db.field_ops_submissions.insert_one({
        "submission_id": submission_id,
        "user_id": data.user_id,
        "op_id": data.op_id,
        "op_type": op["type"],
        "base_reward_ve": op["base_reward_ve"],
        "status": "accepted",
        "accepted_at": _now_iso(),
        "expires_at": expires_at,
    })
    return {"accepted": True, "submission_id": submission_id, "expires_at": expires_at,
            "op": op}

@field_ops_router.post("/submit")
async def submit_op(data: SubmitOpRequest):
    """Submit captured media. Runs quality check and either auto-pays or queues for review."""
    db = get_db()
    sub = await db.field_ops_submissions.find_one({"submission_id": data.submission_id, "user_id": data.user_id})
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    if sub["status"] not in ("accepted", "in_progress"):
        raise HTTPException(status_code=400, detail=f"Submission status is '{sub['status']}', cannot resubmit")

    op = await db.field_ops_library.find_one({"op_id": sub["op_id"]}, {"_id": 0})
    if not op:
        raise HTTPException(status_code=404, detail="Op definition missing")

    # Validate media size and MIME
    raw = _decode_data_url(data.media_base64)
    size = len(raw)
    if size == 0:
        raise HTTPException(status_code=400, detail="Empty media payload")
    if size > MAX_MEDIA_BYTES:
        raise HTTPException(status_code=413, detail=f"Media too large ({size} bytes, max {MAX_MEDIA_BYTES})")
    if data.mime_type not in OP_TYPES[op["type"]]["accepted_mime"]:
        raise HTTPException(status_code=400, detail=f"MIME {data.mime_type} not allowed for {op['type']}")

    # Quality check by type
    if op["type"] == "photo":
        qc = await _ai_check_photo(data.media_base64, data.mime_type, op)
    elif op["type"] == "voice":
        qc = _heuristic_check_audio(size, data.duration_ms, data.mime_type)
    else:
        qc = _heuristic_check_video(size, data.duration_ms, data.mime_type)

    # Geo bonus
    geo_valid = False
    distance_m = None
    if op.get("geo_required") and op.get("target_lat") is not None and op.get("target_lng") is not None \
            and data.lat is not None and data.lng is not None:
        distance_m = round(haversine_m(data.lat, data.lng, op["target_lat"], op["target_lng"]))
        geo_valid = distance_m <= op.get("geo_radius_m", 150)
    elif op.get("geo_required") and (op.get("target_lat") is None or op.get("target_lng") is None):
        # Op requires geo but no target set — treat any submitted coords as a soft bonus
        geo_valid = data.lat is not None and data.lng is not None

    base = float(op["base_reward_ve"])
    geo_bonus = round(base * (GEO_BONUS_MULTIPLIER - 1.0), 4) if geo_valid else 0.0
    potential_total = round(base + geo_bonus, 4)

    # Decide path: auto-pay vs human review
    requires_review = base >= HUMAN_REVIEW_THRESHOLD_VE
    passes = qc["score"] >= AUTO_PAY_MIN_SCORE

    new_status = "queued_review"
    paid_ve = 0.0
    boost_applied = False
    if not requires_review:
        if passes:
            new_status = "auto_approved"
            paid_ve, boost_applied = await _credit_worker(
                db, data.user_id, potential_total, "field_ops", data.submission_id
            )
        else:
            new_status = "auto_rejected"

    # Persist media + result
    await db.field_ops_submissions.update_one(
        {"submission_id": data.submission_id},
        {"$set": {
            "status": new_status,
            "submitted_at": _now_iso(),
            "media_mime": data.mime_type,
            "media_size_bytes": size,
            "media_base64": data.media_base64,    # NOTE: capped at MAX_MEDIA_BYTES above
            "duration_ms": data.duration_ms,
            "lat": data.lat,
            "lng": data.lng,
            "distance_m": distance_m,
            "geo_valid": geo_valid,
            "geo_bonus_ve": geo_bonus,
            "quality_check": qc,
            "paid_ve": paid_ve,
            "boost_applied": boost_applied,
            "notes": data.notes,
        }}
    )

    return {
        "submitted": True,
        "status": new_status,
        "quality_check": qc,
        "geo_valid": geo_valid,
        "geo_bonus_ve": geo_bonus,
        "paid_ve": paid_ve,
        "boost_applied": boost_applied,
        "requires_review": requires_review,
        "potential_total_ve": potential_total,
    }

@field_ops_router.get("/my-submissions/{user_id}")
async def my_submissions(user_id: str, limit: int = 50):
    """User's submissions (most recent first). Excludes media payload for list views."""
    db = get_db()
    docs = await db.field_ops_submissions.find(
        {"user_id": user_id},
        {"_id": 0, "media_base64": 0},
    ).sort("accepted_at", -1).to_list(limit)
    # Resolve op title for display
    op_ids = list({d["op_id"] for d in docs})
    ops = await db.field_ops_library.find({"op_id": {"$in": op_ids}}, {"_id": 0, "op_id": 1, "title": 1, "type": 1}).to_list(200)
    by_id = {o["op_id"]: o for o in ops}
    for d in docs:
        meta = by_id.get(d["op_id"], {})
        d["op_title"] = meta.get("title", d["op_id"])
        d["op_type"] = meta.get("type", d.get("op_type"))
    return {"submissions": docs, "count": len(docs)}

@field_ops_router.get("/submission/{submission_id}")
async def get_submission(submission_id: str, include_media: bool = False):
    """Single submission detail; media payload excluded by default."""
    db = get_db()
    projection = {"_id": 0}
    if not include_media:
        projection["media_base64"] = 0
    doc = await db.field_ops_submissions.find_one({"submission_id": submission_id}, projection)
    if not doc:
        raise HTTPException(status_code=404, detail="Submission not found")
    return doc

@field_ops_router.get("/review-queue")
async def review_queue(limit: int = 50):
    """Submissions awaiting human review (high-value ops)."""
    db = get_db()
    docs = await db.field_ops_submissions.find(
        {"status": "queued_review"},
        {"_id": 0, "media_base64": 0},
    ).sort("submitted_at", 1).to_list(limit)
    return {"queue": docs, "count": len(docs)}

@field_ops_router.post("/review")
async def review_submission(data: ReviewSubmissionRequest):
    """Reviewer approves or rejects a queued submission. Approval triggers payout."""
    db = get_db()
    # Reviewer must exist; for now: anyone with user_profiles.permission_level == 'sirix_1' or 'admin'
    reviewer = await db.user_profiles.find_one({"id": data.reviewer_id}, {"_id": 0, "permission_level": 1, "username": 1})
    if not reviewer or reviewer.get("permission_level") not in ("admin", "sirix_1"):
        raise HTTPException(status_code=403, detail="Reviewer must be admin or sirix_1")

    sub = await db.field_ops_submissions.find_one({"submission_id": data.submission_id})
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    if sub["status"] != "queued_review":
        raise HTTPException(status_code=400, detail=f"Submission is '{sub['status']}', not queued_review")

    if data.decision == "approve":
        total = float(sub["base_reward_ve"]) + float(sub.get("geo_bonus_ve", 0.0))
        paid, boost = await _credit_worker(db, sub["user_id"], total, "field_ops_review", sub["submission_id"])
        await db.field_ops_submissions.update_one(
            {"submission_id": data.submission_id},
            {"$set": {
                "status": "approved",
                "paid_ve": paid,
                "boost_applied": boost,
                "reviewed_at": _now_iso(),
                "reviewer_id": data.reviewer_id,
                "review_feedback": data.feedback,
            }}
        )
        return {"reviewed": True, "decision": "approve", "paid_ve": paid, "boost_applied": boost}
    elif data.decision == "reject":
        await db.field_ops_submissions.update_one(
            {"submission_id": data.submission_id},
            {"$set": {
                "status": "rejected",
                "reviewed_at": _now_iso(),
                "reviewer_id": data.reviewer_id,
                "review_feedback": data.feedback or "No feedback provided",
            }}
        )
        return {"reviewed": True, "decision": "reject"}
    else:
        raise HTTPException(status_code=400, detail="decision must be 'approve' or 'reject'")

@field_ops_router.get("/stats")
async def stats():
    """High-level Field Ops stats."""
    db = get_db()
    total_ops = await db.field_ops_library.count_documents({"active": True})
    total_subs = await db.field_ops_submissions.count_documents({})
    approved = await db.field_ops_submissions.count_documents({"status": {"$in": ["approved", "auto_approved"]}})
    queued = await db.field_ops_submissions.count_documents({"status": "queued_review"})
    rejected = await db.field_ops_submissions.count_documents({"status": {"$in": ["rejected", "auto_rejected"]}})

    agg = await db.field_ops_submissions.aggregate([
        {"$match": {"status": {"$in": ["approved", "auto_approved"]}}},
        {"$group": {"_id": None, "total_paid": {"$sum": "$paid_ve"}}}
    ]).to_list(1)
    total_paid = round(agg[0]["total_paid"], 2) if agg else 0.0

    return {
        "active_ops": total_ops,
        "submissions_total": total_subs,
        "approved": approved,
        "auto_approval_rate": round(approved / total_subs, 3) if total_subs else 0.0,
        "queued_review": queued,
        "rejected": rejected,
        "total_paid_ve": total_paid,
    }
