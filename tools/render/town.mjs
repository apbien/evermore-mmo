#!/usr/bin/env node
/**
 * Whole-town render harness — the image every layout claim has to be backed by.
 *
 * shoot.mjs renders ONE venue against a flat plane. v1's composition defects
 * (blocked main street, floating masses, dead sightlines) all shipped because
 * nothing ever rendered the venues NEXT TO EACH OTHER. This assembles the whole
 * town from content/town/hearthmere.json and shoots it at the locked 09:30 rig
 * read from that same file. See docs/BUILD_DIRECTIVE.md §8.
 *
 *   node tools/render/town.mjs --views plan,aerial-ne,arrival,square
 *   node tools/render/town.mjs --views walk --route "0,-44;0,0;0,40" --frames 8
 *   node tools/render/town.mjs --views free --at 12,-8 --look 0,0 --eye 1.62
 *   node tools/render/town.mjs --views plan --footprints        # labelled layout
 *
 * Views: plan · aerial-ne/nw/sw/se · arrival · gate-north · gate-south ·
 *        square · walk · silhouette · approach-s/ne/w · bridge · free
 *
 * DRAW CALLS MEAN THE WHOLE FRAME. scene pass + shadow maps + the AO
 * G-buffer + every post quad, measured by `client/src/perf.js` — the same
 * module `client/src/main.js` measures with, so this report and
 * `tools/check_client.mjs` print the same number for the same town. They used
 * to differ by 3x; see the header of that file for what each was counting.
 *
 * Exit codes: 0 ok · 1 the render itself failed · 2 a venue mesh is missing
 * (pass --allow-missing to downgrade that to a warning) · 3 the BUILD_DIRECTIVE
 * §7 performance budget gate failed.
 *
 * The gate compares the worst GAMEPLAY-camera frame against the §7 budget and
 * against review/perf-baseline.json. Rewrite the baseline deliberately, with
 * --write-baseline, and say why in docs/DECISIONS.md.
 */
import { chromium } from 'playwright';
import http from 'http';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(__dirname, '../..');

// Browser resolution: some environments preinstall a Chromium at a fixed path
// whose revision does not match the npm playwright build, so an explicit path
// wins. Where that path does not exist (any normal machine, Windows included),
// fall through to playwright's own managed download. Same logic as shoot.mjs.
const PINNED = process.env.CHROME_BIN || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const CHROME = fs.existsSync(PINNED) ? PINNED : undefined;

function arg(name, dflt = null) {
  const i = process.argv.indexOf(`--${name}`);
  if (i >= 0 && process.argv[i + 1] && !process.argv[i + 1].startsWith('--')) return process.argv[i + 1];
  return process.argv.includes(`--${name}`) ? true : dflt;
}
const flag = name => process.argv.includes(`--${name}`);

const outDir  = arg('out', 'review/shots/town');
const label   = arg('label', 'town');
const townRel = arg('town', 'content/town/hearthmere.json');
const W = +arg('w', 1600), H = +arg('h', 900);
const frames  = +arg('frames', 6);
const eye     = arg('eye', null);
const dist    = arg('dist', null);
const skip    = String(arg('skip', '') || '');
const wantFigure = flag('no-figure') ? '0' : '1';
const footprints = flag('footprints') ? '1' : '0';
const allowMissing = flag('allow-missing');
const reportPath = arg('report', path.join(outDir, `${label}-report.json`));

const pair = s => (s && typeof s === 'string' && s.includes(',')) ? s.split(',').map(Number) : null;
const at   = pair(arg('at'));
const look = pair(arg('look'));
const route = (() => {
  const r = arg('route');
  if (!r || typeof r !== 'string') return null;
  const pts = r.split(';').map(s => s.trim()).filter(Boolean).map(pair).filter(Boolean);
  return pts.length > 1 ? pts : null;
})();

// --at with no explicit --views means the caller wants that free camera.
// The three approach cameras are in the standard set now: they are how the
// skyline — the town's most-cited defect — is judged, and the art director had
// to type them by hand every time. review/reports/ad-town-03.md item 10.
const defaultViews = at ? 'free'
  : 'plan,aerial-ne,aerial-sw,arrival,square,silhouette,approach-s,approach-ne,approach-w,bridge';
