# Documentation audit — art director (fresh eyes) — round 01

Date: 2026-08-02 · Reviewer: independent agent with no project context, briefed
as a veteran AAA MMO environment art director. Commissioned by the owner.
Preserved verbatim. Dispositions: `docs-audit-synthesis-01.md`. Decision: D-070.

---

**Verdict: DO NOT SIGN OFF.** This is a genuinely unusual document set — the plan reasons from cause, the sightline math actually checks out, and §7 of the Art Bible is better than most shipped bibles. But it is a *town planning* document set wearing an art bible's hat. The things that actually make 94 buildings by 94 different hands look like one town — colour management, a pattern book, a colour script, water and sky, reference imagery — are either absent or filed in an engineering doc that sits outside the precedence chain. Below, most severe first.

### 1. [WRONG] CRITICAL — The sun is in the north-east, and the palette says north faces are the shadowed ones
`ART_BIBLE.md` §4 ("Sun elevation 38°, azimuth 125°") vs §4 Architecture table ("Lime plaster (shadowed variant) — *For north faces and recesses*"). The shipped rig computes `(cos el·sin az, sin el, cos el·cos az)` = **(+0.645, +0.616, −0.452)** — +X, −Z, i.e. **east and north**, confirmed by `TOWN_PLAN.md` §7.1 and by `tools/render/viewer.html:172` ("azimuth 125° lights exactly those −Z faces" — −Z is north).
**Why it matters:** every artist authoring a facade has two contradictory instructions about which elevation is lit, and every "which faces are lit at 09:30" argument in the World Bible and Town Plan rests on a sun position the Art Bible's own palette denies.
**Fix:** state the sun as a world-space unit vector in the Art Bible next to the azimuth, and either re-key the palette's shadow variants to south/west faces or move the sun to a compass position that matches them.

### 2. [UNCLEAR] CRITICAL — "Azimuth 125°" has no stated convention, and it is not the compass convention
`ART_BIBLE.md` §4; `content/town/hearthmere.json` → `lighting.sunAzimuthDeg`. The code's formula makes 0° = **south**, 90° = east, 180° = north — so the true compass azimuth is 55°, a 70° error for anyone who types 125 into a sun position. `tools/assetgen/venues/church.py:158` literally carries the comment "*guessed:*".
**Why it matters:** `CLAUDE.md` hard constraint 1 and `ENGINE_PORTING.md` exist to make the Unreal/Unity port free, and the first thing a porter does is enter the sun azimuth — at which point every shadow in Hearthmere rotates 70° and the arrival frame's "every facade in the frame is a lit one" premise collapses.
**Fix:** one line in §4: "azimuth measured clockwise from +Z (south); compass equivalent 55°; world direction-to-sun (0.645, 0.616, −0.452)."

### 3. [MISSING] CRITICAL — No colour management. The "locked palette" is not lockable as written
`ART_BIBLE.md` §4: "Hex values are **linear-space authoring targets in sRGB notation**" — that phrase is self-contradictory (an sRGB hex is gamma-encoded by definition). There is no tonemapper, no exposure, and no grade in the Art Bible; `exposure: 1.05` exists only in the JSON, and ACES + the colour-grade LUT — described in `ARCHITECTURE.md` §5 as "**where the anime look is finalized**" — live in a document `PROMPT.md` §3 places *outside the precedence chain*.
**Why it matters:** `#E8DCC4` means three different colours depending on whether you gamma-decode it, and none of them is what reaches the screen after ACES and a warm-midtone lift — so "palette-compliant per §4" in the §8 checklist is unverifiable and every builder will land somewhere different.
**Fix:** declare in §4 that hexes are sRGB-encoded authoring values, decoded to linear on import, and pull exposure, tonemapper and the grade's intent into the Art Bible as law with ARCHITECTURE holding only the implementation.

