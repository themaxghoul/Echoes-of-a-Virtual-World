import unittest
import asyncio
import importlib
import json
import os
import tempfile
from pathlib import Path

import httpx
import anyio

from auth_security import issue_session_token
from persistent_world import PersistentWorldStore

from world_status import build_health_status


SECRET = "test-only-secret-that-is-longer-than-thirty-two-bytes"


class AuthenticatedWorkshopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        # Avoid opening the application's production database on import.
        previous = os.environ.get("EOV_WORLD_DATABASE")
        os.environ["EOV_WORLD_DATABASE"] = str(Path(self.temp.name) / "import.sqlite3")
        try:
            self.api = importlib.import_module("persistent_world_app")
        finally:
            if previous is None:
                os.environ.pop("EOV_WORLD_DATABASE", None)
            else:
                os.environ["EOV_WORLD_DATABASE"] = previous
        self.saved = self.api.store, self.api.SESSION_SECRET, self.api.OWNER_USER_ID
        self.api.store = PersistentWorldStore(Path(self.temp.name) / "world.sqlite3")
        self.api.SESSION_SECRET = SECRET
        self.api.OWNER_USER_ID = "owner"
        self.world = self.api.store.create_world(now_ms=1_000_000)["world_id"]
        self.token = issue_session_token("alice", 0, SECRET)[0]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def tearDown(self):
        self.api.store.close()
        self.api.store, self.api.SESSION_SECRET, self.api.OWNER_USER_ID = self.saved
        self.saved[0].close()
        self.temp.cleanup()

    def request(self, method, suffix, **kwargs):
        async def send():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.api.app), base_url="http://test") as client:
                try:
                    return await client.request(method, f"/worlds/{self.world}{suffix}", **kwargs)
                finally:
                    await anyio.to_thread.run_sync(self.api.store.close)
        return asyncio.run(send())

    def stream(self, *, token=None, query=b"", after_snapshot=None):
        async def exchange():
            incoming, outgoing = asyncio.Queue(), asyncio.Queue()
            await incoming.put({"type": "websocket.connect"})
            protocols = ["eov-session", token] if token else []
            scope = {"type": "websocket", "asgi": {"version": "3.0"}, "scheme": "ws", "path": f"/worlds/{self.world}/stream", "raw_path": b"/", "query_string": query, "headers": [(b"sec-websocket-protocol", ", ".join(protocols).encode())], "client": ("test", 1), "server": ("test", 80), "subprotocols": protocols, "root_path": ""}
            task = asyncio.create_task(self.api.app(scope, incoming.get, outgoing.put))
            messages = []
            try:
                while True:
                    message = await asyncio.wait_for(outgoing.get(), 5)
                    messages.append(message)
                    if message["type"] == "websocket.close":
                        break
                    if message["type"] == "websocket.send":
                        if after_snapshot and len([m for m in messages if m["type"] == "websocket.send"]) == 1:
                            after_snapshot()
                        else:
                            break
            finally:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            return messages
        return asyncio.run(exchange())

    def test_action_identity_comes_only_from_token_and_conflicts_are_rejected(self):
        for body in ({"actor_id": "bob"}, {"action": {"type": "join", "actor_id": "bob"}}):
            payload = {"action_id": "spoofed-join", "action": {"type": "join"}, **body}
            response = self.request("POST", "/actions", json=payload, headers=self.headers)
            self.assertEqual(403, response.status_code, response.text)
        response = self.request("POST", "/actions", json={"action_id": "honest-join", "action": {"type": "join"}}, headers=self.headers)
        self.assertEqual(200, response.status_code)
        self.assertEqual(["alice"], list(self.api.store.snapshot()["state"]["players"]))
        self.assertEqual(403, self.request("GET", "/living-workshop?actor_id=bob", headers=self.headers).status_code)

    def test_workshop_projection_cannot_read_other_memory_or_hidden_diagnosis(self):
        self.api.store.apply_action(self.world, "join-bob-private", "bob", {"type": "join"})
        snapshot = self.api.store.snapshot()
        snapshot["state"]["players"]["bob"]["memories"] = [{"text": "BOB-SECRET"}]
        with self.api.store.transaction() as connection:
            connection.execute("UPDATE worlds SET state_json=? WHERE world_id=?", (json.dumps(snapshot["state"]), self.world))
        self.assertEqual(401, self.request("GET", "/living-workshop").status_code)
        response = self.request("GET", "/living-workshop", headers=self.headers)
        self.assertEqual(200, response.status_code)
        view = response.json()
        self.assertEqual("alice", view["viewer_id"])
        self.assertNotIn("BOB-SECRET", response.text)
        self.assertNotIn("condition", view["state"]["installations"]["water"])
        self.assertNotIn("water_repair_spec", view["state"]["living_workshop"])

    def test_websocket_authenticates_before_accept_and_rejects_identity_override(self):
        for token, query in ((None, b""), (self.token, b"actor_id=bob"), ("invalid", b"")):
            messages = self.stream(token=token, query=query)
            self.assertEqual([{"type": "websocket.close", "code": 1008, "reason": ""}], messages)

    def test_websocket_emits_ordered_filtered_projection_changes(self):
        def change():
            self.api.store.apply_action(self.world, "stream-alice-join", "alice", {"type": "join"}, now_ms=1_000_001)
        messages = self.stream(token=self.token, after_snapshot=change)
        frames = [json.loads(item["text"]) for item in messages if item["type"] == "websocket.send"]
        first, update = frames
        self.assertEqual("snapshot", first["type"])
        self.assertEqual("projection", update["type"])
        self.assertGreater(update["revision"], first["revision"])
        self.assertGreaterEqual(update["tick"], first["tick"])
        self.assertEqual("alice", update["data"]["viewer_id"])
        sequences = [event["sequence"] for event in update["events"]]
        self.assertEqual(sorted(set(sequences)), sequences)
        self.assertNotIn("condition", update["data"]["state"]["installations"]["water"])

    def test_health_reports_pending_catch_up_and_owner_controls_remain_separate(self):
        self.api.store.advance_due(now_ms=1_150_000, max_ticks=1)
        self.assertTrue(self.api.health()["catch_up_pending"])
        response = self.request("POST", "/actions", headers=self.headers, json={"action_id": "owner-spoof", "action": {"type": "operator_amendment"}})
        self.assertEqual(403, response.status_code)
        response = self.request("POST", "/operator-amendments", headers=self.headers, json={"action_id": "owner-spoof", "operation": "pause_world", "reason": "testing separation", "confirmation": "CONFIRM WORLD AMENDMENT"})
        self.assertEqual(403, response.status_code)

    def test_owner_identity_conflicts_are_rejected_and_authorized_amendment_is_audited(self):
        owner_headers = {"Authorization": "Bearer " + issue_session_token("owner", 0, SECRET)[0]}
        body = {"action_id": "audited-owner-pause", "operation": "pause_world", "reason": "Testing recovery boundary", "confirmation": "CONFIRM WORLD AMENDMENT"}
        self.assertEqual(403, self.request("POST", "/operator-amendments", headers=owner_headers, json={**body, "actor_id": "bob"}).status_code)
        self.assertEqual(200, self.request("POST", "/operator-amendments", headers=owner_headers, json=body).status_code)
        state = self.api.store.snapshot()["state"]
        self.assertTrue(state["clock"]["paused"])
        self.assertEqual("owner", state["operator_audit"][-1]["principal"])
        self.assertNotIn("owner", state["players"])

    def test_websocket_replay_cursor_never_moves_back_from_initial_snapshot(self):
        for index in range(130):
            self.api.store.apply_action(self.world, f"backlog-join-{index}", "alice", {"type": "join"}, now_ms=1_000_001 + index)
        messages = self.stream(token=self.token, after_snapshot=lambda: None)
        frames = [json.loads(item["text"]) for item in messages if item["type"] == "websocket.send"]
        self.assertGreaterEqual(frames[1]["cursor"], frames[0]["cursor"])
        self.assertLessEqual(len(frames[1]["events"]), 250)
        self.assertEqual(1, frames[1]["events"][0]["sequence"])

    def test_owner_directive_rejects_another_principals_idempotency_key(self):
        self.api.store.apply_action(self.world, "occupied-owner-key", "alice", {"type": "join"})
        before = self.api.store.snapshot()
        headers = {"Authorization": "Bearer " + issue_session_token("owner", 0, SECRET)[0]}
        response = self.request("POST", "/owner-directives", headers=headers, json={
            "action_id": "occupied-owner-key", "objective": "Check the water installation", "priority": "water",
        })
        self.assertEqual(403, response.status_code)
        self.assertEqual(before, self.api.store.snapshot())

    def test_websocket_emits_catch_up_status_without_a_new_revision(self):
        def change():
            self.api.store.advance_due(now_ms=1_150_000, max_ticks=0)
        try:
            messages = self.stream(token=self.token, after_snapshot=change)
        except TimeoutError:
            self.fail("Stream did not publish the changed catch-up status")
        frames = [json.loads(item["text"]) for item in messages if item["type"] == "websocket.send"]
        first, update = frames
        self.assertEqual(first["revision"], update["revision"])
        self.assertFalse(first["data"]["catch_up_pending"])
        self.assertTrue(update["data"]["catch_up_pending"])
        self.assertEqual([], update["events"])


class PersistentWorldHealthTests(unittest.TestCase):
    def test_health_status_reports_world_tick_interval_and_process_uptime(self):
        snapshot = {
            "world_id": "founders-settlement",
            "revision": 17,
            "tick": 144,
            "state": {"clock": {"tick_seconds": 15}},
        }

        status = build_health_status(snapshot, writes_enabled=True, started_at_ms=1_000, now_ms=7_385_000)

        self.assertEqual(
            {
                "ok": True,
                "world_id": "founders-settlement",
                "revision": 17,
                "tick": 144,
                "tick_seconds": 15,
                "writes_enabled": True,
                "started_at_ms": 1_000,
                "uptime_seconds": 7_384,
            },
            status,
        )


if __name__ == "__main__":
    unittest.main()
