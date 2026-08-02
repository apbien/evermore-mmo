# Instruments, determinism and the budget — wave 06

**Owner of this report:** the instruments agent. Everything below is measured on
this machine, in this checkout, and every number has the command that produced
it beside it. Where I did not measure something I say so.

---

## Headline

Two bugs, and between them they account for every instrument disagreement in
`ad-town-05` **and for at least one of the visual regressions that pass blamed on
an asset**.

1. **The build was not deterministic, and it was one line.**
   `venues/landscape.py:670` seeded its ground-patch lattice from
   `abs(hash(asset_id))`. Python salts `str` hashing per process, so every
   ground patch in Hearthmere — and every tree, hedge and verge scattered
   against one — came out different on every build. Fixed, verified
   byte-identical over two builds, and gated.

2. **The perf harness was not sampling the previous frame's LOD state. It was
   rendering with a broken shadow cascade.**
   `ad-town-05` §12's five probe runs are reproduced exactly here, and the
   diagnosis in that section is wrong in a way that matters: the LOD state is
   *identical* in both orders. What leaked was `client/src/shadows.js`'s
   `fitSingle()`, which parks cascades 1..n on a 0.1–0.2 m slab, and three's CSM
   `_updateShadowBounds()` — which restores every cascade's `left/right/top/
   bottom` and **never its `near`/`far`**. So the moment any review ran a plan,
   an aerial or a silhouette, **cascade 1 stopped rendering for the rest of the
   session** — in the *picture* as well as in the count.

   The standard view list opens with `plan`. **Every gameplay frame the standard
   command has ever produced is missing its 5.4–30 m shadows.** Verified in frame
   in §9: in pass 05's `t-square` nothing casts a shadow except the 1.75 m
   figure; with the fix the fountain, the butcher's pitch, the market oak and the
   buildings all do.

   *I checked whether this also explains `ad-town-05` §4's missing dapple at
   `t-gate-south`. It does not — I re-shot that camera and there is simply no
   tree near the south gate in this build. Two different findings that produced
   the same symptom; the tree is genuinely absent and belongs to whoever plants
   it. What the determinism fix guarantees is that once planted it will still be
   there after the next rebuild.*

### Reproduce everything below

```
python tools/determinism.py --check-only        # instant source lint
python tools/determinism.py --venue landscape   # the full gate, scoped
python tools/assetgen/build.py --skip-textures
python tools/validate.py
node tools/render/town.mjs --out review/shots/town --label t --allow-missing
node tools/check_client.mjs                     # reads review/parity.json
```

---

## 1. Determinism — FIXED, verified, gated

### The measurement

Hashed `assets/meshes/`, `content/collision/`, `content/entities/` (482 files),
ran `python tools/assetgen/build.py --skip-textures` (2 m 37 s), re-hashed:

```
changed vs pre-build: 2
['assets/meshes/landscape.bin', 'assets/meshes/landscape.gltf']
```

Rebuilt `landscape` alone again — **different again**. So one venue, every run.

### The cause

`tools/assetgen/venues/landscape.py:670`

```python
seed = abs(hash(asset_id)) % 9973          # <- process-salted
```

fed `_lattice()`, which is the corner-offset grid under `_surface_patch` — every
grass verge, yard, garden and ground cover in the town, and the scatter that
sits on them. `core/mathx.py` has provided `seed_from()` (blake2b) for exactly
this since the project began, and `build.py`, `core/venue.py` and
`venues/streets.py` all carry comments warning against `hash()`. The warning
existed; nothing checked.

### The fix

`seed_from(asset_id) % 9973`, plus the import. Verified:

```
build landscape -> 5596c638... / 15a174c0...
build landscape -> 5596c638... / 15a174c0...      byte-identical
```

### The gate — `tools/determinism.py` (new)

```
python tools/determinism.py                 # full gate
python tools/determinism.py --check-only    # source lint only, instant
python tools/determinism.py --venue landscape
```

Three things, deliberately:

- **A source lint**, AST-parsed (not grepped — the warnings against `hash()` live
  in the docstrings of the modules that do it right, so a text search flags the
  cure as the disease). Any call to builtin `hash()` under `tools/assetgen/`
  fails. Instant, so it can run everywhere.
- **Two builds under two different `PYTHONHASHSEED` values**, compared byte for
  byte. Two builds in one hash regime can agree by luck; seeds 0 and 1 cannot.
  That makes the catch guaranteed rather than probabilistic.
- **A staleness comparison** against what was on disk before it started, so "a
  generator was edited and nobody regenerated" is reported as its own, different
  failure.

Exit 0 clean · 1 nondeterministic · 2 stale · 3 build failed.

Also wired into `tools/validate.py` as `check_determinism_sources()`, so the lint
half runs on every validate at no cost.

**The gate, run against the venue that was broken:**

```
source lint: clean — every generator seeds through core.mathx.seed_from
  build PYTHONHASHSEED=0: exit 0 in 71s
  build PYTHONHASHSEED=1: exit 0 in 67s
  build 1 vs build 2 (DETERMINISM): identical
  committed vs rebuilt (STALENESS): identical
