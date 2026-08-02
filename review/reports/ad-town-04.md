# Art-director review — Hearthmere, whole town, pass 04

**Verdict: REJECT.**

Reviewed 2026-08-02 against `docs/ART_BIBLE.md` §8, `docs/BUILD_DIRECTIVE.md` §3
(arrival), §4 (geography), §6 (structure), §7 (budget) and §9 (done).
**87 frames rendered by me at the locked 09:30 rig into `review/shots/ad-town-04/`
and read as PNGs**, plus twelve crops and four shipped albedo sheets read
directly — two of which I regenerated from source with `--force-textures` to
prove the shipped sheet is current and not stale.

I reviewed from images. Where a line number appears below, I opened the file
only after a frame told me what to look for. I took no build agent's
self-assessment: **five claims from this wave are contradicted by the renders
and are named in "Claims the renders do not support".**

Frames read: `t-plan`, `t-aerial-ne/nw/sw/se`, `t-arrival`, `t-square`,
`t-silhouette`, `t-gate-north`, `t-gate-south`, `t-approach-s/ne/w`;
`spine-walk-01..10` (bridge → north gate → Ford Road → market place);
`south-walk-01..08` (market place → south gate); `wharf-walk-01..09` (Wharf Lane
→ water gate → quay → Fishers' Steps); `kirk-walk-01..08` (Kirkgate → Kirk Green
→ market place); `craft-walk-01..07` (Bakers' Row); `sty-walk-01..06` (Sty Lane);
`alley-walk-01..06` (Bell Alley → Smiths' Lane); `bailey-walk-01..07` (The
Bailey); `mere-walk-01..08` (Mere Street → West Lanes); plus five free cameras
(`westfront`, `fountain`, `bridge`, `quayboats`, `fordlook`).

---

## The verdict, stated plainly

**This is the first wave that produced frames I would defend, and it is still a
REJECT.**

Three things genuinely landed, and they are the three biggest single objects in
the build:

- **The fountain now holds the arrival frame.** It is ~5.4 m to the heron, it
  has visible water, and at 43 m through the church doors it is unmistakably
  the focal point. Pass 02 and pass 03 both rejected it. It is fixed.
- **The silhouette now reads as a town.** `t-silhouette` is a working
  instrument for the first time in the project, and what it shows is a
  continuous mass with two attached towers, a spire, a cupola and a chimney
  line. Pass 03 got a detached floating block and four unexplained specks.
- **The guild tower exists and is visible** from the altar, from the west
  approach and from the air. The town has a vertical hierarchy for the first
  time.

Against that, **not one of pass 03's six headline findings is closed**, and two
of them are unchanged at the level of the number in the file:

| pass-03 headline | state now |
| --- | --- |
| §1 masonry is crazy paving | **PARTLY** — `rubble`/`coursed` fixed and visible (`wharf-walk-06` left); `cobble` still crazy paving on every street (`mere-walk-05`); `cobble_wall` rebuilt and **still reads as untextured** (`bailey-walk-04`) |
| §2 ground quilt of rectangles | **PARTLY** — gone from the air, still hard-edged saturated emerald rectangles at eye height (`bailey-walk-04`, `mere-walk-05`) |
| §3 no skyline, wall too low | **PARTLY** — towers exist; `wall.walkHeight` is **still 5.2 + 1.1 parapet**, byte-for-byte unchanged |
| §4 aerial perspective 2× over-driven | **NOT FIXED** — `density 0.0058 / maxOpacity 0.93 / fullDistance 130`, **all three numbers identical to pass 03** |
| §5 roofscape checkerboard | **FIXED for clustering, NOT for tint** — `(district, terrace)` blocks work and read from the air; terracotta is one flat saturated orange on ~45 % of roofs |
| §7 waterfront has no boats | **PARTLY** — two lighters and a punt exist and are correct; at any gameplay camera they are invisible |

And the build acquired new damage. The single most-viewed camera in the project
after the altar — **`approach-s`, the canonical return from the quest zones — is
now 40 % obscured by a tree standing five metres in front of the lens**, and
that tree's leaves are rendered as **regular chequerboard grids of green
squares**. That is a worse asset than pass 03 had.

Blind, side by side against Divinity's Reach, Gridania, Ul'dah and post-Legion
Boralus: **three frames now survive the first two seconds and none survives ten.**
Which three, and what separates them, is answered in the last section — it is
the question the project turns on and it now has a real answer instead of "no".

---

## Claims from this wave that the renders do not support

- **MATERIAL-RECIPES: *"the frames confirm the rectangles are gone."*** They are
  gone from the aerials. They are not gone from the gameplay camera.
  **`alley-walk-03` is the frame that settles it**: the whole lower half is a
  quilt of opaque, hard-edged, **saturated emerald** polygons over brown earth
  and grey cobble, with dead-straight boundaries and zero feathering, at 3–8 m
  from the eye. `bailey-walk-04` has three more at 4–12 m; `mere-walk-05` two at
  6 m; `kirk-walk-06` one on the paving at 15 m. The cell got smaller; the edge
  did not get softer, and the green did not get quieter.
- **MATERIAL-RECIPES: *"`foundation_stone` and `limewashed_stone` rebuilt on
  `coursed` … recessed joints."*** True in source and it landed on `rubble`
  (`wharf-walk-06`, the best masonry in the build). It has **not** reached the
  street: `mere-walk-05`, `craft-walk-04`, `t-square` and `kirk-walk-06` are
  paved in random-polygon crazy paving at ~0.8 m, every slab the same value.
  The agent named the cause itself and did not fix it — **421 literal
  `uv_scale=` call sites against 3 uses of `MATS.uv_scale()`.** The recipe is
  right and the scale that reaches the mesh is wrong.
- **MATERIAL-RECIPES / GATES: the `cobble_wall` rebuild.** I regenerated
  `cobble_wall_albedo.png` from current source with `--force-textures` and
  diffed it against the shipped sheet: **identical**. So the rebuild is real,
  current, and *still produces a nearly featureless beige* (`crop/NEW-cobble_wall.png`).
  Adjacent "cobbles" differ by about five luminance levels out of 255. This is
  the untextured 30 m run of the enceinte in `bailey-walk-04` and the blank
  slab at the end of Bakers' Row in `craft-walk-04`, unchanged in appearance
  through two waves of work on it.
- **HERO-VENUES: *"All four §3.2 boxes now tick."*** Three tick. The fourth —
  "at least two other venue anchor silhouettes" — is carried by the guild tower
  and one slate gable. There is no forge chimney, no gatehouse and no inn
  roofline in `t-arrival`. Call it one and a half.
- **GEOMETRY-DEFECTS: *"All ten items are closed."*** Nine are. Item 10, "Ford
  Road not completable", is closed. But `check_walkable.mjs` still ends with
  **`1 unreachable door(s): hm.townhouse.door.15`**, and `BUILD_DIRECTIVE` §9's
  first box is *"the player can walk from the church altar to every venue door."*
  The agent found this and handed it on rather than closing it; the box is still
  unticked and the report should not read as if the sweep is complete.

---

## The three standing questions, answered from frames

### (a) Does the arrival frame deliver BUILD_DIRECTIVE §3?

**Nearly. For the first time this is a "nearly" and not a "no."** `t-arrival`,
crops at `crop/arr-fountain.png` and `crop/arr-floor.png`.

| §3.2 requires | in `t-arrival` |
| --- | --- |
| the descending church steps | **yes** — perron, cheeks, balustrade, and the eye is led |
| a street leading the eye | **yes** — the market place opens, the jettied range at frame-left walls the composition |
| the market fountain as the focal point | **yes** — first time. ~110 px of a 900 px frame at 43 m, tiered basin, visible water, bronze heron |
| ≥ 2 other venue anchor silhouettes | **one and a half** — the guild tower (unmistakable, ~200 px) and one slate gable. No forge stack, no gatehouse, no inn |

**The composition is solved. The surfaces are not, and they are what stops it.**
Three things, in order of how much they cost the frame:

1. **The floor shadow is a 30 cm stair-step staircase across the whole nave.**
   `crop/arr-floor.png` — the sun/shade boundary is a perfect blocky staircase
   with ~30 px risers, running diagonally through the most important
   composition in the build. It is the first thing the eye lands on. The map is
   4096² over a **92 m box** (`client/src/main.js:83`, `left/right/top/bottom
   ±46`) — 44 texels per metre with no cascade, which is exactly this artefact.
   No shipped AAA MMO has this on its spawn frame.
2. **The church's own interior is two unrelated masonries a metre apart.** The
   pier is a coursed grey-brown stone; the wall panel behind it is a cartoon
   "wavy block" with ~10 cm rounded arrises that reads as inflated foam. In the
   spawn room, at 2 m. This is the "one world" question failing on frame one.
3. **Everything in the aperture is one value.** `t-report.json → valueBands`
   for `arrival`: `foregroundToBackground 94.9`, `midgroundToBackground 12.6`,
   **`temperatureSwing 0.2`.** Pass 03 asked for +45–60 and got +92; it is now
   **+94.9** — further in the wrong direction — and the temperature half, which
   Art Bible §1 requires and which `atmosphere.md` was written to deliver, is
   **zero**. The mid-to-background separation of 12.6 is the real number: past
   ~25 m the picture is one flat cream plane. The market place surface inside
   the aperture carries no paving pattern at all.

Also: the market place is **empty**. Six bare stall frames, no goods, no crates,
no awnings with sag, no spill. Art Bible §7 calls residue the highest-value
detail per unit effort and the town's central space has almost none.

And one thing the 43 m view flatters: at 6 m (`fountain-free`) **the falling
water reads as flat pale ribbons stuck to the air** — hard-edged vertical
strips hanging off the bowl with no transparency, no volume and no splash where
they land, and the bronze spouts are near-black lumps with no metal in them. The
basin is a flat teal disc with no ripple and no refraction. The fountain's
*mass* is fixed; its *water* is not, and it is the object the whole town is
composed around.

### (b) Does the silhouette read as a town with a skyline?

**Yes as a shape. No as a hierarchy.** `t-silhouette`, `t-approach-w`,
`t-approach-ne`, `t-approach-s`.

`t-silhouette` is finally usable and what it shows is real: a continuous ~1350 px
mass with the church tower and spire left of centre, the guild's battlemented
head and corner turrets right of centre, a cupola between them, a pyramid-capped
tower east, chimneys throughout. Both towers are **attached**. Pass 03's
"detached black mass floating 11 m above the town line" is gone. This is the
instrument fix and the geometry fix both landing.

What is still wrong is proportion:

- **The towers are under 2× the general roofline.** 21–22 m against a 10–12 m
  roof line, over a 170 m width. Divinity's Reach and Ul'dah run 2.5–3×. The
  profile reads as *a large village* rather than *a town*.
- **The wall does not appear in the silhouette at all.** 5.2 m to the walk plus
  1.1 m of parapet sits entirely behind 10 m houses. `content/town/hearthmere.json
  → wall.walkHeight` is **still 5.2**, unchanged from pass 03, and the towers
  are still **8.9 m** and **flat-capped**. From `t-gate-south` the enceinte
  reads as a garden wall; from `t-approach-ne` it is a low pale ribbon. A town
  with a wall you can see over from the field has no defensive silhouette and
  no base to its mass.
- **`approach-s` — the canonical return — is ruined by a tree.** 40 % of the
  frame is foliage at ~5 m. The guild tower is in there at ~50 px, heavily
  hazed, competing with a saturated red barn *outside* the wall which is the
  brightest object in the picture.
- **`approach-w` works.** The guild tower and the church roof both stand clear
  above the wall line. It is the proof the geometry is now right and the
  atmosphere and the foreground are what is left.

### (c) Does it read as one world?

**No — and the seams have narrowed to exactly two systems, which is the best
news in this report.** Everything below is one of:

**(i) The masonry family is not one family.** `t-gate-north` alone carries
**five** treatments in a single frame: giant-plate ashlar on the curtain, a
smeared cloudy mottle on the drum towers, a third block scale on the gate
frontispiece, a "crocodile skin" of wavy chamfered blocks on the bridge
parapet, and a smeared cream-and-brown camouflage on the building at frame
right that reads as a stained bedsheet over a box. Pass 02 said three; pass 03
said four; it is now five. `wharf-walk-06` puts the *best* masonry in the build
(real coursed ashlar with per-stone value) immediately beside a pale green-grey
crazy paving, meeting at a hard corner on one structure.

**(ii) The ground is three unrelated surfaces per frame.** `bailey-walk-04`:
grey cobble, beige compacted earth and pale crazy paving across a 10 m span
with hard boundaries. `craft-walk-04`: two different crazy pavings meeting.
`kirk-walk-06`: crazy paving, a hard emerald quad, and a featureless pale plane.

Everything else that made pass 03's list — the crimson confectioner, the green
of last resort, the thatch that is two materials — is still true, still on
screen, and is a consequence of one of those two.

---

## The running scorecard

### Pass-02 findings (as tracked in pass 03)

| # | pass-02 finding | pass 03 | **pass 04** | proof |
| --- | --- | --- | --- | --- |
| 1 | 18 of 32 venues do not exist | FIXED | **FIXED** | `t-report.json` 32 placed / 0 missing, 94 building slots (§5 target 75–95) |
| 2 | leaf atlas incapable of a tree | FIXED | **REGRESSED** | `t-approach-s`, `t-square`, `kirk-walk-06`: leaves are regular grids of green squares at LOD0 |
| 3 | yew is a 28-face polyhedron | PARTLY | **PARTLY** | no faceted sphere found in 79 frames; the cards that replaced it are §(2) |
| 4 | thatch is a smooth cream membrane, knife edge | PARTLY | **NOT FIXED** | `mere-walk-05` (both roofs), `south-walk-04`, `spine-walk-03`. `crop/NEW-thatch.png` — the regenerated albedo has no straw in it at all |
| 5 | no fog / aerial perspective | over-driven | **NOT FIXED** | `plan_data.py ATMOSPHERE` unchanged: 0.0058 / 0.93 / 130 |
| 6 | fountain must anchor at 43 m | PARTLY | **FIXED** | `t-arrival`, `crop/arr-fountain.png`. 5.4 m, water visible, bronze heron, reads at 43 m |
| 7 | no skyline; tower detached; floating masses; wall too low | NOT FIXED | **PARTLY** | `t-silhouette` — towers attached, profile reads. Wall unchanged at 5.2+1.1, towers 8.9 m flat-capped |
| 8 | Mere a stamped ellipse; Emberflow a rectangle; water blows to white | PARTLY | **NOT FIXED** | `t-aerial-sw`: perfect ellipse, uniform beach ring, far half a pure white blowout; the Emberflow is a dead-straight parallel-sided canal |
| 9 | `rubble` is crazy paving with green mortar | NOT FIXED | **PARTLY** | fixed and visible in `wharf-walk-06`; `cobble` on every street is unchanged crazy paving (`mere-walk-05`); `cobble_wall` still untextured (`bailey-walk-04`) |
| 10 | three masonry treatments on one wall | NOT FIXED (four) | **NOT FIXED (five)** | `t-gate-north` |
| 11 | inside the wall is bare brown dirt | PARTLY | **PARTLY** | fixed from the air (`t-aerial-sw`); hard emerald quads remain at eye height (`bailey-walk-04`) |
| 12 | church west front blank; nave black; tower off-axis | PARTLY | **PARTLY** | `westfront-free`: the great west arch is now enormous and the nave beyond is lit, with real king-post trusses, an arcade and a clerestory — genuine progress. Still **no west window**, still **no tower in frame from its own door axis**, still a **blank pale east wall** with no window/reredos/apse, still **no light shafts on the floor**, still **no worn path**, and the **two faceted stone spheres are still on the flanking piers** |
| 13 | no AO; 21 px/m shadows | PARTLY | **NOT FIXED** | `crop/arr-floor.png` stair-stepped shadow; the 1.75 m figure has **zero contact darkening** in `t-square`, `t-gate-south`, `spine-walk-06`, `mere-walk-05` — every frame it appears in |
| 14 | one green mottle doing daub, hedge and ground | NOT FIXED | **PARTLY** | ivy/hedge/weeds split is real. Still on screen: `alley-walk-03` — the timber-frame **infill panels are bright emerald**, which is pass-02 §14's "green daub" verbatim; hard-edged green quads on the ground in the same frame; green blotches on the fountain kerb (`t-square`) |
| 15 | a hedge stands in Kirkgate and swallows the camera | NOT FIXED | **MOVED, NOT FIXED** | Kirkgate is clear (`kirk-walk-01..08`); the same defect is now on **`t-approach-s`**, a mandated camera |
| 16 | large black unlit polygons | FIXED | **PARTLY** | `t-approach-w`: the field hedge in the foreground is **pure unlit black** over the bottom half of the frame |
| 17 | crude LOD at 25 m; lanes lose their surface | PARTLY | **PARTLY** | no popping; lanes have a surface; the surface is §9 |
| 18 | cloth and ivy are flat single-sided quads | NOT FIXED | **PARTLY** | `sty-walk-03`: cloth is still perfect rectangles, dead-straight hems, no sag, no peg pinch, no thickness. `cloth_rust` **is** desaturated — half the fix landed |
| 19 | landscape 83 % of triangles; fields a radial spiderweb | PARTLY | **PARTLY** | triangles fine; fields **still radial-and-concentric** (`t-plan`, `t-aerial-sw`), hedges still sine-topped extruded ribbons (`t-approach-s/w`), fallow still pink-mauve |
| 20 | composition defects in the hero cameras | NOT FIXED | **NOT FIXED** | `t-square`: lamp **still** bisects the frame. `t-gate-north`: **still** off-axis and low, parapet fills the right 45 %. `spine-walk-01`: camera **still inside the bridge deck** — an entirely brown frame, third pass running |
| 21 | roof distribution reads as a checkerboard | NOT FIXED | **PARTLY** | clustering now reads from the air (`t-plan`, `t-aerial-sw`) — real win. Terracotta is still one flat saturated orange on ~45 % of roofs |

**Pass-02 score: 2 fixed · 12 partly · 6 not fixed · 1 regressed.**
(pass 03 was 3 / 9 / 9. Two items moved from FIXED to worse; nine moved from
NOT FIXED to PARTLY. The distribution improved; almost nothing closed.)

### Pass-03's own 15 findings

| § | pass-03 finding | **pass 04** | proof |
| --- | --- | --- | --- |
| 1 | crazy paving is `stone`/`limewash`/`ivy`, not `rubble` | **PARTLY** | recipes rebuilt correctly; 421 literal `uv_scale=` sites keep the result off the screen |
| 2 | ground blend is opaque axis-aligned rectangles | **PARTLY** | `cell` 1.25 → 0.72; edges still binary and unfeathered, patches still saturated emerald |
| 3 | no skyline, church tower invisible everywhere | **PARTLY** | guild tower reads from three approaches; wall and tower heights untouched |
| 4 | aerial perspective 2× over-driven | **NOT FIXED** | three numbers unchanged in `plan_data.py` |
| 5 | roofscape checkerboard | **PARTLY** | block-dealing fixed (85/94 in runs of 3+, and it reads); terracotta tint split never done |
| 6 | confectioner barge board shoots 5 m into the sky | **FIXED / NOT FIXED** | board fixed. `PAINT = "painted_crimson"` at `confectioner.py:62` still paints the **whole building** — `kirk-walk-06` is a fire-engine-red house on the church-to-market route |
| 7 | the waterfront has no boats | **PARTLY** | boats exist and are correct (`crop/ne-boats.png`); invisible at every gameplay camera; quay deck still an orthogonal 0.6 m slab grid (`wharf-walk-08`) |
| 8 | foliage: wrong leaf, tree in a street | **REGRESSED** | leaf is now a chequerboard grid; the street tree moved onto `t-approach-s` |
| 9 | Mere a stamped ellipse that blows out to white | **NOT FIXED** | `atmosphere.water.specularKnee` still **1.05**; `t-aerial-sw`, `t-approach-ne` |
| 10 | enceinte is four masonry treatments, one untextured | **NOT FIXED (five)** | `t-gate-north`, `bailey-walk-04`, `craft-walk-04` |
| 11 | cloth is flat rectangles, two saturated orange | **PARTLY** | orange desaturated; geometry untouched (`sty-walk-03`) |
| 12 | three hero-camera composition defects | **NOT FIXED (3/3)** | `t-square`, `t-gate-north`, `spine-walk-01` |
| 13 | church west front has no west window; nave ends blank | **PARTLY** | `westfront-free` — see pass-02 #12. Perron and portal are now genuinely good; window, tower-on-axis, east end, light shafts and worn path all still absent |
| 14 | green is the material of last resort in five places | **PARTLY** | see pass-02 #14 |
| 15 | smaller defects (untextured box, sett repeat, street width, sky) | **PARTLY** | streets narrowed (Ford Rd ~9 m from ~14 m) and `sett` has real per-stone edges — both real wins. The **untextured dark-brown box at the water gate is still there** (`wharf-walk-06`, x≈750). Clouds exist but appear in ~4 of 79 frames; **no frame contains a sun disc** |

**Pass-03 score: 0 fixed outright · 9 partly · 4 not fixed · 2 regressed.**

---

## Findings, ordered by how much they damage the frame

### 1. The shadow map is 44 texels per metre and it stair-steps across the spawn frame

`client/src/main.js:83` — `Object.assign(sun.shadow.camera, { near: 0.5, far:
200, left: -46, right: 46, top: 46, bottom: -46 })` with `mapSize 4096²` at
`:74`. That is a single 92 m box: **44.5 texels/m**. A 0.30 m shadow texel at a
1.62 m eye is a visible right-angled step at any range under 12 m.

**Frames:** `crop/arr-floor.png` — the shadow boundary is a blocky staircase
running diagonally across the church nave, in the frame `BUILD_DIRECTIVE` §3
calls "the most important composition in the build". `t-arrival` at full frame.
`t-gate-south` — the dappled tree shadow, the best lighting event in the build,
is stepped at its edges. `spine-walk-06`, `sty-walk-03`.

Compounding it: **the 1.75 m figure has no contact shadow in any frame it
appears in** (`t-square`, `t-gate-south`, `spine-walk-03/06`, `mere-walk-05`,
`craft-walk-04`, `bailey-walk-04`). It reads as a decal pasted on the ground.
Pass 03 §13 reported this; nothing moved.

**Fix.** A two- or three-cascade split — 0–18 m at ±10 m (205 texels/m), 18–60 m
at ±32 m, 60–200 m at the current box — is the standard answer and it is ~30
lines in `main.js` and the same in `town.html`. Cheaper interim: drop the single
box to ±18 m and accept shadow pop at 25 m; that alone takes the spawn frame
from 44 to 114 texels/m. Separately, contact darkening: the GTAO pass is in the
build and is not reaching dynamic geometry — either feed the figure into the AO
G-buffer or give every character a cheap projected contact blob.

*Why this is #1:* it is the single largest area of wrong pixels in the two most
important frames in the project, it is invisible to `validate.py`, and it is not
art — it is four numbers.

### 2. `cobble` is crazy paving at ~3× scale, and it is the surface of every street in the town

`tools/assetgen/core/materials.py` builds the recipes correctly. **421 call
sites pass a literal `uv_scale=` and only 3 call `MATS.uv_scale(key)`**, so the
authored metres-per-tile is overridden at the mesh and the pattern lands at
roughly three times its intended size.

**Frames:** `mere-walk-05` — the whole carriageway of the poorest lane in town
is irregular white-cream polygons at ~0.9 m, every slab the same value, like a
suburban patio. `craft-walk-04` — two different crazy pavings meeting mid-road.
`t-square` — the market place, 60 % of the frame. `kirk-walk-06` — on the
church-to-market route. `crop/arr-fountain.png` — inside the arrival aperture.

The previous agent identified this cause precisely and did not act on it. It is
the highest-value uncompleted item in the build.

**Fix.** Make `MATS.uv_scale(key)` the only path: change the signature so
`uv_scale` defaults to `None` meaning "ask the library", then delete the literals
in one mechanical sweep and re-render. The recipes do not need to change —
only the number of metres each tile covers.

**The other half of the same surface** is `venues/landscape.py:524
_surface_patch(..., cell=0.72, lift=0.028, ragged=0.55)`. `cell` came down from
1.25, which is real work, and the quilt is gone from every aerial. It is not
gone from the eye. **`alley-walk-03`** is the frame: the bottom half is
hard-edged opaque **saturated emerald** polygons over brown earth and grey
cobble, with dead-straight boundaries at 3–8 m. `ragged` still drops *whole
cells*, so the boundary is still a rectilinear staircase — a 0.72 m step at 3 m
is still a right angle to the eye. Pass 03's fix list asked for three things and
one was done: **feather the alpha over the outer 2–3 cells instead of a binary
in/out, rotate each patch's lattice by a per-patch seeded angle, and desaturate
`grass_lush` by ~25 %.** That last one matters most — this green is still more
saturated than anything else in Hearthmere, including the crimson confectioner.

### 3. The aerial perspective is unchanged from pass 03, and the temperature half of it is dead

`content/town/hearthmere.json → atmosphere.scattering`, authored at
`tools/plan/plan_data.py:ATMOSPHERE`. **`density 0.0058`, `maxOpacity 0.93`,
`fullDistance 130` — all three byte-identical to the values pass 03 rejected.**

**Frames:** `t-approach-ne` (the whole town at 125 m at ~65 % haze),
`t-approach-w` (~65 %), `t-approach-s` (~70 %), all four aerials, and — worse —
`t-square`, where the moot hall **30 m away** is already ~40 % washed, and
`t-gate-south`, where the view through the arch at ~40 m is ~60 % gone.

The measured proof is in `t-report.json → valueBands`: `arrival`
`foregroundToBackground` is now **94.9** (pass 03 measured +92 and called it a
veil, not depth), `midgroundToBackground` is **12.6**, and **`temperatureSwing`
is 0.2** — the warm-near/cool-far separation that Art Bible §1 requires and that
this system was built for is not happening at all in the arrival frame.

**Fix.** As pass 03 specified and nobody applied: `density` → **0.0030**,
`maxOpacity` → **0.62**, `fullDistance` → **300**, then re-run
`town.mjs --bands` and drive `foregroundToBackground` to +45–60 and
`temperatureSwing` above +20. Three numbers, one file, and it changes 79 frames.

### 4. The leaf card is a chequerboard of green squares

**Frames:** `t-approach-s` (40 % of the canonical return camera, at ~5 m),
`t-square` (the market oak, at ~18 m), `kirk-walk-06` (both flanking trees at
6 m), `t-gate-south` (top right).

At LOD0 the sprigs resolve into **regular rectangular grids of dark-green
squares** — a pixel-art chequer, not foliage. This is a regression: pass 03
called the trees "real trees" and the atlas coverage "fixed". Whatever changed
in the leaf sheet or its alpha threshold this wave has produced a hard-edged
dot matrix. `validate.py` flags `leaf_oak` and `leaf_yew` as drifting 5.3 from
the palette; the shape is the bigger problem.

There is also still **no leaf translucency**: at 09:30 with the sun behind,
`t-approach-w`'s field hedge is **pure unlit black** over the bottom half of the
frame, and the `sty-walk-03` canopy blows to pure white where it is lit. One
transmission term fixes both ends.

**Fix.** Look at `leaf_oak_albedo.png` at 100 % before anything else — the
regular grid is in the sheet or in a `shingle_leaves` tiling that is repeating a
single sprig on a lattice. A leaf card must never be laid on a regular grid.
Then a transmission/back-lit term on the foliage material.

### 5. Nothing may stand in a mandated camera, and a tree stands in `approach-s`

`t-approach-s` at (0, 138) looking at (0, 0), eye 6 m. A tree is ~5 m in front
of the lens. `check_walkable.mjs` passes 15/15 because the camera is outside the
wall and no street runs there — so no instrument in the project can see this.

**Fix.** Add a "hero camera clearance" check to the harness: for each named
view, cast the frustum's central 20 % and fail if anything is nearer than 12 m
that is not authored as a framing element. Cheaper immediate fix: move the
`approach-s` station 8 m west, or clear the trees from the south road corridor —
a road approaching a town gate is kept clear of standard trees for exactly this
reason.

### 6. `cobble_wall` has been rebuilt twice and still reads as a missing texture

`tools/assetgen/core/materials.py:2444 cobble_walling()`. I regenerated it with
`--force-textures` and the output is pixel-identical to the shipped sheet, so
the code below the (duplicated) comment block is what you see:
`crop/NEW-cobble_wall.png`. The `coursed` bond is in there, `ident` is being
used, and **adjacent stones still differ by about five luminance levels.** The
`m.darken(dome * per * 0.9, 0.26)` is being cancelled by the four `tint` calls
above and below it, all of which paint the same `dome` mask.

**Frames:** `bailey-walk-04` (the ~30 m featureless run of the enceinte, right
third of frame), `craft-walk-04` (the wall closing the end of Bakers' Row — a
blank beige slab), `mere-walk-05` (the west gate, an untextured arch), `t-gate-
north` (the gate cheeks), `t-approach-ne` (the whole curtain from the water),
`t-approach-w`.

**Fix.** Two things, both one line. (a) Raise the per-stone value spread to
±35 % *luminance* and apply it after the tints, not before, so it is not
overwritten. (b) Deepen the mortar: `m.add_height(dome*1.05 - joint*0.55)` is a
0.55 recess on a 1.05 dome; a river-cobble wall's mortar sits 15–25 mm below the
stone face and that shadow is 80 % of what makes it read. Then **do not use this
key on the enceinte at all** until a render proves it — `venues/wall.py` and
`venues/gatehouse.py` must agree one masonry key with the church's, which is the
best in the build.

### 7. The wall is still 6.3 m, the towers are still 8.9 m and flat-capped

`content/town/hearthmere.json → wall`: `walkHeight 5.2`, `parapet 1.1`,
`towers[].height 8.9`. Unchanged since pass 02.

**Frames:** `t-silhouette` (the wall does not appear in the town's profile at
all), `t-gate-south` (reads as a garden wall — roughly 2× the 1.75 m figure),
`t-approach-ne` (a low pale ribbon under the roofline), `t-approach-w`,
`bailey-walk-04`, `t-aerial-ne`. `t-gate-north`'s twin drums are open-topped
cylinders with a thin cap ring and no roof.

A town wall you can see over from the field gives the settlement no base and no
defensive read. It is also the cheapest silhouette work available: the path and
the heights are **data**, not geometry.

**Fix.** Curtain to **8.5–9.0 m** to the walk plus parapet; towers to **14–16 m
with conical or pyramidal roofs**; a gate with actual doors. Then re-shoot
`t-silhouette` — the profile gains a continuous base line under the whole town,
which is what makes the two towers read as 2.5× instead of 1.8×.

### 8. Five masonry treatments in one frame

**`t-gate-north`.** Left to right: giant-plate ashlar (curtain), a smeared
cloudy mottle with no courses (drum towers), a third block scale (gate
frontispiece), a **"crocodile skin" of wavy heavily-chamfered blocks** (bridge
parapet — the worst masonry in the build; at 3 m it reads as reptile hide), and
a smeared cream-and-brown camouflage (`lime_plaster`) on the building at frame
right that reads as a stained bedsheet draped over a box.

Also in this frame, unchanged from pass 03: **bare putlog beams projecting into
space carrying nothing** (`bailey-walk-04`, top right), the heron keystone
plaque as a flat panel at a different value from its wall, and the gate with no
doors and no portcullis.

**Fix.** One masonry family for the whole enceinte and its gates, ashlar
reserved for dressings, exactly as the church already does it. Then re-cut the
bridge parapet: its `wobble` and its chamfer radius are both roughly double what
they should be.

### 9. The Mere is a stamped ellipse, the Emberflow is a rectangle, and the water is opaque enamel

`atmosphere.water.specularKnee` is **still 1.05** (pass 03 asked for ~0.55).
`content/town/hearthmere.json → water.bodies` still takes its outlines straight
from the terrain channel with no noise.

**Frames:** `t-aerial-sw` — a mathematically perfect oval with a **uniform-width
beach ring** and a far half that is a pure white blowout. `t-plan`,
`t-aerial-ne` — the Emberflow is a **dead-straight parallel-sided canal** with
perfectly parallel banks, which is the most obviously synthetic thing in the
build. `t-approach-ne` — the water is a **solid emerald sheet with visible
triangular polygon facet seams** across a third of the frame, no transparency,
no depth gradient, no reflection of a town standing on its bank. `t-gate-north`
— a **hard sawtooth of flat triangles** where the bank meets the water, at 8 m,
in a mandated hero frame; and a stone bridge over water with **zero reflection**.

**Fix, in value order.** (a) Perturb the `basin` and `channel` outlines with two
octaves of low-frequency noise and let them interpenetrate the terrain — the
shoreline is geometry, not shading, and this alone kills both the ellipse and
the canal. (b) Knee to 0.55 plus a roughness gradient with distance. (c) A
screen-space or planar reflection on the water; a bridge with no reflection is
the tell that stops any water frame. (d) Replace the sawtooth bank with a
battered revetment, reeds, shingle and a wet line.

### 10. The thatch albedo contains no straw

`tools/assetgen/core/materials.py:4755 thatch_variant()`. I regenerated
`thatch_albedo.png` from source: **identical to shipped** — `crop/NEW-thatch.png`
is a flat brown-olive blur with a low-contrast fingerprint whorl and one band of
speckles at the bottom. No stalk direction, no bundle edge, no thickness, no
depth.

And the tile still ramps in `v`: `smoothstep(0.35,1.0,_v)` for age,
`smoothstep(0.4,0.0,_v)` for the lightening, `smoothstep(0.88,0.97,_v)` for the
eaves cut. **A roof tiled three times in `v` gets three eaves bands and three
age gradients.** That is why pass 02 §4's thatch is fixed in one frame and not
in others — the previous agent identified this and did not fix it.

**Frames:** `mere-walk-05` (both roofs — smooth pale cream membranes with
knife-edge eaves and dead-straight ridges), `south-walk-04`, `spine-walk-03`.

**Fix.** Move the eaves cut out of the tile and into the *mesh* — an eaves
course is a separate strip of geometry with its own material, which is what it
is in reality. Then rebuild the field texture with directional stalk noise at
3–8 mm and a bundle edge every 0.3–0.5 m, and give the ridge and eaves real
thickness (60–90 mm) instead of a knife edge.

### 11. Six masses are sunk into the ground and one door is unreachable

`validate.py` (0 failures, 41 warnings) reports geometry below terrain at:
**quay −4.55 m** (48.4, −57.8), **gatehouse −2.65 m** (4.1, −81.0), **wellhouse
−2.80 m** (−38.4, 26.6), **watermill −2.40 m** (−52.9, −84.8), **townhouse
−2.09 m** (57.4, −15.9), **moot_hall −2.03 m** (−13.1, 1.0). `town.mjs`
independently flags moot_hall and wellhouse as sunk masses under §6.1.

`check_walkable.mjs`: 15/15 streets PASS, 0 obstructed — and
**`1 unreachable door(s): hm.townhouse.door.15`**, which fails
`BUILD_DIRECTIVE` §9's first box. The previous agent traced it to
`church.parapet` standing 1.27 m in front of the door and handed it on.

Some of these are legitimate (a quay has a submerged footing; a sunken pub floor
is authored). **None of them are annotated**, so the check cannot distinguish a
cellar from a defect, and a real one will hide in the list. Annotate the
legitimate ones in content and fix the rest.

### 12. All three hero-camera composition defects, third pass running

- **`t-square`:** the lamp standard **still** stands dead centre on the camera
  axis, bisecting the frame top to bottom and cropping the fountain. Its base is
  still a bulbous pale plinth and its column is still a marbled black-and-white
  spiral that reads as polished stone, not iron. `core/streetscape.py:242
  lamp_post`. The `valueBands` for this view come back `None` — **the instrument
  cannot even measure the frame because the lamp fills the foreground band.**
- **`t-gate-north`:** **still** off-axis and low over the water, parapet filling
  the right 45 %, the mandated arch in a ~200 px gap.
- **`spine-walk-01`:** the camera is **still inside the bridge deck** — an
  entirely brown frame. The walk camera takes Y from `terrain.height()` and
  knows nothing about authored decks.

These are three camera definitions. They have survived two explicit rejections.

**And here is what that has cost.** I authored a free camera off the bank
(`bridge-free`, at −22,−88 looking at the crown) and looked at the Emberflow
bridge for the first time in this project. **The asset is good.** Three
segmental arches with real voussoirs and a keystone, cutwaters, triangular
refuges over them, a string course, a coped parapet, a timber rail on the
approach, reeds and a timber revetment at the bank, and a weir throwing white
water at frame left. It is one of the better structures in the build and it has
been sitting behind a broken camera for four passes while three reports called
it a defect.

Its real faults are the build's general ones: the parapet and the gate tower
beside it are the "crocodile skin" masonry (§8); the coping blocks are a fourth,
flat, untextured material; the arch soffits are plain brown planes; and **a
three-arch stone bridge stands over water with no reflection in it at all**,
which is the single tell that stops any water frame (§9).

### 13. The market place and Ford Road carry almost no residue

`t-square`, `crop/arr-fountain.png`, `spine-walk-06`. The town's central space
at 09:30 on a market day: six bare stall frames with no goods, one stall with
hanging produce, a handful of flat grey pebbles that read as decals, some weed
sprigs, and nothing else. No crates, no sacks, no barrels, no straw, no
puddles, no cart ruts, no dung, no dropped cabbage.

By contrast `sty-walk-03` (Sty Lane, a back alley) has washing lines, drying
frames, pallets, a woodpile, bean poles, a barrel and an open door — it is the
best-dressed frame in the build and it is the least important street in the
town. The residue budget is inverted.

Art Bible §7 names this the highest-value detail per unit of effort, and it is.

### 14. The confectioner is a fire-engine-red building on the arrival route

`tools/assetgen/venues/confectioner.py:62 PAINT = "painted_crimson"`, applied at
`:88, :124, :170, :208, :212, :239, :467, :502, :505`. **Frame: `kirk-walk-06`**
— every timber, every mullion, the barge boards, the door, the shopfront frame
and the window surrounds are saturated crimson, with a saturated orange awning
over the oriel. It is the most saturated object in Hearthmere and it stands on
Kirk Green, on the church-to-market sightline, ~25 m from the arrival axis.

Pass 03 asked for the paint to be confined to trim. `geometry-defects` recorded
it as "untouched by design — a colour call". It is a colour call and this is the
review that makes it: **confine `painted_crimson` to barge boards, door and
shutters; put the frame back in oak.**

### 15. Smaller, still visible from the gameplay camera

- **The untextured dark-brown box at the water gate is still there.**
  `wharf-walk-06` at x≈750 — a ~2 m unchamfered box with no material, in a hero
  venue. Pass 03 §15, unchanged.
- **The quay deck is still a modern civic plaza** — a rigid orthogonal grid of
  0.6 m slabs, some inset in recesses (`wharf-walk-08`). A working quay is
  planked, patched, stained and worn in the load paths.
- **The boats do not read.** `crop/ne-boats.png` proves they exist and are
  correctly moored; they are drawn in the same pale timber as the deck they lie
  against, at the same value, and one reads as an open rib frame with no
  planking. Give them dark tarred hulls and a cargo, and they will do the work
  `BUILD_DIRECTIVE` §4 wants from them.
- **The fields are still radial-and-concentric** (`t-plan`, `t-aerial-sw`,
  `t-aerial-ne`) and the fallow is still **pink-mauve**, a hue that appears
  nowhere else in the palette.
- **The field hedges are still solid extruded ribbons with a sinusoidal top
  edge**, and in `t-approach-w` they are pure unlit black across the bottom half
  of the frame.
- **`masonry_wall(uv=1.0)` has produced a chevron textile.** The guild tower in
  `crop/arr-fountain.png` and the gatehouse cheeks in `south-walk-04` and
  `t-approach-w` carry visible diagonal herringbone stripes that read as woven
  fabric or wallpaper, not stone. The moiré it was added to cure has been traded
  for a decorative pattern; it needs a real LOD/mip strategy, not a uv change.
- **Two black unlit blobs** sit on the perron balustrade in `t-arrival` and on
  the churchyard pier in `kirk-walk-06` — finials with no material. The **two
  faceted low-poly stone spheres** pass 03 §13 asked to retire are still on the
  church's flanking piers (`westfront-free`, frame left).
- **The fountain's falling water is flat ribbons** and its spouts are black
  lumps (`fountain-free`). The town's focal point does not survive a close
  approach.
- **The sky.** Clouds appear in about 4 of 79 frames. **No frame contains a sun
  disc**, including `t-arrival`, whose entire upper third is a flat blue
  gradient. `atmosphere.sky` authors `sunAngularSize 1.6` and `cloudAmount 0.34`
  and neither is arriving.

---

## The three changes that buy the most quality per unit of work

**1. Cascade the shadow map and give the figure a contact shadow. (§1)**
Four numbers in `client/src/main.js:74–83` and the same in `town.html`. It fixes
the largest area of visibly wrong pixels in `t-arrival` and `t-square` — the two
frames `BUILD_DIRECTIVE` names as the build's most important — and it improves
every one of the 79 frames at once, because a stepped shadow edge is the single
loudest "this is not a shipped game" signal a frame can carry. **No art
required.**

**2. Retune the atmosphere, then route `uv_scale` through the library. (§3, §2)**
Three numbers in `plan_data.py:ATMOSPHERE` and one mechanical sweep of 421 call
sites. The first gives the town back 200 m of legible depth and restores the
temperature separation that is currently 0.2; the second finally puts this
wave's correct material recipes on screen at their authored scale, which is the
one thing that turns "crazy paving" into "paving". Between them they change the
ground and the air — which is every pixel that is not a building.

**3. Raise the wall, split the terracotta, and dress the market place.
(§7, pass-02 #21, §13)** Three independent edits: `wall.walkHeight` to 8.5–9.0
and `towers[].height` to 14–16 with roofs (data, not geometry); three seeded
terracotta tints in `building.roof_covering` (one pick, and it changes every
aerial); and a day of residue in the market place — crates, sacks, straw, a
tarpaulin, spill — to bring the town's central space up to the standard Sty Lane
already meets. Together these close the "unfinished set" read from the air, from
the field and from the square.

*Close fourth, and it is now cheap because the composition is solved:* put a
west window in the church, an east window or apse behind the altar, clerestory
light shafts reaching the floor, and the worn path from door to altar that §3.1
names explicitly. The arrival frame's outward half now works; its inward half is
a stone box with a blank wall in it.

---

## What the next wave should do, ranked

1. **Shadows and contact.** Cascades or a tightened box; AO on dynamic
   geometry; a contact term under every character and prop. §1.
2. **`uv_scale` through `MATS.uv_scale()`**, all 421 sites, then re-render every
   street. This is what makes the whole of this wave's material work visible.
   §2.
3. **Atmosphere retune.** 0.0030 / 0.62 / 300, then drive `--bands` to +45–60
   separation and >+20 temperature swing. §3.
4. **Foliage emergency.** Find and kill the chequerboard leaf grid; add a
   transmission term; clear the tree out of `approach-s` and add a hero-camera
   clearance check to the harness. §4, §5.
5. **One masonry family.** Enceinte, gates and bridge on the church's key; fix
   `cobble_wall`'s value spread and joint depth or retire it; re-cut the bridge
   parapet's wobble and chamfer. §6, §8.
6. **Skyline.** Curtain 8.5–9.0 m, towers 14–16 m with roofs, gates with doors.
   §7.
7. **Water.** Noised shoreline outlines (kills both the ellipse and the canal),
   knee 0.55, a reflection, a battered bank at the bridge. §9.
8. **Thatch.** Eaves cut out of the tile and into the mesh; real stalk
   structure; thickness at ridge and eaves. §10.
9. **Residue rebalance.** Market place and Ford Road up to Sty Lane's standard;
   goods on the stalls; cargo and tarred hulls on the boats; a planked, worn
   quay deck. §13, §15.
10. **The three hero cameras**, again: lamp off the `square` axis, `gate-north`
    onto the bridge centreline, and the walk camera onto authored deck levels.
    Add `bridge` and `westfront` to the standard set — both are hero
    compositions and neither is in it. §12.
11. **The church.** West window; east window or apse behind the altar;
    clerestory light reaching the floor; the worn path §3.1 names; the tower on
    or within ~6 m of the west-door axis; retire the faceted spheres. The
    composition around it is now good enough that this is the cheapest big win
    left. §12/§13 of pass 03.
12. **The fountain's water.** Volumetric falling water with a splash, a rippled
    basin surface, and bronze that reads as bronze. §(a).
13. **Correctness sweep.** Annotate or fix the six sunk masses; close
    `hm.townhouse.door.15`; delete the untextured box at the water gate; confine
    `painted_crimson` to trim; give the black finials a material. §11, §14, §15.
14. **Fields.** Break the radial-and-concentric layout; re-hue the pink-mauve
    fallow; replace the sine-topped extruded hedge ribbons. §15.
15. **Sky.** Get the authored sun disc and 0.34 cloud amount to actually
    render. §15.
16. **Draw calls.** 1,416 against a 900 budget, and §7's own required "texture
    atlasing across the kit" has still never been done (538 batches, 2.8 draws
    per batch). Not what is wrong with these frames — but it is the last box on
    §9 and it will not fix itself.

---

## Would any of these frames survive a blind side-by-side against a shipped AAA MMO?

This is the question the project turns on, so here is a precise answer rather
than a mood.

**Three frames survive the first two seconds.**

1. **`t-gate-south`** — the strongest frame in the build. Real sett paving with
   a kerb, a gutter, a verge and a wear pattern; a wall with a batter, a coping
   and putlog holes; a gatehouse with a proper arch, a chamber over it, a tiled
   roof and a chimney; dappled tree shadow across the road; a barrel, bollards,
   a mounting block and a planted tub; and a legible view through the arch into
   the town. Put this next to a Divinity's Reach outer gate and it holds its
   ground for the length of a glance.
2. **`spine-walk-06`** — Ford Road looking south. Two coherent street walls of
   jettied, half-timbered, brick-nogged, shuttered buildings; an open cart shed
   with a real cart, a wheel, a barrel and a plank stack; a tree in the middle
   distance; correct kerb-gutter-verge; correct aerial perspective for once.
3. **`sty-walk-03`** — Sty Lane. The best-dressed frame in the project: washing
   lines, drying frames, pallets, a woodpile, bean poles, an open door, a barrel,
   dappled shade, and — rare in this build — clouds.

**What those three have in common, and it is not luck:** *the subject of the
frame is timber and dressed stone, and the ground is either setts or compacted
earth.* Every one of them avoids all four of the build's systemic failures —
they contain no crazy paving, no `cobble_wall`, no water, and no leaf card at
close range.

**None of the three survives ten seconds**, and each fails for a reason on the
list above:

- `t-gate-south`: the wall is 2× the figure and reads as a garden wall; the
  gatehouse piers are a different material from the gatehouse; the thatch at
  frame left is a cream membrane; the tree at top right is the chequerboard
  leaf; the figure has no contact shadow; the sky is empty.
- `spine-walk-06`: the sky is empty, the figure floats, and the far third is
  over-hazed.
- `sty-walk-03`: the washing is flat paper rectangles with dead-straight hems,
  and the foliage is plastic cards blowing to pure white.

**Two frames are close and are held back by one thing each.** `t-silhouette`
would pass as a concept elevation today — it fails only because the wall gives
the town no base line. `t-arrival` has solved its composition — steps, street,
focal point, tower — and fails on the stair-stepped shadow across its floor and
the flat single-value cream of everything past 25 m. Both of those are on the
top-three list above, which is why the top-three list is what it is.

**Everything else fails inside two seconds**, and always on the same four
things: the ground surface (§2), the shadow edge (§1), the water (§9), or a
leaf at close range (§4). That is a much shorter and much cheaper list than
pass 03's, and it is the reason this report reads as a REJECT with a route out
rather than a REJECT with a wall in front of it.

---

## Budget, for the record

`t-report.json`, worst gameplay camera (`square`): **1,416 draw calls / 900**
(**1.57× over — BUDGET GATE FAILED**, `EXIT 3`), **2,880,832 triangles /
3,500,000** (in budget). Attribution: scene 498 + shadow 600 + AO 257 + post 61.
Client and harness agree to 0.7 % from the identical camera, which is this
wave's instrumentation win and it is real.

`validate.py`: **0 failures, 41 warnings** in 40 s — the harness is honest now
and that matters more than the number.
`check_walkable.mjs`: **15/15 streets PASS, 0 obstructed, 1 unreachable door.**
`check_client.mjs`: boots, 2,534 collision volumes, 258 entities, walks 151.5 m.
Mesh memory 239.4 MB against a 240 MB budget — 99.75 % consumed, which is not a
budget, it is a cliff.

The budget is still not what is wrong with these frames. But §7's required
texture atlasing has never been done, 538 batches yield 2.8 draws each, and the
draw count has now failed the gate in two consecutive passes. It is the last
unticked box in §9 that no amount of art will close.
