# Consolidation — one siting convention, and a safe content pipeline

**Scope.** Two agents working in parallel found the same mirrored-rotation bug
and each shipped a different cure into shared core. This report unifies them,
proves the result corner-exact against the slot polygons, makes
`content/town/hearthmere.json` regeneration total and idempotent, and audits
every venue module for placement.

Status at time of writing: **items 1, 2 and 4 done; item 3 (clean full build +
walkable/client checks) in progress**, results at the end.

---

## 1. One siting convention

### What was wrong

Two mirrored conventions, both load-bearing:

| | maps local `+X` to | source of truth |
| --- | --- | --- |
| **plan** | `(cos t, sin t)` | `docs/TOWN_PLAN.md` §6, `core.building.Footprint`, every `buildingSlots[].polygon` |
| **placement** | `(cos t, −sin t)` | three.js `rotation.y` in `client/src/main.js:174`, `client/src/collision.js:201`, `tools/render/town.html:413`, `tools/check_walkable.mjs` |

Compose them and a mesh authored front-to-local-`−Z` comes out facing
`(−sin t, −cos t)` instead of `(sin t, −cos t)`. At `t = 0` or `180` the error
is exactly zero, which is why fourteen venues shipped before anyone saw it.

**Measured cost of the bug**, worst footprint-corner displacement per venue if
the correction is removed (recomputed from the plan, not quoted):

| slot | venue | rot | corner error |
| --- | --- | --- | --- |
| 11 | church | 270° | **31.24 m** |
| 02 | guild | 90° | **22.63 m** |
| 01 | inn | 90° | **21.26 m** |
| 43 | blacksmith | 60° | **19.75 m** |
| 70 | stables | 80° | **19.70 m** |
| 38 | waggon_shed | 257° | **15.71 m** |
| 03 | moot_hall | 60° | **13.22 m** |
| 93 | tannery | 225° | **12.17 m** |
| 57 | dovecote | 81° | 7.54 m |
| 36 | bowyer | 349° | 2.30 m |
| 32 | bakery | 6° | 1.55 m |
| 91 / 34 | bathhouse / carpenter | 357° | 0.93 / 0.90 m |
| 90 / 33 | wellhouse / cooper | 354° / 3° | 0.83 / 0.82 m |
| 35 | chandler | 183° | 0.70 m |
| 04, 07, 21, 72 | shop_row, chophouse, confectioner, pub | 0° / 180° | 0.00 m |

### The resolution

`core.siting.Site` is now the **only** siting class in the repo.

- **Kept:** `core/siting.py::Site`. It is the module named for the job, it
  carries the full derivation in its docstring, and it already owned the
  ground (`base`, `lo`, `hi`, `ground(x, z)`, graded-pad lookup) that
  Directive §6.1 requires and that `Plot` did not have.
- **Deleted:** `core.venue.Plot` (191 lines) and its parallel `-2.0 * theta`.
  Its useful surface was absorbed first — `front`/`back`/`hw`/`hd`,
  `xz`/`p3` aliases, `cell_at`, `instance`, `collider_from`, dict/list
  collider passthrough, and the `rotY` normalisation that keeps a `-0.0` out
  of an unrotated plot's collision file.
- **Deleted:** the second town-document reader. `siting.py` used to open and
  cache `hearthmere.json` itself; it now imports `town`/`slot`/`TOWN_JSON`
  from `core.venue`. One reader, one cache.
- **Deleted:** the hand fix in `venues/church.py`. The docstring paragraph
  that derived `−2t` by hand is gone. Church now declares
  `SITE = SI.Site("church", authored=math.pi)` — "these 1400 lines are already
  the design frame turned 180°" — and core computes the residual. Today the
  residual is exactly `0.0`, so **not one vertex moved**; if the plan ever
  changes slot 11's rotation the residual stops being zero and `build()`
  raises with an explanatory message instead of silently mirroring the arrival
  frame. Re-coordinating 1400 lines of hand-tuned interior for zero geometric
  change was rejected as pure risk; the guard is what makes it safe.

