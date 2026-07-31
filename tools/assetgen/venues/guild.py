"""Adventurer's Guild — Hearthmere's hero building.

The guild reads as **imported**. Where the rest of the town is timber frame
and lime plaster built by locals over generations, the guild is dressed ashlar
with a square tower, put up by an outside organisation with outside money. It
is the only symmetrical building in Hearthmere, and the only one whose stone
was cut rather than gathered.

That contrast does the storytelling. A player who has walked past six crooked
timber cottages reads "this is not from here" without being told.

Composition:
  - The tower is the anchor silhouette — visible from the north gate, and the
    thing that tells an arriving player where to go.
  - The quest board under the porch is the single most important interactable
    in the town, so it gets hero-class detail.
  - Crimson banners supply the only strong saturated colour on the building,
    which is why they read as identity rather than decoration.
"""

from __future__ import annotations

import numpy as np

from core import mesh as M
from core import kit as K
from core.mathx import rng_for
from core.venue import VenueContext

NAME = "guild"
CELLS = ["C2", "D2"]

HALL_W, HALL_D = 14.0, 10.5
HALL_H = 6.2
TOWER_W, TOWER_H = 5.2, 15.5


def _quoin_column(height, block_h=0.42, mat="ashlar", size=0.40, seed_id="q"):
    """Alternating long/short corner quoins.

    Dressed corners are the cheapest possible signal of expensive masonry, and
    the alternating rhythm is what makes them read as quoins rather than as a
    column of identical bricks.
    """
    rng = rng_for(seed_id, "quoin")
    out = M.Group()
    n = int(height / block_h)
    for i in range(n):
        long_side = (i % 2 == 0)
        w = size * (1.45 if long_side else 0.95)
        d = size * (0.95 if long_side else 1.45)
        b = M.box(w, block_h * 0.97, d, 0.018, mat, uv_scale=0.7)
        b.translate(rng.uniform(-0.006, 0.006), block_h * (i + 0.5),
                    rng.uniform(-0.006, 0.006))
        out.add(b)
    return out


def _quest_board(ctx, asset_id):
    """The most important interactable in Hearthmere.

    What sells it is the LAYERING and the age spread: notices pinned over other
    notices, some crisp and square, some sun-bleached and curling off the board,
    torn corners where a job was taken. A tidy grid of identical parchment reads
    as a UI element, not as a thing people use every day.

    Art Bible §2: no readable lettering. Notices carry marks, wax seals and
    ribbon only.
    """
    rng = rng_for(asset_id, "questboard")
    out = M.Group()

    # Frame and backing boards.
    for i in range(6):
        p = M.plank(2.30, 0.30, 0.045, 0.005, "oak_weathered")
        p.translate(0, 0.90 + i * 0.30, 0)
        out.add(p)
    for sx in (-1, 1):
        post = M.box(0.16, 2.60, 0.16, 0.012, "oak_dark")
        post.translate(sx * 1.20, 1.30, 0)
        out.add(post)
    head = M.plank(2.72, 0.20, 0.16, 0.012, "oak_dark")
    head.translate(0, 2.62, 0)
    out.add(head)
    # Small pent roof — the notices are outdoors, so they need cover.
    roof = M.prism([(-1.45, 0), (1.45, 0), (1.45, 0.06), (-1.45, 0.06)], 0.62, chamfer=0.008)
    roof.rotate_x(-0.32)
    roof.translate(0, 2.76, -0.20)
    out.add(roof.with_material("oak_dark"))

    # Notices. Age drives everything: colour, curl, and how square it is.
    for i in range(17):
        age = rng.uniform(0.0, 1.0)
        w = rng.uniform(0.17, 0.29)
        h = rng.uniform(0.20, 0.32)
        n = M.box(w, h, 0.004, 0.001, "parchment")
        # Old notices curl off the board and hang crooked.
        n.rotate_z(rng.uniform(-0.06, 0.06) - age * rng.uniform(0.0, 0.22))
        n.rotate_x(-age * rng.uniform(0.0, 0.28))
        n.translate(rng.uniform(-1.02, 1.02),
                    1.02 + rng.uniform(0.0, 1.42),
                    -0.028 - rng.uniform(0.0, 0.012))
        out.add(n)

        # Iron pin holding it, and a wax seal on about half of them.
        pin = M.lathe([(0.010, 0), (0.014, 0.006), (0.008, 0.012)], 6, "iron")
        pin.rotate_x(-np.pi * 0.5)
        pin.translate(n.bounds()[0][0] + w * 0.5, n.bounds()[1][1] - 0.03, -0.042)
        out.add(pin)
        if rng.random() < 0.5:
            seal = M.lathe([(0.0, 0), (0.020, 0.004), (0.017, 0.009)], 8, "wax")
            seal.rotate_x(-np.pi * 0.5)
            seal.translate(n.bounds()[0][0] + w * 0.5,
                           n.bounds()[0][1] + 0.05, -0.040)
            out.add(seal)

    ctx.entity(f"{asset_id}", "quest_board", (0, 0, 0), cell="C2",
               verbs=["read"],
               quest_board={"notices": [], "capacity": 20},
               collider={"shape": "box", "half": [1.35, 1.30, 0.12]})
    return out


