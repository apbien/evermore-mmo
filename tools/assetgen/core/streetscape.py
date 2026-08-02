"""The furniture of the public realm.

`core/kit.py` owns how Hearthmere is CONSTRUCTED and `core/props.py` owns what
is LEFT LYING ABOUT. This owns the third category, which is neither: the
objects a town puts in its streets on purpose and then never moves — kerb
bollards, hitching posts, mounting blocks, troughs, lamp standards, finger
posts, the public well, boot scrapers, thresholds, gully stones, handrails.

They are here rather than inside `venues/streets.py` because every one of them
is wanted somewhere else. The inn wants a mounting block, the stables want a
rail and a trough, the pub wants a lamp, the quay wants bollards, the gates
want spur stones. A second copy of the hitching post is two different towns.

Art Bible §7 is the brief: *"Vertical interest every 8-10 m along any street:
a hanging sign, a banner, a lamp bracket, a first-floor overhang, a window
box."* BUILD_DIRECTIVE §5 lists the same objects under infrastructure. What
they have in common structurally is that they are all **placed by rule along a
network**, so they are all authored the same way:

* base at local `y = 0`, origin on the ground under the object's own footprint,
  so a caller places one with a single translate to `terrain.height(x, z)`;
* seeded from an asset id, so `ctx.instance` can carry them as rigid transforms
  and a review diff means something;
* built from `core/mesh.py` primitives only, chamfered per §6, and using
  materials that live in the `kit_props` / `kit_trim` atlases wherever the
  choice is free — a street with forty props on it cannot afford a draw call
  each.
"""

from __future__ import annotations

import numpy as np

from . import mesh as M
from . import kit as K
from .mathx import rng_for, jitter
from . import materials as MATS


# ---------------------------------------------------------------------------
# Kerbside stone
# ---------------------------------------------------------------------------

def bollard(asset_id, height=0.78, mat="stone", kind="stone"):
    """A post keeping wheels off a footway or a stall pitch.

    TOWN_PLAN J5 puts "a line of six bollards" across the market place's north
    mouth and J4 one at Kirkgate. The ones on paving are dressed stone; the
    ones in the lanes are a baulk of oak set on end. Both are worn round on
    top, because that is what a nave hub does to a post in two hundred years.
    """
    rng = rng_for(asset_id, "bollard")
    h = jitter(rng, height, 0.06)
    out = M.Group()
    if kind == "oak":
        b = M.box(0.185, h, 0.185, 0.022, mat)
        b.translate(0, h * 0.5, 0)
        out.add(b)
        out.add(M.lathe([(0.10, h), (0.085, h + 0.04), (0.0, h + 0.07)], 8, mat))
    else:
        out.add(M.lathe([(0.135, 0.0), (0.145, 0.05), (0.115, h * 0.72),
                         (0.108, h - 0.10), (0.078, h - 0.02), (0.0, h)], 10, mat))
    out.rotate_y(rng.uniform(0.0, 6.28))
    out.rotate_x(rng.uniform(-0.035, 0.035))
    return out


def spur_stone(asset_id, height=0.62, mat="stone"):
    """A wheel guard: the raking stone at a corner that takes the hub.

    TOWN_PLAN asks for spur stones at the gate jambs "deeply scored by nave
    hubs" and a chamfered corner stone at J4. A right-angled corner in a town
    where every load is on an iron tyre is a corner that would not survive a
    winter, and its absence is why generated street corners look like diagrams.
    """
    rng = rng_for(asset_id, "spur")
    h = jitter(rng, height, 0.05)
    prof = [(-0.19, 0.0), (0.23, 0.0), (0.19, h * 0.55), (0.09, h),
            (-0.13, h), (-0.19, h * 0.6)]
    m = M.chamfered_prism(prof, 0.32, mat, chamfer=0.022)
    m.rotate_y(rng.uniform(-0.06, 0.06))
    return M.Group().add(m)


def mounting_block(asset_id, height=0.62, mat="stone"):
    """Three worn steps beside the kerb: how anyone short gets onto a horse.

    Every inn, gate and market place in a horse town has one, and their absence
    is a thing a player cannot name but can feel.
    """
    rng = rng_for(asset_id, "mount")
    out = M.Group()
    n = 3
    for k in range(n):
        w = 0.92 - k * 0.045
        d = 0.86 - k * 0.24
        h = height * (k + 1) / n
        s = M.box(w, h, d, 0.024, mat)
        s.rotate_y(rng.uniform(-0.02, 0.02))
        s.translate(rng.uniform(-0.012, 0.012), h * 0.5,
                    -0.43 + d * 0.5 + rng.uniform(-0.01, 0.01))
        out.add(s)
    return out


