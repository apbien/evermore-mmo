/**
 * The sun's shadow rig: cascaded shadow maps, in ONE module, for all three
 * renderers.
 *
 * WHY THIS FILE EXISTS
 * --------------------
 * `docs/ARCHITECTURE.md` §5 specifies "one directional key (sun) with cascaded
 * shadow maps". It was never built. What shipped instead was a single
 * orthographic shadow camera with a 92 m box at 4096² — 44.5 texels per metre,
 * a 2.2 cm texel — declared in three places that had already drifted:
 *
 *   client/src/main.js:83   left/right/top/bottom ±46, near 0.5, far 200
 *   tools/render/town.html  CLIENT_SHADOW { half: 46, dist: 70 }
 *   tools/render/viewer.html sc.left = -45 … sc.far = 220
 *
 * `review/reports/ad-town-04.md` §1 rejected the build on what that does to the
 * spawn frame: the sun/shade boundary crosses the church nave as a blocky
 * right-angled staircase, in the composition BUILD_DIRECTIVE §3 calls the most
 * important in the project. A single box cannot be both wide enough to hold the
 * town's casters and fine enough for a 1.62 m eye — that is the entire reason
 * cascades exist.
 *
 * WHAT IT DOES
 * ------------
 * Three cascades fitted to the CAMERA FRUSTUM rather than to a box around the
 * player, so the near band gets a dense map over a small area and the far band
 * a coarse map over a large one. Each cascade is a light-space square sized by
 * the diagonal of its frustum slice and snapped to its own texel grid, which is
 * what keeps the edge from crawling when the camera turns.
 *
 * The shader work is three's own `three/addons/csm/CSM.js`, whose
 * `CSMShader.lights_fragment_begin` selects exactly one cascade per fragment by
 * view depth. This module owns the POLICY — how many cascades, where they
 * split, how big each map is, how far shadows reach — and the policy is
 * authored in `content/town/hearthmere.json → lighting.shadows`, the same way
 * the 09:30 rig itself is (D-009). Nothing here is a literal except the
 * fallbacks.
 *
 * COST IS THE SAME PROBLEM AS QUALITY
 * -----------------------------------
 * The shadow pass was already BIGGER than the beauty pass — 600 shadow draws
 * against 498 scene draws at the `square` camera — because a ±46 m box around
 * the player contains every caster within 46 m in EVERY direction, including
 * the two-thirds of them that are behind the lens. Cascades fitted to the
 * frustum draw a fraction of that in the near bands, and the far band is the
 * only expensive one. The three boxes below (≈16 m, ≈34 m, ≈82 m across) cover
 * less total area than the one 92 m box they replace, so this is not a quality
 * increase bought with draw calls — it is both at once. `stats()` reports the
 * measured texel density and box size per cascade so a review can check the
 * claim rather than take it.
 *
 * TWO MODES, because a review harness has cameras no player holds:
 *
 *   fitCascades(camera)          gameplay perspective cameras. The client runs
 *                                this every frame; the harness runs it for
 *                                every eye-level view. Both derive the rig from
 *                                the camera alone, so they cannot disagree.
 *   fitSingle(camera, c, r)      the plan, the aerials and the silhouette —
 *                                orthographic or 200 m up, where a cascade
 *                                split on view depth is meaningless. One box
 *                                over the whole town, cascades 1..n parked.
 */

import * as THREE from 'three';
import { CSM } from 'three/addons/csm/CSM.js';

/**
 * Authored in `content/town/hearthmere.json → lighting.shadows`. Repeated here
 * only so a renderer pointed at a town document that predates the block still
 * draws shadows — the content file is the authority.
 *
 *   distance   metres of shadowed depth from the eye. Beyond it the sun still
 *              lights the town, it just stops casting. Must be >= the LOD
 *              layer's SHADOW_CAST_DISTANCE or casters are dropped before the
 *              shadow camera ever sees them.
 *   splits     cascade boundaries as fractions of `distance`. Authored, not
 *              computed: three's 'practical' scheme is tuned for a 1000 m view
 *              distance and puts its first break at 18 % of a 40 m range, which
 *              is 7 m — too far out to help the frame that was rejected.
 *   mapSizes   one per cascade. The far cascade is the big one BECAUSE it
 *              covers the big box; giving all three 2048 would leave the
 *              18–40 m band coarser than the single map it replaces.
 *   margin     how far up-sun of a cascade's box the light stands. A building
 *              outside the frustum still casts INTO it — at 38° elevation a
 *              12 m gable throws a 15 m shadow — so this is what stops shadows
 *              popping in at the edge of frame.
 */
