# Stabilisation report — Hearthmere v2

**Pass run:** 2026-08-01, 14:50–15:40.
**Scope:** first verification of the six-agent wave — `core/atlas.py`,
`circuit.py`, `props.py`, `roadnet.py`, `streetscape.py`, `vegetation.py`, and
`venues/wall.py`, `gatehouse.py`, `landscape.py`, `props_sheet.py`,
`props_situ.py`, plus in-flight edits to `core/building.py`, `roof.py`,
`materials.py`, `venues/streets.py`, `townhouse.py`. None of it had been run by
anyone.

> **The repo was being edited by another agent while this pass ran.** Between
> 15:00 and 15:28 someone else wrote `venues/church.py`, built `church.gltf`,
> and touched `client/src/main.js`, `content/town/terrain.json` and
> `venues/landscape.py`. Every measurement below is stamped with the time it was
> taken. The build/render numbers are from **15:05**, before the church landed;
> treat the "19 missing venues" figure as 18 from 15:27 onward.

---

## 1. Headline

**The wave landed and it works.** Nothing on disk is half-finished in the sense
of crashing, raising, or importing in a cycle. All sixteen venue modules build,
the town assembles, every street is walkable, and the §7 performance budget is
met with room to spare.

The town now has a **wall**, a **gatehouse and bridge**, a **landscape layer**,
a **props library** and a **real street network**. Those four questions are
answered YES, with the qualifications in §4.

The real problems are not in the new code:

1. **Eighteen venues have no generator at all** — a quarter of the town's
   authored buildings are simply absent, and until 15:27 that included the
   Church of Summoning, which is where the player spawns.
2. **Tree canopies are broken** and it is the most visible art defect in the
   build, plainly wrong from the gameplay camera.
3. **Two review instruments were lying.** `tools/render/town.mjs`'s plan and
   silhouette were framed on a 550 m box and useless; `tools/validate.py` was
   reporting every asset as 65534 m across. Both are fixed in this pass (§5).
4. Inside the wall, **the ground is still bare brown dirt.** The landscape layer
   went in outside the wall, not in the town.

---

## 2. What runs

| Command | Result | When |
| --- | --- | --- |
| `python tools/assetgen/build.py --skip-textures` | **PASS** exit 0 — 16 venues, 1,824,345 tris, 4 m 46 s | 14:52 |
| `node tools/check_walkable.mjs` | **PASS** exit 0 — 76/76 doors reachable, 15/15 streets traversable | 14:58 |
| `node tools/render/town.mjs` | **PASS** exit 0 — 13 venues placed, 19 missing, budget gate RED | 15:05 |
| `python tools/validate.py` | **DID NOT FINISH** — stalls in `check_collision`, no verdict (§5.3) | 14:57 |

No import cycles: `build.py --list` discovers all 16 modules cleanly. There is
not one `TODO`, `FIXME` or `NotImplementedError` anywhere in `tools/assetgen/`.
Determinism holds — every `.bin` this build produced is byte-identical in size
to the one the killed wave left behind, venue for venue.

### Build output (14:52)

```
  venue                 tris  cells  draws        lod0/1/2/3 draws  inst  ent vols   time
  blacksmith          11,684      4     18               18/12/9/8     0    3    7   0.41s
  cottage              9,976      4     25              25/20/10/8     0    1    8   0.29s
  gatehouse           22,426      3     14                14/8/5/4     0    6   49   4.03s
  guild               43,256      5     40               40/21/9/8     0    6   11   3.42s
  inn                 38,242      4     30              30/22/11/8     0    4    8   2.94s
  landscape          281,856    115    546         546/386/292/272  9149    7  404 162.19s
  market_square       20,348      6     23                23/9/5/5     0    3   69   3.92s
  props_sheet        161,396      4    132             132/26/12/8     0    0    1   9.32s
  props_situ          42,040      3     47               47/13/8/6     0    0   12   3.87s
  pub                 14,261      4     27              27/19/10/8     0    5    9   1.02s
  shop_row            51,672      4     43              43/25/12/8     0    6   18   3.69s
  stalls              73,850      4     41              41/19/12/8     0    8    8   4.02s
  streets             21,442     32    155           155/139/88/63     0   14  379  34.52s
  terrain            265,888      1      9                 9/9/9/9     0    0   65   5.01s
  townhouse          715,574     75    833         833/491/210/145     0   67  538  61.07s
  wall                50,434     20    142            142/69/45/38   549   24  484   7.99s
total 1,824,345 tris   draws by LOD: L0 2,125 / L1 1,288 / L2 747 / L3 606
```

