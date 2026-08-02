"""The tannery — slot 93, Tan Road, OUTSIDE the wall.

`docs/plan/schedule.md`: *"the single most defensible placement in the plan: it
needs running water, it stinks, and it is 90 m from the nearest occupied window
with the wind blowing away from town."*

This is the town's ugly necessary trade and the brief is explicit that it should
be allowed to be ugly. Nothing here is tidied and nothing is prettified: the job
is to make the SITING legible, so that a player who walks out of the water gate
and finds this understands in one look why it is out here and nothing else is.

## What has to read

    PITS      twenty-four of them, sunk in a timber-curbed platform, and the
              liquor in them at four different colours because they are at four
              different stages: lime (milky, and it is the lime that takes the
              hair off), bate, the weak tan liquor, and the old ooze that has
              been eating a hide for a year. A row of identical pits would say
              nothing; the colour gradient says the whole process.
    HIDES     on stretcher frames, laced through the edge with cord and pulled
              square. This is the tallest thing on the plot after the shed and
              the only one with a human-sized rhythm.
    BEAM      the currier's beam and his knives, which is where the hair and
              the flesh come off. `props.tanner_kit` owns it.
    BARK      the tan itself: oak bark stacked to dry and the edge-runner mill
              that grinds it. The mill is the anchor — a 1.6 m stone wheel on
              its edge in a circular trough is unmistakable and there is
              nothing else like it in Hearthmere.
    GROUND    stained. Not a decal over the whole plot but a gradient: black at
              the pit lips, brown in the working lanes, and only the far corner
              of the plot still has anything green on it.

## Why the pits stand proud instead of being dug

`core/terrain.py` owns `height(x, z)` and a venue may not cut into it, so a pit
modelled below ground level is a box the terrain surface draws straight over.
The pits are therefore sunk into a raised working platform 0.55 m above the
yard, which is also what a real pit yard does where the water table is high —
and this one is 25 m from the Mere. Two steps up at the entry, `surface`
collision on the platform top, `solid` on the curbs.
"""

from __future__ import annotations

import numpy as np

from core import kit as K
from core import mesh as M
from core import props as P
from core.mathx import rng_for
from core.siting import Site
from core.venue import VenueContext

NAME = "tannery"
SLOT = 93
CELLS = ["K5", "K6", "L5", "L6"]

ASSET = "hm.tannery"

PLAT_H = 0.55
SHED_D = 4.2
EAVES = 5.0

# The four stages, in the order a hide goes through them. Colour is the whole
# communication here, so the materials are chosen for value separation first.
LIQUOR = [("limewash", 0.30), ("mud", 0.22), ("stained", 0.18),
          ("stained_dark", 0.12)]


