/**
 * Hearthmere client — renderer, scene assembly, and the frame loop.
 *
 * Reads the authoritative town layout from content/ and assembles a scene from
 * it. Per docs/ARCHITECTURE.md §1 the client may READ authoritative data but
 * never authors gameplay state: interactions go out as intents (src/net.js).
 */

import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

import { installAtmosphere, makePostChain } from './atmosphere.js';
import { SunRig } from './shadows.js';
import { ThirdPersonController } from './player.js';
import { CollisionWorld, loadTerrain } from './collision.js';
import { LocalTransport } from './net.js';
import { Ambient } from './ambient.js';
import { Water } from './water.js';
import { VisibilitySet, prepareLods } from './lod.js';
import { FrameProbe, BUDGET, formatFrame } from './perf.js';
import { Sim } from '../../server/src/sim.js';

const $ = s => document.querySelector(s);
const status = m => { const el = $('#status'); if (el) el.textContent = m; };

// ---------------------------------------------------------------------------
// Renderer
// ---------------------------------------------------------------------------

const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
renderer.setSize(innerWidth, innerHeight);
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;    // Art Bible §5
renderer.toneMappingExposure = 1.05;
renderer.outputColorSpace = THREE.SRGBColorSpace;
document.body.appendChild(renderer.domElement);

const scene = new THREE.Scene();
// Far plane at 2000 m, not 500.
//
// 500 m was inherited from a build whose ground was a 300 m plane. The terrain
// plate is a 576 m square, so its corners stand at 407 m and were being clipped
// out of the frame; the horizon skirt that closes the world edge reaches
// 1200 m and would have been clipped entirely. The review harness has always
// run 2000 m, and D-023's rule is that the harness must measure the town the
// client draws — a different far plane is a different town.
const camera = new THREE.PerspectiveCamera(55, innerWidth / innerHeight, 0.1, 2000);

// ---------------------------------------------------------------------------
// Sky, image-based lighting, aerial perspective, horizon
// ---------------------------------------------------------------------------
//
// All four from `client/src/atmosphere.js`, driven by the `atmosphere` block in
// content/town/hearthmere.json. This file used to carry its own two-stop
// gradient dome and no fog at all; `tools/render/town.html` and
// `tools/render/viewer.html` carried two more copies. See D-049 — and D-009,
// which is the same rule about the same file for the same reason.
//
// Installed in boot(), once the town document is in hand.
let ENV = null, post = null;

// ---------------------------------------------------------------------------
// Lighting — must match tools/render/viewer.html exactly, or the town will not
// look like the renders it was signed off from.
// ---------------------------------------------------------------------------

// Read from content/town/hearthmere.json so the client and the review harness
// cannot drift apart — and so the town looks like the renders each venue was
// signed off from. Populated in boot(); see applyLighting().
let EL = 38 * Math.PI / 180, AZ = 125 * Math.PI / 180;

// THE SUN IS NOT A LIGHT HERE ANY MORE. It is `client/src/shadows.js SunRig` —
// three cascades, fitted to the camera frustum, built in boot() once the
// authored `lighting.shadows` block is in hand and driven by `fitCascades()`
// once per frame.
//
// What stood here was a single DirectionalLight with a 4096 map over a 92 m
// box: 44.5 texels per metre at every distance, which is a 2.25 cm shadow texel
// on a floor 2 m from the eye. `review/reports/ad-town-04.md` §1 is the picture
// of what that does to the spawn frame, and `docs/ARCHITECTURE.md` §5 has
// specified cascades since before v2 started. The rig is shared with
// tools/render/town.html and tools/render/viewer.html for the reason D-009
// exists: three renderers with three shadow rigs are three different towns.
let rig = null;

// Desaturated sky tint: the PMREM environment already supplies saturated blue,
// and stacking both turns every shadowed facade cyan.
const hemi = new THREE.HemisphereLight(new THREE.Color('#AFC9E0'), new THREE.Color('#8A7352'), 1.35);
const amb = new THREE.AmbientLight(new THREE.Color('#6B5A46'), 0.55);
scene.add(hemi, amb);