def threshold_stone(asset_id, width=1.30, depth=0.62, rise=0.10, mat="stone"):
    """A doorstep worn hollow, deepest where the traffic actually crosses it.

    Art Bible §5's wear rule made structural. The hollow is off-centre because
    a door swings one way and people cut the corner, and that asymmetry is what
    stops it reading as a moulding. Placed at the door, level with the footway.
    """
    rng = rng_for(asset_id, "threshold")
    bias = rng.uniform(-0.18, 0.18)

    def hf(u, v):
        du = (u - 0.5 - bias * 0.5) * 2.0
        dv = (v - 0.46) * 2.0
        return rise - 0.048 * max(0.0, 1.0 - (du * du * 0.85 + dv * dv)) ** 0.75

    out = M.Group()
    out.add(M.sheet(width, depth, hf, nx=7, nz=5, mat=mat,
                    uv_fn=lambda x, z: (x * 0.5, z * 0.5)))
    body = M.box(width, rise, depth, 0.016, mat)
    body.translate(0, rise * 0.5 - 0.006, 0)
    out.add(body)
    out.rotate_y(rng.uniform(-0.012, 0.012))
    return out


def gully_stone(asset_id, mat="sett", iron="iron"):
    """Where a street channel empties: a dished stone box with forged bars.

    A gutter that runs downhill to nowhere is a moulding, not drainage. This is
    the "somewhere" — placed at the low point of a channel, which the street's
    own fall decides. Sits with its rim at y = 0, i.e. at channel invert level.
    """
    out = M.Group()
    for (dx, dz, sx, sz) in ((0, 0.30, 0.72, 0.12), (0, -0.30, 0.72, 0.12),
                             (0.30, 0, 0.12, 0.48), (-0.30, 0, 0.12, 0.48)):
        b = M.box(sx, 0.17, sz, 0.016, mat)
        b.translate(dx, -0.065, dz)
        out.add(b)
    floor = M.box(0.52, 0.09, 0.52, 0.012, mat)
    floor.translate(0, -0.21, 0)
    out.add(floor)
    for k in range(3):
        bar = M.box(0.50, 0.024, 0.032, 0.005, iron)
        bar.translate(0, -0.014, -0.15 + k * 0.15)
        out.add(bar)
    return out


# ---------------------------------------------------------------------------
# Horse furniture
# ---------------------------------------------------------------------------

def hitching_post(asset_id, height=1.12, mat="oak_weathered", iron="iron"):
    """A post with a forged ring — where a rider ties up outside a shop."""
    rng = rng_for(asset_id, "hitch")
    h = jitter(rng, height, 0.05)
    out = M.Group()
    p = M.box(0.135, h, 0.135, 0.014, mat)
    p.translate(0, h * 0.5, 0)
    out.add(p)
    out.add(M.lathe([(0.088, h), (0.072, h + 0.035), (0.0, h + 0.055)], 8, mat))
    r = M.ring(0.070, 0.018, iron, 10)
    r.rotate_x(np.pi * 0.5)
    r.translate(0.0, h - 0.24, 0.082)
    out.add(r)
    out.add(M.tube((0.0, h - 0.17, 0.055), (0.0, h - 0.24, 0.074), 0.011, iron, 5))
    out.rotate_y(rng.uniform(0, 6.28))
    return out


def hitching_rail(asset_id, length=2.8, height=1.02, mat="oak_weathered"):
    """Two posts and a rail: what a carter ties a team to. Rail runs +X."""
    rng = rng_for(asset_id, "rail")
    out = M.Group()
    for sx in (-1, 1):
        h = height + rng.uniform(-0.03, 0.03)
        p = M.box(0.13, h + 0.13, 0.13, 0.013, mat)
        p.rotate_z(rng.uniform(-0.02, 0.02))
        p.translate(sx * length * 0.5, (h + 0.13) * 0.5, 0)
        out.add(p)
    r = M.plank(length + 0.28, 0.115, 0.075, 0.008, mat)
    r.rotate_z(rng.uniform(-0.008, 0.008))
    r.translate(0, height, 0.008)
    out.add(r)
    return out


