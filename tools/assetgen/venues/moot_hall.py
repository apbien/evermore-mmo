"""Moot Hall — slot 03. The one secular civic building, and a silhouette anchor.

Read `review/reports/ad-town-02.md` §1 before changing anything here. The art
director's finding on the arrival frame is that the player looks out of the
church door at a middle distance that is *supposed* to hold this building and
holds nothing, so the eye lands on a blank gable 110 m away. From the altar
(43, 3.30, -0.5) the moot hall stands 60 m west and 9 degrees left of the axis.
A 15.8 m bell-cote at 60 m subtends 15 degrees — a quarter of the frame height.
That is what this building is for.

## The form, and why it is that form

A market moot hall of this date is **a first-floor chamber carried on an open
arcade**. The market shelters underneath (this one is the butter market), the
council meets over it, and the two are reached separately — the market walks
straight in, the council climbs an outside stair. That single arrangement gives
the building everything a hero silhouette needs for free:

  - a **void at eye level**, so the market place reads THROUGH the building
    instead of stopping at it. From the square you see daylight, posts and
    people under a floating box. Nothing else in Hearthmere does that.
  - a **jetty**, because the chamber oversails the posts on all four sides
  - an **outside stair**, which is the one piece of civic theatre a town of
    three hundred can afford, and it faces the square
  - a **bell-cote**, because the moot bell has to be heard and cannot live in
    the church tower — the church would then own the summons

It is skewed 60 degrees to everything around it because it was built along the
old sheep-pen rail (slot note), which is also the single best thing about it in
plan: it is the one mass in the market place that is not parallel to a street.

## Function, arranged by workflow (Art Bible §7)

Under the arcade, in the order a market morning uses them: the standings (stone
slabs the butter and cheese sit on, cold and washable) — the beam scale hung
from the bressumer where the goods are weighed in front of the buyer — the
town's sealed measures fixed to the lock-up wall, which is what makes the
weighing binding — the clerk's board and box beside them. Then the lock-up
itself at the east end, then the stair, then the whipping post out on the
paving where the town could see it and now nobody looks.

## Residue

The whipping post has not been used in fifty years, and the building says so:
the shackles are seized shut with rust, the paving round its foot has gone to
moss and weed because nobody stands there, and a market basket has been left
leaning against it. That contrast — civic violence gone quietly obsolete —
buys more character than any amount of carving.
"""

from __future__ import annotations

import math

import numpy as np

from core import mesh as M
from core import kit as K
from core import props as P
from core import roof as R
from core import streetscape as S
from core import siting as SI
from core.mathx import rng_for
from core.venue import VenueContext
from core import materials as MATS

NAME = "moot_hall"
ASSET = "hm.slot.03.moot"

SITE = SI.Site(NAME)
CELLS = SITE.cells

W, D = SITE.w, SITE.d              # 13.0 x 8.0
PLAT = 0.42                        # stylobate top — "one step above the fountain"
POST_H = 2.90                      # clear head under the bressumer
JETTY = 0.42
EAVES = SITE.eaves                 # 7.20 above ground, per the schedule
PITCH = 0.96
BELL_TOP = 15.80                   # slot note; the whole point of the building

FLOOR = PLAT + POST_H + 0.34       # first-floor boards, over the bressumer
UPPER = EAVES - FLOOR              # upper storey clear height

# The lock-up takes the east end of the arcade. Stone, because it has to hold.
CELL_X0, CELL_X1 = W * 0.5 - 3.40, W * 0.5 - 0.15
CELL_Z0, CELL_Z1 = -D * 0.5 + 1.05, D * 0.5 - 0.15


# ---------------------------------------------------------------------------

def _platform(ctx, rng):
    """The stylobate, its step down to the market, and the bank behind it.

    The plot's back-east corner sits in a 1.15 m bank — the terrace the shop
    row stands on — while the rest of the footprint is market paving at 0.00.
    A constant plinth would either float over the market or bury itself in the
    bank, so the platform is retained where the ground is above it and stepped
    where the ground is below it. Directive §6.1.
    """
    g = M.Group()
    poly = SI.rect(0.0, 0.0, W + 1.30, D + 1.30)
    slab, y0 = SI.plinth_under(SITE, poly, PLAT, mat="ashlar_civic",
                               chamfer=0.035)
    g.add(slab)
    ctx.collider("box", center=SITE.p(0, (y0 + PLAT) * 0.5, 0),
                 half=((W + 1.30) * 0.5, max((PLAT - y0) * 0.5, 0.05),
                       (D + 1.30) * 0.5),
                 rot_y=SITE.yaw(), kind="surface", tag="stylobate")

    # A single 0.42 m step all round is exactly the controller's step height,
    # so it needs no flight; the nosing course is a different stone and is what
    # reads as "one step above the fountain" from across the square.
    for (cx, cz, sw, sd) in ((0.0, -(D + 1.30) * 0.5, W + 1.30, 0.42),
                             (0.0, (D + 1.30) * 0.5, W + 1.30, 0.42),
                             (-(W + 1.30) * 0.5, 0.0, 0.42, D + 1.30),
                             ((W + 1.30) * 0.5, 0.0, 0.42, D + 1.30)):
        n = SI.slab(SI.rect(cx, cz, sw, sd), PLAT - 0.055, PLAT + 0.005,
                    "stone", 0.02)
        g.add(n)

    # Where the bank is higher than the platform, retain it and climb out of
    # the corner in three treads to the upper market.
    bx, bz = W * 0.5 - 1.2, D * 0.5 + 0.9
    if SITE.ground(bx, bz) > PLAT + 0.15:
        top = SITE.ground(W * 0.5 + 0.2, D * 0.5 + 2.2)
        g.add(SI.slab(SI.rect(W * 0.5 - 1.55, D * 0.5 + 1.25, 4.2, 0.55),
                      PLAT - 0.30, top + 0.10, "rubble", 0.03))
        for i in range(3):
            t = M.box(1.55, 0.24, 0.34, 0.02, "stone")
            t.translate(W * 0.5 - 2.9, PLAT + 0.12 + i * (top - PLAT) / 3.0,
                        D * 0.5 + 0.42 + i * 0.34)
            g.add(t)
        ctx.collider("box",
                     center=SITE.p(W * 0.5 - 2.9, (PLAT + top) * 0.5,
                                   D * 0.5 + 0.76),
                     half=(0.80, max((top - PLAT) * 0.5, 0.05), 0.62),
                     rot_y=SITE.yaw(), kind="surface", tag="bank_steps")

    # Worn tracks: the market walks in at the two front bays and out at the
    # back, so those are the stones that are polished.
    for i, (wx, wz, sz) in enumerate(((-3.6, -D * 0.5 - 0.2, 1.5),
                                      (2.2, -D * 0.5 - 0.2, 1.7),
                                      (-1.0, D * 0.5 + 0.2, 1.3))):
        wp = P.worn_patch(f"{ASSET}.worn{i}", shape="path", size=sz, mat="stone")
        wp.rotate_y(rng.uniform(-0.3, 0.3))
        wp.translate(wx, PLAT + 0.012, wz)
        g.add(wp)
    return g


