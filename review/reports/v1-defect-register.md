# v1 Defect Register

Forensic audit of the shipped v1 assets, produced for the v2 rebuild. Every
entry below was confirmed by **both** reading the generator and looking at a
render. Nothing here is inferred from code alone.

> **Baseline: commit `d36d31a`** ("Hearthmere: art direction, procedural asset
> pipeline, review harness, 15 venues"). Every `file:line` reference below is
> against that tree and was re-verified there after the audit completed. Read
> them with `git show d36d31a:<path>`.
>
> **Currency warning.** A v2 rebuild was running in this working tree
> concurrently with this audit. By the time the register was written, that work
> had already added `tools/assetgen/core/terrain.py`,
> `tools/assetgen/core/collision.py`, `client/src/terrain.js`,
> `client/src/collision.js`, and grown `tools/validate.py` from 223 to 997 lines
> with terrain, collision, road-intrusion and floating-mass checks — i.e. it has
> begun landing the remedies named in D-1, D-2, D-11 and D-12. Every venue module
> under `tools/assetgen/venues/` has also been rewritten. **The diagnosis below
> is a record of what v1 did wrong and why; do not read the line numbers against
> the current working tree.** The "what core/ is missing" sections should be
> treated as requirements to check off, not as a to-do list assumed untouched.

**Method.** All 10 venues rebuilt with `python tools/assetgen/build.py
--skip-textures` (329,834 tris, exit 0). All 9 non-NPC venues rendered with
`tools/render/shoot.mjs` at `gameplay,approach,detail,silhouette` into
`review/shots/v1audit/<venue>/`. `VenueContext.emit` was then monkeypatched in a
throwaway harness to capture the vertex cloud **and the generator file:line** of
all 760 emitted masses, and those were tested for ground support, roof/plate
agreement, mutual interpenetration, and intrusion into the authored street
corridors after applying each venue's `origin`/`rotationDeg` from
`content/town/hearthmere.json`.

Ordered by how much of the town each defect class affects.

---

## Verdict on the four reported symptoms

| Reported | Verdict | Real cause |
| --- | --- | --- |
| "no roads" | **Confirmed, worse than described** | Roads exist as geometry but are flat texture-mapped quads 0.11 m proud of a flat ground plane. Smith's Lane is a *dirt* ribbon on a *dirt* plane with no kerb — literally invisible. `core/mesh.scatter_cobbles()` (real per-stone paving) is defined and **called by nothing**. D-3 |
| "things are floating" | **Confirmed** | 87 of 760 masses have nothing within 0.10 m under their base. The named-and-shame cases are roof-mounted and wall-mounted props whose Y is a hand-typed constant. D-6, D-7 |
| "polygons/roofs aren't attached" | **Confirmed, one severe instance** | The Adventurer's Guild hall roof is placed at the top of the **stone** storey instead of the top of the **timber** storey — 3.10 m too low. It is buried inside the upper storey, cuts through the tower, and only a 4.1 m strip of a 12.6 m roof clears the wall head. D-5 |
| "the guild looks basic and is blocking the road" | **Confirmed, both halves** | *Basic*: because its roof is missing from the silhouette (D-5), the guild reads as a plain box with a crenellated tower. *Blocking*: the guild's east wall, plinth, quoins **and its entire training yard** stand inside Ford Road's 7 m carriageway. The yard straddles the centreline. D-8 |

---

## D-1 — Collision is one AABB per venue, so the town is a solid block

**Affects:** every venue (14/14 placements). This is the single largest defect.

`client/src/main.js:172-178` derives one axis-aligned box from each venue's
whole bounding volume:

```js
const box = new THREE.Box3().setFromObject(root);
if (box.max.y > 0.8) {
  colliders.push(new THREE.Box3(
    new THREE.Vector3(box.min.x + 0.2, 0, box.min.z + 0.2),
    new THREE.Vector3(box.max.x - 0.2, Math.min(box.max.y, 3.0), box.max.z - 0.2)));
}
```

Measured world colliders (computed from the built glTF accessor min/max plus the
town transform):

| Venue | Collider footprint | Area |
| --- | --- | --- |
| `streets` | x[-32.0, 32.0] z[-47.8, 47.8] | **6116 m²** |
| `market_square` | x[-16.8, 16.8] z[-15.8, 16.2] | 1075 m² |
| `guild` | x[-22.4, **+5.4**] z[-29.1, -14.8] | 396 m² |
| `stalls` | x[-9.4, 8.9] z[-14.1, 3.3] | 318 m² |

Consequences, all verified by arithmetic against `content/town/hearthmere.json`:

- The `streets` venue spans the gate (z=-48) to the south waymarkers (z=+48) and
  Mere Street's full width, and its gate is 6.7 m tall, so it passes the
  `box.max.y > 0.8` test and **seals a 6116 m² box over the entire town**.
- `playerSpawn` is `[0, 0, -44]` — *inside* that box. `player.js:140-156` pushes
  out along the shallowest axis, so the player is ejected to the box edge on
  frame one and can never re-enter the town.
- The guild's collider reaches x=+5.4, i.e. it covers Ford Road's whole
  carriageway (x ∈ [-3.5, 3.5]) for 14 m of its length, independently of
  geometry.

**Class of mistake:** *collision is inferred from a render bound rather than
authored.* A venue is a composition of many disjoint masses with walkable space
between them; its bounding box is the convex hull of the composition and
contains almost entirely walkable space.

**What core/ is missing:** there is no collision concept anywhere in
`tools/assetgen/core/`. `VenueContext` has `emit()` and `entity()` and nothing
that says "this mass is solid". `core/venue.py` never writes a collision file;
`content/collision/` does not exist.

> **v2 needs:** `ctx.collide(convex_or_box, tag)` on `VenueContext`, emitting
> `content/collision/<venue>.json`; a `ctx.emit_solid(mesh, ...)` convenience
> that registers geometry and its collider together so they cannot drift; and a
> build-time walkability check (flood fill from the spawn point to every
> `door.*` entity) that fails the build.

---

## D-2 — There is no terrain function; every generator hardcodes y=0

**Affects:** every venue, every prop, the client, and the whole town silhouette.

`client/src/main.js:207-210` builds the world as
`new THREE.PlaneGeometry(300, 300)` at `y = -0.01`. Every generator writes
literal Y constants against that plane — `kit.stone_plinth` puts its base at
y=0, `market_square._paving` builds at y=0, `streets._ribbon` hardcodes
`ROAD_LIFT = 0.10` (`streets.py:81`), `blacksmith.py:143` puts its yard at
y=0.01, `guild.py:619` puts its training-yard ring at y=0.012.

There is no `core/terrain.py`. Nothing can ask "what is the ground height at
(x, z)?", so nothing can sit on a slope, no street can drain, and BUILD_DIRECTIVE
§4's mandated 4 m north-south fall cannot be expressed at all.

**Class of mistake:** *the ground is an assumption baked into hundreds of
literals rather than a queryable function.* Every one of those literals becomes
a defect the moment terrain exists.

> **v2 needs:** `core/terrain.py` with a single deterministic `height(x, z)` and
> `normal(x, z)`, consumed by the client *and* by a `ctx.ground(x, z)` helper, so
> that "sits on the ground" is expressed as `ctx.ground(x, z)` and never as `0`.

---

## D-3 — Every paved surface is a flat quad with a tiling texture; the real cobble generator is dead code

**Affects:** all three streets, the market square, the pub apron, the blacksmith
yard, the guild training yard — i.e. every horizontal surface in the town.
**This is the direct cause of "no roads".**

`core/mesh.py:484` defines `scatter_cobbles(width, depth, asset_id, ...)`, which
builds individually jittered, domed, chamfered stones with a running bond, and
whose docstring says *"A tiled cobble texture on a flat plane reads as wallpaper
at grazing angles."* Grepping the whole repo:

```
tools/assetgen/core/mesh.py:484:def scatter_cobbles(...)
```

**One hit — the definition. It is called from nowhere.**

What ships instead:

- `streets.py:43-104` `_ribbon()` — flat quads, `LANES = 6` across, lifted to
  `ROAD_LIFT = 0.10`, UVs `(x*uv, z*uv)`. Zero relief.
- `market_square.py:139-157` `_paving()` — a 12×12 grid of flat quads at y=0,
  plus 340 loose boxes scattered *on top* at `y = h*rng.uniform(0.10, 0.34)`,
  which read as gravel lying on a floor rather than as paving.
- Smith's Lane has `"surface": "dirt"`, so `_ribbon` uses the **dirt** material,
  and `streets.py:149` only emits kerbs `if st.get("surface") == "cobble"`. The
  result is a dirt ribbon on a dirt ground plane with no edge treatment —
  invisible.

Renders: `review/shots/v1audit/market_square/market_square-detail.png` shows the
plaza as a perfectly flat slab meeting bare ground along a dead-straight
diagonal seam with no kerb, no verge, and specular streaking that only a flat
plane produces. `review/shots/v1audit/streets/streets-gameplay.png` shows Ford
Road as a featureless pale strip between two rows of kerbstones.

The triangle-budget argument in `market_square._paving`'s docstring (recorded as
D-006) is sound — 40,000 modelled cobbles is not viable. But the conclusion
drawn from it (a bare plane) is the wrong end of the trade. Note also that
`market_square.py:11-12`'s module docstring still claims *"Paving is real
per-stone geometry, worn into DESIRE PATHS"*, which the code does not do.

