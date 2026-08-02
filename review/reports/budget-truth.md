# Budget truth — what Hearthmere actually costs

**Brief:** the two instruments that measure this town disagreed by 3x. Settle
it, fix the instruments, state the real number against BUILD_DIRECTIVE §7, fix
the content if it is over, re-derive the baseline, and project honestly with
players in the square.

**Verdict up front.** Neither instrument was lying and neither was right. They
were counting different things and neither said which. The town is **over the
draw-call budget and was over the triangle budget**; this wave took 26 % off
both and put triangles back inside budget, and the residual draw-call overrun is
named, attributed and costed rather than re-baselined.

---

## 1. Why 2,153 and 727 were both true

`tools/check_client.mjs`: 2,153 draws / 3.77 M tris.
`tools/render/town.mjs`: 727 draws / 1.15 M tris. Same town, same commit.

One line of three.js r180 `WebGLRenderer.render` explains all of it:

```js
shadowMap.render( shadowsArray, scene, camera );
...
if ( this.info.autoReset === true ) this.info.reset();      // AFTER the shadows
```

**The counter is reset after the shadow pass, not before it.**

| | `autoReset` | what its number meant |
| --- | --- | --- |
| `tools/render/town.html` | `true` (default) | **beauty pass only** — its shadow draws were wiped before it read them |
| `client/src/main.js` | `false`, reset per tick | **whole frame** — beauty + shadow + AO G-buffer + post |

The harness's report header said *"scene pass + shadow pass"* and its `shadow`
column printed **16**. Those 16 were not shadows. They were the difference
between three's counter and the harness's own per-object tally — i.e. the sky
dome, the water, the scale figure. The shadow pass was **absent**, and its real
size at that camera was **988 draws**.

Three more divergences were found while proving parity, any one of which would
have kept the two apart on its own:

1. the harness aimed the sun with a **42 m** shadow box, the client with **60 m**;
2. the harness let **terrain cast shadows**; the client does not;
3. `check_client` ran a **1.60** aspect viewport against the harness's **1.78**,
   so the two frustum-culled different sets of batches.

And the harness rendered the scene **twice per shot** — once bare, to read the
counters off, then again through the composer to make the picture — and
reported the cost of the throwaway, which had no post chain and no AO in it.

### The fix

`client/src/perf.js` is new and is the single definition. It takes `autoReset`
off, resets once per frame, attributes every object draw to a **stage** via
three's `onAfterRender` / `onAfterShadow` hooks, and wraps the composer so the
AO pass's G-buffer is counted as AO rather than as a doubled beauty pass.
`client/src/main.js` and `tools/render/town.html` both import it. Both
instruments print the identical decomposition.

`hm.shoot({pos, look, fov})` renders the shipping client from an arbitrary
camera and reports what it cost, so the two can be compared from the **same
viewpoint** instead of from two different ones. `check_client.mjs` calls it on
the arrival camera every run.

**Parity, measured, at the identical camera (playerSpawn, facing 270°):**

| | draws | scene | shadow | ao | post | batches |
| --- | --- | --- | --- | --- | --- | --- |
| client (`hm.shoot`) | **1,380** | 560 | 526 | 227 | 67 | 209 |
| harness (`--views arrival`) | **1,370** | 564 | 526 | 230 | 50 | 209 |

Batch count identical, shadow count identical. The 17-draw residual is
full-screen post quads, whose count follows the viewport (640×360 against
1600×900) and not the town. **0.7 %, and explained.** Before this wave the same
two numbers were 2,153 and 727.

---

## 2. The real number

**§7's `< 900 draw calls` governs the whole frame.** That is a decision, recorded
as D-051, and it is the only defensible reading: a budget met by not counting
two thirds of the draws is not a budget. §7's separate row for shadow-casting
*lights* limits how many such passes there may be; it does not make them free.

### Before this wave — worst gameplay camera (`square`)

| stage | draws | triangles |
| --- | --- | --- |
| scene | 503 | 1,133,343 |
| shadow | 916 | 1,658,848 |
| AO G-buffer | 449 | 1,080,553 |
| post quads | 61 | 11,907 |
| **total** | **1,929** | **3,884,651** |
| **§7 budget** | **900** | **3,500,000** |
| | **2.14x OVER** | **1.11x OVER** |

