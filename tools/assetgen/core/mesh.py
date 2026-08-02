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

import math

import numpy as np

from .mathx import rng_for

# ---------------------------------------------------------------------------
# UV scale resolution — the library is the authority, not the call site
# ---------------------------------------------------------------------------
#
# `_planar_uv` lays UVs in METRES. A builder therefore needs to know how many
# metres of world one tile of its material covers, and that number is authored
# once, in `materials.LIBRARY[key].coverage`, against the Art Bible §5
# texel-density table. Until D-046 every builder here defaulted to `1.0` and
# 350 call sites passed a literal instead — so the number that actually reached
# the mesh was whatever the venue author typed, and `MATS.uv_scale()` was
# consulted at 3 sites out of 421.
#
# Measured consequences, straight off the shipped glTF (dequantised):
#   landscape  leaf_oak     0.49 m/tile against 2.0 authored  (0.25x)
#   landscape  leaf_apple   0.50 m/tile against 2.0           (0.25x)
#   streets    sett         1.23 m/tile against 2.0           (0.62x)
#   streets    weeds        0.82 m/tile against 2.0           (0.41x)
#   church     alabaster    2.15 m/tile against 1.0           (2.15x)
# The first two are `ad-town-04` §4 exactly: a 2 m leaf ATLAS laid on a 0.49 m
# tile repeats its 4x4 sprig grid sixteen times across one canopy card, which
# is the "regular chequerboard grid of green squares" on the canonical return
# camera. It was never a bad leaf sheet. It was a bad number at the call site.
#
# So: `uv_scale=None` (the default everywhere now) means ASK THE LIBRARY, using
# the material key the builder already has. A bare float raises. An override
# must come from `materials.uv_detail(key, metres, why=...)`, which carries its
# reason with it.

#: Set HM_UV_STRICT=0 to downgrade the bare-literal error to a warning. It
#: exists for bisecting a regression, not for shipping.
_UV_WARNED = set()


