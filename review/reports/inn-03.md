# Grey Heron Inn — Review 3

**Verdict:** REVISE
**Renders:** `review/shots/inn/inn-approach.png`, `inn-gameplay.png`,
`inn-detail.png`, `inn-silhouette.png`
**Context:** `review/shots/town-arrival.png`, `town-square.png`
**Reviewed against:** `review/reports/inn-02.md`

**Render/build freshness — checked, and clean.** All four inn shots are dated
21:35:01–21:35:10; `assets/meshes/inn.gltf` was written 21:34:19 and the newest
texture at 21:29:16. Every render postdates the build. The process failure that
cost review 2 its headline result did not recur.

---

## First impression (before analysis)

The dormers are lit. Two small bright windows up in the roof, and for a second
the building looks occupied.

Then the eye drops to the facade and it is the same building as last time and the
time before: **I still cannot see into a single window.** Every pane on all three
storeys is the same cream as the wall around it. Not similar — the same.

Third beat: the roof is one flat sheet of orange. Third review running, and it is
still the flattest surface in the town.

---

## Blind AAA comparison

Against **FFXIV / Gridania**.

The gap has not moved. Almost none of this pass's work landed here.

Measured at the gameplay camera, scanning across the first-floor window band:
plaster wall reads `(200, 192, 172)`; the pane interiors read `(200, 190, 168)`,
`(200, 190, 168)`, `(201, 191, 169)`, `(200, 189, 167)`. Luminance delta **−1.4**.
The brightest pixel anywhere inside a pane is `(206, 197, 179)` — review 2 found
`(206, 198, 180)`. That is the same number to within a rounding error, one round
later.

In Gridania every window is warm-lit, dark, or shuttered. Never wall. Here they
are wall, and at the detail camera the lime plaster's trowel marks and hairline
cracks run continuously across the panes, across the mullion, and back out onto
the facade without a break.

And the roof: **HF stdev 3.10, LF stdev 3.74** on a clean sunlit patch. For scale,
the guild's much-criticised flat ashlar measures 5.5. Nothing on this building's
largest surface reveals its form.

**Would people play this?** They walk toward it and are disappointed at the door.
Identical to reviews 1 and 2.

---

## Scores

| Axis | R1 | R2 | R3 | Note |
| --- | --- | --- | --- | --- |
| Silhouette | 6 | 7 | **5** | **Downgrade on honest re-measurement, not regression** — see below. Against white this is a box, a triangle, and two thin posts. Dormers, balcony, sign and jetties contribute essentially nothing. |
| Material truth | 4 | 3 | **3** | Panes are plaster. Roof HF 3.10. Sills are street rubble. Barrel sat 0.06 — worse than R2's 0.102. Shutters still tile a blob motif. Plaster itself remains good. |
| Lighting response | 5 | 4 | **4** | Dormers genuinely read as lit — the first emissive in this venue that survives to a render. Everything below the eaves is unchanged: panes at wall value, roof LF 3.74. |
| Detail hierarchy | 6 | 6 | **6** | Still the best-structured venue. Tertiary tier undermined by the windows being decals and by a structural rail crossing an opening (N1). |
| Wear & story | 4 | 4 | **4** | Plaster from the sill beam upward: 191, 191, 191, 192, 192, 192, 191, 190, 189. Dead flat over ~0.9 m. No streak below any of ~30 sills. Unchanged. |
| Life & residue | 5 | 5 | **5** | Laundry repointed and it reads — a real fix. Lit dormers help. Still nothing mid-task; barrel is grey. |
| Cohesion | 7 | 7 | **7** | Still the strongest axis. The laundry no longer ties the inn to the market stalls. It still looks like Hearthmere. |
| Scale truth | 7 | 7 | **7** | Holds against the §3 table at the gameplay camera. Noted below: storey heights are under spec, and the panes are plate glass by §2's definition. |
| AAA comparison | 4 | 4 | **4** | The plaster-filled windows give it away in the first second, for the third review running. |

**Acceptance requires no axis < 7 and AAA ≥ 8. Six axes block.**

**On the silhouette downgrade.** I scored this 7 in review 2 against a render
that was 46% solid black ground and unusable, on the strength of the chimney fix.
That was a score I should not have given. The rig is fixed, the test ran, and the
building failed it. The building did not get worse; my previous number was
unearned. I am correcting it rather than protecting it.

---

## The §6 black-on-white test, now that it can be run

`inn-silhouette.png` is clean. The result is the most important new finding in
this review.

What reads: a rectangular mass, a gable roof, two thin chimney posts, and about
four shallow steps down each flank where the jetties break the edge.

What does not read, at all:

- **The dormers.** They project forward, not sideways, so from the frontal
  silhouette camera their outline falls entirely inside the roof triangle. The
  inn's most characterful roof element contributes zero.
