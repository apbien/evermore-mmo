/**
 * Visibility: LOD selection, frustum culling, cell distance culling, portals.
 *
 * The runtime half of BUILD_DIRECTIVE §7. `core/venue.py` bakes the town into
 * one primitive per (16 m cell, material) with a four-step LOD chain declared
 * as MSFT_lod; this decides, every frame, which of those to draw.
 *
 * It lives in `client/src/` and is imported by BOTH `client/src/main.js` and
 * `tools/render/town.html`, for the reason D-023 exists: a review harness that
 * measures a different town from the one that ships is worse than no harness.
 * The draw-call number in a town.mjs report is the number the client gets,
 * because it is the same code producing it.
 *
 * Three things are worth knowing before changing anything here:
 *
 * 1. **three.js already frustum-culls every Mesh.** Doing it again per group is
 *    not where the win is — the win is distance culling, LOD selection and
 *    portals, none of which three does. The group-level frustum test is kept
 *    because it lets one test skip a whole cell's children instead of walking
 *    them, but it is not what moves the draw-call count.
 * 2. **MSFT_lod alternates are not in the glTF scene**, by design (see
 *    core/gltf.py). A consumer that ignores the extension draws level 0 and is
 *    correct, merely expensive. `prepareLods` is what opts this renderer in: it
 *    instantiates the alternates through the loader's own dependency graph and
 *    parents them next to level 0, hidden.
 * 3. **Preparation happens on the loaded glTF, placement on clones.** A venue
 *    placed six times is one parse and six `clone(true)` calls, and because the
 *    alternates are attached before cloning, every clone carries its own LOD
 *    chain with no second parse.
 */

import * as THREE from 'three';

/** Fallback switch distances. The authored values ride in the glTF manifest
 *  (`gltf.userData.hm.lodDistances`) so the build and the runtime cannot drift;
 *  these are only used for a file built before the manifest existed. */
export const LOD_DISTANCES = [15, 40, 100];

/** Beyond this a cell is not drawn at all. Generous on purpose: the far side of
 *  a 192 m town is 270 m from a corner, and a town that pops out at the edge of
 *  the square reads worse than one that costs 40 extra draws. */
export const CELL_CULL_DISTANCE = 190;

/**
 * Beyond this a batch stops casting sun shadows.
 *
 * Measured before this existed: at the arrival camera the frame was 2,065 draw
 * calls, of which the SHADOW PASS was 988 — more than the beauty pass's 574,
 * and 48% of the whole frame against a §7 budget of 900 for all of it. Nothing
 * about that was visible in either instrument, because one of them was reading
 * `renderer.info` with `autoReset` on and three r180 resets it after the shadow
 * pass (see client/src/perf.js).
 *
 * A shadow caster costs a full depth draw whether or not its shadow lands
 * anywhere a player can see. Three things are therefore excluded, and all three
 * are the same settings an engine exposes — `r.Shadow.DistanceScale`, per-mesh
 * "Cast Shadow", and shadow LOD bias — so none of it is a web-only trick:
 *
 *   1. **Distance.** The sun sits at 38 degrees, so a 15 m gable throws a 19 m
 *      shadow. A caster 42 m from the eye puts its shadow at the very edge of
 *      the readable midground and behind ~60% aerial opacity. Past that it is
 *      paying a draw to darken haze.
 *
 *      THIS CONSTANT IS THE FALLBACK, NOT THE AUTHORITY. It is now the same
 *      decision as the shadow rig's own reach — `lighting.shadows.distance` in
 *      content — because the caster set is a disc of this radius around the
 *      camera and its AREA is what the shadow pass costs, while the far
 *      cascade's box is sized by the same number. Both renderers pass the
 *      authored value in as `shadowDistance`, so the two cannot drift; see
 *      `client/src/shadows.js`.
 *   2. **Greeble.** Groups the build gave a screen-size cull to (`cullAt` —
 *      roadside grit, window furniture, cobble chips) are, by construction, too
 *      small to be worth a draw call at range. They are equally not worth a
 *      shadow draw, and their shadows are sub-pixel long before the objects are.
 *   3. **Coarse LOD.** A group already at LOD2 is at least 40 m away and is
 *      drawing a decimated shell. Casting from it is both the most expensive
 *      and the least accurate shadow in the frame.
 */
export const SHADOW_CAST_DISTANCE = 42;

/** Coarser than this never casts. LOD2 begins at 40 m. */
export const SHADOW_MAX_LOD = 1;

