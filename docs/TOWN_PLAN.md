# Town Plan — Hearthmere v2

**This is the master plan. Nothing else in the rebuild starts until a builder
has read the row it is being handed from §6.** Where this conflicts with
`WORLD_BIBLE.md`, this wins and the World Bible gets updated. Where it
conflicts with `BUILD_DIRECTIVE.md` §§2–5 or with `ART_BIBLE.md`, those win.

The plan is **generated data, not prose with numbers in it.**
`tools/plan/plan_data.py` holds every coordinate; `tools/plan/townplan.py`
checks them and writes `docs/plan/hearthmere-plan.svg`,
`content/town/hearthmere.json`, and the generated tables in this file.
`tools/plan/lay.py` is what put the plots on their frontages in the first
place. The tables below sit between `<!-- BEGIN GENERATED -->` markers and are
rewritten by the tool, so the drawing, the content record and this document
cannot drift apart — which is the failure mode D-009 was written about.

```
python tools/plan/lay.py            # re-lay the plots on their frontages
python tools/plan/townplan.py       # check, then write the drawing, JSON and tables
python tools/plan/townplan.py --check
```

The checker is not decoration. It proves, from the coordinates:

- no two building masses overlap;
- no mass stands in a carriageway, and nothing at all is within 3.8 m of Ford
  Road's centreline (v1's real defect was a main street you could not walk
  down);
- nothing stands in the water and no carriageway is under it — both asked of
  `terrain.height(x, z)`, not of a polygon typed beside it, with one declared
  exemption for Ford Road across the Emberflow bridge;
- every mass is on the side of the wall it is supposed to be on;
- **every anchor of the arrival frame lies inside the church portal's cone,
  under its head, and is unblocked by any of the other 93 masses**;
- the ground falls 3.75 m from the south gate to the north gate.

---

## 1. What kind of town this is, and why it is this shape

Hearthmere is not a plan. It is four events that each left a mark, and the
marks never got tidied up.

1. **The ford.** The only safe crossing of the Emberflow for a day in either
   direction. Everything else is downstream of this fact. The drove road came
   to the crossing, and the crossing is why there is a town rather than a farm.
2. **The market at the crossing.** Travellers had to stop anyway, so they were
   sold to where they stopped. The market place is a wide place on the road,
   not a square: it is bounded on its east by the road itself, which is why the
   fountain sits off-centre and why the plots facing it are 5–8 m wide and
   10–14 m deep. Frontage on a market place is the most expensive land in a
   town of three hundred people, and narrow-and-deep is what expensive
   frontage does to a plot.
3. **The church on the knowe.** The only high dry ground. A church is the one
   building that must never flood and the one building that wants to be seen,
   so it took the knowe before anything else was built, and the rest of the
   town grew downhill and west of it. This is why the arrival frame works at
   all: the player spawns on the highest floor in Hearthmere and looks down the
   fall of the land.
4. **The guild's stone tower.** Late, rich, and from outside. It bought the
   west frontage of the market place — the best block — and faces the church
   across the market. It is the only symmetrical building in town and the only
   one in dressed stone, and it does not quite belong. That is the point.
5. **The wall.** Last. It is a customs boundary, not a defence: 5.2 m to the
   walk. It follows the river on the north and the contour everywhere else, so
   it is an irregular oval and never a square, and on the north-east it stands
   straight out of the water because there was no bank to build it on.

The consequences a builder can see:

- **Streets bend because they are cart tracks.** Ford Road runs down the fall
  line (it drains, and a laden cart can brake on it). Mere Street holds the
  −0.3 m contour for its whole 89 m — it is the drove track to the mere-side
  pastures and it is the only level street in Hearthmere, which is why the
  carriers use it.
- **The market place is irregular** because it was never set out; it is the
  space left when the plots stopped.
- **The Bailey exists because the wall does.** It is the lane that was left
  over when the circuit went up outside everyone's back fence, and it is where
  the town keeps its woodpiles, its middens and its poorest cottages.

---

## 2. Districts

Real towns are sorted by cause: water, fire, smell, defence, trade, status.
Every quarter below is where it is for one of those five reasons, and the
reason is written down so that a builder scattering residue in it knows what
kind of residue belongs.

<!-- BEGIN GENERATED districts -->
| district | cells | why it is there | what it holds |
| --- | --- | --- | --- |
| **Waterside** | D2-H4 | Water and bulk. Everything heavy arrives at the bridge or the quay and cannot be carried uphill, so the trades that handle weight sit on the lowest ground within 60 m of the water. | Stables and waggon yard, farrier, the Ferryman's Lamp, gate ward, warehouses, mill and granary. |
| **Quayside** | H2-K5 | Downstream of the bridge, so laden boats never have to pass under it, and the mere is deep enough to lie alongside. The wall runs behind the wharf, not in front of it, so the town can shut the gate without losing the moorings. | Quay, crane, customs house, warehouse row, net lofts, rope house, fish eatery, fishers' cottages. Tannery outside, downstream. |
| **The Market Place** | E5-G8 | The crossing. Travellers had to stop at the ford anyway, so they were sold to where they stopped. Frontage here is the most expensive in town, which is why the plots are 5-8 m wide and 10-14 m deep and why the buildings are three storeys. | Fountain, market cross, stalls, inn, guild, moot hall, shop row, chophouse, townhouses. |
| **Kirk Knowe** | H5-K8 | The only ground in Hearthmere that is both high and dry. A church is the one building that must never flood and the one building that wants to be seen, so it took the knowe before anything else was built. | Church of Summoning, churchyard and graveyard, bede houses, song school, parsonage, sexton, dovecote, charnel. |
| **The Fire Lane** | G8-K10 | Ovens, tallow, glue, charcoal. Downwind (the wind blows east-south-east), on the high dry side, and separated from the thatch of the west lanes by the whole width of Ford Road. | Bakery, cooper, carpenter, chandler, bowyer, sawshed, tithe barn. |
| **Southgate** | F10-H12 | Where the road climbs away. Carts stage here before the pull up to the quest zones, so the yard, the shed and the carter are here and the blacksmith is 40 m away across the lane. | Waggon shed, carter, gate ward, cottages. |
| **Smithward** | C10-E11 | The high south edge: highest, driest, furthest from thatch, and with the wind carrying sparks out over the tenter ground and the wall rather than across roofs. Charcoal comes in through the south gate, 60 m away. | Blacksmith and yard, smith's house, charcoal store, cottages, byre. |
| **The West Lanes** | A5-D9 | Poorest ground and the last to be built on: no through trade, no frontage, and the market's wash-down drains across it. Cottages, gardens, sheds, and the widest gaps between buildings in the town. | Cottages, well-house, bathhouse, kitchen gardens, tenter ground, byre, the Bailey. |
<!-- END GENERATED districts -->

Two placement rules that fall out of the causes and are worth stating
separately, because they are the ones most easily broken:

- **The wind blows east-south-east** (`ambient.wind` = `[0.82, 0, 0.57]`, and
  that is the direction of travel, so the wind comes from the west-north-west).
  Every fire trade and every smell is therefore on the **east or south-east**
  side of whatever it would otherwise foul: the bakery, cooper, carpenter and
  chandler stand in a line along Bakers' Row with the east wall and the orchard
  downwind of them, and the tannery is outside the wall on the mere shore with
  90 m and a prevailing wind between it and the nearest occupied window.
- **The river flows west to east into the Mere**, so everything that dirties
  water is downstream: the watermill takes its leat above the town, the quay is
  below the bridge, and the tannery is below the quay.

---

## 3. Levels — where the ground falls, and how it is taken up

Datum: **Y = 0.00 is the market-place paving at the fountain kerb (0, 0).**

The ground falls **3.75 m from the south gate (+1.90) to the north gate
(−1.85)** and another 1.25 m to the water. The Emberflow and the Mere share one
surface at **−3.10**, and it is the only water elevation in Hearthmere.

**The plan does not own these numbers.** `content/town/terrain.json` does, and
`core/terrain.py` and `client/src/terrain.js` are two ports of its evaluator.
The plan used to carry its own height model — a base profile plus a Gaussian
rise called Kirk Knowe — and D-022 measured it disagreeing with the real ground
by up to 1.48 m on venue origins and 1.24 m on street paths. D-024 deleted it:
`plan_data.height()` is now a one-line forward, every level in the table below
that reads `terrain` in its source column IS the height field, and the ones
that read `made` are floors, decks and treads a building owns, checked against
the ground they stand on. Kirk Knowe went with the old model; the church takes
its 2.40 m from a plinth and a perron, and whether the rise should be put back
is D-020, still open.

The analytic form is in `content/town/terrain.json`:

```
height(x, z) = lerp(baseProfile, z)
             + 1.55 * exp(-(((x - 44)/30)^2 + ((z + 2)/26)^2))
```

