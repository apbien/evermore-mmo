# Draw-call budget, texture atlasing, and the close-range leaf card

Wave of 2026-08-02. Scope handed to me: **BUILD_DIRECTIVE §7's "texture atlasing
across the kit"**, which had never been done; **systemic failure #4, the
close-range leaf card**; the real numbers at every named camera; and the
100-character projection.

Everything below is measured. Where a claim is not backed by a render I say so.

> **Read this caveat before the numbers.** Four agents were editing this tree
> at the same time tonight. The client's shadow rig changed under me three
> times while I was measuring — I recorded the same `square` camera at 971,
> 1053, 1416 and 1397 draws within ninety minutes, with my own assets
> unchanged between the last three (1,416 / 1,397 / 1,385). Every absolute
> frame number here is a
> reading taken at the end of my wave. The numbers that are **mine** and are
> stable are the geometry ones: primitives, materials, take rate, texture and
> mesh memory. I have separated them.

---

## 1. What the atlas did

### The state I found

`core/atlas.py` was a complete, correct, well-argued module that had **never
reached a building**. The auto-apply hook in `core/venue.py._add` existed in
source but the shipped `assets/meshes/` predated it: of 35 mesh files, **11 had
no `kit` material in them at all**, including `townhouse` — the venue that
carries 57 of the town's 94 building masses and 775 of its 2,780 LOD0
primitives. `townhouse` cell `0_3` shipped as

```
brick glass glass_lit iron lead oak oak_dark oak_weathered painted
plaster plaster_shade ridge stone terracotta
```

— fourteen draw calls for one cell, six of which are materials that live on the
kit page.

Once rebuilt against current source the page reached them, and `pack_split`
then **refused most of what it was given.** Measured on `townhouse`: 212 `oak`
members refused at a median required squeeze of 2.0, 157 `oak_dark` at 13.1,
43 `sandstone` at 2.6. The refusals were not a bug — `MAX_FIT = 2.0` is Art
Bible §5's texel-density floor doing its job. They were a **rect-size** problem:
a rect held one tile, and a building is full of members longer than one tile —
wall plates, sole plates, jetty bressumers, principal posts, purlins, door
leaves, the iron straps on them and the lead flashing over them.

### The change: multi-tile rects

`ATLASES["kit"]` is now a mapping `key -> tiles`, where `tiles` is how many
repeats of that material's own tile the rect holds along each axis.

**Texel density is invariant under it.** A 2-tile rect is twice the pixels over
twice the metres: `_cov[k] = coverage * tiles[k]`, and `inner_density()` returns
the same 252–255 px/m for `oak` at 1 tile and at 2. What the multiplier buys is
*reach* — a member up to `tiles` long is taken at its authored density with no
squeeze at all. `tiles` must divide `2 * GUTTER`, because the rect's interior is
`tiles * cell - 2 * GUTTER` texels and each tile in it must be a whole number of
them; the constructor raises rather than silently mis-tiling.

I tested 4-tile rects as well. They take 19 more primitives and cost **+289 MB**
of texture memory (page 6656² against 5120²). Not worth it; the shipped
configuration is 2 tiles on the eighteen keys that carry long members and 1 on
the small goods.

Supporting work: `atlas.STATS` + `build.py --atlas-report` prints take rate per
material with the distribution of refused squeezes, so the quality/draw trade
this module makes once per member is now a number instead of an assertion. That
table is what told me the problem was reach and not geometry.

### Measured result

| | before (shipped assets, start of wave) | after |
| --- | --- | --- |
| glTF materials across 35 mesh files | **718** | **601** |
| LOD0 primitives town-wide | **2,780** | **2,241** (−19.4 %) |
| atlas take rate, eligible triangles | ~0 % reaching buildings; 92 % once wired | **99 %** |
| groups carrying a `kit` primitive | 146 / 552 | **265 / 379** |
| `townhouse` LOD0 primitives | 775 | **508** (−34 %) |
| `warehouse` | 153 | **75** (−51 %) |
| `tannery` / `watermill` / `stalls` | 44 / 57 / 41 | 21 / 34 / 24 |

The brief and `ad-town-04.md` quote 846 and 902 materials. I cannot reproduce
either; `sum(len(gltf.materials))` over the 35 files was 718 when I started.
The 846 is probably a count taken before some venues were rebuilt. 601 is what
is on disk now; reproduce it with a walk of `assets/meshes/*.gltf` summing
`len(doc["materials"])`, and the primitive count by summing
`len(mesh.primitives)` over nodes whose `extras.hm.lod` is 0.

### The quality check the brief demanded