def _lock_up(ctx, g, rng):
    """The town gaol under the east end, and the sealed measures on its wall.

    A moot hall of this date almost always has one; it is where the constable
    puts a drunk until morning. It is here because it gives the arcade an
    asymmetric plan — a symmetrical civic building in a town where nothing else
    is symmetrical would read as a model, and the schedule already gives the
    guild that job.
    """
    cx = (CELL_X0 + CELL_X1) * 0.5
    cz = (CELL_Z0 + CELL_Z1) * 0.5
    cw, cd = CELL_X1 - CELL_X0, CELL_Z1 - CELL_Z0
    top = PLAT + POST_H + 0.10

    for (a0, a1, b0, b1) in ((CELL_X0, CELL_X1, CELL_Z0, CELL_Z0 + 0.34),
                             (CELL_X0, CELL_X1, CELL_Z1 - 0.34, CELL_Z1),
                             (CELL_X0, CELL_X0 + 0.34, CELL_Z0, CELL_Z1),
                             (CELL_X1 - 0.34, CELL_X1, CELL_Z0, CELL_Z1)):
        g.add(SI.slab([(a0, b0), (a1, b0), (a1, b1), (a0, b1)], PLAT, top,
                      "rubble", 0.035))
    # Quoins on the free angle, because the one stone corner in a timber
    # building is where the money went.
    for i in range(7):
        q = M.box(0.44 if i % 2 else 0.30, 0.30, 0.30 if i % 2 else 0.44,
                  0.02, "ashlar")
        q.translate(CELL_X0 + 0.16, PLAT + 0.20 + i * 0.36, CELL_Z0 + 0.16)
        g.add(q)

    # Door: studded oak in a chamfered stone surround, shut. It is a gaol.
    dz = CELL_Z0 - 0.02
    g.add(K.door_frame(width=0.98, height=1.95, mat="stone", depth=0.36)
          .translate(cx - 0.7, PLAT, dz))
    dr = K.plank_door(f"{ASSET}.gaol", width=0.94, height=1.90, mat="oak_dark",
                      open_angle=0.0)
    dr.translate(cx - 0.7, PLAT, dz - 0.04)
    g.add(dr)
    for r in range(4):
        for c in range(3):
            st = M.globe(0.032, "iron", 6, 3, sy=0.55)
            st.translate(cx - 1.06 + c * 0.30, PLAT + 0.42 + r * 0.40, dz - 0.10)
            g.add(st)
    SITE.entity(f"{ASSET}.lockup.01", "door.lockup",
                (cx - 0.7, PLAT, dz - 0.06), verbs=["inspect"])

    # Barred light, high and small, because that is the whole architecture of a
    # lock-up: you can hear the market and not see it.
    op = M.box(0.62, 0.44, 0.40, 0.02, "oak_dark")
    op.translate(cx + 0.95, PLAT + 1.72, dz + 0.06)
    g.add(op)
    for i in range(4):
        b = M.cylinder(0.019, 0.46, 5, 0.002, "iron_pitted")
        b.translate(cx + 0.72 + i * 0.155, PLAT + 1.72, dz - 0.03)
        g.add(b)

    # THE TOWN'S MEASURES, fixed to the wall beside the door — a bronze bushel
    # and a gallon on an oak board, and the standard ell as an iron bar let
    # into the stone with lead. Weighing is only binding against these.
    bd = M.plank(1.35, 0.86, 0.045, 0.008, "oak_dark")
    bd.translate(cx + 0.55, PLAT + 1.05, dz - 0.03)
    g.add(bd)
    bu = M.lathe([(0.0, 0), (0.20, 0.02), (0.215, 0.30), (0.235, 0.34)], 14,
                 "bronze", close_top=False)
    bu.rotate_x(-np.pi * 0.5)
    bu.translate(cx + 0.24, PLAT + 1.05, dz - 0.12)
    g.add(bu)
    gl = M.lathe([(0.0, 0), (0.105, 0.02), (0.098, 0.20), (0.115, 0.23)], 12,
                 "bronze", close_top=False)
    gl.rotate_x(-np.pi * 0.5)
    gl.translate(cx + 0.86, PLAT + 1.22, dz - 0.10)
    g.add(gl)
    ell = M.box(1.14, 0.055, 0.030, 0.004, "iron")
    ell.translate(cx + 0.55, PLAT + 0.52, dz - 0.06)
    g.add(ell)
    for sx in (-1, 1):
        pg = M.cylinder(0.020, 0.10, 6, 0.002, "lead")
        pg.rotate_x(np.pi * 0.5)
        pg.translate(cx + 0.55 + sx * 0.55, PLAT + 0.52, dz - 0.03)
        g.add(pg)
    SITE.entity(f"{ASSET}.measures.01", "prop.town_measures",
                (cx + 0.55, PLAT + 1.05, dz - 0.14), verbs=["inspect"])

    # The clerk's stool and box live under the board, because that is where he
    # sits to witness a weighing.
    g.add(P.stool(f"{ASSET}.clerk", height=0.52)
          .translate(cx + 1.35, PLAT, dz - 0.62))
    g.add(P.crate(f"{ASSET}.clerkbox", size=0.42, height=0.30, lid=True)
          .translate(cx + 1.25, PLAT, dz - 1.05))

    SITE.collider_walls(cw, cd, POST_H, y=PLAT, thickness=0.34,
                        center=(cx, cz), doors=[], tag="lockup")
    return top


