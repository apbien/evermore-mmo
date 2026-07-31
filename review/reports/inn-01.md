# Grey Heron Inn — Review 1

**Verdict:** REVISE
**Renders:** `review/shots/inn/inn-approach.png`, `inn-gameplay.png`
**Context:** `review/shots/town-arrival.png`

---

## First impression (before analysis)

A half-timbered inn. I knew what it was, which is more than I could say for the
guild. Then, in the same breath: it is very flat, very symmetrical, and I cannot
see into a single window — they are filled with the same cream as the wall.

At the gameplay camera the second read arrived: the front door is standing wide
open and there is a lit plaster wall behind it. Nobody lives here.

---

## Blind AAA comparison

Against **FFXIV / Gridania** (semi-realistic anime materials, warm inviting
palette, readable pictorial signage).

Closer than the guild, and the massing would survive the comparison. The jettied
storeys and dormers are doing real AAA-grade silhouette work.

It still loses, and it loses on one thing above all: **in Gridania every window
is either warm-lit, dark, or shuttered, and here every window is filled with
daylit plaster.** That single tell converts the building from an inn into a
facade prop. Gridania's inns are the warmest thing in frame; this one is the
same value as the wall it is cut into. The World Bible brief says the inn must be
"the most inviting thing in the frame" — right now it is the flattest.

Second-order tells a player would register without naming: no chimneys on a
three-storey inn with a hearth; a sign that carries no device; a facade whose
window bays are perfectly mirror-symmetric.

**Would people play this?** Yes — they would walk toward it, which is more than
the guild earns. They would be disappointed at the door.

---

## Scores

| Axis | Score | Note |
| --- | --- | --- |
| Silhouette | **6** | Jetties and dormers work genuinely well. Both chimneys are buried inside the roof; the sign never breaks the outline. |
| Material truth | **4** | Windows show wall plaster. Roof is one uniform sheet. Sill is street cobble. Barrel reads as galvanised steel. |
| Lighting response | **5** | Jetty shadows are the best lighting read in either venue. Zero emissive against a brief demanding warm light in every window. |
| Detail hierarchy | **6** | Best-structured venue reviewed. Tertiary tier is present but mostly failing to read. |
| Wear & story | **4** | Good plaster blotching. No streaking below ~30 sills, no ground splash, no differential timber weathering. |
| Life & residue | **5** | Laundry, boots, cat, bench, barrel, mounting block — real effort. The cat and boots are carved from oak. |
| Cohesion | **7** | It looks like Hearthmere. The strongest axis. |
| Scale truth | **7** | Storey heights match §3; door and windows check against the 1.75 m figure. |
| AAA comparison | **4** | The plaster-filled windows alone give it away. |

**Acceptance requires no axis < 7 and AAA ≥ 8. Six axes block.**

---

## Defects

### 1. Every window is filled with wall — there is no interior

`_storey` (`inn.py:31-48`) builds four walls per floor and nothing else. No
floor, no ceiling, no room, no interior blocker. The back wall is built
`style="square"` with no openings.

Consequence: sky light floods through the front apertures and lights the inner
face of the back wall to roughly exterior value. Every window and the open front
door therefore show **daylit cream plaster**, complete with the wall's own dirt
blotches visible through the "glass." In `inn-gameplay.png` the door stands open
at ~40° onto a solid pale surface.

The World Bible brief — *"Warm light in every window — the inn is the most
inviting thing in the frame"* and *"Ground floor: common room, hearth, long
tables, stairs up"* — delivers none of it. The palette even reserves
`Window interior spill #FFD9A0 @ 2.2` for exactly this and it is unused
anywhere in the venue.

This is the defect that costs the most AAA score. Nothing else on the building
matters as much.

**Fix, cheapest sufficient version:** add an interior shell per storey — a dark
floor plane, a ceiling at 2.70 m, and an interior wall material at low value —
so apertures read as voids. Then give the ground-floor glass an emissive warm
tint (`#FFD9A0`) and the upper floors a dimmer variant, so the inn glows against
the plaster. Full room interiors are not required for this pass; killing the sky
flood and adding the glow gets ~90% of the benefit.

### 2. Both chimneys are generated entirely inside the roof

`inn.py:212-215` emits two chimneys. Working the arithmetic through:

- `y3` (eaves level) = `0.45 + 3.05 + 2.85 + 2.60` = **10.95**
- chimney bases at `y3 - 0.2` = 10.75, heights 2.6 and 3.0 → tops at **13.35 / 13.75**
- roof: `gable_roof(D2=10.512, W2=13.01, pitch=0.92, overhang=0.50)`
  → `w = 11.512`, `h = 5.756 × 0.92` = 5.295 → **ridge at y3 + 5.295 = 16.245**
