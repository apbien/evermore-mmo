"""The one deterministic ground.

BUILD_DIRECTIVE section 6 rule 3: *terrain is a function, not a plane.*
`content/town/terrain.json` is the authoritative parameter set; this module and
`client/src/terrain.js` are two ports of the same evaluator and must agree
bit-for-bit. `tools/render/terrain_parity.mjs` proves it on a fixed lattice.

Everything a generator needs::

    from core import terrain

    y  = terrain.height(x, z)          # float, or ndarray for array input
    n  = terrain.normal(x, z)          # (3,) or (N, 3), unit length, Y-up
    w  = terrain.is_water(x, z)        # bool / ndarray
    wl = terrain.water_level()         # the one water surface elevation

    lvl  = terrain.pad_level("hm.pad.market_square")   # exact, flat, no noise
    rect = terrain.pad("hm.pad.blacksmith")            # centre/half/rot/level

A generator that places an object derives Y from `height`, never from 0.0.
A generator whose venue must stand on level ground uses `pad_level`, which is
exactly what `height` returns anywhere inside that pad's rectangle.

Why the arithmetic looks pedantic
---------------------------------
Every expression here is mirrored character-for-character in the JavaScript
port. Only +, -, *, /, comparison, floor and sqrt are used inside the sampled
path, because those are the operations IEEE-754 pins exactly in both
languages. Transcendentals appear only when parsing (a pad's rotation is turned
into cos/sin once at load), where a last-ulp difference cannot accumulate.
Everything is float64: float32 anywhere in the chain would blow the 1e-6 parity
budget within one multiply.
"""

from __future__ import annotations

import json
import math
import os

import numpy as np

# mesh only depends on mathx, so this cannot cycle back into terrain.
from core import mesh as M

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
TERRAIN_JSON = os.path.join(REPO, "content/town/terrain.json")

_U32 = np.uint64(0xFFFFFFFF)


# ---------------------------------------------------------------------------
# Scalar/array plumbing
# ---------------------------------------------------------------------------

def _arr(a):
    return np.asarray(a, dtype=np.float64)