def _arcade(ctx, g, rng):
    """Ten oak posts, the bressumer they carry, and the floor over them.

    The posts are on the perimeter only — four to each long side, one to each
    end — so the market really does flow under and round, which is the whole
    reason the building is on stilts. Every post stands on its own pad-stone;
    none of them touches the ground.
    """
    xs = [-W * 0.5 + 0.55 + i * (W - 1.10) / 3.0 for i in range(4)]
    posts = ([(x, -D * 0.5 + 0.55) for x in xs] +
             [(x, D * 0.5 - 0.55) for x in xs] +
             [(-W * 0.5 + 0.55, 0.0), (W * 0.5 - 0.55, 0.0)])
    head = PLAT + POST_H

    for i, (px, pz) in enumerate(posts):
        if CELL_X0 - 0.3 < px < CELL_X1 + 0.3 and CELL_Z0 - 0.3 < pz < CELL_Z1 + 0.3:
            continue                       # the lock-up wall carries this bay
        pad = M.box(0.58, 0.16, 0.58, 0.02, "ashlar", uv_scale=MATS.uv_detail("ashlar", 1.11, why="0.58 m member; the library's 2 m tile shows 29% of one tile here and reads as flat colour"))
        pad.translate(px, PLAT + 0.08, pz)
        g.add(pad)
        # Slight taper and a hand-adzed lean: ten identical extrusions is the
        # loudest generated tell an arcade can have.
        po = M.box(0.30, POST_H - 0.16, 0.28, 0.022, "oak")
        po.rotate_y(rng.uniform(-0.035, 0.035))
        po.rotate_z(rng.uniform(-0.008, 0.008))
        po.translate(px, PLAT + 0.16 + (POST_H - 0.16) * 0.5, pz)
        g.add(po)
        # Jowl at the head — the swelling that lets one post carry both the
        # bressumer and the cross beam. It is also what says "oak", not "pine".
        jw = M.lathe([(0.20, 0.0), (0.23, 0.16), (0.20, 0.34)], 8, "oak")
        jw.translate(px, head - 0.34, pz)
        g.add(jw)
        ctx.collider("cylinder", center=SITE.p(px, PLAT + POST_H * 0.5, pz),
                     radius=0.24, height=POST_H, tag="arcade_post")

    # Bressumer round all four sides, carried on the post heads.
    for (bx, bz, bw, bd_) in ((0.0, -D * 0.5 + 0.55, W - 0.7, 0.34),
                              (0.0, D * 0.5 - 0.55, W - 0.7, 0.34),
                              (-W * 0.5 + 0.55, 0.0, 0.34, D - 0.7),
                              (W * 0.5 - 0.55, 0.0, 0.34, D - 0.7)):
        bm = M.box(bw, 0.36, bd_, 0.02, "oak_dark")
        bm.translate(bx, head + 0.18, bz)
        g.add(bm)

    # Curved braces, post head to bressumer. Two per post, in the plane of the
    # frame — the diagonal is what stops an arcade reading as scaffolding.
    for (px, pz) in posts:
        if CELL_X0 - 0.3 < px < CELL_X1 + 0.3 and CELL_Z0 - 0.3 < pz < CELL_Z1 + 0.3:
            continue
        along_x = abs(pz) > D * 0.25
        for s in (-1, 1):
            L = 0.82
            br = M.chamfered_prism(
                [(0.0, 0.0), (L, L), (L, L - 0.16), (0.20, 0.0)], 0.14,
                "oak", 0.012, uv_scale=MATS.uv_detail("oak", 1.43, why="0.14 m member; the library's 2 m tile shows 7% of one tile here and reads as flat colour"))
            br.rotate_z(0.0)
            if along_x:
                br.scale(s, 1.0, 1.0)
                br.translate(px + s * 0.14, head - 0.34, pz)
            else:
                br.rotate_y(np.pi * 0.5)
                br.scale(1.0, 1.0, s)
                br.translate(px, head - 0.34, pz + s * 0.14)
            g.add(br)

    # Floor: joists across the short span, boarded over. Seen from below by
    # everybody who ever shelters here, so it is real joists, not a slab.
    n = int((W - 0.6) / 0.62)
    for i in range(n):
        jx = -W * 0.5 + 0.9 + i * (W - 1.8) / max(n - 1, 1)
        jo = M.box(0.11, 0.22, D - 0.9, 0.012, "oak")
        jo.translate(jx, head + 0.11, 0.0)
        g.add(jo)
    bo = M.box(W + JETTY * 2 - 0.1, 0.06, D + JETTY * 2 - 0.1, 0.012,
               "oak_weathered")
    bo.translate(0, head + 0.28, 0)
    g.add(bo)

    # The jetty bracket course: the chamber oversails the arcade on all four
    # sides, and the brackets are what carry it.
    for i, (bx, bz, ry) in enumerate(
            [(x, -D * 0.5, 0.0) for x in np.linspace(-W * 0.42, W * 0.42, 5)] +
            [(x, D * 0.5, np.pi) for x in np.linspace(-W * 0.42, W * 0.42, 5)] +
            [(-W * 0.5, z, np.pi * 0.5) for z in (-2.0, 2.0)] +
            [(W * 0.5, z, -np.pi * 0.5) for z in (-2.0, 2.0)]):
        co = K.corbel(f"{ASSET}.cb{i}", project=JETTY + 0.10, width=0.24,
                      height=0.30, mat="oak_dark")
        co.rotate_y(ry)
        co.translate(bx, head - 0.06, bz)
        g.add(co)
    return head