**Class of mistake:** *ground surfaces are authored as material, not as
construction.* A road is not a texture; it is a cambered build-up with a kerb, a
gutter, a verge and a transition to what it abuts.

> **v2 needs:** a `core/paving.py` that owns the road cross-section as a swept
> profile — carriageway camber, kerb, gutter channel, crossing stones, verge
> scatter, and a *blended* edge into terrain — driven by the same polyline the
> town JSON already authors. Modelled stones only in the 0–15 m LOD band and
> only along kerbs and desire paths; the field carried by material. Plus a
> `core/junction.py`, because the current `_ribbon` lays each street
> independently and nothing resolves where two roads cross.

---

## D-4 — `gable_roof` spends 95% of its triangles on tile courses that are geometrically coplanar, and the tile texture is rotated 90°

**Affects:** every tiled roof in the town — guild (×3), inn (×3 incl. dormers),
pub, blacksmith, shop_row (×3), 4 of 6 cottages.

`core/kit.py:255-307`. Two independent faults in one function.

**(a) The courses do not step.** Each course is
`M.box(seg*1.22, 0.055, d, 0.010, tile_mat)` rotated to the slope angle and
translated to `((x0+x1)*0.5, (y0+y1)*0.5 + 0.028, jitter)` — the `+0.028` offset
is applied in **world Y**, identically for every course, so all courses lie in
one plane. Measured on a test roof:

