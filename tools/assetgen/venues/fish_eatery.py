"""The mere-fish eating house — slot 64, on the north side of Wharf Lane.

`docs/areas/hearthmere/plan/schedule.md`: *"Six trestles under an awning, a smoking shed behind,
and a queue at noon. Faces north onto Wharf Lane, so it is lit."*

The brief for this venue is a smell, and a smell has to be built as something
you can see. Three things do it:

  the CHIMNEY that is always going, so there is a plume over the waterfront
  the SMOKING SHED behind, doors ajar on racks of split fish over a smother
  the GUTTING BOARDS at the lane end, wet, with the barrel of trimmings beside
  them that the cat is working on

Composed as Art Bible §7 asks. The anchor is the smoke shed's louvred cowl and
its stack; the function is laid out by workflow, from the water end to the
street — gutting, brining, smoking, then the trestles where it is eaten; and
the residue is what six trestles look like at half past nine, which is
half-cleared from last night rather than laid for lunch.
"""

from __future__ import annotations

import json
import math
import os

import numpy as np

from core import building as BLD
from core import kit as K
from core import mesh as M
from core import props as PR
from core import terrain as T
from core.mathx import rng_for
from core.venue import VenueContext, REPO
from core import materials as MATS

NAME = "fish_eatery"
CELLS = ["H3", "H4", "I3", "I4"]

TOWN = os.path.join(REPO, "content/town/hearthmere.json")
SLOT = "hm.slot.64.fish_eatery"
AID = "hm.fish_eatery"

STYLE = dict(
    name="fish_eatery",
    # half_hip, not gable — see core/mesh.py:spin_y. The gable was a workaround
    # for rafter feet sliding off the roof, which is fixed.
    walls=["rubble", "timber"], frame="cross", roof="half_hip",
    roof_mat="terracotta", pitch=(0.92, 1.00), jetty=0.0, plinth=(0.36, 0.46),
    windows=1.8, wealth=0.35, dormers=(0, 0), chimneys=1, shutters=True,
    shopfront=True, storey_h=(2.85, 3.05))


