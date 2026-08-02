"""Static batching, cell partitioning and LOD decimation.

This is the file that decides what a frame costs. Everything here runs at BUILD
time and produces geometry the runtime can throw away cheaply — which is the
only kind of optimisation that survives contact with a 90-building town.

Three jobs:

1. **Cell assignment.** Every emitted object is bucketed into a 16 m cell (the
   same module `docs/ARCHITECTURE.md` §3 partitions entities on) and merged with
   everything else in that cell that shares a material. One primitive per
   (cell, material) is one draw call, and it is also the unit the client culls
   and LODs, so batching and culling agree by construction rather than by
   discipline.

2. **LOD decimation.** A deterministic grid vertex-clustering simplifier. Not
   quadric error — QEM is better per triangle but is neither cheap nor
   byte-stable across numpy versions, and `docs/ARCHITECTURE.md` §7 makes
   determinism non-negotiable. Clustering is O(n), reproducible, and its
   failure mode (thin features collapsing) is invisible at the distances the
   coarse levels are drawn at.

3. **Instance grouping.** Repeated props are grouped by (mesh id, cell) so they
   export as one `EXT_mesh_gpu_instancing` node — an Unreal
   `InstancedStaticMeshComponent` or a Unity `Graphics.DrawMeshInstanced` batch
   with no re-authoring.

**Cell keys are VENUE-LOCAL, not world.** A venue mesh is placed by
`content/town/hearthmere.json`, sometimes more than once and usually with a
rotation, so a world cell baked into the file would be a lie for the second
placement. The client derives the world cell from each batch node's transformed
bounds. The grid is therefore phase-shifted per venue; that costs nothing,
because culling wants spatial coherence, not global alignment.
"""

from __future__ import annotations

import numpy as np

from .mesh import Mesh, Group

# The town cell module. Kept equal to content/town/hearthmere.json grid.cellSize
# — a venue may override it (terrain does) but may not silently disagree.
CELL = 16.0

# An object whose plan extent exceeds this many cells is split triangle-by-
# triangle instead of being assigned whole. Below it, objects stay intact so a
# barrel is never sliced in half by a cull boundary.
SPLIT_CELLS = 2.0


# LOD switch distances in metres (BUILD_DIRECTIVE §7). Level i is drawn from
# LOD_DISTANCES[i-1] out to LOD_DISTANCES[i]; level 0 starts at the camera.
LOD_DISTANCES = (15.0, 40.0, 100.0)
LOD_RATIOS = (1.0, 0.5, 0.2, 0.06)


def cell_index(x, z, size=CELL):
    return int(np.floor(x / size)), int(np.floor(z / size))


def cell_name(i, j):
    """A filename- and glTF-node-safe cell key. Negative indices get an `n`
    prefix rather than a minus sign, which some importers mangle."""
    f = lambda v: (f"n{-v}" if v < 0 else f"{v}")
    return f"{f(i)}_{f(j)}"


def assign_cells(m: Mesh, size=CELL, split_cells=SPLIT_CELLS):
    """Bucket a mesh's triangles into cells. Returns [(cell_key, Mesh)].

    Small objects are assigned whole to the cell containing their centroid.
    Large ones (roads, terrain plates, town walls) are split per triangle so
    that a network spanning the town does not force every cell it touches to be
    resident.
    """
    if m.tri_count == 0:
        return []
    lo, hi = m.bounds()
    span = max(hi[0] - lo[0], hi[2] - lo[2])
    if span <= size * split_cells:
        c = (lo + hi) * 0.5
        return [(cell_name(*cell_index(c[0], c[2], size)), m)]
    return _split_by_triangle(m, size)


def _split_by_triangle(m: Mesh, size):
    idx = m.idx.reshape(-1, 3)
    tri = m.v[idx]                                   # (T, 3, 3)
    cen = tri.mean(axis=1)
    ij = np.stack([np.floor(cen[:, 0] / size), np.floor(cen[:, 2] / size)],
                  axis=1).astype(np.int64)
    # Grouped on the (i, j) pair itself rather than a packed integer key:
    # packing then unpacking is where a sign bug hides, and a cell key that is
    # silently wrong for negative coordinates would mis-place half the town.
    cells, inv = np.unique(ij, axis=0, return_inverse=True)
    out = []
    for c in range(len(cells)):
        sel = idx[inv == c]
        used, remap = np.unique(sel.reshape(-1), return_inverse=True)
        sub = Mesh(m.v[used], m.n[used], m.uv[used],
                   remap.astype(np.uint32),
                   None if m.col is None else m.col[used], m.mat)
        out.append((cell_name(int(cells[c, 0]), int(cells[c, 1])), sub))
    return out


