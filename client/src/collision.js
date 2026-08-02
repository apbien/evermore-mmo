/**
 * Collision world — loads authored volumes and answers movement queries.
 *
 * This replaces the v1 approach, in which the client built one THREE.Box3 from
 * each venue's whole bounding box. The `streets` venue spans C1–C6, so its box
 * sealed Ford Road; `market_square`'s sealed the plaza. The player was walled
 * out of every place they were meant to walk. Build Directive §6 rule 4 now
 * bans inferring collision from geometry: the generators author it, and this
 * module consumes it.
 *
 * Deliberately DEPENDENCY-FREE — no three.js, no DOM. Two consumers need it:
 * the client, and tools/check_walkable.mjs, which floods the town headlessly
 * and fails the build if Ford Road is not traversable. A prover that ran on a
 * re-implementation of the collision maths would prove nothing.
 *
 * Broadphase is a uniform grid on the SAME 16 m cell partition as
 * docs/ARCHITECTURE.md §3, so the bucketing this needs today is the bucketing
 * network interest management needs later.
 */

export const STEP_HEIGHT = 0.35;   // matches tools/assetgen/core/collision.py
export const CELL_SIZE = 16;

const BOX = 0, CYL = 1, HULL = 2;

// ---------------------------------------------------------------------------
// Volume construction (world space)
// ---------------------------------------------------------------------------

/** Rotate (x, z) about +Y. Must match core/collision.py rot_xz exactly. */
function rotXZ(x, z, c, s) {
  return [c * x + s * z, -s * x + c * z];
}

function makeBox(cx, cy, cz, hx, hy, hz, rotY, solid, tag) {
  const c = Math.cos(rotY), s = Math.sin(rotY);
  // World AABB of an oriented box: the extents projected onto world axes.
  const ex = Math.abs(c) * hx + Math.abs(s) * hz;
  const ez = Math.abs(s) * hx + Math.abs(c) * hz;
  return {
    shape: BOX, cx, cz, hx, hz, cos: c, sin: s, solid, tag,
    minY: cy - hy, maxY: cy + hy,
    x0: cx - ex, x1: cx + ex, z0: cz - ez, z1: cz + ez,
    _q: -1,
  };
}

function makeCylinder(cx, cy, cz, r, h, solid, tag) {
  return {
    shape: CYL, cx, cz, r, solid, tag,
    minY: cy - h * 0.5, maxY: cy + h * 0.5,
    x0: cx - r, x1: cx + r, z0: cz - r, z1: cz + r,
    _q: -1,
  };
}

function makeHull(pts, minY, maxY, solid, tag) {
  let x0 = Infinity, x1 = -Infinity, z0 = Infinity, z1 = -Infinity;
  for (const [x, z] of pts) {
    if (x < x0) x0 = x; if (x > x1) x1 = x;
    if (z < z0) z0 = z; if (z > z1) z1 = z;
  }
  return { shape: HULL, pts, minY, maxY, solid, tag, x0, x1, z0, z1, _q: -1 };
}

// ---------------------------------------------------------------------------
// Per-shape depenetration in the XZ plane
//
// Every query is a circle (the player's capsule cross-section, or the camera's
// probe sphere) against a vertical prism, so all of this is 2D. Each function
// returns the minimum translation that puts the circle outside the shape, or
// null. Applying only that translation is what produces WALL SLIDING for free:
// the component of motion along the surface is untouched.
// ---------------------------------------------------------------------------

function pushBox(v, px, pz, R, out) {
  const dx = px - v.cx, dz = pz - v.cz;
  // Into the box's own frame: Ry(-rot) * d
  const lx = v.cos * dx - v.sin * dz;
  const lz = v.sin * dx + v.cos * dz;
  const clx = lx < -v.hx ? -v.hx : (lx > v.hx ? v.hx : lx);
  const clz = lz < -v.hz ? -v.hz : (lz > v.hz ? v.hz : lz);
  let nx, nz;
  if (lx !== clx || lz !== clz) {
    const ox = lx - clx, oz = lz - clz;
    const d = Math.hypot(ox, oz);
    if (d >= R) return false;
    if (d > 1e-9) { nx = ox / d * (R - d); nz = oz / d * (R - d); }
    else { nx = 0; nz = R; }
  } else {
    // Centre is inside: escape along the shallowest face.
    const px_ = v.hx - Math.abs(lx), pz_ = v.hz - Math.abs(lz);
    if (px_ < pz_) { nx = (lx < 0 ? -1 : 1) * (px_ + R); nz = 0; }
    else { nx = 0; nz = (lz < 0 ? -1 : 1) * (pz_ + R); }
  }
  // Back to world.
  out[0] = v.cos * nx + v.sin * nz;
  out[1] = -v.sin * nx + v.cos * nz;
  return true;
}

