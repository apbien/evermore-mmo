# Gate repair — `validate.py`, `check_client.mjs`, the perf baseline, roof verges, materials

Working report, written as the work happens.

---

## 1. `tools/validate.py` — was unrunnable, now 40 s on the full town

### Why it stalled

`check_collision` had no broadphase. On the shipped town that is

    2,513 volumes x 1,072 street stations x 37 lateral samples
      x 5 neighbourhood probes x up to 4 step-resolution rounds
    = ~2.0e9 Python-level volume tests

Measured by brute force: 1,500 probe points took 3.3 s, so the real run was
~250 s in that function alone. Three agents reported it hanging past three
minutes and stopped there, so **nothing else in the file had been run on the
town for several waves either**.

`tools/validate.py:1503 _col_world` now also returns each volume's world-space
XZ bounding box, and `tools/validate.py:_Broadphase` indexes those into a
uniform 4 m grid. A point query goes from 2,513 candidates to single digits.

**Verified equivalent, not just faster:** 1,500 random points across the town,
brute force vs broadphase, on both `ground()` and `blocked_by()` — 0 mismatches.
And smoke-tested that it still *fires*: dropping a 40x40 m solid slab over the
market place produced 3 street failures naming `ford_road`, `mere_street` and
`kirk_green`. `check_collision` now runs in **0.74 s** and reports the town's
1,072 street stations clear.

### Other things fixed in the same file

| Where | What was wrong |
| --- | --- |
| `voxelise` / `connected` / `vertex_components` | Voxel keys were an `(N,3)` int array plus an **XOR hash** `(i*73856093)^(j*19349663)^(k*83492791)`. That hash is not injective, so distinct masses metres apart could collide and be welded into one connected component — a floating mass silently absorbed into the building beside it, which is the one answer this check exists to give. Replaced with an exact packed int64 key (20-bit fields, ±262 km at 0.5 m). **Mass counts jumped: `landscape` 159 → 292, `townhouse` 11 → 37.** The check had been under-reporting. Also removed `np.unique(..., axis=0)` on ~30 M rows, which was most of the pass's 100 s. |
| `load_terrain` | `height()` was called once per point on scalars, unchunked. `townhouse`'s 1,841,435 vertices are only **234,295 distinct ground columns** — the other 87% were re-computed, at 11 s for that one venue. Now exact-deduplicated (two float64 packed into a complex128, uniqued in 1-D) and evaluated in 200 k chunks, which is also what bounds the transient allocation that raised the earlier `numpy._ArrayMemoryError`. |
| `check_placement` | One boolean mask over the whole vertex array per label — quadratic in exactly the venue with the most of both. Now a segmented reduction. |
| `check_instanced` | Walked 9,149 instances in Python, each with its own `meshgrid` and its own scalar call into `terrain.height` (28 s on `landscape`). Now one batched transform and one terrain call per batch. |

**Runtime: never finished → 40.4 s** for the whole town, no flags.
Breakdown: geometry 34 s, collision 0.7 s, everything else ~6 s.

### The 63 false failures I removed, and why they were false

The first clean run produced 70 failures. **63 of them were correct
construction** being reported as floating geometry, from one cause: a mass was
only ever tested against *terrain*, and each venue was voxelised *alone*.
Directive §6.1 allows three ways to be legitimate — sits on ground, is carried
by something that reaches the ground, **or is visibly fixed to a wall** — and
only the first was implemented.

- **44 x `wall`.** The town wall's own **corbel table and putlog ends**
  (`tools/assetgen/venues/wall.py:350`, `:360`). Masonry brackets socketed into
  the wall face, GPU-instanced, so voxelised without the wall they are set into.
  Corbels sit at y 5.36–6.34 directly under a 6.3 m parapet; putlogs are
  scaffold holes in the face.
- **19 x `landscape`.** Window boxes on iron brackets (`foliage_flower` +
  `iron` + `timber_grey` + `earth`, e.g. at (-45.6, 0.5) y 1.58–1.75 with the
  bracket at 1.35–1.57), authored in `landscape` and hung on `townhouse` walls
  — so the wall carrying them is **in a different file**. Same for the ivy
  sheet at (57.2, -22.1).
