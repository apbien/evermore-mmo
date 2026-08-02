# Documentation audit — technical director (fresh eyes) — round 01

Date: 2026-08-02 · Reviewer: independent agent with no project context, briefed
as a veteran MMO technical director. Commissioned by the owner. Preserved
verbatim. Dispositions: `docs-audit-synthesis-01.md`. Decision: D-070.

---

**Headline:** This is the best-written *art* documentation I've seen on a project this size, and it is not yet technical documentation for an MMO. It is technical documentation for a procedural architectural-visualization pipeline with an MMO-shaped comment header. The four "seams" ARCHITECTURE §1 says were paid for up front — authoritative content, stable IDs, spatial cells, intents — are three-quarters unimplemented and one-quarter provably dead. Every finding below is verified against the repo, not inferred.

### 1. [WRONG] CRITICAL — The authoritative seam is dead code, and the docs present it as proven
**Evidence:** `server\src\sim.js:80` (`_onMove`), `:37` (`cellOf`), `:44` (`interestSet`) — grep across the entire repo returns **zero callers** for all three. The only intent call site in the codebase is `client\src\main.js:509`. No `Move` intent is ever sent, so the sim's player position is frozen at `town.playerSpawn.pos` forever, and `_inRange` (`sim.js:71`) compares every interaction against the church altar.
**Why it matters:** ARCHITECTURE §4 sells the whole "pay four small costs now" thesis on this seam working; in fact every interactable more than 2 m from spawn returns `out_of_range` today, and no prover exercises intents at all.
**Fix:** Send a `Move` intent at a fixed cadence, make `check_client.mjs` walk to a distant venue and successfully `Inspect` it, and add "one intent round-trip at range" to the prover list.

### 2. [MISSING] CRITICAL — There is no netcode specification of any kind
**Evidence:** Grep across `docs/` for `tick rate`, `snapshot`, `delta compression`, `reconnect`, `rate limit`, `shard`, `zone server` → **zero hits**. ARCHITECTURE §4 stops at "the server validates and broadcasts."
**Why it matters:** The document set's central claim is that these seams make netcode a drop-in; without a stated tick rate, replication cadence, reliability/ordering model, or reconciliation scheme, nobody can check whether the seams are sufficient — and `LocalTransport` is pure request/response with zero-latency promise resolution, which is not the shape a replicated sim has.
**Fix:** A `docs/NETCODE.md` fixing server tick rate, movement authority, per-component replication cadence, reliability classes, and the target latency envelope.

### 3. [WRONG] CRITICAL — Movement is client-authoritative, and §4 explicitly calls that exploit-proof
**Evidence:** `server\src\sim.js:80-84` — `_onMove` accepts any 3-element array as truth with no speed, terrain, or collision validation. `docs\ARCHITECTURE.md` §4: *"That split is what makes prediction safe to add later without exploits."*
**Why it matters:** This is textbook teleport/speedhack, and it is load-bearing — every other server check derives from a number the client dictates.
**Fix:** Rewrite §4 to state that the server integrates input and owns position, and make `_onMove` reject deltas exceeding `maxSpeed * dt` and positions failing the collision/terrain test.

### 4. [WRONG] CRITICAL — Two documents specify two different world grids
**Evidence:** `docs\ARCHITECTURE.md` §3: *"a grid of 16 m × 16 m cells, labelled `A1`…`F6`"* (6×6 = 96 m). `BUILD_DIRECTIVE.md` §2 (LOCKED): *"12 × 12 cells of 16 m = 192 m × 192 m, Columns `A`–`L`"*. ARCHITECTURE is describing v1's grid, which BUILD_DIRECTIVE §0 says was replaced. The staleness has propagated into `content\schemas\entity.schema.json:16` (`"pattern": "^[A-F][1-6]$"`), which **150 of 259 shipped entities violate**.
**Why it matters:** ARCHITECTURE §3 is the document a network engineer reads to size the interest-management partition, and it is off by 4× in area.
**Fix:** ARCHITECTURE §3 cites BUILD_DIRECTIVE §2 and states no dimensions of its own; regenerate the schema pattern and add entity-schema validation.