PASS
```

Its first run also found something I want on the record, because it is a fact
about how this project works rather than about the build: it reported
`terrain.bin` changing between two `--venue landscape` builds. `--venue
landscape` does not write `terrain.bin`. **Another agent had rebuilt terrain in
the eighty seconds between my two snapshots.** I confirmed terrain is
deterministic by building it three times in a row — three identical hashes — and
then scoped the gate's comparison to the venues it was asked to build, so it
cannot cry nondeterminism at a colleague's build. A gate that produces false
alarms in a four-agent repository is a gate people learn to ignore.

### What this invalidates

Any visual diff between pass 04 and pass 05 that involves ground cover, verges,
hedges or scattered vegetation was comparing two different towns. That includes
the vanished tree in `t-gate-south`.

---

## 2. The perf instrument — FIXED at the cause

### Reproduced first, on this checkout

| command | `square` draws | scene | shadow | ao | post | batches drawn | by LOD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `--views square` | **1,385** | 467 | 604 | 242 | 72 | 177/544 | 193/93/171/10 |
| `--views plan,square` | **989** | 467 | 220 | 242 | 60 | 177/544 | 193/93/171/10 |

**The LOD state is identical.** Same 467 scene draws, same 177 of 544 batches
drawn, same 193/93/171/10 level distribution, same `culledDistance 104` and
`culledFrustum 263`. The entire 396-draw difference is the **shadow pass**,
604 against 220.

### The cause

`client/src/shadows.js fitSingle()` parks cascades 1..n by shrinking their
shadow cameras:

```js
k.left = -0.01; k.right = 0.01; k.top = 0.01; k.bottom = -0.01;
k.near = 0.1;   k.far = 0.2;
```

`fitCascades()` then calls `CSM.updateFrustums()` to refit. Read
`node_modules/three/examples/jsm/csm/CSM.js:_updateShadowBounds()`: it writes
`left`, `right`, `top`, `bottom` and calls `updateProjectionMatrix()`. It never
touches `near` or `far` — those are written once, in `_createLights()`, from
`lightNear`/`lightFar`.

So the **10 cm deep slab survives the refit**. `stats()` reports the box size and
the box size is restored, which is why five probe runs could not see it: cascade
1 reports `boxM 63.82` in both orders and renders nothing in one of them.

### The fix

`client/src/shadows.js`, in `fitCascades()` — restore `near`/`far` from the
authored config whenever the rig is coming back out of `single` mode. 8 lines,
in another agent's file; smallest edit I could make, flagged here.

### Verified in the instrument

```
--views plan,square :  square  1386 draws  = 467 + 604 + 242 + 73   3,599,966 tris
--views square      :  square  1386 draws  = 467 + 604 + 242 + 73   3,599,966 tris
```

**Identical.** The number no longer depends on what was rendered before it.

### And a second, structural guard — `tools/render/town.mjs`

Every view now renders **twice** and is sampled on the second (`--no-settle` to
measure the raw first frame). One renderer-state leak survived four passes
undetected because nothing made a frame independent of its predecessor; this
makes that property structural instead of something to keep remembering. The
settle rows are dropped from `viewStats` and every reported peak is re-derived
from the measured rows, so a settle frame can never become the published number.

Before the settle render, `plan,square` gave 1,386 and `square` gave 1,385 — a
residual 1-draw/8.6k-triangle first-frame cost (a lazily allocated post target).
With it, both are 1,386 exactly.

---

## 3. Client / harness parity — restored

| instrument | arrival camera | scene | shadow | ao | post | triangles | batches |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `check_client.mjs` (`hm.shoot`) | **1,396** | 541 | 570 | 205 | 80 | 2,943,210 | 212 |
| `town.mjs --views arrival` | **1,377** | 542 | 568 | 204 | 63 | 2,939,573 | 212 |

**1.4 % apart** (was 36 %). Scene, shadow, AO and batch count agree to within 2
draws; the whole residual is 17 `post` draws, which is the remainder bucket —
the client draws a player mesh and its own overlay chain that the harness has no
equivalent of. Same 212 batches, so the two are looking at the same town.

*(the client was never wrong: it only ever calls `fitCascades`, so it never lost
a cascade. `check_client.mjs`'s 1,395 was the honest number all along, exactly
as `ad-town-05` §15 said.)*

### The regression test

Two files, and the contract is written down instead of remembered:

- `tools/render/town.mjs` writes **`review/parity.json`** every time it shoots
  the `arrival` view — its own draw count, stage split, triangles and batch
  count, with a 3 % tolerance.
- `tools/check_client.mjs` reads it back, prints the delta on every run, and
  **fails the harness** when the client is outside tolerance.

Measured now: `vs tools/render/town.mjs (2026-08-02): 1378 draws, client is
1.5 % higher (tolerance 3 %)`. Against pass 05's state — harness 1,024, client
1,395 — this gate would have failed at **36 %** and named it.

`arrival` and not the worst camera, because it is the one frame both instruments
can hold identically: `BUILD_DIRECTIVE` §3's spawn, authored in content,
reachable from `hm.shoot()` without a route.

**What it cannot catch, stated so nobody trusts it further than it goes:** the
two instruments drifting *together*. It is a cross-check between two renderers,
not an absolute. The absolute is the §7 budget gate, which both of them already
run.

---

## 4. Mesh memory — FIXED. 243.3 MB → 233.4 MB against a 240 MB budget

`tools/assetgen/core/venue.py _levels()`. Measured first, because 243.3 MB is a
number with no attribution in it. Across the 35 shipped meshes:

| | bytes | share |
| --- | --- | --- |
| POSITION | 101.8 MB | 41.9 % |
| NORMAL | 50.4 MB | 20.8 % |
| TEXCOORD_0 | 50.4 MB | 20.8 % |
| INDEX | 34.5 MB | 14.2 % |
| COLOR_0 | 5.7 MB | 2.3 % |

Everything is already quantized (D-042, D-052) and 30.2 of the 34.5 MB of
indices are already `uint16` — there is nothing left in the *encoding*. But
**the LOD chain was 47 % of every byte the client downloads**:

| | before | after |
| --- | --- | --- |
| LOD0 (0–15 m) | 127.9 MB | 127.8 MB |
| LOD1 (15–40 m) | 76.9 MB | 76.9 MB |
| LOD2 (40–100 m) | 29.3 MB | **23.5 MB** |
| LOD3 (past 100 m) | 8.6 MB | **4.8 MB** |
| total | **243.3 MB** | **233.4 MB** |

LOD2's decimation went .40 → .32 of LOD1 and LOD3's .30 → .20 of LOD2. **LOD0
and LOD1 are untouched on purpose**: LOD1 starts at 15 m, and `ad-town-05` §17 is
already unhappy with how buildings read at 25–30 m. Nothing a reviewer can
resolve moved; 9.9 MB did. `validate.py` no longer fails, and reports the
remaining 233.4 MB as a warning at 97 % of budget, which is honest — this bought
headroom, not slack.

**What I did NOT do, and the number it would have bought.** `draw-budget.md`
item 4 asks for LOD2's material cap to go 3 → 2 (~100 draws at the far ring).
I left it at 3. `ad-town-05` §17 rejects on *"buildings past ~30 m still collapse
to one flat cream"*, and dropping LOD2 to two materials is the same defect,
deliberately, at 40 m. This is the wave the art director says decides ACCEPT and
it says plainly that the budget *"is still not what is wrong with these
frames"*. I am not buying 100 draws with the finding that is.

---

## 5. `validate.py`'s five failures — 2 cleared, 3 located and NOT claimed

`validate.py` now reports **5 failures**, and it is not the same five. Ledger:

| `ad-town-05` failure | now | what happened |
| --- | --- | --- |
| `uv_density` `nogging` 0.47× | **CLEARED** | the *instrument* was wrong — see below |
| §7 mesh memory 243.3 MB | **CLEARED** | §4 |
| `uv_density` `straw` 0.38× | open | located, one cause, §5.2 |
| `uv_density` `wool_crimson` 3.10× | open | located, §5.2 |
| `uv_density` `canvas_amber` 0.41× | open | located, one cause, §5.2 |
| *(new this wave, not mine)* `foam` albedo off-palette | open | a material added by the water work in progress |
| *(new this wave, not mine)* `water_fall` 512 px/m vs class 256 | open | same |

### 5.1 `nogging` was the instrument, not the asset

`core/materials.py uv_detail(key, metres, why)` is the pipeline's own sanctioned
way to depart from a material's authored coverage, and it *will not compile*
without a real sentence of justification. There are **47 such call sites**.
`tools/uv_density.py` could not see any of them, so it failed the build on
decisions the build had deliberately made and written down. `nogging` at
0.94 m/tile is `core/kit.py:117` asking for **0.91**, because a herringbone
panel between studs is 0.6–1.1 m wide and at the library's 2 m tile one panel
shows a third of one repeat.

An instrument that fails a documented decision is not measuring the town, it is
measuring its own ignorance of it — and it would have gone on failing however
many times somebody "fixed" the asset.

`uv_density.py` now reads every literal `uv_detail()` call out of the source by
AST and judges each material against the nearest coverage the build is entitled
to use, naming which. Statically and not from a build-time registry, on purpose:
a registry only records the overrides that happened to execute, so `--venue inn`
would silently un-sanction the other thirty-one venues. Non-literal arguments
are skipped **and reported**, so it can never quietly widen its own tolerance.

Effect: 4 failures → 3, 11 warnings → 10, and `oak` moved 0.50× → 0.70× (a
`moot_hall.py:298` override it could not previously see).

### 5.2 The other three are ONE bug, and it is in shared core

`tools/assetgen/core/mesh.py:1038`, inside `sheet()`:

```python
uv_fn = lambda x, z: (x, z)          # noqa: E731 — metres, per §5
```

**Every cloth surface in Hearthmere is UV-mapped one tile per metre, whatever
its material's authored coverage says.** `resolve_uv()` — the D-046 mechanism
that closed 421 literal `uv_scale=` sites and that `mesh.py`'s own header says
makes a bare float a build error — is never consulted by `sheet()`.

The evidence is a cluster in the measurement, not an inference. Every one of
these is a 2 m material shipping at ~1 m:

```
canvas_slate    1.02 m/tile   0.51x        oak_weathered  1.01   0.50x
foliage_flower  1.02          0.51x        oak            1.00   0.50x
leaf_oak        1.02          0.51x        weeds          1.07   0.54x
canvas_amber    0.83          0.41x  FAIL  straw          0.76   0.38x  FAIL
```

`wool_crimson` is the same file's other half. `venues/guild.py:281` maps the
banner **0..1 instead of in metres**, with a comment explaining exactly why:
the `banner` material carries an authored top-to-bottom sun-bleach gradient that
must not tile. That reasoning is right for `banner` and was never revisited when
the two big tower banners were switched to `wool_crimson` — plain dyed wool,
which must tile. Hence 3.78 m/tile on a 2.30 × 6.60 m drop.

**I am not claiming these three and I did not edit them.** `core/mesh.py` is
outside my lane, the fix rescales every cloth, awning, washing line and hanging
in the town by 2×, and I cannot verify that many surfaces in frame this wave.
Landing it in source is not landing it in the frame, and this project has been
burned by exactly that in every pass. The prescription, for whoever owns
`core/mesh.py`:

- `sheet()` takes `uv_scale=None` and defaults its `uv_fn` to
  `lambda x, z: (x * s, z * s)` with `s = resolve_uv(uv_scale, mat)`.
- `guild.py _banner` keeps 0..1 for `banner` and takes metres for everything
  else, or declares `uv_detail("wool_crimson", 3.8, why=...)` if 0..1 is the
  intent — but silence is not a reason, and `uv_detail` exists to say so.
- Then re-shoot `t-square`, `sty-walk-03` (the washing), `craft-walk-04` and the
  guild porch, because that is where it will show.

---

## 6. The budget, honestly — and a correction to the costed route

*(numbers in §7 below, from the full standard view set after the shadow fix.)*

The corrected shadow rig makes the honest number **larger**, not smaller: every
gameplay frame in every previous report was rendered — and measured — with
cascade 1 dead. `ad-town-05` §12's "the real number is 1,385/900" was right about
the magnitude and right for the wrong reason.

### The costed route, re-costed against what I measured

`review/reports/draw-budget.md` §3 sets out a route to ~922 draws. Two of its
five items rest on a premise the frame does not support, and I would rather say
so than execute arithmetic that cannot land.

**(1) "Per-cascade caster culling, −250." The premise is three cascades. There
are two.** `sunRig.stats()` at every gameplay camera reports exactly two:
cascade 0 covering 0–5.4 m in an 11.65 m box, cascade 1 covering 5.4–30 m in a
63.82 m box. And cascade 1 legitimately needs the near casters: at a 38° sun a
12 m gable throws a 15 m shadow, so a caster at 3 m shades fragments at 8 m.
Culling by cascade band deletes shadows; it does not save draws for free.

**The real structural win in the shadow pass is a different one, and it is
bigger.** The shadow pass is **depth only**. Material splits cost nothing there
and are free to merge — but the town casts from its beauty-pass primitives, so
it pays one shadow draw per *material* per cell per cascade. Measured at
`square`: 467 scene draws from 177 drawn batches is **2.64 primitives per
batch**, and the shadow pass is 604 draws over 2 cascades. A single merged
depth-only proxy per batch group would take the shadow pass to roughly
`2 × (casting groups)` — on that ratio, **604 → ~230, a saving near 375**, half
again the estimate in the costed route, with **no change to a single shadow the
player sees** because a depth buffer cannot tell which material drew it.

It is a real piece of work and it spans two files I do not own: `core/venue.py`
would emit the proxy (that half *is* mine) and `client/src/lod.js` +
`client/src/main.js` would have to swap proxies in for the shadow pass and out
for the beauty pass — three's `renderObject` skips `visible === false` in the
shadow pass too, so the swap has to happen between `shadowMap.render()` and the
scene pass, which is exactly what `scene.onBeforeRender` is for. **I did not
build it blind in a wave where four agents are in these files.** It is the
single largest item left in the budget and it should be one agent's whole job.

**(2) "Merged character meshes, 582 → 150."** There are no characters.
`BUILD_DIRECTIVE` §1 removed them from scope and `townsfolk` is deleted from
`assets/meshes/` in this working tree. This item cannot be executed against this
build; it is a projection parameter, and §7 below re-runs the projection with it
stated as such.

**(3) The three material collapses** (`plaster_shade` → COLOR_0 −62, a glazing
page −51, `tree_far` −150) are `core/materials.py` and `core/atlas.py` work.
Outside my lane, and `ad-town-05` names the atlas as the one thing that already
landed without reaching the frame — so these want the agent who owns the pages.

**(4) The LOD2 material cap** — declined, with reasons, in §4.

---

## 7. The numbers, measured, at the end of this wave

`node tools/render/town.mjs --out review/shots/town --label t --allow-missing`
— the **standard command, standard view list, opening with `plan`**, which is
the exact configuration that used to under-report by 30 %.

```
  view           draws = scene + shadow +   ao + post     triangles   batches   LOD 0/1/2/3
  plan            3723    1824     1780      0    119     7,330,763   368/544   1824/0/0/0
  aerial-ne        941     665      142      4    130     1,874,338   397/544   119/0/0/546
  aerial-sw        926     661      132      3    130     1,837,986   397/544   114/0/0/547
  arrival         1378     544      568    203     63     3,015,529   211/544   155/101/226/62  <- gameplay
  square          1381     462      604    242     73     3,698,183   176/544   186/93/168/15   <- gameplay
  silhouette      3491    1752     1733      0      6     7,276,588   317/544   1752/0/0/0
  approach-s       728     561       70     35     62     1,362,029   280/544   69/33/137/322   <- gameplay
  approach-ne      550     499        0     15     36     1,324,800   267/544   58/0/118/323    <- gameplay
  approach-w       826     606      100     58     62     1,735,349   304/544   80/40/153/333   <- gameplay
  bridge           767     312      290    134     31     2,705,149   141/544   107/50/98/57    <- gameplay