/**
 * Shadow LOD bias: the COARSEST-allowed... no — the FINEST level each cascade
 * is allowed to cast from. Index is the cascade; the last entry repeats.
 *
 * `[0, 1]` means: the near cascade casts from whatever the frame is drawing,
 * and every cascade past it casts from at least LOD1.
 *
 * The near cascade is not biased, deliberately. It is 0-5.4 m — the contact
 * shadows, the figure's feet, the doorstep — and it is also the cascade whose
 * box is small enough that three's own per-primitive frustum test is doing real
 * work inside it. Cascade 1 is 5.4-30 m against a ~64 m light box, where that
 * test rejects nothing, and LOD1 is already what the beauty pass draws from
 * 15 m; a depth-only silhouette off a half-decimated mesh at 5 m+ is the
 * standard shadow LOD bias every engine ships (`r.Shadow.LODBias`).
 */
export const SHADOW_CASCADE_LOD = [0, 1];

/** How far the town's ground falls, metres (BUILD_DIRECTIVE §4: ~4 m south to
 *  north). Added to a batch's own height when bounding how far its shadow can
 *  reach, so a batch on the high side still covers the low ground. */
export const GROUND_FALL = 5;

/**
 * Materials that must keep casting as themselves rather than being folded into
 * a merged depth proxy.
 *
 * Two reasons, and both are visible in a frame if they are got wrong:
 *   - **cut-outs.** A leaf card is a quad with an alpha map; merged into an
 *     opaque proxy its shadow is a solid rectangle, which is the single most
 *     recognisable procedural-foliage tell there is.
 *   - **vertex motion.** `client/src/ambient.js` displaces the sway materials in
 *     the vertex shader. A proxy baked at rest would cast a still shadow under
 *     a moving object.
 * Alpha is detected off the material (`transparent`, `alphaTest`, `alphaMap`);
 * this name test is for the opaque things that still move, and it is the same
 * key set `SunRig`'s FOLIAGE_RE and `core/vegetation.py SWAY_MATERIALS` use.
 */
const NO_MERGE_RE = /^(leaf_|hedge$|ivy$|foliage|reed$|weeds$|tree_far$|banner|cloth_|canvas|washing|rope$|net$)/;

/**
 * Instantiate the MSFT_lod alternates of a loaded glTF and hide them.
 *
 * Idempotent, and must be called BEFORE any `clone()` of `gltf.scene`.
 */
export async function prepareLods(gltf) {
  if (gltf.userData.__lodPrepared) return gltf;
  gltf.userData.__lodPrepared = true;

  const parser = gltf.parser;
  const json = parser?.json;
  if (!parser || !json?.nodes) return gltf;

  // parser.associations is the only mapping from a built Object3D back to its
  // glTF node index, and the node index is the only key MSFT_lod speaks.
  const byIndex = new Map();
  for (const [obj, assoc] of parser.associations) {
    if (assoc && assoc.nodes !== undefined) byIndex.set(assoc.nodes, obj);
  }

  const jobs = [];
  for (const [idx, obj] of byIndex) {
    const ids = json.nodes[idx]?.extensions?.MSFT_lod?.ids;
    if (!ids || !ids.length || !obj.parent) continue;
    const parent = obj.parent;
    for (const id of ids) {
      jobs.push(parser.getDependency('node', id).then(alt => {
        alt.visible = false;
        parent.add(alt);
      }).catch(e => console.warn('LOD alternate', id, 'failed:', e.message)));
    }
  }
  await Promise.all(jobs);
  anisotropic(gltf.scene);
  return gltf;
}


/**
 * Turn anisotropic filtering on for every texture the file brought in.
 *
 * three.js defaults `Texture.anisotropy` to 1. With isotropic filtering a
 * surface picks its mip from the LARGER of its two screen-space derivatives,
 * so anything the camera sees at a grazing angle is blurred along the axis
 * that did not need blurring — and at a 1.62 m eye that is the whole ground
 * plane past a few metres. `ad-town-05` has it as "the market place past 12 m
 * mips to a flat sandy plane", which was correctly diagnosed there as a
 * filtering problem rather than a texture one: the setts are right and the
 * filter is throwing them away. It is equally the reason distant walls lose
 * their bond and pick up moire at 25 m.
 *
 * It lives here rather than in `client/src/main.js` because `prepareLods` is
 * the one function BOTH the client and `tools/render/town.html` call on a
 * loaded glTF, once per file, after the LOD alternates are attached — so one
 * edit covers the runtime, the review harness and every LOD level, and the
 * two cannot drift. 16 is clamped down to the device maximum by three.js at
 * upload, and is a no-op where the extension is absent.
 */
const ANISO = 16;
const ANISO_MAPS = ['map', 'normalMap', 'roughnessMap', 'metalnessMap',
                    'aoMap', 'emissiveMap', 'alphaMap', 'bumpMap'];
