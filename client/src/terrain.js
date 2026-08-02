/**
 * Hearthmere terrain — the JavaScript port of the one deterministic ground.
 *
 * `content/town/terrain.json` is authoritative. This file and
 * `tools/assetgen/core/terrain.py` are two ports of the same evaluator and
 * MUST agree bit-for-bit; `tools/render/terrain_parity.mjs` samples a fixed
 * lattice through both and fails the build if any sample differs by more than
 * 1e-6 (BUILD_DIRECTIVE section 6 rule 3).
 *
 * Every expression below is mirrored character-for-character in the Python
 * port. Only +, -, *, /, comparison, Math.floor and Math.sqrt appear in the
 * sampled path, because those are the operations IEEE-754 pins exactly in both
 * languages. Math.imul + `>>> 0` reproduce numpy's masked uint64 multiply.
 * If you change one port you have changed the ground under a hundred
 * generators — change both, and re-run the parity check.
 *
 *   const T = await Terrain.load('/content/town/terrain.json');
 *   T.height(x, z);  T.normal(x, z);  T.isWater(x, z);  T.waterLevel;
 *   T.padLevel('hm.pad.market_square');
 */

// ---------------------------------------------------------------------------
// Shared scalar helpers
// ---------------------------------------------------------------------------

function clamp(v, lo, hi) { return v < lo ? lo : (v > hi ? hi : v); }

function smoothstep(e0, e1, x) {
  if (e1 - e0 <= 0.0) return x < e0 ? 0.0 : 1.0;
  const t = clamp((x - e0) / (e1 - e0), 0.0, 1.0);
  return t * t * (3.0 - 2.0 * t);
}

/** Exact trig for the cardinal headings, so a pad rotation cannot introduce a
 *  last-ulp difference between libm implementations. */
function cosDeg(d) {
  const m = ((d % 360) + 360) % 360;
  if (m === 0) return 1.0;
  if (m === 90 || m === 270) return 0.0;
  if (m === 180) return -1.0;
  return Math.cos(m * Math.PI / 180.0);
}
function sinDeg(d) {
  const m = ((d % 360) + 360) % 360;
  if (m === 0 || m === 180) return 0.0;
  if (m === 90) return 1.0;
  if (m === 270) return -1.0;
  return Math.sin(m * Math.PI / 180.0);
}

// ---------------------------------------------------------------------------
// Monotone cubic Hermite (Fritsch-Carlson PCHIP)
// ---------------------------------------------------------------------------

class Spline {
  constructor(pts) {
    this.x = pts.map(p => +p[0]);
    this.y = pts.map(p => +p[1]);
    const n = this.x.length;
    this.h = new Array(n - 1);
    const d = new Array(n - 1);
    for (let i = 0; i < n - 1; i++) {
      this.h[i] = this.x[i + 1] - this.x[i];
      d[i] = (this.y[i + 1] - this.y[i]) / this.h[i];
    }
    const m = new Array(n).fill(0.0);
    m[0] = d[0];
    m[n - 1] = d[n - 2];
    for (let i = 1; i < n - 1; i++) {
      if (d[i - 1] * d[i] <= 0.0) { m[i] = 0.0; continue; }
      const w1 = 2.0 * this.h[i] + this.h[i - 1];
      const w2 = this.h[i] + 2.0 * this.h[i - 1];
      m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i]);
    }
    this.m = m;
  }

  at(t) {
    const x = this.x, n = x.length;
    t = clamp(t, x[0], x[n - 1]);
    // Largest i with x[i] <= t, clamped to a valid interval. Matches numpy's
    // searchsorted(side='right') - 1 exactly, including at the knots.
    let lo = 0, hi = n - 1;
    while (lo < hi) { const mid = (lo + hi + 1) >> 1; if (x[mid] <= t) lo = mid; else hi = mid - 1; }
    const i = clamp(lo, 0, n - 2);
    const hh = this.h[i];
    const s = (t - x[i]) / hh;
    const s2 = s * s;
    const s3 = s2 * s;
    return (this.y[i] * (2.0 * s3 - 3.0 * s2 + 1.0)
          + hh * this.m[i] * (s3 - 2.0 * s2 + s)
          + this.y[i + 1] * (-2.0 * s3 + 3.0 * s2)
          + hh * this.m[i + 1] * (s3 - s2));
  }
}

// ---------------------------------------------------------------------------
// Deterministic value noise — must match core/terrain.py bit for bit
// ---------------------------------------------------------------------------

