"""Well-house — slot 90. The public well, and the town's best gossip.

The smallest venue in this brief and, per square metre, the one that does most
for how inhabited Hearthmere feels. A well is the only place in a
pre-industrial town that every single household visits every single day, and
the objects prove it without a person in frame:

  - the **stone lip is worn into a dish** where two hundred years of rope has
    sawed across it, and it is worn on ONE side, because everybody stands where
    the sun is
  - the **puddle** never dries, so there is moss on the north face of the
    coping and green in the joints of the paving for a metre and a half
  - there is a **bench**, because there is always a bench, because drawing
    water is the only errand a town gives you an excuse to stand around on
  - the **cup is chained**, because it is public and because somebody would
    otherwise take it

Slot 90: open on all four sides, tiled pyramid roof, a windlass, a chained cup,
and a stone trough the whole west quarter draws from. It is also the conduit
head that feeds the market fountain, so a lead pipe leaves it eastward under
the lane — the one visible piece of the town's water engineering.
"""

from __future__ import annotations

import math

import numpy as np

from core import mesh as M
from core import kit as K
from core import props as P
from core import roof as R
from core import streetscape as S
from core import vegetation as V
from core import siting as SI
from core.mathx import rng_for
from core.venue import VenueContext
from core import materials as MATS

NAME = "wellhouse"
ASSET = "hm.slot.90.wellhouse"

SITE = SI.Site(NAME)
CELLS = SITE.cells

W, D = SITE.w, SITE.d              # 5.6 x 5.6
EAVES = SITE.eaves                 # 3.20
PLINTH = 0.30
PITCH = 0.86
WELL_R = 0.72                      # inside face of the coping
LIP = 0.84                         # Art Bible §3: a well lip is hip height


def _platform(ctx, g, rng):
    """A raised, gently domed apron that sheds spilt water back to the gutter.

    The single most useful thing a well-house does structurally is get the
    water AWAY, and a flat pad round a well is the one detail that says nobody
    thought about it. This one falls 60 mm from the coping to its edge.
    """
    poly = SI.rect(0.0, 0.0, W + 0.9, D + 0.9)
    slab, y0 = SI.plinth_under(SITE, poly, PLINTH, mat="stone", chamfer=0.03)
    g.add(slab)
    ctx.collider("box", center=SITE.p(0, (y0 + PLINTH) * 0.5, 0),
                 half=((W + 0.9) * 0.5, max((PLINTH - y0) * 0.5, 0.05),
                       (D + 0.9) * 0.5),
                 rot_y=SITE.yaw(), kind="surface", tag="apron")
    # The fall, as a shallow dished slab over the top: 60 mm from centre to rim.
    dish = M.lathe([(0.0, PLINTH + 0.06), (W * 0.30, PLINTH + 0.045),
                    (W * 0.50, PLINTH + 0.005)], 16, "stone",
                   close_bottom=False, close_top=False)
    g.add(M.retex(dish, 0.85))
    # The gutter it falls into, and the gully stone that takes it away.
    for a in (0.35, 2.05, 3.75, 5.10):
        gz = M.box(0.34, 0.09, 0.34, 0.012, "sett", uv_scale=MATS.uv_detail("sett", 0.714, why="0.34 m member; the library's 2 m tile shows 17% of one tile here and reads as flat colour"))
        gz.translate(math.cos(a) * (W * 0.5 + 0.30), PLINTH - 0.045,
                     math.sin(a) * (D * 0.5 + 0.30))
        g.add(gz)
    gy = S.gully_stone(f"{ASSET}.gully")
    gy.translate(W * 0.5 + 0.25, PLINTH - 0.06, D * 0.5 - 0.35)
    g.add(gy)
    return y0


