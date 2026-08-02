# Foliage rebuild — answering ad-town-02 §2, §3 and §11

**Scope.** The three vegetation defects the art director measured: the leaf
atlas (§2), the yew and `blob_canopy` (§3), and the bare intramural ground
(§11). Everything here is generator work in `core/materials.py`,
`core/vegetation.py` and `venues/landscape.py`. Renders in
`review/shots/veg-01/`, compared frame-for-frame against
`review/shots/ad-town-02/`.

---

## 0. A build-blocking defect found on the way in

**`landscape` had been deleted from `content/town/hearthmere.json`.**

The AD reviewed a build where it was present (`ad-town-02/t-report.json`
lists it between `terrain` and `streets`, at 1,508,214 triangles). By the time
I started, the `venues[]` array in the town file no longer contained it —
somebody's rewrite of that file dropped the entry. The mesh was still being
built and written to `assets/meshes/landscape.gltf`; nothing was loading it.

Consequence: **the town was rendering with no vegetation and no intramural
ground at all** — no trees, no hedges, no tussocks, no churchyard, no orchard,
no distance wood. I spent a while chasing "the leaf cards are invisible" before
finding it, which is worth recording so the next person does not.

Restored at `content/town/hearthmere.json`, spliced back in its original
position as text so the rest of the file's formatting is untouched (another
agent is editing it concurrently). The entry now carries a comment saying what
its absence costs.

Related: `tools/assetgen/build.py` `discover()` now reports and **skips** a
venue module that fails to import instead of taking the whole build down with
it. A half-saved `moot_hall.py` meant nobody could rebuild any venue for as
long as it took that agent to finish the line they were on. The failure still
prints, and `--venue X` on a broken module still fails with "unknown venue", so
nothing goes quietly.

---

## 1. The leaf atlas (§2)

### What was measured, before

Read directly off the shipped PNGs' alpha and albedo:

| sheet | opaque coverage | pixels warmer than green |
| --- | --- | --- |
| `leaf_oak` | 17.8 % | 31.4 % |
| `leaf_ash` | 11.0 % | 31.1 % |
| `leaf_apple` | 15.7 % | 18.5 % |
| `leaf_willow` | **6.6 %** | 17.8 % |

The AD's arithmetic was right and if anything generous: willow was at a
fifteenth of the sheet.

### What was changed

**`materials.leaf_cards` is now a spray, not a blade.** Each of the sixteen
cells carries two or three shoots rising from one node just inside the cell's
own bottom edge, with five to seven alternate leaves per shoot that stand more
upright the higher up the shoot they sit. That last part is what fills a square
cell — a simple fan from one point leaves the top corners empty and tops out
around 35 %.

**The season is out of the albedo.** `leaf_atlas` ships all green in every
season. The autumn share is now a per-card `COLOR_0` tint applied in
`vegetation.leaf_cards` (`AUTUMN = (1.00, 0.62, 0.33)`), default 0.0. COLOR_0
multiplies into base colour, so it can only darken and warm — which is exactly
what a turning leaf does to a green one, and lands on a russet rather than the
candy orange §1 forbids.

**The petiole cannot be clipped.** Every stalk converges inside its own cell.
The only thing a 2×2 sub-rect card can cut is the short stub where the shoot
meets the cell's bottom edge — and that edge *is* the twig, so a stub there is
correct. No card can draw a severed stalk with no leaf on it any more.

**A second, free win: `COLOR_0` also carries crown depth.** Cards inside the
crown are multiplied down toward 0.68 and cards on its surface stay at 1.0,
with a small lift for cards high in the crown. That is baked canopy AO for one
multiply and no extra vertex, and it is most of the difference between a tree
and a flat green cloud.

### What was measured, after

| sheet | opaque coverage | warmer than green |
| --- | --- | --- |
| `leaf_oak` | **47.4 %** | 0.0 % |
| `leaf_ash` | **59.7 %** | 0.0 % |
| `leaf_apple` | **53.8 %** | 0.0 % |
| `leaf_willow` | **59.4 %** | 0.0 % |
| `leaf_yew` (new) | **57.2 %** | 0.0 % |

