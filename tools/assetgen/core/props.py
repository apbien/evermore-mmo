"""Residue — the props that prove somebody works here.

Art Bible §7: *"Residue is the highest-value detail per unit of effort. A
perfectly modelled empty room reads as dead. A modest room with a stool knocked
over and tools mid-task reads as inhabited."* This module is that sentence,
made buildable. `core/kit.py` owns how Hearthmere is CONSTRUCTED — walls,
roofs, openings, the handful of props architecture implies. This owns what is
LEFT LYING ABOUT, which is a different and much larger vocabulary, and it grew
past the point where it belonged in the same file.

Everything here is re-exported through `core.kit` as well, so a venue author has
one import for the whole vocabulary and never has to guess which file a barrel
lives in.

## The five rules that make an arrangement read as real

1. **Nothing is centred, nothing is axis-aligned, nothing is in a neat row.**
   Every builder jitters position, yaw and scale from its own seed. A row of
   identical barrels at 90° is the single loudest "this was generated" tell.

2. **Every arrangement answers "who put this here and what were they doing".**
   That is why the tool sets are grouped by TRADE and ordered by WORKFLOW
   rather than by size — a cooper's croze sits on the block beside the
   raising-up because that is the next cut, not because it is the next-biggest
   tool.

3. **Stacked and leaning things are physically stable, and the support is
   shown.** `lean()` computes the tilt that puts an object's top ON a named
   wall plane rather than near it; `stack()` places each layer on the measured
   top of the one below. A floating or interpenetrating prop is worse than no
   prop, because the eye finds it instantly and then distrusts everything else
   in the frame.

4. **Dressing functions, not just objects.** `dress_workbench`, `dress_yard`,
   `dress_shopfront`, `dress_threshold`, `spill`, `stack_against_wall` give a
   venue author a convincing arrangement in one call. This is the part that
   actually determines cohesion: thirty venues each hand-placing their own
   clutter produce thirty visual languages, and no review pass can unpick that
   afterwards.

5. **One Group per arrangement, so one draw call per material.** Every builder
   returns a `mesh.Group`, and `ctx.emit(group)` merges it per material into
   the cell batch. Never emit props one at a time — that cost the streets venue
   1,344 draw calls. For anything repeated more than a dozen times across a
   venue use `ctx.instance(mesh_id, proto, transforms)`; `PROTOTYPES` below
   names the props worth instancing and their canonical mesh ids. Materials are
   chosen from the `kit_props` / `kit_trim` atlas sets wherever the object
   allows, so `atlas.pack_eligible()` collapses a dressed yard from eleven
   draw calls to three.

## Authoring convention

- `asset_id` is always the first argument and is the only source of randomness.
- Local origin is the object's **ground contact**, centred in plan, except
  where an object is defined by its attachment (a wheel is hub-centred, a wall
  fitting is at its fixing point). Every docstring says which.
- The principal face looks **-Z**, matching the kit and the render rig.
- A wall to lean against is the plane **z = 0 with its face toward -Z**, so
  objects stand at negative z and tip back. `stack_against_wall` and the
  `dress_*` functions all use that frame; rotate the result into place.
- Chamfers: `CH_PROP` (8 mm) for furniture and containers, `CH_SMALL` (3 mm)
  for handheld and small metal. Art Bible §6.
- Scale comes from the Art Bible §3 table. Where the table is silent the
  dimension is in the docstring so review can check it against a real object.
"""

from __future__ import annotations

import numpy as np

from . import mesh as M
from .mathx import rng_for, jitter
from . import materials as MATS

# Art Bible §6 chamfer classes. Never write a bare number in a builder.
CH_PROP = 0.008
CH_SMALL = 0.003

# Art Bible §3, plus the dimensions the table does not carry but which every
# builder here has to agree on or the town loses its sense of size.
WHEEL_DIA = 1.15        # §3 — cart wheel
TABLE_H = 0.74          # §3
BENCH_H = 0.45          # §3
COUNTER_H = 1.05        # §3
STALL_H = 0.90          # §3
BARREL_H, BARREL_D = 0.88, 0.62     # §3
CRATE = 0.55            # §3
BUCKET_H = 0.30         # a two-gallon coopered bucket
SACK_H = 0.55           # a full grain sack standing

# Props worth a GPU instance batch, with the mesh id every venue must use for
# them. Sharing the id is the whole point: two venues that both call their
# barrels "barrel" get one batch across the town, and two that invent their own
# names get two. `ctx.instance` folds a batch back into the cell geometry below
# twelve copies, so calling it is never a pessimisation.
PROTOTYPES = (
    "prop.barrel", "prop.crate", "prop.sack", "prop.bucket", "prop.basket",
    "prop.stool", "prop.amphora", "prop.jar", "prop.log", "prop.cobble",
    "prop.cart_wheel", "prop.rope_coil", "prop.beehive",
)


# ---------------------------------------------------------------------------
# Placement — the part that keeps arrangements physical
# ---------------------------------------------------------------------------

def lean(geom, length, foot_gap, wall_z=0.0, x=0.0, yaw=0.0, roll=0.0):
    """Tip a standing object back until its top rests ON the wall plane.

    The object is authored standing on `y = 0` with its top at `y = length`.
    Its foot stays `foot_gap` metres out from the wall; the tilt is then
    `asin(foot_gap / length)`, which is the angle at which the top touches
    `z = wall_z` exactly — not an eyeballed rotation that leaves a 4 cm gap or
    buries the tip 4 cm into the plaster.

    `roll` adds a little sideways lean, because nothing is ever set down square.
    Returns the geometry, moved into place.
    """
    L = max(float(length), 1e-3)
    g = float(np.clip(foot_gap, 0.0, L * 0.85))
    tilt = float(np.arcsin(g / L))
    if roll:
        geom.rotate_z(roll)
    geom.rotate_x(tilt)
    if yaw:
        geom.rotate_y(yaw)
    geom.translate(x, 0.0, wall_z - g)
    return geom


def stack(items, x=0.0, z=0.0, jitter_xz=0.02, yaw_spread=0.35, rng=None):
    """Pile objects, each seated on the measured top of the one below.

    `items` are geometries authored with their base at `y = 0`. Nothing is
    placed at a guessed height: each layer is translated by the running top of
    the stack as measured from real bounds, so the pile cannot float or
    interpenetrate however the shapes vary. Small lateral jitter and yaw keep
    it from reading as a column.
    """
    out = M.Group()
    y = 0.0
    for it in items:
        if it is None:
            continue
        lo, hi = it.bounds()
        if yaw_spread and rng is not None:
            it.rotate_y(float(rng.uniform(-yaw_spread, yaw_spread)))
        dx = float(rng.uniform(-jitter_xz, jitter_xz)) if rng is not None else 0.0
        dz = float(rng.uniform(-jitter_xz, jitter_xz)) if rng is not None else 0.0
        it.translate(x + dx, y - float(lo[1]), z + dz)
        out.add(it)
        y += float(hi[1] - lo[1]) * 0.985      # settle: things bed into each other
    return out


def scatter(rng, count, rx, rz, power=0.65):
    """Positions in an ellipse, biased toward the centre. Spills, heaps, chips."""
    for _ in range(int(count)):
        a = float(rng.uniform(0.0, 2.0 * np.pi))
        d = float(rng.uniform(0.0, 1.0)) ** power
        yield np.cos(a) * d * rx, np.sin(a) * d * rz


def _yaw(rng, spread=np.pi):
    return float(rng.uniform(-spread, spread))


# ---------------------------------------------------------------------------
# Transport and haulage
# ---------------------------------------------------------------------------

