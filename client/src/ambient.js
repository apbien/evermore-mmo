/**
 * Ambient life: smoke, fire flicker, cloth sway, dust motes.
 *
 * Art Bible §7 — "static worlds read as dioramas". A town where nothing moves
 * fails the AAA comparison no matter how well the buildings are modelled,
 * because the eye reads stillness as a photograph rather than a place.
 *
 * Everything here is driven by the `ambient` block in
 * content/town/hearthmere.json, so the parameters stay authoritative data
 * rather than magic numbers buried in the renderer.
 */

import * as THREE from 'three';

export class Ambient {
  constructor(scene, town, entities) {
    this.scene = scene;
    this.cfg = town.ambient || {};
    this.t = 0;
    this.swayers = [];
    this.smokes = [];
    this.fires = [];
    this.foliage = [];

    this._wind = new THREE.Vector3(...(this.cfg.wind?.direction || [0.8, 0, 0.5])).normalize();
    this._windSpeed = this.cfg.wind?.speed ?? 1.4;
    this._gustHz = this.cfg.wind?.gustHz ?? 0.35;

    this._buildFromEntities(entities);
    this._buildMotes();
  }

  /**
   * Entities declare their own effects — a chimney carries a `smoke`
   * component, a forge carries `light` with a flicker rate. The renderer
   * reads them; it does not invent them.
   */
  _buildFromEntities(entities) {
    for (const e of entities) {
      const p = e.transform?.pos;
      if (!p) continue;
      const c = e.components || {};
      if (c.smoke) this.addSmoke(new THREE.Vector3(...p), c.smoke);
      if (c.light) this.addLight(new THREE.Vector3(...p), c.light);
    }
  }

  // -- smoke ---------------------------------------------------------------