### 5. [WRONG] CRITICAL — The content schemas are enforced by nothing
**Evidence:** `tools\validate.py:2011` loads **only** `collision.schema.json`, and only inside a `try: import jsonschema` that degrades to a `warn` when absent. `Makefile:10` installs `numpy Pillow` — never `jsonschema`. `entity.schema.json` and `town.schema.json` are loaded by no tool in the repo.
**Why it matters:** ARCHITECTURE §1's thesis is "the server owns authoritative content in schema'd JSON" — in a clean checkout, *no* schema check runs at all, which is exactly how the grid drift in finding 4 survived 259 entities.
**Fix:** Add `jsonschema` to `make setup`, validate all three schemas, and make a missing validator library a hard failure.

### 6. [MISSING] CRITICAL — No persistence design whatsoever
**Evidence:** The word "persistence" appears exactly once in the doc set, as an adjective. No document names a store, a save shape, write cadence, or what is authored-immutable vs. runtime-mutable. Meanwhile `sim.js:138-139` mutates `e.state.open` directly onto the shared authored content record, and vendor stock is decremented in place.
**Why it matters:** "Which of these 259 entity records is a save-game row and which is a content constant" determines whether a content hotfix wipes player state — unanswered while content is authored at volume.
**Fix:** A persistence section defining the player record, the world-delta record, the rule that `content/` is immutable at runtime, and content-version reconciliation with live saves.

### 7. [WRONG] CRITICAL — The performance budget is presented as the standard and is already blown 58%
**Evidence:** ARCHITECTURE §5 and BUILD_DIRECTIVE §7 both state `Draw calls < 900`. `review\perf-baseline.json` records `"drawCalls": 1419`, `"peakDrawCalls": 5066`, with `townhouse: 775` and `landscape: 603`. The gate does raise OVER BUDGET — the gate is honest; the documents are not. The budget's `16.6 ms` row is measured by nothing: `client\src\perf.js:50` defines draws/tris/textureBytes only.
**Why it matters:** A budget the recorded baseline exceeds is not a budget, and PROMPT §8's "town.mjs exits clean" definition-of-done box cannot currently be ticked.
**Fix:** Either re-derive the budget from measured hardware and record it, or treat 900 as a blocking gate; add real frame-time and VRAM instrumentation.

### 8. [MISSING] CRITICAL — Zero budget is reserved for players, characters, UI, or VFX
**Evidence:** BUILD_DIRECTIVE §7: *"the town must hold up with players in it"* — yet every number was measured on an empty town with a capsule avatar.
**Why it matters:** A market square in an MMO holds 60–150 skinned characters with nameplates, none of it in the 900/3.5 M envelope; discovering the world consumed the entire budget after 90 buildings are authored is the most expensive late discovery.
**Fix:** Split the budget world / characters / UI / effects with a stated concurrency target, and re-gate the town against the world share only.

### 9. [MISSING] CRITICAL — No streaming or memory architecture; the client loads the entire town at boot
**Evidence:** `client\src\main.js:370` — `for (const v of town.venues) await loadVenue(v);` with no unload path, no residency budget. `assets/meshes` measures **240 MB** for a single 192 m town.
**Why it matters:** The cell grid is advertised as the streaming unit "now," but nothing streams — and 240 MB per 192 m extrapolates to an unshippable world before the second zone exists.
**Fix:** State a per-cell residency budget and a load/evict contract keyed to the cell grid; one venue proves the round-trip before authoring continues.

### 10. [WRONG] MAJOR — Both porting claims about glTF extensions are false
**Evidence:** ARCHITECTURE §5: *"never listed in `extensionsRequired`."* ENGINE_PORTING "Known gaps": quantisation *"none of them is done."* Actual: `core\gltf.py:32` — `REQUIRED_EXTENSIONS = {"KHR_mesh_quantization", "KHR_texture_transform"}`, both written into `extensionsRequired` per D-052.
**Why it matters:** `KHR_texture_transform` is precisely where UE5 Interchange and Unity glTFast historically disagree, and the UE5 import recipe mentions neither — the "port is free" claim rests on an assumption its own doc now contradicts.
**Fix:** Document the two required extensions, name tested importer versions, and round-trip one real venue into UE5.