const views = String(arg('views', defaultViews)).split(',').map(s => s.trim()).filter(Boolean);

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
  } else if (rel === '/town.html') {
    file = path.join(__dirname, 'town.html');
  } else {
    file = path.join(REPO, rel.replace(/^\/+/, ''));
  }
  fs.readFile(file, (err, data) => {
    if (err) { res.writeHead(404); res.end(`404 ${rel}`); return; }
    res.writeHead(200, { 'Content-Type': MIME[path.extname(file)] || 'application/octet-stream' });
    res.end(data);
  });
});

const townAbs = path.resolve(REPO, townRel);
if (!fs.existsSync(townAbs)) {
  console.error(`town file not found: ${townAbs}`);
  process.exit(1);
}

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

const params = new URLSearchParams({
  w: W, h: H, figure: wantFigure, footprints,
  town: '/' + path.relative(REPO, townAbs).replace(/\\/g, '/'),
});
if (skip) params.set('skip', skip);
// `--query k=v,k=v` reaches town.html's own switches. The two that matter:
//   atmos=0   render the world WITHOUT the shared environmental layer, which
//             is the only honest way to shoot a before and an after out of one
//             build rather than out of two checkouts
//   ao=raw    output the ambient-occlusion term on its own
for (const kv of String(arg('query', '') || '').split(',').filter(Boolean)) {
  const i = kv.indexOf('=');
  if (i > 0) params.set(kv.slice(0, i).trim(), kv.slice(i + 1).trim());
}

const bail = async (code, msg) => {
  console.error(msg);
  [...new Set(errors)].slice(0, 12).forEach(e => console.error('   ', e));
  await browser.close(); server.close();
  process.exit(code);
};

await page.goto(`http://localhost:${port}/town.html?${params}`);
try {
  await page.waitForFunction(() => window.__ready === true, { timeout: 180000 });
} catch {
  await bail(1, 'town assembly did not become ready — nothing was rendered');
}

const report = await page.evaluate(() => window.__report);

// ---------------------------------------------------------------------------
// Shoot
// ---------------------------------------------------------------------------
fs.mkdirSync(outDir, { recursive: true });
const written = [];

const wantBands = flag('bands');
const bandRows = [];

// Renders per measurement. The first one SETTLES the renderer; the number is
// read off the second.
//
// ad-town-05 §12 measured `--views square` at 1,385 draws and `--views
// plan,square` at 989 on identical assets and concluded the harness samples the
// previous frame's LOD state. The LOD state was identical in both (467 scene
// draws, 177/544 batches, 193/93/171/10 by level); what leaked was the SHADOW
// rig, and that is fixed at its cause in client/src/shadows.js — `fitSingle`
// parked cascades 1..n on a 0.1..0.2 m slab and CSM's refit restores the box
// but never the near/far planes.
//
// This stays anyway, and it is not belt-and-braces for its own sake. The claim
// this harness has to be able to make is "the number does not depend on what
// was rendered before it", and one renderer-state leak has already survived
// four passes undetected because nothing here made the frame independent of its
// predecessor. A settle render costs one frame per view and makes the property
// structural instead of a thing somebody has to keep remembering. Any residual
// first-frame cost — a lazily allocated bloom mip, a shader compiled on first
// use — is absorbed here too. `--no-settle` measures the raw first frame, which
// is how you catch the next leak.
const SETTLE = flag('no-settle') ? 1 : 2;

async function shoot(view, opts, filename) {
  let stats = null;
  for (let i = 0; i < SETTLE; i++) {
    stats = await page.evaluate(([v, o]) => window.__setView(v, o), [view, opts]);
  }
  await page.waitForTimeout(140);            // let bloom settle
  // Measure the frame BEFORE it is written out. `__valueBands` reads the
  // composited drawing buffer and then renders a depth pass into an offscreen
  // target, so the canvas the screenshot captures is untouched.
  let bands = null;
  if (wantBands && stats.gameplayCamera) {
    bands = await page.evaluate(() => window.__valueBands());
    if (bands) bandRows.push(bands);
  }
  const p = path.join(outDir, filename);
  await page.screenshot({ path: p });
  written.push({ path: p, ...stats, bands });
  console.log(`wrote ${p}   ${stats.drawCalls} draws  ${stats.trianglesDrawn.toLocaleString()} tris  — ${stats.title}`);
  if (bands) {
    const b = bands.bands.map(x => `${x.band[0].toUpperCase()} ${x.pixels ? x.meanValue : '--'}`).join('  ');
    console.log(`     value bands  ${b}   separation fg->bg ` +
                `${bands.separation.foregroundToBackground}  temp ${bands.separation.temperatureSwing}`);
  }
}