```
slope-normal offsets of all tile verts: min -0.0062 max 0.0488 spread 0.0550 m
tile tris in one roof: 3212 of 3388 total (95%)
```

The total spread perpendicular to the slope is 0.0550 m — exactly one slab
thickness. There is no lap, no step, no shadow line, and the eave is a dead
straight edge rather than the saw-tooth the docstring promises.

**(b) The tile texture runs the wrong way.** `M.box` computes UVs at build time
via `_planar_uv` on the *unrotated* slab, whose top face normal is +Y, giving
`U = x` (0.2 m, across one course) and `V = z` (the full ridge length). The
`terracotta_tile` material (`core/materials.py:252-287`) steps its courses along
V and runs its pan-tile barrel curvature along U. Mapped this way, the courses
run **down the slope** and the barrels run **along the ridge** — both 90° wrong —
and because every course slab samples the identical `U ∈ [-0.1, 0.1]` slice, the
same strip repeats unchanged from eave to ridge.

Confirmed visually: `review/shots/v1audit/pub/pub-approach.png` (and the 2×
crop) shows the roof as fine vertical corduroy from ridge to eave, one flat
plane, dead-straight eave, with a plain rectangular ridge box.

**(c) Dead code in the same function.** `kit.py:290-293` builds a shaped lathe
ridge capping, rotates it, scales it — and never adds it to `out`. The ridge
that ships is the plain `M.box(0.22, 0.10, d, 0.03)` on line 294.

**Class of mistake:** *decorative geometry is authored in world space instead of
surface space, so it is silently flattened by the frame it lives in; and UVs are
baked before the transform that gives them meaning.*

> **v2 needs:** a roof module that works in **slope-local space** — a
> `core/roof.py` owning a `RoofSurface` with `(along_ridge, up_slope, normal)`
> basis, so courses are offset along the surface normal and UVs are assigned in
> `(along_ridge, up_slope)` metres by construction. Add `Mesh.uv_from_frame(o, u,
> v)` so any generator can re-project UVs *after* placing geometry. Add a
> build-time check that a roof's deviation from its own slope plane is at least
> one course lap.

---

## D-5 — Roof height is a hand-typed constant rather than derived from the wall plate; the guild's is 3.10 m wrong

**Affects:** the guild catastrophically; it is one typo away in the other 8
roofs.

`core/kit.py:255` `gable_roof(width, depth, asset_id, pitch, overhang, ...)`
takes **no wall-head parameter**. It builds a roof whose eave sits at its local
y=0 and hands the caller the job of translating it to the right height. Every
venue does this by hand:

| Venue | Wall head | Roof translate | |
| --- | --- | --- | --- |
| `cottage.py:91` | `0.42 + eaves` | `0.42 + eaves` | ok |
| `inn.py:197` | `y3 = 8.95` | `y3` | ok |
| `pub.py:123` | `y_e` | `y_e` | ok |
| `blacksmith.py:189` | plate top 3.21 | `POST_H + 0.20` = 3.20 | ok |
| `shop_row.py:241` | `y2 = y1 + up_h` | `y2` | ok |
| **`guild.py:556`** | **`y_eaves = 8.25`** | **`0.55 + HALL_H` = 5.15** | **−3.10 m** |

The guild builds a stone storey to `y_up = 0.55 + HALL_H = 5.15` and then a
jettied timber upper storey on top of it to `y_eaves = y_up + UPPER_H = 8.25`
(both names are defined at `guild.py:265-266` and the walls are emitted at
`guild.py:272-283`, measured y[5.15, 8.25]). The roof is then translated to
`0.55 + HALL_H` — the top of the *stone* storey, not the top of the building.
`guild.py:559-562` puts the gable ends at the same wrong height.

Measured consequences:

- Hall roof occupies y[5.09, 9.79]. The upper-storey walls run to y=8.25. Only a
  **4.1 m strip of the 12.6 m-wide roof** clears the wall head; the rest is
  inside an open-topped box.
- The roof interpenetrates the entrance-bay roof (`guild.py:492`) by **42.3 m³**
  and passes through the tower's side walls (`guild.py:371`, `guild.py:375`).
- What the player sees is a thin terracotta band emerging at the *jetty line*,
  under the timber wall, and a flat-topped building.

