"""Bakery — slot 32. The oven is the building.

A bakehouse is not a shop with an oven in it. It is an oven with a shop stuck
on the front, and everything about the plan follows from the oven's own
requirements: a brick dome that takes four hours to heat and holds that heat
all day, a flue tall enough to draw it, stone walls round it because it is the
one permanent open fire on this street, and the whole thing set at the BACK of
the plot with the fire lane behind — which is precisely what the slot note
authors ("oven-house projecting south with a 12.0 m stone flue").

So the mass is two things and reads as two things:

  **The shop**, two storeys, timber, on Bakers' Row, with the widest unglazed
  opening in Hearthmere. It is unglazed because bread is sold hot and the
  smell is the advertisement; glass would be both unaffordable and stupid.

  **The oven-house**, single storey, stone, behind it, with a flue to 12.0 m —
  the second tallest chimney in the town and the landmark the south road sees
  before it sees anything else inside the wall.

The two are joined by the one element that matters: the **oven mouth opens
into the shop**. Stand on Bakers' Row and you look straight through the
counter opening at a lit brick arch with a fire in it, forty feet away, all
day. That is the strongest single read any venue in this quarter has and it is
free — it is just where a real oven goes.

## Function, arranged by workflow

Flour store (sacks against the cool north wall) -> trough (kneading) -> bench
(shaping) -> peel -> **oven** -> cooling rack -> the window -> the counter.
That is the order a baking runs in, it is the order the objects stand in from
the back of the shop to the street, and it is why the customer is looking at
the fire down the whole length of the working line.

## Residue

Flour. Art Bible §7's rule about dust is that it settles, it does not stop at
an edge — so it is on the trough, on the bench, on the sill, on the counter,
on the step, on the flags a metre outside the door, and it is thinner the
further out it goes. Slot 32 says five metres. Plus the queue: the threshold of
a bakery is the most walked-on stone in a town of three hundred, because every
one of them comes here every day.
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

NAME = "bakery"
ASSET = "hm.slot.32.bakery"

SITE = SI.Site(NAME)
CELLS = SITE.cells

W, D = SITE.w, SITE.d              # 11.0 x 10.0
EAVES = SITE.eaves                 # 6.60
PLINTH = 0.46
GF = 3.05
JETTY = 0.30
PITCH = 0.90
FLUE_TOP = 12.00                   # slot note; the landmark

FLOOR = PLINTH
UPPER_Y = FLOOR + GF + 0.24
UPPER_H = EAVES - UPPER_Y

SHOP_D = 6.4                       # the shop range, front part of the plot
SHOP_Z0, SHOP_Z1 = -D * 0.5, -D * 0.5 + SHOP_D
OVEN_W, OVEN_D = 5.6, 3.3          # the oven-house, behind it
OVEN_X = 1.6
OVEN_Z0, OVEN_Z1 = SHOP_Z1, SHOP_Z1 + OVEN_D
OVEN_H = 3.10


def _shop(ctx, g, rng):
    """The two-storey timber shop on Bakers' Row, and the opening in its front."""
    poly = SI.rect(0.0, (SHOP_Z0 + SHOP_Z1) * 0.5, W + 0.26, SHOP_D + 0.26)
    plinth, y0 = SI.plinth_under(SITE, poly, PLINTH, mat="rubble", chamfer=0.03)
    g.add(plinth)
    ctx.collider("box",
                 center=SITE.p(0, (y0 + PLINTH) * 0.5, (SHOP_Z0 + SHOP_Z1) * 0.5),
                 half=((W + 0.26) * 0.5, max((PLINTH - y0) * 0.5, 0.05),
                       (SHOP_D + 0.26) * 0.5),
                 rot_y=SITE.yaw(), kind="surface", tag="plinth")

    zf = SHOP_Z0
    door_x = -W * 0.5 + 2.05
    win_x, win_w, win_h = 1.55, 3.60, 1.42     # the widest opening in town
    sill = FLOOR + 1.00

    front = K.timber_frame_wall(
        W, GF, f"{ASSET}.gf", style="square", sill_y=FLOOR,
        openings=[(door_x, K.DOOR_H * 0.5 + 0.06, K.DOOR_W + 0.42, K.DOOR_H + 0.30),
                  (win_x, sill - FLOOR + win_h * 0.5, win_w + 0.26, win_h + 0.24)])
    front.translate(0, 0, zf)
    g.add(front)
    back = K.timber_frame_wall(
        W, GF, f"{ASSET}.gb", style="square", sill_y=FLOOR,
        openings=[(OVEN_X, 1.28, 2.55, 2.45)])   # the oven arch, into the shop
    back.rotate_y(np.pi)
    back.translate(0, 0, SHOP_Z1)
    g.add(back)
    for sx in (-1, 1):
        side = K.timber_frame_wall(SHOP_D, GF, f"{ASSET}.gs{sx}", style="square",
                                   sill_y=FLOOR,
                                   openings=[(1.4, 1.70, 0.95, 1.05)] if sx < 0 else None)
        side.rotate_y(sx * np.pi * 0.5)
        side.translate(sx * W * 0.5, 0, (SHOP_Z0 + SHOP_Z1) * 0.5)
        g.add(side)

    # The interior shell stops SHORT of the back wall. Full depth, its own back
    # face stood between the counter opening and the oven mouth and hid the one
    # thing this building is for — the fire, lit, seen from the street all day.
    sh_d = SHOP_D - 2.30
    sh = M.box(W - 0.5, GF, sh_d, 0.02, "oak_dark")
    sh.scale(-1.0, 1.0, 1.0)
    sh.translate(0, FLOOR + GF * 0.5, SHOP_Z0 + 0.25 + sh_d * 0.5)
    SITE.emit(sh, shell=True)

    jt = K.jetty(W, SHOP_D, JETTY)
    jt.translate(0, FLOOR + GF, (SHOP_Z0 + SHOP_Z1) * 0.5)
    g.add(jt)

    uw, ud = W + JETTY * 2, SHOP_D + JETTY
    uz = (SHOP_Z0 + SHOP_Z1) * 0.5 - JETTY * 0.5
    wins = [(-3.4, 0.95, 1.20), (-0.6, 1.05, 1.28), (2.7, 0.88, 1.14),
            (4.6, 0.72, 1.00)]
    up = K.timber_frame_wall(uw, UPPER_H, f"{ASSET}.uf", style="square",
                             sill_y=UPPER_Y,
                             openings=[(x, 1.30, w + 0.18, h + 0.16)
                                       for x, w, h in wins])
    up.translate(0, 0, SHOP_Z0 - JETTY)
    g.add(up)
    ub = K.timber_frame_wall(uw, UPPER_H, f"{ASSET}.ub", style="square",
                             sill_y=UPPER_Y)
    ub.rotate_y(np.pi)
    ub.translate(0, 0, SHOP_Z1)
    g.add(ub)
    for sx in (-1, 1):
        s2 = K.timber_frame_wall(ud, UPPER_H, f"{ASSET}.us{sx}", style="square",
                                 sill_y=UPPER_Y,
                                 openings=[(0.0, 1.30, 0.90, 1.10)])
        s2.rotate_y(sx * np.pi * 0.5)
        s2.translate(sx * uw * 0.5, 0, uz)
        g.add(s2)
    for i, (x, ww, wh) in enumerate(wins):
        w = K.leaded_window(f"{ASSET}.uw{i}", width=ww, height=wh,
                            mat="glass", shutters=i == 3,
                            shutter_mat="oak_weathered")
        w.translate(x, UPPER_Y + 1.30, SHOP_Z0 - JETTY - 0.07)
        g.add(w)

    SITE.collider_walls(W, SHOP_D, GF + UPPER_H, y=FLOOR, thickness=0.30,
                        center=(0.0, (SHOP_Z0 + SHOP_Z1) * 0.5),
                        doors=[("-z", door_x, K.DOOR_W + 0.50)], tag="shop")
    SITE.collider_steps((door_x, 0.0, SHOP_Z0 - 0.13), PLINTH,
                        tread=0.50, width=1.45)

    # --- roof ------------------------------------------------------------
    rpoly = SI.rect(0.0, uz, uw, ud)
    plate = R.wall_plate(rpoly, EAVES, edges=["eaves", "gable", "eaves", "gable"],
                         thickness=0.30, wall_mat="plaster")
    roof = R.roof_from_plate(plate, "gable", PITCH, 0.48, f"{ASSET}.roof",
                             mat="terracotta", timber_mat="oak_dark",
                             ridge_axis="u")
    g.add(roof)
    for sx in (-1, 1):
        ge = K.gable_end(ud, EAVES, PITCH, mat="plaster", depth=0.24)
        ge.rotate_y(np.pi * 0.5)
        ge.translate(sx * uw * 0.5, 0, uz)
        g.add(ge)
    return door_x, win_x, win_w, win_h, sill, zf, roof


