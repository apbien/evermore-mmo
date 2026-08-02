# Documentation audit — lead game designer (fresh eyes) — round 01

Date: 2026-08-02 · Reviewer: independent agent with no project context, briefed
as a veteran MMO lead game designer. Commissioned by the owner. Preserved
verbatim (first-hour reconstruction included in full). Dispositions:
`docs-audit-synthesis-01.md`. Decision: D-070.

---

## Headline

You have a **world-art production bible of genuinely professional quality** bolted to a **game design document that is 799 lines long and describes no game**.

The numbers: `docs/philosophy/` + `docs/world/` + `docs/systems/` + `docs/social/` + `world-events.md` = **799 lines total**. The art chain = **2,173 lines for one town**, plus ~14,000 lines of review reports. The art direction on Hearthmere is better than most shipped MMOs' first towns. The game design would not pass a publisher's first gate.

I would not sign this off as a design foundation. I would sign off the *art* foundation immediately.

## Findings — ranked

### 1. [COHESION] CRITICAL — The game design tree has no authority and no reader
`PROMPT.md` §3 names the governed documents and the binding list — **not one of `docs/philosophy/`, `docs/systems/`, `docs/social/`, or `docs/world/` appears anywhere in that chain.** `CLAUDE.md`'s read-first table omits them. Meanwhile `docs/README.md:14` states "The philosophy layer is authoritative." Two documents make opposite claims about what governs the project, and the operative one has quietly demoted the entire game design to unread commentary. `git log` confirms it: the design tree landed in one commit and has not been touched since, while 60+ decisions accumulated in the art chain.
**Fix:** put the tree into the chain, or delete the claim in `docs/README.md` and admit this is an art project.

### 2. [MISSING] CRITICAL — There is no combat design, in a game whose core identity system is defined as combat
`systems/disciplines.md:5` — "A Discipline defines a player's primary combat identity." That is the entire treatment. No targeting model, no GCD, no resource model, no TTK target, no threat rules despite Vanguard being "threat management," no animation-cancel policy, no combat tick rate. `skills.md:23` references "cast time, cooldown, cost" — none of those three axes is defined anywhere, and "cost" has no resource to spend.
**Fix:** a `systems/combat.md` fixing targeting paradigm, resource model, GCD, TTK bands, and the threat contract before another word of Arts design is written.

### 3. [MISSING] CRITICAL — No minute-to-minute core loop
Nothing describes what a player *does* for five minutes. "Discovery is gameplay" is a statement of intent, not a loop. No verb list, no interaction grammar, no timings.
**Fix:** write the 30-second loop, the 10-minute loop, and the 2-hour session shape, with the actual button presses.

### 4. [MISSING] CRITICAL — No death, failure, or penalty rules — and the lore has already answered a question nobody asked
Zero occurrences of death, respawn, corpse recovery, durability, or any failure state. Simultaneously, the locked entry is a **teleportation altar in a Church of Summoning**, and the altar has an undefined verb `attune`.
**Why it matters:** the altar is obviously the respawn anchor, which means the "most important composition in the build" is actually a high-traffic death-recovery hub, and the emotional brief ("nothing here is threatening") is being written for a room players will most often see after losing.
**Fix:** a `systems/death.md` stating penalty, recovery location, and whether the altar network is the respawn graph — then re-review the arrival frame against that reality.

### 5. [MISSING] CRITICAL — "MMO scale" is asserted and never defined
BUILD_DIRECTIVE §7: "the town must hold up with players in it" — but the budget allocates **zero line items for other players.** No concurrency target, no per-zone cap, no sharding/layering policy, no character LOD budget, no crowd strategy. A starting town in a shipped MMO holds 100–300 visible players — 100–300 skinned meshes at 2–4 draw calls each, more than a third of the entire draw budget, unbudgeted.
**Fix:** state the concurrency target, reserve the budget now, and re-run the perf gate with a synthetic crowd.

### 6. [MISSING] CRITICAL — No character pipeline, in an anime MMO
D-012 deleted the townsfolk and skin/hair materials outright. D-069 then asserts, as the justification for the camera policy, "**in an MMO, seeing your character is the game.**" The named look anchors are character-forward games. There is no design, budget, schedule, or owner for character creation, customization, rigs, animation, or armor visualization — and armor visualization retroactively constrains the crafting economy, the all-procedural art pipeline, and the perf budget.
**Fix:** a decision entry that either commits to a character pipeline with a budget and art bar, or states explicitly that this project ships environments only.