export function anisotropic(root) {
  if (!root) return root;
  root.traverse(o => {
    const mat = o.material;
    if (!mat) return;
    for (const m of (Array.isArray(mat) ? mat : [mat])) {
      if (!m) continue;
      for (const k of ANISO_MAPS) {
        const t = m[k];
        if (!t || t.userData.__aniso) continue;
        t.userData.__aniso = true;
        t.anisotropy = ANISO;
        t.needsUpdate = true;
      }
    }
  });
  return root;
}

/** One batch group: a (cell, material-set) bundle and its LOD alternates. */
class Group {
  constructor(key, meta) {
    this.key = key;
    this.venue = meta.venue || null;
    this.cell = meta.cell || null;
    this.interior = meta.interior || null;
    this.meshId = meta.meshId || null;
    this.levels = [];            // Object3D per LOD level, sparse
    this.cost = [];              // { prims, tris } per level
    this.distances = LOD_DISTANCES;
    // Build-time screen-size cull (core/venue.py `_cull_distance`). Set only on
    // groups too small to be worth a draw call at range — roadside grit, window
    // furniture — never on a building.
    this.cullAt = meta.cullAt ?? null;
    this.sphere = new THREE.Sphere();
    this.box = new THREE.Box3();
    this.worldCell = null;
    this.current = -2;           // force the first setLevel through
    // Meshes of every level, with the castShadow flag the renderer gave them.
    // Shadow state is only ever turned DOWN from that: `terrain` opts out of
    // casting in both renderers because a 576 m heightfield shadowing its own
    // slopes buys acne rather than contact, and this must not turn it back on.
    this.shadowMeshes = [];
    // Same list, split by LOD level: only the VISIBLE level can cast, so the
    // caster policy is written per level and the hidden levels are left alone.
    this.levelMeshes = [];
    // Merged depth proxy per level, built lazily the first time that level is
    // asked to cast. See VisibilitySet._proxyFor.
    this.proxies = [];
    // The level currently written into the caster flags (-1 = not casting).
    // Null forces a write.
    this._castSig = null;
    this._castLevel = -1;
    this.proxy = null;
    this.casting = null;
    // Whether this group is an eligible caster AT ALL this frame (distance,
    // LOD, greeble). Decided once per frame in `update()`.
    this.casts = false;
    // Which cascade's caster set is currently written into `shadowMeshes`.
    // -1 = none applied. See VisibilitySet.applyCascade.
    this.cascadeApplied = -1;
    // How far down-sun this group's shadow can reach, metres. Static: it is
    // (top of the batch - the town's floor) / tan(sun elevation), so it is the
    // longest shadow the batch can throw onto level ground. Filled in by
    // `addPlacement` once the box is known and the sun angle is in hand.
    this.shadowReach = 0;
  }

  addLevel(obj) {
    const i = obj.userData?.hm?.lod ?? 0;
    this.levels[i] = obj;
    this.cost[i] = { prims: obj.userData?.hm?.prims ?? 1, tris: obj.userData?.hm?.tris ?? 0 };
    obj.visible = false;
    const own = this.levelMeshes[i] || (this.levelMeshes[i] = []);
    obj.traverse(o => {
      if (o.isMesh || o.isInstancedMesh) {
        this.shadowMeshes.push([o, o.castShadow !== false]);
        own.push([o, o.castShadow !== false]);
      }
    });
  }

  /** Toggle this batch's shadow casting. Walks its meshes only on a TRANSITION,
   *  which is rare — a player has to cross the 42 m ring or an LOD boundary —
   *  so the per-frame cost of the policy is one comparison per group. */
  setShadow(on) {
    if (on === this.casting) return;
    for (const [m, allowed] of this.shadowMeshes) m.castShadow = on && allowed;
    this.casting = on;
  }

  /** Finest available level at or coarser than the ideal for `d`. */
  levelFor(d) {
    let want = this.distances.length;
    for (let i = 0; i < this.distances.length; i++) {
      if (d < this.distances[i]) { want = i; break; }
    }
    return this.clampLevel(want);
  }

  /** Coarsest authored level no coarser than `want`. A group under
   *  `LOD_MIN_TRIS` has only level 0 and stays there at every distance. */
  clampLevel(want) {
    for (let i = Math.min(want, this.levels.length - 1); i >= 0; i--) {
      if (this.levels[i]) return i;
    }
    return -1;
  }

  setLevel(i) {
    if (i === this.current) return;
    for (let k = 0; k < this.levels.length; k++) {
      if (this.levels[k]) this.levels[k].visible = (k === i);
    }
    this.current = i;
    this._castSig = null;      // the caster policy is written per level
  }

