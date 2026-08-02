# Art-director review — Hearthmere, whole town, pass 02

**Verdict: REJECT.**

Reviewed 2026-08-01 against `docs/ART_BIBLE.md` §8, `docs/BUILD_DIRECTIVE.md` §3
(arrival), §6 (structure) and §9 (done). All images rendered by me at the locked
09:30 rig into `review/shots/ad-town-02/` and read as PNGs. I did not review from
source and I did not take either build agent's self-assessment.

Frames read: `t-plan`, `t-aerial-ne`, `t-aerial-sw`, `t-aerial-nw`, `t-aerial-se`,
`t-arrival`, `t-square`, `t-silhouette`, `t-gate-north`, `t-gate-south`,
`spine-walk-01..10` (bridge → north gate → Ford Road → square → south gate),
`wharf-walk-01..07` (Wharf Lane → water gate → wharf), `kirk-walk-01..06`
(Kirk Green → church west front → Kirkgate), `lanes-walk-01..08` (Bell Alley →
Smiths' Lane → Sty Lane → Bakers' Row), `westfront-free`.

---

## The verdict, stated plainly

Blind, side by side against Divinity's Reach, Gridania, Ul'dah and post-Legion
Boralus, **no frame in this build would be mistaken for a shipped AAA MMO.** Two
or three would pass as a competent greybox with a first texture pass on it. The
half-timbered street frames (`spine-walk-02`) and the north gate (`t-gate-north`)
have real quality in their massing and are the proof that the kit *can* get
there. Everything around them is unfinished, and several of the systems that
would carry the town — foliage, water, ground, roofs, atmosphere — are not
merely unpolished, they are producing artefacts that read as bugs.

The two prior reports are broadly honest about their own scope and both
substantially overstate the state of the world outside it. Specifically:

- STABILIZE: "wall + gatehouse **yes** — the town has an edge and the bridge/quay
  work." **The quay does not exist.** `quay.gltf` is one of eighteen venue meshes
  that fail to load. `wharf-walk-06` at (55.8, −59.7), which is the authored
  wharf deck, is bare brown dirt and a single plank jetty. No customs house, no
  crane, no boats, no nets, no warehouses.
- CHURCH: "the arrival frame works." It resolves — the axis is right, the portal
  is real, the perron reads — and that is a genuine achievement over a mirrored
  camera. But the *content* inside the aperture does not carry it, and the
  reverse of the same composition (`kirk-walk-01`, the church seen from Kirk
  Green, which every player will look at ten seconds after spawning) is the
  single worst frame in the build.

---

## The three questions asked, answered directly

**(a) The arrival frame from the altar.** *Structurally yes, pictorially no.*
`t-arrival` is a real composition for the first time: the axis is correct, the
two-order portal arch is the strongest element in the frame, the arcade crops
left and right, the perron cheek walls step down and lead the eye, and the guild
tower's crenellation appears top-right. That is genuine progress and CHURCH
earned it. But the aperture is only ~35 % of the frame width, so two thirds of
the image is interior masonry in a crazy-paving texture (§9); the object at the
optical centre of the aperture is a **blank cream guild gable**, because the
three venues that should occupy that middle distance do not exist (§1); the
fountain the directive names as the focal point is 19 pixels tall (§6); the
canopy at frame-left is multicoloured confetti (§2); and with no fog the far
buildings sit in the same value band as the piers 2 m away (§5), so the frame is
flat. It reads as a well-composed shot of an unfinished set.

**(b) The silhouette.** *No.* Neither the wall nor the church tower has given
Hearthmere a skyline. `t-silhouette` is a 6 m ragged strip with no vertical
hierarchy; the church tower reads as a **detached floating mass** with no visible
stem to the ground; four further unidentified masses float 8–15 m up; and the
wall's towers stand only 2.6 m proud of a 6.3 m curtain, so from any aerial the
enceinte reads as a low grey ribbon. Full detail at §7.

