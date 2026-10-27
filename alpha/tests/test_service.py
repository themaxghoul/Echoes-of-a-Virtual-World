import pytest
from fastapi.testclient import TestClient
from alpha.app import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(
        create_app(tmp_path / "test.sqlite3", origins=["http://testserver"])
    ) as c:
        yield c


def account(c, name):
    r = c.post("/api/session", json={"name": name, "password": "a-long-test-password"})
    assert r.status_code == 200
    return r.json()["token"]


def test_requires_auth_and_rejects_invalid_commands(client):
    assert client.get("/api/world").status_code == 401
    token = account(client, "Ada")
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/world", headers=headers).status_code == 200
    assert (
        client.post(
            "/api/command", headers=headers, json={"type": "teleport", "x": 999}
        ).status_code
        == 400
    )
    assert client.get("/api/chunk?cx=999999&cy=0", headers=headers).status_code == 400
    assert (
        client.post(
            "/api/command",
            headers=headers,
            json={"type": "chat", "text": "x" * 1001, "request_id": "bad"},
        ).status_code
        == 400
    )
    assert client.post("/api/logout", headers=headers).status_code == 200
    assert client.get("/api/world", headers=headers).status_code == 401


def test_two_authenticated_clients_share_chat_and_presence(client):
    one, two = account(client, "Ada"), account(client, "Bea")
    with client.websocket_connect("/ws", headers={"origin": "http://testserver"}) as a:
        a.send_json({"token": one})
        assert a.receive_json()["self"]["name"] == "Ada"
        with client.websocket_connect(
            "/ws", headers={"origin": "http://testserver"}
        ) as b:
            b.send_json({"token": two})
            assert any(p["name"] == "Ada" for p in b.receive_json()["players"])
            a.send_json(
                {"type": "chat", "text": "Shared world hello", "request_id": "hello"}
            )
            for _ in range(20):
                snap = b.receive_json()
                if any(
                    m["text"] == "Shared world hello" for m in snap.get("messages", [])
                ):
                    break
            else:
                pytest.fail("Other player did not receive world chat")


def test_unknown_credentials_never_join(client):
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
            "/ws", headers={"origin": "http://testserver"}
        ) as ws:
            ws.send_json({"token": "forged"})
            ws.receive_json()


def test_frontend_and_health_are_public_but_legacy_money_routes_absent(client):
    assert client.get("/").status_code == 200
    assert client.get("/health").json()["economy"] == "experimental-no-cash-value"
    assert client.post("/api/payout").status_code == 404


def test_simultaneous_http_replays_transfer_only_once(client):
    from concurrent.futures import ThreadPoolExecutor

    one, two = account(client, "Ada"), account(client, "Bea")
    headers = {"Authorization": f"Bearer {one}"}
    target = client.get(
        "/api/world", headers={"Authorization": f"Bearer {two}"}
    ).json()["self"]["id"]
    payload = {
        "type": "transfer",
        "to": target,
        "amount": 70,
        "request_id": "simultaneous-transfer",
    }
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(
            pool.map(
                lambda _: client.post("/api/command", headers=headers, json=payload),
                range(4),
            )
        )
    assert all(r.status_code == 200 for r in responses)
    assert client.get("/api/world", headers=headers).json()["self"]["credits"] == 30
    assert (
        client.get("/api/world", headers={"Authorization": f"Bearer {two}"}).json()[
            "self"
        ]["credits"]
        == 170
    )