def resolve_uv(uv_scale, mat):
    """UV units per metre for `mat`, honouring an explicit override.

    `None` -> the material library's authored coverage.
    `UVScale` -> as given (it came from `uv_scale()` or `uv_detail()`).
    a bare float -> BUILD ERROR. See the module note above.
    """
    from . import materials as _MAT
    if uv_scale is None:
        m = _MAT.LIBRARY.get(mat)
        # `default`, an atlas page name, or a key not in the library: one tile
        # per metre, which is what every builder did before D-046.
        cov = 1.0 if m is None else m.coverage
        return _MAT.UVScale(1.0 / cov, mat, "library coverage")
    if isinstance(uv_scale, _MAT.UVScale):
        # Already justified. Returned as-is so one builder can forward to
        # another (chamfered_prism -> prism) without tripping this check.
        return uv_scale
    import os
    msg = (f"bare uv_scale={uv_scale!r} on material {mat!r}. The authored "
           f"coverage lives in materials.LIBRARY and a mesh builder asks for "
           f"it by itself — pass nothing. If this surface genuinely needs a "
           f"local scale, say so and say why: "
           f"MATS.uv_detail({mat!r}, <metres per tile>, why='...').")
    if os.environ.get("HM_UV_STRICT", "1") == "0":
        if (mat, float(uv_scale)) not in _UV_WARNED:
            _UV_WARNED.add((mat, float(uv_scale)))
            print(f"  WARN uv: {msg}")
        return float(uv_scale)
    raise TypeError(msg)


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

    def spin_y(self, radians, about=None):
        """Rotate about a VERTICAL AXIS THROUGH THIS MESH, not the world origin.

        `rotate_y` is a world-space rotation, which is what you want while a
        part is still being built at the origin and exactly wrong once it has
        been placed: a piece already sitting at radius r is *translated* by
        about `r * radians`. `core/roof.py`'s rafter feet were jittered with
        `rotate_y(+/-0.02)` after `M.place`, so on a 5 m half-plate they slid up
        to 0.10 m out from under the deck and on a 12 m one — a granary, a
        tithe barn, a warehouse — some left the roof altogether and hung in
        clear air beside the building. That is the "detached timbers at the
        verge" defect, and it was never about verges.

        `about` defaults to the mesh's own bounding-box centre.
        """
        if not len(self.v):
            return self
        if about is None:
            lo, hi = self.v.min(axis=0), self.v.max(axis=0)
            about = (lo + hi) * 0.5
        cx, _cy, cz = (float(about[0]), float(about[1]), float(about[2]))
        self.translate(-cx, 0.0, -cz)
        self.rotate_y(radians)
        self.translate(cx, 0.0, cz)
        return self

    def mirror_x(self, about=0.0):
        """Reflect the mesh in the plane x = `about`. The safe way to hand a part.

        Mirroring a part is NOT `rotate_z(-angle)`. `rotate_z` mirrors the
        *angle* and leaves the *direction* the geometry extends alone, so a
        piece built from its own origin outward in +x rotates the wrong way
        round and leaves the object it trims. That is the confectioner's barge
        board, which climbed five metres past its own apex into open sky on the
        market place, and it is the same family as the `rotate_y`-about-the-
        world-origin defect `spin_y` exists to prevent.

        Nor is it `scale(-1, 1, 1)`. Negating one axis reverses triangle
        WINDING, so every face of the mirrored copy becomes a back face: the
        part turns inside out and, with backface culling on, disappears. This
        negates x on positions and normals AND flips the winding back, which is
        the whole reason it belongs in core rather than in a venue.
        """
        if not len(self.v):
            return self
        self.v = self.v.copy()
        self.v[:, 0] = 2.0 * float(about) - self.v[:, 0]
        if len(self.n):
            self.n = self.n.copy()
            self.n[:, 0] = -self.n[:, 0]
        if len(self.idx):
            t = self.idx.reshape(-1, 3)[:, ::-1]
            self.idx = np.ascontiguousarray(t).reshape(-1).astype(np.uint32)
        return self

    def with_material(self, mat):
        self.mat = mat
        return self

    # -- combination --------------------------------------------------------

    def merge(self, other):
        """Append another mesh. Materials are resolved at export by grouping."""
        off = len(self.v)
        # Vertex colours have to be reconciled BEFORE self.v is replaced, and
        # a mesh without them has to be padded with white rather than dropped:
        # merging a plain mesh into a coloured one otherwise leaves COLOR_0
        # shorter than POSITION, which glTF accepts and the renderer then reads
        # off the end of. White is the identity for the COLOR_0 multiply, so
        # padding is also semantically correct.
        if self.col is not None or other.col is not None:
            a = self.col if self.col is not None else np.ones((off, 4), np.float32)
            b = other.col if other.col is not None else np.ones((len(other.v), 4), np.float32)
            self.col = np.vstack([a, b]).astype(np.float32) if off else np.asarray(b, np.float32).copy()
        self.v = np.vstack([self.v, other.v]) if len(self.v) else other.v.copy()
        self.n = np.vstack([self.n, other.n]) if len(self.n) else other.n.copy()
        self.uv = np.vstack([self.uv, other.uv]) if len(self.uv) else other.uv.copy()
        self.idx = np.concatenate([self.idx, other.idx + off]).astype(np.uint32)
        return self

    def with_colour(self, col):
        """Attach per-vertex COLOR_0 (N,4) in linear space.

        glTF multiplies COLOR_0 into base colour, so it can only darken and
        tint — never brighten. Terrain uses it to blend one ground material
        toward its neighbour across a splat boundary and to carry large-scale
        colour variation that no tiling texture can.
        """
        c = np.asarray(col, np.float32)
        if c.ndim == 1:
            c = np.repeat(c[None, :], len(self.v), axis=0)
        if len(c) != len(self.v):
            raise ValueError(f"colour count {len(c)} != vertex count {len(self.v)}")
        if c.shape[1] == 3:
            c = np.concatenate([c, np.ones((len(c), 1), np.float32)], axis=1)
        self.col = c.astype(np.float32)
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

    def mirror_x(self, about=0.0):
        for m in self.parts.values():
            m.mirror_x(about)
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

def _project2(pts, normal):
    """Drop the polygon onto the axis plane it is most face-on to."""
    a = np.abs(normal)
    if a[1] >= a[0] and a[1] >= a[2]:
        return [(float(p[0]), float(p[2])) for p in pts]
    if a[0] >= a[2]:
        return [(float(p[2]), float(p[1])) for p in pts]
    return [(float(p[0]), float(p[1])) for p in pts]


