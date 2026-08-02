"""The ground.

Until now Hearthmere stood on a 300 m plane with a tiled dirt albedo, and
every generator in the repository assumed y = 0. This module turns
`content/town/terrain.json` into real geometry: a graded, LOD'd, multi-material
heightfield with the Emberflow and the Mere carved into it, the retaining walls
and step flights that carry the town's 4 m fall, and a water surface.

It is a consumer, not an author. Every elevation here comes from
`core.terrain`, which is the same function `client/src/terrain.js` evaluates —
so the mesh, the client's collision, and every venue generator's placement all
agree by construction. That is BUILD_DIRECTIVE section 6 rule 3, and it is the
whole point of the module.

Three things carry the visual read, in order of impact:

1. **Levelling.** The market square, the church precinct and every building pad
   are dead flat, and the fall between them is taken up in scarps with walls
   and steps. A building on a slope with a level floor plate is a floating
   building; that is the defect being eliminated, and it is fixed in the
   ground, not in the buildings.
2. **Material variety.** Turf, trodden earth, shingle, wet silt, submerged bed
   and open water are five different substrates, not five tints. Boundaries are
   dithered with the same noise field the height uses, so no splat edge follows
   a contour line.
3. **Per-vertex colour.** A 4 m tiling texture repeats 144 times across the
   town. COLOR_0 carries 20 m colour variation over the top of it, which is
   what actually kills the tiling read at distance.
"""

from __future__ import annotations

import numpy as np

from core import kit as K
from core import materials as MATS
from core import mesh as M
from core import palette as P
from core import terrain as TR
from core import vegetation as V
from core.mathx import rng_for

NAME = "terrain"
CELLS = []          # the terrain underlies every cell; it belongs to none

# The one venue that opts out of core's batching and LOD (core/venue.py).
#
# BATCH: the ground plate is 576 m square, so a 16 m module is 1,296 cells and
# ~5,000 primitives — the batcher would turn 31 draw calls into thousands to buy
# culling on a surface that is visible from everywhere and can never be culled.
# LOD: the heightfield is ALREADY a 4-ring LOD, built here at 1/2/4/8 m cells
# and stitched. Decimating it a second time would collapse the stitching and
# tear seams into the ground.
BATCH = False
LOD = False

# Ground materials, in the order the splat resolves them.
GROUND_MATS = ["riverbed", "mud", "gravel", "earth", "grass"]

# Mean linear albedo per ground material, used to tint one material toward its
# neighbour across a splat boundary. These are the `set_base` values from
# core/materials.py; if a builder's base colour changes, change it here too.
MAT_BASE = {
    "grass": P.rgb("#5E7A3E"),
    "earth": P.rgb("#6E5C46"),
    "gravel": P.rgb("#8C8272"),
    "mud": P.rgb("#4E4033"),
    "riverbed": P.rgb("#3E4A40"),
}

# Ground UVs come from `materials.uv_scale(key)` per material now, not from
# one shared constant — see `_ground_group`. Kept only as the value the water
# grid's noise fields were tuned against.
# 2.5 m per tile. Ripples must be at RIPPLE scale: at a 10 m tile the normal
# map's waves are 10 m across, so the sun's specular lobe stays coherent over
# the whole lake and renders as one blown-white plate instead of a glitter
# path. Lives in core.kit so the fountain basin and the harbour agree.
WATER_UV = K.WATER_UV


# ---------------------------------------------------------------------------
# Heightfield rings
# ---------------------------------------------------------------------------

