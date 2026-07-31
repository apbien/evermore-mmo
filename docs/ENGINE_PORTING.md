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
| Repeated props | `InstancedStaticMeshComponent` | `Graphics.DrawMeshInstanced` |
| Locked 09:30 lighting | Directional Light + Sky Light, values in Art Bible §4 | Same |
| Post chain | Post Process Volume (ACES, bloom 0.32, SSAO) | Volume profile |

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

From `docs/ASSET_PIPELINE.md`, these need doing regardless of engine:

- No LOD chain generated (specified in Art Bible §6, not built)
- No collision meshes — colliders are declared as primitives per entity
- No texture atlasing, so draw calls exceed the §5 budget
- No vertex-colour export, so position-dependent wear is specified but unwired
- No skeletal meshes or animation — NPCs and the player are placeholder capsules
