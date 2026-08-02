# Visual References

The blind comparison bar from `docs/REVIEW_PROTOCOL.md` needs specific
reference points, not a vague sense of "AAA". These are the targets.

## The look anchors (owner direction, D-063)

The production bar below says how *good* the town must be. These two say what
it must *feel like* — the owner named them as the definitive look:

- **Echoes of Aincrad** (UE5, 2026) — SAO's Town of Beginnings realized at
  scale. What defines it: a warm, stylized-clean world that deliberately
  avoids the stock-UE5 photoreal look; simplified, painterly surfaces that
  still light physically; a town that reads bustling and MMO-convincing at
  street level. This is the closest existing image of what Hearthmere
  should be.
- **DragonSword: Awakening** (UE5, 2026) — colour identity over photoreal
  ambition. What defines it: a warm, vibrant, saturated open world; clean
  value structure; polished subculture-style character design that pops
  against the softer world.

What we take: the warmth, saturation, and clean painterly surfacing of both
worlds — which is Art Bible §1's axis, now anchored to shipped games. What we
do not take: neither anchor's **cel-shading** applies to Hearthmere's
environment. Our materials stay stylised PBR; the anime read comes from §1's
five tells (rim, warm AO, sky bounce, tight specular, plane separation), not
from toon ramps or outlines. Both anchors cel-shade *characters* against a
softer world — when characters return (D-012), they follow that convention.

## Primary references

| Game | Location | What we take from it |
| --- | --- | --- |
| **FFXIV** | Gridania, Ul'dah | Semi-realistic anime materials; how a fantasy town reads at a distance; warm inviting palette; readable pictorial signage |
| **Guild Wars 2** | Divinity's Reach, Lion's Arch | Set-dressing density; how much residue a plaza can hold; vertical layering of streets |
| **WoW (post-Legion)** | Boralus, Dazar'alor | Silhouette clarity; bold primary forms; palette discipline; readability at 100m |
| **Genshin Impact** | Mondstadt | Anime material clarity; stylised PBR that still feels physical; rim-light usage |

## What "AAA" means concretely here

When judging, ask these in order:

1. **Does the silhouette read?** Squint. Boralus reads instantly at any
   distance because primary masses are bold and secondary elements break the
   outline deliberately.
2. **Do materials read as substance?** In Gridania you know instantly what is
   plaster, what is thatch, what is wet timber. If a surface is ambiguous, it
   has failed.
3. **Is there density hierarchy?** Divinity's Reach has quiet walls *and* dense
   corners. Uniform clutter is as wrong as uniform emptiness.
4. **Is there evidence of people?** The single largest gap between amateur and
   shipped environment art. Not props — *residue*: interrupted work, worn
   paths, things left where someone put them down.
5. **Does the light do work?** Shipped AAA scenes have deliberate light: a warm
   key, a cool fill, and something bright at the end of the sightline.

## Anti-references

Things that specifically read as amateur, all of which the first cottage pass
hit at least once:

- **Razor-sharp edges.** Nothing in the real world lacks a chamfer.
- **Uniform roughness.** Reads as painted cardboard under any lighting.
- **Tiling texture at wrong scale.** Our first plaster crackled at ~30cm cells
  and read as crazy-paving stone instead of lime render.
- **Banded procedural grain.** A pure sine wood grain aliases into stripes.
- **Black metal.** Full metalness with a dim environment renders as a cutout.
- **Symmetry.** Hand-built settlements have none. Centred doors are a tell.
- **Empty rooms.** A perfectly modelled empty interior reads as dead.
- **Flat ground.** A texture plane under buildings kills an otherwise good shot.
