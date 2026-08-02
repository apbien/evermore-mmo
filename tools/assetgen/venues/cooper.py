"""The cooper — slot 33, Bakers' Row.

A cask is the only container this world has for anything wet, so the cooper is
not a picturesque trade, he is infrastructure: the brewery, the tannery, the
quay and the inn all buy from this yard. That is the reason the venue is worth
building well — it explains half the other props in Hearthmere.

## Why it is arranged the way it is

A cask is made in one direction and the shop is laid out along it. Standing in
Bakers' Row and looking in, the player reads the whole process left to right
without being told a word of it:

    RAW          riven staves in cones, seasoning in the open west end, and
                 the cleft billets they were riven from
    HOLLOW       the shaving horse and the long jointer, where a stave stops
                 being a board
    RAISE        the raising-up — seventeen staves stood in a truss hoop,
                 splayed at the foot like a flower. This is the silhouette
                 that says COOPER from across the street and it is the middle
                 of the shop because it is the middle of the job
    FIRE         the setting fire, out in the open where a fire belongs in a
                 timber town, with the cask over it and the windlass rope on
                 the truss
    HEAD         the block with the croze and the adze on it, the next two
                 cuts, and the hoops graded on the back wall
    FINISHED     the cask pyramid by the kerb, where the carrier picks up

Nothing is symmetrical and nothing is centred. Art Bible §7: a working person
arranges by workflow, and the shop is the strongest evidence of that rule in
the town after the forge.

## Open-fronted

Roofed, not walled, on the street side — the same decision as the blacksmith,
for the same reasons: the fire wants air, the staves want air, and the player
wants to see the work. The side walls are boarded only to waist height, which
is what keeps the wind off the setting fire without taking the light.
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

NAME = "cooper"
SLOT = 33
CELLS = ["I8", "I9"]

ASSET = "hm.cooper"

# The range sits back in the plot and the yard is the strip it leaves toward
# the street. 6.2 m of covered floor is a real setting-up floor: the raising-up
# needs a clear 2 m round it and the jointer is 1.9 m long on its own.
RANGE_D = 6.2
EAVES = 5.2
PITCH = 0.72        # a 10 m plot at the kit's 0.86 would put the ridge at
                    # 10.2 m — taller than the bakery, on a one-storey shed.


def _stave_cone(asset_id, count=13, height=2.15, radius=0.34, mat="oak"):
    """Riven staves stood in a cone to season. Ground origin.

    A cone, not a stack: staves are stood on end and leant together so the air
    gets at every face, and the resulting tepee is the shape a timber yard
    actually has in it. It is also cheap — thirteen boxes — and it reads as
    cooper from thirty metres, which is what the west end of the yard is for.
    """
    rng = rng_for(asset_id, "cone")
    out = M.Group()
    for i in range(count):
        a = 2 * np.pi * i / count + rng.uniform(-0.09, 0.09)
        h = height * rng.uniform(0.92, 1.06)
        r = radius * rng.uniform(0.88, 1.12)
        st = M.chamfered_prism([(-0.058, 0), (0.058, 0), (0.046, 1.0),
                                (-0.046, 1.0)], 0.024, mat, 0.003)
        st.scale(1.0, h, 1.0)
        # Lean the head IN toward the axis. `rotate_x` tips the head toward
        # local +Z, so the yaw that aims that at the axis from a foot at
        # azimuth `a` is -(a + pi/2), not `a` — get that wrong and the cone
        # comes out as a fan of staves splaying outward, which is what the
        # first pass rendered.
        st.rotate_x(float(np.arctan2(r * 0.86, h)))
        st.rotate_y(-(a + np.pi * 0.5))
        st.translate(np.cos(a) * r, 0.0, np.sin(a) * r)
        out.add(st)
    return out


def _cask_pyramid(asset_id, rows=3, unit=0.62, height=0.88):
    """Finished casks stacked bilge-up in a pyramid. Ground origin, axis +X.

    Casks are stacked on their sides with the bung uppermost and chocked, and
    a pyramid is how the bottom row is kept from rolling. It is the one place
    in the venue where a regular arrangement is CORRECT, because the geometry
    of a round thing on a flat floor makes it so.
    """
    rng = rng_for(asset_id, "pyramid")
    out = M.Group()
    for r in range(rows):
        n = rows - r
        for i in range(n):
            c = P.barrel_lying(f"{asset_id}.{r}{i}", height=height, belly=unit)
            c.rotate_y(rng.uniform(-0.035, 0.035))
            c.translate(-(n - 1) * unit * 0.5 + i * unit + rng.uniform(-0.02, 0.02),
                        r * unit * 0.86, rng.uniform(-0.03, 0.03))
            out.add(c)
    # Chocks under the bottom row, because a cask that is not chocked rolls.
    for i in range(rows + 1):
        ch = M.chamfered_prism([(-0.10, 0), (0.10, 0), (0.0, 0.09)], 0.13,
                               "oak_weathered", 0.004)
        ch.rotate_y(np.pi * 0.5)
        ch.translate(-rows * unit * 0.5 + i * unit, 0.0, unit * 0.42)
        out.add(ch)
    return out


def _setting_fire(p, asset_id):
    """The firing pit: a cresset of shavings inside a cask being drawn in.

    Setting is the moment the trade turns on. The staves are wetted, a fire of
    the shop's own shavings is lit inside the truss, and the wood gives up and
    comes together under the rope. So the fire is the shop's fuel — which is
    why the shaving heap is next to it and not tidied away — and the windlass
    rope is on the cask, taut, mid-job.

    Plot-frame group; the caller places it.
    """
    rng = rng_for(asset_id, "fire")
    out = M.Group()

    # A sunk hearth ring of rough kerbstones — a fire in a timber yard is
    # never on the bare floor, and the ring is what says somebody thought
    # about that.
    for i in range(11):
        a = 2 * np.pi * i / 11
        k = M.box(rng.uniform(0.20, 0.30), rng.uniform(0.16, 0.24),
                  rng.uniform(0.16, 0.22), 0.02, "stone")
        k.rotate_y(a + rng.uniform(-0.2, 0.2))
        k.translate(np.cos(a) * 0.62, 0.09, np.sin(a) * 0.62)
        out.add(k)

    # Embers. `coal` carries the emissive channel — this is the second real
    # light source in the town after the forge, and it is what makes the
    # cooper's yard read at 09:30 under a deep roof.
    for i in range(26):
        a, d = rng.uniform(0, 6.283), rng.uniform(0.0, 0.46) ** 0.7
        c = M.box(rng.uniform(0.05, 0.11), rng.uniform(0.03, 0.07),
                  rng.uniform(0.05, 0.10), 0.010, "coal")
        c.rotate_y(rng.uniform(0, 3.14))
        c.translate(np.cos(a) * d, 0.045 + rng.uniform(0, 0.03), np.sin(a) * d)
        out.add(c)

    # The cask being set, standing over the fire on a low iron trivet, drawn
    # in at the head by the truss hoops.
    for sx in (-1, 1):
        lg = M.tube((sx * 0.42, 0.0, -0.36), (sx * 0.40, 0.34, 0.0), 0.022,
                    "iron_pitted", 6, 0.002)
        out.add(lg)
        lg2 = M.tube((sx * 0.42, 0.0, 0.36), (sx * 0.40, 0.34, 0.0), 0.022,
                     "iron_pitted", 6, 0.002)
        out.add(lg2)
    ring = M.ring(0.44, 0.030, "iron_pitted", 16)
    ring.translate(0, 0.34, 0)
    out.add(ring)

    cask = K.barrel(f"{asset_id}.cask", height=0.94, belly=0.70)
    cask.translate(0, 0.36, 0)
    out.add(cask)
    # Truss hoops: the wide temporary ones a cooper drives down to draw the
    # head in, sitting proud of the finished hoops.
    for y, r in ((0.62, 0.395), (1.06, 0.345)):
        h = M.ring(r, 0.055, "iron", 18)
        h.rotate_x(rng.uniform(-0.012, 0.012))
        h.translate(0, y, 0)
        out.add(h)
    # The rope still on it, running off to the windlass.
    out.add(M.catenary((0.30, 1.16, 0.0), (1.55, 0.92, -0.55), 0.10,
                       "canvas", 0.017, 8, 4))
    return out


def _windlass(asset_id):
    """The frame the setting rope is drawn down on. Ground origin, axle on X."""
    out = M.Group()
    for sx in (-1, 1):
        po = M.box(0.16, 1.05, 0.16, 0.010, "oak_dark")
        po.translate(sx * 0.44, 0.52, 0)
        out.add(po)
    ax = M.cylinder(0.075, 1.02, 10, 0.006, "oak_weathered")
    ax.rotate_z(np.pi * 0.5)
    ax.translate(0, 0.92, 0)
    out.add(ax)
    for i in range(5):                       # rope wound on the barrel
        r = M.ring(0.088, 0.017, "canvas", 10, tilt=0.0)
        r.rotate_z(np.pi * 0.5)
        r.translate(-0.18 + i * 0.09, 0.92, 0)
        out.add(r)
    hd = M.cylinder(0.028, 0.46, 6, 0.003, "oak_weathered")
    hd.rotate_x(np.pi * 0.5)
    hd.rotate_z(0.5)
    hd.translate(0.50, 0.92, 0.10)
    out.add(hd)
    return out


def _shaving_horse(asset_id):
    """The horse a stave is hollowed on. Ground origin, rider faces -Z.

    A drawknife bench with a foot-treadle clamp: the cooper sits astride it and
    pulls the knife toward himself. It is the most-used object in the shop and
    the one whose seat is worn palest.
    """
    out = M.Group()
    body = M.plank(1.72, 0.30, 0.085, 0.008, "oak_weathered")
    body.rotate_z(-0.075)                     # the head end rides higher
    body.translate(0, 0.58, 0)
    out.add(body)
    for sx, ln in ((-1, 0.62), (1, 0.58)):
        for sz in (-1, 1):
            out.add(M.tube((sx * 0.66, 0.56, sz * 0.06),
                           (sx * 0.80, 0.0, sz * 0.30), 0.035, "oak_weathered",
                           6, 0.003))
    # The swinging head: the arm, the jaw and the treadle under it.
    arm = M.plank(0.62, 0.11, 0.055, 0.006, "oak_dark")
    arm.rotate_z(1.35)
    arm.translate(-0.40, 0.82, 0)
    out.add(arm)
    jaw = M.box(0.20, 0.09, 0.24, 0.006, "oak_dark")
    jaw.translate(-0.52, 1.02, 0)
    out.add(jaw)
    tr = M.plank(0.34, 0.16, 0.035, 0.005, "oak_weathered")
    tr.rotate_z(0.25)
    tr.translate(-0.30, 0.20, 0)
    out.add(tr)
    # A stave still in the jaw, half hollowed — the job left mid-cut.
    st = M.chamfered_prism([(-0.055, 0), (0.055, 0), (0.045, 1.0), (-0.045, 1.0)],
                           0.026, "oak", 0.003)
    st.scale(1.0, 0.95, 1.0)
    st.rotate_z(np.pi * 0.5 + 0.08)
    st.translate(-0.10, 0.94, 0.0)
    out.add(st)
    # The drawknife dropped across it where the hands left it.
    out.add(M.tube((-0.34, 1.00, 0.12), (0.10, 1.00, 0.16), 0.010, "steel_blued",
                   5, 0.002))
    for x in (-0.36, 0.12):
        out.add(M.tube((x, 1.00, 0.13), (x + 0.02, 0.94, 0.20), 0.017, "oak", 5,
                       0.002))
    return out


def _jointer(asset_id):
    """The long jointer: a 2 m plane lying sole-up on splayed legs.

    A cooper does not push the plane, he pushes the stave over it, so the
    plane is a piece of furniture and it lives at the head of the shop. Two
    metres of it is unmistakable and nothing else in the town looks like it.
    """
    out = M.Group()
    sole = M.plank(1.95, 0.16, 0.075, 0.007, "endgrain")
    sole.rotate_z(-0.10)
    sole.translate(0, 0.72, 0)
    out.add(sole)
    cheek = M.plank(1.95, 0.30, 0.026, 0.005, "oak_dark")
    cheek.rotate_z(-0.10)
    cheek.translate(0, 0.60, 0.055)
    out.add(cheek)
    ir = M.box(0.055, 0.10, 0.16, 0.003, "steel_blued")
    ir.rotate_z(-0.10 - 0.38)
    ir.translate(0.10, 0.79, 0)
    out.add(ir)
    for sx in (-1, 1):
        for sz in (-1, 1):
            out.add(M.tube((sx * 0.72, 0.66, 0.0),
                           (sx * 0.86, 0.0, sz * 0.26), 0.036, "oak_weathered",
                           6, 0.003))
    return out


def build(ctx: VenueContext, asset_id=ASSET):
    p = Site(slot=SLOT, ctx=ctx, asset_id=asset_id)
    rng = rng_for(asset_id, "cooper")

    # ------------------------------------------------------------------ yard
    # A cooper's yard is beaten earth with a permanent skin of chips and
    # shavings trodden into it. Laid 0.09 m proud so it clears the height
    # field's own roughness and reads as a made hardstanding, and declared
    # `surface` so it offers a standing height without becoming a 90 mm kerb.
    # `yard` is a pale chip-and-dust surface, and that is the RIGHT colour
    # here: a cooper's floor is oak shavings trodden into chalk dust and it
    # bleaches. It also gives Bakers' Row a light patch against the brown
    # intramural ground the town-02 review calls out in §11.
    yard = M.box(p.w + 0.6, 0.10, p.d + 0.6, 0.035, "yard",
                 uv_scale=ctx.uv_scale("yard"))
    yard.translate(0, 0.05, 0)
    p.emit(yard)
    p.collider("box", center=(0, 0.05, 0),
               half=((p.w + 0.6) * 0.5, 0.05, (p.d + 0.6) * 0.5),
               kind="surface", tag="yard")

    # Wear laid over the pale floor, not islands of it beside — DARK on light,
    # so the marks read as ground that has been used rather than as slabs
    # dropped on the grass. The cart line in from the kerb and the two arcs
    # where a cask gets rolled are the ones a player's eye actually resolves.
    for i, (wx, wz, size, ang, shape) in enumerate([
            (2.3, -3.2, 3.0, 0.12, "path"), (1.1, -0.6, 2.4, -0.4, "path"),
            (-3.4, -1.4, 1.9, 0.6, "path"), (4.2, 1.4, 1.7, -0.2, "cat"),
            (-1.0, 3.4, 2.3, 0.05, "path"), (5.0, -3.6, 1.2, 0.9, "cat")]):
        w = P.worn_patch(f"{asset_id}.wear.{i}", shape=shape, size=size,
                         mat="dirt")
        w.rotate_y(ang)
        w.translate(wx, 0.104, wz)
        p.emit(w)

    # The frontage onto Bakers' Row: the strip carts stand on, worn to dust.
    kerb = M.box(p.w + 0.6, 0.13, 0.26, 0.02, "cobble",
                 uv_scale=ctx.uv_scale("cobble"))
    kerb.translate(0, 0.065, p.front - 0.16)
    p.emit(kerb)

    # ----------------------------------------------------------------- range
    # Set back so the yard in front of it is deep enough to work a fire in.
    rz = p.back - RANGE_D * 0.5
    rng_geom = K.open_range(
        f"{asset_id}.range", p.w - 0.6, RANGE_D, EAVES,
        pitch=PITCH, overhang=0.62, roof_mat="terracotta",
        walls=("back",), half_boarded=("left", "right"),
        plinth=0.0, board_gap=0.055, plot=None, tag="cooper")
    rng_geom.translate(0, 0.10, rz)
    p.emit(rng_geom, container="range", shell=True)

    # No stone plinth under this one. A cooper's setting floor is beaten earth
    # and chips — the same reason the blacksmith's is — because a fire is lit on
    # it and shavings are swept across it all day. What the timber gets instead
    # is a pad stone under each post, which is the real detail: it is how the
    # post foot is kept out of the wet without paving the whole shop.
    for i in range(5):
        px = -(p.w - 0.6) * 0.5 + i * (p.w - 0.6) / 4
        for pz in (rz - RANGE_D * 0.5, rz + RANGE_D * 0.5):
            pad = M.box(0.52, 0.14, 0.52, 0.022, "stone",
                        uv_scale=ctx.uv_scale("stone"))
            pad.rotate_y(rng.uniform(-0.08, 0.08))
            pad.translate(px, 0.13, pz)
            p.emit(pad)

    # Collision by hand rather than through `open_range(plot=...)`, because the
    # range is translated in Z and the helper authors about its own origin.
    # Back wall solid, posts solid, THE WHOLE FRONT OPEN — the player walks in
    # off the street, which is the entire point of the form.
    p.collider("box", center=(0, 0.09 + (EAVES - 0.16) * 0.5, p.back - 0.10),
               half=((p.w - 0.6) * 0.5 + 0.05, (EAVES - 0.16) * 0.5, 0.11),
               tag="back_wall")
    bays = 4
    for i in range(bays + 1):
        px = -(p.w - 0.6) * 0.5 + i * (p.w - 0.6) / bays
        for pz in (rz - RANGE_D * 0.5, rz + RANGE_D * 0.5):
            p.collider("box", center=(px, 0.09 + EAVES * 0.5, pz),
                       half=(0.17, EAVES * 0.5, 0.17), tag="post")
    # The waist-high side screens: a fence, not a wall, so they read solid and
    # the head-height gap above them stays open.
    for sx in (-1, 1):
        p.collider("box", center=(sx * (p.w - 0.6) * 0.5, 0.09 + 0.65, rz),
                   half=(0.09, 0.65, RANGE_D * 0.5), tag="side_screen")

    # A loft over the back two metres of the range, boarded, where the hoops
    # and the dry staves live. It gives the open front a ceiling to look into
    # instead of straight up at the rafters, which is what makes a shed read as
    # a shop.
    loft = M.Group()
    deck = M.box(p.w - 0.7, 0.07, 2.30, 0.008, "oak_weathered")
    deck.translate(0, 2.92, p.back - 1.35)
    loft.add(deck)
    for i in range(9):
        jx = -(p.w - 0.9) * 0.5 + i * (p.w - 0.9) / 8
        j = M.plank(2.30, 0.16, 0.10, 0.006, "oak_dark", grain_axis=1)
        j.rotate_y(np.pi * 0.5)
        j.translate(jx, 2.83, p.back - 1.35)
        loft.add(j)
    # Dry staves stacked flat on it — stock, and it breaks the deck's edge.
    for i in range(4):
        bundle = M.box(1.90, 0.13, 0.44, 0.008, "oak")
        bundle.rotate_y(rng.uniform(-0.05, 0.05))
        bundle.translate(-3.2 + i * 1.05, 3.03 + (i % 2) * 0.14,
                         p.back - 1.35 + rng.uniform(-0.25, 0.25))
        loft.add(bundle)
    loft.translate(0, 0.09, 0)
    p.emit(loft)

    # ------------------------------------------------------- 1. RAW MATERIAL
    # Seasoning cones in the open, west end. They stand OUTSIDE the roof: green
    # oak wants weather, and they give the venue a silhouette on the street
    # frontage that is not a building.
    for i, (cx, cz, n, h) in enumerate([(-4.9, -3.35, 13, 2.15),
                                        (-3.7, -2.15, 11, 1.95),
                                        (-5.0, -0.95, 12, 2.30)]):
        cone = _stave_cone(f"{asset_id}.cone.{i:02d}", count=n, height=h,
                           radius=0.32 + i * 0.03)
        cone.translate(cx, 0.09, cz)
        p.emit(cone)
        p.collider("cylinder", center=(cx, 0.09 + h * 0.45, cz), radius=0.40,
                   height=h * 0.9, tag="stave_cone")

    # The cleft billets they came off: cross-stacked in courses, ends out, the
    # way any sawn or riven stock is piled so it dries. A heap would be wrong —
    # a cooper who heaps his clefts has a yard full of warped staves.
    billets = M.Group()
    for course in range(5):
        n = 5 - (course // 2)
        across = course % 2 == 1
        for i in range(n):
            t = -(n - 1) * 0.5 * 0.24 + i * 0.24
            b = M.chamfered_prism([(-0.105, 0), (0.105, 0), (0.062, 0.215),
                                   (-0.088, 0.205)], 0.90, "endgrain", 0.006)
            b.rotate_z(np.pi * 0.5)
            if across:
                b.rotate_y(np.pi * 0.5)
                b.translate(rng.uniform(-0.04, 0.04), course * 0.225, t)
            else:
                b.translate(t, course * 0.225, rng.uniform(-0.04, 0.04))
            b.rotate_y(rng.uniform(-0.03, 0.03))
            billets.add(b)
    billets.translate(-2.35, 0.11, -4.05)
    p.emit(billets)
    p.collider("box", center=(-2.35, 0.11 + 0.56, -4.05), half=(0.62, 0.56, 0.62),
               tag="billets")

    blk = P.chopping_block(f"{asset_id}.cleaving_block", height=0.52, radius=0.34,
                           axe=False)
    blk.translate(-1.25, 0.09, -3.55)
    p.emit(blk)
    froe = M.Group()                          # froe: the L of a stave-river
    froe.add(M.box(0.055, 0.026, 0.40, 0.002, "steel_blued"))
    froe.add(M.tube((0.0, 0.0, -0.20), (0.0, 0.34, -0.24), 0.020, "oak", 5, 0.002))
    froe.rotate_y(0.7)
    froe.translate(-1.25, 0.09 + 0.52, -3.55)
    p.emit(froe)
    p.collider("cylinder", center=(-1.25, 0.09 + 0.26, -3.55), radius=0.36,
               height=0.52, tag="cleaving_block")

    # ------------------------------------------------------------ 2. HOLLOW
    # Everything a cooper does with a knife he does in the LIGHT, so the horse
    # and the jointer stand at the open edge of the covered floor and not back
    # against the wall. The first pass put them deep under the roof and the
    # whole trade disappeared into shadow in the gameplay frame.
    horse = _shaving_horse(f"{asset_id}.horse")
    horse.rotate_y(-0.42)
    horse.translate(-3.75, 0.25, rz - RANGE_D * 0.5 + 1.05)
    p.emit(horse)
    p.collider("box", center=(-3.75, 0.25 + 0.35, rz - RANGE_D * 0.5 + 1.05),
               half=(0.95, 0.35, 0.42), rot_y=-0.42, tag="shaving_horse")

    joint = _jointer(f"{asset_id}.jointer")
    joint.rotate_y(0.20)
    joint.translate(-4.35, 0.25, rz + 0.85)
    p.emit(joint)
    p.collider("box", center=(-4.35, 0.25 + 0.40, rz + 0.85), half=(1.05, 0.40, 0.28),
               rot_y=0.20, tag="jointer")

    # -------------------------------------------------- 3. THE RAISING-UP
    # `props.cooper_setup` is the shared library's answer to this trade and it
    # already carries the raising-up, the croze and adze on the block, the
    # graded hoops and the shavings. It is authored against a wall at
    # `wall_z = 0` — here that plane is the covered floor's own back line, not
    # the shed's rear wall, so the whole set stands one pace inside the drip
    # line where the morning sun reaches it and it is the first thing the eye
    # finds from the street.
    setup = P.cooper_setup(f"{asset_id}.setup", wall_z=1.55)
    setup.rotate_y(0.14)
    setup.translate(-0.35, 0.25, rz - RANGE_D * 0.5 + 1.20)
    p.emit(setup)
    p.collider("cylinder", center=(-0.35, 0.25 + 0.45, rz - RANGE_D * 0.5 + 1.20),
               radius=0.42, height=0.90, tag="raising_up")

    p.entity(f"{asset_id}.station.01", "crafting_station.cooper",
             (-0.35, 0.25, rz - RANGE_D * 0.5 + 1.20), verbs=["use"],
             crafting_station={"profession": "cooper", "tier": 1})

    # A lantern hung off the tie beam over the setting floor. It is not
    # decoration: a shed roofed on 12 m of frontage is dark at 09:30 whatever
    # the sun does, and one warm point under a deep eave is what tells the eye
    # there is a room in there rather than a hole.
    lamp = K.lantern(f"{asset_id}.lamp", glass_mat="glass_lit", scale=1.15)
    lamp.translate(-0.35, 0.09 + 2.62, rz - RANGE_D * 0.5 + 1.35)
    p.emit(lamp)
    hook = M.tube((-0.35, 0.09 + 3.10, rz - RANGE_D * 0.5 + 1.35),
                  (-0.35, 0.09 + 2.78, rz - RANGE_D * 0.5 + 1.35), 0.010,
                  "iron", 5, 0.002)
    p.emit(hook)
    p.entity(f"{asset_id}.lamp.01", "prop.lantern",
             (-0.35, 0.09 + 2.62, rz - RANGE_D * 0.5 + 1.35),
             light={"color": "#FFB566", "intensity": 1.4, "range": 5.5})

    # ------------------------------------------------------------- 4. FIRE
    fire = _setting_fire(p, f"{asset_id}.fire")
    fire.rotate_y(0.22)
    fire.translate(1.55, 0.09, rz - RANGE_D * 0.5 - 0.85)
    p.emit(fire)
    p.collider("cylinder", center=(1.55, 0.09 + 0.55, rz - RANGE_D * 0.5 - 0.85),
               radius=0.78, height=1.10, tag="setting_fire")
    p.entity(f"{asset_id}.fire.01", "prop.hearth",
             (1.55, 0.09, rz - RANGE_D * 0.5 - 0.85), verbs=[],
             light={"color": "#FF7A2E", "intensity": 2.6, "range": 6.5,
                    "flickerHz": [6, 11]},
             smoke={"rate": 0.35, "drift": [0.7, 0, 0.4]})

    wind = _windlass(f"{asset_id}.windlass")
    wind.rotate_y(0.9)
    wind.translate(2.95, 0.09, rz - RANGE_D * 0.5 - 1.35)
    p.emit(wind)
    p.collider("box", center=(2.95, 0.09 + 0.52, rz - RANGE_D * 0.5 - 1.35),
               half=(0.55, 0.52, 0.22), rot_y=0.9, tag="windlass")

    # Its fuel: the shop's own shavings, heaped where they were swept to. This
    # is the join between two stations and it is why the heap is here and not
    # tidied — Art Bible §7, residue that explains something.
    heap = P.kindling(f"{asset_id}.shaveheap", radius=0.52)
    heap.translate(0.55, 0.09, rz - RANGE_D * 0.5 - 1.55)
    p.emit(heap)

    # ---------------------------------------------------------- 5. THE HOOPS
    # Graded on the back wall by size, which is how a cooper finds the one he
    # wants without measuring. Hung, not stacked: an iron hoop on a floor rusts.
    hoops = M.Group()
    for i in range(9):
        r = 0.20 + i * 0.048
        h = M.ring(r, 0.042, "iron" if i % 3 else "iron_pitted", 18)
        h.rotate_x(np.pi * 0.5)
        h.rotate_y(rng.uniform(-0.05, 0.05))
        h.translate(2.05 + i * 0.30, 1.55 + r * 0.6, p.back - 0.30)
        hoops.add(h)
        pg = M.tube((2.05 + i * 0.30, 1.58 + r * 1.2, p.back - 0.16),
                    (2.05 + i * 0.30, 1.58 + r * 1.2, p.back - 0.42),
                    0.016, "iron", 5, 0.002)
        hoops.add(pg)
    hoops.translate(0, 0.09, 0)
    p.emit(hoops)

    # A hoop that sprung on the anvil and was thrown down, still oval. The one
    # object here that records a FAILURE, which is worth more than four that
    # record success.
    bad = M.ring(0.40, 0.042, "iron_pitted", 18)
    bad.scale(1.0, 1.0, 0.72)
    bad.rotate_x(0.16)
    bad.rotate_y(0.8)
    bad.translate(4.35, 0.13, rz + 1.25)
    p.emit(bad)

    # --------------------------------------------------------- 6. FINISHED
    # By the kerb, where the carrier picks up. Casks leave this yard; the
    # composition should say which way.
    pyr = _cask_pyramid(f"{asset_id}.stack", rows=3)
    pyr.rotate_y(-0.08)
    pyr.translate(3.95, 0.09, -3.15)
    p.emit(pyr)
    p.collider("box", center=(3.95, 0.09 + 0.80, -3.15), half=(1.05, 0.80, 0.42),
               rot_y=-0.08, tag="cask_stack")

    for i, (bx, bz, ry) in enumerate([(2.15, -4.10, 0.4), (1.35, -3.55, -1.1)]):
        b = K.barrel(f"{asset_id}.out.{i}", height=0.88, belly=0.62)
        b.rotate_y(ry)
        b.translate(bx, 0.09, bz)
        p.emit(b)
        p.collider("cylinder", center=(bx, 0.09 + 0.44, bz), radius=0.33,
                   height=0.88, tag="cask")
    roll = P.barrel_lying(f"{asset_id}.rolling", height=0.88, belly=0.62)
    roll.rotate_y(1.35)
    roll.translate(0.35, 0.09, -4.30)
    p.emit(roll)

    # ---------------------------------------------------------- the sign
    # Pictorial only, Art Bible §2: a cask on a bracket, hung off the range's
    # street-side corner post where it reads down Bakers' Row.
    sign = K.hanging_sign(f"{asset_id}.sign", width=0.62, height=0.48,
                          board_mat="painted", reach=0.86,
                          sway=rng.uniform(-0.06, 0.06))
    sign.translate(-(p.w - 0.6) * 0.5 + 0.20, 0.09 + 3.35,
                   rz - RANGE_D * 0.5 - 0.14)
    p.emit(sign)
    icon = K.barrel(f"{asset_id}.icon", height=0.26, belly=0.20)
    icon.translate(-(p.w - 0.6) * 0.5 + 0.20 + 0.58, 0.09 + 3.35 - 0.52,
                   rz - RANGE_D * 0.5 - 0.20)
    p.emit(icon)

    # ------------------------------------------------------------- residue
    # Shavings underfoot — the brief's word, and the truest thing about a
    # cooper's floor. Two spreads: dense under the horse and the jointer,
    # scattered where they blew across the yard.
    # `props.shavings`, never `spill`: a spill builds a conical heap, which is
    # right for grain and wrong for shavings. Shavings lie FLAT and scattered,
    # and a heap of them at eye height under this roof read as a sand dune.
    for i, (sx, sz, n, rx, rz2) in enumerate([(-3.9, rz - 0.2, 46, 1.5, 1.0),
                                              (-0.2, rz + 0.9, 34, 1.2, 0.9),
                                              (1.1, -2.4, 22, 1.6, 1.1)]):
        sh = P.shavings(f"{asset_id}.shav.{i}", n, rx, rz2, "oak")
        sh.translate(sx, 0.09 if i == 2 else 0.25, sz)
        p.emit(sh)

    bench = P.dress_workbench(f"{asset_id}.bench", trade="cooper", length=2.0,
                              wall_z=0.0, ctx=None)
    bench.rotate_y(np.pi)
    bench.translate(3.85, 0.25, p.back - 0.45)
    p.emit(bench)
    p.collider("box", center=(3.85, 0.25 + 0.43, p.back - 0.85), half=(1.0, 0.43, 0.32),
               tag="bench")

    # The apron on its peg and the mug on the cask — the two objects that say
    # somebody stood up ten minutes ago.
    apron = M.sheet(0.54, 0.80, lambda u, v: -0.03 * np.sin(u * 3.1) * (1 - v),
                    nx=6, nz=6, mat="leather", plane="xy")
    apron.rotate_y(np.pi)
    apron.translate(5.15, 0.09 + 1.62, p.back - 0.22)
    p.emit(apron)
    peg = M.tube((5.15, 0.09 + 1.68, p.back - 0.14),
                 (5.15, 0.09 + 1.70, p.back - 0.34), 0.014, "oak_dark", 5, 0.002)
    p.emit(peg)

    mug = P.mug(f"{asset_id}.mug", full=True)
    mug.translate(2.15 + 0.10, 0.09 + 0.88, -4.10)
    p.emit(mug)

    # Boot scuffs at the threshold and a worn track from the fire to the kerb —
    # the ground evidence that anyone actually crosses this yard.
    for i, (wx, wz, sz2, shape) in enumerate([(2.0, -1.5, 1.6, "path"),
                                              (-2.4, -1.9, 1.2, "path"),
                                              (4.4, 0.6, 0.7, "cat")]):
        wp = P.worn_patch(f"{asset_id}.worn.{i}", shape=shape, size=sz2,
                          mat="grass_worn")
        wp.rotate_y(rng.uniform(0, 3.14))
        wp.translate(wx, 0.095, wz)
        p.emit(wp)

    # A bucket of water by the fire, because a timber yard with a fire in it
    # and no water reads as a yard that has not thought about fire.
    bkt = P.bucket(f"{asset_id}.firebucket", full=True)
    bkt.translate(2.55, 0.09, rz - RANGE_D * 0.5 - 0.35)
    p.emit(bkt)

    # Street furniture: a spur stone on the corner the carts clip. Cheap, and
    # it is the detail that makes a frontage read as a frontage.
    sp = S.spur_stone(f"{asset_id}.spur", height=0.60)
    sp.translate(p.w * 0.5 - 0.55, 0.09, p.front + 0.25)
    p.emit(sp)
    p.collider("cylinder", center=(p.w * 0.5 - 0.55, 0.09 + 0.30, p.front + 0.25),
               radius=0.22, height=0.60, tag="spur_stone")