def _oven_house(ctx, g, rng):
    """Stone oven-house and the 12 m flue: the landmark half of the building.

    Stone, and the only stone building on Bakers' Row, because a bakehouse is
    the fire risk a timber town is most afraid of. The flue is deliberately
    over-tall: draught is what gets a beehive oven to temperature, and a 12 m
    stack on a 3 m building is what a town builds when the alternative is
    burning down the street.
    """
    poly = SI.rect(OVEN_X, (OVEN_Z0 + OVEN_Z1) * 0.5, OVEN_W + 0.3, OVEN_D + 0.3)
    plinth, y0 = SI.plinth_under(SITE, poly, PLINTH, mat="rubble", chamfer=0.03)
    g.add(plinth)

    top = PLINTH + OVEN_H
    for (a0, a1, b0, b1) in (
            (OVEN_X - OVEN_W * 0.5, OVEN_X + OVEN_W * 0.5, OVEN_Z1 - 0.42, OVEN_Z1),
            (OVEN_X - OVEN_W * 0.5, OVEN_X - OVEN_W * 0.5 + 0.42, OVEN_Z0, OVEN_Z1),
            (OVEN_X + OVEN_W * 0.5 - 0.42, OVEN_X + OVEN_W * 0.5, OVEN_Z0, OVEN_Z1)):
        g.add(SI.slab([(a0, b0), (a1, b0), (a1, b1), (a0, b1)], PLINTH, top,
                      "rubble", 0.035))

    # A catslide off the shop's rear plate down over the oven-house — one
    # continuous fall, which is what makes the two masses read as one building
    # that grew rather than two models pushed together.
    rp = SI.rect(OVEN_X, (OVEN_Z0 + OVEN_Z1) * 0.5 + 0.1, OVEN_W + 0.5, OVEN_D + 0.7)
    plate = R.wall_plate(rp, PLINTH + OVEN_H,
                         edges=["abut", "gable", "eaves", "gable"],
                         thickness=0.30, wall_mat="rubble")
    orf = R.roof_from_plate(plate, "lean_to", 0.46, 0.40, f"{ASSET}.ovenroof",
                            mat="terracotta", timber_mat="oak_dark",
                            ridge_axis="v")
    g.add(orf)

    # --- the flue --------------------------------------------------------
    fx, fz = OVEN_X, OVEN_Z1 - 0.28
    base = PLINTH
    stages = ((base, 4.2, 1.34), (4.2, 8.0, 1.14), (8.0, FLUE_TOP - 0.55, 0.96))
    for i, (a, b, s) in enumerate(stages):
        st = M.box(s, b - a, s * 0.88, 0.03, "rubble")
        st.translate(fx, (a + b) * 0.5, fz)
        g.add(st)
        if i:
            off = M.box(s + 0.22, 0.16, s * 0.88 + 0.22, 0.025, "ashlar")
            off.translate(fx, a + 0.08, fz)
            g.add(off)
    # Corbelled cap and two pots — the profile that reads at 100 m.
    for k, (dy, ds) in enumerate(((0.0, 0.96), (0.17, 1.16), (0.34, 1.34))):
        c = M.box(ds, 0.18, ds * 0.88, 0.025, "ashlar")
        c.translate(fx, FLUE_TOP - 0.55 + dy + 0.09, fz)
        g.add(c)
    for sx in (-1, 1):
        pot = M.lathe([(0.17, 0.0), (0.19, 0.07), (0.175, 0.44), (0.20, 0.52)],
                      12, "terracotta", close_top=False)
        pot.translate(fx + sx * 0.26, FLUE_TOP - 0.09, fz)
        g.add(pot)
    SITE.entity(f"{ASSET}.flue.01", "landmark.bakery_flue",
                (fx, FLUE_TOP, fz), verbs=["inspect"],
                smoke={"rate": 1.1, "drift": [0.9, 0.0, 0.55]},
                landmark={"name": "The Bakehouse Flue", "silhouette": True})
    ctx.collider("box", center=SITE.p(fx, PLINTH + 2.0, fz),
                 half=(0.70, 2.0, 0.62), rot_y=SITE.yaw(), tag="flue")
    SITE.collider_walls(OVEN_W, OVEN_D, OVEN_H, y=PLINTH, thickness=0.42,
                        center=(OVEN_X, (OVEN_Z0 + OVEN_Z1) * 0.5),
                        doors=[("-x", 0.0, 1.30)], tag="ovenhouse")

    # The yard door in the oven-house's west flank: townspeople bring their own
    # dough here and pay the baker to bake it, and that door is how they do it.
    ax = OVEN_X - OVEN_W * 0.5 - 0.02
    az = (OVEN_Z0 + OVEN_Z1) * 0.5
    arch = K.arch_ring(f"{ASSET}.yardarch", span=1.30, rise=0.62, ring=0.26,
                       depth=0.52, mat="brick")
    arch.rotate_y(np.pi * 0.5)
    arch.translate(ax, PLINTH + 1.55, az)
    g.add(arch)
    dr = K.plank_door(f"{ASSET}.yarddoor", width=1.24, height=1.95,
                      mat="oak_weathered", open_angle=0.95)
    dr.rotate_y(np.pi * 0.5)
    dr.translate(ax - 0.06, PLINTH, az)
    g.add(dr)
    SITE.entity(f"{ASSET}.yarddoor.01", "door.bakehouse",
                (ax - 0.10, PLINTH, az), verbs=["enter"])
    return top


