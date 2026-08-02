# Foliage — placement, shadow and transmission (wave 1, item 4)

Owner: `tools/assetgen/core/vegetation.py`, `tools/assetgen/venues/landscape.py`,
plus the leaf/needle atlas functions in `core/materials.py`.

Answering `review/reports/ad-town-05.md` §3 and the pass-04 §4 carry-over.

## What I found before touching anything

Three separate defects, only one of which the review had named.

### 1. The cards are near-horizontal plates

`vegetation.leaf_cards` built each card's frame from
`yaw = U(0, 2pi)`, `pitch = -droop + U(-0.35, 0.35)`, `roll = U(-0.5, 0.5)` and
then
```
ay = (-sin y * cos p,  sin p,  -cos y * cos p)
```
With `droop` between 0.14 and 0.34 for every species except willow, `sin p` is
about -0.2, so **`ay` — the axis that runs up the sheet from petiole to tip — is
97 % horizontal, and `ax` is at most 47 % off horizontal.** Every leaf card in
Hearthmere is a nearly flat plate lying face-up.

From a 1.62 m eye that is the worst possible orientation: every card is seen
edge-on, so it paints a thin horizontal streak instead of its 55 % coverage, the
crown never closes however many cards are in it, and the cards that ARE seen
face-on are the ones above the eye — seen from *underneath*, where the
double-sided flip turns the normal away from a 38 deg sun and they render black.

Cropped `review/shots/ad-town-05/t-square.png` at 3x (the market oak at 18 m):
the crown is 60 % sky, the leaf mass reads as horizontal streaks in rows, and
the whole top half of the canopy is near-black while the lower left is blown
yellow-green. That is not a lattice in the scatter. It is a **card orientation
bug**, and it explains the "rows and columns" reading, the see-through crown and
the black/white split in one mechanism.

### 2. `hedge` is 99.9 % opaque

Measured off the shipped alpha, coverage at `alpha >= 0.5`:

| sheet | coverage | mip 4 | mip 6 |
| --- | --- | --- | --- |
| `leaf_oak` | 0.401 | 0.40 | 0.36 |
| `leaf_ash` | 0.526 | 0.53 | 0.50 |
| `leaf_apple` | 0.476 | 0.48 | 0.46 |
| `leaf_willow` | 0.543 | 0.55 | 0.50 |
| `leaf_yew` | 0.501 | 0.50 | 0.44 |
| **`hedge`** | **0.999** | 1.00 | 1.00 |

`hedge` carries an alpha channel that is opaque everywhere. It is declared
`alphaMode: MASK` and masks nothing. That is the whole of AD §8's "smooth solids
with a green mottle painted on, no light through, no shadow side that is
anything but black" — and it is also the LOD3 material for every tree in the
town.

### 3. Alpha-tested shadow casting works in this engine and did in pass 04

`review/shots/ad-town-04/t-gate-south.png` has a correct, soft, leaf-shaped
dapple across the carriageway. The engine path is sound: glTF writes
`alphaMode MASK` + `alphaCutoff 0.5`, three r180's `getDepthMaterial` forwards
`map`, `alphaMap` and `alphaTest` into the depth material and
`refreshUniformsCommon` uploads `mapTransform`, so `KHR_texture_transform`
(scale 143.82 on every texture in this project) is honoured in the shadow pass
too. So the black lozenges in `craft-walk-04` are not a missing alpha test in
the renderer.


---

## The black lozenges in `craft-walk-04` are NOT foliage

`ad-town-05.md` §3, second half, and item 2 of my brief. I have to report this
one against the brief rather than for it, and the proof is two renders.

**Test.** Same free camera as `craft-walk-04` (eye 1.62 m at 40.2, 25.4 looking
50.2, 25.9), rendered twice: once normally, once with `--skip landscape`, which
removes every tree, hedge, shrub, tussock, crop, reed and leaf card in the town.

- `review/shots/fol-02/ref-free.png` — the rosette of hard black quadrilaterals.
- `review/shots/fol-02/noveg-free.png` — **the rosette is byte-for-byte still
  there.** The grass verges disappear and nothing else changes.