def _chamber(ctx, g, rng):
    """The council chamber: one room, jettied, close-studded, well glazed.

    Close studding and glass are how a pre-industrial town says "this cost
    money" without carving anything, and the chamber is the only room in
    Hearthmere that the whole town paid for.
    """
    uw, ud = W + JETTY * 2, D + JETTY * 2
    y0 = FLOOR
    # Four lights, and NOT on a regular pitch. The pair over the standings is
    # close-coupled because that is where the chamber's own table stands; the
    # east light is wider and set alone because the mayor's seat is under it.
    # Art Bible §6: no element three times in a row without a variant.
    wins_front = [(-4.75, 1.00, 1.30), (-2.95, 0.94, 1.22),
                  (0.95, 1.06, 1.30), (4.35, 1.24, 1.44)]

    front = K.timber_frame_wall(
        uw, UPPER, f"{ASSET}.uf", style="close", sill_y=y0,
        openings=[(x, 1.60, w + 0.16, h + 0.14) for x, w, h in wins_front] +
                 [(-uw * 0.5 + 1.45, 1.12, 1.25, 2.24)])
    front.translate(0, 0, -ud * 0.5)
    g.add(front)

    back = K.timber_frame_wall(uw, UPPER, f"{ASSET}.ub", style="close",
                               sill_y=y0, openings=[(x, 1.60, 1.05, 1.30)
                                         for x in (-3.2, 0.6, 3.9)])
    back.rotate_y(np.pi)
    back.translate(0, 0, ud * 0.5)
    g.add(back)

    for sx in (-1, 1):
        side = K.timber_frame_wall(ud, UPPER, f"{ASSET}.us{sx}", style="close",
                                   sill_y=y0, openings=[(0.0, 1.72, 1.20, 1.45)])
        side.rotate_y(sx * np.pi * 0.5)
        side.translate(sx * uw * 0.5, 0, 0)
        g.add(side)

    for i, (x, ww, wh) in enumerate(wins_front):
        w = K.leaded_window(f"{ASSET}.w{i}", width=ww, height=wh,
                            mat="glass_lit" if i == 3 else "glass",
                            shutters=False)
        w.translate(x, y0 + 1.60, -ud * 0.5 - 0.07)
        g.add(w)

    # The town's arms on a painted board over the chamber door — a heron, the
    # bird the fountain and the inn are both named for. Pictorial, Art Bible §2:
    # a moot hall identifies itself by device, never by lettering.
    ar = M.chamfered_prism([(-0.62, 0.28), (0.0, 0.0), (0.62, 0.28),
                            (0.62, 1.02), (-0.62, 1.02)], 0.07,
                           "painted_crimson", 0.012, uv_scale=MATS.uv_detail("painted_crimson", 0.833, why="0.07 m member; the library's 2 m tile shows 4% of one tile here and reads as flat colour"))
    ar.translate(-uw * 0.5 + 3.35, y0 + 1.10, -ud * 0.5 - 0.09)
    g.add(ar)
    hr = M.Group()                            # the heron, in relief
    hr.add(M.lathe([(0.0, 0.0), (0.115, 0.06), (0.10, 0.34), (0.0, 0.44)], 9,
                   "alabaster"))
    nk = M.cylinder(0.022, 0.30, 6, 0.003, "alabaster")
    nk.rotate_z(-0.30)
    nk.translate(0.09, 0.52, 0)
    hr.add(nk)
    bk = M.lathe([(0.030, 0.0), (0.0, 0.19)], 6, "painted_amber")
    bk.rotate_z(-np.pi * 0.42)
    bk.translate(0.20, 0.64, 0)
    hr.add(bk)
    for lx in (-0.045, 0.055):
        lg = M.cylinder(0.014, 0.22, 5, 0.002, "painted_amber")
        lg.translate(lx, -0.11, 0)
        hr.add(lg)
    hr.scale(0.92, 0.92, 0.55)
    hr.translate(-uw * 0.5 + 3.32, y0 + 1.42, -ud * 0.5 - 0.14)
    g.add(hr)
    for i, x in enumerate((-3.2, 0.6, 3.9)):
        w = K.leaded_window(f"{ASSET}.b{i}", width=0.92, height=1.16,
                            mat="glass", shutters=False)
        w.rotate_y(np.pi)
        w.translate(x, y0 + 1.60, ud * 0.5 + 0.07)
        g.add(w)
    for sx in (-1, 1):
        w = K.leaded_window(f"{ASSET}.e{sx}", width=1.06, height=1.32,
                            mat="glass_lit", shutters=False)
        w.rotate_y(sx * np.pi * 0.5)
        w.translate(sx * (uw * 0.5 + 0.07), y0 + 1.72, 0.0)
        g.add(w)

    # The chamber door at the head of the stair, standing open — a moot in
    # session with the door shut would be the wrong story for a market town.
    dx = -uw * 0.5 + 1.45
    g.add(K.door_frame(width=1.10, height=2.16, mat="oak_dark", depth=0.30)
          .translate(dx, y0, -ud * 0.5 - 0.06))
    dr = K.plank_door(f"{ASSET}.chamber", width=1.06, height=2.12,
                      mat="oak_weathered", open_angle=0.85)
    dr.translate(dx, y0, -ud * 0.5 - 0.14)
    g.add(dr)
    SITE.entity(f"{ASSET}.door.01", "door.moot_hall",
                (dx, y0, -ud * 0.5 - 0.16), verbs=["enter"])

    # Interior shell, so the open door and the glass read as a dark room and
    # not as sunlit plaster seen from the far side.
    sh = M.box(uw - 0.6, UPPER - 0.1, ud - 0.6, 0.02, "oak_dark")
    sh.scale(-1.0, 1.0, 1.0)
    sh.translate(0, y0 + UPPER * 0.5, 0)
    SITE.emit(sh, shell=True)

    SITE.collider_walls(uw, ud, UPPER, y=y0, thickness=0.30,
                        doors=[("-z", dx, 1.30)], tag="chamber")
    return uw, ud


