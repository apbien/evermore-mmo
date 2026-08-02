# Evermore — Agent Instructions

An MMORPG first town, **Hearthmere**, built to modern AAA standards in a
semi-realistic anime style (SAO / Shangri-La Frontier / Echoes of Aincrad),
benchmarked against FFXIV, Guild Wars 2, and World of Warcraft.

**Standing mission:** `PROMPT.md` at the repo root is the owner's standing
order — what to build next, in what order, and the rules of evidence. Read it
first when continuing the work.

## Read before doing anything

| Document | What it governs |
| --- | --- |
| `docs/ART_BIBLE.md` | **Law.** Style, palette, scale, materials, geometry, done-criteria |
| `docs/ARCHITECTURE.md` | Layers, entities, cells, intents, directory contract |
| `docs/ASSET_PIPELINE.md` | How to generate, export, and validate assets |
| `docs/REVIEW_PROTOCOL.md` | The art-director bar and iteration loop |
| `docs/areas/hearthmere/WORLD_BIBLE.md` | Hearthmere's lore, layout, and venue briefs |
| `docs/areas/README.md` | The per-area doc pattern — one directory per haven, route, cave, or dungeon |
| `docs/DECISIONS.md` | Recorded deviations and why |

If an instruction here conflicts with the Art Bible, **the Art Bible wins.**

## Hard constraints

1. **glTF 2.0, Y-up, 1 unit = 1 metre.** No exceptions, no per-asset transform
   fixups. This is what makes the Unreal/Unity port free.
2. **Assets are generated, never hand-authored.** Everything in `assets/` is
   deterministic output of a generator in `tools/assetgen/`. To change an
   asset, change its generator and regenerate. Never hand-edit a `.gltf`.
3. **Seed every RNG.** Derive the seed from the asset ID. Unseeded randomness
   breaks review diffing and reproducibility.
4. **No anachronisms.** Hearthmere is pre-industrial. See Art Bible §2. No
   screws, no plate glass, no machined metal, no readable lettering anywhere.
5. **Chamfer every hard edge.** Art Bible §6. This is the first thing review
   rejects.
6. **Full PBR sets only.** Albedo + roughness + metalness + normal + AO. A flat
   colour with uniform roughness will be rejected.
7. **Client never authors gameplay state.** Read from `content/`, emit intents.
   See Architecture §4.
8. **Every interactable gets a stable entity ID.** `hm.<venue>.<kind>.<nn>`,
   never recycled.

## Working rules

- **Use the shared core.** `tools/assetgen/core/` owns geometry, materials, and
  export. Do not reimplement beveling, noise, UV layout, or glTF writing in a
  venue module — extend core instead. Divergent implementations are how the
  world loses cohesion.
- **Verify visually before claiming done.** Render your asset with
  `tools/render/shoot.mjs` at the locked 09:30 lighting and look at the image.
  An asset you have not seen is not finished.
- **Include a 1.75 m scale reference** in review renders. Scale errors are the
  most common and most immersion-breaking defect.
- **Judge from the gameplay camera** (1.62 m eye, 3.5 m orbit, 55° FOV), not
  from a hero close-up.
- **Residue over polish.** Evidence of use — a half-finished job, a cloak on a
  chair, spilled grain — buys more life per unit effort than another 10k tris.

## Commands

```bash
make setup          # install python + node deps
make assets         # regenerate all assets (deterministic)
make assets V=inn   # regenerate one venue
make shots          # render review screenshots for all venues
make shots V=inn    # render one venue
make validate       # schema + scale + palette + anachronism checks
make serve          # run the playable client at :8080
```

## Definition of done

An item is done when it passes every box in Art Bible §8 **and** an
art-director review has signed off at `ACCEPT`. See `docs/REVIEW_PROTOCOL.md`.
Self-assessment is not sign-off.

## Style of work

Match the surrounding code. Prefer extending the shared core to adding a
special case. Keep generators readable — they are the source of truth for the
art, so a confusing generator is a confusing asset.
