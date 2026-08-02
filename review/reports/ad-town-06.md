# Art-director review — Hearthmere, whole town, pass 06

**Verdict: REJECT — and the distance to ACCEPT has closed to two waves, with a
shorter and more concrete list than this project has ever had.**

Reviewed 2026-08-02 against `docs/ART_BIBLE.md` §8, `docs/BUILD_DIRECTIVE.md` §3
(arrival), §4 (geography), §6 (structure), §7 (budget) and §9 (done).

**I rebuilt the whole tree from source before rendering anything.**
`tools/assetgen/core/materials.py` had an mtime *later* than `ashlar_albedo.png`,
`ashlar_civic_albedo.png`, `sandstone_albedo.png` and `cobble_wall_albedo.png` —
i.e. the masonry sheets on disk were potentially stale against the very change
this wave is judged on. `python tools/assetgen/build.py --force-textures`,
7m07s, exit 0. Every frame below is that build.

**69 frames rendered by me at the locked 09:30 rig into
`review/shots/ad-town-06/`** on the identical camera list to pass 05, so the two
sets are comparable frame for frame (`review/shots/ad-town-06/render.sh`).
**Twenty-eight read at full resolution**, several with crops; the remaining
forty-one scanned on three contact sheets (`sheet-0/1/2.png`). Every frame cited
below I opened. I ran `validate.py`, `check_walkable.mjs`, `check_client.mjs`
and `uv_density.py` myself.

---

## The verdict, stated plainly

**This wave did what I asked it to do, and it did it in the frame, not in the
source.** I said pass 05 that the pattern in this project is "data changes land
and recipe changes do not", that wave 1 was entirely recipe changes, and that if
it came back claimed-but-unchanged the distance would go to five or six waves.
It came back changed. Four of the four items:

- **§1 the wavy cyclopean block is gone.** `t-arrival`'s nave is properly
  coursed ashlar with straight joints, a real arris and per-stone value at
  ~0.4 m courses against the 1.75 m figure. `spine-walk-06`, `kirk-walk-05`,
  `craft-walk-04`, `mereshore-free`, `bailey-walk-04` all confirm. The single
  largest area of wrong pixels in the build is now right. **FIXED.**
- **§7 one masonry family.** `wharf-walk-06` had four treatments in one 8 m span
  and now has one. `t-gate-north` had five and now reads as one bond across
  curtain, towers and gate. `t-gate-south`'s cold blue-grey plate — pass 05's
  worst regression — is gone. **Seven recipes down to one family, verified in
  frame.** The count that rose every single pass has fallen.
- **§2 the water.** `t-bridge` has a river in it and the camera is above the
  surface. `t-approach-ne`'s featureless white specular plate is gone and
  replaced by a resolved glitter path over a rippled sheet. `mereshore-free`'s
  sawtooth teeth are gone. `t-square` has falling water in the fountain at 12 m.
  `t-aerial-sw`'s Mere is no longer an ellipse. **Substantially FIXED.**
- **§3 the leaf-card lattice.** `t-square`'s market oak and `kirk-walk-05`'s
  flanking trees now have branching crowns with a real silhouette and dappled
  light. The axis-aligned grid I could count eight columns of last pass is not
  in any of the 69 frames. **FIXED.** The *shadow* half of §3 is not.

**And the instruments told the truth for the first time.** `check_client.mjs`
1,398 draws against `town.mjs` 1,378 — **1.5 % apart, was 36 %.** The gameplay
number the harness prints is now 1,381 at `square`, not the 989 it used to print
while the real number was 1,385. That is a project that can now measure itself.

**Against that, this is still a REJECT, and for reasons that are almost entirely
individual named objects rather than systems.** The list:

1. **The bridge parapet at `t-gate-north` is a perforated industrial panel** —
   a machine-regular row of oval portholes filling the right 45 % of a mandated
   hero camera. The masonry agent flagged it, declined to claim it, and was
   right to; it is now the loudest single defect in the build.
2. **`spine-walk-01` is still inside the bridge deck.** 45 % of the frame is
   unlit black. **Fifth pass.** It is the *first* frame of the town's spine.
3. **`westfront-free` is still a brown unlit roof soffit over open ground**, 42 %
   of the frame, six metres from the church door, with no supporting structure
   in view. That is the 547 m³ / 359 m³ deep overlap made visible. **Unchanged.**
4. **The black lozenges on the paving are still there** (`craft-walk-04`,
   `craft-walk-02`) — and I can now say what they are not, and what they are.
5. **The emerald ground quilt is unchanged for a fifth pass** (`alley-walk-03`,
   `spine-walk-06`, `bailey-walk-04`, `wharf-walk-06`).
6. **The enceinte's inner face is a chevron pleat** in roughly eight frames — a
   *mesh* defect, correctly diagnosed by the masonry agent and not owned by
   anyone.
7. **The one masonry family landed at the wrong value.** `t-arrival` lost a
   third of its light: mean luminance **116.1 → 82.6**, 10th percentile
   **53 → 32**. Every other frame I measured is flat or brighter. This is not
   the lighting; it is `MASON_BODY`.

**Blind, side by side against Divinity's Reach, Gridania, Ul'dah and
post-Legion Boralus: twelve frames survive two seconds, and two survive ten.**
Last pass, eight and one. Named in the last section.

---

## Claims from this wave that the renders do not support

Fewer than any previous pass, and two of the four were declared by the agent
itself, which I count as reporting correctly rather than as a failed claim.

- **water-finally: *"`t-gate-north`'s bank is a coherent shingle beach instead
  of a 1 m grass/silt chequerboard."*** **Rejected.**
  `review/shots/ad-town-06/crop-gn-bank.png`. The bank is a **row of dark
  triangular teeth**, each 3–4 m across, in a perfectly regular zigzag along the
  entire visible shore, with a hard-edged saturated emerald ribbon on top of
  them. It is not a chequerboard any more; it is a sawtooth revetment, and it is
  the same defect class the report claims to have removed. The chequerboard was
  fixed; the beach was not built.
- **foliage-placement: *"The black lozenges in `craft-walk-04` are not
  foliage."*** **Partly rejected, and I have a better lead than the one handed
  off.** They are in `craft-walk-04` and in `craft-walk-02`, and in
  `craft-walk-02` **they lie on fully sunlit paving with no shadow around them**
  (x≈380–900, y≈600–880). That settles it: they are not shadows. They are
  **flat, near-black, leaf-shaped polygons lying on the road surface** — dark
  arrowheads and lozenges, individually scattered, 0.2–0.5 m across. The three
  `--skip` proofs in the report all skipped the wrong layer. See finding §4.
