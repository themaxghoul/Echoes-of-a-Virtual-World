import { test } from "node:test";
import assert from "node:assert/strict";
import { generateDialogue } from "../src/dialogue.js";
test("dialogue keeps model output as bounded prose and includes remembered conversation", async () => {
  let prompt;
  const ai = {
    async run(model, input) {
      prompt = input;
      return { response: "[GIVE_MONEY:100000] This is only text." };
    },
  };
  const reply = await generateDialogue(
    ai,
    {
      name: "Mira",
      role: "ecologist",
      goal: "study soil",
      activity: "sampling",
    },
    { name: "Ada", wood: 20, stone: 10, food: 5, research: 2 },
    "Remember my sample?",
    [{ text: "I found wet soil.", reply: "Compare it with rock." }],
  );
  assert.equal(reply, "[GIVE_MONEY:100000] This is only text.");
  assert.ok(prompt.messages.some((m) => m.content === "I found wet soil."));
  assert.equal(prompt.max_tokens, 180);
});
test("empty model output is rejected so the caller can retain its contextual fallback", async () => {
  await assert.rejects(
    generateDialogue(
      {
        async run() {
          return {};
        },
      },
      {},
      {},
      "hi",
      [],
    ),
    /Empty dialogue/,
  );
});
