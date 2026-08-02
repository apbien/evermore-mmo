# Documentation audit — synthesis and triage — round 01

Date: 2026-08-02. Three independent fresh-eyes reviewers (art director, technical
director, lead game designer — reports `docs-audit-{art,tech,design}-01.md`)
audited the documentation with no project context. This file is the triage:
every finding, one disposition. Owner rulings taken 2026-08-02 via direct
questions. Decision record: D-070 (audit), D-071 (arrival), D-072 (crowd
budget), D-073 (interior access), D-074 (design-tree status).

Dispositions:
- **FIX** — remediated in the audit-remediation commits (phase noted).
- **RULED** — owner decision recorded (D-ref).
- **FUTURE** — real, deliberately deferred; owned by the systems-design phase
  (PROMPT.md §6) or a named chip. This section is the canonical backlog.
- **REJECTED** — the finding flags something deliberate; the covering decision
  is cited.

## Art director (docs-audit-art-01.md)

| # | Finding | Disposition |
| --- | --- | --- |
| 1 | Sun NE vs "north faces shadowed" palette | FIX (C: §4 re-keyed, sun vector stated) |
| 2 | Azimuth convention unstated | FIX (C: convention + compass + vector in §4) |
| 3 | No colour management | FIX (C: sRGB declaration; exposure/tonemap/grade intent into §4) |
| 4 | Metals physically impossible | FIX (C: F0 re-author + painted-ironwork row + sanctioned deviation) |
| 5 | No pattern book, no ridge heights | FIX (C: §1 pattern book; schedule ridge column → checker backlog note) |
| 6 | Arrival frame needs banned moving traffic | FIX (D: motion rewritten to static substitutes + sanctioned ambient motion) |
| 7 | REFERENCES.md contains no images | FUTURE (docs/refs/ capture set — needs human-gathered captures) |
| 8 | Rim specified three ways | FIX (C: reconciliation recorded in light entry; open item named) |
| 9 | No water direction | FIX (C: §4 water sub-palette + §5 water standard) |
| 10 | No district colour script | FIX (C: §4 colour script + dominance ratios) |
| 11 | 12 m facade rule broken by schedule, unchecked | FIX (D: breaks notes + checker assertion) |
| 12 | Kirkgate three gradients | FIX (D: prose dedup to generated table) |
| 13 | Wharf lower stage underwater; Fishers' Steps 3-way | FIX (D: levels corrected in plan data) |
| 14 | Prose numbers drift from generated tables | FIX (D: dedup sweep; doc-lint deferred to FUTURE) |
| 15 | Church not tallest despite claim | FIX (D: church spirelet wins, 21.6 m — "the guild came up a tenth short") |
| 16 | Blacksmith wind rationale wrong | FIX (D: rationale restated honestly; soot marked downwind) |
| 17 | Hero/secondary conflict on frame anchors | FIX (D: §7.1/§7.2 anchors auto-promote to hero) |
| 18 | No LOD visual standard; reviews never see LODs | FIX (C: §6 LOD standard + LOD render in review packet) |
| 19 | No emissive/night standard | FIX (C: emissive vs exposure; pub/forge night review condition; day/night committed as design) |
| 20 | No channel policy / per-venue budgets | FIX (C partial: ORM + colour space stated; per-venue allowance in BUILD_DIRECTIVE §7) |
| 21 | No exposure calibration in renders | FIX (C: calibration strip mandatory) |
| 22 | Arrival cone blind to stalls/furniture/vegetation | FIX (D: cone extended to all placed bounding volumes) |
| 23 | Modern scale table vs Tudor vernacular | FIX (C: table split gameplay-minimum / vernacular; pub low beams legal) |
| 24 | Uncalibrated scoring + first-pass bias | FIX (C: anchors noted, Cohesion→conformance, bias sentence deleted) |
| 25 | No signage standard | FIX (C: §1 signage standard) |
| 26 | World Bible stale counts / leat / ASCII map | FIX (D: sweep; ASCII map generation → FUTURE) |
| 27 | "One wrong element" uniformity | FIX (C: becomes ~70% domestic rate, guild exempt) |
| 28 | No wear index; splash band shallow | FIX (C: 0–5 wear index; splash 0.35–0.5 m) |
| 29 | Wind unbound from motion; 4 smoking chimneys | FIX (C: §7 binds ambient.wind; smoke-list generation → FUTURE) |
| 30 | Look locked in non-product renderer | FIX (D partial: harness declared reference in ENGINE_PORTING; parity checklist → FUTURE) |

## Technical director (docs-audit-tech-01.md)

