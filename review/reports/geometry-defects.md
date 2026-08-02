# Geometry defect sweep — the ten diagnosed items

Agent: geometry-defects. Working file, written as the work happened.
Every claim below is backed by a measurement or a frame I opened and read.
Where I could not prove it, I say so.

---

## Summary

| # | Item | Status |
| --- | --- | --- |
| 1 | bakery flour decal 0.46 m below terrain | fixed |
| 2 | dovecote residue 0.32 m below terrain | fixed |
| 3 | `hm.watermill.wheel.01` 0.55 m below terrain | fixed |
| 4 | `landscape.gltf` is 34.2 m tall — "the floating mass" | **no floating mass exists**; check corrected + D-054 |
| 5 | `church.gltf` 22.3 m over a 22.0 m ceiling | fixed — the check was measuring buried plinth |
| 6 | `LIBRARY['tree_far']` 512 px/m in a 256 px/m class | fixed |
| 7 | confectioner barge board overshoots the apex by 5 m | fixed; whole-repo audit of the idiom done |
| 8 | roof block-deal re-rolls per asset; 26 m blocks | fixed |
| 9 | the lake town's quay has no boats | **premise false** — it has three; warps fixed, gangway added |
| 10 | Ford Road not completable — 202.6 m for a 127 m route | **nothing was blocking it**; harness bug, fixed |

---

## 4 and 10 first, because both were hunts for something that was not there

### 10. Ford Road is not blocked. The route ends four metres short of its own finish line.

`tools/check_client.mjs` reported *"player stopped at z=40.0 after 203 m of
walking (route is 127 m) — something on Ford Road is blocking it"*. Two waves
have been told the main street is obstructed.

I instrumented the walk and logged the player every ten physics steps. From
step ~4,300 to step ~12,440 the trace is one line repeated:

```
s=12440 leg= 9 p=(5.2,1.8,40.0) d=0.016 goal=(5.2,40) walked=319.9
```

The player is standing **on the last waypoint**, at `leg = 9` of a 10-waypoint
route, oscillating over a 3 cm step and burning the distance budget. Three
numbers had drifted apart:

- `fordRoute()` filtered Ford Road's authored path to `z <= 46`, and the path
  has no vertex between **z = 40** and z = 52 — so the last waypoint is z = 40.
- the walk loop's arrival break was `p[2] > 44`.
- the pass line was `b[2] > 40`, and `40.0 > 40` is false.

So the player walked the whole street, arrived, and could neither break out nor
pass. The 202.6 m "for a 127 m route" is 127 m of real walking plus ~75 m of
oscillating on the spot. **Nothing on Ford Road obstructs anything.**

Fixed two ways so it cannot drift again: arrival is now derived from the last
waypoint (`within 2.0 m of route[route.length-1]`) instead of a typed z, and
the route now runs south to the gate threshold (`z <= 74`) so the check covers
the street its own docstring claims it covers.

**Proof — `node tools/check_client.mjs`, after:**

```
walked: (43.0, -0.5) → (1.6, 71.0), 151.5 m of path over 296 samples
        (budget 256 m over a 160 m route)
OK — client boots clean and the player walks.
```

151.5 m of path for a 160 m route — *under* the route length, because the
controller cuts corners. Altar → nave → west door → perron → Kirk Green → Ford
Road → market place → south gate, with no deflection at all, over a route now
33 m longer than the one that was failing.

**One thing this exposes.** The `perf:` reading is taken wherever the walk
stops. It used to stop at z = 40 in the dense middle of town and reported 2,159
draws / 3.73 M triangles, both over §7 budget; it now stops at z = 71 by the
south gate and reads 426 draws / 0.90 M. The §7 failure did not go away, it
moved out of shot — the probe should be the WORST frame along the walk, not the
last one. It is now caught at the arrival camera instead (1,380 draws against
900), which is the right place for it and is reported as a live failure below.
Related, and also not mine: that arrival reading is **not deterministic** —
2,072 draws on one run and 1,380 on the next, on identical bits, tracking only
how long the LOD set took to settle. Both belong with ad-town-03 §10, "harness
truth".

### 4. `landscape.gltf` is 34.2 m tall because it is the ground, not a building. There is no floating mass.

Pass 02 §7 and pass 03 §3 both name an "unidentified mass 28.29 m up inside the
landscape venue" and pass 03 asks for it to be found and deleted. It does not
exist.

I de-quantized every LOD0 primitive in `landscape.gltf` through its node TRS and
sorted by world Y:

