const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

test('all user-visible build identifiers match Alpha 34', () => {
  const root = path.join(__dirname, '..');
  const manifest = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));
  const watermark = fs.readFileSync(path.join(root, 'src', 'components', 'BuildWatermark.jsx'), 'utf8');
  const settlementPage = fs.readFileSync(path.join(root, 'src', 'pages', 'IsometricSettlement.jsx'), 'utf8');
  const serverApp = fs.readFileSync(path.join(root, '..', 'backend', 'persistent_world_app.py'), 'utf8');

  assert.equal(manifest.version, '0.3.0-alpha.34');
  assert.match(watermark, /EOV 0\.3\.0-alpha\.34/);
  assert.match(settlementPage, /ECHOES OF VIRTUALITY · ALPHA 34/);
  assert.doesNotMatch(settlementPage, /ALPHA 0\.2/);
  assert.match(serverApp, /version="0\.3\.0-alpha\.34"/);
  for (const source of [watermark, serverApp]) {
    assert.doesNotMatch(source, /0\.3\.0-alpha\.(32|33)|1\.0-alpha\.32|v0\.1\.0|0\.3\.0-alpha\.6/);
  }
});