- **The balcony.** Absorbed into the wall plane.
- **The heron sign.** Absorbed — direct confirmation of defect 3 below.
- **The laundry.** Absorbed.
- **The base.** A dead-straight horizontal line across the full width. Nothing
  settles into the ground, nothing breaks it.

Everything I praised in reviews 1 and 2 — the jettied massing, the dormers, the
balcony — is doing its work through *shading only*. Against white this is a
child's drawing of a house. The two chimneys are the entire secondary tier, and
they are thin.

This is fixable without a rebuild, and cheaply: rotate the sign perpendicular,
push one dormer to the gable end where it breaks the roof edge, extend the
balcony rail past the wall line, hang the laundry proud on a pole, and let the
plinth and steps break the base line. None of that is a massing change.

---

## Status of every defect enumerated in inn-02

### 1. Every window is filled with wall → **NOT RESOLVED** (third round) — but the diagnosis was wrong, and here is the right one

The shell **was** added. `inn.py:101-107` builds an inverted `oak_dark` box
across all three storeys and emits it with `shell=True`. It is correct work, it
follows the guild's pattern as instructed, and it does nothing for the windows.
The doorway does read dark, which proves the shell functions.

It could never have helped, because **there is no aperture behind any window.**

`kit.py`, `timber_frame_wall`:

```python
infill = M.box(width, height, depth * 0.55, CHAMFER_ARCH, plaster_mat, uv_scale=0.5)
```

One solid plaster slab spanning the entire wall. The `openings` list is only ever
consumed by `blocked()`, which suppresses *studs and rails* — its own docstring
says the rectangles are left clear *"so doors and windows can be placed without
geometry interpenetrating."* Nothing is ever subtracted from the infill.

So every window on this building is a transparent glass box sitting in front of
solid, sunlit plaster. That is precisely why the panes measure the plaster's own
value to within 1.4 luminance levels, and why the plaster's surface marks
continue across them: **you are looking at the wall, through the glass, at point
blank range.** The interior shell is behind the wall and can never be seen.

My reviews 1 and 2 both prescribed "add an interior shell." That was the wrong
instruction and it cost this venue a round. The correct fix:

- **Build the infill in segments around each opening**, exactly as
  `guild.py:179-197` does for the guild's doorway — which is why the guild's
  doorway works and the inn's thirty windows do not. This is the whole fix; the
  shell already added will then do its job.
- While in there: `materials.py:150` still writes emissive as
  `linear_to_srgb(np.clip(self.emissive, 0, 1))`, so the `* 2.4` in
  `leaded_glass(lit=True)` is still clipped to 1.0. Latent, flagged in R2,
  unfixed. Any future attempt to brighten the glow will silently do nothing.

### 2. Chimneys — follow-ons → **NOT RESOLVED**

The stacks themselves remain correct and clear the ridge. Both follow-ons are
open: no flaunching or weathering collar where they penetrate the tile plane, and
the section is still thin — confirmed against white, where they read as posts.

### 3. The heron sign carries no heron → **NOT RESOLVED** (third round)

`_heron_sign` (`inn.py:51-93`) is unchanged in every respect that was criticised.

- **Still parallel to the facade.** The only rotation applied is
  `board.rotate_z(0.055)`. There is no `rotate_y`, so it presents as a wide board
  from straight on and vanishes in silhouette. Confirmed in `inn-silhouette.png`.
- **Still collides with the window band.** Visible in both `inn-gameplay.png` and
  `inn-detail.png`: the board overlaps the head of the window and its shutter to
  the lower right.
- **The bird still does not read** — and there is a reason I can now name. The
  heron's body, neck, beak and legs are all emitted with `mat="ashlar"`. A grey
  heron built out of dressed-limestone material, in low relief on a dark board,
  is why it renders as three pale scratches. Give it a pale painted material with
  some value contrast against the board, and deepen the relief.

### 4. The roof is one uniform sheet → **NOT RESOLVED** (third round)

Clean sunlit patch: **HF 3.10, LF 3.74** (R2: 3.49 / 3.56). Confirmed at source —
`git log -- tools/assetgen/core/kit.py` returns `c20b6de`, which predates review
1. `gable_roof` still builds each course as one slab spanning the full roof
depth. Zero tiles, 0% of the ~30% `TERRACOTTA_AGED` §4 requires, no §6 jitter.
Straight fail against §8's *"no flat/uniform channels."*

Dormer roofs still read as a different material family: mean **61.5** against the
main roof's **120**. Saturation now matches better (0.63 vs 0.68); the value gap
does not.

The dead `ridge` lathe in the same function is still built, rotated, scaled, and
never added to the group.

### 5. Laundry is awning cloth → **RESOLVED**

