# Hybrid-Growth Economic Subsystem — VE0 (proto) / VE Vouchers / VE$ (final)
# BTC-indexed hybrid valuation: f(BTC) = alpha*ln(BTC) + beta + gamma*BTC^delta
# Simulation-native mining: quantum entropy + XR spatial work + AI cognitive yield.

import os
import math
import time
import uuid
import random
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from pymongo import ReturnDocument

from shared_db import db

hybrid_economy_router = APIRouter(prefix="/hybrid-economy", tags=["hybrid-economy"])
logger = logging.getLogger(__name__)

CONFIG_KEY = "hybrid_economy"
ADMIN_ID = "sirix_1_supreme"
COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"
ATTRIBUTION = "Data provided by CoinGecko"

DEFAULT_CONFIG = {
    "config_key": CONFIG_KEY,
    "alpha": 1.8,
    "beta": 5.0,
    "gamma": 0.02,
    "delta": 0.22,
    "ve0_conversion_ratio": 0.25,
    "voucher_unit_multiplier": 1000000.0,
    "btc_override": None,
    "milestone_target": 25000.0,
    "quantum_progress": 0.0,
    "launched": False,
    "launch_btc_price": None,
    "launch_ve_value": None,
    "launched_at": None,
    "launch_reason": None,
    "gold_mine": None,
    "ve_migration_done": False,
}

VOUCHER_TIERS = {
    "bronze":   {"btc_units": 0.000001, "label": "Bronze"},
    "silver":   {"btc_units": 0.000005, "label": "Silver"},
    "gold":     {"btc_units": 0.00001,  "label": "Gold"},
    "quantum":  {"btc_units": 0.00005,  "label": "Quantum"},
    "systemic": {"btc_units": 0.0001,   "label": "Systemic"},
}

CHANNELS = {
    "presence": {
        "rate": 0.15, "max_per_call": 3.0, "daily_cap": 30.0, "entropy": 0.25,
        "label": "XR Presence",
        "how": "Simply be inside the world (Story Mode or 3D Explorer). Every minute of presence mints VE0 automatically.",
    },
    "xr_spatial": {
        "rate": 0.02, "max_per_call": 240.0, "daily_cap": 45.0, "entropy": 0.5,
        "label": "XR Spatial Work",
        "how": "Move, explore and interact while in the world. Movement and interaction logs convert into spatial yield.",
    },
    "ai_cognitive": {
        "rate": 0.8, "max_per_call": 5.0, "daily_cap": 40.0, "entropy": 1.0,
        "label": "AI Cognitive Yield",
        "how": "Talk to NPCs and train AI minds. Every meaningful conversation feeds simulation cognition and pays you.",
    },
    "quantum_entropy": {
        "rate": 0.5, "max_per_call": 10.0, "daily_cap": 50.0, "entropy": 2.0,
        "label": "Quantum Entropy",
        "how": "Stabilize the quantum field from the Economy Nexus. Extracted entropy mints VE0 and awakens the Gold Mine fastest.",
    },
}

# Lifetime per-channel VE0 thresholds -> voucher tier auto-award
VOUCHER_LADDER = [(50.0, "bronze"), (200.0, "silver"), (600.0, "gold"), (1500.0, "quantum"), (4000.0, "systemic")]

_btc_cache = {"price": None, "ts": 0.0}
_last_tick = {}
_last_stab = {}


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


async def get_config() -> dict:
    cfg = await db.economy_config.find_one({"config_key": CONFIG_KEY}, {"_id": 0})
    if not cfg:
        await db.economy_config.update_one(
            {"config_key": CONFIG_KEY}, {"$setOnInsert": dict(DEFAULT_CONFIG)}, upsert=True
        )
        cfg = dict(DEFAULT_CONFIG)
    for k, v in DEFAULT_CONFIG.items():
        cfg.setdefault(k, v)
    return cfg