const baseOpts = {};
if (eye != null) baseOpts.eye = +eye;
if (dist != null) baseOpts.dist = +dist;
if (at) baseOpts.at = at;
if (look) baseOpts.look = look;

for (const v of views) {
  if (v === 'walk') {
    const n = Math.max(2, frames);
    for (let i = 0; i < n; i++) {
      await shoot('walk', { ...baseOpts, route, frames: n, index: i },
                  `${label}-walk-${String(i + 1).padStart(2, '0')}.png`);
    }
  } else {
    await shoot(v, baseOpts, `${label}-${v}.png`);
  }
}

const finalReport = await page.evaluate(() => window.__report);
finalReport.valueBands = bandRows;

// `__setView` appends to `viewStats` and maxes the peaks on EVERY call, so the
// settle renders are in there too. Keep the last row per view — the measured
// one — and re-derive every peak from what is left, because a peak taken over
// the settle frames is exactly the order-dependent number this is fixing.
{
  const last = new Map();
  for (const s of finalReport.viewStats) last.set(s.view, s);
  finalReport.settleRenders = finalReport.viewStats.length - last.size;
  finalReport.viewStats = [...last.values()];
  finalReport.drawCalls = Math.max(0, ...finalReport.viewStats.map(s => s.drawCalls));
  const gp = finalReport.viewStats.filter(s => s.gameplayCamera);
  finalReport.gameplayDrawCalls = Math.max(0, ...gp.map(s => s.drawCalls));
  finalReport.gameplayTriangles = Math.max(0, ...gp.map(s => s.trianglesDrawn));
}
await browser.close();
server.close();

// ---------------------------------------------------------------------------
// Report. Loud on purpose — a harness that renders a hole in the town and says
// nothing is how v1 shipped.
// ---------------------------------------------------------------------------
const R = finalReport;
const n = x => x.toLocaleString('en-US');
const line = (c = '-') => console.log(c.repeat(78));

console.log('');
line('=');
console.log(`  ${R.town} — whole-town assembly`);
line('=');
console.log(`  town file    ${R.townUrl}`);
console.log(`  grid         ${R.grid.cols} x ${R.grid.rows} cells @ ${R.grid.cellSize} m  ` +
            `= ${R.grid.cols * R.grid.cellSize} x ${R.grid.rows * R.grid.cellSize} m`);
console.log(`  lighting     ${R.lighting.timeOfDay} locked rig  sun ${R.lighting.sunElevationDeg}° elev / ` +
            `${R.lighting.sunAzimuthDeg}° azi  exposure ${R.lighting.exposure}`);
console.log(`  spawn        ${R.playerSpawn ? `${R.playerSpawn.pos.join(', ')} facing ${R.playerSpawn.facingDeg}°` : 'NOT AUTHORED'}`);
console.log(`  bounds       min ${R.bounds.min.join(', ')}   max ${R.bounds.max.join(', ')}`);

console.log('');
console.log(`venues — ${R.venues.filter(v => v.ok).length} placed, ${R.missing.length} missing` +
            (R.skipped.length ? `, ${R.skipped.length} skipped (${R.skipped.join(', ')})` : ''));
console.log('  ' + 'key'.padEnd(14) + 'mesh'.padEnd(15) + 'origin'.padEnd(22) +
            'rot'.padEnd(6) + 'tris'.padStart(8) + '   ' + 'footprint'.padStart(10) + '   y-range');