- **masonry-family: *"`sandstone` is fixed as cohesion but not yet as
  character."*** Accepted as stated, and I want the honesty on the record — but
  the same sentence is now true of the **whole family**. `t-gate-south`'s
  1,600 px of curtain wall is one flat value with no weathering, no batter, no
  plinth and no bedding variation; `mereshore-free`'s mill is a 12 m grey slab;
  `mere-walk-03`'s left-hand building is a blank ashlar plane over 40 % of the
  frame. Cohesion was bought with character, and the trade is visible.
- **masonry-family: *"all my frames are much darker than pass 05 and it is not
  the masonry."*** **Rejected — it is the masonry, and only on masonry-dominated
  frames.** Measured, pass 05 → pass 06 mean luminance: `t-square` 121.2 → 121.3,
  `t-gate-south` 105.8 → 107.8, `mere-walk-05` 109.0 → 108.6, `craft-walk-04`
  80.7 → 82.4, `wharf-walk-06` 68.7 → 72.1. Five frames flat or brighter. And
  **`t-arrival` 116.1 → 82.6, p10 53 → 32.** The only frame that went dark is
  the only frame that is 55 % close-range masonry. `MASON_BODY` is too dark and
  too cool.
- **instruments-and-determinism: everything I could check, I confirm.**
  `check_client` 1,398 vs `town.mjs` 1,378 at the same camera. `t-report.json`
  now prints 1,381 at `square` where it used to print 989 for a real 1,385. The
  §12 diagnosis in my own pass-05 report was wrong and this agent proved it
  wrong with numbers. That is the correct way to overrule a review.

---

## The three standing questions, answered from frames

### (a) Does the arrival frame deliver BUILD_DIRECTIVE §3?

**Composition: yes. Surface: fixed. Light: newly broken.**

| §3.2 requires | in `t-arrival` |
| --- | --- |
| the descending church steps | **yes** |
| a street leading the eye | **yes** |
| the market fountain as the focal point | **no** — still ~40 px of blur at 43 m; the guild tower still owns the aperture |
| ≥ 2 other venue anchor silhouettes | **yes** — tower, slate gable, cupola, jettied range |

The thing that stopped this frame for two passes is **closed**. The nave piers,
voussoirs and wall panels are coursed ashlar at a believable module. I compared
`ad-town-05/t-arrival.png` and `ad-town-06/t-arrival.png` side by side and the
difference is the difference between a stylised cave and a parish church.

What now stops it, in order:

- **The frame lost a third of its light.** Mean 116.1 → 82.6. The nave reads
  gloomy and cold where it read as sunlit limestone. The masonry is right and
  the *stone* is wrong: `MASON_BODY` (`core/materials.py:779`) is mixed
  `FOUNDATION → CANVAS_CREAM` at 0.24, and the family's whole warmth span is
  0.013. Lift the body ~15 % in value, push the mix toward `CANVAS_CREAM`, and
  widen the family warmth spread to ~0.05 so a church, a curtain wall and a
  quay are not the same grey.
- **A pure-black unlit void in the aisle arch**, ~200 × 150 px at 1–3 m
  (`crop-arrival-pier.png`, upper left). Not a dark interior — an unlit polygon.
- **Detached leaf sprigs hanging in the sky** at frame right, x≈990–1070,
  y≈280–420 (`crop-arrival-leaf.png`): four clusters of leaf cards with no
  branch, no trunk and nothing behind them. The new card frames fixed the
  canopy; the *climber* scatter still emits orphan cards.
- **A flat saturated emerald panel** at x≈1010–1075, y≈555–640 — a market stall
  cloth as one opaque green plane.

### (b) Does the silhouette read as a town with a skyline?

**Better again, and still not a hierarchy.** `t-silhouette` at 8 px/m.

- **Ten to twelve distinct vertical events** now read across the profile, at
  four heights. Pass 04 had four, pass 05 seven. The trees now read as *trees*
  in silhouette — branching, irregular crowns — which is the foliage rebuild
  showing in the one instrument that judges profile.
- **The hierarchy has got slightly worse, and I measured it rather than
  eyeballing it this time.** Running the same script over pass 04, 05 and 06's
  `t-silhouette` — datum = median bottom of the black mass, tallest = highest
  row carrying a mass ≥ 6 px wide, general roofline = highest row black across
  ≥ 25 % of the town's span, caption band excluded:

  | | tallest mass | general roofline | ratio |
  | --- | --- | --- | --- |
  | pass 04 | 22.1 m | 15.1 m | 1.46× |
  | pass 05 | 22.1 m | 16.2 m | 1.36× |
  | **pass 06** | **22.1 m** | **16.2 m** | **1.36×** |

  **The tallest mass in Hearthmere has not moved in three passes; the general
  roofline rose a metre, so the ratio fell.** (Pass 05's "2.1×" and my own first
  eyeball of this frame both used a lower roofline estimate; the number that
  matters is the one measured the same way across passes, and by that measure
  the profile is flatter than it was at pass 04.) Divinity's Reach and Ul'dah
  run 2.5–3×. Nothing exists between 17 m and 21 m: the profile still jumps
  from roofline to tower with no intermediate step, and the fix is **one
  building at 18–19 m**, not another tower.
- **The two black boxes below the ground line are still there** at x≈805–870 and
  x≈1090–1140 — the quay and the watermill, legitimately sunk, reading as
  detached masses under the town. Third pass. Clip sunk geometry at the datum in
  the silhouette view.
- **The lower edge of the town between x≈1250 and x≈1450 is still tree crowns.**
  Improved from pass 05's x≈700–1250, but the town's own elevation drawing still
  terminates in scrub at its right-hand end.
- **The wall still contributes no base line**, and cannot at 6.0 + 1.2 m.

### (c) Does it read as one world?

**Yes, for the first time — on masonry. No, still, on ground and on cloth.**

**(i) The masonry family is one family.** This is the finding that has got
monotonically worse every pass since pass 02 — two, three, four, five, seven —
and it has now closed. `wharf-walk-06`: one bond. `t-gate-north`: one bond
across curtain, drum towers and gate frontispiece. `bailey-walk-04`: the wall
and the gate agree. `t-gate-south`: the curtain and the gatehouse agree.
Seven `masonry_bond()` call sites in `core/materials.py` (1742, 1922, 2820,
2937, 3011, 3065, 3135) and every masonry key parameterised against them. **This
is the single largest cohesion win the project has had.** Two exceptions
survive: the **bridge parapet** (§1 below) and the **watermill's own elevation**,
which still carries two bonds meeting at a hard vertical seam at x≈880 in
`mereshore-free`.