<!-- BEGIN GENERATED levels -->
| name | (x, z) | level | kind | source |
| --- | --- | --- | --- | --- |
| fountain kerb — DATUM | (0, 0) | +0.00 | paving | terrain |
| square, north mouth | (0, -24) | -1.05 | paving | terrain |
| square, south mouth | (0, 18) | +1.15 | paving | terrain |
| square, west kerb | (-24, -2) | +0.00 | paving | terrain |
| Market Step, upper tread | (-8, 1.6) | +0.48 | step | made, ground +0.00 |
| Market Step, lower tread | (-8, -0.4) | +0.16 | step | made, ground +0.00 |
| Ford Road at Kirk Green | (9.5, -0.5) | +0.00 | paving | terrain |
| Kirk Green paving | (19, -0.5) | +0.00 | made | terrain |
| church perron, foot | (24, -0.5) | +0.80 | made | terrain |
| church perron, head | (32, -0.5) | +2.40 | made | made, ground +0.00 |
| church floor / altar plinth | (43, -0.5) | +2.40 | floor | made, ground +0.00 |
| guild forecourt | (-25, 5) | +0.42 | made | made, ground +0.00 |
| inn threshold | (-26, -20) | -0.60 | floor | made, ground -1.05 |
| moot hall threshold | (-24, 17) | +1.35 | floor | made, ground +0.64 |
| Ferryman's Lamp floor | (19, -68) | -2.40 | floor | made, ground -1.85 |
| Wharf Lane at the pub | (19, -63) | -1.85 | paving | terrain |
| blacksmith yard platform | (-31, 57) | +1.82 | made | made, ground +1.62 |
| south gate threshold | (1, 78.5) | +1.90 | paving | terrain |
| north gate threshold | (-2.4, -76) | -1.85 | paving | terrain |
| bridge deck, crown | (-3.7, -86) | -0.90 | deck | made, ground -5.60 |
| west gate threshold | (-79, -13) | +0.40 | paving | terrain |
| water gate threshold | (50, -57) | -1.07 | paving | terrain |
| wharf deck | (58, -60) | -1.55 | deck | terrain |
| wharf lower stage | (64.8, -68.9) | -3.70 | deck | made, ground -5.35 |
| harbour bed at the quay face | (64.5, -68.5) | -5.35 | water | terrain |
| Emberflow / Mere surface | (0, -95) | -3.10 | water | made, ground -2.25 |

`terrain` levels are read straight from `content/town/terrain.json`; there is nothing to disagree with. `made` levels are floors, decks and treads a building owns, and the checker asserts each one stands on the ground rather than in it or a storey above it. See D-024.
<!-- END GENERATED levels -->

### How the fall is taken up

Nothing in Hearthmere is terraced for the sake of it. Every level change below
exists because something needed a flat floor or a cart needed a gradient it
could hold.

| where | what | how much |
| --- | --- | --- |
| **The church perron** | Three flights of shallow risers with two broad landings, 8.0 m deep and 15 m wide, from the west door down to Kirk Green. Mean slope 0.20 — deliberately shallower than 0.229, which is the slope of the sightline from the altar over the threshold. Any steeper and the steps vanish below the door sill and the arrival frame loses its foreground. | 1.60 m, 10 risers at 0.16 |
| **Churchyard terrace** | Rubble retaining wall on the west and north sides of the knowe platform, 0.9–1.6 m exposed, cut into the slope on the east. The graveyard is the fill. | up to 1.6 m |
| **The Market Step** | Three risers and a stone bench-wall running east–west across the market place at z = +0.6, with a cart ramp at its east end. It separates the upper market (dry goods, south) from the lower (fish and greens, north) — and the reason it is where it is, is that the wash-down drains north. Traders sit on it. | 0.48 m, 3 risers at 0.16 |
| **Kirkgate** | No steps: a steady 3.0% for 41 m. That is what a coffin bearer can manage and a laden cart cannot, so carts go round by Ford Road. Ends at the churchyard's north gate and six steps. | 1.26 m as gradient |
| **The Ferryman's Lamp** | Floor 0.55 m below Wharf Lane, reached by two steps down through the door. The lane has been re-metalled over itself for two hundred years; the pub has not moved. | 0.55 m |
| **The blacksmith's platform** | Cut-and-fill on the high south edge with a 1.1 m rubble revetment on its north side. A forge floor must not flood. | 1.1 m |
| **The Bailey, south** | Cut into the slope with a 0.8–1.4 m revetment on its uphill side for 50 m. The bowyer shoots at a butt against it. | 0.8–1.4 m |
| **The Water Gate** | An 0.8 m ramp inside the arch down to the wharf deck, with a cart-brake groove worn 60 mm into the threshold stone. | 0.8 m |
| **The wharf** | Stone-faced platform, deck at −1.55 with 2.25 m of dredged water at its face. The quay stair descends the face into the basin; its bottom four treads are always wet. | 3.80 m of quay wall |
| **Ford Road** | 2.5% mean over 194 m; steepest at 3.9% climbing south out of the market place. No steps anywhere: it is the cart route and it must stay one. | 4.9 m over its length |

---

## 4. The street network

Widths are kerb to kerb. `verge` is the footway the plan wants between kerb and
building line; the **hard** rule the checker enforces is that no mass may come
within `width/2 + 0.3 m` of a centreline, and a handful of frontages come down
almost to the kerb, which is normal and correct for a town of this date.

Art Bible §7 requires that **every street terminate in something worth walking
toward**. What each one ends in is in its note.

<!-- BEGIN GENERATED streets -->
| street | class | width | surface | length | falls | mean grade |
| --- | --- | --- | --- | --- | --- | --- |
| **Ford Road** | primary | 7.0 m | granite setts | 194 m | -2.25 to +2.18 | 2.3% |
| **Mere Street** | primary | 6.0 m | cobble | 89 m | -0.09 to +0.40 | 0.6% |
| **Kirk Green** | primary | 10.0 m | squared cobble | 10 m | +0.80 to +0.00 | 7.6% |
| **Wharf Lane** | secondary | 5.5 m | granite setts | 51 m | -1.85 to -1.07 | 1.5% |
| **Mill Lane** | secondary | 4.5 m | gravel, stone edged | 46 m | -1.85 to -1.85 | 0.0% |
| **Kirkgate** | secondary | 5.0 m | cobble | 41 m | -1.85 to +0.00 | 4.5% |
| **Bakers' Row** | secondary | 4.5 m | cobble, worn to dust | 55 m | +0.96 to +1.15 | 0.3% |
| **Smiths' Lane** | secondary | 4.0 m | dirt and cinder | 27 m | +1.62 to +1.62 | 0.0% |
| **Well Lane** | secondary | 4.0 m | cobble | 29 m | +1.15 to +1.15 | 0.0% |
| **The Bailey** | secondary | 4.5 m | gravel and grass | 332 m | -1.85 to -1.05 | 0.2% |
| **Tenter Lane** | lane | 3.0 m | dirt | 12 m | +1.15 to +1.15 | 0.0% |
| **Bell Alley** | alley | 2.5 m | beaten earth | 21 m | +1.15 to +1.62 | 2.2% |
| **Sty Lane** | lane | 3.0 m | beaten earth | 46 m | +1.41 to +1.18 | 0.5% |
| **Tan Road** (outside) | lane | 4.0 m | dirt, tan-black | 38 m | -1.07 to -1.05 | 0.0% |
| **Fishers' Steps** | steps | 2.5 m | stone steps | 6 m | -1.55 to -1.55 | 0.0% |

Centrelines, west-to-east or north-to-south as listed. `y` is the ground level at that point.

- `ford_road` — (-4,-96) (-4,-89) (-3.4,-80.5) (-2.4,-76) (-1.6,-68) (-0.6,-60) (0.6,-52) (2,-44) (3.8,-36) (5.6,-28) (7.4,-20) (8.8,-11) (9.5,-2) (9.2,6) (8,16) (6.6,28) (5.2,40) (3.8,52) (2.4,64) (1.4,73) (1,78.5) (0.6,88) (0,96)
  <br>The spine, and the reason the town exists. Runs straight down the fall line, so it drains and so carts can brake. Worn to a shallow trough down the centre; kerbed both sides with a deep gutter on the east where the run-off goes. It bends twice: east round the old waggon yard, then east again round the market place, because the market place was there first.
- `mere_street` — (9.2,-8.5) (0,-10) (-12,-12.5) (-24,-14) (-38,-13) (-50,-12) (-62,-11.5) (-72,-12.4) (-79,-13)
  <br>The contour road, and older than Ford Road: it is the drove track to the mere-side pastures and it holds the -0.3 m contour for its whole length, which is why it is the only level street in Hearthmere and why the carters use it.
- `kirk_green` — (24,-0.5) (19,-0.5) (13.5,-0.5)
  <br>Not a street so much as the church's forecourt, driven west through the burgage plots when the perron was rebuilt. It is the arrival axis: church door, perron, green, Ford Road, market place, fountain.
- `wharf_lane` — (-0.8,-61) (10,-62) (22,-62.4) (32,-61) (40,-59.5) (46,-58.5) (50,-57)
  <br>The bulk-goods road: everything that arrives by water crosses it. Setts laid on edge to take iron tyres, kerbs 0.22 m high, gutters wide enough to lose a boot in.
- `mill_lane` — (-1.2,-63.4) (-12,-65.4) (-24,-67.2) (-34,-69) (-42,-70.8) (-46,-71.6)
  <br>Runs along the inside of the north wall to the mill postern. Flour-dusted for its last thirty metres and rutted the rest.
- `kirkgate` — (26,-62.4) (27,-52) (27.5,-40) (27.5,-28) (27,-21)
  <br>Links the waterfront to the church, along the churchyard's west wall. Climbs 2.0 m over its length at a steady 4%, which is what a coffin bearer can manage and a laden cart cannot, so carts go round by Ford Road. Ends at the churchyard's north gate and six steps; there is no cart way through.
- `bakers_row` — (7.4,22) (18,23.6) (30,24.8) (42,25.5) (53,25) (62,23.5)
  <br>The fire lane. Every trade on it burns something — oven, tallow pan, glue pot, charcoal — and the wall is 20 m downwind of the last of them.
- `smiths_lane` — (3.4,53) (-8,55.4) (-18,58) (-23,59)
  <br>Paved for 12 m off Ford Road and then not paved at all. The surface change is the junction: past it the lane is black cinder rolled hard, and it narrows to 3.2 m at the yard gate.
- `well_lane` — (-27,18.5) (-36,20) (-46,21) (-56,21.5)
  <br>Runs from the market place to the well-house and the spring head under the west wall. The conduit that feeds the fountain is buried under its crown; the manhole slabs are the only dressed stone in the surface.
