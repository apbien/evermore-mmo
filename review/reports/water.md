# Water — wave 06

Owner: the water system. `core/terrain.py` water + shoreline, `venues/terrain.py`
water + shoreline, the water materials, and the water shading in `client/src/`
and both harnesses. Plus every other place water appears in Hearthmere.

**Standing rule for this file: nothing is claimed until I have seen it in a
frame.** What I changed but could not verify is under NOT VERIFIED. What I did
not do is under NOT DONE, with the reason.

Frames: `review/shots/water-08/` is the final set for every camera except
`approach-ne`, whose final frame is `review/shots/water-09/t-approach-ne.png`
(one further roughness change after `water-08` was shot). `water-01` … `water-07` are
the intermediate rounds and I have kept them, because two of the findings below
are only legible as a sequence. Compare against
`review/shots/ad-town-05/t-gate-north.png`, `mereshore-free.png`,
`t-aerial-sw.png`, `t-approach-ne.png`, `t-bridge.png`, `t-square.png`.

---

## The two diagnoses that mattered

Three art-director passes have described the shoreline correctly and attributed
it wrongly, and that is why three passes of shoreline work did not land.

### 1. The sawtooth is the WATER, not the ground

`ad-town-05` §2: *"the water plane meets the terrain in a row of sharp
triangular teeth at 5–10 m from the eye, the raw terrain mesh poking through the
surface."* The observation is exact. The attribution is backwards.

`venues/terrain._water` sank each dry edge vertex to `gh - sink`, where
`sink = 0.06 + 0.22 · cell`, on the stated assumption that a dry vertex is
*just* above the water. On a steep bank it is not. Measured with `T.height`, not
inferred:

| cell | ground at the two corners | where the sheet was put | above the surface by |
| --- | --- | --- | --- |
| x −49.2, z −88 | −4.81 → −2.04 | −3.10, −2.32 | **+0.78 m** |
| x −48.0, z −86 | −1.55, −1.55 | −1.83, −1.83 | **+1.27 m** |

The water sheet was climbing the bank. The teeth are its own edge triangles
standing out of the lake — water material, lit near-vertically, which is exactly
why they read dark. Nothing was poking through anything.

**Fix:** one `np.minimum(…, lvl)`. A dry vertex can now only be at the surface
or below it, so near the waterline the old burial still happens and up a steep
bank the sheet goes flat and the ground occludes it.

**Verified:** `water-08/mereshore-free.png` against
`ad-town-05/mereshore-free.png`. The row of teeth is gone; the mill's leat now
has a shoreline.

### 2. The scalloped edge is two meshes disagreeing about one contour

The ground is a four-ring LOD field at 0.5 / 1 / 2 / 4 m. Its surface is a
piecewise-LINEAR interpolation of `T.height`. The water sheet was built on its
own 1.2 m grid from the true function. The two therefore disagree about where
the waterline is — by metres of plan on the 4 m ring — and every disagreement
shows as a triangle of water on the beach or a triangle of beach in the water.

`_mesh_height` (new) evaluates the ground's own triangles: the same rings, the
same cell sizes, and the same alternating diagonal `_ring` lays, all four
interpolation cases. The water now asks the ground how high it is, so "this
vertex is dry" means "the ground the player can see is above the water here" —
the only definition that cannot produce a tooth at any LOD, because both sides
of the edge are the same surface.

---

## Landed, and verified in a frame

1. **The camera stood under the river.** `tools/render/town.html` took every eye
   height from `terrain.height()`, which over the Emberflow is the channel bed
   at −5.6 m against a surface of −3.1 m. New `standY = max(groundY,
   waterLevel)`, used for the camera and for figure placement. `t-bridge` goes
   from daylight through all three arches, piers on dry ground and a black unlit
   wedge, to **a frame with a river in it**. Same bug, same fix, on
   `spine-walk-01`. *(`water-08/t-bridge.png`.)*
