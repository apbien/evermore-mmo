"""The quay — where Hearthmere touches the water, and the reason it exists.

`docs/areas/hearthmere/BUILD_DIRECTIVE.md` §4 says Hearthmere is a lake town at a ford. Inside
the walls the only evidence for that claim is this venue, and until it existed
`review/reports/ad-town-02.md` §1 was correct to call the waterfront "the
largest single dead area in the build".

Composed to Art Bible §7:

  ANCHOR    the treadwheel crane (slot 94) — a 12 m timber tower with its wheel
            open to the water, its jib overhanging the berth, and its rope
            actually reeved from drum to sheave to hook. It is the one object
            that identifies this quarter from anywhere in the town, and the
            schedule names it "silhouette anchor of the whole waterfront".
  FUNCTION  laid out the way a wharf is worked, from the water inward: berth,
            quay face with rings, bollards on the edge, the crane at the deep
            end where the lighters lie, the customs house squared onto the
            Water Gate so nothing lands without passing its window, and the
            bonded sheds behind (venue `warehouse`).
  RESIDUE   a half-loaded lighter with its tarpaulin turned back, split fish on
            the racks, a net still wet on the frame, eel traps stacked where
            they were emptied, spilled grain trodden into the flags, a bailing
            bucket left in the bilge, weed on the four bottom treads of the
            water stair.

THE JOIN IS THE POINT. Three levels have to resolve within eight metres:

    Water Gate threshold  -1.07     (paved, `wall` builds the arch)
    wharf deck            -1.44 crown, falling to -1.54 at both edges
    mere surface          -3.10     (`terrain.water_level()`)
    dredged harbour bed   -5.35     (terrain, `hm.water.harbour`)

The pad `hm.pad.quay` holds the deck flat at -1.55 and the ground drops off a
near-vertical scarp to the bed in a metre of plan. That scarp is not a defect,
it is the place a quay wall goes: the masonry here is built to bury it, from a
coping 0.06 m proud of the flags down to 0.55 m below the dredged bed, battered
1:14 so the face reads as built rather than extruded.

Authored in a WHARF-LOCAL frame and placed once — `+X` runs along the quay to
the north-east, `+Z` is landward toward the Water Gate, `-Z` is the water. The
venue itself is world-space (D-046), so colliders and entities go through
`_w()`.
"""

from __future__ import annotations

import json
import math
import os

import numpy as np

from core import building as BLD
from core import collision as COL
from core import kit as K
from core import mesh as M
from core import props as PR
from core import streetscape as SS
from core import terrain as T
from core import vegetation as VEG
from core.mathx import rng_for
from core.venue import VenueContext, REPO
from core import materials as MATS

NAME = "quay"
CELLS = ["I3", "I4", "J3", "J4", "J2", "K3", "K4"]

TOWN = os.path.join(REPO, "content/town/hearthmere.json")

WATER_Y = T.water_level()          # -3.10
BED_Y = -5.35                      # hm.water.harbour bedLevel
DECK_CROWN = -1.44                 # highest flag, on the crown line
CAMBER = 0.10                      # fall from crown to either edge
CROWN_C = 1.0                      # the crown sits a metre landward of centre
COPING_T = 0.30                    # depth of the coping course
CORD = "sacking"                   # hemp: rope, net, seizing, mooring warp
QUAY_BATTER = 0.28                 # how far the face leans out over its height


# ---------------------------------------------------------------------------
# The wharf frame
# ---------------------------------------------------------------------------

def _wharf():
    """(centre, U, EZ, half_a, half_c) from the authored wharf polygon.

    Read from `content/town/hearthmere.json` rather than typed here, because
    `hm.pad.quay` is solved from the same polygon and a second copy is a second
    thing that can be wrong. The polygon is the OUTER FACE of the quay wall.
    """
    doc = json.load(open(TOWN, encoding="utf-8"))
    p = [(float(x), float(z)) for x, z in doc["water"]["wharf"]]
    cx = sum(q[0] for q in p) / 4.0
    cz = sum(q[1] for q in p) / 4.0
    # p[0]->p[1] is the landward edge, with the Water Gate at its midpoint.
    ux, uz = p[1][0] - p[0][0], p[1][1] - p[0][1]
    ln = math.hypot(ux, uz)
    U = (ux / ln, uz / ln)
    # Right-handed with +Y: ex x ey = ez, so this is the LANDWARD normal.
    EZ = (-U[1], U[0])
    ha = ln * 0.5
    hc = math.hypot(p[2][0] - p[1][0], p[2][1] - p[1][1]) * 0.5
    # The landward edge must come out at +hc, not -hc.
    mid = ((p[0][0] + p[1][0]) * 0.5, (p[0][1] + p[1][1]) * 0.5)
    if (mid[0] - cx) * EZ[0] + (mid[1] - cz) * EZ[1] < 0:
        EZ = (-EZ[0], -EZ[1])
        U = (-U[0], -U[1])
    return (cx, cz), U, EZ, ha, hc


CENTRE, U, EZ, HALF_A, HALF_C = _wharf()


def _w(a, y, c):
    """Wharf-local -> world. Y passes through: the frame has no rise."""
    return (CENTRE[0] + U[0] * a + EZ[0] * c, float(y),
            CENTRE[1] + U[1] * a + EZ[1] * c)


def _wxz(a, c):
    return (CENTRE[0] + U[0] * a + EZ[0] * c, CENTRE[1] + U[1] * a + EZ[1] * c)


def _place(geom):
    """Put a wharf-local group into the world."""
    return M.place(geom, (CENTRE[0], 0.0, CENTRE[1]),
                   (U[0], 0.0, U[1]), (0.0, 1.0, 0.0), (EZ[0], 0.0, EZ[1]))


def deck_y(c):
    """Top of the flags at a given distance landward. A cambered deck sheds
    water to both edges, which is why the gutter is where it is and why the
    ruts hold puddles."""
    t = (float(c) - CROWN_C) / 8.0
    return DECK_CROWN - CAMBER * t * t


# ---------------------------------------------------------------------------
# Deck
# ---------------------------------------------------------------------------

def _slab(a0, a1, c0, c1, y_bot, mat="stone", uv=None):
    """A cambered-top prism of made ground under the flags."""
    b = []
    n = 6
    for i in range(n + 1):
        c = c0 + (c1 - c0) * i / n
        b.append((a0, c))
    out = M.Group()
    for i in range(n):
        ca, cb = c0 + (c1 - c0) * i / n, c0 + (c1 - c0) * (i + 1) / n
        ya, yb = deck_y(ca), deck_y(cb)
        prof = [(ca, y_bot), (cb, y_bot), (cb, yb), (ca, ya)]
        # profile in (Z, Y) -> extrude along X, then swing into place
        m = M.prism([(p[0], p[1]) for p in prof], a1 - a0, mat, chamfer=0.0,
                    uv_scale=uv)
        m.rotate_y(-math.pi * 0.5)
        m.translate((a0 + a1) * 0.5, 0.0, 0.0)
        out.add(m)
    return out


def _flags(asset_id, a0, a1, c0, c1, mat="sett", flag=(1.15, 0.78)):
    """Stone flags, laid in courses parallel to the quay face and settled.

    Individually modelled because a wharf deck is seen at a grazing angle from
    the gameplay camera more often than any other surface in the town, and a
    tiled plane at a grazing angle is wallpaper (Art Bible §5). Every flag
    carries its own settle, tilt and yaw, which is what makes the puddles and
    the cart ruts read.
    """
    rng = rng_for(asset_id, "flags")
    out = M.Mesh(mat=mat)
    fw, fd = flag
    nc = max(1, int(round((c1 - c0) / fd)))
    fd = (c1 - c0) / nc
    for j in range(nc):
        c = c0 + (j + 0.5) * fd
        off = fw * (0.5 if j % 2 else 0.0) + rng.uniform(-0.1, 0.1)
        na = max(1, int(round((a1 - a0) / fw)))
        w = (a1 - a0) / na
        for i in range(-1, na + 1):
            a = a0 + (i + 0.5) * w + off
            if a < a0 - 0.2 or a > a1 + 0.2:
                continue
            sw = min(w, a1 + 0.15 - a + w * 0.5) * rng.uniform(0.93, 0.99)
            if sw < 0.25:
                continue
            settle = rng.uniform(-0.022, 0.008)
            h = 0.16
            s = M.box(sw, h, fd * rng.uniform(0.93, 0.98), 0.014, mat)
            s.rotate_z(rng.uniform(-0.010, 0.010))
            s.rotate_x(rng.uniform(-0.010, 0.010))
            s.rotate_y(rng.uniform(-0.012, 0.012))
            s.translate(a, deck_y(c) + settle - h * 0.5, c)
            out.merge(s)
    return out