export const SHADOW_DEFAULTS = {
  cascades: 3,
  // How far shadows reach AND the radius of the caster set — both renderers
  // hand this straight to `VisibilitySet({ shadowDistance })`, so a batch
  // beyond it has already had `castShadow` turned off. The two are one
  // decision: a cascade reaching past the caster radius renders nothing, and a
  // caster radius reaching past the cascades pays for shadows nobody sees.
  distance: 32.0,
  splits: [0.17, 0.44],
  mapSizes: [4096, 4096, 4096],
  // EQUAL map sizes, and that is not laziness. CSM snaps each cascade's light
  // position to a texel grid derived from its single `shadowMapSize`; if a
  // cascade's real map is a non-power-of-two multiple of that grid the snap
  // lands between texels and the shadow edge crawls when the camera moves.
  // Equal sizes make the grid exact for every cascade.
  bias: -0.0004,
  // Scaled per cascade by that cascade's own texel size — see the constructor.
  // A normal offset tuned for a 2.2 cm texel peter-pans a 0.3 cm one and lets
  // a 4 cm one acne, so one number for three cascades is one number wrong
  // twice.
  normalBias: 0.02,
  normalBiasTexelRef: 0.0225,     // the 92 m / 4096 texel this was tuned at
  // Blend across the cascade boundary. Without it the density change at the
  // split is a hard line across the ground — and at 3.6x between cascade 0 and
  // cascade 1 that line is visible, which would be a NEW artefact in the frame
  // this work exists to fix.
  fade: true,
  margin: 55.0,
  near: 0.5,
  far: 200.0,
};

/** Read the authored block over the fallbacks. */
export function readShadows(lighting) {
  const s = Object.assign({}, SHADOW_DEFAULTS, (lighting && lighting.shadows) || {});
  s.cascades = Math.max(1, Math.min(4, s.cascades | 0));
  // A malformed split list is worse than none: it would silently give one
  // cascade the whole range and the others nothing.
  if (!Array.isArray(s.splits) || s.splits.length !== s.cascades - 1) {
    s.splits = SHADOW_DEFAULTS.splits.slice(0, s.cascades - 1);
  }
  if (!Array.isArray(s.mapSizes) || s.mapSizes.length !== s.cascades) {
    s.mapSizes = SHADOW_DEFAULTS.mapSizes.slice(0, s.cascades);
  }
  s.__authored = !!(lighting && lighting.shadows);
  return s;
}

/** World-space unit vector pointing AT the sun. Identical to
 *  `atmosphere.js sunDirection()`; if these two ever disagree the haze glows on
 *  one side of the sky and the shadows fall from the other. */
export function sunVector(lighting) {
  const el = (lighting?.sunElevationDeg ?? 38) * Math.PI / 180;
  const az = (lighting?.sunAzimuthDeg ?? 125) * Math.PI / 180;
  return new THREE.Vector3(Math.cos(el) * Math.sin(az), Math.sin(el), Math.cos(el) * Math.cos(az));
}

const _v = new THREE.Vector3();

/**
 * Materials that get the leaf transmission term. Keyed off the material NAME,
 * which is the library key — the same contract `client/src/ambient.js` uses for
 * wind and `tools/assetgen/core/vegetation.py SWAY_MATERIALS` publishes.
 */
const FOLIAGE_RE = /^(leaf_|hedge$|ivy$|foliage|reed$|weeds$|tree_far$|moss$)/;

