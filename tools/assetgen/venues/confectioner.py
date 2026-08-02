"""Confectioner — slot 21. The one luxury frontage in Hearthmere.

Every other shop in this town sells things people need. This one sells sugar,
which at this date arrives by ship in a hard cone wrapped in blue paper, costs
more by weight than most of what the blacksmith makes, and is bought by the
ounce for a wedding or a saint's day. That single fact is the whole design:

  - the frontage is **painted**, and nothing else on Kirk Green is. Paint is
    expensive and it announces that the owner can waste money on being seen.
  - the glazing is **leaded quarries in small panes** — more lead than glass,
    because the panes are small and there are a lot of them, which is exactly
    what a period luxury shopfront looks like
  - it is the **tidiest** front in Hearthmere. Everywhere else in this town
    Art Bible §7's residue is mess: shavings, spilled grain, mud. Here the
    residue is *fastidiousness* — swept step, wiped counter, goods squared up,
    a cloth over the tray — and the one spill is sugar, which is white, and
    which somebody has already half-swept. Contrast is what makes a street
    read as several different people rather than one generator.

The slot note gives it two jobs: a gable to Kirk Green with a sugar-loaf sign
on an iron bracket, and the **second near jamb of the arrival frame**. From the
altar it stands 23 m away and 29 degrees left of the axis, which puts it right
on the edge of the aperture — so what matters from that camera is its silhouette
against the sky and the colour of its gable, not its counter. It is authored to
work at both ranges: the painted gable, the bracket and the loaf read at 23 m,
and the sugar work rewards walking up to it.
"""

from __future__ import annotations

import math

import numpy as np

from core import mesh as M
from core import kit as K
from core import props as P
from core import roof as R
from core import streetscape as S
from core import siting as SI
from core.mathx import rng_for
from core.venue import VenueContext
from core import materials as MATS

NAME = "confectioner"
ASSET = "hm.slot.21.confectioner"

SITE = SI.Site(NAME)
CELLS = SITE.cells

W, D = SITE.w, SITE.d              # 6.0 x 10.0, gable to the green
EAVES = SITE.eaves                 # 6.40
PLINTH = 0.44
GF = 2.95                          # shop floor to the bressumer
JETTY = 0.34
PITCH = 1.02

FLOOR = PLINTH
UPPER_Y = FLOOR + GF + 0.26
UPPER_H = EAVES - UPPER_Y

# Two paints, and they are the identity of the building from across the green.
PAINT = "painted_crimson"
TRIM = "painted_amber"