  /**
   * Write this group's caster state for one cascade.
   *
   * `level < 0` means "does not cast into this cascade". Otherwise the group
   * casts from the level it is DRAWING — never a coarser one — so the shadow
   * silhouette is the silhouette on screen and this change cannot alter a
   * single shadow's shape. What it changes is how many draws that costs: a
   * merged depth proxy stands in for every opaque primitive of the level, and
   * a 16 m cell at LOD0 is about ten primitives.
   */
  applyCast(level, proxyFor) {
    if (level === this._castSig) return level >= 0;
    this._castSig = level;
    // Clear whatever the previous cascade wrote. Both the level being drawn and
    // the level last cast from are cleared: they can differ, and a stale
    // `castShadow` on a visible node is a caster nobody asked for.
    if (this.proxy) { this.proxy.visible = false; this.proxy.castShadow = false; this.proxy = null; }
    for (const [m] of (this.levelMeshes[this._castLevel] || [])) m.castShadow = false;
    for (const [m] of (this.levelMeshes[this.current] || [])) m.castShadow = false;
    this._castLevel = -1;
    const node = level >= 0 ? this.levels[level] : null;
    if (!node) { this.casting = false; return false; }
    // The cast level may be COARSER than the drawn level (shadow LOD bias), and
    // three skips an invisible node before it looks at `castShadow`. Showing it
    // here is safe because the beauty pass's render list was built before the
    // shadow pass ran; `VisibilitySet.endShadowPass` puts it back.
    node.visible = true;
    this._castLevel = level;
    const own = this.levelMeshes[level] || [];
    const p = proxyFor ? proxyFor(this, level) : null;
    if (p && p.mesh) {
      this.proxy = p.mesh;
      p.mesh.visible = true;
      p.mesh.castShadow = true;
      // Only what could not be merged — cut-outs and anything that moves in the
      // vertex shader — still casts as itself.
      for (const [m, allowed] of own) m.castShadow = allowed && p.loose.has(m);
    } else {
      for (const [m, allowed] of own) m.castShadow = allowed;
    }
    this.casting = true;
    return true;
  }

  /** Undo everything `applyCast` did to the scene graph. */
  restoreLevels() {
    if (this.proxy) { this.proxy.visible = false; this.proxy.castShadow = false; this.proxy = null; }
    for (const [m] of (this.levelMeshes[this._castLevel] || [])) m.castShadow = false;
    for (let k = 0; k < this.levels.length; k++) {
      if (this.levels[k]) this.levels[k].visible = (k === this.current);
    }
    this._castLevel = -1;
    this._castSig = null;
    this.casting = false;
  }
}

export class VisibilitySet {
  /**
   * @param {object} opts
   *   cullDistance  — cell distance cull radius, metres
   *   grid          — { cellSize, cols, rows } from content/town/hearthmere.json,
   *                   used only to label cells the way the town file does
   */
  constructor(opts = {}) {
    this.groups = [];
    this.cullDistance = opts.cullDistance ?? CELL_CULL_DISTANCE;
    this.shadowDistance = opts.shadowDistance ?? SHADOW_CAST_DISTANCE;
    this.cellSize = opts.grid?.cellSize ?? 16;
    this.cols = opts.grid?.cols || null;
    this.rows = opts.grid?.rows || null;
    this.interiors = [];
    this._frustum = new THREE.Frustum();
    this._m = new THREE.Matrix4();
    this._v = new THREE.Vector3();
    this.stats = this._zero();
    // Per-cascade caster culling. OFF unless a SunRig binds itself with
    // `bindCasters()`: a renderer with a single shadow box (shoot.mjs, the
    // viewer) must keep the old behaviour, where `update()` writes the flags
    // directly and nothing else touches them.
    this.cascadeCull = false;
    this._sun = null;
    this._reachDirty = true;
    this._floorY = 0;
    this._sphere = new THREE.Sphere();
    this.cascadeCasters = [];
    // Merged depth proxies. On whenever per-cascade culling is; `false` is the
    // control experiment, and `tools/render/town.mjs --query shadowproxy=0`
    // reaches it so a before and an after come out of one build.
    this.shadowProxies = true;
    // First cascade allowed to use a merged proxy. Cascade 0's light box is
    // ~12 m, so three's per-primitive frustum test rejects most of a 16 m cell
    // inside it; merging the cell hands that back and the near cascade's
    // triangle count triples. Measured: cascade 0 with a proxy was 90 draws /
    // 1,082,238 triangles for a 0-5.4 m band. So the proxy starts at cascade 1,
    // where the box is 64 m and the test rejects nothing anyway.
    this.proxyFromCascade = 1;
    this._live = new Set();
    this._proxyBind = (g, level) => this._proxyFor(g, level);
    this.onProxyBuilt = null;
    this.proxyBytes = 0;
    this.proxyCount = 0;
    this.proxySaved = 0;
  }

