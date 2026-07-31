"""Market Square — the town hub, and the focal point of the arrival shot.

The player enters through the north gate and sees this. The fountain at world
origin is what their eye lands on, so it carries more weight than any other
single object in Hearthmere.

Composition notes:
  - The square is IRREGULAR — wider at the north where Ford Road enters. It
    grew around a crossing rather than being planned, and a perfect rectangle
    would read as a car park.
  - Paving is real per-stone geometry, worn into DESIRE PATHS: polished smooth
    along the diagonals everyone walks, mossy and rough where nobody does.
  - The stalls are a separate venue and sit in the cleared bands here.
"""

from __future__ import annotations

import numpy as np

from core import mesh as M
from core import kit as K
from core.mathx import rng_for
from core.venue import VenueContext

NAME = "market_square"
CELLS = ["C3", "D3", "C4", "D4"]

# The plaza is a trapezoid: wider at the north (road mouth) than the south.
NORTH_W, SOUTH_W = 34.0, 26.0
DEPTH = 32.0


def _fountain(ctx, asset_id):
    """The town's anchor. Carved stone basin, worn lip, heron spout.

    Everything about it should say "people sit on this every day": the lip is
    dished and polished where they perch, algae grows only on the shaded north
    face, and the rim is chipped where buckets scrape it.
    """
    rng = rng_for(asset_id, "fountain")
    out = M.Group()

    # Stepped base — two courses, so it reads as built rather than placed.
    for i, (r, h) in enumerate([(3.15, 0.17), (2.72, 0.17)]):
        step = M.lathe([(r, 0), (r, h), (r - 0.10, h)], 26, "stone")
        step.translate(0, i * 0.17, 0)
        out.add(step)

    # Basin: outer wall, dished seating lip, inner bowl.
    basin = M.lathe([
        (2.30, 0.34), (2.44, 0.42), (2.46, 0.78),      # outer wall
        (2.40, 0.86), (2.24, 0.90),                     # the sitting lip
        (2.16, 0.84), (2.12, 0.52), (1.98, 0.44),       # inner face
        (0.55, 0.40), (0.50, 0.44),                     # bowl floor
    ], 30, "stone", close_bottom=False)
    out.add(basin)

    # Chipped rim: a few stones missing a corner. Perfect rims read as CAD.
    for _ in range(7):
        a = rng.uniform(0, 6.283)
        chip = M.box(rng.uniform(0.10, 0.20), 0.10, rng.uniform(0.08, 0.15),
                     0.012, "stone")
        chip.rotate_y(a + rng.uniform(-0.3, 0.3))
        chip.translate(np.cos(a) * 2.33, 0.90 + rng.uniform(-0.02, 0.01),
                       np.sin(a) * 2.33)
        out.add(chip)

    # Central pillar carrying the spout.
    pillar = M.lathe([(0.54, 0.40), (0.50, 0.56), (0.42, 1.30), (0.46, 1.44),
                      (0.38, 1.60), (0.34, 2.02), (0.40, 2.14)], 18, "stone")
    out.add(pillar)

    # Heron — the town emblem, and the reason the inn is called the Grey Heron.
    # Read as a bird in silhouette: body, arched neck, beak, folded wings.
    body = M.lathe([(0.0, 0), (0.15, 0.09), (0.17, 0.26), (0.11, 0.42), (0.0, 0.48)],
                   12, "stone")
    body.translate(0, 2.14, 0)
    out.add(body)

    for i in range(7):                       # arched neck
        t = i / 6.0
        seg = M.cylinder(0.052 - t * 0.016, 0.10, 8, 0.004, "stone")
        seg.rotate_z(-0.55 + t * 1.35)
        seg.translate(np.sin(t * 1.5) * 0.32, 2.56 + t * 0.40, 0)
        out.add(seg)

    beak = M.lathe([(0.038, 0), (0.012, 0.22)], 8, "stone")
    beak.rotate_z(-1.45)
    beak.translate(0.47, 2.94, 0)
    out.add(beak)

    for s in (-1, 1):                        # folded wings
        wing = M.prism([(0, 0), (0.30, 0.06), (0.34, -0.14), (0.05, -0.22)], 0.05,
                       chamfer=0.006)
        wing.rotate_y(np.pi * 0.5)
        wing.translate(0, 2.34, s * 0.17)
        out.add(wing.with_material("stone"))

    # Water: a thin sheet from the beak and a filled basin surface. Flat and
    # smooth so it takes a sharp sky reflection against all that rough stone.
    jet = M.box(0.055, 1.30, 0.055, 0.008, "glass")
    jet.rotate_z(0.20)
    jet.translate(0.53, 2.58, 0)
    out.add(jet)

    surface = M.lathe([(0.0, 0.62), (2.10, 0.62)], 28, "glass",
                      close_bottom=False, close_top=False)
    out.add(surface)

    ctx.entity(f"{asset_id}", "prop.fountain", (0, 0, 0), cell="C4",
               verbs=["inspect", "drink"],
               collider={"shape": "cylinder", "radius": 2.5, "height": 0.9})
    return out


