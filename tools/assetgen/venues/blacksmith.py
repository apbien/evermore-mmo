"""Blacksmith — the most ACTIVE venue in Hearthmere.

Sited at the town edge for fire risk, which is why Smith's Lane narrows and
turns to cinder before it gets here. That siting is not decoration: it is why
the venue exists where it does, and the dirt floor and scorched posts follow
from it.

The forge is the town's only significant emissive surface and its strongest
light source. Everything here is arranged the way a working smith arranges a
shop — by WORKFLOW, not by symmetry: fire, then anvil within a pace of it, then
quench within a pace of the anvil, with the tool rack at the smith's back hand.

Open-fronted: roofed but not walled, which is both the correct historical form
and far better for gameplay, since the player can see the work from the lane.
"""

from __future__ import annotations

import numpy as np

from core import mesh as M
from core import kit as K
from core.mathx import rng_for
from core.venue import VenueContext

NAME = "blacksmith"
CELLS = ["B5", "B6"]

YARD_W, YARD_D = 9.5, 7.5
POST_H = 3.05


def _forge(ctx, asset_id):
    """Stone hearth with a live coal fire. The town's only real emissive."""
    out = M.Group()

    # Raised hearth — a smith works standing, so the fire is at waist height.
    base = M.box(2.5, 0.78, 1.35, 0.03, "stone", uv_scale=0.9)
    base.translate(0, 0.39, 0)
    out.add(base)
    lip = M.box(2.62, 0.14, 1.46, 0.025, "stone", uv_scale=0.9)
    lip.translate(0, 0.82, 0)
    out.add(lip)

    # Fire bed. `coal` carries the emissive channel.
    rng = rng_for(asset_id, "coals")
    for i in range(48):
        a = rng.uniform(0, 6.283)
        d = rng.uniform(0.0, 0.52) ** 0.7
        c = M.box(rng.uniform(0.06, 0.13), rng.uniform(0.04, 0.09),
                  rng.uniform(0.06, 0.12), 0.012, "coal")
        c.rotate_y(rng.uniform(0, 3.14))
        c.translate(np.cos(a) * d * 1.5, 0.90 + rng.uniform(-0.01, 0.03),
                    np.sin(a) * d * 0.8)
        out.add(c)

    # Hood and flue carrying smoke up to the chimney.
    hood = M.prism([(-1.35, 0), (1.35, 0), (0.42, 1.15), (-0.42, 1.15)], 1.5,
                   chamfer=0.02)
    hood.translate(0, 1.55, 0)
    out.add(hood.with_material("stone"))
    stack = M.box(1.0, 2.6, 1.0, 0.025, "stone", uv_scale=0.7)
    stack.translate(0, 4.0, 0)
    out.add(stack)
    cap = M.box(1.25, 0.18, 1.25, 0.02, "stone", uv_scale=0.7)
    cap.translate(0, 5.35, 0)
    out.add(cap)

    ctx.entity(f"{asset_id}", "crafting_station.forge", (0, 0.9, 0), cell="B5",
               verbs=["use"],
               crafting_station={"profession": "blacksmith", "tier": 1},
               light={"color": "#FF8C42", "intensity": 4.0, "range": 9.0,
                      "flickerHz": [8, 12]})
    return out


def _bellows(asset_id):
    """Great bellows — the thing that makes a forge a forge."""
    out = M.Group()
    for i, (w, y) in enumerate([(0.95, 0.0), (0.95, 0.30)]):
        board = M.prism([(-0.52, 0), (0.30, -0.26), (0.52, 0), (0.30, 0.26)], 0.05,
                        chamfer=0.008)
        board.rotate_x(np.pi * 0.5)
        board.translate(0, 1.05 + y, 0)
        out.add(board.with_material("oak_dark"))
    # Leather sides, pleated.
    for i in range(5):
        t = i / 4.0
        pl = M.lathe([(0.30 + t * 0.14, 0), (0.34 + t * 0.16, 0.055)], 10, "leather",
                     close_bottom=False, close_top=False)
        pl.scale(1.5, 1.0, 0.85)
        pl.translate(0.06, 1.09 + i * 0.055, 0)
        out.add(pl)
    handle = M.cylinder(0.035, 1.05, 7, 0.005, "oak_weathered")
    handle.rotate_z(np.pi * 0.5)
    handle.rotate_y(0.2)
    handle.translate(0.55, 1.42, 0)
    out.add(handle)
    nozzle = M.cylinder(0.05, 0.55, 8, 0.005, "iron")
    nozzle.rotate_z(-np.pi * 0.5)
    nozzle.translate(-0.55, 1.15, 0)
    out.add(nozzle)
    return out


