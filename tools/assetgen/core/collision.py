"""Authored collision volumes.

Build Directive §6 rule 4: *collision is authored, not inferred.* v1 derived one
axis-aligned box from each venue's whole bounding box, which is why the town was
unwalkable — the `streets` venue spans C1–C6, so its bounds sealed Ford Road
end to end, and `market_square`'s bounds sealed the plaza. Both are the exact
places the player is supposed to walk.

The reason v1 did it the wrong way is not that anyone thought bounds were
correct. It is that authoring collision was expensive and inferring it was one
line. So the shape of this module is a response to that: declaring collision for
a wall must be *one line at the site where the wall is emitted*, or generators
will drift back to not declaring any.

Three shapes, all Y-extruded, because a town is made of vertical prisms:

    box       centre + half-extents + rotation about Y
    cylinder  centre + radius + height (posts, wells, the fountain)
    hull      convex polygon in XZ + a Y span (irregular plazas, road segments)

Two kinds, and the distinction matters more than it looks:

    solid     blocks movement (walls, plinths, props)
    surface   does NOT block; only offers a standing height (roads, plazas,
              yard floors, aprons)

Without `surface`, a road built 0.10 m proud of the ground becomes a 0.10 m
kerb-wall the moment the terrain function puts the surrounding ground lower
than the road slab — i.e. the same "the street is sealed" failure, arriving by
a different route. A made road is a raised surface, so it is authored as one.

Everything here is in VENUE-LOCAL space. The client composes the venue's own
origin and Y rotation, exactly as it does for the mesh, so collision and
geometry can never drift apart by a transform.
"""

from __future__ import annotations

import math

# The character controller's contract, restated here because generators need to
# author against it: anything a player is expected to walk over must present a
# top surface no more than STEP_HEIGHT above the ground in front of it.
STEP_HEIGHT = 0.35

KINDS = ("solid", "surface")


def rot_xz(x, z, a):
    """Rotate (x, z) about +Y by `a` radians.

    Same convention as `Mesh.rotate_y` and three.js `rotation.y`:
    x' = cos*x + sin*z, z' = -sin*x + cos*z. Any divergence here shows up as
    collision that is mirrored about the venue's origin, which is very hard to
    see and very easy to introduce, so it lives in exactly one function.
    """
    c, s = math.cos(a), math.sin(a)
    return c * x + s * z, -s * x + c * z


def _f(x, name):
    v = float(x)
    if not math.isfinite(v):
        raise ValueError(f"collision: {name} is not finite ({x!r})")
    return round(v, 4)


def _v3(p, name):
    p = list(p)
    if len(p) != 3:
        raise ValueError(f"collision: {name} needs 3 components, got {p!r}")
    return [_f(v, name) for v in p]


def _tag(vol, tag, kind, cid):
    if kind not in KINDS:
        raise ValueError(f"collision: kind must be one of {KINDS}, got {kind!r}")
    if kind != "solid":
        vol["kind"] = kind
    if tag:
        vol["tag"] = str(tag)
    if cid:
        vol["id"] = str(cid)
    return vol


# ---------------------------------------------------------------------------
# Shapes
# ---------------------------------------------------------------------------

def box(center, half, rot_y=0.0, kind="solid", tag=None, cid=None):
    """Oriented box. `rot_y` is radians about +Y; the other two axes are locked.

    Buildings, walls, crates, plinths — everything in a pre-industrial town is
    a vertical prism, so a full 3-DOF orientation would only buy authoring
    mistakes.
    """
    h = _v3(half, "half")
    if min(h) <= 0.0:
        raise ValueError(f"collision: box half-extents must be positive, got {h}")
    v = {"shape": "box", "center": _v3(center, "center"), "half": h}
    if abs(float(rot_y)) > 1e-9:
        v["rotY"] = _f(rot_y, "rotY")
    return _tag(v, tag, kind, cid)


def cylinder(center, radius, height, kind="solid", tag=None, cid=None):
    """Vertical cylinder. `center` is the centre of the VOLUME, not the base —
    the same convention as `box`, so the two are interchangeable at a call site.
    """
    r, hgt = _f(radius, "radius"), _f(height, "height")
    if r <= 0 or hgt <= 0:
        raise ValueError(f"collision: cylinder needs positive radius/height ({r}, {hgt})")
    v = {"shape": "cylinder", "center": _v3(center, "center"),
         "radius": r, "height": hgt}
    return _tag(v, tag, kind, cid)