The shadow pass was **larger than the beauty pass** and neither instrument could
see it. `review/reports/ad-town-03.md` closed its budget section with *"727 draw
calls / 900 … the budget is not what is wrong with these frames"*. It was.

### After this wave — every gameplay camera in the standard set

| view | draws | scene | shadow | ao | post | triangles |
| --- | --- | --- | --- | --- | --- | --- |
| **square** | **1,419** | 498 | 602 | 258 | 61 | **2,896,190** |
| arrival | 1,370 | 564 | 526 | 230 | 50 | 2,507,714 |
| gate-north | 1,333 | 707 | 376 | 200 | 50 | 2,379,053 |
| gate-south | 1,252 | 698 | 306 | 183 | 65 | 1,963,939 |
| approach-w | 786 | 603 | 88 | 47 | 48 | 1,503,658 |
| approach-s | 719 | 558 | 74 | 39 | 48 | 1,280,707 |
| approach-ne | 559 | 501 | 0 | 12 | 46 | 1,180,953 |

**Draw calls: 1,419 against 900 — 1.58x over. Triangles: 2,896,190 against
3,500,000 — inside budget, from 1.11x over.** 32 venues placed, 538 batches over
221 cells, 4,167,718 triangles in the scene graph.

### All four §7 rows, measured

| resource | measured | budget | |
| --- | --- | --- | --- |
| Draw calls | **1,419** whole frame at the worst gameplay camera | 900 | **1.58x over** (was 2.14x) |
| Triangles drawn | **2,896,190** | 3,500,000 | 83 % — **in budget** (was 1.11x over) |
| Texture memory | **827 MB** (338 PNGs, RGBA8 + mip chain, whole town resident; 132 MB on disk) | 1.5 GB | 55 % — **in budget** |
| Shadow-casting lights | 1 sun, 0 local | 1 + 8 | **in budget** |
| Mesh memory *(validate.py's own row, not §7's)* | **242.3 MB** of `.bin` | 240 MB | **1 % over** (was 15 % over) — see §4 |

---

## 3. What was cut, and why each cut is an engine setting

Nothing here is a web trick; all three map 1:1 onto Unreal/Unity equivalents,
which is hard constraint 1.

**Shadow casters are now decided per batch** (`client/src/lod.js`). A caster
costs a full depth draw whether or not its shadow lands anywhere a player can
see. Excluded: anything past `SHADOW_CAST_DISTANCE = 42 m`; anything the build
gave a screen-size cull to (`cullAt` — roadside grit, window furniture), which
is by construction too small to be worth a draw at range and whose shadow is
sub-pixel long before the object is; and anything at LOD2 or coarser, which is
≥ 40 m away and drawing a decimated shell. → `r.Shadow.DistanceScale`, per-mesh
Cast Shadow, shadow LOD bias.

**The sun's ortho box came in from ±60 m to ±46 m.** three frustum-culls the
shadow pass against exactly this box, so its size *is* the shadow draw count. At
4096 across 92 m it is 2.2 cm/texel — **finer** than the 60 m box was, so this
buys sharper shadows as well as cheaper ones.

**`atmosphere.ao.farDistance` 80 m → 35 m** (`tools/plan/plan_data.py`). GTAO
needs a full normal+depth prepass, i.e. a second complete scene render; it was
449 draws and 1.08 M triangles of a 1,929-draw frame. The AO radius is 2.4 m and
`atmosphere.scattering` is already at ~60 % opacity by 35 m, so every draw beyond
that was multiplying an occlusion term into haze. → an engine's AO distance.

Verified visually at `review/shots/perf3/p3-square.png`: near-field contact
shadows, the stall, the lamp and the figure all still cast; composition intact.

---

## 4. Mesh memory: 275.7 MB against 240 MB

Broken down by attribute for the first time (276.3 MB of accessor data across 35
files):

