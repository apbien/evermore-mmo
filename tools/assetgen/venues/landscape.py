"""Landscape — the natural layer, inside the wall and out.

Hearthmere had 576 m of ground and not one tree, hedge, fence or planted bed on
it. Two things follow from that and both are visible from the air: the walled
town read as a uniform brown blob because nothing broke it up, and its edge
followed nothing because the land outside was an unmarked green field with a
settlement dropped on it. A real town's plan is legible precisely because of
what this module builds — plot boundaries inside the wall and field boundaries
outside it.

`core/vegetation.py` owns the shapes. This module owns *where*, and it invents
no layout: every position here is derived from data that was already authored.

    buildingSlots[]  94 plots. A back plot is derived per slot from the
                     building's own footprint and the street it fronts, and the
                     boundary round it is what makes docs/areas/hearthmere/plan/schedule.md
                     legible on the ground.
    openLots[]       the orchard, the churchyard, the two kitchen gardens, the
                     working yards. Authored polygons, planted to their `kind`.
    streets[]        verges, street trees, and the keep-out that stops a hedge
                     growing across Ford Road.
    wall.path        the boundary the field system runs up to.
    terrain.json     the water channels — the meadow is where the Emberflow is,
                     not where it would be convenient.

Everything is seeded from its own id, sits on `terrain.height`, and — except
the four hero pieces — is instanced with an authored LOD chain, because a town's
planting is the textbook instancing case and a naive tree implementation would
eat the whole §7 draw-call budget by itself.
"""

from __future__ import annotations

import json
import math
import os

import numpy as np

from core import collision as COL
from core import kit as K
from core import materials as MATS
from core import mesh as M
from core import terrain as TERR
from core import vegetation as V
from core.mathx import rng_for, seed_from, smoothstep
from core.venue import VenueContext, REPO

NAME = "landscape"
CELLS = []          # the natural layer underlies every cell and belongs to none

# Batched on a 48 m module rather than core's 16 m, and this is the single
# most consequential number in the file.
#
# This layer is genuinely everywhere — 576 m of it — and almost all of it is
# cheap, thin geometry: a hedge is 16 triangles a metre. Cell batching trades
# draw calls for culling granularity, and for geometry this thin the trade runs
# the wrong way: measured at 32 m the natural layer occupied 238 cells and cost
# 465 draw calls at LOD0, more than every building in Hearthmere put together,
# to cull hedges that are two triangles each. 48 m is three town cells exactly,
# so the partition still nests inside the 16 m grid, and it takes the same
# content to well under half that.
CELL_SIZE = 48.0

TOWN = os.path.join(REPO, "content/town/hearthmere.json")

# Land bands, measured from the town centre. The wall sits at ~80 m.
#
# WOOD_INNER is set so the nearest distance tree is over 100 m from anywhere a
# player can stand, because a distance tree is an LOD3 mass and nothing else. At
# 168 m the treeline stood 76 m from the water meadow and rendered as a row of
# twenty-metre faceted green crystals across the whole northern sky. The rule is
# the LOD table's: impostors start at 100 m, so the wood starts at wall + 100.
FIELD_INNER = 96.0        # first hedged field boundary outside the town
FIELD_OUTER = 198.0       # last one; beyond this is the wooded ring
WOOD_INNER = 206.0
WOOD_OUTER = 276.0        # terrain extent is 288; the wood stops short of it

WATER_MARGIN = 0.35       # a plant this far above the surface is not in the river

# Metres of clear ground either side of the carriageway on a road leaving the
# town, in which no standard tree may grow. 8 m puts the nearest bole outside a
# 9 m canopy's reach of the centreline, which is what stops a hedgerow oak
# closing over the road — and over the camera standing on it. See
# `Keepout.open_road`.
HIGHWAY_CLEAR = 8.0

# The roads that LEAVE. Not "every street whose far end is past 62 m" — the
# Bailey is an internal ring that touches 80 m at its east end, and testing by
# radius took the two Bailey trees, which are two of the six trees inside the
# whole wall. These three are the same set `_approach` gives a ditched verge to.
HIGHWAYS = ("ford_road", "mere_street", "tan_road")


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

def _load():
    with open(TOWN) as f:
        town = json.load(f)
    with open(os.path.join(REPO, "content/town/terrain.json")) as f:
        town["_terrain"] = json.load(f)
    for st in town.get("streets", []):
        st["_path"] = [(float(p[0]), float(p[-1])) for p in st["path"]]
    return town


def _ground(x, z):
    """Terrain height, vectorised. Scalar in, scalar out."""
    return TERR.height(x, z)


class Keepout:
    """Where nothing may be planted.

    Buildings, made roads, the wall line, the working yards and open water. A
    vectorised test, because the meadow and the field system scatter tens of
    thousands of candidate points and a per-point Python loop over 94 building
    polygons and 15 streets takes minutes.
    """

    def __init__(self, town, slot_pad=1.2, lot_pad=0.5, road_pad=1.1,
                 wall_half=3.4):
        # Two instances of this are built. The generous one decides where a tree
        # or a bed may go — nothing should be planted within a metre of a wall
        # it would clip. The tight one decides how far back a PLOT reaches, and
        # it has to be tight, because a burgage plot's whole character is that
        # it runs to within a foot of its neighbour's.
        self.polys = []
        for s in town.get("buildingSlots", []):
            self.polys.append((np.asarray(s["polygon"], np.float64), slot_pad))
        for lot in town.get("openLots", []):
            # A working yard is a surface people and carts use. The orchard,
            # graveyard and gardens are the opposite — they are the reason this
            # module exists — so they are not keep-outs.
            if lot["kind"] in ("yard", "quay", "midden"):
                self.polys.append((np.asarray(lot["poly"], np.float64), lot_pad))
        mp = town.get("marketPlace", {}).get("polygon")
        if mp:
            self.polys.append((np.asarray(mp, np.float64), lot_pad * 2.0))

        self.segs = []
        for st in town.get("streets", []):
            half = float(st.get("width", 4.0)) * 0.5 + road_pad
            p = st["_path"]
            for i in range(len(p) - 1):
                self.segs.append((p[i][0], p[i][1], p[i + 1][0], p[i + 1][1], half))
        wp = town.get("wall", {}).get("path", [])
        for i in range(len(wp) - 1):
            self.segs.append((wp[i][0], wp[i][1], wp[i + 1][0], wp[i + 1][1], wall_half))
        self.seg = np.asarray(self.segs, np.float64) if self.segs else np.zeros((0, 5))

        # The highway corridor. A separate list, tested only by `open_road`,
        # because it must clear STANDARD TREES and must NOT clear hedges: a
        # field boundary crossing a road with a gate in it is the detail that
        # proves the field system and the road network are one landscape.
        #
        # `review/reports/ad-town-04.md` §5: a hedgerow standard grew on the
        # south road 5 m in front of `approach-s`, the canonical return camera,
        # and took 40 % of the frame. It was legal — the road keep-out is
        # width/2 + 1.1, about 3.1 m, and a 9 m canopy at 3.1 m off the
        # centreline closes the road over the top of a rider. No instrument in
        # the project could see it, because `check_walkable` only walks streets
        # inside the wall.
        #
        # The rule is not "keep the camera clear", it is the real one: an
        # approach to a town gate is kept clear either side of the way. A
        # standard is allowed to grow at the field boundary; it is not allowed
        # to grow over the road.
        self.highway = []
        for st in town.get("streets", []):
            if st["id"] not in HIGHWAYS:
                continue
            p = st["_path"]
            half = float(st.get("width", 4.0)) * 0.5 + HIGHWAY_CLEAR
            for i in range(len(p) - 1):
                a, b = p[i], p[i + 1]
                if math.hypot(*a) < 62.0 and math.hypot(*b) < 62.0:
                    continue
                self.highway.append((a[0], a[1], b[0], b[1], half))
            # The road does not stop where the town document stops drawing it.
            # `ford_road` is authored to (0, 96) because 96 m is the edge of the
            # 192 m plan grid, and the field system then runs over the next
            # 190 m of it. `approach-s` stands at (0, 138) — 42 m past the last
            # authored point — which is why the hedgerow standard that took 40 %
            # of that frame was on nobody's road. A way out of a town continues
            # to the horizon; the corridor continues with it.
            for end, prev in ((p[-1], p[-2]), (p[0], p[1])):
                if math.hypot(*end) < 62.0:
                    continue
                dx, dz = end[0] - prev[0], end[1] - prev[1]
                ln = math.hypot(dx, dz)
                if ln < 1e-6:
                    continue
                self.highway.append((end[0], end[1],
                                     end[0] + dx / ln * 220.0,
                                     end[1] + dz / ln * 220.0, half))

    @staticmethod
    def _inside(poly, X, Z, pad):
        """Point-in-convex-polygon, inflated by `pad`, for arrays.

        The slot polygons and lot outlines are all convex quads, so a half-plane
        test is exact and is four comparisons instead of a crossing count.
        """
        n = len(poly)
        inside = np.ones(np.shape(X), bool)
        # Orientation, so the test works whichever way the quad was wound.
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += poly[i][0] * poly[j][1] - poly[j][0] * poly[i][1]
        sgn = 1.0 if area > 0 else -1.0
        for i in range(n):
            ax, az = poly[i]
            bx, bz = poly[(i + 1) % n]
            ex, ez = bx - ax, bz - az
            ln = math.hypot(ex, ez) or 1.0
            # Signed distance to the edge line, positive outside.
            d = (ez * (X - ax) - ex * (Z - az)) / ln * sgn
            inside &= (d < pad)
        return inside

    def blocked(self, x, z, pad=0.0):
        X = np.asarray(x, np.float64)
        Z = np.asarray(z, np.float64)
        out = np.zeros(np.shape(X), bool)
        for poly, p in self.polys:
            out |= self._inside(poly, X, Z, p + pad)
        if len(self.seg):
            for ax, az, bx, bz, half in self.seg:
                ex, ez = bx - ax, bz - az
                ee = ex * ex + ez * ez
                if ee <= 1e-9:
                    continue
                t = np.clip(((X - ax) * ex + (Z - az) * ez) / ee, 0.0, 1.0)
                dx = X - (ax + ex * t)
                dz = Z - (az + ez * t)
                out |= (dx * dx + dz * dz) < (half + pad) ** 2
        return out

    def free(self, x, z, pad=0.0):
        """Blocked, plus open water. The test a scatter actually wants."""
        h = _ground(x, z)
        wet = h < TERR.water_level() + WATER_MARGIN
        return (~self.blocked(x, z, pad)) & (~wet)

    def open_road(self, x, z):
        """False inside the cleared corridor of a road leaving the town.

        Applied to standard trees only, and applied in `TreeSet.add` so that no
        caller can forget it — the same reason batching and LOD are decided in
        `core/venue.py` rather than in thirty venue modules.
        """
        X = np.asarray(x, np.float64)
        Z = np.asarray(z, np.float64)
        out = np.zeros(np.shape(X), bool)
        for ax, az, bx, bz, half in self.highway:
            ex, ez = bx - ax, bz - az
            ee = ex * ex + ez * ez
            if ee <= 1e-9:
                continue
            t = np.clip(((X - ax) * ex + (Z - az) * ez) / ee, 0.0, 1.0)
            dx = X - (ax + ex * t)
            dz = Z - (az + ez * t)
            out |= (dx * dx + dz * dz) < half * half
        return ~out