**(c) Cohesion.** *It reads as several agents' separate work bolted together,
and I can name the seams.* One continuous run of town wall changes masonry
material three times in a single frame (§10). One green mottle texture is doing
wall infill, hedges and ground cover (§14). Ford Road is properly paved with
kerbs and gutters while Sty Lane two hundred metres away has no road surface at
all (§17). The `rubble` crazy-paving is doing duty as both church walling and
market paving (§9). Roofs are an even scatter of saturated orange with no
clustering logic (§21). And the three things that would knit it all into one
world — atmosphere, ambient occlusion, and a coherent ground treatment — are
absent everywhere (§5, §11, §13). The individual pieces are not the problem; the
absence of any shared environmental layer over the top of them is.

---

## Findings, ordered by how much they damage the frame

### 1. Eighteen of thirty-two venues do not exist, including a hero

`review/shots/ad-town-02/t-report.json` → `missing[]`. Missing:
`quay` (**hero**), `moot_hall`, `chophouse`, `confectioner`, `bakery`, `cooper`,
`carpenter`, `chandler`, `bowyer`, `stables` (×2 slots), `dovecote`,
`warehouse`, `fish_eatery`, `watermill`, `wellhouse`, `bathhouse`, `tannery`.

Fourteen venues are placed. This is not a polish problem — it is the reason the
town reads as a doughnut of houses round a hole. In `t-plan` and `t-aerial-ne`
the entire east side (Bakers' Row, Sty Lane), the entire waterfront, and the
whole intramural ring are bare brown ground where those eighteen masses belong.
`t-arrival` looks through the church door at a composition whose middle distance
is *supposed* to contain the moot hall, the confectioner and the bakery; it
contains nothing, so the eye lands on a blank guild gable.

**Fix.** Nothing else on this list changes the verdict until this is closed. The
kit already builds houses convincingly; these are mostly one generator each
against `docs/TOWN_PLAN.md`'s slot table. Build `quay` first — it is a hero, it
owns the town's stated identity as a lake town at a ford, and its absence leaves
the largest single dead area in the build.

### 2. The leaf atlas is arithmetically incapable of making a tree

`tools/assetgen/core/materials.py:3789` `leaf_atlas()`. I read
`assets/textures/leaf_oak_albedo.png` directly. Two defects, both fatal:

- **Four of the sixteen leaves are baked bright orange in the albedo.** A card
  that maps the full 4×4 sheet — which `vegetation._atlas_rect` chooses 72 % of
  the time (`tools/assetgen/core/vegetation.py:114`) — therefore draws 25 %
  autumn leaves *on every card in every tree*. This is why every canopy in the
  build is multicoloured confetti at 09:30 in high summer (`t-square`,
  `t-arrival`, `spine-walk-02`). There is no parameter that turns it off; the
  season is painted into the texture.
- **Opaque coverage is roughly 12–14 % of the sheet.** Each leaf is a narrow
  blade in a 256 px cell. At `CARD_M = 1.05` (`vegetation.py:74`) one card paints
  ~0.13 m² of leaf for 2 triangles and a full quad's worth of overdraw. The 694
  cards STABILIZE measured on the market oak therefore paint ~90 m² of leaf
  through a crown of ~110 m³. That cannot be opaque at any card count the budget
  allows. Card count is not the cause and adding cards is not the fix.
- Third-order: the petiole is clipped by the top edge of every cell, so the 2×2
  sub-rect cards (28 % of them) draw severed stalks with no leaf attached —
  those are the loose brown sticks visible in every canopy.

**Fix.** Regenerate the atlas: (a) drive autumn share from a per-card *vertex
colour or material tint*, not the albedo — ship the sheet all green; (b) raise
opaque coverage to ≥ 45 % by drawing a **sprig of 3–5 leaves per cell** rather
than one blade, which is what every shipped foliage atlas does and is the only
way the card economics work; (c) keep the petiole inside its cell.

### 3. The yew is a 28-face polyhedron and it is standing on both flanks of the church

`tools/assetgen/core/vegetation.py:88–91` — `"yew": dict(leaf="hedge", card=0.0)`
routes the yew to `blob_canopy()` at `vegetation.py:279`, whose default is
`rings=4, segments=7`. That is a 28-facet lathe. At the ~9 m diameter the
churchyard yews are placed at, each facet is 3–4 m across.

In `kirk-walk-01` these are two enormous flat dark-green angular slabs occupying
the left and right thirds of the frame, hard-edged against the sky, with three
loose stick branches poking out of them. They read as painted scenery flats.
They also crop both aisles off the church. The same `blob_canopy` builds the
distance wood, which is the row of faceted green crystals across the Mere in
`wharf-walk-06`.

**Fix.** `blob_canopy` is correct as an LOD2/LOD3 mass and wrong as anything a
player stands under. Give the yew a real card canopy on a needle atlas (or reuse
`leaf_ash` darkened); raise `blob_canopy`'s defaults to `rings=7, segments=16`
and displace the vertices before smoothing so it is never a readable polyhedron;
and gate it so LOD0 within 40 m never uses it.

### 4. Thatch is a smooth cream membrane with a knife-edge

`lanes-walk-02`, `lanes-walk-03`, and every white roof in `t-aerial-ne` /
`t-aerial-sw`. The thatched roofs are untextured pale cream planes with zero
surface, no straw direction, no rolled ridge, and eaves that terminate at zero
thickness. They read as canvas stretched over rafters — tents, not buildings.
From the air they read as *missing material*, which is worse.

`tools/assetgen/core/kit.py:863` `thatch_roof()` authors `thickness=0.38` and a
rolled eaves, and `tools/assetgen/core/materials.py:979` / `:3971` author a
directional straw texture, so the geometry and the texture both exist. What is
arriving on screen has neither. Either the kit path is not the one
`core/roof.py` takes for the townhouse/cottage kit (see `roof.py:56 THATCH_T`
and the note at `roof.py:134` about the coat depth being 0.31 m short), or the
material key is falling through to a default. **Diagnose this first** — it is a
wiring failure, not an authoring one, and it is disfiguring roughly a third of
the roofs in the town.

### 5. There is no fog, haze or aerial perspective anywhere

Confirmed by grep: neither `tools/render/town.html` (lighting block,
lines 129–181) nor `client/src/main.js` (lines 36–83) sets `scene.fog`.

Consequence, visible in every single frame: the far treeline in `wharf-walk-06`
is exactly as saturated and as contrasty as the mud at the player's feet; the
distant roofs in `t-arrival` sit in the same value band as the church piers 2 m
away; the town has no depth and no atmosphere. This is the cheapest large
quality win available and every reference title in the brief has it.

**Fix.** `scene.fog = new THREE.FogExp2(<sky horizon colour>, ~0.0035)` in both
files, driven from `lighting` in `content/town/hearthmere.json` so the client and
the harness cannot disagree. Add a horizon value ramp to the sky shader while
you are in there — the sky is currently a flat two-stop gradient with no cloud
and no sun disc.

### 6. The Heron Fountain is 0.90 m tall and is required to be the focal point at 43 m

`tools/assetgen/venues/market_square.py:113` `_fountain()`. Its collision note at
`:208` states "solid to its sitting lip at 0.90 m". In `t-square` it is a low
circular kerb with a small pale stub in it — no water reading, no heron, no
vertical element at all.

`BUILD_DIRECTIVE.md` §3.2 makes this object the focal point of the mandated
arrival composition. From the altar it is 43 m away. A 0.90 m object at 43 m
subtends 1.2°, which in a 55° FOV at 1600×900 is **19 pixels**. It is
geometrically impossible for it to hold that composition, and in `t-arrival` it
does not — the object my eye actually lands on at the centre of the aperture is
a market stall.

CHURCH's report calls this "present and centred but under-weighted… the fix is
in `market_square`/`stalls`, not the church." Correct diagnosis, and it is the
single highest-value change available to the arrival frame.

**Fix.** Give the fountain the vertical it needs: a carved shaft or a crocketed
canopy over the basin, 4.5–6.0 m to the finial, with the heron on top. That is
also historically the right answer — a market fountain of this date usually
*is* a cross or a canopied conduit. It will read at 43 m, it will read in
silhouette, and it will give the market place the anchor it currently lacks.

### 7. The town has no skyline. The wall and the church tower have not given it one

`t-silhouette`, read at 8 px/m.

- The built mass is a **6-metre-tall ragged strip**. Almost the entire town sits
  in one narrow height band with no hierarchy.
- The church tower reads as a **detached floating mass**: black from y≈618 to
  y≈665, then nothing until the town line at y≈740. There is no visible stem
  connecting the tallest object in Hearthmere to the ground.
- Four further unattached masses float 8–15 m up at x≈800, 855, 925 and 1350.
  These are the ones STABILIZE flagged and nobody has identified. Note that
  `landscape.gltf` measures **y ∈ [−5.90, +29.03]** in `t-report.json` — 7 m
  taller than the church spirelet. The tallest thing in the town is something
  unidentified inside the landscape venue.
- The distance ring behind is a **uniform sawtooth** of near-identical
  triangular peaks at constant amplitude and frequency. In a silhouette test
  that is the dominant read and it announces "procedural noise ridge".

Against the wall specifically: `content/town/hearthmere.json` authors
`walkHeight 5.2 + parapet 1.1 = 6.3 m` with eleven towers at 8.9–11.5 m. The
towers therefore stand **2.6 m proud of the curtain**, which is why in
`t-aerial-ne` and `lanes-walk-02` they do not read as towers at all and the wall
reads as a low grey ribbon. Divinity's Reach and Ul'dah put their walls at
15–25 m for exactly this reason.

**Fix.** Curtain to 8.5–9.0 m; towers to 14–16 m and give them roofs; put the
church tower's stem into the silhouette (it is being occluded or LOD'd out —
`t-report.json` shows no authored LOD chain on it); find and delete the four
floating masses; break the distance ridge into two or three distinct massifs
with real amplitude variation and put the fog from §5 behind them.

