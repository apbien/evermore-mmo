#!/usr/bin/env node
/**
 * Walkability prover — floods the town from the player spawn and reports what
 * a player can actually reach.
 *
 *     node tools/check_walkable.mjs
 *     node tools/check_walkable.mjs --strict     # unreachable doors also fail
 *     node tools/check_walkable.mjs --dump map.txt
 *
 * Why this exists: every v1 venue was signed off from a render, and a render
 * cannot show you that the main street is sealed. The build reported success,
 * the screenshots looked correct, and the town could not be walked down. The
 * only defence against that is a test that moves through the world the way a
 * player does, so this runs the REAL collision data through the REAL controller
 * maths — client/src/collision.js, imported, not re-implemented. A prover built
 * on a second copy of the collision code would only prove the copies agree.
 *
 * Exit code is non-zero when Ford Road is not traversable end to end. That is
 * the specific failure the town shipped with, so it is the specific failure
 * that gets a hard gate rather than a warning nobody reads.
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

import { CollisionWorld, STEP_HEIGHT, loadTerrain } from '../client/src/collision.js';

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const argv = process.argv.slice(2);
const STRICT = argv.includes('--strict');
const DUMP = argv.includes('--dump') ? argv[argv.indexOf('--dump') + 1] : null;

// The body the town is measured against. Art Bible §3: 1.75 m, and a 0.32 m
// capsule radius, both identical to client/src/player.js. Measuring with a
// smaller body than the player has is how a "walkable" report and an unwalkable
// town coexist.
const RADIUS = 0.32;
const BODY = 1.75;
const GRID = 0.5;              // m; the flood lattice
// The lattice must cover everything a street can be authored across, or a
// station that falls outside it reads as "severed" and the gate fails for a
// reason that has nothing to do with the town. v2's grid is ±96 (Directive §2)
// and the causeway runs out to z ≈ -104, so the lattice is ±108. Sizing this to
// v1's ±48 town was worth 56 phantom severed stations on Ford Road alone.
const BOUND = 108;             // m; town grid is ±96, plus approach ground
const TOWN_HALF = 96;          // m; Directive §2 — half the 192 m grid
const MAX_DROP = 3.0;          // m the player may walk down in one 0.5 m step
const DOOR_REACH = 1.6;        // m from a door before it counts as reached

const readJson = async (p) => {
  const f = path.join(REPO, p.replace(/^\//, ''));
  if (!fs.existsSync(f)) return null;
  return JSON.parse(fs.readFileSync(f, 'utf8'));
};

/** Venue-local → world, matching CollisionWorld.addVenue and the renderer. */
function toWorld(p, origin, rotationDeg) {
  const a = (rotationDeg || 0) * Math.PI / 180;
  const c = Math.cos(a), s = Math.sin(a);
  return [origin[0] + c * p[0] + s * p[2],
          origin[1] + p[1],
          origin[2] - s * p[0] + c * p[2]];
}

