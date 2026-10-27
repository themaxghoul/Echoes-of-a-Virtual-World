const test = require('node:test');
const assert = require('node:assert/strict');
const { scopedNamespace } = require('./storage-access.cjs');

test('storage identity is derived from the authenticated desktop user', () => {
  const user = { id: 'real-user-id', is_owner: false };
  assert.equal(scopedNamespace('world:forged-user-id', user), 'world--real-user-id');
  assert.equal(scopedNamespace('ledger', user), 'ledger--real-user-id');
});

test('Jarvis memory requires an authenticated owner', () => {
  assert.throws(() => scopedNamespace('jarvis', { id: 'player-id', is_owner: false }), /Owner session/);
  assert.equal(scopedNamespace('jarvis:anything', { id: 'owner-id', is_owner: true }), 'jarvis--owner-id');
  assert.throws(() => scopedNamespace('jarvis', null), /Authenticated desktop session/);
});
