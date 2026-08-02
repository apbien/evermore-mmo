# Owner verdict 01 — first walkthrough of the assembled town

**2026-08-02. Verdict: REJECT.** The owner played the build in the real client
and walked through the town.

PROMPT.md §8 makes the owner the last critic. This verdict therefore outranks
every art-director report in this directory, including `ad-town-06.md`, whose
"twelve frames survive two seconds" is now known to be a more generous bar than
the owner's.

## The verdict, verbatim

1. Better than the previous iteration, but **it lagged a lot** walking through
   town.
2. **It does not look like a AAA game made in 2026.** "Even Skyrim looks better
   than this." (Skyrim shipped in 2011.)
3. **Still a lot of unconnected roads.**
4. **Some textures do not line up properly**, so it looks odd.
5. **Some things are still not connected, or floating.** It does not look
   cohesive.

## Which of these the machinery can currently catch

This was checked against the tools rather than assumed. Three of the five are
invisible to every prover and every critic this project has.

| Reported | Caught? | Why |
| --- | --- | --- |
| Lag | **No** | `check_client.mjs` runs the frame loop on a fixed 1/60 s timestep **with rendering disabled** — it was made deterministic that way on purpose. It measures LOD settle time and draw counts, never a frame. The perf gate compares draw/triangle *counts* against `review/perf-baseline.json`; no tool in this repo has ever measured a millisecond of frame time on real hardware. ARCHITECTURE §5 budgets 16.6 ms and nothing tests it. |
| Not AAA / Skyrim looks better | Partly | The art director has said REJECT every pass, so the direction is right — but its bar is measurably more generous than the owner's, and it grades stills at a locked hour while the owner grades motion. |
| Unconnected roads | **No** | `check_walkable.mjs` floods the town on foot and proves you *can* walk it. A road that visually stops dead at a wall, or whose surface does not meet the next street, still floods fine — pedestrians cross the gap. Walkability is not continuity. `townplan.py --check` proves the shipped polygons match the plan, which says nothing about whether the built surfaces meet. |
| Textures not lining up | **No** | `uv_density.py` measures metres-per-tile — scale only. Nothing checks UV alignment, seam continuity across adjacent faces, or whether a pattern carries across a corner. Its three current failures (`straw`, `wool_crimson`, `canvas_amber`) are all scale. |
| Floating / not connected | Partly | `validate.py` has floating and sunk-mass checks, deliberately tuned to prefer false negatives after an earlier version produced ~40 false positives per build. It also spent four art-director passes hunting a 34.2 m floating mass that did not exist while real ones survived. |

## What this means

The gap is not that agents ignored these defects. It is that **the project's
evidence chain cannot see three of them**, so no amount of iteration under the
current tools would have found them. PROMPT.md §4 rule 3 says a machine prover
outranks any claim; where no prover exists, the claim has never been tested.

Three provers are missing and are prerequisites, not follow-ups — building more
town before they exist means building more of the same defects:

1. **A frame-time prover.** Drive the real client with rendering ON, walk the
   spawn-to-south-gate route, and record frame time percentiles — p50, p95, p99
   — plus the worst camera. Fail on the 16.6 ms budget in ARCHITECTURE §5. The
   existing counts are a proxy that has now been shown to miss what the owner
   experiences. Note that the committed baseline already exceeds D-072's world
   share (1,419 draws against < 600), so the lag is expected, not mysterious —
   but it must become measurable in milliseconds.
2. **A road-continuity prover.** For every street in `hearthmere.json`, sample
   its centreline and assert a paved surface exists beneath, that adjacent
   segments' surfaces actually meet at junctions, and that each street
   terminates in something the plan declares rather than in nothing. An early
   render caught Smith's Lane authored in content with no surface rendered
   beneath it at all; the same class of defect is what the owner is seeing.
3. **A UV-continuity prover.** Alignment and seams across adjacent faces, not
   just texel density.

## Where this slots into §6

The owner's report is of the assembled town, so it lands on §6h (cohesion) —
but items 1, 3 and 4 are systemic and cheap to prove, and every venue built
before they exist inherits them. They belong before §6a, alongside the D-075
law-compliance pass.

The "Skyrim looks better" line deserves to be taken literally rather than as
frustration. Skyrim's town interiors and exteriors hold up because of
consistent surface treatment, believable joins, and light that grounds objects
to what they stand on — not because of triangle counts. Every one of those is a
cohesion property, and cohesion is what all five reported defects have in
common.

