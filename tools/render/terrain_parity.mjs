#!/usr/bin/env node
/**
 * Terrain parity check — the proof behind BUILD_DIRECTIVE section 6 rule 3.
 *
 * There is ONE deterministic height function and it has two implementations:
 * `tools/assetgen/core/terrain.py` (which every generator uses to place
 * geometry) and `client/src/terrain.js` (which the client and the review
 * viewer use to build ground). If those two ever disagree, every building in
 * the town floats or sinks by the amount of the disagreement — silently, and
 * only in the client, which is the worst possible place to find out.
 *
 * So: sample a fixed lattice through both and assert agreement to 1e-6.
 *
 *   node tools/render/terrain_parity.mjs
 *
 * The lattice is deliberately nasty. It is not a uniform grid — it lands
 * exactly on pad edges, ramp ends, water shorelines and spline knots, because
 * those are the only places where two ports of a piecewise function can
 * plausibly diverge. A smooth interior grid would pass while a branch
 * mismatch at a knot went undetected.
 */
import { spawnSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { Terrain } from '../../client/src/terrain.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(__dirname, '../..');
const TOL = 1e-6;

const doc = JSON.parse(fs.readFileSync(path.join(REPO, 'content/town/terrain.json'), 'utf8'));
const T = Terrain.fromDoc(doc);

// --- build the sample lattice ----------------------------------------------
const xs = new Set(), zs = new Set();
const add = (S, v) => { S.add(+v.toFixed(6)); };

// A coarse sweep across the whole extent, at an irrational-ish step so samples
// do not all land on round numbers.
for (let t = -288; t <= 288; t += 7.3) { add(xs, t); add(zs, t); }
// The town at the mesh's finest resolution.
for (let t = -48; t <= 48; t += 1.5) { add(xs, t); add(zs, t); }
// Spline knots and their immediate neighbourhood — interval-selection edges.
for (const [k] of doc.fall.zSpine) { for (const e of [-0.001, 0, 0.001]) add(zs, k + e); }
for (const [k] of doc.fall.xSpine) { for (const e of [-0.001, 0, 0.001]) add(xs, k + e); }
// Pad rectangle edges and apron toes — the smoothstep branch boundaries.
for (const p of doc.pads.list.concat((doc.pads.generated || {}).list || [])) {
  const ap = p.apron === undefined ? 1.2 : p.apron;
  for (const e of [-ap - 0.01, -ap, -0.001, 0, 0.001, 0.5]) {
    add(xs, p.centre[0] + p.half[0] + e); add(xs, p.centre[0] - p.half[0] - e);
    add(zs, p.centre[1] + p.half[1] + e); add(zs, p.centre[1] - p.half[1] - e);
  }
  add(xs, p.centre[0]); add(zs, p.centre[1]);
}
// Ramp ends, where the linear gradient meets the terrace it lands on.
for (const r of doc.ramps.list) {
  for (const e of [-r.apron, -0.001, 0, 0.001]) {
    add(xs, r.centre[0] + r.half[0] + e); add(xs, r.centre[0] - r.half[0] - e);
    add(zs, r.centre[1] + r.half[1] + e); add(zs, r.centre[1] - r.half[1] - e);
  }
}
// Water: channel centrelines, bank toes, and the mere shoreline vertices.
for (const s of doc.water.channels) {
  const pts = s.path || s.polygon;
  for (const p of pts) { add(xs, p[0]); add(zs, p[1]); }
  if (s.path) for (const p of pts) { add(zs, p[1] + s.halfWidth); add(zs, p[1] + s.halfWidth + s.bank); }
}

const X = [...xs].sort((a, b) => a - b);
const Z = [...zs].sort((a, b) => a - b);
// The full cross product would be ~1.6M samples; stride Z so the check stays
// under a couple of seconds while still hitting every X edge case.
const Zs = Z.filter((_, i) => i % 3 === 0);
const samples = [];
for (const x of X) for (const z of Zs) samples.push([x, z]);
console.log(`lattice: ${X.length} x ${Zs.length} = ${samples.length} samples`);

// --- Python side ------------------------------------------------------------
const inFile = path.join(REPO, 'review', 'terrain_parity_samples.json');
fs.mkdirSync(path.dirname(inFile), { recursive: true });
fs.writeFileSync(inFile, JSON.stringify(samples));

const py = spawnSync(process.env.PYTHON || 'python',
  [path.join(REPO, 'tools/assetgen/terrain_sample.py'), inFile],
  { encoding: 'utf8', maxBuffer: 1 << 28 });
if (py.status !== 0) {
  console.error('python sampler failed:\n' + (py.stderr || py.stdout));
  process.exit(1);
}
const pyOut = JSON.parse(py.stdout);
const ph = pyOut.height, pn = pyOut.normal, pw = pyOut.water;

// --- compare ----------------------------------------------------------------
let worstH = 0, worstHAt = null, worstN = 0, worstNAt = null, waterMismatch = 0;
let minY = Infinity, maxY = -Infinity;
for (let i = 0; i < samples.length; i++) {
  const [x, z] = samples[i];
  const jh = T.height(x, z);
  const dh = Math.abs(jh - ph[i]);
  if (dh > worstH) { worstH = dh; worstHAt = [x, z, jh, ph[i]]; }
  if (jh < minY) minY = jh;
  if (jh > maxY) maxY = jh;
  if ((jh < T.waterLevel) !== pw[i]) waterMismatch++;

  // Normals only on a subsample: each one costs four more height evaluations.
  if (i % 17 === 0) {
    const jn = T.normal(x, z);
    const dn = Math.max(Math.abs(jn[0] - pn[i][0]), Math.abs(jn[1] - pn[i][1]), Math.abs(jn[2] - pn[i][2]));
    if (dn > worstN) { worstN = dn; worstNAt = [x, z]; }
  }
}

console.log(`height   worst |dy| = ${worstH.toExponential(3)} m` +
  (worstHAt ? `  at (${worstHAt[0]}, ${worstHAt[1]})  js=${worstHAt[2]}  py=${worstHAt[3]}` : ''));
console.log(`normal   worst |dn| = ${worstN.toExponential(3)}` + (worstNAt ? `  at (${worstNAt[0]}, ${worstNAt[1]})` : ''));
console.log(`is_water mismatches = ${waterMismatch}`);
console.log(`sampled height range: ${minY.toFixed(3)} .. ${maxY.toFixed(3)} m`);

const ok = worstH <= TOL && worstN <= TOL && waterMismatch === 0;
console.log(ok ? `\nPARITY OK — both ports agree to better than ${TOL}` : `\nPARITY FAILED (tolerance ${TOL})`);
process.exit(ok ? 0 : 1);
