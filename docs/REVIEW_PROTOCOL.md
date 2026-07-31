# Review Protocol — The Art Director Bar

## Why this exists

Procedural asset generation has a characteristic failure mode: everything is
*technically* correct — right scale, right palette, valid topology, full PBR
set — and the result still looks like a prototype. Checklists catch defects.
They do not catch *lifelessness*.

So the final gate is not a checklist. It is a hostile art director who has
shipped AAA and is looking at your screenshot next to a Guild Wars 2 capture,
deciding whether yours embarrasses itself.

## The bar

> Placed side by side with a screenshot from FFXIV's Gridania, Guild Wars 2's
> Divinity's Reach, or WoW's Boralus — **blind**, without knowing which is
> which — would a player pick this one out as the amateur work?
>
> And: **would people actually play this?**

If the answer to the first is yes, it is not done. "Good for procedural" is
not a passing grade. "Good for a demo" is not a passing grade. There is one
standard and it is the shipped-AAA standard.

## The two roles

The loop deliberately separates making from judging, because the person who
built a thing cannot see it clearly.

**Builder agent** — owns a venue. Writes generators, produces assets, renders
its own screenshots, iterates. Reports `READY_FOR_REVIEW` with render paths.

**Critic agent** — reviews one venue, never builds. Has not seen the generator
code and does not read it before forming a visual judgement. Looks at the
images first, as a player would. Writes a verdict.

A builder may not self-certify. A critic may not soften a verdict to be
agreeable — a critic that passes mediocre work has failed at its job.

## Critic procedure

1. **Look before reading.** Open the renders. Form a first impression in the
   first two seconds, as a player would, and write that impression down before
   any analysis. First-glance reads are the most honest signal you get and are
   destroyed by prior knowledge of intent.
2. **Blind comparison.** Put the render next to the AAA reference described in
   `docs/REFERENCES.md`. Ask the bar question above. Answer honestly.
3. **Diagnose specifically.** "Looks flat" is useless to a builder. "The
   plaster has uniform roughness so it reads as painted cardboard; it needs
   broad dampness variation near the ground and fine lime texture" is
   actionable. Every criticism names the surface, the defect, and the fix.
4. **Check the Art Bible §8 list** — but only after the visual judgement, so
   the checklist does not launder a bad-looking asset into a pass.
5. **Verdict.**

## Scoped exceptions

Some limitations are recorded scope boundaries, not defects. **Do not block a
verdict on them.** Report them separately so environment findings stay
actionable.

Currently in force:
- **NPC / character fidelity** — D-011. Figures are primitives without
  skinning. Score the architecture; note character findings apart from the
  venue verdict.

## Verdicts

| Verdict | Meaning |
| --- | --- |
| `ACCEPT` | Ships. Holds up blind against AAA reference. |
| `REVISE` | Specific, enumerated defects. Builder fixes and resubmits. |
| `REJECT` | Fundamentally wrong approach — composition, proportion, or concept. Rebuild, do not patch. |

`REVISE` is the expected verdict on a first submission. A first-pass `ACCEPT`
usually means the critic was not looking hard enough.

## Scoring

Score each 1–10. **Any axis below 7 blocks acceptance** regardless of total.
This prevents a beautiful-but-wrongly-scaled asset from averaging into a pass.

| Axis | What it measures |
| --- | --- |
| **Silhouette** | Reads at distance; interesting in black-on-white |
| **Material truth** | Surfaces read as their actual substance |
| **Lighting response** | Form revealed; edges catch light; no flat facets |
| **Detail hierarchy** | Primary/secondary/tertiary layering, no detail-soup |
| **Wear & story** | Physically motivated, tells you how it is used |
| **Life & residue** | Evidence of recent human activity |
| **Cohesion** | Belongs to Hearthmere; consistent with neighbours |
| **Scale truth** | Correct against the 1.75 m reference |
| **AAA comparison** | The blind side-by-side verdict |

**Acceptance requires: no axis < 7, and AAA comparison ≥ 8.**

## Report format

Written to `review/reports/<venue>-<iteration>.md`:

```markdown
# <Venue> — Review <n>

**Verdict:** REVISE
**Renders:** review/shots/inn-03-*.png

## First impression (before analysis)
Two seconds, honestly. What did it look like?

## Blind AAA comparison
Which reference, and the honest verdict.

## Scores
| Axis | Score | Note |
...

## Defects
1. **[surface/element]** — what is wrong — why it reads wrong — the fix.
...

## What is working
Do not skip this. Builders need to know what to preserve.
```

## Iteration

Loop until `ACCEPT`. Each iteration:
1. Builder addresses every enumerated defect
2. Regenerates and re-renders
3. Critic re-reviews **against the previous report** — verifying each defect is
   actually resolved, not merely changed

If a venue reaches iteration 5 without `ACCEPT`, escalate: the problem is
likely in the shared core or the venue's fundamental composition, not in the
details being iterated on.

## Cohesion review

Per-venue acceptance is necessary but not sufficient. A town of nine
individually excellent buildings that do not belong together is a failure.

After all venues pass, a **cohesion critic** reviews the town as a whole:
- Do the venues read as one settlement built by one culture?
- Is the palette consistent, or has drift crept in?
- Do material treatments match across venues?
- Do sightlines work? Does the square compose from every entrance?
- Is density varied — quiet corners against busy ones — or uniformly cluttered?
- Walk the streets at the gameplay camera. Is it pleasant to move through?

The cohesion critic may send an individually-accepted venue back for revision.
