"""Two-player network smoke test. Default target is local Wrangler.

Run with Python environment containing httpx and websockets. A supplied public
URL creates two disposable alpha settlers; never use against unrelated systems.
"""

import asyncio
import json
import secrets
import sys
import uuid
import httpx
import websockets


async def main(base):
    async with httpx.AsyncClient(base_url=base, timeout=20) as client:
        assert (await client.get("/health")).json()["status"] == "ok"
        assert (await client.get("/api/world")).status_code == 401
        sessions = []
        for _ in range(2):
            response = await client.post(
                "/api/session",
                json={
                    "name": "Test_" + uuid.uuid4().hex[:10],
                    "password": secrets.token_urlsafe(24),
                },
            )
            assert response.status_code == 200, response.text
            sessions.append(response.json())
        one, two = sessions
        h1 = {"Authorization": "Bearer " + one["token"]}
        h2 = {"Authorization": "Bearer " + two["token"]}
        before = (await client.get("/api/world", headers=h1)).json()
        async with websockets.connect(
            base.replace("http", "ws", 1) + "/ws", origin=base
        ) as a, websockets.connect(
            base.replace("http", "ws", 1) + "/ws", origin=base
        ) as b:
            await a.send(json.dumps({"token": one["token"]}))
            assert json.loads(await a.recv())["self"]["id"] == one["player"]["id"]
            await b.send(json.dumps({"token": two["token"]}))
            snap = json.loads(await b.recv())
            assert any(p["id"] == one["player"]["id"] for p in snap["players"])
            await a.send(json.dumps({"type": "input", "dx": 1, "dy": 0}))
            moved = False
            for _ in range(10):
                snap = json.loads(await asyncio.wait_for(a.recv(), 3))
                if snap.get("self", {}).get("x", 0) > 0:
                    moved = True
                    break
            assert moved, "Movement did not reach the socket client"
            cmd = {
                "type": "transfer",
                "to": two["player"]["id"],
                "amount": 25,
                "request_id": uuid.uuid4().hex,
            }
            results = await asyncio.gather(
                *[client.post("/api/command", headers=h1, json=cmd) for _ in range(3)]
            )
            assert all(r.status_code == 200 for r in results)
            assert (await client.get("/api/world", headers=h1)).json()["self"][
                "credits"
            ] == 75
            assert (await client.get("/api/world", headers=h2)).json()["self"][
                "credits"
            ] == 125
            result = await client.post(
                "/api/command",
                headers=h1,
                json={
                    "type": "talk",
                    "npc": "mira",
                    "text": "How can I help you?",
                    "request_id": uuid.uuid4().hex,
                },
            )
            assert result.status_code == 200
            assert len(result.json()["reply"].strip()) > 20
            await client.post(
                "/api/command",
                headers=h1,
                json={
                    "type": "chat",
                    "text": "network smoke hello",
                    "request_id": uuid.uuid4().hex,
                },
            )
            for _ in range(30):
                snap = json.loads(await asyncio.wait_for(b.recv(), 3))
                if any(
                    m["text"] == "network smoke hello" for m in snap.get("messages", [])
                ):
                    break
            else:
                raise AssertionError("Second player did not receive chat")
            after = (await client.get("/api/world", headers=h1)).json()
            assert before["world"]["radius"] == after["world"]["radius"]
        print(
            "PASS: health, authorization, two-client presence/movement/chat, concurrent transfer replay, dialogue, stable membership"
        )


if __name__ == "__main__":
    asyncio.run(
        main(sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:8787")
    )