**(ii) Emerald is still the material of last resort and it is still
hard-edged.** `alley-walk-03` is the frame that settles it and **it is
byte-for-byte the same complaint as pass 04 and pass 05**: the bottom third is
five or six opaque, hard-edged, saturated emerald polygons over brown earth with
dead-straight 90°/45° boundaries at 3–8 m. `spine-walk-06` has a ~4 × 6 m
emerald rectangle at 3–8 m. `bailey-walk-04` has five green quads over pale
shingle. `wharf-walk-06`, `sty-walk-03`, `t-gate-north`'s bank top. And the same
green is still doing **daub**: `alley-walk-03`'s timber frame at frame right has
bright emerald infill between the studs while `mere-walk-05` two hundred metres
away has correct buff plaster. **Five passes. Nothing has moved.**

**(iii) Cloth is one flat opaque plane wherever it appears.** `fountain-free`
x≈1330–1600 is a 12 %-of-frame dark emerald rectangle with zero sag, fold or
weave. `sty-walk-03`'s washing is five perfect rectangles with dead-straight
hems. `t-arrival` has a green stall panel. This is now the most visible
*remaining* system defect after the ground.

---

## The running scorecard

### Pass-02 findings

| # | pass-02 finding | p03 | p04 | p05 | **p06** | proof |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 18 of 32 venues do not exist | FIXED | FIXED | FIXED | **FIXED** | `t-report.json` 32 placed / 0 missing |
| 2 | leaf atlas incapable of a tree | FIXED | REGR | NOT | **FIXED** | `t-square` market oak, `kirk-walk-05` both trees, `t-approach-s` — branching crowns, no lattice in 69 frames |
| 3 | yew is a 28-face polyhedron | PARTLY | PARTLY | PARTLY | **FIXED** | no faceted sphere; the cards that replaced it now read as a crown |
| 4 | thatch is a smooth cream membrane, knife edge | PARTLY | NOT | NOT | **NOT FIXED** | `mere-walk-05` both roofs, `alley-walk-03` — knife eaves, dead-straight ridge, no bundle, no thickness |
| 5 | no fog / aerial perspective | over | NOT | PARTLY | **PARTLY** | `t-approach-ne` and `t-approach-w` read correctly; `t-arrival` is now too dark to judge |
| 6 | fountain must anchor at 43 m | PARTLY | FIXED | REGR | **PARTLY** | water is back at 12 m (`t-square`) and reads as water at 6 m (`fountain-free`); still ~40 px at 43 m and the tower still owns the aperture |
| 7 | no skyline; tower detached; wall too low | NOT | PARTLY | PARTLY | **PARTLY — slipping** | 10–12 vertical events, up from 7. But measured the same way across three passes the tallest mass is **22.1 m, unchanged**, the roofline rose 15.1 → 16.2 m, and the ratio fell **1.46× → 1.36×** |
| 8 | Mere a stamped ellipse; Emberflow a rectangle; water blows to white | PARTLY | NOT | NOT | **PARTLY** | `t-aerial-sw` — lobed outline, bay and headland, depth, no white plate. Emberflow still near-parallel-sided; a white scalloped fringe on the east shore |
| 9 | `rubble` is crazy paving with green mortar | NOT | PARTLY | FIXED | **FIXED** | holds; and now crisper — the anisotropy fix is visible in `crop-sq05-sett` vs `crop-sq06-sett` |
| 10 | three masonry treatments on one wall | NOT(4) | NOT(5) | REGR(7) | **FIXED** | `wharf-walk-06` 4→1, `t-gate-north` 5→1, `t-gate-south` plate gone. Two exceptions: bridge parapet, watermill |
| 11 | inside the wall is bare brown dirt | PARTLY | PARTLY | PARTLY | **PARTLY** | hard emerald quads remain at 3–8 m in five frames |
| 12 | church west front blank; nave black; tower off-axis | PARTLY | PARTLY | PARTLY | **PARTLY** | nave masonry now correct; still no west window, no apse, and the frame lost a third of its light |
| 13 | no AO; 21 px/m shadows | PARTLY | NOT | FIXED | **PARTLY — REGRESSED** | contact shadows hold in most frames, but in `bailey-walk-04` the figure floats ~0.5 m clear of the shingle (`crop-bailey-feet.png`) and in `mereshore-free` it is buried in the mill wall |
| 14 | one green mottle doing daub, hedge and ground | NOT | PARTLY | NOT | **NOT FIXED** | `alley-walk-03` emerald daub panels; `spine-walk-06` green shutters; ground quads everywhere |
| 15 | a hedge stands in Kirkgate and swallows the camera | NOT | MOVED | PARTLY | **PARTLY** | `t-approach-s` clear of its tree; a ribbon still runs through frame centre |
| 16 | large black unlit polygons | FIXED | PARTLY | NOT | **NOT FIXED** | `t-arrival` aisle void; `sty-walk-03` top-right; `spine-walk-01` 45 % of frame; `westfront-free` 42 %; `kirk-walk-05` two finials; `alley-walk-03` |
| 17 | crude LOD at 25 m; lanes lose their surface | PARTLY | PARTLY | PARTLY | **PARTLY** | lanes hold; `t-square` moot hall, `mere-walk-05` west gate, `fountain-free` church tower all collapse to a flat pale slab past ~25 m |
| 18 | cloth and ivy are flat single-sided quads | NOT | PARTLY | NOT | **NOT FIXED** | `fountain-free` 12 % of frame; `sty-walk-03` five rectangles; `sty-walk-03` fence ivy a green splodge |
| 19 | landscape fields a radial spiderweb | PARTLY | PARTLY | NOT | **NOT FIXED** | `t-plan` — every boundary radiates from or circles the town; fallow still pink-mauve |
| 20 | composition defects in the hero cameras | NOT | NOT | PARTLY(1/3) | **PARTLY (1/3)** | `t-square` holds; `t-gate-north` still off the bridge centreline with the parapet at 45 %; `spine-walk-01` still under the deck. **Fifth pass for both** |
| 21 | roof distribution reads as a checkerboard | NOT | PARTLY | PARTLY | **PARTLY** | `t-aerial-sw` now carries real slate/terracotta clustering; base terracotta still too saturated and ~55 % of roof area |