### 11. [MISSING] MAJOR — No build, CI, or release pipeline exists
**Evidence:** No `.github/`. `package.json` has no `test`/`build`. `tools\test_batching.py` and `tools\test_visibility.mjs` are run by nothing. `tools\determinism.py` is cited in `.gitignore` as the gate that makes untracking `assets/` safe, and appears in no target and no CI.
**Why it matters:** Every gate depends on a human remembering to run it, on one Windows machine, with recovery via OneDrive zips.
**Fix:** CI running validate, walkable, playable, determinism, and both test files on every PR, publishing a hashed asset bundle.

### 12. [RISK] MAJOR — Determinism, the claim everything rests on, has an unpinned toolchain
**Evidence:** ARCHITECTURE §7: *"byte-identical assets on any machine."* `Makefile:10`: `pip3 install numpy Pillow` — no versions, no Python constraint.
**Why it matters:** `assets/` is untracked (D-067), so regeneration is the *only* copy of 240 MB of art; numpy RNG streams and Pillow resampling change across minor versions — a routine `pip install` can silently invalidate every baseline.
**Fix:** Pin Python, numpy and Pillow exactly; `determinism.py` asserts a toolchain fingerprint.

### 13. [MISSING] MAJOR — No asset versioning or content migration, despite the doc claiming there is
**Evidence:** ARCHITECTURE §6: *"Schema changes are versioned."* Actual: two of three schemas have no version field; no migration code exists; the "never recycled" ID guarantee is enforced only by a client-side `console.warn`.
**Why it matters:** Once a live server persists state keyed on these IDs, an un-versioned schema change and un-enforced ID uniqueness are the two ways player data corrupts.
**Fix:** `schemaVersion` on every authored document, a migrations directory, and a build-time global ID-uniqueness check that fails the build.

### 14. [MISSING] MAJOR — No security or anti-cheat assumptions, and the intent dispatcher is unsafe
**Evidence:** Zero doc hits for authentication, session, anti-cheat, rate limiting. `server\src\sim.js:62`: `const fn = this['_on' + type];` — dynamic dispatch on a client-supplied string, no allowlist, no payload validation, no rate limit.
**Why it matters:** The trust boundary is the one thing an MMO architecture document exists to define, and this one defines it as "the client sends a method name."
**Fix:** Explicit handler table, per-payload schema validation, stated per-connection rate limit.

### 15. [MISSING] MAJOR — No audio architecture at all
**Evidence:** Zero occurrences of "audio"/"sound" in the doc set. The entity component vocabulary has `light`, `smoke`, `steam` — no emitter, no acoustic class; `ctx.interior` declares occlusion volumes with no acoustic meaning.
**Why it matters:** Emitter placement and reverb zones are authored data; retrofitting them across 90 buildings is a second full content pass — the class of cost ARCHITECTURE §1 was written to avoid.
**Fix:** Decide whether emitters are entity components or a parallel layer, and add a reverb-volume field to `ctx.interior` while only one interior exists.

### 16. [MISSING] MAJOR — No animation or character architecture, and the conventions it would constrain are already locked
**Evidence:** ENGINE_PORTING "Known gaps": *"No skeletal meshes or animation — the player is a placeholder capsule."* No skeleton spec, no rig conventions, no animation budget.
**Why it matters:** Character metrics determine doorway clearances, stair rise, ceiling heights and interaction ranges — all being authored into 90 buildings right now against a capsule.
**Fix:** Lock the skeleton, eye height, capsule radius and step height as a one-page spec now, even though no character ships in v2.

### 17. [UNCLEAR] MAJOR — Entity `cell` and `transform.pos` are in different coordinate spaces and no document says so
**Evidence:** `content\entities\church.json`: `"cell": "I6"` with venue-local `"pos"`; ARCHITECTURE §2's canonical example shows them side by side with no space qualifier; `sim.js:37` recomputes with a *third* key format (`"cx,cz"` numeric).
**Why it matters:** Two engineers will build incompatible interest management from the same example.
**Fix:** State in §2 that `transform` is venue-local and `cell` world-derived; unify the sim's cell key; add a validator recomputing `cell` from placed position.

### 18. [WRONG] MAJOR — ASSET_PIPELINE's "Known gaps" section is stale in all five bullets, and its material list is 15% complete
**Evidence:** Claims no LOD generation, no AO bake, no collision, no vertex-colour export, no atlasing — all five now exist. The "Available:" material list names 16 keys — `materials.LIBRARY` has **110**.
**Why it matters:** This is the document a new venue author reads to learn what core provides; a stale gap list actively causes the divergent reimplementation BUILD_DIRECTIVE §6.7 bans.
**Fix:** Generate the material list and capability table from the code (the manifest already exists).

