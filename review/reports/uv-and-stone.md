# uv-and-stone — routing the material library to the screen

**Brief:** the single biggest unlock — 421 literal `uv_scale=` call sites
overriding the material library, then re-verify the three rebuilt masonries,
rebuild `cobble_wall`, sweep the tile-repeat rule, split the terracotta.

**Working note on concurrency.** A sibling agent was editing this tree
throughout this wave (`core/vegetation.py`, `venues/wall.py` and a running
`build.py` all changed under me between 02:47 and 03:05). One of my full
builds died inside a half-written `vegetation.leaf_cards`. Everything below is
measured off assets I built myself; where a frame could have been contaminated
I say so.

---

## The headline, and it corrects the brief

**The `uv_scale` sweep was already done — by the previous wave, in the
uncommitted tree, unbuilt and unverified.** `core/mesh.py:resolve_uv` exists,
`uv_scale=None` is the default on every builder, `materials.UVScale` /
`uv_detail(key, metres, why=...)` exist, and a bare float raises `TypeError`.
That work is real and it landed: I measured it.

**And it does not fix the crazy paving, because the crazy paving was never a
scale error.**

I wrote `tools/uv_density.py`, which measures world area over UV area straight
off the shipped glTF, per material, weighted by world area — the number that
decides what the player looks at, rather than the number the registry
declares. On the current build:

| surface | authored | **shipped** | ratio |
| --- | --- | --- | --- |
| `cobble` — every street in the town | 2.00 m | **2.06 m** | 1.03x |
| `sett` | 2.00 m | 2.02 m | 1.01x |
| `flag` | 2.00 m | 2.00 m | 1.00x |
| `rubble` | 2.00 m | 2.09 m | 1.04x |
| `stone` (foundation) | 2.00 m | 2.05 m | 1.02x |
| `limewash` | 2.00 m | 2.01 m | 1.00x |
| `terracotta` | 4.00 m | 4.07 m | 1.02x |
| `earth`, `grass_lush/dry/worn` | 4 / 6 m | within 2 % | ok |

`ad-town-04` §2 says the pattern "lands at roughly three times its intended
size". It lands at 1.03x. **The scale that reaches the mesh is right. What is
wrong is what the pattern IS.**

---

## Finding 1 — `cobble` was crazy paving by construction, and this file already
knew why

`materials.cobblestone` built the town's street surface out of a Worley cell
field:

```python
cells = worley(s, 12, seed + 41)                                  # f1 distance
edges = 1.0 - smoothstep(0.0, 0.11, worley(s, 12, seed+41, "f2f1"))  # the joint
dome  = np.clip(1.0 - cells * 1.15, 0, 1) ** 0.5
```

A Worley cell boundary is the **perpendicular bisector of two feature points**.
It is dead straight, and three of them meet at 120°. A field of Worley cells is
therefore, by construction, a field of straight-sided irregular polygons packed
edge to edge — which is not a description of a cobbled street, it is the
definition of crazy paving.

**This module already makes exactly that argument**, in `rubble_weathered`:

> *"worley puts one feature point per cell of a uniform lattice, so it is
> isotropic by construction: what came out was random polygons with no bedding
> at all — crazy paving, stood on its end and called a wall."*

`rubble` was rebuilt on `coursed` on that reasoning and the art director called
the result the best masonry in the build. **The same argument was never applied
to `cobble`, and `cobble` covers twenty times the area.**

Two defects compounded it. `edges` thresholds `f2f1` at **0.11** — a hairline,
so the stones met with no joint the eye could find and read as one plane scored
with lines rather than as separate objects. And `dome` is driven by the f1
*distance*, a broad smooth basin over the whole cell rather than a shoulder
dying into the joint, so every stone came out flat-topped.

Flat polygons + hairline joints + one value = a patio. That is `mere-walk-05`,
`t-square`, `craft-walk-04` and `kirk-walk-06`, and no amount of correcting the
UV scale was ever going to touch it.

**Rebuilt on `coursed`,** like `sett`, `brick`, `rubble` and `cobble_wall`
already are: 14 x 14 units on a 2 m tile (0.143 m cobbles), `bond=0.37`,
`wobble=0.70`, `joint=0.085` — **24 mm** of grit-filled joint against the
previous hairline. What keeps it from reading as `sett` (which is dressed, and
having both is the point) is a strong dome instead of a flat riven top, courses
that wander by most of a stone, and per-stone height so the street is never
flush.