- `the_bailey` — (-52,-60) (-60,-53) (-66,-45) (-70,-36) (-72.5,-24) (-74,-12) (-74.5,2) (-73.5,18) (-70,33) (-64.5,46) (-56.5,57) (-46,65) (-32,70) (-18,72.4) (-4,73.4) (10,72.8) (24,70.6) (36,66.4) (49,62) (58,53) (65,40) (70,28) (72,15) (72.5,2) (72.5,-12) (70.5,-24)
  <br>The intramural lane. Never planned, simply what was left when the wall went up outside the back fences. Gives every wall stair, every back plot and every midden its access, and it is where the town keeps its woodpiles.
- `tenter_lane` — (-30,24) (-30,30) (-30,36)
  <br>South off Well Lane to the tenter ground, where cloth is stretched to dry. Ends in the frames, which is worth walking toward when they are full.
- `bell_alley` — (-17,31) (-17.6,41) (-18.2,52)
  <br>The back lane behind the Ford Road frontage. Laundry across it at first-floor height, privies at the far ends of the plots, and never dry.
- `sty_lane` — (4.6,45) (16,45.6) (28,45.6) (40,44.4) (50,42.4)
  <br>The back lane of the fire quarter, serving the yards, the sawpit, the sties and the privies. Ends at the wall stair under the Cinder Tower and the midden beyond it.
- `tan_road` — (50,-57) (58,-49) (64,-41) (70,-34) (75,-28)
  <br>OUTSIDE the wall. From the Water Gate along the mere shore to the tannery. Nobody walks it who does not have to.
- `fishers_steps` — (51,-58) (55,-62)
  <br>9 risers of 0.155 m taking the 1.4 m from Wharf Lane up to the Rope Walk terrace. Worn into a hollow on the left-hand side, because a man carrying a basket carries it on his right.
<!-- END GENERATED streets -->

### What each street ends in

| street | one end | the other |
| --- | --- | --- |
| Ford Road | north: the bridge, the gate arch, and beyond it the water meadow | south: the gate, and the road climbing into the trees |
| Mere Street | east: the guild tower over the market place, and the church behind it | west: the West Gate arch and the silver line of the mere |
| Kirk Green | east: the perron and the great west door | west: Ford Road, then the fountain |
| Wharf Lane | east: the Water Gate arch, the crane's jib and masts beyond | west: the Ferryman's Lamp's iron lamp on its bracket, and the fork |
| Mill Lane | west: the mill wheel through the postern arch | east: the fork, the horse trough, the pub |
| Kirkgate | south: the churchyard gate and the tower over it | north: the wharf and open water |
| Bakers' Row | east: the dovecote and the churchyard's east wall | west: Ford Road and the shop row's painted gable |
| Smiths' Lane | west: the forge's open front, the fire, the chimney | east: Ford Road |
| Well Lane | west: the well-house canopy and the bathhouse flue | east: the market place and the moot hall's bell-cote |
| Sty Lane | east: the wall stair under the Cinder Tower | west: Ford Road |
| The Bailey | curves throughout, so it always ends in the next tower | — |
| Tenter Lane | south: the tenter frames, full of cloth | north: Well Lane |
| Bell Alley | south: a lit gable and the smithy's smoke | north: the market place's south-west corner |

### Junctions, and how each resolves

A junction is a piece of design, not a place where two polylines happen to
cross. These are the fourteen the plan has.

| # | at | what happens |
| --- | --- | --- |
| J1 | Bridgefoot, (−3.4, −80.5) | Gate flat meets the bridge's south abutment; the water starts 6.1 m further north. The old ford's stone approach ramp branches east and dies in the water: broken kerb, cart ruts full of weed. |
| J2 | North Gate, (−2.4, −76.0) | The road pinches from 7.0 m to the 4.2 m arch and re-widens. Spur stones at both jambs, deeply scored by nave hubs. |
| J3 | The Fork, (−1.0, −62.5) | Ford Road continues south; Wharf Lane leaves east and Mill Lane leaves west 2 m further north, so it is two tees and not a crossroads. Resolved with a triangular kerbed island carrying the horse trough — which is *why* carts swing wide here and why the corner is worn. |
| J4 | Kirkgate × Wharf Lane, (+26, −62) | Tee. Kirkgate's 5 m mouth splayed 3 m each side, chamfered corner stone, one bollard. |
| J5 | Market place, north mouth, (+6, −27) | Kerbs stop and the paving changes from setts to squared cobble. A line of six bollards keeps carts off the stalls. |
| J6 | Mere Street × market place, (−24, −14) | The street mouth splays from 6.0 m to 10 m over 8 m. Level taken up by the Market Step across the north half and a cart ramp on the south. |
| J7 | Ford Road × Kirk Green, (+11, −0.5) | A **staggered** crossroads, not a crossroads: Kirk Green's axis is at z = −0.5, Mere Street leaves 8 m north at z = −8.5. The church approach and the old track never lined up and were never made to. A triangular paved island carries the conduit standpipe. |
| J8 | Ford Road × Bakers' Row, (+7.4, +22) | Tee on the east. Corner plot cut back to a splay; the bakery's oven-house forms the corner and its flue is the marker. |
| J9 | Ford Road × Smiths' Lane, (+3.4, +53) | Tee on the west at a skew. The lane is paved for 12 m and then is not paved at all: **the surface change is the junction.** It narrows to 3.2 m at the yard gate. |
| J10 | South Gate, (+1.0, +78.5) | Gate, waggon yard opening east, and the Bailey crossing 5 m inside. |
| J11 | West Gate, (−79, −13) | Mere Street meets the Bailey in a small triangular open space — Westgate Green — with the gate ward's cottage and a mounting block. |
| J12 | Water Gate, (+50, −57) | The lane passes through a 4.6 m arch onto the wharf. An 0.8 m ramp inside the arch takes the drop; a boat wicket 1.6 m wide is cut in the north jamb. |
| J13 | Well Lane × market place, (−27, +18.5) | The market place's south-west corner. Well Lane leaves at a skew and the corner plot is cut back; the conduit manhole slabs are the only dressed stone in the surface. |
| J14 | The Bailey × Ford Road, south, (+2, +73) | Crossroads at a skew. The Bailey is unpaved and simply stops at Ford Road's kerbs on both sides — you step up onto the road and down off it. |

---

## 5. The wall

Low, thick and a customs boundary rather than a defence: Hearthmere has never
been besieged and its gate is decorative in the way a prosperous trading town's
gate is. The oldest stretch, north-west of the Mill Tower, is lower (4.4 m) and
thicker (1.8 m) with rubble core showing through the patches; the south-east
stretch is sixty years old and neatly ashlar-faced. A dry ditch 5 m wide and
1.6 m deep runs outside the south and west; on the north the river does the job.

The **wall-walk** is 1.6 m wide and continuous except over the Water Gate,
where it steps down 1.2 m across the arch. Five mural stairs reach it.
Semicircular towers are 5.6 m external, project 3.4 m and rise 2.6 m above the
walk; the two square angle towers (Heron and Tenter) reach 11.5 m.

**From the Crane Tower to the Heron Tower the wall runs along the mere**, its
outer face 0.8–4.0 m inside the shoreline with the berm and Tan Road on the
strip between. The plan originally claimed the face *was* the shoreline; it
cannot be, because Tan Road runs outside the wall on exactly that stretch and
water on the wall would put a road under it (D-024). The batter still stands in
wet ground and that 27 m is still the town's strongest silhouette from a boat,
and it is still the reason the quay is a projecting wharf rather than a strip
of bank — there is no bank there worth the name.

<!-- BEGIN GENERATED wall -->
Closed polyline, 41 vertices, clockwise from the North Gate. 6.0 m to the wall-walk and a 1.2 m parapet where the curtain is ordinary, 1.4 m thick battering to 1.1 m — but the crown is authored per stretch, from the 2.35 m robbed garden wall on the west to the 7.9 m Mere frontage. The towers are older than the curtain and are individually scheduled below.

`(-2.4,-76) (10,-75.6) (20,-74.4) (28,-72.4) (34,-70) (40,-66.8) (45,-62.6) (50,-57) (55,-51.4) (60,-43.4) (66,-35) (71,-29) (75,-20) (77.5,-8) (78,5) (77,20) (75,34) (70,48) (62,60) (50,69) (34,74.5) (18,77.6) (1,78.5) (-14,78) (-30,75.6) (-45,71) (-58,64) (-68,53) (-75,39) (-79,23) (-80,7) (-79.4,-6) (-79,-13) (-78,-26) (-75,-40) (-70,-52) (-62,-62) (-52,-68.6) (-38,-73.2) (-24,-75.4) (-12,-76.2)`

| gate | kind | at | clear | head | notes |
| --- | --- | --- | --- | --- | --- |
| **North Gate** | gate | (-2.4, -76) | 4.2 m | 5.0 m | Ford Road and the bridge. Twin drum towers, 12.8 m overall, spur stones scored by nave hubs, the town's heron carved on the keystone. Departure and return frame. |
| **South Gate** | gate | (1, 78.5) | 4.0 m | 4.8 m | Ford Road climbing away to the quest zones. Single square gatehouse, 10.5 m, ward's chamber over the arch. |
| **West Gate** | gate | (-79, -13) | 3.8 m | 4.6 m | Mere Street to the west pastures. The oldest gate, its arch settled 0.2 m out of plumb and pinned with iron cramps. |
| **Water Gate** | water | (50, -57) | 4.6 m | 5.4 m | Wharf Lane onto the wharf. Wide cart arch with a portcullis groove never fitted, plus a 1.6 m boat wicket at the north jamb. A 0.8 m ramp inside the arch takes the drop to the deck, with a cart-brake groove worn 60 mm into the threshold stone. |
| **Mill Postern** | postern | (-46.5, -71.6) | 2.2 m | 2.9 m | Mill Lane to the watermill and the leat. Foot and handcart only. |
| **Ferry Postern** | postern | (17, -74.9) | 1.9 m | 2.6 m | The old ferry stair, behind the Ferryman's Lamp. The stair is still there; the ferry has not run since the bridge was built. |
| **East Postern** | postern | (78, 4) | 2.0 m | 2.7 m | Onto the orchard and the graveyard extension. Kept locked at dusk. |