- chimneys sit at `z = ±0.6`, i.e. near the ridge, where the roof surface is ~16.14

**Both chimneys are buried 2.4–2.9 m inside the roof volume.** They cost
triangles and are invisible in every render. The two smoke entities
(`inn.py:216-218`) spawn at y = 13.35 — also inside solid roof geometry.

This removes the two strongest vertical silhouette-breakers on the building and
the World Bible's explicitly required *"smoke from two chimneys."* Confirmed
visually: no chimney appears anywhere in `inn-approach.png` or `town-arrival.png`.

**Fix:** compute the roof surface height at the chimney's `(x, z)` and size the
stack to clear it by 1.0–1.4 m, with a flaunching/weathering collar where it
penetrates. Move the smoke emitter to the stack top. Then offset the two stacks
asymmetrically in height and position — they are the best silhouette asset the
building has.

### 3. The heron sign carries no heron

`_heron_sign` (`inn.py:51-92`) is a good idea executed at the wrong scale and the
wrong orientation:

- **It does not read.** The bird is assembled from `"ashlar"` primitives set at
  `z = -0.035` on a 0.045-thick board — roughly **12 mm of relief**, in
  stone-grey on dark oak, occupying maybe 40% of a 1.05 × 0.78 m board. At the
  gameplay camera it renders as a few pale scratches. In `inn-approach.png` the
  sign is a blank brown rectangle.
- **It hangs parallel to the facade.** The board is built in the XY plane and
  never rotated, so its face is coplanar with the wall. A hanging inn sign
  projects *perpendicular* to the wall so it is visible along the street, and so
  it can swing. This one contributes nothing to the silhouette — the World Bible
  names the sign as the inn's anchor element.
- **It collides with the window band.** Placed at `y0 + 2.70` = 3.15, it overlaps
  the first-floor window and its shutter. Visible clipping in both renders.

**Fix:** rotate the board 90° so it hangs off the bracket arm perpendicular to
the facade; move it above the window head (~3.6 m, retaining the §3 2.20 m
clearance); scale the heron to fill ~70% of the board with 25–40 mm of relief;
and give it a high-contrast pale-grey-on-dark-board read so it works as a
*silhouette*, which is what the docstring correctly says a shop sign is for.

### 4. The roof is one uniform sheet

Measured on pure sunlit roof: low-frequency stdev **1.73**, high-frequency stdev
**4.26**, saturation stdev **0.023**. That is the flattest surface on the
building, and by some margin the flattest surface in either venue.

Root cause is in the core: `gable_roof` (`kit.py:196-214`) builds each course as
a **single slab spanning the full roof depth** —
`M.box(seg * 1.22, 0.055, d, ...)`. There are no individual tiles. Consequently:

- No per-tile colour variance. Art Bible §4 requires *Terracotta roof (aged)
  `#8F4E36` — variation, ~30% of tiles*. Zero present.
- No §6 jitter (±3% position, ±2° rotation, ±4% scale) on what is the most
  repeated element in the town.
- No vertical joint lines, so the roof has one axis of rhythm instead of two.
- The 0.16 m course exposure resolves to ~2 px at the approach camera and aliases
  into a uniform hatch rather than a countable rhythm.

The result reads as painted corrugated sheet — a material Hearthmere does not
have (§2).

**Fix, in `core/kit.py` so every venue benefits:** subdivide each course into
individual tiles along `d` at ~0.20 m pitch; assign ~30% the aged variant;
apply §6 jitter per tile. Critically — **at distance a roof reads through albedo
variance, not geometry**, so the per-tile colour split is the fix that actually
moves the approach shot. Keep the 0.16 m physical exposure but deepen the lap
shadow so the courses survive to 25 m.

Secondary: the dormer roofs render markedly darker/more maroon than the main
roof, and the dormer cheeks read grey against cream plaster. Two roofs on one
building should share a material family.

### 5. `canvas` is the striped market-awning material — the laundry is awning cloth

`materials.py:677` maps `"canvas"` → `canvas_awning(**k)`, `stripe=True` by
default: cream with `#9C4A3C` stripes, i.e. the market stall awning. The balcony
laundry requests `"canvas"` (`inn.py:176`).

Result: four red-and-white striped cards on the balcony. It reads as offcuts of
stall awning, not as household linen. (The same lookup is wrecking the guild's
quest board — see `guild-01.md` defect 5.)