`inn.py:186-188` now reads
`"cloth_cream" if rng.random() < 0.6 else "cloth_blue"`. Visible in
`inn-approach.png` as pale and blue cloths on the balcony. The inn no longer
shares a material with the market stalls. Claim 6 holds here.

Residual from the original text, still open: `chamfer=0.0` on the cloth boxes
(hard constraint 5 / Art Bible §6), and they are still flat cards with a ±0.05 rad
Z rotation as the only variation. No drape.

### 6. Plate glass with a stone-rubble sill → **NOT RESOLVED** (third round)

`leaded_window` (`kit.py`) is unchanged. One glass box plus a mullion/transom
cross gives four panes at roughly 0.45 × 0.50 m; §2 permits *hand-blown glass,
small panes only, leaded cames*. No cames anywhere.

The sill is still `M.box(width + 0.28, 0.07, 0.20, 0.008, "stone")` —
`foundation_stone()`, the coursed-rubble street material authored at 2 m world
coverage, applied to a 1.1 m sill. Measured: the sill carries **HF 28.5**, higher
than the ground cobble beside it at 8.8. The windowsills are more coarsely
textured than the street. Visible in `inn-detail.png` as three or four boulders
under each window. Needs a `uv_scale` parameter so sills, thresholds and copings
stop inheriting paving density.

### 7. No braces, no deliberately wrong element → **NOT RESOLVED**

Still not one diagonal anywhere in three storeys of framing.

This one is nearly free. `timber_frame_wall` already supports
`style="cross"` — *"St-Andrew's cross bracing in each panel"* — and it is used by
the pub. `inn.py` calls `"square"` for the ground floor and `"close"` for both
upper floors, neither of which has a diagonal. Brace at least the end bays and
the gable, and let one panel be visibly out of true for §6's required
imperfection.

### 8. Timber frame reads as two different woods → **NOT RESOLVED**

Measured at the detail camera: the structural frame and rails read blonde-tan,
the window frames and door posts read dark brown (mean 87–99, sat 0.42). The
extreme spread of R2 (174 vs 80) has narrowed, but there are still visibly two
wood families on one wall, and the rails still read as battens applied over the
plaster rather than as members of the frame.

Every joint is still a plain butt overlap — no notch, no peg, no chamfered
arris. Art Bible §2: *"Every join must be physically explicable."*

### 9. No water logic, no ground contact → **NOT RESOLVED** (third round)

Plaster luminance rising from the sill beam, `inn-detail.png`:
`191, 191, 191, 192, 192, 192, 192, 192, 192, 191, 192, 191, 191, 191, 191, 191,
191, 191, 190, 189`. Dead flat over ~0.9 m.

Below the sills: profile `181 → 190` monotone, cross-wall standard deviation
**6.6**, which is broad shading, not streaking. Not one streak below any sill,
and `kit.py` still documents the sill as *"the source of the streaks below it."*
The cobble apron still terminates in a hard straight line into the ground plane.

### 10. Props: right instincts, wrong materials → **PARTIAL**

- **Barrel: worse.** Measured saturation **0.035–0.062**, rgb ~`(80, 76, 76)` —
  neutral grey, against `oak_weathered`'s 0.48. R2 measured 0.102. The claimed
  `M.lathe` fix did not recover it. **The cause is not the UVs** — see the guild
  report, D1: this rig's cool rim light (`#8FB8E8`, 1.15) washes curved surfaces
  to neutral across their whole limb, and on a cylinder the limb is most of the
  visible face. The lathe's terracotta cap on the guild turret measures 0.477, so
  lathes carry material fine. Fix the rim, and the barrel comes back for free.
- **Bench legs** still 0.055 m in section (`kit.py:570`). `kit.py` untouched.
- **Nothing is mid-task.** The barrel is now tipped on its side, which is a
  start. The bench is still parallel to the wall.

### N1 (R2). Shutters carry a tiling blob motif → **NOT RESOLVED**

Clearly visible at both the gameplay and detail cameras: brown leaf-or-fish
shapes repeating on a regular grid, plus a horizontal band of identical marks
crossing every shutter at the same height. `painted_wood()` is unchanged —
`flake = smoothstep(0.60, 0.78, normalize01(fbm(s, 13, seed + 102, octaves=4)))`
drives `edge_wear` against `OAK_WEATHERED`, and `grain` is a plain
`sin(linspace * 40 + fbm * 6)`, which is where the regular horizontal band comes
from. Two `docs/REFERENCES.md` anti-reference entries at once, on the most
repeated coloured element of the facade.

---

## New defect

### N1. A structural rail runs straight across the window openings

Visible unmistakably in `inn-detail.png` at magnification: a full-width blonde
timber rail passes horizontally **in front of** the panes, through the middle of
the window, from one side of the opening to the other.