def hull(points, y0, y1, kind="solid", tag=None, cid=None):
    """Convex prism: the convex hull of a point set in XZ, extruded in Y.

    A general 3D hull would be the more impressive primitive and the wrong one:
    every collidable thing in this town has vertical sides, and a 2D hull test
    is a handful of dot products the client can run thousands of times a frame.
    Points may be (x, z) pairs or (x, y, z) triples — a triple's Y is dropped,
    so a mesh's own vertices can be handed straight in.
    """
    pts = []
    for p in points:
        p = list(p)
        if len(p) == 3:
            pts.append((float(p[0]), float(p[2])))
        elif len(p) == 2:
            pts.append((float(p[0]), float(p[1])))
        else:
            raise ValueError(f"collision: hull point must be (x,z) or (x,y,z), got {p!r}")
    poly = convex_hull_xz(pts)
    if len(poly) < 3:
        raise ValueError("collision: hull needs at least 3 non-collinear points")
    lo, hi = _f(min(y0, y1), "y0"), _f(max(y0, y1), "y1")
    if hi - lo <= 0:
        raise ValueError(f"collision: hull has no height ({lo}..{hi})")
    v = {"shape": "hull",
         "points": [[_f(x, "x"), _f(z, "z")] for x, z in poly],
         "minY": lo, "maxY": hi}
    return _tag(v, tag, kind, cid)


def convex_hull_xz(points):
    """Andrew's monotone chain. Returns a counter-clockwise ring in XZ."""
    pts = sorted(set((round(x, 5), round(z, 5)) for x, z in points))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


# ---------------------------------------------------------------------------
# Derivation helpers — the part that makes authoring cheap enough to happen
# ---------------------------------------------------------------------------

def from_bounds(lo, hi, inset=0.0, y0=None, y1=None, rot_y=0.0,
                kind="solid", tag=None, cid=None):
    """Box from a (lo, hi) bounds pair, e.g. `Mesh.bounds()`.

    `inset` shrinks the footprint in XZ — useful when a mesh's bounds include
    trim (an eaves overhang, a jetty) that must not become a wall. `y0`/`y1`
    override the vertical span, which is the usual case: a wall's collision
    should run from the ground to head height regardless of where its geometry
    happens to start.
    """
    x0, y_lo, z0 = float(lo[0]), float(lo[1]), float(lo[2])
    x1, y_hi, z1 = float(hi[0]), float(hi[1]), float(hi[2])
    x0 += inset; x1 -= inset; z0 += inset; z1 -= inset
    if y0 is not None:
        y_lo = float(y0)
    if y1 is not None:
        y_hi = float(y1)
    hx, hy, hz = (x1 - x0) * 0.5, (y_hi - y_lo) * 0.5, (z1 - z0) * 0.5
    if min(hx, hy, hz) <= 1e-4:
        raise ValueError(f"collision: degenerate bounds box {hx:.3f}x{hy:.3f}x{hz:.3f} "
                         f"— inset too large, or the mesh is empty")
    return box(((x0 + x1) * 0.5, (y_lo + y_hi) * 0.5, (z0 + z1) * 0.5),
               (hx, hy, hz), rot_y=rot_y, kind=kind, tag=tag, cid=cid)


def segment_box(a, b, width, y0, y1, kind="surface", tag=None, extend=0.0):
    """Box covering one segment of a polyline path — a road, a wall run, a quay.

    `extend` lengthens the box at both ends, which is how consecutive segments
    of a bending street overlap instead of leaving a diagonal sliver of
    un-authored ground at every kink.
    """
    ax, az = (float(a[0]), float(a[2])) if len(a) == 3 else (float(a[0]), float(a[1]))
    bx, bz = (float(b[0]), float(b[2])) if len(b) == 3 else (float(b[0]), float(b[1]))
    dx, dz = bx - ax, bz - az
    ln = math.hypot(dx, dz)
    if ln < 1e-4:
        raise ValueError("collision: degenerate path segment")
    # A box's local +X maps to world (cos, -sin), so this aims it down the run.
    ang = math.atan2(-dz, dx)
    return box(((ax + bx) * 0.5, (float(y0) + float(y1)) * 0.5, (az + bz) * 0.5),
               (ln * 0.5 + extend, max((float(y1) - float(y0)) * 0.5, 0.01),
                float(width) * 0.5),
               rot_y=ang, kind=kind, tag=tag)


