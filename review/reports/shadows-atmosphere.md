# Shadows, atmosphere, grade — build report

Against `review/reports/ad-town-04.md` §1 (shadow map), §3 and §(a).3 (aerial
perspective), §9 (water), and `docs/ARCHITECTURE.md` §5 (cascades, grade LUT).

**Everything below is measured off a PNG or off an instrument. Where a claim is
not backed by a frame I have looked at, it says so.**

---

## 0. The headline is not the one that was expected

**`ad-town-04.md` §1 is misattributed. The stair-step across the spawn frame was
never the shadow map.**

§1 rejected the build on `crop/arr-floor.png` — *"the floor shadow is a 30 cm
stair-step staircase across the whole nave … the map is 4096² over a 92 m box
(`client/src/main.js:83`) — 44 texels per metre with no cascade, which is
exactly this artefact"* — and named it the largest area of wrong pixels in the
two most important frames in the project. That diagnosis came from reading
`main.js:83`, not from testing it.

I added `?shadows=0` to the harness (`tools/render/town.html`) — the sun's shadow
map off, nothing else changed — and re-shot the arrival frame:

| frame | what it shows |
| --- | --- |
| `review/shots/csm-after/zoom-before.png` | the staircase, shipped build |
| `review/shots/csm-after/zoom-after.png` | the staircase, **cascaded shadow map at 7.4× the texel density — unchanged, riser for riser** |
| `review/shots/csm-noshadow/town-arrival.png` | the staircase, **shadow map switched off entirely — still there, and now visibly a brown surface over pale paving** |

It is `tools/assetgen/venues/church.py:1006`, the worn path from the altar to
the doors:

```python
for i in range(24):
    z = 1.6 + i * 0.42
    w = 2.90 + max(0.0, (z - 8.0)) * 0.55        # fans out at the door
    p = M.quad(w, 0.46, "flag", uv_scale=uv)
    p = p.with_colour((0.64, 0.60, 0.55))
```

24 hard-edged quads, 0.46 m deep at a 0.42 m pitch, each carrying a **flat 36 %
value step with no ramp at all**, each 0.23 m wider per side than the one behind
it past z = 8. A 0.42 m tread with a 0.23 m riser repeated down a diagonal is a
staircase by construction. The seven rotated 0.7–1.5 m quads at the dais foot
(`:1016`) are the large rectangular notches in the same crop.

