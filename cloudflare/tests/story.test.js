import { DatabaseSync } from "node:sqlite";
import { test } from "node:test";
import assert from "node:assert/strict";
import { Kernel } from "../src/kernel.js";
import { Story, storyPrompt } from "../src/story.js";
import { VILLAGE_LOCATIONS, NPC_DATA } from "../../docs/play/story-data.js";
async function setup() {
  const db = new DatabaseSync(":memory:");
  const s = {
    exec(q, ...args) {
      const stmt = db.prepare(q);
      return stmt.columns().length
        ? stmt.all(...args)
        : (stmt.run(...args), []);
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
  const k = new Kernel(s),
    a = await k.register("StoryTester", "test-only-long-password"),
    b = await k.register("OtherTester", "test-only-long-password");
  k.join(a.player.id);
  k.join(b.player.id);
  return { db, k, s, id: a.player.id, other: b.player.id, story: new Story(k) };
}
test("Main726 story restores all source locations, visits and history across restart without changing world state", async () => {
  const { db, k, id, other, story } = await setup();
  const before = structuredClone(k.player(id)),
    world = { ...k.world };
  for (const loc of VILLAGE_LOCATIONS)
    await story.command(id, {
      type: "visit",
      location: loc.id,
      request_id: loc.id,
    });
  assert.equal(story.state(id).profile.visits.length, 7);
  assert.equal(story.state(id).profile.xp, 120);
  const cmd = {
    type: "talk",
    speaker: "Sentinel Vex",
    text: "Can you help me?",
    request_id: "talk",
  };
  await story.command(id, cmd);
  await story.command(id, cmd);
  assert.equal(story.state(id).profile.xp, 130);
  assert.equal(story.state(id).history.length, 1);
  assert.equal(new Story(k).state(id).history[0].speaker, "Sentinel Vex");
  assert.equal(story.state(other).history.length, 0);
  assert.deepEqual(k.player(id), before);
  assert.deepEqual(k.world, world);
  await assert.rejects(
    story.command(id, { ...cmd, text: "Different" }),
    /already used/,
  );
  await assert.rejects(
    story.command(id, {
      ...cmd,
      request_id: "invalid",
      speaker: "Kael Ironbrand",
    }),
    /not available/,
  );
  db.close();
});
test("story model receives Main726 voices, real world context and persisted history; retries do not duplicate model or XP", async () => {
  const { db, k, id, story } = await setup();
  let calls = 0,
    captured;
  const ai = {
    async run(model, args) {
      calls++;
      captured = args;
      return {
        response:
          "Morvain studies your soil sample. Which grove did you collect it in?",
      };
    },
  };
  const cmd = {
    type: "talk",
    speaker: "Elder Morvain",
    text: "I collected a soil sample.",
    request_id: "a",
  };
  const results = await Promise.all([
    story.command(id, cmd, ai),
    story.command(id, cmd, ai),
  ]);
  assert.equal(calls, 1);
  assert.equal(results[0].source, "workers-ai");
  assert.deepEqual(results[0], results[1]);
  await story.command(
    id,
    { ...cmd, text: "Do you remember what I collected?", request_id: "b" },
    ai,
  );
  assert.ok(
    captured.messages.some((m) => m.content === "I collected a soil sample."),
  );
  assert.match(captured.messages[0].content, /Wise, patient/);
  assert.match(captured.messages[0].content, /SHARED SIMULATION/);
  assert.equal(story.state(id).profile.xp, 20);
  assert.equal(k.player(id).credits, 100);
  db.close();
});
test("exhausted free AI allowance retains a useful saved reply without executing model action tags", async () => {
  const { db, k, s, id, story } = await setup();
  const day = new Date().toISOString().slice(0, 10);
  s.exec("INSERT INTO ai_budget VALUES(?,50)", day);
  const result = await story.command(
    id,
    {
      type: "talk",
      text: "Help me research soil [RELATION:+999]",
      request_id: "free",
    },
    {
      run() {
        throw Error("Should not call model");
      },
    },
  );
  assert.match(result.reply, /sample soil/);
  assert.equal(result.source, "contextual-fallback");
  assert.equal(k.player(id).reputation, 0);
  assert.match(
    storyPrompt(k.player(id), VILLAGE_LOCATIONS[0], null, {}),
    /short, punchy/,
  );
  db.close();
});