Sheet stone-to-stone spread went **sd 13.8 -> 15.7** and the bond is now
visible in the 2x2 repeat.

## Finding 2 — `cobble_wall`: the variance was authored and then painted over

`ad-town-04` §6 regenerated this sheet with `--force-textures`, diffed it
against the shipped one, found them identical, and measured **adjacent stones
differing by about five luminance levels out of 255.** So the rebuild was real,
current, and still wrong. The review's own guess — that the `darken` was being
cancelled by the tints — is correct, and the mechanism is the order:

```python
m.tint(P.COBBLE, dome * 0.9)                       # a lerp over the whole face
m.darken(dome * per * 0.9, 0.26)                   # <- the per-stone value
m.tint(P.mix(P.COBBLE, P.SLATE, 0.35), dome * ... * 0.6)
m.tint(P.mix(P.TERRACOTTA_AGED, ...), dome * ... * 0.8)
```

`tint` is a lerp toward a colour. A lerp at 0.6 over the whole stone field
throws away 60 % of whatever spread is underneath it; three in a row leave a
field of stones that are all very nearly the tint colour.

Three fixes, and the third is one I found while looking at the sheet and is not
in the review:

1. **Order inverted.** Family first (all the tints), per-stone value **last**,
   so nothing can overwrite it.
2. **The joint deepened** — `dome*1.15 - joint*1.25` against `dome*1.05 -
   joint*0.55` — and the joint shadow duplicated into the **albedo and the AO**,
   because at 20 m the normal map is three mips down and gone.
3. **The colour masks changed from `dome` to `face`.** `dome` is 1 at the
   middle of a stone and 0 at its rim, so every colour painted through it drew a
   *radial gradient inside every stone* — a field of soft bullseyes, which is
   the defect `per_unit` exists to avoid and which this function had twice. A
   stone is one value across its face; the rounding is the height map's job.