def _nudge(keep, x, z, pad=1.2, rings=(0.0, 2.0, 3.2, 4.6, 6.4, 8.5, 11.0)):
    """The nearest free point to an AUTHORED position, or None.

    Every position in this module that was chosen rather than sampled — the
    market square's shade tree, the churchyard's yews, the wayside shrine — is
    doing a specific job, so silently dropping it when a building's keep-out has
    crept over it loses the composition. Four of the churchyard's five yews were
    lost that way before this existed.
    """
    for r in rings:
        if r == 0.0:
            if bool(keep.free(x, z, pad)):
                return (x, z)
            continue
        for a in np.linspace(0.0, math.tau, 13)[:-1]:
            c = (x + math.cos(a) * r, z + math.sin(a) * r)
            if bool(keep.free(c[0], c[1], pad)):
                return c
    return None


def _scatter(rng, keep, x0, x1, z0, z1, n, pad=0.0, tries=8, min_gap=0.0):
    """`n` free points in a rectangle, rejection-sampled and thinned.

    Returns (N, 2). `min_gap` runs a cheap Poisson thinning so a scatter does
    not clump — the single tell that separates a placed landscape from a
    random one.

    The oversample factor is deliberately generous. Thinning happens AFTER
    rejection, so sampling only `n` free points and then thinning them to a
    minimum spacing yields a fraction of `n`: a first pass asked for 78 graves
    and placed 12.
    """
    got = np.zeros((0, 2), np.float64)
    want = n * (6 if min_gap > 0 else 2)
    for _ in range(tries):
        if len(got) >= want:
            break
        cand = np.stack([rng.uniform(x0, x1, want),
                         rng.uniform(z0, z1, want)], axis=1)
        ok = keep.free(cand[:, 0], cand[:, 1], pad)
        got = np.vstack([got, cand[ok]])
    if min_gap > 0 and len(got):
        kept = []
        g2 = min_gap * min_gap
        for p in got:
            if all((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 > g2 for q in kept):
                kept.append(p)
            if len(kept) >= n:
                break
        got = np.asarray(kept, np.float64).reshape(-1, 2)
    return got[:n]


# ---------------------------------------------------------------------------
# Tree bookkeeping
# ---------------------------------------------------------------------------

class TreeSet:
    """Collects every tree placement, then emits one instance batch per kind.

    Trees are the textbook instancing case and this is the whole of the
    discipline it needs: a venue asks for `add("apple", x, z)` and never sees a
    prototype. The prototypes and their four-step LOD chains are built once, at
    `flush`, and only for the kinds that were actually used.
    """

    KINDS = {
        # id                species  height  trunk collider radius
        "oak_great":       ("oak",    12.5, 0.62),
        "oak":             ("oak",     9.0, 0.42),
        "ash":             ("ash",    11.0, 0.36),
        "ash_hedgerow":    ("ash",     8.0, 0.30),
        "apple":           ("apple",   4.8, 0.24),
        "apple_old":       ("apple",   5.8, 0.32),
        "yew":             ("yew",     7.2, 0.55),
        "yew_ancient":     ("yew",     9.0, 0.80),
    }

    def __init__(self, ctx, asset_id, keep=None):
        self.ctx = ctx
        self.asset_id = asset_id
        self.place = {}
        self.keep = keep
        self.refused = 0

    def add(self, kind, x, z, yaw=0.0, scale=1.0, collide=True):
        # The one funnel every tree in the town goes through, which is why the
        # highway rule is enforced here. A tree refused in a caller is a tree
        # the next caller plants anyway.
        if self.keep is not None and not bool(self.keep.open_road(x, z)):
            self.refused += 1
            return False
        self.place.setdefault(kind, []).append((float(x), float(z), float(yaw),
                                                float(scale), bool(collide)))
        return True

    def flush(self):
        stats = {}
        for kind, items in sorted(self.place.items()):
            species, height, r = self.KINDS[kind]
            mid = f"tree_{kind}"
            chain = V.tree_lods(f"{self.asset_id}.{mid}", species, height)
            self.ctx.lod(mid, chain)
            tf = []
            for x, z, yaw, sc, collide in items:
                y = float(_ground(x, z))
                tf.append({"pos": (x, y, z), "rot_y": yaw, "scale": sc})
                if collide:
                    # A bole, not a bounding box: the player must be able to
                    # stand under the canopy, which is the entire point of the
                    # market square's shade tree.
                    self.ctx.collider("cylinder", center=(x, y + 1.2, z),
                                      radius=r * sc, height=2.4, tag="tree")
            self.ctx.instance(mid, chain[0], tf)
            stats[kind] = len(tf)
        return stats


# ---------------------------------------------------------------------------
# Inside the wall — plots, gardens, boundaries
# ---------------------------------------------------------------------------

def _slot_frame(slot, town):
    """(centre, back direction, half width across, half depth) for a plot.

    The back of a plot is the direction AWAY from the street the building
    FRONTS, and the slot record names that street — `fronts` is one of the
    `streets[]` ids for 87 of the 94 slots. Using it rather than the slot's
    `rotationDeg` is deliberate: the rotation convention differs between the
    frontage axis and the facing axis depending on how a slot was placed, and
    reading it wrong puts every kitchen garden in the road.

    Falling back to the NEAREST street is not good enough on its own and was
    measurably wrong: `hm.slot.26.cottage_a` fronts Bell Alley 6.0 m to its east
    and Tenter Lane runs 6.6 m to its west, so nearest-street sent its garden
    across the lane and into its neighbour's house.
    """
    c = np.asarray(slot["centre"], np.float64)
    named = [st for st in town["streets"] if st["id"] == slot.get("fronts")]
    best, bestd = None, 1e18
    for st in (named or town["streets"]):
        p = st["_path"]
        for i in range(len(p) - 1):
            a = np.asarray(p[i], np.float64)
            b = np.asarray(p[i + 1], np.float64)
            e = b - a
            ee = float(e @ e)
            if ee <= 1e-9:
                continue
            t = float(np.clip(((c - a) @ e) / ee, 0.0, 1.0))
            q = a + e * t
            d = float(np.linalg.norm(c - q))
            if d < bestd:
                bestd, best = d, q
    if best is None:
        return c, np.array([0.0, 1.0]), 4.0, 4.0
    v = c - best
    n = float(np.linalg.norm(v))
    back = v / n if n > 1e-6 else np.array([0.0, 1.0])
    poly = np.asarray(slot["polygon"], np.float64)
    # Half-extent of the footprint along and across the back direction.
    rel = poly - c
    across = np.array([-back[1], back[0]])
    hd = float(np.abs(rel @ back).max())
    hw = float(np.abs(rel @ across).max())
    return c, back, hw, hd


def _open_runs(path, keep, pad=0.0, step=1.0):
    """Split a boundary polyline wherever it would cross something.

    A hedge is not allowed to grow across a road, and `tools/check_walkable.mjs`
    is the thing that says so: the first churchyard wall was drawn round the
    whole authored lot polygon and severed Kirk Green at the lych gate and
    Kirkgate in fourteen places. Every boundary run in the town goes through
    here, so the gateways are a property of the road network rather than of a
    list of hand-authored gaps that would rot the first time a street moved.
    """
    pts = [(float(p[0]), float(p[-1])) for p in path]
    dense = []
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        ln = math.hypot(b[0] - a[0], b[1] - a[1])
        n = max(1, int(round(ln / step)))
        for k in range(n):
            t = k / n
            dense.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    dense.append(pts[-1])
    if not dense:
        return []
    X = np.array([p[0] for p in dense])
    Z = np.array([p[1] for p in dense])
    ok = keep.free(X, Z, pad)
    runs, cur = [], []
    for i, good in enumerate(ok):
        if good:
            cur.append(dense[i])
        else:
            if len(cur) > 1:
                runs.append(cur)
            cur = []
    if len(cur) > 1:
        runs.append(cur)
    return runs


def _boundary(ctx, rng, asset_id, path, style, height=None, collide=True):
    """Emit one plot boundary run and its collision.

    Three constructions in a fixed proportion, and the proportion is the point:
    a town where every boundary is the same is a town built by one contractor
    on one afternoon. Hedge dominates because it is both the commonest and by
    far the cheapest — 16 triangles a metre against 83 for wattle and 114 for
    dry stone.
    """
    if len(path) < 2:
        return
    if style == "wattle":
        h = height or rng.uniform(0.95, 1.20)
        ctx.emit(TERR.drape(V.wattle_fence(asset_id, path, h)))
    elif style == "stone":
        h = height or rng.uniform(0.90, 1.25)
        ctx.emit(TERR.drape(V.dry_stone_wall(asset_id, path, h)))
    else:
        h = height or rng.uniform(1.15, 1.75)
        gaps = [(0.42, 0.52)] if rng.random() < 0.35 else []
        ctx.emit(TERR.drape(V.hedge_run(asset_id, path, h,
                                        width=rng.uniform(0.62, 0.95), gaps=gaps)))
    if not collide:
        return
    for i in range(len(path) - 1):
        a, b = path[i], path[i + 1]
        ln = math.hypot(b[0] - a[0], b[1] - a[1])
        if ln < 0.4:
            continue
        steps = max(1, int(round(ln / 5.0)))
        for s in range(steps):
            p0 = (a[0] + (b[0] - a[0]) * s / steps, a[1] + (b[1] - a[1]) * s / steps)
            p1 = (a[0] + (b[0] - a[0]) * (s + 1) / steps,
                  a[1] + (b[1] - a[1]) * (s + 1) / steps)
            g = min(float(_ground(*p0)), float(_ground(*p1)))
            ctx.collider(COL.segment_box(p0, p1, 0.8, g, g + h,
                                         kind="solid", tag="boundary", extend=0.15))



# ---------------------------------------------------------------------------
# The ground inside the wall
# ---------------------------------------------------------------------------

def _lattice(x0, x1, z0, z1, cell, seed):
    """A jittered quad lattice. Corners are SHARED, so cells cannot gap.

    The first version of the intramural ground was an axis-aligned grid of
    1.8 m squares, and at a 1.62 m eye that is exactly what it looked like: a
    chequerboard of flat green and beige tiles painted over the mud, every
    boundary a straight line at 0 or 90 degrees. A ground blend has to have no
    readable direction and no readable module, so the lattice is jittered and
    every cell borrows its corners from its neighbours.

    Returns (nx, nz, C) with C shaped (nx+1, nz+1, 2).
    """
    nx = max(1, int(math.ceil((x1 - x0) / cell)))
    nz = max(1, int(math.ceil((z1 - z0) / cell)))
    gx = np.linspace(x0, x1, nx + 1)
    gz = np.linspace(z0, z1, nz + 1)
    C = np.stack(np.meshgrid(gx, gz, indexing="ij"), axis=-1)
    # Deterministic per-corner offset. A hash rather than an rng draw so the
    # same corner gets the same offset whichever cell asks for it.
    I = np.arange(nx + 1)[:, None] + 0.0
    J = np.arange(nz + 1)[None, :] + 0.0
    hx = np.sin(I * 12.9898 + J * 78.233 + seed * 0.017) * 43758.5453
    hz = np.sin(I * 39.3468 + J * 11.135 + seed * 0.031) * 24634.6345
    C[..., 0] += ((hx - np.floor(hx)) - 0.5) * cell * 0.62
    C[..., 1] += ((hz - np.floor(hz)) - 0.5) * cell * 0.62
    return nx, nz, C


def _poly_inside(P, x, z):
    """Even-odd crossing test. Plot corners are convex; authored lots are not."""
    n = len(P)
    inside = False
    j = n - 1
    for i in range(n):
        zi, zj = P[i][1], P[j][1]
        if (zi > z) != (zj > z):
            xc = P[i][0] + (z - zi) / (zj - zi + 1e-12) * (P[j][0] - P[i][0])
            if x < xc:
                inside = not inside
        j = i
    return inside


def _ground_value(X, Z):
    """The ground's COLOR_0 grey at a world position. Continuous, per VERTEX.

    ## The other half of the quilt

    Both ground layers used to draw `g = 0.72 + 0.24 * rng.random()` **once per
    cell** and apply it to all four of that cell's corners. Two adjacent cells
    therefore differ by up to a quarter of a stop with a hard edge between them,
    and since `mesh._Builder.poly` writes a flat colour per polygon, the edge is
    the cell boundary exactly. That is a patchwork of value laid over the ground
    independently of what material is on it — and it is visible in
    `ad-town-03`'s `sty-walk-03` as dark and light rectangles down the middle of
    a lane that is all one material, and under the green in
    `crop/ground-quilt.png`. The cover changes were only half of §2's "quilt of
    opaque axis-aligned rectangles"; this was the other half, and it survives
    every fix to the cover boundaries because it does not depend on them.

    Sampling a smooth world-space field per VERTEX instead makes the value
    continuous: `_lattice` shares corners between neighbouring cells, so two
    cells meeting at a corner agree there, the value interpolates across each
    quad, and no cell boundary can be seen. Three scales, none of them at the
    lattice pitch, and an amplitude a third of what it was — the variation is
    there to stop a large flat surface reading as paint, not to be seen.
    """
    return (0.80
            + 0.055 * np.sin(X * 0.21 + 0.7) * np.cos(Z * 0.19 - 1.3)
            + 0.040 * np.sin((X + Z * 0.6) * 0.53 + 2.1)
            + 0.030 * np.sin((X * 0.7 - Z) * 1.17 - 0.4))


def _poly_edge_dist(P, X, Z):
    """Distance from each (X, Z) to the polygon's boundary. Vectorised.

    Unsigned — `_poly_inside` supplies the sign. Used to feather a patch's
    margin over a real distance rather than over whole lattice cells.
    """
    A = P
    B = np.roll(P, -1, axis=0)
    E = B - A                                          # (n, 2)
    L2 = np.maximum((E * E).sum(1), 1e-12)
    px = X[..., None] - A[None, :, 0]
    pz = Z[..., None] - A[None, :, 1]
    t = np.clip((px * E[None, :, 0] + pz * E[None, :, 1]) / L2[None, :], 0.0, 1.0)
    dx = px - t * E[None, :, 0]
    dz = pz - t * E[None, :, 1]
    return np.sqrt(dx * dx + dz * dz).min(axis=-1)


def _surface_patch(asset_id, poly, mat, cell=0.72, lift=0.028, ragged=0.55,
                   feather=1.60):
    """A draped skin of one ground material over a polygon, with a SOFT margin.

    The terrain splat resolves ONE material per triangle over a 4 m mesh, which
    is the right unit for a hillside and far too coarse for a town: a burgage
    plot is 5 m across, so a whole yard falls inside two triangles and takes
    whatever the splat decided for them. That is why the intramural ground read
    as one brown field from every aerial - not because nothing was authored
    there, but because nothing authored there could be smaller than the mesh.

    ## Why this was rebuilt

    The first version fixed that and became its own defect. `ad-town-03` §2
    called the result "a quilt of opaque axis-aligned rectangles" and "the
    ugliest thing in the build" (`bailey-walk-04`, `crop/ground-quilt.png`),
    and D-047 records the trade that got us there. Three causes, all here:

    1. **`cell=1.25` with a whole-cell drop.** `ragged` deleted entire cells at
       the margin, so the boundary was a staircase whose tread was 1.25 m — and
       a 1.25 m step seen from 3 m is a right angle. The margin is now a real
       DISTANCE feather: a cell's survival probability falls off smoothly over
       `feather` metres of the polygon edge, warped by a noise field, and the
       cell is a third the size, so the boundary is a stipple of 0.45 m tufts
       thinning out over a metre and a bit. That is how grass actually stops.
    2. **The lattice was the world grid.** Every patch in the town shared one
       axis-aligned lattice, so every patch edge was parallel to every other
       one and the whole aerial read as a pixel quilt. Each patch now builds in
       its own frame, rotated by a per-patch seeded angle.
    3. **The boundary was the polygon.** A burgage plot is a quadrilateral, so
       a skin clipped to it is a quadrilateral however ragged its edge. The
       polygon is now only the *centre of the probability ramp*: two octaves of
       low-frequency noise push the effective boundary in and out by up to
       `feather`, so the yard's cover spills through the gate and dies back
       under the eaves, and no straight run of edge survives anywhere.

    Cost: about 6x the quads of the old version on a typical yard (a 5 x 9 m
    plot goes from ~28 to ~230), which is ~460 triangles for a burgage plot.
    Against `t-report.json`'s 1.15 M in the worst frame and a 3.5 M budget that
    is affordable, and it is the difference between a ground blend and a quilt.
    """
    rng = rng_for(asset_id, "skin", mat)
    # Each cover at ITS OWN authored coverage. `yard`, `dirt`, `cinder` and
    # `gravel` are 2 m materials and `grass_*` are 6 m ones; one shared UV scale
    # stretches four of the six by 3x and the result is a blurred flat colour,
    # which is precisely what makes a ground patch read as paint.
    uv = MATS.uv_scale(mat)
    P = np.asarray(poly, np.float64)
    if len(P) < 3:
        return None
    lo, hi = P.min(axis=0), P.max(axis=0)
    if (hi[0] - lo[0]) * (hi[1] - lo[1]) > 30000.0:
        return None

    # -- the patch's own frame ----------------------------------------------
    # Seeded per patch, so no two patches in the town share a lattice
    # direction. `_lattice` is built in this frame and rotated back on emit.
    # `seed_from`, NEVER `hash()`. Python salts str hashing per process, so this
    # one line made every ground patch in the town — and therefore every tree,
    # hedge and verge scattered against it — different on every build. It is why
    # `ad-town-05` measured a rebuild from source as a non-no-op: a tree vanished
    # from `t-gate-south` and validate.py went 0 -> 5 failures without a single
    # source change. docs/ARCHITECTURE.md §7. See tools/determinism.py.
    seed = seed_from(asset_id) % 9973
    ang = float(rng.random()) * math.pi          # a quad lattice is pi-periodic
    ca, sa = math.cos(ang), math.sin(ang)
    cen = P.mean(axis=0)
    Q = np.stack([(P[:, 0] - cen[0]) * ca + (P[:, 1] - cen[1]) * sa,
                  -(P[:, 0] - cen[0]) * sa + (P[:, 1] - cen[1]) * ca], axis=1)
    qlo, qhi = Q.min(axis=0), Q.max(axis=0)
    pad = feather * 1.15
    nx, nz, C = _lattice(qlo[0] - pad, qhi[0] + pad, qlo[1] - pad, qhi[1] + pad,
                         cell, seed)

    # Cell centres in the patch frame, and the same centres in world space.
    QC = np.stack([C[:-1, :-1], C[1:, :-1], C[1:, 1:], C[:-1, 1:]], axis=2)
    CEN = QC.mean(axis=2)
    cx, cz = CEN[..., 0], CEN[..., 1]

    # -- the feather ---------------------------------------------------------
    # Signed distance to the polygon edge, pushed in and out by two octaves of
    # noise at ~3 m and ~1.1 m, then turned into a keep probability. The noise
    # is what stops a straight polygon edge ever appearing as a straight edge
    # of cover, which is the whole finding.
    d = _poly_edge_dist(Q, cx, cz)
    # `_poly_inside` is scalar; the same even-odd crossing test, vectorised.
    inside = np.zeros(cx.shape, bool)
    n = len(Q)
    for i in range(n):
        j = (i - 1) % n
        zi, zj = Q[i][1], Q[j][1]
        cross = (zi > cz) != (zj > cz)
        with np.errstate(divide="ignore", invalid="ignore"):
            xc = Q[i][0] + (cz - zi) / (zj - zi + 1e-12) * (Q[j][0] - Q[i][0])
        inside ^= cross & (cx < xc)
    sd = np.where(inside, -d, d)                      # negative inside

    warp = (np.sin(cx * 0.34 + seed * 0.11) * np.cos(cz * 0.29 - seed * 0.07) * 0.62 +
            np.sin((cx - cz) * 0.92 + seed * 0.23) * 0.30)
    sd = sd + warp * feather * ragged
    keep_p = 1.0 - smoothstep(-0.5, 0.5, sd / max(feather, 1e-3))
    draw = rng.random(cx.shape) < keep_p

    b = M._Builder()
    idx = np.argwhere(draw)
    if not len(idx):
        return None
    for i, j in idx:
        q2 = QC[i, j]
        q = []
        for p in q2:
            wx = cen[0] + p[0] * ca - p[1] * sa
            wz = cen[1] + p[0] * sa + p[1] * ca
            q.append(np.array([wx, lift, wz], np.float32))
        b.poly(q, [(p[0] * uv, p[2] * uv) for p in q],
               np.array([0, 1, 0], np.float32))
    m = b.build(mat)
    if not len(m.v):
        return None
    # Value per VERTEX from a continuous world field, not per cell from an
    # rng draw — see `_ground_value`. This is what stops the patch reading as
    # a patchwork of flat greys whatever material is on it.
    g = _ground_value(m.v[:, 0], m.v[:, 2]).astype(np.float32)
    m.with_colour(np.stack([g, g, g], axis=1))
    return TERR.drape(m)


# What a back plot's ground actually is. Weighted, because a poor quarter is
# mostly beaten earth and dung-and-straw and only a merchant keeps grass.
YARD_SURFACES = (
    ("grass_worn", 0.24),      # rough grass, walked over
    ("yard", 0.22),            # dung, straw and trodden muck
    ("grass_lush", 0.16),      # the corner nobody crosses
    ("dirt", 0.16),            # beaten earth
    ("cinder", 0.11),          # ash from the hearth, spread to kill the mud
    ("gravel", 0.11),
)


def _pick(rng, table):
    r = float(rng.random()) * sum(w for _, w in table)
    for k, w in table:
        r -= w
        if r <= 0:
            return k
    return table[-1][0]


def _desire_path(asset_id, a, b, width=0.85, mat="grass_worn"):
    """The worn line between two places everybody walks between.

    Art Bible section 7 - "worn smooth where everyone walks, mossy where nobody
    does". A yard whose whole surface is one cover reads as painted; the path
    from the back door to the gate is the thing that says somebody uses it.
    """
    rng = rng_for(asset_id, "desire")
    a = np.asarray(a, np.float64)
    b = np.asarray(b, np.float64)
    d = b - a
    ln = float(np.linalg.norm(d))
    if ln < 1.2:
        return None
    d = d / ln
    nrm = np.array([-d[1], d[0]])
    bld = M._Builder()
    steps = max(2, int(ln / 0.9))
    phase = rng.uniform(0.0, 3.0)
    prev = None
    for k in range(steps + 1):
        t = k / steps
        # A path wanders and it is wider where it is used most. A straight
        # constant-width ribbon is a decal, not a worn line.
        w = width * (0.72 + 0.5 * math.sin(t * 3.1 + phase))
        c = a + d * (ln * t) + nrm * (math.sin(t * 2.3 + phase) * width * 0.45)
        cur = (c - nrm * w * 0.5, c + nrm * w * 0.5)
        if prev is not None:
            q = [np.array([prev[0][0], 0.034, prev[0][1]], np.float32),
                 np.array([prev[1][0], 0.034, prev[1][1]], np.float32),
                 np.array([cur[1][0], 0.034, cur[1][1]], np.float32),
                 np.array([cur[0][0], 0.034, cur[0][1]], np.float32)]
            bld.poly(q, [(p[0] * 0.3, p[2] * 0.3) for p in q],
                     np.array([0, 1, 0], np.float32))
        prev = cur
    m = bld.build(mat)
    return TERR.drape(m) if len(m.v) else None


def _intramural_ground(ctx, town, tight, asset_id):
    """Green everything inside the wall that nobody has paved or built on.

    The largest single area in every aerial of Hearthmere was featureless brown:
    no grass, no verges, no yards, only the two market trees. The town read as a
    construction site with houses parked on it. `venues/terrain.py` does leave
    green pockets, but they resolve at its 4 m mesh, which cannot see a 5 m plot
    or a 2 m verge - so at town scale the whole walled area came out as one
    trodden-earth splat.

    This lays a second, finer ground over the top of it on a jittered 1.8 m
    lattice, on exactly the cells that are neither building, road, working yard
    nor water. What it paints is a BLEND rather than a material, per the ground
    rule: rough grass in the open, a trodden band against every road edge, the
    wetter greens in the hollows, dung-and-straw in the pockets behind the
    houses - and the thresholds between them are dithered by the same noise that
    chose them, so no two covers meet along a line.
    """
    rng = rng_for(asset_id, "intra")
    # 1.35 m, down from 1.8. The cover boundaries here are already noise
    # driven, so what made them read as a quilt from the air was the
    # MODULE — a 1.8 m step is a readable rectangle at 3 m and a readable
    # pixel from the air. See `_surface_patch` for the same finding.
    CELL = 1.35
    HALF = 88.0
    nx, nz, C = _lattice(-HALF, HALF, -HALF, HALF, CELL, 4451)
    # Cell centres, from the jittered corners.
    Q = np.stack([C[:-1, :-1], C[1:, :-1], C[1:, 1:], C[:-1, 1:]], axis=2)
    CEN = Q.mean(axis=2)
    X, Z = CEN[..., 0].ravel(), CEN[..., 1].ravel()

    # Inside the enceinte: the same rounded rectangle `terrain.json`'s
    # `townEarth` uses, so the two ground layers agree about where the town is.
    hx, hz, corner = 84.0, 82.0, 30.0
    ax = np.maximum(np.abs(X) - (hx - corner), 0.0)
    az = np.maximum(np.abs(Z) - (hz - corner), 0.0)
    r = np.hypot(ax, az)
    inside = r < (corner - 1.4 + (np.sin(X * 0.21) + np.cos(Z * 0.17)) * 1.1)
    free = inside & tight.free(X, Z, -0.35)
    if not free.any():
        return 0

    # Two noise scales decide the cover. The low one gives a whole quarter its
    # character; the high one breaks it up so no patch has a straight edge.
    # Art Bible section 8 wants variation from two scales; this is the ground's.
    lo = (np.sin(X * 0.061 + 1.7) * np.cos(Z * 0.053 - 0.8) +
          0.6 * np.sin((X + Z) * 0.028 + 2.9))
    hi = (np.sin(X * 0.63 + 0.4) * np.cos(Z * 0.57 + 1.9) +
          0.7 * np.sin((X - Z) * 0.41))
    v = lo + hi * 0.42 + rng.uniform(-0.22, 0.22, X.shape)

    # The trodden band. Everything within a couple of metres of a made road is
    # walked on, and that band is what stops the green reading as a lawn laid up
    # to a kerb.
    d_road = np.full(X.shape, 1e9)
    for sax, saz, sbx, sbz, half in tight.seg:
        ex, ez = sbx - sax, sbz - saz
        ee = ex * ex + ez * ez
        if ee <= 1e-9:
            continue
        t = np.clip(((X - sax) * ex + (Z - saz) * ez) / ee, 0.0, 1.0)
        dx, dz = X - (sax + ex * t), Z - (saz + ez * t)
        d_road = np.minimum(d_road, np.hypot(dx, dz) - half)
    # And everything in front of a DOOR. `ad-town-03` §2 asked for transitions
    # that follow how ground actually wears; a road band alone gives a town
    # whose grass runs up to every threshold, which no inhabited building has
    # ever had. The apron in front of a door is trodden to bare earth for two
    # or three metres and it is the single cheapest signal that a house is
    # lived in. Measured from the street face of every slot.
    d_door = np.full(X.shape, 1e9)
    for slot in town["buildingSlots"]:
        poly = np.asarray(slot["polygon"], np.float64)
        south = _face(poly, (0.0, 1.0))
        if south is None:
            continue
        mid, out, _yaw, _ln = south
        p = mid + out * 1.1
        d_door = np.minimum(d_door, np.hypot(X - p[0], Z - p[1]))
    worn = ((d_road < (2.0 + hi * 0.9 + rng.uniform(-0.5, 0.5, X.shape))) |
            (d_door < (2.4 + hi * 0.8 + rng.uniform(-0.4, 0.4, X.shape))))

    h = _ground(X, Z)
    wet = h < TERR.water_level() + 2.2

    # Mud where the water actually sits, rather than lush grass right down to
    # the waterline — §2 asks for transitions that follow how ground wears, and
    # the bottom 0.8 m of a river town is silt, not lawn. Trodden ground wins
    # over wet, because a path through a wet hollow is a path.
    soak = h < TERR.water_level() + 0.85
    key = np.where(worn & ~soak, 0,
                   np.where(soak, 5,
                            np.where(wet, 1,
                                     np.where(v > 0.55, 2,
                                              np.where(v > -0.45, 3, 4)))))
    COVERS = ["grass_worn", "grass_lush", "grass_dry", "grass_worn", "yard",
              "mud"]

    QF = Q.reshape(-1, 4, 2)
    total = 0
    for mi, mat in enumerate(COVERS):
        sel = np.flatnonzero(free & (key == mi))
        if not len(sel):
            continue
        uv = MATS.uv_scale(mat)
        b = M._Builder()
        for k in sel:
            q = [np.array([QF[k, c, 0], 0.02, QF[k, c, 1]], np.float32)
                 for c in range(4)]
            b.poly(q, [(p[0] * uv, p[2] * uv) for p in q],
                   np.array([0, 1, 0], np.float32))
        m = b.build(mat)
        if len(m.v):
            # COLOR_0 carries the variation a 2 m tile cannot, sampled per
            # VERTEX from a continuous world field. Drawn per CELL from an rng
            # it was itself a quilt — see `_ground_value`.
            g = _ground_value(m.v[:, 0], m.v[:, 2]).astype(np.float32)
            m.with_colour(np.stack([g, g, g], axis=1))
            ctx.emit(TERR.drape(m))
            total += len(sel)
    return total


def _plots(ctx, town, keep, tight, trees, asset_id):
    """A back plot behind every dwelling, with a boundary round it.

    This is the single biggest change to the aerial read inside the wall. 94
    buildings on undifferentiated ground is a brown blob; 94 buildings each with
    a fenced yard behind it is a town plan, and it is the same plan
    `docs/areas/hearthmere/plan/schedule.md` already describes in prose.
    """
    rng = rng_for(asset_id, "plots")
    KITS = {"cottage", "townhouse", "workshop", "shed", "bakery", "cooper",
            "carpenter", "chandler", "bowyer", "confectioner", "stables"}
    n_plot = n_garden = 0
    for slot in town["buildingSlots"]:
        if slot["kit"] not in KITS:
            continue
        c, back, hw, hd = _slot_frame(slot, town)
        across = np.array([-back[1], back[0]])
        # GROW the plot outward from the building's back wall until it hits
        # something, rather than proposing a size and testing it.
        #
        # This is the third attempt and the first that works, and the reason the
        # first two did not is worth stating: Hearthmere is dense. A plot deep
        # enough to be interesting is longer than the gap to the next lane for
        # two thirds of the town, so "propose 9 m, shrink on failure" finds
        # nothing for most slots and leaves the aerial exactly as it was. What a
        # burgage plot actually is, is *everything between this house and the
        # next obstruction*, which is what this measures.
        gap = 1.0
        wl = wr = float(min(hw, 5.5))
        depth = 0.0
        step = 0.55
        while depth < 12.0:
            p = c + back * (hd + gap + depth + step)
            if not bool(tight.free(np.array([p[0]]), np.array([p[1]]), 0.0)[0]):
                break
            # Each side is measured independently, so a plot that meets its
            # neighbour on one hand and open ground on the other comes out as
            # the wedge it really is. Half of slot 51's brief is "its back fence
            # has a kink in it"; this is where that comes from.
            stop = False
            for sgn in (-1, 1):
                for _ in range(5):
                    w = wl if sgn < 0 else wr
                    q = p + across * (sgn * w)
                    if bool(tight.free(np.array([q[0]]), np.array([q[1]]), 0.0)[0]):
                        break
                    w *= 0.76
                    if w < 1.0:
                        stop = True
                        break
                    if sgn < 0:
                        wl = w
                    else:
                        wr = w
                if stop:
                    break
            if stop:
                break
            depth += step
        depth -= 0.3
        # A yard "four paces deep" is what the schedule gives slot 54, and it is
        # what most of this town has room for. The boundary matters more than
        # the depth: it is the line that makes the plan legible from the air.
        if depth < 1.6 or min(wl, wr) < 1.0:
            continue
        near = c + back * (hd + gap)
        far = near + back * depth
        corners = [near - across * wl, far - across * wl, far + across * wr,
                   near + across * wr]
        w = (wl + wr) * 0.5
        n_plot += 1
        sid = f"{asset_id}.plot.{slot['n']:02d}"
        style = ("hedge", "hedge", "wattle", "hedge", "stone",
                 "wattle")[int(rng.integers(0, 6))]
        for k, run in enumerate(_open_runs([tuple(p) for p in corners], keep, 0.1)):
            _boundary(ctx, rng, f"{sid}.{k}", run, style)

        # What is IN the plot. A quarter are worked gardens; the rest get the
        # residue a back yard actually has.
        cen = (near + far) * 0.5
        garden = rng.random() < 0.55 and depth > 3.0 and w > 1.8

        # The plot's own GROUND. A fenced yard on the same brown splat as the
        # road outside it is a fence drawn on a field; the surface is what makes
        # it a yard. A worked garden is turned earth; everything else takes a
        # weighted pick from what a back plot in a pre-industrial town actually
        # has underfoot.
        surf = "earth" if garden else _pick(rng, YARD_SURFACES)
        skin = _surface_patch(f"{sid}.skin", [(float(p[0]), float(p[1]))
                                              for p in corners], surf)
        if skin is not None:
            ctx.emit(skin)
        # And the line everybody walks: back door to the far corner of the plot,
        # worn through whatever the surface is.
        if depth > 2.4:
            gate = far + across * (rng.uniform(-0.55, 0.55) * w)
            path = _desire_path(f"{sid}.path", near, gate,
                                width=rng.uniform(0.6, 0.95),
                                mat="dirt" if surf.startswith("grass") else "grass_worn")
            if path is not None:
                ctx.emit(path)

        if garden:
            n_garden += 1
            _kitchen_garden(ctx, sid, cen, back, across, w * 1.7, depth * 0.8, rng)
        else:
            _back_yard(ctx, sid, cen, back, across, w, depth, rng, trees)
    return n_plot, n_garden


def _kitchen_garden(ctx, asset_id, centre, back, across, width, depth, rng):
    """Beds, crops at real spacing, poles, a cloche, a heap, a skep, a scarecrow.

    Laid out as a working gardener would: beds run along the plot so you can
    reach the middle from a path on either side, the tallest crop (beans) at the
    end that does not shade the rest, and the compost against the boundary.
    """
    yaw = float(math.atan2(across[0], across[1]))
    n_bed = max(1, int(min(4, depth / 1.5)))
    bw = min(1.35, width * 0.42)
    for i in range(n_bed):
        t = (i + 0.5) / n_bed - 0.5
        p = centre + back * (t * depth)
        g = float(_ground(p[0], p[1]))
        bed = V.dug_bed(f"{asset_id}.bed.{i}", bw, width * 0.86)
        bed.rotate_y(yaw)
        bed.translate(p[0], g, p[1])
        ctx.emit(bed)
        kind = ("cabbage", "leek", "root", "herb")[int(rng.integers(0, 4))]
        spacing = {"cabbage": 0.46, "leek": 0.17, "root": 0.22, "herb": 0.34}[kind]
        row = V.crop_row(f"{asset_id}.row.{i}", width * 0.80, kind, spacing)
        row.rotate_y(yaw + math.pi * 0.5)
        row.translate(p[0], g + 0.20, p[1])
        ctx.emit(row)

    end = centre + back * (depth * 0.5 + 0.6)
    g = float(_ground(end[0], end[1]))
    poles = V.bean_poles(f"{asset_id}.beans", min(width * 0.7, 3.4))
    poles.rotate_y(yaw + math.pi * 0.5)
    poles.translate(end[0], g, end[1])
    ctx.emit(poles)

    if rng.random() < 0.55:
        p = centre + across * (width * 0.36) + back * rng.uniform(-0.3, 0.3) * depth
        c = V.cloche(f"{asset_id}.cloche")
        c.translate(p[0], float(_ground(p[0], p[1])), p[1])
        ctx.emit(c)
    if rng.random() < 0.45:
        p = centre - across * (width * 0.40) - back * (depth * 0.36)
        h = V.compost_heap(f"{asset_id}.compost", rng.uniform(0.7, 1.05))
        h.translate(p[0], float(_ground(p[0], p[1])), p[1])
        ctx.emit(h)
    if rng.random() < 0.28:
        p = centre + across * (width * 0.40) - back * (depth * 0.30)
        s = V.beehive(f"{asset_id}.skep")
        s.translate(p[0], float(_ground(p[0], p[1])), p[1])
        ctx.emit(s)
    if rng.random() < 0.22:
        p = centre + back * rng.uniform(-0.2, 0.2) * depth
        s = V.scarecrow(f"{asset_id}.crow")
        s.rotate_y(rng.uniform(0, math.tau))
        s.translate(p[0], float(_ground(p[0], p[1])), p[1])
        ctx.emit(s)


def _back_yard(ctx, asset_id, centre, back, across, width, depth, rng, trees):
    """The plots that are not gardens: rough grass, a bush, sometimes a tree.

    Art Bible §7 — residue. A yard with nothing in it is a hole in the town, and
    it is exactly the hole the aerial was showing.
    """
    for i in range(int(rng.integers(1, 4))):
        p = centre + across * (rng.uniform(-0.42, 0.42) * width) + \
            back * (rng.uniform(-0.42, 0.42) * depth)
        b = V.shrub(f"{asset_id}.bush.{i}", rng.uniform(0.55, 1.1),
                    rng.uniform(0.7, 1.35))
        b.translate(p[0], float(_ground(p[0], p[1])), p[1])
        ctx.emit(b)
    if rng.random() < 0.30 and depth > 5.0:
        p = centre + back * (depth * 0.30) + across * (width * rng.uniform(-0.3, 0.3))
        trees.add("apple_old" if rng.random() < 0.6 else "oak",
                  p[0], p[1], yaw=rng.uniform(0, math.tau),
                  scale=rng.uniform(0.82, 1.1))


# ---------------------------------------------------------------------------
# The authored lots
# ---------------------------------------------------------------------------

def _lot(town, lid):
    for l in town.get("openLots", []):
        if l["id"] == lid:
            return np.asarray(l["poly"], np.float64)
    return None


def _orchard(ctx, town, keep, trees, asset_id):
    """The glebe orchard: rows, but not a grid, with a hedge round it.

    `openLots` calls for twelve old apples with the grass long under them. Rows
    are how an orchard was actually planted and are what makes it read as an
    orchard from the air rather than as scrub — but a perfect lattice reads as a
    spreadsheet, so the row spacing wanders and trees are missing where one
    died and was never replaced.
    """
    poly = _lot(town, "hm.lot.orchard")
    if poly is None:
        return 0
    rng = rng_for(asset_id, "orchard")
    c = poly.mean(axis=0)
    # Row axis along the lot's longest edge.
    e = poly[1] - poly[0]
    if np.linalg.norm(poly[2] - poly[1]) > np.linalg.norm(e):
        e = poly[2] - poly[1]
    u = e / (np.linalg.norm(e) or 1.0)
    v = np.array([-u[1], u[0]])
    hu = float(np.abs((poly - c) @ u).max()) - 2.6
    hv = float(np.abs((poly - c) @ v).max()) - 2.6

    n = 0
    row_pos = -hv
    ri = 0
    while row_pos < hv:
        step = rng.uniform(5.2, 6.6)
        along = -hu + rng.uniform(0.0, 1.6)
        while along < hu:
            p = c + u * along + v * (row_pos + rng.uniform(-0.55, 0.55))
            along += rng.uniform(5.0, 6.4)
            if rng.random() < 0.12:
                continue                        # one died; nobody replanted
            if not bool(keep.free(p[0], p[1], 1.0)):
                continue
            trees.add("apple_old" if rng.random() < 0.7 else "apple", p[0], p[1],
                      yaw=rng.uniform(0, math.tau), scale=rng.uniform(0.85, 1.15))
            n += 1
            # Under a heavy branch: fallen fruit, a prop, long grass.
            if rng.random() < 0.5:
                a = rng.uniform(0, math.tau)
                r = rng.uniform(1.6, 2.8)
                px, pz = p[0] + math.cos(a) * r, p[1] + math.sin(a) * r
                prop = M.cylinder(0.055, rng.uniform(2.0, 2.6), 5, 0.008, "timber_grey")
                prop.rotate_z(rng.uniform(0.35, 0.6))
                prop.rotate_y(a + math.pi)
                prop.translate(px, float(_ground(px, pz)), pz)
                ctx.emit(prop)
            for _ in range(int(rng.integers(3, 9))):
                a = rng.uniform(0, math.tau)
                r = rng.uniform(0.5, 2.9)
                px, pz = p[0] + math.cos(a) * r, p[1] + math.sin(a) * r
                fr = M.lathe([(0.0, 0.0), (0.035, 0.018), (0.030, 0.052),
                              (0.0, 0.062)], 6, "foliage_flower")
                fr.rotate_x(rng.uniform(0, 1.2))
                fr.translate(px, float(_ground(px, pz)) + 0.02, pz)
                ctx.emit(fr)
        row_pos += step
        ri += 1

    # "Grass long under them" — the lot note, and the thing that separates an
    # orchard from a car park with trees in it. Nobody grazes an orchard while
    # the fruit is on, so the sward under it is the longest inside 100 m.
    long_grass = []
    x0, z0 = poly[:, 0].min(), poly[:, 1].min()
    x1, z1 = poly[:, 0].max(), poly[:, 1].max()
    for px, pz in _scatter(rng, keep, x0, x1, z0, z1, 700, pad=0.2, min_gap=0.55):
        long_grass.append({"pos": (float(px), float(_ground(px, pz)), float(pz)),
                           "rot_y": rng.uniform(0, math.tau),
                           "scale": rng.uniform(0.55, 1.05)})
    ctx.instance("tussock_long", V.tussock(f"{asset_id}.orchgrass", 0.30, 0.44, blades=13),
                 long_grass)

    # Boundary hedge, with a gap where the path comes in from the postern.
    ring = [tuple(p) for p in poly] + [tuple(poly[0])]
    for k, run in enumerate(_open_runs(ring, keep, 0.2)):
        _boundary(ctx, rng, f"{asset_id}.orchard.hedge.{k}", run, "hedge",
                  height=1.85)
    gx, gz = float(c[0]), float(c[1])
    ctx.entity(f"{asset_id}.orchard", "landmark.orchard",
               (gx, float(_ground(gx, gz)), gz), cell="K7", verbs=["gather"])
    return n


def _churchyard(ctx, town, keep, trees, asset_id):
    """Yews, leaning markers, a lych gate, and a wall round the whole.

    The lot note authors the composition: "Yew at the north-west angle, older
    stones leaning north, newer ground to the east." The stones lean because
    ground settles over a grave, always downhill and always north here, and
    that consistent lean is what makes sixty markers read as a burial ground
    rather than as sixty props.
    """
    poly = _lot(town, "hm.lot.graveyard")
    if poly is None:
        return 0
    rng = rng_for(asset_id, "churchyard")
    x0, z0 = poly[:, 0].min(), poly[:, 1].min()
    x1, z1 = poly[:, 0].max(), poly[:, 1].max()

    # Yews. Two ancient at the north-west angle, two more round the ground.
    for i, (fx, fz, kind) in enumerate((
            (0.10, 0.10, "yew_ancient"), (0.17, 0.22, "yew"),
            (0.86, 0.16, "yew"), (0.80, 0.88, "yew"), (0.13, 0.83, "yew"))):
        px = float(x0 + (x1 - x0) * fx)
        pz = float(z0 + (z1 - z0) * fz)
        p = _nudge(keep, px, pz, 1.4)
        if p is None:
            continue
        trees.add(kind, p[0], p[1], yaw=rng.uniform(0, math.tau),
                  scale=rng.uniform(0.9, 1.15))

    # Markers. Rejection-sampled off the church, its paths and its neighbours.
    pts = _scatter(rng, keep, x0 + 1.5, x1 - 1.5, z0 + 1.5, z1 - 1.5, 150,
                   pad=0.4, min_gap=1.15)
    stones = M.Mesh(mat="sandstone")
    for i, (px, pz) in enumerate(pts):
        m = V.grave_marker(f"{asset_id}.stone.{i:03d}",
                           mat="sandstone" if i % 5 else "rubble")
        # Rows, loosely: a churchyard is laid out east-west and then drifts.
        m.rotate_y(rng.uniform(-0.22, 0.22))
        m.translate(float(px), float(_ground(px, pz)) - 0.03, float(pz))
        stones.merge(m)
    ctx.emit(stones)

    # A grass bank and tussocks between the stones — the ground nobody mows.
    tuss = []
    for px, pz in _scatter(rng, keep, x0 + 1.5, x1 - 1.5, z0 + 1.5, z1 - 1.5, 130,
                           pad=1.0, min_gap=0.7):
        tuss.append({"pos": (float(px), float(_ground(px, pz)), float(pz)),
                     "rot_y": rng.uniform(0, math.tau),
                     "scale": rng.uniform(0.7, 1.4)})
    ctx.instance("tussock_long", V.tussock(f"{asset_id}.tuss", 0.28, 0.40, blades=11), tuss)

    # The lych gate, on the churchyard's west boundary where Kirk Green meets
    # it — the same line the plan puts slot 17's gate on, but OFF the church
    # door's axis.
    #
    # It used to stand at z = -0.5, dead on the axis of the great west door and
    # 19 m from the altar. Measured from the arrival eye (43, 4.92, -0.5), a
    # 3.6 m wide gate with a 3.6 m ridge at that range hides everything below
    # y = 1.93 at the fountain's distance across 8.1 m of the frame — i.e. it
    # cropped the basin of the Heron Fountain, which is BUILD_DIRECTIVE §3.2's
    # focal point, out of the most important composition in the build. Moved
    # clear of the door cone (±5.5 m at this range) to the south side of the
    # perron, where the path from Kirk Green's south verge actually enters the
    # burial ground and where a coffin gate belongs anyway.
    lx, lz = float(x0), 8.5
    ly = float(_ground(lx, lz))
    gate = V.lych_gate(f"{asset_id}.lych")
    gate.rotate_y(math.pi * 0.5)
    gate.translate(lx, ly, lz)
    ctx.emit(gate)
    for sx in (-1, 1):
        for sz in (-1, 1):
            ctx.collider("box", center=(lx + sz * 1.1, ly + 1.0, lz + sx * 1.1),
                         half=(0.16, 1.0, 0.16), tag="lychgate")
    ctx.entity(f"{asset_id}.lychgate", "landmark.lychgate", (lx, ly, lz),
               cell="H6", verbs=["inspect"])

    # Boundary wall, broken wherever a street runs through it — the lych gate
    # on Kirk Green, and Kirkgate along the churchyard's west side.
    ring = [tuple(p) for p in poly] + [tuple(poly[0])]
    for k, run in enumerate(_open_runs(ring, keep, 0.2)):
        _boundary(ctx, rng, f"{asset_id}.churchyard.wall.{k}", run, "stone",
                  height=1.15)
    return len(pts)


def _gardens(ctx, town, keep, asset_id):
    """The two authored kitchen gardens, planted to their own notes."""
    rng = rng_for(asset_id, "gardens")
    n = 0
    for lid in ("hm.lot.gardens_west", "hm.lot.gardens_ne"):
        poly = _lot(town, lid)
        if poly is None:
            continue
        c = poly.mean(axis=0)
        e = poly[1] - poly[0]
        u = e / (np.linalg.norm(e) or 1.0)
        v = np.array([-u[1], u[0]])
        hu = float(np.abs((poly - c) @ u).max())
        hv = float(np.abs((poly - c) @ v).max())
        _kitchen_garden(ctx, f"{asset_id}.{lid.split('.')[-1]}", c, v, u,
                        hu * 1.7, hv * 1.55, rng)
        ring = [tuple(p) for p in poly] + [tuple(poly[0])]
        for k, run in enumerate(_open_runs(ring, keep, 0.2)):
            _boundary(ctx, rng, f"{asset_id}.{lid.split('.')[-1]}.fence.{k}", run,
                      "wattle", height=1.05)
        n += 1
    return n


# ---------------------------------------------------------------------------
# Street trees and greens
# ---------------------------------------------------------------------------

def _street_trees(ctx, town, keep, trees, asset_id):
    """Trees only where a real town would have one.

    Not an avenue. A pre-industrial town plants a tree for a reason: shade over
    the place people wait, a churchyard yew, a boundary marker at a lane end. An
    evenly spaced row of street trees is a nineteenth-century municipal idea and
    would be the loudest anachronism in the build.
    """
    rng = rng_for(asset_id, "streettrees")
    out = []
    # The market place shade tree, at the square's south-east corner where the
    # step-wall is: people sit on the wall, so the tree goes over the wall.
    for (px, pz, kind) in ((3.5, 12.5, "oak_great"),          # market place
                           (-24.5, 21.0, "oak"),              # Well Lane head
                           (-40.0, 44.0, "ash"),              # Smiths' Lane end
                           (30.5, 44.0, "ash"),               # Sty Lane
                           (-62.0, 4.0, "oak"),               # the Bailey, west
                           (58.0, 60.0, "ash_hedgerow")):     # the Bailey, east
        found = _nudge(keep, px, pz, 1.2)
        if found is None:
            continue
        px, pz = found
        if trees.add(kind, px, pz, yaw=rng.uniform(0, math.tau)):
            out.append((px, pz, kind))

    # A bench under the market tree, and a ring of tussocks in its unswept root
    # circle. This is what "people sit under it" has to look like.
    if out:
        px, pz, _ = out[0]
        g = float(_ground(px, pz))
        for i in range(3):
            a = i * math.tau / 3 + 0.4
            b = K.bench(f"{asset_id}.bench.{i}", 1.7)
            b.rotate_y(-a)
            b.translate(px + math.cos(a) * 1.55, g, pz + math.sin(a) * 1.55)
            ctx.emit(b)
        ctx.entity(f"{asset_id}.market.tree", "landmark.tree", (px, g, pz),
                   cell="F7", verbs=["rest", "inspect"])
    return out


def _face(poly, want):
    """The wall face pointing most nearly toward `want`. (mid, yaw, length).

    `yaw` turns a mesh authored facing +Z onto that face, matching
    `Mesh.rotate_y`'s convention (x' = cos x + sin z).

    Not the polygon's bounding box. Half the town is skewed to its street, so a
    slot's AABB touches the building at one corner only — dressing hung on the
    AABB's north edge floats up to two metres off the wall it is supposed to be
    growing on, which is a §6.1 "nothing floats" defect on forty buildings at
    once.
    """
    want = np.asarray(want, np.float64)
    n = len(poly)
    # Winding, so "outward" is outward.
    area = sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1]
               for i in range(n))
    sgn = 1.0 if area > 0 else -1.0
    best, bestd = None, -1e18
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        e = np.asarray(b, np.float64) - np.asarray(a, np.float64)
        ln = float(np.linalg.norm(e))
        if ln < 0.4:
            continue
        e = e / ln
        out = np.array([e[1], -e[0]]) * sgn
        d = float(out @ want)
        if d > bestd:
            bestd = d
            mid = (np.asarray(a, np.float64) + np.asarray(b, np.float64)) * 0.5
            best = (mid, out, float(math.atan2(out[0], out[1])), ln)
    return best


