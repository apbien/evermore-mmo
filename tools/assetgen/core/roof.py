"""Roofs, derived from the wall plate.

v1's defect register is blunt about why every building in Hearthmere was
broken: a roof was authored as an independent prism and placed above a box by
an eyeballed Y offset. Two numbers had to agree — the wall's height and the
roof's offset — and nothing checked that they did, so roofs floated, gaps
opened at the eaves, and gable ends showed the sky through the roof void.

The fix is structural, not procedural. **A roof has no position of its own.**
`roof_from_plate` takes a `Plate` — the polygon of the wall head, carrying the
absolute Y of its bearing surface — and derives every vertex from it. There is
no `y` argument on any public function in this module and no code path that
accepts one, so a caller *cannot* place a roof by an offset even by mistake.
Raise the wall and the roof follows; there is nothing to keep in sync.

Everything else follows from the same rule:

  ridge height      = plate.y + pitch * halfspan          (never authored)
  eaves height      = plate.y - pitch * overhang          (the rafter foot
                      projects past the wall face, so the eaves is BELOW the
                      bearing line — this is why real eaves throw a shadow)
  gable / verge      closure is computed by asking the finished roof surface
                     how high it is along each plate edge, so a gable end can
                     never be forgotten and closes exactly, for every roof kind
  chimneys, dormers  are positioned by querying `surface_y(x, z)` on the roof
                     they pass through, so they cannot fail to emerge

Supported kinds: ``gable``, ``hip``, ``half_hip`` (jerkinhead), ``catslide``,
``gambrel``, ``lean_to``, ``pyramid``. Cross-gables, wings and valleys are
built by roofing the wing's own plate and passing ``clip_against=`` the main
roof: the wing's slopes are cut on the line where the two planes meet, which
*is* the valley.

Coordinates are world/venue space throughout (glTF Y-up, 1 unit = 1 m).
"""

from __future__ import annotations

import math

import numpy as np

from . import mesh as M
from .mathx import rng_for

# Art Bible §3: roof tile exposure 0.16 m. The course step is what gives a roof
# its saw-tooth edge against the sky; a tiled plane reads as wallpaper.
EXPOSURE = 0.16
# One tile's standing height. A course's head bears on the deck at TILE_T and
# its tail on the head of the course below at 2*TILE_T, so this IS the riser
# that shows at every course line. 0.055 m is a pantile, which is the tile Art
# Bible §3's 0.16 m exposure describes; at the old 0.030 the courses were also
# emitted coplanar, so the riser was buried and the relief was exactly zero.
# See `_tile_slope`. D-040.
TILE_T = 0.055
THATCH_T = 0.34         # depth of a thatch coat — `_thatch_slope`'s shell
DECK_T = 0.055          # rafters + boarding, closes the underside
CHAMFER = 0.015         # Art Bible §6, architectural class

TILE_MATS = {"terracotta", "slate"}


class RoofTooSmall(RuntimeError):
    """The solver's slopes do not cover the plate they were asked to roof.

    Its own class, not a bare RuntimeError, because there is exactly one
    legitimate way to handle it and it is not "carry on": a caller building a
    WING may retry with a shorter lap, since how far the wing runs back into
    the main range is its choice. A caller roofing a building may not — for
    that case this is the guard that stops eight roofless boxes shipping, and
    swallowing it puts them straight back (D-034).
    """


def _uv_scale(mat):
    """UV units per metre for a covering, from the material registry.

    Roof coverings laid their UVs with `mesh._planar_uv`'s default scale of
    1.0 — UVs in metres — while `terracotta` and `slate` are authored over a
    4 m tile and `thatch` likewise. Measured on the shipped town, the roofs
    sampled their texture over 1.17 m instead of 4 m: a 3.4x scale error, so
    Art Bible §3's 0.16 m tile exposure printed at 0.047 m. That is small
    enough to be sub-pixel from the air, which is why the roofs read as flat
    orange paper, and it also meant the printed courses disagreed with the
    modelled courses by 3.4x — two tile grids at once.

    Laid in the slope's own (t, s) frame rather than by planar projection, so
    texture V runs UP the slope: `terracotta_tile`'s 25 rows then land on the
    same 0.16 m gauge as the geometry instead of at an angle to it.
    """
    from . import materials as _M
    try:
        return _M.uv_scale(mat)
    except KeyError:
        return 0.5


# Course-scale colour, in COLOR_0. Art Bible §4 wants ~30% aged tiles, and §6
# forbids more than three identical elements in a row. COLOR_0 multiplies base
# colour, so it can only darken — which is the direction TERRACOTTA_AGED and a
# weathered slate both go.
_COVER_AGED = {
    "terracotta": 0.74,     # #8F4E36 against #B5603E is a 0.74 multiply
    "slate": 0.80,
    "ridge": 0.78,
}


# Per-BUILDING kiln batch, in COLOR_0. (D-050)
#
# `ad-town-04` asks for this twice — pass-02 #21 and pass-03 §5, both scored
# "clustering fixed, tint never done" — and names it in the top-three list:
# *"terracotta is one flat saturated orange on ~45 % of roofs"*, in every
# aerial. `_ROOF_POOL` already deals slate and thatch into blocks and the
# review confirms that reads; what it cannot do is make two tiled roofs differ,
# because they both take the identical `terracotta` sheet.
#
# Three batches, not three materials. A fourth and fifth texture set would be
# ~34 MB and, worse, two more batches on a build whose draw call gate is
# already failed at 1,416/900 (`ad-town-04`, Budget). COLOR_0 costs nothing:
# it is already on every roof vertex for the course jitter.
#
# COLOR_0 MULTIPLIES, so a batch can only go down from the authored
# `TERRACOTTA` #B5603E. That is the right direction anyway — a tile kiln
# underfires, it does not overfire — and the three are separated in SATURATION
# and HUE as well as value, because three roofs at three values of one orange
# still read as one orange from 120 m.
#
#   fired    the authored orange. The best clay, the newest roofs.
#   under    a browner, duller batch: less red, value nearly held.
#   lichen   the oldest roofs, gone grey-buff. This is the one that breaks the
#            aerial, because it is the only tiled roof that is not orange.
#
# Widened once, after looking at `t-aerial-sw`. The first cut was
# 1.00 / 0.87,0.91,0.98 / 0.73,0.81,0.92 dealt evenly, and the aerial still
# read as an orange town: only the third batch was far enough from the
# authored orange to tell, and it was one roof in three. The pool below deals
# `fired` at 2/9 rather than 3/9 — the newest roof is the RAREST roof in a town
# that has been standing for two hundred years — and puts real distance between
# the other three.
_KILN_BATCH = {
    "terracotta": ((1.00, 1.00, 1.00),          # fired: the authored orange
                   (1.00, 1.00, 1.00),
                   (0.90, 0.94, 1.00),          # sun-bleached: same value, less red
                   (0.90, 0.94, 1.00),
                   (0.80, 0.85, 0.95),          # under-fired: browner, a stop down
                   (0.80, 0.85, 0.95),
                   (0.66, 0.75, 0.90),          # lichened: grey-buff, not orange
                   (0.66, 0.75, 0.90),
                   (0.60, 0.70, 0.88)),         # the oldest roofs on the lane
    # Slate weathers from blue-black to a pale grey-green and the range is real
    # from the air, though it is a quieter problem than the terracotta.
    "slate": ((1.00, 1.00, 1.00), (0.90, 0.93, 0.95), (0.80, 0.85, 0.88)),
}


def kiln_batch(asset_id, mat):
    """The per-BUILDING COLOR_0 multiplier for a roof covering.

    Seeded from `asset_id` ALONE — not from the slope index — so every slope,
    every hip, every dormer and the ridge of one building come out of the same
    kiln. Seeding it per slope is the obvious mistake and it would give a town
    of two-tone roofs.
    """
    pool = _KILN_BATCH.get(mat)
    if pool is None:
        return (1.0, 1.0, 1.0)
    r = rng_for(asset_id, "kiln")
    return pool[int(r.integers(0, len(pool)))]


def _course_colour(rng, mat, batch=(1.0, 1.0, 1.0)):
    aged = _COVER_AGED.get(mat)
    if aged is None:
        return None if batch == (1.0, 1.0, 1.0) else batch
    # ~30% of courses carry a kiln batch that fired darker; the rest take a
    # small value jitter so no two adjacent courses match exactly.
    if rng.random() < 0.30:
        f = aged * rng.uniform(0.96, 1.06)
    else:
        f = rng.uniform(0.93, 1.0)
    f = float(np.clip(f, 0.55, 1.0))
    # Aged clay loses more blue than red as the surface weathers and takes
    # lichen, so the darkening is not neutral.
    return (f * batch[0], f * 0.985 * batch[1], f * 0.95 * batch[2])


