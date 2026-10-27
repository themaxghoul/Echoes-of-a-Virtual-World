const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

const ITERATIONS = 210000;

function normalizeIdentifier(value) { return String(value || '').trim().toLowerCase(); }
function passwordHash(password, salt) { return crypto.pbkdf2Sync(String(password || ''), salt, ITERATIONS, 32, 'sha256'); }

function createDesktopAuth(userDataPath, options = {}) {
  const authDir = path.join(userDataPath, 'identity');
  const authFile = path.join(authDir, 'accounts.json');
  const backupFile = path.join(authDir, 'accounts.backup.json');
  const temporary = path.join(authDir, 'accounts.tmp');
  const sessionSecretFile = path.join(authDir, 'session-secret');
  const ownerFile = path.join(authDir, 'owner.json');
  const lastSessionFile = path.join(authDir, 'last-session');
  fs.mkdirSync(authDir, { recursive: true });
  const configuredOwnerUsername = normalizeIdentifier(options.ownerUsername || 'luciferous');
  const configuredOwnerPassword = String(options.ownerPassword || '');

  function sessionSecret() {
    if (!fs.existsSync(sessionSecretFile)) fs.writeFileSync(sessionSecretFile, crypto.randomBytes(32), { mode: 0o600 });
    return fs.readFileSync(sessionSecretFile);
  }

  function ownerId() {
    try { return JSON.parse(fs.readFileSync(ownerFile, 'utf8')).user_id || null; } catch { return null; }
  }

  function matchesConfiguredOwnerPassword(suppliedPassword) {
    if (!configuredOwnerPassword) return false;
    const supplied = crypto.createHash('sha256').update(String(suppliedPassword || '')).digest();
    const configured = crypto.createHash('sha256').update(configuredOwnerPassword).digest();
    return crypto.timingSafeEqual(supplied, configured);
  }

  function bindConfiguredOwner(account, suppliedPassword) {
    const boundId = ownerId();
    if (boundId) return account.id === boundId;
    if (account.username !== configuredOwnerUsername) return false;
    // Existing alpha accounts may predate private owner provisioning. This
    // function is called only after the account password hash was verified by
    // authenticate(). When no separate bootstrap secret was configured, that
    // successful authentication may establish the one-time immutable UUID
    // binding. New registrations remain unable to claim the reserved name.
    if (configuredOwnerPassword && !matchesConfiguredOwnerPassword(suppliedPassword)) return false;
    fs.writeFileSync(ownerFile, JSON.stringify({ schema: 1, user_id: account.id }), { mode: 0o600, flag: 'wx' });
    return true;
  }

  function publicProfile(account) {
    const { password_hash, password_salt, ...profile } = account;
    const isOwner = account.id === ownerId();
    return {
      ...profile, is_owner: isOwner, permission_level: isOwner ? 'sirix_1' : (profile.permission_level || 'basic'),
      inspection_policy: isOwner ? 'null_read' : undefined,
      capabilities: isOwner ? ['creator', 'owner', 'administer_world', 'manage_users', 'jarvis'] : ['play'],
      auth_source: 'desktop_local',
    };
  }

  function readAccounts() {
    for (const candidate of [authFile, backupFile]) {
      try {
        const parsed = JSON.parse(fs.readFileSync(candidate, 'utf8'));
        if (parsed.schema === 1 && Array.isArray(parsed.accounts)) return parsed.accounts;
      } catch { /* Try the known-good backup. */ }
    }
    return [];
  }

  function writeAccounts(accounts) {
    const descriptor = fs.openSync(temporary, 'w');
    try {
      fs.writeFileSync(descriptor, JSON.stringify({ schema: 1, accounts }, null, 2), 'utf8');
      fs.fsyncSync(descriptor);
    } finally { fs.closeSync(descriptor); }
    if (fs.existsSync(authFile)) {
      fs.copyFileSync(authFile, backupFile);
      fs.unlinkSync(authFile);
    }
    fs.renameSync(temporary, authFile);
  }

  function authenticate(identifier, password) {
    const normalized = normalizeIdentifier(identifier);
    // sirix_1 was an early role label, never a durable account identity.  Do
    // not let a stale alpha account authenticate and inherit mismatched state.
    if (normalized === 'sirix_1') return null;
    const account = readAccounts().find((item) => item.username === normalized || item.email === normalized);
    if (!account) return null;
    const candidate = passwordHash(password, Buffer.from(account.password_salt, 'hex'));
    const expected = Buffer.from(account.password_hash, 'hex');
    if (candidate.length !== expected.length || !crypto.timingSafeEqual(candidate, expected)) return null;
    bindConfiguredOwner(account, password);
    return publicProfile(account);
  }

  function register(input) {
    const username = normalizeIdentifier(input?.username);
    const email = normalizeIdentifier(input?.email) || null;
    const displayName = String(input?.displayName || '').trim();
    const password = String(input?.password || '');
    if (!/^[a-z0-9_]{3,32}$/.test(username)) return { ok: false, error: 'Username must be 3-32 letters, numbers, or underscores' };
    if (username === 'sirix_1') return { ok: false, error: 'That retired username is unavailable' };
    if (username === configuredOwnerUsername && !matchesConfiguredOwnerPassword(password)) return { ok: false, error: 'That owner username is provisioned privately' };
    if (!displayName || displayName.length > 64) return { ok: false, error: 'Display name must be 1-64 characters' };
    if (password.length < 12) return { ok: false, error: 'Password must contain at least 12 characters' };
    if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return { ok: false, error: 'Email address is invalid' };
    const accounts = readAccounts();
    if (accounts.some((item) => item.username === username || (email && item.email === email))) return { ok: false, error: 'Username or email already exists' };
    const salt = crypto.randomBytes(16);
    const user = {
      id: crypto.randomUUID(), username, email, display_name: displayName,
      mailbox_address: `${username}@eov.local`, permission_level: 'basic', is_owner: false,
      is_transcendent: false, created_at: new Date().toISOString(),
      password_salt: salt.toString('hex'), password_hash: passwordHash(password, salt).toString('hex'),
    };
    accounts.push(user);
    writeAccounts(accounts);
    bindConfiguredOwner(user, password);
    return { ok: true, user: publicProfile(user), character: { id: `character-${user.id}`, name: username } };
  }

  function issueSession(user, ttlMs = 7 * 24 * 60 * 60 * 1000) {
    const payload = Buffer.from(JSON.stringify({ sub: user.id, exp: Date.now() + ttlMs, nonce: crypto.randomUUID() })).toString('base64url');
    const signature = crypto.createHmac('sha256', sessionSecret()).update(payload).digest('base64url');
    const token = `${payload}.${signature}`;
    fs.writeFileSync(lastSessionFile, token, { mode: 0o600 });
    return token;
  }

  function resumeSession(token) {
    try {
      const [payload, signature] = String(token || '').split('.');
      const expected = crypto.createHmac('sha256', sessionSecret()).update(payload).digest();
      const supplied = Buffer.from(signature, 'base64url');
      if (expected.length !== supplied.length || !crypto.timingSafeEqual(expected, supplied)) return null;
      const claims = JSON.parse(Buffer.from(payload, 'base64url').toString('utf8'));
      if (!claims.sub || claims.exp <= Date.now()) return null;
      const account = readAccounts().find((item) => item.id === claims.sub);
      return account ? publicProfile(account) : null;
    } catch { return null; }
  }

  function resumeLastSession() {
    try { return resumeSession(fs.readFileSync(lastSessionFile, 'utf8')); } catch { return null; }
  }

  function clearSession() {
    try { fs.unlinkSync(lastSessionFile); } catch { /* Already signed out. */ }
  }

  return { authenticate, register, issueSession, resumeSession, resumeLastSession, clearSession, authFile, ownerFile };
}

module.exports = { createDesktopAuth };
