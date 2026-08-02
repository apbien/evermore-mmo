"""The stables — slot 70, Ford Road.

Eleven stalls, a hay loft over them, and a yard open to Ford Road that the
carriers turn in. It is the biggest single-storey mass in the craft quarter and
the only venue on the road between the north gate and the market place, so its
job in the town is as much about the ROAD as about the horses: this is where a
waggon coming through the gate stops.

## The stall range is open-fronted, and that is not a compromise

A working stable range of this date is a shelter shed — a roof on posts with the
stalls divided under it and a boarded screen only to the horses' shoulder. It
keeps the wind off and lets the air through, which is the whole argument, and it
is also the only way the player ever sees the inside of a stable. Closed doors
on eleven stalls would be eleven closed doors.

## Arrangement, which is a stableman's and not a designer's

Walking in from Ford Road: the mounting block and the trough at the gate, where
a rider arrives; the muck heap at the far downwind corner, as far from the hay
as the plot allows; the tack at the north end under cover and out of the rain;
the farrier's corner at the south end next to the open yard, because a horse
being shod has to stand still somewhere it is not in the way. The hay is over
the horses because that is where hay goes and because the pitching door and its
hoist beam are the range's only vertical incident.
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

NAME = "stables"
SLOT = 70
CELLS = ["E3", "E4", "F3", "F4"]

ASSET = "hm.stables"

RANGE_D = 5.2
EAVES = 5.4
STALLS = 11


def _stall_run(asset_id, count, width, depth, height=2.35, wall_z=0.0):
    """A run of stalls: heel posts, boarded divisions, mangers, bedding.

    The division boards stop at 1.35 m — shoulder height on a working horse —
    so a player looking along the range sees over every one of them into the
    whole run. A full-height division would have made this eleven cupboards.
    Ground origin, run along +X, the back wall at `z = wall_z`.
    """
    rng = rng_for(asset_id, "stalls")
    out = M.Group()
    pitch = width / count
    for i in range(count + 1):
        x = -width * 0.5 + i * pitch
        # Heel post: the one that takes the kicking, so it is the heaviest
        # timber in the building and it is rounded at the head.
        po = M.lathe([(0.105, 0), (0.105, height - 0.10), (0.075, height)], 8,
                     "oak_dark")
        po.translate(x, 0.0, wall_z - depth + 0.35)
        out.add(po)
        if i == count:
            continue
        # The division: boards to shoulder height on a bottom rail.
        for j in range(4):
            b = M.plank(depth - 0.55, 0.30, 0.045, 0.006, "oak_weathered",
                        grain_axis=1)
            b.rotate_y(np.pi * 0.5)
            b.rotate_z(rng.uniform(-0.004, 0.004))
            b.translate(x, 0.30 + j * 0.31, wall_z - depth * 0.5 + 0.10)
            out.add(b)

    for i in range(count):
        cx = -width * 0.5 + (i + 0.5) * pitch
        # Manger on the back wall, and the hay rack over it.
        mg = M.chamfered_prism([(-pitch * 0.42, 0), (pitch * 0.42, 0),
                                (pitch * 0.36, 0.36), (-pitch * 0.36, 0.36)],
                               0.40, "oak_weathered", 0.008)
        mg.translate(cx, 0.78, wall_z - 0.22)
        out.add(mg)
        for j in range(2):
            br = M.plank(0.10, 0.09, 0.09, 0.005, "oak_dark")
            br.rotate_z(0.9)
            br.translate(cx + (j * 2 - 1) * pitch * 0.34, 0.62, wall_z - 0.12)
            out.add(br)
        for j in range(6):                    # hay rack bars
            bx = cx - pitch * 0.30 + j * pitch * 0.12
            out.add(M.tube((bx, 1.24, wall_z - 0.06), (bx, 1.74, wall_z - 0.30),
                           0.013, "iron", 5, 0.001))
        if i % 3 != 1:                        # hay in most of them, not all
            for j in range(5):
                h = M.chamfered_prism([(0, 0), (0.16, 0.05), (0.02, 0.10)], 0.10,
                                      "straw", 0.002)
                h.rotate_y(rng.uniform(0, 3.14))
                h.translate(cx + rng.uniform(-0.20, 0.20), 1.30 + j * 0.06,
                            wall_z - 0.18)
                out.add(h)
        # Tie ring in the wall.
        rg = M.ring(0.045, 0.011, "iron", 8)
        rg.rotate_x(np.pi * 0.5)
        rg.translate(cx + pitch * 0.30, 1.30, wall_z - 0.05)
        out.add(rg)

    # Bedding: straw trodden into a bank against the divisions, thinner in the
    # middle where the horse actually stands. That gradient is the difference
    # between a stall in use and a stall in a diagram.
    for i in range(count):
        cx = -width * 0.5 + (i + 0.5) * pitch
        n = 12 if i % 3 != 1 else 4
        for j in range(n):
            a = rng.uniform(0, 6.283)
            d = rng.uniform(0.45, 1.0) ** 0.5
            st = M.chamfered_prism([(0, 0), (0.30, 0.045), (0.05, 0.075)], 0.22,
                                   "straw", 0.002)
            st.rotate_y(rng.uniform(0, 3.14))
            st.translate(cx + np.cos(a) * d * pitch * 0.42, 0.02,
                         wall_z - depth * 0.5 + np.sin(a) * d * depth * 0.36)
            out.add(st)
    return out


def _tack_wall(asset_id, width=2.6, wall_z=0.0):
    """Harness on pegs: collars, bridles, hames, a saddle over a rail."""
    rng = rng_for(asset_id, "tack")
    out = M.Group()
    rail = M.plank(width, 0.10, 0.09, 0.006, "oak_dark")
    rail.translate(0, 1.92, wall_z - 0.06)
    out.add(rail)
    for i in range(7):
        pg = M.tube((-width * 0.5 + 0.2 + i * (width - 0.4) / 6, 1.92, wall_z - 0.06),
                    (-width * 0.5 + 0.2 + i * (width - 0.4) / 6, 1.86, wall_z - 0.24),
                    0.017, "oak_dark", 5, 0.002)
        out.add(pg)
    # Two horse collars — the most recognisable object in any tack room.
    for i, cx in enumerate((-width * 0.5 + 0.55, -width * 0.5 + 1.30)):
        col = M.lathe([(0.075, 0), (0.10, 0.05), (0.075, 0.10)], 8, "leather",
                      close_bottom=False, close_top=False)
        col.scale(1.0, 1.0, 1.0)
        ring = M.Group()
        for j in range(14):
            a = 2 * np.pi * j / 14
            seg = M.lathe([(0.055, 0), (0.070, 0.06), (0.055, 0.12)], 6, "leather")
            seg.rotate_z(np.pi * 0.5)
            seg.rotate_y(a + np.pi * 0.5)
            seg.translate(np.cos(a) * 0.24, np.sin(a) * 0.30, 0)
            ring.add(seg)
        ring.translate(cx, 1.50 - i * 0.06, wall_z - 0.16)
        out.add(ring)
    # Bridles: a strap loop and a bit.
    for i in range(4):
        bx = 0.05 + i * 0.30
        out.add(M.catenary((bx, 1.86, wall_z - 0.16), (bx + 0.12, 1.86, wall_z - 0.16),
                           0.40, "leather", 0.014, 8, 4))
        out.add(M.tube((bx - 0.03, 1.44, wall_z - 0.16), (bx + 0.15, 1.44, wall_z - 0.16),
                       0.010, "iron", 5, 0.001))
    # A saddle over the rail's end, and a coil of rope on the last peg.
    sd = M.lathe([(0.0, 0), (0.20, 0.06), (0.24, 0.20), (0.14, 0.32), (0.0, 0.34)],
                 10, "leather")
    sd.scale(1.5, 0.7, 1.0)
    sd.rotate_z(np.pi)
    sd.translate(width * 0.5 - 0.42, 2.08, wall_z - 0.22)
    out.add(sd)
    rp = K.rope_coil(f"{asset_id}.rope", radius=0.17)
    rp.rotate_x(np.pi * 0.5)
    rp.translate(width * 0.5 - 0.05, 1.72, wall_z - 0.18)
    out.add(rp)
    return out


def _muck_heap(asset_id, radius=1.5, height=0.95):
    """The muck heap. Steaming, nettled, and downwind of everything."""
    rng = rng_for(asset_id, "muck")
    out = M.Group()
    body = M.lathe([(radius, 0), (radius * 0.92, height * 0.45),
                    (radius * 0.62, height * 0.85), (0.0, height)], 13, "earth")
    out.add(body)
    for i in range(46):                       # straw worked through it
        a = rng.uniform(0, 6.283)
        d = rng.uniform(0, 1.0) ** 0.5
        y = height * (1.0 - d) * rng.uniform(0.4, 1.0)
        st = M.chamfered_prism([(0, 0), (0.26, 0.04), (0.04, 0.065)], 0.18,
                               "straw", 0.002)
        st.rotate_y(rng.uniform(0, 3.14))
        st.rotate_z(rng.uniform(-0.5, 0.5))
        st.translate(np.cos(a) * d * radius * 0.95, y,
                     np.sin(a) * d * radius * 0.95)
        out.add(st)
    for i in range(9):                        # nettles round the foot
        a = rng.uniform(0, 6.283)
        cl = K.leaf_cluster(f"{asset_id}.n{i}", radius=0.13, count=6,
                            mat="foliage", droop=0.5)
        cl.translate(np.cos(a) * radius * 1.12, 0.12, np.sin(a) * radius * 1.12)
        out.add(cl)
    fork = M.Group()
    fork.add(M.tube((0, 0, 0), (0.28, 1.42, 0.10), 0.022, "oak_weathered", 6, 0.002))
    for j in range(3):
        fork.add(M.tube((-0.02 + j * 0.02, 0.0, -0.05 + j * 0.05),
                        (-0.06 + j * 0.06, -0.34, -0.10 + j * 0.10),
                        0.008, "iron", 4, 0.001))
    fork.translate(radius * 0.35, height * 0.62, radius * 0.20)
    out.add(fork)
    return out


def build(ctx: VenueContext, asset_id=ASSET):
    p = Site(slot=SLOT, ctx=ctx, asset_id=asset_id)
    rng = rng_for(asset_id, "stables")

    # ------------------------------------------------------------------ yard
    yard = M.box(p.w + 0.8, 0.10, p.d + 0.8, 0.035, "gravel",
                 uv_scale=ctx.uv_scale("gravel"))
    yard.translate(0, 0.05, 0)
    p.emit(yard)
    p.collider("box", center=(0, 0.05, 0),
               half=((p.w + 0.8) * 0.5, 0.05, (p.d + 0.8) * 0.5),
               kind="surface", tag="yard")

    # The turning circle: this yard exists so a four-wheel waggon can come off
    # Ford Road, swing round and go back out, and the ruts are the record of it.
    for i in range(9):
        a = -0.95 + i * 0.24
        r = 4.6 + rng.uniform(-0.25, 0.25)
        rt = M.box(1.9, 0.03, 0.34, 0.012, "mud_wet",
                   uv_scale=ctx.uv_scale("mud_wet"))
        rt.rotate_y(a)
        rt.translate(np.sin(a) * r * 0.9, 0.108, p.front + 1.2 + np.cos(a) * r * 0.55)
        p.emit(rt)

    # ------------------------------------------------------- the stall range
    RW = p.w - 0.9
    rz = p.back - RANGE_D * 0.5
    body = K.open_range(
        f"{asset_id}.range", RW, RANGE_D, EAVES, pitch=0.78, overhang=0.66,
        roof_mat="terracotta", walls=("back", "left", "right"),
        plinth=0.24, plinth_mat="rubble", board_gap=0.05, bays=6,
        tag="stable")
    body.translate(0, 0.10, rz)
    p.emit(body, container="range", shell=True)

    fy = 0.10 + 0.24
    fh = EAVES - 0.24
    p.collider("box", center=(0, 0.10 + 0.12, rz),
               half=(RW * 0.5 + 0.12, 0.12, RANGE_D * 0.5 + 0.12),
               kind="surface", tag="stable_floor")
    p.collider("box", center=(0, fy + fh * 0.5, p.back - 0.10),
               half=(RW * 0.5 + 0.05, fh * 0.5, 0.11), tag="back_wall")
    for s in (-1, 1):
        p.collider("box", center=(s * RW * 0.5, fy + fh * 0.5, rz),
                   half=(0.11, fh * 0.5, RANGE_D * 0.5), tag="side_wall")
    for i in range(7):
        px = -RW * 0.5 + i * RW / 6
        p.collider("box", center=(px, fy + fh * 0.5, rz - RANGE_D * 0.5),
                   half=(0.16, fh * 0.5, 0.16), tag="post")

    # --- the stalls -------------------------------------------------------
    stalls = _stall_run(f"{asset_id}.stalls", STALLS, RW - 0.7, RANGE_D - 0.5,
                        height=2.35, wall_z=p.back - 0.20)
    stalls.translate(0, fy, 0)
    p.emit(stalls)
    # Every division board is solid to shoulder height; the stalls themselves
    # stay walkable, which is what makes the range a place and not a facade.
    pitch = (RW - 0.7) / STALLS
    for i in range(STALLS + 1):
        px = -(RW - 0.7) * 0.5 + i * pitch
        p.collider("box", center=(px, fy + 0.78, p.back - 0.20 - RANGE_D * 0.5 + 0.35),
                   half=(0.12, 0.78, (RANGE_D - 0.5) * 0.5 - 0.28), tag="division")
    p.collider("box", center=(0, fy + 0.55, p.back - 0.42),
               half=((RW - 0.7) * 0.5, 0.55, 0.30), tag="mangers")

    p.entity(f"{asset_id}.stable.01", "service.stable",
             (0.0, fy, rz - RANGE_D * 0.5 + 0.6), verbs=["stable"],
             service={"kind": "stable", "capacity": STALLS})

    # --- the hay loft, its pitching door and the hoist --------------------
    loft_y = fy + 2.62
    deck = M.box(RW - 0.5, 0.075, RANGE_D - 0.6, 0.008, "oak_weathered")
    deck.translate(0, loft_y, rz + 0.10)
    p.emit(deck)
    for i in range(11):
        jx = -(RW - 0.7) * 0.5 + i * (RW - 0.7) / 10
        j = M.plank(RANGE_D - 0.6, 0.18, 0.11, 0.006, "oak_dark", grain_axis=1)
        j.rotate_y(np.pi * 0.5)
        j.translate(jx, loft_y - 0.10, rz + 0.10)
        p.emit(j)
    # Hay on the deck, spilling over the edge where it was forked in.
    for i in range(34):
        h = M.chamfered_prism([(0, 0), (0.42, 0.07), (0.06, 0.12)], 0.30, "straw",
                              0.003)
        h.rotate_y(rng.uniform(0, 3.14))
        h.rotate_z(rng.uniform(-0.25, 0.25))
        h.translate(rng.uniform(-RW * 0.42, RW * 0.42),
                    loft_y + 0.05 + rng.uniform(0, 0.55),
                    rz + rng.uniform(-0.9, 1.4))
        p.emit(h)
    # The pitching door: a gap in the front plate with a hoist beam out of it
    # and a truss of hay on the rope, halfway up. It is the range's only
    # vertical event and it is what stops 15 m of eaves reading as a ruler.
    px0 = RW * 0.5 - 4.3
    for s in (-1, 1):
        jm = M.box(0.14, 1.55, 0.20, 0.008, "oak_dark")
        jm.translate(px0 + s * 0.85, loft_y + 0.80, rz - RANGE_D * 0.5 + 0.10)
        p.emit(jm)
    lint = M.plank(1.95, 0.16, 0.22, 0.008, "oak_dark")
    lint.translate(px0, loft_y + 1.62, rz - RANGE_D * 0.5 + 0.10)
    p.emit(lint)
    hoist = M.plank(1.55, 0.17, 0.16, 0.008, "oak_dark", grain_axis=1)
    hoist.rotate_y(np.pi * 0.5)
    hoist.translate(px0, fy + EAVES + 0.30, rz - RANGE_D * 0.5 - 0.50)
    p.emit(hoist)
    p.emit(M.tube((px0, fy + EAVES + 0.24, rz - RANGE_D * 0.5 - 1.05),
                  (px0, fy + 2.15, rz - RANGE_D * 0.5 - 1.05), 0.012, "canvas",
                  5, 0.0))
    truss = M.Group()
    for i in range(16):
        h = M.chamfered_prism([(0, 0), (0.46, 0.07), (0.06, 0.12)], 0.32, "straw",
                              0.003)
        h.rotate_y(rng.uniform(0, 3.14))
        h.translate(rng.uniform(-0.28, 0.28), rng.uniform(0, 0.55),
                    rng.uniform(-0.28, 0.28))
        truss.add(h)
    truss.translate(px0, fy + 1.55, rz - RANGE_D * 0.5 - 1.05)
    p.emit(truss)

    # --- tack, at the sheltered north end ---------------------------------
    tack = _tack_wall(f"{asset_id}.tack", width=2.8, wall_z=p.back - 0.22)
    tack.translate(-RW * 0.5 + 1.85, fy, 0)
    p.emit(tack)

    # --- the farrier's corner, at the open south end ----------------------
    FX, FZ2 = RW * 0.5 - 1.35, rz - RANGE_D * 0.5 - 1.55
    tri = M.Group()                            # the shoeing tripod
    for j in range(3):
        a = 2 * np.pi * j / 3
        tri.add(M.tube((np.cos(a) * 0.30, 0.0, np.sin(a) * 0.30),
                       (0, 0.62, 0), 0.026, "iron_pitted", 5, 0.002))
    tri.add(M.lathe([(0.0, 0), (0.13, 0.02), (0.12, 0.055)], 10, "iron_pitted")
            .translate(0, 0.62, 0))
    tri.translate(FX, 0.10, FZ2)
    p.emit(tri)
    box = P.crate(f"{asset_id}.shoebox", size=0.46, height=0.34, open_top=True)
    box.rotate_y(0.4)
    box.translate(FX - 0.85, 0.10, FZ2 + 0.35)
    p.emit(box)
    for i in range(11):                        # shoes in the box and beside it
        sh = M.lathe([(0.055, 0), (0.075, 0.016)], 10, "iron_pitted",
                     close_bottom=False, close_top=False)
        sh.scale(1.0, 1.0, 0.72)
        sh.rotate_y(rng.uniform(0, 3.14))
        sh.rotate_z(rng.uniform(-0.2, 0.2) if i > 7 else 0.0)
        sh.translate(FX - 0.85 + rng.uniform(-0.16, 0.16),
                     0.13 + (i % 5) * 0.020,
                     FZ2 + 0.35 + rng.uniform(-0.16, 0.16))
        p.emit(sh)
    # The hoof-paring pile: horn shavings, pale, and unmistakably not wood.
    par = P.shavings(f"{asset_id}.parings", 34, 0.52, 0.44, "elm", curl=0.55)
    par.translate(FX + 0.42, 0.10, FZ2 - 0.30)
    p.emit(par)
    bkt = P.bucket(f"{asset_id}.farrier_bucket", full=True)
    bkt.translate(FX + 0.85, 0.10, FZ2 + 0.55)
    p.emit(bkt)
    p.collider("cylinder", center=(FX, 0.10 + 0.32, FZ2), radius=0.42,
               height=0.64, tag="shoeing_stand")

    # --- the gate: mounting block, trough, rail --------------------------
    mb = S.mounting_block(f"{asset_id}.block", height=0.64)
    mb.rotate_y(-0.30)
    mb.translate(-p.w * 0.5 + 1.6, 0.10, p.front + 1.15)
    p.emit(mb)
    p.collider("box", center=(-p.w * 0.5 + 1.6, 0.10 + 0.32, p.front + 1.15),
               half=(0.55, 0.32, 0.42), rot_y=-0.30, kind="surface",
               tag="mounting_block")

    tr = S.horse_trough(f"{asset_id}.trough", length=2.1, width=0.66, height=0.58)
    tr.rotate_y(0.06)
    tr.translate(-p.w * 0.5 + 3.6, 0.10, p.front + 0.85)
    p.emit(tr)
    p.collider("box", center=(-p.w * 0.5 + 3.6, 0.10 + 0.29, p.front + 0.85),
               half=(1.08, 0.29, 0.36), tag="trough")

    rail = S.hitching_rail(f"{asset_id}.rail", length=3.2, height=1.05)
    rail.rotate_y(-0.05)
    rail.translate(p.w * 0.5 - 3.0, 0.10, p.front + 0.75)
    p.emit(rail)
    for s in (-1, 1):
        p.collider("cylinder", center=(p.w * 0.5 - 3.0 + s * 1.6, 0.10 + 0.52,
                                       p.front + 0.75),
                   radius=0.09, height=1.05, tag="rail_post")

    # --- the muck heap, downwind, as far from the hay as the plot allows --
    muck = _muck_heap(f"{asset_id}.muck", radius=1.55, height=0.98)
    muck.translate(p.w * 0.5 - 1.9, 0.10, p.back - 1.5)
    p.emit(muck)
    p.collider("cylinder", center=(p.w * 0.5 - 1.9, 0.10 + 0.49, p.back - 1.5),
               radius=1.45, height=0.98, tag="muck_heap")
    stain = P.worn_patch(f"{asset_id}.muckstain", shape="cat", size=3.8,
                         mat="mud_wet")
    stain.translate(p.w * 0.5 - 1.9, 0.106, p.back - 1.5)
    p.emit(stain)

    # --- residue ----------------------------------------------------------
    barrow = P.wheelbarrow(f"{asset_id}.barrow", tipped=False)
    barrow.rotate_y(1.9)
    barrow.translate(p.w * 0.5 - 3.6, 0.10, p.back - 2.6)
    p.emit(barrow)

    for i, (bx, bz) in enumerate([(-RW * 0.5 + 0.9, rz - RANGE_D * 0.5 - 0.9),
                                  (-RW * 0.5 + 1.6, rz - RANGE_D * 0.5 - 1.3)]):
        bk = P.bucket(f"{asset_id}.bkt.{i}", full=i == 0)
        bk.rotate_y(rng.uniform(0, 3.0))
        bk.translate(bx, 0.10, bz)
        p.emit(bk)
    br = P.broom(f"{asset_id}.broom", wall_z=p.back - 0.24,
                 x=-RW * 0.5 + 0.55)
    br.translate(0, fy, 0)
    p.emit(br)

    for i in range(3):
        st = P.stool(f"{asset_id}.stool.{i}", height=0.42, radius=0.16)
        st.rotate_y(rng.uniform(0, 3.0))
        st.translate(FX - 1.6 + i * 0.9, 0.10, FZ2 + rng.uniform(-0.5, 0.5))
        p.emit(st)

    # Straw dropped on the way from the loft to the stalls, and mud where the
    # horses come out. Both are marks of a path somebody actually walks.
    for i in range(26):
        h = M.chamfered_prism([(0, 0), (0.30, 0.05), (0.05, 0.085)], 0.20, "straw",
                              0.002)
        h.rotate_y(rng.uniform(0, 3.14))
        h.translate(rng.uniform(-RW * 0.45, RW * 0.45), 0.11,
                    rz - RANGE_D * 0.5 - rng.uniform(0.1, 2.6))
        p.emit(h)
    for i, (wx, wz, size) in enumerate([(-2.0, rz - RANGE_D * 0.5 - 1.2, 4.2),
                                        (3.5, rz - RANGE_D * 0.5 - 1.6, 3.4),
                                        (0.0, p.front + 2.0, 4.6)]):
        w = P.worn_patch(f"{asset_id}.wear.{i}", shape="path", size=size,
                         mat="mud_wet")
        w.rotate_y(rng.uniform(0, 3.0))
        w.translate(wx, 0.104, wz)
        p.emit(w)

    lamp = K.lantern(f"{asset_id}.lamp", glass_mat="glass_lit", scale=1.15)
    lamp.translate(-RW * 0.5 + 1.85, fy + 2.30, p.back - 0.55)
    p.emit(lamp)
    p.entity(f"{asset_id}.lamp.01", "prop.lantern",
             (-RW * 0.5 + 1.85, fy + 2.30, p.back - 0.55),
             light={"color": "#FFB566", "intensity": 1.3, "range": 6.0})

    sign = K.hanging_sign(f"{asset_id}.sign", width=0.68, height=0.50,
                          board_mat="painted", reach=0.90,
                          sway=rng.uniform(-0.06, 0.06))
    sign.translate(-RW * 0.5 + 0.25, 0.10 + 3.55, rz - RANGE_D * 0.5 - 0.18)
    p.emit(sign)
    ic = M.lathe([(0.055, 0), (0.075, 0.016)], 12, "iron",
                 close_bottom=False, close_top=False)
    ic.scale(2.6, 1.0, 1.9)
    ic.rotate_x(np.pi * 0.5)
    ic.translate(-RW * 0.5 + 0.25 + 0.58, 0.10 + 3.55 - 0.48,
                 rz - RANGE_D * 0.5 - 0.24)
    p.emit(ic)
