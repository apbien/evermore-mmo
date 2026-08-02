#!/usr/bin/env python3
"""Automated conformance checks.

These catch the mechanical defects — scale errors, palette drift, malformed
entity IDs, missing textures, geometry sunk into the ground or floating above
it. They do NOT and cannot replace the art-director review in
docs/REVIEW_PROTOCOL.md: a mesh can pass every check here and still look like a
prototype, because "lifeless" is not a property a checker can see.

    python tools/validate.py
    python tools/validate.py --venue inn
    python tools/validate.py --quick        # skip the geometry and palette passes

## The noise policy

Every check here is written to the standard set by `core/venue.py`'s
`check_occlusion`: **a check that cries wolf is worse than no check**, because
it trains everyone to skim the output. So:

- Prefer a test whose positives are unarguable. "This mass has no path to the
  ground" is unarguable. "This vertex is below y=0" is not — plinth footings,
  kerbs and the pub's sunken floor all go below grade legitimately.
- Where a tolerance is needed, set it at the point where a human would call the
  result a defect, not at the point where the number stops being pretty.
- Give an escape hatch that costs a line of source (`# anachronism-ok: reason`,
  `PALETTE_WAIVED`) rather than one that costs an argument.
- Report file and line wherever the defect has one.
- Say how many things each check actually looked at. A check that silently
  matches nothing is the most expensive kind of green tick.

## What this deliberately does NOT check

Chamfering (Art Bible §6), roof-to-wall attachment (Directive §6.2), whole-town
walkability (§9), building-mass count (§9), and the arrival composition (§3).
Those need either a renderer or a human. `tools/render/town.mjs` and the review
protocol own them.
"""

from __future__ import annotations

import argparse
import ast
import glob
import json
import math
import os
import re
import sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MESH_DIR = os.path.join(REPO, "assets/meshes")
TEX_DIR = os.path.join(REPO, "assets/textures")
ENT_DIR = os.path.join(REPO, "content/entities")
COL_DIR = os.path.join(REPO, "content/collision")
SCHEMA_DIR = os.path.join(REPO, "content/schemas")
TOWN_PATH = os.path.join(REPO, "content/town/hearthmere.json")
ASSETGEN = os.path.join(REPO, "tools/assetgen")

ID_RE = re.compile(r"^hm\.[a-z_]+(\.[a-z_0-9]+)*$")

# Art Bible §3. Checked against the whole-venue bounding box, so these are
# sanity bounds rather than exact dimensions.
MAX_VENUE_SPAN = 60.0     # m; a single venue larger than this is a layout bug
# Venues that legitimately span the whole town rather than occupying one site.
# `townhouse` is the modular building kit: one venue module generating the 63
# filler masses wherever their slots stand, so its extent is the town's, not a
# site's. It is a network like the streets, not a building.
TOWN_WIDE = {"streets.gltf", "terrain.gltf", "townhouse.gltf",
             "wall.gltf"}
MAX_VENUE_HEIGHT = 22.0   # m; the guild tower is the tallest thing in town
# The ground is not a building. Its vertical span is the landscape's relief
# (the distance ring rises ~28 m above the mere bed) and it defines the datum
# every other check measures against, so height and sink limits do not apply.
#
# `landscape` belongs here and was missing, which is why the town has spent two
# art-director passes hunting an "unidentified floating mass 34.2 m tall".
# There is no mass. `landscape.gltf` spans 553 x 540 m; its y range is
# [-5.90, +28.29] because the mere bed is at -5.9 and the wooded north ridge
# stands at +15 with 13 m distance-wood impostors on it, 250 m outside the
# wall. Measured above the height function, the tallest thing `landscape`
# carries anywhere inside the +/-100 m town box is a 12.8 m oak. See D-054.
LANDSCAPE = {"terrain.gltf", "terrain", "landscape.gltf", "landscape"}
MIN_VENUE_HEIGHT = 0.25

# Directive §7 performance budget.
TRI_BUDGET = 3_500_000
DRAW_BUDGET = 900

# Mesh memory. Directive §7 budgets draw calls, triangles, texture memory and
# shadow lights, and had nothing at all for the bytes of geometry — so the town
# quietly reached 318 MB of vertex and index data with townhouse.bin alone at
# 157 MB. That is not a streaming problem to be solved later: it is the whole
# download for a web client, and no LOD or culling scheme touches it.
#
# 240 MB total is the measured 207 MB after KHR_mesh_quantization (D-042) plus
# room for the venues still unbuilt. 96 MB for one file is townhouse's current
# 103 MB minus a little, deliberately: the modular building kit is the one file
# that is 63 buildings, and it is the one that should be split by cell before
# anything else in the town is optimised.
#
# When this is hit, in order of value: quantize TEXCOORD_0 (measured 71.8 MB,
# 40% of the remaining total — needs KHR_texture_transform, see core/gltf.py),
# make LOD3 an impostor, split townhouse per cell.
MESH_BYTES_BUDGET = 240 * 1024 * 1024
MESH_FILE_BUDGET = 96 * 1024 * 1024

# Art Bible §4 gives appearance targets; `core.materials.expose` maps them to
# physical reflectances. Nothing in the library may ship an albedo brighter
# than fresh limewash, which is where this number comes from — real lime
# plaster tops out near 0.65 sRGB luminance and the brightest natural diffuse
# surface (fresh snow) is about 0.90.
ALBEDO_MEAN_MAX = 0.70
ALBEDO_P99_MAX = 0.86

problems, warnings = [], []


def err(msg, where=None):
    problems.append((where, msg))


def warn(msg, where=None):
    warnings.append((where, msg))


def rel(p):
    return os.path.relpath(p, REPO).replace("\\", "/")


# ---------------------------------------------------------------------------
# glTF reading
# ---------------------------------------------------------------------------

_CT = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16,
       5125: np.uint32, 5126: np.float32}
_NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def _accessor(doc, blob, i):
    """One accessor as an (count, ncomp) array of its RAW component type.

    Three things this has to respect and did not, each of which silently
    produced garbage rather than an error:

    1. **`byteStride`.** D-042's quantized POSITION is a VEC3 SHORT — six
       bytes — and glTF requires each vertex to start on a four-byte boundary,
       so the buffer view declares `byteStride: 8`. Reading `count * 3` shorts
       contiguously therefore walks one short further into the buffer per
       vertex and returns interleaved padding as coordinates. Every mesh in
       `assets/meshes` has strided views (12,581 of them), so the geometry pass
       has been voxelising noise.
    2. **A short tail.** The last element occupies `elem` bytes, not `stride`,
       so a view may end before its final padded row.
    3. Nothing here may assume the buffer is exactly the size the views claim.
    """
    acc = doc["accessors"][i]
    n = _NCOMP[acc["type"]]
    dt = np.dtype(_CT[acc["componentType"]])
    bv = doc["bufferViews"][acc["bufferView"]]
    base = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    elem = dt.itemsize * n
    stride = bv.get("byteStride") or elem
    count = acc["count"]
    need = (count - 1) * stride + elem
    avail = max(0, len(blob) - base)
    raw = np.frombuffer(blob, np.uint8, min(need, avail), base)
    if len(raw) < count * stride:                      # pad the short tail
        raw = np.concatenate([raw, np.zeros(count * stride - len(raw), np.uint8)])
    rows = raw[: count * stride].reshape(count, stride)[:, :elem]
    return np.ascontiguousarray(rows).view(dt).reshape(count, n)


def _dequant(vals, acc):
    """Decode a possibly-normalized accessor to float (glTF 3.6.2.2)."""
    v = vals.astype(np.float64)
    if not acc.get("normalized"):
        return v
    ct = acc["componentType"]
    if ct == 5122:
        return np.maximum(v / 32767.0, -1.0)
    if ct == 5120:
        return np.maximum(v / 127.0, -1.0)
    if ct == 5123:
        return v / 65535.0
    if ct == 5121:
        return v / 255.0
    return v


def _quat_matrix(q):
    x, y, z, w = q
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def _node_trs(nd):
    """(3x3 linear part, translation) for a node's local transform."""
    if "matrix" in nd:
        m = np.asarray(nd["matrix"], float).reshape(4, 4).T   # glTF is column-major
        return m[:3, :3], m[:3, 3]
    s = np.asarray(nd.get("scale", [1.0, 1.0, 1.0]), float)
    r = _quat_matrix(np.asarray(nd.get("rotation", [0.0, 0.0, 0.0, 1.0]), float))
    return r * s[None, :], np.asarray(nd.get("translation", [0.0, 0.0, 0.0]), float)


def _node_prims(doc, blob, nd):
    """LOD0 primitives of one node, in the node's own mesh space, in METRES."""
    V, T, base = [], [], 0
    for p in doc.get("meshes", [])[nd["mesh"]].get("primitives", []):
        ai = p.get("attributes", {}).get("POSITION")
        if ai is None or "indices" not in p:
            continue
        v = _dequant(_accessor(doc, blob, ai), doc["accessors"][ai])
        t = _accessor(doc, blob, p["indices"]).reshape(-1, 3).astype(np.int64)
        V.append(v)
        T.append(t + base)
        base += len(v)
    if not V:
        return None, None
    return np.concatenate(V), np.concatenate(T)


def _instance_transforms(doc, blob, nd):
    """World-local (linear, translation) per EXT_mesh_gpu_instancing instance."""
    ext = nd.get("extensions", {}).get("EXT_mesh_gpu_instancing")
    if not ext:
        return None
    at = ext.get("attributes", {})
    n = None
    for key in ("TRANSLATION", "ROTATION", "SCALE"):
        if key in at:
            n = doc["accessors"][at[key]]["count"]
            break
    if not n:
        return None
    trans = (_dequant(_accessor(doc, blob, at["TRANSLATION"]),
                      doc["accessors"][at["TRANSLATION"]])
             if "TRANSLATION" in at else np.zeros((n, 3)))
    rots = (_dequant(_accessor(doc, blob, at["ROTATION"]),
                     doc["accessors"][at["ROTATION"]])
            if "ROTATION" in at else np.tile([0.0, 0.0, 0.0, 1.0], (n, 1)))
    scales = (_dequant(_accessor(doc, blob, at["SCALE"]),
                       doc["accessors"][at["SCALE"]])
              if "SCALE" in at else np.ones((n, 3)))
    return [(_quat_matrix(rots[i]) * scales[i][None, :], trans[i]) for i in range(n)]


def load_geometry(path):
    """LOD0 geometry of a venue in VENUE-LOCAL METRES.

    Returns `(V, T, instanced)` where `instanced` is a list of
    `(Vbase, Tbase, [(linear, translation), ...])` for every
    EXT_mesh_gpu_instancing node — 10,811 instances across the town, which is
    most of the vegetation and half the wall, so they cannot just be dropped,
    and expanding them into `V` would be 40x the vertices for no extra truth.

    What changed, and why the geometry pass has been meaningless until now:

    - **Positions are quantized** (D-042). `mesh_bounds` was taught this when
      the extension landed; this reader was not, so it returned raw SHORTs in
      +/-32767 and every "metre" the geometry pass printed was ~4000x too big.
      That is also the hang: `voxelise` walks each edge at 0.5 m, and a 65,000
      unit edge is 130,000 samples, capped at 8,000 — per edge, for millions of
      edges. The numpy `_ArrayMemoryError` another agent hit is the same cause.
    - **Node TRS was ignored.** A quantized mesh carries its metres in the
      node's `scale`/`translation`; without them nothing is where it says.
    - **Every LOD level was loaded.** LOD1-3 are separate meshes in the same
      file, so each venue was checked four times over, with the alternates
      stacked on the original.
    """
    doc = json.load(open(path))
    bin_path = os.path.join(os.path.dirname(path), doc["buffers"][0]["uri"])
    if not os.path.exists(bin_path):
        return None, None, []
    blob = open(bin_path, "rb").read()

    # LOD alternates are reachable only through MSFT_lod; the scene lists LOD0.
    alts = set()
    for nd in doc.get("nodes", []):
        alts.update(nd.get("extensions", {}).get("MSFT_lod", {}).get("ids", []))

    V, T, inst, base = [], [], [], 0
    stack = list(doc.get("scenes", [{}])[0].get("nodes", []))
    seen = set()
    while stack:
        i = stack.pop()
        if i in seen or i in alts:
            continue
        seen.add(i)
        nd = doc["nodes"][i]
        stack += nd.get("children", [])
        if "mesh" not in nd:
            continue
        if (nd.get("extras") or {}).get("hm", {}).get("lod", 0) not in (0, None):
            continue
        v, t = _node_prims(doc, blob, nd)
        if v is None:
            continue
        lin, tr = _node_trs(nd)
        xf = _instance_transforms(doc, blob, nd)
        if xf:
            # Compose the node transform into each instance so the base mesh
            # is only voxelised once.
            inst.append((v, t, [(lin @ il, lin @ it + tr) for il, it in xf]))
            continue
        V.append(v @ lin.T + tr)
        T.append(t + base)
        base += len(v)
    if not V:
        return (None, None, inst) if inst else (None, None, [])
    return np.concatenate(V), np.concatenate(T), inst


