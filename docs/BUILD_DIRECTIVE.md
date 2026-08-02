# Build Directive — Hearthmere v2

**Read this after `ART_BIBLE.md` and before touching anything.** The Art Bible
is law about *how things look*. This is the standing order about *what we are
building and in what shape*. Where this conflicts with `WORLD_BIBLE.md`, this
wins and `WORLD_BIBLE.md` gets updated to match. Where it conflicts with
`ART_BIBLE.md`, the Art Bible wins.

## 0. The verdict on v1

v1 shipped 10 venue modules on a 96 m grid and reads as a diorama, not a town:

- The town has ~14 building masses. A town of three hundred people has ~80.
- There is no whole-town render. Every venue was signed off in isolation, so
  nothing caught composition, floating geometry, or roof/wall separation.
- Collision is one AABB per venue (`client/src/main.js`). The `streets` venue
  spans C1–C6, so its bounding box seals Ford Road. **The player cannot walk
  down the main street of the town.** This is why the build "can't be moved
  around in."
- The ground is a flat 300 m plane with a tiled dirt albedo. No terrain, no
  drainage logic, no transition between paving and earth.
- NPCs are placeholder capsules and are being removed.

v2 is not a polish pass over v1. It is a rebuild of the town on real
infrastructure, reusing the parts of `tools/assetgen/core/` that are good.

## 1. Scope of v2

The walled town of Hearthmere, complete, at the quality bar of Art Bible §8 —
which is: *would a player believe this shipped in a current AAA MMO?* Judged
side by side against Divinity's Reach (GW2), Gridania and Ul'dah (FFXIV), and
post-Legion WoW.

Interiors are in scope only where they are visible from the street through an
open door or window. Full walkable interiors are out of scope for v2 except the
Church of Summoning, which the player spawns inside.

**NPCs are out of scope and are being removed.** The town comes first. Do not
add characters, do not preserve `townsfolk`.

## 2. The grid (LOCKED)

- **12 × 12 cells of 16 m = 192 m × 192 m.** Columns `A`–`L` west→east, rows
  `1`–`12` north→south.
- **World origin (0,0,0) is the market square fountain**, at the grid centre.
  The grid therefore spans `x ∈ [-96, +96]`, `z ∈ [-96, +96]`.
- Cell `A1` spans `x[-96,-80] z[-96,-80]`. Cell letter index = `floor(x/16)+6`.
- Y-up, 1 unit = 1 metre, -Z forward, right-handed (glTF 2.0). Unchanged.
- The **town wall** rings the built area at roughly `±80 m`, following terrain
  and the river rather than a perfect square. Outside the wall, out to `±140 m`,
  is approach terrain: river, water meadow, orchard, the south road climbing
  away. Beyond that, a distance ring that only needs to read at silhouette.

## 3. Arrival (LOCKED — this replaces the v1 arrival)

**The player spawns on the teleportation altar inside the Church of Summoning.**
That is the canonical entry into the world. Consequences, all mandatory:

1. The church interior is fully walkable and is the first thing anyone sees. It
   gets hero-tier treatment: the summoning altar, light shafts from clerestory
   windows, a stone floor worn into a path from altar to doors.
2. **The church's main doors are a framing device.** Standing on the altar and
   looking out through the open doors, the player must see, in one composition:
   the descending church steps, a street leading the eye, the market square
   fountain as the focal point, and at least two other venue anchor silhouettes
   (guild tower, inn roofline, forge chimney, or wall gatehouse). Site the
   church to make this true. This frame is now the most important composition
   in the build.
3. The **north gate and its bridge over the Emberflow** remain a hero
   composition, but as the *departure/return* frame rather than the arrival.
4. `playerSpawn` in `content/town/hearthmere.json` moves to the altar.

**Nothing may stand on Ford Road's centreline.** Still true, still the rule
that the guild violated in v1.

## 4. Geography (LOCKED)

Hearthmere is a lake town at a ford. Make that legible from inside the walls:

- The **Emberflow** runs roughly east–west across the **north** of the town.
  Ford Road crosses it on a stone bridge just outside the north gate — the ford
  that named the road is still visible beside the bridge, silted and disused.
- The **Mere** opens to the **north-east**, where the river widens. A quay and
  water gate on the north-east wall give the town a working waterfront: moored
  flat-bottomed boats, nets, a crane, fish drying, the customs house.
- Ground **falls about 4 m from south to north** toward the water. This is not
  decoration: it is why the streets drain the way they do, why the pub's floor
  is sunken, why the blacksmith sits on the high south edge, and it gives the
  town silhouette a slope instead of a table.
- Outside the south gate the road climbs away toward the quest zones.

## 5. What the town contains

Target: **75–95 discrete building masses** inside the wall. Not 95 unique
generators — a modular townhouse kit with seeded variation carries the filler,
and hero venues are individually authored.