Renders: `review/shots/v1audit/guild/guild-silhouette.png` — the guild's
silhouette contains no roof triangle at all over the hall, only the small
entrance-bay gable and a chimney. `review/shots/v1audit/guild/guild-approach.png`
and the 2× crop show the upper storey's top edge cut bare against the sky.

**This is also the whole answer to "the guild looks basic."** A 19 × 11.5 m
hero building whose primary roof mass is invisible reduces to two boxes and a
tower.

**Class of mistake:** *the roof is authored as an independent prism positioned by
an eyeballed Y offset rather than derived from the structure it caps.* Eight
callers got the arithmetic right and one did not, and nothing in the pipeline
could tell the difference.

> **v2 needs:** the wall plate to be a first-class object. A `core/building.py`
> with a `Building` that accumulates storeys and **returns its own plate height**,
> so `roof = b.roof(pitch=...)` cannot be given the wrong Y — there is no Y to
> give. `gable_roof` should take a `plate_y` and assert it against the storeys
> registered on the same building, and the junction (wall plate, eaves board,
> oversailing overhang, closed gable) should be generated as one piece rather
> than as three independent calls the caller must align.

---

## D-6 — Roof-mounted objects are positioned by hand-typed Y too, so chimneys are buried or start in mid-air

**Affects:** 5 of 9 roofs.

- **shop_row `shop_row.py:249-252`** — `ch.translate(..., y2 - 0.2, ...)` with
  `height = 2.2 + srng.uniform(0, 0.6)`. Measured: all three chimneys top out at
  **y = 9.60**; the three ridges are at **9.83 / 10.46 / 11.56**. Every chimney
  is shorter than its own ridge and is placed within z = ±0.5 of it. All three
  are completely buried. `review/shots/v1audit/shop_row/shop_row-silhouette.png`
  shows three bare trapezoids with **zero** vertical interest above the eaves —
  a direct Art Bible §6 "secondary tier reads at 30 m" failure.
- **guild `guild.py:515-518`** — the hall chimney's base is at y=8.05, which is
  2.90 m above the hall's stone-storey ceiling and 1.22 m below the roof surface
  at that point. It is carried by nothing; it begins in mid-air inside the roof
  void. The `prop.chimney` smoke entity is registered at y=12.45 on a stack with
  no flue beneath it.
- The inn (`inn.py:229-236`) and pub (`pub.py:132-136`) get this right, and both
  carry comments recording that they got it *wrong twice first*
  ("this stack finished 0.31 m below its own ridge and was buried in the roof").
  The same fix was rediscovered independently in two venues and never lifted
  into core.

**Class of mistake:** *"clears the ridge" is re-derived by hand at every call
site from constants the caller has to reconstruct* (`((D2 + 1.0) * 0.5) * pitch`
appears verbatim in inn.py and in a subtly different form in pub.py, with a
comment in each explaining the trap).

> **v2 needs:** `RoofSurface.point_at(x, z) -> y` and
> `RoofSurface.penetrate(footprint, clearance) -> Mesh`, so a chimney is
> *cut through* a roof rather than positioned near it: the API returns the stack
> base at the ceiling, the flashing, the hole in the roof plane, and the required
> height to clear the ridge. No caller should ever type a chimney Y again.

---

## D-7 — Wall-mounted and hung objects have no fixing and no derived attachment point

**Affects:** every venue. 87 of 760 emitted masses (11%) have nothing within
0.10 m under their base.

Verified individual cases:

- **`guild.py:603-605`** — the comment says *"Lantern on a bracket beside the
  doors."* **No bracket is emitted.** The lantern is placed at
  `(PORCH_W*0.5 - 0.35, 0.55 + 2.5, zf - PORCH_D - 0.05)` = measured
  x[2.1, 2.2] y[3.05, 3.41] z[-7.8, -7.6], while the bay face it should hang on
  is at z = −7.0. It floats **0.7 m clear of the wall, 3 m up, attached to
  nothing.** Visible in `guild-approach.png` (crop `g_roof.png`, left of the
  doorway).
- **`guild.py:667-672`** — the straw target butts. `lathe(...).rotate_x(-0.22)`
  then `.translate(..., 0.30, ...)`. Computed lowest vertex: **y = 0.248**. Both
  butts hover a quarter of a metre above the yard. Visible in crop `g_yard.png`.
- **`guild.py:532-540`** — the tower banners' hanging poles sit at
  `tz - TOWER_W*0.5 - 0.10`, i.e. 0.10 m off a tower face that is at
  `tz - TOWER_W*0.5`, with no bracket, corbel or ring.
- Aggregate by venue (unsupported emits / total): guild 35/114, shop_row 18/118,
  pub 14/36, inn 9/49, blacksmith 8/103, cottage 3/44.

**Class of mistake:** *an object's attachment is expressed as a coordinate the
author computed, not as a relationship the pipeline can check.* When the author
also writes a comment describing the fixing, nothing verifies the fixing exists.

