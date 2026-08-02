#!/usr/bin/env node
/**
 * Material contact sheet — the review surface for core/materials.py.
 *
 * Renders every set in the library on a lit 1 m chamfered cube and a lit 0.5 m
 * sphere at the locked 09:30 rig, and writes one tall PNG a human (or a critic
 * agent) can actually look at. CLAUDE.md: an asset nobody has seen is not
 * finished — and until this existed, no material in this project had ever been
 * looked at except through whichever building happened to use it, which is how
 * `leather` shipped as striped market awning for four venues.
 *
 *   node tools/render/swatches.mjs --out review/shots/materials
 *   node tools/render/swatches.mjs --keys slate,copper,brick --out review/shots/roofs
 *   node tools/render/swatches.mjs --split          # one PNG per class as well
 *
 * Requires the manifest: python tools/assetgen/build.py --textures-only
 */
import { chromium } from 'playwright';
import http from 'http';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(__dirname, '../..');

// Same browser resolution as shoot.mjs: some environments preinstall a
// Chromium at a fixed path whose revision does not match the npm playwright
// build, so an explicit path wins where it exists.
const PINNED = process.env.CHROME_BIN || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const CHROME = fs.existsSync(PINNED) ? PINNED : undefined;

function arg(name, dflt = null) {
  const i = process.argv.indexOf(`--${name}`);
  if (i >= 0 && process.argv[i + 1] && !process.argv[i + 1].startsWith('--')) return process.argv[i + 1];
  return process.argv.includes(`--${name}`) ? true : dflt;
}

const outDir = arg('out', 'review/shots/materials');
const keys   = arg('keys', '');
const width  = +arg('w', 1720);
const split  = !!arg('split');

const manifestPath = path.join(REPO, 'assets/textures/manifest.json');
if (!fs.existsSync(manifestPath)) {
  console.error('no assets/textures/manifest.json — run:\n  python tools/assetgen/build.py --textures-only');
  process.exit(1);
}
const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
const all = Object.keys(manifest.materials);

const MIME = {
  '.html':'text/html', '.js':'text/javascript', '.mjs':'text/javascript',
  '.json':'application/json', '.png':'image/png', '.jpg':'image/jpeg',
  '.gltf':'model/gltf+json', '.bin':'application/octet-stream',
};

const server = http.createServer((req, res) => {
  const rel = decodeURIComponent(req.url.split('?')[0]);
  let file;
  if (rel.startsWith('/vendor/addons/')) {
    file = path.join(REPO, 'node_modules/three/examples/jsm', rel.slice('/vendor/addons/'.length));
  } else if (rel.startsWith('/vendor/')) {
    file = path.join(REPO, 'node_modules/three/build', rel.slice('/vendor/'.length));
  } else if (rel === '/swatches.html') {
    file = path.join(__dirname, 'swatches.html');
  } else {
    file = path.join(REPO, rel.replace(/^\/+/, ''));
  }
  fs.readFile(file, (err, data) => {
    if (err) { res.writeHead(404); res.end(`404 ${rel}`); return; }
    res.writeHead(200, { 'Content-Type': MIME[path.extname(file)] || 'application/octet-stream' });
    res.end(data);
  });
});
await new Promise(r => server.listen(0, r));
const port = server.address().port;

const browser = await chromium.launch({
  executablePath: CHROME,
  args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader',
         '--no-sandbox', '--disable-dev-shm-usage'],
});

fs.mkdirSync(path.join(REPO, outDir), { recursive: true });
const written = [];

async function sheet(label, keyList) {
  const page = await browser.newPage({ viewport: { width, height: 1000 } });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });

  const params = new URLSearchParams();
  if (keyList) params.set('keys', keyList.join(','));
  await page.goto(`http://localhost:${port}/swatches.html?${params}`);
  try {
    await page.waitForFunction(() => window.__ready === true, { timeout: 600000 });
  } catch {
    console.error(`sheet '${label}' did not become ready`);
    [...new Set(errors)].slice(0, 8).forEach(e => console.error('  ', e));
    await page.close();
    return null;
  }
  const n = await page.evaluate(() => window.__count);
  const p = path.join(REPO, outDir, `materials-${label}.png`);
  await page.screenshot({ path: p, fullPage: true });
  await page.close();
  console.log(`wrote ${path.relative(REPO, p)}  (${n} materials)`);
  if (errors.length) {
    console.warn(`  ${errors.length} console error(s):`);
    [...new Set(errors)].slice(0, 8).forEach(e => console.warn('   ', e));
  }
  written.push(p);
  return p;
}

await sheet('all', keys ? keys.split(',').map(s => s.trim()).filter(Boolean) : null);

if (split) {
  // Per-class sheets. Useful when a review is about one density class — the
  // full sheet is 8000+ px tall and a critic reading it at page scale cannot
  // judge a hero material fairly next to a roof.
  for (const cls of ['hero', 'standard', 'large']) {
    const sub = all.filter(k => manifest.materials[k]['class'] === cls);
    if (sub.length) await sheet(cls, sub);
  }
}

await browser.close();
server.close();
console.log(`\n${written.length} contact sheet(s) at the locked 09:30 rig.`);