# ---------------------------------------------------------------------------
# Quay wall
# ---------------------------------------------------------------------------

def _quay_face(ctx, g, asset_id, p0, p1, rings=True):
    """One run of battered quay wall between two wharf-local plan points.

    `p0`/`p1` are (a, c) on the OUTER FACE at coping level. The wall leans out
    as it falls, so the base is `QUAY_BATTER` further out than the top, and it
    runs from 0.55 m below the dredged bed to a coping 0.06 m proud of the
    flags — which buries the terrain scarp completely and means there is no
    line anywhere at which the ground stops and the masonry starts.
    """
    rng = rng_for(asset_id, "quayface")
    a0, c0 = p0
    a1, c1 = p1
    da, dc = a1 - a0, c1 - c0
    ln = math.hypot(da, dc)
    ua, uc = da / ln, dc / ln
    # Outward normal (away from the deck centre).
    na, nc = uc, -ua
    if (a0 + a1) * 0.5 * na + (c0 + c1) * 0.5 * nc < 0:
        na, nc = -na, -nc

    top_y = deck_y((c0 + c1) * 0.5) + 0.06
    bot_y = BED_Y - 0.55

    # Body, in three lifts so the courses read and so the algae band below the
    # waterline is its own material rather than a tint on one prism.
    #
    # `stone` (coursed rubble squared to beds), NOT `rubble` (random field
    # walling). A quay wall is the most engineered masonry a town of this size
    # builds and it is laid to courses; `rubble`'s Voronoi field also reads as
    # crazy paving at this scale, which `review/reports/ad-town-02.md` §9
    # rejected on the church.
    # The three lifts take the library's authored coverage (D-046): the three
    # bare `uv_scale=` floats that used to sit here were the last survivors of
    # the sweep, and they were the reason the quay wall's courses landed at a
    # different size from the same `stone` everywhere else in the town.
    lifts = [(bot_y, WATER_Y - 0.55, "stone", None),
             (WATER_Y - 0.55, WATER_Y + 0.22, "algae", None),
             (WATER_Y + 0.22, top_y - COPING_T, "stone", None)]
    for y0, y1, mat, uv in lifts:
        if y1 <= y0 + 0.01:
            continue
        o0 = QUAY_BATTER * (top_y - y0) / max(0.1, top_y - bot_y)
        o1 = QUAY_BATTER * (top_y - y1) / max(0.1, top_y - bot_y)
        pts = [
            (a0 + na * o0, c0 + nc * o0), (a1 + na * o0, c1 + nc * o0),
            (a1 - na * 1.35, c1 - nc * 1.35), (a0 - na * 1.35, c0 - nc * 1.35),
        ]
        g.add(_prism2(pts, y0, y1, mat, uv))
        _ = o1

    # Coping: ashlar, laid as individual stones so the joints are real.
    n = max(2, int(ln / 1.05))
    for i in range(n):
        t0, t1 = i / n, (i + 1) / n
        la = a0 + da * t0
        lc = c0 + dc * t0
        seg = ln / n * rng.uniform(0.94, 0.99)
        st = M.box(seg, COPING_T, 1.05, 0.024, "ashlar")
        st.rotate_y(-math.atan2(uc, ua) + rng.uniform(-0.004, 0.004))
        st.translate(la + ua * (ln / n) * 0.5 - na * 0.28,
                     top_y - COPING_T * 0.5 + rng.uniform(-0.012, 0.006),
                     lc + uc * (ln / n) * 0.5 - nc * 0.28)
        g.add(st)

    if not rings:
        return []
    # Mooring rings, set in the face a metre above the water so a line from a
    # laden boat still leads down. Every one is a staple, a ring and a rust run.
    #
    # RETURNED, in wharf-local coordinates, because a mooring line has to end
    # ON one. `_lighter` used to run its warps to `(a +/- 4.3, WATER_Y + 1.0,
    # c + 1.85)` — a point derived from the boat and from nothing on the wall,
    # 0.20 m short of the face at a height no ring is at — so the town's warps
    # ended in clear air beside the masonry. A rope that does not reach its
    # ring is worse than no rope: it is the one prop whose entire job is to say
    # the boat is attached to the town.
    out = []
    n = max(1, int(ln / 4.4))
    for i in range(n):
        t = (i + 0.5) / n
        ra, rc = a0 + da * t, c0 + dc * t
        y = WATER_Y + 1.05 + rng.uniform(-0.1, 0.1)
        o = QUAY_BATTER * (top_y - y) / max(0.1, top_y - bot_y)
        st = M.box(0.24, 0.10, 0.10, 0.012, "iron_pitted")
        st.rotate_y(-math.atan2(uc, ua))
        st.translate(ra + na * (o + 0.10), y, rc + nc * (o + 0.10))
        g.add(st)
        rg = M.ring(0.17, 0.045, "iron_pitted", segments=11)
        rg.rotate_x(math.pi * 0.5)
        rg.rotate_y(-math.atan2(uc, ua) + rng.uniform(-0.2, 0.2))
        rg.translate(ra + na * (o + 0.30), y - 0.12, rc + nc * (o + 0.30))
        g.add(rg)
        # The eye of the ring, which is where a warp is actually made fast.
        out.append((ra + na * (o + 0.30), y - 0.12 - 0.17, rc + nc * (o + 0.30)))
    return out


def _prism2(pts2, y0, y1, mat, uv=None, chamfer=0.0):
    """Vertical prism over a wharf-local plan polygon."""
    return M.prism([(p[0], p[1]) for p in pts2], y1 - y0, mat,
                   chamfer=chamfer, uv_scale=uv).rotate_x(
        -math.pi * 0.5).translate(0.0, (y0 + y1) * 0.5, 0.0)


# ---------------------------------------------------------------------------
# The water stair
# ---------------------------------------------------------------------------

def _water_stair(ctx, g, asset_id, a_top, c_face):
    """Steps down the quay face into the basin, on a projecting spur.

    A stair notched into the wall would need the deck cut round it; a spur is
    what a real quay does and it puts a second mass on the water line. The
    bottom four treads are below the surface, greened, and that is the whole
    reason the stair is worth building — it is the one place the player can see
    that the water has a depth.
    """
    rng = rng_for(asset_id, "stair")
    top_y = deck_y(c_face)
    n = 15
    rise = (top_y - (WATER_Y - 0.62)) / n
    going = 0.30
    spur = 1.65

    # Masonry spur carrying the flight.
    run = n * going
    pts = [(a_top + 0.55, c_face + 0.15), (a_top + 0.55, c_face - spur),
           (a_top - run - 0.55, c_face - spur), (a_top - run - 0.55, c_face + 0.15)]
    g.add(_prism2(pts, BED_Y - 0.3, top_y - 0.02, "stone"))

    for i in range(n):
        y = top_y - (i + 1) * rise
        a = a_top - (i + 0.5) * going
        wet = y < WATER_Y + 0.10
        mat = "algae" if wet else "stone"
        tr = M.box(going * 1.06, rise + 0.10, spur - 0.20, 0.018, mat)
        tr.rotate_y(rng.uniform(-0.006, 0.006))
        tr.translate(a, y + (rise + 0.10) * 0.5 - 0.05,
                     c_face - spur * 0.5 + 0.10)
        g.add(tr)
        if wet and i % 2 == 0:
            wd = VEG.tussock(f"{asset_id}.weed.{i}", radius=0.20, height=0.26,
                             mat="algae", blades=7)
            wd.translate(a + rng.uniform(-0.1, 0.1), y + rise * 0.5,
                         c_face - spur + rng.uniform(0.15, 0.5))
            g.add(wd)

    # Cheek wall and a hand-chain on iron stanchions: the only guard on a wharf.
    ch = M.box(0.34, 1.0, spur, 0.02, "ashlar")
    ch.translate(a_top + 0.42, top_y + 0.35, c_face - spur * 0.5)
    g.add(ch)
    posts = []
    for k in range(3):
        pa = a_top - 0.2 - k * (run * 0.5)
        py = top_y - max(0.0, (0.2 + k * run * 0.5)) * (rise / going) * 0.0
        p = M.cylinder(0.035, 0.92, 7, 0.006, "iron_pitted")
        p.translate(pa, deck_y(c_face + 0.2), c_face + 0.10)
        g.add(p)
        posts.append((pa, deck_y(c_face + 0.2) + 0.86, c_face + 0.10))
        _ = py
    for k in range(len(posts) - 1):
        g.add(K.forged_chain(f"{asset_id}.chain.{k}", posts[k], posts[k + 1],
                             sag=0.16, link=0.11))
    return run


