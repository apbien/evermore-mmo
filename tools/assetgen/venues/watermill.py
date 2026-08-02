"""The watermill on the Emberflow, and the granary — slots 77 and 78.

The single test this venue has to pass is stated in the brief and it is the one
every procedural mill fails: **the wheel must sit in the water and the leat
must actually deliver water to it.** A mill wheel not touching its race is the
classic tell, and it is a tell because it says nobody worked out what the
building is for.

So the whole thing is solved from levels, north to south:

    leat water surface      -2.00   impounded behind the head sluice
    launder sill            -1.90   where the water leaves the leat
    wheel axle              -2.10   `docs/areas/hearthmere/plan/schedule.md` slot 77
    wheel diameter           3.60   so the rim runs -0.30 to -3.90
    mere / river surface    -3.10   `terrain.water_level()`
    tail race invert        -3.30

Water enters the 3.60 m wheel a hand above the axle — that is what *breastshot*
means — and the rim runs 0.80 m under the tail water, so the wheel is IN its
race and the buckets on the way up are visibly wet. The mill floor is the pad
at -1.55, so from the town side the wheel is a pit; from the river and the
bridge, where the bank falls to -5.60, the whole 3.6 m of it is in the air.

The impounded leat is the one place in Hearthmere with a second water surface,
and it is not a violation of D-024: the terrain evaluator still has exactly one
water level, and this is a made channel with a dam across it, which is what a
mill leat physically is. Nothing in `content/town/terrain.json` moves. See the
note in `review/reports/waterfront.md`.

Slot 78, the granary, is the other half of the same business: staddle stones,
0.6 m clear beneath so a rat cannot climb, no ground floor at all, and a ladder
that gets taken away.
"""

from __future__ import annotations

import json
import math
import os

import numpy as np

from core import building as BLD
from core import kit as K
from core import mesh as M
from core import props as PR
from core import terrain as T
from core.mathx import rng_for
from core.venue import VenueContext, REPO

NAME = "watermill"
CELLS = ["C1", "C2", "D1", "D2", "E1", "E2"]

TOWN = os.path.join(REPO, "content/town/hearthmere.json")
MILL = "hm.slot.77.watermill"
GRANARY = "hm.slot.78.granary"

WATER_Y = T.water_level()          # -3.10
LEAT_Y = -2.00                     # impounded head water
AXLE_Y = -2.10
WHEEL_R = 1.80                     # 3.6 m diameter, per the schedule
TAIL_INVERT = -3.30

MILL_STYLE = dict(
    name="watermill",
    walls=["rubble", "timber"], frame="close", roof="gable",
    roof_mat="terracotta", pitch=(0.92, 1.00), jetty=0.0, plinth=(0.44, 0.56),
    windows=1.6, wealth=0.45, dormers=(0, 0), chimneys=1, shutters=True,
    storey_h=(3.10, 3.35))

GRANARY_STYLE = dict(
    name="granary",
    # half_hip, not gable. The gable was a workaround for `core/roof.py`'s
    # rafter feet sliding out from under the deck (they were jittered with
    # `rotate_y`, which turns about the WORLD origin, so a placed foot was
    # translated by ~r*theta and on a plate this size left the roof entirely).
    # Fixed in core/mesh.py:spin_y; the workaround is no longer needed.
    walls=["timber"], frame="square", roof="half_hip", roof_mat="terracotta",
    pitch=(0.88, 0.96), jetty=0.0, plinth=(0.10, 0.10), windows=0.5,
    wealth=0.3, dormers=(0, 0), chimneys=0, shutters=True,
    storey_h=(2.55, 2.80))

STADDLE_CLEAR = 0.62               # air under the sill, per the schedule


# ---------------------------------------------------------------------------
# The water: leat, wheel pit, tail race
# ---------------------------------------------------------------------------