def horse_trough(asset_id, length=1.9, width=0.62, height=0.56, mat="stone"):
    """A hollowed block full of water on the kerb, green at the water line.

    TOWN_PLAN J3 makes the trough the reason the Fork has a kerbed island and
    the reason its corner is worn, so this is infrastructure, not dressing.
    """
    rng = rng_for(asset_id, "trough")
    out = M.Group()
    wall = 0.11
    for (dx, dz, sx, sz) in ((0, (width - wall) * 0.5, length, wall),
                             (0, -(width - wall) * 0.5, length, wall),
                             ((length - wall) * 0.5, 0, wall, width - wall * 2),
                             (-(length - wall) * 0.5, 0, wall, width - wall * 2)):
        b = M.box(sx, height, sz, 0.018, mat)
        b.translate(dx, height * 0.5, dz)
        out.add(b)
    floor = M.box(length - wall * 1.6, 0.16, width - wall * 1.6, 0.016, mat)
    floor.translate(0, 0.08, 0)
    out.add(floor)
    out.add(K.water_slab(length - wall * 2.3, width - wall * 2.3,
                         y=height - 0.10, depth=0.20))
    for sz in (-1, 1):
        band = M.box(length - wall * 2.0, 0.055, 0.026, 0.006, "algae")
        band.translate(0, height - 0.125, sz * (width * 0.5 - wall - 0.013))
        out.add(band)
    out.rotate_y(rng.uniform(-0.03, 0.03))
    return out


# ---------------------------------------------------------------------------
# Standing ironwork
# ---------------------------------------------------------------------------

def boot_scraper(asset_id, mat="iron"):
    """A forged blade between two stone cheeks, set beside a door.

    The cheapest possible evidence that people walk in from mud — which in
    Hearthmere they do everywhere except the market place. Ninety triangles.
    """
    out = M.Group()
    for sx in (-1, 1):
        c = M.box(0.075, 0.19, 0.105, 0.012, "stone", uv_scale=MATS.uv_detail("stone", 1, why="0.19 m member; the library's 2 m tile shows 10% of one tile here and reads as flat colour"))
        c.translate(sx * 0.112, 0.095, 0)
        out.add(c)
    blade = M.box(0.170, 0.026, 0.016, 0.004, mat)
    blade.translate(0, 0.163, 0)
    out.add(blade)
    return out


def lamp_post(asset_id, height=2.65, mat="iron", glass_mat="glass"):
    """A standard carrying a lantern, where no wall is near enough to hold one.

    Hearthmere lights its streets off brackets on the buildings; a standard is
    what you get where the building line steps back — a junction, an island, a
    green. Which is exactly where Art Bible §7 wants vertical interest anyway.
    """
    rng = rng_for(asset_id, "lamppost")
    h = jitter(rng, height, 0.04)
    out = M.Group()
    out.add(M.lathe([(0.135, 0.0), (0.145, 0.055), (0.085, 0.16),
                     (0.062, 0.28)], 9, "stone"))
    out.add(M.lathe([(0.052, 0.24), (0.043, h * 0.55), (0.036, h - 0.22),
                     (0.054, h - 0.15), (0.038, h - 0.11)], 8, mat))
    for a in (0.0, np.pi):
        out.add(M.tube((np.cos(a) * 0.038, h - 0.55, np.sin(a) * 0.038),
                       (np.cos(a) * 0.19, h - 0.20, np.sin(a) * 0.19), 0.013, mat, 5))
    lam = K.lantern(f"{asset_id}.lamp", mat=mat, glass_mat=glass_mat, scale=1.25)
    lam.translate(0, h - 0.11, 0)
    out.add(lam)
    out.rotate_y(rng.uniform(0, 6.28))
    return out