function hash01(ix, iz, seed32) {
  let h = Math.imul(ix | 0, 0x27D4EB2D) >>> 0;
  h = (h ^ (Math.imul(iz | 0, 0x165667B1) >>> 0)) >>> 0;
  h = (h ^ seed32) >>> 0;
  h = (h ^ (h >>> 15)) >>> 0;
  h = Math.imul(h, 0x2C1B3C6D) >>> 0;
  h = (h ^ (h >>> 12)) >>> 0;
  h = Math.imul(h, 0x297A2D39) >>> 0;
  h = (h ^ (h >>> 15)) >>> 0;
  return h / 4294967296.0;
}

function valueNoise(x, z, seed32) {
  const ix = Math.floor(x), iz = Math.floor(z);
  const fx = x - ix, fz = z - iz;
  const ux = fx * fx * fx * (fx * (fx * 6.0 - 15.0) + 10.0);
  const uz = fz * fz * fz * (fz * (fz * 6.0 - 15.0) + 10.0);
  const n00 = hash01(ix, iz, seed32);
  const n10 = hash01(ix + 1, iz, seed32);
  const n01 = hash01(ix, iz + 1, seed32);
  const n11 = hash01(ix + 1, iz + 1, seed32);
  const a = n00 + (n10 - n00) * ux;
  const b = n01 + (n11 - n01) * ux;
  return a + (b - a) * uz;
}

// ---------------------------------------------------------------------------
// Signed distance shapes
// ---------------------------------------------------------------------------

function sdPolyline(x, z, pts) {
  let best = 1.0e18;
  for (let k = 0; k < pts.length - 1; k++) {
    const ax = pts[k][0], az = pts[k][1];
    const ex = pts[k + 1][0] - ax, ez = pts[k + 1][1] - az;
    const ee = ex * ex + ez * ez;
    if (ee <= 0.0) continue;
    const wx = x - ax, wz = z - az;
    const t = clamp((wx * ex + wz * ez) / ee, 0.0, 1.0);
    const dx = wx - ex * t, dz = wz - ez * t;
    const d = Math.sqrt(dx * dx + dz * dz);
    if (d < best) best = d;
  }
  return best;
}

/** Metres of signed displacement of a water outline. Two octaves of the same
 *  seeded value noise the generator uses, so client and generator agree to the
 *  bit. See `Terrain.shapeWeight`. */
function outlineNoise(n, x, z) {
  const seed = (n.seed === undefined ? 5150011 : +n.seed) >>> 0;
  const f1 = n.frequency === undefined ? 0.014 : +n.frequency;
  const a1 = n.amplitude === undefined ? 0.0 : +n.amplitude;
  const f2 = n.detailFrequency === undefined ? f1 * 4.0 : +n.detailFrequency;
  const a2 = n.detailAmplitude === undefined ? a1 * 0.32 : +n.detailAmplitude;
  let d = (valueNoise(x * f1, z * f1, seed) * 2.0 - 1.0) * a1;
  if (a2) d = d + (valueNoise(x * f2, z * f2, (seed + 7717) >>> 0) * 2.0 - 1.0) * a2;
  return d;
}

/** iq's sdPolygon. Negative inside. */
function sdPolygon(x, z, poly) {
  const n = poly.length;
  let d = (x - poly[0][0]) * (x - poly[0][0]) + (z - poly[0][1]) * (z - poly[0][1]);
  let s = 1.0;
  let j = n - 1;
  for (let i = 0; i < n; i++) {
    const vix = poly[i][0], viz = poly[i][1];
    const vjx = poly[j][0], vjz = poly[j][1];
    const ex = vjx - vix, ez = vjz - viz;
    const wx = x - vix, wz = z - viz;
    const ee = ex * ex + ez * ez;
    const t = clamp((wx * ex + wz * ez) / ee, 0.0, 1.0);
    const bx = wx - ex * t, bz = wz - ez * t;
    const dd = bx * bx + bz * bz;
    if (dd < d) d = dd;
    const c1 = z >= viz, c2 = z < vjz, c3 = (ex * wz) > (ez * wx);
    if ((c1 && c2 && c3) || (!c1 && !c2 && !c3)) s = -s;
    j = i;
  }
  return s * Math.sqrt(d);
}

function sdBox(lx, lz, hx, hz) {
  const qx = Math.abs(lx) - hx;
  const qz = Math.abs(lz) - hz;
  const mx = qx > 0.0 ? qx : 0.0;
  const mz = qz > 0.0 ? qz : 0.0;
  const outer = Math.sqrt(mx * mx + mz * mz);
  const inner = Math.min(Math.max(qx, qz), 0.0);
  return outer + inner;
}

