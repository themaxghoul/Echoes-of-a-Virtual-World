const path = require('node:path');
const { app, BrowserWindow, ipcMain, shell } = require('electron');
const { createStore } = require('./store.cjs');

let store;

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
  ipcMain.handle('eov:version', () => app.getVersion());
  ipcMain.handle('eov:store:read', (_event, namespace) => store.read(namespace));
  ipcMain.handle('eov:store:write', (_event, namespace, payload) => store.write(namespace, payload));
  ipcMain.handle('eov:diagnostics', () => ({ appVersion: app.getVersion(), platform: process.platform, ...store.diagnostics() }));
  createWindow();
  app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
});

app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