async def ensure_ve0_migration():
    """One-time: convert all existing VE$ balances to VE0 at 1:1 (grandfathering)."""
    cfg = await get_config()
    if cfg.get("ve_migration_done"):
        return {"migrated": False, "reason": "already_done"}
    result = await db.entity_wallets.update_many(
        {"balance_ve": {"$gt": 0}},
        [{"$set": {
            "balance_ve0": {"$add": [{"$ifNull": ["$balance_ve0", 0]}, "$balance_ve"]},
            "ve_grandfathered": "$balance_ve",
            "balance_ve": 0,
        }}],
    )
    await db.economy_config.update_one(
        {"config_key": CONFIG_KEY},
        {"$set": {"ve_migration_done": True, "ve_migration_at": _now_iso(),
                  "ve_migration_wallets": result.modified_count}},
    )
    logger.info(f"VE$ -> VE0 migration complete: {result.modified_count} wallets converted 1:1")
    return {"migrated": True, "wallets": result.modified_count}


async def get_btc_price(cfg: Optional[dict] = None):
    cfg = cfg or await get_config()
    if cfg.get("btc_override"):
        return float(cfg["btc_override"]), "admin_override"
    now = time.time()
    if _btc_cache["price"] and now - _btc_cache["ts"] < 300:
        return _btc_cache["price"], "coingecko_cached"
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(COINGECKO_URL, params={
                "vs_currencies": "usd",
                "ids": "bitcoin",
                "x_cg_demo_api_key": os.environ.get("COINGECKO_API_KEY"),
            })
            r.raise_for_status()
            price = float(r.json()["bitcoin"]["usd"])
        _btc_cache["price"] = price
        _btc_cache["ts"] = now
        await db.economy_state.update_one(
            {"state_key": "btc_last"},
            {"$set": {"price": price, "fetched_at": _now_iso()}},
            upsert=True,
        )
        return price, "coingecko"
    except Exception as e:
        logger.warning(f"CoinGecko fetch failed: {e}")
        if _btc_cache["price"]:
            return _btc_cache["price"], "stale_cache"
        stored = await db.economy_state.find_one({"state_key": "btc_last"})
        if stored:
            return float(stored["price"]), "stored_fallback"
        return 0.0, "unavailable"


def ve_index_value(btc_price: float, cfg: dict) -> dict:
    """Hybrid growth: log stability + polynomial responsiveness. Hard-capped at 1% of BTC."""
    beta = float(cfg["beta"])
    if btc_price <= 0:
        return {"value": round(beta, 6), "log_term": 0.0, "poly_term": 0.0, "beta": beta, "capped": False}
    log_term = float(cfg["alpha"]) * math.log(btc_price)
    poly_term = float(cfg["gamma"]) * (btc_price ** float(cfg["delta"]))
    raw = log_term + beta + poly_term
    cap = btc_price * 0.01
    return {
        "value": round(min(raw, cap), 6),
        "log_term": round(log_term, 6),
        "poly_term": round(poly_term, 6),
        "beta": beta,
        "capped": raw > cap,
    }


async def _today_totals(entity_id: str):
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rows = await db.ve0_ledger.aggregate([
        {"$match": {"entity_id": entity_id, "day": day}},
        {"$group": {"_id": "$channel", "total": {"$sum": "$ve0"}}},
    ]).to_list(20)
    return {r["_id"]: r["total"] for r in rows}, day


async def _award_voucher(owner_id: str, tier: str, earned_via: str) -> dict:
    v = {
        "voucher_id": str(uuid.uuid4()),
        "owner_id": owner_id,
        "tier": tier,
        "btc_units": VOUCHER_TIERS[tier]["btc_units"],
        "earned_via": earned_via,
        "created_at": _now_iso(),
        "redeemed": False,
        "ve_payout": None,
    }
    cfg = await get_config()
    if cfg.get("launched"):
        btc, _ = await get_btc_price(cfg)
        val = ve_index_value(btc, cfg)["value"]
        payout = round(val * v["btc_units"] * float(cfg["voucher_unit_multiplier"]), 4)
        v["redeemed"] = True
        v["ve_payout"] = payout
        v["redeemed_at"] = _now_iso()
        await db.entity_wallets.update_one(
            {"entity_id": owner_id},
            {"$inc": {"balance_ve": payout, "total_earned": payout}},
            upsert=True,
        )
    await db.ve_vouchers.insert_one(dict(v))
    return v


