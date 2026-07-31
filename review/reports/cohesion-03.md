# Hearthmere — Whole-Town Cohesion Review 03

**Verdict:** `REVISE` (town layer)
**Prior reports:** `review/reports/cohesion-01.md`, `review/reports/cohesion-02.md`
**Renders assessed:** `review/shots/town-arrival.png`, `town-square.png`, and every venue folder.
All measurements taken from the shipped PNGs, the shipped textures in `assets/textures/`, and
the shipped meshes in `assets/meshes/`.

---

## Submission hygiene — clean, for the first time

Every render is 21:34–21:39; the last asset build is 21:34. Nothing on disk predates the build.
Two reviews running I opened with a stale-frame complaint. That is fixed and I will not raise it
again.

One thing does need saying, though it is a briefing problem rather than a build problem:
**`town-square.png` and `town-arrival.png` are the same camera.** Both are shot from the spawn
looking south through the gate; they differ only in a banner drape. There is no town-level frame
of the market square anywhere in this submission. The square is the destination of the entire
arrival composition, it is the venue I have criticised hardest for three reviews, and I have
still never been shown it in context — only in its own isolated venue render, on bare ground,
with no buildings around it. I cannot judge whether the square composes from its entrances
because no frame has ever attempted it.

---

## First impression (before analysis)

Two seconds on the arrival frame: **"a warm dirt track between two Lego pillars."**

This is a real improvement and I want to be precise about which part. The ground is warm now.
The frame has colour in it — earth, terracotta, green shutters, striped awnings. There is a
line running away from me made of two rows of kerbstones, and at the end of it there is a
building with an orange roof, awnings, and *people*. I know where to walk. That was not true in
either previous review, and it is the single thing the arrival brief cares most about.

Then the eye goes back to what is wrong, and it is the same two things as last time: the gate
piers are still nine perfectly identical stacked blocks per corner, jutting proud, occupying
roughly 38% of the frame's width; and the surface I am supposed to be walking on is not a road.
It is dirt with stones down the sides.

Second impression, walking the venues: the guild has been genuinely redesigned and is better.
The inn's windows are windows now. The stalls are still the best thing here. And the market
square has gone *backwards* — it is now a pale grey slab with a black hole in the middle,
sitting on brown earth with a razor-straight cliff edge around it.

---

## The headline claim: "verify the road actually reads"

**It does not. NOT RESOLVED — and I can tell you exactly why.**

The builder found two real causes, fixed both correctly, and I have verified both:

- **Ground is now earth.** `viewer.html:117` and `main.js:225` both load `dirt_albedo`.
  Confirmed.
- **Cobble palette drift is genuinely fixed.** Shipped `cobble_albedo` mean is now `#898477`,
  **ΔE 0.3** from locked `COBBLE #8A8578` (was ΔE 37.2, sitting on `COBBLE_WORN`). ΔE from
  `COBBLE_WORN` is now 10.6. That is a clean, verified re-lock. Median luminance separation from
  `dirt_albedo` is 132 vs 90.
- **The carriageway is proud, not buried.** `streets.py:81` `ROAD_LIFT = 0.10`; exported
  positions run y −0.013…+0.108 against a ground plane at −0.002. Confirmed.

All three claims are true. And the road still does not render.

Measured on `streets-gameplay.png`, full sun, no buildings in the way:

| Sample | Rendered L | Rendered hex |
| --- | --- | --- |
| Between the kerbs ("road") | 92.4 | `#6A5B48` |
| Earth, left of kerb | 102.7 | `#77644C` |
| Earth, right of kerb | 126.6 | `#8D7D65` |

The "road" is **darker than the earth on both sides**, and its rendered colour `#6A5B48` matches
`dirt_albedo`'s own mean `#6B5B47` to within one unit per channel. At y=470–485 the difference
across road and verge is 0.4–2.0 L units — the same ±5 I measured in round 02.

Meanwhile the market square plaza, which is **the same `cobble` material at the same 2.0 m
tiling**, renders at **L=158.5 / `#A29E98`**. Same material, same light, same frame family,
**66 luminance units apart.**

So I decoded the meshes. Here is the third cause, and it is one line:

```
assets/meshes/streets.gltf   Ford Road ribbon primitive
  576 verts, x −3.5..3.5, z −48..48, stored NORMAL = [0,1,0] on all 576
  triangles whose winding disagrees with that normal: 100 / 100

assets/meshes/market_square.gltf   plaza (control)
  same "cobble" material, 2.02 m tiling, 1101 m² flat surface
  triangles whose winding disagrees with that normal: 0 / 14368
```

`streets.py:92` reads:

```python
bld = M._Builder()
# Wound for a +Y geometric normal.
quad = [c3, c2, c1, c0]
```

