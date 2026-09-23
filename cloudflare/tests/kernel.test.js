import { DatabaseSync } from "node:sqlite";
import { test } from "node:test";
import assert from "node:assert/strict";
import { Kernel } from "../src/kernel.js";
import { deriveSeed } from "../src/possibilities.js";

function storage() {
  const db = new DatabaseSync(":memory:");
  return {
    db,
    exec(query, ...args) {
      const statement = db.prepare(query);
      return statement.columns().length
        ? statement.all(...args)
        : (statement.run(...args), []);
    },
    transactionSync(fn) {
      db.exec("BEGIN");
      try {
        const result = fn();
        db.exec("COMMIT");
        return result;
      } catch (e) {
        db.exec("ROLLBACK");
        throw e;
      }
    },
  };
}
async function user(k, name) {
  const session = await k.register(name, "a-long-test-password");
  return { id: await k.authenticate(session.token), token: session.token };
}

test("Workers AI parsed-object decisions use the same action validation as text JSON", async () => {
  const s = storage(),
    k = new Kernel(s);
  const result = await k.agents.cycle(
    {
      async run() {
        return {
          response: {
            action: "reflect",
            goal: "compare meadow samples",
            intention: "Consider evidence.",
          },
        };
      },
    },
    Date.now(),
  );
  assert.equal(result.status, "applied");
  assert.equal(
    k.npcs().find((n) => n.id === result.agent).goal,
    "compare meadow samples",
  );
  s.db.close();
});

test("instantiated terrain survives a generator change and exposes hierarchical provenance", () => {
  const s = storage(),
    k = new Kernel(s);
  const chunk = k.chunk(-2, 3);
  assert.equal(typeof chunk.seed, "string");
  assert.equal(chunk.path.length, 4);
  assert.deepEqual(
    chunk.path.map((n) => n.kind),
    ["world", "region", "settlement", "parcel"],
  );
  const restarted = new Kernel(s);
  restarted.possibilities.generator = {
    generatePossibility() {
      throw Error("must not reroll saved land");
    },
  };
  assert.deepEqual(restarted.chunk(-2, 3), chunk);
  assert.equal(restarted.terrain(-32, 48), chunk.tiles[0]);
  s.db.close();
});

test("hierarchical seeds are order independent and negative parcels remain distinct", () => {
  const s = storage(),
    k = new Kernel(s);
  const a = k.chunk(-1, 0),
    b = k.chunk(0, 0);
  assert.notEqual(a.seed, b.seed);
  assert.equal(a.path[1].key.includes("region:-1,0"), true);
  assert.equal(
    deriveSeed(a.seed, "room", "main"),
    deriveSeed(a.seed, "room", "main"),
  );
  assert.notEqual(
    deriveSeed(a.seed, "room", "main"),
    deriveSeed(a.seed, "object", "main"),
  );
  const s2 = storage(),
    k2 = new Kernel(s2);
  k2.chunk(0, 0);
  assert.deepEqual(k2.chunk(-1, 0), a);
  s.db.close();
  s2.db.close();
});

test("terrain generation stops at its shared budget while saved terrain stays readable", () => {
  const s = storage(),
    k = new Kernel(s),
    saved = k.chunk(0, 0);
  s.exec("UPDATE generation_budget SET used=1000");
  assert.throws(() => k.chunk(1, 1), /generation allowance/);
  assert.deepEqual(new Kernel(s).chunk(0, 0), saved);
  s.db.close();
});

test("an exhausted generation allowance does not stop other settlers moving", async () => {
  const s = storage(),
    k = new Kernel(s),
    a = await user(k, "Ada"),
    b = await user(k, "Bea");
  k.join(a.id);
  k.join(b.id);
  k.chunk(0, 0);
  k.players.get(a.id).x = 15.99;
  s.exec("UPDATE generation_budget SET used=1000");
  for (const u of [a, b]) k.command(u.id, { type: "input", dx: 1, dy: 0 });
  assert.doesNotThrow(() => k.step(0.1));
  assert.ok(k.player(b.id).x > 0);
  assert.match(k.snapshot(a.id).notice, /generation allowance/);
  s.db.close();
});

test("a restarted inference is marked interrupted without duplicate consequences", async () => {
  const s = storage(),
    k = new Kernel(s),
    now = Math.floor(Date.now() / 7200000) * 7200000 + 1000;
  s.exec(
    "INSERT INTO agent_cycles VALUES(?,?,?,?,?)",
    String(Math.floor(now / 7200000)),
    "mira",
    "pending",
    JSON.stringify({ perception: {} }),
    now,
  );
  const restarted = new Kernel(s);
  await restarted.agents.cycle(null, now + 60000);
  assert.equal(
    s.exec("SELECT status FROM agent_cycles")[0].status,
    "interrupted",
  );
  assert.equal(restarted.npcs().find((n) => n.id === "mira").resources.food, 0);
  s.db.close();
});