> **v2 needs:** an attachment API — `ctx.mount(obj, surface, u, v, kind="bracket"
> | "corbel" | "ring" | "nail")` that (a) derives the position from the surface
> it is given, and (b) **emits the hardware**, so a mounted object physically
> cannot exist without its fixing. Plus a global support check in the build (not
> opt-in — see D-11) that fails on any mass with no contact within tolerance.

---

## D-8 — No generator knows where the streets are, so five venues stand in the carriageway

**Affects:** guild, shop_row, pub, stalls, market_square.

`content/town/hearthmere.json` authors `streets[]` with paths and widths, and
`venues[]` with `origin`/`rotationDeg`. **Nothing cross-checks the two.** Venue
modules build in local coordinates and are placed by the client; no generator
ever loads `streets[]` except `streets.py` itself.

Vertices inside an authored carriageway between y=0.02 and y=2.4, after applying
the town transform:

| Venue | Street | Generator site | Closest approach to centreline | Height |
| --- | --- | --- | --- | --- |
| **guild** | ford_road | `guild.py:692` (training yard) | **0.01 m** | 2.14 m |
| guild | ford_road | `guild.py:380` (tower quoins) | 2.11 m | 2.12 m |
| guild | ford_road | `guild.py:296` (hall quoins) | 2.70 m | 2.25 m |
| guild | ford_road | `guild.py:217/234/244/258` (plinth + hall walls) | 3.00 m | 0.57 m |
| **shop_row** | ford_road | `shop_row.py:59` (shop front) | **0.19 m** | 2.01 m |
| shop_row | ford_road | `shop_row.py:159`, `:78`, `:105`, `:115` | 0.21–0.80 m | up to 2.4 m |
| **pub** | mere_street | `pub.py:71`, `:77`, `:109` | **0.05 m** | 2.14 m |
| stalls | mere_street | `stalls.py:1867` | **0.00 m** | 2.40 m |

Ford Road's carriageway is x ∈ [−3.5, +3.5]. The guild's hall wall face lands at
x = −3.0 and its quoins at x = −2.7 — 0.8 m inside the road. The tower quoins
reach x = −2.11, 1.4 m inside. And the **training yard** (dirt ring, three pells,
weapon rack, two straw butts, a nine-post fence) occupies world
x ∈ [−3.0, +5.6], z ∈ [−27.3, −19.8]: **it straddles Ford Road completely,
including a waist-high fence built across it.**

`hearthmere.json`'s guild entry carries a comment saying the guild was
*deliberately moved west of the centreline* to stop it blocking the road. The
move relocated the hall — but the training yard is authored at
`YX = HALL_W*0.5 + 4.0` in **guild-local** coordinates, so it moved west with the
building and straight onto the road. The fix addressed the symptom in world
space while the cause lived in local space.

**Class of mistake:** *layout is authored in two coordinate systems with no
shared arbiter.* The town JSON knows where roads are; the generators know where
masses are; nothing holds both.

> **v2 needs:** the street network as a queryable object in core —
> `core/streets.py` exposing `clearance(x, z) -> distance to nearest carriageway`
> and `is_carriageway(x, z)`. `ctx` should carry the venue's world transform so a
> generator can ask *in world space* whether it is about to build on a road, and
> the build must **fail** (not warn) on any solid mass inside a carriageway or
> within the doorway approach of another venue.

---

## D-9 — `emit`-before-`translate` silently buries duplicate geometry

**Affects:** every cottage (×6 instances) and every shop unit (×3).

The `ctx.emit()` API takes geometry whose transform is already baked, so the
idiom is *build → translate → emit*. Omitting the translate is invisible: the
object lands at the venue origin, inside the building, and nothing complains.

```python
# cottage.py:101-104
ctx.emit(K.door_frame(), "oak_dark")     # never translated — buried at origin
frame = K.door_frame()
frame.translate(door_x, 0.42, zf + 0.02)
ctx.emit(frame)                          # the real one
```

```python
# shop_row.py:201-204
ctx.emit(K.stone_plinth(w + 0.1, DEPTH + 0.2, 0.35), "stone")   # never translated
pl = K.stone_plinth(w + 0.1, DEPTH + 0.2, 0.35)
pl.translate(x + w * 0.5, 0, 0)
ctx.emit(pl, "stone")                                            # the real one
```

The shop_row case stacks three full-size plinths on top of each other at the
venue origin — the 18–20 m³, 100%-containment hits in the interpenetration scan.
Cost: 176 tris × 6 cottages = 1,056 stray tris, plus 3 buried plinths.

**Class of mistake:** *placement is a mutation applied after construction, so
"forgot to place it" is indistinguishable from "meant it to be there".*

> **v2 needs:** `ctx.emit(mesh, at=(x, y, z), rot=..., ...)` as the *only*
> sanctioned form, so placement is an argument rather than a prior mutation, and
> an unplaced emit is a missing required keyword rather than a silent default.

---

## D-10 — Texture seeds come from Python's salted `hash()`, so the town is not reproducible

**Affects:** all 40+ material sets, i.e. the entire visual appearance.

