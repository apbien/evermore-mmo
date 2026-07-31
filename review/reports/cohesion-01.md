# Hearthmere — Whole-Town Cohesion Review 01

**Verdict:** `REJECT` (town layer) — individual venues return as `REVISE`
**Renders:** `review/shots/town-arrival.png`, `review/shots/{guild,inn,pub,blacksmith,shop_row,market_square,stalls,cottage}/*`
**Re-shot during review:** the `town-arrival.png` on disk was stale (rendered 20:11, before
`townsfolk.gltf` at 20:19, and it reads `13 venues, 34 entities`). I re-captured the client at
the spawn point to judge current state (`14 venues, 55 entities`). Both frames are assessed
below. Nothing in the re-shot changes the verdict.

---

## First impression (before analysis)

A greybox. Two seconds on the arrival frame and the read is *unfinished prototype*: a blue
pill-man standing on a vast flat grey plain, with a handful of untextured-looking boxes pushed
to the edges of the frame and nothing at all in the middle. I did not know where to walk. I did
not know what the settlement was for. My eye went to the crimson banner in the top-right corner
— which is clipped by the frame edge — because it is the only saturated colour in the picture.

Second impression, walking the venue shots: the *buildings* are further along than the frame
suggests. The inn is a real building. The stalls have real residue. But they are seven objects
photographed separately on an infinite grey plane, and the town between them was never built.

---

## Does this read as one settlement built by one culture?

**No — it reads as one asset kit, applied inconsistently, with no town underneath it.**

There is a difference between *cohesion* and *sameness*. Hearthmere currently has the wrong one.
Every venue is built from the same core kit — same plank door, same shutter, same leaded window,
same gable roof — so at the level of components it is uniform. But the things that actually make
a settlement read as one place, all of which sit *between* the buildings, do not exist:

