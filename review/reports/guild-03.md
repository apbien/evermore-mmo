# Adventurer's Guild — Review 3

**Verdict:** REVISE
**Renders:** `review/shots/guild/guild-approach.png`, `guild-gameplay.png`,
`guild-detail.png`, `guild-silhouette.png`
**Context:** `review/shots/town-arrival.png`, `town-square.png`
**Reviewed against:** `review/reports/guild-02.md`

**Render/build freshness — checked, and clean.** All four guild shots are dated
21:34:40–21:34:49; `assets/meshes/guild.gltf` was written 21:34:18. Every render
postdates every mesh and every texture. The process failure that invalidated
review 2 did not recur, and I assessed nothing against a stale image.

---

## First impression (before analysis)

The gable over the door faces the street now. That was one line of code and it
changed the whole front of the building — there is a triangle stepping forward
out of the facade where there used to be a horizontal smear. Second beat: the
tower has windows. Small, bright, but they are *there*, and a 15.5 m blank stone
face is no longer the first thing I see.

Third beat, and it is still the problem: the stone. At the door, from three and
a half metres, the wall is a flat tan gradient with a grid drawn on it. There is
nothing between the joints. It is the primary material of the hero building of
the town and it has no surface at all.

**One correction I owe the builder.** My first-glance read of the approach shot
was "the banner is still a stack of red bars." At magnification that is wrong.
The two tower banners are now continuous cloth with a real catenary hem and
blotchy dye — the rebuild worked. I called it wrong at 1:1 and I am striking it.
The banding I saw is real, but it is on the *entrance* banners only. See N2.

---

## Blind AAA comparison

Against **WoW / Boralus** (silhouette clarity, palette discipline).

The silhouette test is finally runnable and the guild passes it. Against white,
this reads as a fortified hall with a stair turret: finial, ogee cap, turret
shaft, merlons, tower parapet, hall ridge, chimney, eaves — eight steps, and a
clear two-mass composition. Boralus would recognise the massing. That is a real
result and it is the first time I have been able to say it.

It still loses on surface, and the measurements are blunt:

1. **The ashlar has no surface.** HF stdev **5.5–6.0** at the gameplay camera,
   **3.4–5.4** at the detail camera. Target was 15–25. It got *flatter* at close
   range, which is the opposite of how stone behaves.
2. **The turret is not made of stone.** Measured across its lit face: saturation
   **0.007 to 0.044**, rgb reaching a literal neutral (123,123,123), against
   ashlar's 0.25. Review 2 measured 0.097. It is now worse.
3. **The roof is one sheet.** `core/kit.py` has not been touched since `c20b6de`
   — before review 1. Zero per-tile colour, 0% of tiles in `TERRACOTTA_AGED`.
4. **Nothing has ever been used.** Threshold flat, no splash band, no streaking.
   Measured down the wall to the threshold: 164 → 169 → 163. Three rounds.

**Would people play this?** They walk toward it, they can now see it is a guild,
and there is light in the windows. They would still not believe it shipped — the
stone gives it away in the first second at the gameplay camera.

---

## Scores