| tower | at | shape | height | roof | cell |
| --- | --- | --- | --- | --- | --- |
| Mill Tower | (-52, -68.6) | round | 13.6 m | cone | C2 |
| Bridgefoot Tower | (-12, -76.2) | round | 15.8 m | cone | F2 |
| Ferry Tower | (20, -74.4) | round | 12.8 m | cone | H2 |
| Crane Tower | (45, -62.6) | round | 15.2 m | cone | I3 |
| Heron Tower | (66, -35) | square | 18.4 m | pyramid | K4 |
| Orchard Tower | (77, 20) | round | 11.4 m | open | K8 |
| Cinder Tower | (62, 60) | round | 14 m | cone | J10 |
| Southgate Tower | (-30, 75.6) | round | 15 m | cone | E11 |
| Tenter Tower | (-68, 53) | square | 17.2 m | pyramid | B10 |
| Spring Tower | (-80, 7) | round | 10.6 m | open | B7 |
| Pasture Tower | (-78, -26) | round | 13.2 m | cone | B5 |

Mural stairs to the wall-walk at (-6, -74.6), (52.5, -53), (74.5, 22), (-6, 76.6), (-79.4, -6).
<!-- END GENERATED wall -->

---

## 6. The building schedule

**94 discrete building masses** — 90 inside the wall, 4 outside (watermill,
tannery, crane, sties). BUILD_DIRECTIVE §5 asks for 75–95.

Read a row like this: the plot is a rectangle `w × d` centred on `centre`,
rotated so its principal facade points along `faces` (forward = `(sin θ, 0,
−cos θ)`, so 0° faces north/−Z, 90° east, 180° south, 270° west). `w` runs
along the frontage and `d` runs back into the plot, so the front face sits at
`centre + forward × d/2`. `ridge` is `along` for eaves-to-the-street or `gable`
for gable-end-to-the-street. The four world-space corners of every plot are in
`content/town/hearthmere.json` under `buildingSlots[].polygon` — use those
rather than recomputing, so a rounding difference cannot put a wall 40 mm into
a neighbour.

**Ground level.** Every row carries `groundY`. Derive Y from
`core/terrain.py`, never from the number alone, and never assume 0
(BUILD_DIRECTIVE §6.1). The number is there so that a mismatch is visible.

The same table is written to `docs/plan/schedule.md` and drawn, numbered, on
`docs/plan/hearthmere-plan.svg`.