def _fan_or_earclip(pts, normal):
    """Triangle index triples for a planar polygon, convex or not.

    Ear clipping (O(n^2), and n is never more than a few dozen here) rather
    than a library: the only concave polygons this town builds are arch
    spandrels and gable outlines with twenty vertices, and a dependency for
    that is not worth the port cost to Unreal.

    Winding is repaired per triangle against the polygon's own normal, which
    removes the whole question of which way the 2D projection turned. A face
    wound against its stored normal is back-face culled, and the way that
    shows up is a hole in a wall that nothing in the build log mentions.
    """
    n = len(pts)
    if n == 3:
        return [(0, 1, 2)]
    p2 = _project2(pts, normal)
    area2 = sum(p2[i][0] * p2[(i + 1) % n][1] - p2[(i + 1) % n][0] * p2[i][1]
                for i in range(n))
    sgn = 1.0 if area2 >= 0 else -1.0

    def cross(o, a, b):
        return sgn * ((a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]))

    if all(cross(p2[i], p2[(i + 1) % n], p2[(i + 2) % n]) >= -1e-9 for i in range(n)):
        tris = [(0, i, i + 1) for i in range(1, n - 1)]
    else:
        idx = list(range(n))
        tris = []
        guard = 0
        while len(idx) > 3 and guard < 4 * n * n:
            guard += 1
            for k in range(len(idx)):
                i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
                a, b, c = p2[i0], p2[i1], p2[i2]
                if cross(a, b, c) <= 1e-12:
                    continue                      # reflex, not an ear
                bad = False
                for m in idx:
                    if m in (i0, i1, i2):
                        continue
                    q = p2[m]
                    if (cross(a, b, q) >= 0 and cross(b, c, q) >= 0
                            and cross(c, a, q) >= 0):
                        bad = True
                        break
                if bad:
                    continue
                tris.append((i0, i1, i2))
                idx.pop(k)
                break
            else:
                break                              # degenerate: bail to a fan
        if len(idx) == 3:
            tris.append(tuple(idx))
        elif len(idx) > 3:
            tris += [(idx[0], idx[i], idx[i + 1]) for i in range(1, len(idx) - 1)]

    out = []
    for (i, j, k) in tris:
        gn = np.cross(pts[j] - pts[i], pts[k] - pts[i])
        out.append((i, j, k) if float(np.dot(gn, normal)) >= 0 else (i, k, j))
    return out


class _Builder:
    """Accumulates flat-shaded polygons and emits a Mesh."""

    def __init__(self):
        self.v, self.n, self.uv, self.idx, self.col = [], [], [], [], []
        self._coloured = False

    def poly(self, pts, uvs=None, normal=None, colour=None):
        """Add a planar polygon, flat-shaded. Convex fans; concave ear-clips.

        `colour` is an optional per-polygon COLOR_0 (RGB or RGBA, linear). It
        exists so a builder can carry unit-to-unit variance in geometry rather
        than only in a tiling texture — the roof courses use it, because a
        texture repeats every 4 m and a roof does not.

        The fan is the fast path, because almost every polygon in this town is
        a box face. The ear-clip exists because an ARCH is not: the wall around
        a gate opening is a rectangle with a bite taken out of its bottom edge,
        and a fan over that fills the bite back in. Every arch in Hearthmere —
        four gates, three posterns, three bridge spans — rendered as solid
        masonry until this was here, with the voussoir ring and the hood mould
        drawn neatly over the top of a blocked hole.
        """
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
        if colour is None:
            c = (1.0, 1.0, 1.0, 1.0)
        else:
            c = tuple(float(x) for x in colour)
            if len(c) == 3:
                c = c + (1.0,)
            self._coloured = True
        base = len(self.v)
        for p, t in zip(pts, uvs):
            self.v.append(p)
            self.n.append(normal)
            self.uv.append(t)
            self.col.append(c)
        for (i, j, k) in _fan_or_earclip(pts, normal):
            self.idx += [base + i, base + j, base + k]

    def build(self, mat="default"):
        if not self.v:
            return Mesh(mat=mat)
        m = Mesh(np.array(self.v, np.float32), np.array(self.n, np.float32),
                 np.array(self.uv, np.float32), np.array(self.idx, np.uint32), mat=mat)
        if self._coloured:
            # `lathe` appends to v/n/uv directly for its smooth ring, so the
            # colour list can trail the vertex list. White is COLOR_0's
            # identity, so padding is also semantically correct.
            if len(self.col) < len(self.v):
                self.col = list(self.col) + [(1.0, 1.0, 1.0, 1.0)] * (len(self.v) - len(self.col))
            m.col = np.array(self.col[:len(self.v)], np.float32)
        return m


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

