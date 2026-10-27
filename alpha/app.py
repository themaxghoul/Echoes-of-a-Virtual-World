"""HTTP/WebSocket boundary. Run with one Uvicorn worker; see docs/HANDOFF.md."""

import asyncio
from collections import defaultdict, deque
from contextlib import asynccontextmanager, suppress
import json
import os
from pathlib import Path
import time

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from alpha.kernel import Kernel


def create_app(path=None, origins=None):
    origins = origins or os.getenv(
        "EOV_ORIGINS",
        "http://localhost:8000,http://127.0.0.1:8000,https://themaxghoul.github.io",
    ).split(",")
    clients = {}
    limits = defaultdict(deque)

    def rate(key, count, seconds):
        now = time.monotonic()
        bucket = limits[key]
        while bucket and bucket[0] < now - seconds:
            bucket.popleft()
        if len(bucket) >= count:
            raise HTTPException(429, "Too many requests. Please wait a moment.")
        bucket.append(now)
        # Bound bookkeeping under many unauthenticated addresses.
        if len(limits) > 10000:
            for old_key in list(limits):
                if not limits[old_key] or limits[old_key][-1] < now - 3600:
                    del limits[old_key]

    async def tick(app):
        previous = time.monotonic()
        ticks = 0
        while True:
            await asyncio.sleep(0.05)
            now = time.monotonic()
            app.state.kernel.step(now - previous)
            previous = now
            ticks += 1
            if ticks % 2 == 0:
                for pid, connections in list(clients.items()):
                    snap = app.state.kernel.snapshot(pid)
                    for queue in list(connections):
                        if queue.full():
                            with suppress(asyncio.QueueEmpty):
                                queue.get_nowait()
                        queue.put_nowait(snap)

    @asynccontextmanager
    async def lifespan(app):
        app.state.kernel = Kernel(path or os.getenv("EOV_DATABASE", "data/eov.sqlite3"))
        task = asyncio.create_task(tick(app))
        yield
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        app.state.kernel.flush()
        app.state.kernel.db.close()

    app = FastAPI(title="Echoes of a Virtual World — public alpha", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.middleware("http")
    async def boundaries(request, call_next):
        if request.method == "POST":
            # Read bounded body, including chunked requests without Content-Length.
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > 8192:
                    from fastapi.responses import JSONResponse

                    return JSONResponse(
                        {"detail": "Request too large."}, status_code=413
                    )
            request._body = bytes(body)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    def identity(request):
        token = request.headers.get("authorization", "").removeprefix("Bearer ")
        try:
            return app.state.kernel.authenticate(token)
        except ValueError as exc:
            raise HTTPException(401, str(exc)) from None

    class Credentials(BaseModel):
        name: str = Field(min_length=3, max_length=24)
        password: str = Field(min_length=12, max_length=128)

    @app.get("/health")
    async def health():
        app.state.kernel.db.execute("SELECT 1")
        return {
            "status": "ok",
            "protocol": 1,
            "economy": "experimental-no-cash-value",
            "dialogue": "contextual-rules",
            "online": len(clients),
        }

    @app.post("/api/session")
    async def register(data: Credentials, request: Request):
        rate(("register", request.client.host), 5, 3600)
        try:
            result = app.state.kernel.register(data.name, data.password)
            app.state.kernel.join(result["player"]["id"])
            return result
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from None

    @app.post("/api/login")
    async def login(data: Credentials, request: Request):
        rate(("login", request.client.host), 20, 60)
        try:
            return app.state.kernel.login(data.name, data.password)
        except ValueError as exc:
            raise HTTPException(401, str(exc)) from None

    @app.post("/api/logout")
    async def logout(request: Request):
        pid = identity(request)
        app.state.kernel.logout(
            request.headers["authorization"].removeprefix("Bearer ")
        )
        # Live sockets reauthenticate each message and before each snapshot.
        return {"ok": True}

    @app.get("/api/world")
    async def world(request: Request):
        return app.state.kernel.join(identity(request))

    @app.get("/api/chunk")
    async def chunk(request: Request, cx: int, cy: int):
        pid = identity(request)
        rate(("chunk", pid), 120, 1)
        try:
            return app.state.kernel.chunk(cx, cy)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from None

    @app.get("/api/ledger")
    async def ledger(request: Request):
        return app.state.kernel.ledger(identity(request))

    @app.post("/api/command")
    async def command(request: Request):
        pid = identity(request)
        rate(("command", pid), 30, 10)
        try:
            return app.state.kernel.command(pid, await request.json())
        except (ValueError, TypeError) as exc:
            raise HTTPException(400, str(exc)) from None

    @app.websocket("/ws")
    async def socket(ws: WebSocket):
        # Native future clients may omit Origin, browsers must match the deployment allowlist.
        origin = ws.headers.get("origin")
        if origin and origin not in origins:
            await ws.close(code=1008)
            return
        await ws.accept()
        pid, sender = None, None
        queue = asyncio.Queue(maxsize=2)
        try:
            auth_raw = await asyncio.wait_for(ws.receive_text(), timeout=5)
            if len(auth_raw) > 1024:
                raise ValueError("Invalid handshake")
            auth = json.loads(auth_raw)
            token = auth.get("token")
            pid = app.state.kernel.authenticate(token)
            if (
                sum(len(v) for v in clients.values()) >= 100
                or len(clients.get(pid, [])) >= 3
            ):
                await ws.close(code=1013)
                return
            app.state.kernel.join(pid)
            clients.setdefault(pid, set()).add(queue)
            app.state.kernel.online.add(pid)
            await ws.send_json(app.state.kernel.snapshot(pid))

            async def send_snapshots():
                while True:
                    snap = await queue.get()
                    try:
                        app.state.kernel.authenticate(token)
                    except ValueError:
                        await ws.close(code=1008)
                        return
                    await asyncio.wait_for(ws.send_json(snap), timeout=5)

            sender = asyncio.create_task(send_snapshots())
            while True:
                raw = await ws.receive_text()
                if len(raw) > 4096:
                    await ws.close(code=1009)
                    break
                try:
                    app.state.kernel.authenticate(token)
                    data = json.loads(raw)
                    rate(
                        (
                            (
                                "ws-input"
                                if isinstance(data, dict)
                                and data.get("type") == "input"
                                else "command"
                            ),
                            pid,
                        ),
                        60,
                        (
                            10
                            if not isinstance(data, dict) or data.get("type") != "input"
                            else 1
                        ),
                    )
                    result = app.state.kernel.command(pid, data)
                    if data.get("type") != "input":
                        # UI normally sends actions over HTTP; socket actions remain protocol-compatible.
                        if queue.full():
                            queue.get_nowait()
                        queue.put_nowait({"type": "result", **result})
                except (ValueError, TypeError, HTTPException) as exc:
                    if queue.full():
                        queue.get_nowait()
                    queue.put_nowait(
                        {"type": "error", "message": getattr(exc, "detail", str(exc))}
                    )
        except (WebSocketDisconnect, asyncio.TimeoutError, ValueError, AttributeError):
            with suppress(RuntimeError):
                await ws.close(code=1008)
        finally:
            if sender:
                sender.cancel()
                with suppress(
                    asyncio.CancelledError,
                    RuntimeError,
                    WebSocketDisconnect,
                    asyncio.TimeoutError,
                ):
                    await sender
            if pid and queue in clients.get(pid, set()):
                clients[pid].discard(queue)
                if not clients[pid]:
                    clients.pop(pid)
                    app.state.kernel.disconnect(pid)

    site = Path(__file__).resolve().parent.parent / "docs" / "play"

    @app.get("/")
    async def index():
        return RedirectResponse("/play/")

    app.mount(
        "/play", StaticFiles(directory=site, check_dir=False, html=True), name="play"
    )
    return app


app = create_app()