- There is no ground. There is a 400 × 400 m flat plane (`tools/render/viewer.html:107`,
  `PlaneGeometry(400,400)`). Every venue sits on it as an island, several of them on their own
  little raised rectangular paving pad that terminates in a visible hard cliff edge
  (clearest in `pub/pub-approach.png` and `market_square/market_square-detail.png`, where the
  square's pad ends in a raw diagonal seam mid-frame at gameplay height).
- There are no streets. `content/town/hearthmere.json` authors three streets — Ford Road with a
  7 m width, a cobble surface, a six-point path, and a comment about the cart-worn centre trough
  — and **nothing in the pipeline consumes `streets[]`.** The data is written and unused.
- There is no gate. `hm.gate.north` is declared at `(0,0,-46)`, two metres behind the spawn, with
  a comment describing the framing it is supposed to provide. No geometry exists for it.
- There is no wall, no mere, no orchard, no midden, no garden, no stable — six of the plan's
  labelled cells in `WORLD_BIBLE.md` are empty ground.

So: same components, no place. The result is the specific failure the protocol warns about —
technically consistent, and still not a town.

### Palette drift — measured, not eyeballed

I k-means clustered every gameplay render and matched each dominant cluster to its nearest
Art Bible §4 entry. Findings:

| Drift | Evidence | Verdict |
| --- | --- | --- |
| **Lime plaster has drifted off its own primary** | Every plaster surface in town clusters at `#C8BEA9` / `#C4BAA4` / `#C9BFAA` (inn, shop row, pub). The locked primary is `#E8DCC4`. Nothing anywhere in the build lands near it. The town's declared base value is ~20 units brighter and warmer than what actually ships. | The whole town is rendering in the *shadowed* variant `#D4C4A8` and below. The base value is wrong everywhere, which is why the settlement reads cool and dour rather than "warm, inviting, safe." |
| **Terracotta has drifted hot** | Roofs cluster at `#BE673C`, `#C16F41`, `#C2683D`, `#C37345`, `#BC673C`. Locked value `#B5603E`. Consistently 8–20 units more orange and lighter. | The roofs read as saturated modern orange, not fired clay. This is the loudest colour in the town and it is off-palette in every venue. |
| **Aged terracotta is absent** | §4 specifies `#8F4E36` on ~30% of tiles. No cluster anywhere resolves to it. | Every roof is one hue. Combined with the uniform tile pattern, roofs read as printed corrugated sheet. |
| **The cottage roof is off-palette entirely** | `#BE9F5E` at 13.1% of the cottage frame; nearest palette entry is *foundation stone* at ΔE 53.5. This is thatch. | §4 lists **two** roof materials: terracotta and slate. Thatch is not in the palette and there is no entry in `docs/DECISIONS.md`. The cottages — the "residential filler that makes it a *town*" — are the one venue whose roofs do not match the town. That is precisely backwards. |
| **Guild stone is a different family** | `#A3957A`, `#AA9C82`, `#9A8B71`, `#B8AC94` — warm sandstone, drifting up to ΔE 42 from foundation stone `#9A9083`. | The brief *does* want the guild to read as imported. But imported means different *form and dressing*, not a different colour temperature — right now it reads as a different game's asset. |
| **Timber value drifts between venues** | Inn framing clusters `#88633D`, shop row `#816540` with large `#B49868`-family highlights; the cottage frame is lighter and yellower again. | Same structural member, three different woods, no story explaining why. |
| **Half the accent palette is unused** | Bronze, brass, verdigris, herb green, produce accent and pub amber register above 2% in essentially no frame. | §4's entire "Accent & Life" block is decorative documentation. The town has three colours: cream, orange, grey. |

### Material treatments do not match

- **The documented anti-reference is still shipping.** `docs/REFERENCES.md` calls out by name:
  *"Our first plaster crackled at ~30cm cells and read as crazy-paving stone instead of lime
  render."* That exact defect is on the cottage walls (`cottage-gameplay.png`), the smithy floor
  (`blacksmith-approach.png`), and the market square paving (`market_square-detail.png`). Cell
  size reads 0.4–0.8 m against the §3 cobble spec of 0.12–0.22 m. A known, written-down,
  previously-rejected defect made it into three venues.
- **Flat ground.** Same document: *"Flat ground. A texture plane under buildings kills an
  otherwise good shot."* It is the dominant surface of the entire build.
- **Roughness is uniform where it matters most.** The square's "desire path" is not worn stone —
  it is a broad low-roughness specular streak that reads as spilled oil or a render artifact
  (`market_square-detail.png`). §5 asks for roughness 0.65 broken by regions at 0.12 with soft
  transitions plus per-stone variance; what shipped is a single smooth band painted over a
  voronoi tile.
- **The guild's masonry is machine-perfect.** `guild-detail.png` is a running bond of identical
  rectangles with dead-flat faces and **no visible chamfer at all** — hard 90° corners at 2 m
  from camera. Art Bible §6 calls chamfering "the first thing the art director check looks for,"
  and §2 forbids anything perfectly repeated. This fails both, on the hero building, at hero
  distance.

---

## The arrival shot

This is the most important composition in the build and it fails its own written specification.
The World Bible requires seven things in one frame. Scored:

| Required | Present | Note |
| --- | --- | --- |
| Gate arch framing the shot | **No** | No gate geometry exists. The frame has no foreground element whatsoever. |
| Ford Road leading the eye | **No** | No road exists as geometry or material. The ground between spawn and square is one undifferentiated texture for ~40 m. |
| Fountain as focal point at centre | **Technically** | It is centred and it is the *darkest, lowest-contrast, least legible* object in the frame. |
| Guild tower | **Clipped** | Occupies the right third, cropped by the frame edge; the tower top and the banner are cut off. |
| Inn roofline | **Wrong face** | The arrival angle shows the inn's blank gable end. |
| Stall colour | **No** | Awnings desaturate to grey-brown at that distance; the square reads as dark clutter. |
| NPCs moving | **No** | All 21 townsfolk are `schedule: "static_v0"`. Nothing in the town moves except smoke. |

Measured on the re-shot frame:

- **52% of the image is empty ground** below the building line, at a standard deviation of 23.9 —
  a flat field with essentially no information in it.
- **The central mid-distance band — where the eye is supposed to land — has mean luminance 113
  against a frame mean of 131.** The focal point region is *darker* than the average of the
  picture, and the brightest pixel in the frame (229) is not in it (band max 208). Art Bible §7
  and `REFERENCES.md` both require "something bright at the end of the sightline." The
  composition currently leads the eye *away* from where the player must walk.
- Mean saturation across the frame is 0.239, and 0.198 across the ground band. This is a
  desaturated grey picture, against a §1 target of "~15% above photoreal."

**The stated failure condition is met.** `WORLD_BIBLE.md`: *"If the player does not immediately
know where to walk, the composition has failed."* I did not know where to walk.

Two further problems specific to this frame:

- **The player character is a placeholder capsule** — blue pill limbs, sphere head — and it is
  the largest, most central, most contrasted object in the most important frame in the build.
  Meanwhile the NPCs beside it are properly articulated posed figures. Whatever the reason, this
  frame cannot be shown to anyone in this state.
- **The two documents disagree about the composition and nobody noticed.** `WORLD_BIBLE.md:108`
  says *"the guild tower rising on the LEFT ... the inn's roofline on the right."*
  `content/town/hearthmere.json:352` says *"guild tower right, inn roofline left."* The build
  matches the JSON. That the two specs for the single most important frame in the project
  contradict each other, and both were signed off, tells me the arrival shot was never actually
  reviewed against its brief.
- **The arrival frame is not lit to the locked rig.** `make shots` renders venues at the §4
  values. The arrival frame comes from the client, and `client/src/main.js` uses hemisphere
  `#AFC9E0`/`#8A7352` at **1.35** (spec: `#93BEE8`/`#7A6A52` at 1.1), rim at **1.15** (spec 1.4),
  plus an extra `#C9A87E` bounce light at 0.55 that is not in the Art Bible at all. That is why
  the arrival frame is hazier and flatter than every venue render. **The town does not look like
  its own venues, because it is not lit like them.**

---

## Density layering (§7)

Uniformly sparse, with one accidental exception.

The §7 model is anchor / function / residue, with quiet corners set against busy ones. What
exists is a single density everywhere, and that density is *low*:

- **Gate to square: ~40 m of absolutely nothing.** Not a kerb, a bollard, a gutter, a cart rut, a
  puddle, a weed, a crate, a hitching post, a milestone. The player's first forty metres of the
  world are an empty car park.
- **The market square is empty.** `market_square-gameplay.png` in isolation: a fountain, one
  signpost, two trestle frames, two barrels, a stone bench, and a scatter of flat pebble decals
  on a plane. The brief calls for spilled produce, a broken crate nobody has cleared, pigeons, a
  dog under a cart, chalk tallies. Almost none of it is there. This is the town's living room and
  it is furnished like a parking lot.
- **The shop row is three empty shops.** The brief differentiates them sharply — general store
  "barrels and sacks spilling onto the street," apothecary "hanging dried herbs, bottles, the
  most colourful interior," tailor "bolts of cloth, a dress form." All three counters are bare.
  The three shops are visually indistinguishable: same door, same shutter, same counter, same
  sign bracket, same roof pitch, same everything.
- **Every window in Hearthmere is a black hole.** The inn brief says *"Warm light in every window
  — the inn is the most inviting thing in the frame."* Not one lit window exists in the town. The
  emissive channel is in the §5 material standard and is used nowhere except the forge coals.
- **The forge does no lighting work.** §7/§4 call it "the town's strongest light source and the
  only significant emissive," at intensity 4.0. In `blacksmith-gameplay.png` the coals are an
  orange strip and *nothing around them is lit* — not the stone hood above, not the anvil, not
  the posts, not the floor. The single most dramatic lighting opportunity in the town is a flat
  decal.
- **The exception:** the stalls. `stalls-gameplay.png` has laid-out fish, crates of produce,
  spilled tomatoes on the ground, a leaning cartwheel, a broom, a cat, and chalk tally marks on a
  slate. This is the only venue in the build where a person appears to have been present. It is
  also, not coincidentally, the only venue I enjoyed looking at. **This is the standard the other
  seven have to meet, and the builder who made it should be the one who fixes the square.**

---

## Sightlines (§7)

- **"No wall of undifferentiated facade longer than 12 m without a break."** Shop row is a
  continuous ~24 m frontage of near-identical timber bays, broken only by a shallow step in three
  roof planes of identical pitch and identical material (`shop_row-approach.png`). Direct
  violation, on the longest facade in town.
- **"Every street must terminate in something worth walking toward."** No street terminates in
  anything, because no street exists. `hm.road.south` is a bare landmark coordinate with a comment
  quoting this exact rule and no geometry behind it.
- **"Vertical interest every 8–10 m along any street."** There is none, anywhere, because the
  roofscape is bald — see below.
- **"From each entrance of the square, at least two other venues visible."** This one accidentally
  works from the north, and is untestable from the others because the square has no defined
  entrances.

### The roofline is bald, and it is a bug, not a choice

This is the highest-value finding in the review and it is fully diagnosed.

`tools/assetgen/core/kit.py:247` ships a `chimney()` builder whose own docstring reads:
*"A roofline without chimneys reads as a model kit; they are the cheapest possible vertical
interest."* The pipeline agrees with me. It just doesn't work.

- **Pub** (`venues/pub.py:122`): `K.chimney(height=2.9)` translated to `y_e - 0.25`. The roof is
  `gable_roof(D=8.0, ...)` at `pitch=0.88`, so the ridge stands `0.88 × 4.0 = 3.52 m` above the
  eave. The chimney's top, cap and pot included, reaches `y_e + 3.21`. **It is 0.31 m short of
  the ridge and is placed within 0.4 m of the ridge line — so it is emitted entirely inside the
  roof solid.**
- **Inn** (`venues/inn.py:212`): two chimneys at heights 2.6 and 3.0, translated to `y3 - 0.2`,
  under a `pitch=0.92` roof. Same arithmetic, worse margin. Both buried.
- **Blacksmith** (`venues/blacksmith.py:196`): declares the entity `hm.blacksmith.chimney.01`
  with a smoke component and **never calls `K.chimney` at all.** The forge — the venue whose
  entire declared anchor silhouette is *"forge chimney + open work yard"* — has a smoke emitter
  with no stack, and its stone flue hood terminates flush against the underside of the roof.

Net effect: `hearthmere.json` declares four smoke sources; **zero of the four chimneys are
visible in any render.** The town has no vertical elements above its rooflines at all. That is
why the arrival skyline is three flat orange triangles and a grey slab, and why the blacksmith's
roof is the single largest, brightest, emptiest surface in the settlement.

---

## Walking it at the gameplay camera

Unpleasant, mostly because it is boring. The traversal from the gate to the square is forty
seconds of flat grey with no landmark to steer by, no edge to follow, and no reason to look at
anything. The square offers no reason to stop. The shop row is a wall. Only the stalls reward
approach, and only because someone put fish on a board.

Three specific movement problems:

1. **The paving pads are trip hazards to the eye.** Each venue's ground pad ends in a hard raised
   lip against the base plane. At 1.62 m eye height these edges are constantly visible and they
   scream "separate assets placed on a plane."
2. **The guild's porch has broken geometry.** In both `guild-gameplay.png` and
   `guild-approach.png` there is a large pale angular wedge occupying the middle of the porch
   with no plausible reading as architecture. It looks like a mis-transformed plane. It is on the
   hero building, directly in front of the most important interactable in the town.
3. **The guild's doors are shut and its interior is a grey box.** The brief: *"Tall double doors,
   always open ... Interior visible from the door: a stone hall, a reception counter, a big map on
   the wall, weapon racks, adventurers loitering."* Shipped: one closed dark leaf and a flat grey
   wall. The player's "what do I do next" building is sealed and empty.

### The people

21 townsfolk exist and the figure builder is genuinely good — `core/npc.py` builds posed, not
T-posed, at correct §3 proportions, with a real children-are-not-small-adults rule. Up close in
the re-shot arrival frame a townsperson reads convincingly. Then:

- **All 21 have rotation `[0,0,0,1]`.** Every person in Hearthmere faces the same direction. The
  four "talk" figures are arranged in pairs 1.1 m apart — and both members of each pair stare
  the same way, side by side, at nothing. This is the "rank of identical mannequins" the
  generator's own docstring says reads worse than an empty street.
- **All 21 are `schedule: "static_v0"`.** The arrival brief requires NPCs *moving*. Nothing moves.
- **No animals.** The briefs ask for a dog under a cart, a cat on the inn windowsill, pigeons in
  the square. There is one cat, at the stalls.

---

## Blind AAA comparison

Against Gridania, Divinity's Reach, and Boralus — **a player would pick this out instantly, in
under a second, and would not need to be told which one it was.**

They would not need to reason about materials or palette. The arrival frame alone gives it away
four separate ways: the placeholder capsule protagonist, the flat empty plane occupying half the
image, the total absence of any foreground framing element, and the fact that nothing in the
picture is bright, saturated, or moving. Gridania opens on a canopy of layered green with light
shafts and a path curving out of frame. Divinity's Reach opens through an arch onto a plaza with
density stacked in three depth planes. Boralus opens on masts, gulls, and a harbour wall. Every
one of them puts something *in front of* the player and something *bright* at the end of the
sightline. This frame does neither.

**Would people play this?** In this state, no — and not because of the art quality of the
buildings, which is further along than the frame suggests. They would not play it because the
first fifteen seconds communicate "unfinished tech demo," and first towns exist precisely to
communicate the opposite.

That said, I want to be accurate about where this actually sits: this is not a hopeless build.
The inn is a real three-storey jettied timber building with dormers and a balcony. The stalls
are legitimately good set dressing. The pub massing is sound. The NPC figure builder is better
than it needs to be. The problem is that **nobody built the town.** Seven venues were built as
isolated objects, individually reviewed as isolated objects, and then placed on an empty plane —
and the entire layer that turns buildings into a settlement was skipped. That layer is a
smaller job than the seven venues were.

---

## Scores

**Acceptance requires no axis < 7 and AAA comparison ≥ 8.**

| Axis | Score | Note |
| --- | --- | --- |
| Silhouette (town skyline) | **3** | Bald roofline; all four chimneys buried inside roof solids; guild "tower" is a flat slab; three identical gables in the arrival frame. |
| Material truth | **4** | Documented crazy-paving anti-reference shipped in three venues; plaster reads as painted card; ground is a texture plane; guild masonry unchamfered at hero distance. |
| Lighting response | **3** | Client rig deviates from the locked §4 values on four of five lights; focal region is darker than frame mean; forge emissive lights nothing; no lit windows anywhere. |
| Detail hierarchy / density layering | **3** | One density everywhere and it is low. 40 m of nothing at the arrival. Three empty shops. Only the stalls layer correctly. |
| Wear & story | **4** | Good at the stalls, near-absent elsewhere. No dished threshold, no ground splash, no interrupted work. |
| Life & residue | **3** | 21 people all facing the same way, none moving, no animals, no interior light, no laundry, no smoke until this week. |
| Cohesion (one culture) | **4** | Same kit, drifted values: plaster off its own primary town-wide, terracotta hot, cottage roofs an undocumented off-palette thatch, guild stone a foreign family. |
| Scale truth | **6** | Component scale is broadly correct. The square and the gate approach are sized for a city, not for three hundred people, which reads as emptiness. |
| Sightlines & navigation | **2** | The arrival composition fails five of its seven written requirements. Streets are authored data that nothing consumes. No street terminates in anything. |
| **AAA comparison** | **2** | Identified as amateur in under a second, on the arrival frame, by four independent tells. |

Every axis below 7. AAA comparison at 2 against a bar of 8.

---

## Verdict

`REJECT` — scoped to the town layer.

This is not a "fix the enumerated defects and resubmit" situation, which is what `REVISE` means.
The composition of the arrival frame and the ground/street layer beneath the whole settlement are
fundamentally not built, and the protocol is explicit that composition-level failure is `REJECT`:
build the missing layer, do not patch the venues around it.

Scoping, so this is actionable rather than just a rejection:

- **`REJECT`** — the town assembly layer: ground, streets, gate, arrival composition, lighting rig
  parity between client and review harness. Build it; it does not currently exist.
- **`REVISE`** — guild (unchamfered machine masonry, sealed doors, empty interior, porch geometry
  artifact, slab tower), blacksmith (no chimney geometry, forge emissive does no lighting work,
  wrong floor material), shop row (>12 m undifferentiated facade, three identical shops, empty
  counters), market square (empty, black-void fountain basin, oil-slick desire path), cottage
  (off-palette thatch, crazy-paving walls), inn and pub (buried chimneys, dead windows).
- **Hold** — stalls. Do not touch these. They are the only part of the build that is working, and
  they are the reference for what the rest of the town's residue pass should look like.

Per `REVIEW_PROTOCOL.md`, the cohesion critic may send individually-accepted venues back. Six of
seven go back.

One process note, offered as diagnosis rather than criticism of any one agent: every venue passed
its own review, and the town failed. That is exactly the failure mode the protocol's cohesion
gate exists to catch, so the process worked — but it caught it late, because the arrival frame
was never rendered at the locked lighting and never checked against its own brief until now. The
arrival shot should be re-rendered on every venue merge, not once at the end.

---

## What is working — preserve this

Do not let a `REJECT` verdict destroy the parts that are genuinely ahead.

1. **The stalls.** The best work in the build by a wide margin. Fish laid out on wet boards,
   crates of produce, spilled tomatoes on the ground, a leaning cartwheel, a broom left against a
   post, a cat, and chalk tally marks on a slate — which is both perfect residue *and* a correct
   §2-compliant solution to "no readable lettering." This is shipped-game set dressing.
2. **The inn's massing.** Three storeys, double jetty, correct dormers, a balcony, a proper stone
   plinth. The silhouette is right and the proportions are right. It needs light in its windows
   and its chimneys unburied, not a rebuild.
3. **The NPC figure builder.** `core/npc.py` is better than the job required — posed rather than
   T-posed, correct §3 proportions, and a genuinely thoughtful children-at-0.62-scale-with-larger-
   heads rule. It needs a yaw value, not a rewrite.
4. **The kit discipline.** One shared core owns doors, windows, shutters, roofs and chimneys, and
   the venues use it rather than reimplementing. This is why the fixes below are cheap: the
   chimney bug is one arithmetic error in one shared function's callers, not seven separate
   problems. The architecture is sound; the values running through it are not.
5. **The pub's exterior life.** Trestle tables, benches, mugs left on the boards, casks by the
   wall. Second-best residue in the town.
6. **The self-awareness in the codebase.** `kit.py:247` knows a roofline without chimneys reads as
   a model kit. `npc.py` knows an empty town reads as a diorama. `REFERENCES.md` knows flat ground
   kills a shot. The documentation diagnosed every one of the top defects in this review before I
   did. The gap is between what the docs know and what the renders show — which is a much better
   problem to have than not knowing.

---

## Top defects, ranked by impact per unit of effort

1. **Ford Road does not exist — build the street layer from the data already authored.**
   `content/town/hearthmere.json:250` defines all three streets with paths, widths, surfaces and
   wear notes, and no code reads `streets[]`. Extend `tools/assetgen/core/` with a street builder
   that consumes it: a 7 m cobbled band down the Ford Road path with a worn centre trough, a
   material change where it meets the square, kerbs, and cinder past Smith's Lane's midpoint.
   Cobble cells at the §3 spec of 0.12–0.22 m, not the current 0.4–0.8 m voronoi. This converts
   52% of the arrival frame from dead grey into the element that tells the player where to walk,
   and it kills the "flat ground" anti-reference town-wide. The data is written; only the
   consumer is missing.

2. **Unbury the four chimneys.** `pub.py:122`, `inn.py:213`, and add the missing `K.chimney` call
   in `blacksmith.py:196`. Derive height from the ridge (`pitch × span/2 + freeboard`), not from
   the eave — currently the pub's stack is 0.31 m short of its own ridge and is emitted inside the
   roof solid. Roughly ten lines. It restores vertical interest to every roofline in town, gives
   the blacksmith the anchor silhouette its brief demands, and activates four smoke emitters that
   are already configured in `ambient.smoke.sources` and already work. Highest ratio in the review.

3. **Build the north gate.** `hm.gate.north` is a declared landmark at `(0,0,-46)` with a comment
   describing the framing it should provide and no geometry. One kit function — arch, timber
   gates, a heron keystone per the emblem canon. It gives the arrival frame the foreground
   framing element it completely lacks, a scale cue, and the "you have arrived" beat. Single
   largest composition gain per unit of effort in the build.

4. **Give the town a yaw and a lit window.** Two independent one-liners with town-wide effect:
   (a) every one of the 21 townsfolk has rotation `[0,0,0,1]` — yaw them to face what they are
   doing, so talk pairs face each other and workers face their benches; (b) no window in
   Hearthmere is lit — add the §4 `#FFD9A0` window spill at 2.2 to the inn and pub interiors, and
   make the forge emissive actually light the hood, anvil and posts around it at the specified
   4.0. The inn brief's "most inviting thing in the frame" currently reads as abandoned, and the
   arrival frame contains nothing bright at the end of its sightline. Largest life-per-line-of-code
   in the review.

5. **Re-lock the palette and kill the crazy-paving.** Three related value fixes:
   (a) plaster ships at `#C8BEA9` town-wide against a locked primary of `#E8DCC4` — the base value
   of the settlement is wrong everywhere, and correcting it warms the entire town at a stroke;
   (b) terracotta ships hot at `#BE673C` against `#B5603E`, with the `#8F4E36` aged variant absent
   from the specified ~30% of tiles; (c) the voronoi cell size that produces crazy-paving on the
   cottage walls, smithy floor and square paving is the exact defect written down as an
   anti-reference in `REFERENCES.md`. Then either bring the cottage roofs onto the §4 palette or
   record thatch in `docs/DECISIONS.md` — currently it is an undocumented third roof material on
   the venue whose entire job is to make the place feel like a town.

**Also required before re-review, lower ratio but non-negotiable:**

6. Bring `client/src/main.js` lighting onto the §4 locked rig — hemisphere `#93BEE8`/`#7A6A52`
   at 1.1, rim at 1.4, and delete the undeclared `#C9A87E` bounce. The arrival frame currently
   does not match the venue renders because it is not lit like them.
7. Chamfer the guild masonry (§6, 15 mm architectural) and break its perfectly repeating bond;
   open its doors; dress its interior; and find out what the pale wedge in the porch is.
8. Break the shop row facade — it exceeds the §7 12 m limit by double — and differentiate the
   three shops per their briefs. Their counters are empty.
9. Replace the placeholder player capsule before anyone outside the team sees the arrival frame.
10. Reconcile `WORLD_BIBLE.md:108` with `hearthmere.json:352`. They specify opposite compositions
    for the most important frame in the project.

---

## Re-review criteria

I will re-review the town when the arrival frame, re-rendered at the locked 09:30 rig from the
client, shows: a gate framing the shot, a legible road leading to a fountain that is the
brightest thing in the mid-distance, at least three chimneys smoking above the roofline, lit
windows in the inn, and people facing different directions. That is the bar for `REVISE`.
`ACCEPT` requires the blind comparison to hold, and it is a long way from holding today.
