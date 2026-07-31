/**
 * Hearthmere client — renderer, scene assembly, and the frame loop.
 *
 * Reads the authoritative town layout from content/ and assembles a scene from
 * it. Per docs/ARCHITECTURE.md §1 the client may READ authoritative data but
 * never authors gameplay state: interactions go out as intents (src/net.js).
 */

import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

import { ThirdPersonController } from './player.js';
import { LocalTransport } from './net.js';
import { Ambient } from './ambient.js';
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
const camera = new THREE.PerspectiveCamera(55, innerWidth / innerHeight, 0.1, 500);

// ---------------------------------------------------------------------------
// Sky + image-based lighting
// ---------------------------------------------------------------------------

const skyGeo = new THREE.SphereGeometry(400, 32, 16);
const skyMat = new THREE.ShaderMaterial({
  side: THREE.BackSide,
  uniforms: {
    top: { value: new THREE.Color('#5B9BD9') },
    mid: { value: new THREE.Color('#A8CDEC') },
    bottom: { value: new THREE.Color('#E5DCC8') },
  },
  vertexShader: `varying vec3 vP; void main(){ vP=position; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0); }`,
  fragmentShader: `
    varying vec3 vP; uniform vec3 top, mid, bottom;
    void main(){
      float h = normalize(vP).y;
      vec3 c = h > 0.0 ? mix(mid, top, pow(h, 0.65)) : mix(mid, bottom, pow(-h, 0.5));
      gl_FragColor = vec4(c, 1.0);
    }`,
});
scene.add(new THREE.Mesh(skyGeo, skyMat));

const pmrem = new THREE.PMREMGenerator(renderer);
const envScene = new THREE.Scene();
envScene.add(new THREE.Mesh(skyGeo.clone(), skyMat.clone()));
scene.environment = pmrem.fromScene(envScene, 0.04).texture;

// ---------------------------------------------------------------------------
// Lighting — must match tools/render/viewer.html exactly, or the town will not
// look like the renders it was signed off from.
// ---------------------------------------------------------------------------

// Read from content/town/hearthmere.json so the client and the review harness
// cannot drift apart — and so the town looks like the renders each venue was
// signed off from. Populated in boot(); see applyLighting().
let EL = 38 * Math.PI / 180, AZ = 125 * Math.PI / 180;
const sun = new THREE.DirectionalLight(new THREE.Color('#FFF2D8'), 3.2);
sun.castShadow = true;
sun.shadow.mapSize.set(4096, 4096);
sun.shadow.bias = -0.0004;
sun.shadow.normalBias = 0.02;
Object.assign(sun.shadow.camera, { near: 0.5, far: 260, left: -60, right: 60, top: 60, bottom: -60 });
scene.add(sun, sun.target);

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
  sun.color.set(L.sun.color); sun.intensity = L.sun.intensity;
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
// Post chain
// ---------------------------------------------------------------------------

const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
composer.addPass(new UnrealBloomPass(new THREE.Vector2(innerWidth, innerHeight), 0.32, 0.55, 1.0));
composer.addPass(new OutputPass());

// ---------------------------------------------------------------------------
// World assembly
// ---------------------------------------------------------------------------

const loader = new GLTFLoader();
const colliders = [];
const cells = new Map();          // cellKey -> THREE.Group, for cell culling
let CELL = 16;

function cellKey(x, z) {
  return `${Math.floor(x / CELL)},${Math.floor(z / CELL)}`;
}

function cellGroup(x, z) {
  const k = cellKey(x, z);
  if (!cells.has(k)) {
    const g = new THREE.Group();
    g.userData.center = new THREE.Vector3(
      (Math.floor(x / CELL) + 0.5) * CELL, 0, (Math.floor(z / CELL) + 0.5) * CELL);
    scene.add(g);
    cells.set(k, g);
  }
  return cells.get(k);
}

async function loadVenue(v) {
  const file = `/assets/meshes/${v.id}.gltf`;
  const gltf = await loader.loadAsync(file).catch(() => null);
  if (!gltf) { console.warn('missing venue mesh:', file); return null; }

  const root = gltf.scene;
  root.position.set(...v.origin);
  root.rotation.y = (v.rotationDeg || 0) * Math.PI / 180;
  root.updateMatrixWorld(true);

  root.traverse(o => {
    if (!o.isMesh) return;
    o.castShadow = true;
    o.receiveShadow = true;
    if (o.material) o.material.envMapIntensity = 1.0;
  });

  // Venues are bucketed into 16m cells so culling — and later network interest
  // management — operates on the same partition (docs/ARCHITECTURE.md §3).
  cellGroup(v.origin[0], v.origin[2]).add(root);
  if (ambient) ambient.harvest(root);

  const box = new THREE.Box3().setFromObject(root);
  // Only block at body height; roof overhangs must not become walls.
  if (box.max.y > 0.8) {
    colliders.push(new THREE.Box3(
      new THREE.Vector3(box.min.x + 0.2, 0, box.min.z + 0.2),
      new THREE.Vector3(box.max.x - 0.2, Math.min(box.max.y, 3.0), box.max.z - 0.2)));
  }
  return root;
}