`review/shots/budget/crop-atlased-timber.png` — a jettied timber-framed facade
at **8 m**, which is inside the gameplay ring. Posts, braces, rails, the jetty
bressumer, window mullions, shutters and boarding are all on the atlas page.
Grain scale is correct, there is no blurring, and nothing reads at the wrong
size. `review/shots/budget/kit-page.png` is the page itself: the 2-tile blocks
show their 2×2 repeat and the tile joins are invisible, because every material
in the library tiles seamlessly.

`tools/uv_density.py` (new this wave, another agent's) exempts `kit` from its
scale check by name, so **nothing automated is watching the density of atlased
geometry**. `street_props` is not in its exemption set either and should be.
That gap is worth closing before the page grows again.

---

## 2. The numbers, at every named camera

Measured at the 09:30 locked rig, `tools/render/town.mjs`, end of wave.
Baseline column is `review/shots/ad-town-04` as recorded in the harness
baseline (2026-08-02, 32 venues placed).

| camera | draws | scene | shadow | ao | post | triangles |
| --- | --- | --- | --- | --- | --- | --- |
| arrival | 1,376 | 541 | 568 | 205 | 62 | 2,931,622 |
| **square** (worst gameplay) | **1,385** | 467 | 604 | 242 | 72 | **3,591,341** |
| gate-south | 1,211 | 680 | 276 | 177 | 78 | 2,053,371 |
| approach-s | 736 | 561 | 72 | 41 | 62 | 1,369,636 |
| gate-north † | 1,242 | 671 | 332 | 175 | 64 | 2,676,194 |
| approach-ne † | 571 | 497 | 0 | 14 | 60 | 1,207,677 |
| approach-w † | 802 | 603 | 84 | 53 | 62 | 1,587,433 |
| silhouette † (not gameplay) | 3,503 | — | — | — | — | — |

† from a run twenty minutes earlier, before the last seven venues were rebuilt.
The four rows above the line are the final reading. I could not re-shoot the
other three: `client/src/atmosphere.js` was left mid-edit by another agent and
`town.mjs` failed with `Unexpected identifier 'lift'` for the last stretch of
my wave.

Baseline `square`: **1,419 draws** (scene 498 · shadow 602 · ao 258 · post 61)
/ 2,896,190 triangles.

**So the frame total moved 1,419 → 1,385, and that is the honest headline.**
The beauty pass fell (498 → 467) and the town's primitive count fell 19 %, and
almost none of it reached the total, because **the shadow pass acquired a
three-cascade rig in the same wave** — `client/src/shadows.js`, which is the
right fix for `ad-town-04` §1 and the largest single cost in the frame. Three
cascades re-draw the casters inside 42 m up to three times. Triangles rose
2.90 M → 3.60 M for the same reason and are now over budget.

At an intermediate point tonight, with my assets in and before the cascade rig
settled, the same instrument read **1,053 draws at the worst gameplay camera**
(`gate-south`), scene 677 · shadow 132 · ao 178 · post 66 — a −366 improvement.
That is roughly what the atlas is worth on its own. It is not what ships.

**Instrument parity, re-checked:** `town.mjs` arrival 1,380 / 2,925,154;
`check_client.mjs` arrival 1,399 / 2,935,683. **1.4 % on draws, 0.4 % on
triangles.** They were 82 % apart for about an hour while the shadow rig was
mid-change (town 230 shadow draws against the client's 1,024); they agree
again now. Anyone quoting a number from that window should re-measure.

### Memory

**Texture: 1,169 MB resident** (RGBA8 + mips, 102 referenced sets) against the
1,536 MB budget. The `kit` page is 420 MB of that at 5120², `street_props`
105 MB at 2560².

Atlasing **cost** texture memory rather than saving it, and that is worth
stating plainly: the page does not replace the loose sets, because the members
`pack_split` refuses still reference them. +269 MB spent to remove 539
primitives. Inside budget with 367 MB spare, and it is the trade §7 asks for —
but the next page must be sized against that 367 MB, not against 1.5 GB.

**Mesh: 243.2 MB of geometry across 35 files** (+5.3 MB of glTF JSON) against
the 240 MB budget — **1.3 % over.** Up from 239.4 MB. Some of that rise is
mine: `pack_split` cuts one mesh into two and re-indexes both halves, so
vertices on the cut exist twice. `validate.py` fails on it and should.

`validate.py`: 5 failures, 46 warnings. Four failures are `uv_density.py` on
`nogging`, `straw`, `wool_crimson`, `canvas_amber` (another agent's live sweep);
the fifth is the mesh-memory budget above.

---

## 3. The 100-character projection, re-run

Method is `review/reports/budget-truth.md` §"per-character cost", unchanged so
the two are comparable: 6 submeshes / ~25 k triangles at LOD0, one scene draw
each plus a shadow draw inside 42 m and an AO draw inside 35 m, distributed
15 / 35 / 50 across the LOD rings.

```
players     15x18 + 35x7.5 + 50x1   =   582 draws
            15x75k + 35x20k + 50x2k = 1.93 M triangles
town (square, end of this wave)     = 1,385 draws / 3.59 M triangles
                                      ------------------------------
TOTAL                               = 1,967 draws / 5.52 M triangles
§7 budget                           =   900 draws / 3.50 M triangles
                                        2.2x over      1.58x over
```

**It does not hold.** It is 34 draws better than before atlasing and worse on
triangles, and the reason is the cascade rig, not the atlas.

### What else has to change, in value order, with the number for each

1. **The shadow pass — the single largest item in the frame.** 604 draws at
   `square`, 568 at `arrival`: more than the beauty pass, 44 % of the frame.
   Three cascades × every caster inside 42 m. The fix is per-cascade caster
   culling (cascade 2 does not need LOD0 geometry; cascade 0 does not need
   anything past 18 m) and it is worth on the order of **250 draws** with no
   change to the shadow quality that `ad-town-04` §1 asked for. Nothing else
   available is that big. **This is now the budget's critical path and it
   belongs to whoever owns `client/src/shadows.js`.**
2. **Merged character meshes** — one skinned mesh, one atlas material per
   character. 582 → ~150 at 100 characters. Unchanged from `budget-truth.md`
   item 3, and now the second-largest lever.
3. **Three more material collapses, all measured.** Marginal primitives saved
   if each were folded into the primitive its cell already draws:

   | candidate | prims saved | how |
   | --- | --- | --- |
   | `plaster_shade` → `plaster` | **62** | `materials.py:966` — `lime_plaster(shaded=True)` differs from `plaster` in **its base colour and nothing else**. Move the difference to COLOR_0 (the vertex-colour path already exists and `_Accum` already pads it) and the key disappears, along with 19 MB of texture. |
   | `glass_lit` → one glazing page | **51** | a second atlas page, BLEND + emissive, holding both. Windows are small non-tiling quads and are eligible by construction. |
   | `tree_far` | **~150** | 157 primitives for 24 k triangles: 2,995 distance impostors spread over 157 instance cells. One prototype and one page makes it ~1. |

   `stone` (165), `terracotta` (82), `rubble` (67) and `ashlar` (58) are the
   next four and **none of them can go on an atlas** — they tile across walls,
   roofs and paving, and a repeated atlas UV samples the material packed next
   to it. They need a texture *array*, which is an engine-port feature, not a
   glTF one. Do not let anyone "fix" them by adding them to a page: `pack_split`
   would take the individual slabs of a paving field and land every slab on the
   same corner of the tile, which is `ad-town-04` §2's crazy paving arriving by
   a new route.
4. **The LOD2 material ceiling.** `venue.py._levels` caps LOD2 at 3 materials
   per group. At `square`, 171 of 473 drawn groups are at LOD2. Dropping the
   cap to 2 is one number and is worth roughly **100 draws** at the far ring,
   at a cost nobody can see past 40 m.

With (1) and (2): 1,385 − 250 + 150 = **~1,285** at 100 characters. Still over.
With (1), (2), (3) and (4) together: ~1,285 − 263 − 100 = **~922**, which is
within 4 % of the budget and is the first arithmetic in this project that lands
in the right neighbourhood. §7 is reachable. It is not reachable without the
shadow work.

---

## 4. The close-range leaf card (systemic failure #4)

### The sheet had never been baked

`materials.leaf_cards` contains a per-cell quarter-turn, tilt and zoom that
breaks the sheet's own 4×4 lattice, and it cites `ad-town-04.md` §4 by name. The
shipped `leaf_oak_albedo.png` was **seven hours older than that code**. Every
frame the art director read was rendered against a sheet that did not contain
the fix. Regenerated all five sheets with `--force-textures`;
`review/shots/budget/leaf-oak-sheet.png` is the result — sixteen sprays, each at
its own rotation, ~50 % opaque, lobed, with non-axis-aligned alpha edges.

### The card level, which is what I changed

A sheet with no lattice in it still produces one if seven hundred cards map it
the same way up. `core/vegetation._atlas_rect` now returns **four corner UVs in
one of eight orientations** — flip in u, flip in v, transpose — instead of a
min/max box. Those eight are the square's own symmetries and they are the only
transforms that map the 4×4 cell grid onto itself, so the sheet's guarantee that
no blade crosses a cell boundary survives and no card ever shows a severed leaf.
Eight orientations × nine sub-rect origins is 72 distinct cards from one sheet.

`core/vegetation.leaf_cards` also gives each card **four corner normals fanned
outward from its own centre** (`puff = 0.55`). A quad with one normal is flat,
and at five metres flat is exactly what it read as. This composes with
`_spherify`, which is applied first: `_spherify` makes the crown a volume, the
splay makes each clump one. It costs nothing — the vertices already exist.

### Verified, at both ranges

- `review/shots/budget/crop-square-oak.png` — the market oak at **18 m**.
- `review/shots/budget/town-free.png` — a free camera **5.5 m** from the market
  oak's bole, which is the range `approach-s` had the defect at.

**No chequerboard at either range.** Individual leaves resolve as leaves, at
many orientations, with light and dark across the crown. Against
`ad-town-04` §4's "regular rectangular grids of dark-green squares" this is a
different asset.

### What I did NOT fix, and am not claiming

- **No transmission term.** At 09:30 roughly a third of the visible cards are
  silhouette-black against the sky (`crop-atlased-timber.png` shows it clearly).
  `ad-town-04` §4 asked for one and it is a client shader change, not a
  generator one. It is the largest remaining foliage defect and it is
  unaddressed.
- **Canopy density fell ~12 %.** A 2×2 sub-rect card carries a quarter of a
  full-sheet card's leaf area, so the `big` parameter is a density dial as much
  as a variety dial. I moved it 0.72 → 0.55. Conserving leaf area would mean
  ~3× the cards on the same crown and I did not think a tripled foliage
  triangle count was the right trade with triangles already over budget.
- A few cards read as thin dark streaks where they are seen edge-on. Two
  triangles at grazing incidence; real, minor, and the standard cure is crossed
  card pairs at ~2× the triangles.

---

## 5. `approach-s`: the tree in the canonical return camera

**Cause, found from the data rather than guessed.** `ford_road` is authored to
`(0, 96)` — the edge of the 192 m plan grid — and `approach-s` stands at
`(0, 138)`, **42 m past the last authored point.** The field system runs over
the next 190 m of the road's line. So the hedgerow standard that took 40 % of
the frame was on nobody's road, no keep-out reached it, and
`check_walkable.mjs` passes 15/15 because it only walks streets inside the wall.
No instrument in the project could see it.

**Fix.** `landscape.Keepout.highway` — an 8 m clear corridor either side of the
carriageway on the three roads that actually leave (`ford_road`, `mere_street`,
`tan_road`), **continued 220 m past the last authored point along the road's
exit bearing.** It is tested by `open_road()` and enforced inside
`TreeSet.add`, which is the one funnel every tree in the town goes through — a
rule enforced in a caller is a rule the next caller does not apply.

It is a real-world rule, not a camera hack: an approach to a town gate is kept
clear either side of the way. It clears **standard trees only** and deliberately
not hedges, so field boundaries still cross the roads with gates in them.

Two false positives caught on the first run — the two Bailey street trees, taken
because the Bailey's east end touches 80 m and my first test was by radius.
Restricted to the three named highways; 6 street trees again, **5 hedgerow
standards refused.**

**Verified: `review/shots/budget/town-approach-s.png`.** The frame is clear. The
south gate reads through the corridor, the wall runs the width of the frame with
a tower at each end, and the roofscape behind it is legible for the first time.

Still wrong in that frame, and not mine: the field hedges are solid extruded
ribbons with sinusoidal tops and near-black flanks (`ad-town-04` §15); the wall
is still 5.2 + 1.1; the sky has no sun disc.

---

## 6. Files changed

| file | what |
| --- | --- |
| `tools/assetgen/core/atlas.py` | multi-tile rects (`ATLASES` values may be `{key: tiles}`), `_grid`/`_try_place`/`_place` packer, `_cellpos`, tiled `write()`, `inner_density` per key, `STATS`/`_tally` |
| `tools/assetgen/build.py` | `atlas_report()` — take rate per material, refused-squeeze distribution, page cost |
| `tools/assetgen/core/vegetation.py` | `_atlas_rect` returns 4 corner UVs in one of 8 orientations; `leaf_cards` per-card corner normal splay (`puff`); `_quad` accepts per-vertex normals |
| `tools/assetgen/venues/landscape.py` | `HIGHWAY_CLEAR`, `HIGHWAYS`, `Keepout.highway` + `open_road()`, enforcement in `TreeSet.add`, refusal count in the build line |

Renders and crops: `review/shots/budget/`.

## 7. One thing the next agent should not repeat

I spent a third of this wave measuring a moving target. Four agents were
rebuilding `assets/` and editing `client/src/` at once; a full build died
mid-run because another agent's `uv_scale` sweep had left `venues/quay.py`
broken, and the `square` camera moved 445 draws in ninety minutes with my own
assets unchanged. **Any wave that has a budget agent in it should give that
agent the last build.** A frame number measured while someone else is editing
the renderer is not a measurement.
