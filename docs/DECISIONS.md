# Decisions

Recorded deviations, and the reasoning. Art Bible changes require an entry here.

---

## D-001 — Engine target: portable glTF assets + WebGL harness

**Context.** Unity and Unreal downloads are blocked by the environment's
network policy (403 at the CDN and at `EpicGames/UnrealEngine`), and available
disk (~30 GB) is below a usable UE5 install regardless. Neither engine could be
installed or run here.

**Decision.** Author the town as engine-neutral **glTF 2.0 + PBR texture sets**,
with a three.js render harness for verification and a UE5 project scaffold that
imports the same assets.

**Why.** The art-director iteration loop the project is built around requires
that agents can *see* their work. Authoring a UE5 project blind would produce
code referencing assets that do not exist, with no way to verify anything looks
right. glTF imports natively into both engines with no transform fixup, so the
expensive part — the assets — stays portable.

**Cost.** The three.js client is a reference implementation, not a shipping
Unreal build. Engine-specific features (Nanite, Lumen, VSM) are unavailable.

---

## D-002 — MMO seams established up front, netcode deferred

**Context.** Scope is visual fidelity first, but the user asked that MMO systems
not require a later rewrite.

**Decision.** Lock four architectural seams now — authoritative JSON content,
stable entity IDs, 16 m spatial cells, and intent-based interactions — while
deferring actual networking. See `docs/ARCHITECTURE.md`.

**Why.** The expensive retrofit is not netcode; it is discovering the world was
built as client-side scenery with no entity identity and no spatial structure.
These four cost little now and are painful to add later.

---

## D-003 — Principal facades face −Z

**Context.** The locked 09:30 sun (azimuth 125°) lights −Z-facing surfaces. The
first render pass viewed assets from +Z and judged every one on its shadowed
back — a warm cream wall measured as blue-grey.

**Decision.** Every venue is authored with its principal facade toward −Z, and
review cameras sit on that side.

**Why.** It matches the town plan (the player arrives through the north gate
and sees −Z faces) and guarantees review renders show lit material.

---

## D-004 — Wrought iron authored below full metalness

**Context.** Physically, iron is a metal (metalness 1.0). At 1.0 the albedo is
ignored and the surface renders purely from environment reflection; under the
software-rasterised environment used here it collapsed to a flat black cutout,
losing all hammer-facet detail.

**Decision.** Author wrought iron at metalness 0.55 with a lifted albedo.

**Why.** Aged iron genuinely carries scale and oxide that scatter diffusely, so
this is defensible physically as well as practically. The form reads in all
lighting. **Revisit** if the project moves to an engine with a stronger IBL —
this is a compensation, and it is the kind of thing that should not silently
persist.

---

## D-005 — World-position wear is not baked into tiling materials

**Context.** `ground_splash` and `water_streak` were applied inside tiling
material builders. Because the texture tiles across a wall, a "bottom 15 cm of
the wall" dirt band repeated at every tile seam.

**Decision.** Tiling materials carry only position-independent wear. Ground
splash and streaking are applied per-vertex at assembly time.

**Status.** The helpers still exist on `MaterialSet` for non-tiling use, but
per-vertex application is **not yet wired through glTF export** (no vertex
colour channel). Listed as a known gap in `docs/ASSET_PIPELINE.md`.

---

## D-006 — Plaza paving is a tiling surface plus scattered proud stones

**Context.** `docs/ART_BIBLE.md` and the market-square brief called for real
per-stone cobble geometry, on the reasoning that a flat textured plane reads as
wallpaper at grazing angles. That is true, but it does not survive contact with
the budget: a 34x32 m plaza at 0.17 m spacing is ~40,000 stones, and at 44 tris
per chamfered stone that is **1.35 M triangles for the paving alone** — against
a 3.5 M budget for the entire frame (Art Bible §6). The first market-square
build did exactly this and consumed the whole frame budget with one venue.

**Decision.** Carry the cobble read in the tiling material, and scatter a few
hundred *proud* stones — tilted, frost-heaved, sunken — where they matter for
silhouette: the fountain surround, kerb edges, and desire paths. ~20 k tris.

**Why.** This is what shipped titles do; nobody models every cobble. The proud
stones supply the grazing-angle silhouette that a bare plane lacks, which was
the legitimate part of the original concern.

**Cost, stated honestly.** At distance the paving still reads flatter than the
Art Bible wants — the normal map mips away and the albedo variance is doing
most of the work (strengthened in D-007). The real fixes are a detail/decal
layer near the camera and per-vertex wear, neither of which is built. This is
a known shortfall, not a solved problem.

---

## D-007 — Cobble albedo carries per-stone variance

**Context.** With paving reduced to a tiling surface, the street read as flat
grey mud past a few metres. Normal-map detail mips away with distance, so it
cannot be what makes a cobbled street legible.

**Decision.** Drive stone-to-stone colour variance from the Worley cell id
rather than smooth noise, so each stone gets its own value and hue rather than
a blur across stones.

**Status.** Improves the near and mid field. The far field is still weaker than
the reference targets in `docs/REFERENCES.md`.

---

## D-008 — Hearthmere is Haven I; design bible updated to match

**Context.** The design bible defines the game as **Evermore**, the
world as **Arkadion**, and settlements as **Havens** with a numerical
designation plus a historical name. Its example register listed
`Haven I: Hearth`. This branch had already been built naming the first town
**Hearthmere**, with entity IDs prefixed `hm.*`.

**Decision.** Keep **Hearthmere** and register it as **Haven I** in the design
bible, replacing the placeholder `Hearth`. Entity IDs stay `hm.*`.

**Why.** The conflict was naming only — the design bible specifies no art
direction, engine, or starting-town detail, so the Art Bible and World Bible
fill a genuine gap rather than contradicting canon. Hearthmere also already
satisfies the canonical naming structure once paired with its numeral, and
`docs/ARCHITECTURE.md` §2 commits to entity IDs never being recycled, so
preserving `hm.*` avoids a rewrite for no functional gain.

**Cost.** The design bible is edited on this branch, so if it is maintained
elsewhere the change needs reconciling with its owner rather than silently
diverging.

**Follow-up.** This is exactly what happened. `main` subsequently restructured
`docs/GAME_DESIGN.md` into a `docs/world/` + `docs/systems/` tree, and because
the restructure was a delete-and-rewrite rather than an edit, git merged both
sides cleanly and the Haven register silently reverted to the placeholder
`Haven I: Hearth`. Re-applied to `docs/world/arkadion.md`, which is now the
canonical location. Worth noting the failure mode: a clean merge is not
evidence that a semantic change survived.


---

## D-009 — The locked lighting rig lives in content, not in the renderers

**Context.** A cohesion review found that `docs/ART_BIBLE.md` §4 specified one
rig, `tools/render/viewer.html` and `client/src/main.js` both hardcoded a
*different* one, and `content/town/hearthmere.json`'s `lighting` block — the
authored copy — had no consumer at all.

Worse, `viewer.html` declared the §4-correct constants near the top under a
comment citing the Art Bible and then never used them. Dead values that make a
file pass inspection are worse than no values.

The consequence is blunt: **§8's "reviewed at the locked 09:30 lighting" had
never been true for any asset in this repo.** Every sign-off to date was made
under an undocumented rig.

**Decision.** `content/town/hearthmere.json.lighting` is the single
authoritative copy; both renderers read it at startup. The Art Bible documents
the values and points at the file.

**Which values won, and why the SPEC moved rather than the rigs.** The values
in the renderers do fix two real defects — shadowed facades reading blue-grey
(the PMREM environment and the hemisphere light double-counting sky) and
cast-shadow regions crushing to near-black — both of which were measured at the
time. Reverting to the §4 numbers would reintroduce them, so the spec was
corrected to match and the two undeclared fills were written into the table.

**Provenance corrected.** An earlier version of this entry said the renderer
values were "deliberately tuned" after the spec was set. A reviewer checked the
history and that is not what happened: `git show ac718cf` shows `ART_BIBLE.md`
and `viewer.html` authored in the SAME foundation commit carrying different
numbers, and `git log -L` shows the rig untouched from then until `2cb6b67`.
The tuning happened inside the foundation working session, before anything was
committed, and the Art Bible was simply never updated to match. So this was not
drift away from a spec — the spec and the implementation **never agreed at any
point in the repository's history**, which is worse, and is why nothing ever
flagged it.

**Still open.** The rim light ships at 1.15 against §1's 1.4, and §1 calls rim
the single strongest anime-3D signature. That value was inherited, not chosen,
and should be re-tested on its merits rather than grandfathered by this entry.

**The generalisable failure.** This is the same shape as `streets[]`: data
authored in `content/`, no consumer, and nothing detects it. Both were found by
review rather than by tooling. A check that flags authored blocks in
`content/` with no reader would have caught both.


---

## D-010 — The rim light, and a governance correction

**The governance point first, because it matters more than the value.**

Commit `2cb6b67` changed `ART_BIBLE.md` §4's rim from 1.4 to 1.15 as part of
reconciling the spec to the shipped rig. D-009 justified that reconciliation
with two measured defects — blue-grey shadowed facades and crushed cast
shadows. **Neither of those arguments reaches the rim light at all.**

So the Art Bible — a document whose own header says it is law and that changes
require a recorded decision — had a number altered to close a review finding,
under a rationale that did not cover it. That is the wrong way round: the
finding should have forced an argument about the rim on its merits, or been
left open. Recording it here rather than quietly leaving it.

**The value, argued on its merits.** §1 calls rim "the single strongest
anime-3D signature", and it is. But the implementation is a *directional
light*, which lights every surface facing it, whereas a true rim affects only
grazing angles. On curved geometry the limb is most of the projected face, so a
strongly saturated blue rim drains colour from every lathed object in the town.

Measured on the guild turret against the ashlar wall beside it:

| | saturation | curve/flat ratio |
| --- | --- | --- |
| `#8FB8E8` @ 1.15 | 0.228 vs 0.447 | 0.51 |
| `#A9C6E2` @ 0.85 | 0.260 vs 0.447 | 0.58 |

Desaturating and reducing the rim recovers curved-surface colour without
touching flat surfaces. **Partial, not solved** — the ratio should be near
1.0, and it is 0.58. The real fix is a shader-side Fresnel term so the rim only
appears at grazing angles, which is a renderer change rather than a value
change and is not done.

**Note on provenance.** This was originally diagnosed as a `M.lathe` UV bug.
That fix (arc-length UVs) was correct on its own terms and is kept, but it was
not the cause: the terracotta turret cap is also a lathe and measures 0.477.
The lathe is exonerated; the rim was always the culprit.


---

## D-011 — NPC fidelity is a scoped exception *(SUPERSEDED by D-012)*

> **Superseded.** The characters were removed from the build entirely. This
> entry is kept for the record and for whoever reopens a character pipeline;
> it is no longer a live scoped exception. See D-012.

**Decision.** Character fidelity is explicitly OUT OF SCOPE for this build.
Reviews must not block acceptance on it.

**What ships.** `core/npc.py` builds posed figures from primitives: capsule
limbs, lathed torsos, sphere heads. No skeletal mesh, no skinning, no faces, no
animation beyond a player walk cycle. They read as people at arrival and
gameplay distance and as mannequins close up.

**Why this is a scope boundary and not a defect.** Fixing it does not mean
better procedural geometry — it means a different discipline: authored
skeletal meshes, skin weights, an animation set, and a retargeting pipeline.
None of that is procedural environment generation, which is what this
repository is. Grinding the primitive figures further would spend effort on
the axis with the lowest ceiling.

**Cost, stated honestly.** Both round-03 reviewers independently flagged
characters as the most conspicuous single element in the arrival frame and as
one of five blind-comparison tells. It costs roughly one point on Life &
residue and depresses the town-level AAA read. Both also concluded it is *not*
what is holding the build back.

**For reviewers.** Score the environment. Report character findings separately
and do not count them against a venue verdict. When the project takes on a
character pipeline, this entry should be reopened rather than deleted.

---

## D-012 — The townsfolk are deleted, not deferred

**Context.** D-011 scoped character fidelity out of review while keeping 21
posed primitive figures in the town. Three cohesion reviews then flagged those
same figures as the most conspicuous element in the arrival frame and as one of
five blind-comparison tells, while the environment around them — 14 building
masses on a flat plane, a main street sealed by a collision box — was the thing
actually failing. `docs/BUILD_DIRECTIVE.md` §1 settles it: NPCs are out of
scope for v2.

**Decision.** Remove the characters from the repository rather than carry them
disabled. Deleted:

- `tools/assetgen/venues/townsfolk.py` — the venue module
- `tools/assetgen/core/npc.py` — the figure builder
- `content/entities/townsfolk.json` — 21 entity records, IDs `hm.townsfolk.*`
- `assets/meshes/townsfolk.gltf` / `.bin` — 28,617 tris
- `review/shots/townsfolk/`
- `skin`, `hair_dark`, `hair_fair` from `core/materials.LIBRARY`, their two
  builder functions, and their nine generated PNGs — character-only materials
  with no other consumer

The `cloth_*` dye family stays: it is a generic textile set, and awnings,
bedrolls, laundry lines and drapes all draw on it.

**Why delete rather than disable.** A disabled generator is a generator nobody
maintains and everybody has to reason about. It would keep costing texture
build time, keep appearing in the venue registry, keep needing an exception in
`validate.py`'s town-wide bounding-box list, and keep inviting a future agent to
"just re-enable townsfolk." The IDs are not recycled either way — `hm.townsfolk.*`
is retired, per the never-reuse rule in Architecture §2.

**Consequences.**

- `hm.townsfolk.*` entity IDs are retired and must never be reissued.
- The v1 arrival brief in `WORLD_BIBLE.md` required "NPCs moving"; that clause
  is struck. Movement in the arrival frame now has to come from cloth, smoke,
  fire, water and vegetation — Art Bible §7 — which is where it should have
  come from anyway.
- The scoped exception in `REVIEW_PROTOCOL.md` is retired with it. Nothing in
  the build is now out of review scope.
- `content/town/hearthmere.json` still carries a `townsfolk` venue entry. That
  file is being rewritten for the v2 grid and the entry goes with the rewrite.

**Cost.** `core/npc.py` was better than the job required — posed rather than
T-posed, seeded variation, derived facing. It is in git history at `d36d31a`
if a character pipeline ever starts. Nothing about that pipeline would reuse
this code, which is the point.

---

## D-013 — Collision is authored geometry, and `surface` is a first-class kind

**Context.** v1 built one `THREE.Box3` per venue from that venue's whole
bounding box and pushed it in as a collider. The `streets` venue spans C1–C6,
so its box sealed the full 96 m of Ford Road; `market_square`'s box sealed the
plaza. The two places the entire town is composed around walking through were
the two places a player could not stand. Nothing caught it, because every venue
was signed off from a render and a render cannot show you that the street is
solid.

The root cause is not that anyone believed bounding boxes were correct. It is
that inferring collision was one line and authoring it was a chore, so the
cheap wrong thing won.

**Decision.** Generators declare collision explicitly, next to the geometry it
belongs to, through `ctx.collider(...)` / `ctx.collider_from(...)` /
`ctx.collider_walls(...)` / `ctx.collider_steps(...)`. `VenueContext.write()`
emits `content/collision/<venue>.json` beside the mesh, schema'd by
`content/schemas/collision.schema.json`. The client loads those files and never
derives collision from anything it renders. Build Directive §6 rule 4 is now
enforced by `tools/validate.py` and proved by `tools/check_walkable.mjs`.

Three shapes — box (with Y rotation), cylinder, convex hull in XZ extruded in
Y. All vertical prisms, because everything in a pre-industrial town is one, and
a 2D containment test is cheap enough to run thousands of times a frame.

**Two kinds, and this is the load-bearing part.** A volume is `solid` (blocks)
or `surface` (offers a standing height only). Roads, plazas, aprons and yard
floors are surfaces. Without that distinction, Ford Road — which is built up
0.10 m proud of the earth, as a made road should be — becomes a continuous
0.10 m kerb-wall the moment the terrain function drops the ground beside it,
and the street is sealed again by a different route. Encoding "this is ground
you walk on" as a first-class authored fact makes that failure unrepresentable.

**Consequences.**

- Every building declares its walls with a doorway gap, and every plinth taller
  than the controller's 0.35 m step declares a flight up to its threshold.
  `ctx.collider_steps` clamps risers so a door can never be visible and
  unreachable.
- Collision is authored in VENUE-LOCAL space and composed with the venue's
  origin and Y rotation, exactly as the mesh is. When the terrain integration
  sets each venue's placement Y, collision follows for free.
- The step height (0.35 m) is a published contract in
  `core/collision.STEP_HEIGHT` and `client/src/collision.js`, not a number
  buried in the controller. Generators author against it.
- `tools/check_walkable.mjs` imports the client's own collision module rather
  than reimplementing it. A prover built on a second copy of the maths proves
  only that the copies agree.

**What this does not do.** Terrain slope is not limited: the ground is walkable
however steep it gets, and only authored volumes obey the step height. That is
the permissive choice, deliberately — an over-strict slope rule can seal a
street, and sealing streets is the failure this exists to end. A slope limit
belongs with the retaining walls it would enforce.

---

## D-014 — Shop Row moved off Ford Road

**Context.** The first run of `tools/check_walkable.mjs` found Ford Road
blocked at z≈28. The shop row terrace is 20.4 m wide and stood at origin x=4,
spanning x∈[−6.2, 14.2] over z∈[20, 28] — straight across a carriageway that
runs down x=0. The main street dead-ended at the back of the general store.

**Decision.** Move it to x=15, spanning x∈[4.8, 25.2], fronting the road from
the east.

**Why here rather than in the v2 rebuild.** Build Directive §3 locks the rule
that nothing may stand on Ford Road's centreline, and the whole point of this
pass is that the town can be walked *today*. A one-number layout fix is cheaper
and more honest than a walkability prover that ships red.

**Consequences.** `cells` updated to D5/E5/F5. The composition of the south end
of the square changes and the v2 layout owns re-siting it properly.

---

## D-015 — The locked palette gains a ground-cover family

**Decision.** Art Bible §4's palette is extended with five ground-cover
colours. They are authored in `core/materials.py` and, unlike every other
deviation recorded here, they are an *addition* rather than a departure:

| Role | Hex | Where |
| --- | --- | --- |
| Meadow turf | `#5E7A3E` | everything outside the wall, and every terrace bank |
| Trodden earth | `#6E5C46` | the ground between buildings inside the wall |
| River shingle | `#8C8272` | scree on unmaintained slopes, the shore |
| Waterline silt | `#4E4033` | the wet margin of the Emberflow and the Mere |
| Open water | `#28453F` | the water surface |