def _shell(ctx, g, rng):
    """Plinth, walls, the jettied upper storey and the roof.

    Gable to the street, so the ridge runs back into the plot and the frontage
    is one narrow, tall, painted end wall — the most valuable 6 m of elevation
    in the town per square metre, and it is spent entirely on being looked at.
    """
    poly = SI.rect(0.0, 0.0, W + 0.24, D + 0.24)
    plinth, y0 = SI.plinth_under(SITE, poly, PLINTH, mat="ashlar", chamfer=0.03)
    g.add(plinth)
    ctx.collider("box", center=SITE.p(0, (y0 + PLINTH) * 0.5, 0),
                 half=((W + 0.24) * 0.5, max((PLINTH - y0) * 0.5, 0.05),
                       (D + 0.24) * 0.5),
                 rot_y=SITE.yaw(), kind="surface", tag="plinth")

    zf = -D * 0.5
    door_x = W * 0.5 - 1.28
    win_x, win_w, win_h = -W * 0.5 + 1.95, 2.35, 1.35
    sill = FLOOR + 0.98

    front = K.timber_frame_wall(
        W, GF, f"{ASSET}.gf", style="close", sill_y=FLOOR, timber_mat=PAINT,
                openings=[(door_x, K.DOOR_H * 0.5 + 0.05, K.DOOR_W + 0.34, K.DOOR_H + 0.28),
                  (win_x - 0.0, sill - FLOOR + win_h * 0.5, win_w + 0.26, win_h + 0.24)])
    front.translate(0, 0, zf)
    g.add(front)

    back = K.timber_frame_wall(W, GF, f"{ASSET}.gb", style="square",
                               sill_y=FLOOR,                                openings=[(0.6, 1.55, 0.95, 1.05)])
    back.rotate_y(np.pi)
    back.translate(0, 0, -zf)
    g.add(back)
    for sx in (-1, 1):
        side = K.timber_frame_wall(D, GF, f"{ASSET}.gs{sx}", style="close",
                                   sill_y=FLOOR)
        side.rotate_y(sx * np.pi * 0.5)
        side.translate(sx * W * 0.5, 0, 0)
        g.add(side)

    # Interior: a dark, warm room behind the counter, so the display opening
    # reads as a hole into a shop and not as a painted panel.
    sh = M.box(W - 0.5, GF + UPPER_H, D - 0.5, 0.02, "oak_dark")
    sh.scale(-1.0, 1.0, 1.0)
    sh.translate(0, FLOOR + (GF + UPPER_H) * 0.5, 0)
    SITE.emit(sh, shell=True)

    # --- the jetty -------------------------------------------------------
    # Only on the FRONT, which is how a narrow burgage plot jetties: you cannot
    # oversail your neighbour's ground, and both side walls are on the boundary.
    jt = K.jetty(W, D, JETTY)
    jt.translate(0, FLOOR + GF, 0)
    g.add(jt)

    uw, ud = W + 0.20, D + JETTY
    uz = -JETTY * 0.5
    up_front = K.timber_frame_wall(
        uw, UPPER_H, f"{ASSET}.uf", style="close", sill_y=UPPER_Y,
        timber_mat=PAINT,
                openings=[(-0.35, 1.42, 2.90, 1.45)])
    up_front.translate(0, 0, zf - JETTY)
    g.add(up_front)
    up_back = K.timber_frame_wall(uw, UPPER_H, f"{ASSET}.ub", style="square",
                                  sill_y=UPPER_Y)
    up_back.rotate_y(np.pi)
    up_back.translate(0, 0, -zf)
    g.add(up_back)
    for sx in (-1, 1):
        s2 = K.timber_frame_wall(ud, UPPER_H, f"{ASSET}.us{sx}", style="close",
                                 sill_y=UPPER_Y,                                  openings=[(1.9, 1.45, 0.95, 1.10)])
        s2.rotate_y(sx * np.pi * 0.5)
        s2.translate(sx * uw * 0.5, 0, uz)
        g.add(s2)

    SITE.collider_walls(W, D, GF + UPPER_H, y=FLOOR, thickness=0.30,
                        doors=[("-z", door_x, K.DOOR_W + 0.45)], tag="shop")
    SITE.collider_steps((door_x, 0.0, -(D + 0.24) * 0.5), PLINTH,
                        tread=0.48, width=1.35)

    # --- roof ------------------------------------------------------------
    # Edge 0 runs along +X (the frontage), and slot 21 says ridge "gable", so
    # the ridge runs BACK into the plot: `ridge_axis="v"`. The street end is a
    # gable, which is the whole point of the plot shape.
    rpoly = SI.rect(0.0, uz, uw, ud)
    plate = R.wall_plate(rpoly, EAVES, edges=["gable", "eaves", "gable", "eaves"],
                         thickness=0.30, wall_mat="plaster")
    roof = R.roof_from_plate(plate, "gable", PITCH, 0.46, f"{ASSET}.roof",
                             mat="terracotta", timber_mat="oak_dark",
                             ridge_axis="v")
    g.add(roof)

    for sz in (-1, 1):
        ge = K.gable_end(uw, EAVES, PITCH, mat="plaster", depth=0.24)
        ge.translate(0, 0, uz + sz * ud * 0.5)
        g.add(ge)

    # PAINTED barge boards with a cusped edge, and a finial. This is the
    # element that reads from the church door: a red-and-amber gable in a town
    # of bare oak and lime.
    apex = EAVES + PITCH * uw * 0.5
    for sx in (-1, 1):
        # Build the RIGHT-HAND board every time, then hand it. The board is
        # anchored at its own origin and runs out in +x, so `rotate_z(-angle)`
        # for the left side mirrored the angle and not the direction: the board
        # climbed up-and-right, left the roof at the apex and ended five metres
        # above the ridge in open sky, on the market place, in the sightline
        # from Ford Road. Mirror the geometry (mesh.mirror_x, which also flips
        # the winding) and both boards descend from the apex to their eaves.
        rafter = math.hypot(uw * 0.5, PITCH * uw * 0.5) + 0.30
        bb = M.chamfered_prism(
            [(0.0, 0.0), (rafter, 0.0), (rafter, 0.30), (0.0, 0.30)],
            0.055, PAINT, 0.010)
        bb.rotate_z(-math.atan(PITCH))
        if sx < 0:
            bb.mirror_x()
        bb.translate(sx * 0.10, apex - 0.20, zf - JETTY - 0.30)
        g.add(bb)
    for k in range(7):
        f = (k + 0.5) / 7.0
        cu = M.lathe([(0.085, 0.0), (0.10, 0.05), (0.0, 0.20)], 7, TRIM)
        cu.rotate_x(np.pi * 0.5)
        for sx in (-1, 1):
            c2 = cu.copy()
            c2.translate(sx * uw * 0.5 * f, apex - PITCH * uw * 0.5 * f - 0.30,
                         zf - JETTY - 0.33)
            g.add(c2)
    fin = M.lathe([(0.075, 0.0), (0.055, 0.30), (0.11, 0.36), (0.0, 0.62)], 8,
                  TRIM)
    fin.translate(0, apex - 0.05, zf - JETTY - 0.16)
    g.add(fin)

    ch = R.chimney_through(roof, 0.9, D * 0.5 - 1.6, FLOOR, f"{ASSET}.ch",
                           section=0.66, mat="brick", above=1.05)[0]
    g.add(ch)
    return door_x, win_x, win_w, win_h, sill, zf