```

**Worst gameplay camera: `square`, 1,381 draws / 3,698,183 triangles** against
900 / 3,500,000 — **1.53× and 1.06× over.** `arrival` is 1,378. The budget gate
fails, correctly and loudly, and it is now the same number in both instruments.

Note `square` at **1,381 in a run that opened with `plan`**. That is the whole of
§2 demonstrated in the published report rather than in a probe.

**Attribution:** the shadow pass is **604 of 1,381 at `square` (44 %) and 568 of
1,378 at `arrival` (41 %)** — larger than the beauty pass in both. It is the
budget's critical path and §6(1) is the route.

| instrument | before this wave | now |
| --- | --- | --- |
| `validate.py` | 5 failures, 46 warnings | **5 failures, 47 warnings** (2 of the original 5 cleared; 2 new ones arrived from concurrent material work; see §5) |
| `check_client.mjs` arrival | 1,395 draws | 1,398 draws — **agrees with the harness to 1.5 %** |
| `town.mjs` arrival (standard cmd) | 1,024 draws (wrong) | **1,378** |
| §7 mesh memory | 243.3 MB **FAIL** | **233.4 MB pass** |
| build determinism | **NOT DETERMINISTIC** | byte-identical, gated |

### The 100-character projection, re-run

Method unchanged from `budget-truth.md` so the three runs are comparable: 6
submeshes / ~25 k triangles per character at LOD0, one scene draw each plus a
shadow draw inside the caster radius and an AO draw inside 35 m, distributed
15 / 35 / 50 across the LOD rings.

```
players     15x18 + 35x7.5 + 50x1   =   582 draws
            15x75k + 35x20k + 50x2k = 1.93 M triangles
