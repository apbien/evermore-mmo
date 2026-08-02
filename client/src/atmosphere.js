/**
 * The shared environmental layer: aerial perspective, sky, horizon closure,
 * warm ambient occlusion and the colour grade.
 *
 * WHY THIS FILE EXISTS
 * --------------------
 * `review/reports/ad-town-02.md` answered the cohesion question with: "The
 * individual pieces are not the problem; the absence of any shared
 * environmental layer over the top of them is." Findings §5 (no fog anywhere),
 * §11/§13 (no ambient occlusion, nothing bedded into anything) and
 * `docs/ARCHITECTURE.md` §5 (a grade LUT that was specified and never built)
 * are three faces of one omission: every venue was lit, and the WORLD was not.
 *
 * There were three renderers — `tools/render/town.html`, `tools/render/viewer.html`
 * and `client/src/main.js` — each carrying its own copy of the sky dome and its
 * own post chain, and they had already drifted (only the venue viewer had any
 * AO at all, and it was neutral grey). Adding fog in three places would have
 * been a fourth copy of the same divergence CLAUDE.md's "extend the core, never
 * fork it" rule exists to prevent, so this module IS the core for the
 * presentation layer and all three import it.
 *
 * Every number comes from `content/town/hearthmere.json` → `atmosphere`, the
 * same way the 09:30 rig comes from `lighting` (D-009). Nothing here is
 * hardcoded except the fallbacks, which exist so a viewer opened against an old
 * town file still draws something rather than throwing.
 *
 * WHAT IT DOES, IN THE ORDER `docs/ARCHITECTURE.md` §5 specifies
 * --------------------------------------------------------------
 *   sky + IBL  →  height/distance scattering  →  SSAO(GTAO, warm)
 *              →  bloom  →  ACES  →  grade  →  vignette
 *
 * The scattering is not `THREE.FogExp2`. Uniform-density exponential fog is
 * one colour at every height, so a town that falls 4 m to a river and a
 * distance ring 300 m out get the same haze and the frame flattens a second
 * time in a different way. What is installed instead is an analytic
 * height-integrated exponential with two colours — warm near, cool far, per
 * Art Bible §1's "colour separation between planes … pushed apart in value and
 * temperature" — plus a forward-scattering term toward the sun. It is patched
 * into `THREE.ShaderChunk` rather than added per material, so it reaches every
 * material in the town including ones no code here has ever seen.
 */

import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { GTAOPass } from 'three/addons/postprocessing/GTAOPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';

// ---------------------------------------------------------------------------
// Defaults
// ---------------------------------------------------------------------------
//
// These are the values `content/town/hearthmere.json` carries. They are
// repeated here ONLY as a fallback for a viewer pointed at a town document that
// predates the block — an atmosphere that silently does nothing is the failure
// mode D-023 is about, and a renderer that throws on an old file is no better.
// The content file is the authority; if the two ever disagree, the content file
// is right and this table is stale.
export const ATMOSPHERE_DEFAULTS = {
  scattering: {
    nearColor: '#E4D3B0', farColor: '#8FB2DE',
    density: 0.0038, heightFalloff: 30.0, baseY: -4.0,
    maxOpacity: 0.78, startDistance: 12.0, fullDistance: 82.0,
    sunColor: '#FFE7C0', sunAmount: 0.34, sunPower: 5.0,
  },
  sky: {
    top: '#4E8FD6', mid: '#A8CDEC', horizon: '#D7E2EA', ground: '#B6AE96',
    horizonPower: 3.4, horizonWidth: 0.17,
    sunColor: '#FFF8E6', sunAngularSize: 1.6, sunGlow: 0.40, sunGlowPower: 22.0,
    cloudAmount: 0.34, cloudScale: 0.016, cloudColor: '#FFFCF4', cloudShade: '#B9C6D4',
  },
  horizon: {
    innerHalfExtent: 288.0, outerRadius: 1200.0,
    innerDrop: 0.35, outerDrop: 26.0, color: '#93A07C', segments: 160,
  },
  ao: {
    tint: '#4A3828', tintStrength: 0.65, intensity: 0.80,
    radius: 2.4, distanceExponent: 1.0, thickness: 2.0, scale: 1.6,
    samples: 16, screenSpaceRadius: false, farDistance: 80.0,
    denoiseRadius: 10, lumaPhi: 8.0,
  },
  bloom: { strength: 0.26, radius: 0.55, threshold: 1.0 },
  grade: {
    lift: 0.038, shadowTint: '#7FB2C8', shadowAmount: 0.14,
    midTint: '#FFD7A2', midAmount: 0.14,
    highlightRolloff: 0.14, contrast: 1.05, saturation: 1.12,
    vignette: 0.16, vignetteSoftness: 0.62,
  },
  water: { specularKnee: 1.05, envIntensity: 0.72 },
};

