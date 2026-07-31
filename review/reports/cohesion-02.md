# Hearthmere — Whole-Town Cohesion Review 02

**Verdict:** `REVISE` (town layer) — up from `REJECT`
**Prior report:** `review/reports/cohesion-01.md`
**Renders assessed:** `review/shots/town-arrival.png` (20:59), `review/shots/streets/*`,
and every venue folder. Measurements taken directly from the shipped PNGs and the shipped
albedo textures in `assets/textures/`.

---

## Submission hygiene, first

`review/shots/town-square.png` is stale. Its HUD reads `14 venues, 55 entities`; the arrival
frame reads `15 venues, 61 entities`. It was rendered at 20:20, before the gate, before the
street layer, before the guild redesign, and before the lit-window pass. It was not
re-rendered in any of the three commits that followed. One of the two headline town frames I
was pointed at shows a build that no longer exists.

Also stale: `market_square/market_square-detail.png` (18:48), `market_square/sq_noground-gameplay.png`,
`cottage/cottage-detail.png` (14:36).

I judged the current state from the frames that are current. But this is the second review in
a row where a headline frame on disk did not match the build, and last time I said the arrival
shot should be re-rendered on every venue merge. That has not happened.

---

## First impression (before analysis)

Two seconds on the arrival frame: **"I am looking through a hole in a wall at a car park."**

There is a gate now, and that is a real change — the frame has a foreground and an aperture.
But my eye did not go into the town. It went to the giant beige blocks jutting out of the
piers on both sides, because they are the nearest, largest, highest-contrast objects in the
picture and they look like unfinished blockout geometry. The middle distance is a wide pale
grey nothing with a dotted line of stones down each side. There is a cluster of small striped
awnings at the end, which is the only place in the frame that has any colour or any life, and
it is small, dark, and 40 m away.

Second impression, walking the venue shots: the buildings have moved forward. The guild has a
real tower. The pub and inn have chimneys. The stalls are still excellent. But the *town*
between the buildings has been built as geometry and not as a picture — it is there in the
mesh and it is not there in the frame.

---

## Adjudication of the disputed claims

The builder disputed two of my findings. **On the palette, the builder is right and I was
wrong. On the lighting, I was wrong about the mechanism, and the underlying defect is real,
unfixed, and worse than I described.**

### Palette — I was wrong. Withdrawn.

Art Bible §4 is explicit: *"Hex values are linear-space authoring targets in sRGB notation.
All albedo maps stay within these families."* The lock is on the **albedo**, not on rendered
pixels. In cohesion-01 I k-means clustered *gameplay renders* and reported the cluster
centres as palette drift. That conflates albedo with lighting, exposure and ACES tone
mapping, and it is not a valid measurement against §4. The finding was methodologically
unsound and I should not have shipped it.

Measured correctly, against the authored albedo:

| Texture | Shipped mean | Locked | ΔE (CIELAB) | Verdict |
| --- | --- | --- | --- | --- |
| `plaster_albedo` | `#E6DBC5` | `#E8DCC4` | **1.2** | Compliant. Builder's number is exact. |
| `plaster_shade_albedo` | `#D0C2A9` | `#D4C4A8` | 1.9 | Compliant |
| `terracotta_albedo` | `#A95D3B` | `#B5603E` | **4.3** | Compliant |
| `ashlar_albedo` | `#ACA18E` | `#9A9083` (foundation) | 7.3 | Within tolerance |
| `stone_albedo` | `#847B70` | `#8A8578` (cobble) | 3.7 | Compliant |

`cohesion-01` claimed plaster ships ~20 units off its own primary and that terracotta ships
hot at `#BE673C`. Both claims are **withdrawn**. The albedo library is the most disciplined
part of this build, `core/palette.py` is a genuine single source of truth, and I mis-tested it.

Two of the five palette rows survive, corrected in scope:

- **Aged terracotta is present but under-weighted.** §4 asks for `#8F4E36` on ~30% of tiles.
  Measured: 12.8% of `terracotta_albedo` pixels sit within 20 RGB of the aged value; 74.6% sit
  on the primary. More importantly the whole texture spans only **13 luminance units**
  (p05=100, p50=109, p95=113). That is why every roof in town reads as one flat hue at
  distance, which is what I actually saw and mis-attributed to hue drift.
- **Thatch is still an undocumented off-palette roof material.** `thatch_albedo` = `#A58851`,
  nearest §4 entry is *oak* at ΔE 12.0. §4 lists two roof materials, terracotta and slate.
  `docs/DECISIONS.md` still has no entry (D-001…D-008 checked). This is unchanged from
  cohesion-01 and it is on the venue whose stated job is to make the place read as a town.