def cart_wheel(asset_id, dia=WHEEL_DIA, width=0.085, spokes=12, dish=0.030,
               detail=1.0, missing=(), nave_mat="elm", spoke_mat="oak",
               felloe_mat="oak_weathered", tyre_mat="iron"):
    """A wheel built the way a wheelwright builds one. **Hub-centred origin.**

    Art Bible §3 gives 1.15 m. The construction is the point: a disc with lines
    scratched on it reads as a toy, and a wheel is the most-looked-at object on
    any cart because it is at eye level for a seated player camera.

    - **Nave** — the elm hub, barrelled, with iron bands shrunk on at each end.
      Elm because it does not split when twelve mortises are cut round it, and
      it is the one place in the town that timber reads as end grain.
    - **Spokes** — oak, tapered, and **dished**: they lean outboard so the wheel
      is a shallow cone. A dished wheel takes the sideways thrust of a road
      camber; a flat one is a modelling error a wheelwright would notice.
    - **Felloes** — the rim in six arc segments, each carrying two spokes, with
      the joints between them visible. A single turned annulus is wrong.
    - **Tyre** — one iron hoop, shrunk on hot. Not a bolted strake: Art Bible §2
      forbids the standardized fastener that would imply.

    `missing` omits spokes by index, which is how `broken_wheel` gets a real
    gap in the rhythm rather than a wheel that merely has fewer spokes.

    Local axes: the wheel lies in XY and rolls about Z; **+Z is outboard**.
    """
    rng = rng_for(asset_id, "wheel")
    out = M.Group()
    R = dia * 0.5
    seg = max(6, int(round(10 * detail)))

    # -- nave ---------------------------------------------------------------
    nl = width * 2.4
    nave = M.lathe([(0.055, -nl * 0.5), (0.105, -nl * 0.46), (0.115, -nl * 0.22),
                    (0.120, 0.0), (0.115, nl * 0.22), (0.105, nl * 0.46),
                    (0.055, nl * 0.5)], max(8, int(12 * detail)), nave_mat)
    nave.rotate_x(np.pi * 0.5)
    out.add(nave)
    for zz in (-nl * 0.40, nl * 0.40):
        out.add(M.ring(0.112, 0.030, tyre_mat, seg + 2).rotate_x(np.pi * 0.5).translate(0, 0, zz))

    # -- spokes -------------------------------------------------------------
    # Tenoned into the nave at r=0.10 and into the felloe at r=R-0.055. Each
    # leans `dish` outboard at the rim: that is the cone.
    nsp = int(spokes)
    gone = set(int(i) % nsp for i in missing)
    for i in range(nsp):
        if i in gone:
            continue
        a = 2.0 * np.pi * i / nsp + rng.uniform(-0.012, 0.012)
        r0, r1 = 0.10, R - 0.058
        p0 = (np.cos(a) * r0, np.sin(a) * r0, -dish * 0.15)
        p1 = (np.cos(a) * r1, np.sin(a) * r1, dish)
        sp = M.tube(p0, p1, 0.026 * rng.uniform(0.94, 1.06), spoke_mat,
                    max(4, int(6 * detail)), CH_SMALL)
        out.add(sp)
        # Shoulder where the spoke swells into the nave — the strongest section
        # of a spoke and the reason a wheel does not shear at the hub. It costs
        # as much as the spoke itself, so it is the first thing a waggon's four
        # wheels drop: at 3.5 m it is a 4 cm swelling behind a 12 cm nave band.
        if detail >= 0.9:
            sh = M.tube((np.cos(a) * 0.095, np.sin(a) * 0.095, -dish * 0.15),
                        (np.cos(a) * 0.20, np.sin(a) * 0.20, -dish * 0.02),
                        0.036, spoke_mat, max(4, int(6 * detail)), CH_SMALL)
            out.add(sh)

    # -- felloes ------------------------------------------------------------
    nfel = max(4, nsp // 2)
    span = 2.0 * np.pi / nfel
    ro, ri = R - 0.005, R - 0.062
    for i in range(nfel):
        a0 = i * span + 0.010                  # a real joint gap at each end
        a1 = (i + 1) * span - 0.010
        arc = []
        steps = max(3, int(4 * detail))
        for t in np.linspace(a0, a1, steps):
            arc.append((np.cos(t) * ro, np.sin(t) * ro))
        for t in np.linspace(a1, a0, steps):
            arc.append((np.cos(t) * ri, np.sin(t) * ri))
        fel = M.chamfered_prism(arc, width * rng.uniform(0.96, 1.04),
                                felloe_mat, CH_PROP)
        fel.translate(0, 0, dish * 0.92)
        out.add(fel)

    # -- tyre ---------------------------------------------------------------
    tyre = M.lathe([(R - 0.004, -width * 0.42), (R + 0.016, -width * 0.34),
                    (R + 0.016, width * 0.34), (R - 0.004, width * 0.42)],
                   max(14, int(28 * detail)), tyre_mat,
                   close_bottom=False, close_top=False)
    tyre.rotate_x(np.pi * 0.5)
    tyre.translate(0, 0, dish * 0.92)
    out.add(tyre)
    return out


def _axle(length, mat="oak_dark", r=0.055):
    ax = M.cylinder(r, length, 8, CH_SMALL, mat)
    ax.rotate_x(np.pi * 0.5)
    ax.translate(0, 0, 0)
    return ax


def _cart_bed(asset_id, length, width, mat="oak_weathered", planks=6,
              thickness=0.035):
    """A boarded load bed with a rail frame under it. Top at y = 0."""
    rng = rng_for(asset_id, "bed")
    out = M.Group()
    for i in range(planks):
        p = M.plank(length, width / planks * 0.96, thickness, CH_PROP, mat)
        p.rotate_z(rng.uniform(-0.004, 0.004))
        p.translate(0, -thickness * 0.5, -width * 0.5 + (i + 0.5) * width / planks)
        out.add(p)
    for sz in (-1, 1):
        r = M.plank(length * 1.01, 0.075, 0.070, CH_PROP, "oak_dark")
        r.translate(0, -thickness - 0.035, sz * (width * 0.5 - 0.05))
        out.add(r)
    for i in range(3):
        b = M.plank(width, 0.075, 0.065, CH_PROP, "oak_dark", grain_axis=1)
        b.rotate_y(np.pi * 0.5)
        b.translate(-length * 0.5 + (i + 0.5) * length / 3, -thickness - 0.035, 0)
        out.add(b)
    return out


def handcart(asset_id, length=1.55, width=0.86, wheel=0.92, tipped=False):
    """A two-wheel porter's cart, resting on its prop stick. Ground origin.

    The bed sits ABOVE the axle so the wheels clear it, and the shafts run out
    at a hand height a standing person could actually lift: 0.95 m at the grip.
    Standing empty it tips forward onto a prop stick, which is both what a real
    one does and the thing that proves it is not floating.
    """
    rng = rng_for(asset_id, "handcart")
    out = M.Group()
    R = wheel * 0.5
    bed_y = R + 0.10

    bed = _cart_bed(f"{asset_id}.bed", length, width)
    bed.translate(0, bed_y, 0)
    out.add(bed)

    # Sides and tail board — three boards a side, the top one sprung loose.
    for sz in (-1, 1):
        for k in range(3):
            h = 0.115
            b = M.plank(length * 0.98, h, 0.026, CH_PROP, "oak_weathered")
            b.rotate_x(0.06 * sz)
            b.rotate_z(rng.uniform(-0.005, 0.005) if k < 2 else 0.021)
            b.translate(0, bed_y + 0.04 + k * h, sz * (width * 0.5 - 0.02))
            out.add(b)
    tail = M.plank(width * 0.96, 0.30, 0.028, CH_PROP, "oak_weathered", grain_axis=1)
    tail.rotate_y(np.pi * 0.5)
    tail.translate(length * 0.5 - 0.02, bed_y + 0.14, 0)
    out.add(tail)

    # Shafts: two poles running forward from under the bed to the grips.
    for sz in (-1, 1):
        z = sz * (width * 0.5 - 0.12)
        sh = M.tube((-length * 0.5 + 0.05, bed_y - 0.05, z),
                    (-length * 0.5 - 0.72, 0.95, z), 0.032, "oak", 6, CH_SMALL)
        out.add(sh)
        grip = M.tube((-length * 0.5 - 0.72, 0.95, z),
                      (-length * 0.5 - 0.88, 0.96, z), 0.028, "oak_dark", 6, CH_SMALL)
        out.add(grip)

    # Axle and wheels.
    out.add(_axle(width + 0.34).translate(0, R, 0))
    for sz in (-1, 1):
        w = cart_wheel(f"{asset_id}.wheel.{sz}", dia=wheel, width=0.075,
                       spokes=10, detail=0.9)
        w.rotate_y(0 if sz > 0 else np.pi)
        w.translate(0, R, sz * (width * 0.5 + 0.09))
        out.add(w)

    # Prop stick under the nose — what it is actually standing on.
    prop_x = -length * 0.5 - 0.18
    st = M.tube((prop_x, bed_y - 0.06, 0.10), (prop_x + 0.16, 0.0, 0.13),
                0.028, "oak_weathered", 6, CH_SMALL)
    out.add(st)

    if tipped:
        out.rotate_z(-0.10)
    out.rotate_y(rng.uniform(-0.05, 0.05))
    return out


def waggon(asset_id, length=3.4, width=1.55, rear=1.30, front=0.98, load=None):
    """A four-wheel farm waggon. Ground origin, pole pointing -X.

    Real waggon logic, because every part of it is visible: the front wheels are
    smaller so they can turn under the bed on a swivelling fore-carriage, the
    bed is carried on a pair of longitudinal side rails, and the sides are open
    ladders rather than solid boards — which is what a hay or barrel waggon has
    and is far better in silhouette than a box on wheels.

    `load` ∈ {None, "barrels", "sacks", "timber", "hay"} dresses the bed.
    """
    rng = rng_for(asset_id, "waggon")
    out = M.Group()
    Rr, Rf = rear * 0.5, front * 0.5
    bed_y = Rr + 0.14

    bed = _cart_bed(f"{asset_id}.bed", length, width, planks=7)
    bed.translate(0, bed_y, 0)
    out.add(bed)

    # Ladder sides: uprights with two rails, raked outward.
    for sz in (-1, 1):
        z0 = sz * (width * 0.5 - 0.03)
        z1 = sz * (width * 0.5 + 0.20)
        for i in range(6):
            x = -length * 0.5 + (i + 0.5) * length / 6 + rng.uniform(-0.02, 0.02)
            up = M.tube((x, bed_y, z0), (x, bed_y + 0.60, z1), 0.034,
                        "oak_weathered", 5, CH_SMALL)
            out.add(up)
        for t, r in ((0.34, 0.36), (1.0, 0.6)):
            rail = M.plank(length * 0.99, 0.075, 0.040, CH_PROP, "oak_weathered")
            rail.translate(0, bed_y + t * 0.60,
                           sz * (width * 0.5 - 0.03 + t * 0.23))
            out.add(rail)

    # Head board and tail board.
    for sx, h in ((-1, 0.52), (1, 0.42)):
        for k in range(3):
            b = M.plank(width * 0.94, h / 3 * 0.92, 0.028, CH_PROP,
                        "oak_weathered", grain_axis=1)
            b.rotate_y(np.pi * 0.5)
            b.translate(sx * (length * 0.5 - 0.03),
                        bed_y + 0.05 + (k + 0.5) * h / 3, 0)
            out.add(b)

    # Chassis: side rails, rear axle bed, and the swivelling fore-carriage.
    for sz in (-1, 1):
        r = M.plank(length * 1.02, 0.10, 0.095, CH_PROP, "oak_dark")
        r.translate(0, bed_y - 0.13, sz * (width * 0.5 - 0.18))
        out.add(r)
    rear_x, front_x = length * 0.32, -length * 0.30
    for x, R in ((rear_x, Rr), (front_x, Rf)):
        blk = M.plank(width * 0.92, 0.14, 0.13, CH_PROP, "oak_dark", grain_axis=1)
        blk.rotate_y(np.pi * 0.5)
        blk.translate(x, R + 0.09, 0)
        out.add(blk)
        ax = _axle(width + 0.42)
        ax.translate(x, R, 0)
        out.add(ax)
    # King pin plate under the fore-carriage: what lets the front axle swing.
    pin = M.cylinder(0.055, 0.16, 8, CH_SMALL, "iron")
    pin.translate(front_x, Rf + 0.14, 0)
    out.add(pin)
    # Pole (the shafts of a horse pair), sloped down to the ground where it is
    # dropped when the team is out.
    pole = M.tube((front_x, Rf + 0.10, 0), (front_x - 2.05, 0.16, 0.06),
                  0.052, "oak", 6, CH_SMALL)
    out.add(pole)
    for sz in (-1, 1):
        st = M.tube((front_x - 0.10, Rf + 0.10, sz * 0.34),
                    (front_x - 1.05, 0.42, sz * 0.14), 0.030, "oak", 5, CH_SMALL)
        out.add(st)

    for x, R, d, sp in ((rear_x, Rr, rear, 12), (front_x, Rf, front, 10)):
        for sz in (-1, 1):
            # Four wheels at hero detail is 40% of a large prop's whole budget
            # (Art Bible §6: 8k), and two of them are always turned away.
            w = cart_wheel(f"{asset_id}.w.{x:.1f}.{sz}", dia=d, width=0.09,
                           spokes=sp, detail=0.7)
            w.rotate_y(0 if sz > 0 else np.pi)
            w.translate(x, R, sz * (width * 0.5 + 0.13))
            out.add(w)

    if load:
        out.add(_waggon_load(f"{asset_id}.load", load, length, width, bed_y))
    out.rotate_y(rng.uniform(-0.04, 0.04))
    return out


def _waggon_load(asset_id, kind, length, width, bed_y):
    """What is on the bed. Half-loaded always beats full: a full bed is a
    delivery that has not started, a half one is a job in progress."""
    rng = rng_for(asset_id, kind)
    out = M.Group()
    if kind == "barrels":
        # Chocked on their sides, which is how a cask travels — upright it
        # walks. The chocks are shown, because otherwise they roll off.
        for i in range(3):
            x = -length * 0.5 + 0.55 + i * 0.72
            b = barrel_lying(f"{asset_id}.{i}")
            b.translate(x, bed_y + BARREL_D * 0.5, rng.uniform(-0.09, 0.09))
            out.add(b)
            for sx in (-1, 1):
                ch = M.chamfered_prism([(0, 0), (0.16, 0), (0.0, 0.11)], 0.20,
                                       "oak_dark", CH_PROP)
                ch.rotate_y(np.pi * 0.5 if sx > 0 else -np.pi * 0.5)
                ch.translate(x + sx * 0.34, bed_y, 0)
                out.add(ch)
    elif kind == "sacks":
        from . import kit as K
        for i in range(5):
            s = K.sack(f"{asset_id}.{i}", height=0.50)
            s.scale(1.0, rng.uniform(0.78, 0.92), 1.0)      # slumped by the load above
            s.rotate_z(rng.uniform(-0.18, 0.18))
            s.translate(-length * 0.4 + i * 0.42 + rng.uniform(-0.05, 0.05),
                        bed_y + 0.02, rng.uniform(-0.22, 0.22))
            out.add(s)
    elif kind == "timber":
        for i in range(7):
            row, col = divmod(i, 4)
            lg = M.cylinder(rng.uniform(0.085, 0.115), length * 0.86, 7,
                            CH_SMALL, "oak")
            lg.rotate_z(np.pi * 0.5)
            lg.translate(length * 0.43, bed_y + 0.10 + row * 0.19,
                         -0.42 + col * 0.28 + row * 0.13)
            out.add(lg)
    elif kind == "hay":
        # Three overlapping forkfuls, not one dome: a single smooth ellipsoid
        # reads as a sand dune, and hay's whole character is that it was thrown
        # up there in armfuls and then roped down because it would blow away.
        for i in range(3):
            t = (i - 1) * 0.30
            h = M.globe(0.62, "straw", 8, 4,
                        sx=length * rng.uniform(0.20, 0.26) / 0.62,
                        sy=rng.uniform(0.42, 0.58),
                        sz=width * rng.uniform(0.40, 0.50) / 0.62)
            h.rotate_y(_yaw(rng, 0.5))
            h.translate(length * t, bed_y + 0.30 + rng.uniform(-0.05, 0.08),
                        rng.uniform(-0.05, 0.05))
            out.add(M.retex(h, 1.4, 1.4, rng.uniform(0, 0.7), rng.uniform(0, 0.7)))
        # Loose stalks out of the sides — the broken silhouette that says hay.
        for i in range(26):
            a = rng.uniform(0, 2 * np.pi)
            r0 = np.array([np.cos(a) * length * 0.30, bed_y + 0.30,
                           np.sin(a) * width * 0.40])
            out.add(M.tube(r0, r0 + np.array([np.cos(a) * 0.20,
                                              rng.uniform(-0.10, 0.16),
                                              np.sin(a) * 0.18]),
                           0.006, "grass_dry", 4, 0.001))
        # And the rope over the top, which is what holds it on.
        for x in (-length * 0.24, length * 0.22):
            out.add(M.catenary((x, bed_y - 0.10, -width * 0.62),
                               (x, bed_y - 0.10, width * 0.62),
                               -0.62, "canvas_plain", 0.012, 8, 4))
    return out


def sledge(asset_id, length=1.9, width=0.78, loaded="stone"):
    """A stone-sledge — runners, no wheels. Ground origin.

    Used everywhere a cart cannot go: up a yard, over a threshold, across mud.
    The runners are shod with iron strips on their wear face, and the whole
    thing sits on the ground rather than on an axle, which makes it the easiest
    honest way to break up a run of wheeled vehicles.
    """
    rng = rng_for(asset_id, "sledge")
    out = M.Group()
    for sz in (-1, 1):
        z = sz * (width * 0.5 - 0.06)
        run = M.chamfered_prism([(-length * 0.5, 0.0), (length * 0.42, 0.0),
                                 (length * 0.5, 0.13), (length * 0.5, 0.20),
                                 (-length * 0.5, 0.20)], 0.10,
                                "oak_dark", CH_PROP)
        run.rotate_y(np.pi * 0.5)
        run.translate(0, 0, z)
        out.add(run)
        shoe = M.plank(length * 0.99, 0.10, 0.014, CH_SMALL, "iron")
        shoe.translate(0, 0.007, z)
        out.add(shoe)
    for i in range(4):
        x = -length * 0.42 + i * length * 0.28
        cb = M.plank(width, 0.09, 0.075, CH_PROP, "oak_weathered", grain_axis=1)
        cb.rotate_y(np.pi * 0.5)
        cb.translate(x, 0.24, 0)
        out.add(cb)
    for i in range(5):
        p = M.plank(length * 0.94, width / 5 * 0.94, 0.030, CH_PROP, "oak_weathered")
        p.rotate_z(rng.uniform(-0.005, 0.005))
        p.translate(0, 0.30, -width * 0.5 + (i + 0.5) * width / 5)
        out.add(p)
    # Draught rope, coiled where it was dropped over the nose.
    out.add(M.catenary((-length * 0.5, 0.30, -0.20), (-length * 0.5 - 0.30, 0.05, 0.24),
                       0.10, "canvas_plain", 0.016, 6))

    if loaded == "stone":
        for i, (dx, dz) in enumerate(scatter(rng, 5, length * 0.30, width * 0.26)):
            s = M.box(rng.uniform(0.26, 0.40), rng.uniform(0.16, 0.24),
                      rng.uniform(0.22, 0.34), 0.022, "sandstone")
            s.rotate_y(_yaw(rng))
            s.translate(dx, 0.32 + rng.uniform(0, 0.10), dz)
            out.add(s)
    out.rotate_y(rng.uniform(-0.10, 0.10))
    return out


def wheelbarrow(asset_id, wheel=0.56, tipped=True):
    """A single-wheel barrow, tipped onto its nose against a wall or standing
    on its two legs. Ground origin, handles toward +X.

    Medieval barrows have the wheel right at the nose and the load between the
    handles, so almost all the weight is on the wheel — the opposite of a modern
    one and instantly readable as "not from now".
    """
    rng = rng_for(asset_id, "barrow")
    out = M.Group()
    R = wheel * 0.5
    tray_y = 0.42

    for sz in (-1, 1):
        z = sz * 0.26
        # The stave runs the whole length: it IS the handle and the frame.
        st = M.tube((-R - 0.10, R + 0.04, z * 0.50), (0.90, tray_y + 0.30, z),
                    0.032, "oak", 6, CH_SMALL)
        out.add(st)
        leg = M.tube((0.44, tray_y + 0.06, z * 0.92), (0.46, 0.0, z * 1.08),
                     0.028, "oak_weathered", 5, CH_SMALL)
        out.add(leg)
        # Foot bar between the legs, or it splays.
        if sz > 0:
            out.add(M.tube((0.46, 0.05, -0.28), (0.46, 0.05, 0.28), 0.020,
                           "oak_weathered", 5, CH_SMALL))

    # Tray: a real trough with sides that rise, built as one U-section rather
    # than as loose boards. The first version laid four planks nearly flat and
    # the barrow read as a ladder with a wheel on it — the SIDES are the whole
    # silhouette, and they have to be 0.22 m of visible rise.
    u = [(-0.30, 0.0), (0.30, 0.0), (0.42, 0.24), (0.38, 0.255),
         (0.27, 0.028), (-0.27, 0.028), (-0.38, 0.255), (-0.42, 0.24)]
    trough = M.chamfered_prism(u, 0.86, "oak_weathered", CH_PROP)
    trough.rotate_y(np.pi * 0.5)
    trough.rotate_z(-0.10)                       # nose-down, as it is set down
    trough.translate(0.18, tray_y, 0)
    out.add(trough)
    for sx, wd in ((-1, 0.60), (1, 0.74)):       # front and back boards
        b = M.chamfered_prism([(-wd * 0.5, 0.0), (wd * 0.5, 0.0),
                               (wd * 0.5 - 0.055, 0.235), (-wd * 0.5 + 0.055, 0.235)],
                              0.024, "oak_weathered", CH_PROP)
        b.rotate_y(np.pi * 0.5)
        b.rotate_z(sx * 0.16)
        b.translate(0.18 + sx * 0.42, tray_y + 0.015, 0)
        out.add(b)

    fork = M.tube((-R - 0.10, R + 0.04, -0.10), (-R - 0.10, R + 0.04, 0.10),
                  0.024, "iron", 5, CH_SMALL)
    out.add(fork)
    w = cart_wheel(f"{asset_id}.wheel", dia=wheel, width=0.065, spokes=8,
                   dish=0.012, detail=0.8)
    w.rotate_y(np.pi * 0.5)
    w.translate(-R - 0.10, R, 0)
    out.add(w)

    if tipped:
        out.rotate_z(0.0)
    out.rotate_y(rng.uniform(-0.15, 0.15))
    return out


def yoke_and_buckets(asset_id, mode="down", wall_z=0.0):
    """A shoulder yoke with two buckets. Ground origin.

    The yoke is the piece of evidence: it says somebody carries water from the
    well to this door twice a day, which is a whole daily routine implied by
    one 1.1 m curved board.

    `mode` decides what holds it up, and the default is the one that needs
    NOTHING — a wall-dependent default is how a prop ends up hanging in mid-air
    in every venue whose author did not read this line:

      `down` — set down across the two bucket rims. Self-supporting.
      `peg`  — hung on a peg in a wall at `z = wall_z`.
      `lean` — stood on end against that wall.
    """
    rng = rng_for(asset_id, "yoke")
    out = M.Group()
    # Curved to sit over the shoulders, with a neck cut-out in the middle.
    prof = [(-0.55, 0.02), (-0.30, 0.085), (-0.10, 0.075), (0.0, 0.045),
            (0.10, 0.075), (0.30, 0.085), (0.55, 0.02),
            (0.55, -0.03), (0.0, -0.005), (-0.55, -0.03)]
    yk = M.chamfered_prism(prof, 0.10, "oak_weathered", CH_PROP)

    bz = wall_z - 0.26
    bh = BUCKET_H
    if mode == "lean":
        lean(yk, 1.10, 0.30, wall_z=wall_z, roll=np.pi * 0.5)
        yoke_y, yoke_z = None, None
    elif mode == "peg":
        yoke_y, yoke_z = 0.88, wall_z - 0.16
        yk.translate(0, yoke_y, yoke_z)
        peg = M.cylinder(0.022, 0.14, 6, CH_SMALL, "oak_dark")
        peg.rotate_x(np.pi * 0.5)
        peg.translate(0, yoke_y + 0.04, wall_z - 0.07)
        out.add(peg)
    else:
        # Resting across the bucket rims — the yoke's own thickness above the
        # rim, tilted a little because it was dropped, not placed.
        yoke_y, yoke_z = bh + 0.035, bz
        yk.rotate_z(rng.uniform(-0.05, 0.05))
        yk.rotate_y(rng.uniform(-0.10, 0.10))
        yk.translate(0, yoke_y, yoke_z)
    out.add(yk)

    for i, sx in enumerate((-1, 1)):
        b = bucket(f"{asset_id}.b{i}", full=(i == 0))
        b.rotate_y(_yaw(rng))
        b.translate(sx * 0.46 + rng.uniform(-0.02, 0.02), 0.0,
                    bz + rng.uniform(-0.02, 0.02))
        out.add(b)
        if mode == "peg":
            # The rope from the yoke end down to the bail — the load path.
            out.add(M.catenary((sx * 0.52, yoke_y, yoke_z),
                               (sx * 0.46, bh - 0.02, bz),
                               0.02, "canvas_plain", 0.007, 4))
    return out


def panniers(asset_id, weave="stake"):
    """A pack-saddle pair of baskets, set down as a unit. Ground origin.

    Set down they lean into each other over the wooden saddle-tree, which is
    both what happens and how the arrangement stays up without a mule in it.
    """
    rng = rng_for(asset_id, "panniers")
    out = M.Group()
    tree = M.chamfered_prism([(-0.30, 0.0), (0.30, 0.0), (0.22, 0.20),
                              (0.0, 0.10), (-0.22, 0.20)], 0.44,
                             "oak_weathered", CH_PROP)
    tree.translate(0, 0.26, 0)
    out.add(tree)
    for sx in (-1, 1):
        bk = basket(f"{asset_id}.{sx}", radius=0.24, height=0.40, weave=weave,
                    taper=0.80)
        bk.rotate_z(sx * 0.30)
        bk.rotate_y(_yaw(rng, 0.4))
        bk.translate(sx * 0.36, 0.0, rng.uniform(-0.03, 0.03))
        out.add(bk)
        # Girth strap over the tree, into the basket rim.
        out.add(M.catenary((sx * 0.02, 0.44, -0.16), (sx * 0.42, 0.36, -0.14),
                           0.03, "leather", 0.014, 4))
    return out


def broken_wheel(asset_id, dia=WHEEL_DIA, wall_z=0.0, x=0.0):
    """A wheel with the tyre sprung and two spokes gone, leaning on a wall.

    The single best piece of residue available for a waggon yard or a farrier:
    it is a job somebody has not got to yet. Built by taking a real wheel apart
    rather than by modelling a broken one, so the break is legible — the felloe
    joint has opened, the tyre has come off its seat, and the two spokes that
    went with it are on the ground beside it.

    Origin at the ground, wheel face parallel to the wall at `z = wall_z`.
    """
    rng = rng_for(asset_id, "broken")
    out = M.Group()
    R = dia * 0.5

    # Two spokes out of the twelve, adjacent, so the gap is a hole in the
    # rhythm and reads as damage from across the yard rather than as a wheel
    # that merely has fewer spokes.
    w = M.Group()
    w.add(cart_wheel(f"{asset_id}.core", dia=dia, spokes=12, detail=0.85,
                     missing=(4, 5)))
    # Sprung tyre: a separate arc of hoop standing off its seat.
    arc = []
    for t in np.linspace(-0.55, 0.55, 7):
        arc.append((np.cos(t + 1.9) * (R + 0.055), np.sin(t + 1.9) * (R + 0.055)))
    for t in np.linspace(0.55, -0.55, 7):
        arc.append((np.cos(t + 1.9) * (R + 0.032), np.sin(t + 1.9) * (R + 0.032)))
    sprung = M.chamfered_prism(arc, 0.075, "iron_pitted", CH_SMALL)
    w.add(sprung)

    # Stand it on its rim and tip it back onto the wall. A wheel leaning at an
    # arbitrary angle with no contact is the classic floating prop.
    w.translate(0, R, 0)
    lean(w, dia, 0.34, wall_z=wall_z, x=x, roll=rng.uniform(-0.06, 0.06))
    out.add(w)

    # The two spokes that came out, on the ground where they were dropped.
    for i in range(2):
        sp = M.tube((0, 0, 0), (R - 0.16, 0.0, 0.0), 0.026, "oak", 5, CH_SMALL)
        sp.rotate_y(rng.uniform(-0.9, 0.9))
        sp.translate(x + rng.uniform(-0.35, 0.35), 0.026,
                     wall_z - 0.75 + rng.uniform(-0.15, 0.15))
        out.add(sp)
    return out


# ---------------------------------------------------------------------------
# Storage and trade
# ---------------------------------------------------------------------------

def barrel_lying(asset_id, height=BARREL_H, belly=BARREL_D, mat="oak_weathered"):
    """A cask on its side, bung up. Origin at the ground under its axis.

    Not a rotated `kit.barrel`: a cask laid down has its bung hole turned to
    the top, which is the whole reason it is laid down, and a stave pattern
    that runs the other way. Rotating the standing one leaves the bung
    underground half the time.
    """
    from . import kit as K
    rng = rng_for(asset_id, "cask")
    out = M.Group()
    b = K.barrel(f"{asset_id}.body", height=height, belly=belly, mat=mat)
    b.rotate_z(np.pi * 0.5)
    b.translate(height * 0.5, belly * 0.5, 0)
    out.add(b)
    # Bung, on top where a cellarman put it.
    bung = M.lathe([(0.036, 0), (0.042, 0.018), (0.030, 0.030)], 8, "oak_dark")
    bung.translate(rng.uniform(-0.06, 0.06), belly - 0.004, rng.uniform(-0.03, 0.03))
    out.add(bung)
    out.translate(-height * 0.5, 0, 0)
    return out


def bucket(asset_id, height=BUCKET_H, top=0.15, full=False, mat="oak_weathered",
           liquid="water"):
    """A coopered bucket with an iron bail. Ground origin.

    0.30 m tall, 0.30 m across the top — about two gallons, which is what a
    person can actually carry. Staves taper in toward the base, hoops top and
    bottom, and the bail is a real hoop through two ears rather than a handle
    stuck on the rim.
    """
    rng = rng_for(asset_id, "bucket")
    out = M.Group()
    h = jitter(rng, height, 0.05)
    rt, rb = top, top * 0.82
    out.add(M.lathe([(rb, 0), (rb + 0.004, 0.02), (rt - 0.004, h - 0.02), (rt, h)],
                    12, mat, close_top=False))
    for y, r in ((0.035, rb + 0.006), (h - 0.028, rt - 0.006)):
        out.add(M.ring(r + 0.006, 0.022, "iron", 12).translate(0, y, 0))
    # Ears and bail.
    for sx in (-1, 1):
        e = M.box(0.028, 0.055, 0.014, CH_SMALL, "iron")
        e.translate(sx * (rt - 0.004), h - 0.045, 0)
        out.add(e)
    bail = M.Group()
    for i in range(7):
        t = i / 6.0
        a = np.pi * t
        bail.add(M.tube((np.cos(a) * rt, np.sin(a) * rt * 0.85, 0),
                        (np.cos(np.pi * (i + 1) / 6.0) * rt,
                         np.sin(np.pi * (i + 1) / 6.0) * rt * 0.85, 0),
                        0.008, "iron", 4, 0.002))
    bail.rotate_z(rng.uniform(-0.5, 0.5))       # swung to wherever it was let go
    bail.translate(0, h - 0.03, 0)
    out.add(bail)
    if full:
        out.add(M.lathe([(0.0, h - 0.055), (rt - 0.012, h - 0.055)], 12, liquid,
                        close_bottom=False, close_top=False))
    out.rotate_y(_yaw(rng))
    return out


def basket(asset_id, radius=0.22, height=0.28, weave="stake", taper=0.78,
           handle=False, mat=None, fill=None):
    """A basket in one of four weaves. Ground origin.

    Four, because a market with one basket shape reads as a shop that sells one
    basket. They are genuinely different constructions, not one mesh with a
    different texture, and each belongs to different goods:

    - `stake`   — stake-and-strand: vertical stakes, horizontal randing. The
                  general-purpose basket. Willow.
    - `coil`    — coiled straw bound with bramble. Bread, proving, bee skeps.
    - `slath`   — square-work: an open lattice of flat splints. Produce, so the
                  air gets through and you can see what you are buying.
    - `spale`   — a heavy oak-spelk swill: thick riven splints, a bent rim.
                  Charcoal, potatoes, anything that would burst a willow basket.

    `fill` ∈ {None, "grain", "apples", "wool", "loaves"} puts something in it,
    heaped proud of the rim, because an empty basket is a shop that is closed.
    """
    rng = rng_for(asset_id, "basket", weave)
    dflt = {"stake": "reed", "coil": "straw", "slath": "reed", "spale": "oak_weathered"}
    m = mat or dflt.get(weave, "reed")
    out = M.Group()
    rb = radius * taper

    def r_at(t):
        return rb + (radius - rb) * t

    if weave == "coil":
        # One continuous rope of straw wound up the wall — so it is built as a
        # stack of slightly offset rings, which is exactly how it is made.
        n = max(4, int(height / 0.045))
        for i in range(n):
            t = (i + 0.5) / n
            rr = r_at(t)
            c = M.ring(rr, 0.048, m, 12)
            c.translate(rng.uniform(-0.004, 0.004), (i + 0.5) * height / n,
                        rng.uniform(-0.004, 0.004))
            out.add(M.retex(c, 2.2))
    elif weave == "slath":
        # Open square-work: flat splints crossing, with gaps you can see through.
        nst = 10
        for i in range(nst):
            a = 2 * np.pi * i / nst
            sp = M.box(0.016, height, 0.006, 0.002, m)
            sp.rotate_y(-a)
            sp.translate(np.cos(a) * r_at(0.5), height * 0.5, np.sin(a) * r_at(0.5))
            out.add(sp)
        for k in range(3):
            t = (k + 0.5) / 3
            out.add(M.ring(r_at(t), 0.020, m, 12).translate(0, t * height, 0))
    elif weave == "spale":
        # Riven oak splints, thick, with a steamed rim band.
        nst = 12
        for i in range(nst):
            a = 2 * np.pi * i / nst + rng.uniform(-0.03, 0.03)
            sp = M.chamfered_prism([(-0.030, 0.0), (0.030, 0.0),
                                    (0.038, height), (-0.038, height)],
                                   0.010, m, 0.002)
            sp.rotate_y(-a + np.pi * 0.5)
            sp.translate(np.cos(a) * r_at(0.5), 0, np.sin(a) * r_at(0.5))
            out.add(sp)
        out.add(M.ring(radius + 0.012, 0.034, "oak_dark", 14).translate(0, height - 0.012, 0))
        out.add(M.ring(rb + 0.008, 0.028, "oak_dark", 14).translate(0, 0.016, 0))
    else:   # stake
        nst = 14
        for i in range(nst):
            a = 2 * np.pi * i / nst + rng.uniform(-0.02, 0.02)
            sp = M.tube((np.cos(a) * rb, 0.0, np.sin(a) * rb),
                        (np.cos(a) * radius, height + 0.018, np.sin(a) * radius),
                        0.008, m, 4, 0.002)
            out.add(sp)
        nrow = max(3, int(height / 0.055))
        for k in range(nrow):
            t = (k + 0.5) / nrow
            rr = M.ring(r_at(t), 0.020, m, 14)
            rr.translate(0, t * height, 0)
            out.add(M.retex(rr, 3.0, 3.0, k * 0.13))
        out.add(M.ring(radius + 0.004, 0.030, m, 14).translate(0, height + 0.006, 0))

    # Base: a woven slath, always visible when the basket is tipped.
    base = M.lathe([(0.0, 0.008), (rb, 0.008)], 12, m, close_bottom=False)
    out.add(base)

    if handle:
        for i in range(9):
            a0, a1 = np.pi * i / 8, np.pi * (i + 1) / 8
            out.add(M.tube((np.cos(a0) * radius * 0.92, height + np.sin(a0) * radius * 0.75, 0),
                           (np.cos(a1) * radius * 0.92, height + np.sin(a1) * radius * 0.75, 0),
                           0.011, m, 4, 0.002))

    if fill:
        out.add(_heap_in(f"{asset_id}.fill", fill, radius * 0.92, height))
    out.rotate_y(_yaw(rng))
    return out


def _heap_in(asset_id, kind, radius, rim_y):
    """Goods heaped proud of a rim. The heap is what says "for sale"."""
    rng = rng_for(asset_id, kind)
    out = M.Group()
    if kind == "grain":
        h = M.lathe([(radius, 0.0), (radius * 0.72, 0.055), (0.0, 0.10)], 14, "straw")
        h.translate(0, rim_y - 0.03, 0)
        out.add(M.retex(h, 2.4))
    elif kind == "apples":
        for i, (dx, dz) in enumerate(scatter(rng, 14, radius * 0.86, radius * 0.86)):
            r = rng.uniform(0.030, 0.042)
            # `terracotta` is the town's warm fired-earth family and reads as
            # ripe fruit at this size; the per-instance UV offset below is what
            # makes fourteen apples fourteen shades rather than one.
            ap = M.globe(r, "terracotta", 6, 3, sy=0.92)
            ap.translate(dx, rim_y - 0.02 + r + rng.uniform(0, 0.05), dz)
            out.add(M.retex(ap, 3.0, 3.0, rng.uniform(0, 0.8), rng.uniform(0, 0.8)))
    elif kind == "wool":
        for i, (dx, dz) in enumerate(scatter(rng, 6, radius * 0.7, radius * 0.7)):
            f = M.globe(rng.uniform(0.075, 0.105), "fleece", 6, 3, sy=0.75)
            f.translate(dx, rim_y + 0.02 + rng.uniform(0, 0.05), dz)
            out.add(f)
    elif kind == "loaves":
        for i, (dx, dz) in enumerate(scatter(rng, 5, radius * 0.6, radius * 0.6)):
            b = M.globe(0.085, "bread", 7, 3, sy=0.62, sz=0.78)
            b.rotate_y(_yaw(rng))
            b.translate(dx, rim_y + 0.02, dz)
            out.add(M.retex(b, 2.0, 2.0, rng.uniform(0, 0.6)))
    return out


def crate(asset_id, size=CRATE, height=None, mat="oak", lid=False, open_top=False):
    """A nailed board crate. Ground origin, **base at y = 0**.

    Art Bible §3 gives a 0.55 m cube as the standard; `size` scales the plan and
    `height` overrides the rise independently, because a shipment is never all
    one box. `kit.crate` is the cube; this is the family.
    """
    rng = rng_for(asset_id, "crate2")
    s = jitter(rng, size, 0.035)
    h = jitter(rng, height if height is not None else size, 0.035)
    out = M.Group()
    t = 0.024
    nb = 4
    for sx in (-1, 1):                                  # ends
        for i in range(nb):
            b = M.plank(s, h / nb * 0.93, t, CH_PROP, mat, grain_axis=1)
            b.rotate_y(np.pi * 0.5)
            b.translate(sx * s * 0.5, (i + 0.5) * h / nb, 0)
            out.add(b)
    for sz in (-1, 1):                                  # sides
        for i in range(nb):
            b = M.plank(s, h / nb * 0.93, t, CH_PROP, mat)
            b.translate(0, (i + 0.5) * h / nb, sz * s * 0.5)
            out.add(b)
    if not open_top:
        for i in range(3):
            b = M.plank(s * 1.02, s / 3 * 0.94, t, CH_PROP, mat)
            b.rotate_z(rng.uniform(-0.004, 0.004))
            b.translate(0, h + t * 0.5, -s * 0.5 + (i + 0.5) * s / 3)
            out.add(b)
    for i in range(3):
        b = M.plank(s * 1.02, s / 3 * 0.94, t, CH_PROP, mat)
        b.translate(0, t * 0.5, -s * 0.5 + (i + 0.5) * s / 3)
        out.add(b)
    for sx in (-1, 1):                                  # corner battens
        for sz in (-1, 1):
            b = M.box(0.042, h * 1.01, 0.042, CH_PROP, "oak_dark")
            b.translate(sx * s * 0.5, h * 0.5, sz * s * 0.5)
            out.add(b)
    if lid:
        ld = M.plank(s * 1.06, s * 1.06, 0.028, CH_PROP, mat)
        ld.rotate_z(0.05)
        ld.rotate_y(0.28)
        ld.translate(0.05, h + 0.045, 0.03)
        out.add(ld)
    out.rotate_y(rng.uniform(-0.22, 0.22))
    return out


def crate_stack(asset_id, count=4, wall_z=None):
    """Crates of several sizes piled the way a porter piles them: biggest at the
    bottom, each one set down slightly askew, the top one open with its lid off.

    Layers are seated on measured bounds by `stack()`, so nothing floats. If
    `wall_z` is given the pile is pushed back until its deepest crate touches
    the wall, which is what stops a stack reading as marooned in open floor.
    """
    rng = rng_for(asset_id, "crates")
    sizes = sorted([rng.uniform(0.38, 0.62) for _ in range(int(count))], reverse=True)
    items = []
    for i, s in enumerate(sizes):
        top = (i == len(sizes) - 1)
        items.append(crate(f"{asset_id}.{i}", size=s,
                           height=s * rng.uniform(0.62, 1.0),
                           mat="oak" if i % 2 else "oak_weathered",
                           lid=top, open_top=top))
    out = stack(items, rng=rng, jitter_xz=0.035, yaw_spread=0.22)
    if wall_z is not None:
        lo, hi = out.bounds()
        out.translate(0, 0, wall_z - float(hi[2]) - 0.015)
    return out


def sack_stack(asset_id, count=5, wall_z=None, mat="sacking"):
    """Sacks piled against each other, sagging over the ones below. Ground origin.

    This is the arrangement the brief means by "sag against each other": a sack
    is soft goods, so the ones on top spread and flatten, and the ones at the
    bottom bulge out under the load. Modelled by scaling each layer wider and
    shorter the further down it is, and by tipping the upper ones toward the
    centre of the pile so they sit in the dish the lower ones make.
    """
    from . import kit as K
    rng = rng_for(asset_id, "sacks")
    out = M.Group()
    n = int(count)
    rows = [3, 2, 1] if n >= 5 else [2, 1]
    idx, y = 0, 0.0
    for r, cnt in enumerate(rows):
        load = 1.0 - r / max(1, len(rows))          # how much is stacked on top
        hgt = SACK_H * (1.05 - 0.20 * load)
        for k in range(cnt):
            if idx >= n:
                break
            s = K.sack(f"{asset_id}.{idx}", height=hgt, mat=mat)
            # Squashed WIDE by the load above and standing tall where there is
            # none. This is the whole illusion: a stack of identical lathes
            # reads as onions, and the vertical difference between the bottom
            # row and the top one is what makes it read as weight.
            s.scale(1.0 + 0.34 * load, 1.0, 1.0 + 0.22 * load)
            # Tipped into the dish the layer below makes.
            if r:
                s.rotate_z(rng.uniform(-0.22, 0.22))
                s.rotate_x(rng.uniform(-0.18, 0.18))
            spread = 0.38 * (cnt - 1)
            px = -spread * 0.5 + k * 0.38 + rng.uniform(-0.03, 0.03)
            pz = rng.uniform(-0.08, 0.08)
            s.translate(px, y, pz)
            out.add(s)
            idx += 1
        y += hgt * 0.70                              # they bed into each other
    if wall_z is not None:
        lo, hi = out.bounds()
        out.translate(0, 0, wall_z - float(hi[2]) - 0.01)
    return out


def amphora(asset_id, height=0.82, mat="pottery", standing=True):
    """A tall two-handled jar for oil or wine. Ground origin.

    Pointed at the base, so standing it needs a ring stand or a hole in the
    ground — and that is the detail: an amphora resting flat on paving is
    wrong, so this one comes with its stand, or it leans in a rack.
    """
    rng = rng_for(asset_id, "amphora")
    out = M.Group()
    h = jitter(rng, height, 0.05)
    r = h * 0.24
    body = M.lathe([(0.030, 0.0), (0.10, h * 0.10), (r, h * 0.40),
                    (r * 0.92, h * 0.58), (r * 0.42, h * 0.80),
                    (r * 0.34, h * 0.90), (r * 0.44, h)], 14, mat, close_top=False)
    out.add(M.retex(body, 1.0, 1.0, rng.uniform(0, 0.7)))
    for sx in (-1, 1):
        for i in range(4):
            t0, t1 = i / 4.0, (i + 1) / 4.0
            def hp(t):
                return (sx * (r * 0.36 + np.sin(t * np.pi) * r * 0.42),
                        h * (0.78 + t * 0.19), 0.0)
            out.add(M.tube(hp(t0), hp(t1), 0.020, mat, 5, 0.002))
    if standing:
        ring = M.ring(0.115, 0.055, "straw", 10)
        ring.translate(0, 0.028, 0)
        out.add(M.retex(ring, 3.0))
    out.rotate_y(_yaw(rng))
    return out


def glazed_jar(asset_id, height=0.40, mat="pottery_slip", stopper=True):
    """A fat glazed storage jar — honey, preserves, salt. Ground origin."""
    rng = rng_for(asset_id, "jar")
    out = M.Group()
    h = jitter(rng, height, 0.07)
    r = h * 0.44
    body = M.lathe([(r * 0.62, 0.0), (r * 0.70, h * 0.06), (r, h * 0.38),
                    (r * 0.86, h * 0.72), (r * 0.52, h * 0.92),
                    (r * 0.56, h)], 14, mat, close_top=not stopper)
    out.add(M.retex(body, 1.0, 1.0, rng.uniform(0, 0.7), rng.uniform(0, 0.5)))
    if stopper:
        st = M.lathe([(r * 0.50, h - 0.01), (r * 0.54, h + 0.03),
                      (r * 0.44, h + 0.055)], 10, "canvas_plain")
        out.add(st)
        # Tied down over the stopper with a cord, because it has to keep.
        out.add(M.ring(r * 0.56, 0.014, "canvas_plain", 12).translate(0, h + 0.008, 0))
    out.rotate_y(_yaw(rng))
    return out


def jar_cluster(asset_id, count=5, spread=0.55):
    """Jars and amphorae set down together, touching, never in a row.

    Vessels get grouped by whoever last carried them, so they cluster and lean
    on each other. Placement is a jittered ring plus one stray — the stray is
    what stops it reading as a pattern.
    """
    rng = rng_for(asset_id, "jars")
    out = M.Group()
    n = int(count)
    for i in range(n):
        a = 2 * np.pi * i / n + rng.uniform(-0.35, 0.35)
        d = spread * (0.35 + rng.uniform(0, 0.65)) * (1.9 if i == n - 1 else 1.0)
        if rng.random() < 0.35:
            g = amphora(f"{asset_id}.{i}", height=rng.uniform(0.66, 0.90))
        else:
            g = glazed_jar(f"{asset_id}.{i}", height=rng.uniform(0.24, 0.46),
                           mat="pottery" if i % 2 else "pottery_slip")
        g.translate(np.cos(a) * d, 0.0, np.sin(a) * d)
        out.add(g)
    return out


def cloth_bolt(asset_id, length=1.05, radius=0.085, mat="wool_undyed", loose=0.0):
    """A bolt of cloth on its board. Origin at the base, axis along X.

    The loose end matters more than the roll: a bolt with a tail hanging over
    the counter edge is cloth, and a bolt without one is a log.
    """
    rng = rng_for(asset_id, "bolt")
    out = M.Group()
    r = jitter(rng, radius, 0.08)
    core = M.lathe([(r, -length * 0.5), (r * 1.02, 0), (r, length * 0.5)], 12, mat,
                   close_bottom=True, close_top=True)
    core.rotate_z(np.pi * 0.5)
    core.translate(0, r, 0)
    out.add(M.retex(core, 1.0, 1.0, rng.uniform(0, 0.6)))
    # The last wrap, standing slightly proud so the roll has an edge.
    lap = M.chamfered_prism([(0, 0), (r * 1.5, -r * 0.35), (r * 1.6, -r * 0.1)],
                            length * 0.98, mat, 0.002)
    lap.rotate_y(np.pi * 0.5)
    lap.translate(0, r * 1.4, 0)
    out.add(lap)
    if loose > 0:
        # Over the front of the roll and straight down — `plane="xy"`, or it
        # comes out as a 45° ramp with the cloth going nowhere.
        def hf(u, v):
            return r * 1.1 * (1.0 - v) ** 2 + np.sin(u * 5.0) * 0.014 * v
        tail = M.sheet(length * 0.96, loose, hf, nx=8, nz=5, plane="xy", mat=mat)
        tail.translate(0, r * 1.55 - loose * 0.5, -r * 0.6)
        out.add(M.retex(tail, 1.0, 1.0, rng.uniform(0, 0.6)))
    return out


def bolt_rack(asset_id, count=6, width=1.2):
    """Bolts of cloth racked on a slope with one pulled out and dropped flat.

    Sloped, so the customer sees the ends and the colours read as a fan. The
    pulled-out bolt is the residue: somebody was showing it to somebody.
    """
    rng = rng_for(asset_id, "boltrack")
    out = M.Group()
    cols = ["wool_undyed", "wool_crimson", "wool_green", "wool_blue",
            "wool_amber", "linen", "cloth_brown"]
    for sx in (-1, 1):
        side = M.chamfered_prism([(0.0, 0.0), (0.42, 0.0), (0.42, 0.86),
                                  (0.0, 0.62)], 0.045, "oak_weathered", CH_PROP)
        side.rotate_y(np.pi * 0.5)
        side.translate(sx * width * 0.5, 0, 0)
        out.add(side)
    n = int(count)
    for i in range(n):
        t = i / max(1, n - 1)
        b = cloth_bolt(f"{asset_id}.{i}", length=width * 0.94, radius=0.075,
                       mat=cols[i % len(cols)])
        b.rotate_x(-0.36)
        b.rotate_y(np.pi * 0.5)
        b.translate(rng.uniform(-0.02, 0.02), 0.16 + t * 0.52, 0.16 - t * 0.30)
        out.add(b)
    stray = cloth_bolt(f"{asset_id}.stray", length=width * 0.9, radius=0.08,
                       mat=cols[(n + 2) % len(cols)], loose=0.42)
    stray.rotate_y(np.pi * 0.5 + rng.uniform(-0.2, 0.2))
    stray.translate(rng.uniform(-0.1, 0.1), 0.0, -0.52)
    out.add(stray)
    return out


def hanging_scales(asset_id, span=0.62, drop=0.55, tilt=0.055, mat="brass",
                   bracket=True, reach=0.34):
    """A beam-and-pan balance hung from a bracket. **Origin at the fixing.**

    Hung from `y = 0` and reaching DOWN, because it fixes to a wall or a beam,
    and hanging it from its own base is how a scale ends up embedded in a
    counter. `bracket` builds the forged arm it hangs from, ON by default:
    the thing it hangs from is not optional detail, it is the difference
    between a scale and a scale floating in the air.

    Weighted slightly off level — a balance resting exactly level with nothing
    in it is a balance nobody has used.
    """
    rng = rng_for(asset_id, "scales")
    out = M.Group()
    if bracket:
        # Reaches back along +Z to the wall, matching the module's wall frame:
        # a caller places the origin where the pans should hang and the arm
        # finds the plaster on its own.
        arm = M.box(0.030, 0.035, reach, CH_SMALL, "iron")
        arm.translate(0, 0.014, reach * 0.5)
        out.add(arm)
        out.add(M.tube((0, 0.004, reach * 0.30), (0, 0.26, reach - 0.01),
                       0.011, "iron", 5, 0.002))
        plate = M.box(0.050, 0.34, 0.024, 0.004, "iron")
        plate.translate(0, 0.14, reach - 0.008)
        out.add(plate)
    t = tilt * float(rng.choice([-1.0, 1.0]))
    beam = M.box(span, 0.018, 0.018, 0.002, mat)
    beam.rotate_z(t)
    beam.translate(0, -0.10, 0)
    out.add(beam)
    hook = M.tube((0, 0, 0), (0, -0.09, 0), 0.007, "iron", 5, 0.002)
    out.add(hook)
    for i in range(4):
        a0, a1 = np.pi * (0.2 + i * 0.15), np.pi * (0.2 + (i + 1) * 0.15)
        out.add(M.tube((np.cos(a0) * 0.035, -0.09 + np.sin(a0) * 0.035, 0),
                       (np.cos(a1) * 0.035, -0.09 + np.sin(a1) * 0.035, 0),
                       0.005, "iron", 4, 0.0015))
    for sx in (-1, 1):
        ex = sx * span * 0.5
        ey = -0.10 + np.sin(t) * ex
        # Pan hung on three cords, which is what stops it swinging.
        pd = drop * (1.0 - 0.18 * sx * np.sign(t or 1.0))
        for k in range(3):
            a = 2 * np.pi * k / 3
            out.add(M.tube((ex, ey, 0), (ex + np.cos(a) * 0.10, ey - pd,
                                         np.sin(a) * 0.10),
                           0.0035, "iron", 4, 0.001))
        pan = M.lathe([(0.0, 0.012), (0.075, 0.0), (0.115, 0.014),
                       (0.118, 0.022)], 14, mat, close_top=False)
        pan.translate(ex, ey - pd, 0)
        out.add(pan)
    return out


def weight_set(asset_id, count=5, mat="lead"):
    """A nest of graduated weights on a board. Ground origin.

    Ordered smallest to largest, which is the one arrangement a working person
    DOES make in size order — because the order is the information. Two are
    off the board where they were last used.
    """
    rng = rng_for(asset_id, "weights")
    out = M.Group()
    bd = M.plank(0.46, 0.16, 0.024, CH_PROP, "oak_dark")
    bd.translate(0, 0.012, 0)
    out.add(bd)
    for i in range(int(count)):
        r = 0.020 + i * 0.0105
        h = 0.022 + i * 0.011
        w = M.lathe([(r * 0.90, 0), (r, 0.006), (r * 0.94, h * 0.8), (r * 0.74, h)],
                    9, mat)
        stray = i >= count - 2 and rng.random() < 0.8
        x = -0.19 + i * 0.085
        if stray:
            w.translate(x + rng.uniform(0.05, 0.13), 0.0, rng.uniform(0.12, 0.20))
        else:
            w.translate(x, 0.024, rng.uniform(-0.015, 0.015))
        w.rotate_y(_yaw(rng))
        out.add(w)
    return out


def counting_board(asset_id, width=0.52, depth=0.36):
    """A chequered reckoning board with counters on it, mid-sum. Ground origin.

    A counting board is how arithmetic is done here, and it is safely
    pictorial — Art Bible §2 forbids readable lettering, and lines scored into
    a board carry no letters. The counters are NOT tidied into their lines:
    two are pushed up the board and one has fallen off, which is what "the
    reckoning was interrupted" looks like.
    """
    rng = rng_for(asset_id, "counting")
    out = M.Group()
    bd = M.plank(width, depth, 0.020, CH_PROP, "oak_dark")
    bd.translate(0, 0.010, 0)
    out.add(bd)
    for i in range(5):
        ln = M.box(width * 0.86, 0.003, 0.006, 0.001, "oak_weathered")
        ln.translate(0, 0.021, -depth * 0.34 + i * depth * 0.17)
        out.add(ln)
    for i in range(9):
        c = M.lathe([(0.014, 0), (0.016, 0.002), (0.014, 0.005)], 9, "brass")
        row = int(rng.integers(0, 5))
        if i == 8:
            c.translate(width * 0.5 + rng.uniform(0.04, 0.11), 0.003,
                        rng.uniform(-0.1, 0.1))
        else:
            c.translate(-width * 0.32 + rng.uniform(0, 0.6) * width * 0.64, 0.022,
                        -depth * 0.34 + row * depth * 0.17 + rng.uniform(-0.01, 0.01))
        out.add(c)
    return out


def coin_scales(asset_id):
    """A small folding coin balance in its open case. Ground origin.

    Every trader who takes silver owns one, because coin is clipped and has to
    be weighed. 0.24 m across — the smallest object in the library, and it
    exists to reward the player who walks right up to a counter.
    """
    rng = rng_for(asset_id, "coinscale")
    out = M.Group()
    case = M.chamfered_prism([(-0.12, 0), (0.12, 0), (0.115, 0.030),
                              (-0.115, 0.030)], 0.085, "oak_dark", CH_SMALL)
    case.rotate_x(np.pi * 0.5)
    case.translate(0, 0.015, 0)
    out.add(case)
    lid = M.plank(0.24, 0.085, 0.012, CH_SMALL, "oak_dark")
    lid.rotate_z(0.0)
    lid.rotate_x(-1.15)
    lid.translate(0, 0.075, 0.075)
    out.add(lid)
    sc = hanging_scales(f"{asset_id}.bal", span=0.15, drop=0.05, mat="brass",
                        bracket=False)
    sc.translate(0.0, 0.20, -0.01)
    out.add(sc)
    post = M.tube((0, 0.030, -0.01), (0, 0.20, -0.01), 0.005, "brass", 6, 0.001)
    out.add(post)
    for i in range(3):
        c = M.lathe([(0.010, 0), (0.011, 0.0015)], 8, "brass")
        c.translate(rng.uniform(-0.08, 0.08), 0.032, rng.uniform(-0.03, 0.03))
        out.add(c)
    out.rotate_y(rng.uniform(-0.4, 0.4))
    return out


def poultry_crate(asset_id, width=0.62, depth=0.44, height=0.36, birds=3):
    """A slatted crate of live poultry. Ground origin.

    Slatted rather than boarded, so the birds are visible — which is the point,
    and also why it is one of the few props here that reads as *alive*. The
    birds are simple heaped forms with a head each; at the gameplay camera that
    is exactly enough, and any more geometry would be modelling a chicken
    nobody can see.
    """
    rng = rng_for(asset_id, "poultry")
    out = M.Group()
    for sz in (-1, 1):
        for i in range(6):
            s = M.box(0.016, height, 0.020, 0.002, "oak_weathered")
            s.translate(-width * 0.5 + (i + 0.5) * width / 6, height * 0.5,
                        sz * depth * 0.5)
            out.add(s)
    for sx in (-1, 1):
        for i in range(4):
            s = M.box(0.020, height, 0.016, 0.002, "oak_weathered")
            s.translate(sx * width * 0.5, height * 0.5,
                        -depth * 0.5 + (i + 0.5) * depth / 4)
            out.add(s)
    for y in (0.012, height - 0.012):
        for sz in (-1, 1):
            r = M.plank(width * 1.02, 0.030, 0.018, CH_SMALL, "oak_dark")
            r.translate(0, y, sz * depth * 0.5)
            out.add(r)
    for i in range(4):
        s = M.plank(width * 0.98, depth / 4 * 0.9, 0.016, CH_SMALL, "oak_weathered")
        s.translate(0, height + 0.008, -depth * 0.5 + (i + 0.5) * depth / 4)
        out.add(s)
    for i in range(int(birds)):
        b = M.globe(0.11, "fleece", 7, 3, sx=1.25, sy=0.80, sz=0.85)
        b.rotate_y(_yaw(rng))
        b.translate(-width * 0.28 + i * width * 0.28 + rng.uniform(-0.03, 0.03),
                    0.10, rng.uniform(-0.06, 0.06))
        out.add(b)
        hd = M.globe(0.042, "fleece", 6, 3)
        hd.translate(-width * 0.28 + i * width * 0.28 + rng.uniform(0.06, 0.10),
                     0.20, rng.uniform(-0.06, 0.06))
        out.add(hd)
    out.rotate_y(rng.uniform(-0.25, 0.25))
    return out


# ---------------------------------------------------------------------------
# Tools, by trade — arranged by WORKFLOW
# ---------------------------------------------------------------------------
# Art Bible §7: "arranged as a *working person* would arrange them, by
# workflow, not by symmetry." That is the whole design rule for this section
# and it is not a stylistic preference — it is the difference between a shop
# and a shop-shaped display case. A smith's tongs hang in jaw order because he
# reaches for them blind with hot iron in the other hand. A cooper's croze sits
# on the block by the raising-up because it is the next cut. A carpenter's saws
# hang over the bench end he saws at. Sorting any of these by size is the tell.
#
# Each builder returns a Group with its origin on the ground at the CENTRE of
# the working area it describes, so a venue can drop one in and it lands as a
# composed station rather than as a pile of tools.

def _tool_handle(p0, p1, r=0.016, mat="oak_weathered"):
    return M.tube(p0, p1, r, mat, 5, CH_SMALL)


def _wall_pegs(asset_id, width, y, count=5, wall_z=0.0, mat="oak_dark"):
    """The pegs a tool wall actually hangs from. Nothing hangs on nothing."""
    rng = rng_for(asset_id, "pegs")
    out = M.Group()
    xs = []
    for i in range(int(count)):
        x = -width * 0.5 + (i + 0.5) * width / count + rng.uniform(-0.02, 0.02)
        pg = M.tube((x, y, wall_z), (x, y - 0.012, wall_z - 0.085), 0.011, mat, 5,
                    0.002)
        out.add(pg)
        xs.append(x)
    return out, xs


def smith_tools(asset_id, wall_z=0.0, width=1.9):
    """A smith's hand: tongs in jaw order, hardies in the block, the job in the
    quench. Origin on the ground, centred on the rack, wall at `z = wall_z`.

    Ordered by jaw — flat, hollow, bolt, box — because that is what a smith
    reaches for by feel while the iron cools. The hardy tools live in the
    anvil's hardy hole and its stump, not on the rack, because they are used
    in the anvil. And the half-finished blade is in the quench with its tang
    out, which is the single most legible "somebody stopped mid-job" cue in
    the town.
    """
    rng = rng_for(asset_id, "smith")
    out = M.Group()

    # Rack: a rail on two brackets, at the height a hand falls to.
    rail = M.plank(width, 0.055, 0.045, CH_PROP, "oak_dark")
    rail.translate(0, 1.42, wall_z - 0.075)
    out.add(rail)
    for sx in (-1, 1):
        br = M.chamfered_prism([(0, 0), (0.12, 0), (0, -0.16)], 0.035,
                               "iron", CH_SMALL)
        br.rotate_y(np.pi * 0.5)
        br.translate(sx * width * 0.42, 1.42, wall_z - 0.03)
        out.add(br)

    # Tongs, hung by the rein, jaws down. Jaw type changes along the rail.
    for i in range(6):
        x = -width * 0.42 + i * width * 0.168 + rng.uniform(-0.012, 0.012)
        rein = 0.34 + i * 0.055                       # longer reins for hotter work
        tilt = rng.uniform(-0.06, 0.06)
        for sx in (-1, 1):
            top = (x, 1.42, wall_z - 0.075)
            piv = (x + sx * 0.020, 1.42 - rein * 0.62, wall_z - 0.075 + tilt * 0.1)
            jaw = (x + sx * 0.030 * (1 + i * 0.35), 1.42 - rein, wall_z - 0.075)
            out.add(_tool_handle(top, piv, 0.0075, "iron"))
            out.add(_tool_handle(piv, jaw, 0.0095, "iron"))
        # The rivet, which is what makes it tongs and not two rods.
        rv = M.cylinder(0.010, 0.024, 6, 0.002, "iron")
        rv.rotate_x(np.pi * 0.5)
        rv.translate(x, 1.42 - rein * 0.62, wall_z - 0.088)
        out.add(rv)

    # Swage block on a stump, and the tool stump beside it. Both are what the
    # loose iron STANDS ON — nothing here is allowed to hang in the air, and
    # the first pass had three hammers doing exactly that beside a bench that
    # did not exist in this builder.
    sx0, sz0 = -width * 0.34, wall_z - 0.62
    stump = M.lathe([(0.26, 0), (0.24, 0.06), (0.25, 0.44), (0.23, 0.50)], 12,
                    "endgrain")
    stump.translate(sx0, 0, sz0)
    out.add(stump)
    sw = M.box(0.40, 0.10, 0.34, 0.012, "iron_pitted", uv_scale=MATS.uv_detail("iron_pitted", 0.833, why="0.40 m member; the library's 1 m tile shows 40% of one tile here and reads as flat colour"))
    sw.rotate_y(0.22)
    sw.translate(sx0, 0.55, sz0)
    out.add(sw)
    for i in range(4):
        d = 0.022 + i * 0.011
        hole = M.lathe([(d, 0.0), (d, 0.02)], 8, "cinder",
                       close_bottom=False, close_top=False)
        hole.translate(sx0 - 0.12 + i * 0.085, 0.595,
                       sz0 + rng.uniform(-0.05, 0.05))
        out.add(hole)

    # Tool stump: a second block a pace along, carrying the hardies and the
    # hammers. Hardies stand point-DOWN in its drilled holes and hammers lie
    # across its top, head outward, which is how they are set down between
    # heats — you pick a hammer up by its handle without looking at it.
    tx, tz = sx0 + 0.62, wall_z - 0.56
    tstump = M.lathe([(0.24, 0), (0.22, 0.06), (0.23, 0.56), (0.21, 0.62)], 12,
                     "endgrain")
    tstump.translate(tx, 0, tz)
    out.add(tstump)
    for i, (hl, hw) in enumerate(((0.20, 0.030), (0.17, 0.046), (0.22, 0.024))):
        x = tx - 0.10 + i * 0.10
        z = tz - 0.06 + rng.uniform(-0.02, 0.02)
        sh = M.box(0.030, hl, 0.030, CH_SMALL, "iron")
        sh.rotate_z(rng.uniform(-0.05, 0.05))
        sh.translate(x, 0.62 + hl * 0.5, z)
        out.add(sh)
        hdd = M.chamfered_prism([(-hw, 0), (hw, 0), (0.0, 0.075)], 0.030,
                                "steel_blued", CH_SMALL)
        hdd.translate(x, 0.62 + hl, z)
        out.add(hdd)
    for i, (ln, hd) in enumerate(((0.34, 0.075), (0.40, 0.095), (0.30, 0.060))):
        a = 0.5 + i * 0.9 + rng.uniform(-0.15, 0.15)
        top = 0.62 + hd * 0.55
        out.add(_tool_handle((tx, top, tz + 0.10),
                             (tx + np.cos(a) * ln, top, tz + 0.10 + np.sin(a) * ln),
                             0.013))
        h = M.box(hd * 1.6, hd, hd, CH_SMALL, "iron")
        h.rotate_y(-a)
        h.translate(tx - np.cos(a) * 0.045, top, tz + 0.10 - np.sin(a) * 0.045)
        out.add(h)

    # Quench tub with the job in it — the tang out of the water, still gripped.
    from . import kit as K
    q = K.barrel(f"{asset_id}.quench", height=0.70, belly=0.66)
    q.translate(width * 0.46, 0, wall_z - 0.85)
    out.add(q)
    out.add(K.water_disc(0.29, y=0.58, depth=0.5, segments=16)
            .translate(width * 0.46, 0, wall_z - 0.85))
    blade = M.chamfered_prism([(0.0, -0.020), (0.46, -0.012), (0.52, 0.0),
                               (0.46, 0.014), (0.0, 0.022)], 0.010,
                              "steel_blued", 0.002)
    blade.rotate_z(1.05)
    blade.rotate_y(0.6)
    blade.translate(width * 0.46 - 0.06, 0.42, wall_z - 0.88)
    out.add(blade)
    # Scale and clinker on the ground round the tub: iron sheds it every heat.
    for dx, dz in scatter(rng, 22, 0.55, 0.45):
        c = M.box(rng.uniform(0.018, 0.042), rng.uniform(0.004, 0.012),
                  rng.uniform(0.018, 0.038), 0.002, "cinder")
        c.rotate_y(_yaw(rng))
        c.translate(width * 0.46 + dx, 0.004, wall_z - 0.85 + dz)
        out.add(c)
    return out


def cooper_setup(asset_id, wall_z=0.0):
    """A cask half-built: staves in a raising-up hoop, croze and adze to hand.

    The **raising-up** is the moment a cask exists — the staves stood in a
    truss hoop, splayed at the bottom like a flower, before they are fired and
    drawn together. It is the most distinctive silhouette in any trade in the
    town and it is unmistakably a job in progress.

    Workflow order, left to right: riven staves in a stack → the raising-up →
    the block with the croze and the adze on it (the next two cuts) → finished
    hoops leaning. Origin on the ground at the raising-up.
    """
    rng = rng_for(asset_id, "cooper")
    out = M.Group()

    # -- 1. riven staves, stacked and leaning where they season -------------
    for i in range(9):
        st = M.chamfered_prism([(-0.055, 0), (0.055, 0), (0.045, 0.92),
                                (-0.045, 0.92)], 0.022, "oak", 0.003)
        lean(st, 0.92, 0.20 + rng.uniform(0, 0.05), wall_z=wall_z,
             x=-1.35 + i * 0.055 + rng.uniform(-0.015, 0.015),
             roll=rng.uniform(-0.10, 0.10))
        out.add(st)

    # -- 2. the raising-up --------------------------------------------------
    n, R, H = 17, 0.30, 0.86
    for i in range(n):
        a = 2 * np.pi * i / n + rng.uniform(-0.02, 0.02)
        # Splayed: the foot is wider than the head, held only at the truss hoop.
        top = (np.cos(a) * R * 0.93, H, np.sin(a) * R * 0.93)
        bot = (np.cos(a) * R * 1.30, 0.0, np.sin(a) * R * 1.30)
        st = M.chamfered_prism([(-0.052, 0), (0.052, 0), (0.044, 1.0), (-0.044, 1.0)],
                               0.020, "oak", 0.003)
        # Point the stave along its own axis by placing it on a basis.
        #
        # `ex` is the TANGENT, not the radius. A stave is a board 104 mm wide
        # and 20 mm thick, and its width lies AROUND the cask — that is what
        # makes seventeen of them close into a barrel. Built radial (which the
        # first pass did) they stand edge-on with 80 mm of air between each
        # pair, and the raising-up reads as a crown of sticks instead of as a
        # cask taking shape.
        d = np.array(top) - np.array(bot)
        L = float(np.linalg.norm(d))
        ey = d / L
        ex = np.array([-np.sin(a), 0.0, np.cos(a)])          # tangential
        ez = np.cross(ex, ey)
        ez /= np.linalg.norm(ez)
        ex = np.cross(ey, ez)
        st.scale(1.0, L, 1.0)
        M.place(st, origin=bot, ex=ex, ey=ey, ez=ez)
        out.add(st)
    # Truss hoop holding the head — remove it and the whole thing falls over,
    # so it is the load path and it has to be there.
    out.add(M.ring(R * 0.96, 0.055, "iron_pitted", 18).translate(0, H - 0.06, 0))

    # -- 3. the block, with the next two tools ON it ------------------------
    blk = M.lathe([(0.32, 0), (0.30, 0.08), (0.31, 0.54), (0.29, 0.60)], 14,
                  "endgrain")
    blk.translate(0.95, 0, wall_z - 0.55)
    out.add(blk)
    # Croze — the plane that cuts the groove the head sits in. Flat on the
    # block with its fence up, exactly as it is set down between staves.
    cz = M.chamfered_prism([(-0.13, 0), (0.13, 0), (0.13, 0.055), (-0.13, 0.055)],
                           0.075, "oak_dark", CH_SMALL)
    cz.rotate_y(0.4)
    cz.translate(0.88, 0.63, wall_z - 0.62)
    out.add(cz)
    czc = M.box(0.030, 0.026, 0.055, 0.002, "steel_blued")
    czc.rotate_y(0.4)
    czc.translate(0.88, 0.66, wall_z - 0.62)
    out.add(czc)
    # Adze, hung over the block edge by its head — the way it is left, because
    # standing it on its edge blunts it.
    out.add(_tool_handle((1.06, 0.62, wall_z - 0.42), (1.22, 0.44, wall_z - 0.20),
                         0.017, "oak"))
    adz = M.chamfered_prism([(0.0, -0.045), (0.10, -0.055), (0.13, 0.0),
                             (0.10, 0.050), (0.0, 0.040)], 0.055,
                            "steel_blued", CH_SMALL)
    adz.rotate_z(-0.8)
    adz.rotate_y(0.9)
    adz.translate(1.05, 0.63, wall_z - 0.43)
    out.add(adz)

    # -- 4. finished hoops, graded, leaning on the wall --------------------
    for i in range(4):
        r = 0.24 + i * 0.055
        hp = M.ring(r, 0.045, "iron", 18)
        hp.rotate_x(np.pi * 0.5)
        hp.translate(0, r, 0)
        lean(hp, r * 2.0, 0.16 + i * 0.035, wall_z=wall_z, x=-2.15 - i * 0.06,
             roll=rng.uniform(-0.05, 0.05))
        out.add(hp)

    # -- residue: shavings, everywhere a cooper stands --------------------
    out.add(shavings(f"{asset_id}.sv", 22, 1.5, 0.85, "oak",
                     centre=(0.6, wall_z - 0.6)))
    return out


def shavings(asset_id, count, rx, rz, mat="oak", centre=(0.0, 0.0), curl=1.0):
    """Curled shavings on a floor. The signature of every wood trade.

    PUBLIC because every wood trade in the craft quarter needs it and the
    alternative they were reaching for — `spill(kind="sand")` — builds a
    smooth conical HEAP. A heap is right for grain and wrong for shavings: at
    eye height under a cooper's or a joiner's roof it reads as a sand dune,
    which is what the first craft-quarter renders came back with. Shavings lie
    flat and scattered, and that is the whole difference.

    A three-point profile, not four: a shaving is a curl seen edge-on and the
    fourth point bought nothing but a third more triangles, on the one prop in
    the file that is scattered forty at a time.
    """
    rng = rng_for(asset_id, "shavings")
    out = M.Group()
    cx, cz = centre
    for dx, dz in scatter(rng, int(count), rx, rz, power=0.5):
        ln = rng.uniform(0.07, 0.13) * curl
        sv = M.chamfered_prism([(0, 0), (ln, 0.014), (ln * 0.1, 0.028)],
                               0.024, mat, 0.0015)
        sv.rotate_x(np.pi * 0.5)
        sv.rotate_y(_yaw(rng))
        sv.rotate_z(rng.uniform(-0.4, 0.4))
        sv.translate(cx + dx, 0.008, cz + dz)
        out.add(sv)
    return out


_shavings = shavings          # the name this had before it went public


def carpenter_bench(asset_id, length=2.4, wall_z=0.0):
    """Trestles carrying a half-jointed frame, saws over the sawing end.

    The frame on the trestles is the job: two rails and a stile with the mortise
    cut and the tenon offered up but not driven, and the marking gauge lying
    across it where the line was struck. Nothing about it is finished, which is
    the point — Art Bible §7 asks for a half-finished job, not a finished one
    displayed. Origin at the ground, centred under the frame.
    """
    from . import kit as K
    rng = rng_for(asset_id, "carp")
    out = M.Group()
    top_y = 0.72

    # Trestles.
    for sx in (-1, 1):
        x = sx * length * 0.30
        beam = M.plank(0.90, 0.10, 0.085, CH_PROP, "oak_weathered", grain_axis=1)
        beam.rotate_y(np.pi * 0.5)
        beam.translate(x, top_y, 0)
        out.add(beam)
        for dz in (-1, 1):
            for dx in (-1, 1):
                out.add(_tool_handle((x + dx * 0.05, top_y, dz * 0.10),
                                     (x + dx * 0.26, 0.0, dz * 0.34),
                                     0.026, "oak_weathered"))

    # The frame being jointed: two rails, a stile, one tenon offered up.
    for i, z in enumerate((-0.26, 0.26)):
        rl = M.plank(length * 0.92, 0.13, 0.045, CH_PROP, "oak")
        rl.translate(rng.uniform(-0.02, 0.02), top_y + 0.09, z)
        out.add(rl)
    stile = M.plank(0.80, 0.15, 0.048, CH_PROP, "oak", grain_axis=1)
    stile.rotate_y(np.pi * 0.5)
    stile.rotate_z(0.03)
    stile.translate(-length * 0.16, top_y + 0.135, 0)
    out.add(stile)
    # The mortise: a real hole, cut as a dark recess rather than drawn on.
    mort = M.box(0.075, 0.028, 0.14, 0.003, "cinder")
    mort.translate(-length * 0.16, top_y + 0.135, 0.26)
    out.add(mort)
    # The tenon, offered up and standing a few centimetres out — not driven.
    ten = M.plank(0.34, 0.13, 0.044, CH_PROP, "oak")
    ten.rotate_y(0.06)
    ten.translate(length * 0.16, top_y + 0.135, 0.26)
    out.add(ten)
    # Marking gauge lying where the line was struck.
    gg = M.box(0.075, 0.030, 0.075, CH_SMALL, "oak_dark")
    gg.rotate_y(0.7)
    gg.translate(length * 0.02, top_y + 0.13, -0.05)
    out.add(gg)
    out.add(_tool_handle((length * 0.02, top_y + 0.13, -0.05),
                         (length * 0.02 + 0.13, top_y + 0.13, -0.14),
                         0.010, "oak_dark"))

    # Saws hung on the wall over the end that gets sawn.
    pegs, xs = _wall_pegs(f"{asset_id}.pegs", 0.9, 1.55, 3, wall_z)
    out.add(pegs)
    for i, x in enumerate(xs):
        bl = 0.62 - i * 0.11
        px = x + length * 0.5 - 0.45
        tilt = rng.uniform(-0.06, 0.06)
        # Hung heel-up from the peg, blade tapering to the toe. The TEETH are
        # what make it a saw at three metres: a plain tapered rectangle in a
        # dark blued steel reads as a black paddle, which is what the first
        # pass hung on three walls of this town.
        saw = M.chamfered_prism([(0.0, 0.0), (bl, 0.020), (bl, 0.062),
                                 (0.0, 0.120)], 0.005, "steel_blued", 0.0015)
        saw.rotate_z(-np.pi * 0.5)
        saw.rotate_y(tilt)
        saw.translate(px, 1.53, wall_z - 0.055)
        out.add(saw)
        nteeth = int(bl / 0.028)
        for t in range(nteeth):
            ty = 1.53 - (t + 0.5) * bl / nteeth
            tw = 0.020 + (t / nteeth) * 0.042        # deeper toward the heel
            tooth = M.chamfered_prism([(0.0, 0.0), (0.014, 0.0), (0.0, tw)],
                                      0.005, "steel_blued", 0.0012)
            tooth.rotate_z(-np.pi * 0.5)
            tooth.rotate_y(tilt)
            tooth.translate(px + 0.062 + tw * 0.5, ty, wall_z - 0.055)
            out.add(tooth)
        hnd = M.chamfered_prism([(0.0, 0.0), (0.135, 0.010), (0.145, 0.100),
                                 (0.060, 0.145), (0.0, 0.135)], 0.028,
                                "oak_dark", CH_SMALL)
        hnd.rotate_z(-np.pi * 0.5)
        hnd.rotate_y(tilt)
        hnd.translate(px, 1.545, wall_z - 0.062)
        out.add(hnd)
    # Brace and bits, hung under the saws.
    brc = M.Group()
    for i in range(6):
        t0, t1 = i / 6.0, (i + 1) / 6.0
        def cr(t):
            a = t * 2 * np.pi
            return (np.sin(a) * 0.10, -abs(np.cos(a)) * 0.0 + t * 0.36 - 0.18,
                    -0.02 + np.cos(a) * 0.055)
        brc.add(M.tube(cr(t0), cr(t1), 0.014, "oak_dark", 5, 0.002))
    brc.translate(length * 0.5 - 0.72, 1.22, wall_z - 0.10)
    out.add(brc)

    # Shavings and offcuts under the bench — the floor of every joiner's shop.
    out.add(_shavings(f"{asset_id}.sv", 26, length * 0.55, 0.55, "oak"))
    for i in range(4):
        oc = M.plank(rng.uniform(0.18, 0.42), rng.uniform(0.07, 0.13), 0.030,
                     CH_PROP, "oak")
        oc.rotate_y(_yaw(rng))
        oc.rotate_z(rng.uniform(-0.1, 0.1))
        oc.translate(rng.uniform(-length * 0.5, length * 0.5), 0.016,
                     rng.uniform(-0.7, 0.5))
        out.add(oc)
    out.add(K.rope_coil(f"{asset_id}.rope", 0.18)
            .translate(-length * 0.5 - 0.15, 0.0, wall_z - 0.30))
    return out


def baker_kit(asset_id, wall_z=0.0):
    """Peels leaning by the oven mouth, a dough trough, and flour on EVERYTHING.

    The flour is the whole prop. A bakery without a metre of flour dust around
    the trough is a room with an oven in it; with it, every surface within reach
    of the tipping is pale and the floor holds footprints. Origin on the ground
    at the trough.
    """
    rng = rng_for(asset_id, "baker")
    out = M.Group()

    # Dough trough: a coffin-shaped tub on splayed legs, lid slid half off.
    tw, td, th = 1.35, 0.62, 0.42
    body = M.chamfered_prism([(-tw * 0.5, 0.0), (tw * 0.5, 0.0),
                              (tw * 0.5 + 0.055, th), (-tw * 0.5 - 0.055, th)],
                             td, "oak_weathered", CH_PROP)
    body.translate(0, 0.52, 0)
    out.add(body)
    for sx in (-1, 1):
        for sz in (-1, 1):
            out.add(_tool_handle((sx * tw * 0.38, 0.54, sz * td * 0.36),
                                 (sx * (tw * 0.38 + 0.12), 0.0,
                                  sz * (td * 0.36 + 0.10)), 0.030))
    lid = M.plank(tw * 0.72, td * 1.02, 0.028, CH_PROP, "oak_weathered")
    lid.rotate_y(0.05)
    lid.translate(tw * 0.20, 0.945, 0.02)
    out.add(lid)
    # The dough, risen proud of the trough where the lid is off.
    dg = M.globe(0.30, "bread", 9, 4, sx=1.5, sy=0.42, sz=0.85)
    dg.translate(-tw * 0.18, 0.94, 0)
    out.add(M.retex(dg, 1.6))

    # Peels: long-handled, leaning against the wall by the oven. Blade UP —
    # a peel stood blade-down warps, and every baker knows it.
    for i, bl in enumerate((0.36, 0.30, 0.24)):
        pl = M.Group()
        pl.add(M.cylinder(0.019, 1.55, 6, CH_SMALL, "oak_weathered"))
        blade = M.chamfered_prism([(-bl * 0.5, 0), (bl * 0.5, 0),
                                   (bl * 0.42, 0.40), (-bl * 0.42, 0.40)],
                                  0.014, "oak", 0.002)
        blade.translate(0, 1.53, 0)
        pl.add(blade)
        lean(pl, 1.93, 0.34 + i * 0.04, wall_z=wall_z, x=-1.15 + i * 0.13,
             roll=rng.uniform(-0.07, 0.07))
        out.add(pl)

    # Flour barrel with the scoop left standing in it — nobody puts it back.
    from . import kit as K
    fb = K.barrel(f"{asset_id}.flour", height=0.72, belly=0.60)
    fb.translate(1.15, 0, wall_z - 0.48)
    out.add(fb)
    fl = M.lathe([(0.0, 0.70), (0.27, 0.68)], 14, "flour",
                 close_bottom=False, close_top=False)
    fl.translate(1.15, 0, wall_z - 0.48)
    out.add(fl)
    sc = M.lathe([(0.0, 0), (0.075, 0.02), (0.085, 0.10)], 9, "oak",
                 close_top=False)
    sc.rotate_z(0.55)
    sc.translate(1.09, 0.66, wall_z - 0.52)
    out.add(sc)
    out.add(_tool_handle((1.09, 0.72, wall_z - 0.52), (1.02, 1.02, wall_z - 0.60),
                         0.014, "oak"))

    # Cooling rack of loaves, because the smell is the shop's advertisement.
    for sx in (-1, 1):
        out.add(_tool_handle((-1.05 + sx * 0.34, 0.0, wall_z - 0.95),
                             (-1.05 + sx * 0.30, 0.86, wall_z - 0.90), 0.026))
    shelf = M.plank(0.80, 0.34, 0.026, CH_PROP, "oak_weathered")
    shelf.translate(-1.05, 0.86, wall_z - 0.92)
    out.add(shelf)
    for i in range(4):
        lf = M.globe(0.082, "bread", 8, 3, sy=0.66, sz=0.82)
        lf.rotate_y(_yaw(rng, 0.5))
        lf.translate(-1.34 + i * 0.19, 0.955, wall_z - 0.92 + rng.uniform(-0.04, 0.04))
        out.add(M.retex(lf, 2.0, 2.0, rng.uniform(0, 0.6)))

    # THE FLOUR. A metre of it, thinning outward, plus handprints on the trough.
    out.add(spill(f"{asset_id}.flour", kind="flour", radius=1.15, centre=(0, wall_z - 0.1)))
    for i in range(3):
        hp = M.quad(0.10, 0.075, "flour", uv_scale=MATS.uv_detail("flour", 0.167, why="0.10 m member; the library's 1 m tile shows 10% of one tile here and reads as flat colour"))
        hp.rotate_x(-np.pi * 0.5)
        hp.rotate_z(rng.uniform(-0.5, 0.5))
        hp.translate(rng.uniform(-0.5, 0.5), 0.955, -td * 0.5 - 0.004)
        out.add(hp)
    return out


def chandler_kit(asset_id, wall_z=0.0):
    """Dipping frames of candles at graduated diameters over the tallow pot.

    Dipping is repetitive and cumulative: each pass adds a layer, so on one
    frame the candles are fat and on the next they are still thin. Showing two
    frames at different stages is the trade in one glance, and it also explains
    why the pot is where it is — directly under, so the drips go back in.
    Origin on the ground at the pot.
    """
    rng = rng_for(asset_id, "chandler")
    out = M.Group()

    # The tallow pot on its trivet over a low fire pit.
    pot = M.lathe([(0.20, 0.0), (0.30, 0.10), (0.32, 0.34), (0.30, 0.42),
                   (0.33, 0.46)], 16, "iron_pitted", close_top=False)
    pot.translate(0, 0.24, 0)
    out.add(pot)
    for i in range(3):
        a = 2 * np.pi * i / 3
        out.add(_tool_handle((np.cos(a) * 0.20, 0.26, np.sin(a) * 0.20),
                             (np.cos(a) * 0.26, 0.0, np.sin(a) * 0.26),
                             0.016, "iron"))
    tal = M.lathe([(0.0, 0.62), (0.29, 0.60)], 16, "tallow",
                  close_bottom=False, close_top=False)
    out.add(tal)
    for dx, dz in scatter(rng, 9, 0.30, 0.30):
        e = M.box(rng.uniform(0.05, 0.11), rng.uniform(0.03, 0.06),
                  rng.uniform(0.05, 0.10), 0.006, "cinder")
        e.rotate_y(_yaw(rng))
        e.translate(dx, 0.02, dz)
        out.add(e)

    # Two dipping frames on their own legs: one early, one nearly finished.
    # The pair IS the trade — dipping is cumulative, so the difference in
    # diameter between the two frames is a whole morning's work made visible.
    for f, (x, rad, ln) in enumerate(((-0.74, 0.014, 0.20), (0.76, 0.030, 0.30))):
        bar = M.cylinder(0.020, 0.72, 7, CH_SMALL, "oak_weathered")
        bar.rotate_x(np.pi * 0.5)
        bar.translate(x, 1.26, 0)
        out.add(bar)
        for sz in (-1, 1):
            out.add(_tool_handle((x, 1.26, sz * 0.34), (x, 0.0, sz * 0.42),
                                 0.026, "oak_weathered"))
            out.add(_tool_handle((x - 0.20, 0.30, sz * 0.38),
                                 (x + 0.20, 0.30, sz * 0.38), 0.018,
                                 "oak_weathered"))
        for i in range(6):
            z = -0.26 + i * 0.104
            # The wick runs the WHOLE length inside the candle and hangs a
            # finger's width proud at the bottom; wax builds from the outside
            # in, so the candle is a stubby taper with a drip at its foot.
            out.add(M.tube((x, 1.26, z), (x, 1.26 - ln - 0.045, z), 0.0030,
                           "canvas_plain", 4, 0.001))
            cd = M.lathe([(rad * 0.55, 0.0), (rad * 0.95, 0.022),
                          (rad, ln * 0.45), (rad * 0.90, ln * 0.92),
                          (rad * 0.62, ln)], 8, "beeswax")
            cd.rotate_x(np.pi)
            cd.translate(x + rng.uniform(-0.005, 0.005), 1.235, z)
            out.add(cd)
            # The drip hanging off the bottom, which is the whole silhouette
            # difference between a candle and a length of dowel.
            dp = M.globe(rad * 0.85, "beeswax", 6, 3, sy=1.5)
            dp.translate(x, 1.235 - ln + rad * 0.5, z)
            out.add(dp)

    # Finished candles bundled on the wall shelf, tied in dozens.
    shelf = M.plank(0.86, 0.24, 0.026, CH_PROP, "oak_dark")
    shelf.translate(0, 1.55, wall_z - 0.12)
    out.add(shelf)
    for i in range(3):
        bd = M.Group()
        for k in range(6):
            a = 2 * np.pi * k / 6
            c = M.cylinder(0.010, 0.26, 7, 0.002, "beeswax")
            c.translate(np.cos(a) * 0.021, 0, np.sin(a) * 0.021)
            bd.add(c)
        bd.add(M.ring(0.030, 0.014, "canvas_plain", 8).translate(0, 0.16, 0))
        bd.rotate_z(1.45)
        bd.rotate_y(rng.uniform(-0.3, 0.3))
        bd.translate(-0.28 + i * 0.28, 1.60, wall_z - 0.12 + rng.uniform(-0.03, 0.03))
        out.add(bd)
    return out


def tanner_kit(asset_id, wall_z=0.0):
    """The beam, the currier's knives, and hides on stretcher frames.

    A tanner's beam is a half-round log on a slope that the worker leans over
    to push the flesh off a hide with a two-handled knife. It is unmistakable
    and it is the reason the tannery is downwind. The hides on the frames are
    the residue AND the product. Origin on the ground at the beam.
    """
    rng = rng_for(asset_id, "tanner")
    out = M.Group()

    # Beam: a half log on a slope, LOW END ON THE GROUND and high end on two
    # legs. Both ends have to be carried — the first pass rotated the log about
    # its foot and then lifted the whole thing, which left the low end hanging
    # 0.32 m in the air with the legs under the far end only.
    # Laid ACROSS the view, not pointing at it. A beam seen end-on is a stump,
    # and the whole reason this object identifies a tannery is its 1.8 m of
    # sloped length with a hide over it. The worker stands at the low end and
    # pushes away, so in a venue it is turned to face the street; here it lies
    # along X with the butt at -X on the ground and the head on two legs.
    ln, tilt = 1.85, 0.62
    beam = M.lathe([(0.0, 0.0), (0.16, 0.03), (0.175, ln - 0.06), (0.0, ln)],
                   12, "elm")
    beam.rotate_z(-np.pi * 0.5 + tilt)              # butt down at -X
    beam.translate(-ln * 0.48, 0.10, 0.0)
    out.add(beam)
    hx = -ln * 0.48 + ln * np.cos(tilt)
    hy = 0.10 + ln * np.sin(tilt)
    for sz in (-1, 1):
        out.add(_tool_handle((hx - 0.06, hy - 0.10, sz * 0.05),
                             (hx + 0.10, 0.0, sz * 0.34), 0.042))
    # The hide over it, half worked, lying along and hanging down both sides.
    def hf(u, v):
        return 0.17 - 0.17 * (abs(v - 0.5) * 2.0) ** 1.6 - 0.02 * np.sin(u * 5.0)
    hide = M.sheet(1.30, 0.80, hf, nx=9, nz=7, mat="hide_raw")
    hide.rotate_z(tilt * 0.92)
    hide.translate(-ln * 0.48 + ln * 0.52 * np.cos(tilt),
                   0.10 + ln * 0.52 * np.sin(tilt) + 0.02, 0.0)
    out.add(hide)

    # Currier's knives on the wall: two-handled, hung by both handles.
    pegs, xs = _wall_pegs(f"{asset_id}.pegs", 1.0, 1.48, 2, wall_z)
    out.add(pegs)
    for x in xs:
        bl = M.chamfered_prism([(-0.34, 0.0), (0.34, 0.0), (0.32, 0.085),
                                (-0.32, 0.085)], 0.005, "steel_blued", 0.002)
        bl.rotate_y(rng.uniform(-0.05, 0.05))
        bl.translate(x, 1.40, wall_z - 0.055)
        out.add(bl)
        for sx in (-1, 1):
            h = M.cylinder(0.020, 0.115, 6, CH_SMALL, "oak_dark")
            h.rotate_z(np.pi * 0.5 * sx)
            h.rotate_y(np.pi * 0.5)
            h.translate(x + sx * 0.38, 1.44, wall_z - 0.055)
            out.add(h)

    # Hides on stretcher frames, laced to the frame at intervals — the lacing
    # is what proves it is stretched rather than draped.
    for i, sx in enumerate((-1, 1)):
        fx = sx * 1.35
        # The frame SURROUNDS the hide: two stiles at ±X and two rails at
        # top and bottom, all in the same XY plane the hide is stretched in.
        # Built at ±Z (which the first pass did) the frame stands in front of
        # and behind the skin instead of around it, and the hide reads as a
        # sheet of board propped against two posts.
        fr = M.Group()
        for dx in (-0.50, 0.50):
            st = M.plank(1.78, 0.060, 0.055, CH_PROP, "oak_weathered")
            st.rotate_z(np.pi * 0.5)
            st.translate(dx, 0.89, 0)
            fr.add(st)
        for dy in (0.06, 1.72):
            rl = M.plank(1.06, 0.060, 0.055, CH_PROP, "oak_weathered")
            rl.translate(0, dy, 0)
            fr.add(rl)
        # The hide is a HIDE-SHAPED outline, not a rectangle. A rectangular
        # sheet in a rectangular frame reads as a sheet of plywood, which is
        # what the first pass produced; the four leg lobes and the neck are the
        # whole silhouette, and they are the reason the lacing has to be
        # irregular too.
        lobes = [(-0.16, -0.72), (0.16, -0.70),                # two hind legs
                 (0.40, -0.34), (0.36, 0.10),
                 (0.19, 0.52), (0.30, 0.72),                   # foreleg
                 (0.05, 0.78), (-0.08, 0.74),                  # neck
                 (-0.28, 0.70), (-0.19, 0.46),                 # foreleg
                 (-0.38, 0.06), (-0.41, -0.36)]
        sk = M.chamfered_prism([(x * 0.98 + rng.uniform(-0.02, 0.02),
                                 y * 1.02 + rng.uniform(-0.02, 0.02))
                                for x, y in lobes], 0.010, "hide_raw", 0.003,
                               uv_scale=MATS.uv_detail("hide_raw", 1, why="0.01 m member; the library's 2 m tile shows 0% of one tile here and reads as flat colour"))
        sk.translate(rng.uniform(-0.03, 0.03), 0.88, 0)
        fr.add(sk)
        # Lacing: cords from the hide's edge out to the frame, at the lobes.
        for k, (lx, ly) in enumerate(lobes):
            if k % 2:
                continue
            ex = 0.47 if lx > 0 else -0.47
            fr.add(M.tube((lx, 0.88 + ly, 0.0), (ex, 0.88 + ly * 0.94, 0.0),
                          0.005, "canvas_plain", 4, 0.001))
        lean(fr, 1.78, 0.28, wall_z=wall_z, x=fx, roll=rng.uniform(-0.04, 0.04))
        out.add(fr)

    # Bark for the tan pit, in a heap: the other half of the trade.
    for dx, dz in scatter(rng, 26, 0.55, 0.42):
        bk = M.chamfered_prism([(0, 0), (0.085, 0.010), (0.080, 0.045), (0.0, 0.038)],
                               0.055, "oak_dark", 0.002)
        bk.rotate_x(np.pi * 0.5)
        bk.rotate_y(_yaw(rng))
        bk.translate(0.10 + dx, 0.02 + abs(dx) * 0.10, wall_z - 1.35 + dz)
        out.add(bk)
    return out


def bowyer_kit(asset_id, wall_z=0.0):
    """Bow staves seasoning in a rack, and one on the tiller.

    Staves season for years, so a bowyer's shop is mostly a wall of timber
    doing nothing — which is exactly the kind of quiet, specific detail that
    reads as a real trade. The one on the tillering frame is the job.
    Origin on the ground at the rack.
    """
    rng = rng_for(asset_id, "bowyer")
    out = M.Group()

    # Rack: two rails on brackets, staves stood between them on a foot plate.
    # Seven staves in three groups, not thirteen evenly spaced — thirteen at an
    # even pitch is a picket fence, which is exactly what the first pass built.
    # A seasoning rack is filled as staves arrive, so it comes in clumps with
    # gaps where somebody has taken one out.
    for y in (0.20, 1.60):
        r = M.plank(1.9, 0.075, 0.055, CH_PROP, "oak_dark")
        r.translate(0, y, wall_z - 0.11)
        out.add(r)
        for sx in (-1, 1):
            br = M.chamfered_prism([(0, 0), (0.13, 0), (0, -0.11)], 0.030,
                                   "iron", CH_SMALL)
            br.rotate_y(np.pi * 0.5)
            br.translate(sx * 0.80, y, wall_z - 0.05)
            out.add(br)
    plate = M.plank(1.9, 0.20, 0.045, CH_PROP, "oak_dark")
    plate.translate(0, 0.022, wall_z - 0.22)
    out.add(plate)
    xs = [-0.78, -0.70, -0.60, -0.22, -0.12, 0.34, 0.44, 0.52]
    for i, x0 in enumerate(xs):
        x = x0 + rng.uniform(-0.02, 0.02)
        ln = rng.uniform(1.72, 2.05)                 # a stave is a whole tree limb
        w = rng.uniform(0.026, 0.038)
        # ROUND, tapering, with bark on one face — a bow stave is a split limb,
        # not a milled board. Flat prisms read as fence palings, which is what
        # they were doing, and milled dimensional lumber is banned outright by
        # Art Bible §2 anyway.
        st = M.Group()
        st.add(M.lathe([(w * 0.92, 0.0), (w, ln * 0.08), (w * 0.88, ln * 0.62),
                        (w * 0.66, ln)], 7,
                       "elm" if i % 3 else "oak", close_top=False))
        bark = M.chamfered_prism([(-w * 0.75, 0), (w * 0.75, 0),
                                  (w * 0.55, ln * 0.92), (-w * 0.55, ln * 0.92)],
                                 w * 0.35, "oak_dark", 0.002)
        bark.translate(0, ln * 0.04, -w * 0.80)
        st.add(bark)
        lean(st, ln, 0.19 + rng.uniform(0, 0.06), wall_z=wall_z - 0.13, x=x,
             roll=rng.uniform(-0.09, 0.09))
        out.add(st)

    # Tillering frame: the stave braced on a post with the string down a scale
    # of notches, which is how draw weight is judged.
    px = 1.35
    post = M.box(0.10, 1.65, 0.10, CH_PROP, "oak_dark")
    post.translate(px, 0.825, wall_z - 0.42)
    out.add(post)
    for k in range(7):
        n = M.box(0.115, 0.016, 0.030, 0.002, "oak_dark")
        n.translate(px, 0.70 + k * 0.085, wall_z - 0.36)
        out.add(n)
    bow = M.Group()
    n = 9
    pts = []
    for i in range(n + 1):
        t = i / n
        y = -0.82 + t * 1.64
        pts.append((px - 0.02 - np.cos(t * np.pi) * 0.0, 1.30 + y,
                    wall_z - 0.42 - 0.30 * np.sin(t * np.pi)))
    for i in range(n):
        bow.add(M.tube(pts[i], pts[i + 1], 0.017 * (1.0 - abs(i / n - 0.5) * 0.5),
                       "elm", 5, 0.002))
    out.add(bow)
    out.add(M.tube(pts[0], pts[-1], 0.004, "canvas_plain", 4, 0.001))

    # Long ribbon shavings from the drawknife — a bowyer's are the longest of
    # any trade, because a stave is worked in single passes down its length.
    out.add(_shavings(f"{asset_id}.sv", 18, 0.75, 0.40, "elm",
                      centre=(px - 0.3, wall_z - 0.95), curl=1.6))
    return out


def fishmonger_kit(asset_id, wall_z=0.0):
    """Wet boards on trestles, a gutting knife stuck in the end, straw and ice.

    Everything here is about water: the board is sloped to a drip channel, the
    ground below it is dark, the straw from the ice house is wet where the fish
    sat on it. The knife stuck point-down in the board end is where a fishwife
    actually leaves it between fish. Origin on the ground at the board.
    """
    from . import kit as K
    rng = rng_for(asset_id, "fish")
    out = M.Group()
    bw, bd = 1.75, 0.86

    for sx in (-1, 1):
        x = sx * bw * 0.32
        cross = M.plank(bd * 1.05, 0.085, 0.070, CH_PROP, "oak_weathered",
                        grain_axis=1)
        cross.rotate_y(np.pi * 0.5)
        cross.rotate_x(-0.09)                    # the slope to the drip end
        cross.translate(x, 0.82, 0)
        out.add(cross)
        for dz in (-1, 1):
            for dx in (-1, 1):
                out.add(_tool_handle((x + dx * 0.04, 0.82, dz * 0.14),
                                     (x + dx * 0.24, 0.0, dz * 0.36), 0.028))
    board = M.plank(bw, bd, 0.042, CH_PROP, "oak_weathered")
    board.rotate_x(-0.09)
    board.translate(0, 0.87, 0)
    out.add(board)
    # Drip channel along the low edge and the puddle it makes on the ground.
    ch = M.box(bw * 0.98, 0.024, 0.045, 0.004, "oak_dark")
    ch.translate(0, 0.87 - bd * 0.5 * 0.09 + 0.02, bd * 0.5 - 0.03)
    out.add(ch)
    pud = K.water_slab(0.55, 0.34, y=0.006, depth=0.03)
    pud.translate(0.10, 0, bd * 0.5 + 0.22)
    out.add(pud)

    # Straw bed from the ice house, and fish laid head-to-tail on it.
    for dx, dz in scatter(rng, 26, bw * 0.42, bd * 0.30):
        s = M.box(rng.uniform(0.09, 0.17), 0.008, rng.uniform(0.010, 0.020),
                  0.001, "straw")
        s.rotate_y(_yaw(rng))
        s.translate(dx, 0.895 - dx * 0.0 + 0.004, dz)
        out.add(s)
    for i in range(6):
        f = M.globe(0.085, "fish", 7, 3, sx=2.3, sy=0.55, sz=0.75)
        f.rotate_y(np.pi * 0.5 + rng.uniform(-0.25, 0.25) + (np.pi if i % 2 else 0))
        f.rotate_z(rng.uniform(-0.06, 0.06))
        f.translate(-bw * 0.36 + i * bw * 0.145, 0.925, rng.uniform(-0.14, 0.14))
        out.add(M.retex(f, 1.6, 1.6, rng.uniform(0, 0.6)))
        tl = M.chamfered_prism([(0, 0), (0.075, 0.055), (0.075, -0.055)], 0.006,
                               "fish", 0.002)
        tl.rotate_y(np.pi * 0.5 + (np.pi if i % 2 else 0))
        tl.translate(-bw * 0.36 + i * bw * 0.145 + (0.19 if i % 2 else -0.19),
                     0.925, 0)
        out.add(tl)

    # The knife, stuck point-down in the board end.
    kb = M.chamfered_prism([(0.0, -0.016), (0.20, -0.012), (0.23, 0.0),
                            (0.20, 0.014), (0.0, 0.020)], 0.004,
                           "steel_blued", 0.0015)
    kb.rotate_z(-1.30)
    kb.translate(bw * 0.5 - 0.10, 0.80, -0.24)
    out.add(kb)
    kh = M.cylinder(0.017, 0.10, 6, CH_SMALL, "oak_dark")
    kh.rotate_z(0.27)
    kh.translate(bw * 0.5 - 0.155, 1.02, -0.24)
    out.add(kh)

    # A hand balance over the board, and the scale-and-guts bucket beneath it.
    sc = hanging_scales(f"{asset_id}.scale", span=0.50, drop=0.36, mat="brass",
                        reach=0.50)
    sc.translate(-bw * 0.5 + 0.30, 1.85, wall_z - 0.50)
    out.add(sc)
    out.add(bucket(f"{asset_id}.gut", full=True, liquid="water")
            .translate(-bw * 0.5 + 0.22, 0.0, -0.42))
    return out


# ---------------------------------------------------------------------------
# Domestic and street
# ---------------------------------------------------------------------------

def laundry_line(asset_id, a, b, sag=None, items=5, mat="canvas_plain"):
    """A line between two points with washing pegged along it. World-space.

    Takes WORLD endpoints rather than a local origin, because a laundry line is
    defined by the two things it is tied to — a window mullion and a bracket
    across the alley — and authoring it at an origin then trying to move it
    into place is how one end ends up in mid-air. `sag` defaults to 4% of span,
    which is what a wet line does.

    Each garment hangs from the line's OWN height at its own point along the
    catenary, so the washing follows the droop instead of hanging off a
    straight line the eye can see is straight. Every piece has a real drape
    across its width from the two pegs.
    """
    rng = rng_for(asset_id, "laundry")
    p0 = np.asarray(a, np.float64)
    p1 = np.asarray(b, np.float64)
    span = float(np.linalg.norm(p1 - p0))
    sg = float(sag if sag is not None else span * 0.04)
    out = M.Group()
    out.add(M.catenary(p0, p1, sg, "canvas_plain", 0.007, 10, 4))

    # Weighted toward the dyed cloths rather than the undyed ones. A line of
    # cream linen hung against lime plaster is invisible from across a yard —
    # measured on the first in-situ render, where four of five garments
    # vanished into the wall behind them — and washing is one of the few
    # chances the town gets to put Art Bible §4's accent colours at height.
    cloths = ["cloth_green", "linen", "cloth_blue", "cloth_rust",
              "cloth_cream", "cloth_green", "cloth_brown", "cloth_blue"]
    for i in range(int(items)):
        t = (i + 0.5) / items + rng.uniform(-0.03, 0.03)
        t = float(np.clip(t, 0.05, 0.95))
        pt = p0 + (p1 - p0) * t + np.array([0.0, -sg * 4.0 * t * (1.0 - t), 0.0])
        w = rng.uniform(0.34, 0.62)
        h = rng.uniform(0.42, 0.86)
        # Belly: pinched to nothing at the two pegs, bulging between them, and
        # swinging further out the further down it hangs. `plane="xy"` so it
        # HANGS rather than lying at 45° — see mesh.sheet.
        def hf(u, v, s=rng.uniform(0.6, 1.4)):
            pin = float(np.sin(u * np.pi)) ** 0.7   # 0 at the pegs, 1 mid-width
            return pin * 0.10 * (0.25 + v) + np.sin(u * 6.0 * s) * 0.014 * v
        cl = M.sheet(w, h, hf, nx=7, nz=6, plane="xy",
                     mat=cloths[(i + len(asset_id)) % len(cloths)])
        cl.rotate_y(float(np.arctan2(p1[0] - p0[0], p1[2] - p0[2])) + np.pi * 0.5)
        # Its top edge is at local +h/2, so drop it onto the line.
        cl.translate(*(pt + np.array([0.0, -h * 0.5 - 0.006, 0.0])))
        out.add(M.retex(cl, 1.0, 1.0, rng.uniform(0, 0.6)))
        # Pegs, so the washing is attached to something.
        for sx in (-1, 1):
            d = (p1 - p0) / max(span, 1e-6)
            pp = pt + d * (sx * w * 0.46)
            pg = M.box(0.014, 0.055, 0.014, 0.002, "oak")
            pg.translate(*pp)
            out.add(pg)
    return out


def broom(asset_id, length=1.32, wall_z=None, x=0.0):
    """A birch besom. Leaning on a wall if `wall_z` is given, else upright.

    The head is a bundle of twigs bound twice to a shaft, splayed at the
    bottom and worn short on one side — a broom that has swept anything is
    never symmetrical.
    """
    rng = rng_for(asset_id, "broom")
    out = M.Group()
    shaft = M.cylinder(0.019, length, 6, CH_SMALL, "oak_weathered")
    out.add(shaft)
    n = 22
    for i in range(n):
        a = 2 * np.pi * i / n + rng.uniform(-0.15, 0.15)
        r0 = 0.024
        splay = rng.uniform(0.055, 0.11) * (0.55 if np.cos(a) > 0.4 else 1.0)
        out.add(M.tube((np.cos(a) * r0, 0.42, np.sin(a) * r0),
                       (np.cos(a) * splay, rng.uniform(-0.01, 0.02), np.sin(a) * splay),
                       0.0045, "reed", 4, 0.001))
    for y in (0.16, 0.34):
        out.add(M.ring(0.038, 0.016, "canvas_plain", 9).translate(0, y, 0))
    if wall_z is not None:
        lean(out, length, 0.26, wall_z=wall_z, x=x, roll=rng.uniform(-0.12, 0.12))
    else:
        out.rotate_y(_yaw(rng))
    return out


def boot_scraper(asset_id, wall_z=0.0, x=0.0):
    """A forged scraper set in a stone block beside a door. Ground origin.

    Two uprights and a blade between them, worn hollow in the middle by twenty
    years of boots. The hollow is the detail — a straight bar reads as new, and
    nothing beside a door in this town is new.
    """
    rng = rng_for(asset_id, "scraper")
    out = M.Group()
    blk = M.box(0.34, 0.11, 0.22, 0.022, "sandstone", uv_scale=MATS.uv_detail("sandstone", 0.714, why="0.34 m member; the library's 2 m tile shows 17% of one tile here and reads as flat colour"))
    blk.translate(x, 0.055, wall_z - 0.20)
    out.add(blk)
    for sx in (-1, 1):
        u = M.chamfered_prism([(-0.014, 0), (0.014, 0), (0.010, 0.20),
                               (-0.010, 0.20)], 0.020, "iron", 0.002)
        u.translate(x + sx * 0.115, 0.10, wall_z - 0.20)
        out.add(u)
    # The blade: dished in the middle where the boots land.
    for i in range(5):
        t = (i + 0.5) / 5
        dip = np.sin(t * np.pi) * 0.014
        seg = M.box(0.052, 0.020 - dip * 0.35, 0.016, 0.002, "iron")
        seg.translate(x - 0.10 + i * 0.05, 0.285 - dip, wall_z - 0.20)
        out.add(seg)
    # And the mud it scraped off, at its foot.
    out.add(spill(f"{asset_id}.mud", kind="mud", radius=0.30,
                  centre=(x, wall_z - 0.34), density=0.6))
    return out


def stool(asset_id, height=BENCH_H, radius=0.17, mat="oak_weathered", legs=3):
    """A three-legged stool. Ground origin, seat at `height` (Art Bible §3).

    Three legs, because a three-legged stool does not rock on a beaten earth
    floor and a four-legged one does — which is why every one in the town has
    three and why getting it right reads as knowledge rather than decoration.
    """
    rng = rng_for(asset_id, "stool")
    out = M.Group()
    h = jitter(rng, height, 0.045)
    seat = M.lathe([(0.0, h - 0.035), (radius * 0.95, h - 0.038),
                    (radius, h - 0.012), (radius * 0.92, h)], 12, mat)
    out.add(M.retex(seat, 1.4, 1.4, rng.uniform(0, 0.6)))
    for i in range(int(legs)):
        a = 2 * np.pi * i / legs + rng.uniform(-0.10, 0.10)
        out.add(M.tube((np.cos(a) * radius * 0.62, h - 0.035, np.sin(a) * radius * 0.62),
                       (np.cos(a) * radius * 1.18, 0.0, np.sin(a) * radius * 1.18),
                       0.020, mat, 6, CH_SMALL))
    out.rotate_y(_yaw(rng))
    return out


def chair(asset_id, cloak=True, height=0.92, mat="oak_weathered",
          cloak_mat="wool_crimson"):
    """A ladder-back chair with a cloak over it. Ground origin, back toward +Z.

    Art Bible §7 names "a cloak over a chair back" specifically, and it is the
    best single prop in this file: it implies a person who is somewhere else in
    the building right now. The cloak is a real draped sheet folded over the
    top rail, not a box, so it hangs down both sides at different lengths.
    """
    rng = rng_for(asset_id, "chair")
    out = M.Group()
    seat_h = BENCH_H
    for sx in (-1, 1):
        # Back legs run all the way up and become the stiles.
        out.add(_tool_handle((sx * 0.19, 0.0, 0.19), (sx * 0.17, height, 0.20),
                             0.022, mat))
        out.add(_tool_handle((sx * 0.19, 0.0, -0.19), (sx * 0.18, seat_h, -0.17),
                             0.022, mat))
    for k, t in enumerate((0.45, 0.72, 0.97)):
        y = seat_h + (height - seat_h) * t
        rail = M.chamfered_prism([(-0.175, -0.012), (0.175, -0.012),
                                  (0.175, 0.030), (-0.175, 0.030)], 0.020, mat,
                                 CH_SMALL)
        rail.rotate_x(np.pi * 0.5)
        rail.translate(0, y, 0.195)
        out.add(rail)
    for i in range(4):
        p = M.plank(0.38, 0.085, 0.024, CH_PROP, mat)
        p.translate(0, seat_h, -0.15 + i * 0.095)
        out.add(p)
    for dz in (-0.17, 0.17):
        st = M.plank(0.36, 0.030, 0.024, CH_PROP, mat)
        st.translate(0, 0.19, dz)
        out.add(st)

    if cloak:
        # Folded over the top rail: a long fall down the back and a short one
        # down the front, built as two hanging panels rather than one folded
        # surface — a fold modelled as a single sheet cannot have two different
        # lengths, and the difference in length is what says "thrown over"
        # rather than "hung up".
        # Long tail behind the chair, short one over the seat.
        for face, drop in ((-1.0, 0.62), (1.0, 0.34)):
            def hf(u, v, f=face):
                # Bunched at the rail, spreading and rippling as it falls.
                return f * (0.045 + 0.055 * v + np.sin(u * 5.0 + f) * 0.022 * v)
            cl = M.sheet(0.44, drop, hf, nx=8, nz=6, plane="xy", mat=cloak_mat)
            cl.rotate_y(rng.uniform(-0.10, 0.10))
            cl.translate(rng.uniform(-0.04, 0.04),
                         height - 0.015 - drop * 0.5, 0.195)
            out.add(M.retex(cl, 1.2))
        # The bight over the rail itself, closing the two panels at the top.
        cap = M.chamfered_prism([(-0.055, 0.0), (0.055, 0.0), (0.048, 0.055),
                                 (-0.048, 0.055)], 0.44, cloak_mat, 0.003)
        cap.rotate_y(np.pi * 0.5)
        cap.translate(0, height - 0.030, 0.195)
        out.add(cap)
    out.rotate_y(rng.uniform(-0.30, 0.30))
    return out


def mug(asset_id, height=0.115, mat="pottery", full=True):
    """A drinking mug with a strap handle. Ground origin.

    500 tris of nothing that nonetheless does more for a rail or a bar top than
    another window would, because it is the object that proves a person was
    standing right here a minute ago.
    """
    rng = rng_for(asset_id, "mug")
    out = M.Group()
    h = jitter(rng, height, 0.06)
    r = h * 0.42
    body = M.lathe([(r * 0.82, 0.0), (r * 0.86, 0.012), (r, h * 0.55),
                    (r * 0.97, h), (r * 0.90, h)], 12, mat, close_top=False)
    out.add(M.retex(body, 1.6, 1.6, rng.uniform(0, 0.7)))
    out.add(M.lathe([(0.0, 0.014), (r * 0.84, 0.014)], 12, mat,
                    close_bottom=False, close_top=False))
    for i in range(5):
        t0, t1 = i / 5.0, (i + 1) / 5.0
        def hp(t):
            a = np.pi * (t - 0.5)
            return (r * 0.96 + np.cos(a) * r * 0.52, h * 0.30 + t * h * 0.44 +
                    np.sin(a) * 0.0, 0.0)
        out.add(M.tube(hp(t0), hp(t1), 0.008, mat, 4, 0.0015))
    if full:
        out.add(M.lathe([(0.0, h * 0.80), (r * 0.92, h * 0.80)], 12, "water",
                        close_bottom=False, close_top=False))
    out.rotate_y(_yaw(rng))
    return out


def spill(asset_id, kind="grain", radius=0.55, centre=(0.0, 0.0), density=1.0,
          vessel=True):
    """Something tipped over and what came out of it. Ground origin.

    Two halves, and both are needed. The **cause** — a sack on its side, a
    holed bucket, a barrel on its end — because a patch of grain with nothing
    to have come out of is a texture decal, and the eye reads it as one. And
    the **spread**, which is dense at the mouth and thins outward with a few
    strays well beyond, because that is what a poured heap does.

    `kind` ∈ {grain, flour, coal, sand, apples, mud}.
    """
    from . import kit as K
    rng = rng_for(asset_id, "spill", kind)
    out = M.Group()
    cx, cz = centre

    # `cinder`, not `coal`. `coal` carries the EMISSIVE channel because it is
    # the blacksmith's live fire bed; spilling it lit a glowing orange heap on
    # the cobbles of anything that used it. Cold coal is `cinder`.
    spec = {
        "grain": ("straw", 0.016, 0.006, "sacking"),
        "flour": ("flour", 0.030, 0.004, "sacking"),
        "coal":  ("cinder", 0.045, 0.030, "oak_weathered"),
        "sand":  ("sand", 0.022, 0.005, "sacking"),
        "apples": ("terracotta", 0.038, 0.036, "oak"),
        "mud":   ("mud_wet", 0.055, 0.006, None),
    }
    mat, gsz, gh, vmat = spec.get(kind, spec["grain"])

    # The heap at the mouth. It has to have real VOLUME: the first version was
    # a 24 mm dome over a half-metre radius and read as a doily painted on the
    # paving. A poured heap stands at its angle of repose, which for grain is
    # about 30° — so the mound is a third as tall as it is wide, and the loose
    # grains below sit ON it rather than beside it.
    hh = radius * 0.30
    if kind != "mud":
        mound = M.lathe([(radius * 0.62, 0.0), (radius * 0.50, hh * 0.35),
                         (radius * 0.30, hh * 0.75), (0.0, hh)], 14, mat)
        mound.translate(cx, 0.0, cz)
        out.add(M.retex(mound, 3.0))

    # Grains are UNCHAMFERED, and that is a deliberate exception to Art Bible
    # §6, not an oversight. The smallest chamfer class in the table is 3 mm for
    # handheld metal; a 16 mm grain of wheat would need a sub-millimetre bevel
    # that is smaller than a texel at any distance a player sees it from, and
    # a chamfered box costs 44 triangles against 12. One spill at the density
    # this needs is the difference between 1.2k and 4.5k triangles for detail
    # nobody can resolve. Anything 25 mm or over keeps its bevel.
    ch = min(gh * 0.3, 0.002) if gsz >= 0.025 else 0.0
    n = int(np.clip(70 * density * (radius / 0.55) ** 1.4, 8, 150))
    for dx, dz in scatter(rng, n, radius, radius * 0.86, power=0.45):
        s = M.box(gsz * rng.uniform(0.6, 1.5), gh * rng.uniform(0.6, 1.6),
                  gsz * rng.uniform(0.6, 1.4), ch, mat)
        s.rotate_y(_yaw(rng))
        # Ride the mound's own cone where it is under them, so the loose grain
        # and the heap are one body of material rather than two props.
        d = float(np.hypot(dx / radius, dz / (radius * 0.86)))
        on_mound = max(0.0, 1.0 - d / 0.62) * hh if kind != "mud" else 0.0
        s.translate(cx + dx, on_mound + gh * 0.5, cz + dz)
        out.add(s)
    # Strays, well outside the main patch. A spill with a hard edge is a decal.
    for dx, dz in scatter(rng, max(3, n // 12), radius * 2.1, radius * 1.8, power=1.5):
        s = M.box(gsz * 0.9, gh * 0.8, gsz * 0.8, ch, mat)
        s.rotate_y(_yaw(rng))
        s.translate(cx + dx, gh * 0.4, cz + dz)
        out.add(s)

    if vessel and vmat:
        if kind in ("coal", "apples"):
            v = crate(f"{asset_id}.v", size=0.44, height=0.32, mat=vmat,
                      open_top=True)
            v.rotate_z(1.42)
            v.rotate_y(rng.uniform(-0.4, 0.4))
            v.translate(cx - radius * 0.62, 0.22, cz + radius * 0.28)
        else:
            v = K.sack(f"{asset_id}.v", height=0.50, mat=vmat)
            v.rotate_z(1.35)
            v.rotate_y(rng.uniform(0, 6.28))
            v.translate(cx - radius * 0.70, 0.17, cz + radius * 0.30)
        out.add(v)
    return out


def meal(asset_id, height=TABLE_H):
    """A half-eaten meal left on a board. Origin at the table TOP (`y = 0`).

    Interrupted, not laid out: the knife is in the cheese, the loaf has a heel
    torn off it rather than a slice cut, and the mug is not on the board at all
    but pushed to the side. A neatly set place reads as a still life; this
    reads as somebody who got up.
    """
    rng = rng_for(asset_id, "meal")
    out = M.Group()
    bd = M.plank(0.36, 0.26, 0.020, CH_PROP, "oak")
    bd.rotate_y(rng.uniform(-0.3, 0.3))
    bd.translate(0, 0.010, 0)
    out.add(bd)
    lf = M.globe(0.10, "bread", 8, 3, sx=1.25, sy=0.60, sz=0.85)
    lf.rotate_y(rng.uniform(-0.4, 0.4))
    lf.translate(-0.06, 0.020, -0.02)
    out.add(M.retex(lf, 2.0, 2.0, rng.uniform(0, 0.6)))
    # The torn heel, on the board beside it.
    hl = M.globe(0.045, "bread", 6, 3, sx=1.1, sy=0.75)
    hl.rotate_y(_yaw(rng))
    hl.translate(0.10, 0.020, 0.05)
    out.add(M.retex(hl, 2.4, 2.4, rng.uniform(0, 0.6)))
    ch = M.chamfered_prism([(0, 0), (0.11, 0.0), (0.075, 0.075), (0.0, 0.055)],
                           0.075, "sugar", CH_SMALL)
    ch.rotate_x(np.pi * 0.5)
    ch.rotate_y(rng.uniform(-0.5, 0.5))
    ch.translate(0.06, 0.020, -0.05)
    out.add(ch)
    kb = M.chamfered_prism([(0.0, -0.010), (0.13, -0.007), (0.15, 0.0),
                            (0.13, 0.009), (0.0, 0.014)], 0.003,
                           "steel_blued", 0.0012)
    kb.rotate_z(0.95)
    kb.rotate_y(0.6)
    kb.translate(0.055, 0.030, -0.045)
    out.add(kb)
    kh = M.cylinder(0.012, 0.075, 6, 0.002, "oak_dark")
    kh.rotate_z(0.95 - np.pi * 0.5)
    kh.rotate_y(0.6)
    kh.translate(0.028, 0.075, -0.075)
    out.add(kh)
    mg = mug(f"{asset_id}.mug", full=True)
    mg.translate(0.27 + rng.uniform(-0.03, 0.03), 0.0, 0.13 + rng.uniform(-0.03, 0.03))
    out.add(mg)
    for dx, dz in scatter(rng, 12, 0.20, 0.16):
        cr = M.box(0.010, 0.006, 0.008, 0.0015, "bread")
        cr.rotate_y(_yaw(rng))
        cr.translate(dx, 0.003, dz)
        out.add(cr)
    return out


def dice_on_barrel(asset_id, barrel_height=BARREL_H):
    """A game left on a barrel top. Origin at the GROUND under the barrel.

    Three dice, two of them together and one thrown clear, plus scattered coins
    and two mugs. The arrangement is the story: somebody threw, and then
    something happened. Dice pips are drilled recesses, not printed — Art Bible
    §2 bans printed marks and a drilled pip is what a real bone die has.
    """
    rng = rng_for(asset_id, "dice")
    from . import kit as K
    out = M.Group()
    out.add(K.barrel(f"{asset_id}.barrel", height=barrel_height))
    top = barrel_height + 0.004

    for i in range(3):
        s = 0.021
        d = M.box(s, s, s, 0.0035, "alabaster")
        d.rotate_y(_yaw(rng))
        d.rotate_x(rng.uniform(-0.03, 0.03))
        px = (rng.uniform(-0.06, -0.02) if i < 2 else rng.uniform(0.10, 0.17))
        pz = rng.uniform(-0.06, 0.06)
        d.translate(px, top + s * 0.5, pz)
        out.add(d)
        for k in range(int(rng.integers(1, 6))):
            p = M.lathe([(0.0028, 0.0), (0.0028, 0.0018)], 6, "cinder")
            p.translate(px + rng.uniform(-0.006, 0.006), top + s - 0.0005,
                        pz + rng.uniform(-0.006, 0.006))
            out.add(p)
    for i in range(7):
        c = M.lathe([(0.0105, 0.0), (0.0115, 0.0012), (0.0105, 0.0024)], 9, "brass")
        c.rotate_x(rng.uniform(-0.02, 0.02))
        c.translate(rng.uniform(-0.20, 0.20), top + 0.0012, rng.uniform(-0.20, 0.20))
        out.add(c)
    for sx in (-1, 1):
        m = mug(f"{asset_id}.mug{sx}", full=(sx > 0))
        m.translate(sx * 0.20 + rng.uniform(-0.02, 0.02), top,
                    -0.17 * sx + rng.uniform(-0.03, 0.03))
        out.add(m)
    return out


def worn_patch(asset_id, shape="cat", size=0.55, mat="grass_worn"):
    """The absence of something that is usually here. Ground origin, flat.

    A cat-shaped bare patch on a doorstep, or the polished arc a gate has swept
    across the yard, or the pale rectangle where a crate stood all summer. It
    is one of the cheapest props in the file and one of the most effective,
    because it implies a THING and a DURATION without modelling either.

    Emitted 8 mm proud of local zero so it never z-fights the ground it lies
    on; drape it with the surface it belongs to.

    `shape` ∈ {cat, arc, rect, path}.
    """
    rng = rng_for(asset_id, "worn", shape)
    out = M.Group()
    y = 0.008

    def blob(cx, cz, rx, rz, seg=9):
        pts = []
        for i in range(seg):
            a = 2 * np.pi * i / seg
            j = rng.uniform(0.82, 1.18)
            pts.append((cx + np.cos(a) * rx * j, cz + np.sin(a) * rz * j))
        m = M.chamfered_prism([(p[0], p[1]) for p in pts], 0.004, mat, 0.0015)
        m.rotate_x(-np.pi * 0.5)
        m.translate(0, y, 0)
        return m

    if shape == "cat":
        # A curled cat: body ellipse, a tail arc off it, and a notch where the
        # head tucks in. Nobody will identify it as a cat; everybody will read
        # it as "something lay here", which is the whole trick.
        out.add(blob(0, 0, size * 0.42, size * 0.34, 11))
        out.add(blob(size * 0.30, size * 0.20, size * 0.18, size * 0.13, 8))
        for i in range(5):
            t = i / 4.0
            a = -0.6 + t * 2.6
            out.add(blob(np.cos(a) * size * 0.45, np.sin(a) * size * 0.40,
                         size * 0.075, size * 0.075, 7))
    elif shape == "arc":
        for i in range(9):
            t = i / 8.0
            a = -0.9 + t * 1.8
            out.add(blob(np.sin(a) * size, np.cos(a) * size - size * 0.6,
                         size * 0.12, size * 0.12, 7))
    elif shape == "path":
        for i in range(7):
            out.add(blob(rng.uniform(-0.1, 0.1), -size + i * size * 0.33,
                         size * 0.30, size * 0.26, 8))
    else:
        m = M.box(size, 0.004, size * 0.7, 0.006, mat)
        m.rotate_y(rng.uniform(-0.08, 0.08))
        m.translate(0, y, 0)
        out.add(m)
    return out


def dust_film(asset_id, radius=1.5, mat="flour", centre=(0.0, 0.0), y=0.0,
              density=1.0, lobes=None):
    """Settled dust — a THIN film that breaks up as it thins outward.

    Art Bible §7's rule about dust is that it settles and it does not stop at
    an edge. `spill()` is the wrong tool for it and it is worth saying why,
    because it was used for exactly this and shipped: a spill is a poured HEAP
    and stands at its angle of repose, so `spill(radius=4.4)` builds a 1.3 m
    cone of flour in the street. Dust has no repose. It is four millimetres
    thick everywhere and its edge is not an edge at all — it is a scatter of
    islands that get smaller and further apart until they stop.

    So: one soft core lobe, a ring of smaller overlapping lobes at 0.5-0.9 R,
    and a thin outer scatter to about 1.5 R. All flat, 4 mm proud of `y`, and
    all one material — a bakery's flour, a mill's meal, a smithy's soot, ash
    round a hearth, sawdust round a bench.

    Origin is the centre of the fall, on the ground it settles on.
    """
    rng = rng_for(asset_id, "dust", mat)
    out = M.Group()
    cx, cz = centre
    R = float(radius)

    def lobe(px, pz, rx, rz, seg=10, t=0.004):
        pts = []
        for i in range(seg):
            a = 2 * np.pi * i / seg
            j = float(rng.uniform(0.72, 1.28))
            pts.append((px + np.cos(a) * rx * j, pz + np.sin(a) * rz * j))
        m = M.chamfered_prism(pts, t, mat, 0.0012)
        m.rotate_x(-np.pi * 0.5)
        m.translate(0.0, y + 0.004, 0.0)
        return m

    out.add(lobe(cx, cz, R * 0.46, R * 0.40, 12, 0.006))
    n_mid = lobes if lobes is not None else max(4, int(7 * density))
    for i in range(n_mid):
        a = 2 * np.pi * (i + rng.uniform(-0.25, 0.25)) / n_mid
        d = R * float(rng.uniform(0.45, 0.86))
        s = R * float(rng.uniform(0.14, 0.28))
        out.add(lobe(cx + np.cos(a) * d, cz + np.sin(a) * d * 0.88, s, s * 0.86, 9))
    for _dx, _dz in scatter(rng, int(9 * density) + 3, R * 1.45, R * 1.25,
                            power=1.6):
        s = R * float(rng.uniform(0.035, 0.085))
        out.add(lobe(cx + _dx, cz + _dz, s, s * 0.8, 7))
    return out


def firewood_stack(asset_id, length=2.2, height=1.05, depth=0.42, wall_z=None):
    """Split logs stacked in courses with cross-stacked ends. Ground origin.

    The ends are the reason this is a prop and not a box: a woodpile stands up
    because its ends are cross-stacked into piers, alternating direction each
    course. Get that right and the pile is self-evidently stable; leave it out
    and it is a rectangle of log ends that would fall over.
    """
    rng = rng_for(asset_id, "wood")
    out = M.Group()
    lr = 0.062
    rows = max(2, int(height / (lr * 2.05)))
    per = max(2, int(depth / (lr * 2.05)))
    for r in range(rows):
        y = lr + r * lr * 2.02
        # Middle: logs lying along X, cut ends facing out.
        for i in range(per):
            z = -depth * 0.5 + lr + i * lr * 2.02 + rng.uniform(-0.006, 0.006)
            lg = M.cylinder(lr * rng.uniform(0.82, 1.12), length - 0.86, 7,
                            CH_SMALL, "oak" if (r + i) % 3 else "oak_weathered")
            lg.rotate_z(np.pi * 0.5)
            lg.rotate_x(rng.uniform(-0.02, 0.02))
            lg.translate(length * 0.5 - 0.43, y, z)
            out.add(M.retex(lg, 1.6, 1.6, rng.uniform(0, 0.6)))
        # Cross-stacked piers at both ends, alternating direction per course.
        for sx in (-1, 1):
            along_z = (r % 2 == 0)
            m = max(2, int(0.42 / (lr * 2.05)))
            for k in range(per if along_z else m):
                lg = M.cylinder(lr * rng.uniform(0.85, 1.10), 0.42, 7, CH_SMALL,
                                "oak_weathered")
                if along_z:
                    lg.rotate_x(np.pi * 0.5)
                    lg.translate(sx * (length * 0.5 - 0.21) + rng.uniform(-0.01, 0.01),
                                 y, -depth * 0.5 + lr + k * lr * 2.02)
                else:
                    lg.rotate_z(np.pi * 0.5)
                    lg.translate(sx * (length * 0.5 - 0.21) + rng.uniform(-0.01, 0.01),
                                 y, -depth * 0.5 + lr + k * lr * 2.02)
                out.add(M.retex(lg, 1.6, 1.6, rng.uniform(0, 0.6)))
    if wall_z is not None:
        lo, hi = out.bounds()
        out.translate(0, 0, wall_z - float(hi[2]) - 0.02)
    return out


def kindling(asset_id, radius=0.34):
    """A loose heap of split kindling and bark. Ground origin.

    Deliberately unstacked: kindling is what has not been stacked yet, and the
    contrast between it and a neat woodpile a metre away is the thing that
    makes the woodpile read as deliberate.
    """
    rng = rng_for(asset_id, "kindling")
    out = M.Group()
    for dx, dz in scatter(rng, 34, radius, radius * 0.85, power=0.55):
        ln = rng.uniform(0.16, 0.34)
        st = M.chamfered_prism([(-0.014, 0), (0.014, 0), (0.011, ln), (-0.011, ln)],
                               0.020, "oak" if rng.random() < 0.6 else "oak_weathered",
                               0.002)
        st.rotate_z(np.pi * 0.5)
        st.rotate_x(rng.uniform(-0.35, 0.35))
        st.rotate_y(_yaw(rng))
        d = float(np.hypot(dx / radius, dz / max(radius * 0.85, 1e-6)))
        st.translate(dx, 0.016 + (1.0 - d) * 0.11 * rng.uniform(0.4, 1.0), dz)
        out.add(st)
    return out


def chopping_block(asset_id, height=0.46, radius=0.28, axe=True):
    """An end-grain block with the axe left standing in it. Ground origin.

    The axe IN the block, not beside it — that is where an axe lives between
    strokes, and the one detail that turns a stump into a job. The block top is
    hacked into a dish and the chips are all around it.
    """
    rng = rng_for(asset_id, "block")
    out = M.Group()
    blk = M.lathe([(radius, 0.0), (radius * 0.94, 0.07), (radius * 0.97, height - 0.05),
                   (radius * 0.90, height)], 14, "endgrain")
    out.add(M.retex(blk, 1.2))
    # The dish, hacked out of the top.
    dish = M.lathe([(radius * 0.86, height - 0.005), (radius * 0.4, height - 0.035),
                    (0.0, height - 0.045)], 12, "endgrain")
    out.add(dish)

    if axe:
        hd = M.chamfered_prism([(0.0, -0.035), (0.085, -0.055), (0.115, -0.020),
                                (0.118, 0.030), (0.085, 0.055), (0.0, 0.040)],
                               0.030, "steel_blued", CH_SMALL)
        hd.rotate_z(-0.30)
        hd.rotate_y(0.55)
        hd.translate(0.03, height + 0.005, -0.02)
        out.add(hd)
        out.add(_tool_handle((0.03, height + 0.01, -0.02),
                             (-0.20, height + 0.60, 0.16), 0.019, "oak"))
        # Split billet still on the block, half-open.
        for sx in (-1, 1):
            bl = M.chamfered_prism([(-0.055, 0), (0.055, 0), (0.045, 0.28),
                                    (-0.045, 0.28)], 0.075, "oak", 0.003)
            bl.rotate_z(sx * 0.12)
            bl.rotate_x(np.pi * 0.5)
            bl.translate(sx * 0.10, height + 0.038, 0.12)
            out.add(bl)
    for dx, dz in scatter(rng, 30, 0.85, 0.75, power=0.4):
        ch = M.chamfered_prism([(0, 0), (0.07, 0.016), (0.065, 0.040), (0.0, 0.030)],
                               0.024, "oak", 0.0015)
        ch.rotate_x(np.pi * 0.5)
        ch.rotate_y(_yaw(rng))
        ch.rotate_z(rng.uniform(-0.4, 0.4))
        ch.translate(dx, 0.010, dz)
        out.add(ch)
    return out


def water_butt(asset_id, height=1.05, belly=0.78, wall_z=0.0, x=0.0, downpipe=True):
    """A rainwater butt under a downpipe, green with algae. Ground origin.

    Wet-and-neglected, which is the opposite of every other barrel in town: the
    water is dark, the staves are stained to the fill line and green below it,
    and something is floating in it. If `downpipe` is on, the eaves gutter and
    its spout are built too — a butt collecting from nothing is a barrel that
    happens to be full.
    """
    from . import kit as K
    rng = rng_for(asset_id, "butt")
    out = M.Group()
    b = K.barrel(f"{asset_id}.body", height=height, belly=belly,
                 mat="timber_grey", hoop_mat="iron_pitted")
    b.translate(x, 0, wall_z - belly * 0.5 - 0.10)
    out.add(b)
    # Algae band at the fill line, on the OUTSIDE, where it splashes over.
    alg = M.ring(belly * 0.5 * 0.995, 0.16, "algae", 16)
    alg.translate(x, height * 0.74, wall_z - belly * 0.5 - 0.10)
    out.add(alg)
    out.add(K.water_disc(belly * 0.42, y=height * 0.80, depth=0.9, segments=18)
            .translate(x, 0, wall_z - belly * 0.5 - 0.10))
    # A leaf and a twig floating on it.
    for i in range(3):
        lf = M.box(0.055, 0.004, 0.035, 0.001, "leaf_oak")
        lf.rotate_y(_yaw(rng))
        lf.translate(x + rng.uniform(-0.2, 0.2), height * 0.803,
                     wall_z - belly * 0.5 - 0.10 + rng.uniform(-0.2, 0.2))
        out.add(lf)

    if downpipe:
        # Lead spout out of a timber gutter, discharging over the butt.
        sp = M.lathe([(0.045, 0.0), (0.050, 0.05), (0.048, 0.55)], 9, "lead",
                     close_bottom=False, close_top=False)
        sp.rotate_x(0.20)
        sp.translate(x, height * 1.15, wall_z - 0.20)
        out.add(sp)
        gt = M.chamfered_prism([(-0.075, 0.0), (0.075, 0.0), (0.075, 0.085),
                                (0.050, 0.085), (0.050, 0.030), (-0.050, 0.030),
                                (-0.050, 0.085), (-0.075, 0.085)], 0.90,
                               "oak_weathered", CH_SMALL)
        gt.rotate_y(np.pi * 0.5)
        gt.translate(x, height * 1.72, wall_z - 0.13)
        out.add(gt)
    # A dipping bucket beside it, and the wet ground under the overflow.
    out.add(bucket(f"{asset_id}.dip", full=False)
            .translate(x + belly * 0.5 + 0.24, 0.0, wall_z - 0.30))
    out.add(spill(f"{asset_id}.wet", kind="mud", radius=0.44, density=0.55,
                  centre=(x, wall_z - belly - 0.20), vessel=False))
    return out


def drying_herbs(asset_id, width=1.1, y=2.05, wall_z=0.0, bunches=6):
    """Bunches hung head-down from a rail under a ceiling or an eave.

    Head-down, because that is how you dry a herb and getting it upside down is
    the tell that somebody who knows made this. **Origin at the ground below
    the rail**, so it places like everything else.
    """
    rng = rng_for(asset_id, "herbs")
    from . import kit as K
    out = M.Group()
    rail = M.cylinder(0.022, width, 7, CH_SMALL, "oak_weathered")
    rail.rotate_z(np.pi * 0.5)
    rail.translate(0, y, wall_z - 0.14)
    out.add(rail)
    for sx in (-1, 1):
        br = M.chamfered_prism([(0, 0), (0.14, 0), (0, -0.12)], 0.024, "iron",
                               CH_SMALL)
        br.rotate_y(np.pi * 0.5)
        br.translate(sx * width * 0.46, y, wall_z - 0.07)
        out.add(br)
    for i in range(int(bunches)):
        x = -width * 0.40 + i * width * 0.80 / max(1, bunches - 1)
        x += rng.uniform(-0.02, 0.02)
        ln = rng.uniform(0.24, 0.40)
        bun = M.Group()
        for k in range(7):
            a = 2 * np.pi * k / 7 + rng.uniform(-0.2, 0.2)
            bun.add(M.tube((0, 0, 0),
                           (np.cos(a) * ln * 0.28, -ln, np.sin(a) * ln * 0.28),
                           0.006, "grass_dry", 4, 0.001))
        # Faded along the rail: the oldest bunches are at the dry end. All of
        # them fresh green is a bunch of herbs hung up this minute, which is
        # not what "drying" means.
        lc = K.leaf_cluster(f"{asset_id}.{i}", radius=ln * 0.34, count=7,
                            mat="foliage" if i >= bunches - 2 else "grass_dry",
                            droop=0.9)
        lc.rotate_x(np.pi)
        lc.translate(0, -ln * 0.72, 0)
        bun.add(lc)
        bun.add(M.ring(0.026, 0.014, "canvas_plain", 8).translate(0, -0.035, 0))
        bun.rotate_y(_yaw(rng))
        bun.rotate_z(rng.uniform(-0.06, 0.06))
        bun.translate(x, y - 0.025, wall_z - 0.14)
        out.add(bun)
    return out


def hanging_game(asset_id, width=0.9, y=2.10, wall_z=0.0, birds=3, hare=True):
    """Game hung on a rail outside a chophouse or a kitchen door.

    Hung by the feet, which is both correct and the reason the silhouette
    works — a row of long tapering shapes with the heads down catches the eye
    from the street. Origin at the ground under the rail.
    """
    rng = rng_for(asset_id, "game")
    out = M.Group()
    rail = M.cylinder(0.026, width, 7, CH_SMALL, "oak_dark")
    rail.rotate_z(np.pi * 0.5)
    rail.translate(0, y, wall_z - 0.18)
    out.add(rail)
    for sx in (-1, 1):
        out.add(_tool_handle((sx * width * 0.46, y, wall_z - 0.18),
                             (sx * width * 0.46, y + 0.04, wall_z), 0.016, "iron"))
    for i in range(int(birds)):
        x = -width * 0.34 + i * 0.24 + rng.uniform(-0.02, 0.02)
        out.add(M.tube((x, y - 0.02, wall_z - 0.18), (x, y - 0.14, wall_z - 0.17),
                       0.004, "canvas_plain", 4, 0.001))
        bd = M.globe(0.10, "fleece", 7, 3, sx=0.72, sy=1.45, sz=0.72)
        bd.rotate_z(rng.uniform(-0.10, 0.10))
        bd.translate(x, y - 0.16, wall_z - 0.17)
        out.add(bd)
        # Head hanging below, and a wing half open — a dead bird is not neat.
        hd = M.globe(0.038, "fleece", 6, 3, sy=1.2)
        hd.translate(x + 0.02, y - 0.40, wall_z - 0.16)
        out.add(hd)
        wg = M.chamfered_prism([(0, 0), (0.075, -0.03), (0.10, -0.13), (0.02, -0.10)],
                               0.006, "fleece", 0.0015)
        wg.rotate_y(rng.uniform(-0.4, 0.4))
        wg.translate(x + 0.05, y - 0.20, wall_z - 0.15)
        out.add(wg)
    if hare:
        x = width * 0.34
        out.add(M.tube((x, y - 0.02, wall_z - 0.18), (x, y - 0.10, wall_z - 0.17),
                       0.005, "canvas_plain", 4, 0.001))
        hb = M.globe(0.13, "hide_raw", 7, 4, sx=0.62, sy=1.9, sz=0.62)
        hb.rotate_z(0.06)
        hb.translate(x, y - 0.14, wall_z - 0.17)
        out.add(hb)
        for sx in (-1, 1):
            er = M.chamfered_prism([(0, 0), (0.030, 0.02), (0.026, 0.14), (0, 0.13)],
                                   0.005, "hide_raw", 0.0015)
            er.rotate_z(np.pi + sx * 0.20)
            er.translate(x + sx * 0.03, y - 0.48, wall_z - 0.16)
            out.add(er)
    return out


def beehive(asset_id, height=0.46, radius=0.26):
    """A straw skep on a low stand, with a flight board. Ground origin.

    A skep is a coiled straw basket upside down, which is why it shares its
    construction with `basket(weave="coil")` — the same coiled rope of straw
    bound with bramble. The flight board and the worn entrance are what make it
    a working hive rather than an ornament.
    """
    rng = rng_for(asset_id, "hive")
    out = M.Group()
    stand_h = 0.24
    for i in range(3):
        a = 2 * np.pi * i / 3
        out.add(_tool_handle((np.cos(a) * 0.18, stand_h, np.sin(a) * 0.18),
                             (np.cos(a) * 0.24, 0.0, np.sin(a) * 0.24),
                             0.026, "oak_weathered"))
    bd = M.lathe([(0.0, stand_h), (0.32, stand_h), (0.32, stand_h + 0.028),
                  (0.0, stand_h + 0.028)], 12, "oak_weathered")
    out.add(bd)
    n = max(5, int(height / 0.058))
    for i in range(n):
        t = (i + 0.5) / n
        rr = radius * float(np.cos(t * np.pi * 0.46)) + 0.02
        c = M.ring(rr, 0.062, "straw", 12)
        c.translate(rng.uniform(-0.004, 0.004), stand_h + 0.028 + t * height,
                    rng.uniform(-0.004, 0.004))
        out.add(M.retex(c, 2.4))
    cap = M.globe(0.075, "straw", 9, 3, sy=0.7)
    cap.translate(0, stand_h + 0.045 + height, 0)
    out.add(M.retex(cap, 2.4))
    # Bramble binding — the spiral that holds the coils together.
    for i in range(n * 3):
        t = i / (n * 3.0)
        a = t * n * 2.0 * np.pi
        rr = radius * float(np.cos(t * np.pi * 0.46)) + 0.024
        out.add(M.tube((np.cos(a) * rr, stand_h + 0.028 + t * height, np.sin(a) * rr),
                       (np.cos(a + 0.5) * rr, stand_h + 0.030 + t * height,
                        np.sin(a + 0.5) * rr), 0.004, "reed", 4, 0.001))
    # Entrance, cut in the coil at the front, and the alighting board.
    ent = M.box(0.10, 0.045, 0.055, 0.004, "cinder")
    ent.translate(0, stand_h + 0.062, -radius * 0.95)
    out.add(ent)
    alb = M.plank(0.20, 0.12, 0.016, CH_SMALL, "oak_weathered")
    alb.rotate_x(-0.10)
    alb.translate(0, stand_h + 0.032, -radius - 0.06)
    out.add(alb)
    out.rotate_y(_yaw(rng))
    return out


def dovecote_holes(asset_id, width=1.6, height=1.9, wall_z=0.0, rows=6, cols=5):
    """A panel of nesting holes with alighting ledges. Origin at the wall base.

    Applied to a wall face at `z = wall_z`: the holes are real recesses set
    back 0.22 m so they read as dark from the street, and every one has a
    ledge, because a pigeon has to land. The bottom two rows are stained pale —
    droppings, which is the honest detail and the reason a dovecote is always
    scrubbed white below its holes.
    """
    rng = rng_for(asset_id, "dovecote")
    out = M.Group()
    hw, hh = 0.16, 0.20
    y0 = height - rows * (hh + 0.10)
    for r in range(int(rows)):
        for c in range(int(cols)):
            # Every other row offset: a real dovecote courses its holes.
            off = (hw + 0.14) * 0.5 if r % 2 else 0.0
            x = -width * 0.5 + (c + 0.5) * width / cols + off
            if x > width * 0.5 - hw * 0.4:
                continue
            y = y0 + r * (hh + 0.10)
            rec = M.box(hw, hh, 0.24, 0.006, "cinder")
            rec.translate(x, y, wall_z + 0.12)
            out.add(rec)
            sur = M.box(hw + 0.055, hh + 0.055, 0.030, 0.006, "limewash")
            sur.translate(x, y, wall_z - 0.014)
            out.add(sur)
            lg = M.plank(hw + 0.16, 0.10, 0.020, CH_SMALL, "limewash")
            lg.rotate_x(-0.06)
            lg.translate(x, y - hh * 0.5 - 0.012, wall_z - 0.055)
            out.add(lg)
            if r < 2:
                st = M.box(hw + 0.16, 0.16, 0.004, 0.002, "limewash")
                st.translate(x + rng.uniform(-0.02, 0.02), y - hh * 0.5 - 0.14,
                             wall_z - 0.020)
                out.add(st)
    return out


# ---------------------------------------------------------------------------
# Dressing — one call, one convincing arrangement
# ---------------------------------------------------------------------------
# The reason this section exists: thirty venue agents each hand-placing their
# own clutter produce thirty visual languages, and no review pass can unpick
# that afterwards. A venue calls `dress_yard` and gets the town's idea of what
# a working yard looks like, the same one every other venue got.
#
# All of these use the same frame: **a wall along X at z = 0 with its face
# toward -Z, and the usable ground at negative z.** Build in that frame, then
# rotate and translate the result onto whichever wall you meant. The
# `ctx` argument is optional; pass it and the arrangement declares collision
# for the volumes a player could otherwise walk through.

TRADES = ("smith", "cooper", "carpenter", "baker", "chandler", "tanner",
          "bowyer", "fishmonger", "general")


def stack_against_wall(asset_id, items, wall_z=0.0, x0=-1.0, x1=1.0, gap=0.10):
    """Set a run of objects down along a wall, each one touching it.

    The rule this enforces is the boring one that everything depends on: each
    item is pushed back until its own measured bounding box touches `wall_z`,
    so nothing hovers 12 cm off the plaster and nothing is buried in it. Items
    are spaced along X with real gaps and a small forward jitter, because a run
    of objects flush to a line is the second-loudest generated tell after a
    perfect row.

    `items` is a list of geometries authored with their base at y = 0.
    """
    rng = rng_for(asset_id, "against")
    out = M.Group()
    items = [i for i in items if i is not None]
    if not items:
        return out
    widths = []
    for it in items:
        lo, hi = it.bounds()
        widths.append(float(hi[0] - lo[0]))
    total = sum(widths) + gap * (len(items) - 1)
    x = x0 + max(0.0, ((x1 - x0) - total)) * float(rng.uniform(0.0, 1.0))
    for it, w in zip(items, widths):
        lo, hi = it.bounds()
        it.translate(x + w * 0.5 - float((lo[0] + hi[0]) * 0.5),
                     0.0,
                     wall_z - float(hi[2]) - float(rng.uniform(0.02, 0.14)))
        out.add(it)
        x += w + gap * float(rng.uniform(0.6, 1.6))
    return out


def dress_threshold(asset_id, width=1.6, wall_z=0.0, ctx=None, mud=True):
    """The half-metre outside a door: the most-looked-at ground in any venue.

    Everything here is about feet. A boot scraper on the hinge side, mud tracked
    off it, a besom leaning where somebody swept and stopped, a worn arc where
    the door has swung across the step for a century, and a cat's patch in the
    sun. Nothing large: this dressing must never block the doorway, which is
    why every item sits outside a 0.95 m clear width.
    """
    rng = rng_for(asset_id, "threshold")
    out = M.Group()
    side = 1.0 if rng.random() < 0.5 else -1.0
    clear = 0.55                                   # half the §3 door opening

    out.add(boot_scraper(f"{asset_id}.scr", wall_z=wall_z,
                         x=side * (clear + 0.22)))
    out.add(broom(f"{asset_id}.broom", wall_z=wall_z,
                  x=-side * (clear + 0.30 + rng.uniform(0, 0.15))))
    # The arc the door sweeps, and a cat in the sun clear of it.
    arc = worn_patch(f"{asset_id}.arc", shape="arc", size=0.72, mat="cobble")
    arc.rotate_y(rng.uniform(-0.2, 0.2))
    arc.translate(0, 0, wall_z - 0.72)
    out.add(arc)
    cat = worn_patch(f"{asset_id}.cat", shape="cat", size=0.42, mat="grass_worn")
    cat.rotate_y(_yaw(rng))
    cat.translate(side * (clear + 0.55), 0, wall_z - 0.35)
    out.add(cat)
    if mud:
        out.add(spill(f"{asset_id}.mud", kind="mud", radius=0.42, density=0.5,
                      centre=(0.0, wall_z - 0.60), vessel=False))
    # A mug left on the step by whoever swept.
    out.add(mug(f"{asset_id}.mug", full=False)
            .translate(-side * (clear + 0.18), 0.0, wall_z - 0.16))
    if ctx is not None:
        ctx.collider("box", center=(side * (clear + 0.22), 0.15, wall_z - 0.20),
                     half=(0.20, 0.15, 0.13), tag="boot_scraper")
    return out


def dress_shopfront(asset_id, width=3.0, wall_z=0.0, trade="general", ctx=None,
                    sill_y=STALL_H):
    """Goods spilling out of a shop onto the street under the window sill.

    A shop that keeps all its stock indoors is a shop the player walks past. The
    arrangement is the one every trading street in the world makes: the biggest
    and least stealable things stand outside against the wall, sample goods sit
    on a board across two barrels at counter height, and the overflow is stacked
    where it does not block the door.

    `trade` selects what the goods ARE, which is the only thing that changes
    between a cooper's front and a chandler's — the grammar is identical, and
    that is what makes a street read as one street.
    """
    from . import kit as K
    rng = rng_for(asset_id, "shopfront", trade)
    out = M.Group()

    # Trestle board across two barrels: the display counter.
    bx = -width * 0.5 + 0.85 + rng.uniform(-0.1, 0.1)
    for sx in (-1, 1):
        b = K.barrel(f"{asset_id}.b{sx}", height=0.80)
        b.translate(bx + sx * 0.62, 0.0, wall_z - 0.55)
        out.add(b)
    board = M.plank(1.62, 0.62, 0.038, CH_PROP, "oak_weathered")
    board.rotate_y(rng.uniform(-0.03, 0.03))
    board.translate(bx, 0.82, wall_z - 0.55)
    out.add(board)

    goods = {
        "smith": lambda i: crate(f"{asset_id}.g{i}", size=0.30, height=0.20,
                                 open_top=True),
        "cooper": lambda i: bucket(f"{asset_id}.g{i}"),
        "carpenter": lambda i: basket(f"{asset_id}.g{i}", weave="spale",
                                      radius=0.19, height=0.22),
        "baker": lambda i: basket(f"{asset_id}.g{i}", weave="coil", radius=0.20,
                                  height=0.16, fill="loaves"),
        "chandler": lambda i: glazed_jar(f"{asset_id}.g{i}", height=0.26),
        "tanner": lambda i: cloth_bolt(f"{asset_id}.g{i}", length=0.52,
                                       radius=0.070, mat="leather"),
        "bowyer": lambda i: basket(f"{asset_id}.g{i}", weave="stake", radius=0.16,
                                   height=0.34),
        "fishmonger": lambda i: basket(f"{asset_id}.g{i}", weave="slath",
                                       radius=0.20, height=0.18),
        "general": lambda i: basket(f"{asset_id}.g{i}", weave="stake",
                                    radius=0.19, height=0.22,
                                    fill=("apples", "grain", "wool")[i % 3]),
    }
    mk = goods.get(trade, goods["general"])
    for i in range(3):
        g = mk(i)
        g.rotate_y(_yaw(rng))
        g.translate(bx - 0.52 + i * 0.52 + rng.uniform(-0.05, 0.05), 0.84,
                    wall_z - 0.55 + rng.uniform(-0.07, 0.07))
        out.add(g)

    # Overflow against the wall on the other side of the door.
    ox = width * 0.5 - 0.75
    out.add(stack_against_wall(
        f"{asset_id}.over",
        [crate_stack(f"{asset_id}.cs", count=3),
         sack_stack(f"{asset_id}.ss", count=3)],
        wall_z=wall_z, x0=ox - 0.75, x1=ox + 0.75, gap=0.12))

    # A hanging balance over the board, because goods sold by weight are weighed
    # in front of the customer, and it is the strongest vertical in the group.
    sc = hanging_scales(f"{asset_id}.sc", span=0.46, drop=0.30, reach=0.42)
    sc.translate(bx + 0.55, 2.05, wall_z - 0.42)
    out.add(sc)
    # And the residue: a stool nobody is sitting on and a tipped basket.
    out.add(stool(f"{asset_id}.stool")
            .translate(bx + 1.05, 0.0, wall_z - 0.95 + rng.uniform(-0.1, 0.1)))
    tip = basket(f"{asset_id}.tip", radius=0.20, height=0.24, weave="stake")
    tip.rotate_z(1.42)
    tip.rotate_y(_yaw(rng))
    tip.translate(bx - 1.15, 0.21, wall_z - 0.85)
    out.add(tip)

    if ctx is not None:
        for sx in (-1, 1):
            ctx.collider("cylinder", center=(bx + sx * 0.62, 0.40, wall_z - 0.55),
                         radius=0.33, height=0.82, tag="shopfront_barrel")
    return out


def dress_workbench(asset_id, trade="carpenter", length=2.2, wall_z=0.0,
                    ctx=None, bench_h=0.86):
    """A bench with a trade's work on it, mid-job. Origin on the ground, centred.

    The bench itself is the same everywhere in the town — a slab top on four
    splayed legs with a shelf under it — and what is ON it is the trade. That
    is deliberate: a joiner and a chandler in the same town buy their benches
    from the same joiner.

    The trade sets go in front of / around the bench rather than on it where the
    tool wants a floor (a cooper's raising-up, a tanner's beam), because those
    are floor work; the bench then carries the small work and the residue.
    """
    from . import kit as K
    rng = rng_for(asset_id, "bench", trade)
    out = M.Group()

    top = M.plank(length, 0.62, 0.070, CH_PROP, "oak_weathered")
    top.translate(0, bench_h, wall_z - 0.40)
    out.add(top)
    for sx in (-1, 1):
        for sz in (-1, 1):
            out.add(_tool_handle((sx * (length * 0.5 - 0.13), bench_h - 0.04,
                                  wall_z - 0.40 + sz * 0.22),
                                 (sx * (length * 0.5 - 0.05), 0.0,
                                  wall_z - 0.40 + sz * 0.30), 0.045, "oak_dark"))
    shelf = M.plank(length * 0.86, 0.42, 0.030, CH_PROP, "oak_weathered")
    shelf.translate(0, 0.30, wall_z - 0.42)
    out.add(shelf)
    # Bench dogs and a holdfast: what makes it a workbench and not a table.
    for i in range(3):
        dg = M.box(0.026, 0.075, 0.026, 0.002, "oak_dark")
        dg.translate(-length * 0.3 + i * 0.30, bench_h + 0.055,
                     wall_z - 0.40 + rng.uniform(-0.02, 0.02))
        out.add(dg)
    hf = M.Group()
    hf.add(M.tube((0, 0, 0), (0, 0.30, 0), 0.014, "iron", 5, 0.002))
    hf.add(M.tube((0, 0.30, 0), (-0.22, 0.24, 0.0), 0.012, "iron", 5, 0.002))
    hf.translate(length * 0.28, bench_h + 0.035, wall_z - 0.34)
    out.add(hf)

    # The trade's own station, placed in front of the bench.
    station = {
        "smith": smith_tools, "cooper": cooper_setup, "carpenter": carpenter_bench,
        "baker": baker_kit, "chandler": chandler_kit, "tanner": tanner_kit,
        "bowyer": bowyer_kit, "fishmonger": fishmonger_kit,
    }.get(trade)
    if station is not None:
        st = station(f"{asset_id}.{trade}", wall_z=wall_z)
        # Forward of the bench, turned slightly, so the two read as a working
        # area with a person-sized gap between them rather than as a wall of
        # stuff. 1.1 m is one comfortable pace plus a turn.
        st.rotate_y(rng.uniform(-0.22, 0.22))
        st.translate(rng.uniform(-0.2, 0.2), 0.0, -1.35)
        out.add(st)

    # Residue on the bench, the same three beats everywhere: a light left
    # burning, a mug, and something half-done pushed to one side.
    out.add(K.lantern(f"{asset_id}.lamp")
            .translate(-length * 0.5 + 0.16, bench_h + 0.02, wall_z - 0.24))
    out.add(mug(f"{asset_id}.mug", full=True)
            .translate(length * 0.5 - 0.22 + rng.uniform(-0.06, 0.06),
                       bench_h + 0.035, wall_z - 0.24 + rng.uniform(-0.05, 0.05)))
    out.add(stool(f"{asset_id}.stool", height=0.58, radius=0.16)
            .translate(rng.uniform(-0.4, 0.4), 0.0, wall_z - 1.05))
    # Offcuts and dust under the bench.
    out.add(spill(f"{asset_id}.dust",
                  kind={"baker": "flour", "smith": "coal",
                        "fishmonger": "sand"}.get(trade, "sand"),
                  radius=0.50, density=0.45,
                  centre=(rng.uniform(-0.5, 0.5), wall_z - 0.75), vessel=False))

    if ctx is not None:
        ctx.collider("box", center=(0, bench_h * 0.5, wall_z - 0.40),
                     half=(length * 0.5, bench_h * 0.5, 0.31), tag="workbench")
    return out


def dress_yard(asset_id, width=7.0, depth=5.5, trade="general", ctx=None,
               wall_z=0.0, waggon_load="barrels", laundry=True):
    """A whole working yard in one call.

    **Origin at the centre of the BACK WALL**, with the yard running away
    toward -Z for about `0.8 * depth`. Not the centre of the ground: every
    other builder here is placed against a wall, and an origin that agreed
    with the wall in some functions and with the floor in others is how a
    venue author ends up eyeballing offsets.

    `laundry=True` strings a line between the two SIDE walls at `x = ±width/2`
    and 2.85 m up. If the yard has no side walls that high, pass `False` — a
    washing line tied to nothing is the worst floating prop in the file
    because the eye follows the line straight to both ends.

    Composed the way a real yard composes itself, which is by CIRCULATION —
    everything is pushed to the edges because a cart has to get in and out, and
    the middle is the worn track it takes. That is the single decision that
    makes a yard read as used rather than as a shop window:

      - the back wall (z = wall_z) takes the tall stationary things: woodpile,
        water butt, leaning stock, the tool wall
      - the two sides take the working stations and the waggon
      - the middle stays clear except for a worn path and whatever was dropped
        crossing it
      - the laundry goes overhead, which is the only way to put life above
        eye level without another building

    `ctx` gets colliders for the waggon, the butt and the woodpile — the three
    things a player would otherwise walk through.
    """
    from . import kit as K
    rng = rng_for(asset_id, "yard", trade)
    out = M.Group()
    hw, hd = width * 0.5, depth * 0.5
    back = wall_z - 0.0

    # -- the worn track through the middle: laid FIRST so everything else
    #    reads as having been pushed out of its way.
    track = worn_patch(f"{asset_id}.track", shape="path", size=depth * 0.30,
                       mat="grass_worn")
    track.rotate_y(rng.uniform(-0.15, 0.15))
    track.translate(rng.uniform(-0.3, 0.3), 0.0, back - hd * 0.9)
    out.add(track)

    # -- back wall: woodpile, water butt, and stock leaning up -------------
    wood = firewood_stack(f"{asset_id}.wood", length=width * 0.34,
                          height=1.05, depth=0.42, wall_z=back)
    wood.translate(-hw + width * 0.20, 0.0, 0.0)
    out.add(wood)
    out.add(kindling(f"{asset_id}.kind", radius=0.34)
            .translate(-hw + width * 0.20 + width * 0.22, 0.0, back - 0.55))
    out.add(water_butt(f"{asset_id}.butt", wall_z=back, x=hw - 1.25))
    out.add(chopping_block(f"{asset_id}.block")
            .translate(-hw + 0.85, 0.0, back - 1.15))

    # -- left side: the trade's station, turned to face the yard ----------
    station = {
        "smith": smith_tools, "cooper": cooper_setup, "carpenter": carpenter_bench,
        "baker": baker_kit, "chandler": chandler_kit, "tanner": tanner_kit,
        "bowyer": bowyer_kit, "fishmonger": fishmonger_kit,
    }.get(trade)
    if station is not None:
        st = station(f"{asset_id}.{trade}", wall_z=0.0)
        st.rotate_y(np.pi * 0.5 + rng.uniform(-0.12, 0.12))
        st.translate(-hw + 0.35, 0.0, back - hd * 0.95)
        out.add(st)
    else:
        out.add(stack_against_wall(
            f"{asset_id}.gen",
            [crate_stack(f"{asset_id}.cs", 4), sack_stack(f"{asset_id}.ss", 5),
             K.barrel(f"{asset_id}.bar")],
            wall_z=back, x0=-hw + 0.5, x1=-hw + width * 0.42))

    # -- right side: haulage. A yard exists to get goods in and out. -------
    veh = rng.random()
    if veh < 0.45:
        v = waggon(f"{asset_id}.wag", load=waggon_load)
        v.rotate_y(np.pi * 0.5 + rng.uniform(-0.10, 0.10))
        v.translate(hw - 1.35, 0.0, back - hd * 0.85)
        vol = ("box", dict(center=(hw - 1.35, 0.75, back - hd * 0.85),
                           half=(1.0, 0.75, 1.85), rot_y=0.0, tag="waggon"))
    elif veh < 0.75:
        v = handcart(f"{asset_id}.cart")
        v.rotate_y(-np.pi * 0.35 + rng.uniform(-0.15, 0.15))
        v.translate(hw - 1.15, 0.0, back - hd * 0.75)
        vol = ("box", dict(center=(hw - 1.15, 0.55, back - hd * 0.75),
                           half=(0.75, 0.55, 0.75), tag="handcart"))
    else:
        v = sledge(f"{asset_id}.sledge")
        v.rotate_y(np.pi * 0.42)
        v.translate(hw - 1.10, 0.0, back - hd * 0.70)
        vol = ("box", dict(center=(hw - 1.10, 0.22, back - hd * 0.70),
                           half=(0.55, 0.22, 1.0), tag="sledge"))
    out.add(v)
    out.add(broken_wheel(f"{asset_id}.bw", wall_z=back, x=hw - 2.6))

    # -- overhead: laundry across the yard, and herbs under the eave ------
    if laundry:
        y = 2.85 + rng.uniform(-0.15, 0.15)
        out.add(laundry_line(f"{asset_id}.wash",
                             (-hw + 0.25, y, back - hd * 0.55),
                             (hw - 0.25, y - 0.10, back - hd * 1.15),
                             items=5))
    out.add(drying_herbs(f"{asset_id}.herbs", width=0.9, y=2.15, wall_z=back)
            .translate(-hw + width * 0.62, 0, 0))

    # -- the middle: only what was dropped crossing it --------------------
    out.add(bucket(f"{asset_id}.bkt")
            .translate(rng.uniform(-0.6, 0.6), 0.0, back - hd * 1.05))
    out.add(spill(f"{asset_id}.drop", kind="grain", radius=0.42, density=0.7,
                  centre=(rng.uniform(-0.9, 0.2), back - hd * 1.25)))
    out.add(worn_patch(f"{asset_id}.cat", shape="cat", size=0.46)
            .translate(hw - 0.7, 0.0, back - 0.55))
    out.add(beehive(f"{asset_id}.hive").translate(-hw + 0.55, 0.0, back - hd * 1.6))

    if ctx is not None:
        ctx.collider(vol[0], **vol[1])
        ctx.collider("cylinder", center=(hw - 1.25, 0.52, back - 0.50),
                     radius=0.42, height=1.05, tag="water_butt")
        ctx.collider("box", center=(-hw + width * 0.20, 0.52, back - 0.23),
                     half=(width * 0.17, 0.52, 0.23), tag="woodpile")
        ctx.collider("cylinder", center=(-hw + 0.85, 0.23, back - 1.15),
                     radius=0.30, height=0.46, tag="chopping_block")
    return out


# ---------------------------------------------------------------------------
# Re-exports — one import for the whole residue vocabulary
# ---------------------------------------------------------------------------
# `core/kit.py` shipped barrel, crate, sack, rope_coil, trestle_table, bench and
# lantern before this module existed and those names are used across the town.
# Rather than move them (and break every venue) or leave an author guessing
# which of two files a barrel is in, they are visible from here too.

def __getattr__(name):
    # `kit.__dict__` rather than `getattr(kit, name)`: kit forwards unknown
    # names here by the same mechanism, so getattr would bounce between the two
    # modules forever on a name that is in neither.
    from . import kit as K
    obj = K.__dict__.get(name)
    if obj is None:
        raise AttributeError(f"module 'core.props' has no attribute '{name}'")
    return obj
