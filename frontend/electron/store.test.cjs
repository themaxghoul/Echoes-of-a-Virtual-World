const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const { createStore } = require('./store.cjs');

test('increments revisions and reads the latest valid payload', () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'eov-store-'));
  const store = createStore(directory);
  assert.equal(store.write('world', { tick: 1 }).revision, 1);
  assert.equal(store.write('world', { tick: 2 }).revision, 2);
  assert.deepEqual(store.read('world').payload, { tick: 2 });
});

test('recovers the prior snapshot when the live save is corrupt', () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'eov-recovery-'));
  const store = createStore(directory);
  store.write('world', { tick: 1 });
  store.write('world', { tick: 2 });
  fs.writeFileSync(path.join(directory, 'saves', 'world.json'), '{broken', 'utf8');
  const recovered = store.read('world');
  assert.equal(recovered.recovered, true);
  assert.deepEqual(recovered.payload, { tick: 1 });
});

test('rejects unexpected storage namespaces', () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'eov-namespace-'));
  assert.throws(() => createStore(directory).write('../escape', {}), /Unsupported save namespace/);
});