def _pit_yard(asset_id, ctx, cols=6, rows=4, pit=1.05, curb=0.26):
    """A curbed pit platform. Ground origin at the platform's centre, top at
    `PLAT_H`. Returns (group, [(x, z, stage) ...]) so the caller can dress it."""
    rng = rng_for(asset_id, "pits")
    out = M.Group()
    W = cols * pit + (cols + 1) * curb
    D = rows * pit + (rows + 1) * curb
    # The platform is a LATTICE, not a slab. The first pass built a solid block
    # and recessed the pits into it, which meant the liquor, the boarding and
    # the pit floors were all inside solid geometry and twenty-four pits
    # rendered as a paved terrace. What stands here is the base under the pits
    # plus the curb walls between them, so the holes are real holes.
    base = M.box(W, PLAT_H - 0.45, D, 0.03, "rubble",
                 uv_scale=ctx.uv_scale("rubble"))
    base.translate(0, (PLAT_H - 0.45) * 0.5, 0)
    out.add(base)
    for c in range(cols + 1):
        x = -W * 0.5 + curb * 0.5 + c * (pit + curb)
        cb = M.box(curb, 0.45, D, 0.02, "rubble", uv_scale=ctx.uv_scale("rubble"))
        cb.translate(x, PLAT_H - 0.225, 0)
        out.add(cb)
    for r in range(rows + 1):
        z = -D * 0.5 + curb * 0.5 + r * (pit + curb)
        cb = M.box(W, 0.45, curb, 0.02, "rubble", uv_scale=ctx.uv_scale("rubble"))
        cb.translate(0, PLAT_H - 0.225, z)
        out.add(cb)

    centres = []
    for r in range(rows):
        for c in range(cols):
            x = -W * 0.5 + curb + pit * 0.5 + c * (pit + curb)
            z = -D * 0.5 + curb + pit * 0.5 + r * (pit + curb)
            # Stage runs along the row and drifts down the yard, so the colour
            # gradient reads as a process and not as a chequerboard.
            stage = min(3, int((c / cols) * 3.4 + rng.uniform(-0.4, 0.4) + r * 0.12))
            stage = max(0, stage)
            centres.append((x, z, stage))
            # The pit: a boarded box sunk into the platform.
            for s in (-1, 1):
                b = M.box(pit + 0.02, 0.45, 0.038, 0.003, "pine_tarred")
                b.translate(x, PLAT_H - 0.225, z + s * (pit * 0.5 - 0.019))
                out.add(b)
                b2 = M.box(0.038, 0.45, pit + 0.02, 0.003, "pine_tarred")
                b2.translate(x + s * (pit * 0.5 - 0.019), PLAT_H - 0.225, z)
                out.add(b2)
            mat, depth = LIQUOR[stage]
            liq = M.box(pit - 0.06, 0.02, pit - 0.06, 0.004, mat,
                        uv_scale=ctx.uv_scale(mat))
            liq.translate(x, PLAT_H - depth, z)
            out.add(liq)
            floor = M.box(pit - 0.02, 0.03, pit - 0.02, 0.004, "stained_dark")
            floor.translate(x, PLAT_H - 0.45, z)
            out.add(floor)
    # Curb capping: a plank walk between the pits, worn pale along its middle.
    for c in range(cols + 1):
        x = -W * 0.5 + curb * 0.5 + c * (pit + curb)
        pl = M.plank(D, curb * 0.92, 0.055, 0.005, "oak_weathered", grain_axis=1)
        pl.rotate_y(np.pi * 0.5)
        pl.translate(x, PLAT_H + 0.028, 0)
        out.add(pl)
    for r in range(rows + 1):
        z = -D * 0.5 + curb * 0.5 + r * (pit + curb)
        pl = M.plank(W, curb * 0.92, 0.055, 0.005, "oak_weathered")
        pl.translate(0, PLAT_H + 0.028, z)
        out.add(pl)
    return out, centres, W, D


def _hide_frame(asset_id, width=1.65, height=2.05, hung=True):
    """A hide laced into a stretcher frame. Ground origin, face toward -Z."""
    rng = rng_for(asset_id, "hide")
    out = M.Group()
    for s in (-1, 1):
        po = M.box(0.085, height + 0.30, 0.085, 0.006, "timber_grey")
        po.translate(s * width * 0.5, (height + 0.30) * 0.5, 0)
        out.add(po)
    for y in (0.28, height + 0.22):
        rl = M.plank(width + 0.14, 0.075, 0.070, 0.005, "timber_grey")
        rl.translate(0, y, 0)
        out.add(rl)
    if not hung:
        return out
    # The hide: a sheet with a real sag and a ragged margin, not a flat quad.
    # Emitted TWICE, the second copy turned about Y — `hide_raw` is not in
    # `materials.DOUBLE_SIDED`, so a single sheet is invisible from behind, and
    # a stretcher frame is a thing a player walks all the way round.
    for turn in (0.0, np.pi):
        hd = M.sheet(width - 0.26, height - 0.36,
                     lambda u, v: -0.055 * np.sin(u * 3.1) * np.sin(v * 3.1)
                     - 0.02 * np.cos(u * 7.0),
                     nx=9, nz=9, mat="hide_raw", plane="xy")
        hd.rotate_y(turn)
        hd.translate(0, 0.28 + (height - 0.36) * 0.5 + 0.12,
                     -0.03 + (0.012 if turn else 0.0))
        out.add(hd)
    # The lacing, which is what makes it a stretched hide and not a curtain.
    for i in range(7):
        x = -(width - 0.26) * 0.5 + (i + 0.5) * (width - 0.26) / 7
        out.add(M.tube((x, height + 0.22, 0.0),
                       (x + rng.uniform(-0.03, 0.03), height - 0.06, -0.03),
                       0.0055, "canvas", 4, 0.0))
        out.add(M.tube((x, 0.28, 0.0), (x + rng.uniform(-0.03, 0.03), 0.42, -0.03),
                       0.0055, "canvas", 4, 0.0))
    for i in range(5):
        y = 0.50 + i * (height - 0.80) / 4
        for s in (-1, 1):
            out.add(M.tube((s * width * 0.5, y, 0.0),
                           (s * (width * 0.5 - 0.14), y + rng.uniform(-0.04, 0.04),
                            -0.03), 0.0055, "canvas", 4, 0.0))
    return out


