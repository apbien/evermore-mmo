"""Mesh primitives with mandatory chamfering.

Art Bible §6: no razor-sharp edges. Sharp edges are the fastest way to read as
cheap 3D, because a real edge always catches a specular highlight. Every
primitive here takes a `chamfer` and builds true bevel faces — flat-shaded, so
they produce a crisp highlight line rather than a smeared smooth-normal blur.

Coordinate convention is glTF's: Y-up, right-handed, -Z forward, 1 unit = 1m.
Authoring in the target convention is what makes the Unreal/Unity port free.

Triangle winding is counter-clockwise when viewed from outside.
"""

from __future__ import annotations

import numpy as np

from .mathx import rng_for


class Mesh:
    """Triangle soup with per-vertex position/normal/uv and an optional colour.

    Deliberately flat-shaded by default: hard-surface props read better with
    faceted normals, and it keeps the chamfer highlights sharp.
    """

    __slots__ = ("v", "n", "uv", "idx", "col", "mat")

    def __init__(self, v=None, n=None, uv=None, idx=None, col=None, mat="default"):
        self.v = np.zeros((0, 3), np.float32) if v is None else np.asarray(v, np.float32)
        self.n = np.zeros((0, 3), np.float32) if n is None else np.asarray(n, np.float32)
        self.uv = np.zeros((0, 2), np.float32) if uv is None else np.asarray(uv, np.float32)
        self.idx = np.zeros((0,), np.uint32) if idx is None else np.asarray(idx, np.uint32)
        self.col = col if col is None else np.asarray(col, np.float32)
        self.mat = mat

    # -- basic properties ---------------------------------------------------

    @property
    def tri_count(self):
        return len(self.idx) // 3

    def copy(self):
        return Mesh(self.v.copy(), self.n.copy(), self.uv.copy(), self.idx.copy(),
                    None if self.col is None else self.col.copy(), self.mat)

    # -- transforms ---------------------------------------------------------

    def translate(self, x=0.0, y=0.0, z=0.0):
        self.v = self.v + np.array([x, y, z], np.float32)
        return self

    def scale(self, s, sy=None, sz=None):
        v = np.array([s, s, s], np.float32) if sy is None else np.array([s, sy, sz], np.float32)
        self.v = self.v * v
        # Normals need the inverse-transpose under non-uniform scale.
        inv = 1.0 / np.where(np.abs(v) < 1e-9, 1.0, v)
        self.n = self.n * inv
        ln = np.linalg.norm(self.n, axis=1, keepdims=True)
        self.n = self.n / np.where(ln < 1e-9, 1.0, ln)
        return self

    def rotate_y(self, radians):
        c, s = np.cos(radians), np.sin(radians)
        m = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], np.float32)
        self.v = self.v @ m.T
        self.n = self.n @ m.T
        return self

    def rotate_x(self, radians):
        c, s = np.cos(radians), np.sin(radians)
        m = np.array([[1, 0, 0], [0, c, -s], [0, s, c]], np.float32)
        self.v = self.v @ m.T
        self.n = self.n @ m.T
        return self

    def rotate_z(self, radians):
        c, s = np.cos(radians), np.sin(radians)
        m = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], np.float32)
        self.v = self.v @ m.T
        self.n = self.n @ m.T
        return self

    def with_material(self, mat):
        self.mat = mat
        return self

    # -- combination --------------------------------------------------------

    def merge(self, other):
        """Append another mesh. Materials are resolved at export by grouping."""
        off = len(self.v)
        self.v = np.vstack([self.v, other.v]) if len(self.v) else other.v.copy()
        self.n = np.vstack([self.n, other.n]) if len(self.n) else other.n.copy()
        self.uv = np.vstack([self.uv, other.uv]) if len(self.uv) else other.uv.copy()
        self.idx = np.concatenate([self.idx, other.idx + off]).astype(np.uint32)
        return self

    def bounds(self):
        if not len(self.v):
            return np.zeros(3), np.zeros(3)
        return self.v.min(axis=0), self.v.max(axis=0)