/** Apply the authoritative rig from content/. */
function applyLighting(L) {
  if (!L) return;
  EL = L.sunElevationDeg * Math.PI / 180;
  AZ = L.sunAzimuthDeg * Math.PI / 180;
  if (rig) rig.applyLighting(L);           // colour, intensity and sun angle
  hemi.color.set(L.hemisphere.sky); hemi.groundColor.set(L.hemisphere.ground);
  hemi.intensity = L.hemisphere.intensity;
  amb.color.set(L.ambient.color); amb.intensity = L.ambient.intensity;
  bounce.color.set(L.bounce.color); bounce.intensity = L.bounce.intensity;
  rim.color.set(L.rim.color); rim.intensity = L.rim.intensity;
  renderer.toneMappingExposure = L.exposure;
  bounce.position.set(-Math.cos(EL) * Math.sin(AZ) * 30, 8, -Math.cos(EL) * Math.cos(AZ) * 30);
  rim.position.set(-Math.sin(AZ) * 40, 14, -Math.cos(AZ) * 40);
}

const bounce = new THREE.DirectionalLight(new THREE.Color('#C9A87E'), 0.55);
bounce.position.set(-Math.cos(EL) * Math.sin(AZ) * 30, 8, -Math.cos(EL) * Math.cos(AZ) * 30);
scene.add(bounce);

const rim = new THREE.DirectionalLight(new THREE.Color('#8FB8E8'), 1.15);
rim.position.set(-Math.sin(AZ) * 40, 14, -Math.cos(AZ) * 40);
scene.add(rim);

// ---------------------------------------------------------------------------
// Post chain — docs/ARCHITECTURE.md §5, built by the shared module in boot().
// ---------------------------------------------------------------------------

// EffectComposer calls renderer.render() once per pass, and renderer.info
// resets itself at the start of each. Left alone, reading the counters after a
// composed frame reports the cost of the LAST pass — one full-screen quad — so
// the client cheerfully claimed "1 draw call, 1 triangle" for a town of 72
// buildings.
//
// `FrameProbe` takes `autoReset` off and resets once per frame, so the counters
// mean the whole frame, AND splits that frame into scene / shadow / ao / post.
// It is the same module `tools/render/town.html` measures with — see the header
// of `client/src/perf.js` for why the two used to disagree by 3x.
const probe = new FrameProbe(renderer);

// ---------------------------------------------------------------------------
// World assembly
// ---------------------------------------------------------------------------

const loader = new GLTFLoader();
const townRoot = new THREE.Group();
scene.add(townRoot);
let CELL = 16;

// Culling, LOD and portals (client/src/lod.js). The partition it works on is
// the 16 m cell grid of docs/ARCHITECTURE.md §3 — the same one entities record
// and the same one network interest management will subscribe on — except that
// it is now the BATCH's cell rather than the venue's. That distinction is the
// whole point: `streets` is one venue spanning 77 cells, so culling it as a
// venue culls nothing.
let visibility = null;

// Parsed once per mesh FILE, cloned per placement. A town with six cottages in
// it must not parse six cottages, and — more importantly — must not build six
// copies of the LOD chain.
const meshCache = new Map();

