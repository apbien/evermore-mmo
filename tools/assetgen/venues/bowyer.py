"""The bowyer — slot 36, Sty Lane.

The smallest of the six trades and the one with the clearest single image: a
stave bending on the tillering frame. Everything else on the plot exists to
explain that one object.

## Read from Sty Lane, left to right

    SEASON   staves standing under the eaves, out of the rain and in the
             draught, where they have been for two years. A bow stave is
             bought as a billet and used four winters later, and the rack is
             the physical form of that wait.
    TILLER   the tillering frame in the open, with a stave at half draw and
             the scale of notches under it. This is the anchor.
    HORN     the composite bench: horn plates, hanks of sinew, the glue pot
             over its brazier
    STRING   strings drying on a line, waxed and looped
    SHOOT    the butt at the plot's east end, a turf bank faced with straw
             bundles, arrows in it and two in the ground short of it

## Why the butt is where it is

`docs/plan/schedule.md` slot 36: *"a shooting butt against the wall revetment
behind, which is the only straight 30 m in the south quarter."* The plot itself
is 9 x 8, so what stands here is the near end of that shot — the butt, the mark
stone the archer stands on, and the line between them running out of the plot
along the revetment. Building only the butt would have been a prop; building
the mark stone as well makes it a range.
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

NAME = "bowyer"
SLOT = 36
CELLS = ["I10", "I9", "J10", "J9"]

ASSET = "hm.bowyer"

RANGE_D = 4.0
EAVES = 4.8


def _tillering_frame(asset_id, height=2.25):
    """A stave at half draw on the tiller. Ground origin, bow across +X.

    The frame is a post with a horizontal rest at the top for the handle and a
    ladder of notches below it that the string is dropped into, one notch at a
    time, so the bowyer can walk back and look at the curve. The stave on it
    here is at the third notch and it is NOT yet symmetrical — the lower limb
    is stiffer than the upper, which is the fault every bowyer is looking for
    and the reason the tool exists.
    """
    out = M.Group()
    post = M.box(0.20, height, 0.17, 0.010, "oak_dark")
    post.translate(0, height * 0.5, 0)
    out.add(post)
    foot = M.box(0.62, 0.16, 0.72, 0.010, "oak_weathered")
    foot.translate(0, 0.08, 0)
    out.add(foot)
    for s in (-1, 1):                        # braces to the foot
        out.add(M.tube((0, height * 0.62, 0), (s * 0.30, 0.16, 0.0), 0.045,
                       "oak_weathered", 6, 0.004))
    rest = M.plank(0.34, 0.13, 0.10, 0.006, "oak_dark", grain_axis=1)
    rest.rotate_y(np.pi * 0.5)
    rest.translate(0, height, -0.16)
    out.add(rest)
    # The notch ladder.
    for i in range(9):
        n = M.box(0.24, 0.035, 0.055, 0.004, "oak_dark")
        n.translate(0, height - 0.42 - i * 0.115, -0.11)
        out.add(n)

    # The stave, bent. Two limbs of a quadratic, drawn to the third notch.
    draw_y = height - 0.42 - 2 * 0.115
    tip = 0.92
    for s in (-1, 1):
        stiff = 1.0 if s > 0 else 0.82       # the lower limb is stiffer
        pts = []
        for i in range(7):
            t = i / 6.0
            pts.append((s * t * tip * (0.10 + 0.90 * (1 - 0.18 * t)),
                        height - t * t * (height - draw_y) * 1.55 * stiff,
                        -0.16 - 0.02 * np.sin(t * 3.1)))
        for i in range(6):
            out.add(M.tube(pts[i], pts[i + 1],
                           0.020 - 0.008 * (i / 5.0), "oak", 6, 0.002))
    # The string, from tip to tip through the notch.
    out.add(M.tube((-tip * 0.86, height - (height - draw_y) * 1.27, -0.185),
                   (0.0, draw_y, -0.115), 0.0045, "canvas", 4, 0.0))
    out.add(M.tube((0.0, draw_y, -0.115),
                   (tip * 0.86, height - (height - draw_y) * 1.55, -0.185),
                   0.0045, "canvas", 4, 0.0))
    return out


def _stave_rack(asset_id, count=11, height=2.05, width=2.4, wall_z=0.0):
    """Bow staves standing in a rack against a wall. Ground origin.

    Standing, never lying: a stave stored flat takes a set and is worthless.
    They are graded left to right by how long they have been there, which is
    also how thick they still are.
    """
    rng = rng_for(asset_id, "staves")
    out = M.Group()
    sill = M.plank(width, 0.14, 0.16, 0.008, "oak_weathered")
    sill.translate(0, 0.07, wall_z - 0.20)
    out.add(sill)
    rail = M.plank(width, 0.09, 0.09, 0.006, "oak_dark")
    rail.translate(0, 1.62, wall_z - 0.16)
    out.add(rail)
    for s in (-1, 1):
        po = M.box(0.10, 1.70, 0.10, 0.006, "oak_dark")
        po.translate(s * width * 0.5, 0.85, wall_z - 0.16)
        out.add(po)
    for i in range(count):
        x = -width * 0.5 + (i + 0.5) * width / count
        t = i / max(1, count - 1)
        w = 0.075 - t * 0.028
        h = height * rng.uniform(0.94, 1.05)
        st = M.chamfered_prism([(-w * 0.5, 0), (w * 0.5, 0),
                                (w * 0.36, 1.0), (-w * 0.36, 1.0)],
                               0.038 - t * 0.010, "oak", 0.003)
        st.scale(1.0, h, 1.0)
        st.rotate_z(rng.uniform(-0.03, 0.03))
        st.rotate_x(-0.10)
        st.translate(x + rng.uniform(-0.02, 0.02), 0.14, wall_z - 0.26)
        out.add(st)
    return out


def _butt(asset_id, width=3.2, height=2.1, depth=1.5):
    """A shooting butt: a turf bank faced with straw bundles. Ground origin.

    Faced, not solid turf, because straw stops an arrow without blunting it and
    a bundle can be replaced when it is shot to pieces. The boss is three
    concentric straw rings — PICTORIAL, no lettering anywhere (Art Bible §2).
    """
    rng = rng_for(asset_id, "butt")
    out = M.Group()
    # The bank: turf, battered back hard, with the face nearly vertical. It is
    # revetted at the foot with hurdle stakes because an earth bank that is not
    # revetted washes into the lane in one winter.
    bank = M.prism([(-width * 0.5, 0), (width * 0.5, 0),
                    (width * 0.40, height), (-width * 0.40, height)],
                   depth, chamfer=0.06)
    bank.translate(0, 0, depth * 0.5)
    out.add(bank.with_material("grass_worn"))
    cap = M.prism([(-width * 0.42, 0), (width * 0.42, 0),
                   (width * 0.34, 0.16), (-width * 0.34, 0.16)], depth * 0.92,
                  chamfer=0.04)
    cap.translate(0, height - 0.02, depth * 0.5)
    out.add(cap.with_material("grass_dry"))
    for i in range(int(width / 0.28)):
        st = M.tube((0, 0, 0), (rng.uniform(-0.03, 0.03), 0.52, 0.0), 0.028,
                    "timber_grey", 5, 0.002)
        st.translate(-width * 0.5 + (i + 0.5) * 0.28, 0.0, -0.06)
        out.add(st)

    # The boss: a coiled straw target roped to the face. Concentric rings only,
    # no device and no lettering anywhere (Art Bible section 2).
    boss = M.lathe([(0.0, 0), (0.52, 0.02), (0.54, 0.10), (0.50, 0.13)], 20,
                   "straw")
    boss.rotate_x(-np.pi * 0.5)
    boss.translate(0.0, 1.24, -0.13)
    out.add(boss)
    for r, mat in ((0.40, "canvas_crimson"), (0.20, "straw"), (0.075, "canvas_plain")):
        ring = M.lathe([(r - 0.065, 0), (r, 0.022), (r - 0.065, 0.044)], 18, mat,
                       close_bottom=False, close_top=False)
        ring.rotate_x(-np.pi * 0.5)
        ring.translate(0.0, 1.24, -0.20)
        out.add(ring)
    for s in (-1, 1):                       # the ropes it hangs on
        out.add(M.tube((s * 0.50, 1.76, -0.08), (s * 0.30, 1.24, -0.16),
                       0.010, "canvas", 4, 0.0))
    for i in range(6):
        a = rng.uniform(0, 6.283)
        d = rng.uniform(0.03, 0.46)
        ax, ay = np.cos(a) * d, 1.24 + np.sin(a) * d
        tail = (ax + rng.uniform(-0.05, 0.05), ay + rng.uniform(0.03, 0.11),
                -0.24 - rng.uniform(0.58, 0.76))
        out.add(M.tube((ax, ay, -0.22), tail, 0.006, "oak", 4, 0.0))
        for j in range(3):
            fl = M.chamfered_prism([(0, 0), (0.070, 0.014), (0.0, 0.028)], 0.003,
                                   "canvas_plain", 0.001)
            fl.rotate_z(np.pi * 0.5)
            fl.rotate_y(j * 2.09 + rng.uniform(-0.2, 0.2))
            fl.translate(tail[0], tail[1], tail[2] + 0.06)
            out.add(fl)
    return out


def build(ctx: VenueContext, asset_id=ASSET):
    p = Site(slot=SLOT, ctx=ctx, asset_id=asset_id)
    rng = rng_for(asset_id, "bowyer")

    # No full-plot hardstanding here. The ground round the bowyer is grass —
    # it has to be, because the shot runs over it — so the only made surface is
    # the strip in front of the shop and the shooting line worn across the turf.
    # A rectangle of laid earth on a grass site reads as a card lying on a lawn,
    # which is what the first pass rendered.
    apron = M.box(p.w * 0.66, 0.09, 3.1, 0.03, "earth",
                  uv_scale=ctx.uv_scale("earth"))
    apron.rotate_y(0.05)
    apron.translate(-p.w * 0.5 + p.w * 0.33 + 0.2, 0.045, p.back - 2.6)
    p.emit(apron)
    p.collider("box", center=(-p.w * 0.5 + p.w * 0.33 + 0.2, 0.045, p.back - 2.6),
               half=(p.w * 0.33, 0.045, 1.55), rot_y=0.05,
               kind="surface", tag="apron")
    for i, (wx, wz, size) in enumerate([(2.2, 0.4, 4.0), (2.6, -2.6, 3.2),
                                        (-1.0, -2.4, 2.6)]):
        w = P.worn_patch(f"{asset_id}.line.{i}", shape="path", size=size,
                         mat="dirt")
        w.rotate_y(1.35 + i * 0.2)
        w.translate(wx, 0.035, wz)
        p.emit(w)

    # ----------------------------------------------------------- the range
    # Only 5.6 m of the 9 m frontage: the east third is the shooting line, and
    # a bowyer needs it clear more than he needs another bay of workshop.
    RW = 5.6
    RX = -p.w * 0.5 + RW * 0.5 + 0.25
    rz = p.back - RANGE_D * 0.5
    body = K.open_range(
        f"{asset_id}.range", RW, RANGE_D, EAVES, pitch=0.86, overhang=0.62,
        roof_mat="terracotta", walls=("back", "left"),
        half_boarded=("right",), plinth=0.20, plinth_mat="rubble",
        board_gap=0.05, tag="bowyer")
    body.translate(RX, 0.10, rz)
    p.emit(body, container="range", shell=True)

    fh = EAVES - 0.20
    p.collider("box", center=(RX, 0.10 + 0.10, rz),
               half=(RW * 0.5 + 0.12, 0.10, RANGE_D * 0.5 + 0.12),
               kind="surface", tag="floor")
    p.collider("box", center=(RX, 0.30 + fh * 0.5, p.back - 0.10),
               half=(RW * 0.5 + 0.05, fh * 0.5, 0.11), tag="back_wall")
    p.collider("box", center=(RX - RW * 0.5, 0.30 + fh * 0.5, rz),
               half=(0.11, fh * 0.5, RANGE_D * 0.5), tag="side_wall")
    for i in range(3):
        px = RX - RW * 0.5 + i * RW / 2
        p.collider("box", center=(px, 0.30 + fh * 0.5, rz - RANGE_D * 0.5),
                   half=(0.15, fh * 0.5, 0.15), tag="post")

    # ------------------------------------------------- SEASON: staves in rack
    rack = _stave_rack(f"{asset_id}.rack", count=11, width=2.5,
                       wall_z=p.back - 0.18)
    rack.translate(RX - 1.20, 0.30, 0)
    p.emit(rack)
    p.collider("box", center=(RX - 1.20, 0.30 + 0.90, p.back - 0.45),
               half=(1.35, 0.90, 0.28), tag="stave_rack")

    # And more of them in the roof, lying on the tie beams — the schedule's own
    # note, "staves in the rafters". Under cover, out of the way, and the one
    # thing that makes the roof space read as used.
    for i in range(9):
        st = M.chamfered_prism([(-0.035, 0), (0.035, 0), (0.026, 1.0),
                                (-0.026, 1.0)], 0.042, "oak", 0.003)
        st.scale(1.0, 2.35, 1.0)
        st.rotate_z(np.pi * 0.5)
        st.rotate_y(rng.uniform(-0.04, 0.04))
        st.translate(RX + rng.uniform(-0.6, 0.6), 0.10 + EAVES + 0.02,
                     rz - 1.15 + i * 0.24)
        p.emit(st)

    # ------------------------------------------------------ TILLER: the anchor
    till = _tillering_frame(f"{asset_id}.tiller", height=2.25)
    till.rotate_y(-0.24)
    till.translate(RX + 1.35, 0.30, rz - RANGE_D * 0.5 + 0.95)
    p.emit(till)
    p.collider("box", center=(RX + 1.35, 0.30 + 1.12, rz - RANGE_D * 0.5 + 0.95),
               half=(0.34, 1.12, 0.40), rot_y=-0.24, tag="tillering_frame")
    p.entity(f"{asset_id}.station.01", "crafting_station.bowyer",
             (RX + 1.35, 0.30, rz - RANGE_D * 0.5 + 0.95), verbs=["use"],
             crafting_station={"profession": "bowyer", "tier": 1})

    # `props.bowyer_kit` — the shared library's rack and the stave on the
    # tiller. Set at the covered floor's west end so the two stations read as
    # one working area rather than as two displays.
    kit = P.bowyer_kit(f"{asset_id}.kit", wall_z=0.85)
    kit.rotate_y(0.16)
    kit.translate(RX - 1.55, 0.30, rz - 0.30)
    p.emit(kit)

    # ---------------------------------------------------- HORN, SINEW, GLUE
    bench = P.dress_workbench(f"{asset_id}.bench", trade="bowyer", length=1.9,
                              wall_z=0.9, ctx=None)
    bench.rotate_y(np.pi + 0.12)
    bench.translate(RX + 0.35, 0.30, rz + 0.85)
    p.emit(bench)
    p.collider("box", center=(RX + 0.35, 0.30 + 0.43, rz + 0.15),
               half=(0.98, 0.43, 0.32), tag="bench")

    # Horn plates in a shallow crate, and hanks of sinew hung over the rail.
    for i in range(7):
        hp = M.chamfered_prism([(-0.055, 0), (0.055, 0), (0.040, 0.36),
                                (-0.040, 0.34)], 0.012, "bronze", 0.002)
        hp.rotate_z(rng.uniform(1.2, 1.5))
        hp.rotate_y(rng.uniform(0, 3.0))
        hp.translate(RX - 0.55 + i * 0.05, 0.32 + 0.02 * i, rz + 1.35)
        p.emit(hp)
    for i in range(4):
        hank = M.Group()
        for j in range(6):
            hank.add(M.catenary((-0.10 + j * 0.04, 0.0, 0.0),
                                (-0.10 + j * 0.04, 0.0, 0.16),
                                0.14 + j * 0.005, "fleece", 0.0055, 6, 3))
        hank.translate(RX - 1.9 + i * 0.30, 0.30 + 1.92, p.back - 0.34)
        p.emit(hank)
    glue = M.Group()
    glue.add(M.lathe([(0.155, 0), (0.17, 0.09), (0.155, 0.22)], 10, "iron_pitted"))
    for i in range(8):
        c = M.box(rng.uniform(0.04, 0.07), 0.03, rng.uniform(0.04, 0.06), 0.006,
                  "coal")
        c.translate(rng.uniform(-0.08, 0.08), 0.21, rng.uniform(-0.08, 0.08))
        glue.add(c)
    glue.add(M.lathe([(0.085, 0), (0.095, 0.04), (0.085, 0.17), (0.095, 0.19)],
                     9, "brass").translate(0, 0.25, 0))
    glue.translate(RX + 1.45, 0.30, rz + 1.15)
    p.emit(glue)
    p.entity(f"{asset_id}.glue.01", "prop.hearth", (RX + 1.45, 0.30, rz + 1.15),
             light={"color": "#FF9A4A", "intensity": 1.1, "range": 3.6,
                    "flickerHz": [7, 12]})

    # ------------------------------------------------- STRING: drying on a line
    for i in range(6):
        x = RX - 2.15 + i * 0.44
        loop = M.Group()
        loop.add(M.catenary((0, 0, 0), (0, 0, 0.16), 0.30 + i * 0.02, "canvas",
                            0.0042, 10, 4))
        loop.add(M.catenary((0.02, 0, 0), (0.02, 0, 0.16), 0.30 + i * 0.02,
                            "canvas", 0.0042, 10, 4))
        loop.translate(x, 0.30 + 2.28, rz - RANGE_D * 0.5 + 0.40)
        p.emit(loop)
    line = M.catenary((RX - 2.45, 0.30 + 2.30, rz - RANGE_D * 0.5 + 0.40),
                      (RX + 0.55, 0.30 + 2.30, rz - RANGE_D * 0.5 + 0.40),
                      0.06, "canvas", 0.007, 10, 4)
    p.emit(line)

    # --------------------------------------------------- SHOOT: the butt
    BX, BZ = p.w * 0.5 - 1.85, p.back - 1.35
    # Facing the street, NOT along the plot: the butt's whole value is that a
    # player walking Sty Lane sees the boss and the arrows in it. Turned side-on
    # (which the first pass did) it is a dark box and reads as a woodpile.
    butt = _butt(f"{asset_id}.butt", width=3.0, height=2.05, depth=1.5)
    butt.rotate_y(-0.14)
    butt.translate(BX, 0.10, BZ)
    p.emit(butt)
    p.collider("box", center=(BX, 0.10 + 1.02, BZ + 0.75), half=(1.55, 1.02, 0.80),
               rot_y=-0.14, tag="butt")

    # The mark: a flat stone the archer stands on, at the near end of the shot.
    mark = M.box(0.72, 0.14, 0.52, 0.02, "stone", uv_scale=ctx.uv_scale("stone"))
    mark.rotate_y(0.18)
    mark.translate(BX - 0.35, 0.13, p.front + 1.05)
    p.emit(mark)
    worn = P.worn_patch(f"{asset_id}.stand", shape="cat", size=1.5,
                        mat="grass_worn")
    worn.translate(BX - 0.35, 0.106, p.front + 1.05)
    p.emit(worn)
    # Two arrows that fell short, lying in the line of the shot. Nothing else
    # in the venue says as clearly that people actually shoot here.
    for i, (ax, az, ay) in enumerate([(BX + 0.25, BZ - 3.30, 0.14),
                                      (BX - 0.75, BZ - 4.60, 0.13)]):
        sh = M.tube((0, 0, 0), (rng.uniform(-0.15, 0.15), 0.0, 0.72), 0.006,
                    "oak", 4, 0.0)
        sh.rotate_y(rng.uniform(-0.5, 0.5))
        sh.translate(ax, ay, az)
        p.emit(sh)

    # A quiver of finished arrows and a strung bow leaning by the rack — the
    # shop's finished goods, and where they end up.
    qv = P.basket(f"{asset_id}.quiver", radius=0.13, height=0.52, weave="stake")
    qv.translate(RX + 2.15, 0.30, rz + 0.35)
    p.emit(qv)
    for i in range(9):
        a = rng.uniform(0, 6.283)
        d = rng.uniform(0, 0.075)
        p.emit(M.tube((RX + 2.15 + np.cos(a) * d, 0.30 + 0.40,
                       rz + 0.35 + np.sin(a) * d),
                      (RX + 2.15 + np.cos(a) * d * 2.4, 0.30 + 1.05,
                       rz + 0.35 + np.sin(a) * d * 2.4), 0.005, "oak", 4, 0.0))

    bow = M.Group()
    pts = [(0.0, 0.0, 0.0)]
    for i in range(1, 9):
        t = i / 8.0
        pts.append((0.16 * np.sin(t * np.pi), t * 1.78, 0.0))
    for i in range(8):
        bow.add(M.tube(pts[i], pts[i + 1], 0.018 - 0.006 * (i / 7.0), "oak", 6,
                       0.002))
    bow.add(M.tube(pts[0], pts[-1], 0.0045, "canvas", 4, 0.0))
    P.lean(bow, 1.78, 0.34, wall_z=p.back - 0.20, x=RX + 2.05,
           roll=rng.uniform(-0.05, 0.05))
    bow.translate(0, 0.30, 0)
    p.emit(bow)

    # ------------------------------------------------------------ residue
    sh = P.shavings(f"{asset_id}.shav", 44, 1.25, 0.85, "oak")
    sh.translate(RX + 1.15, 0.31, rz - 0.55)
    p.emit(sh)
    # A stave that broke on the tiller, thrown into the corner in two pieces.
    for i, (bx2, ang) in enumerate([(RX + 2.6, 1.20), (RX + 2.35, 0.55)]):
        br = M.chamfered_prism([(-0.036, 0), (0.036, 0), (0.024, 1.0),
                                (-0.024, 1.0)], 0.042, "oak", 0.003)
        br.scale(1.0, 0.95 + i * 0.25, 1.0)
        br.rotate_z(np.pi * 0.5)
        br.rotate_y(ang)
        br.translate(bx2, 0.34, rz + 1.55)
        p.emit(br)

    sign = K.hanging_sign(f"{asset_id}.sign", width=0.56, height=0.44,
                          board_mat="painted", reach=0.80,
                          sway=rng.uniform(-0.06, 0.06))
    sign.translate(RX + RW * 0.5 - 0.20, 0.10 + 3.05, rz - RANGE_D * 0.5 - 0.14)
    p.emit(sign)
    ib = M.Group()
    ipts = [(0.0, -0.24, 0.0)]
    for i in range(1, 7):
        t = i / 6.0
        ipts.append((0.10 * np.sin(t * np.pi), -0.24 + t * 0.46, 0.0))
    for i in range(6):
        ib.add(M.tube(ipts[i], ipts[i + 1], 0.010, "oak_dark", 5, 0.001))
    ib.add(M.tube(ipts[0], ipts[-1], 0.004, "canvas", 4, 0.0))
    ib.translate(RX + RW * 0.5 - 0.20 + 0.54, 0.10 + 3.05 - 0.44,
                 rz - RANGE_D * 0.5 - 0.20)
    p.emit(ib)

    for i, (wx, wz, size) in enumerate([(RX + 0.5, rz - 2.2, 2.6),
                                        (p.w * 0.5 - 2.0, 0.4, 2.2)]):
        w = P.worn_patch(f"{asset_id}.wear.{i}", shape="path", size=size,
                         mat="dirt")
        w.rotate_y(rng.uniform(0, 3.0))
        w.translate(wx, 0.104, wz)
        p.emit(w)

    hp2 = S.hitching_post(f"{asset_id}.post")
    hp2.translate(-p.w * 0.5 + 0.6, 0.10, p.front + 0.55)
    p.emit(hp2)
    p.collider("cylinder", center=(-p.w * 0.5 + 0.6, 0.10 + 0.56, p.front + 0.55),
               radius=0.10, height=1.12, tag="hitching_post")
