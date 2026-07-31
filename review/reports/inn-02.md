# Grey Heron Inn — Review 2

**Verdict:** REVISE
**Renders:** `review/shots/inn/inn-approach.png`, `inn-gameplay.png`,
`inn-detail.png`, `inn-silhouette.png`
**Context:** `review/shots/town-arrival.png`
**Reviewed against:** `review/reports/inn-01.md`

---

## First impression (before analysis)

Two chimneys. They clear the roof, they are different heights, and the roofline
finally has something on it. That is a genuine fix and I saw it in the first
second.

Then the same second read as last time, unchanged: **I cannot see into a single
window.** Every pane on the facade is the same cream as the wall around it. At
the gameplay camera you can watch the plaster's own surface marks run straight
through the glass without a break. Nobody lives here.

Third beat: the roof is a single sheet of orange. It was the flattest surface in
either venue last review and it still is.

---

## Blind AAA comparison

Against **FFXIV / Gridania**.

The gap is where it was. One defect was fixed and it was not the one that costs
the score.

In Gridania every window is warm-lit, dark, or shuttered — never wall. Here,
measured at the gameplay camera, a first-floor pane reads **154.6** mean
luminance against the plaster immediately beside it at **154.4**. A delta of
**+0.2**. The window is not merely *similar* to the wall; it is the wall,
to within a fifth of a luminance level. The panes even carry *more* fine detail
than the plaster does (HF 42.1 vs 14.8) because you are looking at the wall
behind through transparent glass at a longer texture stride.

The World Bible says this building must be "the most inviting thing in the
frame." The brightest pixel inside any window measures lum 198 with a red-blue
skew of +26 — that is sunlit plaster, not firelight. The one real light source on
the facade, the lantern by the door, peaks at lum **127**. The inn's lamp is
dimmer than its walls.

**Would people play this?** Same answer as review 1: they would walk toward it,
and be disappointed at the door. Nothing in this pass changed that.

---

## Scores

| Axis | R1 | R2 | Note |
| --- | --- | --- | --- |
| Silhouette | 6 | **7** | The chimney fix is real and it is the best silhouette work on the building. Sign still contributes nothing to the outline. |
| Material truth | 4 | **3** | None of six material defects fixed. Roof measures flatter than the guild's ashlar. Sills are still street cobble. Barrel still reads galvanised. New: the shutters carry a visibly tiling blob motif. |
| Lighting response | 5 | **4** | Windows at exactly wall value. Zero emissive in the delivered renders. Roof LF stdev 3.56 — no form revealed anywhere on the largest surface. |
| Detail hierarchy | 6 | **6** | Unchanged. Still the best-structured venue; tertiary tier still mostly failing to read. |
| Wear & story | 4 | **4** | Unchanged. Measured: wall luminance 189.2 → 190.2 over the last 0.9 m down to the sill beam. Flat. No streaks under ~30 sills. |
| Life & residue | 5 | **5** | Inventory still right, execution still wrong. Lit windows would have moved this; they are not in the render. |
| Cohesion | 7 | **7** | Still the strongest axis. It still looks like Hearthmere. |
| Scale truth | 7 | **7** | Unchanged and still holds against the §3 table. |
| AAA comparison | 4 | **4** | The plaster-filled windows alone still give it away, in the first second. |

**Acceptance requires no axis < 7 and AAA ≥ 8. Six axes block.**

---

## Status of every defect enumerated in inn-01

### 1. Every window is filled with wall — there is no interior → **NOT RESOLVED**

This was flagged as *"the defect that costs the most AAA score. Nothing else on
the building matters as much."* It is not fixed in any submitted render.

Measured, `inn-gameplay.png`, pane interior vs plaster immediately adjacent:

| Window | Pane mean | Wall mean | Delta | Pane HF |
| --- | --- | --- | --- | --- |
| 1st floor, x≈360 | 154.6 | 154.4 | **+0.2** | 42.1 |
| 1st floor, x≈655 | 157.7 | 154.4 | **+3.3** | 41.7 |
| Ground, x≈530 | 172.7 | — | at plaster value | 35.7 |
| Ground, x≈825 | 176.1 | — | at plaster value | 33.3 |

Zoom `inn-detail.png` on any window and the plaster's pale surface marks continue
across the panes and across the mullion at the same scale. Brightest pixel found
inside any window: (206, 198, 180) — daylight on lime render.

**Two separate root causes, and the builder needs both.**

**(a) The unlit glass is transparent.** In `assets/meshes/inn.gltf` the material
named `glass` carries `"alphaMode": "BLEND"`. It is alpha-blended onto whatever
is behind it, which is the sunlit inner face of the far wall. No interior shell
was added to the inn — `_storey` still builds four walls and nothing else. The
claim that *"interior shells added to guild/inn/pub so openings read dark"* holds
for the guild (measured interior mean 23.6, correctly dark) and **does not hold
for the inn's windows**, which are the thirty apertures that matter.

