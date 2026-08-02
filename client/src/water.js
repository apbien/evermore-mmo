/**
 * Water — the one implementation.
 *
 * Hearthmere is a lake town at a ford. The Mere, the Emberflow, the harbour,
 * the mill race, the fountain, the troughs and the tannery pits are all the
 * same substance, so they are all one material, one shader patch and one set
 * of authored numbers in `content/town/hearthmere.json → atmosphere.water`.
 * `client/src/main.js`, `tools/render/town.html` and `tools/render/viewer.html`
 * all import THIS module and hand it THAT block; none of them contains a line
 * of water code of its own. That is D-009 and it is why a review render and
 * the game cannot disagree about what the lake looks like.
 *
 * The mesh side is generated. `venues/terrain.py` builds the surface of the
 * Emberflow, the Mere and the harbour basin, tucks its outermost ring of
 * triangles under the bank so the waterline is the exact intersection of the
 * plane with the ground, and writes a depth tint and a depth TRANSMISSION into
 * COLOR_0. `core/kit.water_disc` does the same for the fountain basin and the
 * troughs. That gets shape, shoreline and looking-straight-down depth right.
 *
 * What geometry cannot do is the other four things, and they are what this
 * module is:
 *
 *  1. MOVE. A still normal map on a lake reads as ice. Two counter-scrolling
 *     samples of the same map for standing water (interference: crests form
 *     and die in place); one direction at two rates for a channel (a current
 *     you can see the direction of). Driven by the town's authored wind.
 *  2. FRESNEL. Water is not one opacity. Looking down into it you see the bed;
 *     looking along it you see the sky. COLOR_0's alpha is only the first half,
 *     and without the second the far side of a lake reads as translucent paint.
 *  3. DISTANCE ROUGHNESS. The far half of a lake is never sharper than the near
 *     half. Without this the ripple normal mips toward flat, every pixel out
 *     there answers the sun identically, and you get the hard white plate the
 *     art director measured across `t-approach-ne` for four passes.
 *  4. THE SPECULAR SHOULDER. See SPEC_CHUNK.
 *
 * The patches are defensive: if three's chunks are not where this expects them
 * (a version bump, a different material type), each one warns loudly and the
 * rest still install. A renderer feature that silently does nothing is the
 * failure mode D-023 is about.
 */

import * as THREE from 'three';

/** Defaults, used only when content does not author the key. Content is the
 *  authority; these exist so a venue harness with no town document still gets
 *  water that moves rather than water that is a sheet of green glass. */
const DEF = {
  specularKnee: 0.55,
  envIntensity: 0.62,
  fresnel: { f0: 0.02, power: 5.0, reflectOpacity: 1.0 },
  distanceRoughness: { gain: 0.34, start: 22.0, full: 140.0 },
  shallow: { colour: '#B9A57E', depth: 0.85, roughness: 0.34 },
  flow: {
    still: { a: [0.0140, -0.0065], b: [-0.0083, 0.0112], scaleB: 0.47 },
    river: { a: [0.0045, 0.0780], b: [-0.0031, 0.0506], scaleB: 0.47 },
  },
  wind: { drift: 0.0042, chop: 0.22, gust: 0.18 },
};

const num = (v, d) => (Number.isFinite(v) ? +v : d);

/** Which flow pair a material takes, by the name `core/gltf.py` wrote from the
 *  library key. `water_flow` is the channel and `water_fall` is a jet off a
 *  fountain rim or a weir lip — both are moving water with a direction, and
 *  both lay V down the direction of travel, so both take the river pair.
 *  Standing water is everything else. */
const isChannel = name => /flow|fall|race|weir/i.test(name || '');

/** A falling sheet is not a lake surface: it is thin, it overlaps itself, and
 *  it must not occlude the two ribbons behind it. Everything else is one
 *  closed sheet per body and has to write depth or the far bank draws over
 *  the near water. */
const isSheet = name => /fall|spray|froth/i.test(name || '');

