const fs = require('node:fs');
const path = require('node:path');

const projectRoot = path.join(__dirname, '..');
const projectManifest = require(path.join(projectRoot, 'package.json'));
const stage = path.join(projectRoot, 'desktop-stage');
const buildDirectory = path.resolve(projectRoot, process.env.EOV_BUILD_DIR || 'build');

if (!fs.existsSync(path.join(buildDirectory, 'index.html'))) {
  throw new Error(`Desktop package build is missing index.html: ${buildDirectory}`);
}

fs.rmSync(stage, { recursive: true, force: true });
fs.mkdirSync(path.join(stage, 'electron'), { recursive: true });
fs.cpSync(buildDirectory, path.join(stage, 'build'), { recursive: true });
for (const filename of ['main.cjs', 'preload.cjs', 'store.cjs', 'auth.cjs', 'storage-access.cjs']) {
  fs.copyFileSync(path.join(__dirname, filename), path.join(stage, 'electron', filename));
}
fs.writeFileSync(path.join(stage, 'package.json'), JSON.stringify({
  name: 'echoes-of-virtuality',
  productName: 'Echoes of Virtuality',
  version: projectManifest.version,
  main: 'electron/main.cjs',
}, null, 2));

console.log(`Prepared minimal desktop stage at ${stage} from ${buildDirectory}`);