def _oven(ctx, g, rng):
    """The beehive itself: a brick dome, its arched mouth, and the fire in it.

    The mouth opens through the shop's back wall, so it is lit and visible from
    the street through the counter opening all day. `coal` is the one emissive
    material in the library and this is exactly what it is for.
    """
    mz = SHOP_Z1 - 0.02                       # face of the mouth, in the shop
    ox = OVEN_X
    hearth = FLOOR + 0.86                     # a beehive oven's floor is waist high

    # Brick surround round the mouth — the one brick face in the shop.
    sur = M.box(2.55, 2.45, 0.42, 0.03, "brick")
    sur.translate(ox, FLOOR + 1.28, mz + 0.20)
    g.add(sur)
    arch = K.arch_ring(f"{ASSET}.mouth", span=1.15, rise=0.52, ring=0.20,
                       depth=0.62, mat="brick")
    arch.translate(ox, hearth, mz - 0.02)
    g.add(arch)
    # The dome behind it, seen only from the oven-house side but built because
    # the flue has to spring off something and the mass has to be there.
    dome = M.lathe([(1.36, 0.0), (1.34, 0.34), (1.10, 0.86), (0.62, 1.18),
                    (0.0, 1.30)], 16, "brick")
    dome.translate(ox, hearth, SHOP_Z1 + 1.55)
    g.add(dome)

    # The oven chamber and the fire. A dark brick barrel with a bed of embers
    # raked to one side, which is how a beehive oven is fired: the fire goes in,
    # the fire comes out, the bread goes in on the stored heat.
    ch = M.lathe([(1.06, 0.0), (1.02, 0.28), (0.80, 0.62), (0.0, 0.82)], 14,
                 "timber_charred")
    ch.scale(-1.0, 1.0, 1.0)
    ch.translate(ox, hearth, SHOP_Z1 + 1.30)
    g.add(ch)
    fl = M.box(2.10, 0.05, 2.20, 0.01, "cinder")
    fl.translate(ox, hearth + 0.02, SHOP_Z1 + 1.05)
    g.add(fl)
    # The embers are raked to the mouth end of the sole, which is where a baker
    # leaves them between draws and — not coincidentally — the only place they
    # can be seen from Bakers' Row through the counter opening.
    for i in range(14):
        a = rng.uniform(0, 6.28)
        r = rng.uniform(0.2, 1.0) ** 0.5
        em = M.globe(rng.uniform(0.055, 0.115), "coal", 6, 3, sy=0.5)
        em.translate(ox + math.cos(a) * r * 0.72, hearth + 0.05,
                     SHOP_Z1 + 0.42 + math.sin(a) * r * 0.34)
        g.add(em)
    glow = M.quad(1.90, 1.05, "coal")
    glow.rotate_x(-math.pi * 0.5)
    glow.translate(ox, hearth + 0.015, SHOP_Z1 + 0.45)
    g.add(glow)
    SITE.entity(f"{ASSET}.oven.01", "prop.oven",
                (ox, hearth + 0.30, mz - 0.30), verbs=["inspect"],
                light={"color": "#FF7A2E", "intensity": 3.4, "range": 9.0})

    # The iron oven door, leaning against the brickwork where it was set down —
    # a bakehouse door is a slab of iron with a handle and it never gets hung
    # back up between draws.
    dr = M.chamfered_prism([(-0.62, 0.0), (0.62, 0.0), (0.62, 0.66),
                            (0.0, 0.86), (-0.62, 0.66)], 0.055, "iron_pitted",
                           0.008, uv_scale=MATS.uv_detail("iron_pitted", 0.714, why="0.06 m member; the library's 1 m tile shows 6% of one tile here and reads as flat colour"))
    P.lean(dr, 0.90, 0.24, wall_z=mz - 0.22, x=ox - 1.05)
    dr.translate(0, hearth * 0.0 + FLOOR, 0)
    g.add(dr)
    hd = M.tube((ox - 1.05, FLOOR + 0.62, mz - 0.44), (ox - 1.05, FLOOR + 0.78, mz - 0.50),
                0.018, "iron", 5)
    g.add(hd)

    # Ash raked out at the mouth, and the rake standing in it.
    g.add(P.dust_film(f"{ASSET}.ash", radius=0.70, mat="cinder",
                      centre=(ox + 1.15, mz - 0.55), y=FLOOR, density=0.9))
    rake = M.Group()
    rake.add(M.cylinder(0.019, 1.90, 6, 0.003, "oak_weathered"))
    hh = M.box(0.34, 0.055, 0.09, 0.004, "iron")
    hh.translate(0, -0.02, 0)
    rake.add(hh)
    P.lean(rake, 1.90, 0.36, wall_z=mz - 0.30, x=ox + 1.42,
           roll=rng.uniform(-0.08, 0.08))
    rake.translate(0, FLOOR, 0)
    g.add(rake)
    return hearth


