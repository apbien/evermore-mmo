# Waterfront — build report

Answering `review/reports/ad-town-02.md` §1: *"Build `quay` first — it is a
hero, it owns the town's stated identity as a lake town at a ford, and its
absence leaves the largest single dead area in the build."*

Five venues shipped, in the order the brief gave them, each finished before the
next was started:

| venue | slots | file | tris | draws L0/L1/L2/L3 |
| --- | --- | --- | --- | --- |
| `quay` **hero** | 61 customs, 94 crane_house, + the wharf itself | `tools/assetgen/venues/quay.py` | 139,318 | 58 / 32 / 16 / 13 |
| `warehouse` | 58, 59, 60, 62, 63, 67, 80 | `tools/assetgen/venues/warehouse.py` | 127,004 | 154 / 85 / 37 / 27 |
| `fish_eatery` | 64 | `tools/assetgen/venues/fish_eatery.py` | 36,496 | 41 / 17 / 9 / 6 |
| `watermill` | 77 mill, 78 granary | `tools/assetgen/venues/watermill.py` | 47,232 | 56 / 29 / 17 / 12 |

Renders: `review/shots/quay/`, `review/shots/warehouse/`,
`review/shots/fish_eatery/`, `review/shots/watermill/`,
`review/shots/granary/`, and a 7-frame walk down Wharf Lane through the Water
Gate onto the wharf at `review/shots/town/town-walk-01..07.png`, plus
`town-aerial-ne`, `town-plan`, `town-silhouette`. Every one has been read as a
PNG, not asserted.

**Verification at town level** (`review/shots/town/town-report.json`, after a
full rebuild):

- all four venues load and are placed; the only `missing[]` entry left in the
  whole build is `tannery`
- `floating[]` names nothing from these venues
- **339 draw calls / 900** and **778,791 gameplay triangles / 3.5 M** — the
  four venues together add 348 k triangles and the budget is not close
- `node tools/check_walkable.mjs` — 15/15 streets clear, 0 obstructed,
  including Wharf Lane and Tan Road past the new sheds. The one unreachable
  door is `hm.townhouse.door.15`, which is D-044's and pre-dates this work.
- `tools/validate.py --venue <x>` was not run to completion: its `check_collision`
  has no broadphase and does not finish inside ten minutes on a town this size,
  which the build directive for this wave already flagged.

---

## 1. The join, which is what the brief said mattered

Four levels have to resolve inside eight metres of plan, and the whole venue is
solved from them rather than placed by eye:

| what | level | source |
| --- | --- | --- |
| Water Gate threshold | −1.07 | `wall` builds the arch at (50, −57) |
| wharf deck | −1.44 crown, −1.54 at both edges | authored camber, always ≥ the pad |
| `hm.pad.quay` | −1.55 | `content/town/terrain.json` |
| mere surface | −3.10 | `terrain.water_level()` |
| dredged harbour bed | −5.35 | `hm.water.harbour` bedLevel |

**There is no hard cut edge anywhere on the waterfront, and that is by
construction rather than by luck.** The pad drops off a near-vertical scarp —
−1.55 at 8.0 m from the wharf centreline, −3.69 at 8.5 m, −5.33 at 9.0 m. That
scarp is not a defect, it is the void a quay wall is built to fill. The
masonry runs from a coping 0.06 m proud of the flags down to 0.55 m **below**
the dredged bed and is battered 1:14, and its inboard face is 1.35 m back
under the deck, so the terrain scarp is inside the mass, not beside it.

The deck is cambered — `quay.deck_y(c)`, crown a metre landward of centre,
0.10 m of fall to each edge — and the camber is authored so the flags are
**never below −1.54**, i.e. never below the pad. That is the one arithmetic
constraint that decides whether the terrain pokes through the paving, and it
is stated in the function rather than discovered in a render.

The deck itself is 493 individually settled stone flags — 21,692 triangles, a
sixth of the venue — not a tiled plane. A
wharf deck is seen at a grazing angle from the gameplay camera more often than
any other surface in Hearthmere, and a tiled plane at a grazing angle is
wallpaper (Art Bible §5). Each flag carries its own settle, tilt and yaw,
which is what makes the cart ruts and the gutter puddle read.

