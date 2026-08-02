"""The waggon shed — slot 38, Ford Road.

`docs/plan/schedule.md`: *"Waggon shed: five open bays, waggon poles up, a spare
axle on brackets and a broken wheel leaning where it fell. Carriers turn in the
yard beside it."*

Five bays, nothing in front of them, and that is the whole building. A waggon
shed is a roof and a row of posts because a waggon has to be backed in and
pulled out without unhitching, and the bay module is set by the width of a
waggon plus the room to walk down one side of it. Getting that module right is
what makes the row read as a place vehicles live rather than as a colonnade.

**Poles up.** A four-wheel waggon parked with its pole on the ground is a
tripping hazard and a rotted pole, so it is stood against the bay's own post.
Five raked poles at 60 degrees along a 13 m frontage is the single strongest
rhythm available in the craft quarter, and it costs five cylinders.

## Why it is a venue of its own

Slot 38 and slot 70 both read `kit: stables` in the schedule, and both used to
resolve to one venue id — so `tools/render/town.mjs`, which loads
`/assets/meshes/<venue.id>.gltf`, placed the SAME mesh twice: a 16 x 12 stable
range dropped onto a 14 x 8 waggon-shed plot at a different rotation. They are
different buildings doing different jobs 30 m apart. Split in `plan_data.py`
(`VENUE_OF_SLOT[38] = "waggon_shed"`) so the generator, the document and the
renderer agree.
"""

from __future__ import annotations

import numpy as np

from core import kit as K
from core import mesh as M
from core import props as P
from core import streetscape as S
from core.mathx import rng_for
from core.siting import Site
from core.venue import VenueContext

NAME = "waggon_shed"
SLOT = 38
CELLS = ["G4", "G5", "H4", "H5"]

ASSET = "hm.waggon_shed"

EAVES = 4.6
BAYS = 5