class Group:
    """A multi-material assembly: {material_key: Mesh}.

    Most real objects use more than one material — a timber-framed wall is
    plaster and oak, a door is timber and iron. Merging them into a single Mesh
    would throw the assignment away, so anything composite is built as a Group.

    Transforms apply to every part, and merging groups keeps parts batched per
    material, which is exactly the batching the renderer wants anyway
    (docs/ARCHITECTURE.md §5).
    """

    __slots__ = ("parts",)

    def __init__(self, parts=None):
        self.parts = {}
        if parts:
            for k, m in parts.items():
                self.parts[k] = m

    def add(self, mesh, mat=None):
        """Add a Mesh (or merge in another Group)."""
        if mesh is None:
            return self
        if isinstance(mesh, Group):
            for k, m in mesh.parts.items():
                self._slot(k).merge(m)
            return self
        key = mat or mesh.mat
        self._slot(key).merge(mesh)
        return self

    def _slot(self, key):
        if key not in self.parts:
            self.parts[key] = Mesh(mat=key)
        return self.parts[key]

    # Transforms fan out to every part so a Group behaves like a single object.
    def translate(self, x=0.0, y=0.0, z=0.0):
        for m in self.parts.values():
            m.translate(x, y, z)
        return self

    def rotate_y(self, r):
        for m in self.parts.values():
            m.rotate_y(r)
        return self

    def rotate_x(self, r):
        for m in self.parts.values():
            m.rotate_x(r)
        return self

    def rotate_z(self, r):
        for m in self.parts.values():
            m.rotate_z(r)
        return self

    def scale(self, s, sy=None, sz=None):
        for m in self.parts.values():
            m.scale(s, sy, sz)
        return self

    @property
    def tri_count(self):
        return sum(m.tri_count for m in self.parts.values())

    def bounds(self):
        los, his = [], []
        for m in self.parts.values():
            if m.tri_count:
                lo, hi = m.bounds()
                los.append(lo); his.append(hi)
        if not los:
            return np.zeros(3), np.zeros(3)
        return np.min(los, axis=0), np.max(his, axis=0)

    def items(self):
        return [(k, m) for k, m in self.parts.items() if m.tri_count]


# ---------------------------------------------------------------------------
# Builder helper
# ---------------------------------------------------------------------------

class _Builder:
    """Accumulates flat-shaded polygons and emits a Mesh."""

    def __init__(self):
        self.v, self.n, self.uv, self.idx = [], [], [], []

    def poly(self, pts, uvs=None, normal=None):
        """Add a convex polygon as a fan. Flat-shaded."""
        pts = [np.asarray(p, np.float32) for p in pts]
        if len(pts) < 3:
            return
        if normal is None:
            normal = np.cross(pts[1] - pts[0], pts[2] - pts[0])
            ln = np.linalg.norm(normal)
            if ln < 1e-12:
                return
            normal = normal / ln
        if uvs is None:
            uvs = _planar_uv(pts, normal)
        base = len(self.v)
        for p, t in zip(pts, uvs):
            self.v.append(p)
            self.n.append(normal)
            self.uv.append(t)
        for i in range(1, len(pts) - 1):
            self.idx += [base, base + i, base + i + 1]

    def build(self, mat="default"):
        if not self.v:
            return Mesh(mat=mat)
        return Mesh(np.array(self.v, np.float32), np.array(self.n, np.float32),
                    np.array(self.uv, np.float32), np.array(self.idx, np.uint32), mat=mat)


def _planar_uv(pts, normal, scale=1.0):
    """Project onto the plane most perpendicular to the normal.

    Keeps texel density uniform in world space, which is what the Art Bible §5
    density classes assume (they are specified in px/metre).
    """
    a = np.abs(normal)
    if a[1] >= a[0] and a[1] >= a[2]:
        return [(p[0] * scale, p[2] * scale) for p in pts]
    if a[0] >= a[2]:
        return [(p[2] * scale, p[1] * scale) for p in pts]
    return [(p[0] * scale, p[1] * scale) for p in pts]


# ---------------------------------------------------------------------------
# Chamfered box — the workhorse
# ---------------------------------------------------------------------------