<!-- BEGIN GENERATED schedule -->
| # | slot id | kit / venue | centre x,z | w x d | faces | st | eaves | ridge | cells | fronts | role |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 01 | `hm.slot.01.inn` | `inn` | -34.0, -26.0 | 16.0 x 14.0 | 90&deg; | 3 | 10.6 | gable | D4 D5 E4 E5 | the market place | hero |
| 02 | `hm.slot.02.guild` | `guild` | -33.0, +0.0 | 16.0 x 16.0 | 90&deg; | 2 | 8.4 | along | D6 D7 E6 E7 | the market place | hero |
| 03 | `hm.slot.03.moot` | `moot_hall` | -16.0, +9.0 | 13.0 x 8.0 | 60&deg; | 2 | 7.2 | along | E7 E8 F7 F8 | the market place | secondary |
| 04 | `hm.slot.04.store` | `shop_row` | -19.0, +23.5 | 8.0 x 11.0 | 0&deg; | 2 | 6.6 | along | E8 F8 | the market place | secondary |
| 05 | `hm.slot.05.apothecary` | `shop_row` | -11.5, +23.5 | 6.0 x 11.0 | 0&deg; | 2 | 6.6 | along | F8 | the market place | secondary |
| 06 | `hm.slot.06.tailor` | `shop_row` | -5.5, +23.5 | 6.0 x 11.0 | 0&deg; | 2 | 6.9 | along | F8 | the market place | secondary |
| 07 | `hm.slot.07.chophouse` | `chophouse` | -21.3, -38.0 | 9.4 x 9.4 | 180&deg; | 2 | 6.4 | along | E4 | the market place | secondary |
| 08 | `hm.slot.08.townhouse_a` | `townhouse` | -12.0, -33.0 | 7.0 x 10.0 | 180&deg; | 2 | 6.2 | along | F4 F5 | the market place | filler |
| 09 | `hm.slot.09.townhouse_b` | `townhouse` | -4.5, -33.0 | 6.0 x 10.0 | 180&deg; | 3 | 8.0 | gable | F4 F5 | the market place | filler |
| 10 | `hm.slot.10.townhouse_c` | `townhouse` | +17.3, -20.6 | 4.0 x 9.0 | 261&deg; | 2 | 7.4 | gable | G5 H5 | Ford Road | filler |
| 11 | `hm.slot.11.church` | `church` | +44.0, -0.5 | 20.0 x 24.0 | 270&deg; | 1 | 9.0 | gable | H6 H7 I6 I7 J6 J7 | Kirk Green | hero |
| 12 | `hm.slot.12.church_tower` | `church` | +35.8, -14.3 | 7.6 x 7.6 | 270&deg; | 1 | 18.4 | flat | H5 H6 I5 I6 | Kirk Green | hero |
| 13 | `hm.slot.13.parsonage` | `townhouse` | +50.0, +15.5 | 11.0 x 9.0 | 270&deg; | 2 | 6.4 | along | I7 I8 J7 J8 | Kirkgate | filler |
| 14 | `hm.slot.14.bede_houses` | `townhouse` | +65.0, -2.4 | 24.0 x 8.0 | 90&deg; | 1 | 3.4 | along | J6 J7 K6 K7 | The Bailey | filler |
| 15 | `hm.slot.15.song_school` | `townhouse` | +48.0, -18.0 | 10.0 x 7.0 | 0&deg; | 1 | 4.4 | along | I5 I6 J5 J6 | Kirkgate | filler |
| 16 | `hm.slot.16.sexton` | `cottage` | +57.0, -19.0 | 7.0 x 6.0 | 180&deg; | 1 | 3.8 | along | J5 | Kirkgate | filler |
| 17 | `hm.slot.17.lychgate` | `church` | +24.0, -0.5 | 3.6 x 3.2 | 270&deg; | 1 | 2.6 | gable | H6 H7 | Kirk Green | hero |
| 18 | `hm.slot.18.charnel` | `cottage` | +57.0, +14.0 | 6.0 x 4.5 | 90&deg; | 1 | 2.8 | along | J7 J8 | Kirkgate | filler |
| 19 | `hm.slot.19.workshop_a` | `workshop` | +27.6, +15.7 | 7.0 x 10.0 | 186&deg; | 2 | 6.4 | gable | H7 H8 | Bakers' Row | filler |
| 20 | `hm.slot.20.townhouse_d` | `townhouse` | +18.7, -15.2 | 7.0 x 10.0 | 261&deg; | 2 | 6.2 | gable | G5 G6 H5 H6 | Ford Road | filler |
| 21 | `hm.slot.21.confectioner` | `confectioner` | +20.5, +12.0 | 6.0 x 10.0 | 0&deg; | 2 | 6.4 | gable | H7 H8 | Kirk Green | secondary |
| 22 | `hm.slot.22.townhouse_e` | `townhouse` | +16.2, +35.8 | 5.5 x 10.0 | 277&deg; | 2 | 6.2 | gable | G9 H9 | Ford Road | filler |
| 23 | `hm.slot.23.townhouse_f` | `townhouse` | -4.9, +32.9 | 6.0 x 11.0 | 97&deg; | 2 | 6.4 | gable | F8 F9 G8 G9 | Ford Road | filler |
| 24 | `hm.slot.24.townhouse_g` | `townhouse` | -5.8, +39.8 | 6.0 x 11.0 | 97&deg; | 3 | 8.2 | gable | F9 G9 | Ford Road | filler |
| 25 | `hm.slot.25.cordwainer` | `workshop` | -6.6, +46.8 | 6.0 x 11.0 | 97&deg; | 2 | 6.4 | gable | F10 F9 | Ford Road | filler |
| 26 | `hm.slot.26.cottage_a` | `cottage` | -23.4, +34.1 | 8.0 x 8.0 | 93&deg; | 1 | 4.2 | along | E8 E9 | Bell Alley | filler |
| 27 | `hm.slot.27.cottage_b` | `cottage` | -44.0, +57.1 | 8.0 x 8.0 | 217&deg; | 1 | 4.2 | along | C10 D10 | The Bailey | filler |
| 28 | `hm.slot.28.shed_a` | `shed` | -22.6, +47.2 | 6.0 x 5.0 | 93&deg; | 1 | 2.9 | along | E10 E9 | Bell Alley | filler |
| 29 | `hm.slot.29.cottage_c` | `cottage` | -36.6, +34.5 | 9.0 x 8.0 | 90&deg; | 1 | 4.4 | along | D8 D9 | Tenter Lane | filler |
| 30 | `hm.slot.30.cottage_d` | `cottage` | +66.7, +52.7 | 9.0 x 8.0 | 298&deg; | 1 | 4.4 | along | J10 J9 K10 K9 | The Bailey | filler |
| 31 | `hm.slot.31.shed_b` | `shed` | -15.9, +66.7 | 6.0 x 4.5 | 184&deg; | 1 | 2.8 | along | E11 F11 | The Bailey | filler |
| 32 | `hm.slot.32.bakery` | `bakery` | +27.3, +33.4 | 11.0 x 10.0 | 6&deg; | 2 | 6.6 | along | H8 H9 I8 I9 | Bakers' Row | secondary |
| 33 | `hm.slot.33.cooper` | `cooper` | +39.2, +34.2 | 12.0 x 10.0 | 3&deg; | 1 | 5.2 | along | I8 I9 | Bakers' Row | secondary |
| 34 | `hm.slot.34.carpenter` | `carpenter` | +53.1, +33.9 | 14.0 x 10.0 | 357&deg; | 1 | 5.6 | along | I8 I9 J8 J9 | Bakers' Row | secondary |
| 35 | `hm.slot.35.chandler` | `chandler` | +40.2, +17.0 | 10.0 x 9.0 | 183&deg; | 1 | 5.0 | along | I7 I8 | Bakers' Row | secondary |
| 36 | `hm.slot.36.bowyer` | `bowyer` | +48.7, +49.4 | 9.0 x 8.0 | 349&deg; | 1 | 4.8 | along | I10 I9 J10 J9 | Sty Lane | secondary |
| 37 | `hm.slot.37.sawshed` | `shed` | +38.6, +50.2 | 10.0 x 6.0 | 354&deg; | 1 | 3.6 | along | I10 I9 | Sty Lane | filler |
| 38 | `hm.slot.38.waggon_shed` | `stables` | +14.8, -29.9 | 14.0 x 8.0 | 257&deg; | 1 | 4.6 | along | G4 G5 H4 H5 | Ford Road | secondary |
| 39 | `hm.slot.39.carter` | `cottage` | +13.0, +54.6 | 8.0 x 8.0 | 277&deg; | 1 | 4.2 | along | G10 H10 | Ford Road | filler |
| 40 | `hm.slot.40.gateward_s` | `cottage` | -9.0, +62.9 | 8.0 x 7.0 | 345&deg; | 1 | 4.0 | along | F10 F11 | Smiths' Lane | filler |
| 41 | `hm.slot.41.cottage_e` | `cottage` | +60.8, +60.9 | 9.0 x 8.0 | 315&deg; | 1 | 4.4 | along | J10 J11 K10 K11 | The Bailey | filler |
| 42 | `hm.slot.42.cottage_f` | `cottage` | +30.0, +60.5 | 9.0 x 8.0 | 161&deg; | 1 | 4.4 | along | H10 H11 I10 I11 | The Bailey | filler |
| 43 | `hm.slot.43.blacksmith` | `blacksmith` | -33.0, +51.0 | 18.0 x 14.0 | 60&deg; | 1 | 5.4 | along | D10 D9 E10 E9 | Smiths' Lane | hero |
| 44 | `hm.slot.44.smith_house` | `townhouse` | +12.5, +64.8 | 9.0 x 8.0 | 171&deg; | 2 | 6.0 | along | G10 G11 H10 H11 | The Bailey | filler |
| 45 | `hm.slot.45.charcoal_store` | `shed` | -27.5, +64.1 | 8.0 x 6.0 | 190&deg; | 1 | 3.4 | along | E10 E11 | The Bailey | filler |
| 46 | `hm.slot.46.cottage_g` | `cottage` | +64.2, +15.9 | 9.0 x 8.0 | 99&deg; | 1 | 4.4 | along | J7 J8 K7 K8 | The Bailey | filler |
| 47 | `hm.slot.47.cottage_h` | `cottage` | -56.6, +44.1 | 9.0 x 8.0 | 234&deg; | 1 | 4.4 | along | C10 C9 | The Bailey | filler |
| 48 | `hm.slot.48.byre` | `shed` | -52.2, +14.3 | 10.0 x 7.0 | 177&deg; | 1 | 4.0 | along | C7 C8 D7 D8 | Well Lane | filler |
| 49 | `hm.slot.49.cottage_i` | `cottage` | +22.1, +52.2 | 9.0 x 8.0 | 0&deg; | 1 | 4.4 | along | H10 | Sty Lane | filler |
| 50 | `hm.slot.50.cottage_j` | `cottage` | -37.1, +12.6 | 9.0 x 8.0 | 174&deg; | 1 | 4.4 | along | D7 D8 | Well Lane | filler |
| 51 | `hm.slot.51.cottage_k` | `cottage` | +71.2, +44.4 | 9.0 x 8.0 | 298&deg; | 1 | 4.4 | along | K10 K9 | The Bailey | filler |
| 52 | `hm.slot.52.sties` | `shed` | +68.0, +66.0 | 8.0 x 5.0 | 225&deg; | 1 | 2.8 | along | J10 J11 K10 K11 | The Bailey *(outside)* | filler |
| 53 | `hm.slot.53.privy_row` | `shed` | +30.0, +49.5 | 6.0 x 3.0 | 354&deg; | 1 | 2.4 | along | H10 H9 I10 I9 | Sty Lane | filler |
| 54 | `hm.slot.54.cottage_l` | `cottage` | +10.8, -45.4 | 7.0 x 7.0 | 257&deg; | 1 | 4.2 | along | G3 G4 | Mill Lane | filler |
| 55 | `hm.slot.55.cottage_m` | `cottage` | -40.3, -62.5 | 8.0 x 8.0 | 13&deg; | 1 | 4.2 | along | D2 D3 | Mill Lane | filler |
| 56 | `hm.slot.56.cottage_n` | `cottage` | -11.9, -73.2 | 8.0 x 8.0 | 189&deg; | 1 | 4.2 | along | E2 F2 | Mill Lane | filler |
| 57 | `hm.slot.57.dovecote` | `dovecote` | +65.2, -17.8 | 5.4 x 5.4 | 81&deg; | 1 | 6.2 | cone | J5 J6 K5 K6 | The Bailey | secondary |
| 58 | `hm.slot.58.tithe_barn` | `warehouse` | +35.5, -24.9 | 13.0 x 8.0 | 274&deg; | 1 | 5.8 | along | H5 I5 | Kirkgate | filler |
| 59 | `hm.slot.59.warehouse_a` | `warehouse` | +40.4, +72.3 | 14.0 x 7.0 | 341&deg; | 2 | 7.2 | along | I11 J11 | The Bailey | secondary |
| 60 | `hm.slot.60.netloft` | `warehouse` | +30.6, -68.5 | 10.0 x 5.5 | 188&deg; | 2 | 6.2 | along | H2 I2 | Wharf Lane | filler |
| 61 | `hm.slot.61.customs` | `quay` | +48.0, -44.0 | 12.0 x 10.0 | 315&deg; | 2 | 7.0 | along | I3 I4 J3 J4 | Wharf Lane | hero |
| 62 | `hm.slot.62.warehouse_b` | `warehouse` | +35.7, -40.0 | 12.0 x 8.0 | 270&deg; | 2 | 7.4 | along | H4 I4 | Kirkgate | secondary |
| 63 | `hm.slot.63.warehouse_c` | `warehouse` | -63.7, -59.8 | 11.0 x 8.0 | 139&deg; | 2 | 7.2 | along | B2 B3 C2 C3 | The Bailey | secondary |
| 64 | `hm.slot.64.fish_eatery` | `fish_eatery` | +36.4, -51.6 | 10.0 x 8.0 | 11&deg; | 1 | 5.0 | along | H3 H4 I3 I4 | Wharf Lane | secondary |
| 65 | `hm.slot.65.fisher_a` | `cottage` | +18.9, -53.8 | 8.0 x 8.0 | 358&deg; | 1 | 4.2 | along | G3 H3 | Wharf Lane | filler |
| 66 | `hm.slot.66.fisher_b` | `cottage` | +20.9, +63.4 | 8.0 x 8.0 | 171&deg; | 1 | 4.2 | along | H10 H11 | The Bailey | filler |
| 67 | `hm.slot.67.ropehouse` | `warehouse` | +52.0, -31.0 | 24.0 x 5.0 | 340&deg; | 1 | 4.4 | along | I4 I5 J4 J5 K4 K5 | Wharf Lane | filler |
| 68 | `hm.slot.68.cottage_o` | `cottage` | +19.1, -45.1 | 8.0 x 8.0 | 88&deg; | 1 | 4.2 | along | G3 G4 H3 H4 | Kirkgate | filler |
| 69 | `hm.slot.69.cottage_p` | `cottage` | +9.4, -53.5 | 8.0 x 8.0 | 355&deg; | 1 | 4.2 | along | G3 | Wharf Lane | filler |
| 70 | `hm.slot.70.stables` | `stables` | -10.2, -47.4 | 16.0 x 12.0 | 80&deg; | 1 | 5.4 | along | E3 E4 F3 F4 | Ford Road | secondary |
| 71 | `hm.slot.71.farrier` | `blacksmith` | -30.0, -48.0 | 9.0 x 8.0 | 90&deg; | 1 | 4.6 | along | D3 D4 E3 E4 | Ford Road | filler |
| 72 | `hm.slot.72.pub` | `pub` | +19.0, -70.0 | 12.0 x 7.5 | 180&deg; | 2 | 5.4 | along | G2 H2 | Wharf Lane | hero |
| 73 | `hm.slot.73.gateward_n` | `cottage` | +6.9, -69.7 | 8.0 x 7.0 | 175&deg; | 1 | 4.0 | along | G2 | Wharf Lane | filler |
| 74 | `hm.slot.74.cottage_q` | `cottage` | -55.1, -20.5 | 8.0 x 8.0 | 178&deg; | 1 | 4.2 | along | C5 | Mere Street | filler |
| 75 | `hm.slot.75.cottage_r` | `cottage` | -55.9, -3.0 | 8.0 x 8.0 | 358&deg; | 1 | 4.2 | along | C6 C7 | Mere Street | filler |
| 76 | `hm.slot.76.shed_c` | `shed` | -58.1, -45.5 | 6.0 x 5.0 | 307&deg; | 1 | 3.0 | along | C3 C4 | The Bailey | filler |
| 77 | `hm.slot.77.watermill` | `watermill` | -49.0, -79.5 | 13.0 x 10.0 | 150&deg; | 2 | 7.4 | along | C1 C2 D1 D2 | Mill Lane *(outside)* | secondary |
| 78 | `hm.slot.78.granary` | `watermill` | -22.9, -75.4 | 12.0 x 9.0 | 190&deg; | 2 | 6.8 | along | E1 E2 | Mill Lane | secondary |
| 79 | `hm.slot.79.miller` | `townhouse` | -31.3, -60.1 | 10.0 x 9.0 | 10&deg; | 2 | 6.4 | along | D2 D3 E2 E3 | Mill Lane | filler |
| 80 | `hm.slot.80.malthouse` | `warehouse` | -66.1, +7.1 | 11.0 x 9.0 | 266&deg; | 2 | 6.8 | along | B7 C7 | The Bailey | filler |
| 81 | `hm.slot.81.cottage_s` | `cottage` | -21.6, -59.0 | 9.0 x 8.0 | 9&deg; | 1 | 4.2 | along | E3 | Mill Lane | filler |
| 82 | `hm.slot.82.cottage_t` | `cottage` | -51.2, -50.7 | 9.0 x 8.0 | 319&deg; | 1 | 4.2 | along | C3 C4 D3 D4 | The Bailey | filler |
| 83 | `hm.slot.83.cottage_u` | `cottage` | -63.6, -29.5 | 9.0 x 8.0 | 282&deg; | 1 | 4.2 | along | B4 B5 C4 C5 | The Bailey | filler |
| 84 | `hm.slot.84.shed_d` | `shed` | -62.4, -38.1 | 7.0 x 5.0 | 294&deg; | 1 | 3.0 | along | B4 C4 | The Bailey | filler |
| 85 | `hm.slot.85.cottage_v` | `cottage` | -46.0, -21.1 | 9.0 x 8.0 | 175&deg; | 1 | 4.4 | along | C5 D5 | Mere Street | filler |
| 86 | `hm.slot.86.cottage_w` | `cottage` | -64.4, -20.5 | 9.0 x 8.0 | 185&deg; | 1 | 4.4 | along | B5 C5 | Mere Street | filler |
| 87 | `hm.slot.87.gateward_w` | `cottage` | -66.5, +16.2 | 7.0 x 7.0 | 266&deg; | 1 | 4.0 | along | B7 B8 C7 C8 | The Bailey | filler |
| 88 | `hm.slot.88.cottage_x` | `cottage` | -47.0, -3.5 | 9.0 x 8.0 | 355&deg; | 1 | 4.4 | along | C6 C7 D6 D7 | Mere Street | filler |
| 89 | `hm.slot.89.cottage_y` | `cottage` | -65.0, -3.0 | 9.0 x 8.0 | 5&deg; | 1 | 4.4 | along | B6 B7 C6 C7 | Mere Street | filler |
| 90 | `hm.slot.90.wellhouse` | `wellhouse` | -37.7, +26.5 | 5.6 x 5.6 | 354&deg; | 1 | 3.2 | along | D8 | Well Lane | secondary |
| 91 | `hm.slot.91.bathhouse` | `bathhouse` | -51.9, +30.3 | 14.0 x 11.0 | 357&deg; | 1 | 5.6 | along | C8 C9 D8 D9 | Well Lane | secondary |
| 92 | `hm.slot.92.cottage_z` | `cottage` | -64.2, +24.7 | 9.0 x 8.0 | 257&deg; | 1 | 4.4 | along | B8 C8 | The Bailey | filler |
| 93 | `hm.slot.93.tannery` | `tannery` | +86.0, -16.0 | 14.0 x 10.0 | 225&deg; | 1 | 5.0 | along | K5 K6 L5 L6 | the market place *(outside)* | secondary |
| 94 | `hm.slot.94.crane_house` | `quay` | +62.0, -57.0 | 7.0 x 7.0 | 42&deg; | 1 | 5.6 | along | J3 K3 | the market place *(outside)* | hero |