# ---------------------------------------------------------------------------
# Boats
# ---------------------------------------------------------------------------

def _hull(asset_id, length=8.6, beam=2.55, depth=0.95, rake=0.60,
          mat="oak_weathered", tar="pine_tarred"):
    """A flat-bottomed lake lighter, built the way one is built.

    Not a lofted solid: a bottom of cross-planking, two side strakes flared
    from the chine, two raked transoms, frames and thwarts. The player looks
    DOWN into these from 2.5 m above on the quay edge, so the inside is the
    half that matters — a closed hull would read as a boat-shaped lid.

    Origin at the bottom of the hull amidships; the caller sets the draught.
    """
    rng = rng_for(asset_id, "hull")
    out = M.Group()
    N = 11
    ts = [-1.0 + 2.0 * i / N for i in range(N + 1)]

    def rise(t):
        # Flat for the middle 45 %, then the ends sweep up. A punt-built lake
        # barge has no stem: both ends are raked transoms.
        u = max(0.0, (abs(t) - 0.45) / 0.55)
        return rake * u ** 1.75

    def hb(t):
        return (beam * 0.5 - 0.26) * (1.0 - 0.68 * abs(t) ** 4)

    def hg(t):
        return (beam * 0.5) * (1.0 - 0.46 * abs(t) ** 4)

    def gun(t):
        return depth + 0.11 * t * t          # a little sheer

    half = length * 0.5

    # -- bottom: cross-planked, so the grain runs athwartships -------------
    path = [(t * half, rise(t), 0.0) for t in ts]
    prof = [[(-hb(t), 0.0), (hb(t), 0.0), (hb(t), 0.075), (-hb(t), 0.075)]
            for t in ts]
    out.add(M.sweep(prof, path, tar))

    # -- sides: one strake each, flared out from the chine ------------------
    for sgn in (1, -1):
        order = ts if sgn > 0 else ts[::-1]
        pth = [(t * half, rise(t), sgn * hb(t)) for t in order]
        pr = []
        for t in order:
            flare = hg(t) - hb(t)
            h = gun(t) - rise(t)
            pr.append([(0.0, 0.0), (0.055, 0.0), (flare + 0.055, h), (flare, h)])
        out.add(M.sweep(pr, pth, mat, cap_start=True, cap_end=True))

    # -- transoms ----------------------------------------------------------
    for sgn in (1, -1):
        t = 1.0 * sgn
        r, b, gg, gy = rise(t), hb(t), hg(t), gun(t)
        prof2 = [(-b, r), (b, r), (gg, gy), (-gg, gy)]
        tr = M.prism(prof2, 0.07, mat, chamfer=0.006)
        tr.rotate_y(-math.pi * 0.5)
        tr.rotate_z(0.0)
        tr.translate(sgn * (half - 0.03), 0.0, 0.0)
        out.add(tr)

    # -- gunwale capping, frames, floorboards, thwarts ---------------------
    for sgn in (1, -1):
        order = ts if sgn > 0 else ts[::-1]
        pth = [(t * half, gun(t), sgn * hg(t)) for t in order]
        pr = [[(-0.075, -0.045), (0.085, -0.045), (0.085, 0.035), (-0.075, 0.035)]
              for _t in order]
        out.add(M.sweep(pr, pth, "oak_dark"))

    for i in range(7):
        t = -0.78 + i * 0.26
        fr = M.box(0.075, 0.14, hb(t) * 2.0 + 0.5, 0.008, "oak_dark")
        fr.translate(t * half, rise(t) + 0.10, 0.0)
        out.add(fr)
    for i in range(3):
        t = -0.52 + i * 0.52
        th = M.plank(hg(t) * 2.0 - 0.06, 0.28, 0.045, 0.006, "oak_weathered",
                     grain_axis=1)
        th.rotate_y(math.pi * 0.5)
        th.translate(t * half, gun(t) - 0.14, 0.0)
        out.add(th)
    # Floorboards over the frames, with one board sprung loose.
    nb = 7
    for i in range(nb):
        z = -beam * 0.5 + 0.42 + i * (beam - 0.84) / max(1, nb - 1)
        fb = M.plank(length * 0.72, (beam - 0.84) / nb * 0.9, 0.032, 0.005,
                     "oak_weathered")
        lift = 0.055 if i == nb - 3 else 0.0
        fb.rotate_z(0.02 if lift else 0.0)
        fb.translate(rng.uniform(-0.2, 0.2), 0.20 + lift, z)
        out.add(fb)
    # Bilge water in the after end: a boat that has been in the rain.
    bw = M.quad(length * 0.20, beam * 0.55, "water", uv_scale=K.WATER_UV)
    bw.translate(-half * 0.62, 0.085, 0.0)
    out.add(bw)
    return out