**Pass-02 score: 7 fixed · 8 partly · 6 not fixed · 0 regressed.**
(p05 was 4 / 9 / 7 / 1; p04 2 / 12 / 6 / 1.) **Three more items closed, nothing
regressed outright, and the two that closed — the leaf atlas and the masonry
count — are the two systems that were between six frames and a ten-second
survival.**

### Pass-05's own findings

| § | pass-05 finding | **p06** | proof |
| --- | --- | --- | --- |
| 1 | wavy cyclopean block owns 55 % of the spawn frame | **FIXED** | `t-arrival`, `crop-arrival-pier.png`; and in all eight other named frames |
| 2 | water not attempted | **PARTLY (mostly fixed)** | `t-bridge`, `t-approach-ne`, `mereshore-free`, `t-square` fountain, `t-aerial-sw`. Not fixed: reflection, the diamond lattice, the `t-gate-north` bank |
| 3 | leaf-card lattice + black-lozenge shadow | **PARTLY (1/2)** | lattice FIXED (`t-square`, `kirk-walk-05`); lozenges NOT (`craft-walk-04`, `craft-walk-02`) |
| 4 | `t-gate-south` regressed | **FIXED** | blue-grey plate gone, one family, tree returned to `t-approach-s`. Wear channel still missing; still no dappled shadow at the gate |
| 5 | `cobble_wall` cracked mud / chevron textile | **PARTLY** | `bailey-walk-04` at 2 m is now correctly coursed stone at ~0.35 m. The chevron at 25 m survives — and it is the wall's **mesh**, not the material |
| 6 | emerald hard-edged, most saturated colour in town | **NOT FIXED** | `alley-walk-03`, `spine-walk-06`, `bailey-walk-04`, `wharf-walk-06`, `sty-walk-03` |
| 7 | seven masonry treatments | **FIXED** | see (c)(i) above |
| 8 | hedges extruded ribbons with a sine top | **PARTLY** | they are lit now, not pure black — the transmission term landed (`t-approach-w`, `t-approach-s`). They are still single lofted solids with a sinusoid top edge owning the bottom 45 % of both frames |
| 9 | fountain water culled between 6 m and 12 m | **FIXED** | `t-square` at 12 m has falling water; `fountain-free` at 6 m now reads as translucent water with volume. Heron still a black lump |
| 10 | confectioner is a fire-engine-red building | **NOT FIXED** | `kirk-walk-05`, `spine-walk-06` — `confectioner.py:63 PAINT = "painted_crimson"` unchanged. **Fourth pass.** Two black finials in the same frame, also unchanged |
| 11 | thatch / cloth / water gate box / quay / river_gravel / tree_far | **NOT FIXED** | every one. `wharf-walk-06`'s untextured box is dead centre for a fourth pass; `wharf-walk-08`'s quay is still an empty municipal plaza; `bailey-walk-04`'s shingle is still polystyrene |
| 12 | perf instrument reports previous frame's LOD state | **FIXED** | `t-report.json` 1,381 at `square`; `check_client` 1,398 vs `town.mjs` 1,378, 1.5 % |
| 13 | the sky has never rendered | **NOT FIXED** | 69 frames, no sun disc, no cloud bank. `cloudAmount 0.34`, `sunAngularSize 1.6` authored and not drawn |
| 14 | floating dovecote cone; unlit roof plane west of the church | **NOT FIXED** | `alley-walk-03` x≈1075–1215 y≈120–135, sky visible under the eaves both sides; `westfront-free` unchanged |
| 15 | instruments regressed and disagree | **PARTLY** | `validate` 5 → **3** failures; parity restored. Still: 1 unreachable door, 7 vs 2 sunk masses, 547 m³ overlap |

**Pass-05 score: 6 fixed · 4 partly · 5 not fixed · 0 regressed.**

---

## Findings, ordered by how much they damage the frame

### 1. The bridge parapet is a perforated industrial panel, and it owns 45 % of a hero camera

**Frames:** `t-gate-north` (right 45 %, 3–25 m), crop at
`review/shots/ad-town-06/crop-gn-parapet.png`; also visible in `spine-walk-02`.

The parapet is a machine-regular grid of **oval portholes** — pale ovals inside
dark rings, four courses high, repeating identically for the full run of the
bridge. It reads as pressed steel or a concrete screen block. It is worse than
pass 05's "crocodile skin", because a wandering organic pattern reads as bad
stone whereas this reads as *manufactured*, which is an Art Bible §2 anachronism
in the plainest sense.

**Cause, already located and correctly declined by the masonry agent:**
`tools/assetgen/venues/gatehouse.py:263` sweeps the parapet in `cobble_wall`
with a **stretched swept UV**. `cobble_wall`'s per-unit dome is now a proper
ellipsoid; stretched 3–4× along the sweep it becomes an oval, and the joint
becomes a ring around it.

**Fix.** Route the sweep's UV through `MATS.uv_scale('cobble_wall')` so the
module is metric in both axes, or — better and cheaper — give the parapet the
**ashlar coping and dressed-block** treatment the rest of the bridge already
carries. A parish bridge parapet is dressed stone, not river cobble. One venue
file, one material key, one hero camera fixed.

*Why this is #1:* it is the largest area of unambiguously wrong pixels in the
build and it is in a mandated camera. Everything else on this list is smaller,
older, or both.

### 2. `spine-walk-01` is still under the bridge deck — fifth pass

**Frame:** `spine-walk-01`. 45 % of the frame is the unlit underside of the
bridge deck; the rest is three steps of flagstone.

The water wave fixed `t-bridge` with `standY = max(groundY, waterLevel)` and it
worked — `t-bridge` is now one of the twelve. The **walk** camera is a different
code path and was not fixed. The eye at (−4, −92) is inside the deck mass, not
under the water.

**Fix.** The walk camera must take its Y from the *rendered surface at that
point* — the same `_mesh_height` the water agent added — and then from authored
deck levels where a deck exists, not from `terrain.height()`. It is the same
one-function fix I asked for in pass 05 §2(a) and it is half done.

*Why:* it is the first frame a player crossing the Emberflow into Hearthmere
sees, and it has been broken in every review this project has run.

### 3. `westfront-free` — an unlit roof over open ground beside the hero venue

**Frame:** `westfront-free`. Eye 1.62 m at (38, −0.5) looking at the church west
front. The **upper 42 % of the frame is a brown, near-unlit roof soffit** with
no wall, no post and no structure anywhere in view, over grass and a low stone
wall. Unchanged from pass 05.

