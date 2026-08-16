let localUrl = '';
try { localUrl = JSON.parse(localStorage.getItem('eov-game-settings'))?.worldServerUrl || ''; } catch { localUrl = ''; }
const configuredUrl = (process.env.REACT_APP_WORLD_SERVER_URL || localUrl).trim().replace(/\/$/, '');
export const worldServerUrl = configuredUrl;
export const worldServerConfigured = Boolean(configuredUrl);
export const defaultWorldId = 'founders-settlement';

function authenticatedHeaders(extra = {}) {
  const token = sessionStorage.getItem('eovAccessToken');
  return { ...extra, ...(token ? { Authorization: `Bearer ${token}` } : {}) };
}

export async function fetchWorldSnapshot(worldId = defaultWorldId, signal) {
  if (!configuredUrl) throw new Error('No persistent world server configured');
  const response = await fetch(`${configuredUrl}/worlds/${encodeURIComponent(worldId)}`, { signal, cache: 'no-store', headers: authenticatedHeaders() });
  if (!response.ok) throw new Error(`World server returned ${response.status}`);
  return response.json();
}

export async function fetchWorldEvents(worldId = defaultWorldId, after = 0, signal) {
  const response = await fetch(`${configuredUrl}/worlds/${encodeURIComponent(worldId)}/events?after=${after}`, { signal, cache: 'no-store', headers: authenticatedHeaders() });
  if (!response.ok) throw new Error(`Event replay returned ${response.status}`);
  return response.json();
}

export async function submitWorldAction(action, expectedRevision, worldId = defaultWorldId) {
  const response = await fetch(`${configuredUrl}/worlds/${encodeURIComponent(worldId)}/actions`, {
    method: 'POST', headers: authenticatedHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ action_id: crypto.randomUUID(), expected_revision: expectedRevision, action }),
  });
  if (!response.ok) throw new Error((await response.json()).detail || `Action rejected with ${response.status}`);
  return response.json();
}

export async function submitOwnerDirective(directive, expectedRevision, worldId = defaultWorldId) {
  const response = await fetch(`${configuredUrl}/worlds/${encodeURIComponent(worldId)}/owner-directives`, {
    method: 'POST', headers: authenticatedHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ action_id: crypto.randomUUID(), expected_revision: expectedRevision, ...directive }),
  });
  if (!response.ok) throw new Error((await response.json()).detail || `Owner directive rejected with ${response.status}`);
  return response.json();
}