# ---------------------------------------------------------------------------
# Terrain
# ---------------------------------------------------------------------------

def load_terrain():
    """The single deterministic height function, per Directive §6.3.

    Falls back to a flat plane when `core/terrain.py` does not exist yet, and
    says so in the output — a fallback nobody is told about is how a check
    quietly stops checking anything.
    """
    if ASSETGEN not in sys.path:
        sys.path.insert(0, ASSETGEN)
    try:
        from core import terrain as T           # noqa: F401
        fn = getattr(T, "height", None)
    except Exception:
        fn = None
    if fn is None:
        return (lambda x, z: np.zeros(np.shape(x))), "flat plane y=0 (core/terrain.py absent)"

    # `height` is the real function — dozens of water shapes, pads and ramps,
    # each allocating a full-length temporary — so it costs ~6 us per point and
    # its peak memory is (points x shapes). Two things follow, and both are
    # required rather than nice to have:
    #
    # - **Deduplicate.** A wall has its vertices stacked at the same (x, z), so
    #   `townhouse`'s 1,841,435 vertices are only 234,295 distinct ground
    #   columns. Asking for the other 87% again cost 11 seconds on that venue
    #   alone.
    # - **Chunk.** The transient allocation is what raised the
    #   `numpy._ArrayMemoryError` another agent hit. Capping the batch bounds it
    #   no matter how large a mesh grows.
    CHUNK = 200_000

    def h(x, z):
        x = np.asarray(x, float)
        z = np.asarray(z, float)
        x, z = np.broadcast_arrays(x, z)
        shape = x.shape
        fx, fz = x.ravel(), z.ravel()
        if fx.size == 0:
            return np.zeros(shape)
        # Exact dedup: two float64 packed into one complex128, uniqued in 1-D.
        # `np.unique(..., axis=0)` on the (N,2) pair is the same answer an order
        # of magnitude slower.
        key, inv = np.unique(fx + 1j * fz, return_inverse=True)
        ux, uz = key.real.copy(), key.imag.copy()
        out = np.empty(len(ux))
        for s in range(0, len(ux), CHUNK):
            e = min(s + CHUNK, len(ux))
            try:
                r = np.asarray(fn(ux[s:e], uz[s:e]), float)
                if r.shape != ux[s:e].shape:
                    raise ValueError("height() did not answer element-wise")
            except Exception:
                r = np.asarray([float(fn(float(a), float(b)))
                                for a, b in zip(ux[s:e], uz[s:e])])
            out[s:e] = r
        return out[inv].reshape(shape)

    return h, "core/terrain.py height()"


# ---------------------------------------------------------------------------
# Mass placement: nothing sunk, nothing floating (Directive §6.1)
# ---------------------------------------------------------------------------

VOXEL = 0.5          # m; connectivity resolution for "is this one mass?"
FLOAT_GAP = 0.60     # m of clear air under a mass before it is called floating
FLOAT_MIN_VOX = 4    # smaller than ~0.5 m^3 is reported as a warning, not a failure
SINK_DEEP = 2.00     # m below terrain before a vertex is worth a warning
BURIED_EPS = 0.05    # m; a mass whose highest point is under the ground
# The longest single edge in the town is the terrain ring's 576 m skirt, so
# 1,600 steps of 0.375 m covers every real edge. A cap 5x that only ever fires
# on garbage input, and firing at 8,000 was what turned garbage into a hang.
MAX_EDGE_STEPS = 1600


def _pow2(n):
    return np.clip(2 ** np.ceil(np.log2(np.maximum(n, 1.0))), 1, 256).astype(int)


# A voxel key is ONE int64, not three int32s and not a hash of them.
#
# Two things came out of the old `(i,j,k)` array plus XOR-hash pair. The hash
# `(i*73856093) ^ (j*19349663) ^ (k*83492791)` is not injective, so two voxels
# metres apart could share a code and be welded into one connected component —
# a floating mass silently absorbed into the building next to it, which is the
# one answer this check exists to give. And `np.unique(..., axis=0)` on an
# (N, 3) array sorts structured rows, which on `landscape`'s ~30 M samples was
# most of the pass's 100 seconds.
#
# 20-bit fields at a 0.5 m voxel cover +/-262 km, and three of them plus sign
# headroom fit in an int64 with three bits to spare. The key is exact, so a
# lookup is an equality test and a neighbour is an integer offset.
VOX_B = 1 << 19
VOX_SX = 1 << 40
VOX_SY = 1 << 20
VOX_SZ = 1


def _pack_grid(k):
    """(N,3) integer voxel indices -> (N,) int64 keys."""
    k = np.clip(k, -VOX_B + 2, VOX_B - 2).astype(np.int64)
    return ((k[:, 0] + VOX_B) * VOX_SX + (k[:, 1] + VOX_B) * VOX_SY
            + (k[:, 2] + VOX_B))


def _pack_points(p):
    """(N,3) metres -> (N,) int64 voxel keys."""
    return _pack_grid(np.floor(np.asarray(p, float) / VOXEL))


def _unpack(keys):
    """(N,) int64 keys -> (N,3) integer voxel indices."""
    keys = np.asarray(keys, np.int64)
    i = keys // VOX_SX
    r = keys - i * VOX_SX
    j = r // VOX_SY
    return np.stack([i - VOX_B, j - VOX_B, r - j * VOX_SY - VOX_B], 1)


def voxelise(V, T):
    """Voxel keys covering every triangle SURFACE at <= VOXEL spacing.

    Two false positives are avoided here, and both were observed before this
    was written this way:

    - Sampling only *vertices* splits a 3 m beam into two lumps, because a beam
      has vertices only at its ends. The far lump then reports as floating.
    - Sampling only *edges* leaves the interior of a large flat face empty, so a
      tankard standing in the middle of a table top connects to nothing and
      reports as floating. Every stall counter and table in the town is that
      case.

    So edges are walked, and interiors are covered by a lattice subdivided
    *per direction* — a 20 m x 2 cm sliver of trim needs 27 samples along its
    length and one across, not 27 x 27. Doing it by longest edge alone cost 11
    seconds on the guild alone.

    Spacing is VOXEL rather than half of it because 26-connectivity is what
    matters: two samples no more than one voxel apart on every axis land in
    voxels that touch, which is all connectivity needs.
    """
    a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    step = VOXEL * 0.75

    # Samples are folded into the deduplicated set as they are produced rather
    # than piled into one list and uniqued at the end. The old code held every
    # sample of every triangle at once — with the quantization bug that was
    # tens of gigabytes and raised numpy's _ArrayMemoryError; even decoded
    # correctly, `landscape` produces ~30 M samples for ~2 M distinct voxels,
    # so paying 15x the memory for the duplicates is pointless.
    acc = [np.zeros(0, np.int64)]
    pending, npend = [], 0

    def flush(force=False):
        nonlocal pending, npend
        if not pending or (npend < 3_000_000 and not force):
            return
        acc[0] = np.unique(np.concatenate([acc[0]] + pending))
        pending, npend = [], 0

    def add(p):
        nonlocal npend
        pending.append(_pack_points(p))
        npend += len(p)
        flush()

    # Edges, so no boundary is missed regardless of how the interior is diced.
    e = np.unique(np.sort(np.concatenate(
        [T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]), axis=1), axis=0)
    ea, eb = V[e[:, 0]], V[e[:, 1]]
    L = np.linalg.norm(eb - ea, axis=1)
    add(ea)
    add(eb)
    k = 1
    while True:
        m = L > k * step
        if not m.any() or k > MAX_EDGE_STEPS:
            break
        t = (k * step / L[m])[:, None]
        add(ea[m] + (eb[m] - ea[m]) * t)
        k += 1

    # Interiors, bucketed by (u, v) subdivision so the lattice is vectorised.
    nu = _pow2(np.ceil(np.linalg.norm(b - a, axis=1) / step))
    nv = _pow2(np.ceil(np.linalg.norm(c - a, axis=1) / step))
    for ku in np.unique(nu):
        for kv in np.unique(nv[nu == ku]):
            if ku == 1 and kv == 1:
                continue                      # the edge pass already covers it
            m = (nu == ku) & (nv == kv)
            ii, jj = np.meshgrid(np.arange(1, ku), np.arange(1, kv), indexing="ij")
            sel = (ii / ku + jj / kv) < 1.0
            if not sel.any():
                continue
            u = (ii[sel] / ku)[None, :, None]
            v = (jj[sel] / kv)[None, :, None]
            am, bm, cm = a[m][:, None, :], b[m][:, None, :], c[m][:, None, :]
            chunk = max(1, int(1_000_000 / max(1, u.shape[1])))
            for s in range(0, am.shape[0], chunk):
                p = (am[s:s + chunk] + (bm[s:s + chunk] - am[s:s + chunk]) * u
                     + (cm[s:s + chunk] - am[s:s + chunk]) * v)
                add(p.reshape(-1, 3))
    flush(force=True)
    return acc[0]                      # sorted, unique, packed int64 keys


def _lookup(vox_sorted, query):
    """Index into `vox_sorted` of each query key, or -1. Both are packed keys."""
    if len(vox_sorted) == 0:
        return np.full(len(query), -1, np.int64)
    pos = np.searchsorted(vox_sorted, query)
    np.clip(pos, 0, len(vox_sorted) - 1, out=pos)
    hit = vox_sorted[pos] == query
    out = np.full(len(query), -1, np.int64)
    out[hit] = pos[hit]
    return out


def connected(vox):
    """26-connected component label per voxel. `vox` is sorted packed keys.

    The neighbour search was always vectorised; the union was not — it walked
    every matched pair in a Python loop with a path-compressing `find` per
    element, then rebuilt the labels with a second Python loop over every
    voxel. On `landscape`'s ~2 M voxels that is tens of millions of interpreted
    iterations. scipy does the same job as one sparse connected-components
    call, and `vox` is already sorted by construction — so no argsort, and a
    neighbour is `key + dx*VOX_SX + dy*VOX_SY + dz` rather than a rehash.
    """
    n = len(vox)
    if n == 0:
        return np.zeros(0, np.int64)
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components

    src, dst = [], []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                if (dx, dy, dz) <= (0, 0, 0):
                    continue
                off = dx * VOX_SX + dy * VOX_SY + dz * VOX_SZ
                j = _lookup(vox, vox + off)
                m = j >= 0
                if m.any():
                    src.append(np.nonzero(m)[0])
                    dst.append(j[m])
    if not src:
        return np.arange(n)
    src = np.concatenate(src)
    dst = np.concatenate(dst)
    g = coo_matrix((np.ones(len(src), np.int8), (src, dst)), shape=(n, n))
    _ncomp, lab = connected_components(g, directed=False)
    return lab.astype(np.int64)


def vertex_components(V, T, vox=None):
    """(component label per vertex, voxel count per label, occupied voxels)."""
    if vox is None:
        vox = voxelise(V, T)
    lab = connected(vox)
    pos = _lookup(vox, _pack_points(V))
    # Every vertex is an edge endpoint, so its voxel is always in the set; the
    # clamp is belt and braces against a degenerate mesh rather than a case.
    vlab = lab[np.maximum(pos, 0)]
    keys, counts = np.unique(lab, return_counts=True)
    return vlab, dict(zip(keys, counts)), vox


def _supported_by(static_vox, lo, hi):
    """Is there other town geometry under (or level with) this world AABB?

    Directive §6.1 allows three ways for a mass to be legitimate: it sits on
    ground, something that reaches the ground carries it, **or it is visibly
    fixed to a wall**. The placement checks only ever knew about the first, and
    each venue was voxelised alone, so anything mounted on a structure reported
    as floating. On the real town that was 63 of 70 failures and every one of
    them was correct construction:

    - the town wall's corbel table and putlog ends — masonry brackets socketed
      into the wall face, instanced, so voxelised without the wall they are set
      into;
    - nineteen window boxes on their iron brackets, authored in `landscape` and
      hung on `townhouse` walls, so the wall carrying them is in another file;
    - the market stalls, which stand on `market_square`'s paved podium.

    So the question is asked against the WHOLE TOWN in world space: is there
    anything at all beneath this mass's footprint within a step of its
    underside. Unarguable in both directions — geometry under a mass is
    support, and none is not — and it is the only form of the question that a
    town assembled from thirty-odd separately-generated files can answer.
    """
    if static_vox is None or len(static_vox) == 0:
        return False
    k0 = np.floor(np.asarray([lo[0], lo[1] - FLOAT_GAP - VOXEL, lo[2]]) / VOXEL)
    k1 = np.floor(np.asarray([hi[0], lo[1] + VOXEL, hi[2]]) / VOXEL)
    span = (k1 - k0 + 1)
    if span.min() < 1 or float(np.prod(span)) > 20000:
        return False                    # too coarse to answer cheaply; stay quiet
    gx, gy, gz = np.meshgrid(np.arange(k0[0], k1[0] + 1),
                             np.arange(k0[1], k1[1] + 1),
                             np.arange(k0[2], k1[2] + 1), indexing="ij")
    q = _pack_grid(np.stack([gx.ravel(), gy.ravel(), gz.ravel()], 1))
    return bool((_lookup(static_vox, q) >= 0).any())