### 4. [WRONG] CRITICAL — The metals table is physically impossible at metalness 1.0, and the code already knows it
`ART_BIBLE.md` §4 Metals ("Wrought iron `#3A3632`, metalness 1.0") and §5 ("Metalness — binary in practice, 0.0 or 1.0"). `#3A3632` is ~4% reflectance; real iron is ~56%. `tools/assetgen/core/materials.py:1670` deviates in silence: "*a fully-metallic surface at #3A3632 … renders as a black cutout*", shipping `metalness 0.55`; lead ships 0.9, flashings 0.45.
**Why it matters:** the law as written produces exactly the "**Black metal**" entry in `REFERENCES.md`'s own anti-reference list, so the pipeline is already off-book with no recorded decision — which is the drift `PROMPT.md` §4 rule 8 was written to prevent.
**Fix:** re-author the metals as F0 reflectance values (iron ≈ `#8E8E8D`, bronze ≈ `#F0C0A0`, brass ≈ `#E8C88A`), move the current dark hexes to a "painted/limed ironwork" dielectric row, and record the fractional-metalness exception.

### 5. [MISSING] CRITICAL — There is no architectural pattern book, and no building in the plan has a ridge height
`ART_BIBLE.md` §1 "The architectural idiom" and §3 scale table; `TOWN_PLAN.md` §6 schedule (columns `st | eaves | ridge`, where `ridge` is *orientation*, not height). Grep confirms the word "pitch" appears nowhere in the Art Bible or any area doc; "jettied" appears with no dimension.
**Why it matters:** roof mass is 40–60% of every street elevation and the whole of §7.2's "best whole-town view in the build", and it is currently undefined — two builders handed adjacent plots will produce a 35° and a 55° roof and both will pass §8. The one derivable pitch in the docs (church, 20 m span, eaves 9.0, ridge 14.6) is ~29°, which is not "steeply pitched" by any Tudor measure.
**Fix:** add a §1 pattern book with hard ranges — roof pitch by covering (thatch 50–55°, tile 45–50°, slate 38–42°), eaves overhang, verge detail, jetty depth, post bay spacing, window light/mullion module, door module — and add a `ridge` height column to the generated schedule.

### 6. [WRONG] CRITICAL — The most important composition in the build depends on content that is out of scope and unreportable
`TOWN_PLAN.md` §7.1 item 3: "Traffic crosses the composition at right angles: **carts, a dog, someone with a yoke. Movement across a static frame is what stops it reading as a painting.**" `BUILD_DIRECTIVE.md` §1 and `PROMPT.md` §6 remove NPCs and defer "anything that moves on the roads"; `REVIEW_PROTOCOL.md` "Scoped exceptions" says "**Do not report character findings at all**".
**Why it matters:** the arrival frame is required to get its own ACCEPT (`PROMPT.md` §8), its author has stated the thing that makes it work, that thing is banned, and the critic is forbidden from naming the resulting deadness — a guaranteed unresolvable review loop at exactly the frame the game opens on.
**Fix:** either bring a minimal ambient-life pass into v2 scope by decision entry, or rewrite §7.1 item 3 to specify a static substitute (a parked cart, a tethered mule, laundry crossing the gap) and delete the "movement" claim.

### 7. [MISSING] CRITICAL — `REFERENCES.md` contains no references
`REFERENCES.md` opens "The blind comparison bar … needs **specific reference points**" and then delivers only prose. There is not one image in the repo except `hearthmere-plan.svg`; there is no shot list, no colour key, no paint-over, no capture directory. `REVIEW_PROTOCOL.md` step 2 mandates "**Put the render next to the AAA reference described in `docs/REFERENCES.md`**" — an instruction that cannot be executed.
**Why it matters:** the entire quality gate is a side-by-side that no reviewer can actually perform, so "AAA comparison ≥ 8" is being scored from memory, which is precisely the failure `PROMPT.md` §4 rule 1 exists to stop.
**Fix:** land a `docs/refs/` set — 10–15 captures per anchor, at the gameplay camera, tagged by what each proves (silhouette, material read, density hierarchy, light) — and make step 2 name specific files.

### 8. [WRONG] CRITICAL — The single strongest anime tell is specified three different ways
`ART_BIBLE.md` §1 tell 1 ("Implemented as a directional light… **Until a Fresnel term exists, the rim is deliberately desaturated and reduced**") vs `ARCHITECTURE.md` §5 Lighting ("**Screen-space rim pass** for the anime separation signature") vs `content/town/hearthmere.json` (still a directional).
**Why it matters:** §1 calls rim "the single strongest anime-3D signature" and then deliberately weakens it on the grounds that a proper rim does not exist — while the architecture doc says it does; the town's defining stylistic feature is therefore being suppressed for a possibly-stale reason nobody has reconciled.
**Fix:** resolve which rim ships, record it, and if the screen-space pass is real, restore the rim's saturation and intensity in §4 and re-shoot the reference swatches.