/** Deep-merge the authored block over the fallbacks. One level of nesting is
 *  all the block has and all it should ever have — a renderer setting that
 *  needs a tree is a renderer setting that needs a name. */
export function readAtmosphere(town) {
  const src = (town && town.atmosphere) || {};
  const out = {};
  for (const k of Object.keys(ATMOSPHERE_DEFAULTS)) {
    out[k] = Object.assign({}, ATMOSPHERE_DEFAULTS[k], src[k] || {});
  }
  out.__authored = !!(town && town.atmosphere);
  return out;
}

// ---------------------------------------------------------------------------
// Colour helpers
// ---------------------------------------------------------------------------

/** sRGB hex → the renderer's WORKING colour space (linear-sRGB, because
 *  `THREE.ColorManagement` is on by default in r152+).
 *
 *  This matters and it is easy to get wrong. Everything the scattering chunk
 *  does happens BEFORE tone mapping, i.e. in linear light, while everything the
 *  grade does happens after `OutputPass` has encoded to sRGB. Feeding an sRGB
 *  literal to the linear half washes the haze out by roughly a stop and a half
 *  and is exactly what makes fog look like milk. */
const lin = hex => { const c = new THREE.Color(hex); return [c.r, c.g, c.b]; };
const f = n => (Number.isFinite(n) ? n : 0).toFixed(6);
const v3 = hex => { const c = lin(hex); return `vec3(${f(c[0])},${f(c[1])},${f(c[2])})`; };
/** For passes that run AFTER OutputPass the buffer is display-referred, so the
 *  literal must stay in sRGB rather than being linearised. */
const v3srgb = hex => {
  const c = new THREE.Color(); c.setStyle(hex, THREE.SRGBColorSpace);
  const s = c.convertLinearToSRGB();
  return `vec3(${f(s.r)},${f(s.g)},${f(s.b)})`;
};

/** World-space unit vector pointing AT the sun, from the locked rig.
 *  Identical to the expression `aimSun()` in `tools/render/town.html` and the
 *  per-frame sun placement in `client/src/main.js` — if it ever stops being
 *  identical the in-scatter will glow on the wrong side of the sky. */
export function sunDirection(lighting) {
  const el = (lighting?.sunElevationDeg ?? 38) * Math.PI / 180;
  const az = (lighting?.sunAzimuthDeg ?? 125) * Math.PI / 180;
  return new THREE.Vector3(Math.cos(el) * Math.sin(az), Math.sin(el), Math.cos(el) * Math.cos(az));
}

// ---------------------------------------------------------------------------
// 1. Atmospheric perspective
// ---------------------------------------------------------------------------

let _fogInstalled = null;

/**
 * Replace three's fog chunks with height-integrated, two-colour scattering.
 *
 * The four chunks are overwritten globally rather than per material. That is
 * deliberate: `scene.fog` only decides WHETHER a material fogs, and every
 * standard material in the town already respects it, so patching the chunk
 * reaches the 36 venues, the terrain plate, the instanced clutter and the
 * horizon ring without any of them being enumerated here. A per-material
 * `onBeforeCompile` would have to be re-applied at every load and would miss
 * whatever the next venue introduces.
 *
 * Constants are baked into the source as literals rather than plumbed as
 * uniforms. `THREE.UniformsLib.fog` is deep-CLONED into every material at
 * construction, so a shared uniform object does not stay shared and the
 * alternative is walking every material in the scene on every change. The
 * atmosphere is authored in content and fixed for the life of the page, so a
 * literal is both simpler and one less thing that can silently be zero.
 * `fogColor` and `fogDensity` DO stay uniforms — they are the far colour and
 * the base density — so `scene.fog` remains a live handle worth poking in a
 * console.
 */