def _building_dressing(ctx, town, keep, asset_id):
    """Window boxes, wall ivy, and moss on the shaded foot of every wall.

    Ivy goes on NORTH faces only, which at this latitude and this locked 09:30
    rig is the face that never dries — and putting it on the sunny face instead
    is the sort of detail that reads as wrong without a player being able to say
    why. North is -Z.
    """
    rng = rng_for(asset_id, "dressing")
    boxes = ivies = mosses = 0
    for slot in town["buildingSlots"]:
        poly = np.asarray(slot["polygon"], np.float64)
        sid = f"{asset_id}.dress.{slot['n']:02d}"
        gy = float(slot.get("groundY", 0.0))
        north = _face(poly, (0.0, -1.0))
        south = _face(poly, (0.0, 1.0))
        if north is None or south is None:
            continue

        # Ivy on the north face of about a fifth of the buildings, and always
        # on the oldest ones (the almshouses, the warehouses, the charnel).
        old = slot["kit"] in ("warehouse", "cottage", "shed")
        if rng.random() < (0.30 if old else 0.10):
            mid, out, yaw, ln = north
            w = ln * rng.uniform(0.45, 0.85)
            h = min(float(slot.get("eavesHeight", 4.0)) * rng.uniform(0.5, 0.85), 5.5)
            panel = V.ivy_panel(f"{sid}.ivy", w, h, ragged=rng.uniform(0.3, 0.6))
            panel.rotate_y(yaw)
            off = mid + out * 0.02
            panel.translate(float(off[0]), gy, float(off[1]))
            ctx.emit(panel)
            ivies += 1

        # Moss at the foot of the north wall. Art Bible §7's rule literally:
        # worn smooth where everyone walks, mossy where nobody does.
        if rng.random() < 0.55:
            mid, out, yaw, ln = north
            skin = V.wall_moss(f"{sid}.moss", ln * rng.uniform(0.5, 0.95),
                               rng.uniform(0.18, 0.42))
            skin.rotate_y(yaw)
            off = mid + out * 0.015
            skin.translate(float(off[0]), gy, float(off[1]))
            ctx.emit(skin)
            mosses += 1

        # Window boxes on the sunny frontage of dwellings.
        if slot["kit"] in ("cottage", "townhouse") and rng.random() < 0.45:
            mid, out, yaw, ln = south
            along = np.array([out[1], -out[0]])
            for i in range(int(rng.integers(1, 3))):
                p = mid + out * 0.10 + along * (ln * rng.uniform(-0.3, 0.3))
                wb = V.window_box(f"{sid}.wbox.{i}")
                wb.rotate_y(yaw)
                wb.translate(float(p[0]), gy + rng.uniform(1.25, 1.55), float(p[1]))
                ctx.emit(wb)
                boxes += 1
    return boxes, ivies, mosses