def yaw(V, deg):
    if not deg:
        return V
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    out = V.copy()
    out[:, 0] = V[:, 0] * c + V[:, 2] * s
    out[:, 2] = -V[:, 0] * s + V[:, 2] * c
    return out


def check_placement(name, V, vlab, sizes, placement, H, world_vox=None):
    """Sunk / buried / floating, for one venue at one placement."""
    origin = np.asarray(placement.get("origin", [0, 0, 0]), float)
    W = yaw(V, placement.get("rotationDeg", 0)) + origin
    ground = H(W[:, 0], W[:, 2])
    dy = W[:, 1] - ground
    tag = placement.get("_tag", name)

    worst = int(np.argmin(dy))
    # The terrain venue IS the datum, so "below terrain" is meaningless for it:
    # its own heightfield is the reference, and the parts that legitimately go
    # under are the quay revetment's footing and the step flights' cheeks,
    # which are founded below water on purpose.
    if dy[worst] < -SINK_DEEP and tag not in LANDSCAPE and name not in LANDSCAPE:
        warn(f"{tag}: geometry reaches {-dy[worst]:.2f} m below terrain at "
             f"({W[worst,0]:.1f}, {W[worst,2]:.1f}) — sunk?")

    # Per-mass extremes by segmented reduction rather than one boolean mask per
    # label: `landscape` has 159 masses over ~200 k vertices, and masking the
    # whole array once per label is quadratic in exactly the venue that has the
    # most of both.
    labs, inv = np.unique(vlab, return_inverse=True)
    nl = len(labs)
    top = np.full(nl, -np.inf)
    bot = np.full(nl, np.inf)
    np.maximum.at(top, inv, dy)
    np.minimum.at(bot, inv, dy)
    cnt = np.maximum(np.bincount(inv, minlength=nl), 1)
    cxs = np.bincount(inv, weights=W[:, 0], minlength=nl) / cnt
    czs = np.bincount(inv, weights=W[:, 2], minlength=nl) / cnt
    lo = np.full((nl, 3), np.inf)
    hi = np.full((nl, 3), -np.inf)
    for ax in range(3):
        np.minimum.at(lo[:, ax], inv, W[:, ax])
        np.maximum.at(hi[:, ax], inv, W[:, ax])

    for i, lab in enumerate(labs):
        n = int(sizes.get(lab, 0))
        cx, cz = cxs[i], czs[i]
        if top[i] < -BURIED_EPS:
            err(f"{tag}: an isolated mass ({n} voxels) is entirely below terrain — "
                f"its highest point is {-top[i]:.2f} m down at ({cx:.1f}, {cz:.1f}). "
                f"It renders nothing.")
        elif bot[i] > FLOAT_GAP:
            if _supported_by(world_vox, lo[i], hi[i]):
                continue                   # carried by something else in town
            msg = (f"{tag}: an isolated mass ({n} voxels) floats — nothing under it "
                   f"for {bot[i]:.2f} m at ({cx:.1f}, {cz:.1f}). Directive §6.1: "
                   f"every mass sits on ground, is carried by something that reaches "
                   f"the ground, or is visibly fixed to a wall.")
            (err if n >= FLOAT_MIN_VOX else warn)(msg)


def check_instanced(name, inst, placement, H, static_vox=None):
    """Sunk / floating for EXT_mesh_gpu_instancing batches.

    The base mesh is voxelised ONCE and its components' local bounding boxes
    are then carried through each instance transform, because expanding 10,811
    instances into triangles to answer a question about bounding boxes would
    cost forty times the memory for the same answer. The box form is
    deliberately the conservative one — the ground under a footprint is taken
    at its HIGHEST and the mass at its LOWEST — so an instance only reports as
    floating when it is unarguably in the air.
    """
    origin = np.asarray(placement.get("origin", [0, 0, 0]), float)
    rot = placement.get("rotationDeg", 0)
    tag = placement.get("_tag", name)
    found = {}
    for mi, (Vb, Tb, xforms) in enumerate(inst):
        vlab, sizes, _vx = vertex_components(Vb, Tb)
        # All instances of one batch at once. Walking 9,149 of them in Python,
        # each with its own meshgrid and its own scalar call into
        # `terrain.height`, was 28 seconds on `landscape` alone.
        L = np.stack([x[0] for x in xforms])            # (I,3,3)
        Tr = np.stack([x[1] for x in xforms])           # (I,3)
        for lab in np.unique(vlab):
            m = vlab == lab
            n = int(sizes.get(lab, 0))
            if n < FLOAT_MIN_VOX:
                continue                       # sub-half-m3 shard; not a mass
            lo, hi = Vb[m].min(0), Vb[m].max(0)
            corners = np.array([[x, y, z] for x in (lo[0], hi[0])
                                for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
            # (I,8,3): every corner of every instance, venue-local then world.
            wl = np.einsum("ijk,ck->icj", L, corners) + Tr[:, None, :]
            w = yaw(wl.reshape(-1, 3), rot).reshape(len(L), 8, 3) + origin
            # A mass fixed to a wall is carried by it (Directive §6.1), and the
            # wall may be in another venue's file, so the question is asked of
            # the whole town in world space.
            carried = np.zeros(len(L), bool)
            for i in range(len(L)):
                carried[i] = _supported_by(static_vox, w[i].min(0), w[i].max(0))
            x0, x1 = w[:, :, 0].min(1), w[:, :, 0].max(1)
            z0, z1 = w[:, :, 2].min(1), w[:, :, 2].max(1)
            # A 3x3 ground probe over each footprint, evaluated in one call.
            f = np.array([0.0, 0.5, 1.0])
            gx = (x0[:, None] + (x1 - x0)[:, None] * f[None, :])[:, :, None]
            gz = (z0[:, None] + (z1 - z0)[:, None] * f[None, :])[:, None, :]
            gx, gz = np.broadcast_arrays(gx, gz)
            g = np.asarray(H(gx.ravel(), gz.ravel()), float).reshape(len(L), 9)
            gap = w[:, :, 1].min(1) - g.max(1)
            sunk = g.min(1) - w[:, :, 1].max(1)
            cx, cz = w[:, :, 0].mean(1), w[:, :, 2].mean(1)
            for key, metric in (((mi, int(lab)), gap),
                                ((mi, int(lab), "buried"), sunk)):
                sel = np.nonzero(metric > (FLOAT_GAP if len(key) == 2
                                           else BURIED_EPS))[0]
                if len(key) == 3:
                    sel = sel[gap[sel] <= FLOAT_GAP]     # float beats buried
                else:
                    sel = sel[~carried[sel]]
                if not len(sel):
                    continue
                b = sel[int(np.argmax(metric[sel]))]
                found[key] = [len(sel), float(metric[b]),
                              (float(cx[b]), float(cz[b])), n]
    for key, (count, worst, at, n) in sorted(found.items()):
        buried = len(key) == 3
        verb = ("is entirely below terrain by up to" if buried
                else "floats — nothing under it for up to")
        err(f"{tag}: {count} instance(s) of an instanced mass ({n} voxels) "
            f"{verb} {worst:.2f} m, worst at ({at[0]:.1f}, {at[1]:.1f}). "
            f"Directive §6.1")


def _placements_of(placements, name):
    here = placements.get(name)
    if not here:
        here = [{"origin": [0, 0, 0], "rotationDeg": 0,
                 "_tag": f"{name} (not placed in the town file)"}]
    out = []
    for i, pl in enumerate(here):
        pl = dict(pl)
        pl.setdefault("_tag", name if len(here) == 1 else f"{name}#{i}")
        out.append(pl)
    return out


def check_geometry(paths, town, H, hsrc):
    """Run the placement checks for every venue at every placement it has."""
    print(f"\ngeometry (terrain: {hsrc}):")
    placements = {}
    for v in (town.get("venues", []) if town else []):
        placements.setdefault(v["id"], []).append(v)

    # Pass 1: where the town's static geometry actually IS, in world space.
    # Support is a property of the assembled town, not of one file — see
    # `_supported_by`. Only the packed voxel keys are kept between the passes
    # (a few tens of MB for the whole town); the vertex arrays are released and
    # re-read in pass 2, which costs a fraction of a second and bounds the peak.
    local_vox, world = {}, []
    for p in paths:
        name = os.path.basename(p)[:-5]
        V, T, _inst = load_geometry(p)
        if V is None:
            continue
        vox = voxelise(V, T)
        local_vox[name] = vox
        # Voxel centres carry the mass's footprint through the placement
        # transform without needing the vertices again.
        centres = (_unpack(vox) + 0.5) * VOXEL
        for pl in _placements_of(placements, name):
            w = yaw(centres, pl.get("rotationDeg", 0)) \
                + np.asarray(pl.get("origin", [0, 0, 0]), float)
            world.append(_pack_points(w))
        del V, T, centres
    world_vox = (np.unique(np.concatenate(world)) if world
                 else np.zeros(0, np.int64))
    print(f"  {len(world_vox):,} occupied voxels across the assembled town "
          f"(what 'carried by something' is tested against)")

    checked = 0
    for p in paths:
        name = os.path.basename(p)[:-5]
        V, T, inst = load_geometry(p)
        if V is None and not inst:
            err(f"{name}.gltf: could not read vertex data")
            continue
        vlab, sizes, _v = (vertex_components(V, T, local_vox.get(name))
                           if V is not None
                           else (np.zeros(0, np.int64), {}, None))
        here = _placements_of(placements, name)
        for pl in here:
            if V is not None:
                check_placement(name, V, vlab, sizes, pl, H, world_vox)
            if inst:
                check_instanced(name, inst, pl, H, world_vox)
            checked += 1
        # Distinct vertex labels, not distinct voxel components: a lattice
        # sample with no vertex in it is an artefact of sampling, not a mass.
        del V, T
        ninst = sum(len(x[2]) for x in inst)
        print(f"  {name:24s} {len(np.unique(vlab)):4d} masses  {len(here)} placement(s)"
              + (f"  +{ninst:,} instances" if ninst else ""))
    print(f"  {checked} placements tested for sunk / buried / floating mass")


def check_entity_ground(town, H):
    """An interactable buried in the ground is a broken interaction, not a look."""
    if not town:
        return
    n = 0
    for v in town.get("venues", []):
        p = os.path.join(ENT_DIR, f"{v['id']}.json")
        if not os.path.exists(p):
            continue
        doc = json.load(open(p))
        origin = np.asarray(v.get("origin", [0, 0, 0]), float)
        for e in doc.get("entities", []):
            pos = e.get("transform", {}).get("pos")
            if not pos or len(pos) != 3:
                continue
            w = yaw(np.asarray([pos], float), v.get("rotationDeg", 0))[0] + origin
            g = float(H(np.asarray([w[0]]), np.asarray([w[2]]))[0])
            n += 1
            if w[1] - g < -0.40:
                err(f"entity '{e.get('id')}' sits {g - w[1]:.2f} m below terrain — "
                    f"unreachable", rel(p))
    print(f"  {n} entity positions tested against terrain")


# ---------------------------------------------------------------------------
# Scale sanity against the Art Bible §3 table
# ---------------------------------------------------------------------------
#
# Measuring a door out of a merged triangle soup is not possible; the mesh has
# no idea which of its 74,000 triangles is a door. What IS possible, cheaply and
# exactly, is to read the generators' own named dimensions — which is where a
# scale error is actually introduced — and hold them against the table.

SCALE_RULES = [
    (r"^DOOR_W$|^door_w$",                   (0.95,),  0.05, "Door opening 0.95 m wide"),
    (r"^DOOR_H$|^door_h$",                   (2.10,),  0.05, "Door opening 2.10 m high"),
    (r"^CEIL_H$|^CEILING_H$",                (2.70,),  0.10, "Interior floor-to-ceiling 2.70 m"),
    (r"^FLOOR_H$|^STOREY_H$",                (3.20,),  0.15, "Floor-to-floor 3.20 m"),
    (r"^POST$|^POST_SECTION$",               (0.18,),  0.02, "Timber frame post section 0.18 m"),
    (r"^SILL_H$|^HANDRAIL_H$|^RAIL_H$",      (0.95,),  0.05, "Handrail / sill 0.95 m"),
    (r"^TABLE_H$|^TABLETOP_H$",              (0.74,),  0.03, "Table height 0.74 m"),
    (r"^BENCH_H$|^SEAT_H$|^STOOL_H$",        (0.45,),  0.04, "Bench seat height 0.45 m"),
    (r"^COUNTER_H$|^BAR_H$",           (1.05, 0.90),  0.05, "Counter/bar 1.05 m, market stall counter 0.90 m"),
    (r"^AWNING_CLEAR$|^AWNING_H$",           (2.20,),  0.10, "Stall awning clearance 2.20 m"),
    (r"^STEP_RISE$|^RISE$",                 (0.175,), 0.015, "Step rise 0.175 m"),
    (r"^STEP_GOING$|^GOING$|^TREAD$",        (0.28,),  0.02, "Step going 0.28 m"),
    (r"^EYE_H$|^EYE_HEIGHT$",                (1.62,),  0.02, "Player eye height 1.62 m"),
    (r"^PLAYER_H$|^CHAR_H$",                 (1.75,),  0.02, "Player character height 1.75 m"),
    (r"^BARREL_H$",                          (0.88,),  0.03, "Barrel height 0.88 m"),
    (r"^CRATE$|^CRATE_SIZE$",                (0.55,),  0.03, "Crate 0.55 m cube"),
    (r"^WHEEL_DIA$|^CART_WHEEL$",            (1.15,),  0.05, "Cart wheel 1.15 m diameter"),
    # Art Bible §6 chamfer table — same failure mode, same cheap test.
    (r"^CHAMFER_ARCH$|^CH_ARCH$",           (0.015,), 0.002, "Architectural chamfer 15 mm"),
    (r"^CHAMFER_PROP$|^CH_PROP$",           (0.008,), 0.002, "Prop chamfer 8 mm"),
    (r"^CH_SMALL$|^CHAMFER_SMALL$",         (0.003,), 0.001, "Small metal chamfer 3 mm"),
]

# Function-default dimensions, keyed `function.argument`.
DEFAULT_RULES = [
    (r"^bench\.height$",                     (0.45,),  0.04, "Bench seat height 0.45 m"),
    (r"^table\.height$",                     (0.74,),  0.03, "Table height 0.74 m"),
    (r"^(plank_door|door_frame)\.height$",   (2.10,),  0.05, "Door opening 2.10 m high"),
    (r"^(plank_door|door_frame)\.width$",    (0.95,),  0.05, "Door opening 0.95 m wide"),
    (r"^barrel\.height$",                    (0.88,),  0.03, "Barrel height 0.88 m"),
    (r"^crate\.size$",                       (0.55,),  0.03, "Crate 0.55 m cube"),
]


def _num(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) \
            and not isinstance(node.value, bool):
        return float(node.value)
    return None


def _match(rules, key, value, where, tested):
    for pat, expected, tol, label in rules:
        if not re.match(pat, key):
            continue
        tested.append(key)
        if not any(abs(value - e) <= tol for e in expected):
            want = " or ".join(f"{e:g}" for e in expected)
            err(f"{key} = {value:g} m, Art Bible §3 says {want} m ({label})", where)
        return


def check_scale():
    print("\nscale (Art Bible §3 named dimensions):")
    tested = []
    files = sorted(glob.glob(os.path.join(ASSETGEN, "**", "*.py"), recursive=True))
    for f in files:
        if "__pycache__" in f:
            continue
        try:
            tree = ast.parse(open(f, encoding="utf-8").read(), filename=f)
        except SyntaxError as e:
            err(f"cannot parse: {e.msg}", f"{rel(f)}:{e.lineno}")
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            where = f"{rel(f)}:{node.lineno}"
            if isinstance(node, ast.Assign):
                for tgt in node.targets:
                    # `DOOR_W, DOOR_H = 0.95, 2.10`
                    if isinstance(tgt, ast.Tuple) and isinstance(node.value, ast.Tuple):
                        for t, v in zip(tgt.elts, node.value.elts):
                            n = _num(v)
                            if isinstance(t, ast.Name) and n is not None:
                                _match(SCALE_RULES, t.id, n, where, tested)
                    elif isinstance(tgt, ast.Name):
                        n = _num(node.value)
                        if n is not None:
                            _match(SCALE_RULES, tgt.id, n, where, tested)
            else:
                args = node.args
                pairs = list(zip(args.args[len(args.args) - len(args.defaults):],
                                 args.defaults))
                pairs += list(zip(args.kwonlyargs, args.kw_defaults))
                for a, d in pairs:
                    n = _num(d) if d is not None else None
                    if n is not None:
                        _match(DEFAULT_RULES, f"{node.name}.{a.arg}", n, where, tested)
    print(f"  {len(tested)} named dimensions checked "
          f"({', '.join(sorted(set(tested))[:8])}{'…' if len(set(tested)) > 8 else ''})")
    if not tested:
        warn("the scale check matched nothing — either the generators renamed "
             "their dimension constants or SCALE_RULES has rotted", rel(__file__))


def check_street_widths(town):
    """Art Bible §3: main street 7.0 m, side alley 2.5 m."""
    if not town:
        return
    widths = []
    for s in town.get("streets", []):
        w = s.get("width")
        if w is None:
            warn(f"street '{s.get('id')}' declares no width", rel(TOWN_PATH))
            continue
        widths.append(w)
        if w < 2.5:
            err(f"street '{s.get('id')}' is {w:g} m wide; Art Bible §3 floors a "
                f"side alley at 2.5 m", rel(TOWN_PATH))
        elif w > 12.0:
            warn(f"street '{s.get('id')}' is {w:g} m wide — that is a square, "
                 f"not a street (§3 main street is 7.0 m)", rel(TOWN_PATH))
    if widths and not any(abs(w - 7.0) <= 0.25 for w in widths):
        warn(f"no street is 7.0 m wide; §3 says the main artery is. Widest is "
             f"{max(widths):g} m", rel(TOWN_PATH))
    print(f"  {len(widths)} street widths checked")


# ---------------------------------------------------------------------------
# Palette conformance of generated albedo maps (Art Bible §4)
# ---------------------------------------------------------------------------
#
# The metric compares each pixel to the nearest locked palette colour in CIELAB,
# and it is deliberately asymmetric:
#
#   - hue error counts in full. A hue with no palette family is drift.
#   - chroma BELOW the palette costs nothing. Sun-fade, dust and wear all
#     desaturate, and Art Bible §5 requires that wear.
#   - chroma ABOVE the palette counts in full. §1 lists "candy-bright" under
#     "Not this", and over-saturation is the way procedural texturing gets there.
#   - lightness is discounted to a quarter. Every builder darkens and lightens
#     to make a surface read; that is not a palette question.
#
# Measured on the shipped library, everything authored from a palette constant
# lands under 4.6, and everything over 5.0 is a material authored from a hex
# literal that is not in §4. That is where the thresholds come from.

PALETTE_WARN = 5.0
PALETTE_FAIL = 9.0

# Materials whose Art Bible §4 family does not exist, so measuring them against
# it says more about the checker than the material. Each of these is a row §4
# should arguably grow; until it does, silence beats a permanent false positive.
PALETTE_WAIVED = {
    "thatch": "§4 has no thatch row (roof table lists terracotta and slate only)",
    "thatch_new": "§4 has no thatch row",
    "thatch_old": "§4 has no thatch row",
    "glass": "§4 has no leaded-glass row",
    "glass_lit": "§4 has no leaded-glass row",
    "stained": "§4 has no stained-glass row; the window IS six accent dyes at once",
    "stained_dark": "§4 has no stained-glass row",
    "coal": "forge embers span iron to iron_hot; a single-colour family is wrong",
    # Two-family transitions, waived on exactly the argument `coal` is waived
    # on. Copper going to verdigris and bronze going to patina are materials
    # whose SUBJECT is the journey between two §4 rows — BRONZE and VERDIGRIS —
    # and every pixel in the middle is legitimately between families. The
    # metric measures distance to the nearest single colour, so it cannot score
    # a gradient between two of them, and forcing the number down would mean
    # deleting the transition, which is the material.
    "copper": "verdigris run: the subject is the BRONZE->VERDIGRIS transition",
    "bronze": "cast bell patina: same BRONZE->VERDIGRIS transition",
}


def _lab(rgb):
    c = np.asarray(rgb, float)
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    m = np.array([[0.4124, 0.3576, 0.1805],
                  [0.2126, 0.7152, 0.0722],
                  [0.0193, 0.1192, 0.9505]])
    xyz = lin @ m.T / np.array([0.95047, 1.0, 1.08883])
    d = 6 / 29
    f = np.where(xyz > d ** 3, np.cbrt(xyz), xyz / (3 * d * d) + 4 / 29)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]),
                     200 * (f[..., 1] - f[..., 2])], -1)


