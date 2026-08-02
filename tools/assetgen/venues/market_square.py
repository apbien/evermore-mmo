"""Market Square — the town hub, and the focal point of the arrival shot.

The player enters through the north gate and sees this. The fountain at world
origin is what their eye lands on, so it carries more weight than any other
single object in Hearthmere.

Composition notes:
  - The square is IRREGULAR — wider at the north where Ford Road enters. It
    grew around a crossing rather than being planned, and a perfect rectangle
    would read as a car park.
  - Paving is real per-stone geometry, worn into DESIRE PATHS: polished smooth
    along the diagonals everyone walks, mossy and rough where nobody does.
  - The stalls are a separate venue and sit in the cleared bands here.
"""

from __future__ import annotations

import numpy as np

from core import mesh as M
from core import kit as K
from core import props as P
from core import terrain as TERR
from core.mathx import rng_for
from core.venue import VenueContext
from core import materials as MATS

NAME = "market_square"
CELLS = ["C3", "D3", "C4", "D4"]

# The plaza is a trapezoid: wider at the north (road mouth) than the south.
NORTH_W, SOUTH_W = 34.0, 26.0
DEPTH = 32.0


# --- the ground -----------------------------------------------------------
# This venue was authored against a flat world and its origin Y is 0, but the
# ground is a function now (Directive §6.3). Measured across the trapezoid the
# height field runs -0.525 m at the north mouth to +1.150 m at the south edge:
# 13% of the plaza had earth standing through the paving and 10% of it hung
# over a void, which is what put brown mud between the flagstones and a dark
# undercut round the fountain in `town-square.png`. The client meanwhile walks
# on `terrain.height()`, so the player's feet were up to a metre off the
# surface they could see. Nothing here may assume y = 0 any more.

# The paving is a MADE surface and stands proud of the unmade ground, at the
# same lift as the streets that run into it (kit.MADE_LIFT). Draped flush it
# was coplanar with the terrain mesh and the two z-fought into a patchwork of
# slabs and mud. Everything standing IN the square stands on the paving, so
# the whole venue takes the same lift.
LIFT = K.MADE_LIFT


def _drape(geom, offset=LIFT):
    """A SURFACE follows the ground: paving, kerbs, scattered stones."""
    return TERR.drape(geom, offset)


def _seat(geom):
    """An OBJECT is seated, not draped.

    Draping a fountain per-vertex would warp the bowl wherever the ground
    falls away under it. A basin, a trough, a post is moved bodily instead, so
    its local y = 0 lands on the paving beneath the centre of its own
    footprint and it stays rigid.
    """
    if geom is None:
        return geom
    (x0, _y0, z0), (x1, _y1, z1) = geom.bounds()
    geom.translate(0.0, _paving_y((x0 + x1) * 0.5, (z0 + z1) * 0.5), 0.0)
    return geom


def _paving_y(x, z):
    """Top of the paving at (x, z) — the surface everything here stands on."""
    return float(TERR.height(x, z)) + LIFT


def _emit(ctx, geom, **kw):
    """Seat an object, then emit it. Surfaces call `_drape` first themselves."""
    return ctx.emit(_seat(geom), **kw)


def _half_w(z):
    """Half-width of the trapezoid at depth z."""
    return (NORTH_W + (SOUTH_W - NORTH_W) * ((z + DEPTH * 0.5) / DEPTH)) * 0.5


def _plaza_tiles(ctx, n=8):
    """The walkable paving, as a grid of thin surface tiles that track it."""
    dz = DEPTH / n
    for j in range(n):
        z0 = -DEPTH * 0.5 + j * dz
        zc = z0 + dz * 0.5
        hw = _half_w(z0 + dz)          # the wider end, so tiles never gap
        dx = (hw * 2.0) / n
        for i in range(n):
            xc = -hw + (i + 0.5) * dx
            top = max(_paving_y(xc + sx * dx * 0.5, zc + sz * dz * 0.5)
                      for sx in (-0.5, 0.0, 0.5) for sz in (-0.5, 0.0, 0.5))
            ctx.collider("box", center=(xc, top - 0.15, zc),
                         half=(dx * 0.5, 0.15, dz * 0.5),
                         kind="surface", tag="plaza")


def _col(ctx, shape="box", **kw):
    """A collider matches the geometry it stands for, so it takes the same
    ground lift. `center` and `y0`/`y1` are venue-local absolutes."""
    c = kw.get("center")
    if c is not None:
        kw["center"] = (c[0], c[1] + _paving_y(c[0], c[2]), c[2])
    return ctx.collider(shape, **kw)


# --- the fountain ---------------------------------------------------------
# Hero-tier, and rebuilt for the third time. `ad-town-03.md` §(a) failed it on
# three counts and every one of them is a MEASURED count, so this pass is
# written against the numbers rather than against a description:
#
#   1. "3.0 m to the finial where I asked for 4.5-6.0" — it read at 19 px from
#      the church door at 43 m and the eye landed on a cart behind it instead.
#      Now 5.40 m to the crest, which at 43 m under the locked 55 deg rig is
#      2*atan(2.70/43) = 7.2 deg = 118 px of a 900 px frame. That is a focal
#      point; 19 px is a bollard.
#   2. "built in the same material as the ground it stands on ... it has no
#      edge and visually dissolves." The old fountain was `stone` standing on
#      `cobble` and `stone`. It is now warm `sandstone` and `ashlar_civic`
#      against the grey paving, with a `bronze` bird — three values inside the
#      object and a hard value break against the ground.
#   3. "the water can never be seen": 0.24 m of water 0.28 m BELOW a 0.90 m
#      lip on a 2.1 m bowl, so the sight-line from a standing eye cleared it
#      only inside 8 m. The lower water now sits 0.08 m under a 1.02 m lip in
#      a 5.4 m bowl, which a 1.62 m eye clears at any range. And the water is
#      no longer only horizontal: the upper tazza THROWS it, so there are ten
#      moving vertical white elements between 0.9 and 2.6 m. Falling water is
#      what makes a fountain legible at 40 m; a flat disc never was.
#
# The vertical also does a second job the town needs (§3, "no skyline"): at
# 5.4 m this is the tallest thing in the market place that is not a building,
# and it stands on the arrival axis at 43 m, in front of the guild tower at
# 71.5 m. Two anchors at different depths is what gives that frame its depth.