`props_sheet` and `props_situ` are **review harnesses, not town venues**. Both
say so in their docstrings, both are deliberately absent from
`content/town/hearthmere.json`, and `town.mjs` assembles from that file, so they
cannot leak into a town render. Their 203 k tris are not town cost. This is
correct behaviour, not a defect.

---

## 3. Performance against the §7 budget (15:05)

| Resource | Budget | Measured | Verdict |
| --- | --- | --- | --- |
| Draw calls, gameplay camera | < 900 | **395** | **PASS**, 44% of budget |
| Triangles, gameplay camera | < 3.5 M | **1,010,862** | **PASS**, 29% of budget |
| Texture memory | < 1.5 GB | **0.842 GB** (329 PNGs, RGBA8 + mips) | **PASS**, 56% of budget |
| Shadow-casting lights | 1 sun + 8 | 1 sun | PASS |

Peak draws over all views is 1,928, but that is the orthographic **plan**
camera with distance culling off and LOD pinned to 0. The harness says so itself
and it is not a frame cost.

**Draw-call attribution, worst gameplay frame (`square`, 376 scene draws):**
townhouse 112 · landscape 110 · streets 50 · wall 33 · stalls 31 ·
market_square 21 · shop_row 10 · terrain 9.

### Mesh bytes — the number nobody has a budget for, and should

| venue | .bin |
| --- | --- |
| townhouse | **89.9 MB** |
| landscape | 36.9 MB |
| streets | 15.1 MB |
| stalls | 6.7 MB |
| terrain | 5.8 MB |
| wall | 5.5 MB |
| shop_row | 5.1 MB |
| guild | 4.2 MB |
| inn | 3.7 MB |
| gatehouse | 2.1 MB |
| market_square | 2.0 MB |
| pub | 1.4 MB |
| blacksmith | 1.1 MB |
| **town total** | **183.4 MB** |

Plus 20.2 MB of orphan/harness meshes (`cottage`, `props_sheet`, `props_situ`)
that are built every run and never placed. `validate.py` carries a 240 MB
comment as the post-quantization ceiling, so the town is inside it — but
`townhouse.bin` alone is half the town's bytes, and that is where any future
squeeze has to go.

### BUDGET GATE: **RED** — and I did not re-baseline it

```
   venue 'shop_row' went from 36 to 43 LOD0 draw calls
   venue 'streets' went from 94 to 155 LOD0 draw calls
```

`review/perf-baseline.json` was recorded with **10 venues placed**, before wall,
gatehouse and landscape existed. The two flagged venues are the same venues, so
the comparison is fair and the regression is real.

`streets` 94 → 155 is almost certainly *earned*: `core/roadnet.py`'s docstring
records that eleven of the fifteen streets had silently lost their kerbs to a
`.get(..., "cobble")` fallback, and they now have kerbs, gutters and gullies.
That is new content, not a batching bug. But it is a judgement call about cost,
and per the harness's own instruction it needs either a generator fix or a
`docs/DECISIONS.md` entry. **I have deliberately not re-baselined it** — that
would be weakening a check to make it pass. It needs the owner's decision.

---

## 4. The five questions, answered with evidence

Renders: `review/shots/town/town-plan.png`, `town-aerial-ne.png`,
`town-square.png`, `town-silhouette.png` (all re-rendered 15:20 after the
framing fix in §5.1).

### 4.1 The town WALL and GATEHOUSES — **YES, this works**

`town-aerial-ne.png` shows a continuous stone circuit ringing the town with a
wall-walk, towers, gates and posterns. **Hearthmere has an edge.** The circuit
follows the terrain rather than sitting level on it, and the crown steps in
whole courses as `venues/wall.py` says it should. The gatehouse and the
Emberflow bridge are built and legible at the north-east waterfront, with the
quay beside them. `check_walkable.mjs` reaches all three posterns
(`hm.wall.postern.mill`, `.ferry`, `.east`), so the circuit is not sealing the
town.