**Why the Art Bible did not have them.** §4 is a palette for *architecture*.
It has eleven building colours, six metals and seven accents, and no ground at
all, because in v1 the ground was a 300 m plane with the blacksmith's yard
texture on it. There was nothing to specify. v2's terrain is by far the largest
surface in the build and it needs a vocabulary.

**Why these values.** Each is picked to sit inside the existing scheme rather
than beside it: the turf green is the §4 herb green `#6B8E4E` dropped in value
and desaturated so a whole hillside of it does not compete with the market
stalls; trodden earth is the existing beaten-earth tone unchanged; shingle sits
between `COBBLE` and `FOUNDATION`; silt is `AO_TINT` cooled; open water is the
only genuinely new hue, and it is `VERDIGRIS` taken far down in value, which is
why `tools/validate.py` reports it as the largest palette drift in the build
(8.6). That drift is this decision.

**What is NOT permitted by this.** These are ground colours. A building may not
draw from them, and nothing here licenses a new architectural colour — that
still needs its own entry.

---

## D-016 — Trodden ground follows the wall and the cart routes, not a radius

**Decision.** The earth/grass boundary is a rounded rectangle on the wall line,
wobbled by ~11 m of noise, with trodden earth forced onto every ramp corridor.

**What it replaces.** A radial mask, which is the obvious first implementation
and produced a geometrically perfect **circle of brown earth** in the middle of
a green meadow — visible from the first aerial and unmistakably artificial. No
settlement has a circular footprint unless its wall is circular, and
Hearthmere's is not.

**The second half matters as much as the first.** With the radius replaced, the
green pockets that make the town read as inhabited (yards, gardens, the
churchyard) landed wherever the patch noise put them — including straight down
Ford Road, which rendered as a lawn running the length of the town. Trodden
ground is not a texture decision, it is a record of where people walk, so the
ramp corridors now force it. When the street network is authored as real
geometry it should feed this the same way.

---

## D-017 — Ford Road's centreline constrains the *ground*, not just the buildings

**Decision.** No pad edge, terrace scarp, retaining wall or step flight may
cross Ford Road's carriageway. The terrace crossings are ramps at x = 0, and
every wall run is broken for them.

**How it was caught.** The first terrain laid the town's four terrace scarps as
continuous east–west lines and jogged Ford Road east to x = +14 south of the
square, so that the church could close the axis at x = 0. `tools/validate.py`
reported a 0.61 m obstruction on the carriageway at (0, 44) — a retaining wall
standing across the main street — which is Directive §3's rule, broken by the
ground rather than by a building.

**The consequence, taken.** The church precinct pad moved to x = +22, east of
the road and fronting it, and the grand step flight moved to x = −17.5 beside
the Ford Road ramp. Whether the church closes the axis is the arrival author's
composition to make; the terrain's job is to leave the carriageway clear at
every level change, and that is now true at all four scarps plus Smith's Lane.

---

## D-018 — The whole town is planned around one interior sightline

**Context.** Build Directive §3 moves the player's arrival from the north gate
to the altar inside the Church of Summoning, and requires that the open west
door frame the fountain plus at least two other venue anchors. That is a much
harder constraint than a street-level arrival, because a doorway is a hard
aperture: standing 11 m behind a 6.4 m opening leaves a horizontal cone of
±16.2°, and everything the brief asks for has to fit inside it.

**Decision.** Site the church **east of the market place, on the high ground**,
with its west front on the axis `z = −0.5`, and plan the east half of the town
outward from that cone rather than fitting the church into a layout.

**The three things that make it work, none of which are decoration.**

1. **East, so the player looks west.** The locked 09:30 rig puts the sun at
   `+X, −Z` in both renderers, so lit faces are the ones pointing east and
   north. Facing west means every facade in the arrival frame is a lit one and
   the sun is behind the player. Facing east — the other way to orient a church
   — would have put the entire composition in shade.
2. **Up, so the player looks down the fall.** The church floor is 2.40 m above
   the market place. Roofs stack instead of hiding each other, and the fountain
   at 43 m sits below the eye rather than on it.
3. **A shallow perron.** The steps fall 1.60 m over 8.0 m — slope 0.20 against
   a sightline-over-threshold slope of 0.229. Anything steeper and the flight
   drops below the sill: the player sees the distance but not the foreground,
   and "the descending church steps" that §3 asks for are invisible. This is
   the least obvious number in the plan and the easiest one for a later edit to
   break, so `tools/plan/townplan.py --check` computes it.

**This partly supersedes D-003.** "Every venue is authored with its principal
facade toward −Z" cannot survive a real street network: a facade faces its
street, and Hearthmere's streets run in every direction. What D-003 was
actually protecting — that review cameras see lit material — is preserved by
the *frames*, not by the buildings: the arrival looks west at east-facing
walls, the north gate looks south at the lit flanks of the towers, and the
market place's two most important frontages (west and south) both face a lit
quarter. D-003 stands as guidance for isolated venue renders and no longer as a
town-wide rule.

**Cost, stated honestly.** The church's own west front is in shade at 09:30,
which is the one hero facade in Hearthmere that a `shoot.mjs` render will
flatter least. Mitigated by putting the tower on the church's **north-west**
angle, so its north and east faces are lit and it reads from the north gate and
from the water; not solved.

---

## D-019 — The plan is generated data with a checker, and the placer is a tool

**Context.** v1's layout lived in prose plus a hand-typed JSON, and the two
disagreed: `streets[]` had no consumer (D-009), the guild sat across the road
the World Bible said it must not block, and nothing detected either. The v2
plan is 94 building masses, 15 streets, a wall, water and a sightline. Typed by
hand it would be wrong on the day it was written.

**Decision.** `tools/plan/plan_data.py` is the only place a coordinate is
authored. `tools/plan/townplan.py` checks it and generates
`docs/plan/hearthmere-plan.svg`, `content/town/hearthmere.json`,
`docs/plan/schedule.md`, and the tables inside `docs/TOWN_PLAN.md` between
`<!-- BEGIN GENERATED -->` markers. `tools/plan/lay.py` places the plots.

**What the checker proves, and why each one exists.** No two masses overlap;
nothing stands in a carriageway; nothing is within 3.8 m of Ford Road's
centreline; nothing stands in water or on the wrong side of the wall; every
arrival-frame anchor is inside the portal cone, under its head, and unblocked
by any of the other 93 masses; and the ground falls 4.02 m north. Every one of
those is a defect that shipped in v1 or was caught while writing this plan.

**The placer, and what it cost.** `lay.py` does not invent buildings. Each plot
is authored as *this much frontage, on this street, on this side, near here*,
which is what a burgage plot actually is, and the placer walks (street, side,
station) at 0.5 m resolution and gives each plot the nearest position that
passes every validity test. Plots are claimed street by street in order of how
much the town cares about the frontage, so a warehouse cannot take a cottage
lane on the far side of town.

**It still moved 23 of the 94 plots more than 16 m from where they were
authored**, because the town is genuinely full: an 8 × 8 m plot has no valid
frontage left anywhere inside the wall once 93 others are down. Where that
happened the *notes* were rewritten to match where the building ended up, so
the schedule's prose and its coordinates cannot disagree — but the honest
description is that the districts in §2 of the Town Plan are true of the hero
and secondary venues and are approximately true of the filler. Two consequences
are listed as known weaknesses in Town Plan §9: the Bailey carries more
cottages than one lane should, and three of the five back alleys were cut
because they ran through the plots they were meant to serve.

**The alternative that was tried and abandoned.** A relaxation solver — push
everything apart until nothing overlaps. It converged onto piles: with the
street network and the plot count this dense, the gradients cancel and
buildings collapse into each other. It is preserved nowhere; the frontage
placer replaced it entirely. Worth recording because "just relax it" is the
obvious idea and it does not work here.

---

## D-020 — Kirk Knowe: the plan asks terrain for a rise that terrain does not have

**This is an open conflict, recorded rather than smoothed over.**

**Context.** `core/terrain.py` shipped while this plan was being drawn. It puts
the fountain at 0.00 (same datum, good), the south gate at +1.75, the north
gate at −1.85 — a total fall of 3.6 m — and **the church site at +0.00**. The
plan needs the church floor 2.40 m above the market place, and dimensions its
levels from a base profile falling 4.02 m plus a 1.55 m rise, *Kirk Knowe*,
centred on (44, −2).

**Decision.** The plan's spot levels in `content/town/hearthmere.json` under
`terrain.spotLevels` are the target. `core/terrain.py` must be reconciled to
them, and the substantive part of that reconciliation is adding Kirk Knowe.

**Why the knowe and not 2.4 m of fill.** Either produces the same floor level,
so the arrival frame works on the shipped terrain today. But the reason the
church is *there* — the argument the whole east half of the plan rests on — is
that it is the only high dry ground, and a church takes the best site before
anything else is built. With no rise, that reasoning is a story about a
2.4 m-high artificial mound in the middle of a flat town, which is not the same
thing and does not read from the air.

**What is genuinely at risk if this is not done.** Nothing in the arrival
frame: it depends only on *relative* levels (church floor 2.40 above the market
place, perron slope ≤ 0.20), and those hold on either terrain. What is at risk
is the top-down and aerial read, the drainage logic, and the plan's own
credibility, since §1 of the Town Plan claims a knowe that would not exist.

**Also unreconciled, and smaller.** The plan's fall is 4.02 m against terrain's
3.6 m; the directive says "about 4 m" and both qualify, so whichever is
adopted, one of the two documents needs its numbers changed rather than left to
be discovered later.

---

## D-021 — Three v1 sitings are overturned, and why each one moved

Recorded individually because each is a lore change, not a layout tweak, and
`WORLD_BIBLE.md` now reads differently because of them.

**The Ferryman's Lamp leaves the market place for the waterfront.** In v1 it
sat on the square's west side. It is now on Wharf Lane by the old ferry stair,
65 m north. The reason is its own name: the sign is the actual iron ferry lamp
that guided the ferry across, and the bridge put the ferry out of business. A
pub called the Ferryman's Lamp on a market place 80 m from any water is a name
with no cause behind it. On the wharf it explains itself, it gives the trade
quarter its social anchor, and the sunken floor that v1 already specified now
has a reason — the low ground by the river, re-metalled over itself for two
hundred years.

**The Moot Hall stands free in the market place.** Every frontage siting tried
for it either blocked the guild tower in the arrival frame or fouled Well Lane.
Standing it free — arcaded ground floor on ten oak posts, chamber over — is the
normal English market-hall form, solves the conflict outright, gives the plaza
a mass to walk around, and puts its bell-cote exactly where the frame wanted a
left-hand anchor. This is the one case in the plan where the constraint
produced a better building than the intention did.

**The Adventurer's Guild takes the market place's west frontage, facing the
church.** v1 put it north of the square near the gate, where its job was to be
seen on arrival. The arrival moved, so the job moved: the guild now closes the
view west from the church door, and the two institutions face each other across
the market — the old foundation on the high ground in the east, the new money
in dressed stone in the west. That tension is worth more than the proximity to
the gate was.

**Cost.** `content/entities/*.json` for pub and guild carry v1 world
coordinates and are now wrong. They are the venue builders' to reissue against
Town Plan §6; nothing in this pass touched them.

---

## D-022 — There are two terrain models in `content/`, and only one of them is the ground

**Context.** `core/terrain.py` and `client/src/terrain.js` evaluate
`content/town/terrain.json`. Everything that renders, collides or walks reads
that file. Separately, `content/town/hearthmere.json` carries its own
`terrain{}` block — a base profile plus a "Kirk Knowe" rise — and, derived from
it, a Y on all 31 venue origins, on all 15 street path polylines, on the wall
path, and on 26 named spot levels. The two models were authored in parallel and
never reconciled.

**Measured disagreement.** Venue origins are 0.02–1.48 m out (church +1.35,
chandler +1.48, dovecote +1.15). Street paths are out by a mean of 0.18–0.68 m
per street, worst +1.24 m on Ford Road at z = 88. `waterY` is −3.30 in the town
file and −3.10 in the terrain file. The planner's Mere reaches x = 104, z = −25;
the terrain's Mere stops at z ≈ −66, so the quay, warehouse row and fish eatery
are sited 33–42 m inland on dry ground 2 m above the water, and the Emberflow
crosses Ford Road at z = −105 — nine metres outside the 192 m grid — so the
bridge that Directive §3 makes a hero composition has no river under it.

**Decision.** `content/town/terrain.json` is the ground. Directive §6.3 permits
exactly one height field and that is the one every tool already evaluates. The
Y values in `hearthmere.json` are therefore **not authoritative and must not be
read by a generator**; a generator takes `terrain.pad_level(id)` for a building
and `terrain.height(x, z)` for anything else.

**Not resolved here.** This decision says which file wins, not which layout is
right. The planner's water is a better town — Directive §4 wants the lake and
the ford legible from inside the walls, and the shipped terrain puts both
outside them. Someone has to either move the terrain's water south-west to meet
the plan, or move the plan's waterfront north-east to meet the terrain. Until
that happens Hearthmere is a lake town with no lake in it. Supersedes the
narrower D-020, which recorded only the Kirk Knowe half of the same conflict.

**Cost.** Every authored Y in `hearthmere.json` is now decorative. Leaving them
in the file is a trap for the next agent, and they should be stripped or
regenerated from `terrain.py` once the layout conflict above is settled.

---

## D-023 — The review harness was drawing a flat plane over the real ground

**Context.** `tools/render/town.html` created a 576 m flat dirt plane at
y = −0.012 as a stand-in for terrain that did not exist. When the terrain landed,
`client/src/main.js` dropped its equivalent `buildGround()`; the harness kept
its plane, and nothing noticed because the plane is a helper excluded from the
tri count, the draw-call budget and the bounds.

**What it cost.** The town falls ~4 m south to north, so everything north of
the datum was rendered *underneath* the plane and was invisible. Ford Road,
Kirkgate and the northern arc of the Bailey showed only their dashed
centrelines, and were read as never having been built. The Mere did not appear
at all. The market square paving sits 0.014 m above its pad against a plane at
−0.012, so 26 mm of separation z-fought and the plaza rendered as pale slabs
scattered on mud — read as "the paving is texture, not construction". No
eye-level frame ever showed the fall the whole layout is organised around.

**Decision.** The plane is deleted. `groundY()` imports
`client/src/terrain.js` — the proven port, not a second copy of the curve — and
the report names its source on every run. If a flat stand-in is ever wanted
again it must be opt-in and printed in the report, because a review harness that
quietly draws something the game does not have is worse than no review harness
at all.

---

## D-033 — Texel density is a property of the material, and the geometry does not honour it yet

> **Renumbered from D-024.** Two agents working in parallel both claimed
> D-024 in the same wave: this one and "The water moves to the layout"
> below. Numbers are never recycled, so the collision had to break one
> way; the water ruling had thirty references across `content/`, `docs/`
> and the toolchain and this one had a single line in `core/venue.py`, so
> this is the entry that moved. `D-024` now means the water ruling and
> nothing else.

**Context.** Art Bible §5 makes texel density a done-criterion (§8) and gives
three classes: hero 512 px/m, standard 256, large 128. It also says tiling
materials are authored at 2 m x 2 m per tile "unless noted". Nothing in the
pipeline recorded either number. `build.py` generated **every** set at 1024 px
regardless of whether the player could stand within 2 m of it, and the world
coverage each builder had actually been authored for existed only in its own
comments — `lime_plaster` says 2 m, `town_earth` says 4 m, `meadow_grass` says
6 m, and nothing enforced any of them.

**Measured.** `core/mesh.py` lays UVs in **metres** (`_planar_uv` with
`uv_scale=1.0`), so one tile of every material covers exactly one metre of world
whatever it was authored for. Every material in the town therefore renders at
`size / 1 m` = **1024 px/m**: twice the hero class, four times standard, eight
times large. It also means `lime_plaster`'s crackle, authored at 2-5 cm for a
2 m tile, ships at 1-2.5 cm; and `town_earth`, authored for 4 m, ships its
20 cm gravel structure at 5 cm.

**Decision, in two halves.**

1. **The registry owns density.** Each `LIBRARY` entry declares `coverage`
   (world metres per tile) and `klass`, and the texture size is derived from
   them: `size = class_density x coverage`, to a power of two, floored at 512.
   The floor is not arbitrary — every builder here carries a fine octave
   between `fbm(s, 70)` and `fbm(s, 150)`, and a tileable Perlin field needs
   about six pixels per cycle before detail becomes static. The floor has a
   consequence worth stating: a hero material must cover >= 1 m, a standard
   >= 2 m, a large >= 4 m. `python tools/assetgen/build.py --audit` prints the
   table and `tools/validate.py` fails on a violation, including on a texture
   whose file size no longer matches its declaration.

2. **The geometry does not honour it, deliberately, not yet.**
   `materials.uv_scale(key)` and `ctx.uv_scale(key)` return the `1/coverage`
   that a mesh builder must pass, and no venue passes it. Applying it globally
   — either by defaulting `mesh._planar_uv` from the material or by emitting
   `KHR_texture_transform` — changes the tiling scale of every surface in the
   town by 2-8x in one commit, which is a whole-town visual change that has to
   be reviewed as one, and this pass is the material library. It is a one-line
   change per call site and it belongs to whoever next touches the venues.

**Cost, stated plainly.** Until half 2 lands, every material renders `coverage`
times finer than the class it declares — a 2 m material at 512 px/m rather than
256. That is over-dense, not under-dense, so nothing looks worse than it should;
it looks *smaller*. The number the §8 checklist reports is the authored one.

**Also fixed here.** Roof tile exposure. Art Bible §3 fixes it at 0.16 m;
`terracotta_tile` laid 12 courses on what is now a 4 m tile, which is 0.33 m —
exactly double, on every roof in the town. A scale error inside a repeating
pattern is the hardest kind to see, because there is nothing in frame to measure
it against. `slate_roof` was authored against the same wrong assumption.

---

## D-025 — Two bugs in the shared helpers meant no texture in the repo was what its source said

Recorded because both invalidate every texture generated before this commit, and
because a reader comparing an old review render against a new one needs to know
why everything moved.

**`smoothstep` inverted every descending mask.** `core/mathx.py` computed
`t = clip((x - e0) / max(e1 - e0, 1e-9))`. For a descending pair the denominator
is `1e-9`, so `smoothstep(0.55, 0.0, v)` did not ramp from 1 down to 0 across
`v` — it returned a **hard step, 1 wherever v exceeded 0.55**, which is the
opposite half of the field and with no ramp at all. **Forty-four call sites in
`core/materials.py` were affected** and no other module uses a descending pair.
Two visible consequences, everywhere: masks were binary, so they aliased into
hard-edged blotches instead of blending; and each was applied to the wrong half
of its own noise, so the moss grew where the traffic was, the damp hollows sat
on the high ground, and the plaster patches were the parts that had not been
patched.