def _roof_and_bell(ctx, g, rng):
    """Gable roof on the chamber's plate, and the bell-cote on the east gable.

    The roof takes its height from the plate and nowhere else (`core/roof.py`).
    The bell-cote is then measured off the finished RIDGE — it is the tallest
    thing this building has and the reason it appears in the arrival frame, so
    a hand-authored Y that missed the ridge by 300 mm would be the whole defect.
    """
    uw, ud = W + JETTY * 2, D + JETTY * 2
    poly = SI.rect(0.0, 0.0, uw, ud)
    # Edge 0 runs along +X, so `ridge_axis="u"` lays the ridge along the
    # frontage: gables east and west, eaves to the square. Slot: ridge "along".
    plate = R.wall_plate(poly, EAVES, edges=["eaves", "gable", "eaves", "gable"],
                         thickness=0.30, wall_mat="plaster")
    roof = R.roof_from_plate(plate, "gable", PITCH, 0.52, f"{ASSET}.roof",
                             mat="slate", timber_mat="oak_dark", ridge_axis="u")
    g.add(roof)
    ridge_y = roof.ridge_y

    for i, sx in enumerate((-1, 1)):
        ge = K.gable_end(ud, EAVES, PITCH, mat="plaster", depth=0.26)
        ge.rotate_y(np.pi * 0.5)
        ge.translate(sx * uw * 0.5, 0, 0)
        g.add(ge)
        # Barge boards and a finial, which is what a gable end is FOR at this
        # distance: the profile against the sky.
        for sz in (-1, 1):
            bb = M.box(0.10, 0.26, ud * 0.55, 0.012, "oak_dark")
            bb.rotate_x(sz * math.atan(PITCH))
            bb.translate(sx * (uw * 0.5 + 0.06),
                         (EAVES + ridge_y) * 0.5 + 0.10, sz * ud * 0.25)
            g.add(bb)

    # --- the bell-cote ----------------------------------------------------
    # Four oak posts standing on the east gable's tie beam, a louvred stage,
    # a lead spirelet. Its feet are inside the roof and its apron is lead, so
    # it is carried by the frame rather than balanced on the tiles.
    bx = uw * 0.5 - 1.35
    base = EAVES + 0.60
    stage0, stage1 = BELL_TOP - 4.30, BELL_TOP - 2.05
    half = 0.78
    for sxx in (-1, 1):
        for szz in (-1, 1):
            po = M.box(0.17, stage1 - base, 0.17, 0.012, "oak")
            po.translate(bx + sxx * half, (base + stage1) * 0.5, szz * half)
            g.add(po)
    # Rails and the louvre boards — the sound has to get out, and the louvre is
    # the only place in Hearthmere where a horizontal stripe reads at 60 m.
    for y in (stage0, stage1):
        for (rx, rz, rw, rd) in ((bx, -half, half * 2 + 0.34, 0.14),
                                 (bx, half, half * 2 + 0.34, 0.14),
                                 (bx - half, 0.0, 0.14, half * 2 + 0.34),
                                 (bx + half, 0.0, 0.14, half * 2 + 0.34)):
            rl = M.box(rw, 0.16, rd, 0.012, "oak")
            rl.translate(rx, y, rz)
            g.add(rl)
    nl = 6
    for k in range(nl):
        y = stage0 + 0.22 + k * (stage1 - stage0 - 0.34) / (nl - 1)
        for (lx, lz, lw, ld, ax) in ((bx, -half, half * 2, 0.05, True),
                                     (bx, half, half * 2, 0.05, True),
                                     (bx - half, 0.0, 0.05, half * 2, False),
                                     (bx + half, 0.0, 0.05, half * 2, False)):
            lv = M.box(lw, 0.16, ld, 0.006, "oak_weathered")
            if ax:
                lv.rotate_x(0.52)
            else:
                lv.rotate_z(0.52)
            lv.translate(lx, y, lz)
            g.add(lv)
    # The bell itself, hung on its headstock, visible through the louvre.
    hs = M.box(half * 1.9, 0.20, 0.22, 0.012, "oak_dark")
    hs.translate(bx, stage1 - 0.30, 0)
    g.add(hs)
    bell = M.lathe([(0.0, 0.86), (0.10, 0.84), (0.13, 0.62), (0.20, 0.26),
                    (0.315, 0.06), (0.345, 0.0), (0.30, 0.0)], 14, "bronze")
    bell.rotate_x(np.pi)
    bell.translate(bx, stage1 - 0.36, 0)
    g.add(bell)
    ctx.emit(SITE.place(M.lathe([(0.035, 0), (0.028, 0.55)], 6, "iron")
                        .translate(bx, stage1 - 1.30, 0)))

    # Spirelet: a lead pyramid to the authored 15.80 m, and a vane on it.
    sp = M.lathe([(half + 0.24, 0.0), (half + 0.10, 0.10), (0.0, BELL_TOP - 0.55 - stage1)],
                 4, "lead")
    sp.rotate_y(np.pi * 0.25)
    sp.translate(bx, stage1 + 0.10, 0)
    g.add(sp)
    fin = M.lathe([(0.05, 0), (0.03, 0.42), (0.08, 0.46), (0.0, 0.55)], 8, "iron")
    fin.translate(bx, BELL_TOP - 0.55, 0)
    g.add(fin)
    vane = M.chamfered_prism([(0.0, 0.0), (0.46, 0.10), (0.46, 0.30), (0.0, 0.24)],
                             0.014, "iron", 0.003)
    vane.rotate_y(np.pi * 0.5)
    vane.rotate_y(0.42)
    vane.translate(bx, BELL_TOP - 0.34, 0)
    g.add(vane)

    # Lead apron where the cote breaks the slate.
    ap = M.box(half * 2 + 0.70, 0.08, half * 2 + 0.70, 0.014, "lead")
    ap.translate(bx, base + 0.04, 0)
    g.add(ap)

    SITE.entity(f"{ASSET}.bell.01", "landmark.moot_bell",
                (bx, stage1 - 0.60, 0.0), verbs=["inspect"],
                landmark={"name": "The Moot Bell", "silhouette": True})
    return ridge_y