def signpost(asset_id, arms=2, height=2.35, mat="oak_weathered", iron="iron"):
    """A finger post whose boards carry CARVED DEVICES, never lettering.

    Art Bible §2 forbids readable text anywhere in the world, so the arm points
    and the boss on its end says what lies that way — the town's heron, a
    wheatsheaf for the mill, a ring for the quay. At the gameplay camera a
    board reads as a board and the device reads as an intention, which is the
    whole job of a signpost.
    """
    rng = rng_for(asset_id, "signpost")
    h = jitter(rng, height, 0.05)
    out = M.Group()
    p = M.box(0.145, h, 0.145, 0.015, mat)
    p.rotate_y(np.pi * 0.25)
    p.translate(0, h * 0.5, 0)
    out.add(p)
    out.add(M.lathe([(0.11, h), (0.09, h + 0.05), (0.0, h + 0.10)], 6, mat))
    prev = rng.uniform(0, 6.28)
    for k in range(int(arms)):
        y = h - 0.32 - k * 0.36
        a = prev if k == 0 else prev + rng.uniform(1.9, 2.7)
        prev = a
        board = M.chamfered_prism(
            [(0.0, -0.110), (0.60, -0.110), (0.76, 0.0), (0.60, 0.110), (0.0, 0.110)],
            0.034, mat, chamfer=0.008)
        board.rotate_x(-np.pi * 0.5)
        board.rotate_y(a)
        board.translate(np.sin(a) * 0.07, y, np.cos(a) * 0.07)
        out.add(board)
        boss = M.lathe([(0.0, 0), (0.052, 0.012), (0.052, 0.038), (0.0, 0.050)], 7, iron)
        boss.rotate_x(np.pi * 0.5)
        boss.rotate_y(a)
        boss.translate(np.sin(a) * 0.50, y, np.cos(a) * 0.50)
        out.add(boss)
    return out


def handrail(asset_id, length, height=0.95, mat="oak_weathered", iron="iron",
             posts=None):
    """An oak rail on forged standards, running +X. Art Bible §3: 0.95 m.

    Wanted wherever a flight is cut into a scarp. A public stair with a 1.5 m
    drop beside it and nothing to hold is the most obviously unfinished thing a
    street can have, and Hearthmere has five such flights.
    """
    rng = rng_for(asset_id, "handrail")
    out = M.Group()
    n = posts or max(2, int(round(length / 1.30)) + 1)
    for k in range(n):
        x = -length * 0.5 + length * k / max(n - 1, 1)
        st = M.box(0.042, height, 0.042, 0.006, iron)
        st.rotate_y(np.pi * 0.25)
        st.rotate_z(rng.uniform(-0.012, 0.012))
        st.translate(x, height * 0.5, 0)
        out.add(st)
        foot = M.box(0.13, 0.05, 0.13, 0.008, iron)
        foot.translate(x, 0.026, 0)
        out.add(foot)
    r = M.lathe([(0.0, -length * 0.5 - 0.08), (0.036, -length * 0.5 - 0.06),
                 (0.040, 0.0), (0.036, length * 0.5 + 0.06),
                 (0.0, length * 0.5 + 0.08)], 8, mat)
    r.rotate_z(np.pi * 0.5)
    r.translate(0, height, 0)
    out.add(r)
    return out


# ---------------------------------------------------------------------------
# Water, wood and waste
# ---------------------------------------------------------------------------

def well_head(asset_id, radius=0.66, mat="stone", iron="iron", oak="oak_weathered"):
    """A public draw-well: coped ring, oak frame, windlass, bucket, moss.

    BUILD_DIRECTIVE §5 lists a public well under infrastructure. A town of
    three hundred people whose water comes from nowhere visible is a set, not
    a settlement — and this is also the tallest thing on a lane of cottages, so
    it does §7's vertical-interest work at the same time.
    """
    rng = rng_for(asset_id, "well")
    out = M.Group()
    out.add(M.lathe([(radius, 0.0), (radius + 0.03, 0.10), (radius, 0.60),
                     (radius + 0.06, 0.68), (radius - 0.14, 0.72),
                     (radius - 0.17, 0.64), (radius - 0.17, 0.0)], 14, mat))
    for sx in (-1, 1):
        p = M.box(0.13, 1.55, 0.13, 0.014, oak)
        p.rotate_z(sx * 0.028)
        p.translate(sx * (radius - 0.02), 0.85, 0)
        out.add(p)
    beam = M.beam(radius * 2.4, 0.13, oak, 0.012)
    beam.translate(0, 1.60, 0)
    out.add(beam)
    drum = M.lathe([(0.0, -radius * 0.80), (0.10, -radius * 0.76), (0.115, 0.0),
                    (0.10, radius * 0.76), (0.0, radius * 0.80)], 9, oak)
    drum.rotate_z(np.pi * 0.5)
    drum.translate(0, 1.38, 0)
    out.add(drum)
    out.add(M.tube((radius - 0.02, 1.38, 0), (radius + 0.21, 1.38, 0), 0.019, iron, 5))
    out.add(M.tube((radius + 0.21, 1.38, 0), (radius + 0.21, 1.16, 0), 0.019, iron, 5))
    out.add(M.tube((0.0, 1.34, 0.02), (0.0, 0.80, 0.02), 0.011, "canvas", 5))
    bkt = M.lathe([(0.0, 0.0), (0.112, 0.02), (0.132, 0.30), (0.112, 0.32)],
                  10, oak, close_top=False)
    bkt.translate(0.0, 0.48, 0.02)
    out.add(bkt)
    hoop = M.ring(0.135, 0.021, iron, 10)
    hoop.translate(0.0, 0.72, 0.02)
    out.add(hoop)
    out.add(M.lathe([(radius + 0.006, 0.06), (radius + 0.014, 0.28)], 14, "moss",
                    close_bottom=False, close_top=False))
    out.rotate_y(rng.uniform(0, 6.28))
    return out