/**
 * Leaf transmission — authored in `lighting.foliage`, defaulted here.
 *
 * `ad-town-05.md` §3: *"a third of cards are still silhouette-black and the lit
 * ones blow to pure white"*. That is what a canopy does when it is shaded as an
 * opaque dielectric: at 09:30 with a 38 deg sun, a large share of every crown is
 * seen from the shaded side, and a leaf seen from its shaded side is not black —
 * it is the brightest green in the frame, because a leaf is 0.1 mm of
 * translucent tissue and the sun goes through it. Art Bible §1 already asks for
 * exaggerated bounce and rim; this is the same request, on the surface that
 * covers most of the sky in this town.
 *
 *   transmission  strength of light arriving through the leaf
 *   wrap          how far the diffuse terminator is carried past 90 deg. A leaf
 *                 has no dark side at all in daylight; this is what stops the
 *                 unlit half going to the ambient floor.
 *   tint          what the leaf does to the light on the way through. Green
 *                 tissue passes yellow-green and eats blue, which is why a
 *                 backlit canopy is warmer AND more saturated than a lit one.
 *   viewGain      extra when looking toward the sun. Physically it is forward
 *                 scattering; in the frame it is the reason a tree between you
 *                 and the sun glows and the same tree behind you does not.
 */
export const FOLIAGE_DEFAULTS = {
  // Tuned against `t-square`, which is the worst case in the town: the market
  // oak sits between the camera and a 38 deg sun, so the whole crown is
  // forward-scattering at once. At 0.55/1.25 that frame was a real tree and a
  // flat one — the glow reached far enough round the terminator to take the
  // canopy's own depth out. 0.40 at a steeper power keeps the glow on the cards
  // that are actually backlit and leaves the layers behind them dark, which is
  // where a canopy's volume comes from.
  transmission: 0.40,
  wrap: 0.12,
  tint: [1.00, 1.28, 0.46],
  viewGain: 0.78,
  power: 1.55,
};

export class SunRig {
  /**
   * @param {object}  o
   * @param {THREE.Scene}  o.scene    cascade lights are added here
   * @param {object}  o.lighting      `town.lighting`
   * @param {THREE.Camera} o.camera   the camera the cascades are fitted to
   */
  constructor({ scene, lighting, camera }) {
    this.scene = scene;
    this.lighting = lighting || {};
    this.cfg = readShadows(this.lighting);
    this.sunDir = sunVector(this.lighting);
    this.mode = 'cascaded';
    this._sig = '';

    const c = this.cfg;
    this.csm = new CSM({
      camera,
      parent: scene,
      cascades: c.cascades,
      maxFar: c.distance,
      mode: 'custom',
      // Authored splits. CSM wants them as fractions of `far`, last entry 1.
      customSplitsCallback: (amount, near, far, target) => {
        target.length = 0;
        for (let i = 0; i < amount - 1; i++) target.push(c.splits[i]);
        target.push(1);
      },
      // The SNAP grid, not the allocation. `update()` quantises each cascade's
      // light position to `box / shadowMapSize`; taking the MINIMUM authored
      // size makes that grid a whole multiple of every cascade's real texel, so
      // the snap stays exact even if the sizes are ever made to differ.
      shadowMapSize: Math.min(...c.mapSizes),
      shadowBias: c.bias,
      lightDirection: this.sunDir.clone().negate(),   // from the sun, downward
      lightIntensity: this.lighting.sun?.intensity ?? 3.2,
      lightNear: c.near,
      lightFar: c.far,
      lightMargin: c.margin,
    });

    this.csm.fade = !!c.fade;

    // Per-cascade map size and per-cascade normal bias.
    //
    // `mapSize` is written ONCE, here, and never again: three allocates the
    // shadow render target lazily on the first shadow render and only when
    // `shadow.map === null`, so a size changed after the first frame is a
    // number in a field that nothing reads. Everything downstream that wants
    // to know how big the map really is reads `shadow.map.width` — see
    // `stats()`.
    this.csm.lights.forEach((l, i) => {
      l.shadow.mapSize.set(c.mapSizes[i], c.mapSizes[i]);
      l.shadow.bias = c.bias;
      l.shadow.normalBias = c.normalBias;      // refined by _rebias() per fit
      l.name = `hm.sun.cascade${i}`;
    });
    this._rebias();

    this.applyLighting(this.lighting);

    // Every material lit by the sun must be registered or it takes the stock
    // three path, which loops over ALL directional lights — and the cascades
    // are three copies of one sun, so an unregistered material renders at 3x
    // the sun's intensity. `audit()` counts the misses.
    this._registered = new WeakSet();
    this._count = 0;

    // Per-cascade caster culling. Off until `bindCasters()`.
    this._casters = null;
    this._sliceCam = new THREE.PerspectiveCamera();
    this._sliceFrustum = new THREE.Frustum();
    this._sliceM = new THREE.Matrix4();
  }

