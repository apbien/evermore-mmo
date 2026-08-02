# Art-director review — Hearthmere, whole town, pass 05

**Verdict: REJECT.**

Reviewed 2026-08-02 against `docs/ART_BIBLE.md` §8, `docs/BUILD_DIRECTIVE.md` §3
(arrival), §4 (geography), §6 (structure), §7 (budget) and §9 (done).

**69 frames rendered by me at the locked 09:30 rig into
`review/shots/ad-town-05/`**, plus a value-band pass on six hero cameras
(`review/shots/ad-town-05/bands/`) and a five-run determinism probe on the perf
instrument (`review/shots/ad-town-05/probe/`) — 80 renders. Twenty-six read
closely as PNGs, the rest scanned; every frame cited below I opened and read.
I also ran `validate.py`, `check_walkable.mjs`, `check_client.mjs` and
`uv_density.py` myself rather than taking any reported number.

Frames: `t-plan`, `t-aerial-ne/nw/sw/se`, `t-arrival`, `t-square`,
`t-silhouette`, `t-approach-s/ne/w`, `t-gate-north`, `t-gate-south`,
`t-bridge`; `spine-walk-01..08` (bridge → north gate → Ford Road → market
place), `wharf-walk-01..08` (Wharf Lane → water gate → quay → Fishers' Steps),
`kirk-walk-01..06` (Kirkgate → Kirk Green), `craft-walk-01..06` (Bakers' Row),
`alley-walk-01..06` (Bell Alley → Smiths' Lane), `mere-walk-01..06` (Mere
Street → West Gate), `bailey-walk-01..06` (The Bailey), `sty-walk-01..05` (Sty
Lane), plus four free cameras (`fountain`, `westfront`, `quaydeck`,
`mereshore`).

I reviewed from images. Where a line number or a file appears below, I opened it
only after a frame told me what to look for.

---

## The verdict, stated plainly

**This wave produced the single largest jump in quality the project has had, and
it is still a REJECT — for a reason that is now different in kind from every
previous pass.**

Three things landed that I have been asking for since pass 02, and all three are
verified in frame, not in source:

- **The crazy paving is gone.** `t-square`, `mere-walk-05`, `craft-walk-04`,
  `spine-walk-06` all show properly coursed setts with per-stone value, a kerb,
  a gutter and a wear channel. The street surface of Hearthmere went from the
  worst material in the build to one of the better ones in a single wave. This
  is the largest area of pixels in the project and it is now right.
- **The stair-stepped shadow is gone, and the figure has a contact shadow.**
  `t-arrival`'s nave floor is a smooth gradient. `t-square`, `t-gate-south`,
  `craft-walk-04`, `mere-walk-05`, `t-bridge` — every frame the 1.75 m figure
  appears in, it is now planted on the ground. Three passes of asking.
- **The wall reads.** `t-gate-south` puts it at ~4.5× the figure; `t-approach-s`
  and `t-approach-ne` show a continuous curtain with cone-capped towers.
  Pass 04's "garden wall" is closed.

Against that, **the reason this is still a REJECT has changed.** For four passes
the answer was "the surfaces are wrong". The surfaces are now *substantially*
right. What stops the build today is a shorter and much more specific list:

1. **One masonry recipe — the wavy rounded cyclopean block — is on the single
   most important surface in the project** (the church interior, 55 % of
   `t-arrival`) and on six other close-range walls. It is the "inflated foam"
   material pass 04 named at item 2 of the arrival findings, and it is
   untouched.
2. **The water was not attempted.** `atmosphere.water.specularKnee` is
   **1.05**, byte-identical through four passes. `t-approach-ne`,
   `t-aerial-sw`, `t-gate-north` are unchanged. The wave's own report says so
   plainly and I confirm it.
3. **The leaf card is still a chequerboard**, and the claim that it is fixed is
   contradicted by `t-square` and `kirk-walk-05`.
4. **The foliage's *shadow* is a handful of black lozenges** (`craft-walk-04`) —
   a defect nobody has named, and at 09:30 it is on the ground in half the
   frames in the build.

And the build acquired new damage in three places, one of which is severe:
**`t-gate-south`, the strongest frame in the project, has lost its dappled tree
shadow and gained a cold blue-grey giant-plate curtain wall that matches nothing
else in the town.** The light-and-air agent warned that a tree had vanished from
this frame after a source rebuild. It is gone, and I can see the hole it left.

**And the instruments went backwards while the frames went forwards.**
`validate.py` 0 failures → **5**. `check_client.mjs` now **fails the budget gate
outright at 1,395 draws** while `town.mjs` reports 1,024 for the same camera —
pass 04's 0.7 % client/harness agreement is now a **36 % disagreement**, and I
have proved why (§12). The unreachable door was moved, not closed. Two
instruments disagree about how many masses are sunk. A build whose harness says
"0 warnings" while a floating roof, a dry river and a culled fountain sit in the
frames is a build whose harness is no longer telling it the truth.

Blind, side by side against Divinity's Reach, Gridania, Ul'dah and post-Legion
Boralus: **eight frames now survive the first two seconds, and one survives
ten.** Last pass it was three and zero. That is the first time this project has
put a frame past ten seconds. Which eight, which one, and what the ten-second
failures are is answered in the last section — and the answer is that **six of
the eight fail at ten seconds on §1 or §3 alone.**

---

## Claims from this wave that the renders do not support

- **atlas-and-foliage: *"Leaf card — fixed and verified at 5.5 m and 18 m … No
  chequerboard at either range."*** **Rejected.** `t-square`: the market oak's
  canopy at ~18 m resolves into regular rows and columns of small dark-green
  rectangles on a visible axis-aligned lattice — you can count eight columns on
  its left edge. `kirk-walk-05`: both flanking trees at 6–10 m, same lattice,
  same axis alignment. It is *better* than pass 04 — the cards are smaller and
  denser — but the regular grid is still the first thing the eye finds in the
  canopy. Whatever the 8-way UV orientation did, it did not break the lattice
  the cards are *placed* on, which is the half of the problem that was never in
  the sheet.
- **atlas-and-foliage: the draw budget.** The report says 1,385 draws at
  `square`, and that is the correct number. But `t-report.json` from the
  standard command says **989**, and the budget gate reads that one. I proved
  why in five probe runs: **the harness samples the previous frame's LOD state.**
  `--views square` alone → 1,385. `--views arrival,square` → 1,385. `--views
  plan,square` → **989**. `--views aerial-ne,square` → **989**. The default view
  list opens with `plan` and three aerials, so every gameplay camera in every
  report this project has ever produced has been measured with the whole town
  sitting at far LOD. The gate is under-reporting by ~30 %, and it is
  order-dependent, which means it can be silently gamed by adding an aerial.
  Details and fix in finding §12.
- **wall-water-market: *"the lamp that bisected `t-square` through three
  rejections is out."*** True and verified — `t-square` is a clean composition
  for the first time. But the report also implies the frame is now measurable:
  it is not. `bands/b-square` still returns `separation fg->bg null / temp
  null`, because the background band has zero pixels. The instrument has been
  blind on the town's second-most-important camera for three passes and the
  cause was never the lamp.
- **light-and-air: *"Atmosphere — retuned … arrival's number barely moves (0.2 →
  3.1) and I explain why the metric fights itself on that one view while the
  picture improves a lot."*** The picture *has* improved a lot and I credit it.
  But the explanation does not survive `t-approach-ne`, which the harness itself
  labels "the best profile in the build" and which now measures
  **temperatureSwing −36.9** — the background is *warmer* than the foreground by
  a wide margin, which is Art Bible §1 exactly backwards. Nobody measured that
  view. Two of the six hero cameras (`arrival` +3.1, `approach-ne` −36.9) still
  fail the temperature requirement outright and one (`square`) cannot be
  measured at all.
- **wall-water-market: *"`crop/tower-far2.png` proves it at 180 m."*** The tower
  LOD chain is genuinely fixed — no floating cones in any of my 61 frames, and
  `t-approach-s`/`t-approach-ne` show roofed towers at 130 m. Accepted. But the
  same report's silhouette claim — six new vertical events — is generous: in
  `t-silhouette` the wall contributes no base line at all, and the *lower* edge
  of the town's mass between x≈700 and x≈1250 is **tree crowns, not
  architecture**. From the north elevation the thing that terminates Hearthmere
  at the ground is scrub.
- **uv-scale-and-masonry: `cobble_wall`.** The agent explicitly declined to
  claim this one ("right in the sheet but I never got it in a frame"). That was
  the correct call and I want it on the record as the right way to report.
  I have it in two frames now, and the honest answer is that it changed failure
  mode rather than getting fixed: `bailey-walk-04` at 2 m reads as **cracked
  mud** — irregular polygonal plates, straight edges, three-way junctions, no
  dome, no course, plates 0.5–0.9 m across against a 1.75 m figure.
  `craft-walk-04` at 25 m reads as a **chevron textile**. Neither is river
  cobble. See §5.

---

## The three standing questions, answered from frames

### (a) Does the arrival frame deliver BUILD_DIRECTIVE §3?

**Composition: yes. Surface: no, and now for exactly one reason.**
`t-arrival`, `bands/b-arrival`.

| §3.2 requires | in `t-arrival` |
| --- | --- |
| the descending church steps | **yes** |
| a street leading the eye | **yes** — the aperture opens onto the market place |
| the market fountain as the focal point | **no — it has lost the frame.** The fountain is ~40 px of pale blur at 43 m. The **guild tower** is now the focal point at ~180 px, dead centre in the aperture |
| ≥ 2 other venue anchor silhouettes | **yes** — guild tower, a slate gable, a cupola and a jettied range all read |

Two of the three things pass 04 held against this frame are **fixed**:

- **The 30 cm stair-step staircase across the nave is gone.** The floor is a
  smooth wear field with a soft sun/shade gradient. Verified in frame. The
  light-and-air agent's finding that this was never the shadow map — it was
  `church.py:1006`'s 24 hard-edged quads — is correct, and the rebuild landed.
- **Everything past 25 m is no longer one flat cream.** `foregroundToBackground`
  94.9 → **70.7**. Still over the +45–60 target, but the market place, the
  jettied range and the tower now separate. The town has depth in the aperture
  for the first time.

What stops it is now a **single material**. The nave's piers, arch voussoirs and
wall panels are the **wavy rounded cyclopean block** — pale blocks ~0.9 × 0.6 m
with ~10 cm rounded arrises, wandering joints, and near-zero value difference
between neighbours. They fill roughly **55 % of the spawn frame at 1–3 m from
the eye.** Against the 1.75 m figure those are megaliths. Pass 04 called this
"cartoon wavy block that reads as inflated foam"; it is byte-unchanged, and it
is now the *only* thing wrong with the most important composition in the build.

Three smaller things in the same frame:

- **`temperatureSwing` is 3.1.** Art Bible §1's requirement is not met on frame
  one. It moved 0.2 → 3.1; the target is >+20.
- **The worn path over-corrected.** The old defect was a hard staircase; the new
  one is a soft yellow-green wash across the flags that reads as a *stain*
  rather than as wear. It wants a value change and a polish change, not a hue
  change.
- **Two black unlit objects** stand in the bottom corners of the frame. Same
  defect as the churchyard finials in `kirk-walk-05` (§10).

### (b) Does the silhouette read as a town with a skyline?

**Better than pass 04, and still not a hierarchy.** `t-silhouette` (8 px/m),
`t-approach-s`, `t-approach-ne`, `t-approach-w`.

- **Seven distinct vertical events** now read across the profile, at four
  different heights — two cone-capped drums left, a spire, a cupola, the church
  tower with corner pinnacles centre, a pyramid-capped tower right. Pass 04 had
  four. This is real and it is the tower work landing.
- **The tallest is ~23 m against a 10–12 m general roofline: 2.1×.** Pass 04
  measured 1.8–2.0×. Divinity's Reach and Ul'dah run 2.5–3×. Still reads as a
  large village rather than a town, and the gap is now small enough to close
  with **one** building: nothing between 14 m and 21 m exists, so the profile
  jumps straight from the roofline to the two towers with no intermediate step.
- **The wall still contributes no base line.** 6.0 + 1.2 m behind a 10–12 m
  roofline is absorbed into the mass, exactly as the wave's own report says. It
  cannot not be, at a canonically low height.
- **Worse: between x≈700 and x≈1250 the lower edge of the town's mass is tree
  crowns.** A fuzzy vegetal line, not a wall, not a roof. That is what
  terminates the town at the ground in its own elevation drawing.
- **Two black boxes hang *below* the ground line** at x≈810–870 and
  x≈1100–1140 — the quay and the watermill, legitimately sunk, reading as two
  detached masses under the town. In the one instrument that judges profile, a
  sunk mass should be clipped at the datum.
- **`t-approach-s` is fixed of its tree** — the 40 % obscuring foliage is gone,
  the `ford_road` corridor fix worked, and the wall with three roofed towers now
  carries the frame. **But the bottom 45 % of the canonical return camera is now
  field hedges**: solid extruded ribbons with a sine-wave top edge, one of which
  runs dead through frame centre. Same class of defect as the tree, moved down.
- **`t-approach-w` measures clean** — `fg→bg 52.5`, `temp 33.6`, both in target,
  the only hero camera that passes both. And it is ruined in the same way: two
  **pure unlit black** hedge ribbons across the bottom 45 %.

### (c) Does it read as one world?

**Closer than it has ever been, and the seams have narrowed to one system and
one hue.**

The ground is no longer three unrelated surfaces per frame — that was pass 04's
finding (ii) and the sett rebuild closed most of it. `mere-walk-05`,
`craft-walk-04`, `spine-walk-06` and `t-square` all read as one town's paving.

What is left:

**(i) The masonry family is still not one family, and it is now *seven*
recipes, not five.** In `t-gate-north` alone: giant-plate ashlar (curtain), a
smeared cloudy mottle with no courses (drum towers), a fine speckled sandstone
(gate frontispiece), the wavy-lozenge "crocodile skin" (bridge parapet), and a
flat untextured pale slab (coping). `t-gate-south` adds a **cold blue-grey
polygonal plate** curtain that appears nowhere else. `bailey-walk-04` adds
`cobble_wall`'s cracked-mud. `t-arrival` and `spine-walk-06` and `kirk-walk-05`
carry the wavy rounded cyclopean block. `wharf-walk-06` has four in one 8 m
span. Pass 02 said three, pass 03 four, pass 04 five. **It is seven.** This is
the one thing in the build that has got monotonically worse every single pass.

**(ii) Emerald is still the material of last resort, and it is still
hard-edged.** `spine-walk-06` (a 4 m saturated emerald rectangle at 3–8 m with
dead-straight boundaries), `bailey-walk-04` (five green quads over shingle),
`craft-walk-04` (both verges), `wharf-walk-06`, `sty-walk-03`. pass-02 §14,
pass-03 §2, pass-04 §2 — **unchanged in four passes.** The patch cell came down
and the recipe was rebuilt, but `ragged` still drops whole cells so the boundary
is still a rectilinear staircase, and `grass_lush` is still the most saturated
colour in Hearthmere including the crimson confectioner.

---

## The running scorecard

### Pass-02 findings

| # | pass-02 finding | p03 | p04 | **p05** | proof |
| --- | --- | --- | --- | --- | --- |
| 1 | 18 of 32 venues do not exist | FIXED | FIXED | **FIXED** | `t-report.json` 32 placed / 0 missing |
| 2 | leaf atlas incapable of a tree | FIXED | REGRESSED | **NOT FIXED** | `t-square`, `kirk-walk-05` — regular lattice of green rectangles at 6–18 m |
| 3 | yew is a 28-face polyhedron | PARTLY | PARTLY | **PARTLY** | no faceted sphere in 61 frames; the cards that replaced it are §2 |
| 4 | thatch is a smooth cream membrane, knife edge | PARTLY | NOT FIXED | **NOT FIXED** | `mere-walk-05` — both roofs, knife-edge eaves, dead-straight ridge, no bundle, no thickness |
| 5 | no fog / aerial perspective | over-driven | NOT FIXED | **PARTLY** | retuned and it works on 3 of 6 hero cameras; `approach-w` 52.5/33.6 passes both. `arrival` temp 3.1, `approach-ne` temp −36.9, `square` unmeasurable |
| 6 | fountain must anchor at 43 m | PARTLY | FIXED | **REGRESSED** | `t-arrival` — the guild tower is the focal point at ~180 px; the fountain is ~40 px of blur. `fountain-free` at 6 m has falling water; `t-square` at 12 m has **none** — the water is culled between 6 m and 12 m |
| 7 | no skyline; tower detached; wall too low | NOT FIXED | PARTLY | **PARTLY** | wall raised and reads (`t-gate-south`, `t-approach-s`); towers roofed; ratio 1.8× → **2.1×**; wall still absent from `t-silhouette` |
| 8 | Mere a stamped ellipse; Emberflow a rectangle; water blows to white | PARTLY | NOT FIXED | **NOT FIXED** | `t-aerial-sw` — perfect ellipse, uniform beach ring, pure white far half, dead-straight parallel-sided canal. `specularKnee` still 1.05 |
| 9 | `rubble` is crazy paving with green mortar | NOT FIXED | PARTLY | **FIXED** | `t-square`, `mere-walk-05`, `craft-walk-04`, `spine-walk-06` — coursed setts, per-stone value, kerb, gutter, wear channel |
| 10 | three masonry treatments on one wall | NOT FIXED (4) | NOT FIXED (5) | **REGRESSED (7)** | `t-gate-north` (5), plus `t-gate-south`'s blue-grey plate and `bailey-walk-04`'s cracked mud |
| 11 | inside the wall is bare brown dirt | PARTLY | PARTLY | **PARTLY** | hard emerald quads remain at 3–8 m (`spine-walk-06`, `bailey-walk-04`) |
| 12 | church west front blank; nave black; tower off-axis | PARTLY | PARTLY | **PARTLY** | nave lit, trusses, arcade, clerestory, **worn path now real**; still no west window, no east window/apse, and the interior masonry is the wavy cyclopean block |
| 13 | no AO; 21 px/m shadows | PARTLY | NOT FIXED | **FIXED** | `t-square`, `t-gate-south`, `t-bridge`, `craft-walk-04`, `mere-walk-05` — contact shadow under the figure in every frame it appears in; no stepped edges anywhere in 61 frames |
| 14 | one green mottle doing daub, hedge and ground | NOT FIXED | PARTLY | **NOT FIXED** | daub is buff on `mere-walk-05` and **bright emerald on `alley-walk-03` and `spine-walk-03`** — the fix landed on some buildings and not others, which is a cohesion failure of its own. Ground quads and green shutters unchanged |
| 15 | a hedge stands in Kirkgate and swallows the camera | NOT FIXED | MOVED | **PARTLY** | `t-approach-s` cleared of its tree; a hedge ribbon still runs through its centre |
| 16 | large black unlit polygons | FIXED | PARTLY | **NOT FIXED** | `t-approach-w` (two hedge ribbons, bottom 45 %), `sty-walk-03` (top-right corner), `t-bridge` (east bank wedge), `wharf-walk-06` |
| 17 | crude LOD at 25 m; lanes lose their surface | PARTLY | PARTLY | **PARTLY** | lanes hold; buildings past ~30 m still collapse to one flat cream (`t-square` moot hall, `kirk-walk-05`) |
| 18 | cloth and ivy are flat single-sided quads | NOT FIXED | PARTLY | **NOT FIXED** | `sty-walk-03` — washing is five perfect rectangles, dead-straight hems, no sag, no peg pinch, no thickness; fence ivy is a green splodge on a quad |
| 19 | landscape fields a radial spiderweb | PARTLY | PARTLY | **NOT FIXED** | `t-plan`, `t-aerial-sw` — every hedge radiates from or circles the town; fallow still pink-mauve |
| 20 | composition defects in the hero cameras | NOT FIXED | NOT FIXED | **PARTLY (1/3)** | `t-square` **fixed** — lamp out, clean composition. `t-gate-north` still off-axis, parapet fills right 45 %. `spine-walk-01` still **inside the bridge deck** |
| 21 | roof distribution reads as a checkerboard | NOT FIXED | PARTLY | **PARTLY** | clustering reads; terracotta split into three kiln batches is **not visible in any aerial** — `t-plan` and `t-aerial-sw` are ~70 % one saturated orange |

**Pass-02 score: 4 fixed · 9 partly · 7 not fixed · 1 regressed.**
(p04 was 2 / 12 / 6 / 1.) **Four items closed outright — the first pass in this
project where anything closed at all.** Two regressed.

### Pass-04's own findings

| § | pass-04 finding | **p05** | proof |
| --- | --- | --- | --- |
| 1 | shadow map 44 texels/m, stair-steps across the spawn frame | **FIXED** | `t-arrival` floor smooth; contact shadows everywhere. Cause was misattributed by the review and the wave found it: `church.py:1006`, not the shadow map |
| 2 | `cobble` is crazy paving; 421 literal `uv_scale` sites | **FIXED** | 421 → **5** literal sites, 63 `MATS.uv_scale()` calls; `tools/uv_density.py` measures 4 fails / 11 warnings over 102 materials, none of them a ground key |
| 3 | aerial perspective unchanged, temperature dead | **PARTLY** | retuned; 1 of 6 hero cameras passes both bands, 2 fail temperature, 1 unmeasurable |
| 4 | the leaf card is a chequerboard of green squares | **NOT FIXED** | `t-square`, `kirk-walk-05`. Plus a new one: the foliage's **shadow** is a set of hard black lozenges (`craft-walk-04`) |
| 5 | a tree stands in `approach-s` | **FIXED** | `t-approach-s` clear; cause found (`ford_road` authored to z=96, camera at z=138) |
| 6 | `cobble_wall` reads as a missing texture | **NOT FIXED** | `bailey-walk-04` (cracked mud at 2 m), `craft-walk-04` (chevron textile at 25 m) |
| 7 | wall 6.3 m, towers 8.9 m flat-capped | **FIXED** | 6.0+1.2 with 11 individually authored towers 10.6–18.4 m, roofed, and the LOD chain that made them invisible is fixed |
| 8 | five masonry treatments in one frame | **REGRESSED (7)** | `t-gate-north`, `t-gate-south`, `bailey-walk-04`, `wharf-walk-06` |
| 9 | the Mere is a stamped ellipse, water is opaque enamel | **NOT FIXED** | `specularKnee` 1.05 unchanged; `t-aerial-sw`, `t-approach-ne`, `t-gate-north` |
| 10 | the thatch albedo contains no straw | **PARTLY** | some directional streaking arrived; no stalk, no bundle edge, no thickness, knife eaves (`mere-walk-05`) |
| 11 | six masses sunk, one door unreachable | **NOT FIXED** | `validate.py` still reports **five** sunk masses and `t-report.json` reports **two** — the instruments disagree. The unreachable door was **moved, not closed**: `hm.townhouse.door.15` → `hm.slot.07.chophouse.door.01`. `validate.py` went 0 → **5 failures** |
| 12 | three hero-camera composition defects | **PARTLY (1/3)** | `square` fixed; `gate-north` and `spine-walk-01` unchanged, fourth pass |
| 13 | market place and Ford Road carry no residue | **FIXED — and it is the best work in the wave** | `fountain-free` is the proof: a butcher's pitch with hanging meat, a cheese table, a chopping block, firewood, a wine cup, a straw heap, a handcart, crates, baskets, a sagged striped awning, weeds and pebbles in the sett joints. `t-square`, `t-arrival` corroborate |
| 14 | the confectioner is a fire-engine-red building | **NOT FIXED** | `kirk-walk-05` — every timber, mullion, barge board, door and surround is saturated crimson, plus an orange awning and orange finials |
| 15 | smaller defects | **PARTLY** | untextured box at the water gate **still there** (`wharf-walk-06`, dead centre); black finials still there (`kirk-walk-05`); putlogs carrying nothing still there (`bailey-walk-04`); **no frame in 61 contains a sun disc or more than a wisp of cloud** |

**Pass-04 score: 5 fixed · 5 partly · 4 not fixed · 1 regressed.**

---

## Findings, ordered by how much they damage the frame

### 1. One masonry recipe — the wavy rounded cyclopean block — owns 55 % of the spawn frame

**Frames:** `t-arrival` (nave piers, arch voussoirs, wall panels, 1–3 m,
~55 % of frame), `mereshore-free` (the watermill's whole 12 m elevation at 5 m,
~70 % of frame), `spine-walk-06` (the right-hand building's ground floor at 2 m,
~40 % of frame), `kirk-walk-05` (churchyard wall and piers at 4 m),
`kirk-walk-02` (frame-left ground floor at 3 m), `craft-walk-04` (the
timber-frame's stone ground floor at 3 m), `t-bridge` (gate drum),
`t-gate-north` (bridge parapet — the same recipe at a smaller scale, which is
the "crocodile skin"), `wharf-walk-08` (wobbling inside every quay slab).

Its signature: blocks 0.6–1.1 m across with **~10 cm rounded arrises**,
wandering non-straight joints, and adjacent blocks differing by only a few
luminance levels. At any range under 5 m it reads as inflated foam or reptile
hide; it never reads as cut stone. Against the 1.75 m figure the blocks are
megaliths — no pre-industrial mason moves a 1 m ashlar for a parish church
arcade.

Pass 04 named this at item 2 of the arrival findings. Nothing in this wave
touched it, because every agent was working on the *ground* and the *outside* of
the wall.

**Fix.** This is one recipe. Chamfer radius down by ~4×, joints straightened
onto the `coursed` lattice the streets now use, block size to 0.35–0.55 m for
walling and 0.25 × 0.45 m for voussoirs, and per-stone value spread to ±25 %
luminance applied **last**. The `coursed`-based rebuild that fixed `cobble` and
`rubble_weathered` is the proven route and it has not been carried here.

*Why this is #1:* it is the largest area of visibly wrong pixels in the frame
`BUILD_DIRECTIVE` §3 calls the most important in the build, and it is the only
thing left wrong with that frame.

### 2. The water was not attempted, and it is 55 % of two hero cameras

`content/town/hearthmere.json → atmosphere.water.specularKnee` is **1.05**.
Pass 03 asked for ~0.55. Pass 04 asked for ~0.55. It is byte-identical.
The wave's own report states this plainly and I credit the honesty.

**Frames:**
- **`t-approach-ne`** — the water is 55 % of the frame: a solid opaque emerald
  sheet with **visible triangular polygon facet seams** at 40–80 m, a hard
  featureless **pure-white specular plate** running the full height at x≈900–1200,
  and **zero reflection** of a 190 m walled town standing on the far bank.
  Measured `temperatureSwing` **−36.9** — cold near, warm far, Art Bible §1
  exactly inverted, on the camera the harness itself labels the best profile in
  the build.
- **`t-aerial-sw`** — a mathematically perfect ellipse with a uniform-width
  beach ring and a pure white far half; the Emberflow a dead-straight
  parallel-sided canal.
- **`t-gate-north`** — tropical emerald-teal at 8 m, completely opaque (the bed
  is invisible even where it must be centimetres deep), a **hard sawtooth of
  flat dark triangles** where the bank meets the surface, a flat green
  shallow-water band with a hard edge, and a three-arch stone bridge with no
  reflection in it.
- **`mereshore-free`** (the watermill from the leat, eye 4 m) — the clearest
  example in the build: the water plane meets the terrain in a **row of sharp
  triangular teeth** at 5–10 m from the eye, the raw terrain mesh poking through
  the surface. Behind it, the mill's 12 m elevation is the cyclopean block (§1)
  with two more masonries on its quoins and its wheel race, its waterwheel hangs
  clear of the water, and a 12 m building standing in a pool casts no reflection
  into it.
- **`t-bridge`** — and this one is a bug, not a material. The `bridge` camera
  takes its Y from `terrain.height()`, which is the **channel bed**, so the eye
  is *below* `water.surfaceY = -3.1`. The water plane is single-sided, so the
  river disappears: you see daylight through all three arches, the piers
  standing on dry ground, the figure standing in the river, a pale green
  translucent wedge (the surface from underneath) and a **pure black unlit
  wedge** on the east bank. This is the same class of bug as `spine-walk-01`
  and it is in a view this wave *added* to the standard set.

**Fix, in value order.** (a) The `bridge` and `walk` cameras must take Y from
`max(terrain.height(), waterLevel) + eye` and from authored deck levels — one
function, and it fixes `spine-walk-01` too. (b) `specularKnee` → 0.55 plus a
roughness gradient with distance. (c) Perturb the `basin` and `channel`
outlines with two octaves of low-frequency noise; the shoreline is geometry, and
this alone kills both the ellipse and the canal. (d) A planar reflection — a
bridge with no reflection is the single tell that stops any water frame. (e) A
depth-based colour ramp so the shallows are not the same value as the deeps.

### 3. The leaf card is still a lattice, and its shadow is a set of black lozenges

**Frames:** `t-square` (market oak at ~18 m — count eight columns on the
canopy's left edge), `kirk-walk-05` (both trees at 6–10 m), `spine-walk-06`
(~25 m), `sty-walk-03` (at 1.5 m the cards resolve into four recognisable
**die-cut maple leaves** blown to near-white against the sky, with no overlap
and no depth).

The sheet work landed — the cards are smaller and denser than pass 04. The
**placement** did not: the cards are still laid on a regular axis-aligned grid,
so an 8-way UV rotation rotates the *content* of each cell and leaves the cell
grid intact. That is why the fix measured clean in the sheet and fails in the
frame.

**And the defect nobody has named:** in `craft-walk-04` the tree's shadow on the
paving is **five or six discrete hard-edged black quadrilaterals** — the leaf
cards casting as opaque polygons with no alpha in the shadow pass. At 09:30 with
a 38° sun this is on the ground in roughly half the frames in the build, and it
is the loudest possible "this is not a shipped game" signal short of a missing
texture. `t-gate-south`'s dapple used to be the best lighting event in the
project; this is the same system failing.

**Fix.** (a) Jitter each card's *position* by ±0.5 cell and its *scale* by
±30 % — the lattice is in the placement, not the UVs. (b) Enable alpha-test in
the shadow material for foliage. (c) A transmission term: a third of cards are
still silhouette-black and the lit ones blow to pure white.

### 4. `t-gate-south` has regressed, and it was the best frame in the build

Pass 04: *"the strongest frame in the build … put this next to a Divinity's
Reach outer gate and it holds its ground."* Three things have been taken out of
it:

- **The dappled tree shadow is gone.** There is no tree near the south gate in
  this build and the road is a flat, evenly-lit plane. The light-and-air agent
  warned that a rebuild from source made a tree vanish from this frame. It has.
- **The wear pattern in the carriageway is gone.** The setts are correct and
  coursed but uniform in value from kerb to kerb, with no worn channel — which
  `t-square` and `mere-walk-05` both have.
- **The curtain wall is now a cold blue-grey polygonal plate** — near-flat
  irregular slabs 1.5–2.5 m across (larger than the figure), in a hue that
  appears nowhere else in Hearthmere, with the **tile visibly repeating five
  times** across the run: the same light slab with a dark notch recurs at
  x≈60, 300, 420, 1150 and 1290. It abuts the gatehouse's warm sandy stone at a
  hard vertical seam with no transition, at 12 m, in a mandated hero camera.

Also unchanged: the gatehouse's own stone is the smeared cream-and-brown
camouflage with no course lines and no block edges — the blankest surface in the
frame — and the shrine box at frame right is a flat beige untextured box on a
plinth.

**Fix.** Whatever changed the enceinte's material key this wave, change it back
or forward to the church's — one masonry family for curtain, gates and towers,
as §8 has asked for three passes. And find the missing tree: `check_walkable`
and `validate.py` both pass, so nothing in the harness can see it.

### 5. `cobble_wall` changed failure mode rather than getting fixed

`tools/assetgen/core/materials.py:2602 cobble_walling()`. The order-inversion
and the deeper joint are real and documented in source, and the sheet now
carries per-stone value. In the frame:

- **`bailey-walk-04` at 2 m:** irregular polygonal plates with straight edges
  meeting at three-way junctions, separated by thin dark cracks. That is a
  Worley tessellation — a dried lake bed — which is the exact mechanism the
  uv-and-stone agent correctly diagnosed and removed from `cobble`,
  `town_earth` and `river_gravel`. It was never carried to `cobble_wall`. And
  the plates are 0.5–0.9 m across against a 1.75 m figure: river cobble is
  80–250 mm.
- **`craft-walk-04` at 25 m:** the same wall resolves into a dense regular
  **chevron/zigzag moiré** that reads as corrugated cardboard. That is a mip
  problem, not an albedo problem: a high-frequency normal at a grazing angle
  with no LOD strategy.

**Fix.** Rebuild on `coursed` like everything else that got fixed this wave;
stone size 0.12–0.28 m; a real dome (the ellipsoid exponent is in there, it is
being flattened by the plate boundary); and a mip chain that fades the normal
map's amplitude with distance rather than aliasing it.

### 6. Emerald is still hard-edged and it is still the most saturated colour in the town

**`alley-walk-03` is the frame that settles it, and pass 04's sentence still
describes it word for word:** the bottom third is a quilt of opaque, hard-edged,
**saturated emerald** polygons over brown earth and pale shingle, with
dead-straight boundaries and zero feathering, at 3–8 m. I count six distinct
green polygons with 90°/45° straight edges. The cell got smaller between passes;
the edge did not get softer and the green did not get quieter.

**Other frames:** `spine-walk-06` (a ~4 × 6 m emerald rectangle at 3–8 m butting
brown earth and stone), `bailey-walk-04` (five green quads over pale shingle at
3–6 m), `craft-walk-04` (both verges), `spine-walk-03`, `wharf-walk-06`,
`sty-walk-03`, `t-square` (blotches on the fountain kerb).

**And the same green is still doing daub.** `alley-walk-03`'s timber-frame at
frame right and `spine-walk-03`'s at frame left both have **bright emerald
infill panels between the studs** — pass-02 §14's "green daub" verbatim — while
`mere-walk-05` two hundred metres away has correct buff plaster. The fix landed
on some buildings and not others, which is worse than not landing at all: it
means two of the same building type disagree about what a wall is made of.

`venues/landscape.py _surface_patch` — `ragged` still drops **whole cells**, so
a 0.72 m step at 3 m is still a right angle to the eye. Pass 03 asked for three
things; none of the three has been done in two passes: **feather the alpha over
the outer 2–3 cells instead of a binary in/out, rotate each patch's lattice by a
per-patch seeded angle, and desaturate `grass_lush` by ~25 %.**

The desaturation is the one that matters. In `spine-walk-06` the grass verge is
a more saturated colour than the crimson confectioner two buildings away.

### 7. Seven masonry treatments, and the count has risen every pass

Two, three, four, five, **seven**. In `t-gate-north` alone: giant-plate ashlar
(curtain), smeared cloudy mottle (drum towers), fine speckled sandstone (gate
frontispiece), wavy-lozenge crocodile skin (bridge parapet), flat untextured
slab (coping). `t-gate-south` adds the cold blue-grey plate. `bailey-walk-04`
adds `cobble_wall`'s cracked mud. `wharf-walk-06` puts four of them within one
8 m span, meeting at hard corners with no transition.

Also unchanged in `t-gate-north`: no gate doors, no portcullis, the heron
keystone plaque still a flat inset panel at a different value from its wall, and
in `bailey-walk-04` a row of **bare putlog beams projecting into space carrying
nothing**.

**Fix.** Pick the church's key. Every curtain, tower, gate cheek, bridge parapet
and revetment in Hearthmere uses it, with ashlar reserved for dressings and one
authored sandstone for the rebuilt stretch. This is a `MATS` mapping table, not
new recipes, and it is the single highest-leverage cohesion edit available.

### 8. Field hedges are extruded ribbons with a sine top, and they own the bottom half of two approach cameras

**Frames:** `t-approach-w` — two ribbons, **pure unlit black**, bottom 45 % of
the frame, in the western field approach. `t-approach-s` — four or five ribbons,
dark green, bottom 45 %, one running dead through frame centre. `t-plan`,
`t-aerial-sw` — the radial-and-concentric layout they are laid on.

They are smooth solids with a green mottle painted on and a sinusoid along the
top edge. No branch, no gap, no light through, no shadow side that is anything
but black. Pass-02 §19, pass-03, pass-04 §15 — unchanged.

**Fix.** Two things and they are cheap. (a) A transmission term, which the
foliage needs anyway (§3) — a hedge at 09:30 with the sun behind it is *bright*
at the edges, never black. (b) Break the extrusion: a hedge is a run of
individual bushes with gaps, gate posts and a ditch, and the run should be a
scatter along the line rather than one lofted solid.

### 9. The fountain has lost the arrival frame, and its water is culled between 6 m and 12 m

**Frames:** `fountain-free` at 6 m — the falling water **is** there, and it is
exactly what pass 04 described: hard-edged opaque pale ribbons stuck to the air
with no transparency, no volume and no splash where they land; the basin is a
flat teal disc with green blotches, no ripple, no refraction; the bronze spouts
are near-black lumps with no metal in them.

**`t-square` at 12 m — there is no falling water at all.** The upper bowl is
empty and the basin is a flat sandy disc. The water is being culled somewhere
between 6 m and 12 m, which is inside every gameplay camera that looks at the
square. `t-arrival` at 43 m — the fountain is ~40 px of pale blur and the guild
tower is the composition's focal point at ~180 px.

Pass 04 measured the fountain at ~110 px in the aperture and called it fixed. It
is smaller now, the tower beside it got taller, and the water that made it read
is gone by 12 m.

`BUILD_DIRECTIVE` §3.2 names the fountain as the arrival frame's focal point.
It is not.

**Fix.** In order: (a) find the LOD/distance cull on the fountain's water
primitive — this is a one-line reach change and it is the difference between a
dry ornament and a fountain in the town's most-viewed space; (b) volumetric
falling water with a splash ring; (c) a rippled basin; (d) metalness on the
heron and the spouts. The mass is right — it is the only object in the build
this review has ever called fixed on its geometry.

### 10. The confectioner is still a fire-engine-red building on the arrival route

`tools/assetgen/venues/confectioner.py:62 PAINT = "painted_crimson"`.
**Frame: `kirk-walk-05`** — every timber, every mullion, the barge boards, the
door, the shopfront frame, the jetty brackets and the window surrounds are
saturated crimson, with a saturated orange awning and a row of orange finials
along the barge board. It is the most saturated object in Hearthmere and it
stands on the church-to-market sightline ~25 m from the arrival axis.

Pass 03 asked for the paint to be confined to trim. Pass 04 made it an explicit
AD ruling. **Third pass, unchanged.** Confine `painted_crimson` to barge boards,
door and shutters; put the frame back in oak.

Two **black unlit finials** stand on the churchyard piers in the same frame,
also unchanged from pass 04.

### 11. Thatch, cloth and the quay are unchanged

- **Thatch** (`mere-walk-05`, both roofs; `spine-walk-03`): some directional
  streaking arrived, which is progress in the sheet. In the frame it is still a
  smooth pale olive membrane with a **knife-edge eaves** (zero thickness), a
  dead-straight ridge, no bundle edges and no courses. It reads as canvas
  stretched over a frame. The eaves cut belongs in the *mesh* — an eaves course
  is a separate strip of geometry with its own material, which is what it is in
  reality.
- **Cloth** (`sty-walk-03`): five perfect rectangles on a line, dead-straight
  hems, no sag, no peg pinch, no thickness. The desaturation landed two passes
  ago; the geometry has never been touched.
- **The water gate** (`wharf-walk-06`): the **untextured dark-brown box is
  still there**, dead centre of frame, ~2 m, unchamfered, no material detail —
  third pass. Plus a pure-black unlit bar, a vermilion untextured bar that
  recurs in `spine-walk-06`, four masonries in one 8 m span, and a pole running
  the full height of frame centre.
- **The quay deck** (`wharf-walk-08`): still a modern civic plaza — a rigid
  orthogonal grid of ~1.2 m slabs, all one pale grey value, 90° joints, some
  inset in recesses, covering 60 % of the frame at 1–15 m, with the wavy
  crocodile normal wobbling inside every slab. **And it is empty**: two rope
  coils and four bollards. No cargo, no crates, no barrels, no nets, no stains,
  no load-path wear — and no boats anywhere in the frame. Pass-04 §15, and this
  is the town's working waterfront.
- **`river_gravel`** (`t-bridge` bank at 2 m, `bailey-walk-04` at 3 m): reads as
  **polystyrene packing foam** — rounded pale blobs on a lattice, one value, no
  dirt, no wet line, no size grading. The uv-and-stone agent said "closer to
  mosaic than shingle"; it is worse than that at 2 m.
- **`tree_far`** (`wharf-walk-08`, the far bank at 100 m): a solid wall of
  identical pale mint-green crowns blown out to near-white at the top, over a
  hard white shoreline. `uv_density.py` clears it at 1.07×, so this is a value
  and variation problem, not a scale one.

### 12. The perf instrument reports the previous frame's LOD state, and the budget gate reads it

Proven in five probe runs into `review/shots/ad-town-05/probe/`, all on
identical assets:

| command | `square` draws | `square` tris |
| --- | --- | --- |
| `--views square` | **1,385** | 3,591,341 |
| `--views square` (repeat) | **1,385** | 3,591,341 |
| `--views arrival,square` | **1,385** | 3,591,341 |
| `--views plan,square` | **989** | 2,767,053 |
| `--views aerial-ne,square` | **989** | 2,767,053 |

The harness samples `renderer.info` before the LOD selector has been re-run for
the new camera, so a gameplay camera that follows a distant camera is measured
with the whole town at far LOD. **The default view list opens with `plan` and
three aerials.** Every gameplay number in every report this project has produced
is therefore ~30 % low and order-dependent.

**`check_client.mjs` independently confirms it and fails outright:**
`FAIL: 1395 draw calls at the arrival camera (scene 540 + shadow 570 + ao 206 +
post 79), over the §7 budget of 900`. My isolated probe of the same camera gave
1,376. `t-report.json` from the standard command gives **1,024** for that
camera. Pass 04's headline instrumentation win was that the client and the
harness agreed to 0.7 %; **they now disagree by 36 %**, and the harness is the
one that is wrong.

The honest current numbers: **1,385 draws against 900 (1.54× over) and 3.59 M
triangles against 3.5 M (2.6 % over)** at `square`; 1,395 at `arrival`. Notably
the **shadow pass is 570 of the 1,395** — 41 % of the frame and larger than the
beauty pass, exactly as the atlas agent reported. The cascade rig, not the
atlas, is the budget's critical path.

**Fix.** In `shoot()`, render twice and sample after the second render, or call
the LOD update explicitly before `renderer.info` is read. Then re-baseline —
and note that the atlas work is still a real 19.4 % primitive reduction; it is
the measurement that is wrong, not the optimisation.

### 13. The sky has never rendered, five passes running

`atmosphere.sky` authors `sunAngularSize 1.6`, `sunGlow 0.4` and
`cloudAmount 0.34`. **In 61 frames there is no sun disc anywhere and one wisp of
cloud** (`sty-walk-03`, top-left corner). Every exterior frame's upper third is
a flat blue gradient.

This is not a small thing at this stage. Six frames are now within reach of a
blind side-by-side and *all six* have an empty sky, which is the cheapest
remaining tell. A single cumulus bank at 30° elevation behind the church tower
would do more for `t-arrival` than another material pass.

### 14. Two geometry defects the instruments cannot see

Both found by looking, neither reachable from `validate.py` (0 failures, 0
warnings), `check_walkable` or `town.mjs`'s own floating-mass check.

- **A roof that does not attach.** `alley-walk-03`, the dovecote at
  x≈1050–1200: the cone's eaves float clear of the drum with a bright sky sliver
  visible on both sides at y≈130–150. "Nothing floats, roofs attach" is a hard
  constraint and this is a roof hanging off its own wall at 25 m.
- **An unlit roof plane over open ground 6 m west of the church door.**
  `westfront-free` (eye 1.62 m at 38, −0.5 looking at the west front): the whole
  upper half of the frame is a brown, near-unlit roof soffit with no supporting
  structure anywhere in view, over grass and a stone wall. This is consistent
  with the **359 m³ `church`/`warehouse` deep geometry overlap** and the
  **547 m³ `warehouse`/`townhouse` overlap** that `t-report.json` reports as
  kit-layer intersections. 547 m³ is a room. Either they are authored and should
  be annotated, or a kit mass is sitting through the town's hero venue.

### 15. Correctness, for the record

**The instruments have regressed, and worse, they now disagree with each other.**
I ran all four myself:

| instrument | pass 04 | **pass 05** |
| --- | --- | --- |
| `validate.py` | 0 failures, 41 warnings | **5 failures, 46 warnings** |
| `check_walkable.mjs` | 15/15 PASS, 1 unreachable door | 15/15 PASS, **1 unreachable door** |
| `check_client.mjs` | boots, budget not gated | **FAIL: 1,395 draws at the arrival camera** |
| `town.mjs` → `t-report.json` | 1,416 draws, 41 warnings | 1,031 draws, **0 warnings** |

- **`validate.py` fails on five items**: four `uv_density` scale failures
  (`nogging` 0.47×, `straw` 0.38×, `wool_crimson` 3.10×, `canvas_amber` 0.41×)
  and **`§7 mesh memory 243.3 MB / 240 MB`** — 1.4 % over the cliff. The uv
  agent flagged the memory one and it is still over.
- **The unreachable door was not closed, it was moved.** Pass 04's was
  `hm.townhouse.door.15`; it is now **`hm.slot.07.chophouse.door.01`** — and
  slot 07 is the one the wall-market agent moved from a 4.4 m overlap to a
  0.7 m overlap with the inn. `BUILD_DIRECTIVE` §9's first box — *"the player
  can walk from the church altar to every venue door"* — is unticked for the
  fifth consecutive pass.
- **The two geometry instruments disagree about a countable fact.**
  `validate.py` reports **five** sunk masses (`moot_hall` −2.03, `quay` −4.55,
  `townhouse` −2.09, `watermill` −2.40, `wellhouse` −2.80). `t-report.json`
  reports **two** (`moot_hall`, `wellhouse`). Same tree, same run, same
  question, different answers. Whichever is right, the project cannot currently
  say how many masses are sunk. Still none of them annotated, so no check can
  tell a cellar from a defect.
- **`check_client.mjs` is the honest one.** It fails the budget gate outright at
  **1,395 draws at the arrival camera**, which matches my isolated probe of
  1,376 and the atlas agent's 1,385 at `square`. `town.mjs` says 1,024 for the
  same camera in the same wave. **The client harness and the render harness now
  disagree by 36 %** — and pass 04's headline instrumentation win was that they
  agreed to 0.7 %. That agreement is gone, and §12 is why.

**And §14 above is the caveat that outranks all of this: the harness got
cleaner and the frames did not.** A floating cone roof, an unlit roof plane over
open ground beside the hero venue, a vanished tree on a hero camera, a fountain
whose water is culled at 12 m, and a mandated camera that stands under the river
are all invisible to every instrument in the project. Zero warnings from
`town.mjs` is not zero defects, and this is the pass where that gap became the
largest thing between the build and an ACCEPT.

`tools/uv_density.py` is a genuinely good new instrument and I want it kept —
it is the first thing in the project that turns "the texture is the wrong size"
into a number with a venue attached. Beyond the four failures it warns on
`oak_dark` 0.56× (the timber framing on the town's most-repeated building),
`ashlar_civic` 0.60× (the guild tower) and `dirt` 0.59×.

---

## Would any of these frames survive a blind side-by-side against a shipped AAA MMO?

Counting gameplay cameras only. Last pass: three survived two seconds, none
survived ten. **This pass: eight survive two seconds, and one survives ten.**

**Survives ten seconds — one frame, and it is the first in the project.**

**`mere-walk-05`** (Mere Street looking west to the West Gate). Two coherent
street walls of jettied, braced, shuttered timber-frame with **buff plaster
infill**; a correctly coursed sett carriageway with a worn channel, a kerb, a
gutter and weeds in the joints; barrels, planters, a lamp; the figure planted
with a contact shadow; a gate arch closing the view at 40 m with correctly
judged aerial perspective and trees beyond it. I looked at this for a minute and
the only two things I can name are the thatch (a cream membrane with a knife
edge — and it is at the top of frame, where the eye goes last) and the empty
sky. Put it next to a Divinity's Reach residential lane and you would have to
hunt for the difference.

**Survives two seconds — eight frames.**

1. **`mere-walk-05`** — as above.
2. **`fountain-free`** (the market place at 1.62 m, 6 m from the fountain) — the
   best-dressed frame in the project and it is now the *most important* space in
   the town, not the least. A butcher's pitch with hanging meat, a cheese table,
   a chopping block, firewood, a wine cup, a straw heap, a handcart, a sagged
   striped awning. Pass 04's §13 asked for exactly this and got more than it
   asked for. Fails at ten because the church tower behind it is a blank pale
   slab at 20 m and the falling water is opaque cream ribbons.
3. **`t-square`** — the biggest single-frame improvement in the project. Lamp
   out, clean composition, correct setts, a worn diagonal, real residue, a
   contact shadow. Fails at ten on the chequerboard oak, the dry fountain and
   the black heron.
4. **`craft-walk-04`** — Bakers' Row. Excellent paving, good timber-frame with
   nogging and hanging goods, real depth. Fails at ten on the chevron-textile
   enceinte closing the view and the black-lozenge tree shadow.
5. **`kirk-walk-02`** — Kirkgate. Setts with a worn patch, jettied ranges,
   bean poles, a good warm/cool read. Fails at ten on the cyclopean ground floor
   at frame left and the chequerboard tree.
6. **`spine-walk-06`** — Ford Road. Fails at ten on the right-hand building's
   cyclopean ground floor at 2 m and the hard emerald quad.
7. **`t-approach-s`** — the canonical return, cleared of its tree, a real walled
   profile with roofed towers. Fails at ten on the extruded sine-top hedges in
   the bottom 45 %.
8. **`t-arrival`** — solved composition, real worn floor, depth in the aperture.
   Fails at ten on the cyclopean interior masonry, which is 55 % of it.

**What separates the survivors is no longer luck and it is no longer four
things — it is two.** Every surviving frame is *paved in the new setts* and
*contains no water, no leaf card within 25 m, and no cyclopean masonry within
5 m.* The paving fix alone moved four frames onto the list. The two remaining
systemic failures are **the close-range masonry recipe (§1)** and **the foliage
system (§3)** — every other ten-second failure on the list above is one object,
not a system.

**And that is the whole answer to "how far".** Six of the eight survivors fail
at ten seconds on §1 or §3. Fix those two and six frames go from two seconds to
ten in one wave, without a single new asset.

**Everything else still fails inside two seconds**, and now on a much shorter
list than pass 04's: the water (§2), the cyclopean masonry (§1), the hedges
(§8), or a leaf at close range (§3).

---

## What the next wave must do, ranked

1. **Rebuild the close-range masonry recipe on `coursed`.** Chamfer down 4×,
   joints straight, blocks 0.35–0.55 m, per-stone value last. It is the only
   thing wrong with `t-arrival` and it is on six other frames. §1
2. **One masonry family for the enceinte, gates, towers and bridge** — the
   church's key, ashlar for dressings only. A mapping table, not new recipes.
   It closes the count that has risen every pass. §7, §4
3. **Water.** Camera Y above `waterLevel` first (it fixes `t-bridge` and
   `spine-walk-01` in one function), then knee 0.55, then noised shoreline
   outlines, then a planar reflection. §2
4. **Foliage: jitter the card *placement*, alpha-test the shadow pass, add a
   transmission term.** The sheet is fixed; the lattice is in the scatter and
   the shadow is opaque. §3
5. **Desaturate `grass_lush` ~25 % and feather `_surface_patch`'s alpha over
   the outer 2–3 cells.** Two numbers, and they close a finding that is four
   passes old. §6
6. **Get the fountain's water rendering at 12 m and 43 m**, then give the heron
   metalness. The town is composed around an object that is currently dry. §9
7. **Fix the perf instrument** (render twice, sample second), re-baseline, and
   accept that the real number is 1,385/900. Then take the atlas agent's costed
   route: per-cascade caster culling, merged character meshes, the three
   material collapses. §12
8. **The sky.** Get the authored sun disc and 0.34 cloud amount to render. It is
   the cheapest remaining tell, and it is on all eight surviving frames. §13
9. **Hedges:** transmission term, and break the extrusion into a scatter. §8
10. **`gate-north` onto the bridge centreline**, and the walk camera onto
    authored deck levels. Fourth pass for both. §7, §2
11. **Thatch:** eaves course into the *mesh*; stalk structure; thickness at
    ridge and eaves. §11
12. **Correctness sweep from the frames, not the instruments**: confine
    `painted_crimson` to trim; give the black finials a material; delete the
    untextured box at the water gate; attach the dovecote's cone to its drum;
    resolve or annotate the 547 m³ and 359 m³ deep overlaps and the roof plane
    west of the church door; annotate the two sunk masses. §10, §11, §14, §15
13. **Terracotta:** the three kiln batches exist in `COLOR_0` and do not read
    from the air. The base is too saturated to multiply down from — desaturate
    the base sheet by ~20 % and re-check `t-aerial-sw`. §pass-02 21
14. **Fields:** break the radial-and-concentric layout; re-hue the pink-mauve
    fallow. §pass-02 19
15. **The quay.** Plank it, patch it, wear it in the load paths, and put cargo
    and moored boats on it. It is the town's working waterfront and it is
    currently an empty municipal plaza. §11
16. **`river_gravel`** — size grading and a wet line; it currently reads as
    packing foam at 2 m. `tree_far` — value variation and a top that does not
    blow to white. §11

---

## How far is this from an ACCEPT?

**Three waves, and I will say what has to be in each.**

This is the first time I can answer that question with a number instead of a
shrug, and the reason is that the failure list is now *specific objects and two
systems*, not "the surfaces are wrong".

- **Wave 1 — the one that decides it.** Items 1–4: the close-range masonry
  recipe, one masonry family, the water, and the foliage placement/shadow. Those
  four stand between **six frames at two seconds and six frames at ten**. They
  are four recipes and one camera function; they need no new assets, no new
  venues and no new geometry. If wave 1 lands and I can verify it in frame, the
  build is one wave from ACCEPT.
- **Wave 2.** Items 5–9: grass, the fountain's water, the perf instrument and
  the real 1,395 → 900 route, the sky, the hedges. This is the wave that turns
  "survives ten seconds" into "I would not know which game this is".
- **Wave 3.** Items 10–16 plus a full re-shoot and a clean `validate` /
  `check_walkable` / `check_client` / budget-gate sweep with the four
  instruments agreeing with each other. Correctness and the last unticked box in
  §9.

**What would make me revise that upward to five or six waves — and it is a real
risk:** if wave 1 comes back with the masonry claimed and the frame unchanged.
The cyclopean block has now survived one explicit rejection; `cobble_wall` has
survived three; `painted_crimson` three; `gate-north`'s composition four; the
emerald ground quilt four; `spine-walk-01`'s camera four. **The pattern in this
project is that data changes land and recipe changes do not** — the wall
heights, the tower list, the atmosphere numbers and the `KEEP_CLEAR` rule all
landed this wave, and every one of them is a number in a file. Items 1 and 2 are
both recipe changes and item 4 is a scatter change. That is the project's known
weak axis, and it is the whole of wave 1.

**What makes me say three and not six:** this wave closed **four pass-02
findings outright — the first time anything in this project has closed** — and
it did it on the two largest surfaces in the build, the streets and the shadow
edge. It also produced the first frame I would defend for ten seconds. And the
agents caught and stated four things they had *not* fixed rather than claiming
them; one of them — `cobble_wall`, *"right in the sheet but I never got it in a
frame, so I am not claiming it"* — is exactly the standard this review has asked
for through four passes. **That is the behaviour that gets a project to ACCEPT,
and it appeared this wave for the first time.** Five claimed-but-false fixes
last pass; one this pass (the leaf card).

---

## Budget, for the record

Worst gameplay camera, measured honestly: **1,395 draw calls / 900 at `arrival`
(`check_client.mjs`, FAIL)** and **1,385 / 900 with 3,591,341 triangles /
3,500,000 at `square`** (isolated `town.mjs` run). Attribution at `arrival`:
scene 540 + shadow 570 + AO 206 + post 79 — **the shadow pass is 41 % of the
frame and larger than the beauty pass.** `t-report.json` from the standard
command claims 1,031 and passes the triangle gate; §12 explains why that number
is wrong and how to fix the instrument.

`validate.py`: **5 failures, 46 warnings** (was 0 / 41). Four are
`uv_density` scale failures; one is **§7 mesh memory 243.3 MB / 240 MB**.
`check_walkable.mjs`: 15/15 streets PASS, 0 obstructed, **1 unreachable door**
(`hm.slot.07.chophouse.door.01`) — §9's first box unticked for the fifth pass.
`check_client.mjs`: boots, walks 151.5 m, fails the budget gate.

The budget is still not what is wrong with these frames. But it is now failing
in *three* instruments that disagree with each other about by how much, and
that is a new problem this wave created.