FOUNT_STEPS = ((4.05, 0.15), (3.66, 0.16), (3.30, 0.16))   # (radius, rise)
FOUNT_PLINTH = sum(h for _, h in FOUNT_STEPS)              # 0.47
FOUNT_LIP = 1.02                                           # basin rim
FOUNT_WATER = 0.94                                         # lower water plane
FOUNT_R = 3.05                                             # basin outer radius
TAZZA_Y, TAZZA_R = 2.55, 1.42                              # upper bowl
FOUNT_TOP = 5.40                                           # heron crest


def _heron(asset_id, mat="bronze"):
    """The town's emblem, cast in bronze, wings half-raised, beak down.

    Hearthmere is named for a heron and both the inn and the moot hall carry
    one; this is the original the others copy. It is BRONZE, not stone: the
    single darkest small mass in the market place, silhouetted against sky at
    the top of a pale shaft. That value inversion is what makes the finial
    read at 43 m — a stone bird on a stone column is one blur.
    """
    out = M.Group()
    # Legs, standing in a shallow cup of water on the column head.
    for lx in (-0.075, 0.075):
        lg = M.cylinder(0.032, 0.34, 6, 0.004, mat)
        lg.rotate_z(lx * 0.9)
        lg.translate(lx, 0.17, 0.0)
        out.add(lg)
        ft = M.chamfered_prism([(0.0, -0.05), (0.17, -0.09), (0.16, 0.02),
                                (0.0, 0.05)], 0.022, mat, 0.004)
        ft.rotate_x(-np.pi * 0.5)
        ft.translate(lx, 0.012, 0.0)
        out.add(ft)

    body = M.lathe([(0.0, 0.0), (0.16, 0.07), (0.235, 0.24), (0.20, 0.48),
                    (0.09, 0.62), (0.0, 0.66)], 12, mat)
    body.rotate_z(-0.16)
    body.translate(-0.03, 0.32, 0.0)
    out.add(body)

    # Tail, streaming back and down — the counterweight that makes a standing
    # bird read as a bird and not as a bottle.
    tail = M.chamfered_prism([(0.0, 0.10), (-0.46, -0.02), (-0.44, -0.14),
                              (0.0, -0.10)], 0.10, mat, 0.008)
    tail.rotate_x(np.pi * 0.5)
    tail.rotate_z(0.18)
    tail.translate(-0.16, 0.46, 0.0)
    out.add(tail)

    # WINGS HALF-RAISED. A heron with folded wings is a lump; the raised
    # wing is the whole silhouette, and its tips are the top of the object.
    for s in (-1, 1):
        for k, (chord, rise, thick) in enumerate(((0.62, 0.86, 0.055),
                                                  (0.50, 0.66, 0.045))):
            wg = M.chamfered_prism([(0.0, 0.0), (0.30, rise * 0.62),
                                    (0.16, rise), (-0.16, rise * 0.86),
                                    (-chord * 0.55, rise * 0.30),
                                    (-chord * 0.42, 0.0)], thick, mat, 0.008)
            wg.rotate_y(np.pi * 0.5)
            wg.rotate_x(s * (0.26 + k * 0.10))
            wg.translate(-0.02, 0.56 + k * 0.06, s * (0.17 + k * 0.05))
            out.add(wg)

    # Neck: up, over, and down. The beak points into the bowl it feeds.
    for i in range(9):
        t = i / 8.0
        r = 0.062 - t * 0.020
        seg = M.cylinder(r, 0.115, 8, 0.004, mat)
        # An S: back at the shoulder, forward and over at the crown.
        ang = -0.62 + t * 2.35
        seg.rotate_z(ang)
        seg.translate(-0.10 + np.sin(t * 2.5) * 0.30, 0.86 + t * 0.44, 0.0)
        out.add(seg)
    head = M.lathe([(0.0, 0.0), (0.055, 0.03), (0.062, 0.11), (0.0, 0.16)], 8, mat)
    head.rotate_z(1.35)
    head.translate(0.27, 1.28, 0.0)
    out.add(head)
    # Crest plume — two trailing feathers, and the highest point of the bird.
    for s in (-1, 1):
        cr = M.chamfered_prism([(0.0, 0.0), (-0.22, 0.10), (-0.24, 0.03)],
                               0.014, mat, 0.003)
        cr.rotate_x(s * 0.20)
        cr.translate(0.20, 1.36, s * 0.02)
        out.add(cr)
    beak = M.lathe([(0.046, 0.0), (0.030, 0.13), (0.0, 0.34)], 7, mat)
    beak.rotate_z(-2.05)
    beak.translate(0.33, 1.25, 0.0)
    out.add(beak)
    return out


def _heron_spout(asset_id, mat="bronze"):
    """A small cast heron head on the pedestal, throwing water into the basin.

    Four of them, on the cardinals. They are the emblem repeated at a size the
    player meets at arm's length — the fountain's own detail tier — and their
    jets are four more white verticals in the middle band of the object.
    """
    out = M.Group()
    boss = M.lathe([(0.16, 0.0), (0.20, 0.05), (0.14, 0.11)], 10, mat)
    boss.rotate_z(-np.pi * 0.5)
    out.add(boss)
    for i in range(4):
        t = i / 3.0
        seg = M.cylinder(0.058 - t * 0.016, 0.10, 7, 0.004, mat)
        seg.rotate_z(-np.pi * 0.5 + 0.42 * t)
        seg.translate(0.14 + t * 0.26, -t * 0.10, 0.0)
        out.add(seg)
    hd = M.lathe([(0.0, 0.0), (0.048, 0.03), (0.052, 0.09), (0.0, 0.13)], 8, mat)
    hd.rotate_z(-1.10)
    hd.translate(0.42, -0.11, 0.0)
    out.add(hd)
    bk = M.lathe([(0.036, 0.0), (0.0, 0.20)], 6, mat)
    bk.rotate_z(-1.95)
    bk.translate(0.52, -0.17, 0.0)
    out.add(bk)
    return out