  _zero() {
    return {
      groups: 0, drawn: 0, prims: 0, tris: 0, instances: 0,
      culledDistance: 0, culledFrustum: 0, culledPortal: 0, shadowCasters: 0,
      byLod: [0, 0, 0, 0], byVenue: {}, byCell: {},
    };
  }

  /** Label a world position the way content/town/hearthmere.json does (E3).
   *
   *  Outside the authored grid — the terrain plate reaches 288 m, the grid
   *  stops at 96 — there is no such label, and inventing one produced rows like
   *  "C-3" in the report. Those get an explicit out-of-grid key instead, so a
   *  reader can tell "this cost is outside the town" from "this cost is in a
   *  cell you can name". */
  cellLabel(x, z) {
    const i = Math.floor(x / this.cellSize), j = Math.floor(z / this.cellSize);
    const nc = this.cols?.length ?? 12, nr = this.rows?.length ?? 12;
    const ci = i + nc / 2, cj = j + nr / 2;
    if (ci < 0 || ci >= nc || cj < 0 || cj >= nr) return `out[${i},${j}]`;
    const col = this.cols?.[ci] ?? String.fromCharCode(65 + ci);
    const row = this.rows?.[cj] ?? (cj + 1);
    return `${col}${row}`;
  }

  /**
   * Register one PLACED venue. `root` is the positioned scene graph (a clone is
   * fine); `manifest` is `gltf.userData.hm`.
   *
   * Objects with no `hm` metadata — an older mesh, or a hand-built helper — are
   * left alone and always drawn, so adding this to a scene can never make part
   * of the town disappear.
   */
  addPlacement(root, manifest = null, label = null) {
    root.updateMatrixWorld(true);
    const found = new Map();
    root.traverse(o => {
      const hm = o.userData?.hm;
      if (!hm || hm.venue === undefined) return;
      const key = `${label || hm.venue}#${hm.interior ? 'int:' + hm.interior : hm.cell}` +
                  (hm.meshId ? '@' + hm.meshId : '');
      let g = found.get(key);
      if (!g) {
        g = new Group(key, hm);
        g.venue = label || hm.venue;
        if (manifest?.lodDistances?.length) g.distances = manifest.lodDistances;
        found.set(key, g);
      }
      g.addLevel(o);
      if (hm.instances) g.instances = hm.instances;
    });

    for (const g of found.values()) {
      const base = g.levels.find(Boolean);
      if (!base) continue;
      g.box.setFromObject(base);
      g.box.getBoundingSphere(g.sphere);
      const c = g.box.getCenter(new THREE.Vector3());
      g.worldCell = this.cellLabel(c.x, c.z);
      if (g.interior) {
        g.portals = (manifest?.interiors || [])
          .filter(it => it.id === g.interior)
          .flatMap(it => (it.portals || []).map(p => {
            const pos = new THREE.Vector3(p.pos[0], p.pos[1], p.pos[2]).applyMatrix4(root.matrixWorld);
            // The normal is a DIRECTION: rotate it, never translate it. Applying
            // the full matrix would put the doorway's outward normal wherever
            // the venue happens to stand, which for a venue 44 m off the origin
            // means every portal faces the fountain.
            const n = new THREE.Vector3(p.normal[0], 0, p.normal[1])
              .transformDirection(root.matrixWorld);
            return { pos, nx: n.x, nz: n.z, range: p.range ?? 30,
                     radius: Math.hypot(p.size?.[0] ?? 2, p.size?.[1] ?? 2) * 0.5 };
          }));
        // An interior with no portals is only visible from inside it. That is a
        // sealed room, which is a legitimate thing to author but almost always
        // means someone forgot the doorway, so say so.
        if (!g.portals.length) {
          console.warn(`interior '${g.interior}' of '${g.venue}' declares no portals — ` +
                       `it will only be drawn from inside`);
        }
        this.interiors.push(g);
      }
      this.groups.push(g);
    }
    this.stats.groups = this.groups.length;
    this._reachDirty = true;
    return found.size;
  }

  /**
   * The sun direction — a unit vector pointing AT the sun, the same one
   * `client/src/shadows.js sunVector()` returns.
   *
   * It is the second half of per-cascade caster culling: a caster is kept for a
   * cascade when the caster OR ITS SHADOW can land in that cascade's slice, and
   * the shadow is the batch swept down-sun until it reaches the ground.
   */
  setSun(dir) {
    if (!dir) return this;
    (this._sun || (this._sun = new THREE.Vector3())).copy(dir).normalize();
    this._reachDirty = true;
    return this;
  }

