# Architecture — Evermore

## The governing decision

We are building **visuals first, but never in a way that has to be torn out to
become an MMO.**

The expensive part of retrofitting multiplayer is not writing netcode. It is
discovering that the world was authored as client-side scenery — meshes in a
scene graph with no stable identity, state living wherever it was convenient,
content hardcoded in the renderer, and no spatial structure to hang interest
management on. That refactor touches everything and is why "we'll add
multiplayer later" usually means "we'll rewrite it later."

So we pay four small costs now to avoid that:

| Seam | Cost now | What it buys |
| --- | --- | --- |
| Authoritative content in engine-neutral JSON | Write a schema instead of a literal | Server owns content on day one; client never becomes the source of truth |
| Stable entity IDs on every interactable | A registry and an ID scheme | The replication unit already exists |
| Spatial cell partitioning | A grid and a bucketing pass | Interest management and streaming drop in unchanged |
| Intents, not mutations | One indirection at the call site | Client→server RPC swaps in with zero call-site edits |

None of these slow down building a beautiful town. All of them are painful to
add afterwards.

---

## 1. Layer model

```
┌─────────────────────────────────────────────────────────────┐
│  content/            Authoritative data (JSON + schemas)     │
│                      Shop stock, opening hours, quests,      │
│                      prices, town layout, entity placement   │
│                      ── The server owns this. ──             │
└───────────────────────────┬─────────────────────────────────┘
                            │ loaded by both
              ┌─────────────┴─────────────┐
              ▼                           ▼
┌─────────────────────────┐   ┌───────────────────────────────┐
│  server/                │   │  client/                      │
│  Authoritative sim      │   │  Presentation + input         │
│  - entity registry      │   │  - renderer (three.js)        │
│  - intent validation    │   │  - scene assembly from        │
│  - state mutation       │   │    content/ + assets/         │
│  - interest management  │   │  - predicts, never decides    │
└─────────────────────────┘   └───────────────────────────────┘
              ▲                           │
              └────── intents ────────────┘
                  ◄───── state ─────
```

Today the server runs **in-process** in the client as a local module. The
transport is a direct function call behind an interface. Moving to a real
server is a transport swap, not an architecture change.

**The rule that keeps this honest:** `client/` may read from `content/`, but may
never author gameplay state. If the client needs to know a price, it reads the
authoritative record. If it wants to change one, it emits an intent.

---

## 2. Entity model

Everything the player can perceive as a *thing* — not scenery — is an entity.

```jsonc
{
  "id": "hm.blacksmith.anvil.01",   // stable, hierarchical, never reused
  "archetype": "prop.anvil",
  "cell": "C3",
  "transform": { "pos": [x,y,z], "rot": [x,y,z,w], "scale": 1.0 },
  "components": {
    "renderable": { "mesh": "anvil_hero", "materialSet": "iron_worked" },
    "interactable": { "verbs": ["inspect"], "range": 2.0 },
    "collider": { "shape": "box", "half": [0.35, 0.42, 0.18] }
  }
}
```

### ID scheme

`hm.<venue>.<kind>.<nn>` — `hm` is the Hearthmere zone prefix. IDs are assigned
at authoring time, are stable across builds, and are **never recycled**. They
are the key for replication, persistence, and save state.

### Why components

Components are how a renderable prop later gains network behaviour without
being rewritten. The anvil above becomes usable by adding a `crafting_station`
component. Its mesh, transform, and ID do not change, so nothing that
referenced it breaks.

### Scenery vs. entities

Cobblestones, roof tiles, and wall panels are **not** entities. They are baked
into static batched geometry with no identity and no server presence. Only
things that can be interacted with, occupied, owned, or changed get IDs.
Getting this line right keeps the entity count in the hundreds, not millions.

---

## 3. Spatial partitioning

The town is divided into a grid of **16 m × 16 m cells**, labelled `A1`…`F6`.

Every entity records its cell. This single field powers, in order of when we
need it:

1. **Now:** frustum and distance culling by cell, and asset streaming.
2. **Soon:** LOD selection at cell granularity.
3. **Later, unchanged:** network interest management — a client subscribes to
   its own cell plus the 8 neighbours, and receives updates only for entities
   in that set.

