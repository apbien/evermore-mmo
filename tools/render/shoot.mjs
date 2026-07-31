#!/usr/bin/env node
/**
 * Headless render harness — the infrastructure the art-director loop runs on.
 *
 * Renders a glTF at the locked 09:30 lighting from a set of standard views and
 * writes PNGs a critic agent can actually look at. An asset nobody has seen is
 * not finished (CLAUDE.md), so this is not optional tooling.
 *
 *   node tools/render/shoot.mjs --asset assets/meshes/inn.gltf --out review/shots/inn
 *   node tools/render/shoot.mjs --asset ... --views gameplay,hero,detail,silhouette
 *   node tools/render/shoot.mjs --asset ... --no-figure --w 1920 --h 1080
 */
import { chromium } from 'playwright';
import http from 'http';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(__dirname, '../..');

// Pinned browser: the npm playwright build and the preinstalled Chromium in
// this environment are different revisions, so we point at the real binary.
const CHROME = process.env.CHROME_BIN || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';

function arg(name, dflt = null) {
  const i = process.argv.indexOf(`--${name}`);
  if (i >= 0 && process.argv[i + 1] && !process.argv[i + 1].startsWith('--')) return process.argv[i + 1];
  return process.argv.includes(`--${name}`) ? true : dflt;
}

const asset  = arg('asset');
const outDir = arg('out', 'review/shots/untitled');
const views  = String(arg('views', 'gameplay,hero,detail')).split(',').map(s => s.trim()).filter(Boolean);
const W = +arg('w', 1600), H = +arg('h', 900);
const figure = arg('no-figure') ? '0' : '1';
const ground = arg('no-ground') ? '0' : '1';
const label  = arg('label', path.basename(outDir));

const MIME = {
  '.html':'text/html', '.js':'text/javascript', '.mjs':'text/javascript',
  '.json':'application/json', '.gltf':'model/gltf+json', '.bin':'application/octet-stream',
  '.png':'image/png', '.jpg':'image/jpeg', '.glb':'model/gltf-binary', '.ktx2':'image/ktx2',
};

const server = http.createServer((req, res) => {
  let rel = decodeURIComponent(req.url.split('?')[0]);
  // /vendor/* is mapped to the installed three.js so the viewer needs no bundler.
  let file;
  if (rel.startsWith('/vendor/addons/')) {
    file = path.join(REPO, 'node_modules/three/examples/jsm', rel.slice('/vendor/addons/'.length));
  } else if (rel.startsWith('/vendor/')) {
    // three >= 0.176 splits the build into three.module.js + three.core.js,
    // so serve the whole build dir rather than a single pinned file.
    file = path.join(REPO, 'node_modules/three/build', rel.slice('/vendor/'.length));
  } else if (rel === '/viewer.html') {
    file = path.join(__dirname, 'viewer.html');
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
const page = await browser.newPage({ viewport: { width: W, height: H } });

const errors = [];
page.on('pageerror', e => errors.push(e.message));
page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });

const params = new URLSearchParams({ w: W, h: H, figure, ground });
if (asset) params.set('asset', '/' + path.relative(REPO, path.resolve(asset)).replace(/\\/g, '/'));

await page.goto(`http://localhost:${port}/viewer.html?${params}`);
try {
  await page.waitForFunction(() => window.__ready === true, { timeout: 120000 });
} catch {
  console.error('render did not become ready');
  errors.forEach(e => console.error('  ', e));
  await browser.close(); server.close(); process.exit(1);
}

const loadErr = await page.evaluate(() => window.__error || null);
if (loadErr) {
  console.error('asset load failed:', loadErr);
  await browser.close(); server.close(); process.exit(1);
}

fs.mkdirSync(outDir, { recursive: true });
const written = [];
for (const v of views) {
  const silhouette = v === 'silhouette';
  await page.evaluate(([vv, ss]) => window.__setView(vv, ss), [v, silhouette]);
  await page.waitForTimeout(120);   // let SSAO/bloom settle
  const p = path.join(outDir, `${label}-${v}.png`);
  await page.screenshot({ path: p });
  written.push(p);
  console.log('wrote', p);
}

if (errors.length) {
  console.warn(`\n${errors.length} console error(s):`);
  [...new Set(errors)].slice(0, 10).forEach(e => console.warn('  ', e));
}

await browser.close();
server.close();
console.log(`\n${written.length} view(s) rendered at 09:30 locked lighting.`);
