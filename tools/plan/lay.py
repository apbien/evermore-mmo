#!/usr/bin/env python3
"""Lay the building slots out along their frontages, then write the result
back into `plan_data.py` as literal world coordinates.

    python tools/plan/lay.py --dry
    python tools/plan/lay.py

A burgage plot is not "a rectangle at (x,z)". It is *so many metres of
frontage, at such a point along such a street, on such a side*, and its depth
runs back from there. So that is how the plan is authored here: a hint point
near where the plot belongs, a street, and a side. This module snaps the hint
to the street's centreline, packs neighbouring plots along the frontage until
they stop overlapping (a 1-D problem, which is why it converges exactly), sets
the building's setback from the kerb and its rotation so it faces the street,
and emits world coordinates.

Composition-critical slots are given literal coordinates in PINS and are never
laid out — the church, its tower, the lychgate, the three institutions on the
market place, the two frontages that form the arrival frame's jambs, and
everything outside the wall.

Deterministic. Run it twice, get the same plan.
"""

from __future__ import annotations

import argparse
import io
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import plan_data as P    # noqa: E402

SETBACK = 0.7            # footway between the kerb line and the building line
GAP = 1.1                # eavesdrip gap between neighbouring plots

# --- fixed by composition, never laid out ---------------------------------
PINS = {
    1:  (-34.0, -26.0,  90),   # Grey Heron Inn, market place west frontage
    2:  (-33.0,   0.0,  90),   # Adventurer's Guild, ditto
    3:  (-16.0,   9.0,  60),   # Moot Hall, free-standing in the market place
    4:  (-19.0,  23.5,   0),   # shop row: general store
    5:  (-11.5,  23.5,   0),   #           apothecary
    6:  ( -5.5,  23.5,   0),   #           tailor
    7:  (-21.5, -33.0, 180),   # market place north frontage: chophouse
    8:  (-12.0, -33.0, 180),
    9:  ( -4.5, -33.0, 180),
    11: ( 44.0,  -0.5, 270),   # CHURCH OF SUMMONING
    12: ( 35.8, -14.3, 270),   # its tower
    13: ( 50.0,  15.5, 270),   # parsonage, inside the churchyard
    15: ( 48.0, -18.0, 180),   # song school
    16: ( 57.0, -19.0, 180),   # sexton
    17: ( 24.0,  -0.5, 270),   # lychgate, at the foot of the perron
    18: ( 57.0,  14.0,  90),   # charnel house, on the churchyard's east wall
    21: ( 20.5,  12.0,   0),   # confectioner - south jamb of the arrival frame
    43: (-33.0,  51.0,  60),   # BLACKSMITH
    54: ( 10.8, -45.4, 257),   # the last infill plot in the north quarter
    52: ( 68.0,  66.0, 225),   # sties, outside on the midden
    61: ( 48.0, -44.0, 315),   # customs house, square on to the Water Gate
    67: ( 52.0, -31.0, 340),   # rope house
    71: (-30.0, -48.0,  90),   # farrier, behind the stable yard
    72: ( 19.0, -70.0, 180),   # THE FERRYMAN'S LAMP
    77: (-49.0, -79.5, 150),   # watermill, outside on the leat
    93: ( 86.0, -16.0, 225),   # tannery, outside and downstream
    94: ( 62.0, -57.0,  42),   # treadwheel crane, on the wharf
}