Compounding, same lines: `M.box(..., 0.008, 0.0, "canvas")` — **chamfer 0.0**,
violating Art Bible §6 and hard constraint 5 — and the only variation applied is
a ±0.05 rad Z rotation. They are flat rectangular cards with no drape, no sag
between pegs, and no thickness cue.

**Fix:** point the laundry at `cloth_cream` (already in the registry,
`materials.py:693`) or a new `linen` material; restore the chamfer; and give each
piece a catenary sag plus a slight out-of-plane bow so it reads as cloth over a
rail rather than card taped to the balcony.

### 6. Windows are plate glass with a stone-rubble sill

`leaded_window` (`kit.py:332-357`) builds one glass box plus a single
mullion/transom cross — **four panes of roughly 0.40 × 0.50 m each.** Art Bible
§2 permits *"hand-blown glass (small panes only, leaded cames)"* and forbids
plate glass. At half a metre square these are plate glass. There are no cames,
no lead grid, no pane-to-pane variation.

Separately, the sill (`kit.py:354`) uses material `"stone"` =
`foundation_stone()`, the coursed-rubble street material, authored at 2 m world
coverage. On a 1.1 m sill you see two or three cobbles the size of a fist. This
is visible in `inn-gameplay.png` — the sills look like they were paved. It is a
texel-density / material-class error, and it repeats on every window in the town.

**Fix:** subdivide the glass into a came grid at 0.12–0.18 m panes with thin iron
cames, and jitter per-pane tint and roughness slightly so the glass reads as
hand-blown rather than float. Give `leaded_window` a dressed-stone sill material
and a `uv_scale` parameter so sills, thresholds and copings stop inheriting
street-paving texel density.

### 7. Facade is mirror-symmetric

`win_1` at ±3.6, ±1.2 and `win_2` at ±2.9, 0.0 (`inn.py:134-135, 149`) are
perfectly symmetric about centre. The dormers at −3.0 / +0.6 are the only
asymmetry on the whole elevation, and the timber studs are evenly spaced at
identical section throughout.

`docs/REFERENCES.md` lists **"Symmetry. Hand-built settlements have none. Centred
doors are a tell"** in the anti-reference list. Art Bible §6 requires *"Every
building has at least one element that is visibly wrong — a sagging beam, a
patched wall, a replaced shutter of different wood."* There is no such element.

Compounding it: there is not one diagonal brace anywhere in the frame. A real
half-timbered wall braces against racking, so a frame of pure verticals and
horizontals is both structurally illiterate and — more importantly here —
visually monotone. The bay rhythm has no accent.

**Fix:** jitter the window bay positions by ±0.25 m and break the mirror; add
diagonal braces to at least the ground-floor corner bays (they also break up the
grid); and give the building its one wrong thing — a sagging first-floor sill, a
patched infill panel of different plaster tone, one shutter in unpainted oak.

### 8. Timber frame reads as two different woods glued together

The horizontal rails render markedly lighter and yellower than the vertical
studs (sampled: rails ≈ `#C8BEA9`, studs ≈ `#7C6343`). They read as raw pine
battens applied over the plaster rather than as structural members of the same
oak frame. Every joint is a plain butt overlap — no notch, no peg, no chamfered
arris where the rail crosses the stud.

Art Bible §2: *"Every join must be physically explicable — if it holds weight,
show how."*

**Fix:** bring rails and studs into the same tone family (differentiate by
exposure weathering, not by base colour — sun-facing members lighten, sheltered
members stay dark, which also solves defect 9); add visible peg ends at the
principal joints; chamfer the arrises so the rail/stud crossings catch light.

### 9. No water logic, no ground contact

Art Bible §5 requires streaking below every ledge, splash dirt on the bottom
0.15 m of every wall, and touch polish where hands go. Present: none of it.

- Roughly thirty window sills, not one streak below any of them — and
  `kit.py:353` documents the sill as *"sloped to throw water — and the source of
  the streaks below it."*
- The jetty undersides are the largest drip edges on the building. No staining.
- The wall meets the cobble apron at a razor line. No splash zone, no dirt
  wedge, no moss.
- The cobble apron itself terminates in a hard straight edge into the ground
  plane, with no transition, loose stones, or dirt feathering. It reads as a rug
  thrown down rather than paving laid against a building.
- The mounting-block steps (`inn.py:254-257`) use `"stone"` while the apron reads
  tan — two stone materials meeting with no relationship.

