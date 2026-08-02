"""The town wall — the thing that makes a group of buildings read as a town.

`content/town/hearthmere.json` has carried `wall{}` since the town was laid
out: a 41-vertex closed polyline, 5.2 m to the walk, seven openings, eleven
towers and five mural stairs. Nothing consumed it. The silhouette showed a
40 m stub of decorative arch on the north road and nothing else, so from any
distance Hearthmere read as a flat band of roofs on open ground.

This module is that missing consumer, and it invents no layout. If the circuit
has to move it moves in the town JSON and this follows.

What the World Bible constrains, and why the wall looks like this
----------------------------------------------------------------
Hearthmere has never been besieged. The wall is a customs boundary, so it is
low, thin, and patched — a boundary that says *pay here*, not *keep out*. That
single fact decides everything below: no machicolation, no crenellated merlons,
a walk carried on corbels rather than won by thickening the wall, gates that
are decorative in the way a prosperous trading town's gates are, and arrow
loops that are older than the wall they now sit in because they were salvaged
out of whatever stood here first.

The one thing that must be right
--------------------------------
**The crown steps.** A wall whose top runs level across falling ground is the
single most common tell of a procedural circuit, and Hearthmere falls 3.75 m
from the south gate to the north and another 1.25 m to the water. So the walk
is quantised to whole courses: the base follows `terrain.height` continuously
and the top holds level for a run and then drops 0.34 m in one riser. Every
run is swept with its own per-station section (`core.mesh.sweep`), so the
riser at a step is a real end cap and not a stretched face.

The north gate and the Emberflow bridge are `venues/gatehouse.py` — they are
the departure frame and get hero treatment on their own venue record. This
module owns the ring, the towers, the walk, the stairs, and the other three
gates and three posterns.
"""

from __future__ import annotations

import json
import math
import os

import numpy as np

from core import batch as B
from core import circuit as CIRC
from core import collision as COL
from core import kit as K
from core import materials as MATS
from core import mesh as M
from core import terrain as TERR
from core import vegetation as VEG
from core.circuit import COURSE, DECK_T, FOUNDATION, Ring, WALK_W
from core.mathx import rng_for
from core.venue import VenueContext

NAME = "wall"
CELLS = []

# Batched on 32 m like `streets`, and for the same reason: the wall is the
# other thing in Hearthmere that is genuinely everywhere. On core's 16 m module
# the circuit occupies ~70 cells of two or three materials each and costs more
# draw calls than every building in the frame combined. 32 m is two town cells
# exactly, so the partition still nests inside the grid.
CELL_SIZE = 32.0

# The section, the arc-length curve and the outward-normal convention all live
# in `core/circuit.py` — `venues/gatehouse.py` engages the same curtain at the
# North Gate and the two must agree about where the wall face is.
STRETCH_DEFAULT = dict(walk=CIRC.WALK_H, parapet=CIRC.PARAPET_H,
                       thick=CIRC.THICK, face="rubble", walkable=True)

CORBEL_SPACING = 1.30

# A mural stair is steeper than Art Bible §3's domestic 0.175/0.28, because a
# wall stair is: stone, no handrail, and built to take up 5.2 m in the least
# length of Bailey it can. But not arbitrarily steep — the ceiling is set by
# `tools/check_walkable.mjs`, which floods the town on a 0.5 m lattice and can
# therefore only climb 0.35 m per 0.5 m of plan. A 45-degree flight is
# climbable by the real controller and unprovable by the prover, and an asset
# nobody can prove walkable is not finished. 0.22/0.34 is a 0.65 slope: 0.32 m
# per lattice step, with margin.
STAIR_RISE, STAIR_GO = 0.22, 0.34

# THE CURTAIN'S LOD IS A COARSER SWEEP, NOT A DECIMATED ONE (D-058).
#
# `core.batch._cluster` — the automatic simplifier behind `ctx.lod`-less
# geometry — snaps vertices onto a world-axis grid and AVERAGES the UVs of
# everything that lands in a cell. On a building that is harmless. On a swept
# ribbon it is not: one grid cell holds vertices from the outer face, the crown
# and the inner face, whose V coordinates are metres apart on the section
# perimeter, so the average is meaningless. Because the grid is axis-aligned
# and the circuit runs diagonally across it, the damage is PERIODIC along the
# run — which is exactly the dense chevron pleat `ad-town-06` §6 found on the
# inner face in eight frames, with a matching sawtooth on the crown from the
# same averaging applied to position. Proved by rasterising `wall#2_0` straight
# out of the .gltf: LOD0's courses are level and its crown steps are square;
# LOD1's courses zigzag and its crown is a sawtooth, with no material, no mip
# and no anisotropy in the picture at all.
#
# A sweep does not need a simplifier. It is parameterised by its stations, so
# the honest coarse level is the same section swept at every 2nd, 4th or 6th
# station: the profile is preserved EXACTLY, so the courses stay level, the
# crown steps stay square, and the plinth and drip courses stay where a mason
# put them. It is also cheaper than the clusterer's output at the same level.
#
# (stride, sections dropped, fuse-to-one-material). The mouldings go first — a
# 0.17 m drip course is below a pixel past 40 m — then the deck, leaving body,
# parapet and coping. `fuse` re-keys the dressed-stone sections onto the
# stretch's own face material past 40 m, which is what `collapse_materials`
# would have done for a cell batch: it holds the coarse levels to ONE draw per
# cell, so replacing the decimator does not cost the budget anything at the
# distances where most of the circuit is on screen at once.
_LOD_PLAN = (
    (1, (), False),
    (2, (), False),
    (4, ("plinth", "string"), True),
    (6, ("plinth", "string", "deck"), True),
)


# ---------------------------------------------------------------------------
# Character: which stretch of the circuit a given arc length is in
# ---------------------------------------------------------------------------

def _stretches(ring):
    """The wall's history as arc-length ranges.

    Every entry here is a sentence from `docs/areas/hearthmere/WORLD_BIBLE.md` or TOWN_PLAN §5
    turned into geometry. A wall of one section all the way round is a fence.
    """
    V = ring.s_of_vertex

    def span(i, j):
        return (V(i), V(j))

    return [
        # "The oldest stretch, north-west of the Mill Tower, is lower and
        # thicker, with rubble core showing through the patches." It is the
        # low point of the built circuit and the reason the north-west profile
        # sags before the Mill Tower picks it up again.
        dict(span=span(34, 38), name="old", walk=4.90, parapet=1.05,
             thick=(1.80, 1.45), face="rubble", core=True, ivy=0.5),
        # "The south-east stretch is sixty years old and neatly ashlar-faced."
        # It is also the tallest built stretch on land: it was put up when the
        # tolls were good and it is the face the road from the quest zones
        # sees, which is `approach-s` and `t-gate-south`.
        dict(span=span(16, 20), name="new", walk=7.60, parapet=1.40,
             thick=(1.40, 1.15), face="ashlar"),
        # The collapse. Thirty metres on the east went down in a wet winter and
        # was put back in the only stone anyone could get that year, so it is
        # the wrong colour, it is nearly a metre out of line with the crown
        # either side of it, the joint at each end is dead straight, and the
        # props that went in while the mortar cured were never taken away.
        dict(span=span(12, 14), name="rebuilt", walk=6.90, parapet=1.15,
             thick=(1.50, 1.20), face="sandstone", buttress=True),
        # The Mere frontage, Crane Tower round to Heron Tower. The tallest
        # stretch on the circuit, because this is the customs face: everything
        # dutiable arrives by water and the town wanted the boat to see a wall.
        # This is the run that carries `approach-ne` and `t-aerial-ne`.
        dict(span=span(3, 10), name="water", walk=7.90, parapet=1.35,
             thick=(1.45, 1.15), face="ashlar"),
        # The town outgrew it. Between the Tenter Tower and the Spring Tower
        # the circuit runs through the west kitchen gardens: the parapet and
        # the walk were robbed for building stone within living memory and what
        # is left is a garden wall with fruit trained on it.
        dict(span=span(28, 29), name="garden", walk=2.35, parapet=0.0,
             thick=(1.20, 0.95), face="rubble", walkable=False, ivy=1.0),
    ]