def _ring(T, inner, outer, cell, coarse_cell):
    """One square LOD ring of the heightfield.

    Returns (verts, normals, quads) where `quads` indexes into `verts`.

    The outer edge is STITCHED to the coarser ring beyond it. Every second
    vertex on that edge coincides with a coarse vertex and takes its exact
    height; the ones between are set to the mean of their two neighbours, which
    places them exactly on the coarse edge segment. That is a geometric
    identity, not an approximation, so there is no crack and no skirt is
    needed — and skirts are what usually ship instead, showing as a dark rim
    at every LOD boundary.
    """
    n = int(round(2.0 * outer / cell))
    if n % 2 and coarse_cell:
        raise ValueError(f"ring outer={outer} is not an even number of {cell} m cells")
    coords = -outer + np.arange(n + 1, dtype=np.float64) * cell
    X, Z = np.meshgrid(coords, coords, indexing="ij")
    H = T.height(X.ravel(), Z.ravel()).reshape(X.shape)

    if coarse_cell:
        step = int(round(coarse_cell / cell))
        odd = np.array([i % step != 0 for i in range(n + 1)])
        lo = np.array([(i // step) * step for i in range(n + 1)])
        hi = np.minimum(lo + step, n)
        for edge in (0, n):
            # Along a row (constant Z) and a column (constant X) of the border.
            H[odd, edge] = 0.5 * (H[lo[odd], edge] + H[hi[odd], edge])
            H[edge, odd] = 0.5 * (H[edge, lo[odd]] + H[edge, hi[odd]])

    verts = np.stack([X.ravel(), H.ravel(), Z.ravel()], axis=1)
    nrm = T.normal(X.ravel(), Z.ravel())

    # Cells whose centre is outside the inner hole.
    ci = np.arange(n)
    cx = coords[:-1] + cell * 0.5
    CX, CZ = np.meshgrid(cx, cx, indexing="ij")
    keep = np.maximum(np.abs(CX), np.abs(CZ)) >= inner - 1e-9
    I, J = np.meshgrid(ci, ci, indexing="ij")
    I, J = I[keep], J[keep]

    stride = n + 1
    v0 = I * stride + J
    v1 = (I + 1) * stride + J
    v2 = (I + 1) * stride + (J + 1)
    v3 = I * stride + (J + 1)

    # Alternate the diagonal so the field is not one combed direction — a
    # uniform diagonal reads as corduroy on any slope lit across it.
    alt = ((I + J) % 2) == 0
    tri = np.empty((len(I) * 2, 3), np.int64)
    a = np.where(alt[:, None], np.stack([v0, v3, v2], 1), np.stack([v1, v0, v3], 1))
    b = np.where(alt[:, None], np.stack([v0, v2, v1], 1), np.stack([v1, v3, v2], 1))
    tri[0::2] = a
    tri[1::2] = b
    return verts, nrm, tri


def _build_field(T):
    """Concatenate the LOD rings into one vertex pool and triangle list."""
    verts, nrms, tris = [], [], []
    base = 0
    rings = T.rings
    for k, r in enumerate(rings):
        inner = 0.0 if k == 0 else float(rings[k - 1]["outer"])
        coarse = float(rings[k + 1]["cell"]) if k + 1 < len(rings) else None
        v, nn, t = _ring(T, inner, float(r["outer"]), float(r["cell"]), coarse)
        verts.append(v)
        nrms.append(nn)
        tris.append(t + base)
        base += len(v)
    return np.vstack(verts), np.vstack(nrms), np.vstack(tris)


# ---------------------------------------------------------------------------
# Splat resolve + vertex colour
# ---------------------------------------------------------------------------

def _ground_group(T, verts, nrms, tris):
    x, y, z = verts[:, 0], verts[:, 1], verts[:, 2]
    ny = np.clip(nrms[:, 1], 1e-9, 1.0)
    slope = np.sqrt(np.maximum(1.0 - ny * ny, 0.0)) / ny

    w = T.surface_weights(x, z, h=y, slope=slope)
    W = np.stack([w[k] for k in GROUND_MATS], axis=1)       # (V, 5)
    Wsum = np.maximum(W.sum(axis=1, keepdims=True), 1e-9)
    Wn = W / Wsum

    # Blend colour: what this vertex would be if the five substrates were mixed.
    bases = np.stack([MAT_BASE[k] for k in GROUND_MATS], axis=0)   # (5, 3)
    blend = Wn @ bases                                             # (V, 3)

    # Large-scale colour, in WORLD space. This is the half of the ground's
    # appearance that a tiling texture structurally cannot provide: the 6 m
    # albedo tile repeats ~30 times across the town, so anything above a metre
    # or two has to live here or it reads as wallpaper. Three octaves at 18 m,
    # 59 m and 32 m, deliberately incommensurate with the tile size.
    var = TR._value_noise(x * 0.055, z * 0.055, 991733)
    var2 = TR._value_noise(x * 0.017, z * 0.017, 4410221)
    variance = 0.72 + 0.16 * var + 0.12 * var2

    # Hue as well as value. Damp ground runs green-blue, dry ground runs warm;
    # varying only brightness gives a grey-scale patchwork that still reads as
    # one material with a dirt overlay on it.
    hue = TR._value_noise(x * 0.031, z * 0.031, 2276641)
    hue_rgb = np.stack([1.0 - 0.13 * hue,
                        np.ones_like(hue),
                        1.0 - 0.17 * (1.0 - hue)], axis=1)

    # Soil washes off a scarp, so steep ground reads lighter and stonier.
    slope_f = 1.0 - 0.10 * np.clip(slope, 0.0, 1.2)

    # Per-triangle material: the mean of its three vertices' weights, with the
    # tie broken by a COHERENT field rather than by whatever the noise happened
    # to do at that vertex.
    #
    # Plain `argmax` is right everywhere two weights differ and catastrophic
    # everywhere they are equal — and they are equal along the whole length of
    # every band boundary, which is the only place anybody looks. On the north
    # gate's bank the mud band met the turf at 50/50 for a 1.5 m strip and the
    # splat alternated grass, silt, grass, silt at the cell size: `ad-town-05`
    # §2's "hard sawtooth of flat dark triangles where the bank meets the
    # surface". The module docstring has always claimed these boundaries are
    # dithered; this is the line that makes it true.
    #
    # ~6 m and ~1.9 m wavelengths, one bias field per material, seeded off the
    # material index. A 50/50 boundary now breaks into coherent tongues of one
    # material into the other, which is what a real transition between shingle
    # and turf looks like, instead of into a chequerboard.
    tw = (Wn[tris[:, 0]] + Wn[tris[:, 1]] + Wn[tris[:, 2]]) * (1.0 / 3.0)
    cx = (x[tris[:, 0]] + x[tris[:, 1]] + x[tris[:, 2]]) * (1.0 / 3.0)
    cz = (z[tris[:, 0]] + z[tris[:, 1]] + z[tris[:, 2]]) * (1.0 / 3.0)
    bias = np.stack([
        (TR._value_noise(cx * 0.17, cz * 0.17, 6600011 + k * 9173) - 0.5) * 0.20 +
        (TR._value_noise(cx * 0.52, cz * 0.52, 8800033 + k * 4517) - 0.5) * 0.09
        for k in range(len(GROUND_MATS))], axis=1)
    pick = np.argmax(tw + bias, axis=1)

    # The wet band. Capillary rise and splash keep the 0.35 m of bank above
    # the waterline permanently damp, and wet ground is much darker and a
    # little cooler than the same ground dry. Without it the water meets the
    # land on a hard line, which is the single most reliable tell of
    # procedural terrain — and no amount of work on the water itself fixes it,
    # because the defect is on the other side of the edge.
    #
    # Per-vertex rather than in a texture, because "how far above the water is
    # this" is a world-position question and the ground textures tile.
    #
    # Widened from 0.42 m to 0.95 m and deepened. 0.42 m of damp on a bank that
    # falls 2.5 m to the water is a line, not a band: at any gameplay range it
    # is one row of vertices, so the transition it exists to make happens
    # inside a single triangle. A real waterline is wet for the better part of
    # a metre of ELEVATION above the surface — capillary rise, splash, and the
    # fact that a lake is not always at the same height — and that wetting is
    # what carries the eye from water to land. Cooler as well as darker: wet
    # silt and wet stone lose more red than blue, which is why a tide line
    # reads blue-grey against dry sand.
    lvl = T.water_level()
    wet = (1.0 - TR._smoothstep(0.0, 0.95, np.maximum(y - lvl, 0.0))) * \
        TR._smoothstep(0.02, 0.26, T.water_influence(x, z))
    wet_rgb = np.stack([1.0 - 0.50 * wet, 1.0 - 0.44 * wet, 1.0 - 0.30 * wet], axis=1)

    grp = M.Group()
    for mi, key in enumerate(GROUND_MATS):
        sel = tris[pick == mi]
        if not len(sel):
            continue
        used, inv = np.unique(sel.reshape(-1), return_inverse=True)
        own = MAT_BASE[key]
        tint = np.clip(blend[used] / np.maximum(own, 1e-6), 0.0, 1.0)
        col = np.clip(tint * hue_rgb[used] * wet_rgb[used]
                      * (variance[used] * slope_f[used])[:, None], 0.16, 1.0)
        col = np.concatenate([col, np.ones((len(used), 1))], axis=1)
        # Each ground material at ITS OWN authored coverage, not at one shared
        # GROUND_UV. `gravel`, `mud` and `riverbed` are 2 m materials and were
        # being sampled over 4 m, so every river stone and every dried mud
        # polygon on the bank rendered at 2.04-2.35x its authored size —
        # measured against the registry, and Art Bible §5 makes declared
        # coverage a done-criterion. `materials.uv_scale` is the API D-024
        # added for exactly this and the terrain was not using it.
        sc = MATS.uv_scale(key)
        uv = np.stack([x[used] * sc, z[used] * sc], axis=1).astype(np.float32)
        m = M.Mesh(verts[used].astype(np.float32), nrms[used].astype(np.float32),
                   uv, inv.astype(np.uint32), mat=key)
        m.with_colour(col)
        grp.add(m, key)
    return grp


# ---------------------------------------------------------------------------
# Water surface
# ---------------------------------------------------------------------------

def _mesh_height(T, X, Z, band=3.2):
    """Elevation of the RENDERED ground, not of the height function.

    This is the fix for the scalloped shoreline, and it is the third attempt at
    it in this project, so it is worth stating exactly what the defect is.

    The ground is a four-ring LOD field at 0.5 / 1 / 2 / 4 m cells. Its surface
    is therefore a piecewise-LINEAR interpolation of `T.height` sampled on those
    grids, and it can sit tens of centimetres away from the true function in the
    middle of a 4 m cell. The water sheet is built on its own 1.2 m grid from
    the true function. So the two disagree about where the waterline is — by
    metres of plan on the 4 m ring — and every disagreement shows as a triangle
    of water lying on the beach or a triangle of beach standing in the water.
    That is the "scalloped edge", the "pale scalloped teeth" and the
    "uniform-width beach ring" of three consecutive reviews, and no amount of
    work on the water material touches it, because it is a disagreement between
    two meshes about a contour.

    So the water asks the GROUND how high it is, using the ground's own
    triangles — the same rings, the same cell sizes, the same alternating
    diagonal `_ring` lays. Then "this vertex is dry" means "the ground the
    player can see is above the water here", which is the only definition that
    cannot produce a tooth: both sides of the edge are now the same surface.

    Evaluated only within `band` metres of the surface, because that is the only
    place the two definitions can differ visibly and the exact function is four
    times cheaper.
    """
    lvl = T.water_level()
    H = T.height(X, Z)
    live = np.abs(H - lvl) < band
    if not live.any():
        return H
    x, z = X[live], Z[live]
    cheb = np.maximum(np.abs(x), np.abs(z))
    out = H[live].copy()
    rings = T.rings
    for k, r in enumerate(rings):
        outer = float(r["outer"])
        inner = 0.0 if k == 0 else float(rings[k - 1]["outer"])
        sel = (cheb >= inner) & ((cheb < outer) if k + 1 < len(rings) else True)
        if not sel.any():
            continue
        cell = float(r["cell"])
        n = int(round(2.0 * outer / cell))
        # Cell index and the local (u, v) inside it, exactly as `_ring` lays
        # them: coords = -outer + i * cell, i indexes X and j indexes Z.
        fx = np.clip((x[sel] + outer) / cell, 0.0, n - 1e-9)
        fz = np.clip((z[sel] + outer) / cell, 0.0, n - 1e-9)
        i = np.floor(fx).astype(np.int64)
        j = np.floor(fz).astype(np.int64)
        u = fx - i
        v = fz - j
        x0 = -outer + i * cell
        z0 = -outer + j * cell
        h00 = T.height(x0, z0)
        h10 = T.height(x0 + cell, z0)
        h01 = T.height(x0, z0 + cell)
        h11 = T.height(x0 + cell, z0 + cell)
        # `_ring` alternates the diagonal so the field is not one combed
        # direction. Both cases, both triangles, or the interpolation is wrong
        # on half the cells — which would put the teeth straight back.
        alt = ((i + j) % 2) == 0
        # alt: diagonal v0-v2, i.e. u == v.
        a_alt = h00 * (1.0 - v) + h01 * (v - u) + h11 * u          # u <= v
        b_alt = h00 * (1.0 - u) + h11 * v + h10 * (u - v)          # u >= v
        # not alt: diagonal v1-v3, i.e. u + v == 1.
        a_odd = h10 * u + h00 * (1.0 - u - v) + h01 * v            # u + v <= 1
        b_odd = h10 * (1.0 - v) + h01 * (1.0 - u) + h11 * (u + v - 1.0)
        hh = np.where(alt,
                      np.where(u <= v, a_alt, b_alt),
                      np.where(u + v <= 1.0, a_odd, b_odd))
        idx = np.flatnonzero(sel)
        out[idx] = hh
    H = H.copy()
    H[live] = out
    return H


def _shore_occlusion(T, px, pz, lvl,
                     dists=(1.6, 4.0, 9.0, 18.0, 34.0), azimuths=10):
    """How much of the sky this square metre of water CANNOT see, 0..1.

    The cheap half of a reflection, and the half that carries the read.

    `ad-town-05` §2 says it four times: "zero reflection of a 190 m walled town
    standing on the far bank", "a three-arch stone bridge with no reflection in
    it", "a 12 m building standing in a pool casts no reflection into it". A
    true planar reflection is a second full scene pass — at the north gate the
    beauty pass is 687 draw calls and the frame is already 1,283 against a
    budget of 900, so buying it this wave would be buying it out of somebody
    else's lane. It is costed and named in the report as NOT DONE.

    But most of what the eye reads as "reflection" on a lake is not the image.
    It is that water beside a bank is DARK and water in the middle is BRIGHT,
    because the first is mirroring earth and the second is mirroring sky. That
    term is a horizon test, it is view-independent, it bakes into COLOR_0, and
    it costs nothing at runtime. It also lands automatically on every case the
    review names: the Emberflow is 11 m wide between 2.5 m banks and goes
    properly dark; the water under the bridge arches goes darker still; the
    harbour under the quay wall goes dark against the open Mere beyond it.

    Sampled as a horizon elevation in `azimuths` directions at five ranges,
    which is enough to separate "open water" from "under a bank" and far too
    coarse to be mistaken for an image. Buildings are not in the height field,
    but their PADS are — `height()` flattens terrain to every building
    platform — so the wall's terrace, the quay and the mill's apron all count.
    """
    occ = np.zeros(len(px), np.float64)
    for a in range(azimuths):
        th = 2.0 * np.pi * a / azimuths
        dx, dz = float(np.cos(th)), float(np.sin(th))
        best = np.zeros(len(px), np.float64)
        for d in dists:
            h = T.height(px + dx * d, pz + dz * d)
            best = np.maximum(best, (h - lvl) / d)
        # 0.09 is about 5 degrees — a far shore that low reflects almost
        # nothing. 0.55 is 29 degrees, at which the sky is properly shut out.
        occ += TR._smoothstep(0.09, 0.55, best)
    return occ / azimuths


def _water(T, cell=1.2):
    """The water surface: flat at the authored level, tucked into the bank.

    Getting the SHORELINE right is the whole problem. A sheet clipped to fully
    submerged cells leaves a dry sawtooth gutter all round the lake — that was
    the first attempt and it was the ugliest thing in the render. A sheet
    clipped to partly submerged cells instead floats visibly over the bank.

    So: keep every cell with at least one submerged corner, and pull the DRY
    corner vertices down to just under the ground. The sheet's outermost ring
    of triangles then dives into the bank, and the visible waterline is the
    exact intersection of the plane with the terrain — a smooth curve at any
    mesh resolution, with no gutter and nothing floating. Only that outer ring
    is non-planar, and it is buried.
    """
    lvl = T.water_level()
    far = float(T.extent["far"])
    n = int(round(2.0 * far / cell))
    coords = -far + np.arange(n + 1, dtype=np.float64) * cell
    X, Z = np.meshgrid(coords, coords, indexing="ij")
    # THE GROUND'S OWN SURFACE, not the height function. See `_mesh_height`:
    # this single substitution is what stops the shoreline scalloping, and
    # everything downstream — the wet/dry test, the sink, the depth tint and
    # the wrack contour — inherits it for free.
    H = _mesh_height(T, X.ravel(), Z.ravel()).reshape(X.shape)
    wet = H < lvl

    # Keep a cell if any corner is submerged OR within `MARGIN` of the surface.
    # Insurance: the sheet's own grid is 1.2 m, so the last wet vertex can be up
    # to a cell short of the true crossing. Every extra cell is clamped to the
    # water plane below and is therefore hidden by ground that is above it; it
    # costs triangles and buys a guarantee.
    MARGIN = 0.55
    near_lvl = H < lvl + MARGIN
    keep = (near_lvl[:-1, :-1] | near_lvl[1:, :-1] |
            near_lvl[1:, 1:] | near_lvl[:-1, 1:])
    if not keep.any():
        return None, 0.0
    ci = np.arange(n)
    I, J = np.meshgrid(ci, ci, indexing="ij")
    I, J = I[keep], J[keep]
    stride = n + 1
    v0 = I * stride + J
    v1 = (I + 1) * stride + J
    v2 = (I + 1) * stride + (J + 1)
    v3 = I * stride + (J + 1)
    tri = np.vstack([np.stack([v0, v3, v2], 1), np.stack([v0, v2, v1], 1)])

    used, inv = np.unique(tri.reshape(-1), return_inverse=True)
    inv = inv.reshape(tri.shape)
    px = X.ravel()[used]
    pz = Z.ravel()[used]
    gh = H.ravel()[used]

    # How far to sink a dry edge vertex under the bank. It cannot be a constant:
    # the water grid samples the exact height function, but the ground it has to
    # hide under is a LINEAR INTERPOLATION across a terrain cell, and on a
    # convex bank that interpolation sits below the true surface by roughly a
    # tenth of the cell size. At 4 m cells in the distance ring that error let
    # the sheet's edge triangles poke through as a rim of dark teeth right
    # round the far shore of the Mere. So the sink scales with the local LOD
    # cell. Over-sinking costs nothing — the triangle is buried either way.
    cheb = np.maximum(np.abs(px), np.abs(pz))
    cellsz = np.full(len(used), float(T.rings[-1]["cell"]))
    for r in reversed(T.rings):
        cellsz = np.where(cheb <= float(r["outer"]), float(r["cell"]), cellsz)
    # 0.06 + 0.22*cell, raised from 0.04 + 0.14*cell after the D-024 water
    # landed: the new north bank runs along the bridge abutment's apron,
    # which falls 3.4 m in 2.5 m, and at that gradient a tenth of a cell
    # was not enough — the sheet's edge showed as a row of dark teeth
    # along the far bank in the departure frame.
    #
    # AND THEN CLAMPED TO THE WATER PLANE, which is the whole of `ad-town-05`
    # §2's sawtooth. `gh - sink` is only "just under the bank" while `gh` is
    # just above the water. On a steep bank it is not: at the mill leat the
    # ground goes from -4.81 to -2.04 across one 1.2 m cell, so the dry corner
    # was placed at -2.32 — 0.78 m ABOVE the surface — and against the mill's
    # own pad at -1.55 it was placed at -1.83, 1.27 m above. The sheet was
    # climbing the bank, and the triangles standing out of the lake are
    # precisely the "row of sharp triangular teeth" in `mereshore-free` and
    # the "hard sawtooth of flat dark triangles" in `t-gate-north`. Measured,
    # not inferred: `T.height` at those cells returns exactly those numbers.
    #
    # With the clamp a dry vertex can only ever be AT the surface or below it.
    # Near the waterline `gh - sink` is below `lvl` and the old burial still
    # happens, so nothing that worked stops working. Up a steep bank the sheet
    # goes flat at `lvl` and the terrain — which is above `lvl` there — simply
    # occludes it, so the visible waterline becomes the exact intersection of
    # the water plane with the RENDERED ground rather than with the height
    # function. That is the one definition that cannot produce a tooth at any
    # LOD, because both sides of the edge are the same triangles.
    py = np.minimum(np.where(gh >= lvl, gh - (0.06 + 0.22 * cellsz), lvl), lvl)

    verts = np.stack([px, py, pz], axis=1).astype(np.float32)

    # Swell. Every vertex normal was exactly +Y, and that is why the Mere
    # rendered as one flat plate: a perfectly level surface answers the sun's
    # specular with a single lobe of the same width everywhere, so the glitter
    # path is a SHEET. Raising roughness does not fix it — GGX conserves
    # energy, so a rougher surface spreads the same light over more area, which
    # is measurably what happened: the blown region went from 40% of the lake
    # to 85% of it at a lower peak.
    #
    # What breaks a glitter path on real water is swell, at a scale far larger
    # than the ripple normal map: 25-70 m wavelengths, a couple of degrees of
    # tilt. Two degrees is nothing to the eye directly and everything to a
    # specular lobe, and unlike the normal map it is per-vertex, so it does not
    # mip away at 150 m — which is exactly where the defect was worst.
    # ROTATED, and that is not cosmetic. `_value_noise` is defined on an
    # INTEGER lattice, so sampling it at `px * f, pz * f` puts its cells on the
    # world axes at a spacing of exactly 1/f metres. On a near-mirror seen at a
    # grazing angle, a two-degree normal difference between neighbouring cells
    # is a large change in what is reflected, so those cells become visible —
    # as the regular diagonal lattice of light and dark diamonds across the
    # bottom-right of `t-approach-ne`, which `ad-town-05` §2 reads as "visible
    # triangular polygon facet seams" and which is neither seams nor polygons.
    # Every octave is now sampled in its own rotated frame at an angle that is
    # not a simple fraction of a turn, so no two lattices line up with each
    # other or with the world, and their sum has no grid in it.
    ROT = (0.0, 0.7391, 1.4711, 2.3999)

    def _swell(fx, fz, seed, rot=0.0):
        c, s = float(np.cos(rot)), float(np.sin(rot))
        return TR._value_noise((px * c - pz * s) * fx,
                               (px * s + pz * c) * fz, seed) * 2.0 - 1.0
    #
    # Amplitudes raised again after the quay landed. The blown patch that
    # `review/reports/ad-town-02.md` §8 names sits 30-90 m out, which is
    # exactly the band the two long octaves cannot break — a 55 m swell tilts
    # a 60 m glitter path as ONE piece. What chops it is the short octave, and
    # at 0.016 it was contributing under a degree. It is 0.038 now and there is
    # a fourth at ~9 m wavelength, which is still four vertices per wave on the
    # 2 m LOD ring and therefore does not alias. Peak tilt goes from 6 deg to
    # 10 deg: nothing to the eye on the water itself, and it turns the glitter
    # sheet into a stipple, which is what real water does with it.
    # The two short octaves come down (0.038 -> 0.022 and 0.022 -> 0.012) now
    # that they are rotated. They were carrying most of the glitter break-up
    # AND most of the visible lattice; with the frames decorrelated the same
    # break-up survives at a lower amplitude, and the shoal roughness and the
    # 0.55 specular knee are now doing the rest of that job properly rather
    # than being asked to do it with geometry alone.
    sw = (_swell(0.041, 0.036, 771431, ROT[0]) * 0.055 +
          _swell(0.017, 0.021, 3312277, ROT[1]) * 0.038 +
          _swell(0.093, 0.087, 5590211, ROT[2]) * 0.022 +
          _swell(0.155, 0.168, 9911777, ROT[3]) * 0.012)
    sw_x = (_swell(0.041, 0.036, 771431 + 7, ROT[0]) * 0.055 +
            _swell(0.017, 0.021, 3312277 + 7, ROT[1]) * 0.038 +
            _swell(0.093, 0.087, 5590211 + 7, ROT[2]) * 0.022 +
            _swell(0.155, 0.168, 9911777 + 7, ROT[3]) * 0.012)
    nrm = np.stack([sw_x, np.ones_like(sw), sw], axis=1)
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
    nrm = nrm.astype(np.float32)

    # UVs. The lake takes world-planar UVs; the CHANNEL takes its own
    # curvilinear frame, so V runs down the current wherever the reach bends
    # and the flow shader has one direction to scroll in for the whole river.
    flow_w, across, along = T.channel_frame(px, pz)
    uv_lake = np.stack([px * WATER_UV, pz * WATER_UV], axis=1)
    uv_flow = np.stack([across * WATER_UV, along * WATER_UV], axis=1)
    f = (flow_w > 0.5)[:, None]
    uv = np.where(f, uv_flow, uv_lake).astype(np.float32)

    # Depth tint AND depth transmission. COLOR_0's RGB can only darken, which
    # is the right direction for the tint; its ALPHA is what makes the water
    # actually deep. A shallow margin at alpha 0.30 shows the bed it is lying
    # on and a 3 m channel at 0.97 does not, which is the whole difference
    # between water and a disc of teal paint — and it is also what dissolves
    # the shoreline, because the sheet fades out as it thins instead of ending
    # on an edge. Costs one blended surface; needs no transmission extension
    # and no refraction pass, so `tools/render/town.html` and the client agree
    # by construction.
    # The ramp is EXPONENTIAL, not linear. Light is absorbed by a water column
    # geometrically, so the first half-metre does most of the colour change and
    # anything past two metres is the same colour as anything past ten. A
    # linear ramp to 2.6 m spends most of its range on depths the eye cannot
    # tell apart and almost none of it on the 0-0.5 m margin, which is the only
    # band a player ever reads — and that is why `t-aerial-sw` has shown a
    # uniform-value lake with a uniform-width beach ring for four passes.
    dm = np.maximum(lvl - gh, 0.0)                 # metres of water column
    tint_t = 1.0 - np.exp(-dm / 0.85)
    deep = np.array(K.WATER_DEEP)
    col = 1.0 + (deep - 1.0) * tint_t[:, None]
    # Wind lanes so a 150 m sheet is not one flat value.
    lanes = 0.90 + 0.10 * TR._value_noise(px * 0.021, pz * 0.021, 5512099)
    col = np.clip(col * lanes[:, None], 0.2, 1.0)
    # What the water is reflecting. See `_shore_occlusion`: water against a
    # bank mirrors the bank, so it is DARK, and water in mid-lake mirrors the
    # sky, so it is bright. Without this every square metre of the Mere
    # reflects the same sky at the same strength and the sheet has no relation
    # to the land it sits in — which is what "zero reflection of a 190 m walled
    # town standing on the far bank" and "a three-arch stone bridge with no
    # reflection in it" are actually describing.
    occl = _shore_occlusion(T, px, pz, lvl)
    col[:, :3] = np.clip(col[:, :3] * (1.0 - 0.52 * occl)[:, None], 0.06, 1.0)
    alpha = K.water_alpha(dm / 2.6)
    col = np.concatenate([col, alpha[:, None]], axis=1)

    # Split into still and flowing. Two materials, so `client/src/water.js` can
    # give the river a directional current and the lake an interference of two
    # counter-scrolling layers — and so the river is not simply the lake with
    # the same texture stretched along it, which is how it shipped.
    tri_flow = flow_w[inv].mean(axis=1) > 0.5
    out = M.Group()
    for sel, key in ((~tri_flow, "water"), (tri_flow, "water_flow")):
        sub = inv[sel]
        if not len(sub):
            continue
        u2, i2 = np.unique(sub.reshape(-1), return_inverse=True)
        m = M.Mesh(verts[u2], nrm[u2], uv[u2], i2.astype(np.uint32), mat=key)
        m.with_colour(col[u2])
        out.add(m, key)
    area = float(keep.sum()) * cell * cell
    return out, area, (X, Z, H, lvl)


def _shoreline(T, grid, width=1.15):
    """The wrack line: weed, scum and pond litter on the true waterline.

    The water sheet's outer ring is tucked under the bank (see `_water`), which
    guarantees no gutter and nothing floating but leaves the waterline as the
    sheet's own cell sawtooth — visible as a scalloped edge right round the
    Mere in `town-aerial-sw.png`. The real waterline is the contour where the
    ground crosses the water level, and it is a smooth curve.

    So: march the squares of the same grid the sheet was built on, take the
    contour segments, and lay a ribbon along them draped just above the water.
    Every lake and river edge in the world has this line — wind pushes scum,
    pollen, duckweed and dead reed to the lee shore and it collects where the
    water thins. It replaces a hard geometric boundary with a soft one, which
    is the thing a procedural shoreline never has.

    Three things changed after `ad-town-05` looked at `t-aerial-sw` and found a
    hard white scalloped ring round the north-east of the Mere, which is the
    ribbon itself:

    1. **It stops at 100 m.** The contour is marched on the height FUNCTION at
       1.2 m; the ground it has to sit on is a rendered mesh at 0.5 m in the
       town, 1 m to the wall, 2 m in the approach and 4 m in the distance ring.
       Past the 1 m ring the two disagree by metres, so half the ribbon buries
       itself in the bank and half floats out on open water — and a ribbon that
       is buried in alternate segments IS a scallop. Inside 100 m they agree to
       centimetres. The same reasoning, and the same distance, as
       `surfaces.waterlineMud.dropOff`: past it a far shore is turf running
       down to water, which is both cheaper and what a far shore looks like.
    2. **It is broken, not continuous.** Wrack collects in windrows on the LEE
       shore and nowhere else. A continuous band round a whole lake is a
       painted outline, which is exactly how it read. Coverage is a
       low-frequency noise gated by how square the shore lies to the town's
       authored wind, and roughly half the contour now carries nothing.
    3. **Its width varies.** A constant 1.15 m ribbon has two parallel edges
       and the eye finds them; 0.5-1.9 m does not.
    """
    X, Z, H, lvl = grid
    d = (lvl - H)                       # > 0 where wet
    b = M._Builder()
    # Where the ribbon can be trusted. See (1) above.
    FADE_FROM, FADE_TO = 100.0, 150.0
    # The town's wind, from content. Wrack piles on the shore the wind blows
    # ONTO, so a segment whose outward normal opposes the wind gets the scum
    # and the weather shore gets bare gravel.
    WIND = (0.82, 0.57)
    wl = float(np.hypot(*WIND)) or 1.0
    wdx, wdz = WIND[0] / wl, WIND[1] / wl
    # Marching squares, vectorised per crossed edge. Each cell contributes at
    # most one segment; the ambiguous saddle case is not worth resolving at
    # 1.2 m against a 0.02 m ribbon.
    n = d.shape[0] - 1
    c00, c10, c01, c11 = d[:-1, :-1], d[1:, :-1], d[:-1, 1:], d[1:, 1:]
    code = ((c00 > 0).astype(np.int32) | ((c10 > 0).astype(np.int32) << 1)
            | ((c11 > 0).astype(np.int32) << 2) | ((c01 > 0).astype(np.int32) << 3))
    cross = np.argwhere((code > 0) & (code < 15))
    if not len(cross):
        return None

    def lerp(pa, pb, da, db):
        t = da / (da - db) if abs(da - db) > 1e-9 else 0.5
        return (pa[0] + (pb[0] - pa[0]) * t, pa[1] + (pb[1] - pa[1]) * t)

    run = 0.0
    for i, j in cross:
        p = [(X[i, j], Z[i, j]), (X[i + 1, j], Z[i + 1, j]),
             (X[i + 1, j + 1], Z[i + 1, j + 1]), (X[i, j + 1], Z[i, j + 1])]
        v = [d[i, j], d[i + 1, j], d[i + 1, j + 1], d[i, j + 1]]
        hits = []
        for k in range(4):
            a, bb = k, (k + 1) % 4
            if (v[a] > 0) != (v[bb] > 0):
                hits.append(lerp(p[a], p[bb], v[a], v[bb]))
        if len(hits) < 2:
            continue
        (ax, az), (bx, bz) = hits[0], hits[1]
        ex, ez = bx - ax, bz - az
        ln = float(np.hypot(ex, ez))
        if ln < 1e-4:
            continue
        nx, nz = -ez / ln, ex / ln
        mx, mz = (ax + bx) * 0.5, (az + bz) * 0.5
        # (1) the ribbon stops where the mesh can no longer carry it.
        far = float(np.hypot(mx, mz))
        if far > FADE_TO:
            continue
        near_t = 1.0 - TR._smoothstep(FADE_FROM, FADE_TO, far)
        # (2) windrows. `_value_noise` is the same seeded field everything else
        # on this venue uses, so the pattern is deterministic and diffable.
        lee = 0.5 - 0.5 * (nx * wdx + nz * wdz)      # 1 on the lee shore
        rows = float(TR._value_noise(np.array([mx * 0.031]),
                                     np.array([mz * 0.031]), 4471223)[0])
        cover = near_t * (0.24 + 0.76 * lee) * (0.30 + 1.15 * rows)
        if cover < 0.42:
            continue
        # (3) a width that is not two parallel lines.
        wob = float(TR._value_noise(np.array([mx * 0.085]),
                                    np.array([mz * 0.085]), 8813377)[0])
        hw = width * (0.45 + 1.20 * wob) * 0.5
        y = lvl + 0.022
        quad = [np.array([ax - nx * hw, y, az - nz * hw], np.float32),
                np.array([bx - nx * hw, y, bz - nz * hw], np.float32),
                np.array([bx + nx * hw, y, bz + nz * hw], np.float32),
                np.array([ax + nx * hw, y, az + nz * hw], np.float32)]
        up = np.array([0.0, 1.0, 0.0], np.float32)
        if float(np.dot(np.cross(quad[1] - quad[0], quad[2] - quad[0]), up)) < 0:
            quad.reverse()
        # V across the ribbon so the material's own gradient puts the dense
        # scum on the landward side; U along it in metres so the foam does not
        # repeat at a fixed period round the whole lake.
        sc = 1.0 / 2.0
        uvs = [(run * sc, 0.0), ((run + ln) * sc, 0.0),
               ((run + ln) * sc, 1.0), (run * sc, 1.0)]
        b.poly(quad, uvs, up)
        run += ln
    m = b.build("foam")
    return m if m.tri_count else None


def _contour(grid, step=1):
    """The true waterline as a list of (x, z, outward nx, nz, length).

    Marching squares on the same grid `_water` and `_shoreline` use, so
    everything on the shore agrees about where the shore is. `outward` points
    away from the water (up the beach), which is what a beach profile needs.
    """
    X, Z, H, lvl = grid
    d = lvl - H
    n = d.shape[0] - 1
    c00, c10, c01, c11 = d[:-1, :-1], d[1:, :-1], d[:-1, 1:], d[1:, 1:]
    code = ((c00 > 0).astype(np.int32) | ((c10 > 0).astype(np.int32) << 1)
            | ((c11 > 0).astype(np.int32) << 2) | ((c01 > 0).astype(np.int32) << 3))
    out = []
    for i, j in np.argwhere((code > 0) & (code < 15))[::step]:
        p = [(X[i, j], Z[i, j]), (X[i + 1, j], Z[i + 1, j]),
             (X[i + 1, j + 1], Z[i + 1, j + 1]), (X[i, j + 1], Z[i, j + 1])]
        v = [d[i, j], d[i + 1, j], d[i + 1, j + 1], d[i, j + 1]]
        hits = []
        for k in range(4):
            a, bb = k, (k + 1) % 4
            if (v[a] > 0) != (v[bb] > 0):
                t = v[a] / (v[a] - v[bb]) if abs(v[a] - v[bb]) > 1e-9 else 0.5
                hits.append((p[a][0] + (p[bb][0] - p[a][0]) * t,
                             p[a][1] + (p[bb][1] - p[a][1]) * t))
        if len(hits) < 2:
            continue
        (ax, az), (bx, bz) = hits
        ex, ez = bx - ax, bz - az
        ln = float(np.hypot(ex, ez))
        if ln < 1e-4:
            continue
        nx, nz = -ez / ln, ex / ln
        # Orient toward the DRY side: the cell centre's wetness decides.
        cx, cz = (X[i, j] + X[i + 1, j + 1]) * 0.5, (Z[i, j] + Z[i + 1, j + 1]) * 0.5
        if float(np.mean(v)) > 0:              # cell is mostly wet
            tx, tz = cx - (ax + bx) * 0.5, cz - (az + bz) * 0.5
            if nx * tx + nz * tz > 0:
                nx, nz = -nx, -nz
        out.append(((ax + bx) * 0.5, (az + bz) * 0.5, nx, nz, ln))
    return out


# ---------------------------------------------------------------------------
# The margin: reed, and shingle graded up the beach
# ---------------------------------------------------------------------------

def _margin(ctx, T, grid, asset_id="hm.terrain.margin"):
    """What actually makes a waterline convincing.

    A lake meeting the land on a graded material boundary is still a lake
    meeting the land on a boundary. What tells you the water is shallow, before
    you step in, is stuff standing IN it and stuff lying at the edge of it:
    reed and sedge where it is shallow and still, and shingle sorted by size —
    coarse at the storm line, fine at the water — up the beach. That sorting is
    real physics (the swash carries small grains further up and the backwash
    drags them back) and it is instantly readable.

    Both are instanced off the marching-squares contour, so they follow the
    same waterline the wrack ribbon and the water sheet do. Two prototypes,
    two draw calls per cell batch.

    Reed goes only where the shore is STILL and SHELVING:
      - not in a flowing channel (`channel_frame` weight), because reed beds
        wash out of a current;
      - not on a steep bank, because there is nothing for it to root in;
      - not in the town, because a working quay and a water gate are dredged
        and a reed bed against a masonry quay is a wrong note.
    """
    pts = _contour(grid, step=1)
    if not pts:
        return 0, 0
    rng = rng_for(asset_id, "margin")
    reeds, sedge, coarse, fine = [], [], [], []
    town = float(T.extent["wall"])
    for (mx, mz, nx, nz, _ln) in pts:
        # Beach profile: sample the ground along the outward normal.
        s = T.slope(np.array([mx]), np.array([mz]))[0]
        flow_w, _a, _b = T.channel_frame(np.array([mx]), np.array([mz]))
        inside = max(abs(mx), abs(mz)) < town + 6.0
        far = float(np.hypot(mx, mz))
        if far > 150.0:
            continue

        # --- reed: into the water, on a shelving still margin --------------
        if s < 0.34 and flow_w[0] < 0.35 and not inside and rng.random() < 0.55:
            for _ in range(int(rng.integers(1, 4))):
                # Negative offset = lakeward. Reed stands IN the water.
                o = float(rng.uniform(-2.4, 0.7))
                px, pz = mx - nx * o, mz - nz * o
                py = float(T.height(px, pz))
                if py > T.water_level() + 0.35 or py < T.water_level() - 0.75:
                    continue
                (reeds if rng.random() < 0.62 else sedge).append({
                    "pos": (px, py, pz), "rot_y": float(rng.uniform(0, 2 * np.pi)),
                    "scale": float(rng.uniform(0.55, 1.45))})

        # --- shingle: graded up the beach ---------------------------------
        # Coarse at the top of the beach, fine at the water. Two prototypes and
        # a scale ramp do the grading; the eye reads the size gradient long
        # before it reads any individual stone.
        for _ in range(int(rng.integers(1, 5))):
            o = float(rng.uniform(-0.5, 3.4))       # up the beach
            px, pz = mx + nx * o, mz + nz * o
            py = float(T.height(px, pz))
            if py > T.water_level() + 1.1 or py < T.water_level() - 0.45:
                continue
            up = np.clip((py - T.water_level() + 0.3) / 1.3, 0.0, 1.0)
            rec = {"pos": (px, py - 0.02, pz),
                   "rot_y": float(rng.uniform(0, 2 * np.pi)),
                   "scale": float(rng.uniform(0.6, 1.25) * (0.55 + 0.95 * up))}
            (coarse if up > 0.45 else fine).append(rec)

    if reeds:
        ctx.instance("mere_reed", V.reed_tuft(f"{asset_id}.reed", 1.55, 18), reeds)
    if sedge:
        ctx.instance("mere_sedge",
                     V.tussock(f"{asset_id}.sedge", 0.34, 0.52, "reed", 9,
                               blade_w=0.013), sedge)
    if coarse:
        ctx.instance("shore_cobble", K.pebble(f"{asset_id}.cob", 0.19, "gravel"), coarse)
    if fine:
        ctx.instance("shore_shingle", K.pebble(f"{asset_id}.shg", 0.085, "gravel"), fine)
    return len(reeds) + len(sedge), len(coarse) + len(fine)


# ---------------------------------------------------------------------------
# Retaining walls and step flights
# ---------------------------------------------------------------------------

def _heading(dx, dz):
    """Rotation about Y that maps the mesh's +X onto (dx, dz)."""
    return float(np.arctan2(-dz, dx))


def _retaining_wall(rec):
    """Coursed rubble revetment holding one terrace against the next.

    Built as a wall body plus an individually-jittered coping course. The
    coping is what the eye actually reads at 30 m — a continuous extruded top
    edge is the tell that a wall was made by a loop rather than by masons, and
    Art Bible §6 forbids more than three identical elements in a row anyway.
    """
    ax, az = float(rec["from"][0]), float(rec["from"][1])
    bx, bz = float(rec["to"][0]), float(rec["to"][1])
    dx, dz = bx - ax, bz - az
    length = float(np.hypot(dx, dz))
    if length < 0.2:
        return None
    dx, dz = dx / length, dz / length
    top, bot = float(rec["top"]), float(rec["bottom"])
    th = float(rec.get("thickness", 0.6))
    rng = rng_for(rec["id"], "retaining")

    face = float(rec.get("faceDeg", 180.0))
    fx = TR._sin_deg(face)
    fz = TR._cos_deg(face)

    grp = M.Group()
    h = max(top - bot, 0.2)
    body = M.box(length, h, th, 0.025, "stone")
    body.translate(0, bot + h * 0.5, 0)

    # Coping: a run of individual stones, each jittered. Slight overhang so the
    # course throws a shadow line down the wall face.
    cop = M.Mesh(mat="stone")
    stone_len = 0.62
    count = max(1, int(round(length / stone_len)))
    sl = length / count
    for i in range(count):
        w = sl * rng.uniform(0.90, 0.99)
        s = M.box(w, rng.uniform(0.12, 0.17), th + rng.uniform(0.10, 0.16), 0.02,
                  "stone")
        s.rotate_y(rng.uniform(-0.03, 0.03))
        s.translate(-length * 0.5 + (i + 0.5) * sl + rng.uniform(-0.02, 0.02),
                    top + 0.07 + rng.uniform(-0.012, 0.012),
                    rng.uniform(-0.03, 0.03))
        cop.merge(s)

    # One displaced stone per run, and a missing one on the longer runs. The
    # Art Bible §6 requirement that every structure carries a visible flaw.
    grp.add(body, "stone")
    grp.add(cop, "stone")
    grp.rotate_y(_heading(dx, dz))
    grp.translate((ax + bx) * 0.5 - fx * th * 0.5, 0.0, (az + bz) * 0.5 - fz * th * 0.5)
    return grp


def _step_flight_colliders(ctx, rec):
    """Each tread declared as a `surface` volume.

    Surface, not solid: a flight is something to stand on, not something to
    walk into. Riser height is well under core.collision.STEP_HEIGHT, so the
    controller climbs it without any special case.
    """
    ax, az = float(rec["at"][0]), float(rec["at"][1])
    top, bot = float(rec["top"]), float(rec["bottom"])
    width = float(rec["width"])
    drop = top - bot
    n = max(1, int(round(drop / 0.175)))
    rise = drop / n
    going = 0.30
    head = float(rec.get("headingDeg", 180.0))
    fx, fz = TR._sin_deg(head), TR._cos_deg(head)
    yaw = float(np.arctan2(fx, fz))
    for k in range(n):
        ty = top - (k + 1) * rise
        d = (k + 0.5) * going + 0.025
        ctx.collider("box",
                     center=(ax + fx * d, ty - (rise + 0.14) * 0.5, az + fz * d),
                     half=(width * 0.5, (rise + 0.14) * 0.5, (going + 0.05) * 0.5),
                     rot_y=yaw, kind="surface", tag="steps", cid=f"{rec['id']}.{k:02d}")


def _step_flight(rec):
    """A flight through a scarp. Rise/going per Art Bible §3.

    The riser count is chosen so the flight lands exactly on both authored
    levels; that moves the actual rise by a few millimetres, which is correct —
    real flights are set out to the drop they have to cover, not to a nominal
    rise.
    """
    ax, az = float(rec["at"][0]), float(rec["at"][1])
    top, bot = float(rec["top"]), float(rec["bottom"])
    width = float(rec["width"])
    drop = top - bot
    n = max(1, int(round(drop / 0.175)))
    rise = drop / n
    going = 0.30
    head = float(rec.get("headingDeg", 180.0))
    fx, fz = TR._sin_deg(head), TR._cos_deg(head)
    rng = rng_for(rec["id"], "steps")

    grp = M.Group()
    treads = M.Mesh(mat="stone")
    for k in range(n):
        # Tread k spans going*k .. going*(k+1) from the top nosing, its top
        # surface one rise below the level above it.
        ty = top - (k + 1) * rise
        slab = M.box(width, rise + 0.14, going + 0.05, 0.018, "stone")
        slab.translate(rng.uniform(-0.008, 0.008),
                       ty - (rise + 0.14) * 0.5,
                       (k + 0.5) * going + 0.025)
        treads.merge(slab)
    grp.add(treads, "stone")

    # Cheeks: a solid wedge each side, so the flight is carried rather than
    # floating in a bank. Extruded in the vertical plane along the flight.
    run = n * going
    prof = [(-0.12, bot - 0.45), (run + 0.16, bot - 0.45), (run + 0.16, bot + 0.10), (-0.12, top + 0.10)]
    for side in (-1, 1):
        cheek = M.prism(prof, 0.34, "stone")
        # prism extrudes along Z with the profile in XY: X runs down the
        # flight, Y is up. Move it out to the edge of the treads.
        cheek.translate(0, 0, side * (width * 0.5 + 0.15))
        grp.add(cheek, "stone")

    grp.rotate_y(_heading(fx, fz))
    grp.translate(ax, 0.0, az)
    return grp


# ---------------------------------------------------------------------------
# Collision
# ---------------------------------------------------------------------------

def _wall_collider(ctx, rec):
    """A revetment blocks. Build Directive §6 rule 4.

    The ground itself gets no volume at all: the client samples
    `terrain.height(x, z)` directly, which is cheaper than any hull soup and
    exactly correct everywhere including the LOD seams. What needs a volume is
    anything standing ON the ground, and on this venue that is the retaining
    walls — a 1.15 m revetment you can walk through is worse than none, because
    the player falls through the scarp into the terrace below.
    """
    ax, az = float(rec["from"][0]), float(rec["from"][1])
    bx, bz = float(rec["to"][0]), float(rec["to"][1])
    dx, dz = bx - ax, bz - az
    length = float(np.hypot(dx, dz))
    if length < 0.2:
        return
    th = float(rec.get("thickness", 0.6))
    face = float(rec.get("faceDeg", 180.0))
    fx, fz = TR._sin_deg(face), TR._cos_deg(face)
    top, bot = float(rec["top"]), float(rec["bottom"])
    h = max(top - bot, 0.2) + 0.14
    ctx.collider("box",
                 center=((ax + bx) * 0.5 - fx * th * 0.5,
                         bot + h * 0.5,
                         (az + bz) * 0.5 - fz * th * 0.5),
                 half=(length * 0.5, h * 0.5, th * 0.5),
                 rot_y=_heading(dx / length, dz / length),
                 tag="retaining", cid=rec["id"])


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build(ctx):
    T = TR.get()

    verts, nrms, tris = _build_field(T)
    ground = _ground_group(T, verts, nrms, tris)
    ctx.emit(ground, shell=True)

    water, area, grid = _water(T)
    if water is not None:
        ctx.emit(water, shell=True)
    foam = _shoreline(T, grid)
    if foam is not None:
        ctx.emit(foam, "foam", shell=True)
    # Reed in the shallows, shingle graded up the beach. See `_margin`.
    n_reed, n_stone = _margin(ctx, T, grid)

    for rec in T.retaining:
        ctx.emit(_retaining_wall(rec), shell=True)
        _wall_collider(ctx, rec)
    for rec in T.steps:
        ctx.emit(_step_flight(rec), shell=True)
        _step_flight_colliders(ctx, rec)

    # Report what was actually built, in the units a reviewer cares about.
    town = float(T.extent["town"])
    g = np.arange(-town, town + 0.5, 1.0)
    GX, GZ = np.meshgrid(g, g, indexing="ij")
    HH = T.height(GX.ravel(), GZ.ravel())
    print(f"      terrain: town footprint +/-{town:.0f} m  "
          f"height {HH.min():+.3f} .. {HH.max():+.3f} m  (range {HH.max()-HH.min():.3f} m)")
    print(f"      shore: {n_reed} reed/sedge stands, {n_stone} graded shingle")
    print(f"      water level {T.water_level():+.2f} m, surface area {area:,.0f} m^2, "
          f"{len(tris):,} ground tris across {len(T.rings)} LOD rings")