def _fall(width, y0, y1, r0, r1, a, mat="glass", bow=0.10):
    """One falling ribbon of water, bowed outward as it leaves the rim.

    Built as a swept strip rather than a cylinder: falling water is a SHEET
    seen edge-on from most angles, and a round jet reads as a painted post —
    which is exactly what `ad-town-03.md` recorded of the old 55 mm bar.
    """
    b = M._Builder()
    n = 9
    ca, sa = np.cos(a), np.sin(a)
    prev = None
    for i in range(n + 1):
        t = i / n
        y = y0 + (y1 - y0) * t
        # Parabolic: leaves the rim outward, then falls plumb.
        r = r0 + (r1 - r0) * t + bow * np.sin(t * np.pi) * 0.8
        w = width * (1.0 - 0.28 * t)
        cx, cz = ca * r, sa * r
        tx, tz = -sa * w * 0.5, ca * w * 0.5
        cur = (np.array([cx - tx, y, cz - tz], np.float32),
               np.array([cx + tx, y, cz + tz], np.float32))
        if prev is not None:
            nrm = np.array([ca, 0.0, sa], np.float32)
            b.poly([prev[0], prev[1], cur[1], cur[0]],
                   [(0, t - 1.0 / n), (1, t - 1.0 / n), (1, t), (0, t)], nrm)
            b.poly([cur[0], cur[1], prev[1], prev[0]],
                   [(0, t), (1, t), (1, t - 1.0 / n), (0, t - 1.0 / n)], -nrm)
        prev = cur
    return b.build(mat)