def _well(ctx, g, rng):
    """The shaft, the coping worn on one side, the windlass and the cup."""
    # Coping: a drum of dressed stone, with the top course a separate ring so
    # the wear can be cut into it without disturbing the courses below.
    for k, (y0, y1, r) in enumerate(((PLINTH, PLINTH + 0.32, WELL_R + 0.30),
                                     (PLINTH + 0.32, LIP - 0.13, WELL_R + 0.27))):
        drum = M.lathe([(r, y0), (r, y1), (WELL_R, y1), (WELL_R, y0)], 20,
                       "ashlar", close_bottom=False, close_top=False)
        g.add(M.retex(drum, 0.8))
    lip = M.lathe([(WELL_R, LIP - 0.13), (WELL_R + 0.34, LIP - 0.13),
                   (WELL_R + 0.36, LIP - 0.05), (WELL_R + 0.30, LIP),
                   (WELL_R - 0.02, LIP)], 24, "stone")
    # THE WEAR. The rope has sawed the lip down on the drawing side only —
    # the side the sun is on, which is the side everybody stands. Cut it into
    # the vertices by angle, so it is geometry the light finds, not a texture.
    v = lip.v
    ang = np.arctan2(v[:, 2], v[:, 0])
    hit = np.clip(np.cos(ang - 0.9), 0.0, 1.0) ** 2.5
    lip.v[:, 1] -= (hit * 0.055 * (v[:, 1] > LIP - 0.10)).astype(np.float32)
    g.add(M.retex(lip, 0.9))
    # Two rope grooves cut across the lip on that side, 90 mm apart.
    for s in (-1, 1):
        gr = M.box(0.055, 0.05, 0.42, 0.006, "stone", uv_scale=MATS.uv_detail("stone", 0.5, why="0.42 m member; the library's 2 m tile shows 21% of one tile here and reads as flat colour"))
        gr.rotate_y(0.9)
        gr.translate(math.cos(0.9) * (WELL_R + 0.16) + s * 0.045 * math.sin(0.9),
                     LIP - 0.03,
                     math.sin(0.9) * (WELL_R + 0.16) - s * 0.045 * math.cos(0.9))
        g.add(gr)

    # The shaft: dark, wet, and with a disc of water a long way down. A well
    # with a black hole in it reads as a prop; a well with WATER in it reads as
    # a well, and the reflection is the whole trick.
    shaft = M.lathe([(WELL_R, PLINTH - 3.10), (WELL_R, LIP - 0.10)], 18,
                    "cobble_wall", close_bottom=False, close_top=False)
    shaft.scale(-1.0, 1.0, 1.0)
    g.add(M.retex(shaft, 0.6))
    wt = M.lathe([(0.0, 0.0), (WELL_R - 0.02, 0.0)], 18, "water")
    wt.translate(0, PLINTH - 2.85, 0)
    g.add(wt)
    ctx.collider("cylinder", center=SITE.p(0, PLINTH + (LIP - PLINTH) * 0.5, 0),
                 radius=WELL_R + 0.36, height=LIP - PLINTH, tag="wellhead")

    # --- the windlass ----------------------------------------------------
    for sx in (-1, 1):
        po = M.box(0.16, 1.42, 0.16, 0.012, "oak")
        po.rotate_z(rng.uniform(-0.012, 0.012))
        po.translate(sx * (WELL_R + 0.22), LIP + 0.71, 0)
        g.add(po)
        cp = M.lathe([(0.13, 0.0), (0.15, 0.045), (0.0, 0.20)], 6, "oak")
        cp.translate(sx * (WELL_R + 0.22), LIP + 1.42, 0)
        g.add(cp)
    barrel = M.lathe([(0.115, -(WELL_R + 0.02)), (0.135, -(WELL_R - 0.06)),
                      (0.135, WELL_R - 0.06), (0.115, WELL_R + 0.02)], 10, "oak")
    barrel.rotate_z(np.pi * 0.5)
    barrel.translate(0, LIP + 1.16, 0)
    g.add(M.retex(barrel, 1.4))
    # The axle runs on through both bearings and out to the crank, so the crank
    # is carried by something instead of hanging in the air beside the frame.
    axle = M.cylinder(0.038, (WELL_R + 0.44) * 2, 8, 0.003, "iron")
    axle.rotate_z(np.pi * 0.5)
    axle.translate(0, LIP + 1.16, 0)
    g.add(axle)
    # Crank: an iron elbow on the drawing side, worn bright.
    cr = M.Group()
    cr.add(M.cylinder(0.024, 0.30, 6, 0.003, "iron").rotate_z(np.pi * 0.5))
    cr.add(M.cylinder(0.022, 0.26, 6, 0.003, "iron").translate(0.15, -0.13, 0))
    cr.add(M.cylinder(0.026, 0.13, 6, 0.003, "oak_weathered")
           .rotate_z(np.pi * 0.5).translate(0.28, -0.26, 0))
    cr.rotate_x(rng.uniform(0.4, 2.6))
    cr.translate(WELL_R + 0.36, LIP + 1.16, 0)
    g.add(cr)
    # Rope, wound on the barrel, with the bucket hanging just below the lip.
    for k in range(9):
        rp = M.ring(0.145, 0.012, "canvas", 12)
        rp.rotate_z(np.pi * 0.5)
        rp.translate(-0.36 + k * 0.09, LIP + 1.16, 0)
        g.add(rp)
    g.add(M.catenary((0.0, LIP + 1.03, 0.0), (0.10, LIP + 0.16, 0.12), 0.02,
                     "canvas", 0.012, 6, 4))
    bkt = P.bucket(f"{ASSET}.bucket", height=0.34, top=0.20, full=True)
    bkt.rotate_y(rng.uniform(0, 6.0))
    bkt.translate(0.10, LIP - 0.18, 0.12)
    g.add(bkt)
    SITE.entity(f"{ASSET}.well.01", "prop.well", (0.0, LIP, 0.0),
                verbs=["draw"], landmark={"name": "The Town Well"})

    # --- the chained cup -------------------------------------------------
    # Public property, and it says so by being chained. A horn cup, because a
    # metal one would have gone in a week.
    cup = M.lathe([(0.045, 0.0), (0.055, 0.02), (0.050, 0.11), (0.058, 0.125)],
                  10, "alabaster", close_top=False)
    cup.rotate_z(rng.uniform(-0.25, 0.25))
    cup.translate(math.cos(2.4) * (WELL_R + 0.16), LIP + 0.02,
                  math.sin(2.4) * (WELL_R + 0.16))
    g.add(cup)
    g.add(K.forged_chain(
        f"{ASSET}.cupchain",
        (math.cos(2.4) * (WELL_R + 0.16), LIP + 0.10, math.sin(2.4) * (WELL_R + 0.16)),
        (-(WELL_R + 0.22), LIP + 0.42, 0.0), sag=0.24, link=0.05, mat="iron"))
    st = M.box(0.055, 0.09, 0.055, 0.004, "iron")
    st.translate(-(WELL_R + 0.22), LIP + 0.42, 0.0)
    g.add(st)