One drift I missed last time and should have caught: **`cobble_albedo` ships at the worn
value.** Mean `#756F62` is ΔE 2.9 from `COBBLE_WORN #6E6A60` and ΔE **37.2** from `COBBLE
#8A8578`. The entire town — every street, the square, and the 400 × 400 m ground plane — is
paved in the colour §4 reserves for *"traffic paths, gutters."* That is a genuine, measurable
reason the settlement reads dour, and it is one constant.

### Lighting — I was wrong about the mechanism. The defect is real and now systemic.

I claimed the client deviates from the review harness. **It does not.** The two rigs are
byte-identical, and the builder is right that the deviation cannot be reproduced:

```
client/src/main.js:85   HemisphereLight('#AFC9E0','#8A7352', 1.35)
tools/render/viewer.html:90  HemisphereLight('#AFC9E0','#8A7352', 1.35)
client/src/main.js:86 / viewer.html:93   AmbientLight('#6B5A46', 0.55)
client/src/main.js:88 / viewer.html:97   DirectionalLight('#C9A87E', 0.55)   // bounce
client/src/main.js:92 / viewer.html:102  DirectionalLight('#8FB8E8', 1.15)   // rim
```

`git log -L 85,105:tools/render/viewer.html` shows these values were introduced in the
foundation commit `ac718cf` and never changed. So my framing — *"`make shots` renders venues
at the §4 values, the client does not"* — was simply false. Withdrawn.

**The corrected finding is worse.** Both rigs deviate from Art Bible §4 on three of six
lighting entries and add two lights that do not exist in the Art Bible at all:

| §4 role | Locked | Shipped (both rigs) | Delta |
| --- | --- | --- | --- |
| Key (sun) | `#FFF2D8` @ 3.2 | `#FFF2D8` @ 3.2 | correct |
| Sun elevation / azimuth | 38° / 125° | 38° / 125° | correct |
| Sky fill (hemi top) | `#93BEE8` @ 1.1 | `#AFC9E0` @ 1.35 | desaturated, **+23% intensity** |
| Ground bounce (hemi bottom) | `#7A6A52` @ 1.1 | `#8A7352` @ 1.35 | **+23% intensity** |
| Rim / separation | `#8FB8E8` @ **1.4** | `#8FB8E8` @ **1.15** | **−18%** |
| — | *not in Art Bible* | `AmbientLight #6B5A46` @ 0.55 | undeclared |
| — | *not in Art Bible* | `DirectionalLight #C9A87E` @ 0.55 | undeclared |

Three consequences, all of which I can see in the renders:

1. **Art Bible §8 requires "Reviewed at the locked 09:30 lighting setup." That box has never
   been true for any asset in this repository.** Every venue that passed its individual review
   passed at non-spec lighting. This is not a client bug; it is baked into the review harness.
2. **The rim is the deliberate anime signature** — §1 calls it *"the single strongest anime-3D
   signature"* — and it is running at 82% of spec while 1.1 units of undeclared flat ambient
   and bounce wash over it. That combination is precisely why the whole build reads hazy and
   low-contrast, and why §1's "colour separation between planes" does not happen.
3. **`tools/render/viewer.html:26` declares `skyFill:'#93BEE8', groundBounce:'#7A6A52'` under
   a comment reading `Locked review setup, docs/ART_BIBLE.md §4` — and then never uses either
   value.** They are dead constants. Any grep-based or eyeball compliance check on that file
   passes. That is how this survived two reviews.
4. **`content/town/hearthmere.json` authors the correct rig** (`skyFill #93BEE8`,
   `groundBounce #7A6A52`, `rim #8FB8E8`) **and nothing reads it.** This is the identical
   failure mode as `streets[]`: correct data authored in the content layer with no consumer.
   The builder just fixed that pattern for streets. It is still live for lighting.

**Net adjudication: builder wins the palette outright, wins the mechanism on lighting, loses
the substance on lighting.** I have adjusted the Cohesion axis up for the palette and left
Lighting where it was.

---

## Prior ranked findings — resolved?

### 1. Ford Road does not exist — build the street layer — **PARTIAL**

`tools/assetgen/venues/streets.py` exists, reads `streets[]`, and builds ribbon carriageways,
kerbs, verge scatter and south waymarkers. As *code and data*, this is a clean, well-reasoned
module and it is the right shape. The `streets[]` block finally has a consumer.

**And the road is invisible in the render.** Measured cross-sections of `town-arrival.png`
across the full 7 m carriageway and 4 m either side of it:

```
y=430   ... 121 124 125 125 124 121 119 119 121 124 125 125 124 122 ...
y=455   ... 125 123 120 118 117 118 120 124 124 124 125 124 121 118 ...
y=480   ... 121 117 118 117 120 124 125 123 122 124 125 123 121 119 ...
```

