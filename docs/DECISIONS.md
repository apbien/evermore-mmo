# Decisions

Recorded deviations, and the reasoning. Art Bible changes require an entry here.

---

## D-001 — Engine target: portable glTF assets + WebGL harness

**Context.** Unity and Unreal downloads are blocked by the environment's
network policy (403 at the CDN and at `EpicGames/UnrealEngine`), and available
disk (~30 GB) is below a usable UE5 install regardless. Neither engine could be
installed or run here.

**Decision.** Author the town as engine-neutral **glTF 2.0 + PBR texture sets**,
with a three.js render harness for verification and a UE5 project scaffold that
imports the same assets.

**Why.** The art-director iteration loop the project is built around requires
that agents can *see* their work. Authoring a UE5 project blind would produce
code referencing assets that do not exist, with no way to verify anything looks
right. glTF imports natively into both engines with no transform fixup, so the
expensive part — the assets — stays portable.

**Cost.** The three.js client is a reference implementation, not a shipping
Unreal build. Engine-specific features (Nanite, Lumen, VSM) are unavailable.

---

## D-002 — MMO seams established up front, netcode deferred

**Context.** Scope is visual fidelity first, but the user asked that MMO systems
not require a later rewrite.

**Decision.** Lock four architectural seams now — authoritative JSON content,
stable entity IDs, 16 m spatial cells, and intent-based interactions — while
deferring actual networking. See `docs/ARCHITECTURE.md`.

**Why.** The expensive retrofit is not netcode; it is discovering the world was
built as client-side scenery with no entity identity and no spatial structure.
These four cost little now and are painful to add later.

---

## D-003 — Principal facades face −Z

**Context.** The locked 09:30 sun (azimuth 125°) lights −Z-facing surfaces. The
first render pass viewed assets from +Z and judged every one on its shadowed
back — a warm cream wall measured as blue-grey.

**Decision.** Every venue is authored with its principal facade toward −Z, and
review cameras sit on that side.

**Why.** It matches the town plan (the player arrives through the north gate
and sees −Z faces) and guarantees review renders show lit material.

---

## D-004 — Wrought iron authored below full metalness

**Context.** Physically, iron is a metal (metalness 1.0). At 1.0 the albedo is
ignored and the surface renders purely from environment reflection; under the
software-rasterised environment used here it collapsed to a flat black cutout,
losing all hammer-facet detail.

**Decision.** Author wrought iron at metalness 0.55 with a lifted albedo.

**Why.** Aged iron genuinely carries scale and oxide that scatter diffusely, so
this is defensible physically as well as practically. The form reads in all
lighting. **Revisit** if the project moves to an engine with a stronger IBL —
this is a compensation, and it is the kind of thing that should not silently
persist.

---

## D-005 — World-position wear is not baked into tiling materials

**Context.** `ground_splash` and `water_streak` were applied inside tiling
material builders. Because the texture tiles across a wall, a "bottom 15 cm of
the wall" dirt band repeated at every tile seam.

**Decision.** Tiling materials carry only position-independent wear. Ground
splash and streaking are applied per-vertex at assembly time.

**Status.** The helpers still exist on `MaterialSet` for non-tiling use, but
per-vertex application is **not yet wired through glTF export** (no vertex
colour channel). Listed as a known gap in `docs/ASSET_PIPELINE.md`.