def _spec_at(s, stretches):
    for st in stretches:
        a, b = st["span"]
        inside = (a <= s <= b) if a <= b else (s >= a or s <= b)
        if inside:
            out = dict(STRETCH_DEFAULT)
            out.update(st)
            return out
    out = dict(STRETCH_DEFAULT)
    out["name"] = "customs"
    return out


# ---------------------------------------------------------------------------
# Section profiles
# ---------------------------------------------------------------------------

def _rings(spec, deck_y, base_y, sgn):
    """The five swept sections at one station, as `(key, ring)` pairs.

    `v` is measured from `base_y` (the ground at this station), so the base
    follows the contour while `deck_y` — the top — is whatever the run holds.
    That separation is the whole point: it is what lets the crown step.
    """
    tb, tt = spec["thick"]
    ob, ib = tb * 0.5 + 0.02, tb * 0.5 - 0.02
    ot, it = tt * 0.5 + 0.02, tt * 0.5 - 0.02
    v = deck_y - base_y                     # walk deck TOP, above this ground
    top = v - DECK_T                        # masonry top the deck lies on
    par = spec["parapet"]
    u = lambda x: x * sgn                   # noqa: E731 — outward -> path-right

    out = [("body", spec["face"], [(u(-ib), -FOUNDATION), (u(ob), -FOUNDATION),
                                   (u(ot), top), (u(-it), top)])]
    if spec.get("walkable", True):
        inner = -(WALK_W - (ot - 0.02))     # corbelled walk, inboard face
        out.append(("deck", "stone", [(u(ot - 0.02), top), (u(inner), top),
                                      (u(inner), v), (u(ot - 0.02), v)]))
        if par > 0.0:
            out.append(("parapet", spec["face"],
                        [(u(ot), top), (u(it * 0.35), top),
                         (u(it * 0.35), v + par), (u(ot), v + par)]))
            out.append(("coping", "stone",
                        [(u(ot + 0.09), v + par), (u(ot + 0.09), v + par + 0.09),
                         (u((ot + it * 0.35) * 0.5), v + par + 0.18),
                         (u(it * 0.35 - 0.07), v + par + 0.09),
                         (u(it * 0.35 - 0.07), v + par)]))
        # Plinth offset. A wall this thin is built off a wider footing and
        # steps in above it, and the weathered course at that step is the ONE
        # horizontal that runs at eye height for the whole circuit. Without it
        # the outer face is 400 m of undifferentiated rubble, which Art Bible
        # §7 forbids in twelve.
        out.append(("plinth", "stone",
                    [(u(ob), 0.74), (u(ob + 0.14), 0.83),
                     (u(ob + 0.14), 0.93), (u(ob), 1.06)]))
        # Drip course under the walk: it throws rainwater off the outer face
        # and it is the horizontal line that makes the crown's steps legible
        # at a hundred metres, which is the whole point of the wall.
        out.append(("string", "stone",
                    [(u(ot), top - 0.62), (u(ot + 0.17), top - 0.44),
                     (u(ot + 0.17), top - 0.36), (u(ot), top - 0.36)]))
    else:
        out.append(("coping", "stone",
                    [(u(ob * 0.92), top), (u(ob * 0.92), top + 0.09),
                     (u(0.0), top + 0.17),
                     (u(-ib * 0.92), top + 0.09), (u(-ib * 0.92), top)]))
    return out


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build(ctx: VenueContext, asset_id="hm.wall"):
    doc = CIRC.load()
    ring = Ring(doc["path"])
    rng = rng_for(asset_id, "wall")
    stretches = _stretches(ring)

    openings = _openings(ring, doc)
    runs = _runs(ring, stretches, openings)

    # The two things built by sweeping or stepping along the circuit — the
    # curtain and the mural stairs' balustrades — share one per-cell authored
    # LOD chain, which is what keeps them off the vertex-cluster simplifier
    # (see `_LOD_PLAN`) without costing a node. Everything else in the venue is
    # a chunky block the automatic path handles correctly.
    lod_cells = _ring_masonry(ctx, ring, runs, asset_id, rng)
    _towers(ctx, ring, doc, runs, asset_id)
    _stairs(ctx, ring, doc, runs, openings, asset_id, lod_cells)
    _register_lod(ctx, lod_cells)
    for g in doc["gates"]:
        _gate(ctx, ring, g, asset_id)
    _accretion(ctx, ring, runs, asset_id, rng)

    ctx.entity(f"{asset_id}.circuit", "landmark.wall", (0.0, 0.0, 0.0),
               cell="F6", verbs=["inspect"])


# --- openings ---------------------------------------------------------------

def _openings(ring, doc):
    """Arc-length gaps the ring is not built across.

    A gate is a hole in the wall, so the ring simply stops either side of it
    and the gate structure carries its own jambs, arch and spandrel. Cutting
    an opening out of a swept solid would need a boolean; leaving a gap needs
    a comparison.
    """
    out = []
    for g in doc["gates"]:
        s = ring.s_of_point(*g["pos"])
        # Jamb allowance either side. The wide gates carry a masonry block that
        # is deeper than the wall, so the gap is generous; a postern is barely
        # more than its own arch.
        if g["id"].endswith(".north"):
            # `venues/gatehouse.py` stands twin 5.2 m drums on this opening and
            # they engage the curtain, so the ring stops well short of it.
            jamb = 3.10
        else:
            jamb = 1.55 if g["kind"] != "postern" else 0.62
        # `keepout` is what nothing ELSE may stand in, which is not the same
        # as the gap in the ring: the North Gate's twin drums are built by
        # `venues/gatehouse.py` and reach 6.9 m either side of the road, so a
        # mural stair laid on the ring's own gap ran straight through one.
        keep = 7.9 if g["id"].endswith(".north") else float(g["clear"]) * 0.5 + jamb + 0.6
        out.append(dict(rec=g, s=s, half=float(g["clear"]) * 0.5 + jamb,
                        keepout=keep))
    return out


def _blocked(s, openings, total):
    for o in openings:
        d = abs((s - o["s"] + total * 0.5) % total - total * 0.5)
        if d < o["half"]:
            return True
    return False


# --- the ring ---------------------------------------------------------------

def _runs(ring, stretches, openings):
    """Split the circuit into runs of constant crown height.

    This is the function the wall lives or dies by. Walking the stations, the
    target crown is `ground + walk`, and a run holds its level until the target
    has drifted more than 0.6 of a course — at which point the run ends and the
    next starts a whole number of courses lower or higher. The result is a
    stepped crown over a continuous base, which is what a mason building
    level courses on falling ground has no choice but to produce.
    """
    total = ring.total
    runs, cur = [], None
    for s in ring.stations(2.0):
        x, z, _t, _n = ring.at(s)
        if _blocked(s, openings, total):
            cur = None
            continue
        spec = _spec_at(s, stretches)
        g = float(TERR.height(x, z))
        target = g + spec["walk"]
        if cur is not None and cur["spec"]["name"] != spec["name"]:
            cur = None                       # a material change is a straight joint
        if cur is None:
            cur = dict(spec=spec, deck=round(target / COURSE) * COURSE, st=[])
            runs.append(cur)
        elif abs(target - cur["deck"]) > COURSE * 0.6:
            steps = round((target - cur["deck"]) / COURSE)
            last = cur["st"][-1]
            cur = dict(spec=spec, deck=cur["deck"] + steps * COURSE, st=[])
            runs.append(cur)
            # Repeat the previous station so the two runs share a plan position
            # and the step is a clean vertical riser rather than a 2 m ramp.
            cur["st"].append(last)
        cur["st"].append((s, x, z, g))
    return [r for r in runs if len(r["st"]) >= 2]


