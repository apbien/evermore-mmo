# Changelog

## 2026-07-31

Split the single `GAME_DESIGN.md` into a structured `docs/` tree
(`philosophy/`, `world/`, `systems/`, `social/`, `world-events.md`). The
original file is preserved as `GAME_DESIGN.md.bak`.

The new `systems/` documents add the unlock architecture:

- Discipline-owned Arts with shared-unlock (unlocking an Art-version of a
  Skill under one Discipline unlocks it for every Discipline that owns
  that Art).
- The Rarity/Mastery skill model (Rarity as discovery difficulty and
  prestige, decoupled from power; Mastery as the player-fed,
  Art-independent progression axis).
- A skill tag taxonomy (effect type, targeting/shape, element/school) as
  the load-bearing interface Arts, mastery-triggers, and role-balance
  checks query against.
- The server-side / repeatable-vs-consumable secret discovery model
  (unlock state evaluated server-side to protect first-discovery pace,
  with secrets classified as repeatable or consumable so discovered
  knowledge stays valuable instead of "solving" the game).