  /**
   * Hand the rig the visibility set, so each cascade draws only the casters
   * whose shadows land in it.
   *
   * The shadow pass is the largest stage in a Hearthmere frame — 604 draws at
   * the `square` camera against a 462-draw beauty pass — and the reason is
   * structural: three culls a cascade against that cascade's light-space BOX,
   * which is the bounding square of its view-frustum slice. For the 5.4-30 m
   * cascade that square is ~68 m across, so it holds every caster inside the
   * 30 m caster radius in every direction including behind the lens, and every
   * one of them costs a depth draw.
   *
   * THE HOOK. `WebGLShadowMap.render()` does, per cascade:
   *
   *     shadow.updateMatrices( light, vp );
   *     _frustum = shadow.getFrustum();
   *     renderObject( scene, camera, shadow.camera, light, type );
   *
   * so `updateMatrices` is the last thing that runs before the scene walk for
   * THAT cascade — the one point at which "which casters does this cascade
   * need" can still be answered. Wrapping it per cascade needs no fork of
   * three, no second shadow loop and no change to the render order, and it is
   * the same per-object shadow culling an engine exposes as
   * `r.Shadow.CSMCasterPerObjectCulling`.
   *
   * Idempotent. Safe to call before or after the town is placed: the caster
   * geometry it needs is recomputed lazily inside `applyCascade`.
   *
   * @param {import('./lod.js').VisibilitySet} visibility
   */
  bindCasters(visibility, renderer) {
    this._casters = visibility || null;
    if (!visibility) return this;
    visibility.cascadeCull = true;
    visibility.setSun(this.sunDir);
    // Bracket the whole shadow pass. The merged depth proxies have to be
    // visible while three walks the scene for a cascade and invisible for the
    // beauty pass, and `WebGLRenderer.render()` makes that trivially safe: it
    // builds the beauty render list in `projectObject()` BEFORE it calls
    // `shadowMap.render()`, so a proxy that appears and disappears inside the
    // shadow pass was never a candidate for the frame it is in.
    const sm = renderer && renderer.shadowMap;
    if (sm && !sm.__hmBracket) {
      sm.__hmBracket = true;
      const inner = sm.render.bind(sm);
      sm.render = (lights, scene, camera) => {
        visibility.beginShadowPass();
        try { inner(lights, scene, camera); } finally { visibility.endShadowPass(); }
      };
    }
    this.csm.lights.forEach((l, i) => {
      const sh = l.shadow;
      if (sh.__hmCascade) return;
      sh.__hmCascade = true;
      const inner = sh.updateMatrices.bind(sh);
      sh.updateMatrices = (light, vp) => { inner(light, vp); this._cullCascade(i); };
    });
    return this;
  }

  /** Set the caster flags for cascade `i`. See `bindCasters`. */
  _cullCascade(i) {
    const vis = this._casters;
    if (!vis) return;
    const cam = this.csm.camera;
    // `fitSingle` — the plan, the aerials, the silhouette — is one box over the
    // whole town with no view-depth split, so there is no slice to cull to and
    // every eligible caster is kept. Culling those frames to a frustum would
    // make the harness draw a different town from the client, which is the one
    // thing D-023 exists to prevent.
    if (this.mode !== 'cascaded' || !cam || !cam.isPerspectiveCamera) {
      // One box over the whole town: there is no slice to cull to, and the box
      // is hundreds of metres across so three's own test rejects nothing —
      // which is exactly the case the merged proxy is for. `forceProxy` because
      // the near-cascade exemption is about a 12 m box and there isn't one.
      vis.applyCascade(i, null, true);
      return;
    }
    vis.applyCascade(i, this.sliceFrustum(i));
  }