**The boats float at the draught their load implies.** A loaded lighter sits at
0.36 m, an empty one at 0.19 m, both measured from the hull bottom, both
against `terrain.water_level()`. The hulls are built the way a flat-bottomed
lake barge is built — a cross-planked bottom swept along its own rocker, two
flared side strakes lofted off the chine, two raked transoms, frames, thwarts
and floorboards — because the player looks *down into* these from 2.5 m above
on the quay edge. A closed lofted solid would read as a boat-shaped lid.

## 2. The crane (slot 94) — the silhouette anchor

`docs/plan/schedule.md` calls it *"silhouette anchor of the whole waterfront"*.
Built as a real machine, and sized from the work it does:

- **12.0 m** from the deck to the jib head — the tallest thing on the water,
  and 4.7 m clear of the wall-walk behind it.
- double **treadwheel**, 4.1 m over the shrouds, on a timber axle at 2.55 m,
  with tread boards on the inside because men walk in it — and the tower is
  boarded on the landward face only, and on the flanks only *above* the axle,
  so the wheel is visible from the quay, from the harbour, and from the
  approach. Boarding all three sides turned it into a black shed with a stick
  on it; that is in the first iteration's render and it is why it changed.
- **jib tip overhangs the quay face by 1.2 m**, which is the number that
  matters: a lighter lying alongside is under the hook. The fall is reeved from
  the drum, over the sheave, down to a hook at 2.35 m above the water — so the
  rope reaches the boat rather than stopping at deck level.
- ratchet and pawl on the axle, back-stays from the jib head to the landward
  posts, stone counterweight box, and a slate roof from `kit.gable_roof` (real
  tile courses, ridge, fascia — not a rotated slab; the first iteration was a
  rotated slab and it read as a wide-brimmed hat).

## 3. The mill: the wheel is in the water and the leat delivers to it

This was the explicit test in the brief. Solved from levels:

```
leat water surface  -2.00   impounded, in a launder
wheel axle          -2.10   docs/plan/schedule.md slot 77
wheel diameter       3.60   rim runs -0.30 to -3.90
mere / river        -3.10   terrain.water_level()
```

Water enters the wheel a hand above the axle — that is what *breastshot* means
— and **the rim runs 0.80 m under the tail water**, printed by the build:

```
mill ridge 10.35, wheel axle -2.10 (rim -3.90 to -0.30),
tail water -3.10 — wheel dips 0.80 m
```

**The leat is a launder on trestle bents, not a cut channel, and that was a
correction.** The first version cut a stone-lined trench: the mill pad holds
the ground at −1.55 and the leat has to arrive at −2.00, so the water surface
was half a metre *inside* the terrain and the leat was invisible except where
the bank happened to fall away. A launder carried on measured bents is what a
mill on a made platform actually has, it needs nothing carved out of the height
field, and the long horizontal it draws across the bank is the best thing in
the venue's silhouette. Every bent's height is measured from `terrain.height`
at its own foot, so nothing floats and nothing is buried.

The impounded leat is the only second water surface in Hearthmere. It is not a
D-024 violation: the terrain evaluator still has exactly one water level, and
nothing in `content/town/terrain.json` moved. A mill leat is by definition a
made channel with a dam across it, and the alternative — a mill whose wheel
turns in the same water it discharges into — is the tell the brief named.

The granary (slot 78) stands on twelve **staddle stones**: a tapered pier and a
wide flat cap, 0.62 m of clear air under the sill. The cap overhang *is* the
machine — it is why the stone is that shape — and `core.building`'s plinth
would have buried it, so the plan's `floor_y`/`plate_y`/`ridge_y` are lifted
and its plinth reduced to a 0.22 m sill band before the walls are built. The
door has no steps and never will: it has a ladder, leaning, which is the point
of a granary.

## 4. Changes made to shared code

Four, all of them extensions rather than forks, and all of them fixing
something that was planned and never built.

**`core.building._loading_door`** (new). `plan["loading"]` has been computed
from the style table since the table was written and *nothing consumed it*, so
every warehouse in Hearthmere had grain on the first floor and no way of
getting it there. Now any warehouse-kit mass anywhere in the town gets a
taking-in door under the plate, a gibbet beam with a knee brace, a block, a
fall, a cleat, and half the time a pair of sacks on the hook. `_walls` also
stores `plan["front_run"]` now, which is the frame anything hung on the
frontage after the walls exist needs.