def box(sx, sy, sz, chamfer=0.015, mat="default", uv_scale=None):
    """Axis-aligned box with a true chamfer on all 12 edges.

    Origin is at the centre. The chamfer is clamped so it can never invert a
    thin box (a 15mm architectural chamfer on a 20mm plank would otherwise
    produce degenerate geometry).
    """
    uv_scale = resolve_uv(uv_scale, mat)
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
          smooth=True, uv_scale=None):
    """Revolve a 2D profile around +Y.

    `profile` is [(radius, height), ...] bottom-to-top. This builds barrels,
    pottery, the fountain bowl, mugs, bottles — anything turned or thrown.

    Smooth normals around the circumference (correct for a turned object),
    flat across profile segments (so a shoulder stays crisp).

    ## Orientation, which this got wrong in two independent ways

    Vertices run round the ring in increasing theta with X = cos and Z = sin.
    Emitting the side quad in the order (theta_j, y0) -> (theta_j+1, y0) ->
    (theta_j+1, y1) -> (theta_j, y1) winds it CLOCKWISE seen from OUTSIDE, so
    glTF's CCW front-face rule made the outside of every lathed object in
    Hearthmere a back face. Measured on `lathe([(0.4,0),(0.5,0.3),(0.5,0.7),
    (0.4,1.0)])`: 100% of triangles wound opposite their own vertex normals.
    Every barrel, mug, bowl, chimney pot, turned post and the market fountain
    was inside-out, and the caps had the same fault with the opposite sign.

    The normal was separately wrong. For a profile step (dr, dy) the outward
    normal in the (r, y) half-plane is (dy, -dr) — this had `ny = +dr/len`, so
    the Y component was inverted on every non-vertical segment. A horizontal
    tread came out facing DOWN. That is what made the market fountain's outer
    step rings render near-black from any raised angle: the treads were both
    culled and, where drawn, lit as if they were soffits. It is not AO and not
    shadow acne — `tools/render` was reporting the geometry honestly.

    A vertical wall is the one case where both faults are invisible in the
    normal (dr = 0, so the sign of dr does not matter) which is why cylinders
    looked merely odd rather than obviously broken, and why this survived.
    D-039.
    """
    uv_scale = resolve_uv(uv_scale, mat)
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
            # Wound (theta_j, y0) -> (theta_j, y1) -> (theta_j+1, y1) ->
            # (theta_j+1, y0): counter-clockwise seen from outside, which is
            # glTF's front face. See the docstring — the other order is what
            # every lathed object in the town shipped with.
            pts = [p for p in (p00, p01, p11, p10)]
            # Degenerate ring (r == 0) collapses to a triangle.
            # U is ARC LENGTH IN METRES, not normalised angle.
            #
            # Angular UVs stretch exactly one texture tile around the whole
            # circumference regardless of size, so a 1m-radius turret sampled a
            # single tile across 6.6m while the flat wall beside it — whose UVs
            # are planar and in metres — tiled three times. Same material, wildly
            # different texel density: measured saturation 0.097 on the turret
            # against 0.253 on the wall. Two venues, two lathes, one root cause.
            a0 = (j / seg) * 2.0 * np.pi
            a1 = ((j + 1) / seg) * 2.0 * np.pi
            u0, u1 = a0 * max(r0, r1), a1 * max(r0, r1)
            uvs = [(u0 * uv_scale, y0 * uv_scale), (u0 * uv_scale, y1 * uv_scale),
                   (u1 * uv_scale, y1 * uv_scale), (u1 * uv_scale, y0 * uv_scale)]
            if smooth:
                # Radial normals, tilted by the profile slope. The outward
                # normal to a profile step (dr, dy) is (dy, -dr) in the (r, y)
                # half-plane; `ny = +dr/len` faced every tread and shoulder the
                # wrong way in Y.
                dr, dy = r1 - r0, y1 - y0
                ln = np.hypot(dr, dy) or 1.0
                ny, nr = -dr / ln, dy / ln
                nrms = [
                    np.array([nr * cs[j], ny, nr * sn[j]], np.float32),
                    np.array([nr * cs[j], ny, nr * sn[j]], np.float32),
                    np.array([nr * cs[j + 1], ny, nr * sn[j + 1]], np.float32),
                    np.array([nr * cs[j + 1], ny, nr * sn[j + 1]], np.float32),
                ]
                base = len(b.v)
                keep = [k for k in range(4)]
                for k in keep:
                    b.v.append(pts[k]); b.n.append(nrms[k]); b.uv.append(uvs[k])
                b.idx += [base, base + 1, base + 2, base, base + 2, base + 3]
            else:
                b.poly(pts, uvs)

    # Caps. Increasing theta with X = cos, Z = sin traces a ring that is
    # clockwise seen from +Y, so the DOWNWARD cap takes the forward order and
    # the UPWARD cap takes the reversed one. Both were the wrong way round.
    if close_bottom and prof[0][0] > 1e-6:
        r, y = prof[0]
        pts = [np.array([r * cs[j], y, r * sn[j]], np.float32) for j in range(seg)]
        b.poly(pts, None, np.array([0, -1, 0], np.float32))
    if close_top and prof[-1][0] > 1e-6:
        r, y = prof[-1]
        pts = [np.array([r * cs[j], y, r * sn[j]], np.float32) for j in range(seg)][::-1]
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


def prism(profile2d, depth, mat="default", chamfer=0.0, uv_scale=None):
    """Extrude a 2D polygon (XY) along Z. Roof gables, brackets, signage."""
    uv_scale = resolve_uv(uv_scale, mat)
    pts = [np.asarray(p, np.float32) for p in profile2d]
    hd = depth * 0.5
    b = _Builder()
    front = [np.array([p[0], p[1], hd], np.float32) for p in pts]
    back = [np.array([p[0], p[1], -hd], np.float32) for p in pts]
    # The end caps took `uv_scale` too. They were the one pair of faces in this
    # function that did not, so a prism authored at a material's real coverage
    # still printed its ends at 1 m per tile — visible on every gable end, every
    # bracket cheek and both ends of a thatch shell.
    fn = np.array([0, 0, 1], np.float32)
    b.poly(front, _planar_uv(front, fn, uv_scale), fn)
    b.poly(back[::-1], _planar_uv(back[::-1], -fn, uv_scale), -fn)
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        quad = [front[i], front[j], back[j], back[i]]
        b.poly(quad, _planar_uv(quad, np.cross(quad[1] - quad[0], quad[2] - quad[0]), uv_scale))
    return b.build(mat)


