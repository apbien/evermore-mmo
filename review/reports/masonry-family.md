# Masonry family — wave 06

**Lane:** `tools/assetgen/core/materials.py`, masonry keys only.
**Job:** kill the wavy cyclopean block; collapse seven masonry treatments to one
family; honour the tile-repeat rule; desaturate the terracotta base.

---

## 1. What the wavy cyclopean block actually is (found before changing anything)

The art director's §1 describes "blocks 0.6–1.1 m across with ~10 cm rounded
arrises, wandering non-straight joints, adjacent blocks differing by only a few
luminance levels". I measured all three against the frames and the source, and
**all three come from `coursed()` call sites, not from a Worley field.** Every
masonry key in the file was already on `coursed()` before this wave. The
argument "Worley cannot read as masonry" had in fact been carried to the whole
family — and the family still read as crazy paving, for three different
reasons.

### (a) `wobble` dissolves the bond, and it does so faster the finer the lattice

`coursed()` warps the lattice with

```python
gy = gy + fbm(s, 3, seed + 401, octaves=2) * wobble * rows * 0.12
gx = gx + fbm(s, 4, seed + 402, octaves=2) * wobble * cols * 0.18
```

The warp is scaled by `rows`/`cols`, so it is measured **in lattice widths, not
in units.** `fbm` runs about ±0.7. So the actual peak warp in *units* is:

| key | rows × cols | wobble | x-warp (units, pk-pk) |
| --- | --- | --- | --- |
| `rubble` fine | 6 × 8 | 0.62 | **1.25** |
| `rubble` coarse patch | 3 × 4 | 0.55 | 0.55 |
| `cobble_wall` | 10 × 11 | 0.52 | **1.44** |
| `limewash` | 11 × 7 | 0.55 | 0.97 |
| `stone` | 9 × 5 | 0.40 | 0.50 |

Once the x-warp exceeds ~0.5 units the perpends of neighbouring stones cross
each other, two units merge into one amorphous polygon, and the bond is gone.
At 1.25 and 1.44 units the lattice is *destroyed*: what comes out is a field of
irregular polygons with wandering boundaries meeting at three-way junctions —
which is the exact read the AD calls "cracked mud" on `cobble_wall` and
"inflated foam" on `rubble`. **The Worley pattern was removed and then
re-created by warping a regular lattice past the point where it is a lattice.**

The docstring warns "past ~0.8 the bond dissolves", but the threshold is not a
`wobble` value — it depends on `cols`. `rubble` at 0.62 and `cobble_wall` at
0.52 were both already past it.

### (b) the "10 cm rounded arris" is a full-unit sine pillow

`rubble_weathered` shapes its stone face as

```python
face = np.sin(np.clip(bed, 0.0, 1.0) * np.pi) ** 0.65
m.add_height(face * 0.30 * (1.0 - joint) - joint * 1.0)
```

`bed` is the unit-local coordinate, so the profile is a **half-sine across the
whole stone** — a pillow, not a stone with a chamfered edge. On the coarse
patch lattice (3 × 4 on a 2 m tile = 0.67 × 0.50 m units) that is a 0.5 m wide
dome. `foundation_stone`, `limewash` and `cobble_wall` all do the same thing.
That is the inflated-foam read, and it is why the surface reads as reptile hide
at any range under 5 m. A real dressed stone is **flat with a 20–30 mm arris**.

### (c) the per-stone value is authored and then painted over

`cobble_walling`'s docstring diagnoses this exactly, and fixes it *only inside
`cobble_walling`*:

> `tint` is a lerp toward a colour: a lerp at 0.6 over the whole stone field
> throws away 60 % of whatever spread was underneath it.

`rubble_weathered`, `foundation_stone` and `limewashed_stone` all still do it in
the broken order — `darken/lighten(±0.18…0.21)` first, then two `tint(…, 0.45)`
calls and a `tint(…, 0.20)` through overlapping masks. Net surviving spread is
a few luminance levels, which is the AD's third symptom verbatim.