### 9. [MISSING] CRITICAL — No water direction, in a lake town at a ford
`ART_BIBLE.md` §4 palette (no water colour), §5 (no water material), §7 ("Water: fountain, troughs — flowing normal maps, ripples"). The world contains the Emberflow, the Mere, a dredged harbour basin at −5.35, a bridge, a silted ford, a slipway, a mill wheel and a quay stair whose "bottom four treads are always wet".
**Why it matters:** cobblestone gets two hex values and a wetness rule while the largest single surface in the north half of the town gets one line — so water colour, depth absorption, transparency, shoreline foam, the wet/dry waterline transition, reflection method and the mere's read at distance will each be invented per venue.
**Fix:** add a §4 water sub-palette and a §5 water standard (shallow/deep absorption tint, waterline wetness band width, foam/algae rules, reflection budget), plus a wet-material rule for anything within 0.5 m of the surface.

### 10. [MISSING] CRITICAL — No colour script. Eight causally distinct districts share one flat palette
`TOWN_PLAN.md` §2 defines eight districts by cause (fire, smell, water, status, poverty) with explicit residue guidance; `ART_BIBLE.md` §4 gives one town-wide list with no district modulation, no value key, and no colour-dominance ratio.
**Why it matters:** a builder on Kirk Knowe and a builder in the West Lanes will produce visually identical buildings from identical hexes, erasing the plan's best idea — and with no ratio rule, a building that is 80% guild crimson is "palette-compliant".
**Fix:** add a §4 colour script — per district, a value range, a temperature offset, a soot/bleach/damp bias and a permitted accent set — plus a dominance ratio rule, and give filler buildings a defined shutter/door accent family (currently only seven accents exist for 94 masses).

### 11. [WRONG] MAJOR — Ten-plus scheduled masses break §7's 12 m facade rule, and nothing checks it
`ART_BIBLE.md` §7: "No wall of undifferentiated facade longer than 12 m without a break." `TOWN_PLAN.md` §6: bede houses 24.0 m, rope house 24.0 m, blacksmith 18.0, inn 16.0, guild 16.0, stables 16.0, carpenter 14.0, waggon shed 14.0, warehouse_a 14.0, tithe barn 13.0, moot hall 13.0 — with no break recorded on any row and no checker assertion.
**Why it matters:** the rope house alone is a 24 m unbroken wall on the Quayside, which is the failure mode §7 was written to prevent, and the plan hands the builder a footprint that cannot satisfy the law it is built under.
**Fix:** add a `breaks` column to the schedule for any mass over 12 m naming the recess/projection/material change, and add the assertion to `townplan.py --check`.

### 12. [WRONG] MAJOR — Kirkgate has three different gradients and both has and does not have steps
`TOWN_PLAN.md` §3 "How the fall is taken up" — "**No steps: a steady 3.0% for 41 m** … **Ends at the churchyard's north gate and six steps.**" §4 generated table — falls −1.85 to +0.00, **4.5%**. §4 street note — "Climbs **2.0 m** over its length at a steady **4%**."
**Why it matters:** Kirkgate is the coffin route and the Water-Gate-to-church link, its whole justification is a gradient a bearer can manage, and a builder gets three incompatible numbers plus a contradiction about whether steps exist — in the same document.
**Fix:** delete the hand-written gradients from §3 and §4's notes, cite the generated table, and state the six steps as a terminal feature outside the run.

