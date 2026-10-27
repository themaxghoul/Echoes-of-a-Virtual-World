const { test } = require('node:test');
const assert = require('node:assert/strict');
const { createCamera, projectPoint, tileAtPoint, visibleBounds, clampZoom } = require('./isometricCamera.cjs');

test('camera follows the visible player, including fractional movement', () => {
  const camera = createCamera(1000, 600, { x: 26.5, y: 19.25 }, 1.5);
  assert.deepEqual(projectPoint(camera, 26.5, 19.25), { x: 500, y: 300 });
  assert.deepEqual(projectPoint(camera, 27.5, 19.25), { x: 548, y: 324 });
});
test('clicks invert the rendered camera at every zoom, not the pending destination', () => {
  for (const zoom of [0.5, 1, 1.75]) {
    const camera = createCamera(640, 480, { x: 10, y: 8 }, zoom);
    assert.deepEqual(tileAtPoint(camera, 320 + 32 * zoom, 240 + 48 * zoom), { x: 12, y: 9 });
    assert.deepEqual(tileAtPoint(camera, 320, 240), { x: 10, y: 8 });
  }
});
test('zoom exposes more viewport, not more knowledge; bounds include all screen corners', () => {
  const bounds = visibleBounds(createCamera(1000, 600, { x: 32, y: 32 }, 0.5), 64);
  assert.ok(bounds.minX <= 0 && bounds.minY <= 0);
  assert.equal(bounds.maxX, 63);
  assert.equal(bounds.maxY, 63);
  assert.equal(clampZoom(-4), 0.5);
  assert.equal(clampZoom(6), 1.75);
  assert.equal(clampZoom(NaN), 1);
});