def _anvil(ctx, asset_id):
    """Anvil on an oak stump. Working face at ~0.75m — knuckle height."""
    out = M.Group()
    # Stump: a section of trunk, checked and split from drying.
    stump = M.lathe([(0.30, 0), (0.28, 0.10), (0.29, 0.45), (0.27, 0.52)], 14, "oak_weathered")
    out.add(stump)

    # The anvil silhouette: horn, waist, body, heel. This shape is instantly
    # readable and does more for the venue than any texture.
    body = M.box(0.62, 0.16, 0.20, 0.012, "iron")
    body.translate(0, 0.68, 0)
    out.add(body)
    waist = M.box(0.30, 0.10, 0.15, 0.010, "iron")
    waist.translate(0, 0.58, 0)
    out.add(waist)
    foot = M.box(0.46, 0.07, 0.24, 0.010, "iron")
    foot.translate(0, 0.535, 0)
    out.add(foot)
    horn = M.lathe([(0.095, 0), (0.075, 0.10), (0.04, 0.22), (0.0, 0.28)], 10, "iron")
    horn.rotate_z(np.pi * 0.5)
    horn.translate(0.31, 0.68, 0)
    out.add(horn)

    ctx.entity(f"{asset_id}", "crafting_station.anvil", (0, 0.76, 0), cell="B5",
               verbs=["use"],
               crafting_station={"profession": "blacksmith", "tier": 1},
               collider={"shape": "box", "half": [0.35, 0.42, 0.18]})
    return out