**Hero venues** (individually authored, art-director sign-off each):
Church of Summoning + altar plaza · Adventurer's Guild · Grey Heron Inn ·
The Ferryman's Lamp (pub) · Blacksmith & yard · Market square + fountain ·
Market stalls · North gatehouse + bridge · Town wall + towers + wall-walk ·
Quay & customs house.

**Secondary venues** (authored, lighter review):
Shop row (general store · apothecary · tailor) · Bakery · Confectioner ·
Chophouse (restaurant) · Mere-fish eatery · Watermill + granary on the river ·
Moot hall (town hall) · Bathhouse · Stables & waggon yard · Cooper · Chandler ·
Carpenter/joiner · Bowyer · Tannery & dye yard (downwind, by the water) ·
Well-house · Dovecote · Warehouse row.

**Filler** (procedural kit, seeded, no two identical):
Townhouses, cottages, workshops-with-dwelling-over, back-lane sheds, privies,
lean-tos, kitchen gardens, orchard, graveyard, midden.

**Infrastructure**: road network with real junctions, kerbs, gutters and
crossing stones · back alleys · steps and retaining walls where the ground
falls · drainage · street furniture (lamp brackets, hitching posts, mounting
blocks, horse troughs, boot scrapers, bollards, signposts) · washing lines ·
window boxes · vines · woodpiles · the residue that Art Bible §7 calls the
highest-value detail per unit of effort.

## 6. Non-negotiable structural rules

These exist because v1 broke every one of them.

1. **Nothing floats.** Every mass either sits on ground, or is carried by
   something that reaches the ground, or is visibly fixed to a wall by shown
   hardware. A generator that places an object must derive its Y from the
   terrain height function, never assume `y=0`.
2. **Roofs attach.** A roof plane meets its wall head at a physically explicable
   junction — wall plate, eaves board, and an overhang that oversails the wall
   face. No roof may be a separate floating prism above a box. Gable ends are
   closed. Ridges meet. Valleys and hips resolve.
3. **Terrain is a function, not a plane.** `core/terrain.py` owns a single
   deterministic `height(x, z)` used by every generator and by the client.
   Nothing may disagree with it.
4. **Collision is authored, not inferred.** Generators emit convex collision
   volumes per structure into `content/collision/<venue>.json`. The client loads
   those. Deriving one AABB from a venue's bounds is banned. Roads, doorways,
   alleys and the square must be walkable; a player must be able to walk from
   the church altar to every venue door in the town.
5. **Chamfer everything** (Art Bible §6) and **full PBR sets only**
   (Art Bible §5). First two things review rejects.
6. **Seed every RNG from the asset ID.** Determinism is what makes review
   diffing work.
7. **Extend `tools/assetgen/core/`, never fork it.** Divergent bevel or roof
   code is how the town loses cohesion. If two venues need it, it belongs in
   core.
8. **No anachronisms, no readable lettering** (Art Bible §2). Signage is
   pictorial.

## 7. Performance targets

This is packaged as a real MMO client, so the town must hold up with players
in it, not just in a screenshot.

| Resource | Budget (1080p, mid-range GPU, 60 fps) |
| --- | --- |
| Draw calls | < 900 |
| Triangles drawn | < 3.5 M |
| Texture memory | < 1.5 GB |
| Shadow-casting lights | 1 sun + 8 local |

Required techniques: per-cell per-material static batching · GPU instancing for
repeated props keyed by mesh ID · 4-step LOD chain (0–15 m / 15–40 m / 40–100 m
/ impostor) · frustum + cell distance culling · texture atlasing across the kit
· interiors as portal-linked cells so their contents are not drawn from
outside. All of these map 1:1 onto Unreal/Unity equivalents — see
`docs/ENGINE_PORTING.md`.

## 8. Verification — an asset nobody has looked at is not finished

- `tools/render/shoot.mjs` renders **one venue** in isolation. Necessary, not
  sufficient. It is why v1's composition defects shipped.
- `tools/render/town.mjs` renders the **assembled town** at the locked 09:30
  rig: the arrival frame, orthographic top-down, aerial obliques, and
  street-level eye-height views along a walk route. Every claim about
  placement, floating, road blocking, or sightlines must be backed by one of
  these images.
- Every review render includes a 1.75 m scale reference.
- Judge from the gameplay camera: 1.62 m eye, 3.5 m orbit, 55° FOV.
- The bar is Art Bible §8's last line, and it is a blind side-by-side, not a
  self-assessment.

## 9. Definition of done for v2

Every box in Art Bible §8, for every venue, plus:

- [ ] The player can walk from the church altar to every venue door.
- [ ] Nothing floats; every roof is attached; no geometry interpenetrates
      visibly.
- [ ] The arrival frame from the altar reads without a HUD.
- [ ] 75–95 building masses, no two visibly identical.
- [ ] Whole-town top-down and aerial renders read as a real settlement plan.
- [ ] Performance budget met with the whole town loaded.
- [ ] An art-director pass at ACCEPT on every hero venue and on cohesion.
