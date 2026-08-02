# Wall, market place, placement, bridge — build report

Scope: `ad-town-04.md` §7 (the wall does not appear in the silhouette), §13 (the
market place carries no residue), §11/§12 (two placement defects and the bridge
camera). Everything below was rendered at the locked 09:30 rig and **read as a
PNG**; where I did not see it, I say so.

Shots: `review/shots/wall-market/` (`town-silhouette`, `town-approach-s/ne/w`,
`town-aerial-ne/nw/sw/se`, `town-square`, `town-arrival`, `town-gate-north/south`,
**`town-bridge`** — new), plus `tower-crane/`, `tower-far/`, `mkt/`, `inn/`, and
crops in `crop/`.

---

## The one-paragraph verdict

**The wall now reads as the town's edge from the field and from the air, and it
does it through its towers.** `town-approach-s` is the frame that proves it: the
canonical return camera now shows a continuous curtain of real height with three
capped drums standing along it and the town behind. `town-approach-ne` and
`town-aerial-ne` show the same thing from the water. **In the 400 m orthographic
north elevation the curtain itself is still fused into the mass** — that is
honest and I explain below why it cannot be otherwise while the wall stays
canonically low — but the elevation gained four new vertical events it did not
have in pass 04, and they are all wall towers.
`crop/sil-before-after.png` is pass 04 over today, same crop, same camera.

**And the reason none of last wave's tower work was visible: the tower roofs were
dissolving at distance and the spires were left hanging in the sky.** That is
fixed, and it is the single most important thing in this report.

---

## 1. The wall (ad-town-04 §7, §(b))

### 1.1 What is in the data now

`tools/plan/plan_data.py` → `content/town/hearthmere.json`:

| | pass 04 | now |
| --- | --- | --- |
| `wall.walkHeight` | 5.2 | **6.0** |
| `wall.parapet` | 1.1 | **1.2** |
| tower heights | 8.9 × 9, 11.5 × 2 | **10.6 – 18.4, all eleven individually authored** |
| tower roofs | none (flat-capped) | **7 cone · 2 pyramid · 2 deliberately open** |

The canon is preserved and is the *reason* it works. WORLD_BIBLE says the wall is
a customs boundary, not a defence, so the curtain stays low — **the height comes
from the towers, and the towers are older than the wall** (D-047). Hearthmere had
a burh enclosure with a ring of stone turrets three centuries before it had a
toll boundary; the bank went, the turrets were too expensive to pull down, so the
town strung a low curtain *between* them and re-roofed the ones worth roofing.
Two were never re-roofed and stand open with an ash growing in the crown, which
is what stops eleven cones reading as a kit.

The curtain is no longer one section either. `venues/wall.py::_stretches` runs it
from **2.35 m** (the robbed garden stretch behind the west kitchen gardens, no
parapet, fruit trained on it) to **7.90 m** (the Mere frontage — the customs
face, because everything dutiable arrives by water and the town wanted the boat
to see a wall), with a **6.90 m sandstone stretch on the east that is the wrong
colour and a metre out of line with the crown either side of it**, because thirty
metres went down in a wet winter and was put back in the only stone anyone could
get. Four lean-tos, a woodpile and a fire bucket on the walk are built against
the inner face.

### 1.2 The defect that was hiding all of it

**Every tower roof was floating, or missing, at any distance past ~40 m.**

- `crop/ne-floatcone.png` (`approach-ne`, 140 m): a slate cone hanging ~2.4 m
  above a flat-topped drum, and a second one detached beside it.
- `crop/tower-far.png` (free camera, 180 m): a pyramid roof with its finial
  **alone in the sky with nothing under it at all**.
- `town-aerial-ne` before the fix: **not one of the eleven towers had a roof.**

Cause, and it will catch the next person: `core/venue.py::_levels` decimates
**per material primitive**. In a 32 m wall cell whose `rubble` primitive is thirty
metres of curtain plus one small drum, 6 % of that primitive's triangles is the
curtain and the drum dissolves — while the `slate` primitive in the same cell is
nothing but the spire, so 6 % of *it* is still a recognisable cone. Roof survives,
tower does not.

