# Art Bible — Hearthmere

**This document is law.** Every asset in this repository conforms to it. If an
asset disagrees with the Art Bible, the asset is wrong. Changes to this file
require an explicit decision recorded in `docs/DECISIONS.md`.

**Scope note (D-068).** This bible is game-wide law, with four sections that
are **Hearthmere-scoped**: §2 (the non-technological constraint), §4 (the
locked palette and lighting), and §1's "The architectural idiom" and "Variety
within the idiom". Those bind Haven I absolutely; a future area declares its
own equivalents in its `docs/areas/<area>/BUILD_DIRECTIVE.md`, adding to the
shared registries through decision entries — never overriding this file. The
area pattern lives at `docs/areas/README.md`.

---

## 1. Style Target

**Modern 3D semi-realistic with anime sensibility.** The reference axis runs
between *Sword Art Online* (Town of Beginnings), *Shangri-La Frontier*, and
*Echoes of Aincrad*, benchmarked for production quality against *Final Fantasy
XIV* (Gridania / Ul'dah), *Guild Wars 2* (Divinity's Reach), and *World of
Warcraft* (post-Legion art standard).

The owner has anchored the look (D-063): **Echoes of Aincrad** and
**DragonSword: Awakening** are the definitive feel — see "The look anchors"
in `REFERENCES.md` for what is taken from each and what is not (their
cel-shading is not).

Concretely, that means:

| Axis | Target | Not this |
| --- | --- | --- |
| Proportion | Realistic human proportion, 7.5 heads | Chibi, stylized-squash |
| Material | Physically-based, idealized | Photoreal grime, muddy PBR |
| Saturation | ~15% above photoreal | Desaturated realism, candy-bright |
| Shadow falloff | Soft, lifted ambient floor | Crushed blacks |
| Silhouette | Bold, readable at 100 m | Noisy, detail-soup |
| Edge treatment | Everything chamfered | Razor-sharp CAD edges |
| Mood | Warm, inviting, safe | Grimdark, oppressive |

This is a **starting town**. The emotional brief is *arrival* — the player has
just entered the world. It must feel welcoming, alive, and slightly wondrous.
Nothing here is threatening.

### The anime tell

What separates this from straight realism, in order of impact:

1. **Rim light is always present.** Every hero object gets a cool rim
   (`#A9C6E2`) separating it from the background. This is the single strongest
   anime-3D signature.

   Implemented as a directional light, which is an approximation: a real rim
   affects only grazing angles, while a directional light lights every face
   turned toward it. On curved geometry that drains saturation — see D-010.
   Until a Fresnel term exists, the rim is deliberately desaturated and
   reduced to limit the damage.
2. **Ambient occlusion is warm, not grey.** Contact shadows tint toward
   `#4A3828`, never neutral black.
3. **Sky bounce is exaggerated.** Upward-facing surfaces pick up noticeably
   more sky colour than physical accuracy would give.
4. **Specular is tighter and brighter** than photoreal for the same roughness.
5. **Colour separation between planes.** Foreground/midground/background are
   pushed apart in value and temperature so the frame reads instantly.

### The architectural idiom

**The town is, for the most part, Tudor** (owner direction, D-040). The
domestic and commercial fabric — houses, shops, inns, workshops — is Tudor
vernacular:

- Exposed **timber framing**, close-studded on show frontages, with
  **jettied upper storeys** on street-facing buildings.
- Infill of lime-plastered wattle-and-daub or **brick nogging**, in the §4
  plaster tones; frame members in the §4 oak family.
- **Steeply pitched roofs** in clay tile or thatch, dealt per the covering
  rules; **tall, prominent chimneys** — a Tudor chimney is a silhouette
  feature, not plumbing.
- **Leaded casement windows** in small panes, as §2 already requires.

"For the most part" is load-bearing. Stone remains the mark of the sacred,
the civic, and the boundary: the church, the guild's tower, the town wall
with its gates and towers, and the bridge stay masonry per their World Bible
and Town Plan briefs. Timber town, stone institutions — the contrast is the
founding logic made visible, and it is what keeps Tudor from becoming a
theme park.