def cover_thickness(mat):
    """How far the covering stands proud of the deck plane.

    Everything that meets a roof from outside derives its height from
    `Roof.surface_y` — the gable closure, a chimney's emergence, a party wall's
    coping, a dormer's sill. So this number has to be the real one for the
    covering actually laid.

    It used to be `TILE_T` for every roof in the town. That is right for tile
    and 0.31 m short for thatch, and 26 of the 63 kit buildings are thatched:
    their gable closures stopped 0.31 m below the coat that then oversailed the
    gap, their chimneys lost 0.31 m of the emergence they were sized for, and a
    party wall coping meant to stand proud of both roofs sat *under* the thatch
    it was closing. D-036.

    For tile it is now `2 * TILE_T`, not `TILE_T`: since D-040 a course's tail
    bears on the head of the course below, so the covering stands two
    thicknesses proud at every course line. Returning one would put every gable
    coping and chimney flashing a tile's depth under the tiles they close.
    """
    return THATCH_T if is_thatch(mat) else TILE_T * 2.0


# ---------------------------------------------------------------------------
# Small vector helpers
# ---------------------------------------------------------------------------

def _u(v):
    v = np.asarray(v, float)
    n = float(np.linalg.norm(v))
    return v / (n if n > 1e-12 else 1.0)


def _h3(p2, y):
    """A 2D (x, z) point lifted to 3D at height y."""
    return np.array([float(p2[0]), float(y), float(p2[1])], float)


def _perp(d2):
    """Rotate a 2D (x, z) direction 90° so (U, V) is a consistent frame."""
    return np.array([-d2[1], d2[0]], float)


def _area2(poly):
    a = 0.0
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        a += x0 * y1 - x1 * y0
    return a * 0.5


def _clip(poly, a, b, c):
    """Sutherland-Hodgman: keep the half-plane a*x + b*y <= c."""
    if not poly:
        return []
    out = []
    n = len(poly)
    for i in range(n):
        p = poly[i]
        q = poly[(i + 1) % n]
        dp = a * p[0] + b * p[1] - c
        dq = a * q[0] + b * q[1] - c
        if dp <= 1e-9:
            out.append(p)
        if (dp < -1e-9 and dq > 1e-9) or (dp > 1e-9 and dq < -1e-9):
            t = dp / (dp - dq)
            out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
    return out if len(out) >= 3 else []


def _poly_intersect(subject, clipper):
    """Sutherland-Hodgman against a CONVEX clipper. Both wound CCW.

    Plates are convex by construction (`Footprint.rect` and every plate this
    module builds), which is what makes the cheap algorithm exact here.
    """
    poly = [(float(p[0]), float(p[1])) for p in subject]
    n = len(clipper)
    for i in range(n):
        px, py = clipper[i]
        qx, qy = clipper[(i + 1) % n]
        dx, dy = qx - px, qy - py
        # CCW winding puts the interior on the left of p->q, i.e.
        # cross(d, r - p) >= 0, which is  dy*rx - dx*ry <= dy*px - dx*py.
        poly = _clip(poly, dy, -dx, dy * px - dx * py)
        if not poly:
            return []
    return poly


def _inside(poly, x, y, eps=1e-6):
    """Point in polygon, assuming CCW convex-ish. Uses the crossing rule so a
    non-convex closure polygon still answers correctly."""
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y):
            xc = xi + (y - yi) * (xj - xi) / ((yj - yi) or 1e-12)
            if x < xc + eps:
                inside = not inside
        j = i
    return inside


# ---------------------------------------------------------------------------
# The plate — the only thing that positions a roof
# ---------------------------------------------------------------------------

class Plate:
    """The wall head: the polygon of the outer wall face plus its bearing Y.

    Behaves as a sequence of `(x, z)` points, so `wall_plate(...)` satisfies
    its documented "-> polygon" contract while still carrying the height and
    the per-edge metadata the roof needs.

    `edges[i]` describes the edge from `pts[i]` to `pts[i+1]`:

        "eaves"   the roof oversails it and the wall stops at plate.y
        "gable"   the roof rakes over it; a closure panel fills the triangle
        "party"   shared with the neighbour; no overhang, no closure
        "abut"    runs into a taller wall (lean-to head)
    """

    __slots__ = ("pts", "y", "edges", "thickness", "style", "wall_mat")

    def __init__(self, pts, y, edges=None, thickness=0.30, style=None,
                 wall_mat="plaster"):
        self.pts = [(float(p[0]), float(p[1])) for p in pts]
        if len(self.pts) < 3:
            raise ValueError("a wall plate needs at least 3 corners")
        y = float(y)
        if not math.isfinite(y):
            raise ValueError("plate.y must be a real elevation — derive it from "
                             "terrain.pad_level() or terrain.height(), never 0")
        self.y = y
        if _area2(self.pts) < 0:
            # Edge i spans pts[i]..pts[i+1]. Reversing the point list maps
            # old edge i onto new edge n-2-i, NOT onto n-1-i: `reversed()`
            # gives [e3,e2,e1,e0] where the correct answer is [e2,e1,e0,e3].
            # Rect footprints are always CCW so this never fired, but dormer()
            # builds a plate with no winding guarantee. D-034.
            n = len(self.pts)
            self.pts.reverse()
            if edges is not None:
                edges = [edges[(n - 2 - i) % n] for i in range(n)]
        self.edges = list(edges) if edges else ["eaves"] * len(self.pts)
        self.thickness = float(thickness)
        self.style = style
        self.wall_mat = wall_mat

    # sequence protocol -----------------------------------------------------
    def __len__(self):
        return len(self.pts)

    def __getitem__(self, i):
        return self.pts[i]

    def __iter__(self):
        return iter(self.pts)

    # frame -----------------------------------------------------------------
    def frame(self):
        """Oriented rectangle `(centre, U, V, hu, hv)` in the XZ plane.

        Edge 0 sets U, so a plate built front-edge-first gets U along the
        frontage and V into the plot — which is what `ridge='along'` and
        `ridge='gable'` in the building schedule mean.
        """
        p = np.asarray(self.pts, float)
        U = _u(np.asarray(self.pts[1], float) - np.asarray(self.pts[0], float))
        V = _perp(U)
        a = p @ U
        b = p @ V
        c = U * (a.min() + a.max()) * 0.5 + V * (b.min() + b.max()) * 0.5
        return c, U, V, (a.max() - a.min()) * 0.5, (b.max() - b.min()) * 0.5

    def edge(self, i):
        return (np.asarray(self.pts[i], float),
                np.asarray(self.pts[(i + 1) % len(self.pts)], float),
                self.edges[i])

    def with_y(self, y):
        return Plate(self.pts, y, self.edges, self.thickness, self.style,
                     self.wall_mat)


def wall_plate(footprint, eaves_y, edges=None, thickness=0.30, style=None,
               wall_mat="plaster"):
    """Build the plate a roof will be derived from.

        plate = wall_plate(footprint_polygon, floor_y + storeys * FLOOR_H)
        roof  = roof_from_plate(plate, "gable", pitch, overhang, asset_id)

    `footprint` is any sequence of (x, z) — a raw polygon, or anything with a
    `.polygon` attribute (a building.Footprint).
    """
    pts = getattr(footprint, "polygon", footprint)
    return Plate(pts, eaves_y, edges=edges, thickness=thickness, style=style,
                 wall_mat=wall_mat)


# ---------------------------------------------------------------------------
# Slopes
# ---------------------------------------------------------------------------

