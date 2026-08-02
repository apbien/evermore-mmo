#!/usr/bin/env python3
"""Hearthmere v2 master plan — checker and generator.

    python tools/plan/townplan.py --check     # geometry conformance only
    python tools/plan/townplan.py             # check, then write all outputs

Writes:
    docs/areas/hearthmere/plan/hearthmere-plan.svg     1:200 top-down plan
    docs/areas/hearthmere/plan/schedule.md             the building schedule, as a table
    content/town/hearthmere.json      the v2 town record

Nothing here is decorative. Every check exists because a defect of that exact
shape shipped in v1: a venue whose bounding box sealed the main street, masses
that interpenetrated, geometry that assumed y=0. A plan that passes this is
not automatically a good plan, but a plan that fails it is definitely a broken
one and no builder agent should be handed a row from it.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plan_data as P  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
SVG_OUT = os.path.join(REPO, "docs/areas/hearthmere/plan/hearthmere-plan.svg")
MD_OUT = os.path.join(REPO, "docs/areas/hearthmere/plan/schedule.md")
DOC_OUT = os.path.join(REPO, "docs/areas/hearthmere/TOWN_PLAN.md")
TOWN_OUT = os.path.join(REPO, "content/town/hearthmere.json")
TERRAIN_IN = os.path.join(REPO, "content/town/terrain.json")

with open(TERRAIN_IN, encoding="utf-8") as _f:
    TERRAIN_DOC = json.load(_f)

FIELDS = ("n kit_group kit cx cz w d rot storeys eaves ridge street role note").split()

NL = chr(10)

problems: list[str] = []
notes: list[str] = []


def fail(m):
    problems.append(m)


# --------------------------------------------------------------------------
# geometry helpers
# --------------------------------------------------------------------------

def fwd(rot):
    r = math.radians(rot)
    return (math.sin(r), -math.cos(r))


def right(rot):
    r = math.radians(rot)
    return (math.cos(r), math.sin(r))


def corners(s):
    """Four world-space corners, front-left, front-right, back-right, back-left."""
    fx, fz = fwd(s["rot"])
    rx, rz = right(s["rot"])
    hw, hd = s["w"] / 2.0, s["d"] / 2.0
    cx, cz = s["cx"], s["cz"]
    f = (cx + fx * hd, cz + fz * hd)
    b = (cx - fx * hd, cz - fz * hd)
    return [(f[0] - rx * hw, f[1] - rz * hw),
            (f[0] + rx * hw, f[1] + rz * hw),
            (b[0] + rx * hw, b[1] + rz * hw),
            (b[0] - rx * hw, b[1] - rz * hw)]


def poly_axes(poly):
    ax = []
    for i in range(len(poly)):
        x0, z0 = poly[i]
        x1, z1 = poly[(i + 1) % len(poly)]
        ex, ez = x1 - x0, z1 - z0
        n = math.hypot(ex, ez)
        if n > 1e-9:
            ax.append((-ez / n, ex / n))
    return ax


def sat_overlap(a, b):
    """Convex-polygon overlap depth (0 if separated)."""
    best = 1e9
    for ax, az in poly_axes(a) + poly_axes(b):
        pa = [x * ax + z * az for x, z in a]
        pb = [x * ax + z * az for x, z in b]
        d = min(max(pa) - min(pb), max(pb) - min(pa))
        if d <= 0:
            return 0.0
        best = min(best, d)
    return best


def seg_dist(px, pz, ax, az, bx, bz):
    ex, ez = bx - ax, bz - az
    L2 = ex * ex + ez * ez
    t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((px - ax) * ex + (pz - az) * ez) / L2))
    return math.hypot(px - (ax + t * ex), pz - (az + t * ez))


def path_dist(px, pz, path):
    return min(seg_dist(px, pz, a[0], a[1], b[0], b[1]) for a, b in zip(path, path[1:]))


def poly_path_dist(poly, path):
    """Min distance from a polygon (edges sampled) to a polyline."""
    best = 1e9
    for i in range(len(poly)):
        x0, z0 = poly[i]
        x1, z1 = poly[(i + 1) % len(poly)]
        for k in range(21):
            t = k / 20.0
            best = min(best, path_dist(x0 + (x1 - x0) * t, z0 + (z1 - z0) * t, path))
    return best


def point_in_poly(px, pz, poly):
    inside = False
    n = len(poly)
    for i in range(n):
        x0, z0 = poly[i]
        x1, z1 = poly[(i + 1) % n]
        if (z0 > pz) != (z1 > pz):
            xi = x0 + (pz - z0) * (x1 - x0) / (z1 - z0)
            if px < xi:
                inside = not inside
    return inside


def seg_hits_poly(a, b, poly):
    """Does segment a-b cross convex polygon `poly`?"""
    if point_in_poly(a[0], a[1], poly) or point_in_poly(b[0], b[1], poly):
        return True
    for i in range(len(poly)):
        p, q = poly[i], poly[(i + 1) % len(poly)]

        def cr(o, u, v):
            return (u[0] - o[0]) * (v[1] - o[1]) - (u[1] - o[1]) * (v[0] - o[0])
        d1, d2 = cr(a, b, p), cr(a, b, q)
        d3, d4 = cr(p, q, a), cr(p, q, b)
        if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)):
            return True
    return False


def cells_of(poly):
    xs = [p[0] for p in poly]
    zs = [p[1] for p in poly]
    out = []
    x = math.floor(min(xs) / P.CELL) * P.CELL
    while x < max(xs):
        z = math.floor(min(zs) / P.CELL) * P.CELL
        while z < max(zs):
            out.append(P.cell_of(x + 0.1, z + 0.1))
            z += P.CELL
        x += P.CELL
    return sorted(set(out))


# --------------------------------------------------------------------------
# build the slot records
# --------------------------------------------------------------------------

def build_slots():
    out = []
    for row in P.SLOTS:
        s = dict(zip(FIELDS, row))
        s["poly"] = corners(s)
        s["cells"] = cells_of(s["poly"])
        s["outside"] = not point_in_poly(s["cx"], s["cz"], P.WALL)
        s["ground"] = round(P.height(s["cx"], s["cz"]), 2)
        s["id"] = f"hm.slot.{s['n']:02d}.{s['kit_group']}"
        out.append(s)
    return out


STREETS = {st["id"]: st for st in P.STREETS}


# --------------------------------------------------------------------------
# checks
# --------------------------------------------------------------------------

def check(slots):
    n = len(slots)
    if not (75 <= n <= 95):
        fail(f"slot count {n} outside the 75-95 range in BUILD_DIRECTIVE section 5")
    notes.append(f"{n} building slots "
                 f"({sum(1 for s in slots if s['outside'])} outside the wall)")

    seen = {}
    for s in slots:
        if s["n"] in seen:
            fail(f"duplicate slot number {s['n']}")
        seen[s["n"]] = s
        if s["street"] not in STREETS and s["street"] not in ("market_square", "quay_road"):
            fail(f"slot {s['n']} fronts unknown street '{s['street']}'")

    # 1. no two slots may overlap
    for i in range(len(slots)):
        for j in range(i + 1, len(slots)):
            d = sat_overlap(slots[i]["poly"], slots[j]["poly"])
            if d > 0.02:
                fail(f"slots {slots[i]['n']:02d} ({slots[i]['kit_group']}) and "
                     f"{slots[j]['n']:02d} ({slots[j]['kit_group']}) overlap by {d:.2f} m")

    # 2. no slot may intrude into a street corridor (width/2 + verge)
    STREET_FREE = {17}          # the lychgate IS a gateway across the path
    # Slots allowed to stand over water. Both are now DRY on their own made
    # ground — the mill on its platform out into the bank, the crane on the
    # wharf — so the list is empty and the check is unconditional. Kept as a
    # named, empty set rather than deleted, because the next thing built out
    # over the mere (a jetty, a boathouse) will want it and should have to add
    # itself here deliberately.
    OVER_WATER: set[int] = set()
    for s in slots:
        if s["n"] in STREET_FREE:
            continue
        for st in P.STREETS:
            # The wall separates the town from the roads outside it, so an
            # out-of-wall track is only ever a constraint on an out-of-wall slot.
            if st.get("outside") and not s["outside"]:
                continue
            # Hard rule: the carriageway plus a 0.3 m kerb margin must be
            # clear, because v1's real defect was a street you could not walk
            # down. The verge on top of that is the footway the plan wants;
            # falling short of it is a warning, not a broken plan - plenty of
            # real medieval frontages come straight down to the kerb.
            hard = st["width"] / 2.0 + 0.3
            want = st["width"] / 2.0 + st["verge"]
            d = poly_path_dist(s["poly"], st["path"])
            if d < hard - 0.02:
                fail(f"slot {s['n']:02d} ({s['kit_group']}) stands {d:.2f} m from "
                     f"{st['name']} centreline; carriageway needs {hard:.2f} m")
            elif d < want - 0.02:
                notes.append(f"slot {s['n']:02d} ({s['kit_group']}) fronts "
                             f"{st['name']} with {d - st['width'] / 2:.2f} m of "
                             f"footway, less than the {st['verge']:.2f} m wanted")

    # 3. Ford Road's centreline is sacred (BUILD_DIRECTIVE section 3)
    ford = STREETS["ford_road"]["path"]
    for s in slots:
        if poly_path_dist(s["poly"], ford) < 3.5:
            fail(f"slot {s['n']:02d} stands on Ford Road's carriageway")

    # 4. nothing may stand in the water — asked of the height field, not of a
    #    polygon drawn beside it. D-024: the water IS the ground.
    wet = 0
    for s in slots:
        if s["n"] in OVER_WATER:
            continue
        for c in list(s["poly"]) + [(s["cx"], s["cz"])]:
            if P.height(c[0], c[1]) < P.WATER_Y:
                fail(f"slot {s['n']:02d} ({s['kit_group']}) stands in the water at "
                     f"({c[0]:+.1f}, {c[1]:+.1f}): ground {P.height(c[0], c[1]):+.2f} m "
                     f"is below the water surface at {P.WATER_Y:+.2f} m")
                wet += 1
                break
    notes.append(f"{len(slots) - wet - len(OVER_WATER)} of {len(slots)} slots "
                 f"stand clear of the water"
                 + (f"; {len(OVER_WATER)} are authored over it" if OVER_WATER else ""))

    # 4b. and no water may stand on a road. The one exemption is the Emberflow
    #     bridge, declared as a z interval on Ford Road, because a bridge is
    #     precisely a road that is allowed to be over water.
    for st in P.STREETS:
        half = st["width"] / 2.0
        bridged = st.get("bridged")
        drowned = []
        for a, b in zip(st["path"], st["path"][1:]):
            ln = math.hypot(b[0] - a[0], b[1] - a[1])
            for k in range(int(ln / 1.0) + 1):
                t = min(1.0, k / max(ln, 1e-6))
                x = a[0] + (b[0] - a[0]) * t
                z = a[1] + (b[1] - a[1]) * t
                if bridged and bridged[0] <= z <= bridged[1]:
                    continue
                for off in (-half, 0.0, half):
                    dx, dz = b[0] - a[0], b[1] - a[1]
                    nx, nz = -dz / max(ln, 1e-6), dx / max(ln, 1e-6)
                    if P.height(x + nx * off, z + nz * off) < P.WATER_Y:
                        drowned.append((round(x, 1), round(z, 1)))
                        break
        if drowned:
            fail(f"street {st['id']} is under water at "
                 f"{len(drowned)} stations, first at {drowned[0]}")
    notes.append("no carriageway is under water except Ford Road across the "
                 f"Emberflow bridge (z {P.STREETS[0]['bridged'][0]:g} to "
                 f"{P.STREETS[0]['bridged'][1]:g})")

    # 5. everything must be inside the grid
    for s in slots:
        for c in s["poly"]:
            if abs(c[0]) > P.EXTENT or abs(c[1]) > P.EXTENT:
                fail(f"slot {s['n']:02d} leaves the 192 m grid at {c}")
                break

    # 6. no street may leave the grid, and every street must terminate
    for st in P.STREETS:
        for x, z in st["path"]:
            if abs(x) > P.EXTENT + 0.5 or abs(z) > P.EXTENT + 0.5:
                fail(f"street {st['id']} leaves the grid at ({x},{z})")

    # 7. the arrival frame (BUILD_DIRECTIVE section 3.2)
    check_arrival(slots)

    # 8. levels. A spot level with no authored y IS the height function and
    #    there is nothing to check. One with an authored y is a MADE surface —
    #    a floor, a deck, a tread — and what has to be true of it is that it
    #    stands on the ground rather than in it or above it. The old check
    #    compared two height models and was the thing D-022 caught.
    # How far a made surface of each kind may sit below / above the ground it
    # stands on. A floor may be dug in — the Ferryman's Lamp is sunken 0.55 m
    # and that is the building's most-quoted feature. A deck is a structure
    # over water and is allowed real height, but never below the bed.
    MADE = {"paving": (0.06, 2.8), "made": (0.06, 2.8), "step": (0.06, 1.2),
            "floor": (0.80, 2.8), "deck": (0.00, 6.0)}
    for name, x, z, y, kind in P.SPOT_LEVELS:
        if y is None or kind == "water":
            continue
        g = P.height(x, z)
        under, over = MADE.get(kind, (0.06, 2.8))
        if y < g - under:
            fail(f"made level '{name}' ({kind}) at {y:+.2f} is {g - y:.2f} m below "
                 f"the ground at {g:+.2f} — it would be buried")
        elif y - g > over:
            fail(f"made level '{name}' ({kind}) at {y:+.2f} stands {y - g:.2f} m "
                 f"above the ground at {g:+.2f} — that is fill, not a plinth")
    notes.append(f"{sum(1 for s in P.SPOT_LEVELS if s[3] is None)} spot levels "
                 f"read straight from terrain, "
                 f"{sum(1 for s in P.SPOT_LEVELS if s[3] is not None)} are made "
                 f"surfaces checked against it")
    fall = P.height(1, 78.5) - P.height(-2.4, -76)
    if not (3.6 <= fall <= 4.6):
        fail(f"south-gate to north-gate fall is {fall:.2f} m, brief says ~4 m")
    notes.append(f"ground falls {fall:.2f} m from the south gate to the north gate")


ALTAR = (43.0, -0.5)
CHURCH_FLOOR = 2.40
DAIS = 0.90
EYE = CHURCH_FLOOR + DAIS + 1.62          # 4.92
DOOR_X = 32.0                             # church west front plane
DOOR_HALF = 3.2                           # clear opening 6.4 m
DOOR_HEAD = CHURCH_FLOOR + 8.0            # 10.40

ANCHORS = [
    ("fountain", (0.0, 0.0), 4.4),
    ("guild tower", (-28.5, -4.5), 21.5),
    ("moot hall bell-cote", (-9.3, 12.6), 15.8),
    ("Grey Heron Inn, south-east angle", (-27.0, -18.0), 14.2),
    ("market cross", (-6.0, 8.0), 5.2),
]


def check_arrival(slots):
    ax, az = ALTAR
    dz = -0.5                                  # portal centreline in z
    tan = DOOR_HALF / (ax - DOOR_X)            # aperture half-tangent = 0.2909
    for name, (px, pz), top in ANCHORS:
        R = math.hypot(ax - px, az - pz)
        lat = abs(pz - dz) * (ax - DOOR_X) / max(1e-6, (ax - px)) * (ax - px) / max(1e-6, (ax - px))
        lat = abs(pz - dz)
        if lat > tan * (ax - px) + 1e-6:
            fail(f"arrival frame: '{name}' is {lat:.1f} m off axis at "
                 f"{ax - px:.1f} m, outside the {tan * (ax - px):.1f} m portal cone")
        # vertical: does it fit under the door head?
        up = (DOOR_HEAD - EYE) / (ax - DOOR_X)
        if top - EYE > up * (ax - px):
            fail(f"arrival frame: '{name}' top {top} m is above the portal head")
        # occlusion by any other slot
        for s in slots:
            if s["n"] in (11, 12, 17):         # the church itself
                continue
            if seg_hits_poly((ax, az), (px, pz), s["poly"]):
                # the anchor's own footprint is allowed to be hit
                if not point_in_poly(px, pz, s["poly"]):
                    fail(f"arrival frame: slot {s['n']:02d} ({s['kit_group']}) "
                         f"blocks the view of '{name}'")
        notes.append(f"arrival frame: {name} at {R:.1f} m, "
                     f"{math.degrees(math.atan2(pz - dz, ax - px)):+.1f} deg off axis")

    # ground profile: is the paving continuously visible out to the fountain?
    hidden = []
    for k in range(200):
        R = 11.0 + k * 0.25
        x = ax - R
        if x < 0:
            break
        h = ground_profile(x)
        if R < (EYE - h) / ((EYE - CHURCH_FLOOR) / (ax - DOOR_X)):
            hidden.append(round(x, 1))
    if hidden:
        lo, hi = min(hidden), max(hidden)
        notes.append(f"arrival frame: ground hidden behind the threshold for "
                     f"x={hi:.1f} down to x={lo:.1f} (the dead zone below the perron)")
        if lo < 12.0:
            fail(f"arrival frame: the market place at x={lo:.1f} is hidden by the "
                 f"door threshold — the perron is too steep or the altar too far back")


PERRON = [(32.0, 2.40), (24.0, 0.80)]      # head, foot


def ground_profile(x):
    """Height along the arrival axis z = -0.5, west of the church door."""
    if x >= 32.0:
        return CHURCH_FLOOR
    if x >= 24.0:
        t = (32.0 - x) / 8.0
        return 2.40 - 1.60 * t
    if x >= 13.5:
        return 0.80 - 0.25 * (24.0 - x) / 10.5
    if x >= 5.0:
        return 0.55 - 0.25 * (13.5 - x) / 8.5
    return 0.30 * (x / 5.0) if x > 0 else 0.0


# --------------------------------------------------------------------------
# SVG
# --------------------------------------------------------------------------
# 1:200 — 1 world metre = 5 mm of paper. Units below are millimetres, and the
# sheet declares its real size, so printing it gives a true 1:200 drawing.

MM = 5.0
PAD_X, PAD_Y = 60.0, 96.0
W_MM, H_MM = 1120.0, 1180.0


def px(x):
    return PAD_X + (x + 100.0) * MM


def py(z):
    return PAD_Y + (z + 100.0) * MM


def pts(poly):
    return " ".join(f"{px(x):.1f},{py(z):.1f}" for x, z in poly)


def contours(levels):
    """Marching squares on the height function, for the plan's contour lines."""
    step, out = 2.0, {lv: [] for lv in levels}
    xs = [(-98.0 + i * step) for i in range(int(196 / step) + 1)]
    zs = [(-98.0 + i * step) for i in range(int(196 / step) + 1)]
    H = [[P.height(x, z) for z in zs] for x in xs]
    for i in range(len(xs) - 1):
        for j in range(len(zs) - 1):
            cs = [(xs[i], zs[j], H[i][j]), (xs[i + 1], zs[j], H[i + 1][j]),
                  (xs[i + 1], zs[j + 1], H[i + 1][j + 1]), (xs[i], zs[j + 1], H[i][j + 1])]
            for lv in levels:
                seg = []
                for a, b in zip(cs, cs[1:] + cs[:1]):
                    if (a[2] > lv) != (b[2] > lv):
                        t = (lv - a[2]) / (b[2] - a[2])
                        seg.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
                if len(seg) == 2:
                    out[lv].append(seg)
    return out