def _banner(asset_id, width=2.10, height=6.40, sway=0.05):
    """Hanging banner with a weighted, wind-lifted lower edge.

    A flat rectangle reads as cardboard. The curve across the width and the
    lift at the free corner are what make it read as heavy cloth.
    """
    rng = rng_for(asset_id, "banner")
    out = M.Group()
    rows, cols = 12, 6
    for r in range(rows):
        for c in range(cols):
            t_r, t_c = r / rows, c / cols
            # Catenary sag across the width, growing toward the free lower edge.
            bow = np.sin(t_c * np.pi) * 0.10 * (0.35 + t_r)
            lift = (t_r ** 2) * rng.uniform(0.10, 0.24) * np.sin(t_c * np.pi + 0.6)
            # Generous overlap: each panel is tilted by its own lift, which
            # opens a seam against its neighbour. At 1.02 those seams read as
            # venetian-blind striping across the cloth.
            panel = M.box(width / cols * 1.06, height / rows * 1.35, 0.012, 0.0, "banner")
            panel.rotate_x(-lift * 0.28)
            panel.translate(-width * 0.5 + (c + 0.5) * width / cols,
                            -(r + 0.5) * height / rows,
                            -bow - lift * 0.4)
            out.add(panel)
    # Hanging pole with finials.
    # rotate_z(+pi/2) maps +Y onto -X, so the bar runs from the origin toward
    # -X. Offsetting by +half its length is what actually centres it on the
    # banner; offsetting by -half pushes it clear of the cloth entirely.
    pole = M.cylinder(0.042, width + 0.40, 8, 0.005, "iron")
    pole.rotate_z(np.pi * 0.5)
    pole.translate((width + 0.40) * 0.5, 0.07, 0)
    out.add(pole)
    for sx in (-1, 1):                       # finials
        f = M.lathe([(0.0, 0), (0.055, 0.05), (0.03, 0.12)], 8, "iron")
        f.translate(sx * (width + 0.40) * 0.5, 0.07, 0)
        out.add(f)
    out.rotate_z(sway)
    return out