**Fixed.** The path is now a continuous lattice of coplanar cells over the nave
floor carrying a per-VERTEX wear field: the cells butt exactly so there is no
geometric seam anywhere, the tint interpolates across each cell instead of
stepping at its edge, the centre-line wanders, and cells the field never reaches
are white (COLOR_0's identity) and are dropped. **The boundary is a gradient, not
a polygon.** +266 triangles on the church.

- **before** `review/shots/csm-after/cmp-floor-before.png`
- **after** `review/shots/path-fix/floor-fixed.png`

Why this matters beyond one crop: the top item on ad-town-04's ranked list would
have consumed a wave and left the artefact on screen. The shadow work was still
worth doing — ARCHITECTURE §5 has specified cascades since before v2 and the
single box really was 44.5 texels/m — but it is not what §1 was looking at.

---

## 1. Cascaded shadow maps — BUILT

`client/src/shadows.js` already existed when I started: a complete `SunRig` CSM
module, **wired into nothing**. No file imported it. `client/src/main.js:83`
still declared its own single box, and so did `tools/render/town.html`
(`CLIENT_SHADOW = { half: 46, dist: 70 }`) and `tools/render/viewer.html`
(`sc.far = 220`, `left = -45` — already drifted from the client's 200 and 46).
Four hand-maintained copies of the same four numbers.

Installed now, in all three renderers, from one authored block.

| file | change |
| --- | --- |
| `tools/plan/plan_data.py` → `LIGHTING["shadows"]` | **new** — the authored policy, content is the authority (D-009's rule) |
| `client/src/shadows.js` | per-cascade normal bias, cascade fade, exact texel snap, and a camera-assignment bug in `fitSingle` that would have rendered the plan and the aerials unlit |
| `client/src/main.js` | the single `DirectionalLight` is gone; `SunRig` fitted to the camera every frame and in `hm.shoot()` |
| `tools/render/town.html` | `CLIENT_SHADOW` and `aimSun()` gone; `fitCascades` for gameplay cameras, `fitSingle` for plan/aerial/silhouette |
| `tools/render/viewer.html` | its fourth copy of the rig gone |
| `client/src/lod.js` | `SHADOW_CAST_DISTANCE` demoted to a fallback; both renderers pass the authored reach |

Three things that are easy to get wrong and are worth knowing:

- **Registration order.** `SunRig.register()` must run AFTER `Water.harvest` and
  `Ambient.harvest`, because all three install `onBeforeCompile` and only
  `register` chains what it finds. The other order drops the CSM hook, the
  `CSM_cascades` uniform never gets a value and every fragment falls into
  cascade 0.
- **An unregistered material renders at `cascades` × the sun**, because three's
  stock lighting chunk loops over all directional lights and the cascades are
  copies of one. The horizon skirt, the scale figures and the player avatar all
  needed registering explicitly. `rig.audit(scene)` counts misses and both
  instruments print it: **currently 0 unregistered of 597 materials.**
- **`mapSize` is written once and never again.** three allocates the shadow
  target lazily only when `shadow.map === null`, so a size changed after the
  first frame is a number nothing reads. `stats()` reports `shadow.map.width`.

### Measured density, off the live shadow cameras

| | range | box | map | texels/m | texel |
| --- | --- | --- | --- | --- | --- |
| **before** | 0 – 42 m | 92.0 m | 4096² | **44.5** | 2.25 cm |
| cascade 0 | 0 – 5.4 m | 11.6 m | 4096² | **352** | 0.28 cm |
| cascade 1 | 5.4 – 30 m | 63.8 m | 4096² | **64** | 1.56 cm |

In screen pixels, which is the only unit a stepped edge is visible in (55° over
900 px):

| distance from eye | before | after |
| --- | --- | --- |
| 1 m | 19.4 px/texel | **2.4 px** |
| 3 m | 6.5 px | **0.81 px** |
| 6 m | 3.2 px | **1.35 px** |
| 15 m | 1.30 px | **0.90 px** |
| 30 m | 0.65 px | **0.45 px** |

Every distance improves; nothing regresses.

### It is visible, and here is the frame that proves it

`review/shots/csm-after/gs-before.png` vs `gs-after.png` — the dappled tree
shadow on the road at `gate-south`, which ad-town-04 called *"the best lighting
event in the build"* and *"stepped at its edges"*. Before, the leaf gaps smear
into large amorphous blobs. After, individual sun-flecks resolve with real edges
and the dapple reads as foliage. That crop spans 4.3 m to 12.7 m from the eye.

**And the figure now has a contact shadow.** ad-town-04 §1 and pass-02 #13:
*"the 1.75 m figure has zero contact darkening in every frame it appears in — it
reads as a decal pasted on the ground."* `review/shots/final/AB-gate-south-after.png`
against `AB-gate-south-before.png`: the body now casts a resolved shadow with
contact darkening under the feet. A 0.17 m limb at a 2.25 cm texel under PCF was
below the threshold; at 0.28 cm it is not. This closes the shadow half of that
finding. The AO half (GTAO not reaching dynamic geometry) is untouched.

---

## 2. Cascade cost — the other half of the same problem

The brief was explicit that quality and cost are one problem here. They are, and
the obvious configuration gets the cost badly wrong. Recorded because the shape
of the answer is not obvious:

| config | shadow draws @ `square` | frame draws | frame tris |
| --- | --- | --- | --- |
| **before** (1 box, 42 m reach) | 602 | 1,416 | 2.88 M |
| 3 cascades, 42 m | **1,128** (+88 %) | 1,917 | 4.45 M |
| 3 cascades, 32 m | 896 | 1,671 | 4.16 M |
| 2 cascades, 32 m | 672 | 1,445 | 3.61 M |
| **2 cascades, 30 m — shipped** | **604** | **1,385** | 3.59 M |

**Why cascades do not pay for themselves by themselves.** CSM sizes each
cascade's box by its frustum slice's far-plane diagonal, which for a 55° camera
at 16:9 is 2.12 × the slice's far distance. At a 42 m reach the FAR cascade's box
is 89 m — the same 92 m box again — so it holds the entire caster set on its own,
and the near cascades are added on top of it. Hence +88 %.

The caster set is a disc of radius `distance` around the camera, and **its area
is what the shadow pass costs**. Bringing the reach from 42 m to 30 m is what
buys the near cascades back. `lighting.shadows.distance` and the visibility set's
`shadowDistance` are now one authored number so they cannot drift.

**What it costs:** a mass between 30 m and 42 m from the eye no longer casts.
Checked in `gate-south`, `approach-w` and `approach-s`, the three views with open
ground running away from the lens — I could not find a terminator in any of them,
because in a walled town at eye height almost everything past 30 m is occluded by
something nearer. It is a real trade and a reviewer should look for it.

**Shipped: 2 cascades, 30 m, splits [0.18], 4096² each, fade on.**

Draw calls at the worst gameplay camera go **1,416 → 1,385**. Triangles go
2.88 M → 3.59 M, and I am not going to pretend that is free — see §6.

---

## 3. Atmosphere — retuned, measured

Authored in `tools/plan/plan_data.py → ATMOSPHERE["scattering"]`.

| | before | after |
| --- | --- | --- |
| `nearColor` | `#E8DCC8` (b−r −32, luma 219) | `#E4D3B0` (b−r −52, luma 210) |
| `farColor` | `#A9C2DC` (b−r +51, luma 192) | `#8FB2DE` (b−r **+79**, luma **175**) |
| `density` | 0.0058 | **0.0038** |
| `maxOpacity` | 0.93 | **0.78** |
| `startDistance` | 14 | 12 |
| `fullDistance` | 130 | **82** |

**The finding that made it work is `fullDistance`.** Pass 03 asked for 300 and
pass 04 repeated it; that would have been the wrong direction. `fullDistance` is
the ONLY control over where warm becomes cool. At 130 m the crossover sat beyond
the 192 m town, so every distance a player ever looks at was still being mixed
toward the warm cream near colour and the cool far colour never reached the
frame at all — which is exactly why `temperatureSwing` measured **0.2**. It is
the colour interpolation, not the opacity, that was killing the temperature half.
`density` and `maxOpacity` are the value half and both come down. The two colours
are now pushed apart in hue (near-to-far b−r 83 → **131**) and pulled together in
value (27 → **35 the other way**: the far colour is now DARKER than the near one,
so distance stops meaning "brighter" and starts meaning "cooler").

### Measured, `town.mjs --bands`

`review/shots/csm-before/before-report.json` → `review/shots/final/town-report.json`

| view | fg→bg before | after | **temperatureSwing** before | after |
| --- | --- | --- | --- | --- |
| `arrival` | 94.9 | **70.7** | 0.2 | **3.1** |
| `gate-south` | 83.4 | **30.3** | 25.5 | **47.1** |
| `approach-s` | 75.6 | **69.0** | 17.7 | **23.6** |
| `approach-w` | 80.6 | **52.5** | 26.3 | **33.6** |
| `approach-ne` | 51.1 | 35.2 | −40.2 | −36.9 |

Band luminances at `arrival`: fore 61.3 → 62.8, mid **143.6 → 132.5**, back
**156.2 → 133.5**. The midground is 11 points less washed and the background 23
points less washed, which is the "veil that flattens the fountain" coming off.

**Read honestly:**

- Three of five views are now inside or through the +45–60 fg→bg band and above
  the +20 temperature target. `approach-w` at 52.5 / 33.6 is exactly on spec.
- **`arrival` is still the weak one at 70.7 / 3.1, and I know why.** Its
  foreground band (0–22 m) is the dark church interior — the fg→bg number is
  mostly interior-vs-exterior, not haze, and no fog setting will fix that. Its
  temperature swing is small because the grade's new cyan shadow lift (§4) cools
  that dark foreground, narrowing the measured gap: on the same build with the
  OLD grade it measured **7.7**. The metric is fighting itself on this one view.
  **The picture is much better even though the number barely moved** —
  `review/shots/final/AB-arrival-before.png` vs `AB-arrival-after.png`: the guild
  tower has value and stone texture instead of being a pale ghost, the jettied
  range at frame-left has colour, and a second spire and the market clutter are
  visible through the aperture where before there was cream.
- `approach-ne`'s swing is negative in both builds because its foreground is the
  green Mere. That number is not measuring haze and should not be read as if it
  were.
- `square` returns `null` in both builds: the lamp standard still fills the
  foreground band, so the instrument still cannot measure that frame. ad-town-04
  §12 — unfixed, not mine.

The clearest single image of the change is the aerial:
`review/shots/csm-verify/x-aerial-before.png` vs `x-aerial-after.png`.

---

## 4. The grade — it was installed everywhere and it was inert

**Applied identically? Yes.** All three renderers call `makePostChain` from
`client/src/atmosphere.js`, which builds one `makeGrade` from
`atmosphere.grade`. `town.html` and `viewer.html` disable it only for the
silhouette, where it would lift the black the image exists to measure. There is
no fourth copy and no drift.

**Does it do what ARCHITECTURE §5 says? No — it was computing the move and
rounding it away.** Evaluated on a neutral ramp with the shipped numbers:

| input | Δ value | Δ blue−red |
| --- | --- | --- |
| 0.06 | **+1.0** | **+1.5** |
| 0.12 | +0.3 | +1.9 |
| 0.20 | −0.3 | +1.3 |
| 0.46 | −0.9 | −6.6 |

§5's *"lifted shadows … slight cyan push in the shadows for complementary
contrast"* was landing at **1.5 levels out of 255**. The cause: the cyan was a
MULTIPLY (`c * shadowTint * 1.28`), and a multiplicative tint changes a pixel by
a fraction *of that pixel* — the pixels in question are dark, so the whole move
fits inside the quantiser. The warm midtone was the only part working, because a
midtone is bright enough that a percentage of it is a visible number.

**Fixed.** A lift is an offset, so its colour has to be an offset too.
`shadowTint` is now a DIRECTION: normalised to unit luminance (leaving a pure hue
ratio with no brightness in it), and `shadowAmount` is how far the lift leans
along it. The lift's luminance is always `lift`; only its hue moves. Floored at
zero per channel, because a negative channel is not a tint — it is a crushed
black and Art Bible §1 forbids it.

Re-measured, `lift` 0.028 → 0.038 and `shadowAmount` 0.20 → 0.14:

| input | Δ value | Δ blue−red |
| --- | --- | --- |
| 0.06 | **+3.8** | **+15.3** |
| 0.12 | +3.0 | +12.3 |
| 0.20 | +2.0 | +8.1 |
| 0.30 | +0.9 | +2.8 |
| 0.46 | −0.3 | −6.0 |

Shadows lifted, cyan in the shadows, warm in the mids, decaying to nothing by 30 %
grey. Same transform shape, same two authored numbers, finally doing something.
`docs/ENGINE_PORTING.md`'s LUT bakes straight off it, unchanged.

---

## 5. Water — NOT DONE, and I am not going to imply otherwise

Item 3 of my brief (shoreline transition in `terrain.py`: a wet band that darkens
and smooths toward the water, weed and scum at the line, depth-tinted
transmission, plus the fountain water and the mill race) **was not started.** The
shadow and atmosphere work plus the church-floor finding consumed the budget.

What the frames say about it now, so the next agent starts ahead:

- `review/shots/final/town-aerial-sw.png` — the Mere is still a stamped ellipse
  with a uniform-width beach ring, and its far half is still a **pure white
  blowout**. `atmosphere.water.specularKnee` is still **1.05**; pass 03 asked for
  ~0.55 and it has now survived three reviews at 1.05. That is one number.
- The land/water meeting line is still a hard edge with no wet band anywhere.
- The atmosphere retune made the blowout MORE conspicuous, not less: the rest of
  the frame is no longer washed toward cream, so the white plate now stands
  alone. Weakening the haze does not fix water; it stops hiding it.

**Water is systemic failure #3 and it is untouched. Frames containing it should
not be scored as improved.**

---

## 6. Budget — read this before believing any A/B in this report

**The shipped content and assets were not current outputs of their generators.**
`tools/plan/townplan.py` is deterministic (verified: two consecutive runs give a
byte-identical `hearthmere.json`), so regenerating it — which the pipeline
requires — should have been a no-op. It was not. Between the baseline frames in
`review/shots/csm-before/` (rendered by the previous session) and my first run,
with only `plan_data.py` edited:

- `chophouse` **moved 5 m** (−21.5, −33 → −21.3, −38)
- `wall` +3 batches, **+7,998 triangles**
- `quay` +1 batch, `landscape` +1 batch
- and a later full `build.py` moved `market_square` from **26,925 to 50,611
  source triangles**

**Consequences you must hold in mind:**

1. **A tree that stood at frame right in `gate-south` — the one throwing the
   dappled shadow ad-town-04 called the best lighting event in the build — is not
   in the current town.** `review/shots/final/tree-before.png` vs
   `tree-after.png`. Nothing I changed can hide geometry (`VisibilitySet.setShadow`
   only writes `castShadow`, and the drawn-batch count is unchanged at 302 → 305).
   This is a regression in one of the three frames that survive a blind
   side-by-side, and **it arrived with the pipeline being re-run, not with my
   code.** It needs an owner.
2. Whole-frame A/B against `csm-before` carries that confound. The claims in §0
   and §1 do not depend on it: the shadows-off test is a single-build A/B, and
   the two crops compare the same frame region in the same asset state.
3. The triangle rise at `square` (2.88 M → 3.59 M) is **not all mine**: the
   `market_square` rebuild alone adds ~23.7 k source triangles, which amplify
   through scene + shadow + AO.
4. **`validate.py` now reports 5 failures / 46 warnings where ad-town-04
   recorded 0 / 41.** Four are `uv_density` failures naming hand-laid UVs —
   `nogging` at 0.47×, `straw` 0.38×, `wool_crimson` 3.10×, `canvas_amber`
   0.41× — which is ad-town-04 §2's "421 literal `uv_scale=` call sites against
   3 uses of `MATS.uv_scale()`" showing up as a hard failure for the first time.
   The fifth is §7 mesh memory at **243.3 MB against the 240 MB budget** (the AD
   measured 239.4 MB and called it "not a budget, it is a cliff" — it has now
   gone over). **None of these is reachable from anything I edited**: a vertex
   colour field on the church floor cannot change `nogging`'s metres per tile.
   They appeared when the assets were rebuilt from their current generators,
   which is the same finding as the rest of this section — **the shipped build
   was passing because it was older than its own source.**
5. `check_walkable.mjs` now names a **different** unreachable door —
   `hm.slot.07.chophouse.door.01` instead of `hm.townhouse.door.15` — which is
   the 5 m `chophouse` move. Still 15/15 streets PASS, Ford Road traversable end
   to end, still exactly one unreachable door, but it is not the same one and
   BUILD_DIRECTIVE §9's first box is still unticked.

Current worst gameplay camera (`square`): **1,385 draws / 3,591,341 triangles**
against 900 / 3,500,000. Draw calls are *below* where they started (1,416).
Triangles are 2.6 % over and were 17.7 % under. The gate was already failed at
1.57× on draws before this wave, and §7's own required texture atlasing has still
never been done — which remains the item that no amount of art or shadow tuning
will close.

### Instrument parity, which the brief said not to break

`tools/check_client.mjs` (the real client) against `tools/render/town.mjs`, same
arrival camera:

| stage | client | harness | Δ |
| --- | --- | --- | --- |
| scene | 540 | 541 | 0.2 % |
| **shadow** | **570** | **568** | **0.35 %** |
| ao | 206 | 205 | 0.5 % |
| post | 79 | 62 | (full-screen quads; viewport-dependent) |
| **triangles** | 2,935,499 | 2,931,622 | **0.13 %** |

The three geometry stages agree to ≤ 0.5 % and triangles to 0.13 %. The rig is
derived from the camera by the same class in both, so parity is now structural
rather than two expressions somebody has to keep matching. `check_client` also
walks 151.5 m and boots clean with 0 unregistered materials.

---

## 7. New instruments left behind

- `tools/render/town.mjs --query shadows=0` — the sun's shadow map off, nothing
  else changed. This is the A/B that settles "is that edge light, or is it
  geometry?" in one frame, and it is what caught §0. An artefact nobody can
  switch off is an artefact nobody can attribute.
- `SunRig.stats()` — box size, **allocated** map size (three clamps `mapSize` to
  the driver limit silently), texels/m, texel cm and normal bias per cascade.
  In every `town-report.json` per view, in `hm.shadows()` in the client, and in
  `check_client`.
- `SunRig.audit(scene)` — sun-lit materials the rig never registered, which
  render at `cascades` × the sun. In `report.shadows.unregistered` and as a
  harness warning.

## 8. Handover, ranked

1. **Reconcile the pipeline with what shipped.** §6. This is now ahead of the
   art items, because until it is done no review is reviewing the build the
   generators produce. Three symptoms of one cause: the `gate-south` tree is
   gone from a top-three frame, `validate.py` went 0 → 5 failures, and mesh
   memory went over budget — all of it on a plain regeneration, none of it from
   a generator edit. Either the shipped state was stale, or something in the
   pipeline is not reproducible; `townplan.py` is proven deterministic, so
   `build.py` is where to look next.
2. **Water.** §5. `specularKnee` 1.05 → 0.55 is one number and three reviews old.
   The shoreline is geometry and is still a hard edge.
3. **The rest of `ad-town-04` §2** — the ground quilt. The church floor's share
   of it is closed; `review/shots/path-fix/floor-fixed.png` still shows two
   straight-edged pale quads at frame right that are not the worn path.
4. **Triangles.** 2.6 % over. The cheapest lever is `splits`: dropping the near
   cascade's share shrinks its box, which makes it both finer AND cheaper — the
   one place in this system where quality and cost move the same way.
5. **`square` still cannot be measured** because the lamp fills the foreground
   band. Three passes.

## 9. Recorded

`docs/DECISIONS.md` D-060 (the cascade rig, and why the reach is the cost),
D-061 (a lift is an offset, so its colour is an offset), D-062 (`fullDistance`
is the temperature control and raising it was the wrong direction). Numbering
follows the build session's sequence and renumbers at reconciliation per the
owner's D-036/D-040 ruling.

## 10. Frames, for a reviewer who wants to check rather than take

| claim | before | after |
| --- | --- | --- |
| the spawn-frame staircase is not a shadow | `review/shots/csm-after/zoom-before.png` | `review/shots/csm-noshadow/town-arrival.png` (shadow map OFF) |
| the worn path is fixed | `review/shots/csm-after/cmp-floor-before.png` | `review/shots/path-fix/floor-fixed.png` |
| the dapple resolves | `review/shots/csm-after/gs-before.png` | `review/shots/csm-after/gs-after.png` |
| the figure casts | `review/shots/final/AB-gate-south-before.png` | `review/shots/final/AB-gate-south-after.png` |
| the arrival aperture | `review/shots/final/AB-arrival-before.png` | `review/shots/final/AB-arrival-after.png` |
| the haze comes off the town | `review/shots/csm-verify/x-aerial-before.png` | `review/shots/csm-verify/x-aerial-after.png` |
| the wall reads from the field | `review/shots/csm-verify/x-apw-before.png` | `review/shots/csm-verify/x-apw-after.png` |
| **the lost tree** | `review/shots/final/tree-before.png` | `review/shots/final/tree-after.png` |

Full current set: `review/shots/final/` (8 named views + a waterfront walk +
a back lane), `review/shots/csm-verify/` (adds `gate-north` and `silhouette`).