def _run_sweep(ctx, ring, run, stride=1, drop=(), fuse=False):
    """One run of curtain, swept at every `stride`-th station.

    `stride` is the LOD knob (see `_LOD_PLAN`). The last station is always
    kept, whatever the stride divides into, because dropping it would shorten
    the run and open a hole between this run and the next one at exactly the
    distance the coarse level is drawn at.
    """
    st = run["st"]
    if stride > 1 and len(st) > 2:
        want = list(range(0, len(st) - 1, stride)) + [len(st) - 1]
        sel = []
        for i in want:
            if sel and math.hypot(st[i][1] - st[sel[-1]][1],
                                  st[i][2] - st[sel[-1]][2]) < 0.05:
                continue
            sel.append(i)
        st = [st[i] for i in sel] if len(sel) >= 2 else [st[0], st[-1]]
    path, per_station = [], []
    for (_s, x, z, g) in st:
        path.append((x, g, z))
        per_station.append(_rings(run["spec"], run["deck"], g, ring.sgn))
    out = M.Group()
    for i, (key, mat, _r) in enumerate(per_station[0]):
        if key in drop:
            continue
        if fuse:
            mat = run["spec"]["face"]
        profiles = [ps[i][2] for ps in per_station]
        out.add(M.sweep(profiles, path, mat=mat, uv_scale=ctx.uv_scale(mat)))
    return out


def _ring_masonry(ctx, ring, runs, asset_id, rng):
    corbels, ivy, putlogs = [], [], []
    tris = 0
    # [level][cell key] -> Group. Bucketed per cell before the chain is
    # registered so the circuit still culls in 32 m pieces: one authored chain
    # for all 512 m would be 512 m of wall drawn whenever any of it is on
    # screen, which is the opposite of what an LOD chain is for.
    lod_cells = [{} for _ in _LOD_PLAN]
    for ri, run in enumerate(runs):
        spec = run["spec"]
        deck = run["deck"]
        for li, (stride, drop, fuse) in enumerate(_LOD_PLAN):
            grp = _run_sweep(ctx, ring, run, stride, drop, fuse)
            if li == 0:
                tris += grp.tri_count
            _lod_add(lod_cells, ctx, li, grp)

        _run_collision(ctx, run, ring)

        if not spec.get("walkable", True):
            continue
        # Corbels under the walk, and the hedge/ivy that a wall this old grows.
        s0, s1 = run["st"][0][0], run["st"][-1][0]
        n = max(1, int(round(abs(s1 - s0) / CORBEL_SPACING)))
        for k in range(n):
            s = s0 + (s1 - s0) * (k + 0.5) / n
            x, z, _t, nout = ring.at(s)
            g = float(TERR.height(x, z))
            _tt = spec["thick"][1] * 0.5 - 0.02
            px, pz = x - nout[0] * _tt, z - nout[1] * _tt
            corbels.append((px, deck - DECK_T, pz, math.atan2(nout[0], nout[1])))
        for k in range(int(abs(s1 - s0) / 1.70)):
            for lvl in (2.05, 3.75):
                if deck - lvl < 1.0 or rng.random() < 0.18:
                    continue
                sp = s0 + (s1 - s0) * (k + 0.5) * 1.70 / max(abs(s1 - s0), 1e-6)
                px, pz, _t, no = ring.at(sp)
                gy = float(TERR.height(px, pz))
                thk = spec["thick"][0] * 0.5
                putlogs.append(dict(
                    pos=(px + no[0] * (thk - 0.04), gy + lvl + rng.uniform(-0.05, 0.05),
                         pz + no[1] * (thk - 0.04)),
                    rot_y=CIRC.yaw_facing(no)))
        for k in range(int(abs(s1 - s0) * spec.get("ivy", 0.10) * 0.30)):
            s = s0 + (s1 - s0) * rng.random()
            x, z, _t, nout = ring.at(s)
            g = float(TERR.height(x, z))
            h = rng.uniform(0.2, 0.80) * (deck - g)
            ivy.append(dict(pos=(x + nout[0] * (spec["thick"][0] * 0.5 + 0.06),
                                 g + h,
                                 z + nout[1] * (spec["thick"][0] * 0.5 + 0.06)),
                            rot_y=CIRC.yaw_facing(nout),
                            scale=rng.uniform(0.75, 1.5)))

    ctx.instance(f"{NAME}_corbel", K.corbel(f"{asset_id}.corbel", project=0.52),
                 corbels)
    # Putlog holes: the scaffold poles were built into the wall as it went up
    # and sawn off flush when it came down, and five hundred years later the
    # rotted ends are still in the holes. Two rows of small dark squares is the
    # cheapest possible "a person built this, course by course" cue, and it is
    # the detail that stops the outer face reading as an extruded slab.
    putlog = M.Group()
    putlog.add(M.box(0.17, 0.15, 0.26, 0.012, "oak_dark"))
    putlog.add(M.box(0.24, 0.06, 0.06, 0.008, "stone").translate(0, 0.10, 0.06))
    ctx.instance(f"{NAME}_putlog", putlog, putlogs)
    # Ivy as small crossed sheets rather than one big card: a single quad reads
    # as a decal, three at 60 degrees reads as a mass with a silhouette, which
    # is the only thing that matters at the distance the wall is seen from.
    sheet = M.Group()
    for a in (0.0, 1.05, 2.10):
        q = M.box(1.15, 1.45, 0.02, 0.0, "ivy")
        q.rotate_y(a)
        q.translate(0, 0, -0.05)
        sheet.add(q)
    ctx.instance(f"{NAME}_ivy", sheet, ivy)
    return lod_cells


def _lod_add(lod_cells, ctx, li, group):
    """Bucket one level of one object into the per-cell chain accumulator."""
    for key, m in group.items():
        cuts = (B.assign_cells(m, ctx.cell_size) if ctx.batching
                else [("all", m)])
        for ck, sub in cuts:
            lod_cells[li].setdefault(ck, M.Group()).add(sub, key)


def _register_lod(ctx, lod_cells):
    """One authored chain per cell of circuit-following masonry.

    A coarse level that lost a cell entirely — a two-station stub whose
    stride-6 sweep is the same two stations — inherits the level above rather
    than vanishing, because a missing cell at 40 m is a hole in the town's edge.
    """
    for ck in sorted(lod_cells[0]):
        chain = [lod_cells[li].get(ck) for li in range(len(_LOD_PLAN))]
        for i in range(1, len(chain)):
            if chain[i] is None or not chain[i].tri_count:
                chain[i] = chain[i - 1]
        ctx.lod(f"curtain.{ck}", chain)


def _run_collision(ctx, run, ring):
    """Solid wall, standable crown, solid parapet — authored per sub-run.

    Sub-divided to ~6 m because a single box down a 40 m run of a bending
    circuit is a box that leaves the wall at both ends, and because the crown
    the player stands on has to be at the height the geometry actually is.
    """
    spec = run["spec"]
    deck = run["deck"]
    st = run["st"]
    tb = spec["thick"][0]
    i = 0
    while i < len(st) - 1:
        j = min(len(st) - 1, i + 3)
        a, b = st[i], st[j]
        if math.hypot(b[1] - a[1], b[2] - a[2]) < 0.05:
            i = j
            continue
        g = min(a[3], b[3])
        ctx.collider(COL.segment_box((a[1], 0.0, a[2]), (b[1], 0.0, b[2]),
                                     tb, g - FOUNDATION, deck,
                                     kind="solid", tag="town_wall", extend=0.35))
        if spec.get("walkable", True):
            # The corbelled half of the walk: a surface, never a solid. It
            # overhangs the Bailey by nearly a metre at 5 m up and a solid
            # there would be an invisible ceiling over the lane.
            mid_s = (a[0] + b[0]) * 0.5
            _x, _z, _t, nout = ring.at(mid_s)
            off = WALK_W * 0.5
            ax = a[1] - nout[0] * off
            az = a[2] - nout[1] * off
            bx = b[1] - nout[0] * off
            bz = b[2] - nout[1] * off
            ctx.collider(COL.segment_box((ax, 0.0, az), (bx, 0.0, bz),
                                         WALK_W, deck - 0.25, deck,
                                         kind="surface", tag="wall_walk",
                                         extend=0.35))
            if spec["parapet"] > 0:
                ox = spec["thick"][1] * 0.5 - 0.21
                ctx.collider(COL.segment_box(
                    (a[1] + nout[0] * ox, 0.0, a[2] + nout[1] * ox),
                    (b[1] + nout[0] * ox, 0.0, b[2] + nout[1] * ox),
                    0.44, deck, deck + spec["parapet"],
                    kind="solid", tag="wall_parapet", extend=0.35))
        i = j