```
top    28.29  bot    14.49  at ( -100.25,  252.14)  mat=tree_far   node=landscape#n3_5
top    28.01  bot    13.07  at (   18.10,  252.81)  mat=tree_far   node=landscape#0_5
top    27.28  bot    13.09  at (  -73.61,  253.78)  mat=tree_far   node=landscape#n2_5
```

`terrain.height(-100.25, 252.14) = 15.21`. These are the distance-wood
impostors standing on the **north ridge, 250 m outside the wall**, on ground
that legitimately rises to +21 m. The venue's low point, −5.90, is the mere bed.
28.29 − (−5.90) = 34.19 — the reported "height" is the relief of a
553 × 540 m piece of countryside.

Then the question that actually matters: is anything floating over the *town*?
I measured every LOD0 primitive inside the ±100 m town box against
`terrain.height` at its own highest vertex:

```
tallest-above-terrain inside the town box (+/-100 m):
    12.82 m above terrain, y= 13.46 at (  15.2,  15.8) mat=leaf_oak
    11.77 m above terrain, y= 13.67 at (  10.4,  86.8) mat=leaf_ash
    11.37 m above terrain, y= 10.49 at ( -82.7, -71.7) mat=leaf_oak
    10.87 m above terrain, y= 10.93 at (  11.8,   8.0) mat=timber_grey
```

The tallest thing `landscape` puts anywhere inside the wall is a 12.8 m oak.
Nothing floats.

`tools/validate.py` already carries a `LANDSCAPE` exemption whose comment reads
*"The ground is not a building… the distance ring rises ~28 m above the mere
bed"* — written for exactly this, and `landscape` was never added to the set
when the terrain venue was split in two. Added, with the measurement recorded
at D-054 so the next reviewer does not spend a third pass on it.

The composition finding underneath it stands and is somebody's job: the
**tallest thing on Hearthmere's north skyline is a tree in the far wood**.
That is a skyline problem (ad-town-03 §3), not a floating mass.

### 5. The church is 21.95 m tall. The other 0.35 m is underground.

`church.gltf` measured 22.30 m against a 22.0 m ceiling. Its bounds are
y ∈ [−0.35, +21.95]: 21.95 to the bronze finial over the lead spire, and 0.35 m
of `rubble` foundation carried below the datum — which Directive §6.1 *requires*
so nothing floats on falling ground.

`check_gltf` was measuring the bounding box's vertical span and calling it
height, so it counted buried foundation as building. That is a category error,
not a scale error, and shrinking the church to satisfy it would run directly
against ad-town-03 §3, which asks for the tower to be *more* visible. Height is
now measured from the venue datum up. Church: 21.95 m, under the ceiling, no
exemption needed and nothing about the building changed.

---

## 1, 2, 3 — three things authored at y = 0 on ground that is not at y = 0

All three are one defect: a generator assumed a flat datum where
`BUILD_DIRECTIVE` §6.1 says *"a generator that places an object must derive its
Y from the terrain height function, never assume y=0."*

**1. bakery — the flour on Bakers' Row.** `venues/bakery.py:539`. Four rings of
flour dust; ring 0 on the shop floor at `PLINTH`, rings 1-3 out on the street at
`y = 0.0`, with the comment *"the rest are out on Bakers' Row, which is 0.46 m
lower."* Bakers' Row is not 0.46 m lower, so a 4.4 m ring of flour sat **0.46 m
under the road** and rendered nothing at all.

**2. dovecote — the droppings and the feathers.** `venues/dovecote.py:283`.
`P.spill(...)` at a flat `y = 0.03` on ground that falls, so one 2.7 m patch ran
from **+0.44 m in clear air** on the uphill side to **−0.36 m buried** on the
downhill side. The buried lobe was validate's one-voxel isolated mass. The 30
scattered feathers were authored the same way.

**3. watermill — `hm.watermill.wheel.01`.** The wheel's axle is at −2.10 m
because a 3.6 m wheel has to dip 0.80 m into tail water at −3.10 m; the mill's
made platform is at −1.55 m. So the entity, anchored on the axle, was 0.55 m
underground. The wheel itself is fine — its rim reaches −0.30 m, 1.25 m proud of
the platform — the *anchor* was in the wrong place. It is now
`min(rim − 0.30, ground + 1.00)` = −0.60 m, the part of the wheel a player
standing on the bank actually looks at, with the axle recorded as the animation
`pivot` so the spin is unaffected.

### The fix, in core

`core.siting.Site.drape(geom, offset=0.0)` — new. `Site.ground(x, z)` answers for
ONE point, which is all a venue had, and a residue patch is not one point.
`drape` takes DESIGN-frame geometry (what a venue module is holding, before
`place()`), keeps its local Y and reads it as a height above ground — exactly
`terrain.drape`'s contract, which every generator already knows, in the frame a
venue actually works in.