def _roof(ctx, g, rng):
    """Four posts and a tiled pyramid. Open on all four sides, per slot 90."""
    hw = W * 0.5 - 0.30
    for sx in (-1, 1):
        for sz in (-1, 1):
            pad = M.box(0.42, 0.14, 0.42, 0.02, "ashlar", uv_scale=MATS.uv_detail("ashlar", 1.11, why="0.42 m member; the library's 2 m tile shows 21% of one tile here and reads as flat colour"))
            pad.translate(sx * hw, PLINTH + 0.07, sz * hw)
            g.add(pad)
            po = M.box(0.22, EAVES - PLINTH - 0.14, 0.20, 0.018, "oak")
            po.rotate_y(rng.uniform(-0.03, 0.03))
            po.translate(sx * hw, PLINTH + 0.14 + (EAVES - PLINTH - 0.14) * 0.5,
                         sz * hw)
            g.add(po)
            ctx.collider("cylinder", center=SITE.p(sx * hw, PLINTH + 1.4, sz * hw),
                         radius=0.17, height=2.6, tag="post")
            # Straight knee braces, post head to plate, both ways. They are
            # the only thing holding a four-post open frame square, and both
            # ends are SOLVED — foot on the post at EAVES-0.90, head on the
            # plate 0.62 m in. Two earlier cuts used a mirrored prism and a
            # rotated profile, and both left the braces in mid-air under the
            # roof with nothing touching either end.
            L = 0.877                                    # hypot(0.62, 0.62)
            bx = M.box(L, 0.13, 0.115, 0.010, "oak")
            bx.rotate_z(-sx * np.pi * 0.25)
            bx.translate(sx * (hw - 0.31), EAVES - 0.59, sz * hw)
            g.add(bx)
            bz = M.box(0.115, 0.13, L, 0.010, "oak")
            bz.rotate_x(sz * np.pi * 0.25)
            bz.translate(sx * hw, EAVES - 0.59, sz * (hw - 0.31))
            g.add(bz)
    for sz in (-1, 1):
        pl = M.box(hw * 2 + 0.44, 0.20, 0.18, 0.014, "oak_dark")
        pl.translate(0, EAVES - 0.10, sz * hw)
        g.add(pl)
    for sx in (-1, 1):
        pl = M.box(0.18, 0.20, hw * 2 + 0.08, 0.014, "oak_dark")
        pl.translate(sx * hw, EAVES - 0.10, 0)
        g.add(pl)

    poly = SI.rect(0.0, 0.0, hw * 2 + 0.44, hw * 2 + 0.44)
    plate = R.wall_plate(poly, EAVES, edges=["eaves"] * 4, thickness=0.20,
                         wall_mat="oak")
    roof = R.roof_from_plate(plate, "pyramid", PITCH, 0.62, f"{ASSET}.roof",
                             mat="terracotta", timber_mat="oak_dark")
    g.add(roof)
    fin = M.lathe([(0.07, 0.0), (0.05, 0.34), (0.10, 0.40), (0.0, 0.62)], 8,
                  "iron")
    fin.translate(0, roof.ridge_y - 0.06, 0)
    g.add(fin)
    return roof.ridge_y