| Axis | R1 | R2 | R3 | Note |
| --- | --- | --- | --- | --- |
| Silhouette | 3 | 5 | **7** | Test finally runnable. Merlons measure 1.05 m and read; turret/cap/finial/chimney step the outline eight times. Bay gable still absorbed into the hall outline; banners still flush; chimney still a post. |
| Material truth | 4 | 4 | **3** | Ashlar HF 5.5–6.0 (target 15–25), flatter at 1.5 m than at 3.5 m. Turret sat 0.007–0.044, worse than R2's 0.097. Sack at the threshold still market-awning canvas. Roof flat. |
| Lighting response | 4 | 5 | **4** | Lancets now emit — first real light on the building. But the cool rim washes every curved surface to neutral (see D1), interior carries no emissive (mean 26.3), roof LF 4.5. |
| Detail hierarchy | 3 | 6 | **7** | Bay gable now presents to the street, which was the missing secondary element. Quest board, lancet surrounds, quoins, string course all read. Three tiers present and legible. |
| Wear & story | 3 | 3 | **3** | Unchanged, third round. Threshold still a plain box under a comment claiming it is dished. No splash band, no string-course streaking, no traffic wear. |
| Life & residue | 4 | 5 | **5** | Lit lancets read as occupied. Interior still an unlit empty box — 1 of the World Bible's 5 items. Bedroll repointed; the sack beside it is still striped awning. |
| Cohesion | 5 | 4 | **4** | Tower banners are a genuine gain. Offset by: turret reads as concrete, striped canvas sack at the guild door, ogee cap is the only onion dome in a Northern-European town. |
| Scale truth | 6 | 6 | **7** | The named defect is fixed — merlons measure 1.05 m two independent ways. Building proportions hold. Docked one for the 1.75 m reference being cropped out of every submitted frame (rig, see R2). |
| AAA comparison | 2 | 4 | **5** | Real movement again. Flat stone and flat roof still pick it out at the gameplay camera. |

**Acceptance requires no axis < 7 and AAA ≥ 8. Six axes block.**

Verdict is REVISE. The composition is right and getting righter; what is left is
surface, wear, and one lighting bug.

---

## Status of every defect enumerated in guild-02

### Merlons still 0.62 m → **RESOLVED**

`guild.py:322`: `M.box(per / n_m * 0.9, 1.05, 0.38, ...)`. Verified twice off the
render: the silhouette gives merlon tops at y=142, crenel floors at y=184 — 42 px
— and the validator's 20.4 m overall height calibrates the frame at 40.4 px/m.
**42 / 40.4 = 1.04 m.** Thickness also went 0.34 → 0.38 m.

Below the 1.2–1.8 m I asked for, but the criterion is whether they read, and
against white they now read as a battlement rather than as a dentil course. Done.

Residual, minor: three merlons across a 6.8 m face is a 2.3 m pitch, coarser than
the 1.2–2.0 m period is worth. Not blocking.

### Entrance bay gable faces the wrong way → **RESOLVED**

`guild.py:396-405`. The `rotate_y` is gone and there is a comment explaining why.
In `guild-approach.png` the bay now presents a triangle stepping forward out of
the facade. This is the single best value-for-effort change in the pass.

Residual: it still contributes **nothing to the outline** — in
`guild-silhouette.png` the bay is entirely interior to the hall's profile,
because it is lower than the hall roof and in front of it. It reads through
shading, not through silhouette. That is acceptable; just do not count it as
silhouette work.

### Tower lancets buried inside the wall → **RESOLVED**

`guild.py:341-348`. Pushed to `tz + szz * (TOWER_W * 0.5 + 0.02)` — proud of the
face, depth 0.22 — switched to `glass_lit`, given lintel and cill, and emitted
with `label=f"tower lancet {i}{szz}"` so the occlusion tripwire finally covers
the case its own docstring was written for. Measured at the gameplay camera: pane
mean **212** against adjacent ashlar **154**, delta **+58**. It reads.

Two residuals:
- **No jambs.** The surround is lintel and cill only (`for oy in (-1, 1)`), so the
  opening has a top and a bottom but no sides.
- **At 09:30 a lit window reads as a white blob.** In `town-arrival.png` the
  lancets register as flat white rectangles stuck on the tower — closer to paper
  labels than to glass. `glass_lit` is the right call for dusk; in mid-morning
  daylight it needs a darker glass base so the emissive reads as depth behind
  glazing rather than as a luminous panel.

### The banner is a quilt of 72 boxes → **RESOLVED for the tower banners, NOT for the entrance banners**

`guild.py:124-176` is a genuine rebuild and the reasoning in the docstring is
correct on both counts: boxes cannot share normals across seams, and the UVs had
been tiling `banner_cloth`'s top-to-bottom sun-bleach gradient down the drop. It
is now one displaced quad grid with normalised 0..1 UVs, a catenary bow and a
wind lift. On the 2.10 × 6.40 tower banners this works — see the crop; it reads
as heavy dyed wool.