for (const v of R.venues) {
  if (!v.ok) {
    console.log('  ' + v.key.padEnd(14) + v.id.padEnd(15) + '** MESH FAILED TO LOAD **');
    continue;
  }
  const o = `${v.origin[0]}, ${v.origin[1]}, ${v.origin[2]}`;
  console.log('  ' + v.key.padEnd(14) + v.id.padEnd(15) + o.padEnd(22) +
              String(v.rotationDeg).padEnd(6) + n(v.tris).padStart(8) + '   ' +
              `${v.footprintM2} m2`.padStart(10) + `   ${v.box.min[1].toFixed(2)} .. ${v.box.max[1].toFixed(2)}`);
}
console.log('  ' + ''.padEnd(29) + 'TOTAL'.padEnd(22) + ''.padEnd(6) + n(R.totalTris).padStart(8) + '  triangles in the scene graph');

// ---------------------------------------------------------------------------
// Batching. What the build did to make the town affordable, per venue.
// ---------------------------------------------------------------------------
if (R.batching) {
  console.log('');
  console.log(`static batching — ${R.batching.groups} batch groups over ` +
              `${R.batching.cellsOccupied} town cells, ` +
              `LOD switch at ${(R.batching.lodDistances || []).join(' / ')} m, ` +
              `cell cull at ${R.batching.cullDistance} m`);
  console.log('  ' + 'key'.padEnd(14) + 'cells'.padStart(6) + '  ' +
              'draws L0/L1/L2/L3'.padStart(22) + '  ' + 'tris L0'.padStart(9) + '  ' +
              'tris L3'.padStart(8) + '  inst  interiors');
  for (const v of R.venues) {
    if (!v.ok || !v.lodPrims) continue;
    console.log('  ' + v.key.padEnd(14) + String(v.batchCells).padStart(6) + '  ' +
                v.lodPrims.join('/').padStart(22) + '  ' +
                n(v.lodTris[0]).padStart(9) + '  ' + n(v.lodTris[3]).padStart(8) + '  ' +
                String(v.instances).padStart(4) + '  ' + String(v.interiors).padStart(9));
  }
}

// ---------------------------------------------------------------------------
// Per-view cost, and the attribution that tells the next agent where it went.
// ---------------------------------------------------------------------------
console.log('');
console.log('per-view cost — THE WHOLE FRAME: scene + shadow maps + AO G-buffer + post quads');
console.log('  ' + 'view'.padEnd(14) + 'draws'.padStart(6) + ' =' + 'scene'.padStart(6) +
            ' +' + 'shadow'.padStart(7) + ' +' + 'ao'.padStart(5) + ' +' + 'post'.padStart(5) +
            '   ' + 'triangles'.padStart(11) +
            '   batches drawn/total   LOD 0/1/2/3');
for (const s of R.viewStats) {
  const b = s.batches || {};
  console.log('  ' + s.view.padEnd(14) + String(s.drawCalls).padStart(6) + '  ' +
              String(s.sceneCalls ?? 0).padStart(6) + '  ' + String(s.shadowCalls ?? 0).padStart(7) +
              '  ' + String(s.aoCalls ?? 0).padStart(5) + '  ' + String(s.postCalls ?? 0).padStart(5) +
              '   ' + n(s.trianglesDrawn).padStart(11) +
              `   ${String(b.drawn ?? 0).padStart(5)}/${String(b.total ?? 0).padEnd(5)}` +
              `        ${(s.byLod || []).join('/')}` +
              (s.gameplayCamera ? '   <- gameplay camera' : ''));
}
// The shadow pass, split by cascade. It was the largest stage in the frame and
// one undivided number, which made "per-cascade caster culling" an argument
// rather than a measurement; `client/src/perf.js` attributes each shadow draw
// to the shadow camera that asked for it, and a cascade IS its shadow camera.
if (R.viewStats.some(s => (s.shadowByCascade || []).length)) {
  console.log('');
  console.log('  shadow pass by cascade — draws (casters kept after per-cascade culling)');
  for (const s of R.viewStats) {
    const c = s.shadowByCascade || [];
    if (!c.length) continue;
    const casters = (s.shadows?.cascades || []).map(k => k.casters);
    const cells = c.map((k, i) => {
      const cs = casters[i];
      return `c${i} ${String(k.draws).padStart(4)}` + (cs == null ? '' : ` (${cs})`);
    });
    cells.push(`eligible ${s.batches?.shadowCasters ?? '?'}`);
    const un = s.shadowUnattributed?.draws || 0;
    console.log('  ' + s.view.padEnd(14) + cells.join('   ') +
                `   LOD ${(s.shadowByLod || []).join('/')}` +
                (un ? `   unattributed ${un}` : '') +
                (s.gameplayCamera ? '   <- gameplay camera' : ''));
  }
  const w = R.viewStats.filter(s => s.gameplayCamera)
    .sort((a, b) => b.drawCalls - a.drawCalls)[0];
  if (w) {
    const rows = Object.entries(w.shadowByVenue || {}).sort((a, b) => b[1].draws - a[1].draws);
    console.log(`  shadow casters by venue (${w.view}): ` +
                rows.map(([k, v]) => `${k} ${v.draws}`).join(' · '));
  }
}
console.log(`  peak draw calls ${R.drawCalls} over all views;  ` +
            `${R.gameplayDrawCalls} from a gameplay camera  ` +
            `(BUILD_DIRECTIVE §7 budget: < ${R.budget.drawCalls})`);