def _shopfront(ctx, g, rng, door_x, win_x, win_w, win_h, sill, zf):
    """The fold-down display window: shutter up as an awning, shutter down as
    the counter. Painted, because everything at the front of this shop is.

    Period-correct and instantly readable as "shop", and it does the one thing
    a street elevation most needs — it puts goods at the player's eye level,
    outside, in colour.
    """
    op_y = sill + win_h * 0.5

    # Moulded surround in the shop's own paint.
    for sy in (-1, 1):
        r = M.plank(win_w + 0.36, 0.17, 0.24, 0.010, PAINT)
        r.translate(win_x, op_y + sy * (win_h * 0.5 + 0.085), zf - 0.13)
        g.add(r)
    for sx in (-1, 1):
        j = M.box(0.17, win_h + 0.34, 0.24, 0.010, PAINT)
        j.translate(win_x + sx * (win_w * 0.5 + 0.085), op_y, zf - 0.13)
        g.add(j)
    # Dentil course over the opening — the cheap classical gesture a provincial
    # shopkeeper reaches for, and the reason this front looks "done".
    for k in range(11):
        d = M.box(0.075, 0.085, 0.13, 0.006, TRIM)
        d.translate(win_x - win_w * 0.5 + 0.09 + k * (win_w - 0.18) / 10.0,
                    op_y + win_h * 0.5 + 0.245, zf - 0.19)
        g.add(d)

    # Small leaded quarries behind the opening: more lead than glass.
    gl = M.box(win_w, win_h, 0.03, 0.004, "glass")
    gl.translate(win_x, op_y, zf + 0.05)
    g.add(gl)
    for k in range(5):
        mu = M.box(0.035, win_h, 0.05, 0.003, "lead")
        mu.translate(win_x - win_w * 0.5 + (k + 1) * win_w / 6.0, op_y, zf + 0.01)
        g.add(mu)
    for k in range(3):
        tr = M.plank(win_w, 0.05, 0.035, 0.003, "lead")
        tr.translate(win_x, op_y - win_h * 0.5 + (k + 1) * win_h / 4.0, zf + 0.01)
        g.add(tr)

    # Upper shutter, propped out as an awning, with a scalloped cloth valance.
    up = M.Group()
    for i in range(5):
        b = M.box(win_w / 5 * 0.95, 0.70, 0.032, 0.005, PAINT)
        b.translate(-win_w * 0.5 + (i + 0.5) * win_w / 5, 0, 0)
        up.add(b)
    for y in (-0.22, 0.22):
        led = M.plank(win_w * 0.96, 0.085, 0.026, 0.004, TRIM)
        led.translate(0, y, 0.030)
        up.add(led)
    up.rotate_x(-1.12)
    up.translate(win_x, op_y + win_h * 0.5 + 0.24, zf - 0.46)
    g.add(up)
    for sx in (-1, 1):
        st = M.cylinder(0.020, 0.84, 6, 0.003, "oak_weathered")
        st.rotate_x(0.52)
        st.translate(win_x + sx * win_w * 0.42, op_y + win_h * 0.5 - 0.02, zf - 0.32)
        g.add(st)
    val = M.sheet(win_w * 0.98, 0.30,
                  lambda u, v: -0.045 * abs(math.sin(u * 7.0)),
                  nx=13, nz=3, mat="canvas_crimson", plane="xz")
    val.rotate_x(np.pi * 0.5)
    val.translate(win_x, op_y + win_h * 0.5 + 0.42, zf - 0.86)
    g.add(val)

    # Lower shutter dropped flat: the counter. Its front edge is where the
    # town's money changes hands, so it is the most-worn oak on the building.
    low = M.Group()
    for i in range(5):
        b = M.box(win_w / 5 * 0.95, 0.78, 0.034, 0.005, "oak_weathered")
        b.translate(-win_w * 0.5 + (i + 0.5) * win_w / 5, 0, 0)
        low.add(b)
    low.rotate_x(np.pi * 0.5)
    cy = op_y - win_h * 0.5 - 0.02
    low.translate(win_x, cy, zf - 0.50)
    g.add(low)
    for sx in (-1, 1):
        lg = M.box(0.075, cy - PLINTH, 0.075, 0.006, "oak_weathered")
        lg.translate(win_x + sx * win_w * 0.42, PLINTH + (cy - PLINTH) * 0.5,
                     zf - 0.82)
        g.add(lg)
    ctx.collider("box", center=SITE.p(win_x, (PLINTH + cy) * 0.5, zf - 0.48),
                 half=(win_w * 0.5, (cy - PLINTH) * 0.5, 0.42),
                 rot_y=SITE.yaw(), tag="counter")

    SITE.entity(f"{ASSET}.counter.01", "vendor.confectioner",
                (win_x, cy, zf - 0.50), verbs=["buy"],
                vendor={"currency": "copper", "stock": [
                    {"item": "sugar_comfits", "price": 14, "qty": 30},
                    {"item": "candied_quince", "price": 22, "qty": 12},
                    {"item": "honeycomb", "price": 9, "qty": -1},
                    {"item": "marchpane_subtlety", "price": 96, "qty": 2},
                ]})
    return cy