/**
 * The moving normal.
 *
 * `hmFlow` carries both layers' UV offsets; `hmWave.x` is the wind-driven
 * amplitude gain, breathed at the authored gust rate by the updater so the
 * surface is not metronomic. `scaleB` is baked into the source because it is a
 * compile-time constant of the interference pattern, not a per-frame value.
 */
const FLOW_CHUNK = scaleB => /* glsl */`
#ifdef USE_NORMALMAP_TANGENTSPACE
  vec2 hmUvA = vNormalMapUv + hmFlow.xy;
  vec2 hmUvB = vNormalMapUv * ${scaleB.toFixed(4)} + hmFlow.zw;
  vec3 hmNa = texture2D( normalMap, hmUvA ).xyz * 2.0 - 1.0;
  vec3 hmNb = texture2D( normalMap, hmUvB ).xyz * 2.0 - 1.0;
  vec3 mapN = normalize( vec3( hmNa.xy + hmNb.xy, hmNa.z * hmNb.z ) );
  mapN.xy *= normalScale * hmWave.x;
  // tbn is built unconditionally by <normal_fragment_begin> whenever
  // USE_NORMALMAP_TANGENTSPACE is defined — with or without vertex tangents,
  // in which case it comes from getTangentFrame(). The first version of this
  // patch branched on USE_TANGENT and called perturbNormal2Arb() in the other
  // arm, which three removed; the fragment shader failed to compile and the
  // whole water material went black. Verified against the vendored r180.
  normal = normalize( tbn * mapN );
#endif
`;

/**
 * Roughness against view distance.
 *
 * Two defects, one cause. As the ripple normal map mips past ~30 m its average
 * tends to (0,0,1) — dead flat — so the whole far half of the lake answers the
 * sun with the same narrow GGX lobe and renders as one hard-edged white plate.
 * The same mip transition aliases as the camera moves. Raising the roughness
 * with distance is what the lost normal variance *was*: a wide lobe. It is
 * also, exactly, an LOD strategy for a normal map, which `ad-town-05` §5 asks
 * for by name on the masonry.
 */
const ROUGH_CHUNK = /* glsl */`
#include <roughnessmap_fragment>
roughnessFactor = clamp(
  roughnessFactor + hmRough.x *
    smoothstep( hmRough.y, hmRough.z, length( vViewPosition ) )
  // Shallow water is ROUGHER. A sheet thin enough to see the bed through it is
  // being broken continuously by that bed - it is a shoal, and a shoal is never
  // a mirror. Without this the whole waterline answers the sun with the same
  // narrow lobe the open lake does, and on any shore that faces the sun it
  // renders as a hard pale rim following the sheet's own cell boundary: the
  // white scalloped ring round the north-east of the Mere that ad-town-05
  // section 2 finds first in t-aerial-sw. diffuseColor.a is the depth
  // transmission and has been written by <color_fragment>, which three runs
  // before this chunk.
  //
  // NOTE: no backticks in here. This block is a JS template literal, and a
  // backtick inside the GLSL closes it - which is a whole-client syntax error,
  // not a shader bug, and it takes the page down before anything renders.
  + hmRough2 * ( 1.0 - smoothstep( 0.0, hmShallow.a, clamp( diffuseColor.a, 0.0, 1.0 ) ) ),
  0.0, 1.0 );
`;

/**
 * Depth colour and the Fresnel half of transmission.
 *
 * COLOR_0's alpha is the Beer-Lambert transmission of the water column under
 * each vertex — correct, and only correct looking straight down. Real water is
 * ~2 % reflective at normal incidence and a mirror at a grazing one, and the
 * crossover is the single most recognisable thing about the substance. Without
 * it a lake seen from the bank is uniformly semi-transparent, which reads as
 * coloured glass; with it the near margin shows its bed and the far reach
 * turns to sky, which is what every photograph of a lake looks like.
 *
 * The shallow tint rides the same alpha: where the sheet is thin it is warmed
 * toward silt, because a hand's depth of water over gravel is a sand colour,
 * not a lake colour. A margin at the same value as the middle is the loudest
 * tell of a stamped polygon and it is what `t-aerial-sw` has shown for four
 * passes.
 *
 * `hmEdge` kills the last centimetre outright: the sheet is built with a
 * feathered margin that oversails the bank (see `venues/terrain._water`), and
 * a grazing Fresnel would otherwise put a bright mirror on top of dry ground.
 */