**Slot notes.** `ground` is the terrain height at the plot centre; the ground floor sits on it unless the note says otherwise. `w` runs along the frontage, `d` back into the plot, and the front face is at centre + forward x d/2.

**01 inn** &mdash; ground -1.05 m. The Grey Heron. Tallest timber structure in town; upper floors jettied 0.45 m each. Gable to the square so the sign hangs over the paving. Four dormers on the east slope, two chimneys, stable yard behind.

**02 guild** &mdash; ground +0.00 m. Adventurer's Guild. Dressed stone in a plaster town, symmetrical in a town where nothing is, and it bought the best block on the market place. Forecourt raised 0.42 m on a stylobate with four steps across the full frontage. Square tower on the block's NORTH-EAST corner, footprint x[-32,-25] z[-8,-1], parapet 18.6 m, pyramid roof and iron finial to 21.5 m, crimson banners on the north and east faces. That tower is the far anchor of the arrival frame: it stands just right of the fountain at 71.5 m and closes the view west.

**03 moot** &mdash; ground +0.00 m. Moot Hall. FREE-STANDING in the market place, not on a frontage: arcaded ground floor on ten oak posts (the butter market) with the council chamber over, so the market flows under and round it. Skewed 60 degrees because it was built along the old sheep-pen rail. Louvred bell-cote on the EAST gable, 15.8 m — the left-hand anchor of the arrival frame. Stands on the upper market, one step above the fountain.

**04 store** &mdash; ground +1.15 m. General store. Widest of the three, shutters that fold down into counters, goods out over the footway. Party wall east with the apothecary.

**05 apothecary** &mdash; ground +1.15 m. Apothecary. Party walls both sides. Smallest windows, most colour behind them. Herb bundles under the eaves.

**06 tailor** &mdash; ground +1.15 m. Tailor. Party wall west; east gable is exposed to Ford Road and is the first thing seen coming up from the south gate, so it gets the painted gable and the pole sign.

**07 chophouse** &mdash; ground -1.05 m. Chophouse. North side, so its front is in shade all morning and its fire-light reads from across the square at 09:30 — that is why it is here and not on the sunny side. Set 5 m further back than it was: at z -28 its west corner stood 0.5 m off the inn's front plot line and covered 4.4 m of the Grey Heron's 7.4 m gable, so the town's second hero venue had no elevation from the market place at all (ad-town-04). Standing back also opens the plaza's north mouth, which is what WORLD_BIBLE says the market place does where the road enters.

**08 townhouse_a** &mdash; ground -1.05 m. Merchant's townhouse, shop below, hall above.

**09 townhouse_b** &mdash; ground -1.05 m. Narrow, deep and three storeys because the frontage is the most expensive in Hearthmere. 5 m wide on a 10 m plot.

**10 townhouse_c** &mdash; ground -1.05 m. The infill plot: 4.0 m of frontage squeezed between its neighbour and Ford Road's kerb, skewed 10 degrees to take up the angle, and three storeys because that was the only way up. Its east gable takes the full morning sun and carries the only painted plaster panel in town.

**11 church** &mdash; ground +0.00 m. CHURCH OF SUMMONING. Aisled hall church, ridge east-west, 14.6 m to the ridge. Great west portal 6.4 m clear x 8.0 m to the arch apex, doors standing open. Floor at +2.40, altar dais +0.90 above that. Clerestory over the arcade on both sides; lantern over the altar bay. THE ARRIVAL FRAME IS AUTHORED FROM THIS BUILDING — see docs/TOWN_PLAN.md section 7.

**12 church_tower** &mdash; ground +0.80 m. Church tower, north-west angle. Part of venue `church`. Parapet 18.4 m, lead spirelet to 21.4 m — the tallest thing in Hearthmere by 0.1 m over the guild, which the guild has never mentioned. Sited at the NORTH-west angle so its north and east faces are lit at 09:30 and it reads from the north gate and from the water.

**13 parsonage** &mdash; ground +0.88 m. The parsonage, inside the churchyard's south-east corner. Best garden in town, a lean-to glasshouse of leaded quarries against its south wall.

**14 bede_houses** &mdash; ground +0.00 m. Bede houses: six one-room almshouses under one long roof, six doors, six chimneys, no two shutters the same colour. On the Bailey under the east wall, so the old people get the morning sun over the orchard and the wall keeps the wind off their backs.

**15 song_school** &mdash; ground +0.80 m. Song school and vestry, its BACK against the churchyard's north wall and its door on the north side, onto the lane behind the rope house. It faced south until ad-town-04: the churchyard is terraced 2.40 m above this ground, so the church's own retaining parapet stood 1.1 m in front of the door and hm.townhouse.door.15 was the one unreachable door in Hearthmere. A building that is 'against' a wall has its back to it, not its face.

**16 sexton** &mdash; ground +0.80 m. Sexton's cottage. Spades and a bier under a lean-to on its west gable.

**17 lychgate** &mdash; ground +0.80 m. Lychgate in the churchyard wall at the foot of the perron. Oak, half-hipped, a coffin stool inside. Part of venue `church`.

**18 charnel** &mdash; ground +0.02 m. Charnel house, built into the churchyard's north-east angle. Barred window, no door.

**19 workshop_a** &mdash; ground +1.04 m. Workshop below, dwelling over, gable to the street. Shutters that fold down into a counter, a bench visible from the pavement, shavings in the gutter. Eaves capped at 6.6 m.

**20 townhouse_d** &mdash; ground +0.00 m. Narrow burgage plot on Ford Road's east side, gable to the road, long yard behind running to the Kirkgate boundary wall. Privy at the far end, as far from the house as the plot allows.

**21 confectioner** &mdash; ground +0.00 m. Confectioner. Gable to Kirk Green, sugar-loaf sign on an iron bracket. Second near jamb of the arrival frame; same eaves constraint as 19.

**22 townhouse_e** &mdash; ground +1.15 m. Burgage plot on Ford Road's east side, gable to the road, long garden running back to the bakery's yard wall.

**23 townhouse_f** &mdash; ground +1.15 m. Burgage plot: 6 m of frontage, 11 m deep, yard and privy behind.