class Slope:
    """One planar roof surface, in its own (t along the eaves, s up the slope)
    frame. Everything the roof does — tiling, clipping, height queries, the
    valley cut — happens in this frame, so hips, valleys and half-hips are all
    the same code."""

    __slots__ = ("origin", "du", "ds", "n", "poly2", "pitch", "mat", "kind")

    def __init__(self, origin, du, ds, pts3, pitch, mat="terracotta", kind="slope"):
        self.origin = np.asarray(origin, float)
        du = _u(du)
        ds = _u(ds)
        if float(np.cross(du, ds)[1]) < 0:
            du = -du                    # keep (du, ds, n) right-handed, n up
        self.du, self.ds = du, ds
        self.n = _u(np.cross(du, ds))
        self.pitch = float(pitch)
        self.mat = mat
        self.kind = kind
        self.poly2 = self._project(pts3)

    def _project(self, pts3):
        out = []
        for p in pts3:
            d = np.asarray(p, float) - self.origin
            out.append((float(d @ self.du), float(d @ self.ds)))
        if _area2(out) < 0:
            out.reverse()
        return out

    # -- queries ------------------------------------------------------------

    def _st(self, x, z):
        """Solve the horizontal projection for (t, s)."""
        dx, dz = x - self.origin[0], z - self.origin[2]
        a11, a21 = self.du[0], self.du[2]
        a12, a22 = self.ds[0], self.ds[2]
        det = a11 * a22 - a12 * a21
        if abs(det) < 1e-12:
            return None
        t = (dx * a22 - dz * a12) / det
        s = (a11 * dz - a21 * dx) / det
        return t, s

    def y_at(self, x, z, pad=0.0):
        st = self._st(x, z)
        if st is None:
            return None
        t, s = st
        if not _inside(self.poly2, t, s, eps=pad):
            return None
        return float(self.origin[1] + s * self.ds[1])

    def plane_y(self, x, z):
        """Height of the slope's PLANE, ignoring its boundary. The valley cut
        needs this: a wing rafter dies where its plane meets the main plane,
        which is a property of the planes, not of their outlines."""
        st = self._st(x, z)
        if st is None:
            return None
        return float(self.origin[1] + st[1] * self.ds[1])

    def p3(self, t, s, off=0.0):
        return self.origin + self.du * t + self.ds * s + self.n * off

    def s_max(self):
        return max(s for _t, s in self.poly2) if self.poly2 else 0.0

    def s_min(self):
        return min(s for _t, s in self.poly2) if self.poly2 else 0.0

    def area(self):
        return abs(_area2(self.poly2))

    # -- clipping -----------------------------------------------------------

    def clip_plane(self, other, keep="above"):
        """Cut this slope against `other`'s plane. Two senses, both needed:

        `keep="above"` — the VALLEY. A wing's slope dies where the main range's
        plane climbs through it, so the wing keeps the part standing proud.

        `keep="below"` — the HIP. A main slope loses the corner that the hip
        face covers. There the hip plane springs from the gable head, *above*
        the main eaves, and it is the part of the main slope that rises through
        the hip that must go. Keeping "above" here deletes exactly the piece
        that should survive, and two hips on one slope delete all of it —
        which is how 8 buildings shipped with no roof (D-034).

        Both surfaces are planes, so `self_y - other_y` is linear in (t, s) and
        the cut is a straight line. Sampling three points recovers it exactly.
        """
        def f(t, s):
            p = self.p3(t, s)
            oy = other.plane_y(p[0], p[2])
            return None if oy is None else float(p[1] - oy)

        f0, f1, f2 = f(0.0, 0.0), f(1.0, 0.0), f(0.0, 1.0)
        if f0 is None or f1 is None or f2 is None:
            return
        a, b = f1 - f0, f2 - f0          # keep  a*t + b*s + f0 >= 0
        if keep == "below":
            a, b, f0 = -a, -b, -f0       # keep  a*t + b*s + f0 <= 0
        elif keep != "above":
            raise ValueError("clip_plane keep must be 'above' or 'below'")
        self.poly2 = _clip(self.poly2, -a, -b, f0)


def _slope(eaves_a, eaves_b, up_h, pitch, pts3, mat, kind="slope"):
    """A slope from its eaves line and the horizontal direction up the roof."""
    up = _u(np.array([up_h[0], 0.0, up_h[1]], float))
    ds = _u(up + np.array([0.0, pitch, 0.0], float))
    return Slope(eaves_a, np.asarray(eaves_b, float) - np.asarray(eaves_a, float),
                 ds, pts3, pitch, mat, kind)


# ---------------------------------------------------------------------------
# The roof
# ---------------------------------------------------------------------------

class Roof(M.Group):
    """A Group that also knows its own surface.

    Carrying the slopes is what lets a chimney, a dormer or a flashing derive
    its geometry from the roof instead of guessing at it.
    """

    __slots__ = ("slopes", "ridge_y", "eaves_y", "plate", "kind", "pitch",
                 "overhang", "mat", "ridge_line", "cover_t")

    def __init__(self):
        super().__init__()
        self.slopes = []
        self.ridge_y = 0.0
        self.eaves_y = 0.0
        self.plate = None
        self.kind = "gable"
        self.pitch = 0.85
        self.overhang = 0.4
        self.mat = "terracotta"
        self.ridge_line = None
        self.cover_t = TILE_T

    def deck_y(self, x, z, pad=0.0):
        """The rafter/boarding plane at (x, z) — under the covering."""
        best = None
        for sl in self.slopes:
            y = sl.y_at(x, z, pad=pad)
            if y is not None and (best is None or y > best):
                best = y
        return best

    def surface_y(self, x, z, pad=0.0):
        """Top of the roof COVERING at (x, z), or None if outside the roof."""
        best = self.deck_y(x, z, pad=pad)
        return None if best is None else best + self.cover_t

    def covers(self, x, z, pad=0.0):
        return self.surface_y(x, z, pad=pad) is not None

    def slope_at(self, x, z):
        best, bs = None, None
        for sl in self.slopes:
            y = sl.y_at(x, z)
            if y is not None and (bs is None or y > bs):
                best, bs = sl, y
        return best


# ---------------------------------------------------------------------------
# Solvers — each returns a list of Slope, all derived from the plate
# ---------------------------------------------------------------------------