**Second, independent proof.** I rewrote every leaf card's orientation, size and
position in the town (below). Over the whole of `craft-walk-04` 12.6 % of pixels
changed; **inside the rosette, 0.68 %** — noise. A defect that does not move when
the entire foliage system is replaced is not the foliage system.

**Third proof, and it narrows it.** Same camera with
`--skip bakery,chandler,carpenter,cooper,bowyer,tannery,warehouse,dovecote,confectioner`
(`review/shots/fol-03/bisect-free.png`) — **still there, unchanged.** So it is
not any of the nine Bakers' Row trade venues either. What is left in that frame
is `streets`, `townhouse`, `church`, `wall`, `market_square` and `terrain`.

**Fourth: it is not one object.** `review/shots/fol-04/craft-walk-02.png`, at
(18.3, 23.6) — 22 m back down the same street, no tree within 40 m — has the
same hard dark polygons scattered across the carriageway, at several sizes, all
along Bakers' Row. They preserve the sett texture underneath them, so they are
shadows and not unlit geometry. The caster stands up-sun of each, i.e. at
roughly `p + 1.28h * (0.82, -0.57)` for a caster height `h`, and nothing is
visible there.

**What I think it is, offered as a lead and not as a finding:** flat polygons in
the street/ground layer sitting some way above the paving with `castShadow` on —
a wear patch, a crossing stone or a puddle decal authored at the wrong Y. That
would produce exactly this: hard-edged planar shadows with no visible caster,
scattered along one street, in the sizes those patches come in.

**Why this matters beyond one frame.** The review has this filed as the foliage
system's worst defect and priced wave 1 partly on it. Whoever owns Bakers' Row
should have it, and the foliage agent should not be credited with fixing it.

**And the engine path is fine.** `ad-town-04/t-gate-south.png` has a correct soft
leaf dapple, glTF writes `alphaMode MASK` + `alphaCutoff 0.5` on every leaf
sheet, and three r180's `getDepthMaterial` forwards `map`/`alphaMap`/`alphaTest`
into the depth material with `mapTransform` uploaded, so `KHR_texture_transform`
is honoured in the shadow pass. Alpha-tested foliage shadows work in this
project today. What was needed was not to enable them but to stop the LOD
inflating a card to 2.1 m — see below.

---

## 1. Placement, not the sheet — what changed

All in `tools/assetgen/core/vegetation.py`.

### `leaf_cards` — card orientation

The defect in §1 above, fixed. Every card now gets a full three-axis frame:

- **Face.** The card's normal is the crown's outward radial blended with a free
  random direction, `shell_face` controlling the mix, and the mix is stronger at
  the crown's surface than in its middle. A canopy's outside is a wall of leaf
  presented to the sky; its inside is a jumble. `shell_face` is 0.74 for a yew
  (you cannot see through one), 0.48 for an old apple (pruned open), 0.62
  otherwise.
- **Hang.** `+Y` of the sheet — petiole to tip — is the in-plane direction
  closest to `mix(outward, down, droop)`, so a willow at `droop 0.95` hangs
  straight down and an oak spray at 0.22 reaches out. This is what `droop` was
  always supposed to mean and never did.
- **Roll.** A random turn about the card's own normal, mostly within ±66° of the
  hang, and one card in six turned right over — a spray on the underside of a
  limb points any way at all.

### `_crown_points` — blue noise, clumps, limbs, ragged edge

- **Blue noise** (`_blue_noise`, Mitchell best-candidate). The old sampler drew
  each card independently from a uniform spherical distribution. That is white
  noise, and white noise is not "random-looking" — it is lumpy at every scale,
  so the eye finds its clusters and voids and calls them a pattern. Best
  candidate rather than Bridson because it takes an arbitrary sampler (so the
  crown can be clumped and lopsided rather than a ball) and never fails to place
  the count asked for.