**Proof — geometry against `terrain.height` at its own x/z, after:**

```
BAKERY   flour   : min +0.001 m   (max +1.553 is the shop floor and the bench)
DOVECOTE flour   : min +0.029 m
DOVECOTE feathers: min +0.034 m
```

Nothing below terrain. Before, the bakery's minimum was **−0.468 m** and the
dovecote's **−0.355 m**. `hm.watermill.wheel.01` is at y = −0.60 m against
terrain at −1.55 m.

---

## 6. `tree_far` — the coverage was a fiction, so the audit failed on it

`LIBRARY["tree_far"]` declared `coverage = 1.0` in class `standard`. The size
floor is 512 px, so the audit read 512 px/m against a 256 px/m class. Bending
the coverage to 2.0 would have passed the check by writing down a different
fiction.

One cell of `tree_impostor`'s 2x2 sheet is **one whole nine-metre tree**, drawn
only past 140 m where a tree is fifteen pixels wide. The tile covers about 16 m
of world, and at that range 32 px/m is already more resolution than the frame
can show. So the entry is `coverage = 16.0` in a new `impostor` density class at
32 px/m, both documented at `DENSITY`. `uv_scale()` is never called for this key
— `vegetation.distance_tree` addresses its quadrant explicitly — and the map on
disk is unchanged at 512 px, so nothing needed rebuilding.

```
('tree_far', 512, 16.0, 32.0, 'impostor', 32.0, 'ok')
```

---

## 7. The confectioner's barge board, and the audit of the idiom behind it

`venues/confectioner.py:166`. The board is built anchored at its own origin
running out in +x, then `rotate_z(sx * -atan(PITCH))` per side. That mirrors the
*angle* and not the *direction*, so the left-hand board rotated up-and-right,
left the roof at the apex and ended in open sky.

**Measured** (apex 9.56 m, eaves 6.40 m, rafter 4.73 m, pitch 1.02):

```
OLD left barge board tip  y = 12.73 m  ->  +3.17 m above the apex, in clear air
NEW left barge board tip  y =  5.99 m  ->  lands on the eaves line, correct
```

(The art director read it as ~5 m; 3.17 m is the vertical component, ~4.7 m is
the distance along the board from where it should have ended.)

**Fix, in core: `core.mesh.Mesh.mirror_x(about=0.0)` and `Group.mirror_x`.**
Mirroring a part is not `rotate_z(−angle)`, and it is not `scale(-1, 1, 1)`
either — negating one axis reverses triangle WINDING, so the mirrored copy turns
inside out and vanishes under backface culling. `mirror_x` negates x on
positions and normals **and flips the winding back**, which is exactly why it
belongs in core rather than in a venue. The confectioner now builds the
right-hand board every time and hands it.

**Frames:** `review/shots/geom/confectioner/confectioner-approach.png` and
`confectioner-silhouette.png`. Both boards descend from the apex to their own
eaves; the silhouette is a clean symmetric gable with no spike.

### The audit the brief asked for

Two passes over the whole repo: every `rotate_x`/`rotate_z` whose argument is
sign-mirrored (`sx *`, `side *`, `sgn *` — 29 sites), and every `rotate_*`
applied within eight lines of an ORIGIN-ANCHORED constructor
(`prism`, `chamfered_prism`, `lathe` — 118 sites).

**The intersection is one line, and it is `confectioner.py:171`.** Every other
mirrored rotation in the repo is applied to `M.box`, `M.plank` or `M.beam`,
which are centred on the origin, so a world rotation is a rotation in place and
is correct. The 118 anchored-constructor sites are all single-orientation —
`rotate_x(pi/2)` to stand a lathe up and so on — where turning about the origin
is the intent. `kit.py:448` is the same barge-board job done right: a centred
`M.plank` with a full-quadrant `arctan2(h, -side * w * 0.5)`.

In the file and NOT fixed, because it is a colour decision: `PAINT =
"painted_crimson"` at `:62` paints the whole building, and ad-town-03 §6 asks
for it confined to trim with the frame back in oak.

---

## 8. The roof block-deal

Full rationale and measurements at **D-056**. In short: the 26 m lattice was not
just too small, it **cut across the terraces**, so a block routinely held two
buildings on two different shelves with a retaining wall between them.
Enlarging the square (§5 suggests 42-48 m) improves the statistics and keeps the
category error. A block is now `(district, terrace)` — both already authored in
content — via a new `core.terrain.terrace_of(x, z)`.