def _town_greens(ctx, town, keep, asset_id):
    """Rough grass, nettles and docks on every scrap of untrodden ground.

    Inside the wall the terrain splat already leaves green pockets — yards,
    verges, the churchyard — but they are FLAT green, and at a 1.62 m eye a
    flat green pocket reads as painted concrete. This is the layer that makes
    the ground have a surface: tussocks in the open, and a denser band of
    nettles and docks against every wall, fence and hedge, because that is
    exactly where they grow and exactly where nobody walks.

    Every one of these is a nine-triangle instance, so the whole layer is a
    handful of draw calls.
    """
    rng = rng_for(asset_id, "greens")
    tuft, nettle = [], []
    # Open ground inside the wall.
    for px, pz in _scatter(rng, keep, -82, 82, -82, 82, 2600, pad=0.35,
                           min_gap=0.9):
        y = float(_ground(px, pz))
        tuft.append({"pos": (float(px), y, float(pz)),
                     "rot_y": rng.uniform(0, math.tau),
                     "scale": rng.uniform(0.55, 1.35)})

    # The band against every building's foot. `_face` gives the real wall line,
    # so this follows a skewed building instead of its bounding box.
    for slot in town["buildingSlots"]:
        poly = np.asarray(slot["polygon"], np.float64)
        n = len(poly)
        for i in range(n):
            a, b = poly[i], poly[(i + 1) % n]
            e = np.asarray(b, np.float64) - np.asarray(a, np.float64)
            ln = float(np.linalg.norm(e))
            if ln < 1.0:
                continue
            e = e / ln
            out = np.array([e[1], -e[0]])
            for k in range(int(ln * 0.8)):
                t = rng.uniform(0.05, 0.95)
                for sgn in (-1, 1):
                    p = np.asarray(a, np.float64) + e * (ln * t) + \
                        out * (sgn * rng.uniform(0.25, 0.85))
                    if not bool(keep.free(p[0], p[1], -1.1)):
                        continue
                    y = float(_ground(p[0], p[1]))
                    nettle.append({"pos": (float(p[0]), y, float(p[1])),
                                   "rot_y": rng.uniform(0, math.tau),
                                   "scale": rng.uniform(0.7, 1.5)})
                    break

    ctx.instance("grass_tuft", V.tussock(f"{asset_id}.tuft", 0.24, 0.30, blades=9), tuft)
    ctx.instance("wall_nettles",
                 V.tussock(f"{asset_id}.nettle", 0.26, 0.52, "weeds", 9, blade_w=0.016), nettle)
    return len(tuft), len(nettle)


