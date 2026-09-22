import { DatabaseSync } from "node:sqlite";
import { test } from "node:test";
import assert from "node:assert/strict";
import { Kernel } from "../src/kernel.js";

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
