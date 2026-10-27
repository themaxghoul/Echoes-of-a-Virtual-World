const test = require('node:test');
const assert = require('node:assert/strict');
const { stepEntityMotion } = require('./entityMotion.cjs');

test('authoritative tile changes interpolate smoothly without changing the target state', () => {
  const first = stepEntityMotion(null, { x: 4, y: 6 }, 1000);
  assert.deepEqual(first.position, { x: 4, y: 6 });

  const moved = stepEntityMotion(first.motion, { x: 5, y: 6 }, 1000);
  assert.deepEqual(moved.position, { x: 4, y: 6 });
  const midpoint = stepEntityMotion(moved.motion, { x: 5, y: 6 }, 1250);
  assert.deepEqual(midpoint.position, { x: 4.5, y: 6 });
  assert.deepEqual(midpoint.motion.to, { x: 5, y: 6 });
});

test('a new authoritative step during animation continues from the current visual position', () => {
  const initial = stepEntityMotion(null, { x: 2, y: 2 }, 0);
  const firstStep = stepEntityMotion(initial.motion, { x: 3, y: 2 }, 0);
  const halfway = stepEntityMotion(firstStep.motion, { x: 3, y: 2 }, 250);
  const retargeted = stepEntityMotion(halfway.motion, { x: 3, y: 3 }, 250);
  assert.deepEqual(retargeted.position, halfway.position);
  assert.deepEqual(retargeted.motion.to, { x: 3, y: 3 });
});