def _smoothstep(e0, e1, x):
    """Identical to the JS port. e0/e1 are scalars, x may be an array."""
    if e1 - e0 <= 0.0:
        return np.where(_arr(x) < e0, 0.0, 1.0)
    t = np.clip((_arr(x) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _cos_deg(d):
    """Exact at the cardinal headings.

    `math.sin(math.radians(180))` is 1.2e-16, not 0, and the two languages'
    libm need not round it identically. Every heading authored in terrain.json
    is a multiple of 90, so special-casing them removes the question entirely
    rather than leaving a term that is merely small.
    """
    m = d % 360.0
    if m == 0.0:
        return 1.0
    if m == 90.0 or m == 270.0:
        return 0.0
    if m == 180.0:
        return -1.0
    return math.cos(m * math.pi / 180.0)


def _sin_deg(d):
    m = d % 360.0
    if m == 0.0 or m == 180.0:
        return 0.0
    if m == 90.0:
        return 1.0
    if m == 270.0:
        return -1.0
    return math.sin(m * math.pi / 180.0)


# ---------------------------------------------------------------------------
# Monotone cubic Hermite (Fritsch-Carlson PCHIP)
# ---------------------------------------------------------------------------

class Spline:
    """PCHIP through authored control points, clamped outside the range.

    PCHIP rather than Catmull-Rom because it provably cannot overshoot its own
    control points. An overshooting spline would put a dip below water level in
    the middle of the market square, and nothing downstream would notice.
    """

    __slots__ = ("x", "y", "h", "m")

    def __init__(self, pts):
        self.x = np.array([float(p[0]) for p in pts], np.float64)
        self.y = np.array([float(p[1]) for p in pts], np.float64)
        n = len(self.x)
        if n < 2:
            raise ValueError("spline needs >= 2 control points")
        h = self.x[1:] - self.x[:-1]
        d = (self.y[1:] - self.y[:-1]) / h
        m = np.zeros(n, np.float64)
        m[0] = d[0]
        m[n - 1] = d[n - 2]
        for i in range(1, n - 1):
            if d[i - 1] * d[i] <= 0.0:
                m[i] = 0.0
            else:
                w1 = 2.0 * h[i] + h[i - 1]
                w2 = h[i] + 2.0 * h[i - 1]
                m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
        self.h = h
        self.m = m

    def __call__(self, t):
        t = np.clip(_arr(t), self.x[0], self.x[-1])
        i = np.clip(np.searchsorted(self.x, t, side="right") - 1, 0, len(self.x) - 2)
        hh = self.h[i]
        s = (t - self.x[i]) / hh
        s2 = s * s
        s3 = s2 * s
        return (self.y[i] * (2.0 * s3 - 3.0 * s2 + 1.0)
                + hh * self.m[i] * (s3 - 2.0 * s2 + s)
                + self.y[i + 1] * (-2.0 * s3 + 3.0 * s2)
                + hh * self.m[i + 1] * (s3 - s2))


# ---------------------------------------------------------------------------
# Deterministic value noise
# ---------------------------------------------------------------------------
# Exact 32-bit integer hashing. numpy's uint64 multiply wraps mod 2^64 and we
# mask to 32 bits after every step, which is exactly what JavaScript's
# Math.imul + `>>> 0` pair does. This is the only reason the two ports agree.

def _hash01(ix, iz, seed32):
    a = (np.asarray(ix, np.int64) & 0xFFFFFFFF).astype(np.uint64)
    b = (np.asarray(iz, np.int64) & 0xFFFFFFFF).astype(np.uint64)
    h = (a * np.uint64(0x27D4EB2D)) & _U32
    h = h ^ ((b * np.uint64(0x165667B1)) & _U32)
    h = h ^ np.uint64(seed32)
    h = h ^ (h >> np.uint64(15))
    h = (h * np.uint64(0x2C1B3C6D)) & _U32
    h = h ^ (h >> np.uint64(12))
    h = (h * np.uint64(0x297A2D39)) & _U32
    h = h ^ (h >> np.uint64(15))
    return h.astype(np.float64) / 4294967296.0


def _value_noise(x, z, seed32):
    """Tile-free value noise in [0,1), smootherstep interpolated."""
    ix = np.floor(x)
    iz = np.floor(z)
    fx = x - ix
    fz = z - iz
    ux = fx * fx * fx * (fx * (fx * 6.0 - 15.0) + 10.0)
    uz = fz * fz * fz * (fz * (fz * 6.0 - 15.0) + 10.0)
    ii = ix.astype(np.int64)
    jj = iz.astype(np.int64)
    n00 = _hash01(ii, jj, seed32)
    n10 = _hash01(ii + 1, jj, seed32)
    n01 = _hash01(ii, jj + 1, seed32)
    n11 = _hash01(ii + 1, jj + 1, seed32)
    a = n00 + (n10 - n00) * ux
    b = n01 + (n11 - n01) * ux
    return a + (b - a) * uz


# ---------------------------------------------------------------------------
# Signed distance shapes
# ---------------------------------------------------------------------------

def _sd_polyline(x, z, pts):
    """Unsigned distance to a polyline. Drives the river channel."""
    best = np.full(np.shape(x), 1.0e18, np.float64)
    for k in range(len(pts) - 1):
        ax, az = pts[k]
        bx, bz = pts[k + 1]
        ex, ez = bx - ax, bz - az
        ee = ex * ex + ez * ez
        if ee <= 0.0:
            continue
        wx = x - ax
        wz = z - az
        t = np.clip((wx * ex + wz * ez) / ee, 0.0, 1.0)
        dx = wx - ex * t
        dz = wz - ez * t
        best = np.minimum(best, np.sqrt(dx * dx + dz * dz))
    return best


def _polyline_frame(x, z, pts):
    """(distance, side, arc-length) to the nearest point on a polyline.

    `side` is +1 left of the direction of travel and -1 right; `arc` is
    measured from the first vertex along the polyline. Together they are a
    curvilinear coordinate frame for a river, which is what lets a bending
    reach carry UVs whose V runs down the current everywhere.
    """
    best = np.full(np.shape(x), 1.0e18, np.float64)
    side = np.ones(np.shape(x), np.float64)
    arc = np.zeros(np.shape(x), np.float64)
    run = 0.0
    for k in range(len(pts) - 1):
        ax, az = pts[k]
        bx, bz = pts[k + 1]
        ex, ez = bx - ax, bz - az
        ee = ex * ex + ez * ez
        if ee <= 0.0:
            continue
        ln = np.sqrt(ee)
        wx, wz = x - ax, z - az
        t = np.clip((wx * ex + wz * ez) / ee, 0.0, 1.0)
        dx, dz = wx - ex * t, wz - ez * t
        d = np.sqrt(dx * dx + dz * dz)
        take = d < best
        best = np.where(take, d, best)
        # Cross product z-component of (edge x offset): sign is the side.
        side = np.where(take, np.where(ex * wz - ez * wx >= 0.0, 1.0, -1.0), side)
        arc = np.where(take, run + t * ln, arc)
        run += float(ln)
    return best, side, arc


def _sd_polygon(x, z, poly):
    """Signed distance to a simple polygon; negative inside (iq's sdPolygon)."""
    n = len(poly)
    d = (x - poly[0][0]) * (x - poly[0][0]) + (z - poly[0][1]) * (z - poly[0][1])
    s = np.ones(np.shape(x), np.float64)
    j = n - 1
    for i in range(n):
        vix, viz = poly[i]
        vjx, vjz = poly[j]
        ex, ez = vjx - vix, vjz - viz
        wx = x - vix
        wz = z - viz
        ee = ex * ex + ez * ez
        t = np.clip((wx * ex + wz * ez) / ee, 0.0, 1.0)
        bx = wx - ex * t
        bz = wz - ez * t
        d = np.minimum(d, bx * bx + bz * bz)
        c1 = z >= viz
        c2 = z < vjz
        c3 = (ex * wz) > (ez * wx)
        flip = (c1 & c2 & c3) | ((~c1) & (~c2) & (~c3))
        s = np.where(flip, -s, s)
        j = i
    return s * np.sqrt(d)


def _sd_box(lx, lz, hx, hz):
    """Signed distance to an axis-aligned box in the box's own frame."""
    qx = np.abs(lx) - hx
    qz = np.abs(lz) - hz
    mx = np.maximum(qx, 0.0)
    mz = np.maximum(qz, 0.0)
    return np.sqrt(mx * mx + mz * mz) + np.minimum(np.maximum(qx, qz), 0.0)


# ---------------------------------------------------------------------------
# Authored records
# ---------------------------------------------------------------------------

class Pad:
    """A flat region. Inside the rectangle `height` returns `level` exactly."""

    __slots__ = ("id", "cx", "cz", "hx", "hz", "level", "apron", "rot", "cos", "sin", "note")

    def __init__(self, rec, fallback_level=None):
        self.id = rec["id"]
        self.cx, self.cz = float(rec["centre"][0]), float(rec["centre"][1])
        self.hx, self.hz = float(rec["half"][0]), float(rec["half"][1])
        self.apron = float(rec.get("apron", 1.2))
        self.rot = float(rec.get("rotationDeg", 0.0))
        self.cos, self.sin = _cos_deg(self.rot), _sin_deg(self.rot)
        self.level = float(rec["level"]) if rec.get("level") is not None else float(fallback_level)
        self.note = rec.get("note")

    def local(self, x, z):
        dx = x - self.cx
        dz = z - self.cz
        return self.cos * dx - self.sin * dz, self.sin * dx + self.cos * dz

    def weight(self, x, z):
        lx, lz = self.local(x, z)
        d = _sd_box(lx, lz, self.hx, self.hz)
        return 1.0 - _smoothstep(0.0, self.apron, d)

    def corners(self):
        """World-space rectangle corners, CCW from the -x/-z corner."""
        out = []
        for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            lx, lz = sx * self.hx, sz * self.hz
            out.append((self.cx + self.cos * lx + self.sin * lz,
                        self.cz - self.sin * lx + self.cos * lz))
        return out

    def as_dict(self):
        return {"id": self.id, "centre": [self.cx, self.cz], "half": [self.hx, self.hz],
                "level": self.level, "apron": self.apron, "rotationDeg": self.rot,
                **({"note": self.note} if self.note else {})}


class Ramp:
    __slots__ = ("id", "cx", "cz", "hx", "hz", "low", "high", "apron", "cos", "sin")

    def __init__(self, rec):
        self.id = rec["id"]
        self.cx, self.cz = float(rec["centre"][0]), float(rec["centre"][1])
        self.hx, self.hz = float(rec["half"][0]), float(rec["half"][1])
        self.low, self.high = float(rec["low"]), float(rec["high"])
        self.apron = float(rec.get("apron", 1.0))
        hd = float(rec.get("headingDeg", 0.0))
        self.cos, self.sin = _cos_deg(hd), _sin_deg(hd)

    def eval(self, x, z):
        dx = x - self.cx
        dz = z - self.cz
        lx = self.cos * dx - self.sin * dz
        lz = self.sin * dx + self.cos * dz
        t = np.clip((lz + self.hz) / (2.0 * self.hz), 0.0, 1.0)
        level = self.low + (self.high - self.low) * t
        d = _sd_box(lx, lz, self.hx, self.hz)
        return level, 1.0 - _smoothstep(0.0, self.apron, d)


# ---------------------------------------------------------------------------
# Terrain
# ---------------------------------------------------------------------------

class Terrain:
    def __init__(self, doc):
        self.doc = doc
        self.extent = doc["extent"]
        self.rings = doc["lod"]["rings"]
        self.zs = Spline(doc["fall"]["zSpine"])
        self.xs = Spline(doc["fall"]["xSpine"])

        r = doc["roughness"]
        self.n_seed = int(r["seed"]) & 0xFFFFFFFF
        self.n_oct = int(r["octaves"])
        self.n_freq = float(r["baseFrequency"])
        self.n_lac = float(r["lacunarity"])
        self.n_gain = float(r["gain"])
        self.n_amp_town = float(r["amplitudeTown"])
        self.n_amp_field = float(r["amplitudeField"])
        self.n_r0 = float(r["townRadius"])
        self.n_r1 = float(r["fieldRadius"])

        w = doc["water"]
        self.water = float(w["level"])
        self.shapes = w["channels"]

        # Hand-authored pads first, then the venue pads generated from the town
        # plan by `tools/plan/ground.py`. Order matters — later pads win where
        # they overlap — and that is the right way round: a venue pad is a
        # building platform cut into the terrace it stands on, so it must be
        # able to override the terrace and never the reverse.
        self.pads = []
        self._generated_ids = set()
        for rec in self._pad_records(doc):
            fb = None
            if rec.get("level") is None:
                fb = float(self.base_spine(rec["centre"][0], rec["centre"][1]))
            self.pads.append(Pad(rec, fb))
        self._pad_by_id = {p.id: p for p in self.pads}

        self.ramps = [Ramp(rec) for rec in doc["ramps"]["list"]]
        self.retaining = doc["retaining"]["list"]
        self.steps = doc["steps"]["list"]
        self.surfaces = doc["surfaces"]

    @staticmethod
    def _authored_pad_records(doc):
        return list(doc["pads"]["list"])

    def _pad_records(self, doc):
        recs = self._authored_pad_records(doc)
        gen = doc["pads"].get("generated", {}).get("list", [])
        for rec in gen:
            self._generated_ids.add(rec["id"])
        return recs + list(gen)

    # -- the height function ------------------------------------------------

    def base_spine(self, x, z):
        """The fall alone: no noise, no water, no pads. Used for `level: null`."""
        return self.zs(z) + self.xs(x)

    def roughness(self, x, z):
        rad = np.sqrt(x * x + z * z)
        amp = self.n_amp_town + (self.n_amp_field - self.n_amp_town) * \
            _smoothstep(self.n_r0, self.n_r1, rad)
        total = np.zeros(np.shape(x), np.float64)
        norm = 0.0
        a = 1.0
        f = self.n_freq
        for o in range(self.n_oct):
            total = total + (_value_noise(x * f, z * f, (self.n_seed + o * 7919) & 0xFFFFFFFF) * 2.0 - 1.0) * a
            norm = norm + a
            a = a * self.n_gain
            f = f * self.n_lac
        return (total / norm) * amp

    def height(self, x, z):
        scalar = np.isscalar(x) and np.isscalar(z)
        X = _arr(x)
        Z = _arr(z)
        X, Z = np.broadcast_arrays(X, Z)
        X = np.ascontiguousarray(X, np.float64)
        Z = np.ascontiguousarray(Z, np.float64)

        h = self.base_spine(X, Z)
        h = h + self.roughness(X, Z)

        # 3. water shapes carve toward an ABSOLUTE bed elevation
        for s in self.shapes:
            h = h + (float(s["bedLevel"]) - h) * self.shape_weight(s, X, Z)

        # 4. pads flatten
        for p in self.pads:
            w = p.weight(X, Z)
            h = h + (p.level - h) * w

        # 5. ramps cut constant-gradient corridors through the scarps
        for r in self.ramps:
            level, w = r.eval(X, Z)
            h = h + (level - h) * w

        return float(h) if scalar else h

    # -- derived ------------------------------------------------------------

    NORMAL_EPS = 0.25   # metres; fixed and documented so both ports agree

    def normal(self, x, z):
        scalar = np.isscalar(x) and np.isscalar(z)
        e = self.NORMAL_EPS
        X = _arr(x)
        Z = _arr(z)
        hx = self.height(X + e, Z) - self.height(X - e, Z)
        hz = self.height(X, Z + e) - self.height(X, Z - e)
        nx = -hx
        ny = np.full(np.shape(hx), 2.0 * e, np.float64)
        nz = -hz
        ln = np.sqrt(nx * nx + ny * ny + nz * nz)
        out = np.stack([nx / ln, ny / ln, nz / ln], axis=-1)
        return tuple(float(v) for v in out) if scalar else out

    def slope(self, x, z):
        """Gradient magnitude, dy per horizontal metre. 0 is level."""
        n = self.normal(x, z)
        n = np.asarray(n, np.float64)
        ny = np.clip(n[..., 1], 1e-9, 1.0)
        return np.sqrt(np.maximum(1.0 - ny * ny, 0.0)) / ny

    def water_influence(self, x, z):
        """How strongly the water shapes claim this point, 0..1.

        The same weights `height` uses to carve the channels and the basin.
        Exposed because "how far above the water surface is this" is NOT enough
        to identify a river margin: the town's lowest terrace sits 1.25 m above
        the mere, which put the whole gate flat inside the waterline mud band
        and rendered a third of Hearthmere as tidal silt. Proximity to an
        actual water body is the missing term.
        """
        X, Z = _arr(x), _arr(z)
        X, Z = np.broadcast_arrays(X, Z)
        out = np.zeros(np.shape(X), np.float64)
        for s in self.shapes:
            out = np.maximum(out, self.shape_weight(s, X, Z))
        return out

    def shape_weight(self, s, X, Z):
        """How strongly ONE water shape claims a point, 0..1.

        The single implementation of a water outline. `height` and
        `water_influence` each had their own copy and they had to agree
        exactly, which is the sort of duplication that survives right up until
        somebody edits one of them.

        `outlineNoise` is what makes the outline not a drawing. `ad-town-05` §2
        on `t-aerial-sw`: "a mathematically perfect ellipse with a uniform-width
        beach ring ... the Emberflow a dead-straight parallel-sided canal". Both
        readings are exactly right and both are the SDF: an authored polygon
        carved with a constant shelf gives a smooth offset curve, and a polyline
        carved at a constant half-width gives two parallel lines. No amount of
        work on the water itself fixes it, because the defect is the shape.

        Two octaves of value noise displace the distance field before the
        shelf smoothstep. Displacing the FIELD rather than the vertices moves
        the whole graded profile — bed, shelf, waterline and beach all
        together — so the beach stays a beach and simply stops being a ring of
        constant width. The coarse octave (50-80 m) makes bays and headlands;
        the fine one (12-20 m) makes the metre-scale wander that stops a
        shoreline being a curve.

        Authored per shape, because it is not wanted everywhere: the harbour
        basin has a built quay wall on it and the old ford is 3 m wide.
        """
        n = s.get("outlineNoise")
        if "path" in s:
            d = _sd_polyline(X, Z, [(float(p[0]), float(p[1])) for p in s["path"]])
            hw, bank = float(s["halfWidth"]), float(s["bank"])
            if n:
                d = d + self._outline_noise(n, X, Z)
            return 1.0 - _smoothstep(hw, hw + bank, d)
        sd = _sd_polygon(X, Z, [(float(p[0]), float(p[1])) for p in s["polygon"]])
        if n:
            sd = sd + self._outline_noise(n, X, Z)
        return 1.0 - _smoothstep(0.0, float(s["shelf"]), np.maximum(sd, 0.0))

    @staticmethod
    def _outline_noise(n, X, Z):
        """Metres of signed displacement of a water outline. Seeded, so the
        shoreline is byte-identical between builds and a review diff means
        something (BUILD_DIRECTIVE §6.6)."""
        seed = int(n.get("seed", 5150011)) & 0xFFFFFFFF
        f1 = float(n.get("frequency", 0.014))
        a1 = float(n.get("amplitude", 0.0))
        f2 = float(n.get("detailFrequency", f1 * 4.0))
        a2 = float(n.get("detailAmplitude", a1 * 0.32))
        d = (_value_noise(X * f1, Z * f1, seed) * 2.0 - 1.0) * a1
        if a2:
            d = d + (_value_noise(X * f2, Z * f2, (seed + 7717) & 0xFFFFFFFF)
                     * 2.0 - 1.0) * a2
        return d

    def channel_frame(self, x, z):
        """(weight, across, along) for the flowing channels only.

        `across` and `along` are metres in the river's OWN frame: distance from
        the centreline, and arc length measured down it from the path's first
        vertex. `weight` is 1 inside the channel and falls off across the bank,
        so a caller can say "this triangle is river, that one is lake".

        Exists so the Emberflow can be laid out with V running down the current
        wherever the reach bends. A river textured on world-planar UVs has its
        ripple lanes at whatever angle the world axes happen to be, and its
        flow can then only be scrolled in one global direction — which is why
        the river shipped as a uniform ribbon indistinguishable from the lake.
        Only the `path` shapes are channels; the Mere and the harbour are
        polygons and have no current.
        """
        X, Z = _arr(x), _arr(z)
        X, Z = np.broadcast_arrays(X, Z)
        shp = np.shape(X)
        w_best = np.zeros(shp, np.float64)
        across = np.zeros(shp, np.float64)
        along = np.zeros(shp, np.float64)
        for s in self.shapes:
            if "path" not in s:
                continue
            pts = [(float(p[0]), float(p[1])) for p in s["path"]]
            d, side, arc = _polyline_frame(X, Z, pts)
            hw, bank = float(s["halfWidth"]), float(s["bank"])
            w = 1.0 - _smoothstep(hw, hw + bank, d)
            take = w > w_best
            w_best = np.where(take, w, w_best)
            across = np.where(take, d * side, across)
            along = np.where(take, arc, along)
        return w_best, across, along

    def is_water(self, x, z):
        h = self.height(x, z)
        return h < self.water

    def water_level(self):
        return self.water

    # -- pads ---------------------------------------------------------------

    def pad(self, pad_id):
        p = self._pad_by_id.get(pad_id)
        if p is None:
            raise KeyError(f"no pad '{pad_id}' in content/town/terrain.json. "
                           f"Have: {', '.join(sorted(self._pad_by_id))}")
        return p

    def pad_level(self, pad_id):
        return self.pad(pad_id).level

    def terrace_of(self, x, z):
        """Which authored terrace a world point stands on, or None.

        Hearthmere falls ~4 m south to north in SHELVES, not as a ramp, and the
        shelves are authored once in `pads.list` as `hm.pad.terrace_*`. A shelf
        is the real unit a row of houses is built on and re-roofed with — one
        terrace is one act of construction — so anything that wants to group
        buildings the way the town was actually built should ask here rather
        than lay its own lattice over the map. `core/building.roof_covering`
        is the first caller; the roofscape read as a checkerboard precisely
        because its 26 m lattice cut across these.

        Later pads win, exactly as `height` resolves them, so the terraces are
        searched in reverse: `terrace_lower` is authored after the gate flats
        because it overrides them where they overlap.
        """
        for p in reversed(self.pads):
            if not p.id.startswith("hm.pad.terrace_"):
                continue
            lx, lz = p.local(x, z)
            if abs(lx) <= p.hx and abs(lz) <= p.hz:
                return p.id
        return None

    def flatten_region(self, pad_id, centre, half, level=None, apron=1.2,
                       rotation_deg=0.0, note=None):
        """Build a pad record. Pure — call `add_pad` to make it take effect.

        A venue that needs its own graded pad authors it here and persists it,
        because the CLIENT reads `content/town/terrain.json` too. A pad that
        exists only inside a generator would make the client's ground disagree
        with the generator's, which is the exact class of bug rule 3 forbids.

            pad = T.flatten_region("hm.pad.bakery", (12, 40), (8, 7))
            T.add_pad(pad); T.persist()
        """
        rec = {"id": pad_id, "centre": [float(centre[0]), float(centre[1])],
               "half": [float(half[0]), float(half[1])],
               "level": None if level is None else float(level),
               "apron": float(apron), "rotationDeg": float(rotation_deg)}
        if note:
            rec["note"] = note
        fb = None if level is not None else float(self.base_spine(centre[0], centre[1]))
        return Pad(rec, fb)

    def add_pad(self, pad):
        """Add or replace a pad in this in-memory terrain."""
        self.pads = [p for p in self.pads if p.id != pad.id] + [pad]
        self._pad_by_id = {p.id: p for p in self.pads}
        return pad

    def persist(self, path=TERRAIN_JSON):
        """Write the hand-authored pad list back to the authoritative JSON.

        `pads.generated` is left alone: it belongs to `tools/plan/ground.py`
        and is rewritten wholesale from the town plan every time that runs.
        """
        self.doc["pads"]["list"] = [p.as_dict() for p in self.pads
                                    if p.id not in self._generated_ids]
        with open(path, "w") as f:
            json.dump(self.doc, f, indent=2)
        return path

    # -- convenience for venue generators -----------------------------------

    def drape(self, mesh, offset=0.0):
        """Push a Mesh or Group onto the ground, keeping its local Y as a height.

        The ground height is ADDED to each vertex's existing Y, so a kerbstone
        authored at y = 0.145 stays 0.145 m proud of whatever the ground is
        doing under it.

        A Group is draped part by part. Draping the merged result would give
        the same vertices, but doing it per part keeps the material split
        intact — which is what `ctx.emit` batches on.

        Only sane for something that should follow the ground: a path ribbon, a
        plaza, a scatter of stones, street furniture. A BUILDING is placed with
        `pad_level()`, never draped — draping a building racks its floor.
        """
        if mesh is None:
            return mesh
        if isinstance(mesh, M.Group):
            for m in mesh.parts.values():
                self.drape(m, offset)
            return mesh
        if len(mesh.v) == 0:
            return mesh
        y = self.height(mesh.v[:, 0].astype(np.float64), mesh.v[:, 2].astype(np.float64))
        mesh.v = mesh.v.copy()
        mesh.v[:, 1] = (mesh.v[:, 1] + y + offset).astype(np.float32)
        return mesh

    def surface_weights(self, x, z, h=None, slope=None):
        """Ground-cover weights: grass, earth, gravel, mud, riverbed.

        Returned as a dict of arrays that sum to ~1. Used by the terrain mesh
        generator for per-triangle material choice and per-vertex tinting.
        """
        X, Z = _arr(x), _arr(z)
        if h is None:
            h = self.height(X, Z)
        if slope is None:
            slope = self.slope(X, Z)
        S = self.surfaces
        en = S["edgeNoise"]
        # Ragged boundaries, at two scales. A splat edge that follows a
        # contour exactly reads as a jigsaw, and one wobbled at a single
        # frequency reads as a sine wave; the mesh then dices it into
        # per-triangle teeth that are unmistakably aliasing. Two octaves, the
        # coarse one wide enough to move the boundary several metres, make the
        # same teeth read as an irregular shoreline instead.
        f1 = float(en["frequency"])
        f2 = float(en.get("detailFrequency", f1 * 3.0))
        wob = ((_value_noise(X * f1, Z * f1, int(en["seed"])) * 2.0 - 1.0)
               * float(en["amplitude"])
               + (_value_noise(X * f2, Z * f2, int(en["seed"]) + 811) * 2.0 - 1.0)
               * float(en.get("detailAmplitude", 0.0)))
        mud_cfg = S["waterlineMud"]
        # The waterline gets its own, much smaller wobble. The coarse `wob`
        # above is sized to move the town/meadow boundary by metres; running
        # the mud band off the same field moved the band by nearly a metre of
        # ELEVATION, which on a 2% terrace is hundreds of metres of plan.
        wn = float(mud_cfg.get("wobble", 0.22))
        hw = h - self.water + wob * (wn / max(float(en["amplitude"]), 1e-6))

        bed = 1.0 - _smoothstep(-float(mud_cfg["below"]), float(mud_cfg["below"]) + 0.12, hw)
        near = _smoothstep(0.04, 0.30, self.water_influence(X, Z))
        # Drop the silt band out in the distance rings. It is a decimetre-scale
        # feature resolved on a 2-4 m grid, so past ~130 m it stops being a
        # shoreline and becomes a row of dark triangular teeth around the far
        # side of the Mere. Turf running down to the water is both cheaper and
        # what a far shore actually looks like at that distance.
        far = float(mud_cfg.get("dropOff", 130.0))
        shore = near
        near = near * (1.0 - _smoothstep(far, far + 60.0, np.sqrt(X * X + Z * Z)))
        # What the band drops out INTO matters as much as dropping it. The
        # priority order is bed > mud > gravel > earth > grass, so switching
        # the mud off past the drop-off handed the far shore to `gravel` — and
        # `#8C8272` scree at the waterline, on the 2 m and 4 m LOD rings,
        # renders as a ring of pale scalloped teeth right round the Mere. It
        # is the first thing the eye finds in the departure frame, 140 m away
        # and reading as damage. The far shore has to fall through to turf,
        # which is both cheaper and what a far shore looks like, so the same
        # proximity term that selects the mud band also suppresses the scree.
        far_shore = np.maximum(shore - near, 0.0)
        mud = (_smoothstep(-float(mud_cfg["below"]), float(mud_cfg["below"]) + 0.10, hw)
               * (1.0 - _smoothstep(float(mud_cfg["above"]),
                                    float(mud_cfg["above"]) + float(mud_cfg["fade"]), hw))
               * near)

        slope = _arr(slope)
        g = S["gravelSlope"]
        gravel = _smoothstep(float(g["from"]), float(g["to"]), slope)

        # Trodden ground follows the wall line as a rounded rectangle, wobbled
        # by tens of metres of noise. A radius here draws a perfect disc of
        # earth in the middle of a meadow — the most artificial thing a splat
        # can do, and unmissable from the air.
        t = S["townEarth"]
        te = S["townEdgeNoise"]
        twob = (_value_noise(X * float(te["frequency"]), Z * float(te["frequency"]),
                             int(te["seed"])) * 2.0 - 1.0) * float(te["amplitude"])
        r = float(t["corner"])
        qx = np.abs(X) - (float(t["half"][0]) - r)
        qz = np.abs(Z) - (float(t["half"][1]) - r)
        mx = np.maximum(qx, 0.0)
        mz = np.maximum(qz, 0.0)
        sd_town = np.sqrt(mx * mx + mz * mz) + np.minimum(np.maximum(qx, qz), 0.0) - r
        town = 1.0 - _smoothstep(0.0, float(t["fade"]), sd_town + twob)

        # Green pockets inside the wall: yards, gardens, the churchyard.
        pf = float(t["patchFrequency"])
        patch = float(t["patchFloor"]) + (1.0 - float(t["patchFloor"])) * \
            _smoothstep(0.34, 0.66, _value_noise(X * pf, Z * pf, 8123457))
        # Anything steeper than a working surface inside the town is a grassed
        # bank, not a trodden yard. This is what makes the terrace scarps
        # legible from the air — a green line along every retaining wall.
        b0, b1 = float(t["bankSlope"][0]), float(t["bankSlope"][1])
        earth = town * patch * (1.0 - _smoothstep(b0, b1, slope))
        # A cart ramp is trodden ground by definition. Without this the green
        # pockets land wherever the patch noise puts them, and Ford Road — the
        # one route every cart in Hearthmere takes — came out as a lawn running
        # the length of the town.
        ramp_w = np.zeros(np.shape(X), np.float64)
        for r in self.ramps:
            _lvl, rw = r.eval(X, Z)
            ramp_w = np.maximum(ramp_w, rw)
        earth = np.maximum(earth, ramp_w * town)
        # Scree belongs on slopes nobody maintains, i.e. outside the wall —
        # and not on the far shore, where turf runs down to the water.
        # `shore`, not `far_shore`. The intent was already written down here —
        # "the same proximity term that selects the mud band also suppresses
        # the scree" — but `far_shore` is `shore` MINUS the near term, so the
        # suppression only ever applied past the drop-off, and the slope-driven
        # scree survived at every waterline inside it. Scree is what collects
        # on an unmaintained slope; it is not what collects at the edge of a
        # lake, at any distance. Near the town the `beach` band below puts
        # shingle back deliberately and at a controlled width; far from it the
        # shore falls through to turf. `far_shore` is kept as the reason the
        # drop-off exists at all.
        gravel = gravel * (1.0 - town * 0.92) * (1.0 - shore)

        # THE BEACH. Above the wet mud band and below the turf there is a strip
        # of shingle on every lake and every slow river in the world, and it is
        # the band that tells a player how deep the water is before they step
        # in. It was missing, and its absence is why the bank at the north gate
        # is a 1 m checkerboard of grass and silt in `t-gate-north`: the mud
        # band's upper edge ran straight into turf, so a per-triangle argmax
        # over two near-equal weights alternated between them all along it.
        #
        # It is NOT suppressed inside the town the way scree is. A town bank at
        # the waterline is shingle and mud; lawn running into a river inside a
        # walled town is the one thing it certainly is not.
        b0 = float(mud_cfg["above"]) * 0.55
        b1 = b0 + float(mud_cfg.get("beach", 0.85))
        beach = (_smoothstep(b0, b0 + 0.45, hw)
                 * (1.0 - _smoothstep(b1, b1 + float(mud_cfg["fade"]), hw))
                 * near)
        # `near` carries the drop-off, and the drop-off is the important half.
        # Shingle is a decimetre-scale material resolved on a 2 m or 4 m grid
        # past the town, so out there it stops being a beach and becomes the
        # "ring of pale scalloped teeth right round the Mere" this file's own
        # comment already records — the brightest thing in `t-aerial-sw` and a
        # continuous outline round the lake. Inside the drop-off the mesh is at
        # 0.5-1 m and it reads as shingle. Beyond it, turf runs down to the
        # water, which is both cheaper and what a far shore looks like.
        gravel = np.maximum(gravel, beach)

        # Priority: submerged beats waterline beats scree beats trodden.
        rem = 1.0
        w_bed = bed * rem
        rem = rem - w_bed
        w_mud = np.minimum(mud, 1.0) * rem
        rem = rem - w_mud
        w_gravel = gravel * rem
        rem = rem - w_gravel
        w_earth = earth * rem
        rem = rem - w_earth
        return {"riverbed": w_bed, "mud": w_mud, "gravel": w_gravel,
                "earth": w_earth, "grass": rem}


# ---------------------------------------------------------------------------
# Module-level default instance — the API other generators call
# ---------------------------------------------------------------------------

_INSTANCE = None


def load(path=TERRAIN_JSON):
    with open(path) as f:
        return Terrain(json.load(f))


def get():
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = load()
    return _INSTANCE


def height(x, z):
    return get().height(x, z)


def normal(x, z):
    return get().normal(x, z)


def slope(x, z):
    return get().slope(x, z)


def is_water(x, z):
    return get().is_water(x, z)


def water_level():
    return get().water_level()


def pad(pad_id):
    return get().pad(pad_id)


def pad_level(pad_id):
    return get().pad_level(pad_id)


def terrace_of(x, z):
    return get().terrace_of(x, z)


def flatten_region(*a, **k):
    return get().flatten_region(*a, **k)


def drape(mesh, offset=0.0):
    return get().drape(mesh, offset)