def _rect_slopes(plate, kind, pitch, overhang, verge, mat, opts):
    c, U, V, hu, hv = plate.frame()
    y0 = plate.y
    ridge_axis = opts.get("ridge_axis", "u")
    if ridge_axis == "v":                       # ridge runs into the plot
        U, V = V, -U
        hu, hv = hv, hu

    # Overhang is suppressed on party walls and abutments: a shared wall has
    # no room for an eaves, and a roof that oversails one drives its neighbour.
    def edge_over(direction, default):
        for i in range(len(plate)):
            a, b, k = plate.edge(i)
            d = _u(b - a)
            nrm = _perp(d)
            if float(nrm @ direction) > 0.9 and k in ("party", "abut"):
                return 0.0
        return default

    oh_p = edge_over(V, overhang)               # +V eaves
    oh_m = edge_over(-V, overhang)              # -V eaves
    vg_p = edge_over(U, verge)
    vg_m = edge_over(-U, verge)

    def P(a, b, y):
        return _h3(c + U * a + V * b, y)

    slopes = []
    ridge_line = None

    if kind in ("gable", "catslide", "half_hip"):
        run = float(opts.get("catslide_run", 0.0)) if kind == "catslide" else 0.0
        ridge_y = y0 + pitch * hv
        # +V side (the catslide, if any, always falls to the back)
        for sgn, oh, extra in ((1.0, oh_p, 0.0), (-1.0, oh_m, run)):
            edge_b = sgn * (hv + oh + extra)
            ey = y0 - pitch * (oh + extra)
            a0, a1 = -(hu + vg_m), (hu + vg_p)
            pts = [P(a0, edge_b, ey), P(a1, edge_b, ey),
                   P(a1, 0.0, ridge_y), P(a0, 0.0, ridge_y)]
            slopes.append(_slope(P(a0, edge_b, ey), P(a1, edge_b, ey),
                                 -sgn * V, pitch, pts, mat))
        ridge_line = (P(-(hu + vg_m), 0.0, ridge_y), P(hu + vg_p, 0.0, ridge_y))

        if kind == "half_hip":
            # Jerkinhead: the gable rises to `frac` of its full height, then is
            # hipped back. The hip face springs from a horizontal line on the
            # gable plane and its apex is the (shortened) ridge end.
            frac = float(opts.get("hip_frac", 0.55))
            k = frac * hv                       # height/pitch, in plan metres
            for sgn, vg in ((1.0, vg_p), (-1.0, vg_m)):
                a_edge = sgn * (hu + vg)
                b_half = max(0.15, hv - k)
                apex = P(a_edge - sgn * b_half, 0.0, ridge_y)
                y_spring = y0 + pitch * k
                e0 = P(a_edge, -b_half, y_spring)
                e1 = P(a_edge, b_half, y_spring)
                slopes.append(_slope(e0, e1, -sgn * U, pitch,
                                     [e0, e1, apex], mat, kind="hip"))
            # and the main slopes lose their corners to it
            for sl in slopes[:2]:
                for hp in slopes[2:]:
                    sl.clip_plane(hp, keep="below")

    elif kind == "hip":
        if hu < hv:
            U, V = V, -U
            hu, hv = hv, hu
            oh_p, oh_m, vg_p, vg_m = vg_p, vg_m, oh_p, oh_m
        ridge_y = y0 + pitch * hv
        ra = max(0.0, hu - hv)
        for sgn, oh in ((1.0, oh_p), (-1.0, oh_m)):
            eb = sgn * (hv + oh)
            ey = y0 - pitch * oh
            e0, e1 = P(-(hu + vg_m), eb, ey), P(hu + vg_p, eb, ey)
            pts = [e0, e1, P(ra, 0.0, ridge_y), P(-ra, 0.0, ridge_y)]
            slopes.append(_slope(e0, e1, -sgn * V, pitch, pts, mat))
        for sgn, vg in ((1.0, vg_p), (-1.0, vg_m)):
            ea = sgn * (hu + vg)
            ey = y0 - pitch * vg
            e0, e1 = P(ea, -(hv + oh_m), ey), P(ea, hv + oh_p, ey)
            apex = P(sgn * ra, 0.0, ridge_y)
            slopes.append(_slope(e0, e1, -sgn * U, pitch, [e0, e1, apex], mat,
                                 kind="hip"))
        ridge_line = (P(-ra, 0.0, ridge_y), P(ra, 0.0, ridge_y))

    elif kind == "pyramid":
        ridge_y = y0 + pitch * min(hu, hv)
        apex = P(0.0, 0.0, ridge_y)
        for sgn, oh in ((1.0, oh_p), (-1.0, oh_m)):
            eb = sgn * (hv + oh)
            ey = y0 - pitch * oh
            e0, e1 = P(-(hu + vg_m), eb, ey), P(hu + vg_p, eb, ey)
            slopes.append(_slope(e0, e1, -sgn * V, pitch, [e0, e1, apex], mat,
                                 kind="hip"))
        for sgn, vg in ((1.0, vg_p), (-1.0, vg_m)):
            ea = sgn * (hu + vg)
            ey = y0 - pitch * vg
            e0, e1 = P(ea, -(hv + oh_m), ey), P(ea, hv + oh_p, ey)
            slopes.append(_slope(e0, e1, -sgn * U, pitch, [e0, e1, apex], mat,
                                 kind="hip"))
        ridge_line = (apex, apex)

    elif kind == "gambrel":
        p_low = pitch * float(opts.get("gambrel_steep", 2.0))
        p_hi = pitch * float(opts.get("gambrel_shallow", 0.45))
        hb = hv * float(opts.get("gambrel_break", 0.46))
        y_b = y0 + p_low * (hv - hb)
        ridge_y = y_b + p_hi * hb
        a0, a1 = -(hu + vg_m), (hu + vg_p)
        for sgn, oh in ((1.0, oh_p), (-1.0, oh_m)):
            ey = y0 - p_low * oh
            e0, e1 = P(a0, sgn * (hv + oh), ey), P(a1, sgn * (hv + oh), ey)
            slopes.append(_slope(e0, e1, -sgn * V, p_low,
                                 [e0, e1, P(a1, sgn * hb, y_b), P(a0, sgn * hb, y_b)],
                                 mat))
            u0, u1 = P(a0, sgn * hb, y_b), P(a1, sgn * hb, y_b)
            slopes.append(_slope(u0, u1, -sgn * V, p_hi,
                                 [u0, u1, P(a1, 0.0, ridge_y), P(a0, 0.0, ridge_y)],
                                 mat))
        ridge_line = (P(a0, 0.0, ridge_y), P(a1, 0.0, ridge_y))

    elif kind == "lean_to":
        # Falls from the -V head (against the taller wall) to the +V eaves.
        ridge_y = y0 + pitch * 2.0 * hv
        eb, ey = hv + oh_p, y0 - pitch * oh_p
        a0, a1 = -(hu + vg_m), (hu + vg_p)
        e0, e1 = P(a0, eb, ey), P(a1, eb, ey)
        slopes.append(_slope(e0, e1, -V, pitch,
                             [e0, e1, P(a1, -hv, ridge_y), P(a0, -hv, ridge_y)],
                             mat))
        ridge_line = (P(a0, -hv, ridge_y), P(a1, -hv, ridge_y))

    else:
        raise ValueError(f"unknown roof kind '{kind}'. Have: gable, hip, "
                         f"half_hip, catslide, gambrel, lean_to, pyramid")

    return slopes, ridge_y, ridge_line


# ---------------------------------------------------------------------------
# Covering
# ---------------------------------------------------------------------------

def _tile_slope(out, sl, asset_id, i, exposure, mat, detail=0):
    """Lay courses up the slope.

    ## Why the old version cast no shadow

    Every course's top plane was emitted at the SAME offset (`TILE_T`) above
    the deck, and each course's tail riser ran from the deck up to that same
    offset. So the riser terminated exactly in the plane of the course below
    it: it was an internal wall, buried, coplanar at its top edge with the
    surface it was supposed to stand proud of. The covering was one flat plane
    with a hidden fin every 0.16 m — geometrically a decal, which is exactly
    how it rendered. Raising `TILE_T` alone would not have fixed it; the fault
    was that the courses did not step.

    ## What a laid course actually does

    A tile's head bears on the deck; its tail bears on the HEAD of the course
    below. So the covering is one thickness at the head and two at the tail,
    and the exposed surface of every course is a shallow ramp falling from
    `2T` at its tail to `T` at its head, with a riser of most of `T` showing at
    each course line. Two things then read at distance, and neither needs the
    shadow map to resolve a 5 cm feature:

      * the riser turns away from the sun and shades by N·L;
      * the ramp sits `atan(T/exposure)` = 19° shallower than the deck, so
        consecutive courses take measurably different key light.

    At the locked 09:30 rig (elevation 38°, azimuth 125°) a `T` of 0.055 m
    throws 0.028–0.047 m of shadow across a 0.16 m exposure on the sun-facing
    slopes — 18–29% of every course — and rakes the away-facing slopes
    completely. 0.055 m is also the right number physically: it is a pantile's
    standing height, and Art Bible §3's 0.16 m exposure is a pantile gauge.

    Course-scale colour rides in COLOR_0. Tile-scale colour and roughness stay
    in the material, where they belong — but they were invisible until the UV
    fix below, because the covering was sampling its 4 m texture over 1.17 m of
    roof and printing 0.047 m tiles under 0.16 m courses.
    """
    rng = rng_for(asset_id, "courses", i)
    # One kiln for the whole building — see `kiln_batch`.
    batch = kiln_batch(asset_id, mat)
    s0_all, s1_all = sl.s_min(), sl.s_max()
    span = s1_all - s0_all
    if span <= 1e-4:
        return
    e = exposure * (1.0, 2.2, 5.0, 12.0)[min(detail, 3)]
    n = max(1, int(math.ceil(span / e)))
    e = span / n
    sc = _uv_scale(mat)
    b = M._Builder()
    for k in range(n):
        s0 = s0_all + k * e
        s1 = s0 + e
        lap = e * 0.34
        band = _clip(sl.poly2, 0.0, 1.0, s1)                 # s <= s1
        band = _clip(band, 0.0, -1.0, -(s0 - lap))           # s >= s0 - lap
        if len(band) < 3:
            continue
        # Art Bible §6: position jitter on every repeated element.
        jit = rng.uniform(-0.004, 0.004)
        tail_s = s0 - lap
        head, tail = TILE_T + jit, TILE_T * 2.0 + jit

        def off_at(s):
            """The ramp: 2T at the course tail falling to T at its head."""
            t = (s - tail_s) / max(s1 - tail_s, 1e-6)
            return tail + (head - tail) * float(np.clip(t, 0.0, 1.0))

        col = _course_colour(rng, mat, batch)
        top = [sl.p3(t, s, off_at(s)) for t, s in band]
        b.poly(top, [(t * sc, s * sc) for t, s in band], None, col)
        # The tail lip — the visible course step, now standing proud of the
        # course below rather than terminating in its plane.
        edge = [(t, s) for t, s in band if s <= tail_s + 1e-4]
        if len(edge) >= 2:
            e0, e1 = edge[0], edge[-1]
            lo0, lo1 = sl.p3(*e0, head * 0.35), sl.p3(*e1, head * 0.35)
            hi0, hi1 = sl.p3(*e0, tail), sl.p3(*e1, tail)
            quad = [lo0, lo1, hi1, hi0]
            uvq = [(e0[0] * sc, e0[1] * sc), (e1[0] * sc, e1[1] * sc),
                   (e1[0] * sc, (e1[1] + head) * sc), (e0[0] * sc, (e0[1] + head) * sc)]
            nrm = -_u(sl.ds)
            if float(np.dot(np.cross(quad[1] - quad[0], quad[2] - quad[0]), nrm)) < 0:
                quad.reverse()
                uvq.reverse()
            b.poly(quad, uvq, nrm, col)
    out.add(b.build(mat))