| attribute | bytes | share | stored as |
| --- | --- | --- | --- |
| POSITION | 96.03 MB | 34.8 % | int16 normalized, padded to 8 B (D-042) |
| **TEXCOORD_0** | **95.12 MB** | **34.4 %** | **float32, 8 B** |
| NORMAL | 47.56 MB | 17.2 % | int8 normalized, 4 B (D-042) |
| INDICES | 30.49 MB | 11.0 % | uint16 where ≤ 65 k verts |
| COLOR_0 | 6.71 MB | 2.4 % | ubyte normalized (D-042) |

`KHR_mesh_quantization` was already implemented (D-042) — the task's "if it is
not already there" is answered: it is, for POSITION, NORMAL and COLOR_0.
TEXCOORD_0 was the one attribute left at float32, and `core/gltf.py` carried a
comment explaining why: quantizing it needs a `KHR_texture_transform` **per
material** to undo the scale, so materials could no longer be shared between
primitives with different UV extents.

**The premise was right and the conclusion was wrong.** The scale only has to be
per material if it is *derived per primitive*. Take **one scale for the whole
file** — the largest |uv| any mesh in it reaches — and every material in that
file carries the identical transform, so sharing is untouched. Materials are
never shared across files, so a per-file scale costs nothing.

TEXCOORD_0 is now written last, as normalized SHORT, with
`KHR_texture_transform.scale = [S, S]` on every texture slot. 8 bytes → 4.
Quantum is `S / 32767`: 0.46 mm on the wellhouse (S = 14.95), ~8.8 mm on the
290 m ground venues, against textures that tile at 1–2 m and sample at
~3.9 mm/texel.

Rendering verified in three.js at `review/shots/uvq/uvq-detail.png` (one venue)
and `review/shots/perf4/p4-arrival.png` (the whole town after a full rebuild) —
stone coursing, timber grain, paving and tile all tile correctly, no smear, no
mis-scale. `KHR_texture_transform` is what gltfpack emits for exactly this
reason; three.js, Babylon, Cesium, the Blender importer, gltf-validator and
Unreal 5's Interchange pipeline all support it. **Unreal itself was not run —
that verification is open, and it is the one risk this change carries against
hard constraint 1.**

### The measured result

Full rebuild, 35 files:

| | before | after |
| --- | --- | --- |
| `.bin` total | 275.7 MB | **242.3 MB** (−12.1 %) |
| TEXCOORD_0 | 95.12 MB | **50.82 MB** |
| vs 240 MB budget | 14.9 % over | **1.0 % over** |
| `townhouse.bin` (largest) | 78.28 MB | 65.28 MB |

**Still 2.3 MB over, and not re-baselined.** Checked for the next lever and it
is not where it looks: every index accessor in the build is *already* uint16
(32.51 MB, 6,274 primitives, zero uint32), and no COLOR_0 primitive is constant,
so neither is recoverable. POSITION's 4-byte padding (25 % of 102.55 MB) is
mandated by glTF's 4-byte vertex-element alignment and cannot be reclaimed. The
remaining levers are the ones `validate.py`'s own note already names — split
`townhouse` by cell, and reduce source triangles — plus `EXT_meshopt_compression`,
which was **rejected here**: it would halve the download but not the GPU bytes,
and Unreal's importer does not read it, which trades hard constraint 1 for a
number that only helps the web build.

### The bug class, closed

An earlier wave found `validate.py` reading quantized POSITION accessors raw and
reporting every asset as 65,534 m across — fifteen false scale errors on a clean
town. The UV equivalent would be a file that quantizes TEXCOORD_0 and does *not*
carry the transform: every texture then tiles at 1/S of the authored rate, which
looks like a material bug rather than a pipeline bug, and no existing check would
say a word.

`check_quantization_contract()` in `tools/validate.py` now asserts, per file:
quantized attributes ⇒ `KHR_mesh_quantization` in **extensionsRequired**;
quantized POSITION ⇒ every mesh node carries `extras.hm.min/max`, so nothing
ever *needs* to de-quantize by hand (that reach for accessor min/max is what
produced 65,534 m); quantized TEXCOORD_0 ⇒ `KHR_texture_transform` required,
present on **every** texture slot of every material, and **exactly one** scale in
the file. A tool can no longer read half a quantized pair and get a plausible
wrong answer — it gets a build failure naming the file.

