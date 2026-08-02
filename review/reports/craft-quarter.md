# Craft quarter — build report

Answering `review/reports/ad-town-02.md` §1: eight of the eighteen missing
venues — the ones that make the town look like it MAKES things rather than just
houses people.

| venue | slot | file | tris | draws | colliders |
| --- | --- | --- | --- | --- | --- |
| `cooper` | 33 Bakers' Row | `tools/assetgen/venues/cooper.py` | 49,998 | 50 | 29 |
| `carpenter` | 34 Bakers' Row | `tools/assetgen/venues/carpenter.py` | 45,840 | 41 | 26 |
| `chandler` | 35 Bakers' Row | `tools/assetgen/venues/chandler.py` | 45,486 | 51 | 31 |
| `bowyer` | 36 Sty Lane | `tools/assetgen/venues/bowyer.py` | 33,710 | 43 | 12 |
| `stables` | 70 Ford Road | `tools/assetgen/venues/stables.py` | 45,453 | 39 | 31 |
| `waggon_shed` | 38 Ford Road | `tools/assetgen/venues/waggon_shed.py` | 42,286 | 32 | 23 |
| `dovecote` | 57 The Bailey | `tools/assetgen/venues/dovecote.py` | 40,728 | 29 | 26 |
| `tannery` | 93 Tan Road (outside) | `tools/assetgen/venues/tannery.py` | 35,004 | 44 | 20 |