def _paving_life(ctx, town, keep, asset_id):
    """Weeds in the joints and moss in the wet corners, along every street.

    Placed AGAINST the kerb, never in the wheel ruts, because that is where they
    survive. It is the cheapest possible answer to "this paving looks new", and
    it is instanced, so a thousand tufts is one draw call per cell.
    """
    rng = rng_for(asset_id, "paving")
    weeds, moss = [], []
    for st in town["streets"]:
        p = st["_path"]
        half = float(st.get("width", 4.0)) * 0.5
        for i in range(len(p) - 1):
            a = np.asarray(p[i], np.float64)
            b = np.asarray(p[i + 1], np.float64)
            d = b - a
            ln = float(np.linalg.norm(d))
            if ln < 0.5:
                continue
            d = d / ln
            n = np.array([-d[1], d[0]])
            for _ in range(int(ln * 0.55)):
                t = rng.uniform(0.02, 0.98)
                side = 1 if rng.random() < 0.5 else -1
                off = half - rng.uniform(0.05, 0.55)
                q = a + d * (ln * t) + n * (side * off)
                y = float(_ground(q[0], q[1])) + 0.20      # streets.ROAD_LIFT
                if rng.random() < 0.62:
                    weeds.append({"pos": (float(q[0]), y, float(q[1])),
                                  "rot_y": rng.uniform(0, math.tau),
                                  "scale": rng.uniform(0.6, 1.5)})
                else:
                    moss.append({"pos": (float(q[0]), y, float(q[1])),
                                 "rot_y": rng.uniform(0, math.tau),
                                 "scale": rng.uniform(0.7, 1.6)})
    ctx.instance("joint_weeds", V.joint_weeds(f"{asset_id}.weed", 6), weeds)
    ctx.instance("joint_moss",
                 M.lathe([(0.0, 0.0), (0.16, 0.022), (0.13, 0.05), (0.0, 0.055)],
                         7, "moss"), moss)
    return len(weeds), len(moss)