`t-report.json` reports it: `warehouse`/`townhouse` deep overlap **547.3 m³**
(`warehouse#2_n2_2` ∩ `townhouse#3_n2_8`) and `church`/`warehouse` **359.0 m³**
(`church#n1_0_6` ∩ `warehouse#2_n2_2`). 547 m³ is a room. A kit mass is sitting
through the town's hero venue and standing over its west door.

**Fix.** Resolve the two deep overlaps, or annotate them and give the harness a
gate that fails on any *geometry* overlap over ~50 m³ that is not annotated.
`town.mjs` currently reports these under `overlaps` and emits **zero warnings**.

### 4. The black lozenges are ground-lying leaf polygons with no albedo — not shadows

**Frames:** `craft-walk-04` (x≈400–900, y≈570–700, ~8 shapes in a line),
`craft-walk-02` (x≈380–900, y≈600–880, ~10 shapes scattered).

The foliage agent's three proofs — `--skip landscape`, replacing every leaf
card, `--skip` of the nine Bakers' Row venues — all failed to move them, and the
report concluded they are "not foliage". **The frames say something more
specific.** In `craft-walk-02` they lie on **fully sunlit paving**, outside any
shadow, each one a discrete dark arrowhead or lozenge 0.2–0.5 m across. A
shadow cannot exist on lit ground. They are **objects**: flat leaf-shaped
polygons lying on the road, rendered near-black.

Two mechanisms fit and one test separates them:

- **(a) A ground-scatter card whose material has no albedo bound** — the same
  class as `kirk-walk-05`'s black finials and `t-arrival`'s aisle void.
- **(b) A leaf/weed scatter card whose frame ended up face-DOWN.** The new
  three-axis card frames in `vegetation.leaf_cards` (`shell_face`, `droop`,
  roll) can produce a card whose normal points at the ground; single-sided, lit
  from above, it renders as an unlit silhouette. This would also explain why
  they arrived *this* wave in `craft-walk-02` where pass 05 had none.

**Test that separates them in one build:** clamp `ay·(0,1,0) > 0` on every card
frame in `core/vegetation.py leaf_cards()` and re-shoot `craft-walk-02`. If they
vanish, it is (b) and the fix is the clamp. If they survive, it is (a) and the
material is findable by dumping the material key of every primitive whose
bounding box is within 0.1 m of the paving in cell H7.

*Why this is #4:* it is on the ground in the two craft-lane frames I would
otherwise put on the two-second list, and it is the loudest "this is not a
shipped game" signal short of a missing texture.

### 5. The one masonry family landed too dark and too cool

**Frame:** `t-arrival`. Measured, pass 05 → pass 06: mean luminance
**116.1 → 82.6**, 10th percentile **53 → 32**, fraction below 24 **1.6 % →
3.3 %**. Five other frames measured over the same change are flat or brighter
(`t-square` 121.2→121.3, `t-gate-south` 105.8→107.8, `mere-walk-05`
109.0→108.6, `craft-walk-04` 80.7→82.4, `wharf-walk-06` 68.7→72.1). **The only
frame that went dark is the only frame that is 55 % close-range masonry.**

The family's own report gives the number: warmth spans **0.013** across seven
keys, down from 0.04. That is what cohesion cost. `core/materials.py:779`
`MASON_BODY = P.mix(P.FOUNDATION, P.CANVAS_CREAM, 0.24)`.

**Fix, and it is two constants.** (a) Raise the mix toward `CANVAS_CREAM` to
~0.38 so the body is limestone rather than granite. (b) Widen the family spread
back to ~0.04–0.05 of warmth so `ashlar` (church, civic), `sandstone` (gates)
and `rubble`/`cobble_wall` (quay, revetment) are recognisably different stones
from the same quarry district — which is what "one family" means. Cohesion is
not one colour.

Related and in the same fix: **the wall has no weathering.** `t-gate-south`'s
1,600 px of curtain is one value from end to end; `mereshore-free`'s mill is a
12 m grey slab; `mere-walk-03`'s left building is a blank ashlar plane over 40 %
of the frame. Add a low-frequency damp/soot/lichen gradient that rises from the
plinth and falls under the eaves — `masonry_colour()` already has `patina`,
`lichen` and `damp` terms and they are being applied at a strength that does not
survive to 12 m.

### 6. The enceinte's inner face is a chevron pleat — and it is the mesh

**Frames:** `craft-walk-04` (x≈620–1050 at 25 m, the wall closing the view),
`craft-walk-02`, `craft-walk-05`, `craft-walk-06`, `bailey-walk-02`,
`bailey-walk-03`, `bailey-walk-05`, `bailey-walk-06`, `t-approach-s` (x≈450–750
and 900–1080 at 130 m). Roughly eight frames.

The wall's inner face resolves into a dense regular **chevron/zigzag** that
reads as corrugated cardboard, and its top edge is a matching sawtooth. The
masonry agent proved it is not a mip problem: pixel-identical through a full
material rebuild *and* through the anisotropy change. It is geometry — the inner
face is being generated with an alternating or pleated profile.

**Fix.** This belongs to whoever owns `venues/wall.py`. Find where the inner
face's vertex ring is built and stop it alternating; the outer face does not do
this, so the two are built by different code paths and one of them is wrong.
Nobody owned this last wave and it is now in eight frames.

### 7. The emerald ground quilt — fifth pass, unchanged

**Frames:** `alley-walk-03` (bottom third, 5–6 hard-edged saturated emerald
polygons at 3–8 m, 90°/45° boundaries), `spine-walk-06` (a ~4 × 6 m emerald
rectangle at 3–8 m butting brown earth), `bailey-walk-04` (five green quads over
pale shingle at 3–6 m), `wharf-walk-06`, `sty-walk-03`, `t-gate-north` (the bank
top as a hard emerald ribbon), `mereshore-free`.

`venues/landscape.py _surface_patch` — `ragged` still drops **whole cells**.
Pass 03 asked for three things, pass 04 repeated them, pass 05 repeated them:
**feather the alpha over the outer 2–3 cells instead of a binary in/out; rotate
each patch's lattice by a per-patch seeded angle; desaturate `grass_lush` by
~25 %.** None of the three has been done in three passes.

The desaturation is the one that matters most. In `spine-walk-06` the grass
verge is still a more saturated colour than the crimson confectioner two
buildings away.

### 8. The water's three remaining defects, in value order

The water is 80 % fixed and I want that on the record. What is left:

- **(a) No reflection anywhere.** `t-bridge`: a three-arch stone bridge two
  metres above a still river reflects nothing. `t-approach-ne`: a 190 m walled
  town on the far bank reflects nothing into a mirror-flat lake. `t-gate-north`:
  the gatehouse reflects nothing. This is now **the single tell that stops every
  water frame**, and two of them are otherwise on the two-second list. The
  agent costed it honestly at 687 draws for a second scene pass at
  `gate-north`; the costed route in `review/reports/water.md` should be taken,
  but with a **reflection-only proxy set** (silhouette masses at LOD3, no props,
  no foliage, half resolution) rather than a full scene pass. A blurred,
  low-resolution reflection of the right *shapes* buys almost all of the effect.
- **(b) The diamond lattice in `t-approach-ne`'s near water** — bottom-right
  quadrant, x≈1050–1600, y≈600–870, a regular chequer of ~60 px alternating
  light/dark diamonds, ~12 % of the frame at 5–15 m. Also visible in
  `t-aerial-sw` at the eastern shallow margin (x≈980–1120, y≈180–230). The
  agent's remaining untested hypothesis — `_ring`'s deliberately alternating
  triangle diagonal showing through near-transparent water over a near-level
  bed — is almost certainly right, because the lattice appears **only where the
  water is shallow and the bed is flat**, which is exactly where a
  vertex-interpolated term differs most between the two diagonal choices. Test:
  build `_ring` with a consistent diagonal and re-shoot `approach-ne`.
- **(c) The `t-gate-north` bank** (§ "claims not supported"): a regular sawtooth
  of 3–4 m dark triangular facets with a hard emerald ribbon on top. Whatever
  built the shingle contour did not run here.

Also: the water's **hue is tropical**. `t-bridge` and `t-gate-north` are
Caribbean teal-turquoise; an English mill river over a silt bed at 09:30 is
olive-brown-green. `t-approach-ne`'s open lake is right and the shallows are
wrong; the `shallow.colour` `#B9A57E` is being over-applied or the deep tint is
too saturated toward cyan.

### 9. Foliage: the crown is fixed, the impostor and the close range are not

Credit first: `t-square`, `kirk-walk-05`, `t-approach-s` and `t-silhouette` all
show real trees now. That is a system fixed.

What is left:

- **The LOD3 impostor is confetti.** `t-aerial-sw` and `t-aerial-ne`: the woods
  ringing the town read as **scattered flat green paper scraps**, not canopies.
  `wharf-walk-08`: the far bank at 100 m is a continuous 1,600 px band of pale
  mint blobs blown to near-white over a hard white shoreline. The foliage agent
  handed off the cause and it is correct — **the `hedge` alpha channel is opaque
  over 99.9 % of its area** and `hedge` is the LOD3 impostor material for every
  tree in the build (`core/vegetation.py:786`). Fix the alpha and both defects
  go at once. This is the cheapest large win left in the build.
- **At 1.5–2 m the cards are die-cut leaves.** `kirk-walk-04` reads as a rubber
  plant; `t-bridge`'s frame-left tree is six flat pale leaves on a stick;
  `sty-walk-03`'s ivy is a green splodge on a quad. Sub-rect probability needs
  to rise steeply inside ~4 m so a near card is a *cluster*, never a single
  recognisable leaf.
- **Orphan sprigs.** `t-arrival` x≈990–1070 y≈280–420 — four leaf clusters
  hanging in the sky with no branch behind them.

### 10. Hedges are lit now and still extruded ribbons

**Frames:** `t-approach-w` (two ribbons, bottom 45 %), `t-approach-s` (four or
five, bottom 45 %, one dead through frame centre), `t-plan`, `t-aerial-sw`.

The transmission term landed and it matters — pass 05's "two pure unlit black
ribbons" is closed, and `SunRig._transmit` in `client/src/shadows.js` is the
right place for it given the harness does not import `ambient.js`. But they are
still **single lofted solids with a sinusoid top edge and a mottle painted on**,
and at 5–30 m they read as green foam. `core/vegetation.py:896 hedge_run()`'s
own docstring argues against instancing bushes; the docstring is wrong at this
range. A hedge needs a broken top line, gaps, gate posts and a ditch. Second
half of pass-05 §8, unchanged.

### 11. The correctness list that has not moved in three to five passes

Every one of these is a single object with a file, and every one is visible in a
frame I would otherwise be arguing about:

| defect | frame | passes unchanged |
| --- | --- | --- |
| `painted_crimson` on every timber of the confectioner | `kirk-walk-05` | 4 (`venues/confectioner.py:63`) |
| two pure-black finials on the churchyard piers | `kirk-walk-05` | 3 |
| untextured dark-brown box, dead centre, at the water gate | `wharf-walk-06` | 4 |
| a vermilion untextured bar | `wharf-walk-06`, `spine-walk-06` | 3 |
| a pole running the full height of frame centre | `wharf-walk-06` | 3 |
| the dovecote's cone floats clear of its drum, sky visible both sides | `alley-walk-03` | 2 |
| the quay is an empty municipal plaza — two rope coils, four bollards, no cargo, no boats | `wharf-walk-08` | 3 |
| `river_gravel` reads as polystyrene packing foam at 2 m | `bailey-walk-04` | 3 |
| thatch: knife eaves, straight ridge, no bundle, no thickness | `mere-walk-05` | 4 |
| washing is five perfect rectangles with straight hems | `sty-walk-03` | 3 |
| putlogs projecting into space carrying nothing | `bailey-walk-04` | 3 |
| no gate doors, no portcullis, flat inset heron plaque | `t-gate-north` | 3 |
| radial-and-concentric field spiderweb; pink-mauve fallow | `t-plan`, `t-aerial-sw` | 5 |
| no sun disc, no cloud, in 69 frames | all exteriors | 6 |
| `hm.slot.07.chophouse.door.01` unreachable | `check_walkable` | 6 |

**These are not hard.** They are one venue file each. They are also, cumulatively,
the reason six of the twelve two-second frames do not reach ten seconds.

### 12. Two new geometry defects the instruments cannot see

- **The 1.75 m figure floats.** `bailey-walk-04`, crop at
  `review/shots/ad-town-06/crop-bailey-feet.png`: the legs terminate ~0.5 m
  clear of the shingle with unoccluded gravel visible beneath them and the
  contact shadow displaced. The standing query and the rendered surface disagree
  on the graded shingle the water wave added. **This is a regression against
  pass 05's §13 FIXED**, and it is exactly the kind of thing that will make a
  player's own character skate.
- **The figure is buried in a wall.** `mereshore-free` x≈960–1000: the torso is
  inside the mill's stonework with only the arms outside.

Both are in the review harness's own scale reference, which means the harness is
lying about the thing it exists to measure.

