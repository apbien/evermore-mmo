# Session handoff — the v2 build session, 2026-08-02

Written for the successor session. This is not a verdict; it is the two things
the §5 ritual cannot tell you by itself, plus the gap list between what is built
and the law added in D-063…D-078.

## 1. `review/validate.txt` was stale and said the town was broken

The copy committed before this note was written at 08:39 against a tree that had
since moved. It reported **43 failures**, sixteen of them "venue is placed but
has no collision file", and cited `materials.py` line numbers that no longer
pointed at the code they blamed. On disk there were 35 collision files and 35
meshes the whole time.

Re-run, the real verdict is **8 failures / 48 warnings**. It is now regenerated
and committed.

The lesson is worth keeping: §4 rule 3 says the prover outranks any claim, and
that is right, but `validate.txt` is a *record* of a prover run, not the prover.
Regenerate it before trusting it — `python tools/validate.py > review/validate.txt`
takes about 40 s against assets already on disk, no rebuild needed.

## 2. The 8 real failures

Five are one problem: **duplicate decision IDs.** D-025, D-026, D-038, D-040 and
D-050 each head two sections, so every citation of them in the repo is ambiguous.
This is the collision recorded earlier for reconciliation — the ruling on file is
that the documentation session's entries keep their numbers and the build
session's entries renumber. That reconciliation was never performed; the
validator now catches it. It is a docs-only job and a clean first task.

Three are texel density: `straw` at 0.38×, `wool_crimson` at 3.10× and
`canvas_amber` at 0.41× their authored scale, from hand-laid UVs that bypass
`MATS.uv_scale()`. 421 such sites were routed through the library earlier; these
are the survivors.

## 3. Where the build stands against the standing order's §6

Built and rendered: terrain and one authoritative height field; authored
collision; the town plan and its 94 plots; 35 venue modules including the church
with a walkable interior, the wall and four gates, the quay and crane, the
watermill; the whole-town render harness; the determinism gate; instrument
parity at 1.5%.

Not closed: **§6a — the filler building kit has never reached ACCEPT.** It stands
at REJECT in `review/reports/building-kit-01.md`. Everything sited among its
houses inherits that.

The standing art-director verdict is REJECT at pass 06
(`review/reports/ad-town-06.md`): twelve frames survive two seconds of a blind
side-by-side, two survive ten (`mere-walk-05`, `t-gate-south`). Passes 02–06 carry
a per-finding scorecard; pass 06 was the first with zero regressions.

## 4. What D-063…D-078 invalidate in what is already built

None of this was law when the geometry was authored. Listed so it is not
rediscovered one venue at a time.

| Ruling | What it invalidates |
| --- | --- |
| D-075 metals as F0 | Every iron surface is authored the old way. Wrought iron moves `#3A3632` → `#8E8E8D` at metalness 1.0, and painted/limed ironwork becomes a dielectric. |
| D-075 sun convention | 125° is clockwise from +Z (south); **north and east elevations are the lit ones**, and shadowed palette variants belong on south and west faces. Anything weathered to the old reading is weathered on the wrong side. |
| D-064 typed variety | The kit jitters one archetype. Five house types and three dressings, adjacency-constrained, is a rebuild of its variety model — and D-064's own text names the failure it is answering. |
| D-076 pattern book | Roof pitch by covering, eaves, verge, jetty, framing bays, window lights, and the two door scales are now numbers. The kit builds to none of them. |
| D-077 | The district colour script (with its 60/25/10/5 dominance ratio), the wear index 0–5, and the single sign language do not exist yet. |
| D-072 budget shares | The world's share is **< 600 draws**, not the whole 900. Measured worst gameplay camera is 1,381. |
| D-069 camera | Boom 3.6 m, camera height 2.05 m. Reviews to date were framed at 3.5 m orbit / 1.62 m eye, so every render was judged from slightly the wrong place. |
| D-065 | Upper storeys are sealed. |
| D-063 | The look is anchored to Echoes of Aincrad and DragonSword: Awakening — warm, saturated, painterly-clean; explicitly not stock-UE5 photoreal, and no cel-shading of the environment. |

## 5. Method note

This session ran eight large parallel waves and committed once at the end. §7 is
right that this is a defect: an uncommitted tree older than one iteration breaks
review diffing and risks the work. It also fits the usage limits badly — a wave
costs roughly one usage window, and a wave killed mid-flight loses everything its
agents had not written to a file.

What worked: agents writing `review/reports/<name>.md` as they went, so a killed
agent lost its final message but not its findings. What did not: fanning out
wider than a committed checkpoint could reach.

## 6. The instrument findings worth not re-learning

Every significant defect this session was found by fixing an instrument, not by
looking harder. Recorded so the next session trusts its tools less and its
renders more:

- The town was rendered above a phantom ground plane that hid the northern road
  network and the entire lake.
- `dirFromDeg` was mirrored, so the arrival camera pointed due east for several
  passes.
- The shadow cascades were parked on a 0.1 m slab, so gameplay frames were
  missing their 5.4–30 m shadows *in the picture*, not merely in the count.
- `viewer.html` had no water code at all — every basin, trough and pit was signed
  off in a viewer that drew them as still green glass.
- `check_client.mjs` was not flaky, it was dead.
- The build silently stopped being deterministic on `abs(hash(asset_id))`;
  Python salts string hashing per process. `tools/determinism.py` now gates it.