export function installScattering(scene, atmos, lighting) {
  const s = atmos.scattering;
  const d = sunDirection(lighting);

  THREE.ShaderChunk.fog_pars_vertex = /* glsl */`
#ifdef USE_FOG
  varying float vFogDepth;
  varying vec3 vFogWorld;
#endif`;

  // World position is recovered from the view-space one rather than from
  // `worldPosition`, which only exists under USE_ENVMAP / USE_SHADOWMAP and so
  // cannot be relied on here. For a rigid view matrix
  // `world = cameraPosition + transpose(R) * view`, and in GLSL `v * M` IS
  // `transpose(M) * v`, so this costs one mat3 multiply and no inverse.
  THREE.ShaderChunk.fog_vertex = /* glsl */`
#ifdef USE_FOG
  vFogDepth = - mvPosition.z;
  vFogWorld = cameraPosition + mvPosition.xyz * mat3( viewMatrix );
#endif`;

  THREE.ShaderChunk.fog_pars_fragment = /* glsl */`
#ifdef USE_FOG
  uniform vec3 fogColor;
  varying float vFogDepth;
  varying vec3 vFogWorld;
  #ifdef FOG_EXP2
    uniform float fogDensity;
  #else
    uniform float fogNear;
    uniform float fogFar;
  #endif
#endif`;

  THREE.ShaderChunk.fog_fragment = /* glsl */`
#ifdef USE_FOG
{
  // --- Hearthmere aerial perspective ------------------------------------
  // Density falls off exponentially with height, so the integral along the
  // view ray has a closed form. Without the height term a 4 m fall to the
  // river and a ridge 300 m out haze identically and the frame flattens in a
  // new way; with it, the water meadow sits in haze and the church tower
  // stands clear of it, which is the whole point.
  const float HM_H     = ${f(s.heightFalloff)};
  const float HM_Y0    = ${f(s.baseY)};
  const float HM_MAX   = ${f(s.maxOpacity)};
  const float HM_START = ${f(s.startDistance)};
  const float HM_FULL  = ${f(s.fullDistance)};
  const vec3  HM_NEAR  = ${v3(s.nearColor)};
  const vec3  HM_SUNC  = ${v3(s.sunColor)};
  const vec3  HM_SUND  = vec3(${f(d.x)},${f(d.y)},${f(d.z)});
  const float HM_SUNA  = ${f(s.sunAmount)};
  const float HM_SUNP  = ${f(s.sunPower)};

  float hmDist = max( vFogDepth - HM_START, 0.0 );

  float hmYa = ( cameraPosition.y - HM_Y0 ) / HM_H;
  float hmYb = ( vFogWorld.y      - HM_Y0 ) / HM_H;
  float hmEa = exp( - clamp( hmYa, -6.0, 24.0 ) );
  float hmEb = exp( - clamp( hmYb, -6.0, 24.0 ) );
  float hmDy = hmYb - hmYa;
  // The limit of (e^-a - e^-b)/(b - a) as b -> a is e^-a. Taking the branch at
  // 1e-3 rather than 0 keeps a horizontal ray — every eye-height street frame
  // in the build — off the wrong side of a divide by nearly nothing.
  float hmInt = abs( hmDy ) < 1e-3 ? hmEa : ( hmEa - hmEb ) / hmDy;

  float hmFactor = ( 1.0 - exp( - fogDensity * hmDist * max( hmInt, 0.0 ) ) ) * HM_MAX;

  // Warm foreground, cool distance. Two colours rather than one is what buys
  // the temperature separation Art Bible §1 asks for; one colour only buys
  // value separation and the frame still reads as a single plane tinted.
  float hmT = clamp( ( vFogDepth - HM_START ) / max( HM_FULL - HM_START, 1.0 ), 0.0, 1.0 );
  hmT = hmT * hmT * ( 3.0 - 2.0 * hmT );
  vec3 hmCol = mix( HM_NEAR, fogColor, hmT );

  // Forward scatter. Looking toward the sun the haze is bright and warm;
  // looking away it stays cool. Without this the fog is a flat wash and reads
  // as a filter over the lens rather than as air with light in it.
  vec3 hmView = normalize( vFogWorld - cameraPosition );
  float hmSun = pow( max( dot( hmView, HM_SUND ), 0.0 ), HM_SUNP );
  hmCol = mix( hmCol, HM_SUNC, hmSun * HM_SUNA );

  gl_FragColor.rgb = mix( gl_FragColor.rgb, hmCol, hmFactor );
}
#endif`;

  // FogExp2 is what defines FOG_EXP2 and supplies `fogDensity`; the curve above
  // then ignores three's own factor entirely. Keeping the object means
  // `scene.fog.density` and `scene.fog.color` still steer the real thing.
  scene.fog = new THREE.FogExp2(new THREE.Color(s.farColor), s.density);

  // Materials compiled before the chunks changed hold the old program.
  // Nothing has loaded this early in practice, but a viewer that installs the
  // atmosphere after its ground is on screen would otherwise show one unfogged
  // venue and no clue why.
  if (_fogInstalled) {
    scene.traverse(o => {
      const mats = o.material ? (Array.isArray(o.material) ? o.material : [o.material]) : [];
      for (const m of mats) if (m) m.needsUpdate = true;
    });
  }
  _fogInstalled = s;
  return scene.fog;
}

// ---------------------------------------------------------------------------
// 2. Sky
// ---------------------------------------------------------------------------

/**
 * The sky dome, which is also the IBL source.
 *
 * What it replaces was a two-stop vertical gradient: no horizon ramp, no sun,
 * no cloud (§5). Three things are added and each of them is doing a job in the
 * frame rather than decorating it —
 *
 *   horizon ramp — the pale band the distance ring and the horizon skirt
 *                  dissolve into. Without it the far fog colour and the sky
 *                  meet at a visible line and the closure of §6 fails no
 *                  matter how good the geometry is.
 *   sun disc     — one bright anchor, and the thing the scattering's forward
 *                  lobe is pointing at. A haze that brightens toward a sun
 *                  that is not drawn reads as a lens flare.
 *   cloud        — value-noise cirrus on a planar projection, faded out at the
 *                  horizon where the projection degenerates. Low contrast on
 *                  purpose: this is a 09:30 summer sky in a starting town, not
 *                  weather.
 */
