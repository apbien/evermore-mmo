# Civic and food venues — moot hall, bakery, confectioner, chophouse, bathhouse, well-house

Answering `review/reports/ad-town-02.md` §1: *"`t-arrival` looks through the church
door at a composition whose middle distance is supposed to contain the moot
hall, the confectioner and the bakery; it contains nothing, so the eye lands on
a blank guild gable."*

Six venues built, all six placed, all six looked at. Every claim below is backed
by a PNG in `review/shots/civic*`.

---

## 1. The arrival frame, before and after

| | |
| --- | --- |
| before | `review/shots/civic-base/base-arrival.png` |
| after | `review/shots/civic/civic-arrival.png` |

**Before:** the aperture's optical centre is bare brown ground with a blank
cream guild gable behind it at 110 m. Nothing between 20 m and 110 m.

**After:** the moot hall stands 60 m out and 9° left of the axis and is now the
largest object in the aperture. What it puts into the frame, in order of how
much work each element does:

1. **The void.** The ground floor is an open arcade on ten oak posts, so you
   see *daylight and market under a floating box*. It is the only mass in
   Hearthmere you can see through, and at this range that reads instantly as a
   building with people in it rather than a shape.
2. **The bell-cote**, 15.8 m to the vane, breaking the roofline left of centre.
   At 60 m it subtends 15° — about a quarter of the frame height.
3. **A slate roof.** It is the only dark roof in the aperture, against a
   middle distance that was otherwise all one saturated terracotta (AD §21).
   The value break is doing as much as the silhouette.
4. **The outside stair** on the frontage, which gives the mass a diagonal and a
   readable human scale at a range where windows have stopped resolving.

**One thing in the after-frame that is not mine and should be looked at:** a
tree canopy (from the landscape/vegetation pass) stands directly in front of the
bell-cote's louvre stage and veils the top third of it. The spirelet and vane
still clear it, but the strongest new vertical in the most important composition
in the build is being half-eaten by a tree that could move three metres north.

**What the arrival frame still does not get from me, and why.** The
confectioner is at 23 m and **29° off the axis**, and the gameplay camera's
half-FOV is 27.5°. It is outside the frame by about a degree and a half. Slot
21's note calls it "second near jamb of the arrival frame"; on the authored
geometry that is not true from the authored spawn, and no amount of work on the
building changes it. Either the note is aspirational or slot 21 wants to move
~2 m north. Flagging, not fixing — moving a slot is a plan change, not a venue
change. The bakery (65° off-axis) was never in this frame; its 12 m flue is a
south-road landmark, which is what slot 32 actually says.

---

## 2. What was built

| venue | slot | tris | draws | ent | vols | anchor |
| --- | --- | --- | --- | --- | --- | --- |
| `moot_hall` | 03 | 54,150 | 36 | 6 | 36 | 15.8 m bell-cote over an open arcade |
| `bakery` | 32 | 63,660 | 36 | 6 | 19 | 12.0 m stone flue; lit oven mouth on the sightline |
| `confectioner` | 21 | 32,416 | 31 | 3 | 9 | the town's one painted gable |
| `chophouse` | 07 | 44,282 | 37 | 6 | 14 | a real fire in a real arch, on the frontage |
| `bathhouse` | 91 | 51,694 | 35 | 9 | 14 | ridge louvre + 9 m external flue |
| `wellhouse` | 90 | 20,490 | 20 | 2 | 8 | pyramid roof over the public well |

`node tools/check_walkable.mjs` → **15/15 streets pass, 0 obstructed**, Ford
Road traversable end to end. The one unreachable door it names
(`hm.townhouse.door.15`) is not in these six.

### The design decision in each

- **moot hall** — first-floor chamber on an open arcade, because that single
  arrangement gives a hero silhouette a void at eye level, a jetty, an outside
  stair and a bell-cote for free. Function under the arcade is the butter
  market laid out by a market morning: standings → beam scale → the town's
  sealed measures on the lock-up wall → the clerk's stool. The **whipping post**
  is the residue that carries the building: seized shackles, moss and weed round
  its foot because nobody has stood there in fifty years, and a basket left
  leaning against it.
- **bakery** — the oven is the building. The beehive's mouth opens *through the
  back wall of the shop*, so from Bakers' Row you look through the counter
  opening down the whole working line (flour → trough → bench → peel) at a lit
  brick arch. Flour goes down in four rings of falling density out to 4.4 m,
  per slot 32.
- **confectioner** — the one painted frontage. Everywhere else in Hearthmere
  residue is mess; here it is *fastidiousness* — swept step, wiped counter,
  goods squared up, a cloth over the comfits — and the single spill is sugar,
  half-swept. Contrast is what stops a street reading as one generator.