Luminance varies by **±5 units** across road and verge alike. There is no value step at the
road edge, no darker centre trough, no material change. The road is not legible as a road.

The cause is in one line. `streets.py:35` maps Ford Road's `"surface": "cobble"` to material
`"cobble"` — and `viewer.html:109` / `main.js:205` texture **the entire 400 × 400 m ground
plane with `cobble_albedo` at the same 2 m tiling.** A cobble ribbon has been laid on a cobble
plane. The only thing distinguishing Ford Road from the field beside it is a dotted line of
kerbstones and a 7.5 cm dish that subtends well under a pixel at gameplay distance.

`streets/streets-approach.png` proves this on its own: with the buildings out of frame, the
road is a featureless plain with two dashed rows of stones on it.

Two knock-on problems from the same root:
- Hearthmere is a 300-person lake town **paved in cobblestone to the horizon**, including
  outside its own customs wall. In `streets-approach.png` the wall stands on cobble, and
  beyond it is more cobble to the skyline.
- `REFERENCES.md` anti-reference *"Flat ground. A texture plane under buildings kills an
  otherwise good shot"* is not addressed. It is now the same texture plane with kerbs on it.

**The fix is not more street geometry. It is to stop the ground being cobble.** Earth, mud,
grass and gravel outside the paved areas; then the paved road reads by contrast, for free,
everywhere in town, and D-006's honest note about paving reading flat at distance stops
mattering.

### 2. Unbury the four chimneys — **RESOLVED, with one exception**

- **Inn** — two stacks clearly above the ridge in `inn-approach.png`. Resolved.
- **Pub** — stack clearly above the ridge in `pub-approach.png`. Resolved.
- **Cottage** — stack present. Resolved.
- **Blacksmith** — a stack now exists where there was none, and it is a **stub**. In
  `blacksmith-approach.png` it breaks the ridge by roughly 0.3 m on a 6 m building. The venue's
  declared anchor silhouette in `WORLD_BIBLE.md` is *"forge chimney + open work yard."* §6
  requires secondary elements to read at 30 m. This does not read at 10 m. **NOT RESOLVED** as
  an anchor, even though the geometry now exists.
- **Shop row has no chimneys at all** — a 20.4 m terrace of three shops with living quarters
  above and a bald roofline. Not in the prior report; flagging now.

The **build-time occlusion tripwire** in `core/venue.py:87 check_occlusion()`, wired through
`build.py:109`, is the right engineering answer and is exactly the kind of thing that stops
this class of defect recurring. Credit where due — this is the best process artifact added
this pass.

Smoke is now visible in `town-arrival.png` (two faint plumes, top-centre). Working.

### 3. Build the north gate — **PARTIAL**

The gate exists: piers, quoins, voussoired arch, keystone with a heron, lamps, low customs
wall. Its presence is the single biggest reason this is `REVISE` and not `REJECT`.

It is also the worst-finished object in the build, and it is now in the foreground of the most
important frame in the project.

- **The arch is not in the arrival frame.** Crop the top 260 px of `town-arrival.png`: between
  the two piers there is only sky. The brief requires *"the gate arch framing the shot."* The
  shot is bounded by two piers, which is a slot, not a frame.
- **The quoins read as Lego.** `streets.py` builds each as
  `M.box(0.34×1.4, 0.40, 0.34×0.9, chamfer=0.016, "ashlar")` translated to
  `px + cx*PIER*0.5` — i.e. centred *on* the pier corner, so half of every quoin projects
  ~0.2 m proud of the wall face. Nine courses per corner, alternating long/short with **zero
  jitter** in size, position or rotation. §6 mandates ±3% position, ±2° rotation, ±4% scale on
  repeated elements and *"no element may appear more than 3 times in a row without a variant."*
  These are the nearest, largest objects in the arrival frame and they are perfectly repeated.
- **The voussoirs are not voussoirs.** Thirteen identical `M.box(0.62, 0.90, ...)` cuboids
  rotated around an arc. A voussoir is a wedge; identical boxes on a curve leave stepped gaps
  at the extrados, which is visible in `streets-gameplay.png`.
- **The two piers occupy ~46% of the arrival frame's width.** Nearly half the most important
  composition in the build is unchamfered, perfectly-repeating blockout masonry.
- **The customs wall is the documented crazy-paving anti-reference.** Seven segments of
  `M.box(1.9, 1.15, 0.55, "stone", uv_scale=0.6)`. `stone_albedo` is a large-cell Worley at
  ~0.25 m per cell at native 2 m tiling, stretched further by `uv_scale=0.6` to ~0.4 m. On a
  1.15 m wall that is two cells tall. `REFERENCES.md` names this exact defect —
  *"our first plaster crackled at ~30cm cells and read as crazy-paving stone"* — and it is now
  the material of the town boundary, the kerbs, the waymarkers and every building plinth.
