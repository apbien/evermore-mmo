"""The chandler — slot 35, Bakers' Row.

The schedule's own note is the design: *"sited at the far end of the fire lane
with the prevailing wind carrying everything it renders away over the orchard
and out of town."* Rendering tallow is boiling animal fat in an open vat, all
day, and a town puts that building downwind on purpose. The venue's job is to
make that decision legible from the street without a word of text.

## How the smell is made visible

You cannot render a smell, so it is built four ways and they compound:

  1. **A flue that never stops.** The rendering-house stack is the tallest
     thing on the plot at 8.4 m and it carries a permanent smoke emitter. It
     is the venue's anchor silhouette and it is the only part visible from the
     far end of Bakers' Row.
  2. **The wall behind the vats is stained.** `stained_dark` boarding for the
     two bays the steam actually reaches, `stained` for the fall-off, plain
     weathered oak beyond. The gradient is the point: a uniformly dirty wall
     reads as a texture choice, a wall dirty in the shape of what stands in
     front of it reads as a consequence.
  3. **The ground is greasy** where the vats are skimmed out, and nothing
     grows within two metres of the settling tub.
  4. **Nothing else is near it.** The rendering house is at the back of the
     plot with its own open sides; the shop is a clean, plastered, ordinary
     little building at the street, and the contrast between the two halves is
     the whole composition.

## Open where the trade allows

Dipping is not: a draught across a dipping frame gives you crooked candles, so
the frames stand inside. What the street gets instead is a fold-down counter
with the frames right behind it, and one rack of finished candles hung out
under the eaves to harden — which is period practice and puts the venue's most
recognisable object at eye height on the footway.
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

NAME = "chandler"
SLOT = 35
CELLS = ["I7", "I8"]

ASSET = "hm.chandler"

SHOP_D = 4.0
SHED_D = 4.2
EAVES = 5.0
PLINTH = 0.38


def _dipping_frame(asset_id, width=1.55, rails=4, y=1.95, graded=True,
                   mat="tallow"):
    """A dipping frame: rows of candles hung by their wicks, graded by dip.

    A chandler dips a whole frame at once and hangs it to set, then dips it
    again — so a shop always has three or four frames going at different
    thicknesses and lengths, and that GRADIENT is what identifies the trade.
    One frame of identical candles is a shelf of dowels.

    Ground origin, the frame's rails running along +X.
    """
    rng = rng_for(asset_id, "dip")
    out = M.Group()
    for sx in (-1, 1):
        po = M.box(0.085, y + 0.16, 0.085, 0.006, "oak_weathered")
        po.translate(sx * width * 0.5, (y + 0.16) * 0.5, 0)
        out.add(po)
        ft = M.box(0.20, 0.07, 0.52, 0.006, "oak_weathered")
        ft.translate(sx * width * 0.5, 0.035, 0)
        out.add(ft)
    for r in range(rails):
        rz = -0.20 + r * 0.135
        rail = M.plank(width + 0.10, 0.045, 0.040, 0.003, "oak_weathered")
        rail.translate(0, y - r * 0.055, rz)
        out.add(rail)
        # Candles: the older the row, the fatter and the longer.
        t = (r + 1) / rails if graded else 0.7
        n = int(width / 0.115)
        for i in range(n):
            cx = -width * 0.5 + (i + 0.5) * width / n
            ln = 0.16 + t * 0.20 + rng.uniform(-0.012, 0.012)
            rad = 0.011 + t * 0.011
            for s in (-1, 1):          # a dipped pair, one wick over the rail
                c = M.lathe([(rad * 0.55, 0), (rad, 0.035), (rad, ln * 0.94),
                             (rad * 0.75, ln)], 7, mat)
                c.rotate_x(np.pi)      # hanging point up
                c.translate(cx, y - r * 0.055 - 0.02, rz + s * 0.030)
                c.translate(0, 0, 0)
                out.add(c)
            wick = M.tube((cx, y - r * 0.055 - 0.02, rz - 0.030),
                          (cx, y - r * 0.055 + 0.022, rz),
                          0.0022, "canvas", 4, 0.0)
            out.add(wick)
            wick2 = M.tube((cx, y - r * 0.055 - 0.02, rz + 0.030),
                           (cx, y - r * 0.055 + 0.022, rz),
                           0.0022, "canvas", 4, 0.0)
            out.add(wick2)
    return out


def _tallow_vat(asset_id, radius=0.62, lit=True):
    """A rendering vat on a stone firebox. Ground origin.

    An iron cauldron bedded into a stone box with the fire under it and a lip
    of set tallow round the rim. The lip is the detail that makes it read as
    used: a clean cauldron is a prop, a cauldron with a week of spill down one
    side is a place of work.
    """
    rng = rng_for(asset_id, "vat")
    out = M.Group()
    box = M.lathe([(radius + 0.34, 0), (radius + 0.32, 0.62), (radius + 0.08, 0.70)],
                  12, "stone")
    out.add(box)
    # The stoke hole, and the fire in it.
    mouth = M.box(0.52, 0.34, 0.30, 0.02, "timber_charred")
    mouth.translate(0, 0.24, -(radius + 0.20))
    out.add(mouth)
    if lit:
        for i in range(14):
            c = M.box(rng.uniform(0.05, 0.10), 0.035, rng.uniform(0.04, 0.08),
                      0.008, "coal")
            c.translate(rng.uniform(-0.18, 0.18), 0.13,
                        -(radius + 0.16) + rng.uniform(-0.06, 0.06))
            out.add(c)
    pot = M.lathe([(0.0, 0.70), (radius * 0.55, 0.70), (radius, 0.90),
                   (radius * 1.02, 1.16), (radius * 0.94, 1.20)], 16, "iron_pitted")
    out.add(pot)
    # The set tallow: a run down the outside and a skin on the top.
    skin = M.lathe([(0.0, 1.08), (radius * 0.93, 1.09)], 14, "tallow",
                   close_bottom=False, close_top=False)
    out.add(skin)
    for i in range(3):
        a = rng.uniform(0, 6.283)
        run = M.chamfered_prism([(-0.055, 0), (0.055, 0), (0.030, 0.34),
                                 (-0.040, 0.30)], 0.022, "tallow", 0.003)
        run.rotate_y(a)
        run.translate(np.cos(a) * radius * 1.02, 0.82, np.sin(a) * radius * 1.02)
        out.add(run)
    return out


def build(ctx: VenueContext, asset_id=ASSET):
    p = Site(slot=SLOT, ctx=ctx, asset_id=asset_id)
    rng = rng_for(asset_id, "chandler")

    # ------------------------------------------------------------------ yard
    yard = M.box(p.w + 0.6, 0.10, p.d + 0.6, 0.035, "earth",
                 uv_scale=ctx.uv_scale("earth"))
    yard.translate(0, 0.05, 0)
    p.emit(yard)
    p.collider("box", center=(0, 0.05, 0),
               half=((p.w + 0.6) * 0.5, 0.05, (p.d + 0.6) * 0.5),
               kind="surface", tag="yard")
    kerb = M.box(p.w + 0.6, 0.13, 0.26, 0.02, "cobble",
                 uv_scale=ctx.uv_scale("cobble"))
    kerb.translate(0, 0.065, p.front - 0.16)
    p.emit(kerb)

    # =================================================== THE SHOP (street end)
    # The shop takes only the WEST 6.2 m of the 10 m frontage. The other 3.8 m
    # is the cart entry into the rendering yard, and that gap is the single most
    # important decision in the venue: the first pass filled the whole frontage
    # with the shop, and the vats, the stain and the 8.4 m flue — everything the
    # venue is actually about — were completely invisible from Bakers' Row.
    # A town workshop plot IS a shop plus a gateway; build it that way and the
    # street gets a view straight through into the work.
    SHOP_W = 6.2
    SHOP_X = -(p.w * 0.5) + SHOP_W * 0.5 + 0.30
    sz = p.front + SHOP_D * 0.5
    ph = K.stone_plinth(SHOP_W + 0.2, SHOP_D + 0.2, PLINTH, mat="rubble")
    ph.translate(SHOP_X, 0.10, sz)
    p.emit(ph)
    y0 = 0.10 + PLINTH
    wall_h = EAVES - PLINTH - 1.05        # eaves 5.0 belongs to the RIDGE of a
    # one-storey shop, not to 4.5 m of blank plaster over a door. 3.57 m of wall
    # under a 0.92 pitch puts the ridge at 5.0 exactly.
    sw = SHOP_W
    FZ = p.front                          # centre-line of the front wall
    OUT = FZ - 0.13                       # its outer face, plus a hair

    door_x = SHOP_X + sw * 0.30
    win_x = SHOP_X - sw * 0.18
    WIN_W, WIN_H = 2.05, 1.20
    front = K.timber_frame_wall(
        sw, wall_h, f"{asset_id}.front", style="square", sill_y=0.0,
        openings=[(door_x - SHOP_X, K.DOOR_H * 0.5, K.DOOR_W + 0.35, K.DOOR_H + 0.25),
                  (win_x - SHOP_X, 1.38, WIN_W + 0.28, WIN_H + 0.28)])
    front.translate(SHOP_X, y0, FZ)
    p.emit(front)
    for s in (-1, 1):
        side = K.timber_frame_wall(SHOP_D, wall_h, f"{asset_id}.side{s}",
                                   style="cross", sill_y=0.0)
        side.rotate_y(s * np.pi * 0.5)
        side.translate(SHOP_X + s * sw * 0.5, y0, sz)
        p.emit(side)
    back = K.timber_frame_wall(sw, wall_h, f"{asset_id}.back", style="square",
                               sill_y=0.0)
    back.rotate_y(np.pi)
    back.translate(SHOP_X, y0, sz + SHOP_D * 0.5)
    p.emit(back)

    roof = K.gable_roof(SHOP_D, sw, f"{asset_id}.shoproof", pitch=0.92,
                        overhang=0.52, tile_mat="slate")
    roof.rotate_y(np.pi * 0.5)
    roof.translate(SHOP_X, y0 + wall_h, sz)
    p.emit(roof, container="shoproof", shell=True)
    for s in (-1, 1):
        g = K.gable_end(SHOP_D + 1.04, 0.0, 0.92, mat="plaster", depth=0.20)
        g.rotate_y(np.pi * 0.5)
        g.translate(SHOP_X + s * (sw * 0.5 + 0.52), y0 + wall_h, sz)
        p.emit(g)

    p.collider_walls(sw, SHOP_D, wall_h, y=y0, thickness=0.30,
                     center=(SHOP_X, sz),
                     doors=[("-z", door_x - SHOP_X, K.DOOR_W + 0.5)])
    p.collider("box", center=(SHOP_X, 0.10 + PLINTH * 0.5, sz),
               half=((sw + 0.2) * 0.5, PLINTH * 0.5, (SHOP_D + 0.2) * 0.5),
               kind="surface", tag="plinth")
    p.collider_steps(front=(door_x, 0.10, FZ - 0.11), height=PLINTH,
                     tread=0.42, width=1.5)

    fr = K.door_frame(mat="oak_dark")
    fr.translate(door_x, y0, FZ - 0.11 - 0.14)
    p.emit(fr)
    door = K.plank_door(f"{asset_id}.door", mat="oak_weathered", open_angle=0.62)
    door.translate(door_x, y0, FZ - 0.11 - 0.22)
    p.emit(door)
    p.entity(f"{asset_id}.door.01", "door.chandler",
             (door_x, y0, p.front + 0.05), verbs=["enter"])

    # --- the fold-down counter, and what is on it -------------------------
    ozy = y0 + 1.42
    for s in (-1, 1):
        r = M.plank(WIN_W + 0.26, 0.12, 0.22, 0.008, "oak_dark")
        r.translate(win_x, ozy + s * (WIN_H * 0.5 + 0.06), FZ - 0.11 - 0.13)
        p.emit(r)
    for s in (-1, 1):
        j = M.box(0.12, WIN_H + 0.24, 0.22, 0.008, "oak_dark")
        j.translate(win_x + s * (WIN_W * 0.5 + 0.06), ozy, FZ - 0.11 - 0.13)
        p.emit(j)
    dark = M.box(WIN_W, WIN_H, 0.05, 0.004, "oak_dark")
    dark.translate(win_x, ozy, FZ - 0.11 + 0.10)
    p.emit(dark)
    # Awning shutter propped out, counter shutter dropped flat.
    up = M.Group()
    for i in range(5):
        b = M.box(WIN_W / 5 * 0.96, 0.66, 0.030, 0.004, "oak_weathered")
        b.translate(-WIN_W * 0.5 + (i + 0.5) * WIN_W / 5, 0, 0)
        up.add(b)
    up.rotate_x(-1.20)
    up.translate(win_x, ozy + WIN_H * 0.5 + 0.22, FZ - 0.11 - 0.44)
    p.emit(up)
    for s in (-1, 1):
        st = M.cylinder(0.018, 0.82, 6, 0.003, "oak_weathered")
        st.rotate_x(0.55)
        st.translate(win_x + s * WIN_W * 0.4, ozy + WIN_H * 0.5 - 0.06,
                     FZ - 0.11 - 0.32)
        p.emit(st)
    low = M.Group()
    for i in range(5):
        b = M.box(WIN_W / 5 * 0.96, 0.76, 0.032, 0.004, "oak_weathered")
        b.translate(-WIN_W * 0.5 + (i + 0.5) * WIN_W / 5, 0, 0)
        low.add(b)
    low.rotate_x(np.pi * 0.5)
    low.translate(win_x, ozy - WIN_H * 0.5 - 0.02, FZ - 0.11 - 0.50)
    p.emit(low)
    cy = ozy - WIN_H * 0.5 - 0.02
    for s in (-1, 1):
        lg = M.box(0.07, cy - 0.10, 0.07, 0.005, "oak_weathered")
        lg.translate(win_x + s * WIN_W * 0.42, 0.10 + (cy - 0.10) * 0.5,
                     FZ - 0.11 - 0.84)
        p.emit(lg)
    p.collider("box", center=(win_x, cy - 0.42, FZ - 0.11 - 0.50),
               half=(WIN_W * 0.5 + 0.1, 0.42, 0.40), tag="counter")

    # Stock on the counter, in the order a chandler sells it: the cheap
    # rushlights loose, the tallow candles bundled, the two beeswax tapers
    # standing apart because they cost a week's wages.
    for i in range(5):
        b = M.Group()
        for j in range(7):
            a = 2 * np.pi * j / 7
            c = M.lathe([(0.014, 0), (0.016, 0.30), (0.011, 0.32)], 6, "tallow")
            c.translate(np.cos(a) * 0.026, 0, np.sin(a) * 0.026)
            b.add(c)
        b.add(M.ring(0.035, 0.008, "canvas", 8).translate(0, 0.17, 0))
        b.rotate_y(rng.uniform(0, 3.0))
        b.rotate_z(rng.uniform(-0.06, 0.06))
        b.translate(win_x - 0.72 + i * 0.24, cy + 0.02,
                    FZ - 0.11 - 0.50 + rng.uniform(-0.06, 0.06))
        p.emit(b)
    for i in range(2):
        t = M.lathe([(0.016, 0), (0.019, 0.44), (0.012, 0.47)], 7, "beeswax")
        t.translate(win_x + 0.78 + i * 0.09, cy + 0.02, FZ - 0.11 - 0.44)
        p.emit(t)
    rushtub = P.basket(f"{asset_id}.rushtub", radius=0.20, height=0.30,
                       weave="stake")
    rushtub.translate(win_x + 0.42, cy + 0.02, FZ - 0.11 - 0.52)
    p.emit(rushtub)
    for i in range(15):                       # peeled rushes, standing loose
        r = M.tube((0, 0, 0), (rng.uniform(-0.05, 0.05), rng.uniform(0.30, 0.42),
                               rng.uniform(-0.05, 0.05)), 0.0035, "straw", 4, 0.0)
        r.translate(win_x + 0.42 + rng.uniform(-0.10, 0.10), cy + 0.20,
                    FZ - 0.11 - 0.52 + rng.uniform(-0.10, 0.10))
        p.emit(r)

    p.entity(f"{asset_id}.counter.01", "vendor.chandler",
             (win_x, cy, FZ - 0.11 - 0.50), verbs=["buy"],
             vendor={"currency": "copper",
                     "stock": [{"item": "tallow_candle", "price": 3, "qty": -1},
                               {"item": "rushlight_bundle", "price": 1, "qty": -1},
                               {"item": "beeswax_taper", "price": 34, "qty": 6},
                               {"item": "lamp_oil", "price": 12, "qty": 14}]})

    # A rack of finished candles hung out under the eave to harden. This is the
    # object that identifies the venue at eye height on the footway.
    dip = _dipping_frame(f"{asset_id}.dip.out", width=1.45, rails=3, y=1.75)
    dip.rotate_y(0.08)
    dip.translate(SHOP_X - sw * 0.5 + 1.15, y0, FZ - 0.11 - 0.62)
    p.emit(dip)
    p.collider("box", center=(SHOP_X - sw * 0.5 + 1.15, y0 + 0.95, FZ - 0.73),
               half=(0.85, 0.95, 0.34), tag="dipping_frame")

    win = K.leaded_window(f"{asset_id}.upper", width=0.72, height=0.86,
                          mat="glass_lit", shutters=True, shutter_mat="painted")
    win.translate(door_x + 1.05, y0 + wall_h - 1.15, FZ - 0.17)
    p.emit(win)

    sign = K.hanging_sign(f"{asset_id}.sign", width=0.60, height=0.46,
                          board_mat="painted", reach=0.84,
                          sway=rng.uniform(-0.06, 0.06))
    sign.translate(SHOP_X + sw * 0.5 - 0.45, y0 + 2.70, FZ - 0.27)
    p.emit(sign)
    ic = M.lathe([(0.030, 0), (0.034, 0.30), (0.020, 0.33)], 8, "tallow")
    ic.translate(SHOP_X + sw * 0.5 - 0.45 + 0.56, y0 + 2.70 - 0.62, FZ - 0.33)
    p.emit(ic)
    fl = M.lathe([(0.0, 0), (0.022, 0.035), (0.0, 0.10)], 6, "glass_lit")
    fl.translate(SHOP_X + sw * 0.5 - 0.45 + 0.56, y0 + 2.70 - 0.29, FZ - 0.33)
    p.emit(fl)

    # ================================================= THE RENDERING HOUSE
    hz = p.back - SHED_D * 0.5
    shed = K.open_range(
        f"{asset_id}.shed", p.w - 1.4, SHED_D, 3.55,
        pitch=0.70, overhang=0.55, roof_mat="terracotta",
        walls=("back",), half_boarded=("left", "right"),
        plinth=0.0, board_gap=0.06, tag="render")
    shed.translate(0, 0.10, hz)
    p.emit(shed, container="shed", shell=True)

    sh_h = 3.55
    p.collider("box", center=(0, 0.10 + sh_h * 0.5, p.back - 0.10),
               half=((p.w - 1.4) * 0.5, sh_h * 0.5, 0.11), tag="shed_wall")
    for i in range(4):
        px = -(p.w - 1.4) * 0.5 + i * (p.w - 1.4) / 3
        for pz in (hz - SHED_D * 0.5, hz + SHED_D * 0.5):
            p.collider("box", center=(px, 0.10 + sh_h * 0.5, pz),
                       half=(0.16, sh_h * 0.5, 0.16), tag="post")

    # --- the stain, laid in bands over the boarding ----------------------
    # Two bays of `stained_dark` directly over the vats, one of `stained`
    # falling off to each side. The gradient is what makes it read as a
    # consequence rather than as a dirty texture.
    for i, (bx, bw, mat) in enumerate([(3.05, 3.20, "stained_dark"),
                                       (0.60, 1.70, "stained"),
                                       (-1.60, 2.60, "stained")]):
        n = max(2, int(bw / 0.29))
        for j in range(n):
            b = M.box(bw / n * 0.92, 2.55, 0.030, 0.004, mat,
                      uv_scale=ctx.uv_scale(mat))
            b.translate(bx - bw * 0.5 + (j + 0.5) * bw / n, 0.10 + 1.42,
                        p.back - 0.02)
            p.emit(b)

    # --- two vats, a settling tub and the skimming station ---------------
    for i, (vx, vz, r) in enumerate([(3.55, hz + 0.35, 0.62),
                                     (1.85, hz + 0.60, 0.52)]):
        vat = _tallow_vat(f"{asset_id}.vat.{i}", radius=r, lit=True)
        vat.rotate_y(rng.uniform(-0.2, 0.2))
        vat.translate(vx, 0.10, vz)
        p.emit(vat)
        p.collider("cylinder", center=(vx, 0.10 + 0.60, vz), radius=r + 0.32,
                   height=1.20, tag="tallow_vat")
        p.entity(f"{asset_id}.vat.{i:02d}", "prop.hearth", (vx, 0.10, vz),
                 light={"color": "#FF8A3C", "intensity": 1.8, "range": 5.0,
                        "flickerHz": [5, 9]},
                 smoke={"rate": 0.6, "drift": [0.9, 0, 0.6]})

    p.entity(f"{asset_id}.station.01", "crafting_station.chandler",
             (2.70, 0.10, hz - 0.55), verbs=["use"],
             crafting_station={"profession": "chandler", "tier": 1})

    # The stirring paddle left standing in the near vat, and the skimmer
    # hooked over its rim with the day's scum still on it.
    pad = M.Group()
    pad.add(M.tube((0, 0, 0), (0.30, 1.55, 0.14), 0.026, "oak_weathered", 6, 0.002))
    pad.add(M.plank(0.16, 0.34, 0.026, 0.004, "oak_weathered").translate(0, 0.10, 0))
    pad.translate(3.55, 0.10 + 0.85, hz + 0.35)
    p.emit(pad)
    sk = M.Group()
    sk.add(M.lathe([(0.0, 0), (0.16, 0.02), (0.15, 0.055)], 10, "iron_pitted"))
    sk.add(M.tube((0.14, 0.04, 0), (0.74, 0.20, 0.04), 0.014, "iron", 5, 0.002))
    sk.rotate_y(1.1)
    sk.translate(1.85, 0.10 + 1.20, hz + 0.55)
    p.emit(sk)

    tub = K.barrel(f"{asset_id}.settling", height=1.05, belly=0.86)
    tub.translate(0.10, 0.10, hz + 0.75)
    p.emit(tub)
    fat = M.lathe([(0.0, 0.88), (0.40, 0.88)], 14, "tallow",
                  close_bottom=False, close_top=False)
    fat.translate(0.10, 0.10, hz + 0.75)
    p.emit(fat)
    p.collider("cylinder", center=(0.10, 0.10 + 0.52, hz + 0.75), radius=0.44,
               height=1.05, tag="settling_tub")

    # `props.chandler_kit` — the shared library's dipping station. It goes in
    # the covered bay at the shed's east end where the draught is least.
    kit = P.chandler_kit(f"{asset_id}.kit", wall_z=1.35)
    kit.rotate_y(-0.18)
    kit.translate(-2.15, 0.10, hz - 0.30)
    p.emit(kit)

    # --- the flue: 8.4 m, and it never stops ------------------------------
    # Sited over the vats at the plot's EAST end, which is what puts it in
    # the gap beside the shop and makes it the thing you see first from Bakers'
    # Row. Rising to 8.9 m it stands 3.9 m clear of the shop ridge.
    SX = 2.85
    stack = K.chimney(f"{asset_id}.stack", height=5.4, section=1.10, mat="stone")
    stack.translate(SX, 0.10 + 3.40, p.back - 0.95)
    p.emit(stack, label="render stack")
    hood = M.prism([(-1.95, 0), (1.95, 0), (0.68, 1.45), (-0.68, 1.45)], 2.1,
                   chamfer=0.025)
    hood.translate(SX, 0.10 + 2.05, hz + 0.45)
    p.emit(hood.with_material("plaster"))
    for hx in (-1.85, 1.85):                  # the posts the hood is carried on
        po = M.box(0.19, 2.05, 0.19, 0.012, "oak_dark")
        po.translate(SX + hx, 0.10 + 1.02, hz + 0.45)
        p.emit(po)
    p.entity(f"{asset_id}.chimney.01", "prop.chimney",
             (SX, 0.10 + 3.40 + 5.5, p.back - 0.95),
             smoke={"rate": 1.0, "drift": [1.4, 0, 0.9]})

    # --- the cart entry -------------------------------------------------
    # The 3.5 m gap between the shop's east gable and the plot boundary. Two
    # gate posts, a gate hung off one of them and standing open against the
    # wall because it has not been shut in a year, and a rutted way in.
    for gx in (SHOP_X + SHOP_W * 0.5 + 0.35, p.w * 0.5 - 0.35):
        gp = M.box(0.24, 2.35, 0.24, 0.014, "oak_dark")
        gp.translate(gx, 0.10 + 1.18, p.front + 0.55)
        p.emit(gp)
        cap = M.chamfered_prism([(-0.17, 0), (0.17, 0), (0.0, 0.17)], 0.34,
                                "oak_dark", 0.008)
        cap.translate(gx, 0.10 + 2.35, p.front + 0.55)
        p.emit(cap)
        p.collider("box", center=(gx, 0.10 + 1.18, p.front + 0.55),
                   half=(0.16, 1.18, 0.16), tag="gate_post")
    gate = M.Group()
    for i in range(5):
        br = M.plank(2.85, 0.11, 0.045, 0.005, "timber_grey")
        br.translate(0, 0.28 + i * 0.36, 0)
        gate.add(br)
    gate.add(M.plank(2.20, 0.10, 0.042, 0.005, "timber_grey")
             .rotate_z(0.62).translate(0, 1.00, -0.045))
    for hx in (-1.38, 1.38):
        gate.add(M.box(0.10, 1.86, 0.05, 0.005, "timber_grey")
                 .translate(hx, 0.99, 0))
    gate.rotate_y(np.pi * 0.5 - 0.22)
    gate.translate(SHOP_X + SHOP_W * 0.5 + 0.50, 0.10, p.front + 1.90)
    p.emit(gate)

    ruts = P.worn_patch(f"{asset_id}.ruts", shape="path", size=4.2, mat="mud_wet")
    ruts.rotate_y(0.10)
    ruts.translate(3.35, 0.104, p.front + 2.60)
    p.emit(ruts)

    # --- residue: what boiling fat does to a yard ------------------------
    grease = P.worn_patch(f"{asset_id}.grease", shape="path", size=2.6,
                          mat="stained_dark")
    grease.rotate_y(0.2)
    grease.translate(2.60, 0.104, hz - 1.35)
    p.emit(grease)
    for i, (gx, gz, s) in enumerate([(0.6, hz - 1.1, 1.5), (4.0, hz + 0.4, 1.2)]):
        g = P.worn_patch(f"{asset_id}.grease.{i}", shape="cat", size=s,
                         mat="stained")
        g.rotate_y(rng.uniform(0, 3.0))
        g.translate(gx, 0.104, gz)
        p.emit(g)

    # Barrels of rendered tallow waiting to go to the shop, and the fat
    # brought up from the shambles in a covered tub.
    for i, (bx, bz) in enumerate([(-3.55, hz + 1.15), (-4.15, hz + 0.55),
                                  (-3.05, hz + 0.35)]):
        b = K.barrel(f"{asset_id}.stock.{i}", height=0.82, belly=0.58)
        b.rotate_y(rng.uniform(0, 3.0))
        b.translate(bx, 0.10, bz)
        p.emit(b)
        p.collider("cylinder", center=(bx, 0.10 + 0.41, bz), radius=0.31,
                   height=0.82, tag="tallow_cask")

    cart = P.handcart(f"{asset_id}.cart")
    cart.rotate_y(2.2)
    cart.translate(3.20, 0.10, -0.30)
    p.emit(cart)
    p.collider("box", center=(3.20, 0.10 + 0.55, -0.30), half=(0.80, 0.55, 0.80),
               tag="handcart")

    wood = P.firewood_stack(f"{asset_id}.wood", length=2.6, height=1.15,
                            depth=0.46, wall_z=p.back - 0.16)
    wood.translate(0.55, 0.10, 0)
    p.emit(wood)
    p.collider("box", center=(0.55, 0.10 + 0.58, p.back - 0.40),
               half=(1.35, 0.58, 0.26), tag="woodpile")

    # Nothing grows within reach of the vats. Two nettles and a dock at the
    # plot's clean corner, and bare greasy earth everywhere else, is a cheaper
    # and truer statement than any amount of decal.
    for i in range(6):
        sb = M.Group()
        for j in range(5):
            bl = M.chamfered_prism([(0, 0), (0.035, 0.10), (0.0, 0.22)], 0.004,
                                   "foliage", 0.001)
            bl.rotate_y(rng.uniform(0, 6.28))
            bl.rotate_z(rng.uniform(-0.4, 0.4))
            sb.add(bl)
        sb.translate(p.w * 0.5 - rng.uniform(0.3, 1.4), 0.10,
                     p.front + rng.uniform(0.3, 1.6))
        p.emit(sb)

    sp = S.spur_stone(f"{asset_id}.spur", height=0.58)
    sp.translate(-p.w * 0.5 + 0.5, 0.10, p.front + 0.30)
    p.emit(sp)
    p.collider("cylinder", center=(-p.w * 0.5 + 0.5, 0.10 + 0.29, p.front + 0.30),
               radius=0.21, height=0.58, tag="spur_stone")
