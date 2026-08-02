# Ground and stone — the pass-03 material find

Scope: `ad-town-03` §1 (the crazy paving is `stone`/`limewash`, not `rubble`),
§14 (`ivy` is an opaque green sheet doing three jobs), §2 (the intramural ground
blend is a quilt of opaque axis-aligned rectangles), plus a tile-repeat audit of
every material in `core/materials.py`.

Before/after frames are in `review/shots/mat-04/`, shot at the same cameras
`ad-town-03` recorded in its own frame headers, so they diff directly against
`review/shots/ad-town-03/`:

| after | before | what it shows |
| --- | --- | --- |
| `kirkgate2-free.png` | `ad-town-03/kirkgate2-free.png` | the frame §1 cites — wall, plinth, steps and road in one shot |
| `westfront-free.png` | `ad-town-03/westfront-free.png` | church west front, Kirk Green paving |
| `paving-free.png` | `ad-town-03/crop/market-paving.png` | the market paving and its joints |
| `fountain-free.png` | `ad-town-03/crop/fountain.png` | the fountain's own material |
| `sty03-free.png` | `ad-town-03/sty-walk-03.png` | a back lane — the ground blend |
| `bailey04-free.png` | `ad-town-03/bailey-walk-04.png` | the enceinte and the ground quilt |
| `t-square.png`, `t-arrival.png`, `t-aerial-ne.png` | same names | the hero frames |

---

## 1. The root cause under §1: the mortar joint was sub-pixel

`core/materials.py coursed()` is the shared bond generator — brick, ashlar,
sett, slate, plank, sandstone, flagstone and `rubble_weathered` all lay their
units with it. Its joint-width line read

```python
d = np.minimum(np.minimum(tx, 1 - tx) * cols, np.minimum(ty, 1 - ty) * rows)
```

`tx` is already unit-local, so the tile-fraction distance to a perpend is
`tx / cols`. Multiplying scales the joint down by `cols²`, and it scales the two
axes in opposite directions, so beds and perpends came out different widths the
wrong way round.

Measured on `rubble` (6 x 8 units on a 2 m tile at 512 px): the mortar was
**3.4 mm wide — 0.9 of one texel**. It filtered away to nothing in the albedo
and to nothing in the normal map.

That is why last wave's `rubble_weathered` rebuild — which was correct work, on
the right function, with the right bond — changed nothing the art director could
see. The wall was brought to course and then the course lines were thrown away
by the filter. `crop/tex-rubble.png` in `ad-town-03` shows exactly that: bedding
present, stones bleeding into each other, no joint anywhere.