# ---------------------------------------------------------------------------
# Outside the wall
# ---------------------------------------------------------------------------

def _water_meadow(ctx, town, keep, trees, asset_id):
    """The Emberflow's north bank: reed, sedge, pollard willow, poached mud.

    The channel is authored in `terrain.json` and runs along z ~= -91, so the
    meadow is the strip between the town wall at z ~= -76 and the water. Reeds
    go IN the margin — between the waterline and 0.9 m above it — which is the
    one band `keep.free` deliberately excludes, so this is the only scatter in
    the module that tests the water directly.
    """
    rng = rng_for(asset_id, "meadow")
    chan = None
    for s in town["_terrain"]["water"]["channels"]:
        if s.get("id") == "hm.water.emberflow":
            chan = np.asarray(s["path"], np.float64)
    if chan is None:
        return 0, 0

    wl = TERR.water_level()
    reeds, sedge, willows = [], [], 0

    # March along the river and sample a band each side of it.
    for i in range(len(chan) - 1):
        a, b = chan[i], chan[i + 1]
        if a[0] < -150 or a[0] > 110:
            continue
        d = b - a
        ln = float(np.linalg.norm(d))
        if ln < 1.0:
            continue
        d = d / ln
        n = np.array([-d[1], d[0]])
        # Dense sampling, because the two bands this is looking for are narrow:
        # the reed margin is 1.4 m of ELEVATION on a bank that falls a metre in
        # ten, and a sparse scatter across a 52 m strip lands almost none of its
        # points in it. The first pass placed 115 tufts along 260 m of river.
        count = int(ln * 26.0)
        cand = np.stack([rng.uniform(0.0, ln, count),
                         rng.uniform(-26.0, 26.0, count)], axis=1)
        P = a[None, :] + d[None, :] * cand[:, 0:1] + n[None, :] * cand[:, 1:2]
        h = _ground(P[:, 0], P[:, 1])
        # Reed grows in the shallows and on the wet margin, not out in the
        # channel. A 1.4 m band starting 0.45 m BELOW the surface put whole
        # stands in open water where the bank shelves gently, which is most of
        # the Emberflow's north side.
        margin = (h > wl - 0.22) & (h < wl + 0.55)
        meadow = (h >= wl + 0.55) & (h < wl + 3.0)
        blocked = keep.blocked(P[:, 0], P[:, 1], 0.6)
        for j in range(count):
            if blocked[j]:
                continue
            if margin[j]:
                reeds.append({"pos": (float(P[j, 0]), float(h[j]), float(P[j, 1])),
                              "rot_y": rng.uniform(0, math.tau),
                              "scale": rng.uniform(0.6, 1.5)})
            elif meadow[j] and rng.random() < 0.55:
                sedge.append({"pos": (float(P[j, 0]), float(h[j]), float(P[j, 1])),
                              "rot_y": rng.uniform(0, math.tau),
                              "scale": rng.uniform(0.7, 1.6)})

    ctx.instance("reed_stand", V.reed_tuft(f"{asset_id}.reed", 1.7, 22), reeds)
    ctx.instance("sedge_tussock",
                 V.tussock(f"{asset_id}.sedge", 0.30, 0.60, "reed", 11, blade_w=0.014), sedge)

    # Pollard willows: one every 12-18 m along the bank, which is exactly how a
    # withy line was managed, and gives the meadow a rhythm the reeds cannot.
    walk = 0.0
    for i in range(len(chan) - 1):
        a, b = chan[i], chan[i + 1]
        if a[0] < -140 or a[0] > 100:
            continue
        d = b - a
        ln = float(np.linalg.norm(d))
        if ln < 1.0:
            continue
        d = d / ln
        n = np.array([-d[1], d[0]])
        while walk < ln:
            here = walk
            walk += rng.uniform(11.0, 17.0)
            # Search outward for the first dry ground on either bank rather than
            # guessing an offset. The Emberflow's authored channel is 11 m of
            # bed plus a 9 m bank, and how far that is from the centreline
            # depends entirely on how the terrace shelves at that point — a
            # fixed 7-15 m offset put sixteen willows of twenty in the river,
            # and a fixed 13-24 m put half of them inside the town wall.
            p = None
            for off in (11.0, 14.0, 17.0, 20.0, 24.0):
                for side in ((1, -1) if rng.random() < 0.55 else (-1, 1)):
                    q = a + d * here + n * (side * off * rng.uniform(0.92, 1.08))
                    y = float(_ground(q[0], q[1]))
                    if wl + 0.3 < y < wl + 3.4 and \
                            not bool(keep.blocked(q[0], q[1], 1.5)):
                        p = q
                        break
                if p is not None:
                    break
            if p is None:
                continue
            y = float(_ground(p[0], p[1]))
            w = V.willow_pollard(f"{asset_id}.willow.{willows:02d}",
                                 rng.uniform(4.0, 5.6))
            w.rotate_y(rng.uniform(0, math.tau))
            w.translate(float(p[0]), y, float(p[1]))
            ctx.emit(w)
            ctx.collider("cylinder", center=(float(p[0]), y + 1.1, float(p[1])),
                         radius=0.45, height=2.2, tag="tree")
            willows += 1
        walk -= ln

    # The drinking place: where the cattle come down, the bank is poached into
    # mud, the reeds stop dead, and there are hoof prints in it. One spot, west
    # of the ford, because a herd uses one crossing and wears it out.
    dx, dz = -34.0, -88.0
    dy = float(_ground(dx, dz))
    poach = M.Group()
    for i in range(26):
        a = rng.uniform(0, math.tau)
        r = rng.uniform(0.0, 6.5)
        px, pz = dx + math.cos(a) * r, dz + math.sin(a) * r
        blob = M.lathe([(rng.uniform(0.7, 1.9), 0.0), (rng.uniform(0.5, 1.4), 0.05)],
                       7, "mud_wet", close_bottom=False)
        blob.translate(px, 0.03, pz)
        poach.add(blob)
    for i in range(30):
        a = rng.uniform(0, math.tau)
        r = rng.uniform(0.4, 6.0)
        px, pz = dx + math.cos(a) * r, dz + math.sin(a) * r
        hoof = M.lathe([(0.075, 0.0), (0.055, -0.055)], 6, "mud_wet",
                       close_top=False)
        hoof.scale(1.0, 1.0, 1.6)
        hoof.rotate_y(rng.uniform(0, math.tau))
        hoof.translate(px, 0.02, pz)
        poach.add(hoof)
    ctx.emit(TERR.drape(poach))
    ctx.entity(f"{asset_id}.drinkingplace", "landmark.ford", (dx, dy, dz),
               cell="D2", verbs=["inspect"])
    del trees
    return len(reeds) + len(sedge), willows