# --- towers -----------------------------------------------------------------

def _towers(ctx, ring, doc, runs, asset_id):
    """Eleven towers: nine D-plan drums and two square angle turrets.

    **These are older than the wall they stand in** (D-047, `plan_data.TOWERS`).
    Hearthmere had a burh enclosure — ditch, bank and a ring of stone turrets —
    three centuries before it had a customs boundary, and when it finally walled
    itself for tolls it strung a low curtain between the turrets it already had.
    That is the whole reason the profile works: a 6 m customs wall stays
    canonically low while eleven 11-18 m verticals give the town's edge a
    rhythm. Pass 04 rejected the previous scheme in one line — "towers stand
    only 2.6 m proud of a 6.3 m curtain, so from any aerial it is a low grey
    ribbon."

    Nine of the eleven were re-roofed when the curtain went up, in slate, on
    the cheap: a conical spire on a drum, a squat pyramid on a square. Two
    never were, and stand open with a wall-head and a self-sown ash in the
    crown — which is what stops a ring of identical cones reading as a kit.

    A mural tower on a customs wall is a lookout and a store, not a gun
    platform, so these are solid to the walk and carry a turret above it with
    the walk passing along its inner side. The arrow loops are in the lower
    stage, below the walk and at the wrong spacing for it — they are the burh's,
    not the curtain's.
    """
    def deck_near(s):
        """The crown of the curtain AT this tower, not the schedule default.

        The stretches now run from a 2.35 m robbed garden wall to a 7.9 m Mere
        frontage, so a tower that takes its walk level from `STRETCH_DEFAULT`
        puts its corbel table a metre and a half off the wall it grows out of.
        """
        best, bd = None, 1e18
        for r in runs:
            for (rs, _x, _z, _g) in r["st"]:
                d = abs((rs - s + ring.total * 0.5) % ring.total - ring.total * 0.5)
                if d < bd:
                    best, bd = r, d
        return best

    # THE TOWERS ARE ONE AUTHORED LOD CHAIN, NOT ELEVEN CELL BATCHES.
    #
    # They used to go into the ordinary 32 m cell batching with everything
    # else, and at LOD2/LOD3 that produced a floating roof. The mechanism is
    # worth writing down because it will catch the next person:
    # `core.venue._levels` decimates PER MATERIAL PRIMITIVE, so in a cell whose
    # `rubble` primitive is thirty metres of curtain plus one small drum, 6 % of
    # the cell's rubble triangles is the curtain — the drum dissolves — while
    # the `slate` primitive in the same cell is nothing but the spire, so 6 % of
    # it is still a recognisable cone. Result: a slate cone hanging in the sky
    # over a flat-topped wall, which is exactly what `approach-ne` and the four
    # aerials rendered, and it is why every tower roof was missing from
    # `t-aerial-ne` while the towers themselves were visible.
    #
    # `ctx.lod` is the documented escape for this ("where the automatic
    # simplifier destroys something that has to survive — a spire"). One chain
    # for all eleven, not one each: eleven authored nodes would cost eleven
    # times two or three primitives at every distance, and the eleven towers
    # together are ~20 k triangles and three materials, so as one node they are
    # three draw calls that never dissolve. The silhouette this whole wave is
    # about is carried by these eleven shapes; they are the last thing in the
    # build that should be allowed to simplify away.
    towers_all = M.Group()

    for rec in doc["towers"]:
        x, z = rec["pos"]
        s = ring.s_of_point(x, z)
        _px, _pz, tan, nout = ring.at(s)
        g = float(TERR.height(x, z))
        square = rec["shape"] == "square"
        top = g + float(rec["height"])
        roof_kind = rec.get("roof", "pyramid" if square else "cone")
        run = deck_near(s)
        deck = run["deck"] if run else g + STRETCH_DEFAULT["walk"]
        # A turret on the robbed garden stretch has no walk to meet, so it
        # keeps a nominal lower stage rather than a 2 m stump.
        deck = max(deck, g + 3.6)
        rid = rec["id"]
        rng = rng_for(asset_id, rid)

        out = M.Group()
        R = 2.80                              # 5.6 m external
        proj = 3.40
        # Centre it so the drum stands `proj` outside the wall's outer face.
        cx = x + nout[0] * (proj + 0.72 - R)
        cz = z + nout[1] * (proj + 0.72 - R)
        # The drum is authored with its flat back on local +Z, so local -Z has
        # to end up OUTWARD. `ang_out` is the world heading of outward, kept
        # separately because the loops are placed in world space off it.
        yaw = CIRC.yaw_facing(nout)
        ang_out = math.atan2(nout[0], nout[1])

        # The drum's centre stands this far OUTBOARD of the wall centreline, so
        # its flat back — the wall's own inner face — is at this local +Z. Get
        # this wrong and the clamp eats the tower: the first version worked in
        # the wrong frame, clipped at local z = -0.77, and left a 0.8 m slab of
        # what should have been a 5.6 m drum.
        centre_out = proj + 0.72 - R
        back = centre_out + STRETCH_DEFAULT["thick"][0] * 0.5

        # Lower stage: solid to the walk, battered, with a plinth splay.
        lower = _drum(R, g - 0.8, deck, square, batter=0.16, mat="rubble")
        _clip_back(lower, back)
        lower.rotate_y(yaw)
        lower.translate(cx, 0, cz)
        out.add(lower)

        # Turret above the walk, set outboard so the walk passes inside it. Its
        # own back is 0.42 m further out again, which puts the clamp beyond its
        # radius — a turret is a full drum and does not need clipping.
        #
        # `top` is the authored OVERALL height — the apex of the spire, or the
        # wall-head on an unroofed turret. The masonry stops at `head` and the
        # roof takes the rest, so raising a tower in the plan raises the thing
        # the silhouette actually reads and not a length of blank drum.
        R2 = R - 0.55
        roof_h = {"cone": R2 * 1.62, "pyramid": R2 * 1.34, "open": 0.0}[roof_kind]
        head = top - roof_h
        tcx, tcz = cx + nout[0] * 0.42, cz + nout[1] * 0.42
        up = _drum(R2, deck - 0.10, head, square, batter=0.07, mat="rubble")
        _clip_back(up, back - 0.42)
        up.rotate_y(yaw)
        up.translate(tcx, 0, tcz)
        out.add(up)
        # Corbelled eaves table. On a roofed turret it is what the spire sits
        # inside; on an open one it is the wall-head itself, and it is the only
        # thing between the crown and the sky.
        cap = _drum(R2 + 0.20, head, head + 0.20, square, batter=0.0, mat="stone")
        _clip_back(cap, back - 0.42)
        cap.rotate_y(yaw)
        cap.translate(tcx, 0, tcz)
        out.add(cap)

        if roof_kind == "open":
            # Never re-roofed. A broken wall-head, and something growing in the
            # crown: two of these round the circuit are what proves the other
            # nine roofs are a repair rather than a design.
            for k in range(9):
                a = ang_out + (k - 4) * 0.30
                bh = rng.uniform(0.18, 0.62)
                mer = M.box(0.62, bh, 0.42, 0.03, "rubble",
                            uv_scale=MATS.uv_detail(
                                "rubble", 0.8,
                                why="a broken wall-head stub 0.18-0.62 m high; "
                                    "the library's 2 m tile puts a quarter of "
                                    "one stone on it and it reads as untextured"))
                mer.rotate_y(CIRC.yaw_facing((math.sin(a), math.cos(a))))
                mer.translate(tcx + math.sin(a) * (R2 - 0.22), head + 0.20 + bh * 0.5,
                              tcz + math.cos(a) * (R2 - 0.22))
                out.add(mer)
            ash = VEG.shrub(f"{rid}.ash", radius=rng.uniform(0.85, 1.15),
                            height=rng.uniform(1.5, 2.0))
            ash.translate(tcx + rng.uniform(-0.4, 0.4), head + 0.20,
                          tcz + rng.uniform(-0.4, 0.4))
            out.add(ash)
        elif roof_kind == "pyramid":
            # The two angle turrets are the tallest things on the circuit and
            # the town's profile from the water. A squat slate pyramid gives
            # them a point to read against the sky; a flat top at this height
            # reads as an unfinished box.
            spire = M.lathe([(R2 * 1.10, 0.0), (R2 * 0.94, 0.42),
                             (0.0, roof_h)], 4, "slate", close_bottom=False)
            spire.rotate_y(math.pi * 0.25 + yaw)
            spire.translate(tcx, head + 0.10, tcz)
            out.add(spire)
            fin = M.lathe([(0.0, 0.0), (0.055, 0.09), (0.03, 0.62), (0.0, 0.78)],
                          8, "iron")
            fin.translate(tcx, top - 0.06, tcz)
            out.add(fin)
        else:
            # A conical slate spire on a D-plan drum, oversailing the corbel
            # table so it throws a shadow line on the masonry rather than
            # sitting on it like a hat. Steep, because slate on a cone is laid
            # steep or it leaks, and a steep cone is the shape that reads at
            # 140 m from the water.
            spire = M.lathe([(R2 * 1.14, 0.0), (R2 * 1.02, 0.30),
                             (R2 * 0.55, roof_h * 0.62), (0.0, roof_h)],
                            16, "slate", close_bottom=False)
            spire.translate(tcx, head + 0.14, tcz)
            out.add(spire)
            # Weathervane on the Bridgefoot Tower only — the one on the
            # departure frame. A vane on all nine would be a kit.
            if rid.endswith(".02"):
                mast = M.cylinder(0.035, 1.15, 6, 0.004, "iron")
                mast.translate(tcx, top + 0.50, tcz)
                out.add(mast)
                vane = M.box(0.62, 0.30, 0.02, 0.004, "iron")
                vane.rotate_y(0.7)
                vane.translate(tcx + 0.20, top + 0.92, tcz)
                out.add(vane)

        # Loops: three round the outer face of the lower stage, at a level
        # that has nothing to do with the present walk.
        for k in (-0.62, 0.0, 0.62):
            a = ang_out + k
            lx, lz = math.sin(a), math.cos(a)
            lp = K.arrow_loop(f"{rid}.loop{k}", height=0.95)
            lp.rotate_y(CIRC.yaw_facing((lx, lz)))
            lp.translate(cx + lx * (R - 0.20), g + 2.15 + rng.uniform(-0.1, 0.1),
                         cz + lz * (R - 0.20))
            out.add(lp)
        towers_all.add(out)

        # TWO volumes, not one. A single cylinder to the top is the obvious
        # thing and it severs the wall-walk at every one of the eleven towers —
        # measured: it cut the circuit into eighteen unconnected segments, so
        # each mural stair reached only its own stretch. The lower stage is
        # solid only to the walk, which the player stands ON; above that, only
        # the turret blocks, and the turret is set outboard by design so 1.1 m
        # of walk passes inside it.
        ctx.collider("cylinder" if not square else "box",
                     **({"center": (cx, (g - 0.8 + deck) * 0.5, cz),
                         "radius": R, "height": deck - g + 0.8}
                        if not square else
                        {"center": (cx, (g - 0.8 + deck) * 0.5, cz),
                         "half": (R, (deck - g + 0.8) * 0.5, R), "rot_y": yaw}),
                     tag="wall_tower")
        # Only the MASONRY blocks. The spire is 3-4 m of slate over the player's
        # head and a collider on it would be an invisible ceiling on the walk.
        tx, tz = tcx, tcz
        ctx.collider("cylinder" if not square else "box",
                     **({"center": (tx, (deck + head) * 0.5, tz),
                         "radius": R2, "height": max(0.2, head - deck)}
                        if not square else
                        {"center": (tx, (deck + head) * 0.5, tz),
                         "half": (R2, max(0.1, (head - deck) * 0.5), R2),
                         "rot_y": yaw}),
                     tag="wall_turret")
        ctx.entity(rid, "landmark.tower", (x, g, z), verbs=["inspect"],
                   cell=None)

    # One level. `ctx.lod` pads a short list by repeating the last, so this is
    # "never simplify" stated once rather than four coarse drums authored by
    # hand — and at ~20 k triangles across the whole circuit there is nothing
    # to win by simplifying them.
    ctx.lod(f"{asset_id}.towers", [towers_all])


