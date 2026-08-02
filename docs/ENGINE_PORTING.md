# Engine Porting

## Why the assets are portable

Everything expensive in this repo — the meshes, the PBR texture sets, the town
layout, the entity records — is engine-neutral by construction. The three.js
client is a reference implementation and verification harness, not the thing
that would be hard to replace.

The portability comes from three deliberate choices:

1. **Authored in glTF 2.0's own coordinate convention** — Y-up, right-handed,
   −Z forward, 1 unit = 1 metre. Both Unreal and Unity import glTF natively.
   Because we author in the target convention there is no transform fixup, no
   scale factor, and no flipped-normal debugging.
2. **ORM channel packing** — R=occlusion, G=roughness, B=metalness in one
   texture. This is glTF's own convention when `occlusionTexture` and
   `metallicRoughnessTexture` share an image, *and* it is the native packing
   for both engines.
3. **Content as JSON, not as scene files.** The town layout and entity records
   describe the world declaratively. An importer reads them; nothing is locked
   inside a proprietary scene format.

## Which engine

**Unreal Engine 5** is the recommendation for a large-scale MMO:

| Factor | UE5 | Unity |
| --- | --- | --- |
| Out-of-box world scale | World Partition, built for large streamed worlds | Requires third-party or custom streaming |
| Rendering ceiling | Nanite + Lumen + VSM; highest fidelity available | HDRP is capable but more assembly required |
| Dedicated server | First-class, replication built into the actor model | Netcode for GameObjects is younger |
| Source access | Full C++ source | Closed (barring enterprise licensing) |
| Our art style | Handles stylised PBR well; Lumen suits the warm-bounce look | Also fine |

Unity's advantages (iteration speed, C#, smaller team ramp) are real but matter
less for a project whose defining constraints are world scale and player count.

## Mapping table

| This repo | Unreal 5 | Unity |
| --- | --- | --- |
| `assets/meshes/*.gltf` | Interchange glTF import → Static Mesh | glTFast → Mesh + Prefab |
| ORM texture | `M_Hearthmere_Base` sampling R/G/B | Standard/HDRP mask map (needs channel swizzle) |
| `content/town/hearthmere.json` | Data Asset + editor utility that spawns venues | ScriptableObject + spawner |
| `content/entities/*.json` | `AHearthmereEntity` actors with component set | GameObjects + components |
| 16 m cell grid | World Partition cells / Replication Graph nodes | Custom spatial hash |
| `ctx.entity` component records | Actor Components | MonoBehaviours |
| Intents (`net.js`) | Client→Server RPC (`Server_RequestPurchase`) | ServerRpc |
| `Sim` (`server/src/sim.js`) | Dedicated server `AGameModeBase` + authoritative subsystem | NetworkBehaviour server logic |
| `ctx.instance` → `EXT_mesh_gpu_instancing` | `HierarchicalInstancedStaticMeshComponent` | `Graphics.DrawMeshInstanced` |
| `ctx.lod` / auto chain → `MSFT_lod` | StaticMesh LOD0–3 (Interchange reads it) | LODGroup |
| `cullAt` (screen-size cull) | ISM `CullDistances` / Cull Distance Volume | LODGroup culled % |
| `ctx.interior` + portals | Level Instance + Precomputed Visibility / Data Layer | Occlusion Portal |
| Per-cell batch node (`venue#cell`) | World Partition cell / HLOD proxy | Custom spatial hash |
| Locked 09:30 lighting | Directional Light + Sky Light, values in Art Bible §4 | Same |
| Post chain | Post Process Volume (ACES, bloom 0.32, SSAO) | Volume profile |

## Batching, LOD and instancing (Directive §7)

These are not runtime tricks the three.js client happens to do. They are baked
into the exported glTF by `tools/assetgen/core/venue.py`, in forms both engines
read natively, and they are the reason a 90-building town fits in 900 draw
calls.

### What is in the file

1. **One node per (16 m cell, LOD level)**, named `venue#cell` /
   `venue#cell$lod1`, holding one primitive per material. That is one draw call
   per material per cell, and the cell is also the culling unit — so batching
   and culling agree by construction.
2. **`MSFT_lod`** on each level-0 node, listing levels 1–3 as alternates.
   Alternates are referenced *only* from the extension and are never scene
   roots, so a consumer that ignores it renders a correct, merely expensive
   town. Switch distances are 15 / 40 / 100 m; `MSFT_screencoverage` carries
   the same decision as coverage fractions for importers that prefer it.
