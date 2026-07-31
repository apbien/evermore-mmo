# Asset Pipeline

## Principle

**Assets are generated, never hand-authored.** Everything in `assets/` is the
deterministic output of a generator in `tools/assetgen/`. To change an asset,
change its generator and regenerate.

This is not bureaucracy — it is what makes the art-director loop work. A
critique ("the plaster reads as crazy-paving") maps to a specific code change
("the crackle worley is at 9 cells, it needs ~52"), which is reproducible,
reviewable in a diff, and fixes every wall in the town at once. Hand-poked
meshes give you none of that.

## Commands

```bash
# Everything (textures are incremental — existing PNGs are skipped)
python3 tools/assetgen/build.py

# One venue
python3 tools/assetgen/build.py --venue inn --skip-textures

# You changed a material builder — you MUST force, or you will not see it
python3 tools/assetgen/build.py --textures-only --only plaster --force-textures

# What venues exist
python3 tools/assetgen/build.py --list
```

**The most common wasted iteration** is editing a material builder, rebuilding,
and seeing no change because the PNG already existed. Pass `--force-textures`.

## Rendering for review

```bash
node tools/render/shoot.mjs --asset assets/meshes/inn.gltf \
    --out review/shots/inn --label inn \
    --views approach,gameplay,detail,orbit
```

Then **open the PNGs and look at them.** An asset you have not seen is not
finished.

### Views

| View | What it is for |
| --- | --- |
| `gameplay` | **The one that matters.** True third-person rig — 3.6 m behind, 2.05 m high, 55° FOV, character in frame. The game is always default third-person, so this is the player's actual camera. |
| `approach` | Whole venue from down the street. Does it anchor the block? |
| `orbit` | Off-axis third-person. Does it hold up from angles players circle to? |
| `detail` | Tight on the entrance. Hero-class detail and residue. |
| `front` / `side` | Orthographic-ish elevations for proportion checking. |
| `silhouette` | Black-on-white. If it is boring here, texturing will not save it. |
| `top` | Layout and footprint. |

Flags: `--no-figure` drops the 1.75 m reference, `--no-ground` drops the ground
plane, `--w`/`--h` set resolution.

## Conventions that are not negotiable

- **glTF 2.0, Y-up, right-handed, −Z forward, 1 unit = 1 metre.** Authoring in
  the target convention is what makes the Unreal/Unity port free.
- **Principal facade faces −Z.** The player arrives from the north gate and the
  locked 09:30 sun (azimuth 125°) lights exactly those faces. Build a venue
  facing +Z and every review render judges its shadowed back.
- **Seed every RNG** via `rng_for(asset_id, ...)`. Unseeded randomness breaks
  review diffing.
- **Chamfer every hard edge** — 15 mm architectural, 8 mm props, 3 mm small
  metal. First thing review rejects.

## Writing a venue module

```python
# tools/assetgen/venues/inn.py
NAME = "inn"
CELLS = ["E3", "E4"]

def build(ctx):
    ctx.emit(K.stone_plinth(9.0, 7.0, 0.45), "stone")
    wall = K.timber_frame_wall(9.0, 3.2, "hm.inn.front", style="close")
    wall.translate(0, 0, -3.5)
    ctx.emit(wall)
    ctx.entity("hm.inn.door.01", "door.inn", (0, 0.45, -3.6), verbs=["enter"])
```

`ctx.emit` takes a `Mesh` or a multi-material `Group`. `ctx.material(key)` is
handled automatically. `ctx.entity` registers an interactable and writes it to
`content/entities/<venue>.json`.

Drop the module in `tools/assetgen/venues/` and it is discovered automatically.

## Geometry core

| Function | Use |
| --- | --- |
| `mesh.box(sx,sy,sz,chamfer)` | True chamfered box — 6 faces + 12 bevels + 8 corners |
| `mesh.lathe(profile, seg)` | Revolve. Barrels, pottery, fountain bowls, mugs |
| `mesh.prism(profile2d, depth)` | Extrude. Gables, brackets, signage |
| `mesh.plank(l,w,t)` | Board with grain-aligned UVs |
| `mesh.cylinder(r,h)` | Chamfered-rim cylinder |
| `mesh.scatter_cobbles(w,d,id)` | Real per-stone paving geometry |
| `mesh.Group()` | Multi-material assembly. Anything composite |

## Material core

`materials.LIBRARY` maps a key to a builder. Use a library key — **never invent
a material inside a venue module.** If you need a new one, add it to the
library so every venue can use it, and so the palette stays locked.

Available: `plaster`, `plaster_shade`, `oak`, `oak_dark`, `oak_weathered`,
`terracotta`, `cobble`, `iron`, `canvas`, `thatch`, `stone`, `coal`, `painted`,
`glass`, `foliage`, `foliage_flower`.

Every material ships albedo + ORM (R=AO, G=roughness, B=metalness) + normal,
and emissive where relevant. ORM packing is what both Unreal and Unity expect.

### Two rules that cause most material defects

1. **Roughness must vary from two noise scales** (`MaterialSet.rough` does
   this). Uniform roughness reads as painted cardboard.
2. **Never bake world-position wear into a tiling texture.** Ground splash and
   water streaks depend on where a surface is in the world; baked into a tiling
   map they repeat at every seam. Apply them per-vertex at assembly instead.

## Known gaps

Honest list of what the pipeline does not yet do:

- **No LOD generation.** The chain is specified in Art Bible §6 but not built.
- **No lightmap or AO bake.** AO comes from the material's cavity term and
  runtime SSAO only.
- **No collision meshes.** Colliders are declared per entity as primitives.
- **No vertex-colour export**, so per-vertex world-position wear is specified
  but not yet wired through glTF.
- **No texture atlasing**, so draw calls are higher than the §5 budget wants.