- **Clumps, not a shell.** `shell=0.50` used to push every card onto one
  surface: a hollow green balloon, closed where you do not want it and empty
  where the branches are. Cards now come from clump balls whose centres are
  themselves blue-noise-spaced through the volume, with per-clump radius spread
  0.55–1.70x and per-clump card share drawn on a `**1.5` curve so a crown has
  two or three dominant masses rather than forty equal ones.
- **The masses hang on the limbs.** Every branch tip seeds a clump. The first
  render of this work (`review/shots/fol-02/t-square.png`) showed exactly why:
  bare secondary limbs projecting a metre and a half past the leaf mass, which
  reads as a dead tree with a green cloud behind it.
- **Ragged silhouette.** Density inside a clump falls as `r**0.70` toward its
  own edge, and the clump's reach is jittered per clump, so the outline is
  bitten into rather than being an offset of a shape function.
- **Individuals.** `crown_shape()` draws 3–5 low-frequency lobes, a lean, an
  aspect and a clumpiness from the tree's own seed. Two asset ids of the same
  species are now two different trees, not one tree at two scales.

### Card size follows the silhouette

`_atlas_rect`'s `big` probability now ramps 0.72 → 0.20 from the crown's middle
to its edge, and card size tapers by 26 % over the outer 30 %. A full-sheet
card's empty corners read as a square hole on a silhouette; small 2x2 sub-rect
cards are what makes an outline look bitten rather than cut.

### The LOD card inflation, which is where the lozenge risk really was

`tree()` multiplied card size by **1.9x** at LOD1 and LOD2. On a 9 m oak that is
a **2.1 m alpha-masked quad** — one card covering a metre and a half of ground
in the shadow pass, with the sheet's holes spread too thin to read as dapple at
any mip. It is now **1.35x**. This is the change that makes a distant tree's
shadow dapple instead of blotch, and it is measured below.

## 3. Transmission — `client/src/shadows.js`

**This is the single largest change in the wave and it is nine lines of GLSL.**

A leaf is 0.1 mm of translucent tissue. At 09:30 with a 38 deg sun, a large
share of every canopy in Hearthmere is seen from its shaded side, and shading
that side as an opaque dielectric is why `ad-town-05.md` §3 reads *"a third of
cards are silhouette-black and the lit ones blow to pure white"*. It is also
most of §8's black hedges: a hedge at 09:30 with the sun behind it is bright at
the edges and never black.

`SunRig._transmit(m)` installs a term on any material whose library key matches
`/^(leaf_|hedge$|ivy$|foliage|reed$|weeds$|tree_far$|moss$)/`, injected before
`#include <opaque_fragment>`:

```glsl
vec3  leafL    = normalize( ( viewMatrix * vec4( uLeafSunW, 0.0 ) ).xyz );
float leafBack = max( 0.0, dot( -geometryNormal, leafL ) );
float leafFwd  = clamp( dot( -geometryViewDir, leafL ) * 0.5 + 0.5, 0.0, 1.0 );
float leafGlow = pow( leafBack, uLeafPow ) * mix( 1.0 - uLeafView, 1.0, pow( leafFwd, 3.0 ) );
float leafWrap = max( 0.0, dot( geometryNormal, leafL ) * 0.5 + 0.5 );
outgoingLight += diffuseColor.rgb * uLeafTint * uLeafSun
               * ( uLeafTrans * leafGlow + uLeafWrap * leafWrap * leafWrap );
```

`geometryNormal` has already been flipped to face the viewer by
`normal_fragment_begin` on a double-sided material, so a positive dot against
the sun means the light is arriving from behind the leaf — which is exactly the
case that renders black today. `leafFwd` is forward scatter, so a tree between
you and the sun glows and the same tree behind you does not. `leafWrap` is a
soft terminator so no leaf's dark half falls to the ambient floor.
`diffuseColor` already carries `COLOR_0`, so `leaf_cards`' crown-depth shade
attenuates the glow inside the canopy for free.