def _channel(pts, half_w, invert, surface, wall_mat="stone", uv=None):
    """A stone-lined channel with water in it, along a plan polyline.

    Returns a Group. Both walls and the bed are built, so the channel is a
    trough rather than a blue ribbon lying on the ground — which is the whole
    difference between a leat and a decal.
    """
    out = M.Group()
    for i in range(len(pts) - 1):
        a = np.asarray(pts[i], float)
        b = np.asarray(pts[i + 1], float)
        d = b - a
        ln = float(np.hypot(d[0], d[1]))
        if ln < 1e-3:
            continue
        u = d / ln
        n = np.array([-u[1], u[0]])
        yaw = math.atan2(u[0], u[1]) - math.pi * 0.5
        mid = (a + b) * 0.5
        bed = M.box(ln, 0.30, half_w * 2.0, 0.02, wall_mat, uv_scale=uv)
        bed.rotate_y(yaw)
        bed.translate(mid[0], invert - 0.15, mid[1])
        out.add(bed)
        for sgn in (-1, 1):
            wl = M.box(ln, surface + 0.55 - invert, 0.42, 0.025, wall_mat,
                       uv_scale=uv)
            wl.rotate_y(yaw)
            wl.translate(mid[0] + n[0] * sgn * (half_w + 0.21),
                         (invert + surface + 0.55) * 0.5,
                         mid[1] + n[1] * sgn * (half_w + 0.21))
            out.add(wl)
        w = M.box(ln, 0.06, half_w * 2.0, 0.0, "water", uv_scale=K.WATER_UV)
        w.rotate_y(yaw)
        w.translate(mid[0], surface - 0.03, mid[1])
        out.add(w)
    return out


def _wheel(asset_id, radius=WHEEL_R, width=1.35, buckets=24):
    """A breastshot wheel: two rims, shrouds, sole boards and real buckets.

    Buckets, not paddles. A breastshot wheel is driven by the WEIGHT of water
    it carries, so the boards are set at an angle into a closed pocket between
    the shrouds; that angle is the shape that tells a player which way the
    thing turns, and it is the only part of a mill wheel anybody looks at.
    """
    rng = rng_for(asset_id, "wheel")
    out = M.Group()
    for sz in (-1, 1):
        # Shroud (the outer ring plate) and the inner rim.
        sh = M.lathe([(radius - 0.34, 0.0), (radius, 0.0), (radius, 0.075),
                      (radius - 0.34, 0.075)], 30, "oak_weathered")
        sh.rotate_z(math.pi * 0.5)
        sh.translate(sz * width * 0.5, 0, 0)
        out.add(sh)
        band = M.ring(radius + 0.02, 0.075, "iron_pitted", segments=30)
        band.rotate_z(math.pi * 0.5)
        band.translate(sz * (width * 0.5 + 0.05), 0, 0)
        out.add(band)
    for i in range(12):
        a = i / 12 * 2 * math.pi
        sp = M.box(width * 0.9, radius - 0.30, 0.085, 0.008, "oak_dark")
        sp.rotate_x(a)
        sp.rotate_y(math.pi * 0.5)
        sp.rotate_x(0.0)
        sp2 = M.box(0.085, radius - 0.30, width * 0.9, 0.008, "oak_dark")
        sp2.rotate_z(0.0)
        sp2.rotate_x(a)
        sp2.translate(0, 0, 0)
        # Spokes lie in the wheel's plane (YZ), so build them there directly.
        arm = M.box(width * 0.8, radius - 0.32, 0.09, 0.008, "oak_dark")
        arm.rotate_x(a)
        arm.translate(0, math.cos(a) * (radius - 0.32) * 0.5,
                      math.sin(a) * (radius - 0.32) * 0.5)
        out.add(arm)
        _ = (sp, sp2)
    # Sole boards close the drum; the bucket boards stand off them at an angle.
    for i in range(buckets):
        a = i / buckets * 2 * math.pi
        sole = M.plank(width - 0.10, 2 * math.pi * (radius - 0.30) / buckets * 1.05,
                       0.04, 0.005, "oak_weathered", grain_axis=0)
        sole.rotate_x(a)
        sole.translate(0, math.cos(a) * (radius - 0.30),
                       math.sin(a) * (radius - 0.30))
        out.add(sole)
        bk = M.plank(width - 0.10, 0.34, 0.038, 0.005, "oak_weathered")
        bk.rotate_x(a - 0.62)
        bk.translate(0, math.cos(a - 0.16) * (radius - 0.16),
                     math.sin(a - 0.16) * (radius - 0.16))
        out.add(bk)
        # Every fourth board is a replacement and a different colour.
        if i % 7 == 3:
            pat = M.plank(width - 0.30, 0.30, 0.030, 0.004, "oak")
            pat.rotate_x(a - 0.62)
            pat.translate(float(rng.uniform(-0.05, 0.05)),
                          math.cos(a - 0.16) * (radius - 0.13),
                          math.sin(a - 0.16) * (radius - 0.13))
            out.add(pat)
    # Axle, gudgeons and the iron hoops that hold the whole thing together.
    ax = M.cylinder(0.24, width + 3.4, 12, 0.012, "oak_dark")
    ax.rotate_z(math.pi * 0.5)
    ax.translate(-(width + 3.4) * 0.5 + width * 0.5 + 0.6, 0, 0)
    out.add(ax)
    for sz in (-1, 1):
        gd = M.cylinder(0.10, 0.55, 8, 0.006, "iron_pitted")
        gd.rotate_z(math.pi * 0.5)
        gd.translate(sz * (width * 0.5 + 0.55), 0, 0)
        out.add(gd)
    return out