def _awning(g, plan, rng):
    """Six trestles under a canvas awning on the lane frontage.

    The awning is a lean-to on poles, not a roof: it is stitched out of three
    widths of sailcloth with the seams showing, it sags between the poles
    because canvas does, and one corner has been let go so the light gets in
    under it.
    """
    fp = plan["footprint"]
    hw, hd = fp.half
    fy = plan["floor_y"]
    theta = fp.theta

    def L(a, b):
        return fp.world(a, b)

    reach = 3.9
    eaves = fy + 2.45
    poles = []
    for i in range(4):
        a = -hw + 0.6 + i * (hw * 2 - 1.2) / 3
        x, z = L(a, -hd - reach)
        gy = float(T.height(x, z))
        p = M.cylinder(0.095, eaves - 0.20 - gy, 8, 0.008, "oak_weathered")
        p.rotate_z(float(rng.uniform(-0.012, 0.012)))
        p.translate(x, gy, z)
        g.add(p)
        poles.append((x, gy, z, a))
    # Head rail on the poles, and the wall plate the other side.
    for (bx, bz), y in ((L(0.0, -hd - reach), eaves - 0.20),
                        (L(0.0, -hd - 0.10), eaves + 0.55)):
        rail = M.plank(hw * 2.0, 0.13, 0.11, 0.008, "oak_weathered")
        rail.rotate_y(-theta)
        rail.translate(bx, y, bz)
        g.add(rail)
    # The cloth itself: three widths, sagging, one corner dropped.
    for k in range(3):
        w = (hw * 2.0) / 3.0
        a0 = -hw + k * w
        cx, cz = L(a0 + w * 0.5, -hd - reach * 0.5)
        drop = 0.55 if k == 2 else 0.0

        def hf(u, v, k=k, drop=drop):
            return (-0.22 * math.sin(math.pi * u) * math.sin(math.pi * v)
                    - drop * u * v)
        cl = M.sheet(w * 0.99, reach, hf, nx=8, nz=7,
                     mat=["canvas_slate", "canvas_plain", "canvas_slate"][k],
                     plane="xz")
        cl.rotate_x(-0.16)
        cl.rotate_y(-theta)
        cl.translate(cx, eaves + 0.18, cz)
        g.add(cl)

    # Six trestles and their benches, in two ranks, none of them square to the
    # wall because they get pushed about all day.
    for i in range(6):
        a = -hw + 1.1 + (i % 3) * (hw * 2 - 2.2) / 2
        b = -hd - 1.5 - (i // 3) * 1.95
        x, z = L(a + float(rng.uniform(-0.25, 0.25)),
                 b + float(rng.uniform(-0.2, 0.2)))
        gy = float(T.height(x, z))
        yaw = -theta + float(rng.uniform(-0.16, 0.16))
        t = PR.trestle_table(f"{AID}.trestle.{i}", length=1.85, width=0.72)
        t.rotate_y(yaw)
        t.translate(x, gy, z)
        g.add(t)
        for sb in (-1, 1):
            bn = K.bench(f"{AID}.bench.{i}.{sb}", length=1.75)
            bn.rotate_y(yaw + float(rng.uniform(-0.09, 0.09)))
            bn.translate(x - math.sin(yaw) * sb * 0.72,
                         gy, z - math.cos(yaw) * sb * 0.72)
            g.add(bn)
        # What is on the table: last night, half cleared.
        if i % 3 != 1:
            g.add(PR.meal(f"{AID}.meal.{i}").rotate_y(yaw).translate(x, gy, z))
        for k in range(int(rng.integers(0, 3))):
            mg = PR.mug(f"{AID}.mug.{i}.{k}", full=bool(rng.random() < 0.4))
            mg.translate(x + float(rng.uniform(-0.6, 0.6)), gy + 0.74,
                         z + float(rng.uniform(-0.25, 0.25)))
            g.add(mg)
        if i == 4:
            ch = PR.chair(f"{AID}.cloak", cloak=True)
            ch.rotate_y(yaw + 1.1)
            ch.translate(x + 1.35, gy, z + 0.3)
            g.add(ch)


def _smoke_shed(ctx, g, plan, rng):
    """The smoke house behind: racks of split fish over a smother of oak dust.

    Doors ajar on purpose. A closed smoke house is a shed; an open one is the
    reason the venue exists, and it is the only place in Hearthmere where the
    player can see what a smell looks like.
    """
    fp = plan["footprint"]
    hw, hd = fp.half
    theta = fp.theta
    cx, cz = fp.world(hw * 0.15, hd + 3.1)
    gy = float(T.height(cx, cz))
    w, d, h = 4.2, 3.4, 2.75

    shed = M.Group()
    # Rubble to a metre, boarded above, because the fire is inside it.
    shed.add(M.box(w + 0.2, 1.05, d + 0.2, 0.03, "stone")
             .translate(0, 0.525, 0))
    for sx, sz in ((0, 1), (-1, 0), (1, 0)):
        n = int(((w if sz else d) - 0.1) / 0.24)
        for i in range(n):
            t = -0.5 + (i + 0.5) / n
            b = M.box(0.245, h - 1.0, 0.032, 0.005, "timber_charred")
            b.rotate_z(float(rng.uniform(-0.008, 0.008)))
            if sz:
                b.translate(t * w, 1.05 + (h - 1.0) * 0.5, sz * d * 0.5)
            else:
                b.rotate_y(math.pi * 0.5)
                b.translate(sx * w * 0.5, 1.05 + (h - 1.0) * 0.5, t * d)
            shed.add(b)
    # The doors, ajar, on the lane side.
    for sx, ang in ((-1, 0.95), (1, 0.35)):
        leaf = K.plank_door(f"{AID}.smoke{sx}", width=0.85, height=2.0,
                            mat="timber_charred", open_angle=ang)
        leaf.translate(sx * 0.44, 0.0, -d * 0.5 - 0.03)
        shed.add(leaf)
    for sx in (-1, 1):
        j = M.box(0.16, 2.15, 0.34, 0.012, "oak_dark")
        j.translate(sx * 0.95, 1.07, -d * 0.5)
        shed.add(j)
    lin = M.plank(2.2, 0.22, 0.34, 0.010, "oak_dark")
    lin.translate(0, 2.20, -d * 0.5)
    shed.add(lin)
    # Inside: three rails of split fish over the smother, and the smother
    # itself — a heap of oak dust with one dull red eye in it.
    for k in range(3):
        rail = M.cylinder(0.038, w - 0.5, 6, 0.005, "timber_charred")
        rail.rotate_z(math.pi * 0.5)
        rail.translate(0, 1.55 + k * 0.42, -0.55 + k * 0.55)
        shed.add(rail)
        for i in range(9):
            x = -w * 0.5 + 0.4 + i * (w - 0.8) / 8
            ln = float(rng.uniform(0.26, 0.36))
            f = M.prism([(0.0, 0.0), (0.075, -ln * 0.30), (0.05, -ln),
                         (-0.05, -ln), (-0.075, -ln * 0.30)],
                        0.026, "fish", chamfer=0.004, uv_scale=MATS.uv_detail("fish", 0.417, why="0.03 m member; the library's 1 m tile shows 3% of one tile here and reads as flat colour"))
            f.rotate_y(float(rng.uniform(-0.2, 0.2)))
            f.translate(x, 1.53 + k * 0.42, -0.55 + k * 0.55)
            shed.add(f)
    for i in range(26):
        c = M.box(float(rng.uniform(0.05, 0.11)), float(rng.uniform(0.03, 0.07)),
                  float(rng.uniform(0.05, 0.10)), 0.01,
                  "coal" if i < 3 else "cinder")
        c.rotate_y(float(rng.uniform(0, 3.14)))
        c.translate(float(rng.uniform(-0.7, 0.7)), 0.06 + float(rng.uniform(0, 0.10)),
                    float(rng.uniform(-0.6, 0.6)))
        shed.add(c)
    # Roof: a shallow pyramid with a louvred cowl, because smoke has to leave
    # slowly. The cowl is the shed's whole silhouette.
    for sz in (-1, 1):
        sl = M.box(w + 0.8, 0.13, (d + 0.8) * 0.62, 0.02, "terracotta")
        sl.rotate_x(sz * 0.62)
        sl.translate(0, h + 0.42, sz * (d + 0.8) * 0.24)
        shed.add(sl)
    for sx in (-1, 1):
        gb = M.prism([(-(d + 0.8) * 0.5, 0.0), ((d + 0.8) * 0.5, 0.0),
                      (0.0, (d + 0.8) * 0.5 * 0.72)], 0.12, "timber_charred",
                     chamfer=0.008, uv_scale=MATS.uv_detail("timber_charred", 1.11, why="0.12 m member; the library's 2 m tile shows 6% of one tile here and reads as flat colour"))
        gb.rotate_y(math.pi * 0.5)
        gb.translate(sx * (w * 0.5 + 0.03), h, 0.0)
        shed.add(gb)
    cowl = M.Group()
    for k in range(4):
        lv = M.box(1.15, 0.10, 0.06, 0.008, "timber_charred")
        lv.rotate_x(0.42)
        lv.translate(0, 0.18 + k * 0.20, 0.44)
        cowl.add(lv)
        lv2 = M.box(1.15, 0.10, 0.06, 0.008, "timber_charred")
        lv2.rotate_x(-0.42)
        lv2.translate(0, 0.18 + k * 0.20, -0.44)
        cowl.add(lv2)
    for sx in (-1, 1):
        p = M.box(0.10, 1.05, 0.95, 0.008, "timber_charred")
        p.translate(sx * 0.58, 0.52, 0)
        cowl.add(p)
    cap = M.box(1.55, 0.14, 1.35, 0.02, "terracotta")
    cap.translate(0, 1.12, 0)
    cowl.add(cap)
    cowl.translate(0, h + 1.05, 0)
    shed.add(cowl)

    shed.rotate_y(-theta)
    shed.translate(cx, gy, cz)
    g.add(shed)
    ctx.collider("box", center=(cx, gy + h * 0.5, cz),
                 half=(w * 0.5 + 0.1, h * 0.5, d * 0.5 + 0.1), rot_y=-theta,
                 tag="smoke_shed")
    ctx.entity(f"{AID}.smokehouse.01", "prop.smokehouse", (cx, gy, cz),
               cell="H3", verbs=["inspect"],
               smoke={"rate": 0.9, "drift": [0.8, 0, 0.5]},
               light={"color": "#C4531F", "intensity": 1.2, "range": 4.0,
                      "flickerHz": [5, 9]})
    _ = hd


def _wet_end(ctx, g, plan, rng):
    """Gutting boards, the brine tubs and the trimmings barrel. Workflow order.

    Everything here is placed by the job: the boards nearest the lane where the
    baskets come off the wharf, the brine tubs behind them, and the trimmings
    barrel where a man can drop into it without turning round.
    """
    fp = plan["footprint"]
    hw, hd = fp.half
    theta = fp.theta

    def L(a, b):
        return fp.world(a, b)

    x, z = L(-hw - 1.5, -hd - 1.2)
    gy = float(T.height(x, z))
    kit = PR.fishmonger_kit(f"{AID}.boards")
    kit.rotate_y(-theta + 0.4)
    kit.translate(x, gy, z)
    g.add(kit)
    for k in range(2):
        tx, tz = L(-hw - 1.9 - k * 0.05, -hd + 0.5 + k * 1.25)
        ty = float(T.height(tx, tz))
        tub = M.lathe([(0.46, 0.0), (0.52, 0.62), (0.50, 0.68)], 14,
                      "oak_weathered", close_top=False)
        tub.translate(tx, ty, tz)
        g.add(tub)
        for h in (0.12, 0.52):
            hp = M.ring(0.50 + h * 0.03, 0.055, "iron_pitted", segments=14)
            hp.translate(tx, ty + h, tz)
            g.add(hp)
        br = M.lathe([(0.0, 0.0), (0.475, 0.0)], 14, "water",
                     close_bottom=False, close_top=False)
        br.translate(tx, ty + 0.50, tz)
        g.add(br)
    bx, bz = L(-hw - 1.2, -hd - 2.5)
    by = float(T.height(bx, bz))
    bar = K.barrel(f"{AID}.trimmings", height=0.80, belly=0.62)
    bar.translate(bx, by, bz)
    g.add(bar)
    g.add(PR.spill(f"{AID}.scales", kind="grain", radius=0.9, centre=(bx, bz),
                   vessel=False).translate(0, by, 0))
    cat = PR.worn_patch(f"{AID}.cat", shape="cat", size=0.5, mat="grass_worn")
    cat.translate(bx + 0.9, by, bz - 0.5)
    g.add(cat)
    # Baskets stacked where they were emptied, and a yoke against the wall.
    for k in range(4):
        bk = PR.basket(f"{AID}.basket.{k}", radius=0.26, height=0.30)
        px, pz = L(hw - 0.9 - k * 0.1, -hd - 0.55 - k * 0.02)
        bk.rotate_y(float(rng.uniform(0, 3.1)))
        bk.translate(px, float(T.height(px, pz)) + k * 0.29, pz)
        g.add(bk)
    yx, yz = L(hw + 0.4, -hd - 0.35)
    yk = PR.yoke_and_buckets(f"{AID}.yoke", mode="down")
    yk.rotate_y(-theta)
    yk.translate(yx, float(T.height(yx, yz)), yz)
    g.add(yk)


def build(ctx: VenueContext):
    doc = json.load(open(TOWN, encoding="utf-8"))
    slot = {s["id"]: s for s in doc["buildingSlots"]}[SLOT]
    rng = rng_for(AID, "eatery")

    plan = BLD.plan_building(slot, STYLE, AID)
    BLD.build_building(ctx, slot, STYLE, AID, plan=plan)

    g = M.Group()
    _awning(g, plan, rng)
    _smoke_shed(ctx, g, plan, rng)
    _wet_end(ctx, g, plan, rng)

    # The serving hatch: shutters folded down into a counter on the lane, with
    # the day's pot on it. This is the transaction the venue is for.
    fp = plan["footprint"]
    hw, hd = fp.half
    fy = plan["floor_y"]
    theta = fp.theta
    cx, cz = fp.world(hw * 0.30, -hd - 0.42)
    cnt = M.Group()
    top = M.plank(2.5, 0.72, 0.075, 0.008, "oak_weathered")
    top.translate(0, 1.05, 0)
    cnt.add(top)
    for sx in (-1, 1):
        br = M.plank(0.75, 0.09, 0.08, 0.006, "iron_pitted")
        br.rotate_z(-0.9 * sx)
        br.translate(sx * 1.0, 0.72, 0.24)
        cnt.add(br)
    pot = M.lathe([(0.0, 0.0), (0.30, 0.06), (0.32, 0.30), (0.26, 0.36)], 14,
                  "iron_pitted", close_top=False)
    pot.translate(-0.5, 1.09, 0.0)
    cnt.add(pot)
    stew = M.lathe([(0.0, 0.0), (0.27, 0.0)], 12, "water",
                   close_bottom=False, close_top=False)
    stew.translate(-0.5, 1.39, 0.0)
    cnt.add(stew)
    for k in range(6):
        bw = M.lathe([(0.0, 0.0), (0.095, 0.045), (0.085, 0.06)], 10, "pottery")
        bw.translate(0.35 + (k % 3) * 0.22, 1.09 + (k // 3) * 0.06,
                     float(rng.uniform(-0.15, 0.15)))
        cnt.add(bw)
    cnt.rotate_y(-theta)
    cnt.translate(cx, fy, cz)
    g.add(cnt)
    ctx.entity(f"{AID}.counter.01", "vendor.fish_eatery", (cx, fy, cz),
               cell="H3", verbs=["talk", "buy"])

    ctx.emit(g)