console.log(`  peak triangles  ${n(R.gameplayTriangles)} from a gameplay camera  ` +
            `(budget < ${n(R.budget.triangles)})`);
console.log('  Plan and silhouette are orthographic review cameras: distance culling OFF,');
console.log('  LOD pinned to 0, no post chain. They are the worst case, not the frame cost,');
console.log('  and they are not budgeted. Only `<- gameplay camera` rows are.');

// Attribution: the heaviest venue and the heaviest cell in the most expensive
// gameplay frame. This exists so the next agent who blows the budget is told
// exactly where, instead of being handed one number for the whole town.
{
  const gp = R.viewStats.filter(s => s.gameplayCamera);
  const worst = gp.sort((a, b) => b.drawCalls - a.drawCalls)[0];
  if (worst) {
    console.log('');
    console.log(`draw-call attribution — worst gameplay frame (${worst.view}): ` +
                `${worst.sceneCalls} scene draws, ${n(worst.sceneTris)} triangles`);
    const rows = Object.entries(worst.byVenue || {}).sort((a, b) => b[1].draws - a[1].draws);
    console.log('  by venue: ' + (rows.length
      ? rows.map(([k, v]) => `${k} ${v.draws}`).join(' · ') : 'nothing drawn'));
    const cells = Object.entries(worst.byCell || {}).sort((a, b) => b[1].draws - a[1].draws).slice(0, 8);
    console.log('  by cell:  ' + (cells.length
      ? cells.map(([k, v]) => `${k} ${v.draws}`).join(' · ') : 'nothing drawn'));
  }
}

if (R.warnings?.length) {
  console.log('');
  line('!');
  R.warnings.forEach(w => console.log('  WARNING: ' + w));
  line('!');
}

if (R.missing.length) {
  console.log('');
  line('!');
  console.log(`  ${R.missing.length} VENUE MESH(ES) MISSING — THE TOWN IN THESE IMAGES HAS HOLES IN IT`);
  line('!');
  for (const m of R.missing) console.log(`  MISSING  ${m.key.padEnd(14)} expected ${m.file}`);
  (R.loadErrors || []).forEach(e => console.log(`           ${e}`));
  console.log('  run: python tools/assetgen/build.py --skip-textures');
}

if (R.floating.length) {
  console.log('');
  console.log(`floating / sunk masses (BUILD_DIRECTIVE §6.1) — ${R.floating.length}` +
              `   [ground: ${R.terrainSource}]`);
  for (const f of R.floating) {
    console.log(`  ${f.key.padEnd(14)} box min y = ${String(f.minY).padStart(7)} m   ` +
                `terrain ${String(f.groundY).padStart(7)} m   gap ${String(f.gap).padStart(7)} m  (${f.kind})`);
  }
} else {
  console.log(`\nfloating / sunk masses: none at venue-box level  [ground: ${R.terrainSource}]`);
}