### 8. The Mere is a stamped ellipse, the Emberflow is a straight-sided rectangle, and the water blows out to white

`t-aerial-sw`: the Mere is a **pure white specular blowout** across the entire
north-east, with a hard-edged elliptical shoreline. `t-plan`: the Emberflow is a
literal straight-sided rectangular canal with parallel banks. `t-gate-north`: the
river is a flat opaque teal plane — no depth gradient, no transparency, no
transmission, no foam at the bridge cutwaters, no flow — meeting a bank that is
a **hard sawtooth of flat triangles**. `wharf-walk-06`: the far shore is a
constant-width beige strip, like a bathtub rim.

`content/town/hearthmere.json` → `water.bodies` uses `channel`/`basin` primitives
that are producing analytic shapes. A lake town whose lake is an aluminium disc
does not read as a lake town.

**Fix.** Perturb the water body outlines with low-frequency noise and let the
shoreline interpenetrate the terrain instead of being clipped to it; drop
roughness variation and a depth-tinted transmission into the water material so
the specular does not clip to 1.0; add a wet-line, reeds and shingle at the
margin; give the Emberflow a curved thalweg and asymmetric banks (cut bank
outside the bend, point bar inside).

### 9. `rubble` is crazy paving with green mortar, and it is the most-seen surface in the arrival frame