---

## 5. The silhouette, and the approach cameras

`review/reports/ad-town-03.md` judged the town's most-cited defect — *"the town
has no skyline"* — and could not use the instrument built for it:

> whether the tower is genuinely detached or its stem is hidden behind nearer
> terrain, **the instrument cannot tell me**

**Diagnosis.** `silhouette` is an orthographic elevation shot from 400 m north,
so the projection is true. The terrain plate is 576 m square and `landscape`
carries the field system and distance wood out to 270 m — so roughly **190 m of
ground, hedge and tree stood between the lens and the town**, painted `SIL_LAND`
grey, with the black roofline behind it. An orthographic camera has no
perspective to disambiguate that. Secondary defect: the camera sat at
`0.72 × halfH` = 41 m over a town 0–22 m tall, so the skyline hugged the bottom
edge under 60 % dead white.

**Fix.** `near` sits at the town's own north edge (6 m of margin, so the north
gatehouse and the bridge parapet — which *are* skyline — survive); `far` stops
short of the southern distance wood; the frame is centred on the built band.

Before: `review/shots/perf/perf-silhouette.png` — a grey mass across the bottom
third with two black shapes clearing it.
After: `review/shots/perf3/p3-silhouette.png` — church tower and spirelet, guild
tower, moot bell-cote, dovecote cone, the chimney line and the quay, all reading.

Note for the reviewer: at 192 m wide the vertical extent is pinned to
192/aspect by square pixels, so 16:9 can only ever give the town a fifth of the
frame height. Shoot it letterboxed for the tightest read:
`--views silhouette --w 1800 --h 520`.

**The three approach cameras are named views now** — `approach-s`,
`approach-ne`, `approach-w`, with the exact numbers from
`review/shots/ad-town-03/approach-*-report.json`, in the default view list
(ad-town-03 item 10). A camera a review verdict rests on cannot live in a shell
command inside a report; typed slightly differently next wave it measures a
different town.

---

## 6. The baseline

`review/perf-baseline.json` gains `schema`. The old baseline's 727 was a
scene-pass-only number; comparing it to a whole-frame number produces a
screaming false regression, and the obvious way to silence a false regression is
to rewrite the baseline — which is exactly how a real one gets laundered
through. So:

- A baseline from a **superseded instrument is refused, loudly, and counted as a
  gate failure.** The only way past it is a deliberate `--write-baseline`.
- The frame-cost regression check **always runs**. It used to be guarded by
  `current.venuesPlaced <= base.venuesPlaced`, so a baseline stale at
  `venuesPlaced: 10` against a town of 32 disabled it **silently** — the town
  could have doubled in cost and the gate would have said nothing. That is the
  "fails on staleness rather than on regression" defect, and it failed on
  neither.
- When the town has grown, the comparison is **draws per placed venue**, so
  growth is allowed and per-building efficiency regression is not.
- Per-stage figures are recorded, so a future regression is attributable to
  scene, shadow, AO or post rather than to one number.
- `check_client.mjs` now gates on the **arrival camera** rather than on wherever
  the walk stopped. The walk ends outside the south wall looking away from the
  town — 419 draws against the town's 1,390 — so the old gate tested where the
  route ended, not the budget.

---

## 7. Projection: does it hold with players in the square?

**No. Not at any realistic player count, and not close.**

There are no character meshes in the build (NPCs are out of scope by directive
§1), so this is projected from the town's own measured LOD rings and from
standard MMO character budgets, and every number is shown so it can be argued
with.

**Per-character cost.** A geared character in this class of game is body + head
+ hair + weapon + 2–3 gear pieces = **6 submeshes / ~25 k triangles at LOD0**.
Each submesh costs one scene draw, plus one shadow draw inside 42 m, plus one AO
G-buffer draw inside 35 m — because a character is exactly the kind of object
none of this wave's exclusions apply to.