def _mill_water(ctx, g, plan, rng):
    """Head race, penstock, launder, wheel, pit and tail race — in that order.

    Laid out along the fall, because that is the only order these things can be
    in: the water arrives high on the west, is held by the sluice, is let onto
    the wheel through a launder, drops 3.6 m, and leaves under the tail arch
    into the river.
    """
    fp = plan["footprint"]
    hw, hd = fp.half
    theta = fp.theta

    # The wheel stands off the river-facing gable, in a pit cut into the bank.
    # `_gable_out` is the outward normal of the gable that looks at the water.
    cand = [(fp.U[0], fp.U[1]), (-fp.U[0], -fp.U[1]),
            (fp.V[0], fp.V[1]), (-fp.V[0], -fp.V[1])]
    best, best_h = cand[0], 1e9
    for n in cand:
        px = fp.centre[0] + n[0] * (max(hw, hd) + 3.5)
        pz = fp.centre[1] + n[1] * (max(hw, hd) + 3.5)
        h = float(T.height(px, pz))
        if h < best_h:
            best_h, best = h, n
    n = best
    t = (-n[1], n[0])                      # along the gable
    reach = (hw if abs(n[0] * fp.U[0] + n[1] * fp.U[1]) > 0.7 else hd)
    wx = fp.centre[0] + n[0] * (reach + 1.55)
    wz = fp.centre[1] + n[1] * (reach + 1.55)
    yaw = math.atan2(t[0], t[1]) - math.pi * 0.5

    # -- wheel pit: two masonry cheeks and a paved invert -------------------
    for sgn in (-1, 1):
        cheek = M.box(4.6, 3.6, 0.62, 0.03, "stone")
        cheek.rotate_y(yaw)
        cheek.translate(wx + t[0] * sgn * 1.35, AXLE_Y + 0.15,
                        wz + t[1] * sgn * 1.35)
        g.add(cheek)
        ctx.collider("box", center=(wx + t[0] * sgn * 1.35, AXLE_Y + 0.15,
                                    wz + t[1] * sgn * 1.35),
                     half=(2.3, 1.8, 0.31), rot_y=yaw, tag="wheel_pit")

    # -- the wheel ---------------------------------------------------------
    wheel = _wheel(f"{MILL}.wheel")
    wheel.rotate_y(yaw)
    wheel.translate(wx, AXLE_Y, wz)
    g.add(wheel)
    # The interaction anchor is NOT the axle. The axle is at -2.10 because the
    # wheel has to dip into tail water at -3.10, and the mill's made platform
    # stands at -1.55 — so an entity on the axle is 0.55 m underground, which
    # validate calls unreachable and is right to. A player inspects the wheel
    # from the bank, at the part of it they can see: the face standing proud of
    # the pit. Anchor a metre above the ground the player is standing on, and
    # never above the rim.
    ey = min(AXLE_Y + WHEEL_R - 0.30, float(T.height(wx, wz)) + 1.00)
    ctx.entity("hm.watermill.wheel.01", "prop.mill_wheel", (wx, ey, wz),
               cell="C1", verbs=["inspect"],
               animation={"spin": {"axis": [t[0], 0, t[1]], "rpm": 6.5,
                                   "pivot": [wx, AXLE_Y, wz]}})

    # -- head race: a timber LAUNDER on trestles, along the bank ----------
    # NOT a cut channel. The leat has to arrive at -2.00, a hand above the
    # axle, and the mill pad holds the ground at -1.55 — so a trench would put
    # its water surface half a metre inside the terrain and the leat would be
    # invisible except where the bank happened to fall away. A launder carried
    # on trestle bents is what a mill on a made platform actually has, it is
    # entirely above ground so nothing has to be carved, and the long
    # horizontal it draws across the bank is the best thing in the venue's
    # silhouette.
    #
    # The direction is chosen, not assumed: whichever way along the gable the
    # ground falls faster is upstream, because that is where a leat can be
    # taken off above the wheel.
    def _ground_at(k):
        return float(T.height(wx + t[0] * k, wz + t[1] * k))
    sign = 1.0 if _ground_at(9.0) < _ground_at(-9.0) else -1.0
    tt = (t[0] * sign, t[1] * sign)
    L_len = 13.0
    bed_y = LEAT_Y - 0.42

    def _lp(k):
        return (wx + tt[0] * k, wz + tt[1] * k)
    lyaw = math.atan2(tt[0], tt[1]) - math.pi * 0.5
    # Trough: two sides, a bottom, and the water in it.
    for sgn in (-1, 1):
        side = M.box(L_len, 0.62, 0.075, 0.008, "oak_weathered")
        side.rotate_y(lyaw)
        mx, mz = _lp(1.1 + L_len * 0.5)
        side.translate(mx - tt[1] * 0.0 + (-tt[1]) * sgn * 0.78,
                       bed_y + 0.31, mz + (tt[0]) * sgn * 0.78)
        g.add(side)
    trough = M.box(L_len, 0.09, 1.55, 0.010, "oak_weathered")
    trough.rotate_y(lyaw)
    mx, mz = _lp(1.1 + L_len * 0.5)
    trough.translate(mx, bed_y + 0.045, mz)
    g.add(trough)
    lw = M.box(L_len - 0.1, 0.05, 1.42, 0.0, "water", uv_scale=K.WATER_UV)
    lw.rotate_y(lyaw)
    lw.translate(mx, LEAT_Y - 0.02, mz)
    g.add(lw)
    # Trestle bents down to the ground, each one measured, so nothing floats.
    for i in range(6):
        k = 1.6 + i * (L_len - 0.8) / 5
        bx, bz = _lp(k)
        gy = float(T.height(bx, bz))
        h = bed_y - gy
        if h < 0.25:
            continue
        for sgn in (-1, 1):
            leg = M.box(0.17, h, 0.17, 0.010, "timber_grey")
            leg.rotate_y(lyaw)
            leg.translate(bx + (-tt[1]) * sgn * 0.72, gy + h * 0.5,
                          bz + tt[0] * sgn * 0.72)
            g.add(leg)
        cap = M.plank(1.85, 0.14, 0.14, 0.008, "timber_grey")
        cap.rotate_y(lyaw + math.pi * 0.5)
        cap.translate(bx, gy + h + 0.07, bz)
        g.add(cap)
        for sgn in (-1, 1):
            br = M.tube((bx + (-tt[1]) * sgn * 0.70, gy + h * 0.35,
                         bz + tt[0] * sgn * 0.70),
                        (bx, gy + h - 0.05, bz), 0.055, "timber_grey",
                        segments=4)
            g.add(br)
        ctx.collider("cylinder", center=(bx, gy + h * 0.5, bz), radius=0.30,
                     height=h, tag="launder_bent")
    # The head intake: a masonry mouth in the bank with a hatch across it, and
    # the bywash that spills the surplus straight back down to the river.
    hx, hz = _lp(L_len + 1.6)
    hy = float(T.height(hx, hz))
    intake = M.box(3.2, max(0.9, bed_y - hy + 0.9), 2.0, 0.03, "stone")
    intake.rotate_y(lyaw)
    intake.translate(hx, (hy + bed_y + 0.9) * 0.5 - 0.45, hz)
    g.add(intake)
    ctx.collider("box", center=(hx, (hy + bed_y) * 0.5, hz),
                 half=(1.6, max(0.5, (bed_y - hy) * 0.5), 1.0), rot_y=lyaw,
                 tag="mill_intake")

    # -- tail race: out from under the wheel to the river -------------------
    tail = [(wx - tt[0] * 0.6, wz - tt[1] * 0.6),
            (wx + n[0] * 3.2 - tt[0] * 0.9, wz + n[1] * 3.2 - tt[1] * 0.9)]
    g.add(_channel(tail, 1.30, TAIL_INVERT, WATER_Y))
    # Froth where the wheel puts the water down: the one place in Hearthmere
    # that has any right to white water. `water_fall`, not `foam`: `foam` is
    # now the WRACK line — scum, duckweed and dead reed on the waterline, an
    # olive-brown thing — and aerated white water is a different substance. It
    # is also blended rather than alpha-masked, so it does not mip out of
    # existence at 10 m the way the fountain's falls did (ad-town-05 §9), and
    # it is named `water*` so client/src/water.js makes it move.
    for i in range(7):
        f = M.quad(float(rng.uniform(0.5, 1.1)), float(rng.uniform(0.4, 0.9)),
                   "water_fall")
        f.rotate_y(float(rng.uniform(0, 3.14)))
        f.translate(wx + n[0] * (1.2 + i * 0.7) + t[0] * float(rng.uniform(-0.8, 0.8)),
                    WATER_Y + 0.035,
                    wz + n[1] * (1.2 + i * 0.7) + t[1] * float(rng.uniform(-0.8, 0.8)))
        g.add(f)
    return (wx, wz, n, t, yaw)