def _sugar_work(ctx, g, rng, win_x, win_w, cy, zf):
    """What is actually for sale, in the order it is made and sold.

    Workflow, not symmetry: the loaf and the nippers are at the back where the
    work happens, the scales stand between the loaf and the customer because
    sugar is sold by weight, and the finished goods — comfits, candied fruit,
    honeycomb, the marchpane subtlety — are ranked along the front edge in
    ascending price, which is how a shopkeeper who wants the expensive one
    noticed actually lays out a counter.
    """
    # THE SUGAR LOAF: a hard cone, still half in its blue wrapper. It is the
    # trade's whole identity and it repeats on the sign outside.
    loaf = M.lathe([(0.145, 0.0), (0.150, 0.04), (0.125, 0.30), (0.075, 0.52),
                    (0.028, 0.62), (0.0, 0.66)], 14, "sugar")
    loaf.translate(win_x + win_w * 0.34, cy + 0.02, zf - 0.34)
    g.add(loaf)
    wrap = M.lathe([(0.155, 0.0), (0.152, 0.16), (0.128, 0.30), (0.0, 0.33)],
                   12, "cloth_blue", close_top=False)
    wrap.rotate_y(0.4)
    wrap.translate(win_x + win_w * 0.34, cy + 0.015, zf - 0.34)
    g.add(wrap)
    # Sugar nippers on the block beside it — a loaf is sold in lumps cut off it.
    nip = M.Group()
    for s in (-1, 1):
        a = M.box(0.022, 0.032, 0.24, 0.003, "steel_blued")
        a.rotate_y(s * 0.16)
        a.translate(s * 0.026, 0, 0)
        nip.add(a)
    nip.add(M.ring(0.024, 0.006, "iron", 8))
    nip.rotate_y(rng.uniform(-0.5, 0.5))
    nip.translate(win_x + win_w * 0.20, cy + 0.05, zf - 0.30)
    g.add(nip)

    # Scales, between the loaf and the buyer, because that is where the trust is.
    sc = P.coin_scales(f"{ASSET}.scales")
    sc.translate(win_x + win_w * 0.06, cy + 0.02, zf - 0.44)
    g.add(sc)

    # Comfits in a shallow tray, part-covered with a cloth against the flies —
    # the fastidiousness that stands in for mess in this one shop.
    tray = M.chamfered_prism([(-0.26, -0.17), (0.26, -0.17), (0.26, 0.17),
                              (-0.26, 0.17)], 0.055, "pottery_slip", 0.006,
                             uv_scale=MATS.uv_detail("pottery_slip", 0.5, why="0.06 m member; the library's 1 m tile shows 6% of one tile here and reads as flat colour"))
    tray.rotate_x(np.pi * 0.5)
    tray.translate(win_x - win_w * 0.30, cy + 0.045, zf - 0.44)
    g.add(tray)
    for i in range(16):
        a = rng.uniform(0, 6.28)
        r = rng.uniform(0.0, 1.0) ** 0.6
        cm = M.globe(rng.uniform(0.014, 0.021), "sugar", 6, 3, sy=0.8)
        cm.translate(win_x - win_w * 0.30 + math.cos(a) * r * 0.22,
                     cy + 0.062, zf - 0.44 + math.sin(a) * r * 0.14)
        g.add(cm)
    cov = M.sheet(0.30, 0.36, lambda u, v: -0.02 * math.sin(u * 5.0),
                  nx=5, nz=4, mat="linen", plane="xz")
    cov.translate(win_x - win_w * 0.36, cy + 0.075, zf - 0.44)
    g.add(cov)

    # Candied fruit in small glazed jars, ranked by price along the front edge.
    for i in range(4):
        j = P.glazed_jar(f"{ASSET}.jar{i}", height=0.20 + i * 0.02,
                         stopper=i % 2 == 0)
        j.rotate_y(rng.uniform(-3, 3))
        j.translate(win_x - win_w * 0.44 + i * 0.30, cy + 0.045,
                    zf - 0.66 + rng.uniform(-0.02, 0.02))
        g.add(j)
    # Honeycomb on a slate, cut, with the cut face turned to the street.
    sl = M.box(0.34, 0.022, 0.24, 0.004, "slate", uv_scale=MATS.uv_detail("slate", 0.4, why="0.34 m member; the library's 4 m tile shows 8% of one tile here and reads as flat colour"))
    sl.translate(win_x + win_w * 0.42, cy + 0.032, zf - 0.62)
    g.add(sl)
    for i in range(3):
        hc = M.chamfered_prism([(-0.075, -0.055), (0.075, -0.055),
                                (0.085, 0.055), (-0.065, 0.055)],
                               rng.uniform(0.035, 0.055), "beeswax", 0.004)
        hc.rotate_x(np.pi * 0.5)
        hc.rotate_y(rng.uniform(-0.4, 0.4))
        hc.translate(win_x + win_w * 0.42 + rng.uniform(-0.09, 0.09),
                     cy + 0.06, zf - 0.62 + rng.uniform(-0.06, 0.06))
        g.add(hc)

    # The marchpane subtlety in the window itself — the thing nobody can afford
    # and everybody stops to look at. A moulded castle in almond paste.
    sub = M.Group()
    sub.add(M.box(0.34, 0.075, 0.28, 0.006, "sugar"))
    for sx in (-1, 1):
        for sz in (-1, 1):
            t = M.lathe([(0.048, 0.0), (0.042, 0.16), (0.055, 0.185),
                         (0.0, 0.28)], 8, "sugar")
            t.translate(sx * 0.12, 0.038, sz * 0.10)
            sub.add(t)
    sub.add(M.box(0.16, 0.13, 0.16, 0.006, "sugar").translate(0, 0.10, 0))
    sub.rotate_y(0.5)
    sub.translate(win_x - win_w * 0.06, cy + 0.30, zf + 0.28)
    g.add(sub)
    st = M.lathe([(0.13, 0.0), (0.115, 0.24), (0.20, 0.28)], 10, "oak_dark")
    st.translate(win_x - win_w * 0.06, cy + 0.02, zf + 0.28)
    g.add(st)

    # Shelved jars behind, seen through the glass and through the opening.
    for r in range(2):
        shf = M.plank(win_w * 0.92, 0.24, 0.030, 0.006, "oak_weathered")
        shf.translate(win_x, cy + 0.62 + r * 0.44, zf + 0.42)
        g.add(shf)
        for i in range(5):
            j = P.glazed_jar(f"{ASSET}.bj{r}{i}", height=0.24, stopper=True)
            j.rotate_y(rng.uniform(-3, 3))
            j.translate(win_x - win_w * 0.36 + i * win_w * 0.18,
                        cy + 0.635 + r * 0.44, zf + 0.42)
            g.add(j)


