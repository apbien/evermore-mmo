# Architecture — Unlimitless Horizons

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
│                      Shop stock, NPC schedules, quests,      │
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

### Batching

Scenery is merged into **per-cell, per-material static batches** at build time.
Repeated props (barrels, crates, cobbles) use **GPU instancing** keyed by mesh
ID. The instancing key maps 1:1 onto Unreal's `InstancedStaticMeshComponent`
and Unity's `Graphics.DrawMeshInstanced`, so the batching strategy ports.

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
