"""Authoritative single-process world; all durable mutations use SQLite transactions.

No client-supplied positions, balances, permissions, or AI-generated commands are trusted.
Coordinates are in tiles. Persisted seed + coordinates determine terrain independently
of map size. The public service must run with exactly one worker.
"""

import hashlib
import hmac
import json
import math
from pathlib import Path
import re
import secrets
import sqlite3
import time
import uuid

from alpha.samaritans import SAMARITANS, respond


class Kernel:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
          CREATE TABLE IF NOT EXISTS world(id INTEGER PRIMARY KEY CHECK(id=1), seed INTEGER NOT NULL, radius INTEGER NOT NULL);
          INSERT OR IGNORE INTO world VALUES(1, 738291, 512);
          CREATE TABLE IF NOT EXISTS players(id TEXT PRIMARY KEY, name TEXT UNIQUE COLLATE NOCASE, salt TEXT, password_hash TEXT,
            x REAL DEFAULT 0, y REAL DEFAULT 0, wood INTEGER DEFAULT 20, stone INTEGER DEFAULT 10,
            food INTEGER DEFAULT 5, research INTEGER DEFAULT 0, reputation INTEGER DEFAULT 0,
            last_gather REAL DEFAULT 0, last_research REAL DEFAULT 0);
          CREATE TABLE IF NOT EXISTS sessions(hash TEXT PRIMARY KEY, player TEXT REFERENCES players(id), expires REAL);
          CREATE TABLE IF NOT EXISTS members(player TEXT PRIMARY KEY REFERENCES players(id));
          CREATE TABLE IF NOT EXISTS ledger(id INTEGER PRIMARY KEY, tx TEXT, account TEXT, amount INTEGER NOT NULL, reason TEXT, created REAL);
          CREATE INDEX IF NOT EXISTS ledger_account ON ledger(account);
          CREATE TABLE IF NOT EXISTS requests(player TEXT, key TEXT, payload TEXT, result TEXT, PRIMARY KEY(player,key));
          CREATE TABLE IF NOT EXISTS buildings(id TEXT PRIMARY KEY, owner TEXT REFERENCES players(id), kind TEXT, x INTEGER, y INTEGER, UNIQUE(x,y));
          CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY, sender TEXT, name TEXT, text TEXT, created REAL);
          CREATE TABLE IF NOT EXISTS conversations(id INTEGER PRIMARY KEY, player TEXT, npc TEXT, text TEXT, reply TEXT, created REAL);
          CREATE TABLE IF NOT EXISTS relations(player TEXT, npc TEXT, PRIMARY KEY(player,npc));
        """)
        self.db.commit()
        self.seed = self.db.execute("SELECT seed FROM world").fetchone()[0]
        self.inputs = {}
        self.online = set()
        self.elapsed = 0.0
        self.flush_elapsed = 0.0
        self.positions = {}

    @staticmethod
    def password_hash(password, salt):
        return hashlib.scrypt(
            password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1
        ).hex()

    def register(self, name, password):
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_-]{3,24}", name):
            raise ValueError(
                "Use 3–24 letters, numbers, underscores or hyphens for your name."
            )
        if not isinstance(password, str) or not 12 <= len(password) <= 128:
            raise ValueError("Use a password between 12 and 128 characters.")
        pid, salt = str(uuid.uuid4()), secrets.token_hex(16)
        hashed = self.password_hash(password, salt)
        try:
            with self.db:
                self.db.execute(
                    "INSERT INTO players(id,name,salt,password_hash) VALUES(?,?,?,?)",
                    (pid, name, salt, hashed),
                )
        except sqlite3.IntegrityError:
            raise ValueError("That name is already registered.") from None
        return self.session(pid)

    def login(self, name, password):
        if (
            not isinstance(name, str)
            or not isinstance(password, str)
            or len(password) > 128
        ):
            raise ValueError("Invalid name or password.")
        row = self.db.execute("SELECT * FROM players WHERE name=?", (name,)).fetchone()
        salt = row["salt"] if row else "00" * 16
        hashed = self.password_hash(password, salt)
        if not row or not hmac.compare_digest(hashed, row["password_hash"]):
            raise ValueError("Invalid name or password.")
        return self.session(row["id"])

    def session(self, pid):
        token = secrets.token_urlsafe(32)
        with self.db:
            self.db.execute("DELETE FROM sessions WHERE expires < ?", (time.time(),))
            self.db.execute(
                "INSERT INTO sessions VALUES(?,?,?)",
                (
                    hashlib.sha256(token.encode()).hexdigest(),
                    pid,
                    time.time() + 30 * 86400,
                ),
            )
        return {"token": token, "player": self.player(pid)}

    def authenticate(self, token):
        if not isinstance(token, str) or len(token) > 128:
            raise ValueError("Session expired. Please log in.")
        row = self.db.execute(
            "SELECT player FROM sessions WHERE hash=? AND expires>?",
            (hashlib.sha256(token.encode()).hexdigest(), time.time()),
        ).fetchone()
        if not row:
            raise ValueError("Session expired. Please log in.")
        return row["player"]

    def logout(self, token):
        with self.db:
            self.db.execute(
                "DELETE FROM sessions WHERE hash=?",
                (hashlib.sha256(token.encode()).hexdigest(),),
            )

    def player(self, pid):
        row = self.db.execute(
            "SELECT id,name,x,y,wood,stone,food,research,reputation FROM players WHERE id=?",
            (pid,),
        ).fetchone()
        if not row:
            raise ValueError("Player not found.")
        result = dict(row)
        result.update(self.positions.get(pid, {}))
        result["credits"] = self.balance(pid)
        return result

    def balance(self, pid):
        return self.db.execute(
            "SELECT COALESCE(SUM(amount),0) FROM ledger WHERE account=?", (pid,)
        ).fetchone()[0]

    def post(self, debit, credit, amount, reason):
        tx = str(uuid.uuid4())
        self.db.executemany(
            "INSERT INTO ledger(tx,account,amount,reason,created) VALUES(?,?,?,?,?)",
            [
                (tx, debit, -amount, reason, time.time()),
                (tx, credit, amount, reason, time.time()),
            ],
        )

    def join(self, pid):
        self.player(pid)
        with self.db:
            new = self.db.execute(
                "INSERT OR IGNORE INTO members VALUES(?)", (pid,)
            ).rowcount
            if new:
                self.db.execute("UPDATE world SET radius=radius+32")
                self.post(
                    "system:issuance", pid, 100, "Alpha starter credits; no cash value"
                )
        return self.snapshot(pid)

    def terrain(self, x, y):
        x, y = math.floor(x), math.floor(y)
        if abs(x) < 10 and abs(y) < 10:
            return "meadow"
        # Coarse coordinate noise produces navigable lakes/woods, without allocating the world.
        digest = hashlib.blake2s(
            f"{self.seed}:{x//6}:{y//6}".encode(), digest_size=4
        ).digest()
        n = int.from_bytes(digest, "little") % 100
        return (
            "water" if n < 9 else "rock" if n < 17 else "forest" if n < 47 else "meadow"
        )

    def chunk(self, cx, cy):
        if type(cx) is not int or type(cy) is not int:
            raise ValueError("Chunk coordinates must be integers.")
        radius = self.db.execute("SELECT radius FROM world").fetchone()[0]
        if abs(cx * 16) > radius + 16 or abs(cy * 16) > radius + 16:
            raise ValueError("This land is beyond the current frontier.")
        return {
            "cx": cx,
            "cy": cy,
            "size": 16,
            "tiles": [
                self.terrain(cx * 16 + x, cy * 16 + y)
                for y in range(16)
                for x in range(16)
            ],
        }

    def passable(self, x, y):
        radius = self.db.execute("SELECT radius FROM world").fetchone()[0]
        if abs(x) >= radius or abs(y) >= radius or self.terrain(x, y) == "water":
            return False
        return not self.db.execute(
            "SELECT 1 FROM buildings WHERE x=? AND y=?", (math.floor(x), math.floor(y))
        ).fetchone()

    def step(self, dt):
        dt = max(0, min(float(dt), 0.1))
        self.elapsed += dt
        self.flush_elapsed += dt
        now = time.monotonic()
        for pid, (dx, dy, stamp) in list(self.inputs.items()):
            if now - stamp > 0.3:
                continue
            p = self.positions.get(pid)
            if p is None:
                row = self.player(pid)
                p = self.positions[pid] = {"x": row["x"], "y": row["y"]}
            length = max(1, math.hypot(dx, dy))
            speed = 4 if self.terrain(p["x"], p["y"]) == "forest" else 6
            x, y = p["x"] + dx / length * speed * dt, p["y"] + dy / length * speed * dt
            if self.passable(x, p["y"]):
                p["x"] = x
            if self.passable(p["x"], y):
                p["y"] = y
        if self.flush_elapsed >= 1:
            self.flush()
            self.flush_elapsed = 0

    def flush(self):
        with self.db:
            self.db.executemany(
                "UPDATE players SET x=?,y=? WHERE id=?",
                [(p["x"], p["y"], pid) for pid, p in self.positions.items()],
            )

    def disconnect(self, pid):
        self.inputs.pop(pid, None)
        self.online.discard(pid)
        self.flush()

    def npcs(self):
        # Autonomous work routes derive from wall clock so restart does not reset their day.
        phase = time.time() / 35
        return [
            {
                **n,
                "x": n["home"][0] + math.sin(phase + i) * 2,
                "y": n["home"][1] + math.cos(phase + i) * 2,
                "activity": n["activities"][
                    int(time.time() / 60 + i) % len(n["activities"])
                ],
            }
            for i, n in enumerate(SAMARITANS)
        ]

    def snapshot(self, pid):
        p = self.player(pid)
        world = dict(self.db.execute("SELECT seed,radius FROM world").fetchone())
        world["members"] = self.db.execute("SELECT COUNT(*) FROM members").fetchone()[0]
        return {
            "type": "snapshot",
            "world": world,
            "self": p,
            "players": [
                self.player(q)
                for q in self.online
                if q != pid
                and math.hypot(
                    self.player(q)["x"] - p["x"], self.player(q)["y"] - p["y"]
                )
                < 80
            ],
            "npcs": self.npcs(),
            "buildings": [
                dict(r)
                for r in self.db.execute(
                    "SELECT * FROM buildings WHERE x BETWEEN ? AND ? AND y BETWEEN ? AND ?",
                    (p["x"] - 80, p["x"] + 80, p["y"] - 80, p["y"] + 80),
                )
            ],
            "messages": [
                dict(r)
                for r in reversed(
                    self.db.execute(
                        "SELECT * FROM messages ORDER BY id DESC LIMIT 40"
                    ).fetchall()
                )
            ],
        }

    def command(self, pid, data):
        if (
            not isinstance(data, dict)
            or not self.db.execute(
                "SELECT 1 FROM members WHERE player=?", (pid,)
            ).fetchone()
        ):
            raise ValueError("Join the world first.")
        kind = data.get("type")
        if kind == "input":
            dx, dy = data.get("dx", 0), data.get("dy", 0)
            if any(
                type(v) not in (int, float) or not math.isfinite(v) or abs(v) > 1
                for v in (dx, dy)
            ):
                raise ValueError("Invalid movement input.")
            self.inputs[pid] = (dx, dy, time.monotonic())
            return {"ok": True}
        if kind not in (
            "gather",
            "build",
            "research",
            "transfer",
            "chat",
            "talk",
            "diplomacy",
            "home",
        ):
            raise ValueError("Unknown command.")
        key = data.get("request_id")
        if not isinstance(key, str) or not 1 <= len(key) <= 80:
            raise ValueError("A unique request_id is required.")
        payload = json.dumps(data, sort_keys=True, allow_nan=False)
        with self.db:
            previous = self.db.execute(
                "SELECT payload,result FROM requests WHERE player=? AND key=?",
                (pid, key),
            ).fetchone()
            if previous:
                if previous["payload"] != payload:
                    raise ValueError("Request ID already used for a different action.")
                return json.loads(previous["result"])
            result = self.act(pid, data)
            self.db.execute(
                "INSERT INTO requests VALUES(?,?,?,?)",
                (pid, key, payload, json.dumps(result)),
            )
            return result

    def act(self, pid, data):
        p = self.player(pid)
        kind = data["type"]
        if kind == "home":
            self.inputs.pop(pid, None)
            self.positions[pid] = {"x": 0.0, "y": 0.0}
            self.db.execute("UPDATE players SET x=0,y=0 WHERE id=?", (pid,))
            return {
                "ok": True,
                "reply": "Returned to the protected commons. Your settlement remains where you built it.",
            }
        if kind == "transfer":
            amount, recipient = data.get("amount"), data.get("to")
            if (
                type(amount) is not int
                or not 1 <= amount <= 1000000
                or recipient == pid
            ):
                raise ValueError("Transfer a positive whole number to another player.")
            if (
                not isinstance(recipient, str)
                or not self.db.execute(
                    "SELECT 1 FROM members WHERE player=?", (recipient,)
                ).fetchone()
            ):
                raise ValueError("Recipient has not joined this world.")
            if self.balance(pid) < amount:
                raise ValueError("Insufficient credits.")
            self.post(pid, recipient, amount, "Player transfer; no cash value")
            return {"ok": True, "reply": f"Transferred {amount} experimental credits."}
        if kind == "gather":
            last = self.db.execute(
                "SELECT last_gather FROM players WHERE id=?", (pid,)
            ).fetchone()[0]
            if time.time() - last < 3:
                raise ValueError("Rest a moment: gathering takes three seconds.")
            terrain = self.terrain(p["x"], p["y"])
            resource = (
                "wood"
                if terrain == "forest"
                else "stone" if terrain == "rock" else "food"
            )
            self.db.execute(
                f"UPDATE players SET {resource}={resource}+2,last_gather=? WHERE id=?",
                (time.time(), pid),
            )
            return {"ok": True, "reply": f"Gathered 2 {resource} from {terrain}."}
        if kind == "build":
            building = data.get("kind")
            costs = {"camp": (8, 2), "farm": (10, 4), "lab": (16, 10)}
            if building not in costs:
                raise ValueError("Choose camp, farm or lab.")
            wood, stone = costs[building]
            if p["wood"] < wood or p["stone"] < stone:
                raise ValueError(f"A {building} needs {wood} wood and {stone} stone.")
            x, y = math.floor(p["x"]) + 1, math.floor(p["y"])
            if abs(x) < 10 and abs(y) < 10:
                raise ValueError(
                    "The commons is protected. Build at least 10 tiles from its center."
                )
            if not self.passable(x, y) or any(
                math.floor(q["x"]) == x and math.floor(q["y"]) == y
                for q in [self.player(qid) for qid in self.online]
            ):
                raise ValueError(
                    "The tile east of you is occupied or blocked. Move to a clear site."
                )
            self.db.execute(
                "INSERT INTO buildings VALUES(?,?,?,?,?)",
                (str(uuid.uuid4()), pid, building, x, y),
            )
            self.db.execute(
                "UPDATE players SET wood=wood-?,stone=stone-? WHERE id=?",
                (wood, stone, pid),
            )
            return {"ok": True, "reply": f"Built a {building} at {x}, {y}."}
        if kind == "research":
            last = self.db.execute(
                "SELECT last_research FROM players WHERE id=?", (pid,)
            ).fetchone()[0]
            if time.time() - last < 10:
                raise ValueError("Record your previous sample first; wait ten seconds.")
            if p["food"] < 1:
                raise ValueError(
                    "Gather food before conducting another field experiment."
                )
            terrain = self.terrain(p["x"], p["y"])
            moisture = {"meadow": 45, "forest": 70, "rock": 15, "water": 100}[terrain]
            self.db.execute(
                "UPDATE players SET research=research+1,food=food-1,last_research=? WHERE id=?",
                (time.time(), pid),
            )
            self.post("system:research", pid, 2, "Field research reward")
            return {
                "ok": True,
                "reply": f"Soil sample: {terrain}, modeled moisture {moisture}%. Hypothesis: forest soil retains more water than exposed rock. +1 research, +2 alpha credits. This is a simplified model, not measured science.",
            }
        if kind == "diplomacy":
            npc = self.npc(data.get("npc"))
            if self.db.execute(
                "SELECT 1 FROM relations WHERE player=? AND npc=?", (pid, npc["id"])
            ).fetchone():
                return {
                    "ok": True,
                    "reply": f'Your cooperation agreement with {npc["name"]} is already recorded.',
                }
            self.db.execute("INSERT INTO relations VALUES(?,?)", (pid, npc["id"]))
            self.db.execute(
                "UPDATE players SET reputation=reputation+1 WHERE id=?", (pid,)
            )
            return {
                "ok": True,
                "reply": f'{npc["name"]} agrees to peaceful knowledge sharing. +1 reputation. No resources or authority were transferred.',
            }
        text = data.get("text")
        if not isinstance(text, str) or not 1 <= len(text.strip()) <= 1000:
            raise ValueError("Write a message between 1 and 1000 characters.")
        text = text.strip()
        if kind == "chat":
            self.db.execute(
                "INSERT INTO messages(sender,name,text,created) VALUES(?,?,?,?)",
                (pid, p["name"], text, time.time()),
            )
            return {"ok": True, "reply": "Message sent to world chat."}
        npc = self.npc(data.get("npc"))
        history = [
            dict(r)
            for r in self.db.execute(
                "SELECT text,reply FROM conversations WHERE player=? AND npc=? ORDER BY id DESC LIMIT 6",
                (pid, npc["id"]),
            )
        ]
        reply = respond(npc, p, text, history)
        self.db.execute(
            "INSERT INTO conversations(player,npc,text,reply,created) VALUES(?,?,?,?,?)",
            (pid, npc["id"], text, reply, time.time()),
        )
        return {
            "ok": True,
            "reply": reply,
            "npc": npc["name"],
            "remembered": len(history),
            "dialogue": "contextual-rules",
        }

    def npc(self, npc_id):
        for npc in self.npcs():
            if npc["id"] == npc_id:
                return npc
        raise ValueError("Choose a Samaritan to speak with.")

    def ledger(self, pid):
        return [
            dict(r)
            for r in self.db.execute(
                "SELECT tx,amount,reason,created FROM ledger WHERE account=? ORDER BY id DESC LIMIT 100",
                (pid,),
            )
        ]