**Material seeds came from `hash()`.** Both `build.py` and `core/venue.py`
seeded each set with `abs(hash(key)) % 9973`. Python salts `str` hashing per
process, so **every run produced different textures from identical source** —
which silently voids the determinism guarantee `docs/ARCHITECTURE.md` §7 rests
on and makes a review diff meaningless. It was measurable: three materials
regenerated with no source change moved their §4 palette distance by up to 3.8.
`core/mathx.seed_from` has existed for exactly this reason since the first
commit, and its docstring names the bug. Both call sites now use it.

**Decision.** Both fixed, and the whole library regenerated. Any review render
made before this commit is not comparable with one made after it.

---

## D-026 — The texture atlas is a build-time UV remap, and it refuses tiling surfaces

**Context.** Directive §7 requires "texture atlasing across the kit" to defend
two budgets: < 900 draw calls and < 1.5 GB of texture memory. A back lane holds
a barrel, a crate, a sack, a rope coil, a bucket, a boot scraper, a hitching
post and a lantern bracket — eight materials, so eight primitives and eight
texture sets even after `core/batch.py` has merged the cell.

**Decision.** `core/atlas.py`, with two properties that are the whole design:

**Atlas coordinates are emitted into the glTF UVs by the generator.** The API is
`atlas.pack(mesh, key)` at the build site, not `atlas.fixup(gltf)` at the end,
and there must never be a post-process version. By export time `core/batch.py`
has merged every prop in a cell into one vertex buffer, so "which rect does this
triangle belong to" is no longer an answerable question.

**It refuses anything that tiles.** An atlased rect has neighbours, so
`wrapS = REPEAT` on it samples the barrel packed next door. `pack()` measures
the mesh's UV extent and raises rather than producing the silently-wrong result.
Props are authored in metres and are smaller than their material's coverage, so
they are eligible by construction; walls, roofs, paving and ground are not, and
never will be. Gutters are real repeat-padding — a wrap of each tile's opposite
edge — so a mip tap that strays outside a rect lands on more of the same
material rather than on the next one along.

**Not done here.** No venue uses it yet. Two standing atlases are declared
(`kit_props`, `kit_trim`) covering thirty materials between them, and
`ctx.atlas()` is one line at a call site, but adopting it is a change to the
venue modules and belongs with them.

---

## D-027 — Batching, LOD and instancing are core's job, not each venue's

**Context.** Directive §7 requires per-cell per-material static batching, GPU
instancing and a four-step LOD chain. None of it existed. Eight venues drew 852
of a 900 draw-call budget, and the town was about to grow to ninety buildings.

The measured cause of the draw-call count was not the number of buildings. It
was that `ctx.emit` appended one glTF primitive per call, so a venue's cost was
proportional to how its author had chosen to structure their loops. `streets`
emitted one primitive per pebble and cost 1,344 draw calls; the fix at the time
was for that generator to accumulate into a `Group` first, which worked and
which every future generator would have to remember to do.

**Decision.** `core/venue.py` re-buckets everything emitted, at `write()`, into
one primitive per (16 m cell, material), builds a 1 / .5 / .2 / .06 LOD chain
per cell, and exports the chain as `MSFT_lod`. `ctx.instance(mesh_id, mesh,
transforms)` and `ctx.lod(mesh_id, levels)` are the opt-in halves. A venue gets
all of it by existing.

**Why not per-venue discipline.** Because it is not enforceable. A rule that
every generator must merge before emitting is a rule that holds until the
ninetieth building, and the failure is silent — the town looks right and costs
four times what it should. Making `ctx.emit` cheap regardless of call pattern
removes the class of mistake instead of documenting it.

**What each technique actually buys, measured.**

- **Batching** is the draw-call lever, but only in combination with culling. It
  makes each batch *bigger* (fewer, larger primitives) and simultaneously
  *cullable* (one per cell rather than one per venue). On its own, per-cell
  splitting made the square view slightly worse — 117 draws to 125 — because
  three.js already frustum-culls per mesh and splitting produced more meshes.
  It is the LOD chain hanging off the cells that pays.
- **LOD** is where the draw calls go. The lever is not triangles, it is
  materials: a cell of nine materials costs nine draws whether it holds 9,000
  triangles or 900. LOD2 is capped at three materials and LOD3 at two, so a far
  cell costs at most two draws no matter what is in it.
- **Instancing** buys memory, not draw calls, and this is worth stating plainly
  because it is the opposite of what the name suggests. An
  `EXT_mesh_gpu_instancing` node is exactly one draw call for N copies — but
  the cell batch was already drawing that material, so instancing a prop whose
  material the cell already has *adds* a draw call. It saves the vertex buffer:
  the streets' 1,250 verge pebbles went from 11.7 MB to 4.4 MB. Below
  `INSTANCE_MIN = 12` per cell core bakes them into the cell batch instead,
  because under that count the draw call costs more than the memory saves.

**Cost.** The LOD chain adds ~76% to every venue's vertex buffer; the town's
meshes are ~180 MB on disk. Mesh memory, not draw calls, is now the binding
constraint, and the fixes for it (quantised attributes, Meshopt, streaming the
coarse levels separately) are not done. Recorded in `docs/ENGINE_PORTING.md`.

---

## D-028 — Material dominance is measured by area, not by triangle count

**Context.** The coarse LOD levels fold minor materials into the dominant one.
The first implementation picked the dominant material by triangle count.

**What it did.** A chamfered timber frame is thousands of tiny triangles
covering four square metres; a plaster panel is a dozen triangles covering
forty. By count, oak_dark is the dominant material of the Grey Heron Inn. The
first aerial rendered after batching landed showed the inn, the pub and half
the town as solid dark-brown boxes with no plaster and no roofs — the impostor
had deleted exactly the two things a building reads by at 150 m.

**Decision.** `collapse_materials` ranks by summed triangle **area**, and the
impostor level keeps the top **two** materials rather than one.

**Why two and not one.** One draw call per cell is the tidier number and it is
wrong. Past 100 m a building is a roof colour over a wall colour; that pair is
the entire read, and Art Bible §6's silhouette test is precisely a test of the
contrast a single-material impostor destroys. Two materials over 144 cells is
288 draw calls for an entire town seen at once, against a budget of 900. The
second draw call is affordable and the read is not optional.

---

## D-029 — The review harness runs the client's culling code, not its own

**Context.** `tools/render/town.mjs` reports the draw calls the §7 budget is
judged on. The client decides which batches to draw. D-023 is the record of
what happens when those two disagree about the world.

**Decision.** `client/src/lod.js` owns LOD selection, frustum culling, cell
distance culling and portals, and `tools/render/town.html` imports it. There is
one implementation.

**Consequence, and it is the useful part.** A review camera is not a gameplay
camera. An orthographic plan sits 600 m above the town, so honest distance
culling returns an empty image; an aerial at 260 m would draw everything at
LOD3 and report a wonderful, meaningless number. So the harness marks which
views a player can actually have, disables the distance cull for the whole-town
review cameras, and reports **two** peaks: the worst gameplay frame, which is
what the budget gate tests, and the worst overall, which is the upper bound
nothing can exceed. A single "peak draw calls" number across both kinds of
camera is the number that was being reported before, and it was 851 for a
picture no player will ever see.

Attribution comes from `onAfterRender`, which three.js calls only for objects
that survived culling — measured, not predicted — split per venue and per 16 m
cell, and excluding the shadow pass because "300 draws, 90 of them shadows" is
actionable and one merged number is not.

---

## D-030 — The budget gate fails on regression, not only on the budget

**Context.** Directive §7's budget is a ceiling. A town does not hit a ceiling
in one commit; it hits it in forty commits that each cost twenty draw calls and
were each individually fine.

**Decision.** `tools/render/town.mjs` writes `review/perf-baseline.json` and
fails (exit 3) when a venue's LOD0 draw calls rise more than 5% above it, or
when the town's gameplay draw calls rise with no new venue placed — as well as
when the absolute budget is exceeded. `tools/validate.py` gates statically on
the one number culling cannot improve: the whole town drawn at LOD3.

**Why per venue.** Twenty-two venues are still unbuilt. Every total will rise
legitimately as they land, and a gate that fires on legitimate growth is a gate
someone disables. What must not regress is the cost of a venue that already
existed, which is a comparison the baseline can make honestly.

Rewriting the baseline requires `--write-baseline` and an entry here.

---

## D-024 — The water moves to the layout, and the layout stops carrying levels

**The ruling.** D-022 established that `content/town/terrain.json` is the ground
and left the substantive question open: the plan's water and the terrain's water
were 40 m apart, and one of them had to move. **The water moves.** The town plan
is the product of deliberate urban-design reasoning with 94 building slots, a
wall, 15 streets and a sightline hanging off it; the terrain is parametric, and
a river is a handful of numbers. Moving the plan to the water would relocate a
quarter of Hearthmere to make a spline true.

### What was actually wrong

Measured from the height field, before and after:

| | before | after |
| --- | --- | --- |
| water to the quay face | 33–42 m of dry ground | **0.5–1.0 m** |
| water depth at the quay | none — dry, 2.0 m above the mere | **2.25 m** |
| Emberflow crossing on Ford Road | z = −105, 29 m past the gate, **outside the 192 m grid** | z = −90, 10 m past the gate |
| open water at the crossing | — | 11.5 m wide, 2.5 m deep |
| worst venue origin Y drift | 1.48 m | **0.001 m** |
| street path Y drift | mean 0.18–0.68 m, worst 1.24 m | **no Y stored at all** |
| water surfaces in `content/` | two, 0.20 m apart | one |

### The four changes in `terrain.json`

1. **The Emberflow comes south.** Centreline z ≈ −90 to −92 across the town's
   north, half-width 5.5 m on a 9 m bank cut to −5.60. The bridge is now in the
   departure frame — you see it from the gate — and `hm.pad.bridge_north` is a
   causeway projecting into the channel from the far bank, which narrows the
   crossing to 11.5 m of open water and is *why* the bridge is three short
   arches rather than a viaduct. The river stays wholly outside the wall: the
   south waterline is z ≈ −82, the wall is at −76.
2. **The silted ford lies beside it.** `hm.water.ford` is a gravel bar with
   0.45 m of water over it at x ≈ 13, sixteen metres east of the bridge, with a
   shelving bay in the south bank where the old approach ramp ran in. Visible
   from the bridge parapet, which is the whole point of keeping it.
3. **The Mere's south-western shore comes in to the quay.** `hm.pad.quay` is
   the plan's wharf exactly — a 26 × 16 m stone-faced platform at −1.55 with the
   Water Gate at the middle of its landward edge — and the mere's shoreline runs
   along its seaward face, where `hm.wall.quay_face_a/b` stand. `hm.water.harbour`
   dredges the basin alongside to −5.35. A laden flat-bottomed lighter draws
   under a metre; there is 2.25 m at the wall at any season, which is the reason
   the quay is here and not at the bridge.
4. **Two terraces were cut back.** This is the non-obvious part and it is the
   whole reason the first waterfront failed. Pads are applied *after* water in
   the height function, so a terrace is a bulldozer: `terrace_gateflat` at −1.85
   ran to z = −84 and x = +56, and it filled the Emberflow's south bank and the
   entire harbour back in. Its east half is now `terrace_wharfside`, **rotated
   21.8° to follow the north-east wall**, because an axis-aligned rectangle here
   either leaves natural ground inside the wall or floods the berm outside it.
   `terrace_lower` was split so its northern half stops 10 m short of the mere's
   south-east shore, where Tan Road runs.

### The shoreline is solved, not typed

**The waterline is not the polygon edge.** A polygon shape carves to `bedLevel`
inside itself and blends back to the land over `shelf` metres outside, so the
`h == level` contour sits some way *outside* the polygon — 9.5 m, at the mere's
original shelf and bed — by an amount that depends on how high the land beside
it happens to be. Every vertex is different and none of it is eyeballable. That
is exactly how the waterfront ended up 40 m from the water in the first place.

So `terrain.json` now authors the **`shoreline`** — the curve the water's edge
is required to land on — and `tools/plan/ground.py` **solves** `polygon` from
it: march out from each shoreline vertex, find where the ground actually crosses
the water surface, correct by the error, eight passes. Residual: **mean 0.08 m,
worst 1.41 m** over 26 vertices. Three are excluded (`solveSkip`) because the
quay pad and the harbour basin pin the waterline there whatever the mere polygon
does, and two more (`solveRange`) because the Emberflow's own bank governs the
river mouth. The solver caps its total displacement at 9 m and reports the
residual, so a vertex that *cannot* converge names the thing holding it rather
than walking 30 m inland and tying the polygon in a knot — which is what the
uncapped first version did.

### The venue pads were pointing at a town that no longer existed

`hm.pad.inn` was 42 m from the inn. `hm.pad.pub` was on the opposite side of
Hearthmere from the pub. `hm.pad.quay` was in the water. Eleven of the fifteen
venue pads named a building they were not under, and none of it showed, because
no generator has called `terrain.pad_level()` yet — the first one to do so would
have got a confident wrong answer.

`tools/plan/ground.py` now generates all 23 venue pads from `plan_data.SLOTS`:
the slot's own centre, its footprint plus a 1.6 m working margin, and its own
rotation. Level is the terrace at that point, evaluated from the terraces and
the fall spines alone — no noise, so the pad is level *with* its shelf, and no
water, so a building beside the river is not dragged into it. Only the 24 slots
in `VENUE_OF_SLOT` get one: a pad per building for all 94 would triple the cost
of `height()`, which is evaluated at 1.6 M vertices per terrain build and at
every step the player takes.

### Ford Road's ramps were cut for a road that does not exist

D-017 established that no scarp, retaining wall or step flight may cross Ford
Road's carriageway. The terrace ramps were then cut at x = 0 — but the plan's
Ford Road bends east and crosses the market scarp at **x = +8**, straight into
`hm.wall.market_n_c`. Every ramp is now centred on the carriageway where it
actually crosses (+0.6, +8.0, +8.0, +5.0) and every retaining run is broken for
it. `hm.ramp.north_causeway` is deleted; the gate flat carries the abutment.

### No Y is stored in `hearthmere.json` that a tool could ask for

`streets[].path`, `wall.path`, `wall.stairs`, `openLots[].poly`,
`marketPlace.polygon` and `landmarks[].pos` are now **`[x, z]`**. The whole
`terrain.model` block and the duplicate `water` geometry are gone, replaced by
pointers at `content/town/terrain.json`. Consumers updated:
`venues/streets.py`, `tools/validate.py`, `tools/check_walkable.mjs`,
`tools/render/town.html`, and `content/schemas/town.schema.json`.

`venues[].origin[1]` survives, because that one is a scene-graph transform the
client applies rather than a lookup — but it is written from `terrain.height` at
the venue's own centre, so the drift is zero **by construction** rather than by
anyone remembering to re-derive it. (Two infrastructure origins were hand-typed
and one of them, the gatehouse, was 0.45 m under its own gate flat; they take
the height field now too.) `plan_data.height()` is a one-line forward to
`core.terrain`; the plan's base profile and its Gaussian Kirk Knowe are deleted.

The spot-level check changed shape with them. Comparing two height models is
what D-022 caught. A spot level with no authored `y` now simply *is* the height
field — there is nothing to disagree about — and one with an authored `y` is a
made surface, a floor or deck or tread, checked only for standing on the ground
rather than in it or a storey above it. A sunken floor is allowed 0.80 m below;
a deck over water is allowed 6.0 m above and no burial. Fourteen levels read
from terrain, twelve are made and checked.

### Water is now rendered as water

- **Flowing.** `client/src/water.js` patches the standard material to sample its
  normal map **twice**, at different scales and counter-scrolling velocities,
  and adds the tangents. One scrolling layer is the obvious implementation and
  it reads as a conveyor belt: the ripple field translates bodily and the eye
  sees the texture rather than the water. Two layers have no shared frame to
  translate in, so what you get instead is interference — crests forming and
  dying in place. `tools/render/town.html` installs the same shader at a fixed
  phase, because a review harness drawing something the client does not have is
  D-023 all over again.
- **The fountain basin is water, not glass.** It was a `glass` lathe: the town's
  largest piece of standing water, in the place a player stands longest,
  rendering as a sheet of window pane in a stone bowl. `core.kit.water_disc` /
  `water_slab` build it from the same material, the same ripple scale
  (`kit.WATER_UV`, 2.5 m per tile) and the same depth tint as the Mere, so the
  fountain and the harbour read as the same substance. The horse trough went
  with it.
- **Two shoreline defects, both found by looking at the render.** The water
  sheet's buried edge ring was sunk `0.04 + 0.14 × cell`, which is not enough
  against the bridge abutment's 3.4-m-in-2.5-m apron and showed as dark teeth
  along the far bank; now `0.06 + 0.22 × cell` on a 1.2 m grid. And past
  `waterlineMud.dropOff` the silt band switched off and handed the shore to
  **gravel** — `#8C8272` scree at the waterline on a 2 m LOD ring, a ring of
  pale scalloped teeth right round the Mere and the first thing the eye found in
  the departure frame. The far shore now falls through to turf, which is both
  cheaper and what a far shore looks like. Water roughness floor 0.06 → 0.13,
  because the water is now *in* two of the three hero frames instead of 40 m
  behind them and the glitter path was clipping to white through the bloom pass.

### What this does not settle

**Kirk Knowe.** D-020 argued the church sits where it does because it is the
only high, dry ground, and the shipped terrain has no rise there at all. That
argument is untouched by this ruling — it is not a water question — and the
church still takes its 2.40 m from a plinth and a perron rather than from a
hill. Left open deliberately, rather than smuggled into a water decision the way
D-009 smuggled the rim light.

**The gate-to-gate fall is 3.75 m**, against the Directive's "about 4 m". The
grid-wide fall in the spines is 4.17 m; the terraces take 3.75 m of it between
the two gate thresholds, and `hm.pad.south_gate` at +1.90 supplies the last
0.28 m as the road starts to climb away. Both numbers are defensible and they
are different numbers; the check now measures and reports the gate-to-gate one
rather than asserting a figure neither of them is.

