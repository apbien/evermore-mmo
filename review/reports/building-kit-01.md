# Art-director review — the modular building kit

**Subject:** `tools/assetgen/core/building.py`, `tools/assetgen/core/roof.py`,
`tools/assetgen/venues/townhouse.py`
**Built:** `python tools/assetgen/build.py --skip-textures --venue townhouse`
→ 63 buildings, 615,554 tris, 826 draws, 9 party walls
**Rendered:** `review/shots/ad-kit/*` (12 frames, `shoot.mjs`, free cameras at
gameplay eye height and at oblique), `review/shots/ad-town/*` (plan, aerial-ne,
silhouette). All at the locked 09:30 rig.

---

# VERDICT: **REJECT**

Not a close call. Thirteen percent of the buildings this kit generates have
**no roof at all** — open-topped boxes with a ridge line and barge boards
hanging in mid-air above them, visible from the street, from the air, and in
the orthographic town plan as black holes. That alone ends the review. Behind
it sits a party-wall system that does not close a terrace, a roof covering that
is a flat orange decal on the largest surface in the town, and a variance model
that produces sixty-three shuffles of one house.

The bones are right. `roof.py`'s "a roof has no position of its own" is the
correct architecture and it is doing its job — nothing in these frames floats
*because a Y was authored wrong*. The failures below are all downstream of that
good decision, and most of them are cheap to fix. But this code will stamp
seventy to ninety masses, and every one of these defects ships eighty times.

---

## Findings, ordered by damage to the frame

### 1. Every `half_hip` roof has zero roof area. Eight buildings are roofless.
`tools/assetgen/core/roof.py:429-431`, root cause at `roof.py:292-307`

```
hm.slot.09.townhouse_b  half_hip  slope areas [0.0, 0.0, 2.3, 2.3]  plan 60.0 m2
hm.slot.10.townhouse_c  half_hip  slope areas [0.0, 0.0, 1.3, 1.3]  plan 36.0 m2
hm.slot.30.cottage_d    half_hip  slope areas [0.0, 0.0, 3.0, 3.0]  plan 72.0 m2
hm.slot.42.cottage_f    hm.slot.63.warehouse_c    hm.slot.75.cottage_r
hm.slot.80.malthouse    hm.slot.81.cottage_s
```

The jerkinhead solver builds the two main slopes, then cuts them with the two
hip planes:

```python
for sl in slopes[:2]:
    for hp in slopes[2:]:
        sl.clip_plane(hp)
```

`Slope.clip_plane` keeps the half-plane where **self is above other** — correct
for a valley, inverted for a hip. The hip plane springs at `y_spring` on the
gable end and keeps rising past its apex, so over the body of the roof it sits
metres above the main slope; the clip therefore keeps only the small triangle
at each gable that the hip is supposed to *replace*. Two hips, two opposite
slivers, empty intersection.

Evidence: `review/shots/ad-kit/pw10-free.png` (slot 10 as an open walled
enclosure with two tiled fins inside it), `obC-free.png` and `obD-free.png`
(interiors visible from the air), `sec30-free.png` (a string of ridge tiles
floating in clear sky with nothing beneath it), `ad-town/town-plan.png` (eight
black rectangles in the settlement plan).

**Fix:** for the half-hip case clip with the opposite sense — cut the main
slope where the hip plane is *below* it. Cleanest is a `keep="below"` argument
on `clip_plane` (default `"above"`, preserving valley behaviour) and pass
`keep="below"` from `roof.py:431`.

### 2. Nothing checks that a roof covered its plate, so the trim ships anyway.
`roof.py:870`, `roof.py:897-901`, `roof.py:917`