**`core.building.BAY_ALT["timber"]`: `brick` → `limewash`.** The town plan gives
brick nogging to exactly one building — slot 50, *"the only nogging in
Hearthmere, and a different colour from everything near it"* — and dealing a
brick bay onto every timber elevation over 12 m contradicted that on the
granary, two warehouses and the bede houses at once. Caught in
`review/shots/granary/granary-approach.png`, where half the granary was clad in
brick.

**`venues/townhouse.KITS`: `warehouse` removed.** Seven slots carry that kit and
they were being built as anonymous filler, which is precisely why not one of
them had a loading door, a hoist beam or a dock. `venues/warehouse.py` owns
them now.

**`venues/terrain._water` swell amplitudes raised.** See §6.

## 5. D-046 — four venues moved to world space

`content/town/hearthmere.json`'s `venues[]` gave `quay` the customs-house slot's
centre and a 315° rotation as its root transform. That is workable for a single
mass built about its own centre and unworkable for anything that spans several
slots or calls `core.building` / `core.roof`, because those read the height
field at **world** x,z and hand back world polygons — put that output under a
rotated root and the building lands somewhere else entirely. `quay` is authored
from the wharf polygon and the harbour basin, 15 m from the customs slot;
`warehouse` owns seven slots from the wharf to the Bailey.

So `quay`, `warehouse`, `fish_eatery` and `watermill` now take a null root
transform, exactly as `townhouse`, `streets`, `wall` and `market_square`
already do. The change is in **`tools/plan/townplan.py`**
(`WORLD_SPACE_VENUES`), not hand-edited into the JSON, so a re-plan reproduces
it. `docs/DECISIONS.md` D-046 records it.

The quay's own geometry is still authored in a wharf-local frame — `+X` along
the quay to the north-east, `+Z` landward toward the Water Gate — and placed
once, because every dimension on a wharf is measured along or across the quay
and nothing is measured in world axes. Colliders and entities go through
`quay._w()`.

## 6. The water, which the brief said was in my frame more than anyone's

`ad-town-02` §8: the Mere blows out to white and its shoreline is a hard
scallop. What I changed at source, and what I did not:

**Changed.** `venues/terrain._water`'s per-vertex swell. The blown patch sits
30–90 m out, which is exactly the band the two long octaves cannot break — a
55 m swell tilts a 60 m glitter path as *one piece*. The short octave was
contributing under a degree. It is now 0.038 and there is a fourth at about a
9 m wavelength, still four vertices per wave on the 2 m LOD ring so it does not
alias. Peak tilt goes from 6° to 10°: nothing to the eye on the water itself,
and it turns the glitter sheet into a stipple, which is what real water does
with it.

**Not changed, and here is the honest reason.** The remaining blowout is a
tone-mapping problem, not a material problem, and `core/materials.water()`
already carries a measured note saying so — raising the roughness floor spread
the blown region from 40 % of the Mere to 85 % of it at a lower peak, because
GGX conserves energy. The fix `ad-town-02` §5 names, `scene.fog` in
`tools/render/town.html` and `client/src/main.js`, would close both this and
the far-shore scallop in one afternoon and is the single cheapest quality win
on the list. I have deliberately not touched those two files: they are the
shared render harness, another agent in this wave may be in them, and a merge
conflict there costs more than the frame it buys. **It is still the first thing
the next wave should do.**

The scallop itself is the terrain's waterline-mud band diced per triangle at
2 m and 4 m LOD, not the water sheet — `terrain.surface_weights`'s `mud` term,
which `dropOff` already suppresses past 130 m. It needs the same treatment
inside 130 m, i.e. per-vertex weights rather than per-triangle material choice.
That is a `venues/terrain.py` mesh change, not a material change, and it is a
day's work rather than an hour's.

## 7. Defects found and not fixed

Reported precisely rather than silently worked around.

**`core/roof.py` leaves detached timbers at the verge.** Visible at both eaves
corners of the granary in `review/shots/granary/granary-approach.png` as two
dark boxes floating clear of the roof, and on the fish eatery's first
iteration. It is worse on `half_hip` than on `gable`, which is why the granary,
the tithe barn and the fish eatery are all gabled — that is a workaround, not a
fix, and `cottage_thatch` (half-hipped by style, roughly a fifth of the town)
still shows it. `_fascia` at `roof.py:~1050` already carries two guards against
exactly this class of bug; a third case is getting through.

