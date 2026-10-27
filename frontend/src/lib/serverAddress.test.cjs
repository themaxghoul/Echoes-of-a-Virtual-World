const { test } = require('node:test');
const assert = require('node:assert/strict');
const { serverAddress } = require('./serverAddress.cjs');
test('player connection settings override bundled development addresses and preserve ports', () => {
  assert.equal(serverAddress(' http://example.test:8765/ ', 'http://localhost:1'), 'http://example.test:8765');
  assert.equal(serverAddress('', 'https://world.test'), 'https://world.test');
  assert.equal(serverAddress('', ''), '');
});