### 19. [MISSING] MAJOR — ASSET_PIPELINE never documents collision, instancing, LOD, or interiors — the four APIs the Directive makes mandatory
**Evidence:** "Writing a venue module" shows only `ctx.emit` and `ctx.entity`. Absent: `ctx.collider*`, `ctx.instance`, `ctx.lod`, `ctx.interior`. `review\validate.txt` reports **17 placed venues with no collision file**, and the build merely prints a warning and exits zero.
**Why it matters:** The rule is law in one document and omitted from the only document that shows how to obey it.
**Fix:** Show a complete venue example; promote missing-collision to a build failure.

### 20. [WRONG] MAJOR — The "single source" rule is violated by three documents, including by the document that declares it
**Evidence:** ARCHITECTURE §5 camera: *"none may restate its numbers"* — restated at `CLAUDE.md:56`, `ASSET_PIPELINE.md:49`, BUILD_DIRECTIVE §8. The perf table is copied verbatim into BUILD_DIRECTIVE §7.
**Why it matters:** Finding 4 is that prophecy already fulfilled; four copies of the camera rig means the next tuning pass leaves three wrong.
**Fix:** Replace restatements with citations; add a doc-lint for governed numbers outside their owning section.

### 21. [MISSING] MAJOR — No client platform target, minimum spec, or download budget
**Evidence:** Only *"1080p, mid-range GPU, 60 fps"*. No browser matrix, no WebGL2/WebGPU decision, no VRAM floor, no first-play download ceiling — while the client ships GTAO + TAA + bloom over 240 MB of meshes and the Low tier is explicitly untuned.
**Fix:** Name the min spec, browser matrix, and download budget; measure the Low tier on real hardware.

### 22. [MISSING] MAJOR — No error, crash, or degraded-mode contract
**Evidence:** Every failure path in `client\src\main.js` is `console.warn` and continue — missing venue mesh, missing collision, duplicate entity ID, missing lighting. A town with zero collision boots, looks correct, and lets the player walk through every wall.
**Why it matters:** The quality bar is entirely visual, so the one failure class it cannot see — silently degraded data — is the one the client is engineered to hide.
**Fix:** Classify failures fatal / degrade-with-telemetry / dev-only; missing collision is fatal in a shipping build.

### 23. [UNCLEAR] MAJOR — Interest-management radius is self-contradictory in a single paragraph, and diverges from the draw distance
**Evidence:** ARCHITECTURE §3: *"its own cell plus the 8 neighbours"* (3×3) justified by *"a 3-cell radius (48 m)"* (7×7). LOD3 draws to 100 m.
**Why it matters:** Two engineers build different subscription sets; either way, the player draws buildings at 100 m whose entities are not replicated.
**Fix:** State the radius once in cells *and* metres, reconciled against the LOD3 cull distance.

### 24. [WRONG] MINOR — Decision IDs, cited as authority across the doc set, are not unique
**Evidence:** `docs\DECISIONS.md` contains five duplicated IDs — D-025, D-026, D-038, D-040, D-050. A citation to D-050 is now ambiguous.
**Why it matters:** DECISIONS.md is the arbitration record all doc/reality disagreements route into; an ambiguous key makes it unciteable.
**Fix:** Renumber the collisions; add a validate.py check that D-numbers are unique and every citation resolves.

---

## The sign-off

**I cannot sign these off as MMO foundations.** I would sign them off as *world-building* foundations, which is what they actually are and what they are excellent at — the art bible, the review protocol, the determinism rule, and the machine-prover culture are better discipline than most shipped projects have.

The corner this paints you into: ARCHITECTURE.md is written as a promise that the expensive retrofit has been pre-paid. Findings 1, 3, 4, and 17 show it has not been. Meanwhile 240 MB of content is being authored on top of that promise. Every venue authored before findings 4, 8, 9 and 17 are resolved is a venue that will be re-touched.

**Three things before another venue is built:** (a) make the seams executable and prove them — one `Move` intent and one interaction at 60 m; (b) reconcile the grid across ARCHITECTURE, the entity schema, and `sim.js`, enforced in `validate.py`; (c) split the perf budget to reserve a character share. Everything else can be written down while building continues.