# ---------------------------------------------------------------------------
# Decimation
# ---------------------------------------------------------------------------

def _cluster(m: Mesh, s):
    """Collapse vertices onto an `s`-metre grid. Returns a flat-shaded Mesh."""
    q = np.floor(m.v / s).astype(np.int64)
    # A 3D key. The offsets keep the product inside int64 for any town-sized
    # coordinate: our world is +/- 300 m, so at s >= 1 mm the indices fit.
    key = (q[:, 0] * 2654435761 + q[:, 1] * 2246822519 + q[:, 2] * 3266489917)
    uniq, inv = np.unique(key, return_inverse=True)
    n = len(uniq)
    # Cluster representative: the mean of its members. Averaging UVs alongside
    # keeps texel density roughly right; the alternative (picking a member) puts
    # a visible seam wherever two clusters straddle a UV discontinuity.
    pos = np.zeros((n, 3), np.float64)
    uv = np.zeros((n, 2), np.float64)
    cnt = np.zeros(n, np.float64)
    np.add.at(pos, inv, m.v.astype(np.float64))
    np.add.at(uv, inv, m.uv.astype(np.float64))
    np.add.at(cnt, inv, 1.0)
    cnt = np.maximum(cnt, 1.0)[:, None]
    pos /= cnt
    uv /= cnt
    col = None
    if m.col is not None:
        cc = np.zeros((n, m.col.shape[1]), np.float64)
        np.add.at(cc, inv, m.col.astype(np.float64))
        col = (cc / cnt).astype(np.float32)

    tri = inv[m.idx.reshape(-1, 3)]
    keep = ((tri[:, 0] != tri[:, 1]) & (tri[:, 1] != tri[:, 2]) & (tri[:, 0] != tri[:, 2]))
    tri = tri[keep]
    if not len(tri):
        return None
    # De-duplicate: two coplanar source triangles can collapse onto the same
    # cluster triple and would then z-fight.
    srt = np.sort(tri, axis=1)
    _, first = np.unique(srt, axis=0, return_index=True)
    tri = tri[np.sort(first)]

    a, b, c = pos[tri[:, 0]], pos[tri[:, 1]], pos[tri[:, 2]]
    nrm = np.cross(b - a, c - a)
    ln = np.linalg.norm(nrm, axis=1, keepdims=True)
    ok = ln[:, 0] > 1e-12
    tri, nrm, ln = tri[ok], nrm[ok], ln[ok]
    if not len(tri):
        return None
    nrm = nrm / ln

    # Flat-shaded output: one vertex triple per surviving triangle. The source
    # geometry is flat-shaded too (Art Bible §6 chamfers need faceted normals),
    # so this costs nothing in vertex count and keeps the chamfer read.
    v = pos[tri.reshape(-1)].astype(np.float32)
    uvo = uv[tri.reshape(-1)].astype(np.float32)
    no = np.repeat(nrm, 3, axis=0).astype(np.float32)
    io = np.arange(len(v), dtype=np.uint32)
    co = None if col is None else col[tri.reshape(-1)]
    return Mesh(v, no, uvo, io, co, m.mat)


def decimate(m: Mesh, ratio, min_tris=8):
    """Reduce `m` to about `ratio` of its triangles. Deterministic.

    Returns the original mesh when it is already small enough to be pointless
    to simplify — a 12-triangle bracket has no LOD1.
    """
    if m is None or m.tri_count <= min_tris or ratio >= 0.999:
        return m
    target = max(min_tris, int(m.tri_count * ratio))
    lo, hi = m.bounds()
    diag = float(np.linalg.norm(hi - lo))
    if diag <= 1e-6:
        return m

    # Bisect on the grid size. Triangle count falls monotonically with s, so
    # this converges; 14 steps over four decades resolves to ~0.06%.
    smin, smax = diag * 1e-4, diag * 0.75
    best = None
    for _ in range(14):
        s = np.sqrt(smin * smax)                      # geometric mean: scale-free
        cand = _cluster(m, s)
        n = 0 if cand is None else cand.tri_count
        if n <= target:
            best = cand if cand is not None else best
            smax = s
            if n >= target * 0.85:
                break
        else:
            best = cand
            smin = s
    if best is None or best.tri_count < 3:
        return m
    return best


def lod_chain(m, ratios=(1.0, 0.5, 0.2, 0.06)):
    """Build a decimation chain for a Mesh or a Group. Level 0 is the input."""
    if isinstance(m, Group):
        return [Group({k: (v if i == 0 else decimate(v, r))
                       for k, v in m.parts.items()})
                for i, r in enumerate(ratios)]
    return [m if i == 0 else decimate(m, r) for i, r in enumerate(ratios)]


