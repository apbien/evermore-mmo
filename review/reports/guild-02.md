# Adventurer's Guild — Review 2

**Verdict:** REVISE (was REJECT)
**Renders:** `review/shots/guild/guild-approach.png`, `guild-gameplay.png`,
`guild-detail.png`, `guild-silhouette.png`
**Context:** `review/shots/town-arrival.png`
**Reviewed against:** `review/reports/guild-01.md`

---

## First impression (before analysis)

It is a building now. That is a real change — last time it was a massing study
with props leaned against it. The tower has a tube with a pointed hat on the
front corner and my eye goes there, which is more than the old slab ever earned.

Second beat, about a second later: the hat's tube is a *different colour from
the tower it is attached to* — pale cold grey against warm stone — and the big
identity banner is a stack of red horizontal bars with white gaps. It reads as a
striped awning nailed to a castle. Those were the two things I looked at first
and both are wrong.

Third beat, at the door: the doorway is genuinely open and there is a dark room
behind it. Good. It is an empty dark room with no light in it.

---

## Blind AAA comparison

Against **WoW / Boralus** (silhouette clarity, palette discipline).

The gap has narrowed from "amateur at 60 m" to "amateur at 25 m." The turret and
the hall chimney do work Boralus would recognise — a second mass, round against
square, stepping the outline twice. That is the correct instinct and it was
executed.

It still loses, on four things a player registers without naming:

1. **The banner.** Boralus's hanging cloth is cloth. This is twelve red bars.
2. **The tower has no windows.** A 15.5 m stone tower with a blank front face
   below a banner is a chimney stack, not a tower. Boralus never does this.
3. **The turret is the wrong material.** Measured saturation 0.097 against the
   ashlar's 0.253. It reads as rendered concrete bolted to dressed stone.
4. **The roof is a single sheet of orange.** Measured LF stdev 4.55 on a clean
   sunlit patch. Boralus's roofs carry per-tile colour break-up; this carries
   none.

**Would people play this?** They would now walk *toward* it, which is the change
from review 1. They would still not believe it shipped.

---

## Scores

| Axis | R1 | R2 | Note |
| --- | --- | --- | --- |
| Silhouette | 3 | **5** | Turret + cone + finial + chimney genuinely break the outline. Merlons still 0.62 m; the entrance bay's gable ridge runs the wrong way so it adds a horizontal band, not a triangle. |
| Material truth | 4 | **4** | Ashlar surface response unchanged (HF 5.28 vs 5.31). Turret and porch reveals read as concrete. Banner reads as striped awning. Bedroll still awning canvas. Parchment is the one real gain. |
| Lighting response | 4 | **5** | Rim separation now +16 to +23 lum (was +6.8). Interior reads dark. But roof LF 4.55, ashlar HF 5.28, and there is no emissive anywhere on the town's anchor building. |
| Detail hierarchy | 3 | **6** | A secondary tier now exists. It is thin, and the bay merges with the main roof instead of reading against it. |
| Wear & story | 3 | **3** | Nothing changed. Threshold still a plain box, still commented "dished by decades of boots." No splash band, no string-course streaking. |
| Life & residue | 4 | **5** | The quest board now reads as a quest board — the single best change in this pass. Interior is an empty unlit box; bedroll is market awning. |
| Cohesion | 5 | **4** | Regression. The grey turret and grey reveals break the "imported dressed stone" story the concept depends on. The bedroll still ties the guild to the market stalls. |
| Scale truth | 6 | **6** | Unchanged. Merlon proportion still wrong. |
| AAA comparison | 2 | **4** | Real movement. Still picked out at the gameplay camera. |

**Acceptance requires no axis < 7 and AAA ≥ 8. Six axes block.**

Verdict is REVISE, not REJECT: the composition is no longer fundamentally wrong.
Everything below is patchable without a rebuild.

---

## Status of every defect enumerated in guild-01

### 1. The doorway is not a doorway — sealed stone box → **RESOLVED**