### 7. [WRONG] CRITICAL — The arrival frame is composed for exactly one viewer, and will never be seen that way
§7.1 specifies the arrival to five significant figures, machine-proved. The player stands on a **0.90 m dais** inside a single-spawn church that is the entry point for every player on the server.
**Why it matters:** the composition the east half of the town was arranged to serve will, in practice, be occluded by a pile of other players' avatars and nameplates — the single most reliable outcome in MMO design. The Bree-land stone-circle problem, the Northshire problem, and the Limsa aetheryte problem, all at once.
**Fix:** design the arrival as a solo-instanced sequence that hands off to the shared world, or move the shared spawn off the hero frame.

### 8. [MISSING] CRITICAL — No economy design; the only economy that exists is broken by design
No economy document. What exists is data: a starting purse of 250 copper; a loaf at 3; a cloak at 78. **No faucet** (no documented way to earn a copper), **no sink**, no player trade, and no restock rule — `sim.js:109` decrements stock permanently, so in a shared world the bakery's 24 loaves are gone forever, on day one, to whoever logs in first.
**Fix:** a `systems/economy.md` with faucets, sinks, restock semantics, and a decision on player trade — before more prices are authored.

### 9. [MISSING] CRITICAL — There is no quest content, and the docs call the quest board the most important thing in town
The guild's quest board — "the single most important interactable in the town" — is `"notices": []`. The only reference to content beyond the walls is the phrase "the quest zones."
**Why it matters:** "quest zones" is a placeholder noun doing the work of an entire content design, and it contradicts `design-rules.md` ("avoid disposable content") — a zone whose name is its gameplay function is exactly the checklist design the philosophy bans.
**Fix:** design one quest end to end, and write down what a "quest zone" is in Evermore's vocabulary, or stop using the phrase in locked documents.

### 10. [WRONG] MAJOR — Free Discipline switching plus permanent global unlocks collapses the specialization pillar
`disciplines.md:36` — switching is free. `arts.md:37` — Art-unlocks are permanent and global across Disciplines. The only brake governs *acquisition* rate. At steady state every long-lived character owns every Art of every Discipline — so "specialization" and "personal identity," two of the five pillars, become a temporary property of new accounts. FFXIV survives this only because per-job level and gear are *not* shared; this design deliberately shares everything.
**Fix:** pick the brake and state it — equip-slot budget, non-transferring mastery, or a switching cost.

### 11. [WRONG] MAJOR — First-discovery prestige is a one-winner-per-server reward carrying a core pillar
First discovery is claimed within hours by the most optimized guild, and **every subsequent player is structurally excluded from the game's headline reward forever.** It also incentivizes discovery-camping and information-hiding — which `knowledge-economy.md` says is what you want to avoid. The docs never say what the millionth player gets.
**Fix:** tiered recognition (first-on-server / first-in-guild / personal-first / seasonal), with the *repeatable* recognition carrying the pillar.

### 12. [WRONG] MAJOR — The town being built cannot host the systems the design tree promises
Interiors are visible-through-door only; upper storeys sealed; NPCs deleted. Against that: `professions.md` needs crafting stations, the inn has a `rest_point`, the guild a quest board, six counters have `vendor` components. Every interaction the systems documents assume terminates at a sealed door with nobody behind it. The blacksmith — "the most *active* venue" — is an open shed with a live forge and no smith.
**Fix:** decide now whether venues are enterable, because the answer changes footprints, collision, portals, and the budget. Retrofitting walkable interiors into 94 authored masses is a rebuild, not a pass.

### 13. [COHESION] MAJOR — The locked arrival composition still requires the NPCs the owner deleted
`TOWN_PLAN.md` §7.1 row 3: "carts, a dog, someone with a yoke." `WORLD_BIBLE.md:140`: "Ford Road crossing the view with traffic on it"; `:228`: "adventurers loitering." D-012 struck the NPC clause and stated movement "now has to come from cloth, smoke, fire, water and vegetation" — but the higher-precedence documents still instruct builders to place people a decision deleted.
**Fix:** regenerate §7.1 row 3 and the two World Bible clauses to name the actual motion sources, or reopen D-012.