Hard constraint #3 is *"Seed every RNG. Derive the seed from the asset ID."*
`core/mathx.py:19-26` implements exactly that with blake2b and documents why:
*"Uses blake2b rather than hash() because Python salts str hashing per process,
which would silently break determinism across runs."*

Both texture call sites ignore it:

```python
# core/venue.py:73
MAT.LIBRARY[key](name=key, size=1024, seed=abs(hash(key)) % 9973).write(TEX_DIR)
# tools/assetgen/build.py:60
fn(name=key, size=size, seed=abs(hash(key)) % 9973).write(TEX_DIR)
```

Measured across three consecutive interpreter runs:

```
plaster -> 3675   terracotta -> 6124
plaster -> 1971   terracotta -> 14
plaster -> 2387   terracotta -> 6171
```

Delete `assets/textures/` and rebuild and you get a **different town** — different
plaster crackle, different cobbles, different tile firing variance. The only
reason this has not been noticed is that `build.py:56` skips textures whose PNGs
already exist, so the non-determinism is frozen into whatever the first run
happened to produce. Review diffing across iterations is therefore unreliable by
construction.

**Class of mistake:** *core provides the correct primitive and the call sites
bypass it.*

> **v2 needs:** `seed_from()` to be the only path — delete the `hash()` call
> sites, and add a CI check that greps for `hash(` and unseeded
> `default_rng(` in `tools/`. Better: make `MaterialSet.__init__` require an
> asset id and derive the seed itself, so a seed cannot be passed at all.

---

## D-11 — The occlusion tripwire is opt-in, one-directional, and covers 6 of 760 emits

**Affects:** the reliability of every other check in this register.

`core/venue.py:87-133` `check_occlusion()` is a genuinely good idea with a
docstring that names the exact bugs it was written to catch — buried chimneys,
an entombed counter, lancets inside walls. In practice:

- It only tests emits carrying an explicit `label=`. **6 call sites** in the
  whole town: `blacksmith.py:201`, `guild.py:419`, `guild.py:518`,
  `guild.py:700`, `inn.py:236`, `pub.py:136`.
- It only tests against emits carrying `container=`. **2 call sites**:
  `inn.py:198` and `pub.py:124`.
- **The guild's roof is not a container**, which is precisely why the guild's
  chimney (D-6) and its 3.10 m-misplaced roof (D-5) both shipped. The one venue
  the check was written for is the one it does not cover.
- The test is `hi[1] <= ohi[1] + 0.02` — "does the element clear the container's
  top". It detects *too low* and is blind to *too high*, *floating*, *offset
  sideways*, and *not attached to anything*.

The docstring's justification for opt-in is that a blanket AABB sweep produced
~40 false positives per build. That is true of an AABB containment sweep — but it
is an argument against that particular test, not against automatic checking. The
column-contact test used for this audit produced actionable results across all
760 emits.

**Class of mistake:** *the correctness check is opt-in, so it protects exactly
the cases someone already suspected.*

> **v2 needs:** checks that run on everything by default, with an explicit
> `ctx.emit(..., expect="floating")` escape hatch for the handful of legitimate
> cases (hanging signs, banners, smoke). Specifically: support/contact,
> roof-to-plate agreement, carriageway intrusion, and duplicate-at-origin. All
> should **fail the build**, not print a line the build then reports success
> after.

---

## D-12 — `validate.py` checks none of the above, and two of its documented checks do not exist

**Affects:** the whole quality gate.

`CLAUDE.md` documents `make validate` as *"schema + scale + palette +
anachronism checks"*. Reading `tools/validate.py` (223 lines): there is **no
palette check and no anachronism check**. The only occurrence of the word
"palette" is in the module docstring.

What it does check is per-file and coarse:

- `validate.py:80` — `if lo[1] > 0.35: warn(...)` tests only the **whole venue's**
  lowest point. A single floating chimney, lantern or straw butt can never trip
  it, because the venue's plinth is on the ground.
- `validate.py:72` — footprint warning, with `streets` explicitly exempted via
  `TOWN_WIDE` — the exemption is granted to the exact venue whose town-wide span
  causes D-1.
- `validate.py:149-176` `check_town()` — only checks whether two venues share an
  *identical rounded origin*. It does not test footprint overlap, road
  intrusion, or reachability.
- Nothing checks roofs, contact, collision, or interpenetration.

> **v2 needs:** validation to move from "per-file glTF sanity" to "town-level
> structural conformance", and the checks in D-11 to live there.

---

## D-13 — The town has 16 roofed masses against a target of 75–95, and no whole-town render exists

**Affects:** the composition, which is the thing every per-venue sign-off could
not see.

Counting roofed building masses from `hearthmere.json` placements: guild 3, shop
row 3, cottages 6, inn 1, pub 1, blacksmith 1, gate 1 = **16**.
BUILD_DIRECTIVE §5 targets 75–95.