This is the other half of the `openings` bug. `blocked()` is consulted when
placing intermediate *posts*, but `rail_at(POST * 0.5, -hw, hw)` and
`rail_at(height - POST * 0.5, -hw, hw)` run the full width unconditionally, and
the intermediate rails are not tested either. So the framing marches through the
apertures as if they were not there.

It is also the clearest possible proof to a player that the window is not a hole:
you cannot put a wall rail across an opening. Fix it in the same edit as defect 1
— segment the rails around `openings` the way the posts already are.

---

## Scale note (does not change the score)

- Storey heights are `G_H, F1_H, F2_H = 3.05, 2.85, 2.60` under a comment citing
  Art Bible §3, which specifies **3.20 m floor-to-floor** and **2.70 m interior
  floor-to-ceiling**. All three are under spec, and 2.60 m gross cannot yield
  2.70 m clear. Diminishing upper storeys are authentic to jettied construction,
  so I am not treating this as an error — but the comment claims §3 compliance
  and the numbers do not comply. Either correct them or record the deviation.
- The panes at ~0.45 × 0.50 m are plate glass by §2's standard, per defect 6.
- `make validate` passes: 0 failures, 0 warnings. Inn 27,874 tris,
  14.0 × 16.6 × 12.1 m.

---

## Review-rig status

1. **Silhouette render fixed.** `ground.visible = false; skyMesh.visible = false`
   during the silhouette pass. The §6 test ran, and it is the most valuable thing
   this pass delivered to the inn — it exposed a real, previously invisible
   defect.
2. **Lighting single-sourced.** Both renderers read
   `content/town/hearthmere.json`. Verified.
3. **The 1.75 m reference is unusable.** Cropped by the bottom of frame in both
   the approach and gameplay shots, and placed on the camera axis rather than at
   the facade. §8's scale box cannot be formally ticked from any submitted
   render.
4. **Approach-camera ground still mips flat**, so ground-contact work remains
   unjudgeable from that shot.

---

## What is working

Preserve these.

- **The laundry repoint.** Small, but it landed and it reads.
- **The lit dormers.** The first emissive on this building that survives into a
  render. `glass_lit`'s reasoning — deliberately not lighting every window,
  because a uniform facade reads as a lightbox — is right, and the dormers prove
  it works. Get it onto the facade behind real apertures.
- **The interior shell** (`inn.py:101-107`). Correct work that will start paying
  the moment the apertures are cut. Do not remove it.
- **The plaster.** Measured HF 12–22 with genuine trowel marks, cracks and
  mottling. It is the best-authored surface in either venue and it is what makes
  the walls read. It is also, ironically, what fills the windows.
- **The jettied massing, the chimney fix, the storey rhythm, the residue
  inventory, the lantern geometry** — everything reviews 1 and 2 listed as
  working still is. Nothing was broken.

---

## Required before resubmission — ranked by impact on the AAA score

1. **Cut real apertures in `timber_frame_wall`.** Segment the plaster infill —
   and the rails — around `openings`, the way `guild.py:179-197` does. This is
   the single defect that has cost this venue the most for three rounds, the
   shell is already in place waiting for it, and it fixes N1 in the same edit.
   Nothing else on this building matters as much.
2. **Per-tile roofs in `core/kit.py`** — ~30% aged variant, §6 jitter, and bring
   the dormer roofs into the main roof's value family. Third round asking, and it
   fixes every roof in Hearthmere.
3. **Stop the rim desaturating curved surfaces** (guild report, D1). Recovers the
   barrel here and the guild's turret in one edit to the rig.
4. **Make the building read in silhouette.** Rotate the heron sign perpendicular
   to the facade; move one dormer to break the roof edge; extend the balcony rail
   past the wall line; hang the laundry proud; break the base line. All cheap,
   none of it a massing change.
5. **Leaded came grid on the glass**, and a `uv_scale` on the sill so it stops
   rendering as street paving. (Defect 6)
6. **Sill streaking and ground splash** via `lime_plaster()`'s `wall_height`
   mechanism. (Defect 9)
7. **Switch the end bays and the gable to `style="cross"`** — the bracing already
   exists in the kit — and leave one panel visibly out of true. (Defect 7)
8. Bring rails and joinery into one tone family; add peg ends and chamfered
   arrises at the joints. (Defect 8)
9. Repaint the heron off `"ashlar"` and deepen its relief so the bird reads.
   (Defect 3)
10. Fix `painted_wood()`'s noise period and the regular `grain` band. (R2 N1)
11. Widen the bench legs; leave one thing genuinely mid-task. (Defect 10)
12. Flaunching collars on the chimneys; take the section to ~0.9 m. (Defect 2)
13. Chamfer and drape on the laundry cloths. (Defect 5 residual)
14. Unclip the emissive in `materials.py:150`. (Latent, defect 1)