async function loadVenue(v) {
  const file = `/assets/meshes/${v.id}.gltf`;
  if (!meshCache.has(v.id)) {
    meshCache.set(v.id, loader.loadAsync(file)
      .then(g => prepareLods(g))
      .catch(e => { console.warn('missing venue mesh:', file, e.message); return null; }));
  }
  const gltf = await meshCache.get(v.id);
  if (!gltf) return null;

  // clone(true) AFTER prepareLods, so every placement carries its own LOD
  // alternates without a second parse.
  const root = gltf.scene.userData.__placed ? gltf.scene.clone(true) : gltf.scene;
  gltf.scene.userData.__placed = true;

  root.position.set(...v.origin);
  root.rotation.y = (v.rotationDeg || 0) * Math.PI / 180;
  root.updateMatrixWorld(true);

  // The ground is a 576 m heightfield that is visible from everywhere, and it
  // cannot usefully cast shadows onto itself at that scale — a sun-facing
  // heightfield shadowing its own slopes buys acne, not contact.
  const isGround = v.id === 'terrain';

  root.traverse(o => {
    if (!o.isMesh && !o.isInstancedMesh) return;
    o.castShadow = !isGround;
    o.receiveShadow = true;
    if (o.material) o.material.envMapIntensity = 1.0;
  });

  townRoot.add(root);
  // The terrain venue registers too. It opts out of batching and LOD in the
  // generator, so it is one group with a 576 m bounding sphere: the distance
  // test measures to that sphere's SURFACE and therefore never culls the ground
  // out from under the player, which is the failure the old venue-level cull
  // had to be special-cased around.
  visibility.addPlacement(root, gltf.userData?.hm || null, v.instance || v.id);
  // Per-draw attribution, in the same partition the harness uses. This is the
  // only way "the frame costs N" can be followed by "and here is where".
  probe.instrument(root, v.instance || v.id,
                   (x, z) => visibility.cellLabel(x, z), THREE);
  if (!isGround && ambient) ambient.harvest(root);
  // Water is the one material that animates, and it is on the terrain
  // venue (mere, river, harbour) AND on the market square (fountain
  // basin, horse trough), so it is harvested from every placement.
  if (water) water.harvest(root);

  // LAST, and the order is the whole of it. `Ambient.harvestFoliage` and
  // `Water.harvest` both install their own `onBeforeCompile`; CSM installs one
  // too, and `SunRig.register` captures whatever is already there and chains
  // it. Registering first would mean water and foliage overwrite the CSM hook,
  // the `CSM_cascades` uniform never gets a value, every fragment falls into
  // cascade 0 and the town is shadowed by a 12 m box. Registering last chains
  // correctly. A material this never sees is lit by all three cascades at once,
  // i.e. at 3x the sun — `rig.audit()` counts those and perfReport() prints it.
  if (rig) rig.register(root);

  // NO collision is derived here. Build Directive §6 rule 4: collision is
  // authored in the generators and loaded from content/collision/. Taking it
  // from a venue's bounding box is what sealed Ford Road and the market square
  // in v1 — the two places the whole town is arranged around walking through.
  return root;
}

async function loadCollision(town) {
  const readJson = async (path) => {
    const r = await fetch(path).catch(() => null);
    if (!r || !r.ok) { console.warn('no collision data:', path); return null; }
    return r.json();
  };
  return CollisionWorld.load(town, readJson);
}

/** Venue-local → world. Identical to CollisionWorld.addVenue and to
 *  tools/check_walkable.mjs, because all three have to agree on where a thing
 *  is or the prover and the game are describing different towns. */
function toWorld(p, origin, rotationDeg) {
  const a = (rotationDeg || 0) * Math.PI / 180;
  const c = Math.cos(a), s = Math.sin(a);
  return [origin[0] + c * p[0] + s * p[2],
          origin[1] + p[1],
          origin[2] - s * p[0] + c * p[2]];
}

/**
 * Entity records are authored in VENUE-LOCAL space — that is the whole point of
 * a venue being reusable — but every consumer downstream (interaction range,
 * chimney smoke, lamp lights, the sim) compares them against WORLD positions.
 * While every venue sat at the origin those were the same number; they stopped
 * being the same number the moment the town was laid out, and the symptom is
 * that no door, stall or forge in Hearthmere is interactable: `nearest()` looks
 * for the inn's door 4.6 m from the fountain instead of 44 m away where the inn
 * actually is.
 *
 * Composing the placement the town file already declares is reading content, not
 * authoring state, so it belongs here. What does NOT belong here is minting ids:
 * a venue placed twice yields two entities with one id, and the client may not
 * invent a second (ARCHITECTURE §1). Those are reported once, loudly, and the
 * fix is one entity record per placement in the generator.
 */
async function loadEntities(venues) {
  const all = [];
  const seen = new Map();
  const cache = new Map();
  for (const v of venues) {
    if (!cache.has(v.id)) {
      const r = await fetch(`/content/entities/${v.id}.json`).catch(() => null);
      cache.set(v.id, r && r.ok ? await r.json() : null);
    }
    const doc = cache.get(v.id);
    if (!doc) continue;
    for (const e of (doc.entities || [])) {
      const prev = seen.get(e.id);
      if (prev !== undefined) {
        console.warn(`entity id '${e.id}' is emitted by venue '${v.id}' which is ` +
                     `placed more than once; the client cannot mint a second id, ` +
                     `so this instance is not interactable. Fix: one entity record ` +
                     `per placement in the generator.`);
        continue;
      }
      seen.set(e.id, v);
      all.push({
        ...e,
        venue: v.instance || v.id,
        transform: { ...e.transform,
                     pos: toWorld(e.transform.pos, v.origin || [0, 0, 0], v.rotationDeg || 0) },
      });
    }
  }
  return all;
}

