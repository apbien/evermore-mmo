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

import numpy as np

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


# ---------------------------------------------------------------------------
# Walls
# ---------------------------------------------------------------------------

def stone_plinth(width, depth, height=0.80, mat="stone"):
    """Coursed rubble base. Every building in Hearthmere sits on one — it
    keeps timber out of the wet, which is why it exists historically and why
    it reads as correct."""
    m = M.box(width, height, depth, 0.025, mat, uv_scale=0.5)
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
    for (rx, ry, rw, rh) in _subtract_rects(width, height, openings):
        panel = M.box(rw, rh, depth * 0.55, CHAMFER_ARCH, plaster_mat, uv_scale=0.5)
        panel.translate(rx, sill_y + ry, 0)
        out.add(panel)

    zf = depth * 0.5 - POST * 0.5 + 0.02   # frame sits proud on the -Z face
    tm = timber_mat

    def post_at(x, y0, y1, w=POST):
        h = y1 - y0
        if h <= 0.02:
            return
        p = M.box(w, h, POST, CHAMFER_ARCH, tm)
        p.uv = np.stack([p.v[:, 0] * 2.0, p.v[:, 1] * 0.5], axis=1).astype(np.float32)
        p.translate(x, sill_y + y0 + h * 0.5, -zf)
        out.add(p)

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
    post_at(-hw + POST * 0.5, 0, height)
    post_at(hw - POST * 0.5, 0, height)

    spacing = {"square": 1.35, "close": 0.52, "cross": 1.5, "herring": 0.62}[style]
    n = max(1, int(round(width / spacing)))
    step = width / n

    for i in range(1, n):
        x = -hw + i * step + rng.uniform(-0.02, 0.02)   # hand-built variance
        if not blocked(x, height * 0.5, POST, height):
            post_at(x, POST, height - POST, POST * (0.85 if style == "close" else 1.0))

    # Mid rail on taller walls — structurally necessary and breaks the panel.
    if height > 2.4 and style != "close":
        my = height * rng.uniform(0.50, 0.56)
        rail_at(my, -hw, hw, POST * 0.85)

    if style == "cross":
        # Braces per bay. Real cross-bracing alternates direction along a wall.
        for i in range(n):
            x0 = -hw + i * step + POST * 0.5
            x1 = x0 + step - POST
            if blocked((x0 + x1) * 0.5, height * 0.5, step, height):
                continue
            y0, y1 = POST, height - POST
            for sign in (1, -1):
                dx, dy = (x1 - x0) * sign, (y1 - y0)
                ln = float(np.hypot(dx, dy))
                br = M.plank(ln, POST * 0.72, POST * 0.8, CHAMFER_ARCH, tm)
                br.rotate_z(float(np.arctan2(dy, dx)))
                br.translate((x0 + x1) * 0.5, sill_y + (y0 + y1) * 0.5, -zf - 0.012)
                out.add(br)

    if style == "herring":
        # Herringbone nogging: short diagonals inside each panel.
        for i in range(n):
            cx = -hw + (i + 0.5) * step
            if blocked(cx, height * 0.5, step, height):
                continue
            rows = int((height - 2 * POST) / 0.19)
            for r in range(rows):
                y = POST + (r + 0.5) * 0.19
                ang = 0.62 * (1 if r % 2 == 0 else -1)
                b = M.plank(step * 0.80, 0.085, 0.07, 0.004, "oak_dark")
                b.rotate_z(ang)
                b.translate(cx, sill_y + y, -zf + 0.03)
                out.add(b)

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
    for side in (-1, 1):
        for c in range(courses):
            t0 = c / courses
            t1 = (c + 1) / courses
            x0, y0 = side * (w * 0.5) * (1 - t0), h * t0
            x1, y1 = side * (w * 0.5) * (1 - t1), h * t1
            seg = float(np.hypot(x1 - x0, y1 - y0))
            # Each course is a thin slab, tilted to the slope, oversized so it
            # laps the course below.
            slab = M.box(seg * 1.22, 0.055, d, 0.010, tile_mat, uv_scale=1.0)
            ang = float(np.arctan2(y1 - y0, x1 - x0))
            slab.rotate_z(ang)
            slab.translate((x0 + x1) * 0.5, (y0 + y1) * 0.5 + 0.028,
                           rng.uniform(-0.004, 0.004))
            out.add(slab)

    # Ridge capping.
    ridge = M.lathe([(0.075, 0), (0.105, 0.055), (0.075, 0.11)], 10, tile_mat,
                    close_bottom=False, close_top=False)
    ridge.rotate_x(np.pi / 2).rotate_y(np.pi / 2)
    ridge.scale(1.0, 1.0, 1.0)
    cap = M.box(0.22, 0.10, d, 0.03, tile_mat)
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
    tri = M.prism([(-hw, 0), (hw, 0), (0, h)], depth, chamfer=0.0, uv_scale=0.5)
    tri.translate(0, height_at_eaves, 0)
    return tri.with_material(mat)


def chimney(asset_id, height=2.2, section=0.62, mat="stone", pot=True):
    """Stone stack with a clay pot. A roofline without chimneys reads as a
    model kit; they are the cheapest possible vertical interest."""
    rng = rng_for(asset_id, "chimney")
    out = M.Group()
    stack = M.box(section, height, section * 0.85, 0.02, mat, uv_scale=0.6)
    stack.translate(0, height * 0.5, 0)
    out.add(stack)
    # Corbelled cap — the stack widens at the top to throw water clear.
    cap = M.box(section * 1.22, 0.16, section * 1.05, 0.02, mat, uv_scale=0.6)
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
    glass = M.box(width, height, 0.03, 0.004, mat, uv_scale=1.0)
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
    board = M.Group().add(M.box(width, height, 0.038, 0.008, board_mat, uv_scale=1.2))
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


def sack(asset_id, height=0.55, mat="cloth_cream"):
    """Grain sack — slumped, never a neat cylinder."""
    rng = rng_for(asset_id, "sack")
    h = jitter(rng, height, 0.08)
    r = h * 0.42
    prof = [(r * 0.72, 0), (r * 0.98, h * 0.16), (r, h * 0.42),
            (r * 0.88, h * 0.70), (r * 0.52, h * 0.90), (r * 0.30, h)]
    m = M.lathe(prof, 12, mat)
    # Squash off-axis so it reads as soft goods under its own weight.
    m.scale(1.0 + rng.uniform(0, 0.12), 1.0, 1.0 - rng.uniform(0, 0.10))
    m.rotate_y(rng.uniform(0, 6.28))
    return m


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

    shell = M.prism([(float(x), float(y)) for x, y in profile], d,
                    chamfer=0.0, uv_scale=1.1)
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
                  chamfer=0.0, uv_scale=1.1)
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