  /**
   * Longest shadow every group can throw, in metres. Static per (sun angle,
   * town), so it is computed once and only redone when a placement or the sun
   * moves.
   *
   * `(own height + GROUND_FALL) / tan(elevation)`. A batch is a whole 16 m
   * cell, so it runs from the ground it stands on to the ridge above it and its
   * own height IS the height of the shadow-casting silhouette; `GROUND_FALL`
   * covers the town's 4 m south-to-north drop, so a batch on the high side
   * still reaches the low ground its shadow falls on.
   *
   * Measured against the TOWN floor instead — which was the first thing tried —
   * this returns nonsense: the terrain plate and the horizon skirt reach tens
   * of metres below the town, so every batch got a 60 m+ reach, the swept test
   * accepted everything, and per-cascade culling removed 4 draws out of 604.
   * A conservative bound that is conservative by a factor of three is not a
   * bound, it is a no-op with a comment on it.
   */
  _refreshReach() {
    this._reachDirty = false;
    if (!this.groups.length) return;
    const el = this._sun
      ? Math.max(0.05, Math.asin(Math.max(-1, Math.min(1, this._sun.y))))
      : Math.PI / 4;
    const t = Math.tan(el);
    for (const g of this.groups) {
      const h = Math.max(0, g.box.max.y - g.box.min.y) + GROUND_FALL;
      g.shadowReach = h / t;
    }
  }

  /**
   * Write the caster set for ONE cascade into the scene's `castShadow` flags.
   *
   * Called from `SunRig`, once per cascade, from inside three's own shadow loop
   * — `LightShadow.updateMatrices()` is the last thing that runs before
   * `renderObject()` walks the scene for that cascade, so this is the only
   * point at which "which casters does THIS cascade need" can be answered.
   *
   * WHY IT IS WORTH DOING. three culls each cascade against that cascade's
   * light-space BOX, and the box is the bounding square of the cascade's view
   * frustum slice: for the 5.4-30 m cascade at 55 deg / 16:9 that square is
   * ~68 m across, which contains every caster within the 30 m caster radius in
   * every direction, INCLUDING the two thirds of them behind the lens. Measured
   * at the `square` camera the shadow pass was 604 draws against a 462-draw
   * beauty pass — the largest stage in the frame, and most of it was casters
   * whose shadows are not in shot.
   *
   * The test is the honest one: a caster is kept if its bounding sphere, or
   * that sphere swept down-sun as far as its shadow reaches, meets the
   * cascade's receiver frustum. So a building behind the camera whose shadow
   * falls across the street in front of it is kept, and the same building with
   * the sun behind the lens is not. That is per-object shadow culling —
   * `r.Shadow.CSMCasterPerObjectCulling` in Unreal, "Cast Shadows: Two Sided /
   * culling volumes" in Unity — not a web trick.
   *
   * @param {number} i          cascade index
   * @param {THREE.Frustum|null} frustum  that cascade's receiver region, or
   *                            null to keep every eligible caster (the single-
   *                            box mode the plan and the aerials use)
   */
  applyCascade(i, frustum, forceProxy = false) {
    if (this._reachDirty) this._refreshReach();
    let n = 0;
    const bias = SHADOW_CASCADE_LOD[Math.min(i, SHADOW_CASCADE_LOD.length - 1)];
    const proxies = (forceProxy || i >= this.proxyFromCascade) ? this._proxyBind : null;
    for (const g of this.groups) {
      const on = g.casts && (!frustum || this._shadowVisible(g, frustum));
      const level = on ? g.clampLevel(Math.max(g.current, bias)) : -1;
      if (g.applyCast(level, proxies)) { n++; this._live.add(g); }
    }
    this.cascadeCasters[i] = n;
    return n;
  }

  /**
   * Bracket the shadow pass.
   *
   * A merged depth proxy has to be VISIBLE for three to draw it — `renderObject`
   * returns on `object.visible === false` before it looks at `castShadow` — and
   * invisible for the beauty pass, where it would be an untextured black
   * duplicate of the cell. Both are true at once because
   * `WebGLRenderer.render()` builds its render list in `projectObject()` BEFORE
   * it calls `shadowMap.render()`: the beauty pass is already committed by the
   * time the proxies appear, and they are gone again before the next frame
   * projects. `SunRig` installs the wrapper that calls these two.
   */
  beginShadowPass() { this._live.clear(); }

  endShadowPass() {
    for (const g of this._live) g.restoreLevels();
    this._live.clear();
  }