def _hex_rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])


def check_texel_density():
    """Art Bible §5's density table is a §8 done-criterion, so measure it.

    Two independent things are checked and they fail differently:

    - **Declared** density, `size / coverage` from the material registry. This
      is what the material was authored to be, and getting it wrong is a
      decision error.
    - **Actual** file size on disk against that declaration. This catches a
      texture built before a registry change and never regenerated, which is
      otherwise invisible — the build skips existing PNGs by design.
    """
    if ASSETGEN not in sys.path:
        sys.path.insert(0, ASSETGEN)
    try:
        from core import materials as M
    except Exception as e:
        warn(f"cannot import core/materials.py, so §5 density is unchecked: {e}")
        return
    try:
        from PIL import Image
    except ImportError:
        return
    print("\ntexel density (Art Bible §5):")
    rows = M.density_audit()
    for key, size, cov, got, kls, want, verdict in rows:
        where = f"tools/assetgen/core/materials.py (LIBRARY['{key}'])"
        if verdict != "ok":
            err(f"'{key}' is {got:.0f} px/m; class '{kls}' is {want:.0f} px/m "
                f"(§5). Its {size} px map covers {cov:g} m.", where)
        p = os.path.join(TEX_DIR, f"{key}_albedo.png")
        if not os.path.exists(p):
            err(f"material '{key}' has no albedo on disk — run "
                f"python tools/assetgen/build.py --textures-only", where)
            continue
        w, _h = Image.open(p).size
        if w != size:
            err(f"'{key}' is {w} px on disk but its registry entry says {size} px "
                f"— stale texture. The build skips existing PNGs; use "
                f"--force-textures.", rel(p))
    print(f"  {len(rows)} sets against 3 density classes "
          f"(hero {M.DENSITY['hero']:.0f} / standard {M.DENSITY['standard']:.0f} / "
          f"large {M.DENSITY['large']:.0f} px/m), declared and on disk")


def check_uv_density():
    """What the MESH samples, not what the material declares. See D-050.

    `check_texel_density` above checks the registry against itself and against
    the PNG on disk. Neither can see the number that decides what the player
    looks at: how many world metres one tile of that texture is stretched over
    when it reaches the mesh.

    `core/mesh.py:resolve_uv` now makes a bare `uv_scale=` literal raise, which
    closed 421 call sites. It cannot see the five places that lay UVs by hand —
    `streets._Paving`, `landscape._surface_patch`, `market_square._paving`,
    `roof._uv_scale`, `vegetation` — and between them those are most of the
    ground and roof pixels in a street-level frame. A literal `* 0.5` in one of
    them is invisible to every other instrument in this file, and it is the
    defect `ad-town-03` §1 and `ad-town-04` §2 both rejected on.

    So this measures the shipped glTF: world area over UV area, per material,
    area-weighted. Atlas keys are exempt and the reason is in `tools/uv_density.py`.
    """
    try:
        sys.path.insert(0, os.path.join(REPO, "tools"))
        import uv_density
    except Exception as e:
        warn(f"cannot import tools/uv_density.py, so shipped UV scale is "
             f"unchecked: {e}")
        return
    print("\nuv density — what the mesh samples (D-050):")
    try:
        fails, warns = uv_density.audit()
    except Exception as e:
        warn(f"uv density audit failed to run: {e}")
        return
    for key, area, cov, mpt, ratio in fails:
        err(f"'{key}' ships at {mpt:.2f} m per tile over {area:.0f} m2 of the "
            f"town, against {cov:g} m authored — {ratio:.2f}x. The pattern is "
            f"landing at {ratio:.1f} times life size. Find the hand-laid UV "
            f"and route it through MATS.uv_scale({key!r}).",
            "tools/uv_density.py")
    for key, area, cov, mpt, ratio in warns:
        warn(f"'{key}' ships at {mpt:.2f} m per tile ({ratio:.2f}x authored) "
             f"over {area:.0f} m2. Over half a stop of texel density.",
             "tools/uv_density.py")