It does not work on the 0.85 × 2.4 entrance banners. See N2, which has the cause.

### Ashlar has no surface → **NOT RESOLVED** (third round)

| Surface | Camera | R1 | R2 | **R3** |
| --- | --- | --- | --- | --- |
| Guild ashlar | gameplay (3.5 m) | 6.96 | 6.86 | **5.54 / 6.00** |
| Guild ashlar | detail (~1.5 m) | 5.31 | 5.28 | **3.42 / 5.43** |

Target 15–25 at the gameplay camera. Confirmed at source: `ashlar()`
(`materials.py`) is untouched since the original guild commit.

The diagnosis is now precise. `ashlar()` gives you exactly two things:
`ridged(s, 64, seed+131, octaves=2) * 0.10` in the height channel, and per-*block*
albedo variance (`m.darken(blk * 0.8, 0.13)`). That is why the detail render
measures **LF 36.9 with HF 3.4** — the blocks differ from each other and each
block's interior is dead flat. You have coursing and no stone.

Fix: within-block albedo noise (two octaves, ~0.15 m and ~0.02 m features), and
take the tooling amplitude well above 0.10 so the chisel marks survive into the
normal map at gameplay range.

### No ground contact, no wear logic → **NOT RESOLVED** (third round)

- `guild.py:274-277`: threshold still `M.box(PORCH_W - 0.6, 0.14, 1.0, ...)`, and
  the comment above it still reads *"Threshold, dished by decades of boots."*
  Third review in a row quoting this line.
- Wall down to the threshold, `guild-detail.png`: 164, 164, 164, 163, 165, 169,
  169, 169, 170, 163, 166. Flat. No splash band.
- Plinth face: 167 → 136 over its visible height, which is shading falloff.
- String course: still no streak below it anywhere.

`lime_plaster()`'s `wall_height` mechanism is still sitting unused by `ashlar()`.

### Warm emissive in the guild interior → **NOT RESOLVED**

Interior back wall measures mean **26.3** (R2: 23.6) — correctly dark, and still
completely unlit. The World Bible brief (*stone hall, reception counter, big map,
weapon racks, adventurers loitering*) still delivers 1 of 5. §4 specifies
`#FFD9A0` at intensity 2.2 for window interior spill and the guild has none.

### Per-tile roofs in `core/kit.py` → **NOT RESOLVED** (third round)

`git log -- tools/assetgen/core/kit.py` returns `c20b6de` — before review 1.
`gable_roof` still builds each course as `M.box(seg * 1.22, 0.055, d, ...)`, one
slab spanning the full roof depth. Zero individual tiles, 0% aged variant against
§4's ~30%, no §6 jitter.

This was #5 on the R2 ranked list and #3 on the inn's, explicitly because one fix
in core repairs every roof in Hearthmere. It has now survived two rounds
untouched. The dead `ridge` lathe (built, rotated, scaled, never added to the
group) is also still there.

### Repoint the bedroll off `"canvas"` → **PARTIAL**

`guild.py:508` is now `M.lathe([(0.13, 0), (0.14, 0.62)], 10, "cloth_brown")`.
The named callsite was fixed.

But `guild.gltf` still carries a `canvas` primitive, and in `guild-detail.png`
there is still a **red-and-white striped market-awning object at the guild
threshold** — it is just a different object. `guild.py:505` calls
`K.sack(f"{asset_id}.pack", height=0.48)`, and `kit.py:509` is
`def sack(asset_id, height=0.55, mat="canvas")`. The pack inherits the striped
awning material from the default.

I misattributed this object in review 2 — it was always the sack, not the
bedroll. The defect as a *player sees it* is unchanged: the most saturated object
at the guild's front door is market-stall canvas. Pass `mat="cloth_brown"` at the
callsite, or change the kit default; a grain sack is not an awning either way.