def _working_line(ctx, g, rng, hearth):
    """Flour store, trough, bench, peels, racks — in the order a baking runs.

    `props.baker_kit` is the trough, the peels, the flour barrel, a cooling
    rack of loaves and the metre of flour dust round all of it, in one call.
    It is placed facing the oven, on the working side of the shop, so the whole
    line from the door to the fire is legible through the counter opening.
    """
    kit = P.baker_kit(f"{ASSET}.kit", wall_z=SHOP_Z1 - 0.55)
    kit.rotate_y(0.10)
    kit.translate(-2.4, FLOOR, -0.30)
    g.add(kit)
    ctx.collider("box", center=SITE.p(-2.4, FLOOR + 0.48, SHOP_Z1 - 1.05),
                 half=(0.90, 0.48, 0.42), rot_y=SITE.yaw(), tag="dough_trough")

    # Flour sacks against the cool north-west corner, one split and spilling.
    sacks = P.sack_stack(f"{ASSET}.sacks", count=5, wall_z=0.0)
    sacks.rotate_y(0.35)
    sacks.translate(-W * 0.5 + 1.05, FLOOR, SHOP_Z1 - 0.75)
    g.add(sacks)
    g.add(P.spill(f"{ASSET}.split", kind="flour", radius=0.72, density=0.9,
                  centre=(-W * 0.5 + 1.6, SHOP_Z1 - 1.35))
          .translate(0, FLOOR, 0))

    # Shaping bench between the trough and the oven, with dough on it.
    bench = M.plank(2.20, 0.68, 0.075, 0.008, "oak_weathered")
    bench.translate(-0.55, FLOOR + 0.90, SHOP_Z1 - 1.85)
    g.add(bench)
    for sx in (-1, 1):
        for sz in (-1, 1):
            lg = M.box(0.085, 0.90, 0.085, 0.006, "oak_dark")
            lg.translate(-0.55 + sx * 0.95, FLOOR + 0.45,
                         SHOP_Z1 - 1.85 + sz * 0.24)
            g.add(lg)
    for i in range(5):
        dg = M.globe(rng.uniform(0.085, 0.115), "bread", 8, 3, sy=0.62, sz=0.86)
        dg.rotate_y(rng.uniform(-3, 3))
        dg.translate(-1.35 + i * 0.38 + rng.uniform(-0.04, 0.04),
                     FLOOR + 0.97, SHOP_Z1 - 1.85 + rng.uniform(-0.14, 0.14))
        g.add(M.retex(dg, 2.0, 2.0, rng.uniform(0, 0.6)))
    g.add(P.dust_film(f"{ASSET}.benchflour", radius=0.85, mat="flour",
                      centre=(-0.55, SHOP_Z1 - 2.35), y=FLOOR, density=0.7))
    # And on the bench top itself, because that is where it is thrown.
    g.add(P.dust_film(f"{ASSET}.benchtop", radius=0.95, mat="flour",
                      centre=(-0.55, SHOP_Z1 - 1.85), y=FLOOR + 0.94,
                      density=0.5))

    # Faggots for firing, stacked in the corner by the oven arch. Brushwood,
    # not logs: a beehive oven is fired with fast hot wood.
    for r in range(3):
        for i in range(4):
            fg = M.lathe([(0.075, 0.0), (0.065, 1.10)], 7, "timber_grey")
            fg.rotate_z(np.pi * 0.5)
            fg.rotate_y(rng.uniform(-0.05, 0.05))
            fg.translate(W * 0.5 - 1.35, FLOOR + 0.09 + r * 0.155,
                         SHOP_Z1 - 0.42 - i * 0.17)
            g.add(fg)
    for r in range(3):
        for i in range(4):
            bd = M.ring(0.078, 0.010, "canvas", 8)
            bd.rotate_y(np.pi * 0.5)
            bd.translate(W * 0.5 - 1.35 + (0.34 if i % 2 else -0.34),
                         FLOOR + 0.09 + r * 0.155, SHOP_Z1 - 0.42 - i * 0.17)
            g.add(bd)
    ctx.collider("box", center=SITE.p(W * 0.5 - 1.35, FLOOR + 0.28, SHOP_Z1 - 0.72),
                 half=(0.60, 0.28, 0.42), rot_y=SITE.yaw(), tag="faggots")


