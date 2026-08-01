const fs = require('node:fs');
const path = require('node:path');

const projectRoot = path.join(__dirname, '..');
const stage = path.join(projectRoot, 'desktop-stage');

fs.rmSync(stage, { recursive: true, force: true });
fs.mkdirSync(path.join(stage, 'electron'), { recursive: true });
fs.cpSync(path.join(projectRoot, 'build'), path.join(stage, 'build'), { recursive: true });
for (const filename of ['main.cjs', 'preload.cjs', 'store.cjs']) {
  fs.copyFileSync(path.join(__dirname, filename), path.join(stage, 'electron', filename));
}
fs.writeFileSync(path.join(stage, 'package.json'), JSON.stringify({
  name: 'echoes-of-virtuality',
  productName: 'Echoes of Virtuality',
  version: '0.3.0-alpha.1',
  main: 'electron/main.cjs',
}, null, 2));

console.log(`Prepared minimal desktop stage at ${stage}`);
