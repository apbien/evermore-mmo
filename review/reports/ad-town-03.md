# Art-director review — Hearthmere, whole town, pass 03

**Verdict: REJECT.**

Reviewed 2026-08-01 against `docs/ART_BIBLE.md` §8, `docs/BUILD_DIRECTIVE.md` §3
(arrival), §4 (geography), §6 (structure) and §9 (done). **88 frames rendered by
me at the locked 09:30 rig into `review/shots/ad-town-03/` and read as PNGs**,
plus eleven crops and the shipped albedo sheets of nine materials read directly.
I did not review from source: where a line number appears below I opened the file
only *after* an image told me what to look for. I did not take any build agent's
self-assessment — three of this wave's claims are contradicted by the renders and
are named. One of pass 02's own findings was mis-attributed by me, the build
agent fixed the function I named, and the defect is still on screen; that is
§1 and I own it.

Frames read: `t-plan`, `t-aerial-ne/nw/sw/se`, `t-arrival`, `t-square`,
`t-silhouette`, `t-gate-north`, `t-gate-south`; `spine-walk-01..11` (bridge →
north gate → Ford Road → market place); `south-walk-01..08` (market place → south
gate); `wharf-walk-01..09` (Wharf Lane → water gate → quay → Fishers' Steps);
`kirk-walk-01..09` (Kirkgate → Kirk Green → market place); `craft-walk-01..08`
(Bakers' Row); `sty-walk-01..06` (Sty Lane); `alley-walk-01..06` (Bell Alley →
Smiths' Lane); `mere-walk-01..08` (Mere Street → West Lanes);
`bailey-walk-01..07` (The Bailey); plus six cameras I authored because the
harness could not answer the standing questions: `westfront-free` (church west
front from Kirk Green), `kirkgate2-free`, `fordlook-free`, and the three approach
silhouettes `approach-s-free`, `approach-ne-free`, `approach-w-free`.

---

## The verdict, stated plainly

**The build moved further this wave than in any wave before it, and it is still a
REJECT.** 32 venues placed, 0 missing, ~70 masses, and `t-plan` reads for the
first time as a settlement plan rather than a doughnut round a hole. The trees
are trees. The streets are paved. There is air in the picture. `spine-walk-03`,
`spine-walk-06`, `t-gate-south`, `sty-walk-03` and `approach-ne-free` are frames
I would not be embarrassed to show.

But blind, side by side against Divinity's Reach, Gridania, Ul'dah and
post-Legion Boralus, **no frame in this build would be mistaken for a shipped AAA
MMO**. The reasons have narrowed from twenty-one structural problems to about
six *surface* problems, and every one of them is cheap:

1. **Half the masonry in the town is green-jointed crazy paving, and it is not
   the function anybody has been fixing.** §1. This alone would move the verdict
   further than anything else on the list.
2. **The intramural ground blend is a quilt of opaque axis-aligned rectangles.**
   §2. `bailey-walk-04`.
3. **The town still has no skyline, and the church tower is invisible from
   everywhere.** §3.
4. **The aerial perspective is over-driven by roughly 2×.** §4.
5. **The roofscape is still a checkerboard**, for four reasons that are all in
   thirty lines of one function. §5.
6. **The waterfront of a lake town has no boats.** §7.

Three claims in this wave's reports that the renders do not support:

- ATMOSPHERE: *"The Mere goes from a solid white disc to a lake."* It does not.
  `t-aerial-sw` is still a mathematically perfect ellipse whose far half is a
  **pure white specular blowout** inside a uniform-width beige beach ring;
  `approach-ne-free` shows the sun path clipped flat white across a third of the
  frame with visible polygon facet edges in the glitter.
- ATMOSPHERE: *"Roofs — dealt by district → 26 m block → wealth."* The code at
  `core/building.py:486` is good and the intent is right, but `t-plan` and all
  four aerials show **no visible clustering whatever**. Mechanism at §5.
- GATES: *"rubble … clearly a wall now."* Half true and it does not matter — the
  rebuilt `rubble` is real work, but the crazy paving on screen is a *different
  material*. §1.

---

## The three questions asked, answered directly

### (a) Does the arrival frame from the altar deliver BUILD_DIRECTIVE §3?

**Closer than it has ever been, and still no.** `t-arrival`, crop at
`crop/arr-aperture.png`.

| §3.2 requires | in `t-arrival` |
| --- | --- |
| the descending church steps | **yes** — the perron cheeks and balustrade read, and the eye is led |
| a street leading the eye | **yes** — the market place opens; the half-timbered jetty at frame-left gives the composition a wall |
| the market fountain as the focal point | **no** |
| ≥ 2 other venue anchor silhouettes | **partly** — one chimney and one tiled gable; no guild tower, no forge chimney, no gatehouse |

The aperture is ~40 % of frame width and its content is a real street scene, not
a blank gable. That is this wave's achievement and it is genuine.

What stops it:

- **The fountain does not hold the centre.** `_fountain`
  (`venues/market_square.py:113`) now builds a pillar and a heron, but the beak
  lands at **y ≈ 3.0 m** (`pillar` tops at 2.14, `body` +0.48, neck +0.40, `beak`
  at 2.94). I asked for 4.5–6.0 m to the finial. At 43 m that is ~4 % of frame
  height and the object my eye actually lands on is a long dark hull-shaped mass
  in front of it.
- **The fountain is built in the same material as the ground it stands on**
  (`crop/fountain.png`) — the whole object, basin, step rings and pillar, is the
  crazy paving of §1 at the same value as the paving around it, so it has no
  edge and visually dissolves.
- **The water in it can never be seen.** `K.water_disc(2.10, y=0.62, depth=0.24)`
  sits 0.28 m *below* a 0.90 m lip on a 2.1 m bowl. From a 1.62 m eye the
  sight-line over the lip clears the water only inside about 8 m. From 22 m
  (`kirk-walk-09`) and from 43 m (`t-arrival`) the town's focal point is a dry
  stone drum.
- **Two thirds of the frame is still crazy-paving masonry** (§1), and the market
  place ground inside the aperture is a flat featureless beige plane past ~15 m.
- A saturated blue-teal wedge sits between the buildings at frame-centre-right
  and reads as a hole in the geometry.

### (b) Does the silhouette read as a town with a skyline?

**No.** And I could not get that answer out of the harness, which is a finding in
itself.

`t-silhouette` is unusable: the black-on-white ortho north elevation is dominated
by a grey horizon plate that occludes the town, and the church tower appears as a
**detached black mass floating 11 m above the town line** (measured at 8 px/m)
with four smaller unattached specks beside it. Whether the tower is genuinely
detached or its stem is hidden behind nearer terrain, **the instrument cannot
tell me** — which means nobody has actually tested the silhouette since pass 02.

So I shot three approach cameras myself:

- **`approach-s-free`** (0, 138 → 0, 0, eye 6 m — the canonical return from the
  quest zones): Hearthmere is a **flat grey strip ~40 px tall**, no tower, no
  spire, no gatehouse, no vertical hierarchy. A 21.95 m church tower should be
  130 px in this frame. It is not there.
- **`approach-ne-free`** (across the Mere): the **best** profile in the build —
  the wall, two capped drum towers, the warehouse gable and the treadwheel crane
  make a real skyline. The tallest object on it is the crane. The church is
  invisible.
- **`approach-w-free`**: nothing above the wall line.

Against the wall specifically, nothing moved: `content/town/hearthmere.json →
wall` still authors 5.2 m to the walk + 1.1 m parapet, and in `bailey-walk-04`,
`wharf-walk-05` and every aerial the enceinte is a low ribbon whose towers stand
2–3 m proud of the curtain. Divinity's Reach and Ul'dah are at 15–25 m for
exactly this reason.

### (c) Does it read as one world, or as many agents' work bolted together?

**Still several agents' work — but the seams are now *surface* seams rather than
structural ones, which is progress and is why they are cheap to close.** Each
named with its frame:

- **The enceinte is four different masonry treatments.** `t-gate-north`: blocky
  ashlar curtain, speckled-mottle drum towers, giant-plate parapet.
  `bailey-walk-04`: over-chamfered "foam block" cobble right, **a completely
  featureless beige plane over a ~30 m run** in the middle, grey blockwork left.
  `mere-walk-05` and `south-walk-04`: the same featureless beige on the gate
  cheeks. `wharf-walk-05`: crazy paving. Pass 02 said three; it is four, and one
  of them reads as untextured.
- **One texture is doing wall, plinth, steps, market paving and road.**
  `kirkgate2-free` shows all five in one frame. §1.
- **The ground is three unrelated systems in one 12 m span.**
  `crop/ground-quilt.png`: fine grey cobble, pale crazy paving, and the green
  rectangle quilt, meeting at hard axis-aligned edges.
- **Thatch is two different materials.** `spine-walk-06` top-left has a real
  brown straw coat with depth (fixed). `mere-walk-05` left *and* right are
  **smooth pale cream membranes with knife-edge eaves** — pass 02 §4 verbatim,
  unchanged. `south-walk-04` the same.
- **One building in the town is fire-engine crimson.**
  `venues/confectioner.py:62 PAINT = "painted_crimson"`, at (20.5, 12) on the
  market place's east frontage — timbers, barge boards, door, jambs, shopfront.
  It is the only saturated hue in the built fabric and it is 30 m from the
  arrival axis. `spine-walk-09`, `t-square`.
- **Green is the material of last resort in five places.** §14.

---

## Pass-02 findings — status, with the frame that proves it

| # | pass-02 finding | status | proof |
| --- | --- | --- | --- |
| 1 | 18 of 32 venues do not exist | **FIXED** | `t-report.json` → `missing: []`; 32 placed; `t-plan` is a full town. The achievement of the wave. |
| 2 | leaf atlas incapable of a tree | **FIXED** | `t-square` market oak, `spine-walk-09`, `sty-walk-03`. All green, real canopies, no autumn confetti at 09:30. |
| 3 | yew is a 28-face polyhedron | **PARTLY** | `vegetation.py:341` now `rings=7, segments=16`; `westfront-free`'s churchyard trees are card canopies. But `kirk-walk-06` still shows a **faceted low-poly sphere floating over a wall**, and at LOD0 the cards are 1.5–2 m pinnate fern fronds (§8). |
| 4 | thatch is a smooth cream membrane with a knife-edge | **PARTLY** | fixed in `spine-walk-06`; **not** fixed in `mere-walk-05` (both roofs) or `south-walk-04`. |
| 5 | no fog / aerial perspective | **FIXED, then over-driven** | present in every frame; now a defect in the other direction — §4. |
| 6 | fountain 0.90 m, must anchor at 43 m | **PARTLY** | ~3.0 m with a heron, still 1.5–3.0 m short, still built in its own ground's material, water geometrically invisible. §(a). |
| 7 | no skyline; tower detached; four floating masses; wall too low | **NOT FIXED** | `approach-s-free`, `t-silhouette`. `landscape.gltf` still **y ∈ [−5.90, +28.29]** = 34.2 m tall, 6.3 m over the church; `gates.md` §4 found the same number independently and nobody has looked at it. |
| 8 | Mere a stamped ellipse; Emberflow a rectangle; water blows to white | **PARTLY / NOT FIXED** | `t-aerial-sw` (ellipse + **white blowout** + uniform beach ring), `t-plan`/`t-aerial-se` (parallel-sided canal), `t-gate-north` (**hard sawtooth bank** unchanged). Progress: near water now has a depth gradient and a ripple. |
| 9 | `rubble` is crazy paving with green mortar | **NOT FIXED — and mis-attributed** | See §1. `rubble` was genuinely rebuilt; the crazy paving on screen is `stone`, `limewash` and `ivy`. `kirkgate2-free`, `crop/tex-sheet.png`, `crop/market-paving.png`. |
| 10 | three masonry materials on one run of wall | **NOT FIXED — now four** | `t-gate-north`, `bailey-walk-04`, `mere-walk-05`, `wharf-walk-05`. |
| 11 | everything inside the wall is bare brown dirt | **PARTLY** | genuinely greener, streets paved — implemented as the rectangle quilt. §2. |
| 12 | church west front blank; nave black; tower off-axis | **PARTLY** | `westfront-free`: perron reads, portal real, trees frame instead of crop. **No tower in frame. No west window** — 8 m of blank wall over the arch. The nave is no longer black; it is a **blank pale wall** with a small altar, no east window, no arcade, no light shafts, no worn path. |
| 13 | no AO; 21 px/m shadows | **PARTLY** | GTAO is in and softens junctions. The 1.75 m figure has **zero contact darkening** (`crop/figure-shadow.png`); wall bases meet ground with no occlusion (`wharf-walk-05`); `t-arrival`'s floor shadow is a **stepped blocky polygon** — shadow resolution unchanged. |
| 14 | one green mottle doing daub, hedge and ground | **NOT FIXED** | `crop/green-daub.png` — and the cause is now known: it is `ivy`, an opaque green Voronoi sheet with no alpha. §14. |
| 15 | a hedge stands in Kirkgate and swallows the camera | **NOT FIXED — worse** | `kirk-walk-06` at (26.3, −17.1): **80 % of the frame is the inside of a tree**, on a public street on the church-to-market route. `check_walkable` still passes 15/15. |
| 16 | large black unlit polygons in three frames | **FIXED** | none in 88 frames. |
| 17 | crude LOD at 25 m; lanes lose their road surface | **PARTLY** | LOD popping no longer visible at 25 m. Sty Lane has a surface (`sty-walk-03`) — the surface is the brown rectangle quilt. |
| 18 | cloth and ivy are flat single-sided quads | **NOT FIXED** | `crop/washing.png`: five perfect rectangles, dead-straight hems, no sag, no peg pinch, no thickness, **two still saturated orange**. The rope got its catenary; the cloth did not. Ivy is §14. |
| 19 | landscape spends 83 % of triangles; fields a radial spiderweb | **PARTLY / NOT FIXED** | triangles down to **1.24 M of 3.97 M (31 %)** — real work, credit due. Fields **still radial-and-concentric** (`t-plan`, `t-aerial-sw`, `t-aerial-se`), and in 3D the hedges are solid dark-green extruded ribbons with a sine-wave top edge (`approach-s-free`). |
| 20 | composition defects in the hero cameras | **NOT FIXED** | `t-square`: the lamp **still bisects the frame** dead centre and crops the fountain. `t-gate-north`: **still** off-axis and low, parapet filling the right half, arch in a ~150 px gap. `spine-walk-01`: camera **still inside the bridge deck** — an entirely brown frame. |
| 21 | roof distribution reads as a checkerboard | **NOT FIXED** | `t-plan`, all four aerials. Mass count is now good (~70 vs §5's 75–95); the clustering is not. §5. |

**Score: 3 fixed · 9 partly · 9 not fixed.**

---

## Findings, ordered by how much they damage the frame

### 1. The crazy paving is `stone`, `limewash` and `ivy` — not `rubble`. Nobody has fixed it because pass 02 named the wrong function

**This is the single highest-value finding in the report and it is my error to
own.** Pass 02 §9 blamed `materials.py rubble_weathered()`. GATES faithfully
rebuilt that function on `materials.coursed` — and it worked: I read
`assets/textures/rubble_albedo.png` directly and it now has bed lines and strong
per-stone value spread. It also changed nothing on screen, because **the material
actually covering the church, the fountain, the plinths, the steps and the market
paving is a different key.**

I read the shipped albedos (`crop/tex-sheet.png`):

- **`stone` → `foundation_stone()` at `materials.py:1092`.** Docstring says
  "Coursed rubble plinth". The code is `worley(s, 6, seed+81)` plus
  `worley(..., metric="f2f1")` — *two interleaved Worley fields*, which is
  **isotropic by construction**: random polygons with zero bedding. That is
  word-for-word the failure `rubble_weathered`'s new docstring describes and
  fixes. Worse, the value variation at `:1101–1102` is `fbm(s, 12)` and
  `fbm(s, 9)` — **independent noise fields not keyed to the Worley cell id** — so
  the "per-stone" variation blurs *across* stones and every stone comes out the
  same value. This is `LIBRARY["stone"]`, the generic default masonry key, and it
  is the 4th material in `townhouse.gltf`.
- **`limewash` → `limewashed_stone()` at `materials.py:2199`.** Same
  construction, `worley(s, 9, seed+371)`, and the wash coats it without breaking
  it. This is the pale market paving in `crop/market-paving.png` — every cell the
  same value, and **the joints are olive green** from `cavity_dirt(edges…)`.
- **`ivy` → `ivy()`.** `crop/tex-ivy.png`: an **opaque green Voronoi crazy paving
  with no alpha cutout and no leaf shapes at all.** §14.

**Frames:** `kirkgate2-free` (crop at `crop/rubble-wall.png`) — at 5 m, *every*
masonry surface in the frame is this, with no bedding and no value difference
between adjacent stones. `crop/market-paving.png` — the market place, green
joints, uniform value. `crop/fountain.png` — the town's focal point.
`t-arrival` — ≈60 % of the pixels in the most important composition in the build.
`westfront-free`, `wharf-walk-07`, `kirk-walk-09`.

Two further materials found the same way and worth naming while somebody is in
the file:

- **`cobble_wall` → `cobble_walling()`** is a nearly featureless beige with faint
  wavy lines (`crop/tex-cobble_wall.png`). This is the "untextured 30 m run" of
  the enceinte in `bailey-walk-04`, `mere-walk-05` and `south-walk-04`.
- **`plaster` → `lime_plaster()`** is a blurry blue-grey/cream mottle with no
  structure. This is the camouflage-looking gable and wall panel in
  `craft-walk-04`, `spine-walk-03` and `crop/green-daub.png`.

**Fix.** `rubble_weathered` already contains the correct recipe. Apply it to the
other three: (a) drive `foundation_stone` and `limewashed_stone` from
`coursed(size, courses, cols, bond, joint, wobble, seed)` at `materials.py:477`
so the wall is brought to course — `wobble` around 0.35–0.45, *lower* than
`rubble`'s 0.62, because these are the *dressed* stones; (b) key value variation
to `coursed`'s own `ident` field, not to an independent `fbm`, so it is per-stone
and not a blur; (c) give the joint 6–10 mm of real recess in the height and
normal maps — the shadow in the joint is 80 % of what makes stone read as stone;
(d) desaturate the mortar to warm lime grey and make moss a local mask driven by
ground proximity, not a global `cavity_dirt` tint; (e) rebuild `ivy` as a
leaf-shaped **alpha-cut** sheet; (f) give `cobble_wall` and `plaster` an actual
surface. Then diff a render — none of these need a new idea, only the recipe that
already exists applied to the keys that are actually on screen.

### 2. The intramural ground blend is a quilt of opaque axis-aligned rectangles

`tools/assetgen/venues/landscape.py:476
_surface_patch(asset_id, poly, mat, cell=1.25, lift=0.028, ragged=0.55)`.

**Frame: `bailey-walk-04`, crop at `crop/ground-quilt.png`** — saturated emerald
right-angled quads laid over grey cobble with hard 90° corners and zero
feathering. **`craft-walk-04`**: the same system emitting dark-brown rectangles
down the middle of Bakers' Row. **`sty-walk-03`**: the back-lane road surface is
this. **`t-aerial-ne/se`**: visible from the air as a green pixel-quilt between
the houses.

`cell=1.25` with a `ragged` term that drops only *whole cells* produces a
stair-stepped rectilinear boundary, and a 1.25 m step at 3 m is a right angle to
the eye. The grass material itself (`grass_lush`, `crop/tex-sheet.png`) is a
saturated emerald — more saturated than anything else in the town, including the
crimson confectioner.

This is the implementation of pass 02 §11 ("author the ground as a blend, not a
material"), and it is the ugliest thing in the build.

**Fix.** Inside `_surface_patch`: (a) `cell` to 0.35–0.5 m so the step falls
below edge-detection at 3 m; (b) **feather the alpha over the outer 2–3 cells**
instead of a binary in/out, and dither the boundary with the same noise field
that drives the mask — a patch edge must never be an axis-aligned line;
(c) rotate each patch's lattice by a per-patch seeded angle so no two patches
share the world grid. Then desaturate `grass_lush` by ~25 %.

### 3. The town has no skyline, and the church tower is invisible from everywhere

**Frames: `approach-s-free`, `approach-ne-free`, `approach-w-free`,
`westfront-free`, `t-silhouette`.**

From the south road at 138 m the town is a 6.6 m grey strip with no vertical
hierarchy. From the Mere the best profile in the build is topped by the quay
crane. From Kirk Green, on the door axis of its own church, **no part of the
tower is in frame** — pass 02 §12's measurement (13.8 m off-axis at 22 m = 32°
from centre, outside the 27.5° half-FOV) is unchanged. And `landscape.gltf` is
still **34.2 m tall** (y ∈ [−5.90, +28.29]) against a 22.0 m ceiling, so the
tallest thing in Hearthmere remains an unidentified mass inside the landscape
venue.

**Fix, by value per unit work.** (i) Curtain to 8.5–9.0 m, towers to 14–16 m
**with roofs** — the path and heights are data in `content/town/hearthmere.json →
wall`, so this is numbers plus a cap on the tower generator. (ii) Move the church
tower onto or within ~6 m of the west-door axis, or angle Kirk Green's approach
to catch it; §3.1 makes the church the first thing anyone sees and it cannot
currently be seen. (iii) Find and delete the 28.29 m landscape mass. (iv) Retire
or reposition the `silhouette` camera — the three approach cameras I authored are
what a player actually gets and they should be in the standard set.

### 4. The aerial perspective is over-driven by roughly 2×

`content/town/hearthmere.json → atmosphere.scattering` (authored at
`tools/plan/plan_data.py:ATMOSPHERE`): `density 0.0058`, `maxOpacity 0.93`,
`fullDistance 130`.

This was the right call and it went too far. **`approach-ne-free`**: the whole
town at 120 m is bleached to ~85 % haze, so no material, no value and no
silhouette survives. **`wharf-walk-09`**: the far shore is a wall of near-white
cauliflower. **All four aerials**: behind frosted glass, with the near foreground
nearly as hazed as the far distance. **`spine-walk-03`, `craft-walk-04`**: the
end of a 70 m street is already ~70 % washed.

`atmosphere.md`'s measured before/after is honest and the depth ordering it
bought is real. The failure is `maxOpacity 0.93` — the background asymptotes to
sky colour, so past `fullDistance` the world is simply gone. Reference titles
hold 250–400 m of legible town.

**Fix.** `density` → **0.0030**, `maxOpacity` → **0.62**, `fullDistance` →
**300**. Re-run `town.mjs --bands`: separation should land around **+45 to +60**,
not the +92 the arrival frame currently reports — +92 is not depth, it is a veil.
Keep the temperature swing exactly as it is; that half is working.

### 5. The roofscape is still a checkerboard, and the block-dealing logic cannot fix it

`core/building.py:393 DISTRICT_ROOFING`, `:412 ROOF_BLOCK_M`, `:486
roof_covering`. **Frames: `t-plan`, `t-aerial-ne/se/sw`.** Tracing the south
block in `t-aerial-se` left to right: orange, cream, orange, cream, cream,
orange, brown, orange. There is no run anywhere in the town.

The code is good and the intent is right. Four reasons it produces noise anyway:

1. **`ROOF_BLOCK_M = 26.0` gives about two buildings per block.** ~70 masses over
   a ~160 m built area is ~36 blocks. A block of two is indistinguishable from an
   independent roll.
2. **Three separate paths re-roll per-asset instead of per-block**: the 1-in-7
   odd-one-out (`:516`), `_no_fire_risk`'s fallback (`:512`), and the style-veto
   fallback (`:559`) all use `rng` (asset-seeded), not `brng`.
3. **Terracotta is the plurality in 6 of the 8 districts** (`market` 5/10,
   `quayside` 4/9, `fireside` 6/8, `smithward` 5/7 — plus both fallbacks landing
   in `merchant_townhouse`'s 6-of-9 terracotta pool).
4. **`terracotta` is one flat material**, so even where a block *does* agree,
   adjacent roofs are pixel-identical and read as one decal rather than a run of
   separate roofs.

**Fix.** (a) `ROOF_BLOCK_M` to **42–48 m** — four to six plots, which is what
reads as a run from the air. (b) Route every fallback through `brng`. (c) Flip
`knowe`, `westlanes`, `waterside` and `southgate` so terracotta is not the
plurality; a town where 55 % of roofs are one hue is a town with one roofer.
(d) Split `terracotta` into three seeded tints (new / faded / mossed) picked per
building — the cheapest of the four and on its own it changes every aerial.

### 6. The confectioner's barge board shoots five metres into the sky, on the market place

`tools/assetgen/venues/confectioner.py:166–174`. **Frames: `spine-walk-09`
(crop at `crop/red-building.png`), `t-square`.**

```python
bb = M.chamfered_prism([(0.0, 0.0), (L + 0.30, 0.0),
                        (L + 0.30, 0.30), (0.0, 0.30)], 0.055, PAINT, ...)
bb.rotate_z(sx * -math.atan(PITCH))
bb.translate(sx * 0.10, apex - 0.20, zf - JETTY - 0.30)
```

The prism is always built extending in **+x**. `rotate_z` mirrors the *angle* and
not the *direction*, so for `sx = -1` the board rotates up-and-outward, leaves the
roof entirely, overshoots the apex by roughly the height of the gable and
terminates in mid-air. Same class of bug as the `roof.py` rotate-about-origin
defect `gates.md` found. It violates BUILD_DIRECTIVE §6.1 in the sightline from
Ford Road and from the market place.

**Fix.** Mirror the geometry, not the angle: build from `−(L + 0.30)` to `0` when
`sx < 0`, or `bb.scale_x(sx)` before `rotate_z`. While in the file:
**`PAINT = "painted_crimson"` at `:62` paints the whole building** (`:88, :124,
:170, :208, :212, :239, :467, :502, :505`). Keep the paint as the confectioner's
signature but confine it to trim — barge boards, door, shutter — and put the
frame back in oak.

### 7. The waterfront of a lake town has no boats

**Frames: `wharf-walk-09` (the quay deck), `approach-ne-free` (the whole
waterfront from the water), `t-aerial-ne`.**

`BUILD_DIRECTIVE` §4 names the waterfront as the thing that makes Hearthmere
legible: *"moored flat-bottomed boats, nets, a crane, fish drying, the customs
house."* The crane is there and it is the best silhouette element in the build.
The customs house is there. **There is not one vessel on the water anywhere in
the town, and not one moored at the wharf.**

`wharf-walk-09` is an empty plaza with a rope rail, three small fish heaps and a
bollard. Its paving is a rigid orthogonal grid of 0.6 m slabs, some inset in
recesses, which reads as a modern civic plaza rather than a working quay.

**Fix.** Three or four moored flat-bottomed lighters against the quay face —
hulls only, no rigging — plus what goes with them: stacked barrels, sacks under a
tarpaulin, coiled rope, a net drying on a frame, a plank gangway. Highest ratio
of *identity* to *effort* left in the build; the venue exists and needs dressing.

### 8. Foliage: right density, wrong leaf, and one tree is standing in a street

`materials.py:3963 leaf_atlas()`, `vegetation.py:341 blob_canopy()`,
`venues/landscape.py:351 _open_runs()`.

The rebuild worked — `t-square`'s market oak and `spine-walk-09`'s tree are real
trees and the orange confetti is gone. Three things stop it landing:

- **`kirk-walk-06` at (26.3, −17.1): the camera is inside a tree**, on Kirkgate,
  on the church-to-market route. 80 % of the frame is dark foliage at point-blank
  range. Pass 02 §15 reported the same defect as a hedge; it is now a tree, and
  `tools/check_walkable.mjs` still reports 15/15 clear — so either the checker
  cannot see it or it has no collider, and a player walks *through* a
  solid-looking tree.
- **At LOD0 the cards are 1.5–2 m pinnate fern fronds** (`kirk-walk-06`,
  `westfront-free`) — not an oak, a yew or an ash, and roughly 2× too large.
  The atlas has the coverage now; the sprig *shape* is wrong.
- **`blob_canopy` still ships a readable faceted sphere** — `kirk-walk-06` has a
  low-poly ball floating over the churchyard wall.
- There is **no leaf translucency**: at 09:30 with the sun behind, every canopy
  is opaque near-black. One transmission term would transform every tree in town.

### 9. The Mere is still a stamped ellipse that blows out to white

**`t-aerial-sw`** (perfect ellipse, far half a **pure white blowout**, uniform
beige beach ring); **`approach-ne-free`** (sun path clipped flat white over a
third of the frame, with visible polygon facet edges in the glitter);
**`t-plan`/`t-aerial-se`** (the Emberflow is still a literal parallel-sided
rectangular canal); **`t-gate-north`** (the bank is still a **hard sawtooth of
flat triangles** — the first thing the eye lands on in a mandated hero frame);
**`wharf-walk-09`** (hard line where water meets quay, no wet margin).

`atmosphere.water.specularKnee = 1.05` is set too high to catch a lobe whose peak
goes as roughness⁻⁴, and it does nothing about the environment term.

**Fix.** (a) Knee to ~0.55, plus a roughness *gradient* with distance so the
glitter path narrows instead of filling the far half. (b) The shoreline is
geometry, not shading: perturb the `basin`/`channel` outlines in
`content/town/hearthmere.json → water.bodies` with two octaves of low-frequency
noise and let them interpenetrate the terrain instead of clipping to it.
(c) Replace the sawtooth bank at the bridge with a proper batter, and put reeds,
shingle and a wet line on it.

### 10. The enceinte is four masonry treatments, one of which reads as untextured

**`t-gate-north`, `bailey-walk-04`, `mere-walk-05`, `south-walk-04`,
`wharf-walk-05`.** In `bailey-walk-04` alone: over-chamfered "foam block" cobble
whose ~10 cm rounded arrises read as inflated rubber (right), a **featureless
beige plane over a ~30 m run** (middle — this is `cobble_wall`, §1), and grey
blockwork at a different scale (left). The timber hoarding floats above the
featureless section with no visible support, and `wharf-walk-05` has **bare
putlog beams projecting into space carrying nothing**.

**Fix.** One masonry family for the whole enceinte with ashlar reserved for
dressings, exactly as the church already does it — `venues/wall.py` and
`venues/gatehouse.py` must agree one key, and that key must not be
`cobble_wall` until `cobble_walling()` has a surface.

### 11. Cloth is still flat rectangles; two of them are still saturated orange

`core/streetscape.py:510 washing_line()` and `hung_cloth` above it.
**Frame: `sty-walk-03`, crop at `crop/washing.png`.**

The rope got its catenary — good. The cloth did not: `hung_cloth`'s fold function
modulates the sheet in the *depth* direction only, so the mesh corrugates but the
**silhouette stays a perfect rectangle** with a dead-straight hem and a
dead-straight top. It reads as coloured paper pinned to a string. `cloth_rust`
(`crop/tex-sheet.png`) is a saturated orange that is out of palette against
everything near it.

**Fix.** Scallop the hem — sag the bottom edge 6–10 cm between the pegs and pinch
the top edge at each peg. Add 8–12 mm of thickness. Desaturate `cloth_rust` ~30 %.

### 12. All three hero-camera composition defects are unchanged

- **`t-square`:** the lamp standard **still** stands dead centre on the camera
  axis, bisecting the frame top to bottom and cropping the fountain. Its base is
  a bulbous pale plinth and the column is a marbled black-and-white cylinder that
  reads as polished stone, not iron. `core/streetscape.py:242 lamp_post`.
- **`t-gate-north`:** **still** shot off-axis and low over the water; the bridge
  parapet is a featureless slab filling the right half and the mandated arch is
  in a ~150 px gap. Put the camera on the bridge centreline at 1.62 m.
- **`spine-walk-01` (bridge crown):** the camera is **still inside the bridge
  deck** — an entirely brown frame. The walk camera takes its Y from
  `terrain.height()` and knows nothing about authored decks. **No bridge frame
  has ever been reviewed in this project.**

### 13. The church west front has no west window; the nave ends in a blank wall

**Frame: `westfront-free`.** Real progress: the perron reads as a processional
flight, the portal is a proper two-order arch, the trees frame rather than crop.
Then: **no west window**, ~8 m of blank wall above the arch, no hood mould, no
gable, no string course. Through the arch the nave is now lit — but the east end
is a **flat featureless pale wall** with a small altar table in front of it: no
east window, no reredos, no apse, no arcade, and none of §3.1's clerestory light
shafts reaching the floor. The floor has no worn path from door to altar, which
§3.1 names explicitly. Two large low-poly faceted stone spheres sit on the
flanking piers.

### 14. Green is the material of last resort in five places, and one texture causes three of them

**`crop/green-daub.png`** — the "green wattle-and-daub panels" of pass 02 §14 are
not daub at all: they are **hard-edged rectangular `ivy` decals laid over the
plaster panels, overlapping the timber frame**, at random bays. And
**`crop/tex-ivy.png` shows `ivy_albedo.png` is an opaque green Voronoi crazy
paving with no alpha cutout and no leaf shapes whatever.** So pass 02 §14 (green
daub) and §18's ivy half (flat rectangular decal) are one defect with one fix.

The other three: **`crop/market-paving.png`** — the market paving's mortar joints
are olive green (`limewash`, §1). **`wharf-walk-05`, `bailey-walk-04`** — green
blotches over the wall stone (`rubble`'s `moss` parameter applied as large
blotches rather than a ground-proximity mask). **`wharf-walk-07`** — large flat
saturated-green triangles lying on the paving as "grass tufts", plus saturated
emerald shutters and awnings in `craft-walk-04` and `kirk-walk-09`.

Daub is limewashed — off-white or ochre. Mortar is warm grey. Moss is local and
desaturated. Ivy has leaves and a broken margin.

### 15. Smaller, still visible from the gameplay camera

- **`wharf-walk-07`:** a large **untextured dark-brown box** with unchamfered
  corners against the water-gate pier — a placeholder mass in a hero venue.
- **`t-gate-north`:** a crumpled faceted grey-brown lump fills the right of the
  frame and reads as a paper bag; the bridge parapet carries dark curvy scribbles
  that look like a crack or vine decal applied to the wrong surface.
- **`approach-s-free`:** the field hedges are **solid dark-green extruded ribbons
  with a sinusoidal top edge** — the field system reads worse in 3D than in plan.
  `venues/landscape.py:389 _boundary`, `:1451 _fields`; the radial-and-concentric
  layout is unchanged from pass 02.
- **`t-aerial-ne`, `t-aerial-sw`:** the fallow fields are a **desaturated
  pink-mauve** that appears nowhere else in the palette.
- **Road paving repeat.** `spine-walk-06`, `spine-walk-09`, `mere-walk-05`: the
  `sett` material resolves into an obvious light/dark chequerboard at 2–8 m and
  its tile repeat is readable; `crop/figure-shadow.png` shows it has **no
  per-stone edge, no joint and no bevel** — the setts I read in the wide shot are
  blur.
- **Streets are too wide.** Ford Road reads as ~14 m of empty carriageway
  (`spine-walk-06`); Mere Street, the *poorest* lane in town, is ~10 m
  (`mere-walk-05`). 4–7 m is the period width, and narrowing would double the
  apparent density of the town for free.
- **Sky.** There are clouds now (`sty-walk-03`) but they are absent from most
  frames, and no frame I read contains a sun disc.

---

## The three changes that buy the most quality per unit of work

**1. Course `stone`, `limewash` and `ivy` — the recipe already exists. (§1, §14)**
`rubble_weathered` was rebuilt correctly this wave; apply the same `coursed()`
bond, per-stone identity keying and recessed joint to `foundation_stone`
(`materials.py:1092`) and `limewashed_stone` (`:2199`), and give `ivy` an alpha
cut. Between them these three textures own the church, the fountain, the plinths,
the steps, the market paving and the "green daub". Every street frame, both
arrival frames and half the aerials change. Nothing else on this list touches as
many pixels per hour of work, and **no new idea is required — only applying this
wave's own fix to the keys that are actually on screen.**

**2. Halve the fog and split the terracotta. (§4, §5d)** Three numbers in
`plan_data.py:ATMOSPHERE` and one seeded tint pick in `building.py:roof_covering`.
The first gives the town back its legibility at distance — which is what makes a
skyline possible at all — and the second turns a 55 %-of-roofs flat orange decal
into a roofscape. Both are an afternoon.

**3. Feather the ground patch, raise the wall, put boats on the water.
(§2, §3i, §7)** Three edits in three files, each independent: a sub-grid
feathered `_surface_patch`; the curtain to 8.5–9.0 m and towers to 14–16 m with
roofs; four moored lighters and their cargo on a quay that already exists.
Together they close the last of the "unfinished set" read from the ground, from
the air and from the water.

*Close fourth, and not cheap:* move the church tower onto the west-door axis
(§3ii) and put a west window in the front (§13). The church is the spawn point
and the most important composition in the build, and it is currently a stone box
with a hole in it containing a blank wall.

---

## What the next wave should do, ranked

1. **The material pass.** Course `stone` and `limewash`; key their value to the
   cell id; recess the joints; alpha-cut `ivy`; give `cobble_wall` and `plaster`
   a surface; kill the green mortar and the global moss. One masonry family for
   the enceinte. §1, §10, §14.
2. **Atmosphere retune and the roof deal.** density 0.0030 / maxOpacity 0.62 /
   fullDistance 300; `ROOF_BLOCK_M` to 42–48 m; every fallback through `brng`;
   three terracotta tints; terracotta off the plurality in half the districts.
   §4, §5.
3. **Ground blend.** Sub-grid cells, feathered dithered edges, per-patch lattice
   rotation, desaturated `grass_lush`. §2.
4. **Skyline.** Curtain 8.5–9.0 m, towers 14–16 m with roofs, church tower onto
   the west-door axis, find and delete the 28.29 m landscape mass, retire or
   reposition the `silhouette` camera. §3.
5. **Correctness sweep — three floating/blocking defects.** The confectioner
   barge board (`confectioner.py:166`); the tree standing in Kirkgate at
   (26.3, −17.1) and the `check_walkable` blind spot that lets it pass; the
   untextured box at the water gate. §6, §8, §15.
6. **Waterfront dressing.** Boats, cargo, nets, gangways; a real quay surface
   instead of the orthogonal slab grid. §7.
7. **Water.** Specular knee ~0.55, roughness gradient with distance, noised
   shoreline outlines, a thalweg on the Emberflow, kill the sawtooth bank. §9.
8. **The church.** West window; east window or apse behind the altar; clerestory
   light reaching the floor; the worn path §3.1 asks for; retire the faceted
   spheres. §13.
9. **The fountain.** 4.5–6.0 m to the finial; raise the water or lower the lip so
   it can be seen from a standing eye; and a material that is not the material of
   the ground it stands on. §(a).
10. **Harness truth.** Put the walk/free cameras on authored deck and floor
    levels rather than `terrain.height()` — no bridge or perron frame has ever
    been reviewed. Move the `square` camera off the lamp axis and the
    `gate-north` camera onto the bridge centreline. Add the three approach
    silhouettes to the standard set. §12.
11. **Foliage finish.** Smaller cards with a north-European sprig shape; a
    transmission term; retire the last faceted `blob_canopy` from LOD0. §8.
12. **Residue and streets.** Scalloped hems and pinched pegs on the washing;
    desaturate `cloth_rust`; narrow Ford Road toward 7–8 m and the lanes toward
    4–5 m; give `sett` a real per-stone edge. Ford Road and the market place
    still carry far less residue than Sty Lane. §11, §15.

---

## Budget, for the record

`t-report.json`, worst gameplay frame: **727 draw calls / 900**,
**1,154,547 triangles / 3.5 M**, with 32 venues placed and 3.97 M triangles in
the scene graph. `landscape` is down from 83 % to **31 %** of scene triangles —
the largest single engineering win of the wave.

The budget is not what is wrong with these frames, and it has enough headroom to
pay for every fix on the list above.
