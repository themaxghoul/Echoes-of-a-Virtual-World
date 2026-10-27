import { test } from "node:test";
import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import { Kernel } from "../src/kernel.js";
import { template, validateSchematic } from "../../docs/play/schematics.js";

function setup() {
  const db = new DatabaseSync(":memory:");
  const storage = {
    exec(sql, ...args) {
      const s = db.prepare(sql);
      return s.columns().length ? s.all(...args) : (s.run(...args), []);
    },
    transactionSync(fn) {
      db.exec("BEGIN");
      try {
        const r = fn();
        db.exec("COMMIT");
        return r;
      } catch (e) {
        db.exec("ROLLBACK");
        throw e;
      }
    },
  };
  return { db, storage, k: new Kernel(storage) };
}
async function settler(k, name = "Crafter") {
  const { player } = await k.register(name, "a-long-test-password");
  k.join(player.id);
  const p = k.players.get(player.id);
  p.x = 30;
  p.y = 30;
  p.wood = 100;
  p.stone = 100;
  k.save(p);
  k.terrain = () => "meadow";
  return p;
}
const command = (k, p, data) =>
  k.command(p.id, { request_id: crypto.randomUUID(), ...data });

test("AI designs are bounded drafts, coalesce concurrent retries, and persist across restart", async () => {
  const { k, storage, db } = setup(),
    p = await settler(k);
  let calls = 0,
    release;
  const ai = {
    async run() {
      calls++;
      await new Promise((r) => (release = r));
      return {
        response: JSON.stringify({
          name: "Stone-legged bench",
          width: 4,
          depth: 2,
          height: 3,
          material: "stone",
          roof: "open",
        }),
      };
    },
  };
  const data = {
    kind: "workbench",
    prompt: "Long bench with stone legs",
    request_id: "design",
  };
  const first = k.crafting.generate(p.id, data, ai),
    second = k.crafting.generate(p.id, data, ai);
  release();
  const [a, b] = await Promise.all([first, second]);
  assert.deepEqual(a, b);
  assert.equal(calls, 1);
  assert.equal(a.source, "workers-ai");
  assert.equal(a.schematic.cost.stone, 8);
  assert.equal(k.buildings.length, 0);
  assert.deepEqual(
    await new Kernel(storage).crafting.generate(p.id, data, ai),
    a,
  );
  assert.equal(calls, 1);
  db.close();
});

test("invalid AI and exhausted budget retain procedural drafts without world changes", async () => {
  const { k, db } = setup(),
    p = await settler(k);
  let calls = 0;
  const ai = {
    async run() {
      calls++;
      return { response: { width: 999, depth: 2, height: 2 } };
    },
  };
  const a = await k.crafting.generate(
    p.id,
    { kind: "workbench", prompt: "bench", request_id: "bad" },
    ai,
  );
  assert.equal(a.source, "procedural");
  assert.equal(k.buildings.length, 0);
  k.storage.exec("UPDATE ai_budget SET used=50");
  const b = await k.crafting.generate(
    p.id,
    { kind: "structure", prompt: "hut", request_id: "capped" },
    ai,
  );
  assert.equal(b.source, "procedural");
  assert.equal(calls, 1);
  db.close();
});

test("failed material persistence rolls back construction and schematic geometry stays immutable", async () => {
  const { k, storage, db } = setup(),
    p = await settler(k);
  command(k, p, { type: "craft_planks", amount: 20 });
  const saved = command(k, p, {
    type: "save_schematic",
    schematic: template(),
  });
  const before = k.player(p.id),
    exec = storage.exec;
  storage.exec = (sql, ...args) => {
    if (sql.startsWith("INSERT INTO players")) throw Error("disk failure");
    return exec(sql, ...args);
  };
  assert.throws(
    () =>
      command(k, p, { type: "construct", schematic_id: saved.schematic.id }),
    /disk failure/,
  );
  assert.equal(k.buildings.length, 0);
  assert.deepEqual(k.player(p.id), before);
  assert.equal(exec("SELECT * FROM buildings").length, 0);
  storage.exec = exec;
  db.close();
});

test("custom workbench keeps a plank surface and supported legs; rejects floating/duplicate blocks", () => {
  const bench = template({ kind: "workbench", width: 3, depth: 2, height: 2 });
  assert.equal(validateSchematic(bench).cost.planks, 10);
  const broken = structuredClone(bench);
  broken.cells.pop();
  assert.throws(() => validateSchematic(broken), /surface|support/);
  assert.throws(
    () =>
      validateSchematic({ ...bench, cells: [...bench.cells, bench.cells[0]] }),
    /Duplicate/,
  );
  assert.throws(
    () =>
      validateSchematic({
        kind: "structure",
        name: "Floating",
        width: 2,
        depth: 2,
        height: 2,
        cells: [[0, 0, 1, "stone"]],
      }),
    /ground/,
  );
});

test("planks, saved workbenches and buildings conserve materials across replay and restart", async () => {
  const { k, storage, db } = setup(),
    p = await settler(k);
  const cut = { type: "craft_planks", amount: 10, request_id: "cut" };
  k.command(p.id, cut);
  k.command(p.id, cut);
  assert.equal(k.player(p.id).wood, 90);
  assert.equal(k.player(p.id).planks, 20);
  const saved = command(k, p, {
    type: "save_schematic",
    schematic: template({ kind: "workbench" }),
  });
  const build = {
    type: "construct",
    schematic_id: saved.schematic.id,
    request_id: "bench",
  };
  const result = k.command(p.id, build);
  k.command(p.id, build);
  assert.equal(k.buildings.length, 1);
  assert.equal(k.player(p.id).planks, 10);
  const restored = new Kernel(storage);
  assert.deepEqual(restored.command(p.id, build), result);
  assert.equal(restored.crafting.list(p.id)[0].id, saved.schematic.id);
  assert.equal(restored.buildings[0].schematic.kind, "workbench");
  db.close();
});

test("construction rejects foreign plans, missing benches, occupied footprint and insufficient materials atomically", async () => {
  const { k, db } = setup(),
    p = await settler(k),
    q = await settler(k, "Other");
  const saved = command(k, p, {
    type: "save_schematic",
    schematic: template({ kind: "structure" }),
  });
  assert.throws(
    () =>
      command(k, q, { type: "construct", schematic_id: saved.schematic.id }),
    /own/,
  );
  assert.throws(
    () =>
      command(k, p, { type: "construct", schematic_id: saved.schematic.id }),
    /workbench/,
  );
  const bench = command(k, p, {
    type: "save_schematic",
    schematic: template({ kind: "workbench" }),
  });
  const before = k.player(p.id);
  assert.throws(
    () =>
      command(k, p, { type: "construct", schematic_id: bench.schematic.id }),
    /materials/,
  );
  assert.deepEqual(k.player(p.id), before);
  command(k, p, { type: "craft_planks", amount: 50 });
  command(k, p, { type: "construct", schematic_id: bench.schematic.id });
  assert.throws(
    () =>
      command(k, p, { type: "construct", schematic_id: saved.schematic.id }),
    /occupied/,
  );
  k.players.get(p.id).y += 2;
  command(k, p, { type: "construct", schematic_id: saved.schematic.id });
  assert.equal(k.passable(32, 33), false);
  db.close();
});