town (square, measured this wave)   = 1,381 draws / 3.70 M triangles
                                      ------------------------------
TOTAL                               = 1,963 draws / 5.63 M triangles
§7 budget                           =   900 draws / 3.50 M triangles
                                        2.2x over      1.61x over
```

**It does not hold, and it is marginally worse than pass 05's 1,967 / 5.52 M —**
4 draws better and 110 k triangles worse. The draw saving is the LOD2/LOD3
decimation; the triangle rise is concurrent art work landing in the same build.
**Nothing this wave moved the projection, because nothing this wave was allowed
to touch the shadow pass, and the shadow pass is 44 % of the frame.**

State the character number honestly: **there are no characters in this build.**
`BUILD_DIRECTIVE` §1 removed them and `townsfolk` is deleted from
`assets/meshes/`. The 582 is a projection from an asset that does not exist, so
the two-thirds of it that the "merged character mesh" item would remove is
bookkeeping, not engineering. The load-bearing half of the projection is the
town's own 1,381, and that is real and measured.

**The route that closes it, with what each is worth against the numbers above:**

| | draws | owner |
| --- | --- | --- |
| depth-only shadow proxy per batch group (§6.1) | **−375** | `core/venue.py` (mine) + `client/src/lod.js`, `main.js` |
| `tree_far` to one prototype + one page | −150 | `core/atlas.py` |
| character mesh merge, *if characters return* | −430 | out of scope today |
| `plaster_shade` → COLOR_0 | −62 | `core/materials.py` |
| glazing page (`glass` + `glass_lit`) | −51 | `core/atlas.py` |
| LOD2 material cap 3 → 2 | −100 | declined this wave, §4 |

Town alone: 1,381 − 375 − 150 − 62 − 51 = **743**, inside 900 with room.
With 100 merged characters: 743 + 150 = **893**. §7 is reachable, the arithmetic
now rests on measured numbers rather than on a mis-measured baseline, and **the
shadow proxy is more than half of it.**

---

## 8. What I changed, and what I touched that is not mine

| file | change | mine? |
| --- | --- | --- |
| `tools/determinism.py` | **new** — the determinism gate | yes |
| `tools/validate.py` | `check_determinism_sources()` | yes |
| `tools/uv_density.py` | read sanctioned `uv_detail()` overrides | yes (consumed by validate) |
| `tools/render/town.mjs` | settle render, de-duplicated peaks, `review/parity.json` | yes |
| `tools/check_client.mjs` | the parity gate | yes |
| `tools/assetgen/core/venue.py` | LOD2/LOD3 decimation ratios | yes |
| `tools/assetgen/venues/landscape.py` | **2 lines** — `hash()` → `seed_from()` + its import | **no** — the determinism bug lived there |
| `client/src/shadows.js` | **8 lines** in `fitCascades()` — restore cascade near/far | **no** — the perf bug lived there |

Both out-of-lane edits are the smallest possible form of the fix and neither
changes a policy: the landscape one swaps a seed function, the shadows one
restores two numbers the config already authored.

## 9. Verified in frame, not in source

`review/shots/town/t-square.png` against `review/shots/ad-town-05/t-square.png`,
same camera, same rig:

- **pass 05:** the figure has a contact shadow and nothing else in the frame
  casts. The fountain, the butcher's pitch, the market oak and every building
  around the square sit on flat, evenly lit paving.
- **now:** the fountain casts a shadow across its own basin and onto the setts,
  the butcher's pitch throws a shadow across the frame-left paving, the market
  oak lays a broad dapple over the setts to the right of the figure, and the
  buildings shade their own bases.

That is the 5.4–30 m cascade returning. It confirms the fix is in the picture,
and it confirms the diagnosis: **`ad-town-05`'s "the harness samples the
previous frame's LOD state" was measuring a shadow rig that had stopped
rendering, and the reason the count and the image were both wrong is that they
were the same bug.**

`review/shots/town/t-arrival.png` corroborates: the nave floor now carries a
real cast shadow from the west wall with a defined edge, where pass 05 had only
a soft sun/shade gradient.

`review/shots/town/t-gate-south.png` (re-shot for this, 1,208 draws = 682 scene
+ 272 shadow + 176 ao + 78 post): **no tree, therefore no dapple.** The
`ad-town-05` §4 finding stands on its own and is not mine to claim. The
blue-grey plate curtain that report also names is gone — another agent's masonry
work, landing in the same build.

*(caveat, stated because it matters: three other agents were editing
`core/materials.py`, `core/vegetation.py`, `tools/render/town.html` and
`client/src/` while these renders ran, so `review/shots/town/` is a mixed state.
Every number above is reproducible from this checkout; the surfaces in the
images are not all mine to claim.)*
