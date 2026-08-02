"""Bathhouse — slot 91. Fed by the town's water, and the best ambient in it.

Slot 91: *"on the conduit and next to its own spring. Furnace and a 9.0 m flue
at the west end; steam out of the roof louvres on a cold morning is one of the
town's best ambient reads."*

A bathhouse is a **furnace with rooms attached**, and the plan reads as that
from outside: a long low range, a stone stoke-house at the west end with the
flue over it, and a timber ridge louvre running most of the length to let the
steam out. Everything about it is horizontal — it is the lowest, longest mass
on Well Lane — and the flue is the only vertical, which is exactly the contrast
that makes a low building read.

## What makes it read as WET, which is the whole job

Every other venue in Hearthmere is dry. This one has to be visibly, obviously
wet at 09:30 in high summer, or it is just a shed:

  - **the flagstones outside the door are dark and never dry**, and the wet
    runs from the door to the gully in a tongue, not a circle
  - **towels on lines**, sagging, in the yard on the sunny side — the one
    laundry line in town that is a business rather than a household
  - **the tail-water leaves the building** through a stone spout in the east
    gable into an open channel, steaming, and runs off down the lane
  - **pattens** — wooden overshoes — kicked off in a row at the threshold,
    because you do not walk into a bathhouse in your street boots
  - the **firewood** is stacked to the eaves along the whole west end, because
    a furnace that has to hold a hot room all day eats a cord a week

## Function, arranged by workflow

Cold in at the east (the conduit and the cistern) -> the furnace at the west
-> the hot room over the flue -> the cooling room -> the towels -> out. So the
building is read west-to-east as fire, heat, water, cloth, and the objects go
in that order along the frontage.
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

NAME = "bathhouse"
ASSET = "hm.slot.91.bathhouse"

SITE = SI.Site(NAME)
CELLS = SITE.cells

W, D = SITE.w, SITE.d              # 14.0 x 11.0
EAVES = SITE.eaves                 # 5.60
PLINTH = 0.42
PITCH = 0.55                       # low: slot 91 asks for a low roof
FLUE_TOP = 9.00                    # slot note

FLOOR = PLINTH
STOKE_W = 3.60                     # the stone stoke-house at the west end
STOKE_X = -W * 0.5 + STOKE_W * 0.5


def _shell(ctx, g, rng):
    """A long low range: stone at the fire end, timber for the rest."""
    poly = SI.rect(0.0, 0.0, W + 0.30, D + 0.30)
    plinth, y0 = SI.plinth_under(SITE, poly, PLINTH, mat="rubble", chamfer=0.03)
    g.add(plinth)
    ctx.collider("box", center=SITE.p(0, (y0 + PLINTH) * 0.5, 0),
                 half=((W + 0.30) * 0.5, max((PLINTH - y0) * 0.5, 0.05),
                       (D + 0.30) * 0.5),
                 rot_y=SITE.yaw(), kind="surface", tag="plinth")

    zf = -D * 0.5
    door_x = -W * 0.5 + 6.40
    wall_h = EAVES - 0.55

    # The stoke-house: stone, and it runs the full depth of the west end.
    for (a0, a1, b0, b1) in (
            (-W * 0.5, -W * 0.5 + 0.42, zf, -zf),
            (-W * 0.5, STOKE_X + STOKE_W * 0.5, zf, zf + 0.42),
            (-W * 0.5, STOKE_X + STOKE_W * 0.5, -zf - 0.42, -zf),
            (STOKE_X + STOKE_W * 0.5 - 0.42, STOKE_X + STOKE_W * 0.5, zf, -zf)):
        g.add(SI.slab([(a0, b0), (a1, b0), (a1, b1), (a0, b1)],
                      PLINTH, PLINTH + wall_h, "rubble", 0.035))
    # Stoke-hole: a low segmental arch onto the yard, sooted black round it.
    sh_z = zf - 0.02
    ar = K.arch_ring(f"{ASSET}.stokehole", span=1.30, rise=0.42, ring=0.24,
                     depth=0.60, mat="brick")
    ar.translate(STOKE_X, PLINTH + 0.95, sh_z)
    g.add(ar)
    void = M.box(1.26, 1.30, 0.42, 0.01, "timber_charred")
    void.translate(STOKE_X, PLINTH + 0.62, sh_z + 0.35)
    g.add(void)
    for i in range(9):
        em = M.globe(rng.uniform(0.05, 0.10), "coal", 6, 3, sy=0.5)
        em.translate(STOKE_X + rng.uniform(-0.45, 0.45), PLINTH + 0.06,
                     sh_z + 0.30 + rng.uniform(-0.14, 0.14))
        g.add(em)
    g.add(M.quad(1.10, 0.55, "coal").rotate_x(-np.pi * 0.5)
          .translate(STOKE_X, PLINTH + 0.03, sh_z + 0.30))
    SITE.entity(f"{ASSET}.furnace.01", "prop.furnace",
                (STOKE_X, PLINTH + 0.40, sh_z - 0.10), verbs=["inspect"],
                light={"color": "#FF7C33", "intensity": 3.0, "range": 8.0})
    g.add(P.dust_film(f"{ASSET}.soot", radius=1.35, mat="cinder",
                      centre=(STOKE_X, zf - 0.85), y=0.0, density=1.0))

    # The timber range: everything east of the stoke-house.
    tx0 = STOKE_X + STOKE_W * 0.5
    tw = W * 0.5 - tx0
    wins = [(-1.35, 0.72, 0.62), (1.55, 0.66, 0.58), (4.35, 0.80, 0.66)]
    front = K.timber_frame_wall(
        tw, wall_h, f"{ASSET}.f", style="close", sill_y=PLINTH,
        openings=[(door_x - (tx0 + tw * 0.5), K.DOOR_H * 0.5 + 0.05,
                   K.DOOR_W + 0.40, K.DOOR_H + 0.28)] +
                 [(x - (tx0 + tw * 0.5), 2.15, w + 0.16, h + 0.14)
                  for x, w, h in wins])
    front.translate(tx0 + tw * 0.5, 0, zf)
    g.add(front)
    back = K.timber_frame_wall(tw, wall_h, f"{ASSET}.b", style="square",
                               sill_y=PLINTH,
                               openings=[(0.0, 2.15, 0.90, 0.72)])
    back.rotate_y(np.pi)
    back.translate(tx0 + tw * 0.5, 0, -zf)
    g.add(back)
    east = K.timber_frame_wall(D, wall_h, f"{ASSET}.e", style="square",
                               sill_y=PLINTH)
    east.rotate_y(np.pi * 0.5)
    east.translate(W * 0.5, 0, 0)
    g.add(east)
    for i, (x, ww, wh) in enumerate(wins):
        # Small, high and SHUTTERED — a bath house does not want to be looked
        # into, and small high lights are also how you keep the heat.
        w = K.leaded_window(f"{ASSET}.w{i}", width=ww, height=wh,
                            mat="glass_lit", shutters=i != 1,
                            shutter_mat="oak_weathered")
        w.translate(x, PLINTH + 2.15, zf - 0.07)
        g.add(w)

    sh = M.box(W - 0.7, wall_h - 0.2, D - 0.7, 0.02, "timber_charred")
    sh.scale(-1.0, 1.0, 1.0)
    sh.translate(0, PLINTH + (wall_h - 0.2) * 0.5, 0)
    SITE.emit(sh, shell=True)

    SITE.collider_walls(W, D, wall_h, y=PLINTH, thickness=0.34,
                        doors=[("-z", door_x, K.DOOR_W + 0.46)], tag="bathhouse")
    SITE.collider_steps((door_x, 0.0, zf - 0.16), PLINTH, tread=0.50,
                        width=1.40)
    return door_x, zf, wall_h


def _roof_and_louvre(ctx, g, rng, wall_h):
    """A low tiled roof with a long timber louvre along the ridge.

    The louvre is the whole reason the building has a silhouette. It is 8 m of
    boarded lantern with a little roof of its own, sitting astride the ridge,
    and it is where the steam goes.
    """
    poly = SI.rect(0.0, 0.0, W + 0.30, D + 0.30)
    plate = R.wall_plate(poly, PLINTH + wall_h,
                         edges=["eaves", "gable", "eaves", "gable"],
                         thickness=0.32, wall_mat="plaster")
    roof = R.roof_from_plate(plate, "half_hip", PITCH, 0.55, f"{ASSET}.roof",
                             mat="terracotta", timber_mat="oak_dark",
                             ridge_axis="u")
    g.add(roof)
    ridge_y = roof.ridge_y

    lv_x0, lv_x1 = -W * 0.5 + 2.6, W * 0.5 - 2.2
    lw, lh = 1.05, 0.95
    base = ridge_y - 0.30
    for sz in (-1, 1):
        pl = M.box(lv_x1 - lv_x0, 0.14, 0.13, 0.010, "oak_dark")
        pl.translate((lv_x0 + lv_x1) * 0.5, base + 0.07, sz * lw * 0.5)
        g.add(pl)
    n = int((lv_x1 - lv_x0) / 0.78)
    for k in range(n + 1):
        px = lv_x0 + k * (lv_x1 - lv_x0) / n
        for sz in (-1, 1):
            po = M.box(0.11, lh, 0.11, 0.008, "oak")
            po.translate(px, base + lh * 0.5, sz * lw * 0.5)
            g.add(po)
    for k in range(5):                        # the louvre boards themselves
        y = base + 0.16 + k * (lh - 0.28) / 4.0
        for sz in (-1, 1):
            lb = M.box(lv_x1 - lv_x0 - 0.06, 0.15, 0.045, 0.005,
                       "oak_weathered")
            lb.rotate_x(sz * 0.55)
            lb.translate((lv_x0 + lv_x1) * 0.5, y, sz * lw * 0.5)
            g.add(lb)
    # Its own little roof, on its own little plate — same rule as the big one.
    lpoly = SI.rect((lv_x0 + lv_x1) * 0.5, 0.0, lv_x1 - lv_x0 + 0.34, lw + 0.42)
    lplate = R.wall_plate(lpoly, base + lh,
                          edges=["eaves", "gable", "eaves", "gable"],
                          thickness=0.12, wall_mat="oak")
    lroof = R.roof_from_plate(lplate, "gable", 0.80, 0.22, f"{ASSET}.louvreroof",
                              mat="lead", timber_mat="oak_dark", ridge_axis="u")
    g.add(lroof)
    for sx in (-1, 1):
        ge = K.gable_end(lw + 0.42, base + lh, 0.80, mat="oak_weathered",
                         depth=0.10)
        ge.rotate_y(np.pi * 0.5)
        ge.translate((lv_x0 + lv_x1) * 0.5 + sx * (lv_x1 - lv_x0 + 0.34) * 0.5,
                     0, 0)
        g.add(ge)

    # THE STEAM. Geometry cannot do this well and should not try; the client
    # renders it from the entity, exactly as the pub's chimney smoke is done.
    # Three vents along the louvre so the plume has length, not a single puff.
    for k, f in enumerate((0.22, 0.52, 0.80)):
        px = lv_x0 + (lv_x1 - lv_x0) * f
        SITE.entity(f"{ASSET}.steam.{k + 1:02d}", "prop.vent",
                    (px, base + lh + 0.30, 0.0),
                    steam={"rate": 0.55, "drift": [0.75, 0.55, 0.40],
                           "spread": 1.4, "life": 3.2})
    return ridge_y


def _flue(ctx, g, rng):
    """The 9 m stack over the furnace: the only vertical this building has."""
    # Clasping the WEST GABLE, outside the roof. Inside the plan its 9.00 m
    # stood under a 9.54 m ridge and was invisible from every direction — a
    # landmark the roof ate. On the gable it stands clear for its whole height,
    # and an external stack is where a fire-conscious town would want it.
    # At the FRONT-WEST corner, outside the eaves and directly over the
    # stoke-hole, which is where a flue actually rises from. Set at mid-depth
    # it stood 0.37 m clear of the eaves line but six metres further back, so
    # from the lane it projected onto the roof and vanished — a 9 m landmark
    # the building ate. Here its whole shaft is against the sky.
    fx, fz = -W * 0.5 - 0.66, -D * 0.5 + 1.15
    stages = ((PLINTH, 4.0, 1.14), (4.0, FLUE_TOP - 0.50, 0.94))
    for i, (a, b, s) in enumerate(stages):
        st = M.box(s, b - a, s * 0.9, 0.03, "rubble")
        st.translate(fx, (a + b) * 0.5, fz)
        g.add(st)
        if i:
            off = M.box(s + 0.20, 0.15, s * 0.9 + 0.20, 0.025, "ashlar")
            off.translate(fx, a + 0.075, fz)
            g.add(off)
    for k, (dy, ds) in enumerate(((0.0, 0.94), (0.16, 1.12))):
        c = M.box(ds, 0.17, ds * 0.9, 0.025, "ashlar")
        c.translate(fx, FLUE_TOP - 0.50 + dy + 0.085, fz)
        g.add(c)
    pot = M.lathe([(0.18, 0.0), (0.20, 0.07), (0.185, 0.38), (0.21, 0.45)], 12,
                  "terracotta", close_top=False)
    pot.translate(fx, FLUE_TOP - 0.14, fz)
    g.add(pot)
    SITE.entity(f"{ASSET}.flue.01", "prop.chimney",
                (fx, FLUE_TOP, fz), smoke={"rate": 1.6, "drift": [0.9, 0, 0.5]})
    ctx.collider("box", center=SITE.p(fx, PLINTH + 1.9, fz),
                 half=(0.60, 1.9, 0.55), rot_y=SITE.yaw(), tag="flue")


def _yard(ctx, g, rng, door_x, zf):
    """Firewood, towels, the tail-water, and the wet that never dries."""
    # --- the wood, along the whole west end -------------------------------
    # TWO stacks, at the fire end only, and 1.35 m rather than 1.70 m. Three
    # at 1.70 m ran from the stoke-house to the door and walled off the
    # threshold, the wet flags and both low windows — the whole of the frontage
    # this venue has to be read by.
    for k in range(2):
        wd = P.firewood_stack(f"{ASSET}.wood{k}", length=2.30, height=1.35,
                              depth=0.50, wall_z=zf - 0.10)
        wd.translate(-W * 0.5 + 1.30 + k * 2.45, 0.0, 0.0)
        g.add(wd)
        ctx.collider("box",
                     center=SITE.p(-W * 0.5 + 1.30 + k * 2.45, 0.68, zf - 0.35),
                     half=(1.18, 0.68, 0.27), rot_y=SITE.yaw(), tag="woodpile")
    g.add(P.kindling(f"{ASSET}.kindling", radius=0.42)
          .translate(-W * 0.5 + 6.2, 0.0, zf - 0.95))
    g.add(P.chopping_block(f"{ASSET}.block", height=0.48, radius=0.30, axe=True)
          .translate(-W * 0.5 + 1.15, 0.0, zf - 1.65))
    ctx.collider("cylinder", center=SITE.p(-W * 0.5 + 1.15, 0.24, zf - 1.65),
                 radius=0.32, height=0.48, tag="chopping_block")

    # --- towels on lines, on the sunny side -------------------------------
    # Two props and three runs. A washing line tied to nothing is the worst
    # floating prop there is, so both ends are on something that reaches the
    # ground: one prop, and the building itself.
    px, pz = W * 0.5 + 1.15, zf - 2.35
    prop = S.laundry_prop(f"{ASSET}.prop", height=3.20)
    prop.translate(px, 0.0, pz)
    g.add(prop)
    ctx.collider("cylinder", center=SITE.p(px, 1.60, pz), radius=0.10,
                 height=3.20, tag="laundry_prop")
    for k, (ax, ay, az) in enumerate(((W * 0.5 - 1.2, 2.55, zf - 0.15),
                                      (W * 0.5 - 4.6, 2.62, zf - 0.15),
                                      (W * 0.5 - 0.4, 2.30, 1.10))):
        g.add(P.laundry_line(f"{ASSET}.line{k}", (ax, ay, az),
                             (px, 3.05 - k * 0.10, pz), sag=0.26,
                             items=4 if k < 2 else 3, mat="linen"))
    # A basket of dry ones taken in, and one dropped.
    g.add(P.basket(f"{ASSET}.linen", radius=0.28, height=0.34, weave="spale")
          .translate(W * 0.5 - 0.35, 0.0, zf - 1.45))
    tw = M.sheet(0.55, 0.80, lambda u, v: -0.05 * math.sin(u * 4.0),
                 nx=5, nz=4, mat="linen", plane="xz")
    tw.rotate_y(0.7)
    tw.translate(W * 0.5 - 1.05, 0.02, zf - 1.95)
    g.add(tw)

    # --- the tail-water, out of the east gable and away down the lane -----
    sx = W * 0.5 + 0.02
    spout = M.chamfered_prism([(0.0, -0.16), (0.52, -0.13), (0.52, 0.13),
                               (0.0, 0.16)], 0.22, "stone", 0.012, uv_scale=MATS.uv_detail("stone", 0.833, why="0.22 m member; the library's 2 m tile shows 11% of one tile here and reads as flat colour"))
    spout.rotate_y(np.pi * 0.5)
    spout.rotate_z(-0.10)
    spout.translate(sx + 0.26, PLINTH + 0.52, 1.85)
    g.add(spout)
    for k in range(7):                        # the open channel it falls into
        cs = M.chamfered_prism([(-0.34, -0.30), (0.34, -0.30), (0.30, 0.0),
                                (-0.30, 0.0)], 0.62, "stone", 0.02)
        cs.rotate_x(np.pi * 0.5)
        cs.rotate_y(np.pi * 0.5)
        cs.translate(sx + 0.70 + k * 0.60, PLINTH - 0.24,
                     1.85 + k * 0.12 + rng.uniform(-0.03, 0.03))
        g.add(cs)
    wat = M.box(4.30, 0.03, 0.42, 0.004, "water_flow")
    wat.rotate_y(0.20)
    wat.translate(sx + 2.45, PLINTH - 0.20, 2.25)
    g.add(wat)
    SITE.entity(f"{ASSET}.tailrace.01", "prop.vent",
                (sx + 0.55, PLINTH + 0.30, 1.95),
                steam={"rate": 0.35, "drift": [0.6, 0.5, 0.3], "spread": 0.9})
    for i in range(5):
        g.add(V.reed_tuft(f"{ASSET}.reed{i}", height=0.55, blades=7)
              .translate(sx + 1.2 + i * 0.85, PLINTH - 0.22,
                         2.35 + rng.uniform(-0.25, 0.25)))

    # --- the wet, and the pattens ----------------------------------------
    for i, (r, dn, cx, cz) in enumerate(((1.15, 1.0, door_x, zf - 0.85),
                                         (1.95, 0.6, door_x + 0.9, zf - 1.85),
                                         (1.25, 0.8, sx + 1.1, 2.30))):
        g.add(P.dust_film(f"{ASSET}.wet{i}", radius=r, mat="mud_wet",
                          centre=(cx, cz), y=0.0, density=dn))
    g.add(P.dust_film(f"{ASSET}.slime", radius=0.95, mat="algae",
                      centre=(sx + 1.6, 2.60), y=0.0, density=0.7))
    th = S.threshold_stone(f"{ASSET}.step", width=1.50, depth=0.70, rise=0.12)
    th.translate(door_x, PLINTH - 0.12, zf - 0.38)
    g.add(th)
    # Pattens: wooden overshoes kicked off in a row. Nobody walks into a bath
    # house in street boots, and a row of six says how many people are inside.
    for i in range(6):
        pt = M.Group()
        sole = M.chamfered_prism([(-0.055, -0.13), (0.055, -0.13),
                                  (0.048, 0.13), (-0.048, 0.13)], 0.030,
                                 "oak_weathered", 0.005, uv_scale=MATS.uv_detail("oak_weathered", 0.625, why="0.03 m member; the library's 2 m tile shows 2% of one tile here and reads as flat colour"))
        sole.rotate_x(np.pi * 0.5)
        pt.add(sole)
        for sz in (-1, 1):
            bl = M.box(0.095, 0.055, 0.045, 0.004, "oak_dark")
            bl.translate(0, -0.045, sz * 0.085)
            pt.add(bl)
        st = M.box(0.085, 0.012, 0.16, 0.003, "leather")
        st.translate(0, 0.028, 0.0)
        pt.add(st)
        pt.rotate_y(rng.uniform(-0.7, 0.7))
        pt.translate(door_x + 1.05 + (i // 2) * 0.30 + rng.uniform(-0.03, 0.03),
                     PLINTH + 0.06,
                     zf - 0.42 - (i % 2) * 0.28 + rng.uniform(-0.03, 0.03))
        g.add(pt)
    for i in range(6):
        g.add(V.joint_weeds(f"{ASSET}.wd{i}", count=4)
              .translate(rng.uniform(-W * 0.4, W * 0.4), 0.01,
                         zf - rng.uniform(2.4, 4.2)))

    # A bench outside the door for whoever is cooling off, and a pail.
    bn = K.bench(f"{ASSET}.bench", length=2.05)
    bn.rotate_y(0.05)
    bn.translate(door_x + 2.55, 0.0, zf - 1.05)
    g.add(bn)
    ctx.collider("box", center=SITE.p(door_x + 2.55, 0.22, zf - 1.05),
                 half=(1.05, 0.22, 0.20), rot_y=SITE.yaw(), tag="bench")
    g.add(P.bucket(f"{ASSET}.pail", height=0.32, top=0.19, full=True)
          .translate(door_x - 1.15, 0.0, zf - 0.75))
    SITE.entity(f"{ASSET}.bench.01", "prop.bench",
                (door_x + 2.55, 0.45, zf - 1.05), verbs=["sit"])


def build(ctx: VenueContext, asset_id=ASSET):
    SITE.bind(ctx)
    rng = rng_for(asset_id, "bathhouse")
    g = M.Group()

    door_x, zf, wall_h = _shell(ctx, g, rng)
    ridge = _roof_and_louvre(ctx, g, rng, wall_h)
    _flue(ctx, g, rng)
    _yard(ctx, g, rng, door_x, zf)

    fr = K.door_frame(width=1.04, height=2.05, mat="oak_dark", depth=0.32)
    fr.translate(door_x, PLINTH, zf - 0.10)
    g.add(fr)
    dr = K.plank_door(f"{ASSET}.door", width=1.00, height=2.00,
                      mat="oak_weathered", open_angle=0.45)
    dr.translate(door_x, PLINTH, zf - 0.20)
    g.add(dr)
    SITE.entity(f"{ASSET}.door.01", "door.bathhouse",
                (door_x, PLINTH, zf - 0.22), verbs=["enter"])
    # A pictorial sign: a steaming bowl on an iron bracket.
    br = K.sign_bracket(f"{ASSET}.bracket", reach=0.82, mat="iron")
    br.translate(door_x - 1.15, PLINTH + 2.75, zf - 0.10)
    g.add(br)
    bowl = M.lathe([(0.0, 0.0), (0.16, 0.02), (0.26, 0.20), (0.28, 0.24)], 12,
                   "pottery_slip", close_top=False)
    bowl.translate(door_x - 1.15 + 0.60, PLINTH + 2.05, zf - 0.10)
    g.add(bowl)
    for k in range(3):
        wisp = M.lathe([(0.030, 0.0), (0.016, 0.30)], 6, "alabaster")
        wisp.rotate_z(0.22 * (k - 1))
        wisp.translate(door_x - 1.15 + 0.60 + (k - 1) * 0.10,
                       PLINTH + 2.30, zf - 0.10)
        g.add(wisp)
    SITE.entity(f"{ASSET}.sign.01", "prop.sign",
                (door_x - 0.55, PLINTH + 2.20, zf - 0.10), verbs=["inspect"])

    SITE.emit(g, container="bathhouse")

    print(SITE.report())
    print(f"      eaves {PLINTH + wall_h:.2f}  ridge {ridge:.2f}  "
          f"louvre to {ridge + 0.95:.2f}  flue {FLUE_TOP:.2f}")
