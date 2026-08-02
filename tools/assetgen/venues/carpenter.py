"""The carpenter and joiner — slot 34, Bakers' Row.

Next door but one to the cooper, and the two are the same argument made twice:
a wood trade needs air, light and a way to get a four-metre baulk in and out,
so it works under a roof that is not walled on the street side.

## What the venue has to prove

That timber arrives here as trees and leaves as buildings. The plot is read in
three bands from the street:

    SAWING     the great baulk up on its trestles under a lean-to, with the
               two-man pit saw hanging in its own kerf and the sawdust heaped
               under it. This is the anchor: it is 4.2 m of oak at head height
               and it reads from the far end of Bakers' Row.
    SEASONING  boards stacked IN STICK — every board separated from the one
               below by a cross-batten so the air gets at both faces. It is
               the single most recognisable thing in any timber yard and it is
               nine boxes and a rhythm.
    JOINING    the open range: benches, the half-jointed frame on trestles,
               the tool wall, and the finished work stacked by the door

## The saw pit that is not a pit

A real sawyer works over a pit with the pitman standing in it. This yard cannot
have one: `core/terrain.py` owns `height(x, z)` and a venue may not cut a hole
in it, so a modelled pit would be a box the terrain surface draws straight over
and the player would look into a filled trench — worse than not having one.

So this is the other historical form, trestle sawing: the baulk is carried up
on two cross-trestles and the pitman works at ground level under it. It is
correct, it is legible, and unlike a pit it reads from across the street
instead of only from directly above. Recorded as `D-CQ-1` in the report.
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

NAME = "carpenter"
SLOT = 34
CELLS = ["I8", "I9", "J8", "J9"]

ASSET = "hm.carpenter"

RANGE_D = 4.8
EAVES = 5.6
PITCH = 0.80


def _timber_in_stick(asset_id, boards=7, length=3.6, width=0.30, thick=0.055,
                     courses=6, mat="oak", stick_mat="oak_weathered"):
    """A board stack racked in stick. Ground origin, boards run along +X.

    "In stick" is the whole trade in one arrangement: every course of boards is
    separated from the one below by three cross-battens, so air passes both
    faces and the board dries without cupping. Stack them touching and you have
    firewood in two winters. The gaps are therefore not a modelling flourish —
    they are the reason the stack exists, and they are what makes it read as
    timber rather than as a crate.
    """
    rng = rng_for(asset_id, "instick")
    out = M.Group()
    # Bearers: the stack never sits on the ground.
    for i in range(3):
        bz = -width * (boards - 1) * 0.5 + i * width * (boards - 1) * 0.5
        b = M.plank(width * boards + 0.25, 0.14, 0.12, 0.008, stick_mat,
                    grain_axis=1)
        b.rotate_y(np.pi * 0.5)
        b.translate(-length * 0.5 + 0.4 + i * (length - 0.8) * 0.5, 0.07, 0)
        out.add(b)
    y = 0.14
    for c in range(courses):
        n = boards - (c // 3)
        run = width * n
        for i in range(n):
            bz = -run * 0.5 + (i + 0.5) * width
            bd = M.plank(length * rng.uniform(0.94, 1.0), width * 0.93,
                         thick * rng.uniform(0.85, 1.25), 0.005, mat)
            bd.rotate_y(rng.uniform(-0.010, 0.010))
            bd.translate(rng.uniform(-0.06, 0.06), y + thick * 0.5,
                         bz + rng.uniform(-0.008, 0.008))
            out.add(bd)
        y += thick + 0.005
        # Three sticks across, over the bearers.
        for i in range(3):
            st = M.plank(run + 0.1, 0.052, 0.030, 0.003, stick_mat, grain_axis=1)
            st.rotate_y(np.pi * 0.5)
            st.translate(-length * 0.5 + 0.4 + i * (length - 0.8) * 0.5,
                         y + 0.015, 0)
            out.add(st)
        y += 0.032
    return out


def _saw_trestle(asset_id, height=1.78, span=1.25):
    """One cross-trestle carrying a baulk. Ground origin, saddle on +X axis."""
    out = M.Group()
    for s in (-1, 1):
        out.add(M.tube((s * span * 0.5, 0.0, -0.62), (-s * 0.10, height, 0.10),
                       0.070, "oak_weathered", 6, 0.005))
        out.add(M.tube((s * span * 0.5, 0.0, 0.62), (-s * 0.10, height, -0.10),
                       0.070, "oak_weathered", 6, 0.005))
    saddle = M.plank(1.05, 0.20, 0.14, 0.008, "oak_dark", grain_axis=1)
    saddle.rotate_y(np.pi * 0.5)
    saddle.translate(0, height, 0)
    out.add(saddle)
    br = M.plank(span + 0.2, 0.13, 0.075, 0.006, "oak_weathered")
    br.translate(0, height * 0.42, 0)
    out.add(br)
    return out


def _pit_saw(asset_id, length=2.05, y_top=2.30, y_bot=0.35, x=0.0, z=0.0):
    """The two-man saw left standing in its own kerf. World-ish local origin.

    A pit saw hangs vertically in the cut with a tiller box on top and a box
    handle below, and it is left in the kerf between shifts because taking it
    out means starting the cut again. That is why it is here and not on the
    tool wall: it is the strongest possible statement that the job is half
    done.
    """
    out = M.Group()
    blade = M.box(0.115, y_top - y_bot, 0.0055, 0.001, "steel_blued")
    blade.translate(x, (y_top + y_bot) * 0.5, z)
    out.add(blade)
    # Tiller: the crossbar the top sawyer pulls on.
    til = M.plank(0.70, 0.09, 0.075, 0.005, "oak", grain_axis=1)
    til.rotate_y(np.pi * 0.5)
    til.translate(x, y_top + 0.06, z)
    out.add(til)
    for s in (-1, 1):
        out.add(M.tube((x, y_top + 0.06, z + s * 0.30),
                       (x, y_top + 0.30, z + s * 0.30), 0.028, "oak", 6, 0.003))
    # Box handle at the pitman's end.
    bh = M.box(0.16, 0.30, 0.15, 0.008, "oak")
    bh.translate(x, y_bot - 0.10, z)
    out.add(bh)
    out.add(M.tube((x - 0.20, y_bot - 0.10, z), (x + 0.20, y_bot - 0.10, z),
                   0.026, "oak_weathered", 6, 0.003))
    return out


def _tool_wall(asset_id, width=3.0, wall_z=0.0, y=1.05):
    """A joiner's tool wall: saws, augers, planes, squares — hung, in order.

    Ordered by use and by size because that is the only way a man finds a
    3/8 chisel without looking. The rack itself is two rails; everything hangs
    off pegs or sits on the lower rail, and nothing is on the floor, because a
    plane iron on a floor is a ruined plane iron.
    """
    rng = rng_for(asset_id, "toolwall")
    out = M.Group()
    for yy in (y, y + 0.74):
        r = M.plank(width, 0.085, 0.075, 0.006, "oak_dark")
        r.translate(0, yy, wall_z - 0.055)
        out.add(r)
    # Handsaws, graded, hanging by the handle.
    for i in range(4):
        x = -width * 0.5 + 0.30 + i * 0.28
        ln = 0.58 + i * 0.075
        bl = M.chamfered_prism([(0.0, 0.0), (ln, 0.055), (ln, 0.115),
                                (0.0, 0.175)], 0.0035, "steel_blued", 0.001)
        bl.rotate_z(-np.pi * 0.5)
        bl.rotate_y(np.pi * 0.5)
        bl.translate(x, y + 0.74 - ln - 0.10, wall_z - 0.10)
        out.add(bl)
        hd = M.chamfered_prism([(-0.055, 0), (0.055, 0), (0.075, 0.16),
                                (-0.075, 0.15)], 0.026, "oak_dark", 0.004)
        hd.rotate_y(np.pi * 0.5)
        hd.translate(x, y + 0.74 - 0.06, wall_z - 0.10)
        out.add(hd)
    # Augers and a brace, hung by their crank.
    for i in range(5):
        x = width * 0.5 - 0.90 + i * 0.145
        sh = M.tube((x, y + 0.70, wall_z - 0.09), (x, y + 0.70 - 0.42 - i * 0.05,
                                                   wall_z - 0.09),
                    0.011, "iron", 5, 0.001)
        out.add(sh)
        ey = M.ring(0.032, 0.010, "iron", 8)
        ey.rotate_x(np.pi * 0.5)
        ey.translate(x, y + 0.72, wall_z - 0.09)
        out.add(ey)
    # Planes on the lower rail, sole down and set back off the edge.
    for i in range(4):
        x = -width * 0.5 + 0.35 + i * 0.42 + rng.uniform(-0.03, 0.03)
        ln = 0.20 + i * 0.11
        bd = M.chamfered_prism([(-ln * 0.5, 0), (ln * 0.5, 0), (ln * 0.5, 0.075),
                                (-ln * 0.5, 0.075)], 0.062, "endgrain", 0.004)
        bd.rotate_y(rng.uniform(-0.06, 0.06))
        bd.translate(x, y + 0.055, wall_z - 0.16)
        out.add(bd)
        ir = M.box(0.048, 0.075, 0.006, 0.001, "steel_blued")
        ir.rotate_x(0.35)
        ir.translate(x, y + 0.11, wall_z - 0.16)
        out.add(ir)
    # A try square hung square, which is the joke every joiner's wall makes.
    sq = M.Group()
    sq.add(M.box(0.024, 0.30, 0.012, 0.002, "steel_blued"))
    sq.add(M.box(0.070, 0.024, 0.020, 0.002, "oak_dark").translate(0.023, -0.14, 0))
    sq.translate(width * 0.5 - 0.22, y + 0.55, wall_z - 0.075)
    out.add(sq)
    return out


def build(ctx: VenueContext, asset_id=ASSET):
    p = Site(slot=SLOT, ctx=ctx, asset_id=asset_id)
    rng = rng_for(asset_id, "carpenter")

    # ------------------------------------------------------------------ yard
    # `gravel`, not the cooper's pale chip and not the terrain's brown: a
    # timber yard is hardstanding because a four-metre baulk has to be dragged
    # across it in February. Giving each craft plot its own worked surface is
    # also the cheapest available answer to town-02 §11, which is that the
    # whole intramural ground is one brown.
    yard = M.box(p.w + 0.6, 0.10, p.d + 0.6, 0.035, "gravel",
                 uv_scale=ctx.uv_scale("gravel"))
    yard.translate(0, 0.05, 0)
    p.emit(yard)
    p.collider("box", center=(0, 0.05, 0),
               half=((p.w + 0.6) * 0.5, 0.05, (p.d + 0.6) * 0.5),
               kind="surface", tag="yard")
    kerb = M.box(p.w + 0.6, 0.13, 0.26, 0.02, "cobble",
                 uv_scale=ctx.uv_scale("cobble"))
    kerb.translate(0, 0.065, p.front - 0.16)
    p.emit(kerb)

    # ----------------------------------------------------------------- range
    rz = p.back - RANGE_D * 0.5
    body = K.open_range(
        f"{asset_id}.range", p.w - 0.8, RANGE_D, EAVES,
        pitch=PITCH, overhang=0.58, roof_mat="terracotta",
        walls=("back", "left"), half_boarded=("right",),
        plinth=0.22, plinth_mat="rubble", board_gap=0.05, tag="joiner")
    body.translate(0, 0.10, rz)
    p.emit(body, container="range", shell=True)

    fh = EAVES - 0.22
    p.collider("box", center=(0, 0.10 + 0.11, rz),
               half=((p.w - 0.8) * 0.5 + 0.12, 0.11, RANGE_D * 0.5 + 0.12),
               kind="surface", tag="joiner_floor")
    p.collider("box", center=(0, 0.32 + fh * 0.5, p.back - 0.10),
               half=((p.w - 0.8) * 0.5 + 0.05, fh * 0.5, 0.11), tag="back_wall")
    p.collider("box", center=(-(p.w - 0.8) * 0.5, 0.32 + fh * 0.5, rz),
               half=(0.11, fh * 0.5, RANGE_D * 0.5 + 0.05), tag="side_wall")
    p.collider("box", center=((p.w - 0.8) * 0.5, 0.32 + 0.62, rz),
               half=(0.09, 0.62, RANGE_D * 0.5), tag="side_screen")
    bays = 4
    for i in range(bays + 1):
        px = -(p.w - 0.8) * 0.5 + i * (p.w - 0.8) / bays
        p.collider("box", center=(px, 0.32 + fh * 0.5, rz - RANGE_D * 0.5),
                   half=(0.17, fh * 0.5, 0.17), tag="post")

    # ------------------------------------------------- SAWING: the lean-to
    # Four posts and a mono-pitch, tucked into the west end of the yard so the
    # 4.2 m baulk can be run in off the street without turning.
    # Pulled forward until its rear posts clear the range's own front line by
    # 0.65 m. The first pass had them standing inside the covered floor.
    LX, LZ = -3.9, -2.30           # centre of the sawing stage
    lean = M.Group()
    for sx in (-1, 1):
        for sz in (-1, 1):
            h = 3.55 if sz < 0 else 2.65      # falls toward the street
            po = M.box(0.20, h, 0.20, 0.012, "oak_dark")
            po.translate(sx * 2.55, h * 0.5, sz * 1.85)
            lean.add(po)
            p.collider("box", center=(LX + sx * 2.55, 0.10 + h * 0.5, LZ + sz * 1.85),
                       half=(0.14, h * 0.5, 0.14), tag="leanto_post")
    for sz, h in ((-1, 3.55), (1, 2.65)):
        pl = M.plank(5.5, 0.20, 0.18, 0.010, "oak_dark")
        pl.translate(0, h + 0.08, sz * 1.85)
        lean.add(pl)
    # The slope itself: boards, not tile. A lean-to over a saw is a rain hat.
    slope_len = float(np.hypot(3.7, 0.90))
    for i in range(14):
        bx = -2.75 + (i + 0.5) * 5.5 / 14
        bd = M.plank(slope_len, 0.40, 0.038, 0.005, "timber_grey", grain_axis=1)
        bd.rotate_y(np.pi * 0.5)
        bd.rotate_x(float(np.arctan2(0.90, 3.7)))
        bd.translate(bx, 3.14, 0.0)
        lean.add(bd)
    for i in range(4):                        # purlins under it
        pu = M.plank(5.4, 0.11, 0.11, 0.006, "oak_dark")
        pu.translate(0, 3.48 - i * 0.24, -1.55 + i * 1.05)
        lean.add(pu)
    lean.translate(LX, 0.10, LZ)
    p.emit(lean, container="leanto", shell=True)

    # The baulk on its trestles: 4.2 m of oak, half converted.
    for s in (-1, 1):
        tr = _saw_trestle(f"{asset_id}.trestle.{s}", height=1.78)
        tr.rotate_y(0.04 * s)
        tr.translate(LX + s * 1.55, 0.10, LZ)
        p.emit(tr)
        p.collider("box", center=(LX + s * 1.55, 0.10 + 0.89, LZ),
                   half=(0.62, 0.89, 0.30), tag="saw_trestle")

    baulk = M.chamfered_prism([(-0.24, 0), (0.24, 0), (0.26, 0.46), (-0.22, 0.48)],
                              4.2, "oak", 0.012)
    baulk.rotate_y(np.pi * 0.5)
    baulk.rotate_z(0.012)
    baulk.translate(LX + 0.15, 0.10 + 1.80, LZ)
    p.emit(baulk)
    # The kerf: a slot already run 2.1 m in from the near end.
    kerf = M.box(2.10, 0.50, 0.014, 0.001, "oak_dark")
    kerf.translate(LX - 0.90, 0.10 + 2.03, LZ)
    p.emit(kerf)
    p.emit(_pit_saw(f"{asset_id}.pitsaw", y_top=0.10 + 2.62, y_bot=0.10 + 1.05,
                    x=LX + 0.18, z=LZ))
    p.collider("box", center=(LX + 0.15, 0.10 + 2.03, LZ),
               half=(2.15, 0.26, 0.28), tag="baulk")

    # The sawdust under it — a cone, because that is what falls out of a kerf.
    # `sand`, not `flour`: the first pass used the baker's flour heap and three
    # white domes under the trestles read as snow, not sawdust.
    # A scatter, not a heap: `spill` builds a smooth cone and three of those
    # under the trestles read as sand dunes. What falls out of a kerf is a
    # drift of chips, so it is `shavings` with a wide radius and a dense count.
    dust = P.shavings(f"{asset_id}.sawdust", 70, 1.30, 0.95, "oak")
    dust.translate(LX - 0.35, 0.10, LZ + 0.15)
    p.emit(dust)
    for i in range(3):
        wedge = M.chamfered_prism([(0, 0), (0.30, 0.055), (0.0, 0.075)], 0.075,
                                  "oak_dark", 0.003)
        wedge.rotate_y(rng.uniform(0, 3.14))
        wedge.translate(LX + rng.uniform(-1.2, 1.2), 0.11,
                        LZ + rng.uniform(-1.2, 1.2))
        p.emit(wedge)

    p.entity(f"{asset_id}.sawpit.01", "crafting_station.sawpit",
             (LX, 0.10, LZ), verbs=["use"],
             crafting_station={"profession": "carpenter", "tier": 1})

    # -------------------------------------------- SEASONING: timber in stick
    # Two racks along the plot's south-east, where the sun and the wind get at
    # them and where they are out of the way of a baulk being run in.
    for i, (sx, sz, ln, bo, co, ang) in enumerate([
            (4.35, 2.05, 3.6, 7, 6, 0.06), (5.35, -1.65, 3.0, 6, 5, -0.05)]):
        st = _timber_in_stick(f"{asset_id}.stick.{i}", boards=bo, length=ln,
                              courses=co)
        st.rotate_y(np.pi * 0.5 + ang)
        st.translate(sx, 0.10, sz)
        p.emit(st)
        p.collider("box", center=(sx, 0.10 + 0.42, sz),
                   half=(0.52 * bo * 0.5 + 0.1, 0.42, ln * 0.5),
                   rot_y=ang, tag="timber_stack")

    # Round timber waiting to be converted, chocked so it cannot roll. A yard
    # with sawn boards and no logs has no upstream.
    for i, (lx, lz, ln, r) in enumerate([(-0.4, 4.05, 3.2, 0.28),
                                         (-0.4, 3.35, 2.8, 0.24),
                                         (0.9, 3.95, 2.4, 0.21)]):
        lg = M.lathe([(r, 0), (r * 0.97, ln * 0.4), (r * 0.90, ln)], 10, "oak")
        lg.rotate_z(np.pi * 0.5)
        lg.rotate_y(rng.uniform(-0.05, 0.05))
        lg.translate(lx - ln * 0.5, 0.10 + r, lz)
        p.emit(lg)
        p.collider("cylinder", center=(lx, 0.10 + r, lz), radius=r,
                   height=r * 2, tag="log")
        for s in (-1, 1):
            ch = M.chamfered_prism([(-0.12, 0), (0.12, 0), (0.0, 0.13)], 0.16,
                                   "oak_weathered", 0.005)
            ch.translate(lx + s * ln * 0.36, 0.10, lz + 0.02)
            p.emit(ch)

    # ------------------------------------------------- JOINING: the range
    bench = P.dress_workbench(f"{asset_id}.bench", trade="carpenter", length=2.6,
                              wall_z=1.15, ctx=None)
    bench.rotate_y(0.10)
    bench.translate(1.35, 0.32, rz + 0.55)
    p.emit(bench)
    p.collider("box", center=(1.35, 0.32 + 0.44, rz + 1.65), half=(1.30, 0.44, 0.34),
               tag="workbench")

    p.emit(_tool_wall(f"{asset_id}.tools", width=3.2, wall_z=p.back - 0.13,
                      y=1.18).translate(-1.75, 0.32, 0))

    p.entity(f"{asset_id}.station.01", "crafting_station.carpenter",
             (1.35, 0.32, rz + 0.55), verbs=["use"],
             crafting_station={"profession": "carpenter", "tier": 1})

    # A second bench with the half-jointed frame, out at the drip line where
    # the light is. `carpenter_bench` is the shared library's version of this
    # and it already carries the mortise cut, the tenon offered up and the
    # marking gauge lying where the line was struck.
    frame = P.carpenter_bench(f"{asset_id}.frame", length=2.6, wall_z=0.0)
    frame.rotate_y(-0.22)
    frame.translate(-0.55, 0.10, rz - RANGE_D * 0.5 - 1.05)
    p.emit(frame)
    p.collider("box", center=(-0.55, 0.10 + 0.42, rz - RANGE_D * 0.5 - 1.05),
               half=(1.35, 0.42, 0.48), rot_y=-0.22, tag="trestle_frame")

    # Finished work, stacked by the way out: door leaves and a window frame,
    # which is the only place in the venue where anything is square and tidy.
    for i in range(3):
        leaf = M.Group()
        for j in range(4):
            bd = M.plank(1.94, 0.24, 0.036, 0.005, "oak")
            bd.rotate_z(np.pi * 0.5)
            bd.translate(-0.36 + j * 0.24, 0.97, 0)
            leaf.add(bd)
        for yy in (0.42, 1.52):
            lg = M.plank(0.98, 0.13, 0.030, 0.004, "oak_dark")
            lg.translate(0, yy, -0.032)
            leaf.add(lg)
        P.lean(leaf, 1.94, 0.30 + i * 0.09, wall_z=p.back - 0.16,
               x=5.05 - i * 0.06, roll=rng.uniform(-0.02, 0.02))
        leaf.translate(0, 0.32, 0)
        p.emit(leaf)
    p.collider("box", center=(5.05, 0.32 + 0.95, p.back - 0.42),
               half=(0.60, 0.95, 0.34), tag="door_leaves")

    # A chair with a broken leg brought in to be mended, and the new leg beside
    # it. Repair work is most of a village joiner's living and nothing else in
    # the venue says so.
    ch = P.chair(f"{asset_id}.chair", cloak=False)
    ch.rotate_y(2.5)
    ch.rotate_z(0.28)
    ch.translate(3.55, 0.32, rz + 1.35)
    p.emit(ch)
    newleg = M.lathe([(0.030, 0), (0.042, 0.10), (0.032, 0.30), (0.040, 0.44)],
                     8, "oak")
    newleg.rotate_z(np.pi * 0.47)
    newleg.translate(3.15, 0.36, rz + 1.05)
    p.emit(newleg)

    # ------------------------------------------------------------- residue
    for i, (sx, sz, n, rx, rz2) in enumerate([(1.35, rz + 0.10, 52, 1.6, 1.1),
                                              (-0.6, rz - RANGE_D * 0.5 - 1.1, 40, 1.4, 0.9),
                                              (-2.2, -3.1, 20, 1.6, 1.2)]):
        sh = P.shavings(f"{asset_id}.shav.{i}", n, rx, rz2, "oak")
        sh.translate(sx, 0.11 if i == 2 else 0.33, sz)
        p.emit(sh)

    offc = M.Group()
    for i in range(22):
        ln = rng.uniform(0.16, 0.52)
        oc = M.plank(ln, rng.uniform(0.07, 0.20), rng.uniform(0.022, 0.05),
                     0.003, "oak" if i % 3 else "oak_weathered")
        oc.rotate_y(rng.uniform(0, 3.14))
        oc.rotate_z(rng.uniform(-0.1, 0.1))
        oc.translate(rng.uniform(-2.2, 3.2), 0.12 + rng.uniform(0, 0.05),
                     rng.uniform(-4.2, 1.2))
        offc.add(oc)
    p.emit(offc)

    # The glue pot on its brazier — small, warm, and the reason a joiner's shop
    # smells the way it does.
    braz = M.Group()
    braz.add(M.lathe([(0.19, 0), (0.21, 0.10), (0.19, 0.26)], 10, "iron_pitted"))
    for i in range(9):
        c = M.box(rng.uniform(0.04, 0.08), 0.035, rng.uniform(0.04, 0.07), 0.008,
                  "coal")
        c.translate(rng.uniform(-0.10, 0.10), 0.255, rng.uniform(-0.10, 0.10))
        braz.add(c)
    braz.add(M.lathe([(0.10, 0), (0.115, 0.05), (0.10, 0.19), (0.115, 0.21)],
                     10, "brass").translate(0, 0.29, 0))
    braz.translate(2.95, 0.32, rz + 1.45)
    p.emit(braz)
    p.entity(f"{asset_id}.brazier.01", "prop.hearth", (2.95, 0.32, rz + 1.45),
             light={"color": "#FF9A4A", "intensity": 1.5, "range": 4.5,
                    "flickerHz": [7, 12]})

    lamp = K.lantern(f"{asset_id}.lamp", glass_mat="glass_lit", scale=1.1)
    lamp.translate(1.35, 0.10 + 2.72, rz - 0.2)
    p.emit(lamp)
    hook = M.tube((1.35, 0.10 + 3.20, rz - 0.2), (1.35, 0.10 + 2.88, rz - 0.2),
                  0.010, "iron", 5, 0.002)
    p.emit(hook)

    # A hanging sign: a saw and a square, pictorial only (Art Bible §2).
    sign = K.hanging_sign(f"{asset_id}.sign", width=0.64, height=0.48,
                          board_mat="painted", reach=0.88,
                          sway=rng.uniform(-0.06, 0.06))
    sign.translate((p.w - 0.8) * 0.5 - 0.22, 0.10 + 3.45,
                   rz - RANGE_D * 0.5 - 0.16)
    p.emit(sign)
    ic = M.Group()
    ic.add(M.chamfered_prism([(0.0, 0.0), (0.34, 0.03), (0.34, 0.075),
                              (0.0, 0.105)], 0.004, "steel_blued", 0.001))
    ic.add(M.box(0.024, 0.20, 0.010, 0.002, "oak_dark").translate(0.30, -0.09, 0))
    ic.rotate_y(np.pi * 0.5)
    ic.translate((p.w - 0.8) * 0.5 - 0.22 + 0.60, 0.10 + 3.45 - 0.44,
                 rz - RANGE_D * 0.5 - 0.22)
    p.emit(ic)

    for i, (wx, wz, size, shape) in enumerate([(-2.0, -3.4, 3.2, "path"),
                                               (1.6, -1.4, 2.6, "path"),
                                               (4.6, -3.4, 2.2, "path")]):
        w = P.worn_patch(f"{asset_id}.wear.{i}", shape=shape, size=size,
                         mat="dirt")
        w.rotate_y(rng.uniform(0, 3.0))
        w.translate(wx, 0.104, wz)
        p.emit(w)

    sp = S.spur_stone(f"{asset_id}.spur", height=0.60)
    sp.translate(-p.w * 0.5 + 0.5, 0.10, p.front + 0.30)
    p.emit(sp)
    p.collider("cylinder", center=(-p.w * 0.5 + 0.5, 0.10 + 0.30, p.front + 0.30),
               radius=0.22, height=0.60, tag="spur_stone")
