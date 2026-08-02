"""Shared architectural kit.

This is the cohesion anchor. Seven agents building seven venues will produce
seven unrelated buildings unless they share a construction vocabulary — the
same wall build-up, the same roof pitch logic, the same door proportions, the
same hardware. Hearthmere reads as one settlement because every venue is
assembled from these pieces.

Extend this module rather than reimplementing a piece inside a venue. If a
venue needs a variant, add a parameter here so every venue can use it.

All dimensions follow the Art Bible §3 scale table. All edges are chamfered
per §6. Principal facades face -Z per the render convention.
"""

from __future__ import annotations

import math

import numpy as np

from . import materials as MAT
from . import mesh as M
from .mathx import rng_for, jitter

# Art Bible §3 constants — never hardcode these in a venue module.
DOOR_W, DOOR_H = 0.95, 2.10
FLOOR_H = 3.20
CEIL_H = 2.70
POST = 0.18
SILL_H = 0.95
CHAMFER_ARCH = 0.015
CHAMFER_PROP = 0.008

# How proud a MADE surface — carriageway, plaza, yard — sits above the unmade
# ground it is laid on. Two things need it and both need the same number:
#
#  1. A made surface draped flush onto `terrain.height()` is COPLANAR with the
#     terrain mesh, and the two z-fight into a mottled patchwork of paving and
#     mud. The market square shipped exactly that.
#  2. It has to clear the height field's own roughness (0.03-0.06 m) plus any
#     wear trough the surface carries, or the ground simply comes through.
#
# `venues/streets.py:ROAD_LIFT` is this number, derived there against Ford
# Road's 0.075 m worn trough. The square meets those streets, so it takes the
# same lift and the made surface stays continuous across the junction.
MADE_LIFT = 0.22


# ---------------------------------------------------------------------------
# Walls
# ---------------------------------------------------------------------------

def stone_plinth(width, depth, height=0.80, mat="stone"):
    """Coursed rubble base. Every building in Hearthmere sits on one — it
    keeps timber out of the wet, which is why it exists historically and why
    it reads as correct."""
    m = M.box(width, height, depth, 0.025, mat)
    m.translate(0, height * 0.5, 0)
    return m