def _trough_and_bench(ctx, g, rng):
    """The trough the west quarter draws from, the conduit, and the bench.

    Arranged by workflow: the windlass is over the shaft, the trough stands
    where a filled bucket can be tipped into it without carrying it anywhere,
    and the bench faces BOTH — because whoever is waiting wants to see who is
    drawing.
    """
    tx, tz = -W * 0.5 - 0.55, 0.55
    tr = S.horse_trough(f"{ASSET}.trough", length=2.30, width=0.72, height=0.62)
    tr.rotate_y(np.pi * 0.5)
    tr.translate(tx, PLINTH - 0.02, tz)
    g.add(tr)
    ctx.collider("box", center=SITE.p(tx, PLINTH + 0.31, tz),
                 half=(0.40, 0.31, 1.18), rot_y=SITE.yaw(), tag="trough")
    # The trough is FULL — a dry trough at a working well is the one thing
    # that would say nobody uses this. A lathe scaled 3.3x in Z came out a
    # black lozenge; a plain slab of water sits flat and catches the sky.
    wat = M.box(0.50, 0.02, 2.05, 0.004, "water")
    wat.translate(tx, PLINTH + 0.44, tz)
    g.add(wat)
    # A lead spout over it, fed from the coping — this well IS the conduit head
    # and the fountain in the market place is downstream of it.
    sp = M.tube((tx + 0.62, PLINTH + 1.05, tz), (tx + 0.10, PLINTH + 0.80, tz),
                0.038, "lead", 6)
    g.add(sp)
    br = M.box(0.10, 0.34, 0.10, 0.006, "iron")
    br.translate(tx + 0.66, PLINTH + 0.92, tz)
    g.add(br)
    # The conduit run east, its cover stones lifted at one joint and never
    # relaid — the only visible piece of the town's water engineering.
    for k in range(5):
        cs = M.box(0.52, 0.12, 0.62, 0.015, "stone")
        cs.rotate_y(rng.uniform(-0.05, 0.05))
        cs.translate(W * 0.5 + 0.75 + k * 0.58, PLINTH - 0.10,
                     -0.85 + rng.uniform(-0.04, 0.04))
        g.add(cs)
    lift = M.box(0.52, 0.12, 0.62, 0.015, "stone")
    lift.rotate_z(0.42)
    lift.rotate_y(0.3)
    lift.translate(W * 0.5 + 1.05, PLINTH + 0.10, -1.62)
    g.add(lift)
    pipe = M.tube((W * 0.5 + 1.35, PLINTH - 0.12, -0.85),
                  (W * 0.5 + 1.95, PLINTH - 0.12, -0.85), 0.055, "lead", 6)
    g.add(pipe)

    # --- THE GOSSIP BENCH ------------------------------------------------
    # Every real well has one and it is the single cheapest way to say that
    # people stand here. It is worn pale in two places and nowhere else.
    # Art Bible §3: a bench seat is 0.45 m. The first cut sat at 0.77 m on
    # 0.42 m stone feet and read as a counter, and its two "wear" boards were
    # authored flat but built on edge, so they stood up like hoardings.
    bx, bz = 0.35, -W * 0.5 - 1.05
    seat_y = PLINTH + 0.45
    for sx in (-1, 1):
        ft = M.box(0.32, 0.45, 0.30, 0.02, "stone", uv_scale=MATS.uv_detail("stone", 1.11, why="0.45 m member; the library's 2 m tile shows 22% of one tile here and reads as flat colour"))
        ft.translate(bx + sx * 0.92, PLINTH + 0.225, bz)
        g.add(ft)
    seat = M.plank(2.35, 0.44, 0.085, 0.012, "oak_weathered")
    seat.rotate_y(rng.uniform(-0.03, 0.03))
    seat.translate(bx, seat_y, bz)
    g.add(seat)
    # Worn pale where two people have always sat, and nowhere else.
    for sx in (-1, 1):
        wn = M.box(0.62, 0.010, 0.34, 0.003, "oak")
        wn.translate(bx + sx * 0.58, seat_y + 0.048, bz + 0.02)
        g.add(wn)
    ctx.collider("box", center=SITE.p(bx, PLINTH + 0.24, bz),
                 half=(1.20, 0.24, 0.24), rot_y=SITE.yaw(), tag="bench")
    SITE.entity(f"{ASSET}.bench.01", "prop.bench",
                (bx, seat_y, bz), verbs=["sit"])

    # Buckets and a yoke left by the bench by whoever is talking instead of
    # carrying, plus a pot standing in the queue holding a place.
    g.add(P.yoke_and_buckets(f"{ASSET}.yoke", mode="down")
          .rotate_y(0.7).translate(bx + 1.45, PLINTH, bz + 0.42))
    for i, (px, pz) in enumerate(((-1.55, -1.85), (-1.20, -2.25))):
        bu = P.bucket(f"{ASSET}.b{i}", height=0.32, top=0.19,
                      full=i == 0)
        bu.rotate_y(rng.uniform(0, 6.0))
        bu.translate(px, PLINTH, pz)
        g.add(bu)
    g.add(P.amphora(f"{ASSET}.pot", height=0.62, standing=True)
          .translate(1.85, PLINTH, -1.95))