Renders: `review/shots/<venue>/`, plus `review/shots/craft/town-aerial-sw.png`,
`review/shots/craft/town-walk-01..08` (Bakers' Row) and
`review/shots/craft-lanes/town-walk-01..06` (Bakers' Row → Sty Lane).
`node tools/check_walkable.mjs`: **15/15 streets pass, 0 obstructed**, Ford Road
traversable end to end, and the one unreachable door in the town
(`hm.townhouse.door.15`) is not in this quarter.

---

## 0. Three pieces of shared work that had to happen first

### 0.1 `core.venue.Plot` — the venue frame, fixed once

There are two rotation conventions in this repo and they are not the same one.

- `core.building.Footprint` — and therefore every `polygon` in
  `content/town/hearthmere.json` and every number in `docs/plan/schedule.md` —
  maps plot-local to world as `world = rot_y(-theta) * local + centre`.
- The renderers and the client place a venue mesh with a three.js
  `rotation.y = +theta`, i.e. `world = rot_y(+theta) * local + origin`.

They agree only where `sin theta == 0`. Everywhere else a venue authored with
its front at local -Z comes out **mirrored about its own frontage normal**, and
at this quarter's angles that is not a small error:

| slot | theta | plan says the front faces | naive local -Z would face |
| --- | --- | --- | --- |
| 70 stables | 80° | east, into the Ford Road yard | **west — 160° wrong** |
| 38 waggon shed | 257° | west, onto Ford Road | **east — 154° wrong** |
| 93 tannery | 225° | south-west, onto Tan Road | **south-east — 90° wrong** |
| 57 dovecote | 81° | east | **west** |
| 36 bowyer | 349° | north, onto Sty Lane | north, 22° of yaw error |

`venues/church.py` hit this first and solved it by hand — its docstring works
out that local +Z is west — which is the right answer for one venue and not a
thing eight more should each rediscover, especially since getting it wrong
produces a building that is *plausible in isolation* and wrong in the town.

`core/venue.py` now carries **`Plot`**, which takes a `buildingSlots[]` row and
applies the one corrective yaw that makes the two conventions compose to the
identity:

    rot_y(theta) · rot_y(-2·theta) · d  ==  rot_y(-theta) · d

A venue author works in the frame the schedule is written in — `+X` along the
frontage, `-Z` out of the front door, `y = 0` at `groundY` — and geometry,
colliders and entities all go through the same rotation, so they cannot drift
apart. Verified numerically against `Footprint`: `Plot(slot 33).world(0, -5)`
returns `(39.46, 29.21)`, which is that polygon's own front-edge midpoint.

`Plot` also carries `w/d/hw/hd/front/back/eaves/ground/cells`, `cell_at()`, and
plot-frame `collider`, `collider_walls`, `collider_steps`, `collider_from`,
`instance` and `entity`.

### 0.2 `core.kit.open_range` — the form the whole quarter is built from

Half these trades work under a roof that is not walled on the street side, and
that is not styling: fire, smoke, shavings, wet hides and a two-metre stave all
want air, and a trade that has to be seen to be sold wants a customer able to
look in. `venues/blacksmith.py` established the form; every other workshop
should be built from the same posts, plates and braces rather than from its own,
or the quarter loses cohesion exactly the way town-02 §10 describes.

`open_range(asset_id, width, depth, eaves, ...)` gives posts on a bay module,
knee braces at every head, wall plates and tie beams, boarding on the sides you
name, a tiled roof, closed gable ends — and, given a `Plot`, its own collision:
solid walls, solid posts, **nothing across an open side**.

One parameter earned its place during review: **`board_gap`**. The first cooper
render came back with a solid boarded rear wall behind an open front, and the
whole covered floor went black — the work stopped reading, which is the exact
failure the open form exists to avoid. A working shed is boarded with a
deliberate gap (cheaper, the timber can move, the light gets in), so the gap is
authored and the light slits between the boards do the job.

### 0.3 `core.props.shavings` promoted from private

Every wood trade needs curled chips on the floor, and what the venues were
reaching for instead was `spill(kind="sand")` — which builds a smooth conical
**heap**. A heap is right for grain and wrong for shavings: at eye height under
a cooper's or a joiner's roof, three of them read as sand dunes, which is what
`carpenter-detail.png` and the first `town-walk-05` came back with.
`props._shavings` already did the right thing (flat, scattered, curled) and was
private. It is now `props.shavings`, with `_shavings` kept as an alias for the
three existing internal callers.

---

## 1. cooper — slot 33, Bakers' Row

A cask is the only container this world has for anything wet, so the cooper is
not picturesque, he is infrastructure: the brewery, the tannery, the quay and
the inn all buy from this yard. Building it well explains half the other props
in Hearthmere.

**Arrangement is by workflow and reads without a word of text.** From Bakers'
Row: riven staves in seasoning cones and the cleft billets they came off (RAW) →
the shaving horse and the two-metre jointer (HOLLOW) → the raising-up,
seventeen staves stood in a truss hoop and splayed at the foot (RAISE) → the
setting fire in the open with the cask over it and the windlass rope still taut
on it (FIRE) → the croze and adze on the block and the hoops graded on the back
wall (HEAD) → the cask pyramid at the kerb where the carrier picks up
(FINISHED).

Calls worth defending:

- **Open front, boarded rear only, waist-high screens to the sides.** The
  screens keep the wind off the setting fire without taking the light.
- **No stone plinth.** A cooper's setting floor is beaten earth and chips, for
  the same reason the blacksmith's is: a fire is lit on it and shavings are
  swept across it all day. The timber gets a pad stone under each post instead —
  the post foot out of the wet without paving the shop.
- **The setting fire is the town's second emissive** after the forge, and its
  fuel is the shop's own shavings, which is why the shaving heap is beside it
  and not tidied away.
- **A hoop that sprung and was thrown down, still oval.** The one object here
  that records a failure, which is worth more than four that record success.
- **Pitch dropped to 0.72** from the kit's 0.86: at 0.86 a 10 m plot with 5.2 m
  eaves puts the ridge at 10.2 m, taller than the bakery, on a one-storey shed.

## 2. carpenter — slot 34, Bakers' Row

Three bands from the street. **SAWING**: the 4.2 m baulk up on cross-trestles
under a boarded lean-to, the two-man pit saw hanging in its own half-run kerf,
wedges and a drift of chips under it. **SEASONING**: two racks of boards *in
stick* — every course separated by three cross-battens so the air gets at both
faces — plus round timber chocked so it cannot roll. **JOINING**: the open
range with the tool wall (saws graded, augers, planes sole-down on the rail, a
try square hung square), the half-jointed frame on trestles at the drip line,
finished door leaves stacked by the way out, and a chair with a broken leg
brought in to be mended with the new leg lying beside it.

**D-CQ-1 — the saw pit is not a pit.** `core/terrain.py` owns `height(x, z)` and
a venue may not cut into it, so a modelled pit is a box the terrain surface
draws straight over: the player would look into a filled trench, which is worse
than not having one. This is the other historical form — trestle sawing, the
baulk carried up and the pitman working under it at ground level. It is correct,
and unlike a pit it reads from across the street instead of only from above.

Yard surface is `gravel`, not the cooper's pale chip and not the terrain's
brown. Giving each craft plot its own worked surface is the cheapest available
partial answer to town-02 §11.

## 3. chandler — slot 35, Bakers' Row

The schedule's note is the design: sited at the end of the fire lane so the
prevailing wind carries everything it renders away over the orchard. You cannot
render a smell, so it is built four ways that compound: a rendering-house flue
that never stops (8.9 m, permanent smoke emitter, 3.9 m clear of the shop
ridge); the wall behind the vats stained in a **gradient** — `stained_dark` for
the two bays the steam reaches, `stained` falling off each side, plain oak
beyond, so it reads as a consequence and not as a dirty texture; greasy ground
where the vats are skimmed; and nothing green within reach of them.

**The structural fix that mattered.** The first pass filled the whole 10 m
frontage with the shop, and the vats, the stain and the flue — everything the
venue is about — were invisible from Bakers' Row (`chandler-approach.png`,
first version). The shop now takes only the west 6.2 m and the other 3.8 m is
the **cart entry** into the rendering yard, with gate posts and a gate standing
open against the wall because it has not been shut in a year. A town workshop
plot IS a shop plus a gateway, and building it that way gives the street a view
straight through into the work.

Trade objects: dipping frames with candles graded by dip (older = fatter and
longer), a rack of them hung out under the eave to harden at eye height on the
footway, two lit tallow vats with the set-tallow lip down one side, the stirring
paddle standing in the near vat and the skimmer hooked over its rim, a settling
tub, rushlights loose in a basket and two beeswax tapers standing apart because
they cost a week's wages.

## 4. bowyer — slot 36, Sty Lane

The smallest of the six and the one with the clearest single image: a stave
bending on the tillering frame, at the third notch, with the lower limb visibly
stiffer than the upper — which is the fault the tool exists to find. Staves
stand in a graded rack (never lying: a stave stored flat takes a set) and more
of them lie on the tie beams, which is the schedule's own "staves in the
rafters". Strings dry in waxed loops on a line. Horn plates, hanks of sinew and
the glue pot over its brazier are the composite bench.

The **shooting butt** is a turf bank revetted with hurdle stakes, with a coiled
straw boss roped to its face, six arrows in it and two that fell short lying in
the line of the shot. It faces the street, not along the plot: turned side-on —
which the first pass did — it is a dark box and reads as a woodpile.

No full-plot hardstanding: the ground here is grass because the shot runs over
it, so the only made surface is the apron in front of the shop and the line worn
across the turf.

## 5. stables — slot 70, Ford Road

Eleven stalls, a hay loft over, and a yard open to Ford Road that the carriers
turn in. The stall range is open-fronted, which is the correct form (a shelter
shed) and the only way a player ever sees the inside of a stable — eleven closed
doors would be eleven closed doors. **Divisions stop at 1.35 m**, shoulder height
on a working horse, so the eye runs the whole length of the range over the top
of them.

Arranged as a stableman would: mounting block and trough at the gate where a
rider arrives; muck heap at the far downwind corner, as far from the hay as the
plot allows, steaming and nettled with the fork left in it; tack under cover at
the north end (two horse collars, bridles, a saddle over the rail); the
farrier's corner at the open south end with the shoeing tripod, the shoe box,
the hoof-paring pile and a bucket. Bedding is banked against the divisions and
thin in the middle where the horse actually stands.

The **pitching door and its hoist beam** with a truss of hay halfway up the rope
is the range's only vertical incident, and it is what stops 15 m of eaves
reading as a ruler.

## 6. waggon_shed — slot 38, Ford Road

Five open bays. Two waggons, a sledge, one bay deliberately EMPTY (a shed with
every bay full is a shed nobody uses), and the wheelwright's corner: a spare
axle on brackets, three wheels stacked flat, the broken one leaning where it
fell, an iron tyre stood on edge against the wall, tar and a brush. **Poles up**
against each bay's own post — five raked poles along a 13 m frontage is the
strongest rhythm available in this quarter and it costs five lathes.

**This venue exists because of a placement bug.** Slots 38 and 70 both read
`kit: stables` and both resolved to venue id `stables`, so `tools/render/town.mjs`
— which loads `/assets/meshes/<venue.id>.gltf` — placed the SAME mesh twice: a
16 × 12 stable range dropped onto a 14 × 8 waggon-shed plot at a different
rotation. Split in `tools/plan/plan_data.py`
(`VENUE_OF_SLOT[38] = "waggon_shed"`) so the generator, the document and the
renderer agree.

## 7. dovecote — slot 57, The Bailey

The only round building in Hearthmere, and the schedule is right that it is
worth the whole quarter for silhouette: four lathes and a band of holes buy more
in an aerial than three more houses would. Battered drum in coursed rubble, a
conical tiled roof in real courses to 7.6 m, and a louvred lantern with an iron
finial on top.

Three details make it a dovecote and not a silo: the **rat ledge** (a projecting
string course oversailing 0.22 m — a rat can climb coursed rubble but cannot get
round that, and its shadow is the only horizontal on the elevation); the **flight
holes and alighting ledge** with the whitewash streaked down the wall from each
perch, as a band and not as a global texture; and the **potence** — the post on a
pintle with two arms and a ladder that the boy swings round to reach all 240
boxes, visible through the open door and the object that explains the building.

Collision is a ring of segment boxes with the doorway segment **left out**. A
single cylinder would have sealed the door, and the door is the point.

## 8. tannery — slot 93, Tan Road, OUTSIDE the wall

The town's ugly necessary trade, and the brief says let it be ugly. Twenty-four
pits, and the liquor in them at four values because they are at four stages —
lime (milky), bate, weak tan, and old ooze — so the colour gradient states the
whole process where a grid of identical pits would state nothing. Hides on
stretcher frames, laced through the edge with cord. The currier's beam and
knives with a pile of scud beside it. Oak bark stacked under a scrap board roof,
ground tan in sacks, and the **edge-runner mill** — a 1.6 m stone wheel on its
edge in a circular trough with the horse walk worn round it — which is the
anchor and unlike anything else in Hearthmere. An open board runnel takes the
spent liquor off the platform and down the slope to the water, which is the
reason the tannery is sited here at all, so it is built rather than implied.

**D-CQ-2 — the pits stand proud instead of being dug.** Same constraint as the
saw pit: a venue may not cut `terrain.height`. The pits are therefore sunk into
a working platform 0.55 m above the yard — which is also what a real pit yard
does where the water table is high, and this one is 25 m from the Mere. The
platform is a **lattice**, not a slab: base course plus the curb walls between
the pits, so the holes are real holes. (The first pass built a solid block and
recessed the pits into it; twenty-four pits rendered as a paved terrace.)

---

## Which of these is weakest — my own ranking for the art director

1. **`tannery`.** Composition, not content. The hide stretchers screen the pit
   yard from the approach, the drying shed's roof still reads as a porch rather
   than a louvred shed, and the plot's dark `mud` slab meets the grass at a
   ruled edge. Everything the brief asked for is present and the *arrangement*
   of it has had one pass, not three. Review this one first.
2. **`chandler`.** The restructure works, but the shop is still the most generic
   building I made — 3.6 m of plaster with a door and a counter in it — and it
   is doing the job of screening the interesting half of the plot. It wants a
   loft pitching door or a jettied band to break the wall.
3. **`cooper`.** The best-arranged of the eight and still the darkest: the
   covered floor loses the shaving horse, the jointer and (partly) the
   raising-up into shadow at 09:30, which is the exact thing the open front
   exists to prevent. The gapped boarding and a hung lantern both helped. A
   second pass wants the range a metre shallower.
4. **`stables`.** Reads well and is the least *surprising* thing here. The
   eleven-stall rhythm is strong from the road; the loft is under-dressed.
5. **`dovecote`.** Strongest silhouette per triangle in the quarter. One real
   defect: the build reports `OCCLUDED: 'finial' does not clear 'cone'` — the
   finial and the cone cap top out at the same 8.57 m, so the finial is not
   standing proud of what it finishes. Cheap fix, not yet made.
6. **`waggon_shed`**, 7. **`bowyer`**, 8. **`carpenter`** — these three I would
   defend as they stand. The bowyer's butt-and-tiller pair and the carpenter's
   timber-in-stick are the two arrangements in this quarter I am most confident
   would survive a blind side-by-side.

## Defects I introduced and did not fix

- `dovecote` finial buried in the cone cap (above). One number.
- `tannery` drying shed: the louvres are emitted on the two long faces only and
  the end frames read as bare posts; the roof is still too steep for a 6 m span.
- `chandler`: the shop's upper window is placed on the wall centre-line rather
  than proud of the outer face, so only its shutters read. Same class of error
  as the one already corrected on the counter.
- Ground wear across all eight uses `props.worn_patch`, which is an octagonal
  decal. At gameplay range it reads as wear; at 2 m it reads as a shape. It is
  the right call for now but it is not a shipping answer.
- The perf gate in `tools/render/town.mjs` fails on `streets` (94 → 155 LOD0
  draws) and `shop_row` (36 → 43). Both were already failing before this work
  (town-02 "Budget, for the record") and neither is mine; none of the eight
  venues here exceeds 52 LOD0 draws or 51 k triangles.

## Incident — `content/town/hearthmere.json` was clobbered and regenerated

While splitting slot 38 off into its own venue I ran `git checkout` on
`content/town/hearthmere.json` to undo a formatting change. The v2 document was
**uncommitted work in the tree**, so that restored the v1 file and destroyed it.

Recovered by running `python tools/plan/townplan.py`, which is the document's
generator of record (`docs/plan/schedule.md` carries the "GENERATED … do not
hand-edit" banner). The regenerated file is verified identical to what I had
read out of the working copy earlier in this session: 94 building slots, 32
venues, all 15 streets, `playerSpawn` on the altar at `(43.0, 3.3, -0.5)` facing
270°, and slot 33's row byte-for-byte the same.

Two things anyone downstream should know:

1. **`landscape` was missing from `townplan.write_town`'s infrastructure list**
   while `venues/landscape.py` existed and was placed in the document — so *any*
   regeneration of `hearthmere.json`, by anyone, silently dropped the entire
   vegetation, field, garden and churchyard venue out of the town. That was a
   live landmine, not something I introduced; it is now fixed in
   `tools/plan/townplan.py` and the venue is generated rather than hand-added.
2. **`write_town` copies `lighting` and `ambient` verbatim from the previous
   file.** If anybody had hand-edited either block since the last regeneration —
   for example adding the fog parameters town-02 §5 asks for — that edit is
   gone, because the file it copied from was v1's. Both blocks now hold the
   locked 09:30 rig and the four-source smoke list, which is what v1 carried.
   Worth a glance from whoever owns atmosphere.

## Files touched

    tools/assetgen/core/venue.py        + Plot, town(), slot()
    tools/assetgen/core/kit.py          + open_range()
    tools/assetgen/core/props.py        _shavings -> shavings (public)
    tools/assetgen/venues/cooper.py     new
    tools/assetgen/venues/carpenter.py  new
    tools/assetgen/venues/chandler.py   new
    tools/assetgen/venues/bowyer.py     new
    tools/assetgen/venues/stables.py    new
    tools/assetgen/venues/waggon_shed.py new
    tools/assetgen/venues/dovecote.py   new
    tools/assetgen/venues/tannery.py    new
    tools/plan/plan_data.py             VENUE_OF_SLOT[38] = "waggon_shed"
    tools/plan/townplan.py              + landscape to the infrastructure list
    content/town/hearthmere.json        regenerated (see incident above)
    docs/plan/schedule.md               regenerated
    docs/plan/hearthmere-plan.svg       regenerated
    docs/TOWN_PLAN.md                   generated fragments respliced