2. **`specularKnee` 1.05 → 0.55.** Three reviews old, asked for by name twice.
   The pure-white far half of the Mere is gone and the sun path now resolves
   into a glitter path of individual highlights. *(`t-aerial-sw`,
   `t-approach-ne`.)*
3. **The colour.** `water_surface`'s albedo ran R:G:B = 0.37 : 1.00 : 0.69 in
   linear, so the diffuse term was four times greener than red — no specular
   work could rescue that, and it is why four passes called the Mere "tropical
   emerald". Now 0.48 : 1.00 : 0.71. `kit.WATER_DEEP` ran the wrong way too: it
   took red down twice as far as green, so deeper meant greener. Real water
   absorbs red first and blue last. Measured at `t-gate-north`, same pixels:
   **(32, 101, 71) → (16, 60, 49)**, and the frame reads as a northern mere
   instead of a lagoon.
4. **Depth.** The tint ramp was linear over 2.6 m — most of its range spent on
   depths nobody can distinguish and almost none on the 0–0.5 m margin that is
   the only band a player reads. Exponential now. `WATER_MIN` 0.26 → 0.08.
5. **Fresnel.** COLOR_0's alpha is only the looking-straight-down half of
   transmission. Schlick at f0 0.02 in `client/src/water.js`: the near margin
   shows its bed, the far reach turns to sky.
6. **Distance roughness.** The ripple normal mips toward flat past ~30 m, so the
   whole far half answered the sun identically — the "hard featureless
   pure-white specular plate" of `t-approach-ne`. Roughness now rises with view
   distance.
7. **Shoal roughness.** Shallow water is rougher, because the bed is breaking
   it. Without it every sunlit shore answered the sun with the open lake's
   narrow lobe and rendered as a pale rim following the sheet's cell boundary.
8. **The wrack line.** `t-aerial-sw`'s "hard white scalloped ring" round the
   north-east is this ribbon, not the water. Three changes: it stops at 100 m
   (past the 1 m ring the contour and the rendered mesh disagree by metres, so
   half of it buries and half floats — which *is* a scallop); it is broken into
   windrows on the lee shore instead of ringing the lake; its width varies. And
   the material went from near-`PLASTER_SHADE` to olive pond wrack, because
   standing-water scum is not surf. Palette: 9.6 (FAIL) → **3.9**.
9. **The fountain's water was mipping out of existence.** Not culled — nothing
   was culling it. `_fall` used `foam`, which is alpha-MASKED; at 12 m a
   0.09–0.30 m ribbon samples a mip where the lace has averaged below the
   alpha-test threshold and every fragment is discarded. New `water_fall`
   material, BLENDED, so there is no threshold to fall under. **`t-square` at
   20 m now has falling water off the tazza rim and off the heron's beak**,
   which `ad-town-05` §9 records as absent. It also fixes the other half of that
   finding — "hard-edged opaque pale ribbons stuck to the air with no
   transparency" — because the ribbons are translucent now. The mill wheel's
   tail race moved to the same material.
10. **The outlines.** "A mathematically perfect ellipse with a uniform-width
    beach ring … the Emberflow a dead-straight parallel-sided canal" is the
    signed distance field: a polygon carved at a constant shelf gives a smooth
    offset curve whose beach is the offset of an offset, and a polyline carved
    at a constant half-width *is* two parallel lines. `outlineNoise` (authored
    per shape in `content/town/terrain.json`, applied in `core/terrain.py`,
    ported to `client/src/terrain.js`) displaces the FIELD, so bed, shelf,
    waterline and beach move together and the beach stays a beach. Authored on
    the Mere, the deep water and the Emberflow; deliberately NOT on the harbour
    (a built quay stands on it) or the old ford (3 m wide).