def _bark_mill(asset_id, radius=0.82):
    """An edge-runner: a stone wheel on its edge in a circular trough.

    The anchor of the venue. Nothing else in Hearthmere looks like this, it is
    two lathes and a beam, and it explains what all the bark is for.
    """
    out = M.Group()
    trough = M.lathe([(1.55, 0), (1.62, 0.42), (1.50, 0.46), (1.44, 0.16),
                      (0.42, 0.16), (0.36, 0.46), (0.24, 0.42), (0.30, 0)],
                     22, "stone")
    out.add(trough)
    hub = M.lathe([(0.26, 0), (0.24, 1.35)], 10, "oak_dark")
    hub.translate(0, 0.46, 0)
    out.add(hub)
    wheel = M.lathe([(0.0, 0), (radius * 0.55, 0.02), (radius, 0.10),
                    (radius, 0.24), (radius * 0.55, 0.32), (0.0, 0.34)], 20,
                    "stone")
    wheel.rotate_z(np.pi * 0.5)
    wheel.translate(0.95, radius + 0.16, 0)
    out.add(wheel)
    # The beam from the hub to the wheel's axle, and the shaft the horse walks.
    out.add(M.plank(1.25, 0.16, 0.14, 0.008, "oak_dark")
            .translate(0.48, radius + 0.16, 0))
    out.add(M.plank(2.20, 0.13, 0.12, 0.008, "oak_weathered")
            .translate(-1.30, 1.05, 0))
    return out


