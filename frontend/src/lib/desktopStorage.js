export const isDesktop = () => Boolean(window.eovDesktop);

export async function readDurable(namespace, fallbackKey, fallbackValue) {
  if (window.eovDesktop) {
    const envelope = await window.eovDesktop.read(namespace);
    return envelope?.payload ?? fallbackValue;
  }
  try {
    const value = JSON.parse(localStorage.getItem(fallbackKey));
    return value ?? fallbackValue;
  } catch {
    return fallbackValue;
  }
}

export async function writeDurable(namespace, fallbackKey, value) {
  if (window.eovDesktop) return window.eovDesktop.write(namespace, value);
  localStorage.setItem(fallbackKey, JSON.stringify(value));
  return { revision: 0, savedAt: new Date().toISOString(), payload: value };
}

export async function getDiagnostics() {
  if (window.eovDesktop) return window.eovDesktop.diagnostics();
  return { appVersion: 'browser-alpha', platform: 'web', schemaVersion: 0, namespaces: {} };
}