def _drum(R, y0, y1, square, batter=0.12, mat="rubble", segments=14):
    """A round or square tower stage, battered, base at y0 and top at y1."""
    if square:
        h = y1 - y0
        b = M.box(R * 2.0, h, R * 2.0, 0.03, mat)
        b.translate(0, y0 + h * 0.5, 0)
        # Batter: pull the top in. Scaling the whole box would move the base
        # too, so the taper is applied to the top ring of vertices only.
        t = (b.v[:, 1] - y0) / max(h, 1e-6)
        b.v[:, 0] -= (b.v[:, 0] / R) * batter * t
        b.v[:, 2] -= (b.v[:, 2] / R) * batter * t
        return b
    return M.lathe([(R, y0), (R - batter * 0.35, y0 + (y1 - y0) * 0.28),
                    (R - batter, y1)], segments, mat, close_bottom=False)


def _clip_back(mesh, z_at):
    """Flatten everything behind local +Z = `z_at` onto that plane.

    The back of a mural tower is the wall it grows out of, so it is not a
    curve; clamping is enough and it avoids a boolean. Called before the
    tower is rotated into place, while +Z is still 'inboard'.
    """
    for m in (mesh.parts.values() if isinstance(mesh, M.Group) else [mesh]):
        if len(m.v):
            m.v[:, 2] = np.minimum(m.v[:, 2], z_at)
    return mesh


# --- mural stairs -----------------------------------------------------------

def _slots_near_wall(ring, reach):
    """(arc length, half-extent) for building masses that stand IN the stair band.

    Read from `buildingSlots[].polygon` in the town record rather than guessed
    at, so a plot that moves takes its exclusion with it. `reach` is measured
    from the wall centreline to the nearest polygon CORNER, not to the plot's
    centre: the flight occupies a band roughly 1.0-2.5 m inboard of the face,
    so a house whose back fence is six metres off the wall is not in its way,
    and treating it as one leaves the North Gate with no room for a stair at
    all — which is what happened, and the scorer then put the flight inside
    the Bridgefoot Tower because that was the least bad of no good options.
    """
    with open(CIRC.TOWN_JSON, encoding="utf-8") as f:
        slots = json.load(f).get("buildingSlots", [])
    out = []
    for s in slots:
        poly = [(float(p[0]), float(p[1])) for p in s.get("polygon", [])]
        if len(poly) < 3:
            continue
        arcs, close = [], False
        for (px, pz) in poly:
            sp = ring.s_of_point(px, pz)
            qx, qz, _t, _n = ring.at(sp)
            arcs.append(sp)
            if math.hypot(px - qx, pz - qz) <= reach:
                close = True
        if not close:
            continue
        # Once ANY corner is in the stair band the WHOLE mass is excluded. The
        # authored polygon is the plot, not the collider: the townhouse kit adds
        # outshuts, eaves and plinths outside it, so an exclusion sized to the
        # corners that happen to be nearest is an exclusion a flight walks past
        # and then into the back of the building.
        near = arcs
        # Arc span of the offending corners, unwrapped about the first.
        base = near[0]
        rel = [((v - base + ring.total * 0.5) % ring.total) - ring.total * 0.5
               for v in near]
        lo, hi = min(rel), max(rel)
        out.append((base + (lo + hi) * 0.5, (hi - lo) * 0.5 + 1.2))
    return out