Fixed: `joint` now means *half-width as a fraction of the shorter unit side*,
which is what the docstring always claimed. `joint=0.055` on a rubble tile is
27 mm of mortar. Four callers were re-derived against a real width in
millimetres (`ashlar_civic` 4.5 mm, `sandstone` 8 mm, `flagstone` 19 mm,
`rubble`'s coarse second lattice 26 mm); the rest were already sane once the
scaling was right.

## 2. `stone` and `limewash`, rebuilt on `coursed`

**`foundation_stone` (`LIBRARY["stone"]`)** — the church, the fountain, the
plinths, the perron steps, the market paving; §1 measured it at ~60 % of the
pixels in the arrival frame. It was four lines: two interleaved Worley fields
(isotropic by construction — crazy paving), value variation from two independent
`fbm` fields that blur *across* stones rather than keying to them, and a
`ground_splash` that darkens the bottom of the sheet.

Now: `coursed` at 9 courses x 5 units (0.40 x 0.22 m stones) with `wobble=0.40`
— lower than rubble's 0.62 because these are the *dressed* stones; a drafted
margin and camber per face; boaster tooling; value keyed to `coursed`'s own
`ident` at ±21 % plus a within-stone cloud; warm lime-grey mortar with grit;
lichen as patches. No `ground_splash`.

**`limewashed_stone` (`LIBRARY["limewash"]`)** — the pale market paving, with
olive-green joints. Same Worley fault, plus `cavity_dirt` tinting the joints
toward `P.AO_TINT`, which on a sheet that pale lands olive. Now a `coursed`
substrate with per-stone value at ±24 %, a wash whose coverage is keyed to the
joint and to the stone identity (limewash pools in a joint and wears off a proud
face, which is what makes the bond read *through* the coat), and a warm lime
grey in the joint instead of the AO tint.

## 3. The tile-repeat audit

I audited all 90 library entries for two faults, both of which put a feature the
size of the tile into a tiling texture. The rule is now written into
`core/materials.py` above a new `mottle()` helper, with `FREQ_FLOOR = 6`.

**Fault A — a gradient in u or v.** A tiling material cannot know where the
ground is or which way is up; any ramp in u or v is a hard band once per tile.
On a 24 m curtain wall at 2 m coverage that is twelve bands.

| material | what it banded | fixed |
| --- | --- | --- |
| `stone` | `ground_splash` — dark band at the foot of every tile | yes, removed |
| `limewash` | renewal coat banded across the lower third | yes, now patches |
| `rubble` | moss ramped up from the bottom edge — **the flaw the agent who rebuilt it declined to sign off** | yes, now patches |
| `hedge` | "new growth at the top" — a yellow band every 2 m along a 60 m field boundary | yes, now patches |
| `sett` | two wheel ruts at fixed `u` — **seven pairs of ruts across a 14 m carriageway, in register, every 2 m along it**; this is §15's "obvious light/dark chequerboard" | yes, now patchy polish |
| `cobble` | a diagonal "desire path" through the tile centre — five parallel diagonal stripes across a 10 m lane | yes, now patchy polish |
| `flag` | a worn band down the middle of every tile — a corduroy across the nave rather than one path door-to-altar | yes, now patchy wear |

Not fixed, and named for the next pass: `thatch_variant` ramps its eaves
treatment in `v`, which on a 6 m roof pitch at 2 m coverage draws **three eaves
bands up every thatched roof**. That is a strong candidate for pass-02 §4's
"smooth pale cream membrane with knife-edge eaves" surviving in `mere-walk-05`
and `south-walk-04` after being fixed in `spine-walk-06` — the difference
between those roofs may simply be how many tiles fit up the pitch. I did not
touch it because thatch was outside this brief and it needs its own render pass.
`canvas_awning` and `banner_cloth` also ramp in `v`; both are small objects
where one tile covers the whole piece, so they are defensible.

**Fault B — one low-frequency blob per tile.** `fbm(s, 3)` puts about one
feature across the sheet, which repeats as a lattice of identical light and dark
patches. Fixed in `rubble` (the per-lift mask), `sett`, `cobble`, `flag`. Twenty
other entries carry `fbm(s, 3..4)` terms; most are on props where one tile
covers the object, and I left them.

## 4. `ivy`, and the three-way green split

`ivy_albedo.png` was an opaque green Voronoi sheet with **no alpha channel at
all**, so `vegetation.ivy_panel`'s quads and `venues/wall.py`'s ivy boxes
rendered as solid green rectangles pasted on the wall. That single texture is
simultaneously §14's "green daub doing wall infill" and §18's "flat rectangular
ivy" — one material, two findings.

Added `core/materials.shingle_leaves()`: a **tiling** mat of overlapping cut-out
leaves resolved Worley-style over a 3 x 3 neighbourhood, so cost is nine
evaluations per pixel whatever the leaf count and the sheet wraps exactly.
`leaf_cards` was the wrong tool — it builds a 4 x 4 *atlas* of discrete sprays
for tree cards, and a wall climber has no cell boundaries.

The old green mottle is now three materials:

- **`ivy`** — palmate 5-lobed leaves at 17 cm, alpha-cut (MASK + double-sided),
  palmate venation from the petiole, bronzed margins, brown aerial-root stems
  running up the wall through the gaps in the mat.
- **`hedge`** — still a MASS, but built from the same leaf scatter at hawthorn
  scale (5 cm) under a two-scale clump shadow, and **cut at clump scale**: a
  hedge now loses about a tenth of its area, which is what stops §19's "solid
  dark-green extruded ribbon" reading as rubber. Because `hedge_run` is
  double-sided the holes show the far face's interior, which reads as depth.
- **`weeds`** — new key. Ovate rosette blades and grass through the gaps,
  alpha-cut. `vegetation.joint_weeds` and `tussock` now default to it, which
  retires §14's "large flat saturated-green triangles lying on the paving".

`foliage` keeps its opaque sheet for produce and cabbage globes, where a cut-out
would punch holes in solid objects.

## 5. The intramural ground blend

`venues/landscape.py:_surface_patch` — §2's "quilt of opaque axis-aligned
rectangles" and "the ugliest thing in the build". Three causes, all rewritten:

1. **`cell=1.25` with a whole-cell drop.** `ragged` deleted entire cells at the
   margin, so the boundary was a staircase with a 1.25 m tread, which at 3 m is
   a right angle. Replaced with a real distance feather: survival probability
   falls off smoothly over 1.35 m of the polygon edge and the cell is 0.45 m,
   so the margin is a stipple of tufts thinning out — which is how grass stops.
2. **The lattice was the world grid.** Every patch shared one axis-aligned
   lattice, so every patch edge was parallel to every other. Each patch now
   builds in its own frame at a per-patch seeded angle.
3. **The boundary was the polygon.** A burgage plot is a quadrilateral, so a
   skin clipped to one is a quadrilateral however ragged its edge. The polygon
   is now only the centre of the probability ramp; two octaves of noise push the
   effective boundary in and out by up to a feather width, so cover spills
   through the gate and dies back under the eaves.

Cost, and it is the one number that constrained this: at the 0.45 m cell the
feather read best and put §7 mesh memory at **241.7 MB against a 240 MB
budget** — `tools/validate.py` failed on it, correctly. Backed off to a 0.72 m
cell with a 1.6 m feather and `_intramural` from 1.8 m to 1.35 m, which lands at
**239.4 MB, 0 failures**, and I re-shot `bailey04-free` and `westfront-free` at
the final settings to confirm the margin still reads as a margin and not as a
step. If somebody frees mesh memory elsewhere, `_surface_patch(cell=...)` is a
good place to spend it. `grass_lush` is desaturated 22 % toward `COBBLE_WORN`
per §2's last line.

**And a fourth cause, which none of the above would have fixed.** Comparing
`sty-walk-03` against `crop/ground-quilt.png` I noticed the lane in Sty Lane is
a quilt of dark and light rectangles *in a single material* — so the cover
boundaries were only half the finding. Both ground layers drew

```python
g = 0.72 + 0.24 * rng.random()          # once per CELL
b.poly(q, ..., colour=(g, g, g))        # flat across the whole quad
```

An independent draw per cell, applied flat to all four corners, means adjacent
cells differ by up to a quarter of a stop with a hard edge on the cell boundary.
That is a patchwork of *value* laid over the ground independently of what
material is on it, and it survives every fix to the cover boundaries because it
does not depend on them. Replaced with `_ground_value(x, z)` — a continuous
three-scale world field sampled **per vertex**. `_lattice` shares corners
between neighbours, so the value now interpolates across each quad and no cell
boundary can be seen. Amplitude is also a third of what it was.

Also added, per §2's "transitions following how ground actually wears": a
trodden apron in front of every building's street door (2.4 m, noise-broken),
and `mud` rather than lush grass in the bottom 0.85 m above the water line.

## 6. Also fixed while in the file

`cobble_walling` (`LIBRARY["cobble_wall"]`) — §1 and §10's "featureless beige
plane over a ~30 m run" of the enceinte, the treatment that reads as an
*untextured* wall. Rebuilt on `coursed` like every other laid wall in the file:
the old body kept only the Worley cell cores (`clip(1 - d * 2.1)`), so the sheet
was ~80 % mortar with isolated pebbles floating in it, and its per-stone colour
came from an independent `per_unit` field that blurs across stones. Now ~60 %
stone in rough courses with the value keyed to the unit.

`ashlar` — a hand-rolled copy of `coursed` (the fifth in the file, per that
function's own note about drift) carrying the same inverted joint scaling.
Routed through the shared generator, so the guild's ashlar inherits the fix.

`cobblestone` — the largest green in the town. Its joints were tinted
`HERB_GREEN` at 0.55 along **every joint of every cobbled street**, which is
§14's green mortar at far larger scale than the market paving. Now warm-grey
sand and grit, with moss at a third the strength and only in patches. Its
stones also had the `foundation_stone` fault — value from an independent
`fbm(s, 26)` rather than from the cell — so a street read as flat grey mud past
4 m. That needed a core extension: **`mathx.worley` now takes
`metric="id"`**, returning a stable 0..1 per cell, which is the missing
primitive that made per-stone colour impossible for every Worley-based material
in the library.

`lime_plaster` — §1's "blurry blue-grey/cream mottle with no structure" and
§(c)'s camouflage gable. Its three low-frequency terms (`fbm(s, 3)`,
`fbm(s, 4)`, `albedo_break(broad_freq=4)`) were each about one blob per tile, in
three slightly different creams, repeating on a 2 m lattice. All three lifted
above `FREQ_FLOOR`, `albedo_break`'s `warm` cut from 0.30 to 0.12 (the default
cools the lows toward blue, which is where the blue-grey came from), and trowel
arcs added to the albedo so the surface has a direction.