### Variety within the idiom (owner direction, D-064)

One idiom must never read as one house. The domestic kit ships **distinct
types, not jittered clones**:

- **At least five house types**, each with its own plan, roof form, and
  framing rhythm: single-storey cottage, storey-and-a-half with dormers,
  two-storey jettied townhouse, gable-end-to-street, and eaves-to-street.
- **At least three material dressings** dealt across every type: close
  studding with limewash infill, square panelling with brick nogging, and
  plaster-dominant with exposed corner posts — roof coverings dealt
  separately per the covering rules.
- **Dealt by seed, constrained by adjacency:** neighbours differ in type or
  dressing. A uniform run needs a recorded reason — a terrace built as one
  campaign is such a reason.
- **Jitter is not variety.** §6's ±3% variance stops repetition from being
  *detected*; types and dressings stop it from being *felt*. "Sixty-three
  shuffles of one house" (`review/reports/building-kit-01.md`) is the named
  failure.

Cohesion still wins: every type and dressing draws from §4's palette and
this idiom. Five houses, one town.

### The pattern book (D-076)

The idiom has numbers. Two builders on adjacent plots must produce roofs
that argue about nothing but their seeds:

- **Roof pitch by covering**: thatch 50–55°; plain tile 45–50°; slate
  38–42°. Stone civic buildings (church, guild, moot hall) may run
  shallower per their briefs — the vernacular may not.
- **Eaves overhang** 0.35–0.55 m; **verge** 0.15–0.25 m; exposed rafter
  feet on domestic work.
- **Jetty**: 0.45–0.65 m per jettied storey, dragon beams at corners.
- **Framing rhythm**: post bays 2.4–3.6 m; close studding at 0.35–0.45 m
  centres on show frontages.
- **Windows**: lights 0.45–0.55 m wide in oak mullions; domestic openings
  small and horizontal; leaded quarries per §2.
- **Doors**: per §3's split — thoroughfare and civic doors at the gameplay
  minimum, domestic doors at vernacular scale.

The generated building schedule grows `eaves`/`ridge` **height** columns so
every mass's roof is checkable against these ranges (checker support
pending).

---

## 2. Non-Technological Constraint

Hearthmere predates industry. This is an **absolute content filter** — the most
common way a fantasy town breaks immersion is anachronism.

**Permitted:** timber framing, mortise-and-tenon joinery, wattle and daub, lime
plaster, fired clay, hand-forged iron, bronze, riveted joins, rope, leather,
oiled canvas, hand-blown glass (small panes only, leaded cames), tallow and
beeswax candles, oil lamps, water power, animal power, gravity-fed plumbing.

**Forbidden:** any machined or extruded metal, screws (use nails, pegs, rivets),
springs, plate glass, milled dimensional lumber with uniform section, plastic,
rubber, printed or stencil-repeated text, standardized fasteners, coil springs,
wire rope, chain of uniform machine links, painted line markings, anything
suggesting electricity or combustion engines.

**Signage is pictorial, never typographic.** Shops advertise with carved or
forged icons — a boot, an anvil, a wheat sheaf. This is both period-correct and
solves localization. No readable lettering anywhere in the world.

**The sign language (D-077).** With lettering banned, signs are the town's
wayfinding — one language, not ninety-four dialects:

- **One bracket family**, wrought, three variants: plain scroll (shops),
  heron scroll (civic), lantern-and-board (licensed houses). Mounted at
  2.6 m to the bracket, board clearing §3's 2.20 m awning line.
- **Board sizes**: 0.75 × 0.55 m for shops; 0.9 × 0.7 m for the inn, pub,
  and guild.
- **Icons are silhouette-first**: one object, carved or painted, readable
  black-on-white at 30 m — a boot, an anvil, a sugar loaf. If it needs a
  second object to parse, it is wrong.