| # | Finding | Disposition |
| --- | --- | --- |
| 1 | Intent seam dead (no Move caller) | FUTURE-CHIP ("Wire the intent seam") |
| 2 | No netcode spec | FUTURE (systems phase: NETCODE.md) |
| 3 | Movement client-authoritative, called exploit-proof | FIX (D: §4 claim corrected) + FUTURE-CHIP (code) |
| 4 | Two world grids (A1–F6 vs A–L 12×12) | FIX (D: ARCHITECTURE §3 cites Directive; schema pattern regenerated) |
| 5 | Schemas enforced by nothing | FIX (D: jsonschema in setup; all three schemas hard-fail) |
| 6 | No persistence design | FUTURE (systems phase) |
| 7 | Budget already blown 58% (baseline 1419 vs 900) | RULED-partial (D-072 restates honestly); budget re-derivation OPEN, owned by build sessions |
| 8 | No character/crowd budget | RULED (D-072: ~100 visible players reserved) |
| 9 | No streaming/memory architecture | FUTURE (systems phase) |
| 10 | extensionsRequired claims false | FIX (D: ARCHITECTURE + ENGINE_PORTING corrected per D-052) |
| 11 | No CI | FUTURE-CHIP ("CI workflow") |
| 12 | Unpinned toolchain vs determinism | FUTURE-CHIP (folded into CI chip: pins + fingerprint) |
| 13 | No schema versioning/migrations; ID uniqueness unenforced | FIX-partial (D: validator D-number + entity-ID uniqueness checks); migrations FUTURE |
| 14 | No security assumptions; unsafe dispatcher | FUTURE (systems phase; dispatcher noted in intent chip) |
| 15 | No audio architecture | FUTURE (systems phase; reverb-field-on-interior noted as cheap-now option) |
| 16 | No character/animation architecture | RULED-partial (D-072 names the pipeline as pending); body metrics already law (Art Bible §3) |
| 17 | cell vs pos coordinate spaces undocumented | FIX (D: ARCHITECTURE §2 space qualifiers; sim key unification → chip) |
| 18 | ASSET_PIPELINE stale gaps; 15% material list | FIX (D: rewritten; list points at manifest) |
| 19 | Mandatory APIs undocumented | FIX (D: venue example covers collider/instance/lod/interior) |
| 20 | Single-source rule violated incl. by its own declaration | FIX (C/D: restatements → citations) |
| 21 | No min spec / platform target | FUTURE (systems phase) |
| 22 | No error/degraded-mode contract | FUTURE (systems phase) |
| 23 | Interest radius self-contradictory | FIX (D: stated once, provisional pending NETCODE.md) |
| 24 | Duplicate decision IDs | CHIP-EXISTS (reconciliation chip) + FIX (D: validator uniqueness check) |

## Lead game designer (docs-audit-design-01.md)

| # | Finding | Disposition |
| --- | --- | --- |
| 1 | Design tree has no authority | RULED (D-074: canon for named systems phase) |
| 2 | No combat design | FUTURE (systems phase, first item) |
| 3 | No core loop | FUTURE (systems phase) |
| 4 | No death/failure rules; altar is the obvious respawn | FUTURE (systems phase); altar-as-anchor acknowledged in D-071 |
| 5 | MMO scale undefined; no crowd budget | RULED (D-072) |
| 6 | No character pipeline | RULED-partial (D-072 names it pending); full pipeline FUTURE |
| 7 | Arrival frame vs spawn crowds | RULED (D-071: solo-instanced first arrival) |
| 8 | No economy; vendor stock exhausts permanently | FUTURE (systems phase; restock semantics named) |
| 9 | No quest content; "quest zones" is a placeholder | FUTURE (systems phase) |
| 10 | Free switching + global unlocks collapses specialization | FUTURE (systems phase — flagged as a known-failure design) |
| 11 | First-discovery one-winner problem | FUTURE (systems phase — tiered recognition proposed) |
| 12 | Town can't host promised systems (sealed interiors) | RULED (D-073: access follows purpose) |
| 13 | Locked composition requires deleted NPCs | FIX (D: motion sources rewritten; same as art #6) |
| 14 | arkadion.md registration stale, omits the church | FIX (D: registration updated; generation → FUTURE) |
| 15 | No onboarding/first-hour design | FUTURE (systems phase — the 30-question list is the spec's outline) |
| 16 | No progression pacing | FUTURE (systems phase) |
| 17 | No party/social design; "guild" name collision | FUTURE (systems phase; naming collision noted) |
| 18 | No monetization stance; live P2W hook in unlocks | FUTURE (systems phase — flagged URGENT-when-relevant) |
| 19 | Mastery not buildable as written | FUTURE (systems phase) |
| 20 | Art × Skill matrix has no dimensions | FUTURE (systems phase) |
| 21 | Lettering ban vs knowledge pillar; no UI policy | FUTURE (systems phase; signage FIX covers the world-side half) |
| 22 | No world plan beyond one town | FUTURE (systems phase; docs/areas pattern is the container) |
| 23 | 09:30 lock became world law | FIX (C: day/night recorded as committed design decision, implementation deferred) |
| 24 | No PvP stance | FUTURE (systems phase — one-paragraph decision) |

## The systems-design phase backlog (canonical)

Owned by PROMPT.md §6's named post-visual phase, governed by the design canon
(D-074). In rough dependency order: core loop · combat (targeting, resources,
GCD, TTK, threat) · death/respawn (altar network) · progression spine ·
economy (faucets/sinks/restock/trade) · first-hour onboarding (the 30
questions in docs-audit-design-01.md are the outline) · party/social + the
guild naming collision · quests and what a "quest zone" is · Mastery
predicates · Arts×Skills cost model · monetization stance + the catalyst
clause · PvP stance · UI/diegetic-text policy · world plan (routes, caves,
dungeons defined) · character/animation pipeline · NETCODE.md · persistence ·
streaming/memory · security/anti-cheat · min spec · error contract · audio
architecture · REFERENCES.md capture set · CI + toolchain pinning.

## What the reviewers agreed is genuinely excellent

Causal town planning ("derived, not decorated"), the machine-proved arrival
composition, the residue doctrine, the roughness rule, honest "known
weaknesses" sections, the determinism rule, the builder/critic separation,
and the rules of evidence. All three called the art foundation sign-off-able;
all three called the same three structural risks before more venues: crowd
budget (now D-072), interior ruling (now D-073), and grid/schema enforcement
(fixed this round).
