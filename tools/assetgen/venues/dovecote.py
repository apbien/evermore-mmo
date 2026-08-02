"""The glebe dovecote — slot 57, The Bailey.

`docs/plan/schedule.md`: *"Circular, coursed rubble, conical tiled roof to 7.6 m
with a lantern. 240 nest boxes. The only round building in Hearthmere and worth
the whole quarter for silhouette."*

The schedule is right about why it matters. Every other mass in this town is a
rectangle with a ridge, and one 5.4 m drum with a cone on it does more for an
aerial or a silhouette than three more houses would. It is also the cheapest
hero shape in the build: four lathes and a band of holes.

## The three details that make it a dovecote and not a silo

1. **The rat ledge.** A projecting string course two-thirds of the way up,
   oversailing 0.22 m, with its top surface smooth. A rat can climb coursed
   rubble; it cannot get round that. Every real dovecote has one, and its
   shadow is also the only horizontal on the elevation.
2. **The flight holes and the alighting ledge.** A band of small square holes
   under the eaves with a continuous stone ledge under them, worn and stained.
   That is where the birds land, so that is the part of the building that is
   white.
3. **The potence.** A vertical post on a pintle in the middle of the floor with
   two arms and a ladder on them, which the boy swings round to reach all 240
   boxes. Visible through the open door, and it is the object that explains
   what the building is for.

Doves are creatures and creatures are out of scope (`BUILD_DIRECTIVE` §1), so
the birds are not modelled. What is modelled is everything they leave behind.
"""

from __future__ import annotations

import numpy as np

from core import kit as K
from core import mesh as M
from core import props as P
from core.mathx import rng_for
from core.siting import Site
from core.venue import VenueContext

NAME = "dovecote"
SLOT = 57
CELLS = ["J5", "J6", "K5", "K6"]

ASSET = "hm.dovecote"

R_OUT = 2.72            # outside radius at the base
WALL_T = 0.52
EAVES = 6.2
CONE_TOP = 7.6
SEG = 26