All five clear the ≥ 45 % bar. Orange is gone from every sheet.

### The card economics that follow

Coverage per card went up ~3.5×, so `tree()`'s card multiplier went **9.0 →
6.0** and still buys a denser canopy than before. It is not the 3× the coverage
alone would allow: I tried 3.1 first, looked at `t-square`, and the crown was
still see-through, so I bought some of the win back as opacity rather than
taking all of it as triangles. Measured per tree, LOD0:

| tree | cards before | cards after | LOD0 tris after |
| --- | --- | --- | --- |
| 9 m oak | 605 | **403** | 1,102 |
| 4.8 m apple | 143 | **81** | 492 |
| 9 m yew | none (28-face lathe ×3) | **645** | 1,856 |

LOD chains now measure oak `1102 / 452 / 218 / 36`, apple `492 / 170 / 124 /
36`, yew `1856 / 800 / 342 / 36`. LOD3 is unchanged — a 36-triangle blob at
100 m. The yew is the most expensive tree in the town by a distance, on purpose:
it is 1.6× density because you cannot see through a yew, and there are four of
them.

---

## 2. The yew and `blob_canopy` (§3)

**`SPECIES["yew"]` no longer routes to `blob_canopy`.** A yew is a conifer, so
it does not get a broadleaf sheet either: `materials.needle_atlas` is a new
`leaf_yew` set — flat sprays of linear needles in two ranks along a shoot, dark
olive with a pale underside band, 57 % coverage. The churchyard yews are card
canopies at 1.6× the normal density (you cannot see through a yew).

**`blob_canopy`'s defaults are `rings=7, segments=16`** (were 4 and 7), and the
radial noise is now two low-order lobes plus per-vertex jitter rather than one
uniform per-vertex draw — one frequency at one amplitude keeps the facets in
readable rings however many segments you add. Its docstring now says in plain
words that nothing a player can stand under may use it. After this change the
only callers are LOD2, LOD3 and a hedge's end, all beyond 40 m.

**The distance wood is an impostor, not a lathe.** `distance_tree` is three
crossed billboards plus one 45°-tilted cap — **8 triangles**, on a new 2×2
`tree_far` sheet carrying four different whole-tree silhouettes with lobed
margins, sky-holes through the crown, a bole and a top-lit vertical ramp. The
first version used a near-flat cap; in a wood of two thousand that reads as a
field of glowing horizontal slashes from a 1.62 m eye, hence 45°.

`landscape` LOD0 triangles: **1,508,214 → 262,134 (−83 %).** The wood alone went
from ~207,000 triangles to ~7,500 for the same 2,995 instances. Instancing is
unchanged — `ctx.instance` / `ctx.lod` throughout, three prototypes so the
horizon does not read as a repeat, coppiced into blocks so each batching cell
clears `INSTANCE_MIN`; every tree kind is a four-step `ctx.lod` chain.

Where the venue's geometry goes now, across all four LOD levels (543,907 tris,
31.8 MB of `.bin`):

| material | tris | share |
| --- | --- | --- |
| `hedge` | 118,542 | 21.8 % |
| `foliage` (tussocks, nettles, crops) | 71,456 | 13.1 % |
| `leaf_oak` | 70,630 | 13.0 % |
| `timber_grey` (boles, limbs, wattle) | 52,819 | 9.7 % |
| `foliage_flower` | 39,252 | 7.2 % |
| `grass_worn` (new intramural ground) | 31,704 | 5.8 % |
| `leaf_yew` | 24,367 | 4.5 % |
| `tree_far` (2,995 distance trees) | 7,504 | 1.4 % |

The next target is obvious from that table and is not the leaves: `hedge` is the
largest single consumer in the venue, ahead of every leaf material combined, and
it is a lofted prism with no LOD of its own.