The comment asserts exactly the thing that is false. The reversal to `[c3, c2, c1, c0]` gives a
clockwise winding seen from above, i.e. a **back face**. The `cobble` material ships
`doubleSided: false`. **Every carriageway triangle in Hearthmere is back-face culled. The road
surface is not drawn at all.** What I have been looking at between the kerbstones, in all three
reviews, is the bare ground plane — first cobble, now dirt. It reads *darker* than the verge
because three.js still renders shadow casters for `FrontSide` materials, so the invisible 10 cm
slab is casting its own shadow onto the earth beneath it.

Everything else about the street layer is correct and already built: paths, widths, materials,
tiling, kerbs, verge scatter, the lift, the trough. `quad = [c0, c1, c2, c3]` makes Ford Road,
Mere Street and Smith's Lane visible for the first time. **This is a one-line fix and it is the
highest-value change available in this project.**

Two process notes, offered as diagnosis:

1. CLAUDE.md: *"Verify visually before claiming done. An asset you have not seen is not
   finished."* Three genuine root causes were found and fixed by reasoning at source, and the
   result was submitted with "Verify the road actually reads" as an instruction to me rather
   than a check performed by the builder. A single luminance sample across the kerb line would
   have caught this.
2. This is a *class* of defect, not an instance. Across the ten shipped meshes there are
   **10,266 flat-shaded triangles wound exactly opposite to their own stored normal**
   (`stalls` 2,943, `townsfolk` 3,373, `cottage` 579, `guild` 572). Most are probably interior
   or hidden faces where it does not matter. Some are not. `core/venue.py:check_occlusion()` was
   the best process artifact of the last pass; a winding-consistency assertion beside it is the
   same idea and would have caught this before render.

---

## Adjudication: D-009, the lighting resolution

**The mechanism is right. The justification is not supported by the repository's own history,
and that matters.**

What is right, and it is the cleanest work in this pass:

- `content/town/hearthmere.json.lighting` is the single authoritative copy.
- `viewer.html:27` and `main.js:92` both read it at startup. Verified.
- The dead `skyFill`/`groundBounce` constants at `viewer.html:26` are **deleted**, and the
  comment that replaced them explains why dead values are worse than none. Verified by grep:
  `93BEE8` and `7A6A52` no longer appear anywhere in the repo.
- Art Bible §4 now documents the shipped values and points at the file.
- §8's *"reviewed at the locked 09:30 lighting"* is true for the first time in the project.

That is the correct shape of fix and I endorse it fully.

What is not supported. D-009 says the hardcoded values *"were deliberately tuned early on to fix
two measured defects"* and that *"the §4 numbers were the original untested guess."* The git
history says otherwise:

```
git show ac718cf --stat     # "Foundation: art bible, ... render harness"
                            # docs/ART_BIBLE.md AND tools/render/viewer.html, same commit
git show ac718cf:tools/render/viewer.html
  :26  skyFill:'#93BEE8', groundBounce:'#7A6A52'      <- the §4 values, declared
  :90  HemisphereLight('#AFC9E0','#8A7352', 1.35)     <- the shipped values, used
git log -- tools/render/viewer.html
  ac718cf, 38ece5b, 2cb6b67                            # lighting untouched until 2cb6b67
```

Both sets of numbers were authored **in the same commit, side by side**, and the rig was never
subsequently changed. There is no commit in which anyone rendered blue-grey facades, measured
crushed shadows, and adjusted the lights. The tuning pass that D-009 cites as its justification
did not happen. The two values diverged at birth and nobody noticed for three reviews.

Does that change the decision? Probably not — and I want to be fair here. The shipped frame is
*not* blue-grey and is *not* crushed; shadow regions in `guild-detail.png` and `inn-gameplay.png`
are warm and lifted, which is what §1 asks for. Keeping the rig may well be correct. But the
decision should be recorded on the grounds that actually exist — *"we kept the values the
renderers had; the frames look right with them and nobody has evidence the §4 guess is better"* —
not on a provenance that the history contradicts. A DECISIONS entry is the project's memory.
Ratifying a spec change on a reconstructed story is a worse failure than the divergence it
documents, because the next reader has no way to tell.

There is one live consequence. §1 calls the rim *"the single strongest anime-3D signature."*
It is now locked at **1.15** rather than 1.4, and 1.1 units of ambient and warm bounce sit over
it, on the strength of that story. The shipped arrival frame measures mean saturation 0.290
against a §1 target of "~15% above photoreal," and the plane separation §1 asks for is weak —
look at the guild tower against the sky in `town-arrival.png`, there is no cool edge on it at
all. I am not asking for a revert. I am asking that the rim be re-tested against 1.4 on its own
merits and the result written down honestly, whichever way it goes.