export function makeSky(atmos, lighting) {
  const k = atmos.sky;
  const d = sunDirection(lighting);
  // Unit sphere, scaled and re-centred on whatever camera is about to render
  // it. A fixed radius cannot work: this module is shared, and the three
  // renderers run far planes of 500, 1000 and 2000 m — the first version put a
  // 3000 m dome in front of a 2000 m far plane and the arrival frame rendered
  // the sky as a black hole, which is the whole reason the dome now follows the
  // lens instead of standing in the world.
  const geo = new THREE.SphereGeometry(1, 48, 24);
  const mat = new THREE.ShaderMaterial({
    side: THREE.BackSide, depthWrite: false, depthTest: false, fog: false,
    vertexShader: /* glsl */`
      varying vec3 vDir;
      void main() {
        vDir = position;
        gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );
      }`,
    fragmentShader: /* glsl */`
      varying vec3 vDir;

      float hmHash( vec2 p ) {
        return fract( sin( dot( p, vec2( 127.1, 311.7 ) ) ) * 43758.5453123 );
      }
      float hmNoise( vec2 p ) {
        vec2 i = floor( p ), fr = fract( p );
        vec2 u = fr * fr * ( 3.0 - 2.0 * fr );
        return mix( mix( hmHash( i ), hmHash( i + vec2( 1.0, 0.0 ) ), u.x ),
                    mix( hmHash( i + vec2( 0.0, 1.0 ) ), hmHash( i + vec2( 1.0, 1.0 ) ), u.x ), u.y );
      }
      float hmFbm( vec2 p ) {
        float a = 0.5, s = 0.0;
        for ( int i = 0; i < 4; i ++ ) { s += a * hmNoise( p ); p *= 2.07; a *= 0.5; }
        return s;
      }

      void main() {
        vec3 dir = normalize( vDir );
        float h = dir.y;

        vec3 c = h > 0.0 ? mix( ${v3(k.mid)}, ${v3(k.top)}, pow( h, 0.62 ) )
                         : mix( ${v3(k.mid)}, ${v3(k.ground)}, pow( -h, 0.5 ) );

        // Horizon value ramp — the band everything distant dissolves into.
        float band = pow( max( 1.0 - abs( h ) / max( ${f(k.horizonWidth)}, 0.001 ), 0.0 ), ${f(k.horizonPower)} );
        c = mix( c, ${v3(k.horizon)}, clamp( band, 0.0, 1.0 ) );

        // Cirrus on a planar projection, faded where the projection blows up.
        float deck = smoothstep( 0.02, 0.34, h );
        vec2 cp = dir.xz / max( h, 0.05 ) * ${f(k.cloudScale)};
        float n = hmFbm( cp * 3.0 + vec2( 11.3, 4.7 ) );
        float cl = smoothstep( 0.52, 0.86, n ) * deck * ${f(k.cloudAmount)};
        float lit = smoothstep( -0.1, 0.6, dot( dir, vec3(${f(d.x)},${f(d.y)},${f(d.z)}) ) );
        c = mix( c, mix( ${v3(k.cloudShade)}, ${v3(k.cloudColor)}, lit ), cl );

        // Sun: a soft glow with a small hard core inside it.
        float cd = dot( dir, vec3(${f(d.x)},${f(d.y)},${f(d.z)}) );
        float glow = pow( max( cd, 0.0 ), ${f(k.sunGlowPower)} ) * ${f(k.sunGlow)};
        float disc = smoothstep( cos( radians( ${f(k.sunAngularSize)} ) * 1.25 ),
                                 cos( radians( ${f(k.sunAngularSize)} ) ), cd );
        c = mix( c, ${v3(k.sunColor)}, clamp( glow + disc, 0.0, 1.0 ) );

        gl_FragColor = vec4( c, 1.0 );
      }`,
  });
  const mesh = new THREE.Mesh(geo, mat);
  mesh.frustumCulled = false;
  mesh.renderOrder = -1000;
  mesh.userData.helper = true;   // the review harness excludes helpers from measurement
  mesh.userData.hmSky = true;
  // `onBeforeRender` runs before three composes `modelViewMatrix`, so writing
  // the transform here is picked up by the very draw it is preparing for.
  mesh.onBeforeRender = (renderer, scene, cam) => {
    const far = cam.far || 2000;
    let r = far * 0.45;
    if (cam.isOrthographicCamera) {
      r = Math.max(r, Math.hypot(cam.right - cam.left, cam.top - cam.bottom));
    }
    mesh.scale.setScalar(r);
    mesh.position.copy(cam.position);
    mesh.updateMatrixWorld(true);
  };
  return mesh;
}