def sweep(profiles, path, mat="default", uv_scale=None, cap_start=True,
          cap_end=True):
    """Loft a convex 2D cross-section along a plan polyline. The wall primitive.

    `path` is [(x, y, z), ...]: the plan line, carrying the BASE height of each
    station in its Y. `profiles` is either one closed ring `[(u, v), ...]` used
    at every station, or one ring per station — same vertex count, same order.
    `u` is metres to the RIGHT of the direction of travel in plan view (x right,
    z down, i.e. along `(-dz, 0, dx)`); `v` is metres above that station's own Y.

    Per-station profiles are the whole reason this exists. A town wall on
    sloping ground has a base that follows the contour and a crown that steps
    down a course at a time, and the two are independent — which no primitive
    that takes one section and one extrusion length can express. Sweeping a
    ring that changes shape station to station also covers a parapet that dies
    away at a stair, a wall that thickens into a gate pier, and a coping that
    widens over a tower.

    Rings must be CONVEX: the caps are fans. Compose an L-shaped or T-shaped
    section from two sweeps, which is also what you want for materials — a
    rubble body does not carry the same texture as its ashlar coping.

    Lateral vectors are mitred at interior stations and scaled by 1/cos of the
    half-angle, so a section keeps its true thickness round a bend instead of
    pinching. The scale is clamped, because an unclamped mitre at a hairpin is
    an inside-out panel a hundred metres long.
    """
    P = np.asarray(path, np.float64)
    if P.ndim != 2 or P.shape[1] != 3 or len(P) < 2:
        raise ValueError("sweep: path needs >= 2 (x, y, z) stations")
    n_st = len(P)
    rings = [profiles] * n_st if profiles and not isinstance(profiles[0][0], (list, tuple, np.ndarray)) \
        else list(profiles)
    if len(rings) != n_st:
        raise ValueError(f"sweep: {len(rings)} profiles for {n_st} stations")
    ring0 = [(float(u), float(v)) for u, v in rings[0]]
    k = len(ring0)
    if k < 3:
        raise ValueError("sweep: a profile ring needs >= 3 points")

    # Normalise winding to counter-clockwise in (u, v) so the outward normal of
    # every edge is (dv, -du) and the quad winding below has a reference to
    # agree with. A caller who hands over a clockwise ring gets the same solid,
    # not an inside-out one.
    uv_scale = resolve_uv(uv_scale, mat)
    area = sum(ring0[i][0] * ring0[(i + 1) % k][1] - ring0[(i + 1) % k][0] * ring0[i][1]
               for i in range(k))
    flip = area < 0.0
    rings = [[(float(u), float(v)) for u, v in r] for r in rings]
    if flip:
        rings = [r[::-1] for r in rings]

    # Segment directions and their plan normals.
    seg_f, seg_n, seg_len = [], [], []
    for i in range(n_st - 1):
        dx, dz = P[i + 1, 0] - P[i, 0], P[i + 1, 2] - P[i, 2]
        ln = math.hypot(dx, dz)
        if ln < 1e-9:
            raise ValueError(f"sweep: duplicate station at index {i}")
        seg_f.append((dx / ln, dz / ln))
        seg_n.append((-dz / ln, dx / ln))
        seg_len.append(ln)

    lat, fwd = [], []
    for i in range(n_st):
        a = seg_n[max(0, i - 1)]
        b = seg_n[min(i, n_st - 2)]
        mx, mz = a[0] + b[0], a[1] + b[1]
        ml = math.hypot(mx, mz)
        if ml < 1e-6:
            mx, mz, ml = b[0], b[1], 1.0
        mx, mz = mx / ml, mz / ml
        # 1/cos(half-angle), clamped: a 60-degree kink already doubles the
        # section and past that the mitre is a lie worth refusing.
        c = max(0.5, mx * b[0] + mz * b[1])
        lat.append((mx / c, mz / c))
        fwd.append(seg_f[min(i, n_st - 2)])

    # Running distance for U, ring perimeter for V. V follows the section's own
    # perimeter, so on a vertical face it IS height above the base and coursed
    # masonry stays level; over the top it wraps continuously.
    run = [0.0]
    for ln in seg_len:
        run.append(run[-1] + ln)

    b = _Builder()
    P3 = []
    for i in range(n_st):
        lx, lz = lat[i]
        base = P[i]
        P3.append([np.array([base[0] + lx * u, base[1] + v, base[2] + lz * u], np.float32)
                   for u, v in rings[i]])

    for i in range(n_st - 1):
        r0, r1 = rings[i], rings[i + 1]
        per = 0.0
        for e in range(k):
            e2 = (e + 1) % k
            du, dv = r0[e2][0] - r0[e][0], r0[e2][1] - r0[e][1]
            elen = math.hypot(du, dv)
            if elen < 1e-9:
                continue
            ox, oy = dv / elen, -du / elen          # outward normal in (u, v)
            lx, lz = lat[i]
            nrm = np.array([ox * lx, oy, ox * lz], np.float32)
            nl = float(np.linalg.norm(nrm))
            nrm = nrm / (nl or 1.0)
            quad = [P3[i][e], P3[i][e2], P3[i + 1][e2], P3[i + 1][e]]
            uvs = [(run[i] * uv_scale, per * uv_scale),
                   (run[i] * uv_scale, (per + elen) * uv_scale),
                   (run[i + 1] * uv_scale, (per + elen) * uv_scale),
                   (run[i + 1] * uv_scale, per * uv_scale)]
            if np.dot(np.cross(quad[1] - quad[0], quad[2] - quad[0]), nrm) < 0:
                quad = quad[::-1]
                uvs = uvs[::-1]
            b.poly(quad, uvs, nrm)
            per += elen

    for do_cap, i, sign in ((cap_start, 0, -1.0), (cap_end, n_st - 1, 1.0)):
        if not do_cap:
            continue
        fx, fz = fwd[i]
        nrm = np.array([fx * sign, 0.0, fz * sign], np.float32)
        pts = list(P3[i])
        # Winding is DERIVED, not assumed. A cap wound against its own stored
        # normal is back-face culled and the wall reads as hollow at every step
        # in its crown — which is every few metres on sloping ground.
        if np.dot(np.cross(pts[1] - pts[0], pts[2] - pts[0]), nrm) < 0:
            pts = pts[::-1]
        b.poly(pts, [(p[0] * uv_scale, p[1] * uv_scale) for p in pts], nrm)

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