def _fountain(ctx, asset_id):
    """The town's anchor: 5.40 m, two basins, ten falls and a bronze heron.

    Everything about it should say "people sit on this every day": the lip is
    dished and polished where they perch, algae grows only on the shaded north
    face, and the rim is chipped where buckets scrape it. What is new is that
    it also has to WORK at 43 m from the church door — see the block above.
    """
    rng = rng_for(asset_id, "fountain")
    out = M.Group()

    # --- stepped stylobate ------------------------------------------------
    # Three courses now, not two, and 8.1 m across the bottom tread. The mass
    # is the point: the fountain has to hold the middle of a 34 m square, and
    # a 6.3 m drum with nothing under it read as a bollard at range.
    #
    # Each tread runs all the way to the axis. It used to stop 0.10 m in, which
    # left an open annulus between the courses: from above eye level you looked
    # down those slots into unlit cavity and the town's focal point read as a
    # dark iron grating. The rings above hide the surplus; only the tread shows.
    y = 0.0
    for i, (r, h) in enumerate(FOUNT_STEPS):
        step = M.lathe([(r, 0), (r, h), (0.0, h)], 32,
                       "ashlar_civic" if i else "rubble")
        step.translate(0, y, 0)
        out.add(step)
        # Nosing course in a second stone, so the steps read as three lines and
        # not as one chamfered cone.
        nose = M.lathe([(r, h - 0.045), (r + 0.035, h - 0.030), (r, h)], 32,
                       "sandstone")
        nose.translate(0, y, 0)
        out.add(nose)
        y += h

    # --- lower basin ------------------------------------------------------
    # Outer wall, dished seating lip at 1.02 (0.55 above the top tread, which
    # is a bench), inner face, bowl floor at 0.62.
    basin = M.lathe([
        (FOUNT_R - 0.20, FOUNT_PLINTH), (FOUNT_R, FOUNT_PLINTH + 0.14),
        (FOUNT_R, FOUNT_LIP - 0.20),
        (FOUNT_R - 0.06, FOUNT_LIP - 0.08), (FOUNT_R - 0.24, FOUNT_LIP),
        (FOUNT_R - 0.34, FOUNT_LIP - 0.07),                 # dished seat
        (FOUNT_R - 0.38, FOUNT_PLINTH + 0.30),
        (FOUNT_R - 0.52, FOUNT_PLINTH + 0.16),
        (0.72, 0.60), (0.66, 0.66),                         # bowl floor
    ], 36, "sandstone", close_bottom=False)
    out.add(basin)

    # Moulded string under the rim: one shadow line all the way round, which is
    # what stops a 6 m drum reading as a flat pale band at distance.
    strg = M.lathe([(FOUNT_R + 0.02, FOUNT_LIP - 0.40),
                    (FOUNT_R + 0.13, FOUNT_LIP - 0.34),
                    (FOUNT_R + 0.11, FOUNT_LIP - 0.22),
                    (FOUNT_R + 0.01, FOUNT_LIP - 0.16)], 36, "ashlar_civic")
    out.add(strg)

    # Chipped rim: a few stones missing a corner. Perfect rims read as CAD.
    for _ in range(9):
        a = rng.uniform(0, 6.283)
        chip = M.box(rng.uniform(0.10, 0.22), 0.11, rng.uniform(0.08, 0.16),
                     0.012, "sandstone")
        chip.rotate_y(a + rng.uniform(-0.3, 0.3))
        chip.translate(np.cos(a) * (FOUNT_R - 0.28),
                       FOUNT_LIP + rng.uniform(-0.03, 0.005),
                       np.sin(a) * (FOUNT_R - 0.28))
        out.add(chip)

    # Algae on the shaded north face only (world -Z), from the waterline down
    # the outside where the overflow runs. Growth that ignores aspect is the
    # loudest "generated" tell a wet stone object can have.
    #
    # As CARDS on the drum face. The first cut built each patch as a 4-segment
    # `lathe` at r = 3.065 — which is not a short arc of a 3 m drum, it is a
    # 4.3 m SQUARE — and scaling one axis to 0.15 turned it into a 3 m green
    # plank lying across the basin. It rendered as a slab of turf in the middle
    # of the market place, and it is a good reminder that `lathe(n=4)` is a box.
    for i in range(13):
        a = -np.pi * 0.5 + rng.uniform(-0.80, 0.80)
        w = rng.uniform(0.22, 0.48)
        h = rng.uniform(0.16, 0.40)
        al = M.quad(w, h, "algae")
        al.rotate_x(-np.pi * 0.5)            # stand the card up, facing -Z
        al.rotate_y(-a - np.pi * 0.5)        # turn it onto the drum tangent
        al.translate(np.cos(a) * (FOUNT_R + 0.012),
                     FOUNT_PLINTH + rng.uniform(0.04, 0.34) + h * 0.5,
                     np.sin(a) * (FOUNT_R + 0.012))
        out.add(al)

    # --- pedestal ---------------------------------------------------------
    # Octagonal, moulded base and cap, carrying the tazza. Faceted rather than
    # round: eight flats give eight different values as the sun moves round it,
    # and a smooth cylinder at this diameter reads as a pipe.
    ped = M.lathe([(0.78, 0.60), (0.82, 0.72), (0.68, 0.86), (0.62, 1.02),
                   (0.56, 1.74), (0.60, 1.88), (0.72, 2.02), (0.76, 2.14),
                   (0.52, 2.26)], 8, "sandstone")
    ped.rotate_y(np.pi / 8.0)
    out.add(ped)

    # Four bronze heron-head spouts on the cardinals, throwing into the basin.
    for i in range(4):
        a = i * np.pi * 0.5 + np.pi * 0.25
        sp = _heron_spout(f"{asset_id}.sp{i}")
        sp.rotate_y(-a)
        sp.translate(np.cos(a) * 0.56, 1.62, np.sin(a) * 0.56)
        out.add(sp)
        out.add(_fall(0.085, 1.44, FOUNT_WATER + 0.02, 1.05, 1.34, a,
                      "water_fall", bow=0.05))

    # --- upper tazza ------------------------------------------------------
    # A shallow bowl 2.84 m across at 2.55, brimming and spilling. This is the
    # element that buys the fountain its read: a bright horizontal disc at
    # eye-plus-a-metre, with water leaving it on every side.
    tz = M.lathe([(0.50, TAZZA_Y - 0.72), (0.86, TAZZA_Y - 0.50),
                  (1.16, TAZZA_Y - 0.28), (TAZZA_R, TAZZA_Y - 0.10),
                  (TAZZA_R + 0.05, TAZZA_Y),                     # brimming rim
                  (TAZZA_R - 0.13, TAZZA_Y - 0.02),
                  (TAZZA_R - 0.22, TAZZA_Y - 0.16),
                  (0.34, TAZZA_Y - 0.30)], 28, "sandstone", close_bottom=False)
    out.add(tz)
    # Gadroons under the bowl — the one piece of carving on the object, and it
    # is on the underside because that is the face a standing player sees.
    for i in range(12):
        a = i * np.pi / 6.0
        gd = M.lathe([(0.0, 0.0), (0.075, 0.05), (0.062, 0.24), (0.0, 0.30)],
                     6, "sandstone")
        gd.rotate_z(0.34)
        gd.rotate_y(-a)
        gd.translate(np.cos(a) * 1.03, TAZZA_Y - 0.46, np.sin(a) * 1.03)
        out.add(gd)

    # Eight falls off the tazza rim into the lower basin: 1.6 m of moving white
    # on every side, and the reason this object survives at 43 m.
    for i in range(8):
        a = i * np.pi * 0.25 + 0.14
        # Three ribbons per fall at slightly different widths and radii. `foam`
        # is an alpha-MASKED material: one ribbon is mostly cut away and reads
        # as a few white flecks, which is what the first cut of this did. Three
        # overlapping masks give a broken, continuously white column, which is
        # what falling water actually looks like.
        for k, (wf, dr) in enumerate(((0.30, 0.00), (0.22, 0.055), (0.15, -0.05))):
            out.add(_fall(wf, TAZZA_Y - 0.02 - k * 0.03, FOUNT_WATER + 0.03,
                          TAZZA_R + 0.03 + dr, TAZZA_R + 0.10 + dr,
                          a + k * 0.035, "water_fall", bow=0.04))
        # A lace of foam where the sheet breaks over the rim and where it
        # lands. `foam` is masked and double-sided, so it reads as spray from
        # both faces instead of as a card.
        lc = M.quad(0.34, 0.30, "water_fall", uv_scale=MATS.uv_detail("water_fall", 0.5, why="0.34 m lace of broken water; the library's 1 m tile shows a third of one tile here and reads as flat colour"))
        lc.rotate_x(-np.pi * 0.5)
        lc.rotate_y(-a)
        lc.translate(np.cos(a) * (TAZZA_R + 0.06), TAZZA_Y - 0.06,
                     np.sin(a) * (TAZZA_R + 0.06))
        out.add(lc)
        sp = M.quad(rng.uniform(0.55, 0.85), rng.uniform(0.50, 0.75), "water_fall")
        sp.translate(np.cos(a) * (TAZZA_R + 0.24), FOUNT_WATER + 0.045,
                     np.sin(a) * (TAZZA_R + 0.24))
        out.add(sp)

    # --- upper shaft and the heron ---------------------------------------
    shaft = M.lathe([(0.42, TAZZA_Y - 0.14), (0.36, TAZZA_Y + 0.10),
                     (0.30, TAZZA_Y + 0.90), (0.34, TAZZA_Y + 1.06),
                     (0.28, TAZZA_Y + 1.18), (0.30, TAZZA_Y + 1.32),
                     (0.34, TAZZA_Y + 1.42)], 8, "sandstone")
    shaft.rotate_y(np.pi / 8.0)
    out.add(shaft)
    cup = M.lathe([(0.34, TAZZA_Y + 1.42), (0.30, TAZZA_Y + 1.48),
                   (0.10, TAZZA_Y + 1.45)], 8, "sandstone", close_bottom=False)
    out.add(cup)

    heron = _heron(f"{asset_id}.heron")
    heron.rotate_y(-0.62)                    # quartering, so it is never flat on
    heron.translate(0, TAZZA_Y + 1.45, 0)
    out.add(heron)
    # The bird's beak feeds the tazza: one plumb thread from 5.05 down to 2.53.
    out.add(_fall(0.065, TAZZA_Y + 1.30, TAZZA_Y - 0.02, 0.30, 0.24,
                  -0.62 + 0.34, "water_fall", bow=0.02))

    # --- the two water planes --------------------------------------------
    # `kit.water_disc` is the same surface the mere uses — same material, same
    # ripple scale, same depth tint — so the fountain and the harbour read as
    # the same substance (D-024). The FALLS are `water_fall`, not `foam`:
    # `foam` is alpha-MASKED, and a 0.09-0.30 m ribbon of masked lace mips
    # below the alpha-test threshold at about 10 m and is discarded entirely.
    # That is why `fountain-free` at 6 m had falling water and `t-square` at
    # 12 m had none (ad-town-05 §9). `water_fall` is BLENDED, so it has no
    # threshold to fall under and it survives to whatever range the geometry
    # does. It is also named `water*`, so client/src/water.js harvests it and
    # the falls move.
    #
    # The lower plane is 0.08 m under the lip, not 0.28 m under it: that single
    # number is the whole of §(a)'s third finding.
    # Depth 0.11, not 0.30. `kit.water_tint` drives the green toward
    # WATER_DEEP with depth, and a fountain basin is 0.3 m of clean conduit
    # water over dressed stone — at lake depth it rendered as a slab of pond.
    # Depth 0.30 and 0.14, up from 0.11 and 0.05. Those numbers were tuned when
    # the water material was an OPAQUE dark-green lake surface and a basin at
    # lake depth rendered as a slab of pond. The material is now depth-
    # transmissive with a Fresnel term (client/src/water.js), so 0.11 m of it
    # over pale dressed stone is 22 % opaque at a standing eye and the basin
    # reads DRY — which is what two art-director passes have called it. 0.30 m
    # is also simply what a fountain basin is: you can see the bottom, and you
    # can see that there is water over it.
    out.add(K.water_disc(FOUNT_R - 0.40, y=FOUNT_WATER, depth=0.30, segments=34))
    out.add(K.water_disc(TAZZA_R - 0.16, y=TAZZA_Y - 0.05, depth=0.14, segments=24))

    ctx.entity(f"{asset_id}", "prop.fountain", (0, 0, 0), cell="C4",
               verbs=["inspect", "drink"],
               landmark={"name": "The Heron Fountain", "silhouette": True},
               collider={"shape": "cylinder", "radius": FOUNT_R,
                         "height": FOUNT_LIP})
    # The basin is solid to its sitting lip. The stylobate treads are 0.16 m
    # risers — under the controller's step — so the player walks up onto them
    # and is stopped by the basin, which is exactly how people use a fountain.
    for i, (r, h) in enumerate(FOUNT_STEPS):
        top = sum(hh for _, hh in FOUNT_STEPS[:i + 1])
        _col(ctx, "cylinder", center=(0, top - h * 0.5, 0), radius=r,
             height=h, kind="surface", tag="fountain_step")
    _col(ctx, "cylinder", center=(0, FOUNT_LIP * 0.5, 0), radius=FOUNT_R,
         height=FOUNT_LIP, tag="fountain")
    return out


