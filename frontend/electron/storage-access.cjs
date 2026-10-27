const ALLOWED_BASES = new Set(['world', 'jarvis', 'ledger']);

function scopedNamespace(requested, user) {
  if (!user?.id) throw new Error('Authenticated desktop session required');
  const base = String(requested || '').split(':', 1)[0];
  if (!ALLOWED_BASES.has(base)) throw new Error('Unsupported save namespace');
  if (base === 'jarvis' && user.is_owner !== true) throw new Error('Owner session required for Jarvis memory');
  return `${base}--${user.id}`;
}

module.exports = { scopedNamespace };