def _wet(ctx, g, rng, y0):
    """The puddle, the moss, and the green in the joints. This never dries.

    A well that is dry round its foot is a well nobody uses. The water is on
    the drawing side and in the run to the gully; the moss is on the north
    face of the coping and in the paving joints where the boots do not go.
    """
    g.add(P.dust_film(f"{ASSET}.puddle", radius=1.05, mat="mud_wet",
                      centre=(math.cos(0.9) * 1.55, math.sin(0.9) * 1.55),
                      y=PLINTH + 0.02, density=1.0))
    g.add(P.dust_film(f"{ASSET}.run", radius=0.70, mat="mud_wet",
                      centre=(W * 0.5 + 0.05, D * 0.5 - 0.45),
                      y=PLINTH - 0.03, density=0.7))
    g.add(P.dust_film(f"{ASSET}.algae", radius=0.85, mat="algae",
                      centre=(-1.35, -1.15), y=PLINTH + 0.015, density=0.6))
    # Moss up the north face of the coping, where the sun never reaches it.
    for i in range(6):
        a = np.pi * 1.25 + i * 0.16
        ms = V.wall_moss(f"{ASSET}.moss{i}", width=0.34, height=0.30)
        ms.rotate_y(-a + np.pi * 0.5)
        ms.translate(math.cos(a) * (WELL_R + 0.30), PLINTH + 0.16 + (i % 2) * 0.14,
                     math.sin(a) * (WELL_R + 0.30))
        g.add(ms)
    for i in range(7):
        wd = V.joint_weeds(f"{ASSET}.wd{i}", count=4)
        a = rng.uniform(2.2, 5.0)
        r = rng.uniform(1.9, 3.1)
        wd.translate(math.cos(a) * r, PLINTH + 0.01, math.sin(a) * r)
        g.add(wd)
    # And the worn path from the lane to the drawing side, which is the only
    # part of this apron the moss has never been able to hold.
    g.add(P.worn_patch(f"{ASSET}.path", shape="path", size=2.10, mat="stone")
          .rotate_y(0.9 - np.pi * 0.5)
          .translate(math.cos(0.9) * 1.9, PLINTH + 0.02, math.sin(0.9) * 1.9))


def build(ctx: VenueContext, asset_id=ASSET):
    SITE.bind(ctx)
    rng = rng_for(asset_id, "wellhouse")
    g = M.Group()

    y0 = _platform(ctx, g, rng)
    _well(ctx, g, rng)
    ridge = _roof(ctx, g, rng)
    _trough_and_bench(ctx, g, rng)
    _wet(ctx, g, rng, y0)

    SITE.emit(g, container="wellhouse")

    print(SITE.report())
    print(f"      lip {LIP:.2f}  eaves {EAVES:.2f}  ridge {ridge:.2f}  "
          f"shaft to {PLINTH - 3.10:.2f}  water at {PLINTH - 2.85:.2f}")