async def _check_voucher_awards(entity_id: str, channel: str) -> list:
    wallet = await db.entity_wallets.find_one({"entity_id": entity_id}, {"_id": 0})
    if not wallet:
        return []
    lifetime = (wallet.get("mining_totals") or {}).get(channel, 0.0)
    already = set((wallet.get("voucher_awards") or {}).get(channel, []))
    awarded = []
    for threshold, tier in VOUCHER_LADDER:
        if lifetime >= threshold and tier not in already:
            voucher = await _award_voucher(entity_id, tier, f"{channel}_milestone_{int(threshold)}")
            await db.entity_wallets.update_one(
                {"entity_id": entity_id},
                {"$addToSet": {f"voucher_awards.{channel}": tier}},
            )
            awarded.append({"tier": tier, "voucher_id": voucher["voucher_id"], "threshold": threshold})
    return awarded


async def record_contribution(entity_id: str, channel: str, raw_amount: float,
                              source: str = "system", meta: Optional[dict] = None) -> dict:
    if channel not in CHANNELS:
        return {"minted": 0.0, "channel": channel, "error": "unknown_channel"}
    ch = CHANNELS[channel]
    raw = max(0.0, min(float(raw_amount), ch["max_per_call"]))
    if raw <= 0:
        return {"minted": 0.0, "channel": channel}
    cfg = await get_config()
    launched = bool(cfg.get("launched"))
    totals, day = await _today_totals(entity_id)
    used = totals.get(channel, 0.0)
    room = max(0.0, ch["daily_cap"] - used)
    minted = round(min(raw * ch["rate"], room), 4)
    entropy = 0.0
    vouchers_awarded = []
    if minted > 0:
        entropy = round(minted * ch["entropy"] * (0.8 + random.random() * 0.4), 4)
        bal_field = "balance_ve" if launched else "balance_ve0"
        inc = {bal_field: minted, f"mining_totals.{channel}": minted}
        if launched:
            inc["total_earned"] = minted
        await db.entity_wallets.update_one(
            {"entity_id": entity_id},
            {"$inc": inc,
             "$set": {"updated_at": _now_iso()},
             "$setOnInsert": {"entity_type": "player", "created_at": _now_iso(), "is_active": True}},
            upsert=True,
        )
        await db.ve0_ledger.insert_one({
            "entry_id": str(uuid.uuid4()),
            "entity_id": entity_id,
            "channel": channel,
            "raw": raw,
            "ve0": minted,
            "currency": "VE$" if launched else "VE0",
            "entropy": entropy,
            "source": source,
            "meta": meta or {},
            "day": day,
            "created_at": _now_iso(),
        })
        if not launched:
            updated = await db.economy_config.find_one_and_update(
                {"config_key": CONFIG_KEY},
                {"$inc": {"quantum_progress": entropy}},
                return_document=ReturnDocument.AFTER,
            )
            if updated and updated.get("quantum_progress", 0) >= updated.get("milestone_target", float("inf")):
                await trigger_economic_launch("quantum_awakening")
        vouchers_awarded = await _check_voucher_awards(entity_id, channel)
    return {
        "channel": channel,
        "minted": minted,
        "currency": "VE$" if launched else "VE0",
        "entropy_contributed": entropy,
        "daily_used": round(used + minted, 4),
        "daily_cap": ch["daily_cap"],
        "vouchers_awarded": vouchers_awarded,
    }