# --- everything else: (street, side, hint x, hint z) ----------------------
# side +1 = right of travel along the path, -1 = left.
LAY = {
    # Ford Road, east side (-1) then west side (+1)
    10: ("ford_road", -1, +14, -20), 22: ("ford_road", -1, +16, +36),
    39: ("ford_road", -1, +19, +56), 38: ("ford_road", -1, +18, +64),
    70: ("ford_road", +1, -16, -44),
    23: ("ford_road", +1, -5, +33), 24: ("ford_road", +1, -5, +40),
    25: ("ford_road", +1, -6, +47),
    # Mere Street, south side (-1) and north side (+1)
    75: ("mere_street", -1, -52, +2),  88: ("mere_street", -1, -46, +3),
    89: ("mere_street", -1, -58, +4),
    74: ("mere_street", +1, -52, -20), 85: ("mere_street", +1, -42, -20),
    86: ("mere_street", +1, -54, -21), 83: ("mere_street", +1, -66, -21),
    # Wharf Lane
    73: ("wharf_lane", -1, +7, -70),   60: ("wharf_lane", -1, +30, -67),
    69: ("wharf_lane", +1, +8, -57),   65: ("wharf_lane", +1, +19, -56),
    64: ("wharf_lane", +1, +34, -54),
    # Mill Lane, south side
    81: ("mill_lane", -1, -14, -60), 79: ("mill_lane", -1, -26, -65),
    78: ("mill_lane", -1, -38, -70),
    # Kirkgate, churchyard side (-1) and town side (+1)
    14: ("kirkgate", -1, +35, -30), 62: ("kirkgate", -1, +35, -52),
    68: ("kirkgate", +1, +19, -45), 20: ("kirkgate", +1, +19, -35),
    19: ("kirkgate", +1, +19, -25),
    # Bakers' Row, south side
    32: ("bakers_row", +1, +20, +31), 33: ("bakers_row", +1, +33, +32),
    34: ("bakers_row", +1, +47, +33), 35: ("bakers_row", +1, +58, +32),
    # Smiths' Lane, south side
    40: ("smiths_lane", -1, -9, +63),
    # Well Lane
    90: ("well_lane", -1, -38, +25), 91: ("well_lane", -1, -52, +28),
    48: ("well_lane", +1, -52, +12),
    # Sty Lane, south side
    49: ("sty_lane", +1, +16, +53), 53: ("sty_lane", +1, +26, +53),
    37: ("sty_lane", +1, +34, +53), 36: ("sty_lane", +1, +44, +51),
    # Tenter Lane, west side
    29: ("tenter_lane", +1, -36, +30),
    # Bell Alley, west side
    26: ("bell_alley", +1, -26, +34), 27: ("bell_alley", +1, -26, +43),
    28: ("bell_alley", +1, -26, +50),
    # The Bailey, town side, clockwise from the mill quarter. It skips the
    # stretch between z=-22 and z=+4, where Mere Street comes to the West
    # Gate and the two lanes share one corridor.
    42: ("the_bailey", -1, -52, +58), 63: ("the_bailey", -1, +26, +72),
    82: ("the_bailey", -1, -56, -56), 76: ("the_bailey", -1, -63, -49),
    80: ("the_bailey", -1, -68, -41), 84: ("the_bailey", -1, -72, -32),
    87: ("the_bailey", -1, -75, +6),  92: ("the_bailey", -1, -74, +20),
    47: ("the_bailey", -1, -71, +32), 44: ("the_bailey", -1, -66, +44),
    66: ("the_bailey", -1, -60, +54), 46: ("the_bailey", -1, -52, +62),
    45: ("the_bailey", -1, -42, +68), 41: ("the_bailey", -1, -30, +72),
    30: ("the_bailey", -1, -18, +74), 31: ("the_bailey", -1, -8, +74),
    59: ("the_bailey", -1, +4, +74),
    58: ("the_bailey", -1, +40, +64), 51: ("the_bailey", -1, +54, +54),
    50: ("the_bailey", -1, +60, +48),
    57: ("the_bailey", -1, +72, +12), 56: ("the_bailey", -1, +72, +2),
    55: ("the_bailey", -1, +72, -6),
}

STREETS = {s["id"]: s for s in P.STREETS}


def cum(path):
    out = [0.0]
    for a, b in zip(path, path[1:]):
        out.append(out[-1] + math.dist(a, b))
    return out


def at(path, cs, s):
    """(point, unit tangent) at arclength s."""
    s = max(0.0, min(cs[-1], s))
    for i in range(len(path) - 1):
        if cs[i] <= s <= cs[i + 1]:
            L = cs[i + 1] - cs[i]
            u = 0.0 if L < 1e-9 else (s - cs[i]) / L
            a, b = path[i], path[i + 1]
            return ((a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u),
                    ((b[0] - a[0]) / max(L, 1e-9), (b[1] - a[1]) / max(L, 1e-9)))
    return path[-1], (0.0, 1.0)