### (d) the coarse patch selector breaks the tile-repeat rule

`rubble_weathered` chose between two lattices with
`big = normalize01(fbm(s, 3, ...)) > 0.52` — **one blob per tile**, the exact
thing `FREQ_FLOOR` and the rule above `mottle()` exist to forbid, and it
selected roughly half the sheet into 0.5–0.67 m megaliths. That is where
"0.6–1.1 m blocks" comes from.

### (e) the fine joints are sub-texel

`joint` is a half-width as a fraction of the shorter unit side. Converted to
millimetres at the shipped texel density:

| key | short side | `joint` | mortar | texels at shipped density |
| --- | --- | --- | --- | --- |
| `ashlar` | 0.286 m | 0.008 | 4.6 mm | **1.2** |
| `ashlar_civic` | 0.286 m | 0.008 | 4.6 mm | **1.2** (512 px/m, hero) 2.4 |
| `sandstone` | 0.333 m | 0.012 | 8.0 mm | **2.0** |

A 1–2 texel line does not survive one mip. That is why the drum towers and the
gate frontispiece read as "a smeared cloudy mottle with no courses" and the
guild tower as "a blank pale slab": **their bond is authored below the
resolution it ships at.** Physically-correct is not the same as visible; the
joint plus its shadow and dirt line has to be ≥ 3 texels or the wall has no
bond at all past 10 m.

---

## 2. What was built

One geology, one mortar, one weathering logic, and **one relief/colour engine
that every masonry key in the town now calls.** In
`tools/assetgen/core/materials.py`:

| new | what it is |
| --- | --- |
| `MASON_BODY/WARM/COOL/DEEP/MORTAR/LICHEN/DAMP` | the quarry. Seven constants; every masonry key starts from `MASON_BODY` and no key has a base colour of its own any more |
| `masonry_bond(...)` | lays the wall. Module in **metres**, joint in **millimetres floored at three texels**, and a flat face with a real **arris** instead of a full-unit sine pillow |
| `masonry_colour(...)` | colours it, in the order that survives: family tints → within-stone grain → weather → mortar → **per-stone value LAST** |
| `coursed(..., wobble_u=, stagger=, vary=, hash_unit=)` | four opt-in parameters; every existing caller is byte-identical without them |

Every one of the seven keys is now a short parameter list against that engine.
`rubble` and `stone` differ by `wobble_u` 0.30 vs 0.09, `stagger` 0.62 vs 0.30
and a `sneck` course — they are the same rock through two levels of a mason's
wages, which is what "one family" has to mean if it is going to hold next pass.

**The four `coursed` parameters, and why they had to be new rather than tuned.**
`wobble` is scaled by `rows`/`cols`, so it is measured in lattice widths. It
cannot be turned down to a safe value *and* leave the existing callers (brick,
slate, sett, tile, plank) where they are. `wobble_u` measures the same warp in
**units** at a noise frequency tied to the lattice, so 0.30 is 0.30 of a stone
whether the wall is 4 stones wide or 40. `stagger` (per-course random phase)
and `vary` (per-course width scale) are what actually make a wall read as
hand-laid — a fixed `bond` alone is brickwork — and they do it without bending
a single joint. `hash_unit` replaces `coursed`'s low-discrepancy per-unit
sequence with a real 2-D hash; see §4, because that one surprised me.

Module table, measured against the 1.75 m figure, all at 2 m coverage:

| key | course | stone | mortar | arris | reads as |
| --- | --- | --- | --- | --- | --- |
| `rubble` | 0.20 m | 0.36 m | 26 mm | 30 mm | random rubble brought to course, with snecks |
| `stone` | 0.22 m | 0.40 m | 16 mm | 22 mm | squared and graded |
| `limewash` | 0.19 m | 0.30 m | 28 mm | 28 mm | `rubble`, poorer, under one coat of lime |
| `sandstone` | 0.28 m | 0.55 m | 18 mm | 20 mm | quarry-faced blockwork, bedded |
| `ashlar` | 0.30 m | 0.60 m | 12 mm | 14 mm | dressed; the town's quoins and jambs |
| `ashlar_civic` | 0.30 m | 0.75 m | 8 mm | 10 mm | fine-dressed; guild, moot hall, nave |
| `cobble_wall` | 0.185 m | 0.19 m | 45 mm | — (domed) | whole river cobble in a fat bed |