`tools/assetgen/core/materials.py:1932` `rubble_weathered()`. I read
`assets/textures/rubble_albedo.png` directly:

- The pattern is **random Voronoi polygons with no bedding whatsoever**. Real
  rubble walling is laid to rough courses; this is crazy paving. On the church
  piers and the town wall it reads as a garden path turned on its side.
- Every stone is **the same value**. There is jitter in the shape and none in the
  albedo, so beyond ~4 m the whole surface flattens to one grey. Art Bible §8
  requires variation from at least two noise sources; there is one.
- **The mortar joints are green.** Over an entire wall this puts a green cast on
  the church, the perron cheeks, the podium and the town wall.

This material covers roughly 60 % of the pixels in `t-arrival` — the piers, the
arcade, the reveals — and most of `kirk-walk-01`.

**Fix.** Quantise cell centres into horizontal bands of 0.18–0.28 m with
jittered break joints so the wall is coursed; spread stone albedo by at least
±18 % value with a second low-frequency mask so bands of stone read as different
lifts; desaturate the mortar to a warm grey and let moss be a separate, *local*
mask driven by ground proximity and rain shadow, not a global joint colour.

### 10. Three different masonry materials along one continuous run of town wall

`t-gate-north`. From left to right in a single frame: the curtain west of the
gate is a **smooth putty-beige stucco** with no coursing or joints at all; the
drum towers are a **blocky ashlar**; the wall east of the gate is the **crazy
paving** of §9. The wall is the town's longest continuous object and it changes
material three times in one shot. This is the clearest single instance of the
cohesion failure the brief asks about — it does not read as one world because it
was not one decision.