def _mill_dressing(ctx, g, plan, rng, frame):
    """Sack hoist, lucam, meal floor residue. What a mill smells of, drawn."""
    wx, wz, n, t, yaw = frame
    fp = plan["footprint"]
    hw, hd = fp.half
    fy = plan["floor_y"]
    plate = plan["plate_y"]

    # The lucam: a projecting hoist housing over the leat side, with the sack
    # door in it and the block hanging out. A mill without one has no way of
    # getting a sack off a cart, and it is the mill's whole silhouette.
    lx = fp.centre[0] + t[0] * (hw * 0.0) - n[0] * 0.0
    _ = lx
    face_n = (-n[0], -n[1])
    ox = fp.centre[0] - n[0] * (hd if abs(n[0] * fp.V[0] + n[1] * fp.V[1]) > 0.7 else hw)
    oz = fp.centre[1] - n[1] * (hd if abs(n[0] * fp.V[0] + n[1] * fp.V[1]) > 0.7 else hw)
    luc = M.Group()
    w, d, h = 1.9, 1.5, 1.9
    for sgn in (-1, 1):
        s = M.box(0.10, h, d, 0.008, "timber_grey")
        s.translate(sgn * w * 0.5, h * 0.5, -d * 0.5)
        luc.add(s)
    front = M.box(w, h, 0.09, 0.008, "timber_grey")
    front.translate(0, h * 0.5, -d)
    luc.add(front)
    for sz in (-1, 1):
        r = M.box(w + 0.35, 0.11, d * 0.78, 0.015, "terracotta")
        r.rotate_x(sz * 0.72)
        r.translate(0, h + 0.30, -d * 0.5 + sz * d * 0.28)
        luc.add(r)
    beam = M.plank(0.16, 0.18, d + 1.1, 0.010, "oak_dark", grain_axis=1)
    beam.translate(0, h - 0.30, -d * 0.5 - 0.55)
    luc.add(beam)
    luc.add(M.tube((0.0, h - 0.38, -d - 0.95), (0.0, h - 2.35, -d - 0.95),
                   0.020, "sacking", segments=5))
    sk = K.sack(f"{MILL}.hoisted", height=0.55, mat="sacking")
    sk.translate(0.0, h - 2.90, -d - 0.95)
    luc.add(sk)
    luc.rotate_y(math.atan2(-face_n[0], -face_n[1]))
    luc.translate(ox, plate - 2.1, oz)
    g.add(luc)

    # Meal-floor residue on the ground: flour on everything within five metres,
    # sacks against the wall, a broken millstone leaning where it cracked.
    for i in range(4):
        a = float(rng.uniform(-hw * 0.7, hw * 0.7))
        b = -hd - float(rng.uniform(0.5, 1.9))
        x, z = fp.world(a, b)
        st = PR.sack_stack(f"{MILL}.sacks.{i}", count=int(rng.integers(3, 6)))
        st.rotate_y(-fp.theta + float(rng.uniform(-0.5, 0.5)))
        st.translate(x, float(T.height(x, z)), z)
        g.add(st)
    x, z = fp.world(-hw * 0.55, -hd - 1.4)
    g.add(PR.spill(f"{MILL}.flour", kind="flour", radius=1.4,
                   centre=(x, z)).translate(0, float(T.height(x, z)), 0))
    x, z = fp.world(hw * 0.65, -hd - 1.0)
    stone = M.lathe([(0.0, 0.0), (0.82, 0.0), (0.82, 0.20), (0.0, 0.20)], 20,
                    "stone")
    stone.rotate_z(math.pi * 0.5 - 0.24)
    stone.rotate_y(-fp.theta + 0.4)
    stone.translate(x, float(T.height(x, z)) + 0.80, z)
    g.add(stone)
    eye = M.cylinder(0.16, 0.26, 10, 0.01, "stone")
    eye.rotate_z(math.pi * 0.5 - 0.24)
    eye.rotate_y(-fp.theta + 0.4)
    eye.translate(x, float(T.height(x, z)) + 0.80, z)
    g.add(eye)
    _ = (wx, wz, fy, yaw)