- **Scale.** `WORLD_BIBLE.md` says the wall is *"more customs boundary than defence"* and the
  gate *"decorative in the way a prosperous trading town's gate is."* What shipped is 1.5 m
  square piers, 5.2 m high, with 0.4 m quoins. It reads as a fortification on a town that has
  never been besieged.

### 4a. Give the town a yaw — **NOT RESOLVED. Changed, not fixed.**

The entity records do now carry real quaternions — `content/entities/townsfolk.json` has 21
distinct non-identity rotations, derived in `townsfolk.py:77-90`. The data-layer complaint is
answered.

But the yaws are hand-authored constants that do not point at anything. Measured facing error
from each `talk` figure to its nearest neighbour:

| Figure | Nearest | Distance | Facing error |
| --- | --- | --- | --- |
| `hm.folk.00` | `hm.folk.01` | 1.25 m | **46°** |
| `hm.folk.05` | `hm.folk.06` (child) | 1.14 m | **150°** |
| `hm.folk.10` | `hm.folk.09` | 1.75 m | **86°** |
| `hm.folk.18` | `hm.folk.17` | 5.61 m | **122°** |

`townsfolk.py:31` comments the first pair *"pair mid-conversation."* They are looking 46° past
each other. `folk.05` is commented *"child with a parent"* and is standing with its **back** to
the child, 1.14 m away.

Cohesion-01 asked for *"talk pairs face each other and workers face their benches."* What
shipped is arbitrary yaw with comments asserting relationships the geometry does not support.
A rank of identical mannequins reads as unfinished; four people standing back-to-back at
conversational distance reads as **broken**. This is a regression in effect, if not in intent.
Derive facing from the target — the partner's position, the counter, the anvil — not from a
literal.

All 21 remain `schedule: "static_v0"`. The arrival brief requires *"NPCs moving."* Nothing
moves. Animals: one cat, one dog, unchanged.

### 4b. Lit windows and forge light — **NOT RESOLVED**

`glass_lit` exists, is applied in `inn.py`, `pub.py`, `shop_row.py`, `cottage.py`, and ships
with `emissiveFactor [1,1,1]` and a near-white emissive map (`glass_lit_emissive` mean
`#EFE5AE`). Numerically the panes emit.

**Visually, the fix converted every window from a black void into an opaque painted
rectangle.** In `inn-gameplay.png` a first-floor pane measures L=147–151 against a sunlit
plaster wall at L=169. There is no contrast, no warmth, no depth, no interior, no spill onto
the reveal or sill. Zoomed, the inn now reads as a plaster wall with picture frames nailed to
it. That is a worse read than a dark window, because it destroys the *glass* cue entirely.

The mechanism is wrong. §4 specifies **`Window interior spill #FFD9A0 at 2.2`** — a *light*,
not an emissive decal. At 09:30 under a 3.2 key, a cream emissive pane saturates to the same
value as sunlit plaster and does nothing. Lit windows read when the aperture is *darker* than
the sunlit facade with a warm concentrated core, plus actual spill on the reveal.

The same defect is on the shop row and is more damaging there: crop
`shop_row-approach.png` behind the fold-down counters and the "display windows" are **blank
cream plaster**. The shops have no interiors. `REFERENCES.md` anti-reference *"Empty rooms"* —
these are not even empty rooms, they are solid walls where an opening is drawn.

The forge is unchanged: in `blacksmith-gameplay.png` the coal bed glows and **nothing around
it is lit** — not the stone hood, not the anvil, not the posts, not the floor. §4 specifies
`Forge fire #FF8C42 @ 4.0, flickering`. There is no forge light in the scene, only an
emissive texture. The town's declared strongest light source still does no lighting work.

### 5. Re-lock the palette and kill the crazy-paving — **(a),(b) WITHDRAWN; (c) NOT RESOLVED**

(a) and (b) withdrawn — see adjudication above.

(c) stands and has got worse. Measured cell sizes at the shipped 2 m tiling:

| Texture | Cells across tile | Cell long axis | §3 spec | Used on |
| --- | --- | --- | --- | --- |
| `cobble` | ~14 fine | 0.14 m | 0.12–0.22 m | fine structure is **correct** |
| `cobble` | ~5–6 coarse | **0.33–0.40 m** | 0.12–0.22 m | dominant read; mips to crazy-paving |
| `stone` | ~8 | **0.25 m**, stretched to ~0.4 m by `uv_scale` | 0.12–0.22 m | customs wall, kerbs, all plinths, forge hood |
| `terracotta` | ~6 courses | **~0.33 m** exposure | 0.16 m | every roof in town |
| `ashlar` | ~3 | ~0.67 m | — | guild + gate |

