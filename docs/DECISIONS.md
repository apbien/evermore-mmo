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

---

## D-006 — Plaza paving is a tiling surface plus scattered proud stones

**Context.** `docs/ART_BIBLE.md` and the market-square brief called for real
per-stone cobble geometry, on the reasoning that a flat textured plane reads as
wallpaper at grazing angles. That is true, but it does not survive contact with
the budget: a 34x32 m plaza at 0.17 m spacing is ~40,000 stones, and at 44 tris
per chamfered stone that is **1.35 M triangles for the paving alone** — against
a 3.5 M budget for the entire frame (Art Bible §6). The first market-square
build did exactly this and consumed the whole frame budget with one venue.

**Decision.** Carry the cobble read in the tiling material, and scatter a few
hundred *proud* stones — tilted, frost-heaved, sunken — where they matter for
silhouette: the fountain surround, kerb edges, and desire paths. ~20 k tris.

**Why.** This is what shipped titles do; nobody models every cobble. The proud
stones supply the grazing-angle silhouette that a bare plane lacks, which was
the legitimate part of the original concern.

**Cost, stated honestly.** At distance the paving still reads flatter than the
Art Bible wants — the normal map mips away and the albedo variance is doing
most of the work (strengthened in D-007). The real fixes are a detail/decal
layer near the camera and per-vertex wear, neither of which is built. This is
a known shortfall, not a solved problem.

---

## D-007 — Cobble albedo carries per-stone variance

**Context.** With paving reduced to a tiling surface, the street read as flat
grey mud past a few metres. Normal-map detail mips away with distance, so it
cannot be what makes a cobbled street legible.

**Decision.** Drive stone-to-stone colour variance from the Worley cell id
rather than smooth noise, so each stone gets its own value and hue rather than
a blur across stones.

**Status.** Improves the near and mid field. The far field is still weaker than
the reference targets in `docs/REFERENCES.md`.

---

## D-008 — Hearthmere is Haven I; design bible updated to match

**Context.** The design bible defines the game as **Evermore**, the
world as **Arkadion**, and settlements as **Havens** with a numerical
designation plus a historical name. Its example register listed
`Haven I: Hearth`. This branch had already been built naming the first town
**Hearthmere**, with entity IDs prefixed `hm.*`.

**Decision.** Keep **Hearthmere** and register it as **Haven I** in the design
bible, replacing the placeholder `Hearth`. Entity IDs stay `hm.*`.

**Why.** The conflict was naming only — the design bible specifies no art
direction, engine, or starting-town detail, so the Art Bible and World Bible
fill a genuine gap rather than contradicting canon. Hearthmere also already
satisfies the canonical naming structure once paired with its numeral, and
`docs/ARCHITECTURE.md` §2 commits to entity IDs never being recycled, so
preserving `hm.*` avoids a rewrite for no functional gain.

**Cost.** The design bible is edited on this branch, so if it is maintained
elsewhere the change needs reconciling with its owner rather than silently
diverging.

**Follow-up.** This is exactly what happened. `main` subsequently restructured
`docs/GAME_DESIGN.md` into a `docs/world/` + `docs/systems/` tree, and because
the restructure was a delete-and-rewrite rather than an edit, git merged both
sides cleanly and the Haven register silently reverted to the placeholder
`Haven I: Hearth`. Re-applied to `docs/world/arkadion.md`, which is now the
canonical location. Worth noting the failure mode: a clean merge is not
evidence that a semantic change survived.


---

## D-009 — The locked lighting rig lives in content, not in the renderers

**Context.** A cohesion review found that `docs/ART_BIBLE.md` §4 specified one
rig, `tools/render/viewer.html` and `client/src/main.js` both hardcoded a
*different* one, and `content/town/hearthmere.json`'s `lighting` block — the
authored copy — had no consumer at all.

Worse, `viewer.html` declared the §4-correct constants near the top under a
comment citing the Art Bible and then never used them. Dead values that make a
file pass inspection are worse than no values.

The consequence is blunt: **§8's "reviewed at the locked 09:30 lighting" had
never been true for any asset in this repo.** Every sign-off to date was made
under an undocumented rig.

**Decision.** `content/town/hearthmere.json.lighting` is the single
authoritative copy; both renderers read it at startup. The Art Bible documents
the values and points at the file.

**Which values won, and why the SPEC moved rather than the rigs.** The values
in the renderers do fix two real defects — shadowed facades reading blue-grey
(the PMREM environment and the hemisphere light double-counting sky) and
cast-shadow regions crushing to near-black — both of which were measured at the
time. Reverting to the §4 numbers would reintroduce them, so the spec was
corrected to match and the two undeclared fills were written into the table.

**Provenance corrected.** An earlier version of this entry said the renderer
values were "deliberately tuned" after the spec was set. A reviewer checked the
history and that is not what happened: `git show ac718cf` shows `ART_BIBLE.md`
and `viewer.html` authored in the SAME foundation commit carrying different
numbers, and `git log -L` shows the rig untouched from then until `2cb6b67`.
The tuning happened inside the foundation working session, before anything was
committed, and the Art Bible was simply never updated to match. So this was not
drift away from a spec — the spec and the implementation **never agreed at any
point in the repository's history**, which is worse, and is why nothing ever
flagged it.

**Still open.** The rim light ships at 1.15 against §1's 1.4, and §1 calls rim
the single strongest anime-3D signature. That value was inherited, not chosen,
and should be re-tested on its merits rather than grandfathered by this entry.

**The generalisable failure.** This is the same shape as `streets[]`: data
authored in `content/`, no consumer, and nothing detects it. Both were found by
review rather than by tooling. A check that flags authored blocks in
`content/` with no reader would have caught both.


---

## D-010 — The rim light, and a governance correction

**The governance point first, because it matters more than the value.**

Commit `2cb6b67` changed `ART_BIBLE.md` §4's rim from 1.4 to 1.15 as part of
reconciling the spec to the shipped rig. D-009 justified that reconciliation
with two measured defects — blue-grey shadowed facades and crushed cast
shadows. **Neither of those arguments reaches the rim light at all.**

So the Art Bible — a document whose own header says it is law and that changes
require a recorded decision — had a number altered to close a review finding,
under a rationale that did not cover it. That is the wrong way round: the
finding should have forced an argument about the rim on its merits, or been
left open. Recording it here rather than quietly leaving it.

**The value, argued on its merits.** §1 calls rim "the single strongest
anime-3D signature", and it is. But the implementation is a *directional
light*, which lights every surface facing it, whereas a true rim affects only
grazing angles. On curved geometry the limb is most of the projected face, so a
strongly saturated blue rim drains colour from every lathed object in the town.

Measured on the guild turret against the ashlar wall beside it:

| | saturation | curve/flat ratio |
| --- | --- | --- |
| `#8FB8E8` @ 1.15 | 0.228 vs 0.447 | 0.51 |
| `#A9C6E2` @ 0.85 | 0.260 vs 0.447 | 0.58 |

Desaturating and reducing the rim recovers curved-surface colour without
touching flat surfaces. **Partial, not solved** — the ratio should be near
1.0, and it is 0.58. The real fix is a shader-side Fresnel term so the rim only
appears at grazing angles, which is a renderer change rather than a value
change and is not done.

**Note on provenance.** This was originally diagnosed as a `M.lathe` UV bug.
That fix (arc-length UVs) was correct on its own terms and is kept, but it was
not the cause: the terracotta turret cap is also a lathe and measures 0.477.
The lathe is exonerated; the rim was always the culprit.
