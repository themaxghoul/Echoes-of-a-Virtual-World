const path = require('node:path');
const { app, BrowserWindow, ipcMain, shell } = require('electron');
const { createStore } = require('./store.cjs');
const { createDesktopAuth } = require('./auth.cjs');
const { scopedNamespace } = require('./storage-access.cjs');

let store;
let desktopAuth;

function characterFor(user) {
  return {
    id: `character-${user.id}`,
    user_id: user.id,
    name: user.username,
    abilities: user.is_owner ? ['creator', 'owner', 'administer_world', 'manage_users', 'jarvis'] : ['explore', 'talk', 'trade'],
    stats: user.is_owner ? null : { health: 100, energy: 100 },
    inspection_policy: user.is_owner ? 'null_read' : 'public',
  };
}

function createWindow() {
  const window = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1024,
    minHeight: 700,
    backgroundColor: '#030708',
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      webSecurity: true,
    },
  });

  window.removeMenu();
  window.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('https://')) shell.openExternal(url);
    return { action: 'deny' };
  });
  window.webContents.on('will-navigate', (event, url) => {
    if (!url.startsWith('file:')) event.preventDefault();
  });
  window.once('ready-to-show', () => window.show());
  window.loadFile(path.join(__dirname, '..', 'build', 'index.html'));
}

app.whenReady().then(() => {
  store = createStore(app.getPath('userData'));
  desktopAuth = createDesktopAuth(app.getPath('userData'), {
    ownerUsername: process.env.EOV_OWNER_USERNAME || 'luciferous',
    ownerPassword: process.env.EOV_OWNER_PASSWORD || '',
  });
  ipcMain.handle('eov:version', () => app.getVersion());
  ipcMain.handle('eov:auth:login', (_event, credentials) => {
    const user = desktopAuth.authenticate(credentials?.identifier, credentials?.password);
    if (!user) return { ok: false, error: 'Invalid username, email, or password' };
    return { ok: true, user, session: desktopAuth.issueSession(user), character: characterFor(user) };
  });
  ipcMain.handle('eov:auth:register', (_event, registration) => {
    const result = desktopAuth.register(registration);
    return result.ok ? { ...result, session: desktopAuth.issueSession(result.user) } : result;
  });
  ipcMain.handle('eov:auth:resume', (_event, token) => {
    const user = desktopAuth.resumeSession(token);
    return user ? { ok: true, user, character: characterFor(user) } : { ok: false };
  });
  ipcMain.handle('eov:auth:resume-last', () => {
    const user = desktopAuth.resumeLastSession();
    return user ? { ok: true, user, character: characterFor(user) } : { ok: false };
  });
  ipcMain.handle('eov:auth:logout', () => { desktopAuth.clearSession(); return { ok: true }; });
  const activeDesktopUser = () => {
    const user = desktopAuth.resumeLastSession();
    if (!user) throw new Error('Authenticated desktop session required');
    return user;
  };
  ipcMain.handle('eov:store:read', (_event, namespace) => {
    const user = activeDesktopUser();
    const scoped = scopedNamespace(namespace, user);
    const current = store.read(scoped);
    if (current || !String(namespace).startsWith('jarvis') || !user.is_owner) return current;
    const legacy = store.read('jarvis');
    return legacy ? store.write(scoped, legacy.payload) : null;
  });
  ipcMain.handle('eov:store:write', (_event, namespace, payload) => store.write(scopedNamespace(namespace, activeDesktopUser()), payload));
  ipcMain.handle('eov:diagnostics', () => {
    const user = activeDesktopUser();
    const namespaces = ['world', 'ledger', ...(user.is_owner ? ['jarvis'] : [])].map((base) => scopedNamespace(base, user));
    return { appVersion: app.getVersion(), platform: process.platform, authMode: 'desktop_local', ...store.diagnostics(namespaces) };
  });
  createWindow();
  app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
});

app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