---

## Prior ranked findings — resolved?

### 1. Stop the ground being cobble (my #1) — **PARTIAL**

Ground swapped to earth: **RESOLVED**. Cobble palette re-locked to ΔE 0.3: **RESOLVED**.
Carriageway lifted proud: **RESOLVED**. The road reading in the frame: **NOT RESOLVED** — the
surface is back-face culled and undrawn. See above.

Two new problems created by the ground change, both real and both cheap:

- **Every paved pad now ends in a cliff.** In `market_square-detail.png` the plaza terminates in
  a razor-straight diagonal seam with a **58 L-unit step** (plaza 158.5, earth 98.9), no
  transition, no mud spill onto the paving, no worn-through patches, no scatter across the join.
  When ground and plaza were both cobble this seam was invisible. It is now the most prominent
  edge in the venue. Same defect at the inn plinth and the shop-row frontage. This is
  cohesion-01's *"paving pads are trip hazards to the eye"* finding, re-created by the fix.
- **The plaza reads as poured concrete.** L=158.5, near-neutral `#A29E98`, with a broad
  low-roughness specular band across it — the "oil slick desire path" from cohesion-01, still
  there, now far more visible against dark earth. The cobble *cell* size is the culprit and is
  unchanged: the coarse Worley layer reads at 0.33–0.40 m against the §3 spec of 0.12–0.22 m.
  D-007 records this shortfall honestly; it is now the largest single surface in the town.

### 2. Lighting single-source (my #3) — **RESOLVED as architecture, PARTIAL as light**

Rig plumbing resolved (above). Not resolved:

- **Forge still lights nothing.** `blacksmith-approach.png`: the coal bed glows and the stone
  hood above it, the anvil, the posts and the floor are all unlit. §4 specifies
  `Forge fire #FF8C42 @ 4.0, flickering`. Third review. The town's declared strongest light
  source is still an emissive decal.
- **No window spill anywhere.** §4 specifies `Window interior spill #FFD9A0 @ 2.2`. There is no
  such light in either rig.
- **The fountain is still the darkest object in the frame** — see below.

### 3. NPC talk-pair facing (my #5) — **RESOLVED**

Verified by computing yaw-to-partner from `content/entities/townsfolk.json`:

| Pair | Distance | Facing error |
| --- | --- | --- |
| `hm.folk.00` → `.01` | 1.25 m | **4.0°** (partner returns 1.3°) |
| `hm.folk.05` → `.06` | 1.14 m | **1.0°** (partner returns 2.9°) |
| `hm.folk.10` → `.09` | 1.75 m | **2.6°** (partner returns 0.6°) |
| `hm.folk.18` → `.17` | 5.61 m | **2.4°** (partner returns 0.7°) |

Was 46–150°. Now derived from the partner, all within 4°. Clean fix, exactly as asked.

Two things left over. `folk.18`/`folk.17` face each other precisely across **5.61 m** — that is
not a conversation, it is two people staring at each other from opposite kerbs; move them
together or re-label the pose. And **21 of 21 are still `schedule: "static_v0"`.** The arrival
brief requires *"NPCs moving."* Nothing in Hearthmere moves except smoke. Third review.

### 4. Guild massing — **RESOLVED**

Verified in `guild-approach.png` and `guild-silhouette.png`:

- Merlons are full height and read clearly as crenellation. Resolved.
- The entrance bay is a real gable presenting to the street, not a band. Resolved.
- Tower lancets stand proud of the wall and cast their own shadow. Resolved.
- The silhouette render itself is now usable — the black override no longer swallows the ground
  plane, so §6's black-on-white test can actually be run for the first time. That is a genuine
  tooling fix and it should have been called out louder.

The massing is now the best in the town: asymmetric tower, projecting gabled bay, lower hall
wing, spire and finial. Credit where due — this went from a flat slab to a landmark in two
passes.

### 5. `M.lathe` material loss — **RESOLVED**

Verified at source in `2cb6b67`: lathe U is now arc length in metres rather than normalised
angle, so a 6.6 m-circumference turret no longer stretches one tile around itself while the box
wall beside it tiles three times. This was a real core bug affecting every lathed object
town-wide and finding it was good work.

It did **not** rescue the fountain, because the fountain's problem is not its UVs.

---

## Still open from round 02 — scored against

### Gate finish — **PARTIAL, and I owe a correction**

**I was wrong about the chamfer and I withdraw it.** `streets.py:216–228` builds the pier blocks
at `chamfer=0.025`, the quoins at `0.016` and the voussoirs at `0.02`, against a §6 architectural
spec of 15 mm. The gate masonry *is* chamfered, at or above spec, and the bevel highlight is
visible on the quoin edges in `streets-detail.png`. My round-02 phrasing "unchamfered ashlar" was
wrong and I should have read the geometry before writing it.