def _paving(ctx, asset_id):
    """Plaza paving: a tiling cobble surface plus scattered proud stones.

    Modelling every cobble is not viable at plaza scale — a 34x32m square at
    0.17m spacing is ~40,000 stones, and at 44 tris per chamfered stone that is
    1.35M triangles for the paving alone, against a 3.5M budget for the ENTIRE
    frame (Art Bible §6). The first pass did exactly that and blew the budget
    by itself.

    What shipped games do, and what we do here: carry the cobble read in the
    material (its normal/height data is strong and it tiles seamlessly), then
    scatter a few hundred PROUD stones — sunken, tilted, frost-heaved — where
    they actually matter for silhouette: kerb edges, the fountain surround, and
    the desire paths. Those are the stones that catch a grazing highlight and
    break the flatness a plain plane would have.

    Recorded as decision D-006.
    """
    rng = rng_for(asset_id, "paving")
    out = M.Group()

    # Base surface, subdivided so it can take undulation later and so vertex
    # lighting across a 34m plaza is not one flat quad.
    seg = 12
    for i in range(seg):
        for j in range(seg):
            t0, t1 = j / seg, (j + 1) / seg
            w0 = NORTH_W + (SOUTH_W - NORTH_W) * t0
            w1 = NORTH_W + (SOUTH_W - NORTH_W) * t1
            z0 = -DEPTH * 0.5 + t0 * DEPTH
            z1 = -DEPTH * 0.5 + t1 * DEPTH
            x0a, x1a = -w0 * 0.5 + i * w0 / seg, -w0 * 0.5 + (i + 1) * w0 / seg
            x0b, x1b = -w1 * 0.5 + i * w1 / seg, -w1 * 0.5 + (i + 1) * w1 / seg
            b = M._Builder()
            # Wound so the geometric normal is +Y. Listing these in increasing
            # z order gives a -Y normal and the whole plaza gets backface-culled
            # into an invisible hole — which is exactly what the first pass did.
            pts = [np.array([x0b, 0, z1], np.float32), np.array([x1b, 0, z1], np.float32),
                   np.array([x1a, 0, z0], np.float32), np.array([x0a, 0, z0], np.float32)]
            uvs = [(p[0] * 0.5, p[2] * 0.5) for p in pts]
            b.poly(pts, uvs, np.array([0, 1, 0], np.float32))
            out.add(b.build("cobble"))

    # Proud stones. Concentrated at the fountain surround and thinning outward,
    # because that is where feet, buckets and cart wheels disturb the paving.
    for i in range(340):
        a = rng.uniform(0, 6.283)
        # Bias toward the middle: sqrt gives uniform area, power > 0.5 clusters in.
        # Starts outside the fountain's 4.05 m bottom tread and its kerb.
        d = 4.75 + (rng.uniform(0, 1) ** 0.75) * 12.0
        x, z = np.cos(a) * d, np.sin(a) * d
        half_w = (NORTH_W + (SOUTH_W - NORTH_W) * ((z + DEPTH * 0.5) / DEPTH)) * 0.5
        if abs(x) > half_w - 0.6:
            continue
        s = rng.uniform(0.15, 0.26)
        h = s * rng.uniform(0.24, 0.40)
        stone = M.box(s, h, s * rng.uniform(0.8, 1.15), s * 0.20, "cobble")
        stone.rotate_y(rng.uniform(0, 3.14))
        stone.rotate_z(rng.uniform(-0.09, 0.09))   # frost-heaved, never flush
        stone.translate(x, h * rng.uniform(0.10, 0.34), z)
        out.add(stone)

    # Kerb ring around the fountain — a raised lip people trip on and sit on.
    # Pushed out to 4.45 m: the fountain's bottom tread is now 4.05 m and the
    # old 3.30 m kerb would have been buried inside its own stylobate.
    kerb = M.lathe([(4.45, 0), (4.57, 0.02), (4.59, 0.14), (4.45, 0.16)], 34,
                   "stone")
    out.add(kerb)
    return out