def place(geom, origin=(0.0, 0.0, 0.0), ex=(1, 0, 0), ey=(0, 1, 0), ez=(0, 0, 1)):
    """Map a mesh's local axes onto an arbitrary orthonormal basis, then move it.

    `rotate_x/y/z` cannot express "lie in the plane of that roof slope" without
    composing three angles and getting the order right, which is exactly the
    kind of arithmetic that puts a barge board 90° out. A basis is the direct
    statement: local +X becomes `ex`, +Y becomes `ey`, +Z becomes `ez`.

    Pass a right-handed basis. A left-handed one mirrors the mesh and inverts
    its winding, which renders as an object turned inside out.
    """
    B = np.array([np.asarray(ex, np.float32), np.asarray(ey, np.float32),
                  np.asarray(ez, np.float32)], np.float32).T
    meshes = geom.parts.values() if isinstance(geom, Group) else [geom]
    o = np.asarray(origin, np.float32)
    for m in meshes:
        if len(m.v):
            m.v = (m.v @ B.T) + o
        if len(m.n):
            n = m.n @ B.T
            ln = np.linalg.norm(n, axis=1, keepdims=True)
            m.n = (n / np.where(ln < 1e-9, 1.0, ln)).astype(np.float32)
    return geom


def quad(w, d, mat="default", uv_scale=None):
    """Horizontal ground quad centred at origin, facing +Y."""
    uv_scale = resolve_uv(uv_scale, mat)
    hw, hd = w * 0.5, d * 0.5
    b = _Builder()
    pts = [np.array([-hw, 0, hd], np.float32), np.array([hw, 0, hd], np.float32),
           np.array([hw, 0, -hd], np.float32), np.array([-hw, 0, -hd], np.float32)]
    uvs = [(0, 0), (w * uv_scale, 0), (w * uv_scale, d * uv_scale), (0, d * uv_scale)]
    b.poly(pts, uvs, np.array([0, 1, 0], np.float32))
    return b.build(mat)


# ---------------------------------------------------------------------------
# Soft, swept and hung forms
# ---------------------------------------------------------------------------
# Everything a prop library needs that a box and a lathe cannot express: a
# member between two arbitrary points, a line that hangs, a band, a blob, a
# cloth. These lived as private helpers inside `venues/stalls.py`, which
# annotated them "venue-local; core/ is owned by other agents this pass" — and
# that is exactly the fork Directive §6.7 exists to prevent. A second copy of
# the catenary is how a town ends up with two different ideas of how rope hangs.