11. **The bank was a chequerboard, and it was the splat.** `t-gate-north`'s
    "hard sawtooth of flat dark triangles where the bank meets the surface" is
    per-triangle `argmax` over two near-equal weights: the mud band's upper edge
    ran straight into turf, so the ground alternated grass, silt, grass, silt at
    the cell size all along it. Two fixes: a **beach band** between the wet mud
    and the turf (a lake has one, and it is what tells a player how deep the
    water is), and a **coherent tie-break field** on the `argmax` so a 50/50
    boundary breaks into tongues rather than a chequerboard. The module
    docstring has always claimed those boundaries were dithered; now they are.
    *(`water-08/t-gate-north.png` — one coherent shingle beach under a green
    verge.)*
12. **The wet band.** 0.42 m → 0.95 m and darker, and cooler as well as darker,
    because wet silt loses more red than blue. At 0.42 m on a bank that falls
    2.5 m the whole transition happened inside one triangle.
13. **Reed and graded shingle.** Reed and sedge where the shore is shallow,
    still, shelving and outside the town; shingle graded coarse at the storm
    line to fine at the water, which is real sorting and instantly readable.
    Both instanced off the same marching-squares contour the water and the wrack
    use. 211 reed/sedge stands, 994 stones, **+4 draw calls** on the terrain
    venue.
14. **The reflection, cheaply.** `_shore_occlusion` bakes a horizon test into
    COLOR_0: water beside a bank mirrors the bank and is dark, water in mid-lake
    mirrors the sky and is bright. It is not an image and it is not claimed as
    one — see NOT DONE — but it is the term that was missing, it costs nothing
    at runtime, and it lands on every case the review names: the Emberflow goes
    properly dark between its banks, the water under the bridge arches darker
    still, the harbour dark against the open Mere.
15. **One implementation, three harnesses.** `tools/render/viewer.html` had **no
    water code at all** — every fountain basin, horse trough, tannery pit and
    mill race in this project has been signed off in a viewer that draws them as
    still green glass with no flow, no Fresnel and no specular shoulder. It now
    imports the same `client/src/water.js` and is handed the same authored
    blocks. Flow rates, wind response, Fresnel, both roughness ramps, the
    shallow colour and the specular knee are all in
    `content/town/hearthmere.json → atmosphere.water`; **nothing about water is
    hardcoded in any harness** (D-009).
16. **Wind.** `ambient.wind` already drove the cloth and the smoke. It now
    drifts the still-water ripple field downwind, scales the chop with wind
    speed, and breathes it at the authored `gustHz`. The Emberflow ignores it —
    a current wins over a breeze.
17. **A whole-client syntax error, caught before it shipped.** The GLSL chunks
    in `water.js` are JS template literals, and a backtick inside one closes it.
    I put ``` `ad-town-05` ``` in a shader comment and took the entire client
    down — not the shader, the *page*. `node --check` caught it; there is now a
    NOTE in that chunk. Worth recording because the same trap is in every
    `onBeforeCompile` in this repo.

---

## NOT DONE, stated plainly

- **A true planar reflection.** `ad-town-05` §2(d) asks for it and calls it "the
  single tell that stops any water frame". I did not build it, and the reason is
  a number: at `gate-north` the beauty pass is 687 draw calls and the frame is
  **1,283 against a §7 budget of 900**. A planar reflection is a second full
  scene pass. Buying it this wave would be spending 300–600 draws out of the
  perf agent's lane in a build that is already failing the gate, and I am not
  going to do that without the AD deciding it is worth it. §14 above is the
  view-independent half of the term, baked, at zero runtime cost. **The costed
  route when it is wanted:** the water is ONE plane at `surfaceY = -3.1`, which
  is the easy case — a mirrored camera, a clip plane at the water, a half-res
  target, shadows off, and a reflector layer containing only masses within ~60 m
  of a water body. That last clause is the whole cost control and it needs a
  tag on the cell batches that does not exist yet.