def _counter(ctx, g, rng, door_x, win_x, win_w, win_h, sill, zf):
    """The counter opening: unglazed, shuttered, and full of bread.

    No glass. Bread is sold hot through a hole in the wall, the shutter drops
    to make the counter, and the cooling racks stand INSIDE the opening so the
    loaves are the first thing anybody sees. Bread is the warmest colour note
    on this street and it is spent here deliberately.
    """
    op_y = sill + win_h * 0.5
    for sy in (-1, 1):
        r = M.plank(win_w + 0.30, 0.15, 0.24, 0.008, "oak_dark")
        r.translate(win_x, op_y + sy * (win_h * 0.5 + 0.075), zf - 0.13)
        g.add(r)
    for sx in (-1, 1):
        j = M.box(0.15, win_h + 0.30, 0.24, 0.008, "oak_dark")
        j.translate(win_x + sx * (win_w * 0.5 + 0.075), op_y, zf - 0.13)
        g.add(j)

    # Upper shutter propped as an awning; lower shutter down as the counter.
    up = M.Group()
    for i in range(6):
        b = M.box(win_w / 6 * 0.95, 0.72, 0.032, 0.005, "oak_weathered")
        b.translate(-win_w * 0.5 + (i + 0.5) * win_w / 6, 0, 0)
        up.add(b)
    up.add(M.plank(win_w * 0.96, 0.09, 0.026, 0.004, "oak_weathered")
           .translate(0, 0, 0.030))
    up.rotate_x(-1.20)
    up.translate(win_x, op_y + win_h * 0.5 + 0.22, zf - 0.50)
    g.add(up)
    for sx in (-1, 1):
        st = M.cylinder(0.021, 0.92, 6, 0.003, "oak_weathered")
        st.rotate_x(0.56)
        st.translate(win_x + sx * win_w * 0.40, op_y + win_h * 0.5 - 0.02, zf - 0.34)
        g.add(st)

    low = M.Group()
    for i in range(6):
        b = M.box(win_w / 6 * 0.95, 0.80, 0.034, 0.005, "oak_weathered")
        b.translate(-win_w * 0.5 + (i + 0.5) * win_w / 6, 0, 0)
        low.add(b)
    low.rotate_x(np.pi * 0.5)
    cy = op_y - win_h * 0.5 - 0.02
    low.translate(win_x, cy, zf - 0.52)
    g.add(low)
    for sx in (-1, 1):
        lg = M.box(0.08, cy - PLINTH, 0.08, 0.006, "oak_weathered")
        lg.translate(win_x + sx * win_w * 0.42, PLINTH + (cy - PLINTH) * 0.5,
                     zf - 0.86)
        g.add(lg)
    ctx.collider("box", center=SITE.p(win_x, (PLINTH + cy) * 0.5, zf - 0.50),
                 half=(win_w * 0.5, (cy - PLINTH) * 0.5, 0.44),
                 rot_y=SITE.yaw(), tag="counter")

    # Cooling racks standing IN the opening — four shelves of loaves.
    # The racks fill the LEFT half of the opening only. Across the full width
    # they walled off the one sightline this building is built around: the oven
    # mouth, lit, straight down the middle of the opening from the street.
    rx, rw = win_x - win_w * 0.26, win_w * 0.44
    for r in range(3):
        y = cy + 0.30 + r * 0.40
        shf = M.plank(rw, 0.36, 0.028, 0.005, "oak_weathered")
        shf.translate(rx, y, zf + 0.30)
        g.add(shf)
        for i in range(4):
            lf = M.globe(rng.uniform(0.080, 0.100), "bread", 8, 3,
                         sy=0.66, sz=0.84)
            lf.rotate_y(rng.uniform(-3, 3))
            lf.translate(rx - rw * 0.36 + i * rw * 0.24,
                         y + 0.085, zf + 0.30 + rng.uniform(-0.06, 0.06))
            g.add(M.retex(lf, 2.0, 2.0, rng.uniform(0, 0.7)))
    for sx in (-1, 1):
        up_ = M.box(0.06, 1.55, 0.06, 0.005, "oak_dark")
        up_.translate(rx + sx * rw * 0.55, cy + 0.78, zf + 0.30)
        g.add(up_)

    # Baskets of loaves on the counter itself, and one on the flags below.
    for i in range(3):
        bk = P.basket(f"{ASSET}.bk{i}", radius=0.22, height=0.17, weave="coil",
                      fill="loaves")
        bk.rotate_y(rng.uniform(-3, 3))
        bk.translate(win_x - 1.15 + i * 1.05 + rng.uniform(-0.08, 0.08),
                     cy + 0.02, zf - 0.52 + rng.uniform(-0.07, 0.07))
        g.add(bk)
    bk = P.basket(f"{ASSET}.bkfloor", radius=0.26, height=0.30, weave="stake",
                  fill="loaves")
    bk.rotate_y(rng.uniform(-3, 3))
    bk.translate(win_x + 2.05, PLINTH, zf - 0.62)
    g.add(bk)
    SITE.entity(f"{ASSET}.counter.01", "vendor.baker",
                (win_x, cy, zf - 0.52), verbs=["buy"],
                vendor={"currency": "copper", "stock": [
                    {"item": "loaf_maslin", "price": 3, "qty": -1},
                    {"item": "loaf_white", "price": 6, "qty": 24},
                    {"item": "trencher_bread", "price": 2, "qty": -1},
                    {"item": "honey_cake", "price": 11, "qty": 8},
                ]})
    return cy