const ALPHA_CHUNK = /* glsl */`
{
  float hmA = clamp( diffuseColor.a, 0.0, 1.0 );
  // Warm the thin water toward its own bed.
  float hmShoal = 1.0 - smoothstep( 0.0, hmShallow.a, hmA );
  diffuseColor.rgb = mix( diffuseColor.rgb, hmShallow.rgb, hmShoal * 0.85 );
  float hmNdV = clamp( dot( normalize( normal ), normalize( vViewPosition ) ), 0.0, 1.0 );
  float hmF = hmWater.x + ( 1.0 - hmWater.x ) * pow( 1.0 - hmNdV, hmWater.y );
  float hmEdge = smoothstep( 0.0, 0.10, hmA );
  diffuseColor.a = clamp( mix( hmA, hmWater.z * hmEdge, hmF ), 0.0, 1.0 );
}
#include <opaque_fragment>
`;

/**
 * The specular shoulder.
 *
 * `review/reports/ad-town-02.md` §8: "the Mere is a pure white specular blowout
 * across the entire north-east". `core/materials.water_surface` has already
 * been round the roughness loop twice over it and its own comment records why
 * that could not work — a GGX lobe conserves energy, so a rougher surface
 * spreads the SAME light over more pixels, and at floor 0.30 the blown region
 * grew from 40 % of the Mere to 85 % of it. The peak came down and the frame
 * got worse.
 *
 * The energy is the problem, not its distribution, and the only place to take
 * energy out without making the lake matte is the DIRECT specular term. This is
 * a Reinhard shoulder on that term alone. It lives here rather than in the
 * grade because by the time the grade sees it the pixel is already 1.0 and
 * there is nothing left to recover, and here rather than in the generator
 * because it is a response curve, not a material property.
 *
 * The knee is authored. It shipped at 1.05 through four art-director passes,
 * two of which asked for 0.55 by name — at 1.05 the shoulder only bites above
 * a term of 1.0, which is past the point the pixel has already clipped.
 */
const SPEC_CHUNK = knee => /* glsl */`
#include <lights_fragment_end>
{
  vec3 hmSpec = reflectedLight.directSpecular;
  reflectedLight.directSpecular = hmSpec / ( 1.0 + hmSpec * ${knee.toFixed(4)} );
}
`;

/** Authored hex is sRGB, like every other colour in content/; the shader wants
 *  it linear. `setStyle` with the colour space does both in one call. */
function linearColour(hex, fallback) {
  const c = new THREE.Color();
  try {
    c.setStyle(String(hex || fallback), THREE.SRGBColorSpace);
  } catch (e) {
    c.setStyle(String(fallback), THREE.SRGBColorSpace);
  }
  return c;
}

/** Wrap one water material so it flows, refracts and reflects.
 *  `opts` is the resolved `atmosphere.water` block; `wind` is `ambient.wind`.
 *  Returns a per-frame updater, or null if the material is already wrapped. */