# ---------------------------------------------------------------------------
# The granary on staddle stones
# ---------------------------------------------------------------------------

def _staddles(ctx, g, plan, rng):
    """Mushroom stones: a tapered pier and a wide flat cap a rat cannot pass.

    The cap overhang IS the machine — it is why the stone is that shape and why
    the building is worth 0.62 m of air under it. Three ranks of four, set out
    on the sill beams, not on a grid, because they carry the beams.
    """
    fp = plan["footprint"]
    hw, hd = fp.half
    sill = plan["floor_y"] - plan["plinth_h"]
    pts = []
    for i in range(4):
        for j in range(3):
            a = -hw + 0.55 + i * (hw * 2 - 1.1) / 3
            b = -hd + 0.55 + j * (hd * 2 - 1.1) / 2
            pts.append((a, b))
    for k, (a, b) in enumerate(pts):
        x, z = fp.world(a, b)
        gy = float(T.height(x, z))
        h = sill - gy - 0.18
        if h < 0.15:
            continue
        pier = M.lathe([(0.34, 0.0), (0.30, h * 0.55), (0.22, h)], 12, "stone")
        pier.translate(x, gy, z)
        g.add(pier)
        cap = M.lathe([(0.0, 0.0), (0.56, 0.05), (0.54, 0.16), (0.0, 0.18)], 14,
                      "stone")
        cap.rotate_y(float(rng.uniform(0, 3.1)))
        cap.translate(x, gy + h, z)
        g.add(cap)
        ctx.collider("cylinder", center=(x, gy + h * 0.5, z), radius=0.34,
                     height=h, tag="staddle")
    # The sill beams the stones carry, and the boarded floor on them.
    for j in range(3):
        b = -hd + 0.55 + j * (hd * 2 - 1.1) / 2
        x, z = fp.world(0.0, b)
        beam = M.plank(hw * 2.0 - 0.4, 0.22, 0.24, 0.012, "oak_dark")
        beam.rotate_y(-fp.theta)
        beam.translate(x, sill - 0.11, z)
        g.add(beam)