def _trough(asset_id):
    """Horse trough — hollowed from a single stone, green inside."""
    out = M.Group()
    shell = M.box(2.30, 0.62, 0.86, 0.03, "stone")
    shell.translate(0, 0.31, 0)
    out.add(shell)
    water = K.water_slab(2.02, 0.58, y=0.51, depth=0.16)
    out.add(water)
    for sx in (-1, 1):                      # stone feet
        f = M.box(0.26, 0.14, 0.70, 0.02, "stone")
        f.translate(sx * 0.86, 0.07, 0)
        out.add(f)
    return out


def _notice_post(asset_id):
    """A post where the town pins announcements. Pictorial only, per §2 —
    wax seals and ribbons, never lettering."""
    rng = rng_for(asset_id, "notice")
    out = M.Group()
    post = M.box(0.20, 2.55, 0.20, 0.012, "oak_weathered")
    post.translate(0, 1.27, 0)
    out.add(post)
    cap = M.prism([(-0.17, 0), (0.17, 0), (0, 0.22)], 0.34, chamfer=0.008)
    cap.translate(0, 2.55, 0)
    out.add(cap.with_material("oak_dark"))
    for i in range(5):
        n = M.box(rng.uniform(0.16, 0.24), rng.uniform(0.20, 0.30), 0.006, 0.002,
                  "parchment")
        n.rotate_z(rng.uniform(-0.14, 0.14))
        n.translate(rng.uniform(-0.04, 0.04),
                    1.35 + i * 0.19 + rng.uniform(-0.03, 0.03), -0.105)
        out.add(n)
        seal = M.lathe([(0.0, 0), (0.021, 0.004), (0.018, 0.008)], 8, "wax")
        seal.rotate_x(-np.pi * 0.5)
        seal.translate(rng.uniform(-0.05, 0.05), 1.35 + i * 0.19 + 0.07, -0.112)
        out.add(seal)
    return out


def build(ctx: VenueContext, asset_id="hm.market"):
    rng = rng_for(asset_id, "square")

    # The paving is a SURFACE, so it is draped, not seated: it has to follow
    # the 1.68 m the ground moves across the trapezoid.
    ctx.emit(_drape(_paving(ctx, asset_id)))

    # The plaza is a WALKABLE SURFACE. In v1 this venue's bounding box was
    # pushed in as a collider, so the hub of the town — the thing the arrival
    # frame is composed around — was a solid 34x32 m block the player could
    # not enter.
    #
    # It is emitted as a GRID of thin surface tiles, not one hull. The ground
    # moves 1.68 m across the trapezoid, and `Collision.groundAt` only stands
    # the player on a volume whose top is within a step of their feet: one
    # prism tall enough to span the whole fall is above reach everywhere
    # except its high corner, so it silently stops being a floor. A tile per
    # 4 m of square tracks the paving to within its own local roughness.
    _plaza_tiles(ctx)

    _emit(ctx, _fountain(ctx, f"{asset_id}.fountain.01"))

    # Trough on the road side, where carts pull up.
    tr = _trough(f"{asset_id}.trough")
    tr.rotate_y(0.10)
    tr.translate(-9.4, 0.0, -10.2)
    _emit(ctx, tr)
    _col(ctx, "box", center=(-9.4, 0.31, -10.2), half=(1.15, 0.31, 0.43),
                 rot_y=0.10, tag="trough")
    ctx.entity(f"{asset_id}.trough.01", "prop.trough", (-9.4, 0, -10.2),
               cell="C3", verbs=["inspect"])

    npost = _notice_post(f"{asset_id}.notice")
    npost.rotate_y(-0.22)
    npost.translate(6.8, 0.0, -11.6)
    _emit(ctx, npost)
    _col(ctx, "box", center=(6.8, 1.27, -11.6), half=(0.14, 1.27, 0.14),
                 rot_y=-0.22, tag="notice_post")
    ctx.entity(f"{asset_id}.notice.01", "prop.notice_post", (6.8, 0, -11.6),
               cell="D3", verbs=["read"])

    # Hitching rails near the road mouth.
    for i, (x, z, a) in enumerate([(-12.5, -6.0, 0.08), (11.8, -7.2, -0.12)]):
        rail = M.Group()
        for sx in (-1, 1):
            p = M.box(0.14, 1.15, 0.14, 0.010, "oak_weathered")
            p.translate(sx * 1.30, 0.57, 0)
            rail.add(p)
        bar = M.plank(2.90, 0.13, 0.11, 0.008, "oak_weathered")
        bar.translate(0, 1.02, 0)
        rail.add(bar)
        rail.rotate_y(a)
        rail.translate(x, 0, z)
        _emit(ctx, rail)
        _col(ctx, "box", center=(x, 0.55, z), half=(1.40, 0.55, 0.12),
                     rot_y=a, tag="hitching_rail")

    # --- residue: Art Bible §7 --------------------------------------------
    # The square is where the town's daily life leaves the most traces.

    # Broken crate nobody has cleared, half-collapsed.
    for i in range(5):
        board = M.plank(rng.uniform(0.36, 0.52), 0.11, 0.022, 0.004, "oak")
        board.rotate_y(rng.uniform(0, 3.14))
        board.rotate_z(rng.uniform(-0.25, 0.25))
        board.translate(-6.1 + rng.uniform(-0.35, 0.35), 0.035 + i * 0.022,
                        6.4 + rng.uniform(-0.35, 0.35))
        _emit(ctx, board)

    # Spilled produce, rolled into the low spots.
    for i in range(14):
        a = rng.uniform(0, 6.283)
        d = rng.uniform(0.4, 3.2)
        fruit = M.lathe([(0, 0), (0.055, 0.03), (0.06, 0.075), (0, 0.11)], 8,
                        "foliage_flower")
        fruit.translate(-5.6 + np.cos(a) * d, 0.05, 6.0 + np.sin(a) * d)
        _emit(ctx, fruit)

    # Sacks and barrels waiting to be carried in — traders stage goods here.
    for i, (x, z) in enumerate([(9.2, 4.8), (9.9, 5.6), (8.6, 5.9)]):
        s = K.sack(f"{asset_id}.sack{i}")
        s.translate(x, 0.0, z)
        _emit(ctx, s)
    for i, (x, z) in enumerate([(-10.6, 3.2), (-10.2, 4.3)]):
        b = K.barrel(f"{asset_id}.barrel{i}")
        b.translate(x, 0.0, z)
        _emit(ctx, b)

    # A stool left by the fountain, and a bucket on the lip.
    stool = M.Group()
    seat = M.lathe([(0.16, 0), (0.17, 0.035)], 12, "oak_weathered")
    seat.translate(0, 0.44, 0)
    stool.add(seat)
    for k in range(3):
        a = k * 2.094
        leg = M.cylinder(0.022, 0.45, 6, 0.004, "oak_weathered")
        leg.rotate_x(0.13 * np.cos(a))
        leg.rotate_z(0.13 * np.sin(a))
        leg.translate(np.cos(a) * 0.11, 0, np.sin(a) * 0.11)
        stool.add(leg)
    stool.translate(4.7, 0, 3.5)
    _emit(ctx, stool)

    # Bucket left standing on the basin lip, where somebody set it down to
    # gossip. Follows the rim, so it moves when the rim moves.
    buck = M.lathe([(0.125, 0), (0.145, 0.26)], 12, "oak_weathered", close_top=False)
    buck.translate(-(FOUNT_R - 0.30) * 0.72, FOUNT_LIP,
                   (FOUNT_R - 0.30) * 0.69)
    _emit(ctx, buck)

    # Two more on the bottom tread with a yoke across them: the well-house
    # feeds the conduit, but the fountain is where the whole west quarter
    # actually draws, and the queue leaves its gear on the steps.
    yb = P.yoke_and_buckets(f"{asset_id}.yoke", mode="down")
    yb.rotate_y(2.35)
    yb.translate(-3.05, 0.31, -2.55)
    _emit(ctx, yb)

    _dress_lower_market(ctx, asset_id, rng)