---

## Before and after, read from the PNGs

Every claim below I checked against the image, not against the diff.

**Fixed, and I would sign it off.**

- **The crazy paving is gone from the frame §1 names.** `kirkgate2-free`: the
  retaining wall, the plinth, the steps and the building's flank are all coursed
  masonry with discrete stones and bed lines. Before, every masonry surface in
  that frame was Worley polygons with no bedding and no value difference
  between neighbours.
- **Kirk Green.** `westfront-free`: the paving reads as setts laid in courses.
  Before it was flat blue-grey slabs carrying a 1.8 m light/dark chequerboard.
  The churchyard walls and the church piers are coursed.
- **The market paving's green mortar is gone**, in both `paving-free` and
  `fountain-free`. So is the green in every cobbled street.
- **The fountain is no longer built of the ground it stands on.** `t-square`:
  the basin, step rings and pillar read as coursed stone against the paving.
  (It is still ~3 m to the finial, which is §(a) and not mine.)
- **The Sty Lane quilt is gone.** `sty03-free` against `ad-town-03/sty-walk-03`:
  a checkerboard of ~2 m dark and light rectangles down the middle of the lane
  has become a continuous earth surface with a few soft irregular patches.
- **The Bailey quilt is gone.** `bailey04-free` against
  `ad-town-03/bailey-walk-04`: the emerald right-angled quads are down to a few
  small scraps that read as grass in the joints.