The empty-slope filter at line 870 only runs inside `if clip_against is not
None`. Degenerate slopes from the half-hip path survive into `_deck`,
`_tile_slope`, `_fascia`, `_verge`; `ridge_line` is computed from the solver
and capped unconditionally at 897; `_closures` then builds a full-height gable
panel by querying a surface that no longer exists. That is why the failure mode
is not "a missing roof" — a missing roof would be a hole — but **a floating
ridge, floating barge boards and floating hip tiles over an open box**, which is
strictly worse and is the single most obviously broken thing in the build.

**Fix:** in `roof_from_plate`, after the solver, drop slopes with
`area() < 0.05` unconditionally, then assert the surviving slope area covers at
least 80 % of the plate polygon area and raise if not. This module already
argues in its header that a roof cannot be mispositioned by construction; the
same guarantee has to cover "a roof exists".

### 3. Party walls do not make a terrace. Two boxes touch, with a slot between.
`building.py:1162` (`t = 0.36`), `building.py:1174-1176`,
`building.py:844-851`, `townhouse.py:47` (`PARTY_GAP = 0.45`)

Three compounding defects:

**(a) The wall is too thin for the gap it spans.** Both neighbours skip the
shared edge (844-851). The owner's prism is 0.36 m thick and `M.prism` centres
the extrusion, so it reaches 0.18 m from the owner's wall face. Measured gaps
in the schedule: 0.437, 0.417, 0.413, 0.308, 0.25, 0.239, 0.051, 0.047, 0.01.
**Six of nine terraces have an open, full-height slot** — up to 0.26 m of
daylight straight into the neighbour's interior. `pw44-free.png` shows a
background roof visible *through* the tightest pair (gap 0.01) at the junction.

**(b) The wall guesses the neighbour's roof instead of asking it.**
`yo = o_ridge - o_pitch * abs(tt)` assumes the neighbour presents a gable at
their pitch, centred on this wall. For `hm.slot.10.townhouse_c` the party edge
is an *eaves* edge (`ridge_axis="v"`, edge 3) and the neighbour has a **hip**;
the wall is built as a fake raked gable rising to 9.31 m against a roof whose
eaves is at 5.82 m. That fake gable is the pale slab standing in the middle of
slot 10 in `obA-free.png`.

**(c) It does not read as a party wall.** In `pw44-free.png` and
`pw10-free.png` the junction is a narrow dark perforated strip between two
roofs that die into each other. There is no proud raked coping, no visible
lead. `pw30-free.png` shows the coping where it does stand proud, and its
ashlar UV (`uv_scale=0.6` on a 0.36 m wide prism) reads as a grey chequerboard.

**Fix:** build the party wall on the *mid-line between the two footprint
edges*, with thickness `gap + 2 × 0.20` so it bears on both walls; take its
profile from `max(roofA.surface_y, roofB.surface_y)` by querying both `Roof`
objects (build both neighbours' roofs before either party wall, which
`plan_building`/`find_terraces` is already structured to allow) rather than from
a gable approximation; raise the coping 0.20 m proud and give it a real
weathered section instead of a slab. Drop `PARTY_GAP` to 0.30 and widen the
wall to suit, or re-space the schedule.

### 4. The roof covering is a flat decal, and it is the largest surface in town.
`roof.py:48-49` (`EXPOSURE 0.16`, `TILE_T 0.030`), `roof.py:513-552`,
`building.py:184-237`

At 12 m (`pw44-free.png`) and 20 m (`bede-free.png`) the roof is a uniform
orange plane with a fine diagonal weave and a handful of stray dark lines. The
course-step lip is 30 mm and it is the only relief there is: at the locked 38°
sun it casts nothing, so the promise in this module's own docstring — "that
step is what a roof reads by at 100 m" — is not being kept. There is also **no
tile-level colour variation**, which Art Bible §4 explicitly requires
(`terracotta aged #8F4E36`, ~30 % of tiles).

Worse, the kit has one roof material. `STYLES` puts `roof_mat="terracotta"` on
eight of ten styles; `slate` appears only on `stone_civic`, which the kit never
instantiates; `thatch` appears on one building, and that one is a half-hip so
it is roofless. **62 of 63 roofs are the identical orange.** The aerial
(`ad-town/town-aerial-ne.png`) is a rash of orange rectangles with no
district, no wealth gradient, no hierarchy — the exact opposite of Divinity's
Reach or the Ul'dah rooftops.

