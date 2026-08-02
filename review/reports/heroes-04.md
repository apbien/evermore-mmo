# heroes-04 — guild, inn and blacksmith rebuilt to their v2 slots; the fountain re-massed

Author's own report. **Not a sign-off** (`docs/REVIEW_PROTOCOL.md`): everything
below is backed by a render I looked at, and the renders are named.

## What was asked, and what shipped

| venue | slot | plot | v1 geometry | v1 fill | now |
| --- | --- | --- | --- | --- | --- |
| Adventurer's Guild | 02 | 16 x 16 @ (-33, 0) rot 90 | hall 19.0 x 11.5 + an 8 m training yard | **overhung 4.1 m** | hall 14.8 x 11.0 + 7 x 7 tower on the noted corner, 21.30 m to the vane |
| Grey Heron Inn | 01 | 16 x 14 @ (-34, -26) rot 90 | 11.5 x 9.0 | 46 % | 3-storey range + stable + yard, ~96 % of the plot used |
| Blacksmith | 43 | 18 x 14 @ (-33, +51) rot 60 | 9.5 x 7.5 | **30 %** | 11.6 x 11.6 open shed + 4.6 x 12 dwelling + apron, ~92 % |
| Market fountain | — | world origin | 3.0 m, `stone` on `cobble`, water 0.28 m under a 0.90 m lip | — | 5.40 m, `sandstone`/`ashlar_civic`/`bronze`, water 0.08 m under the lip, ten falls |

`tools/validate.py`: **0 failures**, 41 warnings (all pre-existing; the two new
`guild.py` DOOR_W/DOOR_H failures were mine and are fixed — see §7).
`node tools/check_walkable.mjs`: all three doors **reachable**, Ford Road and
all fifteen streets **PASS, 0 obstructed**. `node tools/check_client.mjs`:
boots, walks 151.5 m, no geometry failure.

---

## 1. The two questions I was asked to answer

### (a) Does the arrival frame's focal point hold now?

**Yes, with one caveat that is not mine to fix.**

`review/shots/h4/h4ship-arrival.png` (and `h4a-arrival.png` is the same camera
before the fountain went in, for the diff).

`ad-town-03.md` §(a) measured the fountain at **19 px** from the church door at
43 m and reported that the eye landed on "a long dark hull-shaped mass in front
of it". Measured off the shipped frame with a 3x crop, the fountain now stands
**~112 px** of a 900 px frame — heron crest to bottom tread. The geometric
prediction for 5.40 m at 43 m under the locked 55-degree rig is 118 px; the
12-pixel shortfall is the 3.3 m altar eye looking slightly down on it. Call it
**5.9x the object it was**.

The §3.2 checklist, re-read against the shipped frame:

| §3.2 requires | in `h4ship-arrival.png` |
| --- | --- |
| the descending church steps | **yes** — unchanged, still reads |
| a street leading the eye | **yes** — unchanged |
| the market fountain as the focal point | **yes** — 112 px, two basins, a bronze bird against sky, and the only object in the aperture with a hard value break in it |
| >= 2 other venue anchor silhouettes | **yes** — the guild tower dead centre at 71.5 m, the moot hall arcade and roof at frame-left, tiled gables and two chimneys at frame-right |

Three things made the fountain hold, and only one of them is the height:

1. **Height.** 3.0 -> 5.40 m to the crest, on a three-course stylobate 8.1 m
   across the bottom tread. The mass matters as much as the finial: a 6.3 m
   drum with nothing under it read as a bollard.
2. **Value.** It was `stone` standing on `cobble` and `stone` — the AD's words
   were "it has no edge and visually dissolves". It is now warm `sandstone`
   over `ashlar_civic` treads with a **bronze** heron, which is three values
   inside the object and a hard break against the grey paving. The bronze bird
   is the single thing the eye lands on at 43 m.
3. **Movement.** The water is no longer only horizontal. An upper tazza at
   2.55 m throws eight falls into the lower basin and four bronze heron-head
   spouts throw four more, so there are twelve bright vertical elements
   between 0.94 and 2.55 m. Falling water is what makes a fountain legible at
   40 m; a flat disc never was.