What is actually wrong is more specific and it is unchanged:

- **Quoins are still centred on the pier corner.** `q.translate(px + cx * PIER * 0.5, ...)` —
  half of every quoin projects ~0.17 m proud of *both* faces. In `arr_pierL` at 6 m you can see
  the underside shelf of each one. They read as stacked bricks, not as dressed corners.
- **Zero jitter across nine identical courses per corner, four corners, two piers.** §6:
  ±3% position, ±2° rotation, ±4% scale, and *"no element may appear more than 3 times in a row
  without a variant."* Seventy-two quoins, no variance. Note that `rng = rng_for(asset_id,
  "gate")` is created at line 204 and **never used anywhere in the function** — the jitter was
  intended and never written. These are the nearest, largest, highest-contrast objects in the
  most important frame in the project.
- **Voussoirs are still cuboids.** Thirteen identical `M.box(0.62, 0.90, ...)` rotated around an
  arc. The stepped extrados gaps are plainly visible in `streets-gameplay.png`. A voussoir is a
  wedge.
- **The arch is still not in the arrival frame.** Crop the top 300 px of `town-arrival.png`:
  between the piers there is only sky. The arch *exists* and frames beautifully in
  `streets-gameplay.png` — which makes this purely a camera or springing-height problem, and
  therefore cheap. The brief requires *"the gate arch framing the shot."* Two piers is a slot.
- **Still fortress-scale.** 1.5 m piers at 5.2 m with 0.4 m quoins, on a town the World Bible
  calls *"more customs boundary than defence."*

### Fountain being the darkest object in its own frame — **NOT RESOLVED**

`market_square-gameplay.png`: basin **L=45.6** in a plaza at **L=150.7**. A 105-unit hole. It is
by a wide margin the lowest-luminance object in its own venue render.

In `town-arrival.png` the fountain region measures **L=87.8** against a frame mean of **118.0**
and a central focal band of **130.3**. The town's declared anchor, sitting at world origin at the
exact centre of the most important composition in the project, is a dark grey lump 30 units below
frame average. Third review running.

The composition *around* it has genuinely improved, which makes this worse rather than better:
the focal band is now **12 L units brighter than the frame mean** (round 02: 20 units *darker*).
The picture finally leads the eye to its own destination — and the thing waiting there is a hole.

### Square entity density — **NOT RESOLVED**

Counted from `content/entities/`: market_square **3**, cottage **1**, blacksmith **3**, inn 4,
guild 5, pub 5, streets 5, shop_row 6, stalls 8. **Identical to round 02. Nothing was added
anywhere.**

The square is a signpost, two trestle frames, four barrels, a stone bench and pebble decals
across ~34 × 32 m. The brief asks for spilled produce, a broken crate nobody has cleared,
pigeons, a dog under a cart, chalk tallies on the fountain lip. Third review, unchanged text.

### Aged-terracotta proportion — **PARTIAL**

Coverage within 20 RGB of `#8F4E36` is now **22.5%**, up from 12.8%, against a §4 target of ~30%.
Real movement. But the luminance span is still **15 units** (p05 98, p95 114) versus 13 last
review, and that is the number that actually matters — it is why every roof in town still reads
as one flat sheet at distance. `blacksmith-approach.png` shows it best: the largest roof in the
settlement is a single uninflected orange plane with corrugation-scale course spacing.

### Thatch off-palette with no DECISIONS entry — **NOT RESOLVED**

`thatch_albedo` = `#A68852`, nearest §4 entry *oak* at **ΔE 14.1**. §4 lists two roof materials.
`docs/DECISIONS.md` runs D-001…D-009 and the word "thatch" appears **zero times** in it or in the
Art Bible. Unchanged across three reviews.

And it still does not read as thatch. `cottage-approach.png`: a smooth olive-green sheet with
hard chamfered edges and three horizontal bands. No straw direction, no courses, no ridge
treatment, no sag, no eaves depth. The hue is wrong for straw in the first place. This is on the
venue whose stated job is to make Hearthmere read as a town, and there are six of them.

### Also unchanged, from the round-02 list

- **Blacksmith chimney** — still a stub clearing the ridge by ~0.3 m on a 6 m building, against
  a declared anchor silhouette of *"forge chimney + open work yard."* §6 requires secondary
  elements to read at 30 m. **NOT RESOLVED**, third review.