The fine cobble layer is authored correctly; the coarse layer over it is 1.5–1.8× the §3
maximum and it is what survives mipping, which is exactly the shortfall D-007 records
honestly. Roof tile exposure is **2× spec**, which is why roofs read as corrugated sheet.

Correction to cohesion-01: I placed crazy-paving on the *cottage walls*. That was wrong — the
cottage wall panels are `plaster`, and they are good. The defect is on the cottage **plinth**,
the smithy floor, the square, and now the ground plane and customs wall.

### 6. Bring client lighting onto the §4 rig — **NOT RESOLVED** (see adjudication)

### 7. Chamfer the guild masonry, break the bond, open the doors, dress the interior — **PARTIAL**

- **Doors open.** Resolved. `guild-gameplay.png` shows both leaves open with a visible interior.
- **The pale wedge in the porch is gone.** Resolved.
- **The tower is real.** `guild-silhouette.png` now shows a square tower with crenellations, a
  spire and a finial reading clearly above the roofline. This was a "flat slab" last review and
  it is now the best silhouette in the town. Genuine fix.
- **The masonry is unchanged and it is still the worst material in the build.**
  `guild-detail.png` at ~1.5 m: `ashlar_albedo` is a perfectly regular running bond of
  identical rectangles, dead-flat faces, no mortar depth, no per-stone relief, no chamfer,
  no wear. §2: *"Nothing is perfectly straight or perfectly repeated."* §6: *"This is
  non-negotiable and is the first thing the art director check looks for."* Failing both, on
  the hero building, at hero distance, for a second consecutive review — **and the same
  material has now been propagated onto the north gate**, so the defect went from one building
  to the foreground of the arrival frame.
- **The interior is a grey box.** Brief: *"a stone hall, a reception counter, a big map on the
  wall, weapon racks, adventurers loitering."* Shipped: a dark room, a counter shape, a flat
  back wall. The three NPCs authored at the guild are outside on the porch.
- The threshold slab **is** properly chamfered and dished. Chamfer is available in the kit and
  is used correctly on some pieces. It is simply not applied to the ashlar or the quoins.

### 8. Break the shop row facade; differentiate the three shops — **PARTIAL**

Improved: three roof planes now differ in height and pitch (0.86 / 1.02 / 0.78), upper storey
heights differ (2.95 / 3.30 / 2.70), and framing styles differ (square / herringbone / close
studding). The roofline is no longer three identical gables.

Not resolved:
- The **ground-floor wall plane is continuous and coplanar for 20.4 m** with no recess, no
  projection, no material change. §7's 12 m limit is exceeded by 70%. A roofline step is not a
  facade break.
- **The three shops are still not their briefs.** Counters carry roughly six props between
  them. General store: no barrels, no sacks spilling onto the street. Apothecary: no hanging
  herbs, no bottles. Tailor: no cloth bolts, no dress form.
- **Hanging signs exist but do no work.** `K.hanging_sign(width=0.66, height=0.50,
  reach=0.90)` mounts them tight to the wall above the counter awnings, which occlude two of
  the three. They read as green postage stamps at gameplay distance. §7 wants vertical
  interest every 8–10 m along a street; this is the one place in town that has signage and it
  is invisible.

### 9. Replace the placeholder player capsule — **NOT RESOLVED**

Blue pill limbs, sphere head, still the largest, most central, highest-contrast object in the
arrival frame, standing 2 m from properly articulated townsfolk.

### 10. Reconcile `WORLD_BIBLE.md` with `hearthmere.json` — **RESOLVED**

`WORLD_BIBLE.md:105-113` now states the handedness explicitly and both documents agree. I
verified the build against the corrected brief by projecting venue origins into the arrival
camera: guild at x=−12.5 projects to screen x≈1260 (**right**), inn at x=+22 projects to
screen x≈342 (**left**). The frame matches the brief as now written. The builder's correction
is right and my prior note is answered.

---

## The arrival composition against its brief

`WORLD_BIBLE.md:106-108` requires seven things in one view.

| Required | Status | Note |
| --- | --- | --- |
| Gate arch framing the shot | **Partial** | Piers frame it; the arch is above the frame line. Two piers = a slot, not an arch. |
| Ford Road leading the eye | **No** | Built, measured invisible: ±5 L units across road and verge. Kerbstones only. |
| Fountain as focal point at centre | **No** | Centred, and still the darkest thing in the picture. |
| Guild tower rising on the RIGHT | **Yes** | Correct side per the corrected brief; tower reads. |
| Inn's roofline on the left | **Technically** | Correct side. It is the inn's blank gable end — zero windows, zero door on the face the player arrives at. Unchanged from cohesion-01. |
| Stall awnings adding colour | **Yes** | Cream/crimson striped awnings are visible and are the only saturated colour in the frame. Real gain. |
| NPCs moving | **No** | 21/21 `static_v0`. Two visible; the nearer one faces nothing. |

