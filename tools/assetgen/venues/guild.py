"""Adventurer's Guild — Hearthmere's hero building.

The guild reads as **imported**: an outside organisation with outside money,
the only cut stone and the only symmetry in a town of crooked timber cottages.

But imported must not mean ECCLESIASTICAL. The first pass landed on a small
parish church — vertical mass, all ashlar, pointed lancets, a conical spire
and a gabled porch. Every one of those cues is a church cue, and nothing in
the silhouette said "an organisation that sends armed people into danger".

The reference is the anime/MMO guild hall, which is the opposite shape:

  - HORIZONTAL, not vertical. A broad mead-hall mass that hugs the ground.
    Height comes from one stocky WATCHTOWER, not a spire.
  - Stone base, TIMBER above. Pure ashlar reads institutional; a jettied
    timber upper storey reads as a hall people live and work in.
  - Square-headed mullioned windows. The pointed arch was doing most of the
    church work on its own.
  - A wide, heavy double door — an entrance a party walks through together,
    not a chapel door.
  - A large heraldic device over the entrance. Guilds advertise.
  - Visible WORK: a training yard with pells and weapon racks, open to the
    street, so the building's function is legible without entering it.

Art Bible §2 still applies: the device is a carved emblem, never lettering.

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

# Broad and low. Was 14.0 x 10.5 with a 5.2 x 15.5m tower — a 3:1 vertical
# slab that read as a church steeple. A guild hall is a horizontal mass with a
# stocky lookout, so the hall widened and the tower got shorter and fatter.
HALL_W, HALL_D = 19.0, 11.5
HALL_H = 4.6            # stone storey; timber storey sits above it
UPPER_H = 3.1           # jettied timber upper floor
TOWER_W, TOWER_H = 6.4, 11.0


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


def _banner(asset_id, width=2.10, height=6.40, sway=0.05, mat="banner"):
    """Hanging banner as ONE continuous displaced surface.

    Previously 72 independent flat boxes on a grid. Boxes cannot share normals
    across their seams, so every panel edge caught the light differently and
    the cloth read as horizontal striping — the defect survived two review
    rounds because the fix attempted was overlap, which cannot help: the
    problem is that a box has six faces and a hanging cloth has one.

    Built instead as a single smooth-shaded quad grid, displaced by a catenary
    sag across the width and a wind-lift that grows toward the free lower
    corner, with normals derived from the actual surface. That is what makes it
    read as heavy dyed wool rather than as slats.
    """
    rng = rng_for(asset_id, "banner")
    COLS, ROWS = 14, 30

    def surface(u, v):
        """u across the width (0..1), v down the drop (0..1)."""
        x = (u - 0.5) * width
        y = -v * height
        # Catenary across the width, deepening down the drop as the cloth
        # takes its own weight.
        bow = np.sin(u * np.pi) * 0.13 * (0.30 + v)
        # Wind lifts the free lower corner, not the fixed top edge.
        lift = (v ** 2.2) * 0.55 * np.sin(u * np.pi * 0.85 + 0.5)
        z = -bow - lift * 0.45
        y += lift * 0.30
        # Fine wrinkling so the surface is never geometrically flat.
        z += np.sin(u * 9.0 + v * 5.0) * 0.012 * v
        return np.array([x, y, z], np.float32)

    b = M._Builder()
    for j in range(ROWS):
        for i in range(COLS):
            u0, u1 = i / COLS, (i + 1) / COLS
            v0, v1 = j / ROWS, (j + 1) / ROWS
            p00, p10 = surface(u0, v0), surface(u1, v0)
            p11, p01 = surface(u1, v1), surface(u0, v1)
            # Smooth normal from the surface itself, shared across the quad, so
            # neighbouring quads agree and no seam catches light.
            n = np.cross(p10 - p00, p01 - p00)
            ln = float(np.linalg.norm(n))
            n = n / ln if ln > 1e-9 else np.array([0, 0, -1], np.float32)
            # NORMALISED 0..1, not metres. banner_cloth carries a directional
            # top-to-bottom gradient (sun-bleached at the hanging edge, dirty
            # at the hem). Mapping in metres tiled that gradient 6.4x down the
            # drop and produced the horizontal banding that survived two review
            # rounds — the seams were never the cause, and rebuilding the mesh
            # as one surface could not have fixed it.
            uvs = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
            b.poly([p00, p10, p11, p01], uvs, n)
    out = M.Group().add(b.build(mat))

    # Hanging pole with finials. rotate_z(+pi/2) maps +Y onto -X, so centring
    # needs a POSITIVE half-length offset.
    pole = M.cylinder(0.042, width + 0.40, 10, 0.005, "iron")
    pole.rotate_z(np.pi * 0.5)
    pole.translate((width + 0.40) * 0.5, 0.07, 0)
    out.add(pole)
    for sx in (-1, 1):
        f = M.lathe([(0.0, 0), (0.055, 0.05), (0.03, 0.12)], 10, "iron")
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

    # --- jettied TIMBER upper storey -------------------------------------
    # Stone base, timber above. Pure ashlar to the eaves is what made the first
    # pass read institutional; a jettied timber storey reads as a hall that
    # people work and sleep in, and matches the inn's construction so the guild
    # belongs to Hearthmere even while standing apart from it.
    y_up = 0.55 + HALL_H
    y_eaves = y_up + UPPER_H
    jt = K.jetty(HALL_W, HALL_D, 0.38)
    jt.translate(0, y_up, 0)
    ctx.emit(jt)
    UW, UD = HALL_W + 0.76, HALL_D + 0.76
    for sz in (-1, 1):
        wl = K.timber_frame_wall(UW, UPPER_H, f"{asset_id}.up{sz}", style="close",
                                 sill_y=0)
        if sz > 0:
            wl.rotate_y(np.pi)
        wl.translate(0, y_up, sz * UD * 0.5)
        ctx.emit(wl)
    for sx in (-1, 1):
        wl = K.timber_frame_wall(UD, UPPER_H, f"{asset_id}.ups{sx}", style="close",
                                 sill_y=0)
        wl.rotate_y(sx * np.pi * 0.5)
        wl.translate(sx * UW * 0.5, y_up, 0)
        ctx.emit(wl)
    for i, wx in enumerate((-6.2, -2.1, 2.1, 6.2)):
        w_ = K.leaded_window(f"{asset_id}.upw{i}", width=1.05, height=1.15,
                             mat="glass_lit" if i % 2 else "glass",
                             shutters=(i % 3 == 0), shutter_mat="painted")
        w_.translate(wx, y_up + UPPER_H * 0.5, -UD * 0.5 - 0.06)
        ctx.emit(w_)

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

    # WIDE, heavy double doors standing open — an entrance a party walks
    # through together. Chapel doors are tall and narrow; hall doors are broad.
    for sx in (-1, 1):
        d = K.plank_door(f"{asset_id}.door{sx}", width=1.85, height=3.10,
                         mat="oak_dark", open_angle=sx * rng.uniform(0.85, 1.05))
        d.translate(sx * 1.85, 0.62, zf + 0.05)
        ctx.emit(d)

    # Big carved heraldic device over the entrance. Guilds advertise; a church
    # does not. Pictorial only per Art Bible §2 — a shield carrying the crossed
    # blades and the town heron, no lettering anywhere.
    shield = M.prism([(-0.95, 0.85), (0.95, 0.85), (0.95, -0.15),
                      (0.55, -0.75), (0.0, -1.05), (-0.55, -0.75), (-0.95, -0.15)],
                     0.20, chamfer=0.02)
    shield.translate(0, 0.55 + PORCH_H + 1.15, zf - PORCH_D - 0.28)
    ctx.emit(shield.with_material("painted_crimson"))
    rim_ = M.prism([(-1.05, 0.95), (1.05, 0.95), (1.05, -0.18),
                    (0.62, -0.84), (0.0, -1.17), (-0.62, -0.84), (-1.05, -0.18)],
                   0.12, chamfer=0.015)
    rim_.translate(0, 0.55 + PORCH_H + 1.15, zf - PORCH_D - 0.20)
    ctx.emit(rim_.with_material("iron"))
    for sgn in (-1, 1):                       # crossed blades on the device
        bl = M.box(0.10, 1.45, 0.05, 0.008, "iron")
        bl.rotate_z(sgn * 0.62)
        bl.translate(0, 0.55 + PORCH_H + 1.20, zf - PORCH_D - 0.40)
        ctx.emit(bl)
    hrn = M.lathe([(0.0, 0), (0.14, 0.09), (0.16, 0.28), (0.0, 0.44)], 10, "ashlar")
    hrn.translate(0, 0.55 + PORCH_H + 0.95, zf - PORCH_D - 0.46)
    ctx.emit(hrn)
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
            # Full-height merlons. These were 0.62m — half height — which is
            # why they read as nicks rather than as crenellation.
            m_ = M.box(per / n_m * 0.9, 1.05, 0.38, 0.018, "ashlar", uv_scale=0.7)
            if side % 2:
                m_.rotate_y(np.pi * 0.5)
                m_.translate(tx + (per * 0.5 - 0.19) * (1 if side == 1 else -1),
                             TOWER_H + 0.83, tz + off)
            else:
                m_.translate(tx + off, TOWER_H + 0.83,
                             tz + (per * 0.5 - 0.19) * (1 if side == 0 else -1))
            ctx.emit(m_)

    # Tall lancet openings up the tower — vertical rhythm, and they read as
    # arrow-slits softened into windows by a town that was never besieged.
    for i in range(2):
        y = 4.6 + i * 3.6
        for szz in (-1, 1):
            # Proud of the wall face, not inside it. At z-offset 0.20 these sat
            # within the 0.5m wall thickness and rendered nothing. They now
            # carry a label so the occlusion tripwire tests them — its docstring
            # names this exact bug as its motivation, but they were untested.
            # SQUARE-HEADED and mullioned, not a lancet. A tall narrow opening
            # under a pointed head is a church window; a wide square one under a
            # heavy stone lintel is a hall window.
            sl = M.box(1.15, 0.95, 0.22, 0.012, "glass_lit")
            sl.translate(tx, y, tz + szz * (TOWER_W * 0.5 + 0.02))
            ctx.emit(sl, label=f"tower window {i}{szz}")
            mull = M.box(0.11, 0.95, 0.26, 0.010, "ashlar", uv_scale=0.9)
            mull.translate(tx, y, tz + szz * (TOWER_W * 0.5 + 0.03))
            ctx.emit(mull)
            for oy in (-1, 1):
                lint = M.box(1.55, 0.20, 0.30, 0.014, "ashlar", uv_scale=0.8)
                lint.translate(tx, y + oy * 0.58, tz + szz * (TOWER_W * 0.5 + 0.02))
                ctx.emit(lint)

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
    # NO CONE. A conical cap on a corner turret is a steeple, and it was the
    # single loudest church cue on the building. The turret gets a flat
    # battlemented head instead — a lookout somebody stands on.
    lookout = M.lathe([(1.34, TOWER_H + 2.05), (1.34, TOWER_H + 2.28)], 8, "ashlar")
    ctx.emit(lookout.translate(turr_x, 0, turr_z))
    for k in range(8):
        a = k * np.pi * 0.25
        if k % 2:
            continue
        mer = M.box(0.62, 0.72, 0.30, 0.02, "ashlar", uv_scale=0.7)
        mer.rotate_y(-a)
        mer.translate(turr_x + np.sin(a) * 1.18, TOWER_H + 2.64, turr_z + np.cos(a) * 1.18)
        ctx.emit(mer)
    # A brazier up there instead of a finial: this is a signal point, not a spire.
    braz = M.lathe([(0.0, 0), (0.26, 0.10), (0.30, 0.30), (0.22, 0.36)], 10, "iron")
    ctx.emit(braz.translate(turr_x, TOWER_H + 2.28, turr_z))
    coals = M.lathe([(0.0, 0.30), (0.24, 0.30)], 10, "coal",
                    close_bottom=False, close_top=False)
    ctx.emit(coals.translate(turr_x, TOWER_H + 2.28, turr_z))
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
    # NO rotate_y here. Rotating put the ridge PARALLEL to the facade, so from
    # the approach the bay added a horizontal band rather than the gable
    # triangle that breaks the eaves line. The gable must face the street.
    bay_roof = K.gable_roof(BAY_W + 0.5, BAY_D + 0.9, f"{asset_id}.bayroof",
                            pitch=1.05, overhang=0.35)
    bay_roof.translate(0, 0.55 + BAY_H, -HALL_D * 0.5 - BAY_D * 0.5)
    ctx.emit(bay_roof)
    bay_gable = K.gable_end(BAY_W + 0.5, 0.55 + BAY_H, 1.05, mat="ashlar", depth=0.4)
    bay_gable.translate(0, 0, -HALL_D * 0.5 - BAY_D - 0.15)
    ctx.emit(bay_gable)

    # Buttresses only on the stone base, and shallow. Tall stepped buttresses
    # are a church cue; a low plinth spur reads as ordinary heavy construction.
    for sx in (-1, 1):
        for i in range(2):
            bz = -HALL_D * 0.28 + i * HALL_D * 0.28
            for k, (bw, bh, bd) in enumerate([(0.85, HALL_H * 0.55, 0.80)]):
                b = M.box(bw, bh, bd, 0.022, "ashlar", uv_scale=0.6)
                b.translate(sx * (HALL_W * 0.5 + bd * 0.5 - 0.22 - k * 0.12),
                            0.55 + (0 if k == 0 else HALL_H * 0.62) + bh * 0.5, bz)
                ctx.emit(b)
            cap_ = M.prism([(-0.34, 0), (0.34, 0), (0.34, 0.09), (0, 0.24), (-0.34, 0.09)],
                           0.56, chamfer=0.01)
            cap_.rotate_y(np.pi * 0.5)
            cap_.translate(sx * (HALL_W * 0.5 + 0.20), 0.55 + HALL_H * 0.55, bz)
            ctx.emit(cap_.with_material("ashlar"))

    # A chimney on the hall — the guild has hearths, and a roofline with no
    # stack reads as a model kit.
    hch = K.chimney(f"{asset_id}.hallchimney",
                    height=((UD + 1.3) * 0.5) * 0.62 + 1.5, section=0.86)
    hch.translate(-HALL_W * 0.26, y_eaves - 0.2, 0.7)
    ctx.emit(hch, label="guild hall chimney")
    ctx.entity(f"{asset_id}.chimney.01", "prop.chimney",
               (-HALL_W * 0.26, y_eaves + 4.2, 0.7), cell="C2",
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
    roll = M.lathe([(0.13, 0), (0.14, 0.62)], 10, "cloth_brown")
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

    # --- training yard ----------------------------------------------------
    # The single strongest identity cue available, and the thing the first pass
    # lacked entirely: VISIBLE WORK. A player walking past should be able to
    # tell what this organisation does without going in. Open to the street,
    # fenced only waist-high.
    YX, YZ = HALL_W * 0.5 + 4.0, -2.6
    yard = M.Group()

    # Beaten-earth ring, scuffed bare by boots.
    ring = M.quad(8.0, 7.5, "dirt", uv_scale=0.45)
    ring.translate(YX, 0.012, YZ)
    yard.add(ring)

    # Pells — the posts you actually hit. Hacked, splintered, leaning.
    for i, (px, pz) in enumerate([(-2.3, -1.6), (0.1, -2.1), (2.4, -1.2)]):
        pell = M.cylinder(0.17, rng.uniform(1.55, 1.80), 10, 0.012, "oak_weathered")
        pell.rotate_z(rng.uniform(-0.05, 0.05))
        pell.translate(YX + px, 0, YZ + pz)
        yard.add(pell)
        # Hack marks: chips taken out around head and body height.
        for k in range(int(rng.integers(4, 8))):
            a = rng.uniform(0, 6.283)
            ch = M.box(rng.uniform(0.05, 0.12), rng.uniform(0.03, 0.07), 0.09, 0.006,
                       "oak_dark")
            ch.rotate_y(a)
            ch.translate(YX + px + np.cos(a) * 0.16, rng.uniform(0.85, 1.55),
                         YZ + pz + np.sin(a) * 0.16)
            yard.add(ch)

    # Weapon rack along the street edge — the read from outside.
    rack = M.Group()
    for sx in (-1, 1):
        p_ = M.box(0.12, 1.70, 0.12, 0.010, "oak_dark")
        p_.translate(sx * 1.55, 0.85, 0)
        rack.add(p_)
    for yy in (0.65, 1.50):
        r_ = M.plank(3.20, 0.10, 0.09, 0.006, "oak_dark")
        r_.translate(0, yy, 0)
        rack.add(r_)
    for i in range(7):
        wx = -1.30 + i * 0.43
        if i == 3:
            continue                          # a gap: someone took theirs out
        shaft = M.cylinder(0.030, rng.uniform(1.75, 2.05), 7, 0.004, "oak_weathered")
        shaft.rotate_z(rng.uniform(0.07, 0.15))
        shaft.translate(wx, 0, rng.uniform(-0.03, 0.03))
        rack.add(shaft)
        if i % 2:
            head = M.prism([(0, 0), (0.11, 0.17), (0.0, 0.36), (-0.08, 0.15)], 0.035,
                           chamfer=0.004)
            head.translate(wx + 0.20, 1.78, 0)
            rack.add(head.with_material("iron"))
    rack.rotate_y(0.06)
    rack.translate(YX - 0.4, 0, YZ - 2.9)
    yard.add(rack)

    # Straw target butts.
    for i, (bx, bz) in enumerate([(3.3, 1.9), (3.3, 3.2)]):
        butt = M.lathe([(0.0, 0), (0.52, 0.06), (0.58, 0.34), (0.50, 0.62),
                        (0.0, 0.70)], 14, "thatch")
        butt.rotate_x(-0.22)
        butt.translate(YX + bx, 0.30, YZ + bz)
        yard.add(butt)
        for k in range(int(rng.integers(2, 5))):   # arrows still in it
            arw = M.cylinder(0.014, 0.62, 5, 0.003, "oak_weathered")
            arw.rotate_x(np.pi * 0.5 - 0.22)
            arw.rotate_y(rng.uniform(-0.2, 0.2))
            arw.translate(YX + bx + rng.uniform(-0.22, 0.22),
                          0.55 + rng.uniform(-0.18, 0.18), YZ + bz - 0.45)
            yard.add(arw)

    # Waist-high rail: encloses without hiding. A solid wall would defeat it.
    for i in range(9):
        fx = YX - 3.9 + i * 1.05
        post = M.box(0.13, 1.05, 0.13, 0.010, "oak_weathered")
        post.rotate_y(rng.uniform(-0.03, 0.03))
        post.translate(fx, 0.52, YZ - 3.6)
        yard.add(post)
        if i < 8:
            rl = M.plank(1.18, 0.09, 0.07, 0.006, "oak_weathered")
            rl.translate(fx + 0.575, 0.86, YZ - 3.6)
            yard.add(rl)
    ctx.emit(yard)
    ctx.entity(f"{asset_id}.trainingyard.01", "prop.training_yard",
               (YX, 0, YZ), cell="D2", verbs=["use"],
               crafting_station={"profession": "combat", "tier": 1})

    # Reception counter visible through the open doors.
    counter = M.box(2.6, 1.05, 0.62, 0.012, "oak_dark", uv_scale=1.2)
    counter.translate(0.6, 0.55 + 0.525, zf + 3.6)
    ctx.emit(counter, label="guild counter")
    ctx.entity(f"{asset_id}.counter.01", "vendor.guild", (0.6, 1.08, zf + 3.6),
               cell="C2", verbs=["talk"])
