const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('eovDesktop', Object.freeze({
  platform: process.platform,
  version: () => ipcRenderer.invoke('eov:version'),
  login: (identifier, password) => ipcRenderer.invoke('eov:auth:login', { identifier, password }),
  register: (registration) => ipcRenderer.invoke('eov:auth:register', registration),
  resume: (token) => ipcRenderer.invoke('eov:auth:resume', token),
  resumeLast: () => ipcRenderer.invoke('eov:auth:resume-last'),
  logout: () => ipcRenderer.invoke('eov:auth:logout'),
  read: (namespace) => ipcRenderer.invoke('eov:store:read', namespace),
  write: (namespace, payload) => ipcRenderer.invoke('eov:store:write', namespace, payload),
  diagnostics: () => ipcRenderer.invoke('eov:diagnostics'),
}));