  /**
   * The merged depth proxy for one (group, level), built once and cached.
   *
   * WHY. A shadow draw is a depth draw: for an opaque surface the material
   * contributes nothing but its side. A 16 m cell at LOD0 is ~10 primitives
   * because it is one primitive PER MATERIAL — plaster, oak, oak_dark, lead,
   * ridge, terracotta, glass… — and the shadow pass paid all ten, twice, once
   * per cascade. Measured at the `square` camera that was 600 draws against a
   * 462-draw beauty pass: the largest stage in the frame.
   *
   * Merging every opaque primitive of a level into one position-only buffer
   * makes it one draw. The vertices are the SAME vertices, so no silhouette
   * moves — this is a draw-call change and not a quality change, which is the
   * property that makes it safe to do inside the near field where the contact
   * shadows are. It is Unreal's merged shadow proxy and Unity's
   * "Cast Shadows: on a combined mesh"; §7 asks for per-cell static batching
   * and this is that technique applied to the depth pass.
   *
   * Returns null when merging cannot pay — fewer than two mergeable primitives.
   */
  _proxyFor(g, level) {
    if (!this.shadowProxies) return null;
    const cached = g.proxies[level];
    if (cached !== undefined) return cached;
    const root = g.levels[level];
    if (!root) return (g.proxies[level] = null);

    const loose = new Set();
    const merge = [];
    for (const [m] of (g.levelMeshes[level] || [])) {
      // An InstancedMesh is already one draw for N copies; merging it would
      // expand it back out to N copies of geometry. Leave it alone.
      if (m.isInstancedMesh || !m.geometry?.attributes?.position) { loose.add(m); continue; }
      const mats = Array.isArray(m.material) ? m.material : [m.material];
      const keep = mats.some(x => !x || x.transparent || (x.alphaTest > 0) ||
                                  x.alphaMap || NO_MERGE_RE.test(x.name || ''));
      if (keep) loose.add(m); else merge.push(m);
    }
    if (merge.length < 2) return (g.proxies[level] = null);

    let verts = 0, idx = 0;
    for (const m of merge) {
      verts += m.geometry.attributes.position.count;
      idx += m.geometry.index ? m.geometry.index.count : m.geometry.attributes.position.count;
    }
    // 32-bit indices past 65 535 vertices; the build guarantees uint16 per
    // primitive but a merged cell can cross the line.
    const pos = new Float32Array(verts * 3);
    const ind = verts > 65535 ? new Uint32Array(idx) : new Uint16Array(idx);
    const inv = new THREE.Matrix4().copy(root.matrixWorld).invert();
    const mm = new THREE.Matrix4();
    const v = new THREE.Vector3();
    let vo = 0, io = 0, side = THREE.FrontSide;
    for (const m of merge) {
      const a = m.geometry.attributes.position;
      mm.multiplyMatrices(inv, m.matrixWorld);
      for (let k = 0; k < a.count; k++) {
        v.fromBufferAttribute(a, k).applyMatrix4(mm);
        pos[(vo + k) * 3] = v.x; pos[(vo + k) * 3 + 1] = v.y; pos[(vo + k) * 3 + 2] = v.z;
      }
      const gi = m.geometry.index;
      if (gi) for (let k = 0; k < gi.count; k++) ind[io + k] = vo + gi.getX(k);
      else for (let k = 0; k < a.count; k++) ind[io + k] = vo + k;
      io += gi ? gi.count : a.count;
      vo += a.count;
      const mat = Array.isArray(m.material) ? m.material[0] : m.material;
      if (mat && mat.side === THREE.DoubleSide) side = THREE.DoubleSide;
    }

    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    geo.setIndex(new THREE.BufferAttribute(ind, 1));
    geo.computeBoundingSphere();
    geo.computeBoundingBox();
    const mesh = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ side }));
    mesh.name = `${g.key}$shadow${level}`;
    mesh.visible = false;
    mesh.castShadow = true;
    mesh.receiveShadow = false;
    mesh.matrixAutoUpdate = false;
    root.add(mesh);
    mesh.updateMatrixWorld(true);

    this.proxyBytes += pos.byteLength + ind.byteLength;
    this.proxyCount++;
    this.proxySaved += merge.length - 1;
    if (this.onProxyBuilt) this.onProxyBuilt(mesh, g);
    return (g.proxies[level] = { mesh, loose });
  }

  /** Does `g` or its shadow reach `frustum`? Swept-sphere, conservative. */
  _shadowVisible(g, frustum) {
    if (frustum.intersectsSphere(g.sphere)) return true;
    const reach = g.shadowReach;
    if (!(reach > 0.01) || !this._sun) return false;
    const s = this._sphere;
    // Sample the swept capsule at a spacing no coarser than the sample sphere's
    // own radius, so the union of the samples covers the capsule with no gap.
    // Capped at 8 samples; past that the radius grows to keep the cover exact
    // rather than the count growing to keep it cheap.
    const n = Math.max(1, Math.min(8, Math.ceil(reach / Math.max(2, g.sphere.radius))));
    const step = reach / n;
    s.radius = Math.max(g.sphere.radius, step * 0.5);
    for (let k = 1; k <= n; k++) {
      s.center.copy(g.sphere.center).addScaledVector(this._sun, -step * k);
      if (frustum.intersectsSphere(s)) return true;
    }
    return false;
  }

  /**
   * Everything not registered above is drawn unconditionally.
   *
   * `opts` exists for the review harness, which has to shoot cameras no player
   * ever has — an orthographic plan from 600 m up would distance-cull the
   * entire town, and a silhouette is meaningless at LOD3:
   *   cullDistance — override the distance cull (Infinity to disable)
   *   origin       — measure distances from here instead of the camera
   *   forceLod     — pin every group to one level
   */
  update(camera, opts = {}) {
    camera.updateMatrixWorld();
    this._m.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);
    this._frustum.setFromProjectionMatrix(this._m);
    const eye = opts.origin || camera.position;
    const cullDistance = opts.cullDistance ?? this.cullDistance;
    // A review camera that disables the distance cull (plan, aerial) must not
    // simultaneously switch every shadow in the town off — that would be a
    // different image from the one the client draws, which is the whole thing
    // D-023 exists to prevent. `cullDistance: Infinity` implies shadows to
    // match unless the caller says otherwise.
    const shadowDistance = opts.shadowDistance ??
      (opts.cullDistance === Infinity ? Infinity : this.shadowDistance);

    const s = this.stats = this._zero();
    s.groups = this.groups.length;

    for (const g of this.groups) {
      // Distance to the group's SURFACE, not to its centre. A 16 m cell has an
      // 11 m radius, so centre distance would switch the cell you are standing
      // in to LOD1 the moment you cross to its far half.
      const d = Math.max(0, g.sphere.center.distanceTo(eye) - g.sphere.radius);
      let level = -1;
      if (d > cullDistance || (g.cullAt !== null && d > g.cullAt)) {
        s.culledDistance++;
      } else if (!this._frustum.intersectsSphere(g.sphere)) {
        s.culledFrustum++;
      } else if (g.interior && !this.interiorVisible(g, eye)) {
        s.culledPortal++;
      } else {
        level = opts.forceLod != null ? g.clampLevel(opts.forceLod) : g.levelFor(d);
      }
      g.setLevel(level);
      // Shadow casting, decided per batch. See SHADOW_CAST_DISTANCE. A culled
      // group is invisible and cannot cast anyway, but the flag is cleared so
      // the state never drifts from the level.
      const casts = level >= 0 && level <= SHADOW_MAX_LOD &&
                    g.cullAt === null && d <= shadowDistance;
      g.casts = casts;
      // With per-cascade culling on, the flags belong to `applyCascade` and
      // writing them here would be overwritten by the first cascade anyway.
      // Without it, this is still the only thing that sets them.
      if (!this.cascadeCull) g.setShadow(casts);
      if (casts) s.shadowCasters++;
      if (level < 0) continue;

      const c = g.cost[level] || { prims: 1, tris: 0 };
      s.drawn++; s.prims += c.prims; s.tris += c.tris;
      s.instances += g.instances || 0;
      s.byLod[Math.min(3, level)]++;
      const bv = s.byVenue[g.venue] || (s.byVenue[g.venue] = { groups: 0, prims: 0, tris: 0 });
      bv.groups++; bv.prims += c.prims; bv.tris += c.tris;
      const bc = s.byCell[g.worldCell] || (s.byCell[g.worldCell] = { groups: 0, prims: 0, tris: 0, venues: [] });
      bc.groups++; bc.prims += c.prims; bc.tris += c.tris;
      if (!bc.venues.includes(g.venue)) bc.venues.push(g.venue);
    }
    return s;
  }

  /**
   * Portal test. An interior is drawn when the camera is inside it, or when it
   * is on the outside of a doorway that is on screen and within range.
   *
   * This is the cheap half of a portal system — it decides visibility of the
   * whole interior cell, not per-object visibility through the aperture — and
   * that is the half that matters here: the church nave is ~9,000 triangles
   * across six materials that would otherwise be drawn, occluded, from every
   * point in the town.
   */
  interiorVisible(g, eye) {
    if (g.box.containsPoint(eye)) return true;
    for (const p of g.portals || []) {
      if (p.pos.distanceToSquared(eye) > p.range * p.range) continue;
      // Outside the doorway plane, i.e. actually able to look in through it.
      if ((eye.x - p.pos.x) * p.nx + (eye.z - p.pos.z) * p.nz < -0.2) continue;
      this._v.copy(p.pos);
      if (this._frustum.intersectsSphere(new THREE.Sphere(this._v, p.radius + 0.5))) return true;
    }
    return false;
  }

  /** Cells the town actually occupies — the partition interest management will
   *  subscribe on (docs/ARCHITECTURE.md §3). */
  occupiedCells() {
    return [...new Set(this.groups.map(g => g.worldCell))].sort();
  }
}