# ---------------------------------------------------------------------------
# Material collapse for the coarse levels
# ---------------------------------------------------------------------------

def surface_area(m: Mesh):
    """Total triangle area. The correct measure of "how much of this do you
    see", which triangle COUNT is not — see collapse_materials."""
    if m is None or not m.tri_count:
        return 0.0
    t = m.v[m.idx.reshape(-1, 3)]
    return float(np.linalg.norm(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]),
                                axis=1).sum() * 0.5)


def collapse_materials(parts: dict, keep_share=0.03, max_materials=None):
    """Fold minor materials into the dominant one, ranked by SURFACE AREA.

    Area, not triangle count, and the difference is not academic. A chamfered
    timber frame is thousands of tiny triangles covering four square metres; a
    plaster panel is a dozen triangles covering forty. Ranking by count made
    oak_dark the dominant material of the Grey Heron Inn, so at 100 m the inn
    collapsed into a solid dark-brown box with no plaster and no roof — visible
    in the first aerial rendered after batching landed, and the reason this
    function ranks the way it does.

    Below `keep_share` of the group's area a material is merged into whichever
    material carries the most. The colour is wrong by a hair at a distance where
    the whole thing covers a few dozen pixels, and the draw call it saves is
    real.

    `max_materials` turns that from a heuristic into a CEILING, which is the
    property a budget needs. "LOD2 costs at most three draw calls per cell and
    LOD3 at most two" is a sentence you can multiply by 144 cells and get a
    number you can defend; "LOD2 folds materials under 8%" is not, because a
    cell of nine materials at 11% each folds nothing and costs nine.
    """
    live = {k: m for k, m in parts.items() if m is not None and m.tri_count}
    if len(live) <= 1:
        return dict(live)
    area = {k: surface_area(m) for k, m in live.items()}
    total = sum(area.values()) or 1.0
    order = sorted(live, key=lambda k: (-area[k], k))
    dom = order[0]
    keep = set(order[:max_materials]) if max_materials else set(order)
    out, sunk = {}, None
    for k in order:
        m = live[k]
        if k != dom and (area[k] < total * keep_share or k not in keep):
            if sunk is None:
                sunk = live[dom].copy()
            sunk.merge(m)
        elif k != dom:
            out[k] = m
    out[dom] = sunk if sunk is not None else live[dom]
    return out


# ---------------------------------------------------------------------------
# Instance transforms
# ---------------------------------------------------------------------------
#
# `ctx.instance(mesh_id, mesh, transforms)` is called from venue modules written
# by other people, so `transforms` accepts every shape someone would reasonably
# reach for rather than one blessed form. All of them normalise to the triple
# glTF's EXT_mesh_gpu_instancing wants — TRANSLATION / ROTATION / SCALE — which
# is also exactly what an Unreal `FTransform` per ISM instance carries.


def _quat_y(a):
    return (0.0, float(np.sin(a * 0.5)), 0.0, float(np.cos(a * 0.5)))


def _decompose(m):
    """T/R/S from a 4x4 homogeneous matrix (p' = M @ [p,1])."""
    m = np.asarray(m, np.float64).reshape(4, 4)
    t = m[:3, 3]
    b = m[:3, :3]
    s = np.linalg.norm(b, axis=0)
    s = np.where(s < 1e-9, 1.0, s)
    r = b / s
    # Shepperd's method: pick the largest-magnitude component so the divide is
    # never near zero. Naive w-first extraction goes NaN on a 180-degree yaw,
    # which is one in four of the rotations a town full of props actually uses.
    tr = r[0, 0] + r[1, 1] + r[2, 2]
    if tr > 0:
        k = np.sqrt(tr + 1.0) * 2
        q = ((r[2, 1] - r[1, 2]) / k, (r[0, 2] - r[2, 0]) / k, (r[1, 0] - r[0, 1]) / k, 0.25 * k)
    elif r[0, 0] > r[1, 1] and r[0, 0] > r[2, 2]:
        k = np.sqrt(1.0 + r[0, 0] - r[1, 1] - r[2, 2]) * 2
        q = (0.25 * k, (r[0, 1] + r[1, 0]) / k, (r[0, 2] + r[2, 0]) / k, (r[2, 1] - r[1, 2]) / k)
    elif r[1, 1] > r[2, 2]:
        k = np.sqrt(1.0 + r[1, 1] - r[0, 0] - r[2, 2]) * 2
        q = ((r[0, 1] + r[1, 0]) / k, 0.25 * k, (r[1, 2] + r[2, 1]) / k, (r[0, 2] - r[2, 0]) / k)
    else:
        k = np.sqrt(1.0 + r[2, 2] - r[0, 0] - r[1, 1]) * 2
        q = ((r[0, 2] + r[2, 0]) / k, (r[1, 2] + r[2, 1]) / k, 0.25 * k, (r[1, 0] - r[0, 1]) / k)
    return tuple(float(x) for x in t), tuple(float(x) for x in q), tuple(float(x) for x in s)