def _residue(ctx, g, rng, door_x, win_x, cy, zf):
    """Flour, and the queue.

    Art Bible §7: dust settles, it does not stop at an edge. Slot 32 says five
    metres, so the flour goes down in three rings of falling density from the
    counter out onto Bakers' Row, plus the sill, the step and the counter edge.
    The threshold is dished, arced and mudded because every household in
    Hearthmere stands on it every morning.
    """
    for i, (r, dn, cxx, czz) in enumerate(((1.45, 1.0, win_x, zf - 0.85),
                                           (2.60, 0.7, win_x - 0.6, zf - 1.95),
                                           (4.40, 0.4, win_x - 1.4, zf - 3.40),
                                           (1.20, 0.8, door_x, zf - 0.80))):
        # The first ring is on the shop floor. The rest are out on Bakers' Row,
        # and the street is NOT a plane 0.46 m below the plinth — that guess
        # put a 4.4 m ring of flour 0.46 m UNDER the road, where it rendered
        # nothing (validate: "an isolated mass entirely below terrain"). Dust
        # settles on the ground, so it is draped onto the ground: authored at
        # local y = 0 and pushed down onto Bakers' Row by `SITE.drape`, which
        # keeps the 4 mm film 4 mm proud however the row falls under it.
        film = P.dust_film(f"{ASSET}.dust{i}", radius=r, mat="flour",
                           centre=(cxx, czz), y=PLINTH if i == 0 else 0.0,
                           density=dn)
        g.add(film if i == 0 else SITE.drape(film))
    # On the counter edge and the sill — where hands and sacks actually put it.
    for i in range(4):
        hp = M.quad(0.13, 0.10, "flour", uv_scale=MATS.uv_detail("flour", 0.2, why="0.13 m member; the library's 1 m tile shows 13% of one tile here and reads as flat colour"))
        hp.rotate_x(-np.pi * 0.5)
        hp.rotate_z(rng.uniform(-0.6, 0.6))
        hp.translate(win_x + rng.uniform(-1.5, 1.5), cy + 0.036,
                     zf - 0.52 + rng.uniform(-0.20, 0.20))
        g.add(hp)

    th = S.threshold_stone(f"{ASSET}.step", width=1.55, depth=0.74, rise=0.13)
    th.translate(door_x, PLINTH - 0.13, zf - 0.40)
    g.add(th)
    g.add(P.dress_threshold(f"{ASSET}.thr", width=1.55, wall_z=zf - 0.10,
                            ctx=None, mud=True).translate(door_x, PLINTH, 0))
    # The queue's own residue: a bench worn shiny, and a basket left holding a
    # place because that is exactly what people do.
    bn = K.bench(f"{ASSET}.queue", length=1.85)
    bn.rotate_y(0.06)
    bn.translate(win_x - 3.15, PLINTH, zf - 1.25)
    g.add(bn)
    ctx.collider("box", center=SITE.p(win_x - 3.15, PLINTH + 0.22, zf - 1.25),
                 half=(0.95, 0.22, 0.20), rot_y=SITE.yaw(), tag="bench")
    bk = P.basket(f"{ASSET}.place", radius=0.20, height=0.26, weave="stake")
    bk.rotate_y(rng.uniform(-3, 3))
    bk.translate(win_x - 2.60, PLINTH + 0.44, zf - 1.22)
    g.add(bk)
    # Trodden earth, not grass: the queue has worn this stretch of Bakers' Row
    # down to bare ground, and `grass_worn` put a bright green tongue across a
    # dry street.
    g.add(P.worn_patch(f"{ASSET}.queuepath", shape="path", size=3.2,
                       mat="dirt")
          .rotate_y(0.25).translate(win_x - 1.6, 0.012, zf - 1.85))

    # A water butt under the shop eaves — a bakehouse keeps water close.
    g.add(P.water_butt(f"{ASSET}.butt", wall_z=zf - 0.05, x=-W * 0.5 + 0.75)
          .translate(0, PLINTH, 0))
    ctx.collider("cylinder", center=SITE.p(-W * 0.5 + 0.75, PLINTH + 0.52, zf - 0.50),
                 radius=0.40, height=1.05, tag="water_butt")

    # And the sign: a pictorial board, a wheatsheaf, on a plain iron bracket.
    br = K.sign_bracket(f"{ASSET}.bracket", reach=0.88, mat="iron")
    br.translate(door_x - 1.05, PLINTH + 3.05, zf - 0.10)
    g.add(br)
    # A carved wheatsheaf on a painted ground. It has to READ at 20 m down
    # Bakers' Row, so it is modelled solid on a board rather than built from
    # thirteen 14 mm straws that resolve to nothing past three metres.
    sheaf = M.Group()
    sheaf.add(M.chamfered_prism([(-0.40, -0.34), (0.40, -0.34), (0.40, 0.40),
                                 (0.0, 0.54), (-0.40, 0.40)], 0.05,
                                "painted_amber", 0.010, uv_scale=MATS.uv_detail("painted_amber", 0.769, why="0.05 m member; the library's 2 m tile shows 2% of one tile here and reads as flat colour")))
    for i in range(11):
        a = (i / 10.0 - 0.5) * 1.9
        st = M.lathe([(0.030, 0.0), (0.020, 0.62), (0.034, 0.68),
                      (0.0, 0.78)], 6, "straw")
        st.rotate_z(a * 0.42)
        st.translate(math.sin(a) * 0.20, -0.34, -0.055)
        sheaf.add(st)
    sheaf.add(M.ring(0.13, 0.024, "canvas", 10).rotate_x(np.pi * 0.5)
              .translate(0, -0.02, -0.055))
    sheaf.rotate_y(rng.uniform(-0.08, 0.08))
    sheaf.translate(door_x - 1.05 + 0.64, PLINTH + 2.55, zf - 0.10)
    g.add(sheaf)
    SITE.entity(f"{ASSET}.sign.01", "prop.sign",
                (door_x - 0.41, PLINTH + 2.55, zf - 0.10), verbs=["inspect"])


