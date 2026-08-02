"""Texture atlasing for the kit's small props and the building kit's trim.

Directive §7 lists "texture atlasing across the kit" as a required technique and
gives two budgets it exists to defend: **< 900 draw calls** and **< 1.5 GB of
texture memory**. Both are lost the same way. A back lane in Hearthmere holds a
barrel, a crate, a sack, a rope coil, a bucket, a boot scraper, a hitching post
and a lantern bracket; those are eight materials, so even after `core/batch.py`
has merged everything in the cell they are eight primitives and eight texture
sets. On the shipped `streets` venue that pattern cost 1,344 draw calls on its
own. Atlased, the same lane is one primitive and one set.

## The rule that makes this work

**Atlas coordinates are emitted into the glTF UVs by the generator.** There is
no post-process that rewrites a finished mesh's texture coordinates, and there
must never be one: by export time `core/batch.py` has merged every prop in a
cell into one vertex buffer, so "which rect does this triangle belong to" is no
longer answerable. The remap happens at the moment the prop is built, while its
material is still known — which is why the API is `atlas.pack(mesh, key)` at
the build site rather than `atlas.fixup(gltf)` at the end.

## What may and may not go in

An atlas cannot tile. A rect has neighbours, and `wrapS = REPEAT` on an atlased
UV samples the barrel next door. So:

- **Eligible**: anything whose UVs stay inside one tile. Props are authored in
  metres and are smaller than their material's coverage, so a 0.55 m crate on a
  1 m `oak` tile uses UV 0..0.55 and is eligible by construction.
- **Not eligible**: any surface that repeats its texture — walls, roofs, paving,
  ground. `pack()` measures the mesh's UV extent and REFUSES rather than
  producing the silently-wrong result, because a wall that samples its
  neighbour's rect is a bug nobody can see the cause of.

Gutters are real repeat-padding, not blank space: each rect's border carries a
copy of the opposite edge of its own tile, so a mip level (or an anisotropic tap
at a grazing angle) blends into more of the same material instead of into the
next one along.

## Why eligibility is decided per MEMBER, not per mesh

The paragraph above was true and it was also why this module sat unused for four
waves. By the time a venue calls `ctx.emit`, its `oak_dark` is one Mesh holding
every jamb, lintel, sill, fascia, bracket and door in the building — two hundred
separate members merged under one key. Measured on a townhouse, that mesh's UVs
span 34 x 21 tiles, so the whole-mesh test refuses it, and refuses `iron`,
`lead`, `painted` and `oak_weathered` with it. Nothing on a building was ever
eligible, which is why the town shipped 902 materials and 1,416 draw calls.

But a 0.16 m jamb is eligible. The members are only inseparable in the *buffer*;
in the *geometry* they are disjoint connected components, and `_components()`
recovers them by welding vertices on position and flooding the index buffer. So
`pack_split()` fits each member's own UV island into the rect on its own, and
returns the members it could not take as a separate loose mesh. A 6 m jetty beam
falls out and keeps its full texel density; the two hundred small members around
it become one draw call.

`MAX_FIT` is the quality floor and it is the reason this is safe. Squeezing a
member's island to one tile costs texel density in exact proportion, so a member
is only taken if the squeeze is under 2x — which on a 512 rect over a 2 m tile
is 126 px/m across a member 0.15 m wide, i.e. 19 texels across its face. Above
that the member is left loose rather than blurred. Art Bible §5 density is a
done-criterion; an atlas that meets the draw budget by failing it is not a win.
"""

from __future__ import annotations

import math
import os
import numpy as np
from PIL import Image

from . import materials as MAT
from .mathx import seed_from
from .mesh import Mesh, Group

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
TEX_DIR = os.path.join(REPO, "assets/textures")

# Texels of repeat-padding around every rect. Four is the smallest number that
# survives the mip chain to the level where a rect is 8 texels across, which is
# about where a prop stops being resolvable anyway.
GUTTER = 4