def _thatch_slope(out, sl, asset_id, i, mat, detail=0):
    """Thatch is mass, not courses: a 0.35 m shell with a rolled eaves.

    Stacked courses read as corrugated sheet, which is the opposite of thatch —
    whose whole character is depth and the absence of any hard edge.
    """
    rng = rng_for(asset_id, "thatch", i)
    thick = THATCH_T
    b = M._Builder()
    sc = _uv_scale(mat)
    poly = sl.poly2
    s0, s1 = sl.s_min(), sl.s_max()
    # Sag: thatch settles over its life, most in the middle of the slope.
    n = max(2, (6, 3, 2, 1)[min(detail, 3)])
    for k in range(n):
        a = s0 + (s1 - s0) * k / n
        c = s0 + (s1 - s0) * (k + 1) / n
        band = _clip(_clip(poly, 0.0, 1.0, c), 0.0, -1.0, -a)
        if len(band) < 3:
            continue
        def off(s):
            t = (s - s0) / max(s1 - s0, 1e-6)
            return thick - math.sin(t * math.pi) * 0.05 + rng.uniform(-0.01, 0.01)
        b.poly([sl.p3(t, s, off(s)) for t, s in band],
               [(t * sc, s * sc) for t, s in band], sl.n)
    # The RAKE edge, closed. A thatch coat is 0.34 m of stems and its cut end
    # shows at the verge; without this the mass is an open shell and a thatched
    # gable reads as a paper ramp with a flat underside — which is exactly how
    # it rendered. The eaves edge is left to the rolled facets below.
    n_e = len(poly)
    for k in range(n_e):
        t0, ss0 = poly[k]
        t1, ss1 = poly[(k + 1) % n_e]
        if abs(ss1 - ss0) < 0.2:
            continue                      # eaves or ridge, not a rake
        quad = [sl.p3(t0, ss0, 0.0), sl.p3(t1, ss1, 0.0),
                sl.p3(t1, ss1, thick), sl.p3(t0, ss0, thick)]
        b.poly(quad, [(t0 * sc, ss0 * sc), (t1 * sc, ss1 * sc),
                      ((t1 + thick) * sc, ss1 * sc), ((t0 + thick) * sc, ss0 * sc)])

    # Rolled eaves: three facets curling under, which is the silhouette that
    # says "thatch" from across the square.
    edge = _clip(poly, 0.0, 1.0, s0 + 0.02)
    if len(edge) >= 2:
        e0, e1 = edge[0], edge[-1]
        prev = (thick, 0.0)
        for a in (0.55, 1.05, 1.5):
            o = thick * math.cos(a)
            d = -thick * 0.85 * math.sin(a)
            quad = [sl.p3(e0[0], e0[1] + prev[1], prev[0]),
                    sl.p3(e1[0], e1[1] + prev[1], prev[0]),
                    sl.p3(e1[0], e1[1] + d, o), sl.p3(e0[0], e0[1] + d, o)]
            b.poly(quad, [(e0[0] * sc, (e0[1] + prev[1]) * sc),
                          (e1[0] * sc, (e1[1] + prev[1]) * sc),
                          (e1[0] * sc, (e1[1] + d) * sc),
                          (e0[0] * sc, (e0[1] + d) * sc)], -_u(sl.ds))
            prev = (o, d)
    out.add(b.build(mat))


def _deck(out, sl, mat="oak_dark", cover=None):
    """Rafters and boarding: closes the underside so the roof is never paper.

    Also what the eaves soffit shows from below, which is where a thin roof
    gives itself away at the gameplay camera.

    The UPPER face takes the covering's material even though the tiles hide it.
    That is not decoration: the automatic LOD decimator eats the thin course
    geometry first, so at 40 m the deck IS the roof — and a deck in oak read as
    a town of dark brown roofs from the air while every close-up showed
    terracotta. Colour has to survive the simplifier.
    """
    top = M._Builder()
    csc = _uv_scale(cover or mat)
    top.poly([sl.p3(t, s, 0.0) for t, s in sl.poly2],
             [(t * csc, s * csc) for t, s in sl.poly2], sl.n)
    out.add(top.build(cover or mat))
    b = M._Builder()
    b.poly([sl.p3(t, s, -DECK_T) for t, s in reversed(sl.poly2)], None, -sl.n)
    n = len(sl.poly2)
    for i in range(n):
        t0, s0 = sl.poly2[i]
        t1, s1 = sl.poly2[(i + 1) % n]
        quad = [sl.p3(t0, s0, -DECK_T), sl.p3(t1, s1, -DECK_T),
                sl.p3(t1, s1, 0.0), sl.p3(t0, s0, 0.0)]
        b.poly(quad)
    out.add(b.build(mat))


def _ridge_cap(out, a, b, mat, asset_id, half=0.105):
    """Half-round ridge tiles. Derived from the ridge line, so it cannot sit
    beside the ridge or float over it."""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    d = b - a
    ln = float(np.linalg.norm(d))
    if ln < 0.05:
        return
    rng = rng_for(asset_id, "ridge")
    prof = []
    for k in range(7):
        ang = math.pi * k / 6.0
        prof.append((math.cos(ang) * half, math.sin(ang) * half * 0.78))
    prof.append((-half, -half * 0.45))
    prof.append((half, -half * 0.45))
    n = max(1, int(ln / 0.42))
    step = ln / n
    for i in range(n):
        seg = M.prism([(float(x), float(y)) for x, y in prof], step * 0.98,
                      chamfer=0.0)
        # NO `+ pi/2` here. `M.prism` extrudes along **Z**, so the yaw that puts
        # its length on the ridge is exactly atan2(d.x, d.z). The extra quarter
        # turn is the idiom for `M.box`, whose length is on X — and copying it
        # onto a prism laid every ridge tile in Hearthmere ACROSS the ridge
        # instead of along it, so a ridge read as a row of crosswise rungs.
        # `_thatch_ridge` had the same line and one cap the length of the whole
        # ridge, which is the 6.9 m plank that was seen skewering a roof. D-036.
        seg.rotate_y(math.atan2(d[0], d[2]))
        p = a + d * ((i + 0.5) / n)
        seg.translate(float(p[0]), float(p[1]) + rng.uniform(-0.004, 0.004),
                      float(p[2]))
        out.add(seg.with_material(mat))


def _du_span(plate, sl):
    """The plate's extent along this slope's eaves direction, in slope `t`.

    `du` is horizontal (the solver builds it from the eaves line), so this is a
    pure plan projection. It is the number the along-the-eaves reach test needs
    and `_plate_dist` cannot supply: distance-to-polygon is isotropic, so a
    board 1.2 m past the gable and a board 1.2 m past the eaves measure the
    same, and the first is a defect while the second is the overhang.
    """
    o = sl.origin
    ts = [float(np.array([px - o[0], 0.0, pz - o[2]], float) @ sl.du)
          for (px, pz) in plate.pts]
    return min(ts), max(ts)


def _ok_spans(pred, t0, t1, samples=17, minlen=0.20):
    """Every sub-interval of [t0, t1] on which `pred` holds, refined.

    The reach guard used to test a board's MIDPOINT only, so a board whose
    middle sat over the plate and whose end was two metres past it passed
    whole — the barge board hanging in clear air off a gable end, and the plank
    crossing `pw30-free.png` attached to nothing. Clipping is the right answer
    rather than accept-or-reject: on a hipped or valley-clipped slope part of
    the eaves genuinely is over the building and part is not, and where a wing
    crosses an eaves the board is interrupted in the MIDDLE and has to become
    two boards.
    """
    if t1 - t0 <= 1e-6:
        return []
    hits = [t0 + (t1 - t0) * k / (samples - 1) for k in range(samples)]
    flags = [bool(pred(t)) for t in hits]

    def refine(a, b):
        """a fails, b holds -> the boundary."""
        for _ in range(9):
            m = (a + b) * 0.5
            if pred(m):
                b = m
            else:
                a = m
        return b

    spans = []
    i = 0
    while i < samples:
        if not flags[i]:
            i += 1
            continue
        j = i
        while j + 1 < samples and flags[j + 1]:
            j += 1
        lo = hits[i] if i == 0 else refine(hits[i - 1], hits[i])
        hi = hits[j] if j == samples - 1 else refine(hits[j + 1], hits[j])
        if hi - lo >= minlen:
            spans.append((lo, hi))
        i = j + 1
    return spans