### 13. Shaded vertical surfaces are crushed to near-black

**Frames:** `quaydeck-free` (70 % of the frame is a near-black plank wall in
shade), `sty-walk-03` (top-right roof soffit), `westfront-free`, `t-arrival`'s
aisle, `spine-walk-06`'s corbels, `craft-walk-02`'s jetty undersides.

At 09:30 with a bright sky dome, a north-facing plank wall is *blue*, not black.
There is no sky-colour ambient reaching vertical surfaces in shade. This costs
nothing in draws — it is a term in the ambient/IBL path — and it would lift six
frames at once. It is also half of why `t-arrival` reads gloomy.

### 14. Correctness, for the record

| instrument | pass 04 | pass 05 | **pass 06** |
| --- | --- | --- | --- |
| `validate.py` | 0 fail / 41 warn | 5 / 46 | **3 fail / 47 warn** |
| `check_walkable.mjs` | 15/15, 1 unreachable | 15/15, 1 unreachable | **15/15, 1 unreachable** |
| `check_client.mjs` | boots, not gated | FAIL 1,395 | **FAIL 1,398** (scene 544 + shadow 570 + AO 204 + post 80) |
| `town.mjs` → `t-report.json` | 1,416 | 1,031 (wrong) | **1,381 / 3,698,183 at `square`** |
| client ↔ harness parity | 0.7 % | 36 % | **1.5 %** |

- **The parity is the win.** `check_client` 1,398 vs `town.mjs` 1,378 at the
  same camera, gated at 3 % by `review/parity.json`. Both instruments now agree
  the build is 1.53× over the draw budget, and neither can be gamed by
  reordering the view list. That is the first honest budget number this project
  has produced.
- **Triangles got worse.** 3,698,183 at `square` against 3,500,000 — **5.7 %
  over**, up from pass 05's 2.6 %. The foliage rebuild is cost-negative on draws
  (121 vs 127 at `square`, measured by the agent) but the town as a whole gained
  ~107 k triangles.
- **`validate.py` 5 → 3 failures.** Mesh memory 243.3 → **233.4 MB**, now a
  warning not a failure. `nogging` cleared — and the honest finding there is
  that the *instrument* was wrong, not the asset. The three survivors are all
  one located cause: `core/mesh.py:1038 sheet()` maps UVs one tile per metre and
  never consults `resolve_uv`, so every cloth in the town ships at ~0.50× its
  authored coverage (`straw` 0.38×, `canvas_amber` 0.41×, `wool_crimson` 3.10×).
  The instruments agent found it and declined to land it blind because it
  rescales every cloth in the build. **That is the right call and this is the
  wave to take it**, because §(c)(iii) says the cloth needs rebuilding anyway.
- **The two geometry instruments still disagree about a countable fact.**
  `validate.py` reports **seven** sunk masses (gatehouse −2.59, moot_hall −2.03,
  props_situ −3.66, quay −4.55, townhouse −2.09, watermill −2.40, wellhouse
  −2.80); `t-report.json` reports **two**. Pass 05 measured 5 vs 2. The gap
  widened. Still none annotated.
- **`town.mjs` emits zero warnings** while a roof floats over the church west
  door, a 547 m³ mass sits inside the hero venue, the review's own scale figure
  floats half a metre, and the first frame of the spine is inside a bridge.
  Pass 05 said this gap was the largest thing between the build and an ACCEPT.
  It is now the *second* largest.

---

## Would any of these frames survive a blind side-by-side against a shipped AAA MMO?

Counting gameplay cameras only, judged from the 28 I read at full resolution.
Pass 04: three and zero. Pass 05: eight and one. **Pass 06: twelve survive two
seconds, and two survive ten.**

### Survives ten seconds — two frames

**1. `mere-walk-05`** (Mere Street west to the West Gate). Holds from pass 05 and
is *better*: the setts are crisper (the anisotropy fix), the plaster infill is
correct buff, the gate closes the view at 40 m with correct aerial perspective.
The only two things I can name in a minute are the **thatch** — still a cream
membrane with a knife edge — and the **empty sky**. Both are at the top of
frame, where the eye goes last.

**2. `t-gate-south`** (the south gate, looking north into the town). **New.**
Pass 05's regression is fully reversed: the cold blue-grey plate is gone, the
curtain and the gatehouse are one stone, the setts are correct, the figure is
planted with a contact shadow, and the glimpse through the arch has a street, a
tree and buildings in it. There is nothing *broken* in this frame — which is
exactly the ten-second test. What it lacks is dressing: the wall has no
weathering gradient over its whole 1,600 px run, the carriageway has no worn
channel, and the shrine box at frame right is under-detailed. Under-dressed is
not the same as wrong, and at ten seconds I would not know which game this is.

### Survives two seconds — twelve frames

1. **`mere-walk-05`** — as above.
2. **`t-gate-south`** — as above.
3. **`t-bridge`** — **new, and it is the largest single-frame improvement in
   this wave.** Pass 05 had daylight through all three arches, a black wedge and
   the camera under the river. It now has a river, a correct three-arch bridge in
   one stone, depth in the water and a gatehouse beyond. Fails at ten on the
   **absent reflection**, the tropical turquoise, a saturated emerald blob at the
   tower base and a plastic-houseplant tree at frame left.
4. **`t-approach-ne`** — **new.** The white plate is gone; there is a glitter
   path, a ripple field, real depth and a good town profile. Fails at ten on the
   **diamond lattice** in the bottom-right quadrant and the absent reflection.
5. **`t-square`** — holds. Correct setts, clean composition, worn diagonal, real
   residue, a real tree, **water in the fountain**. Fails at ten on the **black
   heron**, the flat-slab moot hall at 30 m and the crimson confectioner.
6. **`t-arrival`** — holds, on a different basis than pass 05: the masonry is now
   right and the light is now wrong. Fails at ten on the value drop, the
   aisle-arch black void and the orphan leaf sprigs.
7. **`mere-walk-03`** — **new.** Setts, kerbs, gutters, a cart, a gate closing the
   view. Fails at ten on the blank ashlar plane over 40 % of frame left.
8. **`craft-walk-01`** — **new.** Good timber frame, good junction, real depth.
   Fails at ten on the chevron enceinte closing the view.
9. **`craft-walk-04`** — holds, marginally. Excellent paving, timber frame with
   nogging, a working timber yard. Fails at ten — and nearly at two — on the
   **black lozenges** and the chevron enceinte.
10. **`t-approach-s`** — holds. The tree is back, the wall reads, the towers are
    roofed, and the hedges are lit rather than black. Fails at ten on the
    extruded sine-top hedges in the bottom 45 %.