And the water can be seen: it sits **0.08 m** under a 1.02 m lip in a 5.4 m
bowl, not 0.28 m under a 0.90 m lip in a 2.1 m one. A 1.62 m eye clears that
sight-line at every range down to about 2 m. `h4f3-free.png`, `h4final-square.png`.

**The caveat.** In `h4ship-arrival.png` the whole middle distance is a pale
beige veil and the fountain is pale-on-pale within it. It holds because of the
bronze and the outline, not because of contrast. That is `ad-town-03` action 2
(atmosphere retune) and action 3 (ground blend), both still open, both outside
this brief. The fountain will get materially better the day they land and I
have not pre-compensated for them by cheating its value.

### (b) Has the silhouette gained anything?

**Yes — a second tower, and the instrument now works.**

`review/shots/h4/h4final-silhouette.png`.

`ad-town-03` §(b) called `t-silhouette` "unusable": a grey horizon plate
occluding the town and the church tower reading as "a detached black mass
floating 11 m above the town line". The horizon plate is gone (somebody else's
fix, landed before this pass) and the frame is now readable. Against it:

- The **guild tower** stands at frame x ~1020 as a distinct vertical with a
  battlemented head, four corner turrets and a pyramid cap, **attached** to a
  mass below it, topping out level with the church spire at frame x ~510.
  Those two are now the only things above the town line and they are 0.1 m
  apart, which is what slot 12's note asserts.
- The town profile now steps: church spire — guild tower — inn gable and
  stacks — moot bell-cote — roofs. Before this pass the only verticals in that
  frame were the church and the crane.

The blacksmith contributes nothing to the NORTH elevation because it is on the
south edge behind everything; its 11.40 m forge stack will show on the south
approach, which is not in the standard set. That is a gap in the harness, not
in the venue — see §8.

---

## 2. Adventurer's Guild (slot 02)

`review/shots/h4-guild/h4-guild-approach.png` (isolated, west elevation),
`review/shots/h4/h4g5-free.png` (frontage from the market side),
`h4ship-arrival.png` (the 71.5 m read).

### Where the tower goes, and how that was derived

The slot note fixes it in WORLD coordinates: `x[-32,-25] z[-8,-1]`. `Site` for
this slot composes to

    world_x = -33 - z_design        world_z = x_design

so that is design `x[-8,-1] z[-8,-1]`: a 7 x 7 tower clasping the **front-left**
corner of the plot, standing on the frontage line. Design `-X` maps to world
`-Z`, so front-left is world **north-east** — the corner the note names. The
derivation is written out in the module docstring so the next person does not
have to redo it.

### What it is

- **Stylobate** over the whole 16 x 16 block at +0.42, four ceremonial risers
  of 0.105 m across the full frontage, a sandstone nosing course all round.
- **Hall** 14.8 x 11.0, two storeys of dressed ashlar to the schedule's 8.40 m
  eaves, gable roof on a `core.roof` plate (ridge 11.81, taken from the plate,
  never hand-authored), slate, stone gable copings and kneelers, corbel table,
  two stacks that clear the ridge.
- **Tower** 7 x 7, battered base, three string courses breaking an 18 m shaft
  into four stages, quoins on every free angle, corbel table, battlements with
  real embrasures, four corner turrets with lead caps, a lead pyramid roof and
  an iron finial and vane to **21.30 m**.
- **Entrance**: a projecting porch bay with its own coping and finial, a
  3.60 m double doorway with both leaves standing open, a threshold **dished by
  boots** (a real `mesh.sheet` height function, not two boxes), and the guild's
  device — crossed blades and the town heron on a crimson shield — over it.
- **Quest board** under the porch, in shadow: 18 layered notices with a real
  age spread (colour, curl, squareness all driven off one `age` term), wax
  seals, iron pins, ribbon on the sealed commissions, and **five torn corners
  still pinned where somebody took the job**.
- **Interior visible from the door**: flagged floor with the route to the
  counter walked pale, a 4.4 m reception counter with scales and ledgers, the
  big map on the back wall (coastline, river, pins — pictorial, no lettering),
  a weapon rack half empty, and a hearth throwing warm light so the doorway
  reads as an opening into somewhere lit.