### 14. [COHESION] MAJOR — Hearthmere's registration in the world register is stale and omits the spawn point
`docs/world/arkadion.md:48` lists Hearthmere's venues — **the Church of Summoning is not in the list**, nor the quay, moot hall, watermill, wall, or gates; the register still describes the town in v1 terms.
**Fix:** generate the haven entries from the area's own plan data so drift is structurally impossible.

### 15. [MISSING] MAJOR — No onboarding design; the first hour is undesigned past the first ten seconds
The first two seconds are specified to five significant figures. There is no character creation flow, no tutorial, no UI/HUD spec, no first objective, no teaching sequence for any of the four identity systems.
**Fix:** a beat-by-beat first-hour script with a target minute count per beat, then check the town against it.

### 16. [MISSING] MAJOR — No progression pacing, and "leveling" appears once, undefined
No XP source, no level cap, no pacing, no time-to-first-Art, no zone banding, no endgame statement. "Horizontal as much as vertical" is unbuildable until someone says how much vertical there is.
**Fix:** state the vertical spine and the horizontal budget hung off it.

### 17. [MISSING] MAJOR — No party/grouping design, in a game that assumes the trinity
No group size, no loot rules, no LFG, no player-organization system — and a naming collision: "guild" in this project means a building.
**Fix:** state party size, the loot rule, and the social-organization system; rename one of the two "guilds."

### 18. [MISSING] MAJOR — No monetization stance, and there is already a live pay-to-win hook
Zero mentions of business model. Meanwhile `unlocks-and-discovery.md:29` makes the Art unlock catalyst "craftable or buyable… Wealth can accelerate this final step" — if a cash shop ever exists, the headline progression system is directly purchasable.
**Fix:** a one-page monetization stance, and an explicit "Art catalysts are never sold for real currency" line if that is the intent.

### 19. [UNCLEAR] MAJOR — Mastery's "contextual and milestone use, never raw repetition" is not buildable as written
Four example contexts, three example milestones, no enumeration, no thresholds, no anti-abuse rule. Two designers build different games from this; the one that ships under deadline is the achievement checklist the philosophy bans. "Clutch situations" is a feeling, not a predicate.
**Fix:** enumerate the context predicates and milestone template, set tier thresholds, state the abuse cases you accept.

### 20. [UNCLEAR] MAJOR — The Art × Skill matrix has no dimensions and no cost model
"Every Skill contains every lens" is a multiplicative content commitment: 8 Disciplines × 4 Arts × 120 Skills = 3,840 authored variants with VFX, animation, audio, balance. Nobody has written the multiplication down.
**Fix:** put the numbers in the document, multiply, and compare against actual authoring capacity.

### 21. [UNCLEAR] MAJOR — "No readable lettering anywhere in the world" versus a game whose pillar is written knowledge
The art rule is correct — but the design tree never states the corollary, that every knowledge artifact (quest notices, cartography, archives) is a UI surface, and there is no UI design at all.
**Fix:** a UI/diegetic-text policy stating which knowledge artifacts are world geometry (pictorial) and which are UI, plus a first-pass map/journal spec.

### 22. [MISSING] MAJOR — The playable world is 0.037 km², and there is no world plan
`arkadion.md` names Haven I, Haven II, Haven X — implying at least ten settlements — and designs none. No design exists for what a route, cave, or dungeon *is*. At MMO run speed the entire current world crosses corner to corner in ~45 seconds, against a pillar that the world "cannot be exhausted."
**Fix:** a world plan with zone count, size bands, travel times, and per-area authoring cost derived from what Hearthmere actually took.

### 23. [WRONG] MINOR — A production convenience has silently become world law
The rig is locked to 09:30 with night deferred — but stalls have `"hours": [7, 17]`, `world-events.md` promises seasonal change, and a permanently-09:30 world is a diorama by definition. The day/night decision retroactively constrains baked AO and every emissive budget.
**Fix:** state the day-length and weather commitment now as a *design* decision, even if implementation stays deferred.

### 24. [MISSING] MINOR — No PvP stance whatsoever
In a game with first-discovery races and a knowledge economy, the PvP decision determines whether discovery-camping and world-first griefing are possible. "No open-world PvP" is a complete and sufficient answer, but it has to be written.

---

## The first hour, reconstructed from the documents alone

**What the docs actually specify — 0:00 to 0:12 (seconds):**