console.log('');
const hard = R.overlaps.filter(o => o.geometry);
console.log(`bounding-box overlaps — ${R.overlaps.length} total, ${hard.length} with geometry in the same space`);
for (const o of R.overlaps) {
  const tag = o.geometry ? 'GEOMETRY' : (o.layer ? 'layer   ' : 'bbox    ');
  const deep = o.deep ? `   deepest ${o.deep.volM3} m3` : '';
  console.log(`  ${tag}  ${o.a} x ${o.b}`.padEnd(46) +
              `${String(o.areaM2).padStart(8)} m2 plan   y-overlap ${o.spanY} m${deep}`);
}
if (hard.length) {
  console.log('  GEOMETRY rows are two masses occupying the same volume — a placement defect,');
  console.log('  or a venue whose mesh sprawls outside its authored cells.');
}
if (R.overlaps.some(o => o.layer)) {
  console.log('  layer rows cross a town-wide network (streets, wall). An AABB says nothing');
  console.log('  there — run tools/check_walkable.mjs, which walks the street and names what');
  console.log('  is standing in it.');
}

if (errors.length) {
  console.log('');
  console.log(`console errors during render — ${errors.length}`);
  [...new Set(errors)].slice(0, 10).forEach(e => console.log('   ' + e));
}

fs.mkdirSync(path.dirname(path.resolve(REPO, reportPath)), { recursive: true });
fs.writeFileSync(path.resolve(REPO, reportPath),
                 JSON.stringify({ ...R, consoleErrors: [...new Set(errors)], images: written.map(w => w.path) }, null, 2));
console.log('');
console.log(`${written.length} view(s) rendered at the ${R.lighting.timeOfDay} locked rig -> ${outDir}`);
console.log(`report ${reportPath}`);

// ---------------------------------------------------------------------------
// The parity contract (review/parity.json)
//
// Pass 04 got this harness and `tools/check_client.mjs` to agree to 0.7% at the
// arrival camera and nothing recorded the fact, so when a shadow-rig bug pushed
// them 36% apart it took an art-director probe run to notice — one pass later.
// Agreement between two independent instruments is the only evidence either of
// them is measuring the town, so it is written down here and checked there.
//
// `arrival` and not the worst view, because it is the one camera both
// instruments can hold identically: BUILD_DIRECTIVE §3's spawn, authored in
// content, reachable from `hm.shoot()` without a route.
// ---------------------------------------------------------------------------
{
  const a = R.viewStats.find(s => s.view === 'arrival');
  if (a) {
    const P = path.resolve(REPO, 'review/parity.json');
    fs.mkdirSync(path.dirname(P), { recursive: true });
    fs.writeFileSync(P, JSON.stringify({
      schema: 2,                        // same instrument generation as BASELINE_SCHEMA
      view: 'arrival',
      measures: 'whole frame: scene + shadow + AO G-buffer + post',
      instrument: 'tools/render/town.mjs',
      drawCalls: a.drawCalls, triangles: a.trianglesDrawn,
      stages: { scene: a.sceneCalls, shadow: a.shadowCalls, ao: a.aoCalls, post: a.postCalls },
      batchesDrawn: a.batches?.drawn ?? null, batchesTotal: a.batches?.total ?? null,
      tolerance: 0.03,
      recorded: new Date().toISOString().slice(0, 10),
    }, null, 2));
    console.log(`parity contract review/parity.json <- arrival ${a.drawCalls} draws ` +
                `(tools/check_client.mjs must land within 3%)`);
  }
}

// ---------------------------------------------------------------------------
// Budget gate (BUILD_DIRECTIVE §7)
//
// Two failures, and they are different failures:
//   OVER BUDGET   — the town does not fit in 900 draws / 3.5 M triangles.
//   REGRESSION    — it still fits, but it got measurably worse than the
//                   recorded baseline. This is the one that matters day to day:
//                   a town does not blow its budget in one commit, it blows it
//                   in forty commits that each cost 20 draws and were each
//                   individually fine.
//
// The baseline is committed (review/perf-baseline.json) and is only rewritten
// on request, so improving it is a deliberate act with a diff.
// ---------------------------------------------------------------------------
const BASELINE = path.resolve(REPO, arg('baseline', 'review/perf-baseline.json'));
const REGRESSION_SLACK = 1.05;          // 5%, to absorb driver/AA jitter
const gateFailures = [];