- **Crimson banners** 2.3 x 6.6 m on the tower's north and east faces per the
  note, plus a short pair flanking the porch.
- **Visible work, inside the plot**: two pells on pad-stones, hacked and
  leaning, a weapon rack against the hall front, a muster bell on a post, and
  the packs, bedroll and boots a party dumps coming off the road.

### The 0.2 m nobody had noticed

Slot 02's note says the guild's finial reaches **21.5 m**. Slot 12's note says
the church spirelet reaches 21.4 m and is *"the tallest thing in Hearthmere by
0.1 m over the guild"*. Those cannot both be true. I built the guild to
**21.30 m** so the church keeps its 0.10 m, because a town whose cathedral is
beaten by its guild hall is a different town. It is recorded at the constant in
`venues/guild.py` and it wants a line in `docs/DECISIONS.md` or a fix in
`tools/plan/plan_data.py`; I have not written either, because the plan is not
mine to edit.

### What I dropped, and why

The v1 training yard is gone. It was an 8 m ring of pells, rail and archery
butts whose own module comments admit it stood **in Ford Road** and declares no
collision for it — which is a confession, not a fix. The forecourt carries the
same "what does this organisation do" read in 9 x 3.2 m and every part of it
collides.

---

## 3. Grey Heron Inn (slot 01)

`review/shots/h4-inn/h4-inn-approach.png` and `h4-inn-silhouette.png`
(isolated), `review/shots/h4/h4i4-free.png` (in the town, from the north-east).

An inn of this class is not one box: it is a tall street range with a **yard**
beside it and the stable off the yard, because horses and carts have to get in
off the street without going through the common room. That is what fills the
plot honestly, and it is what gives the slot note its gable:

    x[-6.40, 1.00]  z[-5.95, 6.40]   main range, 3 storeys, GABLE to the street
    x[ 2.85, 7.90]  z[-0.60, 6.40]   stable range, 1.5 storeys, gable to the yard
    x[ 1.20, 8.00]  z[-7.00,-0.90]   the yard, open to the street

- **Storeys** 0.45 + 3.60 + 3.30 + 3.25 = 10.60, which is the schedule's eaves
  exactly. Ridge 14.53 — the tallest timber structure in the town, under the
  guild tower and the church, as the note requires.
- **Jetties** 0.45 m per floor on the front and both flanks, plumb at the back.
  A jetty on all four faces would have put the top floor 0.9 m outside the plot,
  and back walls were built plumb anyway. `h4-inn-silhouette.png` shows the
  three steps down the flank — that outline is the point of the form.
- **Warm light in every street-facing window**, ground floor unconditionally
  (that is the common room), upper floors at 85 % and 70 % so the facade is a
  building with people in some of the rooms rather than a lightbox.
- **Common room visible from the threshold**: hearth with a live fire, pot on
  a crane, two long tables with benches and a meal, a plank-over-barrels bar
  with casks on the stillage, a stair up to the chambers, herbs drying.
- **Sign**: a painted grey heron in relief on a weathered board, on an iron
  bracket off the first-floor jetty, hanging crooked.
- **Stable**: three bays of stable doors (top leaf open on two, shut on the
  third), a loft door with a gibbet beam and a block, straw trodden out of
  every bay, a muck heap, a barrow, tack on the wall.
- **Yard**: setted, mounting block, trough, hitching rail, a waggon pulled in
  and left standing, water butt, woodpile, lamp.
- **Residue**: boots kicked off by the door at two different angles, a bench
  and a half-drunk mug, a cat asleep on the window sill, laundry on the top
  balcony, smoke from two chimneys.

---

## 4. Blacksmith (slot 43)

