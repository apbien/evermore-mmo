# Unlocks and Discovery

This is the cross-cutting system that governs how Skills and Arts are acquired. It
touches Skills, Arts, Professions, and exploration. It also defines Evermore's
stance on datamining and secrecy in concrete mechanical terms (the philosophy is
in `../philosophy/discovery-principles.md`).

## Skill Unlocks

Skills are acquired through **discovery** — the primary progression path. The
exception is Discipline-native skills, which are the leveled floor learned by
advancing a Discipline (see `disciplines.md`).

Discovery types (from the exploration pillar):

- **Geographic** — finding previously unknown places
- **Historical** — learning about Arkadion's past
- **Mechanical** — learning how systems interact (a crafting reaction, a combat
  interaction, an environmental effect)
- **Skill** — finding new abilities, or unusual applications of known ones
- **World** — understanding deeper truths about Arkadion

## Art Unlocks

Unlocking an Art-version of a Skill combines two gates:

1. **Personal proof-of-use** — using the Skill with the target Art equipped,
   under meaningful conditions (not raw repetition). To do this you must be in a
   Discipline that owns the Art.
2. **A catalyst item** — craftable or buyable (e.g. an "Art catalyst"). Wealth
   can accelerate this final step, but cannot skip the personal proof-of-use.

This ties Arts into the Profession and knowledge economy (crafters make
catalysts) while keeping the principle that a guide reveals possibility but cannot
replace experience.

Unlocks are permanent and global (shared-unlock) — see `arts.md`.

## Server-Side Authority

Unlock state and trigger conditions are evaluated and recorded **server-side.**
The complete unlock graph is never shipped to the client.

What this achieves: it prevents client-side extraction of the full list of what
exists and how to get it. It kills the day-one datamine dump and protects
first-discovery prestige. The community wiki gets *built through play over time*
rather than *extracted in an afternoon.*

What this does **not** attempt: stopping the community from collectively mapping
the game once they're playing it. That mapping is expected and intended (see
below). Server-side authority protects the *pace and integrity* of discovery, not
its permanence.

## Repeatable vs. Consumable Secrets

The real defense against a discovered secret losing its value is designing
secrets that survive being known. Classify every secret:

- **Repeatable secrets** — mastery triggers, Art unlocks, crafting reactions,
  contextual interactions. These *survive* being posted, because knowing the
  trigger is not the same as performing it. A wiki entry is an invitation, not a
  spoiler. **Build the bulk of progression here.**
- **Consumable secrets** — a fixed hidden location, a one-time lever, a set puzzle
  solution. These *die* when posted. Use them sparingly, treat them as
  first-discovery prestige moments (the discoverer earns the historical record /
  title), and accept they become community knowledge quickly. **Do not build core
  progression on them.**

An implementation option for marquee consumable secrets: stream/download that
content only when a player approaches it, so it cannot be found in the files
before anyone reaches it. Use selectively — it adds latency and complexity.

## Authored-Shared World

Arkadion is authored and shared: everyone discovers the same world, and being
first is what earns prestige. Evermore does **not** use procedural-per-player
content as its foundation — that would break first-discovery prestige and the
knowledge economy (there would be no shared truth to trade or teach).

The datamine defense does not depend on procedural randomization. It depends on
the repeatable-secret design above.

## Rotating Layer

On top of the stable authored world sits a thin **rotating / seasonal
world-event layer** — a small set of time-boxed discoveries and events that
refresh mystery on a cadence. This provides fresh discovery without sacrificing
the shared world underneath, and ties into `../world-events.md`.

## Stretch Goals

These are additive; nothing depends on them.

- **Dynamic presentation.** All Skills and overworld interactions always exist,
  but may be *presented differently or acquired elsewhere at different times* —
  varying the route, never the destination, so first-discovery prestige and
  shared knowledge survive.
- **Retroactive unlocks from world events.** A major world event, once conquered
  by players, could retroactively open access to things in areas players did not
  previously know about.