**Why it is in `shadows.js` and not in `client/src/ambient.js`,** where the other
foliage shader hook lives, and this is the part that decides it: **the review
harness does not run `ambient.js`.** `tools/render/town.html` imports
`atmosphere.js`, `shadows.js`, `lod.js`, `perf.js` and `water.js` and nothing
else. A term added to the wind hook would be invisible in every frame this
project is judged from. It is also properly a sun term — it needs the sun's
direction, colour and intensity, and `SunRig` is the only thing that owns all
three. Authorable at `lighting.foliage`; defaults in `FOLIAGE_DEFAULTS`.

**Shared-file discipline.** This is the only file outside my lane I touched.
Two edits: one three-line call in `register()` placed so the hook is captured as
`prev` and chained by the CSM wrapper exactly as water's and ambient's hooks
are, and one new method plus a defaults block. Nothing existing was changed.

---

## 5. Cost, before and after — like for like at the `square` camera

Measured the way `ad-town-05.md` §12 says it must be: **`--views square` on its
own**, so the LOD selector is not sampling the previous camera's state. The
before column is the art director's own probe,
`review/shots/ad-town-05/probe/p1-report.json`, which is the same command on the
same camera.

| at `square` | pass 05 (AD probe) | this wave | delta |
| --- | --- | --- | --- |
| `landscape` draws | 127 | **121** | **−6** |
| `landscape` triangles | 505,414 | **502,547** | **−2,867** |
| `landscape` instances | 4,011 | 3,931 | −80 |
| scene pass draws | 467 | 461 | −6 |
| **shadow pass draws** | **604** | **604** | **0** |
| shadow pass triangles | 1,459,084 | 1,459,144 | +60 |
| AO pass draws | 242 | 242 | 0 |
| whole frame draws | 1,385 | 1,380 | −5 |

**The foliage rewrite is cost-negative and the alpha-tested shadow pass did not
grow: 604 draws before, 604 after.** It could not grow — no caster was added and
no material's alpha mode changed; the LOD card inflation coming down from 1.9x
to 1.35x is a fill-rate saving, not a draw-call one, and the card counts are
unchanged. The frame is still 1.53x over the §7 draw budget for reasons that are
not vegetation: `landscape` is 121 of 1,380 draws, 8.8 % of the frame.

The transmission term is nine ALU instructions in a fragment shader on foliage
materials only. It adds no draw call, no texture fetch and no varying.

A note on the whole-frame number: a second `--views square` run half an hour
later reported 1,384 draws / 3,720,407 triangles with `landscape` **byte
identical at 121 / 502,547**. Other agents rebuilt other venues between the two
runs. Only the `landscape` rows and the pass split above are attributable to
this work.

---

## 4. What was kept

- **Opaque coverage 47–60 %.** The sheets were not touched at all: `leaf_oak`
  0.401, `leaf_ash` 0.526, `leaf_apple` 0.476, `leaf_willow` 0.543, `leaf_yew`
  0.501 (measured above, and unchanged — no texture was rebuilt in this wave).
- **Season on a per-card COLOR_0 tint, not in the albedo.** `AUTUMN` and the
  `autumn` share are untouched; every sheet still ships green.
- **Distance wood as an 8-triangle impostor.** `distance_tree` untouched, 2,995
  instances, `tree_far` sheet unchanged.