**Fix, in order of value:** (i) deal `roof_mat` per building from a weighted
table per style — slate for `merchant_townhouse`/`stone_civic`, thatch for the
poorest cottages and the back lanes, terracotta as the majority — so the plan
reads stratified; (ii) push `TILE_T` to 0.055 and give each course a ±8 mm
seeded offset so the eaves saw-tooth and the ridge line break; (iii) add a
per-course albedo tint index (aged/fresh/mossy) so a roof is not one colour.

### 5. The variance is noise on a single archetype, not real variance.
`building.py:184-237`, `building.py:283-307`

Distribution over the 63 masses this kit builds:

```
styles     cottage_tile 33 · merchant_townhouse 11 · back_lane_shed 9
           waterfront_warehouse 6 · artisan_workshop 2 · almshouse_row 1
           cottage_thatch 1        (shopfront_terrace, stone_civic, byre: 0)
roof mat   terracotta 62 · thatch 1
frames     cross 34 · square 21 · close 7 · herring 1
plan       every building is a single rectangle. No L-plan, no wing, no
           cross-gable, no valley — despite roof.py supporting clip_against.
```

Wall build-up is `["rubble","timber"]` or `["timber"]` on every style the kit
reaches. `limewash`, `brick` and `plastered` exist in `WALL_MAT` and in
`materials.LIBRARY` and are never used. `mere-free.png` is the proof: forty
metres of street where left and right are the same object rotated, and there is
not one colour, material or massing difference between any two buildings.

Eighty of these will read as eighty shuffles of one house. **Fix:** wall
material and roof material must be dealt per building from a weighted table the
way `ROOFS` and `FRAMES` already are, biased by `wealth` and by district; and
the kit needs at least one non-rectangular plan — a rear wing roofed with
`clip_against`, which `roof.py` already supports and nothing calls.

### 6. Trim survives onto slopes it does not belong to and floats.
`roof.py:650-706` (`_fascia`), `roof.py:760-790` (`_verge`),
`roof.py:709-734` (`_plate_dist` reach guard)

`rope-free.png` has a dark board hanging in clear air off the left gable
(x≈150, y≈455). `pw30-free.png` has a plank crossing the whole frame,
attached to nothing. `mere-free.png` has rafter feet projecting past the gable
end over nothing. The `reach` guard tests the board's *midpoint* only, so a
board whose midpoint is over the plate and whose end is 2 m past it passes.

**Fix:** test both endpoints against `_plate_dist`, and clip the board to the
reachable span rather than accepting or rejecting it whole.

### 7. The kit has no bay articulation, so long buildings are dead walls.
`building.py:820-926` (`_walls`), `building.py:464-499` (`masonry_wall`)

`bede-free.png`: 24 m of unbroken rubble under one unbroken roof plane with six
identical doors and no chimneys at all (`almshouse_row` sets `chimneys=0` for
six dwellings). `rope-free.png`: 24 m of dead grey wall with one window and one
door. Art Bible §7 forbids more than 12 m of undifferentiated facade. The kit
has no mechanism to break one — no bay piers, no buttresses, no recessed unit,
no stepped ridge, no material change along a run.

Also visible in `rope-free.png`: `masonry_wall` builds one box per
`subtract_rects` panel with a ±3 % depth jitter, and on a 24 m wall those panel
seams read as three horizontal construction lines across the whole facade.

**Fix:** where `length > 12 m`, split the run into bays at 4–6 m, step the
plinth and the ridge between them, and alternate wall material. That single
change turns the almshouse row into six houses.

### 8. The catslide outshut is unusable and its window breaks out of the wall.
`building.py:1032`, `building.py:1048-1049`