  /**
   * The receiver region of cascade `i`, as a view frustum.
   *
   * It runs from the camera's own near plane to the cascade's far split, NOT
   * from the previous split — deliberately. `fade` blends across the boundary,
   * so a fragment just inside the split samples the cascade beyond it too, and
   * a near caster's shadow is long: at a 38 deg sun a 12 m gable throws 15 m.
   * Cutting the near end would buy a few draws in the near cascades — where
   * there is almost nothing to cull, the boxes are already small — at the price
   * of a missing shadow at a blend seam. The win is lateral, not radial.
   */
  sliceFrustum(i) {
    const cam = this.csm.camera;
    const s = this._sliceCam;
    // Cascade far depths come off CSM's own split, in view space, so this
    // cannot drift from the cascade the shader selects.
    const fr = this.csm.frustums?.[i];
    const farI = fr ? Math.abs(fr.vertices.far[0].z) : this.cfg.distance;
    s.fov = cam.fov; s.aspect = cam.aspect; s.zoom = cam.zoom;
    s.filmGauge = cam.filmGauge; s.filmOffset = cam.filmOffset;
    s.near = cam.near;
    s.far = farI + Math.max(3, farI * 0.15);   // fade margin, and then some
    s.updateProjectionMatrix();
    this._sliceM.multiplyMatrices(s.projectionMatrix, cam.matrixWorldInverse);
    this._sliceFrustum.setFromProjectionMatrix(this._sliceM);
    return this._sliceFrustum;
  }

  /** The lights, for a caller that needs to poke the rig directly. */
  get lights() { return this.csm.lights; }

  /**
   * Scale each cascade's normal bias by its own texel size.
   *
   * `normalBias` pushes the shadow lookup along the surface normal by a fixed
   * number of WORLD metres, and the amount needed is one to two texels — that
   * is the whole geometry of the artefact it cures. The authored 0.02 was tuned
   * against the single 92 m / 4096 map, i.e. a 2.25 cm texel. Cascade 0's texel
   * is 0.3 cm; leaving 0.02 there detaches every contact shadow by 2 cm, which
   * is exactly the "the figure floats" note in the review. Cascade 2's texel is
   * 2.2 cm and wants the full amount.
   *
   * Called after any refit, because the box size — and therefore the texel —
   * changes with the camera's FOV and aspect.
   */
  _rebias() {
    const c = this.cfg;
    const ref = c.normalBiasTexelRef || SHADOW_DEFAULTS.normalBiasTexelRef;
    this.csm.lights.forEach((l, i) => {
      const cam = l.shadow.camera;
      const box = cam.right - cam.left;
      const px = c.mapSizes[i] || c.mapSizes[c.mapSizes.length - 1];
      const texel = box > 0 && px > 0 ? box / px : ref;
      // Floored at a fifth of the authored value: a 3 mm offset on cascade 0 is
      // still enough to keep a flat sunlit floor off its own shadow, and going
      // to zero would trade the staircase for acne.
      l.shadow.normalBias = Math.max(c.normalBias * 0.2, c.normalBias * texel / ref);
    });
  }

  /** Colour, intensity and sun angle from the authoritative rig in content. */
  applyLighting(L) {
    if (!L) return;
    this.lighting = L;
    this.sunDir.copy(sunVector(L));
    this.csm.lightDirection.copy(this.sunDir).negate();
    const col = new THREE.Color(L.sun?.color || '#FFF2D8');
    const int = L.sun?.intensity ?? 3.2;
    for (const l of this.csm.lights) { l.color.copy(col); l.intensity = int; }
    // Shadow reach is a function of the sun's ELEVATION, so a moved sun
    // invalidates every group's swept-shadow bound.
    if (this._casters) this._casters.setSun(this.sunDir);
  }

  /**
   * Register every sun-lit material under `root`.
   *
   * MUST run after any other system that sets `onBeforeCompile` on the same
   * material — `client/src/water.js` and `client/src/ambient.js` both do — so
   * the existing hook is captured and chained rather than dropped. A dropped
   * CSM hook means the `CSM_cascades` uniform never gets a value and every
   * fragment falls into cascade 0.
   */
  register(root) {
    if (!root) return 0;
    let n = 0;
    root.traverse(o => {
      const mats = o.material ? (Array.isArray(o.material) ? o.material : [o.material]) : [];
      for (const m of mats) {
        if (!m || this._registered.has(m)) continue;
        // Only materials that run the lighting chunks. A ShaderMaterial (the
        // sky dome) has no RE_Direct and nothing to select a cascade for.
        if (!(m.isMeshStandardMaterial || m.isMeshPhysicalMaterial ||
              m.isMeshLambertMaterial || m.isMeshPhongMaterial ||
              m.isMeshToonMaterial)) continue;
        this._registered.add(m);
        // Leaf transmission goes on FIRST so that it is captured as `prev` and
        // chained by the CSM wrapper below, exactly as water's and ambient's
        // hooks are. See `_transmit`.
        this._transmit(m);
        const prev = m.onBeforeCompile;
        this.csm.setupMaterial(m);
        const csmHook = m.onBeforeCompile;
        m.onBeforeCompile = function (shader, renderer) {
          csmHook.call(this, shader, renderer);
          if (prev && prev !== csmHook) prev.call(this, shader, renderer);
        };
        m.needsUpdate = true;
        n++;
      }
    });
    this._count += n;
    return n;
  }

