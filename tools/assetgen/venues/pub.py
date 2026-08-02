"""The Ferryman's Lamp — the locals' pub, and the social heart of Hearthmere.

Deliberately NOT a second inn. The Grey Heron is for travellers: tall, proud,
freshly kept. The Ferryman's Lamp is older, lower and squatter, and its whole
character comes from age.

The strongest single device here is that the building has SUNK. The ground rose
around it over two centuries of road-mending, so the threshold is a step DOWN
and the eaves sit low enough to duck under. That one decision does more to say
"this place is ancient" than any amount of texture work.

Cross-braced framing (Art Bible / kit: reads as older stock), a sagging ridge —
Art Bible §6 requires at least one element that is visibly wrong — and an iron
ferryman's lamp for a sign rather than a painted board.
"""

from __future__ import annotations

import numpy as np

from core import mesh as M
from core import kit as K
from core.mathx import rng_for
from core import siting as SI
from core.venue import VenueContext

NAME = "pub"
SITE = SI.Site(NAME)
CELLS = ["B3", "B4"]

W, D = 10.0, 8.0
EAVES = 2.55          # low: this is an old, squat building
SUNK = 0.30           # how far the ground has risen around it


def build(ctx: VenueContext, asset_id="hm.pub"):
    SITE.bind(ctx)
    rng = rng_for(asset_id, "pub")

    # --- the building sits below the modern ground level ------------------
    # Everything is offset down by SUNK, and the surrounding ground is built
    # up to meet it. The step down at the door is the payoff.
    y0 = -SUNK

    plinth = M.box(W + 0.4, 0.55, D + 0.4, 0.03, "stone")
    plinth.translate(0, y0 + 0.275, 0)
    SITE.emit(plinth)

    # Interior shell so the low windows and open door read as a dark, warm
    # room rather than showing sunlit plaster from the far wall.
    shell = M.box(W - 0.5, EAVES, D - 0.5, 0.02, "oak_dark")
    shell.scale(-1.0, 1.0, 1.0)
    shell.translate(0, y0 + 0.55 + EAVES * 0.5, 0)
    SITE.emit(shell, shell=True)

    # Raised ground apron around the building, with a sunken well at the door.
    apron = M.Group()
    for (ax, az, aw, ad) in [(0, -D * 0.5 - 1.9, W + 4.0, 2.4),
                             (-W * 0.5 - 1.6, 0, 2.4, D + 4.0),
                             (W * 0.5 + 1.6, 0, 2.4, D + 4.0)]:
        g = M.box(aw, 0.30, ad, 0.02, "cobble")
        g.translate(ax, 0.15, az)
        apron.add(g)
    SITE.emit(apron)

    # --- walls: cross-braced, older stock ---------------------------------
    door_x = -W * 0.5 + 3.4
    wins = [(door_x + 2.6, 1.35, 1.0, 1.05), (door_x + 4.7, 1.35, 1.0, 1.05),
            (door_x - 2.0, 1.35, 1.0, 1.05)]
    front = K.timber_frame_wall(
        W, EAVES, f"{asset_id}.front", style="cross", sill_y=y0 + 0.55,
        openings=[(door_x, K.DOOR_H * 0.5, K.DOOR_W + 0.4, K.DOOR_H + 0.3)] + wins)
    front.translate(0, 0, -D * 0.5)
    SITE.emit(front)

    back = K.timber_frame_wall(W, EAVES, f"{asset_id}.back", style="square",
                               sill_y=y0 + 0.55)
    back.rotate_y(np.pi)
    back.translate(0, 0, D * 0.5)
    SITE.emit(back)
    for sx in (-1, 1):
        side = K.timber_frame_wall(D, EAVES, f"{asset_id}.s{sx}", style="cross",
                                   sill_y=y0 + 0.55)
        side.rotate_y(sx * np.pi * 0.5)
        side.translate(sx * W * 0.5, 0, 0)
        SITE.emit(side)

    # --- collision -------------------------------------------------------
    # The pub has SUNK: its floor is 0.30 m below the modern street and the
    # ground around it was built up to meet it. So the collision is inverted
    # from every other building — the apron is a raised walkable surface, and
    # the two worn stones at the door are a step DOWN, which the controller
    # handles as ordinary ground following. Only the walls are solid.
    DOORWAY = K.DOOR_W + 0.50
    for (ax, az, aw, ad) in [(0, -D * 0.5 - 1.9, W + 4.0, 2.4),
                             (-W * 0.5 - 1.6, 0, 2.4, D + 4.0),
                             (W * 0.5 + 1.6, 0, 2.4, D + 4.0)]:
        SITE.collider("box", center=(ax, 0.15, az),
                     half=(aw * 0.5, 0.15, ad * 0.5), kind="surface",
                     tag="apron")
    SITE.collider("box", center=(0, y0 + 0.275, 0),
                 half=((W + 0.4) * 0.5, 0.275, (D + 0.4) * 0.5),
                 kind="surface", tag="plinth")
    SITE.collider_walls(W, D, EAVES, y=y0 + 0.55, thickness=0.30,
                       doors=[("-z", door_x, DOORWAY)])

    # --- door: a step DOWN into the pub -----------------------------------
    zf = -D * 0.5 - 0.12
    fr = K.door_frame(width=1.05, height=2.10, mat="oak_dark")
    fr.translate(door_x, y0 + 0.55, zf + 0.04)
    SITE.emit(fr)
    door = K.plank_door(f"{asset_id}.door", width=1.05, height=2.10,
                        mat="oak_weathered", open_angle=rng.uniform(0.6, 0.95))
    door.translate(door_x, y0 + 0.55, zf - 0.05)
    SITE.emit(door)
    SITE.entity(f"{asset_id}.door.01", "door.pub", (door_x, y0 + 0.55, zf),
               cell="B3", verbs=["enter"])

    # Worn steps down from the raised street to the old threshold.
    for i, (sy, sd) in enumerate([(0.30, 1.10), (0.10, 0.85)]):
        st = M.box(1.7 - i * 0.2, 0.20, sd, 0.02, "stone")
        st.translate(door_x, sy - 0.10, zf - 0.55 - i * 0.30)
        SITE.emit(st)

    for (wx, wy, _, _) in wins:
        # The pub's whole character is firelight rather than daylight.
        win = K.leaded_window(f"{asset_id}.w{wx:.1f}", width=0.72, height=0.80,
                              mat="glass_lit",
                              shutters=rng.random() < 0.4, shutter_mat="oak_weathered")
        win.translate(wx, y0 + 0.55 + wy, zf + 0.06)
        SITE.emit(win)

    # --- sagging roof ------------------------------------------------------
    # Art Bible §6 demands one visibly wrong element. An old ridge that has
    # dropped in the middle is the most characterful option available.
    y_e = y0 + 0.55 + EAVES
    pitch = 0.88
    roof = K.gable_roof(D, W, f"{asset_id}.roof", pitch=pitch, overhang=0.55,
                        tile_mat="terracotta")
    roof.rotate_y(np.pi * 0.5)
    roof.translate(0, y_e, 0)
    # Squash the ridge slightly and tip it: the whole roof sags toward one end.
    roof.scale(1.0, 0.94, 1.0)
    roof.rotate_z(0.012)
    roof.translate(0, 0.10, 0)
    SITE.emit(roof, container="pub roof")
    for sx in (-1, 1):
        g = K.gable_end(D, y_e, pitch * 0.94, mat="plaster", depth=0.22)
        g.rotate_y(np.pi * 0.5)
        g.translate(sx * W * 0.5, 0, 0)
        SITE.emit(g)

    # Height must clear the RIDGE, not the eave. Derived from the eave, this
    # stack finished 0.31m below its own ridge and was buried in the roof.
    ridge_h = ((D + 1.1) * 0.5) * pitch * 0.94
    ch = K.chimney(f"{asset_id}.chimney", height=ridge_h + 1.15, section=0.78)
    ch.translate(-W * 0.30, y_e - 0.25, rng.uniform(-0.4, 0.4))
    SITE.emit(ch, label="pub chimney")
    SITE.entity(f"{asset_id}.chimney.01", "prop.chimney",
               (-W * 0.30, y_e - 0.25 + ridge_h + 1.15, 0), cell="B3",
               smoke={"rate": 0.8, "drift": [0.8, 0, 0.5]})

    # --- the sign: an actual iron lamp, not a painted board ---------------
    br = K.sign_bracket(f"{asset_id}.bracket", reach=0.95, mat="iron")
    br.translate(door_x - 1.35, y0 + 0.55 + 2.25, zf - 0.10)
    SITE.emit(br)
    lamp = K.lantern(f"{asset_id}.sign", scale=1.9)
    lamp.translate(door_x - 1.35 + 0.64, y0 + 0.55 + 1.42, zf - 0.10)
    SITE.emit(lamp)
    SITE.entity(f"{asset_id}.sign.01", "prop.sign",
               (door_x - 0.71, y0 + 2.0, zf), cell="B3", verbs=["inspect"],
               light={"color": "#FFB35C", "intensity": 2.0, "range": 6.5})

    # --- outside: trestle tables where the locals actually sit ------------
    for i, (tx, tz, ta) in enumerate([(2.6, -D * 0.5 - 2.3, 0.12),
                                      (-3.4, -D * 0.5 - 2.5, -0.22)]):
        t = K.trestle_table(f"{asset_id}.table{i}", length=2.2)
        t.rotate_y(ta)
        t.translate(tx, 0.30, tz)
        SITE.emit(t)
        for s in (-1, 1):
            b = K.bench(f"{asset_id}.bench{i}{s}", length=2.0)
            b.rotate_y(ta)
            b.translate(tx + np.cos(ta + np.pi * 0.5) * s * 0.72, 0.30,
                        tz + np.sin(ta + np.pi * 0.5) * s * 0.72)
            SITE.emit(b)
        SITE.entity(f"{asset_id}.table.{i+1:02d}", "prop.table", (tx, 0.30, tz),
                   cell="B3", verbs=["sit"])

        # Residue: mugs left on the tables, rings where others stood.
        for k in range(rng.integers(1, 4)):
            mug = M.lathe([(0.045, 0), (0.048, 0.11), (0.044, 0.12)], 10, "terracotta")
            mug.translate(tx + rng.uniform(-0.7, 0.7), 0.30 + 0.74,
                          tz + rng.uniform(-0.22, 0.22))
            SITE.emit(mug)

    # Leaning stack of empty casks awaiting collection.
    for i, (bx, bz, by) in enumerate([(W * 0.5 - 0.9, -D * 0.5 - 1.5, 0.0),
                                      (W * 0.5 - 0.2, -D * 0.5 - 1.6, 0.0),
                                      (W * 0.5 - 0.55, -D * 0.5 - 1.55, 0.62)]):
        b = K.barrel(f"{asset_id}.cask{i}", height=0.62, belly=0.50)
        if i == 2:
            b.rotate_z(np.pi * 0.5)          # the top one is on its side
        b.translate(bx, 0.30 + by, bz)
        SITE.emit(b)

    # Sawdust and a broom at the threshold; a dog asleep in the sun.
    broom = M.Group()
    h = M.cylinder(0.022, 1.35, 6, 0.003, "oak_weathered")
    broom.add(h)
    head = M.box(0.09, 0.26, 0.20, 0.01, "thatch")
    head.translate(0, -0.02, 0)
    broom.add(head)
    broom.rotate_z(0.28)
    broom.translate(door_x + 1.25, 0.30, zf - 0.35)
    SITE.emit(broom)

    dog = M.Group()
    dbody = M.lathe([(0.0, 0), (0.13, 0.06), (0.15, 0.36), (0.09, 0.52)], 9, "oak_weathered")
    dbody.rotate_z(np.pi * 0.5)
    dog.add(dbody)
    dhead = M.lathe([(0.0, 0), (0.085, 0.05), (0.06, 0.14)], 8, "oak_weathered")
    dhead.rotate_z(np.pi * 0.5)
    dhead.translate(0.56, 0.02, 0)
    dog.add(dhead)
    dog.rotate_y(-0.7)
    dog.translate(door_x + 2.6, 0.32, zf - 1.5)
    SITE.emit(dog)