Worst gameplay frame after all of this: **583 draw calls / 1,127,546 triangles**
against the §7 budget of 900 and 3.5 M. `check_palette`, `check_scale`,
`check_anachronisms`, `check_texel_density`, `check_albedo_exposure` and
`check_mesh_bytes` all pass; the leaf atlases no longer appear among the palette
checker's worst offenders (they were at 10–13 dE before, per the code's own
comments).

---

## 3. The bare ground inside the wall (§11)

Two things were wrong and only one of them was the landscape's fault.

The first was §0 above: nothing from `landscape` was loading.

The second is real and is now fixed as far as one pass can. `venues/terrain.py`
resolves **one material per triangle over a 4 m mesh**. A burgage plot is 5 m
across, so an entire back yard falls inside two terrain triangles and takes
whatever the splat decided for them. `terrain.json`'s `townEarth.patch*` does
try to leave green pockets — it cannot, because nothing it can author is
smaller than its own mesh. That is why the intramural ground came out as one
brown field however much was planted on it.

New in `venues/landscape.py`:

- **`_intramural_ground`** — a second, finer ground on a jittered 1.8 m lattice
  over every cell inside the enceinte that is neither building, road, working
  yard nor water. It paints a *blend*: a trodden band within ~2 m of every made
  road, rough grass in the open, the wetter greens in the hollows and
  dung-and-straw in the pockets behind the houses. Thresholds are dithered by
  the same noise that chose them, so no two covers meet along a line. 2,847
  cells.
- **`_lattice`** — shared, hash-jittered corners. The first version was an
  axis-aligned grid and at eye height it looked exactly like one: a
  chequerboard of flat tiles at 0° and 90°. Corners are now borrowed between
  neighbours, so cells are irregular and cannot gap.
- **`_surface_patch`** — every back plot gets its own ground, drawn from
  `YARD_SURFACES` (worn grass, dung-and-straw, beaten earth, cinder, gravel) or
  turned earth if it is a worked garden, with a ragged margin.
- **`_desire_path`** — the worn line from the back door to the plot gate, in
  the opposite cover to the yard it crosses. It wanders and its width varies; a
  straight constant-width ribbon is a decal.
- Each cover is drawn at **its own authored tile size** (`materials.uv_scale`),
  and each cell carries a COLOR_0 value jitter. `yard`, `dirt`, `cinder` and
  `gravel` are 2 m materials and `grass_*` are 6 m ones; one shared UV scale
  stretches four of the six by 3× and blurs them into flat colour, which is
  precisely what makes a ground patch read as paint. I shipped that mistake in
  the first pass and it is visible in the first `lanes-walk-02` I rendered.

`node tools/check_walkable.mjs` still passes 15/15 streets after the ground
layer; the one unreachable door (`hm.townhouse.door.15`) pre-dates this work.

---

## Before / after, honestly

**`kirk-walk-01` — the frame the AD called the worst in the build.** Before:
two enormous flat dark-green angular slabs, hard-edged against the sky,
occupying the left and right thirds and cropping both aisles off the church,
with three loose sticks poking out of each. After: two real yews with needle
sprays and visible branch structure, a broken silhouette, and the west front,
the perron cheeks, both aisles and the arcade all readable through and between
them. This is fixed.

**`t-square`.** Before: bare antlers hung with multicoloured confetti — green,
orange and blue specks with the branches showing straight through. After: a
tree. Closed green crown, real bole with a root flare, limb structure that
supports the canopy, a leaf shadow pattern on the paving. Verified at 11 m
(`oakclose-free.png`) as well as at review distance.

**`t-aerial-ne` / `t-plan`.** Before: the distance ring was hard-faceted green
crystals with visible flat triangles, and the whole intramural area was one
brown field. After: the ring reads as woodland, and the walled area reads as a
plan — green plots and yards between the houses, the churchyard legible, the
ring road legible against them.

**What is still not good enough, in my own work:**