Cost: wall 50,434 tris / 142 L0 draws over 20 cells, 549 instances — cheap for
what it buys.

**Caveat:** the *silhouette* the wall was supposed to give the town does not yet
read. See 4.5.

### 4.2 The LANDSCAPE layer — **YES outside the wall, NO inside it**

Outside: unambiguous success. `town-aerial-ne.png` shows a hedged field system,
an orchard, a water meadow with reeds along the Emberflow, wall-foot nettles,
and a distance wood. 9,149 instanced plants over 115 cells for 281,856 source
tris. The town no longer sits on green felt.

Inside: **the bare brown dirt is not gone.** From the air the whole northern
half and the centre of the town read as one undifferentiated mud-brown surface
with buildings standing on it. The landscape layer put 6 street trees, 30 window
boxes, 18 ivy patches, 51 moss skins and 12 garden plots inside the wall — real,
but nothing like enough to cover the public ground between buildings. The
brief's question was "is the bare brown dirt inside the town gone" and the
honest answer is **no**.

Two composition tells visible from the air, both worth an owner's attention:

- The **distance wood is a perfect annulus** at a constant radius. From any
  aerial it reads as a stamped ring.
- The **field boundaries radiate as spokes** from the town centre. Real field
  systems do radiate from a settlement, so this is defensible, but combined with
  the perfect tree ring the whole outside reads as concentric.

### 4.3 The PROPS library — **YES, 63 builders, and it is good**

`core/props.py` ships **63 prop builders**, 143,080 tris across the whole
vocabulary. The contact sheet at `assets/meshes/props_sheet.gltf` proves each
one in isolation with 1.75 m figures per row; `props_situ` proves
`dress_yard` / `dress_workbench` on real falling terrain (measured 0.67 m of
fall across the yard).