def _slope_plan(sl):
    """The slope's outline projected onto XZ, wound CCW.

    `_poly_intersect` needs a CCW clipper, and the (t, s) frame's handedness in
    XZ depends on which way the solver ran the eaves — so normalise here rather
    than at every call site.
    """
    poly = [(float(p[0]), float(p[2]))
            for p in (sl.p3(t, s) for t, s in sl.poly2)]
    return poly if _area2(poly) >= 0 else poly[::-1]


def _fascia(out, sl, mat="oak_dark", rafters=True, asset_id="hm", plate=None,
            reach=1e9, verge=0.0, exclude=None):
    """Eaves board and exposed rafter feet.

    Directive §6.2: the roof meets the wall at a junction you can explain. The
    fascia is that explanation, and the rafter feet under it are what make the
    overhang read as carried rather than pasted on.

    The outward direction is taken from the slope's own fall line rather than
    from `cross(du, up)`: `du` runs either way along the eaves depending on how
    the solver wound the polygon, so half the roofs in the town had their
    rafter feet pointing INTO the roof and poking out through the tiles.
    """
    s0 = sl.s_min()
    edge = _clip(sl.poly2, 0.0, 1.0, s0 + 0.02)
    if len(edge) < 2:
        return
    ts = sorted(t for t, _s in edge)
    t0, t1 = ts[0], ts[-1]
    # The eaves board stops at the barge board: it may run the verge overhang
    # past the wall and not one millimetre further. Beyond that the rafters it
    # is nailed to do not exist.
    if plate is not None:
        lo, hi = _du_span(plate, sl)
        t0, t1 = max(t0, lo - verge - 0.05), min(t1, hi + verge + 0.05)

    def carried(t):
        p = sl.p3(t, s0)
        if plate is not None and _plate_dist(plate, p) > reach:
            return False
        # A rear wing interrupts the range's eaves: the board stops at the
        # valley and starts again the other side, because that is where the
        # rafters it is nailed to stop.
        if exclude is not None and _inside(exclude, float(p[0]), float(p[2])):
            return False
        return True

    spans = _ok_spans(carried, t0, t1, minlen=0.15)
    if not spans:
        return
    up = np.array([0.0, 1.0, 0.0])
    out_h = -_u(np.array([sl.ds[0], 0.0, sl.ds[2]]))    # down-slope, level
    ex = _u(np.cross(up, out_h))                        # right-handed basis
    for (b0, b1) in spans:
        board = M.box(b1 - b0, 0.19, 0.048, 0.006, mat)
        M.place(board, sl.p3((b0 + b1) * 0.5, s0, -0.02), ex, up, out_h)
        board.translate(0, -0.085, 0)
        out.add(board)
    if not rafters:
        return
    t0, t1 = spans[0][0], spans[-1][1]
    rng = rng_for(asset_id, "rafters")
    # Inset from the verge: a rafter foot placed exactly on the corner of the
    # eaves overhangs both slopes at once and ends up touching neither, which
    # the mass check reads — correctly — as a timber floating beside the roof.
    t0 += 0.16
    t1 -= 0.16
    # A rafter foot is a RAFTER: it stops at the wall it bears on. The verge
    # overhang beyond the gable is carried by the barge board, not by common
    # rafters, so a foot out there projects past the gable end over nothing.
    if plate is not None:
        lo, hi = _du_span(plate, sl)
        t0, t1 = max(t0, lo + 0.10), min(t1, hi - 0.10)
    ln = t1 - t0
    if ln < 0.2:
        return
    n = max(2, int(ln / 0.55))
    for i in range(n + 1):
        t = t0 + ln * i / n
        # A rafter foot only exists where there is a rafter: on a hip or a
        # clipped slope the eaves span narrows as it rises, and a foot placed
        # past the end of it hangs in mid-air. Twelve did, and the mass check
        # caught every one.
        if not _inside(sl.poly2, t, s0 + 0.12, eps=0.02):
            continue
        if plate is not None and _plate_dist(plate, sl.p3(t, s0)) > reach:
            continue
        if not carried(t):
            continue
        r = M.box(0.075, 0.125, 0.36, 0.006, mat)
        M.place(r, sl.p3(t, s0 + 0.10, -DECK_T - 0.030), ex, up, out_h)
        # `spin_y`, not `rotate_y`. `rotate_y` turns about the WORLD origin, so
        # a foot already placed at radius r is translated by ~r*theta: 0.10 m
        # out from under the deck on a 5 m half-plate, and clean off the roof
        # on a granary-sized one. See core/mesh.py:spin_y.
        r.spin_y(rng.uniform(-0.02, 0.02))
        out.add(r)


def _plate_dist(plate, p3):
    """Distance in plan from a point to the plate polygon (0 inside).

    Trim — fascia, rafter feet, barge boards — is derived from a slope's own
    outline, and a slope that has been clipped (a hip, a valley, a jerkinhead)
    can leave an edge whose ends no longer sit over the building. A board there
    is a timber floating in the air beside the roof, which is what the mass
    check found. Anything further from the wall than the roof itself can
    oversail is refused.
    """
    x, z = float(p3[0]), float(p3[2])
    if _inside(list(plate.pts), x, z):
        return 0.0
    best = 1e18
    n = len(plate.pts)
    for i in range(n):
        a = np.asarray(plate.pts[i], float)
        b = np.asarray(plate.pts[(i + 1) % n], float)
        d = b - a
        ln = float(np.linalg.norm(d))
        if ln < 1e-9:
            continue
        u = d / ln
        t = float(np.clip((np.array([x, z]) - a) @ u, 0.0, ln))
        best = min(best, float(np.linalg.norm(np.array([x, z]) - (a + u * t))))
    return best


def _party_lines(plate):
    out = []
    for i in range(len(plate)):
        a, b, k = plate.edge(i)
        if k == "party":
            out.append((a, b))
    return out


def _near_party(plate, p3, tol=0.5):
    x, z = float(p3[0]), float(p3[2])
    for a, b in _party_lines(plate):
        d = b - a
        ln = float(np.linalg.norm(d))
        if ln < 1e-6:
            continue
        u = d / ln
        t = np.clip((np.array([x, z]) - a) @ u, 0.0, ln)
        if float(np.linalg.norm(np.array([x, z]) - (a + u * t))) < tol:
            return True
    return False


def _verge(out, sl, plate, mat="oak_dark", reach=1e9, exclude=None):
    """Barge boards down the rake of a gable, following the roof line."""
    poly = sl.poly2
    if len(poly) < 3:
        return
    n = len(poly)
    smin = sl.s_min()
    for i in range(n):
        t0, s0 = poly[i]
        t1, s1 = poly[(i + 1) % n]
        if abs(s1 - s0) < 0.25:
            continue                     # eaves or ridge, not a rake
        # A verge runs STRAIGHT UP THE SLOPE: it is the gable end, so it is at
        # constant `t`. A hip line and a valley run diagonally, and boarding one
        # puts a plank across the tiles.
        #
        # The old test — "does this edge start part-way up the slope" — catches
        # a valley and misses a jerkinhead, whose hip lines spring from the
        # EAVES. So `half_hip` boarded all four of its hip lines, on the same
        # lines `_ridge_cap` was already capping at roof.py:1305, and the two
        # interpenetrated. It is the reason half_hip has been unusable and
        # three waterfront venues were gabled to dodge it.
        if abs(t1 - t0) > 0.20 * abs(s1 - s0):
            continue
        if min(s0, s1) > smin + 0.12:
            continue
        if _near_party(plate, sl.p3((t0 + t1) * 0.5, (s0 + s1) * 0.5)):
            continue
        # BOTH ends, and clip rather than accept-or-reject. Testing the
        # midpoint let a rake whose foot was over the wall and whose head was
        # two metres past it ship whole, which is the board hanging in clear
        # air off the left gable in `rope-free.png`. A clipped or valleyed
        # slope legitimately has part of its rake over the building and part
        # not, so the honest answer is to shorten the board to the part that
        # is carried.
        p0 = np.array([t0, s0], float)
        p1 = np.array([t1, s1], float)

        def ok(u):
            q = p0 + (p1 - p0) * u
            p = sl.p3(q[0], q[1])
            if exclude is not None and _inside(exclude, float(p[0]), float(p[2])):
                return False
            return _plate_dist(plate, p) <= reach

        u0, u1 = 0.0, 1.0
        f0, f1 = ok(0.0), ok(1.0)
        if not f0 and not f1:
            continue
        if not f0 or not f1:
            a, b = (0.0, 1.0) if f1 else (1.0, 0.0)   # a is out, b is in
            for _ in range(10):
                m = (a + b) * 0.5
                a, b = (a, m) if ok(m) else (m, b)
            if f1:
                u0 = b
            else:
                u1 = b
        q0, q1 = p0 + (p1 - p0) * u0, p0 + (p1 - p0) * u1
        t0, s0 = float(q0[0]), float(q0[1])
        t1, s1 = float(q1[0]), float(q1[1])
        ln = math.hypot(t1 - t0, s1 - s0)
        if ln < 0.20:
            continue
        # The board hangs BELOW the roof plane and covers the rafter feet at
        # the verge; its depth is perpendicular to the slope, not laid on it.
        # Laid on it, it reads as a plank left on the tiles.
        bb = M.box(ln, 0.06, 0.235, 0.006, mat)
        ang = math.atan2(s1 - s0, t1 - t0)
        bb.rotate_z(ang)
        M.place(bb, sl.p3((t0 + t1) * 0.5, (s0 + s1) * 0.5, -0.075),
                sl.du, sl.ds, sl.n)
        out.add(bb)


