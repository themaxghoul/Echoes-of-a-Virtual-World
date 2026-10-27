const test = require('node:test');
const assert = require('node:assert/strict');

const { applyAuthenticatedIdentity } = require('./sessionState.cjs');

function storage() {
  const values = new Map();
  return {
    setItem(key, value) { values.set(key, String(value)); },
    getItem(key) { return values.get(key) ?? null; },
    removeItem(key) { values.delete(key); },
    values,
  };
}

test('desktop identity keeps the server session and server-bound actor id', () => {
  const local = storage();
  const session = storage();
  applyAuthenticatedIdentity({
    localStorage: local,
    sessionStorage: session,
    user: { id: 'desktop-id', username: 'luciferous', display_name: 'Luciferous', permission_level: 'sirix_1', is_owner: true },
    character: { id: 'character-desktop-id', name: 'luciferous' },
    desktopToken: 'desktop-token',
    networkToken: 'server-token',
    networkUserId: 'server-bound-uuid',
  });

  assert.equal(session.getItem('eovDesktopAccessToken'), 'desktop-token');
  assert.equal(session.getItem('eovAccessToken'), 'server-token');
  assert.equal(local.getItem('eovNetworkUserId'), 'server-bound-uuid');
  assert.equal(local.getItem('userId'), 'desktop-id');
});

test('resume does not erase a still-valid server session', () => {
  const local = storage();
  const session = storage();
  session.setItem('eovAccessToken', 'server-token');
  local.setItem('eovNetworkUserId', 'server-bound-uuid');

  applyAuthenticatedIdentity({
    localStorage: local,
    sessionStorage: session,
    user: { id: 'desktop-id', username: 'luciferous', display_name: 'Luciferous', permission_level: 'sirix_1', is_owner: true },
    character: { id: 'character-desktop-id', name: 'luciferous' },
    desktopToken: 'desktop-token',
  });

  assert.equal(session.getItem('eovAccessToken'), 'server-token');
  assert.equal(local.getItem('eovNetworkUserId'), 'server-bound-uuid');
});
