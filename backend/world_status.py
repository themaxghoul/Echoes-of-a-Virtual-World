"""Presentation-safe status metadata for the persistent world service."""

from __future__ import annotations

from typing import Any, Dict


def build_health_status(
    snapshot: Dict[str, Any],
    *,
    writes_enabled: bool,
    started_at_ms: int,
    now_ms: int,
) -> Dict[str, Any]:
    clock = snapshot.get("state", {}).get("clock", {})
    return {
        "ok": True,
        "world_id": snapshot["world_id"],
        "revision": snapshot["revision"],
        "tick": snapshot["tick"],
        "tick_seconds": int(clock.get("tick_seconds", 15)),
        "writes_enabled": bool(writes_enabled),
        "started_at_ms": int(started_at_ms),
        "uptime_seconds": max(0, (int(now_ms) - int(started_at_ms)) // 1000),
    }