**(b) The lit-window work is real but was never rendered.** `glass_lit` exists
(`materials.py:487-529`), the emissive texture is bright and correct
(`glass_lit_emissive.png`, mean RGB 239/229/175), and `inn.py` points the ground
floor, ~70% of the first floor, ~55% of the second and both dormers at it. But:

| File | Written |
| --- | --- |
| `review/shots/inn/inn-gameplay.png` | 20:56:05 |
| `review/shots/inn/inn-detail.png` | 20:56:09 |
| `review/shots/inn/inn-silhouette.png` | 20:56:10 |
| `assets/textures/glass_lit_albedo.png` | **21:01:10** |
| `review/shots/inn/inn-approach.png` | 21:02:01 |
| `assets/meshes/inn.gltf` | **21:04:51** |

Three of the four submitted renders predate the existence of the lit-glass
material by five minutes, and **all four predate the mesh that references it.**
CLAUDE.md: *"Verify visually before claiming done… An asset you have not seen is
not finished."* The headline fix of this pass was submitted unseen.

**Actions:**
- Add the interior shell per storey — dark floor, ceiling at 2.70 m, low-value
  interior wall — so the apertures are backed even where the glass is unlit. The
  guild's `guild.py:203-207` is the pattern; copy it.
- Re-render after `make assets`, every time, and look at the image before
  submitting.
- Latent issue to fix while you are in there: `MaterialSet` writes emissive as
  `linear_to_srgb(np.clip(self.emissive, 0, 1))` (`materials.py:150`). The
  `* 2.4` multiplier in `leaded_glass(lit=True)` is clipped away to 1.0. The lit
  and unlit variants currently differ only by base colour and by 0.28 vs a
  clipped 1.0. Any future attempt to brighten the glow above 1.0 will silently do
  nothing.

### 2. Both chimneys generated entirely inside the roof → **RESOLVED**

`inn.py:229-236` derives `ridge_h = ((D2 + 1.0) * 0.5) * pitch` — correctly
accounting for `gable_roof` adding the overhang to the span — and sizes each
stack to `ridge_h + 1.6 + i * 0.35`. Both stacks clear the ridge, they are
asymmetric in height and position, and they read in `inn-approach.png` and in
`inn-silhouette.png`. Smoke entities moved to the stack tops. Clean fix.

Two follow-ons, both from the original defect text and both still open:

- **No flaunching or weathering collar** where the stack penetrates the roof.
  Review 1 asked for one. The stacks currently emerge from the tile plane at a
  razor line.
- **Section 0.72 m** on a 13 m facade reads thin at the approach camera. Take
  them to ~0.9 m.

Credit where due: the occlusion tripwire in `core/venue.py:87` caught this bug
again after the first fix attempt was still 0.3 m short, and the commit message
says so plainly. That is the check doing exactly the job it was built for.

### 3. The heron sign carries no heron → **NOT RESOLVED**

`_heron_sign` is unchanged.

- **Still parallel to the facade.** In `inn-gameplay.png` (a straight-on view) the
  sign presents as a wide board. If it had been rotated to hang perpendicular off
  its bracket, it would read as a thin sliver from this angle. It does not. It
  contributes nothing to the silhouette, and the World Bible names it the inn's
  anchor element.
- **Still collides with the window band.** In `inn-gameplay.png` the board
  visibly overlaps the ground-floor window head to its right.
- **The bird still does not read.** Measured board mean lum 45.5. At the gameplay
  camera the heron is three pale scratches on a dark rectangle.

### 4. The roof is one uniform sheet → **NOT RESOLVED**

Clean sunlit patch, `inn-approach.png`: **HF stdev 3.49, LF stdev 3.56.** For
scale, the guild's much-criticised ashlar measures HF 5.28. The roof is the
flattest surface in either venue, again.

Confirmed at source: `tools/assetgen/core/kit.py` was last modified in
**`c20b6de`**, long before review 1. `gable_roof` is untouched — each course is
still `M.box(seg * 1.22, 0.055, d, ...)`, one slab spanning the full roof depth.
Zero individual tiles, zero per-tile colour, zero §6 jitter, no vertical joints.
Art Bible §4 requires ~30% of tiles in `TERRACOTTA_AGED #8F4E36`; the count is 0%.
Against §8's *"Full PBR set present; no flat/uniform channels"* this is a
straight fail.

The hue itself is palette-compliant (measured `#BE693D` against `TERRACOTTA
#B5603E`). It is the uniformity, not the colour, that reads as painted
corrugated sheet.