The player materializes at `(43.0, 3.30, −0.5)` on the 0.90 m summoning-altar dais, feet 2.40 m above the market place, facing 270° down the nave. Light shafts fall from the clerestory; the stone floor is worn into a visible path from the dais to the west door. Through a 6.4 m portal, in one composition: the perron, Kirk Green, Ford Road crossing at 19–37 m, the **Heron Fountain at 43.0 m dead centre**, the market cross at 49.7 m, the moot hall's bell-cote at 53.9 m frame-left, the **Adventurer's Guild tower at 71.6 m** with crimson banners, the Grey Heron Inn's jettied gables at 72.2 m frame-right. Sun behind at 09:30, so every facade is lit. The player is told without a word of HUD: there is a way down, a way forward, a place to go, somebody to ask, somewhere to sleep.

**This is the best-specified twelve seconds I have ever read in a design document.** Then it stops.

**What can be reconstructed after that — 0:12 to roughly 0:04:00:**

Walk down the nave. Out the door, down the perron, across Kirk Green, 43 m to the fountain. Look at 14 market stalls whose vendor components carry a trade and hours but **no stock and no prices**. Reach the guild and open the quest board: `notices: []`. Walk to the inn door, which restores "stamina" and "health," neither defined anywhere. Buy a loaf for 3 of your 250 copper with no inventory UI and nothing to use it on. Walk to the south gate and look at the road climbing away to the quest zones, which do not exist. The world is 192 m across; at MMO run speed you have now seen all of it.

**Estimated real first-hour content: about four minutes.**

### Every question the documents cannot answer

**Identity and entry**
1. Who is the player, and what is a "summoned" person in Arkadion's fiction?
2. Does the town know summonings happen? Is the Church of Summoning famous, routine, or feared?
3. Is there character creation? Before or after the spawn? Where?
4. What does the player look like? Species, body, customization? Is there an avatar mesh at all?
5. Does the player choose a Discipline, and if so, when, where, and from whom?
6. What is my starting equipment? Do I have a weapon?
7. What does the `attune` verb on the altar do?
8. Is the altar a teleport network node? What is on the other end?

**The world as a shared space**
9. Do I see other players? How many are on this dais right now? Do we collide?
10. Is there chat? Whisper, say, zone, party?
11. Can I group with anyone in the first hour?
12. What is my name, and is it displayed over my head — in a world with no readable lettering?

**Direction and first objective**
13. What is my first objective, and who gives it, in a town with no NPCs and no quest notices?
14. What is on the quest board, and how does it communicate a quest with no readable lettering?
15. What tells me to leave Hearthmere, and where am I supposed to go?
16. What is the retention hook at minute 55 — what makes me log in tomorrow?

**Systems**
17. How do I acquire my first Skill?
18. How do I level a Discipline, and what grants the XP?
19. How do I fight? What are the inputs, and what am I fighting?
20. What is health? What is stamina? What restores them besides standing at a door?
21. How do I start a Profession? The blacksmith is a sealed shed with no smith.
22. Where do I earn my first copper? Can I sell anything to anyone?
23. What is the map, the journal, the HUD? Fog of war is promised; no interface exists.
24. What is my inventory, and how many slots does it have?

**Failure and time**
25. What happens when I die? Do I wake up on this altar?
26. Is there any failure state inside Hearthmere at all?
27. If I log out and back in, do I spawn on the altar again — and does the hero frame play every time?
28. What time is it, and does it ever change? The stalls are open 07:00–17:00 in a world locked at 09:30.

**Scale**
29. What is past ±140 m, and what happens when I walk there?
30. How big is Arkadion, and how many of these towns exist?

---

## Verdict

**Do not sign off as a design foundation. Sign off as an art foundation immediately.**

`PROMPT.md` §1 is honest about what it is — "Build me my perfect MMORPG **art and world**" — and against that brief this project is executing superbly. The gap is that the design tree claims to be a game design bible and is a 799-line pitch deck: eight pillars, four identity systems, and not one number, resource, cooldown, penalty, price, faucet, party size, or minute.

The single most dangerous item is **finding 5 + finding 6 together**: this is being built and perf-gated as a shipping MMO client with no budget line and no pipeline for the thing an MMO is made of — other players' characters. That one gets more expensive every venue you ACCEPT.

Three things before another venue is built: (a) reserve the character/crowd budget and re-run the perf gate with a synthetic crowd; (b) rule on enterable interiors before the remaining ~80 masses are authored; (c) put the design tree into the precedence chain or delete its claim to authority, so the next session knows whether it is building a game or a diorama.
