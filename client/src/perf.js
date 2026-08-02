/**
 * Frame cost, measured the same way in every renderer that draws Hearthmere.
 *
 * BUILD_DIRECTIVE §7 sets a draw-call and triangle budget. Until this module
 * existed the two instruments that measured it disagreed by 3x — 2,153 draws in
 * `tools/check_client.mjs` against 727 in `tools/render/town.mjs`, on the same
 * town — and neither was labelled with what it had actually counted. The cause
 * is one line of three.js (r180 `WebGLRenderer.render`):
 *
 *     shadowMap.render( shadowsArray, scene, camera );
 *     ...
 *     if ( this.info.autoReset === true ) this.info.reset();      // <-- AFTER
 *
 * The reset happens AFTER the shadow pass. So:
 *
 *   - `tools/render/town.html` left `autoReset` at its default `true`, so every
 *     shadow draw it made was wiped before it read the counter. Its report said
 *     "scene pass + shadow pass" and its `shadowCalls` column said 16; the
 *     shadow pass was in fact entirely absent, and the 16 was the handful of
 *     un-instrumented helpers (sky dome, water, scale figure) that its own
 *     per-object tally did not see.
 *   - `client/src/main.js` set `autoReset = false` and reset once per tick, so
 *     its counter accumulated the whole frame: scene pass, shadow maps, the
 *     GTAO pass's full normal+depth G-buffer render, and every post quad.
 *
 * Two different quantities, both called "draw calls". This module makes the
 * quantity explicit and measures it identically in both places.
 *
 * ## What is counted
 *
 * A frame is divided into STAGES, and every draw is attributed to exactly one:
 *
 *   `scene`   the beauty pass — what ends up on screen
 *   `shadow`  shadow-map rendering, via three's `onAfterShadow` hook
 *   `ao`      the ambient-occlusion G-buffer, a second full scene render
 *   `post`    every full-screen quad in the frame: the AO resolve and denoise,
 *             the bloom mip chain, the tonemap, the grade and the vignette
 *
 * `scene`, `shadow` and `ao` are counted PER OBJECT, so they can be attributed
 * to a venue, a cell and an LOD level. `post` is what is left over from the
 * renderer's own counter — the quads belong to no venue, so a remainder is the
 * honest way to hold them, and it also means nothing in the frame can escape
 * the total by not being instrumented.
 *
 * The §7 number is `total` — every draw the GPU is asked for. A budget that
 * counts only the beauty pass is not a budget, it is a third of one.
 */

/** BUILD_DIRECTIVE §7, in one place. Both instruments read it from here. */
export const BUDGET = {
  drawCalls: 900,
  triangles: 3_500_000,
  textureBytes: 1.5 * 1024 * 1024 * 1024,
};

const STAGES = ['scene', 'shadow', 'ao', 'post'];

function zeroStage() { return { draws: 0, tris: 0 }; }

/** Triangles one draw submits, instances included. Cached: geometry is static. */
function triCount(o) {
  const g = o.geometry;
  if (!g) return 0;
  const n = (g.index ? g.index.count : (g.attributes.position?.count || 0)) / 3;
  return n * (o.isInstancedMesh ? o.count : 1);
}

export class FrameProbe {
  /**
   * @param {THREE.WebGLRenderer} renderer
   */
  constructor(renderer) {
    this.renderer = renderer;
    // Non-negotiable, and the reason this class takes the renderer: with
    // autoReset on, `info` describes whatever ran after the last internal
    // reset, which is the scene pass of the last render() call. Off, plus one
    // reset per frame from `beginFrame()`, and it describes the frame.
    renderer.info.autoReset = false;
    this.enabled = true;
    this.stage = 'scene';
    this._instrumented = new WeakSet();
    this.reset();
  }