/** PMREM environment from the same dome, so IBL and the drawn sky agree. */
export function makeEnvironment(renderer, skyMesh) {
  const pmrem = new THREE.PMREMGenerator(renderer);
  const envScene = new THREE.Scene();
  const probe = new THREE.Mesh(new THREE.SphereGeometry(500, 48, 24), skyMesh.material.clone());
  probe.material.side = THREE.BackSide;
  probe.material.depthTest = true;
  envScene.add(probe);
  const tex = pmrem.fromScene(envScene, 0.04).texture;
  probe.geometry.dispose();
  return tex;
}

// ---------------------------------------------------------------------------
// 3. Horizon closure
// ---------------------------------------------------------------------------

/**
 * The skirt that closes the world edge.
 *
 * `content/town/terrain.json` generates a SQUARE plate of Chebyshev half-extent
 * 288 m and then stops — "beyond `far` there is nothing; the sky dome closes
 * the frame", which is true from directly overhead and false from every camera
 * a player has. At 1.62 m the plate edge is on the horizon line, so the ground
 * ends in mid-air with sky under it (§6).
 *
 * The skirt is a square annulus, not a disc, because the plate is square: its
 * inner edge is stitched to the plate boundary itself — sampled off the same
 * height field wherever one is supplied — so there is no step to see. It falls
 * away outward to `outerDrop` at `outerRadius`, which puts its far edge below
 * the eye from anywhere in the town and makes the last visible thing a horizon
 * rather than a rim.
 *
 * It is not trying to be scenery. By `outerRadius` the scattering has taken it
 * to the far fog colour, which is the same colour the sky's horizon band is, so
 * what the eye gets is land dissolving into air.
 */
export function makeHorizonRing(atmos, heightAt = null) {
  const h = atmos.horizon;
  const N = Math.max(32, h.segments | 0);
  const half = h.innerHalfExtent;
  const pos = [], idx = [], nrm = [];

  // Walk the square boundary once, then push each point out along its own
  // radial direction. Parameterised by perimeter so the inner ring lands
  // exactly on the plate edge on all four sides.
  const boundary = t => {
    const u = ((t % 1) + 1) % 1, s = u * 4;
    if (s < 1) return [-half + 2 * half * s, -half];
    if (s < 2) return [half, -half + 2 * half * (s - 1)];
    if (s < 3) return [half - 2 * half * (s - 2), half];
    return [-half, half - 2 * half * (s - 3)];
  };

  for (let i = 0; i <= N; i++) {
    const [x, z] = boundary(i / N);
    const r = Math.hypot(x, z) || 1;
    const gy = heightAt ? heightAt(x, z) : 0;
    // Inner ring sits just under the plate so a millimetre of numeric
    // disagreement shows as the plate winning, never as a gap.
    pos.push(x, gy - h.innerDrop, z);
    const ox = x / r * h.outerRadius, oz = z / r * h.outerRadius;
    pos.push(ox, gy - h.outerDrop, oz);
    nrm.push(0, 1, 0, 0, 1, 0);
  }
  for (let i = 0; i < N; i++) {
    const a = i * 2, b = a + 1, c = a + 2, d = a + 3;
    idx.push(a, c, b, b, c, d);
  }

  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  geo.setAttribute('normal', new THREE.Float32BufferAttribute(nrm, 3));
  geo.setIndex(idx);

  const mat = new THREE.MeshStandardMaterial({
    color: new THREE.Color(h.color), roughness: 1.0, metalness: 0.0,
    side: THREE.DoubleSide, fog: true,
  });
  const mesh = new THREE.Mesh(geo, mat);
  mesh.castShadow = false;
  mesh.receiveShadow = false;
  mesh.frustumCulled = false;
  mesh.name = 'hm.horizon';
  mesh.userData.helper = true;
  mesh.userData.landscape = true;    // it is ground, not a mass (town.html §LANDSCAPE)
  mesh.userData.hmHorizon = true;
  mesh.renderOrder = -900;
  return mesh;
}

// ---------------------------------------------------------------------------
// 4. Warm ambient occlusion
// ---------------------------------------------------------------------------

/**
 * GTAO, tinted.
 *
 * Art Bible §1: "Ambient occlusion is warm, not grey. Contact shadows tint
 * toward #4A3828, never neutral black." three's `GTAOPass` multiplies the beam
 * by a GREY occlusion factor, which crushes the shadow toward black and is
 * precisely the "muddy PBR" the style table forbids — so its blend shader is
 * replaced with one that multiplies toward the authored tint instead. Full
 * occlusion therefore lands on warm brown, not on nothing.
 */