Fix: the eleven towers are now one authored LOD chain
(`ctx.lod(f"{asset_id}.towers", [towers_all])`), which is the documented escape
for exactly this ("where the automatic simplifier destroys something that has to
survive — a spire"). One chain, not eleven, because eleven authored nodes cost
eleven times two or three primitives at every distance; together the towers are
~20 k triangles and three materials, so as one node they are three draw calls
that never dissolve.

`crop/tower-far2.png` is the same 180 m camera after: every tower carries its cap,
attached, and the wall reads as an enceinte.

### 1.3 Does the silhouette have a hierarchy now?

**Partly, and I will not overclaim it.** `crop/sil-before-after.png`, pass 04 on
top, today underneath, identical crop:

- **New in the profile:** a square pyramid-capped turret clear of the roofline at
  the west end (Tenter, 17.2 m); the Heron angle turret and two capped drums at
  the east end; two more cone tips mid-run. Six vertical events the elevation did
  not have, all of them wall towers, all of them now surviving to LOD3.
- **Still true:** *the curtain does not appear as a base line.* A 6.0 m + 1.2 m
  wall standing on the town's LOW ground (Hearthmere falls 3.75 m south to north,
  so the north curtain is 3.75 m below the datum the houses sit on) cannot clear a
  10–12 m eaves line 40 m behind it, and a 400 m orthographic elevation flattens
  192 m of depth into one plane. Raising the curtain until it *did* read would
  cost the WORLD_BIBLE line the brief said to preserve.

**So the honest answer to "does the silhouette read as a hierarchy" is: the
hierarchy is real in the geometry and it is legible from every camera a player
occupies — it is only the 400 m elevation that flattens it.** The frame that
proves the wall reads is **`town-approach-s`**, not `town-silhouette`: the
canonical return from the quest zones now shows a continuous curtain, three capped
towers along it, and the town standing behind its own wall. `town-approach-ne` and
`town-aerial-ne` show the same from the water.

If the art director wants the curtain in the elevation as well, the cheapest
canon-safe lever left is the **north** towers specifically (Bridgefoot 15.8,
Ferry 12.8, Mill 13.6, Crane 15.2): +3 m each buys the north edge a base line in
the elevation without touching the curtain. I did not do it because the brief said
hierarchy, not height for its own sake, and I would rather the AD make that call
from `crop/sil-before-after.png`.

---

## 2. The market place (ad-town-04 §13, §12)

### 2.1 The lamp is out of the hero frame — third time of asking

`t-square`'s lamp standard has bisected the frame and cropped the fountain through
**three consecutive rejections** (pass 02, pass 03, ad-town-04 §12), and
ad-town-04 also recorded the instrument consequence: `valueBands` for that view
came back `None` because the lamp filled the whole foreground band.

It is gone. `venues/streets.py` now carries a `KEEP_CLEAR` list of world discs on
which no street furniture may stand, with one entry: **the market place's worn
diagonal**, the north-west crossing to the fountain. That is not a camera dodge —
it is what WORLD_BIBLE already says the plaza is (*cobbles worn into desire
paths, polished smooth along the diagonal everyone actually walks*), and
`market_square.py::_paving` already polishes the stones along that line. A market
square keeps its crossing clear. The furniture sequencer works in street space and
cannot see a plaza diagonal, so the plaza states it.

**Frame: `town-square`.** The fountain is unobstructed for the first time.

### 2.2 The residue budget is no longer inverted

ad-town-04 §13: *`sty-walk-03` — a back alley — is the best-dressed frame in the
build and it is the least important street in the town.*

The residue this venue already had was real but **all of it was at +z, in the
upper market behind the fountain**. Both hero cameras read the *lower* market —
`square` stands at the north-west corner, the arrival aperture looks in from the
east — and that half was bare paving. `_dress_lower_market()` is that half,
dressed as what TOWN_PLAN says it is (*fish and greens, north, where the wash-down
drains*):

- **Chalk tally on the fountain lip** — WORLD_BIBLE names it exactly (*chalk marks
  on the fountain lip where a trader tallies*). Fourteen strokes with every fifth
  as the gate, plus the chalk set down beside it. Strokes, not letters: Art Bible
  §2 bans readable lettering and a tally never was letters.
- **A greens pitch** — trestle, the day's baskets on it, empties stacked under,
  and 26 stripped outer cabbage leaves greyed rather than `grass_lush` emerald.
- **A fish pitch** — shallow crate stack, salt barrel, an empty on its side, and
  the wet patch that is the whole reason the fish went on the north side.
- **The broken crate nobody has cleared**, half in the gutter at the road mouth,
  with the sweepings piled against it.
- **A handcart tipped on its shafts**, the broom that swept the sweepings, sacks
  and a rope coil staged at the mouth, and **four cart-rut / hoof-worn patches**
  where the paving stops being swept and the carts turn.

**Frames: `mkt/town-walk-02`** (the plaza at eye height — baskets, stall with
hanging produce, buckets on the paving, weeds in the joints, real setts) and
**`town-arrival`**, where crates, barrels and awninged stalls are now visible
inside the aperture at 43 m. Pass 04's *"the market place is empty"* is closed.