### Code hygiene → **NOT RESOLVED**

`guild.py:466` still reads `tile_mat="slate" if False else "terracotta"`.

### Rim intensity 1.15 vs the palette's 1.4 → **CLOSED BY SPEC CHANGE — and I only half accept it**

Commit `2cb6b67` changed `docs/ART_BIBLE.md` from `Rim / separation | #8FB8E8 |
1.4` to `1.15`, recorded under D-009. Judging D-009 on whether the reasoning
holds, as instructed:

**The general decision is right and I endorse it.** A rig specified in three
places, with the authored copy in `content/` having no consumer at all, is a real
defect; the observation that §8's "reviewed at the locked lighting" had never
been true is honest and important; writing the two undeclared fills (warm ambient
floor, warm bounce) into the §4 table is a correction the table needed. Both
renderers now read `content/town/hearthmere.json` — verified at
`viewer.html:28` and `main.js:74-92`. Claim 7 is **RESOLVED**.

**The rim value specifically is not covered by that reasoning.** D-009 justifies
the spec moving because the hardcoded values fixed two measured defects:
shadowed facades reading blue-grey, and cast shadows crushing to black. Neither
is a rim-light phenomenon — the first is the hemisphere/PMREM double-count, the
second is the ambient floor. Lowering the rim from 1.4 to 1.15 does not address
either, so the stated argument does not reach this row. Closing a review defect
by editing the Law is the one move the process cannot allow on an unargued basis.

Having said that — see D1. The rim is *actively damaging* material read on curved
surfaces, and my R2 instruction to raise it to 1.4 would have made the town
worse. So: **keep 1.15 or go lower, but amend the D-009 entry to state the real
reason**, which is that this rig's rim desaturates curved geometry. Right
number, wrong justification, and the justification is what the file is for.

---

## New defects

### D1. The cool rim washes every curved surface to neutral grey — and this, not the lathe UVs, is why the turret is concrete

This is the round-02 N1 finding, re-diagnosed. **Claim 1 is implemented but did
not fix the symptom, because the symptom was never a UV problem.**

The UV change is real and correct on its own terms — `mesh.py:369-381` now maps U
to arc length in metres, and the reasoning in the comment is sound. It is
observable in the render: the striped sack's bands rotated from horizontal to
vertical between R2 and R3. But:

| Surface | Build | Material | Saturation |
| --- | --- | --- | --- |
| Turret shaft | **lathe** | ashlar | **0.007 – 0.044** |
| Turret cap | **lathe** | terracotta | **0.477** |
| Ashlar wall, sunlit | box | ashlar | 0.248 |
| Ashlar wall, deep shade | box | ashlar | 0.220 – 0.371 |
| Inn barrel | **lathe** | oak_weathered | **0.035 – 0.062** |

A lathe carries its material perfectly well — the terracotta cap measures 0.477.
And a box keeps its warmth even in deep shade, 0.22. So neither "it's a lathe"
nor "it's in shadow" explains the turret.

The pixel scan across the turret shaft does. Moving outward toward the sky edge:

```
x=752  (72.2, 66.0, 57.2)  sat 0.267
x=756  (103.7,102.5, 99.1) sat 0.044
x=764  (119.1,118.2,114.8) sat 0.036
x=772  (121.3,120.8,118.8) sat 0.021
x=778  (127.2,128.0,127.6) sat 0.007   <- sky boundary
```

Progressive brightening with progressive desaturation, terminating in a literal
neutral at the limb. That is a rim/fresnel signature. The rim is `#8FB8E8` at
1.15 — a strongly cool blue. On a **cylinder the limb occupies most of the
projected width**, so a lathe gets washed across its whole visible face; on a box
only the last few pixels of the edge do.

Every lathed object in Hearthmere is affected — turret, barrels, mugs, fountain,
chimney pots, bottles — which is the same list the builder wrote in claim 1, for
the wrong reason.