**Fix.** One masonry family for the whole enceinte, with the ashlar reserved for
dressings — quoins, arch orders, copings, string courses — exactly as the church
already does it. `tools/assetgen/venues/wall.py` and `gatehouse.py` need to agree
a single key.

### 11. Everything inside the wall is bare brown dirt

`t-plan`, `t-aerial-ne`, `t-aerial-sw`. Between the buildings, in the whole
15–20 m intramural ring, and across most of the built area, the ground is a
uniform brown mud. There is essentially no green inside the walls: no gardens,
no yards, no verges, no trees except the two market ones. The town reads as a
construction site with houses parked on it.

`venues/landscape.py` has `_gardens`, `_kitchen_garden`, `_back_yard`,
`_town_greens` and `_building_dressing`, so the intent is there. It is either
not being reached inside the wall or its output is invisible under the default
ground material. STABILIZE's "landscape **yes** outside the wall, **no** inside
it" is correct and this is the most damaging half of that split.

**Fix.** Author the intramural ground as a *blend*, not a material: trodden earth
within 1.5 m of a door or a road edge, weed and nettle against every wall base,
rough grass in the open ring, mud only where carts actually turn. This is one
pass over `_town_greens` and the ground shader and it changes every aerial and
every street frame in the build.

### 12. The church west front is a blank box with a hole in it, and the nave is a black tunnel

`kirk-walk-01`, from Kirk Green looking east — the frame every player will look
at within seconds of walking out of the spawn.

- **No tower appears in the frame at all.** Measured: the west front is at
  x = 32, the camera at x = 13.5 on the door axis (z = −0.5), and the tower
  centre is at (35.8, −14.3) per `docs/TOWN_PLAN.md` slot 12. That is 13.8 m
  off-axis at 22 m range = **32° from centre**, outside the 27.5° half-FOV of
  the gameplay camera. The tallest mass in Hearthmere is sited such that it
  cannot be seen from the frontal approach to its own church — and what would
  have caught a corner of it is occluded by the yew of §3 anyway. The tower needs
  to move onto or nearer the axis, or the approach needs to be angled to catch
  it.
- The west front is a rectangular block with a single round-arched opening and
  **eight metres of dead blank wall above it**. No west window, no wheel, no
  hood mould, no gable, no niches, no string course. A church front like this is
  architecturally impossible and reads as unbuilt.