def water_butt(asset_id, height=0.96, belly=0.68, mat="oak_weathered", iron="iron"):
    """A rain butt under a spout, full, with a green tide mark inside."""
    rng = rng_for(asset_id, "butt")
    h = jitter(rng, height, 0.04)
    r = belly * 0.5
    out = M.Group().add(M.lathe(
        [(r * 0.86, 0), (r, h * 0.45), (r * 0.93, h)], 12, mat, close_top=False))
    for y in (0.07, h * 0.5, h - 0.06):
        hp = M.ring(r * 0.97, 0.028, iron, 12)
        hp.translate(0, y, 0)
        out.add(hp)
    # The water is a disc of ALGAE, not of `water`. A rain butt that has stood
    # under a spout all summer is green to the surface, so this is the more
    # accurate read anyway — and `water` is an 8 m-coverage animated material
    # that cannot go in an atlas, so twelve butts were costing twelve draw
    # calls for twenty-eight triangles.
    out.add(M.lathe([(0.0, h - 0.13), (r * 0.90, h - 0.135)], 12, "algae"))
    out.add(M.lathe([(r * 0.935, h - 0.20), (r * 0.935, h - 0.10)], 12, "algae",
                    close_bottom=False, close_top=False))
    out.rotate_y(rng.uniform(0, 6.28))
    return out


def woodpile(asset_id, length=2.3, height=1.00, depth=0.58, mat="oak",
             end="endgrain"):
    """A stack of split logs, ends out, under a scrap board.

    TOWN_PLAN §1: the Bailey "is where the town keeps its woodpiles". A wall of
    round end-grain catches the 09:30 key better than almost anything else at
    this scale, which is why it earns its place along a back lane.
    """
    rng = rng_for(asset_id, "wood")
    out = M.Group()
    # Deliberately coarse. A log seen end-on at 3 m is a disc 12 cm across, so
    # a five-sided barrel with one end cap carries all the information there
    # is: 23 triangles rather than 70. At 50 logs that is the difference
    # between a prop and a budget problem, and the pile is what reads, not the
    # log — Art Bible §6's "boring in silhouette" test is passed by the STACK.
    rows = max(2, int(height / 0.165))
    cols = max(3, int(length / 0.175))
    for j in range(rows):
        y = 0.075 + j * (height - 0.11) / max(rows - 1, 1)
        n = cols - (1 if j % 2 else 0)
        for i in range(n):
            x = -length * 0.5 + (i + 0.5 + (0.5 if j % 2 else 0.0)) * length / cols
            r = rng.uniform(0.055, 0.082)
            lg = M.lathe([(0.0, -depth * 0.5), (r, 0.0), (0.0, depth * 0.5)], 5, mat)
            lg.rotate_x(np.pi * 0.5)
            lg.rotate_y(rng.uniform(-0.06, 0.06))
            lg.translate(x, y + rng.uniform(-0.014, 0.014), rng.uniform(-0.02, 0.02))
            out.add(lg)
            cap = M.lathe([(0.0, 0.0), (r * 0.94, 0.006)], 5, end)
            cap.rotate_x(-np.pi * 0.5)
            cap.translate(x, y + rng.uniform(-0.014, 0.014), -depth * 0.5 + 0.02)
            out.add(cap)
    board = M.plank(length + 0.18, depth + 0.16, 0.032, 0.006, "timber_grey")
    board.rotate_x(rng.uniform(-0.05, -0.02))
    board.translate(0, height + 0.05, 0)
    out.add(board)
    return out