- **The enceinte's untextured run is textured.** `bailey04-free` left: the
  ~30 m of `cobble_wall` that read as a missing texture now has stones.
- **From the air**, `t-aerial-ne` no longer shows a green pixel-quilt between
  the houses.
- **Ivy is a cut-out.** `assets/textures/ivy_albedo.png` is now palmate leaves
  with real holes in the sheet, against an opaque green Voronoi before.
- **Hedges are leafy.** `sty03-free` left.

**Fixed but I would NOT sign it off yet.**

- **`cobble` on the market place is at roughly 3x its authored scale.**
  `fountain-free` and `paving-free`: the stones read at 50-60 cm when the
  material authors 17 cm ones on a 2 m tile. The texture is now right — per-stone
  value, grey grit, domed stones — but the geometry that lays it is passing a UV
  scale that stretches it, so it still reads as crazy paving at gameplay range.
  This is D-024's problem, not a material one: **346 call sites pass a literal
  `uv_scale=` instead of `MATS.uv_scale(key)`**, and until they are audited no
  texel density in the town can be trusted. That audit is the single highest
  remaining item in this area and I did not have the budget for it.
- **`cobble_wall`** now has stones but they read as angular cracked plates
  rather than rounded river cobbles. Better than untextured, not right.
- **`lime_plaster`** is less camouflaged and no longer repeats a blob per tile,
  but its albedo is still fundamentally a mottle. I moved it; I did not fix it.
- **`limewash`** is coursed and its joints are grey, but the wash is uniform
  enough that the bond is faint at 8 m. It is defensible for limewash and I
  would want the art director's eye on it rather than my own.

**Not fixed, and named so nobody has to find them again.**

- **`thatch_variant` ramps its eaves treatment in `v`**, so at 2 m coverage on a
  6 m pitch it draws three eaves bands up every thatched roof. Strong candidate
  for why pass-02 §4's thatch was fixed in `spine-walk-06` and not in
  `mere-walk-05`. Needs its own render pass.
- **`_intramural_ground` still meets its covers along cell edges.** The value
  quilt is gone and the module is down to 1.15 m, but two different covers still
  butt at a hard line. Doing it properly needs an alpha channel on the ground
  materials and a vertex-alpha feather; three.js honours COLOR_0 alpha under
  `alphaTest`, so the route exists (texture alpha held in [0.55, 1] keeps the
  terrain, which shares these keys, fully opaque). I costed it and did not do it.
- **`tools/validate.py` now passes: 0 failures, 40 warnings** (all 40 pre-date
  this work — sunk geometry, cell draw-call spikes, two leaf atlases off §4).
  It did fail on mesh memory at my first settings; see §5.
- **`check_client.mjs` FAILS the §7 draw budget**: 1379 draws at the arrival
  camera against 900 (scene 559 + shadow 526 + ao 227 + post 67). I did not
  measure a baseline before my changes and I cannot honestly attribute it. What
  I can say: the town report's total draw calls went **down** 2641 → 1427 over
  `ad-town-03`, and scene-graph triangles went **up** 3,974,759 → 4,188,884
  (+5.4 %), which is the ground patches. The new `weeds` key adds one primitive
  per cell it appears in. Somebody should bisect this.
- The over-chamfered "foam block" arrises on the enceinte (§10) are geometry,
  not material, and are unchanged.

## Files changed

`tools/assetgen/core/mathx.py` (`worley(metric="id")`),
`tools/assetgen/core/materials.py` (`coursed`, `mottle`/`FREQ_FLOOR`,
`shingle_leaves`, `foundation_stone`, `limewashed_stone`, `rubble_weathered`,
`cobble_walling`, `ashlar`, `cobblestone`, `granite_sett`, `flagstone`,
`lime_plaster`, `ivy`, `ground_weeds`, `hedge_mass`, `grass_variant`, LIBRARY),
`tools/assetgen/core/vegetation.py` (route weeds/tussock to the new key),
`tools/assetgen/venues/landscape.py` (`_surface_patch`, `_ground_value`,
`_poly_edge_dist`, `_intramural_ground`),
`tools/assetgen/venues/streets.py` (`_dress_field`, `_carriageway`).
