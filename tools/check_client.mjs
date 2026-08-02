#!/usr/bin/env node
/**
 * Client smoke test — boots the real client in a real browser and walks.
 *
 *     node tools/check_client.mjs
 *     node tools/check_client.mjs --headed --shot review/shots/walk.png
 *
 * `tools/check_walkable.mjs` proves the collision DATA is walkable. It cannot
 * prove the client is wired to it: a controller that never receives the world,
 * a module that throws on load, a fetch that 404s — all of those leave the
 * prover green and the town unplayable. This runs the actual page, fails on any
 * console error, and then presses W and checks the player moved.
 *
 * The walk route follows Ford Road south from the spawn, which is the exact
 * traverse the town shipped unable to make.
 */

import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { chromium } from 'playwright';

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

/** Walk waypoints along Ford Road's authored centreline, gate flat to south gate.
 *
 * `streets[].path` is [x, z] since D-024 — the level comes from terrain — so
 * this is a plan-space route and the controller resolves the ground itself.
 */
function fordRoute() {
  const town = JSON.parse(fs.readFileSync(
    path.join(REPO, 'content/town/hearthmere.json'), 'utf8'));
  const ford = (town.streets || []).find(s => s.id === 'ford_road');
  if (!ford) throw new Error('no ford_road in hearthmere.json');
  // South to the gate threshold. The cap used to be 46, and the authored path
  // has no vertex between z=40 and z=52, so the route ENDED at z=40 while the
  // arrival line was z>40 and the loop's break was z>44. The player walked the
  // whole street, arrived on its last waypoint, and then stood there
  // oscillating over a 3 cm step until the distance budget ran out — 75 m of
  // "walking" on the spot, reported for two waves as "something on Ford Road
  // is blocking it". Nothing was. Below, the arrival test is derived from the
  // route instead of typed, so the two can never disagree again.
  const pts = ford.path.filter(([, z]) => z >= -32 && z <= 74);
  // Every third vertex is roughly a waypoint every 24 m, which is far enough
  // apart that the controller drives rather than oscillates between them.
  const out = pts.filter((_, i) => i % 3 === 0);
  if (out[out.length - 1] !== pts[pts.length - 1]) out.push(pts[pts.length - 1]);

  // BUILD_DIRECTIVE §3: the spawn is no longer standing in the street. It is
  // on the summoning altar INSIDE the Church of Summoning, 34 m east of Ford
  // Road with a nave, a portal, a perron and a churchyard terrace between it
  // and the first waypoint. The controller steers straight at whatever it is
  // given, so without the egress leg it walks the player into the north aisle
  // wall and the harness reports a blocked Ford Road — which is exactly what
  // it did the first time the church existed.
  //
  // The leg is authored, not derived, because it is the traverse §9's first
  // box names: altar -> down the nave -> through the west door -> down the
  // perron -> across Kirk Green -> onto Ford Road. If a later edit closes any
  // of those, this check should fail, and it should fail HERE.
  const spawn = town.playerSpawn && town.playerSpawn.pos;
  if (spawn) {
    const egress = [[spawn[0], spawn[2]],   // the altar
                    [36.0, -0.5],           // down the nave
                    [30.5, -0.5],           // through the portal, head of the perron
                    [23.0, -0.5],           // foot of the perron, on the terrace
                    [19.0, -0.5],           // Kirk Green
                    [13.5, -0.5]];          // Kirk Green's mouth onto Ford Road
    out.unshift(...egress);
  }
  return out;
}