test("agent consequences roll back when their journal write fails", async () => {
  const s = storage(),
    k = new Kernel(s),
    exec = s.exec.bind(s);
  s.exec = (sql, ...args) => {
    if (sql.startsWith("UPDATE agent_cycles SET status='applied'"))
      throw Error("disk busy");
    return exec(sql, ...args);
  };
  const result = await k.agents.cycle(
    {
      async run() {
        return {
          response:
            '{"action":"gather","goal":"sample food","intention":"Collect."}',
        };
      },
    },
    Date.now(),
  );
  assert.equal(result.status, "rejected");
  assert.equal(k.npcs().find((n) => n.id === result.agent).resources.food, 0);
  assert.equal(s.exec("SELECT * FROM ecosystem").length, 0);
  assert.equal(
    new Kernel(s).npcs().find((n) => n.id === result.agent).resources.food,
    0,
  );
  s.db.close();
});

test("conversations arriving during reasoning survive the committed action", async () => {
  const s = storage(),
    k = new Kernel(s);
  const result = await k.agents.cycle(
    {
      async run() {
        k.agents.remember(
          "mira",
          "talk:concurrent",
          "Ada asked about forest samples.",
        );
        return {
          response:
            '{"action":"reflect","goal":"compare samples","intention":"Consider the evidence."}',
        };
      },
    },
    Date.now(),
  );
  assert.equal(result.status, "applied");
  assert.equal(
    new Kernel(s).agents.states
      .get("mira")
      .memory.some((m) => m.event === "talk:concurrent"),
    true,
  );
  s.db.close();
});

test("agent decisions persist consequences once and do not grant player money", async () => {
  const s = storage(),
    k = new Kernel(s);
  const a = await user(k, "Ada");
  k.join(a.id);
  const credits = k.player(a.id).credits;
  const ai = {
    async run() {
      return {
        response: JSON.stringify({
          action: "gather",
          goal: "study food availability",
          intention: "Collect a sample.",
        }),
      };
    },
  };
  const now = Date.now();
  const result = await k.agents.cycle(ai, now);
  assert.equal(result.status, "applied");
  const agent = k.npcs().find((n) => n.id === result.agent);
  assert.equal(agent.resources.food, 2);
  const restarted = new Kernel(s);
  assert.deepEqual(
    restarted.npcs().find((n) => n.id === agent.id),
    agent,
  );
  assert.equal((await restarted.agents.cycle(ai, now)).status, "waiting");
  assert.equal(restarted.player(a.id).credits, credits);
  assert.equal(
    s.exec("SELECT * FROM agent_cycles WHERE status='applied'").length,
    1,
  );
  s.db.close();
});

test("invalid model actions are rejected without changing world or inventory", async () => {
  const s = storage(),
    k = new Kernel(s),
    before = k.world.radius;
  const ai = {
    async run() {
      return {
        response:
          '{"action":"transfer","amount":100000,"goal":"own everything","intention":"take it"}',
      };
    },
  };
  const result = await k.agents.cycle(ai, Date.now());
  assert.equal(result.status, "rejected");
  assert.equal(k.world.radius, before);
  assert.equal(s.exec("SELECT * FROM ledger").length, 0);
  s.db.close();
});

test("ecosystem harvest is shared, finite, retry safe and persistent", async () => {
  const s = storage(),
    k = new Kernel(s);
  const a = await user(k, "Ada");
  k.join(a.id);
  for (let i = 0; i < 6; i++) {
    k.players.get(a.id).lastGather = 0;
    k.command(a.id, { type: "gather", request_id: `harvest-${i}` });
  }
  k.players.get(a.id).lastGather = 0;
  assert.throws(
    () => k.command(a.id, { type: "gather", request_id: "depleted" }),
    /depleted/,
  );
  const restarted = new Kernel(s);
  assert.throws(
    () => restarted.command(a.id, { type: "gather", request_id: "depleted" }),
    /depleted|three seconds/,
  );
  assert.equal(restarted.player(a.id).food, 17);
  s.db.close();
});

test("failed position batch retries every rolled-back player", async () => {
  const s = storage(),
    k = new Kernel(s);
  const a = await user(k, "Ada"),
    b = await user(k, "Bea");
  k.join(a.id);
  k.join(b.id);
  for (const id of [a.id, b.id]) k.command(id, { type: "input", dx: 1, dy: 0 });
  k.step(0.05);
  const exec = s.exec.bind(s);
  let writes = 0;
  s.exec = (query, ...args) => {
    if (query.startsWith("INSERT INTO players") && ++writes === 2)
      throw Error("disk busy");
    return exec(query, ...args);
  };
  assert.throws(() => k.flush(), /disk busy/);
  assert.equal(k.dirty.size, 2);
  s.exec = exec;
  k.flush();
  const restarted = new Kernel(s);
  for (const id of [a.id, b.id])
    assert.equal(restarted.players.get(id).x, k.players.get(id).x);
  s.db.close();
});