- **Shop row** — the ground-floor wall plane is still continuous and coplanar for 20.4 m
  (§7 limit: 12 m). Counters still near-bare — no barrels or sacks for the general store, no
  herbs or bottles for the apothecary, no cloth or dress form for the tailor. One hanging sign
  visible and it is occluded by its own awning. Still no chimneys on a three-shop terrace with
  living quarters above. **NOT RESOLVED.**
- **Guild interior** — doors open, and behind them is a dark grey box. Brief: *"a stone hall, a
  reception counter, a big map on the wall, weapon racks, adventurers loitering."*
  **NOT RESOLVED.**
- **`stone` crazy-paving** — `REFERENCES.md` names this by name as an anti-reference. It is the
  customs wall, every plinth, every kerb and the forge hood. In `streets-detail.png` it is
  ~0.4 m Voronoi cells on a 1.15 m wall at 1.5 m from camera, and it is the single worst surface
  in the build. **NOT RESOLVED**, third review.
- **Player capsule** — still the largest, most central, highest-contrast object in the arrival
  frame. **NOT RESOLVED.**

### Windows — **PARTIAL, and a real gain**

Round 02's finding was that lit windows had converted every aperture into an *opaque painted
rectangle*, which was a worse read than a dark window. That is fixed. In `inn-gameplay.png` the
panes are now dark, recessed, and carry leaded mullions and sills — they read as glass. Same on
the shop row's upper storey. Genuine improvement and the right call.

Still open: nothing is lit behind them, so the inn's *"warm light in every window — the most
inviting thing in the frame"* is not delivered, and the shops' ground-floor display windows are
still blank cream plaster behind the counters. The town still has no interiors.

---

## The arrival composition against its brief

| Required | 02 | 03 | Note |
| --- | --- | --- | --- |
| Gate arch framing the shot | Partial | **Partial** | Arch exists and frames well in `streets-gameplay`. Not in the arrival frame — only sky between the piers. |
| Ford Road leading the eye | No | **Partial** | The *line* reads, via kerbstones. The *surface* is undrawn — back-face culled. |
| Fountain as focal point at centre | No | **No** | L=87.8 vs frame 118.0. Darkest thing at the centre of the picture. |
| Guild tower rising on the RIGHT | Yes | **Yes** | Correct side, reads, better massing. Banner still clipped by the top frame edge. |
| Inn's roofline on the left | Technically | **Technically** | Correct side, still the blank gable end. |
| Stall awnings adding colour | Yes | **Yes** | Still the best colour in the frame. |
| NPCs moving | No | **Partial** | Five or six figures now visible at the terminus and they face each other — genuinely reads as a market. 21/21 still `static_v0`; nothing moves. |

Measured on `town-arrival.png` (1600 × 900):

| Metric | 01 | 02 | 03 |
| --- | --- | --- | --- |
| Frame mean L | 131 | 125.4 | **118.0** |
| Central focal band mean L | 113 | 105.7 | **130.3** |
| Focal band vs frame | −18 | −19.7 | **+12.3** |
| Mean saturation | 0.239 | 0.227 | **0.290** |
| Sky fraction | — | 10.1% | 10.1% |

**The focal-band inversion is the most important number in this review.** For two reviews the
composition led the eye away from its own destination. It no longer does. Combined with the
saturation gain and the people at the terminus, the stated failure condition — *"if the player
does not immediately know where to walk, the composition has failed"* — is **no longer met**.
I knew where to walk. That is a real, earned pass on the brief's own hardest test, and it is why
this review moves.

Everything else in that table is still open.

---

## Does it read as one settlement?

**Closer again. Still no.**

What now works: the ground is warm and the town sits in a landscape rather than on a car park;
the palette is verifiably locked at the albedo (`cobble` ΔE 0.3, `plaster` 1.2, `terracotta` 4.3);
one lighting rig with one consumer; the guild is a landmark; the talk pairs are people rather
than mannequins; the windows are apertures.

What still breaks it:

1. **The spine is missing.** The street layer is the thing that turns eight objects into a
   settlement, and its surface is not drawn. Every venue currently sits on undifferentiated
   earth with a line of stones nearby.
2. **Two masonry standards, and it is now measurable.** `ashlar_normal` has a mean XY deviation
   of **0.025** and p95 **0.027** — it is essentially a flat map. Compare `cobble_normal` at p95
   **0.278**, ten times the relief. The hero building and the gate carry a material with no
   mortar depth and no per-stone relief, whose albedo spans **12 luminance units**, so the
   "blocks" exist only as a printed pattern. That is why the guild reads as wallpaper at 1.5 m
   in `guild-detail.png` and why the gate reads as blockout. One material, two of the most
   important objects in the town. This is a much better diagnosis than "unchamfered," which
   was my error.