3. **`EXT_mesh_gpu_instancing`** on instance batches, one node per (prototype,
   cell). The prototype geometry is written once and shared by every cell's
   node, and the LOD alternates re-use the same instance accessors.
4. **A manifest at `extras.hm`** — cells, bounds, per-level triangle and
   primitive counts, instance batches, cull distances, interiors and portals.
   Interchange discards it, so `engine/unreal/import_town.py` reads it out of
   the JSON directly. Recording the batching as *data* rather than leaving it
   implicit in the node graph is what makes that possible.

### Unreal specifics

- Import with **Combine Meshes off**. Combining merges the per-cell split and
  destroys both the culling granularity and the LOD chain.
- Interchange reads `MSFT_lod` into StaticMesh LODs and
  `EXT_mesh_gpu_instancing` into instanced components. `import_town.py` then
  re-forms the instance batches as `HierarchicalInstancedStaticMeshComponent`s
  so the build's `cullAt` becomes `SetCullDistances`, which Interchange has no
  way to know about.
- Fold each `venue#cell` actor into a **World Partition** cell of the same 16 m
  module. The grid is already aligned to `content/town/hearthmere.json`, so the
  streaming partition, the replication graph nodes and the client's culling
  partition are one grid rather than three.
- `MIN_COVERAGE` in `core/venue.py` (0.008 of frame height) is the same
  threshold a Cull Distance Volume expresses in metres; the exported `cullAt`
  is that threshold already resolved to a distance, so it transfers verbatim.

### Unity specifics

- glTFast reads `EXT_mesh_gpu_instancing`; it does **not** read `MSFT_lod`.
  Build `LODGroup`s from the manifest's `lodDistances` and `cells[].lodPrims`
  in the importer rather than expecting them for free.
- `cullAt` becomes the LODGroup's culled percentage — convert with the same
  `radius / (distance * tan(fov/2))` the exporter used.

**The instancing key maps 1:1.** The batching strategy in
`docs/ARCHITECTURE.md` §5 was chosen so that per-material, per-cell batches
become ISM components without re-authoring.

## Import procedure (UE5)

1. Create a blank C++ project, target 5.4+.
2. Enable **Interchange Framework** and **glTF Importer** plugins.
3. Copy `assets/` into `Content/Hearthmere/Raw/`.
4. Import glTF with: *Generate Lightmap UVs* off (we use Lumen), *Combine
   Meshes* off (we need per-material sections for instancing), scale 100
   (Unreal is centimetres; glTF is metres).
5. Build the master material `M_Hearthmere_Base`:
   - `BaseColor` ← albedo texture
   - `Roughness` ← ORM.**G**
   - `Metallic` ← ORM.**B**
   - `AmbientOcclusion` ← ORM.**R**
   - `Normal` ← normal texture (OpenGL +Y — **tick Flip Green Channel**, as
     Unreal expects DirectX −Y)
6. Run the layout importer (`engine/unreal/import_town.py`) as an editor
   utility to place venues from `content/town/hearthmere.json`.

**The green-channel flip is the one thing that silently looks wrong if missed.**
Our normals are OpenGL convention (Art Bible §5); Unreal is DirectX. Lighting
will appear subtly inverted on every surface if this is skipped.

## What does not port

Being honest about the boundary:

- **The three.js renderer, post chain, and player controller.** These are the
  reference implementation. Unreal has its own.
- **The procedural generators** stay as an offline Python pipeline producing
  glTF. That is the right place for them — they are the source of truth for the
  art, and they should not become engine plugins.
- **Runtime shader work** (the sky dome, the rim pass) is re-authored per
  engine.

## Known gaps before a real port

- No collision meshes — colliders are declared as primitives per venue in
  `content/collision/`, which an importer must turn into simple collision.
- **Mesh memory, not draw calls, is now the binding constraint.** The four-step
  LOD chain adds ~76% to every venue's vertex buffer, and the town's `.bin`
  files total ~180 MB. That is fine for a packaged Unreal build and painful for
  a web client. The fixes are ordinary and none of them is done: quantised
  vertex attributes (`KHR_mesh_quantization`), Draco or Meshopt compression,
  and streaming the coarse levels separately from LOD0.
- No skeletal meshes or animation — the player is a placeholder capsule, and
  characters are out of scope for v2 entirely (D-012).
- Interiors are authored (`ctx.interior`) and culled by the client, but no
  venue declares one yet; the church will be the first.