**`rubble` is still crazy paving** (`ad-town-02` §9). The quay wall, the water
stair spur and the boat hard use **`stone`** (`foundation_stone` — coursed
rubble squared to beds) rather than `rubble`, which is both correct for a quay
and sidesteps the defect. It does not fix it for the church or the town wall.

**Nothing else on the waterfront is known-broken.** Collision is authored per
structure — a surface hull over the deck, solid segment boxes along the three
quay faces, cylinders on the crane posts and the launder bents, boxes on the
boats, the smoke shed and the loading docks — and `node tools/check_walkable.mjs`
is clean.

## 8. Does it read as a working waterfront?

The test the brief set. My answer, from the renders and not from the source:

**Yes at the quay, and the crane earns its keep.** `quay-gameplay` is a frame
with a job in it: the crane's wheel open to the water, the fall hanging over a
loaded lighter, the deck flags worn into ruts between the gate and the crane,
fish on the racks, and the customs house squared onto the gate so nothing lands
unwatched. The three things that make it work are all cheap: the flags being
real objects, the boats sitting at a plausible draught, and the quay wall going
down past the bed instead of stopping at the waterline.

**Qualified yes behind it.** The seven sheds now have taking-in doors, hoist
beams, docks and goods under tarpaulins, which is what the AD asked for and
what makes the quarter read as commercial. But five of the seven are still
generic masses with good dressing rather than individually composed buildings,
and the two that *are* composed — the tithe barn with its opposed cart doors
and the rope walk with rope actually laid down it — are visibly better. If
there is another pass, spend it there.

**The honest weakness is the environment, not the venues.** With no fog and no
AO the wharf sits in the same value band as the far shore, and the water still
blows out from the south-west. Every frame here would be materially better with
two lines in the render harness that I have deliberately left for whoever owns
it.

### The walk, frame by frame

`town-walk-01..07`, Wharf Lane eastward from the Fork to the wharf deck.

- **01–02** the lane, properly setted, kerbed, gutters. Reads.
- **03** the fish eatery: awning, trestles, gutting boards, tarpaulined goods
  and the netloft opposite. This is the best frame on the route and it is
  entirely made of residue. It is also the frame that shows `rubble` at its
  worst — both walls either side of the lane are crazy paving and it is the
  single loudest material problem left in the quarter.
- **04–05** through the Water Gate. The arch, the wall, the ramp. There is a
  **dark unlit cuboid at the inner jamb** at roughly (43, −59) — it belongs to
  `wall` or `gatehouse`, not to this venue, and it is another instance of
  `ad-town-02` §16.
- **06** the wharf: crane, treadwheel, bollards, crate stacks, a handcart
  standing where it was left, the mere and the far treeline beyond. The
  vegetation rebuild has landed and the far shore is a real wood now.
- **07** deck level under the crane's jib, the fall hanging into frame, water
  gate behind. The flags carry the frame at a grazing angle, which is what they
  were modelled individually for.

`quay-silhouette` is the one to judge the crane on: the jib, the fall, the
pitched roof and the wheel showing through the open bay are all readable in
pure black, which is the test `docs/plan/schedule.md` set when it called the
crane the waterfront's silhouette anchor.

## 9. What I would do next, ranked

1. **`scene.fog`** in `tools/render/town.html` and `client/src/main.js`, driven
   from `hearthmere.json`'s lighting block. Still the cheapest large win in the
   build and it closes half of §6 above on its own.
2. **Course `rubble`** (`ad-town-02` §9). It is the dominant surface in
   `town-walk-03` and on the town wall either side of the Water Gate.
3. **`core/roof.py`'s detached verge timbers** (§7). It is on a fifth of the
   roofs in town and it reads as broken rather than as unfinished.
4. **Compose the five generic warehouses** the way the tithe barn and the rope
   walk are composed. The dressing is there; the massing is not yet.
5. **A boathouse or a ferry stair off the Ferry Postern** — the one piece of the
   waterfront the schedule implies and nobody has built.
