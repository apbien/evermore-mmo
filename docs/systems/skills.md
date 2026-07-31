# Skills

Skills represent learned knowledge — what a character can do. They are not simply
unlocked buttons; they represent understanding.

Skills may include combat techniques, magical abilities, survival knowledge,
crafting knowledge, exploration abilities, and specialized techniques.

Everyone can learn Skills in their base form (no Art). Art-versions are layered on
top per the Art system (`arts.md`).

## Skill Attributes

Every Skill has three attributes:

- **Rarity** — discovery difficulty / prestige
- **Mastery** — the player's earned progression with the Skill
- **Art compatibility** — which Art lenses the Skill supports

There is deliberately **no "Rank" or power-tier attribute.** A Skill's mechanical
weight (a big situational nuke vs. a fast reliable staple) is *emergent* from its
cast time, cooldown, cost, and effect — not a label. Meteor being both powerful
and rare is two coincident facts about that Skill, not a single tier.

## Rarity

Rarity represents discovery difficulty, uniqueness, significance, and historical
importance. It is revealed on discovery.

**Rarity does not determine power.** Rarity and power are decoupled on purpose: a
common Skill mastered completely may surpass a rare Skill used poorly, and a
Mystic Skill may reveal a truth about Arkadion while being mechanically modest.

Tiers:

- **Common** — foundational knowledge (Basic Swordsmanship, Mining, Cooking,
  Blocking, Tracking).
- **Uncommon** — require specialization or effort (Advanced Shield Techniques,
  specialized crafting methods, improved tracking).
- **Rare** — require unusual circumstances (lost techniques, forgotten crafts,
  advanced movement).
- **Epic** — tied to significant discoveries or events (Stormtouched, Moon
  Jumper).
- **Mystic** — connected to deeper mysteries of Arkadion. These should reveal
  something about the world; they represent greater understanding, not simply
  greater power.

## Mastery

Mastery is the single player-fed progression axis per Skill. It is
**Art-independent** and lives on the base Skill, so it serves players who never
pursue Arts as well as those who do.

Mastery advances through **contextual and milestone use — never raw repetition.**
Casting a Skill a thousand times on a training dummy should not master it. Instead:

- **Contextual use** — mastery advances through varied and challenging
  application: using the Skill against new enemy types, under status effects, in
  clutch situations, to solve environmental problems.
- **Milestone use** — discrete feats ("land it on 3 enemies at once," "defeat an
  enemy above your level with it," "use it to trigger an environmental hazard").

This directly implements the philosophy that meaningful use — not volume — is
what creates understanding.

Mastery is structured as **discrete tiers.** Each tier grants increased potency
and/or unlocks extra traits, so every tier-up is an event rather than a grind
milestone. Mastery tiers are the Skill's visible progression; there is no
separate per-Skill level.

## Tags

Skills are tagged along independent axes. Tags are load-bearing: they are the
interface that Arts, mastery-triggers, role-balance checks, and search all read
against — not just labels. Add a tag only when a system needs to query it.

**Effect type** (a Skill may have several): `damage`, `heal`, `buff`, `debuff`,
`HoT`, `DoT`, `control`, `shield`.

**Targeting / shape** (usually one): `single-target`, `AOE`, `self`.

**Element / school** (its own axis): fire, frost, physical, etc. Note that Arts
are independent of element — this axis is separate from Art compatibility.

## Skill Expression Example

The Skill **Stormtouched** expresses differently by Discipline and Art:

- **Vanguard** — lightning-infused defense, storm barriers, charged attacks
- **Arcanist** — storm manipulation, ranged lightning abilities
- **Ranger** — weather awareness, storm-enhanced mobility

The same Skill creates different experiences depending on the Art lens applied.