3. **Every paved surface is a rug.** Hard 50–60 unit value steps at razor-straight geometric
   seams, with no transition material anywhere. The buildings still sit *on* the world rather
   than growing out of it.
4. **Nothing has an interior and nothing moves.** Guild hall a grey box, shop displays solid
   plaster, no window spill, no forge light, 21/21 static.
5. **The world has no edge.** `streets-approach.png`: flat brown to a hard straight horizon in
   every direction. No terrain, no treeline, no distant hills — and no lake, in a town whose
   name is Hearth*mere* and whose World Bible calls it a lake town. This is not on my prior
   lists and I should have raised it sooner.

---

## Blind AAA comparison

Against Gridania, Divinity's Reach and Boralus — **a player still picks this out, in about two
seconds.**

The tells, in the order they land: the blue capsule protagonist; two piers of nine perfectly
identical stacked blocks filling ~38% of the frame width; an infinite flat plane meeting a hard
horizon with nothing on it; a road that is two rows of stones on dirt; a dark lump where the
focal point should be.

But the gap has changed shape again and that is worth stating precisely. Round 01: nobody had
built the town. Round 02: the town was built to blockout standard under buildings built to a
much higher one. Round 03: **the town layer is now correctly designed, correctly authored, and
failing on execution defects that are individually small.** The road is one character. The
quoins need the `rng` that is already sitting unused three lines above them. The fountain needs
a water surface. That is a finishing pass, not a rebuild, and it is a far better place to be
than either previous review.

**Would people play this?** Not yet. But for the first time the arrival frame communicates
"place" rather than "prototype," and the remaining distance is finish work.

---

## Scores

**Acceptance requires no axis < 7 and AAA comparison ≥ 8.**

| Axis | 01 | 02 | 03 | Note |
| --- | --- | --- | --- | --- |
| Silhouette (town skyline) | 3 | 5 | **6** | Guild massing genuinely fixed — merlons, street-facing gable, proud lancets, and the silhouette rig now works so §6's black-on-white test is runnable at last. Held down by the blacksmith's 0.3 m stub against its own declared anchor, a bald 20.4 m shop-row roofline, and one chimney reading in the arrival frame. |
| Material truth | 4 | 4 | **4** | Cobble re-locked to ΔE 0.3 and the lathe UV bug fixed town-wide — both real. Against that: the carriageway is undrawn so the town's headline surface renders as dirt; `ashlar_normal` measures flat (p95 0.027); `stone` crazy-paving unchanged on wall, plinths, kerbs, forge hood; plaza reads as concrete with a specular slick; thatch still a painted olive sheet. |
| Lighting response | 3 | 3 | **6** | One authoritative rig in `content/`, both renderers consuming it, dead constants deleted, §8's locked-lighting box true for the first time. Focal band moved from 20 L below frame mean to 12 above; saturation 0.227→0.290. Held down by no forge light, no window spill, a focal point 30 L below frame mean, and rim at 82% of the §1 signature on a justification the history does not support. |
| Detail hierarchy / density | 3 | 4 | **4** | Entity counts byte-identical to round 02. Square still 3, cottage still 1, blacksmith still 3. Shop counters near-bare against three sharply differentiated briefs. Stalls still the only layered venue. |
| Wear & story | 4 | 4 | **4** | Guild threshold dished, jar at the door, coal scatter, spilled tomatoes. The road trough now exists on a surface that is not drawn. Ground splash still unwired (D-005). Every paved pad ends in an unweathered cliff — the ground fix made this worse, not better. |
| Life & residue | 3 | 4 | **5** | All four talk pairs verified within 4° of their partner, derived not authored — clean fix. Market terminus now reads as inhabited. Held down by 21/21 `static_v0`, two animals, a 5.6 m "conversation," and no interior life anywhere. |
| Cohesion (one culture) | 4 | 5 | **5** | Warm earth unifies the town and the albedo lock is verified. Held down by a measurably flat ashlar against everything else, undocumented off-palette thatch, hard cliff seams at every paved edge, an invisible street spine, and a world with no horizon treatment in a lake town with no lake. |
| Scale truth | 6 | 5 | **5** | Cobble albedo correct but coarse cells still 0.33–0.40 m against §3's 0.22 m max; roof course exposure still ~2× spec; fortress-scale gate on a town the World Bible says has never been besieged. |
| Sightlines & navigation | 2 | 4 | **5** | The brief's own failure condition is no longer met — the focal band is brighter than the frame and I knew where to walk. Held down by an undrawn carriageway, the arch outside the frame, a 20.4 m unbroken facade, an occluded sign, and a dark focal point. |
| **AAA comparison** | 2 | 4 | **5** | Reads as a place rather than a prototype for the first time. Still identified in ~2 seconds by five tells, three of which are in the gate. |