// ---------------------------------------------------------------------------
// Ground
// ---------------------------------------------------------------------------

// The ground is the `terrain` venue: `assets/meshes/terrain.gltf`, real graded
// geometry generated from `content/town/terrain.json` — the same file
// `src/terrain.js` evaluates for collision and every generator evaluates for
// placement. There is no flat plane anywhere any more, and there cannot be:
// the town takes a 4 m fall from its south edge to the water, so a plane would
// put every building on the wrong side of the ground (Build Directive §4 and
// §6 rule 3). It loads through the ordinary venue path, which is also how its
// retaining-wall collision reaches CollisionWorld.

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

let player, net, sim, ambient, water, collision, terrain, interactables = [];

async function boot() {
  status('loading town…');
  const town = await (await fetch('/content/town/hearthmere.json')).json();
  CELL = town.grid?.cellSize ?? 16;
  // Before applyLighting, which routes the sun's colour and angle into it.
  rig = new SunRig({ scene, lighting: town.lighting, camera });
  if (!rig.cfg.__authored) {
    console.warn('content/town/hearthmere.json has no `lighting.shadows` block; ' +
                 'the client fell back to shadows.js SHADOW_DEFAULTS. Regenerate ' +
                 'with tools/plan/townplan.py.');
  }
  applyLighting(town.lighting);
  // The caster radius IS the shadow rig's reach. One authored number, or the
  // build pays for casters whose shadows no cascade covers.
  visibility = new VisibilitySet({ grid: town.grid, shadowDistance: rig.cfg.distance });
  // Each cascade draws only the casters whose shadows land in it. The shadow
  // pass was the largest stage in the frame; see SunRig.bindCasters.
  rig.bindCasters(visibility, renderer);
  visibility.onProxyBuilt = (mesh, g) =>
    probe.instrument(mesh, g.venue, (x, z) => visibility.cellLabel(x, z), THREE);
  probe.setShadowCameras(rig.lights.map(l => l.shadow.camera));

  // The shared environmental layer. The horizon skirt stitches to the same
  // height field the player walks on, which is why terrain is loaded here
  // rather than left to the collision step below — a skirt hung off a guessed
  // level shows as a step at the world edge from every camera in the town.
  status('loading terrain…');
  const groundY = await loadTerrain();
  ENV = installAtmosphere({ renderer, scene, town, heightAt: groundY });
  post = makePostChain({
    renderer, scene, camera,
    width: innerWidth, height: innerHeight, atmos: ENV.atmos,
  });
  // Each pass renders under its own stage, so the AO pass's full normal+depth
  // G-buffer — a second complete scene render — is counted as AO and not as a
  // doubled beauty pass.
  probe.wrapComposer(post.composer);
  // The horizon skirt is a MeshStandardMaterial and it fills the bottom of
  // every approach frame. Unregistered it takes the stock lighting path, which
  // loops over every directional light — and the cascades are three copies of
  // one sun, so the world edge would render at 3x the sun and read as a band
  // of white land under a normal sky.
  rig.register(ENV.horizon);
  if (!ENV.atmos.__authored) {
    console.warn('content/town/hearthmere.json has no `atmosphere` block; the ' +
                 'client fell back to atmosphere.js ATMOSPHERE_DEFAULTS. Regenerate ' +
                 'with tools/plan/townplan.py.');
  }

  status('loading entities…');
  // Entities load FIRST: ambient effects (chimney smoke, forge flicker) are
  // declared on entity components, and cloth sway is registered per venue as
  // it loads, so Ambient has to exist before the venue loop runs.
  // Passed the PLACEMENTS, not the venue ids — an entity's world position is
  // only knowable from the placement it belongs to.
  const entities = await loadEntities(town.venues);
  ambient = new Ambient(scene, town, entities);
  // `ambient.wind` is the town's one wind vector; it already drives the cloth
  // and the smoke, and the ripple field answers it too. See client/src/water.js.
  water = new Water(ENV.atmos.water, (town.ambient || {}).wind);

  status('loading venues…');
  for (const v of town.venues) await loadVenue(v);

  status('loading collision…');
  [collision, terrain] = await Promise.all([loadCollision(town), loadTerrain()]);

  sim = new Sim(town, entities);
  net = new LocalTransport(sim);
  interactables = entities.filter(e => e.components?.interactable);

  player = new ThirdPersonController(camera, renderer.domElement);
  player.position.set(...(town.playerSpawn?.pos || [0, 0, -44]));
  // NEGATED, and that is the fix, not a typo. `facingDeg` is a COMPASS heading
  // — docs/areas/hearthmere/TOWN_PLAN.md §6, forward = (sin θ, 0, -cos θ), 90 = east, 270 =
  // west — while player.js runs its own yaw with forward = (-sin y, 0, -cos y).
  // Seeding one from the other unnegated spawned the player facing the mirror
  // of the authored heading: at the church altar, `facingDeg 270` (due west,
  // out through the great west door) put them looking east into the back wall.
  player.yaw = -(town.playerSpawn?.facingDeg ?? 180) * Math.PI / 180;
  player.facing = player.yaw;
  player.bindWorld(collision, terrain);
  scene.add(player.avatar);
  rig.register(player.avatar);

  // Anything sun-lit that `register()` never saw is drawn at `cascades`x the
  // sun. This is the one failure mode of a CSM install that looks like an art
  // bug rather than a code bug, so it is reported rather than hoped about.
  const missed = rig.audit(scene);
  if (missed.missed.length) {
    console.warn(`SunRig: ${missed.missed.length} sun-lit material(s) are not ` +
                 `registered and will render at ${rig.cfg.cascades}x the sun: ` +
                 missed.missed.join(', '));
  }

  // Read-only debug handle. tools/check_client.mjs drives the real client
  // headlessly through this — walking the player down Ford Road in the actual
  // renderer is the only way to catch the class of defect that a static
  // collision prover cannot see, e.g. the controller never being wired up.
  globalThis.hm = { scene, camera, player, collision, terrain, town, entities,
                    visibility, perf: () => perfReport(),
                    // One SIMULATION step at a caller-supplied dt, with no
                    // render. `tools/check_client.mjs` walks the town with
                    // this at a fixed timestep, which is the only way that
                    // check can be deterministic: the frame loop below clamps
                    // dt to 50 ms, so under SwiftShader the distance a player
                    // covers per frame depends on how fast the frame rendered.
                    // The harness used to force a frame per sample with a
                    // screenshot, which on the finished town exceeds
                    // Playwright's 30 s screenshot timeout and fails outright.
                    // Physics and collision need no pixels.
                    step: (dt) => {
                      if (player) player.update(dt);
                      if (visibility) visibility.update(camera);
                    },
                    // Render ONE frame from an arbitrary camera and report what
                    // it cost. This is the PARITY hook, and it exists because
                    // "the two instruments disagree by 3x" was allowed to stand
                    // for a wave: tools/render/town.html shoots named views from
                    // cameras nobody holds a controller for, and the only way to
                    // prove it measures the shipping client is to hand the
                    // shipping client the identical camera and compare.
                    //
                    // The sun rig is fitted exactly as tick() fits it — to this
                    // camera, through the same `SunRig.fitCascades` — because
                    // the shadow pass is a full second scene render and is a
                    // third of the frame. Deriving the rig from the camera
                    // alone is what makes that parity structural rather than a
                    // pair of expressions somebody has to keep matching.
                    shoot: ({ pos, look, fov = 55 }) => {
                      camera.fov = fov; camera.near = 0.1; camera.far = 2000;
                      camera.up.set(0, 1, 0);
                      camera.position.set(pos[0], pos[1], pos[2]);
                      camera.lookAt(look[0], look[1], look[2]);
                      camera.updateProjectionMatrix();
                      camera.updateMatrixWorld(true);
                      if (rig) rig.fitCascades(camera);
                      probe.beginFrame();
                      visibility.update(camera);
                      post.render(0);
                      probe.endFrame();
                      return perfReport();
                    },
                    /** The rig as MEASURED off the live shadow cameras — box
                     *  size, allocated map size and texels per metre per
                     *  cascade. `tools/check_client.mjs` prints it so a claim
                     *  about shadow density can be checked instead of taken. */
                    shadows: () => (rig ? rig.stats() : null) };

  net.on('Purchased', e => status(`bought ${e.qty}x ${e.item} for ${e.cost}c — purse ${e.purse}c`));
  net.on('Opened', e => status(`${e.open ? 'opened' : 'closed'} ${e.id}`));
  net.on('QuestBoardOpened', () => status('quest board — notices available'));

  addEventListener('keydown', ev => { if (ev.code === 'KeyE') interact(); });

  status(`Hearthmere — ${town.venues.length} venues, ${entities.length} entities, ` +
         `${collision.volumes.length} collision volumes, ` +
         `${visibility.groups.length} batches over ${visibility.occupiedCells().length} cells. ` +
         `WASD move · Shift run · drag to look · E interact · P perf`);
  requestAnimationFrame(tick);
}

