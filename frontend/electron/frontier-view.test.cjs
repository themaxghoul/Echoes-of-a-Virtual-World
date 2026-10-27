const test = require('node:test');
const assert = require('node:assert/strict');
const { projectObservedFrontier } = require('../src/lib/frontierView.cjs');

test('projects observed terrain and routes without hidden substrate', () => {
  const snapshot = {
    revision: 41,
    state: {
      frontier: { size: 64 },
      observed_tiles: {
        '8,9': { position: [8, 9], terrain: 'grassland', elevation: 1, passable: true, visibility: 'surface' },
        '9,9': { position: [9, 9], terrain: 'rocky', elevation: 2, passable: true, visibility: 'surveyed', excavation_depth_cm: 40, prepared_foundation: true, substrate: [{ material: 'iron_ore', stock: 3 }] },
      },
      players: { alice: { id: 'alice', location: [8, 9], route: { status: 'traveling', path: [[8, 9], [9, 9]], index: 0 } } },
      npcs: {},
      resource_sites: {},
    },
  };

  const view = projectObservedFrontier(snapshot, 'alice');

  assert.equal(view.size, 64);
  assert.equal(view.revision, 41);
  assert.equal(view.tiles['9,9'].excavationDepthCm, 40);
  assert.equal(view.tiles['9,9'].preparedFoundation, true);
  assert.equal(Object.hasOwn(view.tiles['9,9'], 'substrate'), false);
  assert.deepEqual(view.route.remaining, [[9, 9]]);
});

test('returns a disconnected empty frontier for an unusable snapshot', () => {
  assert.deepEqual(projectObservedFrontier(null, 'alice'), { connected: false, size: 64, revision: null, tiles: {}, actors: [], route: null });
});