def box(sx, sy, sz, chamfer=0.015, mat="default", uv_scale=1.0):
    """Axis-aligned box with a true chamfer on all 12 edges.

    Origin is at the centre. The chamfer is clamped so it can never invert a
    thin box (a 15mm architectural chamfer on a 20mm plank would otherwise
    produce degenerate geometry).
    """
    hx, hy, hz = sx * 0.5, sy * 0.5, sz * 0.5
    c = float(np.clip(chamfer, 0.0, 0.45 * min(sx, sy, sz)))
    b = _Builder()

    if c <= 1e-6:
        _plain_box(b, hx, hy, hz, uv_scale)
        return b.build(mat)

    ix, iy, iz = hx - c, hy - c, hz - c

    # 6 main faces, inset by the chamfer.
    for axis, sign in [(0, 1), (0, -1), (1, 1), (1, -1), (2, 1), (2, -1)]:
        nrm = np.zeros(3, np.float32)
        nrm[axis] = sign
        u_ax, v_ax = [(1, 2), (2, 0), (0, 1)][axis]
        ext = [hx, hy, hz]
        ins = [ix, iy, iz]
        corners = []
        for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            p = np.zeros(3, np.float32)
            p[axis] = sign * ext[axis]
            p[u_ax] = su * ins[u_ax]
            p[v_ax] = sv * ins[v_ax]
            corners.append(p)
        if sign < 0:
            corners.reverse()
        b.poly(corners, _planar_uv(corners, nrm, uv_scale), nrm)

    # 12 edge chamfer quads.
    ext = np.array([hx, hy, hz], np.float32)
    ins = np.array([ix, iy, iz], np.float32)
    for a0 in range(3):
        for a1 in range(a0 + 1, 3):
            a2 = 3 - a0 - a1  # the free axis the chamfer runs along
            for s0 in (-1, 1):
                for s1 in (-1, 1):
                    quad = []
                    for s2 in (-1, 1):
                        # Two verts per end: one on face a0, one on face a1.
                        p = np.zeros(3, np.float32)
                        p[a0] = s0 * ext[a0]; p[a1] = s1 * ins[a1]; p[a2] = s2 * ins[a2]
                        q = np.zeros(3, np.float32)
                        q[a0] = s0 * ins[a0]; q[a1] = s1 * ext[a1]; q[a2] = s2 * ins[a2]
                        quad.append((p, q))
                    pts = [quad[0][0], quad[0][1], quad[1][1], quad[1][0]]
                    nrm = np.zeros(3, np.float32)
                    nrm[a0] = s0; nrm[a1] = s1
                    nrm /= np.linalg.norm(nrm)
                    if np.dot(np.cross(pts[1] - pts[0], pts[2] - pts[0]), nrm) < 0:
                        pts.reverse()
                    b.poly(pts, _planar_uv(pts, nrm, uv_scale), nrm)

    # 8 corner triangles.
    for sx_ in (-1, 1):
        for sy_ in (-1, 1):
            for sz_ in (-1, 1):
                pts = [
                    np.array([sx_ * hx, sy_ * iy, sz_ * iz], np.float32),
                    np.array([sx_ * ix, sy_ * hy, sz_ * iz], np.float32),
                    np.array([sx_ * ix, sy_ * iy, sz_ * hz], np.float32),
                ]
                nrm = np.array([sx_, sy_, sz_], np.float32) / np.sqrt(3.0)
                if np.dot(np.cross(pts[1] - pts[0], pts[2] - pts[0]), nrm) < 0:
                    pts.reverse()
                b.poly(pts, _planar_uv(pts, nrm, uv_scale), nrm)

    return b.build(mat)


def _plain_box(b, hx, hy, hz, uv_scale):
    for axis, sign in [(0, 1), (0, -1), (1, 1), (1, -1), (2, 1), (2, -1)]:
        nrm = np.zeros(3, np.float32)
        nrm[axis] = sign
        u_ax, v_ax = [(1, 2), (2, 0), (0, 1)][axis]
        ext = [hx, hy, hz]
        corners = []
        for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            p = np.zeros(3, np.float32)
            p[axis] = sign * ext[axis]
            p[u_ax] = su * ext[u_ax]
            p[v_ax] = sv * ext[v_ax]
            corners.append(p)
        if sign < 0:
            corners.reverse()
        b.poly(corners, _planar_uv(corners, nrm, uv_scale), nrm)


