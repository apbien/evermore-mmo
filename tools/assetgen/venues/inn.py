"""The Grey Heron Inn — slot 01, and the warmest thing in Hearthmere.

`docs/areas/hearthmere/plan/schedule.md` slot 01:

    ground -1.05 m. The Grey Heron. Tallest timber structure in town; upper
    floors jettied 0.45 m each. Gable to the square so the sign hangs over the
    paving. Four dormers on the east slope, two chimneys, stable yard behind.

## Why this is a rebuild

The v1 inn was an 11.5 x 9.0 box on what is now a 16 x 14 plot — 46 % fill —
and it used neither siting class, so D-025/D-026 found its principal facade
pointing WEST, away from the market place the building exists to face. Turning
it round was the easy half. This is the other half.

## The plan, and why it is this plan

An inn of this class is not one box. It is a tall street range with a YARD
beside it and the stable off the yard, because horses and carts have to get in
off the street without going through the common room. That arrangement is what
fills the plot honestly, and it gives the building three things a box cannot:

  - a GABLE to the square (slot note), because the range runs back from the
    street rather than along it. That is what the sign hangs from.
  - a second, lower gable on the stable, so the roofline steps.
  - a real void — the yard — so the mass reads as a place rather than a block.

Design frame (`core.siting`): `+X` along the frontage, `-Z` out of the front
door. For slot 01 that puts the front toward world `+X`, which is the market
place 60 m east down Ford Road.

    x[-6.40, 1.00]  z[-5.95, 6.40]   main range, 3 storeys, gable to street
    x[ 2.85, 7.90]  z[-0.60, 6.40]   stable range, 1.5 storeys
    x[ 1.20, 8.00]  z[-7.00,-0.90]   the yard, open to the street

## The jetties

Each upper floor oversails the one below by 0.45 m (slot note). Historically it
bought floor area over the street; visually it is the best silhouette-breaker
available and it throws a deep horizontal shadow that separates the storeys, so
the building never reads as one extruded slab. It oversails the FRONT and the
two SIDES and not the back — a jetty on all four faces would put the top floor
0.9 m outside the plot, and back walls were built plumb anyway because there
was no street behind to gain over.

## The emotional job

"The inn must be the most inviting thing in any frame." That is carried by
three things and they are all cheap: warm light in every window facing the
street, smoke from two chimneys, and a common room that is VISIBLE from the
threshold — hearth, long tables, and somebody's cloak over a chair.
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

NAME = "inn"
ASSET = "hm.slot.01.inn"

SITE = SI.Site(NAME)
CELLS = SITE.cells

W, D = SITE.w, SITE.d                  # 16.0 x 14.0
EAVES = SITE.eaves                     # 10.60 — slot schedule
PLINTH = 0.45
JETTY = 0.45                           # slot note

# Storey heights. 0.45 + 3.60 + 3.30 + 3.25 = 10.60, which is the schedule's
# eaves exactly. They are generous for timber framing and deliberately so: the
# ground floor is a coaching inn's common room, not a cottage parlour, and the
# eaves height is the number the schedule fixes.
G_H, F1_H, F2_H = 3.60, 3.30, 3.25
Y_G = PLINTH
Y_1 = Y_G + G_H                        # 4.05
Y_2 = Y_1 + F1_H                       # 7.35

# Main range, per storey. Widths grow with the jetty; the BACK wall stays put.
G_W, G_X = 7.40, -2.70
F1_W = G_W + JETTY * 2
F2_W = F1_W + JETTY * 1.42             # the top jetty is shorter, as built
BACK_Z = 6.40
G_ZF = -5.95
F1_ZF = G_ZF - JETTY
F2_ZF = F1_ZF - JETTY * 0.80
PITCH = 0.88

# Stable range.
ST_X0, ST_X1 = 2.85, 7.90
ST_Z0, ST_Z1 = -0.60, 6.40
ST_EAVES = 4.40
ST_PITCH = 0.95

# The yard, open to the street between the two ranges.
YD_X0, YD_X1 = 1.20, 8.00
YD_Z0, YD_Z1 = -7.00, -0.90


def _cx(w, x=G_X):
    return (x - w * 0.5, x + w * 0.5)


# ---------------------------------------------------------------------------

def _heron_sign(asset_id):
    """Painted board showing a grey heron, hung from the front gable.

    The bird is built from primitives rather than painted into a texture, so it
    reads in silhouette from across the market place, which is what a shop sign
    is actually for. Art Bible §2: pictorial, never lettered.

    It hangs from a long iron bracket off the JETTY, which is the whole reason
    the slot note wants the gable to the square — the sign then swings out over
    the paving where an arriving player walks under it.
    """
    out = M.Group()
    out.add(K.sign_bracket(asset_id, reach=0.95, mat="iron"))

    board = M.Group()
    b = M.box(1.32, 0.98, 0.055, 0.010, "oak_dark")
    board.add(b)
    for sy in (-1, 1):
        r = M.plank(1.38, 0.06, 0.038, 0.004, "iron")
        r.translate(0, sy * 0.49, 0)
        board.add(r)
    # Weathered paint: the ground is old limewash, worn back to the boards at
    # the bottom edge where the rain runs off it.
    fld = M.box(1.18, 0.84, 0.020, 0.004, "limewash")
    fld.translate(0, 0.03, -0.038)
    board.add(fld)

    # The heron, in relief on the board face. Grey, and standing.
    body = M.lathe([(0.0, 0), (0.10, 0.06), (0.115, 0.20), (0.0, 0.35)], 10,
                   "alabaster")
    body.rotate_x(np.pi * 0.5)
    body.translate(0.03, -0.12, -0.055)
    board.add(body)
    for i in range(6):                       # neck, arched
        t = i / 5.0
        seg = M.cylinder(0.032 - t * 0.012, 0.075, 6, 0.003, "alabaster")
        seg.rotate_z(-0.55 + t * 1.30)
        seg.translate(-0.07 + math.sin(t * 1.5) * 0.14, 0.12 + t * 0.17, -0.055)
        board.add(seg)
    beak = M.lathe([(0.024, 0), (0.005, 0.17)], 6, "painted_amber")
    beak.rotate_z(-1.45)
    beak.translate(0.17, 0.34, -0.055)
    board.add(beak)
    for i in range(2):                       # legs
        leg = M.cylinder(0.014, 0.24, 5, 0.002, "painted_amber")
        leg.translate(-0.02 + i * 0.08, -0.36, -0.055)
        board.add(leg)
    for s in (-1, 1):                        # a raised wing, for silhouette
        wg = M.chamfered_prism([(0.0, 0.0), (0.22, 0.14), (0.10, 0.26),
                                (-0.14, 0.10)], 0.022, "alabaster", 0.004)
        wg.rotate_z(s * 0.16)
        wg.translate(0.0, 0.02, -0.062)
        board.add(wg)

    board.rotate_z(0.055)                    # hangs crooked, and it swings
    board.translate(0.80, -0.92, 0)
    out.add(board)
    return out


def _storey(g, asset_id, width, depth, height, y, cx, zf, style, front_ops,
            side_ops=(), back_ops=()):
    """One timber-framed storey, four walls, in the design frame."""
    zb = BACK_Z
    cz = (zf + zb) * 0.5
    front = K.timber_frame_wall(width, height, f"{asset_id}.f", style=style,
                                sill_y=0, openings=list(front_ops))
    front.translate(cx, y, zf)
    g.add(front)

    back = K.timber_frame_wall(width, height, f"{asset_id}.b", style="square",
                               sill_y=0, openings=list(back_ops))
    back.rotate_y(np.pi)
    back.translate(cx, y, zb)
    g.add(back)

    for sx in (-1, 1):
        # SQUARE panels on the flanks even when the front is close-studded.
        # That is how it was actually built — close studding was ruinously
        # expensive and went on the elevation the town could see — and it is
        # also 4,000 triangles a wall cheaper, on four walls nobody composes.
        side = K.timber_frame_wall(depth, height, f"{asset_id}.s{sx}",
                                   style="square", sill_y=0,
                                   openings=[(z - cz, oy, ow, oh)
                                             for (z, oy, ow, oh) in side_ops])
        side.rotate_y(sx * np.pi * 0.5)
        side.translate(cx + sx * width * 0.5, y, cz)
        g.add(side)


def _main_range(ctx, g, rng):
    """The street range: three storeys, jettied twice, gable to the square."""
    # --- plinth -------------------------------------------------------------
    poly = SI.rect(G_X, (G_ZF + BACK_Z) * 0.5, G_W + 0.44, BACK_Z - G_ZF + 0.44)
    slab, y0 = SI.plinth_under(SITE, poly, PLINTH, mat="rubble", chamfer=0.03)
    g.add(slab)
    ctx.collider("box",
                 center=SITE.p(G_X, (y0 + PLINTH) * 0.5, (G_ZF + BACK_Z) * 0.5),
                 half=((G_W + 0.44) * 0.5, max((PLINTH - y0) * 0.5, 0.05),
                       (BACK_Z - G_ZF + 0.44) * 0.5),
                 rot_y=SITE.yaw(), kind="surface", tag="inn_plinth")

    # --- ground storey ------------------------------------------------------
    # Door off-centre toward the yard, because the carriage entry is that side
    # and everybody comes round the corner. A centred door on an inn is a
    # symmetry no inn ever had.
    door_x = G_X + 1.60
    win_g = [(G_X - 2.40, 1.85, 1.85, 1.90), (G_X - 0.35, 1.85, 1.55, 1.60)]
    _storey(g, f"{ASSET}.g", G_W, BACK_Z - G_ZF, G_H, Y_G, G_X, G_ZF, "square",
            [(door_x - G_X, K.DOOR_H * 0.5 + 0.10, K.DOOR_W + 0.55,
              K.DOOR_H + 0.34)] + [(x - G_X, y, w, h) for (x, y, w, h) in win_g],
            side_ops=[(1.10, 1.85, 1.45, 1.55), (4.30, 1.85, 1.20, 1.40)],
            back_ops=[(-1.5, 1.85, 1.20, 1.40), (1.5, 1.85, 1.20, 1.40)])

    zf = G_ZF - 0.13
    fr = K.door_frame(width=1.28, height=2.42, mat="oak_dark", depth=0.30)
    fr.translate(door_x, Y_G, zf + 0.05)
    g.add(fr)
    door = K.plank_door(f"{ASSET}.door", width=1.24, height=2.38, mat="oak_dark",
                        open_angle=rng.uniform(0.75, 0.95))
    door.translate(door_x, Y_G, zf - 0.06)
    g.add(door)
    SITE.entity(f"{ASSET}.door.01", "door.inn", (door_x, Y_G, zf - 0.12),
                verbs=["enter"],
                rest_point={"restores": ["stamina", "health"]})

    # Ground-floor lights: BIG, and every one of them lit. This is the common
    # room and it is the warmest thing in any frame.
    for i, (wx, wy, ww, wh) in enumerate(win_g):
        win = K.leaded_window(f"{ASSET}.gw{i}", width=ww - 0.24, height=wh - 0.24,
                              mat="glass_lit", shutters=(i == 0),
                              shutter_mat="painted")
        win.translate(wx, Y_G + wy, zf + 0.07)
        g.add(win)
    for i, (z, wy, ww, wh) in enumerate(((1.10, 1.85, 1.45, 1.55),
                                         (4.30, 1.85, 1.20, 1.40))):
        for sx in (-1, 1):
            win = K.leaded_window(f"{ASSET}.gs{sx}{i}", width=ww - 0.24,
                                  height=wh - 0.24, mat="glass_lit",
                                  shutters=False)
            win.rotate_y(sx * np.pi * 0.5)
            win.translate(G_X + sx * (G_W * 0.5 + 0.07), Y_G + wy, z)
            g.add(win)

    # --- first floor, jettied ----------------------------------------------
    j1 = K.jetty(G_W, BACK_Z - G_ZF, JETTY)
    j1.translate(G_X, Y_1, (G_ZF + BACK_Z) * 0.5)
    g.add(j1)
    win_1 = [(-2.60, 1.60, 1.35, 1.55), (-0.45, 1.60, 1.35, 1.55),
             (1.70, 1.60, 1.35, 1.55)]
    _storey(g, f"{ASSET}.f1", F1_W, BACK_Z - F1_ZF, F1_H, Y_1, G_X, F1_ZF,
            "close", win_1,
            side_ops=[(0.4, 1.60, 1.20, 1.45), (3.4, 1.60, 1.20, 1.45)],
            back_ops=[(-2.0, 1.60, 1.10, 1.35), (1.4, 1.60, 1.10, 1.35)])
    for i, (wx, wy, ww, wh) in enumerate(win_1):
        # Not every room is occupied — a uniformly lit facade reads as a
        # lightbox rather than as a building with people in some of the rooms.
        # But this is the FRONT of the inn, so the odds are heavily warm.
        win = K.leaded_window(f"{ASSET}.w1{i}", width=ww - 0.20, height=wh - 0.20,
                              mat="glass_lit" if rng.random() < 0.85 else "glass",
                              shutters=rng.random() < 0.4, shutter_mat="painted")
        win.translate(G_X + wx, Y_1 + wy, F1_ZF - 0.07)
        g.add(win)
    for i, z in enumerate((0.4, 3.4)):
        for sx in (-1, 1):
            win = K.leaded_window(f"{ASSET}.w1s{sx}{i}", width=1.00, height=1.25,
                                  mat="glass_lit" if (i + sx) % 2 else "glass",
                                  shutters=False)
            win.rotate_y(sx * np.pi * 0.5)
            win.translate(G_X + sx * (F1_W * 0.5 + 0.07), Y_1 + 1.60, z)
            g.add(win)

    # --- second floor, jettied again ---------------------------------------
    j2 = K.jetty(F1_W, BACK_Z - F1_ZF, JETTY * 0.80)
    j2.translate(G_X, Y_2, (F1_ZF + BACK_Z) * 0.5)
    g.add(j2)
    win_2 = [(-2.35, 1.50, 1.20, 1.40), (0.00, 1.50, 1.20, 1.40),
             (2.35, 1.50, 1.20, 1.40)]
    _storey(g, f"{ASSET}.f2", F2_W, BACK_Z - F2_ZF, F2_H, Y_2, G_X, F2_ZF,
            "close", win_2,
            side_ops=[(1.6, 1.50, 1.10, 1.35)],
            back_ops=[(-1.6, 1.50, 1.05, 1.30), (1.6, 1.50, 1.05, 1.30)])
    for i, (wx, wy, ww, wh) in enumerate(win_2):
        win = K.leaded_window(f"{ASSET}.w2{i}", width=ww - 0.20, height=wh - 0.20,
                              mat="glass_lit" if rng.random() < 0.7 else "glass",
                              shutters=False)
        win.translate(G_X + wx, Y_2 + wy, F2_ZF - 0.07)
        g.add(win)
    for sx in (-1, 1):
        win = K.leaded_window(f"{ASSET}.w2s{sx}", width=0.92, height=1.18,
                              mat="glass", shutters=False)
        win.rotate_y(sx * np.pi * 0.5)
        win.translate(G_X + sx * (F2_W * 0.5 + 0.07), Y_2 + 1.50, 1.6)
        g.add(win)

    # --- glazing the back and the remaining side openings -------------------
    # An opening with no glass in it is a hole, and a hole in a plaster wall
    # reads as a bomb site. Every aperture cut in `_storey` gets a light in it,
    # including the ones on the elevations nobody composes for — the back of
    # this range is the first thing seen from Sty Lane.
    for lvl, (yy, ops, ww, hh) in enumerate((
            (Y_G, ((-1.5, 1.85), (1.5, 1.85)), 1.00, 1.20),
            (Y_1, ((-2.0, 1.60),), 0.92, 1.15),
            (Y_2, ((1.6, 1.50),), 0.88, 1.10))):
        for i, (wx, wy) in enumerate(ops):
            win = K.leaded_window(f"{ASSET}.bw{lvl}{i}", width=ww, height=hh,
                                  mat="glass_lit" if (lvl + i) % 3 else "glass",
                                  shutters=False)
            win.rotate_y(np.pi)
            win.translate(G_X + wx, yy + wy, BACK_Z + 0.07)
            g.add(win)

    # --- balcony on the top floor, with the laundry on it -------------------
    bal = M.Group()
    deck = M.box(4.80, 0.10, 0.86, 0.008, "oak_weathered")
    bal.add(deck)
    for i in range(12):
        p = M.box(0.058, 0.90, 0.058, 0.005, "oak_weathered")
        p.translate(-2.20 + i * 0.40, 0.50, -0.38)
        bal.add(p)
    rail = M.plank(4.80, 0.10, 0.075, 0.006, "oak_weathered")
    rail.translate(0, 0.95, -0.38)
    bal.add(rail)
    for sx in (-1, 1):                       # brackets carrying it
        br = M.chamfered_prism([(0.0, 0.0), (0.62, 0.0), (0.0, -0.68)], 0.10,
                               "oak_dark", 0.008)
        br.rotate_y(np.pi * 0.5)
        br.translate(sx * 2.20, 0.0, -0.42)
        bal.add(br)
    # 0.38 m of oversail, not 1.05. A balcony IS meant to hang over the street
    # — but the plot line is the street line and this pass is about not
    # crossing it, so the deck stops where the roof verge does.
    bal.translate(G_X - 0.30, Y_2 + 0.14, F2_ZF - 0.06)
    g.add(bal)
    g.add(P.laundry_line(f"{ASSET}.laundry",
                         (G_X - 2.55, Y_2 + 1.10, F2_ZF - 0.50),
                         (G_X + 2.05, Y_2 + 1.16, F2_ZF - 0.50),
                         sag=0.14, items=4))

    # --- the roof -----------------------------------------------------------
    # Edge 0 of the rect runs along +X, so `ridge_axis="v"` lays the ridge INTO
    # the plot: the gable faces the street, which is the slot note's whole
    # point about the sign. `roof_from_plate` takes its height from the plate
    # and has deliberately no `y` parameter, so the eaves land on the
    # schedule's 10.60 by construction.
    f2_d = BACK_Z - F2_ZF
    poly = SI.rect(G_X, (F2_ZF + BACK_Z) * 0.5, F2_W, f2_d)
    plate = R.wall_plate(poly, EAVES,
                         edges=["gable", "eaves", "gable", "eaves"],
                         thickness=0.26, wall_mat="plaster")
    roof = R.roof_from_plate(plate, "gable", PITCH, 0.50, f"{ASSET}.roof",
                             mat="terracotta", timber_mat="oak_dark",
                             ridge_axis="v", verge=0.24)
    g.add(roof)

    for sz in (-1, 1):
        ge = K.gable_end(F2_W, EAVES, PITCH, mat="plaster", depth=0.26)
        if sz > 0:
            ge.rotate_y(np.pi)
        ge.translate(G_X, 0, F2_ZF if sz < 0 else BACK_Z)
        g.add(ge)
        # Barge boards and a finial on the STREET gable: that profile against
        # the sky is what the inn is recognised by from the market place.
        for sx in (-1, 1):
            bb = M.box(F2_W * 0.56, 0.26, 0.11, 0.010, "oak_dark")
            bb.rotate_z(-sx * math.atan(PITCH))
            bb.translate(G_X + sx * F2_W * 0.25,
                         (EAVES + roof.ridge_y) * 0.5 + 0.10,
                         (F2_ZF - 0.28) if sz < 0 else (BACK_Z + 0.28))
            g.add(bb)
    fin = M.lathe([(0.075, 0.0), (0.10, 0.10), (0.045, 0.42), (0.09, 0.50),
                   (0.0, 0.72)], 8, "oak_dark")
    fin.translate(G_X, roof.ridge_y - 0.10, F2_ZF - 0.24)
    g.add(fin)

    # --- dormers ------------------------------------------------------------
    # The slot note asks for "four dormers on the east slope". The range runs
    # front-to-back so the front IS the east gable and there is no east slope;
    # the two slopes look north and south. Four dormers therefore go three on
    # the SOUTH slope (sunlit at 09:30, and the side the yard and the market
    # both see) and one on the north, which is also what stops them reading as
    # a repeated row — Art Bible §6.
    for (dx, dz, lit) in ((1.0, -3.20, True), (1.0, -0.60, True),
                          (1.0, 2.00, False), (-1.0, -1.90, True)):
        dm = R.dormer(roof, G_X + dx * (F2_W * 0.5 - 1.35), dz,
                      f"{ASSET}.dorm{dx:.0f}{dz:.1f}", width=1.35, height=1.35,
                      mat="plaster")
        if dm is not None:
            g.add(dm)
        w = K.leaded_window(f"{ASSET}.dw{dx:.0f}{dz:.1f}", width=0.78,
                            height=0.88, mat="glass_lit" if lit else "glass")
        w.rotate_y(0.0 if dx > 0 else np.pi)
        w.translate(G_X + dx * (F2_W * 0.5 - 1.35) + dx * 0.62,
                    EAVES + 1.10, dz)
        g.add(w)

    # --- two chimneys, both drawing ----------------------------------------
    # A stack has to clear the RIDGE or it smokes, and the ridge sits higher
    # than a naive half-span suggests because the roof adds its overhang to the
    # span. Derived from `roof.ridge_y` for exactly that reason.
    for i, (cx, cz) in enumerate(((G_X - 2.30, 3.90), (G_X + 1.70, -3.60))):
        ch_h = roof.ridge_y - EAVES + 1.7 + i * 0.35
        ch = K.chimney(f"{ASSET}.ch{i}", height=ch_h, section=0.86)
        ch.translate(cx, EAVES - 0.25, cz)
        g.add(ch)
        SITE.entity(f"{ASSET}.chimney.{i + 1:02d}", "prop.chimney",
                    (cx, EAVES - 0.25 + ch_h, cz),
                    smoke={"rate": 0.7, "drift": [0.8, 0, 0.5]})

    # --- collision ----------------------------------------------------------
    # The ground-floor footprint is the whole of it: the jetties oversail at
    # 4.05 m, which is over a player's head. The doorway is a gap, and steps
    # carry the player up the plinth — without them the door is visible and
    # unreachable, which is the same defect as a sealed street.
    SITE.collider_walls(G_W, BACK_Z - G_ZF, G_H + F1_H, y=Y_G, thickness=0.30,
                        center=(G_X, (G_ZF + BACK_Z) * 0.5),
                        doors=[("-z", door_x - G_X, K.DOOR_W + 0.75)],
                        tag="inn")
    SITE.collider_steps((door_x, 0.0, G_ZF - 0.30), PLINTH, tread=0.42,
                        width=K.DOOR_W + 1.10)

    # --- the sign, hung off the first-floor jetty ---------------------------
    sign = _heron_sign(f"{ASSET}.sign")
    sign.translate(G_X - 3.05, Y_1 + 1.05, F1_ZF - 0.10)
    g.add(sign)
    SITE.entity(f"{ASSET}.sign.01", "prop.inn_sign",
                (G_X - 1.95, Y_1 + 0.10, F1_ZF - 0.16), verbs=["inspect"],
                landmark={"name": "The Grey Heron"})
    return roof


def _common_room(ctx, g, rng):
    """What the player sees through the open door: hearth, tables, people's
    things. The inn's whole emotional job is done in this six square metres.
    """
    fy = Y_G + 0.02
    inner_w = G_W - 0.60
    inner_d = (BACK_Z - G_ZF) - 0.60
    cz = (G_ZF + BACK_Z) * 0.5

    # Dark shell first. Without it the open door and eleven lit windows look
    # straight through to sunlit exterior plaster and sky, which is the single
    # strongest "facade, not a building" tell there is.
    sh = M.box(inner_w, G_H + F1_H + F2_H - 0.10, inner_d, 0.02, "oak_dark")
    sh.scale(-1.0, 1.0, 1.0)
    sh.translate(G_X, Y_G + (G_H + F1_H + F2_H) * 0.5, cz)
    SITE.emit(sh, shell=True)

    # Boarded floor with the route from the door to the hearth walked pale.
    fl = SI.slab(SI.rect(G_X, cz, inner_w, inner_d), Y_G - 0.05, fy,
                 "oak_weathered", 0.010)
    g.add(fl)
    for i, (wx, wz, sz) in enumerate(((G_X + 1.30, G_ZF + 1.6, 2.6),
                                      (G_X - 1.20, G_ZF + 4.6, 2.2))):
        g.add(P.worn_patch(f"{ASSET}.iw{i}", shape="path", size=sz,
                           mat="oak_weathered").translate(wx, fy + 0.008, wz))

    # THE HEARTH, on the back wall on the door axis, with a fire in it. It is
    # the light source that makes every window on this floor read as warm.
    hx, hz = G_X - 2.30, BACK_Z - 0.55
    hood = M.chamfered_prism([(-1.35, 0.0), (1.35, 0.0), (1.35, 1.75),
                              (0.62, 2.55), (-0.62, 2.55), (-1.35, 1.75)],
                             0.90, "rubble", 0.022)
    hood.translate(hx, fy, hz)
    g.add(hood)
    op = M.box(1.70, 1.30, 0.55, 0.014, "timber_charred")
    op.translate(hx, fy + 0.65, hz - 0.50)
    g.add(op)
    for i in range(13):
        a = rng.uniform(0, 6.283)
        d = rng.uniform(0.0, 0.55) ** 0.7
        c = M.box(rng.uniform(0.08, 0.17), rng.uniform(0.05, 0.11),
                  rng.uniform(0.07, 0.14), 0.012, "coal")
        c.rotate_y(rng.uniform(0, 3.14))
        c.translate(hx + math.cos(a) * d, fy + 0.10 + rng.uniform(-0.01, 0.04),
                    hz - 0.55 + math.sin(a) * d * 0.5)
        g.add(c)
    for i in range(5):                       # logs, half burnt through
        lg = M.cylinder(rng.uniform(0.055, 0.085), rng.uniform(0.55, 0.85), 6,
                        0.006, "timber_charred")
        lg.rotate_z(np.pi * 0.5)
        lg.rotate_y(rng.uniform(-0.6, 0.6))
        lg.translate(hx + rng.uniform(-0.35, 0.35), fy + 0.16 + i * 0.055,
                     hz - 0.55 + rng.uniform(-0.12, 0.12))
        g.add(lg)
    # Pot on a crane over the fire, and the crane itself, because a hearth with
    # nothing hanging in it is a fireplace, not a kitchen.
    cr = M.cylinder(0.028, 1.35, 6, 0.003, "iron")
    cr.rotate_z(np.pi * 0.5)
    cr.translate(hx - 0.20, fy + 1.30, hz - 0.55)
    g.add(cr)
    pot = M.lathe([(0.0, 0.0), (0.20, 0.06), (0.24, 0.24), (0.20, 0.36),
                   (0.22, 0.40)], 12, "iron", close_top=False)
    pot.translate(hx - 0.55, fy + 0.72, hz - 0.55)
    g.add(pot)
    g.add(K.forged_chain(f"{ASSET}.potchain", (hx - 0.55, fy + 1.28, hz - 0.55),
                         (hx - 0.55, fy + 1.14, hz - 0.55), sag=0.02, link=0.05))
    SITE.entity(f"{ASSET}.hearth.01", "prop.hearth", (hx, fy + 0.35, hz - 0.60),
                verbs=["inspect"],
                light={"color": "#FF9A4C", "intensity": 3.4, "range": 13.0,
                       "flickerHz": [6, 10]})

    # Long tables down the room, square on the door so the opening frames them.
    for i, (tx, tz, ln) in enumerate(((G_X + 0.90, G_ZF + 3.30, 3.20),
                                      (G_X - 1.90, G_ZF + 2.10, 2.60))):
        tb = K.trestle_table(f"{ASSET}.tbl{i}", length=ln, width=0.92)
        tb.rotate_y(0.06 if i else -0.04)
        tb.translate(tx, fy, tz)
        g.add(tb)
        for s in (-1, 1):
            bn = K.bench(f"{ASSET}.bn{i}{s}", length=ln - 0.30)
            bn.translate(tx, fy, tz + s * 0.78)
            g.add(bn)
        if i == 0:
            g.add(P.meal(f"{ASSET}.meal{i}", height=0.76).translate(tx, fy, tz))
        for k in range(2):
            g.add(P.mug(f"{ASSET}.mug{i}{k}", full=(k != 1))
                  .translate(tx + rng.uniform(-ln * 0.35, ln * 0.35), fy + 0.76,
                             tz + rng.uniform(-0.25, 0.25)))
    g.add(P.chair(f"{ASSET}.chair", cloak=True)
          .translate(G_X + 2.05, fy, G_ZF + 2.10))
    g.add(P.dice_on_barrel(f"{ASSET}.dice")
          .translate(G_X + 1.90, fy, G_ZF + 5.40))

    # The bar: a plank counter over three barrels, which is what an inn of this
    # date actually had. Casks on a stillage behind it.
    bx, bz = G_X + 2.05, BACK_Z - 1.30
    for i in range(3):
        bl = K.barrel(f"{ASSET}.barbase{i}", height=0.86)
        bl.translate(bx, fy, bz - 1.10 + i * 1.10)
        g.add(bl)
    top = M.box(0.86, 0.10, 3.60, 0.012, "oak_dark")
    top.translate(bx, fy + 0.92, bz)
    g.add(top)
    SITE.entity(f"{ASSET}.bar.01", "vendor.innkeeper", (bx - 0.60, fy + 0.95, bz),
                verbs=["talk", "buy"])
    SITE.collider("box", center=(bx, fy + 0.46, bz), half=(0.48, 0.46, 1.85),
                  tag="bar")
    for i in range(2):
        ck = P.barrel_lying(f"{ASSET}.cask{i}", height=1.05, belly=0.78)
        ck.translate(bx + 0.95, fy + 0.45, bz - 0.70 + i * 1.30)
        g.add(ck)
    for i in range(2):                       # mugs and jugs on the counter
        g.add(P.mug(f"{ASSET}.bmug{i}", full=(i % 3 != 0))
              .translate(bx + rng.uniform(-0.25, 0.25), fy + 0.97,
                         bz + rng.uniform(-1.5, 1.5)))
    g.add(P.glazed_jar(f"{ASSET}.jug", height=0.34)
          .translate(bx - 0.20, fy + 0.97, bz + 1.55))

    # A stair up to the chambers, in the corner where the doorway can see it.
    fl_, run = K.stair_flight(f"{ASSET}.stair", Y_1 - Y_G, width=1.05,
                              riser=0.20, going=0.26, mat="oak_weathered",
                              spine=0.0)
    fl_.rotate_y(np.pi)
    fl_.translate(G_X - 2.55, fy, G_ZF + 1.05)
    g.add(fl_)
    g.add(S.handrail(f"{ASSET}.srail", length=run, height=0.92,
                     mat="oak_weathered", posts=4)
          .translate(G_X - 1.95, fy + 0.9, G_ZF + 1.05 + run * 0.5))

    g.add(P.drying_herbs(f"{ASSET}.herbs", width=1.5, y=fy + 2.65,
                         wall_z=BACK_Z - 0.42, bunches=7))
    g.add(P.spill(f"{ASSET}.spilt", kind="ale", radius=0.55, density=0.9,
                  centre=(G_X + 0.30, G_ZF + 4.40), vessel=True)
          .translate(0, fy, 0))


def _stable(ctx, g, rng):
    """The stable range off the yard: half-doors, a loft, and a lot of straw."""
    cx, cz = (ST_X0 + ST_X1) * 0.5, (ST_Z0 + ST_Z1) * 0.5
    w, d = ST_X1 - ST_X0, ST_Z1 - ST_Z0

    poly = SI.rect(cx, cz, w + 0.36, d + 0.36)
    slab, y0 = SI.plinth_under(SITE, poly, 0.30, mat="rubble", chamfer=0.03)
    g.add(slab)
    ctx.collider("box", center=SITE.p(cx, (y0 + 0.30) * 0.5, cz),
                 half=((w + 0.36) * 0.5, max((0.30 - y0) * 0.5, 0.05),
                       (d + 0.36) * 0.5),
                 rot_y=SITE.yaw(), kind="surface", tag="stable_floor")

    # Three bays of half-doors onto the yard, with a loft door over the middle
    # one. Two doors stand open; the third is shut, which is the asymmetry that
    # stops three bays reading as a printed row.
    door_zs = (ST_Z0,)
    bays = [(cx - 1.70, True), (cx, False), (cx + 1.70, True)]
    ops = [(bx - cx, 1.15, 1.35, 2.30) for (bx, _o) in bays] + \
          [(0.0, ST_EAVES - 0.95, 1.20, 1.30)]
    front = K.timber_frame_wall(w, ST_EAVES, f"{ASSET}.stf", style="square",
                                sill_y=0, openings=ops)
    front.translate(cx, 0.30, ST_Z0)
    g.add(front)
    back = K.timber_frame_wall(w, ST_EAVES, f"{ASSET}.stb", style="square",
                               sill_y=0,
                               openings=[(x, 2.55, 0.82, 0.72)
                                         for x in (-1.6, 1.6)])
    back.rotate_y(np.pi)
    back.translate(cx, 0.30, ST_Z1)
    g.add(back)
    for sx in (-1, 1):
        sd = K.timber_frame_wall(d, ST_EAVES, f"{ASSET}.sts{sx}", style="square",
                                 sill_y=0,
                                 openings=[(1.6, 2.45, 0.90, 0.80)])
        sd.rotate_y(sx * np.pi * 0.5)
        sd.translate(cx + sx * w * 0.5, 0.30, cz)
        g.add(sd)

    # Glaze the stable's own openings, back and sides, for the same reason.
    for i, x in enumerate((-1.6, 1.6)):
        wn = K.leaded_window(f"{ASSET}.stbw{i}", width=0.66, height=0.56,
                             mat="glass", shutters=False)
        wn.rotate_y(np.pi)
        wn.translate(cx + x, 0.30 + 2.55, ST_Z1 + 0.06)
        g.add(wn)
    for sx in (-1, 1):
        wn = K.leaded_window(f"{ASSET}.stsw{sx}", width=0.74, height=0.64,
                             mat="glass_lit" if sx > 0 else "glass",
                             shutters=False)
        wn.rotate_y(sx * np.pi * 0.5)
        wn.translate(cx + sx * (w * 0.5 + 0.06), 0.30 + 2.45, cz + 1.6)
        g.add(wn)

    for i, (bx, open_) in enumerate(bays):
        # Stable doors are two leaves one over the other: the top stands open
        # so the horse can put its head out, the bottom stays shut.
        lo = K.plank_door(f"{ASSET}.sdl{i}", width=1.28, height=1.15,
                          mat="oak_weathered", open_angle=0.0)
        lo.translate(bx, 0.30, ST_Z0 - 0.14)
        g.add(lo)
        hi = K.plank_door(f"{ASSET}.sdh{i}", width=1.28, height=1.12,
                          mat="oak_weathered",
                          open_angle=(rng.uniform(1.05, 1.35) if open_ else 0.0))
        hi.translate(bx, 0.30 + 1.18, ST_Z0 - 0.14)
        g.add(hi)
        if open_:
            # Dark inside each open bay, and a hay net hanging in it.
            v = M.box(1.25, 1.10, 0.30, 0.010, "oak_dark")
            v.translate(bx, 0.30 + 1.72, ST_Z0 + 0.22)
            g.add(v)
    SITE.entity(f"{ASSET}.stable.01", "prop.stable", (cx, 0.30, ST_Z0 - 0.30),
                verbs=["use"])

    # Loft door with a gibbet beam and a block, for pitching hay in.
    ld = K.plank_door(f"{ASSET}.loft", width=1.16, height=1.26,
                      mat="oak_weathered", open_angle=0.85)
    ld.translate(cx, 0.30 + ST_EAVES - 1.60, ST_Z0 - 0.14)
    g.add(ld)
    beam = M.box(0.16, 0.18, 1.35, 0.010, "oak_dark")
    beam.translate(cx, 0.30 + ST_EAVES + 0.35, ST_Z0 - 0.55)
    g.add(beam)
    g.add(K.forged_chain(f"{ASSET}.gibbet", (cx, 0.30 + ST_EAVES + 0.28, ST_Z0 - 1.05),
                         (cx, 0.30 + ST_EAVES - 0.95, ST_Z0 - 1.02), sag=0.03,
                         link=0.07))

    # Roof: gable to the yard, so the roofline steps down from the main range.
    poly = SI.rect(cx, cz, w, d)
    plate = R.wall_plate(poly, 0.30 + ST_EAVES,
                         edges=["gable", "eaves", "gable", "eaves"],
                         thickness=0.24, wall_mat="plaster")
    # Tiled, not thatched. An inn with two hearths and a hayloft next door does
    # not roof its stable in straw, and `roof._thatch_slope` is four times the
    # geometry of a tiled slope for a range nobody stands under.
    roof = R.roof_from_plate(plate, "gable", ST_PITCH, 0.42, f"{ASSET}.stroof",
                             mat="terracotta", timber_mat="oak_dark",
                             ridge_axis="v", verge=0.30)
    g.add(roof)
    for sz in (-1, 1):
        ge = K.gable_end(w, 0.30 + ST_EAVES, ST_PITCH, mat="plaster", depth=0.24)
        if sz > 0:
            ge.rotate_y(np.pi)
        ge.translate(cx, 0, ST_Z0 if sz < 0 else ST_Z1)
        g.add(ge)

    SITE.collider_walls(w, d, ST_EAVES, y=0.30, thickness=0.26,
                        center=(cx, cz),
                        doors=[("-z", bays[0][0] - cx, 1.45),
                               ("-z", bays[2][0] - cx, 1.45)],
                        tag="stable")

    # Residue: straw trodden out of every bay, a muck heap in the corner, a
    # barrow, and the tack that lives on the wall between the doors.
    g.add(P.spill(f"{ASSET}.straw", kind="grain", radius=1.8, density=0.8,
                  centre=(cx, ST_Z0 - 1.10), vessel=False))
    g.add(S.midden(f"{ASSET}.muck", radius=0.95, height=0.52)
          .translate(ST_X1 - 0.90, 0.0, ST_Z0 - 1.90))
    bw = P.wheelbarrow(f"{ASSET}.barrow", tipped=False)
    bw.rotate_y(2.1)
    bw.translate(ST_X0 - 0.60, 0.0, ST_Z0 - 2.35)
    g.add(bw)
    for i, bx in enumerate((cx - 0.85, cx + 0.85)):
        pg = M.box(0.09, 0.13, 0.055, 0.004, "iron")
        pg.translate(bx, 0.30 + 2.72, ST_Z0 - 0.10)
        g.add(pg)
        hn = M.lathe([(0.14, 0.0), (0.16, 0.30), (0.09, 0.42)], 8, "leather")
        hn.translate(bx, 0.30 + 2.28, ST_Z0 - 0.22)
        g.add(hn)


def _yard(ctx, g, rng):
    """The inn yard: how a horse gets off the street, and where the mud is."""
    cx, cz = (YD_X0 + YD_X1) * 0.5, (YD_Z0 + YD_Z1) * 0.5
    w, d = YD_X1 - YD_X0, YD_Z1 - YD_Z0

    # Setted, not paved: a yard takes iron tyres and hooves and gets relaid in
    # patches, so it is the roughest made surface on the plot.
    g.add(SI.slab(SI.rect(cx, cz, w, d), -0.04, 0.05, "sett", 0.010))
    ctx.collider("box", center=SITE.p(cx, 0.0, cz),
                 half=(w * 0.5, 0.06, d * 0.5), rot_y=SITE.yaw(),
                 kind="surface", tag="inn_yard")
    for i in range(2):
        g.add(P.worn_patch(f"{ASSET}.yw{i}", shape="path", size=2.4, mat="mud")
              .translate(cx + rng.uniform(-1.8, 1.8), 0.062,
                         cz + rng.uniform(-2.0, 2.0)))

    # Mounting block, trough and rail along the main range's flank, which is
    # the wall a horse stands against while it is unharnessed.
    g.add(S.mounting_block(f"{ASSET}.mount", height=0.66)
          .translate(YD_X0 + 0.85, 0.05, YD_Z0 + 1.35))
    tr = S.horse_trough(f"{ASSET}.trough", length=2.10, width=0.68, height=0.58)
    tr.rotate_y(np.pi * 0.5)
    tr.translate(YD_X1 - 0.70, 0.05, cz + 0.30)
    g.add(tr)
    SITE.collider("box", center=(YD_X1 - 0.70, 0.34, cz + 0.30),
                  half=(0.36, 0.30, 1.08), tag="trough")
    rl = S.hitching_rail(f"{ASSET}.rail", length=2.90, height=1.02)
    rl.rotate_y(np.pi * 0.5)
    rl.translate(YD_X0 + 0.55, 0.05, cz - 0.60)
    g.add(rl)
    SITE.collider("box", center=(YD_X0 + 0.55, 0.55, cz - 0.60),
                  half=(0.14, 0.55, 1.50), tag="hitching_rail")

    # A cart pulled in and left standing. This is the single prop that says
    # "travellers arrive here" better than any amount of signage.
    cart = P.waggon(f"{ASSET}.waggon", length=3.30, width=1.50, load=None)
    cart.rotate_y(1.42)
    cart.translate(cx + 0.65, 0.05, cz - 1.35)
    g.add(cart)
    SITE.collider("box", center=(cx + 0.65, 0.75, cz - 1.35),
                  half=(0.90, 0.75, 1.75), rot_y=SITE.yaw(1.42), tag="waggon")

    # Water butt off the stable gable, and a woodpile against the main range.
    g.add(P.water_butt(f"{ASSET}.butt", height=1.05, wall_z=ST_Z0 - 0.10,
                       x=ST_X0 + 0.55).translate(0, 0.05, 0))
    g.add(S.woodpile(f"{ASSET}.wood", length=1.70, height=0.90, depth=0.50)
          .translate(YD_X0 + 1.60, 0.05, YD_Z1 - 0.55))
    g.add(S.lamp_post(f"{ASSET}.lamp", height=2.70)
          .translate(YD_X1 - 0.90, 0.05, YD_Z0 + 0.80))
    SITE.entity(f"{ASSET}.lantern.01", "prop.lantern",
                (YD_X1 - 0.90, 2.55, YD_Z0 + 0.80),
                light={"color": "#FFB35C", "intensity": 2.0, "range": 9.0})


def _threshold(ctx, g, rng):
    """The doorstep: boots, a bench, a scraper, and the mud everyone brings."""
    door_x = G_X + 1.60
    zf = G_ZF - 0.13
    y = Y_G

    g.add(S.threshold_stone(f"{ASSET}.step", width=1.90, depth=0.72, rise=0.11)
          .translate(door_x, y, zf - 0.36))
    g.add(P.dress_threshold(f"{ASSET}.thr", width=1.9, wall_z=zf - 0.06,
                            mud=True).translate(door_x, y, 0))
    g.add(S.boot_scraper(f"{ASSET}.scrape")
          .translate(door_x - 1.05, y, zf - 0.30))

    # BOOTS BY THE DOOR (WORLD_BIBLE). Four of them, two pairs, kicked off at
    # different angles because two different people did it.
    for i, (bx, bz, a) in enumerate(((-1.62, -0.34, 0.35), (-1.44, -0.28, 0.10))):
        boot = M.lathe([(0.060, 0), (0.068, 0.20), (0.052, 0.30)], 8,
                       "oak_weathered")
        boot.rotate_z(a * 0.4)
        boot.rotate_y(a)
        boot.translate(door_x + bx, y, zf + bz)
        g.add(boot)

    bench = K.bench(f"{ASSET}.obench", length=2.30)
    bench.translate(door_x - 3.05, y, zf - 0.62)
    g.add(bench)
    g.add(P.mug(f"{ASSET}.obmug", full=False)
          .translate(door_x - 2.45, y + 0.45, zf - 0.62))
    g.add(K.barrel(f"{ASSET}.obarrel").translate(door_x + 1.30, y, zf - 0.55))
    for i in range(2):
        lam = K.lantern(f"{ASSET}.dlamp{i}", scale=1.15)
        lam.translate(door_x + (-1.15 if i else 1.05), y + 2.45, zf - 0.06)
        g.add(lam)
        SITE.entity(f"{ASSET}.lantern.{i + 2:02d}", "prop.lantern",
                    (door_x + (-1.15 if i else 1.05), y + 2.45, zf),
                    light={"color": "#FFB35C", "intensity": 2.2, "range": 8.0})

    # A cat on the window sill, asleep in the sun, because §7 says residue
    # buys more life per unit effort than another ten thousand triangles.
    cat = M.Group()
    body = M.lathe([(0.0, 0), (0.080, 0.05), (0.090, 0.26), (0.05, 0.36)], 8,
                   "oak_weathered")
    body.rotate_z(np.pi * 0.5)
    cat.add(body)
    head = M.lathe([(0.0, 0), (0.058, 0.04), (0.0, 0.10)], 8, "oak_weathered")
    head.rotate_z(np.pi * 0.5)
    head.translate(0.42, 0.03, 0)
    cat.add(head)
    cat.rotate_y(0.55)
    cat.translate(G_X - 2.40, y + 1.05, zf - 0.16)
    g.add(cat)


# ---------------------------------------------------------------------------

def build(ctx: VenueContext, asset_id=ASSET):
    SITE.bind(ctx)
    rng = rng_for(asset_id, "inn")
    g = M.Group()

    roof = _main_range(ctx, g, rng)
    _common_room(ctx, g, rng)
    _stable(ctx, g, rng)
    _yard(ctx, g, rng)
    _threshold(ctx, g, rng)

    SITE.emit(g, container="inn")

    print(SITE.report())
    print(f"      range {G_W:g} wide x {BACK_Z - G_ZF:g} deep  eaves {EAVES:.2f} "
          f"ridge {roof.ridge_y:.2f}  stable {ST_X1 - ST_X0:g}x{ST_Z1 - ST_Z0:g}  "
          f"yard {YD_X1 - YD_X0:g}x{YD_Z1 - YD_Z0:g}")