  reset() {
    this.stages = Object.fromEntries(STAGES.map(s => [s, zeroStage()]));
    this.byVenue = {};
    this.byCell = {};
    this.byLod = [0, 0, 0, 0];
    this.shadowByVenue = {};
    this.shadowByLod = [0, 0, 0, 0];
    this.instances = 0;
    this._total = zeroStage();
    this.byCascade = (this._shadowCams ? [...this._shadowCams.values()] : [])
      .map(() => zeroStage());
    this._unattributedShadow = zeroStage();
  }

  /**
   * Name the shadow cameras so a shadow draw can be attributed to the CASCADE
   * that asked for it.
   *
   * The shadow pass is the largest stage in this frame and was, until this
   * existed, one undivided number — which made "per-cascade caster culling"
   * an argument rather than a measurement. `onAfterShadow` hands the object the
   * shadow camera it was drawn for, and a cascade IS its shadow camera, so the
   * split costs one Map lookup per shadow draw and nothing per frame.
   *
   * @param {THREE.Camera[]} cams one per cascade, in cascade order
   */
  setShadowCameras(cams) {
    this._shadowCams = new Map();
    (cams || []).forEach((c, i) => { if (c) this._shadowCams.set(c, i); });
    this.byCascade = (cams || []).map(() => zeroStage());
    return this;
  }

  /** Start a frame: clear the tallies and the renderer's own counter. */
  beginFrame() {
    this.reset();
    this.renderer.info.reset();
    this.stage = 'scene';
  }

  /** Close a frame: fold the renderer's counter in and derive `post`. */
  endFrame() {
    const r = this.renderer.info.render;
    this._total = { draws: r.calls, tris: r.triangles };
    const named = STAGES.filter(s => s !== 'post')
      .reduce((a, s) => ({ draws: a.draws + this.stages[s].draws,
                           tris: a.tris + this.stages[s].tris }), zeroStage());
    // Post is the remainder, floored at zero: a renderer that counted fewer
    // draws than the object hooks saw means the hooks are attributing work the
    // GPU never did, and a negative row would hide that rather than show it.
    this.stages.post = { draws: Math.max(0, r.calls - named.draws),
                         tris: Math.max(0, r.triangles - named.tris) };
    return this.report();
  }

  /**
   * Attribute every draw of one placed venue.
   *
   * `key` is the placement key (`v.instance || v.id`), `cellOf` maps a world
   * point to the town's own cell label so attribution lands in the same
   * partition docs/ARCHITECTURE.md §3 names.
   */
  instrument(root, key, cellOf, THREE) {
    root.traverse(o => {
      if (!o.isMesh && !o.isInstancedMesh) return;
      if (this._instrumented.has(o)) return;
      this._instrumented.add(o);
      let hm = null;
      for (let p = o; p; p = p.parent) {
        if (p.userData?.hm && p.userData.hm.venue !== undefined) { hm = p.userData.hm; break; }
      }
      const lod = hm?.lod ?? 0;
      const inst = o.isInstancedMesh ? o.count : 0;
      const tris = triCount(o);
      let cell = null;
      const cellFor = () => {
        if (cell === null) {
          const c = new THREE.Box3().setFromObject(o).getCenter(new THREE.Vector3());
          cell = cellOf ? cellOf(c.x, c.z) : 'n/a';
        }
        return cell;
      };
      const tally = (stage, shadowCam) => {
        if (!this.enabled) return;
        const s = this.stages[stage];
        s.draws++; s.tris += tris;
        if (stage === 'shadow') {
          const ci = shadowCam ? this._shadowCams?.get(shadowCam) : undefined;
          const bucket = ci === undefined ? this._unattributedShadow : this.byCascade[ci];
          if (bucket) { bucket.draws++; bucket.tris += tris; }
          // Where the shadow pass GOES. It is the largest stage in the frame,
          // and one number for it names nothing to fix.
          const sv = this.shadowByVenue[key] || (this.shadowByVenue[key] = { draws: 0, tris: 0 });
          sv.draws++; sv.tris += tris;
          this.shadowByLod[Math.min(3, lod)]++;
        }
        if (stage !== 'scene') return;      // attribution is about the beauty pass
        this.byLod[Math.min(3, lod)]++;
        this.instances += inst;
        const bv = this.byVenue[key] || (this.byVenue[key] = { draws: 0, tris: 0, instances: 0 });
        bv.draws++; bv.tris += tris; bv.instances += inst;
        const k = cellFor();
        const bc = this.byCell[k] || (this.byCell[k] = { draws: 0, tris: 0, venues: [] });
        bc.draws++; bc.tris += tris;
        if (!bc.venues.includes(key)) bc.venues.push(key);
      };
      o.onAfterRender = () => tally(this.stage);
      // three r165+ calls this from WebGLShadowMap, and it is the only hook
      // that can tell a shadow draw from a beauty draw — `getRenderTarget()`
      // cannot, because the AO G-buffer and the composer's own buffers are
      // render targets too.
      o.onAfterShadow = (_r, _o, _cam, shadowCam) => tally('shadow', shadowCam);
    });
  }