def check_palette():
    try:
        from PIL import Image
    except ImportError:
        warn("Pillow not installed — palette conformance not checked")
        return
    if ASSETGEN not in sys.path:
        sys.path.insert(0, ASSETGEN)
    try:
        from core import palette as P
    except Exception as e:
        err(f"cannot import core/palette.py, so §4 has no single source: {e}")
        return

    names = [n for n in dir(P) if n.isupper()
             and isinstance(getattr(P, n), str) and getattr(P, n).startswith("#")]
    if not names:
        err("core/palette.py exposes no hex constants", "tools/assetgen/core/palette.py")
        return
    # The §4 references are measured through the SAME exposure mapping the
    # textures are written through, or the checker compares an appearance
    # target against a reflectance and every light material reads as drift.
    # `expose` preserves hue and chroma exactly and only moves value, which is
    # the axis this metric already discounts to a quarter — so the effect on
    # the numbers is small and the comparison is finally like-for-like.
    try:
        from core import materials as _MAT
        refs = np.array([_MAT.P.linear_to_srgb(_MAT.reflectance(getattr(P, n)))
                         for n in names])
    except Exception:
        refs = np.array([_hex_rgb(getattr(P, n)) for n in names])
    plab = _lab(refs)
    pc = np.hypot(plab[:, 1], plab[:, 2])

    # Atlas pages are mosaics of a dozen unrelated materials, so "the nearest
    # single §4 family to this image" is not a question that has an answer for
    # them — `kit_trim` holds lead, brick, brass, moss and three paints and
    # measured 5.7 against IRON, which says nothing about any of them. Every
    # material packed into a page is already measured on its own, so scoring
    # the page as well can only produce a false positive that never goes away.
    try:
        from core import atlas as ATL
        pages = set(ATL.ATLASES)
    except Exception:
        pages = set()

    print("\npalette (Art Bible §4):")
    worst = []
    for a in sorted(glob.glob(os.path.join(TEX_DIR, "*_albedo.png"))):
        key = os.path.basename(a)[: -len("_albedo.png")]
        if key in pages:
            continue
        px = (np.asarray(Image.open(a).convert("RGB").resize((48, 48), Image.BOX),
                         float) / 255.0).reshape(-1, 3)
        lab = _lab(px)
        dl = (lab[:, None, 0] - plab[None, :, 0]) * 0.25
        da = lab[:, None, 1] - plab[None, :, 1]
        db = lab[:, None, 2] - plab[None, :, 2]
        dc = np.hypot(lab[:, 1], lab[:, 2])[:, None] - pc[None, :]
        over = np.maximum(0.0, dc - 2.0)
        dh2 = np.maximum(0.0, da * da + db * db - dc * dc)
        d = np.sqrt(dl * dl + over * over + dh2)
        near = d.argmin(1)
        dmin = d.min(1)
        p90 = float(np.percentile(dmin, 90))
        family = names[int(np.bincount(near, minlength=len(names)).argmax())]
        worst.append((p90, key, family))

        if key in PALETTE_WAIVED:
            continue
        where = rel(os.path.join(TEX_DIR, os.path.basename(a)))
        if p90 > PALETTE_FAIL:
            err(f"albedo '{key}' is off-palette (90th-percentile distance {p90:.1f}, "
                f"nearest family {family}). §4: deviation requires a recorded "
                f"decision in docs/DECISIONS.md", where)
        elif p90 > PALETTE_WARN:
            warn(f"albedo '{key}' drifts from §4 (90th-percentile distance {p90:.1f}, "
                 f"nearest family {family}) — authored from a hex literal rather "
                 f"than a palette constant?", where)
    worst.sort(reverse=True)
    print(f"  {len(worst)} albedo maps against {len(names)} locked colours; "
          f"worst: " + ", ".join(f"{k} {d:.1f}" for d, k, _ in worst[:4]))


# ---------------------------------------------------------------------------
# Anachronisms (Art Bible §2)
# ---------------------------------------------------------------------------
#
# A naive grep for these words over the generators returns ~35 hits and every
# single one is a false positive: "bolt" is a bolt of cloth, "extruded" is a
# modelling verb, and most mentions of "screw" are the Art Bible forbidding it.
# So terms with a legitimate modelling sense are excluded outright, and any line
# that negates or cites the rule is suppressed.

ANACHRONISMS = [
    (r"\bscrews?\b|\bscrewed\b|\bscrewing\b", "screws — §2 permits nails, pegs, rivets"),
    (r"\bplate[ _-]?glass\b|\bsheet[ _-]?glass\b", "plate glass — small blown panes only"),
    (r"\bstencil\w*", "stencil-repeated text"),
    (r"\bplastics?\b|\bacrylic\b|\bpvc\b|\bvinyl\b", "plastic"),
    (r"\brubber\b|\bneoprene\b", "rubber"),
    (r"\bmachined\b|\bmilled steel\b|\bextrusion die\b", "machined metal"),
    (r"\bcoil spring|\bleaf spring|\bspring steel\b", "springs"),
    (r"\bwire rope\b|\bsteel cable\b|\bchain[ -]?link\b", "wire rope / machine chain"),
    (r"\blettering\b|\btypeface\b|\bImageFont\b|\bdraw\.text\b|\brender_text\b|"
     r"\bfont_?\w*\s*=", "readable lettering — signage is pictorial"),
    # "printed" alone is a modelling verb here — a texture generator PRINTS a
    # tile grid, a UV scale is what a prism's ends are printed at — and it fired
    # on four such comments in core/. The forbidden class is printed TEXT, so
    # say that, exactly as "bolt" and "extruded" are excluded above.
    (r"\bprinted (?:text|type|lettering|label|sign|word)|\bstamped text\b",
     "printed text"),
    (r"\bconcrete\b|\bcinder ?block\b|\brebar\b", "concrete"),
    (r"\baluminium\b|\baluminum\b|\bchrome\b|\bstainless\b", "modern alloy"),
    (r"\bpistons?\b|\bturbines?\b|\bmotors?\b|\bbatter(y|ies)\b|\belectric\w*",
     "industrial power"),
]

# A line that forbids, negates, or contrasts with the term is a compliance note.
ANACHRONISM_OK = re.compile(
    r"\bno\b|\bnot\b|\bnever\b|\bnone\b|\bwithout\b|\bavoid\w*|\bforbid\w*|\bban\w*|"
    r"\binstead\b|\brather than\b|\bunlike\b|\bfree of\b|\bpredates?\b|"
    r"\bseparates?\b|\breads? (as|like)\b|\blooks? like\b|\bwould\b|"
    r"art bible|§\d|anachronis\w*|#\s*anachronism-ok", re.I)


def check_anachronisms():
    print("\nanachronisms (Art Bible §2):")
    files = [f for f in sorted(glob.glob(os.path.join(ASSETGEN, "**", "*.py"),
                                         recursive=True))
             if "__pycache__" not in f]
    lines = 0
    for f in files:
        src = open(f, encoding="utf-8").read().splitlines()
        for i, line in enumerate(src, 1):
            lines += 1
            # The suppression reads the surrounding lines, not just this one. A
            # comment is a paragraph: `warehouse.py:211` says "readable
            # lettering, so the account is notches on hazel" and the clause that
            # makes it a compliance note — "Art Bible §2: no" — is on the line
            # above. Both of the town's `lettering` failures were that, and a
            # line-at-a-time regex cannot ever see it.
            window = " ".join(src[max(0, i - 2):i + 1])
            for pat, why in ANACHRONISMS:
                if re.search(pat, line, re.I) and not ANACHRONISM_OK.search(window):
                    err(f"{why}: {line.strip()[:90]}", f"{rel(f)}:{i}")
                    break
    print(f"  {lines:,} lines of generator source over {len(files)} files, "
          f"{len(ANACHRONISMS)} forbidden classes "
          f"(suppress a false positive with '# anachronism-ok: reason')")


# ---------------------------------------------------------------------------
# The original mechanical checks
# ---------------------------------------------------------------------------

def mesh_bounds(doc):
    """The asset's real venue-local AABB, in metres. `(lo, hi)`, or `(None, None)`.

    Not the union of the accessors' `min`/`max`. Two things make that wrong, and
    both were live:

    1. **Positions are quantized.** D-042 turned on `KHR_mesh_quantization`, so
       POSITION is a *normalized* SHORT and its accessor `min`/`max` are in
       [-32767, 32767] with the metres carried by the node's `scale` and
       `translation`. Reading them raw measured every asset in the build at
       65534 x 65534 x 65534 m, which tripped the `MAX_VENUE_HEIGHT` error on
       all fifteen non-terrain meshes — fifteen false scale errors on a clean
       build, which is the fastest way to teach everyone to ignore validate.
    2. **It summed every VEC3 accessor**, so NORMAL and TANGENT — unit vectors,
       nothing to do with size — were folded into the footprint.

    `core/venue.py` already writes the true bounds per node as
    `extras.hm.min/max` (that is what the batching manifest is), so use them and
    only fall back to de-quantizing when a mesh predates the manifest.
    """
    lo = [1e9] * 3
    hi = [-1e9] * 3
    seen = False
    for nd in doc.get("nodes", []):
        hm = (nd.get("extras") or {}).get("hm") or {}
        mn, mx = hm.get("min"), hm.get("max")
        if mn is None or mx is None:
            continue
        seen = True
        for i in range(3):
            lo[i] = min(lo[i], float(mn[i]))
            hi[i] = max(hi[i], float(mx[i]))
    if seen:
        return lo, hi

    # Fallback: de-quantize POSITION through its node's TRS. Only POSITION —
    # never every VEC3 accessor.
    accs = doc.get("accessors", [])
    for nd in doc.get("nodes", []):
        if "mesh" not in nd:
            continue
        s = nd.get("scale", [1.0, 1.0, 1.0])
        t = nd.get("translation", [0.0, 0.0, 0.0])
        for prim in doc.get("meshes", [])[nd["mesh"]].get("primitives", []):
            ai = prim.get("attributes", {}).get("POSITION")
            if ai is None:
                continue
            acc = accs[ai]
            mn, mx = acc.get("min"), acc.get("max")
            if mn is None or mx is None:
                continue
            # A normalized SHORT/BYTE accessor stores v / MAXVAL; glTF says the
            # decode is max(v / MAXVAL, -1.0).
            div = {5122: 32767.0, 5120: 127.0}.get(acc.get("componentType"), 1.0) \
                if acc.get("normalized") else 1.0
            seen = True
            for i in range(3):
                a = max(mn[i] / div, -1.0) * s[i] + t[i]
                b = max(mx[i] / div, -1.0) * s[i] + t[i]
                lo[i] = min(lo[i], a, b)
                hi[i] = max(hi[i], a, b)
    return (lo, hi) if seen else (None, None)


def check_gltf(path):
    name = os.path.basename(path)
    with open(path) as f:
        doc = json.load(f)

    if doc.get("asset", {}).get("version") != "2.0":
        err(f"{name}: not glTF 2.0")

    lo, hi = mesh_bounds(doc)
    if lo is None:
        err(f"{name}: no positional data")
        return

    span_x, span_y, span_z = (hi[i] - lo[i] for i in range(3))
    # Height is measured from the venue datum UP, not as the bounding box's
    # vertical span. Every building in Hearthmere reaches below its datum on
    # purpose — Directive §6.1 makes a generator carry its plinth into the
    # ground so nothing floats on falling ground — and counting buried
    # foundation as building height is a category error, not a scale check.
    # It cost the church a FAIL at 22.30 m when the church is 21.95 m tall and
    # 0.35 m of it is underground.
    above = hi[1] if hi[1] > 0.0 else span_y
    if max(span_x, span_z) > MAX_VENUE_SPAN and name not in TOWN_WIDE:
        warn(f"{name}: footprint {span_x:.1f}x{span_z:.1f}m exceeds {MAX_VENUE_SPAN}m")
    if above > MAX_VENUE_HEIGHT and name not in LANDSCAPE:
        err(f"{name}: stands {above:.1f}m above its datum, over {MAX_VENUE_HEIGHT}m "
            f"— scale error?")
    if span_y < MIN_VENUE_HEIGHT:
        err(f"{name}: height {span_y:.2f}m — geometry probably failed to build")

    # Every material must carry a full PBR set (Art Bible §5).
    images = {im.get("uri", "") for im in doc.get("images", [])}
    for mat in doc.get("materials", []):
        mn = mat.get("name", "?")
        pbr = mat.get("pbrMetallicRoughness", {})
        if "baseColorTexture" not in pbr:
            err(f"{name}: material '{mn}' has no albedo texture (flat colour is rejected)")
        if "metallicRoughnessTexture" not in pbr:
            err(f"{name}: material '{mn}' has no ORM texture")
        if "normalTexture" not in mat:
            warn(f"{name}: material '{mn}' has no normal map")

    for uri in images:
        p = os.path.normpath(os.path.join(MESH_DIR, uri))
        if not os.path.exists(p):
            err(f"{name}: missing texture {uri}")

    tris = sum(
        doc["accessors"][p["indices"]]["count"] // 3
        for m in doc.get("meshes", []) for p in m.get("primitives", [])
        if "indices" in p
    )
    # A draw call is one PRIMITIVE, not one material. glTF splits a mesh per
    # material, but a generator that emits an object per prop produces one
    # primitive per prop even when they all share a material — `streets` shipped
    # 1,368 primitives across 7 materials. Counting materials under-reported the
    # town's real cost by ~8x and made the §7 budget check unable to fire.
    prims = sum(len(m.get("primitives", [])) for m in doc.get("meshes", []))

    # The batching manifest core/venue.py writes (Directive §7). Its absence is
    # not an error — a mesh may predate it — but everything downstream that can
    # attribute cost per cell depends on it, so say when it is missing.
    hm = (doc.get("extras") or {}).get("hm")
    if hm is None:
        warn(f"{name}: no batching manifest — rebuild with tools/assetgen/build.py")
    else:
        # Scene roots must be LOD0 ONLY. If an MSFT_lod alternate leaks into the
        # scene, every consumer draws all four levels stacked, which looks almost
        # right and costs four times the budget. Cheap to check, catastrophic to
        # miss.
        alts = set()
        for nd in doc.get("nodes", []):
            alts.update(nd.get("extensions", {}).get("MSFT_lod", {}).get("ids", []))
        leaked = [i for i in doc.get("scenes", [{}])[0].get("nodes", []) if i in alts]
        if leaked:
            err(f"{name}: {len(leaked)} MSFT_lod alternate(s) are scene roots — "
                f"every LOD level will be drawn at once")
        # A heavy batch with no LOD chain costs full price at every distance.
        # Skipped for a venue that opted out on purpose — `terrain` carries its
        # own concentric rings — because that is a decision, not an oversight.
        if hm.get("lod", True):
            for nd in doc.get("nodes", []):
                ex = (nd.get("extras") or {}).get("hm", {})
                if ex.get("lod") == 0 and "MSFT_lod" not in nd.get("extensions", {}) \
                        and ex.get("tris", 0) > 20000:
                    warn(f"{name}: batch '{nd.get('name')}' is {ex['tris']:,} "
                         f"triangles with no LOD chain")

    return {"name": name, "tris": tris, "span": (span_x, span_y, span_z),
            "materials": len(doc.get("materials", [])), "primitives": prims,
            "hm": hm,
            "instancedNodes": sum(1 for nd in doc.get("nodes", [])
                                  if "EXT_mesh_gpu_instancing" in nd.get("extensions", {}))}