/** What the frame actually cost, attributed, in the ONE shape both instruments
 *  print. `client/src/perf.js` owns the definition; this only adds the batching
 *  state that is a property of the visibility set rather than of the frame. */
function perfReport() {
  const s = visibility.stats;
  const p = probe.report();
  const worstCell = Object.entries(p.byCell).sort((a, b) => b[1].draws - a[1].draws).slice(0, 5);
  return {
    ...p,
    trianglesDrawn: p.triangles,          // legacy name, same number
    batches: { total: s.groups, drawn: s.drawn, byLod: s.byLod,
               culledDistance: s.culledDistance, culledFrustum: s.culledFrustum,
               culledPortal: s.culledPortal },
    predicted: { prims: s.prims, tris: s.tris },
    worstCells: worstCell.map(([k, v]) => ({ cell: k, ...v })),
    shadows: rig ? rig.stats() : null,
  };
}

function nearest() {
  let best = null, bestD = Infinity;
  for (const e of interactables) {
    const p = e.transform.pos;
    const dx = p[0] - player.position.x, dz = p[2] - player.position.z;
    const d = dx * dx + dz * dz;
    const r = (e.components.interactable.range ?? 2.0) + 0.6;
    if (d < r * r && d < bestD) { best = e; bestD = d; }
  }
  return best;
}

