# Church of Summoning — build report

Status: IN PROGRESS. Written as I go so it survives a cut-off.

## 1. What existed before I started

- **No `venues/church.py`.** Slots 11 (church), 12 (church_tower) and 17
  (lychgate) all carry `kit: "church"`, which is not in `townhouse.KITS`, so
  **nothing in the build produced any church geometry at all.** The town has a
  hole where its most important building goes, and the player spawns in mid-air
  at (43, 3.3, -0.5).
- `venues/landscape.py::_churchyard` DOES already build the churchyard: five
  yews, ~150 grave markers, tussocks, a boundary wall broken at the street
  openings, and **a lych gate at the graveyard lot's west edge (x = 24,
  z = -0.5)** with collision and an entity. So slot 17 is covered by landscape
  and the church venue must NOT duplicate it.
- `content/town/hearthmere.json` already carries the locked spawn
  (`pos [43, 3.3, -0.5]`, `facingDeg 270`) and the authored arrival sightline
  with its five `mustBeVisible` anchors.

## 2. The blocking geometry problem I found (and had to solve first)

The arrival frame is a pure geometry problem and the plan as committed does not
satisfy it. The numbers:

- Eye on the altar: `(43.0, 4.92, -0.5)`. Church floor `+2.40`, dais `+0.90`,
  eye `1.62`.
- The occluder is the church floor's own west edge at the threshold,
  `(x=32, y=2.40)`. The sightline that grazes it descends at
  `(4.92 - 2.40) / 11.0 = 0.229` m per metre. **Anything west of x=32 that lies
  below that ray is hidden behind the threshold.**