**One thing I got wrong and then fixed, recorded because the render caught it:**
the first placement put the greens trestle at (−8.6, −6.9), **3.3 m from the
`square` lens** — I had replaced a lamp bisecting the hero frame with a table
doing it. Both pitches now sit in the 10–16 m band and the near ground stays
swept. The comment in `_dress_lower_market` says so, so nobody re-does it.

### 2.3 What `town-square` still is, said plainly

**It is a good frame with an empty right-hand two-thirds.** The lamp is gone and
the fountain is clear, the setts are real per-stone geometry with a gutter and a
polished desire path through them, the figure has a contact shadow, and the greens
pitch reads in the mid-ground at frame-left. But this camera stands 9.9 m from the
fountain on the diagonal, so the fountain occludes the whole far half and the near
half has to stay swept — there is genuinely not much room to dress *inside this
frame*, and I would rather say that than fill it with props that make the crossing
look like a junk yard.

**The frame that shows the market place working is `mkt/town-walk-02`**, at the
north mouth looking south. If the AD wants `t-square` itself to carry the trade,
the lever is the camera, not more objects: from the plaza's *north* mouth at
(0, −14) looking south the fountain, both pitches, the moot hall arcade and the
stalls are all in one composition, and the near ground is the cart-worn mouth
rather than 10 m of swept paving.

### 2.4 What the square still fails on

Not mine, but they are in these frames and they are what stops it:

- The **falling water is still flat pale ribbons** and the basin is a flat teal
  disc (`mkt/town-walk-02`). The town is composed around this object.
- **Hard-edged green quads on the fountain kerb and basin floor** — ad-town-04 §14
  verbatim, still on screen.
- Everything past ~25 m is still one flat cream value in `town-arrival`.

---

## 3. The two placement defects (ad-town-04 §11)

Both were authored in `plan_data.py` by a previous, interrupted run of this task
and **had never been regenerated**, so neither had reached the shipped file.

- **Slot 07 chophouse** moved from centre (−21.5, −33.0) to **(−21.3, −38.0)**,
  footprint 10.0 → 9.4. Its south face is now at z **−33.30**; the Grey Heron's
  north-east corner is at z −34.0, so the overlap with the inn's street elevation
  is **0.7 m, not 4.4 m of 7.4 m**. The plaza's north mouth opens 5 m at the same
  time, which is what WORLD_BIBLE says the market place does where the road enters.
- **Slot 15 song school** turned 180° → **0°**, so its back is against the
  churchyard's north wall and its door is on the lane behind the rope house.
  `church.parapet` retains a terrace 2.40 m above that ground and stood 1.27 m in
  front of the old south-facing door; a building that is *against* a wall has its
  back to it, not its face.

Verified in `content/town/hearthmere.json`: slot 07 polygon
`[[-16.6,-33.3],[-26.0,-33.3],[-26.0,-42.7],[-16.6,-42.7]]`, slot 15
`rotationDeg 0`. **I did not get a clean render of the inn's elevation from the
market place** — the two attempts I made either put the camera inside a mass or
hit the render outage described in §5 — so the chophouse fix is verified in the
plan and in the shipped polygons, **not** in a frame. Someone should shoot it.
`check_walkable.mjs` has not been re-run since the regeneration either.

### 3.1 The planner deadlock I had to break to do any of this

`townplan.py::check_siting` compared the plan against **the shipped
`hearthmere.json` before anything was written**. Moving slot 07 five metres made
the shipped file disagree with the plan; the disagreement was a `FAIL`; a `FAIL`
suppressed the write; and the write was the only thing that could have made them
agree. The planner was un-runnable the moment the plan changed — *a check that
forbids the fix for the thing it is checking is a trap, not a check*.

Split out into `check_shipped(slots)`, which runs **after** the write, against
what was actually written. Same two assertions, same 11 mm tolerance, and it still
catches the case it was built for (someone hand-editing the town file), because
the next planner run rewrites and compares. `--check` runs it read-only.
It now reports `shipped: 94 of 94 slot polygons agree with the plan to 11 mm`.

---

## 4. The Emberflow bridge (ad-town-04 §12)

**`bridge` is now a named view** in `tools/render/town.html` and in the default set
in `tools/render/town.mjs`. It stands off the south-west bank at 2.2 m eye, three
quarters on to the crown — the angle that shows the arch series, the cutwaters,
the water under them and the gate beyond in one frame, none of which the on-deck
`spine-walk-01` camera can ever see. That camera takes its Y from
`terrain.height()` and has therefore stood *inside* the deck for four passes while
three separate reports recorded an entirely brown frame and called the bridge a
defect.