def _sign_and_threshold(ctx, g, rng, door_x, zf):
    """The sugar-loaf sign on its iron bracket, and the swept step.

    The sign is the slot note's own instruction and it is the element that
    identifies this building at 23 m from the church door. It is pictorial:
    the loaf IS the sign (Art Bible §2 — no lettering anywhere).
    """
    bx = door_x + 0.42
    by = FLOOR + 3.15
    br = K.sign_bracket(f"{ASSET}.bracket", reach=0.92, mat="iron")
    br.translate(bx, by, zf - 0.10)
    g.add(br)
    # A cone of sugar, carved and painted, hanging from the bracket.
    hang = M.Group()
    for s in (-1, 1):
        hang.add(M.tube((s * 0.16, 0.0, 0.0), (s * 0.05, -0.30, 0.0), 0.010,
                        "iron", 5))
    lf = M.lathe([(0.22, 0.0), (0.225, 0.05), (0.185, 0.36), (0.10, 0.66),
                  (0.035, 0.80), (0.0, 0.86)], 14, "sugar")
    lf.rotate_x(np.pi)                       # hangs point DOWN, as it is stored
    lf.translate(0, -0.34, 0)
    hang.add(lf)
    bnd = M.lathe([(0.20, 0.0), (0.19, 0.14), (0.0, 0.16)], 12, "cloth_blue",
                  close_top=False)
    bnd.rotate_x(np.pi)
    bnd.translate(0, -0.42, 0)
    hang.add(bnd)
    hang.rotate_y(rng.uniform(-0.06, 0.06))
    hang.translate(bx + 0.70, by - 0.06, zf - 0.10)
    g.add(hang)
    SITE.entity(f"{ASSET}.sign.01", "prop.sign",
                (bx + 0.70, by - 0.80, zf - 0.10), verbs=["inspect"])

    # A swept, scrubbed threshold — the anti-residue that makes this shop read
    # as somebody's pride. The one spill is sugar, and it is half-swept already.
    th = S.threshold_stone(f"{ASSET}.step", width=1.45, depth=0.68, rise=0.12)
    th.translate(door_x, PLINTH - 0.12, zf - 0.36)
    g.add(th)
    g.add(P.worn_patch(f"{ASSET}.arc", shape="arc", size=0.82, mat="stone")
          .translate(door_x, PLINTH + 0.012, zf - 0.62))
    g.add(P.broom(f"{ASSET}.broom", length=1.28, wall_z=zf, x=door_x + 0.92))
    g.add(P.dust_film(f"{ASSET}.sugar", radius=0.42, mat="sugar",
                      centre=(door_x + 0.55, zf - 0.72), y=PLINTH, density=0.5))
    # Window boxes, clipped and in flower, on the upper front.
    from core import vegetation as V
    for sx in (-1, 1):
        wb = V.window_box(f"{ASSET}.wb{sx}", width=0.78)
        wb.translate(-0.35 + sx * 1.05, UPPER_Y + 0.62, zf - 0.34 - 0.10)
        g.add(wb)
    # A hitching ring and a scrubbing bucket, upturned to drain.
    bu = P.bucket(f"{ASSET}.bucket", height=0.28, top=0.16)
    bu.rotate_z(np.pi)
    bu.translate(door_x + 1.28, PLINTH + 0.28, zf - 0.44)
    g.add(bu)