def build(ctx: VenueContext, asset_id="hm.guild"):
    rng = rng_for(asset_id, "guild")

    # --- plinth ----------------------------------------------------------
    plinth = M.box(HALL_W + 0.9, 0.55, HALL_D + 0.9, 0.03, "ashlar", uv_scale=0.55)
    plinth.translate(0, 0.275, 0)
    ctx.emit(plinth)

    # --- hall walls ------------------------------------------------------
    # Solid ashlar, unlike every other building in town.
    #
    # The FRONT wall is built in segments around a real door aperture. Built as
    # one solid box, the "always open" double doors hung against unbroken stone
    # and the reception counter behind them was entombed — the classic
    # "it's a facade, not a building" tell.
    DOOR_W_OPEN, DOOR_H_OPEN = 3.4, 3.30
    for sz in (-1, 1):
        if sz == -1:
            side_w = (HALL_W - DOOR_W_OPEN) * 0.5
            for sx in (-1, 1):
                w = M.box(side_w, HALL_H, 0.55, 0.02, "ashlar", uv_scale=0.55)
                w.translate(sx * (DOOR_W_OPEN * 0.5 + side_w * 0.5),
                            0.55 + HALL_H * 0.5, sz * (HALL_D * 0.5 - 0.275))
                ctx.emit(w)
            # Wall over the opening.
            over_h = HALL_H - DOOR_H_OPEN
            w = M.box(DOOR_W_OPEN, over_h, 0.55, 0.02, "ashlar", uv_scale=0.55)
            w.translate(0, 0.55 + DOOR_H_OPEN + over_h * 0.5,
                        sz * (HALL_D * 0.5 - 0.275))
            ctx.emit(w)
        else:
            w = M.box(HALL_W, HALL_H, 0.55, 0.02, "ashlar", uv_scale=0.55)
            w.translate(0, 0.55 + HALL_H * 0.5, sz * (HALL_D * 0.5 - 0.275))
            ctx.emit(w)

    # Interior shell: a dark box inside the hall. Without it the open door and
    # every opening look straight through to sunlit exterior plaster and sky,
    # which reads as an empty stage set. In Gridania every opening is lit,
    # dark, or shuttered — never wall, and never daylight from the far side.
    inner = M.box(HALL_W - 1.2, HALL_H - 0.2, HALL_D - 1.2, 0.02, "oak_dark",
                  uv_scale=0.5)
    inner.scale(-1.0, 1.0, 1.0)      # flip inward so we see its inside faces
    inner.translate(0, 0.55 + (HALL_H - 0.2) * 0.5, 0)
    ctx.emit(inner, shell=True)
    for sx in (-1, 1):
        w = M.box(0.55, HALL_H, HALL_D - 1.1, 0.02, "ashlar", uv_scale=0.55)
        w.translate(sx * (HALL_W * 0.5 - 0.275), 0.55 + HALL_H * 0.5, 0)
        ctx.emit(w)

    # Quoins at every hall corner.
    for sx in (-1, 1):
        for sz in (-1, 1):
            q = _quoin_column(HALL_H + 0.4, seed_id=f"{asset_id}.q{sx}{sz}")
            q.translate(sx * HALL_W * 0.5, 0.55, sz * HALL_D * 0.5)
            ctx.emit(q)

    # String course — the horizontal band that stops a tall wall reading blank.
    band = M.box(HALL_W + 0.5, 0.22, HALL_D + 0.5, 0.02, "ashlar", uv_scale=0.6)
    band.translate(0, 0.55 + HALL_H * 0.62, 0)
    ctx.emit(band)

    # --- entrance: recessed porch, tall double doors ---------------------
    # The porch recess is what gives the facade depth and puts the quest board
    # in shadow, which makes the parchment read.
    PORCH_W, PORCH_D, PORCH_H = 5.0, 1.9, 4.3
    zf = -HALL_D * 0.5
    for sx in (-1, 1):                       # porch side walls
        w = M.box(0.45, PORCH_H, PORCH_D, 0.02, "ashlar", uv_scale=0.6)
        w.translate(sx * (PORCH_W * 0.5 - 0.225), 0.55 + PORCH_H * 0.5, zf - PORCH_D * 0.5)
        ctx.emit(w)
    lintel = M.box(PORCH_W + 0.9, 0.62, PORCH_D + 0.3, 0.025, "ashlar", uv_scale=0.6)
    lintel.translate(0, 0.55 + PORCH_H + 0.31, zf - PORCH_D * 0.5)
    ctx.emit(lintel)

    # Keystone carrying the town's grey heron. Pictorial, never lettered.
    key = M.prism([(-0.26, 0), (0.26, 0), (0.20, 0.52), (-0.20, 0.52)], 0.30, chamfer=0.012)
    key.translate(0, 0.55 + PORCH_H + 0.10, zf - PORCH_D - 0.16)
    ctx.emit(key.with_material("ashlar"))
    heron = M.lathe([(0.0, 0), (0.07, 0.05), (0.08, 0.15), (0.0, 0.24)], 10, "ashlar")
    heron.translate(0, 0.55 + PORCH_H + 0.22, zf - PORCH_D - 0.30)
    ctx.emit(heron)

    # Threshold, dished by decades of boots.
    thr = M.box(PORCH_W - 0.6, 0.14, 1.0, 0.03, "ashlar", uv_scale=0.9)
    thr.translate(0, 0.60, zf - PORCH_D + 0.2)
    ctx.emit(thr)

    # Tall double doors, standing open — the guild never closes.
    for sx in (-1, 1):
        d = K.plank_door(f"{asset_id}.door{sx}", width=1.30, height=3.10,
                         mat="oak_dark", open_angle=sx * rng.uniform(0.85, 1.05))
        d.translate(sx * 1.30, 0.62, zf + 0.05)
        ctx.emit(d)
    ctx.entity(f"{asset_id}.door.01", "door.guild", (0, 0.62, zf), cell="C2",
               verbs=["enter"])

    # --- quest board, under the porch -----------------------------------
    qb = _quest_board(ctx, f"{asset_id}.questboard.01")
    qb.translate(-PORCH_W * 0.5 - 1.75, 0.55, zf - 0.34)
    ctx.emit(qb)

    # --- tower -----------------------------------------------------------
    tx, tz = HALL_W * 0.5 - TOWER_W * 0.5 + 0.6, -HALL_D * 0.5 + TOWER_W * 0.5 - 0.6
    for sxx in (-1, 1):
        w = M.box(0.5, TOWER_H, TOWER_W, 0.02, "ashlar", uv_scale=0.5)
        w.translate(tx + sxx * (TOWER_W * 0.5 - 0.25), TOWER_H * 0.5, tz)
        ctx.emit(w)
    for szz in (-1, 1):
        w = M.box(TOWER_W - 1.0, TOWER_H, 0.5, 0.02, "ashlar", uv_scale=0.5)
        w.translate(tx, TOWER_H * 0.5, tz + szz * (TOWER_W * 0.5 - 0.25))
        ctx.emit(w)
    for sxx in (-1, 1):
        for szz in (-1, 1):
            q = _quoin_column(TOWER_H, seed_id=f"{asset_id}.tq{sxx}{szz}")
            q.translate(tx + sxx * TOWER_W * 0.5, 0, tz + szz * TOWER_W * 0.5)
            ctx.emit(q)

    # Corbelled parapet with merlons — the tower's read against the sky.
    cor = M.box(TOWER_W + 0.7, 0.30, TOWER_W + 0.7, 0.025, "ashlar", uv_scale=0.6)
    cor.translate(tx, TOWER_H + 0.15, tz)
    ctx.emit(cor)
    per = TOWER_W + 0.7
    n_m = 5
    for side in range(4):
        for i in range(n_m):
            if i % 2:
                continue
            off = -per * 0.5 + (i + 0.5) * per / n_m
            m_ = M.box(per / n_m * 0.9, 0.62, 0.34, 0.018, "ashlar", uv_scale=0.7)
            if side % 2:
                m_.rotate_y(np.pi * 0.5)
                m_.translate(tx + (per * 0.5 - 0.17) * (1 if side == 1 else -1),
                             TOWER_H + 0.61, tz + off)
            else:
                m_.translate(tx + off, TOWER_H + 0.61,
                             tz + (per * 0.5 - 0.17) * (1 if side == 0 else -1))
            ctx.emit(m_)

    # Tall lancet openings up the tower — vertical rhythm, and they read as
    # arrow-slits softened into windows by a town that was never besieged.
    for i in range(3):
        y = 4.4 + i * 3.4
        for szz in (-1, 1):
            sl = M.box(0.42, 1.55, 0.16, 0.012, "glass")
            sl.translate(tx, y, tz + szz * (TOWER_W * 0.5 - 0.20))
            ctx.emit(sl)

    # --- secondary silhouette tier ---------------------------------------
    # The massing reviewed as "two rectangles and a triangle": one hall box,
    # one tower slab, one roof, with half-height merlons as the only break in
    # the outline. Art Bible §6 requires a secondary tier that reads at 30m.
    # These are the elements that break it.

    # Octagonal stair turret clasping the tower corner and oversailing it.
    # A turret is the single most effective silhouette-breaker on any tower:
    # it reads as a different mass, it is round against square, and it rises
    # past the parapet so the outline steps twice.
    # Front-facing corner: on the rear corner the turret was fully occluded
    # by the tower from the approach, which is the view that matters.
    turr_x = tx - TOWER_W * 0.5
    turr_z = tz - TOWER_W * 0.5
    turret = M.lathe([(1.05, 0.0), (1.05, TOWER_H + 1.5),
                      (1.22, TOWER_H + 1.75), (1.18, TOWER_H + 2.05)],
                     8, "ashlar")
    ctx.emit(turret.translate(turr_x, 0, turr_z))
    # Conical cap — the only cone in Hearthmere, so it reads instantly.
    cap = M.lathe([(1.22, TOWER_H + 2.05), (0.92, TOWER_H + 3.10),
                   (0.42, TOWER_H + 3.95), (0.0, TOWER_H + 4.35)], 8, "terracotta")
    ctx.emit(cap.translate(turr_x, 0, turr_z))
    # Finial.
    fin = M.lathe([(0.10, 0), (0.14, 0.14), (0.05, 0.30), (0.03, 0.62)], 8, "iron")
    ctx.emit(fin.translate(turr_x, TOWER_H + 4.30, turr_z))
    # Slit windows spiralling up the turret, following the stair inside.
    for i in range(6):
        a = 0.9 + i * 0.85
        sl = M.box(0.26, 0.68, 0.30, 0.010, "glass")
        sl.rotate_y(a)
        sl.translate(turr_x + np.sin(a) * 1.02, 3.0 + i * 2.05,
                     turr_z + np.cos(a) * 1.02)
        ctx.emit(sl)

    # Projecting entrance bay with its own gable, stepping the hall front
    # forward. Without it the facade is a single unbroken plane.
    BAY_W, BAY_D, BAY_H = 6.4, 1.25, 5.4
    for sx in (-1, 1):
        w = M.box(0.5, BAY_H, BAY_D, 0.02, "ashlar", uv_scale=0.6)
        w.translate(sx * (BAY_W * 0.5 - 0.25), 0.55 + BAY_H * 0.5,
                    -HALL_D * 0.5 - BAY_D * 0.5)
        ctx.emit(w)
    bay_face = M.box(BAY_W, BAY_H - PORCH_H - 0.62, 0.5, 0.02, "ashlar", uv_scale=0.6)
    bay_face.translate(0, 0.55 + PORCH_H + 0.62 + (BAY_H - PORCH_H - 0.62) * 0.5,
                       -HALL_D * 0.5 - BAY_D + 0.25)
    ctx.emit(bay_face)
    bay_roof = K.gable_roof(BAY_D + 0.9, BAY_W + 0.5, f"{asset_id}.bayroof",
                            pitch=1.05, overhang=0.35)
    bay_roof.rotate_y(np.pi * 0.5)
    bay_roof.translate(0, 0.55 + BAY_H, -HALL_D * 0.5 - BAY_D * 0.5)
    ctx.emit(bay_roof)
    bay_gable = K.gable_end(BAY_D + 0.9, 0.55 + BAY_H, 1.05, mat="ashlar", depth=0.4)
    bay_gable.rotate_y(np.pi * 0.5)
    bay_gable.translate(0, 0, -HALL_D * 0.5 - BAY_D * 0.5)
    ctx.emit(bay_gable)

    # Stepped buttresses down the hall flanks — vertical rhythm against a long
    # blank wall, and they cast the shadow bars that give the wall depth.
    for sx in (-1, 1):
        for i in range(3):
            bz = -HALL_D * 0.28 + i * HALL_D * 0.28
            for k, (bw, bh, bd) in enumerate([(0.75, HALL_H * 0.62, 0.95),
                                              (0.62, HALL_H * 0.30, 0.72)]):
                b = M.box(bw, bh, bd, 0.022, "ashlar", uv_scale=0.6)
                b.translate(sx * (HALL_W * 0.5 + bd * 0.5 - 0.22 - k * 0.12),
                            0.55 + (0 if k == 0 else HALL_H * 0.62) + bh * 0.5, bz)
                ctx.emit(b)
            # Weathered slope on top of each buttress.
            cap_ = M.prism([(-0.31, 0), (0.31, 0), (0.31, 0.10), (0, 0.34), (-0.31, 0.10)],
                           0.62, chamfer=0.01)
            cap_.rotate_y(np.pi * 0.5)
            cap_.translate(sx * (HALL_W * 0.5 + 0.24), 0.55 + HALL_H * 0.92, bz)
            ctx.emit(cap_.with_material("ashlar"))

    # A chimney on the hall — the guild has hearths, and a roofline with no
    # stack reads as a model kit.
    hch = K.chimney(f"{asset_id}.hallchimney",
                    height=(HALL_D * 0.5) * 0.72 + 1.3, section=0.78)
    hch.translate(-HALL_W * 0.26, 0.55 + HALL_H - 0.2, 0.7)
    ctx.emit(hch, label="guild hall chimney")
    ctx.entity(f"{asset_id}.chimney.01", "prop.chimney",
               (-HALL_W * 0.26, 0.55 + HALL_H + 4.2, 0.7), cell="C2",
               smoke={"rate": 0.5, "drift": [0.8, 0, 0.5]})

    # --- banners ---------------------------------------------------------
    # The only strong saturated colour on the building.
    # _banner builds in the XY plane, so an unrotated banner faces -Z. Each one
    # must be rotated to match the tower face it hangs on AND pushed clear of
    # that face — the first pass left one buried inside the tower volume and
    # rotated the other edge-on to the camera, so neither read at all.
    #
    # -Z face: faces the arriving player coming down Ford Road. This is the one
    # that has to carry the guild's identity from the north gate.
    b = _banner(f"{asset_id}.banner0", sway=rng.uniform(-0.05, 0.05))
    b.translate(tx, TOWER_H - 1.1, tz - TOWER_W * 0.5 - 0.10)
    ctx.emit(b)

    # -X face: seen from the market square side.
    b = _banner(f"{asset_id}.banner1", sway=rng.uniform(-0.05, 0.05))
    b.rotate_y(-np.pi * 0.5)
    b.translate(tx - TOWER_W * 0.5 - 0.10, TOWER_H - 1.1, tz)
    ctx.emit(b)

    # Banners flanking the entrance, hung on the projecting bay's face rather
    # than on the wall behind it — on the old flat facade they sat where the
    # bay now stands and read as pale slabs clipping through it.
    for sx in (-1, 1):
        b = _banner(f"{asset_id}.ebanner{sx}", width=0.85, height=2.4,
                    sway=rng.uniform(-0.04, 0.04))
        b.translate(sx * (BAY_W * 0.5 - 0.55), 0.55 + BAY_H - 0.85,
                    -HALL_D * 0.5 - BAY_D - 0.10)
        ctx.emit(b)

    # --- hall roof -------------------------------------------------------
    roof = K.gable_roof(HALL_D, HALL_W, f"{asset_id}.roof", pitch=0.72,
                        overhang=0.55, tile_mat="slate" if False else "terracotta")
    roof.rotate_y(np.pi * 0.5)
    roof.translate(0, 0.55 + HALL_H, 0)
    ctx.emit(roof)
    for sx in (-1, 1):
        g = K.gable_end(HALL_D, 0.55 + HALL_H, 0.72, mat="ashlar", depth=0.5)
        g.rotate_y(np.pi * 0.5)
        g.translate(sx * HALL_W * 0.5, 0, 0)
        ctx.emit(g)

    # --- residue: Art Bible §7 -------------------------------------------
    # Adventurers loiter here. The evidence of that is what stops the guild
    # reading as a monument.

    # Weapon rack by the door, half empty — people took their gear out.
    rack = M.Group()
    for sx in (-1, 1):
        p = M.box(0.10, 1.55, 0.10, 0.008, "oak_dark")
        p.translate(sx * 0.62, 0.78, 0)
        rack.add(p)
    for y in (0.55, 1.35):
        r = M.plank(1.34, 0.09, 0.08, 0.006, "oak_dark")
        r.translate(0, y, 0)
        rack.add(r)
    for i in range(4):
        if i == 2:
            continue                          # a gap: somebody is out on a job
        shaft = M.cylinder(0.028, 1.85, 7, 0.004, "oak_weathered")
        shaft.rotate_z(rng.uniform(0.10, 0.18))
        shaft.translate(-0.48 + i * 0.32, 0, rng.uniform(-0.03, 0.03))
        rack.add(shaft)
        head = M.prism([(0, 0), (0.10, 0.16), (0.0, 0.34), (-0.07, 0.14)], 0.03, chamfer=0.004)
        head.translate(-0.48 + i * 0.32 + 0.24, 1.80, 0)
        rack.add(head.with_material("iron"))
    rack.rotate_y(0.16)
    rack.translate(PORCH_W * 0.5 + 1.5, 0.55, zf - 0.7)
    ctx.emit(rack)

    # A pack and a bedroll dumped by the threshold.
    pack = K.sack(f"{asset_id}.pack", height=0.48)
    pack.translate(-PORCH_W * 0.5 + 0.5, 0.55, zf - 1.15)
    ctx.emit(pack)
    roll = M.lathe([(0.13, 0), (0.14, 0.62)], 10, "canvas")
    roll.rotate_z(np.pi * 0.5)
    roll.rotate_y(0.4)
    roll.translate(-PORCH_W * 0.5 + 1.15, 0.68, zf - 1.05)
    ctx.emit(roll)

    # Lantern on a bracket beside the doors.
    lam = K.lantern(f"{asset_id}.lantern")
    lam.translate(PORCH_W * 0.5 - 0.35, 0.55 + 2.5, zf - PORCH_D - 0.05)
    ctx.emit(lam)
    ctx.entity(f"{asset_id}.lantern.01", "prop.lantern",
               (PORCH_W * 0.5 - 0.35, 3.05, zf - PORCH_D - 0.05), cell="C2",
               light={"color": "#FFB35C", "intensity": 1.8, "range": 6.0})

    # Reception counter visible through the open doors.
    counter = M.box(2.6, 1.05, 0.62, 0.012, "oak_dark", uv_scale=1.2)
    counter.translate(0.6, 0.55 + 0.525, zf + 3.6)
    ctx.emit(counter, label="guild counter")
    ctx.entity(f"{asset_id}.counter.01", "vendor.guild", (0.6, 1.08, zf + 3.6),
               cell="C2", verbs=["talk"])