# How far a member's UV island may be squeezed to reach one tile before the
# member is left out of the page instead. See the module docstring: this is the
# texel-density floor, expressed where it is enforced.
MAX_FIT = 2.0

# Below this share of a mesh's triangles, packing is refused outright. Splitting
# a mesh puts BOTH halves in the cell, so a split that leaves most of the
# geometry loose has bought a second draw call and saved nothing.
MIN_TAKE = 0.45


# Why the take rate is measured and not asserted.
#
# `pack_split` is a quality/draw-call trade made once per MEMBER, and until this
# existed nobody could say which way it had gone. The shipped town had 2,780
# LOD0 primitives with the page already wired in; 725 of them belonged to
# materials that ARE on the page and had been refused member by member, and the
# build printed nothing about it. `build.py --atlas-report` prints this table.
STATS = {}


def _tally(key, page, took_tris, left_tris, need_refused):
    s = STATS.setdefault((page, key), {"took": 0, "left": 0, "members": 0,
                                       "refused": 0, "need": []})
    s["took"] += int(took_tris)
    s["left"] += int(left_tris)
    s["refused"] += len(need_refused)
    s["need"].extend(float(x) for x in need_refused)


def _grid(tiles):
    """The smallest square page, in cells, that a greedy shelf fit can hold.

    Tried rather than solved: the packer below is a first-fit scan and its
    failure mode is a page one cell too small, not a wrong page. Searching up
    from the area lower bound costs microseconds and cannot be wrong.
    """
    tiles = list(tiles)
    need = sum(t * t for t in tiles)
    g = max(max(tiles), int(math.ceil(math.sqrt(need))))
    while True:
        if _try_place(tiles, g) is not None:
            return g
        g += 1


def _try_place(sizes, g):
    """First-fit an ordered list of square blocks into a g x g cell grid."""
    used = np.zeros((g, g), bool)
    out = []
    for n in sizes:
        spot = None
        for r in range(g - n + 1):
            for c in range(g - n + 1):
                if not used[r:r + n, c:c + n].any():
                    spot = (r, c)
                    break
            if spot:
                break
        if spot is None:
            return None
        used[spot[0]:spot[0] + n, spot[1]:spot[1] + n] = True
        out.append(spot)
    return out


def _place(keys, tiles, g):
    """{key: (row, col)} in cells. Big blocks first, then declaration order.

    Sorting by size is what makes the fit tight — a 4x4 block placed after
    thirty 1x1s has no square hole left to go in — and the sort is stable on the
    declared order, so the layout is a function of the declaration and a review
    diff of the page is readable.
    """
    order = sorted(range(len(keys)), key=lambda i: (-tiles[keys[i]], i))
    spots = _try_place([tiles[keys[i]] for i in order], g)
    return {keys[i]: spots[j] for j, i in enumerate(order)}


def _components(v, idx):
    """Per-vertex connected-component labels, welded on position.

    `Builder.poly` appends fresh vertices per polygon, so index connectivity
    alone separates a box into its six faces — which would fit each face of a
    beam to the tile independently and land a different grain scale on each
    side of one member. Welding on rounded position first puts the box back
    together, so a component is a MEMBER.

    Label propagation with pointer jumping rather than a union-find: the same
    answer, vectorised, and deterministic in a way a dict-ordered union is not.
    """
    if not len(idx):
        return np.zeros(len(v), np.int64)
    key = np.round(np.asarray(v, np.float64) * 1000.0).astype(np.int64)
    _, node = np.unique(key, axis=0, return_inverse=True)
    node = np.asarray(node, np.int64).ravel()
    lab = np.arange(int(node.max()) + 1, dtype=np.int64)
    tri = node[np.asarray(idx, np.int64).reshape(-1, 3)]
    a = np.concatenate([tri[:, 0], tri[:, 1], tri[:, 2]])
    b = np.concatenate([tri[:, 1], tri[:, 2], tri[:, 0]])
    for _ in range(64):
        prev = lab.copy()
        m = np.minimum(lab[a], lab[b])
        np.minimum.at(lab, a, m)
        np.minimum.at(lab, b, m)
        lab = lab[lab]                      # path compression, one hop a pass
        if np.array_equal(lab, prev):
            break
    return lab[node]