`tools/render/` contains `shoot.mjs` (one venue in isolation), `viewer.html` and
`town.html`. There is **no `town.mjs`**. Two stale whole-town stills exist
(`review/shots/town-arrival.png`, `town-square.png`) with no generator that
reproduces them. Every defect in this register that is *between* venues — D-1,
D-8, and the guild's road blocking — is invisible to the only rendering tool
that exists, which is why they all shipped through nine `ACCEPT` reviews in
`review/reports/`.

> **v2 needs:** `tools/render/town.mjs` as a *gating* tool, per BUILD_DIRECTIVE
> §8: the arrival frame, ortho top-down, aerial obliques, and an eye-height walk
> route. No venue sign-off should be possible without the town shot that contains
> it.

---

## D-14 — `Mesh`/`Group` transforms are about the world origin, with no pivot concept

**Affects:** any generator that transforms after placing. Confirmed instance:

```python
# pub.py:123-128
roof.translate(0, y_e, 0)
roof.scale(1.0, 0.94, 1.0)     # scales the Y POSITION too, not just the shape
roof.rotate_z(0.012)           # rotates about the world origin, ~4 m below the roof
roof.translate(0, 0.10, 0)     # hand-tuned correction for the above
```

The author wanted a sagging ridge. `scale` multiplied the roof's *height above
ground* by 0.94 (dropping it 0.16 m), `rotate_z` swung it sideways about a point
four metres below it, and the `+0.10` on the next line is an empirical patch for
the combination. The result happens to look acceptable; the method does not
generalise.

**Class of mistake:** *the transform API has no pivot, so "deform this object"
and "move this object" are the same operation.*

> **v2 needs:** `Mesh.transform_about(point, matrix)` and a `Group` that carries
> its own origin, so `scale`/`rotate` default to the object's own centre or a
> named anchor.

---

## D-15 — Smaller confirmed items

- **`core/mesh.py:478-480`** — `beam(axis="z")` builds a `plank`, assigns it to
  `m`, then immediately overwrites `m` with a `box`. The plank is dead.
- **`core/kit.py:290-293`** — the shaped ridge-capping lathe is built, rotated,
  scaled, and never added to the group (see D-4c).
- **Thatch reads as green folded card.** `core/kit.py:694-783` `thatch_roof`
  builds a prism whose docstring says thatch's character is *"the absence of any
  hard edge"*; the output has a hard crease at every one of its 10 segments and a
  hard-chamfered eave roll. `core/materials.py:415-427` tints
  `P.HERB_GREEN` at 0.45 strength over a broad mask, so the reed base `#B9975B`
  reads olive. See `review/shots/v1audit/cottage/cottage-approach.png`.
- **`market_square.py:11-12`** — module docstring claims per-stone paving that
  the code does not build (see D-3).
- **`kit.timber_frame_wall`** has no top plate cap, so a storey's walls terminate
  in a bare cut edge — which is what makes the guild's open-topped upper storey
  read as unfinished rather than as damaged.

---

# What in `core/` is good and must be preserved

These are load-bearing and correct. Build v2 on them.

### `core/mathx.py` — keep entirely, unchanged
- `seed_from()` — blake2b, process-stable. This is the correct determinism
  primitive and the only reason D-10 is a call-site bug rather than a design bug.
- `rng_for()` — the sanctioned RNG accessor.
- `perlin2()` / `fbm()` / `worley()` / `ridged()` — all tileable by construction;
  `worley()`'s 3×3-neighbourhood optimisation is the difference between a 2-minute
  and a multi-hour texture build.
- `smoothstep()`, `normalize01()`, `gradient_v()`, `jitter()`.

### `core/materials.py` — keep the framework, it is the strongest part of v1
- `MaterialSet` and its channel model (albedo / roughness / metalness / height →
  normal / AO / emissive) is exactly right.
- `MaterialSet.rough(base, broad_amp, fine_amp, broad_freq, fine_freq)` — the
  two-noise-scale roughness rule from Art Bible §5, implemented as a primitive
  rather than as a convention. Keep verbatim.
- The wear-logic methods are the highest-value API in the repo and are
  physically motivated exactly as the Art Bible demands:
  `ground_splash()`, `water_streak()`, `touch_polish()`, `cavity_dirt()`,
  `edge_wear()`.
- `_normal_from_height()` — wrapped central difference, keeps tiling materials
  seamless.
- The ORM packing contract (R=occlusion, G=roughness, B=metalness) in
  `gltf.material_from_set()`.

### `core/gltf.py` — keep entirely
- Hand-written writer, byte-stable by design, no library version can silently
  rewrite the repo. `_accessor(..., minmax=True)` on POSITION is what made this
  audit's bounding-box work possible without re-running the generators.
- `write_gltf()` keeping textures as inspectable PNGs on disk is correct for a
  review loop.

### `core/mesh.py` — keep the primitives
- `box(sx, sy, sz, chamfer)` — a **true** 12-edge + 8-corner chamfer with the
  chamfer clamped to `0.45 * min(dim)` so thin members cannot invert. This is the
  workhorse and it is correct.
- `lathe()` — note specifically that its U is **arc length in metres**, not
  normalised angle. That fix (documented in the source) is what keeps texel
  density consistent between a turned column and the flat wall beside it. Do not
  regress it.