def build(ctx: VenueContext, asset_id=ASSET):
    SITE.bind(ctx)
    rng = rng_for(asset_id, "bakery")
    g = M.Group()

    door_x, win_x, win_w, win_h, sill, zf, roof = _shop(ctx, g, rng)
    _oven_house(ctx, g, rng)
    hearth = _oven(ctx, g, rng)
    _working_line(ctx, g, rng, hearth)
    cy = _counter(ctx, g, rng, door_x, win_x, win_w, win_h, sill, zf)
    _residue(ctx, g, rng, door_x, win_x, cy, zf)

    fr = K.door_frame(width=1.06, height=2.12, mat="oak_dark", depth=0.30)
    fr.translate(door_x, FLOOR, zf - 0.10)
    g.add(fr)
    dr = K.plank_door(f"{ASSET}.door", width=1.02, height=2.08,
                      mat="oak_weathered", open_angle=1.05)
    dr.translate(door_x, FLOOR, zf - 0.20)
    g.add(dr)
    SITE.entity(f"{ASSET}.door.01", "door.bakery",
                (door_x, FLOOR, zf - 0.22), verbs=["enter"])

    SITE.emit(g, container="bakery")

    print(SITE.report())
    print(f"      shop eaves {EAVES:.2f}  oven hearth {hearth:.2f}  "
          f"flue {FLUE_TOP:.2f}  counter {SITE.origin_y:+.2f}+{FLOOR + 1.02:.2f}")