function pushCylinder(v, px, pz, R, out) {
  const dx = px - v.cx, dz = pz - v.cz;
  const d = Math.hypot(dx, dz);
  const need = v.r + R;
  if (d >= need) return false;
  if (d > 1e-9) { out[0] = dx / d * (need - d); out[1] = dz / d * (need - d); }
  else { out[0] = 0; out[1] = need; }
  return true;
}

function pushHull(v, px, pz, R, out) {
  const p = v.pts, n = p.length;
  let inside = true;
  let bestD = Infinity, bx = 0, bz = 0;      // closest boundary point
  let bestIn = Infinity, inx = 0, inz = 0;   // shallowest edge if inside
  for (let i = 0; i < n; i++) {
    const ax = p[i][0], az = p[i][1];
    const bxp = p[(i + 1) % n][0], bzp = p[(i + 1) % n][1];
    const ex = bxp - ax, ez = bzp - az;
    const len2 = ex * ex + ez * ez;
    // Points are CCW, so the interior is to the LEFT of every edge.
    const cross = ex * (pz - az) - ez * (px - ax);
    if (cross < 0) inside = false;
    let t = len2 > 1e-12 ? ((px - ax) * ex + (pz - az) * ez) / len2 : 0;
    t = t < 0 ? 0 : (t > 1 ? 1 : t);
    const qx = ax + ex * t, qz = az + ez * t;
    const d = Math.hypot(px - qx, pz - qz);
    if (d < bestD) { bestD = d; bx = qx; bz = qz; }
    if (cross >= 0 && len2 > 1e-12) {
      // Distance to this edge, and its OUTWARD normal. Winding is CCW, so the
      // interior is where cross > 0 and the outward normal is (ez, -ex).
      const dist = cross / Math.sqrt(len2);
      if (dist < bestIn) { bestIn = dist; inx = ez; inz = -ex; }
    }
  }
  if (inside) {
    const l = Math.hypot(inx, inz) || 1;
    out[0] = inx / l * (bestIn + R);
    out[1] = inz / l * (bestIn + R);
    return true;
  }
  if (bestD >= R) return false;
  const dx = px - bx, dz = pz - bz;
  const d = Math.hypot(dx, dz);
  if (d > 1e-9) { out[0] = dx / d * (R - d); out[1] = dz / d * (R - d); }
  else { out[0] = 0; out[1] = R; }
  return true;
}

function push(v, px, pz, R, out) {
  if (v.shape === BOX) return pushBox(v, px, pz, R, out);
  if (v.shape === CYL) return pushCylinder(v, px, pz, R, out);
  return pushHull(v, px, pz, R, out);
}

/** Is (x, z) inside the prism's footprint? Used by the ground query. */
function containsXZ(v, x, z) {
  const out = [0, 0];
  return push(v, x, z, 0, out);
}

// ---------------------------------------------------------------------------
// The world
// ---------------------------------------------------------------------------

export class CollisionWorld {
  constructor(cellSize = CELL_SIZE) {
    this.cellSize = cellSize;
    this.grid = new Map();
    this.volumes = [];
    this.venues = [];        // {id, instance, volumes} for reporting
    this._query = 0;
  }

  _key(cx, cz) { return cx * 4096 + cz; }

  add(v) {
    this.volumes.push(v);
    const s = this.cellSize;
    const cx0 = Math.floor(v.x0 / s), cx1 = Math.floor(v.x1 / s);
    const cz0 = Math.floor(v.z0 / s), cz1 = Math.floor(v.z1 / s);
    for (let cx = cx0; cx <= cx1; cx++) {
      for (let cz = cz0; cz <= cz1; cz++) {
        const k = this._key(cx, cz);
        let bucket = this.grid.get(k);
        if (!bucket) { bucket = []; this.grid.set(k, bucket); }
        bucket.push(v);
      }
    }
    return v;
  }

