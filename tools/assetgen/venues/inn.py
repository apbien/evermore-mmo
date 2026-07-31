"""The Grey Heron Inn — the second-largest mass in Hearthmere.

Three storeys, the tallest TIMBER structure in town. Its emotional job is to be
the most inviting thing in the frame: warm light in every window, smoke from
both chimneys, a sign that swings.

The jettied upper floors do most of the visual work. Each storey oversails the
one below, which is period-correct (it bought floor area over the street) and
is the single best silhouette-breaker available — it also throws a deep
horizontal shadow that separates the storeys so the building never reads as one
extruded slab.
"""

from __future__ import annotations

import numpy as np

from core import mesh as M
from core import kit as K
from core.mathx import rng_for
from core.venue import VenueContext

NAME = "inn"
CELLS = ["E3", "E4"]

W, D = 11.5, 9.0
G_H, F1_H, F2_H = 3.05, 2.85, 2.60      # storey heights, Art Bible §3
JETTY = 0.42


def _storey(ctx, asset_id, width, depth, height, y, style, openings_front,
            shutter="painted"):
    """One timber-framed storey, four walls."""
    front = K.timber_frame_wall(width, height, f"{asset_id}.f", style=style,
                                sill_y=0, openings=openings_front)
    front.translate(0, y, -depth * 0.5)
    ctx.emit(front)

    back = K.timber_frame_wall(width, height, f"{asset_id}.b", style="square", sill_y=0)
    back.rotate_y(np.pi)
    back.translate(0, y, depth * 0.5)
    ctx.emit(back)

    for sx in (-1, 1):
        side = K.timber_frame_wall(depth, height, f"{asset_id}.s{sx}", style=style, sill_y=0)
        side.rotate_y(sx * np.pi * 0.5)
        side.translate(sx * width * 0.5, y, 0)
        ctx.emit(side)


def _heron_sign(asset_id):
    """Painted board showing a grey heron. Pictorial only — Art Bible §2.

    The bird is built from primitives rather than painted into a texture, so it
    reads in silhouette from across the street, which is what a shop sign is
    actually for.
    """
    out = M.Group()
    out.add(K.sign_bracket(asset_id, reach=1.05, mat="iron"))

    board = M.Group()
    b = M.box(1.05, 0.78, 0.045, 0.008, "oak_dark", uv_scale=1.2)
    board.add(b)
    for sy in (-1, 1):
        r = M.plank(1.10, 0.05, 0.032, 0.004, "iron")
        r.translate(0, sy * 0.39, 0)
        board.add(r)

    # The heron, in relief on the board face.
    body = M.lathe([(0.0, 0), (0.085, 0.05), (0.10, 0.17), (0.0, 0.30)], 10, "ashlar")
    body.rotate_x(np.pi * 0.5)
    body.translate(0.02, -0.08, -0.035)
    board.add(body)
    for i in range(5):                       # neck
        t = i / 4.0
        seg = M.cylinder(0.030 - t * 0.010, 0.07, 6, 0.003, "ashlar")
        seg.rotate_z(-0.5 + t * 1.2)
        seg.translate(-0.06 + np.sin(t * 1.4) * 0.12, 0.10 + t * 0.16, -0.035)
        board.add(seg)
    beak = M.lathe([(0.022, 0), (0.006, 0.15)], 6, "ashlar")
    beak.rotate_z(-1.4)
    beak.translate(0.14, 0.30, -0.035)
    board.add(beak)
    for i in range(2):                       # legs
        leg = M.cylinder(0.013, 0.20, 5, 0.002, "ashlar")
        leg.translate(-0.02 + i * 0.07, -0.30, -0.035)
        board.add(leg)

    board.rotate_z(0.055)                    # hangs slightly crooked
    board.translate(0.72, -0.55, 0)
    out.add(board)
    return out


