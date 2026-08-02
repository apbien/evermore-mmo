"""The modular kit venue: every filler mass in Hearthmere, in one module.

`content/town/hearthmere.json` carries 94 `buildingSlots[]`. Nine are hero
venues and twenty-two are authored secondaries, each with its own generator.
The remaining sixty-three — cottages, townhouses, workshops, sheds and
warehouses — are this module, and they are what turns a set of landmarks into
a town (Directive §5: 75-95 masses, no two visibly identical).

They are not a single mesh repeated. Each slot is planned from its own id, so
its ground, storey heights, framing, roof pitch, covering, openings, chimneys,
residue and its one deliberate defect are all seeded from `hm.slot.NN.name` and
reproduce exactly on every build. Slots that touch are built as terraces
sharing one party wall, so a row reads as a street rather than as detached
models standing in a line.

The building system itself lives in `core/building.py` and `core/roof.py`; this
module is only the schedule reader. That split is deliberate — the authored
venues want the same walls, roofs and party walls, and a kit that lived inside
one venue module could not be reused by them.
"""

from __future__ import annotations

import json
import os

import numpy as np

from core import building as BLD
from core import mesh as M
from core.mathx import rng_for
from core.venue import VenueContext, REPO

NAME = "townhouse"

TOWN = os.path.join(REPO, "content/town/hearthmere.json")

# The kits this module owns. Everything else in `buildingSlots[]` belongs to an
# authored venue; a slot with a `venue` field is that venue's business even
# when its kit is one of these (the shop row's three units, the church's
# annexes), because a hero building's mass is authored, not generated.
#
# `warehouse` came out of this list. Seven of the schedule's slots carry it and
# they were being built here as anonymous filler, which is why not one of them
# had a taking-in door, a hoist beam or a loading dock — the three things that
# make a shed a warehouse. `venues/warehouse.py` owns them now, whether or not
# they carry a `venue` field.
KITS = ("townhouse", "cottage", "shed", "workshop")

# Two footprint edges this close, overlapping this far, are a party wall.
# 0.45 m is chosen from the data: real terraces in the schedule sit 0.0-0.35 m
# apart, and the next-closest pair of independent buildings is 0.67 m.
PARTY_GAP = 0.45
PARTY_OVERLAP = 2.0


def slots(town=None):
    doc = town or json.load(open(TOWN, encoding="utf-8"))
    return [s for s in doc.get("buildingSlots", [])
            if not s.get("venue") and s.get("kit") in KITS]


CELLS = sorted({c for s in slots() for c in s.get("cells", [])})


# ---------------------------------------------------------------------------
# Terraces
# ---------------------------------------------------------------------------

def _edges(fp):
    pts = fp.rect()
    return [(np.asarray(pts[i], float), np.asarray(pts[(i + 1) % 4], float))
            for i in range(4)]


def _edge_pair(ea, eb):
    """(gap, overlap, mid-line) between two footprint edges, or None.

    The mid-line is the point of the whole exercise: a party wall is built on
    it, not on either neighbour's face, and it spans only the stretch the two
    edges actually share. Returning it here is what lets `core.building` size
    the wall from the MEASURED gap — `gap + 2 x bearing` — instead of a
    constant 0.36 m that left an open slot on six of nine terraces.
    """
    a0, a1 = ea
    b0, b1 = eb
    da = a1 - a0
    db = b1 - b0
    la, lb = np.linalg.norm(da), np.linalg.norm(db)
    if la < 1e-6 or lb < 1e-6:
        return None
    ua, ub = da / la, db / lb
    if abs(float(np.dot(ua, ub))) < 0.94:
        return None
    n = np.array([-ua[1], ua[0]])
    off = float(np.dot(b0 - a0, n)) * 0.5 + float(np.dot(b1 - a0, n)) * 0.5
    gap = abs(off)
    t0 = float(np.dot(b0 - a0, ua))
    t1 = float(np.dot(b1 - a0, ua))
    lo, hi = max(0.0, min(t0, t1)), min(la, max(t0, t1))
    if hi <= lo:
        return None
    # Half-way between the two faces, over the shared stretch only.
    m0 = a0 + ua * lo + n * (off * 0.5)
    m1 = a0 + ua * hi + n * (off * 0.5)
    return gap, hi - lo, ((float(m0[0]), float(m0[1])), (float(m1[0]), float(m1[1])))