async def trigger_economic_launch(reason: str):
    """The Quantum Awakening: VE0 converts, vouchers evaluate against f(BTC), the Gold Mine springs."""
    flipped = await db.economy_config.find_one_and_update(
        {"config_key": CONFIG_KEY, "launched": False},
        {"$set": {"launched": True}},
        return_document=ReturnDocument.AFTER,
    )
    if not flipped:
        return None
    cfg = await get_config()
    btc, btc_source = await get_btc_price(cfg)
    vix = ve_index_value(btc, cfg)
    ratio = float(cfg["ve0_conversion_ratio"])
    conv = await db.entity_wallets.update_many(
        {"balance_ve0": {"$gt": 0}},
        [{"$set": {
            "balance_ve": {"$add": [{"$ifNull": ["$balance_ve", 0]}, {"$multiply": ["$balance_ve0", ratio]}]},
            "ve0_converted_at_launch": "$balance_ve0",
            "balance_ve0": 0,
        }}],
    )
    mult = float(cfg["voucher_unit_multiplier"])
    redeemed = 0
    total_voucher_ve = 0.0
    async for v in db.ve_vouchers.find({"redeemed": False}):
        payout = round(vix["value"] * float(v["btc_units"]) * mult, 4)
        await db.ve_vouchers.update_one(
            {"voucher_id": v["voucher_id"]},
            {"$set": {"redeemed": True, "ve_payout": payout, "redeemed_at": _now_iso()}},
        )
        await db.entity_wallets.update_one(
            {"entity_id": v["owner_id"]},
            {"$inc": {"balance_ve": payout, "total_earned": payout}},
            upsert=True,
        )
        redeemed += 1
        total_voucher_ve += payout
    gold_mine = {
        "name": "The Aurum Breach",
        "location_id": "outer_realms",
        "x": random.randint(-40, 40),
        "y": random.randint(-40, 40),
        "description": "A colossal gold mine has torn itself out of the digital landscape. "
                       "Quantum computations completed, the simulation awakened — VE$ is live.",
        "sprung_at": _now_iso(),
    }
    await db.economy_config.update_one(
        {"config_key": CONFIG_KEY},
        {"$set": {
            "launch_btc_price": btc,
            "launch_btc_source": btc_source,
            "launch_ve_value": vix["value"],
            "launched_at": _now_iso(),
            "launch_reason": reason,
            "gold_mine": gold_mine,
            "wallets_converted": conv.modified_count,
            "vouchers_redeemed": redeemed,
        }},
    )
    await db.world_events.insert_one({
        "event_id": str(uuid.uuid4()),
        "type": "golden_awakening",
        "title": "THE QUANTUM AWAKENING — The Aurum Breach has sprung from the landscape",
        "description": gold_mine["description"],
        "location_id": gold_mine["location_id"],
        "created_at": _now_iso(),
    })
    logger.info(f"ECONOMIC LAUNCH ({reason}): BTC={btc}, VE index={vix['value']}, "
                f"wallets={conv.modified_count}, vouchers={redeemed}")
    return {
        "launched": True,
        "reason": reason,
        "btc_price": btc,
        "ve_index": vix["value"],
        "wallets_converted": conv.modified_count,
        "vouchers_redeemed": redeemed,
        "total_voucher_ve": round(total_voucher_ve, 4),
        "gold_mine": gold_mine,
    }


# ============ Request Models ============

class PresenceTick(BaseModel):
    entity_id: str
    seconds: float = Field(default=60, ge=0, le=180)
    movements: int = Field(default=0, ge=0)
    interactions: int = Field(default=0, ge=0)


class MineRequest(BaseModel):
    entity_id: str
    channel: str
    amount: float = Field(default=1.0, ge=0)
    source: str = "manual"