# ---------------------------------------------------------------------------
# Closure — the reason a gable end can never be forgotten
# ---------------------------------------------------------------------------

def _closures(roof, plate, mat, out):
    """Fill every plate edge from the wall head up to the roof above it.

    This is asked of the FINISHED roof surface rather than derived per kind, so
    a gable, a jerkinhead's truncated triangle, a gambrel's pentagon and a
    lean-to's rake all close correctly with one piece of code — and a new roof
    kind cannot ship with an open end.
    """
    made = 0
    for i in range(len(plate)):
        a2, b2, kindk = plate.edge(i)
        if kindk in ("party", "abut"):
            # "party" is closed by the shared wall itself. "abut" runs into a
            # taller wall that is already there — a lean-to head, or a wing's
            # plate where it laps back into the main range — so a closure panel
            # on it would be a wall built inside another building.
            continue
        d = b2 - a2
        ln = float(np.linalg.norm(d))
        if ln < 0.2:
            continue
        dh = d / ln
        nrm = _perp(dh)
        n = max(6, int(ln / 0.35))
        prof = []
        for k in range(n + 1):
            t = k / n
            p = a2 + d * t
            # Sample just inside the wall face: exactly on it, a floating-point
            # miss puts the sample outside the roof outline and punches a hole
            # in the closure.
            q = p - nrm * 0.04
            # The DECK plane, not the covering: a gable wall rises to the
            # underside of the roof and the covering oversails it. Asking
            # `surface_y` and subtracting TILE_T was the same thing only while
            # every roof was tiled.
            y = roof.deck_y(q[0], q[1])
            prof.append((t * ln, plate.y if y is None else max(plate.y, y)))
        if max(y for _t, y in prof) - plate.y < 0.06:
            continue
        poly = [(t, plate.y - 0.05) for t, _y in prof]
        poly += [(t, y) for t, y in reversed(prof)]
        panel = M.prism([(float(t), float(y)) for t, y in poly],
                        plate.thickness, chamfer=0.0)
        M.place(panel, _h3(a2 + dh * 0.0, 0.0),
                np.array([dh[0], 0.0, dh[1]]), np.array([0.0, 1.0, 0.0]),
                np.array([nrm[0], 0.0, nrm[1]]))
        panel.translate(0, 0, 0)
        out.add(panel.with_material(mat))
        made += 1
    return made


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def roof_from_plate(plate, kind="gable", pitch=0.85, overhang=0.42,
                    asset_id="hm.roof", mat="terracotta", timber_mat="oak_dark",
                    verge=None, clip_against=None, detail=0, close=True,
                    trim_exclude=None, **opts):
    """Build a roof on `plate`. Its position comes from the plate and nowhere
    else — there is deliberately no `y` parameter.

        plate = wall_plate(footprint, floor_y + eaves_height)
        roof  = roof_from_plate(plate, "half_hip", 0.9, 0.45, asset_id)

    `clip_against` is another Roof (the main range) whose planes cut this one:
    that cut is the valley where a wing meets it.
    """
    if not isinstance(plate, Plate):
        raise TypeError("roof_from_plate needs a Plate from wall_plate(); a bare "
                        "polygon has no bearing height and a roof may not invent one")
    verge = overhang * 0.62 if verge is None else verge
    slopes, ridge_y, ridge_line = _rect_slopes(plate, kind, pitch, overhang,
                                               verge, mat, opts)

    if clip_against is not None:
        # ONLY the main slopes whose own plan outline laps this plate. A plane
        # is infinite and a roof is not: the range's FRONT slope, extended
        # backwards over a rear wing, climbs a metre for every metre of run and
        # sits above the wing everywhere — so clipping against it deletes the
        # whole wing. The valley is where the wing meets the surface that is
        # actually there, which is the slope standing over the lap.
        for other in clip_against.slopes:
            lap = _poly_intersect(plate.pts, _slope_plan(other))
            if abs(_area2(lap)) < 0.25:
                continue
            for sl in slopes:
                sl.clip_plane(other)

    # A degenerate slope is never legitimate: it means a clip ate a face, and
    # the trim that follows (ridge cap, barge board, fascia, rafter feet) would
    # then be built in mid-air over an open box. Drop them unconditionally,
    # then prove the survivors actually cover the plate they were asked to
    # roof. D-034: this guard is the reason a roofless building cannot ship.
    slopes = [s for s in slopes if len(s.poly2) >= 3 and s.area() > 0.05]
    if not slopes:
        raise RuntimeError(
            f"roof_from_plate({kind!r}, {asset_id!r}): every slope was clipped "
            f"away. A roof with no slopes is a hole, not a roof.")
    # Compare like with like: both areas are plan projections onto XZ.
    covered = 0.0
    for s in slopes:
        xz = [(float(p[0]), float(p[2])) for p in (s.p3(t, u) for t, u in s.poly2)]
        covered += abs(_area2(xz))
    plan_area = abs(_area2(plate.pts))
    # A wing's plate deliberately runs back INTO the main range — that overlap
    # is what makes the two planes cross, and the crossing is the valley. The
    # main roof already covers it, so requiring the wing to cover it too would
    # forbid the one plan form the town most needs. Discount the area the main
    # roof genuinely roofs — its SLOPES in plan, which includes the overhang,
    # not its plate — and hold the wing to the same standard on the rest.
    need = 0.80
    if clip_against is not None:
        shaded = 0.0
        for other in clip_against.slopes:
            shaded += abs(_area2(_poly_intersect(plate.pts, _slope_plan(other))))
        plan_area = max(0.0, plan_area - min(shaded, plan_area))
        # The valley is a diagonal across the survivor, so a clipped wing never
        # covers its remainder as squarely as a free-standing roof does.
        need = 0.62
    if plan_area > 0.5 and covered < need * plan_area:
        raise RoofTooSmall(
            f"roof_from_plate({kind!r}, {asset_id!r}): slopes cover "
            f"{covered:.1f} m2 of a {plan_area:.1f} m2 plate "
            f"({covered / plan_area:.0%}); a roof must cover its plate.")

    out = Roof()
    out.slopes = slopes
    out.ridge_y = ridge_y
    out.eaves_y = plate.y - pitch * overhang
    out.plate = plate
    out.kind = kind
    out.pitch = pitch
    out.overhang = overhang
    out.mat = mat
    out.ridge_line = ridge_line
    out.cover_t = cover_thickness(mat)

    # The covering is a FAMILY, not one key: `thatch_new` and `thatch_old`
    # are the same construction as `thatch` and must take the same mass
    # build, not be tiled like a slate. D-034.
    thatched = is_thatch(mat)
    for i, sl in enumerate(slopes):
        _deck(out, sl, timber_mat, cover=mat)
        if thatched:
            _thatch_slope(out, sl, asset_id, i, mat, detail)
        else:
            _tile_slope(out, sl, asset_id, i, EXPOSURE, mat, detail)
            if detail <= 1:
                reach = overhang + verge + 0.45
                _fascia(out, sl, timber_mat, rafters=detail == 0,
                        asset_id=asset_id, plate=plate, reach=reach,
                        verge=verge, exclude=trim_exclude)
                if kind not in ("hip", "pyramid"):
                    _verge(out, sl, plate, timber_mat, reach=reach,
                           exclude=trim_exclude)

    if ridge_line is not None and detail <= 2:
        if thatched:
            _thatch_ridge(out, ridge_line, asset_id, detail, mat)
        else:
            _ridge_cap(out, ridge_line[0], ridge_line[1], "ridge", asset_id)
        # Hip ridges: cap every line where two slopes meet at a corner.
        if kind in ("hip", "pyramid", "half_hip") and detail == 0:
            for sl in slopes:
                if sl.kind != "hip":
                    continue
                poly = sl.poly2
                for i in range(len(poly)):
                    t0, s0 = poly[i]
                    t1, s1 = poly[(i + 1) % len(poly)]
                    if abs(s1 - s0) < 0.3:
                        continue
                    _ridge_cap(out, sl.p3(t0, s0, TILE_T * 0.5),
                               sl.p3(t1, s1, TILE_T * 0.5), "ridge",
                               f"{asset_id}.hip{i}", half=0.075)

    if close:
        _closures(out, plate, plate.wall_mat, out)

    return out