export function makeAO(scene, camera, width, height, atmos) {
  const a = atmos.ao;
  const pass = new GTAOPass(scene, camera, width, height);
  pass.updateGtaoMaterial({
    radius: a.radius,
    distanceExponent: a.distanceExponent,
    thickness: a.thickness,
    scale: a.scale,
    samples: a.samples,
    screenSpaceRadius: !!a.screenSpaceRadius,
  });
  pass.updatePdMaterial({ lumaPhi: a.lumaPhi, radius: a.denoiseRadius });
  pass.blendIntensity = a.intensity;

  // The tint is a HUE, not a level.
  //
  // The obvious implementation — multiply the beauty buffer by #4A3828 where
  // the pixel is occluded — is wrong twice over, and the second way is not
  // obvious at all. `THREE.Color` puts a hex through to the working colour
  // space, so #4A3828 arrives as LINEAR (0.068, 0.038, 0.023): multiplying by
  // it does not tint a shadow warm, it removes 95 % of the light and leaves a
  // hole. And the pass runs before `OutputPass`, so the buffer it multiplies is
  // linear HDR, where an sRGB literal means nothing at all.
  //
  // What Art Bible §1 is asking for is that occlusion take BLUE out faster than
  // it takes red — the crease goes warm as it goes dark, the way a real one
  // does when the only light reaching it has bounced off warm ground. So the
  // tint is normalised to unit luminance, which leaves a pure ratio
  // (~1.57 : 0.88 : 0.53), tempered toward neutral by `tintStrength`, and how
  // DARK the crease goes is `intensity`'s job alone.
  const t = new THREE.Color(a.tint);
  const luma = Math.max(1e-4, 0.2126 * t.r + 0.7152 * t.g + 0.0722 * t.b);
  const s = Number.isFinite(a.tintStrength) ? a.tintStrength : 0.65;
  const hue = new THREE.Color(
    1 + (t.r / luma - 1) * s, 1 + (t.g / luma - 1) * s, 1 + (t.b / luma - 1) * s);

  pass.blendMaterial.uniforms.tint = { value: hue };
  pass.blendMaterial.fragmentShader = /* glsl */`
    uniform float intensity;
    uniform vec3 tint;
    uniform sampler2D tDiffuse;
    varying vec2 vUv;
    void main() {
      // The pass composites with blendSrc = DstColor: this fragment IS the
      // multiplier on the beauty buffer. White leaves the pixel alone.
      float ao = clamp( texture2D( tDiffuse, vUv ).r, 0.0, 1.0 );
      float occ = ( 1.0 - ao ) * intensity;
      gl_FragColor = vec4( mix( vec3( 1.0 ), tint * ( 1.0 - occ ), occ ), 1.0 );
    }`;
  pass.blendMaterial.needsUpdate = true;
  return pass;
}

// ---------------------------------------------------------------------------
// 5. The grade
// ---------------------------------------------------------------------------

/**
 * `docs/ARCHITECTURE.md` §5: "The grade LUT is where the anime look is
 * finalized: lifted shadows, warm midtones, slight cyan push in the shadows for
 * complementary contrast." It had never been built.
 *
 * A sampled 3D LUT would be the shippable form and it is what the Unreal/Unity
 * port will take, but the transform has to exist before it can be baked, and a
 * closed form is the thing you can actually tune against a render. This is that
 * transform, and `docs/ENGINE_PORTING.md`'s LUT can be baked straight off it.
 *
 * It runs AFTER `OutputPass`, i.e. on display-referred sRGB, which is where a
 * LUT belongs — lifting a shadow in linear light lifts it by a factor of forty
 * in the darks and reads as fog on the lens rather than as a print.
 */
