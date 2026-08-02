"""Warehouse row — the seven bulk-goods sheds, and what makes a waterfront
read as commercial rather than as a beach with a crane on it.

`review/reports/ad-town-02.md` §1 ranked these second only to the quay itself.
They are the buildings that explain the quay: nothing lands on a wharf to stay
there, so behind every working quay there is a wall of big simple masses with
loading doors at first floor, hoist beams over them, ramps up to their sills,
and goods stacked under tarpaulins wherever there was room.

Seven slots, all of them `kit: warehouse` in the schedule:

    58 tithe_barn    aisled, five bays, cart doors on both long sides
    59 warehouse_a   the carriers' bonded store, underpinned twice
    60 netloft       net loft over an open boat store
    62 warehouse_b   grain below, wool above
    63 warehouse_c   the same, its north wall stained by the leat
    67 ropehouse     24 x 5 m, because that is what laying rope needs
    80 malthouse     kiln cowl on the ridge

The masses come from `core.building` — same walls, same roofs, same party-wall
logic as the rest of the town, which is the only way seven sheds in four
quarters read as one settlement. What this module adds is the half that makes
them warehouses instead of large houses: the taking-in doors (now in
`core.building._loading_door`, so any warehouse-kit mass anywhere gets them),
the loading ramps and dock stones, and the goods.

They used to be built by `venues/townhouse.py` as anonymous filler. That is why
none of them had a loading door.
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
from core import streetscape as SS
from core import terrain as T
from core.mathx import rng_for
from core.venue import VenueContext, REPO
from core import materials as MATS

NAME = "warehouse"

TOWN = os.path.join(REPO, "content/town/hearthmere.json")

KIT = "warehouse"


def slots(town=None):
    doc = town or json.load(open(TOWN, encoding="utf-8"))
    return [s for s in doc.get("buildingSlots", []) if s.get("kit") == KIT]


CELLS = sorted({c for s in slots() for c in s.get("cells", [])})

# Per-slot overrides. The schedule's note is the brief; this is where a note
# that asks for something the generic style cannot give is answered.
STYLE = {
    # A tithe barn is not a warehouse: it is one enormous roof on a low wall,
    # and its whole character is that the roof is four fifths of the elevation.
    # half_hip, not gable: a barn of this date is jerkinheaded, and the gable
    # here was a workaround for the rafter-foot defect fixed in
    # core/mesh.py:spin_y, not a decision about barns.
    "hm.slot.58.tithe_barn": dict(
        walls=["rubble"], frame="square", roof="half_hip", roof_mat="thatch_old",
        pitch=(1.18, 1.26), jetty=0.0, plinth=(0.42, 0.55), windows=0.0,
        wealth=0.35, dormers=(0, 0), chimneys=0, shutters=False,
        storey_h=(5.0, 5.4), name="tithe_barn"),
    # The oldest timber frame in Hearthmere, and underpinned twice — so it is
    # timber over a tall stone underbuilding, not stone over timber.
    "hm.slot.59.warehouse_a": dict(
        walls=["rubble", "timber", "timber"], frame="close", roof="gable",
        roof_mat="terracotta", pitch=(0.82, 0.92), jetty=0.30,
        plinth=(0.70, 0.88), windows=0.8, wealth=0.45, dormers=(0, 0),
        chimneys=0, shutters=False, loading_door=True, storey_h=(3.05, 3.35),
        name="bonded_store"),
    "hm.slot.67.ropehouse": dict(
        walls=["timber"], frame="square", roof="gable", roof_mat="thatch_old",
        pitch=(1.02, 1.10), jetty=0.0, plinth=(0.30, 0.40), windows=0.4,
        wealth=0.2, dormers=(0, 0), chimneys=0, shutters=False,
        storey_h=(3.5, 3.9), name="rope_walk"),
}


# ---------------------------------------------------------------------------
# Shared warehouse dressing
# ---------------------------------------------------------------------------

def _front(plan):
    """(mid, ex, out_n, ln) of the frontage, and a local->world helper."""
    fr = plan.get("front_run")
    if fr is None:
        fp = plan["footprint"]
        hw, hd = fp.half
        mid = fp.world(0.0, -hd)
        ex = fp.U
        out_n = (-fp.V[0], -fp.V[1])
        fr = (np.asarray(mid, float), np.asarray(ex, float),
              np.asarray(out_n, float), fp.w)
    mid, ex, out_n, ln = fr

    def L(a, b):
        return (float(mid[0] + ex[0] * a + out_n[0] * b),
                float(mid[1] + ex[1] * a + out_n[1] * b))
    return mid, ex, out_n, ln, L


def _dock(ctx, g, plan, aid, rng):
    """The loading dock: a stone bank at cart-bed height under the door.

    A warehouse door that a cart cannot reach is the same defect as a first
    floor door with no hoist. `props.WHEEL_DIA` puts a waggon bed at 1.02 m, so
    the dock is built to that and the ramp climbs to it at 1:6.
    """
    _mid, _ex, out_n, ln, L = _front(plan)
    yaw = math.atan2(-out_n[0], -out_n[1])
    fy = plan["floor_y"]
    a0 = float(rng.uniform(-0.16, 0.16)) * ln
    w = min(4.2, ln * 0.5)
    gx, gz = L(a0, 1.05)
    gy = float(T.height(gx, gz))
    rise = max(0.0, fy - gy)
    if rise < 0.12:
        return
    # The bank itself, standing off the wall so the dock is a platform.
    depth = 1.9
    bank = M.box(w, rise + 0.10, depth, 0.03, "stone")
    bank.rotate_y(yaw)
    bx, bz = L(a0, depth * 0.5 + 0.05)
    bank.translate(bx, fy - (rise + 0.10) * 0.5, bz)
    g.add(bank)
    # Ramp up the side of the dock, at a grade a laden hand-cart can be pushed.
    run = max(1.4, rise * 6.0)
    side = 1.0 if rng.random() < 0.5 else -1.0
    n = 6
    for i in range(n):
        t0, t1 = i / n, (i + 1) / n
        y0 = gy + rise * t0
        y1 = gy + rise * t1
        seg = M.box(run / n * 1.04, (y0 + y1) * 0.5 - gy + 0.10, 1.5, 0.02,
                    "stone")
        seg.rotate_y(yaw)
        rx, rz = L(a0 + side * (w * 0.5 + run * (1.0 - (t0 + t1) * 0.5)),
                   depth * 0.5 + 0.05)
        seg.translate(rx, ((y0 + y1) * 0.5 + gy) * 0.5 - 0.05, rz)
        g.add(seg)
    # Dock stones: the kerbs a cart wheel grinds against, scored and chipped.
    for sx in (-1, 1):
        st = SS.spur_stone(f"{aid}.spur{sx}", height=0.58)
        px, pz = L(a0 + sx * (w * 0.5 + 0.30), depth + 0.30)
        st.rotate_y(yaw + float(rng.uniform(-0.1, 0.1)))
        st.translate(px, float(T.height(px, pz)), pz)
        g.add(st)
    ctx.collider("box", center=(bx, fy - rise * 0.5, bz),
                 half=(w * 0.5, rise * 0.5, depth * 0.5), rot_y=yaw,
                 kind="surface", tag="loading_dock")


def _goods(ctx, g, plan, aid, rng, n_stacks=3):
    """Goods landed and not yet in: crates, casks and bales under tarpaulin.

    Against the wall and never in the middle, because the middle is where the
    cart turns — the same circulation rule `props.dress_yard` is built on.
    """
    _mid, _ex, out_n, ln, L = _front(plan)
    yaw = math.atan2(-out_n[0], -out_n[1])
    for i in range(n_stacks):
        a = (-0.42 + 0.84 * (i + 0.5) / n_stacks) * ln + float(rng.uniform(-0.6, 0.6))
        b = float(rng.uniform(0.55, 1.5))
        x, z = L(a, b)
        y = float(T.height(x, z))
        pick = float(rng.random())
        if pick < 0.4:
            it = PR.crate_stack(f"{aid}.crates.{i}", count=int(rng.integers(2, 5)))
        elif pick < 0.72:
            it = PR.sack_stack(f"{aid}.sacks.{i}", count=int(rng.integers(3, 6)))
        else:
            it = M.Group()
            for k in range(int(rng.integers(3, 6))):
                bl = K.barrel(f"{aid}.cask.{i}.{k}")
                bl.rotate_y(float(rng.uniform(0, 3.14)))
                bl.translate(float(rng.uniform(-0.7, 0.7)), 0.0,
                             float(rng.uniform(-0.5, 0.5)))
                it.add(bl)
        it.rotate_y(yaw + float(rng.uniform(-0.5, 0.5)))
        it.translate(x, y, z)
        g.add(it)
        # Half of them keep the rain off. A tarpaulin over a pile is the single
        # most legible "bonded goods" cue there is.
        if rng.random() < 0.55:
            lo, hi = it.bounds()
            w = float(hi[0] - lo[0]) + 0.5
            d = float(hi[2] - lo[2]) + 0.5
            top = float(hi[1])
            tarp = M.sheet(w, d, lambda u, v: -0.16 * ((u - 0.5) ** 2 +
                                                       (v - 0.5) ** 2) * 4.0,
                           nx=7, nz=6,
                           mat=["canvas_slate", "canvas_plain", "sacking"][i % 3],
                           plane="xz")
            tarp.translate(float((lo[0] + hi[0]) * 0.5), top + 0.06,
                           float((lo[2] + hi[2]) * 0.5))
            g.add(tarp)
            for k in range(3):
                st = M.box(0.16, 0.10, 0.14, 0.02, "stone", uv_scale=MATS.uv_detail("stone", 0.25, why="0.16 m member; the library's 2 m tile shows 8% of one tile here and reads as flat colour"))
                st.translate(float(lo[0]) + w * (k + 0.5) / 3.0, top + 0.10,
                             float(rng.choice([lo[2], hi[2]])))
                g.add(st)
    # Tally sticks by the door — the pictorial record (Art Bible §2: no
    # readable lettering, so the account is notches on hazel).
    x, z = L(-0.3 * ln, 0.28)
    for k in range(5):
        ts = M.cylinder(0.014, float(rng.uniform(0.32, 0.46)), 5, 0.002,
                        "timber_grey")
        ts.rotate_z(float(rng.uniform(-0.25, 0.25)))
        ts.rotate_y(float(rng.uniform(0, 3.14)))
        ts.translate(x + float(rng.uniform(-0.2, 0.2)),
                     float(T.height(x, z)) + 0.02,
                     z + float(rng.uniform(-0.2, 0.2)))
        g.add(ts)


# ---------------------------------------------------------------------------
# Per-slot character
# ---------------------------------------------------------------------------

def _tithe_barn(ctx, g, plan, aid, rng):
    """Cart doors on both long sides with a threshing floor between them.

    The doors are the design: opposed, full height, and open, so the draught
    blows the chaff clear and so the player can see straight through the
    building. A barn read from outside with the doors shut is a shed.
    """
    fp = plan["footprint"]
    hw, hd = fp.half
    fy = plan["floor_y"]
    for sgn in (-1, 1):
        mid = fp.world(0.0, sgn * hd)
        out_n = (sgn * fp.V[0], sgn * fp.V[1])
        yaw = math.atan2(-out_n[0], -out_n[1])
        unit = M.Group()
        w, h = 3.6, 4.0
        for sx in (-1, 1):
            j = M.box(0.26, h + 0.3, 0.42, 0.016, "oak_dark")
            j.translate(sx * (w * 0.5 + 0.13), (h + 0.3) * 0.5, 0.0)
            unit.add(j)
        lin = M.plank(w + 0.7, 0.30, 0.42, 0.014, "oak_dark")
        lin.translate(0, h + 0.15, 0.0)
        unit.add(lin)
        for sx, ang in ((-1, 1.15), (1, 0.55)):
            leaf = K.plank_door(f"{aid}.cart{sgn}{sx}", width=w * 0.5, height=h,
                                mat="oak_weathered", open_angle=ang * sgn)
            leaf.translate(sx * w * 0.25, 0.0, 0.0)
            unit.add(leaf)
        M.place(unit, np.array([mid[0], fy, mid[1]]),
                np.array([fp.U[0], 0.0, fp.U[1]]), np.array([0.0, 1.0, 0.0]),
                np.array([-out_n[0], 0.0, -out_n[1]]))
        g.add(unit)
        _ = yaw
    # Aisle posts on padstones, visible through the open doors, and the boarded
    # threshing floor between them worn pale by two centuries of flails.
    for i in range(4):
        for sx in (-1, 1):
            a = -hw + (i + 0.5) * (hw * 2.0 / 4)
            x, z = fp.world(a, sx * hd * 0.45)
            pad = M.box(0.52, 0.22, 0.52, 0.02, "stone", uv_scale=MATS.uv_detail("stone", 0.5, why="0.52 m member; the library's 2 m tile shows 26% of one tile here and reads as flat colour"))
            pad.rotate_y(-fp.theta)
            pad.translate(x, fy + 0.11, z)
            g.add(pad)
            p = M.box(0.26, 4.4, 0.26, 0.014, "oak_dark")
            p.rotate_y(-fp.theta)
            p.translate(x, fy + 2.42, z)
            g.add(p)
    fl = M.box(hw * 1.5, 0.06, hd * 1.4, 0.01, "oak_weathered")
    fl.rotate_y(-fp.theta)
    fl.translate(fp.centre[0], fy + 0.04, fp.centre[1])
    g.add(fl)
    x, z = fp.world(0.6, -hd - 1.1)
    g.add(PR.spill(f"{aid}.chaff", kind="grain", radius=1.15,
                   centre=(x, z)).translate(0, float(T.height(x, z)), 0))
    for k in range(3):
        a = float(rng.uniform(-hw * 0.7, hw * 0.7))
        x, z = fp.world(a, -hd - float(rng.uniform(0.5, 1.6)))
        fk = M.Group()
        sh = M.cylinder(0.028, 1.75, 5, 0.004, "oak_weathered")
        fk.add(sh)
        for t in range(3):
            tn = M.cylinder(0.014, 0.55, 4, 0.002, "oak_weathered")
            tn.rotate_z(0.14 * (t - 1))
            tn.translate((t - 1) * 0.10, 1.72, 0)
            fk.add(tn)
        fk.rotate_z(1.30)
        fk.rotate_y(float(rng.uniform(0, 6.2)))
        fk.translate(x, float(T.height(x, z)) + 0.1, z)
        g.add(fk)


def _rope_walk(ctx, g, plan, aid, rng):
    """The rope house: 24 m of open-sided shed with rope actually laid in it.

    Its plan shape is the point — nothing else in Hearthmere is 24 x 5 — and
    the way to prove the shape is what it is for is to show the work: the
    spinning jack at one end, the sledge at the other, hemp on the wall, and
    four yarns stretched the whole length at hand height.
    """
    fp = plan["footprint"]
    hw, hd = fp.half
    fy = plan["floor_y"]

    def L(a, b, y=0.0):
        x, z = fp.world(a, b)
        return (x, fy + y, z)

    # Four yarns down the walk on top stakes, twisted at one end.
    for k in range(4):
        b = -0.45 + k * 0.30
        g.add(M.tube(L(-hw + 0.6, b, 1.02), L(hw - 0.6, b, 1.02), 0.020,
                     "sacking", segments=4))
    for i in range(7):
        a = -hw + 0.9 + i * (hw * 2 - 1.8) / 6
        x, z = fp.world(a, 0.0)
        st = M.box(0.10, 1.15, 0.10, 0.008, "timber_grey")
        st.rotate_y(-fp.theta)
        st.translate(x, fy + 0.575, z)
        g.add(st)
        top = M.plank(1.0, 0.09, 0.08, 0.006, "timber_grey", grain_axis=1)
        top.rotate_y(-fp.theta + math.pi * 0.5)
        top.translate(x, fy + 1.15, z)
        g.add(top)
    # The spinning jack: a wheel on a frame with three whorls, hand-cranked.
    jx, jy, jz = L(-hw + 0.5, 0.9)
    jack = M.Group()
    for sz in (-1, 1):
        p = M.box(0.16, 1.45, 0.16, 0.010, "oak_dark")
        p.translate(0, 0.725, sz * 0.45)
        jack.add(p)
    wh = M.lathe([(0.0, 0), (0.62, 0), (0.62, 0.05), (0.0, 0.05)], 18, "oak_weathered")
    wh.rotate_z(math.pi * 0.5)
    wh.translate(0, 1.10, 0)
    jack.add(wh)
    for k in range(8):
        a = k / 8 * 2 * math.pi
        sp = M.box(0.05, 1.20, 0.05, 0.005, "oak_dark")
        sp.rotate_x(a)
        sp.translate(0, 1.10, 0)
        jack.add(sp)
    cr = M.cylinder(0.035, 0.42, 6, 0.005, "iron_pitted")
    cr.rotate_z(math.pi * 0.5)
    cr.translate(0.34, 1.10, 0)
    jack.add(cr)
    jack.rotate_y(-fp.theta)
    jack.translate(jx, jy, jz)
    g.add(jack)
    # Hemp: dressed bundles on the wall, and the tow that came off them.
    for i in range(5):
        a = -hw + 3.5 + i * 1.5
        x, z = fp.world(a, hd - 0.35)
        bn = M.Group()
        for k in range(7):
            f = M.cylinder(0.022, float(rng.uniform(0.9, 1.25)), 4, 0.002,
                           "straw")
            f.rotate_z(float(rng.uniform(-0.10, 0.10)))
            f.translate(float(rng.uniform(-0.09, 0.09)), 0,
                        float(rng.uniform(-0.06, 0.06)))
            bn.add(f)
        bn.rotate_z(0.16)
        bn.rotate_y(-fp.theta + float(rng.uniform(-0.3, 0.3)))
        bn.translate(x, fy, z)
        g.add(bn)
    for i in range(4):
        a = float(rng.uniform(-hw * 0.8, hw * 0.8))
        x, z = fp.world(a, float(rng.uniform(-hd - 1.0, -hd - 0.2)))
        cl = K.rope_coil(f"{aid}.coil.{i}", radius=float(rng.uniform(0.28, 0.40)))
        cl.translate(x, float(T.height(x, z)), z)
        g.add(cl)


def _net_loft(ctx, g, plan, aid, rng):
    """Net loft over an open boat store: tar barrel, floats, a half-mended net.

    The ground floor is open on the water side, so the boat store is a thing
    you can see into — which is the whole reason the building is worth its own
    treatment rather than another blind shed.
    """
    fp = plan["footprint"]
    hw, hd = fp.half
    fy = plan["floor_y"]
    _mid, _ex, out_n, ln, L = _front(plan)
    yaw = math.atan2(-out_n[0], -out_n[1])

    # An upturned punt on trestles under the loft, and a half-mended net over it.
    x, z = L(-0.2 * ln, 1.6)
    gy = float(T.height(x, z))
    for sx in (-1, 1):
        tr = M.Group()
        for sz in (-1, 1):
            lg = M.box(0.09, 0.72, 0.09, 0.008, "timber_grey")
            lg.rotate_x(sz * 0.16)
            lg.translate(0, 0.36, sz * 0.28)
            tr.add(lg)
        tp = M.plank(0.95, 0.10, 0.09, 0.006, "timber_grey")
        tp.translate(0, 0.74, 0)
        tr.add(tp)
        tr.rotate_y(yaw)
        px, pz = L(-0.2 * ln + sx * 1.5, 1.6)
        tr.translate(px, gy, pz)
        g.add(tr)
    boat = M.Group()
    hull = M.lathe([(0.0, 0.0), (0.72, 0.30), (0.80, 0.52), (0.0, 0.56)], 9,
                   "pine_tarred", close_top=False)
    hull.scale(1.0, 1.0, 4.4)
    boat.add(hull)
    boat.rotate_x(math.pi)
    boat.rotate_y(yaw + 1.57)
    boat.translate(x, gy + 1.30, z)
    g.add(boat)

    # Tar barrel on a fire ring, a float bag, and net needles on a board.
    tx, tz = L(0.34 * ln, 1.25)
    ty = float(T.height(tx, tz))
    tb = K.barrel(f"{aid}.tar", height=0.72, belly=0.56)
    tb.translate(tx, ty, tz)
    g.add(tb)
    lid = M.lathe([(0.0, 0.0), (0.30, 0.02)], 12, "pine_tarred")
    lid.translate(tx, ty + 0.73, tz)
    g.add(lid)
    for i in range(9):
        fx, fz = L(0.34 * ln + float(rng.uniform(-1.1, 1.1)),
                   1.25 + float(rng.uniform(-0.8, 0.8)))
        fl = M.globe(float(rng.uniform(0.10, 0.16)), "oak_weathered",
                     segments=7, rings=4, sy=0.78)
        fl.translate(fx, float(T.height(fx, fz)) + 0.12, fz)
        g.add(fl)
    _ = hd, hw, fy


def _malthouse(ctx, g, plan, aid, rng):
    """The kiln cowl on the ridge, and the flue it caps.

    A malt kiln is the only thing in Hearthmere with a moving part on its roof,
    and the cowl swinging into the wind is a silhouette nothing else gives.
    """
    fp = plan["footprint"]
    hw, _hd = fp.half
    ridge_y = plan.get("ridge_y", plan["plate_y"] + 2.0)
    x, z = fp.world(hw * 0.45, 0.0)
    stack = K.chimney(f"{aid}.kiln", height=1.9, section=1.10)
    stack.translate(x, ridge_y - 0.9, z)
    g.add(stack)
    cowl = M.Group()
    drum = M.lathe([(0.62, 0.0), (0.62, 0.95), (0.40, 1.22)], 12, "oak_weathered",
                   close_bottom=False, close_top=False)
    cowl.add(drum)
    vane = M.box(1.55, 0.90, 0.05, 0.01, "timber_grey")
    vane.translate(0.95, 0.62, 0)
    cowl.add(vane)
    cap = M.lathe([(0.70, 0.0), (0.0, 0.40)], 12, "lead", close_bottom=False)
    cap.translate(0, 1.20, 0)
    cowl.add(cap)
    cowl.rotate_y(0.7)
    cowl.translate(x, ridge_y + 1.15, z)
    g.add(cowl)
    ctx.entity(f"{aid}.cowl", "prop.kiln_cowl", (x, ridge_y + 1.15, z),
               verbs=["inspect"], smoke={"rate": 0.35, "drift": [0.8, 0, 0.5]})


def _stain(ctx, g, plan, aid, rng):
    """Slot 63: 'its north wall is stained to head height by the leat'.

    A wet-line on a wall is a decal that costs nothing and says two hundred
    years. Built as a thin algae panel against the wall face rather than as a
    tint, so it has a broken top edge (Art Bible §7 residue over polish).
    """
    fp = plan["footprint"]
    hw, hd = fp.half
    fy = plan["floor_y"]
    mid = fp.world(0.0, hd)
    n = (fp.V[0], fp.V[1])
    for k in range(9):
        a = -hw + 0.4 + k * (hw * 2 - 0.8) / 8
        x, z = fp.world(a, hd)
        h = 1.05 + 0.55 * math.sin(k * 1.7) * 0.5
        panel = M.box((hw * 2 - 0.8) / 8 * 1.05, h, 0.035, 0.006, "algae")
        panel.rotate_y(-fp.theta)
        panel.translate(x + n[0] * 0.03, fy - plan["plinth_h"] + h * 0.5,
                        z + n[1] * 0.03)
        g.add(panel)
    _ = (mid, aid, ctx, rng)


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

EXTRA = {
    "hm.slot.58.tithe_barn": _tithe_barn,
    "hm.slot.67.ropehouse": _rope_walk,
    "hm.slot.60.netloft": _net_loft,
    "hm.slot.80.malthouse": _malthouse,
    "hm.slot.63.warehouse_c": _stain,
}


def build(ctx: VenueContext):
    rows = slots()
    plans = {}
    for s in rows:
        st = STYLE.get(s["id"])
        plans[s["id"]] = BLD.plan_building(s, st, s["id"])

    stats = []
    for s in rows:
        aid = s["id"]
        plan = plans[aid]
        rng = rng_for(aid, "warehouse")
        before = ctx._tri_total
        BLD.build_building(ctx, s, STYLE.get(aid), aid, plan=plan)

        g = M.Group()
        if plan.get("loading"):
            _dock(ctx, g, plan, aid, rng)
        _goods(ctx, g, plan, aid, rng,
               n_stacks=2 if s.get("storeys", 1) < 2 else 3)
        fn = EXTRA.get(aid)
        if fn is not None:
            fn(ctx, g, plan, aid, rng)
        ctx.emit(g)
        stats.append((aid, plan["style"]["name"], ctx._tri_total - before,
                      plan["ridge_y"]))
        ctx.entity(f"{aid}.store", "container.warehouse",
                   (plan["footprint"].centre[0], plan["floor_y"],
                    plan["footprint"].centre[1]),
                   cell=(s.get("cells") or ["I4"])[0], verbs=["inspect"])

    print(f"      {len(stats)} sheds, "
          f"{sum(t for _i, _s, t, _r in stats):,} tris")
    for i, st, t, ry in stats:
        print(f"        {i:<26s} {st:<16s} {t:6,d} tris  ridge {ry:6.2f}")