`review/shots/h4-smith/h4-smith-approach.png` (isolated),
`review/shots/h4/h4s2-free.png` (looking into the shed from Smiths' Lane).

    x[-8.60,-4.00]  z[-5.60, 6.40]   dwelling bay, walled, gable to the lane
    x[-3.30, 8.30]  z[-5.20, 6.40]   work shed, roofed, OPEN to the lane
    x[-3.30, 8.30]  z[-7.00,-5.20]   the cinder apron

Design `-X` maps to world north-west on this slot, so the note's "west end" is
the design `-X` end — which is where the dwelling is.

- **The shed is `kit.open_range`**, walled only at the back and the west, half
  boarded on the east, and completely open to the lane. It declares its own
  collision so the open side really is walkable; the board gap is 35 mm so the
  light gets through the back wall and the work inside stays legible.
- **The forge** is against the back wall with a 46-ember coal bed on `coal`
  (the town's only significant emissive), a hot bar lying in it, a **sooted**
  hood on iron straps, and a stack that goes right through the roof to the
  note's **11.40 m world** — which is local 9.78 on a venue whose origin is
  +1.62, and getting that wrong by the origin is exactly how the v1 stack ended
  up 2 m short.
- **Arranged by workflow**: forge (-0.20, 4.85) -> anvil (1.05, 3.05) -> quench
  (2.55, 3.95), with the bellows behind the fire where the striker is not
  standing and `props.smith_tools` on the back boarding, which hangs tongs in
  **jaw order** rather than by length.
- **Heat, drawn**: the posts within 6 m of the fire carry a charred face on the
  fire side and are clean on the other, the floor is ground black with scale
  and cinder densest at the anvil and thinning outward, the hood is soot.
- **Residue**: half-finished blade tang-out in the scummy quench, horseshoes in
  a pile, bar stock leaning in the corner, coal heap with the shovel standing in
  it, leather apron on a hook, grindstone with its trough, hoof stand and nail
  box on the apron, somebody's cloak over the trestle and a mug going cold.
- **Dwelling**: stone ground storey (a smith builds out of what will not burn),
  framed above, tiled — "30 m from the nearest thatch" is a fire rule and this
  is the building it is written for — quoins, its own chimney, gable to the lane
  so the roofline steps down from the shed's eaves.

**A finding against the plan, not the venue.** The note asks for a *"platform
cut into the slope with a 1.1 m revetment on its north side"*. The pad
`terrain.add_pad` lays for this slot is graded **flat** — `Site` reports ground
`-0.17..+0.00` across the whole footprint — so there is nothing to retain. The
revetment code runs, samples the real terrain, and emits **one** segment where
the ground genuinely falls. Either the pad should be cut into the slope and the
platform stand proud of it, or the note should stop describing a revetment.
I have not changed the terrain: that is a town-wide surface and D-026 exists
because two agents changed shared things independently.

---

## 5. The fountain (market square)

`review/shots/h4/h4f3-free.png` (11 m), `h4final-square.png` (the square rig),
`h4ship-arrival.png` (43 m). Measurements in §1(a).

Built as: three stylobate treads (4.05 / 3.66 / 3.30 m radius, 0.15-0.16 m
risers so a player walks up them), a 6.1 m lower basin with a dished sitting
lip at 1.02 and water at 0.94, an octagonal pedestal with four bronze
heron-head spouts, a 2.84 m upper tazza at 2.55 with gadrooned underside, eight
falls off its rim and a plumb thread from the bird's beak, then a tapering
shaft and the **bronze heron** — legs, tail, half-raised wings, an S-curved
neck and a crest — with its crest at **5.40 m**.

Three defects I introduced and then found in the renders, recorded because the
second one is a trap anyone would fall into:

1. **The falls were `glass` and rendered as tan planks.** Eight diagonal wooden
   struts radiating off the tazza — worse than no water at all. They are `foam`
   now (alpha-masked, double-sided), three overlapping ribbons per fall,
   because a single masked ribbon reads as a few white flecks.
2. **The algae patches were 4-segment `lathe`s.** `M.lathe(profile, 4)` is a
   BOX, not an arc: at radius 3.065 that is a 4.3 m square, and scaling one
   axis to 0.15 turned each "patch of algae on the drum" into a 3 m green plank
   lying across the basin. It rendered as a slab of turf in the middle of the
   market place (`h4f-free.png`, before). They are tangent cards now.
3. **The basin water read as a green pond.** `kit.water_disc(depth=0.30)` drives
   the tint toward `WATER_DEEP`; a fountain basin is 0.3 m of clean conduit
   water over dressed stone. Depth 0.11 keeps D-024's "same substance as the
   mere" while looking like a fountain.

The paving's proud stones and kerb ring moved out to clear the new 4.05 m
bottom tread, and the bucket on the lip now follows the rim rather than a
hard-coded radius.

---

## 6. Core changes (one, additive)

`core/building.py: masonry_wall(..., uv=1.0)`. The tiling scale was hard-coded
at 1.0 with a comment explaining that 0.5 makes rubble read as 0.8 m boulders —
correct for rubble on a cottage, and it puts **0.4 m blocks on an 18 m tower
shaft**, which from 40 m aliases into a visible herringbone moire. The
parameter defaults to the value every existing caller was already getting, so
nothing else moved; the guild passes 0.55. Compare `h4g3-free.png` (before) with
`h4-guild-approach.png` (after) — the courses are ashlar rather than fabric.

Nothing else in `core/` was touched. Everything else is `Site`, `core.roof`,
`core.building`, `core.kit`, `core.props`, `core.streetscape` used as they are.

---

## 7. What I broke and fixed inside this pass

- `guild.py` declared module constants named `DOOR_W`/`DOOR_H` at 3.60/4.10 m.
  `tools/validate.py` checks any constant of that name against Art Bible §3's
  single-leaf 0.95 x 2.10 and **failed the build twice**, correctly. Renamed to
  `GATE_W`/`GATE_H` with a comment saying why the names are not reusable.
- The tower's pyramid roof was a `lathe(..., 4)` at radius `hw`, which is a
  square whose CORNERS are at `hw` — 4.95 m across the flats on a 7 m tower,
  small enough to hide entirely behind its own parapet. It did, in the first
  render. Radius is `hw * sqrt(2)` now.
- The guild's four entrance steps descended OUTWARD from the plot line and put
  2.3 m of tread, cheek wall and bollard into the street — reintroducing, at
  ground level, the exact defect this pass exists to remove. The flight climbs
  inward now. Likewise the inn's top-floor balcony oversailed 1.43 m; it is
  0.38 m, which is a jetty rather than an encroachment.
- **Residual overhang, stated honestly.** Measured from the built meshes:
  guild 17.2 x 17.5 m on a 16 x 16 plot, inn 16.1 x 14.8 on 16 x 14. What
  crosses the line is 0.6 m of hanging banner clear of the tower faces, 0.3 m
  of quoin and stylobate nosing, and roof verge. No **mass** leaves the plot.
  For scale: the defect this replaced was 4.1 m of training yard standing in
  Ford Road. (`blacksmith.gltf`'s reported 20.7 x 22.7 is the local AABB of an
  18 x 14 footprint turned 60 degrees — 9 + 12.1 and 15.6 + 7 — not an
  overhang.)
- **Triangle budget.** The three venues went from 6.1 MB to 18.9 MB of mesh and
  put `§7 mesh memory` over 240 MB. I took it back to 239.4 MB with cuts that
  are also art decisions, and they are listed so they can be argued with:
  square framing on the inn's flanks instead of close studding (that is how it
  was actually built — close studding went on the elevation the town could
  see); lead cames only on windows a player can walk up to; fewer, larger
  quoins; corbels at 1.12 m instead of 0.82 m; single-light openings and blank
  upper flanks on the guild's service elevations; the guild's interior long
  table dropped because the doorway's own reveal occludes it and the counter,
  map and racks are what the opening frames; banner grid density scaled to
  cloth size instead of a fixed 14 x 30 on a 0.9 m pennant.

---

## 8. Open, and not mine

1. **Draw-call gate.** `check_client.mjs` and `town.mjs` both fail §7 at the
   arrival camera: 1372-1382 draws against a budget of 900. The instrument now
   counts **scene + shadow + AO + post** (schema 2); the 900 in the Directive
   and the 727 in `ad-town-03` were scene-pass-only. Scene alone at the arrival
   camera is **561**. The budget and the instrument are measuring different
   things and one of them has to move. My three venues cost +119 draws
   (guild 32 / inn 53 / blacksmith 30 at LOD0), which is real but is not the
   difference between 561 and 1382. Note also that `review/perf-baseline.json`
   is **untracked** and was rewritten today by a harness run, so the "no new
   venues placed" regression lines it prints are not trustworthy.
   `validate.py` separately warns that cell D5 costs 66 LOD0 draws (inn +
   townhouse); the inn's 53 material-cell buckets are the highest of any venue
   and are worth a consolidation pass.
2. **The inn's principal facade has no sightline.** Slot 07 (chophouse, 10 x 10
   at world (-21.5, -33)) stands **0.5 m** off slot 01's front plot line and
   covers 4.4 m of the inn's 7.4 m street elevation; the market stalls cover
   most of the rest. I tried four camera positions across the market place and
   could not get a clean head-on frame of the Grey Heron's front — `h4i1`,
   `h4i2`, `h4i3` are all inside or behind something. The gable, the sign, the
   lit windows and the boots by the door are all pointed at a wall at arm's
   length. That is a plan adjacency and it defeats the slot note's own reason
   for putting the gable and the sign on that elevation.