async function main() {
  const town = await readJson('/content/town/hearthmere.json');
  const world = await CollisionWorld.load(town, readJson);
  const terrain = await loadTerrain(readJson);
  // Sample the ends of the north-south fall rather than the origin: the market
  // pad is authored at exactly 0.0, so testing there cannot tell a loaded
  // terrain from a missing one.
  const relief = Math.abs(terrain(0, 46) - terrain(0, -46));
  const terrainSrc = relief < 1e-9
    ? 'flat y=0 (client/src/terrain.js absent or unloaded)'
    : `client/src/terrain.js height() — ${terrain(0, -44).toFixed(2)}m at spawn, ` +
      `${terrain(0, 46).toFixed(2)}m at the south road`;

  console.log(`Hearthmere walkability — ${world.volumes.length} authored volumes ` +
              `from ${world.venues.length} placements`);
  console.log(`  body ${BODY.toFixed(2)}m r=${RADIUS}m, step ${STEP_HEIGHT}m, ` +
              `lattice ${GRID}m, terrain ${terrainSrc}`);
  const missing = (town.venues || []).filter(
    v => !world.venues.some(w => w.id === v.id));
  for (const m of new Set(missing.map(v => v.id))) {
    console.log(`  ! venue '${m}' has no collision file — treated as walk-through`);
  }

  // ---- flood fill --------------------------------------------------------
  const N = Math.round(BOUND * 2 / GRID);
  const idx = (i, j) => i * N + j;
  const seen = new Uint8Array(N * N);
  const feet = new Float32Array(N * N);
  const toI = (x) => Math.round((x + BOUND) / GRID);
  const toX = (i) => i * GRID - BOUND;

  const spawn = town.playerSpawn?.pos || [0, 0, 0];
  const si = toI(spawn[0]), sj = toI(spawn[2]);
  const groundAt = (x, z, from) => world.groundAt(x, z, from, terrain(x, z), STEP_HEIGHT);

  const start = groundAt(spawn[0], spawn[2], spawn[1]);
  if (!world.isFree(spawn[0], spawn[2], RADIUS, start, BODY, STEP_HEIGHT)) {
    console.error(`\nFAIL: the player spawn (${spawn}) is inside geometry. ` +
                  `Nothing else can be true if the first frame is a wall.`);
    process.exit(2);
  }
  seen[idx(si, sj)] = 1;
  feet[idx(si, sj)] = start;

  const queue = [idx(si, sj)];
  let head = 0, area = 0;
  const NB = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  while (head < queue.length) {
    const cur = queue[head++];
    area++;
    const i = Math.floor(cur / N), j = cur % N;
    const y = feet[cur];
    for (const [di, dj] of NB) {
      const ni = i + di, nj = j + dj;
      if (ni < 0 || nj < 0 || ni >= N || nj >= N) continue;
      const k = idx(ni, nj);
      if (seen[k]) continue;
      const x = toX(ni), z = toX(nj);
      const g = groundAt(x, z, y);
      // groundAt already refuses anything more than a step up, so only the
      // drop needs a limit — a player walks off a kerb, not off a cliff.
      if (y - g > MAX_DROP) continue;
      if (!world.isFree(x, z, RADIUS, g, BODY, STEP_HEIGHT)) continue;
      seen[k] = 1;
      feet[k] = g;
      queue.push(k);
    }
  }
  const reachable = (x, z) => {
    const i = toI(x), j = toI(z);
    return i >= 0 && j >= 0 && i < N && j < N && seen[idx(i, j)] === 1;
  };
  /** Distance from (x, z) to the nearest reachable lattice cell. */
  const nearestReach = (x, z, r) => {
    const n = Math.ceil(r / GRID) + 1;
    const i0 = toI(x), j0 = toI(z);
    let best = Infinity;
    for (let i = i0 - n; i <= i0 + n; i++)
      for (let j = j0 - n; j <= j0 + n; j++) {
        if (i < 0 || j < 0 || i >= N || j >= N || !seen[idx(i, j)]) continue;
        best = Math.min(best, Math.hypot(toX(i) - x, toX(j) - z));
      }
    return best;
  };
  const reachableNear = (x, z, r) => nearestReach(x, z, r) <= r;

  // Two figures, because one of them is misleading on its own: the town has no
  // wall yet, so the flood runs out over open ground to the edge of the
  // lattice and a single total would be dominated by nothing.
  let inTown = 0;
  const T = TOWN_HALF;
  for (let i = toI(-T); i <= toI(T); i++)
    for (let j = toI(-T); j <= toI(T); j++)
      if (seen[idx(i, j)]) inTown++;
  const cellArea = GRID * GRID;
  console.log(`\nreachable area  ${(area * cellArea).toFixed(0)} m² total from ` +
              `the spawn at (${spawn[0]}, ${spawn[2]})`);
  console.log(`                ${(inTown * cellArea).toFixed(0)} m² of the ` +
              `${(2 * T) ** 2} m² inside the town grid ` +
              `(${(100 * inTown * cellArea / (2 * T) ** 2).toFixed(1)}% — the ` +
              `remainder is building footprints and props)`);

  // ---- doors and landmarks ----------------------------------------------
  const doors = [];
  for (const v of (town.venues || [])) {
    const doc = await readJson(`/content/entities/${v.id}.json`);
    if (!doc) continue;
    for (const e of (doc.entities || [])) {
      if (!/^door\./.test(e.archetype || '')) continue;
      const p = toWorld(e.transform.pos, v.origin || [0, 0, 0], v.rotationDeg || 0);
      doors.push({ id: e.id, venue: v.instance || v.id, p });
    }
  }
  // Entity records are authored per venue MESH, so the six cottages share one
  // record; each placement gets its own row above, which is what we want.
  console.log(`\nvenue doors (${doors.length}):`);
  const badDoors = [];
  for (const d of doors.sort((a, b) => a.venue.localeCompare(b.venue))) {
    const dist = nearestReach(d.p[0], d.p[2], DOOR_REACH + 2);
    const ok = dist <= DOOR_REACH;
    if (!ok) badDoors.push(d);
    console.log(`  ${ok ? 'reachable  ' : 'UNREACHABLE'} ${d.venue.padEnd(12)} ` +
                `${d.id.padEnd(26)} (${d.p[0].toFixed(1)}, ${d.p[2].toFixed(1)})` +
                `  stand ${dist === Infinity ? '  n/a' : dist.toFixed(2) + 'm'} away`);
  }

  // A landmark is a THING, not a doorway — the fountain is 2.5 m across, so
  // "reachable" means the player can stand beside it, not on it.
  const MARK_REACH = 3.6;
  console.log(`\nlandmarks (${(town.landmarks || []).length}):`);
  const badMarks = [];
  for (const l of (town.landmarks || [])) {
    const dist = nearestReach(l.pos[0], l.pos[1], MARK_REACH + 2);
    const ok = dist <= MARK_REACH;
    if (!ok) badMarks.push(l);
    console.log(`  ${ok ? 'reachable  ' : 'UNREACHABLE'} ${l.id.padEnd(20)} ` +
                `${(l.name || '').padEnd(14)} (${l.pos[0]}, ${l.pos[1]})` +
                `  stand ${dist === Infinity ? '  n/a' : dist.toFixed(2) + 'm'} away`);
  }

  // ---- the gate: Ford Road, end to end ----------------------------------
  //
  // Two different properties, deliberately kept apart, because conflating them
  // is how you get either a useless gate or a permanently red one:
  //
  //   CONNECTED  every point on the street is in the same flood component as
  //              the spawn. This is what "traversable end to end" means, and
  //              it is the hard gate. A street cut in half by a building the
  //              player can walk round the outside of still fails it, because
  //              the far half would be reachable only via that detour and the
  //              endpoints test catches nothing of the sort.
  //
  //   CLEAR      every station has a standing place at STREET LEVEL. Standing
  //              on top of a retaining wall is reachable but is not walking
  //              down the street, so those cells are excluded here. An
  //              obstruction that leaves the street connected — a scarp with a
  //              ramp ten metres away — is reported, not failed: the player
  //              gets through, with a jog.
  const streetLevel = (x, z) => {
    const i = toI(x), j = toI(z);
    if (i < 0 || j < 0 || i >= N || j >= N || !seen[idx(i, j)]) return false;
    // Not "close to terrain height" — that would exclude the authored step
    // flights that carry a street over a scarp, which ARE the street. What
    // does not count is standing on top of something solid.
    return !world.onSolidTop(toX(i), toX(j), feet[idx(i, j)]);
  };
  /** What is standing at (x, z), for naming a culprit in the report. */
  const obstruction = (x, z) => {
    const g = groundAt(x, z, terrain(x, z));
    for (const v of world.near(x - RADIUS, z - RADIUS, x + RADIUS, z + RADIUS)) {
      if (!v.solid || v.maxY <= g + STEP_HEIGHT || v.minY >= g + BODY) continue;
      if (!world.isFree(x, z, RADIUS, g, BODY, STEP_HEIGHT)) {
        return `${v.tag || 'untagged'} (${(v.maxY - g).toFixed(2)}m above ground)`;
      }
    }
    return 'nothing solid — the ground itself is unreachable';
  };

  const failures = [];
  console.log('\nstreets:');
  for (const st of (town.streets || [])) {
    const half = (st.width || 5) * 0.5 + 1.5;
    const pts = st.path.map(p => [p[0], p[1]]);   // paths are [x, z]; D-024
    let stations = 0;
    const severed = [], obstructed = [];
    for (let i = 0; i < pts.length - 1; i++) {
      const [ax, az] = pts[i], [bx, bz] = pts[i + 1];
      const len = Math.hypot(bx - ax, bz - az);
      const n = Math.max(1, Math.round(len));
      const dx = (bx - ax) / len, dz = (bz - az) / len;
      for (let k = 0; k <= n; k++) {
        const t = (k / n) * len;
        const x = ax + dx * t, z = az + dz * t;
        stations++;
        // Scan across the width; a fountain or a stall in the middle is fine
        // as long as there is a way past it.
        let any = false, level = false;
        for (let u = -half; u <= half + 1e-6; u += 0.25) {
          const px = x - dz * u, pz = z + dx * u;
          if (reachable(px, pz)) any = true;
          if (streetLevel(px, pz)) { level = true; break; }
        }
        if (!any) severed.push([x, z]);
        else if (!level) obstructed.push([x, z]);
      }
    }
    const pass = severed.length === 0;
    console.log(`  ${pass ? 'PASS' : 'FAIL'} ${st.id.padEnd(12)} ` +
                `${stations} stations · ${severed.length} severed · ` +
                `${obstructed.length} obstructed at street level`);
    for (const [label, list] of [['severed', severed], ['obstructed', obstructed]]) {
      if (!list.length) continue;
      const [x, z] = list[0];
      console.log(`       first ${label} at (${x.toFixed(1)}, ${z.toFixed(1)}): ` +
                  `${obstruction(x, z)}` +
                  (list.length > 1 ? `  (+${list.length - 1} more)` : ''));
    }
    if (!pass && st.id === 'ford_road') {
      failures.push(`Ford Road is severed at ${severed.length} station(s) — ` +
                    `no reachable standing place within ${half.toFixed(1)} m of ` +
                    `the centreline, first at (${severed[0][0].toFixed(1)}, ` +
                    `${severed[0][1].toFixed(1)})`);
    } else if (!pass) {
      console.log(`       (${st.id} is not a hard gate; Ford Road is)`);
    }
    if (STRICT && obstructed.length && st.id === 'ford_road') {
      failures.push(`Ford Road is obstructed at street level at ` +
                    `${obstructed.length} station(s)`);
    }
  }

  if (DUMP) {
    const rows = [];
    for (let j = 0; j < N; j += 2) {
      let s = '';
      for (let i = 0; i < N; i += 2) s += seen[idx(i, j)] ? '.' : '#';
      rows.push(s);
    }
    fs.writeFileSync(DUMP, rows.join('\n'));
    console.log(`\nmap written to ${DUMP} (1 char = 1m, '.' walkable)`);
  }

  if (badDoors.length) {
    console.log(`\n${badDoors.length} unreachable door(s): ` +
                badDoors.map(d => d.id).join(', '));
    if (STRICT) failures.push(`${badDoors.length} venue doors unreachable`);
  }
  if (badMarks.length) {
    console.log(`${badMarks.length} unreachable landmark(s): ` +
                badMarks.map(l => l.id).join(', '));
    if (STRICT) failures.push(`${badMarks.length} landmarks unreachable`);
  }

  if (failures.length) {
    console.error('\nFAIL');
    for (const f of failures) console.error('  ' + f);
    process.exit(1);
  }
  console.log('\nOK — Ford Road is traversable end to end.');
}

main().catch(e => { console.error(e); process.exit(2); });