  /**
   * Leaf transmission, for one material. No-op unless the material's NAME is a
   * foliage library key.
   *
   * `ad-town-05.md` §3, third item: *"a third of cards are still
   * silhouette-black and the lit ones blow to pure white"*. A leaf is 0.1 mm of
   * translucent tissue: at a 38 deg sun a large share of every canopy in this
   * town is seen from its shaded side, and that side is not dark — it is the
   * brightest, most saturated green in the frame. Shading foliage as an opaque
   * dielectric is what makes a procedural tree read as plastic, and it is one
   * term.
   *
   * It lives in the sun rig rather than in `client/src/ambient.js` — where the
   * other foliage shader hook is — for one reason that decides it: **the review
   * harness does not run `ambient.js`.** `tools/render/town.html` imports
   * `atmosphere.js`, `shadows.js`, `lod.js`, `perf.js` and `water.js` and
   * nothing else, so a term added to the wind hook would be invisible in every
   * frame this project is judged from. It is also, properly, a sun term: it
   * needs the sun's direction, colour and intensity, and this class is the only
   * thing that owns all three.
   *
   * Three parts, and each answers a different half of the defect:
   *
   *   `back`  light arriving through the leaf. `geometryNormal` has already been
   *           flipped to face the viewer by `normal_fragment_begin` on a
   *           double-sided material, so a positive dot against the sun means the
   *           light is on the far side — which is exactly the case that renders
   *           black today.
   *   `fwd`   forward scatter: much stronger looking INTO the sun than away from
   *           it. Without it every canopy glows from every angle and the town
   *           looks lit from inside.
   *   `wrap`  a soft terminator so the unlit half never falls to the ambient
   *           floor. This is the term that fixes the hedges as well as the
   *           trees, and `ad-town-05.md` §8 asks for exactly it.
   *
   * `diffuseColor` at that point already carries the albedo AND `COLOR_0`, so
   * `vegetation.leaf_cards`' crown-depth shade attenuates the glow inside the
   * canopy for free: a leaf four layers in does not transmit the sun.
   */
  _transmit(m) {
    if (!m || !FOLIAGE_RE.test(m.name || '') || m.userData.__leafTransmit) return false;
    const f = Object.assign({}, FOLIAGE_DEFAULTS, this.lighting.foliage || {});
    if (!(f.transmission > 0 || f.wrap > 0)) return false;
    m.userData.__leafTransmit = true;
    const sun = new THREE.Color(this.lighting.sun?.color || '#FFF2D8');
    const u = {
      uLeafSunW: { value: this.sunDir.clone() },
      uLeafSun: { value: new THREE.Vector3(sun.r, sun.g, sun.b)
                    .multiplyScalar(this.lighting.sun?.intensity ?? 3.2) },
      uLeafTint: { value: new THREE.Vector3(...f.tint) },
      uLeafTrans: { value: +f.transmission },
      uLeafWrap: { value: +f.wrap },
      uLeafView: { value: +f.viewGain },
      uLeafPow: { value: +f.power },
    };
    const prev = m.onBeforeCompile;
    m.onBeforeCompile = function (shader, renderer) {
      if (prev) prev.call(this, shader, renderer);
      Object.assign(shader.uniforms, u);
      shader.fragmentShader = shader.fragmentShader
        .replace('#include <common>', `#include <common>
uniform vec3 uLeafSunW; uniform vec3 uLeafSun; uniform vec3 uLeafTint;
uniform float uLeafTrans; uniform float uLeafWrap; uniform float uLeafView;
uniform float uLeafPow;`)
        .replace('#include <opaque_fragment>', `
{
  vec3 leafL = normalize( ( viewMatrix * vec4( uLeafSunW, 0.0 ) ).xyz );
  float leafBack = max( 0.0, dot( -geometryNormal, leafL ) );
  float leafFwd  = clamp( dot( -geometryViewDir, leafL ) * 0.5 + 0.5, 0.0, 1.0 );
  float leafGlow = pow( leafBack, uLeafPow )
                 * mix( 1.0 - uLeafView, 1.0, pow( leafFwd, 3.0 ) );
  float leafWrap = max( 0.0, dot( geometryNormal, leafL ) * 0.5 + 0.5 );
  outgoingLight += diffuseColor.rgb * uLeafTint * uLeafSun
                 * ( uLeafTrans * leafGlow + uLeafWrap * leafWrap * leafWrap );
}
#include <opaque_fragment>`);
    };
    m.needsUpdate = true;
    (this._leaf || (this._leaf = [])).push(u);
    return true;
  }