def midden(asset_id, radius=1.00, height=0.48):
    """A muck heap: straw, ash and sweepings, nettles round the foot.

    Every town before drains had these, exactly where TOWN_PLAN puts them — on
    the Bailey, behind the plots, downwind of everything that matters.
    """
    rng = rng_for(asset_id, "midden")
    out = M.Group()
    for k in range(9):
        a = rng.uniform(0, 6.28)
        d = radius * rng.uniform(0.0, 0.85)
        r = rng.uniform(0.26, 0.46)
        h = height * rng.uniform(0.5, 1.0) * (1.0 - d / (radius * 1.7))
        lump = M.globe(r, "straw" if rng.random() < 0.55 else "dirt", 7, 3,
                       sy=max(0.25, h / max(r, 1e-3)))
        lump.translate(np.cos(a) * d, max(0.06, h * 0.62), np.sin(a) * d)
        out.add(lump)
    return out


# ---------------------------------------------------------------------------
# Back-lane laundry
# ---------------------------------------------------------------------------

def laundry_prop(asset_id, height=3.30, mat="oak_weathered"):
    """The raking pole a washing line is tied to. Leans along local +X."""
    rng = rng_for(asset_id, "prop")
    h = jitter(rng, height, 0.05)
    out = M.Group()
    p = M.box(0.10, h, 0.10, 0.010, mat)
    p.rotate_z(-0.06)
    p.translate(0, h * 0.5, 0)
    out.add(p)
    for sx in (-1, 1):
        out.add(M.tube((-h * 0.06, h - 0.06, 0), (-h * 0.06 + sx * 0.15, h + 0.13, 0),
                       0.032, mat, 5))
    out.add(M.tube((0, h * 0.55, 0), (0.36, 0.0, 0.10), 0.036, mat, 5))
    return out


def hung_cloth(asset_id, width=0.72, drop=0.86, mat="linen"):
    """A sheet over a line: pegged at the top, sagging, rippled down the drop.

    Hung from y = 0 down to -`drop`, so a caller places it on the line it hangs
    from. Cloth materials are double-sided in the registry — a sheet has no
    back — and Art Bible §7 lists laundry under required motion, so the client
    animates anything in `SWAY_MATERIALS`.
    """
    rng = rng_for(asset_id, "cloth")
    fold = rng.uniform(0.6, 1.6)
    ph = rng.uniform(0, 3.1)
    amp = width * rng.uniform(0.05, 0.10)

    # `M.sheet` is a height field over the XZ plane, so the cloth is built
    # LYING DOWN and then stood up. Building it "hanging" by making the height
    # field itself descend gives a sheet whose x-span is the width and whose
    # z-span is the drop — a 45 degree flap, not a hanging cloth, which is
    # exactly how the first version rendered: three dark rhomboids on a string.
    def hf(u, v):
        return (amp * np.sin(u * np.pi * 2.0 * fold + ph) * (0.25 + 0.75 * v)
                + 0.045 * np.sin(np.pi * u) * (1.0 - v))

    m = M.sheet(width, drop, hf, nx=6, nz=5, mat=mat)
    m.rotate_x(-np.pi * 0.5)          # v = 0 (the line) is now the top edge
    m.translate(0, -drop * 0.5, 0)
    m.rotate_y(rng.uniform(-0.09, 0.09))
    return m


def washing_line(asset_id, p0, p1, sag=0.22, count=3, rope="canvas"):
    """A line between two anchors with cloths pegged along it.

    The single most effective thing that can be done to a back lane: it puts
    colour and movement at first-floor height, breaks a 20 m tunnel of wall
    into three bays, and says somebody lives here. TOWN_PLAN's Bell Alley note
    asks for it by name.
    """
    rng = rng_for(asset_id, "line")
    a = np.asarray(p0, np.float64)
    b = np.asarray(p1, np.float64)
    out = M.Group()
    out.add(M.catenary(a, b, sag, rope, 0.010, 8, 4))
    # Three colourways, not five: every extra cloth material is a draw call in
    # every cell an alley crosses, and three is already more variety than a
    # 21 m lane can show at once.
    mats = ("linen", "cloth_cream", "cloth_rust")
    for k in range(int(count)):
        t = (k + 0.5) / count + rng.uniform(-0.055, 0.055)
        t = float(np.clip(t, 0.08, 0.92))
        p = a + (b - a) * t + np.array([0.0, -sag * 4.0 * t * (1.0 - t), 0.0])
        w = rng.uniform(0.52, 0.86)
        dr = rng.uniform(0.55, 1.05)
        c = hung_cloth(f"{asset_id}.c{k}", w, dr, mats[int(rng.integers(0, len(mats)))])
        c.rotate_y(float(np.arctan2(b[0] - a[0], b[2] - a[2])) + np.pi * 0.5)
        c.translate(float(p[0]), float(p[1]) - 0.015, float(p[2]))
        out.add(c)
    return out