**Fix, in core, one place:** the separation light must not be allowed to
overwhelm albedo hue. Either tint it toward the key (a cool-*ish* `#B9C8DC`
rather than a saturated sky blue), or drop its intensity and recover the
separation from the warm bounce, or clamp its contribution so it cannot exceed
the diffuse term. Do this before touching anything else on this list — it is one
edit and it repairs material read on curved geometry across the entire town.

### N2. The entrance banners are still candy-striped, and the cause is `_Builder.poly()`

The tower banners read as cloth. The two banners flanking the front door — the
ones at eye height in the gameplay camera, the ones a player stands next to —
render as roughly fourteen hard alternating crimson/pale bands. Row profile down
one of them is a square wave: `43 43 43 43 43 53 76 82 88 82 54 45 45 45…`,
period ~26 px, repeating cleanly. It reads as market awning.

The material is exonerated: `banner_albedo.png` has flat column means (99–105)
and one broad tonal step. Not a striped texture.

Two compounding causes, both in code:

**(a) `poly()` is flat-shaded, by construction.** `mesh.py:197-216`, docstring
*"Add a convex polygon as a fan. Flat-shaded."* It appends the *same* normal to
all four vertices and creates fresh vertices per quad. So `guild.py:163-173`'s
comment — *"Smooth normal from the surface itself, shared across the quad, so
neighbouring quads agree and no seam catches light"* — is not what happens.
Sharing one normal *across* a quad is the definition of flat shading, and
adjacent quads on a curved surface do not agree. The mesh became one primitive;
the shading stayed faceted.

**(b) The displacement amplitudes are absolute metres, so they scale wrongly.**
`surface()` uses `bow = sin(u·π) · 0.13 · (0.30 + v)` and `lift = v^2.2 · 0.55 ·
sin(…)`. On the 2.10 m-wide tower banner a 0.17 m bow is an 8% sag — a gentle
catenary. On the 0.85 × 2.4 m entrance banner it is **20% of the width**, with up
to 0.55 m of lift on a 2.4 m drop. The cloth corrugates violently, and each
corrugation is one flat-shaded facet.

**Fix both:** compute per-vertex normals analytically from the partial
derivatives of `surface()` and emit vertices with their own normals — `lathe()`
already does exactly this at `mesh.py:387-397`, so the pattern is in core. And
express `bow` and `lift` as fractions of `width` and `height` rather than in
metres.

### N3. `banner_cloth` has a hard horizontal step across the drop

Now visible because the striping is gone. At ~45% down the tower banner the
albedo steps abruptly from dark crimson to pale pink — measured in the texture
itself, row means go `…68, 69, 69, 68` then **125, 126, 127**. It reads as two
different cloths sewn together, or as a sunburn line. Real sun-fade on a hanging
banner is a gradient, strongest at the exposed top, and it has no edge. Widen the
`smoothstep` in the bleach term until the transition is invisible.

### N4. The weapon rack's spearheads float

In `guild-gameplay.png` at x≈250–390 the three iron heads sit in mid-air with a
visible gap above the shafts leaning below them. Review 1 praised "the weapon
rack's missing weapon" as a residue idea; as rendered it reads as a geometry
error, not as a story. Either reconnect the heads to their shafts or lay the
spare head down somewhere it makes sense.

### N5. Carried forward, unchanged

- **The ogee cap reads as an onion dome** (R2 N2). It is the only such form in a
  Northern-European stone town and it reads as a different architectural culture.
  Straighten to a cone or a slight concave taper.
- **The hall chimney is a fence post** (R2 N4). `guild.py:428`, `section=0.78` on
  a 14 m hall. Confirmed against white — in `guild-silhouette.png` it is a
  toothpick. Widen to ~1.1 m and add a flaunching collar.
- **The buttresses remain unreviewable** (R2 defect 2). `guild.py:409-415` puts
  them on the ±X flanks; every submitted render is frontal, and the two town
  shots are now near-duplicates of the same view. Third round asking: supply one
  3/4 view.