11. **`fountain-free`** — holds and improves: the falling water now reads as
    water. Still the best-dressed frame in the project. Fails at ten on the
    12 %-of-frame flat emerald cloth panel and the black heron.
12. **`spine-walk-06`** — holds, marginally. The cyclopean ground floor is gone.
    Fails at ten — and nearly at two — on the **emerald quad** and the vermilion
    bar.

### What separates them, precisely

Every surviving frame is **paved in the new setts, built in the one masonry
family, and contains no exposed ground patch within 8 m, no cloth within 15 m,
no water reflection opportunity, and no ground-lying leaf polygon.**

**What the ten-second failures now are — and this is the whole answer to "how
far":**

- **Five of the ten** fail on **one object with a file and a line**: the heron,
  the emerald quad, the vermilion bar, the black void, the orphan sprig, the
  blank slab.
- **Two** fail on **the absent water reflection** — one system, one costed fix.
- **Two** fail on **the enceinte's chevron mesh** — one geometry bug.
- **One** fails on **the black lozenges** — one scatter, one clamp test.
- **None** fail on a masonry recipe. **None** fail on a leaf-card lattice.
  **None** fail on crazy paving. Those were the three systemic answers in passes
  03, 04 and 05 and they are all gone.

---

## What the next wave must do, ranked

1. **The bridge parapet** — dressed ashlar, or a metric UV. One venue file, one
   hero camera. §1
2. **The walk camera onto the rendered surface and authored deck levels** —
   closes `spine-walk-01`, fifth pass. §2
3. **Raise and re-spread `MASON_BODY`; make weathering survive to 12 m.** Two
   constants and a strength. Recovers `t-arrival`'s light and gives seven keys
   back their character without breaking the family. §5
4. **Sky-colour ambient on shaded vertical surfaces.** Zero draws, six frames.
   §13
5. **The `hedge` alpha channel.** One texture; it fixes both aerial impostor
   confetti and the 100 m tree wall in `wharf-walk-08`. §9
6. **The enceinte's inner face.** Eight frames, one mesh bug, nobody owns it. §6
7. **`_surface_patch`: feather the alpha, rotate the lattice, desaturate
   `grass_lush` 25 %.** Three numbers, a five-pass finding. §7
8. **Cloth: `core/mesh.py:1038 sheet()` through `resolve_uv`, plus sag, hem
   pinch and thickness.** Closes three `validate` failures and the last visible
   flat-plane system in one job. §(c)(iii), §14
9. **The reflection, as a low-resolution proxy pass** — LOD3 silhouettes only,
   half res, no props, no foliage. It is the last tell on two of the twelve. §8
10. **The `_ring` diagonal** — test and close the diamond lattice. §8(b)
11. **The lozenge clamp test** (`ay·(0,1,0) > 0`), then fix whichever it proves.
    §4
12. **The correctness table in §11, all fifteen rows.** These are one venue file
    each and they are worth more per hour than anything else on this list.
13. **Resolve or annotate the 547 m³ and 359 m³ overlaps; annotate the sunk
    masses; close `hm.slot.07.chophouse.door.01`.** §3, §14
14. **The draw budget: the depth-only merged proxy per batch group** the
    instruments agent costed at ≈ −375 draws with zero visual change. The shadow
    pass is 570 of 1,398 and it is depth-only; its 2.64 primitives-per-batch
    material split is pure waste. Spans `core/venue.py`, `client/src/lod.js`,
    `main.js` — one agent's whole job, as that report says.
15. **The sky.** Sun disc and cloud bank. Sixth pass. It is on all twelve
    surviving frames.
16. **The quay** — plank it, wear it, load it, moor a boat at it. It is the
    town's working waterfront and it is an empty plaza.
17. **One building at 18–19 m.** The tallest mass has not moved in three passes
    while the roofline rose; the profile has no intermediate step and the ratio
    is going the wrong way. This is the only item on the list that needs new
    geometry, and it needs exactly one. §(b)

---

## How far is this from an ACCEPT?

**Two waves — and I hold the number I gave last pass, which I did not expect
to.**

I said pass 05 that this wave decided it, and that the risk was recipe changes
landing in source and not in frame. **They landed in frame.** I checked the
masonry against a forced texture rebuild because I have caught stale sheets
before; I checked the leaf placement in the frame because I caught that exact
failure last pass; I checked the water camera by standing in it. All three hold.
Three pass-02 findings closed, nothing regressed outright, and the two systems
that stood between six frames and a ten-second survival are both gone.

**And here is the thing I want to say plainly, because the brief asks me not to
withhold it: this build is closer to ACCEPT than the length of this report
suggests.** Count the findings above by kind. **One** is a recipe (§5, and it is
two constants). **Two** are systems (the reflection, the cloth). **Everything
else is a single object, a single mesh bug, a single camera function, or a
single alpha channel** — and every one of them has a file, a frame and a line in
this document. There is no longer anything in Hearthmere where the answer is
"the surfaces are wrong". Pass 02 through pass 05 all had one. Pass 06 does not.

**Wave 2** — items 1–8. This is the wave that turns twelve frames at two seconds
into eight or nine at ten. Nothing on it needs a new asset, a new venue or a new
recipe family; item 3 is two constants, item 4 is one ambient term, item 5 is
one texture, items 1, 2 and 6 are one file each.

**Wave 3** — items 9–16 plus a full re-shoot with four instruments that agree
and a green budget gate. Correctness, the reflection, the draw budget, and the
last unticked box in §9.

**What would make me revise upward:** the correctness table in §11. Fifteen
single-object defects, several of them four to six passes old, in a project that
has now proved it can rebuild a material family, a scatter system and a water
shader in one wave. If wave 2 comes back having rebuilt three more systems and
still has a black finial on a churchyard pier and an untextured box at the water
gate, then the problem is not capability, it is that nobody is being given the
boring list — and the boring list is what stands between "survives two seconds"
and "survives ten" in six of the twelve.

**What makes me say two and not four:** for the first time in this project,
every agent's report told me something true that I could not see, and two of
them told me something true that contradicted *my own* pass-05 findings and were
right. The perf instrument diagnosis in `ad-town-05` §12 was wrong and
`instruments-06` disproved it with five probe runs and an 8-line fix. The
`cobble_wall` failure I attributed to a material was the mesh, and
`masonry-family` proved it through a full rebuild and an anisotropy change.
**A project whose agents can overrule its art director with evidence is a
project that is about to ship.**