**`WALL_IN_WATER` became `wall.nearWater`.** The plan claimed the wall's outer
face IS the shoreline from the Crane Tower to the Heron Tower. It cannot be:
Tan Road runs outside the wall on that exact stretch, 1.5–3.2 m from its face,
so putting the shoreline on the wall would put a road under water. The wall now
stands 0.8–4.0 m back with the berm and the road between, and the claim is
downgraded here rather than left to be discovered from a render.

---

## D-031 — A roof has no position of its own

**Context.** v1's defect register puts roof/wall separation at the top: roofs
were authored as independent prisms placed above a wall box by an eyeballed Y
offset. Two numbers had to agree — the wall's height and the roof's offset —
and nothing checked that they did, so roofs floated, gaps opened at the eaves,
and gable ends showed sky through the roof void. Directive §6.2 forbids it. The
modular building kit generates 63 of the town's masses, so whatever it does
with roofs, the town does 63 times.

**Decision.** `core/roof.py` takes a `Plate` — the polygon of the wall head
carrying the absolute Y of its bearing surface — and derives every vertex from
it. **There is no `y` parameter on any public function in that module**, so a
caller cannot place a roof by an offset even by mistake. Raise the wall and the
roof follows; there is nothing left to keep in sync. Ridge height is
`plate.y + pitch × halfspan`. Eaves height is `plate.y − pitch × overhang`,
which is *below* the bearing line because the rafter foot projects past the
wall face — the reason a real eaves throws a shadow.

Three things follow from the same rule and are worth stating because each was a
separate v1 defect:

- **Gable ends close by construction.** The closure panel along each plate edge
  is computed by asking the FINISHED roof surface how high it is at points
  along that edge. Gable, jerkinhead, gambrel, catslide and lean-to all close
  with one piece of code, and a roof kind added later cannot ship with an open
  end because nobody wrote its triangle.
- **Chimneys emerge because they are told where the roof is.** `surface_y(x, z)`
  on the roof they pierce sets their height. v1 shipped three chimneys buried
  2.4–2.9 m inside the inn's roof.
- **Valleys are a plane intersection, not a special case.** A wing is roofed
  from its own plate and clipped against the main roof's planes; the cut line
  *is* the valley.

**Cost.** The solver only handles plates that are rectangles (it takes their
oriented bounding rectangle). Every slot in the building schedule is a
rectangle, and an L-plan is built as a main range plus a clipped wing, so this
has not bitten — but a genuinely non-rectangular plate would need a straight
skeleton, and the day someone authors one the failure will be silent (an
oriented box around a trapezoid) rather than loud.

---

## D-032 — A building's interior is backing panels, not a room shell

**Context.** Since the kit's walls cut real apertures, a window with nothing
behind it looks through the building and out of the window on the far wall. The
obvious fix is an inverted box inside the walls: invisible from outside,
present through every opening, one primitive.

**What it cost.** The interior surface of a 9 × 8 m house is ~330 m² of dark
timber against ~180 m² of roof. D-028 makes the LOD impostor keep a cell's two
largest materials **by area** — so with a room shell the two largest are
oak_dark and oak_dark, and the whole town rendered brown from the air while
every close-up showed a red roof. The first whole-town aerial after the kit
landed is unusable for exactly this reason; the plan view, being closer, was
fine, which is how it survived a look.

**Decision.** No interior shells in generated buildings. Each aperture gets a
backing panel 0.34 m behind it, sized to the opening plus 0.3 m. That is ~4% of
the area, reads identically through an opening, and leaves terracotta and
plaster as the two materials the impostor keeps.

**The general rule this is an instance of.** Geometry that is never seen still
votes on what a building looks like at 150 m. Any surface a generator adds for
a reason other than being looked at — an interior, a foundation, a backing —
has to be sized as if the impostor were watching, because it is.


## D-034 — A roof proves it covered its plate, and a covering is dealt, not fixed

**Context.** Eight of the sixty-three buildings the modular kit generates shipped
with no roof at all — open-topped boxes carrying a ridge line, hip caps and barge
boards hanging in mid-air above them, visible from the street, from the air, and
as black rectangles in the orthographic town plan. Separately, sixty-two of the
sixty-three were roofed in the identical terracotta, so from any aerial the town
read as one material. The art-director pass rejected the kit on both.

**Three findings, and the structural answer to each.**

**1. `clip_plane` had one sense where two are needed.** It kept `self above
other`, which is right for a VALLEY — a wing's slope dies where the main range's
plane climbs through it — and exactly inverted for a HIP, where the hip plane
springs from the gable head *above* the main eaves and it is the part of the main
slope rising through the hip that must go. Each of a jerkinhead's two hips
therefore kept only the sliver it was meant to delete, and their intersection was
empty. `clip_plane(other, keep="above"|"below")` names the two cases; the
half-hip solver passes `keep="below"`.

**2. Nothing checked that the roof covered the plate, so the trim shipped
anyway.** The failure mode was worse than a hole — a degenerate slope emitted no
tiles but still got its ridge cap, its barge boards and its rafter feet, all
floating over the open box. Degenerate slopes are now dropped unconditionally
(the filter used to run only under `clip_against`), and `roof_from_plate` then
asserts the surviving slopes cover at least 80% of the plate in plan projection.
A roof that does not cover its plate raises instead of shipping. All seven roof
kinds were re-exercised against a bare plate: `gable`, `half_hip`, `hip`,
`catslide` and `gambrel` cover 126% of plan (overhang included), `pyramid` 119%,
`lean_to` 117%. `half_hip` was 0%.

**3. `roof_mat` was one scalar per style.** `stone_civic` carries slate and is
never instantiated; `cottage_thatch` carries thatch and is only reached by a note
naming it. So the deal never happened. `ROOF_MATS` is now a weighted tuple per
style, dealt by seed in the same place and the same way `ROOFS` and `FRAMES` are
— tile is the standard, the poor and the outbuildings keep thatch, and only the
civic hand reaches slate or lead. A note naming a covering still outranks the
deal. 63 buildings now come out terracotta 29 / thatch_old 23 / slate 8 /
thatch_new 2 / thatch 1, against Art Bible §4's call for roughly 30% aged.

**Two consequences that had to be handled with it.** The covering is a FAMILY:
`is_thatch()` replaces four exact `== "thatch"` tests, because `thatch_old` is
the same construction and must take the same mass build rather than being tiled
like a slate. And thatch is never laid below about 45°, so dealing it onto a
style pitched for tile raises the pitch to a 1.00 floor — otherwise the seeded
pitch builds a flat thatch, which reads as a hayrick.

**Also fixed, latent.** `Plate` mis-rotated its edge labels on winding reversal:
edge `i` spans `pts[i]..pts[i+1]`, so reversing the point list maps old edge `i`
onto new edge `n-2-i`, not `n-1-i`. `list(reversed(edges))` gives `[e3,e2,e1,e0]`
where the answer is `[e2,e1,e0,e3]`. Rect footprints are always CCW so it never
fired, but `dormer()` builds a plate with no winding guarantee.

## D-035 — A made surface is draped onto the ground and then lifted off it

**Context.** `venues/market_square.py` was authored against a flat world and laid
its 34 x 32 m plaza as one plane at `y = 0`. The ground is a function now
(Directive §6.3), and measured across that trapezoid `terrain.height()` runs
-0.525 m at the north mouth to +1.150 m at the south edge. 13% of the plaza had
earth standing through the paving and 10% of it hung over a void — brown mud
between the flagstones and a dark undercut round the fountain, in the town's
single most important composition. The client meanwhile walks on
`terrain.height()`, so the player's feet were up to a metre off the surface they
could see.

**The rule, in two halves, because one alone is wrong.**

**Drape, then lift.** A made surface — carriageway, plaza, yard — follows the
ground and then stands proud of it. Draping alone is not enough: a surface draped
flush is COPLANAR with the terrain mesh and the two z-fight into a mottled
patchwork of paving and mud, which is what the first attempt at this produced.
The lift also has to clear the height field's own 0.03-0.06 m of roughness. The
number is `kit.MADE_LIFT = 0.22`, which is `streets.ROAD_LIFT` — the square meets
those streets, so it takes their lift and the made surface stays continuous
across the junction.

**Surfaces are draped; objects are seated.** Draping a fountain per-vertex would
warp the bowl wherever the ground fell away under it. `terrain.drape()` now
accepts a `Group` as well as a `Mesh` (draping part by part, which keeps the
material split `ctx.emit` batches on) and the venue-local `_drape` fork in
`streets.py` becomes redundant. An object is instead moved bodily so its local
`y = 0` lands on the paving beneath the centre of its own footprint.

**A walkable surface over a fall is a grid, not a prism.** The plaza's collider
was one hull with a fixed 0.42 m Y band. Widening that band to span the real
1.68 m fall does not work: `Collision.groundAt` only stands the player on a
volume whose top is within a step of their feet, so one prism tall enough to
cover the whole fall is above reach everywhere except its high corner and
silently stops being a floor. The plaza is emitted as an 8 x 8 grid of thin
surface tiles that track the paving to within their own local roughness — 64
volumes, the same technique `streets.py` already uses per segment.

**Still open.** Six venues authored before the terrain landed still reference
`core/terrain.py` nowhere and lay everything at a flat venue-local `y = 0`:
`guild` (1.15 m of ground fall under its own mesh footprint), `stalls` (1.05 m),
`pub` (0.49 m), `shop_row` (0.41 m), `inn` and `blacksmith` (0.00 m — the terrain
gave them dead-flat pads, so they are correct by luck, not by construction).

## D-036 — The project's name is Evermore, everywhere

**Context.** D-008 registered the world as **Arkadion** and Hearthmere as
**Haven I**, and the design tree under `docs/` has called the game **Evermore**
since the v0.5 split — but the repo's own surfaces still said **Unlimitless
Horizons**: `CLAUDE.md`'s title, the root `README.md`, `docs/ARCHITECTURE.md`'s
title, the client's `<title>`, `package.json` and its lockfile, the collision
schema's `$id`, and the glTF writer's `generator` string. Two names for one
project is the same silent drift D-008's postscript warned about.

**Decision.** The game is **Evermore**. The world is **Arkadion**. The town is
**Hearthmere** (Haven I). Every repo-level surface now says so. Entity IDs stay
`hm.*`: per ARCHITECTURE §2 IDs are never recycled, and `hm` names the town,
not the game. The root `PROMPT.md` — the owner's standing order — is introduced
alongside this entry; it sits outside the document precedence chain and owns
only the mission, the priority order, the rules of evidence, and how sessions
run. If it ever disagrees with a governed document, the governed document is
right.

**Why.** `PROMPT.md` states the name as mission-level fact, and it is the first
thing an agent continuing the work will read. The repo must agree with the
document that introduces it, or the drift compounds from the front door.

**Cost, stated honestly.** The `generator` string in `core/gltf.py` is baked
into every exported `.gltf`, so meshes on disk keep `"unlimitless-horizons
assetgen"` until their venue next regenerates — a one-line header diff per
asset, nothing structural. The collision schema's `$id` becomes a bare
`collision.schema.json`, matching its two sibling schemas; this was checked
first — `tools/validate.py` loads the schema by file path and every collision
file uses a relative `$schema`, so nothing dereferences the old URI. Any git
remote may keep an old slug; remotes are out of scope here.

## D-040 — The architecture is Tudor, for the most part

**Context.** Owner direction, 2026-08-01: "For the most part, I want the
architecture style of the first town to be of tudor." Art Bible §1 named a
style axis (SAO / Shangri-La Frontier / Echoes of Aincrad) and §2 permitted
timber framing, but no document named the architectural idiom — builders
inferred it from the kit (`timber_frame_wall`, `jetty`, `leaded_window`),
and an idiom that lives only in code is re-derived from scratch by every
new agent, which is how drift starts.

**Decision.** Art Bible §1 gains "The architectural idiom": the domestic
and commercial fabric is Tudor vernacular — exposed close-studded framing,
jettied upper storeys, plaster or brick-nogging infill, steep tile or
thatch roofs, tall prominent chimneys, leaded casements. Stone remains the
mark of the sacred, the civic, and the boundary: church, guild tower, town
wall with gates and towers, bridge.

**Why.** Naming a real idiom gives builders and critics a shared, checkable
reference — "is this jetty right for Tudor?" is answerable; "does this look
right?" is not. The existing kit already speaks this language, so the entry
ratifies practice rather than forcing a rebuild.

**Cost.** Venues already built are not automatically re-reviewed against
the named idiom; critics apply it from their next review onward. Anything
that reads as a different vernacular is now a defect, not a variation.

*(Renumbered from D-037, which a parallel session had claimed for residue
vocabulary while this entry was being written — the same failure D-033
records. As of this writing D-038 is also claimed twice, by "the wall is
one swept section per run" and "the natural layer is one venue"; the later
claimant should renumber to D-041.)*

---

## D-037 — Residue is a shared vocabulary in core, not clutter per venue

**Context.** Art Bible §7 calls residue "the highest-value detail per unit of
effort", and §8 makes "contains residue" a done-criterion for every asset.
Hearthmere had almost none, and the venues that did have some had grown it
locally: `venues/stalls.py` carried nine private geometry helpers annotated
"venue-local; core/ is owned by other agents this pass", including its own
catenary, its own cloth surface and its own chamfered prism. Twenty-one venues
have no generator yet and every one of them needs a dressed shopfront.

Clutter authored per venue is the same failure as bevel code authored per
venue, one layer up: thirty agents each deciding what a working yard looks
like produce thirty visual languages, and no review pass can unpick that
afterwards.

**Decision.** `core/props.py` owns the residue vocabulary — 63 builders across
transport, storage and trade, tools by trade, and domestic/street — plus six
**dressing functions** (`dress_yard`, `dress_workbench`, `dress_shopfront`,
`dress_threshold`, `stack_against_wall`, `spill`) that hand a venue a composed
arrangement in one call. `core/kit.py` keeps architecture and its original
seven props; the two modules forward unknown names to each other, so a venue
author has one vocabulary regardless of which they import.

The primitives those builders needed are promoted into `core/mesh.py` rather
than duplicated: `tube`, `catenary`, `ring`, `globe`, `sheet`, `retex`, and
`chamfered_prism`. `Atlas.pack_eligible` is added because `pack()` is
all-or-nothing and therefore unusable on a dressed arrangement, where a barrel
is atlasable and the water butt's water is not.

**Four rules the module enforces, because each of them was violated first.**

1. **A wall-dependent prop must be told about its wall, and its default must
   not need one.** `lean()` computes the tilt that puts an object's top exactly
   on a named wall plane; `stack_against_wall` pushes each item back until its
   measured bounds touch. `yoke_and_buckets` defaults to resting across the two
   bucket rims — self-supporting — because a wall-dependent default is how a
   prop ends up hanging in mid-air in every venue whose author did not read the
   docstring. The in-situ harness proved the point twice: a lean-to with no
   back boarding left three saws hanging in open air.

2. **Cloth hangs or it lies down, and the two are different surfaces.**
   `mesh.sheet(plane="xy")` exists because authoring a downward drop against
   the default XZ plane produces a surface that falls in Y *and* in Z at once —
   a 45° ramp. Every hanging cloth in the first pass was one: laundry, the
   cloak over a chair back, a bolt's loose tail.

3. **Arrangement is by workflow, never by size or symmetry.** A smith's tongs
   hang in jaw order because he reaches for them blind; a cooper's croze sits
   on the block by the raising-up because it is the next cut. Sorting any of
   these by size is the tell that nobody who works has touched it.

4. **A spill needs a cause and a heap.** A patch of grain with nothing to have
   come out of reads as a decal, and a 24 mm dome over a half-metre radius
   reads as a doily. The heap now stands at its angle of repose and the loose
   grains ride on it.

**Costs and exceptions, stated.**

- **Spill grains below 25 mm are unchamfered**, which is a deliberate exception
  to Art Bible §6. The smallest chamfer class in the §3 table is 3 mm for
  handheld metal; a 16 mm grain of wheat needs a sub-millimetre bevel that is
  smaller than a texel at any distance a player sees it, and a chamfered box
  costs 44 triangles against 12. One spill at usable density is 4,500 triangles
  chamfered and 1,200 unchamfered. Anything 25 mm or over keeps its bevel.
- **`mesh.prism(chamfer=...)` still ignores its chamfer argument.** That is a
  live Art Bible §6 defect affecting every venue that has ever passed it a
  value — the blacksmith passes 0.02, `kit.jetty` passes 0.006 — and it is not
  fixed here. `chamfered_prism` is the sanctioned path and is what `props.py`
  uses; fixing `prism` in place changes the geometry of eight shipped venues
  and belongs in its own pass with its own renders. Flagged, not hidden.
- **`kit.sack` changed shape and now returns a `Group`.** Eight segments rather
  than twelve, a flat base, and a real gathered neck with a tie: the old
  twelve-segment smooth-shouldered lathe read as an onion at gameplay distance,
  which the prop sheet made unarguable. All seven call sites use only
  transform-and-emit, which `Group` supports, so nothing broke — but a caller
  reaching for `.uv` or `.merge` on it would.
- **Two harness venues ship in `venues/`**: `props_sheet` (every builder on a
  measured grid with 1.75 m figures and adaptive back walls) and `props_situ`
  (a dressed yard and workbench on the real terrain at 65,-30, chosen by
  searching `terrain.height` for a site with real fall after the first
  eyeballed site turned out to be a dead-flat building pad). Neither is in
  `content/town/hearthmere.json`, so `tools/render/town.mjs` cannot place them;
  they cost about 200k triangles of `.gltf` on disk and roughly five seconds of
  a full asset build. Delete them and the review claim in this entry becomes
  unreproducible.

---

## D-038 — The wall is one swept section per run, and the run is what steps

**Decision.** `venues/wall.py` builds the circuit as a sequence of *runs*, each
one a `core.mesh.sweep` of five convex sections along a stretch of the authored
polyline. Within a run the crown holds one level; between runs it moves by a
whole number of 0.34 m courses. The base follows `terrain.height` continuously
at every station.

**Why not one extrusion.** A wall whose top runs level across falling ground is
the single most common tell of a procedural circuit, and Hearthmere falls
3.75 m from the south gate to the north gate and another 1.25 m to the water.
Any primitive that takes one cross-section and one length cannot express "base
on the contour, top on the courses", so the primitive is new: `mesh.sweep`
takes **one profile per station**, which also buys the parapet dying away at a
stair, the wall thickening into a gate pier, and the section changing where the
wall changes date. The riser at a step is the end cap of one run and the start
cap of the next, so it is real geometry rather than a stretched face.

