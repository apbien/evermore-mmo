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
| `gameplay` | **The one that matters.** The true third-person gameplay rig (single source: ARCHITECTURE §5 "The gameplay camera"), character in frame. The game is always default third-person, so this is the player's actual camera. |
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

The context owns material registration, batching, LOD, atlasing and export —
a venue gets all of those without asking. Four things are the module's own
job: geometry, instancing for repeated props, collision, and entities. A
minimal but complete venue touches all four:

```python
# tools/assetgen/venues/inn.py
NAME = "inn"
CELLS = ["E3", "E4"]

def build(ctx):
    # Geometry. Emit per prop or pre-merged — write() re-buckets everything
    # into one primitive per (cell, material) either way.
    ctx.emit(K.stone_plinth(9.0, 7.0, 0.45), "stone")
    wall = K.timber_frame_wall(9.0, 3.2, "hm.inn.front", style="close")
    wall.translate(0, 0, -3.5)
    ctx.emit(wall)

    # Repeated props are DECLARED, never emitted N times (Directive §7):
    # one prototype, N transforms, one GPU-instance batch per cell.
    ctx.instance("barrel_oak", K.barrel("hm.inn.barrel"),
                 [(3.1, 0.45, -2.2, 0.7), (3.9, 0.45, -2.6, 2.1)])

    # Only for venues that can be entered: an interior is an occlusion cell
    # plus its doorway portals, and its geometry is routed into it explicitly
    # so the street never draws it.
    ctx.interior("taproom", aabb=((-4.3, 0.45, -3.3), (4.3, 3.6, 3.3)),
                 portals=[{"pos": (0, 1.5, -3.5), "size": (1.2, 2.1),
                           "normal": (0, -1)}])
    ctx.emit(taproom, interior="taproom")

    # Collision is MANDATORY (Directive §6: authored, never inferred) and is
    # declared next to the geometry it belongs to, in venue-local space.
    # The shell with its doorway, and the steps that make a door on a plinth
    # reachable:
    ctx.collider_walls(9.0, 7.0, 3.2, y=0.45, doors=[("-z", 0.0, 1.2)])
    ctx.collider_steps((0.0, 0.0, -3.6), 0.45, width=1.5)

    # Interactables. Anything with a verb gets a stable ID; scenery stays
    # anonymous batched geometry.
    ctx.entity("hm.inn.door.01", "door.inn", (0, 0.45, -3.6), verbs=["enter"])
```

`ctx.emit` takes a `Mesh` or a multi-material `Group`; `ctx.material(key)` is
handled automatically. `ctx.instance` accepts `(x,y,z)`, `(x,y,z,yaw)`, a dict
or a 4×4 per transform, and instances are grouped by cell so they still cull.
`ctx.lod(mesh_id, levels)` overrides the automatic decimator for the rare
mesh whose silhouette must survive at distance. One-off collision volumes use
`ctx.collider(...)` (box / cylinder / hull, `solid` or `surface`) or
`ctx.collider_from(geom, ...)` to derive a box from bounds; everything lands
in `content/collision/<venue>.json`. `ctx.entity` registers an interactable
and writes it to `content/entities/<venue>.json`.

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

`materials.LIBRARY` maps a key to a builder — around 110 of them, so the list
is not restated here where it would rot. The registry publishes itself:
every build writes `assets/textures/manifest.json` with each key's coverage,
class, density and flags, so that file (or `materials.py` itself) is the
current answer to "what exists".

The rule: **never invent a material inside a venue module — extend the
registry.** `ctx.material()` refuses unknown keys for exactly this reason. A
new material goes in `LIBRARY`, so every venue can use it and the palette
stays locked.

Every material ships albedo + ORM (R=AO, G=roughness, B=metalness) + normal,
and emissive where relevant. ORM packing is what both Unreal and Unity expect.

### Two rules that cause most material defects

1. **Roughness must vary from two noise scales** (`MaterialSet.rough` does
   this). Uniform roughness reads as painted cardboard.
2. **Never bake world-position wear into a tiling texture.** Ground splash and
   water streaks depend on where a surface is in the world; baked into a tiling
   map they repeat at every seam. Apply them per-vertex at assembly instead.

## Known gaps

An earlier version of this list named LOD, collision, vertex colours and
atlasing as missing. All four are built now, into the shared core, so a venue
gets them without asking:

- **LOD** — `core/batch.py` decimates a four-level chain per (cell, material)
  batch and writes it as `MSFT_lod` + screen coverage; `ctx.lod()` overrides
  the decimator where a silhouette must survive.
- **Collision** — authored volumes (`core/collision.py`, the `ctx.collider*`
  family) written to `content/collision/`. Declared, never inferred.
- **Vertex colours** — `COLOR_0` is exported and carries exactly the
  per-vertex wear rule above: terrain splat and water-depth tints, per-course
  roof aging, the season tint (D-047).
- **Texture atlasing** — `core/atlas.py`; eligible kit-prop materials are
  folded onto shared pages automatically at emit time.

Honest list of what the pipeline still does not do:

- **No lightmap or AO bake.** AO is the material's cavity term plus runtime
  GTAO; nothing is baked per placement.
- **No skeletal meshes or animation.** The glTF writer has no skins.
  Characters are out of scope (D-012).
- **No streaming or unload path.** The client loads the whole town at start
  and culls from there; nothing is ever unloaded, and coarse LOD levels
  cannot be fetched separately from LOD0.
- **No frame-time instrumentation.** `client/src/perf.js` attributes draws
  and triangles per stage against the §7 budget, but nothing measures
  milliseconds — so a draw-call win cannot yet be confirmed as a time win.
