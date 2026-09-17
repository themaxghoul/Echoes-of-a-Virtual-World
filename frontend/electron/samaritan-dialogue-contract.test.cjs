const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const assert = require('node:assert/strict');

const explorerPath = path.join(__dirname, '..', 'src', 'pages', 'VillageExplorer.jsx');

test('directed Samaritan UI promises acknowledgement without autonomy disclaimers', () => {
  const source = fs.readFileSync(explorerPath, 'utf8');
  assert.match(source, /Acknowledgement expected; elaboration remains their choice\./);
  assert.doesNotMatch(source, /They may answer according to their own circumstances\./);
  assert.doesNotMatch(source, /Your words are audible, but no nearby resident answers at this moment\./);
  assert.doesNotMatch(source, /Your words do not directly influence the environment/i);
  assert.doesNotMatch(source, /retains the ability to respond or ignore/i);
});