Measured on `town-arrival.png` (1600 × 900):

- **Frame mean luminance 125.4. Central mid-distance focal band mean 105.7.** The place the
  player must walk toward is **20 units darker than the average of the picture**, and the
  brightest pixel in the frame (228) is at (611, 316) — on a gable at the upper left, not in
  the focal band. `REFERENCES.md`: *"Shipped AAA scenes have deliberate light: a warm key, a
  cool fill, and **something bright at the end of the sightline**."* This composition still
  leads the eye away from its own destination. **Unchanged from cohesion-01.**
- **Mean saturation 0.227**, down from 0.239 last review, against a §1 target of "~15% above
  photoreal."
- Sky occupies 10.1% of the frame; the two gate piers occupy ~46% of its width.
- Exactly **one chimney** is visible above a roofline in the frame.

The stated failure condition — *"if the player does not immediately know where to walk, the
composition has failed"* — is marginally better than last review, because the awnings give the
eye a destination. But the road that is supposed to carry it there does not read, and the
fountain that is supposed to be the target is the darkest object in the picture.

---

## Density layering (§7)

Still one density, still low, and the unevenness is now sharper.

Prop entity counts: stalls 8, shop row 6, guild 5, pub 5, inn 4, blacksmith 3,
**market square 3**, cottage 1.

- **The market square is the town's living room and it has three entities in it.**
  `market_square-approach.png`: a fountain, a signpost, two bare trestle frames, two barrels,
  a stone bench, and pebble scatter across a 34 × 32 m plaza. The brief asks for spilled
  produce, a broken crate nobody has cleared, pigeons, a dog under a cart, chalk tallies on the
  fountain lip. None of it is there. **Unchanged from cohesion-01.**
- **The fountain basin is still a black void** and is the lowest-luminance object in its own
  venue render. The town's declared anchor is a hole.
- **Gate to square is still ~40 m of nothing**, now with kerbstones and verge grit. The verge
  scatter is the right instinct and is far too sparse to register — `int(ln*1.4)` items per
  segment, half of them 8–17 cm pebbles, on a 44 m road.
- **The stalls remain the only venue where a person has been.** Fish on wet boards, crates of
  produce, spilled tomatoes on the ground, a leaning cartwheel, a broom, a cat, chalk tallies
  on a slate. It is still the best work in the build and still the standard the others must
  meet.

This is not §7 density *layering* — quiet corners deliberately set against busy ones. It is
one finished venue and seven unfinished ones.

---

## Does it read as one settlement?

**Closer. Not yet.**

What now works: the palette is genuinely disciplined at the albedo level (I was wrong to say
otherwise), the shared kit is used everywhere, the gate and street lines give the town an
edge and a spine, rooflines have chimneys and smoke, and the guild tower gives the skyline a
landmark. Those are the ingredients of cohesion and they are present.

What still breaks it:

1. **Two masonry treatments that belong to different games.** The guild and the gate are a
   machine-perfect, unchamfered, perfectly-repeating ashlar bond. Everything else is
   hand-made-looking plaster and timber. §2 wants the guild to read as *imported* — but
   imported means different dressing and different form, not "modelled by a different studio
   to a different standard." Now that the same ashlar is on the gate, the defect frames the
   town rather than sitting inside it.
2. **The ground undoes the buildings.** Cobble to the horizon at the gutter value, with the
   crazy-paving `stone` material on every plinth, kerb and wall. The buildings sit on it rather
   than growing out of it, and the road it is supposed to distinguish is the same texture.
3. **Nothing has an interior.** The inn's windows are painted panes, the shops' display
   windows are plaster, the guild's hall is a grey box. A town whose every aperture is solid
   reads as a facade set.
4. **Thatch is still undocumented and still doesn't read as thatch** — a smooth olive sheet
   with a chamfered edge, no straw direction, no courses, no ridge, no sag. On the cottages,
   which are the "makes it a town" venue.

---

## Blind AAA comparison

Against Gridania, Divinity's Reach and Boralus — **a player still picks this out instantly,
though it now takes about two seconds rather than under one.**

The tells, in the order they land: the blue capsule protagonist; the two slabs of
unchamfered, perfectly-repeating blockout masonry occupying half the frame; a wide featureless
grey plain where a street should be; and a mid-distance that is darker than the frame average.
Divinity's Reach opens through an arch onto a plaza with density stacked in three depth
planes and light at the far end. This opens through a slot onto a car park with a dark lump in
the middle.

