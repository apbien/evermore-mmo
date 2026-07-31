# Adventurer's Guild — Review 1

**Verdict:** REJECT
**Renders:** `review/shots/guild/guild-approach.png`, `guild-gameplay.png`, `guild-detail.png`
**Context:** `review/shots/town-arrival.png`

---

## First impression (before analysis)

A grey box with a taller grey box next to it, and a red beach towel hanging on
the tall one. It reads as a blockout that someone stopped texturing halfway
through. The tower is a featureless slab. My eye had nowhere to go and nothing
told me this was the most important building in town.

Second beat, at the door: I noticed the doors are open and there is a *wall*
behind them.

---

## Blind AAA comparison

Against **WoW / Boralus** (silhouette clarity, palette discipline) and
**GW2 / Divinity's Reach** (set-dressing density).

A player would pick this out as the amateur work instantly, and they would do it
from 60 m without ever seeing the detail work. Boralus's harbourmaster buildings
read at distance because the primary mass carries a *secondary* tier — brackets,
oriels, chimneys, projecting stair towers, signage arms — that chews up the
outline. This building's entire secondary tier is five half-height merlons.

Put the `guild-approach.png` frame next to a Divinity's Reach street capture and
the difference is not "less detail." It is that one is a *building* and one is a
massing study with props leaned against it. This would embarrass itself in a
screenshot comparison, and the reason is composition, not texture budget.

**Would people play this?** They would walk past it. That is the specific
failure — the World Bible makes this the player's "what do I do next" anchor,
and nothing about it earns a second look.

---

## Scores

| Axis | Score | Note |
| --- | --- | --- |
| Silhouette | **3** | Two rectangles and a triangle. Only merlons break the outline, and they are half-height. |
| Material truth | **4** | Ashlar reads as painted cardboard; banner reads as red masonry; parchment reads as market awning. |
| Lighting response | **4** | No rim separation on the hero silhouette (measured +6.8 lum at the tower edge — antialiasing noise). Flat facets everywhere. |
| Detail hierarchy | **3** | Primary tier jumps straight to tertiary. The middle is missing entirely. |
| Wear & story | **3** | No ground contact, no water streaking, no traffic wear. The "dished" threshold is a plain box. |
| Life & residue | **4** | Intent is genuinely good; execution is undermined by the striped-parchment bug and a sealed interior. |
| Cohesion | **5** | The "imported stone" concept works. The striped-canvas bug wrongly ties it to the market stalls. |
| Scale truth | **6** | Masses and door heights check out. Merlons and tower proportion do not. |
| AAA comparison | **2** | Picked out instantly, at any distance. |

**Acceptance requires no axis < 7 and AAA ≥ 8. Seven axes block.**

---

## Defects

### 1. The doorway is not a doorway — the hall is a sealed stone box

`guild.py:174-181` builds the hall as four solid `M.box` walls. **No aperture is
ever cut.** The tall double doors at `guild.py:222-226` are therefore hung
against unbroken ashlar, and the porch recess bottoms out in a flat stone wall
with the same running-bond coursing as the exterior — clearly visible in
`guild-detail.png`.

Consequence: the reception counter at `guild.py:366-368` (`z = zf + 3.6`) is
entombed inside the sealed hall. It is generated, it costs triangles, and no
camera in the world can see it. The World Bible brief — *"Interior visible from
the door: a stone hall, a reception counter, a big map on the wall, weapon racks,
adventurers loitering"* — delivers zero of five.

This is the defect that makes the building read as scenery rather than
architecture, and it is the highest-value fix available.

**Fix:** cut a real 3.2 × 2.8 m opening through the front wall (build the front
elevation as jamb + jamb + lintel spanner boxes rather than one box). Behind it,
place at minimum an interior shell: dark floor, a ceiling plane at 2.7 m to kill
the sky flood, and a warm emissive patch (`#FFD9A0`, the palette's *Window
interior spill*) so the opening reads as a lit hall rather than a hole. The
counter then lands in view where it was always meant to be.

### 2. Silhouette has no secondary tier