Corollary rules that catch most mistakes:
- Nothing is perfectly straight or perfectly repeated. Hand-made means variance.
- Every join must be physically explicable — if it holds weight, show how.
- Wood grain runs along the structural axis of the member, always.
- Iron shows hammer facets; it is never smooth-extruded.

---

## 3. Scale Standard

**1 unit = 1 metre. Y-up. Right-handed. -Z forward.** (glTF 2.0 convention,
which imports without transform fixup into both Unreal and Unity.)

Scale is the most common source of "something feels off but I can't say what."
These are not suggestions:

| Element | Dimension |
| --- | --- |
| Player character height | 1.75 m |
| Player eye height | 1.62 m |
| Shoulder width | 0.45 m |
| Door opening | 2.10 m × 0.95 m |
| Door head clearance to lintel | 0.15 m |
| Interior floor-to-ceiling | 2.70 m |
| Floor-to-floor (multi-storey) | 3.20 m |
| Step rise / going | 0.175 m / 0.28 m |
| Handrail height | 0.95 m |
| Table height | 0.74 m |
| Bench seat height | 0.45 m |
| Counter / bar height | 1.05 m |
| Market stall counter | 0.90 m |
| Stall awning clearance | 2.20 m |
| Street width (main) | 7.0 m |
| Street width (side alley) | 2.5 m |
| Doorway-to-doorway across alley | 4.0 m min |
| Cobble stone (long axis) | 0.12–0.22 m |
| Roof tile exposure | 0.16 m |
| Timber frame post section | 0.18 × 0.18 m |
| Barrel (height × belly dia.) | 0.88 m × 0.62 m |
| Crate | 0.55 m cube |
| Cart wheel diameter | 1.15 m |

### Gameplay minimums and the vernacular (D-076)

The table above is the **gameplay minimum** set — thoroughfares, the
church, the guild, and any route the player must walk. The Tudor vernacular
is smaller, and domestic buildings use it: door openings 1.85–1.95 m ×
0.85 m, interior floor-to-ceiling 2.2–2.4 m with exposed joists,
head-brushing beams permitted where the player is never forced through
them. The pub's heavy low beams are its identity, and they are legal — its
circulation route still meets the gameplay minimum. Camera consequence per
ARCHITECTURE §5: vernacular rooms collapse toward first person, and that is
the intended feel, not a defect.