**Would people play this?** Not yet — but the reason has changed, and that is worth saying
precisely. Last review the answer was no because *nobody had built the town*. That is no longer
true: the town layer exists. The answer is now no because the town layer is built to blockout
standard while the buildings on it are built to a much higher one. That is a finishing
problem, not a conception problem, and it is a much better place to be.

---

## Scores

**Acceptance requires no axis < 7 and AAA comparison ≥ 8.**

| Axis | 01 | 02 | Note |
| --- | --- | --- | --- |
| Silhouette (town skyline) | 3 | **5** | Chimneys unburied on inn/pub/cottage; guild tower is real and reads. Blacksmith stack is a 0.3 m stub against its own declared anchor; shop row roofline bald; one chimney visible in the arrival frame. |
| Material truth | 4 | **4** | Plaster is genuinely good (correction from 01). Against that: Ford Road is the same material as the ground it sits on; the crazy-paving anti-reference is now the customs wall, every plinth and the ground plane; roof tile exposure 2× spec; thatch reads as painted plywood; every window is opaque. |
| Lighting response | 3 | **3** | Rig off-spec on 3 of 6 §4 entries plus 2 undeclared lights, in **both** renderers; §4 rig authored in `hearthmere.json` with no consumer; focal band 20 L below frame mean; forge emissive still lights nothing; rim at 82% of spec. |
| Detail hierarchy / density | 3 | **4** | Square still has 3 entities; shop counters near-bare; 40 m of nothing now has kerbs and sparse grit. Stalls still the only layered venue. |
| Wear & story | 4 | **4** | Guild threshold correctly dished. Road trough at 7.5 cm is sub-pixel; ground splash still not wired through export (D-005); no interrupted work outside the stalls. |
| Life & residue | 3 | **4** | Smoke works. Yaw exists but all four talk pairs face away from each other by 46–150°; 21/21 static; two animals in the whole town. |
| Cohesion (one culture) | 4 | **5** | Palette compliance conceded and credited. Held down by two masonry standards, undocumented thatch, cobble-to-the-horizon ground, and solid apertures everywhere. |
| Scale truth | 6 | **5** | Component scale still broadly right, but measured errors: roof exposure 0.33 m vs 0.16 m spec, coarse cobble 0.33–0.40 m vs 0.22 m max, and a fortress-scale gate on a town the World Bible says has never been besieged. |
| Sightlines & navigation | 2 | **4** | Real gains: gate aperture, road line, south waymarkers, correct left/right. Held down by an invisible carriageway, a 20.4 m unbroken facade, invisible hanging signs, and a focal point darker than the frame. |
| **AAA comparison** | 2 | **4** | No longer a greybox. Still identified instantly by four tells, three of which are in the gate the builder just added. |

Every axis below 7. AAA comparison at 4 against a bar of 8.

---

## Verdict

`REVISE` — town layer.

`REJECT` was scoped to composition-level failure: no ground, no streets, no gate, no arrival
composition. Three of those four now exist as real geometry consuming the authored data, and
the arrival frame has a foreground, a spine and a terminus. Per `REVIEW_PROTOCOL.md`, `REJECT`
means *"fundamentally wrong approach — rebuild, do not patch."* That is no longer the right
call. The remaining defects are specific, enumerable and mostly cheap. That is `REVISE`.

It is not close to `ACCEPT`, and the gap is almost entirely **finish quality on the town layer
itself** rather than anything conceptual.

Venue scoping unchanged from cohesion-01 except:
- **`REVISE` → still open:** guild (ashlar bond, chamfer, interior), blacksmith (stub chimney,
  forge lights nothing), shop row (20.4 m facade, empty briefs, solid display windows,
  invisible signs), market square (3 entities, black-void fountain), cottage (undocumented
  thatch that does not read as thatch), inn and pub (opaque window panes).
- **`REVISE` → newly added:** streets/gate. The module is well-built and the output is not
  finished to the standard of the buildings around it.
- **Hold — stalls.** Still the reference. Do not touch.

---

## Remaining blockers, ranked by impact per unit of effort

1. **Stop the ground being cobble.** One texture swap on `viewer.html:109` and
   `main.js:205` — earth/grass/gravel outside the paved areas — and Ford Road becomes visible
   everywhere in town at once, the "flat ground" anti-reference dies, the customs wall stops
   standing on a paved field, and the 52% of the arrival frame that is currently dead grey
   starts doing compositional work. The street geometry is already built and correct; it is
   being camouflaged by the plane it sits on. **Highest ratio in this review by a wide margin.**

2. **Finish the gate to the standard of the buildings.** Chamfer the ashlar per §6 (15 mm),
   set the quoins **flush** with the pier faces instead of centred on the corner, add the §6
   mandatory jitter (±3% position, ±2° rotation, ±4% scale) so nine identical courses stop
   reading as Lego, taper the voussoirs into actual wedges, drop the pier section and height so
   it reads as a customs arch rather than a fortification, and lower the camera pitch or the
   arch springing so **the arch is in the arrival frame.** Nearly half the width of the most
   important composition in the project is currently blockout geometry.