export function makeGrade(atmos, width, height) {
  const g = atmos.grade;

  // The shadow tint as a DIRECTION, not a colour to multiply by.
  //
  // What was here multiplied the shadow region by `shadowTint * 1.28` and
  // mixed that in at `shadowAmount`. Read as code it is exactly what
  // `docs/ARCHITECTURE.md` §5 asks for. Measured, it is inert: a multiplicative
  // tint changes a pixel by a fraction OF THAT PIXEL, and the pixels in
  // question are dark, so the whole move lands inside the quantiser. Evaluated
  // on a neutral ramp with the shipped numbers, the darkest step moved by
  // **+1.5 blue-minus-red out of 255** and the shadow lift by +1.0. §5's "cyan
  // push in the shadows for complementary contrast" was not happening; it was
  // being computed and rounded away.
  //
  // A lift is an OFFSET, so its colour has to be an offset too. The tint is
  // normalised to unit luminance — which leaves a pure hue ratio and no
  // brightness in it — and `shadowAmount` scales how far along that direction
  // the lift leans. The luminance of the lift stays `lift`; only its hue is
  // steered. Same two authored numbers, one of them finally doing something.
  const st = new THREE.Color(); st.setStyle(g.shadowTint, THREE.SRGBColorSpace);
  const stl = st.clone().convertLinearToSRGB();     // this pass is post-OutputPass
  const lum = Math.max(1e-4, 0.2126 * stl.r + 0.7152 * stl.g + 0.0722 * stl.b);
  const dir = [stl.r / lum - 1, stl.g / lum - 1, stl.b / lum - 1];
  const amt = Number.isFinite(g.shadowAmount) ? g.shadowAmount : 0.2;
  // `dir` has zero luminance by construction, so the lift's LUMINANCE is
  // exactly `lift` whatever `shadowAmount` is — the tint steers the hue and
  // never the level. Floored at zero because a negative channel is not a tint,
  // it is a crushed black, and Art Bible §1 forbids those outright: driving
  // `shadowAmount` past `lift / 0.247` would start taking red OUT of the
  // shadows rather than putting cyan in.
  const liftV = `vec3(${[0, 1, 2].map(i => f(Math.max(0, g.lift + amt * dir[i]))).join(',')})`;

  const shader = {
    uniforms: {
      tDiffuse: { value: null },
      resolution: { value: new THREE.Vector2(width, height) },
    },
    vertexShader: /* glsl */`
      varying vec2 vUv;
      void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 ); }`,
    fragmentShader: /* glsl */`
      uniform sampler2D tDiffuse;
      varying vec2 vUv;
      void main() {
        vec3 c = texture2D( tDiffuse, vUv ).rgb;
        float l = dot( c, vec3( 0.2126, 0.7152, 0.0722 ) );

        // 1 + 2. A COLOURED lift — Art Bible §1's "never crushed" and
        //    ARCHITECTURE §5's "cyan push in the shadows", which are one move
        //    and not two. The offset's luminance is the authored lift; its hue
        //    leans shadowAmount of the way toward shadowTint, so the shadow
        //    floor comes up AND goes cool at the same time. Doing this as a
        //    lift plus a separate multiply put the whole colour move inside
        //    the quantiser — see the note where the lift vector is built.
        float sh = pow( clamp( 1.0 - l * 1.7, 0.0, 1.0 ), 1.6 );
        c = c + ${liftV} * sh;

        // Warmth into the mids. Multiplicative is right HERE: a midtone is
        // bright enough that a percentage of it is a visible number, and a
        // multiply keeps the warmth proportional to what is lit rather than
        // laying a wash over the whole band.
        float md = 1.0 - abs( l - 0.46 ) * 2.6;
        md = clamp( md, 0.0, 1.0 );
        c = mix( c, c * ${v3srgb(g.midTint)} * 1.06, md * ${f(g.midAmount)} );

        // 3. Highlight rolloff. The Mere's sun glitter arrives here already at
        //    or over 1.0; a soft shoulder keeps the top of the ramp from
        //    reading as a hole punched in the frame (§8).
        c = c / ( 1.0 + ${f(g.highlightRolloff)} * max( c - 1.0 + ${f(g.highlightRolloff)}, 0.0 ) );

        // 4. Contrast about the print pivot, then saturation.
        c = ( c - 0.435 ) * ${f(g.contrast)} + 0.435;
        float lg = dot( c, vec3( 0.2126, 0.7152, 0.0722 ) );
        c = mix( vec3( lg ), c, ${f(g.saturation)} );

        // 5. Vignette last, per the §5 order.
        vec2 p = ( vUv - 0.5 ) * vec2( 1.0, 0.62 );
        float v = 1.0 - ${f(g.vignette)} * smoothstep( ${f(g.vignetteSoftness)} * 0.5, 0.78, length( p ) * 1.62 );
        c *= v;

        gl_FragColor = vec4( clamp( c, 0.0, 1.0 ), 1.0 );
      }`,
  };
  return new ShaderPass(shader);
}

// ---------------------------------------------------------------------------
// 6. The whole chain
// ---------------------------------------------------------------------------

/**
 * Assemble the post chain in the `docs/ARCHITECTURE.md` §5 order:
 * `SSAO → bloom → tonemap (ACES) → colour grade → vignette`.
 *
 * `OutputPass` is the tonemap step — `RenderPass` renders to a float target, so
 * `renderer.toneMapping` is not applied in-material and ACES happens exactly
 * once, there. The grade sits after it because a grade is a print, not a light.
 *
 * Returns a handle rather than nothing because `tools/render/town.html` swaps
 * between a perspective and two orthographic cameras between shots, and an AO
 * pass still holding the previous camera renders the depth of a view nobody is
 * looking at.
 */