test("free runtime retains sessions, seed, membership and ledger across eviction", async () => {
  const s = storage(),
    k = new Kernel(s);
  const a = await user(k, "Ada");
  k.join(a.id);
  const before = k.snapshot(a.id),
    chunk = k.chunk(0, 0);
  k.join(a.id);
  assert.equal(k.snapshot(a.id).self.credits, 100);
  const b = await user(k, "Bea");
  k.join(b.id);
  assert.equal(k.snapshot(a.id).world.radius, before.world.radius + 32);
  assert.deepEqual(k.chunk(0, 0), chunk);
  const restarted = new Kernel(s);
  assert.equal(await restarted.authenticate(a.token), a.id);
  assert.equal(restarted.snapshot(a.id).self.credits, 100);
  s.db.close();
});
test("atomic replay-safe ledger rejects conflicts and overdrafts", async () => {
  const s = storage(),
    k = new Kernel(s),
    a = await user(k, "Ada"),
    b = await user(k, "Bea");
  k.join(a.id);
  k.join(b.id);
  const cmd = { type: "transfer", to: b.id, amount: 75, request_id: "one" };
  k.command(a.id, cmd);
  k.command(a.id, cmd);
  assert.equal(k.snapshot(a.id).self.credits, 25);
  assert.equal(k.snapshot(b.id).self.credits, 175);
  assert.throws(() => k.command(a.id, { ...cmd, amount: 1 }), /used/);
  assert.throws(
    () => k.command(a.id, { ...cmd, request_id: "two" }),
    /Insufficient/,
  );
  assert.throws(() =>
    k.command(a.id, { ...cmd, amount: 1.5, request_id: "float" }),
  );
  assert.ok(
    s
      .exec("SELECT SUM(amount) total FROM ledger GROUP BY tx")
      .every((r) => r.total === 0),
  );
  s.db.close();
});
test("server controls movement, protects commons and provides escape", async () => {
  const s = storage(),
    k = new Kernel(s),
    a = await user(k, "Ada");
  k.join(a.id);
  assert.throws(
    () => k.command(a.id, { type: "build", kind: "camp", request_id: "spawn" }),
    /commons/,
  );
  assert.throws(() => k.command(a.id, { type: "input", dx: NaN, dy: 0 }));
  assert.throws(() =>
    k.command(a.id, { type: "teleport", x: 1000, request_id: "bad" }),
  );
  k.command(a.id, { type: "input", dx: 1, dy: 1 });
  k.step(0.05);
  const p = k.snapshot(a.id).self;
  assert.ok(Math.hypot(p.x, p.y) <= 0.301 && p.x > 0);
  k.command(a.id, { type: "home", request_id: "escape" });
  assert.equal(k.snapshot(a.id).self.x, 0);
  s.db.close();
});
test("dialogue remembers players but only explicit diplomacy changes reputation", async () => {
  const s = storage(),
    k = new Kernel(s),
    a = await user(k, "Ada");
  k.join(a.id);
  const reply = k.command(a.id, {
    type: "talk",
    npc: "mira",
    text: "How can I help you?",
    request_id: "talk",
  });
  assert.match(reply.reply, /soil/);
  const memory = k.command(a.id, {
    type: "talk",
    npc: "mira",
    text: "Do you remember me?",
    request_id: "memory",
  });
  assert.match(memory.reply, /How can I help you/);
  assert.equal(k.snapshot(a.id).self.reputation, 0);
  k.command(a.id, { type: "diplomacy", npc: "mira", request_id: "peace" });
  k.command(a.id, { type: "diplomacy", npc: "mira", request_id: "peace2" });
  assert.equal(k.snapshot(a.id).self.reputation, 1);
  s.db.close();
});
test("gather/research cannot duplicate rewards and position writes are batched", async () => {
  const s = storage(),
    k = new Kernel(s),
    a = await user(k, "Ada");
  k.join(a.id);
  const cmd = { type: "gather", request_id: "food" };
  k.command(a.id, cmd);
  k.command(a.id, cmd);
  assert.equal(k.snapshot(a.id).self.food, 7);
  k.command(a.id, { type: "research", request_id: "sample" });
  assert.throws(
    () => k.command(a.id, { type: "research", request_id: "sample2" }),
    /ten seconds/,
  );
  assert.equal(k.snapshot(a.id).self.research, 1);
  k.command(a.id, { type: "input", dx: 1, dy: 0 });
  k.step(0.05);
  k.flush();
  const fresh = new Kernel(s);
  assert.ok(fresh.snapshot(a.id).self.x > 0);
  s.db.close();
});