Head height above floor, for the 13 catslides:

```
privy_row 1.28 · gateward_w 1.31 · sexton 1.33 · shed_a 1.46 · gateward_s 1.51
gateward_n 1.54 · cottage_t 1.57 · byre 1.60 · cottage_m 1.74 · cottage_k 1.75
cottage_x 2.03 · workshop_a 3.52 · cordwainer 3.67
```

Eleven of thirteen are below 1.8 m; nine are below 1.62 m, i.e. below the
player's eye. The window punched at line 1049 is 0.94 m tall centred at
1.05 m, so its head is at 1.52 m — **above the wall plate on eight of them**.

`obC-free.png` and `obD-free.png` also show what a catslide reads as from
above: one enormous unbroken orange rhombus running to the ground with nothing
under its lower half. **Fix:** clamp `catslide_run` so `head - floor_y >= 2.05`,
and skip the outshut window when `head < 1.9`.

### 9. Under 5 m there is nothing to reward the approach.
`review/shots/ad-kit/tert-free.png`

- **No joinery.** Every stud/rail crossing is two boxes interpenetrating, with
  a visible seam and no shoulder, tenon or peg. Art Bible §2: "every join must
  be physically explicable." This is the first thing the eye lands on.
- **Uniform roughness on the plaster.** One soft stipple normal, no trowel
  pass, no lime bloom, no cracking, no dirt in the corners, no water streak
  under the rail, and no splash dirt at the bottom 0.15 m (Art Bible §5,
  explicit).
- **The window is a card.** Glass is flush with the frame face — no reveal
  depth despite `leaded_light`'s docstring claiming one — with a painted grid
  and no came profile, no reflection, no interior.
- **The cill texture is ~4× oversize.** A 0.075 m thick stone cill sampling the
  `stone` material at its authored 2 m coverage shows 0.15 m cobbles. Same
  class of error the `masonry_wall` comment at 481-484 already identified and
  fixed for rubble; it was not applied to the small dressings.
- **Three different woods in one wall** (pale stud, mid rail, near-black post)
  with no logic connecting them.

### 10. Timber panels repeat far past the §6 limit.
`building.py:296-307` (`FRAMES`) into `kit.timber_frame_wall`

`terrC-free.png`: twelve identical X-braced panels across one facade, six in a
row per band. `terrA-free.png`: fourteen identical vertical studs at identical
spacing, no mid-rail, no bracing — the wall reads as a picket fence, not a
frame. Art Bible §6: "No element may appear more than 3 times in a row without
a variant." The frame style is chosen once per building and then tiled.

**Fix:** vary the panel pattern *within* a wall run — a braced bay at each end
and at the door, plain panels between — and jitter panel width ±8 %.

### 11. The mandated defect reads as a bug, not as a repair.
`building.py:1206-1311` (`_defect`), `building.py:1314-1367` (`_residue`)

Six kinds dealt evenly (patch 9 · prop 11 · board 9 · shutter 10 · slump 11 ·
lean 13), which is good discipline. But at the gameplay camera:

- `shutter` (`bede-free.png`) is one green shutter on one window in a facade
  with no other shutters. It reads as a missing asset, not as a replacement.
- `slump` inserts a bare box through the ridge; nothing under it explains the
  sag, so the ridge simply has a lump.
- the `wood` residue pile (`terrC-free.png` x≈980, `terrB-free.png` x≈490) is
  a honeycomb of cylinders seen end-on and reads as a stack of drainage pipe.

A repair reads as deliberate only when the *thing it repairs* is visible: a
patch needs a crack around it, a replaced shutter needs its surviving partner,
a sagging purlin needs a prop under it.

### 12. Door steps read as slabs of pavement dropped on the mud.
`building.py:958-972`

Each tread is `M.box(DOOR_W + 0.85, ...)` — 1.8 m wide for a 0.95 m door — with
`uv_scale=0.6` on the `stone` material, so the top face shows two enormous
cobbles. `terrB-free.png` and `mere-free.png` both show them as bright flat
polygons with hard edges and no bedding into the ground.