- Through the arch the nave is a **black void**. The clerestory light shafts
  `BUILD_DIRECTIVE` §3.1 calls for as hero-tier treatment are not arriving; the
  interior reads as a tunnel with a lit altar at the far end.
- The perron is buried behind two blank ashlar pylons; of the 15 m wide, ten-riser
  processional flight the plan promises, roughly a 4 m slot is visible.

**Fix.** A west window is the entire fix for the elevation — it is the element
the composition is missing and it will also solve the black nave by putting
light down the axis. Reduce the perron cheek walls to a balustrade or step them
down with the flight so the treads read. Confirm the tower's LOD chain (it has
none) is not culling it.

### 13. No ambient occlusion or contact shadowing anywhere; shadows are 21 px/m

In every eye-height frame the base of every wall meets the ground with no
darkening, the eaves and the jetty undersides in `spine-walk-02` are as bright as
the sunlit gable above them, and the 1.75 m reference figure has no contact
shadow in any frame — in `lanes-walk-02` and `wharf-walk-06` it reads as hovering.
This is the largest single reason the whole build looks like assembled parts
rather than a place: nothing is bedded into anything.

Shadow map is `4096²` over a 192 m town (`town.html:176`, `main.js:83`) = 21 px/m,
which is why every shadow edge in `t-arrival` and `t-square` is visibly
stair-stepped.

**Fix.** SSAO (or baked vertex AO at generation time, which ports cleanly to
Unreal/Unity) plus cascaded shadow maps with the first cascade tight around the
player. Both are renderer-side, both are cheap, both lift every frame.

### 14. One green mottle texture is doing wall infill, hedges, and ground cover

`spine-walk-02` right-hand building and `lanes-walk-02` right-hand building: the
**wattle-and-daub panels between the timbers are bright lichen green**, and it is
visibly the same texture as the ground vegetation 3 m below and the hedge behind.
Daub is limewashed — off-white or ochre. A wall of moss reads as a bug.

### 15. A hedge is standing in Kirkgate and it swallows the camera

`kirk-walk-03`, at (26.1, −14.7) — on Kirkgate, inside the town, on the route
from the church to the market. **The top two-thirds of the frame is the inside
of a dark green mass.** The 1.75 m reference figure is cut off at the knees by
it: only its legs render. A player walking this street walks into a wall of
green.

The texture is `hedge` stretched into long directional streaks, which places it
as `V.hedge_run` from `venues/landscape.py:388` `_boundary()`. `_open_runs`
(`landscape.py:350`) exists precisely to stop a hedge growing across a road, so
either this run is not being tested against Kirkgate's path or its `pad` is too
small for the hedge's actual half-width.

Note that `tools/check_walkable.mjs` reports **15/15 streets clear, 0
obstructed**. Both readings cannot be right. Either the checker does not see
hedges, or the hedge has no collider — in which case the player *walks through*
a solid-looking hedge, which is the worse of the two.

**Fix.** Widen the road keep-out in `_open_runs` to the hedge's built half-width
plus 0.4 m, and make `check_walkable` test against emitted geometry rather than
authored colliders so a non-colliding obstruction cannot pass.

### 16. Large black unlit polygons, in at least three separate frames

`lanes-walk-02`: a black wedge at ground level between the buildings plus a black
roof plane behind it. `lanes-walk-06`: a large black angular mass filling the
top-right quarter of the frame. `t-plan`: three pure-black masses over the church
precinct at H5/H6, I5 and H7. `t-arrival`: two near-black vertical slabs in the
arcade.

Three unrelated locations means this is systemic, not one bad prop — inverted
winding, a material key falling through to an unlit default, or portal-cell
interiors being drawn from outside. It is visible from the street in normal play
and it should be treated as a build-blocking bug, not a dressing note.

### 17. Near-field LOD is crude at ~25 m, and the lanes lose their road surface

