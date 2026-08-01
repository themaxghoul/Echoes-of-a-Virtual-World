const crypto = require('node:crypto');

const OWNER_USERNAME = 'sirix_1';
const OWNER_SALT = Buffer.from('d10dc6625dec0316cb1ad76fa1552b56', 'hex');
const OWNER_HASH = Buffer.from('b807d0f17f8324aa68cff84918ece5f1406f228e610431aa6e00fec3feb3c9ce', 'hex');

function authenticateOwner(identifier, password) {
  const normalized = String(identifier || '').trim().toLowerCase();
  if (normalized !== OWNER_USERNAME) return null;
  const candidate = crypto.pbkdf2Sync(String(password || ''), OWNER_SALT, 210000, OWNER_HASH.length, 'sha256');
  if (!crypto.timingSafeEqual(candidate, OWNER_HASH)) return null;
  return {
    id: 'sirix_1_desktop_owner',
    username: OWNER_USERNAME,
    display_name: 'Sirix-1',
    permission_level: 'sirix_1',
    is_transcendent: true,
    auth_source: 'desktop_test_owner',
  };
}

module.exports = { authenticateOwner };