  /** Sun-lit materials in `scene` that `register()` never saw. Should be 0;
   *  anything else is drawn at `cascades`x the sun and the report must say so. */
  audit(scene) {
    const missed = [];
    (scene || this.scene).traverse(o => {
      const mats = o.material ? (Array.isArray(o.material) ? o.material : [o.material]) : [];
      for (const m of mats) {
        if (!m || this._registered.has(m)) continue;
        if (m.isMeshStandardMaterial || m.isMeshPhysicalMaterial ||
            m.isMeshLambertMaterial || m.isMeshPhongMaterial || m.isMeshToonMaterial) {
          if (!missed.includes(m.name || '(unnamed)')) missed.push(m.name || '(unnamed)');
        }
      }
    });
    return { registered: this._count, missed };
  }

  /**
   * Fit the cascades to a perspective gameplay camera. Call once per frame in
   * the client, once per view in the harness.
   */
  fitCascades(camera) {
    if (camera.isOrthographicCamera) {
      // No view-depth split is meaningful; the caller wanted fitSingle().
      return this.fitSingle(camera, _v.set(0, 0, 0), 100);
    }
    // Undo `fitSingle`'s parking. CSM's `_updateShadowBounds()` rewrites every
    // cascade's left/right/top/bottom and NOTHING ELSE — `near` and `far` are
    // written once, in `CSM._createLights()`, from `lightNear`/`lightFar`. So
    // the 0.1..0.2 m slab `fitSingle` puts on cascades 1..n to park them
    // SURVIVED the refit, and cascade 1 (5.4-30 m) went on rendering a 10 cm
    // deep shadow frustum for the rest of the session.
    //
    // This is the whole of `ad-town-05` §12. Its five probe runs measured
    // `--views square` at 1,385 draws and `--views plan,square` at 989 on
    // identical assets, and read it as "the harness samples the previous
    // frame's LOD state" — the LOD state is identical in both (177/544 batches
    // drawn, 193/93/171/10 by level, 467 scene draws). What differed was the
    // SHADOW pass, 604 against 220, because the default view list opens with
    // `plan` and every gameplay camera after it lost cascade 1.
    //
    // It was never only a measurement bug. A crippled cascade 1 does not draw
    // the shadows either, so every frame the standard command has ever produced
    // is missing its 5.4-30 m shadows — which is where a street tree's dapple
    // lands. See review/reports/instruments-06.md.
    if (this.mode === 'single') {
      for (const l of this.csm.lights) {
        const k = l.shadow.camera;
        k.near = this.cfg.near;
        k.far = this.cfg.far;
        k.updateProjectionMatrix();
      }
      this._sig = '';                     // and force the box refit below
    }
    this.csm.camera = camera;
    this.mode = 'cascaded';
    const sig = `${camera.fov}|${camera.aspect}|${camera.near}|${camera.far}|${this.cfg.distance}`;
    if (sig !== this._sig) {
      this._sig = sig;
      this.csm.maxFar = this.cfg.distance;
      // Rewrites every cascade's left/right/top/bottom from the frustum slice,
      // and therefore every cascade's texel size — so the bias has to follow.
      this.csm.updateFrustums();
      this._rebias();
    }
    camera.updateMatrixWorld();
    this.csm.update();
    return this;
  }