async function loadEntities(venueIds) {
  const all = [];
  for (const id of venueIds) {
    const r = await fetch(`/content/entities/${id}.json`).catch(() => null);
    if (!r || !r.ok) continue;
    const doc = await r.json();
    all.push(...(doc.entities || []));
  }
  return all;
}

// ---------------------------------------------------------------------------
// Ground
// ---------------------------------------------------------------------------

function buildGround(townTex) {
  const mat = new THREE.MeshStandardMaterial({ color: 0x6F6A5C, roughness: 0.95 });
  if (townTex) {
    mat.map = townTex;
    mat.map.wrapS = mat.map.wrapT = THREE.RepeatWrapping;
    // Cobble tiles cover 2m of world, and the ground plane is 300m.
    mat.map.repeat.set(150, 150);
    mat.map.colorSpace = THREE.SRGBColorSpace;
    mat.color.set(0xffffff);
  }
  const g = new THREE.Mesh(new THREE.PlaneGeometry(300, 300).rotateX(-Math.PI / 2), mat);
  g.receiveShadow = true;
  g.position.y = -0.01;
  scene.add(g);
}

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

let player, net, sim, ambient, interactables = [];

async function boot() {
  status('loading town…');
  const town = await (await fetch('/content/town/hearthmere.json')).json();
  CELL = town.grid?.cellSize ?? 16;
  applyLighting(town.lighting);

  const texLoader = new THREE.TextureLoader();
  // Earth, NOT cobble. The street layer paves its carriageways in cobble;
  // texturing the whole ground plane with the same material at the same
  // tiling made Ford Road invisible — a cobble ribbon on a cobble plane,
  // measured at +/-5 luminance units across carriageway and verge alike.
  const cobble = await texLoader.loadAsync('/assets/textures/dirt_albedo.png').catch(() => null);
  buildGround(cobble);

  status('loading entities…');
  const ids = [...new Set(town.venues.map(v => v.id))];
  // Entities load FIRST: ambient effects (chimney smoke, forge flicker) are
  // declared on entity components, and cloth sway is registered per venue as
  // it loads, so Ambient has to exist before the venue loop runs.
  const entities = await loadEntities(ids);
  ambient = new Ambient(scene, town, entities);

  status('loading venues…');
  for (const v of town.venues) await loadVenue(v);
  sim = new Sim(town, entities);
  net = new LocalTransport(sim);
  interactables = entities.filter(e => e.components?.interactable);

  player = new ThirdPersonController(camera, renderer.domElement);
  player.position.set(...(town.playerSpawn?.pos || [0, 0, -44]));
  player.yaw = (town.playerSpawn?.facingDeg ?? 180) * Math.PI / 180;
  player.facing = player.yaw;
  scene.add(player.avatar);

  net.on('Purchased', e => status(`bought ${e.qty}x ${e.item} for ${e.cost}c — purse ${e.purse}c`));
  net.on('Opened', e => status(`${e.open ? 'opened' : 'closed'} ${e.id}`));
  net.on('QuestBoardOpened', () => status('quest board — notices available'));

  addEventListener('keydown', ev => { if (ev.code === 'KeyE') interact(); });

  status(`Hearthmere — ${town.venues.length} venues, ${entities.length} entities. ` +
         `WASD move · Shift run · drag to look · E interact`);
  requestAnimationFrame(tick);
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

  if (player) {
    player.update(dt, colliders);
    if (ambient) ambient.update(dt, player.position);

    // Keep the shadow frustum tight on the player, or a town-sized frustum
    // makes shadows mushy and unusable.
    const p = player.position;
    sun.target.position.copy(p);
    sun.target.updateMatrixWorld();
    sun.position.set(
      p.x + Math.cos(EL) * Math.sin(AZ) * 70,
      Math.sin(EL) * 70,
      p.z + Math.cos(EL) * Math.cos(AZ) * 70);

    // Cell culling on the same 16m partition the sim uses for interest.
    for (const [, g] of cells) {
      const d = g.userData.center.distanceTo(p);
      g.visible = d < 110;
    }
  }

  composer.render();
  requestAnimationFrame(tick);
}

addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
  composer.setSize(innerWidth, innerHeight);
});

boot().catch(e => { status('failed: ' + e.message); console.error(e); });
