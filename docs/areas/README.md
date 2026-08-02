# Areas

One directory per area of Arkadion — havens (towns), routes (the overland
ways between them), caves, dungeons. Hearthmere (Haven I) is the first and
the template.

## The pattern

Every area gets the same three documents plus its generated plan:

| File | What it is | Template |
| --- | --- | --- |
| `BUILD_DIRECTIVE.md` | The standing order: scope, locked compositions, geography, contents, structural rules, budget | `hearthmere/BUILD_DIRECTIVE.md` |
| `<KIND>_PLAN.md` | Generated master plan with a machine checker; never hand-edited (`TOWN_PLAN`, `ROUTE_PLAN`, `DUNGEON_PLAN`…) | `hearthmere/TOWN_PLAN.md` |
| `WORLD_BIBLE.md` | Lore, naming, briefs | `hearthmere/WORLD_BIBLE.md` |
| `plan/` | Generated drawings and schedules | `hearthmere/plan/` |

## The rules that keep many areas one game

1. **The base is never forked.** `docs/ART_BIBLE.md`,
   `docs/REVIEW_PROTOCOL.md`, `docs/ARCHITECTURE.md`,
   `docs/ASSET_PIPELINE.md`, `docs/REFERENCES.md`, and the shared core in
   `tools/assetgen/core/` are game-wide law with exactly one copy. An area
   that needs something the base lacks **adds** (a palette family, a
   material, a kit piece) through a decision entry — it never overrides.
2. **Every area is registered** in `docs/world/arkadion.md` before its
   directory exists.
3. **Every area gets its own entity-ID prefix.** `hm.*` is Hearthmere's —
   the town's, not the game's. Prefixes are never recycled (ARCHITECTURE §2).
4. **Area law is scoped area law.** The Art Bible sections marked
   Hearthmere-scoped (its scope note lists them) bind Haven I; a new area
   declares its own equivalents in its `BUILD_DIRECTIVE.md`, where they
   carry the same force.
5. **One review bar everywhere.** The blind AAA comparison and the
   builder/critic loop in `docs/REVIEW_PROTOCOL.md` apply to every area
   unchanged.