`lanes-walk-06`: buildings at roughly 25 m (frame-left, behind the drying racks)
have already dropped to featureless grey slabs with no fenestration, while
buildings at 15 m are fully detailed. `BUILD_DIRECTIVE` §7 puts the first LOD
switch at 15 m and the second at 40 m; what is on screen looks like LOD2 arriving
around 25 m. Pull the switch distances out to where the geometry actually stops
paying, and give LOD1 keeps its window reveals.

Same frame: **Sty Lane has no road surface.** It is bare brown mud with a broken
line of stone slab decals lying on it, where Ford Road two hundred metres away is
properly paved with kerbs and gutters. The roadnet is surfacing the primary
streets and abandoning the lanes. A back lane should be a different surface, not
an absent one.

### 18. Cloth and ivy are flat single-sided quads

`lanes-walk-06`: the washing lines — which are otherwise the best residue in the
build and exactly what Art Bible §7 asks for — hang **hard-edged rectangles with
no drape, no sag, no fold and no thickness**. They read as coloured paper. Two of
the five are saturated orange, out of palette.

Right of the same frame, the ivy on the wall is a **flat rectangular decal** with
a visible straight top and bottom edge, applied like paint rather than growing
from a root with a broken margin.

**Fix.** Both are cheap: give the cloth a two-segment catenary sag and a slight
V-fold at the line, and cut the ivy panel's silhouette with an alpha mask that
breaks the rectangle and lets a few sprigs stand off the wall.

### 19. Landscape spends 83 % of the town's triangles on the worst-looking thing in it

`t-report.json`: `landscape` is **1,508,214 of 3,323,216 scene triangles**. What
it buys is the faceted crystal wood of §3, the stamped water margin of §8, and
the field pattern below. That ratio is indefensible and it is where the LOD and
impostor work should go first.

The fields themselves (`venues/landscape.py:1175` `_fields`) lay their hedge
boundaries out in a **radial-and-concentric polar pattern centred on the town**.
In `t-plan` and both aerials this reads as a spiderweb of black slashes over flat
green — instantly procedural, and not how field systems work. They should be
rectilinear strips hung off the roads and irregular closes off the lanes.

### 20. Composition defects in two of the three hero review cameras

- `t-square`: a lamp standard stands ~4 m dead centre of the camera axis,
  bisecting the frame from top to bottom and cropping the fountain. Measured off
  the frame it is ≥ 3.7 m tall against `streetscape.lamp_post`'s authored 2.65 m
  (`core/streetscape.py:242`) — worth checking, but the composition is the
  finding: move the camera or move the lamp.
- `t-gate-north`: the "departure and return hero frame" is shot from off-axis and
  low over the water, so the bridge parapet fills the right half as a
  featureless slab and the gate arch is squeezed into a ~90 px gap. Put this
  camera on the bridge centreline at eye height.
- `spine-walk-01` (bridge crown) and `westfront-free` (perron) both put the eye
  **inside geometry**. The walk/free cameras take their Y from
  `terrain.height()` and know nothing about authored decks and floors, so they
  stand under the bridge deck and inside the church podium. `check_walkable`
  passes, so this is a harness fault — but it means no bridge or perron frame has
  ever actually been reviewed.

### 21. Roof material distribution reads as a checkerboard

`t-plan`: roughly 55–60 roofs, of which the great majority are one **saturated
orange terracotta**, scattered evenly among pale (see §4) and a handful of
saturated blue. There is no clustering logic — no sense that one street re-roofed
after a fire, or that the poor quarter is thatched and the merchants' slated. A
real town's roofscape has runs and blocks. Also: I count ~60 masses against
`BUILD_DIRECTIVE` §5's target of **75–95**, and the eighteen missing venues are
most of the gap.

---

## The three changes that buy the most quality per unit of work