// ---------------------------------------------------------------------------
// Terrain
// ---------------------------------------------------------------------------

const NORMAL_EPS = 0.25;   // metres; fixed and documented so both ports agree

export class Terrain {
  constructor(doc) {
    this.doc = doc;
    this.extent = doc.extent;
    this.rings = doc.lod.rings;
    this.zs = new Spline(doc.fall.zSpine);
    this.xs = new Spline(doc.fall.xSpine);

    const r = doc.roughness;
    this.nSeed = r.seed >>> 0;
    this.nOct = r.octaves | 0;
    this.nFreq = +r.baseFrequency;
    this.nLac = +r.lacunarity;
    this.nGain = +r.gain;
    this.nAmpTown = +r.amplitudeTown;
    this.nAmpField = +r.amplitudeField;
    this.nR0 = +r.townRadius;
    this.nR1 = +r.fieldRadius;

    this.waterLevel = +doc.water.level;
    this.shapes = doc.water.channels;

    // Hand-authored pads first, then the venue pads `tools/plan/ground.py`
    // generates from the town plan. Later pads win where they overlap, which
    // is what lets a building platform override the terrace it is cut into.
    // Must match core/terrain.py's ordering exactly or parity fails.
    const padRecords = doc.pads.list.concat((doc.pads.generated || {}).list || []);
    this.pads = padRecords.map(p => {
      const rot = +(p.rotationDeg || 0);
      return {
        id: p.id,
        cx: +p.centre[0], cz: +p.centre[1],
        hx: +p.half[0], hz: +p.half[1],
        apron: p.apron === undefined ? 1.2 : +p.apron,
        cos: cosDeg(rot), sin: sinDeg(rot), rot,
        level: (p.level === undefined || p.level === null)
          ? this.baseSpine(+p.centre[0], +p.centre[1]) : +p.level,
        note: p.note,
      };
    });
    this.padById = new Map(this.pads.map(p => [p.id, p]));

    this.ramps = doc.ramps.list.map(r2 => {
      const rot = +(r2.headingDeg || 0);
      return {
        id: r2.id,
        cx: +r2.centre[0], cz: +r2.centre[1],
        hx: +r2.half[0], hz: +r2.half[1],
        low: +r2.low, high: +r2.high,
        apron: r2.apron === undefined ? 1.0 : +r2.apron,
        cos: cosDeg(rot), sin: sinDeg(rot),
      };
    });

    this.retaining = doc.retaining.list;
    this.steps = doc.steps.list;
    this.surfaces = doc.surfaces;
  }

  static fromDoc(doc) { return new Terrain(doc); }