16 m is chosen so that a 3-cell radius (48 m) comfortably exceeds the ~40 m at
which detail becomes indistinguishable, and so a dense market cell holds a
tractable number of entities.

Cells are also the unit of **occlusion authoring**: building interiors are
separate cells linked by portals at doorways, so an interior's contents are
not simulated or drawn from outside.

---

## 4. Intents

The client never mutates gameplay state. It expresses what the player wants:

```js
// client
net.intent('RequestPurchase', {
  vendor: 'hm.market.stall.produce.01',
  item:   'apple_crate',
  qty:    2
});
```

The server validates (does the vendor exist, is it in range, does it stock the
item, can the player pay), mutates its own state, and broadcasts the result.
The client applies the authoritative result.

Local prediction is allowed for **presentation only** — playing the pickup
animation immediately, showing the coin-purse animation — but the number in the
inventory comes from the server response. That split is what makes prediction
safe to add later without exploits.

The current `LocalTransport` implements this interface with a direct call and
zero latency. A `WebSocketTransport` replaces it without touching a single
intent call site.

---

## 5. Rendering architecture

Presentation-side design, chosen for both visual quality and a clean port.

### Batching, LOD and culling

Built, and built in `tools/assetgen/core/` so that every venue gets it without
doing anything. See D-027 for what each technique actually buys, which is not
what their names suggest.

- **Static batching.** Everything a venue emits is re-bucketed at export into
  one primitive per (16 m cell, material). One primitive is one draw call, and
  the cell is also the unit the client culls and LODs — so batching and culling
  agree by construction rather than by discipline. `ctx.emit` is therefore free
  to call per prop; it was not, and that cost `streets` 1,344 draw calls.
- **LOD.** A four-step chain per cell at 1 / .5 / .2 / .06 triangles, exported
  as `MSFT_lod`, switching at 15 / 40 / 100 m. The coarse levels shed
  *materials* as well as triangles — capped at three at LOD2 and two at LOD3 —
  which is where the draw calls actually go.
- **GPU instancing.** `ctx.instance(mesh_id, mesh, transforms)` exports
  `EXT_mesh_gpu_instancing`, one node per (prototype, cell). Maps 1:1 onto
  Unreal's `InstancedStaticMeshComponent` and Unity's
  `Graphics.DrawMeshInstanced`.
- **Culling.** `client/src/lod.js` does LOD selection, frustum culling, cell
  distance culling, a build-time screen-size cull for clutter, and portal
  visibility for interiors. `tools/render/town.html` imports the same module, so
  the review harness measures the town the client draws (D-029).
- **Interiors** are declared with `ctx.interior(id, aabb, portals)` and are one
  occlusion group, not drawn unless the camera is inside them or in front of an
  on-screen doorway.

Both glTF extensions are fallback-safe and never listed in
`extensionsRequired`: a consumer that ignores them renders a correct, merely
expensive town.

### Quality settings (Low → Ultra)

Designed here, implemented as a client-side profile the renderer reads at
boot (D-066; implementation pending). The principle: **quality tiers reuse
shipping mechanisms — there are no separate low-spec assets.** Every venue
already exports a four-step `MSFT_lod` chain and per-cell batches; a tier
only changes when and how much of that reaches the GPU. Initial values,
to be tuned on real hardware:

| Lever | Low | Medium | High | Ultra |
| --- | --- | --- | --- | --- |
| LOD switch distances (m) | 8 / 20 / 50 | 12 / 30 / 75 | 15 / 40 / 100 | 15 / 40 / 100 |
| Render scale | 0.66 | 0.85 | 1.0 | native DPR |
| Shadow map / local shadow lights | 1024 / sun only | 2048 / sun + 2 | 4096 / sun + 4 | 4096 / sun + 8 |
| SSAO (GTAO) | off — vertex AO carries it | half-res | full | full |
| Bloom | off | on | on | on |
| Clutter screen-size cull | 2× threshold | 1.5× | ship | ship |
| Texture budget | skip top mip (¼ memory) | full | full | full |
| Anti-aliasing | FXAA | FXAA | TAA | TAA |