3. **Make the light do the work the §4 table already specifies.** Bring both rigs onto the
   locked values — `#93BEE8`/`#7A6A52` @ 1.1, rim @ **1.4**, delete the undeclared
   `#6B5A46` ambient and `#C9A87E` bounce — and read them from `hearthmere.json.lighting`
   rather than hardcoding, so the authored block finally has a consumer and the two rigs cannot
   drift again. Delete the dead `C.skyFill`/`C.groundBounce` constants at `viewer.html:26`;
   they are actively misleading. Then put a real `#FFD9A0 @ 2.2` spill behind the inn's windows
   and a real `#FF8C42 @ 4.0` at the forge, instead of emissive decals. This is the single
   change that most affects how the whole town reads, and it fixes the §8 "reviewed at locked
   lighting" box that is currently false for every asset in the repo.

4. **Make the focal point the brightest thing in the mid-distance.** The fountain is the
   declared anchor and it measures as the darkest object in both the arrival frame and its own
   venue render. Give the basin water an actual surface with sky reflection, put the sun on the
   heron spout, lift the stone value, and dress the square to its brief — spilled produce, a
   broken crate, pigeons, a dog, chalk tallies. Three entities is not a town square.

5. **Derive NPC facing from targets, not literals.** `townsfolk.py:31-67` hand-authors 21
   yaw constants; four talk pairs are 46–150° off their partners and one adult has its back to
   the child it is captioned as accompanying. Compute `atan2` to the partner / counter / anvil,
   keep the ±0.10 rad jitter, and give at least the square a walk cycle so `static_v0` stops
   being literally true of every person in the world.

**Also required before re-review, lower ratio but non-negotiable:**

6. Chamfer and break the guild's ashlar bond (§2, §6) — second review running, hero building,
   hero distance — and dress the interior the brief specifies.
7. Give the shops interiors and their briefed goods; break the 20.4 m wall plane with a recess
   or projection, not just a roofline step; move the hanging signs clear of the awnings.
8. Halve the terracotta tile exposure to the §3 0.16 m, and raise aged-tile coverage from
   12.8% toward the specified 30% with real value spread — the current 13-unit luminance range
   is why every roof reads as one sheet.
9. Either bring the cottage roofs onto the §4 palette or record thatch in `docs/DECISIONS.md`
   — and either way, rebuild the material so it reads as straw: direction, courses, a ridge, sag.
10. Replace the placeholder player capsule.
11. Add the blacksmith a real stack — its brief calls the forge chimney the venue's anchor
    silhouette and it currently clears the ridge by 0.3 m.

---

## Re-review criteria

I will re-review when the arrival frame, re-shot from the client at the corrected §4 rig,
shows: a road that is visibly a different surface from the ground beside it; the gate arch
inside the frame with chamfered, jittered masonry; a fountain that is the **brightest** thing
in the mid-distance; at least three chimneys above the roofline; windows that read as
apertures rather than painted panels; and talk pairs facing each other. That is the bar for a
second `REVISE`-to-`ACCEPT` attempt.

---

## What is working — preserve this

1. **The palette discipline, which I wrongly attacked last review.** `core/palette.py` is a
   real single source of truth and the albedo library measures compliant: plaster ΔE 1.2,
   terracotta ΔE 4.3, plaster-shade ΔE 1.9. The plaster material specifically — soft broad
   mottling, fine hairline cracking, correct value — is the best surface in the build and
   should be the model for how the stone materials get rebuilt.
2. **The occlusion tripwire.** `core/venue.py:check_occlusion()` wired through `build.py` is
   the right answer to the buried-chimney class of defect and it caught the inn's second
   regression before I did. More of this.
3. **`streets.py` as a module.** It reads the authored layout, invents nothing, and is
   readable. The road is invisible because of the ground texture, not because the module is
   wrong. Do not rewrite it.
4. **The guild silhouette.** Tower, crenellations, spire, finial — it went from a flat slab to
   the best silhouette in the town in one pass.
5. **The stalls.** Unchanged and still the best work here. Fish on wet boards, spilled
   tomatoes, the cat, the chalk slate that solves §2's no-lettering rule correctly.
6. **The inn's massing and its shutters.** Three storeys, double jetty, dormers, correct
   plinth, and green planked shutters with visible grain and nail heads. It needs light and
   glass, not a rebuild.
7. **The handedness correction.** The builder found and fixed a real left/right error in the
   most important frame's brief, and documented the reasoning in `WORLD_BIBLE.md`. Verified
   correct by projection.