def check_entities(path):
    name = os.path.basename(path)
    doc = json.load(open(path))
    seen = set()
    for e in doc.get("entities", []):
        eid = e.get("id", "")
        if not ID_RE.match(eid):
            err(f"malformed entity id '{eid}' (expected hm.<venue>.<kind>.<nn>)", rel(path))
        if eid in seen:
            err(f"duplicate entity id '{eid}' — IDs are never reused", rel(path))
        seen.add(eid)
        if "archetype" not in e:
            err(f"entity '{eid}' has no archetype", rel(path))
        t = e.get("transform", {})
        if len(t.get("pos", [])) != 3:
            err(f"entity '{eid}' has no valid position", rel(path))
        v = e.get("components", {}).get("vendor")
        if v:
            for line in v.get("stock", []):
                if line.get("price", -1) < 0:
                    err(f"entity '{eid}' has negative price for {line.get('item')}", rel(path))
    return len(doc.get("entities", []))


def check_textures():
    albedos = glob.glob(os.path.join(TEX_DIR, "*_albedo.png"))
    if not albedos:
        err("no textures generated — run: python tools/assetgen/build.py --textures-only")
    for a in albedos:
        key = os.path.basename(a)[: -len("_albedo.png")]
        for ch in ("orm", "normal"):
            p = os.path.join(TEX_DIR, f"{key}_{ch}.png")
            if not os.path.exists(p):
                err(f"texture set '{key}' missing {ch} channel")
    return len(albedos)



def check_mesh_bytes():
    """Directive §7's missing row: how many bytes of geometry the town is.

    Counted from the .bin files, which is what a client downloads and what the
    GPU holds after upload — the .gltf JSON is parsed and discarded, so it is
    reported but not budgeted.
    """
    print("\nmesh memory (Directive §7):")
    bins = sorted(glob.glob(os.path.join(MESH_DIR, "*.bin")))
    if not bins:
        return
    total = 0
    worst = []
    for b in bins:
        n = os.path.getsize(b)
        total += n
        worst.append((n, os.path.basename(b)))
        if n > MESH_FILE_BUDGET:
            err(f"{os.path.basename(b)} is {n / 1048576:.1f} MB, over the "
                f"{MESH_FILE_BUDGET / 1048576:.0f} MB per-file budget. Split the "
                f"venue by cell, or see core/gltf.py for the remaining "
                f"compression levers.", rel(b))
    worst.sort(reverse=True)
    js = sum(os.path.getsize(p) for p in glob.glob(os.path.join(MESH_DIR, "*.gltf")))
    print(f"  {total / 1048576:.1f} MB of geometry across {len(bins)} files "
          f"(+{js / 1048576:.1f} MB of glTF JSON); largest: " +
          ", ".join(f"{n} {v / 1048576:.0f} MB" for v, n in worst[:3]))
    if total > MESH_BYTES_BUDGET:
        err(f"§7 mesh memory: {total / 1048576:.1f} MB exceeds the "
            f"{MESH_BYTES_BUDGET / 1048576:.0f} MB budget")
    elif total > MESH_BYTES_BUDGET * 0.85:
        warn(f"§7 mesh memory: {total / 1048576:.1f} MB, over 85% of the "
             f"{MESH_BYTES_BUDGET / 1048576:.0f} MB budget")

    # Quantization is the reason the number is what it is, so notice if a
    # rebuild silently drops it.
    plain = [os.path.basename(g) for g in glob.glob(os.path.join(MESH_DIR, "*.gltf"))
             if "KHR_mesh_quantization" not in
             (json.load(open(g)).get("extensionsUsed") or [])]
    if plain:
        warn(f"{len(plain)} mesh file(s) are not quantized ({', '.join(plain[:3])}"
             f"{'...' if len(plain) > 3 else ''}) — they cost roughly 1.8x their "
             f"quantized size", "tools/assetgen/core/gltf.py")
    check_quantization_contract()


def check_quantization_contract():
    """A quantized accessor must never be readable as if it were not.

    This exists because of a specific, expensive failure and to make its whole
    CLASS impossible rather than to fix the one instance. D-042 turned POSITION
    into a normalized SHORT whose metres ride on the node's TRS; `mesh_bounds`
    kept summing the raw accessor `min`/`max`, and validate reported every mesh
    in the build as 65,534 m across — fifteen false scale errors on a clean
    town, which is how a project learns to ignore its own validator.

    D-052 quantizes TEXCOORD_0 the same way, with the dequantizing scale on the
    material's `KHR_texture_transform` instead of on a node. The equivalent
    silent failure is a file that quantizes UVs and does NOT carry the
    transform: every texture then samples at 1/S of its authored tiling, which
    looks like a material bug, not a pipeline bug, and no existing check would
    say a word.

    So: for each mesh file, every quantized accessor must have its dequantizing
    partner declared, and the file must REQUIRE the extension that defines it.
    A consumer — including this repository's own tooling — then cannot read one
    without the other and get a plausible wrong answer.
    """
    n_ok = 0
    for g in sorted(glob.glob(os.path.join(MESH_DIR, "*.gltf"))):
        doc = json.load(open(g))
        used = set(doc.get("extensionsUsed") or [])
        req = set(doc.get("extensionsRequired") or [])
        accs = doc.get("accessors", [])
        name = os.path.basename(g)

        def quantized(ai):
            a = accs[ai]
            return bool(a.get("normalized")) and a.get("componentType") in (5120, 5121, 5122, 5123)

        q_pos, q_uv = False, False
        for mesh in doc.get("meshes", []):
            for prim in mesh.get("primitives", []):
                at = prim.get("attributes", {})
                if "POSITION" in at and quantized(at["POSITION"]):
                    q_pos = True
                if "TEXCOORD_0" in at and quantized(at["TEXCOORD_0"]):
                    q_uv = True

        if (q_pos or q_uv) and "KHR_mesh_quantization" not in req:
            err(f"{name} has quantized vertex attributes but does not list "
                f"KHR_mesh_quantization in extensionsRequired — a loader without it "
                f"reads the raw integers as metres", rel(g))

        if q_pos:
            # The metres must be recoverable WITHOUT de-quantizing by hand:
            # core/venue.py writes the true AABB to extras.hm.min/max, and every
            # tool is supposed to read that. If it is missing, the next tool to
            # want a size will reach for accessor min/max and the 65,534 m bug
            # comes straight back.
            missing = [nd.get("name", "?") for nd in doc.get("nodes", [])
                       if "mesh" in nd and
                       not ((nd.get("extras") or {}).get("hm") or {}).get("min")]
            if missing:
                err(f"{name}: {len(missing)} mesh node(s) carry quantized POSITION with no "
                    f"extras.hm.min/max ({', '.join(missing[:3])}) — nothing can read this "
                    f"asset's size without re-deriving the dequantization by hand, which is "
                    f"exactly how D-042 produced fifteen false 65,534 m scale errors",
                    rel(g))

        if q_uv:
            if "KHR_texture_transform" not in req:
                err(f"{name} quantizes TEXCOORD_0 but does not REQUIRE "
                    f"KHR_texture_transform — every texture in it would sample at the "
                    f"wrong tiling in any loader that skips the extension", rel(g))
            bad = []
            for mi, mat in enumerate(doc.get("materials", [])):
                pbr = mat.get("pbrMetallicRoughness", {})
                for holder, slots in ((pbr, ("baseColorTexture", "metallicRoughnessTexture")),
                                      (mat, ("normalTexture", "occlusionTexture",
                                             "emissiveTexture"))):
                    for slot in slots:
                        ti = holder.get(slot)
                        if isinstance(ti, dict) and \
                           "KHR_texture_transform" not in (ti.get("extensions") or {}):
                            bad.append(f"{mat.get('name', mi)}.{slot}")
            if bad:
                err(f"{name}: {len(bad)} texture slot(s) sample quantized UVs with no "
                    f"KHR_texture_transform ({', '.join(bad[:3])}) — they will tile "
                    f"{1}/S of the authored rate", rel(g))
            # One scale for the whole file is the invariant that keeps materials
            # shareable. Two would mean a primitive is being dequantized by the
            # wrong number somewhere.
            scales = set()
            for mat in doc.get("materials", []):
                pbr = mat.get("pbrMetallicRoughness", {})
                for holder in (pbr, mat):
                    for ti in holder.values():
                        if isinstance(ti, dict):
                            xf = (ti.get("extensions") or {}).get("KHR_texture_transform")
                            if xf and "scale" in xf:
                                scales.add(tuple(round(float(x), 6) for x in xf["scale"]))
            if len(scales) > 1:
                err(f"{name} carries {len(scales)} different KHR_texture_transform scales "
                    f"{sorted(scales)[:3]} — the UV dequantization must be one number per "
                    f"file or a shared material dequantizes some primitive wrongly", rel(g))
        n_ok += 1
    if n_ok:
        print(f"  quantization contract checked on {n_ok} mesh file(s)")


def check_albedo_exposure():
    """No albedo may be brighter than a real surface reflects.

    Art Bible §4's hexes are what a material should LOOK like under §4's own
    lighting; an albedo map is a REFLECTANCE. Pasting one into the other put
    `plaster` — the town's commonest surface — at 0.861 mean sRGB luminance,
    which is snow, and whole buildings rendered as featureless white boxes with
    the roof and the wall merged into one shape. `core.materials.expose` is the
    mapping; this is the gate that keeps a new builder from bypassing it.
    """
    try:
        from PIL import Image
    except ImportError:
        return
    print("\nalbedo exposure (Art Bible §4/§5):")
    rows = []
    for a in sorted(glob.glob(os.path.join(TEX_DIR, "*_albedo.png"))):
        key = os.path.basename(a)[: -len("_albedo.png")]
        im = np.asarray(Image.open(a).convert("RGBA"), np.float32) / 255.0
        lum = (0.2126 * im[..., 0] + 0.7152 * im[..., 1] + 0.0722 * im[..., 2])
        alpha = im[..., 3]
        if alpha.min() < 0.99 and (alpha > 0.5).sum() > 16:
            lum = lum[alpha > 0.5]
        mean, p99 = float(lum.mean()), float(np.percentile(lum, 99))
        rows.append((mean, p99, key))
        where = rel(a)
        if mean > ALBEDO_MEAN_MAX:
            err(f"albedo '{key}' has mean luminance {mean:.3f}, over {ALBEDO_MEAN_MAX:.2f}. "
                f"It will clip against §4's own key light. Route it through "
                f"core.materials.expose.", where)
        elif p99 > ALBEDO_P99_MAX:
            warn(f"albedo '{key}' 99th percentile {p99:.3f}, over {ALBEDO_P99_MAX:.2f} "
                 f"— a highlight that blows out under the locked rig", where)
    rows.sort(reverse=True)
    print(f"  {len(rows)} albedo maps, mean luminance "
          f"{np.mean([r[0] for r in rows]):.3f}; brightest: " +
          ", ".join(f"{k} {m:.2f}" for m, _p, k in rows[:4]))


def check_town(town, mesh_info):
    if town is None:
        err("content/town/hearthmere.json missing")
        return
    for v in town.get("venues", []):
        mesh = os.path.join(MESH_DIR, f"{v['id']}.gltf")
        if not os.path.exists(mesh):
            err(f"town references venue '{v['id']}' with no built mesh", rel(TOWN_PATH))

    # Venue overlap. Some venues legitimately occupy the same footprint — the
    # market stalls stand inside the market square — so only flag pairs that are
    # not a known nesting.
    NESTED = {("market_square", "stalls"), ("streets", "market_square"),
              ("streets", "stalls"),
              # The ground underlies everything placed at the world origin.
              ("terrain", "streets"), ("terrain", "market_square"),
              ("terrain", "stalls")}
    nested = {tuple(sorted(p)) for p in NESTED}
    seen = {}
    for v in town.get("venues", []):
        key = tuple(round(c, 1) for c in v["origin"])
        other = seen.get(key)
        if other and other != v["id"]:
            if tuple(sorted((other, v["id"]))) not in nested:
                warn(f"venues '{other}' and '{v['id']}' share origin {key}",
                     rel(TOWN_PATH))
        seen[key] = v["id"]

    check_budget(town, mesh_info)