### 13. [WRONG] MAJOR — The wharf's lower stage is 0.6 m under the town's only water surface
`TOWN_PLAN.md` §3 levels table: "wharf lower stage (64.8, −68.9) **−3.70**" against "Emberflow / Mere surface **−3.10**". `WORLD_BIBLE.md` says the lower stage is at **−2.85**. `Fishers' Steps` is a further three-way conflict: the generated table says 6 m at **0.0%**, its own note says "**9 risers of 0.155 m taking the 1.4 m**", and the World Bible says it joins the wharf deck to the lower stage (the Town Plan says it climbs to the Rope Walk terrace).
**Why it matters:** D-024 established exactly one water elevation, so a "low water stage" is conceptually void and the number as published puts an authored deck permanently submerged — this is the quay's hero silhouette area and it will be built underwater.
**Fix:** delete the lower stage or raise it above −3.10, and pick one function and one rise for Fishers' Steps.

### 14. [WRONG] MAJOR — Hand-written prose still carries numbers the generated tables have moved
Examples: Ford Road — §3 "2.5% mean … 4.9 m over its length" vs §4 generated "2.3%, −2.25 to +2.18" (4.43 m). Wall — §1 "5.2 m to the walk" vs §5 generated "6.0 m to the wall-walk". Church — `WORLD_BIBLE.md` "14.6 m to the ridge" vs `ARCHITECTURE.md` §5 "the church nave at 12.2 m to the ridge" (interior/exterior never distinguished). Bridge — J1 says open water begins ~z −86.6, while the levels table puts the deck crown at z −86 over terrain at −5.60, i.e. 2.5 m of water.
**Why it matters:** the whole point of the `BEGIN GENERATED` architecture is that prose cannot drift from data, and the prose around the tables has drifted anyway — so a builder cannot tell which number is authoritative without reading the generator.
**Fix:** strip every restated dimension from §§1, 3 and 5 prose down to a pointer at the generated block, and add a doc-lint that fails on a number in prose that also exists in a generated table.

### 15. [WRONG] MAJOR — The church is not the tallest building in Hearthmere
`WORLD_BIBLE.md` Church brief: tower "parapet 18.4 m, lead spirelet to **21.4 m**: the tallest thing in Hearthmere **by a tenth of a metre over the guild**". Guild brief, same document: "parapet 18.6 m, pyramid roof and iron finial to **21.5 m**". `TOWN_PLAN.md` §7.1 item 7 then calls the guild tower "the tallest thing in the frame".
**Why it matters:** the height rivalry between church and guild is a stated piece of the town's founding logic and the two hero silhouettes are being built against an inverted claim.
**Fix:** pick the winner, put both heights in the generated schedule as a `ridge`/`apex` column, and delete the prose numbers.

### 16. [WRONG] MAJOR — The blacksmith's placement rationale contradicts the wind vector
`TOWN_PLAN.md` §2 sets `ambient.wind = [0.82, 0, 0.57]` travelling **east-south-east**, and then justifies Smithward with "the wind carrying sparks out over the tenter ground and the wall rather than across roofs". The blacksmith is at (−33, +51); ESE of it lies the charcoal store, shed_b, the south gate ward's cottage and the smith's house. The tenter ground (≈ −30, +30) is **upwind** — and it is where cloth is hung to dry.
**Why it matters:** §2 is explicitly the document that tells a builder what residue belongs where, and its most-cited causal rule is wrong for the town's only significant fire source.
**Fix:** either move the forge east of Ford Road or restate the rationale honestly, and mark the downwind cottages for soot in their briefs.

### 17. [WRONG] MAJOR — Hero/secondary classification disagrees across three governing documents
`PROMPT.md` §6d lists "quay and crane, **moot hall, watermill, bakery**" as hero venues; `BUILD_DIRECTIVE.md` §5 lists all three under "**Secondary venues** (authored, **lighter review**)"; `TOWN_PLAN.md` §6 marks moot hall `secondary`. The moot hall's bell-cote is simultaneously one of the five checker-proven anchors of the arrival frame.
**Why it matters:** "lighter review" on a load-bearing anchor of the most important composition in the build is how a mediocre silhouette reaches the frame that opens the game.
**Fix:** promote any mass named in §7.1 or §7.2 to hero tier automatically, and make the schedule's `role` column the single source.

