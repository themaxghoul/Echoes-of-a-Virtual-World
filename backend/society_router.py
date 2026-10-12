# Societal Standing System — social / political / economic / undercover standing.
# Standings are computed live from real play data + recorded standing events.

import uuid
import math
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from shared_db import db

society_router = APIRouter(prefix="/society", tags=["society"])
logger = logging.getLogger(__name__)

RANKS = {
    "social": [(0, "Stranger"), (20, "Acquaintance"), (40, "Known Face"), (60, "Friend of the Village"), (80, "Pillar of Society"), (95, "Living Legend")],
    "political": [(0, "Unaffiliated"), (20, "Sympathizer"), (40, "Party Member"), (60, "Inner Circle"), (80, "Power Broker"), (95, "Kingmaker")],
    "economic": [(0, "Pauper"), (20, "Laborer"), (40, "Merchant"), (60, "Magnate"), (80, "Tycoon"), (95, "Economic Force")],
    "undercover": [(0, "No Cover"), (20, "Thin Disguise"), (40, "Plausible Alias"), (60, "Deep Cover"), (80, "Ghost"), (95, "Phantom")],
}


def _rank_for(category: str, score: float) -> str:
    title = RANKS[category][0][1]
    for threshold, name in RANKS[category]:
        if score >= threshold:
            title = name
    return title


def _clamp(v: float) -> float:
    return round(max(0.0, min(100.0, v)), 1)


async def _event_delta(user_id: str, category: str) -> float:
    rows = await db.society_events.aggregate([
        {"$match": {"user_id": user_id, "category": category}},
        {"$group": {"_id": None, "total": {"$sum": "$delta"}}},
    ]).to_list(1)
    return rows[0]["total"] if rows else 0.0


class CoverRequest(BaseModel):
    user_id: str
    alias: str = Field(..., min_length=2, max_length=40)
    persona: str = Field(default="", max_length=200)


class DropCoverRequest(BaseModel):
    user_id: str


class StandingEvent(BaseModel):
    user_id: str
    category: str
    delta: float = Field(..., ge=-50, le=50)
    reason: str = "unspecified"


@society_router.get("/standing/{user_id}")
async def get_standing(user_id: str):
    # SOCIAL — NPC relationships and conversations
    npc_models = await db.player_models.count_documents({"player_id": user_id})
    interactions_rows = await db.player_models.aggregate([
        {"$match": {"player_id": user_id}},
        {"$group": {"_id": None, "total": {"$sum": {"$ifNull": ["$total_interactions", 0]}}}},
    ]).to_list(1)
    total_interactions = interactions_rows[0]["total"] if interactions_rows else 0
    social = _clamp(npc_models * 8 + total_interactions * 0.5 + await _event_delta(user_id, "social"))

    # POLITICAL — guild membership, leadership, faction
    political = 0.0
    guild = await db.guilds.find_one({"members.user_id": user_id}, {"_id": 0, "name": 1, "leader_id": 1, "tag": 1})
    guild_name = None
    if guild:
        guild_name = guild.get("name")
        political += 60 if guild.get("leader_id") == user_id else 35
    character = await db.characters.find_one({"user_id": user_id}, {"_id": 0, "faction": 1}) or {}
    if character.get("faction"):
        political += 15
    political = _clamp(political + await _event_delta(user_id, "political"))

    # ECONOMIC — wealth (VE0 + VE$) and mining contribution
    wallet = await db.entity_wallets.find_one({"entity_id": user_id}, {"_id": 0}) or {}
    wealth = wallet.get("balance_ve0", 0) + wallet.get("balance_ve", 0)
    mining_total = sum((wallet.get("mining_totals") or {}).values())
    economic = _clamp(math.log10(wealth + 1) * 22 + mining_total * 0.05 + await _event_delta(user_id, "economic"))

    # UNDERCOVER — active cover identity integrity
    cover = await db.cover_identities.find_one({"user_id": user_id, "active": True}, {"_id": 0})
    undercover = _clamp(cover.get("integrity", 0) if cover else 0)

    standings = {
        "social": {"score": social, "rank": _rank_for("social", social),
                   "detail": f"{npc_models} NPC relationships · {int(total_interactions)} conversations"},
        "political": {"score": political, "rank": _rank_for("political", political),
                      "detail": f"Guild: {guild_name or 'none'} · Faction: {character.get('faction') or 'none'}"},
        "economic": {"score": economic, "rank": _rank_for("economic", economic),
                     "detail": f"Net worth {round(wealth, 1)} VE · {round(mining_total, 1)} lifetime mined"},
        "undercover": {"score": undercover, "rank": _rank_for("undercover", undercover),
                       "detail": f"Cover: {cover['alias']} ({cover.get('persona') or 'no persona'})" if cover else "No active cover identity"},
    }
    overall = _clamp((social + political + economic) / 3)
    return {
        "user_id": user_id,
        "standings": standings,
        "overall": {"score": overall, "rank": _rank_for("social", overall)},
        "cover_identity": cover,
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }


@society_router.post("/cover/adopt")
async def adopt_cover(req: CoverRequest):
    existing = await db.cover_identities.find_one({"user_id": req.user_id, "active": True})
    if existing:
        raise HTTPException(status_code=400, detail=f"Already undercover as '{existing['alias']}'. Drop that cover first.")
    cover = {
        "cover_id": str(uuid.uuid4()),
        "user_id": req.user_id,
        "alias": req.alias,
        "persona": req.persona,
        "integrity": 100.0,
        "active": True,
        "adopted_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.cover_identities.insert_one(dict(cover))
    return {"adopted": True, "cover": cover}


@society_router.post("/cover/drop")
async def drop_cover(req: DropCoverRequest):
    result = await db.cover_identities.update_one(
        {"user_id": req.user_id, "active": True},
        {"$set": {"active": False, "dropped_at": datetime.now(timezone.utc).isoformat()}},
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="No active cover identity")
    return {"dropped": True}


@society_router.post("/event")
async def record_event(event: StandingEvent):
    if event.category not in RANKS:
        raise HTTPException(status_code=400, detail=f"Category must be one of {list(RANKS.keys())}")
    doc = {
        "event_id": str(uuid.uuid4()),
        "user_id": event.user_id,
        "category": event.category,
        "delta": event.delta,
        "reason": event.reason,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.society_events.insert_one(dict(doc))
    if event.category == "undercover":
        await db.cover_identities.update_one(
            {"user_id": event.user_id, "active": True},
            {"$inc": {"integrity": event.delta}},
        )
    return {"recorded": True, "event": doc}