# --- the lower market -------------------------------------------------------

def _dress_lower_market(ctx, asset_id, rng):
    """The north half of the plaza, which is the half every hero camera sees.

    ad-town-04 §13: *the town's central space at 09:30 on a market day —
    six bare stall frames with no goods, a handful of flat grey pebbles that
    read as decals, some weed sprigs, and nothing else. No crates, no sacks,
    no barrels, no straw, no cart ruts, no dropped cabbage.* And then the
    sentence that decides where this goes: *`sty-walk-03` — a back alley — is
    the best-dressed frame in the build and it is the least important street in
    the town. The residue budget is inverted.*

    The residue this venue already had was real but it was all at +z, in the
    UPPER market behind the fountain. The `square` hero camera stands at the
    north-west corner and the arrival aperture looks in from the east, so both
    of them read the LOWER market — everything from the fountain north to the
    road mouth — and that half was bare paving. This is that half.

    It is dressed as what TOWN_PLAN says it is: fish and greens, north, where
    the wash-down drains. That decides the props. Greens leave leaf litter and
    a wet patch; fish leaves shallow crates, baskets, salt barrels and a
    scrubbed board; both leave the sweepings that the traders push to the
    gutter and nobody has carted away yet.

    Nothing here stands on the worn diagonal — `venues/streets.py KEEP_CLEAR`
    holds the same crossing clear of street furniture, and for the same reason.
    """
    # WHERE THE TWO PITCHES STAND, and it is a composition decision, not a
    # dressing one. The `square` hero camera is 9.9 m from the fountain on the
    # plaza diagonal with a 55 deg lens, so its readable wedge is narrow: at
    # 3 m across the axis it is 1.5 m wide and anything standing there is a
    # foreground obstruction, and past about 17 m to the right of the axis
    # everything falls out of frame. The first version of this dressing put the
    # greens trestle at (-8.6, -6.9), 3.3 m from that lens, and replaced a lamp
    # standard bisecting the frame with a table doing it — the exact defect
    # ad-town-04 §12 rejected, moved two metres. So both pitches sit in the
    # 10-16 m band on the frame-right side, where they read as depth behind the
    # fountain rather than as clutter in front of it, and the near ground stays
    # swept, which is also what a crossing everybody walks looks like.
    GREENS = (1.6, -6.6)
    FISH = (5.6, -2.6)

    # 1. Chalk tally on the fountain lip. WORLD_BIBLE, "Market Place", names
    #    this exactly: *chalk marks on the fountain lip where a trader tallies*.
    #    It is a dozen strokes of pale grit 3 mm proud of the coping, on the
    #    north-west arc — the side a trader standing between the fountain and
    #    the road mouth would reach. Strokes, not letters: Art Bible §2 bans
    #    readable lettering, and a tally has never been letters anyway.
    tally = M.Group()
    for i in range(14):
        a = 2.42 + i * 0.031 + rng.uniform(-0.006, 0.006)
        ln = rng.uniform(0.055, 0.105)
        gate = (i % 5 == 4)                    # every fifth stroke is the gate
        st = M.box(0.011, 0.003, ln, 0.0, "flour")
        if gate:
            st.rotate_y(0.95)
        st.rotate_y(-a)
        st.translate(np.cos(a) * (FOUNT_R - 0.30), FOUNT_LIP + 0.003,
                     np.sin(a) * (FOUNT_R - 0.30))
        tally.add(st)
    # The chalk itself, put down on the coping beside the tally.
    ck = M.box(0.055, 0.030, 0.030, 0.004, "flour")
    ck.rotate_y(0.6)
    ck.translate(np.cos(2.86) * (FOUNT_R - 0.33), FOUNT_LIP + 0.018,
                 np.sin(2.86) * (FOUNT_R - 0.33))
    tally.add(ck)
    _emit(ctx, tally)

    # 2. The greens pitch, north-west of the fountain, on the line the `square`
    #    camera reads. A trestle with the day's baskets, the empties stacked
    #    under it, and the leaf litter that comes off a cabbage before anyone
    #    buys it.
    tre = K.trestle_table(f"{asset_id}.greens.trestle", length=2.3, width=0.78)
    tre.rotate_y(-0.42)
    tre.translate(GREENS[0], 0.0, GREENS[1])
    _emit(ctx, tre)
    _col(ctx, "box", center=(GREENS[0], 0.37, GREENS[1]), half=(1.15, 0.37, 0.39),
         rot_y=-0.42, tag="trestle")
    # SIX BASKETS, ONE MESH. A woven stake basket is ~2.7 k triangles, and six
    # copies of it put the town's mesh memory over §7's 240 MB — which
    # ad-town-04 recorded at 239.4 MB and called "not a budget, it is a cliff".
    # `ctx.instance` is the answer the architecture already has: one prototype,
    # six transforms, one Unreal ISM component on import. Three on the trestle
    # at 0.74, three empties stacked under it on the paving.
    gy = _paving_y(GREENS[0], GREENS[1])
    proto = P.basket(f"{asset_id}.greens.basket", radius=0.23, height=0.26)
    xf = [(GREENS[0] + dx, gy + 0.74, GREENS[1] + dz, 0.0)
          for (dx, dz) in ((-0.72, -0.16), (0.05, 0.10), (0.78, -0.06))]
    xf += [(GREENS[0] - 0.9 + i * 0.55 + rng.uniform(-0.1, 0.1), gy,
            GREENS[1] - 1.0 + rng.uniform(-0.2, 0.2), rng.uniform(0, 3.1))
           for i in range(3)]
    ctx.instance("market_basket", proto, xf)

    # Leaf litter: outer cabbage leaves stripped at the stall and dropped. Thin
    # crumpled quads, greyed rather than the `grass_lush` emerald ad-town-04 §2
    # named as the most saturated thing in Hearthmere.
    for i in range(26):
        a, d = rng.uniform(0, 6.283), rng.uniform(0.3, 3.1)
        lf = M.quad(rng.uniform(0.10, 0.19), rng.uniform(0.08, 0.15), "foliage")
        lf.rotate_x(rng.uniform(-0.30, 0.30))
        lf.rotate_z(rng.uniform(-0.30, 0.30))
        lf.rotate_y(rng.uniform(0, 6.283))
        lf.translate(GREENS[0] + np.cos(a) * d, 0.012, GREENS[1] + np.sin(a) * d * 0.8)
        _emit(ctx, _drape(lf, LIFT + 0.012))

    # 3. The fish pitch, north-east, where the wash-down drains. Shallow crates,
    #    a salt barrel, a scrubbed board on trestles, and the wet patch that is
    #    the whole reason the fish went on the north side.
    st = P.crate_stack(f"{asset_id}.fish.crates", count=4)
    st.rotate_y(0.35)
    st.translate(FISH[0], 0.0, FISH[1])
    _emit(ctx, st)
    _col(ctx, "box", center=(FISH[0], 0.55, FISH[1]), half=(0.4, 0.55, 0.4),
         rot_y=0.35, tag="crates")
    br = K.barrel(f"{asset_id}.fish.salt")
    br.translate(FISH[0] + 1.2, 0.0, FISH[1] + 0.7)
    _emit(ctx, br)
    _col(ctx, "cylinder", center=(FISH[0] + 1.2, 0.44, FISH[1] + 0.7), radius=0.33, height=0.88,
         tag="barrel")
    bl = P.barrel_lying(f"{asset_id}.fish.empty")
    bl.rotate_y(1.15)
    bl.translate(FISH[0] + 2.0, 0.0, FISH[1] - 0.6)
    _emit(ctx, bl)
    wet = P.worn_patch(f"{asset_id}.fish.wet", shape="arc", size=1.5,
                       mat="mud_wet")
    wet.translate(FISH[0] + 0.3, 0.0, FISH[1] + 1.4)
    _emit(ctx, _drape(wet))

    # 4. The broken crate nobody has cleared — WORLD_BIBLE names it, and the
    #    one this venue had was at +z behind the fountain where no hero camera
    #    sees it. This one is on the north mouth, half in the gutter, with the
    #    sweepings piled against it.
    for i in range(6):
        board = M.plank(rng.uniform(0.34, 0.54), 0.105, 0.020, 0.004, "oak")
        board.rotate_y(rng.uniform(0, 3.14))
        board.rotate_z(rng.uniform(-0.30, 0.30))
        board.translate(-2.4 + rng.uniform(-0.4, 0.4), 0.030 + i * 0.021,
                        -11.6 + rng.uniform(-0.4, 0.4))
        _emit(ctx, _seat(board))
    sw = P.spill(f"{asset_id}.sweepings", kind="grain", radius=0.85,
                 centre=(-1.6, -11.9), density=0.9, vessel=False)
    _emit(ctx, _drape(sw))

    # 5. A handcart tipped on its shafts by the kerb, and the broom that
    #    swept the sweepings. Both read at 20 m as "somebody works here".
    hc = P.handcart(f"{asset_id}.handcart", tipped=True)
    hc.rotate_y(2.05)
    hc.translate(-4.0, 0.0, -13.0)
    _emit(ctx, _seat(hc))
    _col(ctx, "box", center=(-4.0, 0.45, -13.0), half=(0.85, 0.45, 0.55),
         rot_y=2.05, tag="handcart")
    bm = P.broom(f"{asset_id}.broom", length=1.34)
    bm.rotate_z(-0.30)
    bm.rotate_y(1.1)
    bm.translate(-2.9, 0.0, -12.5)
    _emit(ctx, _seat(bm))

    # 6. Sacks staged at the road mouth, waiting to go up to the dry market.
    ss = P.sack_stack(f"{asset_id}.mouth.sacks", count=4)
    ss.rotate_y(-0.5)
    ss.translate(2.0, 0.0, -12.6)
    _emit(ctx, _seat(ss))
    _col(ctx, "box", center=(2.0, 0.40, -12.6), half=(0.55, 0.40, 0.45),
         rot_y=-0.5, tag="sacks")
    rc = K.rope_coil(f"{asset_id}.mouth.rope", radius=0.26)
    rc.translate(3.0, 0.0, -12.0)
    _emit(ctx, _seat(rc))

    # 7. Cart ruts and hoof-worn ground at the road mouth: the plaza's paving
    #    stops being swept where the carts turn, and that is the transition the
    #    north mouth needs so it reads as a place things arrive at rather than
    #    the top edge of a paved rectangle.
    for i, (px, pz, sz) in enumerate([(-4.6, -13.2, 2.1), (0.8, -13.8, 2.6),
                                      (5.4, -12.6, 1.8), (-8.2, -11.4, 1.6)]):
        wp = P.worn_patch(f"{asset_id}.mouth.worn{i}", shape="path", size=sz,
                          mat="dirt")
        wp.rotate_y(rng.uniform(0, 3.14))
        wp.translate(px, 0.0, pz)
        _emit(ctx, _drape(wp))