# ---------------------------------------------------------------------------
# Directive §7 performance budget, attributed
# ---------------------------------------------------------------------------

def _cell_label(x, z, grid):
    """The town's own cell name for a world point (E3), or an out-of-grid key."""
    size = grid.get("cellSize", 16)
    cols, rows = grid.get("cols") or [], grid.get("rows") or []
    nc, nr = len(cols) or 12, len(rows) or 12
    ci = int(math.floor(x / size)) + nc // 2
    cj = int(math.floor(z / size)) + nr // 2
    if not (0 <= ci < nc and 0 <= cj < nr):
        return "outside-grid"
    col = cols[ci] if ci < len(cols) else chr(65 + ci)
    row = rows[cj] if cj < len(rows) else cj + 1
    return f"{col}{row}"


def check_budget(town, mesh_info):
    """Attribute draw calls and triangles PER VENUE and PER CELL.

    Static analysis of the built files, so it runs in a second and needs no
    GPU — but it can only measure the town with NOTHING culled. That upper
    bound is still the right thing to gate on, for two reasons: it is the only
    number that does not depend on where a camera happens to be pointing, and
    the level that matters most (LOD3, the whole town as impostors) is exactly
    the case where culling saves least.

    `tools/render/town.mjs` measures the real frame with culling and LOD live.
    The two are complementary and neither replaces the other: this one tells
    you a cell is overloaded before you have rendered anything.
    """
    grid = town.get("grid", {})
    per_venue, per_cell = {}, {}
    tris = draws = 0
    lod_draws = [0] * 4
    lod_tris = [0] * 4
    instanced_nodes = instances = 0

    for v in town.get("venues", []):
        info = mesh_info.get(f"{v['id']}.gltf")
        if not info:
            continue
        key = v.get("instance") or v["id"]
        tris += info["tris"]
        draws += info["primitives"]
        instanced_nodes += info.get("instancedNodes", 0)
        hm = info.get("hm")
        pv = per_venue.setdefault(key, {"draws": 0, "tris": 0, "cells": 0, "lod": [0] * 4})
        pv["tris"] += info["tris"]
        if not hm:
            pv["draws"] += info["primitives"]
            for i in range(4):
                pv["lod"][i] += info["primitives"]
                lod_draws[i] += info["primitives"]
                lod_tris[i] += info["tris"]
            continue

        a = math.radians(v.get("rotationDeg", 0) or 0)
        c, s = math.cos(a), math.sin(a)
        ox, _oy, oz = v["origin"]
        groups = list(hm.get("cells", [])) + [
            {"key": i["cell"], "lodPrims": i["lodPrims"], "lodTris": i["lodTris"],
             "min": i.get("min"), "max": i.get("max"), "instances": i["count"]}
            for i in hm.get("instanced", [])]
        cell_m = hm.get("cellSize", 16)
        pv["cells"] += len({g["key"] for g in groups})
        instances += sum(i["count"] for i in hm.get("instanced", []))
        for g in groups:
            lp = g.get("lodPrims") or [0]
            lt = g.get("lodTris") or [0]
            for i in range(4):
                p = lp[i] if i < len(lp) else lp[0]
                lod_draws[i] += p
                pv["lod"][i] += p
                lod_tris[i] += lt[i] if i < len(lt) else lt[0]
            pv["draws"] += lp[0]
            if g.get("min"):
                cx = (g["min"][0] + g["max"][0]) * 0.5
                cz = (g["min"][2] + g["max"][2]) * 0.5
                span = max(g["max"][0] - g["min"][0], g["max"][2] - g["min"][2])
            else:
                cx = cz = 0.0
                span = 0.0
            wx = ox + c * cx + s * cz
            wz = oz - s * cx + c * cz
            # A group spanning more than a couple of cells is a town-wide layer —
            # the ground plate, an unbatched venue — and charging its whole cost
            # to the cell its centroid happens to land in invents a hotspot
            # there. The terrain's single 576 m group put 7 draws plus every
            # instance batch in G7 and reported it as the worst cell in town.
            lab = "town-wide" if span > cell_m * 2.5 else _cell_label(wx, wz, grid)
            pc = per_cell.setdefault(lab, {"draws": 0, "tris": 0, "venues": set()})
            pc["draws"] += lp[0]
            pc["tris"] += lt[0] if lt else 0
            pc["venues"].add(key)

    n_place = len(town.get("venues", []))
    print(f"  {n_place} placements, {tris:,} source tris across every LOD, "
          f"{draws:,} primitives; unculled draw calls by LOD level: "
          + " / ".join(f"L{i} {d:,}" for i, d in enumerate(lod_draws)))
    print("  unculled triangles by LOD level: "
          + " / ".join(f"L{i} {t:,}" for i, t in enumerate(lod_tris)))
    print(f"  {instanced_nodes} GPU-instanced batches carrying {instances:,} instances")

    hot_v = sorted(per_venue.items(), key=lambda kv: -kv[1]["draws"])[:5]
    print("  heaviest venues (LOD0 draws): "
          + ", ".join(f"{k} {d['draws']} over {d['cells']} cells" for k, d in hot_v))
    hot_c = sorted(per_cell.items(), key=lambda kv: -kv[1]["draws"])[:6]
    print("  heaviest cells  (LOD0 draws): "
          + ", ".join(f"{k} {d['draws']} ({'+'.join(sorted(d['venues']))})" for k, d in hot_c))

    # --- the gates ---------------------------------------------------------
    #
    # Triangles, measured the same way the draw gate is: the whole town visible
    # at once with every cell at its impostor level. §7 budgets triangles
    # DRAWN, and the number this used to gate on was `tris` — the sum of every
    # primitive in every file, which is LOD0 *plus* LOD1 *plus* LOD2 *plus*
    # LOD3 of the same cell. Nothing ever draws that; it was 4,983,616 against
    # a 3.5 M budget on a town whose measured worst gameplay frame is 1.13 M,
    # so §7's headline row has been reporting a failure that cannot happen.
    # The honest static bound is the level no culling can improve on.
    if lod_tris[3] > TRI_BUDGET:
        err(f"§7 budget: the whole town at LOD3 is {lod_tris[3]:,} triangles, "
            f"over the {TRI_BUDGET:,} budget. No culling can fix this — the "
            f"impostor level itself is too heavy.")
    elif lod_tris[3] > TRI_BUDGET * 0.7:
        warn(f"§7 budget: the whole town at LOD3 is {lod_tris[3]:,} triangles, "
             f"over 70% of the {TRI_BUDGET:,} budget")
    # LOD0 unculled is not a frame anyone renders, but it is the near-field
    # content weight, and once it passes the whole budget a player standing
    # anywhere open is relying entirely on the cull to stay inside §7.
    if lod_tris[0] > TRI_BUDGET:
        warn(f"§7 budget: the town at LOD0 with nothing culled is "
             f"{lod_tris[0]:,} triangles, over the {TRI_BUDGET:,} drawn budget "
             f"— inside §7 only because of distance culling. "
             f"tools/render/town.mjs owns the real frame.")

    # Draw calls at the IMPOSTOR level are the one static number that must hold.
    # Every cell in the town visible at once, each drawn at LOD3, is the
    # worst case no amount of culling can improve on — if that does not fit in
    # 900, the town cannot be rendered from a hilltop and no runtime trick will
    # save it.
    if lod_draws[3] > DRAW_BUDGET:
        err(f"§7 budget: the whole town at LOD3 is {lod_draws[3]:,} draw calls, "
            f"over the {DRAW_BUDGET} budget. No culling can fix this — the fix "
            f"is fewer materials per cell (texture atlasing) or larger cells.")
    elif lod_draws[3] > DRAW_BUDGET * 0.7:
        warn(f"§7 budget: the whole town at LOD3 is {lod_draws[3]:,} draw calls, "
             f"over 70% of the {DRAW_BUDGET} budget with the town not yet complete")

    # A single 16 m cell is the unit the client draws, so one overloaded cell is
    # a frame spike wherever the player stands in it.
    CELL_DRAW_LIMIT = 45
    for k, d in per_cell.items():
        if k not in ("outside-grid", "town-wide") and d["draws"] > CELL_DRAW_LIMIT:
            warn(f"cell {k} costs {d['draws']} draw calls at LOD0 "
                 f"({', '.join(sorted(d['venues']))}) — over {CELL_DRAW_LIMIT}, "
                 f"a frame spike for anyone standing in it")


def _col_world(vol, origin, rot_deg):
    """A collision volume in world space.

    `(kind, minY, maxY, test(x, z), (x0, x1, z0, z1))` — the last member is the
    world-space XZ bounding box, which is what the broadphase in
    `check_collision` indexes and what lets a point query reject a volume
    without calling its `test` at all.

    Mirrors client/src/collision.js. Two implementations of the same transform
    is a real risk, so it is confined to this one function and the client's
    `addVenue`, and the shared convention is stated in core/collision.py.
    """
    a = math.radians(rot_deg or 0.0)
    c, s = math.cos(a), math.sin(a)
    ox, oy, oz = origin

    def to_world(x, z):
        return ox + c * x + s * z, oz - s * x + c * z

    kind = vol.get("kind", "solid")
    if vol["shape"] == "box":
        cx, cy, cz = vol["center"]
        hx, hy, hz = vol["half"]
        wx, wz = to_world(cx, cz)
        ang = a + vol.get("rotY", 0.0)
        cc, ss = math.cos(ang), math.sin(ang)

        def test(x, z):
            dx, dz = x - wx, z - wz
            lx = cc * dx - ss * dz
            lz = ss * dx + cc * dz
            return abs(lx) <= hx and abs(lz) <= hz
        # The rotated box's AABB: project both half-extents onto each axis.
        ex = abs(cc) * hx + abs(ss) * hz
        ez = abs(ss) * hx + abs(cc) * hz
        return (kind, oy + cy - hy, oy + cy + hy, test,
                (wx - ex, wx + ex, wz - ez, wz + ez))
    if vol["shape"] == "cylinder":
        cx, cy, cz = vol["center"]
        wx, wz = to_world(cx, cz)
        r, h = vol["radius"], vol["height"]
        return (kind, oy + cy - h * 0.5, oy + cy + h * 0.5,
                lambda x, z: math.hypot(x - wx, z - wz) <= r,
                (wx - r, wx + r, wz - r, wz + r))
    pts = [to_world(px, pz) for px, pz in vol["points"]]

    def test(x, z):
        for i in range(len(pts)):
            ax, az = pts[i]
            bx, bz = pts[(i + 1) % len(pts)]
            if (bx - ax) * (z - az) - (bz - az) * (x - ax) < 0:
                return False
        return True
    xs = [p[0] for p in pts]
    zs = [p[1] for p in pts]
    return (kind, oy + vol["minY"], oy + vol["maxY"], test,
            (min(xs), max(xs), min(zs), max(zs)))


# Broadphase. Without one this check is ~2.0e9 Python-level volume tests on the
# real town — 2,513 volumes x ~1,030 street stations x 37 lateral samples x 5
# neighbourhood probes x up to 4 step-resolution rounds — and it never finished.
# Three separate agents reported `tools/validate.py` hanging past three minutes,
# which meant NOTHING in this file had been run against the town for several
# waves. A gate nobody can run is worse than no gate.
#
# A uniform XZ grid over the volumes' world bounding boxes cuts the candidate
# set at a point query from 2,513 to single digits. 4 m is a little over the
# median volume span, so most volumes land in one to four buckets.
BROAD_CELL = 4.0
# A volume whose footprint covers more than this many buckets is a town-wide
# plate (the terrain ground, a road surface) and indexing it would write
# thousands of duplicate references; those are kept in one always-tested list
# instead. There are single digits of them.
BROAD_MAX_CELLS = 256


class _Broadphase:
    """Uniform XZ grid: which collision volumes can possibly contain a point."""

    def __init__(self, records):
        self.recs = records
        self.grid = {}
        self.wide = []
        for idx, (_owner, rec) in enumerate(records):
            x0, x1, z0, z1 = rec[4]
            i0 = int(math.floor(x0 / BROAD_CELL))
            i1 = int(math.floor(x1 / BROAD_CELL))
            j0 = int(math.floor(z0 / BROAD_CELL))
            j1 = int(math.floor(z1 / BROAD_CELL))
            if (i1 - i0 + 1) * (j1 - j0 + 1) > BROAD_MAX_CELLS:
                self.wide.append(idx)
                continue
            for i in range(i0, i1 + 1):
                for j in range(j0, j1 + 1):
                    self.grid.setdefault((i, j), []).append(idx)
        self._empty = tuple(self.wide)
        # Fold the always-tested list into every populated bucket so a query is
        # one dict lookup rather than a chained iteration.
        for key, lst in self.grid.items():
            self.grid[key] = tuple(lst) + self._empty

    def near(self, x, z):
        return self.grid.get((int(math.floor(x / BROAD_CELL)),
                              int(math.floor(z / BROAD_CELL))), self._empty)


