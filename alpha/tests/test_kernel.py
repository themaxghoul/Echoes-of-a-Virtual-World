import math
import sqlite3
import pytest
from alpha.kernel import Kernel


@pytest.fixture
def game(tmp_path):
    k = Kernel(tmp_path / "world.sqlite3")
    yield k
    k.db.close()


def player(k, name="Ada"):
    session = k.register(name, "a-long-test-password")
    return k.authenticate(session["token"])


def test_password_session_and_restart(tmp_path):
    path = tmp_path / "world.sqlite3"
    k = Kernel(path)
    session = k.register("Ada", "a-long-test-password")
    p = k.authenticate(session["token"])
    k.join(p)
    k.db.close()
    k = Kernel(path)
    assert k.authenticate(session["token"]) == p
    assert k.login("ada", "a-long-test-password")["player"]["id"] == p
    with pytest.raises(ValueError):
        k.login("Ada", "incorrect-password")
    assert "password" not in str(k.snapshot(p))
    k.db.close()


def test_world_expands_only_for_new_members_and_terrain_stays_stable(game):
    p = player(game)
    game.join(p)
    radius = game.snapshot(p)["world"]["radius"]
    original = game.chunk(0, 0)
    game.join(p)
    for _ in range(20):
        game.step(0.05)
    assert game.snapshot(p)["world"]["radius"] == radius
    q = player(game, "Bea")
    game.join(q)
    assert game.snapshot(q)["world"]["radius"] == radius + 32
    assert game.chunk(0, 0) == original


def test_movement_is_normalized_bounded_and_server_controlled(game):
    p = player(game)
    game.join(p)
    before = game.snapshot(p)["self"]
    game.command(p, {"type": "input", "dx": 1, "dy": 1})
    game.step(0.05)
    after = game.snapshot(p)["self"]
    assert 0 < math.hypot(after["x"] - before["x"], after["y"] - before["y"]) <= 0.301
    with pytest.raises(ValueError):
        game.command(p, {"type": "input", "dx": float("nan"), "dy": 0})
    with pytest.raises(ValueError):
        game.command(p, {"type": "teleport", "x": 999999})


def test_transfer_is_balanced_idempotent_and_prevents_overdraft(game):
    p = player(game)
    q = player(game, "Bea")
    game.join(p)
    game.join(q)
    action = {"type": "transfer", "to": q, "amount": 25, "request_id": "transfer-1"}
    game.command(p, action)
    game.command(p, action)
    assert game.snapshot(p)["self"]["credits"] == 75
    assert game.snapshot(q)["self"]["credits"] == 125
    assert all(
        row["total"] == 0
        for row in game.db.execute("SELECT SUM(amount) total FROM ledger GROUP BY tx")
    )
    with pytest.raises(ValueError):
        game.command(p, {**action, "request_id": "transfer-2", "amount": 76})
    with pytest.raises(ValueError):
        game.command(p, {**action, "request_id": "transfer-3", "amount": 1.2})
    with pytest.raises(ValueError):
        game.command(p, {**action, "request_id": "transfer-1", "amount": 5})


def test_gather_build_and_experiment_persist_without_replay(tmp_path):
    path = tmp_path / "world.sqlite3"
    k = Kernel(path)
    p = player(k)
    k.join(p)
    action = {"type": "gather", "request_id": "gather-1"}
    result = k.command(p, action)
    resources = k.snapshot(p)["self"]["wood"]
    assert k.command(p, action) == result
    assert k.snapshot(p)["self"]["wood"] == resources
    k.positions[p] = {"x": 12.0, "y": 0.0}
    k.command(p, {"type": "build", "kind": "camp", "request_id": "build-1"})
    k.command(p, {"type": "research", "request_id": "research-1"})
    snap = k.snapshot(p)
    assert len(snap["buildings"]) == 1
    assert snap["self"]["wood"] < resources
    k.db.close()
    k = Kernel(path)
    assert len(k.snapshot(p)["buildings"]) == 1
    assert k.snapshot(p)["self"]["research"] == 1
    k.db.close()


def test_commons_cannot_be_blocked_and_trapped_players_can_return(game):
    p = player(game)
    game.join(p)
    with pytest.raises(ValueError, match="commons"):
        game.command(p, {"type": "build", "kind": "camp", "request_id": "grief-spawn"})
    game.positions[p] = {"x": 30.0, "y": 30.0}
    game.command(p, {"type": "home", "request_id": "escape"})
    assert game.snapshot(p)["self"]["x"] == 0
    assert game.snapshot(p)["self"]["y"] == 0


def test_samaritan_help_social_memory_and_explicit_diplomacy(game):
    p = player(game)
    game.join(p)
    help_reply = game.command(
        p,
        {
            "type": "talk",
            "npc": "mira",
            "text": "How can I help you?",
            "request_id": "talk-1",
        },
    )
    assert "soil" in help_reply["reply"].lower()
    social = game.command(
        p,
        {
            "type": "talk",
            "npc": "mira",
            "text": "How are you today?",
            "request_id": "talk-2",
        },
    )
    assert social["reply"] != help_reply["reply"]
    assert social["remembered"] >= 1
    assert game.snapshot(p)["self"]["reputation"] == 0
    game.command(p, {"type": "diplomacy", "npc": "mira", "request_id": "dip-1"})
    assert game.snapshot(p)["self"]["reputation"] == 1


def test_unjoined_and_invalid_inputs_cannot_mutate(game):
    p = player(game)
    with pytest.raises(ValueError):
        game.command(p, {"type": "gather", "request_id": "bad-1"})
    game.join(p)
    for text in ["", "x" * 1001]:
        with pytest.raises(ValueError):
            game.command(p, {"type": "chat", "text": text, "request_id": "chat-bad"})
    with pytest.raises(ValueError):
        game.chunk(1000000, 1000000)
