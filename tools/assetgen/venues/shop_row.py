"""Shop Row — general store, apothecary and tailor sharing party walls.

Terraces are how towns actually build: one continuous frontage at street level,
three separate businesses above it. The design problem is that a continuous
frontage is also the fastest way to violate Art Bible §7, which forbids more
than 12m of undifferentiated facade.

So the ground floor is continuous and the upper storeys are deliberately NOT:
each shop has a different height, framing style, roof pitch and ridge line.
They were built at different times by different owners, and the roofline should
say so from across the square.

The signature element is the shuttered display window that folds DOWN into a
counter — period-correct, instantly readable as "shop", and it puts goods at
the player's eye level right on the street.
"""

from __future__ import annotations

import numpy as np

from core import mesh as M
from core import kit as K
from core.mathx import rng_for
from core import siting as SI
from core.venue import VenueContext

NAME = "shop_row"
SITE = SI.Site(NAME)
CELLS = ["C5", "D5", "E5"]

DEPTH = 8.0
GROUND_H = 3.0

# (key, width, upper height, framing style, roof pitch, sign colour)
SHOPS = [
    ("general",    7.4, 2.95, "square",  0.86, "painted"),
    ("apothecary", 6.2, 3.30, "herring", 1.02, "painted"),
    ("tailor",     6.8, 2.70, "close",   0.78, "painted"),
]


def _shop_front(ctx, asset_id, width, x0, key, rng):
    """Ground-floor frontage: door, and a fold-down shuttered display counter."""
    zf = -DEPTH * 0.5

    door_x = x0 + width * (0.20 if key != "apothecary" else 0.78)
    win_x = x0 + width * (0.58 if key != "apothecary" else 0.34)
    win_w, win_h = width * 0.42, 1.25

    wall = K.timber_frame_wall(
        width, GROUND_H, f"{asset_id}.g", style="square", sill_y=0.35,
        openings=[(door_x - x0 - width * 0.5 + width * 0.5, 0, 0, 0)])
    # openings are local to the wall centre; rebuild with correct local coords
    wall = K.timber_frame_wall(
        width, GROUND_H, f"{asset_id}.g", style="square", sill_y=0.35,
        openings=[(door_x - (x0 + width * 0.5), 0.35 + K.DOOR_H * 0.5,
                   K.DOOR_W + 0.4, K.DOOR_H + 0.3),
                  (win_x - (x0 + width * 0.5), 0.35 + 1.45, win_w + 0.3, win_h + 0.3)])
    wall.translate(x0 + width * 0.5, 0, zf)
    SITE.emit(wall)

    fr = K.door_frame(mat="oak_dark")
    fr.translate(door_x, 0.35, zf - 0.13)
    SITE.emit(fr)
    door = K.plank_door(f"{asset_id}.door", mat="oak_weathered",
                        open_angle=rng.uniform(0.0, 0.7))
    door.translate(door_x, 0.35, zf - 0.22)
    SITE.emit(door)
    SITE.entity(f"{asset_id}.door.01", f"door.{key}", (door_x, 0.35, zf - 0.15),
               cell="D5", verbs=["enter"])

    # --- the fold-down display counter -----------------------------------
    # Upper shutter hinges at the head and props open as an awning; lower
    # shutter drops flat and becomes the counter goods sit on.
    opening_y = 0.35 + 1.45
    for sy in (-1, 1):                       # opening surround
        r = M.plank(win_w + 0.28, 0.13, 0.22, 0.008, "oak_dark")
        r.translate(win_x, opening_y + sy * (win_h * 0.5 + 0.065), zf - 0.14)
        SITE.emit(r)
    for sx in (-1, 1):
        j = M.box(0.13, win_h + 0.26, 0.22, 0.008, "oak_dark")
        j.translate(win_x + sx * (win_w * 0.5 + 0.065), opening_y, zf - 0.14)
        SITE.emit(j)

    # Dark interior behind the opening so it reads as a hole, not a panel.
    back = M.box(win_w, win_h, 0.05, 0.004, "oak_dark")
    back.translate(win_x, opening_y, zf + 0.06)
    SITE.emit(back)

    # Upper shutter, propped out as an awning.
    up = M.Group()
    for i in range(4):
        b = M.box(win_w / 4 * 0.96, 0.62, 0.030, 0.004, "oak_weathered")
        b.translate(-win_w * 0.5 + (i + 0.5) * win_w / 4, 0, 0)
        up.add(b)
    led = M.plank(win_w * 0.95, 0.08, 0.024, 0.003, "oak_weathered")
    led.translate(0, 0, 0.028)
    up.add(led)
    up.rotate_x(-1.15)                       # propped up and out
    up.translate(win_x, opening_y + win_h * 0.5 + 0.20, zf - 0.42)
    SITE.emit(up)
    for sx in (-1, 1):                       # prop sticks
        st = M.cylinder(0.018, 0.78, 6, 0.003, "oak_weathered")
        st.rotate_x(0.55)
        st.translate(win_x + sx * win_w * 0.4, opening_y + win_h * 0.5 - 0.05, zf - 0.30)
        SITE.emit(st)

    # Lower shutter, dropped flat: this is the counter.
    low = M.Group()
    for i in range(4):
        b = M.box(win_w / 4 * 0.96, 0.72, 0.032, 0.004, "oak_weathered")
        b.translate(-win_w * 0.5 + (i + 0.5) * win_w / 4, 0, 0)
        low.add(b)
    low.rotate_x(np.pi * 0.5)
    low.translate(win_x, opening_y - win_h * 0.5 - 0.02, zf - 0.48)
    SITE.emit(low)
    for sx in (-1, 1):                       # counter legs
        lg = M.box(0.07, 0.90, 0.07, 0.005, "oak_weathered")
        lg.translate(win_x + sx * win_w * 0.42, opening_y - win_h * 0.5 - 0.47, zf - 0.80)
        SITE.emit(lg)

    counter_y = opening_y - win_h * 0.5 - 0.02
    SITE.entity(f"{asset_id}.counter.01", f"vendor.{key}",
               (win_x, counter_y, zf - 0.48), cell="D5", verbs=["buy"],
               vendor={"currency": "copper", "stock": _stock(key)})
    return win_x, counter_y, zf


