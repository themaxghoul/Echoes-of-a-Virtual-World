let localUrl = '';
try { localUrl = JSON.parse(localStorage.getItem('eov-game-settings'))?.worldServerUrl || ''; } catch { localUrl = ''; }
const desktopDefaultUrl = window.eovDesktop ? 'http://127.0.0.1:8765' : '';
const { serverAddress } = require('./serverAddress.cjs');
const configuredUrl = serverAddress(localUrl, process.env.REACT_APP_WORLD_SERVER_URL || desktopDefaultUrl);
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

export async function fetchWorldHealth(signal) {
  if (!configuredUrl) throw new Error('No persistent world server configured');
  const response = await fetch(`${configuredUrl}/health`, { signal, cache: 'no-store' });
  if (!response.ok) throw new Error(`World health check returned ${response.status}`);
  return response.json();
}

export async function fetchWorldEvents(worldId = defaultWorldId, after = 0, signal) {
  const response = await fetch(`${configuredUrl}/worlds/${encodeURIComponent(worldId)}/events?after=${after}`, { signal, cache: 'no-store', headers: authenticatedHeaders() });
  if (!response.ok) throw new Error(`Event replay returned ${response.status}`);
  return response.json();
}

export async function submitWorldAction(action, expectedRevision, worldId = defaultWorldId) {
  const actionId = crypto.randomUUID();
  const send = (revision) => fetch(`${configuredUrl}/worlds/${encodeURIComponent(worldId)}/actions`, {
    method: 'POST', headers: authenticatedHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ action_id: actionId, expected_revision: revision, action }),
  });
  let response = await send(expectedRevision);
  let errorPayload = null;
  if (response.status === 409) {
    errorPayload = await response.clone().json().catch(() => null);
    if (/^expected revision \d+, current \d+$/.test(String(errorPayload?.detail || ''))) {
      const latestSnapshot = await fetchWorldSnapshot(worldId);
      response = await send(latestSnapshot.revision);
      errorPayload = null;
    }
  }
  if (!response.ok) {
    const rejection = errorPayload || await response.json().catch(() => ({}));
    throw new Error(rejection.detail || `Action rejected with ${response.status}`);
  }
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