def _stair(ctx, g, rng):
    """The outside stair, on the front, facing the market place.

    Civic theatre: the council climbs it in public. It runs up the front
    elevation from the square end so that the flight, the landing and the
    chamber door are one gesture seen from the fountain.
    """
    uw = W + JETTY * 2
    zf = -(D + JETTY * 2) * 0.5
    rise = FLOOR - PLAT
    x_head = -uw * 0.5 + 1.45                # under the chamber door
    z_mid = zf - 1.42

    flight, run = K.stair_flight(f"{ASSET}.stair", rise, width=1.30,
                                 riser=0.185, going=0.290, mat="ashlar",
                                 spine=0.0)
    # Authored climbing +Y and receding -Z. `rotate_y(+90)` sends -Z to -X, so
    # the flight climbs WESTWARD to the door, and sends the spine (built on the
    # flight's -X side) to +Z — against the building, where a raking wall
    # belongs. What faces the square is the treads and the parapet, not a
    # blank triangular slab, which is what the first cut of this shipped.
    flight.rotate_y(np.pi * 0.5)
    x_foot = x_head + run
    flight.translate(x_foot, PLAT, z_mid)
    g.add(flight)

    # --- the raking wall the flight is built off, WITH ITS ARCH -----------
    # `stair_flight`'s own `spine` is a solid triangle, and a solid triangle
    # 4.4 m long across a 13 m frontage is 30% of the elevation reading as one
    # blank pale slab — the exact failure Art Bible §7 forbids. A market hall
    # answers this the way every market hall does: the space under the stair
    # is USED. So the wall is two piers and a segmental arch over a recess,
    # and the recess holds the town's fire ladder and its hurdles.
    zw = z_mid + 0.30
    tw = 0.36                                # wall thickness

    def top_at(x):
        return PLAT + 0.20 + rise * (x_foot - x) / run

    xm = x_head + run * 0.54
    xa, xb = xm - 1.00, xm + 1.00
    spring = PLAT + 1.28
    for (p0, p1) in ((x_head - 0.10, xa), (xb, x_foot + 0.16)):
        pier = M.chamfered_prism(
            [(p0, PLAT - 0.10), (p1, PLAT - 0.10), (p1, top_at(p1)),
             (p0, top_at(p0))], tw, "rubble", 0.03)
        pier.translate(0, 0, zw)
        g.add(pier)
    span = M.chamfered_prism(
        [(xa, spring + 0.62), (xb, spring + 0.62), (xb, top_at(xb)),
         (xa, top_at(xa))], tw, "rubble", 0.03)
    span.translate(0, 0, zw)
    g.add(span)
    # Plinth course and a raking string, so the wall has two horizontals in it
    # and does not read as one flat field of stone.
    base = M.chamfered_prism([(x_head - 0.16, PLAT - 0.20),
                              (x_foot + 0.22, PLAT - 0.20),
                              (x_foot + 0.22, PLAT + 0.14),
                              (x_head - 0.16, PLAT + 0.14)],
                             tw + 0.18, "ashlar", 0.025)
    base.translate(0, 0, zw)
    g.add(base)
    strg = M.chamfered_prism([(x_head - 0.12, top_at(x_head - 0.12) - 0.24),
                              (x_foot + 0.18, top_at(x_foot + 0.18) - 0.24),
                              (x_foot + 0.18, top_at(x_foot + 0.18) - 0.06),
                              (x_head - 0.12, top_at(x_head - 0.12) - 0.06)],
                             tw + 0.14, "stone", 0.02)
    strg.translate(0, 0, zw)
    g.add(strg)
    arch = K.arch_ring(f"{ASSET}.understair", span=2.00, rise=0.56, ring=0.26,
                       depth=tw + 0.04, mat="ashlar")
    arch.translate(xm, spring, zw)
    g.add(arch)
    # Something dark behind the arch, or the recess reads as a painted panel.
    void = M.box(1.96, spring - PLAT + 0.54, 0.44, 0.01, "oak_dark")
    void.translate(xm, PLAT + (spring - PLAT + 0.54) * 0.5, zw + 0.34)
    g.add(void)
    # Under-stair store: the town's fire ladder, hurdles and a spare hurdle
    # frame. This is town property and it lives where the town can reach it.
    lad = M.Group()
    for s in (-1, 1):
        lad.add(M.cylinder(0.032, 3.10, 6, 0.004, "oak_weathered")
                .translate(s * 0.20, 1.55, 0))
    for k in range(9):
        rg = M.cylinder(0.020, 0.42, 5, 0.003, "oak_weathered")
        rg.rotate_z(np.pi * 0.5)
        rg.translate(0, 0.28 + k * 0.34, 0)
        lad.add(rg)
    P.lean(lad, 3.10, 0.55, wall_z=zw + 0.10, x=xm - 0.42,
           roll=rng.uniform(-0.05, 0.05))
    lad.translate(0, PLAT, 0)
    g.add(lad)
    for i in range(3):
        hu = M.Group()
        for k in range(6):
            hu.add(M.cylinder(0.022, 0.95, 5, 0.003, "timber_grey")
                   .translate(-0.42 + k * 0.17, 0.475, 0))
        for k in range(2):
            r2 = M.cylinder(0.024, 0.98, 5, 0.003, "timber_grey")
            r2.rotate_z(np.pi * 0.5)
            r2.translate(0, 0.18 + k * 0.60, 0)
            hu.add(r2)
        P.lean(hu, 0.98, 0.16 + i * 0.05, wall_z=zw + 0.06, x=xm + 0.52 + i * 0.06,
               roll=rng.uniform(-0.06, 0.06))
        hu.translate(0, PLAT, 0)
        g.add(hu)
    ctx.collider("box", center=SITE.p(x_head + run * 0.5, PLAT + rise * 0.35, zw),
                 half=(run * 0.5 + 0.2, rise * 0.35, tw * 0.5),
                 rot_y=SITE.yaw(), tag="stair_wall")

    # Raking parapet on the OPEN side, with a coping — this is the piece that
    # makes an external civic stair read as architecture rather than as steps
    # leaning on a wall. It stops 0.95 m above the nosing line, so the flight
    # is still visible over it from across the market place.
    # An OPEN oak balustrade, not a solid raking parapet. A stone parapet is
    # the other period-correct answer and it was tried first: it is a 4.2 m
    # blank triangle that hides the treads and blanks a third of the frontage,
    # which is the exact defect Art Bible §7 forbids on a facade. An open
    # balustrade shows the flight, the soffit and the daylight behind it, and
    # it is what a timber-framed civic building would have anyway.
    zp = z_mid - 0.70
    rake = math.atan2(rise, run)
    string = M.box(math.hypot(run, rise) + 0.30, 0.20, 0.09, 0.012,
                   "oak_weathered")
    string.rotate_z(-rake)                   # falls eastward, toward the foot
    string.translate(x_foot - run * 0.5, PLAT + rise * 0.5 + 0.10, zp)
    g.add(string)
    nb = 8
    for k in range(nb):
        f = (k + 0.5) / nb
        bx = x_foot - run * f
        by = PLAT + rise * f + 0.20
        bal = M.lathe([(0.038, 0.0), (0.044, 0.07), (0.026, 0.24),
                       (0.042, 0.40), (0.030, 0.62), (0.036, 0.74)], 8, "oak")
        bal.rotate_y(rng.uniform(-0.2, 0.2))
        bal.translate(bx, by, zp)
        g.add(bal)
    rail = M.lathe([(0.0, -0.10), (0.048, -0.06), (0.052, math.hypot(run, rise) + 0.20),
                    (0.0, math.hypot(run, rise) + 0.26)], 8, "oak_weathered")
    rail.rotate_z(np.pi * 0.5)
    rail.rotate_z(rake)
    rail.translate(x_foot + 0.10, PLAT + 0.94, zp)
    g.add(rail)
    # Newel at the foot, capped — the one place a hand actually goes.
    nw = M.box(0.17, 1.16, 0.17, 0.014, "oak")
    nw.translate(x_foot + 0.16, PLAT + 0.58, zp)
    g.add(nw)
    nc = M.lathe([(0.13, 0.0), (0.15, 0.05), (0.0, 0.22)], 8, "oak")
    nc.translate(x_foot + 0.16, PLAT + 1.16, zp)
    g.add(nc)

    # Landing at the head, on a corbelled bracket so it is carried, not stuck.
    land = M.box(1.80, 0.26, 1.62, 0.02, "ashlar")
    land.translate(x_head, FLOOR - 0.13, zf - 0.86)
    g.add(land)
    for sx in (-1, 1):
        co = K.corbel(f"{ASSET}.lc{sx}", project=0.52, width=0.28, height=0.34,
                      mat="stone")
        co.translate(x_head + sx * 0.66, FLOOR - 0.58, zf - 0.10)
        g.add(co)
    rl2 = S.handrail(f"{ASSET}.rail2", length=1.66, height=0.98,
                     mat="oak_weathered", posts=3)
    rl2.rotate_y(np.pi * 0.5)
    rl2.translate(x_head - 0.86, FLOOR, zf - 0.86)
    g.add(rl2)

    # `collision.steps` descends along local -Z from the threshold, so the
    # flight is turned to descend along +X — east, back down to the market.
    SITE.collider_steps((x_head, FLOOR, z_mid), rise, tread=0.30,
                        width=1.30, rot_y=-np.pi * 0.5)
    ctx.collider("box", center=SITE.p(x_head, FLOOR - 0.13, zf - 0.86),
                 half=(0.90, 0.13, 0.81), rot_y=SITE.yaw(), kind="surface",
                 tag="landing")
    # The balustrade is what stops a councillor stepping off the flight, so it
    # collides as one barrier along the open edge rather than per baluster.
    ctx.collider("box",
                 center=SITE.p(x_head + run * 0.5, PLAT + rise * 0.5 + 0.50, zp),
                 half=(run * 0.5 + 0.20, rise * 0.5 + 0.50, 0.12),
                 rot_y=SITE.yaw(), tag="stair_balustrade")

    # RESIDUE: somebody's cloak left over the coping halfway up, and pattens
    # kicked off at the foot because the market is mud and the chamber has a
    # boarded floor.
    f = 0.46
    cl = M.sheet(0.74, 1.05, lambda u, v: -0.08 * math.sin(u * 3.4) - 0.05 * v,
                 nx=7, nz=6, mat="wool_crimson", plane="xz")
    cl.rotate_x(np.pi * 0.46)
    cl.rotate_y(0.08)
    cl.translate(x_foot - run * f, PLAT + rise * f + 0.92, zp - 0.09)
    g.add(cl)
    for i, (px, pz) in enumerate(((-0.16, -0.05), (0.14, 0.08))):
        pt = M.box(0.11, 0.075, 0.27, 0.008, "oak_weathered")
        pt.rotate_y(rng.uniform(-0.6, 0.6))
        pt.translate(x_foot + 0.55 + px, PLAT + 0.04, z_mid - 0.55 + pz)
        g.add(pt)
    # Boots have polished the bottom three treads and nothing above them.
    g.add(P.worn_patch(f"{ASSET}.tread", shape="path", size=1.3, mat="stone")
          .translate(x_foot - 0.4, PLAT + 0.02, z_mid))
    return run