Rules that keep tiers honest:

- **Baked vertex AO and the ACES grade are identity, not quality.** Never
  disabled — Low must still look like Evermore, just coarser.
- **The perf budget gate runs at Ultra.** Lower tiers are player headroom,
  never an excuse to blow the §5 budget.
- **Gameplay is identical at every tier.** Collision, entities, interaction
  ranges, and sightline legibility do not change with settings; a Low player
  sees every interactable an Ultra player sees.
- **The review harness renders at Ultra**, and a venue may not depend on a
  tier effect (bloom, GTAO) to read correctly — each cohesion round includes
  one Low-tier spot render to prove it.

### The gameplay camera

The single source of camera policy (owner ruling, D-069). Other documents
cite this section; none may restate its numbers.

**One camera, one zoom axis.** Third person is the default: boom 3.6 m,
camera height 2.05 m, 55° FOV — the rig `client/src/player.js` ships and the
review harness's `gameplay` view reproduces. The mouse wheel dollies the boom
9.0 m → 0: below about 0.9 m the avatar fades out, and at 0 the camera is
the character's own eyes (1.62 m). First person is the inner end of the same
dolly, not a mode switch — which is what makes every transition seamless by
construction.

**Indoors, the camera adapts — never the world.** Interiors are built at
Art Bible §3 scale, are never oversized for the camera, and roofs are never
removed. When the *player* (not the camera eye) stands inside a declared
interior volume (`ctx.interior`), the boom's maximum becomes what the room
affords along the boom ray:

- A tall volume — the church nave at 12.2 m to the ridge — affords third
  person with a shortened indoor profile.
- A standard 2.70 m room smoothly collapses the cap toward first person; a
  genuinely cramped space lands there. The cap eases in and out with the
  camera's existing asymmetric smoothing, so crossing a doorway reads as one
  continuous dolly.
- The cap only lowers the *maximum*. The player may always dolly inward
  voluntarily, anywhere, indoors or out.

**Design consequence for venue briefs:** rooms meant for gathering — the inn
common hall, the guild hall, the church — are designed as open volumes,
which the period supplies honestly: Tudor halls were open to the rafters.
Players keep seeing their characters exactly where they socialise; small
private rooms accept first person, where closeness reads as intimacy rather
than loss.

**Camera collision respects interior floors.** The boom probe must treat
walkable-surface tops as camera blockers (today `probe()` filters to
`solid` volumes only), and the camera floor guard must use composed ground
height, not the raw terrain field. The motivating defect: at the spawn
altar, pitching down drives the camera through the church floor
(`kind="surface"`, at 2.40 m) into the podium masonry, because the only
floor guard is terrain (~0.45 m) plus a margin.

**Status:** policy is law now. Client implementation lands with the church
interior polish pass (PROMPT.md §6 priority (b)): extended zoom-to-first-
person with avatar fade, the player-indoors state and affordance cap, and
the floor-collision fix.

### Lighting

- One directional key (sun) with cascaded shadow maps
- Hemisphere ambient approximating sky/ground bounce
- Baked AO in the mesh vertex colours plus AO maps in indirect
- Local point/spot lights for forge, lamps, and window spill, budgeted per cell
- Screen-space rim pass for the anime separation signature

### Post-processing chain (order is deliberate)

`SSAO → bloom (threshold 1.0, soft knee) → tonemap (ACES) → colour grade LUT →
vignette → FXAA/TAA`

The grade LUT is where the anime look is finalized: lifted shadows, warm
midtones, slight cyan push in the shadows for complementary contrast.

**Built, in `client/src/atmosphere.js`, and there is exactly one of it** (D-049).
`makePostChain()` assembles the chain in that order and
`tools/render/town.html`, `tools/render/viewer.html` and `client/src/main.js`
all call it. The grade is a closed-form transform rather than a sampled LUT —
the transform has to exist before it can be baked, and `ENGINE_PORTING.md`'s LUT
bakes off it. SSAO is `GTAOPass` with its blend shader replaced so occlusion
tints toward Art Bible §1's `#4A3828` by ratio instead of multiplying the linear
beam by a near-black colour.