Unchanged fix, and it belongs in core so every roof in Hearthmere benefits:
subdivide each course into tiles at ~0.20 m along `d`, assign ~30% the aged
variant, apply §6 jitter. **At distance a roof reads through albedo variance, not
geometry** — the colour split is the part that moves the approach shot.

Also still true: the dormer roofs render markedly darker and more maroon
(measured mean 63 / sat 0.47) than the main roof (mean 120 / sat 0.68). Two roofs
on one building, two material families.

Minor, same function: `kit.py:217-220` builds a `ridge` lathe, rotates and scales
it, and never adds it to the group. Dead geometry.

### 5. Laundry is awning cloth → **NOT RESOLVED**

`inn.py:186-188` unchanged:

```python
cloth = M.box(rng.uniform(0.30, 0.46), rng.uniform(0.40, 0.60), 0.008,
              0.0, "canvas")
```

Still `"canvas"` (the striped market awning), still `chamfer=0.0` in violation of
Art Bible §6 and hard constraint 5, still flat cards with a ±0.05 rad Z rotation
as the only variation. Visible as red-and-white striped rectangles on the balcony
in `inn-approach.png`. `cloth_cream` is sitting in the registry at
`materials.py:753`.

(The guild's quest board *was* repointed onto the new `parchment` material this
pass, which proves the fix is a one-line change per callsite. This callsite and
the guild's bedroll were simply missed.)

### 6. Plate glass with a stone-rubble sill → **NOT RESOLVED**

`leaded_window` (`kit.py:332-357`) unchanged. Still one glass box plus a
mullion/transom cross — six panes at roughly 0.40 × 0.40 m. Art Bible §2 permits
*hand-blown glass, small panes only, leaded cames*; at half a metre square these
are plate glass. No cames, no lead grid, no per-pane variation.

Sill still `mat="stone"` = `foundation_stone()`, the coursed-rubble street
material authored at 2 m world coverage, applied to a 1.1 m sill. Clearly visible
in `inn-detail.png`: the sills look paved. This repeats on every window in the
town.

### 7. Facade is mirror-symmetric; no braces; no deliberately wrong element → **NOT RESOLVED**

`inn.py` window arrays unchanged. **There is still not one diagonal brace
anywhere in the frame** — a half-timbered wall of pure verticals and horizontals
is structurally illiterate and visually monotone. There is still no element that
is visibly wrong, which Art Bible §6 requires of every building.
`docs/REFERENCES.md` lists *"Symmetry. Hand-built settlements have none"* in the
anti-reference list.

### 8. Timber frame reads as two different woods → **NOT RESOLVED**

Measured, `inn-gameplay.png`: horizontal rail `#B8AD97` (mean 174) against the
door-frame post `#5F4E3D` (mean 80). The rails still read as raw pine battens
applied over the plaster rather than as members of the same oak frame. Every
joint is still a plain butt overlap — no notch, no peg, no chamfered arris.

Art Bible §2: *"Every join must be physically explicable — if it holds weight,
show how."*

### 9. No water logic, no ground contact → **NOT RESOLVED**

Measured, `inn-detail.png`, luminance up the plaster from the sill beam:

| y (px) | 490 | 520 | 550 | 580 |
| --- | --- | --- | --- | --- |
| lum | 189.2 | 189.8 | 190.2 | 190.2 |

Dead flat over the last ~0.9 m of wall. No splash band, no dirt wedge, no moss.
Not one streak below any of roughly thirty sills, and `kit.py:353` still
documents the sill as *"the source of the streaks below it."* The jetty
undersides — the largest drip edges on the building — carry no staining. The
cobble apron still terminates in a hard straight line into the ground plane.

### 10. Props: right instincts, wrong materials → **NOT RESOLVED**

- **Barrel:** measured saturation **0.102** (review 1: 0.04) against
  `oak_weathered` at 0.48. Still reads as a galvanised tank and is still the most
  anachronistic-looking object on the building. Note this is the same symptom as
  the guild's new stair turret, which is also an `M.lathe` emitted with a warm
  material and also renders desaturated grey (sat 0.097 vs 0.253). **Two lathes
  in two venues both losing their material — this is a core `M.lathe` UV
  problem, not two coincidences.** Fixing it in core fixes both.
- **Bench legs** still 55 mm in section (`kit.py:570`), still read as wires
  holding up a plank. `kit.py` untouched.
- **Boots** now render as two grey-brown lumps (mean 97). Better than oak, still
  not identifiably leather at the gameplay camera.
- **Nothing is mid-task.** The bench is still parallel to the wall, the barrel is
  still lidded and upright. Art Bible §7. This is still the cheapest fix in the
  venue.

---

## New defect

### N1. The shutters carry a visibly tiling blob motif

At both the gameplay and detail cameras the green shutters show a brown
leaf-or-fish shape repeating on a regular grid at roughly 0.2 m, plus a
horizontal band of repeated identical marks running across every shutter at the
same height. It reads as printed wallpaper, not as weathered paint on oak. There
is also blue-cyan fringing along the plank edges, which is wrong on green paint.

This is two entries on the `docs/REFERENCES.md` anti-reference list at once —
*"Tiling texture at wrong scale"* and *"Banded procedural grain"* — on the most
repeated coloured element of the facade. `painted_wood()` needs a larger noise
period and a break-up octave, and the plank-edge highlight needs a warmer tint.

---

## Review-rig defects (not venue defects, but they block judgement)

1. **The silhouette render is unusable.** `viewer.html:288-290` applies the black
   override material to the entire scene including the ground plane, so **412 of
   900 rows (46%) of `inn-silhouette.png` are solid black ground.** The jetties,
   the balcony, the sign and the dormer cheeks — every silhouette element below
   eaves level — are swallowed. The image shows a plain gable with two chimneys.
   The Art Bible §6 black-on-white test cannot be run on it. Hide the ground
   during the silhouette pass.
2. **The approach-camera ground is still effectively flat.** The rig now uses the
   real cobble material and it works at the gameplay camera (HF 16.5), which is a
   genuine fix. At the approach camera the 2 m tile mips away: **HF 2.19**.
   Ground-contact work still cannot be judged from the approach shot.
3. **The scale figure is not at the building.** In `inn-approach.png` it stands
   well forward of the facade and cannot be used for the §3 check.
4. **Renders predate the assets.** Documented under defect 1. This is a process
   failure, not a rig bug, and it is the one that cost this pass its headline
   result.

---

## What is working

Preserve these.

- **The chimney fix, and the way it was found.** Deriving the stack height from
  the true ridge, offsetting the two stacks asymmetrically, and moving the smoke
  emitters to the tops — all correct. The build-time occlusion check independently
  catching the first attempt still being 0.3 m short is exactly the kind of
  tooling that stops this class of bug recurring. That check has now earned its
  place; extend its `label=` coverage to the guild's tower lancets, which its own
  docstring cites and does not currently test.
- **The jettied massing.** Still the best thing in either venue. Untouched, and
  it should stay untouched.
- **The dormers**, **the balcony**, **the plaster material**, **the lantern
  geometry**, **the residue inventory**, and **the storey heights** — everything
  review 1 listed as working still is. Nothing was broken in this pass.
- **`parchment` / `wax` / `glass_lit` as material work.** All three are
  well-authored. `glass_lit`'s reasoning — deliberately not lighting every
  window, because a uniformly lit facade reads as a lightbox — is the right
  instinct and I want to see it in a render.

---

## Required before resubmission — ranked by impact on the AAA score

1. **Re-render on current assets and look at the images.** Non-negotiable, and
   it comes first because it may already resolve part of defect 1. Nothing else
   on this list can be assessed until the renders match the build.
2. **Interior shell per storey**, so every aperture is backed even where the
   glass is unlit. The transparent `glass` material makes this mandatory, not
   optional. (Defect 1a)
3. **Per-tile roofs in `core/kit.py`** with ~30% aged variant and §6 jitter. The
   largest flat surface in the town, and the fix benefits every venue.
   (Defect 4)
4. **Fix `M.lathe` material mapping in core.** Recovers the barrel here and the
   guild's stair turret in one change. (Defect 10)
5. **Leaded came grid on the glass; dressed-stone sills at correct texel
   density**, with a `uv_scale` parameter so sills, thresholds and copings stop
   inheriting street-paving density. (Defect 6)
6. **Sill streaking and ground splash** via the `wall_height` mechanism already
   in `lime_plaster()`. (Defect 9)
7. **Rotate, raise and rescale the heron sign** so the bird reads in silhouette
   and stops clipping the window. (Defect 3)
8. **Break the facade symmetry; add diagonal braces; add the one deliberately
   wrong element.** (Defect 7)
9. **Bring rails and studs into one tone family**; add peg ends and chamfered
   arrises at the joints. (Defect 8)
10. Repoint the laundry off `"canvas"`, restore the chamfer, add drape.
    (Defect 5)
11. Widen the bench legs; leave one thing mid-task. (Defect 10)
12. Fix the shutter texture tiling period. (New N1)
13. Flaunching collars on the chimneys; take the section to ~0.9 m. (Defect 2
    follow-on)
14. Rig: hide the ground in the silhouette pass; place the scale figure at the
    facade; fix approach-camera ground mipping.