def timber_frame_wall(width, height, asset_id, style="square", depth=0.22,
                      plaster_mat="plaster", timber_mat="oak", sill_y=0.0,
                      openings=None):
    """Timber-framed wall with plaster infill — the town's default construction.

    `style` selects the framing pattern, which is how we get visual variety
    across venues without changing the material vocabulary:
      square   — plain box framing (cottages, utilitarian)
      close    — close studding, posts at ~0.5m (wealthier: inn, guild annex)
      cross    — St-Andrew's cross bracing in each panel (pub, older stock)
      herring  — herringbone brick nogging between studs (shop row)

    `openings` is a list of (cx, cy, w, h) rectangles to leave clear so doors
    and windows can be placed without geometry interpenetrating.
    """
    rng = rng_for(asset_id, "wall", style, width, height)
    out = M.Group()
    openings = openings or []

    def blocked(x, y, w=0.16, h=0.16):
        for ox, oy, ow, oh in openings:
            if abs(x - ox) < (ow + w) * 0.5 and abs(y - oy) < (oh + h) * 0.5:
                return True
        return False

    # Plaster infill, set back from the frame face so the timber stands proud
    # and casts a real shadow line — that shadow is what makes a timber-framed
    # wall read at distance.
    #
    # The infill is SEGMENTED around the openings. Previously it was one solid
    # box and `openings` was consumed only by blocked(), which suppresses studs
    # — so no window or door in any timber-framed building in Hearthmere had an
    # aperture behind it. Every pane showed sunlit plaster through glass, which
    # is why the inn's windows measured -1.4 luminance against the wall across
    # three review rounds. Adding interior shells could never have helped;
    # there was nothing for them to be seen through.
    # A lime wall is not one mix. Every patch was run at a different time from
    # a different burn, and the value difference between them is what the eye
    # reads at 3 m — Art Bible §5's "uniform roughness is the single biggest
    # tell of amateur work", answered where it can be answered geometrically.
    #
    # A herringbone panel is BRICK, and `materials.LIBRARY` already carries a
    # `nogging` set that is herringbone brick. Laying it as geometry instead
    # cost 25,168 triangles on the parsonage alone — 56% of that building, for
    # a 0.085 m brick nobody resolves past 4 m, and it is why the parsonage
    # measured 38.6k against Art Bible §6's 30k standard-building budget.
    # The material carries the pattern; geometry carries only the relief.
    infill = "nogging" if style == "herring" else plaster_mat
    shade = plaster_mat if plaster_mat != "plaster" else "plaster_shade"
    for (rx, ry, rw, rh) in _subtract_rects(width, height, openings):
        pm = infill
        if style != "herring" and rng.random() < 0.24:
            pm = shade
        panel = M.box(rw, rh, depth * 0.55, CHAMFER_ARCH, pm,
                      uv_scale=MAT.uv_detail(
                          "nogging", 0.91,
                          why="a nogging panel between studs is 0.6-1.1 m wide "
                              "and the herringbone unit is a 0.085 m brick: at "
                              "the library's 2 m tile one panel shows a third "
                              "of one herringbone repeat, which reads as a "
                              "smear rather than as brick")
                      if style == "herring" else None)
        panel.translate(rx, sill_y + ry, 0)
        out.add(panel)

    zf = depth * 0.5 - POST * 0.5 + 0.02   # frame sits proud on the -Z face
    tm = timber_mat
    # A stud is TENONED INTO the rails, so the rails are the continuous members
    # and the stud sits back behind their face. 14 mm of setback is the whole
    # difference between a joint and two boxes interpenetrating with a seam
    # down the middle, which is what the art-director pass landed on first:
    # "every stud/rail crossing is two boxes interpenetrating, with a visible
    # seam and no shoulder, tenon or peg."
    zs = zf - 0.014
    pegs = []

    def post_at(x, y0, y1, w=POST, principal=False):
        h = y1 - y0
        if h <= 0.02:
            return
        p = M.box(w, h, POST, CHAMFER_ARCH, tm)
        p.uv = np.stack([p.v[:, 0] * 2.0, p.v[:, 1] * 0.5], axis=1).astype(np.float32)
        p.translate(x, sill_y + y0 + h * 0.5, -(zf if principal else zs))
        out.add(p)
        if principal:
            # Draw-bored pegs at the head and foot of a principal post. Only on
            # the principals: a peg at every one of fourteen close studs is
            # 3,700 triangles of detail nobody can resolve, and the joint that
            # actually carries load is the one worth showing.
            pegs.append((x, y0 + 0.09))
            pegs.append((x, y1 - 0.09))

    def rail_at(y, x0, x1, h=POST):
        """Horizontal member, broken where it would cross an opening.

        An unbroken rail running straight through a window is the same defect
        as the solid infill, one layer out.
        """
        spans = [(x0, x1)]
        for (ox, oy, ow, oh) in openings:
            if not (oy - oh * 0.5 <= y <= oy + oh * 0.5):
                continue
            nxt = []
            for (s0, s1) in spans:
                a, b = ox - ow * 0.5, ox + ow * 0.5
                if b <= s0 or a >= s1:
                    nxt.append((s0, s1)); continue
                if a - s0 > 0.02:
                    nxt.append((s0, a))
                if s1 - b > 0.02:
                    nxt.append((b, s1))
            spans = nxt
        for (s0, s1) in spans:
            w = s1 - s0
            if w <= 0.02:
                continue
            r = M.plank(w, POST, h, CHAMFER_ARCH, tm, grain_axis=0)
            r.translate(s0 + w * 0.5, sill_y + y, -zf)
            out.add(r)

    hw = width * 0.5
    # Sill and head plates run the full width — the primary horizontals.
    rail_at(POST * 0.5, -hw, hw)
    rail_at(height - POST * 0.5, -hw, hw)

    # Corner posts.
    post_at(-hw + POST * 0.5, 0, height, principal=True)
    post_at(hw - POST * 0.5, 0, height, principal=True)

    # Bays, at a JITTERED width. The frame style used to be chosen once per
    # building and then tiled at an exact spacing, which put fourteen identical
    # studs at fourteen identical centres across one facade — Art Bible §6's
    # "no element may appear more than 3 times in a row without a variant",
    # broken eleven times over, and it read as a picket fence.
    spacing = {"square": 1.35, "close": 0.52, "cross": 1.5, "herring": 0.62}[style]
    n = max(1, int(round(width / spacing)))
    raw = [1.0 + float(rng.uniform(-0.08, 0.08)) for _ in range(n)]
    tot = sum(raw)
    xs, acc = [-hw], -hw
    for r in raw:
        acc += width * r / tot
        xs.append(acc)
    xs[-1] = hw

    # Mid rail on taller walls — structurally necessary and breaks the panel.
    # It goes on close studding too: a 3 m close-studded wall without one is
    # not a frame, and its absence is exactly why `terrA` read as palings.
    my = None
    if height > 2.4:
        my = height * rng.uniform(0.50, 0.56)
        rail_at(my, -hw, hw, POST * 0.85)

    for i in range(1, n):
        x = xs[i]
        if blocked(x, height * 0.5, POST, height):
            continue
        w = POST * (0.85 if style == "close" else 1.0)
        principal = (style != "close") and (i % 3 == 0)
        if my is not None and not blocked(x, my, POST, POST * 2.0):
            # Broken at the mid rail, with the rail continuous through: the
            # shoulder is the joint.
            post_at(x, POST, my - POST * 0.42, w, principal)
            post_at(x, my + POST * 0.42, height - POST, w, principal)
        else:
            post_at(x, POST, height - POST, w, principal)

    # Bracing. A real frame is braced at its ANGLES and beside its openings —
    # where the racking load is — and left plain between. Bracing every bay
    # equally is what produced twelve identical X-panels across one facade.
    if style in ("cross", "square"):
        want = set()
        if style == "cross":
            want |= {0, n - 1}
            for (ox, _oy, ow, _oh) in openings:
                for i in range(n):
                    if xs[i] - 0.3 < ox < xs[i + 1] + 0.3:
                        want |= {max(0, i - 1), min(n - 1, i + 1)}
            if n >= 7:
                want.add(n // 2)
        else:
            want |= {0, n - 1}
        for i in sorted(want):
            x0 = xs[i] + POST * 0.5
            x1 = xs[i + 1] - POST * 0.5
            if x1 - x0 < 0.45:
                continue
            if blocked((x0 + x1) * 0.5, height * 0.5, x1 - x0, height):
                continue
            y0, y1 = POST, (my - POST * 0.5) if (my and style == "square") else height - POST
            if y1 - y0 < 0.5:
                continue
            signs = (1, -1) if style == "cross" else (1 if i == 0 else -1,)
            for sign in signs:
                dx, dy = (x1 - x0) * sign, (y1 - y0)
                ln = float(np.hypot(dx, dy))
                br = M.plank(ln, POST * 0.72, POST * 0.8, CHAMFER_ARCH, tm)
                br.rotate_z(float(np.arctan2(dy, dx)))
                br.translate((x0 + x1) * 0.5, sill_y + (y0 + y1) * 0.5, -zf - 0.012)
                out.add(br)

    if style == "herring":
        # RELIEF only — the herringbone itself is in the panel material above.
        # Three courses per panel stand proud so the pattern catches the sun at
        # a grazing angle and the panel is not a flat card; the other twenty-six
        # courses are texture, where a 0.085 m brick belongs.
        for i in range(n):
            cx = (xs[i] + xs[i + 1]) * 0.5
            step = xs[i + 1] - xs[i]
            if blocked(cx, height * 0.5, step, height):
                continue
            for r in range(3):
                y = POST + (height - 2 * POST) * (r + 0.5) / 3.0
                ang = 0.62 * (1 if r % 2 == 0 else -1)
                b = M.box(step * 0.78, 0.085, 0.055, 0.0, "nogging")
                b.rotate_z(ang)
                b.translate(cx, sill_y + y, -zf + 0.045)
                out.add(b)

    # Draw-bored pegs, last, so they sit on the finished joints. Two flats and
    # a stub: 20 triangles each, and the thing the eye lands on first at 2 m.
    for (px, py) in pegs:
        pg = M.cylinder(0.026, 0.055, 6, 0.0, tm)
        pg.rotate_x(-math.pi * 0.5)
        pg.translate(px, sill_y + py, -(zf + POST * 0.5) - 0.004)
        out.add(pg)

    return out


def _subtract_rects(width, height, openings):
    """Split a wall rect into panels that avoid the opening rects.

    Guillotine subtraction: carve the wall into horizontal bands at every
    opening's top and bottom edge, then split each band into spans that skip
    the openings crossing it. Axis-aligned and conservative, which is all a
    timber-framed wall needs — the openings are always rectangles between studs.

    Coordinates are wall-local: x centred on the wall, y from the sill.
    """
    if not openings:
        return [(0.0, height * 0.5, width, height)]

    hw = width * 0.5
    # Band edges from every opening's vertical extent, clamped to the wall.
    ys = {0.0, height}
    for (_, oy, _, oh) in openings:
        ys.add(max(0.0, oy - oh * 0.5))
        ys.add(min(height, oy + oh * 0.5))
    ys = sorted(ys)

    out = []
    for i in range(len(ys) - 1):
        y0, y1 = ys[i], ys[i + 1]
        if y1 - y0 < 0.02:
            continue
        ymid = (y0 + y1) * 0.5
        # Openings crossing this band, as x-spans.
        cuts = []
        for (ox, oy, ow, oh) in openings:
            if oy - oh * 0.5 <= ymid <= oy + oh * 0.5:
                cuts.append((max(-hw, ox - ow * 0.5), min(hw, ox + ow * 0.5)))
        cuts.sort()

        x = -hw
        for (c0, c1) in cuts:
            if c0 - x > 0.02:
                out.append(((x + c0) * 0.5, ymid, c0 - x, y1 - y0))
            x = max(x, c1)
        if hw - x > 0.02:
            out.append(((x + hw) * 0.5, ymid, hw - x, y1 - y0))
    return out


# Public name: every wall assembly needs this, not just the timber-framed one.
# A masonry wall with a window in it has exactly the same problem, and a second
# implementation of it is how two walls in the same town end up with openings
# that do not line up with their own frames.
subtract_rects = _subtract_rects


def jetty(width, depth, overhang=0.45, mat="oak_dark"):
    """Overhanging upper floor on carved brackets.

    Historically a way to gain floor area over the street; visually it is the
    single best silhouette-breaker available and creates a deep shadow line
    that separates storeys. Used on the inn and shop row.
    """
    out = M.Group()
    # Bressummer — the big beam carrying the overhang.
    beam = M.plank(width, 0.30, 0.26, CHAMFER_ARCH, mat)
    beam.translate(0, 0, -depth * 0.5 - overhang + 0.13)
    out.add(beam)
    # Brackets.
    n = max(2, int(width / 1.6))
    for i in range(n + 1):
        x = -width * 0.5 + i * (width / n)
        br = M.prism([(0, 0), (overhang, 0), (0, -0.42)], 0.14, chamfer=0.006)
        br.rotate_y(-np.pi / 2)
        br.translate(x, -0.02, -depth * 0.5 - overhang + 0.02)
        out.add(br.with_material(mat))
    return out


# ---------------------------------------------------------------------------
# Roofs
# ---------------------------------------------------------------------------


def _course_tint(mesh, rng, mat):
    """Per-course COLOR_0 for a laid covering. Art Bible §4: ~30% aged tiles.

    Tile-scale variance lives in the material; this is the COURSE-scale
    variance above it — a batch fired darker, a strip relaid after a leak.
    Without it a roof is one flat family whatever the texture does, because a
    4 m texture repeats several times up a single slope and repeats identically
    each time. COLOR_0 multiplies base colour, so it can only darken, which is
    the direction TERRACOTTA_AGED and a weathered slate both go.
    """
    aged = {"terracotta": 0.74, "slate": 0.80, "ridge": 0.78}.get(mat)
    if aged is None:
        return mesh
    if rng.random() < 0.30:
        f = aged * rng.uniform(0.96, 1.06)
    else:
        f = rng.uniform(0.93, 1.0)
    f = float(np.clip(f, 0.55, 1.0))
    return mesh.with_colour((f, f * 0.985, f * 0.95, 1.0))


def gable_roof(width, depth, asset_id, pitch=0.85, overhang=0.42,
               tile_mat="terracotta", timber_mat="oak_dark", ridge_height=None):
    """Pitched gable roof with real tile courses.

    A flat plane with a tile texture reads as wallpaper at grazing angles, so
    the courses are actual stepped geometry. That step is what catches the sun
    and gives a roof its characteristic saw-tooth edge against the sky.
    """
    rng = rng_for(asset_id, "roof")
    out = M.Group()
    w = width + overhang * 2
    d = depth + overhang * 2
    h = ridge_height if ridge_height is not None else (w * 0.5) * pitch

    # Tile courses, stepped up each slope.
    exposure = 0.16   # Art Bible §3
    slope_len = float(np.hypot(w * 0.5, h))
    courses = max(3, int(slope_len / exposure))
    # UVs at the covering's OWN coverage, and oriented so texture V runs UP the
    # slope. `M.box`'s planar projection put V along the RIDGE at a scale of
    # 1 m/tile against terracotta's authored 4 m — so the printed tile grid was
    # four times too fine AND turned 90 degrees against the modelled courses.
    # Every hero venue's roof went through here (only the building kit uses
    # `core/roof.py`), which is why measured coverage was 0.53-0.63 m per tile
    # on the inn, pub, blacksmith, guild and shop row. D-041.
    sc = MAT.uv_scale(tile_mat)
    for side in (-1, 1):
        for c in range(courses):
            t0 = c / courses
            t1 = (c + 1) / courses
            x0, y0 = side * (w * 0.5) * (1 - t0), h * t0
            x1, y1 = side * (w * 0.5) * (1 - t1), h * t1
            seg = float(np.hypot(x1 - x0, y1 - y0))
            # Each course is a thin slab, tilted to the slope, oversized so it
            # laps the course below.
            slab = M.box(seg * 1.22, 0.055, d, 0.010, tile_mat)
            # V = up-slope in the slab's own frame, U = along the ridge. Taken
            # before the rotation, so the course's own extent maps to its own
            # band of the texture and consecutive courses land on consecutive
            # bands rather than all sampling the same one.
            run = float(np.hypot(x0, y0 - h) if side < 0 else np.hypot(x0, y0 - h))
            slab.uv = np.stack([slab.v[:, 2] * sc,
                                (slab.v[:, 0] + run) * sc], axis=1).astype(np.float32)
            ang = float(np.arctan2(y1 - y0, x1 - x0))
            slab.rotate_z(ang)
            slab.translate((x0 + x1) * 0.5, (y0 + y1) * 0.5 + 0.028,
                           rng.uniform(-0.004, 0.004))
            out.add(_course_tint(slab, rng, tile_mat))

    # Ridge capping.
    ridge = M.lathe([(0.075, 0), (0.105, 0.055), (0.075, 0.11)], 10, tile_mat,
                    close_bottom=False, close_top=False)
    ridge.rotate_x(np.pi / 2).rotate_y(np.pi / 2)
    ridge.scale(1.0, 1.0, 1.0)
    cap = M.box(0.22, 0.10, d, 0.03, tile_mat, uv_scale=sc)
    cap.translate(0, h + 0.05, 0)
    out.add(cap)

    # Barge boards on the gable ends — the trim that finishes the silhouette.
    for z in (-d * 0.5 + 0.03, d * 0.5 - 0.03):
        for side in (-1, 1):
            ln = float(np.hypot(w * 0.5, h))
            bb = M.plank(ln, 0.06, 0.20, 0.006, timber_mat)
            bb.rotate_z(float(np.arctan2(h, -side * w * 0.5)))
            bb.translate(side * w * 0.25, h * 0.5 + 0.02, z)
            out.add(bb)

    return out


def gable_end(width, height_at_eaves, pitch=0.85, mat="plaster", depth=0.22):
    """The triangular wall filling a gable. Without it you see straight into
    the roof void, which is the classic unfinished-blockout tell."""
    hw = width * 0.5
    h = hw * pitch
    tri = M.prism([(-hw, 0), (hw, 0), (0, h)], depth, chamfer=0.0)
    tri.translate(0, height_at_eaves, 0)
    return tri.with_material(mat)


def chimney(asset_id, height=2.2, section=0.62, mat="stone", pot=True):
    """Stone stack with a clay pot. A roofline without chimneys reads as a
    model kit; they are the cheapest possible vertical interest."""
    rng = rng_for(asset_id, "chimney")
    out = M.Group()
    stack = M.box(section, height, section * 0.85, 0.02, mat)
    stack.translate(0, height * 0.5, 0)
    out.add(stack)
    # Corbelled cap — the stack widens at the top to throw water clear.
    cap = M.box(section * 1.22, 0.16, section * 1.05, 0.02, mat)
    cap.translate(0, height + 0.08, 0)
    out.add(cap)
    if pot:
        p = M.lathe([(0.13, 0), (0.145, 0.06), (0.135, 0.34), (0.155, 0.40)],
                    12, "terracotta", close_top=False)
        p.translate(rng.uniform(-0.03, 0.03), height + 0.16, rng.uniform(-0.03, 0.03))
        out.add(p)
    return out


# ---------------------------------------------------------------------------
# Openings
# ---------------------------------------------------------------------------

def plank_door(asset_id, width=DOOR_W, height=DOOR_H, mat="oak_weathered",
               iron_mat="iron", open_angle=0.0):
    """Ledged plank door with forged strap hinges.

    Art Bible §2: no screws. Straps are nailed and riveted, and they are the
    most readable "pre-industrial" cue on any building.
    """
    rng = rng_for(asset_id, "door")
    out = M.Group()
    nplanks = max(3, int(width / 0.21))
    pw = width / nplanks
    for i in range(nplanks):
        p = M.box(pw * 0.97, height, 0.045, 0.005, mat)
        p.uv = np.stack([p.v[:, 0] * 2.2, p.v[:, 1] * 0.55], axis=1).astype(np.float32)
        p.translate(-width * 0.5 + (i + 0.5) * pw, height * 0.5,
                    rng.uniform(-0.004, 0.004))
        out.add(p)
    # Ledges on the back.
    for y in (height * 0.18, height * 0.82):
        led = M.plank(width * 0.94, 0.09, 0.035, 0.004, mat)
        led.translate(0, y, 0.038)
        out.add(led)
    # Strap hinges.
    for y in (height * 0.18, height * 0.82):
        strap = M.box(width * 0.62, 0.075, 0.014, 0.004, iron_mat)
        strap.translate(-width * 0.5 + width * 0.31, y, -0.031)
        out.add(strap)
        pin = M.cylinder(0.032, 0.13, 10, 0.006, iron_mat)
        pin.rotate_x(np.pi / 2)
        pin.translate(-width * 0.5 + 0.03, y, -0.03)
        out.add(pin)
    # Ring handle.
    ring = M.lathe([(0.055, 0), (0.068, 0.012), (0.055, 0.024)], 14, iron_mat)
    ring.rotate_x(np.pi / 2)
    ring.translate(width * 0.32, height * 0.46, -0.045)
    out.add(ring)

    if open_angle:
        out.translate(width * 0.5, 0, 0)
        out.rotate_y(open_angle)
        out.translate(-width * 0.5, 0, 0)
    return out


def door_frame(width=DOOR_W, height=DOOR_H, mat="oak_dark", depth=0.26, lintel=True):
    out = M.Group()
    for sx in (-1, 1):
        j = M.box(0.11, height + 0.06, depth, CHAMFER_ARCH, mat)
        j.translate(sx * (width * 0.5 + 0.055), (height + 0.06) * 0.5, 0)
        out.add(j)
    if lintel:
        lt = M.plank(width + 0.34, depth, 0.20, CHAMFER_ARCH, mat)
        lt.translate(0, height + 0.16, 0)
        out.add(lt)
    # Threshold stone, dished by boots — a detail that reads as centuries of use.
    th = M.box(width + 0.20, 0.10, depth * 1.1, 0.02, "stone")
    th.translate(0, 0.05, 0)
    out.add(th)
    return out


def leaded_window(asset_id, width=0.82, height=1.05, mat="glass",
                  frame_mat="oak_dark", shutters=False, shutter_mat="painted"):
    """Small leaded lights in a timber frame. Art Bible §2: no plate glass."""
    rng = rng_for(asset_id, "window")
    out = M.Group()
    glass = M.box(width, height, 0.03, 0.004, mat)
    glass.translate(0, 0, 0.02)
    out.add(glass)
    # Frame + mullion + transom.
    for sx in (-1, 1):
        j = M.box(0.075, height + 0.15, 0.11, 0.006, frame_mat)
        j.translate(sx * (width * 0.5 + 0.037), 0, 0)
        out.add(j)
    for sy in (-1, 1):
        r = M.plank(width + 0.15, 0.11, 0.075, 0.006, frame_mat)
        r.translate(0, sy * (height * 0.5 + 0.037), 0)
        out.add(r)
    mull = M.box(0.05, height, 0.10, 0.005, frame_mat)
    out.add(mull)
    tran = M.plank(width, 0.10, 0.05, 0.005, frame_mat)
    out.add(tran)
    # Sill, sloped to throw water — and the source of the streaks below it.
    sill = M.box(width + 0.28, 0.07, 0.20, 0.008, "stone")
    sill.rotate_x(-0.09)
    sill.translate(0, -(height * 0.5 + 0.10), 0.05)
    out.add(sill)

    if shutters:
        for sx in (-1, 1):
            sh = M.Group()
            n = 4
            for i in range(n):
                b = M.box(width * 0.5 / n * 0.94, height * 0.98, 0.032, 0.004, shutter_mat)
                b.translate(-width * 0.25 + (i + 0.5) * (width * 0.5 / n), 0, 0)
                sh.add(b)
            for y in (-height * 0.36, height * 0.36):
                led = M.plank(width * 0.48, 0.07, 0.026, 0.003, shutter_mat)
                led.translate(0, y, 0.03)
                sh.add(led)
            # Hung open against the wall at a slight, uneven angle.
            ang = rng.uniform(0.18, 0.34) * sx
            sh.translate(sx * width * 0.25, 0, 0)
            sh.rotate_y(ang)
            sh.translate(sx * (width * 0.5 + 0.02), 0, -0.06)
            out.add(sh)
    return out


# ---------------------------------------------------------------------------
# Signage and fittings
# ---------------------------------------------------------------------------

def sign_bracket(asset_id, reach=0.85, mat="iron"):
    """Forged bracket with a scroll. Art Bible §2: signage is pictorial, and
    the bracket does as much identifying work as the board it carries."""
    out = M.Group()
    arm = M.box(reach, 0.045, 0.030, 0.005, mat)
    arm.translate(reach * 0.5, 0, 0)
    out.add(arm)
    stay = M.box(float(np.hypot(reach * 0.62, 0.42)), 0.032, 0.024, 0.004, mat)
    stay.rotate_z(float(np.arctan2(0.42, reach * 0.62)))
    stay.translate(reach * 0.31, -0.21, 0)
    out.add(stay)
    # Scroll curl at the end — the flourish that says "hand-forged".
    for i in range(7):
        t = i / 6.0
        r = 0.075 * (1 - t * 0.55)
        a = t * 3.6
        c = M.cylinder(0.011, 0.035, 6, 0.002, mat)
        c.rotate_x(np.pi / 2)
        c.translate(reach - 0.06 + np.cos(a) * r, 0.10 + np.sin(a) * r, 0)
        out.add(c)
    # Eyes the board hangs from.
    for x in (reach * 0.42, reach * 0.92):
        e = M.lathe([(0.018, 0), (0.026, 0.006), (0.018, 0.012)], 8, mat)
        e.rotate_x(np.pi / 2)
        e.translate(x, -0.03, 0)
        out.add(e)
    return out


def hanging_sign(asset_id, width=0.72, height=0.54, board_mat="painted",
                 iron_mat="iron", reach=0.85, sway=0.06):
    """Bracket + swinging board. `sway` is the resting tilt — a sign that hangs
    perfectly level looks welded, not hung."""
    out = M.Group()
    out.add(sign_bracket(asset_id, reach, iron_mat))
    board = M.Group().add(M.box(width, height, 0.038, 0.008, board_mat))
    frame = M.Group()
    for sy in (-1, 1):
        r = M.plank(width + 0.04, 0.045, 0.028, 0.004, iron_mat)
        r.translate(0, sy * height * 0.5, 0)
        frame.add(r)
    board.add(frame)
    # Chains.
    for x in (reach * 0.42, reach * 0.92):
        for k in range(3):
            lnk = M.lathe([(0.010, 0), (0.014, 0.004), (0.010, 0.008)], 6, iron_mat)
            lnk.rotate_x(np.pi / 2 if k % 2 else 0)
            lnk.translate(x, -0.05 - k * 0.032, 0)
            out.add(lnk)
    board.rotate_z(sway)
    board.translate(reach * 0.67, -0.16 - height * 0.5, 0)
    out.add(board)
    return out


def lantern(asset_id, mat="iron", glass_mat="glass", scale=1.0):
    """Wall lantern — oil, per Art Bible §2. Vertical interest every 8-10m
    along a street (§7), and the town's night lighting."""
    out = M.Group()
    body = M.lathe([(0.0, 0), (0.085, 0.02), (0.085, 0.06), (0.10, 0.075),
                    (0.10, 0.26), (0.075, 0.30), (0.02, 0.34)], 8, mat,
                   close_top=False)
    out.add(body)
    glass = M.lathe([(0.082, 0.075), (0.082, 0.26)], 8, glass_mat,
                    close_bottom=False, close_top=False)
    out.add(glass)
    ring = M.lathe([(0.028, 0.34), (0.036, 0.352), (0.028, 0.364)], 8, mat)
    out.add(ring)
    out.scale(scale)
    return out


# ---------------------------------------------------------------------------
# Common props
# ---------------------------------------------------------------------------

def barrel(asset_id, height=0.88, belly=0.62, mat="oak_weathered", hoop_mat="iron"):
    """Art Bible §3: 0.88m x 0.62m. Staves bulge; hoops are iron, not machined."""
    rng = rng_for(asset_id, "barrel")
    h = jitter(rng, height, 0.03)
    r = belly * 0.5
    rt = r * 0.84
    out = M.Group().add(M.lathe([(rt, 0), (r * 0.97, h * 0.22), (r, h * 0.5),
                                 (r * 0.97, h * 0.78), (rt, h)], 16, mat))
    for y in (h * 0.09, h * 0.30, h * 0.70, h * 0.91):
        rr = rt + (r - rt) * (1.0 - abs(y / h - 0.5) * 2.0) ** 0.6
        hoop = M.lathe([(rr + 0.006, y - 0.026), (rr + 0.014, y - 0.020),
                        (rr + 0.014, y + 0.020), (rr + 0.006, y + 0.026)], 16,
                       hoop_mat, close_bottom=False, close_top=False)
        out.add(hoop)
    out.rotate_y(rng.uniform(0, 6.28))
    return out


def crate(asset_id, size=0.55, mat="oak"):
    """Art Bible §3: 0.55m cube. Nailed boards, never a smooth box."""
    rng = rng_for(asset_id, "crate")
    s = jitter(rng, size, 0.04)
    out = M.Group()
    t = 0.026
    for axis in range(3):
        for sign in (-1, 1):
            n = 4
            for i in range(n):
                if axis == 1:
                    b = M.box(s, t, s / n * 0.94, 0.004, mat)
                    b.translate(0, sign * s * 0.5, -s * 0.5 + (i + 0.5) * s / n)
                elif axis == 0:
                    b = M.box(t, s, s / n * 0.94, 0.004, mat)
                    b.translate(sign * s * 0.5, 0, -s * 0.5 + (i + 0.5) * s / n)
                else:
                    b = M.box(s / n * 0.94, s, t, 0.004, mat)
                    b.translate(-s * 0.5 + (i + 0.5) * s / n, 0, sign * s * 0.5)
                out.add(b)
    # Corner battens.
    for sx in (-1, 1):
        for sz in (-1, 1):
            b = M.box(0.045, s * 1.01, 0.045, 0.004, mat)
            b.translate(sx * s * 0.5, 0, sz * s * 0.5)
            out.add(b)
    out.translate(0, s * 0.5, 0)
    out.rotate_y(rng.uniform(-0.25, 0.25))
    return out


def sack(asset_id, height=0.55, mat="cloth_cream", segments=8, tie=True):
    """Grain sack — slumped, never a neat cylinder.

    Two things stop this reading as a giant onion, which is what the
    twelve-segment smooth-shouldered version did at gameplay distance:

    **Eight segments, not twelve.** A full sack is a flat-bottomed tube of
    coarse cloth pulled into corners by whatever is in it, so it is faceted,
    not turned. Twelve segments smooth those corners away and the silhouette
    becomes a dome.

    **A real gathered neck.** The cloth above the tie flares back out into a
    stub with a rope round it. Without it the sack tapers to a point and the
    point reads as a stalk — the single strongest onion cue.
    """
    rng = rng_for(asset_id, "sack")
    h = jitter(rng, height, 0.08)
    r = h * 0.42
    out = M.Group()
    # Flat base with a real edge, straight-ish sides bellying out at a third
    # height, shoulders pulled in to the tie.
    prof = [(0.0, 0.0), (r * 0.80, 0.0), (r * 0.86, h * 0.05),
            (r * 1.00, h * 0.32), (r * 0.99, h * 0.58),
            (r * 0.80, h * 0.80), (r * 0.42, h * 0.92)]
    body = M.lathe(prof, segments, mat, close_bottom=False, close_top=False)
    out.add(body)
    if tie:
        out.add(M.lathe([(r * 0.42, h * 0.92), (r * 0.30, h * 0.955),
                         (r * 0.40, h * 1.00), (r * 0.34, h * 1.06)],
                        segments, mat, close_bottom=False))
        out.add(M.ring(r * 0.315, r * 0.16, "canvas_plain", segments + 2)
                .translate(0, h * 0.955, 0))
    # Squash off-axis so it reads as soft goods under its own weight.
    out.scale(1.0 + rng.uniform(0, 0.14), 1.0, 1.0 - rng.uniform(0, 0.12))
    out.rotate_y(rng.uniform(0, 6.28))
    return out


def rope_coil(asset_id, radius=0.22, mat="canvas"):
    rng = rng_for(asset_id, "rope")
    out = M.Group()
    for k in range(3):
        r = radius * (1 - k * 0.14)
        seg = 14
        for i in range(seg):
            a = i / seg * 2 * np.pi
            c = M.cylinder(0.022, 2 * np.pi * r / seg * 1.1, 5, 0.003, mat)
            c.rotate_z(np.pi / 2)
            c.rotate_y(-a)
            c.translate(np.cos(a) * r, 0.024 + k * 0.045, np.sin(a) * r)
            out.add(c)
    out.rotate_y(rng.uniform(0, 6.28))
    return out


def trestle_table(asset_id, length=1.9, width=0.72, height=0.74, mat="oak_weathered"):
    """Art Bible §3: table 0.74m."""
    out = M.Group()
    top = M.Group()
    n = 5
    for i in range(n):
        p = M.plank(length, width / n * 0.96, 0.042, 0.005, mat)
        p.translate(0, height, -width * 0.5 + (i + 0.5) * width / n)
        top.add(p)
    out.add(top)
    for sx in (-1, 1):
        x = sx * length * 0.36
        leg = M.prism([(-0.28, 0), (0.28, 0), (0.09, height - 0.05), (-0.09, height - 0.05)],
                      0.07, chamfer=0.005)
        leg.rotate_y(np.pi / 2)
        leg.translate(x, 0, 0)
        out.add(leg.with_material(mat))
    rail = M.plank(length * 0.72, 0.09, 0.05, 0.005, mat)
    rail.translate(0, height * 0.42, 0)
    out.add(rail)
    return out


def bench(asset_id, length=1.9, height=0.45, mat="oak_weathered"):
    """Art Bible §3: bench seat 0.45m."""
    out = M.Group()
    seat = M.plank(length, 0.30, 0.045, 0.005, mat)
    seat.translate(0, height, 0)
    out.add(seat)
    for sx in (-1, 1):
        leg = M.prism([(-0.15, 0), (0.15, 0), (0.07, height), (-0.07, height)], 0.055, chamfer=0.004)
        leg.rotate_y(np.pi / 2)
        leg.translate(sx * length * 0.35, 0, 0)
        out.add(leg.with_material(mat))
    return out


# ---------------------------------------------------------------------------
# Vegetation
# ---------------------------------------------------------------------------

def leaf_cluster(asset_id, radius=0.11, count=7, mat="foliage", droop=0.35):
    """A tuft of real leaf blades.

    Lathed cones read as low-poly crystals, which is what the first cottage
    pass produced. Actual leaf geometry — flat tapered blades, splayed and
    drooping at varied angles — is what makes a planter read as alive.
    """
    rng = rng_for(asset_id, "leaves")
    out = M.Group()
    for i in range(count):
        a = (i / count) * 2 * np.pi + rng.uniform(-0.35, 0.35)
        ln = radius * rng.uniform(1.5, 2.6)
        wd = radius * rng.uniform(0.34, 0.52)
        # Tapered blade: wide at the base, pointed at the tip.
        blade = M.prism([(0.0, 0.0), (wd * 0.5, ln * 0.22), (wd * 0.42, ln * 0.62),
                         (0.0, ln), (-wd * 0.42, ln * 0.62), (-wd * 0.5, ln * 0.22)],
                        0.006, chamfer=0.0)
        blade.rotate_x(np.pi * 0.5 - rng.uniform(0.5, 1.25) * droop)
        blade.rotate_y(a)
        blade.translate(np.cos(a) * radius * 0.16, 0, np.sin(a) * radius * 0.16)
        out.add(blade.with_material(mat))
    return out


def planter_plants(asset_id, width, count=5, mat="foliage_flower", height=0.11):
    """A row of leaf clusters for a window box or trough."""
    rng = rng_for(asset_id, "planter")
    out = M.Group()
    for i in range(count):
        t = (i + 0.5) / count
        c = leaf_cluster(f"{asset_id}.{i}", radius=rng.uniform(0.085, 0.13),
                         count=int(rng.integers(6, 9)), mat=mat)
        c.scale(1.0, rng.uniform(0.85, 1.25), 1.0)
        c.rotate_y(rng.uniform(0, 6.28))
        c.translate(-width * 0.5 + t * width + rng.uniform(-0.025, 0.025),
                    height, rng.uniform(-0.03, 0.03))
        out.add(c)
    return out


def thatch_roof(width, depth, asset_id, pitch=1.05, overhang=0.55,
                thickness=0.38, mat="thatch", segments=10):
    """Thick reed thatch: one smooth extruded shell with rolled eaves.

    Thatch cannot reuse `gable_roof`. Stacked tile courses produce a stepped
    surface that reads as corrugated sheet, which is the opposite of thatch —
    whose entire character is MASS and the absence of any hard edge: 300-400mm
    of packed reed, eaves that roll under into a deep shadow, and a soft
    settled surface.

    Built as a closed cross-section (outer surface, rolled ends, inner
    underside) extruded along the ridge, so the shell is continuous.

    `width` spans the gable; `depth` is the ridge length.
    """
    rng = rng_for(asset_id, "thatch_roof")
    out = M.Group()
    hw = (width + overhang * 2) * 0.5
    d = depth + overhang * 2
    h = hw * pitch

    # Centreline of the roof surface: eave -> ridge -> eave, with a little sag
    # because thatch settles over its lifetime.
    centre = []
    for side in (-1, 1):
        rng_pts = range(segments, -1, -1) if side < 0 else range(1, segments + 1)
        for i in rng_pts:
            t = i / segments
            sag = np.sin(t * np.pi) * 0.045
            centre.append((side * hw * (1.0 - t), h * t - sag))
    centre = [(float(x), float(y)) for x, y in centre]

    def offset_poly(pts, dist):
        """Offset a polyline along its outward normal."""
        out_pts = []
        n = len(pts)
        for i, (x, y) in enumerate(pts):
            px, py = pts[max(0, i - 1)]
            nx_, ny_ = pts[min(n - 1, i + 1)]
            dx, dy = nx_ - px, ny_ - py
            ln = float(np.hypot(dx, dy)) or 1.0
            out_pts.append((x + (dy / ln) * dist, y - (dx / ln) * dist))
        return out_pts

    # Thicker at the eave than the ridge, as laid.
    outer = offset_poly(centre, thickness * 0.5)
    inner = offset_poly(centre, -thickness * 0.5)

    # Roll the eave ends under instead of leaving a flat cut edge. This roll is
    # the single most recognisable feature of a thatched roof.
    profile = []
    profile.extend(outer)
    ex, ey = centre[-1]
    for a in np.linspace(0.0, np.pi, 5)[1:-1]:
        profile.append((ex + np.cos(a) * 0.0 + thickness * 0.5 * np.cos(-a + 0.4),
                        ey - thickness * 0.5 * np.sin(a) * 0.9))
    profile.extend(reversed(inner))

    # `uv_scale=1.1` was 0.91 m per tile against thatch's authored 4 m: the
    # straw printed four times too fine and read as noise rather than as
    # stems. D-041.
    shell = M.prism([(float(x), float(y)) for x, y in profile], d,
                    chamfer=0.0, uv_scale=MAT.uv_scale(mat))
    shell.translate(0, 0, rng.uniform(-0.01, 0.01))
    out.add(shell.with_material(mat))

    # Ridge cap: a rolled bundle running the length of the ridge.
    # Built as a prism extruded along Z, matching the shell. A lathe rotated
    # onto the Z axis extends along -Z, not +Z, which put the cap a full
    # roof-length off the building in the first pass. Prism has no such trap.
    t = thickness
    cap_profile = []
    for a in np.linspace(0.0, np.pi, 11):
        cap_profile.append((np.cos(a) * t * 0.95, np.sin(a) * t * 0.72))
    cap_profile.append((-t * 0.95, -t * 0.30))
    cap_profile.append((t * 0.95, -t * 0.30))
    cap = M.prism([(float(x), float(y)) for x, y in cap_profile], d,
                  chamfer=0.0)
    cap.translate(0, h - t * 0.05, 0)
    out.add(cap.with_material(mat))

    # Crossed hazel spars pinning the ridge. Without them the ridge is a lump.
    nspar = max(4, int(d / 0.55))
    for i in range(nspar):
        z = -d * 0.5 + (i + 0.5) * (d / nspar)
        for sgn in (-1, 1):
            spar = M.cylinder(0.016, thickness * 1.9, 6, 0.003, "oak_weathered")
            spar.rotate_z(np.pi * 0.5)
            spar.rotate_y(sgn * 0.6 + rng.uniform(-0.05, 0.05))
            spar.translate(0, h + thickness * 0.34, z + rng.uniform(-0.02, 0.02))
            out.add(spar)

    return out


# ---------------------------------------------------------------------------
# Standing water
# ---------------------------------------------------------------------------
# One water surface, built the same way everywhere. Before this the mere had a
# real `water` material and every basin, trough and jet in the town was
# authored in `glass` — so the market square's fountain rendered as a sheet of
# window glass sitting in a stone bowl, and the town's largest single piece of
# ambient movement was in the one place a player stands still.

WATER_UV = MAT.uv_scale("water")   # 2.5 m of world per tile, from the library.

# How the depth tint runs. Deep water is nearly opaque and cool; the shallow
# margin shows the bed through it. COLOR_0 can only darken (glTF multiplies it
# into base colour), which is the direction this needs to go anyway.
#
# Darker and cooler than the (0.42, 0.64, 0.60) this shipped at. That ramp was
# a GREEN one — it took red down twice as far as it took green — so the deeper
# the water the greener it got, on top of an albedo that was already four
# times greener than red. `ad-town-05` §2 measured the sum of the two as
# "tropical emerald-teal" at 8 m. Real water absorbs red first and BLUE last,
# so the ratio has to run the other way: this takes red furthest, green next,
# and leaves blue highest, which is why a deep lake is slate and a deep
# swimming pool is blue. It is also darker overall, which is what makes the
# depth read at all — pass 04's note that the shallows and the deeps are the
# same value is a complaint about this constant.
WATER_DEEP = (0.30, 0.35, 0.44)


# Opacity against depth. Beer-Lambert: a water column of depth d transmits
# exp(-k*d), and the surface's own reflection is what is left. k ~= 1.55 per
# metre puts 0.27 alpha at 0.15 m of margin, 0.64 at 0.6 m, and 0.97 by 2.2 m
# — so the bed shows through the shallows and the channel is opaque, which is
# what makes a body of water read as having a VOLUME rather than as a coloured
# lid.
#
# `WATER_MIN` is 0.08, down from 0.26. The floor existed because "a waterline
# at alpha 0 has no specular and reads as a hole", and that was true while
# COLOR_0 alpha was the ONLY opacity term. It is not any more:
# `client/src/water.js` now applies Schlick's Fresnel on top, so a sheet at
# depth zero is still a mirror at a grazing angle and still catches the sun —
# it only vanishes when you are looking straight down into it, which is
# exactly what a centimetre of water over gravel does. Holding a 26 % floor
# instead put a visible grey film on every dry metre of bank the sheet's
# feathered margin oversails, which is the defect this pays for.
WATER_EXTINCTION = 1.55
WATER_MIN = 0.08


def water_alpha(depth_m):
    """COLOR_0 alpha for a water surface over `depth_m` metres of bed."""
    d = np.maximum(np.asarray(depth_m, np.float64), 0.0) * 2.6
    a = 1.0 - np.exp(-WATER_EXTINCTION * d)
    return np.clip(WATER_MIN + (1.0 - WATER_MIN) * a, 0.0, 1.0)


def water_tint(depth, full=2.6):
    """COLOR_0 rows for a water surface `depth` metres over its bed."""
    d = np.clip(np.asarray(depth, np.float64) / full, 0.0, 1.0)
    deep = np.asarray(WATER_DEEP, np.float64)
    col = 1.0 + (deep - 1.0) * d[:, None]
    return np.concatenate([col, water_alpha(d)[:, None]], axis=1).astype(np.float32)


def pebble(asset_id, size=0.12, mat="gravel", squash=0.58):
    """One water-rounded stone, sitting on its flattest face.

    Beach shingle is not spherical: the sea and the river work it into a
    flattened ovoid and then lay it down on its broad face, which is why a
    shingle bank has a grain to it and reads as sorted rather than as scatter.
    `squash` is the axis ratio; the two horizontal axes differ so a run of
    these placed at random yaws does not read as a field of identical lumps.

    Deliberately tiny — 8 x 4 segments is 48 triangles, and a shore that wants
    four hundred of them wants them instanced.
    """
    rng = rng_for(asset_id, "pebble")
    r = float(size) * 0.5
    m = M.globe(r, mat, segments=8, rings=4,
                sx=float(rng.uniform(0.86, 1.22)),
                sy=float(squash) * float(rng.uniform(0.82, 1.16)),
                sz=float(rng.uniform(0.80, 1.14)))
    m.translate(0.0, r * float(squash) * 0.62, 0.0)
    return m


def water_disc(radius, y=0.0, depth=0.30, segments=32, rings=3, mat="water"):
    """A still round water surface — a fountain basin, a trough, a well head.

    Built as a fan of rings rather than one polygon so the depth tint has
    somewhere to live: the margin against the stone is shallow and warm, the
    middle is dark. A single quad would be one flat colour and would read as a
    lid.

    UVs are world-scaled at WATER_UV, the same as the mere, so the ripple in
    the normal map is the same physical size in a 4 m basin as in a 300 m lake
    — which is the thing that makes both read as water rather than as two
    different materials that happen to be blue.
    """
    verts, uvs, dep, tris = [], [], [], []
    verts.append((0.0, y, 0.0))
    uvs.append((0.0, 0.0))
    dep.append(depth)
    for r in range(1, rings + 1):
        rad = radius * (r / rings)
        # Shallower toward the rim: a basin is dished, and the tint has to
        # agree with the stone it meets.
        dd = depth * (1.0 - 0.72 * (r / rings) ** 2)
        for s in range(segments):
            a = 2.0 * np.pi * s / segments
            x, z = np.cos(a) * rad, np.sin(a) * rad
            verts.append((x, y, z))
            uvs.append((x * WATER_UV, z * WATER_UV))
            dep.append(dd)
    def idx(r, s):
        return 1 + (r - 1) * segments + (s % segments)
    for s in range(segments):
        tris.append((0, idx(1, s + 1), idx(1, s)))
    for r in range(1, rings):
        for s in range(segments):
            a, b = idx(r, s), idx(r, s + 1)
            c, d = idx(r + 1, s + 1), idx(r + 1, s)
            tris.append((a, b, c))
            tris.append((a, c, d))
    v = np.asarray(verts, np.float32)
    n = np.tile(np.array([0.0, 1.0, 0.0], np.float32), (len(v), 1))
    m = M.Mesh(v, n, np.asarray(uvs, np.float32),
               np.asarray(tris, np.uint32).reshape(-1), mat=mat)
    m.with_colour(water_tint(np.asarray(dep, np.float64)))
    return m


def water_slab(width, depth_m, y=0.0, depth=0.25, mat="water"):
    """A still rectangular water surface — a trough, a tank, a dye vat."""
    hx, hz = width * 0.5, depth_m * 0.5
    v = np.array([(-hx, y, -hz), (hx, y, -hz), (hx, y, hz), (-hx, y, hz)], np.float32)
    n = np.tile(np.array([0.0, 1.0, 0.0], np.float32), (4, 1))
    uv = np.stack([v[:, 0] * WATER_UV, v[:, 2] * WATER_UV], axis=1).astype(np.float32)
    m = M.Mesh(v, n, uv, np.array([0, 3, 2, 0, 2, 1], np.uint32), mat=mat)
    m.with_colour(water_tint(np.full(4, depth)))
    return m


# ---------------------------------------------------------------------------
# Residue
# ---------------------------------------------------------------------------
# Art Bible §7's residue vocabulary — carts, trade tools, laundry, spills, the
# dressing functions — lives in `core/props.py`. It is a hundred-odd builders
# and it would have doubled this file, which is about how Hearthmere is
# CONSTRUCTED rather than about what is left lying about in it.
#
# The two are one vocabulary as far as a venue author is concerned, so every
# name in `props` is reachable from here and vice versa:
#
#     from core import kit as K
#     K.barrel(...)          # this file
#     K.dress_yard(...)      # forwarded to core/props.py
#
# Prefer `from core import props as P` in a venue that is mostly dressing;
# either import reaches the whole set.

def __getattr__(name):
    # `props.__dict__` rather than `getattr(props, name)`: props forwards
    # unknown names back here by the same mechanism, so getattr would bounce
    # between the two modules forever on a name that is in neither.
    from . import props as P
    obj = P.__dict__.get(name)
    if obj is None:
        raise AttributeError(f"module 'core.kit' has no attribute '{name}'")
    return obj


# ---------------------------------------------------------------------------
# Masonry — arches, mural stairs, and the ironwork that goes with them
#
# The wall, its four gates, three posterns, eleven towers and the Emberflow
# bridge are all the same handful of moves repeated: a voussoir ring, a splayed
# recess, a flight of treads, a hanging chain. They live here rather than in
# `venues/wall.py` because `venues/gatehouse.py` needs every one of them too,
# and two implementations of a voussoir ring is two different towns.
# ---------------------------------------------------------------------------

def arch_ring(asset_id, span, rise=None, ring=0.42, depth=1.4, mat="ashlar",
              voussoirs=None, keystone=1.35, chamfer=0.022, drop=0.0):
    """A voussoir arch. Opening spans local X, barrel runs along local Z.

    Springing is at y = 0 and the intrados apex at y = `rise`; `rise = span/2`
    is semicircular and anything less is segmental, which is what a low bridge
    and a cart arch actually are. `ring` is the depth of the stones measured
    radially, `depth` the thickness of the wall the arch pierces.

    Built as individual stones with a jitter on every joint, because a
    smooth-lofted band is the most obvious procedural tell in masonry: real
    voussoirs are cut one at a time and none of them match. `drop` racks the
    ring by that much at one springing, which is how the West Gate settled
    0.2 m out of plumb without anybody rebuilding it.
    """
    rng = rng_for(asset_id, "arch")
    out = M.Group()
    span = float(span)
    rise = float(span * 0.5 if rise is None else rise)
    # Circle through (-s/2, 0), (0, rise), (s/2, 0): its centre sits at
    # y = (rise^2 - (s/2)^2) / (2*rise), which is 0 for a semicircle and
    # NEGATIVE for a segmental arch — the centre is below the springing line.
    h = span * 0.5
    cy = (rise * rise - h * h) / (2.0 * rise)
    R = rise - cy
    half = math.asin(min(1.0, h / R))
    n = voussoirs or (max(7, int(round(R * half * 2.0 / 0.42))) | 1)
    for i in range(n):
        a0 = -half + (2.0 * half) * i / n
        a1 = -half + (2.0 * half) * (i + 1) / n
        am = (a0 + a1) * 0.5
        key = (i == n // 2)
        wid = (a1 - a0) * R * (keystone if key else 1.0) - 0.012
        rr = ring * (1.16 if key else 1.0) + rng.uniform(-0.02, 0.02)
        v = M.box(wid, rr, depth * rng.uniform(0.97, 1.0), chamfer, mat)
        v.rotate_z(-am)
        v.translate(math.sin(am) * (R + rr * 0.5),
                    cy + math.cos(am) * (R + rr * 0.5),
                    rng.uniform(-0.01, 0.01))
        out.add(v)
    if abs(drop) > 1e-6:
        for m in out.parts.values():
            m.v[:, 1] += (m.v[:, 0] / h) * (-0.5 * float(drop))
    return out


def arch_soffit(span, rise, pad=0.03, samples=25):
    """The intrados curve as `(x, y)` samples — what an arch actually opens.

    Returned so a caller building the wall AROUND an arch can cut the spandrel
    to the same curve the stones follow, instead of eyeballing a rectangle and
    leaving a crescent of masonry floating over the opening.
    """
    h = float(span) * 0.5
    rise = float(rise)
    cy = (rise * rise - h * h) / (2.0 * rise)
    R = rise - cy
    out = []
    for i in range(samples):
        x = -h + (2.0 * h) * i / (samples - 1)
        out.append((x, cy + math.sqrt(max(0.0, R * R - x * x)) + pad))
    return out


def arrow_loop(asset_id, height=1.05, slot=0.075, splay=0.62, depth=0.9,
               mat="sandstone", void_mat="oak_dark"):
    """A splayed loop: a narrow slit outside, a wide embrasure inside.

    Dressed as an older and smaller-scale piece of masonry than the wall it
    sits in — Hearthmere's loops were salvaged from whatever stood here before
    the customs circuit, which is why they are in a different stone and at the
    wrong height for the present wall-walk. Faces local -Z. Origin at the sill,
    on the outer face.
    """
    rng = rng_for(asset_id, "loop")
    out = M.Group()
    for sx in (-1, 1):
        j = M.box(0.20, height + 0.30, 0.14, 0.018, mat)
        j.translate(sx * (slot * 0.5 + 0.10), height * 0.5, -0.055)
        out.add(j)
    head = M.box(slot + 0.44, 0.20, 0.14, 0.018, mat)
    head.translate(0, height + 0.10, -0.055)
    out.add(head)
    sill = M.box(slot + 0.44, 0.14, 0.18, 0.018, mat)
    sill.translate(0, -0.07, -0.045)
    out.add(sill)
    # The void has to start AT the face. Set back behind the surround it reads
    # as a light rectangle at any distance over ten metres, which is a blank
    # panel and not a loop — the slit is 75 mm wide and the only thing that
    # makes it legible at all is that it is black.
    dark = M.box(slot, height, depth, 0.004, void_mat)
    dark.translate(0, height * 0.5, depth * 0.5 - 0.11)
    out.add(dark)
    for sx in (-1, 1):
        cheek = M.prism([(0, 0), (0, height), ((splay - slot) * 0.5, height),
                         ((splay - slot) * 0.5, 0)], depth * 0.86, chamfer=0.0)
        cheek.rotate_y(math.pi * 0.5)
        cheek.translate(sx * (slot * 0.5 + (splay - slot) * 0.25), 0,
                        depth * 0.47 + rng.uniform(-0.01, 0.01))
        out.add(cheek.with_material(mat))
    return out


def stair_flight(asset_id, rise, width=1.2, riser=0.175, going=0.28,
                 mat="stone", chamfer=0.02, spine=0.30):
    """A flight of stone treads climbing local +Y and receding along local -Z.

    Origin is the FOOT of the flight, at the front nosing of the bottom tread.
    `spine` is the raking masonry the treads are built off, which is what stops
    a mural stair reading as a floating escalator seen end-on from the lane
    below. Returns `(Group, run)` so the caller can place what is at the top.
    """
    rng = rng_for(asset_id, "stair")
    out = M.Group()
    n = max(1, int(round(float(rise) / riser)))
    r = float(rise) / n
    run = n * going
    for i in range(n):
        # Nosings are the most-touched stone in the town, so the treads are
        # dished toward their centre. That is geometry, not a texture: the dish
        # is what catches the 09:30 light along the flight.
        t = M.box(width, r + 0.04, going + 0.05, chamfer, mat)
        dish = np.clip(0.5 - np.abs(t.v[:, 0]) / max(width, 1e-6), 0.0, 1.0)
        t.v[:, 1] -= (dish * 0.018 * (t.v[:, 1] > 0)).astype(np.float32)
        t.translate(rng.uniform(-0.006, 0.006), r * (i + 0.5) - 0.02,
                    -going * (i + 0.5))
        out.add(t)
    if spine > 0:
        # prism() extrudes an XY profile along Z, so the raking triangle has to
        # be turned into the (Z, Y) plane: rotate_y(-90) sends profile +X to
        # world +Z and the extrusion depth to world X, which is the flight
        # receding along -Z with its spine thickness across the treads.
        sp = M.prism([(0.0, 0.0), (0.0, float(rise)), (-run, 0.0)], spine,
                     chamfer=0.0)
        sp.rotate_y(-math.pi * 0.5)
        sp.translate(-width * 0.5 - spine * 0.5, 0, 0)
        out.add(sp.with_material(mat))
    return out, run


def forged_chain(asset_id, a, b, links=None, sag=0.35, link=0.14, mat="iron"):
    """A hand-forged chain hanging between two points.

    Art Bible §2 forbids "chain of uniform machine links", so every link here
    is a different length and a different thickness and none of them are quite
    in plane. That variance is the entire reason to model it rather than draw a
    line, and it is what makes the chain across the Water Gate read as forged.
    """
    rng = rng_for(asset_id, "chain")
    out = M.Group()
    a = np.asarray(a, np.float64)
    b = np.asarray(b, np.float64)
    span = float(np.linalg.norm(b - a))
    n = links or max(4, int(span / (link * 0.78)))
    d = (b - a) / max(span, 1e-6)
    for i in range(n):
        t = (i + 0.5) / n
        p = a + (b - a) * t
        p[1] -= sag * 4.0 * t * (1.0 - t)
        ln = link * rng.uniform(0.86, 1.14)
        lk = M.lathe([(0.0, 0.0), (0.021 * rng.uniform(0.8, 1.2), 0.012),
                      (0.021, ln - 0.012), (0.0, ln)], 7, mat)
        lk.translate(0, -ln * 0.5, 0)
        # Alternate links lie at right angles to their neighbours, which is
        # what a chain IS; without it this is a string of beads.
        lk.rotate_x(math.pi * 0.5 if i % 2 else 0.0)
        slope = d[1] - sag * 4.0 * (1.0 - 2.0 * t) / max(span, 1e-6)
        lk.rotate_z(-math.atan2(slope, math.hypot(d[0], d[2]) or 1e-6)
                    + rng.uniform(-0.09, 0.09))
        lk.rotate_y(math.atan2(d[0], d[2]))
        lk.translate(float(p[0]), float(p[1]), float(p[2]))
        out.add(lk)
    return out


def corbel(asset_id, project=0.46, width=0.34, height=0.30, mat="stone"):
    """One stone of a corbel table — the bracket a wall-walk is carried on.

    Two oversailing courses rather than one slab: that is how a 1.6 m walk is
    got out of a 1.1 m wall without doubling its thickness, and the double
    shadow line under it is the detail that reads from the lane below.
    Projects along local -Z from a face at z = 0; origin at the top of the
    upper course.
    """
    rng = rng_for(asset_id, "corbel")
    out = M.Group()
    for i, p in enumerate((project * 0.55, project)):
        w = width * (1.0 if i == 0 else 1.12)
        b = M.box(w, height * 0.5, p, 0.018, mat)
        b.translate(rng.uniform(-0.008, 0.008), -height * (0.75 - 0.5 * i), -p * 0.5)
        out.add(b)
    return out


# ---------------------------------------------------------------------------
# The open range — the working shed the craft quarter is made of
# ---------------------------------------------------------------------------
#
# Half the trades in Hearthmere work under a roof that is not walled on the
# street side, and that is not a stylistic choice: fire, smoke, shavings, wet
# hides and a two-metre stave all want air, and a trade that has to be seen to
# be sold wants a customer able to look in. `venues/blacksmith.py` established
# the form and every other workshop in the town should be built from the same
# posts, plates and braces rather than from its own.
#
# It is also the best gameplay decision available in this quarter: an open
# front means the player sees the work from the lane instead of a closed box
# with a sign on it.

def open_range(asset_id, width, depth, eaves, *, pitch=0.86, overhang=0.52,
               roof_mat="terracotta", post_mat="oak_dark",
               board_mat="oak_weathered", plinth_mat="rubble",
               walls=("back", "left", "right"), open_gable=False,
               bays=None, wall_h=None, plinth=0.20, half_boarded=(),
               board_gap=0.0, ridge_along=True, plot=None, tag="range"):
    """A post-and-plate range, roofed, and open on the sides you leave out.

    Origin on the ground at the centre of the footprint, ridge running along
    local X when `ridge_along` (the schedule's `ridge: along`, i.e. parallel to
    the frontage) and across it otherwise. The street face is local -Z,
    matching the design frame `core.siting.Site` authors in, and the rest of
    the kit.

    `walls` names the boarded sides from {"front", "back", "left", "right"}.
    `half_boarded` names sides that get a waist-high boarded screen instead of
    a full one — the form a cooper's or a farrier's side wall actually takes,
    because it keeps the wind off the fire without taking the light.

    `bays` is the number of post bays along the ridge; the default keeps them
    near 3.2 m, which is the span an oak plate of this section really carries.
    Posts stand ON the plinth, so the timber is out of the wet, which is the
    whole reason `stone_plinth` exists.

    Pass `plot` (a `core.siting.Site`) and the range declares its own collision:
    solid boarded walls, solid posts, a walkable floor, and NOTHING across an
    open side — which is the point of the form and the thing a bounding box
    would destroy.
    """
    rng = rng_for(asset_id, "range")
    out = M.Group()
    hw, hd = width * 0.5, depth * 0.5
    wall_h = eaves if wall_h is None else wall_h
    span = width if ridge_along else depth
    if bays is None:
        bays = max(2, int(round(span / 3.2)))

    # -- plinth: a continuous sill under the whole range --------------------
    if plinth > 0.0:
        pl = M.box(width + 0.24, plinth, depth + 0.24, 0.022, plinth_mat,
                   uv_scale=MAT.uv_scale(plinth_mat))
        pl.translate(0, plinth * 0.5, 0)
        out.add(pl)
        if plot is not None:
            plot.collider("box", center=(0, plinth * 0.5, 0),
                          half=((width + 0.24) * 0.5, plinth * 0.5,
                                (depth + 0.24) * 0.5),
                          kind="surface", tag=tag + "_floor")

    y0 = plinth
    post_x = [(-hw + (i / bays) * width) for i in range(bays + 1)]
    post_z = (-hd, hd)

    # -- posts, with knee braces at every head ------------------------------
    sect = 0.24 if span > 9.0 else 0.21
    for x in post_x:
        for z in post_z:
            p = M.box(sect, eaves - y0, sect, 0.014, post_mat)
            p.rotate_y(rng.uniform(-0.006, 0.006))
            p.translate(x, y0 + (eaves - y0) * 0.5, z)
            out.add(p)
            if plot is not None:
                plot.collider("box", center=(x, y0 + (eaves - y0) * 0.5, z),
                              half=(sect * 0.72, (eaves - y0) * 0.5, sect * 0.72),
                              tag=tag + "_post")
            # Braces: one along the plate, one across the tie. This is the
            # joint that stops a post-and-plate frame racking, so it is also
            # the joint whose absence makes the frame read as a diagram of a
            # building rather than as one.
            for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if dx and abs(x + dx * 0.9) > hw + 0.05:
                    continue
                if dz and abs(z + dz * 0.9) > hd + 0.05:
                    continue
                br = M.plank(0.78, 0.115, 0.10, 0.008, post_mat)
                br.rotate_z(-0.785)
                if dz:
                    br.rotate_y(np.pi * 0.5 * dz)
                elif dx < 0:
                    br.rotate_y(np.pi)
                br.translate(x + dx * 0.27, eaves - 0.48, z + dz * 0.27)
                out.add(br)

    # -- wall plates and tie beams -----------------------------------------
    for z in post_z:
        pl = M.plank(width + 0.30, 0.24, 0.21, 0.012, post_mat)
        pl.translate(0, eaves + 0.10, z)
        out.add(pl)
    for x in post_x:
        tie = M.plank(depth + 0.30, 0.20, 0.17, 0.010, post_mat, grain_axis=1)
        tie.rotate_y(np.pi * 0.5)
        tie.translate(x, eaves + 0.10, 0)
        out.add(tie)

    # -- boarding ----------------------------------------------------------
    SIDES = {"back": (0, 1), "front": (0, -1), "right": (1, 0), "left": (-1, 0)}
    for name, (sx, sz) in SIDES.items():
        full = name in walls
        half = name in half_boarded
        if not (full or half):
            continue
        run = width if sz else depth
        h = (wall_h - y0) if full else min(1.15, wall_h - y0)
        n = max(2, int(run / 0.29))
        # `board_gap` is the air between boards. A working shed is boarded with
        # a deliberate gap — it is cheaper, the timber can move, and the light
        # gets in. That last one is the reason it matters here: a solid dark
        # boarded wall behind an open front turns the whole covered floor black
        # and the work in it stops reading, which is the exact failure this
        # form exists to avoid.
        bw = max(0.06, run / n - board_gap)
        for i in range(n):
            t = -run * 0.5 + (i + 0.5) * run / n
            b = M.box(bw, h, 0.034, 0.005, board_mat,
                      uv_scale=MAT.uv_scale(board_mat))
            b.rotate_z(rng.uniform(-0.005, 0.005))
            if sx:
                b.rotate_y(np.pi * 0.5)
                b.translate(sx * hw, y0 + h * 0.5, t)
            else:
                b.translate(t, y0 + h * 0.5, sz * hd)
            out.add(b)
        # A rail capping a half-height screen, so it reads as built and not cut.
        if half and not full:
            rl = M.plank(run + 0.1, 0.09, 0.09, 0.006, post_mat,
                         grain_axis=0 if sz else 1)
            if sx:
                rl.rotate_y(np.pi * 0.5)
                rl.translate(sx * hw, y0 + h + 0.045, 0)
            else:
                rl.translate(0, y0 + h + 0.045, sz * hd)
            out.add(rl)
        if plot is not None and full:
            if sx:
                plot.collider("box", center=(sx * hw, y0 + h * 0.5, 0),
                              half=(0.10, h * 0.5, hd + 0.05), tag=tag + "_wall")
            else:
                plot.collider("box", center=(0, y0 + h * 0.5, sz * hd),
                              half=(hw + 0.05, h * 0.5, 0.10), tag=tag + "_wall")

    # -- roof ---------------------------------------------------------------
    if ridge_along:
        roof = gable_roof(depth, width, asset_id + ".roof", pitch=pitch,
                          overhang=overhang, tile_mat=roof_mat,
                          timber_mat=post_mat)
        roof.rotate_y(np.pi * 0.5)
        gw = depth
    else:
        roof = gable_roof(width, depth, asset_id + ".roof", pitch=pitch,
                          overhang=overhang, tile_mat=roof_mat,
                          timber_mat=post_mat)
        gw = width
    roof.translate(0, eaves + 0.22, 0)
    out.add(roof)

    # Gable ends: closed unless the trade wants the draught, and one does —
    # a tannery drying shed is louvred on every face on purpose.
    if not open_gable:
        for s in (-1, 1):
            g = gable_end(gw + overhang * 2, 0.0, pitch, mat=board_mat,
                          depth=0.16)
            if ridge_along:
                g.rotate_y(np.pi * 0.5)
                g.translate(s * (hw + overhang), eaves + 0.22, 0)
            else:
                g.translate(0, eaves + 0.22, s * (hd + overhang))
            out.add(g)
    return out