def tube(p0, p1, radius, mat="oak", segments=6, chamfer=0.0015):
    """A cylinder spanning two arbitrary points.

    The workhorse for anything linear that is not axis-aligned: rope, chain
    links, spits, skewers, spokes, tool handles, stretcher rails, cart shafts.
    Returns None for a degenerate span so it composes inside a loop.
    """
    a = np.asarray(p0, np.float64)
    b = np.asarray(p1, np.float64)
    d = b - a
    L = float(np.linalg.norm(d))
    if L < 1e-6:
        return None
    c = cylinder(radius, L, segments, min(chamfer, radius * 0.4), mat)
    dn = d / L
    ang = float(np.arccos(np.clip(dn[1], -1.0, 1.0)))
    if abs(np.sin(ang)) > 1e-6:
        c.rotate_x(ang)
        c.rotate_y(float(np.arctan2(dn[0], dn[2])))
    elif dn[1] < 0:
        c.rotate_x(np.pi)
    c.translate(*a)
    return c


def catenary(p0, p1, sag, mat="canvas", radius=0.008, segments=8, faces=4):
    """A hanging line as a chain of short tubes following a real droop.

    A straight cylinder between two points reads as a steel rod. The droop is
    the entire difference between rope and rod, and it is also what makes a
    laundry line, an awning guy or a string of drying herbs read as carrying
    weight. `sag` is the depth at midspan in metres.

    Parabolic rather than a true hyperbolic cosine: over the spans this town
    uses (< 8 m) the two differ by under a millimetre, and the parabola cannot
    produce a NaN when the horizontal tension is unknown.
    """
    out = Group()
    a = np.asarray(p0, np.float64)
    b = np.asarray(p1, np.float64)
    prev = None
    for i in range(int(segments) + 1):
        t = i / segments
        p = a + (b - a) * t + np.array([0.0, -sag * 4.0 * t * (1.0 - t), 0.0])
        if prev is not None:
            out.add(tube(prev, p, radius, mat, faces))
        prev = p
    return out


def ring(radius, section, mat="iron", segments=12, tilt=0.0):
    """A flattened torus band: barrel hoop, cask chime, bangle, pot rim, tyre."""
    m = lathe([(radius - section * 0.5, -section * 0.35),
               (radius + section * 0.4, 0.0),
               (radius - section * 0.5, section * 0.35)], segments, mat,
              close_bottom=False, close_top=False)
    if tilt:
        m.rotate_x(tilt)
    return m


def globe(radius, mat="default", segments=8, rings=4, sx=1.0, sy=1.0, sz=1.0):
    """Low-poly sphere, centred on the origin. Fruit, loaves, floats, heads.

    Deliberately coarse: at the gameplay camera a 6 cm apple is nine pixels
    across, and the faceting reads as the hand-made variance Art Bible §6 asks
    for rather than as a low-poly artefact.
    """
    prof = [(radius * np.sin(np.pi * i / rings), radius - radius * np.cos(np.pi * i / rings))
            for i in range(rings + 1)]
    m = lathe(prof, segments, mat, close_bottom=False, close_top=False)
    m.translate(0, -radius, 0)
    if (sx, sy, sz) != (1.0, 1.0, 1.0):
        m.scale(sx, sy, sz)
    return m


def sheet(width, depth, hf, uv_fn=None, nx=10, nz=6, mat="linen", plane="xz"):
    """A smooth-shaded cloth surface over an analytic height field.

    `hf(u, v)` with u across the width (+X) and v from the back edge (+Z,
    v=0) to the front (-Z, v=1). Normals are taken from the field, not from
    the faces: cloth is the one thing in this town that must NOT be faceted,
    or it reads as folded cardboard.

    `plane` decides which way the cloth lies, and getting it wrong is not
    subtle — it was shipped wrong once and every hanging cloth in the town
    came out as a 45° ramp:

      `xz` — the cloth LIES DOWN. u,v span the ground plane and `hf` is
             height. Awnings, a hide over a beam, a cloth on a counter.
      `xy` — the cloth HANGS. u spans the width, v runs DOWNWARD from the
             top edge at `+depth/2`, and `hf` is the belly toward -Z.
             Laundry, a cloak over a chair back, a bolt's loose tail.

    Authoring `hf` as a downward drop and leaving `plane="xz"` produces a
    surface that falls in Y *and* in Z at once — a ramp, which is exactly what
    a hanging cloth must never be.
    """
    if uv_fn is None:
        uv_fn = lambda x, z: (x, z)          # noqa: E731 — metres, per §5
    vs, ns, uvs, idx = [], [], [], []
    e = 1e-3
    for j in range(nz + 1):
        for i in range(nx + 1):
            u, v = i / nx, j / nz
            x = -width * 0.5 + u * width
            z = depth * 0.5 - v * depth
            u0, u1 = max(0.0, u - e), min(1.0, u + e)
            v0, v1 = max(0.0, v - e), min(1.0, v + e)
            dydx = (hf(u1, v) - hf(u0, v)) / ((u1 - u0) * width)
            dydz = -(hf(u, v1) - hf(u, v0)) / ((v1 - v0) * depth)
            n = np.array([-dydx, 1.0, -dydz], np.float64)
            n /= np.linalg.norm(n)
            vs.append((x, hf(u, v), z))
            ns.append(n)
            uvs.append(uv_fn(x, z))
    for j in range(nz):
        for i in range(nx):
            a = j * (nx + 1) + i
            idx += [a, a + nx + 2, a + 1, a, a + nx + 1, a + nx + 2]
    m = Mesh(np.array(vs, np.float32), np.array(ns, np.float32),
             np.array(uvs, np.float32), np.array(idx, np.uint32), mat=mat)
    if plane == "xy":
        # Stand it up: local +Z becomes +Y (so v runs downward from the top
        # edge) and the height field becomes the belly toward -Z.
        m.rotate_x(-np.pi * 0.5)
    return m