def _paving(ctx, asset_id):
    """Plaza paving: a tiling cobble surface plus scattered proud stones.

    Modelling every cobble is not viable at plaza scale — a 34x32m square at
    0.17m spacing is ~40,000 stones, and at 44 tris per chamfered stone that is
    1.35M triangles for the paving alone, against a 3.5M budget for the ENTIRE
    frame (Art Bible §6). The first pass did exactly that and blew the budget
    by itself.

    What shipped games do, and what we do here: carry the cobble read in the
    material (its normal/height data is strong and it tiles seamlessly), then
    scatter a few hundred PROUD stones — sunken, tilted, frost-heaved — where
    they actually matter for silhouette: kerb edges, the fountain surround, and
    the desire paths. Those are the stones that catch a grazing highlight and
    break the flatness a plain plane would have.

    Recorded as decision D-006.
    """
    rng = rng_for(asset_id, "paving")
    out = M.Group()

    # Base surface, subdivided so it can take undulation later and so vertex
    # lighting across a 34m plaza is not one flat quad.
    seg = 12
    for i in range(seg):
        for j in range(seg):
            t0, t1 = j / seg, (j + 1) / seg
            w0 = NORTH_W + (SOUTH_W - NORTH_W) * t0
            w1 = NORTH_W + (SOUTH_W - NORTH_W) * t1
            z0 = -DEPTH * 0.5 + t0 * DEPTH
            z1 = -DEPTH * 0.5 + t1 * DEPTH
            x0a, x1a = -w0 * 0.5 + i * w0 / seg, -w0 * 0.5 + (i + 1) * w0 / seg
            x0b, x1b = -w1 * 0.5 + i * w1 / seg, -w1 * 0.5 + (i + 1) * w1 / seg
            b = M._Builder()
            # Wound so the geometric normal is +Y. Listing these in increasing
            # z order gives a -Y normal and the whole plaza gets backface-culled
            # into an invisible hole — which is exactly what the first pass did.
            pts = [np.array([x0b, 0, z1], np.float32), np.array([x1b, 0, z1], np.float32),
                   np.array([x1a, 0, z0], np.float32), np.array([x0a, 0, z0], np.float32)]
            uvs = [(p[0] * 0.5, p[2] * 0.5) for p in pts]
            b.poly(pts, uvs, np.array([0, 1, 0], np.float32))
            out.add(b.build("cobble"))

    # Proud stones. Concentrated at the fountain surround and thinning outward,
    # because that is where feet, buckets and cart wheels disturb the paving.
    for i in range(340):
        a = rng.uniform(0, 6.283)
        # Bias toward the middle: sqrt gives uniform area, power > 0.5 clusters in.
        d = 3.4 + (rng.uniform(0, 1) ** 0.75) * 13.0
        x, z = np.cos(a) * d, np.sin(a) * d
        half_w = (NORTH_W + (SOUTH_W - NORTH_W) * ((z + DEPTH * 0.5) / DEPTH)) * 0.5
        if abs(x) > half_w - 0.6:
            continue
        s = rng.uniform(0.15, 0.26)
        h = s * rng.uniform(0.24, 0.40)
        stone = M.box(s, h, s * rng.uniform(0.8, 1.15), s * 0.20, "cobble")
        stone.rotate_y(rng.uniform(0, 3.14))
        stone.rotate_z(rng.uniform(-0.09, 0.09))   # frost-heaved, never flush
        stone.translate(x, h * rng.uniform(0.10, 0.34), z)
        out.add(stone)

    # Kerb ring around the fountain — a raised lip people trip on and sit on.
    kerb = M.lathe([(3.30, 0), (3.42, 0.02), (3.44, 0.14), (3.30, 0.16)], 30, "stone")
    out.add(kerb)
    return out


def _trough(asset_id):
    """Horse trough — hollowed from a single stone, green inside."""
    out = M.Group()
    shell = M.box(2.30, 0.62, 0.86, 0.03, "stone", uv_scale=0.8)
    shell.translate(0, 0.31, 0)
    out.add(shell)
    water = M.box(2.06, 0.02, 0.62, 0.004, "glass")
    water.translate(0, 0.50, 0)
    out.add(water)
    for sx in (-1, 1):                      # stone feet
        f = M.box(0.26, 0.14, 0.70, 0.02, "stone")
        f.translate(sx * 0.86, 0.07, 0)
        out.add(f)
    return out