def _granary_dressing(ctx, g, plan, rng):
    """The ladder that gets taken away, the threshing floor, chaff and grain."""
    fp = plan["footprint"]
    hw, hd = fp.half
    sill = plan["floor_y"] - plan["plinth_h"]
    doors = plan.get("door_world") or []
    if doors:
        dx, dy, dz, _a = doors[0]
    else:
        dx, dz = fp.world(0.0, -hd)
        dy = plan["floor_y"]
    gy = float(T.height(dx, dz))
    n = (-fp.V[0], -fp.V[1])
    # A ladder, leaning, its foot 0.9 m out — the correct answer to a doorway
    # with no steps, and the reason the building works.
    lad = M.Group()
    rise = dy - gy
    run = 0.95
    length = math.hypot(rise, run) + 0.35
    for sgn in (-1, 1):
        r = M.box(0.075, length, 0.055, 0.006, "oak_weathered")
        r.translate(sgn * 0.24, length * 0.5, 0)
        lad.add(r)
    nr = max(2, int(length / 0.30))
    for k in range(nr):
        rg = M.cylinder(0.022, 0.48, 6, 0.003, "oak_weathered")
        rg.rotate_z(math.pi * 0.5)
        rg.translate(0, 0.22 + k * (length - 0.3) / max(1, nr - 1), 0)
        lad.add(rg)
    lad.rotate_x(math.atan2(run, rise))
    lad.rotate_y(math.atan2(-n[0], -n[1]))
    lad.translate(dx + n[0] * run, gy, dz + n[1] * run)
    g.add(lad)

    # The threshing floor beside it: beaten earth ringed with cobbles, chaff
    # blown to the lee side, and the flails leaning on the wall.
    tx, tz = fp.world(hw + 3.4, 0.0)
    ty = float(T.height(tx, tz))
    floor = M.box(5.4, 0.10, 4.6, 0.02, "earth")
    floor.rotate_y(-fp.theta)
    floor.translate(tx, ty + 0.03, tz)
    g.add(floor)
    g.add(PR.spill(f"{GRANARY}.chaff", kind="grain", radius=1.8,
                   centre=(tx + 1.4, tz + 0.9),
                   vessel=False).translate(0, ty + 0.06, 0))
    g.add(PR.spill(f"{GRANARY}.grain", kind="grain", radius=0.9,
                   centre=(dx + n[0] * 1.9, dz + n[1] * 1.9)).translate(0, gy, 0))
    for k in range(3):
        fl = M.Group()
        handle = M.cylinder(0.026, 1.55, 5, 0.004, "oak_weathered")
        fl.add(handle)
        swingle = M.cylinder(0.032, 0.78, 5, 0.004, "oak_dark")
        swingle.rotate_z(0.5)
        swingle.translate(0.16, 1.72, 0)
        fl.add(swingle)
        fl.rotate_z(0.22 + k * 0.05)
        fl.rotate_y(float(rng.uniform(0, 6.2)))
        px, pz = fp.world(hw + 0.35, -1.2 + k * 0.5)
        fl.translate(px, float(T.height(px, pz)), pz)
        g.add(fl)
    for k in range(4):
        wf = PR.basket(f"{GRANARY}.fan.{k}", radius=0.30, height=0.16,
                       weave="stake")
        px, pz = fp.world(hw + 2.2 + float(rng.uniform(-0.6, 0.6)),
                          -2.2 + k * 0.35)
        wf.rotate_y(float(rng.uniform(0, 3.1)))
        wf.rotate_z(0.9 if k == 0 else 0.0)
        wf.translate(px, float(T.height(px, pz)) + (0.0 if k else 0.25), pz)
        g.add(wf)
    # A cat on the staddles is the joke every granary makes; leave it as the
    # worn patch where one sleeps in the sun.
    px, pz = fp.world(0.0, hd + 1.0)
    g.add(PR.worn_patch(f"{GRANARY}.cat", shape="cat", size=0.55)
          .translate(px, float(T.height(px, pz)), pz))
    _ = sill


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build(ctx: VenueContext):
    doc = json.load(open(TOWN, encoding="utf-8"))
    slots = {s["id"]: s for s in doc["buildingSlots"]}
    g = M.Group()

    # -- the mill ----------------------------------------------------------
    rng = rng_for(MILL, "mill")
    mplan = BLD.plan_building(slots[MILL], MILL_STYLE, MILL)
    BLD.build_building(ctx, slots[MILL], MILL_STYLE, MILL, plan=mplan)
    frame = _mill_water(ctx, g, mplan, rng)
    _mill_dressing(ctx, g, mplan, rng, frame)

    # -- the granary -------------------------------------------------------
    # The plinth is overridden to a sill band before the walls are built: a
    # granary has NO ground floor, and `core.building`'s plinth would otherwise
    # bury the staddle stones the whole building exists to stand on.
    grng = rng_for(GRANARY, "granary")
    gplan = BLD.plan_building(slots[GRANARY], GRANARY_STYLE, GRANARY)
    lift = STADDLE_CLEAR + 0.30
    gplan["floor_y"] = gplan["floor_y"] + lift
    gplan["plate_y"] = gplan["plate_y"] + lift
    gplan["ridge_y"] = gplan["ridge_y"] + lift
    gplan["plinth_h"] = 0.22
    gplan["base_y"] = gplan["floor_y"] - 0.22
    BLD.build_building(ctx, slots[GRANARY], GRANARY_STYLE, GRANARY, plan=gplan)
    _staddles(ctx, g, gplan, grng)
    _granary_dressing(ctx, g, gplan, grng)
    ctx.entity("hm.granary.store.01", "container.granary",
               (gplan["footprint"].centre[0], gplan["floor_y"],
                gplan["footprint"].centre[1]), cell="E1", verbs=["inspect"])

    ctx.emit(g)
    print(f"      mill ridge {mplan['ridge_y']:.2f}, wheel axle {AXLE_Y:.2f} "
          f"(rim {AXLE_Y - WHEEL_R:.2f} to {AXLE_Y + WHEEL_R:.2f}), "
          f"tail water {WATER_Y:.2f} — wheel dips "
          f"{WATER_Y - (AXLE_Y - WHEEL_R):.2f} m")