def normalize_transforms(transforms):
    """-> (T (N,3), R (N,4) xyzw, S (N,3)). Accepts, per element:

        (x, y, z)                      translation
        (x, y, z, rot_y)               translation + yaw in RADIANS
        {"pos": (x,y,z), "rot_y": a, "scale": s or (sx,sy,sz)}
        {"pos": (x,y,z), "rot": (x,y,z,w)}
        a 4x4 numpy matrix

    and, for the whole argument, an (N,3) or (N,4) array.
    """
    arr = None
    if isinstance(transforms, np.ndarray) and transforms.ndim == 2 and transforms.shape[1] in (3, 4):
        arr = transforms
    elif not isinstance(transforms, (list, tuple)):
        transforms = list(transforms)
    if arr is not None:
        transforms = [tuple(float(x) for x in row) for row in arr]

    T, R, S = [], [], []
    for it in transforms:
        if isinstance(it, dict):
            p = tuple(float(x) for x in it.get("pos", it.get("position", (0, 0, 0))))
            if "rot" in it:
                q = tuple(float(x) for x in it["rot"])
            elif "rot_deg" in it:
                q = _quat_y(np.radians(float(it["rot_deg"])))
            else:
                q = _quat_y(float(it.get("rot_y", 0.0)))
            sc = it.get("scale", 1.0)
            s = (float(sc),) * 3 if np.isscalar(sc) else tuple(float(x) for x in sc)
        elif isinstance(it, np.ndarray) and it.shape == (4, 4):
            p, q, s = _decompose(it)
        else:
            vals = tuple(float(x) for x in it)
            if len(vals) == 3:
                p, q, s = vals, (0.0, 0.0, 0.0, 1.0), (1.0, 1.0, 1.0)
            elif len(vals) == 4:
                p, q, s = vals[:3], _quat_y(vals[3]), (1.0, 1.0, 1.0)
            else:
                raise ValueError(
                    f"instance transform of length {len(vals)}; expected (x,y,z), "
                    f"(x,y,z,rot_y), a dict, or a 4x4 matrix")
        T.append(p); R.append(q); S.append(s)
    if not T:
        return (np.zeros((0, 3), np.float32), np.zeros((0, 4), np.float32),
                np.zeros((0, 3), np.float32))
    return (np.asarray(T, np.float32), np.asarray(R, np.float32), np.asarray(S, np.float32))


def _quat_matrix(q):
    x, y, z, w = (float(v) for v in q)
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w),     2 * (x * z + y * w)],
        [2 * (x * y + z * w),     1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w),     2 * (y * z + x * w),     1 - 2 * (x * x + y * y)],
    ], np.float32)


def bake_instances(proto, T, R, S):
    """Stamp a prototype out N times as ordinary geometry.

    This is the fallback path for a consumer with no EXT_mesh_gpu_instancing —
    and, more usefully, the control experiment: `--no-instancing` rebuilds the
    town with instances merged into the cell batches, so the win is measurable
    rather than asserted.
    """
    parts = proto.parts.items() if isinstance(proto, Group) else [(proto.mat, proto)]
    out = Group()
    for key, src in parts:
        if src is None or not src.tri_count:
            continue
        for i in range(len(T)):
            m = src.copy()
            if not np.allclose(S[i], 1.0):
                m.scale(*(float(v) for v in S[i]))
            if abs(R[i][3]) < 0.999999:
                rot = _quat_matrix(R[i])
                m.v = (m.v @ rot.T).astype(np.float32)
                m.n = (m.n @ rot.T).astype(np.float32)
            m.translate(*(float(v) for v in T[i]))
            out.add(m, key)
    return out


def impostor(parts: dict, max_materials=2):
    """The far level: silhouette, roof colour, wall colour, nothing else.

    Two materials rather than one, and that is a deliberate 1-draw-per-cell
    concession. Past 100 m a building IS a roof colour over a wall colour —
    that pair is the entire read, and collapsing it to a single material turns
    a town of orange roofs into a mud-coloured huddle. The whole point of the
    silhouette test in Art Bible §6 is that the skyline reads, and a one-colour
    impostor deletes precisely the contrast the skyline reads by.

    At 144 cells that ceiling is 288 draws for an entire town seen at once,
    against a budget of 900 — which is the trade being bought.
    """
    return collapse_materials(parts, keep_share=0.0, max_materials=max_materials)
