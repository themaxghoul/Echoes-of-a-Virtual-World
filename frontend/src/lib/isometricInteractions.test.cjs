const test = require('node:test');
const assert = require('node:assert/strict');

let interactions = {};
try {
  interactions = require('./isometricInteractions.cjs');
} catch {
  // The assertions below describe the missing behavior during the red phase.
}

test('one tile exposes every stocked item and collocated resource site independently', () => {
  const resources = [
    { id: 'tool-counter', type: 'store', name: 'Tool counter', x: 4, y: 6, stock: { axe: 1, bucket: 2, seed: 8 } },
    { id: 'oak-4-6', type: 'tree', name: 'Oak stand', x: 4, y: 6, stock: 5 },
    { id: 'ridge-4-6', type: 'mineral', name: 'Exposed seam', x: 4, y: 6, stock: 3 },
  ];

  const options = interactions.resourceInteractionOptions?.(resources, { x: 4, y: 6 }, {}, 10) || [];

  assert.deepEqual(
    options.map((option) => [option.siteId, option.operation, option.item || null]),
    [
      ['tool-counter', 'checkout', 'axe'],
      ['tool-counter', 'checkout', 'bucket'],
      ['tool-counter', 'checkout', 'seed'],
      ['oak-4-6', 'chop', null],
      ['ridge-4-6', 'mine', null],
    ],
  );
});

test('collecting one store item does not suppress other stocked choices', () => {
  const resources = [
    { id: 'tool-counter', type: 'store', name: 'Tool counter', x: 2, y: 3, stock: { axe: 1, pick: 1, bucket: 0 } },
  ];

  const options = interactions.resourceInteractionOptions?.(resources, { x: 2, y: 3 }, { axe: 1 }, 10) || [];

  assert.deepEqual(options.map((option) => option.item), ['axe', 'pick']);
});

test('fallback checkout conserves the selected item quantity', () => {
  const site = { id: 'tool-counter', type: 'store', stock: { seed: 8, axe: 1 } };
  const inventory = { seed: 4 };

  const result = interactions.checkoutLocalStoreItem?.(site, inventory, 'seed', 4) || { accepted: false };

  assert.equal(result.accepted, true);
  assert.deepEqual(result.outputs, { seed: 4 });
  assert.equal(site.stock.seed, 4);
  assert.equal(inventory.seed, 8);
  assert.equal(site.stock.axe, 1);
});

test('fallback social dialogue does not repeat an off-shift work reason as the answer', () => {
  const resident = {
    id: 'ada',
    name: 'Ada',
    intention: 'rest',
    reason: 'The scheduled shift ended.',
    task: { label: 'Off shift', reason: 'The scheduled shift ended.' },
    memories: [],
  };

  const reply = interactions.fallbackNpcReply?.(resident, 'I would like to socialize and share an idea with you.') || '';

  assert.notEqual(reply, 'The scheduled shift ended.');
  assert.doesNotMatch(reply, /trying to rest/i);
  assert.match(reply, /talk|listen|conversation/i);
});

test('teaching dialogue records epistemic limits instead of granting expertise', () => {
  const resident = { id: 'ada', name: 'Ada', task: { label: 'Rest', reason: 'The scheduled shift ended.' }, memories: [] };

  const reply = interactions.fallbackNpcReply?.(resident, 'Can I teach you a new algorithm?') || '';

  assert.match(reply, /evidence|practice|demonstrat/i);
  assert.doesNotMatch(reply, /now i know|learned instantly|mastered/i);
});

test('resource selection chooses the nearest known passable approach tile', () => {
  const site = { id: 'oak', x: 7, y: 7 };
  const observed = {
    '6,7': { passable: true },
    '8,7': { passable: false },
    '7,6': { passable: true },
    '7,8': { passable: true },
  };

  const approach = interactions.approachTileForSite?.(site, { x: 4, y: 6 }, observed, 64);

  assert.deepEqual(approach, { x: 7, y: 6 });
});

test('resource action receipt names gains, remaining energy, and custody', () => {
  const receipt = interactions.formatResourceReceipt?.({
    accepted: true,
    operation: 'chop',
    outputs: { timber: 2 },
    energy: 91,
  }, 'Old oak');

  assert.deepEqual(receipt, {
    tone: 'success',
    text: 'Old oak · chop complete · timber +2 · energy 91 · output held in your inventory',
  });
});

test('failed resource action receipt preserves the authoritative blocker', () => {
  const receipt = interactions.formatResourceReceipt?.({ accepted: false, reason: 'an axe is required' }, 'Old oak');

  assert.deepEqual(receipt, { tone: 'blocked', text: 'Old oak · blocked · an axe is required' });
});