class ConfigUpdate(BaseModel):
    admin_id: str
    alpha: Optional[float] = None
    beta: Optional[float] = None
    gamma: Optional[float] = None
    delta: Optional[float] = Field(default=None, ge=0.05, le=0.5)
    ve0_conversion_ratio: Optional[float] = Field(default=None, gt=0, le=1)
    voucher_unit_multiplier: Optional[float] = Field(default=None, gt=0)
    milestone_target: Optional[float] = Field(default=None, gt=0)
    btc_override: Optional[float] = None
    clear_btc_override: bool = False


class ForceLaunch(BaseModel):
    admin_id: str


def _require_admin(admin_id: str):
    if admin_id != ADMIN_ID:
        raise HTTPException(status_code=403, detail="Admin access required")


# ============ Public Endpoints ============

@hybrid_economy_router.get("/status")
async def economy_status():
    cfg = await get_config()
    btc, source = await get_btc_price(cfg)
    vix = ve_index_value(btc, cfg)
    supply_rows = await db.entity_wallets.aggregate([
        {"$group": {"_id": None,
                    "total_ve0": {"$sum": {"$ifNull": ["$balance_ve0", 0]}},
                    "total_ve": {"$sum": {"$ifNull": ["$balance_ve", 0]}}}},
    ]).to_list(1)
    supply = supply_rows[0] if supply_rows else {"total_ve0": 0, "total_ve": 0}
    voucher_rows = await db.ve_vouchers.aggregate([
        {"$group": {"_id": "$tier", "count": {"$sum": 1}}},
    ]).to_list(10)
    miners = await db.ve0_ledger.distinct("entity_id")
    progress = min(cfg["quantum_progress"], cfg["milestone_target"])
    return {
        "launched": cfg["launched"],
        "launched_at": cfg.get("launched_at"),
        "launch_reason": cfg.get("launch_reason"),
        "launch_btc_price": cfg.get("launch_btc_price"),
        "launch_ve_value": cfg.get("launch_ve_value"),
        "gold_mine": cfg.get("gold_mine"),
        "quantum_progress": round(cfg["quantum_progress"], 4),
        "milestone_target": cfg["milestone_target"],
        "progress_pct": round(progress / cfg["milestone_target"] * 100, 2) if cfg["milestone_target"] else 0,
        "btc": {"price": btc, "source": source, "attribution": ATTRIBUTION},
        "ve_index": vix,
        "params": {k: cfg[k] for k in ("alpha", "beta", "gamma", "delta", "ve0_conversion_ratio", "voucher_unit_multiplier")},
        "supply": {
            "total_ve0": round(supply.get("total_ve0", 0), 4),
            "total_ve": round(supply.get("total_ve", 0), 4),
            "vouchers_by_tier": {r["_id"]: r["count"] for r in voucher_rows},
            "active_miners": len(miners),
        },
        "channels": {k: {"label": v["label"], "how": v["how"], "rate": v["rate"],
                         "daily_cap": v["daily_cap"], "entropy": v["entropy"]}
                     for k, v in CHANNELS.items()},
        "voucher_tiers": VOUCHER_TIERS,
        "voucher_ladder": [{"threshold": t, "tier": tier} for t, tier in VOUCHER_LADDER],
    }


@hybrid_economy_router.get("/valuation")
async def valuation():
    cfg = await get_config()
    btc, source = await get_btc_price(cfg)
    vix = ve_index_value(btc, cfg)
    return {
        "btc_price": btc,
        "btc_source": source,
        "attribution": ATTRIBUTION,
        "formula": "VE$ = alpha*ln(BTC) + beta + gamma*BTC^delta (capped at 1% of BTC)",
        "ve_index": vix,
        "params": {k: cfg[k] for k in ("alpha", "beta", "gamma", "delta")},
        "launched": cfg["launched"],
    }