def _fields(ctx, town, keep, trees, asset_id):
    """Hedgerow field boundaries: the single biggest fix for the aerial.

    The land outside the wall was a lawn. Real land around a town is a system of
    small irregular fields, and the boundary between them is a hedge with the
    odd standard tree left in it — which is why a hedgerow tree in England is
    always an ash or an oak standing in a line with nothing either side.

    The fields are generated from a seeded radial partition rather than drawn by
    hand, because the pattern that matters is "irregular closes radiating from
    the town, subdivided as you get further out", and that is a rule, not a
    drawing. Boundaries stop at the road network and at the water, so the roads
    read as running THROUGH the field system instead of over it.
    """
    rng = rng_for(asset_id, "fields")
    runs = 0
    standards = 0
    BANDS = (FIELD_INNER - 4.0, FIELD_INNER + 22.0, FIELD_INNER + 46.0,
             FIELD_INNER + 70.0)

    # Radial boundaries: the sides of each close, running out from the town.
    # Forty-four of them, not twenty-six. This is the number that decides
    # whether the ring outside the wall reads as farmed or as a lawn with lines
    # on it, and at twenty-six the closes were 25 m wide at the wall and 45 m at
    # the treeline — bigger than any medieval close ever was, and the aerial
    # showed it as empty green wedges.
    n_rad = 44
    for i in range(n_rad):
        a = (i / n_rad) * math.tau + rng.uniform(-0.04, 0.04)
        r0 = FIELD_INNER - 10.0 + rng.uniform(-4.0, 8.0)
        r1 = FIELD_OUTER + rng.uniform(-14.0, 10.0)
        # Not every close runs the full depth: the outer half of a strip field
        # system is subdivided more coarsely than the inner half.
        if i % 2 and rng.random() < 0.5:
            r1 = BANDS[2] + rng.uniform(-6.0, 6.0)
        path, cur = [], []
        r = r0
        while r < r1:
            # The line wanders: a hedge follows a ditch, and a ditch follows the
            # ground, so a dead straight boundary is a modern enclosure and
            # would be the wrong century.
            aa = a + math.sin(r * 0.035 + i) * 0.045
            x, z = math.cos(aa) * r, math.sin(aa) * r
            if bool(keep.free(x, z, 1.5)):
                cur.append((x, z))
            else:
                if len(cur) > 1:
                    path.append(cur)
                cur = []
            r += 5.0
        if len(cur) > 1:
            path.append(cur)
        for k, seg in enumerate(path):
            if len(seg) < 2:
                continue
            _boundary(ctx, rng, f"{asset_id}.field.r{i:02d}.{k}", seg, "hedge",
                      height=rng.uniform(1.6, 2.4), collide=False)
            runs += 1
            # A standard every couple of hundred metres of hedge, and a gate
            # where the boundary meets open ground.
            if rng.random() < 0.62:
                px, pz = seg[int(len(seg) * rng.uniform(0.2, 0.8))]
                trees.add("ash_hedgerow" if rng.random() < 0.7 else "oak",
                          px, pz, yaw=rng.uniform(0, math.tau),
                          scale=rng.uniform(0.85, 1.25), collide=False)
                standards += 1

    # Cross boundaries: the headlands at the ends of the closes.
    for band in BANDS:
        rr = band + rng.uniform(-5.0, 5.0)
        step = 0.05
        a = rng.uniform(0, 0.4)
        cur = []
        while a < math.tau:
            rrr = rr + math.sin(a * 5.0) * 4.5
            x, z = math.cos(a) * rrr, math.sin(a) * rrr
            if bool(keep.free(x, z, 1.5)) and rng.random() > 0.07:
                cur.append((x, z))
            else:
                if len(cur) > 2:
                    _boundary(ctx, rng, f"{asset_id}.field.b{int(band)}.{len(cur)}{a:.2f}",
                              cur, "hedge", height=rng.uniform(1.5, 2.2),
                              collide=False)
                    runs += 1
                cur = []
            a += step
        if len(cur) > 2:
            _boundary(ctx, rng, f"{asset_id}.field.b{int(band)}.tail", cur,
                      "hedge", height=1.7, collide=False)
            runs += 1

    # Arable: about half the closes are under the plough, and they get ridge and
    # furrow. This is what gives the ring a second green and a direction, and it
    # is the difference between "fields" and "lines drawn on a lawn".
    n_close = 0
    for i in range(n_rad):
        if rng.random() < 0.44:
            continue
        a = ((i + 0.5) / n_rad) * math.tau
        for j in range(len(BANDS) - 1):
            if rng.random() < 0.42:
                continue
            r0, r1 = BANDS[j] + 3.0, BANDS[j + 1] - 3.0
            rm = (r0 + r1) * 0.5
            c = np.array([math.cos(a) * rm, math.sin(a) * rm])
            if not bool(keep.free(c[0], c[1], 3.0)):
                continue
            u = np.array([math.cos(a), math.sin(a)])     # ploughed up the close
            half_u = (r1 - r0) * 0.5 - 2.0
            half_v = rm * (math.tau / n_rad) * 0.36
            if half_u < 4.0 or half_v < 2.5:
                continue
            # Mostly turned earth. `grass_dry` is stubble and is nearly cream:
            # a ring of it reads from the air as pale slabs laid on the grass
            # rather than as a worked field, so it is the minority crop state.
            mat = "earth" if rng.random() < 0.62 else "grass_dry"
            rf = V.ridge_and_furrow(f"{asset_id}.rf.{i}.{j}", c, u, half_u,
                                    half_v, pitch=rng.uniform(4.6, 6.6),
                                    rise=rng.uniform(0.14, 0.24), mat=mat)
            ctx.emit(TERR.drape(rf, 0.02))
            n_close += 1

    # Gates and stiles where a boundary meets a road: the detail that proves the
    # field system and the road network are one landscape and not two layers.
    for st in town["streets"]:
        p = st["_path"]
        end = p[-1] if math.hypot(*p[-1]) > math.hypot(*p[0]) else p[0]
        if math.hypot(*end) < 70.0:
            continue
        for side in (-1, 1):
            gx = end[0] + side * (float(st.get("width", 4.0)) * 0.5 + 2.4)
            gz = end[1]
            if not bool(keep.free(gx, gz, 0.8)):
                continue
            g = V.field_gate(f"{asset_id}.gate.{st['id']}.{side}", 2.9)
            g.rotate_y(rng.uniform(0, math.tau))
            g.translate(gx, float(_ground(gx, gz)), gz)
            ctx.emit(g)
    return runs, standards