def frontage(sid, side, s, w, d):
    """Centre and facing for a plot of w x d fronting street `sid` at station s."""
    st = STREETS[sid]
    (qx, qz), (tx, tz) = at(st["path"], cum(st["path"]), s)
    nlx, nlz = tz, -tx
    nx, nz = (nlx, nlz) if side < 0 else (-nlx, -nlz)
    off = st["width"] / 2 + st["verge"] + SETBACK + d / 2
    rot = math.degrees(math.atan2(-nx, nz)) % 360
    return round(qx + nx * off, 1), round(qz + nz * off, 1), round(rot)


# --------------------------------------------------------------------------
# The placer
# --------------------------------------------------------------------------
# Every plot in a real town is on a frontage, so the search space is not the
# plane: it is (street, side, distance along the street). This walks that
# space at 1 m resolution, takes the widest plots first (they have the least
# choice), and gives each the valid frontage nearest to the district it
# belongs in. Greedy, deterministic, and it cannot produce a building that
# overlaps another or stands in a carriageway, because those are the
# validity tests.


def candidates():
    out = []
    for st in P.STREETS:
        cs = cum(st["path"])
        n = max(2, int(cs[-1] * 2))
        for i in range(n + 1):
            for side in (-1, +1):
                out.append((st["id"], side, min(i * 0.5, cs[-1])))
    return out


CAND = None


def valid(n, poly, placed, want_inside, over_water):
    import townplan as T
    for c in poly:
        if abs(c[0]) > P.EXTENT - 1 or abs(c[1]) > P.EXTENT - 1:
            return False
    if not over_water:
        # Asked of the HEIGHT FIELD, not of a polygon typed beside it. The
        # plan's own water outline is gone (D-024): content/town/terrain.json
        # is the ground, the water is the ground, and the placer has to test
        # against the same function the checker and the client evaluate or it
        # will happily lay a plot on a river again.
        for c in poly:
            if P.height(c[0], c[1]) < P.WATER_Y:
                return False
    cx = sum(c[0] for c in poly) / 4.0
    cz = sum(c[1] for c in poly) / 4.0
    if T.point_in_poly(cx, cz, P.WALL) != want_inside:
        return False
    if n != 3:                                   # only the moot hall stands in it
        for c in list(poly) + [(cx, cz)]:
            if T.point_in_poly(c[0], c[1], P.SQUARE):
                return False
    for st in P.STREETS:
        if st.get("outside") and want_inside:
            continue
        need = st["width"] / 2 + min(st["verge"], 0.6) + 0.15
        if T.poly_path_dist(poly, st["path"]) < need:
            return False
    for q in placed.values():
        if T.sat_overlap(poly, q) > 1e-9:
            return False
    for (ex, ez), (px, pz) in RAYS:
        if T.point_in_poly(px, pz, poly):
            continue
        if T.seg_hits_poly((ex, ez), (px, pz), poly):
            return False
    return True


RAYS = []