# ---------------------------------------------------------------------------
# Revolved and swept forms
# ---------------------------------------------------------------------------

def lathe(profile, segments=24, mat="default", close_bottom=True, close_top=True,
          smooth=True, uv_scale=1.0):
    """Revolve a 2D profile around +Y.

    `profile` is [(radius, height), ...] bottom-to-top. This builds barrels,
    pottery, the fountain bowl, mugs, bottles — anything turned or thrown.

    Smooth normals around the circumference (correct for a turned object),
    flat across profile segments (so a shoulder stays crisp).
    """
    prof = [(float(r), float(h)) for r, h in profile]
    if len(prof) < 2:
        raise ValueError("lathe profile needs >= 2 points")
    seg = max(3, int(segments))
    b = _Builder()
    ang = np.linspace(0.0, 2.0 * np.pi, seg + 1)
    cs, sn = np.cos(ang), np.sin(ang)

    for i in range(len(prof) - 1):
        r0, y0 = prof[i]
        r1, y1 = prof[i + 1]
        for j in range(seg):
            p00 = np.array([r0 * cs[j], y0, r0 * sn[j]], np.float32)
            p10 = np.array([r0 * cs[j + 1], y0, r0 * sn[j + 1]], np.float32)
            p11 = np.array([r1 * cs[j + 1], y1, r1 * sn[j + 1]], np.float32)
            p01 = np.array([r1 * cs[j], y1, r1 * sn[j]], np.float32)
            pts = [p for p in (p00, p10, p11, p01)]
            # Degenerate ring (r == 0) collapses to a triangle.
            uvs = [(j / seg * uv_scale, y0 * uv_scale), ((j + 1) / seg * uv_scale, y0 * uv_scale),
                   ((j + 1) / seg * uv_scale, y1 * uv_scale), (j / seg * uv_scale, y1 * uv_scale)]
            if smooth:
                # Radial normals, tilted by the profile slope.
                dr, dy = r1 - r0, y1 - y0
                ln = np.hypot(dr, dy) or 1.0
                ny, nr = dr / ln, dy / ln
                nrms = [
                    np.array([nr * cs[j], ny, nr * sn[j]], np.float32),
                    np.array([nr * cs[j + 1], ny, nr * sn[j + 1]], np.float32),
                    np.array([nr * cs[j + 1], ny, nr * sn[j + 1]], np.float32),
                    np.array([nr * cs[j], ny, nr * sn[j]], np.float32),
                ]
                base = len(b.v)
                keep = [k for k in range(4)]
                for k in keep:
                    b.v.append(pts[k]); b.n.append(nrms[k]); b.uv.append(uvs[k])
                b.idx += [base, base + 1, base + 2, base, base + 2, base + 3]
            else:
                b.poly(pts, uvs)

    if close_bottom and prof[0][0] > 1e-6:
        r, y = prof[0]
        pts = [np.array([r * cs[j], y, r * sn[j]], np.float32) for j in range(seg)][::-1]
        b.poly(pts, None, np.array([0, -1, 0], np.float32))
    if close_top and prof[-1][0] > 1e-6:
        r, y = prof[-1]
        pts = [np.array([r * cs[j], y, r * sn[j]], np.float32) for j in range(seg)]
        b.poly(pts, None, np.array([0, 1, 0], np.float32))

    return b.build(mat)


def cylinder(radius, height, segments=16, chamfer=0.008, mat="default"):
    """Vertical cylinder with chamfered rims. Base at y=0."""
    c = float(np.clip(chamfer, 0.0, 0.3 * min(radius, height)))
    if c <= 1e-6:
        prof = [(radius, 0.0), (radius, height)]
    else:
        prof = [(radius - c, 0.0), (radius, c), (radius, height - c), (radius - c, height)]
    return lathe(prof, segments, mat)