// `schema` is what stops a stale baseline from being read as a 3x regression.
// The pre-perf.js baseline recorded 727 gameplay draws, which was the SCENE
// PASS ONLY — the harness's counter had already been reset past the shadow
// maps, and it never saw the AO G-buffer or the post quads at all. The same
// town measured honestly is 2,000+. Comparing those two numbers produces a
// screaming false regression, and the obvious way to silence it is to rewrite
// the baseline, which is exactly how a real regression would get laundered
// through. So a baseline from a different instrument is REFUSED, loudly, and
// the only way forward is a deliberate re-baseline.
const BASELINE_SCHEMA = 2;

if (R.gameplayDrawCalls > 0) {
  const worstGp = R.viewStats.filter(s => s.gameplayCamera)
    .sort((a, b) => b.drawCalls - a.drawCalls)[0] || {};
  const current = {
    schema: BASELINE_SCHEMA,
    measures: 'whole frame at a gameplay camera: scene + shadow + AO G-buffer + post',
    drawCalls: R.gameplayDrawCalls, triangles: R.gameplayTriangles,
    worstView: worstGp.view ?? null,
    stages: worstGp.stages ?? null,
    peakDrawCalls: R.drawCalls,
    batches: R.batching?.groups ?? 0, cells: R.batching?.cellsOccupied ?? 0,
    venuesPlaced: R.venues.filter(v => v.ok).length,
    perVenueDraws: Object.fromEntries(R.venues.filter(v => v.ok && v.lodPrims)
      .map(v => [v.key, v.lodPrims[0]])),
    recorded: new Date().toISOString().slice(0, 10),
  };

  if (R.gameplayDrawCalls > R.budget.drawCalls)
    gateFailures.push(`${R.gameplayDrawCalls} draw calls from a gameplay camera ` +
                      `(${worstGp.view}) exceeds the §7 budget of ${R.budget.drawCalls}`);
  if (R.gameplayTriangles > R.budget.triangles)
    gateFailures.push(`${n(R.gameplayTriangles)} triangles from a gameplay camera ` +
                      `exceeds the §7 budget of ${n(R.budget.triangles)}`);

  let base = null;
  try { base = JSON.parse(fs.readFileSync(BASELINE, 'utf8')); } catch { /* first run */ }

  console.log('');
  if (!base) {
    console.log(`no perf baseline at ${path.relative(REPO, BASELINE)} — writing the first one`);
    fs.mkdirSync(path.dirname(BASELINE), { recursive: true });
    fs.writeFileSync(BASELINE, JSON.stringify(current, null, 2));
  } else if ((base.schema || 1) !== BASELINE_SCHEMA) {
    // Loud, and NOT a pass. Staleness of MEASUREMENT is not a licence to skip
    // the comparison silently, which is what the old gate did whenever the
    // venue count moved.
    line('!');
    console.log(`  BASELINE IS FROM A SUPERSEDED INSTRUMENT (schema ${base.schema || 1}, ` +
                `this build measures schema ${BASELINE_SCHEMA}).`);
    console.log(`  Its ${base.drawCalls} draws were the SCENE PASS ONLY. This build reports ` +
                `${current.drawCalls}`);
    console.log(`  for the whole frame. The numbers are not comparable and no regression ` +
                `check ran.`);
    console.log(`  Re-derive it deliberately:  node tools/render/town.mjs --write-baseline`);
    line('!');
    gateFailures.push(`perf baseline ${path.relative(REPO, BASELINE)} is schema ` +
                      `${base.schema || 1}; this instrument is schema ${BASELINE_SCHEMA}. ` +
                      `No regression check was possible.`);
    if (flag('write-baseline')) {
      fs.writeFileSync(BASELINE, JSON.stringify(current, null, 2));
      console.log(`baseline re-derived at schema ${BASELINE_SCHEMA} (--write-baseline)`);
      gateFailures.length = 0;              // the re-derive IS the fix for this one
      if (R.gameplayDrawCalls > R.budget.drawCalls)
        gateFailures.push(`${R.gameplayDrawCalls} draw calls from a gameplay camera ` +
                          `exceeds the §7 budget of ${R.budget.drawCalls}`);
      if (R.gameplayTriangles > R.budget.triangles)
        gateFailures.push(`${n(R.gameplayTriangles)} triangles from a gameplay camera ` +
                          `exceeds the §7 budget of ${n(R.budget.triangles)}`);
    }
  } else {
    const d = current.drawCalls - base.drawCalls;
    console.log(`perf vs baseline (${base.recorded}, ${base.venuesPlaced} venues placed): ` +
                `${base.drawCalls} -> ${current.drawCalls} gameplay draws ` +
                `(${d >= 0 ? '+' : ''}${d}), ` +
                `${n(base.triangles)} -> ${n(current.triangles)} triangles`);
    if (base.stages && current.stages) {
      const st = k => `${k} ${base.stages[k].draws}->${current.stages[k].draws}`;
      console.log(`  by stage: ` +
                  ['scene', 'shadow', 'ao', 'post'].map(st).join('  ·  '));
    }

    // 1. Per-venue batching. Camera-independent, so it is the one comparison a
    //    changing town cannot excuse.
    for (const [k, was] of Object.entries(base.perVenueDraws || {})) {
      const now = current.perVenueDraws[k];
      if (now === undefined) {
        console.log(`  note: venue '${k}' is in the baseline but not in this build`);
        continue;
      }
      if (now > Math.max(was * REGRESSION_SLACK, was + 4))
        gateFailures.push(`venue '${k}' went from ${was} to ${now} LOD0 draw calls ` +
                          `— a batching regression, not growth`);
    }

    // 2. Frame cost. The old gate only ran this when `venuesPlaced <=
    //    base.venuesPlaced`, so a baseline recorded at 10 venues against a town
    //    of 32 disabled it completely and silently — the town could double in
    //    cost and the gate would say nothing. It always runs now; when the town
    //    HAS grown, the comparison is per placed venue, which is the quantity
    //    that must not regress.
    const grew = current.venuesPlaced > base.venuesPlaced;
    if (grew) {
      console.log(`  NOTE: the town grew ${base.venuesPlaced} -> ${current.venuesPlaced} ` +
                  `venues since the baseline; comparing cost per placed venue.`);
      const wasPer = base.drawCalls / base.venuesPlaced;
      const nowPer = current.drawCalls / current.venuesPlaced;
      console.log(`  draws per placed venue ${wasPer.toFixed(1)} -> ${nowPer.toFixed(1)}`);
      if (nowPer > wasPer * REGRESSION_SLACK + 1)
        gateFailures.push(`draws per placed venue rose ${wasPer.toFixed(1)} -> ` +
                          `${nowPer.toFixed(1)} — the town got more expensive per ` +
                          `building, not just bigger`);
    } else if (current.drawCalls > base.drawCalls * REGRESSION_SLACK + 8) {
      gateFailures.push(`gameplay draw calls rose ${base.drawCalls} -> ${current.drawCalls} ` +
                        `with no new venues placed`);
    }
    if (current.triangles > base.triangles * REGRESSION_SLACK + 50000 && !grew)
      gateFailures.push(`triangles drawn rose ${n(base.triangles)} -> ` +
                        `${n(current.triangles)} with no new venues placed`);

    if (flag('write-baseline')) {
      fs.writeFileSync(BASELINE, JSON.stringify(current, null, 2));
      console.log(`baseline rewritten (--write-baseline)`);
    }
  }
}

if (gateFailures.length) {
  console.error('');
  line('!');
  console.error('  BUDGET GATE FAILED — docs/BUILD_DIRECTIVE.md §7');
  gateFailures.forEach(f => console.error('   ' + f));
  line('!');
  console.error('  Fix the generator, or if the cost is genuinely required, record why in');
  console.error('  docs/DECISIONS.md and re-run with --write-baseline.');
}

if (R.missing.length && !allowMissing) {
  console.error(`\nFAILED: ${R.missing.length} venue mesh(es) missing. These renders do not show the whole town.`);
  process.exit(2);
}
if (gateFailures.length) process.exit(3);