### 18. [MISSING] MAJOR — The LOD chain is never held to the silhouette standard, and the review renders don't see it
`ART_BIBLE.md` §1 ("readable at 100 m"), §6 ("LOD3 @ 6% / impostor (100 m+)"), and `ARCHITECTURE.md` §5, where the Art Bible's distances turn out to be only the High/Ultra tier. Nothing states what a LOD may not lose, whether 15 mm chamfers survive decimation, whether normal maps persist, or how transitions are blended.
**Why it matters:** §7.2 calls the south gate "the best whole-town view in the build" and its content sits at 80–155 m — entirely LOD3 and impostors — while every ACCEPT is granted on a LOD0 render, so the town that ships is not the town that was reviewed.
**Fix:** add a §6 LOD visual standard and require one LOD2/impostor render in every review packet.

### 19. [MISSING] MAJOR — No emissive or night-lighting standard, and the emissive vocabulary is judged only at 09:30
`ART_BIBLE.md` §4 Lighting (forge 4.0, candle 1.8, window spill 2.2 — intensities with no unit, no exposure reference, no bloom threshold), §8 ("Reviewed at the locked 09:30 lighting setup"). The world briefs are saturated with emissive intent: "warm light in every window", "**firelight, not daylight, defines it**" (the pub), lamp brackets, the Ferryman's Lamp itself.
**Why it matters:** every emissive value in the town is being tuned against a mid-morning key that washes them out, and the pub — a hero venue whose entire identity is firelight — cannot be judged at the only lighting condition the protocol permits.
**Fix:** define emissive in physical units against the locked exposure and bloom threshold, and grant the pub and forge interiors a declared night/interior review condition by decision entry.

### 20. [MISSING] MAJOR — Material channel policy and per-venue material budgets are absent, and the pipeline has already diverged
`ART_BIBLE.md` §5 requires five separate maps; `tools/assetgen/core/materials.py:395` ships channel-packed ORM. No document states texture format/compression, resolution caps, atlas membership, or a per-venue material or draw-call allowance against §7's `< 900` draw calls.
**Why it matters:** 900 draw calls across 94 masses is under 10 per building before street furniture, water, VFX and the wall — with no budget issued per venue, the overrun is discovered by the perf gate *after* the art is authored.
**Fix:** state ORM packing and colour space per channel in §5, cap unique materials per venue and district, name the compression format, and publish a per-venue allowance in `BUILD_DIRECTIVE.md` §7.

### 21. [COHESION] MAJOR — Nothing in a review render proves two builders rendered at the same exposure
With ACES, a grade LUT, `exposure: 1.05` and per-tier bloom all in play, two venues shot in the same harness can still be compared with no calibration evidence in frame.
**Why it matters:** cohesion drift in a fan-out-per-venue pipeline shows up as small cumulative value and temperature offsets no per-venue critic can detect.
**Fix:** mandate a calibration strip in every review render — 18% grey sphere, chrome sphere, a §4 palette chip row and the 1.75 m figure — and make a missing strip an automatic REVISE.

### 22. [COHESION] MAJOR — The arrival frame's checker cannot see the things most likely to break the arrival frame
`TOWN_PLAN.md` §7.1 proves items 4–8 are not blocked by any of the other **93 masses** — but §8 explicitly declines to decide the market cross's siting, the 14 stalls, street furniture, props, and **vegetation**. Item 5 of the frame *is* the market cross.
**Why it matters:** the frame is machine-proved against buildings and unprotected against a stall awning, a lamp bracket, a market cross or a single tree on Kirk Green.
**Fix:** extend the cone assertion to every placed object with a bounding volume, and register the market cross as a scheduled mass.

### 23. [UNCLEAR] MAJOR — The scale standard is a modern building code applied to a pre-industrial town
`ART_BIBLE.md` §3 ("Door opening 2.10 m × 0.95 m … Interior floor-to-ceiling 2.70 m") against §1's Tudor idiom and the pub brief ("**Heavy low beams**, small windows").
**Why it matters:** a 2.10 m door head and a 2.70 m ceiling are modern dimensions; Tudor vernacular runs 1.75–1.95 m and 2.0–2.3 m — the law as written makes every cottage read as a modern house and makes the pub's stated identity illegal.
**Fix:** split the table into gameplay minimums and vernacular dimensions, and grant the pub its low beams explicitly.