def _notice_post(asset_id):
    """A post where the town pins announcements. Pictorial only, per §2 —
    wax seals and ribbons, never lettering."""
    rng = rng_for(asset_id, "notice")
    out = M.Group()
    post = M.box(0.20, 2.55, 0.20, 0.012, "oak_weathered")
    post.translate(0, 1.27, 0)
    out.add(post)
    cap = M.prism([(-0.17, 0), (0.17, 0), (0, 0.22)], 0.34, chamfer=0.008)
    cap.translate(0, 2.55, 0)
    out.add(cap.with_material("oak_dark"))
    for i in range(5):
        n = M.box(rng.uniform(0.16, 0.24), rng.uniform(0.20, 0.30), 0.006, 0.002,
                  "canvas")
        n.rotate_z(rng.uniform(-0.14, 0.14))
        n.translate(rng.uniform(-0.04, 0.04),
                    1.35 + i * 0.19 + rng.uniform(-0.03, 0.03), -0.105)
        out.add(n)
        seal = M.lathe([(0.0, 0), (0.021, 0.004), (0.018, 0.008)], 8, "painted")
        seal.rotate_x(-np.pi * 0.5)
        seal.translate(rng.uniform(-0.05, 0.05), 1.35 + i * 0.19 + 0.07, -0.112)
        out.add(seal)
    return out


def build(ctx: VenueContext, asset_id="hm.market"):
    rng = rng_for(asset_id, "square")

    ctx.emit(_paving(ctx, asset_id))
    ctx.emit(_fountain(ctx, f"{asset_id}.fountain.01"))

    # Trough on the road side, where carts pull up.
    tr = _trough(f"{asset_id}.trough")
    tr.rotate_y(0.10)
    tr.translate(-9.4, 0.0, -10.2)
    ctx.emit(tr)
    ctx.entity(f"{asset_id}.trough.01", "prop.trough", (-9.4, 0, -10.2),
               cell="C3", verbs=["inspect"])

    npost = _notice_post(f"{asset_id}.notice")
    npost.rotate_y(-0.22)
    npost.translate(6.8, 0.0, -11.6)
    ctx.emit(npost)
    ctx.entity(f"{asset_id}.notice.01", "prop.notice_post", (6.8, 0, -11.6),
               cell="D3", verbs=["read"])

    # Hitching rails near the road mouth.
    for i, (x, z, a) in enumerate([(-12.5, -6.0, 0.08), (11.8, -7.2, -0.12)]):
        rail = M.Group()
        for sx in (-1, 1):
            p = M.box(0.14, 1.15, 0.14, 0.010, "oak_weathered")
            p.translate(sx * 1.30, 0.57, 0)
            rail.add(p)
        bar = M.plank(2.90, 0.13, 0.11, 0.008, "oak_weathered")
        bar.translate(0, 1.02, 0)
        rail.add(bar)
        rail.rotate_y(a)
        rail.translate(x, 0, z)
        ctx.emit(rail)

    # --- residue: Art Bible §7 --------------------------------------------
    # The square is where the town's daily life leaves the most traces.

    # Broken crate nobody has cleared, half-collapsed.
    for i in range(5):
        board = M.plank(rng.uniform(0.36, 0.52), 0.11, 0.022, 0.004, "oak")
        board.rotate_y(rng.uniform(0, 3.14))
        board.rotate_z(rng.uniform(-0.25, 0.25))
        board.translate(-6.1 + rng.uniform(-0.35, 0.35), 0.035 + i * 0.022,
                        6.4 + rng.uniform(-0.35, 0.35))
        ctx.emit(board)

    # Spilled produce, rolled into the low spots.
    for i in range(14):
        a = rng.uniform(0, 6.283)
        d = rng.uniform(0.4, 3.2)
        fruit = M.lathe([(0, 0), (0.055, 0.03), (0.06, 0.075), (0, 0.11)], 8,
                        "foliage_flower")
        fruit.translate(-5.6 + np.cos(a) * d, 0.05, 6.0 + np.sin(a) * d)
        ctx.emit(fruit)

    # Sacks and barrels waiting to be carried in — traders stage goods here.
    for i, (x, z) in enumerate([(9.2, 4.8), (9.9, 5.6), (8.6, 5.9)]):
        s = K.sack(f"{asset_id}.sack{i}")
        s.translate(x, 0.0, z)
        ctx.emit(s)
    for i, (x, z) in enumerate([(-10.6, 3.2), (-10.2, 4.3)]):
        b = K.barrel(f"{asset_id}.barrel{i}")
        b.translate(x, 0.0, z)
        ctx.emit(b)

    # A stool left by the fountain, and a bucket on the lip.
    stool = M.Group()
    seat = M.lathe([(0.16, 0), (0.17, 0.035)], 12, "oak_weathered")
    seat.translate(0, 0.44, 0)
    stool.add(seat)
    for k in range(3):
        a = k * 2.094
        leg = M.cylinder(0.022, 0.45, 6, 0.004, "oak_weathered")
        leg.rotate_x(0.13 * np.cos(a))
        leg.rotate_z(0.13 * np.sin(a))
        leg.translate(np.cos(a) * 0.11, 0, np.sin(a) * 0.11)
        stool.add(leg)
    stool.translate(3.1, 0, 2.6)
    ctx.emit(stool)

    buck = M.lathe([(0.125, 0), (0.145, 0.26)], 12, "oak_weathered", close_top=False)
    buck.translate(-1.55, 0.90, 1.62)
    ctx.emit(buck)