def _upper(ctx, g, rng, zf):
    """The chamber over the shop: one long leaded oriel, because the confectioner
    lives above the money and wants to be seen doing it."""
    y = UPPER_Y + 0.72
    ow, oh = 2.90, 1.45
    box = M.chamfered_prism([(-ow * 0.5, 0.0), (ow * 0.5, 0.0),
                             (ow * 0.5 - 0.14, 0.42), (-ow * 0.5 + 0.14, 0.42)],
                            oh + 0.30, PAINT, 0.012)
    box.rotate_x(np.pi * 0.5)
    box.translate(-0.35, y + oh * 0.5 - 0.15, zf - JETTY - 0.44)
    g.add(box)
    for i in range(3):
        wdt = (0.86, 1.02, 0.86)[i]
        lt = K.leaded_window(f"{ASSET}.o{i}", width=wdt, height=oh - 0.16,
                             mat="glass", shutters=False)
        lt.translate(-0.35 + (i - 1) * 0.97, y + oh * 0.5 - 0.10,
                     zf - JETTY - 0.72)
        g.add(lt)
    for sx in (-1, 1):
        co = K.corbel(f"{ASSET}.oc{sx}", project=0.42, width=0.22, height=0.30,
                      mat="oak_dark")
        co.translate(-0.35 + sx * 1.20, y - 0.34, zf - JETTY - 0.06)
        g.add(co)
    hood = M.chamfered_prism([(-ow * 0.5 - 0.12, 0.0), (ow * 0.5 + 0.12, 0.0),
                              (ow * 0.5 + 0.04, 0.13), (-ow * 0.5 - 0.04, 0.13)],
                             0.56, TRIM, 0.010)
    hood.rotate_x(np.pi * 0.5)
    hood.translate(-0.35, y + oh + 0.22, zf - JETTY - 0.34)
    g.add(hood)