  static async load(url = '/content/town/terrain.json') {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`terrain.json ${res.status}`);
    return new Terrain(await res.json());
  }

  // -- the height function --------------------------------------------------

  baseSpine(x, z) { return this.zs.at(z) + this.xs.at(x); }

  roughness(x, z) {
    const rad = Math.sqrt(x * x + z * z);
    const amp = this.nAmpTown + (this.nAmpField - this.nAmpTown) *
      smoothstep(this.nR0, this.nR1, rad);
    let total = 0.0, norm = 0.0, a = 1.0, f = this.nFreq;
    for (let o = 0; o < this.nOct; o++) {
      total = total + (valueNoise(x * f, z * f, ((this.nSeed + o * 7919) >>> 0)) * 2.0 - 1.0) * a;
      norm = norm + a;
      a = a * this.nGain;
      f = f * this.nLac;
    }
    return (total / norm) * amp;
  }

  /** How strongly ONE water shape claims a point, 0..1.
   *
   *  The port of `tools/assetgen/core/terrain.py Terrain.shape_weight`, and it
   *  has to stay the port: BUILD_DIRECTIVE §6.3 makes one height function the
   *  law, and the generator carves the channel and the basin with this exact
   *  expression. `outlineNoise` displaces the signed distance field before the
   *  shelf ramp, which moves bed, shelf, waterline and beach together — the
   *  reason the Mere stopped being a mathematically perfect ellipse and the
   *  Emberflow stopped being a parallel-sided canal (ad-town-05 §2). Shapes
   *  with no `outlineNoise` key are untouched, so this is a no-op wherever
   *  content has not asked for it.
   */
  shapeWeight(s, x, z) {
    const n = s.outlineNoise;
    if (s.path) {
      let d = sdPolyline(x, z, s.path);
      if (n) d = d + outlineNoise(n, x, z);
      return 1.0 - smoothstep(+s.halfWidth, +s.halfWidth + +s.bank, d);
    }
    let sd = sdPolygon(x, z, s.polygon);
    if (n) sd = sd + outlineNoise(n, x, z);
    return 1.0 - smoothstep(0.0, +s.shelf, sd > 0.0 ? sd : 0.0);
  }

  height(x, z) {
    let h = this.baseSpine(x, z);
    h = h + this.roughness(x, z);

    // 3. water shapes carve toward an ABSOLUTE bed elevation
    for (const s of this.shapes) {
      h = h + (+s.bedLevel - h) * this.shapeWeight(s, x, z);
    }

    // 4. pads flatten
    for (const p of this.pads) {
      const dx = x - p.cx, dz = z - p.cz;
      const lx = p.cos * dx - p.sin * dz;
      const lz = p.sin * dx + p.cos * dz;
      const w = 1.0 - smoothstep(0.0, p.apron, sdBox(lx, lz, p.hx, p.hz));
      h = h + (p.level - h) * w;
    }

    // 5. ramps cut constant-gradient corridors through the scarps
    for (const r of this.ramps) {
      const dx = x - r.cx, dz = z - r.cz;
      const lx = r.cos * dx - r.sin * dz;
      const lz = r.sin * dx + r.cos * dz;
      const t = clamp((lz + r.hz) / (2.0 * r.hz), 0.0, 1.0);
      const level = r.low + (r.high - r.low) * t;
      const w = 1.0 - smoothstep(0.0, r.apron, sdBox(lx, lz, r.hx, r.hz));
      h = h + (level - h) * w;
    }
    return h;
  }

  // -- derived --------------------------------------------------------------

  /** Unit surface normal, Y-up, as [x, y, z]. */
  normal(x, z) {
    const e = NORMAL_EPS;
    const hx = this.height(x + e, z) - this.height(x - e, z);
    const hz = this.height(x, z + e) - this.height(x, z - e);
    const nx = -hx, ny = 2.0 * e, nz = -hz;
    const ln = Math.sqrt(nx * nx + ny * ny + nz * nz);
    return [nx / ln, ny / ln, nz / ln];
  }

  /** Gradient magnitude, dy per horizontal metre. 0 is level. */
  slope(x, z) {
    const n = this.normal(x, z);
    const ny = clamp(n[1], 1e-9, 1.0);
    return Math.sqrt(Math.max(1.0 - ny * ny, 0.0)) / ny;
  }

  isWater(x, z) { return this.height(x, z) < this.waterLevel; }

  // -- pads -----------------------------------------------------------------

  pad(id) {
    const p = this.padById.get(id);
    if (!p) throw new Error(`no pad '${id}' in terrain.json`);
    return p;
  }

  padLevel(id) { return this.pad(id).level; }
}

// ---------------------------------------------------------------------------
// Module-level default instance
// ---------------------------------------------------------------------------
// `client/src/collision.js` and the player controller want a bare
// `height(x, z)` they can call every frame, so the module owns one instance and
// loads it at import time via TOP-LEVEL await. That matters: a dynamic
// `import('./terrain.js')` then does not resolve until the ground is actually
// available, so there is no window in which the player spawns onto y = 0 and
// falls through the world for a frame.
//
// Skipped outside a browser, because the Node-side parity harness imports this
// module for its evaluator and has no fetch root to resolve a site-absolute
// URL against. Node callers use `Terrain.fromDoc(JSON.parse(...))`.

export const TERRAIN_URL = '/content/town/terrain.json';

let DEFAULT = null;

if (typeof document !== 'undefined' && typeof fetch === 'function') {
  DEFAULT = await Terrain.load(TERRAIN_URL);
}

/** The loaded default terrain, or null outside a browser. */
export function terrain() { return DEFAULT; }

/** Install an instance explicitly (tests, or a second zone later). */
export function setDefault(t) { DEFAULT = t; return t; }

/** Ground elevation in metres. THE function every other system calls. */
export function height(x, z) { return DEFAULT ? DEFAULT.height(x, z) : 0.0; }

/** Unit surface normal at (x, z). */
export function normal(x, z) { return DEFAULT ? DEFAULT.normal(x, z) : [0, 1, 0]; }

/** True where the ground is below the water surface. */
export function isWater(x, z) { return DEFAULT ? DEFAULT.isWater(x, z) : false; }

/** The single water-surface elevation for the whole system. */
export function waterLevel() { return DEFAULT ? DEFAULT.waterLevel : -Infinity; }

export default Terrain;