  /**
   * Wrap an EffectComposer's passes so each one renders under its own stage.
   *
   * The AO pass renders the whole scene again into a G-buffer; without this it
   * would be tallied as a second beauty pass and the `scene` row would read
   * double. Pass names are matched on constructor name, so a chain that gains a
   * pass keeps working — an unrecognised pass that draws objects lands in
   * `scene`, which is conservative in the direction that shows up.
   */
  wrapComposer(composer) {
    for (const pass of composer.passes) {
      if (pass.__hmProbed) continue;
      pass.__hmProbed = true;
      const name = pass.constructor?.name || '';
      const stage = /GTAO|SSAO|SAO/.test(name) ? 'ao'
                  : /RenderPass/.test(name) ? 'scene'
                  : 'post';
      const inner = pass.render.bind(pass);
      pass.render = (...args) => {
        const prev = this.stage;
        this.stage = stage;
        try { return inner(...args); } finally { this.stage = prev; }
      };
    }
    return composer;
  }

  /** The one canonical shape. Both instruments print this and nothing else. */
  report(extra = {}) {
    const s = this.stages;
    const total = this._total.draws
      ? this._total
      : STAGES.reduce((a, k) => ({ draws: a.draws + s[k].draws, tris: a.tris + s[k].tris }), zeroStage());
    return {
      drawCalls: total.draws,
      triangles: total.tris,
      stages: {
        scene: { ...s.scene }, shadow: { ...s.shadow },
        ao: { ...s.ao }, post: { ...s.post },
      },
      byLod: this.byLod.slice(),
      shadowByCascade: (this.byCascade || []).map(c => ({ ...c })),
      shadowUnattributed: { ...this._unattributedShadow },
      shadowByVenue: JSON.parse(JSON.stringify(this.shadowByVenue)),
      shadowByLod: this.shadowByLod.slice(),
      instances: this.instances,
      byVenue: JSON.parse(JSON.stringify(this.byVenue)),
      byCell: JSON.parse(JSON.stringify(this.byCell)),
      budget: { ...BUDGET },
      ...extra,
    };
  }
}

/** One line, identical wherever the number is printed. */
export function formatFrame(p) {
  const st = p.stages;
  const n = x => x.toLocaleString('en-US');
  const casc = (p.shadowByCascade || []).length
    ? ` [c${(p.shadowByCascade).map(c => c.draws).join('/')}` +
      (p.shadowUnattributed?.draws ? `+${p.shadowUnattributed.draws}?` : '') + ']'
    : '';
  return `${p.drawCalls} draws / ${n(p.triangles)} tris  ` +
         `= scene ${st.scene.draws} + shadow ${st.shadow.draws}${casc} + ` +
         `ao ${st.ao.draws} + post ${st.post.draws}`;
}