def build(ctx: VenueContext, asset_id=ASSET):
    SITE.bind(ctx)
    rng = rng_for(asset_id, "confectioner")
    g = M.Group()

    door_x, win_x, win_w, win_h, sill, zf = _shell(ctx, g, rng)
    cy = _shopfront(ctx, g, rng, door_x, win_x, win_w, win_h, sill, zf)
    _sugar_work(ctx, g, rng, win_x, win_w, cy, zf)
    _sign_and_threshold(ctx, g, rng, door_x, zf)
    _upper(ctx, g, rng, zf)

    fr = K.door_frame(width=1.02, height=2.10, mat=PAINT, depth=0.28)
    fr.translate(door_x, FLOOR, zf - 0.10)
    g.add(fr)
    dr = K.plank_door(f"{ASSET}.door", width=0.98, height=2.06, mat=PAINT,
                      open_angle=rng.uniform(0.55, 0.85))
    dr.translate(door_x, FLOOR, zf - 0.18)
    g.add(dr)
    SITE.entity(f"{ASSET}.door.01", "door.confectioner",
                (door_x, FLOOR, zf - 0.20), verbs=["enter"])

    SITE.emit(g, container="confectioner")

    print(SITE.report())
    print(f"      gable to Kirk Green  eaves {EAVES:.2f}  "
          f"apex {EAVES + PITCH * (W + 0.20) * 0.5:.2f}  counter {FLOOR + 1.04:.2f}")