3. **The atmosphere still eats the tower.** At 71.5 m in `h4ship-arrival.png`
   the guild tower is a shape, not a solid, and its crimson banner reads as pale
   tan. I moved the two big banners from `banner` (which carries an authored
   sun-bleach tinting the top half 55 % toward a lighter crimson) to
   `wool_crimson` for exactly this reason and it was not enough. `ad-town-03`
   action 2 owns this.
4. **`ashlar` moires.** Even at uv 0.55 the tower's courses alias into a
   chevron at 70 m (`h4ship-arrival.png`, crop the tower). The material's
   height/normal data needs a mip-safe course break, or hero masonry needs an
   LOD material. This is a materials job, not a venue job.
5. **The `square` camera still bisects the frame with the lamp post** and now
   also puts a tree canopy directly behind the fountain, so the bronze heron —
   which is the whole finial read — is silhouetted against dark foliage instead
   of sky from that one rig. `ad-town-03` action 10 already asks for the camera
   to move; the tree is worth checking too.
6. **The south approach is unrendered.** The blacksmith's 11.40 m forge stack
   is a silhouette element on the road in from the quest zones and no camera in
   the standard set looks at it. `ad-town-03` action 10 asks for the three
   approach silhouettes to be added; this is another argument for it.
7. **Slot 43's revetment.** See §4 — the note describes a 1.1 m revetment and
   the graded pad leaves nothing for it to retain.