Every axis below 7. AAA comparison at 5 against a bar of 8.

---

## Verdict

`REVISE` — town layer.

Not `ACCEPT`, and not close: no axis reaches 7 and the blind comparison fails by three points.
Not `REJECT` either — `REJECT` means *"fundamentally wrong approach, rebuild, do not patch,"* and
that is emphatically not the situation. The design of the town layer is right, the data model is
right, the palette is locked, the lighting is single-sourced, and the largest single defect in
the build is a four-token change to one array literal.

This pass did real, verifiable work: the palette re-lock, the lathe UV bug, the lighting
single-source, the NPC facing derivation, the guild massing, the silhouette rig, the window
apertures. Six of those seven are things I asked for and got. I want that on the record, because
the score movement (AAA 4→5) understates it — most of the gain landed on axes that were already
being held down by defects the builder did not get to.

Venue scoping:

- **`REVISE` → still open:** streets/gate (winding, quoins, voussoirs, arch in frame, scale),
  market square (fountain void, 3 entities, pad edge, concrete plaza), guild (ashlar relief,
  interior), blacksmith (stub stack, forge lights nothing), shop row (20.4 m facade, empty
  briefs, solid display windows, occluded sign, no chimneys), cottage (thatch material and
  DECISIONS entry), inn and pub (no window spill).
- **Hold — stalls.** Unchanged and still the reference. Do not touch.

---

## Remaining blockers, ranked by impact per unit of effort

1. **Flip the carriageway winding.** `tools/assetgen/venues/streets.py:92`,
   `quad = [c3, c2, c1, c0]` → `[c0, c1, c2, c3]`. **One line.** Ford Road, Mere Street and
   Smith's Lane become visible for the first time in the project; the town gets its spine; the
   `REFERENCES.md` "flat ground" anti-reference finally dies; and roughly half the arrival frame
   starts doing compositional work. Everything else about the street layer is already correct
   and verified. Then add a winding-consistency assertion next to `core/venue.py:check_occlusion()`
   — there are 10,266 flat triangles town-wide wound against their own normals and no tooling
   looks for them. **Highest ratio I have seen in three reviews.**

2. **Weather every paved edge, and take the shine off the plaza.** Every pad now meets the earth
   at a razor-straight 50–60 L-unit step. Feather the joins — mud spill onto the paving,
   worn-through patches at the kerb line, scatter across the seam — and bring the plaza's cobble
   cell size down from 0.33–0.40 m to the §3 0.12–0.22 m so it stops reading as poured concrete,
   and kill the low-roughness specular band across it. This is the largest surface area in the
   town and it currently reads as a grey rug on a brown floor.

3. **Make the fountain the brightest thing in the mid-distance, and dress the square to its
   brief.** Basin at L=45.6 inside a plaza at L=150.7, and L=87.8 against a frame mean of 118.0
   at the exact centre of the arrival shot. Third review. Give the basin a water surface with a
   sky reflection, put the sun on the heron spout, lift the stone value — then spilled produce, a
   broken crate, pigeons, a dog, chalk tallies on the lip. Three entities is not a town square.
   The composition now delivers the player to this spot; make something be there.

4. **Finish the gate.** Set the quoins **flush** with the pier faces instead of centred on the
   corner; **use the `rng` created at `streets.py:204` and never referenced** to apply §6's
   mandatory ±3% position / ±2° rotation / ±4% scale, so 72 identical blocks stop reading as
   Lego; taper the voussoirs into wedges; drop the pier section and height to customs-arch scale;
   and get the arch into the arrival frame — it already frames beautifully in
   `streets-gameplay.png`, so this is a camera pitch or springing height, not new geometry.
   *(Withdrawing my round-02 chamfer claim: the gate is chamfered at 16–25 mm, at or above the
   §6 15 mm spec. The defect is repetition, not sharpness.)*

5. **Rebuild `ashlar_normal` and give `ashlar_albedo` a value spread.** Measured mean |XY|
   deviation **0.025**, p95 **0.027** — flat, against `cobble_normal`'s p95 of 0.278. Albedo
   spans 12 luminance units. Add mortar-joint depth, per-stone relief and per-stone value
   variance. One material fixes the hero building at hero distance *and* the foreground of the
   arrival frame, and it is the last thing making the guild look like it came from a different
   game.

6. **Replace the `stone` material.** `REFERENCES.md` names crazy-paving as an anti-reference by
   name; it is the customs wall, every plinth, every kerb and the forge hood, at ~0.4 m cells on
   a 1.15 m wall. Third review running, and in `streets-detail.png` it is the nearest surface to
   camera.

**Also required before re-review, lower ratio but non-negotiable:**