def _stairs(ctx, ring, doc, runs, doc_openings, asset_id, lod_cells=None):
    """Five flights up the inner face, at the authored positions.

    Treads are `surface` volumes: a flight in the Bailey that blocked the lane
    would be worse than no flight at all, and a climbable surface is exactly
    what a stair is.

    **The flight has to be pointed.** All five authored positions are beside a
    gate or a tower, which is exactly where a mason puts a mural stair and
    exactly what makes it hard: a 9 m flight centred on the authored point runs
    half its length into the drum next to it. Measured, before this chose a
    direction: all five flights were blocked, the best of them reaching 2.83 m
    of a 5.25 m climb, so the wall-walk existed and no player could stand on
    it. The flight is therefore laid to ONE side, and the side is the one with
    clear arc length on it.
    """
    deck_at = {}
    for r in runs:
        for (s, _x, _z, _g) in r["st"]:
            deck_at[round(s, 2)] = r["deck"]

    # What a flight may not run into, as (arc length, half-extent). Gates,
    # towers, and — the one that is easy to forget — the buildings that stand
    # against the inside of the wall. The Bailey has cottages on it for most of
    # its 332 m, and a stair laid without asking about them goes through
    # somebody's back wall.
    blockers = [(o["s"], o["keepout"]) for o in doc_openings]
    for t in doc["towers"]:
        blockers.append((ring.s_of_point(*t["pos"]), 3.30))
    for slot in _slots_near_wall(ring, 3.6):
        blockers.append(slot)

    def clearance(a, b):
        """Smallest gap between the arc interval [a, b] and any blocker."""
        best = 1e9
        for (bs, half) in blockers:
            d = abs((0.5 * (a + b) - bs + ring.total * 0.5) % ring.total
                    - ring.total * 0.5)
            best = min(best, d - half - abs(b - a) * 0.5)
        return best

    for i, pos in enumerate(doc.get("stairs", [])):
        x, z = float(pos[0]), float(pos[1])
        s0 = ring.s_of_point(x, z)
        px, pz, _t, _n = ring.at(s0)
        g = float(TERR.height(px, pz))
        deck = min(deck_at.items(), key=lambda kv: abs(kv[0] - s0))[1] \
            if deck_at else g + STRETCH_DEFAULT["walk"]
        rise = deck - g
        if rise < 0.6:
            continue
        sid = f"{asset_id}.stair.{i + 1:02d}"
        flight, run = K.stair_flight(sid, rise, width=1.25, riser=STAIR_RISE,
                                     going=STAIR_GO, mat="stone", spine=0.34)

        # Lay the foot at the authored point and climb away from the blocker,
        # sliding along the wall if BOTH ways are fouled. Scored rather than
        # branched, because every candidate has to be re-checked after it moves
        # — the first version chose a direction, shifted, and never looked
        # again, which walked flight 1 straight into the Bridgefoot Tower.
        cand = []
        for d in (1.0, -1.0):
            for shift in np.arange(0.0, 14.0, 0.5):
                a = s0 + d * shift
                cand.append((min(clearance(a, a + d * run), 2.5) - shift * 0.14,
                             a, d))
        _score, fs, d = max(cand)
        hs = fs + d * run
        fx, fz, tanf, noutf = ring.at(fs)
        hx, hz, _th, _nh = ring.at(hs)
        g = float(TERR.height(fx, fz))
        deck = min(deck_at.items(), key=lambda kv: abs(kv[0] - hs))[1]
        rise = max(0.6, deck - g)
        flight, run = K.stair_flight(sid, rise, width=1.25, riser=STAIR_RISE,
                                     going=STAIR_GO, mat="stone", spine=0.34)

        # A flight is a straight rigid thing and the circuit is not, so the
        # offset from the wall has to clear the SAGITTA of whatever the wall
        # does between foot and head. Flight 2 runs along the bend at the Water
        # Gate and, laid on the foot's own normal, its top half was inside the
        # curtain.
        ln = math.hypot(hx - fx, hz - fz) or 1.0
        ux, uz = (hx - fx) / ln, (hz - fz) / ln
        perp = (-uz, ux)
        if perp[0] * -noutf[0] + perp[1] * -noutf[1] < 0:
            perp = (uz, -ux)
        sag = 0.0
        for t in np.linspace(0.0, 1.0, 13):
            qx, qz, _t2, _n2 = ring.at(fs + (hs - fs) * t)
            sag = max(sag, (qx - fx) * perp[0] + (qz - fz) * perp[1])
        # A metre of daylight between the flight and the wall face. The wall's
        # collision runs as overlapping boxes with 0.35 m of extension at every
        # kink, so at a bend it protrudes further inboard than the geometry
        # does — and a flight tucked hard against the face is a flight the
        # controller cannot get onto.
        off = STRETCH_DEFAULT["thick"][0] * 0.5 + 1.05 + sag

        # `stair_flight` ascends along its own local -Z, so -Z has to point the
        # way the flight CLIMBS: from the foot toward the head.
        climb = (ux, uz)
        flight.rotate_y(CIRC.yaw_facing(climb))
        ax = fx + perp[0] * off
        az = fz + perp[1] * off
        flight.translate(ax, g, az)
        ctx.emit(flight)

        # The balustrade on the open side. Architecturally it is what a mural
        # stair has instead of a handrail (Art Bible §2: no machined metal, and
        # nobody in Hearthmere is forging a balustrade for the wall stair). It
        # is also what makes the flight PROVABLE: `tools/check_walkable.mjs`
        # stores one standing height per lattice cell, so a flight open on both
        # sides gets its treads reached sideways from the ground first, pinned
        # at ground level, and can then never be climbed. Measured before this:
        # the treads were geometrically clear the whole way up and the flood
        # could not get past the second one.
        n = max(1, int(round(rise / 0.32)))
        for k in range(n):
            top = g + rise * (k + 1) / n
            d0 = run * (k / n)
            d1 = run * ((k + 1) / n)
            ctx.collider(COL.segment_box(
                (ax + climb[0] * d0, 0.0, az + climb[1] * d0),
                (ax + climb[0] * d1, 0.0, az + climb[1] * d1),
                1.35, g - 0.2, top, kind="surface", tag="wall_stair",
                extend=0.30))
            ctx.collider(COL.segment_box(
                (ax + perp[0] * 0.86 + climb[0] * d0, 0.0,
                 az + perp[1] * 0.86 + climb[1] * d0),
                (ax + perp[0] * 0.86 + climb[0] * d1, 0.0,
                 az + perp[1] * 0.86 + climb[1] * d1),
                0.34, g - 0.2, top + 0.86, kind="solid", tag="stair_rail",
                extend=0.22))
        # The balustrade is a stepped run like the curtain's crown, so it fails
        # the vertex-cluster simplifier the same way and for the same reason —
        # it was the second half of the chevron in `craft-walk-04`, the part
        # closing the right of the frame. It joins the curtain's per-cell chain
        # (same `stone` primitive, so it costs no extra draw) and its coarse
        # levels are fewer, longer blocks rather than averaged vertices.
        # Past 40 m a 0.30 m rail standing behind a 1.4 m wall is three pixels
        # of the same stone, so levels 2 and 3 drop it — which also keeps the
        # coarse levels at the one fused draw per cell that `_LOD_PLAN` buys.
        if lod_cells is not None:
            for li, (stride, _drop, fuse) in enumerate(_LOD_PLAN):
                if fuse:
                    continue
                _lod_add(lod_cells, ctx, li,
                         _balustrade(g, rise, run, ax, az, climb, perp,
                                     max(1, n // stride)))
        else:
            ctx.emit(_balustrade(g, rise, run, ax, az, climb, perp, n))
        ctx.entity(f"{asset_id}.stair.{i + 1:02d}", "landmark.wall_stair",
                   (ax, g, az), verbs=["inspect"])


def _balustrade(g, rise, run, ax, az, climb, perp, steps):
    """The stepped parapet on the open side of a mural flight, in `steps` blocks.

    Architecturally it is what a mural stair has instead of a handrail (Art
    Bible §2: no machined metal, and nobody in Hearthmere is forging a
    balustrade for the wall stair). It is also what makes the flight PROVABLE:
    `tools/check_walkable.mjs` stores one standing height per lattice cell, so a
    flight open on both sides gets its treads reached sideways from the ground
    first, pinned at ground level, and can then never be climbed. Measured
    before this: the treads were geometrically clear the whole way up and the
    flood could not get past the second one.
    """
    bal = M.Group()
    for k in range(steps):
        top = g + rise * (k + 1) / steps
        d0 = run * (k / steps)
        d1 = run * ((k + 1) / steps)
        bx = ax + perp[0] * 0.86 + climb[0] * (d0 + d1) * 0.5
        bz = az + perp[1] * 0.86 + climb[1] * (d0 + d1) * 0.5
        blk = M.box(0.30, top + 0.86 - (g - 0.15), (d1 - d0) + 0.06, 0.02,
                    "stone")
        blk.rotate_y(CIRC.yaw_facing(climb))
        blk.translate(bx, (g - 0.15 + top + 0.86) * 0.5, bz)
        bal.add(blk)
    return bal


# --- gates ------------------------------------------------------------------

def _gate(ctx, ring, rec, asset_id):
    """One opening in the circuit. Four characters, one construction.

    The north gate is not here: it is the departure frame and it is built by
    `venues/gatehouse.py` on its own venue record with twin drum towers and
    the bridge beyond it. This builds the working south gate, the settled old
    west gate, the water gate onto the wharf, and the three posterns.
    """
    kind = rec["kind"]
    if rec["id"].endswith(".north"):
        return
    x, z = rec["pos"]
    s = ring.s_of_point(x, z)
    px, pz, tan, nout = ring.at(s)
    g = float(TERR.height(px, pz))
    clear = float(rec["clear"])
    head = float(rec["head"])
    rid = rec["id"]
    rng = rng_for(asset_id, rid)
    # Local frame: +X along the wall, -Z outward, so every gate is authored
    # once and turned into place.
    yaw = CIRC.yaw_facing(nout)
    out = M.Group()

    thick = 2.35 if kind != "postern" else 1.45
    rise = clear * 0.5
    spring = head - rise
    settle = 0.20 if rid.endswith(".west") else 0.0

    # Jambs. Battered like the wall, with a splayed spur stone at the outer
    # corner of each — J2's "spur stones at both jambs, deeply scored by nave
    # hubs" is a cart-town detail and it is the same at every gate that carts
    # use.
    pier_w = 1.55 if kind != "postern" else 0.62
    wall_h = g + STRETCH_DEFAULT["walk"]
    block_h = {"gate": head + 2.05, "water": head + 1.65,
               "postern": head + 1.35}[kind]
    for sx in (-1, 1):
        j = M.box(pier_w, block_h, thick, 0.03, "ashlar")
        if settle and sx < 0:
            j.v[:, 1] -= settle * (1.0 - np.clip(j.v[:, 1] / block_h, 0, 1)) * 0.0
            j.v[:, 1] -= settle
        j.translate(sx * (clear * 0.5 + pier_w * 0.5), block_h * 0.5, 0)
        out.add(j)
        if kind != "postern":
            spur = M.lathe([(0.30, 0.0), (0.27, 0.55), (0.17, 0.92), (0.0, 1.02)],
                           9, "stone")
            spur.translate(sx * (clear * 0.5 - 0.10), 0.0, -thick * 0.5 - 0.22)
            out.add(spur)

    arch = K.arch_ring(f"{rid}.arch", clear + 0.10, rise=rise, ring=0.44,
                       depth=thick, mat="ashlar", drop=settle)
    arch.translate(0, spring - settle * 0.5, 0)
    out.add(arch)

    # Spandrel: the masonry between the arch and the block above it, cut to
    # the intrados so no crescent of wall floats over the opening.
    soff = K.arch_soffit(clear + 0.10, rise, pad=0.44)
    prof = [(-clear * 0.5 - 0.55, spring - 0.4)] + \
           [(sx_, spring + yy) for sx_, yy in soff] + \
           [(clear * 0.5 + 0.55, spring - 0.4),
            (clear * 0.5 + 0.55, block_h), (-clear * 0.5 - 0.55, block_h)]
    span = M.prism(prof, thick, chamfer=0.0)
    out.add(span.with_material("ashlar"))

    if kind == "gate" and rid.endswith(".south"):
        out.add(_south_gatehouse(rid, clear, thick, block_h, g))
    if rid.endswith(".west"):
        # "pinned with iron cramps" — the repair that stopped it moving again.
        for k in range(5):
            cr = M.box(0.09, 0.42, 0.05, 0.006, "iron")
            cr.rotate_z(rng.uniform(-0.25, 0.25))
            cr.translate(-clear * 0.5 - 0.28 + rng.uniform(-0.1, 0.1),
                         1.1 + k * 0.78, -thick * 0.5 - 0.03)
            out.add(cr)
    if kind == "water":
        out.add(_water_gate_extras(rid, clear, thick, spring, rise, g))
    if kind == "postern":
        door = K.plank_door(f"{rid}.door", width=clear - 0.12,
                            height=min(2.30, spring + rise * 0.6))
        door.translate(0, 0.0, thick * 0.5 - 0.12)
        out.add(door)

    out.rotate_y(yaw)
    out.translate(px, g, pz)
    ctx.emit(out)

    # Collision: piers solid, the archway OPEN. The arch springs at `spring`,
    # which is over a 1.75 m player at every gate in the town, so the opening
    # needs no volume at all — which is the point of a gate.
    for sx in (-1, 1):
        ox = sx * (clear * 0.5 + pier_w * 0.5)
        ctx.collider("box",
                     center=(px + tan[0] * ox, g + block_h * 0.5, pz + tan[1] * ox),
                     half=(pier_w * 0.5, block_h * 0.5, thick * 0.5),
                     rot_y=yaw, tag="gate_pier")
    if kind != "postern":
        ctx.entity(rid, "landmark.gate", (px, g, pz), verbs=["inspect"])
    else:
        ctx.entity(rid, "door.postern", (px - nout[0] * (thick * 0.5 + 0.45),
                                         g, pz - nout[1] * (thick * 0.5 + 0.45)),
                   verbs=["open"])


def _south_gatehouse(rid, clear, thick, block_h, g):
    """The ward's chamber over the south arch, and the roof that tops it.

    The south gate is the working one: everything bound for the quest zones
    leaves through it, the carts stage in the yard beside it, and it is the
    only gate with somebody permanently in it. So it is a building rather than
    an opening — a lit window at 09:30, a flue, and a boot-worn sill.
    """
    rng = rng_for(rid, "gatehouse")
    out = M.Group()
    W = clear + 3.10
    D = thick + 2.10
    eaves = 7.80
    body = M.box(W, eaves - block_h + 0.30, D, 0.03, "rubble")
    body.translate(0, (block_h + eaves + 0.30) * 0.5 - 0.15, 0)
    out.add(body)
    band = M.box(W + 0.22, 0.20, D + 0.22, 0.02, "stone")
    band.translate(0, block_h + 0.10, 0)
    out.add(band)
    for sz in (-1, 1):
        for k in (-1, 1):
            w = K.leaded_window(f"{rid}.win{sz}{k}", width=0.68, height=0.92)
            w.rotate_y(0.0 if sz < 0 else math.pi)
            w.translate(k * 1.05, block_h + 1.35, sz * (D * 0.5 - 0.06))
            out.add(w)
    roof = K.gable_roof(D, W, f"{rid}.roof", pitch=0.72, overhang=0.44,
                        tile_mat="terracotta")
    roof.rotate_y(math.pi * 0.5)
    roof.translate(0, eaves + 0.15, 0)
    out.add(roof)
    ch = K.chimney(f"{rid}.flue", height=2.35, section=0.66)
    ch.translate(W * 0.5 - 0.95, eaves + 0.55, 0.30)
    out.add(ch)
    # Residue: the ward's stool and a leaning pole-arm by the arch, and the
    # rut a century of iron tyres has worn into the threshold.
    for k in range(2):
        rut = M.box(0.30, 0.09, D + 0.9, 0.02, "stone")
        rut.translate((-0.72 if k else 0.72) + rng.uniform(-0.05, 0.05), 0.03, 0)
        out.add(rut)
    return out


def _water_gate_extras(rid, clear, thick, spring, rise, g):
    """Boat wicket, the groove nobody ever fitted a portcullis into, the chain.

    TOWN_PLAN J12: a 4.6 m cart arch with a 1.6 m boat wicket cut in the north
    jamb, a portcullis groove that was cut and never used, and 0.8 m of ramp
    inside the arch with a cart-brake groove worn 60 mm into the threshold.
    """
    out = M.Group()
    # The groove: a chase up each jamb that stops dead at the springing with
    # no housing over it, because the portcullis was never made.
    for sx in (-1, 1):
        ch = M.box(0.14, spring - 0.25, 0.16, 0.01, "oak_dark")
        ch.translate(sx * (clear * 0.5 - 0.09), (spring - 0.25) * 0.5,
                     -thick * 0.5 + 0.34)
        out.add(ch)
    # Boat wicket through the north jamb, its sill at the water.
    wick_w, wick_h = 1.60, 2.55
    void = M.box(wick_w, wick_h, thick + 0.2, 0.02, "oak_dark")
    void.translate(-(clear * 0.5 + 1.55 * 0.5), wick_h * 0.5 - 1.35, 0)
    out.add(void)
    wa = K.arch_ring(f"{rid}.wicket", wick_w + 0.06, rise=wick_w * 0.5,
                     ring=0.30, depth=1.50, mat="ashlar")
    wa.translate(-(clear * 0.5 + 1.55 * 0.5), wick_h - 1.35 - wick_w * 0.5, 0)
    out.add(wa)
    # The chain across it. Slack, hung off two ring bolts, and forged — every
    # link a different length (Art Bible §2 forbids uniform machine links).
    for sx in (-1, 1):
        bolt = M.lathe([(0.075, 0.0), (0.095, 0.03), (0.075, 0.06)], 10, "iron")
        bolt.rotate_x(math.pi * 0.5)
        bolt.translate(-(clear * 0.5 + 0.775) + sx * (wick_w * 0.5 - 0.1),
                       0.62, -thick * 0.5 - 0.04)
        out.add(bolt)
    out.add(K.forged_chain(f"{rid}.chain",
                           (-(clear * 0.5 + 0.775) - wick_w * 0.5 + 0.1, 0.62,
                            -thick * 0.5 - 0.06),
                           (-(clear * 0.5 + 0.775) + wick_w * 0.5 - 0.1, 0.62,
                            -thick * 0.5 - 0.06),
                           sag=0.42, link=0.20))
    # Cart-brake groove, 60 mm into the threshold stone.
    for k in (-1, 1):
        gr = M.box(0.11, 0.06, thick + 0.6, 0.01, "stone")
        gr.translate(k * 0.78, 0.03, 0)
        out.add(gr)
    return out


# --- what a five-hundred-year-old boundary accretes -------------------------

def _accretion(ctx, ring, runs, asset_id, rng):
    """Lean-tos against the inner face, and the fire bucket over the thatch.

    Art Bible §7: residue buys more life per unit effort than another 10k
    triangles. On a wall the residue IS the story — a boundary that nobody has
    had to defend for three hundred years is a boundary people build sheds
    against, dry washing on, and store firewood inside.
    """
    walkable = [r for r in runs if r["spec"].get("walkable", True)
                and len(r["st"]) >= 4]
    if not walkable:
        return
    out = M.Group()
    # Four lean-tos, spread round the circuit by arc length so two never land
    # on the same stretch of the Bailey.
    picks = []
    for frac in (0.14, 0.37, 0.61, 0.86):
        s = ring.total * frac
        best = min(walkable, key=lambda r: abs((r["st"][0][0] + r["st"][-1][0]) * 0.5 - s))
        picks.append((best, s))
    for i, (run, s) in enumerate(picks):
        s = min(max(s, run["st"][0][0] + 2.0), run["st"][-1][0] - 2.0)
        x, z, tan, nout = ring.at(s)
        g = float(TERR.height(x, z))
        lid = f"{asset_id}.leanto.{i + 1:02d}"
        lr = rng_for(lid, "leanto")
        w = lr.uniform(2.6, 4.2)
        d = lr.uniform(1.9, 2.6)
        high, low = 2.55, 1.85
        lean = M.Group()
        for sx in (-1, 1):
            post = M.beam(low, 0.14, "oak_weathered", axis="y")
            post.translate(sx * w * 0.5, low * 0.5, -d)
            lean.add(post)
        # Monopitch of riven boards, pitched off the wall face. Each board is
        # a different width, because they came off whatever was going.
        u = -0.02
        while u < w:
            bw = lr.uniform(0.16, 0.30)
            ln = float(np.hypot(d, high - low))
            bd = M.plank(bw, ln, 0.035, 0.004, "timber_grey")
            bd.rotate_z(math.pi * 0.5)
            bd.rotate_x(-math.atan2(high - low, d))
            bd.translate(-w * 0.5 + u + bw * 0.5, (high + low) * 0.5, -d * 0.5)
            lean.add(bd)
            u += bw + 0.012
        if i % 2:
            for k in range(int(w * 3)):
                logl = lr.uniform(0.5, 0.8)
                lg = M.cylinder(lr.uniform(0.045, 0.09), logl, 7, 0.006, "oak")
                lg.rotate_z(math.pi * 0.5)
                lg.translate(lr.uniform(-w * 0.4, w * 0.4),
                             0.07 + (k // 5) * 0.16, -d * lr.uniform(0.25, 0.8))
                lean.add(lg)
        else:
            for k in range(2):
                br = K.barrel(f"{lid}.b{k}")
                br.translate(lr.uniform(-w * 0.4, w * 0.4), 0.0,
                             -d * lr.uniform(0.3, 0.7))
                lean.add(br)
        lean.rotate_y(CIRC.yaw_facing((-nout[0], -nout[1])))
        off = STRETCH_DEFAULT["thick"][0] * 0.5
        lean.translate(x - nout[0] * off, g, z - nout[1] * off)
        out.add(lean)
        ctx.collider("box", center=(x - nout[0] * (off + d * 0.5), g + 0.9,
                                    z - nout[1] * (off + d * 0.5)),
                     half=(w * 0.5, 0.9, d * 0.5),
                     rot_y=math.atan2(nout[0], nout[1]), tag="leanto")

    # TOWN_PLAN slot 30: the last thatched roof inside the wall, "and the
    # reason the wall-walk above it carries a leather fire bucket on a hook."
    s = ring.s_of_point(66.7, 52.7)
    x, z, tan, nout = ring.at(s)
    run = min(walkable, key=lambda r: abs((r["st"][0][0] + r["st"][-1][0]) * 0.5 - s))
    deck = run["deck"]
    hook = M.box(0.05, 0.42, 0.05, 0.008, "iron")
    hook.translate(x - nout[0] * 0.30, deck + 1.02, z - nout[1] * 0.30)
    out.add(hook)
    bucket = M.lathe([(0.0, 0.0), (0.14, 0.02), (0.17, 0.30), (0.16, 0.32)],
                     12, "leather", close_top=False)
    bucket.translate(x - nout[0] * 0.30, deck + 0.52, z - nout[1] * 0.30)
    out.add(bucket)
    ctx.emit(out)
    ctx.entity(f"{asset_id}.firebucket", "prop.bucket",
               (x - nout[0] * 0.30, deck + 0.52, z - nout[1] * 0.30),
               verbs=["inspect"])