- The intramural ground is *better*, not *right*. At a 1.62 m eye
  (`lanes-walk-02`) the covers still read as flat coloured shapes lying on the
  mud, because they are opaque materials meeting at a hard silhouette with no
  height blend between them. The correct fix is what `terrain._ground_group`
  already does — one continuous mesh, material per triangle, COLOR_0 tinting
  each vertex toward its neighbour across the boundary — and it belongs in
  terrain, not in a drape on top of it. The AD called this "a week, not a day"
  and was right.
- The leaf sprays are still individually readable at the crown edge at close
  range. That is arguably correct (a real crown has that at its silhouette) but
  the interior wants another ~20 % density and I stopped where the triangle
  budget stopped being obviously free.
- The willow atlas reads more like a fern than a willow. Its `elong` of 4.6
  across 8–11 leaflets is the right proportion for the leaf and the wrong one
  for the spray.
- The impostor's clump highlights are pale; at 140 m it does not matter, and in
  a close aerial it does.
- **Not touched, still open from the AD's list.** The dark slashes over the
  fields in both aerials are NOT the new impostors — I zoomed in to check.
  They are `hedge_run` field boundaries in the radial-and-concentric polar
  pattern of §19, and they are unchanged. Also unchanged: the hedge in Kirkgate
  (§15), and `hedge` itself, which is now the single largest triangle consumer
  in the venue at 118,542 — ahead of every leaf material combined — and has no
  LOD chain of its own. That is the next piece of this job.

---

## Files changed

| file | what |
| --- | --- |
| `tools/assetgen/core/materials.py` | `leaf_cards` rewritten as sprays; `leaf_atlas` all-green + per-species spray params; new `needle_atlas` (`leaf_yew`); new `tree_impostor` (`tree_far`); both registered in `LIBRARY` |
| `tools/assetgen/core/vegetation.py` | `AUTUMN` tint; `_quad` carries COLOR_0; `leaf_cards` gains `autumn`/`depth_shade`/`radius`; yew re-speciated; card multiplier and per-species density; `blob_canopy` defaults and lobed noise; `distance_tree` rebuilt as an impostor; shrub/bean-pole/pollard card counts |
| `tools/assetgen/venues/landscape.py` | `_lattice`, `_poly_inside`, `_surface_patch`, `_desire_path`, `_intramural_ground`, `YARD_SURFACES`; plot skins and desire paths wired into `_plots`; `_distance_wood` docstring |
| `tools/assetgen/build.py` | `discover()` skips a venue that fails to import instead of killing the build |
| `content/town/hearthmere.json` | **restored the deleted `landscape` venue entry** |

Rebuild: `python tools/assetgen/build.py --textures-only --force-textures
--only leaf_oak --only leaf_ash --only leaf_apple --only leaf_willow --only
leaf_yew --only tree_far`, then `--skip-textures --venue landscape`.

## Frames

All in `review/shots/veg-01/`, all at the locked 09:30 rig, all rendered and
looked at. Compare against the same-named frames in `review/shots/ad-town-02/`.

| frame | what to look at |
| --- | --- |
| `kirk-walk-01.png` | the AD's worst frame. Yews, aisles, west front |
| `kirk-walk-02..06.png` | the churchyard and Kirkgate |
| `t-square.png` | the market oak |
| `oakclose-free.png` | the same oak at 11 m |
| `t-arrival.png` | the canopy at frame-left that was confetti |
| `t-aerial-ne.png`, `t-aerial-sw.png`, `t-plan.png` | the wood ring, the intramural ground |
| `lanes-walk-01..05.png` | a back lane and a worked plot at eye height — the weakest of these |
| `oak/oak-gameplay.png`, `oak/oak-detail.png` | the impostor wood in isolation |

The walk routes are stated on each image. `kirk-walk` runs
`13.5,-0.5 → 26,-0.5 → 26,-14.7 → 30,-22 → 22,-26 → 13,-26`, which puts frame
1 at exactly the AD's (13.5, −0.5) heading 90°.