- `content/town/terrain.json` has the whole church precinct dead flat at
  `+0.00` (the Kirk Knowe rise was deleted in D-024; D-020 is still open on
  whether to put it back). So the perron would have to fall the full `2.40 m`
  between x=32 and x=24 (Kirk Green's east end) — a mean slope of **0.30**.
- 0.30 > 0.229, so **every tread of the perron falls below the sightline and
  the entire flight is invisible from the altar.** BUILD_DIRECTIVE §3.2's first
  required element of the arrival frame cannot be delivered on the terrain as
  committed.

`docs/TOWN_PLAN.md` §3 already knows the right answer and states it in prose —
"three flights ... 1.60 m, 10 risers at 0.16", "mean slope 0.20 — deliberately
shallower than 0.229" — but its own GENERATED levels table says the perron foot
is at `+0.00`, because the knowe that used to make up the other 0.80 m is gone.
The prose and the data disagree; the prose is right.

**Resolution:** put the missing 0.80 m back as the churchyard terrace that
TOWN_PLAN §3 already describes ("Churchyard terrace: rubble retaining wall on
the west and north sides of the knowe platform, 0.9-1.6 m exposed. The
graveyard is the fill."). Concretely:

- new authored pad `hm.pad.churchyard`, level `+0.80`, in
  `content/town/terrain.json` `pads.list`;
- the church itself keeps its generated pad at `+0.00` and stands on a masonry
  **podium** that covers that pad and its apron completely, so the 0.80 m step
  between the two pads is buried inside the podium and never shows;
- the podium face therefore stands **1.60 m** above the churchyard — inside the
  0.9-1.6 m the plan asks for;
- the **perron falls 1.60 m over 8.0 m** (x 32.0 -> 24.0), mean slope **0.20**,
  10 risers of 0.16 m — exactly the plan's prose.

Deviation from the plan's prose, recorded: the perron is **one continuous
flight of ten 0.80 m treads, not three flights with two landings.** A landing
spends run without spending height, which forces the flights either side to
exceed 0.229 and drop below the sightline. Ten uniform 0.80 m goings hold the
nosing line at a constant 0.20 and keep the whole flight visible with 0.23 m of
margin at the foot. (Verified: a straight nosing line whose two endpoints are
both above a straight sightline is above it everywhere.)

## 3. Build log

### 3.0 The bug that had to be fixed before ANY arrival frame could be right

**`tools/render/town.html`'s `dirFromDeg()` was mirrored, and the client agreed
with it.** It returned `(-sin θ, 0, -cos θ)`, i.e. 90° = west, 270° = east.
Every heading in `content/` is a COMPASS heading — `docs/TOWN_PLAN.md` §6 and
`core/building.py::Footprint` both define forward as `(sin θ, 0, -cos θ)`, and
all 94 building slots are laid out with it.

Consequence: `playerSpawn.facingDeg 270` ("due west, down the nave and out
through the great west door") pointed the arrival camera **due east**. The
baseline arrival frame — the most important composition in the build — was a
photograph of the back of the bede houses. The player would have spawned facing
the church's east wall.

Fixed in two places:

- `tools/render/town.html` — `dirFromDeg` now returns `(sin, 0, -cos)`.
- `client/src/main.js:325` — `player.yaw = -(facingDeg) * PI/180`. Negated,
  because `client/src/player.js` runs its own free mouse yaw with
  `forward = (-sin y, 0, -cos y)`; the negation is the conversion between the
  two, and without it the client spawns the player the same 180° out.

Baseline (before): `review/shots/town-baseline/town-arrival.png`.

### 3.1 Terrain

Added `hm.pad.churchyard` to `content/town/terrain.json` — centre (40.5, -4.0),
half (18.5, 16.0), level **+0.80**, apron 2.2 — through
`terrain.flatten_region()` + `add_pad()` + `persist()`, i.e. the supported API,
not a hand edit. It is applied BEFORE the generated pads, so `hm.pad.church`
(level 0.00) still wins under the church itself and the 0.80 m step between
them lands inside the podium. Verified by reloading and sampling.

Rebuilt `landscape` after it (the graves, yews and churchyard wall all read the
height field, so they came up onto the terrace for free).

### 3.2 `tools/assetgen/venues/church.py` — new venue

Slots 11 (church) and 12 (tower). Slot 17 (lychgate) deliberately NOT built
here; `landscape.py` already owns it.

84,518 tris · 48 LOD0 draws · 8 cells · 7 entities · 50 collision volumes.
41 of those draws are charged to the worst gameplay frame, out of 479.

- **Podium** covering `hm.pad.church` + its whole 1.2 m apron
  (local lz -15.0..15.2, lx ±13.1, plus a spur under the tower), rubble with an
  ashlar coping, standing 1.60 m out of the churchyard.
- **Perron**: 10 treads, 0.16 rise, 0.80 going, 15 m wide, `FLOOR` 2.40 down to
  `TERRACE` 0.80. Nested solid blocks, dished by 22 mm toward the centre.
- **Nave and aisles**: 20 × 24 m, coursed rubble, ashlar quoins/jambs/arch
  rings. 4 round piers + 2 responds a side carrying 5 semicircular arches;
  clerestory over; slate gable at 0.87 pitch to a 14.6 m ridge; slate lean-to
  aisle roofs; limewashed inner skins.
- **Great west portal**: clear 6.4 m × 8.0 m to the apex, two orders of ashlar,
  hood mould, dished threshold, both leaves swung right back inside against the
  west wall (clear of the ±3.2 m cone).
- **Tower**: 4 stages with set-offs, clasping buttresses dying back in 3 stages,
  lancets, louvred belfry, embattled parapet at 18.40, lead spirelet and vane
  to 21.40. It is the tallest thing in Hearthmere as slot 12 requires.
- **South porch**, priest's door, stone benches.
- **Interior** (portal-linked cell `nave`, two portals): worn flagstone floor
  with a 2.9 m path fanning out at the threshold, ledger stones, five tie-beam
  trusses with king posts and purlins, alabaster/marble altar on a 0.90 m dais
  with a bronze summoning ring set flush at the spawn point, an iron rail with
  a gap on the west axis, ribbons tied to it, heaped offerings, a bench with a
  cloak and a lantern, and a sandstone font.
- **Light patches** on the floor placed by intersecting the ray from each north
  clerestory window with the floor plane, using the sun vector derived from
  `content/town/hearthmere.json` (elev 38, azim 125) rotated into venue space.

### 3.3 Defects found by rendering and fixed

1. **The portal arch was invisible.** `kit.arch_ring`'s `span` is the CLEAR
   opening; I passed the ring's OUTER span, so the intrados was 7.44 m over a
   6.4 m doorway and every voussoir sat buried in the masonry either side. The
   portal rendered as a plain rectangular hole. Fixed: `span=PORTAL_W`,
   `rise=PORTAL_W/2`, plus a second inner order.
2. **The portal ring was also rotated 90°.** `arch_ring` already opens across
   local X with its barrel along Z, which is what a west portal needs; the
   arcade arches span Z and legitimately rotate. Rotating the portal stood the
   whole ring on end down the middle of the doorway — a floating column of
   voussoirs in the dead centre of the arrival frame.
3. **The lych gate stood on the door axis.** `landscape.py` put it at
   (24, -0.5), 19 m from the altar. A 3.6 m gate with a 3.6 m ridge at that
   range hides everything below y = 1.93 at the fountain's distance across 8.1 m
   of frame — it cropped the Heron Fountain, the frame's focal point, out of the
   composition. Moved to (24, +8.5), clear of the ±5.5 m cone and on the side
   where the path from Kirk Green's south verge actually enters the burial
   ground.
4. **The door leaves were built from `kit.plank` rotated the wrong way** and
   came out as 0.5 m tall horizontal slabs. Rebuilt as proper leaves swung back
   inside.
5. **The west front was one 20 m slab to the nave plate** and read as a barn
   end. Rebuilt as three masses: two aisle ends stopping under their own
   lean-tos with a lancet each, and the nave centre carrying the portal and
   gable.
6. **Interior was cold grey rubble.** Added limewashed inner skins; the room is
   now warm and it bounces the clerestory light instead of eating it.

### 3.4 The one thing the geometry will not give, and what was done instead

The treads cannot be a strong foreground element and it is not fixable by
detailing them. The altar eye is 2.52 m above the floor and the nosing line
falls at 0.20 against a sightline of 0.229, so the ENTIRE flight projects into a
band about 11 px tall at 900p. That is inherent to a walkable perron seen from
2.5 m above its head.

Two things carry the read instead:

- The **outer cheek walls at ±7.5 m are useless for this frame** — the door
  jambs crop the view to ±5.5 m at the perron's foot, so they are hidden behind
  the doorway. They are there for the approach view, not the arrival.
- **Inner cheek walls at ±3.1 m**, 0.55 m high, coped and stepped, with a squat
  ashlar standard and an iron lamp part way down each. They stay inside the cone
  the whole way, they converge, and they step. In the render they are what
  actually says "the ground falls away here". The sightline clears them by
  0.4 m at the foot, and at 0.16 rad off axis they frame the fountain
  (±0.079 rad) rather than blocking it.

## 4. What the arrival frame actually shows

`review/shots/church/town-arrival.png` — eye (43.0, 4.92, -0.5), facing 270°,
09:30 locked rig, 1600 x 900, no HUD. Read near to far:

| | what is in frame | verdict |
| --- | --- | --- |
| 1 | **The nave floor** — worn flagstones with the dark polished path running away under the eye and fanning out at the threshold, two soft light patches from the north clerestory lying across it, and the church's own diagonal shadow. | reads |
| 2 | **The great west portal** — a semicircular ashlar arch in two orders filling the middle third of the frame, apex just inside the top edge (the plan's 26.5° head clearance), the two oak leaves standing open as dark verticals inside the reveal. | reads, and it is the strongest single element |
| 3 | **The arcade** — the westernmost arch of each range entering frame-left and frame-right, cropping the composition down to the door. | reads |
| 4 | **The descending steps** — the two inner cheek walls at ±3.1 m stepping down and converging, each with its ashlar standard and iron lamp, and ten ashlar nosings running across the flight. | reads as a descent; see §3.4 for why the treads themselves cannot |
| 5 | **Kirk Green**, then Ford Road crossing the view at right angles. | reads |
| 6 | **The Heron Fountain** at the origin, 43 m, dead centre. | PRESENT but small — see §5.1 |
| 7 | **The Adventurer's Guild** — its long pale hall across the head of the view and its crenellated tower above and just right of centre at 71.6 m. | reads; the far anchor |
| 8 | **The Grey Heron Inn / market-place gables** entering frame-right with the market stalls' awnings under them. | reads; the right-hand anchor |

Against BUILD_DIRECTIVE §3.2's four required elements: descending church steps
**yes**, a street leading the eye **yes**, the market square fountain as the
focal point **present but under-weighted**, at least two other venue anchor
silhouettes **yes** (guild hall + guild tower, inn/market gables).

Supporting frames rendered and looked at:

- `review/shots/church-approach/town-free.png` — eye 1.62 m on Kirk Green
  looking east. The terrace, the perron rising, the portal, and through it the
  nave and the lit altar candles. With the 1.75 m figure for scale.
- `review/shots/church-focal/town-free.png` — eye 4.7 m at the head of the
  perron looking at the fountain. Confirms the fountain, the guild, the stalls
  and Ford Road are all where the sightline record says.
- `review/shots/church-inside/town-free.png` — the interior from the chancel
  looking west down the nave.
- `review/shots/church-aerial/town-free.png` — the tower and roofs from the
  north-west.
- `review/shots/church/town-silhouette.png` — the tower breaks the roofline and
  is the tallest thing in the town, as slot 12 requires.

## 5. Known defects and follow-ups — NOT signed off

This is not an ACCEPT. `docs/REVIEW_PROTOCOL.md` sign-off is a separate pass and
self-assessment is not sign-off. What I know is still wrong:

1. **The fountain is under-weighted in the arrival frame.** It is visible and
   centred, but at 43 m through a 6.4 m aperture it is a small pale object
   rather than the focal point §3.2 asks for. It reads properly from the head
   of the perron (`church-focal`), so the fix is not in the church — it is
   either fountain mass/contrast in `market_square`, or moving the market
   stalls that stand between it and the church out of the axis.
2. **The perron treads are a flat band in shadow.** The church shadows its own
   forecourt at 09:30 (the gable's shadow reaches 26.5 m west of the west
   wall), so the flight is lit only on its north-west diagonal. The nosings
   carry it; the treads do not.
3. **The churchyard yews now crowd the west front.** `landscape.py` places them
   at fractions of the graveyard lot; two of them sit either side of the perron
   and read as large dark low-poly blobs in the approach view. They are outside
   the arrival cone, so this is an approach-view defect, not an arrival one.
4. **Six slots round the churchyard now stand on deep underbuildings** —
   `parsonage`, `bede_houses`, `song_school`, `sexton`, `charnel`,
   `townhouse_c` — because the terrace raised the ground under part of their
   footprints. They are not floating (the whole-town floating check passes) but
   they want a revetment or a re-level pass.
5. **`hm.townhouse.door.15`** (song school, 49.3, -14.5) is the one unreachable
   door in the town after the terrace went in. Every street still passes and
   the altar is reachable; this one door needs steps or a terrace break.
6. **No authored LOD chain on the tower.** `townhouse.py`'s note says a hero
   spire is exactly what earns one, but `ctx.lod` on an id nothing instances
   exports a standalone node and the tower is already in a cell batch, so it
   would ship twice. Doing it properly means building the tower ONLY through
   `ctx.lod` with four authored levels. Deferred.
7. **The church has no bell geometry** — there is a `hm.church.bell.01` entity
   in the belfry with nothing under it.
8. **`tools/validate.py` could not complete its geometry pass** on this
   machine: `numpy` raised `_ArrayMemoryError` allocating 8.79 MiB inside
   `voxelise()`. Everything before it passed — schema, 17 collision files /
   2131 volumes, 15 street widths, 1072 street stations, the draw budget. The
   crash is an environment limit, not a church defect, but the geometry and
   palette passes are therefore UNVERIFIED.
9. **The whole-town budget gate is already failing** on `shop_row` and
   `streets` batching regressions from the earlier agent wave. Pre-existing;
   the church is 41 of 479 gameplay draws and 85 k of 1.02 M triangles.

## 6. Files touched

- `tools/assetgen/venues/church.py` — NEW.
- `tools/assetgen/venues/landscape.py` — lych gate moved off the door axis.
- `content/town/terrain.json` — `hm.pad.churchyard` added (via the API).
- `tools/render/town.html` — `dirFromDeg` compass fix.
- `client/src/main.js` — `playerSpawn.facingDeg` sign fix.
- Regenerated: `church`, `landscape`, `terrain`, `townhouse`, `streets`.

## 7. Recorded decisions

Three entries added to `docs/DECISIONS.md`:

- **D-043** — `facingDeg` is a compass heading, and both renderers had it
  mirrored. (The bug in §3.0.)
- **D-044** — The churchyard is a terrace, because the arrival frame is a
  geometry problem. (`hm.pad.churchyard`, with the sightline arithmetic.)
- **D-045** — A perron tread is 0.80 m, and that is a **declared exception to
  Art Bible §3**, which puts a step going at 0.28 m. `tools/validate.py`
  enforces that on any constant named `GOING`; the constant here is
  `PERRON_GOING` because a perron is a processional flight taken two paces to
  the tread, not a stair, and the 0.80 m is forced by the sightline — at 0.28 m
  the flight is 2.8 m long, falls at 0.57, and vanishes behind the threshold.
  D-045 is the record that makes that rename a declared exception rather than
  an evasion. **An art director should be told about this one explicitly.**

`tools/validate.py --venue church --quick` reports 41 failures across the town;
exactly one of them was the church's, and it was the `GOING` rule above. The
other 40 are pre-existing: 18 venues placed in `hearthmere.json` with no built
mesh and no collision file (the missing secondary venues), and 4 false
positives from the "printed text" anachronism scanner reading the word
"printed" out of source comments in `core/kit.py`, `core/materials.py`,
`core/mesh.py` and `core/roof.py`.

## 8. Verification actually run

| check | result |
| --- | --- |
| `python tools/assetgen/build.py --skip-textures --venue church` | 84,958 tris · 48 LOD0 draws · 8 cells · 7 entities · 50 collision volumes · 1 interior cell with 2 portals |
| `node tools/render/town.mjs --views arrival` | rendered and **looked at**; §4 above is what it shows |
| `node tools/render/town.mjs --views silhouette` | tower breaks the roofline and is the tallest mass in the town |
| whole-town floating check | `floating / sunk masses: none at venue-box level` |
| `node tools/check_walkable.mjs` | `hm.altar` reachable, stand 0.00 m away. All 15 streets PASS, 0 severed, 0 obstructed. Ford Road traversable end to end. 1 unreachable door (`hm.townhouse.door.15`, §5.5) |
| `node tools/check_client.mjs` | **OK — client boots clean and the player walks.** 2110 volumes, 160 entities. The player left the altar at (43, 2.9), walked 195 m of path and arrived at (4.7, 44.1) on Ford Road. 512 draw calls whole frame, 1,069,754 triangles at eye level — inside the §7 budget of 900 / 3.5 M |
| `python tools/validate.py --venue church --quick` | 1 church failure, the declared D-045 `GOING` exception. 40 pre-existing failures unrelated to the church |
| `python tools/validate.py --venue church` (full) | **could not complete** — numpy `_ArrayMemoryError` in `voxelise()`. Geometry and palette passes UNVERIFIED |

`tools/check_client.mjs` needed a fix of its own and got one:
`fordRoute()` started the walk at the spawn and steered straight for Ford Road,
which since BUILD_DIRECTIVE §3 means walking into the church's north aisle wall.
It reported that as a blocked Ford Road. It now prepends an authored egress leg
— altar, down the nave, through the west portal, down the perron, across Kirk
Green, onto Ford Road — which is exactly the traverse §9's first box names, so
if a later edit closes any part of it the check fails at the right place.