### The environmental layer

The same module owns everything the frame shares rather than the objects in it,
because `review/reports/ad-town-02.md` found that the absence of that layer, not
the quality of the venues, was what made the build read as parts:

- **Aerial perspective.** An analytic height-integrated exponential, warm near
  and cool far, with a forward-scattering lobe toward the locked 09:30 sun.
  Patched into `THREE.ShaderChunk` so it reaches every material without any of
  them being enumerated. Not `FogExp2`: uniform density hazes a river valley and
  a distance ridge identically.
- **Sky.** A gradient dome with a horizon value ramp, a sun disc and low cirrus,
  doubling as the PMREM source so the drawn sky and the IBL cannot disagree.
- **Horizon closure.** A square annulus stitched to the terrain plate's own
  boundary, falling away to 1200 m, so the ground does not end in mid-air at the
  world edge.

Every number is authored in `content/town/hearthmere.json` → `atmosphere`,
generated from `tools/plan/plan_data.py:ATMOSPHERE`, on the same rule as the
lighting rig (D-009). Depth separation between planes is measured, not asserted:
`tools/render/town.mjs --bands`.

### Performance budget (1080p, mid-range GPU, 60 fps)

| Resource | Budget |
| --- | --- |
| Draw calls | < 900 |
| Triangles | < 3.5 M |
| Texture memory | < 1.5 GB |
| Shadow-casting lights | 1 sun + 8 local |
| Frame time | 16.6 ms |

---

## 6. Directory contract

| Path | Owns | Rule |
| --- | --- | --- |
| `content/schemas/` | JSON Schema for all authoritative data | Schema changes are versioned |
| `content/town/` | Layout, cells, venue placement | No code |
| `content/entities/` | Entity records per venue | No code |
| `content/collision/` | Authored collision volumes per venue | Generated by `ctx.collider*`; venue-local space; the client may not infer collision from geometry (Directive §6.4) |
| `assets/meshes/` | Generated glTF/GLB | Generated only — never hand-edited |
| `assets/textures/` | Generated PBR sets | Generated only — never hand-edited |
| `tools/assetgen/core/` | Shared mesh/material/export library | The single source of geometry truth |
| `tools/assetgen/venues/` | Per-venue generators | One module per venue |
| `tools/render/` | Headless render + screenshot harness | Review infrastructure |
| `client/src/` | Renderer, input, presentation | May not author gameplay state |
| `server/src/` | Authoritative sim | No rendering imports, ever |
| `engine/unreal/` | UE5 project scaffold + import automation | Consumes `assets/` and `content/` |
| `review/` | Screenshots and art-director reports | Build output, reviewable in PRs |

**`assets/` is generated, not authored.** Every mesh and texture is the
deterministic output of a generator in `tools/assetgen/`. Fixing an asset means
fixing its generator and regenerating. This is what makes the art-director
iteration loop possible: a critique maps to a code change, not to manual
mesh-poking that can't be reproduced.

---

## 7. Determinism

All generators seed from a **fixed per-asset seed** derived from the asset ID.
The same commit produces byte-identical assets on any machine. This matters
because:

- Review screenshots are comparable across iterations — a visual diff reflects
  an intentional change, not RNG.
- Regenerating does not silently churn the whole world.
- A generator bug is reproducible.

Never call an unseeded RNG in a generator.

---

## 8. Engine port path

The assets and content are engine-neutral by construction:

- **glTF 2.0** meshes with PBR metallic-roughness materials — imports natively
  into UE5 (Interchange) and Unity (glTFast) with no transform fixup, because
  we author in glTF's own coordinate convention.
- **PNG texture sets** with channel packing documented in
  `docs/ASSET_PIPELINE.md`.
- **JSON content** consumed by a UE5 data-asset importer in `engine/unreal/`.

The three.js client is the **verification harness and reference
implementation** — it proves the assets look right and the systems work. It is
not a throwaway: it is also a genuinely shippable web client.

See `docs/ENGINE_PORTING.md` for the mapping table.