**Camera reference:** the gameplay rig — third-person, boom 3.6 m, camera
height 2.05 m, 55° FOV (single source: ARCHITECTURE §5 "The gameplay
camera", D-069). Every asset is judged from that camera, not from a hero
close-up. If it only looks good at 0.5 m, it is not finished.

---

## 4. Locked Palette

Hex values are **sRGB-encoded authoring values**, decoded to linear on
import — exactly what a hex colour is everywhere else (D-075; the previous
"linear-space targets in sRGB notation" wording was self-contradictory). All
albedo maps stay within these families; deviation requires a recorded
decision. The palette is only meaningful through the locked viewing
pipeline, which is law: linear-light rendering, exposure 1.05, ACES filmic
tonemap, then the warm grade — lifted shadows, warm midtones, cyan-pushed
shadow hue (implementation in ARCHITECTURE §5). A palette check compares the
render *through that pipeline* against the swatch sheet — never raw hex
against screen.

### Architecture

| Role | Hex | Notes |
| --- | --- | --- |
| Lime plaster (primary wall) | `#E8DCC4` | Warm off-white, the town's base value |
| Lime plaster (shadowed variant) | `#D4C4A8` | For south and west faces and recesses — the faces the locked sun does not reach (D-075) |
| Oak timber (fresh) | `#8B6F47` | Frame members, doors |
| Oak timber (weathered) | `#6B5638` | Sun-facing, older structures |
| Oak timber (dark stain) | `#4A3728` | Structural posts, beams |
| Terracotta roof | `#B5603E` | Primary roof material |
| Terracotta roof (aged) | `#8F4E36` | Variation, ~30% of tiles |
| Slate roof | `#5A6270` | Secondary roofs, wealthier buildings |
| Cobblestone | `#8A8578` | Street paving |
| Cobblestone (wet/worn) | `#6E6A60` | Traffic paths, gutters |
| Foundation stone | `#9A9083` | Plinths, walls to 0.8 m |

### Metals

True metals are authored as **F0 reflectance** — the colour a metal actually
reflects — never as their "look" in shade. A dark albedo at metalness 1.0
renders as a black cutout (the anti-reference list's "black metal"), which
is why the pipeline was already shipping fractional metalness off-book; that
deviation is now sanctioned and bounded (D-075). Values are standard PBR F0
references — verify against the swatch sheet at the locked rig.

| Role | Hex (F0) | Roughness | Metalness |
| --- | --- | --- | --- |
| Wrought iron (bare) | `#8E8E8D` | 0.55 | 1.0 |
| Hot iron (forge) | `#FF7A2E` | 0.40 | 1.0, emissive carries the heat |
| Bronze | `#F0C0A0` | 0.35 | 1.0 |
| Steel (polished blade) | `#C8CCD4` | 0.15 | 1.0 |
| Brass fittings | `#E8C88A` | 0.28 | 1.0 |

Painted, limed, or heavily oxidised ironwork is a **dielectric** — this is
where the dark values live:

| Role | Hex | Roughness | Metalness |
| --- | --- | --- | --- |
| Ironwork, blacked / limed | `#3A3632` | 0.55 | 0.0–0.3 |
| Copper (verdigris) | `#5FA88C` | 0.70 | 0.0 |

### Accent & Life

| Role | Hex | Notes |
| --- | --- | --- |
| Guild banner crimson | `#A32C34` | Adventurer's Guild identity |
| Innkeeper green | `#4A7C59` | Inn awnings, shutters |
| Pub amber | `#C87F2A` | Pub signage, warm interior glow |
| Market canvas cream | `#DCC9A0` | Stall awnings, base |
| Market canvas stripe | `#9C4A3C` | Awning stripe, ~40% of stalls |
| Herb green | `#6B8E4E` | Planters, produce |
| Produce accent | `#D4832F` | Pumpkins, gourds, warm goods |

### Water (D-077)

| Role | Hex | Notes |
| --- | --- | --- |
| Shallow / bed tint | `#6E7A6A` | The ford, margins, fountain basin |
| Deep water | `#2E4A52` | The Mere, the dredged basin |
| Foam / broken water | `#DCE4E2` | The weir, the ford riffle, bow waves |

### The district colour script (D-077)

One palette, eight biases (district names per TOWN_PLAN §2 — where a name
differs there, the plan is right). Buildings draw the same families; each
district applies a bias so a street photographs like its cause:

| District | Value | Temperature | Bias |
| --- | --- | --- | --- |
| Kirk Knowe | high | neutral-warm | clean plaster, pale stone; lowest wear |
| Market place | mid-high | warm | densest accents; canvas and produce carry the colour |
| The Fire Lane | mid | warm | soot above openings; charred timber ends |
| Quayside | mid | cool | silvered timber, algae line, tar blacks |
| West Lanes | low-mid | neutral | damp plaster, moss greens, high wear |
| The Bailey | low | cool-neutral | patched everything; wear index 4 |
| Smithward | mid | warm | cinder greys, scorch, iron staining |
| Gate wards | mid | neutral | travel dust, worn thresholds |

**Dominance ratio** for any single building: roughly 60% wall field, 25%
timber/stone structure, 10% roof accent, 5% painted accent. A building
one-third guild crimson is out of palette no matter which hexes it used.
Filler shutters and doors draw from a five-colour family (`#4A7C59`,
`#9C4A3C`, `#5A6270`, `#C87F2A`, `#6B5638`) dealt by seed.

### Lighting

**The authoritative copy of this rig lives in `content/town/hearthmere.json`
under `lighting`.** Both `tools/render/viewer.html` and `client/src/main.js`
read it. Do not hardcode these anywhere — see D-009 for why.

| Role | Hex | Intensity |
| --- | --- | --- |
| Key (sun, mid-morning) | `#FFF2D8` | 3.2 |
| Sky fill (hemisphere top) | `#AFC9E0` | 1.35 |
| Ground bounce (hemisphere bottom) | `#8A7352` | 1.35 |
| Warm ambient floor | `#6B5A46` | 0.55 |
| Warm bounce (shadow side) | `#C9A87E` | 0.55 |
| Rim / separation | `#A9C6E2` | 0.85 |
| Forge fire | `#FF8C42` | 4.0, flickering |
| Candle / lamp | `#FFB35C` | 1.8, gentle flicker |
| Window interior spill | `#FFD9A0` | 2.2 |

**Time of day is locked to mid-morning, ~09:30.** Sun elevation 38°, azimuth
125° — **azimuth measured clockwise from +Z (south); compass equivalent 55°,
sun in the east-north-east**. World-space direction *to* the sun:
`(0.645, 0.616, −0.452)`. State it that way in any port: typing "125°" into
a compass-convention sun rotates every shadow in Hearthmere by 70° (D-075).
At this hour the **north and east elevations are the lit ones**; shadowed
palette variants belong on south and west faces. This gives
long-but-not-extreme shadows, warm key, and strong sky fill. All review
screenshots use this exact setup.

Emissive intensities in the table above are relative to the locked exposure
(1.05) and the bloom threshold (1.0): an emissive is correct when it reads
at 09:30 without blooming out. The pub and forge, whose identity is
firelight, additionally carry a declared night/interior review condition
(D-078). **Day and night are committed as design** — the 09:30 lock is a
production stage, not world law, and nothing may be authored in a way that
forecloses a day cycle (D-078).

The rim row is the authored directional approximation (D-010); the
screen-space rim pass in ARCHITECTURE §5 is the target implementation. When
it lands, the rim's saturation and intensity are re-tuned and this row is
updated — open item, D-075.

---

## 5. Material Standard

Every material is authored as a full PBR set. **No untextured flat colours
anywhere.** A flat-shaded surface is the fastest way to look like a prototype.

Required channels per material:
- **Albedo** (RGB) — base colour, no baked lighting, no baked AO
- **Roughness** (R) — never uniform; every surface has roughness breakup
- **Metalness** (R) — 0.0 or 1.0 by default; fractional values are the
  recorded exception for bare ironwork under weak IBL and for worn
  metal-through-paint transitions (D-075)
- **Normal** (RGB, tangent-space, OpenGL +Y) — surface detail
- **AO** (R) — cavity occlusion, multiplied into indirect only

Optional: **Emissive** (RGB) for forge, lamps, windows.

Channels ship **ORM-packed** — R=AO, G=roughness, B=metalness in one
texture — the native packing for glTF, Unreal, and Unity (this is what the
pipeline builds; the five channels above are the *authoring* contract).
Albedo is sRGB; ORM and normal maps are linear data.

### Texel density

| Class | Density | Use |
| --- | --- | --- |
| Hero | 512 px/m | Anything the player stands within 2 m of — counters, doors, signage, blacksmith anvil |
| Standard | 256 px/m | Building faces, props, stalls |
| Large | 128 px/m | Roofs, street paving, distant walls |

Tiling materials are authored at 2 m × 2 m world coverage per tile unless noted.

### The roughness rule

**Uniform roughness is the single biggest tell of amateur work.** Every material
must have roughness variation from at least two sources:
1. Broad variation (large-scale noise, 0.5–2 m) — weathering, dampness
2. Fine variation (small-scale noise, 1–5 cm) — surface microstructure

A wet cobble path is not "roughness 0.3." It is roughness 0.65 broken by
puddle regions at 0.12 with soft transitions, plus per-stone variance.

### Wear and story

Every surface answers: *where do hands touch it, where does water run, where
does the sun hit, what is it standing in?*

- **Edge wear** — corners and protruding edges lighten and smooth (paint and
  patina rub off, exposing substrate). Drive with a curvature mask.
- **Dirt accumulation** — crevices and downward-facing corners darken. Drive
  with an inverted-curvature + AO mask.
- **Water streaking** — vertical runs below sills, ledges, and roof edges.
- **Touch polish** — door handles, counter edges, stair nosings, bar tops, and
  the top of every barrel at 0.88 m get smoothed roughness and slight darkening.
- **Ground contact** — the bottom 0.35–0.5 m of every wall gets splash
  dirt, dense at the base with a soft upper edge. Rain splash-back is
  knee-high, not ankle-high (D-077).

### The wear index (D-077)

Wear has a quantity, not just a mechanism. Every venue brief carries a
**wear index 0–5** — 0 new-built, 5 derelict — defaulted by district and
age (the Bailey's cottages run 4; the guild's imported ashlar runs 1) and
applied consistently across a building's materials. Two venues at the same
index weather the same amount. "Physically motivated" no longer passes both
a pristine and a ruined version of the same cottage.

### Water (D-077)

Hearthmere is a lake town; water is a first-class material, not a blue
plane:

- **Colour by depth** — shallow water tints toward its bed (`#6E7A6A`);
  deep water absorbs toward `#2E4A52`; the Mere at distance reads as the
  sky's value, one step darker.
- **The waterline band** — everything within 0.5 m of standing or flowing
  water is wet: darkened albedo, dropped roughness, algae per its brief.
  The quay stair's bottom treads, the fountain rim, the bridge piers.
- **Motion** — two counter-scrolling normal layers (the shipped technique);
  flow direction follows the Emberflow's course, never a tiling default.
- **Foam** — a narrow broken-water line where moving water meets stone;
  none in open water at this wind.
- **Reflection budget** — planar/screen-space reflection is an Ultra-tier
  effect; the base read must hold with IBL alone.

---

## 6. Geometry Standard

### Bevel everything

**No razor-sharp edges exist in the real world, and their absence is instantly
readable as "cheap 3D."** Every hard edge gets a chamfer sized to catch a
specular highlight at gameplay distance:

| Object class | Chamfer |
| --- | --- |
| Architectural (walls, beams, posts) | 15 mm |
| Furniture, props | 8 mm |
| Handheld / small metal | 3 mm |
| Worn / ancient stone | 25 mm, irregular |

This is non-negotiable and is the first thing the art director check looks for.

### Silhouette first

Build in this order, and check the silhouette at each step:
1. **Primary form** — the blockout mass. Must read at 100 m.
2. **Secondary** — the elements that break the primary silhouette: roof
   overhangs, chimneys, awnings, brackets, signage arms, dormers. Must read
   at 30 m.
3. **Tertiary** — the detail that rewards approach: hardware, joinery, wear,
   small props. Reads under 5 m.

If the object is boring in black-on-white silhouette, no amount of texturing
saves it.

### Asymmetry and variance

Hand-built means nothing repeats exactly. Mandatory variance:
- Position jitter on repeated elements (cobbles, tiles, planks): ±3%
- Rotation jitter: ±2°
- Scale jitter: ±4%
- No element may appear more than 3 times in a row without a variant
- Visible imperfection is dealt at a **rate, not a rule** (D-077): roughly
  70% of domestic masses carry one visibly *wrong* element — a sagging beam,
  a patched wall, a mismatched shutter — dealt by seed, biased by district
  age and wealth. The guild (imported, expensive, deliberately alien) and
  the newest work carry none. A wonky thing on every house is itself a
  uniformity.

### Poly budget

Budgets are per-instance, LOD0. Modern GPUs are not vertex-bound at this scale;
these exist to keep memory and streaming sane, not to force ugliness.

| Class | LOD0 tris |
| --- | --- |
| Hero building (inn, guild) | 60k |
| Standard building | 30k |
| Market stall | 12k |
| Large prop (cart, forge) | 8k |
| Medium prop (barrel, crate) | 1.5k |
| Small prop (mug, tool) | 500 |
| Modular kit piece | 2k |

LOD chain: LOD0 (0–15 m), LOD1 @ 50% (15–40 m), LOD2 @ 20% (40–100 m),
LOD3 @ 6% / impostor (100 m+).

### What a LOD may not lose (D-078)

The 100 m views are the town's best views, and they are drawn entirely from
coarse LODs — the town that ships is the town at LOD2, not the review
close-up:

- **Silhouette survives to LOD3**: chimneys, jetty steps, gable lines, and
  every venue's anchor element. Decimation may not flatten a roofline.
- **Chamfers may collapse at LOD2** (sub-pixel past 40 m); normal maps
  persist through LOD2 and may drop at LOD3.
- **Apparent colour is LOD-stable** — material collapse follows the by-area
  dominance rule (D-028); a building may not change colour when it changes
  LOD.
- **Transitions dissolve** (dither crossfade), never pop.
- Every review packet includes **one LOD2-range render (60–100 m)**; the
  silhouette axis is scored against it as well as LOD0.

---

## 7. Composition & World Building

### Density layering

A world feels alive through **layered density**, not uniform clutter. Each
venue is composed as:

- **Anchor** — the one silhouette that identifies the venue from across the
  square (the forge chimney, the guild's banner tower, the inn's sign).
- **Function** — the objects that prove the venue works (anvil, quench barrel,
  tool rack). These must be arranged as a *working person* would arrange them,
  by workflow, not by symmetry.
- **Residue** — evidence of recent human activity. This is what actually sells
  life: a half-finished job on the bench, a cloak over a chair back, spilled
  grain, a cat asleep in the sun, boot scuffs at the threshold, a mug left on
  a rail.

**Residue is the highest-value detail per unit of effort.** A perfectly modelled
empty room reads as dead. A modest room with a stool knocked over and tools mid-
task reads as inhabited.

### Sightline rules

- No wall of undifferentiated facade longer than 12 m without a break
  (recess, projection, material change, or vertical element).
- Every street must terminate in something worth walking toward.
- Frame the market square so that from each of its entrances, at least two
  other venues are visible — this drives player navigation without a map.
- Vertical interest every 8–10 m along any street: a hanging sign, a banner,
  a lamp bracket, a first-floor overhang, a window box.

### Movement and life

Static worlds read as dioramas. Required motion:
- Cloth: awnings, banners, laundry — gentle wind, 0.3–0.8 Hz
- Fire: forge, lamps, hearths — flicker at 8–12 Hz, subtle
- Smoke: chimneys, forge — slow drift
- Water: fountain, troughs — flowing normal maps, ripples
- Vegetation: window boxes, vines, potted herbs — wind sway
- Ambient particulate: dust motes in sun shafts, forge sparks, pollen

All drift takes its direction from `ambient.wind` in
`content/town/hearthmere.json` — cloth, smoke, laundry, steam, and
vegetation lean the same way, or the town reads as a collage (D-077).
Smoke rises from every lived-in chimney, not a shortlist; generating the
source list from the building schedule is pending.

---

## 8. Definition of Done

An asset is done when **all** of these are true. This is the checklist the
art-director review runs.

- [ ] Reads clearly in silhouette at its intended viewing distance
- [ ] Every hard edge chamfered per §6
- [ ] Full PBR set present; no flat/uniform channels
- [ ] Roughness varies from at least two noise sources
- [ ] Wear logic is physically motivated (water, hands, sun, ground)
- [ ] Palette-compliant per §4
- [ ] Correctly scaled against the §3 table, verified with a 1.75 m reference
- [ ] Contains at least one asymmetry or imperfection
- [ ] Zero anachronisms per §2
- [ ] Contains "residue" — evidence of use
- [ ] Texel density within class tolerance
- [ ] Reviewed at the locked 09:30 lighting setup
- [ ] Side-by-side blind comparison against FFXIV / GW2 / WoW reference holds up

The last item is the bar. Not "good for procedural." Not "good for a demo."
**Would a player believe this shipped in a current AAA MMO?**