const argv = process.argv.slice(2);
const HEADED = argv.includes('--headed');
const SHOT = argv.includes('--shot') ? argv[argv.indexOf('--shot') + 1] : null;
const PORT = 8099;

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function main() {
  const server = spawn(process.execPath, [path.join(REPO, 'client/serve.mjs')],
                       { env: { ...process.env, PORT: String(PORT) }, stdio: 'pipe' });
  server.stderr.on('data', d => process.stderr.write('[serve] ' + d));
  await sleep(700);

  const browser = await chromium.launch({
    headless: !HEADED,
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'],
  });
  // Small viewport on purpose. Every pumped frame is a full software render of
  // a 300k-tri town with 4k shadow maps and bloom under SwiftShader, and this
  // test is about whether the player MOVES, not what the frame looks like —
  // tools/render/shoot.mjs owns the picture.
  // 16:9, matching tools/render/town.mjs's default 1600x900. Pixels are cheap
  // to change and irrelevant to a draw-call count, but ASPECT is not: the
  // frustum cull is what decides how many batches survive, and a 1.60 harness
  // measuring a 1.78 client is a third reason for the two to disagree.
  const page = await browser.newPage({ viewport: { width: 640, height: 360 } });

  const errors = [], warns = [], unbuilt = new Set();

  // A venue the town declares but nobody has generated yet 404s three times a
  // boot — mesh, collision, entities. That is a REAL gap, and `tools/validate.py`
  // hard-fails on every one of them by name, which is the right place for it.
  // Counting them here as well only means that during a rebuild, when 22 venues
  // are legitimately missing, this check is red for a reason it cannot help
  // with, and a genuine client regression — a thrown exception, a broken import,
  // a bad shader — is invisible in the noise. So they are bucketed separately
  // and reported, and the pass/fail gate is "any OTHER console error".
  const UNBUILT = /\/(?:assets\/meshes|content\/collision|content\/entities)\/([a-z_0-9]+)\.(?:gltf|bin|json)$/;
  const classify = (text, url) => {
    const m = (url || text).match(UNBUILT);
    if (m) { unbuilt.add(m[1]); return; }
    errors.push(text);
  };

  page.on('console', m => {
    const t = m.type();
    // The browser's bare "Failed to load resource: 404" line does not name the
    // resource; the response hook below does, so drop the anonymous twin.
    if (t === 'error') {
      if (/Failed to load resource/.test(m.text())) return;
      errors.push(m.text());
    } else if (t === 'warning') warns.push(m.text());
  });
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('requestfailed', r => classify(`request failed: ${r.url()}`, r.url()));
  page.on('response', r => {
    if (r.status() >= 400) classify(`HTTP ${r.status()} ${r.url()}`, r.url());
  });

  await page.goto(`http://localhost:${PORT}/`, { waitUntil: 'load' });
  await page.waitForFunction('globalThis.hm && globalThis.hm.player', null,
                             { timeout: 60000 });

  const info = await page.evaluate(() => ({
    volumes: hm.collision.volumes.length,
    venues: hm.collision.venues.length,
    entities: hm.entities.length,
    spawn: hm.player.position.toArray(),
    status: document.querySelector('#status').textContent,
  }));
  console.log(`booted: ${info.volumes} collision volumes across ${info.venues} ` +
              `placements, ${info.entities} entities`);
  console.log(`status: ${info.status}`);
  console.log(`spawn:  ${info.spawn.map(v => v.toFixed(2)).join(', ')}`);

  // Walk the length of Ford Road, north gate to south waymarkers — the
  // traverse the town shipped unable to make.
  //
  // The route steers round the fountain, which stands at the centre of the
  // square with the street's authored centreline running through it. This is a
  // movement test, not a pathfinder: it presses W and turns the camera toward
  // the next waypoint, exactly as a player does.
  //
  // The screenshot in the loop is load-bearing, not diagnostic: headless
  // Chromium drives requestAnimationFrame from the compositor and stops
  // producing frames when nothing asks for one, so the client's frame loop
  // halts after ~25 frames. Forcing a capture forces a frame. Without it this
  // test reports "the player does not move" against a client that is fine.
  // Waypoints are READ FROM THE CARRIAGEWAY, not typed. Ford Road bends: it
  // runs at x = -1.6 at the gate flat and x = +9.5 at the market place, and
  // the terrace ramps are cut where it actually crosses each scarp. A route
  // hardcoded on x = 0 walked into the market scarp's retaining wall and
  // reported the street as blocked when the street was fine — a check that
  // fails on a town that works is worse than no check.
  // ---------------------------------------------------------------------
  // Settle before the clock starts.
  //
  // The walk used to be a fixed 30 samples, and each sample advances the
  // player by however far the frame loop happened to get between screenshots.
  // Under SwiftShader that is dominated by whatever else the process is
  // doing — including the first few hundred milliseconds of LOD preparation
  // and texture upload, which are the most expensive frames of the run and
  // land inside the walk. Measured across 8 runs on identical bits the walk
  // ended at z = 36.3, 41.0, 43.5, 43.7, 44.3, 44.6, 45.1 against a `> 40`
  // pass line: a ~12% false-failure rate on a town that is fine. A gate that
  // fails at random is a gate everyone learns to re-run.
  //
  // Two changes make it deterministic in OUTCOME. First, wait here until the
  // asset and LOD pipeline is quiet, so the walk never pays for it. Second,
  // budget the walk by DISTANCE REMAINING rather than by sample count (below):
  // the player either reaches the end of Ford Road or is genuinely stuck, and
  // frame rate only changes how many samples that takes.
  const settle = await page.evaluate(async () => {
    const t0 = performance.now();
    const idle = () => new Promise(r => requestAnimationFrame(() => r()));
    let quiet = 0, lastLod = -1;
    for (let i = 0; i < 600 && quiet < 12; i++) {
      await idle();
      const s = hm.visibility.stats;
      const sig = `${s.groups}/${s.drawn}/${s.byLod.join(',')}`;
      quiet = sig === lastLod ? quiet + 1 : 0;
      lastLod = sig;
    }
    return { ms: Math.round(performance.now() - t0), stable: quiet >= 12 };
  });
  console.log(`settle: ${settle.ms} ms to a stable LOD/batch set` +
              `${settle.stable ? '' : ' (TIMED OUT — treated as settled)'}`);

  // ---------------------------------------------------------------------
  // Instrument parity (D-051). Before the walk moves the camera, ask the
  // client for the frame `tools/render/town.mjs --views arrival` shoots, from
  // the identical camera and the identical sun rig, and print it next to the
  // gameplay reading. If those two numbers ever diverge again, THIS line is
  // where it shows, instead of two reports in two directories disagreeing by
  // 3x for a wave with nobody able to say which was true.
  const parity = await page.evaluate(() => {
    const s = hm.town.playerSpawn;
    if (!s || !hm.shoot) return null;
    const y = (s.facingDeg ?? 180) * Math.PI / 180;   // compass: forward (sin, 0, -cos)
    const EYE = 1.62;
    const at = [s.pos[0], s.pos[1] + EYE, s.pos[2]];
    const look = [s.pos[0] + Math.sin(y) * 40, s.pos[1] + EYE * 0.92,
                  s.pos[2] - Math.cos(y) * 40];
    const p = hm.shoot({ pos: at, look, fov: 55 });
    return { drawCalls: p.drawCalls, triangles: p.triangles, stages: p.stages,
             batches: p.batches.drawn, at, look };
  });
  if (parity) {
    const st = parity.stages;
    console.log(`parity: arrival camera (${parity.at.map(v => v.toFixed(1)).join(', ')}) ` +
                `-> ${parity.drawCalls} draws / ${parity.triangles.toLocaleString()} tris`);
    console.log(`        = scene ${st.scene.draws} + shadow ${st.shadow.draws} + ` +
                `ao ${st.ao.draws} + post ${st.post.draws}, ` +
                `${parity.batches} batches drawn`);
    console.log(`        compare: node tools/render/town.mjs --views arrival`);
  }

  // ---------------------------------------------------------------------
  // THE PARITY GATE.
  //
  // Printing the two numbers side by side was already here and it was not
  // enough: pass 04 got them to 0.7%, pass 05 found them 36% apart, and the
  // drift was only caught because the art director ran five probe renders by
  // hand. A number nothing compares is a number nothing defends.
  //
  // `tools/render/town.mjs` now writes its own arrival reading to
  // review/parity.json every time it shoots that view. This reads it back and
  // fails on drift beyond its recorded tolerance. Two independent renderers
  // agreeing is the ONLY evidence either of them is measuring the shipped town;
  // when they disagree, at least one report in this repository is fiction and
  // the build cannot say which.
  //
  // A missing file is not a pass and not a failure — it means nobody has shot
  // the town since the contract existed, and it says so.
  const parityDrift = (() => {
    const P = path.join(REPO, 'review/parity.json');
    if (!parity || !fs.existsSync(P)) return null;
    let ref;
    try { ref = JSON.parse(fs.readFileSync(P, 'utf8')); } catch { return null; }
    if (!ref || ref.view !== 'arrival' || !ref.drawCalls) return null;
    const tol = ref.tolerance ?? 0.03;
    const d = (parity.drawCalls - ref.drawCalls) / ref.drawCalls;
    return { ref, tol, d };
  })();
  if (parityDrift) {
    const { ref, tol, d } = parityDrift;
    console.log(`        vs ${ref.instrument} (${ref.recorded}): ${ref.drawCalls} draws, ` +
                `client is ${(d * 100).toFixed(1)}% ${d >= 0 ? 'higher' : 'lower'} ` +
                `(tolerance ${(tol * 100).toFixed(0)}%)`);
  } else if (parity) {
    console.log(`        no review/parity.json — run tools/render/town.mjs --views arrival ` +
                `to record the contract`);
  }

  const ROUTE = fordRoute();
  const track = [];
  // The walk runs on a FIXED TIMESTEP inside the page, not on rendered frames.
  //
  // The old loop forced a frame per sample with a screenshot, because headless
  // Chromium stops driving requestAnimationFrame when nothing asks for one.
  // Two things were wrong with that and the second is fatal:
  //
  // 1. `client/src/main.js`'s frame loop clamps dt to 50 ms, so the distance a
  //    player covers per sample depends on how fast the frame happened to
  //    render. Measured across 8 runs on identical bits the walk ended at
  //    z = 36.3, 41.0, 43.5, 43.7, 44.3, 44.6, 45.1 against a `> 40` pass
  //    line: a ~12% false-failure rate on a town that is fine.
  // 2. On the finished town — 32 venues, 537 batches, 1.15 M triangles — a
  //    single SwiftShader frame now exceeds Playwright's 30 s screenshot
  //    timeout, so the check does not fail 12% of the time, it fails 100% of
  //    the time with `page.screenshot: Timeout 30000ms exceeded`. Measured
  //    three times on identical bits before this change.
  //
  // `hm.step(dt)` advances physics, collision, the camera rig and visibility
  // with no render at all, so the whole walk is one `page.evaluate`, the
  // outcome depends on nothing but the world, and it takes about a second.
  // Budgeted by DISTANCE TRAVELLED, so "did not arrive" can only mean the
  // player is genuinely obstructed.
  const routeLen = ROUTE.reduce((s, p, i) =>
    i ? s + Math.hypot(p[0] - ROUTE[i - 1][0], p[1] - ROUTE[i - 1][1]) : 0, 0);
  const walk = await page.evaluate(({ route, budget }) => {
    const DT = 1 / 60;                  // fixed: the whole point
    const MAX_STEPS = 60 * 300;         // 5 simulated minutes; a hang, not a slow box
    const out = [];
    let leg = 0, travelled = 0, stalled = 0, steps = 0, arrived = false;
    hm.player.keys.add('KeyW');
    hm.player.keys.add('ShiftLeft');
    let prev = hm.player.position.toArray();
    out.push(prev);
    // ARRIVAL IS THE LAST WAYPOINT, not a typed z. The two were separate
    // numbers (route ended z=40, break was z>44, pass line was z>40) and they
    // drifted apart, which reported a walkable street as blocked.
    const end = route[route.length - 1];
    for (; steps < MAX_STEPS; steps++) {
      const [gx, gz] = route[leg];
      const p0 = hm.player.position;
      // yaw is the camera heading; W drives along -Z rotated by it.
      hm.player.yaw = Math.atan2(-(gx - p0.x), -(gz - p0.z));
      hm.step(DT);
      const p = hm.player.position.toArray();
      const d = Math.hypot(p[0] - prev[0], p[2] - prev[2]);
      travelled += d;
      // A tenth of a step at run speed. Sampled per simulated frame, so this
      // is a property of the world, not of the machine.
      stalled = d < 0.01 ? stalled + 1 : 0;
      prev = p;
      if (steps % 6 === 0) out.push(p);
      if (Math.hypot(p[0] - gx, p[2] - gz) < 2.5 && leg < route.length - 1) leg++;
      if (Math.hypot(p[0] - end[0], p[2] - end[1]) < 2.0) { arrived = true; break; }
      if (travelled > budget) break;            // walked far enough to prove it
      if (stalled >= 120) break;                // wedged for 2 s: a real defect
    }
    hm.player.keys.clear();
    out.push(hm.player.position.toArray());
    return { track: out, travelled, steps, stalled, arrived };
  }, { route: ROUTE, budget: routeLen * 1.6 });
  track.push(...walk.track);
  const travelled = walk.travelled;
  const BUDGET = routeLen * 1.6;
  console.log(`walk:   ${walk.steps} fixed 1/60 s steps ` +
              `(${(walk.steps / 60).toFixed(1)} simulated seconds)`);

  // ---------------------------------------------------------------------
  // Culling and LOD, measured in the shipping client (Directive §7).
  //
  // tools/render/town.mjs measures this too, and more thoroughly — but it
  // measures tools/render/town.html. This is the only place the numbers come
  // from client/src/main.js, and the two have diverged before (D-023). If the
  // LOD chain fails to load here, or the cell cull is not wired to the frame
  // loop, every batch stays at level 0 and this is what says so.
  // ---------------------------------------------------------------------
  // A screenshot first: it forces one more frame, so renderer.info describes a
  // frame that was actually drawn from where the player is standing now.
  //
  // ONE frame, and it gets four minutes. A full software render of the
  // finished town under SwiftShader is tens of seconds and blows Playwright's
  // 30 s default — which is exactly how this check went from flaky to dead.
  // The walk above no longer pays this cost at all; only the perf reading and
  // the optional --shot do, and they are one frame each.
  await page.screenshot({ type: 'jpeg', quality: 20, timeout: 240000 });
  const perf = await page.evaluate(() => {
    const p = hm.perf();
    return { ...p, cells: hm.visibility.occupiedCells().length };
  });
  // The SAME decomposition tools/render/town.mjs prints, from the same module
  // (client/src/perf.js). Before that module existed this line said "2,153 draw
  // calls whole frame" and the harness said 727 for the same town, and no one
  // could tell which was true. Both are true; they were counting different
  // things. The number against the §7 budget is the whole frame.
  const st = perf.stages;
  console.log(`perf:   ${perf.drawCalls} draws whole frame = scene ${st.scene.draws} + ` +
              `shadow ${st.shadow.draws} + ao ${st.ao.draws} + post ${st.post.draws}`);
  console.log(`        ${perf.trianglesDrawn.toLocaleString()} triangles = scene ` +
              `${Math.round(st.scene.tris).toLocaleString()} + shadow ` +
              `${Math.round(st.shadow.tris).toLocaleString()} + ao ` +
              `${Math.round(st.ao.tris).toLocaleString()}`);
  console.log(`        ${perf.batches.drawn}/${perf.batches.total} batches over ` +
              `${perf.cells} cells · LOD ${perf.batches.byLod.join('/')} · culled ` +
              `${perf.batches.culledDistance} far / ${perf.batches.culledFrustum} off-screen` +
              `${perf.batches.culledPortal ? ` / ${perf.batches.culledPortal} interior` : ''}`);

  const a = track[0], b = track[track.length - 1];
  console.log(`walked: (${a[0].toFixed(1)}, ${a[2].toFixed(1)}) → ` +
              `(${b[0].toFixed(1)}, ${b[2].toFixed(1)}), ` +
              `${travelled.toFixed(1)} m of path over ${track.length} samples ` +
              `(budget ${BUDGET.toFixed(0)} m over a ${routeLen.toFixed(0)} m route)`);
  console.log(`ground: y ${Math.min(...track.map(p => p[1])).toFixed(2)} … ` +
              `${Math.max(...track.map(p => p[1])).toFixed(2)} ` +
              `(the town falls ~4 m south to north)`);
  // Drift is measured against the ROUTE, not against x = 0.
  //
  // `Math.abs(p[0])` assumed the walk began on Ford Road's centreline, which was
  // true while playerSpawn was the north gate. BUILD_DIRECTIVE §3 moved the
  // spawn to the church altar at x = 43, so the first sample was 43 m "off Ford
  // Road" before the player had taken a step, and the check failed on a town
  // that was fine. Distance to the polyline the player is being steered along
  // says the thing this check is actually for — "collision shoved it sideways"
  // — and keeps saying it wherever the route goes next.
  const segDist = (p, a, b) => {
    const vx = b[0] - a[0], vz = b[1] - a[1];
    const L2 = vx * vx + vz * vz;
    const t = L2 < 1e-9 ? 0 : Math.max(0, Math.min(1, ((p[0] - a[0]) * vx + (p[2] - a[1]) * vz) / L2));
    return Math.hypot(p[0] - (a[0] + t * vx), p[2] - (a[1] + t * vz));
  };
  const spine = [[track[0][0], track[0][2]], ...ROUTE];
  const maxDrift = Math.max(...track.map(p => Math.min(
    ...spine.slice(0, -1).map((a, i) => segDist(p, a, spine[i + 1])))));
  const lowest = Math.min(...track.map(p => p[1]));
  const reachedSouth = walk.arrived;

  if (SHOT) {
    await page.screenshot({ path: path.join(REPO, SHOT), timeout: 240000 });
    console.log(`shot:   ${SHOT}`);
  }

  await browser.close();
  server.kill();

  if (unbuilt.size) {
    console.log(`unbuilt: ${unbuilt.size} venue(s) declared by the town with no ` +
                `mesh/collision/entities on disk — ${[...unbuilt].sort().join(', ')}`);
    console.log(`         (not counted as client errors; tools/validate.py fails on each)`);
  }

  const fails = [];
  if (errors.length) fails.push(`${errors.length} console error(s)`);
  if (travelled < 8) fails.push(`player travelled only ${travelled.toFixed(1)} m ` +
                                `— the controller is not moving at all`);
  // "Did not arrive" is only a defect if the walk was given the distance to
  // arrive in. Exhausting a budget of 1.6x the route length means the player
  // is being steered in circles or shoved off course, which the drift check
  // below names; running out of SAMPLES on a slow machine used to be reported
  // as a blocked street, and that was the whole flake.
  else if (!reachedSouth) fails.push(`player stopped at z=${b[2].toFixed(1)} after ` +
                                     `${travelled.toFixed(0)} m of walking (route is ` +
                                     `${routeLen.toFixed(0)} m) — something on Ford ` +
                                     `Road is blocking it`);
  // A "wandered off the street entirely" bound, not a centreline tolerance:
  // the controller steers toward the next waypoint every sample, so a few
  // metres of overshoot on a corner is normal movement, not a defect.
  if (maxDrift > 12.0) fails.push(`player strayed ${maxDrift.toFixed(1)} m from the ` +
                                  `walk route — collision is pushing it sideways`);
  if (lowest < -3.5) fails.push(`player fell to y=${lowest.toFixed(2)}, below the ` +
                                `water line — ground following is broken`);
  // The budget is judged at the ARRIVAL camera, not at wherever the walk
  // happened to stop.
  //
  // The end of the walk is the south waymarkers, outside the wall, looking away
  // from the town — 419 draws on a town that costs 1,390 at the spawn. Gating
  // there does not test the budget, it tests where the route ends, and it would
  // pass a town that had doubled in cost. The arrival frame is fixed, authored
  // (BUILD_DIRECTIVE §3), the most expensive composition in the build, and the
  // one `tools/render/town.mjs --views arrival` shoots — so the two instruments
  // gate on the same frame as well as measuring it the same way.
  if (parityDrift && Math.abs(parityDrift.d) > parityDrift.tol)
    fails.push(`INSTRUMENT DRIFT: this client measures ${parity.drawCalls} draws at the ` +
               `arrival camera; ${parityDrift.ref.instrument} recorded ` +
               `${parityDrift.ref.drawCalls} on ${parityDrift.ref.recorded} ` +
               `(${(parityDrift.d * 100).toFixed(1)}%, tolerance ` +
               `${(parityDrift.tol * 100).toFixed(0)}%). One of the two reports in this ` +
               `repository is fiction. Do not publish a draw-call number until they agree`);

  const gateFrame = parity || perf;
  const gateWhere = parity ? 'the arrival camera' : 'the end of the walk';
  if (gateFrame.drawCalls > perf.budget.drawCalls)
    fails.push(`${gateFrame.drawCalls} draw calls at ${gateWhere} (scene ` +
               `${gateFrame.stages.scene.draws} + shadow ${gateFrame.stages.shadow.draws} + ` +
               `ao ${gateFrame.stages.ao.draws} + post ${gateFrame.stages.post.draws}), ` +
               `over the §7 budget of ${perf.budget.drawCalls}`);
  if ((gateFrame.triangles ?? gateFrame.trianglesDrawn) > perf.budget.triangles)
    fails.push(`${(gateFrame.triangles ?? gateFrame.trianglesDrawn).toLocaleString()} ` +
               `triangles at ${gateWhere}, over the §7 budget of ` +
               `${perf.budget.triangles.toLocaleString()}`);
  // Every batch sitting at level 0 means the MSFT_lod alternates never loaded —
  // the file is still correct, so nothing looks wrong, and the town silently
  // costs what it cost before any of this existed.
  if (perf.batches.total > 20 && perf.batches.byLod.slice(1).every(n => n === 0))
    fails.push(`all ${perf.batches.drawn} drawn batches are at LOD0 — the LOD chain ` +
               `did not load (client/src/lod.js prepareLods)`);
  if (perf.batches.total > 20 &&
      perf.batches.culledDistance + perf.batches.culledFrustum === 0)
    fails.push(`nothing was culled from ${perf.batches.total} batches — culling is ` +
               `not wired to the frame loop`);
  for (const w of warns.slice(0, 10)) console.log(`  warn: ${w}`);
  for (const e of errors) console.error(`  ERROR: ${e}`);
  if (fails.length) {
    console.error('\nFAIL: ' + fails.join('; '));
    process.exit(1);
  }
  console.log('\nOK — client boots clean and the player walks.');
}

main().catch(e => { console.error(e); process.exit(2); });