**1. Fog and a sky. (§5)** Two lines in `town.html` and `main.js`, driven from
`content/town/hearthmere.json`'s lighting block, plus a horizon ramp in the sky
shader. It costs an afternoon and it changes *every frame in the build* — it is
the single largest gap between these images and the reference titles, it hides
the distance-ring problem, and it makes the silhouette read.

**2. Regenerate the leaf atlas and retire `blob_canopy` from LOD0. (§2, §3)**
One texture function and two constants. Every tree, hedge, orchard, verge and
churchyard in Hearthmere is currently broken by the same two decisions — orange
baked into the albedo and 13 % opaque coverage. Fixing them fixes the green of
the entire world in one pass, including the two yews that are wrecking the church
approach.

**3. Put a vertical on the fountain. (§6)** One generator,
`market_square._fountain`. It is the only change that can make
`BUILD_DIRECTIVE` §3.2's mandated arrival composition actually resolve, it gives
the market place the anchor it has never had, and it puts a second element into
the silhouette. Cheapest possible fix for the most important frame in the build.

*Close fourth, and the biggest win that is not cheap:* green the intramural
ground (§11). It transforms every aerial and every street frame, but it is a
week, not a day.

---

## What the next wave should build, ranked

1. **The eighteen missing venues, `quay` first.** Nothing else moves the verdict.
   Order: `quay` → `warehouse` → `moot_hall` → `bakery`/`cooper`/`carpenter`/
   `chandler`/`bowyer` (Bakers' Row and Sty Lane as a block) → `stables` →
   `watermill` → the rest. §1.
2. **Vegetation rebuild.** Leaf atlas, yew, `blob_canopy` LOD gating, hedge
   volume, and a real distance-wood impostor to reclaim the 1.5 M triangles. §2,
   §3, §16.
3. **Ground and material cohesion.** One masonry family for the wall; coursed
   `rubble`; the intramural ground blend; daub off the moss texture; a single
   roof-material logic with runs and blocks; surface the back lanes. §9, §10,
   §11, §14, §17, §21.
4. **Water.** Shoreline noise, depth-tinted transmission, roughness variation to
   kill the blowout, wet-line and reeds at the margin, a real thalweg on the
   Emberflow. §8.
5. **Atmosphere and lighting.** Fog, sky, AO, cascaded shadows. §5, §13. *(Do the
   fog line itself immediately — it does not need to wait for this slot.)*
6. **Skyline.** Curtain to 8.5–9 m, towers to 14–16 m with roofs, the church
   tower's stem and LOD chain, delete the four floating masses, break the
   distance ridge. §7.
7. **The church west front.** West window, perron cheeks reduced, clerestory
   light reaching the nave floor, and the tower moved onto the approach axis so
   it is visible from its own churchyard. §12.
8. **Thatch.** Diagnose why `kit.thatch_roof`'s 0.38 m coat and the straw texture
   are not arriving on screen. §4.
9. **Residue pass** (Art Bible §7): washing lines, window boxes, woodpiles,
    hanging signs, crates, boot scrapers, vines. Sty Lane shows the pass working;
    Ford Road and the market place have almost none of it. Give the cloth and the
    ivy real drape and a broken silhouette while you are there. §18.
10. **Correctness sweep.** Find and kill the black unlit polygons (§16); get the
    hedge out of Kirkgate and make `check_walkable` able to see it (§15); pull
    the LOD switch distances out (§17).
11. **Harness truth.** Put the review cameras on authored floor levels rather
    than `terrain.height()`, and fix the `square` and `gate-north` compositions.
    §20.

---

## Budget, for the record

`t-report.json`, worst gameplay frame: **550 draw calls / 900**,
**1,050,673 triangles / 3.5 M**. Inside budget with room. The perf gate fails
against `review/perf-baseline.json` on `streets` (94 → 155 LOD0 draws) and
`shop_row` (36 → 43) — batching regressions, still unowned, still not
re-baselined. Not a blocker for this review; the budget is not what is wrong
with these frames.