`guild.py:179-197` builds the front elevation in segments around a real
3.4 × 3.30 m aperture. `guild.py:203-207` adds an inverted interior shell.
Measured interior back wall: mean luminance **23.6** — properly dark, no sky
flood. The reception counter at `guild.py:483` is now visible through the
opening in `guild-gameplay.png`. This is the largest genuine fix in the pass.

**Still open as a sub-item:** review 1 also asked for *"a warm emissive patch
(`#FFD9A0`, the palette's Window interior spill) so the opening reads as a lit
hall rather than a hole."* Not done. The guild received none of the `glass_lit`
work that went to the inn/pub/cottages. The World Bible brief — *"a stone hall,
a reception counter, a big map on the wall, weapon racks, adventurers
loitering"* — now delivers 1 of 5, up from 0. Right now the hero building's
front door opens onto an unlit empty box, which trips the *Empty rooms*
anti-reference in `docs/REFERENCES.md`.

### 2. Silhouette has no secondary tier → **PARTIAL**

Added and working: octagonal stair turret on the front corner (`guild.py:325`),
conical cap and iron finial (`330-335`), hall chimney (`387`). These are real and
they read. The skyline profile now has 8 steps over 15 px where before it had
essentially three edges.

Not fixed, all explicitly enumerated last time:

- **Merlons are still 0.62 m.** `guild.py:292`: `M.box(per / n_m * 0.9, 0.62,
  0.34, ...)`. Measured off the render at 35.6 px/m: **0.59 m**. Review 1 said
  period merlons run 1.2–1.8 m and that at this proportion they read as toy
  battlement. The code comment at `guild.py:313` now *quotes* the diagnosis
  ("half-height merlons as the only break in the outline") and the number was
  left alone. They are also only 0.34 m thick, so they read as plates.
- **The entrance bay's gable faces the wrong way.** `guild.py:357-359` calls
  `gable_roof(BAY_D + 0.9, BAY_W + 0.5, ...)` then `rotate_y(π/2)`, which puts
  the **ridge parallel to the facade**. From the approach — the only view that
  matters for this element — the bay contributes a horizontal orange band tucked
  under the main roof at nearly the same height and the same colour. It does not
  break the outline at all. `bay_gable` (`362-364`) is rotated the same way, so
  the gable end faces ±X where nothing sees it. **Fix: drop the `rotate_y`.** A
  cross-gable presenting a triangle to the street is the whole point of the
  element and it is one line away.
- **The buttresses cannot be judged.** `guild.py:369-383` puts them on the ±X
  flanks. Every submitted render is frontal or near-frontal. Supply a 3/4 view
  at the approach distance or they are unreviewable.
- **The banners still do not break the outline** — all flush to their wall face.
- **The tower/hall junction is still a bare butt joint** — no valley, no
  flashing, no weathering course.

### 3. Ashlar has no surface → **NOT RESOLVED**

Re-measured, clean sunlit wall, same method as review 1:

| Surface | Camera | R1 HF stdev | R2 HF stdev |
| --- | --- | --- | --- |
| Guild ashlar | detail (~1.5 m) | 5.31 | **5.28** |
| Guild ashlar | gameplay (3.5 m) | 6.96 | **6.86** |
| Inn plaster | same rig | 38.41 | 17.83 |

Unchanged within noise. Confirmed at source: `git log -S 'def ashlar'` returns
`c09ddb3` — the original guild commit. **`ashlar()` has not been touched since
review 1.** The target was HF 15–25 at the gameplay camera. The wall is still a
flat gradient with a line grid drawn on it.

Joint lines do now register (max horizontal luminance step 29.8 across a course
boundary), so the coursing reads — but there is no surface *between* the joints.

### 4. The banner is a quilt of 72 boxes → **NOT RESOLVED**

`guild.py:132-147` is byte-identical. Still a 12 × 6 grid of separate boxes at
1.06 × 1.35 overlap, still `chamfer=0.0` on every panel — 72 panels × 4 banners
= 288 unchamfered boxes, a direct violation of hard constraint 5 and Art Bible §6.

The code comment at `guild.py:139-141` still asserts the overlap solves the
striping. It does not. Zoom `guild-approach.png` at the tower and you count
thirteen hard horizontal bands with offset vertical seams. Measured across the
banner: HF stdev 20.8 with a regular vertical period — this is banding, not
cloth. Review 1 called this "a red brick wall hanging on a beige brick wall";
at this render it has tipped over into reading as **market-stall awning**, which
is worse, because it now visually matches the striped canvas the quest board was
just rescued from.

Fix is unchanged: one continuous chamfered subdivided quad, catenary bow and wind
lift carried as vertex displacement. The `banner_cloth` material is fine.

### 5. Quest board candy-striped → **PARTIAL**

**Resolved:** `parchment` (`materials.py:678`) and `sealing_wax` (`:716`) exist and
are registered. `guild.py:96` notices → `"parchment"`, `guild.py:111` seals →
`"wax"`. In `guild-gameplay.png` the board now reads as pinned paper with red
seals. The composition logic review 1 praised now survives into the render. This
is the cheapest large win in the pass and it landed.

**Not resolved:** `guild.py:468` — the bedroll — still requests `"canvas"`:

```python
roll = M.lathe([(0.13, 0), (0.14, 0.62)], 10, "canvas")
```

Review 1 named this exact callsite. In `guild-detail.png` there is a
red-and-white candy-striped bolster sitting by the threshold. It is the most
saturated object at the entrance and it reads as a rolled-up market awning.
Point it at `cloth_cream` or `linen`.

Low-priority follow-on: the notices are pale-on-pale against the ashlar and lose
contrast entirely by the approach distance. Consider darkening the board backing.

### 6. Tower lancet windows buried inside the wall → **NOT RESOLVED**

`guild.py:304-309` is unchanged:

```python
sl = M.box(0.42, 1.55, 0.16, 0.012, "glass")
sl.translate(tx, y, tz + szz * (TOWER_W * 0.5 - 0.20))
```

Glass at ±2.40 spanning ±2.32…±2.48. Tower wall boxes (`guild.py:272-273`) at
±2.35 with depth 0.5, spanning ±2.10…±2.60. **The slits are still entirely
inside the wall thickness.** The tower's front face renders as blank ashlar below
the banner, exactly as in review 1. No reveal, no jamb, no cill, no dark backing.

This one has an extra sting. The new occlusion tripwire (`core/venue.py:87`)
names this bug in its own docstring as one of the three instances that motivated
it — *"the guild's tower lancets sat inside walls spanning past them"* — but the
check is opt-in via `label=`, and `guild.py:309` emits the lancets with a bare
`ctx.emit(sl)`. **The tripwire does not cover the case it was written for.**
Label them, and label the turret slits too.

### 7. Entrance banners collide with the quest board → **RESOLVED**

Flanking banners moved to x = ±2.65 on the bay face (`guild.py:417-422`); the
quest board sits at x = −4.25. No overlap in plan, and no clipping visible in
`guild-gameplay.png`.

### 8. No ground contact, no wear logic → **NOT RESOLVED**

Nothing changed.

- `guild.py:246-249`: threshold is still `M.box(PORCH_W - 0.6, 0.14, 1.0, 0.03,
  "ashlar")`. The comment above it still reads *"Threshold, dished by decades of
  boots."* Nothing is dished. Review 1 quoted this comment verbatim.
- Plinth-to-cobble junction: measured luminance down the plinth face runs
  164 → 152 over the visible height, which is shading falloff, not dirt. No
  splash band, no debris, no darkening.
- String course: still a continuous drip ledge with not one streak below it.
- Zero traffic wear at the doorway.

`lime_plaster()` still takes the `wall_height` parameter that exists for exactly
this. The pattern to copy is still sitting in the core, unused by `ashlar()`.

### 9. No rim separation on the hero silhouette → **PARTIAL**

Measured at the tower's sunlit edge against sky, first 6 px vs interior wall:

| y | delta |
| --- | --- |
| 250 | +23.2 |
| 450 | +16.4 |
| 550 | +22.1 |

Review 1 measured +6.8 (antialiasing noise). There is now real separation, and it
comes from the quoin ladder giving the rim something to catch — the right
mechanism. But part (a) was not done: `viewer.html:102` still sets rim intensity
**1.15** against the palette's specified **1.4**.

### 10. Code hygiene → **NOT RESOLVED**

`guild.py:426` still reads:

```python
overhang=0.55, tile_mat="slate" if False else "terracotta")
```

---

## New defects introduced or newly visible

### N1. The turret and the porch reveals render as concrete, not stone

Both are emitted with `mat="ashlar"` (`guild.py:327`, `guild.py:231`), and both
render as a cold desaturated grey that does not match the wall two metres away:

| Surface | Mean lum | Saturation |
| --- | --- | --- |
| Ashlar wall, sunlit | 146 | **0.253** |
| Turret shaft | 114 | **0.097** |
| Turret cap slab | 112 | **0.088** |
| Porch reveal (shade) | 115 | **0.087** |

Two different causes, both worth fixing in core:

- **The turret is an `M.lathe`.** So is the inn's barrel, which review 1 flagged
  as reading like a galvanised tank at saturation 0.04 — it still measures 0.10.
  Two lathes in two venues both losing their material's warmth is a **core UV /
  texel-density problem on `M.lathe`**, not two coincidences. Fix it there and
  both venues benefit.
- **The porch reveals go cold in shade.** The rig's cool hemisphere
  (`viewer.html:90`, intensity 1.35) is overpowering the warm bounce
  (`viewer.html:97`, 0.55) on shadow-side faces. Every recessed surface in the
  town will do this. Either raise the bounce or give shadowed ashlar a warmer
  ambient response.

This is now the guild's worst cohesion problem, because the entire concept —
"imported dressed stone, outside money, not from here" — depends on one
recognisable material.

### N2. The conical cap reads as a chess piece

`guild.py:330-331` builds an ogee profile (1.22 → 0.92 → 0.42 → 0.0) that bulges
before it tapers, sitting on an octagonal collar (`guild.py:326`, radius 1.22)
that oversails the 1.05 shaft by 17 cm and renders as a pale disc. The result is
a mushroom: wide pale plate, bulbous dark-red bulb, spike. A period spire is a
straight or slightly concave cone springing directly off a corbel course.
Straighten the profile and either thicken the collar into a proper corbel with
courses or delete it.

### N3. The hall and bay roofs are single sheets

Not scored in review 1, and now a large part of the elevation. Clean sunlit
patch, `guild-approach.png`: **HF stdev 4.50, LF stdev 4.55.** Zero per-tile
colour break-up against Art Bible §4's required *~30% of tiles* in
`TERRACOTTA_AGED #8F4E36`. The hue is palette-compliant; the uniformity is not,
and it fails §8's *"no flat/uniform channels."*

Root cause is `core/kit.py:196-214` — each course is one slab spanning the full
roof depth. **`kit.py` has not been modified since `c20b6de`**, so this is the
same unfixed defect as inn-01 #4. Fixing it in core fixes both venues and every
roof in Hearthmere.

Also, `kit.py:217-220` builds a `ridge` lathe, rotates and scales it, and never
adds it to the group. Five lines of dead geometry.

### N4. The hall chimney reads as a fence post

`guild.py:387-388`, section 0.78 m on a 14 m-wide hall. It clears the ridge
(good) but at this proportion it registers as a post. Widen it, and give it a
flaunching collar where it penetrates the roof.

---

## Review-rig defects (not venue defects, but they block judgement)

1. **The silhouette render is unusable.** `viewer.html:288-290` applies
   `scene.overrideMaterial = MeshBasicMaterial(black)` to the whole scene,
   including the ground plane. In `guild-silhouette.png`, **404 of 900 rows
   (45%) are solid black ground**, so everything below eaves level is swallowed.
   The Art Bible §6 black-on-white test cannot be run on this image. Hide the
   ground (`ground.visible = false`) during the silhouette pass.
2. **The ground is fixed at the gameplay camera and still flat at the approach
   camera.** The rig now uses the real cobble material (`viewer.html:110-119`) —
   measured HF 16.5 at the gameplay camera, a genuine fix. But at the approach
   camera the 2 m tile mips down to nothing: **HF 1.09**. Both approach renders
   are still being judged over a featureless plane. Raise anisotropy, or use a
   larger-scale ground albedo variation that survives mipping.
3. **The scale figure is not at the building.** In `guild-approach.png` the
   1.75 m reference stands well forward of the facade and reads roughly 3.8 m
   tall against it. It cannot be used for the check CLAUDE.md requires it for.
4. **Renders are stale relative to the assets.** All four guild shots are dated
   20:51; `assets/meshes/guild.gltf` was last written 21:04:51. The guild's glTF
   happens to be byte-identical to HEAD so these renders are valid *this time* —
   but see the inn report, where the same process failure invalidated the
   headline fix. Re-render after every `make assets`, without exception.

---

## What is working

Preserve these.

- **The doorway and the interior shell.** The single most valuable change in the
  pass. The porch now has real depth, the counter is visible, and the opening
  reads as a way in rather than a decal. Do not touch the geometry — just put a
  light in there.
- **The turret as a *concept*.** Round against square, clasping the front corner,
  rising past the parapet so the outline steps twice — that is exactly the right
  answer to the review-1 massing note, and it is placed on the correct corner.
  The material and the cap profile are wrong; the idea is right. Keep it.
- **The `parchment` and `wax` materials, and the repointed quest board.** The
  board now delivers what its composition logic always promised. `parchment()` is
  well-authored and should be the reference for any future paper/cloth material.
- **The occlusion tripwire** (`core/venue.py:87`). The reasoning in the docstring
  is correct — an untargeted AABB sweep would be noise, opt-in labelling is the
  right call, and the honesty about two failed attempts is exactly what this kind
  of check needs. It caught the inn chimneys. Extend the labels to cover the
  lancets and it earns its place permanently.
- **Rim separation via the quoin ladder.** +6.8 → +20 without adding a light. The
  diagnosis in review 1 ("a directional back-light cannot produce a rim on a flat
  box") was acted on with geometry, which was the right lever.
- Everything review 1 listed as working still is: the quoin generator, the quest
  board composition, the weapon rack's missing weapon, the pack by the threshold,
  the `ashlar`/`banner_cloth` material authoring.

---

## Required before resubmission — ranked by impact on the AAA score

1. **Rebuild the banner as one continuous displaced surface.** It is the largest
   saturated element on the building, it is the guild's identity, and it
   currently reads as market awning. Highest single AAA cost. (Defect 4)
2. **Un-bury the tower lancets** and give them reveals and dark backing. A blank
   15.5 m tower is the second thing that gives the building away. (Defect 6)
3. **Fix `M.lathe` material mapping in core** so the turret reads as the stone it
   is made of. Also fixes the inn's barrel. (New N1)
4. **Raise ashlar surface response** to HF 15–25 at the gameplay camera, and add
   the ground-splash and string-course streaking via the `wall_height` mechanism
   already in `lime_plaster()`. (Defects 3 and 8)
5. **Per-tile roofs in `core/kit.py`** with ~30% aged variant and §6 jitter.
   Fixes the guild and the inn in one change. (New N3)
6. **Drop the `rotate_y` on the bay roof** so the entrance gable faces the street,
   and take the merlons to 1.2–1.8 m. Two small edits, real silhouette return.
   (Defect 2)
7. **Warm emissive in the guild interior**, plus at least a wall map or a rack so
   it is not an empty box. (Defect 1 sub-item)
8. Repoint the bedroll off `"canvas"`. (Defect 5)
9. Dish the threshold with real geometry. (Defect 8)
10. Straighten the cone profile; widen the hall chimney. (New N2, N4)
11. Delete `tile_mat="slate" if False else "terracotta"`. (Defect 10)
12. Rig: hide the ground in the silhouette pass; raise rim to 1.4; place the scale
    figure at the facade; fix approach-camera ground mipping; supply a 3/4 view
    that shows the hall flanks.