**24 townhouse_g** &mdash; ground +1.15 m. Three storeys on a 6 m frontage. Sagging ridge; the middle purlin was replaced with a smaller section and it shows.

**25 cordwainer** &mdash; ground +1.62 m. Cordwainer. Boot sign, last on the bench, offcuts in the gutter.

**26 cottage_a** &mdash; ground +1.15 m. Back-plot cottage on Bell Alley, one room and a loft.

**27 cottage_b** &mdash; ground +1.62 m. Cottage on the Bailey, built ten years after its neighbour against the same party wall, so the two roofs are a course out of line and the junction is flashed with lead offcuts.

**28 shed_a** &mdash; ground +1.62 m. Back-lane shed: firewood, a handcart, a pig.

**29 cottage_c** &mdash; ground +1.15 m. Weaver's cottage on Tenter Lane, loom window on the east.

**30 cottage_d** &mdash; ground +1.62 m. Cottage with a thatched roof instead of tile - the last thatch left inside the wall, and the reason the wall-walk above it carries a leather fire bucket on a hook.

**31 shed_b** &mdash; ground +1.62 m. Tenter shed: frames, tenterhooks, a lime tub.

**32 bakery** &mdash; ground +1.15 m. Bakery. Oven-house projecting south with a 12.0 m stone flue — the second tallest chimney in town and a landmark from the south road. Flour dust on everything within 5 m.

**33 cooper** &mdash; ground +1.15 m. Cooper. Open-sided setting-up floor, a firing pit, staves stacked in cones outside. Yard to the south.

**34 carpenter** &mdash; ground +1.15 m. Carpenter and joiner. Long open front, a sawpit under a lean-to roof, timber in stick to season along the plot's south edge.

**35 chandler** &mdash; ground +1.15 m. Tallow and wax chandler. Sited at the far end of the fire lane with the prevailing wind carrying everything it renders away over the orchard and out of town. Rendering shed behind, drying racks, a smell.

**36 bowyer** &mdash; ground +1.62 m. Bowyer. Staves in the rafters, a shooting butt against the wall revetment behind, which is the only straight 30 m in the south quarter.

**37 sawshed** &mdash; ground +1.62 m. Open saw shed and timber store, three bays, no walls.

**38 waggon_shed** &mdash; ground -1.05 m. Waggon shed: five open bays, waggon poles up, a spare axle on brackets and a broken wheel leaning where it fell. Carriers turn in the yard beside it.

**39 carter** &mdash; ground +1.62 m. Carter's cottage, its door 2 m from the yard gate.

**40 gateward_s** &mdash; ground +1.62 m. Cottage on Smiths' Lane. The south gate ward lives over the gate arch, not here; this is the carter who works for him.

**41 cottage_e** &mdash; ground +1.62 m. Cottage on the Bailey, woodpile stacked to the eaves along its wall and a lean-to henhouse against the wall revetment behind.

**42 cottage_f** &mdash; ground +1.62 m. Shed and lean-to on the Bailey: iron stock under cover, a grindstone, and a cart that has not moved in a year.

**43 blacksmith** &mdash; ground +1.62 m. BLACKSMITH. Open-fronted work shed (roofed, unwalled, so the work is visible from the lane) with the forge, anvil, quench and bellows, plus a walled dwelling bay at the west end. Chimney to 11.4 m. Platform cut into the slope with a 1.1 m revetment on its north side. Highest, driest ground in the town and 30 m from the nearest thatch.

**44 smith_house** &mdash; ground +1.62 m. Cottage on the Bailey. Its garden is bigger than the house and is full of scrap iron, which the owner insists he is going to use.

**45 charcoal_store** &mdash; ground +1.62 m. Charcoal store, deliberately separate from the forge, doors on the leeward side.

**46 cottage_g** &mdash; ground +1.14 m. Cottage on the Bailey. A vine over the door, dead for two years and never cut down.

**47 cottage_h** &mdash; ground +1.62 m. Cottage with a lean-to workshop on its gable, and hens that get into the lane.

**48 byre** &mdash; ground +0.00 m. Cow house and hay loft. Two cows, and the town's milk comes from here.

**49 cottage_i** &mdash; ground +1.62 m. Cottage on Sty Lane.

**50 cottage_j** &mdash; ground +0.00 m. Cottage with a brick-nogged gable, rebuilt after a fire - the only nogging in Hearthmere, and a different colour from everything near it.

**51 cottage_k** &mdash; ground +1.62 m. Cottage skewed to the Bailey's curve, so its plot is a wedge and its back fence has a kink in it.

**52 sties** &mdash; ground +1.62 m, OUTSIDE the wall. Pig sties and a byre OUTSIDE the Cinder Tower, on the midden. Pigs and the midden belong together and both belong outside the wall.

**53 privy_row** &mdash; ground +1.62 m. A row of four privies over a common pit, emptied into the midden outside the Cinder Tower.

**54 cottage_l** &mdash; ground -1.05 m. Cottage on Ford Road's east side in the north quarter, wedged into the last gap between the road and Kirkgate. Two rooms, a loft, and a yard four paces deep.

**55 cottage_m** &mdash; ground -1.85 m. Cottage in the mill quarter, flour-dusted for four months of the year and never entirely clean of it.

**56 cottage_n** &mdash; ground -1.85 m. Cottage on Mill Lane by the north wall, its threshold two courses below the lane because the lane has been re-metalled over itself.

**57 dovecote** &mdash; ground -1.05 m. Glebe dovecote. Circular, coursed rubble, conical tiled roof to 7.6 m with a lantern. 240 nest boxes. The only round building in Hearthmere and worth the whole quarter for silhouette.

**58 tithe_barn** &mdash; ground -1.05 m. Tithe barn. Cart doors on both long sides with a threshing floor between them, so the draught blows the chaff clear. Aisled, five bays, the biggest single roof in the town after the church.

**59 warehouse_a** &mdash; ground +1.62 m. Warehouse on the Bailey: the carriers' bonded store, the oldest timber frame in Hearthmere and underpinned twice. Loading door at first floor with a gibbet beam and a block over it.

**60 netloft** &mdash; ground -1.85 m. Net loft over an open boat store. Tar barrel, floats, a half-mended net on trestles.

**61 customs** &mdash; ground -1.05 m. Customs house. Faces north-west square onto the Water Gate so nothing lands without passing its window. Stone below, timber above, a stair turret, the town's weighbeam under a canopy on its north side.

**62 warehouse_b** &mdash; ground -1.05 m. Warehouse. Grain below, wool above, both smells.

**63 warehouse_c** &mdash; ground -1.85 m. Warehouse on the Bailey in the mill quarter: grain below, wool above, both smells. Its north wall is stained to head height by the leat.

**64 fish_eatery** &mdash; ground -1.05 m. Mere-fish eatery. Six trestles under an awning, a smoking shed behind, and a queue at noon. Faces north onto Wharf Lane, so it is lit.

**65 fisher_a** &mdash; ground -1.61 m. Cottage on Sty Lane behind the tithe barn. Nets over the fence and a punt upturned on trestles: a fisherman who walks to work.

**66 fisher_b** &mdash; ground +1.62 m. Cottage on the Bailey; its gable window is a boat's transom reused, which is how you know who used to live in it.

**67 ropehouse** &mdash; ground -1.05 m. Rope house: 24 m long and 5 m wide because that is what laying rope needs. Its plan shape alone breaks the town's grain and is worth keeping exactly as drawn.

**68 cottage_o** &mdash; ground -1.05 m. Cottage on Kirkgate's west side, backing onto the Ford Road plots.

**69 cottage_p** &mdash; ground -1.84 m. Cottage on Wharf Lane, its front step dished 40 mm by two hundred years of wet boots.

**70 stables** &mdash; ground -1.05 m. Stables and waggon yard. Long range of eleven stalls with a hay loft over, tack on pegs, a mounting block at the yard gate. The yard itself is open to Ford Road and is where the carriers turn.

**71 farrier** &mdash; ground -1.05 m. Farrier's forge, small and open-fronted. A second fire in the town, sited on the lowest, wettest ground 8 m from the wall and 12 m from the river, which is exactly why it is allowed.

**72 pub** &mdash; ground -1.85 m. THE FERRYMAN'S LAMP. Floor sunken 0.55 m below Wharf Lane because the lane has been re-metalled over itself for two hundred years. Low beams, small windows, the warmest interior in Hearthmere. Its sign is the actual iron ferry lamp on a bracket; the ferry stair it used to light is through the Ferry Postern behind.

**73 gateward_n** &mdash; ground -1.85 m. North gate ward's house.

**74 cottage_q** &mdash; ground -1.05 m. Cottage on Mere Street, its wall splashed to 0.4 m by cart wheels.

**75 cottage_r** &mdash; ground +0.00 m. Cottage on Mere Street; the plot in front is a kitchen garden with a hurdle fence.

**76 shed_c** &mdash; ground -1.05 m. Handcart shed and a lean-to woodstore.

**77 watermill** &mdash; ground -1.55 m, OUTSIDE the wall. Watermill, OUTSIDE the wall on the leat. Breastshot wheel 3.6 m diameter on the north gable, axle at -2.10; leat sill -2.00, tailrace -3.30, so the head is 1.95 m and the wheel dips. Sack hoist and a lucam over the leat.

**78 granary** &mdash; ground -1.85 m. Granary on staddle stones, 0.6 m clear beneath, boarded, no ground floor at all. Part of venue `watermill`.

**79 miller** &mdash; ground -1.85 m. Miller's house. Whitest plaster in town, for obvious reasons.

**80 malthouse** &mdash; ground +0.00 m. Malt house. Kiln cowl on the ridge turning in the wind, and a floor you can smell from the lane.

**81 cottage_s** &mdash; ground -1.85 m. Cottage backing onto the stable yard.