`Site` also gained an explicit `bind(ctx)` so the useful module-scope pattern
(`SITE = Site(NAME)` at import, its `w`/`d`/`eaves`/`front` becoming the
module's dimensional constants) survives while every output method takes the
context from one place.

### Callers migrated — all 19 slot venues now go through `Site`

| from | venues |
| --- | --- |
| `core.venue.Plot` (8) | bowyer, carpenter, chandler, cooper, dovecote, stables, tannery, waggon_shed |
| `core.siting.Site`, old ctx-per-call API (6) | bakery, bathhouse, chophouse, confectioner, moot_hall, wellhouse |
| hand fix (1) | church |
| **nothing at all — no frame handling whatsoever (5)** | **inn, guild, blacksmith**, shop_row, pub |

That last row is the find. `inn` (90°), `guild` (90°) and `blacksmith` (60°)
are v1 survivors: they were authored before the v2 schedule existed, they use
neither class, and nothing was correcting their frame. Their fronts were
mirrored — the inn's and the guild's principal facades were pointing **west,
away from the market place they exist to front**, and the blacksmith was 120°
off its own yard. They are the 2nd, 3rd and 4th worst entries in the table
above and they were not on the suspect list. All three author their front at
local `−Z` (`doors=[("-z", …)]`, `zf = -D * 0.5`), so routing them through
`Site` with the default `authored=0` is the whole fix.

`shop_row` (0°) and `pub` (180°) had zero error but were migrated too, so that
"every slot venue is sited by `Site`" is a property of the build rather than a
coincidence of their rotations.

### Verification — corner-exact, and the check is load-bearing

`tools/plan/townplan.py::check_siting` re-derives the entire chain
**without importing `core.siting`**, so a bug in the class cannot pass its own
test: design-frame footprint → `−2t` turn using the three.js matrix →
`rotation.y = theta` about `venues[].origin` → compare against
`buildingSlots[].polygon`. It also asserts `venues[].origin` is the slot centre
and `venues[].rotationDeg` is the slot rotation, and that the polygon on disk
matches the plan.

```
siting: 20 venue slots corner-exact on their polygons
        (16 at a rotation where the two conventions disagree);
        worst corner error 0.0000 mm
```

Tolerance is 1 µm. The four world-space venues (`quay`, `warehouse`,
`fish_eatery`, `watermill`) are placed at origin `(0,0,0)` rotation `0` and
author in world coordinates, so no frame correction applies; they are reported
by name rather than silently skipped.

---

## 2. `hearthmere.json` regeneration is now total, safe and idempotent

Three faults, three fixes.

**(a) A venue module could exist, be built, and be silently dropped.**
`venues/landscape.py` was placed in the document but missing from
`write_town`'s infrastructure list, so every regeneration deleted it and the
town rendered with zero vegetation, zero gardens, zero churchyard and zero
intramural ground for a whole wave.

The infrastructure list moved out of `write_town`'s body into
`plan_data.INFRASTRUCTURE`, beside `VENUE_OF_SLOT`, so the two halves of "what
gets placed" cannot go out of step. `townplan.py::check_placement_total` now
**fails the run** if a module under `tools/assetgen/venues/` is neither placed
on a slot, nor placed as infrastructure, nor declared in
`plan_data.NOT_PLACED` with a reason of at least 40 characters. It also fails
on the reverse (a placement with no module — the client would 404 on the
mesh), on a module both placed and declared not-placed, and on a stale
`NOT_PLACED` entry.

```
placement is total: 35 venue modules — 24 on slots, 8 infrastructure,
                    3 declared not-placed (cottage, props_sheet, props_situ)
```

**(b) `lighting` and `ambient` were copied forward from the file being
overwritten.** Any hand edit to either survived exactly until the next
regeneration. They are now `plan_data.LIGHTING` and `plan_data.AMBIENT`, the
declared authoritative source, and `write_town` no longer opens the previous
document at all. Regeneration is a pure function of `plan_data` +
`terrain.json`.

**(c) Idempotence.** Verified byte-for-byte: two consecutive full runs of
`python tools/plan/townplan.py` produce identical `hearthmere.json`.

---

## 4. Orphan and placement audit — confirm / deny

**Is `venues/cottage.py` an orphan that builds a mesh nobody places?
— CONFIRMED.**

- `NAME = "cottage"`, `CELLS = ["A2","B2","F2","A4","F3","F5"]` — v1 cells,
  not v2 slot cells.
- It builds `hm.cottage.01` and writes `assets/meshes/cottage.gltf` +
  `content/collision/cottage.json`, because `build.py::discover()` picks up any
  module with a `build`.
- No `venues[]` row in `content/town/hearthmere.json` has ever referenced it,
  so the client never loads either file.
- Its work is done elsewhere: `venues/townhouse.py` has
  `KITS = ("townhouse", "cottage", "shed", "workshop")` and builds all 63 kit
  masses straight from `buildingSlots[]`, including every `cottage`-kit slot.

Not deleted — deleting a module to make a build green is forbidden. It is now
declared in `plan_data.NOT_PLACED` with that reasoning, so the state is
explicit and the checker is satisfied without being lied to. Recommend a
separate change that deletes it after someone confirms `townhouse.py` carries
everything it did.

`props_sheet` and `props_situ` are the same shape of thing but legitimately so:
review harnesses (`CELLS = []`), contact sheet and in-situ yard for
art-director review, never placed, never shipped. Also declared.

**Is `moot_hall.py` fully saved? — YES.** 942 lines, imports cleanly, ends in a
complete `build()` with its `SITE.report()` diagnostic. It was the venue the
bug was first *named* on (60°, 13.22 m out), not a truncated file.

**Does every venue in `hearthmere.json` have a generator, and every generator a
placement? — YES, and it is now enforced rather than observed.** 35 modules;
24 on slots, 8 infrastructure, 3 declared not-placed; zero unaccounted in
either direction. `check_placement_total` fails the run otherwise.

---

## 3. Full build, and the venue-by-venue table

### The build

`python tools/assetgen/build.py --skip-textures` — **exit 0, all 35 modules
built, none skipped, no import failures.** 2,795,710 source triangles.

`node tools/check_client.mjs` — **PASS.**

```
booted: 2492 collision volumes across 32 placements, 241 entities
spawn:  43.00, 3.30, -0.50
settle: 194 ms to a stable LOD/batch set
perf:   544 draw calls whole frame, 1,007,088 triangles at eye level
walked: (43.0, 2.7) -> (4.7, 44.2), 204.9 m of path over 52 samples
OK — client boots clean and the player walks.
```

`node tools/check_walkable.mjs` — **PASS.** All 15 streets traversable, 0
severed, 0 obstructed; Ford Road traversable end to end; the altar, fountain,
market cross and bridge all reachable. One pre-existing unreachable door,
`hm.townhouse.door.15` (slot 15, song school) — a `townhouse`-kit mass with no
siting class involved and no change from this work.

`node tools/render/town.mjs --views plan,aerial-ne,aerial-sw,arrival,square,silhouette`
— 6 views at the locked 09:30 rig, `review/shots/town/`. Gameplay cost
**582 draws / 1,129,109 triangles** against the §7 budget of 900 / 3.5 M.

**The budget gate fails, and not on this work.** It names `shop_row` 36 → 43
and `streets` 94 → 155 LOD0 draws against `review/perf-baseline.json`, which
was recorded at `"venuesPlaced": 10` — before the 18-venue wave. `streets` was
not touched here. `shop_row` was, so it was A/B tested: reverting the migration,
rebuilding, and rebuilding again with it restored produces **byte-identical**
`shop_row.gltf`, `shop_row.bin` **and** `shop_row.json` (md5
`128e8e8d…` / `c79fe27b…` / `33bc29ae…`) and 43 draws either way. Both deltas
predate this change; the baseline is stale and should be re-recorded by
whoever owns the perf pass, not silently overwritten here.

### Verification of the siting, three independent ways

**(i) Algebraic, corner-exact.** `check_siting` (above): 20 venue slots,
worst corner error **0.0000 mm** at a 1 µm tolerance.

**(ii) Front doors, from the shipped `content/entities/*.json`.** Every door
entity transformed to world by the runtime formula and projected onto the
plan's front normal. All of them land on the **front** of their slot, at
essentially the plot's half-depth:

| venue | rot | door | offset along the front normal | plot half-depth |
| --- | --- | --- | --- | --- |
| inn | 90° | `hm.inn.door.01` | +4.62 m | 7.0 |
| guild | 90° | `hm.guild.door.01` | +5.75 m | 8.0 |
| church | 270° | `hm.church.door.west.01` | +12.00 m | 12.0 |
| chophouse | 180° | `…chophouse.door.01` | +5.22 m | 5.0 |
| confectioner | 0° | `…confectioner.door.01` | +5.20 m | 5.0 |
| shop_row | 0° | `hm.shop.general.door.01` | +4.15 m | 5.5 |
| pub | 180° | `hm.pub.door.01` | +4.12 m | 3.8 |
| chandler | 183° | `hm.chandler.door.01` | +4.45 m | 4.5 |
| dovecote | 81° | `hm.dovecote.door.01` | +2.77 m | 2.7 |
| bathhouse | 357° | `…bathhouse.door.01` | +5.72 m | 5.5 |
| moot_hall | 60° | `…moot.lockup.01` | +3.03 m | 4.0 |

(`bakery` reports its **yard** door at −3.05 m, which is correct: the yard door
is at the back. Its shop door is on the front.)

**(iii) Footprint aspect, from the shipped `content/collision/*.json`.** A
mirror about the frontage normal is a rotation by `2θ` about the plot centre,
so a mirrored venue's mass runs *across* its plot. Every solid collider corner
was projected onto the plan's own `U` (frontage) and `F` (front normal) axes.
**Every venue runs along its frontage**, including `tannery` (225°, no door
entity, and the one case where the other two tests are degenerate): measured
**13.1 × 9.9 m** against a slot of 14.0 × 10.0.

The same measurement surfaces a defect that is **not** siting and is out of
scope here, but should not go unrecorded — see §5.

### The table

| module | placed | rotation | corner-exact verified | tris | LOD0 draws | collision volumes |
| --- | --- | --- | --- | ---: | ---: | ---: |
| `inn` | slot 01 | 90° | yes — algebraic 0.0000 mm; door +4.62 m front | 38,242 | 28 | 8 |
| `guild` | slot 02 | 90° | yes — algebraic; door +5.75 m front | 43,256 | 39 | 11 |
| `moot_hall` | slot 03 | 60° | yes — algebraic; colliders at −60.00° (mirror would be +60.00°) | 54,150 | 36 | 36 |
| `shop_row` | slot 04 (+05, 06) | 0° | yes — no correction applies at 0°; door +4.15 m front | 51,672 | 43 | 18 |
| `chophouse` | slot 07 | 180° | yes — no correction applies at 180°; door +5.22 m front | 44,282 | 37 | 14 |
| `church` | slot 11 | 270° | yes — algebraic; door +12.00 m = exact half-depth | 84,958 | 48 | 50 |
| `confectioner` | slot 21 | 0° | yes — door +5.20 m front | 32,416 | 30 | 9 |
| `bakery` | slot 32 | 6° | yes — colliders at −6.00° (mirror +6.00°) | 63,660 | 36 | 19 |
| `cooper` | slot 33 | 3° | yes — colliders at −3.00° (mirror +3.00°) | 49,998 | 50 | 29 |
| `carpenter` | slot 34 | 357° | yes — colliders at +3.00° (mirror −3.00°) | 45,840 | 41 | 26 |
| `chandler` | slot 35 | 183° | yes — door +4.45 m front | 45,486 | 51 | 31 |
| `bowyer` | slot 36 | 349° | yes — colliders at +11.00° (mirror −11.00°) | 33,710 | 43 | 12 |
| `waggon_shed` | slot 38 | 257° | yes — colliders at +103.00° (mirror −103.00°) | 42,286 | 32 | 23 |
| `blacksmith` | slot 43 | 60° | yes — colliders at −60.00° (mirror +60.00°) | 11,684 | 18 | 7 |
| `dovecote` | slot 57 | 81° | yes — doorstep at −81.00°; door +2.77 m front | 40,728 | 29 | 26 |
| `quay` | slot 61 | 315° | n/a — world-space venue (origin 0,0,0 rot 0) | 149,326 | 59 | 31 |
| `warehouse` | slot 62 | 270° | n/a — world-space venue | 150,124 | 153 | 63 |
| `fish_eatery` | slot 64 | 11° | n/a — world-space venue | 40,478 | 41 | 9 |
| `stables` | slot 70 | 80° | yes — colliders at −80.00°; footprint 15.7 × 11.9 vs slot 16 × 12 | 45,453 | 39 | 31 |
| `pub` | slot 72 | 180° | yes — door +4.12 m front | 14,261 | 27 | 9 |
| `watermill` | slot 77 | 150° | n/a — world-space venue | 53,390 | 57 | 33 |
| `wellhouse` | slot 90 | 354° | yes — colliders at +6.00° (mirror −6.00°) | 20,490 | 20 | 8 |
| `bathhouse` | slot 91 | 357° | yes — colliders at +3.00°; door +5.72 m front | 51,694 | 35 | 14 |
| `tannery` | slot 93 | 225° | yes — footprint 13.1 × 9.9 along the frontage vs slot 14 × 10 | 35,004 | 44 | 20 |
| `terrain` | infrastructure | — | n/a | 265,888 | 9 | 65 |
| `landscape` | infrastructure | — | n/a | 1,238,446 | 596 | 406 |
| `streets` | infrastructure | — | n/a | 131,781 | 155 | 379 |
| `wall` | infrastructure | — | n/a | 106,602 | 142 | 484 |
| `gatehouse` | infrastructure | — | n/a | 22,426 | 14 | 49 |
| `market_square` | infrastructure | — | n/a | 20,348 | 23 | 69 |
| `stalls` | infrastructure | — | n/a | 73,850 | 41 | 8 |
| `townhouse` | infrastructure (63 kit masses) | — | n/a — built in world space from `buildingSlots[]` | 885,232 | 769 | 495 |
| `cottage` | **NO — declared not-placed** | — | n/a, orphan | — | — | — |
| `props_sheet` | **NO — declared not-placed** | — | n/a, review harness | — | — | — |
| `props_situ` | **NO — declared not-placed** | — | n/a, review harness | — | — | — |

**Totals:** 35 modules, 32 placed, 2,492 collision volumes, 241 entities.
Gameplay **582 draws / 1,129,109 tris** vs a 900 / 3.5 M budget.

Nothing was deleted to make the build green.

---

## 5. Found in passing — NOT fixed, and out of scope

The footprint-aspect measurement in §3(iii) also measures each venue's mass
against the plot it was given. Three v1 survivors are now correctly *oriented*
but were never rebuilt to their v2 slots:

| venue | slot footprint | mass measured | |
| --- | --- | --- | --- |
| `blacksmith` | 18.0 × 14.0 m | **9.8 × 7.8 m** | fills 30 % of its plot |
| `inn` | 16.0 × 14.0 m | **11.9 × 9.4 m** | fills 50 % of its plot |
| `pub` | 12.0 × 7.5 m | 10.3 × 8.3 m | slightly deep |
| `guild` | 16.0 × 16.0 m | **20.1 × 13.9 m** | **overhangs its plot by 4.1 m** |

Their module constants confirm it: `inn.py` has `W, D = 11.5, 9.0`,
`guild.py` has `HALL_W, HALL_D = 19.0, 11.5`, `blacksmith.py` has
`YARD_W, YARD_D = 9.5, 7.5`, and all three still carry v1 `CELLS`
(`["E3","E4"]`, `["C2","D2"]`, `["B5","B6"]`) that do not match their v2 slot
cells. Two of the three are **hero venues**. The guild overhanging its plot is
also why the town render's overlap report lists it.

This is a rebuild-to-schedule job, not a siting job, and doing it inside this
change would have hidden the siting fix inside a large geometric diff. Flagged
here so it is on the record rather than discovered a third time.

Also unchanged and still open: `review/perf-baseline.json` is stale
(`venuesPlaced: 10`) and fails the budget gate on two venues neither of which
regressed in this work.

---

## Files changed

| file | what |
| --- | --- |
| `tools/assetgen/core/siting.py` | the single `Site` class — merged, `bind(ctx)`, `authored=`, `corners()`, one town-document reader |
| `tools/assetgen/core/venue.py` | `Plot` deleted (−191 lines); keeps `town()` / `slot()` / `TOWN_JSON` |
| `tools/assetgen/venues/church.py` | hand fix deleted; declares `Site("church", authored=math.pi)` and raises if the residual stops being zero |
| `tools/assetgen/venues/{inn,guild,blacksmith,shop_row,pub}.py` | newly sited — were using no frame class at all |
| `tools/assetgen/venues/{bowyer,carpenter,chandler,cooper,dovecote,stables,tannery,waggon_shed}.py` | migrated off `Plot` |
| `tools/assetgen/venues/{bakery,bathhouse,chophouse,confectioner,moot_hall,wellhouse}.py` | migrated to the bound-context `Site` API |
| `tools/plan/plan_data.py` | `INFRASTRUCTURE`, `NOT_PLACED`, `LIGHTING`, `AMBIENT` |
| `tools/plan/townplan.py` | `check_placement_total`, `check_siting`; no copy-forward from the file being overwritten |
| `docs/DECISIONS.md` | D-025 (one siting class), D-026 (total, safe regeneration) |
| `content/town/hearthmere.json`, `docs/plan/*`, `docs/TOWN_PLAN.md` | regenerated, idempotent |