@hybrid_economy_router.get("/wallet/{entity_id}")
async def economy_wallet(entity_id: str):
    cfg = await get_config()
    wallet = await db.entity_wallets.find_one({"entity_id": entity_id}, {"_id": 0}) or {}
    totals, _day = await _today_totals(entity_id)
    vouchers = await db.ve_vouchers.find({"owner_id": entity_id}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {
        "entity_id": entity_id,
        "balance_ve0": round(wallet.get("balance_ve0", 0), 4),
        "balance_ve": round(wallet.get("balance_ve", 0), 4),
        "ve_locked": not cfg["launched"],
        "ve_grandfathered": wallet.get("ve_grandfathered", 0),
        "mining_totals": wallet.get("mining_totals", {}),
        "today": {ch: {"used": round(totals.get(ch, 0), 4), "cap": CHANNELS[ch]["daily_cap"]} for ch in CHANNELS},
        "vouchers": vouchers,
        "voucher_count": len(vouchers),
        "launched": cfg["launched"],
    }


@hybrid_economy_router.post("/presence/tick")
async def presence_tick(tick: PresenceTick):
    now = time.time()
    last = _last_tick.get(tick.entity_id, 0)
    if now - last < 45:
        raise HTTPException(status_code=429, detail=f"Presence tick rate-limited. Retry in {round(45 - (now - last))}s")
    _last_tick[tick.entity_id] = now
    presence = await record_contribution(tick.entity_id, "presence", tick.seconds / 60.0, source="presence_tick")
    spatial = {"minted": 0.0}
    xr_raw = min(tick.movements + tick.interactions * 2, 240)
    if xr_raw > 0:
        spatial = await record_contribution(tick.entity_id, "xr_spatial", xr_raw, source="presence_tick",
                                            meta={"movements": tick.movements, "interactions": tick.interactions})
    return {"accepted": True, "presence": presence, "xr_spatial": spatial}


@hybrid_economy_router.post("/mine")
async def mine(req: MineRequest):
    if req.channel not in CHANNELS:
        raise HTTPException(status_code=400, detail=f"Unknown channel. Valid: {list(CHANNELS.keys())}")
    if req.channel == "quantum_entropy":
        now = time.time()
        last = _last_stab.get(req.entity_id, 0)
        if now - last < 20:
            raise HTTPException(status_code=429, detail=f"Quantum field re-charging. Retry in {round(20 - (now - last))}s")
        _last_stab[req.entity_id] = now
    result = await record_contribution(req.entity_id, req.channel, req.amount, source=req.source)
    return result


@hybrid_economy_router.get("/vouchers/{entity_id}")
async def vouchers(entity_id: str):
    items = await db.ve_vouchers.find({"owner_id": entity_id}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {"entity_id": entity_id, "vouchers": items, "count": len(items), "tiers": VOUCHER_TIERS}


@hybrid_economy_router.get("/ledger/{entity_id}")
async def ledger(entity_id: str, limit: int = 50):
    entries = await db.ve0_ledger.find({"entity_id": entity_id}, {"_id": 0}) \
        .sort("created_at", -1).to_list(min(limit, 200))
    return {"entity_id": entity_id, "entries": entries}


# ============ Admin Endpoints ============

@hybrid_economy_router.get("/config")
async def read_config(admin_id: str):
    _require_admin(admin_id)
    return await get_config()


@hybrid_economy_router.put("/config")
async def update_config(update: ConfigUpdate):
    _require_admin(update.admin_id)
    fields = {}
    for key in ("alpha", "beta", "gamma", "delta", "ve0_conversion_ratio",
                "voucher_unit_multiplier", "milestone_target", "btc_override"):
        val = getattr(update, key)
        if val is not None:
            fields[key] = float(val)
    if update.clear_btc_override:
        fields["btc_override"] = None
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    await db.economy_config.update_one({"config_key": CONFIG_KEY}, {"$set": fields})
    _btc_cache["ts"] = 0.0
    return {"updated": True, "fields": fields, "config": await get_config()}


@hybrid_economy_router.post("/launch/force")
async def force_launch(req: ForceLaunch):
    _require_admin(req.admin_id)
    result = await trigger_economic_launch("admin_force")
    if result is None:
        raise HTTPException(status_code=400, detail="Economy already launched")
    return result