def _approach(ctx, town, keep, trees, asset_id):
    """The roads out: verges, milestones, and a wayside shrine at the south.

    Only the roads that actually leave — Ford Road north over the bridge and
    south up the hill, and Mere Street west. Putting a verge down a back alley
    would be the same mistake as an avenue of street trees.
    """
    rng = rng_for(asset_id, "approach")
    n_stone = 0
    APPROACH = {"ford_road": 1.35, "mere_street": 1.0, "tan_road": 0.85}
    for st in town["streets"]:
        if st["id"] not in APPROACH:
            continue
        p = st["_path"]
        # Only the stretch outside the built area gets a ditched verge.
        out = [q for q in p if math.hypot(*q) > 62.0]
        if len(out) < 2:
            continue
        ctx.emit(TERR.drape(V.verge_ditch(f"{asset_id}.verge.{st['id']}", out,
                                          width=APPROACH[st["id"]])))
        # Milestones, at the point each road crosses the field boundary.
        for q in out[::2]:
            if math.hypot(*q) < 88.0:
                continue
            side = 1 if rng.random() < 0.5 else -1
            n = np.array([0.0, 0.0])
            j = out.index(q)
            k = min(j + 1, len(out) - 1)
            d = np.asarray(out[k], np.float64) - np.asarray(out[j], np.float64)
            if np.linalg.norm(d) > 1e-6:
                d = d / np.linalg.norm(d)
                n = np.array([-d[1], d[0]])
            # Clear of the street's own keep-out, which is width/2 + 1.1: a
            # milestone set at width/2 + 1.5 tests as blocked by the road it
            # stands beside, and the first pass placed none at all.
            off = float(st.get("width", 4.0)) * 0.5 + 2.9
            mx = q[0] + n[0] * side * off
            mz = q[1] + n[1] * side * off
            if not bool(keep.free(mx, mz, 0.4)):
                continue
            ms = V.milestone(f"{asset_id}.ms.{st['id']}.{n_stone}")
            ms.rotate_y(float(math.atan2(d[0], d[1])) if np.any(d) else 0.0)
            my = float(_ground(mx, mz))
            ms.translate(mx, my, mz)
            ctx.emit(ms)
            ctx.collider("box", center=(mx, my + 0.45, mz), half=(0.2, 0.45, 0.15),
                         tag="milestone")
            ctx.entity(f"{asset_id}.milestone.{st['id']}.{n_stone}",
                       "prop.milestone", (mx, my, mz), verbs=["inspect"])
            n_stone += 1

    # The shrine, on the south road where it starts to climb — the last thing a
    # player sees leaving and the first thing coming back.
    sp = _nudge(keep, 6.6, 88.0, 1.0) or (6.6, 88.0)
    sx, sz = float(sp[0]), float(sp[1])
    sy = float(_ground(sx, sz))
    shrine = V.wayside_shrine(f"{asset_id}.shrine")
    shrine.rotate_y(-math.pi * 0.5)
    shrine.translate(sx, sy, sz)
    ctx.emit(shrine)
    ctx.collider("box", center=(sx, sy + 0.9, sz), half=(0.45, 0.9, 0.4),
                 tag="shrine")
    ctx.entity(f"{asset_id}.shrine.south", "landmark.shrine", (sx, sy + 0.4, sz),
               cell="G12", verbs=["inspect", "pray"],
               light={"color": "#FFB35C", "intensity": 1.4, "range": 5.0})
    # Two trees flanking it: the shrine is under them, which is why it is here.
    for side in (-1, 1):
        tx, tz = sx + side * 4.2, sz + rng.uniform(-2.0, 2.0)
        if bool(keep.free(tx, tz, 1.2)):
            trees.add("ash", tx, tz, yaw=rng.uniform(0, math.tau))
    return n_stone


def _distance_wood(ctx, town, keep, asset_id):
    """The wooded ring: LOD3 from the start, because that is all it ever is.

    It frames every outward view and hides the world edge, and it is never seen
    closer than 140 m. So it is built as instanced EIGHT-triangle billboard
    impostors on one alpha-masked sheet (`vegetation.distance_tree`), and it is
    the cheapest square metre of scenery in the town by two orders of magnitude.
    It was a 90-triangle lathe, which at this instance count was 207,000
    triangles spent on a row of faceted green crystals across the Mere.

    Density ramps in from the field edge so the wood has a scrubby margin
    rather than a hard tree line, which is what a treeline at 200 m actually
    looks like and what stops the ring reading as a wall.

    It is generated as COPPICES, not as a uniform scatter, and that is a
    performance decision as much as an art one. A GPU instance batch only pays
    for itself above a dozen instances in one batching cell (core/venue.py
    `INSTANCE_MIN`); a uniform ring of 2,300 trees put four or five in each of
    240 cells, every one of them below the threshold and therefore baked into a
    cell batch of its own — 465 draw calls for a treeline. Blocks of woodland
    with clearings between them put sixty to a hundred and fifty trees in a
    cell, which is one draw call each, and is also what a wood looks like.
    """
    rng = rng_for(asset_id, "wood")
    # Three prototypes, not one. A single silhouette repeated two thousand times
    # is legible AS a repeat along a horizon, which is the one place the eye is
    # best at spotting it. Coppicing keeps 70-190 trees per batching cell, so
    # splitting them three ways still clears `INSTANCE_MIN` comfortably.
    protos = [V.distance_tree(f"{asset_id}.dt.{i}", 8.0 + i * 1.8) for i in range(3)]
    tfs = [[] for _ in protos]

    n_wood = 34
    for w in range(n_wood):
        a = (w / n_wood) * math.tau + rng.uniform(-0.06, 0.06)
        r = rng.uniform(WOOD_INNER + 8.0, WOOD_OUTER - 22.0)
        cx, cz = math.cos(a) * r, math.sin(a) * r
        # A block, not a disc: woodland edges follow field boundaries and
        # watercourses, so they are long and lobed.
        rad_a = rng.uniform(26.0, 52.0)
        rad_b = rng.uniform(16.0, 34.0)
        tilt = rng.uniform(0, math.pi)
        n = int(rng.integers(70, 190))
        u = rng.uniform(-1.0, 1.0, n * 2)
        v = rng.uniform(-1.0, 1.0, n * 2)
        inside = (u * u + v * v) < 1.0
        u, v = u[inside][:n], v[inside][:n]
        ct, stt = math.cos(tilt), math.sin(tilt)
        X = cx + (u * rad_a) * ct - (v * rad_b) * stt
        Z = cz + (u * rad_a) * stt + (v * rad_b) * ct
        rad = np.hypot(X, Z)
        H = _ground(X, Z)
        ok = (H > TERR.water_level() + 0.6) & (rad > WOOD_INNER - 14.0) & \
             (rad < WOOD_OUTER + 6.0)
        # Thin toward the block's edge so the wood has a scrubby margin.
        ok &= rng.uniform(0, 1, len(X)) > (u * u + v * v) * 0.55
        for i in np.flatnonzero(ok):
            tfs[int(rng.integers(0, len(protos)))].append(
                {"pos": (float(X[i]), float(H[i]), float(Z[i])),
                 "rot_y": float(rng.uniform(0, math.tau)),
                 "scale": float(rng.uniform(0.70, 1.18))})

    # Outliers: single trees and small clumps in the open ground between the
    # blocks. Without them the ring reads as a hedge of woodland with a hard
    # inner edge; with them it reads as country.
    for _ in range(150):
        a = rng.uniform(0, math.tau)
        r = rng.uniform(WOOD_INNER - 34.0, WOOD_OUTER)
        x, z = math.cos(a) * r, math.sin(a) * r
        h = float(_ground(x, z))
        if h < TERR.water_level() + 0.6:
            continue
        tfs[int(rng.integers(0, len(protos)))].append(
            {"pos": (x, h, z), "rot_y": float(rng.uniform(0, math.tau)),
             "scale": float(rng.uniform(0.62, 1.05))})

    for i, (proto, tf) in enumerate(zip(protos, tfs)):
        ctx.instance(f"wood_far_{i}", proto, tf)
    return sum(len(t) for t in tfs)


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build(ctx: VenueContext, asset_id="hm.landscape"):
    town = _load()
    keep = Keepout(town)
    tight = Keepout(town, slot_pad=0.30, lot_pad=0.30, road_pad=0.45,
                    wall_half=2.2)
    trees = TreeSet(ctx, asset_id, keep=keep)

    # Before anything is planted: the ground everything stands on. It is laid
    # first so every later drape (plot skins at 28 mm, desire paths at 34 mm)
    # sits proud of it rather than fighting it in the depth buffer.
    n_intra = _intramural_ground(ctx, town, tight, asset_id)
    n_plot, n_garden = _plots(ctx, town, keep, tight, trees, asset_id)
    n_lotgarden = _gardens(ctx, town, keep, asset_id)
    n_apple = _orchard(ctx, town, keep, trees, asset_id)
    n_grave = _churchyard(ctx, town, keep, trees, asset_id)
    street = _street_trees(ctx, town, keep, trees, asset_id)
    n_box, n_ivy, n_moss = _building_dressing(ctx, town, keep, asset_id)
    n_tuft, n_nettle = _town_greens(ctx, town, keep, asset_id)
    n_weed, n_jmoss = _paving_life(ctx, town, keep, asset_id)
    n_marsh, n_willow = _water_meadow(ctx, town, keep, trees, asset_id)
    n_hedge, n_standard = _fields(ctx, town, keep, trees, asset_id)
    n_ms = _approach(ctx, town, keep, trees, asset_id)
    n_wood = _distance_wood(ctx, town, keep, asset_id)
    tree_stats = trees.flush()

    print(f"      landscape: {n_intra} intramural ground cells · "
          f"{n_plot} plots ({n_garden} worked + {n_lotgarden} "
          f"authored gardens) · {n_apple} orchard trees · {n_grave} graves · "
          f"{len(street)} street trees · {n_box} window boxes / {n_ivy} ivy / "
          f"{n_moss} moss skins · {n_tuft} tussocks / {n_nettle} wall nettles · "
          f"{n_weed + n_jmoss} joint tufts · "
          f"{n_marsh} marsh tufts / {n_willow} willows · {n_hedge} field hedges "
          f"/ {n_standard} standards · {n_ms} milestones · {n_wood} distance trees")
    print("      trees by kind: " +
          " · ".join(f"{k} {v}" for k, v in sorted(tree_stats.items())) +
          f" · {trees.refused} refused inside a highway corridor")