- **The bank at the north gate is still faceted.** The material chequerboard is
  fixed and the beach reads, but the ground there falls 2.5 m in about 2 m and
  at 1 m cells that is a two-triangle cliff. The honest fix is a masonry
  revetment along the town side of the Emberflow, which is the wall's geometry
  and not mine.
- **The quay's water furniture.** `ad-town-05` §11 wants the quay planked, worn
  and loaded with cargo and moored boats. That is the quay venue, not the water
  system; the water under it is now right.

---

## Two things I changed that somebody should have an opinion about

- **The 1.75 m figure now steps back to dry land, or is dropped.** `t-bridge`
  looked across 11 m of river, so the reference figure was standing IN it —
  `ad-town-05` §2 names that. `figuresForEye` now walks a fan of offsets and
  takes the first that is on ground above the water level; if the whole fan is
  water it returns nothing and the frame keeps its metre bar. `t-bridge` is the
  one frame in my set where the fan is entirely water, so that camera now has
  no figure. CLAUDE.md wants a figure in every review render, and a figure
  walking on water is not one — but this is a judgement call and it is in a
  shared file, so it is flagged rather than assumed.
- **A defect in `t-bridge` that is not mine and is still there.** The "pure
  black unlit wedge on the east bank" is still in the frame at roughly
  x 1160–1260 — it is landscape geometry on the bank, not water, and it is the
  same class as `ad-town-05` §16's black unlit polygons.

---

## NOT VERIFIED

- **`viewer.html`'s water.** The wiring is done and the file parses, but I did
  not render a single-venue shot through it this wave. Somebody should shoot the
  fountain or a horse trough through `shoot.mjs` before trusting it.
- **The client, visually.** `check_client.mjs` boots, walks 151.5 m and emits no
  water warning — which means all four shader patches installed, because each
  one warns loudly by name if its chunk is missing. I did not look at a client
  screenshot.
- **The diamond lattice on `t-approach-ne`.** See below.

---

## The one open defect I found and could not close — with three eliminations

`t-approach-ne`'s bottom-right carries **a regular lattice of light and dark
diamonds** across the near water. `ad-town-05` §2 calls it "visible triangular
polygon facet seams". **It is still there and I am not claiming it fixed.**

What I did close on this camera, and it is a large change: the "hard featureless
pure-white specular plate running the full height at x≈900–1200" is gone. The
sun path is now a broad soft glitter path that resolves into individual
highlights (`water-09/t-approach-ne.png` against
`ad-town-05/t-approach-ne.png`). The water is a dark green-slate lake instead of
a solid opaque emerald sheet.

The diamonds are a separate defect, and three experiments narrow it a long way.
Each was a single change with a render either side:

| hypothesis | test | result |
| --- | --- | --- |
| normal-map tile moiré at grazing incidence | anisotropy 16 on all three water maps | **no change** (`water-07`). Either it is not the cause, or headless GL is clamping anisotropy to 1 — worth checking before discarding the hypothesis |
| the per-vertex swell's value-noise lattice (`_value_noise` is defined on an integer lattice, so it puts cells on the world axes at exactly 1/f metres — 10.8 m and 6.4 m for the two short octaves, close to the observed spacing) | every octave rotated into its own frame at an angle that is not a simple fraction of a turn, and the two short amplitudes dropped | **no change** (`water-08`) |
| a shading response of any kind | distance roughness gain 0.40 → 0.72, start 14 m → 7 m | the plate softened a great deal; **the diamonds did not move at all** (`water-09`) |

A pattern that survives a roughness change of that size is not shading. **The
remaining hypothesis, and the one I would test first, is the GROUND.**
`_ring` deliberately alternates its triangle diagonal — `alt = ((I + J) % 2)` —
"so the field is not one combed direction", and that produces a chequerboard by
construction. Where the bed sits within centimetres of the surface over a wide
flat area, as it does in the Mere's southern margin right in front of this
camera, alternating triangles poke through a nearly transparent sheet and read
as exactly this: a diagonal chequerboard of flat facets, at the LOD ring's cell
size, growing toward the camera. The test is one render with the water sheet
suppressed. I ran out of budget before I could do it, so it is a hypothesis and
it is labelled as one.