The black-on-white test (Art Bible §6: *"If the object is boring in
black-on-white silhouette, no amount of texturing saves it"*) returns two
rectangles and one triangle. The only outline break is the merlon row. The quoin
ladders produce a ~5 cm serration down each corner, which at 25 m is not
architecture — it reads as a rendering artifact.

Contributing specifics:
- **Merlons are half-height.** `guild.py:262` builds them 1.06 m wide × **0.62 m
  tall** on a 15.5 m tower. Period merlons run 1.2–1.8 m. At this proportion they
  read as toy battlement.
- **Tower proportion.** 5.2 × 5.2 × 15.5 m is a 3:1 slab with a flat top and no
  taper, string course, or corner articulation above the parapet. It reads closer
  to a chimney stack than a tower.
- **The banners do not break the outline.** All four are flush to their wall
  face, so in silhouette they contribute nothing — see defect 4.
- **The tower/hall junction is a bare butt joint.** No valley, no flashing, no
  weathering course where the hall roof dies into the tower.

**Fix — this is the rebuild.** The massing needs a designed secondary tier before
any further texture work is worth doing. Cheapest high-yield additions, in order:
a projecting entrance canopy or porch gable that oversails the threshold; a
corner stair-turret or garderobe projection on the tower breaking the 15.5 m
vertical run; a flagstaff angled off the parapet; full-height merlons; a
chimney on the hall. Re-run the silhouette test before texturing.

### 3. Ashlar has no surface

Measured high-frequency luminance variation (surface microstructure, blur-6
residual) on a clean sunlit wall:

| Surface | Distance | HF stdev |
| --- | --- | --- |
| Guild ashlar | ~1.5 m (`guild-detail`) | **5.31** |
| Guild ashlar | 3.5 m gameplay camera | **6.96** |
| Inn plaster (same town, same rig) | sunlit | **38.41** |

The plaster is doing 5–7× more work than the ashlar. The `ashlar()` generator in
`materials.py:552` is well-authored — joint recess, per-block colour, tooled
face, cavity dirt — but almost none of it survives into the render. At the
gameplay camera the wall is a flat gradient with a faint line grid drawn on it,
which is exactly the "painted cardboard" anti-reference.

**Fix:** raise the joint height amplitude (`m.add_height(-jm * 0.55)`) and the
normal-map derivation strength until a sunlit ashlar wall at the 3.5 m gameplay
camera measures HF stdev in the **15–25** band — i.e. parity with the plaster.
The chisel-mark octave (`ridged(s, 64, ...)` at 0.10) is roughly 3 cm features
and is contributing nothing visible; either strengthen it or spend the budget on
joint depth instead, which is what actually reads at range.

### 4. The banner is a quilt of 72 boxes and reads as red masonry

`guild.py:132-147` builds each banner as a 12 × 6 grid of separate `M.box`
panels, each tilted individually, overlapping at 1.06 × 1.35. The code comment at
`guild.py:139-141` already identifies the failure mode ("*those seams read as
venetian-blind striping*") and asserts the current overlap solves it. **It does
not.** In `guild-approach.png` the banner shows twelve hard horizontal bands with
offset vertical breaks — a running-bond pattern. The guild's identity banner
reads as a red brick wall hanging on a beige brick wall.

Also: `chamfer=0.0` on every panel, violating Art Bible §6 / hard constraint 5.

**Fix:** build the banner as **one** continuous chamfered surface — a single
subdivided quad whose vertices carry the catenary bow and the wind lift as
displacement. No seams, no per-panel lighting discontinuity. The
`banner_cloth` material (`materials.py:588`) is good and needs no change; it is
being destroyed by the geometry.

### 5. `canvas` is the striped market-awning material — the quest board is candy-striped

`materials.py:677` maps `"canvas"` → `canvas_awning(**k)` with `stripe=True` by
default: the market stall awning, cream with `#9C4A3C` stripes. The quest board
notices (`guild.py:96`) and the bedroll (`guild.py:351`) both request `"canvas"`.

Result: seventeen red-and-white striped cards pinned at random angles to a rack
of horizontal poles. **The single most important interactable in Hearthmere reads
as laundry on a drying rack.** There is no `parchment` material in the registry
at all.

Compounding: the wax seals (`guild.py:111`) use `"painted"`, which is
`painted_wood(colour=P.INN_GREEN)` — the inn's shutter green. The seals render
as small green dots.

**Fix:** add a `parchment` material — warm off-white base, fibre grain, an
age-driven sun-bleach gradient and edge darkening, high roughness. Point the
notices and bedroll at it. Add a `wax` material (deep red, low roughness, slight
subsurface warmth) for the seals. This is close to a one-line change per callsite
and it is the cheapest large improvement available on this venue.

The board's *composition* is right — the age spread, the curl, the torn-corner
logic, the deliberate gaps. It is being wrecked by two material lookups.

### 6. Tower lancet windows are buried inside the wall

`guild.py:277-279` places 0.16 m-deep `"glass"` boxes at
`tz ± (TOWER_W*0.5 - 0.20)` = ±2.40, spanning ±2.32…±2.48. The tower wall boxes
occupy ±2.10…±2.60. **The slits sit entirely within the wall thickness.** This is
why the tower renders as a blank 15.5 m slab with no fenestration whatsoever —
the vertical rhythm the docstring promises does not exist.

**Fix:** push the glass to the outer face and cut a reveal — jamb boxes plus a
head and cill, with the glass set back 0.12 m so the opening throws a shadow.
Give them a dark interior backing so they do not read as pale patches.

### 7. Entrance banners collide with the quest board

`guild.py:301-305` places the flanking banners at `x = ±3.05, z = zf - 0.12`. The
quest board sits at `x = -4.25, z = zf - 0.34` — in front of and overlapping the
-X banner. In `guild-gameplay.png` you can see a crimson strip clipping through
the notice rack, and in `guild-approach.png` a second banner is stranded in the
porch shadow where nothing sees it.

**Fix:** move the flanking banners outboard of the quest board and the weapon
rack, or delete them — the tower banners already carry the identity, and two more
in the shadow add clutter, not density.

### 8. No ground contact, no wear logic

Art Bible §5 requires ground contact splash on the bottom 0.15 m of every wall,
water streaking below every ledge, and touch polish where hands and boots go. The
guild has none of it:
- The plinth meets the ground at a razor line. No dirt build-up, no debris, no
  darkening.
- The string course at `guild.py:191` is a continuous drip ledge running the full
  perimeter and there is not one streak below it.
- `guild.py:217` builds the threshold as a plain chamfered box while the comment
  above it says "dished by decades of boots." Nothing is dished.
- Zero traffic wear at the doorway of a building the brief says never closes.

**Fix:** dish the threshold with real geometry (a shallow lathe or a displaced
quad, ~25 mm at the centre, offset toward the doorway's traffic side, and 25 mm
irregular chamfer per §6 "worn/ancient stone"). Add the splash-dirt band and the
string-course streaking to the `ashlar` material as a `wall_height`-driven
gradient — `lime_plaster()` already takes a `wall_height` parameter for exactly
this, so the pattern to copy is already in the core.

### 9. No rim separation on the hero silhouette

Measured at the tower's sunlit edge against sky: **+6.8 luminance** over the
interior wall — within antialiasing noise. Art Bible §1 names rim light as *"the
single strongest anime-3D signature"* and requires it on every hero object. The
town's anchor building has none.

The rig does add a rim light (`viewer.html:100-104`, intensity 1.15 vs the
palette's 1.4), so this is not a missing light. It is that **a directional
back-light cannot produce a rim on a flat-sided box.** A rim needs curvature at
the silhouette edge, and the 15 mm architectural chamfer is sub-pixel at the 25 m
approach distance.

**Fix:** two parts. (a) Raise rim intensity to the specified 1.4. (b) More
importantly — give the tower corners something for the rim to catch: a projecting
pilaster, a rolled quoin profile, or a chamfer scaled to viewing distance rather
than to the §6 table. The §6 chamfer spec is authored for a 2 m viewing distance;
hero silhouettes judged at 25 m need geometry, not a chamfer.

### 10. Code hygiene

`guild.py:309`: `tile_mat="slate" if False else "terracotta"` — a dead debug
toggle. CLAUDE.md asks that generators stay readable because they are the source
of truth for the art.

---

## Blocking review-rig issue (not a venue defect)

The ground under the building in both venue renders is
`MeshStandardMaterial({ color: 0x6E6A5E })` on a 400 × 400 plane
(`tools/render/viewer.html:107-109`). Measured high-frequency variation:
**0.00**. It is not a low-detail ground, it is a mathematically constant colour.

`docs/REFERENCES.md` closes its anti-reference list with *"Flat ground. A texture
plane under buildings kills an otherwise good shot."* This is worse than a
texture plane, and it means **ground contact, splash wear, worn paths and the
building's relationship to the street cannot be judged from these renders at
all.** `town-arrival.png` proves a real cobble ground exists in the client
(HF stdev 11.09).

Fix in the rig before the next submission: use the client's actual paving
material for the review ground. This affects every venue's review, not just this
one.

---

## What is working

Preserve these. They are the parts worth rebuilding around.

- **The concept is correct and it is legible.** Dressed ashlar and a square tower
  against a town of timber and plaster genuinely does say "outside money, not
  from here" without a word of exposition. Keep it.
- **The quoin generator** (`_quoin_column`, `guild.py:38`). Alternating long/short
  with per-block jitter is the right way to build quoins and the rhythm reads
  correctly at the gameplay camera. It is the one piece of the stonework doing
  real work.
- **The quest board's composition logic** (`_quest_board`, `guild.py:59`). Age
  driving colour, curl, rotation and squareness simultaneously; pins on all,
  seals on half; overlapping placement rather than a grid. This is exactly right
  and is being destroyed only by the material lookup. Do not rewrite it — repoint
  it at a `parchment` material.
- **The weapon rack's missing weapon** (`guild.py:333-334`, the `i == 2` skip).
  One deliberate gap that implies somebody is out on a job is worth more than ten
  more props. This is the best single storytelling decision in the venue.
- **The pack and bedroll dumped by the threshold.** Right instinct, right place —
  they read as something set down, not as placed set dressing.
- **The `ashlar` and `banner_cloth` material generators themselves.** Both are
  well-authored with multi-source roughness, per-block variance and physically
  motivated staining. The failures above are geometry and UV problems, not
  authoring problems. Do not touch these except to raise the ashlar height
  amplitude.
- **The porch recess as a compositional device.** Putting the quest board in
  shadow so the parchment reads against a dark ground is correct thinking. It
  will work properly once the parchment is parchment.

---

## Required before resubmission

1. Cut the doorway; add an interior shell with warm emissive.
2. Redesign the massing for a secondary silhouette tier; re-run the black-on-white
   test before texturing.
3. Add a `parchment` material and a `wax` material; repoint notices, bedroll, seals.
4. Rebuild the banner as one continuous displaced surface.
5. Un-bury the tower lancets.
6. Raise ashlar surface response to HF stdev 15–25 at the gameplay camera.
7. Ground contact wear, string-course streaking, a genuinely dished threshold.
8. Fix the entrance-banner / quest-board collision.
9. Re-render on a real ground material.
