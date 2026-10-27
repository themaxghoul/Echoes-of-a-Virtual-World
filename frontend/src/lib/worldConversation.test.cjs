const { test } = require('node:test');
const assert = require('node:assert/strict');
const { nearbyResidents, speechAction, mergeMessages } = require('./worldConversation.cjs');
const snapshot = { viewer_id: 'real-player', state: {
  players: { 'real-player': { location: [8, 9], current_region: 'settlement' } },
  npcs: {
    ada: { id: 'ada', name: 'Ada', location: [8, 8] },
    orin: { id: 'orin', name: 'Orin', location: [9, 9] },
    remote: { id: 'remote', location: [8, 9], current_region: 'forest' },
    distant: { id: 'distant', location: [30, 30] },
  },
} };
test('both views address a real nearby listener by default using the authenticated viewer', () => {
  assert.deepEqual(nearbyResidents(snapshot).map(r => r.id), ['ada', 'orin']);
  assert.deepEqual(speechAction(snapshot, '  Hello  '), { type: 'speak', content: 'Hello', target_id: 'ada' });
  assert.equal(speechAction(snapshot, 'Hello', 'orin').target_id, 'orin');
});
test('stale recipients and absent listeners do not invent a conversation', () => {
  assert.throws(() => speechAction(snapshot, 'Hello', 'remote'), /no longer within hearing/i);
  assert.throws(() => speechAction({ state: {} }, 'Hello'), /nobody.*hear/i);
  assert.throws(() => speechAction(snapshot, '  '), /message/i);
});
test('polling cannot duplicate immediate speech replies or lose earlier messages', () => {
  const first = { id: '1', speaker: 'Ada', content: 'Hello' };
  const second = { id: '2', speaker: 'Orin', content: 'Yes?' };
  assert.deepEqual(mergeMessages([first], [first, second]), [first, second]);
});