def build(ctx: VenueContext, asset_id=ASSET):
    p = Site(slot=SLOT, ctx=ctx, asset_id=asset_id)
    rng = rng_for(asset_id, "waggon")

    yard = M.box(p.w + 1.2, 0.10, p.d + 1.6, 0.035, "gravel",
                 uv_scale=ctx.uv_scale("gravel"))
    yard.translate(0, 0.05, 0)
    p.emit(yard)
    p.collider("box", center=(0, 0.05, 0),
               half=((p.w + 1.2) * 0.5, 0.05, (p.d + 1.6) * 0.5),
               kind="surface", tag="yard")

    # The turning: ruts swinging in off Ford Road and back out. The carriers'
    # yard is the reason this plot is the shape it is.
    for i in range(8):
        a = -1.05 + i * 0.27
        rt = M.box(2.4, 0.03, 0.30, 0.012, "mud_wet",
                   uv_scale=ctx.uv_scale("mud_wet"))
        rt.rotate_y(a * 0.8)
        rt.translate(np.sin(a) * 3.6, 0.108, p.front - 0.6 + np.cos(a) * 1.9)
        p.emit(rt)

    # ------------------------------------------------------------- the range
    RW = p.w - 0.6
    RD = p.d - 1.4
    rz = p.back - RD * 0.5
    body = K.open_range(
        f"{asset_id}.range", RW, RD, EAVES, pitch=0.74, overhang=0.70,
        roof_mat="terracotta", walls=("back", "left", "right"),
        plinth=0.0, board_gap=0.055, bays=BAYS, tag="waggon")
    body.translate(0, 0.10, rz)
    p.emit(body, container="range", shell=True)

    # Pad stones under the posts, and the floor left as beaten earth: a waggon
    # shed is never paved, because a paved floor is a floor a wheel skids on.
    for i in range(BAYS + 1):
        px = -RW * 0.5 + i * RW / BAYS
        for pz in (rz - RD * 0.5, rz + RD * 0.5):
            pad = M.box(0.50, 0.14, 0.50, 0.022, "stone",
                        uv_scale=ctx.uv_scale("stone"))
            pad.rotate_y(rng.uniform(-0.08, 0.08))
            pad.translate(px, 0.13, pz)
            p.emit(pad)
            p.collider("box", center=(px, 0.10 + EAVES * 0.5, pz),
                       half=(0.16, EAVES * 0.5, 0.16), tag="post")
    p.collider("box", center=(0, 0.10 + EAVES * 0.5, p.back - 0.10),
               half=(RW * 0.5 + 0.05, EAVES * 0.5, 0.11), tag="back_wall")
    for s in (-1, 1):
        p.collider("box", center=(s * RW * 0.5, 0.10 + EAVES * 0.5, rz),
                   half=(0.11, EAVES * 0.5, RD * 0.5), tag="side_wall")

    # ------------------------------------------------- what is in the bays
    bw = RW / BAYS
    # Bay 1 and 4 hold waggons; bay 2 a sledge; bay 3 stands EMPTY, because a
    # shed with every bay full is a shed nobody uses. Bay 5 is the wheelwright's
    # corner where the broken stock ends up.
    for i, (kind, load) in enumerate([("waggon", "barrels"), ("sledge", None),
                                      (None, None), ("waggon", "sacks"),
                                      (None, None)]):
        bx = -RW * 0.5 + (i + 0.5) * bw
        if kind == "waggon":
            w = P.waggon(f"{asset_id}.wag.{i}", length=3.4, width=1.55,
                         load=load)
            w.rotate_y(np.pi * 0.5 + rng.uniform(-0.05, 0.05))
            w.translate(bx + rng.uniform(-0.15, 0.15), 0.10, rz + 0.15)
            p.emit(w)
            p.collider("box", center=(bx, 0.10 + 0.75, rz + 0.15),
                       half=(0.90, 0.75, 1.80), tag="waggon")
            # POLE UP: stood against the bay's own post, which is where a
            # carter actually leaves it.
            pole = M.lathe([(0.055, 0), (0.048, 1.6), (0.036, 3.15)], 7,
                           "oak_weathered")
            pole.rotate_x(-0.30)
            pole.rotate_y(rng.uniform(-0.12, 0.12))
            pole.translate(bx - bw * 0.42, 0.10, rz - RD * 0.5 + 0.55)
            p.emit(pole)
        elif kind == "sledge":
            sl = P.sledge(f"{asset_id}.sledge", length=1.9, loaded="stone")
            sl.rotate_y(np.pi * 0.5 + 0.12)
            sl.translate(bx, 0.10, rz + 0.35)
            p.emit(sl)
            p.collider("box", center=(bx, 0.10 + 0.28, rz + 0.35),
                       half=(0.50, 0.28, 1.05), tag="sledge")

    # --- the wheelwright's corner ----------------------------------------
    EX = RW * 0.5 - bw * 0.5
    # A spare axle on brackets, up out of the wet.
    for s in (-1, 1):
        br = M.plank(0.42, 0.14, 0.10, 0.006, "oak_dark")
        br.rotate_y(np.pi * 0.5)
        br.translate(EX + s * 0.85, 0.10 + 1.42, p.back - 0.30)
        p.emit(br)
    axle = M.lathe([(0.075, 0), (0.062, 0.35), (0.062, 2.05), (0.075, 2.4)], 8,
                   "oak")
    axle.rotate_z(np.pi * 0.5)
    axle.translate(EX + 1.2, 0.10 + 1.52, p.back - 0.32)
    p.emit(axle)
    for s in (-1, 1):                          # the iron arms at each end
        ir = M.lathe([(0.048, 0), (0.036, 0.26)], 8, "iron_pitted")
        ir.rotate_z(s * np.pi * 0.5)
        ir.translate(EX + s * 1.22, 0.10 + 1.52, p.back - 0.32)
        p.emit(ir)

    # Wheels stacked flat, and the broken one leaning where it fell.
    for i in range(3):
        wh = P.cart_wheel(f"{asset_id}.wheel.{i}", dia=1.12 - i * 0.03)
        wh.rotate_x(np.pi * 0.5)
        wh.rotate_y(rng.uniform(0, 3.0))
        wh.translate(EX - 0.55, 0.14 + i * 0.10, rz + 0.95)
        p.emit(wh)
    p.collider("cylinder", center=(EX - 0.55, 0.10 + 0.16, rz + 0.95),
               radius=0.58, height=0.32, kind="surface", tag="wheel_stack")

    bw2 = P.broken_wheel(f"{asset_id}.broken", wall_z=p.back - 0.20,
                         x=EX + 0.35)
    bw2.translate(0, 0.10, 0)
    p.emit(bw2)

    # Tar and grease: what keeps a wheel on. A bucket of black tar with a
    # brush in it, and the grease pot, both under the bench where they live.
    tar = P.bucket(f"{asset_id}.tar", height=0.34, top=0.17, full=True,
                   mat="oak_weathered", liquid="water")
    tar.translate(EX + 1.05, 0.10, rz + 1.15)
    p.emit(tar)
    brush = M.Group()
    brush.add(M.tube((0, 0, 0), (0.10, 0.55, 0.06), 0.017, "oak_weathered", 5, 0.002))
    brush.add(M.box(0.09, 0.10, 0.05, 0.004, "sacking"))
    brush.translate(EX + 1.05, 0.10 + 0.28, rz + 1.15)
    p.emit(brush)

    # A tyre being sized: an iron hoop stood on edge against the back wall,
    # which is the wheelwright's most recognisable object after the wheel.
    ty = M.ring(0.58, 0.045, "iron_pitted", 22)
    ty.rotate_x(np.pi * 0.5)
    ty.translate(0, 0.58, 0)
    P.lean(ty, 1.16, 0.26, wall_z=p.back - 0.20, x=EX - 1.55,
           roll=rng.uniform(-0.04, 0.04))
    ty.translate(0, 0.10, 0)
    p.emit(ty)

    # ------------------------------------------------------------- residue
    for i, (bx2, bz, ang) in enumerate([(-RW * 0.5 + 0.55, rz + 1.20, 0.5),
                                        (-RW * 0.5 + 1.20, rz + 1.35, -0.9)]):
        c = P.crate(f"{asset_id}.crate.{i}", size=0.52, mat="oak")
        c.rotate_y(ang)
        c.translate(bx2, 0.10, bz)
        p.emit(c)
    hay = P.spill(f"{asset_id}.chaff", kind="grain", radius=0.85, density=0.7,
                  vessel=False)
    hay.translate(-RW * 0.5 + 2.1, 0.11, rz + 0.9)
    p.emit(hay)

    for i, (wx, wz, size) in enumerate([(0.0, rz - RD * 0.5 - 1.4, 5.0),
                                        (-3.0, p.front + 1.3, 3.4),
                                        (3.6, p.front + 1.8, 3.0)]):
        w = P.worn_patch(f"{asset_id}.wear.{i}", shape="path", size=size,
                         mat="mud_wet")
        w.rotate_y(rng.uniform(0, 3.0))
        w.translate(wx, 0.104, wz)
        p.emit(w)

    rail = S.hitching_rail(f"{asset_id}.rail", length=2.8, height=1.02)
    rail.rotate_y(0.10)
    rail.translate(-p.w * 0.5 + 2.0, 0.10, p.front + 0.65)
    p.emit(rail)
    for s in (-1, 1):
        p.collider("cylinder", center=(-p.w * 0.5 + 2.0 + s * 1.4, 0.10 + 0.51,
                                       p.front + 0.65),
                   radius=0.09, height=1.02, tag="rail_post")

    sp = S.spur_stone(f"{asset_id}.spur", height=0.62)
    sp.translate(p.w * 0.5 - 0.4, 0.10, p.front + 0.45)
    p.emit(sp)
    p.collider("cylinder", center=(p.w * 0.5 - 0.4, 0.10 + 0.31, p.front + 0.45),
               radius=0.22, height=0.62, tag="spur_stone")

    p.entity(f"{asset_id}.shed.01", "service.waggon_shed",
             (0.0, 0.10, rz), verbs=[],
             service={"kind": "haulage", "bays": BAYS})