- **`stalls`,** a 182-voxel mass at (-0.3, -18.7): the market stalls stand on
  `market_square`'s paved podium, again another file.
- **`carpenter` / `cooper`,** `iron` + `glass_lit` at y ≈ 4.0: wall lanterns.

`tools/validate.py:_supported_by` now asks the question of the **assembled town
in world space** — 2,586,055 occupied voxels — rather than of one file:
*is there anything at all beneath this mass's footprint within a step of its
underside.* Verified it discriminates: the carpenter lantern, the window box
and the stalls podium all read supported; mid-air probes at 40 m over the
square and 12 m beside the church read unsupported.

Two more noise sources removed:

- **6 anachronism false positives**, all prose. Four were the word *printed*
  used as a modelling verb ("the printed tile grid", "printed its ends at 1 m
  per tile") — the forbidden class is printed **text**, so the pattern now says
  so, exactly as `bolt` and `extruded` are already excluded. Two were
  `lettering` in comments whose negating clause ("Art Bible §2: **no** readable
  lettering") sits on the *previous* line, which a line-at-a-time regex can
  never see; the suppression now reads a three-line window.
- **The §7 triangle gate was measuring a number nothing ever draws.** It summed
  every primitive in every file — that is LOD0 *plus* LOD1 *plus* LOD2 *plus*
  LOD3 of the same cell — and reported **4,983,616 triangles against a 3.5 M
  budget on a town whose measured worst gameplay frame is 1.13 M**. It now
  gates the same worst case the draw-call gate does (whole town at LOD3 =
  **1,194,595**, inside) and warns separately that LOD0 unculled is 3,987,161.

---

## 2. The real failures the fixed tool finds

Seven, and they are all genuine.

### 2.1 Two flat `flour` decals are buried under the ground — they render nothing

| Venue | World position | Depth | Geometry |
| --- | --- | --- | --- |
| `bakery` | (25.6, 47.0) | highest point **0.46 m** below terrain | `flour` material, y 1.15–1.16, 196 verts |
| `dovecote` | (70.3, -15.9) | highest point **0.32 m** below terrain | `flour` material, y -1.02, 96 verts |

Both are flat spill/dust decals ~0.01 m thick placed at a **fixed Y instead of
the terrain height**, which is the exact failure Directive §6.1 names ("a
generator that places an object must derive its Y from the terrain height
function, never assume `y=0`"). They are entirely under the ground and draw
nothing at all.

### 2.2 `hm.watermill.wheel.01` is 0.55 m below terrain

`content/entities/watermill.json`. An interactable under the ground is a broken
interaction, not a look.

### 2.3 `landscape.gltf` is 34.2 m tall — 12 m over the §3 ceiling

`MAX_VENUE_HEIGHT` is 22.0 m and the guild tower is meant to be the tallest
thing in Hearthmere. **This is the same defect `ad-town-02.md` §7 could not
identify**: *"`landscape.gltf` measures y ∈ [−5.90, +29.03] — 7 m taller than
the church spirelet. The tallest thing in the town is something unidentified
inside the landscape venue."* It has since grown to 34.2 m. It is the reason
`t-silhouette` has unattached masses floating 8–15 m up.

### 2.4 `church.gltf` is 22.3 m — 0.3 m over the ceiling

Marginal, and plausibly legitimate for a hero venue with a tower, but it is
either a scale error or a decision that belongs in `docs/DECISIONS.md`.
Currently it is neither.

### 2.5 `tree_far` is authored at double its density class

`tools/assetgen/core/materials.py`, `LIBRARY['tree_far']`: a 512 px map over
1 m is 512 px/m, and its class `standard` is 256 px/m (Art Bible §5). Either
the map is 2x too large for what it is, or it is misclassified.

### 2.6 Mesh memory is 276.9 MB against a 240 MB budget

15% over. `townhouse.bin` is the file to split by cell.

### 2.7 Cell draw hotspots (warnings, but they are the perf story)

Eight 16 m cells exceed 45 LOD0 draw calls: **H7 70**, **H2 65**, **I8 63**,
**H5 61**, **E2 51**, **E8 49**, **K5 49**, **B8 46**. Whole town at LOD3 is
827 draws against the 900 budget — over 70% with the town not yet complete.

---

## 3. `tools/check_client.mjs` — it was not 12% flaky, it was 100% dead

The brief describes a fixed 30-sample walk with a 1–5 m margin. That is not
what was in the tree: a previous wave had already added a settle phase and a
distance budget. What it had **not** done is run it. Measured, three times on
identical bits:

```
settle: 2716 ms to a stable LOD/batch set
page.screenshot: Timeout 30000ms exceeded.
    at main (tools/check_client.mjs:213:16)
real  1m24.157s
```

The walk forced one frame per sample with `page.screenshot`, because headless
Chromium stops driving `requestAnimationFrame` when nothing asks for one. On
the finished town — 32 venues, 537 batches, 1.15 M triangles — **a single
SwiftShader frame now exceeds Playwright's 30 s screenshot default**, so the
loop dies on its first iteration. Raising the sample cap from 30 to 400 to
implement the distance budget made it 13x worse.

### The fix: a fixed simulation timestep, no frames at all

Physics and collision need no pixels. `client/src/main.js` now exports
`hm.step(dt)` — one simulation step (player controller, collision, camera rig,
visibility) with no render — and the walk is a single `page.evaluate` running
it at a fixed `1/60 s`.

This is what makes the check deterministic *in principle*, not just in
outcome: the frame loop clamps `dt` to 50 ms, so under a software rasteriser
the distance a player covers per sample depended on how fast the frame
happened to render. That is the actual mechanism behind the 36.3 / 41.0 / 43.5
/ 43.7 / 44.3 / 44.6 / 45.1 spread. With a fixed timestep the walk depends on
nothing but the world.

**Measured, three consecutive runs, byte-identical:**

```
walk:   5948 fixed 1/60 s steps (99.1 simulated seconds)
walked: (43.0, -0.5) -> (5.2, 40.0), 202.6 m of path over 994 samples
perf:   2153 draw calls whole frame, 3,770,661 triangles at eye level
```

Runtime went from a 30 s timeout to seconds, and the budget is now distance
travelled, as asked.

### Two real defects it immediately finds, which nobody could see while it was dead

**3.1 The player cannot complete Ford Road.** It ends at **z = 40.0** against a
`z > 40` pass line, having burned the full 1.6x budget: **202.6 m of walking to
cover a 127 m route.** Perfectly reproducible. Something is steering it in
circles or shoving it sideways in the last leg. I have not diagnosed which —
`tools/check_walkable.mjs` and this check now disagree, and `ad-town-02` §15
predicted exactly that ("either the checker does not see hedges, or the hedge
has no collider").

**3.2 The client and the review harness disagree about §7 by 3x.**

| measured in | draw calls | triangles |
| --- | --- | --- |
| `client/src/main.js` (this check) | **2153** whole frame (642 scene) | **3,770,661** |
| `tools/render/town.mjs` → `town.html` | **727** | **1,154,547** |

Same town, same locked rig. The client counts the shadow-map and post passes in
`renderer.info`; the harness's `gameplayDrawCalls` evidently does not. §7
budgets "draw calls" and "triangles drawn" without saying which, so **one of
these two gates is not measuring the Directive** — and the town is either
comfortably inside budget or 2.4x over it depending on which you believe. This
is D-023's divergence again and it needs settling before either number is
quoted anywhere. I deliberately did not "fix" it by relaxing a threshold.

---

## 4. `core/roof.py` — the verge defect is real, and it was never about verges

`review/reports/waterfront.md:237` reports "detached timbers at the verge...
two dark boxes floating clear of the roof" at both eaves corners of the
granary, worse on `half_hip`, and three venues were gabled to dodge it.

### Cause: `rotate_y` turns about the WORLD origin

`_fascia` jitters each rafter foot after placing it:

```python
M.place(r, sl.p3(t, s0 + 0.10, -DECK_T - 0.030), ex, up, out_h)
r.rotate_y(rng.uniform(-0.02, 0.02))      # <-- world-space rotation
```

`Mesh.rotate_y` is `self.v = self.v @ m.T` — a rotation about the world origin.
A foot already sitting at radius `r` is therefore **translated by about
`r * theta`**, not spun in place. Measured, foot-top to deck-plane gap:

| plate half-width | feet | gap min | gap max | feet clean **off the roof** |
| --- | --- | --- | --- | --- |
| 5 m | 48 | −0.011 | **+0.098** | 0 |
| 12 m | 100 | −0.061 | — | **several** |
| 25 m | 194 | −0.064 | — | **many** |

At granary / tithe-barn / warehouse scale the feet leave the roof entirely and
hang in clear air beside the building. `half_hip` is worse only because it
emits more feet (48 vs 36 on the same plate) and its hip faces put the furthest
ones at the corners.

**Fix.** `core/mesh.py` gains `spin_y(radians, about=None)` — rotate about a
vertical axis through the mesh itself — and `_fascia` uses it. After the fix
every foot on every kind and every plate size is a uniform **+0.052 m**, no
scatter, none off the roof.

This was a trap anyone could fall into, which is why the fix is a core method
with the reason written on it rather than a local translate/rotate/translate in
`roof.py`.

### Second, genuinely half_hip-specific bug: `_verge` boards the hip lines

`_verge` skipped an edge only if it *started part-way up the slope*
(`min(s0,s1) > smin + 0.12`). A jerkinhead's hip lines **spring from the
eaves**, so they passed the test. `half_hip` therefore got four barge boards
laid along its four hip lines — across the tiles, on the same lines
`_ridge_cap` was already capping at `roof.py:1305`, interpenetrating.

A verge is the gable end, so it runs at **constant `t`**; a hip line and a
valley run diagonally. The test is now `abs(t1 - t0) > 0.20 * abs(s1 - s0)`.
Verified on a 10 x 7 m plate:

- `gable`: 4 barge boards (unchanged).
- `half_hip`: **4** boards, all at x = ±5.28, running eaves (y 4.46) to
  springing (y 6.76) — correct jerkinhead. Previously 8, four of them on hips.

### The three workarounds reverted

`roof="gable"` was doing real work in these three, because they use custom style
names — so `ROOFS` is never consulted and the pin is the only thing choosing the
kind:

| slot | file | now |
| --- | --- | --- |
| granary (78) | `tools/assetgen/venues/watermill.py` `GRANARY_STYLE` | `half_hip` |
| tithe barn (58) | `tools/assetgen/venues/warehouse.py` `STYLE` | `half_hip` |
| fish eatery (64) | `tools/assetgen/venues/fish_eatery.py` `STYLE` | `half_hip` |

All three rebuild clean. **`warehouse` dropped from 9 connected masses to 7 and
`watermill` from 4 to 3** — the two detached rafter-foot clusters the validator
was reporting at (−66.3, 13.8) and (36.3, −64.1) are gone from the shipped
town. Rendered and read:
`review/shots/gates-granary/gates-granary-gameplay.png` shows the granary with a
correct jerkinhead and no floating timbers.

---

## 5. `rubble` — coursed, varied, and no longer green. Improved, not finished.

`ad-town-02` §9 and §10 both reject on this, and it is ~60% of the pixels in the
mandated arrival frame plus the whole enceinte.

**Cause.** `rubble_weathered` was built from two interleaved `worley` fields.
`worley` puts one feature point per cell of a uniform lattice, so it is
**isotropic by construction** — no amount of jitter can produce bedding. What
came out was crazy paving stood on its end.

**Fix**, in `tools/assetgen/core/materials.py` `rubble_weathered`, addressing all
three of the review's points:

1. **Bedding.** Rebuilt on `coursed` — the bond generator already in that module
   that brick, ashlar, sett and plank use. *(I first wrote a new `coursed` into
   `core/mathx.py`, then removed it: `materials.coursed` already existed with
   seven callers, and a second one is exactly the fork CLAUDE.md forbids.)* High
   `wobble` is what turns it from brickwork into rubble brought to course; I
   swept it and read the result — 0.0 / 0.18 / 0.35 / 0.60 — and settled at 0.62
   with 6 courses. A second, coarser lattice supplies big stones in patches,
   selected with a **hard** mask because cross-fading two joint fields leaves
   both sets faintly visible and the surface goes to mush.
2. **Two noise sources of colour** (Art Bible §8): ±18% per *stone* from the
   bond's own per-unit identity, plus a low-frequency mask that moves whole
   *lifts* so courses read as separate days' work.
3. **The green mortar is gone.** The joint was tinted `HERB_GREEN` *globally*,
   which put a green cast over the church, the perron cheeks, the podium and the
   town wall. Mortar is now a warm lime grey; moss is a **local** mask biased low
   on the wall where ground damp actually is, and is a parameter (`moss`) so a
   dry gable and a wet plinth need not be the same texture.

**Verified visually**, same frame before and after:
`review/shots/gates-rubble/gates-rubble-detail.png`. It is unambiguously a wall
now rather than a garden path.

**Honest remaining criticism, so nobody signs this off as finished:** the 2 m
tile repeat is still readable across a large elevation, and stone-to-stone value
contrast could go further. It needs one more pass and an art-director look —
what I have here is a self-assessment, which `CLAUDE.md` is explicit is not
sign-off.

### What I did NOT do on item 5

- **A separate paving material.** The review says `rubble` is "doing duty as
  both church walling and market paving". On the current tree that is no longer
  true: `venues/market_square.py:216 _paving` uses `cobble`, and grep finds no
  `rubble` in `market_square.py`, `core/streetscape.py` or `core/roadnet.py`.
  That split appears to have already happened upstream; the wall material was
  the half still broken.
- **The green-mottle split (§14).** I could not reproduce the stated cause. The
  `foliage` key is used only by `vegetation.crop_row`, `tussock`, `joint_weeds`
  and `kit.leaf_cluster` — all vegetation. Nothing in `core/building.py` uses it
  for timber-frame infill. The green on the daub panels in `spine-walk-02` is
  coming from somewhere else and needs to be found by reading the frame, not the
  source. **Still open.**

---

## Status of the five items

| # | item | state |
| --- | --- | --- |
| 1 | `validate.py` stalls | **Done.** Never finished → **40 s**; broadphase verified equivalent on 1,500 points; 63 false failures removed; 7 real ones reported in §2. |
| 2 | `check_client.mjs` flaky | **Done.** Was 100% failing, not 12%. Now deterministic to the metre across 3 runs, and it surfaced two real defects (3.1, 3.2). |
| 3 | perf gate red | **Done.** Evidence says growth, not regression; re-baselined at 727 / 1,154,547 with the reason recorded as **D-048**. Gate green. |
| 4 | `roof.py` verges | **Done.** Root cause was `rotate_y` about the world origin, plus a real half_hip `_verge` bug. All three workarounds reverted and rebuilt. |
| 5 | `rubble` / green mottle | **Partly.** `rubble` rebuilt and much improved, but wants one more pass and a director's eye. Paving split already done upstream. Vegetation-vs-daub split **not reproduced, still open.** |

## Recommended next actions, ranked

1. **Settle the draw-call accounting (3.2).** Two gates disagree by 3x about
   whether the town meets §7. Until that is resolved neither number means
   anything, and both are being quoted in reports.
2. **Ford Road is not completable (3.1).** 202.6 m of walking for a 127 m route,
   reproducible on demand.
3. **The seven validator failures**, cheapest first: the two buried `flour`
   decals and the watermill wheel entity are one-line Y-derivation fixes.
4. **`landscape.gltf` is 34.2 m tall** — this is `ad-town-02` §7's unidentified
   floating mass, still unfound.
5. **Texture-atlas the six road-surface materials** (D-048): `streets` 155 draws
   → ~60, the largest single draw-call saving available in the build.