export function makeFlowing(material, opts = {}, wind = null) {
  if (!material || material.userData.hmFlow) return null;

  const knee = num(opts.specularKnee, DEF.specularKnee);
  const fr = { ...DEF.fresnel, ...(opts.fresnel || {}) };
  const dr = { ...DEF.distanceRoughness, ...(opts.distanceRoughness || {}) };
  const sh = { ...DEF.shallow, ...(opts.shallow || {}) };
  const wd = { ...DEF.wind, ...(opts.wind || {}) };
  const flows = { ...DEF.flow, ...(opts.flow || {}) };
  const spec = isChannel(material.name) ? (flows.river || DEF.flow.river)
                                        : (flows.still || DEF.flow.still);
  const A = (spec.a || DEF.flow.still.a).slice();
  const B = (spec.b || DEF.flow.still.b).slice();
  const scaleB = num(spec.scaleB, 0.47);

  // The town's one wind vector. `ambient.wind` already drives the cloth and the
  // smoke; water that ignores it is a third motion system disagreeing with the
  // other two, which is exactly the kind of seam Art Bible §7 is about.
  // Standing water DRIFTS downwind; a channel does not care, its current wins.
  const wdir = (wind && Array.isArray(wind.direction)) ? wind.direction : [0, 0, 0];
  const wspeed = num(wind && wind.speed, 0);
  const gustHz = num(wind && wind.gustHz, 0.35);
  const wlen = Math.hypot(wdir[0] || 0, wdir[wdir.length - 1] || 0) || 1;
  if (!isChannel(material.name) && wspeed > 0) {
    // World +X and +Z map straight onto U and V: the lake's UVs are
    // world-planar (venues/terrain._water), so one vector does the job.
    const d = num(wd.drift, DEF.wind.drift) * wspeed;
    A[0] += (wdir[0] / wlen) * d;
    A[1] += (wdir[wdir.length - 1] / wlen) * d;
    B[0] += (wdir[0] / wlen) * d * 0.6;
    B[1] += (wdir[wdir.length - 1] / wlen) * d * 0.6;
  }
  const chop = 1.0 + num(wd.chop, DEF.wind.chop) * wspeed;
  const gust = num(wd.gust, DEF.wind.gust);

  const flow = { value: new THREE.Vector4(0, 0, 0, 0) };
  const wave = { value: new THREE.Vector2(chop, 0) };
  const water = { value: new THREE.Vector3(num(fr.f0, 0.02), num(fr.power, 5.0),
                                           num(fr.reflectOpacity, 1.0)) };
  const rough = { value: new THREE.Vector3(num(dr.gain, 0.34), num(dr.start, 22),
                                           num(dr.full, 140)) };
  const shal = linearColour(sh.colour, DEF.shallow.colour);
  const shallow = { value: new THREE.Vector4(shal.r, shal.g, shal.b,
                                             Math.max(1e-3, num(sh.depth, 0.85))) };
  const shoalRough = { value: num(sh.roughness, DEF.shallow.roughness) };

  if (Number.isFinite(opts.envIntensity)) material.envMapIntensity = opts.envIntensity;
  material.userData.hmFlow = flow;
  // Depth-tinted transmission arrives as COLOR_0 alpha from the generator
  // (`core.kit.water_alpha`), so the sheet fades out as it thins over the bed.
  // three's GLTFLoader gives a BLEND material `transparent`, but leaves
  // depthWrite on — correct here: the water is one closed sheet per body, so
  // it must occlude what is behind it, and turning depthWrite off would let
  // the far bank draw over the near water.
  if (material.transparent) material.depthWrite = !isSheet(material.name);

  // Scrolling only works on a repeating texture; the generated maps are
  // authored to tile, but the loader does not have to have set the wrap mode.
  //
  // ANISOTROPY is not a nicety here, it is the fix for a named defect. A lake
  // seen from 1.62 m is the most extreme grazing angle in the whole build —
  // the footprint of one pixel covers metres along the view direction and
  // centimetres across it — and isotropic mip selection has to pick the LONG
  // axis, so it either aliases the ripple into a regular diamond lattice or
  // blurs it to nothing. `t-approach-ne` shows the lattice as "visible
  // triangular polygon facet seams", which is what `ad-town-05` §2 calls it;
  // they are not seams and they are not polygons, they are the 2.5 m normal
  // tile beating against the mip. 16x is clamped by the renderer to whatever
  // the hardware has, so this is safe everywhere and free where it is not
  // supported.
  for (const t of [material.normalMap, material.map, material.roughnessMap]) {
    if (!t) continue;
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.anisotropy = 16;
    t.needsUpdate = true;
  }

  let patched = false;
  material.onBeforeCompile = shader => {
    shader.uniforms.hmFlow = flow;
    shader.uniforms.hmWave = wave;
    shader.uniforms.hmWater = water;
    shader.uniforms.hmRough = rough;
    shader.uniforms.hmShallow = shallow;
    shader.uniforms.hmRough2 = shoalRough;
    const before = shader.fragmentShader;
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <normal_pars_fragment>',
               '#include <normal_pars_fragment>\n' +
               'uniform vec4 hmFlow;\nuniform vec2 hmWave;\n' +
               'uniform vec3 hmWater;\nuniform vec3 hmRough;\nuniform vec4 hmShallow;\n' +
               'uniform float hmRough2;')
      .replace('#include <normal_fragment_maps>', FLOW_CHUNK(scaleB))
      .replace('#include <roughnessmap_fragment>', ROUGH_CHUNK)
      .replace('#include <opaque_fragment>', ALPHA_CHUNK)
      .replace('#include <lights_fragment_end>', SPEC_CHUNK(knee));
    patched = shader.fragmentShader !== before &&
              shader.fragmentShader.indexOf('hmFlow') >= 0 &&
              shader.fragmentShader.indexOf('hmNa') >= 0;
    if (!patched) {
      console.warn('water: three normal-map chunk not found; ' +
                   'falling back to single-layer offset scroll');
    }
    for (const [needle, why] of [
      ['hmSpec', 'the specular shoulder is NOT applied and the Mere will blow out'],
      ['hmNdV', 'the Fresnel transmission is NOT applied and the water will read as flat paint'],
      ['hmRough.x *', 'the distance roughness is NOT applied and the far water will be a white plate'],
      ['hmRough2', 'the shoal roughness is NOT applied and the waterline will read as a pale rim'],
    ]) {
      if (shader.fragmentShader.indexOf(needle) < 0) {
        console.warn(`water: patch '${needle}' did not install — ${why}`);
      }
    }
  };
  material.customProgramCacheKey = () =>
    `hm-water-${knee.toFixed(4)}-${scaleB.toFixed(3)}-${isChannel(material.name) ? 'r' : 's'}`;
  material.needsUpdate = true;

  return t => {
    flow.value.set(A[0] * t, A[1] * t, B[0] * t, B[1] * t);
    // Gusts. A lake surface is not metronomic; the same rate the cloth uses.
    wave.value.set(chop * (1.0 + gust * Math.sin(t * gustHz * Math.PI * 2.0)), t);
    if (!patched && material.normalMap) {
      material.normalMap.offset.set(A[0] * t, A[1] * t);
    }
  };
}