async function interact() {
  const e = nearest();
  if (!e) { status('nothing in reach'); return; }
  const verb = e.components.interactable.verbs?.[0] || 'inspect';
  // Intent, not mutation — the client asks, the sim decides.
  const map = { open: 'Open', buy: 'RequestPurchase', rest: 'RequestRest',
                read: 'RequestQuestBoard', inspect: 'Inspect' };
  const type = map[verb] || 'Inspect';
  const res = await net.intent(type, { target: e.id });
  if (!res.ok) status(`${verb} failed: ${res.reason}`);
}

// ---------------------------------------------------------------------------
// Frame loop
// ---------------------------------------------------------------------------

let last = performance.now();
function tick(now) {
  const dt = Math.min(0.05, (now - last) / 1000);
  last = now;
  probe.beginFrame();

  if (player) {
    player.update(dt);
    if (ambient) ambient.update(dt, player.position);
    if (water) water.update(dt);
  }

  // Fit the cascades to the CAMERA, not to the player. That is the change: the
  // old rig put a 92 m box around the player's feet, which covers 46 m of town
  // BEHIND the lens — two-thirds of the casters it paid for could not appear in
  // the frame. The cascades are frustum slices, so what they contain is what
  // the player can see. Runs unconditionally, including before the player
  // exists, because a scene with cascade lights parked at the origin renders
  // its first frames unshadowed.
  if (rig) rig.fitCascades(camera);

  // LOD selection, frustum culling, cell distance culling and portals, on the
  // same 16 m partition the sim uses for interest management. Driven by the
  // CAMERA, not the player: a third-person camera sits 3.5 m behind the body
  // and can be looking at cells the player's own position would cull.
  if (visibility) visibility.update(camera);

  if (post) { post.render(dt); probe.endFrame(); }
  requestAnimationFrame(tick);
}

addEventListener('keydown', ev => {
  if (ev.code !== 'KeyP' || !visibility) return;
  const p = perfReport();
  console.table(p.byVenue);
  status(`${formatFrame(p)} · ${p.batches.drawn}/${p.batches.total} batches ` +
         `(LOD ${p.batches.byLod.join('/')}) · ` +
         `culled ${p.batches.culledDistance} far, ${p.batches.culledFrustum} off-screen, ` +
         `${p.batches.culledPortal} interior · budget ${BUDGET.drawCalls}`);
});

addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
  if (post) post.setSize(innerWidth, innerHeight);
});

boot().catch(e => { status('failed: ' + e.message); console.error(e); });
