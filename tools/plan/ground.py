#!/usr/bin/env python3
"""Solve the ground to the town plan, and write it into terrain.json.

    python tools/plan/ground.py            # solve and write
    python tools/plan/ground.py --check    # report, change nothing

D-022 recorded that Hearthmere had two terrain models and only one of them was
the ground. D-024 settled which side moves: **the water moves to the layout.**
This tool is that ruling, executed. It owns two blocks of
`content/town/terrain.json`, and nothing else may write them:

`water.channels[*].polygon` — solved from the authored `shoreline`
    The waterline is *not* the polygon edge. A polygon shape carves the ground
    to `bedLevel` inside itself and blends back to the land across `shelf`
    metres outside, so the `h == level` contour sits some way outside the
    polygon — 9.5 m, at the shelf and bed the mere shipped with. That offset
    depends on how high the land beside it happens to be, so it is different at
    every vertex and cannot be eyeballed. Typing the polygon by hand and hoping
    is exactly how the quay ended up 33-42 m from the water.

    So the *waterline* is authored (`shoreline`) and the polygon is solved:
    march out from each shoreline vertex, find where the ground actually
    crosses the water surface, and pull that vertex in by the error. Six
    passes, and the residual is reported.

`pads.generated.list` — one levelled platform per placed venue
    Built from `plan_data.SLOTS`, at the slot's own centre, footprint and
    rotation. They used to be hand-authored against a layout that no longer
    existed: `hm.pad.inn` was 42 m from the inn and `hm.pad.pub` was on the
    far side of the town from the pub. A pad whose id names a building it is
    not under is worse than no pad at all, because `terrain.pad_level(id)`
    answers confidently and wrongly.

    Level is the terrace the slot stands on — evaluated from the hand-authored
    pads and the fall spines only, with the noise and the water left out — so a
    building platform never disagrees with its shelf and never gets dragged
    down by a river it happens to sit beside.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, os.path.join(REPO, "tools/assetgen"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np                                          # noqa: E402

from core import terrain as TR                              # noqa: E402
import plan_data as P                                       # noqa: E402

TERRAIN_JSON = os.path.join(REPO, "content/town/terrain.json")

# Venue pads take the slot footprint plus a working margin: the ground has to
# be flat a little way outside the walls or the plinth steps off the pad.
PAD_MARGIN = 1.6

# How far the solver may move a polygon vertex from its authored waterline.
CAP = 9.0

# Levels a venue pad may not simply inherit from the terrace under it.
LEVEL_OVERRIDE = {
    # The mill stands on a made platform out into the bank so its wheel can
    # reach the channel. Without this the pad takes the natural bank and half
    # the building is under the Emberflow.
    "watermill": -1.55,
}

# Venues whose ground is authored by hand in `pads.list` and must not be
# generated over: the wharf is a masonry platform with its own freeboard, the
# gates sit on the gate flat with the bridge abutments.
SKIP = {"quay", "terrain", "streets", "wall", "market_square", "townhouse",
        "gatehouse", "stalls"}


# ---------------------------------------------------------------------------
# levels
# ---------------------------------------------------------------------------

def terrace_terrain(doc):
    """A Terrain carrying the terraces and the fall, and nothing else.

    No roughness, no water, no venue pads. This is the shelf a venue pad is
    cut into, and it is what `level` must agree with — sampling the real
    height function instead would fold in a decimetre of noise (so the pad is
    not level with its terrace) and, beside the water, the river bed.
    """
    d = json.loads(json.dumps(doc))
    d["roughness"]["amplitudeTown"] = 0.0
    d["roughness"]["amplitudeField"] = 0.0
    d["water"]["channels"] = []
    d["pads"]["list"] = [p for p in d["pads"]["list"]
                         if p["id"].startswith("hm.pad.terrace_")]
    d["pads"]["generated"] = {"list": []}
    d["ramps"]["list"] = []
    return TR.Terrain(d)


# ---------------------------------------------------------------------------
# shoreline solve
# ---------------------------------------------------------------------------

def _outward(poly, i):
    """Unit normal at vertex i pointing OUT of the polygon (toward land)."""
    n = len(poly)
    ax, az = poly[(i - 1) % n]
    bx, bz = poly[(i + 1) % n]
    tx, tz = bx - ax, bz - az
    ln = math.hypot(tx, tz) or 1.0
    nx, nz = -tz / ln, tx / ln
    # Pick the sign that increases the signed distance, i.e. leaves the water.
    px, pz = poly[i]
    s0 = float(TR._sd_polygon(np.array(px + nx), np.array(pz + nz), poly))
    s1 = float(TR._sd_polygon(np.array(px - nx), np.array(pz - nz), poly))
    return (nx, nz) if s0 > s1 else (-nx, -nz)


def _waterline_error(T, x, z, nx, nz, level, reach=22.0):
    """Signed distance from (x,z) to the real waterline along the normal.

    Positive means the water reaches PAST the authored shoreline onto the
    land; negative means it stops short. Measuring along the outward normal is
    what makes this a distance in metres rather than a height in metres, which
    is what a polygon vertex has to be corrected by.

    The crossing taken is the one NEAREST the authored point, not the furthest
    one along the probe. Near the quay the probe passes a wharf, a stair and a
    dredged basin, so "the last wet sample" picks up the far side of the
    harbour and the solve diverges.
    """
    step = 0.1
    n = int(2 * reach / step) + 1
    t = -reach + np.arange(n) * step
    d = T.height(x + nx * t, z + nz * t) - level      # <0 wet, >0 dry
    sign = d >= 0.0
    cross = np.nonzero(sign[1:] != sign[:-1])[0]
    if not len(cross):
        return -reach if sign[0] else reach
    best = cross[int(np.argmin(np.abs(t[cross] + step * 0.5)))]
    # Linear interpolation between the bracketing samples.
    a, b = d[best], d[best + 1]
    f = 0.0 if b == a else a / (a - b)
    return float(t[best] + f * step)


def solve_shoreline(doc, passes=8, verbose=True):
    """Fit every `shoreline`-carrying polygon so the waterline lands on it."""
    level = float(doc["water"]["level"])
    report = []
    for shape in doc["water"]["channels"]:
        want = shape.get("shoreline")
        if not want:
            continue
        want = [(float(a), float(b)) for a, b in want]
        # Normals are taken from the AUTHORED shoreline and held fixed. Taking
        # them from the polygon as it moves lets a vertex at a sharp corner —
        # and the wharf is two right angles — rotate its own correction
        # direction and walk off along the shore.
        nrm = [_outward(want, i) for i in range(len(want))]
        lo, hi = shape.get("solveRange", [0, len(want) - 1])
        # `solveSkip` names vertices whose waterline is pinned by something
        # else and which the solver must leave exactly where they were
        # authored. The three wharf corners are the case: the quay pad is dry
        # to its edge and the harbour basin is cut two metres outside it, so
        # the water's edge there is set by those two shapes whatever the mere
        # polygon does, and letting the solver chase it just ties a knot.
        skip = set(int(k) for k in shape.get("solveSkip", []))
        live = [i for i in range(int(lo), int(hi) + 1) if i not in skip]
        poly = [list(p) for p in want]
        for _ in range(passes):
            shape["polygon"] = [[round(x, 4), round(z, 4)] for x, z in poly]
            T = TR.Terrain(doc)
            for i in live:
                wx, wz = want[i]
                nx, nz = nrm[i]
                err = _waterline_error(T, wx, wz, nx, nz, level)
                # Clamped. An unclamped step runs away wherever the probe
                # finds no crossing at all — a shoreline vertex that has ended
                # up on a made platform, say — and one runaway vertex ties the
                # polygon in a knot that the signed-distance test then reads
                # inside-out.
                err = max(-5.0, min(5.0, err))
                # Water too far inland -> pull the polygon vertex seaward.
                poly[i][0] -= nx * err * 0.85
                poly[i][1] -= nz * err * 0.85
                # Total displacement cap. A vertex whose waterline is pinned
                # by something else — a pad apron it has been authored inside
                # of — never converges, and left uncapped it walks tens of
                # metres inland and ties the polygon in a spike. Capped, it
                # stops beside the thing that is holding it and the residual
                # in the report names the problem instead of hiding it.
                dx = poly[i][0] - wx
                dz = poly[i][1] - wz
                d = math.hypot(dx, dz)
                if d > CAP:
                    poly[i][0] = wx + dx * CAP / d
                    poly[i][1] = wz + dz * CAP / d
        shape["polygon"] = [[round(x, 3), round(z, 3)] for x, z in poly]
        T = TR.Terrain(doc)
        errs = [_waterline_error(T, want[i][0], want[i][1], *nrm[i], level)
                for i in live]
        report.append((shape["id"], errs))
        if verbose:
            a = np.abs(np.array(errs))
            k = int(np.argmax(a))
            print(f"  {shape['id']:22s} {len(live)}/{len(want)} vertices fitted  "
                  f"waterline error mean {a.mean():.2f} m, worst {errs[k]:+.2f} m "
                  f"at ({want[live[k]][0]:g}, {want[live[k]][1]:g})")
    return report


# ---------------------------------------------------------------------------
# venue pads
# ---------------------------------------------------------------------------

def venue_pads(doc):
    """One levelled pad per placed venue, from the plan's slot schedule.

    Only the 24 slots in `plan_data.VENUE_OF_SLOT` get a pad. The other 70 are
    kit buildings that will carry their own plinth; giving each of them a pad
    would triple the cost of `height()` — which is evaluated at ~1.6 M
    vertices per terrain build and at every step the player takes — to flatten
    ground nobody stands a hero building on.
    """
    TT = terrace_terrain(doc)
    water = float(doc["water"]["level"])
    by_n = {}
    for row in P.SLOTS:
        s = dict(zip(FIELDS, row))
        by_n[s["n"]] = s

    seen = {}
    out = []
    for n, venue in sorted(P.VENUE_OF_SLOT.items()):
        if venue in SKIP:
            continue
        s = by_n[n]
        # Second and later placements of a venue take the instance suffix
        # townplan.py gives them, so a generator can ask for the pad under the
        # instance it is building.
        inst = venue if venue not in seen else f"{venue}_{n:02d}"
        seen[venue] = True
        hx = s["w"] * 0.5 + PAD_MARGIN
        hz = s["d"] * 0.5 + PAD_MARGIN
        lvl = LEVEL_OVERRIDE.get(inst)
        if lvl is None:
            lvl = float(TT.height(s["cx"], s["cz"]))
            # No building in Hearthmere stands with its floor within a metre
            # of the mere. A pad that did would be a building the water laps
            # at, and every one of those is a placement bug.
            lvl = max(lvl, water + 1.10)
        out.append({
            "id": f"hm.pad.{inst}",
            "centre": [round(s["cx"], 2), round(s["cz"], 2)],
            "half": [round(hx, 2), round(hz, 2)],
            "level": round(lvl, 3),
            "apron": 1.2,
            # A pad's local +X runs along the slot's frontage, so `half[0]` is
            # half the frontage `w` and `half[1]` is half the depth `d`.
            # A pad's local +X in world is (cos(padRot), -sin(padRot)); the
            # plan's frontage direction is right(rot) = (cos(rot), sin(rot));
            # equating the two gives padRot = -rot. Getting this 90 degrees
            # wrong swaps every pad's width and depth, which on the pub put
            # 3 m of building platform outside the town wall.
            "rotationDeg": round((-s["rot"]) % 360.0, 2),
            "note": f"slot {s['n']:02d} — {s['role']}, fronts {s['street']}",
        })
    return out


FIELDS = ("n", "kit_group", "kit", "cx", "cz", "w", "d", "rot", "storeys",
          "eaves", "ridge", "street", "role", "note")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="report and write nothing")
    args = ap.parse_args()

    with open(TERRAIN_JSON, encoding="utf-8") as f:
        doc = json.load(f)

    print("shoreline solve:")
    solve_shoreline(doc)

    pads = venue_pads(doc)
    doc["pads"]["generated"]["list"] = pads
    print(f"\nvenue pads: {len(pads)} generated")

    T = TR.Terrain(doc)
    lvl = T.water_level()
    bad = []
    for p in pads:
        h = float(T.height(p["centre"][0], p["centre"][1]))
        if abs(h - p["level"]) > 0.005:
            bad.append(f"    {p['id']} level {p['level']:+.2f} but height() "
                       f"gives {h:+.2f}")
    if bad:
        print("  PADS THAT DO NOT TAKE:")
        print("\n".join(bad))
    else:
        print("  every pad centre returns its own level to 5 mm")

    # The invariant D-024 keeps: ONE water surface, and a bed under all of it.
    # Checked per shape, at the points that shape actually owns (weight 1),
    # because a shape's blend legitimately climbs out onto dry land.
    print("\nbed clearance (surface is "
          f"{lvl:+.2f} m; every body must have its bed below it):")
    g = np.arange(-260.0, 260.5, 1.5)
    GX, GZ = np.meshgrid(g, g, indexing="ij")
    X, Z = GX.ravel(), GZ.ravel()
    H = T.height(X, Z)
    ok = True
    for shape in doc["water"]["channels"]:
        if "path" in shape:
            d = TR._sd_polyline(X, Z, [(float(a), float(b)) for a, b in shape["path"]])
            core = d <= float(shape["halfWidth"])
        else:
            sd = TR._sd_polygon(X, Z, [(float(a), float(b)) for a, b in shape["polygon"]])
            core = sd <= 0.0
        if not core.any():
            print(f"  {shape['id']:22s} claims no ground at all")
            ok = False
            continue
        # A pad applied after the water legitimately stands ground back up
        # inside a channel — that is what a bridge abutment, a mill platform
        # and a quay ARE. Those are excluded and named; anything else standing
        # out of its own water body is a defect.
        claimed = np.zeros(np.shape(X), bool)
        who = set()
        for p in T.pads:
            w = p.weight(X, Z) > 0.5
            hit = w & core & (H > lvl)
            if hit.any():
                who.add(p.id)
                claimed |= w
        sel = core & (~claimed)
        if not sel.any():
            print(f"  {shape['id']:22s} entirely under made ground")
            continue
        hi = float(H[sel].max())
        flag = "" if hi < lvl else "   *** BED ABOVE THE SURFACE ***"
        ok = ok and hi < lvl
        print(f"  {shape['id']:22s} bed {H[sel].min():+.2f} .. {hi:+.2f} m, "
              f"deepest {lvl - float(H[sel].min()):.2f} m, "
              f"shallowest {lvl - hi:.2f} m{flag}")
        if who:
            print(f"  {'':22s}   made ground inside it: {', '.join(sorted(who))}")
    if not ok:
        print("  FAIL: a water body has natural ground standing out of it")

    if args.check:
        print("\n--check: nothing written")
        return
    with open(TERRAIN_JSON, "w", encoding="utf-8") as f:
        f.write(dumps(doc) + "\n")
    print(f"\nwrote {os.path.relpath(TERRAIN_JSON, REPO)}")


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------

def _num(v):
    if isinstance(v, float) and v == int(v) and abs(v) < 1e15:
        return f"{v:.1f}"
    return json.dumps(v, ensure_ascii=False)


def _flat(v):
    """True if `v` is a list of numbers, or a list of lists of numbers."""
    if not isinstance(v, list) or not v:
        return False
    if all(isinstance(e, (int, float)) and not isinstance(e, bool) for e in v):
        return True
    return all(isinstance(e, list) and e and
               all(isinstance(q, (int, float)) and not isinstance(q, bool) for q in e)
               for e in v)


def dumps(o, indent=0):
    """`json.dumps(indent=2)` but coordinate arrays stay on one line.

    terrain.json is read by people. Expanded, a 26-vertex polygon is 78 lines
    of one number each and the file goes from 300 lines to 1,800 — which turns
    every regeneration into an unreviewable diff and hides the authored
    comments the file exists to carry.
    """
    pad = " " * indent
    inner = " " * (indent + 2)
    if isinstance(o, dict):
        if not o:
            return "{}"
        body = ",\n".join(f"{inner}{json.dumps(k)}: {dumps(v, indent + 2)}"
                          for k, v in o.items())
        return "{\n" + body + "\n" + pad + "}"
    if isinstance(o, list):
        if not o:
            return "[]"
        if _flat(o):
            if all(isinstance(e, list) for e in o):
                items = ["[" + ", ".join(_num(q) for q in e) + "]" for e in o]
            else:
                items = [_num(e) for e in o]
            one = "[" + ", ".join(items) + "]"
            if len(one) + indent <= 110:
                return one
            # Wrap long coordinate lists at ~100 columns, four pairs a line.
            lines, cur = [], ""
            for it in items:
                add = (", " if cur else "") + it
                if cur and len(inner) + len(cur) + len(add) > 100:
                    lines.append(inner + cur + ",")
                    cur = it
                else:
                    cur += add
            lines.append(inner + cur)
            return "[\n" + "\n".join(lines) + "\n" + pad + "]"
        body = ",\n".join(inner + dumps(e, indent + 2) for e in o)
        return "[\n" + body + "\n" + pad + "]"
    if isinstance(o, float):
        return _num(o)
    return json.dumps(o, ensure_ascii=False)


if __name__ == "__main__":
    main()
