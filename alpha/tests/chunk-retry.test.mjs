import test from "node:test";
import assert from "node:assert/strict";
import { ChunkRetry } from "../../docs/play/chunk-retry.js";

test("failed terrain requests pause through snapshots and resume at their deadline", () => {
  const retry = new ChunkRetry();
  retry.failed("1,0", { retryAt: 100000 }, 1000);
  for (let now = 1000; now < 100000; now += 100)
    assert.equal(retry.ready("1,0", now), false);
  assert.equal(retry.ready("0,0", 2000), true);
  assert.equal(retry.ready("1,0", 100000), true);
  retry.succeeded("1,0");
  assert.equal(retry.ready("1,0", 100001), true);
});

test("transient terrain failures back off instead of retrying every snapshot", () => {
  const retry = new ChunkRetry();
  retry.failed("0,0", new Error("network"), 1000);
  assert.equal(retry.ready("0,0", 1099), false);
  assert.equal(retry.ready("0,0", 9000), true);
  retry.failed("0,0", new Error("network"), 9000);
  assert.equal(retry.ready("0,0", 20000), false);
  assert.equal(retry.ready("0,0", 25000), true);
});