  addSmoke(pos, cfg = {}) {
    const N = 26;
    const geo = new THREE.BufferGeometry();
    const positions = new Float32Array(N * 3);
    const seeds = new Float32Array(N);
    for (let i = 0; i < N; i++) seeds[i] = Math.random();
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));

    const mat = new THREE.PointsMaterial({
      color: 0xBFB6AA, size: 0.85, transparent: true, opacity: 0.30,
      depthWrite: false, sizeAttenuation: true,
      blending: THREE.NormalBlending,
    });
    const pts = new THREE.Points(geo, mat);
    pts.frustumCulled = false;
    this.scene.add(pts);
    this.smokes.push({ pts, seeds, origin: pos.clone(), N,
                       rate: cfg.rate ?? 0.6,
                       drift: new THREE.Vector3(...(cfg.drift || [0.8, 0, 0.5])) });
  }

  // -- local lights --------------------------------------------------------

  addLight(pos, cfg = {}) {
    const light = new THREE.PointLight(
      new THREE.Color(cfg.color || '#FFB35C'),
      cfg.intensity ?? 1.8,
      cfg.range ?? 7.0,
      1.8);
    light.position.copy(pos).add(new THREE.Vector3(0, 0.4, 0));
    this.scene.add(light);
    const hz = cfg.flickerHz || [8, 12];
    this.fires.push({
      light, base: cfg.intensity ?? 1.8,
      hz: (hz[0] + hz[1]) * 0.5,
      // Forges flicker hard; a lantern barely moves. Driving both off one
      // amplitude makes lanterns look broken.
      amp: (cfg.intensity ?? 1.8) > 3.0 ? 0.22 : 0.07,
      phase: Math.random() * 100,
    });
  }

  // -- cloth ---------------------------------------------------------------

  /**
   * Register an object to sway. Banners and awnings pivot from their top
   * edge, so we rotate about the object's own origin and rely on venue
   * geometry hanging downward from it.
   */
  addSwayer(obj, amplitudeDeg = null, axis = 'z') {
    const amp = (amplitudeDeg ?? (this.cfg.cloth?.amplitudeDeg ?? 4.5)) * Math.PI / 180;
    const [lo, hi] = this.cfg.cloth?.swayHz || [0.3, 0.8];
    this.swayers.push({
      obj, amp, axis,
      hz: lo + Math.random() * (hi - lo),
      phase: Math.random() * Math.PI * 2,
      base: obj.rotation[axis],
    });
  }

  /** Find cloth-like meshes in a loaded venue and register them. */
  harvest(root) {
    const CLOTH = /banner|canvas|cloth/i;
    root.traverse(o => {
      if (!o.isMesh || !o.material) return;
      const name = o.material.name || '';
      if (CLOTH.test(name)) this.addSwayer(o, null, 'z');
    });
    this.harvestFoliage(root);
  }

  // -- vegetation ------------------------------------------------------------

  /**
   * Wind sway for anything that grows.
   *
   * Art Bible §7 lists vegetation under required motion, and the natural layer
   * is now the largest single thing in the scene — a still hedge next to a
   * swaying awning reads worse than no motion at all.
   *
   * Two things make this different from the cloth swayers above, and both are
   * forced by how the town is built:
   *
   *  - It is a VERTEX shader, not a node rotation. `core/venue.py` merges every
   *    primitive in a 48 m cell into one mesh and puts four hundred trees into
   *    one GPU instance batch, so there is no per-plant node left to rotate by
   *    the time this sees it. There never will be: that merge is what keeps the
   *    town inside the §7 draw-call budget.
   *  - Amplitude comes from height above the PRIMITIVE's own base, which is why
   *    `tools/assetgen/core/vegetation.py` splits a tree into a `timber_grey`
   *    trunk and a `leaf_*` canopy. The trunk's material is not in this list, so
   *    it stands still; the canopy's is, and the canopy starts above the fork.
   *    The split is the rig.
   *
   * The contract is the material NAME, which is the library key — see
   * `vegetation.SWAY_MATERIALS`. A venue gets sway by using one of those
   * materials and needs no client change.
   */
  harvestFoliage(root) {
    const FOLIAGE = /^(leaf_|hedge$|ivy$|foliage|reed$)/;
    root.traverse(o => {
      if (!o.isMesh || !o.material) return;
      const mats = Array.isArray(o.material) ? o.material : [o.material];
      for (const m of mats) {
        if (!FOLIAGE.test(m.name || '') || m.userData.__windPatched) continue;
        o.geometry.computeBoundingBox();
        const bb = o.geometry.boundingBox;
        // Stiffness: ivy on a wall barely moves, a willow moves a lot. Keyed off
        // the material because that is all this layer knows about the plant.
        const stiff = /^ivy$/.test(m.name) ? 0.25
                    : /^hedge$/.test(m.name) ? 0.45
                    : /^reed$/.test(m.name) ? 1.35
                    : /^leaf_willow$/.test(m.name) ? 1.5 : 1.0;
        const u = {
          uWindTime: { value: 0 },
          uWindDir: { value: new THREE.Vector2(this._wind.x, this._wind.z) },
          uWindAmp: { value: 0.055 * stiff * this._windSpeed },
          uWindBase: { value: bb.min.y },
          uWindSpan: { value: Math.max(0.35, bb.max.y - bb.min.y) },
        };
        m.userData.__windPatched = true;
        m.onBeforeCompile = (shader) => {
          Object.assign(shader.uniforms, u);
          shader.vertexShader = shader.vertexShader
            .replace('#include <common>', `#include <common>
              uniform float uWindTime; uniform vec2 uWindDir;
              uniform float uWindAmp; uniform float uWindBase; uniform float uWindSpan;`)
            .replace('#include <begin_vertex>', `#include <begin_vertex>
              {
                // World position, so neighbouring plants in one merged batch do
                // not all move in phase — which is the thing that makes
                // procedural wind read as a single wobbling object.
                vec4 wp = modelMatrix * vec4(transformed, 1.0);
                float h = clamp((wp.y - uWindBase) / uWindSpan, 0.0, 1.0);
                // Squared, so the base of a stem is planted and the tip is not.
                float k = h * h;
                float ph = wp.x * 0.21 + wp.z * 0.17;
                // Two incommensurate frequencies plus a slow gust envelope: one
                // sine is a metronome, and a metronome is worse than stillness.
                float gust = 0.62 + 0.38 * sin(uWindTime * 0.55 + ph * 0.15);
                float s = sin(uWindTime * 1.6 + ph) * 0.65
                        + sin(uWindTime * 3.7 + ph * 2.3) * 0.35;
                float a = uWindAmp * k * gust * uWindSpan;
                transformed.x += uWindDir.x * s * a;
                transformed.z += uWindDir.y * s * a;
                // Lift with the sway rather than stretching, so a card does not
                // shear its own length.
                transformed.y -= abs(s) * a * 0.22;
              }`);
          m.userData.__windUniforms = shader.uniforms;
        };
        m.needsUpdate = true;
        this.foliage.push(u);
      }
    });
  }

  // -- dust motes ----------------------------------------------------------

  _buildMotes() {
    if (this.cfg.particulate?.dustMotes === false) return;
    const N = 220;
    const geo = new THREE.BufferGeometry();
    const pos = new Float32Array(N * 3);
    this._moteBase = new Float32Array(N * 3);
    for (let i = 0; i < N; i++) {
      const x = (Math.random() - 0.5) * 90;
      const y = 0.4 + Math.random() * 6.0;
      const z = (Math.random() - 0.5) * 90;
      pos[i * 3] = this._moteBase[i * 3] = x;
      pos[i * 3 + 1] = this._moteBase[i * 3 + 1] = y;
      pos[i * 3 + 2] = this._moteBase[i * 3 + 2] = z;
    }
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    const mat = new THREE.PointsMaterial({
      color: 0xFFE9C4, size: 0.055, transparent: true, opacity: 0.55,
      depthWrite: false, blending: THREE.AdditiveBlending, sizeAttenuation: true,
    });
    this.motes = new THREE.Points(geo, mat);
    this.motes.frustumCulled = false;
    this.scene.add(this.motes);
    this._moteN = N;
  }

  // -- frame ---------------------------------------------------------------

  update(dt, playerPos) {
    this.t += dt;
    const gust = 0.65 + 0.35 * Math.sin(this.t * Math.PI * 2 * this._gustHz);

    for (const s of this.swayers) {
      s.obj.rotation[s.axis] = s.base +
        Math.sin(this.t * Math.PI * 2 * s.hz + s.phase) * s.amp * gust;
    }

    // One uniform write per foliage material, not per plant: every hedge in the
    // town shares a material and therefore shares this clock.
    for (const f of this.foliage) f.uWindTime.value = this.t;

    for (const f of this.fires) {
      // Two incommensurate frequencies: a single sine reads as a pulse, not
      // as fire.
      const n = Math.sin(this.t * f.hz + f.phase) * 0.6
              + Math.sin(this.t * f.hz * 2.7 + f.phase * 1.7) * 0.4;
      f.light.intensity = f.base * (1.0 + n * f.amp);
    }

    for (const sm of this.smokes) {
      const arr = sm.pts.geometry.attributes.position.array;
      for (let i = 0; i < sm.N; i++) {
        // Each particle runs a looping 0..1 life; age drives rise and drift.
        const life = (this.t * sm.rate * 0.25 + sm.seeds[i]) % 1.0;
        const rise = life * 7.5;
        const spread = life * life * 3.2;
        arr[i * 3]     = sm.origin.x + sm.drift.x * spread + Math.sin(life * 9 + i) * 0.35 * life;
        arr[i * 3 + 1] = sm.origin.y + rise;
        arr[i * 3 + 2] = sm.origin.z + sm.drift.z * spread + Math.cos(life * 7 + i) * 0.35 * life;
      }
      sm.pts.geometry.attributes.position.needsUpdate = true;
      sm.pts.material.opacity = 0.30 * gust;
    }

    if (this.motes && playerPos) {
      const arr = this.motes.geometry.attributes.position.array;
      for (let i = 0; i < this._moteN; i++) {
        const b = i * 3;
        // Drift slowly on the wind, and wrap around the player so motes are
        // always where the camera is without simulating the whole town.
        let x = arr[b] + this._wind.x * this._windSpeed * 0.05 * dt * 60;
        let z = arr[b + 2] + this._wind.z * this._windSpeed * 0.05 * dt * 60;
        const y = arr[b + 1] + Math.sin(this.t * 0.7 + i) * 0.0016;
        if (x - playerPos.x > 45) x -= 90; if (x - playerPos.x < -45) x += 90;
        if (z - playerPos.z > 45) z -= 90; if (z - playerPos.z < -45) z += 90;
        arr[b] = x; arr[b + 1] = y; arr[b + 2] = z;
      }
      this.motes.geometry.attributes.position.needsUpdate = true;
    }
  }
}