def _market_under(ctx, g, rng):
    """The butter market: what the arcade is FOR, arranged as a morning uses it.

    Standings first (the cold stone the butter sits on), then the beam scale
    over them, then the goods, then what got dropped. Everything is pushed to
    the flanks — the middle of an arcade is the route through it, and a market
    that blocks its own thoroughfare is a market nobody walks into.
    """
    y = PLAT
    # Stone standings along the west and front-centre bays.
    stand = []
    for i, (sx, sz, sw) in enumerate(((-4.55, -1.9, 3.10), (-4.55, 1.9, 3.10),
                                      (-0.55, 2.05, 3.20))):
        sl = SI.slab(SI.rect(sx, sz, sw, 1.05), y, y + 0.62, "stone", 0.025)
        g.add(sl)
        ctx.collider("box", center=SITE.p(sx, y + 0.31, sz),
                     half=(sw * 0.5, 0.31, 0.53), rot_y=SITE.yaw(),
                     tag="standing")
        stand.append((sx, sz, sw))

    # Butter and cheese on the standings — the goods that name the market.
    for i in range(7):
        sx, sz, sw = stand[i % 3]
        r = rng.uniform(0.13, 0.20)
        ch = M.lathe([(0.0, 0.0), (r, 0.015), (r * 0.97, r * 1.10),
                      (r * 0.80, r * 1.22), (0.0, r * 1.24)], 14, "wax")
        ch.rotate_y(rng.uniform(0, 3.1))
        ch.translate(sx + rng.uniform(-sw * 0.34, sw * 0.34), y + 0.63,
                     sz + rng.uniform(-0.28, 0.28))
        g.add(M.retex(ch, 2.2, 2.2, rng.uniform(0, 0.7)))
    for i in range(4):
        sx, sz, sw = stand[(i + 1) % 3]
        bk = P.basket(f"{ASSET}.bk{i}", radius=0.20, height=0.17, weave="coil",
                      fill="wool")
        bk.rotate_y(rng.uniform(-3, 3))
        bk.translate(sx + rng.uniform(-sw * 0.36, sw * 0.36), y + 0.63,
                     sz + rng.uniform(-0.26, 0.26))
        g.add(bk)
    # Damp linen over one lot, because butter melts and everybody knows it.
    lin = M.sheet(1.15, 0.85, lambda u, v: -0.055 * math.sin(u * 4.2) - 0.03 * v,
                  nx=7, nz=5, mat="linen", plane="xz")
    lin.translate(-4.55, y + 0.66, -1.9)
    g.add(lin)

    # The beam scale, hung from the bressumer over the standings. Goods sold by
    # weight are weighed in front of the buyer, which is why this is public and
    # why the sealed measures are ten paces away on the gaol wall.
    sc = P.hanging_scales(f"{ASSET}.scales", span=0.86, drop=0.62, tilt=0.09,
                          reach=0.0)
    sc.translate(-4.55, PLAT + POST_H - 0.34, 0.0)
    g.add(sc)
    g.add(P.weight_set(f"{ASSET}.weights", count=5)
          .translate(-3.35, y + 0.63, 0.35))
    g.add(P.counting_board(f"{ASSET}.tally")
          .translate(-5.85, y + 0.63, 2.05))
    SITE.entity(f"{ASSET}.scales.01", "prop.town_scales",
                (-4.55, y + 1.55, 0.0), verbs=["inspect"])

    # Overflow pushed against the west post line, out of the walking route.
    g.add(P.stack_against_wall(
        f"{ASSET}.over",
        [P.crate_stack(f"{ASSET}.cs", count=3),
         P.sack_stack(f"{ASSET}.ss", count=3),
         K.barrel(f"{ASSET}.bar", height=0.78)],
        wall_z=D * 0.5 - 0.95, x0=-W * 0.5 + 1.1, x1=-W * 0.5 + 4.4)
        .translate(0, y, 0))

    # What got dropped crossing it. Straw first — the standings are strawed
    # every market morning and it ends up everywhere.
    g.add(P.spill(f"{ASSET}.straw", kind="grain", radius=1.55, density=0.85,
                  centre=(-2.4, 0.4), vessel=False).translate(0, y, 0))
    tip = P.basket(f"{ASSET}.tipped", radius=0.21, height=0.25, weave="stake")
    tip.rotate_z(1.44)
    tip.rotate_y(rng.uniform(-3, 3))
    tip.translate(1.35, y + 0.22, -1.15)
    g.add(tip)
    g.add(P.stool(f"{ASSET}.stool2").translate(-6.05, y, -1.35))
    g.add(P.mug(f"{ASSET}.mug", full=False).translate(-4.05, y + 0.63, -2.15))
    g.add(P.worn_patch(f"{ASSET}.dog", shape="cat", size=0.62, mat="stone")
          .translate(3.15, y + 0.012, -2.35))