def prism(profile2d, depth, mat="default", chamfer=0.0, uv_scale=1.0):
    """Extrude a 2D polygon (XY) along Z. Roof gables, brackets, signage."""
    pts = [np.asarray(p, np.float32) for p in profile2d]
    hd = depth * 0.5
    b = _Builder()
    front = [np.array([p[0], p[1], hd], np.float32) for p in pts]
    back = [np.array([p[0], p[1], -hd], np.float32) for p in pts]
    b.poly(front, None, np.array([0, 0, 1], np.float32))
    b.poly(back[::-1], None, np.array([0, 0, -1], np.float32))
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        quad = [front[i], front[j], back[j], back[i]]
        b.poly(quad, _planar_uv(quad, np.cross(quad[1] - quad[0], quad[2] - quad[0]), uv_scale))
    return b.build(mat)


def plank(length, width, thickness, chamfer=0.006, mat="wood", grain_axis=0):
    """A board with grain-aligned UVs.

    Art Bible §2: wood grain runs along the structural axis. Getting this wrong
    is subtle but reads as instantly fake, so UVs are laid out so that texture
    V follows the long axis.
    """
    m = box(length, thickness, width, chamfer, mat)
    if grain_axis == 0:
        m.uv = np.stack([m.v[:, 0] * 0.5, m.v[:, 2] * 2.0], axis=1).astype(np.float32)
    else:
        m.uv = np.stack([m.v[:, 2] * 0.5, m.v[:, 0] * 2.0], axis=1).astype(np.float32)
    return m


def quad(w, d, mat="default", uv_scale=1.0):
    """Horizontal ground quad centred at origin, facing +Y."""
    hw, hd = w * 0.5, d * 0.5
    b = _Builder()
    pts = [np.array([-hw, 0, hd], np.float32), np.array([hw, 0, hd], np.float32),
           np.array([hw, 0, -hd], np.float32), np.array([-hw, 0, -hd], np.float32)]
    uvs = [(0, 0), (w * uv_scale, 0), (w * uv_scale, d * uv_scale), (0, d * uv_scale)]
    b.poly(pts, uvs, np.array([0, 1, 0], np.float32))
    return b.build(mat)


# ---------------------------------------------------------------------------
# Composite helpers used across venues
# ---------------------------------------------------------------------------

def beam(length, section=0.18, mat="wood_dark", chamfer=0.015, axis="x"):
    """Structural timber. Chamfer is architectural-class per Art Bible §6."""
    if axis == "x":
        m = plank(length, section, section, chamfer, mat, grain_axis=0)
    elif axis == "y":
        m = box(section, length, section, chamfer, mat)
        m.uv = np.stack([m.v[:, 0] * 2.0, m.v[:, 1] * 0.5], axis=1).astype(np.float32)
    else:
        m = plank(section, length, section, chamfer, mat, grain_axis=1)
        m = box(section, section, length, chamfer, mat)
        m.uv = np.stack([m.v[:, 0] * 2.0, m.v[:, 2] * 0.5], axis=1).astype(np.float32)
    return m


def scatter_cobbles(width, depth, asset_id, stone=0.16, gap=0.012, mat="cobble"):
    """Cobbled paving as individually jittered, slightly domed stones.

    A tiled cobble texture on a flat plane reads as wallpaper at grazing
    angles. Real geometry gives per-stone silhouette and self-shadowing at the
    kerb, which is what sells a street.
    """
    rng = rng_for(asset_id, "cobbles")
    out = Mesh(mat=mat)
    nx = max(1, int(width / (stone + gap)))
    nz = max(1, int(depth / (stone + gap)))
    for i in range(nx):
        for j in range(nz):
            # Running bond: offset alternate rows so joints don't line up.
            off = (stone + gap) * 0.5 if j % 2 else 0.0
            x = -width * 0.5 + (i + 0.5) * (stone + gap) + off
            z = -depth * 0.5 + (j + 0.5) * (stone + gap)
            if x > width * 0.5:
                continue
            sx = stone * rng.uniform(0.82, 1.06)
            sz = stone * rng.uniform(0.82, 1.06)
            h = stone * rng.uniform(0.30, 0.44)
            s = box(sx, h, sz, chamfer=min(sx, sz) * 0.22, mat=mat)
            s.rotate_y(rng.uniform(-0.14, 0.14))
            s.translate(x + rng.uniform(-0.012, 0.012),
                        -h * 0.5 + rng.uniform(-0.006, 0.008),
                        z + rng.uniform(-0.012, 0.012))
            out.merge(s)
    return out