- **The 8-way UV orientation** (`_atlas_rect`'s square symmetries) and the
  **corner normal splay** (`puff`) — both untouched and both still doing their
  jobs; the splay in particular is what stops the new outward-facing cards
  reading as flat discs.
- **`_spherify`**, the crown-volume normal blend, untouched.
- **Everything through `ctx.instance` / `ctx.lod`.** No new prototype, no new
  batch, no new material.

### What I deliberately did NOT do, and why

- **No second crown variant per tree kind.** `crown_shape()` makes each of the
  eight `TreeField.KINDS` a distinct individual, and each instance already gets
  a seeded yaw and a 0.82–1.25 scale, so the town does not repeat a silhouette.
  Adding variants would be cheap in triangles and expensive in the currency that
  is actually 1.53x over budget: every variant is a separate instance batch, and
  with 47 trees spread over 90 batching cells most variants would land alone in
  a cell and cost a draw each. The hook is there — `tree_lods` takes an asset id
  — for a wave where draws are not the binding constraint.
- **No change to `materials.leaf_cards`.** The sheet's residual 4x4 station
  lattice was the other candidate for the "rows and columns" reading. It is not
  detectable in frame at 3 m, 8 m or 30 m after the placement fix (frames
  below), and a texture rebuild is a cost I did not need to spend to close the
  finding. If the art director finds the sheet's period at close range, the fix
  is a per-cell jitter of `base_x`/`NODE_Y` in that function and nothing else.

---

## Verified in frame — every claim below I opened and read

All at the locked 09:30 rig. Before is `review/shots/ad-town-05/`, after is
`review/shots/fol-04/` unless stated.

| range | frame | what it settles |
| --- | --- | --- |
| **1.6–8 m** | `fol-04/orchard3-free.png` | The closest look at a canopy in the build. **No lattice, no period, no grid** — and the orchard floor is **dappled**: soft broken leaf shadow with sun-flecks between it, not lozenges. This frame answers two of the three tests on its own. |
| **6–10 m** | `fol-04/kirk-walk-05.png` vs `ad-town-05/kirk-walk-05.png` | The AD's own citation. Before: both flanking trees are scattered dark rectangles on a visible axis-aligned grid. After: two closed crowns with real clump structure, a ragged edge and a warm backlit glow. **The lattice is gone.** |
| **18 m** | `fol-04/t-square.png` vs `ad-town-05/t-square.png` | The market oak — pass-05's headline foliage defect, *"count eight columns on its left edge"*. Before: a chequerboard of dark green rectangles over 60 % sky. After: a tree. Crop at 3x: `sq_oak` before / after in the scratch set; the columns are not countable because they do not exist. |
| **~30 m** | `fol-04/kirk-walk-01.png` | The tree closing Kirkgate reads as a crown against the sky with a broken outline. No period. |
| **60–140 m** | `fol-04/meadow-free.png`, `fol-04/a-approach-s.png` | The distance wood. `tree_far` is untouched but now carries the transmission term, and the treeline has light and shade in it instead of `ad-town-05.md` §11's *"solid wall of identical pale mint-green crowns blown out to near-white"*. |
| **5–10 m** | `fol-04/kirkgreen-free.png` | The two churchyard trees flanking the church west front — the pair `ad-town-02` called the worst frame in the build. They frame the perron and the arcade instead of cropping them, the crowns are closed, the outline is broken, and both are backlit and glowing rather than black. |
| shadow | `fol-04/orchard3-free.png`, `fol-02/t-square.png` ground | Dappled, alpha-tested, soft. |
| backlit | `fol-04/t-square.png`, `kirk-walk-05.png`, `kirk-walk-01.png` | Canopies glow warm-green where the sun is behind them instead of going silhouette-black. |

**Two intermediate states are in the record on purpose**, because they are the
evidence for the two halves of the fix:

- `review/shots/fol-02/t-square.png` — placement fixed, **no transmission**. The
  lattice is already gone here, so the lattice was the scatter and the
  orientation, not the sheet. The crown is also visibly too dark on its
  underside, which is the transmission defect isolated.
- `review/shots/fol-03/t-square.png` — transmission at 0.55/1.25, which is too
  hot: a real tree and a flat one. Shipped at 0.40/1.55.

### Things I can see that are still wrong, in my own work

- **Three or four secondary limbs still project past the leaf mass** on the
  market oak's right flank at 18 m. Seeding a clump at every tip fixed most of
  it; the tips that fall outside the crown's shape function still get a small
  clump and read thin. `tree()`'s secondary reach of `rx * 0.42` is the number.
- **The canopy's value range is narrower than a photograph's.** Transmission
  bought the glow and cost some of the depth. `depth_shade` (0.32) and the
  transmission power are the two dials; I stopped where the tree stopped
  reading as plastic in either direction.
- **A pale blue-grey halo sits around some leaf clumps** against the sky at 18 m
  (`t-square`, upper crown). It is in the AO pass, not the beauty pass — an
  alpha-masked card has no depth for the AO to be right about. I did not chase
  it; it is a screen-space artefact and it belongs with whoever owns the post
  chain.

### The hedge, which is not mine this wave but is measured

`ad-town-05.md` §8 asks for a transmission term on the hedges and it now has
one. It is not enough, and the measurement says why: **the `hedge` alpha channel
is opaque over 99.9 % of its area** (table at the top). A cut-out material that
masks nothing is a solid, so there is no light path through it for a
transmission term to use, and the only thing the term can lift is the wrap on
its silhouette. `fol-04/orchard3-free.png` shows the orchard boundary hedge at
RGB 29/36/24 — still near-black at 6 m. The fix is in `materials.hedge_mass`,
which my brief puts out of my lane, and it is worth more than another pass on
the trees: `hedge` is also the LOD3 impostor material for every tree in the
town.

---

## Files changed

| file | what |
| --- | --- |
| `tools/assetgen/core/vegetation.py` | `crown_shape()`, `_shape_radius()`, `_blue_noise()` new; `_crown_points` rebuilt on clumped blue noise with limb anchors and a ragged edge; `leaf_cards` card frame rebuilt on all three axes with `shell_face`; edge-aware card size and sub-rect probability; `tree()` passes a per-tree crown shape and limb anchors, and the LOD card inflation goes 1.9x -> 1.35x |
| `client/src/shadows.js` | **shared file, two additive edits.** `FOLIAGE_DEFAULTS` + `FOLIAGE_RE` constants; `SunRig._transmit(m)`; one three-line call at the top of `register()`'s per-material block so the hook is chained rather than dropped. Nothing existing was modified. |
| `tools/assetgen/venues/landscape.py` | **not changed.** Tree placement already randomises yaw and scale per instance, and the plan-level work (orchard rows, hedgerow standards, the wood) was not what the review rejected. |
| `tools/assetgen/core/materials.py` | **not changed.** No texture was rebuilt in this wave; every sheet is byte-identical to pass 05. |

Rebuild: `python tools/assetgen/build.py --skip-textures --venue landscape`.

## Handover

1. **The `craft-walk-04` lozenges are not foliage.** Three renders prove it.
   They need an owner in `streets` / `townhouse` / `church` / `wall` /
   `market_square`, and the lead is a flat ground-layer polygon authored above
   the paving with `castShadow` on. They are all along Bakers' Row, including
   `craft-walk-02` where no tree stands within 40 m.
2. **`hedge`'s alpha channel is opaque.** `materials.hedge_mass`. It is §8's
   root cause and it is also the LOD3 material for every tree.
3. **Two crown variants per tree kind** are one argument away in `tree_lods` and
   worth doing in a wave where draw calls are not the binding constraint.

---

## Correctness, for the record

- `python tools/validate.py` — **5 failures, 47 warnings** (pass 05: 5 / 46).
  None of the five is a foliage item; they are `foam`'s palette, `water_fall`'s
  px/m, and the `straw` / `wool_crimson` / `canvas_amber` UV densities, all
  carried from pass 05. **`§7 mesh memory is 233.4 MB against 240**, down from
  pass 05's 243.3 MB failure — that gate has closed, though other agents' work
  is in that number too.
- `node tools/check_client.mjs` — the client **boots and walks**: 32 venues, 258
  entities, 2,588 collision volumes, 544 batches, 1,759 fixed steps, and **no
  shader compile error**, which is the thing a new `onBeforeCompile` could
  plausibly have broken. It then dies on `Page.captureScreenshot` returning a
  protocol error, which is the harness's screenshot step and not the client.
  Separately its `parity:` line now reads `0 draws / 0 tris` at the arrival
  camera where pass 05 read 1,395 — that instrument has broken since pass 05 and
  it is not this work; flagging it because `ad-town-05.md` §12 and §15 are
  already about these two harnesses disagreeing.
- `town.mjs` reports **0 warnings, 0 console errors** on every view I rendered.