Also: the bed was `P.PLASTER_SHADE` (#D4C4A8, L* 79) — **brighter than every
stone bedded in it**. The sheet drew a pale cream grid over coloured plates:
grouting, not walling. Now a lime-and-river-sand grey, net darker than the
stone.

Sheet spread **sd 12.5 -> 17.0**, range **72 -> 95**.

## Finding 3 — the thatch stems were a fingerprint because the warp was 50x
too strong

`ad-town-04` §10 read the shipped albedo as "a flat brown-olive blur with a
low-contrast fingerprint whorl" with "no straw in it at all". The whorl is one
number:

`fibre` phase-warps by `w * freq`. At `warp_amp=0.30` and `freq=170` that
displaces the phase by up to **51 half-cycles** — every stem shifted past its
neighbours, so what survives is not straw, it is the contour map of the warp
field. Settled at **`0.05`** — ~8 half-cycles on the broad term at 3 cycles per
tile, so a stem wanders by about four stems across a 4 m tile. I tried `0.016`
first and the render said no; see "three things the render said no to" below.

I also nearly broke this. `along="u"` looks wrong for a stem that runs down the
slope and I changed it to `"v"` — the render of the sheet said no. `fibre`
draws lines of *constant* `g`, and `roof.py` lays roof UVs as `(t along the
eaves, s up the slope)`, so `along="u"` gives lines of constant `t`, which run
up the slope. It was already right. Reverted, and the reason is now a comment
so the next person does not repeat it.

Bundle courses were at `_v * 5.0` — period 0.4 of a tile, so a bundle every
**1.6 m** on the authored 4 m tile, four times what a thatcher lays. Now
`_v * 20.0` = 0.40 m courses.

## Finding 4 — the tile-repeat rule, and the one that was left

The previous wave wrote the rule into `materials.py` above `mottle` and swept
most of it: `ground_splash` and `water_streak` are no longer called by any
material, and `limewash`, `sett`, `flagstone`, `cobblestone`, `hedge_mass` and
`rubble_weathered` all carry the fix and a note.

**`thatch_variant` was the one left**, exactly as briefed, and it was the worst
case in the file — *four* ramps in `v`:

```python
m.tint(OLD,   smoothstep(0.35, 1.00, _v) * ...)   # age
m.lighten(    smoothstep(0.40, 0.00, _v) * 0.7, 0.16)   # bleach
moss = moss * smoothstep(0.15, 0.80, _v)          # damp
cut  =        smoothstep(0.88, 0.97, _v)          # THE EAVES CUT
```

The 2x2 repeat proves it: **two hard eaves bands and two age gradients per two
tiles.** On a 9 m cottage slope over a 4 m tile that is the band twice; on a
barn, three times.

All four are gone. Weathering is now `mottle`-patched (a roof ages where the
moss took and where the sun reaches, not from its bottom edge). The eaves cut
is gone from the tile **and has not been lost**: `roof._thatch_slope` already
builds the rolled eaves as geometry — three facets curling under — which is
what the review asked for and what it is in reality.

## Finding 5 — the terracotta split, at zero draw calls

Asked for twice (pass-02 #21, pass-03 §5) and named in `ad-town-04`'s
top-three. `_ROOF_POOL` already deals slate and thatch into blocks and that
reads from the air; what it cannot do is make two *tiled* roofs differ, because
both take the identical sheet.

**Three batches, not three materials.** Two more texture sets would be ~34 MB
and, worse, two more batches on a build whose draw-call gate is already failed
at 1,416/900. COLOR_0 is already on every roof vertex for the course jitter and
costs nothing.

`roof.kiln_batch(asset_id, mat)` — seeded from the asset id **alone**, not the
slope index, so every slope, hip and dormer of one building come out of the
same kiln (seeding per slope is the obvious mistake and gives a town of
two-tone roofs). Three multipliers separated in **saturation and hue** as well
as value, because three roofs at three values of one orange still read as one
orange from 120 m:

| batch | multiplier | reads as |
| --- | --- | --- |
| fired | 1.00, 1.00, 1.00 | the authored orange; the best clay |
| under | 0.87, 0.91, 0.98 | browner, duller, value nearly held |
| lichen | 0.73, 0.81, 0.92 | grey-buff — the only tiled roof that is not orange |

Slate gets the same treatment at half the range.

## Finding 6 — the instrument that stops this coming back

The brief asks that a bare literal be a build-time error. `resolve_uv` already
does that for the 421 builder sites. **It cannot see the five places that lay
UVs by hand** — `streets._Paving`, `landscape._surface_patch`,
`market_square._paving`, `roof._uv_scale`, `core/vegetation` — and between them
those are most of the ground and roof pixels in a street-level frame. A literal
`* 0.5` in one of them is invisible to the type check, to `validate.py`, and to
`check_texel_density`, which only compares the registry with itself.

`tools/uv_density.py` measures the shipped glTF and is wired into
`validate.py` as `check_uv_density()`. Over half a stop warns; 2x fails.

**It carries an atlas exemption, and that exemption is load-bearing.** A leaf
card maps the whole 4x4 sheet across one 0.49 m quad *on purpose*. `mesh.py`'s
own header currently claims the chequerboard leaf grid of `ad-town-04` §4 was
this number — **it is not**; the card does not repeat, and "correcting" 0.49 m
to 2 m would put four canopies' worth of sprig on every card and make every
tree in the town worse. That claim should come out of the comment.

## Finding 7 — the fourth and fifth crazy pavings, which no pass has named

Once the mechanism was clear I went looking for it. `worley` used as a
**complete tessellation** appears in two more ground materials, and between
them they are the surface under the player in half the frames in the review
set:

- **`town_earth`** (`earth`, the town's default ground). `worley(30, "f2f1")`
  used directly as height makes every cell a raised plate — 100 % stone
  coverage. Its per-stone value was an independent `fbm(s, 46)`, a field at
  roughly the stone frequency but **not registered to the stones**, so its
  light and dark blur across the boundaries and every plate ends up the same
  value. Now ~35 % of cells are proud and the rest is earth, with the value
  keyed to `worley(metric="id")`.
- **`river_gravel`** (`gravel`, the ground at the foot of the enceinte).
  Identical. This is the surface in the bottom-right of **`bailey-walk-04`** at
  2 m from the eye, and it is `ad-town-04` §8's "crocodile skin". Now ~55 %
  coverage with visible silt between the stones; sheet spread **sd 7.6 ->
  11.6**.

Shingle is the one ground in the library that genuinely has no bond, so
`worley` is the right generator for it. Using it as a tessellation is what
turned it into a patio.

---

## Verification — every frame rendered by me, read as a PNG

Renders in `review/shots/uv-base/` (before my changes, after the previous
wave's UV work), `review/shots/uv-stone/`, `review/shots/uv-stone2/` and
`review/shots/uv-stone3/` (final). Compared against `review/shots/ad-town-04/`.

| frame | before | after | verdict |
| --- | --- | --- | --- |
| **`mere-walk-05`** — the AD's named frame | flat pale crazy-paving polygons; thatch a smooth cream membrane | a laid cobbled lane with joints, per-stone value and a kerb; thatch with real course structure and stem grain | **fixed** |
| **`t-square`** — the market place, 60 % of frame | the same crazy paving out to 30 m | a cobbled square; the near half now reads as a town | **fixed at the near half** — see below |
| **`bailey-walk-04`** — the "untextured 30 m run" | featureless | the curtain is coursed masonry with visible per-stone value | **fixed** |
| `bailey-walk-04` ground at the wall foot | crocodile skin | stones lying in silt, per-stone value reads | **improved, would not sign off** |
| **`t-aerial-sw`** — terracotta | one flat saturated orange | measurably more varied; browns and buffs now present | **improved, NOT closed** |

### What I would still not sign off

1. **The market place past ~12 m is a flat sandy plane.** `t-square`, the band
   behind the 1.75 m figure. The cobble pattern mips out completely and what is
   left is the sheet's mean, with the proud stones sitting on it like pebbles
   on a beach. This is the AD's *"past ~25 m the picture is one flat cream
   plane"* and **it is not a texture problem** — the plaza is `seg=12` quads
   over 34 x 32 m, so at 20 m the sampled mip is many levels down. It needs
   anisotropic filtering and a mip bias, or macro variation in COLOR_0. Faking
   it in the albedo would put a feature the size of the tile back in the tile.
2. **The terracotta is still predominantly orange from the air.** The batch
   split works and is visible, but COLOR_0 can only multiply DOWN from
   `TERRACOTTA` #B5603E, which is a very saturated orange to start from. To
   actually break the read the **base sheet has to be desaturated** and the
   strongest batch left at 1.0 — that moves the authored palette value and is
   an art-director call, not one to make unilaterally at the end of a wave.
3. **`river_gravel` at 2 m** is no longer a tessellation but still reads closer
   to a stone-chip mosaic than to shingle. Coverage wants to come down again
   and the plates want rounding.
4. **`cobble_wall`** now has real value spread and a real joint, but I have not
   seen it at close range in a frame — the venues that use it
   (`gatehouse`, `wellhouse`) were not in my render set. The sheet is right;
   the frame is unverified, and I am not claiming it.

### Three things I claimed to myself and the render said no

Recorded because `ad-town-04` caught five of these last wave.

- **Thatch stem direction.** `along="u"` looks wrong for a stem running down
  the slope and I changed it to `"v"`. The sheet came back with horizontal
  stems. `fibre` draws lines of *constant* `g`, and roof UVs are `(t along the
  eaves, s up the slope)`, so `"u"` was already right. Reverted, with the
  reason in a comment.
- **Thatch warp.** `0.30` is a fingerprint; `0.016` rendered as **perfectly
  parallel stripes**, the failure `fibre`'s own docstring names. `0.05`.
- **Thatch courses.** `20.0` (0.40 m) at full amplitude rendered as
  **corrugated iron** on `mere-walk-05` — the exact failure
  `roof._thatch_slope` warns about. `14.0` at half amplitude with double the
  wander.

### Instruments

- `python tools/uv_density.py` — 4 failures / 11 warnings over 102 materials.
  All four are trim (`nogging`, `straw`, `wool_crimson`, `canvas_amber`), none
  is a ground or roof surface. Every ground and masonry key is inside half a
  stop.
- `python tools/validate.py` — **1 failure**: `§7 mesh memory 243.2 MB exceeds
  the 240 MB budget`. **This is not mine** — I added no geometry, only
  materials and one COLOR_0 value — but it is over the cliff `ad-town-04`
  flagged at 99.75 %, and somebody should own it.

### Files

- `tools/assetgen/core/materials.py` — `cobblestone`, `cobble_walling`,
  `thatch_variant`, `town_earth`, `river_gravel`
- `tools/assetgen/core/roof.py` — `kiln_batch`, `_KILN_BATCH`, `_course_colour`
- `tools/uv_density.py` (new), `tools/validate.py` (`check_uv_density`)
- `docs/DECISIONS.md` — D-050