---

## Review-rig status

1. **Silhouette render fixed — claim 2 RESOLVED.** `viewer.html` now sets
   `ground.visible = false; skyMesh.visible = false` during the silhouette pass,
   and the comment states the measured reason honestly. `guild-silhouette.png` is
   clean black-on-white and the §6 test ran. This unblocked the single most
   important judgement in the review.
2. **Lighting single-sourced — claim 7 RESOLVED.** Verified at `viewer.html:28`
   and `client/src/main.js:74-92`.
3. **The 1.75 m reference is still unusable.** In both the approach and the
   gameplay shots the figure is placed on the camera axis 3.6 m in front of the
   lens (`frameFor(...).player`) and is cropped by the bottom of the frame. §8's
   *"verified with a 1.75 m reference"* box cannot be formally ticked from any
   submitted render. Put a second, uncropped figure at the facade.
4. **Approach-camera ground still mips flat.** Both approach shots are judged
   over a featureless brown plane.
5. **`make validate` passes:** 0 failures, 0 warnings. Guild 28,030 tris,
   15.6 × 20.4 × 13.4 m.

---

## What is working

Preserve these.

- **The bay gable rotation.** Best effort-to-result ratio in the pass.
- **The lancets.** Proud, dressed, lit, and labelled for the tripwire. The tower
  is no longer a chimney stack.
- **The merlons.** Correctly sized, verified, and they read against white.
- **The tower banner rebuild.** The reasoning about box seams and about UV
  tiling of a directional gradient was correct and is the right analysis; it
  reads as cloth now. Carry the same rigour into the flat-shading half (N2).
- **The lathe arc-length UV change.** It did not fix what it was aimed at, but it
  is correct on its own terms and should stay — texel density across a lathe/box
  boundary was genuinely wrong.
- **The single-source lighting rig, and D-009's honesty** about §8 never having
  been true. Amend the rim justification; keep everything else.
- **The doorway, interior shell, quest board, parchment/wax materials, quoin
  ladder, occlusion tripwire** — everything reviews 1 and 2 listed as working
  still is. Nothing was broken in this pass.

---

## Required before resubmission — ranked by impact on the AAA score

1. **Stop the rim desaturating curved surfaces** (D1). One edit in the rig,
   repairs every lathe in Hearthmere. Do this first — several other items are
   measured through it.
2. **Give the ashlar a surface.** HF 15–25 at the gameplay camera, via
   within-block albedo noise and stronger tooling. It is the hero building's
   primary material. (Defect: ashlar)
3. **Per-tile roofs in `core/kit.py`** — ~30% aged variant, §6 jitter. Third
   round asking; fixes the guild, the inn, and every roof in town.
4. **Per-vertex normals in the banner surface, and size-relative displacement**
   (N2). Then delete the dead `ridge` lathe while you are in `mesh.py`/`kit.py`.
5. **Ground splash and string-course streaking** via the `wall_height` mechanism
   already in `lime_plaster()`; dish the threshold with real geometry, or delete
   the comment. (Defect: wear)
6. **Warm emissive in the interior**, plus a wall map or a rack so the hero
   building's front door does not open onto an empty box.
7. Repoint `K.sack` off the `canvas` default. (Defect: bedroll/sack)
8. Jambs on the lancets; darker glass base so `glass_lit` reads as glazing at
   09:30 rather than as a white panel.
9. Soften the `banner_cloth` bleach step (N3); reattach the spearheads (N4).
10. Straighten the ogee cap; widen the hall chimney to ~1.1 m with a flaunching
    collar. (N5)
11. Delete `tile_mat="slate" if False else "terracotta"`.
12. Amend D-009 to state the actual reason the rim is 1.15.
13. Rig: an uncropped 1.75 m figure at the facade; one 3/4 view of the hall
    flanks; fix approach-camera ground mipping.