### 13. Draw budget: the filler alone is 92 % of the whole-town budget.
`build.py` output: `townhouse 826 draws` across 74 cells (≈11 materials per
cell). `tools/render/town.mjs` reports **1182 draw calls with only 10 of 31
venues placed**, against a Directive §7 budget of 900.

Emission is already re-bucketed per cell per material, so the lever is the
material count per building: one house currently touches plaster, oak,
oak_dark, oak_weathered, rubble, ashlar, stone, sandstone, brick, terracotta,
ridge, lead, iron, painted, glass/glass_lit. Collapse the timber family to two
(`oak`, `oak_dark`) and the stone family to two (`stone`, `rubble`), and route
`ridge`/`lead`/`iron` through the atlas, and the kit halves.

### 14. Latent: `Plate` mis-rotates its edge labels when it reverses winding.
`roof.py:153-155`

```python
if _area2(self.pts) < 0:
    self.pts.reverse()
    edges = None if edges is None else list(reversed(edges))
```

Reversing `[p0,p1,p2,p3]` maps edge *i* to edge *(n-2-i)*, not *(n-1-i)*, so
the correct permutation is `[e2,e1,e0,e3]`, not `[e3,e2,e1,e0]`. Every label is
rotated one position. It does not fire today because `Footprint.rect()` is
always CCW in (x, z) — but the moment a venue hands `wall_plate` a
clockwise polygon, a `"party"` label lands on the wrong wall and the overhang
suppression and closure skip go with it. `dormer()` at `roof.py:1056` already
builds a plate whose winding is not guaranteed.

---

## What is working, and should not be touched

- The plate → roof contract. Not one roof in twelve frames is at the wrong
  height, and `chimney_through` genuinely cannot bury a stack. Keep it.
- The plinth-to-lowest-ground rule (`building.py:354`). Nothing gaps at the
  base, on any slope, in any frame.
- `_closures` asking the finished surface. When a roof exists, its gable ends
  are closed and tight, for every kind.
- The hip roof (`obA-free.png`, `pw10-free.png` right) is genuinely good —
  correct hip ridges, correct fascia, correct closure.
- The dormer (`mere-free.png`, `obD-free.png`) is the best secondary element in
  the kit: its own plate, its own roof, cheeks cut to the slope.
- The plank door with strap hinges and the brick chimney (`pw30-free.png`) are
  the two elements that would survive a AAA close-up.
- Determinism. Two builds produced identical stats; the review loop works.

---

## The three changes that buy the most quality per unit of work

**1. Fix the half-hip clip and assert that a roof covers its plate.**
Two lines at `roof.py:431` plus a six-line guard in `roof_from_plate`. It
removes eight roofless buildings, eight floating ridge lines, eight sets of
floating barge boards and eight black holes in the town plan. Nothing else on
this list costs so little or removes so much.

**2. Deal roof material and wall material per building, and give the kit a
second plan form.** `STYLES`/`ROOFS` already prove the pattern works. Add
`ROOF_MATS` and `WALL_KINDS` weighted tables keyed by style and wealth so that
slate, thatch, limewash and brick actually appear, and add an L-plan rear wing
roofed with the `clip_against` path `roof.py` already implements and nothing
uses. This is the difference between "eighty shuffles of one house" and a town.

**3. Rebuild the party wall as a real shared wall, and break facades over
12 m into bays.** Mid-line placement, thickness from the measured gap, profile
queried from *both* neighbours' finished `Roof` objects, coping proud by
0.20 m; and a bay-splitting pass in `_walls` for any run over 12 m. Together
these are what turn a scatter of detached boxes into a street — which is the
whole reason the kit was written.

Re-render `terrA`, `terrC`, `pw10`, `pw44`, `bede`, `mere` and the town aerial
after each, and look at them.