Nothing lays a stone a mason cannot lift onto a scaffold. `ad-town-05` §1 asked
for 0.35–0.55 m walling; `rubble` measures **0.36 × 0.20 m** in
`mereshore-free` (61 px/m, stones 22 × 12 px) and `stone` **0.41 × 0.24 m** in
`bailey-walk-04` (34 px/m).

One family, measured off the shipped sheets:

| key | mean L | L std dev | warmth (R−B) |
| --- | --- | --- | --- |
| `stone` | 0.573 | 0.051 | +0.112 |
| `rubble` | 0.576 | 0.069 | +0.107 |
| `ashlar` | 0.585 | 0.045 | +0.109 |
| `ashlar_civic` | 0.579 | 0.040 | +0.120 |
| `sandstone` | 0.577 | 0.041 | +0.120 |
| `limewash` | 0.637 | 0.023 | +0.111 |
| `cobble_wall` | 0.525 | 0.091 | +0.110 |

Warmth spans **0.013** across the whole family where it used to span 0.04
(`ashlar` +0.120 against `stone` +0.082) — that is the seam that made one wall
run change rock three times. `ashlar`'s value spread went 0.020 → 0.045: pass
02's "stacked polystyrene" was a wall with no per-stone value at all.

The family sits at `ashlar`'s **old** warmth, not at `stone`'s, deliberately.
Art Bible §1 wants a warm foreground, the church interior is lit almost
entirely by sky ambient, and a neutral body turns the spawn frame blue.

Contact sheet: **`review/shots/masonry-06/family-sheet.png`** — all seven at
4 m across with a 1.75 m bar.

---

## 3. In frame — what I would sign off, and what I would not