**Section, and why the walk is corbelled.** The town record authors
`walkHeight 5.2`, `parapet 1.1`, `thicknessBase 1.4` battering to 1.1, and a
1.6 m walk. A 1.6 m walk on a 1.1 m wall reconciles exactly one way: the extra
0.9 m is corbelled off the inner face. That is what a town which will not pay
for a thick wall actually builds, and the double shadow line it throws down the
inner face is the best thing on the circuit seen from the Bailey. The corbels
are `ctx.instance`d, not emitted, as are the putlog holes.

**Where the character comes from.** `_stretches()` turns four sentences of
TOWN_PLAN section 5 and the World Bible into arc-length ranges: the older,
lower, thicker rubble north-west of the Mill Tower; the neat ashlar of the
sixty-year-old south-east; thirty metres of the east put back in the wrong
stone after a collapse; and the stretch between the Tenter and Spring Towers
that the town outgrew, where the parapet and the walk were robbed and what is
left is a garden wall. A wall of one section all the way round is a fence.

---

## D-039 — A concave polygon was being fan-triangulated, so every arch was solid

**Symptom.** The four gates, the three posterns and the three bridge spans all
rendered as unbroken masonry with a voussoir ring and a hood mould drawn neatly
over the top of a hole that was not there. The build reported the triangles.
The collision, authored separately, correctly left the archway open — so the
player could walk through a wall they could see no opening in.

**Cause.** `mesh._Builder.poly` triangulated every polygon as a fan from vertex
0. That is correct for the box faces which are 99% of this town's geometry and
wrong for the one shape an arch needs: a rectangle with a bite out of its
bottom edge. A fan over a concave polygon fills the concavity back in.

**Fix.** `poly` now tests convexity and ear-clips when it fails, and repairs
each triangle's winding against the polygon's own stored normal rather than
trusting the 2D projection's orientation. Convex polygons take the same fan as
before, so no existing geometry moved. `kit.arch_soffit` returns the intrados
curve so a caller can cut its spandrel to the same line the stones follow
instead of eyeballing a rectangle.

**Second half of the same bug.** The North Gate ALSO carried a full-width
facing slab on each face, which sealed the opening independently. Both had to
go. The lesson worth keeping: an opening that is authored in collision and
merely *implied* in geometry will ship, because every automated check passes.

---

## D-040 — Local -Z is outward, and `yaw_facing` is the only place that is decided

`Mesh.rotate_y(r)` sends local -Z to `(-sin r, 0, -cos r)`, so the angle that
aims a mesh's -Z along a direction `d` is `atan2(-dx, -dz)` — and `atan2(dx, dz)`
aims it the *opposite* way. Every gate in Hearthmere is authored with its
ceremonial face on local -Z and was turned by the second one. The result was
four gates with their arms, their lamps, their spur stones and their settled
jambs facing the market place, and mural towers flattened on their outer face
instead of on their back. It is invisible on anything symmetrical, which is why
it survived a review render.

`core.circuit.yaw_facing(d)` is now the only expression of it, and the outward
normal itself is derived from the polyline's signed area rather than assumed,
so re-winding the authored path cannot silently invert every section in the
file.

---

## D-041 — A mural stair is proved, not asserted, and that sets its slope

Three separate things had to be true before a player could stand on the
wall-walk, and none of them were:

1. **The flight has to be pointed.** All five authored stair positions are
   beside a gate or a tower, which is where a mason puts a mural stair and
   exactly what makes it hard. A flight centred on the authored point ran half
   its length into the drum next to it; measured, all five were blocked and the
   best of them reached 2.83 m of a 5.25 m climb. `_stairs` now scores every
   (direction, offset) candidate against gates, towers and the building slots
   that stand in the stair band, and takes the best.
2. **The flight needs its balustrade.** `tools/check_walkable.mjs` stores one
   standing height per lattice cell. A flight open on both sides has its treads
   reached sideways from the ground *first*, which pins them at ground level,
   after which nothing can climb them. A solid raking balustrade on the open
   side is what a mural stair has anyway, and it is what makes the flight
   provable. Reachable walk went from 6 stations to 35.
3. **A tower may not be one cylinder.** A single solid volume from ground to
   parapet severs the walk at every one of the eleven towers — it cut the
   circuit into eighteen unconnected segments, so each stair reached only its
   own stretch. The lower stage is now solid only to the walk (which the player
   stands *on*), and above it only the turret blocks; the turret is set
   outboard by design, so 1.1 m of walk passes inside it. 35 stations to 88.

**The cost, recorded.** The stair is **0.22 rise / 0.34 going**, steeper than
Art Bible section 3's domestic 0.175/0.28. A wall stair is steeper — stone, no
handrail, built to take up 5.2 m in the least length of Bailey it can. The
ceiling is not taste but the prover: a 0.5 m flood lattice can climb 0.35 m per
0.5 m of plan, so anything above a 0.70 slope is climbable by the real
controller and unprovable by the tool that gates the build. 0.65 leaves margin.

**Still open.** 88 of 257 walk stations are reachable from the spawn. The
remaining breaks are the four gates, where the ring stops and the walk is not
yet carried over the gate blocks — TOWN_PLAN section 5 says the walk is
continuous except over the Water Gate, so that is a real gap and it is the next
pass.

---

## D-042 — The bridge solves its span from the height field, and the road hands it over

`content/town/terrain.json` owns the Emberflow and D-024 moved it to cross Ford
Road at z = -90 so the bridge would land inside the departure frame. So
`venues/gatehouse.py` **walks the road line at 0.05 m intervals until the
ground drops below `terrain.water_level()`** and puts its abutments on the two
banks it finds, rather than carrying a copy of those numbers. If the water
agent moves the channel again the bridge follows it in the next build instead
of standing in a field. Three segmental arches, two cutwaters upstream with
triangular refuges over them, a deck 5.6 m between parapets, a crown at -0.90
and an east parapet 0.3 m lower than the west are the landmark record's own
words; only the division of the spans is solved.

The other half of the handshake is authored: `streets[].ford_road.bridged`
declares the stretch the carriageway does **not** lay, because a road draped
onto the height field over a channel is a ribbon of setts on the river bed —
which is what shipped, 25 stations of the main street under water. The deck
reads that same field and overlaps it by 0.6 m at each end, so neither side can
leave a quarter-metre of nothing at the abutment.

## D-038 — The natural layer is one venue, and a tree is an instanced LOD chain

**Context.** There was not a tree, hedge, fence, rock or planted bed anywhere in
576 m of Hearthmere. Two consequences, both visible from the air and both
structural rather than cosmetic: the walled town read as an undifferentiated
brown blob because nothing inside it broke the roofscape up at ground level, and
its edge followed nothing because the land outside was unmarked green felt with
a settlement dropped on it. A real town's plan is legible *because of* its plot
boundaries inside the wall and its field boundaries outside.

**Geometry and placement are separate files, and the split is not stylistic.**
`core/vegetation.py` owns shapes; `venues/landscape.py` owns where they go. A
tree is one shape used four hundred times, so it has to be built once,
instanced, and given an LOD chain — while *where* it stands is a question about
the town plan and belongs next to the plan. `landscape.py` invents no layout: it
consumes `buildingSlots[]` (94 plots), `openLots[]` (the orchard, churchyard and
two authored gardens), `streets[]`, `wall.path` and `terrain.json`'s water
channels. If a plot moves, the hedge round it moves.

**Foliage is cut-out cards with spherical normals.** The four leaf atlases are
alpha sheets of sixteen individual leaves; a canopy card maps a whole sheet, so
two triangles carry sixteen leaves and a real-scale canopy fits in a prop
budget. The normals are then blended toward the radial from the crown centre.
Without that blend a crown shades as a heap of independently-lit shingles — the
side facing the sun blows out, the other goes black, and the tree reads as
tinfoil. It is one line and it is the difference between foliage and confetti.

Three numbers had to be measured rather than guessed, and each was wrong by a
lot on the first pass:

- **Card size.** A leaf does not fill its atlas cell — `leaf_cards` draws a
  blade about 0.4 of the cell across — so a card sized for 130 mm leaves drew
  50 mm ones. `CARD_M` is 1.05 m, which puts an oak leaf at roughly 100 x 230 mm.
- **Card count.** At the first multiplier an apple got 146 cards over a 93 m2
  crown: 8% leaf coverage. Real foliage is nearly opaque; the target is 60-75%,
  which is about `9 x crown volume`.
- **Crown height.** Deriving the crown radius from a species ratio put an 8 m
  oak's highest leaf at 6.5 m — a 19% scale error on the most scale-sensitive
  object in an outdoor scene. The crown is now sized so its top lands on the
  tree's stated height.

**An impostor reaches the ground.** LOD3 is a 36-triangle opaque mass in one
material — no trunk, no cards, no alpha test. Sizing that mass to the crown
alone left two and a half metres of daylight under every distant tree, which at
LOD3 range is twenty-odd pixels of sky beneath a field of floating green
lollipops. Directive §6.1 is not suspended for impostors: the ellipsoid now runs
from just above the ground to the top of the tree and its own bottom vertex is
the trunk. The distance wood also starts at 206 m, not 168 m, because an
impostor is a 100 m-plus object and at 168 m the treeline stood 76 m from the
water meadow and rendered as a row of faceted crystals across the sky.

**A boundary may not cross a road, and that is enforced against the road
network.** Every boundary run is split by `_open_runs` wherever it enters a
street's corridor. The first churchyard wall was drawn round the whole authored
lot polygon and `tools/check_walkable.mjs` found it severing Kirk Green at the
lych gate and Kirkgate in fourteen places. Hand-authored gaps would have rotted
the first time a street moved; derived gateways cannot.

**A plot is grown, not proposed.** Hearthmere is dense: two thirds of its
buildings back directly onto another building or a lane. "Propose a 9 m plot and
shrink it on failure" placed zero plots out of ninety-four, and a smaller
proposal placed twelve. What a burgage plot actually *is* is everything between
this house and the next obstruction, so the depth and each side's width are
marched outward independently until they hit something — which also produces the
wedge-shaped plots and kinked back fences the schedule describes. 29 plots, 13
of them worked gardens.

**Two batching numbers, both measured.** The natural layer is everywhere and is
almost all thin geometry, so cell batching trades draw calls for culling
granularity the wrong way: at core's 16 m module it occupied 238 cells and cost
465 draw calls, more than every building in the town put together, to cull
hedges that are two triangles each. `CELL_SIZE = 48.0` — three town cells, so
the partition still nests. And the distance wood is generated as thirty-four
COPPICES rather than a uniform ring, because a GPU instance batch only pays
above `INSTANCE_MIN` per cell: 2,300 trees spread evenly put four or five in
each of 240 cells, every one below the threshold and therefore baked into a cell
batch of its own. Blocks of woodland put 70-190 in a cell, which is one draw
call — and is also what a wood looks like.

**Wind is a vertex shader keyed off the material name.** `core/venue.py` merges
every primitive in a cell into one mesh and puts four hundred trees into one
instance batch, so by the time `client/src/ambient.js` sees the town there is no
per-plant node left to rotate, and there never will be — that merge is what
keeps the town inside the §7 budget. `vegetation.SWAY_MATERIALS` is the whole
contract: amplitude scales with height above the primitive's own base, which is
why a tree is split into a `timber_grey` trunk and a `leaf_*` canopy. The trunk's
material is not in the list, so it stands still. The split is the rig.

**Known gap.** There is no `bark` material. Trunks use `timber_grey` and
`oak_weathered`, which are sawn-timber sets with the grain running along the
member — correct at gameplay distance, visibly not bark at two metres. The
market square's shade tree is the one place that will fail an art-director pass
on it.

---

## D-043 — `facingDeg` is a compass heading, and both renderers had it mirrored

`docs/TOWN_PLAN.md` §6 and `core/building.py::Footprint` define a heading as
`forward = (sin θ, 0, -cos θ)`: 0 north, 90 east, 180 south, 270 west. All 94
building slots are laid out with it, and every `facingDeg` in `content/` means
it.

`tools/render/town.html::dirFromDeg` returned `(-sin θ, 0, -cos θ)` — the
mirror — with a comment saying it matched `client/src/player.js`. It did match,
and both were wrong the same way. `client/src/main.js` seeded the controller
from the same number unnegated.

The cost was not academic. `playerSpawn.facingDeg` is 270 — due west, down the
nave and out through the great west door — and it pointed the arrival camera
**due east**. The single most important composition in the build
(BUILD_DIRECTIVE §3.2) rendered as the back of the bede houses, and the player
would have spawned in the church facing the chancel wall.

`player.js` keeps its own sign for free mouse yaw, so the conversion lives at
the one place content crosses into the controller:
`player.yaw = -(facingDeg) * PI/180`. `dirFromDeg` now returns
`(sin, 0, -cos)`. The `gate.west` (90) and `gate.water` (222) sightlines in
`content/town/hearthmere.json` were mirrored by the same bug and are now right
too.

---

## D-044 — The churchyard is a terrace, because the arrival frame is a geometry problem

The perron in front of the Church of Summoning cannot be seen from the altar
unless the ground at its foot is 0.80 m above Kirk Green. This is measurable,
not a matter of taste.

The altar eye is `(43, 4.92, -0.5)`. The occluder is the church floor's own west
edge at the threshold, `(x=32, y=2.40)`. The sightline that grazes it falls at
`(4.92 - 2.40) / 11.0 = 0.229` m per metre, and everything west of the threshold
below that ray is hidden behind it. `content/town/terrain.json` had the whole
precinct flat at 0.00 after D-024 deleted the Kirk Knowe rise, so the perron had
to fall the full 2.40 m in the 8.0 m between the west wall and Kirk Green — a
mean slope of 0.30. Every tread of it was invisible.

`docs/TOWN_PLAN.md` §3 already states the right answer in prose — "1.60 m, 10
risers at 0.16", "mean slope 0.20, deliberately shallower than 0.229" — and a
"Churchyard terrace ... rubble retaining wall, 0.9-1.6 m exposed, the graveyard
is the fill". Its own generated levels table disagrees, because the 0.80 m the
knowe used to supply went with D-024. The prose is right.

So `hm.pad.churchyard` (centre 40.5,-4.0, half 18.5x16.0, level +0.80,
apron 2.2) is authored into `content/town/terrain.json` through
`terrain.flatten_region` / `add_pad` / `persist`. It is an AUTHORED pad, so it
is applied before the generated ones and `hm.pad.church` still holds the ground
under the church itself at 0.00; the church's podium is sized to cover that pad
AND its whole 1.2 m apron, so the 0.80 m step between the two is buried inside
masonry and the podium face reads as the 1.60 m revetment the plan asks for.

Consequences accepted: `landscape`, `townhouse`, `streets` and `terrain` were
regenerated onto it; six slots round the churchyard now stand on deeper
underbuildings; `hm.townhouse.door.15` (song school) needs steps. D-020, "should
the knowe rise go back", is now partly answered: the 0.80 m under the churchyard
had to.

---

## D-045 — A perron tread is 0.80 m, and that is a declared exception to Art Bible §3

`ART_BIBLE.md` §3 puts step rise/going at 0.175 / 0.28 m, and
`tools/validate.py`'s `SCALE_RULES` enforces it on any constant named `GOING`.
The Church of Summoning's perron uses **0.16 rise / 0.80 going**, and
`tools/validate.py --venue church` flags it.

It is not an ordinary stair and it is not negotiable. D-044 sets the drop at
1.60 m; the flight has to hold a mean slope under 0.229 or the arrival frame
loses its foreground, which fixes the run at 8.0 m; ten risers into 8.0 m of run
is a 0.80 m going. At 0.28 m the same ten risers occupy 2.8 m, a slope of 0.57,
and the whole flight disappears behind the threshold.

Architecturally this is what a perron IS — a processional flight taken two paces
to the tread — and the Art Bible's table legislates for stairs people climb one
pace at a time. The constant is named `PERRON_GOING` rather than `GOING` so it
does not claim to be the thing the table governs, and this entry is the record
Art Bible §3 requires before that name change is legitimate rather than evasive.

---

## D-046 — A venue that calls `core.building` is a world-space venue

`content/town/hearthmere.json`'s `venues[]` gives every authored venue its
slot's centre and rotation as the root transform its geometry hangs under, and
`client/src/main.js`, `tools/render/town.html` and `tools/check_walkable.mjs`
all apply it. A venue therefore has to author in that rotated local frame. That
is the right contract for `pub`, `cottage` or `blacksmith`, each of which is a
single mass built about its own centre.

It is unworkable for anything that calls `core.building` or `core.roof`. Those
modules read the height field at **world** x,z — `Footprint.ground_samples`,
`terrain.pad_level`, `roof.wall_plate` — and hand back polygons in world
coordinates. Put that output under a rotated root and the building is
transformed twice: it lands somewhere else, on ground it was never levelled
against, with its collision in a third place.

The waterfront forced the issue. `quay` is authored from the wharf polygon and
the harbour basin and its own hero object, the crane, is slot 94 — 15 m from
the customs-house slot whose centre would otherwise have been the venue origin.
`warehouse` owns seven slots spread from the wharf to the Bailey and has no
meaningful single origin at all. `watermill` owns two, 26 m apart.

So `quay`, `warehouse`, `fish_eatery` and `watermill` take a **null root
transform** — origin `[0,0,0]`, rotation 0 — exactly as `townhouse`, `streets`,
`wall` and `market_square` already do, and author in world coordinates. The
decision lives in `tools/plan/townplan.py` as `WORLD_SPACE_VENUES`, not as a
hand-edit of the generated JSON, so a re-plan reproduces it.

**The rule this sets, for whoever builds the next venue:** if your module calls
`build_building`, `plan_building`, `wall_plate` or `roof_from_plate`, add
yourself to `WORLD_SPACE_VENUES` and work in world coordinates. If it does not,
either convention is fine and the local frame is usually easier.

Working in world coordinates does not mean working in world *axes*. Every
dimension on a wharf is measured along or across the quay, so `venues/quay.py`
builds in a wharf-local frame — `+X` along the quay to the north-east, `+Z`
landward toward the Water Gate — and places the whole group once through
`M.place`. Colliders and entities, which are consumed as world data, go through
`quay._w()`. The distinction is between an authoring frame the module owns and
a scene-graph transform the client applies; only the second one can silently
disagree with the height field.

## D-047 — The season is a vertex colour, and a broken venue module no longer stops the build

Two decisions from the foliage rebuild that outlive it. Full working:
`review/reports/foliage.md`.

**The albedo carries no season.** `core/materials.leaf_atlas` baked four of its
sixteen leaves bright autumn orange, and because a card that maps the whole 4x4
sheet draws every one of the sixteen — and `vegetation._atlas_rect` chooses the
whole sheet 72 % of the time — every canopy in Hearthmere rendered as
multicoloured confetti at 09:30 in high summer, with no parameter that could
turn it off. The season had been painted into the texture.