def check_collision(town):
    """Directive §6.4: collision is authored, not inferred.

    Three things are worth checking mechanically, and the third is the one that
    matters. Presence catches a generator that forgot. Schema conformance
    catches a malformed volume before it becomes a silent no-op in the client —
    an unknown shape is skipped at load, so a typo would remove collision from a
    building without anything failing. And the centreline test catches the
    defect that motivated the whole pipeline: something solid standing in a
    street. `tools/check_walkable.mjs` proves the stronger property (the town is
    actually connected); this is the cheap always-on version of it.
    """
    if not os.path.isdir(COL_DIR):
        err("content/collision/ does not exist — collision is still inferred from "
            "venue bounding boxes (Directive §6.4 bans that; it is why Ford Road "
            "is sealed in v1)")
        return
    have = {}
    for p in sorted(glob.glob(os.path.join(COL_DIR, "*.json"))):
        have[os.path.basename(p)[:-5]] = (json.load(open(p)), p)
    want = {v["id"] for v in (town.get("venues", []) if town else [])}
    for v in sorted(want - set(have)):
        err(f"venue '{v}' is placed in the town but has no collision file — the "
            f"client will let the player walk through it", rel(COL_DIR))

    # Schema conformance.
    schema_path = os.path.join(SCHEMA_DIR, "collision.schema.json")
    total = 0
    if os.path.exists(schema_path):
        try:
            import jsonschema
            schema = json.load(open(schema_path))
            for name, (doc, p) in have.items():
                for e in jsonschema.Draft7Validator(schema).iter_errors(doc):
                    loc = "/".join(str(x) for x in e.absolute_path) or "(root)"
                    err(f"{loc}: {e.message}", rel(p))
        except ImportError:
            warn("jsonschema not installed — collision files checked for shape "
                 "sanity only")
    for name, (doc, p) in have.items():
        total += len(doc.get("volumes", []))
        if not doc.get("volumes") and name in want:
            warn(f"venue '{name}' declares zero collision volumes", rel(p))

    # No street may be blocked ACROSS ITS WHOLE WIDTH (Directive §3).
    #
    # The first version of this tested the centreline itself and immediately
    # cried wolf: the market fountain stands at world origin, which is where
    # both Ford Road's and Mere Street's authored polylines cross, and walking
    # round a fountain in a plaza is not a defect. What is unarguable is that no
    # body-width gap exists at some station along the street. So each station is
    # scanned across the carriageway plus 2 m of verge — a street through a
    # square legitimately widens — and reported only when the widest free run
    # falls below one shoulder width.
    BODY = 1.0            # m of clear lateral run a player needs
    MARGIN = 2.0          # m of verge either side that still counts as "the street"
    STEP = 0.35           # client/src/collision.js STEP_HEIGHT
    HEAD = 1.4            # blocking span above the feet (1.75 m body, less the step)
    vols = []
    for v in (town.get("venues", []) if town else []):
        doc = have.get(v["id"], (None, None))[0]
        if not doc:
            continue
        for raw in doc.get("volumes", []):
            try:
                vols.append((v.get("instance", v["id"]),
                             _col_world(raw, v.get("origin", [0, 0, 0]),
                                        v.get("rotationDeg", 0))))
            except (KeyError, TypeError):
                pass                       # malformed; the schema pass reported it
    # Whether a volume blocks depends on where the player's FEET are, and that
    # is not y=0: the town falls 4 m north to south and the terrain layer
    # authors step flights through its own retaining walls. Read literally,
    # every one of those walls looks like a barricade across the street. So the
    # ground is resolved the way the controller resolves it — terrain, then any
    # surface within a step of it, repeatedly, so a flight accumulates — and
    # only then is a volume asked whether it is in the way.
    H, _hsrc = load_terrain()
    bp = _Broadphase(vols)

    def ground(x, z, g):
        """Resolve standing height at (x, z) from terrain height `g`."""
        cand = bp.near(x, z)
        if not cand:
            return g
        recs = vols
        for _ in range(4):
            best = g
            lim = g + STEP
            for idx in cand:
                _k, y0, y1, test, box = recs[idx][1]
                if y1 > best and y1 <= lim and y0 <= lim \
                        and box[0] <= x <= box[1] and box[2] <= z <= box[3] \
                        and test(x, z):
                    best = y1
            if best <= g:
                break
            g = best
        return g

    def blocked_by(x, z, g):
        best = None
        for idx in bp.near(x, z):
            o, (k, y0, y1, test, box) = vols[idx]
            if k != "solid" or y1 <= g + STEP or y0 >= g + HEAD:
                continue
            if box[0] <= x <= box[1] and box[2] <= z <= box[3] and test(x, z):
                # Height above the local ground decides how loudly this is
                # reported: a 0.6 m parapet is something a player steps over
                # from the high side, a 3 m wall is a barricade.
                if best is None or y1 - g > best[1]:
                    best = (o, y1 - g)
        return best

    # The player arrives at a point carrying the height of the ground it was
    # standing on, so the feet height at a probe is the best of a small
    # neighbourhood, not the height of that exact point. Without that, a 0.6 m
    # parapet with a step flight half a metre to one side reads as a barricade
    # — a false positive on the terrain layer's own retaining walls, and this
    # check is only worth having if it stays quiet when the town is fine.
    # `check_walkable.mjs` owns the exact answer; this owns the cheap
    # always-on one.
    NEIGHBOURHOOD = ((0.0, 0.0), (0.5, 0.0), (-0.5, 0.0), (0.0, 0.5), (0.0, -0.5))

    # Every probe point in the town is laid out first so `terrain.height` is
    # called five times on arrays of ~38,000 points instead of ~190,000 times
    # on scalars. On the shipped terrain that alone was ~15 s of the runtime.
    lanes = []          # (street, qx, qz, first_probe_index, n_probes)
    px, pz = [], []
    for st in (town.get("streets", []) if town else []):
        half = float(st.get("width", 5.0)) * 0.5 + MARGIN
        # Street paths are [x, z] (D-024): the ground comes from terrain,
        # never from a stored Y.
        path = [np.array([q[0], 0.0, q[1]], float) for q in st["path"]]
        nlat = int(half * 2 / 0.25) + 1
        for i in range(len(path) - 1):
            a, b = path[i], path[i + 1]
            ln = float(np.linalg.norm(b - a))
            if ln < 1e-6:
                continue
            d = (b - a) / ln
            nrm = np.array([-d[2], 0.0, d[0]])
            for k in range(max(1, int(ln / 1.0)) + 1):
                q = a + d * min(ln, k * 1.0)
                lanes.append((st, float(q[0]), float(q[2]), len(px), nlat))
                for j in range(nlat):
                    p = q + nrm * (-half + j * 0.25)
                    px.append(float(p[0]))
                    pz.append(float(p[2]))

    stations = len(lanes)
    if px:
        AX = np.asarray(px)
        AZ = np.asarray(pz)
        # Chunked so the terrain call can never allocate an unbounded temporary
        # no matter how much street the town grows.
        feet = np.empty(len(AX))
        CH = 65536
        for s in range(0, len(AX), CH):
            e = min(s + CH, len(AX))
            g = None
            for dx, dz in NEIGHBOURHOOD:
                h = np.asarray(H(AX[s:e] + dx, AZ[s:e] + dz), float)
                g = h if g is None else np.maximum(g, h)
            feet[s:e] = g
    else:
        AX = AZ = feet = np.zeros(0)

    # Resolve standing height once per probe, then ask what is in the way.
    hit_owner = [None] * len(px)
    hit_tall = [0.0] * len(px)
    for m in range(len(px)):
        x, z = px[m], pz[m]
        g = feet[m]
        for dx, dz in NEIGHBOURHOOD:
            s = ground(x + dx, z + dz, g)
            if s > g:
                g = s
        h = blocked_by(x, z, g)
        if h is not None:
            hit_owner[m] = h[0]
            hit_tall[m] = h[1]

    by_street = {}
    for st, qx, qz, first, nlat in lanes:
        run = widest = 0.0
        culprit, tallest = None, 0.0
        for m in range(first, first + nlat):
            if hit_owner[m] is None:
                run += 0.25
                if run > widest:
                    widest = run
            else:
                run = 0.0
                culprit = culprit or hit_owner[m]
                tallest = max(tallest, hit_tall[m])
        if widest < BODY:
            by_street.setdefault(id(st), (st, []))[1].append(
                (qx, qz, culprit, tallest))

    for st, pinch in by_street.values():
        if pinch:
            who = sorted({p[2] for p in pinch if p[2]})
            tall = max(p[3] for p in pinch)
            msg = (f"{st['id']} has no {BODY:.1f} m walkable gap at "
                   f"{len(pinch)} station(s) across {st.get('width')} m + "
                   f"{MARGIN} m of verge, e.g. ({pinch[0][0]:.1f}, "
                   f"{pinch[0][1]:.1f}), obstruction {tall:.2f} m above the "
                   f"local ground. Standing in it: {', '.join(who) or 'unknown'}. "
                   f"Directive §3")
            # Anything a player could step over from the high side is a
            # warning, because this is a point-wise test and the flood in
            # tools/check_walkable.mjs is the authority on whether the street
            # is actually severed. Chest height and up is unarguable.
            (err if tall > 1.2 else warn)(msg, rel(COL_DIR))
    print(f"  {len(have)} collision files, {total} volumes, "
          f"{stations} street stations checked for a walkable gap")


# ---------------------------------------------------------------------------

def check_determinism_sources():
    """CLAUDE.md hard constraint 3 / ARCHITECTURE §7, as a check instead of a hope.

    `venues/landscape.py` seeded its ground-patch lattice from
    `abs(hash(asset_id))` for at least two waves. Python salts `str` hashing per
    process, so every ground patch in Hearthmere — and every tree, hedge and
    verge scattered against one — came out different on every build. That is
    what `ad-town-05` measured as "a rebuild from source is not a no-op":
    validate went 0 to 5 failures and a tree vanished from `t-gate-south`
    without a line of source changing.

    Three modules already carried comments warning against `hash()`. Nothing
    checked. This is the cheap half of `tools/determinism.py` (the full gate
    rebuilds twice under two `PYTHONHASHSEED` values and diffs the bytes); it
    runs here because it costs milliseconds and catches the whole class.
    """
    sys.path.insert(0, os.path.join(REPO, "tools"))
    try:
        from determinism import lint_sources
    except Exception as e:                       # noqa: BLE001
        warn(f"determinism lint unavailable: {type(e).__name__}: {e}")
        return
    hits = lint_sources()
    print(f"\ndeterminism (ARCHITECTURE §7): {len(hits)} process-salted seed(s)")
    for path, line, text in hits:
        err(f"builtin hash() is process-salted and cannot seed a generator — "
            f"use core.mathx.seed_from(). Full gate: tools/determinism.py",
            f"{path}:{line}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--venue", "-v", action="append")
    ap.add_argument("--quick", action="store_true",
                    help="skip the geometry and palette passes")
    args = ap.parse_args()

    town = json.load(open(TOWN_PATH)) if os.path.exists(TOWN_PATH) else None

    print("textures:")
    print(f"  {check_textures()} PBR sets")

    print("\nmeshes:")
    paths = sorted(glob.glob(os.path.join(MESH_DIR, "*.gltf")))
    if args.venue:
        paths = [p for p in paths if os.path.basename(p)[:-5] in args.venue]
    total = 0
    mesh_info = {}
    for p in paths:
        info = check_gltf(p)
        if info:
            mesh_info[info["name"]] = info
            total += info["tris"]
            sx, sy, sz = info["span"]
            print(f"  {info['name']:24s} {info['tris']:7,d} tris  "
                  f"{sx:5.1f} x {sy:5.1f} x {sz:5.1f} m  {info['materials']} mats")
    print(f"  total {total:,} tris authored")

    print("\nentities:")
    ent = 0
    for p in sorted(glob.glob(os.path.join(ENT_DIR, "*.json"))):
        c = check_entities(p)
        ent += c
        print(f"  {os.path.basename(p):24s} {c:3d}")
    print(f"  total {ent}")

    print("\ntown:")
    check_town(town, mesh_info)
    check_street_widths(town)
    check_collision(town)

    if not args.quick:
        H, hsrc = load_terrain()
        check_geometry(paths, town, H, hsrc)
        check_entity_ground(town, H)
        check_palette()
        check_texel_density()
        check_uv_density()
        check_albedo_exposure()
    check_mesh_bytes()

    check_scale()
    check_anachronisms()
    check_determinism_sources()

    print()
    for where, w in warnings:
        print(f"  WARN  {where + ': ' if where else ''}{w}")
    for where, e in problems:
        print(f"  FAIL  {where + ': ' if where else ''}{e}")
    print(f"\n{len(problems)} failures, {len(warnings)} warnings")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