_BANDS = None


def water_bands(step=0.6, res=0.5):
    """Wet spans of the height field, as (x0, x1, z0, z1) rows.

    One scanline per `step` metres of z; within a row, the maximal runs where
    `height(x, z) < waterY`. This is the plan's water, and it is the same
    water the client renders because it is the same function.
    """
    global _BANDS
    if _BANDS is not None:
        return _BANDS
    import numpy as np
    out = []
    xs = np.arange(-104.0, 104.0 + res, res)
    z = -140.0
    while z <= 24.0:
        h = P.TERRAIN.get().height(xs, np.full_like(xs, z))
        wet = h < P.WATER_Y
        i = 0
        while i < len(xs):
            if wet[i]:
                j = i
                while j + 1 < len(xs) and wet[j + 1]:
                    j += 1
                if xs[j] - xs[i] >= res:
                    out.append((float(xs[i]), float(xs[j]), z, z + step))
                i = j + 1
            else:
                i += 1
        z += step
    _BANDS = out
    return out


def write_svg(slots):
    o = []
    A = o.append
    A(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W_MM}mm" height="{H_MM}mm" '
      f'viewBox="0 0 {W_MM} {H_MM}" font-family="Georgia,serif">')
    A('<defs>'
      '<pattern id="orch" width="9" height="9" patternUnits="userSpaceOnUse">'
      '<circle cx="4.5" cy="4.5" r="2.6" fill="none" stroke="#7d9460" stroke-width="0.6"/></pattern>'
      '<pattern id="grav" width="7" height="7" patternUnits="userSpaceOnUse">'
      '<path d="M2 1v4M0.6 2.2h2.8" stroke="#9aa08f" stroke-width="0.5"/></pattern>'
      '<pattern id="yard" width="6" height="6" patternUnits="userSpaceOnUse">'
      '<path d="M0 6L6 0" stroke="#c3b494" stroke-width="0.5"/></pattern>'
      '<pattern id="wat" width="14" height="14" patternUnits="userSpaceOnUse">'
      '<path d="M0 4q3.5 -2.5 7 0t7 0M0 10q3.5 -2.5 7 0t7 0" fill="none" '
      'stroke="#8fb3c9" stroke-width="0.6"/></pattern></defs>')
    A(f'<rect width="{W_MM}" height="{H_MM}" fill="#faf6ec"/>')

    # --- outside-the-wall ground -----------------------------------------
    A(f'<rect x="{px(-100):.1f}" y="{py(-100):.1f}" width="{200 * MM:.1f}" '
      f'height="{200 * MM:.1f}" fill="#eee7d3"/>')

    # --- contours ---------------------------------------------------------
    cs = contours([-1.0, 0.0, 1.0, 2.0, 3.0])
    for lv, segs in cs.items():
        bold = abs(lv) < 1e-6
        A(f'<g stroke="#c9b98f" stroke-width="{0.9 if bold else 0.5}" fill="none">')
        for (a, b) in segs:
            A(f'<line x1="{px(a[0]):.1f}" y1="{py(a[1]):.1f}" '
              f'x2="{px(b[0]):.1f}" y2="{py(b[1]):.1f}"/>')
        A('</g>')

    # --- water ------------------------------------------------------------
    # Drawn from the HEIGHT FIELD, not from a polygon typed beside it. The
    # plan used to carry its own water outline and it disagreed with the
    # ground by tens of metres (D-022); a scanline of `height(x, z) < waterY`
    # cannot. Rows are 0.6 m so the shoreline reads as a curve at A0.
    A('<g fill="#cfe2ee">')
    for x0, x1, z0, z1 in water_bands():
        A(f'<rect x="{px(x0):.2f}" y="{py(z1):.2f}" '
          f'width="{(x1 - x0) * MM:.2f}" height="{(z1 - z0) * MM + 0.35:.2f}"/>')
    A('</g>')
    A('<g fill="url(#wat)">')
    for x0, x1, z0, z1 in water_bands():
        A(f'<rect x="{px(x0):.2f}" y="{py(z1):.2f}" '
          f'width="{(x1 - x0) * MM:.2f}" height="{(z1 - z0) * MM + 0.35:.2f}"/>')
    A('</g>')
    A(f'<polygon points="{pts(P.FORD_BAR)}" fill="none" stroke="#b3a074" '
      f'stroke-width="0.9" stroke-dasharray="4 3"/>')
    A(f'<polygon points="{pts(P.WHARF)}" fill="#c8b593" stroke="#7a6a4c" stroke-width="1.0"/>')

    # --- cell grid --------------------------------------------------------
    A('<g stroke="#cdbfa0" stroke-width="0.4" stroke-dasharray="3 3">')
    for i in range(13):
        v = -96 + i * 16
        A(f'<line x1="{px(v):.1f}" y1="{py(-96):.1f}" x2="{px(v):.1f}" y2="{py(96):.1f}"/>')
        A(f'<line x1="{px(-96):.1f}" y1="{py(v):.1f}" x2="{px(96):.1f}" y2="{py(v):.1f}"/>')
    A('</g>')
    A('<g fill="#a2946f" font-size="7" text-anchor="middle">')
    for i, c in enumerate(P.COLS):
        A(f'<text x="{px(-96 + i * 16 + 8):.1f}" y="{py(-96) - 4:.1f}">{c}</text>')
        A(f'<text x="{px(-96 + i * 16 + 8):.1f}" y="{py(96) + 10:.1f}">{c}</text>')
    A('</g><g fill="#a2946f" font-size="7" text-anchor="middle">')
    for i, r in enumerate(P.ROWS):
        A(f'<text x="{px(-96) - 8:.1f}" y="{py(-96 + i * 16 + 10):.1f}">{r}</text>')
        A(f'<text x="{px(96) + 8:.1f}" y="{py(-96 + i * 16 + 10):.1f}">{r}</text>')
    A('</g>')
    A(f'<rect x="{px(-96):.1f}" y="{py(-96):.1f}" width="{192 * MM:.1f}" '
      f'height="{192 * MM:.1f}" fill="none" stroke="#a2946f" stroke-width="1.0"/>')

    # --- open lots --------------------------------------------------------
    fillmap = dict(graveyard="url(#grav)", orchard="url(#orch)", yard="url(#yard)",
                   garden="#dfe6cf", midden="#d8cdb2", quay="#c8b593", water="#ded2b4")
    for lot in P.OPEN_LOTS:
        A(f'<polygon points="{pts(lot["poly"])}" fill="{fillmap.get(lot["kind"], "#e6dec8")}" '
          f'stroke="#b3a074" stroke-width="0.6"/>')

    # --- streets ----------------------------------------------------------
    order = {"primary": 0, "secondary": 1, "lane": 2, "alley": 3, "steps": 3}
    for st in sorted(P.STREETS, key=lambda s: -order[s["cls"]]):
        p = " ".join(f"{px(x):.1f},{py(z):.1f}" for x, z in st["path"])
        A(f'<polyline points="{p}" fill="none" stroke="#b6a67f" '
          f'stroke-width="{(st["width"] + 0.4) * MM:.1f}" stroke-linejoin="round"/>')
        A(f'<polyline points="{p}" fill="none" stroke="#e8e0c8" '
          f'stroke-width="{st["width"] * MM:.1f}" stroke-linejoin="round"/>')
    for st in P.STREETS:
        p = " ".join(f"{px(x):.1f},{py(z):.1f}" for x, z in st["path"])
        A(f'<polyline points="{p}" fill="none" stroke="#b0a punch" stroke-width="0"/>')
        A(f'<polyline points="{p}" fill="none" stroke="#c0b189" stroke-width="0.35" '
          f'stroke-dasharray="6 4"/>')

    # --- market place, over the streets because it IS the street here ----
    A(f'<polygon points="{pts(P.SQUARE)}" fill="#e6dfc6" stroke="#9d8e69" stroke-width="1.2"/>')
    A(f'<text x="{px(-13):.1f}" y="{py(-19):.1f}" font-size="11" fill="#7a6a44" '
      f'text-anchor="middle" letter-spacing="2">THE MARKET PLACE</text>')

    # --- the perron and Kirk Green ---------------------------------------
    for i in range(10):
        x = 32.0 - i * 0.8
        A(f'<line x1="{px(x):.1f}" y1="{py(-8.0):.1f}" x2="{px(x):.1f}" '
          f'y2="{py(7.0):.1f}" stroke="#a89974" stroke-width="0.6"/>')
    A(f'<rect x="{px(24):.1f}" y="{py(-8):.1f}" width="{8 * MM:.1f}" '
      f'height="{15 * MM:.1f}" fill="none" stroke="#8d7f5e" stroke-width="0.8"/>')
    # market step
    ms = P.MARKET_STEP
    A(f'<line x1="{px(ms["a"][0]):.1f}" y1="{py(ms["a"][1]):.1f}" '
      f'x2="{px(ms["b"][0]):.1f}" y2="{py(ms["b"][1]):.1f}" '
      f'stroke="#8d7f5e" stroke-width="1.6"/>')

    # --- the arrival sightline cone --------------------------------------
    ax, az = ALTAR
    tan = DOOR_HALF / (ax - DOOR_X)
    far = ax + 130.0
    cone = [(ax, az), (ax - 130.0, az - 0.0 - tan * 130.0), (ax - 130.0, az + tan * 130.0)]
    A(f'<polygon points="{pts(cone)}" fill="#c8a33a" fill-opacity="0.13" '
      f'stroke="#b58a24" stroke-width="0.7" stroke-dasharray="7 4"/>')
    A(f'<line x1="{px(ax):.1f}" y1="{py(az):.1f}" x2="{px(-96):.1f}" '
      f'y2="{py(az):.1f}" stroke="#b58a24" stroke-width="0.8" stroke-dasharray="12 5"/>')

    # --- wall, towers, gates ---------------------------------------------
    A(f'<polygon points="{pts(P.WALL)}" fill="none" stroke="#6d6350" stroke-width="{1.4 * MM:.1f}"/>')
    A(f'<polygon points="{pts(P.WALL)}" fill="none" stroke="#9b9078" stroke-width="{0.7 * MM:.1f}"/>')
    for t in P.TOWERS:
        x, z = t["pos"]
        if t["shape"] == "round":
            A(f'<circle cx="{px(x):.1f}" cy="{py(z):.1f}" r="{2.8 * MM:.1f}" '
              f'fill="#8d8168" stroke="#57503f" stroke-width="0.8"/>')
        else:
            A(f'<rect x="{px(x - 3.4):.1f}" y="{py(z - 3.4):.1f}" width="{6.8 * MM:.1f}" '
              f'height="{6.8 * MM:.1f}" fill="#8d8168" stroke="#57503f" stroke-width="0.8"/>')
    for g in P.GATES:
        x, z = g["pos"]
        r = 3.6 if g["kind"] != "postern" else 2.0
        A(f'<circle cx="{px(x):.1f}" cy="{py(z):.1f}" r="{r * MM:.1f}" fill="#f3ecd8" '
          f'stroke="#8c3b2e" stroke-width="1.4"/>')
        A(f'<text x="{px(x):.1f}" y="{py(z) + 3:.1f}" font-size="8" fill="#8c3b2e" '
          f'text-anchor="middle" font-weight="bold">'
          f'{"G" if g["kind"] == "gate" else ("W" if g["kind"] == "water" else "p")}</text>')
    for x, z in P.WALL_STAIRS:
        A(f'<rect x="{px(x - 1.0):.1f}" y="{py(z - 1.0):.1f}" width="{2 * MM:.1f}" '
          f'height="{2 * MM:.1f}" fill="none" stroke="#57503f" stroke-width="0.8"/>')

    # --- building slots ---------------------------------------------------
    tone = dict(hero="#b4634a", secondary="#c69a5e", filler="#cbbfa2")
    for s in slots:
        A(f'<polygon points="{pts(s["poly"])}" fill="{tone[s["role"]]}" '
          f'stroke="#4a3728" stroke-width="0.7"/>')
        # ridge line, so the roof orientation reads in plan
        fx, fz = fwd(s["rot"])
        rx, rz = right(s["rot"])
        if s["ridge"] in ("along", "flat", "cone"):
            ux, uz, half = rx, rz, s["w"] / 2 - 0.6
        else:
            ux, uz, half = fx, fz, s["d"] / 2 - 0.6
        if half > 0.8 and s["ridge"] not in ("flat", "cone"):
            A(f'<line x1="{px(s["cx"] - ux * half):.1f}" y1="{py(s["cz"] - uz * half):.1f}" '
              f'x2="{px(s["cx"] + ux * half):.1f}" y2="{py(s["cz"] + uz * half):.1f}" '
              f'stroke="#f4ecd8" stroke-width="0.9"/>')
        # entrance tick on the frontage
        A(f'<line x1="{px(s["cx"] + fx * s["d"] / 2):.1f}" y1="{py(s["cz"] + fz * s["d"] / 2):.1f}" '
          f'x2="{px(s["cx"] + fx * (s["d"] / 2 + 1.6)):.1f}" '
          f'y2="{py(s["cz"] + fz * (s["d"] / 2 + 1.6)):.1f}" '
          f'stroke="#4a3728" stroke-width="0.8"/>')
        A(f'<text x="{px(s["cx"]):.1f}" y="{py(s["cz"]) + 3.0:.1f}" font-size="8.5" '
          f'fill="#fdf8ea" text-anchor="middle" font-weight="bold" '
          f'stroke="#3a2c1f" stroke-width="1.6" paint-order="stroke">{s["n"]}</text>')

    # --- landmarks --------------------------------------------------------
    for lm in P.LANDMARKS:
        x, z = lm["pos"]
        A(f'<circle cx="{px(x):.1f}" cy="{py(z):.1f}" r="{1.9 * MM:.1f}" fill="#7ea9c4" '
          f'stroke="#2f5468" stroke-width="1.0"/>')
    A(f'<text x="{px(0):.1f}" y="{py(0) - 12:.1f}" font-size="9" fill="#2f5468" '
      f'text-anchor="middle" font-style="italic">Heron Fountain (0,0,0)</text>')
    A(f'<circle cx="{px(ALTAR[0]):.1f}" cy="{py(ALTAR[1]):.1f}" r="{1.6 * MM:.1f}" '
      f'fill="#8c3b2e"/>')
    A(f'<text x="{px(ALTAR[0]) + 12:.1f}" y="{py(ALTAR[1]) - 8:.1f}" font-size="9" '
      f'fill="#8c3b2e" font-style="italic">altar / playerSpawn</text>')

    # --- venue captions ---------------------------------------------------
    CAPTIONS = [
        (11, "CHURCH OF SUMMONING"), (12, "tower"), (2, "ADVENTURER'S GUILD"),
        (1, "GREY HERON INN"), (3, "MOOT HALL"), (43, "BLACKSMITH"),
        (72, "FERRYMAN'S LAMP"), (61, "CUSTOMS HOUSE"), (77, "WATERMILL"),
        (93, "TANNERY"), (94, "CRANE"), (32, "BAKERY"), (91, "BATHHOUSE"),
        (70, "STABLES"), (4, "SHOP ROW"), (14, "BEDE HOUSES"), (57, "DOVECOTE"),
        (67, "ROPE HOUSE"), (34, "CARPENTER"), (35, "CHANDLER"), (33, "COOPER"),
    ]
    by_n = {s["n"]: s for s in slots}
    A('<g font-size="8" fill="#3a2c1f" text-anchor="middle" font-style="italic">')
    for n, cap in CAPTIONS:
        s0 = by_n[n]
        A(f'<text x="{px(s0["cx"]):.1f}" y="{py(s0["cz"]) + 13:.1f}" '
          f'stroke="#faf6ec" stroke-width="2.2" paint-order="stroke">{cap}</text>')
    A('</g>')

    # --- street names -----------------------------------------------------
    A('<g font-size="8.5" fill="#6b5a3a" font-style="italic">')
    for st in P.STREETS:
        if st["cls"] in ("alley", "steps"):
            continue
        mid = st["path"][len(st["path"]) // 2]
        nxt = st["path"][min(len(st["path"]) // 2 + 1, len(st["path"]) - 1)]
        ang = math.degrees(math.atan2(py(nxt[1]) - py(mid[1]), px(nxt[0]) - px(mid[0])))
        if ang > 90:
            ang -= 180
        if ang < -90:
            ang += 180
        A(f'<text x="{px(mid[0]):.1f}" y="{py(mid[1]) - 3:.1f}" text-anchor="middle" '
          f'transform="rotate({ang:.1f} {px(mid[0]):.1f} {py(mid[1]):.1f})">{st["name"]}</text>')
    A('</g>')

    # --- water / district captions ---------------------------------------
    A(f'<text x="{px(-40):.1f}" y="{py(-92):.1f}" font-size="13" fill="#3d7291" '
      f'font-style="italic">The Emberflow</text>')
    A(f'<text x="{px(62):.1f}" y="{py(-78):.1f}" font-size="15" fill="#3d7291" '
      f'font-style="italic" transform="rotate(-38 {px(62):.1f} {py(-78):.1f})">The Mere</text>')
    A(f'<text x="{px(6):.1f}" y="{py(-88):.1f}" font-size="7.5" fill="#7a6a4c">the old ford</text>')

    # --- title block, north arrow, scale bar ------------------------------
    A(f'<text x="{PAD_X:.1f}" y="34" font-size="26" fill="#3a2c1f">HEARTHMERE</text>')
    A(f'<text x="{PAD_X:.1f}" y="52" font-size="11" fill="#6b5a3a">Master plan v2 '
      f'&#183; 1:200 at A0 &#183; 12 &#215; 12 cells of 16 m &#183; origin = the '
      f'Heron Fountain &#183; Y-up, 1 unit = 1 m, north is -Z</text>')
    A(f'<text x="{PAD_X:.1f}" y="68" font-size="10" fill="#6b5a3a">Generated by '
      f'tools/plan/townplan.py from tools/plan/plan_data.py. Do not hand-edit.</text>')

    # north arrow (north is -Z, i.e. up the page)
    nx, ny = W_MM - 118, 74
    A(f'<g stroke="#3a2c1f" fill="#3a2c1f">'
      f'<line x1="{nx}" y1="{ny + 34}" x2="{nx}" y2="{ny - 16}" stroke-width="1.6"/>'
      f'<polygon points="{nx},{ny - 24} {nx - 6},{ny - 8} {nx + 6},{ny - 8}"/>'
      f'<text x="{nx}" y="{ny + 48}" font-size="12" text-anchor="middle">N</text></g>')

    # scale bar: 0-50 m
    sx, sy = W_MM - 340, 60
    A(f'<g stroke="#3a2c1f" fill="none" stroke-width="1.0">')
    for i in range(5):
        A(f'<rect x="{sx + i * 10 * MM:.1f}" y="{sy}" width="{10 * MM:.1f}" height="7" '
          f'fill="{"#3a2c1f" if i % 2 == 0 else "#faf6ec"}"/>')
    A('</g>')
    A(f'<g font-size="8.5" fill="#3a2c1f" text-anchor="middle">')
    for i in range(6):
        A(f'<text x="{sx + i * 10 * MM:.1f}" y="{sy + 18}">{i * 10}</text>')
    A(f'<text x="{sx + 25 * MM:.1f}" y="{sy - 5}">metres</text></g>')

    # legend
    lx, ly = PAD_X, H_MM - 60
    items = [("#b4634a", "hero venue"), ("#c69a5e", "secondary venue"),
             ("#cbbfa2", "filler / kit"), ("#9b9078", "town wall"),
             ("#e8e0c8", "carriageway"), ("#cfe2ee", "water"),
             ("#c8a33a", "arrival sightline cone from the altar")]
    A(f'<g font-size="10" fill="#3a2c1f">')
    for i, (c, t) in enumerate(items):
        cx0 = lx + (i % 4) * 250
        cy0 = ly + (i // 4) * 20
        A(f'<rect x="{cx0}" y="{cy0 - 9}" width="18" height="11" fill="{c}" '
          f'stroke="#4a3728" stroke-width="0.6"/>')
        A(f'<text x="{cx0 + 24}" y="{cy0}">{t}</text>')
    A('</g>')
    A('</svg>')
    txt = "\n".join(o).replace('stroke="#b0a punch" stroke-width="0"', 'stroke="none"')
    os.makedirs(os.path.dirname(SVG_OUT), exist_ok=True)
    with open(SVG_OUT, "w", encoding="utf-8") as f:
        f.write(txt)
    return SVG_OUT


# --------------------------------------------------------------------------
# schedule table
# --------------------------------------------------------------------------

def schedule_table(slots):
    """The definitive building schedule. A builder agent is handed one row."""
    L = ["| # | slot id | kit / venue | centre x,z | w x d | faces | st | eaves "
         "| ridge | cells | fronts | role |",
         "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for s in slots:
        st = STREETS.get(s["street"], {}).get("name", "the market place")
        L.append(f"| {s['n']:02d} | `{s['id']}` | `{s['kit']}` | "
                 f"{s['cx']:+.1f}, {s['cz']:+.1f} | {s['w']:.1f} x {s['d']:.1f} | "
                 f"{s['rot']:.0f}&deg; | {s['storeys']} | {s['eaves']:.1f} | {s['ridge']} | "
                 f"{' '.join(s['cells'])} | {st}{' *(outside)*' if s['outside'] else ''} "
                 f"| {s['role']} |")
    L += ["", "**Slot notes.** `ground` is the terrain height at the plot centre; "
              "the ground floor sits on it unless the note says otherwise. `w` runs "
              "along the frontage, `d` back into the plot, and the front face is at "
              "centre + forward x d/2.", ""]
    for s in slots:
        L.append(f"**{s['n']:02d} {s['kit_group']}** &mdash; ground {s['ground']:+.2f} m"
                 f"{', OUTSIDE the wall' if s['outside'] else ''}. {s['note']}")
        L.append("")
    return NL.join(L)


def write_md(slots):
    os.makedirs(os.path.dirname(MD_OUT), exist_ok=True)
    with open(MD_OUT, "w", encoding="utf-8") as f:
        f.write("<!-- GENERATED by tools/plan/townplan.py. Do not hand-edit. -->"
                + NL + NL + schedule_table(slots) + NL)
    return MD_OUT


# --------------------------------------------------------------------------
# content/town/hearthmere.json
# --------------------------------------------------------------------------

# Authored in plan_data, because tools/plan/ground.py needs the same mapping:
# a venue is exactly the set of buildings that gets a named pad in terrain.json.
VENUE_ROLE = P.VENUE_ROLE
VENUE_OF_SLOT = P.VENUE_OF_SLOT


def fragments(slots):
    """The generated tables that docs/areas/hearthmere/TOWN_PLAN.md splices in."""
    out = {}

    L = ["| street | class | width | surface | length | falls | mean grade |",
         "| --- | --- | --- | --- | --- | --- | --- |"]
    for st in P.STREETS:
        pts = st["path"]
        ln = sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
        h0, h1 = P.height(*pts[0]), P.height(*pts[-1])
        L.append(f"| **{st['name']}**{' (outside)' if st.get('outside') else ''} "
                 f"| {st['cls']} | {st['width']:.1f} m | {st['surface']} | "
                 f"{ln:.0f} m | {h0:+.2f} to {h1:+.2f} | "
                 f"{abs(h1 - h0) / max(ln, 1e-6) * 100:.1f}% |")
    L += ["", "Centrelines, west-to-east or north-to-south as listed. "
              "`y` is the ground level at that point.", ""]
    for st in P.STREETS:
        pts = " ".join(f"({x:g},{z:g})" for x, z in st["path"])
        L.append(f"- `{st['id']}` — {pts}")
        L.append(f"  <br>{st['note']}")
    out["streets"] = NL.join(L)

    W = [f"Closed polyline, {len(P.WALL)} vertices, clockwise from the North Gate. "
         f"6.0 m to the wall-walk and a 1.2 m parapet where the curtain is "
         f"ordinary, 1.4 m thick battering to 1.1 m — but the crown is authored "
         f"per stretch, from the 2.35 m robbed garden wall on the west to the "
         f"7.9 m Mere frontage. The towers are older than the curtain and are "
         f"individually scheduled below.",
         ""]
    W.append("`" + " ".join(f"({x:g},{z:g})" for x, z in P.WALL) + "`")
    W += ["", "| gate | kind | at | clear | head | notes |",
          "| --- | --- | --- | --- | --- | --- |"]
    for g in P.GATES:
        W.append(f"| **{g['name']}** | {g['kind']} | ({g['pos'][0]:g}, {g['pos'][1]:g}) "
                 f"| {g['clear']:.1f} m | {g['head']:.1f} m | {g['note']} |")
    W += ["", "| tower | at | shape | height | roof | cell |",
          "| --- | --- | --- | --- | --- | --- |"]
    for t in P.TOWERS:
        h = float(t.get("height", 17.2 if t["shape"] == "square" else 13.4))
        rf = t.get("roof", "pyramid" if t["shape"] == "square" else "cone")
        W.append(f"| {t['name']} | ({t['pos'][0]:g}, {t['pos'][1]:g}) | {t['shape']} "
                 f"| {h:g} m | {rf} | {P.cell_of(*t['pos'])} |")
    W += ["", "Mural stairs to the wall-walk at "
          + ", ".join(f"({x:g}, {z:g})" for x, z in P.WALL_STAIRS) + "."]
    out["wall"] = NL.join(W)

    V = ["| name | (x, z) | level | kind | source |",
         "| --- | --- | --- | --- | --- |"]
    for n, x, z, y, k in P.SPOT_LEVELS:
        lv = P.height(x, z) if y is None else y
        src = "terrain" if y is None else f"made, ground {P.height(x, z):+.2f}"
        V.append(f"| {n} | ({x:g}, {z:g}) | {lv:+.2f} | {k} | {src} |")
    V += ["", "`terrain` levels are read straight from "
              "`content/town/terrain.json`; there is nothing to disagree with. "
              "`made` levels are floors, decks and treads a building owns, and "
              "the checker asserts each one stands on the ground rather than in "
              "it or a storey above it. See D-024."]
    out["levels"] = NL.join(V)

    out["schedule"] = schedule_table(slots)
    D = ["| district | cells | why it is there | what it holds |",
         "| --- | --- | --- | --- |"]
    for d in P.DISTRICTS:
        D.append(f"| **{d['name']}** | {d['cells']} | {d['cause']} | {d['holds']} |")
    out["districts"] = NL.join(D)
    return out


def splice(frags):
    """Rewrite the generated blocks inside docs/areas/hearthmere/TOWN_PLAN.md, in place."""
    if not os.path.exists(DOC_OUT):
        return None
    with open(DOC_OUT, encoding="utf-8") as f:
        doc = f.read()
    for key, body in frags.items():
        a = f"<!-- BEGIN GENERATED {key} -->"
        b = f"<!-- END GENERATED {key} -->"
        if a in doc and b in doc:
            i, j = doc.index(a) + len(a), doc.index(b)
            doc = doc[:i] + NL + body + NL + doc[j:]
    with open(DOC_OUT, "w", encoding="utf-8") as f:
        f.write(doc)
    return DOC_OUT


# Venues that build in WORLD coordinates and therefore take a null transform,
# exactly as `townhouse`, `streets`, `wall` and `market_square` already do.
#
# A venue whose root node carries an origin and a rotation must author its
# geometry in that rotated local frame. That is fine for a single mass built
# about its own centre, and it is unworkable for anything that spans several
# slots or calls `core.building` / `core.roof`, because those read the height
# field at WORLD x,z and hand back world polygons — put that output under a
# rotated root and the building lands somewhere else entirely.
#
# The waterfront is the case that forced the issue: `quay` is authored from the
# wharf polygon and the harbour basin, 15 m from the customs-house slot whose
# centre would otherwise be its origin, and `warehouse` owns seven slots spread
# from the wharf to the Bailey. See D-046.
WORLD_SPACE_VENUES = ("quay", "warehouse", "fish_eatery", "watermill")

WORLD_SPACE_NOTE = ("Built in WORLD coordinates, so its root transform is null "
                    "like townhouse/streets/wall. It uses core.building and "
                    "core.roof, which read the height field at world x,z. D-046.")


VENUE_DIR = os.path.join(REPO, "tools/assetgen/venues")


def venue_modules():
    """Every module under tools/assetgen/venues/ that `build.py` would pick up."""
    out = []
    for f in sorted(os.listdir(VENUE_DIR)):
        if f.endswith(".py") and not f.startswith("_"):
            out.append(f[:-3])
    return out


def check_placement_total():
    """FAIL if a venue module exists and nothing places it, or the reverse.

    `venues/landscape.py` existed, built, and was in the town file while being
    absent from this tool's infrastructure list, so every regeneration silently
    deleted it and the town rendered with zero vegetation and zero intramural
    ground for a whole wave. Regeneration has to be TOTAL: a module is placed
    on a slot, or placed as infrastructure, or declared not-placed with a
    reason. There is no fourth state and no silent one.
    """
    placed = set(P.VENUE_OF_SLOT.values()) | {v["id"] for v in P.INFRASTRUCTURE}
    declared = set(P.NOT_PLACED)
    mods = set(venue_modules())

    for m in sorted(mods - placed - declared):
        fail(f"venue module 'venues/{m}.py' exists but is NEITHER placed NOR "
             f"declared in plan_data.NOT_PLACED. Add it to VENUE_OF_SLOT / "
             f"INFRASTRUCTURE, or declare why it is not placed. A module that "
             f"is silently unplaced is how the whole landscape venue "
             f"disappeared from the town for a wave.")
    for m in sorted(placed - mods):
        fail(f"venue '{m}' is placed in the town but tools/assetgen/venues/"
             f"{m}.py does not exist — the client would 404 on its mesh.")
    for m in sorted(declared & placed):
        fail(f"venue '{m}' is in plan_data.NOT_PLACED and is also placed. "
             f"Pick one.")
    for m in sorted(declared - mods):
        fail(f"plan_data.NOT_PLACED declares '{m}' but no such module exists; "
             f"delete the declaration.")
    for m, why in sorted(P.NOT_PLACED.items()):
        if len(str(why).strip()) < 40:
            fail(f"plan_data.NOT_PLACED['{m}'] needs a real reason, not "
                 f"{why!r}.")
    notes.append(f"placement is total: {len(mods)} venue modules — "
                 f"{len(set(P.VENUE_OF_SLOT.values()))} on slots, "
                 f"{len(P.INFRASTRUCTURE)} infrastructure, "
                 f"{len(declared)} declared not-placed "
                 f"({', '.join(sorted(declared))})")


def check_siting(slots):
    """Prove, corner by corner, that a design-frame venue lands on its polygon.

    This is the check that would have caught the moot hall being 120 degrees
    out. It re-derives the whole chain here, deliberately NOT importing
    `core.siting`, so that a bug in the class cannot pass its own test:

      * the venue mesh is authored in the DESIGN frame — +X along the
        frontage, -Z out of the front door, footprint x in [-w/2, w/2],
        z in [-d/2, d/2];
      * `core.siting.Site.place` turns it by `-2*theta` about Y, using the
        three.js matrix x' = cos*x + sin*z, z' = -sin*x + cos*z (which is
        `Mesh.rotate_y` and `collision.rot_xz` and `rotXZ` in
        client/src/collision.js — all the same one);
      * the client, tools/render/town.html and tools/check_walkable.mjs then
        place the result at `venues[].origin` with `rotation.y = theta`.

    Compose those and every corner must land on `buildingSlots[].polygon`,
    which is drawn by `corners()` above in the plan's own convention. If the
    two conventions have drifted, or if anything reintroduces a second
    correction, the error is metres and this fails.
    """
    TOL = 1e-6
    worst = 0.0
    worst_id = None
    checked = 0

    world_space = set(WORLD_SPACE_VENUES)

    for s in slots:
        vid = P.VENUE_OF_SLOT.get(s["n"])
        if vid is None:
            continue                     # kit slot: townhouse.py builds in world
        t = math.radians(s["rot"])
        turn = -2.0 * t
        ct, st_ = math.cos(t), math.sin(t)
        cf, sf = math.cos(turn), math.sin(turn)
        hw, hd = s["w"] * 0.5, s["d"] * 0.5

        if vid in world_space:
            # Authored in world coordinates: origin [0,0,0], rotationDeg 0, so
            # there is no frame to get wrong and nothing to check. Recorded so
            # the count adds up rather than quietly skipping.
            notes.append(f"siting: slot {s['n']:02d} {vid} is world-space "
                         f"(origin 0,0,0 rot 0) — no frame correction applies")
            continue

        ox, oz = s["cx"], s["cz"]
        want = s["poly"]                       # front-L, front-R, back-R, back-L
        design = [(-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd)]
        for (a, b), (wx, wz) in zip(design, want):
            lx, lz = cf * a + sf * b, -sf * a + cf * b       # Site.place
            gx = ox + ct * lx + st_ * lz                     # rotation.y = theta
            gz = oz - st_ * lx + ct * lz
            e = math.hypot(gx - wx, gz - wz)
            if e > worst:
                worst, worst_id = e, f"slot {s['n']:02d} {vid}"
            if e > TOL:
                fail(f"slot {s['n']:02d} {vid} (rot {s['rot']}): design corner "
                     f"({a:+.2f}, {b:+.2f}) lands at ({gx:.3f}, {gz:.3f}), "
                     f"{e:.3f} m off its polygon corner ({wx:.2f}, {wz:.2f}). "
                     f"The design frame and the placement frame have drifted.")
        checked += 1

    rotated = sum(1 for s in slots
                  if P.VENUE_OF_SLOT.get(s["n"])
                  and P.VENUE_OF_SLOT[s["n"]] not in world_space
                  and s["rot"] % 180 != 0)
    notes.append(f"siting: {checked} venue slots corner-exact on their "
                 f"polygons ({rotated} at a rotation where the two conventions "
                 f"disagree); worst corner error {worst * 1e3:.4f} mm"
                 f"{' at ' + worst_id if worst_id else ''}")


def check_shipped(slots):
    """The shipped town file must be the plan, corner for corner.

    This used to live inside `check_siting`, reading `hearthmere.json` BEFORE
    anything was written. That made the planner un-runnable the moment the plan
    changed: moving slot 07 five metres north made the shipped file disagree
    with the plan, the disagreement was a FAIL, a FAIL suppressed the write, and
    the write was the only thing that could have made them agree. A check that
    forbids the fix for the thing it is checking is a trap, not a check
    (ad-town-04 §11's chophouse and door-15 fixes both hit it).

    So it runs AFTER the write, against what was actually written. Same two
    assertions, same tolerance, and it still catches the case it was built for —
    somebody hand-editing `hearthmere.json` — because the next planner run
    rewrites the file and compares. `--check` runs it against the file on disk
    without writing, which is the read-only form.
    """
    if not os.path.exists(TOWN_OUT):
        fail(f"{TOWN_OUT} was not written")
        return
    with open(TOWN_OUT, encoding="utf-8") as f:
        doc = json.load(f)
    origins = {v["slot"]: v for v in doc.get("venues", []) if v.get("slot")}
    rows = {r["n"]: r for r in doc.get("buildingSlots", [])}
    world_space = set(WORLD_SPACE_VENUES)
    agreed = 0

    for s in slots:
        vid = P.VENUE_OF_SLOT.get(s["n"])
        if vid is not None and vid not in world_space and s["n"] in origins:
            og = origins[s["n"]]["origin"]
            if abs(og[0] - s["cx"]) > 0.011 or abs(og[2] - s["cz"]) > 0.011:
                fail(f"slot {s['n']:02d} {vid}: venues[].origin "
                     f"({og[0]}, {og[2]}) is not the slot centre "
                     f"({s['cx']}, {s['cz']})")
            if abs(float(origins[s["n"]].get("rotationDeg", 0)) - s["rot"]) > 1e-6:
                fail(f"slot {s['n']:02d} {vid}: venues[].rotationDeg "
                     f"{origins[s['n']].get('rotationDeg')} != slot rotationDeg "
                     f"{s['rot']}")
        row = rows.get(s["n"])
        if row is None:
            fail(f"slot {s['n']:02d}: missing from buildingSlots in {TOWN_OUT}")
            continue
        for (wx, wz), (dx, dz) in zip(s["poly"], row["polygon"]):
            if abs(wx - dx) > 0.011 or abs(wz - dz) > 0.011:
                fail(f"slot {s['n']:02d}: polygon in hearthmere.json disagrees "
                     f"with the plan — ({dx}, {dz}) vs ({wx:.2f}, {wz:.2f}).")
                break
        else:
            agreed += 1
    notes.append(f"shipped: {agreed} of {len(slots)} slot polygons in "
                 f"hearthmere.json agree with the plan to 11 mm")


def write_town(slots):
    by_n = {s["n"]: s for s in slots}

    venues = []
    seen = set()
    for n, vid in sorted(VENUE_OF_SLOT.items()):
        s = by_n[n]
        inst = vid if vid not in seen else f"{vid}_{n:02d}"
        seen.add(vid)
        world = vid in WORLD_SPACE_VENUES
        venues.append({
            "id": vid, "instance": inst, "slot": n,
            "cells": s["cells"],
            "origin": [0, 0, 0] if world else
                      [round(s["cx"], 2), round(s["ground"], 2), round(s["cz"], 2)],
            "rotationDeg": 0 if world else s["rot"],
            "role": VENUE_ROLE.get(vid, "secondary"),
            **({"comment": WORLD_SPACE_NOTE} if world else {}),
        })
    # Infrastructure venues, which are not building slots. The list is
    # `plan_data.INFRASTRUCTURE` — declared beside VENUE_OF_SLOT so the two
    # halves of "what gets placed" cannot go out of step, and so
    # `check_placement_total` can see both.
    for row in P.INFRASTRUCTURE:
        org = list(row["origin"])
        # An infrastructure origin with a None Y takes the height field, like
        # every other origin in the file. Hard-typing one was how the gatehouse
        # ended up 0.45 m under its own gate flat.
        if org[1] is None:
            org = [org[0], round(P.height(org[0], org[2]), 2), org[2]]
        venues.append({"id": row["id"], "instance": row["id"],
                       "cells": list(row["cells"]), "origin": org,
                       "rotationDeg": 0, "role": row["role"],
                       "comment": row["note"]})

    doc = {
        "$schema": "../schemas/town.schema.json",
        "id": "hearthmere",
        "displayName": "Hearthmere",
        "zonePrefix": "hm",
        "version": 2,
        "description": "A lake town grown up around the old ford. The first town. "
                       "v2: 192 m walled town on a 12x12 grid, arrival from the "
                       "church altar. See docs/areas/hearthmere/TOWN_PLAN.md.",
        "grid": {
            "cellSize": P.CELL,
            "cols": P.COLS,
            "rows": P.ROWS,
            "originCell": "F6",
            "bounds": {"min": [-96.0, -96.0], "max": [96.0, 96.0]},
            "comment": "12x12 cells of 16 m. World origin (0,0,0) is the market "
                       "square fountain at the grid centre, on the F/G-6/7 corner. "
                       "Cell letter index = floor(x/16)+6, row = floor(z/16)+7. "
                       "Cell A1 spans x[-96,-80] z[-96,-80].",
        },
        "lighting": P.LIGHTING,
        "atmosphere": P.ATMOSPHERE,
        "terrain": {
            "source": "content/town/terrain.json",
            "datum": "Y = 0.00 is the market-square paving at the fountain kerb (0,0).",
            "comment": [
                "THIS FILE DOES NOT MODEL THE GROUND. content/town/terrain.json "
                "does, evaluated by tools/assetgen/core/terrain.py and "
                "client/src/terrain.js. There used to be a second height model "
                "here — a base profile plus a Gaussian rise — and D-022 measured "
                "it disagreeing with the real one by up to 1.48 m on venue "
                "origins and 1.24 m on street paths. D-024 deleted it.",
                "Consequently NO polyline in this file carries a Y any more. "
                "Street paths, the wall, the open lots, the market place and the "
                "landmarks are all [x, z]; a consumer takes the level from "
                "terrain.height(x, z), which is the only number that can be "
                "right. The one Y that survives is venues[].origin[1], because "
                "that is a scene-graph transform the client applies rather than "
                "a lookup, and it is written here straight from terrain.height "
                "at the venue's own centre — so the drift is zero by "
                "construction, not by anyone remembering to re-derive it.",
            ],
            "spotLevels": [
                {"name": n, "pos": [x, z],
                 "y": round(P.height(x, z), 2) if y is None else y,
                 "kind": k,
                 "source": "terrain" if y is None else "made"}
                for n, x, z, y, k in P.SPOT_LEVELS
            ],
        },
        "playerSpawn": {
            "comment": "ON THE SUMMONING ALTAR, inside the Church of Summoning, "
                       "facing west (270 deg) down the nave and out through the "
                       "open great west door. Feet at the dais top: the church "
                       "pad, plus a 2.40 m floor over it, plus a 0.90 m dais. "
                       "This frame is the most important composition in the "
                       "build - see docs/areas/hearthmere/TOWN_PLAN.md section 7.",
            "pos": [43.0, round(P.height(43.0, -0.5) + 2.40 + 0.90, 2), -0.5],
            "facingDeg": 270.0,
        },
        "districts": P.DISTRICTS,
        "venues": venues,
        "buildingSlots": [
            {
                "n": s["n"], "id": s["id"], "kit": s["kit"], "role": s["role"],
                "venue": VENUE_OF_SLOT.get(s["n"]),
                "cells": s["cells"],
                "centre": [round(s["cx"], 2), round(s["cz"], 2)],
                "footprint": {"w": s["w"], "d": s["d"]},
                "polygon": [[round(x, 2), round(z, 2)] for x, z in s["poly"]],
                "rotationDeg": s["rot"],
                "storeys": s["storeys"],
                "eavesHeight": s["eaves"],
                "ridge": s["ridge"],
                "groundY": s["ground"],
                "outsideWall": s["outside"],
                "fronts": s["street"],
                "note": s["note"],
            } for s in slots
        ],
        # Every polyline below is [x, z]. See terrain.comment: a stored Y is a
        # copy of terrain.height(x, z), and a copy is a thing that can be
        # wrong. `streets.py` already discarded the Y it was given and draped
        # onto the height field instead, which is the correct behaviour and is
        # now also the only possible one.
        "streets": [
            {**{k: v for k, v in st.items() if k != "path"},
             "path": [[x, z] for x, z in st["path"]]}
            for st in P.STREETS
        ],
        "wall": {
            "comment": "Low customs wall: 6.0 m to the wall-walk, 1.2 m parapet, "
                       "1.4 m thick battering to 1.1 m — but the height varies "
                       "stretch by stretch with the ground and with the wall's "
                       "history (see venues/wall.py _stretches: robbed garden "
                       "wall 2.35, oldest north-west run 4.9, the collapse "
                       "rebuilt in sandstone 6.9, the sixty-year-old ashlar "
                       "south-east 7.6, the Mere frontage 7.9). The eleven "
                       "towers are the OLDER burh turrets the curtain was "
                       "strung between, which is why they run 10.6-18.4 m. "
                       "Irregular oval following the river and the contour. Its "
                       "outer face is 0.8-4.0 m inside the mere's shoreline "
                       "from the Crane Tower to the Heron Tower, with the berm "
                       "and Tan Road on the strip between. Path is [x, z]; take "
                       "the level from terrain.",
            "path": [[x, z] for x, z in P.WALL],
            "walkHeight": 6.0, "parapet": 1.2, "thicknessBase": 1.4,
            "nearWater": [[P.WALL_NEAR_WATER[0][0], P.WALL_NEAR_WATER[0][1]],
                          [P.WALL_NEAR_WATER[1][0], P.WALL_NEAR_WATER[1][1]]],
            "gates": [{**g, "pos": list(g["pos"])} for g in P.GATES],
            # Height and roof are authored per tower in plan_data. They used to
            # be one constant per shape and ad-town-04 §(b) rejected exactly
            # that: "towers stand only 2.6 m proud of a 6.3 m curtain, so from
            # any aerial it is a low grey ribbon."
            "towers": [{**t, "pos": list(t["pos"]),
                        "height": float(t.get(
                            "height", 17.2 if t["shape"] == "square" else 13.4)),
                        "roof": t.get(
                            "roof", "pyramid" if t["shape"] == "square" else "cone")}
                       for t in P.TOWERS],
            "stairs": [[x, z] for x, z in P.WALL_STAIRS],
        },
        "water": {
            "source": "content/town/terrain.json",
            "comment": "The water is the ground: the same height field that "
                       "carves the channel and the basin is the one the client "
                       "walks on and the terrain venue renders. This block used "
                       "to carry its own polygons for the Emberflow, the Mere, a "
                       "mill leat and the wharf, at a surface 0.20 m off the real "
                       "one — see D-022 and D-024. Read water.channels in "
                       "terrain.json; take the surface from terrain.waterLevel().",
            "surfaceY": P.WATER_Y,
            "bodies": [
                {"id": s["id"], "name": s.get("name"),
                 "kind": "channel" if "path" in s else "basin"}
                for s in TERRAIN_DOC["water"]["channels"]
            ],
            "wharf": [[x, z] for x, z in P.WHARF],
        },
        "marketPlace": {
            "polygon": [[x, z] for x, z in P.SQUARE],
            "step": {"a": list(P.MARKET_STEP["a"]), "b": list(P.MARKET_STEP["b"]),
                     "risers": P.MARKET_STEP["risers"], "rise": P.MARKET_STEP["rise"],
                     "note": P.MARKET_STEP["note"]},
        },
        "openLots": [{**lot, "poly": [[x, z] for x, z in lot["poly"]]}
                     for lot in P.OPEN_LOTS],
        "landmarks": [{"id": lm["id"], "name": lm["name"],
                       "pos": [lm["pos"][0], lm["pos"][1]],
                       "groundY": round(P.height(*lm["pos"]), 2),
                       "comment": lm["note"]} for lm in P.LANDMARKS],
        "sightlines": sightline_records(slots),
        "ambient": P.AMBIENT,
    }
    with open(TOWN_OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)
        f.write("\n")
    return TOWN_OUT


def sightline_records(slots):
    ax, az = ALTAR
    tan = DOOR_HALF / (ax - DOOR_X)
    arrival = {
        "id": "hm.sightline.arrival",
        "name": "The arrival frame",
        "eye": [ax, round(EYE, 2), az],
        "facingDeg": 270.0,
        "aperture": {"plane": ["x", DOOR_X], "halfWidth": DOOR_HALF,
                     "head": DOOR_HEAD, "halfTangent": round(tan, 4)},
        "mustBeVisible": [],
        "comment": "Standing on the altar and looking west through the open great "
                   "west door. Verified by tools/plan/townplan.py --check: every "
                   "anchor lies inside the portal cone, under the door head, and "
                   "is unblocked by any building slot.",
    }
    for name, (x, z), top in ANCHORS:
        R = math.hypot(ax - x, az - z)
        arrival["mustBeVisible"].append({
            "what": name, "pos": [x, z], "topY": top,
            "rangeM": round(R, 1),
            "offAxisDeg": round(math.degrees(math.atan2(z - az, ax - x)), 1),
        })
    out = [arrival]
    for g in P.GATES:
        if g["kind"] == "postern":
            continue
        out.append({"id": g["id"].replace("wall.gate", "sightline.gate"),
                    "name": f"{g['name']} frame",
                    "eye": [g["pos"][0], round(P.height(*g["pos"]) + 1.62, 2), g["pos"][1]],
                    "facingDeg": (g["rot"] + 180) % 360,
                    "comment": "See docs/areas/hearthmere/TOWN_PLAN.md section 7."})
    return out


# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="checks only, write nothing")
    args = ap.parse_args()

    slots = build_slots()
    check(slots)
    check_placement_total()
    check_siting(slots)

    written = []
    if not problems and not args.check:
        written = [write_svg(slots), write_md(slots), write_town(slots)]
    # The shipped file is compared to the plan AFTER it has been written, so a
    # plan change can never lock itself out of the regeneration that would make
    # the two agree. See check_shipped().
    if not problems:
        check_shipped(slots)

    for nm in notes:
        print(f"  ..  {nm}")
    for p in problems:
        print(f"  FAIL  {p}")
    print(f"\n{len(problems)} problems")
    if problems:
        return 1
    for w in written:
        print("wrote", w)
    if written:
        d = splice(fragments(slots))
        if d:
            print("spliced", d)
    return 0


if __name__ == "__main__":
    sys.exit(main())