  /**
   * Add one venue's authored volumes, composed with its placement.
   *
   * World transform is Ry(R)·local + origin, identical to what the renderer
   * applies to the mesh — and because both rotations are about Y, an oriented
   * box stays an oriented box: centre rotates, rotY adds.
   */
  addVenue(doc, origin = [0, 0, 0], rotationDeg = 0, label = null) {
    const R = (rotationDeg || 0) * Math.PI / 180;
    const c = Math.cos(R), s = Math.sin(R);
    const [ox, oy, oz] = origin;
    let n = 0;
    for (const raw of (doc.volumes || [])) {
      const solid = (raw.kind || 'solid') === 'solid';
      const tag = raw.tag || null;
      if (raw.shape === 'box') {
        const [lx, lz] = rotXZ(raw.center[0], raw.center[2], c, s);
        this.add(makeBox(ox + lx, oy + raw.center[1], oz + lz,
                         raw.half[0], raw.half[1], raw.half[2],
                         (raw.rotY || 0) + R, solid, tag));
      } else if (raw.shape === 'cylinder') {
        const [lx, lz] = rotXZ(raw.center[0], raw.center[2], c, s);
        this.add(makeCylinder(ox + lx, oy + raw.center[1], oz + lz,
                              raw.radius, raw.height, solid, tag));
      } else if (raw.shape === 'hull') {
        const pts = raw.points.map(([x, z]) => {
          const [wx, wz] = rotXZ(x, z, c, s);
          return [ox + wx, oz + wz];
        });
        this.add(makeHull(pts, oy + raw.minY, oy + raw.maxY, solid, tag));
      } else {
        console.warn('collision: unknown shape', raw.shape);
        continue;
      }
      n++;
    }
    this.venues.push({ id: doc.venue, label: label || doc.venue, volumes: n });
    return n;
  }

  /**
   * Load every venue in a town document.
   * `readJson(path)` is injected so this works under both fetch and fs.
   */
  static async load(town, readJson) {
    const w = new CollisionWorld(town.grid?.cellSize ?? CELL_SIZE);
    const cache = new Map();
    for (const v of (town.venues || [])) {
      if (!cache.has(v.id)) {
        cache.set(v.id, await readJson(`/content/collision/${v.id}.json`));
      }
      const doc = cache.get(v.id);
      if (!doc) continue;
      w.addVenue(doc, v.origin || [0, 0, 0], v.rotationDeg || 0,
                 v.instance || v.id);
    }
    return w;
  }

  /** Candidate volumes overlapping an XZ rectangle, deduplicated. */
  near(minX, minZ, maxX, maxZ) {
    const s = this.cellSize, q = ++this._query;
    const out = [];
    const cx0 = Math.floor(minX / s), cx1 = Math.floor(maxX / s);
    const cz0 = Math.floor(minZ / s), cz1 = Math.floor(maxZ / s);
    for (let cx = cx0; cx <= cx1; cx++) {
      for (let cz = cz0; cz <= cz1; cz++) {
        const bucket = this.grid.get(this._key(cx, cz));
        if (!bucket) continue;
        for (const v of bucket) {
          if (v._q === q) continue;
          v._q = q;
          if (v.x1 < minX || v.x0 > maxX || v.z1 < minZ || v.z0 > maxZ) continue;
          out.push(v);
        }
      }
    }
    return out;
  }

  /**
   * Highest surface the player can stand on at (x, z).
   *
   * A volume is standable if its top is no more than `step` above the feet —
   * which is what makes kerbs, thresholds and the bottom step climbable
   * without any special-casing, and what makes a 0.42 m plinth NOT climbable
   * unless the generator authored steps up to it.
   */
  groundAt(x, z, feetY, base = 0, step = STEP_HEIGHT) {
    let g = base;
    const reach = feetY + step + 1e-3;
    const cand = this.near(x, z, x, z);
    for (const v of cand) {
      if (v.maxY > reach || v.maxY <= g) continue;
      if (v.minY > reach) continue;
      if (containsXZ(v, x, z)) g = v.maxY;
    }
    return g;
  }

