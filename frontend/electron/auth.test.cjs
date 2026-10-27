const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { createDesktopAuth } = require('./auth.cjs');

test('registers and authenticates a durable local account without storing plaintext', () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'eov-auth-'));
  try {
    const auth = createDesktopAuth(directory);
    const registered = auth.register({ username: 'New_Citizen', email: 'citizen@example.test', displayName: 'New Citizen', password: 'correct horse battery' });
    assert.equal(registered.ok, true);
    assert.equal(registered.user.username, 'new_citizen');
    assert.equal(registered.user.mailbox_address, 'new_citizen@eov.local');
    const source = fs.readFileSync(auth.authFile, 'utf8');
    assert.equal(source.includes('correct horse battery'), false);
    const reopened = createDesktopAuth(directory);
    assert.equal(reopened.authenticate('citizen@example.test', 'correct horse battery').id, registered.user.id);
    assert.equal(reopened.authenticate('new_citizen', 'wrong password'), null);
    const token = reopened.issueSession(registered.user, 60_000);
    assert.equal(reopened.resumeSession(token).id, registered.user.id);
    assert.equal(createDesktopAuth(directory).resumeLastSession().id, registered.user.id);
    assert.equal(reopened.resumeSession(`${token}tampered`), null);
    reopened.clearSession();
    assert.equal(reopened.resumeLastSession(), null);
  } finally { fs.rmSync(directory, { recursive: true, force: true }); }
});

test('Luciferous is owner-authorized only after password authentication', () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'eov-auth-'));
  try {
    const auth = createDesktopAuth(directory, { ownerUsername: 'luciferous', ownerPassword: 'private owner password' });
    const registered = auth.register({ username: 'Luciferous', displayName: 'Luciferous', password: 'private owner password' });
    assert.equal(registered.ok, true);
    assert.equal(registered.user.is_owner, true);
    assert.equal(registered.user.permission_level, 'sirix_1');
    assert.equal(auth.authenticate('luciferous', 'wrong password'), null);
    assert.equal(auth.authenticate('luciferous', 'private owner password').is_owner, true);
    assert.equal(fs.readFileSync(auth.authFile, 'utf8').includes('private owner password'), false);
  } finally { fs.rmSync(directory, { recursive: true, force: true }); }
});

test('owner identity cannot be claimed by username alone', () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'eov-auth-'));
  try {
    const auth = createDesktopAuth(directory, { ownerUsername: 'luciferous', ownerPassword: 'private owner password' });
    const impersonation = auth.register({ username: 'Luciferous', displayName: 'Impostor', password: 'different long password' });
    assert.equal(impersonation.ok, false);
    assert.equal(fs.existsSync(auth.ownerFile), false);
  } finally { fs.rmSync(directory, { recursive: true, force: true }); }
});

test('an existing reserved Luciferous account binds only after its password is verified', () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'eov-auth-'));
  try {
    // Simulate an account created by an older alpha before Luciferous became
    // the reserved local owner identity.
    const legacyAuth = createDesktopAuth(directory, { ownerUsername: 'different_reserved_owner' });
    const legacy = legacyAuth.register({ username: 'Luciferous', displayName: 'Legacy Luciferous', password: 'private legacy password' });
    assert.equal(legacy.ok, true);
    assert.equal(legacy.user.is_owner, false);
    assert.equal(fs.existsSync(legacyAuth.ownerFile), false);

    const upgraded = createDesktopAuth(directory, { ownerUsername: 'luciferous' });
    assert.equal(upgraded.authenticate('luciferous', 'incorrect password'), null);
    assert.equal(fs.existsSync(upgraded.ownerFile), false);
    const authenticated = upgraded.authenticate('luciferous', 'private legacy password');
    assert.equal(authenticated.id, legacy.user.id);
    assert.equal(authenticated.is_owner, true);
    assert.equal(authenticated.permission_level, 'sirix_1');
    assert.equal(JSON.parse(fs.readFileSync(upgraded.ownerFile, 'utf8')).user_id, legacy.user.id);

    const reopened = createDesktopAuth(directory, { ownerUsername: 'luciferous' });
    assert.equal(reopened.authenticate('luciferous', 'private legacy password').is_owner, true);
  } finally { fs.rmSync(directory, { recursive: true, force: true }); }
});

test('owner authority follows the bound UUID instead of the username', () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'eov-auth-'));
  try {
    const auth = createDesktopAuth(directory, { ownerUsername: 'luciferous', ownerPassword: 'private owner password' });
    const registered = auth.register({ username: 'Luciferous', displayName: 'Luciferous', password: 'private owner password' });
    const document = JSON.parse(fs.readFileSync(auth.authFile, 'utf8'));
    document.accounts[0].username = 'renamed_owner';
    fs.writeFileSync(auth.authFile, JSON.stringify(document));
    const renamed = auth.authenticate('renamed_owner', 'private owner password');
    assert.equal(renamed.id, registered.user.id);
    assert.equal(renamed.is_owner, true);
    assert.equal(renamed.permission_level, 'sirix_1');
  } finally { fs.rmSync(directory, { recursive: true, force: true }); }
});

test('rejects weak, duplicate, and reserved registration', () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'eov-auth-'));
  try {
    const auth = createDesktopAuth(directory);
    assert.equal(auth.register({ username: 'sirix_1', displayName: 'Fake', password: 'long enough password' }).ok, false);
    assert.equal(auth.register({ username: 'luciferous', displayName: 'Fake Owner', password: 'long enough password' }).ok, false);
    assert.equal(auth.register({ username: 'valid_user', displayName: 'Valid', password: 'short' }).ok, false);
    assert.equal(auth.register({ username: 'valid_user', displayName: 'Valid', password: 'long enough password' }).ok, true);
    assert.equal(auth.register({ username: 'valid_user', displayName: 'Other', password: 'another valid password' }).ok, false);
  } finally { fs.rmSync(directory, { recursive: true, force: true }); }
});

test('retired sirix_1 account data cannot authenticate as a player identity', () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'eov-auth-'));
  try {
    const legacy = createDesktopAuth(directory, { ownerUsername: 'different_owner' });
    const registered = legacy.register({ username: 'legacy_user', displayName: 'Legacy', password: 'long enough password' });
    const document = JSON.parse(fs.readFileSync(legacy.authFile, 'utf8'));
    document.accounts[0].username = 'sirix_1';
    fs.writeFileSync(legacy.authFile, JSON.stringify(document));
    const current = createDesktopAuth(directory);
    assert.equal(current.authenticate('sirix_1', 'long enough password'), null);
    assert.ok(registered.user.id);
  } finally { fs.rmSync(directory, { recursive: true, force: true }); }
});
