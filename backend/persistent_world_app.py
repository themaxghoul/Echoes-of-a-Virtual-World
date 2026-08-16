"""FastAPI surface for the authoritative EoV persistent world service."""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from auth_security import SessionTokenError, verify_session_token
from owner_policy import is_owner_session_subject
from persistent_world import DEFAULT_WORLD_ID, PersistentWorldStore, RevisionConflict, actor_event_view, actor_world_view


DATABASE_PATH = Path(os.environ.get("EOV_WORLD_DATABASE", Path(__file__).parent / "data" / "persistent-world.sqlite3"))
SESSION_SECRET = os.environ.get("EOV_SESSION_SECRET", "")
OWNER_USER_ID = os.environ.get("EOV_OWNER_USER_ID", "").strip()
RUNNER_ID = f"runclock-{uuid.uuid4()}"
store = PersistentWorldStore(DATABASE_PATH)


class ActionRequest(BaseModel):
    action_id: str = Field(min_length=8, max_length=128)
    expected_revision: Optional[int] = None
    action: Dict[str, Any]


class OwnerDirectiveRequest(BaseModel):
    action_id: str = Field(min_length=8, max_length=128)
    expected_revision: Optional[int] = None
    objective: str = Field(min_length=3, max_length=240)
    priority: str = Field(min_length=1, max_length=40)
    evidence_required: list[str] = Field(default_factory=list, max_length=12)


class OperatorAmendmentRequest(BaseModel):
    action_id: str = Field(min_length=8, max_length=128)
    expected_revision: Optional[int] = None
    operation: str = Field(pattern="^(pause_world|resume_world|amend_tile)$")
    reason: str = Field(min_length=8, max_length=240)
    confirmation: str
    location: Optional[list[int]] = None
    changes: Dict[str, Any] = Field(default_factory=dict)


def authorize_write(authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authenticated EoV session required")
    try:
        return verify_session_token(authorization[7:], SESSION_SECRET)
    except SessionTokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc))


def authorize_owner(claims: Dict[str, Any] = Depends(authorize_write)) -> Dict[str, Any]:
    if not OWNER_USER_ID:
        raise HTTPException(status_code=503, detail="Persistent-world owner UUID is not configured")
    if not is_owner_session_subject(claims, OWNER_USER_ID):
        raise HTTPException(status_code=403, detail="Authenticated owner account required")
    return claims


async def runclock_loop() -> None:
    while True:
        now_ms = int(time.time() * 1000)
        try:
            if store.acquire_lease(DEFAULT_WORLD_ID, RUNNER_ID, now_ms):
                store.advance_due(DEFAULT_WORLD_ID, now_ms)
        except Exception:
            # The next lease interval retries; committed SQLite revisions remain authoritative.
            pass
        await asyncio.sleep(1)


@asynccontextmanager
async def lifespan(_: FastAPI):
    store.create_world(DEFAULT_WORLD_ID)
    task = asyncio.create_task(runclock_loop())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="Echoes of Virtuality Persistent World", version="1.0-alpha.32", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin for origin in os.environ.get("EOV_ALLOWED_ORIGINS", "http://localhost:3000,null").split(",") if origin],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/health")
def health() -> Dict[str, Any]:
    snapshot = store.snapshot(DEFAULT_WORLD_ID)
    return {"ok": True, "world_id": snapshot["world_id"], "revision": snapshot["revision"], "tick": snapshot["tick"], "writes_enabled": len(SESSION_SECRET.encode()) >= 32}


@app.get("/worlds/{world_id}")
def get_world(world_id: str, claims: Dict[str, Any] = Depends(authorize_write)) -> Dict[str, Any]:
    return actor_world_view(store.snapshot(world_id), claims["sub"])


@app.get("/worlds/{world_id}/events")
def get_events(world_id: str, after: int = 0, limit: int = 250, claims: Dict[str, Any] = Depends(authorize_write)) -> Dict[str, Any]:
    snapshot = store.snapshot(world_id)
    events = [actor_event_view(event, snapshot, claims["sub"]) for event in store.events(world_id, after, limit)]
    return {"events": events, "last_sequence": events[-1]["sequence"] if events else after}


@app.post("/worlds/{world_id}/actions")
def post_action(world_id: str, request: ActionRequest, claims: Dict[str, Any] = Depends(authorize_write)) -> Dict[str, Any]:
    try:
        return store.apply_action(world_id, request.action_id, claims["sub"], request.action, request.expected_revision)
    except KeyError:
        raise HTTPException(status_code=404, detail="World not found")
    except RevisionConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@app.post("/worlds/{world_id}/owner-directives")
def post_owner_directive(world_id: str, request: OwnerDirectiveRequest, claims: Dict[str, Any] = Depends(authorize_owner)) -> Dict[str, Any]:
    """Record owner intent as a reviewable proposal, never as divine world mutation."""
    try:
        return store.apply_owner_directive(
            world_id,
            request.action_id,
            claims["sub"],
            {
                "objective": request.objective,
                "priority": request.priority,
                "evidence_required": request.evidence_required,
            },
            request.expected_revision,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="World not found")
    except RevisionConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.post("/worlds/{world_id}/operator-amendments")
def post_operator_amendment(world_id: str, request: OperatorAmendmentRequest, claims: Dict[str, Any] = Depends(authorize_owner)) -> Dict[str, Any]:
    """Apply an explicit world-scoped intervention outside simulated society."""
    try:
        return store.apply_operator_amendment(world_id, request.action_id, claims["sub"], request.model_dump(exclude={"action_id", "expected_revision"}), request.expected_revision)
    except KeyError:
        raise HTTPException(status_code=404, detail="World not found")
    except RevisionConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except (PermissionError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.websocket("/worlds/{world_id}/stream")
async def world_stream(websocket: WebSocket, world_id: str, after: int = Query(default=0)):
    offered = [item.strip() for item in websocket.headers.get("sec-websocket-protocol", "").split(",") if item.strip()]
    try:
        marker = offered.index("eov-session")
        encoded = offered[marker + 1]
    except (ValueError, IndexError):
        encoded = None
    try:
        claims = verify_session_token(encoded or "", SESSION_SECRET)
    except SessionTokenError:
        await websocket.close(code=4401)
        return
    await websocket.accept(subprotocol="eov-session")
    cursor = after
    try:
        await websocket.send_json({"type": "snapshot", "data": actor_world_view(store.snapshot(world_id), claims["sub"])})
        while True:
            if int(time.time()) >= claims["exp"]:
                await websocket.close(code=4401)
                return
            snapshot = store.snapshot(world_id)
            events = [actor_event_view(event, snapshot, claims["sub"]) for event in store.events(world_id, cursor, 250)]
            if events:
                cursor = events[-1]["sequence"]
                await websocket.send_json({"type": "events", "events": events, "cursor": cursor})
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        return