def _spans(length, gaps):
    """Split a wall run of `length` (centred on 0) around door gaps."""
    cuts = []
    for off, w in sorted(gaps):
        cuts.append((off - w * 0.5, off + w * 0.5))
    out, a = [], -length * 0.5
    for (g0, g1) in cuts:
        if g1 <= a:
            continue
        if g0 > a:
            out.append((a, min(g0, length * 0.5)))
        a = max(a, g1)
    if a < length * 0.5:
        out.append((a, length * 0.5))
    return out


SIDES = ("-z", "+z", "-x", "+x")


def wall_ring(width, depth, height, y=0.0, thickness=0.35, center=(0.0, 0.0),
              rot_y=0.0, doors=(), tag="wall", cid=None):
    """Four walls around a rectangular footprint, with gaps for doorways.

    This is the one-liner that a building generator needs, and the reason it
    exists is that "walls solid, doorways open" is otherwise eight box
    declarations per building and nobody writes those.

    `doors` is a list of `(side, offset, width)` where side is one of
    "-z"/"+z"/"-x"/"+x" and `offset` is measured along that wall from the
    footprint centre, in the same local coordinates the generator already uses
    to place the door.
    """
    for (s, _o, _w) in doors:
        if s not in SIDES:
            raise ValueError(f"collision: door side must be one of {SIDES}, got {s!r}")
    t = float(thickness)
    runs = {
        "-z": ("x", float(width), -float(depth) * 0.5),
        "+z": ("x", float(width), float(depth) * 0.5),
        "-x": ("z", float(depth), -float(width) * 0.5),
        "+x": ("z", float(depth), float(width) * 0.5),
    }
    out = []
    for side, (axis, run, off) in runs.items():
        gaps = [(float(o), float(w)) for (s, o, w) in doors if s == side]
        for i, (a, b) in enumerate(_spans(run, gaps)):
            if b - a < 0.02:
                continue
            c = (a + b) * 0.5
            if axis == "x":
                lx, lz, hx, hz = c, off, (b - a) * 0.5, t * 0.5
            else:
                lx, lz, hx, hz = off, c, t * 0.5, (b - a) * 0.5
            wx, wz = rot_xz(lx, lz, rot_y)
            out.append(box((center[0] + wx, y + height * 0.5, center[1] + wz),
                           (hx, height * 0.5, hz), rot_y=rot_y, tag=tag,
                           cid=None if cid is None else f"{cid}.{side}{i}"))
    return out


def steps(front, height, tread=0.6, width=1.4, rot_y=0.0, tag="step"):
    """A flight of steppable slabs climbing to `height` at a threshold.

    `front` is the (x, y, z) of the threshold itself — the outer face of the
    plinth — and the flight descends from there along local **-Z**, which is
    outward for every building in Hearthmere because they all face -Z before
    the town's own rotation is applied. `rot_y` turns the flight for the ones
    that do not.

    Each riser is clamped to STEP_HEIGHT so the controller can actually climb
    it. Every building in this town stands on a 0.35–0.55 m plinth, so without
    a flight its door is visible and unreachable — the same class of defect as
    a sealed street, just smaller.
    """
    n = max(1, int(math.ceil(float(height) / STEP_HEIGHT)))
    rise = float(height) / n
    out = []
    for i in range(n):
        top = rise * (i + 1)
        # The LOWEST tread reaches furthest out and each one above it stops
        # short, so the slabs nest. The ground query takes the highest top
        # containing the player, which then reads off the correct tread — and
        # a single missing slab would leave a riser the player cannot climb.
        depth = tread * (n - i)
        lx, lz = 0.0, -depth * 0.5
        wx, wz = rot_xz(lx, lz, rot_y)
        out.append(box((front[0] + wx, float(front[1]) + top * 0.5, front[2] + wz),
                       (width * 0.5, max(top * 0.5, 0.02), depth * 0.5),
                       rot_y=rot_y, kind="surface", tag=tag))
    return out