  /**
   * One box over `center` with radius `radius`, for the plan, the aerials and
   * the silhouette. Cascades 1..n-1 are parked on a degenerate box 20 km up so
   * the frustum test rejects everything and they cost nothing — parking them
   * geometrically rather than turning `castShadow` off keeps
   * `NUM_DIR_LIGHT_SHADOWS` constant, and therefore keeps every shader program
   * in the scene from being recompiled between views.
   */
  fitSingle(camera, center, radius) {
    this.mode = 'single';
    this._sig = '';                       // force a refit on the next cascade view
    const c = this.cfg;
    // BEFORE `_updateUniforms()`, which reads `camera.near` and `camera.far`
    // off this exact reference. Left pointing at the previous view's camera it
    // publishes that camera's depth range as `shadowFar`, and every fragment
    // lands in the wrong cascade — which on an orthographic plan 600 m up means
    // every fragment lands in NO cascade and the town renders unlit.
    this.csm.camera = camera;
    // `shadowFar` in the shader is min(camera.far, maxFar); every drawn fragment
    // must land inside cascade 0's [0,1] range or it loses its shadow, and an
    // orthographic plan sits 600 m above a town it is drawing.
    this.csm.maxFar = Math.max(camera.far || 2000, 1);
    this.csm.breaks.length = 0;
    for (let i = 0; i < c.cascades; i++) this.csm.breaks.push(1);
    this.csm._updateUniforms();

    const dist = Math.max(radius * 2.0, 120);
    const l0 = this.csm.lights[0];
    l0.target.position.copy(center);
    l0.target.updateMatrixWorld();
    l0.position.copy(center).addScaledVector(this.sunDir, dist);
    l0.updateMatrixWorld();
    const cam = l0.shadow.camera;
    cam.left = -radius; cam.right = radius; cam.top = radius; cam.bottom = -radius;
    cam.near = 0.5; cam.far = dist + radius * 2.5;
    cam.updateProjectionMatrix();

    for (let i = 1; i < this.csm.lights.length; i++) {
      const l = this.csm.lights[i];
      l.position.set(0, 20000, 0);
      l.target.position.set(0, 19999, 0);
      l.target.updateMatrixWorld();
      l.updateMatrixWorld();
      const k = l.shadow.camera;
      k.left = -0.01; k.right = 0.01; k.top = 0.01; k.bottom = -0.01;
      k.near = 0.1; k.far = 0.2;
      k.updateProjectionMatrix();
    }
    this._rebias();
    return this;
  }

  /**
   * What the rig actually is, measured off the live shadow cameras rather than
   * off the config — including the ALLOCATED map size, because three silently
   * clamps `mapSize` to the driver's `maxTextureSize` and a report that quotes
   * the requested size can be wrong by a factor of eight without saying so.
   */
  stats() {
    const c = this.cfg;
    const far = c.distance;
    const out = { mode: this.mode, cascades: [], distanceM: far,
                  fade: !!this.csm.fade, authored: !!c.__authored,
                  perCascadeCulling: !!this._casters };
    let prev = 0;
    this.csm.lights.forEach((l, i) => {
      const cam = l.shadow.camera;
      const box = +(cam.right - cam.left).toFixed(2);
      const alloc = l.shadow.map ? l.shadow.map.width : null;
      const px = alloc || l.shadow.mapSize.x;
      const hi = this.mode === 'cascaded'
        ? +( (this.csm.breaks[i] ?? 1) * far ).toFixed(1) : null;
      out.cascades.push({
        index: i,
        rangeM: this.mode === 'cascaded' ? [+prev.toFixed(1), hi] : null,
        boxM: box,
        mapPx: px,
        requestedPx: l.shadow.mapSize.x,
        texelsPerM: box > 0.02 ? +(px / box).toFixed(1) : null,
        texelCm: box > 0.02 ? +(box / px * 100).toFixed(2) : null,
        normalBias: +l.shadow.normalBias.toFixed(4),
        // Casters this cascade actually drew, after per-cascade culling. The
        // eligible set (`VisibilitySet.stats().shadowCasters`) is the ceiling.
        casters: this._casters?.cascadeCasters?.[i] ?? null,
      });
      if (hi != null) prev = hi;
    });
    return out;
  }
}