It is now a per-card `COLOR_0` tint applied at generation time
(`vegetation.AUTUMN`, and the `autumn` argument on `vegetation.tree` /
`tree_lods`), default 0.0. COLOR_0 multiplies into base colour, so it can only
darken and warm, which is exactly what a turning leaf does to a green one and
is why the result lands on a russet rather than the candy orange Art Bible §1
lists under "Not this".

**The rule this sets:** an atlas ships one population. Anything that varies
per instance — season, age, a diseased tree, a tree in shade — is a vertex
colour or a material tint on the *call*, never a second population on the
sheet. A sheet with two populations also needs two masked `hold_to` passes to
stay on §4, which was the other half of what that code was doing.

**`build.py --venue X` no longer dies because venue Y is half-written.**
`discover()` imports every module in `venues/` to find the ones with a `build`.
Thirty-two venues are written concurrently by different hands, so at any moment
one of them is mid-save; a `SyntaxError` in `moot_hall.py` meant nobody could
rebuild `landscape`, `church` or anything else. A failing import is now reported
and skipped. It is not silent: the failure prints, and `--venue X` on a broken
module still fails with "unknown venue X".

**And a warning that is not a decision.** `landscape` had been dropped from
`content/town/hearthmere.json`'s `venues[]` between the art director's pass and
this one, so the town was loading with no vegetation and no intramural ground
at all — every tree, hedge, tussock, garden, churchyard and the entire distance
wood, absent from every frame, while the meshes were still being built and
written. Nothing in the toolchain caught it: the mesh existed, the build passed,
`check_walkable` passed, and `t-report.json` simply had one fewer row. If you
edit that file, diff `venues[]` against the last review's `t-report.json`.

---

## D-025 — There is one siting class, and it is `core.siting.Site`

**Status:** decided. Supersedes the second half of the "warning that is not a
decision" at the end of D-047.

Two agents working in parallel each found the same defect — the plan's rotation
convention and the runtime's are mirrors, so a venue authored front-to-`−Z`
comes out up to 120° from its own slot polygon — and each shipped a different
cure into shared core, on the same day. `core/siting.py::Site` and
`core.venue::Plot` were two implementations of one `−2 * theta` correction,
with different names for the same frame (`design` vs `plot`), different
constructors, different ergonomics (`site.emit(ctx, g)` vs `p.emit(g)`) and two
independent readers and caches of `content/town/hearthmere.json`.
`venues/church.py` had a third copy, solved by hand in its docstring. CLAUDE.md
names this exact failure and it happened anyway, because two agents cannot see
each other's diffs.

**`core.siting.Site` is the single source of truth.** `Plot` is deleted, the
hand fix is deleted, the second town-document reader is deleted.

*Why `Site` and not `Plot`.* `Site` is a module named for the job rather than
191 lines at the bottom of a 53 k `venue.py`; it carries the whole derivation
in its docstring; and it already owned the ground — `base`, `lo`, `hi`,
`ground(x, z)` and the graded-pad lookup that Directive §6.1 requires and that
`Plot` never had. `Plot`'s better parts were absorbed rather than discarded:
`front`/`back`/`hw`/`hd`, `cell_at`, `instance`, `collider_from`, dict/list
collider passthrough, the `rotY` normalisation that keeps a `-0.0` out of an
unrotated plot's collision file, and — the one real ergonomic win — a bound
context, now `Site.bind(ctx)`.

*The church keeps its coordinates.* Slot 11 is `rotationDeg 270`, so the
correction is 180°, and `venues/church.py`'s 1400 lines are already written in
that turned frame. Re-authoring every hand-tuned interior coordinate to gain a
geometrically identical result is pure risk against the most important
composition in the build. Instead the file declares
`Site("church", authored=math.pi)`: core computes the correction, church
declares which pre-turn its source is in, and the residual is exactly `0.0`
today. `build()` raises if it ever stops being zero. **The arithmetic is in
core; only the declaration is in the venue.** This is the pattern for any
future venue that predates its slot.

*Three venues had no frame handling at all.* `inn` (90°), `guild` (90°) and
`blacksmith` (60°) are v1 survivors that used neither class, so nothing was
correcting them: the inn's and the guild's principal facades were pointing west,
away from the market place, at 21.3 m and 22.6 m of corner error, and the
blacksmith was 120° off its own yard at 19.8 m. They were not on anybody's
suspect list. `shop_row` (0°) and `pub` (180°) had zero error and were migrated
anyway, so that "every slot venue is sited by `Site`" is a property of the build
and not a coincidence of two rotations.

*It is proved, not asserted.* `tools/plan/townplan.py::check_siting`
re-derives design frame → `−2t` → `rotation.y = theta` → world **without
importing `core.siting`**, so a bug in the class cannot pass its own test, and
compares every footprint corner against `buildingSlots[].polygon` at a 1 µm
tolerance. Twenty venue slots, sixteen of them at a rotation where the two
conventions disagree, worst corner error 0.0000 mm. Remove the correction and
the same check reports errors from 0.70 m to 31.24 m.

**The rule:** a venue mesh is authored in the design frame — `+X` along the
frontage, `−Z` out of the front door, footprint `x ∈ [−w/2, w/2]`,
`z ∈ [−d/2, d/2]` — and reaches the world only through `core.siting.Site`. If
you need something siting-shaped, extend that class. A second one is a defect
even when its maths is right.

---

## D-026 — Regeneration is total: a venue module is placed, or declared unplaced with a reason

**Status:** decided.

`content/town/hearthmere.json` was clobbered twice by different agents, and two
concrete faults made that possible.

**`venues/landscape.py` existed, built, and was silently deleted from the town
on every regeneration**, because `landscape` was missing from `write_town`'s
hard-coded infrastructure list. The town rendered with zero vegetation, zero
gardens, zero churchyard and zero intramural ground for a whole wave. Nothing
caught it: the mesh existed, the build passed, `check_walkable` passed, and the
report simply had one fewer row. **A list that can be short by one without
complaining is not a list, it is a trap.**

The list is now `plan_data.INFRASTRUCTURE`, declared beside `VENUE_OF_SLOT` so
the two halves of "what gets placed" cannot go out of step, and
`townplan.py::check_placement_total` **fails the run** unless every module under
`tools/assetgen/venues/` is in one of exactly three states: placed on a slot,
placed as infrastructure, or in `plan_data.NOT_PLACED` with a written reason.
It fails on the reverse too — a placement with no module, which the client
would 404 on — and on stale or contradictory declarations. There is no fourth
state and no silent one.

**`lighting` and `ambient` were copied forward out of the file being
overwritten**, so a hand edit to either survived exactly until the next
regeneration and then vanished without a word. They are now
`plan_data.LIGHTING` and `plan_data.AMBIENT`, and `write_town` no longer opens
the previous document at all. Regeneration is a pure function of `plan_data`
and `content/town/terrain.json`, and is verified byte-identical across two
consecutive runs.

**Consequence for `venues/cottage.py`:** it is an orphan and now says so. It
builds `hm.cottage.01` on v1 cells that no `venues[]` row has ever referenced,
while `venues/townhouse.py` builds every `cottage`-kit slot in the schedule
from `buildingSlots[]`. It is declared in `NOT_PLACED` rather than deleted,
because deleting a module to make a build green is forbidden; deleting it
deliberately, in its own change, is the correct follow-up.

## D-048 — `streets` 94 → 155 draws is the streetscape, not a batching regression; the baseline is re-recorded

`review/perf-baseline.json` was recorded on 2026-08-01 with **10 venues
placed**. The gate in `tools/render/town.mjs` has failed ever since on two
rows — `streets` 94 → 155 and `shop_row` 36 → 43 LOD0 draws — reported as *"a
batching regression, not growth"*. It has been red and unowned for several
waves, which is the worst state a gate can be in: it is the only thing standing
between the town and forty commits that each cost twenty draws.

**It is not a batching regression. Measured, not argued.**

A draw in this build is one `(cell, material)` pair — `core/venue.py` emits one
batch node per 16 m cell, split into primitives by material. So the question
"did batching break" has an exact answer: *is any cell's primitive list
carrying the same material twice?*

| venue | LOD0 batch nodes | primitives | cells whose primitives are **not** one-per-material |
| --- | --- | --- | --- |
| `streets` | 32 | 155 | **0** |
| `shop_row` | 4 | 43 | **0** |
| `townhouse` | 70 | 769 | **0** |

Zero, everywhere. Per-cell per-material static batching (Directive §7) is doing
exactly what it is specified to do, and 155 is the arithmetic **floor** for the
content `streets` now carries, not a failure to merge.

What actually changed is coverage and material count. `streets` at baseline was
the v1 venue; it now surfaces the whole 192 m road network over **32 cells**,
with `street_props` and `earth` in 31 of them, `sett` in 28, `gravel` in 17,
`grass_worn` in 14 and `cobble` in 9 — 4.8 materials per cell. That variety is
the streetscape work `ad-town-02` §17 asks for *more* of ("Sty Lane has no road
surface... the roadnet is surfacing the primary streets and abandoning the
lanes"). `shop_row` is 4 cells at ~11 materials each, up 1.75 materials per cell
from the residue pass. And `townhouse` went **down**, 826 → 769, over 70 cells —
which could not happen if batching had regressed.

**Decision.** Re-baseline. The worst gameplay camera of the three recorded
(`square`, `arrival`, `gate-north`) is **727 draws / 1,154,547 triangles**
against §7's 900 / 3.5 M — inside budget with room, with 32 venues placed
against the baseline's 10. The gate is green again.

Recorded across three cameras on purpose: a single-view baseline reads 520
draws and would have under-recorded the worst case by 207, which is how a
budget gate ends up green on a town that is not.

**The lever this exposes, for whoever picks up perf next.** The cost is
*materials per cell*, not batching, so the only thing that reduces it is
**texture atlasing**. `street_props` + `earth` + `sett` + `gravel` + `cobble` +
`grass_worn` are six ground surfaces that could be one atlased material, which
would take `streets` from 155 draws to roughly 60 with no visual change. That is
also what `tools/validate.py`'s own LOD3 gate message already recommends, and it
is the single largest draw-call saving available in the build.

---

## D-049 — There is one environmental layer, it lives in `client/src/atmosphere.js`, and it is authored in content

**Context.** `review/reports/ad-town-02.md` answered the cohesion question with:
*"The individual pieces are not the problem; the absence of any shared
environmental layer over the top of them is."* Three of its findings are one
omission seen from three angles — §5 (no fog, haze or aerial perspective
anywhere), §13 (no ambient occlusion or contact shadowing anywhere), and
`docs/ARCHITECTURE.md` §5's grade LUT, which had been specified since the
architecture was written and never built. Every venue was lit. The world was
not.

Three renderers existed — `tools/render/town.html`, `tools/render/viewer.html`
and `client/src/main.js` — and each carried its own copy of the sky dome and its
own post chain. They had already drifted: only the venue viewer had any ambient
occlusion, and it was three's `SSAOPass` with a neutral-grey occlusion where
Art Bible §1 requires warm. A venue signed off in that viewer was signed off
against a picture the town render could not reproduce, which is D-023's failure
mode with a different name.

**Decision.**

1. **One module.** `client/src/atmosphere.js` owns sky, IBL, aerial
   perspective, the horizon skirt, ambient occlusion, bloom, the tonemap and
   the grade. All three renderers import it. Adding fog in three places would
   have been a fourth copy of exactly the divergence CLAUDE.md's *"extend the
   core, never fork it"* rule exists to prevent.
2. **One authored copy.** Every number comes from `atmosphere` in
   `content/town/hearthmere.json`, generated from
   `tools/plan/plan_data.py:ATMOSPHERE` — beside `LIGHTING`, under D-009's rule
   and for D-009's reason. `ATMOSPHERE_DEFAULTS` in the JS is a fallback for a
   viewer pointed at an older town document and is explicitly not the
   authority.
3. **The scattering is not `THREE.FogExp2`.** Uniform-density exponential fog
   is one colour at every height, so a town that falls 4 m to a river and a
   distance ring 300 m out haze identically and the frame flattens again in a
   new way. What is installed is an analytic height-integrated exponential with
   two colours — warm near, cool far — plus a forward-scattering lobe toward the
   locked 09:30 sun, patched into `THREE.ShaderChunk` so it reaches every
   material in the town including ones this module has never seen.
4. **AO is warm by ratio, not by multiplication.** Art Bible §1 asks that
   contact shadows tint toward `#4A3828`. Multiplying the beam by that colour is
   wrong twice: `THREE.Color` delivers it as **linear** (0.068, 0.038, 0.023),
   which removes 95 % of the light and leaves a hole rather than a warm shadow,
   and the pass runs before `OutputPass` where an sRGB literal means nothing at
   all. The tint is therefore normalised to unit luminance and used as a pure
   ratio (≈ 1.57 : 0.88 : 0.53) — occlusion takes blue out faster than red, so
   the crease goes warm as it goes dark — and how dark it goes is a separate
   number.
5. **The grade is a closed-form transform, not a sampled LUT.** The transform
   has to exist before it can be baked, and a closed form is what can be tuned
   against a render. `docs/ENGINE_PORTING.md`'s LUT bakes off it.

**Consequence, recorded because it changes what the client draws.**
`client/src/main.js`'s far plane goes **500 m → 2000 m**. 500 was inherited from
a build whose ground was a 300 m plane; the terrain plate is a 576 m square, so
its corners stand at 407 m and were being clipped out of the client's frame
entirely, and the horizon skirt reaches 1200 m. `tools/render/viewer.html` goes
1000 → 2000 for the same reason. All three renderers now agree, which is what
D-023 requires.

**Evidence.** `review/reports/atmosphere.md`. Value separation between the
foreground (0–22 m), midground (22–75 m) and background (> 75 m) depth bands is
measured by `tools/render/town.html:__valueBands()` and reported by
`tools/render/town.mjs --bands`; before and after come from the same build via
`--query atmos=0`. Before the layer, the background sat in the same value band
as the foreground or **darker** in four of six frames — an inverted depth cue,
which is why the build read flat. After, the ordering is monotonic in all six.

---

## D-050 — A roofscape is dealt by district, block and wealth, because a per-building roll is a dither

**Context.** `ad-town-02` §21: *"roughly 55–60 roofs, of which the great
majority are one saturated orange terracotta, scattered evenly among pale and a
handful of saturated blue. There is no clustering logic — no sense that one
street re-roofed after a fire, or that the poor quarter is thatched and the
merchants' slated. A real town's roofscape has runs and blocks."*

`core/building.py:ROOF_MATS` was keyed on **style**, and the weights were good —
that table was itself a fix for 62 of 63 buildings coming out in the identical
terracotta. But a per-style deal is by construction a dither: two neighbours of
the same style are two independent rolls, so the aerial reads as noise however
well the weights are chosen. Improving the weights cannot fix it.

**Decision.** What a roofscape records is history, and history is shared. The
covering is dealt in three stages:

1. **District.** `content/town/hearthmere.json:districts[]` already divides the
   town by economic cause, so `DISTRICT_ROOFING` hangs off that rather than off
   a newly invented map. Two districts are not a matter of taste but of law:
   the Fire Lane holds the ovens, the tallow and the charcoal and its own brief
   says it is *"separated from the thatch of the west lanes by the whole width
   of Ford Road"*; Smithward's says *"furthest from thatch"*. Neither may be
   thatched, and that one rule is most of what makes the aerial read as a town
   with a fire history rather than a texture.
2. **Block.** Within a district the covering is drawn **once per 26 m lattice
   cell**, seeded from the district and the cell rather than from the asset id,
   and every building in that cell takes it. This is the run.
3. **The odd one out.** One building in seven ignores its block, because a real
   street always has the house that did it differently.

**Wealth** re-weights the district's own palette: `role` and storey count from
the building schedule push slate and lead up and thatch down, so the market
place and Kirk Knowe go hard-covered together and the west lanes stay straw.

**The style keeps a veto, and `ROOF_MATS[style]` IS the veto list** — so the two
systems cannot drift apart, and adding a covering to a style is the only way to
let a block reach it. A slated block does not slate a thatch cottage or a byre;
a thatched lane does not thatch a warehouse. An explicit covering named in a
slot's `note` outranks everything, including the fire rule: `hm.slot.30.cottage_d`
is *"the last thatch left inside the wall"* and stays thatched in the Fire Lane
because the schedule says so.

**Measured** over the 70 kit slots: **34 of 40 occupied blocks (85 %) come out
single-covering**, Kirk Knowe splits 4 slate / 4 terracotta, the West Lanes 10
thatch / 4 terracotta, Southgate all thatch, and the Fire Lane 8 terracotta /
1 slate / the one authored exception.

---

## D-051 — A draw call is the whole frame, and one module counts it for every renderer

**Status:** accepted · supersedes the measurement half of D-048

`tools/check_client.mjs` reported **2,153 draw calls / 3.77 M triangles**.
`tools/render/town.mjs` reported **727 / 1.15 M**. Same town, same commit, same
`client/src/lod.js`. The project ran a whole wave with no way to say which was
true, and `review/reports/ad-town-03.md` closed its budget section on the 727.

**Neither was wrong. They were counting different things, and neither said so.**

The cause is one ordering in three.js r180 `WebGLRenderer.render`:

```js
shadowMap.render( shadowsArray, scene, camera );
...
if ( this.info.autoReset === true ) this.info.reset();      // AFTER the shadows
```

- `town.html` left `autoReset` at its default `true`. Every shadow draw it made
  was wiped from the counter before it read it, so its number was **the beauty
  pass alone** — while its report header said "scene pass + shadow pass" and its
  `shadowCalls` column printed 16. That 16 was not shadows at all; it was the
  handful of un-instrumented helpers (sky dome, water, the scale figure) that
  its own `onAfterRender` tally could not see. The harness also rendered the
  scene *twice* per shot — once bare to read counters off, once through the
  composer to make the picture — and reported the cost of the throwaway.
- `client/src/main.js` set `autoReset = false`, so its number was **the whole
  frame**: beauty pass, shadow maps, the GTAO pass's full normal+depth G-buffer
  (a second complete scene render), and every post quad.

### The decision

**Section 7's `< 900 draw calls` governs the whole frame.** Every draw the GPU
is asked to submit at a gameplay camera: scene + shadow + AO G-buffer + post. A
budget that is met by not counting two thirds of the draws is not a budget, and
the shadow pass is not free merely because section 7 also has a row for
shadow-casting *lights*: that row limits how many such passes there may be, this
one limits what they may cost.

`client/src/perf.js` owns the definition. It turns `autoReset` off, resets once
per frame, attributes every object draw to a stage via `onAfterRender` /
`onAfterShadow`, and wraps the composer so the AO pass's G-buffer is counted as
AO and not as a doubled beauty pass. `client/src/main.js` and
`tools/render/town.html` both import it; `check_client.mjs` and `town.mjs` print
the same decomposition. `hm.shoot({pos, look, fov})` renders the client from an
arbitrary camera and reports its cost, so the two can be compared from the
*identical* viewpoint instead of from two different ones.

Three further divergences were found and closed while proving parity, each of
which alone would have kept the numbers apart:

1. the harness aimed the sun with a **42 m** shadow box, the client with **60 m**;
2. the harness let **terrain cast shadows**, the client does not;
3. `check_client` ran a **1.60 aspect** viewport against the harness's 1.78, so
   the two frustum-culled different sets.

Measured after: at the identical arrival camera the client reports **1,380
draws** (scene 560 + shadow 526 + ao 227 + post 67, 209 batches) and the harness
**1,370** (scene 564 + shadow 526 + ao 230 + post 50, 209 batches). Batch count
and shadow count are identical; the 17-draw residual is full-screen post quads,
whose count follows the viewport (640x360 against 1600x900) and not the town.

### What the town actually costs

Worst gameplay camera (`square`), measured whole-frame, before any fix:

| stage | draws | triangles |
| --- | --- | --- |
| scene | 503 | 1,133,343 |
| shadow | 916 | 1,658,848 |
| AO G-buffer | 449 | 1,080,553 |
| post quads | 61 | 11,907 |
| **total** | **1,929** | **3,884,651** |
| **section 7 budget** | **900** | **3,500,000** |

Over on both. The shadow pass alone was larger than the beauty pass, and nothing
in either instrument could see it.

### What was done about it

The shadow pass was costing a full depth draw per batch whether or not the
shadow landed anywhere a player could see, so `client/src/lod.js` now decides
shadow casting per batch — `SHADOW_CAST_DISTANCE = 42 m`, no casting from
`cullAt` greeble, none from LOD2 or coarser — and the sun's ortho box came in
from +/-60 m to +/-46 m, which is both cheaper AND finer (2.2 cm/texel at 4096).
`atmosphere.ao.farDistance` went 80 m to 35 m: the AO prepass was 449 draws of a
1,929-draw frame, and past 35 m the scattering is already at ~60 % opacity, so
those draws were multiplying an occlusion term into haze.

Result at the same camera, after a full asset rebuild: **1,419 draws / 2,896,190
triangles** — triangles now
inside budget, draws still **1.59x over**. All three levers map 1:1 onto engine
settings (`r.Shadow.DistanceScale`, per-mesh Cast Shadow, AO distance), so none
of it is a web-only trick.

**The remaining 519 draws are not re-baselined away.** The beauty pass is 498
draws over 174 batches — **2.86 draws per batch**, because a batch is one
primitive per material and the town carries 846 materials across 35 mesh files.
Section 7's own required-techniques list includes *"texture atlasing across the
kit"* and it has never been done. That is the next lever and it is worth more
than everything above put together.

### The baseline

`review/perf-baseline.json` gains a `schema` field. The old baseline's 727 was a
scene-pass-only number; comparing it to a whole-frame number would produce a
screaming false regression, and the obvious way to silence a false regression is
to rewrite the baseline — which is precisely how a real one gets laundered
through. A baseline from a superseded instrument is now **refused, loudly, and
counted as a gate failure**, and the only way past it is a deliberate
`--write-baseline`. The regression check itself no longer switches itself off
when the town grows: it always runs, and compares draws per placed venue when
the venue count has moved. That silent switch-off is why a baseline stale at
`venuesPlaced: 10` sat unnoticed against a town of 32.

---

## D-052 — TEXCOORD_0 is quantized against one scale per file, and the tooling is made unable to read it raw

**Status:** accepted

Mesh memory measured **275.7 MB of `.bin` against the 240 MB budget** — 276.3 MB
of accessor data, broken down for the first time:

| attribute | bytes | share |
| --- | --- | --- |
| POSITION | 96.03 MB | 34.8 % |
| TEXCOORD_0 | 95.12 MB | 34.4 % |
| NORMAL | 47.56 MB | 17.2 % |
| INDICES | 30.49 MB | 11.0 % |
| COLOR_0 | 6.71 MB | 2.4 % |

D-042 had already quantized POSITION (int16), NORMAL (int8) and COLOR_0 (ubyte);
`validate.py`'s own note named the next lever as *"quantize TEXCOORD_0"*, and
`core/gltf.py` carried a comment explaining why that had been rejected: it would
need a `KHR_texture_transform` **per material** to undo the scale, so materials
could no longer be shared between primitives with different UV extents.

The premise was right and the conclusion was wrong. The scale only has to be per
material if it is *derived* per primitive. **Take one scale for the whole file —
the largest |uv| any mesh in it reaches — and every material in that file
carries the identical transform, so sharing is untouched.** Materials are never
shared across files, so a per-file scale costs nothing.

TEXCOORD_0 is therefore written last, as normalized SHORT, and every texture
slot gets `KHR_texture_transform.scale = [S, S]`. Eight bytes to four per
vertex. The quantum is `S / 32767`: 0.46 mm on the wellhouse (S = 14.95), 8.8 mm
on the 290 m ground venues, against textures that tile at 1-2 m and sample at
~3.9 mm/texel.

**Measured over a full rebuild of all 35 files: 275.7 MB -> 242.3 MB of `.bin`,
TEXCOORD_0 95.12 -> 50.82 MB.** From 14.9 % over the 240 MB budget to 1.0 % over,
and the residual is NOT re-baselined: every index accessor in the build is
already uint16 (32.51 MB, 6,274 primitives, zero uint32), no COLOR_0 primitive is
constant, and POSITION's 4-byte padding is mandated by glTF's vertex-element
alignment — so the next levers are the ones validate.py already names, splitting
`townhouse` by cell and reducing source triangles. `EXT_meshopt_compression` was
considered and rejected: it halves the download but not the GPU bytes, and
Unreal's importer does not read it, which trades hard constraint 1 for a number
that only helps the web build.

`KHR_texture_transform` joins `KHR_mesh_quantization` in `extensionsRequired`,
because a consumer that skips it samples every texture at 1/S of the authored
tiling. It is what gltfpack emits for exactly this reason and is supported by
three.js, Babylon, Cesium, the Blender importer, gltf-validator and Unreal 5's
Interchange glTF pipeline.

### The bug class this must not resurrect

D-042 quantized POSITION and `validate.py` went on summing raw accessor
`min`/`max`, so it reported every mesh in the build at **65,534 m across** and
raised fifteen false scale errors on a clean town — which is how a project
learns to ignore its own validator. The UV equivalent is a file that quantizes
TEXCOORD_0 and does *not* carry the transform: every texture then tiles at the
wrong rate, which looks like a material bug rather than a pipeline bug, and no
existing check would say a word.

So `check_quantization_contract()` in `tools/validate.py` asserts, per mesh file:

1. quantized attributes imply `KHR_mesh_quantization` in **extensionsRequired**;
2. quantized POSITION implies every mesh node carries `extras.hm.min/max`, so
   nothing ever *needs* to de-quantize by hand — the exact reach for accessor
   min/max that produced 65,534 m is closed off;
3. quantized TEXCOORD_0 implies `KHR_texture_transform` required, present on
   **every** texture slot of every material, and **exactly one** scale in the
   file.

A tool cannot now read one half of a quantized pair and get a plausible wrong
answer; it gets a build failure naming the file.

---

## D-053 — The silhouette camera is clipped to the town, and the three approach cameras are named views

**Status:** accepted

`review/reports/ad-town-03.md` judged the town's most-cited defect — *"the town
has no skyline"* — and could not use the instrument built for it:

> whether the tower is genuinely detached or its stem is hidden behind nearer
> terrain, **the instrument cannot tell me**

The `silhouette` view stands an orthographic camera 400 m north of the town so
the projection is a true elevation. The terrain plate is 576 m square and
`landscape` carries the field system and distance wood out to 270 m, so roughly
190 m of ground, hedge and tree sat **between the lens and the town**, painted
`SIL_LAND` grey, with the black roofline behind it. An orthographic camera has
no perspective with which to disambiguate that, so the only fix is to clip:
`near` now sits at the town's own north edge (with 6 m of margin so the north
gatehouse and the bridge parapet, which *are* skyline, survive), and `far` stops
short of the southern distance wood. The camera was also sitting at 0.72 x halfH
= 41 m over a town 0-22 m tall, putting the skyline in the bottom quarter under
60 % dead white; it is centred on the built band now.

