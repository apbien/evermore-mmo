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