class Atlas:
    """A packed page of material tiles, plus the UV transform for each.

    Built at generation time; the PNGs land next to every other texture set and
    are referenced by the same `material_from_set` path, so nothing downstream
    knows the difference.
    """

    def __init__(self, name, keys, cell=512):
        self.name = name
        # A page entry is `key` or `key: tiles`. `tiles` is how many repeats of
        # the material's own tile the rect holds along each axis — see `TILES`.
        spec = dict(keys) if isinstance(keys, dict) else {k: 1 for k in keys}
        self.keys = list(spec)                      # de-duplicated, order kept
        self.tiles = {k: int(spec[k]) for k in self.keys}
        for k, r in self.tiles.items():
            if r not in (1, 2, 4, 8):
                raise ValueError(
                    f"atlas '{name}' asks for {r} tiles on '{k}'. The rect's "
                    f"interior is `r*cell - 2*GUTTER` texels and each of the r "
                    f"tiles in it must be a whole number of them, so r must "
                    f"divide 2*GUTTER = {2 * GUTTER}.")
        self.cell = int(cell)
        if not self.keys:
            raise ValueError("an atlas with no materials in it")
        self.cols = self.rows = _grid(self.tiles.values())
        self.size = self.cols * self.cell
        self._rect = {}
        for k, (r, c) in _place(self.keys, self.tiles, self.cols).items():
            n = self.tiles[k]
            # Inset by the gutter so the usable area is the padded interior.
            self._rect[k] = ((c * self.cell + GUTTER) / self.size,
                             (r * self.cell + GUTTER) / self.size,
                             (n * self.cell - 2 * GUTTER) / self.size,
                             (n * self.cell - 2 * GUTTER) / self.size)
        # A rect holds `n*cell - 2*GUTTER` texels of `n` tiles of a material
        # that covers `coverage` metres each, so this is the metres a rect
        # spans — and dividing a mesh's metre-UVs by it lands them in the rect.
        # Texel density is therefore INDEPENDENT of `n`: a 2-tile rect is twice
        # the pixels over twice the metres. What `n` buys is reach — a member up
        # to n tiles long fits without being squeezed at all.
        self._cov = {k: MAT.LIBRARY[k].coverage * self.tiles[k] for k in self.keys}

    # -- geometry side ------------------------------------------------------

    def rect(self, key):
        """(u0, v0, du, dv) in atlas UV space."""
        return self._rect[key]

    def _cellpos(self, key):
        """(row, col) of this key's rect, in whole cells."""
        u0, v0, _, _ = self._rect[key]
        return (int(round(v0 * self.size - GUTTER)) // self.cell,
                int(round(u0 * self.size - GUTTER)) // self.cell)

    def uv_scale(self, key):
        """UV units per world metre for a prop packed into this atlas."""
        return self._rect[key][2] / self._cov[key]

    def pack(self, geom, key=None, strict=True):
        """Remap a Mesh's (or a whole Group's) UVs into their atlas rects.

        In place, and returns the mesh so it composes at the call site:

            ctx.emit(atlas.pack(kit.barrel(...)), atlas.name)

        A Group is packed part by part using each part's own material key,
        which is the common case — a barrel is oak and iron.
        """
        if geom is None:
            return geom
        if isinstance(geom, Group):
            merged = Mesh(mat=self.name)
            for k, part in geom.items():
                merged.merge(self.pack(part, k, strict))
            return merged
        k = key or geom.mat
        if k not in self._rect:
            raise KeyError(f"'{k}' is not in atlas '{self.name}' "
                           f"(has: {', '.join(self.keys)})")
        if len(geom.uv) == 0:
            return geom.with_material(self.name)

        # UVs are in metres (core/mesh.py `_planar_uv`). Bring them to 0..1 of
        # the material's own tile first, then into the rect.
        uv = np.asarray(geom.uv, np.float64) / self._cov[k]
        lo, hi = uv.min(axis=0), uv.max(axis=0)
        span = hi - lo
        if strict and (span[0] > 1.0 + 1e-6 or span[1] > 1.0 + 1e-6):
            raise ValueError(
                f"cannot atlas '{k}': its UVs span {span[0]:.2f} x {span[1]:.2f} "
                f"tiles, so it RELIES ON REPEAT. An atlased rect has neighbours "
                f"— repeating it samples the material packed next to it. Leave "
                f"tiling surfaces (walls, roofs, paving) out of the atlas.")
        # Shift each prop's UV island to the origin before scaling in. Props
        # are authored about their own centre, so half their UVs are negative;
        # mapping those straight into a rect walks off the left edge into the
        # rect before it, which is exactly the artefact this class exists to
        # prevent.
        #
        # Shift by `lo`, not by `floor(lo)`. Flooring lands a 0.55 m crate on
        # a 2 m tile at UV 0.86-1.14, and the clamp then truncates a seventh of
        # the box onto the rect's right edge as a smear. Every material in the
        # library tiles seamlessly, so WHICH part of the tile a prop samples
        # carries no information — only that it samples one tile's worth.
        u0, v0, du, dv = self._rect[k]
        uv = np.clip(uv - lo, 0.0, 1.0)
        out = np.empty_like(uv)
        out[:, 0] = u0 + uv[:, 0] * du
        out[:, 1] = v0 + uv[:, 1] * dv
        geom.uv = out.astype(np.float32)
        geom.mat = self.name
        return geom

    def pack_split(self, mesh, key=None, max_fit=MAX_FIT, min_take=MIN_TAKE):
        """(atlased, leftover) — take the members that fit, leave the rest.

        This is the entry point everything else uses. `pack()` above is the
        all-or-nothing form and survives for callers that have already proved
        their geometry is one island.

        Each connected member is fitted into one tile on its own: an island
        already inside a tile is mapped at its authored density, one that
        overruns is scaled down uniformly (aspect preserved — a squeezed axis
        would read as stretched grain), and one that would need more than
        `max_fit` is refused and stays under its own material.
        """
        if mesh is None or not mesh.tri_count:
            return None, None
        k = key or mesh.mat
        if k not in self._rect:
            return None, mesh
        if not len(mesh.uv):
            return mesh.with_material(self.name), None

        cov = self._cov[k]
        uv = np.asarray(mesh.uv, np.float64) / cov
        lab = _components(mesh.v, mesh.idx)
        cid, comp = np.unique(lab, return_inverse=True)
        n = len(cid)

        lo = np.full((n, 2), np.inf)
        hi = np.full((n, 2), -np.inf)
        np.minimum.at(lo, comp, uv)
        np.maximum.at(hi, comp, uv)
        span = np.maximum(hi - lo, 0.0).max(axis=1)
        # 0.98 rather than 1.0: a member that exactly fills its rect has its
        # outermost texel row landing on the gutter, which is a wrap of the
        # opposite edge and reads as a seam along the member's arris.
        need = span / 0.98
        ok = need <= max_fit
        scale = np.where(need > 1.0, 0.98 / np.maximum(span, 1e-9), 1.0)

        keep = ok[comp]
        tri = keep[np.asarray(mesh.idx, np.int64).reshape(-1, 3)].all(axis=1)
        took = int(tri.sum())
        refused = need[~ok]
        if took == 0 or took < min_take * mesh.tri_count:
            _tally(k, self.name, 0, mesh.tri_count, need)
            return None, mesh
        _tally(k, self.name, took, mesh.tri_count - took, refused)

        u0, v0, du, dv = self._rect[k]
        out = np.clip((uv - lo[comp]) * scale[comp, None], 0.0, 1.0)
        out[:, 0] = u0 + out[:, 0] * du
        out[:, 1] = v0 + out[:, 1] * dv

        packed = _select(mesh, tri, out.astype(np.float32), self.name)
        left = None if took == mesh.tri_count else _select(mesh, ~tri, mesh.uv, k)
        return packed, left

    def pack_eligible(self, group, max_fit=MAX_FIT, min_take=MIN_TAKE):
        """Atlas the parts of a Group this page covers; leave the rest alone.

        `pack()` is all-or-nothing and raises on a material it does not hold,
        which makes it unusable on a dressed arrangement — a yard holds a
        barrel in `oak`, a water butt with an `algae` ring and a `water` disc,
        and two of those three are ineligible. Refusing the whole arrangement
        because of the water is how a venue author gives up on atlasing and
        pays nine draw calls for a back lane.

        Returns a new Group: one merged part under this atlas's name for
        everything it could take, plus each remaining material untouched. The
        common `core/props.py` dressing collapses 8-11 materials to 2-3.
        """
        out = Group()
        take = Mesh(mat=self.name)
        for k, part in group.items() if isinstance(group, Group) else [(group.mat, group)]:
            packed, left = self.pack_split(part.copy(), k, max_fit, min_take)
            if packed is not None:
                take.merge(packed)
            if left is not None:
                out.add(left, k)
        if take.tri_count:
            out.add(take, self.name)
        return out

    # -- texture side -------------------------------------------------------

    def write(self, outdir=TEX_DIR, force=False):
        """Compose and write the atlas page for every channel.

        Sources are generated at a power-of-two size and then AREA-resampled
        into the rect, never generated at the rect size directly. A rect is
        `cell - 2*GUTTER` texels — 504 at the default — and asking a builder
        for a 504 px map puts its `fbm(s, 90)` octave at 5.6 px per cycle,
        which is the aliasing floor `core/materials.py` sets SIZE_MIN to avoid.
        Generating at 512 and box-filtering down is the same operation a mip
        chain performs, and it is the only one that does not turn fine detail
        into static.
        """
        os.makedirs(outdir, exist_ok=True)
        base = os.path.join(outdir, self.name)
        if not force and os.path.exists(base + "_albedo.png"):
            return base

        want_emissive = any("emissive" in MAT.LIBRARY[k].flags for k in self.keys)
        want_alpha = any("mask" in MAT.LIBRARY[k].flags for k in self.keys)
        pages = {
            "albedo": np.zeros((self.size, self.size, 4 if want_alpha else 3), np.float32),
            "orm": np.zeros((self.size, self.size, 3), np.float32),
            "normal": np.zeros((self.size, self.size, 3), np.float32),
        }
        pages["normal"][..., :] = (0.5, 0.5, 1.0)
        if want_emissive:
            pages["emissive"] = np.zeros((self.size, self.size, 3), np.float32)

        for k in self.keys:
            n = self.tiles[k]
            # `unit` is one tile's texels inside this rect, and `n * unit` is the
            # rect's interior — which is why `n` must divide `2 * GUTTER`. Every
            # material in the library tiles seamlessly, so an n x n repeat inside
            # the rect is continuous and a member three tiles long crosses the
            # joins without a seam.
            inner = n * self.cell - 2 * GUTTER
            unit = inner // n
            gen = int(2 ** math.ceil(math.log2(max(unit, MAT.SIZE_MIN))))
            m = MAT.LIBRARY[k](name=k, size=gen,
                               seed=seed_from("material", k) % 9973)
            tiles = _channels(m)
            r, c = self._cellpos(k)
            y0, x0 = r * self.cell, c * self.cell
            for ch, img in tiles.items():
                if ch not in pages:
                    continue
                page = pages[ch]
                nc = page.shape[2]
                src = img if img.shape[2] >= nc else np.concatenate(
                    [img, np.ones(img.shape[:2] + (nc - img.shape[2],), np.float32)],
                    axis=-1)
                src = _resize(src[..., :nc], unit)
                if n > 1:
                    src = np.tile(src, (n, n, 1))
                # Repeat-pad: the gutter is a wrap of the tile's own opposite
                # edge, so a mip tap that strays outside the rect lands on more
                # of the same material.
                pad = np.pad(src, ((GUTTER, GUTTER), (GUTTER, GUTTER), (0, 0)),
                             mode="wrap")
                page[y0:y0 + n * self.cell, x0:x0 + n * self.cell, :] = pad
            # A resampled normal map is no longer unit length, and a
            # non-normalised normal darkens the whole prop under any lighting
            # model that trusts it.
            if "normal" in pages:
                sub = pages["normal"][y0:y0 + n * self.cell, x0:x0 + n * self.cell]
                nv = sub * 2.0 - 1.0
                nv /= np.maximum(np.linalg.norm(nv, axis=-1, keepdims=True), 1e-6)
                pages["normal"][y0:y0 + n * self.cell,
                                x0:x0 + n * self.cell] = nv * 0.5 + 0.5

        _write(base + "_albedo.png", pages["albedo"])
        _write(base + "_orm.png", pages["orm"])
        _write(base + "_normal.png", pages["normal"])
        if want_emissive:
            _write(base + "_emissive.png", pages["emissive"])
        return base

    # -- reporting ----------------------------------------------------------

    def report(self):
        """What the atlas saved, in the units Directive §7 budgets."""
        loose = sum(MAT.LIBRARY[k].size ** 2 *
                    (4 if "emissive" in MAT.LIBRARY[k].flags else 3)
                    for k in self.keys)
        want_emissive = any("emissive" in MAT.LIBRARY[k].flags for k in self.keys)
        mine = self.size ** 2 * (4 if want_emissive else 3)
        return {
            "atlas": self.name,
            "materials": len(self.keys),
            "page": self.size,
            "cell": self.cell,
            "sets_replaced": len(self.keys),
            "loose_mb": loose * 4 * 1.334 / 1e6,
            "atlas_mb": mine * 4 * 1.334 / 1e6,
            "density": inner_density(self),
        }


def _select(mesh, tri, uv, mat):
    """The sub-mesh of `mesh` under a triangle mask, with `uv` substituted.

    Vertices are re-indexed rather than kept whole: a split that keeps every
    vertex in both halves doubles the vertex buffer of the largest venue in the
    build, and mesh memory is already 1 % over its budget.
    """
    idx = np.asarray(mesh.idx, np.int64).reshape(-1, 3)[tri].ravel()
    used, remap = np.unique(idx, return_inverse=True)
    return Mesh(mesh.v[used], mesh.n[used], np.asarray(uv, np.float32)[used],
                remap.astype(np.uint32),
                None if mesh.col is None else mesh.col[used], mat)


def inner_density(a):
    """px per world metre inside a rect, so the §5 class can still be checked.

    Independent of a key's tile count by construction — `_cov` already carries
    the multiplier — which is the property that makes multi-tile rects a
    draw-call win with no §5 cost. It is asserted nowhere and measured here.
    """
    return {k: (a.tiles[k] * a.cell - 2 * GUTTER) / a._cov[k] for k in a.keys}


def _channels(m):
    """A MaterialSet's channels as float images, matching MaterialSet.write."""
    from . import materials as _M
    # Exposure first, exactly as `MaterialSet.write` does it — this function is
    # a second copy of that pipeline and it silently skipped the step, so every
    # material packed into an atlas page shipped at its authored appearance
    # value while its standalone twin shipped exposure-corrected. Measured:
    # `kit_props` p95 0.847 against `plaster` 0.711 for the same plaster.
    alb = _M.expose(m.albedo, m.alpha)
    if m.alpha is not None:
        alb = _M._dilate(alb, m.alpha)
    out = {}
    a = np.clip(_M.P.linear_to_srgb(np.clip(alb, 0, 1)), 0, 1)
    if m.alpha is not None:
        a = np.concatenate([a, np.clip(m.alpha, 0, 1)[..., None]], axis=-1)
    out["albedo"] = a.astype(np.float32)
    out["orm"] = np.stack([np.clip(m.ao, 0, 1), np.clip(m.roughness, 0, 1),
                           np.clip(m.metalness, 0, 1)], axis=-1).astype(np.float32)
    out["normal"] = m._normal_from_height(2.0).astype(np.float32)
    if m.emissive is not None:
        out["emissive"] = np.clip(
            _M.P.linear_to_srgb(np.clip(m.emissive, 0, 1)), 0, 1).astype(np.float32)
    return out


def _resize(img, n):
    """Area-average an (S,S,C) float image down to (n,n,C). Deterministic.

    Pillow's resamplers are the obvious tool and are not used here: their
    output has changed between Pillow versions, and docs/ARCHITECTURE.md §7
    makes byte-stability across environments a hard requirement. A box filter
    written out is fixed forever.
    """
    s = img.shape[0]
    if s == n:
        return img
    # Fractional-coverage box filter, so non-integer ratios (512 -> 504) are
    # still an area average rather than a nearest-neighbour with extra steps.
    e = np.linspace(0, s, n + 1)
    out = np.empty((n, n, img.shape[2]), np.float32)
    rows = np.empty((n, s, img.shape[2]), np.float32)
    for i in range(n):
        a, b = e[i], e[i + 1]
        i0, i1 = int(np.floor(a)), int(np.ceil(b))
        w = np.clip(np.minimum(np.arange(i0, i1) + 1, b) -
                    np.maximum(np.arange(i0, i1), a), 0, None).astype(np.float32)
        rows[i] = (img[i0:i1] * w[:, None, None]).sum(0) / max(w.sum(), 1e-6)
    for j in range(n):
        a, b = e[j], e[j + 1]
        j0, j1 = int(np.floor(a)), int(np.ceil(b))
        w = np.clip(np.minimum(np.arange(j0, j1) + 1, b) -
                    np.maximum(np.arange(j0, j1), a), 0, None).astype(np.float32)
        out[:, j] = (rows[:, j0:j1] * w[None, :, None]).sum(1) / max(w.sum(), 1e-6)
    return out


def _write(path, arr):
    a = np.clip(arr, 0, 1)
    mode = {3: "RGB", 4: "RGBA"}[a.shape[-1]]
    Image.fromarray((a * 255).astype(np.uint8), mode).save(path, optimize=True)


# ---------------------------------------------------------------------------
# The standing atlases
# ---------------------------------------------------------------------------
# Declared here rather than per venue so that two venues asking for "the prop
# atlas" get the same page — which is the point. An atlas that is rebuilt per
# venue saves draw calls inside a venue and loses them across the town.

ATLASES = {
    # THE kit page. One page, applied automatically by `ctx.emit` to every
    # venue in the town, holding the whole non-tiling vocabulary: the joinery
    # and ironmongery of the building kit, and everything a back lane, a yard
    # or a market stall is made of.
    #
    # One page rather than the two ("kit_props" and "kit_trim") this file used
    # to declare, because the unit that costs a draw call is the (cell,
    # material) pair and a townhouse cell holds both — its window frames AND
    # the barrels in its yard. Two pages would have cost that cell two draws to
    # save eight; one costs it one to save nine. Measured across the town, the
    # split pages saved 1,017 of 3,050 LOD0 primitives and the single page
    # saves the same 1,017 for half the texture memory.
    #
    # What is NOT in here is the whole of the design: no walling, no roofing,
    # no paving, no ground, no water, no glass, no foliage. Every one of those
    # repeats its texture across a surface, and a repeated atlas UV samples the
    # material packed next to it. `pack_split` would refuse them member by
    # member anyway; leaving them out means it never has to try.
    # The number after a key is how many of its own tiles the rect holds along
    # each axis. It is NOT a quality dial — texel density is invariant under it
    # (see `Atlas.__init__`) — it is REACH. A rect of one tile can only hold a
    # member up to `MAX_FIT` tiles long before the squeeze costs more density
    # than Art Bible §5 allows, and on `oak` at 2 m coverage that is a 4 m
    # member. A building is full of members longer than that: wall plates, sole
    # plates, jetty bressumers, principal posts, purlins, door leaves, the iron
    # straps on them and the lead flashing over them. Every one was refused,
    # and every refusal put its material back in the cell as its own draw call.
    #
    # Measured on `townhouse` (57 buildings, the town's largest venue): 212
    # `oak` members refused at a median squeeze of 2.0 and 157 `oak_dark` at
    # 13.1. Four tiles takes the first group whole. The 13.1s are welded
    # terrace-length runs and stay out, which is correct — a 26 m member has no
    # business on a page.
    "kit": {
        # timber — the long members, and the reason this page has tile counts
        "oak": 2, "oak_dark": 2, "oak_weathered": 2, "timber_grey": 2,
        "elm": 2, "endgrain": 1, "pine_tarred": 2,
        # metal — straps, hinges, tie bars, and lead in long dressed lengths
        "iron": 2, "iron_pitted": 2, "steel_blued": 1, "brass": 1,
        "lead": 2, "copper": 2,
        # paint and dressings
        "painted": 2, "painted_crimson": 2, "painted_amber": 1,
        "sandstone": 2, "ridge": 2,
        # cloth, cordage and soft goods — awnings and sacks are small; a
        # tilt over a waggon is not
        "canvas": 2, "canvas_plain": 2, "sacking": 1, "linen": 1,
        "straw": 2, "reed": 2,
        "leather": 1, "hide_raw": 1, "fleece": 1, "wool_undyed": 1,
        "cloth_brown": 1, "cloth_cream": 1, "cloth_rust": 1,
        # trade goods
        "pottery": 1, "beeswax": 1, "tallow": 1, "fish": 1, "bread": 1,
    },
    # The public realm: everything `core/streetscape.py` stands in a street.
    #
    # It needs its own page rather than `kit_props` because street furniture is
    # mostly STONE — bollards, spur stones, mounting blocks, thresholds,
    # crossing stones, well rings, troughs — and the props page has no stone in
    # it. Measured on the streets venue: without this page 347 props spread 13
    # extra materials across 32 cells and cost 322 primitives; with it the same
    # props are one primitive per cell.
    #
    # `stone`, `sett` and `earth` also tile as PAVING elsewhere in the same
    # venue, which is not a conflict: `pack` is applied to the prop, never to
    # the surface, and it refuses anything whose UVs span more than one tile.
    "street_props": ("stone", "sett", "sandstone", "oak", "oak_weathered",
                     "oak_dark", "iron", "endgrain", "elm", "timber_grey",
                     "straw", "canvas", "moss", "algae", "dirt", "earth",
                     "foliage", "foliage_flower", "linen", "cloth_cream",
                     "cloth_rust"),
}


# Pages `ctx.emit` applies on its own, in priority order. A material in two
# pages goes to the first that names it, so the mapping is a function and two
# venues cannot disagree about where `oak` lives.
#
# `street_props` is NOT in here. It holds `stone`, `sett`, `earth` and `dirt`
# because street furniture is mostly stone, and those four are also the paving
# of the venue that owns it — so it is only safe applied deliberately, to a
# prop, which is what `venues/streets.py` does.
AUTO = ("kit",)

_AUTO_OF = {}
for _page in AUTO:
    for _k in ATLASES[_page]:
        _AUTO_OF.setdefault(_k, _page)


def page_for(key):
    """The atlas page `ctx.emit` should route this material to, or None."""
    return _AUTO_OF.get(key)


def get(name, cell=512):
    """The shared atlas for `name`. Built once per process."""
    if name not in ATLASES:
        raise KeyError(f"unknown atlas '{name}' (have: {', '.join(ATLASES)})")
    key = (name, cell)
    if key not in _CACHE:
        _CACHE[key] = Atlas(name, ATLASES[name], cell=cell)
    return _CACHE[key]


_CACHE = {}