The frame goes from a grey mass with two black shapes clearing it to the church
tower and spirelet, the guild tower, the moot bell-cote, the dovecote cone, the
chimney line and the quay all reading as a skyline. Note for the reviewer: at
192 m wide the vertical extent is pinned to 192/aspect by square pixels, so a
16:9 canvas can only ever give the town a fifth of the frame height — shoot it
letterboxed, `--views silhouette --w 1800 --h 520`, for the tightest read.

The art director's item 10 also asked for the three approach cameras they had
authored by hand to join the standard set. They are `approach-s`, `approach-ne`
and `approach-w` in `tools/render/town.html` now, with the exact numbers from
`review/shots/ad-town-03/approach-*-report.json`, and they are in the default
view list. A camera that a review verdict rests on cannot live in a shell
command inside a report: typed slightly differently next wave, it measures a
different town and the comparison is worthless.

---

## D-054 — `landscape` is exempt from the venue height ceiling: it is the ground, and the "34 m floating mass" does not exist

**Status:** accepted

`review/reports/ad-town-02.md` §7 and `review/reports/ad-town-03.md` §3 both
report an unidentified mass 28.29 m up inside the `landscape` venue, and pass 03
lists "find and delete the 28.29 m landscape mass" as a task. Two waves have
looked for it. There is nothing to find.

Measured by de-quantizing every LOD0 primitive in `landscape.gltf` through its
node TRS, the three highest are `tree_far` impostors at (−100.3, 252.1),
(18.1, 252.8) and (−73.6, 253.8), tops 28.29 / 28.01 / 27.28 m. `terrain.height`
at the first is **15.21 m**: they are the distance wood standing on the wooded
north ridge, 250 m outside the wall, on ground that legitimately rises to +21 m.
The venue's low point, −5.90 m, is the mere bed. 28.29 − (−5.90) = 34.19, and
that is the number `validate` was printing as a "height".

The controlling question — is anything floating over the *town* — was then asked
directly: for every LOD0 primitive inside the ±100 m town box, the highest
vertex against `terrain.height` at its own x/z. The answer is a **12.82 m oak at
(15.2, 15.8)**, then an ash at 11.77 m. Nothing in `landscape` floats.

`tools/validate.py`'s `LANDSCAPE` set already carried the right rule and the
right rationale — *"The ground is not a building. Its vertical span is the
landscape's relief (the distance ring rises ~28 m above the mere bed)"* — and
was simply never updated when the terrain venue was split into `terrain` and
`landscape`. `landscape.gltf` is in the set now.

The composition finding underneath the false alarm stands and is not closed by
this: the tallest thing on Hearthmere's northern skyline is a tree in the far
wood. That is ad-town-03 §3, and it is a skyline problem, not a floating mass.

---

## D-055 — A venue's height is measured from its datum up, not as its bounding box's vertical span

**Status:** accepted

`check_gltf` failed `church.gltf` at 22.3 m against `MAX_VENUE_HEIGHT = 22.0`.
The church's bounds are y ∈ [−0.35, +21.95]: 21.95 m to the bronze finial over
the lead spire, and 0.35 m of `rubble` foundation carried below the datum —
which `BUILD_DIRECTIVE` §6.1 *requires*, so that a building on falling ground
grows an underbuilding instead of floating.

So the check was counting buried foundation as building height. That is a
category error, not a scale error, and it applies to every venue in the town,
because every one of them is built to that rule. Acting on it as written would
also have meant shortening the tallest thing in Hearthmere in the same wave that
`ad-town-03` §3 asks for the church tower to become *more* visible.

Height is now `hi.y` — the top above the venue datum — falling back to the full
span for the degenerate case of a venue entirely below its datum, so a genuine
scale error still fires. `MAX_VENUE_HEIGHT` is unchanged at 22.0 m, the church
measures 21.95 m, and no geometry was touched.

---

## D-056 — A roof block is a quarter on a terrace, not a square on a lattice

**Status:** accepted

`ad-town-03` §5: *"the roofscape is still a checkerboard… tracing the south
block left to right: orange, cream, orange, cream, cream, orange, brown, orange.
There is no run anywhere in the town"*, with the cause given as
`ROOF_BLOCK_M = 26.0` producing about two buildings per block, and three
fallback paths re-rolling per asset instead of per block.

Both true. The block size was the smaller half of it: **a 26 m square laid over
the map cuts across the terraces**, so a "block" routinely held two buildings on
two different shelves with a retaining wall between them. Enlarging the square,
which is what §5 suggests (42–48 m), improves the statistics but keeps the
category error.

Hearthmere falls in seven authored shelves, already in `content/town/terrain.json`
as `hm.pad.terrace_*`. A shelf is what was cut, filled and built out in one act
of construction, and a district is who paid for it — so the block is exactly
`(district, terrace)`. `core.terrain.terrace_of(x, z)` answers the first half and
`core.building.district_of` already answered the second. Nothing is invented and
no lattice remains. Measured over the town's 94 building slots:

| scheme | blocks | mean masses | masses in a run of 3+ |
| --- | --- | --- | --- |
| 26 m square (before) | 46 | 2.04 | 48 / 94 |
| 42 m square (§5's suggestion) | 33 | 2.85 | 73 / 94 |
| 48 m square (§5's suggestion) | 31 | 3.03 | 78 / 94 |
| **district × terrace** | **26** | **3.62** | **85 / 94** |

The three re-roll paths §5 names are routed through the block RNG: the fire-ban
substitute, the empty-pool fallback and the style-veto substitute. The one-in-
seven odd-one-out keeps its own per-asset roll, deliberately — breaking the run
is its entire purpose, and it is what stops a ten-plot block reading as one
decal.

Not done here, and still open from §5: terracotta is the plurality in six of
eight districts, and `terracotta` is one flat material where it should be three
seeded tints. Both are colour decisions in the material pass, not mechanism.

---

## D-050 — A Worley cell field is crazy paving by construction, and that, not the UV scale, is what four passes have been rejecting

**Status:** accepted · closes the material half of `ad-town-04` §2 and §6 ·
extends D-046 (`resolve_uv`)

`ad-town-04` §2 names the town's single highest-value uncompleted item: *"421
literal `uv_scale=` call sites against 3 uses of `MATS.uv_scale()`"*, and
attributes the crazy paving on every street to that override — *"the pattern
lands at roughly three times its intended size."*

The first half is true and D-046 fixed it. **The second half is not true, and
building the whole wave on it would have changed nothing.**

`tools/uv_density.py` (new, and wired into `validate.py` as
`check_uv_density`) measures world area over UV area straight off the shipped
glTF, per material, weighted by world area. On the build that review was
written against:

| surface | authored | shipped | ratio |
| --- | --- | --- | --- |
| `cobble` — every street in the town | 2.00 m | 2.06 m | **1.03x** |
| `sett` | 2.00 m | 2.02 m | 1.01x |
| `flag` | 2.00 m | 2.00 m | 1.00x |
| `rubble` | 2.00 m | 2.09 m | 1.04x |
| `stone`, `limewash` | 2.00 m | 2.05 / 2.01 m | 1.02x / 1.00x |
| `terracotta` | 4.00 m | 4.07 m | 1.02x |

The scale that reaches the mesh is right to within 3 %. What was wrong is what
the pattern IS, and the answer was already written in this file:

> `rubble_weathered`: *"worley puts one feature point per cell of a uniform
> lattice, so it is isotropic by construction: what came out was random
> polygons with no bedding at all — crazy paving, stood on its end and called a
> wall."*

**A Worley cell boundary is the perpendicular bisector of two feature points.
It is dead straight, and three of them meet at 120°. A field of Worley cells is
therefore a field of straight-sided irregular polygons packed edge to edge —
which is the definition of crazy paving.** `rubble` was rebuilt on `coursed` on
exactly that reasoning and the review called the result the best masonry in the
build. The argument was never carried to the other four surfaces built the same
way, and between them they cover more of the screen than `rubble` does.

So the rule, stated once:

**A tiling surface made of discrete units is laid on `coursed`. `worley` is for
things that genuinely have no bedding — tussocks, plaster crackle, hammer
facets, the grain of a stone's own face — and it may never be used as a full
tessellation of a man-made surface.**

Rebuilt under it:

- **`cobblestone`** — 14 x 14 units on a 2 m tile (0.143 m cobbles),
  `bond=0.37`, `wobble=0.70`, `joint=0.085` = **24 mm of grit joint** against
  the previous hairline `smoothstep(0.0, 0.11, f2f1)`. A strong dome per stone
  instead of a flat top driven by the f1 distance, and per-stone height so the
  street is never flush. What keeps it from reading as `sett` — which is
  dressed, and having both is the point — is the wander, the dome and the fat
  joint.
- **`town_earth`** — `worley(30, "f2f1")` used directly as height made every
  cell a raised plate: 100 % stone coverage, a complete tessellation, and the
  surface the player is standing on in half the frames in the review set. This
  is `ad-town-04` §8's "crocodile skin" and **no pass has ever named it**,
  because everyone was looking at the paving. Now ~35 % of cells are proud and
  the rest is earth, with the per-stone value keyed to `worley(metric="id")`
  instead of an unregistered `fbm` at roughly the stone frequency.
- **`cobble_walling`** — already on `coursed`; the failure was elsewhere and is
  recorded below.

### The three defects that hide behind a correct recipe

Found by reading sheets, and all three are general:

1. **A `tint` after a value pass erases it.** `cobble_walling` carried its
   per-stone value in one `darken` with four `tint` calls around it, each a
   lerp at 0.6–0.9 over the same mask. Three lerps in a row leave a field of
   stones all very nearly the tint colour — `ad-town-04` §6 measured "about
   five luminance levels out of 255". **Family first, per-unit value last.**
2. **A mask that is 1 at the middle of a unit and 0 at its rim draws a
   bullseye.** `cobble_walling` painted all four tints through `dome`, so every
   stone got a radial gradient. A unit is ONE value across its face; the
   rounding belongs to the height map. Use `1 - joint`, never `dome`.
3. **A bed brighter than what it beds is grouting, not mortar.**
   `cobble_walling`'s base was `PLASTER_SHADE` (#D4C4A8, L* 79) — brighter than
   every stone in it.

Also, and it matters at range: **the joint shadow goes in the albedo and the
AO as well as the height.** At 20 m the normal map is three mips down and the
joint is the whole read.

### The tile-repeat rule, finished

`thatch_variant` was the last material carrying gradients in `v` and it had
four — age, bleach, moss and the eaves cut. The 2x2 repeat shows two hard eaves
bands and two age gradients per two tiles; on a 9 m cottage slope over a 4 m
tile that band appears twice, on a barn three times (`ad-town-04` §10). All four
are gone, replaced by `mottle` patches. **The eaves cut is not lost:**
`roof._thatch_slope` already builds the rolled eaves as geometry, which is what
it is in reality.

Its stems were also a fingerprint, and the cause was one number: `fibre`
phase-warps by `w * freq`, so `warp_amp=0.30` at `freq=170` displaces the phase
by **51 half-cycles** and what survives is the contour map of the warp field.
The usable band is narrow — I rendered `0.016` and got perfectly parallel
stripes, the failure `fibre`'s own docstring names — and `0.05` is the middle
of it.

### The terracotta split: three kilns, not three materials

`ad-town-04` asks for this twice and D-049's own closing note leaves it open.
`roof.kiln_batch(asset_id, mat)` puts a per-BUILDING multiplier in COLOR_0,
seeded from the asset id **alone** so every slope, hip and dormer of one
building come out of the same kiln. Three more texture sets would be ~34 MB and
two more batches on a build whose draw-call gate is already failed at
1,416/900; COLOR_0 is already on every roof vertex for the course jitter and
costs nothing. The batches are separated in saturation and hue as well as
value, because three roofs at three values of one orange still read as one
orange from 120 m, and `fired` is the rarest draw — the newest roof is the
rarest roof in a town two hundred years old.

### What now stops it coming back

D-046's `resolve_uv` makes a bare literal raise, which covers the 421 builder
sites. It cannot see the five places that lay UVs by hand —
`streets._Paving`, `landscape._surface_patch`, `market_square._paving`,
`roof._uv_scale`, `core/vegetation` — and between them those are most of the
ground and roof pixels in a street-level frame. `tools/uv_density.py` measures
the shipped glTF: over half a stop warns, 2x fails.

**Its atlas exemption is load-bearing.** A leaf card maps the whole 4x4 sheet
across one 0.49 m quad on purpose. `core/mesh.py`'s header currently claims the
chequerboard leaf grid of `ad-town-04` §4 was this number — it is not, the card
does not repeat, and "correcting" 0.49 m to 2.0 m would put four canopies of
sprig on every card and make every tree in the town worse. That claim should
come out of the comment.

---

## D-057 — The eleven wall towers are one authored LOD chain, because per-primitive decimation left their roofs hanging in the sky

**Context.** `ad-town-04` §7 and §(b) rejected the enceinte on "the wall does not
appear in the silhouette at all" and "towers stand only 2.6 m proud of a 6.3 m
curtain". The heights were raised (D-047) and the towers given cone, pyramid and
deliberately-open crowns. It changed nothing at distance, and the renders said
why: **`t-aerial-ne` showed eleven towers and not one roof, and `approach-ne` at
140 m showed a slate cone hanging 2.4 m above a flat-topped drum.**

**The mechanism, because it will catch the next venue.** `core/venue.py::_levels`
decimates **per material primitive**: `{k: B.decimate(m, 0.5) for k, m in
l0.items()}`, applied three times, so LOD3 is ~6 % of each primitive. In a 32 m
wall cell the `rubble` primitive is thirty metres of curtain plus one small drum —
6 % of it is the curtain, and the drum dissolves. The `slate` primitive in the
same cell is nothing but the spire, so 6 % of *it* is still a recognisable cone.
Nothing is dropped and nothing is culled; the two halves of one object simply
simplify at different rates because they are made of different stuff. Any small
feature in a large batch, made of a material the batch does not otherwise use, has
this failure mode.

**Decision.** The towers leave cell batching and become **one** authored chain,
`ctx.lod("hm.wall.towers", [towers_all])` — the documented escape ("where the
automatic vertex-cluster simplifier destroys something that has to survive — a
spire").

**One chain, not eleven.** Eleven authored nodes would cost eleven times two or
three primitives at every distance and buy per-tower frustum culling on objects
that are 20 k triangles in total. As a single node they are three draw calls, ~20 k
triangles, and they never dissolve. The trade is that all eleven are drawn whenever
any is; against a 900-draw budget that is three, and against a 3.5 M triangle
budget it is 0.6 %.

**One level, not four.** A short list is padded by repeating the last, so this
says "never simplify" once rather than authoring four coarse drums by hand. There
is nothing to win by simplifying eleven shapes that together are 0.7 % of the
town's triangles and are the entire reason the town has a skyline.

**Status:** accepted · consequence of D-047 · verified in
`review/shots/wall-market/crop/tower-far2.png` at 180 m

---

## D-058 — The shipped town file is compared to the plan AFTER the write, not before

**Context.** `townplan.py::check_siting` read `content/town/hearthmere.json` and
failed if `venues[].origin` or `buildingSlots[].polygon` disagreed with the plan.
`ad-town-04` §11 named two placement defects — slot 07's chophouse covering the
Grey Heron's elevation, and `hm.townhouse.door.15` unreachable behind
`church.parapet`. Fixing either means moving a slot in `plan_data.py`. Moving a
slot makes the shipped file disagree with the plan; the disagreement was a `FAIL`;
a `FAIL` returned before the write; and the write was the only thing that could
have made the two agree.

**The planner was un-runnable the moment the plan changed.** A check that forbids
the fix for the thing it is checking is a trap, not a check — and it is why both
of `ad-town-04` §11's placement fixes were authored in `plan_data.py` by an
earlier session and never reached the shipped file.

**Decision.** Split the shipped-file comparison out of `check_siting` into
`check_shipped(slots)` and run it **after** `write_town`, against what was actually
written. Same two assertions, same 11 mm tolerance. `check_siting` keeps the part
that is genuinely a priori — the corner-by-corner proof that the design frame and
the placement frame agree — and needs nothing on disk to do it.

**It still catches what it was built for.** The case that mattered was somebody
hand-editing `hearthmere.json`; the next planner run rewrites the file from the
plan and compares, so the edit is reported and reverted in the same pass.
`--check` runs it read-only against the file on disk.

Output line: `shipped: 94 of 94 slot polygons in hearthmere.json agree with the
plan to 11 mm`.

**Status:** accepted · unblocks `ad-town-04` §11

---

## D-059 — No street furniture stands on the market place's worn diagonal

**Context.** The lamp standard bisecting `t-square` top to bottom and cropping the
fountain has been rejected in **three consecutive art-director passes** (02, 03,
and `ad-town-04` §12). It also broke the instrument: `valueBands` for that view
returns `None`, because the lamp fills the whole foreground band and there is
nothing left to measure.

**Why it kept coming back.** Nobody placed it. `venues/streets.py::_furniture`
walks each street at 8–10 m stations and puts a vertical element on whichever side
has room. It works in street space and knows about junctions, doorways, building
masses, flights and bridges — it cannot see a plaza, a diagonal, or a camera.
Moving it by hand would have been undone by the next regeneration.

**Decision.** `streets.KEEP_CLEAR` — world XZ discs on which no street furniture
may stand — with one entry: **the market place's north-west crossing to the
fountain**, radius 4.6 m.

**This is art direction, not a camera dodge.** WORLD_BIBLE, "Market Place":
*cobbles worn into desire paths, polished smooth along the diagonal everyone
actually walks*, and `market_square.py::_paving` already polishes the stones along
that exact line. A market square keeps its crossing clear; a lamp planted in the
middle of one is wrong before any camera is pointed at it. The camera axis and the
desire path coincide because the camera was sited to look down the desire path.

The same rule governs the plaza's own dressing: `market_square._dress_lower_market`
keeps both trading pitches in the 10–16 m band and leaves the near ground swept.

**Status:** accepted · closes `ad-town-04` §12's first item

---

## D-060 — The sun is a cascade rig read from content, and it is one object in three renderers

`docs/ARCHITECTURE.md` §5 has specified "one directional key (sun) with cascaded
shadow maps" since before v2. What shipped was a single orthographic box —
4096 texels over a 92 m box, 44.5 texels/m, a 2.25 cm texel — declared FOUR
times: `client/src/main.js:83`, `tools/render/town.html`'s `CLIENT_SHADOW`,
`tools/render/viewer.html`'s `sc.*`, and `client/src/shadows.js`, a complete CSM
module that had been written and wired into nothing.

**Decision.** `client/src/shadows.js SunRig` is the sun, in all three renderers,
and its policy is authored in `content/town/hearthmere.json → lighting.shadows`
from `tools/plan/plan_data.py:LIGHTING`. Same rule as D-009 and for the same
reason: a harness whose shadow rig differs from the client's is not measuring the
client. The rig is derived from the CAMERA — `fitCascades` for any perspective
gameplay camera, `fitSingle` for the plan, the aerials and the silhouette — so
parity is structural rather than two expressions somebody has to keep matching.

**Two cascades and a 30 m reach, and the reach is the cost.** CSM sizes each
cascade's box by its frustum slice's far-plane diagonal, which at 55°/16:9 is
2.12x the slice's far distance. At the old 42 m reach the FAR cascade's box is
89 m — the same 92 m box again — so it holds the whole caster set on its own and
the near cascades are pure addition: three cascades at 42 m measured **+88 %
shadow draws**. The caster set is a disc of radius `distance` around the camera
and its AREA is what the shadow pass costs, so `lighting.shadows.distance` and
`VisibilitySet`'s `shadowDistance` are now ONE authored number. At 2 cascades /
30 m the near band is 352 texels/m against 44.5 and the whole gameplay frame is
1,385 draws against 1,416 before.

**What it costs:** a mass between 30 m and 42 m from the eye no longer casts.

**Status:** accepted · `review/reports/shadows-atmosphere.md` §1–2

---

## D-061 — A lift is an offset, so its colour is an offset; the grade's cyan was a multiply and it was invisible

`docs/ARCHITECTURE.md` §5: "lifted shadows, warm midtones, slight cyan push in
the shadows for complementary contrast." `makeGrade` implemented that as a lift
followed by `mix(c, c * shadowTint * 1.28, sh * shadowAmount)`. Read as code it
is exactly what §5 asks for. Evaluated on a neutral ramp it moved the darkest
step by **+1.0 in value and +1.5 in blue-minus-red out of 255**.

A multiplicative tint changes a pixel by a fraction OF THAT PIXEL. The pixels in
question are dark, so the entire complementary-contrast move fitted inside the
quantiser. It was being computed and rounded away, in all three renderers, for
as long as the grade has existed.

**Decision.** `shadowTint` is a DIRECTION, not a colour to multiply by: it is
normalised to unit luminance — leaving a pure hue ratio with no brightness in it
— and `shadowAmount` is how far the lift leans along it. The lift's luminance is
always `lift`, whatever the tint; only its hue moves. Each channel is floored at
zero, because a negative channel is not a tint, it is a crushed black, and Art
Bible §1 forbids those: `shadowAmount` may not exceed `lift / 0.247`.

Measured after, with `lift` 0.038 and `shadowAmount` 0.14: **+3.8 value and
+15.3 blue-minus-red** at the shadow floor, decaying to zero by 30 % grey. Same
transform shape, same two authored numbers, and `docs/ENGINE_PORTING.md`'s LUT
still bakes straight off it.

**Status:** accepted · `review/reports/shadows-atmosphere.md` §4

---

## D-062 — `fullDistance` is the temperature control, and raising it was the wrong direction

Two reviews asked for `atmosphere.scattering` to go `density` 0.0030 /
`maxOpacity` 0.62 / `fullDistance` **300**, to cure a measured
`temperatureSwing` of **0.2** on the arrival frame.

`fullDistance` is the only control over WHERE the warm near colour becomes the
cool far colour. At 130 m that crossover already sat beyond a 192 m town: every
distance a player ever looks at was still being mixed toward the warm cream, so
the cool far colour never reached the frame at all. Raising it to 300 m would
have removed the temperature separation entirely while fixing the veil.

**Decision.** The two halves of Art Bible §1 have separate controls and are
tuned separately. `density` 0.0058 → 0.0038 and `maxOpacity` 0.93 → 0.78 are
the VALUE half (the veil). `fullDistance` 130 → **82** is the TEMPERATURE half:
it puts the crossover inside the town's own depth. The two colours are pushed
apart in hue (near-to-far blue-minus-red 83 → 131) and pulled together in value,
with the far colour now DARKER than the near one — so distance stops meaning
"brighter" and starts meaning "cooler", which is what stops haze reading as milk.

Measured `temperatureSwing`: `gate-south` 25.5 → 47.1, `approach-w` 26.3 → 33.6,
`approach-s` 17.7 → 23.6.

**Status:** accepted · `review/reports/shadows-atmosphere.md` §3

---

**Numbering note.** D-057 to D-062 were assigned by the build session. Per the
owner's ruling on the D-036/D-040 collision, a documentation session's entries win
an ID clash and these renumber at reconciliation.

## D-063 — The look is anchored: Echoes of Aincrad and DragonSword: Awakening

**Context.** Owner direction, 2026-08-02: the look to go for is "how you would
describe the art direction and details of games like Echoes of Aincrad or
Dragonsword: Awakening." Both are 2026 UE5 releases; both are anime worlds
that deliberately reject the stock-photoreal UE5 look.

**Decision.** `REFERENCES.md` gains "The look anchors": the warmth,
saturation, and clean painterly surfacing of both worlds anchor Art Bible
§1's axis, which now cites them. The environment does **not** adopt their
cel-shading — materials stay stylised PBR and the anime read stays §1's five
tells. Both anchors cel-shade *characters* against a softer world; that
convention is recorded now for whenever characters return (D-012).

**Why.** "Semi-realistic anime" drifts with every reader; two named, shipped
games do not. A critic can hold a render beside a screenshot of either anchor
and ask the feel question concretely.

## D-064 — Variety is typed, not jittered

**Context.** Owner direction, 2026-08-02: "ensure variety of textures even if
it's for the same buildings. Like 5 different varieties of tudor houses,
single floor, double floor, etc., some with different materials but all
cohesively the same." The kit review had already named the failure:
"sixty-three shuffles of one house" (`review/reports/building-kit-01.md`).

**Decision.** Art Bible §1's idiom section gains "Variety within the idiom":
at least five distinct domestic house types (own plan, roof form, framing
rhythm) and at least three material dressings dealt across them by seed with
an adjacency constraint (neighbours differ). Jitter is explicitly not
variety: §6's variance stops repetition being detected, types and dressings
stop it being felt.

**Cost.** Kit work — but D-034's covering dealer already deals materials by
seed, so dressings extend an existing mechanism rather than adding a system.

## D-065 — Upper storeys are sealed

**Context.** Owner direction, 2026-08-02: "unless specified, all 2nd story
access is prohibited, so there's no need to interiorly decorate them."

**Decision.** BUILD_DIRECTIVE §1: no venue grants second-storey access —
stairs to upper floors are scenery or omitted, upper rooms are never
furnished, and upper windows read as shutters, curtains, or warm lamp spill,
never a modelled room. Ground-floor visible-through-door is unchanged; the
church's single tall volume remains the only full interior.

**Why.** Upper interiors are the most expensive space in the town and the
least seen. Sealing them by rule turns the "empty room" anti-reference into
a scope guarantee instead of a defect class.

## D-066 — Quality tiers reuse shipping mechanisms

**Context.** Owner question, 2026-08-02: how do Low→Ultra graphics settings
work so players without the specs can still run the town?

**Decision.** ARCHITECTURE §5 gains "Quality settings (Low → Ultra)": tiers
are a client-side profile over mechanisms that already ship — `MSFT_lod`
switch distances pull in, render scale drops, shadow resolution and local
shadow-light count step down, GTAO/bloom toggle, the clutter cull tightens,
and Low skips the top texture mip. No separate low-spec assets exist or are
authored. Vertex AO and the ACES grade are identity, never disabled. The
perf budget gate and the review harness run at Ultra; each cohesion round
includes one Low-tier spot render so no venue depends on a tier effect to
read.

**Status:** designed; client implementation pending.

## D-067 — Generated binaries leave git; session backups cover them

**Context.** Owner direction, 2026-08-02. Git was version control and asset
store at once: 415 generated files, 410 MB, `townhouse.bin` at 63 MB past
GitHub's 50 MB warning line (100 MB is a hard block), `.git` at 391 MB and
growing with every regeneration. Every byte of it is deterministic generator
output.

**Decision.** `assets/` is untracked and gitignored, joining `review/shots/`.
Git keeps the sources of truth: generators, `content/`, `docs/`, review
reports, `review/perf-baseline.json`. A fresh clone runs
`make setup && make assets` and gets byte-identical output. The generated
state is covered by timestamped zips in `backups/`, written by
`tools/backup.ps1` on every session start (SessionStart hook in
`.claude/settings.json`; skips if the newest zip is under an hour old; keeps
three). `backups/` sits inside the OneDrive-synced tree, so every zip also
leaves the machine.

**Cost, stated honestly.** Byte-level diffing of assets across git history is
gone — determinism is what makes that acceptable: any historical state is
reproducible from its commit's generators. Old asset blobs remain in git
history (history is not rewritten), so `.git` only stops growing; it does not
shrink. The backup zips are ~2 GB each; rotation caps the local cost at
three.

## D-068 — Docs split: game-wide base, per-area directories

**Context.** Owner direction, 2026-08-02: divide the documentation into base
foundations and Hearthmere's own set, future-proofed for many havens, routes,
caves, and dungeons.

**Decision.** `docs/areas/<area>/` holds each area's `BUILD_DIRECTIVE.md`,
its generated plan document, its `WORLD_BIBLE.md`, and its generated `plan/`.
Hearthmere's four moved there. Game-wide law stays at `docs/` top level. The
pattern and its five rules (never fork the base; register in
`docs/world/arkadion.md`; own entity prefix; scoped area law; one review bar)
live in `docs/areas/README.md`. The Art Bible gains a scope note naming its
Hearthmere-scoped sections (§2, §4, the idiom and variety sections).

**Verification.** 29 files' path references updated in the same change;
`tools/plan/townplan.py --check` passes with 0 problems after the move, and
the regenerated `content/town/hearthmere.json` carries the new paths.
Historical records (`docs/DECISIONS.md` entries, `review/reports/`) keep
their old paths on purpose — they describe the repo as it was.
