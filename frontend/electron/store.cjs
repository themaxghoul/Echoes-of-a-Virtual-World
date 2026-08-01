const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

const SCHEMA_VERSION = 1;
const ALLOWED_NAMESPACES = new Set(['world', 'jarvis', 'ledger']);

function checksum(value) {
  return crypto.createHash('sha256').update(JSON.stringify(value)).digest('hex');
}

function createStore(userDataPath) {
  const saveDir = path.join(userDataPath, 'saves');
  fs.mkdirSync(saveDir, { recursive: true });

  const pathsFor = (namespace) => {
    if (!ALLOWED_NAMESPACES.has(namespace)) throw new Error('Unsupported save namespace');
    return {
      live: path.join(saveDir, `${namespace}.json`),
      backup: path.join(saveDir, `${namespace}.backup.json`),
      temporary: path.join(saveDir, `${namespace}.tmp`),
    };
  };

  const decode = (filename) => {
    const envelope = JSON.parse(fs.readFileSync(filename, 'utf8'));
    if (envelope.schemaVersion !== SCHEMA_VERSION || checksum(envelope.payload) !== envelope.checksum) {
      throw new Error('Save integrity check failed');
    }
    return envelope;
  };

  function read(namespace) {
    const files = pathsFor(namespace);
    for (const candidate of [files.live, files.backup]) {
      try {
        if (fs.existsSync(candidate)) return { ...decode(candidate), recovered: candidate === files.backup };
      } catch (error) {
        // Try the previous known-good snapshot.
      }
    }
    return null;
  }

  function write(namespace, payload) {
    const files = pathsFor(namespace);
    const previous = read(namespace);
    const envelope = {
      schemaVersion: SCHEMA_VERSION,
      revision: (previous?.revision || 0) + 1,
      savedAt: new Date().toISOString(),
      payload,
      checksum: checksum(payload),
    };
    const descriptor = fs.openSync(files.temporary, 'w');
    try {
      fs.writeFileSync(descriptor, JSON.stringify(envelope, null, 2), 'utf8');
      fs.fsyncSync(descriptor);
    } finally {
      fs.closeSync(descriptor);
    }
    if (fs.existsSync(files.live)) {
      fs.copyFileSync(files.live, files.backup);
      fs.unlinkSync(files.live);
    }
    fs.renameSync(files.temporary, files.live);
    return envelope;
  }

  function diagnostics() {
    const result = { schemaVersion: SCHEMA_VERSION, saveDirectory: saveDir, namespaces: {} };
    for (const namespace of ALLOWED_NAMESPACES) {
      const current = read(namespace);
      result.namespaces[namespace] = current ? { revision: current.revision, savedAt: current.savedAt, recovered: current.recovered } : null;
    }
    return result;
  }

  return { read, write, diagnostics, saveDir };
}

module.exports = { createStore };