The three rotated-swell and anisotropy changes are kept: they are correct on
their own terms (the swell lattice IS a real hazard on a near-mirror, and
anisotropy IS what a grazing water plane needs), they cost nothing, and they
made no frame worse.

---

## Instruments

| instrument | before this wave | after |
| --- | --- | --- |
| `validate.py` | 5 failures | **3 failures**, none of them water |
| — `§7 mesh memory 243.3 MB` | FAIL | passes (233.4 MB) |
| — `foam` palette | — | 9.6 FAIL → **3.9** (under the 5.0 warn line) |
| — `water_fall` texel density | — | 512 px/m FAIL → **256**, in class |
| `check_client.mjs` | boots, fails the budget gate | boots, walks 151.5 m, **no water warning**, still fails the budget gate at 1,398 |
| `town.mjs` gameplay draws | 1,419 baseline | 1,283 at `gate-north` |

Water palette scores, for the record: `water` 4.9 (INN_GREEN), `water_flow` 4.7
(VERDIGRIS), `water_fall` 2.5 (PLASTER), `foam` 3.9 (HERB_GREEN). All under the
5.0 warn line.

**The three remaining `validate.py` failures are `straw`, `wool_crimson` and
`canvas_amber` UV density — none of them mine, all of them pre-existing.**

---

## Files I touched, and the shared ones I was careful with

Mine outright:

- `tools/assetgen/venues/terrain.py` — `_mesh_height`, `_shore_occlusion`,
  `_contour`, `_margin`, the sheet clamp, the depth ramp, the wrack ribbon, the
  splat tie-break, the wet band, the rotated swell.
- `tools/assetgen/core/kit.py` — `WATER_DEEP`, `WATER_MIN`, `pebble`.
- `client/src/water.js` — rewritten.
- `content/town/hearthmere.json → atmosphere.water` — the authored block.
- `content/town/terrain.json` — `water.channels[*].outlineNoise`,
  `surfaces.waterlineMud.dropOff`.
- `review/reports/water.md`.

Shared, smallest possible edit, stated here because four agents ran concurrently
last wave and interfered:

- `tools/assetgen/core/materials.py` — three edits: `water_surface`'s two colour
  constants, a new `water_fall` builder, `water_foam`'s base and tints, and two
  `LIBRARY` rows. No other function touched. **The file was modified by another
  agent while I worked; every one of my edits was made against a fresh read of
  its own hunk.**
- `tools/assetgen/core/terrain.py` — `shape_weight` and `_outline_noise` (which
  de-duplicate an SDF that `height` and `water_influence` each had their own
  copy of), and the beach band + the `far_shore` → `shore` correction in
  `surface_weights`.
- `client/src/terrain.js` — the port of `shapeWeight`/`outlineNoise`. It has to
  stay a port; BUILD_DIRECTIVE §6.3 makes one height function the law.
- `tools/render/town.html` — `standY`, three call sites, and `figuresForEye`
  walking to dry land. Nothing else.
- `tools/render/viewer.html` — three lines to import and drive `Water`.
- `tools/assetgen/venues/market_square.py` — five material-key swaps
  (`foam` → `water_fall`) and two basin depths.
- `tools/assetgen/venues/watermill.py` — one material-key swap.

## For the next wave

1. Look at `water-08/t-approach-ne.png` and decide whether the swell lattice is
   closed. If it is not, the next lever is to replace `_value_noise` in the
   swell with a gradient noise, which has no visible cell structure at all.
2. Decide whether the planar reflection is worth its draw calls. If yes, the
   blocker is a reflector tag on the cell batches, not the reflection code.
3. A masonry revetment where the Emberflow runs along the town wall. The water
   is right there now and the bank is a two-triangle cliff.
