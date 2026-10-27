const { serverAddress } = require('./serverAddress.cjs');
let saved = '';
try { saved = JSON.parse(localStorage.getItem('eov-game-settings') || '{}').authServerUrl || ''; } catch { /* Use build default. */ }
export const authServerUrl = serverAddress(saved, process.env.REACT_APP_BACKEND_URL);
export const authApi = authServerUrl ? `${authServerUrl.replace(/\/api$/, '')}/api` : '/api';
export function authRequestConfig() {
  const token = sessionStorage.getItem('eovAccessToken');
  return { headers: token ? { Authorization: `Bearer ${token}` } : {} };
}