def _stock(key):
    """Authoritative vendor stock. The server owns this; the client renders it."""
    return {
        "general": [
            {"item": "rope_coil", "price": 18, "qty": -1},
            {"item": "lamp_oil", "price": 12, "qty": 20},
            {"item": "travel_rations", "price": 9, "qty": -1},
            {"item": "iron_nails", "price": 4, "qty": 60},
        ],
        "apothecary": [
            {"item": "salve_minor", "price": 26, "qty": 12},
            {"item": "dried_herbs", "price": 7, "qty": 40},
            {"item": "tonic_clarity", "price": 55, "qty": 4},
        ],
        "tailor": [
            {"item": "linen_bolt", "price": 32, "qty": 8},
            {"item": "travel_cloak", "price": 78, "qty": 3},
            {"item": "thread_spool", "price": 5, "qty": -1},
        ],
    }[key]


def _goods(ctx, key, cx, cy, cz, rng):
    """Goods on the counter — what actually identifies each shop."""
    if key == "general":
        for i in range(4):                   # sacks and a rope coil
            s = K.sack(f"hm.shop.general.sack{i}", height=0.30)
            s.translate(cx - 0.75 + i * 0.42, cy + 0.02, cz + rng.uniform(-0.1, 0.1))
            SITE.emit(s)
        r = K.rope_coil("hm.shop.general.rope", radius=0.16)
        r.translate(cx + 0.95, cy + 0.02, cz)
        SITE.emit(r)
        for i in range(3):                   # barrels spilling onto the street
            b = K.barrel(f"hm.shop.general.b{i}", height=0.70, belly=0.52)
            b.translate(cx - 1.9 - i * 0.62, 0.35, cz - rng.uniform(0.2, 0.7))
            SITE.emit(b)

    elif key == "apothecary":
        for i in range(9):                   # bottles, the most colourful shop
            h = rng.uniform(0.10, 0.20)
            b = M.lathe([(0.030, 0), (0.042, h * 0.25), (0.040, h * 0.7),
                         (0.018, h * 0.85), (0.020, h)], 9, "glass")
            b.translate(cx - 0.8 + i * 0.20, cy + 0.02, cz + rng.uniform(-0.08, 0.08))
            SITE.emit(b)
        for i in range(6):                   # herb bundles hung to dry
            bun = K.leaf_cluster(f"hm.shop.apoth.herb{i}", radius=0.075,
                                 count=7, mat="foliage", droop=0.9)
            bun.rotate_x(np.pi)              # hanging upside down
            bun.translate(cx - 0.9 + i * 0.36, cy + 1.28, cz + 0.12)
            SITE.emit(bun)

    else:                                    # tailor — the tidiest of the three
        for i in range(4):                   # bolts of cloth, stacked neatly
            bolt = M.lathe([(0.075, 0), (0.075, 0.62)], 10, "canvas")
            bolt.rotate_z(np.pi * 0.5)
            bolt.translate(cx - 0.35, cy + 0.08 + i * 0.155, cz + rng.uniform(-0.03, 0.03))
            SITE.emit(bolt)
        # Dress form in the window.
        form = M.lathe([(0.0, 0), (0.10, 0.05), (0.17, 0.34), (0.13, 0.52),
                        (0.17, 0.70), (0.11, 0.86), (0.0, 0.92)], 12, "canvas")
        form.translate(cx + 0.62, cy + 0.02, cz + 0.30)
        SITE.emit(form)


