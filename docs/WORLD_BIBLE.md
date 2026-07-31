# World Bible — Hearthmere (Haven I)

Hearthmere is **Haven I** in the settlement register of `docs/GAME_DESIGN.md`.
Canon pairs a numerical designation with a historical name; players may use
either. This document covers the historical settlement in detail.

## The place

Hearthmere sits where the mere meets the old road — a lake town that grew up
around a ford, then a bridge, then a market. It is prosperous but not rich,
old but well-kept. Three hundred people live here. Everyone knows everyone.

It is the **first town** of Arkadion. The player arrives through the north gate having
just entered the world, and everything they see must say: *you are safe here,
this place is real, and there is somewhere to go next.*

### Tone

Warm, lived-in, unhurried. Morning light, woodsmoke, the sound of a hammer
somewhere. Hearthmere is not in danger and is not hiding anything. The danger
is out past the gate, which is exactly why the town must feel like shelter.

### Founding logic

Every convincing town answers *why is it here* and *why is it shaped like
this*. Hearthmere's answer:

- The **ford** came first — the only safe crossing of the Emberflow for a day
  in either direction.
- The **market** grew at the crossing because travellers had to stop anyway.
- The **guild** came when the roads got dangerous, and built the only stone
  tower in town.
- The **town wall** is low, more customs boundary than defence — Hearthmere
  has never been besieged, and its gate is decorative in the way a prosperous
  trading town's gate is.

This history is why the streets bend (they follow the old cart tracks to the
ford, not a planner's grid), why the square is irregular, and why the guild
looks like it does not quite belong.

---

## Town plan

96 m × 96 m core, on the 16 m cell grid from `docs/ARCHITECTURE.md`.
**World origin (0,0,0) is the centre of the market square fountain.**

```
        ← -X (west)                              +X (east) →
      ┌────────┬────────┬────────┬────────┬────────┬────────┐
  -Z  │   A1   │   B1   │   C1   │   D1   │   E1   │   F1   │
 (N)  │        │        │  NORTH GATE ▲   │        │        │   Row 1
      │  wall  │  wall  │  ═══ARRIVAL═══  │  wall  │  wall  │
      ├────────┼────────┼────────┼────────┼────────┼────────┤
      │   A2   │   B2   │   C2   │   D2   │   E2   │   F2   │
      │ cottage│ cottage│ ADVENTURER'S    │ stable │ cottage│   Row 2
      │        │        │ GUILD (hero)    │        │        │
      ├────────┼────────┼────────┼────────┼────────┼────────┤
      │   A3   │   B3   │   C3   │   D3   │   E3   │   F3   │
      │ garden │  PUB   │   MARKET SQUARE │  INN   │ cottage│   Row 3
      │        │ "Ferry-│  ░░ STALLS ░░   │ "Grey  │        │
      ├────────┼─ man's ┼──── FOUNTAIN ───┼ Heron" ┼────────┤
      │   A4   │ Lamp"  │   C4   │   D4   │   E4   │   F4   │
      │ cottage│        │   ░░ STALLS ░░  │        │ orchard│   Row 4
      ├────────┼────────┼────────┼────────┼────────┼────────┤
      │   A5   │   B5   │   C5   │   D5   │   E5   │   F5   │
      │ midden │ BLACK- │ GENERAL│ APOTH- │ TAILOR │ cottage│   Row 5
      │        │ SMITH  │ STORE  │ ECARY  │        │        │
      ├────────┼────────┼────────┼────────┼────────┼────────┤
      │   A6   │   B6   │   C6   │   D6   │   E6   │   F6   │
  +Z  │  wall  │ smith  │  SOUTH ROAD ▼   │  wall  │  wall  │   Row 6
 (S)  │        │  yard  │  ═══ TO QUESTS  │        │        │
      └────────┴────────┴────────┴────────┴────────┴────────┘
```

### Venue register

| Venue | Cells | Role | Anchor silhouette |
| --- | --- | --- | --- |
| **Market Square** | C3 D3 C4 D4 | Hub. All roads meet here | Fountain + awning canopy |
| **Adventurer's Guild** | C2 | Hero building. Quest board, the "what next" | Stone tower + crimson banners |
| **Grey Heron Inn** | E3 E4 | Rest, save point, second-largest mass | Three storeys + gabled dormers |
| **Ferryman's Lamp (pub)** | B3 B4 | Social heart, warmest interior | Hanging lamp sign + chimney smoke |
| **Blacksmith** | B5 B6 | Craft. Loudest, most active | Forge chimney + open work yard |
| **Shop row** | C5 D5 E5 | General store, apothecary, tailor | Continuous shopfront + hanging signs |
| **Stalls** | in C3–D4 | Market traders, 8 stalls | Striped awnings |
| **Cottages** | perimeter | Residential filler, makes it a *town* | Varied rooflines |

### Streets

- **The Ford Road** — main N–S artery, 7 m wide, enters at the north gate,
  crosses the square, exits south. Cobbled, worn to a shallow trough down the
  centre from cart traffic.
- **Mere Street** — E–W, 6 m, connects pub to inn across the square.
- **Smith's Lane** — B4→B5, 3.5 m, narrows toward the forge, unpaved past the
  midpoint (dirt and cinder).
- **Back alleys** — 2.5 m, between cottage blocks. Dark, damp, laundry
  overhead. These sell the town's density more than the main streets do.

### The arrival shot

The player spawns at **(0, 0, -44)**, just inside the north gate, facing south
down the Ford Road at the square.

This single frame is the most important composition in the build. It must show,
in one view: the gate arch framing the shot, the Ford Road leading the eye, the
fountain as the focal point at centre, the guild tower rising on the LEFT, the
inn's roofline on the right, stall awnings adding colour, and NPCs moving.

**Nothing may stand on the road's centreline.** The guild originally spanned
C2+D2, which put it squarely across Ford Road and blocked the view through to
the fountain — the composition above is impossible if the hero building is in
the way. The guild sits west of the centreline; the road stays clear.

Everything must be legible with no HUD. If the player does not immediately know
where to walk, the composition has failed.

---

## Venue briefs

Each builder agent owns one. The brief is the intent; the Art Bible is the law.

### Market Square — `C3 D3 C4 D4`

The town's living room. An irregular plaza, wider at the north (where the road
enters) than the south, because it grew rather than being planned.