---

## Addendum A — the wind on the foliage (owner, same session)

**Reported:** the wind on the leaves is too dramatic; the leaves look like they
would blow off.

**Diagnosed in `client/src/ambient.js`, `harvestFoliage()`.** The shader itself
is well built — height-weighted so the base of a stem stays planted, phase
offset by world position so neighbours do not move in lockstep, two
incommensurate frequencies under a slow gust envelope. The architecture is not
the problem. The amplitude is:

```
a = uWindAmp * k * gust * uWindSpan
uWindAmp = 0.055 * stiffness * windSpeed        // 0.077 for a generic leaf
uWindSpan = boundingBox.max.y - boundingBox.min.y
```

`uWindSpan` is taken from the **merged mesh's** bounding box, and scenery is
merged per material per cell. So the span is not the plant's height — it is the
vertical extent of every card sharing that material in that batch. Two
consequences, both wrong:

1. On a 9 m oak the tip displacement reaches roughly **0.69 m horizontally**. A
   leaf in a 1.4 m/s breeze moves centimetres; a whole branch might move 10–20.
   Two thirds of a metre is a gale, and it is applied to a leaf.
2. A low hedge merged into the same batch as a tall tree inherits the *tree's*
   span, so the shortest plants swing hardest relative to their own size.

And because the displacement translates the whole leaf card along the wind
vector, the card slides through space rather than a twig bending under it —
which is precisely the "about to blow off" read.

**Fix:** scale amplitude by the individual plant's height, not the batch's.
The per-plant height is known at generation time in `core/vegetation.py` and
should be baked into a vertex attribute or instance attribute, so the shader
stops inferring it from a bounding box that describes a batch. Then retune
against a real reference: at the authored 1.4 m/s the canopy should shimmer and
the branch tips drift, not sway.

Diagnosed from source and arithmetic, **not yet confirmed in a render** — the
next agent should reproduce it in motion before and after.

---

## Addendum B — does lighting and shading affect how this looks?

The owner asked. Yes — for "does this look like a current AAA game" it is
arguably a larger lever than geometry, and it is directly implicated in the
"floating / not connected / not cohesive" complaint, because contact darkening
is what visually glues an object to the ground it stands on.

**What the client actually runs today** (verified, not assumed — `main.js`
installs the chain from `client/src/atmosphere.js`): sun with cascaded shadow
maps, hemisphere ambient, a PMREM environment from the sky dome, warm-tinted
GTAO, height- and distance-based aerial perspective, ACES tonemap, bloom, and
the warm colour grade. That is a real chain, and it is why this question needed
checking rather than answering from instinct.

**The three weakest parts, in order:**

1. **There is no indirect light.** The "bounce" is a second directional light
   pointed back from the sun — a stand-in for light reflecting off the ground
   and off facing walls. Real bounce picks up the colour of what it bounced
   from: a white wall beside a terracotta roof takes warmth from it. A constant
   directional cannot do that, so every shadowed surface in Hearthmere is lit
   by the same flat fill regardless of what is next to it. This reads as
   objects pasted onto a backdrop rather than sitting in a place, and it is a
   strong candidate for the gap the owner feels against Skyrim, which bakes
   its indirect light.
2. **The rim light is a fake, and it is the Art Bible's single strongest anime
   tell** (§1 lists it first). D-010 records that it ships as a directional
   light, which lights every face turned toward it instead of only grazing
   edges — draining saturation from curved objects rather than separating them
   from the background. D-010 is still open, and the rim ships at 1.15 against
   §1's authored 1.4. A true Fresnel rim pass is named in ARCHITECTURE §5 as
   the target implementation and does not exist.
3. **AO is screen-space only.** GTAO can only occlude from what is on screen
   and is thin by nature. The deep contact darkening where a barrel meets a
   cobble, or a wall meets the ground, wants baked or capsule occlusion in
   addition. This is the specific lighting contribution to "things look like
   they are floating" — an object with no darkening beneath it reads as
   hovering even when its geometry is seated perfectly.

**Also relevant:** the world is locked to one hour (09:30, Art Bible §4). That
lock is deliberate and correct for review — it removes a variable — but it
means nothing in the build has ever been lit dramatically, and D-078 has now
committed day and night as design. Time of day is where a lot of a modern
game's visual impact comes from.

None of this contradicts the geometry work. It sits alongside it, and the
lighting items are cheap relative to their effect on every frame at once.