**82 cottage_t** &mdash; ground -1.05 m. Cottage, kitchen garden, a plum tree older than the wall.

**83 cottage_u** &mdash; ground -1.05 m. Cottage on the Bailey.

**84 shed_d** &mdash; ground -1.05 m. Bailey shed: hurdles, a cart, a stack of wall-repair stone that has been there for a decade.

**85 cottage_v** &mdash; ground -1.05 m. Cottage on Mere Street's north side.

**86 cottage_w** &mdash; ground -1.05 m. Cottage, its neighbour, sharing a chimney stack.

**87 gateward_w** &mdash; ground +1.15 m. West gate ward's cottage, angled to watch the gate from its door.

**88 cottage_x** &mdash; ground +0.00 m. Cottage on Mere Street's south side, lit front, window boxes.

**89 cottage_y** &mdash; ground +0.00 m. Cottage; the party fence has been moved twice and the dispute is not over.

**90 wellhouse** &mdash; ground +1.15 m. Well-house over the town well and the conduit head that feeds the fountain. Open on all four sides, tiled pyramid roof, a windlass, a chained cup, and a stone trough the whole west quarter draws from.

**91 bathhouse** &mdash; ground +1.15 m. Bathhouse, on the conduit and next to its own spring. Furnace and a 9.0 m flue at the west end; steam out of the roof louvres on a cold morning is one of the town's best ambient reads.

**92 cottage_z** &mdash; ground +1.15 m. Cottage against the Bailey below the Spring Tower.

**93 tannery** &mdash; ground +0.35 m, OUTSIDE the wall. Tannery and dye yard, OUTSIDE the wall, downstream of the quay and downwind of everything. Pit yard of 24 lime and tan pits, drying shed with louvred sides, a bark store. The single most defensible placement in the plan: it needs running water, it stinks, and it is 90 m from the nearest occupied window with the wind blowing away from town.

**94 crane_house** &mdash; ground -1.55 m, OUTSIDE the wall. Treadwheel crane on the quay, OUTSIDE the wall. Timber tower with a slewing jib, a double treadwheel, and a stone counterweight box. Silhouette anchor of the whole waterfront.

<!-- END GENERATED schedule -->

### Open lots

Unroofed, so they do not count toward the 94, and they are half the reason the
plan reads as a town: churchyard and graveyard, glebe orchard, tenter ground,
southgate waggon yard, the Grey Heron's stable yard, the blacksmith's yard, the
midden, the wharf, the west kitchen gardens, the Kirkgate gardens, and the old
ford. Coordinates in `content/town/hearthmere.json` under `openLots`.

---

## 7. Sightlines

### 7.1 The arrival frame — from the altar, through the west door

This is the most important composition in the build (BUILD_DIRECTIVE §3.2) and
the whole east half of the plan is arranged to make it true.

| | |
| --- | --- |
| Eye | **(43.0, 4.92, −0.5)** — church floor +2.40, altar dais +0.90, eye 1.62 |
| Facing | **270°** (due west, down the nave and out through the open doors) |
| Aperture | the great west portal at `x = 32`, clear 6.4 m wide × 8.0 m to the arch apex |
| Cone half-tangent | 3.2 / 11.0 = **0.291**, i.e. ±16.2° horizontal |
| Head clearance | (10.40 − 4.92) / 11.0 = 0.498, i.e. 26.5° up |

At 09:30 the sun sits east-north-east of the town (`sunAzimuthDeg` 125 places
it at +X, −Z in the renderers), so **the player is looking away from the sun
and every facade in the frame is a lit one.** That is not a coincidence; it is
why the church is east of the market place and not west of it.

What is in the frame, near to far:

| | what | range | off axis | why it reads |
| --- | --- | --- | --- | --- |
| 1 | **The perron** — three shallow flights falling 1.60 m across the full 15 m width | 11–19 m | — | Mean slope 0.20 against a sightline slope of 0.229, so the whole flight stays visible over the threshold. Steepen it and the foreground disappears. |
| 2 | **The near jambs** — slot 19 north, slot 21 (confectioner) south, eaves capped at 6.6 m | 20–26 m | ±6 m | They crop the frame down to the street and funnel the eye. Raise their eaves and the frame closes. |
| 3 | **Kirk Green**, then **Ford Road crossing the view** | 19–37 m | — | Traffic crosses the composition at right angles: carts, a dog, someone with a yoke. Movement across a static frame is what stops it reading as a painting. |
| 4 | **The Heron Fountain** at the origin | **43.0 m** | +0.7° | The focal point, dead centre, filling roughly a quarter of the visible band. Heron spout at 2.9 m, total 4.4 m. |
| 5 | **The market cross** | 49.7 m | +9.8° left | A second vertical, half-left, keeping the middle ground from being flat. |
| 6 | **The moot hall's bell-cote**, 15.8 m, on its east gable | 53.9 m | +14.1° left | The left-hand anchor, right at the frame edge, so it reads as a framing element rather than a competitor. |
| 7 | **The Adventurer's Guild tower**, 21.5 m, crimson banners | 71.6 m | −3.2° right | The far anchor. It stands just right of the fountain and closes the view west, and it is the tallest thing in the frame at 14.7° elevation. |
| 8 | **The Grey Heron Inn**, three jettied storeys, south-east angle | 72.2 m | −14.0° right | The right-hand anchor: gables and dormers entering frame-right at 45° to the view. |

The checker proves items 4–8 lie inside the cone, under the door head, and are
not blocked by any of the other 93 masses. It will fail the build if a later
edit puts something in the way — which is exactly what would otherwise happen
the first time somebody widens a plot.

**What the player is told without a word of HUD:** there is a way down (the
steps), a way forward (the street), a place to go (the fountain and the colour
of the stalls around it), somebody to ask (the guild tower with its banners),
and somewhere to sleep (the inn).

### 7.2 The four gates

**North Gate — (−2.4, −76.0), looking south (180°).** The departure and return
frame. The arch crops the shot; Ford Road runs away uphill and slightly east;
the stable range and the waggon yard fill the left middle ground and the
Ferryman's Lamp's chimney smokes on the right. At 50 m the market place opens.
Beyond it, **two towers flank the road** — the guild's at 85 m on screen-right
(it stands west, and facing +Z screen-right is −X), the church's at 62 m on
screen-left — with the roofs of the town stepping up between them. It reads
because the road is straight for its first 50 m and then the frame is closed by
two verticals at different distances, and because you are looking *up* the
slope, so the roofs stack instead of hiding each other.

**South Gate — (+1.0, +78.5), looking north (0°).** The best whole-town view in
the build, and the returning player's frame. The ground falls 4 m away from you
over 155 m, so the town is laid out below: the fire quarter's chimneys in the
near right, the blacksmith's smoke on the left, the market place and its
awnings at 90 m, the church tower on the right at 110 m and the guild's on the
left at 80 m, and past them the north gate, the bridge, and the water meadow
beyond. It reads because of the fall — from any flat approach this is a
hedgehog of roofs; from up here it is a plan.

**West Gate — (−79, −13), looking east (90°).** Mere Street runs dead level for
70 m, which after the climb from the pastures is itself a statement. Cottage
gables step past on both sides, all of them slightly out of line. At 55 m the
street opens into the market place through a 10 m splayed mouth, and the view
is closed by the **guild tower at 51 m** with the church's roof and tower
behind it at 115 m. Screen-right is south. It reads because a level street with
a single vertical at the end of it is the oldest framing device there is, and
because the two towers overlap at slightly different heights.

**Water Gate — (+50, −57), looking south-west into the town (222°).** The
arrival by water. Through the arch: Wharf Lane, the warehouse gables stepping
away, the customs house square on to the gate so nothing lands without passing
its window — and above the roofs, at 55 m, **the church tower on the knowe.**
That is the landmark that tells a boatman he has arrived, and it is why the
tower is on the church's *north-west* angle: from the water, and from the north
gate, its north and east faces are lit at 09:30. From outside looking in (42°),
the frame is the wall rising out of the mere with the crane's jib in front of
it and the tower behind — the town's silhouette from the only direction it is
ever seen from open water.

---

## 8. What this plan does not decide

Stated so nobody assumes it was overlooked.

- **Interiors**, except that the church's is fully walkable and is the first
  thing anyone sees. Everything else is visible-through-a-door only.
- **Collision volumes.** Generators emit them per structure into
  `content/collision/<venue>.json`. The plan gives footprints, not colliders,
  and deriving one AABB per venue is banned (BUILD_DIRECTIVE §6.4).
- **Props, residue and street furniture.** The plan says where the horse trough
  and the mounting blocks *are* at the junctions that need them; everything
  else is the venue builder's, guided by the district causes in §2.
- **Vegetation and the approach ring** beyond ±96 m.
- **The stall layout** inside the market place: 14 stalls, clustered at the
  north mouth where the footfall is and thinning south, authored in the
  `stalls` venue.

## 9. Known weaknesses in this plan

- **The Bailey carries too much.** Twenty-odd cottages and sheds front a lane
  that is 332 m long and, for most of that, has the wall on one side and back
  fences on the other. It is the right kind of place, but it is where the
  placer put everything that could not fit elsewhere, and a second pass should
  move four or five of them onto short new lanes struck off Mere Street and
  Sty Lane. Right now the density is real but the *variety* of address is not.
- **Only two back alleys survive** (Bell Alley and Tenter Lane). The first
  draft had five; three were cut because they ran through the plots they were
  meant to serve. Art Bible §7 is right that alleys sell density more than main
  streets do, and Hearthmere is currently short of them.
- **The market place's south-west corner is soft.** The moot hall stands free
  in the plaza, which is correct and good, but it leaves the corner between the
  shop row and Well Lane defined by nothing but paving.
- **The east quarter between the churchyard and the wall is thin** — one row of
  plots and the Bailey. It works, but it is the part of the plan with the least
  reason for its shape.