def _lighter(ctx, g, asset_id, a, c, yaw, loaded=True, rings=(), gangway=True):
    """A moored lighter, floating at the draught its load implies.

    `rings` is `_quay_face`'s ring list; the warps are made fast to the two
    nearest, which is the difference between a moored boat and a boat with two
    ropes going nowhere.
    """
    rng = rng_for(asset_id, "lighter")
    draught = 0.36 if loaded else 0.19
    y0 = WATER_Y - draught
    b = _hull(asset_id, length=rng.uniform(8.2, 9.2), beam=rng.uniform(2.4, 2.7))

    if loaded:
        load = M.Group()
        items = []
        for i in range(5):
            items.append(K.barrel(f"{asset_id}.bar.{i}", height=0.82,
                                  belly=0.60))
        for i, it in enumerate(items):
            it.rotate_y(rng.uniform(0, 3.14))
            it.translate(-1.4 + (i % 3) * 0.72, 0.235,
                         -0.42 + (i // 3) * 0.78 + rng.uniform(-0.05, 0.05))
            load.add(it)
        for i in range(4):
            s = K.sack(f"{asset_id}.sack.{i}", height=0.52, mat="sacking")
            s.rotate_y(rng.uniform(0, 3.14))
            s.rotate_z(rng.uniform(-0.25, 0.25))
            s.translate(1.35 + rng.uniform(-0.3, 0.3), 0.235,
                        rng.uniform(-0.5, 0.5))
            load.add(s)
        # Tarpaulin turned back off the forward half — the residue that says
        # the boat is being worked right now rather than parked.
        tarp = M.sheet(2.5, 2.9,
                       lambda u, v: 0.10 * math.sin(u * 3.1) * (1 - v)
                       - 0.22 * v * v,
                       nx=9, nz=7, mat="canvas_slate", plane="xz")
        tarp.translate(-0.55, 1.16, 0.0)
        load.add(tarp)
        roll = M.cylinder(0.19, 2.35, 9, 0.01, "canvas_slate")
        roll.rotate_z(math.pi * 0.5)
        roll.rotate_y(math.pi * 0.5)
        roll.translate(0.95, 1.02, 0.0)
        load.add(roll)
        b.add(load)

    # Quant pole, bailing bucket, a coil of line — every boat has all three.
    pole = M.cylinder(0.038, 4.3, 7, 0.006, "timber_grey")
    pole.rotate_z(math.pi * 0.5)
    pole.rotate_y(0.13)
    pole.translate(-0.6, 0.98, 0.86)
    b.add(pole)
    bk = PR.bucket(f"{asset_id}.bucket", height=0.30, full=False)
    bk.rotate_z(1.35)
    bk.translate(-2.9, 0.30, 0.35)
    b.add(bk)
    cl = K.rope_coil(f"{asset_id}.coil", radius=0.24)
    cl.translate(2.6, 0.235, -0.55)
    b.add(cl)

    b.rotate_y(yaw)
    b.translate(a, y0, c)
    g.add(b)

    # Mooring lines: bow and stern, from the gunwale to a RING IN THE FACE.
    #
    # The end of a warp is not computed from the boat any more, it is looked up
    # from the wall. `rings` carries the eye of every ring `_quay_face` built,
    # and each warp is made fast to the nearest one forward and the nearest one
    # aft — so the rope arrives at a piece of ironwork that is actually there,
    # at the height it is actually at, however the boat is moved along the quay.
    ca, cc = math.cos(yaw), math.sin(yaw)
    gun_y = y0 + 0.95
    used = set()
    for sgn in (1, -1):
        # The fairlead: on the boat's inboard quarter, bow or stern.
        ba = a + ca * sgn * 3.4 + math.sin(yaw) * 1.1
        bc = c + math.cos(yaw) * 1.1
        cand = [(k, r) for k, r in enumerate(rings) if k not in used]
        if cand:
            k, (ra, ry, rc) = min(
                cand, key=lambda kr: (kr[1][0] - (a + ca * sgn * 4.3)) ** 2
                + (kr[1][2] - (c + 1.85)) ** 2)
            used.add(k)
        else:                        # no rings on this face: fall back to the
            ra, ry, rc = (a + ca * sgn * 4.3, WATER_Y + 1.0, c + 1.85)  # old point
        # Sag scales with the span, so a long lead is slack and a short one is
        # nearly straight, which is what makes a rope read as rope.
        span = math.hypot(ra - ba, rc - bc)
        rope = M.catenary((ba, gun_y, bc), (ra, ry, rc),
                          sag=min(0.42, 0.10 + 0.09 * span), mat=CORD,
                          radius=0.022, segments=7, faces=4)
        g.add(rope)

    # A plank gangway from the coping down to the gunwale. ad-town-03 §7 asks
    # for one and it is the only thing on that list the venue did not have —
    # and it is the item that makes the boats READ. The lighters float with
    # their gunwales at about -2.4 m against a deck crown of -1.44 m, so from a
    # 1.62 m eye standing on the quay the hulls are entirely behind the coping
    # and the wharf looks empty. A gangway crosses the coping: it is the thing
    # in the frame that says there is a boat down there, from the deck, from
    # the water gate and from the aerials.
    if gangway:
        ln_g = math.hypot(1.85 + 0.55, deck_y(c + 1.85) - gun_y)
        pl = M.chamfered_prism(
            [(0.0, 0.0), (ln_g, 0.0), (ln_g, 0.055), (0.0, 0.055)],
            0.62, "oak_weathered", 0.010)
        pl.rotate_z(math.atan2(deck_y(c + 1.85) - gun_y, 1.85 + 0.55))
        pl.rotate_y(-math.pi * 0.5)
        pl.translate(a + ca * 1.15, gun_y, c + 0.55)
        g.add(pl)
        # Cleats across it, so it is a gangway and not a ramp.
        for i in range(5):
            f = (i + 0.6) / 5.6
            cl2 = M.box(0.60, 0.035, 0.055, 0.006, "oak_dark")
            cl2.rotate_y(-math.pi * 0.5)
            cl2.translate(a + ca * 1.15,
                          gun_y + (deck_y(c + 1.85) - gun_y) * f + 0.055,
                          c + 0.55 + (1.85 + 0.55) * f)
            g.add(cl2)
    return b


# ---------------------------------------------------------------------------
# Drying ground: fish, nets, traps
# ---------------------------------------------------------------------------

def _net(asset_id, w=3.0, h=2.4, y=0.0, cords=11, rows=7, mat=CORD):
    """A real net: cords, not a cloth quad with a net texture on it.

    A hung net is see-through, and that is the whole of its character. At the
    gameplay camera it costs about 1,400 triangles and there are three of them.
    """
    rng = rng_for(asset_id, "net")
    out = M.Group()
    def belly(u, v):
        return -0.30 * math.sin(math.pi * u) * (0.35 + 0.65 * v)
    for i in range(cords + 1):
        u = i / cords
        x = -w * 0.5 + u * w
        pts = []
        for j in range(rows + 1):
            v = j / rows
            pts.append((x + belly(u, v) * 0.15, y - v * h,
                        belly(u, v) + rng.uniform(-0.02, 0.02)))
        for j in range(rows):
            out.add(M.tube(pts[j], pts[j + 1], 0.012, mat, segments=4))
    for j in range(rows + 1):
        v = j / rows
        pts = []
        for i in range(cords + 1):
            u = i / cords
            pts.append((-w * 0.5 + u * w + belly(u, v) * 0.15, y - v * h
                        - 0.05 * math.sin(math.pi * u), belly(u, v)))
        for i in range(cords):
            out.add(M.tube(pts[i], pts[i + 1], 0.011, mat, segments=4))
    # Cork floats along the head rope and lead weights at the foot.
    for i in range(0, cords + 1, 2):
        u = i / cords
        f = M.globe(0.055, "oak_weathered", segments=6, rings=3, sy=0.7)
        f.translate(-w * 0.5 + u * w, y + 0.06, belly(u, 0.0))
        out.add(f)
    return out


def _drying(ctx, g, asset_id, a, c, yaw=0.0):
    """Fish split and hung, a net on the frame, traps stacked where emptied.

    Laid out by workflow: the gutting board first (nearest the water), the
    racks behind it in the wind, the traps out of the way against the wall.
    """
    rng = rng_for(asset_id, "drying")
    grp = M.Group()

    # Two rack frames, 4.2 m of hanging rail each, at 1.95 m so a man ducks.
    for k in range(2):
        z = -0.9 + k * 1.8
        for sx in (-1, 1):
            p = M.box(0.14, 2.10, 0.14, 0.010, "timber_grey")
            p.translate(sx * 2.1, 1.05, z)
            grp.add(p)
            br = M.plank(0.72, 0.09, 0.08, 0.006, "timber_grey")
            br.rotate_z(-0.78 * sx)
            br.translate(sx * (2.1 - 0.24), 1.72, z)
            grp.add(br)
        rail = M.cylinder(0.045, 4.3, 7, 0.006, "timber_grey")
        rail.rotate_z(math.pi * 0.5)
        rail.translate(0.0, 1.95, z)
        grp.add(rail)
        # Split fish, hung by the tail, thinning toward one end because the
        # day's catch ran out.
        n = 14 - k * 4
        for i in range(n):
            x = -1.95 + i * (3.9 / max(1, n - 1))
            ln = rng.uniform(0.30, 0.44)
            f = M.prism([(0.0, 0.0), (0.085, -ln * 0.30), (0.055, -ln),
                         (-0.055, -ln), (-0.085, -ln * 0.30)],
                        0.028, "fish", chamfer=0.004, uv_scale=MATS.uv_detail("fish", 0.455, why="0.03 m member; the library's 1 m tile shows 3% of one tile here and reads as flat colour"))
            f.rotate_y(rng.uniform(-0.25, 0.25))
            f.rotate_z(rng.uniform(-0.09, 0.09))
            f.translate(x, 1.93, z + rng.uniform(-0.05, 0.05))
            grp.add(f)
            gut = M.cylinder(0.006, 0.10, 4, 0.0, CORD)
            gut.translate(x, 1.93, z)
            grp.add(gut)

    # A net still wet, hung on its own frame at right angles to the racks.
    for sx in (-1, 1):
        p = M.box(0.13, 2.65, 0.13, 0.010, "timber_grey")
        p.translate(sx * 1.6, 1.32, 2.6)
        grp.add(p)
    hr = M.cylinder(0.04, 3.3, 7, 0.005, "timber_grey")
    hr.rotate_z(math.pi * 0.5)
    hr.translate(0.0, 2.58, 2.6)
    grp.add(hr)
    nt = _net(f"{asset_id}.net", w=3.0, h=2.25, y=2.55)
    nt.translate(0.0, 0.0, 2.6)
    grp.add(nt)

    # Gutting board on trestles, and the ground below it dark.
    grp.add(PR.fishmonger_kit(f"{asset_id}.gut").translate(-2.6, 0.0, 2.2))

    # Eel and lobster traps, stacked askew. Withy baskets: a cone of stakes
    # bound with weavers, which is the shape that says "trap" at 20 m.
    for i in range(6):
        tp = M.Group()
        ln = rng.uniform(0.72, 0.95)
        r0 = rng.uniform(0.21, 0.27)
        for k in range(9):
            aa = k / 9 * 2 * math.pi
            st = M.cylinder(0.010, ln, 4, 0.0, "timber_grey")
            st.rotate_z(0.16)
            st.rotate_y(aa)
            st.translate(math.cos(aa) * r0, 0, math.sin(aa) * r0)
            tp.add(st)
        for k in range(4):
            hoop = M.ring(r0 + 0.02 + k * 0.028, 0.022, "timber_grey", segments=10)
            hoop.translate(0, 0.07 + k * ln * 0.28, 0)
            tp.add(hoop)
        tp.rotate_z(rng.uniform(-0.2, 0.2))
        tp.rotate_y(rng.uniform(0, 3.14))
        tp.translate(2.55 + rng.uniform(-0.35, 0.35),
                     (i // 3) * 0.52, 1.6 + (i % 3) * 0.62)
        grp.add(tp)

    grp.rotate_y(yaw)
    grp.translate(a, deck_y(c), c)
    g.add(grp)
    ctx.entity(f"{asset_id}", "prop.drying_rack", _w(a, deck_y(c), c),
               cell="J3", verbs=["inspect"])


# ---------------------------------------------------------------------------
# The treadwheel crane — slot 94, the silhouette anchor
# ---------------------------------------------------------------------------

CRANE_A, CRANE_C = 6.98, 0.07          # wharf-local, from slot 94's centre
TOWER = 3.15                            # half-width of the timber tower
HEAD = 5.60                             # tower head above the deck (slot eaves)
WHEEL_R = 2.05
AXLE_H = 2.55


def _treadwheel(asset_id, radius=WHEEL_R, width=0.90, mat="oak_weathered"):
    """One drum of the double wheel: two rims, sixteen spokes, tread boards.

    Men walk INSIDE it, so the treads face inward and the rim is open — which
    is also why it reads as a wheel and not as a disc from across the harbour.
    """
    rng = rng_for(asset_id, "wheel")
    out = M.Group()
    for sz in (-1, 1):
        for r, sec in ((radius, 0.11), (radius - 0.20, 0.075)):
            hoop = M.ring(r, sec, mat, segments=26)
            hoop.rotate_x(math.pi * 0.5)
            hoop.translate(0, 0, sz * width * 0.5)
            out.add(hoop)
    for i in range(16):
        a = i / 16 * 2 * math.pi
        for sz in (-1, 1):
            sp = M.box(0.075, radius - 0.22, 0.075, 0.008, "oak_dark")
            sp.rotate_z(a)
            sp.translate(math.sin(a) * (radius - 0.22) * 0.5,
                         math.cos(a) * (radius - 0.22) * 0.5, sz * width * 0.5)
            out.add(sp)
    for i in range(24):
        a = i / 24 * 2 * math.pi
        tb = M.plank(width - 0.06, 2 * math.pi * (radius - 0.06) / 24 * 1.04,
                     0.045, 0.006, mat, grain_axis=1)
        tb.rotate_y(math.pi * 0.5)
        tb.rotate_z(a + rng.uniform(-0.01, 0.01))
        tb.translate(math.sin(a) * (radius - 0.075),
                     math.cos(a) * (radius - 0.075), 0)
        out.add(tb)
    return out


def _crane(ctx, g, asset_id):
    """Slot 94. Timber tower, double treadwheel, slewing jib, rope and hook.

    Sized from the work: the jib tip overhangs the quay face by 1.2 m so a
    lighter lying alongside is under the hook, and the fall reaches the water,
    because a crane whose rope stops at deck level is a sculpture.
    """
    rng = rng_for(asset_id, "crane")
    grp = M.Group()
    y0 = deck_y(CRANE_C)
    yaw = 0.0

    # -- stone underbuilding: the crane's own footing on the made ground ---
    grp.add(_prism2([(-TOWER - 0.55, -TOWER - 0.55), (TOWER + 0.55, -TOWER - 0.55),
                     (TOWER + 0.55, TOWER + 0.55), (-TOWER - 0.55, TOWER + 0.55)],
                    y0 - 1.30, y0 + 0.52, "stone"))

    # -- four raking posts, cross-braced ----------------------------------
    foot, headw = TOWER, TOWER - 0.55
    posts = []
    for sx in (-1, 1):
        for sz in (-1, 1):
            p0 = (sx * foot, y0 + 0.52, sz * foot)
            p1 = (sx * headw, y0 + HEAD, sz * headw)
            grp.add(M.tube(p0, p1, 0.19, "oak_dark", segments=6))
            posts.append((p0, p1))
    # Rails at two levels, and the boarding on three sides only: the water
    # side is left open so the wheel is visible from the quay and the harbour.
    for lvl in (1.9, 4.15):
        for sz in (-1, 1):
            wf = foot + (headw - foot) * (lvl / HEAD)
            r = M.box(wf * 2.05, 0.16, 0.15, 0.010, "oak_dark")
            r.translate(0, y0 + lvl, sz * wf)
            grp.add(r)
            r2 = M.box(0.15, 0.16, wf * 2.05, 0.010, "oak_dark")
            r2.translate(sz * wf, y0 + lvl, 0)
            grp.add(r2)
    # Feather-edged boarding, laid vertically and lapped — real cladding, not
    # the picket fence a 0.24 m board on a 0.66 m pitch produced.
    #
    # Clad the landward face to the ground and the two flanks only ABOVE the
    # axle. The wheel is the thing this building exists to house and the whole
    # reason it is worth 12 m of silhouette; boarding all three sides turned it
    # into a black shed with a stick on it. Below the axle every face is open,
    # which is also how the crew and the load get in.
    for sz, sx in ((1, 0), (0, -1), (0, 1)):
        wf = foot - 0.10
        y_bot = y0 + 0.55 if sz else y0 + AXLE_H + 0.55
        y_top = y0 + HEAD - 0.15
        nb = int((wf * 1.86) / 0.235)
        for i in range(nb):
            t = (-0.93 + (i + 0.5) * 1.86 / nb)
            b = M.box(0.235 * 1.06, y_top - y_bot, 0.032, 0.005, "oak_weathered")
            b.rotate_z(rng.uniform(-0.006, 0.006))
            if sz:
                b.translate(t * wf, (y_bot + y_top) * 0.5,
                            wf + (0.012 if i % 2 else 0.0))
            else:
                b.rotate_y(math.pi * 0.5)
                b.translate(sx * (wf + (0.012 if i % 2 else 0.0)),
                            (y_bot + y_top) * 0.5, t * wf)
            grp.add(b)
    # Boarded floor for the treadwheel crew, laid on the lower rail.
    for i in range(9):
        fb = M.plank(foot * 1.9, foot * 1.9 / 9 * 0.94, 0.055, 0.006,
                     "oak_weathered", grain_axis=1)
        fb.rotate_y(math.pi * 0.5)
        fb.translate(0, y0 + 0.58, -foot * 0.95 + (i + 0.5) * foot * 1.9 / 9)
        grp.add(fb)
    # Braces on the open (water) face, so it is open but not unbraced.
    for sx in (-1, 1):
        br = M.tube((sx * foot, y0 + 0.6, -foot),
                    (sx * headw * 0.15, y0 + HEAD - 0.2, -headw),
                    0.11, "oak_dark", segments=5)
        grp.add(br)

    # -- axle, double wheel, rope drum -------------------------------------
    axle_y = y0 + AXLE_H
    grp.add(M.tube((-TOWER - 0.3, axle_y, 0), (TOWER + 0.3, axle_y, 0), 0.145,
                   "oak_dark", segments=8))
    for sx in (-1, 1):
        wh = _treadwheel(f"{asset_id}.wheel.{sx}", width=0.86)
        wh.rotate_y(math.pi * 0.5)
        wh.translate(sx * 1.14, axle_y, 0)
        grp.add(wh)
    drum = M.cylinder(0.34, 1.35, 14, 0.01, "oak_weathered")
    drum.rotate_z(math.pi * 0.5)
    drum.translate(-0.675, axle_y, 0)
    grp.add(drum)
    for k in range(6):
        hoop = M.ring(0.345, 0.05, "iron_pitted", segments=12)
        hoop.rotate_z(math.pi * 0.5)
        hoop.translate(-0.60 + k * 0.24, axle_y, 0)
        grp.add(hoop)
    # Pawl and ratchet: how a treadwheel crane holds a load.
    rat = M.lathe([(0.0, 0), (0.52, 0), (0.52, 0.07), (0.0, 0.07)], 18, "iron_pitted")
    rat.rotate_z(math.pi * 0.5)
    rat.translate(1.60, axle_y, 0)
    grp.add(rat)
    pw = M.plank(0.95, 0.10, 0.075, 0.008, "oak_dark")
    pw.rotate_z(-0.42)
    pw.translate(1.72, axle_y + 0.62, 0.30)
    grp.add(pw)

    # -- jib: two raking timbers out over the water ------------------------
    # The jib springs from a king post BELOW the wall head and passes out under
    # the eaves, which is what lets the roof stay a roof. Springing it at the
    # plate put it through its own covering.
    jib_foot_c = -TOWER + 0.15
    jib_y = y0 + HEAD - 0.95
    tip_c = -(HALF_C - CRANE_C) - 1.20        # 1.2 m past the quay face
    tip_y = y0 + 12.0
    for sx in (-1, 1):
        grp.add(M.tube((sx * 0.62, jib_y, jib_foot_c), (sx * 0.30, tip_y, tip_c),
                       0.155, "oak_dark", segments=6))
    # Cross-ties and the iron strap at the head.
    for k in range(4):
        t = 0.18 + k * 0.24
        y = jib_y + (tip_y - jib_y) * t
        c = jib_foot_c + (tip_c - jib_foot_c) * t
        w = 0.62 + (0.30 - 0.62) * t
        grp.add(M.tube((-w, y, c), (w, y, c), 0.065, "oak_dark", segments=5))
    strap = M.ring(0.30, 0.075, "iron_pitted", segments=10)
    strap.rotate_x(math.pi * 0.5 - 0.62)
    strap.translate(0, tip_y - 0.42, tip_c + 0.30)
    grp.add(strap)
    # Back-stays from the jib head down to the landward posts: the only thing
    # stopping the whole assembly falling into the harbour.
    for sx in (-1, 1):
        grp.add(M.tube((sx * 0.30, tip_y - 0.5, tip_c + 0.35),
                       (sx * headw, y0 + 1.9, headw), 0.062, "iron_pitted",
                       segments=5))

    # -- sheave, fall and hook --------------------------------------------
    sheave = M.lathe([(0.0, 0), (0.30, 0), (0.30, 0.10), (0.0, 0.10)], 14,
                     "oak_dark")
    sheave.rotate_z(math.pi * 0.5)
    sheave.translate(0, tip_y - 0.20, tip_c + 0.10)
    grp.add(sheave)
    # Drum -> jib head, then the fall down to the hook.
    grp.add(M.catenary((-0.675, axle_y + 0.34, 0.0), (0.0, tip_y - 0.22, tip_c + 0.05),
                       sag=0.10, mat=CORD, radius=0.030, segments=7, faces=4))
    hook_y = WATER_Y + 2.35
    grp.add(M.tube((0.0, tip_y - 0.30, tip_c + 0.02), (0.0, hook_y + 0.55, tip_c + 0.02),
                   0.030, CORD, segments=5))
    blk = M.box(0.24, 0.46, 0.16, 0.02, "oak_dark")
    blk.translate(0.0, hook_y + 0.30, tip_c + 0.02)
    grp.add(blk)
    hk = M.lathe([(0.055, 0.0), (0.075, 0.05), (0.055, 0.34)], 8, "iron_pitted")
    hk.translate(0.0, hook_y - 0.05, tip_c + 0.02)
    grp.add(hk)
    curl = M.ring(0.16, 0.055, "iron_pitted", segments=9)
    curl.rotate_x(math.pi * 0.5)
    curl.translate(0.0, hook_y - 0.10, tip_c + 0.16)
    grp.add(curl)

    # -- roof over the wheel, jib passing out under the eaves --------------
    # Ridge along X, so the water face is an EAVES slope and the jib leaves the
    # building under it rather than through it. Solved from the plate, not
    # placed by eye: eaves at the wall head, ridge at plate + `rise`, slope
    # length taken from the two.
    plate_y = y0 + HEAD
    half = headw + 0.55                     # plate half-span plus overhang
    rise = 2.85
    pitch = rise / half
    # `kit.gable_roof`, not a rotated slab: it lays real tile courses with a
    # ridge, a fascia and rafter feet, and it is what every other roof in
    # Hearthmere is made of. A hand-built slope here would have been one more
    # divergent implementation — the thing CLAUDE.md's working rules forbid.
    roof = K.gable_roof(headw * 2.0, headw * 2.0, f"{asset_id}.roof",
                        pitch=pitch, overhang=0.55, tile_mat="slate")
    roof.rotate_y(math.pi * 0.5)
    roof.translate(0, plate_y, 0)
    grp.add(roof)
    for sx in (-1, 1):
        gb = M.prism([(-headw, 0.0), (headw, 0.0), (0.0, headw * pitch)],
                     0.14, "oak_weathered", chamfer=0.01, uv_scale=MATS.uv_detail("oak_weathered", 1.11, why="0.14 m member; the library's 2 m tile shows 7% of one tile here and reads as flat colour"))
        gb.rotate_y(math.pi * 0.5)
        gb.translate(sx * (headw + 0.02), plate_y, 0.0)
        grp.add(gb)

    # -- counterweight box and the working residue ------------------------
    cw = _prism2([(-1.35, TOWER + 0.6), (1.35, TOWER + 0.6),
                  (1.35, TOWER + 2.3), (-1.35, TOWER + 2.3)],
                 y0 - 0.1, y0 + 1.15, "stone")
    grp.add(cw)
    cap = M.box(3.0, 0.20, 1.95, 0.02, "ashlar")
    cap.translate(0, y0 + 1.24, TOWER + 1.45)
    grp.add(cap)

    grp.rotate_y(yaw)
    grp.translate(CRANE_A, 0.0, CRANE_C)
    g.add(grp)

    # Collision: the four posts and the counterweight. The tower is walked
    # THROUGH between the posts — that is where the treadwheel crew stands.
    for sx in (-1, 1):
        for sz in (-1, 1):
            wx, _wy, wz = _w(CRANE_A + sx * TOWER, 0, CRANE_C + sz * TOWER)
            ctx.collider("cylinder", center=(wx, y0 + 2.5, wz), radius=0.26,
                         height=5.0, tag="crane_post")
    cwx, _cy, cwz = _w(CRANE_A, 0, CRANE_C + TOWER + 1.45)
    ctx.collider("box", center=(cwx, y0 + 0.6, cwz), half=(1.5, 0.7, 1.0),
                 rot_y=-math.atan2(U[1], U[0]), tag="crane_counterweight")
    ctx.entity("hm.quay.crane.01", "prop.crane",
               _w(CRANE_A, y0, CRANE_C), cell="J3", verbs=["inspect"],
               landmark={"name": "The Wharf Crane", "topY": round(y0 + 12.0, 2)})
    return grp


# ---------------------------------------------------------------------------
# The customs house — slot 61
# ---------------------------------------------------------------------------

CUSTOMS_STYLE = dict(
    name="customs_house",
    walls=["ashlar", "timber"], frame="close", roof="hip", roof_mat="slate",
    pitch=(0.94, 1.02), jetty=0.36, plinth=(0.48, 0.62), windows=2.4,
    wealth=0.85, dormers=(1, 2), chimneys=2, shutters=True,
    storey_h=(3.05, 3.30))


def _customs(ctx, slot):
    """Stone below, timber above, a stair turret, and the town weighbeam.

    The whole point of the building is the weighbeam under its canopy: a
    customs house is where goods are WEIGHED, and the beam facing the Water
    Gate is the object that says so without a word of signage (Art Bible §2).
    """
    aid = "hm.quay.customs"
    plan = BLD.plan_building(slot, CUSTOMS_STYLE, aid)
    BLD.build_building(ctx, slot, CUSTOMS_STYLE, aid, plan=plan)

    fp = plan["footprint"]
    rng = rng_for(aid, "customs")
    g = M.Group()
    hw, hd = fp.half
    floor = plan["floor_y"]
    theta = fp.theta

    def L(a, y, b):
        x, z = fp.world(a, b)
        return (x, y, z)

    # -- stair turret on the north-west angle ------------------------------
    tx, tz = fp.world(-hw + 0.35, -hd + 0.35)
    tur_h = plan["plate_y"] + 1.35
    tur = M.lathe([(1.28, 0.0), (1.28, tur_h - floor + plan["plinth_h"])], 14,
                  "ashlar", close_bottom=False, close_top=False)
    tur.translate(tx, floor - plan["plinth_h"], tz)
    g.add(tur)
    band = M.lathe([(1.34, 0.0), (1.34, 0.22)], 14, "ashlar")
    band.translate(tx, plan["plate_y"] + 0.9, tz)
    g.add(band)
    cone = M.lathe([(1.42, 0.0), (0.95, 0.62), (0.0, 1.85)], 14, "lead",
                   close_bottom=False)
    cone.translate(tx, tur_h, tz)
    g.add(cone)
    for k in range(3):
        y = floor + 1.1 + k * 1.55
        sl = M.box(0.28, 0.78, 0.20, 0.014, "oak_dark")
        sl.rotate_y(-theta + k * 1.1)
        sl.translate(tx + math.cos(k * 1.1) * 1.24, y,
                     tz + math.sin(k * 1.1) * 1.24)
        g.add(sl)

    # -- weighbeam under a canopy, facing the Water Gate -------------------
    # Local -Z is out of the front door, which faces the gate.
    bx, bz = fp.world(1.6, -hd - 2.5)
    by = float(T.height(bx, bz))
    beam = M.Group()
    for sx in (-1, 1):
        p = M.box(0.26, 3.55, 0.26, 0.014, "oak_dark")
        p.translate(sx * 1.55, 1.78, 0)
        beam.add(p)
    head = M.plank(3.6, 0.28, 0.24, 0.012, "oak_dark")
    head.translate(0, 3.62, 0)
    beam.add(head)
    # The beam itself, hanging out of balance because a scale at rest is a
    # scale nobody uses.
    piv = M.cylinder(0.05, 0.34, 8, 0.005, "iron_pitted")
    piv.rotate_z(math.pi * 0.5)
    piv.translate(-0.17, 3.42, 0)
    beam.add(piv)
    arm = M.box(2.9, 0.09, 0.09, 0.008, "iron_pitted")
    arm.rotate_z(0.085)
    arm.translate(0, 3.40, 0)
    beam.add(arm)
    for sx, drop in ((-1, 1.42), (1, 1.18)):
        for k in (-1, 1):
            beam.add(M.tube((sx * 1.42, 3.40 + sx * 0.12, 0),
                            (sx * 1.42 + k * 0.30, 3.40 + sx * 0.12 - drop, 0),
                            0.010, "iron_pitted", segments=4))
        pan = M.lathe([(0.0, 0.06), (0.46, 0.0), (0.48, 0.055)], 14, "iron_pitted",
                      close_top=False)
        pan.translate(sx * 1.42, 3.40 + sx * 0.12 - drop, 0)
        beam.add(pan)
    ws = PR.weight_set(f"{aid}.weights", count=5)
    ws.translate(1.42, 3.40 + 0.12 - 1.18 + 0.08, 0)
    beam.add(ws)
    for i in range(3):
        s = K.sack(f"{aid}.wsack.{i}", height=0.50, mat="sacking")
        s.rotate_y(rng.uniform(0, 3.1))
        s.translate(-1.42 + rng.uniform(-0.24, 0.24),
                    3.40 - 0.12 - 1.42 + 0.05 + i * 0.02,
                    rng.uniform(-0.2, 0.2))
        beam.add(s)
    # Canopy: a lean-to of pantiles on four posts.
    for sx in (-1, 1):
        for sz in (-1, 1):
            p = M.box(0.20, 3.05, 0.20, 0.012, "oak_weathered")
            p.translate(sx * 2.3, 1.52, sz * 1.5)
            beam.add(p)
    cn = M.box(5.2, 0.14, 3.5, 0.02, "terracotta")
    cn.rotate_x(-0.22)
    cn.translate(0, 3.22, 0)
    beam.add(cn)
    beam.rotate_y(-theta)
    beam.translate(bx, by, bz)
    g.add(beam)
    ctx.collider("cylinder", center=(tx, floor + 3.0, tz), radius=1.30,
                 height=6.5, tag="stair_turret")
    for sx in (-1, 1):
        for sz in (-1, 1):
            px = bx + math.cos(-theta) * sx * 2.3 + math.sin(-theta) * sz * 1.5
            pz = bz - math.sin(-theta) * sx * 2.3 + math.cos(-theta) * sz * 1.5
            ctx.collider("cylinder", center=(px, by + 1.5, pz), radius=0.16,
                         height=3.0, tag="weighbeam_post")
    ctx.entity("hm.quay.weighbeam.01", "prop.weighbeam", (bx, by, bz),
               cell="I4", verbs=["inspect"])
    ctx.emit(g)


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build(ctx: VenueContext):
    doc = json.load(open(TOWN, encoding="utf-8"))
    slots = {s["id"]: s for s in doc["buildingSlots"]}
    rng = rng_for("hm.quay", "wharf")
    g = M.Group()

    a0, a1 = -HALF_A, HALF_A
    c_sea, c_land = -HALF_C, HALF_C
    aid = "hm.quay"

    # -- 1. made ground and the deck ---------------------------------------
    # The slab runs 1.1 m past the landward edge so it dies into the gate
    # flat instead of stopping in a step at the wall.
    g.add(_slab(a0, a1, c_sea, c_land + 1.1, BED_Y - 0.2, "stone"))
    g.add(_flags(f"{aid}.deck", a0 + 0.05, a1 - 0.05, c_sea + 0.55, c_land + 1.0))

    # Cart ruts polished into the flags between the gate and the crane, and
    # the puddle that always stands in the gutter at the wall foot.
    for k in (-1, 1):
        rut = M.box(11.0, 0.03, 0.34, 0.01, "stone")
        rut.rotate_y(0.06)
        rut.translate(1.5, deck_y(2.4) - 0.028, 2.4 + k * 0.72)
        g.add(rut)
    pud = M.quad(6.5, 0.9, "water", uv_scale=K.WATER_UV)
    pud.translate(-4.0, deck_y(c_land + 0.55) + 0.012, c_land + 0.55)
    g.add(pud)

    # -- 2. quay wall on the three water faces -----------------------------
    sea_rings = _quay_face(ctx, g, f"{aid}.face.sea", (a1, c_sea), (a0, c_sea))
    _quay_face(ctx, g, f"{aid}.face.sw", (a0, c_sea), (a0, c_land), rings=False)
    _quay_face(ctx, g, f"{aid}.face.ne", (a1, 1.5), (a1, c_sea), rings=False)

    # -- 3. the ramp down through the Water Gate ---------------------------
    # `wall` builds the arch at (50, -57); this is the 0.8 m fall inside it,
    # made as a paved ramp rather than left to the pad apron, which would put
    # a 55 % pull across the one route every cart in the town takes.
    gate_a = -1.0
    ramp = M.Group()
    n = 8
    for i in range(n):
        t0, t1 = i / n, (i + 1) / n
        cz0 = c_land - 3.4 + (5.9) * t0
        cz1 = c_land - 3.4 + (5.9) * t1
        y0 = deck_y(cz0) + 0.02 + 0.50 * t0
        y1 = deck_y(cz1) + 0.02 + 0.50 * t1
        seg = M.prism([(cz0, y0 - 0.5), (cz1, y1 - 0.5), (cz1, y1), (cz0, y0)],
                      5.0, "sett", chamfer=0.0)
        seg.rotate_y(-math.pi * 0.5)
        seg.translate(gate_a, 0.0, 0.0)
        ramp.add(seg)
    g.add(ramp)
    # The threshold stone, with the cart-brake groove worn into it.
    th = M.box(5.0, 0.26, 0.85, 0.02, "ashlar")
    th.translate(gate_a, deck_y(c_land + 2.4) + 0.52 - 0.13, c_land + 2.35)
    g.add(th)
    for k in (-1, 1):
        gr = M.box(0.13, 0.09, 0.86, 0.01, "stone")
        gr.translate(gate_a + k * 0.78, deck_y(c_land + 2.4) + 0.50, c_land + 2.35)
        g.add(gr)

    # -- 4. bollards, piles and the edge --------------------------------
    for i in range(7):
        ba = a1 - 1.6 - i * 3.6
        bl = SS.bollard(f"{aid}.bollard.{i:02d}", height=0.82, kind="stone")
        bl.translate(ba, deck_y(c_sea + 0.75), c_sea + 0.75)
        g.add(bl)
        wx, _wy, wz = _w(ba, 0, c_sea + 0.75)
        ctx.collider("cylinder", center=(wx, deck_y(c_sea + 0.75) + 0.4, wz),
                     radius=0.24, height=0.82, tag="bollard")
        ctx.entity(f"hm.quay.mooring.{i:02d}", "prop.mooring_bollard",
                   _w(ba, deck_y(c_sea + 0.75), c_sea + 0.75), cell="J3",
                   verbs=["use"])
    # Fender piles driven against the face, capped with old rope grommets.
    for i in range(9):
        pa = a1 - 0.9 - i * 2.9
        pl = M.cylinder(0.20, 3.3, 9, 0.012, "pine_tarred")
        pl.rotate_z(rng.uniform(-0.02, 0.02))
        pl.translate(pa, WATER_Y - 1.5, c_sea - 0.34)
        g.add(pl)
        gm = K.rope_coil(f"{aid}.grommet.{i}", radius=0.26)
        gm.scale(1.0, 0.5, 1.0)
        gm.translate(pa, WATER_Y + 1.45, c_sea - 0.34)
        g.add(gm)

    # -- 5. the water stair and the boat hard -----------------------------
    _water_stair(ctx, g, f"{aid}.stair", a_top=-3.2, c_face=c_sea)

    hard = M.Group()
    hl, hw = 6.6, 3.6
    top_y, bot_y = deck_y(-1.0), WATER_Y - 0.45
    steps = 9
    for i in range(steps):
        t0, t1 = i / steps, (i + 1) / steps
        x0 = a0 - hl * t0
        x1 = a0 - hl * t1
        y0 = top_y + (bot_y - top_y) * t0
        y1 = top_y + (bot_y - top_y) * t1
        mat = "algae" if y1 < WATER_Y + 0.15 else "stone"
        seg = M.prism([(x0, BED_Y - 0.2), (x1, BED_Y - 0.2), (x1, y1), (x0, y0)],
                      hw, mat, chamfer=0.0)
        seg.translate(0.0, 0.0, -1.0)
        hard.add(seg)
    g.add(hard)
    # A punt hauled out on the hard, and the windlass that hauled it.
    punt = _hull(f"{aid}.punt", length=4.6, beam=1.55, depth=0.60, rake=0.42)
    punt.rotate_z(-0.14)
    punt.rotate_y(math.pi * 0.5)
    punt.translate(a0 - 2.1, top_y - 0.55, -1.0)
    g.add(punt)
    for sz in (-1, 1):
        p = M.box(0.20, 1.05, 0.20, 0.012, "oak_weathered")
        p.translate(a0 + 0.55, deck_y(-1.0) + 0.52, -1.0 + sz * 0.62)
        g.add(p)
    dr = M.cylinder(0.17, 1.5, 10, 0.008, "oak_weathered")
    dr.rotate_x(math.pi * 0.5)
    dr.translate(a0 + 0.55, deck_y(-1.0) + 0.92, -1.75)
    g.add(dr)

    # -- 6. the boats ------------------------------------------------------
    # Two lighters lying alongside the dredged face, bow-to-stern, and a
    # smaller one further along with its load out.
    _lighter(ctx, g, f"{aid}.boat.01", a=6.4, c=c_sea - 2.05, yaw=0.02,
             loaded=True, rings=sea_rings)
    _lighter(ctx, g, f"{aid}.boat.02", a=-3.4, c=c_sea - 2.15, yaw=-0.04,
             loaded=False, rings=sea_rings, gangway=False)
    for i, (a, c) in enumerate(((6.4, c_sea - 2.05), (-3.4, c_sea - 2.15))):
        wx, _wy, wz = _w(a, 0, c)
        ctx.collider("box", center=(wx, WATER_Y + 0.1, wz),
                     half=(4.4, 0.75, 1.4),
                     rot_y=-math.atan2(U[1], U[0]), tag="boat")
        ctx.entity(f"hm.quay.boat.{i + 1:02d}", "prop.boat",
                   _w(a, WATER_Y, c), cell="J3", verbs=["inspect"])

    # -- 7. the working deck: drying ground, cargo, residue ----------------
    _drying(ctx, g, f"{aid}.drying", a=-8.6, c=3.4, yaw=0.16)

    # Goods landed and waiting: stacked under the crane, where they were put
    # down, not arranged.
    for i in range(4):
        st = PR.crate_stack(f"{aid}.crates.{i}", count=int(rng.integers(2, 5)))
        st.rotate_y(rng.uniform(0, 3.14))
        ca, cc = 2.6 + i * 1.55, 4.6 + rng.uniform(-0.7, 0.7)
        st.translate(ca, deck_y(cc), cc)
        g.add(st)
    for i in range(3):
        sk = PR.sack_stack(f"{aid}.sacks.{i}", count=int(rng.integers(3, 6)))
        sk.rotate_y(rng.uniform(0, 3.14))
        ca, cc = 10.5 + rng.uniform(-0.9, 0.9), 3.2 + i * 1.4
        sk.translate(ca, deck_y(cc), cc)
        g.add(sk)
    for i in range(6):
        b = K.barrel(f"{aid}.barrel.{i}")
        b.rotate_y(rng.uniform(0, 3.14))
        ca, cc = 12.2 + rng.uniform(-1.1, 1.1), -1.4 + rng.uniform(-1.6, 1.6)
        b.translate(ca, deck_y(cc), cc)
        g.add(b)
    lb = PR.barrel_lying(f"{aid}.rolled")
    lb.rotate_y(0.7)
    lb.translate(11.0, deck_y(-3.4) + 0.31, -3.4)
    g.add(lb)
    hc = PR.handcart(f"{aid}.handcart", tipped=False)
    hc.rotate_y(2.35)
    hc.translate(-0.4, deck_y(5.2), 5.2)
    g.add(hc)

    # Residue (Art Bible §7): spilled grain trodden into the joints, a coil of
    # warp, the tar kettle, an oar left leaning, fish scales by the boards.
    g.add(PR.spill(f"{aid}.grain", kind="grain", radius=0.85,
                   centre=(10.4, 3.9)).translate(0, deck_y(3.9), 0))
    g.add(PR.spill(f"{aid}.scales", kind="chaff", radius=0.7,
                   centre=(-8.9, 5.4)).translate(0, deck_y(5.4), 0))
    for i in range(3):
        cl = K.rope_coil(f"{aid}.warp.{i}", radius=rng.uniform(0.26, 0.36))
        ca, cc = -6.6 + i * 1.35, -5.8 + rng.uniform(-0.5, 0.5)
        cl.translate(ca, deck_y(cc), cc)
        g.add(cl)
    kettle = M.lathe([(0.0, 0.0), (0.40, 0.06), (0.42, 0.46), (0.36, 0.50)], 14,
                     "iron_pitted", close_top=False)
    kettle.translate(-11.2, deck_y(-2.0) + 0.30, -2.0)
    g.add(kettle)
    for k in range(3):
        leg = M.cylinder(0.035, 0.32, 5, 0.004, "iron_pitted")
        leg.rotate_z(0.22)
        leg.rotate_y(k * 2.1)
        leg.translate(-11.2 + math.cos(k * 2.1) * 0.26, deck_y(-2.0),
                      -2.0 + math.sin(k * 2.1) * 0.26)
        g.add(leg)
    for i in range(2):
        oar = M.Group()
        sh = M.cylinder(0.036, 3.1, 6, 0.005, "timber_grey")
        oar.add(sh)
        bl = M.box(0.02, 0.95, 0.16, 0.006, "timber_grey")
        bl.translate(0, 3.35, 0)
        oar.add(bl)
        oar.rotate_z(0.30 + i * 0.05)
        oar.rotate_y(1.3 + i * 0.4)
        oar.translate(-12.0 + i * 0.35, deck_y(4.9), 4.9)
        g.add(oar)
    g.add(PR.worn_patch(f"{aid}.worn", shape="cat", size=2.2)
          .translate(gate_a, deck_y(c_land + 0.2) + 0.006, c_land + 0.2))

    # -- 8. the crane ------------------------------------------------------
    _crane(ctx, g, f"{aid}.crane")

    # -- 9. place the whole wharf and declare its ground -------------------
    ctx.emit(_place(g))

    poly = [_wxz(a, c) for a, c in ((a0, c_sea), (a1, c_sea),
                                    (a1, c_land + 1.0), (a0, c_land + 1.0))]
    ctx.collider("hull", points=poly, y0=BED_Y, y1=deck_y(0.0), kind="surface",
                 tag="wharf_deck")
    # The quay wall is solid from the deck down, so a player cannot walk out
    # of the face; the edge itself is open, because a wharf has no railing and
    # falling in is a legitimate outcome.
    for p, q in (((a0, c_sea), (a1, c_sea)), ((a0, c_sea), (a0, c_land)),
                 ((a1, 1.5), (a1, c_sea))):
        ctx.collider(COL.segment_box(_w(p[0], 0, p[1]), _w(q[0], 0, q[1]),
                                     0.9, BED_Y - 0.6, deck_y(0.0) - 0.30,
                                     kind="solid", tag="quay_wall"))

    # -- 10. the customs house --------------------------------------------
    _customs(ctx, slots["hm.slot.61.customs"])