| scheme | blocks | mean masses/block | masses in a run of 3+ |
| --- | --- | --- | --- |
| 26 m square (before) | 46 | 2.04 | 48 / 94 |
| 42 m square (§5's suggestion) | 33 | 2.85 | 73 / 94 |
| 48 m square (§5's suggestion) | 31 | 3.03 | 78 / 94 |
| **district x terrace (now)** | **26** | **3.62** | **85 / 94** |

The three fallbacks §5 names now draw from the block RNG: the fire-ban
substitute, the empty-pool fallback and the style-veto substitute. The style
veto was the largest single source of the checkerboard — it fires on every
building whose `ROOF_MATS` does not contain the block's covering, and each one
was rolling its own replacement. The one-in-seven odd-one-out keeps its
per-asset roll on purpose: breaking the run is its whole job, and it is what
stops a ten-plot block reading as one decal.

**Frames:** `review/shots/geom/roofs/town-plan.png`,
`review/shots/geom/roofs/town-aerial-sw.png`. Kirk Knowe (I5-K8) is a solid run
of slate; the West Lanes (B4-D6) are a run of thatch; the Fire Lane and
Southgate are terracotta. Against ad-town-03 §5's *"orange, cream, orange,
cream, cream, orange, brown, orange — there is no run anywhere in the town"*,
there are now three legible quarters.

Still open, flagged for the material pass: terracotta is the plurality in six of
eight districts (§5c) and `terracotta` is one flat material where three seeded
tints would change every aerial (§5d). Both are colour calls.

### One thing I found while doing it, and deliberately did not ship

`roof_covering` draws a VARIABLE number of times from the building's shared
`rng`, so every decision taken after it is coupled to how the roof came out.
Giving it its own stream is one line and is plainly right. It also re-rolls the
whole kit, and the re-roll immediately crashes the build:

```
RuntimeError: roof_from_plate('gable', 'hm.slot.19.workshop_a.wing'):
              every slope was clipped away.
```

That is a latent defect in `plan_building`'s L/T wing — a wing can be planned
small enough that its roof clips to nothing — and it wants fixing before the
stream is separated. I reverted to the coupled stream rather than ship a build
that does not build, and left the finding and the repro in a comment at
`roof_covering`.

---

## 9. The quay's boats exist. Nobody could see them, and the warps went nowhere.

**The waterfront agent's report is true and ad-town-03 §7 is wrong on the
facts.** `assets/meshes/quay.gltf` was built after `quay.py` and contains both
moored lighters and the hauled-out punt. Isolating the geometry within 3 m of
`hm.quay.boat.01`:

```
oak_weathered  n=2356  y[-3.46,-2.38]   the hull, topsides
oak_dark       n= 736  y[-3.43,-2.43]   gunwale rubbing strake and frames
canvas         n=5880  y[-3.22,-1.58]   the tarpaulin, turned back
sacking        n=1184  y[-3.26,-2.65]   the sacks
iron           n=3936  y[-3.29,-2.43]
timber_grey    n=  49  y[-2.51,-2.44]   the quant pole
```

Hull bottom **−3.46 m** against a water level of **−3.10 m**: **0.36 m of
draught**, exactly what `_lighter` authors for a loaded boat. §7's *"there is
not one vessel on the water anywhere in the town"* is not the case, and the
draught is right.

**Why the review could not see them.** The gunwale is at −2.38 m and the quay
deck crown is at −1.44 m, so a moored lighter lies **0.94 m below the coping.**
That is correct — you step down into a boat — and it means that from a 1.62 m
eye standing on the deck, which is the only quay camera in the review set
(`wharf-walk-09`), the hulls are entirely behind the coping. From the water at
120 m (`approach-ne-free`) they are about ten pixels behind the over-driven
haze. The boats were invisible from every frame anyone had shot.

### What I changed

**(a) The mooring lines now reach their rings.** `_lighter` ran its warps to
`(a ± 4.3, WATER_Y + 1.0, c + 1.85)` — a point derived from the boat and from
nothing on the wall. Measured against the rings `_quay_face` actually builds:

```
boat.01 bow    OLD warp end -> nearest ring 0.40 m away
boat.01 stern  OLD warp end -> nearest ring 2.12 m away
boat.02 bow    OLD warp end -> nearest ring 0.93 m away
boat.02 stern  OLD warp end -> nearest ring 2.50 m away
```

`_quay_face` now returns the eye of every ring it builds; `_lighter` makes each
warp fast to the nearest unused one, with sag scaled to the span. After, in the
shipped mesh: **280 cord vertices within 0.25 m of ring ironwork, closest
approach 0.016 m.** (Three dead variables in that block are gone too — `ea`,
`ec`, and `bc` assigned three times.)

**(b) A plank gangway, cleated, from the coping down to the loaded lighter's
gunwale.** It is the one item on ad-town-03 §7's own list the venue did not
have, and it is the item that makes the boats read: it crosses the coping, so it
is the thing in the frame that says there is a boat down there — from the deck,
from the water gate, and from the aerials.

**Frame: `review/shots/geom/quay8/town-free.png`** (eye 7.5 m at 77, −75 looking
65.5, −67.5). Two flat-bottomed lighters lying alongside bow-to-stern, floating
with the mere against their planking, the loaded one with its tarpaulin turned
back, mooring rings in the face, and the gangway running down into the starboard
boat. `review/shots/geom/quay7/town-free.png` also shows the hauled-out punt and
its windlass on the boat hard.

### Two things I saw at the quay and did not fix

- The hulls are **too deep for a lake lighter** — about 2.6 m from bottom to
  gunwale on a 9 m boat drawing 0.36 m. It reads as a sailing barge. That is
  `_hull`'s profile, and it is proportion, not a defect.
- All three cameras I authored to see the boats failed first, because `--eye` is
  measured from `terrain.height` and the quay deck is authored geometry, so the
  camera sits UNDER the wharf. This is ad-town-03 §12's bridge-deck finding in a
  second venue: **no quay-edge frame has ever been reviewed either.**

---

## Verification

`python tools/validate.py` — **all six assigned failures gone.**

```
before: 7 failures, 39 warnings
after:  0 failures, 41 warnings
```

The seventh failure, `§7 mesh memory: 275.7 MB exceeds the 240 MB budget`, was
never mine and cleared itself: re-dealing the roofs put a slate quarter where a
thatch one had been, and thatch is mass construction. **275.7 MB -> 239.4 MB.**
It is a warning now, at 85 % of budget, and it is one wave of growth from being
a failure again.

Gone: `church.gltf height 22.3m`, `landscape.gltf height 34.2m`,
`bakery: isolated mass entirely below terrain`,
`dovecote: isolated mass entirely below terrain`,
`hm.watermill.wheel.01 sits 0.55 m below terrain`,
`LIBRARY['tree_far'] is 512 px/m`. Also gone from the warnings:
`landscape: geometry reaches 4.53 m below terrain`.

`node tools/check_client.mjs` — the walk passes:

```
walked: (43.0, -0.5) -> (1.6, 71.0), 151.5 m of path over 296 samples
        (budget 256 m over a 160 m route)
```

`node tools/check_walkable.mjs` — `OK — Ford Road is traversable end to end`,
all 15 streets PASS, 0 severed, 0 obstructed.

### Two things the checks now say that I want on the record

**1. `check_client` fails the §7 draw budget at the arrival camera** — 1,380
draws (scene 560 + shadow 526 + ao 227 + post 67) against 900. That is real,
it is not mine, and it was previously hidden: the perf probe used to be taken
wherever the walk stopped, which was z=40 in the dense middle of town, and with
the route now completing it stops at z=71 by the south gate and reads 426 draws.
The gate has moved to the arrival camera, which is the right place for it.
Related: the arrival parity reading is **not deterministic** — 2,072 draws on one
run and 1,380 on the next, on identical bits, tracking only how long the LOD set
took to settle. Both belong with ad-town-03 §10, "harness truth".

**2. `check_walkable` reports one unreachable door: `hm.townhouse.door.15`**, the
song school's, at (49.3, −14.5) in the churchyard. The blocker is
`church.parapet` — an 18.2 m box standing **1.27 m** in front of the door,
leaving a 1.05 m slot. It is a church-vs-song-school siting collision, and
`church.gltf`/`church.json` were not rebuilt in this session. I checked whether
my roof change caused it by restoring the original 26 m lattice key and
rebuilding: **the door is unreachable either way.** Not caused here, not mine to
fix, and named so it is not lost.

---

## What I did not touch, and who owns it

- **The fountain's water at range.** The brief said to take it if it turned out
  to be geometry or shader rather than scale. It is scale: ad-town-03 §(a)
  measures `K.water_disc(2.10, y=0.62, depth=0.24)` sitting 0.28 m below a
  0.90 m lip on a 2.1 m bowl, so a 1.62 m eye clears the water only inside about
  8 m. That is one number — lip height against water height — and it belongs to
  whoever is rebuilding the fountain's mass, because splitting it across two
  agents is how a fountain ends up with a lip that fits neither design.
- `confectioner.py:62 PAINT` — colour.
- Terracotta plurality and terracotta tints (ad-town-03 §5c, §5d) — colour.
- The latent `roof_from_plate` wing crash, above — `core/building.py`'s owner.