def retex(m, su=1.0, sv=None, ou=0.0, ov=0.0):
    """Rescale and offset a mesh's UVs in place.

    Two jobs. Texel density — a 6 cm apple and a 2 m counter cannot share a UV
    scale or one of them samples a single texel. And variance: every library
    material carries internal variation (per-tile firing colour in terracotta,
    per-board grain in oak), so offsetting each instance into a different
    region of the same texture is how twelve pots come out twelve shades of
    fired clay without adding a material or leaving the locked palette.
    """
    sv = su if sv is None else sv
    if len(m.uv):
        m.uv = (m.uv * np.array([su, sv], np.float32)
                + np.array([ou, ov], np.float32)).astype(np.float32)
    return m


def chamfered_prism(profile2d, depth, mat="default", chamfer=0.006, uv_scale=None):
    """Extruded 2D polygon with a REAL chamfer on every edge.

    `prism()` accepts a `chamfer` argument and ignores it, so every cut-out
    profile in the town — brackets, gable trim, felloes, tool blades — carries
    the razor CAD edge that Art Bible §6 says review rejects first. This does
    the real thing: the profile corners are mitred in-plane and both end caps
    are inset, so the perimeter gets a bevel band that catches the sun.

    Convex profiles only. The end-cap inset is toward the centroid, which for a
    concave polygon crosses its own boundary; pass such a profile to `prism()`
    and accept the sharp edge, or decompose it.
    """
    uv_scale = resolve_uv(uv_scale, mat)
    pts = [np.asarray(p, np.float64) for p in profile2d]
    n = len(pts)
    c = float(chamfer)
    if c <= 1e-6 or n < 3:
        return prism(profile2d, depth, mat, uv_scale=uv_scale)

    # 1. Mitre the in-plane corners: each corner becomes two points, pulled
    #    back along the two edges that meet there.
    cut = []
    for i in range(n):
        p, a, b = pts[i], pts[i - 1], pts[(i + 1) % n]
        din, dout = p - a, b - p
        lin, lout = np.linalg.norm(din), np.linalg.norm(dout)
        if lin < 1e-9 or lout < 1e-9:
            cut.append(p)
            continue
        k = min(c, lin * 0.4, lout * 0.4)
        cut.append(p - din / lin * k)
        cut.append(p + dout / lout * k)
    cut = np.array(cut)

    # 2. An inset copy for the end caps, so the cap meets the side wall through
    #    a bevel instead of a corner.
    cen = cut.mean(axis=0)
    off = cut - cen
    ln = np.linalg.norm(off, axis=1, keepdims=True)
    ins = cut - off / np.maximum(ln, 1e-9) * np.minimum(c, ln * 0.4)

    hd = depth * 0.5
    b = _Builder()
    f_out = [np.array([p[0], p[1], hd - c], np.float32) for p in cut]
    b_out = [np.array([p[0], p[1], -hd + c], np.float32) for p in cut]
    f_in = [np.array([p[0], p[1], hd], np.float32) for p in ins]
    b_in = [np.array([p[0], p[1], -hd], np.float32) for p in ins]

    b.poly(f_in, None, np.array([0, 0, 1], np.float32))
    b.poly(b_in[::-1], None, np.array([0, 0, -1], np.float32))
    m = len(cut)
    for i in range(m):
        j = (i + 1) % m
        for q in ([f_out[i], f_out[j], b_out[j], b_out[i]],      # side wall
                  [f_in[i], f_in[j], f_out[j], f_out[i]],        # front bevel
                  [b_out[i], b_out[j], b_in[j], b_in[i]]):       # back bevel
            nrm = np.cross(q[1] - q[0], q[2] - q[0])
            lnn = np.linalg.norm(nrm)
            if lnn < 1e-12:
                continue
            b.poly(q, _planar_uv(q, nrm / lnn, uv_scale))
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