  /**
   * Move a circle from (x, z) by (dx, dz), sliding along whatever it hits.
   *
   * Swept in sub-steps no longer than half the radius so a running player
   * cannot tunnel through a wall, then depenetrated a few times per sub-step
   * so that inside corners resolve rather than jitter.
   */
  moveCircle(x, z, dx, dz, radius, feetY, height, step = STEP_HEIGHT) {
    const dist = Math.hypot(dx, dz);
    const subs = Math.max(1, Math.ceil(dist / (radius * 0.5)));
    const sx = dx / subs, sz = dz / subs;
    const lo = feetY + step, hi = feetY + height;
    const out = [0, 0];
    let hit = false;

    for (let s = 0; s < subs; s++) {
      x += sx; z += sz;
      const pad = radius + 0.05;
      const cand = this.near(x - pad, z - pad, x + pad, z + pad);
      for (let pass = 0; pass < 3; pass++) {
        let moved = false;
        for (const v of cand) {
          if (!v.solid) continue;
          // Vertical overlap with the body's blocking span. Below the step
          // height it is something to walk over; above the head it is an
          // overhang, a jetty, or an arch — a town is full of both.
          if (v.maxY <= lo || v.minY >= hi) continue;
          if (x + radius < v.x0 || x - radius > v.x1 ||
              z + radius < v.z0 || z - radius > v.z1) continue;
          if (push(v, x, z, radius, out)) {
            x += out[0]; z += out[1];
            moved = true; hit = true;
          }
        }
        if (!moved) break;
      }
    }
    return { x, z, hit };
  }

  /**
   * Is the feet height at (x, z) the top of a SOLID volume, rather than
   * terrain or an authored walkable surface?
   *
   * The distinction is what separates "walking up the step flight that carries
   * the street over a scarp" from "walking along the top of the retaining wall
   * beside it". Both are reachable; only one of them is using the town the way
   * it was built. The prover uses this to report a street as obstructed
   * without calling it severed.
   */
  onSolidTop(x, z, y, eps = 1e-4) {
    for (const v of this.near(x, z, x, z)) {
      if (!v.solid || Math.abs(v.maxY - y) > eps) continue;
      if (containsXZ(v, x, z)) return true;
    }
    return false;
  }

  /** True if a circle at (x, z) is free — the prover's walkability test. */
  isFree(x, z, radius, feetY, height, step = STEP_HEIGHT) {
    const lo = feetY + step, hi = feetY + height;
    const cand = this.near(x - radius, z - radius, x + radius, z + radius);
    const out = [0, 0];
    for (const v of cand) {
      if (!v.solid) continue;
      if (v.maxY <= lo || v.minY >= hi) continue;
      if (push(v, x, z, radius, out)) return false;
    }
    return true;
  }

  /**
   * How far a camera probe of radius `pad` can travel before hitting geometry.
   *
   * Marched rather than analytic: at 0.12 m over a ≤9 m boom that is ~75 point
   * tests against a handful of candidates, which costs nothing, and it treats
   * all three shapes identically instead of needing three ray routines.
   */
  probe(ox, oy, oz, dx, dy, dz, maxT, pad = 0.22) {
    const ex = ox + dx * maxT, ez = oz + dz * maxT;
    const cand = this.near(Math.min(ox, ex) - pad, Math.min(oz, ez) - pad,
                           Math.max(ox, ex) + pad, Math.max(oz, ez) + pad);
    if (!cand.length) return maxT;
    const solids = cand.filter(v => v.solid);
    const out = [0, 0];
    const stepT = 0.12;
    for (let t = stepT; t <= maxT; t += stepT) {
      const px = ox + dx * t, py = oy + dy * t, pz = oz + dz * t;
      for (const v of solids) {
        if (py + pad < v.minY || py - pad > v.maxY) continue;
        if (px < v.x0 - pad || px > v.x1 + pad ||
            pz < v.z0 - pad || pz > v.z1 + pad) continue;
        if (push(v, px, pz, pad, out)) return Math.max(0, t - stepT);
      }
    }
    return maxT;
  }
}

/**
 * Terrain height, resolved at runtime.
 *
 * Build Directive §6 rule 3 makes terrain a single deterministic function that
 * the client and every generator agree on. `terrain.js` self-loads in a browser
 * (top-level await on content/town/terrain.json); under Node there is no fetch
 * root, so a reader is passed in and the SAME evaluator is installed. That
 * matters more than it looks: if the prover measured a flat world while the
 * client walked a terraced one, the prover would be certifying a town nobody
 * plays.
 *
 * A missing module falls back to a flat world rather than throwing, so this
 * file stays independently useful.
 */
export async function loadTerrain(readJson = null) {
  try {
    const t = await import('./terrain.js');
    if (readJson && t.terrain && !t.terrain() && t.default?.fromDoc && t.setDefault) {
      const doc = await readJson(t.TERRAIN_URL || '/content/town/terrain.json');
      if (doc) t.setDefault(t.default.fromDoc(doc));
    }
    if (typeof t.height === 'function') return t.height;
  } catch (e) { /* not built yet */ }
  return () => 0;
}