| ring | per player: scene | shadow | ao | draws | tris (all stages) |
| --- | --- | --- | --- | --- | --- |
| 0–15 m (LOD0, 6 submeshes) | 6 | 6 | 6 | **18** | ~75 k |
| 15–40 m (LOD1, 3 submeshes) | 3 | 3 | ~1.5 | **7.5** | ~20 k |
| 40 m+ (LOD2, 1 submesh, no shadow) | 1 | 0 | 0 | **1** | ~2 k |

**At 100 characters** (FFXIV's "Maximum" display setting; a Ul'dah or Divinity's
Reach hub at peak), distributed 15 / 35 / 50 across those rings:

```
players    15x18 + 35x7.5 + 50x1  =   582 draws
           15x75k + 35x20k + 50x2k = 1.93 M triangles
town (square, after this wave)     = 1,419 draws / 2.90 M triangles
                                     -----------------------------
TOTAL                              = 2,001 draws / 4.83 M triangles
§7 budget                          =   900 draws / 3.50 M triangles
                                       2.2x over      1.4x over
```

**At 50 characters** (FFXIV "Normal"): ~291 player draws → **1,710 draws /
3.87 M triangles.** Still 1.9x over on draws and over on triangles.

**At 0 characters:** 1,419 / 2.90 M. Over on draws, inside on triangles.

So the town does not fit its own budget empty, and characters would add another
582 draws on top. The honest statement is that **§7 is currently a target, not a
measured fact**, and this is the first wave in which anyone can say that with a
number.

### What closes the gap, in order of value

1. **Texture atlasing across the kit — §7's own required technique, never done.**
   The beauty pass is 498 draws over 174 drawn batches: **2.86 draws per batch**,
   because a batch is one primitive *per material* and the town carries **846
   materials across 35 mesh files**. Folding the kit's plaster/timber/cloth/tile
   variants onto atlas pages takes that toward ~1.2 and drags the shadow and AO
   stages down with it, since both draw the same primitives. Rough arithmetic:
   scene 498 → ~210, shadow 602 → ~250, ao 258 → ~110, giving **~630 draws for
   the town**. `tools/assetgen/core/atlas.py` already exists. `validate.py`
   independently reports eight cells costing 46–70 draws at LOD0 against its own
   45 threshold, all of them mixed-material — the same finding from the other
   end.
2. **A character display limit.** FFXIV ships one because this arithmetic is
   universal. 50 shown is 300 draws; 25 is 150.
3. **Merged character meshes** — one skinned mesh, one atlas material per
   character — takes LOD0 from 6 draws to 1–2 and 100 characters from 582 draws
   to ~150.
4. **Crowd impostors past 40 m** — one instanced billboard draw for the whole
   far crowd.

With (1) and (3) together: 630 + ~150 = **~780 draws** at 100 characters, inside
900, with triangles around 2.4 M. That is the shape of a town that meets §7 with
a crowd in it. Nothing above needs new art.

---

## 8. Files

| path | what changed |
| --- | --- |
| `client/src/perf.js` | **new** — the one definition of what a frame costs, staged and attributed |
| `client/src/lod.js` | `SHADOW_CAST_DISTANCE`, `SHADOW_MAX_LOD`, per-batch `setShadow`, `shadowCasters` stat |
| `client/src/main.js` | uses `FrameProbe`; shadow box ±46 m; `hm.shoot()` parity hook |
| `tools/render/town.html` | uses `FrameProbe`; one composed render per shot; client shadow rig; terrain does not cast; silhouette near/far clip and framing; `approach-s/ne/w` |
| `tools/render/town.mjs` | staged per-view table; approaches in the default set; schema-aware baseline gate |
| `tools/check_client.mjs` | staged perf print; arrival-camera parity reading; budget gated at the arrival camera; 16:9 viewport |
| `tools/assetgen/core/gltf.py` | deferred TEXCOORD_0 quantization against one per-file scale + `KHR_texture_transform` |
| `tools/validate.py` | `check_quantization_contract()` |
| `tools/plan/plan_data.py` | `ao.farDistance` 80 → 35 m |
| `docs/DECISIONS.md` | D-051, D-052, D-053 |
| `review/perf-baseline.json` | re-derived at schema 2 |