def is_thatch(mat):
    """Any covering laid as a mass of stems rather than as courses."""
    return bool(mat) and str(mat).startswith("thatch")


def _thatch_ridge(out, line, asset_id, detail=0, mat="thatch"):
    """A rolled bundle pinned with crossed hazel spars."""
    a, b = np.asarray(line[0], float), np.asarray(line[1], float)
    d = b - a
    ln = float(np.linalg.norm(d))
    if ln < 0.1:
        return
    rng = rng_for(asset_id, "thatch_ridge")
    t = 0.30
    prof = [(math.cos(k * math.pi / 8.0) * t, math.sin(k * math.pi / 8.0) * t * 0.72)
            for k in range(9)]
    prof += [(-t, -t * 0.35), (t, -t * 0.35)]
    cap = M.prism([(float(x), float(y)) for x, y in prof], ln, chamfer=0.0)
    cap.rotate_y(math.atan2(d[0], d[2]))      # Z-extruded: see _ridge_cap
    mid = (a + b) * 0.5
    cap.translate(float(mid[0]), float(mid[1]) + 0.05, float(mid[2]))
    out.add(cap.with_material(mat))
    if detail > 0:
        return
    n = max(3, int(ln / 0.6))
    for i in range(n):
        p = a + d * ((i + 0.5) / n)
        for sgn in (-1, 1):
            spar = M.cylinder(0.016, 0.62, 6, 0.003, "oak_weathered")
            spar.rotate_z(math.pi * 0.5)
            spar.rotate_y(math.atan2(d[0], d[2]) + sgn * 0.6)
            spar.translate(float(p[0]), float(p[1]) + 0.28,
                           float(p[2]) + rng.uniform(-0.02, 0.02))
            out.add(spar)


# ---------------------------------------------------------------------------
# Things that pass through a roof
# ---------------------------------------------------------------------------

def chimney_through(roof, x, z, base_y, asset_id, section=0.62, mat="stone",
                    above=0.85, pot=True, detail=0):
    """A stack from `base_y` up THROUGH the roof, with a lead apron where it
    penetrates.

    The height is derived from the roof surface it pierces, so "the chimney
    does not emerge" is not a state this can reach. v1 shipped three chimneys
    buried 2.4–2.9 m inside a roof because their height was authored.
    """
    surf = roof.surface_y(x, z)
    top = (roof.ridge_y if surf is None else max(surf, roof.eaves_y)) + above
    if surf is None:
        top = roof.ridge_y + above
    h = top - base_y
    if h < 0.5:
        return M.Group(), top
    out = M.Group()
    rng = rng_for(asset_id, "chimney")
    lean = rng.uniform(-0.012, 0.012)
    stack = M.box(section, h, section * 0.86, 0.02, mat)
    stack.translate(x, base_y + h * 0.5, z)
    out.add(stack)
    cap = M.box(section * 1.24, 0.15, section * 1.06, 0.02, mat)
    cap.translate(x + lean, top + 0.07, z)
    out.add(cap)
    if pot:
        p = M.lathe([(0.125, 0), (0.142, 0.06), (0.132, 0.32), (0.152, 0.38)],
                    12, "terracotta", close_top=False)
        p.translate(x + rng.uniform(-0.05, 0.05), top + 0.14,
                    z + rng.uniform(-0.05, 0.05))
        out.add(p)
    # Lead apron / soakers where the stack breaks the covering.
    if surf is not None and detail == 0:
        ap = M.box(section * 1.35, 0.05, section * 1.3, 0.01, "lead")
        ap.translate(x, surf + 0.03, z)
        out.add(ap)
    return out, top


def dormer(roof, x, z, asset_id, width=1.15, height=1.25, mat=None,
           wall_mat="plaster", timber_mat="oak_dark", glass_mat="glass",
           detail=0):
    """A gabled dormer sitting ON the slope it interrupts.

    Its sill is the roof surface at (x, z), so it cannot float above the tiles
    or sink into them; its cheeks are cut to the slope for the same reason.
    """
    sl = roof.slope_at(x, z)
    if sl is None:
        return M.Group()
    mat = mat or roof.mat
    out = M.Group()
    st = sl._st(x, z)
    if st is None:
        return out
    t0, s0 = st
    du, ds, n = sl.du, sl.ds, sl.n
    base = sl.p3(t0, s0, 0.0)
    depth = width * 0.85
    # Front face rises vertically from the slope.
    front = sl.p3(t0, s0, 0.0)
    fy = float(front[1])
    horiz = _u(np.array([ds[0], 0.0, ds[2]]))     # up-slope, horizontally
    face_c = np.array([x, fy + height * 0.5, z], float)
    face = M.box(width, height, 0.12, CHAMFER, wall_mat)
    face.rotate_y(math.atan2(du[0], du[2]) + math.pi * 0.5)
    face.translate(*face_c)
    out.add(face)
    win = M.box(width * 0.62, height * 0.6, 0.05, 0.004, glass_mat)
    win.rotate_y(math.atan2(du[0], du[2]) + math.pi * 0.5)
    win.translate(face_c[0] - horiz[0] * 0.08, face_c[1] + 0.05,
                  face_c[2] - horiz[2] * 0.08)
    out.add(win)
    # Cheeks: triangles cut to the slope, so the join is tight by construction.
    for sgn in (-1, 1):
        pts = []
        for k in range(5):
            f = k / 4.0
            p = sl.p3(t0 + sgn * width * 0.5, s0 + depth * f, 0.0)
            pts.append((depth * f, float(p[1]) - fy))
        prof = [(0.0, 0.0), (0.0, height)] + [(a, max(b, 0.0)) for a, b in pts][::-1]
        cheek = M.prism([(float(a), float(b)) for a, b in prof], 0.09,
                        chamfer=0.0)
        M.place(cheek, np.array([x, fy, z]) + du * (sgn * width * 0.5),
                horiz, np.array([0.0, 1.0, 0.0]), du)
        out.add(cheek.with_material(wall_mat))
    # Its own little roof, from its own little plate — same rule as the big one.
    c2 = np.array([x, 0.0, z]) + np.array([horiz[0], 0.0, horiz[2]]) * depth * 0.5
    u2 = np.array([du[0], du[2]])
    v2 = np.array([horiz[0], horiz[2]])
    quad = [(c2[0] - u2[0] * width * 0.55 - v2[0] * depth * 0.5,
             c2[2] - u2[1] * width * 0.55 - v2[1] * depth * 0.5),
            (c2[0] + u2[0] * width * 0.55 - v2[0] * depth * 0.5,
             c2[2] + u2[1] * width * 0.55 - v2[1] * depth * 0.5),
            (c2[0] + u2[0] * width * 0.55 + v2[0] * depth * 0.5,
             c2[2] + u2[1] * width * 0.55 + v2[1] * depth * 0.5),
            (c2[0] - u2[0] * width * 0.55 + v2[0] * depth * 0.5,
             c2[2] - u2[1] * width * 0.55 + v2[1] * depth * 0.5)]
    dp = Plate(quad, fy + height, edges=["gable", "eaves", "gable", "eaves"],
               thickness=0.10, wall_mat=wall_mat)
    dr = roof_from_plate(dp, "gable", roof.pitch * 0.95, 0.14, f"{asset_id}.dr",
                         mat=mat, timber_mat=timber_mat, detail=max(detail, 1),
                         ridge_axis="v")
    out.add(dr)
    return out
