"""Chophouse — slot 07. The restaurant, and the only open fire on the square.

The slot note is a lighting decision before it is anything else: *"North side,
so its front is in shade all morning and its fire-light reads from across the
square at 09:30 — that is why it is here and not on the sunny side."* Every
choice below serves that sentence.

  - The **roasting hearth is on the frontage**, not buried at the back. Its
    chimney breast comes down the front wall and its fire opening is a wide
    segmental brick arch straight onto the market place. At 09:30 the whole
    elevation is in its own shadow and the fire is the brightest thing in it.
  - The **spit turns in that opening** with meat on it, dripping into a pan.
    That is the shop sign; nobody needs a board.
  - **Trestles spill onto the paving** under a canvas awning, because a
    chophouse of this date has almost no seating indoors — the room is the
    kitchen, the street is the dining room.
  - The **menu board is pictorial** (Art Bible §2): carved and painted icons on
    a board — an ox head, a fowl, a fish, a pie — with a peg beside each for the
    day's price in notches. No lettering anywhere in Hearthmere.

## Residue: the greasiest threshold in town

This is the one venue where the residue is *grease*, and it is worth spending
on because no other building in the town has it. Fat has soaked the flags for
sixty years, so the stone at the door is dark and glossy where everything else
in the square is dry and pale. Round it: dropped bones, a dog's worn patch, a
wiping cloth over the rail, mugs and trenchers left on the trestles, a stack of
used wooden platters nobody has washed, and a cat sitting exactly where the
smell is best.
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

NAME = "chophouse"
ASSET = "hm.slot.07.chophouse"

SITE = SI.Site(NAME)
CELLS = SITE.cells

W, D = SITE.w, SITE.d              # 10.0 x 10.0
EAVES = SITE.eaves                 # 6.40
PLINTH = 0.40
GF = 3.00
JETTY = 0.36
PITCH = 0.92

FLOOR = PLINTH
UPPER_Y = FLOOR + GF + 0.26
UPPER_H = EAVES - UPPER_Y

HEARTH_X = 1.85                    # the fire opening, off-centre on the front
HEARTH_W, HEARTH_H = 2.60, 2.05


def _shell(ctx, g, rng):
    poly = SI.rect(0.0, 0.0, W + 0.26, D + 0.26)
    plinth, y0 = SI.plinth_under(SITE, poly, PLINTH, mat="rubble", chamfer=0.03)
    g.add(plinth)
    ctx.collider("box", center=SITE.p(0, (y0 + PLINTH) * 0.5, 0),
                 half=((W + 0.26) * 0.5, max((PLINTH - y0) * 0.5, 0.05),
                       (D + 0.26) * 0.5),
                 rot_y=SITE.yaw(), kind="surface", tag="plinth")

    zf = -D * 0.5
    door_x = -W * 0.5 + 2.15

    front = K.timber_frame_wall(
        W, GF, f"{ASSET}.gf", style="cross", sill_y=FLOOR,
        openings=[(door_x, K.DOOR_H * 0.5 + 0.05, K.DOOR_W + 0.40, K.DOOR_H + 0.30),
                  (HEARTH_X, HEARTH_H * 0.5, HEARTH_W + 0.60, HEARTH_H + 0.55),
                  (-W * 0.5 + 4.6, 1.85, 1.05, 1.05)])
    front.translate(0, 0, zf)
    g.add(front)
    back = K.timber_frame_wall(W, GF, f"{ASSET}.gb", style="square",
                               sill_y=FLOOR,
                               openings=[(-1.2, 1.20, 1.35, 2.20)])
    back.rotate_y(np.pi)
    back.translate(0, 0, -zf)
    g.add(back)
    for sx in (-1, 1):
        side = K.timber_frame_wall(D, GF, f"{ASSET}.gs{sx}", style="cross",
                                   sill_y=FLOOR,
                                   openings=[(-1.6, 1.80, 1.00, 1.00)])
        side.rotate_y(sx * np.pi * 0.5)
        side.translate(sx * W * 0.5, 0, 0)
        g.add(side)

    # The room is a kitchen and it is dark, which is exactly what makes the
    # fire read from the far side of the square.
    sh = M.box(W - 0.5, GF + UPPER_H, D - 0.5, 0.02, "timber_charred")
    sh.scale(-1.0, 1.0, 1.0)
    sh.translate(0, FLOOR + (GF + UPPER_H) * 0.5, 0)
    SITE.emit(sh, shell=True)

    jt = K.jetty(W, D, JETTY)
    jt.translate(0, FLOOR + GF, 0)
    g.add(jt)

    uw, ud = W + JETTY * 2, D + JETTY
    uz = -JETTY * 0.5
    wins = [(-3.55, 1.00, 1.22), (-1.15, 0.90, 1.14), (2.35, 1.10, 1.30),
            (4.30, 0.80, 1.05)]
    up = K.timber_frame_wall(uw, UPPER_H, f"{ASSET}.uf", style="close",
                             sill_y=UPPER_Y,
                             openings=[(x, 1.32, w + 0.18, h + 0.16)
                                       for x, w, h in wins])
    up.translate(0, 0, zf - JETTY)
    g.add(up)
    ub = K.timber_frame_wall(uw, UPPER_H, f"{ASSET}.ub", style="square",
                             sill_y=UPPER_Y)
    ub.rotate_y(np.pi)
    ub.translate(0, 0, -zf)
    g.add(ub)
    for sx in (-1, 1):
        s2 = K.timber_frame_wall(ud, UPPER_H, f"{ASSET}.us{sx}", style="close",
                                 sill_y=UPPER_Y,
                                 openings=[(0.5, 1.32, 0.95, 1.10)])
        s2.rotate_y(sx * np.pi * 0.5)
        s2.translate(sx * uw * 0.5, 0, uz)
        g.add(s2)
    for i, (x, ww, wh) in enumerate(wins):
        w = K.leaded_window(f"{ASSET}.uw{i}", width=ww, height=wh,
                            mat="glass_lit" if i in (1, 2) else "glass",
                            shutters=i == 0, shutter_mat="oak_weathered")
        w.translate(x, UPPER_Y + 1.32, zf - JETTY - 0.07)
        g.add(w)

    # The kitchen light beside the door. The opening was cut in the frame and
    # never filled, and an unglazed rectangle with a dark shell behind it is
    # exactly the black unlit polygon the art director found in three frames.
    kw = K.leaded_window(f"{ASSET}.kitchen", width=0.86, height=0.86,
                         mat="glass_lit", shutters=True,
                         shutter_mat="oak_weathered")
    kw.translate(-W * 0.5 + 4.6, FLOOR + 1.85, zf - 0.07)
    g.add(kw)

    SITE.collider_walls(W, D, GF + UPPER_H, y=FLOOR, thickness=0.30,
                        doors=[("-z", door_x, K.DOOR_W + 0.48)], tag="chophouse")
    SITE.collider_steps((door_x, 0.0, zf - 0.13), PLINTH, tread=0.50,
                        width=1.40)

    rpoly = SI.rect(0.0, uz, uw, ud)
    plate = R.wall_plate(rpoly, EAVES, edges=["eaves", "gable", "eaves", "gable"],
                         thickness=0.30, wall_mat="plaster")
    roof = R.roof_from_plate(plate, "gable", PITCH, 0.46, f"{ASSET}.roof",
                             mat="terracotta", timber_mat="oak_dark",
                             ridge_axis="u")
    g.add(roof)
    for sx in (-1, 1):
        ge = K.gable_end(ud, EAVES, PITCH, mat="plaster", depth=0.24)
        ge.rotate_y(np.pi * 0.5)
        ge.translate(sx * uw * 0.5, 0, uz)
        g.add(ge)
    return door_x, zf, roof


def _hearth(ctx, g, rng, zf, roof):
    """The roasting fire, its arch, its stack, and the spit turning in it.

    Everything here is sized so the fire is visible from the fountain at 34 m:
    the opening is 2.6 m wide and its sill is 0.4 m above the paving, so the
    ember bed is in direct line of sight from the whole southern half of the
    market place.
    """
    x = HEARTH_X
    # The chimney breast is TWO PIERS AND A LINTEL, not a slab. Built as one
    # box it stood 0.75 m proud of the wall with the arch modelled on its back
    # face, so the opening became a relief carving and the fire — the entire
    # reason this venue is sited on the shaded north side of the square — was
    # invisible from anywhere. The arch ring now sits on the FRONT face and the
    # recess runs back to a sooted rear wall, so there is a real hole with a
    # real fire in it, in line of sight from the fountain at 34 m.
    fz = zf - 0.62                            # front face of the breast
    bz = zf + 0.62                            # back of the fire chamber
    depth = bz - fz
    ring = 0.32
    spring = FLOOR + 1.18                     # the arch springs at waist height
    crown = spring + 0.74
    # The piers stand back by the ring depth so the voussoirs are IN the
    # opening rather than buried in the masonry beside it. That is the whole
    # difference between an arch and a rectangle with an arch drawn on it.
    for sx in (-1, 1):
        j = M.box(0.72, crown + ring - FLOOR, depth, 0.03, "brick")
        j.translate(x + sx * (HEARTH_W * 0.5 + ring + 0.36),
                    FLOOR + (crown + ring - FLOOR) * 0.5, (fz + bz) * 0.5)
        g.add(j)
    over = M.box(HEARTH_W + 2 * ring + 1.44,
                 GF + UPPER_H - (crown + ring - FLOOR), depth, 0.03, "brick")
    over.translate(x, crown + ring + (GF + UPPER_H - (crown + ring - FLOOR)) * 0.5,
                   (fz + bz) * 0.5)
    g.add(over)
    # Two corbelled offsets at the head, so 2.5 m of breast is not one flat
    # orange field. Art Bible §7.
    for k, (dy, dw) in enumerate(((0.0, 0.0), (0.19, 0.22))):
        cp = M.box(HEARTH_W + 2 * ring + 1.44 + dw, 0.16, depth + dw, 0.02,
                   "brick")
        cp.translate(x, FLOOR + GF + UPPER_H - 0.10 + dy, (fz + bz) * 0.5)
        g.add(cp)
    arch = K.arch_ring(f"{ASSET}.firearch", span=HEARTH_W, rise=0.74, ring=ring,
                       depth=0.46, mat="brick")
    arch.translate(x, spring, fz + 0.23)
    g.add(arch)
    for sx in (-1, 1):                        # springer jambs under the arch
        j2 = M.box(ring, spring - FLOOR, 0.46, 0.02, "brick")
        j2.translate(x + sx * (HEARTH_W * 0.5 + ring * 0.5),
                     FLOOR + (spring - FLOOR) * 0.5, fz + 0.23)
        g.add(j2)
    # A stone mantel shelf, because that is where the cook's knives live.
    man = M.box(HEARTH_W + 2 * ring + 1.60, 0.20, depth + 0.24, 0.02, "stone")
    man.translate(x, crown + ring + 0.30, (fz + bz) * 0.5 - 0.06)
    g.add(man)

    stack, top = R.chimney_through(roof, x, zf + 0.10, FLOOR + GF, f"{ASSET}.stack",
                                   section=1.05, mat="brick", above=1.35)
    g.add(stack)
    SITE.entity(f"{ASSET}.stack.01", "prop.chimney",
                (x, top, zf + 0.10),
                smoke={"rate": 1.4, "drift": [0.85, 0.0, 0.5]})

    # --- the fire --------------------------------------------------------
    back = M.box(HEARTH_W + 0.6, HEARTH_H + 0.10, 0.26, 0.02, "timber_charred")
    back.translate(x, FLOOR + (HEARTH_H + 0.10) * 0.5, zf + 0.60)
    g.add(back)
    for sxx in (-1, 1):                       # sooted cheeks of the recess
        ck = M.box(0.10, HEARTH_H, 1.20, 0.01, "timber_charred")
        ck.translate(x + sxx * (HEARTH_W * 0.5 - 0.04), FLOOR + HEARTH_H * 0.5,
                     zf + 0.02)
        g.add(ck)
    for sx in (-1, 1):                        # fire-dogs
        fd = M.Group()
        fd.add(M.cylinder(0.030, 0.52, 6, 0.003, "iron_pitted")
               .translate(0, 0.26, 0))
        fd.add(M.lathe([(0.055, 0.0), (0.030, 0.10)], 8, "iron_pitted")
               .translate(0, 0.52, 0))
        bar = M.cylinder(0.024, 0.72, 6, 0.003, "iron_pitted")
        bar.rotate_x(np.pi * 0.5)
        bar.translate(0, 0.11, -0.30)
        fd.add(bar)
        fd.translate(x + sx * 0.86, FLOOR, zf + 0.12)
        g.add(fd)
    # The glow is a small plate BETWEEN the fire-dogs, not a 2.3 x 0.95 m
    # emissive slab: at full opening width it read as a bright rectangle lying
    # on the floor with a hard edge, which is a light box, not a fire.
    bed = M.quad(1.62, 0.62, "coal")
    bed.rotate_x(-np.pi * 0.5)
    bed.translate(x, FLOOR + 0.035, zf + 0.08)
    g.add(bed)
    for i in range(18):
        a = rng.uniform(0, 6.28)
        r = rng.uniform(0.0, 1.0) ** 0.5
        em = M.globe(rng.uniform(0.05, 0.10), "coal", 6, 3, sy=0.55)
        em.translate(x + math.cos(a) * r * 1.05, FLOOR + 0.05,
                     zf + 0.10 + math.sin(a) * r * 0.40)
        g.add(em)
    for i in range(5):                        # logs burning across the dogs
        lg = M.cylinder(rng.uniform(0.055, 0.085), rng.uniform(0.9, 1.25), 7,
                        0.004, "timber_charred")
        lg.rotate_z(np.pi * 0.5)
        lg.rotate_y(rng.uniform(-0.16, 0.16))
        lg.translate(x + rng.uniform(-0.15, 0.15), FLOOR + 0.16 + i * 0.09,
                     zf + 0.06 + rng.uniform(-0.12, 0.12))
        g.add(lg)
    SITE.entity(f"{ASSET}.fire.01", "prop.hearth",
                (x, FLOOR + 0.45, zf + 0.05), verbs=["inspect"],
                light={"color": "#FF8034", "intensity": 5.2, "range": 14.0})

    # --- the spit --------------------------------------------------------
    # A bar across the dogs with a joint on it and a dripping pan under it.
    # Sixty years of that pan is why the threshold outside is black.
    sp = M.cylinder(0.026, HEARTH_W - 0.10, 8, 0.003, "iron")
    sp.rotate_z(np.pi * 0.5)
    sp.translate(x, FLOOR + 0.68, zf - 0.10)
    g.add(sp)
    joint = M.globe(0.30, "leather", 10, 5, sx=1.55, sy=0.86, sz=0.86)
    joint.rotate_z(rng.uniform(-0.1, 0.1))
    joint.translate(x - 0.10, FLOOR + 0.68, zf - 0.10)
    g.add(M.retex(joint, 2.0, 2.0))
    for k in range(3):                        # trussing cord
        cd = M.ring(0.30, 0.010, "canvas", 12)
        cd.rotate_z(np.pi * 0.5)
        cd.scale(1.0, 0.90, 0.90)
        cd.translate(x - 0.42 + k * 0.32, FLOOR + 0.68, zf - 0.10)
        g.add(cd)
    crank = M.Group()
    crank.add(M.cylinder(0.020, 0.28, 6, 0.003, "iron").rotate_z(np.pi * 0.5))
    crank.add(M.cylinder(0.018, 0.22, 6, 0.003, "iron").translate(0.14, -0.11, 0))
    crank.rotate_x(rng.uniform(0, 3.0))
    crank.translate(x + HEARTH_W * 0.5 + 0.05, FLOOR + 0.68, zf - 0.10)
    g.add(crank)
    pan = M.chamfered_prism([(-0.85, -0.26), (0.85, -0.26), (0.90, 0.26),
                             (-0.90, 0.26)], 0.12, "iron_pitted", 0.006,
                            uv_scale=MATS.uv_detail("iron_pitted", 0.625, why="0.12 m member; the library's 1 m tile shows 12% of one tile here and reads as flat colour"))
    pan.rotate_x(np.pi * 0.5)
    pan.translate(x, FLOOR + 0.12, zf - 0.12)
    g.add(pan)

    # Hanging game and a rack of knives on the mantel: the cook's own workflow,
    # left to right — what is waiting, what is cooking, what is being carved.
    g.add(P.hanging_game(f"{ASSET}.game", width=1.15, y=FLOOR + 2.55,
                         wall_z=zf - 0.68, birds=3, hare=True)
          .translate(x - 3.35, 0, 0))
    for i, ln in enumerate((0.34, 0.26, 0.42, 0.20)):
        kn = M.Group()
        kn.add(M.chamfered_prism([(0.0, -0.030), (ln, -0.012), (ln, 0.012),
                                  (0.0, 0.040)], 0.006, "steel_blued", 0.002))
        kn.add(M.cylinder(0.014, 0.13, 6, 0.002, "oak_dark")
               .rotate_z(np.pi * 0.5).translate(-0.07, 0.005, 0))
        kn.rotate_z(-np.pi * 0.5)
        kn.translate(x - 0.95 + i * 0.30, FLOOR + 2.62, zf - 0.90)
        g.add(kn)


def _street_room(ctx, g, rng, door_x, zf):
    """Trestles on the paving under an awning: the room that is actually used.

    Set out the way a working eating-house sets out, which is by SERVICE, not
    symmetry: the tables are ranked along the frontage within a pace of the
    fire so the food arrives hot, the carving block stands between the fire and
    the tables because that is the last stop, and the ale is at the far end
    where it is coolest and where a boy can reach it without crossing the cook.
    """
    yp = 0.0                                   # the paving, outside the plinth
    proj = 2.70                                # how far the awning reaches out
    # Centred on the TABLES, and far enough west that neither post stands in
    # front of the hearth arch (which spans x 0.23 to 3.47).
    ax_c = -2.55
    az = zf - proj
    y_wall = FLOOR + GF - 0.20                 # fixed under the jetty
    y_out = yp + 2.30                          # and falling, because it rains

    # A lean-to awning on two poles. The first cut of this was 7.3 x 3.2 m,
    # almost level, at 2.72 m: from the 1.62 m gameplay eye it was one flat
    # plane across the whole frame with the building hidden behind it. An
    # awning has to FALL — that is what it is for — and the fall is also what
    # opens the elevation back up to the camera.
    # It stops SHORT of the hearth bay. Run the full width it crossed the
    # fire arch at 2.30 m and cut the crown off it from every eye-height
    # camera — and an awning over an open roasting fire is wrong twice over,
    # once architecturally and once compositionally.
    for sx in (-1, 1):
        px = ax_c + sx * 2.55
        po = M.cylinder(0.060, y_out, 7, 0.005, "oak_weathered")
        po.rotate_z(rng.uniform(-0.02, 0.02))
        po.translate(px, yp + y_out * 0.5, az)
        g.add(po)
        ctx.collider("cylinder", center=SITE.p(px, yp + y_out * 0.5, az),
                     radius=0.10, height=y_out, tag="awning_post")
        g.add(M.catenary((px, y_out - 0.06, az),
                         (px + sx * 0.80, yp + 0.05, az - 0.62), 0.05, "canvas",
                         0.009, 8, 4))
    ridge = M.cylinder(0.045, 5.35, 7, 0.004, "oak_weathered")
    ridge.rotate_z(np.pi * 0.5)
    ridge.translate(ax_c, y_out, az)
    g.add(ridge)
    fall = math.atan2(y_wall - y_out, proj)
    span = M.sheet(5.20, math.hypot(proj, y_wall - y_out),
                   lambda u, v: -0.17 * math.sin(u * math.pi) * (0.25 + 0.75 * v),
                   nx=9, nz=6, mat="canvas_amber", plane="xz")
    span.rotate_x(-fall)
    span.translate(ax_c, (y_wall + y_out) * 0.5, (zf + az) * 0.5)
    g.add(span)
    # A scalloped valance on the outer edge, which is the only part of an
    # awning anybody actually sees from across the square.
    val = M.sheet(5.20, 0.34, lambda u, v: -0.05 * abs(math.sin(u * 9.0)),
                  nx=15, nz=3, mat="canvas_crimson", plane="xz")
    val.rotate_x(np.pi * 0.5)
    val.translate(ax_c, y_out - 0.17, az - 0.03)
    g.add(val)
    for sx in (-1, 1):                         # the fixing to the building
        px = ax_c + sx * 2.55
        br = M.tube((px, y_out - 0.04, az), (px, y_wall, zf), 0.022, "iron", 5)
        g.add(br)

    # Two trestles and their benches, neither square to the wall.
    for i, (tx, tz, ta) in enumerate(((-3.35, az + 0.72, 0.075),
                                      (-0.75, az + 1.10, -0.10))):
        t = K.trestle_table(f"{ASSET}.t{i}", length=2.55, width=0.78)
        t.rotate_y(ta)
        t.translate(tx, yp, tz)
        g.add(t)
        ctx.collider("box", center=SITE.p(tx, yp + 0.37, tz),
                     half=(1.30, 0.37, 0.42), rot_y=SITE.yaw(ta), tag="table")
        for s in (-1, 1):
            b = K.bench(f"{ASSET}.b{i}{s}", length=2.35)
            b.rotate_y(ta + rng.uniform(-0.05, 0.05))
            b.translate(tx + math.cos(ta + np.pi * 0.5) * s * 0.78, yp,
                        tz + math.sin(ta + np.pi * 0.5) * s * 0.78)
            g.add(b)
        SITE.entity(f"{ASSET}.table.{i + 1:02d}", "prop.table",
                    (tx, yp + 0.74, tz), verbs=["sit"])

        # What is left on them: a meal half eaten, mugs, and a knife stuck in
        # the board where somebody put it down and forgot it.
        g.add(P.meal(f"{ASSET}.meal{i}", height=0.74).translate(tx - 0.45, yp, tz))
        for k in range(int(rng.integers(2, 5))):
            g.add(P.mug(f"{ASSET}.m{i}{k}", full=rng.random() < 0.5)
                  .translate(tx + rng.uniform(-1.05, 1.05), yp + 0.755,
                             tz + rng.uniform(-0.26, 0.26)))
        for k in range(3):                     # used trenchers, stacked
            tr = M.lathe([(0.135, 0.0), (0.145, 0.018), (0.115, 0.026)], 12,
                         "oak_weathered")
            tr.translate(tx + 1.02, yp + 0.755 + k * 0.026,
                         tz + 0.18 + rng.uniform(-0.02, 0.02))
            g.add(tr)

    # The carving block, between the fire and the tables — the last stop.
    blk = P.chopping_block(f"{ASSET}.block", height=0.82, radius=0.34, axe=False)
    blk.translate(HEARTH_X - 0.55, yp, zf - 1.35)
    g.add(blk)
    ctx.collider("cylinder", center=SITE.p(HEARTH_X - 0.55, yp + 0.41, zf - 1.35),
                 radius=0.36, height=0.82, tag="carving_block")
    cl = M.chamfered_prism([(0.0, -0.045), (0.44, -0.018), (0.44, 0.018),
                            (0.0, 0.055)], 0.008, "steel_blued", 0.002)
    cl.rotate_y(0.7)
    cl.translate(HEARTH_X - 0.62, yp + 0.845, zf - 1.32)
    g.add(cl)
    for k in range(3):
        bn = M.lathe([(0.022, 0.0), (0.014, 0.10), (0.020, 0.16)], 6, "alabaster")
        bn.rotate_z(rng.uniform(1.2, 1.9))
        bn.rotate_y(rng.uniform(0, 6.0))
        bn.translate(HEARTH_X - 0.55 + rng.uniform(-0.55, 0.55), yp + 0.02,
                     zf - 1.35 + rng.uniform(-0.45, 0.45))
        g.add(bn)

    # Ale at the cool end, on a stillage, with a bowl under the tap.
    for i, (bx, by) in enumerate(((3.95, 0.52), (3.95, 0.0))):
        br = K.barrel(f"{ASSET}.cask{i}", height=0.88, belly=0.66)
        if i == 0:
            br.rotate_z(np.pi * 0.5)
        br.translate(bx, yp + by + (0.34 if i == 0 else 0.0), zf - 1.05)
        g.add(br)
    tap = M.lathe([(0.030, 0.0), (0.022, 0.16), (0.036, 0.19)], 8, "brass")
    tap.rotate_x(-np.pi * 0.5)
    tap.translate(3.95, yp + 0.86, zf - 1.42)
    g.add(tap)
    ctx.collider("box", center=SITE.p(3.95, yp + 0.62, zf - 1.05),
                 half=(0.50, 0.62, 0.42), rot_y=SITE.yaw(), tag="stillage")


def _menu_and_grease(ctx, g, rng, door_x, zf):
    """The pictorial board, and the grease that is this venue's whole residue."""
    # --- the board -------------------------------------------------------
    bx, by = door_x + 1.60, FLOOR + 1.15
    bd = M.chamfered_prism([(-0.72, 0.0), (0.72, 0.0), (0.72, 1.05),
                            (-0.72, 1.05)], 0.055, "oak_dark", 0.010,
                           uv_scale=MATS.uv_detail("oak_dark", 0.769, why="0.06 m member; the library's 2 m tile shows 3% of one tile here and reads as flat colour"))
    bd.translate(bx, by, zf - 0.12)
    g.add(bd)
    ledge = M.plank(1.52, 0.10, 0.14, 0.006, "oak_weathered")
    ledge.translate(bx, by - 0.03, zf - 0.18)
    g.add(ledge)

    # Four carved icons: an ox head, a fowl, a fish, a pie. Each has a peg row
    # beside it and the pegs are what carry the day's price — Art Bible §2 is
    # absolute about lettering, and a peg board is how an illiterate town
    # actually priced things.
    def ox(m):
        o = M.Group()
        o.add(M.globe(0.085, m, 8, 4, sx=0.85, sz=1.25))
        for s in (-1, 1):
            h = M.lathe([(0.020, 0.0), (0.010, 0.13)], 6, m)
            h.rotate_z(s * 0.9)
            h.translate(s * 0.070, 0.055, 0)
            o.add(h)
        return o

    def fowl(m):
        o = M.Group()
        o.add(M.globe(0.075, m, 8, 4, sx=0.80, sy=0.95, sz=1.20))
        n = M.lathe([(0.024, 0.0), (0.0, 0.11)], 6, m)
        n.rotate_z(-0.5)
        n.translate(0.045, 0.075, 0)
        o.add(n)
        return o

    def fish(m):
        o = M.Group()
        o.add(M.globe(0.062, m, 8, 4, sx=1.75, sy=0.85, sz=0.45))
        t = M.chamfered_prism([(0.0, 0.0), (0.075, 0.070), (0.075, -0.070)],
                              0.014, m, 0.003)
        t.translate(-0.105, 0.0, 0.0)
        o.add(t)
        return o

    def pie(m):
        o = M.Group()
        o.add(M.lathe([(0.088, 0.0), (0.092, 0.045), (0.070, 0.070),
                       (0.0, 0.078)], 12, m))
        return o

    for i, (mk, col) in enumerate(((ox, "painted_crimson"), (fowl, "painted_amber"),
                                   (fish, "alabaster"), (pie, "painted_amber"))):
        ic = mk(col)
        ic.rotate_y(rng.uniform(-0.15, 0.15))
        ic.translate(bx - 0.46, by + 0.90 - i * 0.235, zf - 0.20)
        g.add(ic)
        for k in range(4):
            pg = M.cylinder(0.010, 0.045, 5, 0.002, "oak")
            pg.rotate_x(np.pi * 0.5)
            pg.translate(bx + 0.02 + k * 0.145, by + 0.90 - i * 0.235,
                         zf - 0.165)
            g.add(pg)
        if i < 3:
            for k in range(3 - i):
                dk = M.ring(0.026, 0.008, "iron", 8)
                dk.rotate_x(np.pi * 0.5)
                dk.translate(bx + 0.02 + k * 0.145, by + 0.90 - i * 0.235,
                             zf - 0.185)
                g.add(dk)
    SITE.entity(f"{ASSET}.menu.01", "prop.menu_board",
                (bx, by + 0.52, zf - 0.20), verbs=["inspect"])

    # --- the grease ------------------------------------------------------
    # Dark, glossy flags at the door and under the fire, spreading with the
    # traffic. `mud_wet` is the library's one dark wet surface and this is
    # exactly the read: stone soaked black and shining at 09:30.
    for i, (r, dn, cx, cz) in enumerate(((1.30, 1.0, door_x, zf - 0.75),
                                         (2.10, 0.6, door_x + 0.5, zf - 1.55),
                                         (1.55, 0.8, HEARTH_X, zf - 1.05))):
        g.add(P.dust_film(f"{ASSET}.grease{i}", radius=r, mat="mud_wet",
                          centre=(cx, cz), y=0.0, density=dn))
    th = S.threshold_stone(f"{ASSET}.step", width=1.55, depth=0.72, rise=0.12)
    th.translate(door_x, PLINTH - 0.12, zf - 0.38)
    g.add(th)
    g.add(P.worn_patch(f"{ASSET}.arc", shape="arc", size=0.90, mat="mud_wet")
          .translate(door_x, 0.012, zf - 0.95))
    # The dog that lives here, or rather the patch where it lies.
    g.add(P.worn_patch(f"{ASSET}.dog", shape="cat", size=0.85, mat="mud_wet")
          .rotate_y(0.6).translate(HEARTH_X - 2.15, 0.012, zf - 1.85))
    # A wiping cloth over the awning rail, greasy at one end.
    # Hung OVER the awning pole with a belly and a fold, the way a wet cloth
    # actually hangs. As a flat quad tipped 86 degrees it read as a hoarding.
    cw = M.sheet(0.44, 0.62,
                 lambda u, v: (math.sin(u * math.pi) ** 0.7) * 0.07 * (0.3 + v)
                 + math.sin(u * 7.0) * 0.012 * v,
                 nx=7, nz=6, mat="linen", plane="xy")
    cw.rotate_y(np.pi * 0.5)
    cw.translate(-4.60, 2.30 - 0.32, zf - 2.70)
    g.add(cw)
    # A stack of unwashed platters by the door, and the bucket they will be
    # washed in when somebody gets round to it.
    for k in range(6):
        tr = M.lathe([(0.14, 0.0), (0.15, 0.020), (0.12, 0.028)], 12,
                     "oak_weathered")
        tr.rotate_y(rng.uniform(-0.4, 0.4))
        tr.translate(door_x - 1.05 + rng.uniform(-0.02, 0.02),
                     PLINTH + 0.02 + k * 0.028, zf - 0.55)
        g.add(tr)
    g.add(P.bucket(f"{ASSET}.wash", height=0.34, top=0.19, full=True)
          .translate(door_x - 1.42, PLINTH, zf - 0.72))
    # And a bone the dog has taken as far as the kerb.
    bn = M.lathe([(0.028, 0.0), (0.016, 0.12), (0.026, 0.19)], 6, "alabaster")
    bn.rotate_z(1.5)
    bn.rotate_y(rng.uniform(0, 6.0))
    bn.translate(door_x - 2.35, 0.03, zf - 2.15)
    g.add(bn)


def build(ctx: VenueContext, asset_id=ASSET):
    SITE.bind(ctx)
    rng = rng_for(asset_id, "chophouse")
    g = M.Group()

    door_x, zf, roof = _shell(ctx, g, rng)
    _hearth(ctx, g, rng, zf, roof)
    _street_room(ctx, g, rng, door_x, zf)
    _menu_and_grease(ctx, g, rng, door_x, zf)

    fr = K.door_frame(width=1.06, height=2.12, mat="oak_dark", depth=0.30)
    fr.translate(door_x, FLOOR, zf - 0.10)
    g.add(fr)
    dr = K.plank_door(f"{ASSET}.door", width=1.02, height=2.08,
                      mat="oak_weathered", open_angle=1.15)
    dr.translate(door_x, FLOOR, zf - 0.20)
    g.add(dr)
    SITE.entity(f"{ASSET}.door.01", "door.chophouse",
                (door_x, FLOOR, zf - 0.22), verbs=["enter"])

    SITE.emit(g, container="chophouse")

    print(SITE.report())
    print(f"      hearth opening {HEARTH_W:.2f}x{HEARTH_H:.2f} at "
          f"x{HEARTH_X:+.2f}  eaves {EAVES:.2f}  awning 2.72")