**Fix:** `lime_plaster()` already accepts a `wall_height` parameter — use it to
drive both the ground splash band and the sill streaking as height-driven
gradients, and apply the same pattern under the jetties. Feather the apron edge
with a scatter of loose stones and a dirt transition.

### 10. Props: right instincts, wrong materials

- **The cat and the boots are carved from oak.** `inn.py:228` and `inn.py:234-237`
  both use `"oak_weathered"`. A `leather` material already exists
  (`materials.py:698`). The cat currently reads as a brown lump on a sill and
  the boots as two wooden pegs — at the gameplay camera neither is identifiable,
  which wastes two of the best residue ideas in the venue.
- **The barrel reads as a galvanised tank.** Sampled saturation **0.04** —
  effectively neutral grey — against `oak_weathered` at 0.48. Worth checking the
  material binding. Geometrically it is a 16-segment lathe, which gives a smooth
  revolve rather than staves, and the hoops project only 6–14 mm. Per §2, iron
  hoops should show hammer facets and stand proud enough to catch light. As
  rendered it is the most anachronistic-looking object on the building.
- **The bench legs are 55 mm in section** (`kit.py:570`) and read as wires
  holding up a plank. Widen to 100–140 mm in the viewing axis and add a stretcher
  rail between the legs.
- **Nothing is mid-task.** Art Bible §7: *"a modest room with a stool knocked
  over and tools mid-task reads as inhabited."* Every prop here is tidily placed.
  The cheapest fix in the venue: turn the bench 15° out of parallel, put a mug on
  it, leave the barrel's lid off and leaning against it.

---

## Blocking review-rig issue (not a venue defect)

The ground in both venue renders is
`MeshStandardMaterial({ color: 0x6E6A5E })` on a flat plane
(`tools/render/viewer.html:107-109`). Measured high-frequency variation:
**0.00** — a mathematically constant colour, not a low-detail texture.

`docs/REFERENCES.md` ends its anti-reference list with *"Flat ground. A texture
plane under buildings kills an otherwise good shot."* Consequently **defect 9's
ground-contact work cannot be judged from these renders at all**, and both
approach shots are being scored against a backdrop that no player will ever see.
`town-arrival.png` proves the client has real paving (HF stdev 11.09).

Fix in the rig before resubmission. This affects every venue.

---

## What is working

Preserve these.

- **The jettied massing is genuinely good and is the best thing in either venue.**
  Two oversailing storeys give the building a real silhouette, and the deep
  horizontal shadow each jetty throws is doing exactly the job the module
  docstring claims — it separates the storeys so the building never reads as one
  extruded slab. This is AAA-grade compositional thinking. Do not touch it.
- **The dormers.** Correct scale, correct proportion, and they break the ridge
  line properly. They are the reason the silhouette scores 6 instead of 3.
- **The balcony.** The best piece of joinery in the town — eleven balusters, a
  proper rail, a deck with visible thickness. It is currently the only complex
  silhouette element on the facade and it reads well at the approach camera.
- **The plaster material.** HF stdev 38.41 — by far the most surface response of
  any material reviewed, roughly 7× the ashlar. `lime_plaster()` is the reference
  standard the other materials should be brought up to.
- **The lantern by the door.** Real cage geometry with a warm pane; the only prop
  that reads correctly at the gameplay camera. It also correctly carries a light
  entity at the palette's `#FFB35C` / 1.8.
- **The residue *inventory* is right.** Boots, cat, laundry, bench, barrel,
  mounting block — and the mounting block especially is a genuinely thoughtful
  inclusion, because it implies travellers arrive on horseback and nobody asked
  for it. The problem is execution and material, not selection. Keep the list.
- **Storey heights and door proportions.** Checked against the 1.75 m figure and
  the §3 table; they hold. Scale truth is not the problem here.

---

## Required before resubmission

1. Interior shell + warm emissive in every window. (Highest impact by a wide margin.)
2. Un-bury both chimneys; relocate the smoke emitters to the stack tops.
3. Rotate, raise and rescale the heron sign so the bird reads in silhouette.
4. Per-tile roofs with ~30% aged variant and §6 jitter — fix in `core/kit.py`.
5. Repoint laundry off `canvas`; restore chamfer; add drape.
6. Leaded came grid on the glass; dressed-stone sills at correct texel density.
7. Break the facade symmetry; add braces; add the one deliberately wrong element.
8. Sill streaking and ground splash via the existing `wall_height` mechanism.
9. Leather for boots and cat; fix the barrel; widen the bench legs; leave one
   thing mid-task.
10. Re-render on a real ground material.
