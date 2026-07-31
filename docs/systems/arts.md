# Arts

Arts define *how* a Discipline expresses a Skill. A Discipline provides the
foundation; an Art provides specialization. This document defines the Art
architecture.

## Core Model

**An Art is a lens.** Once earned, it recolors a Skill's expression and is
toggleable for that Skill. The same Skill, viewed through different Art lenses,
becomes a different experience.

Every Skill is authored with **all** of its Art-versions in mind at design time.
The Skill contains every lens; access to those lenses is what's gated.

## Discipline Ownership (the two-key system)

Arts are owned by Disciplines. A Discipline grants access to a specific set of
Arts.

- The **Skill** is the lock — it contains all Art-versions.
- The **Discipline** is the key — it determines which of those versions you may
  unlock and equip.

Example: if Discipline A owns Arts 1–4, a player in Discipline A can pursue the
Art-versions 1–4 of any Skill they know. To pursue Arts 5–8, they must switch to
a Discipline that owns them.

## Equipping

A player can only **equip** Arts belonging to their currently-active Discipline.
This keeps each Discipline's combat identity coherent — no builds mixing every
Art at once. Switching Disciplines to change which Arts are equippable is free.

## Permanent, Global Unlocks (shared-unlock)

**Unlocking an Art-version of a Skill is permanent and global.** Once earned, it
is yours forever.

Crucially, if an Art is shared by multiple Disciplines (see overlap below),
earning that Art-version of a Skill under one Discipline unlocks it for **every**
Discipline that owns that Art. There is no re-earning the same Art-version per
Discipline. The grind is paid once; the flexibility is free afterward.

## Discipline Overlap and the Art Taxonomy

Disciplines are allowed to share Arts. This expresses philosophical adjacency
between Disciplines and softens the hard access walls without removing them.
Combined with shared-unlock, overlap becomes a *reward* for investing in a family
of related Disciplines.

Design Arts against this three-tier taxonomy:

- **Exclusive Arts** — owned by a single Discipline. The identity-defining,
  signature expressions. This is where a Discipline's soul lives. Make the most
  powerful, identity-critical Arts exclusive.
- **Shared Arts** — deliberately owned by 2–3 related Disciplines. The connective
  tissue that makes switching between adjacent Disciplines rewarding. Lean toward
  utility and cross-role flavor here.
- **Native / Discipline Skills** — the separate leveled floor (see
  `disciplines.md`). Not Arts, but part of the same identity structure.

## Relationship to Elements

Arts are **independent of elements.** A Skill's element/school (fire, frost,
physical, etc.) is a separate tag axis (see `skills.md`). Arts do not key
off element — an Art lens is not "the fire version," it is a distinct expression
that applies regardless of the Skill's element.

## Unlock Mechanism

The concrete unlock recipe for an Art-version of a Skill is defined in
`unlocks-and-discovery.md`. In brief: it combines a personal
proof-of-use requirement (using the Skill with the Art equipped, under meaningful
conditions) with a catalyst item that can be crafted or bought — so wealth can
accelerate the final step but cannot skip the personal experience.