def _whipping_post(ctx, g, rng):
    """Nobody has used it in fifty years, and the building has to say so.

    The shackles are seized, the paving round the foot has gone to moss because
    no crowd stands there any more, and somebody has left a basket leaning
    against it. Art Bible §7: residue is the story, and obsolescence is a story.
    """
    x, z = -W * 0.5 - 0.05, -D * 0.5 - 2.35
    yg = PLAT
    base = SI.slab(SI.rect(x, z, 1.05, 1.05), yg - 0.02, yg + 0.16, "ashlar",
                   0.02)
    g.add(base)
    po = M.box(0.24, 2.10, 0.24, 0.018, "timber_grey")
    po.rotate_z(0.022)                       # fifty years of leaning
    po.translate(x, yg + 0.16 + 1.05, z)
    g.add(po)
    cap = M.lathe([(0.20, 0.0), (0.19, 0.07), (0.0, 0.20)], 4, "iron_pitted")
    cap.rotate_y(np.pi * 0.25)
    cap.translate(x, yg + 2.20, z)
    g.add(cap)
    for sx in (-1, 1):
        # Wrist irons at 1.42 m, hanging shut. A shackle standing open would
        # read as in use; seized shut is the point.
        pl = M.box(0.055, 0.16, 0.055, 0.004, "iron_pitted")
        pl.translate(x + sx * 0.16, yg + 1.58, z)
        g.add(pl)
        rg = M.ring(0.085, 0.016, "iron_pitted", 10, tilt=0.35)
        rg.rotate_x(np.pi * 0.5)
        rg.translate(x + sx * 0.30, yg + 1.50, z)
        g.add(rg)
        g.add(K.forged_chain(f"{ASSET}.ch{sx}", (x + sx * 0.20, yg + 1.55, z),
                             (x + sx * 0.34, yg + 1.18, z - 0.04),
                             sag=0.12, link=0.055, mat="iron_pitted"))
    # The moss and the weed nobody treads out. This is the whole finding.
    g.add(P.worn_patch(f"{ASSET}.moss", shape="cat", size=1.45, mat="moss")
          .translate(x, yg + 0.008, z))
    for i in range(5):
        from core import vegetation as V
        wd = V.joint_weeds(f"{ASSET}.wd{i}", count=4)
        wd.translate(x + rng.uniform(-0.62, 0.62), yg + 0.01,
                     z + rng.uniform(-0.62, 0.62))
        g.add(wd)
    bk = P.basket(f"{ASSET}.leaning", radius=0.23, height=0.34, weave="stake")
    P.lean(bk, 0.34, 0.14, wall_z=z - 0.14, x=x + 0.42)
    g.add(bk)

    ctx.collider("cylinder", center=SITE.p(x, yg + 1.15, z), radius=0.22,
                 height=2.30, tag="whipping_post")
    SITE.entity(f"{ASSET}.post.01", "prop.whipping_post",
                (x, yg + 1.20, z), verbs=["inspect"])


def build(ctx: VenueContext, asset_id=ASSET):
    SITE.bind(ctx)
    rng = rng_for(asset_id, "moot")
    g = M.Group()

    ctx.emit(SITE.place(_platform(ctx, rng)))

    _lock_up(ctx, g, rng)
    head = _arcade(ctx, g, rng)
    _market_under(ctx, g, rng)
    _chamber(ctx, g, rng)
    ridge = _roof_and_bell(ctx, g, rng)
    _stair(ctx, g, rng)
    _whipping_post(ctx, g, rng)

    # Fire hooks and leather buckets on the front bressumer — town property,
    # kept where the whole town knows to find them.
    # On the LOCK-UP wall, where there is real masonry to fix an iron hook to.
    # Hung off the open bressumer they read as four buckets floating under the
    # jetty, which is Directive §6.1's "fixed to a wall by shown hardware"
    # failing on exactly the object the rule was written for.
    hz = CELL_Z0 - 0.14
    for i in range(4):
        hx = CELL_X0 + 0.75 + i * 0.46
        pl = M.box(0.10, 0.14, 0.06, 0.004, "iron")
        pl.translate(hx, PLAT + 1.98, hz)
        g.add(pl)
        hk = M.tube((hx, PLAT + 1.96, hz), (hx, PLAT + 1.86, hz - 0.13),
                    0.013, "iron", 5)
        g.add(hk)
        bu = P.bucket(f"{ASSET}.fire{i}", height=0.32, top=0.16, mat="leather")
        bu.rotate_z(rng.uniform(-0.05, 0.05))
        bu.translate(hx, PLAT + 1.52, hz - 0.15)
        g.add(bu)
    hook = M.Group()
    hook.add(M.cylinder(0.028, 4.20, 6, 0.004, "oak_weathered"))
    hd = M.chamfered_prism([(0.0, 0.0), (0.30, 0.14), (0.24, 0.30), (0.0, 0.16)],
                           0.026, "iron", 0.003)
    hd.translate(0, 2.10, 0)
    hook.add(hd)
    hook.rotate_z(np.pi * 0.5)
    hook.rotate_y(0.03)
    # Stored flat on brackets under the BACK bressumer, out of the frontage and
    # out of anybody's way — 4.2 m of fire hook slung across the market side
    # would cut every composition the building has.
    hook.translate(-1.4, PLAT + POST_H - 0.34, D * 0.5 - 0.42)
    g.add(hook)
    for hx in (-3.2, 0.4):
        br = M.box(0.09, 0.16, 0.34, 0.008, "iron")
        br.translate(hx, PLAT + POST_H - 0.34, D * 0.5 - 0.42)
        g.add(br)

    SITE.emit(g, container="moot hall")

    print(SITE.report())
    print(f"      arcade head {head:.2f}  floor {FLOOR:.2f}  eaves {EAVES:.2f}  "
          f"ridge {ridge:.2f}  bell {BELL_TOP:.2f}")