---

## 9. Evidence index

| file | what it shows |
| --- | --- |
| `review/shots/h4/h4a-arrival.png` | arrival BEFORE the fountain went in |
| `review/shots/h4/h4ship-arrival.png` | arrival as shipped — fountain + guild tower |
| `review/shots/h4/h4final-silhouette.png` | north elevation; the guild tower on the skyline |
| `review/shots/h4/h4final-square.png` | the square rig; fountain mass and falls |
| `review/shots/h4/h4f-free.png` | the green-plank algae bug, for the record |
| `review/shots/h4/h4f3-free.png` | the fountain at 11 m, as shipped |
| `review/shots/h4-guild/h4-guild-approach.png` | guild, isolated, west elevation |
| `review/shots/h4/h4g3-free.png` | the ashlar herringbone moire, before the uv fix |
| `review/shots/h4/h4g5-free.png` | guild frontage, porch, device, banners, steps |
| `review/shots/h4-inn/h4-inn-approach.png` | inn, isolated: jetties, stable, roofline |
| `review/shots/h4-inn/h4-inn-silhouette.png` | inn outline — three jetty steps, two stacks |
| `review/shots/h4/h4i4-free.png` | inn in the town from the north-east |
| `review/shots/h4-smith/h4-smith-approach.png` | blacksmith dwelling and shed gable |
| `review/shots/h4/h4s2-free.png` | into the forge from Smiths' Lane |