### 24. [UNCLEAR] MAJOR — Nine scoring axes with no calibration, one axis that cannot be scored, and a stated bias
`REVIEW_PROTOCOL.md`: nothing anchors a 6 against a 7 against an 8; "**Cohesion** — consistent with neighbours" is scored by a per-venue critic who has seen no neighbours; and "A first-pass ACCEPT usually means the critic was not looking hard enough" instructs the instrument to find defects.
**Why it matters:** with acceptance gated on "no axis < 7" the difference between shipping and a fifth iteration is one uncalibrated judgement, and a critic told what the right answer is will produce it.
**Fix:** anchor each axis with named reference images, replace per-venue Cohesion with a pattern-book conformance check, and delete the first-pass bias sentence.

### 25. [MISSING] MAJOR — Pictorial signage is doing all the wayfinding and has no style sheet
With lettering banned, an icon on a bracket is the *only* thing that tells a player which door is the apothecary — and there is no rule for icon silhouette style, sign size, bracket family, mounting height or how a sign reads at 100 m, so 94 buildings will get 94 sign languages.
**Fix:** ship a signage standard in §1 — one bracket family with three variants, fixed board sizes, a silhouette-first icon rule (readable in black-on-white at 30 m), and a mounting height tied to §3's 2.20 m awning clearance.

### 26. [WRONG] MINOR — The World Bible carries features and counts the Town Plan deleted
"Ninety-four building masses stand inside — and four just outside" (Town Plan: 94 total, 90 inside); the mill leat is deleted by D-024 yet still cited in `TOWN_PLAN.md` §2 and the Mill Postern row; the hand-maintained ASCII map puts the fountain — the world origin, at the grid centre — visibly west of centre.
*Fix:* generate the ASCII map and counts from `plan_data.py`, and grep-sweep "leat".

### 27. [WRONG] MINOR — "Every building has at least one element that is visibly *wrong*" is itself a uniformity
Applied across 94 masses it becomes the recognisable "one wonky thing per house" tell, and it makes the deliberately-alien guild sag like a cottage.
*Fix:* make it a rate (roughly 70% of domestic masses, 0% of the guild) tied to district age and wealth.

### 28. [MISSING] MINOR — No aging vocabulary, and the ground-contact band is too shallow
§5 gives five excellent wear *mechanisms* and no *quantity* — nothing maps the World Bible's rich age story onto a wear index, so "physically motivated" passes both a pristine and a derelict version of the same cottage. "The bottom 0.15 m of every wall gets splash dirt" is about a third of real rain splash-back.
*Fix:* add a 0–5 wear index with per-district and per-age defaults, and raise the splash band to 0.35–0.5 m.

### 29. [MISSING] MINOR — The wind vector never reaches the motion rules, and only four chimneys smoke
§7 specifies frequencies but no direction while `ambient.wind` exists; `ambient.smoke.sources` lists four chimneys against a town of tall chimneys, the bakery flue, and a south-gate frame sold on "the fire quarter's chimneys".
*Fix:* cite `ambient.wind` in §7 as binding, and generate the smoke source list from the schedule.

### 30. [COHESION] MINOR — The look is being locked in a renderer that is not the product's renderer
The bar, palette, rim, grade and every ACCEPT are established in the three.js harness while CLAUDE.md constraint 1 targets Unreal/Unity. Nothing declares the harness the reference renderer or states what must match after the port.
*Fix:* declare the harness authoritative for the *look* and publish a port-parity checklist with a required side-by-side before any engine migration.

---

### What is genuinely good, so it survives the rewrite
The causal reasoning in `TOWN_PLAN.md` §§1–2 and the "how the fall is taken up" table are better than most shipped world bibles — the town is *derived*, not decorated. The arrival-frame math in §7.1 checks out when recomputed, and machine-proving a composition is a technique I have not seen a studio do and would steal. §7's residue doctrine and §5's roughness rule are correct and well-argued. §9 "Known weaknesses" is honest in a way documentation almost never is.

**The through-line:** this document set governs *where things are* to two decimal places and *what things look like* by adjective. Findings 3, 5, 9, 10 and 25 are the ones to fix before another asset is generated — colour management, a pattern book, a colour script, water, and a sign language. Without those five, a hundred individually-passing venues will still fail the cohesion review, and you will not be able to say why.