- **Fountain** at origin — the anchor. Carved stone, worn lip where people sit
  and where buckets scrape, algae in the shaded north face, constantly running
  water from a spouted heron head (the town's emblem).
- **8 stalls** in two loose rows, not a grid. Traders arrange for footfall, so
  stalls cluster near the road mouth and thin toward the south.
- Ground is cobbled but **worn into desire paths** — the cobbles are polished
  smooth along the diagonal everyone actually walks, mossy where nobody does.
- Residue: spilled produce, a broken crate nobody has cleared, pigeons, a dog
  under a cart, chalk marks on the fountain lip where a trader tallies.

### Adventurer's Guild — `C2 D2`

The hero building and the player's "what do I do next." Deliberately reads as
**imported** — built by an outside organisation with outside money. Where the
rest of Hearthmere is timber and plaster, the guild is dressed stone with a
square tower, and it is the only building in town that is symmetrical.

- Tall double doors, always open, worn threshold stone dished by boots.
- **Quest board** under the porch — the single most important interactable in
  the town. Layered parchment, some notices new and crisp, some sun-bleached
  and curling, wax seals, iron pins, a few torn corners where notices were
  taken.
- Crimson banners on the tower, wind-moved.
- Interior visible from the door: a stone hall, a reception counter, a big map
  on the wall, weapon racks, adventurers loitering.

### Grey Heron Inn — `E3 E4`

Three storeys, the tallest timber structure in town, jettied upper floors
overhanging the street (period-correct and great for silhouette). Named for the
birds on the mere.

- Painted hanging sign: a grey heron, hand-painted, weathered, swinging.
- Warm light in every window — the inn is the most inviting thing in the frame.
- Ground floor: common room, hearth, long tables, stairs up.
- Stable attached at `E2` with a water trough, hay, tack on pegs.
- Residue: boots by the door, a cat on the windowsill, laundry on the upper
  balcony, smoke from two chimneys.

### The Ferryman's Lamp (pub) — `B3 B4`

Older and lower than the inn — this is the *locals'* place, not the
travellers'. Slightly sunken floor (the ground rose around it over two
centuries), heavy low beams, small windows.

- Sign is an actual **iron ferryman's lamp** on a bracket, not a painted board.
- Warmest interior in the town. Firelight, not daylight, defines it.
- Outside: two trestle tables, worn benches, a dog, barrels awaiting collection.
- Residue: rings on the tables from mugs, a dartboard, a leaning stack of
  empty casks, sawdust on the floor at the threshold.

### Blacksmith — `B5 B6`

The most *active* venue — this one has to feel hot and loud. Placed at the edge
for fire risk, which is why Smith's Lane narrows and turns to cinder.

- **Open-fronted work yard**, roofed but not walled, so the player can see the
  work. This is the correct historical form and far better for gameplay.
- **Forge** with live fire — the town's strongest light source and the only
  significant emissive. Coal glow, sparks, heat shimmer.
- Anvil on an oak stump, quench barrel with scummy water, bellows, tool rack
  arranged by workflow (not by size), a grindstone.
- Residue: a half-finished blade in the quench, horseshoes in a pile,
  scale and cinder ground into the dirt floor, scorch marks on the posts,
  a leather apron on a hook.

### Shop row — `C5 D5 E5`

Three shops sharing party walls, which is how towns actually build. Continuous
frontage, varied above the ground floor.

- **General store** — barrels and sacks spilling onto the street, broadest
  goods, most cluttered.
- **Apothecary** — hanging dried herbs, small leaded windows, bottles,
  the most colourful interior.
- **Tailor** — bolts of cloth, a dress form in the window, the tidiest.
- Each has a **pictorial hanging sign** on a wrought-iron bracket.
- Shared: shuttered display windows that fold down into counters (period
  correct, very readable as "shop").

### Stalls — inside `C3 D3 C4 D4`

Eight, each individually specified so none repeats: produce, fish (fresh from
the mere), bread, cloth, pottery, charms/trinkets, herbs, roast meat.

- Striped canvas awnings, sagging and patched differently per stall.
- Each is a *person's business* — the pottery seller stacks carefully, the
  fishmonger's boards are wet and scaled, the baker's stall is dusted in flour.
- These carry most of the square's colour. They are why the square reads as
  busy rather than as an empty plaza.

---

## Naming

- **Town:** Hearthmere (Haven I)
- **Lake:** the Mere
- **River:** the Emberflow
- **Inn:** The Grey Heron
- **Pub:** The Ferryman's Lamp
- **Main road:** Ford Road
- **Emblem:** a grey heron, used on the fountain spout, the gate keystone,
  and the town's few official markings

Remember: **no readable lettering anywhere in the world.** Names exist in
dialogue and UI, never painted on a wall.
