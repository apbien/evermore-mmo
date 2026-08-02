"""Blacksmith — slot 43, and the most ACTIVE venue in Hearthmere.

`docs/plan/schedule.md` slot 43:

    ground +1.62 m. BLACKSMITH. Open-fronted work shed (roofed, unwalled, so
    the work is visible from the lane) with the forge, anvil, quench and
    bellows, plus a walled dwelling bay at the west end. Chimney to 11.4 m.
    Platform cut into the slope with a 1.1 m revetment on its north side.
    Highest, driest ground in the town and 30 m from the nearest thatch.

## Why this is a rebuild

The v1 smithy was a 9.5 x 7.5 shed on an 18 x 14 plot — **30 % fill**, the
worst in the town — with no dwelling, no platform, no revetment, and a stack
that stopped 2 m short of the noted 11.4 m. It also used neither siting class,
so it was 19.8 m out at the corners until D-025/D-026.

## The plan

Design frame (`core.siting`): `+X` along the frontage, `-Z` out toward the
lane. For slot 43 (rot 60) design `-X` maps to world north-west, so the slot
note's "west end" is the design `-X` end, and the ground the note says falls
away is the design `-X`/`-Z` corner.

    x[-8.60,-4.00]  z[-5.60, 6.40]   dwelling bay, walled, gable to the lane
    x[-3.30, 8.30]  z[-5.20, 6.40]   work shed, roofed, OPEN to the lane
    x[-3.30, 8.30]  z[-7.00,-5.20]   the cinder apron, where the horses stand

The shed is open on the lane side and half-boarded on the east end. That is
both the correct historical form — a smith works in a through-draught and
needs the light — and far better for gameplay: the player can see the work
without entering, which is what makes a crafting venue read as a crafting
venue from the street.

## Arranged by workflow, not by symmetry

A smith lays a shop out by the reach of his own arms: fire, then the anvil
within a pace of it so the iron does not cool on the way, then the quench
within a pace of the anvil, with the tool rack at the back hand and the
bellows behind the fire where the striker is not standing. The tool rack is
`props.smith_tools`, which hangs tongs in JAW ORDER for the same reason.

## Heat, and the only significant emissive in the town

The forge fire is the strongest light source in Hearthmere and the only real
emissive surface. Everything near it is stained by it: the hood is sooted, the
posts are scorched on the fire side and clean on the other, the floor is
ground black with scale and cinder where the anvil is and only dusty six feet
away. That gradient is the venue — it is what makes the place feel hot.
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

NAME = "blacksmith"
ASSET = "hm.slot.43.blacksmith"

SITE = SI.Site(NAME)
CELLS = SITE.cells

W, D = SITE.w, SITE.d                  # 18.0 x 14.0
EAVES = SITE.eaves                     # 5.40 — slot schedule
PLAT = 0.24                            # the made platform, over the pad

# Dwelling bay, design -X end. Gable to the lane so the roofline steps.
DW_X0, DW_X1 = -8.60, -4.00
DW_Z0, DW_Z1 = -5.60, 6.40
DW_CX, DW_CZ = (DW_X0 + DW_X1) * 0.5, (DW_Z0 + DW_Z1) * 0.5
DW_EAVES = 4.20
DW_PITCH = 1.00

# Work shed.
SH_X0, SH_X1 = -3.30, 8.30
SH_Z0, SH_Z1 = -5.20, 6.40
SH_CX, SH_CZ = (SH_X0 + SH_X1) * 0.5, (SH_Z0 + SH_Z1) * 0.5
SH_W, SH_D = SH_X1 - SH_X0, SH_Z1 - SH_Z0

# The stack. The slot note's 11.4 m is a WORLD height and this venue's origin
# sits at +1.62, so the top of the flue in local coordinates is 9.78. Getting
# that wrong by the origin is how the v1 stack ended up 2 m short of the note.
STACK_TOP = 11.40 - 1.62

# The working triangle. These four numbers are the venue.
FORGE = (-0.20, 4.85)
ANVIL = (1.05, 3.05)
QUENCH = (2.55, 3.95)
BELLOWS = (-2.35, 5.05)


# ---------------------------------------------------------------------------

def _platform(ctx, g, rng):
    """The made platform and the revetment that holds it up.

    Slot note: "Platform cut into the slope with a 1.1 m revetment on its north
    side." Directive §6.1 — the level is taken from the terrain under the
    platform's OWN corners rather than from a constant, so the wall is as tall
    as the ground actually needs and no taller.
    """
    poly = SI.rect(0.0, 0.0, W - 0.4, D - 0.4)
    slab, y0 = SI.plinth_under(SITE, poly, PLAT, mat="rubble", chamfer=0.03)
    g.add(slab)
    ctx.collider("box", center=SITE.p(0, (y0 + PLAT) * 0.5, 0),
                 half=((W - 0.4) * 0.5, max((PLAT - y0) * 0.5, 0.05),
                       (D - 0.4) * 0.5),
                 rot_y=SITE.yaw(), kind="surface", tag="smithy_platform")

    # The revetment proper: a battered rubble wall wherever the ground outside
    # the platform is more than 0.3 m below it, which on this slot is the
    # design -X and -Z edges — the world north-west and north-east faces.
    made = 0
    for (ex, ez, run, along_x) in (
            (-W * 0.5 + 0.2, 0.0, D - 0.4, False),
            (0.0, -D * 0.5 + 0.2, W - 0.4, True)):
        n = 7
        for i in range(n):
            t = -run * 0.5 + (i + 0.5) * run / n
            px = ex + (t if along_x else 0.0)
            pz = ez + (0.0 if along_x else t)
            out_x = px + (0.0 if along_x else -0.9)
            out_z = pz + (-0.9 if along_x else 0.0)
            drop = PLAT - SITE.ground(out_x, out_z)
            if drop < 0.30:
                continue
            made += 1
            h = min(drop + 0.22, 1.60)
            seg = M.chamfered_prism(
                [(-run / n * 0.52, PLAT - h), (run / n * 0.52, PLAT - h),
                 (run / n * 0.52, PLAT + 0.12), (-run / n * 0.52, PLAT + 0.12)],
                0.55, "rubble", 0.028)
            if not along_x:
                seg.rotate_y(np.pi * 0.5)
            seg.translate(px + (0.0 if along_x else -0.20),
                          0.0, pz + (-0.20 if along_x else 0.0))
            g.add(seg)
            # Coping: the flat stones a smith's yard gets its edge from, and
            # the line that makes a retaining wall read as built.
            cap = M.box(run / n * 1.04 if along_x else 0.72, 0.12,
                        0.72 if along_x else run / n * 1.04, 0.02, "stone")
            cap.translate(px + (0.0 if along_x else -0.20), PLAT + 0.16,
                          pz + (-0.20 if along_x else 0.0))
            g.add(cap)

    # The floor of the shed and the apron in front of it: beaten earth with
    # scale and cinder trodden into it. NOT cobbled — this is a working yard,
    # and the ground is the first thing that says so.
    g.add(SI.slab(SI.rect(SH_CX, SH_CZ - 0.9, SH_W + 0.8, SH_D + 2.6),
                  PLAT - 0.03, PLAT + 0.025, "dirt", 0.010))
    g.add(SI.slab(SI.rect(SH_CX, SH_Z0 - 1.15, SH_W + 0.4, 1.9),
                  PLAT - 0.02, PLAT + 0.032, "cinder", 0.010))
    return made


def _dwelling(ctx, g, rng):
    """The smith's own house at the west end: stone below, framed above.

    Walled, unlike the shed, and roofed in tile — "30 m from the nearest
    thatch" is a fire rule and this building is the reason for it. Its gable
    faces the lane, which steps the roofline down from the shed's eaves and
    gives the venue a second, lower mass.
    """
    w, d = DW_X1 - DW_X0, DW_Z1 - DW_Z0
    y0 = PLAT

    # Stone ground storey. A smith builds his own house out of what will not
    # burn, and he is the one man in town who can afford the mason.
    for (a0, a1, b0, b1) in ((DW_X0, DW_X1, DW_Z0, DW_Z0 + 0.40),
                             (DW_X0, DW_X1, DW_Z1 - 0.40, DW_Z1),
                             (DW_X0, DW_X0 + 0.40, DW_Z0, DW_Z1),
                             (DW_X1 - 0.40, DW_X1, DW_Z0, DW_Z1)):
        g.add(SI.slab([(a0, b0), (a1, b0), (a1, b1), (a0, b1)], y0, y0 + 2.45,
                      "rubble", 0.03))
    # Quoins on the two free angles.
    for (qx, qz) in ((DW_X0, DW_Z0), (DW_X0, DW_Z1)):
        for i in range(6):
            q = M.box(0.46 if i % 2 else 0.30, 0.32, 0.30 if i % 2 else 0.46,
                      0.02, "ashlar")
            q.translate(qx + 0.16, y0 + 0.20 + i * 0.38, qz + (0.16 if qz < 0 else -0.16))
            g.add(q)

    # Framed upper storey on a stone sill, with a jetty on the lane gable.
    up_h = DW_EAVES - 2.45
    front = K.timber_frame_wall(w, up_h, f"{ASSET}.dwf", style="square",
                                sill_y=0, openings=[(0.0, 1.05, 1.15, 1.15)])
    front.translate(DW_CX, y0 + 2.45, DW_Z0)
    g.add(front)
    back = K.timber_frame_wall(w, up_h, f"{ASSET}.dwb", style="square",
                               sill_y=0, openings=[(0.0, 1.05, 1.00, 1.05)])
    back.rotate_y(np.pi)
    back.translate(DW_CX, y0 + 2.45, DW_Z1)
    g.add(back)
    for sx in (-1, 1):
        sd = K.timber_frame_wall(d, up_h, f"{ASSET}.dws{sx}", style="square",
                                 sill_y=0,
                                 openings=[(z, 1.05, 1.00, 1.05)
                                           for z in (-2.4, 3.0)])
        sd.rotate_y(sx * np.pi * 0.5)
        sd.translate(DW_CX + sx * w * 0.5, y0 + 2.45, DW_CZ)
        g.add(sd)

    # Door and ground lights on the lane gable, so the house has a face.
    dz = DW_Z0 - 0.02
    g.add(K.door_frame(width=1.10, height=2.05, mat="stone", depth=0.36)
          .translate(DW_CX - 1.05, y0, dz))
    dr = K.plank_door(f"{ASSET}.dwdoor", width=1.06, height=2.00,
                      mat="oak_weathered", open_angle=rng.uniform(0.0, 0.35))
    dr.translate(DW_CX - 1.05, y0, dz - 0.05)
    g.add(dr)
    SITE.entity(f"{ASSET}.door.01", "door.blacksmith",
                (DW_CX - 1.05, y0, dz - 0.10), verbs=["enter"])
    for i, (wx, lit) in enumerate(((DW_CX + 1.15, True),)):
        win = K.leaded_window(f"{ASSET}.dwg{i}", width=0.98, height=1.05,
                              mat="glass_lit" if lit else "glass",
                              shutters=True, shutter_mat="painted")
        win.translate(wx, y0 + 1.45, dz - 0.06)
        g.add(win)
    for i, z in enumerate((-2.4, 3.0)):
        for sx in (-1, 1):
            win = K.leaded_window(f"{ASSET}.dwu{sx}{i}", width=0.82,
                                  height=0.88,
                                  mat="glass_lit" if (i + sx) % 3 == 0 else "glass",
                                  shutters=False)
            win.rotate_y(sx * np.pi * 0.5)
            win.translate(DW_CX + sx * (w * 0.5 + 0.06), y0 + 2.45 + 1.05, z)
            g.add(win)
    win = K.leaded_window(f"{ASSET}.dwuf", width=0.95, height=1.00,
                          mat="glass_lit", shutters=False)
    win.translate(DW_CX, y0 + 2.45 + 1.05, DW_Z0 - 0.07)
    g.add(win)

    # Roof: gable to the lane, ridge running back into the plot.
    poly = SI.rect(DW_CX, DW_CZ, w, d)
    plate = R.wall_plate(poly, y0 + DW_EAVES,
                         edges=["gable", "eaves", "gable", "eaves"],
                         thickness=0.28, wall_mat="plaster")
    roof = R.roof_from_plate(plate, "gable", DW_PITCH, 0.36, f"{ASSET}.dwroof",
                             mat="terracotta", timber_mat="oak_dark",
                             ridge_axis="v", verge=0.26)
    g.add(roof)
    for sz in (-1, 1):
        ge = K.gable_end(w, y0 + DW_EAVES, DW_PITCH, mat="plaster", depth=0.26)
        if sz > 0:
            ge.rotate_y(np.pi)
        ge.translate(DW_CX, 0, DW_Z0 if sz < 0 else DW_Z1)
        g.add(ge)

    # The house chimney — the smith cooks at home, not in the forge.
    ch_h = roof.ridge_y - (y0 + DW_EAVES) + 1.5
    ch = K.chimney(f"{ASSET}.dwstack", height=ch_h, section=0.72)
    ch.translate(DW_CX, y0 + DW_EAVES - 0.25, DW_Z1 - 1.60)
    g.add(ch)
    SITE.entity(f"{ASSET}.chimney.02", "prop.chimney",
                (DW_CX, y0 + DW_EAVES - 0.25 + ch_h, DW_Z1 - 1.60),
                smoke={"rate": 0.4, "drift": [0.8, 0, 0.5]})

    SITE.collider_walls(w, d, DW_EAVES, y=y0, thickness=0.40,
                        center=(DW_CX, DW_CZ),
                        doors=[("-z", -1.05, 1.25)], tag="dwelling")
    sh = M.box(w - 0.9, DW_EAVES - 0.15, d - 0.9, 0.02, "oak_dark")
    sh.scale(-1.0, 1.0, 1.0)
    sh.translate(DW_CX, y0 + DW_EAVES * 0.5, DW_CZ)
    SITE.emit(sh, shell=True)
    return roof.ridge_y


def _shed(ctx, g, rng):
    """The open-fronted work shed. `kit.open_range` owns the frame.

    It is asked for `walls=("back", "left")` and a half screen on the right, so
    the whole lane elevation stays open — and `open_range` declares its own
    collision, which means the open side really is walkable rather than being
    fenced off by a bounding box. That is the whole reason the venue is this
    shape.
    """
    rng_ = rng
    rng2 = rng_for(ASSET, "shed")
    rn = K.open_range(f"{ASSET}.range", SH_W, SH_D, EAVES,
                      pitch=0.92, overhang=0.52, roof_mat="slate",
                      post_mat="oak_dark", board_mat="oak_weathered",
                      plinth_mat="rubble", walls=("back", "left"),
                      half_boarded=("right",), board_gap=0.035,
                      plinth=0.16, ridge_along=True, plot=None, tag="smithy")
    rn.translate(SH_CX, PLAT, SH_CZ)
    g.add(rn)

    # Collision, in design terms: the back and left boarding are solid, every
    # post is solid, the floor is walkable and NOTHING crosses the open front.
    SITE.collider("box", center=(SH_CX, PLAT + EAVES * 0.5, SH_Z1),
                  half=(SH_W * 0.5 + 0.1, EAVES * 0.5, 0.12), tag="smithy_wall")
    SITE.collider("box", center=(SH_X0, PLAT + EAVES * 0.5, SH_CZ),
                  half=(0.12, EAVES * 0.5, SH_D * 0.5 + 0.1), tag="smithy_wall")
    SITE.collider("box", center=(SH_CX, PLAT + 0.08, SH_CZ),
                  half=(SH_W * 0.5 + 0.2, 0.10, SH_D * 0.5 + 0.2),
                  kind="surface", tag="smithy_floor")
    bays = max(2, int(round(SH_W / 3.2)))
    for i in range(bays + 1):
        px = SH_X0 + i * SH_W / bays
        for pz in (SH_Z0, SH_Z1):
            SITE.collider("box", center=(px, PLAT + EAVES * 0.5, pz),
                          half=(0.19, EAVES * 0.5, 0.19), tag="smithy_post")
            # SCORCH. The posts near the fire are charred on the fire side and
            # clean on the other, which is the cheapest possible statement that
            # this building gets hot.
            d2 = math.hypot(px - FORGE[0], pz - FORGE[1])
            if d2 > 6.0:
                continue
            a = math.atan2(FORGE[1] - pz, FORGE[0] - px)
            sc = M.box(0.20, 1.75 - d2 * 0.10, 0.05, 0.004, "timber_charred")
            sc.rotate_y(-a - np.pi * 0.5)
            sc.translate(px + math.cos(a) * 0.155, PLAT + 1.30,
                         pz + math.sin(a) * 0.155)
            g.add(sc)

    # Lean-to log store on the closed east end, under the roof overhang, so the
    # silhouette gets a third step and the fuel has somewhere to live.
    g.add(S.woodpile(f"{ASSET}.wood", length=2.60, height=1.15, depth=0.62)
          .translate(SH_X1 - 1.60, PLAT, SH_Z1 - 0.95))


def _forge(ctx, g, rng):
    """Stone hearth, live fire, hood, and the flue that reaches 11.40 m."""
    fx, fz = FORGE
    y = PLAT

    # Raised hearth: a smith works standing, so the fire is at waist height.
    base = SI.slab(SI.rect(fx, fz, 2.90, 1.60), y, y + 0.82, "rubble", 0.028)
    g.add(base)
    lip = M.box(3.04, 0.16, 1.74, 0.025, "stone")
    lip.translate(fx, y + 0.86, fz)
    g.add(lip)
    # Fire bed. `coal` carries the emissive channel — the only one in the town.
    rngc = rng_for(f"{ASSET}.coals", "coals")
    for i in range(38):
        a = rngc.uniform(0, 6.283)
        d = rngc.uniform(0.0, 0.58) ** 0.7
        c = M.box(rngc.uniform(0.06, 0.14), rngc.uniform(0.04, 0.10),
                  rngc.uniform(0.06, 0.13), 0.012, "coal")
        c.rotate_y(rngc.uniform(0, 3.14))
        c.translate(fx + math.cos(a) * d * 1.6,
                    y + 0.94 + rngc.uniform(-0.01, 0.04),
                    fz + math.sin(a) * d * 0.85)
        g.add(c)
    # Work in the fire: a bar at welding heat with its cold end sticking out.
    bar = M.box(0.045, 0.045, 1.10, 0.006, "coal")
    bar.rotate_y(0.42)
    bar.translate(fx + 0.35, y + 0.99, fz - 0.35)
    g.add(bar)

    # Hood and flue. The hood is SOOTED, not stone-coloured: everything over a
    # fire is black, and a clean hood is the loudest "nobody has lit this" tell.
    hood = M.chamfered_prism([(-1.55, 0.0), (1.55, 0.0), (0.48, 1.35),
                              (-0.48, 1.35)], 1.75, "timber_charred", 0.022)
    hood.translate(fx, y + 1.62, fz)
    g.add(hood)
    for i in range(3):                        # iron straps carrying the hood
        st = M.box(3.18, 0.08, 0.09, 0.006, "iron_pitted")
        st.translate(fx, y + 1.66 + i * 0.42, fz - 0.88 + i * 0.30)
        g.add(st)

    # The stack, from the hood right through the roof to the noted 11.40 m.
    # The v1 flue stopped inside the shed: a smoke entity was declared with no
    # stack above the roofline for it to leave from, and the forge chimney is
    # this venue's anchor silhouette from across the whole town.
    sh_h = STACK_TOP - (y + 2.97)
    stack = M.box(1.16, sh_h, 1.16, 0.022, "rubble")
    stack.translate(fx, y + 2.97 + sh_h * 0.5, fz)
    g.add(stack)
    for i in range(3):                        # oversailing courses up the stack
        band = M.box(1.34, 0.16, 1.34, 0.018, "stone")
        band.translate(fx, y + 4.10 + i * 2.10, fz)
        g.add(band)
    cap = M.box(1.52, 0.22, 1.52, 0.020, "stone")
    cap.translate(fx, STACK_TOP - 0.11, fz)
    g.add(cap)
    for sx in (-1, 1):                        # a louvred cowl, so it draws
        for sz in (-1, 1):
            po = M.box(0.14, 0.62, 0.14, 0.010, "iron_pitted")
            po.translate(fx + sx * 0.58, STACK_TOP + 0.31, fz + sz * 0.58)
            g.add(po)
    cwl = M.lathe([(1.15, 0.0), (0.95, 0.16), (0.0, 0.72)], 4, "iron_pitted")
    cwl.rotate_y(np.pi * 0.25)
    cwl.translate(fx, STACK_TOP + 0.62, fz)
    g.add(cwl)

    SITE.entity(f"{ASSET}.forge.01", "crafting_station.forge",
                (fx, y + 0.95, fz - 0.9), verbs=["use"],
                crafting_station={"profession": "blacksmith", "tier": 1},
                light={"color": "#FF8C42", "intensity": 5.0, "range": 13.0,
                       "flickerHz": [8, 12]})
    SITE.entity(f"{ASSET}.chimney.01", "prop.chimney",
                (fx, STACK_TOP + 0.2, fz),
                smoke={"rate": 1.1, "drift": [0.8, 0, 0.5]})
    SITE.collider("box", center=(fx, y + 0.45, fz), half=(1.52, 0.45, 0.87),
                  tag="forge")
    SITE.collider("box", center=(fx, y + 2.5, fz), half=(0.62, 2.0, 0.62),
                  tag="forge_stack")


def _bellows(g):
    """Great bellows — the thing that makes a forge a forge."""
    out = M.Group()
    for i, dy in enumerate((0.0, 0.30)):
        board = M.chamfered_prism([(-0.58, 0), (0.34, -0.29), (0.58, 0),
                                   (0.34, 0.29)], 0.055, "oak_dark", 0.008)
        board.rotate_x(np.pi * 0.5)
        board.translate(0, 1.12 + dy, 0)
        out.add(board)
    for i in range(6):
        t = i / 5.0
        pl = M.lathe([(0.32 + t * 0.15, 0), (0.36 + t * 0.17, 0.055)], 12,
                     "leather", close_bottom=False, close_top=False)
        pl.scale(1.55, 1.0, 0.88)
        pl.translate(0.06, 1.16 + i * 0.055, 0)
        out.add(pl)
    handle = M.cylinder(0.038, 1.25, 7, 0.005, "oak_weathered")
    handle.rotate_z(np.pi * 0.5)
    handle.rotate_y(0.22)
    handle.translate(0.68, 1.52, 0)
    out.add(handle)
    nozzle = M.cylinder(0.055, 0.85, 8, 0.005, "iron_pitted")
    nozzle.rotate_z(-np.pi * 0.5)
    nozzle.translate(-0.72, 1.22, 0)
    out.add(nozzle)
    # Chain hanging off the lever: the bellows are worked from the fire side.
    out.add(K.forged_chain(f"{ASSET}.bellchain", (0.68, 1.52, 0.0),
                           (0.72, 0.85, -0.10), sag=0.06, link=0.055,
                           mat="iron_pitted"))
    return out


def _anvil(g, rng):
    """Anvil on an oak stump. Working face at ~0.76 m — knuckle height."""
    out = M.Group()
    stump = M.lathe([(0.34, 0), (0.31, 0.10), (0.325, 0.48), (0.30, 0.56)], 14,
                    "endgrain")
    out.add(stump)
    # The silhouette: horn, waist, body, heel. Instantly readable, and it does
    # more for the venue than any texture on it could.
    body = M.box(0.68, 0.17, 0.22, 0.012, "steel_blued")
    body.translate(0, 0.72, 0)
    out.add(body)
    waist = M.box(0.32, 0.11, 0.16, 0.010, "iron")
    waist.translate(0, 0.615, 0)
    out.add(waist)
    foot = M.box(0.50, 0.075, 0.26, 0.010, "iron")
    foot.translate(0, 0.57, 0)
    out.add(foot)
    horn = M.lathe([(0.10, 0), (0.078, 0.11), (0.042, 0.24), (0.0, 0.30)], 10,
                   "steel_blued")
    horn.rotate_z(np.pi * 0.5)
    horn.translate(0.34, 0.72, 0)
    out.add(horn)
    # A hardy in the hardy hole, and the hammer left lying on the face.
    hd = M.chamfered_prism([(-0.035, 0), (0.035, 0), (0.0, 0.17)], 0.05, "iron",
                           0.004)
    hd.translate(-0.22, 0.80, 0)
    out.add(hd)
    hm = M.Group()
    hm.add(M.box(0.10, 0.085, 0.20, 0.008, "steel_blued"))
    hf = M.cylinder(0.019, 0.36, 6, 0.003, "oak_weathered")
    hf.rotate_z(np.pi * 0.5)
    hf.translate(0.26, 0.0, 0)
    hm.add(hf)
    hm.rotate_y(0.62)
    hm.translate(0.05, 0.85, 0.02)
    out.add(hm)
    return out


def _residue(ctx, g, rng):
    """Art Bible §7. What a working day leaves on the floor of a smithy."""
    y = PLAT

    # Scale and cinder ground into the dirt, densest at the anvil and thinning
    # out. This is the gradient that makes the floor read as worked.
    for i in range(40):
        a = rng.uniform(0, 6.283)
        d = rng.uniform(0, 1) ** 0.55 * 4.2
        px, pz = ANVIL[0] + math.cos(a) * d, ANVIL[1] + math.sin(a) * d
        if not (SH_X0 + 0.3 < px < SH_X1 - 0.3 and SH_Z0 - 1.4 < pz < SH_Z1 - 0.3):
            continue
        s = rng.uniform(0.035, 0.085)
        fl = M.box(s, s * rng.uniform(0.10, 0.22), s * rng.uniform(0.7, 1.3),
                   0.004, "cinder" if rng.random() < 0.6 else "iron_pitted")
        fl.rotate_y(rng.uniform(0, 3.14))
        fl.translate(px, y + 0.028, pz)
        g.add(fl)
    g.add(P.worn_patch(f"{ASSET}.anvilworn", shape="cat", size=2.9, mat="cinder")
          .translate(ANVIL[0], y + 0.036, ANVIL[1] - 0.4))
    g.add(P.dust_film(f"{ASSET}.ash", radius=1.9, mat="cinder",
                      centre=(FORGE[0], FORGE[1] - 1.2), y=y + 0.033))

    # Coal heap against the back boarding, with the shovel standing in it.
    for i in range(32):
        a = rng.uniform(0, 6.283)
        d = rng.uniform(0, 1.15) ** 0.6
        c = M.box(rng.uniform(0.08, 0.17), rng.uniform(0.06, 0.12),
                  rng.uniform(0.08, 0.16), 0.014, "coal")
        c.rotate_y(rng.uniform(0, 3.14))
        c.translate(-2.55 + math.cos(a) * d, y + 0.06 + rng.uniform(0, 0.30),
                    SH_Z1 - 1.15 + math.sin(a) * d * 0.65)
        g.add(c)
    sv = M.Group()
    sv.add(M.cylinder(0.024, 1.35, 6, 0.003, "oak_weathered"))
    bl = M.chamfered_prism([(-0.16, 0.0), (0.16, 0.0), (0.13, 0.26),
                            (-0.13, 0.26)], 0.02, "iron_pitted", 0.004)
    bl.translate(0, -0.10, 0)
    sv.add(bl)
    sv.rotate_x(0.30)
    sv.rotate_y(0.8)
    sv.translate(-2.20, y + 0.78, SH_Z1 - 1.55)
    g.add(sv)

    # HORSESHOES IN A PILE, finished stock, and the bar the next job comes from.
    for i in range(8):
        sh = M.lathe([(0.058, 0), (0.078, 0.020)], 10, "iron",
                     close_bottom=False, close_top=False)
        sh.scale(1.0, 1.0, 0.74)
        sh.rotate_y(rng.uniform(0, 3.14))
        sh.rotate_z(rng.uniform(-0.10, 0.10))
        sh.translate(4.35 + rng.uniform(-0.30, 0.30), y + 0.03 + i * 0.021,
                     SH_Z1 - 2.10 + rng.uniform(-0.30, 0.30))
        g.add(sh)
    for i in range(7):
        b = M.cylinder(0.024, rng.uniform(1.7, 2.3), 6, 0.004, "iron_pitted")
        b.rotate_z(rng.uniform(0.13, 0.22))
        b.rotate_y(rng.uniform(0, 3.14))
        b.translate(SH_X1 - 1.05 + rng.uniform(-0.18, 0.18), y,
                    SH_Z1 - 2.60 + rng.uniform(-0.20, 0.20))
        g.add(b)

    # LEATHER APRON ON A HOOK, on the back boarding where he leaves it.
    hk = M.box(0.07, 0.11, 0.05, 0.004, "iron")
    hk.translate(-3.90 + 4.20, y + 1.92, SH_Z1 - 0.12)
    g.add(hk)
    apron = M.sheet(0.62, 0.92,
                    lambda u, v: -0.045 * math.sin(u * 3.1) * (0.3 + v),
                    nx=6, nz=6, plane="xy", mat="leather")
    apron.rotate_y(np.pi)
    apron.translate(0.30, y + 1.40, SH_Z1 - 0.14)
    g.add(apron)
    for sx in (-1, 1):                        # neck strap
        st = M.box(0.035, 0.34, 0.012, 0.003, "leather")
        st.rotate_z(sx * 0.32)
        st.translate(0.30 + sx * 0.13, y + 1.94, SH_Z1 - 0.14)
        g.add(st)

    # GRINDSTONE on its frame, with the trough under it and a treadle.
    gr = M.Group()
    wheel = M.lathe([(0.0, 0), (0.42, 0.0), (0.42, 0.085), (0.0, 0.085)], 20,
                    "stone")
    wheel.rotate_z(np.pi * 0.5)
    gr.add(wheel)
    for sx in (-1, 1):
        leg = M.chamfered_prism([(-0.28, 0), (0.28, 0), (0.06, 0.74),
                                 (-0.06, 0.74)], 0.07, "oak_weathered", 0.008)
        leg.translate(0, -0.74, sx * 0.28)
        gr.add(leg)
    crank = M.cylinder(0.020, 0.26, 6, 0.003, "iron")
    crank.rotate_x(np.pi * 0.5)
    crank.translate(0.0, 0.0, 0.34)
    gr.add(crank)
    gr.translate(5.85, y + 0.74, 1.35)
    g.add(gr)
    tr = M.box(1.05, 0.30, 0.62, 0.02, "oak_weathered")
    tr.translate(5.85, y + 0.15, 1.35)
    g.add(tr)
    g.add(K.water_slab(0.92, 0.50, y=y + 0.26, depth=0.10))
    SITE.collider("cylinder", center=(5.85, y + 0.55, 1.35), radius=0.50,
                  height=1.10, tag="grindstone")
    SITE.entity(f"{ASSET}.grindstone.01", "crafting_station.grindstone",
                (5.85, y + 0.80, 1.35), verbs=["use"],
                crafting_station={"profession": "blacksmith", "tier": 1})

    # The horse waiting to be shod: the hitching ring, the hoof stand and the
    # nail box, on the apron in front. No animal — NPCs are out of scope — but
    # the gear says one was here an hour ago.
    for i, hx in enumerate((-1.20, 1.90)):
        po = S.hitching_post(f"{ASSET}.hitch{i}", height=1.14)
        po.translate(hx, y, SH_Z0 - 1.25)
        g.add(po)
        SITE.collider("cylinder", center=(hx, y + 0.57, SH_Z0 - 1.25),
                      radius=0.13, height=1.14, tag="hitching_post")
    st = M.lathe([(0.20, 0), (0.17, 0.42), (0.24, 0.50)], 10, "oak_weathered")
    st.translate(0.55, y, SH_Z0 - 1.05)
    g.add(st)
    g.add(P.crate(f"{ASSET}.nails", size=0.36, height=0.22, open_top=True)
          .translate(1.15, y, SH_Z0 - 0.75))

    # Somebody's cloak over the trestle, a mug going cold, and the tally the
    # smith keeps of who owes him for what.
    g.add(P.chair(f"{ASSET}.chair", cloak=True).translate(-2.95, y, 1.15))
    g.add(P.mug(f"{ASSET}.mug", full=True).translate(-2.30, y + 0.62, 0.55))
    g.add(P.counting_board(f"{ASSET}.tally").translate(-2.55, y + 0.62, 0.20))
    bench = K.trestle_table(f"{ASSET}.bench", length=1.90, width=0.70)
    bench.rotate_y(0.10)
    bench.translate(-2.45, y, 0.35)
    g.add(bench)
    SITE.collider("box", center=(-2.45, y + 0.38, 0.35), half=(0.95, 0.38, 0.38),
                  rot_y=SITE.yaw(0.10), tag="bench")


def _quench(ctx, g, rng):
    """The quench, with the job still in it. The best story on the plot."""
    qx, qz = QUENCH
    y = PLAT
    q = K.barrel(f"{ASSET}.quench", height=0.92, belly=0.80)
    q.translate(qx, y, qz)
    g.add(q)
    # Scummy water: shallow, so the tint runs warm and the stone shows through.
    g.add(K.water_disc(0.36, y=y + 0.78, depth=0.09, segments=14))
    for i in range(4):                        # scum and scale floating on it
        sc = M.quad(rng.uniform(0.09, 0.17), rng.uniform(0.08, 0.14), "algae")
        sc.rotate_y(rng.uniform(0, 3.14))
        sc.translate(qx + rng.uniform(-0.22, 0.22), y + 0.792,
                     qz + rng.uniform(-0.22, 0.22))
        g.add(sc)
    # THE HALF-FINISHED BLADE, tang out, still in the water.
    blade = M.chamfered_prism([(-0.028, 0.0), (0.028, 0.0), (0.020, 0.62),
                               (0.0, 0.70)], 0.012, "steel_blued", 0.003)
    blade.rotate_x(0.40)
    blade.rotate_y(0.75)
    blade.translate(qx - 0.05, y + 0.62, qz - 0.02)
    g.add(blade)
    tang = M.box(0.020, 0.20, 0.014, 0.002, "iron")
    tang.rotate_x(0.40)
    tang.rotate_y(0.75)
    tang.translate(qx - 0.05, y + 0.55, qz + 0.14)
    g.add(tang)
    SITE.collider("cylinder", center=(qx, y + 0.46, qz), radius=0.44,
                  height=0.92, tag="quench")
    SITE.entity(f"{ASSET}.quench.01", "prop.quench", (qx, y + 0.80, qz),
                verbs=["inspect"])


# ---------------------------------------------------------------------------

def build(ctx: VenueContext, asset_id=ASSET):
    SITE.bind(ctx)
    rng = rng_for(asset_id, "smithy")
    g = M.Group()

    revet = _platform(ctx, g, rng)
    _shed(ctx, g, rng)
    dw_ridge = _dwelling(ctx, g, rng)
    _forge(ctx, g, rng)

    bel = _bellows(g)
    bel.rotate_y(-0.18)
    bel.translate(BELLOWS[0], PLAT, BELLOWS[1])
    g.add(bel)

    an = _anvil(g, rng)
    an.rotate_y(0.58)
    an.translate(ANVIL[0], PLAT, ANVIL[1])
    g.add(an)
    SITE.collider("cylinder", center=(ANVIL[0], PLAT + 0.44, ANVIL[1]),
                  radius=0.36, height=0.88, tag="anvil")
    SITE.entity(f"{ASSET}.anvil.01", "crafting_station.anvil",
                (ANVIL[0], PLAT + 0.78, ANVIL[1]), verbs=["use"],
                crafting_station={"profession": "blacksmith", "tier": 1})

    # The tool rack, on the back boarding at the smith's back hand. `smith_tools`
    # hangs the tongs in JAW ORDER, which is how a smith finds one by feel — the
    # v1 rack graded them by length, which is how a shop display does it.
    tools = P.smith_tools(f"{ASSET}.tools", wall_z=SH_Z1 - 0.16, width=2.30)
    tools.translate(-1.35, PLAT, 0.0)
    g.add(tools)
    SITE.entity(f"{ASSET}.tools.01", "prop.tool_rack",
                (-1.35, PLAT + 1.42, SH_Z1 - 0.30), verbs=["inspect"])

    _quench(ctx, g, rng)
    _residue(ctx, g, rng)

    SITE.emit(g, container="blacksmith")

    print(SITE.report())
    print(f"      shed {SH_W:g}x{SH_D:g} eaves {EAVES:.2f}  stack top "
          f"{STACK_TOP + 1.62:.2f} world  dwelling {DW_X1 - DW_X0:g}x"
          f"{DW_Z1 - DW_Z0:g} ridge {dw_ridge:.2f}  revetment segs {revet}")