def build(ctx: VenueContext, asset_id="hm.shop"):
    SITE.bind(ctx)
    rng = rng_for(asset_id, "shoprow")
    total_w = sum(s[1] for s in SHOPS)
    x = -total_w * 0.5

    for (key, w, up_h, style, pitch, sign_mat) in SHOPS:
        sid = f"{asset_id}.{key}"
        srng = rng_for(sid, "shop")

        SITE.emit(K.stone_plinth(w + 0.1, DEPTH + 0.2, 0.35), "stone")
        pl = K.stone_plinth(w + 0.1, DEPTH + 0.2, 0.35)
        pl.translate(x + w * 0.5, 0, 0)
        SITE.emit(pl, "stone")

        cx, cy, cz = _shop_front(ctx, sid, w, x, key, srng)
        _goods(ctx, key, cx, cy, cz, srng)

        # --- collision ---------------------------------------------------
        # A terrace is one continuous solid mass with three doorways in its
        # street face. The 0.35 m plinth is exactly the controller's step
        # height, so it needs no flight; the jettied upper storey oversails at
        # 3.35 m and is over the player's head.
        door_x = x + w * (0.20 if key != "apothecary" else 0.78)
        DOORWAY = K.DOOR_W + 0.5
        SITE.collider("box", center=(x + w * 0.5, 0.175, 0),
                     half=((w + 0.1) * 0.5, 0.175, (DEPTH + 0.2) * 0.5),
                     tag="plinth")
        SITE.collider_walls(w, DEPTH, GROUND_H + up_h, y=0.35, thickness=0.32,
                           center=(x + w * 0.5, 0.0),
                           doors=[("-z", door_x - (x + w * 0.5), DOORWAY)])

        # --- upper storey: every shop different ---------------------------
        # This is what keeps a 20m terrace from reading as one extruded block.
        y1 = 0.35 + GROUND_H
        jt = K.jetty(w, DEPTH, 0.30)
        jt.translate(x + w * 0.5, y1, 0)
        SITE.emit(jt)

        uw, ud = w + 0.6, DEPTH + 0.6
        for sz in (-1, 1):
            wl = K.timber_frame_wall(uw, up_h, f"{sid}.u{sz}", style=style, sill_y=0)
            if sz > 0:
                wl.rotate_y(np.pi)
            wl.translate(x + w * 0.5, y1, sz * ud * 0.5)
            SITE.emit(wl)
        for sx in (-1, 1):
            wl = K.timber_frame_wall(ud, up_h, f"{sid}.us{sx}", style=style, sill_y=0)
            wl.rotate_y(sx * np.pi * 0.5)
            wl.translate(x + w * 0.5 + sx * uw * 0.5, y1, 0)
            SITE.emit(wl)

        for i in range(2):
            win = K.leaded_window(f"{sid}.uw{i}", width=0.80, height=0.95,
                                  mat="glass_lit" if srng.random() < 0.5 else "glass",
                                  shutters=srng.random() < 0.5,
                                  shutter_mat="painted")
            win.translate(x + w * (0.28 + i * 0.42), y1 + up_h * 0.5, -ud * 0.5 - 0.06)
            SITE.emit(win)

        y2 = y1 + up_h
        roof = K.gable_roof(ud, uw, f"{sid}.roof", pitch=pitch, overhang=0.42)
        roof.rotate_y(np.pi * 0.5)
        roof.translate(x + w * 0.5, y2, 0)
        SITE.emit(roof)
        for sx in (-1, 1):
            g = K.gable_end(ud, y2, pitch, mat="plaster", depth=0.22)
            g.rotate_y(np.pi * 0.5)
            g.translate(x + w * 0.5 + sx * uw * 0.5, 0, 0)
            SITE.emit(g)

        ch = K.chimney(f"{sid}.chimney", height=2.2 + srng.uniform(0, 0.6),
                       section=0.60)
        ch.translate(x + w * srng.uniform(0.2, 0.8), y2 - 0.2, srng.uniform(-0.5, 0.5))
        SITE.emit(ch)

        # --- pictorial hanging sign --------------------------------------
        sign = K.hanging_sign(f"{sid}.sign", width=0.66, height=0.50,
                              board_mat=sign_mat, reach=0.90,
                              sway=srng.uniform(-0.07, 0.07))
        sign.translate(x + w * 0.5, 0.35 + 2.72, -DEPTH * 0.5 - 0.18)
        SITE.emit(sign)

        # The icon on each board — a mortar, a spool, a barrel. No lettering.
        icon_x = x + w * 0.5 + 0.60
        icon_y = 0.35 + 2.72 - 0.42
        icon_z = -DEPTH * 0.5 - 0.22
        if key == "apothecary":
            ic = M.lathe([(0.10, 0), (0.12, 0.04), (0.09, 0.16), (0.12, 0.19)], 10, "ashlar")
            ic.translate(icon_x, icon_y - 0.10, icon_z)
            SITE.emit(ic)
            pst = M.cylinder(0.022, 0.22, 6, 0.003, "oak_dark")
            pst.rotate_z(0.5)
            pst.translate(icon_x + 0.04, icon_y + 0.02, icon_z)
            SITE.emit(pst)
        elif key == "tailor":
            sp = M.lathe([(0.085, 0), (0.045, 0.03), (0.045, 0.17), (0.085, 0.20)], 10, "oak_dark")
            sp.rotate_z(np.pi * 0.5)
            sp.translate(icon_x + 0.10, icon_y, icon_z)
            SITE.emit(sp)
        else:
            bl = K.barrel(f"{sid}.icon", height=0.28, belly=0.22)
            bl.translate(icon_x, icon_y - 0.14, icon_z)
            SITE.emit(bl)

        # --- residue -----------------------------------------------------
        if key == "general":
            br = M.Group()
            hh = M.cylinder(0.020, 1.30, 6, 0.003, "oak_weathered")
            br.add(hh)
            hd = M.box(0.08, 0.24, 0.18, 0.008, "thatch")
            br.add(hd)
            br.rotate_z(-0.26)
            br.translate(x + w * 0.90, 0.35, -DEPTH * 0.5 - 0.5)
            SITE.emit(br)
        elif key == "tailor":
            cat = M.lathe([(0.0, 0), (0.085, 0.05), (0.075, 0.26), (0.0, 0.34)], 8,
                          "oak_weathered")
            cat.rotate_z(np.pi * 0.45)
            cat.rotate_y(0.6)
            cat.translate(cx + 0.15, cy + 0.10, cz + 0.05)
            SITE.emit(cat)

        x += w
