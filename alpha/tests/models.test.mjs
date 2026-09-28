import { test } from "node:test";
import assert from "node:assert/strict";
import {
  modelFor,
  groundColor,
  drawModel,
  previewProjection,
} from "../../docs/play/models.js";
import { template } from "../../docs/play/schematics.js";

test("both projections consume identical seeded models and all design sizes fit the preview", () => {
  const tree = { kind: "tree", x: -3, y: 7 };
  assert.deepEqual(modelFor(tree, 4), modelFor({ ...tree }, 4));
  assert.equal(
    groundColor("forest", -3, 7, 4),
    groundColor("forest", -2.9, 7.2, 4),
  );
  for (const kind of ["workbench", "structure"])
    for (let width = 2; width <= 4; width++)
      for (let depth = 2; depth <= 4; depth++)
        for (let height = 2; height <= 4; height++) {
          const d = template({ kind, width, depth, height }),
            unit = kind === "workbench" ? 0.25 : 1,
            p = previewProjection(d);
          for (const x of [0, width * unit])
            for (const y of [0, depth * unit])
              for (const z of [0, height * unit]) {
                const v = p(x, y, z);
                assert.ok(v.x >= 15 && v.x <= 345 && v.y >= 15 && v.y <= 215);
              }
        }
});
test("near-plane clipping retains the visible part of a block crossing the camera", () => {
  const points = [];
  const ctx = {
    beginPath() {},
    closePath() {},
    fill() {},
    stroke() {},
    moveTo(x, y) {
      points.push([x, y]);
    },
    lineTo(x, y) {
      points.push([x, y]);
    },
  };
  const projection = (x, y, z) => ({
    x: 100 + (x / Math.max(y, 0.1)) * 100,
    y: 100 - (z / Math.max(y, 0.1)) * 100,
    depth: y,
  });
  projection.near = 0.1;
  drawModel(
    ctx,
    [{ x: 0, y: -0.5, z: 0, w: 1, d: 1, h: 1, color: "#fff" }],
    { x: 0, y: 0 },
    projection,
  );
  assert.ok(points.length > 0);
  assert.ok(points.every((p) => p.every(Number.isFinite)));
});
