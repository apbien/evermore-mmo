"""Cottage — the reference venue implementation.

This is the pattern every other venue module follows. It is deliberately a
modest building: the point is to show the standard on something simple, so
that "simplistic" never becomes an excuse for "unfinished".

What makes it hold up is not polygon count. It is:
  - correct scale against the Art Bible §3 table
  - the plinth/frame/roof build-up that every Hearthmere building shares
  - asymmetry: nothing is centred, nothing repeats exactly
  - residue (§7): firewood, a window box, a bucket, a barrel — evidence that
    somebody lives here

Perimeter cottages are what turn a set of landmark venues into a town.
"""

from __future__ import annotations

import numpy as np

from core import mesh as M
from core import kit as K
from core.mathx import rng_for
from core.venue import VenueContext

NAME = "cottage"
CELLS = ["A2", "B2", "F2", "A4", "F3", "F5"]

WIDTH, DEPTH = 6.4, 5.2
EAVES = 2.85


def build(ctx: VenueContext, variant=0, asset_id="hm.cottage.01"):
    rng = rng_for(asset_id, "cottage", variant)

    # Variant drives the whole building so the six perimeter cottages read as
    # related but individually built. Art Bible §6: no element three times in
    # a row without a variant.
    style = ["square", "cross", "square", "herring"][variant % 4]
    roof_mat = "terracotta" if variant % 3 else "thatch"
    shutter = ["painted", "oak_weathered", "painted"][variant % 3]
    w = WIDTH * rng.uniform(0.94, 1.08)
    d = DEPTH * rng.uniform(0.94, 1.06)
    eaves = EAVES * rng.uniform(0.96, 1.05)

    # --- plinth ----------------------------------------------------------
    # Timber never touches the ground in this town; the stone base is why the
    # buildings have survived and why the wall-bottom dirt band sits where it
    # does in the material.
    ctx.emit(K.stone_plinth(w + 0.24, d + 0.24, 0.42), "stone")

    # --- walls -----------------------------------------------------------
    door_x = -w * 0.5 + w * rng.uniform(0.26, 0.38)   # never centred
    win_x = door_x + rng.uniform(1.7, 2.3)

    front = K.timber_frame_wall(
        w, eaves, f"{asset_id}.front", style=style, sill_y=0.42,
        openings=[(door_x, 0.42 + K.DOOR_H * 0.5, K.DOOR_W + 0.3, K.DOOR_H + 0.3),
                  (win_x, 0.42 + 1.55, 1.1, 1.3)])
    front.translate(0, 0, -d * 0.5)
    ctx.emit(front)

    back = K.timber_frame_wall(w, eaves, f"{asset_id}.back", style="square", sill_y=0.42)
    back.rotate_y(np.pi)
    back.translate(0, 0, d * 0.5)
    ctx.emit(back)

    for sx in (-1, 1):
        side = K.timber_frame_wall(d, eaves, f"{asset_id}.side{sx}", style=style, sill_y=0.42)
        side.rotate_y(sx * np.pi * 0.5)
        side.translate(sx * w * 0.5, 0, 0)
        ctx.emit(side)

    # --- gable ends and roof --------------------------------------------
    pitch = rng.uniform(0.82, 0.95)
    gable_pitch = pitch * 1.25 if roof_mat == "thatch" else pitch
    for sz in (-1, 1):
        g = K.gable_end(d, 0.42 + eaves, gable_pitch, depth=0.20)
        g.rotate_y(np.pi * 0.5)
        g.translate(sz * w * 0.5, 0, 0)
        ctx.emit(g, "plaster")

    # Thatch needs its own builder: the tile-course logic produces thin stepped
    # slabs, and thatch's whole character is mass and rounded edges.
    if roof_mat == "thatch":
        roof = K.thatch_roof(d, w, f"{asset_id}.roof", pitch=pitch * 1.25, overhang=0.55)
    else:
        roof = K.gable_roof(d, w, f"{asset_id}.roof", pitch=pitch, overhang=0.40,
                            tile_mat=roof_mat)
    roof.rotate_y(np.pi * 0.5)
    roof.translate(0, 0.42 + eaves, 0)
    ctx.emit(roof)

    # --- chimney ---------------------------------------------------------
    ch = K.chimney(f"{asset_id}.chimney", height=1.9 + pitch * d * 0.5)
    ch.translate(w * rng.uniform(0.26, 0.34), 0.42 + eaves - 0.3, 0)
    ctx.emit(ch)

    # --- openings --------------------------------------------------------
    zf = -d * 0.5 - 0.12
    ctx.emit(K.door_frame(), "oak_dark")
    frame = K.door_frame()
    frame.translate(door_x, 0.42, zf + 0.02)
    ctx.emit(frame)

    door = K.plank_door(f"{asset_id}.door", open_angle=rng.uniform(0.0, 0.35))
    door.translate(door_x, 0.42, zf - 0.05)
    ctx.emit(door)
    ctx.entity(f"{asset_id}.door", "door.cottage",
               (door_x, 0.42, zf), verbs=["open"],
               collider={"shape": "box", "half": [K.DOOR_W * 0.5, K.DOOR_H * 0.5, 0.05]})

    win = K.leaded_window(f"{asset_id}.win1", mat="glass_lit" if variant % 2 else "glass",
                          shutters=True, shutter_mat=shutter)
    win.translate(win_x, 0.42 + 1.55, zf + 0.04)
    ctx.emit(win)

    # A second window on the side wall, at a different height — real cottages
    # are extended piecemeal and their openings do not line up.
    win2 = K.leaded_window(f"{asset_id}.win2", width=0.62, height=0.78, shutters=False)
    win2.rotate_y(-np.pi * 0.5)
    win2.translate(-w * 0.5 - 0.12, 0.42 + rng.uniform(1.4, 1.75), rng.uniform(-0.8, 0.8))
    ctx.emit(win2)

    # --- residue: the part that makes it inhabited -----------------------
    # Art Bible §7. A correct empty building reads as a model; these props are
    # what make it somebody's home.

    # Firewood stacked against the gable, out of the rain under the eaves.
    stack_x = -w * 0.5 - 0.28
    for row in range(4):
        for i in range(rng.integers(5, 8)):
            log = M.cylinder(rng.uniform(0.045, 0.075), rng.uniform(0.34, 0.44),
                             7, 0.004, "oak_weathered")
            log.rotate_z(np.pi * 0.5)
            log.rotate_y(rng.uniform(-0.06, 0.06))
            log.translate(stack_x, 0.44 + row * 0.115 + rng.uniform(-0.01, 0.01),
                          -0.9 + i * 0.135 + rng.uniform(-0.02, 0.02))
            ctx.emit(log)

    # Window box — the strongest single cue that somebody tends this house.
    boxw = 0.86
    wb = M.box(boxw, 0.19, 0.20, 0.008, "oak_weathered")
    wb.translate(win_x, 0.42 + 1.55 - 0.62, zf - 0.06)
    ctx.emit(wb)
    plants = K.planter_plants(f"{asset_id}.box", boxw * 0.82, count=5)
    plants.translate(win_x, 0.42 + 1.55 - 0.55, zf - 0.06)
    ctx.emit(plants)

    # A barrel under the eaves catching roof runoff, and a bucket beside it.
    bar = K.barrel(f"{asset_id}.barrel")
    bar.translate(w * 0.5 - 0.55, 0.42, -d * 0.5 - 0.42)
    ctx.emit(bar)

    buck = M.lathe([(0.115, 0), (0.135, 0.24)], 12, "oak_weathered", close_top=False)
    buck.rotate_z(rng.uniform(-0.1, 0.1))
    buck.translate(door_x + rng.uniform(0.7, 1.0), 0.42, zf - rng.uniform(0.3, 0.5))
    ctx.emit(buck)

    # Boot scraper by the door — small, period-correct, and exactly the kind of
    # detail that rewards a player who walks up close.
    sc = M.box(0.026, 0.11, 0.28, 0.004, "iron")
    sc.translate(door_x - 0.62, 0.42 + 0.055, zf - 0.18)
    ctx.emit(sc)