export function makePostChain({ renderer, scene, camera, width, height, atmos, ao = true }) {
  const composer = new EffectComposer(renderer);
  const renderPass = new RenderPass(scene, camera);
  composer.addPass(renderPass);

  const gtao = ao ? makeAO(scene, camera, width, height, atmos) : null;
  if (gtao) composer.addPass(gtao);

  /* AO gets its own camera, clipped short. This is not a cheat, it is the
   * measurement.
   *
   * `GTAOPass` renders its own full normal+depth G-buffer before it can shade
   * anything, which is a second complete scene pass. Measured on the real
   * client by `tools/check_client.mjs` that is several hundred draws a frame,
   * against BUILD_DIRECTIVE §7's budget of 900 for the whole thing.
   *
   * But the AO radius is 2.4 m, and at 80 m that subtends about two pixels in a
   * 55° frame at 1080p. Past that it cannot be seen at all, so every batch the
   * G-buffer draws beyond it is work that changes no pixel. Clipping the AO
   * camera's far plane lets three's own frustum cull drop them for free, and
   * the pixels it drops read as depth 1.0, which `GTAOShader` already discards.
   * It ports cleanly too: this is what an engine's AO distance setting is.
   *
   * TRIED AND REJECTED, recorded so the next agent does not spend the
   * afternoon on it: `gtao.setGBuffer(depthTexture)` makes the pass reuse a
   * depth buffer the beauty pass already filled and skip the G-buffer render
   * entirely, which would be the real fix. Attaching a `DepthTexture` to
   * `EffectComposer`'s two ping-ponged targets after construction — with
   * `dispose()` to force the framebuffer to be rebuilt, and re-supplying the
   * current one each frame — produced a uniformly white AO term in the
   * vendored r180, i.e. no occlusion at all. It needs the composer's targets to
   * be built with depth textures from the start, which means owning the
   * composer rather than configuring it. */
  const aoCam = gtao ? new THREE.PerspectiveCamera() : null;
  function syncAO(cam) {
    if (!gtao) return;
    // GTAO bakes PERSPECTIVE_CAMERA into its shader at construction, so an
    // orthographic camera reconstructs view positions with the wrong
    // projection and returns noise rather than occlusion.
    if (!cam.isPerspectiveCamera) { gtao.enabled = false; return; }
    aoCam.fov = cam.fov; aoCam.aspect = cam.aspect; aoCam.near = cam.near;
    aoCam.far = Math.min(cam.far, atmos.ao.farDistance || 80);
    aoCam.position.copy(cam.position);
    aoCam.quaternion.copy(cam.quaternion);
    aoCam.updateProjectionMatrix();
    aoCam.updateMatrixWorld(true);
    gtao.camera = aoCam;
  }
  syncAO(camera);

  const bloom = new UnrealBloomPass(new THREE.Vector2(width, height),
                                    atmos.bloom.strength, atmos.bloom.radius, atmos.bloom.threshold);
  composer.addPass(bloom);
  composer.addPass(new OutputPass());
  const grade = makeGrade(atmos, width, height);
  composer.addPass(grade);

  let aoWanted = !!gtao;

  return {
    composer, renderPass, gtao, bloom, grade,
    /** Point every camera-aware pass at the camera actually being rendered. */
    setCamera(cam) {
      renderPass.camera = cam;
      if (gtao) { gtao.enabled = aoWanted; syncAO(cam); }
    },
    /** AO is meaningless on an orthographic plan 600 m up and actively wrong on
     *  the black-on-white silhouette, so views that are not gameplay cameras
     *  turn it off rather than being measured with it. */
    setAO(on) { aoWanted = !!on; if (gtao) gtao.enabled = !!on; },
    setSize(w, h) {
      composer.setSize(w, h);
      if (gtao) gtao.setSize(w, h);
      bloom.setSize(w, h);
      grade.uniforms.resolution.value.set(w, h);
    },
    /** The AO camera has to be re-synced every frame, not just when the view
     *  changes: in the client the camera is the same object moving, so nothing
     *  ever calls setCamera and a once-only sync would light the AO from the
     *  spawn point for the whole session. */
    render(dt) {
      if (gtao && gtao.enabled) syncAO(renderPass.camera);
      composer.render(dt);
    },
  };
}

// ---------------------------------------------------------------------------
// 7. Everything a renderer needs, in one call
// ---------------------------------------------------------------------------

/**
 * Install the environment into a scene: sky, IBL, scattering, horizon skirt.
 * The three renderers differ in what they do with the result, not in what the
 * result is, which is why this returns handles rather than taking callbacks.
 */
export function installAtmosphere({ renderer, scene, town, heightAt = null }) {
  const atmos = readAtmosphere(town);
  const lighting = town?.lighting || {};

  const sky = makeSky(atmos, lighting);
  scene.add(sky);
  scene.environment = makeEnvironment(renderer, sky);

  installScattering(scene, atmos, lighting);

  const horizon = makeHorizonRing(atmos, heightAt);
  scene.add(horizon);

  return { atmos, sky, horizon, fog: scene.fog };
}