**Judgement, from `town-bridge`, read as a PNG:**

**The art director is right — the asset is good.** Three segmental arches with real
voussoirs and keystones, cutwaters with triangular refuges over them, a string
course, a coped parapet, a timber rail on the approach, reeds and a revetment at
the bank, the gate tower and its capped drum closing the frame beyond, and — new
this wave — **a real contact shadow under the 1.75 m figure**. It is one of the
better structures in the build.

**And it is standing over dry land.** The channel under all three arches reads as
olive-green ground, not water: no transparency, no depth gradient, no specular, no
reflection of a three-arch stone bridge in it. `water.surfaceY` is −3.10 and the
bed under the crossing is −5.60, so there are 2.5 m of water there in the data and
**none of it reads as water at a 2.2 m eye in shadow.** This is ad-town-04 §9's
"opaque enamel" seen at the worst possible angle, and it is the single thing
stopping the departure/return frame.

Two more in the same frame: **a large unlit pure-black wedge on the east bank**
where the revetment meets the gate flat (§15's "large black unlit polygons",
unchanged), and the foreground apron at frame-left is still crazy-paving white.

The named camera is the deliverable here. **The bridge is not finished, and now
there is a frame that says why.**

---

## 5. Render outage, and what I could not verify

From ~03:09 another session began editing `client/src/atmosphere.js`,
`client/src/main.js`, `client/src/lod.js` and `client/src/shadows.js`. Two of my
renders died with `SunRig is not defined` and `Unexpected identifier 'lift'` —
the client was mid-edit and would not parse. Everything reported above was
rendered before or between those windows and read as an image; **the inn
elevation in §3 is the one claim I am making from data rather than from a
frame, and I have flagged it as such.**

Also blocking, and fixed on the way past because the build would not complete
otherwise:

- `venues/quay.py` had the last three bare `uv_scale=` floats of the D-046 sweep
  (`stone` at 0.85, `algae` at 0.6), which raised `TypeError` and killed the
  build. They now take the library's authored coverage — which also means the
  quay wall's courses are the same size as `stone` everywhere else in the town.
- `venues/stalls.py::_prism` lays its own UVs with `M._planar_uv`, which takes a
  number and not the "ask the library" sentinel, so every stall sign crashed.
  Resolved once at the top of the builder.

## 6. Numbers

- `townplan.py`: **0 problems**, 94/94 slot polygons agree with the plan to 11 mm.
- `build.py --skip-textures`: all 35 venues build. `wall` 42,860 tris / L0 112
  draws; `market_square` 46,375 tris / L0 30 draws.
- `town.mjs`: **1,419 → 1,050** gameplay draw calls (worst camera `gate-south`),
  by stage `scene 498→680 · shadow 602→124 · ao 258→180 · post 61→66`.
  **Still over the §7 budget of 900** and still not mine to close.
- Triangles 2,896,190 → 2,697,734 on the same camera.
- `validate.py`: **5 failures, 46 warnings.** Four of the five are
  `uv_density.py` (`nogging`, `straw`, `wool_crimson`, `canvas_amber` — the tail
  of somebody else's D-046 sweep). The fifth is **§7 mesh memory at 243.3 MB
  against 240**, which `ad-town-04` already recorded at 239.4 MB and called "not
  a budget, it is a cliff". **It is not the market place**: `market_square.bin`
  is 3.8 MB and `wall.bin` 5.7 MB against `townhouse.bin` **67 MB** and
  `landscape.bin` **26 MB**. I instanced the six market baskets anyway — one
  prototype, six transforms, one Unreal ISM on import — because six copies of a
  2.7 k-triangle woven basket is not something to spend a cliff on.

## 7. What is left, in the order I would take it

1. **The water.** It is what stops `town-bridge`, `town-approach-ne` and every
   aerial. Transparency and a depth gradient before anything else; the shoreline
   noise after.
2. **The chequerboard leaf, and the tree standing in `approach-s`.** Both
   unchanged from pass 04, both in the canonical return camera, both visible in
   `town-approach-s` above.
3. **Shoot the Grey Heron's elevation from the market place** and close §3's one
   unverified claim; re-run `check_walkable.mjs` for `hm.townhouse.door.15`.
4. **The AD's call on the north towers** (§1.3): +3 m on the four north drums
   would put a base line under the town in the 400 m elevation. Data, not
   geometry — one edit in `plan_data.TOWERS`.
5. The black unlit wedge on the bridge's east bank, and the green quads on the
   fountain kerb. Both are single objects with a missing or wrong material.