def build(ctx: VenueContext, asset_id=ASSET):
    p = Site(slot=SLOT, ctx=ctx, asset_id=asset_id)
    rng = rng_for(asset_id, "tannery")

    # ------------------------------------------------------------------ yard
    yard = M.box(p.w + 1.0, 0.10, p.d + 1.0, 0.035, "mud",
                 uv_scale=ctx.uv_scale("mud"))
    yard.translate(0, 0.05, 0)
    p.emit(yard)
    p.collider("box", center=(0, 0.05, 0),
               half=((p.w + 1.0) * 0.5, 0.05, (p.d + 1.0) * 0.5),
               kind="surface", tag="yard")

    # The stain, as a gradient and not a blanket: black at the pit lips, brown
    # in the lanes, and the plot's far corner still has weeds on it.
    for i, (sx, sz, size, mat) in enumerate([
            (-1.2, -0.4, 6.4, "stained_dark"), (2.6, -1.6, 4.6, "stained"),
            (-4.2, 2.2, 4.0, "stained"), (1.0, 3.2, 5.0, "stained_dark"),
            (4.6, 2.6, 3.4, "stained")]):
        s2 = P.worn_patch(f"{asset_id}.stain.{i}", shape="cat", size=size,
                          mat=mat)
        s2.rotate_y(rng.uniform(0, 3.0))
        s2.translate(sx, 0.104, sz)
        p.emit(s2)

    # The runnel: an open board channel taking the spent liquor off the platform
    # and away down the slope to the water. It is the reason the tannery is
    # sited where it is, so it is built rather than implied.
    for i in range(9):
        t = i / 8.0
        seg = M.chamfered_prism([(-0.24, 0), (0.24, 0), (0.20, 0.16),
                                 (-0.20, 0.16)], 0.72, "pine_tarred", 0.006)
        seg.rotate_y(0.34)
        seg.translate(-1.9 - t * 4.4, 0.10 + 0.02, 1.4 + t * 3.6)
        p.emit(seg)
        wet = M.box(0.32, 0.02, 0.66, 0.004, "stained_dark")
        wet.rotate_y(0.34)
        wet.translate(-1.9 - t * 4.4, 0.10 + 0.10, 1.4 + t * 3.6)
        p.emit(wet)

    # -------------------------------------------------------- the pit yard
    pits, centres, PW, PD = _pit_yard(f"{asset_id}.pits", ctx, cols=6, rows=4)
    PX, PZ = -0.6, -0.9
    pits.translate(PX, 0.10, PZ)
    p.emit(pits, container="platform", shell=True)
    p.collider("box", center=(PX, 0.10 + PLAT_H * 0.5, PZ),
               half=(PW * 0.5, PLAT_H * 0.5, PD * 0.5), kind="surface",
               tag="pit_platform")
    p.collider_steps(front=(PX + PW * 0.35, 0.10, PZ - PD * 0.5 - 0.30),
                     height=PLAT_H, tread=0.46, width=1.8)

    p.entity(f"{asset_id}.station.01", "crafting_station.tanner",
             (PX, 0.10 + PLAT_H, PZ), verbs=["use"],
             crafting_station={"profession": "tanner", "tier": 1})

    # A hide half in and half out of one pit, over a pole — the single object
    # that says the pits are not decorative.
    px0, pz0, _ = centres[9]
    pole = M.lathe([(0.045, 0), (0.040, 1.55)], 7, "oak_weathered")
    pole.rotate_z(np.pi * 0.5)
    pole.rotate_y(0.15)
    pole.translate(PX + px0 - 0.75, 0.10 + PLAT_H + 0.10, PZ + pz0)
    p.emit(pole)
    drape = M.sheet(0.95, 1.25,
                    lambda u, v: -0.10 * np.sin(u * 2.6) - 0.05 * v,
                    nx=7, nz=7, mat="hide_raw", plane="xy")
    drape.rotate_x(1.35)
    drape.translate(PX + px0, 0.10 + PLAT_H - 0.02, PZ + pz0 - 0.10)
    p.emit(drape)

    # Poles and paddles left across the curbs, and the lime tub.
    for i in range(4):
        pl = M.lathe([(0.032, 0), (0.028, 2.05)], 6, "oak_weathered")
        pl.rotate_z(np.pi * 0.5)
        pl.rotate_y(rng.uniform(-0.4, 0.4) + (0 if i % 2 else np.pi * 0.5))
        pl.translate(PX + rng.uniform(-2.2, 2.2), 0.10 + PLAT_H + 0.09,
                     PZ + rng.uniform(-1.8, 1.8))
        p.emit(pl)
    lime = K.barrel(f"{asset_id}.lime", height=0.95, belly=0.74)
    lime.translate(PX - PW * 0.5 - 0.75, 0.10, PZ - 1.4)
    p.emit(lime)
    limefill = M.lathe([(0.0, 0.80), (0.34, 0.80)], 12, "limewash",
                       close_bottom=False, close_top=False)
    limefill.translate(PX - PW * 0.5 - 0.75, 0.10, PZ - 1.4)
    p.emit(limefill)
    p.collider("cylinder", center=(PX - PW * 0.5 - 0.75, 0.10 + 0.48, PZ - 1.4),
               radius=0.38, height=0.95, tag="lime_tub")

    # ------------------------------------------------------- the drying shed
    # Louvred on every face — the whole point of a drying shed is that the air
    # gets through and the sun does not, so it is boarded with a slat gap and
    # every board is raked. `open_gable` leaves the ends open for the draught.
    SX, SZ = p.w * 0.5 - 3.2, p.back - SHED_D * 0.5
    shed = K.open_range(
        f"{asset_id}.shed", 6.0, SHED_D, 3.60, pitch=0.72, overhang=0.62,
        roof_mat="terracotta", walls=(), plinth=0.0, open_gable=True,
        bays=2, tag="drying")
    shed.translate(SX, 0.10, SZ)
    p.emit(shed, container="shed", shell=True)
    for i in range(3):
        px = SX - 3.0 + i * 3.0
        for pz in (SZ - SHED_D * 0.5, SZ + SHED_D * 0.5):
            p.collider("box", center=(px, 0.10 + 1.80, pz),
                       half=(0.15, 1.80, 0.15), tag="post")
    # The louvres: raked slats on the two long faces, with a 0.10 m gap.
    for pz, sgn in ((SZ - SHED_D * 0.5, -1), (SZ + SHED_D * 0.5, 1)):
        for j in range(16):
            y = 0.62 + j * 0.24
            if y > 3.60 - 0.30:
                break
            lv = M.plank(5.9, 0.22, 0.032, 0.004, "timber_grey")
            lv.rotate_x(sgn * 0.62)
            lv.translate(SX, y, pz - sgn * 0.04)
            p.emit(lv)
    for sx2 in (-1, 1):                       # end frames, left open
        for j in range(3):
            po = M.box(0.12, 3.40, 0.12, 0.006, "timber_grey")
            po.translate(SX + sx2 * 3.0, 1.80,
                         SZ + (j - 1) * SHED_D * 0.5)
            p.emit(po)

    # Hides hanging inside it, in ranks.
    for i in range(6):
        hd = M.sheet(1.35, 1.95,
                     lambda u, v: -0.07 * np.sin(u * 3.1) * (1.0 - v),
                     nx=7, nz=7, mat="hide_raw", plane="xy")
        hd.rotate_y(np.pi * 0.5 + rng.uniform(-0.06, 0.06))
        hd.translate(SX - 2.35 + i * 0.95, 0.10 + 1.25, SZ + rng.uniform(-0.3, 0.3))
        p.emit(hd)
        hd2 = M.sheet(1.35, 1.95,
                      lambda u, v: -0.07 * np.sin(u * 3.1) * (1.0 - v),
                      nx=7, nz=7, mat="hide_raw", plane="xy")
        hd2.rotate_y(-np.pi * 0.5)
        hd2.translate(SX - 2.35 + i * 0.95, 0.10 + 1.25, SZ + 0.012)
        p.emit(hd2)
    for j in range(2):
        rl = M.lathe([(0.045, 0), (0.042, 5.8)], 6, "oak_weathered")
        rl.rotate_z(np.pi * 0.5)
        rl.translate(SX, 0.10 + 3.25, SZ - 0.35 + j * 0.70)
        p.emit(rl)

    # ------------------------------------------------------ beam and knives
    beam = P.tanner_kit(f"{asset_id}.beam", wall_z=1.05)
    beam.rotate_y(-0.42)
    beam.translate(SX - 4.7, 0.10, SZ - 1.15)
    p.emit(beam)
    p.collider("box", center=(SX - 4.7, 0.10 + 0.55, SZ - 1.15),
               half=(0.90, 0.55, 0.55), rot_y=-0.42, tag="beam")

    # A pile of scud — the hair and lime scraped off the hides. Nothing else in
    # the town is this unpleasant and that is exactly what the brief asked for.
    scud = M.lathe([(0.72, 0), (0.62, 0.16), (0.30, 0.30), (0.0, 0.34)], 12,
                   "fleece")
    scud.translate(SX - 4.7 + 1.1, 0.10, SZ - 1.9)
    p.emit(scud)
    for i in range(14):
        a, d = rng.uniform(0, 6.283), rng.uniform(0, 0.9)
        tf = M.chamfered_prism([(0, 0), (0.14, 0.02), (0.0, 0.045)], 0.004,
                               "fleece", 0.001)
        tf.rotate_x(np.pi * 0.5)
        tf.rotate_y(rng.uniform(0, 6.28))
        tf.translate(SX - 3.6 + np.cos(a) * d, 0.11, SZ - 1.9 + np.sin(a) * d)
        p.emit(tf)

    # ------------------------------------------------- hides on stretchers
    for i, (hx, hz, ang, hung) in enumerate([
            (-p.w * 0.5 + 1.15, -2.7, 0.10, True),
            (-p.w * 0.5 + 1.05, -0.7, -0.06, True),
            (-p.w * 0.5 + 1.20, 1.3, 0.16, True),
            (-p.w * 0.5 + 1.10, 3.2, -0.12, False)]):
        fr = _hide_frame(f"{asset_id}.stretch.{i}", width=1.65, height=2.05,
                         hung=hung)
        fr.rotate_y(np.pi * 0.5 + ang)
        fr.translate(hx, 0.10, hz)
        p.emit(fr)
        p.collider("box", center=(hx, 0.10 + 1.15, hz), half=(0.14, 1.15, 0.90),
                   rot_y=ang, tag="stretcher")

    # ------------------------------------------------------- bark and mill
    mill = _bark_mill(f"{asset_id}.mill", radius=0.80)
    mill.rotate_y(0.7)
    mill.translate(p.w * 0.5 - 2.0, 0.10, p.front + 2.2)
    p.emit(mill)
    p.collider("cylinder", center=(p.w * 0.5 - 2.0, 0.10 + 0.30, p.front + 2.2),
               radius=1.62, height=0.60, tag="bark_mill")
    p.collider("cylinder", center=(p.w * 0.5 - 2.0, 0.10 + 0.95, p.front + 2.2),
               radius=0.34, height=1.30, tag="mill_hub")
    ring = P.worn_patch(f"{asset_id}.millwalk", shape="cat", size=5.4,
                        mat="stained_dark")
    ring.translate(p.w * 0.5 - 2.0, 0.104, p.front + 2.2)
    p.emit(ring)

    # Oak bark drying in a stack under a scrap board roof, and ground tan in
    # sacks beside the mill.
    bark = M.Group()
    for c in range(5):
        n = 6 - c // 2
        for i in range(n):
            b = M.chamfered_prism([(-0.20, 0), (0.20, 0), (0.16, 0.055),
                                   (-0.17, 0.05)], 0.85, "oak_dark", 0.004)
            b.rotate_y(rng.uniform(-0.12, 0.12) + (np.pi * 0.5 if c % 2 else 0))
            b.translate(-(n - 1) * 0.5 * 0.30 + i * 0.30 + rng.uniform(-0.03, 0.03),
                        0.08 + c * 0.14, rng.uniform(-0.06, 0.06))
            bark.add(b)
    bark.translate(p.w * 0.5 - 1.8, 0.10, p.back - 2.0)
    p.emit(bark)
    p.collider("box", center=(p.w * 0.5 - 1.8, 0.10 + 0.42, p.back - 2.0),
               half=(1.05, 0.42, 0.75), tag="bark_stack")
    for i in range(4):
        bd = M.plank(2.4, 0.55, 0.038, 0.005, "timber_grey")
        bd.rotate_z(0.10)
        bd.translate(p.w * 0.5 - 1.8, 0.10 + 0.86 + i * 0.02,
                     p.back - 2.6 + i * 0.52)
        p.emit(bd)
    for i in range(3):
        sk = K.sack(f"{asset_id}.tan.{i}", height=0.52, mat="sacking")
        sk.rotate_y(rng.uniform(0, 3.0))
        sk.translate(p.w * 0.5 - 3.6 + i * 0.55, 0.10, p.front + 3.4)
        p.emit(sk)

    # ------------------------------------------------------------- residue
    cart = P.handcart(f"{asset_id}.cart")
    cart.rotate_y(2.6)
    cart.translate(-2.4, 0.10, p.front + 1.1)
    p.emit(cart)
    p.collider("box", center=(-2.4, 0.10 + 0.55, p.front + 1.1),
               half=(0.80, 0.55, 0.80), tag="handcart")

    for i, (bx, bz) in enumerate([(-4.9, -3.6), (-5.5, -3.0)]):
        bk = P.bucket(f"{asset_id}.bkt.{i}", full=True)
        bk.rotate_y(rng.uniform(0, 3.0))
        bk.translate(bx, 0.10, bz)
        p.emit(bk)

    # The last green thing on the plot, in the corner the liquor never reaches.
    for i in range(7):
        sb = P.shrub(f"{asset_id}.weed.{i}", radius=0.42, height=0.55) \
            if hasattr(P, "shrub") else None
        if sb is None:
            break
        sb.translate(-p.w * 0.5 + rng.uniform(0.2, 1.4), 0.10,
                     p.back - rng.uniform(0.2, 1.6))
        p.emit(sb)

    for i in range(4):
        cl = K.leaf_cluster(f"{asset_id}.nettle.{i}", radius=0.16, count=7,
                            mat="foliage", droop=0.5)
        cl.translate(-p.w * 0.5 + rng.uniform(0.2, 1.6), 0.11,
                     p.back - rng.uniform(0.2, 2.0))
        p.emit(cl)