- `prism()`, `plank()` (grain-aligned UVs), `cylinder()`, `quad()`.
- `Group` as a multi-material assembly that keeps per-material batching through
  merges — this is both correct authoring and the batching the renderer wants.
- `scatter_cobbles()` — currently dead (D-3), but the implementation is right.
  **Revive it**, don't rewrite it.

### `core/kit.py` — keep the vocabulary, rebuild the roofs
Good and reusable as-is:
- `timber_frame_wall()` with the `square/close/cross/herring` style axis and, in
  particular, `_subtract_rects()` — proper guillotine subtraction of openings from
  the plaster infill, plus `rail_at()` breaking horizontals across openings. This
  is real construction logic and it was hard-won.
- `plank_door()`, `door_frame()`, `leaded_window()` (with the shutter hanging at
  an uneven angle), `jetty()`, `stone_plinth()`, `gable_end()`.
- `sign_bracket()` / `hanging_sign()` / `lantern()`.
- The prop set: `barrel()`, `crate()`, `sack()`, `rope_coil()`,
  `trestle_table()`, `bench()`, `leaf_cluster()`, `planter_plants()`.
- The Art Bible §3 constants at the top of the module (`DOOR_W`, `DOOR_H`,
  `FLOOR_H`, `SILL_H`, `POST`, `CHAMFER_ARCH`, `CHAMFER_PROP`) — keep, and extend
  this pattern so nothing is a bare literal.

### `core/venue.py` — keep the contract, extend the responsibilities
- The `NAME` / `CELLS` / `build(ctx)` venue contract, and `ctx` owning material
  registration + glTF assembly, is the right shape and is why nine
  separately-authored venues share one material vocabulary.
- `material()` raising `KeyError` on an unknown key with the message *"Add it to
  materials.LIBRARY rather than inventing one in a venue module"* — this is the
  cohesion guard, keep it.
- `entity()` and the entity-record schema.

### Elsewhere
- `tools/render/shoot.mjs` — the headless harness itself is solid (Chromium
  resolution fallback, `__ready` handshake, console-error capture, per-view
  screenshots). It needs a `town.mjs` sibling, not a replacement.
- `content/town/hearthmere.json` as the single authored source of layout,
  lighting and streets, read by both the client and the render harness (D-009).
  Keep this; the v2 problem is that too few consumers read it, not that it exists.

---

# What in `core/` is structurally wrong for a 90-building town

These do not scale and should be replaced rather than patched.

1. **`kit.gable_roof()` is unfixable in place.** It has no concept of the
   structure it caps (D-5), it builds courses in world space so they flatten
   (D-4a), and it bakes UVs before the transform that gives them meaning (D-4b).
   At 90 buildings it also becomes a budget problem: 3,212 tris of *invisible*
   course geometry per roof × 90 = 289k tris that render as a flat plane. Replace
   with `core/roof.py` owning a slope-local `RoofSurface`.

2. **`VenueContext` is a per-file exporter, not a town builder.** One venue = one
   glTF = one node = one draw-call group = one collider. That model gives:
   - the town-sized collider of D-1,
   - `client/src/main.js:169` bucketing an entire venue into **one** 16 m cell by
     its origin, so cell culling does nothing useful,
   - no path to per-cell per-material static batching or GPU instancing
     (BUILD_DIRECTIVE §7 requires both),
   - no LOD chain — nothing in core emits more than LOD0.

   At 90 buildings this is the binding constraint. v2 needs an *instancing* model:
   generators emit **kit pieces and prototypes**, the town assembles
   **placements**, and export is per-cell rather than per-venue.

3. **There is no ground.** No `core/terrain.py`, no `ctx.ground(x, z)` (D-2).
   Every Y in the repo is measured from an implicit flat plane. On a town with a
   4 m fall this is not a bug list, it is a rewrite of every literal — so the
   terrain function must exist before any v2 geometry is authored.

4. **There is no collision authoring** anywhere in core (D-1). Add it before the
   first venue, not after.

5. **There is no attachment/derivation vocabulary** (D-5, D-6, D-7). Core exposes
   only `translate`/`rotate`/`scale` on absolute coordinates, so every
   relationship — roof-on-plate, chimney-through-roof, lantern-on-wall,
   sign-on-bracket — is re-derived by hand at every call site. Nine venues
   produced nine hand-derivations, six of them with comments recording the two
   attempts it took to get right. That is the single most repeated failure mode
   in v1 and the highest-leverage thing to fix. Every relationship should be a
   call that returns geometry *and* the hardware that makes it physical.

6. **`Group`/`Mesh` have no pivot** (D-14), so transforms cannot express
   "deform in place".

7. **`core/npc.py` (215 lines)** — out of scope per BUILD_DIRECTIVE §1; delete
   with `venues/townsfolk.py`.

---

## Artefacts produced by this audit

- `review/shots/v1audit/<venue>/<venue>-{gameplay,approach,detail,silhouette}.png`
  — 36 renders, 9 venues, locked 09:30 rig, 1.75 m scale figure present.