Renders: `review/shots/masonry-06/` and `review/shots/masonry-06b/` (the second
adds §5's filtering fix), against `review/shots/ad-town-05/`.

**A caveat I have to state first, because it will otherwise be read as mine.**
Three other agents were writing `client/src/shadows.js`, `client/src/terrain.js`,
`client/src/water.js`, `tools/render/town.mjs` and
`content/town/hearthmere.json` while I was rendering — file mtimes inside three
minutes of my render. **Every frame in this wave is markedly darker than
`ad-town-05` and it is not the masonry:** `t-arrival`'s nave wall mean fell
0.442/0.379/0.284 → 0.155/0.159/0.143, while over the same change the `stone`
albedo got *lighter* (L 0.489 → 0.573) and its AO got *brighter* (0.909 →
0.976). Judge my surfaces on structure, not on exposure, until the lighting
lane settles. The comparison crops are exposure-normalised where marked.

### Signed off

**`t-arrival` — the nave, 55 % of the spawn frame.** `cmp-arrival-nave.png`.
The wavy cyclopean block is gone. The piers, the arch voussoirs and the wall
panels read as coursed masonry with straight bed lines, a crisp arris and a
per-stone value spread you can count stones by. The voussoirs read as voussoirs
for the first time. This is the finding `ad-town-05` ranked #1 and called the
only thing left wrong with the most important composition in the build.

**`mereshore-free` — the watermill, 70 % of frame at 5 m.** The mill's 12 m
elevation, its quoins, its wheel race and the town wall behind it now read as
**one stone at four dressings**. Pass 05: "the mill's 12 m elevation is the
cyclopean block with two more masonries on its quoins and its wheel race."
That is the "one world" fix landing in the frame it was worst in.

**`t-gate-south` — the regression pass 05 called severe.** The cold blue-grey
polygonal-plate curtain that "matches nothing else in the town" is gone. Wall,
gatehouse and the arch dressings are one family; the hard vertical seam where
the curtain met the gatehouse's warm stone is closed, and the tile repeat the
review counted at x≈60/300/420/1150/1290 is not findable.

**`t-gate-north` — the frame with five treatments in it.** Curtain, drum
towers, gate frontispiece and coping now read as one stone. The "smeared cloudy
mottle with no courses" on the drums and the "fine speckled sandstone" on the
frontispiece were both the **sub-texel joint** (§1e), and both now carry a
visible bond.

**`bailey-walk-04` — `cobble_wall` at 2 m.** The cracked-mud Worley plates are
gone; the enceinte reads as coursed masonry at 0.41 × 0.24 m against the
figure. Pass 05 rejected this key for the third time and the last agent
declined to claim it. **I am claiming it, and it is in two frames**
(`bailey-walk-04`, `craft-walk-04`).

**`craft-walk-04` — the enceinte at 25 m.** `cmp-craft-enceinte.png`. The blank
slab closing Bakers' Row now carries a legible course line at 25 m.

**`t-aerial-sw` / `t-plan` — terracotta.** The three kiln batches read. The
aerial is a population of deep red, brick red, pale terracotta and ochre
instead of "~70 % one saturated orange". One line: the base was desaturated
22 % toward a neutral **of the same luminance** (#757575 matches #B5603E's
luma), so the roofs did not go darker, they gained room to vary in both
directions. `COLOR_0` can only multiply down, which is why this had to be a
base change and not a vertex-colour change.

### Not signed off

**The bridge parapet in `t-gate-north` reads as portholes, and it is worse than
it was.** `gatehouse.py:263` sweeps the parapet in **`cobble_wall`**, and
`M.sweep` stretches the UV along the sweep, so 0.19 m river cobbles land at
~0.37 m and elongated. My round-footprint cut — correct for a cobble wall —
makes that stretch read as a row of dark ovals. Two things are wrong and
neither is the recipe: a bridge parapet is coped ashlar, not river cobble, and
the swept UV does not go through `MATS.uv_scale`. **This belongs to the
wall/gate lane and I have not touched it.** If nobody picks it up, the cheap
fix is `mat="ashlar"` at that one line.

**`ashlar_civic` still ships at 0.60× its authored density** (`uv_density`,
1508 m², guild = 1.29 m/tile against 2 m authored). The guild lays that UV by
hand. Widening the joint to 8 mm means the bond survives *anyway*, so the
symptom is much reduced, but the density error is real and it is in the guild
venue, not in the material.

**`sandstone`'s bedding does not read at gameplay range.** It is a legible
coursed wall now and it is in the family, which is what the cohesion finding
needed. But its identity — the horizontal bedding plane — is still weak past
10 m. I would not call it a distinct stone yet; I would call it `stone` with a
coarser face. Honest state: fixed as cohesion, not yet fixed as character.

**`limewash` I have in the sheet and in the far background only.** Not claimed
in a frame. Stating it the way pass 05 asked for.

---

## 4. Two things I found that were not in the brief

**(a) `coursed`'s per-unit identity is a sequence, not a hash — and it was
hidden by the very bug I was fixing.** `unit = (19·row + 7·col)·φ mod 1` steps
by exactly 0.326 between neighbours along a course and 0.740 up a wall. Both
are near-rational, so the field repeats on a ~3 × 4 block of stones. While a
`tint` pass was flattening the per-stone spread this was invisible; the moment
the spread survived, **every wall in the town came out as a chequer** — I have
that in an intermediate sheet. Permuting the values does not help, because the
periodicity is spatial. `hash_unit=True` swaps in a real 2-D hash of the unit
index. Opt-in: brick, slate, sett, tile and plank were tuned against the
sequence and I did not move them.

Worth stating plainly, because it is a trap for the next agent: *a material can
hide a second defect behind a first one, and fixing the first one ships the
second.*

**(b) `craft-walk-04`'s "chevron/zigzag moiré that reads as corrugated
cardboard" is the wall's MESH, not a mip problem.** `ad-town-05` §5 attributes
it to "a high-frequency normal at a grazing angle with no LOD strategy". In
`cmp-craft-enceinte.png` the chevron is pixel-for-pixel identical before and
after a complete material rebuild *and* after anisotropic filtering was turned
on — while the material either side of it changed completely. It is a low-poly
sawtooth in the wall / wall-walk silhouette seen almost edge-on. **The wall
lane should look at the mesh, not at the texture.**

---

## 5. The market place past 12 m: anisotropy was never turned on

`ad-town-05`'s open item — "the market place past 12 m mips to a flat sandy
plane (a filtering problem — mip generation or anisotropy, not the texture)" —
is exactly right, and the cause is that **`Texture.anisotropy` was never set
anywhere in the project.** three.js defaults it to 1, so a surface picks its
mip from the larger of its two screen-space derivatives and is blurred along
the axis that needed no blurring. At a 1.62 m eye that is the entire ground
plane past a few metres, and it is also why distant walls lose their bond.

`review/shots/masonry-06/cmp-square-aniso.png` is the proof: same camera, same
setts, and the far half of the market place goes from a featureless sandy plane
to legible paving across its whole depth.

**Shared-file edit, declared.** One function, `anisotropic()`, added to
`client/src/lod.js`, called at the end of `prepareLods()`. That is the single
smallest edit that fixes it everywhere: `prepareLods` is the one function both
`client/src/main.js` and `tools/render/town.html` call on a loaded glTF, once
per file, after the LOD alternates are attached — so the runtime, the review
harness and every LOD level are covered by one change and cannot drift. I wrote
it into `client/src/main.js` first and moved it, because that would have needed
a mirrored edit in `town.html`, and two shared files is worse than one. 16 is
clamped to the device maximum by three.js at upload and is a no-op where the
extension is absent. Draw calls 1399 → 1398 (noise). `check_client.mjs` boots,
walks its 151.5 m, no new warnings.

---

## 6. Instruments

| | before | after |
| --- | --- | --- |
| `uv_density.py` | 4 failures, 11 warnings | **3 failures, 10 warnings** |
| `validate.py` | 5 failures, 46 warnings | 5 failures, 47 warnings — none of them mine; `water_fall` is another lane's, mid-flight |
| `check_walkable.mjs` | 15/15, 1 unreachable door | unchanged: Ford Road traversable, `hm.slot.07.chophouse.door.01` still unreachable |
| `check_client.mjs` | FAIL 1395 draws | FAIL 1398 draws — unchanged in kind, not a masonry cost |

No texture grew: every masonry key ships at the size and coverage it did
before, so mesh and texture memory are untouched by this wave.

---

## 7. Owed to `docs/DECISIONS.md`

Not written by me — the ID space is contested (the doc session's D-036/D-040
won a collision at reconciliation) and I am not going to add to it from a build
session. Three entries are owed:

1. **One masonry family.** Seven keys, one geology, differing by dressing, age
   and wealth. `MASON_*` plus `masonry_bond`/`masonry_colour` are the single
   source; a new masonry key must be a parameter list against them, never a
   body of its own. This is the rule that has to hold or the count goes to
   eight next pass.
2. **`coursed(wobble=)` is deprecated for masonry.** It measures its warp in
   lattice widths, so its safe range depends on `cols`; past ~0.5 units of warp
   it reconstructs a Worley tessellation out of a regular lattice. Masonry uses
   `wobble_u`/`stagger`/`vary`. `wobble` stays for brick, slate, sett, tile and
   plank, whose numbers were tuned against it.
3. **Joints are authored in millimetres and floored at three texels.** A
   physically-correct 4.6 mm ashlar joint at 256 px/m is 1.2 texels and ships
   as no joint at all. A joint you cannot see is a missing joint, not a fine
   one.