def find_terraces(plans):
    """Mark every pair of slots that share a wall.

    The lower slot number owns the shared wall and builds it; the other builds
    nothing on that edge. Both suppress their eaves overhang there, and the
    roof closure code already skips a `party` edge — so the join is closed by
    the wall itself, standing proud of both roofs with a coping.
    """
    pairs = []
    ids = list(plans)
    for i, ka in enumerate(ids):
        pa = plans[ka]
        fa = pa["footprint"]
        ea = _edges(fa)
        for kb in ids[i + 1:]:
            pb = plans[kb]
            fb = pb["footprint"]
            if np.hypot(fa.centre[0] - fb.centre[0],
                        fa.centre[1] - fb.centre[1]) > (fa.w + fa.d + fb.w + fb.d) * 0.5:
                continue
            eb = _edges(fb)
            best = None
            for ia, sa in enumerate(ea):
                for ib, sb in enumerate(eb):
                    r = _edge_pair(sa, sb)
                    if r is None:
                        continue
                    gap, ov, line = r
                    if gap > PARTY_GAP or ov < PARTY_OVERLAP:
                        continue
                    if best is None or gap < best[0]:
                        best = (gap, ov, ia, ib, line)
            if best is None:
                continue
            gap, ov, ia, ib, line = best
            owner = ka < kb
            pa["party"][ia] = {"other": kb, "owner": owner, "gap": gap,
                               "overlap": ov, "line": line,
                               "ridge_y": pb["ridge_y"], "pitch": pb["pitch"],
                               "plate_y": pb["plate_y"]}
            pb["party"][ib] = {"other": ka, "owner": not owner, "gap": gap,
                               "overlap": ov, "line": line,
                               "ridge_y": pa["ridge_y"], "pitch": pa["pitch"],
                               "plate_y": pa["plate_y"]}
            pairs.append((ka, kb, round(gap, 3), round(ov, 2)))
    return pairs


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build(ctx: VenueContext):
    rows = slots()
    plans = {}
    for s in rows:
        plans[s["id"]] = BLD.plan_building(s)

    pairs = find_terraces(plans)

    stats = []
    for s in rows:
        plan = plans[s["id"]]
        before = ctx._tri_total
        BLD.build_building(ctx, s, plan=plan)
        stats.append((s["id"], plan["style"]["name"], ctx._tri_total - before,
                      plan["floor_y"], plan["plinth_h"], plan["ridge_y"],
                      plan.get("defect")))

    # Party walls come AFTER every building, not inside the loop: the profile of
    # a shared wall is the upper envelope of the two roofs it separates, so it
    # cannot be built while either is still a guess. Building it early is what
    # made the wall approximate its neighbour as a gable at their pitch and
    # raise a fake 9.31 m party gable through slot 10's 5.82 m hipped eaves.
    BLD.build_party_walls(ctx, plans)

    # NO authored LOD chain here, deliberately. `core.building.building_lods`
    # is the rule for generating one and other venues are welcome to it, but a
    # filler building must not use it, for two reasons measured on this venue:
    #
    #  1. `ctx.lod(mesh_id, ...)` on an id that nothing instanced exports a
    #     STANDALONE node (see VenueContext.lod). `build_building` has already
    #     emitted the same building into its cell batch, so the building ships
    #     twice, coincident. That is what was happening: 8 buildings, 73,514
    #     duplicate triangles, z-fighting on every surface, plus 226 duplicate
    #     window units left on the venue by the levels' `ctx.instance` calls.
    #     `emit=False` now means "touch the context for nothing", so the second
    #     half of that cannot recur — but the first half is inherent to asking
    #     for both, so a building gets one or the other and this one takes the
    #     cell batch.
    #  2. A standalone node opts the building OUT of per-cell batching, which
    #     costs a draw call per building per level. Cell batching is what keeps
    #     63 buildings inside the Directive §7 budget; the automatic decimator
    #     in `VenueContext._levels` already gives them LOD1-3, and no filler
    #     mass has a silhouette the vertex clusterer destroys.
    #
    # An authored chain earns its draw call on a hero mass — the guild tower,
    # the church spire — where the ridge or the finial has to survive 100 m.

    _report(stats, pairs)


def _report(stats, pairs):
    tot = sum(t for _i, _s, t, *_r in stats)
    print(f"      {len(stats)} buildings, {tot:,} tris "
          f"({tot // max(1, len(stats)):,} mean), {len(pairs)} party walls")
    worst = sorted(stats, key=lambda r: -r[2])[:3]
    for i, st, t, fy, ph, ry, df in worst:
        print(f"        {i:<26s} {st:<20s} {t:6,d} tris  floor {fy:6.2f}  "
              f"plinth {ph:4.2f}  ridge {ry:6.2f}  [{df}]")
    deep = [r for r in stats if r[4] > 0.9]
    if deep:
        print(f"        {len(deep)} on an underbuilding (plinth > 0.9 m): "
              + ", ".join(r[0].split('.')[-1] for r in deep[:6]))