- **chophouse** — sited on the shaded north side so its fire reads across the
  square (slot 07's own note). Roasting hearth on the frontage in a segmental
  brick arch, spit and joint turning in it, trestles on the paving under a
  falling awning, a **pictorial** peg-board menu (ox, fowl, fish, pie — Art
  Bible §2, no lettering). Residue is grease: black glossy flags at the door,
  bones, unwashed trenchers.
- **bathhouse** — a furnace with rooms attached. Long low range, stone
  stoke-house, ridge louvre, external 9 m flue. Wet is the whole job: dark
  flags, towels on lines, a steaming tail-race out of the east gable, pattens
  kicked off in a row at the threshold.
- **wellhouse** — the highest life-per-triangle in the brief. The lip is worn
  into a dish **on one side only** (cut into the vertices by angle, not a
  texture), rope grooves across it, moss on the north face, a puddle that never
  dries, and the gossip bench that every real well has.

---

## 3. One core change, and the reason it had to be core

### `core/siting.py` — the venue-placement frame (NEW)

**There are two rotation conventions in this repo and they are mirrors.**

- `docs/TOWN_PLAN.md` §6 and `core.building.Footprint` define a slot's frame as
  `world = centre + U·a + V·b` with `U = (cos t, sin t)`. Every `polygon` in
  `buildingSlots[]` is drawn in that frame; `venues/townhouse.py` builds 63
  masses straight into world space from it.
- The client (`client/src/main.js:174`), `tools/render/town.html:413` and
  `tools/check_walkable.mjs` all place a venue mesh with a three.js
  `rotation.y` of `rotationDeg` — which sends local `+X` to `(cos t, −sin t)`.
  `mesh.rotate_y` and `collision.rot_xz` are the same matrix.

Compose them and a mesh authored front-to-`−Z` comes out facing
`(−sin t, −cos t)` — the mirror of the `(sin t, −cos t)` the plan asked for. At
`t = 0` or `180` nobody notices, which is why fourteen venues shipped without it
surfacing. **At the moot hall's `t = 60` the building is 120° out and its front
elevation, its stair and its bell-cote all look away from the market place** —
i.e. straight out of the arrival frame.

`venues/church.py` already solved this by hand; its header works out that "local
+Z is west, out of the great door" for `rotationDeg 270`, and 270 → 180 is
exactly `−2t (mod 360)`. That is the general answer. `core/siting.py` is it,
plus the ground:

    site = Site("moot_hall")
    site.emit(ctx, geom)                        # geom authored front toward -Z
    site.collider(ctx, "box", center=site.p(...), rot_y=site.yaw(0))
    site.entity(ctx, eid, "door.moot", (x, y, z))
    site.ground(x, z)                           # terrain, in venue-local Y

Verified: for all six venues the design corner `(+w/2, −d/2)` lands **exactly**
on a vertex of the authored `polygon`, and the design front normal matches
`(sin t, −cos t)` to three decimals. It also owns `site.base` / `site.lo` /
`site.hi` so no generator has to assume `y = 0` is the ground (Directive §6.1),
and `SI.slab` / `SI.plinth_under` / `SI.rect` so a shaped plinth is one call
instead of a hand-derived `rotate_x`.

**Every venue still unbuilt should use this** — `quay`, `cooper`, `carpenter`,
`chandler`, `bowyer`, `stables`, `dovecote`, `warehouse`, `fish_eatery`,
`watermill`, `tannery`. Any of them on a rotation that is not a multiple of 90°
has the same 2t error waiting in it.

### `core/props.dust_film()` — settled dust (NEW)

Art Bible §7 says dust settles and does not stop at an edge, and the only tool
for it was `spill()`. A spill is a poured **heap** standing at its angle of
repose: `spill(kind="flour", radius=4.4)` builds a **1.3 m cone of flour in the
street**, which is exactly what the bakery shipped in its first render
(`review/shots/civic-bake/civic-bake-free.png` — the white dome filling the
lower third). `dust_film` is the other thing: 4 mm thick everywhere, a soft core
lobe, a ring of overlapping lobes at 0.5–0.9 R and a scatter of shrinking
islands to 1.5 R, so the edge is not an edge. Used for flour, sugar, soot, ash
and the chophouse's grease.

---

## 4. Defects found by looking at the renders, and fixed

Listed because each one shipped in a first cut and each is a class of mistake,
not a one-off.

1. **Moot hall stair — a 4.4 m blank triangle across a 13 m frontage.**
   `kit.stair_flight(spine=…)` is a solid raking wedge; on an external civic
   stair it hid the treads and blanked a third of the elevation (Art Bible §7).
   Rebuilt as two rubble piers, a segmental ashlar arch and a used under-stair
   store (the town's fire ladder and its hurdles), with an **open oak
   balustrade** rather than a solid parapet so the flight still reads.
2. **`limewash` is limewashed *stone*.** Passed as `plaster_mat` to
   `timber_frame_wall` it printed crazy-paving Voronoi inside every timber
   panel of the moot hall and the confectioner. Related to AD §9. Timber panels
   are `plaster`.
3. **Chophouse chimney breast built as one box** stood 0.75 m proud of the wall
   with the arch modelled on its *back* face, so the fire opening became a
   relief carving and the fire — the entire reason slot 07 is on the shaded
   side of the square — was invisible from everywhere. Rebuilt as piers + arch
   + lintel with the voussoirs on the front plane and the piers stood back by
   the ring depth.
4. **Chophouse awning: 7.3 × 3.2 m, nearly level, at 2.72 m.** From the 1.62 m
   eye it was one flat plane across the whole frame. An awning has to *fall*;
   it now falls 0.9 m over 2.7 m and stops short of the hearth bay, because an
   awning over an open roasting fire is wrong twice over.
5. **Bathhouse flue invisible.** 9.00 m authored under a 9.54 m ridge, and set
   at mid-depth so it projected onto the roof from the lane. Moved to the
   front-west corner outside the eaves, directly over the stoke-hole, and the
   pitch dropped to 0.55 (ridge 8.58). Its whole shaft is now against the sky.
6. **Bathhouse firewood walled off its own frontage** — three 1.70 m stacks ran
   from the stoke-house across the door. Two stacks at 1.35 m, fire end only.
7. **Well-house braces in mid-air, twice.** A mirrored `chamfered_prism` (which
   also inverts winding — AD §16's black polygons) and then a rotated profile.
   Now a plain rotated beam with both ends solved onto the post and the plate.
8. **Well-house bench at 0.77 m** with two "wear" boards authored flat and
   built on edge, standing up like hoardings. Art Bible §3: a bench is 0.45 m.
9. **Fire buckets hung off an open bressumer** read as four buckets floating
   under the jetty — Directive §6.1's "fixed to a wall by shown hardware"
   failing on the object the rule was written for. Moved onto the lock-up's
   masonry with plates and hooks.
10. **`worn_patch(mat="grass_worn")` on a dry street** put a bright green tongue
    across Bakers' Row. Trodden earth is `dirt`.
11. **Bakery cooling racks across the full opening** walled off the sightline to
    the oven. They now fill the left half only.
12. **A 4.2 m fire hook slung across the moot hall's market frontage** cut every
    composition the building had. Stored on brackets under the back bressumer.

---

## 5. Findings I am NOT fixing, for whoever picks them up

1. **`rotationDeg` is applied as its own mirror by the whole runtime.** See §3.
   The town renders consistently, so nothing looks *broken* — but for every
   venue whose rotation is not a multiple of 90°, the authored mass sits at
   `−2t` to its own slot polygon. Fourteen venues predate `core/siting.py`.
   `blacksmith` (t = 60) and `inn` (t = 90) are the ones to check first: the
   blacksmith's front should face ENE onto Smiths' Lane and under the runtime
   convention it faces WNW. The clean fix is one sign change in `town.html`,
   `client/src/main.js` and `check_walkable.mjs` **plus** a compensating turn in
   every venue authored against the current behaviour — which is a coordinated
   change, not a venue-level one.
2. **The chophouse fire is blocked by the market stalls.**
   `review/shots/civic/chop-square-free.png`, eye at (1, −8) looking at the
   chophouse: the stall canopies at the square's north mouth stand between the
   fountain and the hearth. The chophouse does its job; the stalls own the
   sightline. Worth a stall or two moved 3 m east.
3. **Slot 21's "second near jamb of the arrival frame" is geometrically false**
   from the authored spawn (29° off a 27.5° half-FOV). See §1.
4. **`t-report.json` still shows large GEOMETRY overlaps** —
   `warehouse × townhouse` 19,821 m², `church × townhouse` 1,804 m³ deepest.
   None involve these six.
5. **AD §20's lamp standard still bisects `t-square`.** Unowned.

---

## 6. Images

| what | file |
| --- | --- |
| **arrival frame, after** | `review/shots/civic/civic-arrival.png` |
| arrival frame, before | `review/shots/civic-base/base-arrival.png` |
| moot hall, front elevation | `review/shots/civic-moot_hall/civic-moot_hall-free.png` |
| moot hall in the market place | `review/shots/civic/moot2-free.png` |
| bakery frontage | `review/shots/civic-bakery/civic-bakery-free.png` |
| confectioner frontage | `review/shots/civic-confectioner/civic-confectioner-free.png` |
| chophouse, fire and awning | `review/shots/civic-chophouse/civic-chophouse-free.png` |
| chophouse from the square | `review/shots/civic/chop-square-free.png` |
| bathhouse, flue and louvre | `review/shots/civic-bathhouse/civic-bathhouse-free.png` |
| well-house | `review/shots/civic-wellhouse/civic-wellhouse-free.png` |
| market square | `review/shots/civic/civic-square.png` |