def place_all():
    import townplan as T
    global CAND, RAYS
    CAND = candidates()
    RAYS = [((T.ALTAR[0], T.ALTAR[1]), a[1]) for a in T.ANCHORS]
    rows = {r[0]: r for r in P.SLOTS}
    result, placed = {}, {}

    for n, (x, z, rot) in PINS.items():
        r = rows[n]
        result[n] = (x, z, rot)
        placed[n] = T.corners(dict(cx=x, cz=z, w=r[5], d=r[6], rot=rot))

    # Work street by street, and along each street in order, so a street's own
    # plots get first claim on its frontage. Doing it by size instead lets a
    # warehouse take a cottage lane on the far side of town, which is how the
    # districts came apart the first time this was written.
    # Frontage is claimed in order of how much the town cares about it. The
    # Bailey is last because it is the leftover lane inside the wall and its
    # plots are the ones that can go anywhere.
    PRIORITY = ["ford_road", "mere_street", "wharf_lane", "kirkgate",
                "bakers_row", "mill_lane", "sty_lane", "smiths_lane",
                "well_lane", "tenter_lane", "bell_alley", "the_bailey"]

    def key(n):
        sid, side, hx, hz = LAY[n]
        st = STREETS[sid]
        return (PRIORITY.index(sid) if sid in PRIORITY else 99,
                side, project(st["path"], cum(st["path"]), hx, hz), n)

    homeless = []
    for n in sorted((k for k in rows if k not in PINS), key=key):
        r = rows[n]
        w, d = r[5], r[6]
        pref, side_pref, hx, hz = LAY[n]
        chosen = None
        # phase 1: the authored side of the authored street
        # phase 2: the other side of it
        # phase 3: anywhere, because a plot with no frontage is not a plot
        for phase in (1, 2, 3):
            best, bestcost = None, 1e18
            for sid, side, sta in CAND:
                if phase == 1 and (sid != pref or side != side_pref):
                    continue
                if phase == 2 and sid != pref:
                    continue
                if STREETS[sid].get("outside"):
                    continue
                cx, cz, rot = frontage(sid, side, sta, w, d)
                cost = (cx - hx) ** 2 + (cz - hz) ** 2
                if cost >= bestcost:
                    continue
                poly = T.corners(dict(cx=cx, cz=cz, w=w, d=d, rot=rot))
                if not valid(n, poly, placed, True, False):
                    continue
                best, bestcost = (cx, cz, rot), cost
                bestpoly, bestst = poly, (sid, side)
            if best:
                chosen = (best, bestpoly, bestst)
                break
        if chosen is None:
            homeless.append(n)
            result[n] = (r[3], r[4], r[7])
            continue
        result[n], placed[n], FRONTS[n] = chosen[0], chosen[1], chosen[2]
    return result, homeless


def project(path, cs, x, z):
    best, bs = 1e9, 0.0
    for i in range(len(path) - 1):
        a, b = path[i], path[i + 1]
        ex, ez = b[0] - a[0], b[1] - a[1]
        L2 = ex * ex + ez * ez
        u = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((x - a[0]) * ex + (z - a[1]) * ez) / L2))
        d = math.hypot(x - (a[0] + u * ex), z - (a[1] + u * ez))
        if d < best:
            best, bs = d, cs[i] + u * math.sqrt(L2)
    return bs


FRONTS = {}
ROW = re.compile(r'(S\(\s*(\d+),\s*"[^"]*",\s*"[^"]*",\s*)'
                 r'([-+]?[\d.]+),\s*([-+]?[\d.]+),\s*([\d.]+),\s*([\d.]+),\s*(-?\d+),')


def rewrite(result):
    path = os.path.join(HERE, "plan_data.py")
    src = io.open(path, encoding="utf-8").read()

    def sub(m):
        n = int(m.group(2))
        if n not in result:
            return m.group(0)
        x, z, rot = result[n]
        return (f"{m.group(1)}{x:+.1f}, {z:+.1f}, "
                f"{float(m.group(5)):.1f}, {float(m.group(6)):.1f}, {int(rot)},")
    io.open(path, "w", encoding="utf-8").write(ROW.sub(sub, src))


def rewrite_streets(fronts):
    """Record which street each plot actually ended up fronting."""
    path = os.path.join(HERE, "plan_data.py")
    src = io.open(path, encoding="utf-8").read()
    rows = {r[0]: r for r in P.SLOTS}
    for n, (sid, side) in fronts.items():
        old = rows[n][11]
        if old == sid:
            continue
        src = re.sub(r'(S\(%d, "%s",.*?)"%s"' % (n, rows[n][1], old),
                     r'\1"%s"' % sid, src, count=1, flags=re.S)
    io.open(path, "w", encoding="utf-8").write(src)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    result, homeless = place_all()
    print(f"{len(result)} slots placed, {len(homeless)} with no valid frontage"
          f"{': ' + ', '.join(str(n) for n in homeless) if homeless else ''}")
    if not args.dry:
        rewrite(result)
        rewrite_streets(FRONTS)
        print("rewrote tools/plan/plan_data.py")


if __name__ == "__main__":
    sys.exit(main())