def build(ctx: VenueContext, asset_id="hm.inn"):
    rng = rng_for(asset_id, "inn")

    y0 = 0.45
    ctx.emit(K.stone_plinth(W + 0.3, D + 0.3, y0), "stone")

    # Interior shell. Without it, sky and sunlit exterior plaster show through
    # every window and the open front door, which is the single strongest
    # "facade, not a building" tell.
    shell = M.box(W - 0.5, G_H + F1_H + F2_H, D - 0.5, 0.02, "oak_dark", uv_scale=0.5)
    shell.scale(-1.0, 1.0, 1.0)      # inward-facing
    shell.translate(0, y0 + (G_H + F1_H + F2_H) * 0.5, 0)
    ctx.emit(shell, shell=True)

    # --- ground floor ----------------------------------------------------
    door_x = -W * 0.5 + 3.1
    win_g = [(door_x + 2.5, 1.55, 1.3, 1.4), (door_x + 4.9, 1.55, 1.3, 1.4),
             (door_x - 1.9, 1.55, 1.3, 1.4)]
    _storey(ctx, f"{asset_id}.g", W, D, G_H, y0, "square",
            [(door_x, K.DOOR_H * 0.5, K.DOOR_W + 0.4, K.DOOR_H + 0.3)] + win_g)

    zf = -D * 0.5 - 0.12
    fr = K.door_frame(width=1.15, height=2.25)
    fr.translate(door_x, y0, zf + 0.04)
    ctx.emit(fr)
    door = K.plank_door(f"{asset_id}.door", width=1.15, height=2.25,
                        mat="oak_dark", open_angle=rng.uniform(0.5, 0.8))
    door.translate(door_x, y0, zf - 0.05)
    ctx.emit(door)
    ctx.entity(f"{asset_id}.door.01", "door.inn", (door_x, y0, zf), cell="E3",
               verbs=["enter"], rest_point={"restores": ["stamina", "health"]})

    for (wx, wy, _, _) in win_g:
        win = K.leaded_window(f"{asset_id}.gw{wx:.1f}", width=0.95, height=1.15,
                              shutters=True, shutter_mat="painted")
        win.translate(wx, y0 + wy, zf + 0.06)
        ctx.emit(win)

    # --- first floor, jettied -------------------------------------------
    y1 = y0 + G_H
    j1 = K.jetty(W, D, JETTY)
    j1.translate(0, y1, 0)
    ctx.emit(j1)
    W1, D1 = W + JETTY * 2, D + JETTY * 2
    # Close studding on the upper floors: the kit notes it reads as wealthier
    # construction, which is right for a prosperous inn and contrasts the
    # plain square framing of the cottages.
    win_1 = [(-3.6, 1.35, 1.2, 1.3), (-1.2, 1.35, 1.2, 1.3),
             (1.2, 1.35, 1.2, 1.3), (3.6, 1.35, 1.2, 1.3)]
    _storey(ctx, f"{asset_id}.f1", W1, D1, F1_H, y1, "close", win_1)
    for (wx, wy, _, _) in win_1:
        win = K.leaded_window(f"{asset_id}.w1{wx:.1f}", width=0.88, height=1.05,
                              shutters=rng.random() < 0.5, shutter_mat="painted")
        win.translate(wx, y1 + wy, -D1 * 0.5 - 0.06)
        ctx.emit(win)

    # --- second floor, jettied again ------------------------------------
    y2 = y1 + F1_H
    j2 = K.jetty(W1, D1, JETTY * 0.8)
    j2.translate(0, y2, 0)
    ctx.emit(j2)
    W2, D2 = W1 + JETTY * 1.6, D1 + JETTY * 1.6
    win_2 = [(-2.9, 1.25, 1.1, 1.2), (0.0, 1.25, 1.1, 1.2), (2.9, 1.25, 1.1, 1.2)]
    _storey(ctx, f"{asset_id}.f2", W2, D2, F2_H, y2, "close", win_2)
    for (wx, wy, _, _) in win_2:
        win = K.leaded_window(f"{asset_id}.w2{wx:.1f}", width=0.82, height=0.98,
                              shutters=False)
        win.translate(wx, y2 + wy, -D2 * 0.5 - 0.06)
        ctx.emit(win)

    # Balcony on the top floor — laundry hangs here (residue, §7).
    y3 = y2 + F2_H
    bal = M.Group()
    deck = M.box(4.6, 0.09, 1.05, 0.008, "oak_weathered", uv_scale=1.2)
    deck.translate(0, 0, 0)
    bal.add(deck)
    for i in range(11):
        bx = -2.2 + i * 0.44
        p = M.box(0.055, 0.85, 0.055, 0.005, "oak_weathered")
        p.translate(bx, 0.47, -0.48)
        bal.add(p)
    rail = M.plank(4.6, 0.09, 0.07, 0.006, "oak_weathered")
    rail.translate(0, 0.90, -0.48)
    bal.add(rail)
    bal.translate(-1.4, y2 + 0.10, -D2 * 0.5 - 0.50)
    ctx.emit(bal)

    for i in range(4):                        # laundry
        cloth = M.box(rng.uniform(0.30, 0.46), rng.uniform(0.40, 0.60), 0.008,
                      0.0, "canvas")
        cloth.rotate_z(rng.uniform(-0.05, 0.05))
        cloth.translate(-3.3 + i * 0.62, y2 + 0.62, -D2 * 0.5 - 0.62)
        ctx.emit(cloth)

    # --- roof with dormers ----------------------------------------------
    pitch = 0.92
    roof = K.gable_roof(D2, W2, f"{asset_id}.roof", pitch=pitch, overhang=0.50)
    roof.rotate_y(np.pi * 0.5)
    roof.translate(0, y3, 0)
    ctx.emit(roof, container="inn roof")
    for sx in (-1, 1):
        g = K.gable_end(D2, y3, pitch, mat="plaster", depth=0.24)
        g.rotate_y(np.pi * 0.5)
        g.translate(sx * W2 * 0.5, 0, 0)
        ctx.emit(g)

    # Gabled dormers — the World Bible names these as the inn's anchor.
    for dx in (-3.0, 0.6):
        dm = M.Group()
        face = M.box(1.5, 1.35, 0.20, 0.012, "plaster", uv_scale=0.8)
        face.translate(0, 0.67, 0)
        dm.add(face)
        cheek = M.prism([(-0.75, 0), (0.75, 0), (0, 0.70)], 0.16, chamfer=0.008)
        cheek.translate(0, 1.35, 0)
        dm.add(cheek.with_material("plaster"))
        droof = K.gable_roof(1.9, 1.5, f"{asset_id}.dorm{dx}", pitch=0.95, overhang=0.22)
        droof.translate(0, 1.32, 0.2)
        dm.add(droof)
        w = K.leaded_window(f"{asset_id}.dw{dx}", width=0.72, height=0.82)
        w.translate(0, 0.72, -0.14)
        dm.add(w)
        dm.translate(dx, y3 + 0.55, -D2 * 0.5 + 1.15)
        ctx.emit(dm)

    # --- chimneys, both smoking -----------------------------------------
    # Stacks must clear the RIDGE, and the ridge sits higher than a naive
    # D2/2*pitch suggests because gable_roof adds the overhang to the span.
    # Caught by the build-time occlusion check after a first fix that still
    # left both stacks 0.3m short.
    ridge_h = ((D2 + 1.0) * 0.5) * pitch
    for i, cx in enumerate((-W2 * 0.32, W2 * 0.34)):
        # A stack further down the slope needs to be TALLER to clear the
        # ridge, not shorter — the first attempt had this backwards.
        ch_h = ridge_h + 1.6 + i * 0.35
        ch = K.chimney(f"{asset_id}.ch{i}", height=ch_h, section=0.72)
        ch.translate(cx, y3 - 0.2, rng.uniform(-0.6, 0.6))
        ctx.emit(ch, label=f"inn chimney {i}")
        ctx.entity(f"{asset_id}.chimney.{i+1:02d}", "prop.chimney",
                   (cx, y3 - 0.2 + ch_h, 0), cell="E3",
                   smoke={"rate": 0.6, "drift": [0.8, 0, 0.5]})

    # --- sign -------------------------------------------------------------
    sign = _heron_sign(f"{asset_id}.sign")
    sign.translate(door_x - 2.35, y0 + 2.70, zf - 0.14)
    ctx.emit(sign)

    # --- residue: Art Bible §7 -------------------------------------------
    # Boots by the door, a cat on the sill, a bench, a barrel, a mounting block.
    for i in range(2):
        boot = M.lathe([(0.055, 0), (0.062, 0.16), (0.050, 0.22)], 8, "oak_weathered")
        boot.rotate_z(rng.uniform(-0.25, 0.25))
        boot.translate(door_x - 0.85 + i * 0.17, y0, zf - 0.30 + rng.uniform(-0.05, 0.05))
        ctx.emit(boot)

    cat = M.Group()
    cbody = M.lathe([(0.0, 0), (0.075, 0.05), (0.085, 0.24), (0.05, 0.34)], 8, "oak_weathered")
    cbody.rotate_z(np.pi * 0.5)
    cat.add(cbody)
    chead = M.lathe([(0.0, 0), (0.055, 0.04), (0.0, 0.09)], 8, "oak_weathered")
    chead.rotate_z(np.pi * 0.5)
    chead.translate(0.40, 0.03, 0)
    cat.add(chead)
    cat.rotate_y(0.5)
    cat.translate(win_g[0][0] - 0.25, y0 + win_g[0][1] - 0.62, zf - 0.02)
    ctx.emit(cat)

    bench = K.bench(f"{asset_id}.bench", length=2.1)
    bench.translate(door_x + 3.4, y0, zf - 0.65)
    ctx.emit(bench)

    bar = K.barrel(f"{asset_id}.barrel")
    bar.translate(-W * 0.5 + 0.7, y0, zf - 0.55)
    ctx.emit(bar)

    # Mounting block — travellers arrive on horseback, so the inn has one.
    for i, h in enumerate((0.20, 0.40)):
        st = M.box(0.80 - i * 0.18, 0.20, 0.55 - i * 0.10, 0.02, "stone", uv_scale=1.0)
        st.translate(W * 0.5 - 1.5, h - 0.10 + y0, zf - 0.75)
        ctx.emit(st)

    lam = K.lantern(f"{asset_id}.lantern", scale=1.15)
    lam.translate(door_x - 0.95, y0 + 2.35, zf - 0.08)
    ctx.emit(lam)
    ctx.entity(f"{asset_id}.lantern.01", "prop.lantern",
               (door_x - 0.95, y0 + 2.35, zf), cell="E3",
               light={"color": "#FFB35C", "intensity": 1.8, "range": 7.0})