def build(ctx: VenueContext, asset_id="hm.blacksmith"):
    rng = rng_for(asset_id, "smithy")

    # --- dirt and cinder floor -------------------------------------------
    # Not cobbled. This is a working yard, and the ground is beaten earth with
    # scale and cinder trodden into it.
    floor = M.quad(YARD_W + 1.5, YARD_D + 1.5, "dirt", uv_scale=0.4)
    floor.translate(0, 0.01, 0)
    ctx.emit(floor)

    # --- open-fronted shed ------------------------------------------------
    # Posts and a roof, no front wall: the player sees the work from the lane.
    for sx in (-1, 1):
        for sz in (-1, 1):
            p = M.box(0.26, POST_H, 0.26, 0.015, "oak_dark")
            p.translate(sx * YARD_W * 0.5, POST_H * 0.5, sz * YARD_D * 0.5)
            ctx.emit(p)
            # Knee braces at the head of each post.
            for d in ((0.5, 0), (0, 0.5)):
                br = M.plank(0.62, 0.11, 0.10, 0.008, "oak_dark")
                br.rotate_z(-0.785)
                if d[1]:
                    br.rotate_y(np.pi * 0.5)
                br.translate(sx * (YARD_W * 0.5 - d[0] * 0.42),
                             POST_H - 0.42,
                             sz * (YARD_D * 0.5 - d[1] * 0.42))
                ctx.emit(br)

    # Wall plates and tie beams.
    for sz in (-1, 1):
        pl = M.plank(YARD_W + 0.3, 0.22, 0.20, 0.012, "oak_dark")
        pl.translate(0, POST_H + 0.10, sz * YARD_D * 0.5)
        ctx.emit(pl)
    for i in range(4):
        tx = -YARD_W * 0.5 + (i + 0.5) * YARD_W / 4
        tie = M.plank(YARD_D + 0.3, 0.18, 0.16, 0.010, "oak_dark", grain_axis=1)
        tie.rotate_y(np.pi * 0.5)
        tie.translate(tx, POST_H + 0.10, 0)
        ctx.emit(tie)

    # Back and side walls, boarded rather than plastered — cheap, and it lets
    # the heat out.
    for sz in (1,):
        for i in range(int(YARD_W / 0.30)):
            bx = -YARD_W * 0.5 + (i + 0.5) * 0.30
            b = M.box(0.28, POST_H, 0.032, 0.005, "oak_weathered")
            b.rotate_z(rng.uniform(-0.006, 0.006))
            b.translate(bx, POST_H * 0.5, sz * YARD_D * 0.5)
            ctx.emit(b)

    roof = K.gable_roof(YARD_D + 0.5, YARD_W + 0.5, f"{asset_id}.roof",
                        pitch=0.95, overhang=0.30, tile_mat="terracotta")
    roof.rotate_y(np.pi * 0.5)
    roof.translate(0, POST_H + 0.20, 0)
    ctx.emit(roof)

    # --- the working triangle: fire, anvil, quench ------------------------
    forge = _forge(ctx, f"{asset_id}.forge.01")
    forge.translate(-1.5, 0, YARD_D * 0.5 - 1.5)
    ctx.emit(forge)
    # The forge flue stopped inside the shed: a smoke entity was declared with
    # no stack above the roofline for it to leave from. The forge chimney is
    # the venue's anchor silhouette, visible across town.
    stack = K.chimney(f"{asset_id}.stack", height=3.4, section=0.92)
    stack.translate(-1.5, POST_H + 1.5, YARD_D * 0.5 - 1.5)
    ctx.emit(stack)
    ctx.entity(f"{asset_id}.chimney.01", "prop.chimney",
               (-1.5, POST_H + 1.5 + 3.6, YARD_D * 0.5 - 1.5), cell="B5",
               smoke={"rate": 1.0, "drift": [0.8, 0, 0.5]})

    bel = _bellows(f"{asset_id}.bellows")
    bel.rotate_y(-0.15)
    bel.translate(-3.35, 0, YARD_D * 0.5 - 1.4)
    ctx.emit(bel)

    anvil = _anvil(ctx, f"{asset_id}.anvil.01")
    anvil.rotate_y(0.55)
    anvil.translate(0.35, 0, 0.55)          # one pace from the fire
    ctx.emit(anvil)

    # Quench barrel, water scummed and stagnant.
    q = K.barrel(f"{asset_id}.quench", height=0.78, belly=0.72)
    q.translate(1.95, 0, 1.35)
    ctx.emit(q)
    water = M.lathe([(0.0, 0.66), (0.33, 0.66)], 14, "glass",
                    close_bottom=False, close_top=False)
    water.translate(1.95, 0, 1.35)
    ctx.emit(water)
    # A half-finished blade left in the quench — residue, and a story.
    blade = M.box(0.06, 0.62, 0.014, 0.004, "iron")
    blade.rotate_x(0.35)
    blade.rotate_y(0.7)
    blade.translate(1.95, 0.72, 1.30)
    ctx.emit(blade)

    # --- tool rack, arranged by workflow ---------------------------------
    rack = M.Group()
    for sx in (-1, 1):
        p = M.box(0.09, 1.85, 0.09, 0.008, "oak_dark")
        p.translate(sx * 0.85, 0.92, 0)
        rack.add(p)
    for y in (1.30, 1.72):
        r = M.plank(1.80, 0.08, 0.07, 0.006, "oak_dark")
        r.translate(0, y, 0)
        rack.add(r)
    # Tongs and hammers, hung by size because that is how a smith finds them.
    for i in range(7):
        hx = -0.72 + i * 0.24
        ln = 0.42 + i * 0.055
        handle = M.cylinder(0.016, ln, 6, 0.003, "iron")
        handle.rotate_x(0.06)
        handle.translate(hx, 1.72 - ln, rng.uniform(-0.02, 0.02))
        rack.add(handle)
        if i % 2:
            head = M.box(0.10, 0.075, 0.075, 0.008, "iron")
            head.translate(hx, 1.72 - ln - 0.02, 0)
            rack.add(head)
    rack.translate(-3.1, 0, YARD_D * 0.5 - 0.45)
    ctx.emit(rack)

    # --- residue: Art Bible §7 -------------------------------------------
    # Coal heap, horseshoes, scorched post, apron on a hook, finished stock.
    for i in range(26):
        a = rng.uniform(0, 6.283)
        d = rng.uniform(0, 0.85) ** 0.6
        c = M.box(rng.uniform(0.07, 0.15), rng.uniform(0.05, 0.11),
                  rng.uniform(0.07, 0.14), 0.014, "oak_dark")
        c.rotate_y(rng.uniform(0, 3.14))
        c.translate(-4.0 + np.cos(a) * d, 0.05 + rng.uniform(0, 0.22),
                    YARD_D * 0.5 - 2.9 + np.sin(a) * d)
        ctx.emit(c)

    for i in range(9):
        sh = M.lathe([(0.055, 0), (0.075, 0.018)], 10, "iron",
                     close_bottom=False, close_top=False)
        sh.scale(1.0, 1.0, 0.75)
        sh.rotate_y(rng.uniform(0, 3.14))
        sh.translate(2.9 + rng.uniform(-0.3, 0.3), 0.02 + i * 0.019,
                     -0.4 + rng.uniform(-0.3, 0.3))
        ctx.emit(sh)

    apron = M.box(0.52, 0.78, 0.02, 0.006, "leather")
    apron.rotate_z(0.06)
    apron.translate(YARD_W * 0.5 - 0.18, 1.55, YARD_D * 0.5 - 1.9)
    ctx.emit(apron)

    # Finished bar stock leaning in a corner.
    for i in range(6):
        bar = M.cylinder(0.022, rng.uniform(1.5, 2.0), 6, 0.004, "iron")
        bar.rotate_z(rng.uniform(0.12, 0.2))
        bar.rotate_y(rng.uniform(0, 3.14))
        bar.translate(YARD_W * 0.5 - 0.7 + rng.uniform(-0.15, 0.15), 0,
                      YARD_D * 0.5 - 0.8 + rng.uniform(-0.15, 0.15))
        ctx.emit(bar)

    # Grindstone on a frame.
    gr = M.Group()
    wheel = M.lathe([(0.0, 0), (0.34, 0.0), (0.34, 0.075), (0.0, 0.075)], 18, "stone")
    wheel.rotate_z(np.pi * 0.5)
    gr.add(wheel)
    for sx in (-1, 1):
        leg = M.prism([(-0.22, 0), (0.22, 0), (0.05, 0.62), (-0.05, 0.62)], 0.06, chamfer=0.005)
        leg.translate(0, 0, sx * 0.24)
        gr.add(leg.with_material("oak_weathered"))
    gr.translate(3.4, 0.62, 2.1)
    ctx.emit(gr)

    # Water trough for quenching stock and for the horses being shod.
    tr = M.box(1.5, 0.45, 0.62, 0.025, "oak_weathered")
    tr.translate(-YARD_W * 0.5 + 0.9, 0.225, -YARD_D * 0.5 + 1.1)
    ctx.emit(tr)
