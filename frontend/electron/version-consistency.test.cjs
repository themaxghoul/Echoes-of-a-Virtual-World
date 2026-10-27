const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

test('client package, loading-screen metadata and server identify the same Alpha 36 build', () => {
  const root = path.join(__dirname, '..');
  const manifest = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));
  assert.equal(manifest.version, '0.3.0-alpha.36');
  const display = JSON.parse(fs.readFileSync(path.join(root, 'src', 'buildInfo.json'), 'utf8'));
  assert.equal(display.version, manifest.version);
  const serverApp = fs.readFileSync(path.join(root, '..', 'backend', 'persistent_world_app.py'), 'utf8');
  assert.equal(serverApp.match(/version="([^"]+)"/)[1], manifest.version);
});