def build(ctx: VenueContext, asset_id=ASSET):
    p = Site(slot=SLOT, ctx=ctx, asset_id=asset_id)
    rng = rng_for(asset_id, "dovecote")

    # ------------------------------------------------------------- the ground
    # No hardstanding: this stands on the glebe, in grass, and the only worn
    # ground is the path to the door and the ring the boy walks round it.
    ring = P.worn_patch(f"{asset_id}.ring", shape="cat", size=7.2,
                        mat="grass_worn")
    ring.translate(0, 0.02, 0)
    p.emit(ring)
    path = P.worn_patch(f"{asset_id}.path", shape="path", size=4.0, mat="dirt")
    path.rotate_y(0.08)
    path.translate(0, 0.03, p.front + 1.4)
    p.emit(path)

    # ------------------------------------------------------------- the drum
    # Battered: 2.72 m at the base to 2.48 m at the eaves. A straight-sided
    # drum reads as a tank; the batter is what makes it read as built.
    prof = [(R_OUT, 0.0), (R_OUT - 0.05, 0.55), (R_OUT - 0.14, 3.60)]
    RL_Y = 3.95                                   # the rat ledge
    prof += [(R_OUT - 0.16, RL_Y - 0.10), (R_OUT + 0.22, RL_Y - 0.04),
             (R_OUT + 0.22, RL_Y + 0.10), (R_OUT - 0.20, RL_Y + 0.16),
             (R_OUT - 0.24, EAVES)]
    drum = M.lathe(prof, SEG, "rubble", close_bottom=True, close_top=False,
                   uv_scale=ctx.uv_scale("rubble"))
    p.emit(drum, container="drum", shell=True)

    # Inner face, so the doorway is a hole through a WALL and not through a
    # sheet. Wound inward by lathing the inside profile and flipping it.
    inner = M.lathe([(R_OUT - WALL_T, 0.30), (R_OUT - WALL_T - 0.06, EAVES)],
                    SEG, "rubble", close_bottom=False, close_top=False,
                    uv_scale=ctx.uv_scale("rubble"))
    p.emit(inner)
    floor = M.lathe([(0.0, 0.30), (R_OUT - WALL_T, 0.30)], SEG, "stone",
                    close_bottom=False, close_top=False,
                    uv_scale=ctx.uv_scale("stone"))
    p.emit(floor)

    # Plinth course, splayed, so the wall meets the grass at a made edge.
    plin = M.lathe([(R_OUT + 0.26, 0.0), (R_OUT + 0.24, 0.22),
                    (R_OUT + 0.02, 0.40)], SEG, "ashlar",
                   uv_scale=ctx.uv_scale("ashlar"))
    p.emit(plin)

    # Collision: a ring of segment boxes, with the doorway left OUT. A single
    # cylinder would have sealed the door, and the door is the whole point.
    DOOR_A = 0.0                                  # doorway faces the street
    for i in range(SEG):
        a = 2 * np.pi * (i + 0.5) / SEG
        # Skip the two segments the doorway occupies.
        da = (a - DOOR_A + np.pi) % (2 * np.pi) - np.pi
        if abs(da) < (2 * np.pi / SEG) * 1.05:
            continue
        cx, cz = np.sin(a) * (R_OUT - WALL_T * 0.5), -np.cos(a) * (R_OUT - WALL_T * 0.5)
        p.collider("box", center=(cx, EAVES * 0.5, cz),
                   half=(np.pi * R_OUT / SEG * 1.15, EAVES * 0.5, WALL_T * 0.5),
                   rot_y=-a, tag="drum")

    # ------------------------------------------------- flight holes and ledge
    LEDGE_Y = EAVES - 1.05
    ledge = M.lathe([(R_OUT - 0.22, LEDGE_Y - 0.02), (R_OUT + 0.30, LEDGE_Y + 0.02),
                     (R_OUT + 0.30, LEDGE_Y + 0.12), (R_OUT - 0.22, LEDGE_Y + 0.14)],
                    SEG, "ashlar", close_bottom=False, close_top=False,
                    uv_scale=ctx.uv_scale("ashlar"))
    p.emit(ledge)
    # Two staggered rows of holes over it. Square, small, and dark inside —
    # `oak_dark` reveals rather than a black face, so the hole has depth.
    for row, (y, off) in enumerate(((LEDGE_Y + 0.30, 0.0), (LEDGE_Y + 0.62, 0.5))):
        for i in range(14):
            a = 2 * np.pi * (i + off) / 14
            if abs(((a - DOOR_A + np.pi) % (2 * np.pi)) - np.pi) < 0.34:
                continue
            r = R_OUT - 0.235
            h = M.box(0.19, 0.22, 0.30, 0.008, "oak_dark")
            h.rotate_y(-a)
            h.translate(np.sin(a) * r, y, -np.cos(a) * r)
            p.emit(h)
            sill = M.box(0.30, 0.045, 0.16, 0.006, "ashlar",
                         uv_scale=ctx.uv_scale("ashlar"))
            sill.rotate_y(-a)
            sill.translate(np.sin(a) * (r + 0.10), y - 0.13, -np.cos(a) * (r + 0.10))
            p.emit(sill)

    # The whitewash under the holes. Not a texture: a band of `limewash` panels
    # streaked down the wall from each perch, which is what a colony actually
    # does to a wall and the reason a real dovecote is white on one band only.
    for i in range(24):
        a = rng.uniform(0, 6.283)
        if abs(((a - DOOR_A + np.pi) % (2 * np.pi)) - np.pi) < 0.40:
            continue
        h = rng.uniform(0.45, 1.55)
        st = M.box(rng.uniform(0.10, 0.26), h, 0.022, 0.004, "limewash",
                   uv_scale=ctx.uv_scale("limewash"))
        st.rotate_y(-a)
        st.translate(np.sin(a) * (R_OUT - 0.215), LEDGE_Y - 0.06 - h * 0.5,
                     -np.cos(a) * (R_OUT - 0.215))
        p.emit(st)

    # ---------------------------------------------------------- the doorway
    DW, DH = 0.95, 1.85
    for s in (-1, 1):                             # ashlar jambs
        j = M.box(0.26, DH + 0.18, WALL_T + 0.10, 0.012, "ashlar",
                  uv_scale=ctx.uv_scale("ashlar"))
        j.translate(s * (DW * 0.5 + 0.13), 0.30 + (DH + 0.18) * 0.5, -R_OUT + WALL_T * 0.5)
        p.emit(j)
    lint = M.box(DW + 0.60, 0.24, WALL_T + 0.14, 0.012, "ashlar",
                 uv_scale=ctx.uv_scale("ashlar"))
    lint.translate(0, 0.30 + DH + 0.30, -R_OUT + WALL_T * 0.5)
    p.emit(lint)
    step = M.box(DW + 0.70, 0.16, 0.62, 0.02, "stone",
                 uv_scale=ctx.uv_scale("stone"))
    step.translate(0, 0.14, -R_OUT - 0.24)
    p.emit(step)
    p.collider("box", center=(0, 0.14, -R_OUT - 0.24), half=(0.83, 0.14, 0.31),
               kind="surface", tag="doorstep")

    door = K.plank_door(f"{asset_id}.door", width=DW, height=DH,
                        mat="oak_weathered", open_angle=1.35)
    door.translate(-DW * 0.5 + 0.04, 0.30, -R_OUT - 0.10)
    p.emit(door)
    p.entity(f"{asset_id}.door.01", "door.dovecote", (0, 0.30, -R_OUT - 0.05),
             verbs=["enter"])

    # ------------------------------------------ nest boxes and the potence
    # The interior is only ever seen through the door, so the boxes are built
    # on the three segments the doorway actually looks at. `props.dovecote_holes`
    # is the shared panel; four of them wrapped round the back wall.
    for i, a in enumerate((-0.62, 0.0, 0.62)):
        panel = P.dovecote_holes(f"{asset_id}.nest.{i}", width=1.55, height=3.10,
                                 wall_z=0.0, rows=9, cols=6)
        panel.rotate_y(a + np.pi)
        panel.translate(np.sin(a) * (R_OUT - WALL_T - 0.03),
                        0.70, -np.cos(a) * (R_OUT - WALL_T - 0.03))
        p.emit(panel)

    # The potence: a post on a pintle, two arms, a ladder between them.
    post = M.lathe([(0.13, 0), (0.115, 5.3), (0.10, 5.55)], 9, "oak_dark")
    post.translate(0, 0.30, 0)
    p.emit(post)
    p.collider("cylinder", center=(0, 0.30 + 2.8, 0), radius=0.16, height=5.6,
               tag="potence")
    for y, ln in ((1.35, 1.95), (4.45, 1.95)):
        arm = M.plank(ln, 0.13, 0.10, 0.006, "oak_weathered")
        arm.rotate_y(0.55)
        arm.translate(np.cos(0.55) * ln * 0.5 * 0, 0.30 + y, 0)
        arm.translate(np.sin(0.55) * ln * 0.5, 0, -np.cos(0.55) * ln * 0.5)
        p.emit(arm)
    # The ladder hung between the two arms.
    lx, lz = np.sin(0.55) * 1.86, -np.cos(0.55) * 1.86
    for s in (-1, 1):
        st = M.tube((lx + s * 0.19, 0.30 + 1.30, lz),
                    (lx + s * 0.19, 0.30 + 4.50, lz), 0.030, "oak_weathered",
                    5, 0.002)
        p.emit(st)
    for i in range(11):
        rg = M.tube((lx - 0.19, 0.30 + 1.42 + i * 0.30, lz),
                    (lx + 0.19, 0.30 + 1.42 + i * 0.30, lz), 0.020,
                    "oak_weathered", 5, 0.002)
        p.emit(rg)

    # ------------------------------------------------------------- the cone
    # Tiled, in real courses, so the silhouette has a texture at 100 m and not
    # just an outline. It oversails the drum by 0.30 m, which is what puts the
    # eaves shadow on the flight holes.
    R_EAVE = R_OUT - 0.24 + 0.34
    courses = 15
    for c in range(courses):
        t0, t1 = c / courses, (c + 1) / courses
        r0 = R_EAVE * (1 - t0) + 0.16 * t0
        r1 = R_EAVE * (1 - t1) + 0.16 * t1
        y0 = EAVES + t0 * (CONE_TOP - EAVES - 0.55)
        y1 = EAVES + t1 * (CONE_TOP - EAVES - 0.55)
        band = M.lathe([(r0 + 0.055, y0), (r1 + 0.055, y1),
                        (r1, y1 + 0.02), (r0, y0 + 0.02)], SEG, "terracotta",
                       close_bottom=False, close_top=False,
                       uv_scale=ctx.uv_scale("terracotta"))
        p.emit(band)
    soffit = M.lathe([(R_OUT - 0.24, EAVES), (R_EAVE + 0.06, EAVES - 0.10)], SEG,
                     "oak_dark", close_bottom=False, close_top=False)
    p.emit(soffit)

    # ------------------------------------------------------------ the lantern
    # The birds' own door. A louvred drum with its own little cone on top; the
    # louvres are what stop the rain coming straight down onto the nests.
    LY = CONE_TOP - 0.55
    for i in range(10):
        a = 2 * np.pi * i / 10
        po = M.box(0.075, 0.62, 0.075, 0.005, "oak_dark")
        po.rotate_y(-a)
        po.translate(np.sin(a) * 0.44, LY + 0.31, -np.cos(a) * 0.44)
        p.emit(po)
    for j in range(3):
        lv = M.lathe([(0.50, 0), (0.42, 0.11)], 12, "oak_weathered",
                     close_bottom=False, close_top=False)
        lv.translate(0, LY + 0.10 + j * 0.18, 0)
        p.emit(lv)
    cap = M.lathe([(0.60, LY + 0.66), (0.36, LY + 0.90), (0.0, LY + 1.10)], 12,
                  "terracotta", close_bottom=False,
                  uv_scale=ctx.uv_scale("terracotta"))
    p.emit(cap, container="lantern_cap")
    # The finial stands 0.36 m PROUD of the cap it finishes. The first pass sat
    # it at the apex, so the two topped out at the same 8.57 m and the venue's
    # highest point was a cone with a spike inside it — which the occlusion
    # tripwire caught, and which would have cost the whole silhouette benefit
    # the schedule buys this building for.
    fin = M.lathe([(0.055, 0), (0.030, 0.22), (0.075, 0.28), (0.0, 0.46)], 8,
                  "iron")
    fin.translate(0, LY + 1.00, 0)
    p.emit(fin, label="finial")

    # An authored LOD chain: the cone and the lantern are what this building
    # contributes to the skyline, and the automatic vertex clusterer eats a
    # finial. See BUILD_DIRECTIVE section 7.
    # (Left to the default decimator for the drum, which survives it.)

    # ------------------------------------------------------------- residue
    # Feathers and droppings, thickest under the alighting ledge and on the
    # step. This is the one part of the venue a player is close enough to read.
    for i in range(30):
        a = rng.uniform(0, 6.283)
        d = R_OUT + rng.uniform(0.15, 1.45)
        fe = M.chamfered_prism([(0, 0), (0.11, 0.018), (0.0, 0.034)], 0.002,
                               "canvas_plain", 0.0008)
        fe.rotate_x(np.pi * 0.5)
        fe.rotate_y(rng.uniform(0, 6.28))
        fe.translate(np.cos(a) * d, 0.035, np.sin(a) * d)
        p.emit(p.drape(fe))
    # Droppings follow the ground, and the ground here falls. Authored flat at
    # local y = 0.03 this ran from +0.44 m in clear air on the uphill side to
    # 0.36 m buried on the downhill side across one 2.7 m patch, and the buried
    # end was a validate failure — an isolated mass entirely below terrain.
    drop = P.spill(f"{asset_id}.drop", kind="flour", radius=1.35, density=0.55,
                   vessel=False)
    drop.translate(0.6, 0.03, -R_OUT - 0.9)
    p.emit(p.drape(drop))

    # A ladder left against the wall, a basket for the eggs, and the sack of
    # squab feed that explains why the door is open.
    lad = M.Group()
    for s in (-1, 1):
        lad.add(M.tube((s * 0.21, 0, 0), (s * 0.21, 3.05, 0), 0.032,
                       "oak_weathered", 5, 0.002))
    for i in range(10):
        lad.add(M.tube((-0.21, 0.28 + i * 0.30, 0), (0.21, 0.28 + i * 0.30, 0),
                       0.021, "oak_weathered", 5, 0.002))
    P.lean(lad, 3.05, 0.72, wall_z=-R_OUT - 0.02, x=1.75,
           roll=rng.uniform(-0.03, 0.03))
    p.emit(lad)

    bsk = P.basket(f"{asset_id}.basket", radius=0.24, height=0.30, handle=True)
    bsk.rotate_y(0.7)
    bsk.translate(-1.35, 0.02, -R_OUT - 0.55)
    p.emit(bsk)
    sk = K.sack(f"{asset_id}.feed", height=0.48)
    sk.rotate_y(1.2)
    sk.translate(-1.05, 0.30, -R_OUT + 0.85)
    p.emit(sk)

    p.entity(f"{asset_id}.cote.01", "resource.dovecote", (0, 0.30, 0),
             verbs=["gather"],
             resource={"kind": "squab", "respawnMin": 45})