/**
 * Find every water material under `root` and make it flow.
 *
 * Materials are matched by NAME, which is what `core/gltf.py` writes from the
 * library key — so the mere, the harbour, the fountain basin, the mill race and
 * the horse trough are all one material and all animate together, which is also
 * why they are one draw call. `water_fall` is the falling sheet off a fountain
 * rim: same substance, different geometry, and it is matched too.
 */
const WATER_NAME = /(^|[^a-z])water($|[^a-z])/i;

export class Water {
  /** `opts` is `atmosphere.water` and `wind` is `ambient.wind`, both from
   *  content/town/hearthmere.json. Everything about how water looks is in
   *  those two blocks; nothing is in a harness. */
  constructor(opts = {}, wind = null) {
    this.updaters = [];
    this.materials = new Set();
    this.opts = opts || {};
    this.wind = wind || null;
    this.t = 0;
  }

  harvest(root) {
    root.traverse(o => {
      if (!o.isMesh && !o.isInstancedMesh) return;
      const mats = Array.isArray(o.material) ? o.material : [o.material];
      for (const m of mats) {
        if (!m || !WATER_NAME.test(m.name || '')) continue;
        if (this.materials.has(m)) continue;
        this.materials.add(m);
        const up = makeFlowing(m, this.opts, this.wind);
        if (up) this.updaters.push(up);
      }
    });
    return this.updaters.length;
  }

  /** Advance the flow. `dt` in seconds. */
  update(dt) {
    this.t += dt;
    for (const up of this.updaters) up(this.t);
  }

  /** Freeze at a fixed phase — for still renders, so review images are
   *  deterministic rather than whatever the frame happened to catch. */
  setTime(t) {
    this.t = t;
    for (const up of this.updaters) up(t);
  }
}