Do they float or intersect? **The design is right and the evidence supports it.**
`props.py` computes lean angles against a named wall plane and stacks on the
measured top of the layer below rather than near it, and `props_situ` takes every
wall foot from `terrain.height`. Its own docstring records catching and fixing
exactly this class of bug ("the first render of this venue had three saws hanging
in open air two metres above the yard"). In `town-square.png` the market stall,
the trestle, the lamp standard and the kerb furniture all sit on the ground
correctly.

I did **not** verify every prop instance in the town individually — see the
unresolved floating masses in 4.5, which may or may not be props.

### 4.4 The STREETSCAPE / ROADNET work — **YES, this is the biggest single win**

`town-square.png` at the gameplay camera shows a granite kerb with a gutter
running out of frame, worn joint tufts in the paving, a lamp standard, and a
market stall with an awning. The streets read as built infrastructure rather
than grey stripes.

Build output confirms the model behind it:

```
15 streets, 997 m of carriageway; 10 junctions, 75 frontages, 79 doors served
surfaces: cinder x1, cobble x4, earth x3, gravel x2, mud x1, sett x3, stone x1
fall: 3 street flights, 8 cross-drains, 5 gullies
alleys: 4 dressed, 7 washing lines
furniture: 74 stations, 342 instanced props
```

Seven distinct surfaces where v1 had three with a silent fallback. Kerbs,
gutters, cross-drains and gullies exist. Frontage is computed per street.

`check_walkable.mjs`: all 15 streets **0 severed, 0 obstructed at street level**,
including Ford Road at 216 stations. The v1 defect that sealed the main street is
gone, and 32,701 m² of the 36,864 m² inside the grid is reachable (88.7%).

### 4.5 The ATLAS — **wired in, but only one venue uses it**

Registered and real: three atlas pages in `assets/textures/manifest.json` —
`kit_props` 2048 px / 16 rects, `kit_trim` 2048 px / 14 rects, `street_props`
2560 px / 18 rects. `VenueContext.material()` resolves an atlas name like any
other material, and `atlas.pack()` refuses any mesh whose UVs span more than one
tile rather than silently sampling the neighbouring rect.

**But `venues/streets.py` is the only consumer in the entire build.** Nothing
else calls `ctx.atlas()` or `pack_eligible()`. `core/props.py` claims the benefit
in its docstring ("collapses a dressed yard from eleven [materials]") but never
calls it. The building kit and the landscape layer do not pack.

What it saved: `streets.py`'s own docstring records the measurement — without
the UV-fit step, oak and iron fell out of the page in 22 and 21 cells, "which was
43 of the venue's draw calls". So roughly **43 draw calls on one venue**, and
zero everywhere else. The technique is required by §7 and is currently earning a
fraction of what it should.

### 4.6 The renders, described honestly

**`town-plan.png`** — reads as a real settlement plan. An oval walled circuit,
Ford Road running north–south through it, a market place at the centre, the
Emberflow crossing the north, the Mere opening north-east, radiating field
boundaries outside. This is the render v1 never had and it justifies the wave on
its own. Two large **empty brown quarters** are immediately visible: the Kirk
Green precinct east of the fountain (H6–J7) and Bakers' Row (H8–I8). Those are
missing generators, not layout errors.

**`town-aerial-ne.png`** — the best image in the build. The wall is legible, the
roofs are genuinely varied (orange pantile, blue-grey slate, thatch, different
pitches, jettied upper floors, chimneys), the bridge and quay work. It does not
read as a diorama. The two flaws are the brown interior ground (4.2) and the
concentric tree ring.

**`town-aerial-sw.png`** — the town holds up; the *approach terrain* does not,
and this is the view that shows it. Four defects, none of them in the wave's new
code, all of them in what surrounds it:

- **The terrain is a floating square plate.** A green diamond with hard cut edges
  and empty sky beyond. There is no distance ring past it, so from any oblique
  the whole world ends in mid-air. Directive §2 asks for a distance ring that
  "only needs to read at silhouette" and there is none.
- **The Mere blows out to pure white.** Looking toward the sun the lake is a flat
  white disc with no form at all — a specular/roughness blowout on the water
  material at the locked 09:30 rig. From the north-east it reads correctly teal,
  so it is view-dependent, not a constant.
- **The Mere is a near-perfect ellipse and the Emberflow is a straight ribbon of
  constant width** running off the plate edge at a fixed angle, sitting on the
  ground rather than in a cut channel with banks. Both read as stamped rather
  than as water that found its own level.
- **The concentric read.** The distance wood is a perfect annulus and the field
  boundaries radiate as spokes from the town centre. Either alone would pass;
  together they make the whole outside of the town read as generated.

There is also a faint regular diagonal quilting across the entire grass plate —
either terrain LOD-ring seams or a tiling artifact in the grass albedo.

**`town-square.png` (gameplay camera)** — the town holds up at eye height. Scale
reads correctly against the 1.75 m figure; doors, storey heights and eaves are
all plausible. Kerb, gutter and paving are convincing. **But the shade tree in
the middle of the frame is badly broken** (see 6.1), and it is the first thing
the eye goes to.

**`town-silhouette.png`** — now correctly framed after the §5.1 fix, and it
delivers bad news: the town's built silhouette is a **low, ragged, uniform band
of roofs with no vertical anchor whatsoever**. No guild tower reads, no church
spire, no gatehouse mass. Directive §3.2 requires the arrival frame to close on
"the guild tower, inn roofline, forge chimney, or wall gatehouse" — at silhouette
none of those are doing the work. This is the composition question the whole
wave was supposed to answer and the answer is currently no.

**Unresolved in the silhouette:** three black masses hang in clear air roughly
12–17 m above ground at world x ≈ +1, +7 and +17 (measured off
`town-silhouette.png` at 0.125 m/px against its own scale bar). They are black,
so they are not landscape. Two of them are gable-shaped and one carries what
looks like a chimney stub. If those are detached roofs it is a §6.1 violation of
the worst kind. **I could not identify the owning venue** — `town.mjs` only
floating-tests whole venue boxes, so a detached mass inside a venue is invisible
to it, and my own primitive-level probe gave garbage because the meshes are
quantized (§5.2). This needs a real per-primitive floating test. Reproduction:
`node tools/render/town.mjs --views silhouette --out review/shots/town
--allow-missing`, then crop x 740–1000, y 620–830.

---

## 5. What I fixed

### 5.1 `tools/render/town.html` — plan and silhouette were framed on a 550 m box

`LANDSCAPE = new Set(['terrain', 'water'])` predates `venues/landscape.py`. The
landscape agent added the venue and never registered it here, so its AABB — which
reaches ±270 m because of the distance wood — was unioned into `townBox`.

Consequences, all live until this pass: the plan and silhouette cameras framed a
550 m square so the 192 m town was a sliver; the silhouette was a solid black
tree line with no roofline in it; and the overlap table carried **nine phantom
`landscape × <venue>` GEOMETRY rows**, one against every building in town, each
of them a tree standing next to a house.

The file's own comment 380 lines down predicts this exactly: *"letting it into
the framing box pushed every plan and aerial out to 576 m … and made the
whole-town render useless for review."* The fix that was applied for `terrain`
was never applied to `landscape`.

**Fixed:** added `'landscape'` to the set, with a comment recording why.
Measured before → after: bounds `-269,-268 … +282,+270` → `-96,-100 … +96,+96`;
overlap table 39 rows / 15 GEOMETRY → 28 rows / **6 GEOMETRY**. The six that
remain are real signal and should be looked at: `guild × townhouse` (578 m³),
`blacksmith × townhouse` (311 m³), `gatehouse × townhouse` (104 m³),
`market_square × townhouse` (18 m³), `shop_row × townhouse` (4 m³),
`market_square × stalls` (1.6 m³).

### 5.2 `tools/validate.py` — every asset measured 65534 m across

`check_gltf` computed the asset's bounding box as the union of **every VEC3
accessor's** `min`/`max`, read raw. Two things break that:

- D-042 turned on `KHR_mesh_quantization`. POSITION is a *normalized* SHORT, so
  its accessor min/max are in [-32767, 32767] and the metres live in the node's
  `scale`/`translation`. Every mesh therefore measured **65534 × 65534 × 65534 m**.
- It also folded in NORMAL and TANGENT — unit vectors, nothing to do with size.

`MAX_VENUE_HEIGHT` is 22 m and the check is an `err()`, so a clean build was
producing **fifteen false scale errors**, one for every non-terrain mesh. That is
the fastest possible way to train everyone to ignore validate, and it is exactly
what validate's own noise policy forbids.

**Fixed:** new `mesh_bounds(doc)` helper reads the true bounds from the per-node
`extras.hm.min/max` that `core/venue.py` already writes, and falls back to
de-quantizing POSITION through its node's TRS for meshes that predate the
manifest. Verified — real metres now:

```
blacksmith  11.0 x  8.5 x  9.0      market_square  34.0 x  3.7 x 32.4
church      32.1 x 22.3 x 36.0      pub            15.6 x  8.3 x 13.6
cottage      7.9 x  7.5 x  6.5      shop_row       21.8 x 11.6 x  9.7
gatehouse   14.2 x 19.7 x 27.2      stalls         18.8 x  3.1 x 17.7
guild       28.2 x 14.3 x 14.6      streets       162.0 x  7.5 x192.7
inn         14.0 x 16.6 x 12.1      terrain       576.0 x 30.4 x576.0
landscape  551.3 x 34.9 x538.3      townhouse     150.9 x 16.7 x156.7
                                    wall          165.2 x 18.6 x161.7
```

Note `church 32.1 × 22.3 m` — that is the concurrent agent's venue, and at
22.3 m it will trip `MAX_VENUE_HEIGHT = 22.0` by 0.3 m. Someone has to decide
whether the church is allowed to be the tallest thing in town or whether the
constant moves.

### 5.3 Not fixed, needs an owner: `validate.py` stalls in `check_collision`

**This is the one command in the toolchain I cannot report a verdict for.** Three
runs, none reached the summary:

| run | mode | outcome |
| --- | --- | --- |
| 14:57 | full | still running at 36 min, never printed a verdict |
| 15:16 | `--quick` | killed by a 900 s cap, stalled after `15 street widths checked` |
| 15:29 | `--quick`, post-fix | same stall point at 4 min and counting |

All three stop at the same place, so the location is certain: `main()` runs
`check_town` → `check_street_widths` → **`check_collision`**, and `--quick` does
not skip it.

The cost is structural, not incidental. `check_collision` samples every street at
1 m stations and roughly `width / 0.25` lateral samples — about 30,000 points over
the town's 997 m of carriageway — and for **each** point calls `blocked_by()`,
which loops over all **2,049** authored collision volumes, plus `ground()`, which
loops over them four more times. That is on the order of 300 million Python-level
volume tests with no broadphase. It needs a uniform-grid or AABB bucket index over
`vols`; nothing else about the check is wrong.

Worth noting for whoever picks this up: `node tools/check_walkable.mjs` already
answers the street-traversability question — 2,049 volumes, 15 streets, every one
`0 severed / 0 obstructed` — and it finishes in seconds. `check_collision`'s
street-pinch pass is duplicating it several hundred times more slowly.

What I *can* confirm about validate post-fix, by calling `mesh_bounds()` directly
over every mesh: the dimension table is real metres again and the fifteen false
scale errors are gone.

---

## 6. What is broken, and who has to fix it

### 6.1 Tree canopies — **vegetation owner. Highest-visibility art defect in the build.**

Confirmed from two independent renders: `review/shots/town/town-square.png`
(gameplay camera, 15:05) and `review/shots/town/orchard-free.png` (eye height in
the orchard).

Symptoms:
- Canopies are **see-through**. You look straight through an oak to the sky and
  the roof behind it. Coverage is perhaps 25–35% where `core/vegetation.py`'s own
  comment sets the target at 60–75%. From the market square it reads as confetti
  or a swarm of insects, not foliage.
- **Leaf scale is wildly inconsistent.** Most leaves render as 3–8 cm specks, but
  scattered among them are leaves roughly **0.5–1.2 m long**. A one-metre apple
  leaf is a hard Art Bible §3 scale error and it is unmissable in the orchard
  shot.

Card count is **not** the cause and should not be the first thing anyone
changes. I measured it: `vegetation.tree()` gives the 12.5 m market oak 694 leaf
cards at LOD0 and a 4.8 m apple 118, which at the authored card size is a nominal
74–210% coverage. The geometry is dense; the pixels are not. So the loss is in
how each card samples the leaf atlas, not in how many cards there are.

Where to look: `core/vegetation.py` `leaf_cards()` / `_atlas_rect()`, and the
`leaf_oak` / `leaf_ash` / `leaf_apple` / `leaf_willow` builders in
`core/materials.py`. The check that settles it is to render one card of each leaf
material flat-on and confirm the sheet really is a 4×4 grid with the blade filling
0.4 × 0.9 of its cell, which is what `vegetation.py` assumes.

Second, smaller: leaves are strongly autumn-coloured (orange, brown, dark red) on
a locked 09:30 summer rig.

### 6.2 The hedge material reads as a black wall

In `orchard-free.png` the hedge behind the trees is a near-black band across the
frame. Either its normals or its albedo are wrong for the 09:30 rig. Owner:
`core/materials.py` `hedge`.

### 6.3 The three floating masses in the silhouette

See 4.5. Unidentified. Owner: needs a per-primitive floating test first —
`town.mjs`'s test is whole-venue only, which is why this survived.

### 6.4 The approach terrain ends in mid-air

See the `town-aerial-sw.png` notes in 4.6: the floating plate edge, the white
water blowout, the stamped lake and river, and the concentric wood/field read.
Owner: `venues/terrain.py` + `content/town/terrain.json` for the plate and the
water bodies, `venues/landscape.py` for the wood ring and field spokes,
`core/materials.py` for the water blowout.

### 6.5 The perf baseline is stale and the gate is red

See §3. Owner's decision: fix `streets`' batching, or record the cost in
`docs/DECISIONS.md` and re-baseline. Do not just re-baseline.

### 6.6 `venues/cottage.py` is an orphan

It builds `cottage.gltf` (0.9 MB) every run, but `cottage` is not in
`hearthmere.json`'s `venues[]`, so it is never placed. Its `CELLS` are still v1
values (`A2 B2 F2 A4 F3 F5`) on the old 96 m grid. Its job — perimeter cottages —
was taken over by the `townhouse` kit, which builds all 34 cottage slots from
`core/building.py`.

**I left it alone deliberately.** It is not half-finished and it is not breaking
anything, so deleting it to tidy the build would be exactly the "delete a module
to make the build green" move the brief rules out. But it is a second,
divergent cottage implementation competing with `core/building.py`, which is the
cohesion risk `CLAUDE.md` warns about, and someone should decide its fate.

Same class, lower priority: `inn.CELLS = ["E3","E4"]` and
`blacksmith.CELLS = ["B5","B6"]` are stale v1 grid values. The inn's slot is at
(-34, -26), which is D5/E5 on the locked 12×12 grid. `CELLS` feeds cull metadata,
so stale values mean wrong culling.

---

## 7. Building masses, and the 31 venues

### Building-mass count: **70** (target 75–95)

| source | masses |
| --- | --- |
| `townhouse` kit (63 slots, 10 party walls) | 63 |
| `inn`, `guild`, `blacksmith`, `pub` | 4 |
| `shop_row` (store, apothecary, tailor) | 3 |
| **total inside the wall** | **70** |

Plus the gatehouse and 11 wall towers, which are masses but not buildings.
`hearthmere.json` authors **94 building slots**, so 24 authored masses are not
being built. Building all 94 would land at the top of the 75–95 target.

### Venues with NO generator — 18 at 15:05, **17 from 15:27**

`bakery` · `bathhouse` · `bowyer` · `carpenter` · `chandler` · `chophouse` ·
~~`church`~~ *(landed 15:27, another agent)* · `confectioner` · `cooper` ·
`dovecote` · `fish_eatery` · `moot_hall` · `quay` · `stables` · `tannery` ·
`warehouse` · `watermill` · `wellhouse`

Every one of these is listed in `hearthmere.json`'s `venues[]`, so `town.mjs`
404s on each and prints `MESH FAILED TO LOAD`, and `check_walkable.mjs` reports
each as *"has no collision file — treated as walk-through."* The town in every
render has holes in it exactly where these should stand.

The 24 unbuilt slots behind them:

```
03 moot        07 chophouse   12 church_tower 17 lychgate    21 confectioner
32 bakery      33 cooper      34 carpenter    35 chandler    36 bowyer
38 waggon_shed 57 dovecote    61 customs      62 warehouse_b 64 fish_eatery
70 stables     71 farrier     77 watermill    78 granary     90 wellhouse
91 bathhouse   93 tannery     94 crane_house  11 church (now building)
```

Ranked by what they cost the build:

1. **`church`** — the spawn point and the most important composition in the
   build. *Being written now by another agent.* Slots 12 (tower, 18.4 m) and 17
   (lychgate) go with it, and the tower is one of the two vertical anchors the
   silhouette is missing.
2. **`moot_hall`** — free-standing in the market place with a 15.8 m bell-cote;
   the left-hand anchor of the arrival frame. Its absence is why the square
   reads as an empty parade ground.
3. **`quay`** (slots 61, 94) — the customs house and crane house. The waterfront
   is the town's whole economic reason to exist and it is currently a bare bank.
4. **`stables`** (38, 70), **`watermill`** (77, 78), **`tannery`**,
   **`bathhouse`**, **`wellhouse`** — two slots each in some cases, and all on
   visible frontages.
5. The Bakers' Row trades — **`bakery`, `cooper`, `carpenter`, `chandler`,
   `bowyer`, `confectioner`, `chophouse`, `fish_eatery`, `dovecote`,
   `warehouse`** — these are the ones leaving the large empty brown quarters in
   the plan render.

---

## 8. State of the tree, as I leave it

Two files changed, both review instruments, both strengthened not weakened:

- `tools/render/town.html` — `LANDSCAPE` set now includes `'landscape'`.
- `tools/validate.py` — new `mesh_bounds()`; `check_gltf` uses it.

Nothing in `tools/assetgen/` was touched. No module was deleted, no check was
relaxed, no baseline was rewritten.

Renders regenerated at 15:20 into `review/shots/town/`: `town-plan.png`,
`town-aerial-ne.png`, `town-aerial-sw.png`, `town-square.png`,
`town-silhouette.png`. The silhouette and plan in that directory are the first
correctly-framed ones the project has had.
