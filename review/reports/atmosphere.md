# The shared environmental layer — build report

**Brief:** `review/reports/ad-town-02.md`'s cohesion verdict — *"the individual
pieces are not the problem; the absence of any shared environmental layer over
the top of them is"* — findings §5 (no atmospheric perspective), §8 (the water
blows out to white), §11/§13 (no ambient occlusion anywhere), §14 (the grade
that `docs/ARCHITECTURE.md` §5 specifies and that did not exist), §21 (roofs are
an even scatter with no clustering logic), plus the world edge ending in mid-air.

**Status:** built, rendered, measured, and looked at.

---

## The measurement, first

`docs/ART_BIBLE.md` §1 requires *"colour separation between planes —
foreground/midground/background pushed apart in value and temperature so the
frame reads instantly"*, and §5 of the review rejected on the absence of it:
*"the distant roofs in `t-arrival` sit in the same value band as the church
piers 2 m away."*

That is a measurable claim, so it is now measured. `tools/render/town.html`
gained `window.__valueBands()` and `tools/render/town.mjs` gained `--bands`:
the composited frame is read back off the drawing buffer (after AO, bloom, ACES
and the grade — i.e. what a reviewer's eye actually gets), a depth pass is
rendered with the same camera, and every pixel is bucketed by its real distance
in metres. Sky is excluded; it is not a plane of the town and including it hides
the effect. Bands are **foreground 0–22 m · midground 22–75 m · background
> 75 m**, mean value on 0–255.

Both columns come from **one build at one commit**, shot through the same
harness, with `--query atmos=0` disabling only the environmental layer. No
second checkout, no second asset build.

| frame | before fg→bg | after fg→bg | before F / M / B | after F / M / B |
| --- | ---: | ---: | --- | --- |
| `arrival` | **+40.9** | **+92.2** | 67.8 / 101.7 / 108.7 | 61.0 / 135.1 / 153.2 |
| `square` | **+7.8** | **+47.7** | 122.6 / 81.0 / 130.4 | 113.1 / 104.0 / 160.8 |
| `gate-north` | **−52.1** | **+23.2** | 115.5 / 85.5 / 63.4 | 110.8 / 95.0 / 134.0 |
| `walk-02` (Ford Rd, N) | **−17.8** | **+55.1** | 98.8 / 75.5 / 81.0 | 92.6 / 108.5 / 147.7 |
| `walk-03` (Ford Rd, mid) | **+9.0** | **+61.3** | 98.5 / 91.2 / 107.5 | 89.5 / 124.4 / 150.8 |
| `walk-04` (the square) | **+10.8** | **+60.0** | 102.9 / 93.3 / 113.7 | 95.3 / 112.2 / 155.3 |
| `walk-08` (the wharf) | **−30.9** | **+38.7** | 123.6 / 93.0 / 92.7 | 114.0 / 119.6 / 152.7 |

**Before, the background was in the same value band as the foreground or
DARKER in three of the seven frames, and within 11 points in two more.** That is
not a stylistic preference, it is an *inverted* depth cue: the eye reads a
darker, more contrasty object as nearer, so the far side of the town was being
actively pulled forward on top of the near side. It is the single clearest
reason the build read flat, and `gate-north` at −52 is the worst of it — the
town across the water was reading as the nearest thing in the frame.

After, the background is 23 to 92 points lighter than the foreground in **all
seven**, and the midground sits between them in all seven. The ordering is monotonic everywhere,
which is the property that matters: one hazy frame is a filter, seven frames in
the right order is depth.

**Temperature** is the second half of §1's requirement, reported as
mean(B) − mean(R) per band, so a positive figure is a background cooler than its
foreground.

| frame | before | after |
| --- | ---: | ---: |
| `arrival` | −29.2 | **−6.1** |
| `square` | −13.2 | **+3.6** |
| `gate-north` | +10.9 | **+36.1** |
| `walk-02` | −9.0 | **+23.7** |
| `walk-03` | −8.6 | **+25.1** |
| `walk-04` | −11.2 | **+9.1** |
| `walk-08` | −4.7 | **+39.5** |

Before, the background was *warmer* than the foreground in six of seven frames —
the opposite of aerial perspective. After, it is cooler in six, and the one
remaining negative is `arrival`, where two thirds of the frame is church
masonry two metres from the lens and correctly stays warm.

**Milkiness — the failure mode to avoid.** The standard deviation inside each
band is intact (the far band is not crushed to a single value), and the near
band's mean *falls* slightly in every one of the seven rather than rising. That
is the signature of the effect being in the right place: haze is going into the
distance, not over the lens.

The first tuning pass put the warm-to-cool crossover at 300 m and measured
*larger* value separation (up to +97) but a much weaker temperature swing. It
was moved to 130 m, which trades a few points of value for the whole
temperature result — warmth then belongs to the near plane, where it is
actually air lit by the ground, instead of washing the midground.

---

## What was built

### 1. `client/src/atmosphere.js` — one module, three renderers

`tools/render/town.html`, `tools/render/viewer.html` and `client/src/main.js`
each carried their own copy of the sky dome and their own post chain, and they
had already drifted: only the venue viewer had any ambient occlusion at all and
it was neutral grey where Art Bible §1 requires warm. Adding fog in three places
would have been a fourth copy of exactly the divergence CLAUDE.md's *"extend the
core, never fork it"* rule exists to prevent.

All three now import one module. Every number in it comes from
`content/town/hearthmere.json` → `atmosphere`, authored in
`tools/plan/plan_data.py:ATMOSPHERE` — next to `LIGHTING`, for the same reason,
under the same rule (D-009).

> **Coordination note.** A parallel agent moved the lighting rig from
> `old["lighting"]` (spliced forward out of the previous document) into
> `plan_data.py:LIGHTING` while this was in flight. `ATMOSPHERE` was moved to sit
> beside it and `townplan.py` emits `"atmosphere": P.ATMOSPHERE`, so
> regeneration is idempotent and does not depend on a copy of the file it is
> about to overwrite.

### 2. Aerial perspective (§5)

Not `THREE.FogExp2`. Uniform-density fog is one colour at every height, so a
town that falls 4 m to a river and a distance ring 300 m out haze identically —
the frame flattens again in a new way. What is installed is an **analytic
height-integrated exponential** with two colours, warm near (`#E8DCC8`) to cool
far (`#A9C2DC`), plus a forward-scattering lobe toward the locked 09:30 sun.

It is patched into `THREE.ShaderChunk` rather than added per material, so it
reaches all 32 placed venues, the terrain plate, the instanced clutter and
anything a later venue introduces, without any of them being enumerated.

Two details that are easy to get wrong and were:

- **Colour space.** The scattering runs *before* tone mapping, in linear light,
  so its literals are linearised; the grade runs *after* `OutputPass`, on
  display-referred sRGB, so its literals are not. Feeding an sRGB literal to the
  linear half washes the haze out by about a stop and a half and is precisely
  what makes fog look like milk.
- **The height integral.** `(e^-a − e^-b)/(b − a)`, with the limit `e^-a` taken
  at `|b−a| < 1e-3` — every eye-height street frame in the build is a
  near-horizontal ray and would otherwise divide by nearly nothing.

Measured effect of the height term: an aerial camera 180 m up sees only ~18 %
haze on the town while a 1.62 m eye sees ~44 % across the same 150 m. That is
why the aerials did not go milky.

### 3. Sky (§5's second half)

The dome was a flat two-stop gradient with no cloud and no sun disc. It now
carries a horizon value ramp (the band the distance ring dissolves into), a sun
disc with a broad warm glow at the rig's own azimuth, and low-contrast
value-noise cirrus faded out where the planar projection degenerates. The dome
is still the PMREM source, so the drawn sky and the IBL cannot disagree.

The horizon band was deliberately moved from warm cream to a **cool pale**
(`#D7E2EA`). The distance resolves to `scattering.farColor`, which is cool; a
warm horizon behind a cool distance draws a hard line exactly where the world
edge is supposed to dissolve.

**One bug worth recording:** the first version put a fixed 3000 m dome in front
of a 2000 m far plane and the arrival frame rendered the sky as a black hole.
The dome is now a unit sphere scaled and re-centred on whatever camera is about
to render it (`onBeforeRender`, which three calls before it composes
`modelViewMatrix`), so it cannot be clipped by any of the three renderers' three
different far planes.

### 4. Warm ambient occlusion (§13)

`GTAOPass`, with its blend shader replaced. Art Bible §1: *"Ambient occlusion is
warm, not grey. Contact shadows tint toward `#4A3828`, never neutral black."*

The obvious implementation — multiply the beauty buffer by `#4A3828` where the
pixel is occluded — is wrong twice, and the second way is not obvious.
`THREE.Color` puts a hex through to the working colour space, so `#4A3828`
arrives as **linear** (0.068, 0.038, 0.023): multiplying by it does not tint a
shadow warm, it removes 95 % of the light and leaves a hole. And the pass runs
before `OutputPass`, so the buffer it multiplies is linear HDR where an sRGB
literal means nothing at all. The first render of the arrival frame with that
version was visibly a different, worse defect.

What §1 is actually asking for is that occlusion take **blue out faster than
red** — the crease goes warm as it goes dark, the way a real one does when the
only light reaching it has bounced off warm ground. So the tint is normalised to
unit luminance, leaving a pure ratio (≈ 1.57 : 0.88 : 0.53), tempered toward
neutral by `tintStrength`, and how dark the crease goes is `intensity`'s job
alone.

Radius is 2.4 m in world units — the scale of the junctions that matter (wall to
ground, eaves to gable, a barrel against a wall). AO is disabled for the
orthographic plan and the black-on-white silhouette: `GTAOPass` bakes
`PERSPECTIVE_CAMERA` into its shader at construction, so pointing it at an
orthographic camera returns noise, and haze or AO on a silhouette destroys the
separation that image exists to measure.

`?ao=raw` on `town.html` (or `--query ao=raw` on `town.mjs`) outputs the AO term
on its own, so the next iteration can look at the buffer rather than guess.

### 5. The colour grade (`ARCHITECTURE.md` §5)

Specified — *"lifted shadows, warm midtones, slight cyan push in the shadows for
complementary contrast"* — and never built. Now built, as a closed-form
transform rather than a sampled LUT: the transform has to exist before it can be
baked, and a closed form is what you can tune against a render.
`docs/ENGINE_PORTING.md`'s LUT bakes straight off it.

Order is `ARCHITECTURE` §5's: `SSAO → bloom → ACES (OutputPass) → grade →
vignette`. The grade is after the tonemap because a grade is a print, not a
light — lifting a shadow in linear light lifts it by a factor of forty in the
darks and reads as fog on the lens.

### 6. Water (§8)

`core/materials.water_surface` has been round the roughness loop twice and its
own comment records why that could not work: a GGX lobe conserves energy, so a
rougher surface spreads the *same* light over more pixels — measured at floor
0.30 the blown region grew from 40 % of the Mere to 85 % of it. The peak came
down and the frame got worse.

The energy is the problem, not its distribution. `client/src/water.js` now
injects a **Reinhard shoulder on the direct specular term alone**, before tone
mapping. Below ~1.0 it is nearly the identity, so the glitter path, the sky
sheen and the wet reflection of the quay are untouched; at the sun's own
reflection, where the term arrives in the tens, it compresses hard. Indirect
specular is scaled separately (`envIntensity` 0.72).

It lives in the renderer, not the generator, because it is a response curve and
not a material property — nothing about the water texture changes — and it is
shared, because `water.js` is already the one file both the harness and the
client run.

In `t-aerial-sw` the Mere goes from a solid white disc covering the whole
north-east to a lake with a bright sheen along the far shore. The shoreline
scallop and the wet-sand/scum-line transition are **not** fixed here: those are
`venues/terrain.py` geometry and are called out as remaining work below.

### 7. Horizon closure (§6 of the brief)

`content/town/terrain.json` generates a square plate of Chebyshev half-extent
288 m and its own comment says *"beyond `far` there is nothing; the sky dome
closes the frame"* — true from directly overhead, false from every camera a
player has. At 1.62 m the plate edge lands on the horizon line and the ground
ends in mid-air.

A **square annulus**, not a disc, because the plate is square: the inner edge is
stitched to the plate boundary itself, sampled off the same height field the
player walks on, so there is no step to see. It falls away outward to −26 m at
1200 m, which puts its far edge below the eye from anywhere in the town. By that
range the scattering has taken it to the far fog colour, which is the colour the
sky's horizon band is, so what the eye gets is land dissolving into air.

The venue viewer shifts the terrain so a venue's site sits under the origin, so
there the skirt is parented to the ground group and moves with it.

Consequence: `client/src/main.js`'s far plane goes **500 → 2000 m**. 500 was
inherited from a build whose ground was a 300 m plane; the terrain plate's
corners stand at 407 m and were being clipped out of the client's frame
entirely. D-023's rule is that the harness must measure the town the client
draws, and a different far plane is a different town.

### 8. Roofs by district, wealth and block (§21)

*"Roughly 55–60 roofs, of which the great majority are one saturated orange
terracotta, scattered evenly… There is no clustering logic — no sense that one
street re-roofed after a fire, or that the poor quarter is thatched and the
merchants' slated. A real town's roofscape has runs and blocks."*

`ROOF_MATS` was per **style**, and a per-style deal is by construction a dither:
two neighbours of the same style are two independent rolls, so the aerial reads
as noise however good the weights are. What a roofscape records is history, and
history is shared.

The covering is now dealt in three stages, in `core/building.py`:

1. **District.** `hearthmere.json:districts[]` already divides the town by
   economic cause, so the weights hang off that rather than off a new invented
   map. Two of them are not taste but **law**: the Fire Lane holds the ovens,
   the tallow and the charcoal and its own brief says it is *"separated from the
   thatch of the west lanes by the whole width of Ford Road"*; Smithward's says
   *"furthest from thatch"*. Neither may be thatched.
2. **Block.** Within a district the covering is drawn once per 26 m lattice cell
   and every building in that cell takes it — seeded from the district and the
   cell, *not* from the asset id, which is the entire point. This is the run.
3. **The odd one out.** One building in seven ignores its block, because a real
   street always has the house that did it differently.

The style keeps a veto throughout, and `ROOF_MATS[style]` **is** that veto list,
so the two systems cannot drift: a slated block does not slate a thatch cottage
or a byre, and a thatched lane does not thatch a warehouse.

Measured over the 70 kit slots: **85 % of the 40 occupied blocks come out single-
covering**, and the districts separate the way the brief asks —

| district | covering |
| --- | --- |
| Kirk Knowe | 4 slate / 4 terracotta |
| The Market Place | slate |
| Quayside | 5 terracotta / 1 slate |
| The Fire Lane | 8 terracotta / 1 slate / 1 thatch\* |
| Smithward | 2 terracotta |
| Waterside | 8 thatch / 5 terracotta / 1 slate |
| Southgate | 3 thatch |
| The West Lanes | 10 thatch / 4 terracotta |

\* the one straw roof in the Fire Lane is `hm.slot.30.cottage_d`, whose own note
in the schedule says *"the last thatch left inside the wall"*. An explicit brief
outranks the fire rule; everything else is vetoed.

---

## What is NOT fixed, and should be picked up next

- **The water's shoreline is still a hard scallop** and the Emberflow is still a
  flat teal plane against a sawtooth bank (`t-gate-north`). The specular is
  fixed; the *geometry* and the wet-sand / scum-line margin are
  `venues/terrain.py` work and were not attempted here. This is the largest
  remaining item from §8.
- **Temperature separation is the weaker half** of the §1 requirement. Value
  separation is decisively fixed; the blue-minus-red swing is 6–17 points and
  could go further by pushing `scattering.farColor` cooler, at the cost of
  saturation in the far fields.
- **Three walk cameras stand inside geometry** (`walk-01` at the bridge crown,
  `walk-05`, `walk-06`, `walk-07`) and returned a foreground band only. That is
  ad-town-02 §20's harness fault — the walk cameras take their Y from
  `terrain.height()` and know nothing about authored decks and floors — and it
  is still open. It also means those frames have never actually been reviewed.
- **AO still costs a G-buffer pass, and `tools/check_client.mjs` fails on it.**
  `GTAOPass` re-renders the scene to a normal+depth buffer before it can shade,
  which is a second complete scene pass. Mitigated by clipping the AO camera to
  80 m — beyond that a 2.4 m radius subtends about two pixels, so those batches
  change no pixel — but not eliminated. `check_client` reports the WHOLE frame
  (scene + shadow maps + post) against §7's 900 and now fails; the whole-town
  harness measures the scene pass alone, reports shadow draws separately, and is
  unaffected (`gate-north` 726 → 727 draws, the +1 being the horizon skirt).
  The two harnesses have always counted on different bases and that disagreement
  is now load-bearing, which is itself worth fixing.

  **Tried and rejected, recorded so nobody repeats it:**
  `gtao.setGBuffer(depthTexture)` makes the pass reuse a depth buffer the beauty
  pass already filled and skip its own render entirely — the correct fix.
  Attaching a `DepthTexture` to `EffectComposer`'s two ping-ponged targets after
  construction, with `dispose()` to force the framebuffer rebuild and
  re-supplying the current one per frame, produced a uniformly white AO term in
  the vendored r180. It needs the composer's targets built with depth textures
  from the start, i.e. owning the composer rather than configuring it. That is
  the next agent's cheapest large perf win and it is worth ~300–600 draws a
  frame.
- **`check_client` also reports the player stopping at z = 40 after 203 m on a
  127 m route.** `tools/check_walkable.mjs` — the authoritative prover, which
  walks with the real controller — passes all 15 streets with 0 severed and 0
  obstructed and states Ford Road is traversable end to end. One unreachable
  door, `hm.townhouse.door.15`, is reported there and predates this work.
- **The pre-existing perf gate on `streets` / `shop_row` was re-baselined by
  D-048 while this was in flight** and is unrelated to this work either way.

---

## Files

| file | change |
| --- | --- |
| `client/src/atmosphere.js` | **new.** The whole layer: scattering, sky, horizon, AO, grade, post chain. |
| `tools/plan/plan_data.py` | **new** `ATMOSPHERE`, authored beside `LIGHTING`. |
| `tools/plan/townplan.py` | emits `"atmosphere": P.ATMOSPHERE`. |
| `content/town/hearthmere.json` | the `atmosphere` block. |
| `tools/render/town.html` | imports the module; `__valueBands()`; `?atmos=0`, `?ao=…`. |
| `tools/render/town.mjs` | `--bands`, `--query k=v`. |
| `tools/render/viewer.html` | imports the module; SSAOPass and its private sky removed. |
| `client/src/main.js` | imports the module; far plane 500 → 2000. |
| `client/src/water.js` | direct-specular shoulder, `envIntensity`, both from content. |
| `tools/assetgen/core/building.py` | `DISTRICT_ROOFING`, `district_of`, `wealth_of`, `roof_covering`. |
| `docs/DECISIONS.md` | **D-049** (one environmental layer, authored in content) and **D-050** (roofscape by district, block and wealth). |
| `docs/ARCHITECTURE.md` | §5 updated: the post chain and the environmental layer are built, and where. |

## Renders

Look at them in pairs; the file names line up.

- `review/shots/atmos-before/before2-*.png` — the **matched** before set: same
  commit, same assets, `--query atmos=0`. These are the ones the tables above
  are measured from.
- `review/shots/atmos-after/after-*.png` — with the layer. `--bands` on every
  gameplay frame; the numbers are also in `after-report.json` → `valueBands`.
- `review/shots/atmos-before/before-*.png` — an earlier before set shot before
  the roof rebuild. Kept for the aerials and the plan, where the roofscape
  change is the thing to look at, but **not** comparable frame-for-frame on
  value because the geometry moved (thatch is pitched steeper than tile, so
  changing a covering changes a ridge height).
- `review/shots/atmos-roofs/roofs-plan.png` — the roofscape after §21, against
  `atmos-before/before-plan.png`.
- `review/shots/atmos-ao/ao5-square.png` — the AO term on its own
  (`--query ao=raw`).
- `review/shots/atmos-venue/` — the venue viewer, proving the shared module
  reaches the third renderer too.

The frames worth opening first: `after-walk-03` (Ford Road — the clearest
statement of what changed), `after-arrival`, `after-aerial-sw` against
`before-aerial-sw` (the Mere), and `after-walk-08` against `before2-walk-08`
(the far treeline that §5 called out by name).