7. Give the blacksmith a real stack — its brief calls the forge chimney the venue's anchor
   silhouette and it clears the ridge by 0.3 m — and put a real `#FF8C42 @ 4.0` light at the
   forge so the hood, anvil and floor are lit.
8. Break the shop row's 20.4 m coplanar ground-floor wall with a recess or projection; give the
   three shops the goods their briefs name; move the hanging signs clear of the awnings; add
   chimneys.
9. Put `#FFD9A0 @ 2.2` spill behind the inn's windows and give the shops interiors behind their
   display openings. The apertures now read as glass; light them.
10. Halve the terracotta course exposure to the §3 0.16 m and widen the luminance span past 15
    units — coverage moved 12.8%→22.5% but the value spread is what makes roofs read.
11. Either bring the cottage roofs onto the §4 palette or write the thatch DECISIONS entry —
    and either way rebuild the material so it reads as straw: direction, courses, a ridge, sag,
    and a straw hue rather than olive.
12. Replace the placeholder player capsule.
13. Give at least the square a walk cycle so `static_v0` stops being literally true of every
    person in the world.
14. Do something with the horizon. Flat brown to a hard straight edge in all directions, and no
    lake in a town called Hearthmere.

---

## Known limitation, reported separately — NPC skinning

Per the brief, keeping this apart from the environment findings.

`townsfolk-gameplay.png` at close range: the figures are articulated primitives. Box torso,
capsule limbs with **visible gaps at every joint** between upper and lower arm and leg, a slab
head with a cap of hair, blocky feet, no hands, no faces. There is no skinning and no
deformation, so the poses are assemblies of disconnected parts rather than bodies.

Judged honestly, this costs the build about a point on Life & residue and is one of the five
tells in the blind comparison — at conversational distance a Divinity's Reach NPC is a skinned,
animated character and these are not. At the distances that dominate the arrival frame (15 m+)
they read perfectly well: silhouettes are correct, proportions are correct, the children rule is
right, the clothing colours vary, and now that the facing is derived they read as people doing
things. `core/npc.py` remains better than the job required.

I am recording it as a scored limitation rather than a defect, because it is a stated pipeline
constraint and the owner has not decided whether to accept it as a scoped exception. My
recommendation: **accept it as a scoped exception and record it in `DECISIONS.md`**, with the
cost stated plainly — no close-up NPC shot can be shown, and the town cannot be reviewed at
conversational distance until there is skinning. It is not the thing holding this build back.
The road, the fountain and the gate are.

---

## What is working — preserve this

1. **The palette lock is now verified end to end.** `cobble` ΔE **0.3**, `plaster` **1.2**,
   `plaster_shade` **1.9**, `terracotta` **4.3**. `core/palette.py` is a genuine single source of
   truth and the cobble re-lock was exactly the right response to my finding. This is the most
   disciplined part of the build.
2. **The lighting single-source.** One authoritative copy in `content/`, two consumers, dead
   constants deleted, spec pointing at the file, decision recorded. Whatever I think of D-009's
   provenance argument, the *shape* of this fix is correct and it closed a hole that had
   invalidated every sign-off in the repository.
3. **The `M.lathe` UV fix.** A real core bug, found by reasoning from a symptom in two unrelated
   venues to one root cause. That is exactly the right instinct and it is why the shared-core
   rule in CLAUDE.md exists.
4. **The NPC facing derivation.** Asked for computed facing, got computed facing, verified within
   4° on all four pairs. No arguing, no partial credit needed.
5. **The guild.** Massing, merlons, street-facing gable, proud lancets, spire, finial. Two passes
   from flat slab to the town's landmark. It needs one material fixed and an interior dressed.
6. **The silhouette rig fix.** §6's black-on-white test could not previously be run at all. It
   can now. Unglamorous and important.
7. **The inn's windows.** Round 02's painted panels are gone; they are recessed, mullioned and
   read as glass. Correct fix, and it propagated to the shop row.
8. **The stalls.** Unchanged, still the best work in the build, still the standard. Fish on wet
   boards, spilled tomatoes, the cat, the chalk slate. Do not touch them.
9. **`streets.py` as a module.** Reads the authored layout, invents nothing, readable, and its
   geometry and materials are all correct. It has one character wrong. Do not rewrite it.

---

## Re-review criteria

I will re-review when the arrival frame, re-shot from the client, shows: a carriageway that is
visibly paved stone rather than the ground plane; the gate arch inside the frame with jittered
quoins set flush; a fountain that is the **brightest** object in the mid-distance; a market square
with more than three things in it; and at least three chimneys above the roofline. Those five,
plus the ashlar relief rebuild, are the difference between a 5 and a credible run at the bar.
