const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const pagePath = path.join(__dirname, '..', '..', '..', 'docs', 'support', 'index.html');
const page = () => fs.readFileSync(pagePath, 'utf8');

test('public support page points at the matching Alpha 36 release assets', () => {
  const html = page();
  assert.match(html, /EoV-Alpha\\d\+-Windows-x64/);
  assert.match(html, /EoV-Alpha\\d\+-Persistent-Server/);
  assert.match(html, /EoV-Alpha\\d\+-SHA256/);
  assert.match(html, /browser_download_url/);
});

test('public support page describes playtest limits and does not claim an active checkout', () => {
  const html = page();
  assert.match(html, /self-hosted/i);
  assert.match(html, /playtest/i);
  assert.match(html, /not spendable|not enabled|not available/i);
  assert.match(html, /issues/);
  assert.doesNotMatch(html, /Donate now|Buy CU|Withdraw funds/i);
});

test('browser alpha and Alpha 36 desktop test are clearly separate playtest environments', () => {
  const html = page();
  assert.match(html, /Try the existing browser alpha/);
  assert.match(html, /do not share accounts, saves, or world state/i);
  assert.match(html, /self-hosted local services/i);
});

test('GitHub Pages publishes support beside the existing browser alpha', () => {
  const root = path.join(__dirname, '..', '..', '..');
  const workflow = fs.readFileSync(path.join(root, '.github', 'workflows', 'pages.yml'), 'utf8');
  assert.match(workflow, /cp -a docs\/play\/\. _site\//);
  assert.match(workflow, /cp -a docs\/support\/\. _site\/support\//);
  assert.match(workflow, /path: _site/);
});
