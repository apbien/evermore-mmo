"""Streets — the ground between the buildings.

In a town the player looks at the ground more than at anything else, and until
now Hearthmere's was a paved ribbon down the middle of undifferentiated mud.
This module builds the rest of it: a real street SECTION, the frontage that
resolves paving into a building line, junctions that interlock, the works the
town's 4 m fall needs, back alleys, and the furniture that gives Art Bible §7
its "vertical interest every 8-10 m".

Nothing here invents layout. `content/town/hearthmere.json` authors the fifteen
centrelines, `content/town/terrain.json` authors the ground, and
`buildingSlots[]` authors where the walls stand. `core/roadnet.py` is the model
read from those three; this is the geometry built from the model.

## The section

Across a made street, from the centre out:

    crown ── channel ── kerb ── footway/verge ── building line
      |         |        |          |
      |         |        |          `- flags at a shop, trodden earth at a
      |         |        |             cottage, falling 2% back to the kerb
      |         |        `- 0.16 m face, or 0.22 on Wharf Lane, which
      |         |           TOWN_PLAN says has gutters "wide enough to lose a
      |         |           boot in" because the whole east side drains there
      |         `- dressed setts whatever the carriageway is: a channel is
      |            always the best stone on the street
      `- crowned to shed water, then worn to a trough down the middle

That vertical stack is what was missing. A paved ribbon that stops at a cut
edge reads as a path across a field at any distance; the same ribbon with a
channel, a kerb and a raised footway behind it reads as a street from forty
metres, before a single prop is placed.

## What decides what

* **The surface vocabulary is data** (`roadnet.SURFACES`) and an unauthored
  surface is a build error. It used to be a three-entry dict with a silent
  fallback to cobble, so twelve of fifteen streets were built in the wrong
  material and eleven of them silently lost their kerbs.
* **Frontage is derived from `buildingSlots[]`**: the plot polygon gives the
  building line and `core.building.door_positions` gives the doors, and the
  footway, threshold, dropped kerb and boot scraper all follow from those two.
* **The fall decides the drainage.** Which side a channel deepens on, where the
  gullies go, where a street needs cross-drains and where it needs a flight is
  read from `terrain.height`, so it stays true if the ground moves.
* **Furniture is distributed by rule** along the network with a per-class
  weighting. Ninety hand-placed props do not survive the next layout change.

## Two structural rules this module obeys

**Author in LOCAL Y, then drape.** Every made surface here is built with its Y
as a height ABOVE THE GROUND and pushed onto `terrain.height` by
`terrain.drape`, which is one vectorised call per mesh. Asking for the height
of one point at a time costs 1.66 ms — three orders of magnitude more than the
same query inside an array — and this module asks about forty thousand points.
Only the things that must NOT follow the ground are built in absolute Y: a step
flight spans the fall by definition, so draping one would flatten it.

**Everything repeated is instanced.** `Props` defers every placement to the end
so that all the ground queries are answered in one array, then hands each
prototype to `ctx.instance` — one draw call per prototype instead of one per
prop. Emitting per prop once cost this venue 1,344 draw calls on its own.
"""

from __future__ import annotations

import json
import math
import os

import numpy as np

from core import building as BLD
from core import collision as COL
from core import kit as K
from core import materials as MAT
from core import mesh as M
from core import props as PR
from core import roadnet as RN
from core import streetscape as SF
from core import terrain as TERR
from core import vegetation as VG
from core.mathx import rng_for
from core.venue import VenueContext, REPO

NAME = "streets"

TOWN = os.path.join(REPO, "content/town/hearthmere.json")

# Batched on a 32 m module rather than core's 16 m (core/venue.py).
#
# A road network is the one thing in the town that is genuinely everywhere, and
# it is also the thing that gains least from fine culling, because a
# carriageway you cannot see is usually behind a building you can. 32 m is two
# town cells exactly, so the partition still nests.
CELL_SIZE = 32.0

# How proud a MADE surface sits above the ground it is laid on. Shared with
# `venues/market_square.py` through `kit.MADE_LIFT` so the square and the
# streets running into it stay continuous across the junction — see D-035.
LIFT = K.MADE_LIFT

UP = np.array([0.0, 1.0, 0.0], np.float32)

# Edge treatment -> (channel width, channel invert below the carriageway edge).
CHANNEL = {"kerb": (0.34, 0.085), "kerb_deep": (0.46, 0.115),
           "kerb_flush": (0.24, 0.030), "edging": (0.0, 0.045),
           "verge": (0.0, 0.0), "none": (0.0, 0.0)}

# Edge treatment -> (kerb width, footway height above the carriageway edge).
# The kerb FACE is that height plus the channel invert, so `kerb` gives 0.16 m
# and `kerb_deep` gives 0.22 m — the figure TOWN_PLAN states for Wharf Lane,
# arrived at through the section rather than asserted.
KERB = {"kerb": (0.165, 0.075), "kerb_deep": (0.215, 0.105),
        "kerb_flush": (0.155, 0.012), "edging": (0.185, 0.075),
        "verge": (0.0, 0.0), "none": (0.0, 0.0)}

# What a footway is paved in, by the standing of the building behind it. A shop
# lays flags because goods stand on them; a cottage has trodden earth because
# nobody ever paid for anything else.
FOOTWAY_MAT = {"hero": "flag", "secondary": "sett", "filler": "earth"}

MAX_FOOTWAY = 2.4       # metres; beyond this it is a yard, not a footway
STATION = 9.0           # Art Bible §7: vertical interest every 8-10 m


# ---------------------------------------------------------------------------
# Accumulators
# ---------------------------------------------------------------------------

class Paving:
    """Accumulates polygons per material into one Mesh each, in LOCAL Y.

    Every surface this module lays — carriageway, channel, kerb, footway,
    junction apron, dressing patch — is a polygon whose Y is a height above the
    ground, and the whole network is some forty thousand of them. Buffering per
    material and building once is what keeps the build in seconds, and it hands
    `ctx.emit` exactly one primitive per material to batch.
    """

    __slots__ = ("_b",)

    def __init__(self):
        self._b = {}

    def _bld(self, mat):
        b = self._b.get(mat)
        if b is None:
            b = self._b[mat] = M._Builder()
        return b

    def flat(self, mat, a_lo, a_hi, b_hi, b_lo, uv=None):
        """A horizontal quad, wound for a +Y normal.

        `a`/`b` are the two stations along the run, `lo`/`hi` the low and high
        offsets across it. This ordering is the one that was VERIFIED to wind
        +Y: the previous carriageway carried a comment claiming exactly that
        and produced the opposite, so 288/288 road triangles were back-face
        culled and the street rendered as bare ground between two kerbs.
        """
        uv = MAT.uv_scale(mat) if uv is None else uv
        pts = [a_lo, a_hi, b_hi, b_lo]
        self._bld(mat).poly(pts, [(p[0] * uv, p[2] * uv) for p in pts], UP)

    def face(self, mat, a_top, a_bot, b_bot, b_top, uv=None):
        """A near-vertical quad — a kerb face, a riser, a channel cheek.

        UVs run along the face and up it. A planar XZ projection collapses on a
        vertical surface, which is how a kerb ends up with a metre of texture
        smeared down a 0.16 m face.
        """
        uv = MAT.uv_scale(mat) if uv is None else uv
        pts = [a_top, a_bot, b_bot, b_top]
        n = np.cross(np.asarray(a_bot, np.float64) - np.asarray(a_top, np.float64),
                     np.asarray(b_top, np.float64) - np.asarray(a_top, np.float64))
        ln = float(np.linalg.norm(n))
        nrm = (n / ln).astype(np.float32) if ln > 1e-9 else UP
        uvs = [((float(p[0]) + float(p[2])) * 0.7071 * uv, float(p[1]) * uv)
               for p in pts]
        self._bld(mat).poly(pts, uvs, nrm)

    def tri(self, mat, a, b, c, uv=None):
        uv = MAT.uv_scale(mat) if uv is None else uv
        pts = [a, b, c]
        self._bld(mat).poly(pts, [(p[0] * uv, p[2] * uv) for p in pts], UP)

    def group(self):
        g = M.Group()
        for k, b in self._b.items():
            m = b.build(k)
            if m.tri_count:
                g.add(m, k)
        return g


class Props:
    """Deferred, instanced street furniture.

    Placements are recorded in PLAN and resolved against the ground in one
    vectorised `terrain.height` call at flush time, because a scalar query is
    1.66 ms and there are several hundred props. Each prototype then goes to
    `ctx.instance`: one draw call for the batch, and an Unreal
    `InstancedStaticMeshComponent` with no re-authoring.

    Variants exist because an instance transform is rigid. Three seeded
    bollards give a run of bollards that is not a row of clones, without paying
    three hundred meshes for it.

    Everything is packed into the shared `street_props` atlas page, which is
    what actually keeps this venue inside the Directive §7 budget: 347 props
    across 32 cells is 13 extra materials per cell unatlased and one with it.
    Only `water` and `glass` fall out of the page, because neither can live in
    a rect — one is animated at a different tile scale and one is emissive.
    """

    __slots__ = ("ctx", "atlas", "proto", "pend", "count")

    def __init__(self, ctx):
        self.ctx = ctx
        self.atlas = ctx.atlas("street_props")
        self.proto = {}
        self.pend = {}
        self.count = 0

    def pack(self, geom):
        """Fit a prop's UVs into one tile, then atlas everything eligible.

        The fit is what makes the atlas actually pay. `pack` refuses any part
        whose UVs span more than one tile, and street furniture is full of
        members LONGER than their material's 2 m coverage — a 2.8 m hitching
        rail, a 3.3 m laundry pole, a 2.4 m handrail, a lathed sphere whose
        circumference exceeds its diameter. Measured: without this, oak and
        iron fell out of the page in 22 and 21 cells respectively, which was 43
        of the venue's draw calls. Squeezing a 2.8 m rail onto a 2 m tile costs
        it 1.4x of texel density on a member 0.115 m wide, which is not
        visible; the draw call is.
        """
        for key, part in list(geom.items() if isinstance(geom, M.Group)
                              else [(geom.mat, geom)]):
            if key not in self.atlas.keys or not len(part.uv):
                continue
            cov = MAT.LIBRARY[key].coverage
            span = (part.uv.max(axis=0) - part.uv.min(axis=0)) / cov
            f = float(max(span[0], span[1]))
            if f > 0.98:
                part.uv = (part.uv * (0.98 / f)).astype(np.float32)
        return self.atlas.pack_eligible(geom)

    def place(self, kind, variant, factory, x, z, yaw=0.0, dy=0.0):
        mid = f"street_{kind}_{variant}"
        if mid not in self.proto:
            g = factory()
            if g is None or not g.tri_count:
                return None
            self.proto[mid] = self.pack(g)
        self.pend.setdefault(mid, []).append(
            (float(x), float(z), float(yaw), float(dy)))
        self.count += 1
        return mid

    def flush(self):
        every = [(mid, r) for mid in sorted(self.pend) for r in self.pend[mid]]
        if not every:
            return 0
        xs = np.array([r[0] for _m, r in every], np.float64)
        zs = np.array([r[1] for _m, r in every], np.float64)
        ys = np.asarray(TERR.height(xs, zs), np.float64)
        out = {}
        for i, (mid, r) in enumerate(every):
            out.setdefault(mid, []).append((r[0], float(ys[i]) + r[3], r[1], r[2]))
        for mid in sorted(out):
            self.ctx.instance(mid, self.proto[mid], out[mid])
        return self.count


def _p(x, y, z):
    return np.array([x, y, z], np.float32)


def _yaw_z(t):
    """Rotation mapping a prop's +Z onto the plan direction `t`."""
    return math.atan2(t[0], t[1])


def _yaw_x(t):
    """Rotation mapping a prop's +X onto the plan direction `t`.

    `mesh.rotate_y(a)` sends +Z to (sin a, cos a) and +X to (cos a, -sin a), so
    a rail, a bench, a trough, a handrail or a woodpile — all authored along
    +X — needs this and NOT `_yaw_z`. The kerbstones in the previous version of
    this file used the +Z rotation on an X-long box, which laid every kerbstone
    across the carriageway instead of along it.
    """
    return math.atan2(-t[1], t[0])


def _strip(pv, mat, lo, hi, uv=None):
    for i in range(len(lo) - 1):
        pv.flat(mat, lo[i], hi[i], hi[i + 1], lo[i + 1], uv)


def _in_window(windows, s):
    for (a, b) in windows:
        if a <= s <= b:
            return True
    return False


def _area_xz(pts):
    """Shoelace area of a plan polygon; used to reject degenerate colliders."""
    a = 0.0
    n = len(pts)
    for i in range(n):
        p, q = pts[i], pts[(i + 1) % n]
        a += float(p[0]) * float(q[2]) - float(q[0]) * float(p[2])
    return abs(a) * 0.5


# ---------------------------------------------------------------------------
# The model
# ---------------------------------------------------------------------------

def _door_world(slot):
    """[(x, y, z, a)] for a slot's doors, without emitting the building.

    `core.building.door_positions` is the fast path (it replays the plinth and
    the walls only). The fallback replays the whole building, which is four
    times slower but cannot go stale if that helper ever moves.
    """
    fn = getattr(BLD, "door_positions", None)
    if fn is not None:
        return fn(slot)
    plan = BLD.plan_building(slot)
    BLD.build_building(None, slot, plan=plan, detail=3, emit=False)
    return list(plan.get("door_world") or [])


def _doors_of(slot):
    return [(float(x), float(y), float(z)) for (x, y, z, _a) in _door_world(slot)]


def _slots():
    with open(TOWN, encoding="utf-8") as f:
        return json.load(f).get("buildingSlots", [])


class Net:
    """Everything the geometry passes need, resolved once.

    `masses` is every footprint grown by a margin, tested before any prop is
    placed. Deriving it here rather than per pass is what stops a hitching post
    ending up inside the bakery.
    """

    def __init__(self):
        self.streets = RN.load()
        self.slots = _slots()
        self.junctions = RN.junctions(self.streets)
        self.fronts = RN.frontages(self.streets, self.slots, doors_of=_doors_of,
                                   footprint_of=BLD.footprint_from_slot)
        self.by_street = {}
        for f in self.fronts:
            self.by_street.setdefault(f.street, []).append(f)
        self.discs = [(j.x, j.z, j.radius) for j in self.junctions]
        # Where each street STOPS because another one owns the paving. A
        # junction is not two ribbons crossing: the higher-class surface runs
        # through and the lower one runs up to it and ends. Without this the
        # two overlap coplanar — which is what put a patch of Smiths' Lane
        # cinder in the middle of Ford Road's setts, z-fighting with them.
        self.cut = {}
        for j in self.junctions:
            for (sid, _s, _e) in j.members:
                if sid != j.primary:
                    self.cut.setdefault(sid, []).append((j.x, j.z, j.radius))
        self.masses = []
        for s in self.slots:
            fp = BLD.footprint_from_slot(s)
            self.masses.append((fp.centre, (fp.w * 0.5 + 0.25, fp.d * 0.5 + 0.25),
                                fp.U, fp.V))
        self.flights, self.drains = {}, {}
        for sid, st in self.streets.items():
            for run in RN.steep_runs(st):
                # A cart route may never be stepped. TOWN_PLAN §3 is explicit
                # that Ford Road has "no steps anywhere: it is the cart route
                # and it must stay one", and the same holds for anything a
                # laden waggon uses, so those get cross-drains and a stepped
                # sett bond. Everything else gets a flight, because a 40% scarp
                # on a footway is not walkable and reads as a modelling error.
                if st.rank >= 3 or st.surface.key == "stone steps":
                    self.drains.setdefault(sid, []).append(run)
                else:
                    self.flights.setdefault(sid, []).append(run)

    def excluded(self, st, s):
        """True where another system owns this stretch of the carriageway."""
        if st.is_bridged(s):
            return True
        for (f0, f1, _d) in self.flights.get(st.id, ()):
            if f0 - 0.7 <= s <= f1 + 0.7:
                return True
        cuts = self.cut.get(st.id)
        if cuts:
            x, z = st.at(s)
            for (jx, jz, r) in cuts:
                if (x - jx) ** 2 + (z - jz) ** 2 <= r * r:
                    return True
        return False

    def in_junction(self, x, z, slack=0.0):
        for (jx, jz, r) in self.discs:
            if (x - jx) ** 2 + (z - jz) ** 2 <= (r + slack) ** 2:
                return True
        return False

    def in_mass(self, x, z, margin=0.0):
        for (c, h, U, V) in self.masses:
            dx, dz = x - c[0], z - c[1]
            if (abs(U[0] * dx + U[1] * dz) <= h[0] + margin and
                    abs(V[0] * dx + V[1] * dz) <= h[1] + margin):
                return True
        return False

    def on_carriageway(self, x, z, slack=0.35):
        for st in self.streets.values():
            if st.project(x, z)[2] < st.width * 0.5 + slack:
                return True
        return False


# ---------------------------------------------------------------------------
# 1. The carriageway
# ---------------------------------------------------------------------------

def _profile(surf, t):
    """Height above the carriageway EDGE at `t` = |offset| / half-width.

    A made road crowns so that it sheds water, and then two hundred years of
    hoof and nave wear a trough down the middle of the crown. Both are needed:
    the crown alone reads as a moulding, the trough alone as a ditch. Together
    they catch the 09:30 key along the shoulders and hold a dark line down the
    centre, which is what a worn street actually looks like.
    """
    return (surf.crown * max(0.0, 1.0 - t * t)
            - surf.trough * max(0.0, 1.0 - (t / 0.46) ** 2) ** 0.8)


def _dress_field(p, seed):
    """0..1 field deciding where a street's dressing lies. Smooth in world space.

    `ad-town-03` §2 is written against `landscape._surface_patch`, but the
    rectangles the art director photographed in `sty-walk-03` — dark and light
    quads marching down the middle of a back lane — are not that layer at all.
    They are the dressing below: a whole carriageway CELL, laid or not laid on
    an independent `rng.random() < dress_amount` coin flip. A cell is 2.0 m of
    station by one lane of width, so every dressed cell is a hard-edged
    rectangle aligned to the road, and an independent flip per cell scatters
    them as confetti rather than gathering them into a patch.

    Two changes make it a patch instead. The decision comes from this smooth
    field, so dressed cells are contiguous blobs — silt gathers where the water
    goes, grass grows where the wheels do not, and neither is a Bernoulli trial
    per square metre. And the field is evaluated per CORNER as well, so the
    quad shrinks toward its own centre wherever the field is only just over the
    threshold: the middle of a patch is solid and its margin is scalloped.
    """
    x, z = float(p[0]), float(p[2])
    return float(np.clip(
        0.5
        + 0.26 * math.sin(x * 0.29 + seed) * math.cos(z * 0.24 - seed * 0.7)
        + 0.17 * math.sin((x + z * 0.7) * 0.71 + seed * 1.9)
        + 0.09 * math.sin((x * 0.6 - z) * 1.63 - seed * 0.4), 0.0, 1.0))


def _carriageway(pv, net, st, aid):
    rng = rng_for(aid, "carriageway", st.id)
    surf = st.surface
    half = st.width * 0.5
    lanes = 8 if st.width >= 5.0 else 6
    uv = 0.5
    n = max(1, int(round(st.length / 2.0)))
    dseed = float(rng.uniform(0.0, 6.283))
    prev = None
    for k in range(n + 1):
        s = st.length * k / n
        if net.excluded(st, s):
            prev = None
            continue
        row = []
        for j in range(lanes + 1):
            u = -half + st.width * j / lanes
            x, z = st.offset(s, u)
            row.append(_p(x, LIFT + _profile(surf, abs(u) / half)
                          + rng.uniform(-surf.rough, surf.rough), z))
        if prev is not None:
            for j in range(lanes):
                pv.flat(surf.mat, prev[j], prev[j + 1], row[j + 1], row[j], uv)
                # The dressing: what has silted, grown or washed over the made
                # surface. "cobble, worn to dust" and "gravel and grass" are
                # authored descriptions of a street that is TWO materials, and
                # laying the second in patches over the first is cheaper and
                # far more convincing than inventing a third texture that is
                # the average of them.
                if surf.dress and surf.dress_amount > 0.0:
                    quad = (prev[j], prev[j + 1], row[j + 1], row[j])
                    # Threshold placed so the field clears it about
                    # `dress_amount` of the time; the jitter keeps two streets
                    # of the same surface from patching identically.
                    thr = 1.0 - surf.dress_amount + rng.uniform(-0.04, 0.04)
                    w = [_dress_field(q, dseed) for q in quad]
                    # THE BLACK LOZENGES (`ad-town-06` §4, eight frames, three
                    # reviews). The art director called them "flat, near-black
                    # leaf-shaped polygons lying on the road surface — dark
                    # arrowheads and lozenges, individually scattered, 0.2-0.5 m
                    # across", and three `--skip` proofs failed to find them
                    # because everybody was looking at the foliage. They are
                    # THIS: `earth` dressing on Bakers' Row, 14 mm proud of the
                    # cobble, measured at exactly +0.014 m over the carriageway
                    # at (22.3, 23.6) and (22.5, 25.1) in `craft-walk-02`.
                    #
                    # Two rules made a silt patch into a dart. `max(w) > thr`
                    # let a cell fire on ONE corner clearing the threshold, and
                    # the 0.10 corner floor then dragged the other three to a
                    # tenth of a cell — which is not a scalloped margin, it is a
                    # triangle with a point on it. Now the cell has to be inside
                    # the patch on AVERAGE to be laid at all, and its margin
                    # cells shrink to smaller quads rather than to slivers. Silt
                    # gathers in blobs; it does not fall in arrowheads.
                    if sum(w) * 0.25 > thr:
                        d = _p(0.0, 0.014, 0.0)
                        cx = sum(float(q[0]) for q in quad) * 0.25
                        cy = sum(float(q[1]) for q in quad) * 0.25
                        cz = sum(float(q[2]) for q in quad) * 0.25
                        pts = []
                        for q, wq in zip(quad, w):
                            # 1 well inside the patch, 0 at its margin. The
                            # corner is drawn toward the cell centre as the
                            # field falls away, which is what turns a run of
                            # rectangles into one blob with a ragged edge.
                            c = min(max((wq - thr) / 0.26, 0.0), 1.0)
                            f = 0.62 + 0.38 * c
                            pts.append(_p(cx + (float(q[0]) - cx) * f,
                                          cy + (float(q[1]) - cy) * f,
                                          cz + (float(q[2]) - cz) * f))
                        pv.flat(surf.dress, pts[0] + d, pts[1] + d,
                                pts[2] + d, pts[3] + d, uv)
        prev = row


def _carriageway_collision(ctx, net, st):
    """The carriageway is a WALKABLE SURFACE, never a solid.

    This is the venue whose bounding box sealed Ford Road in v1 — six cells of
    main street became one 96 m box because collision was inferred from
    geometry. Authored, a street is what it obviously is: a raised strip you
    stand on. One box per authored segment cannot do it either, because a 24 m
    leg climbs 0.9 m and a flat box is a third of a metre out at both ends, so
    the volume is subdivided to ~4 m and takes the ground at each end.
    """
    n = max(1, int(round(st.length / 4.0)))
    for k in range(n):
        s0, s1 = st.length * k / n, st.length * (k + 1) / n
        if net.excluded(st, (s0 + s1) * 0.5):
            continue
        p0, p1 = st.at(s0), st.at(s1)
        g0, g1 = st.ground(s0), st.ground(s1)
        ctx.collider(COL.segment_box(
            (p0[0], 0.0, p0[1]), (p1[0], 0.0, p1[1]), st.width + 0.5,
            min(g0, g1) - 0.4, max(g0, g1) + LIFT + st.surface.crown,
            kind="surface", tag="road", extend=0.4))


# ---------------------------------------------------------------------------
# 2. Channel, kerb, and drainage that reaches somewhere
# ---------------------------------------------------------------------------

def _edges(pv, net, st, aid, drops):
    """Channel and kerbs on both sides. Returns where the gullies go.

    `drops` are arc-length windows where the kerb is DROPPED for a doorway or a
    cart entry. A kerb line with no drops in it is a kerb line nobody ever
    crossed, and no barrel ever got over.
    """
    surf = st.surface
    if surf.edge in ("none", "verge"):
        return []
    rng = rng_for(aid, "edge", st.id)
    half = st.width * 0.5
    ch_w, ch_d = CHANNEL[surf.edge]
    kb_w, kb_rise = KERB[surf.edge]
    cham = 0.024

    for side in (-1, 1):
        # -- channel --------------------------------------------------------
        if ch_w > 0.02:
            n = max(1, int(round(st.length / 1.5)))
            inner, outer = [], []
            for k in range(n + 1):
                s = st.length * k / n
                if net.excluded(st, s):
                    if len(inner) > 1:
                        _strip(pv, surf.channel_mat, inner, outer)
                    inner, outer = [], []
                    continue
                deep = ch_d * (1.30 if st.cross_fall(s) * side > 0 else 0.75)
                x0, z0 = st.offset(s, side * half)
                x1, z1 = st.offset(s, side * (half + ch_w))
                inner.append(_p(x0, LIFT, z0))
                outer.append(_p(x1, LIFT - deep, z1))
            if len(inner) > 1:
                _strip(pv, surf.channel_mat, inner, outer)

        # -- kerbstones -----------------------------------------------------
        if kb_w <= 0.02:
            continue
        n = max(1, int(round(st.length / 0.72)))
        for k in range(n):
            s0, s1 = st.length * k / n, st.length * (k + 1) / n
            if net.excluded(st, (s0 + s1) * 0.5) or _in_window(drops, (s0 + s1) * 0.5):
                continue
            joint = rng.uniform(0.008, 0.030)
            y = LIFT + kb_rise + rng.uniform(-0.010, 0.008)
            foot = LIFT - ch_d - 0.34
            u_ch = side * (half + ch_w)
            u_cm = side * (half + ch_w + cham)
            u_kb = side * (half + ch_w + kb_w)
            af, ac, ab = (st.offset(s0 + joint, u) for u in (u_ch, u_cm, u_kb))
            bf, bc, bb = (st.offset(s1 - joint, u) for u in (u_ch, u_cm, u_kb))
            top_a = (_p(ac[0], y, ac[1]), _p(ab[0], y, ab[1]))
            top_b = (_p(bc[0], y, bc[1]), _p(bb[0], y, bb[1]))
            lo, hi = (0, 1) if side > 0 else (1, 0)
            # Top, arris chamfer, and the face down into the channel. Three
            # quads, six triangles: a chamfered `M.box` is forty-four and only
            # ever shows these three — the back is buried in the footway and
            # the ends are against the next stone. At 1,400 stones that is 8k
            # triangles of kerb instead of 60k, and the arris is the one edge
            # that HAS to be chamfered (Art Bible §6) because it is the edge
            # that catches the key light along a whole street.
            # Kerb and channel take the SAME material as each other. Partly
            # because a kerbstone and a channel really are the same dressed
            # granite, and partly for the budget: a separate `stone` here put a
            # thirteenth material into every kerbed cell for a surface the
            # player never looks straight at.
            km = surf.channel_mat
            pv.flat(km, top_a[lo], top_a[hi], top_b[hi], top_b[lo])
            pv.face(km, _p(ac[0], y, ac[1]), _p(af[0], y - cham, af[1]),
                    _p(bf[0], y - cham, bf[1]), _p(bc[0], y, bc[1]))
            pv.face(km, _p(af[0], y - cham, af[1]), _p(af[0], foot, af[1]),
                    _p(bf[0], foot, bf[1]), _p(bf[0], y - cham, bf[1]))

    return _gullies(st, ch_w > 0.02)


def _gullies(st, has_channel, min_gap=22.0):
    """Where a street's channel actually empties: the low points of its fall.

    A gutter that runs downhill to nowhere is a moulding. These come out of the
    ground profile rather than being placed by eye, so they stay right if the
    terrace levels move — and every channelled street gets one at its low end,
    which is where the water leaves it.
    """
    if not has_channel:
        return []
    ss, g = st.ground_profile
    if len(ss) < 6:
        return []
    out = []
    for i in range(2, len(ss) - 2):
        if (g[i] <= g[i - 1] and g[i] <= g[i + 1]
                and g[i] < g[i - 2] and g[i] < g[i + 2]):
            if out and abs(out[-1] - ss[i]) < min_gap:
                continue
            out.append(float(ss[i]))
    low_end = 0.0 if g[0] < g[-1] else float(st.length)
    if not out or min(abs(o - low_end) for o in out) > min_gap * 0.5:
        out.append(low_end)
    return out


# ---------------------------------------------------------------------------
# 3. Frontage: footway, threshold, dropped kerb, boot scraper
# ---------------------------------------------------------------------------

def _frontage(pv, ctx, props, net, st, aid):
    """The strip between the kerb and the building line, and what stands on it.

    A system rather than ninety placements: the plot polygon gives the building
    line, `door_positions` gives the doors, and how deep the footway is, what
    it is paved in, where the kerb drops and where the step and the scraper go
    all follow from those two.
    """
    surf = st.surface
    kb_w, kb_rise = KERB[surf.edge]
    ch_w, _cd = CHANNEL[surf.edge]
    half = st.width * 0.5
    back0 = half + ch_w + kb_w
    rng = rng_for(aid, "frontage", st.id)
    drops = []

    for f in net.by_street.get(st.id, ()):
        depth = min(max(f.gap - ch_w - kb_w, 0.0), MAX_FOOTWAY)
        mat = FOOTWAY_MAT.get(f.role, "earth")
        if not surf.made and f.role == "filler":
            mat = "earth"
        if depth > 0.30:
            n = max(1, int(round(max(f.s1 - f.s0, 0.6) / 1.6)))
            inner, outer = [], []
            for k in range(n + 1):
                s = f.s0 + (f.s1 - f.s0) * k / n
                if net.excluded(st, s):
                    continue
                x0, z0 = st.offset(s, f.side * back0)
                x1, z1 = st.offset(s, f.side * (back0 + depth))
                # Falls 2% back to the kerb, which is why the water reaches the
                # channel instead of standing against somebody's wall.
                inner.append(_p(x0, LIFT + kb_rise, z0))
                outer.append(_p(x1, LIFT + kb_rise + depth * 0.02, z1))
            if len(inner) > 1:
                _strip(pv, mat, inner, outer, 0.5 if mat != "earth" else 0.25)
                gm = st.ground((f.s0 + f.s1) * 0.5)
                # A frontage that presents its gable at a skew projects onto a
                # span of a few centimetres, and a hull of four near-collinear
                # points is not a volume. The paving is still worth laying; the
                # collider is not, because the carriageway's own surface volume
                # already reaches 0.25 m past the kerb.
                quad = [inner[0], inner[-1], outer[-1], outer[0]]
                if _area_xz(quad) > 0.45:
                    ctx.collider("hull",
                                 points=[(float(p[0]), float(p[2])) for p in quad],
                                 y0=gm - 0.6, y1=gm + LIFT + kb_rise + 0.06,
                                 kind="surface", tag="footway")

        for di, (dx, _dy, dz) in enumerate(f.doors):
            ds, _off, dist = st.project(dx, dz)
            if dist > half + f.gap + 1.8:
                continue
            # The kerb drops across the doorway: the detail that says the
            # paving and the building were laid by people who had to get a
            # barrel through that door.
            drops.append((ds - 1.15, ds + 1.15))
            fx, fz = _toward(dx, dz, st, 0.44)
            yaw = math.atan2(dx - fx, dz - fz)
            props.place("threshold", di % 3,
                        lambda sid=f.slot, d=di: SF.threshold_stone(f"{sid}.step{d}"),
                        fx, fz, yaw, dy=LIFT + kb_rise - 0.006)
            if surf.mat != "flag" and rng.random() < 0.55:
                sx, sz = _toward(dx, dz, st, 0.34)
                off = (0.80 + rng.uniform(0.0, 0.20)) * (1 if di % 2 else -1)
                sx += math.cos(yaw) * off
                sz -= math.sin(yaw) * off
                if not net.in_mass(sx, sz) and not net.on_carriageway(sx, sz, 0.1):
                    props.place("scraper", 0,
                                lambda: SF.boot_scraper(f"{aid}.scraper"),
                                sx, sz, yaw, dy=LIFT + kb_rise)
    return drops


def _toward(dx, dz, st, amount):
    """Move a door position `amount` metres toward the street centreline."""
    s, _off, _d = st.project(dx, dz)
    x, z = st.at(s)
    v = np.array([x - dx, z - dz], np.float64)
    n = float(np.hypot(v[0], v[1]))
    if n < 1e-6:
        return dx, dz
    return dx + v[0] / n * amount, dz + v[1] / n * amount


def _verges(pv, net, st, aid):
    """Made-up ground behind the kerb where no building line takes it.

    A road built 0.22 m proud of the field beside it needs its shoulder made up
    too, or the kerb stands out of the grass like a set piece and the paving
    ends in a knife edge. This is also the strip that carries the furniture.
    """
    surf = st.surface
    kb_w, kb_rise = KERB[surf.edge]
    ch_w, _cd = CHANNEL[surf.edge]
    back0 = st.width * 0.5 + ch_w + kb_w
    depth = max(st.verge, 0.55)
    covered = {}
    for f in net.by_street.get(st.id, ()):
        if min(max(f.gap - ch_w - kb_w, 0.0), MAX_FOOTWAY) > 0.30:
            covered.setdefault(f.side, []).append((f.s0 - 0.4, f.s1 + 0.4))

    n = max(1, int(round(st.length / 2.5)))
    for side in (-1, 1):
        wins = covered.get(side, [])
        a, b = [], []
        for k in range(n + 1):
            s = st.length * k / n
            if net.excluded(st, s) or _in_window(wins, s):
                if len(a) > 1:
                    _strip(pv, "earth", a, b)
                a, b = [], []
                continue
            x0, z0 = st.offset(s, side * back0)
            x1, z1 = st.offset(s, side * (back0 + depth))
            a.append(_p(x0, LIFT + kb_rise, z0))
            # The far edge dies into the natural ground, which is what stops
            # the made surface being a slab standing on a field.
            b.append(_p(x1, 0.012, z1))
        if len(a) > 1:
            _strip(pv, "earth", a, b)


# ---------------------------------------------------------------------------
# 4. Junctions
# ---------------------------------------------------------------------------

def _junction(pv, ctx, props, net, j, aid):
    """Where two streets meet, the paving resolves instead of overlapping.

    They used to just overlap: two ribbons of different materials z-fighting in
    a cross. A junction is a piece of design — TOWN_PLAN §4 names fourteen and
    says what each one does — so the higher-class street's surface is laid as
    one apron over the whole mouth, both carriageways run into it, the corners
    are protected, and the unmade ones get crossing stones.
    """
    st = net.streets[j.primary]
    surf = st.surface
    rng = rng_for(aid, "junction", f"{j.x:.1f}_{j.z:.1f}")

    # The apron outline: the convex hull of every mouth, so a staggered
    # crossroads (J7) and a two-tee fork (J3) both come out as the shape the
    # streets actually make rather than as a disc.
    pts = []
    for (sid, s, is_end) in j.members:
        m = net.streets[sid]
        reach = j.radius + m.width * 0.25
        for ds in ((0.0,) if is_end else (-reach, reach)):
            ss = min(max(s + ds, 0.0), m.length)
            for u in (-1, 1):
                pts.append(m.offset(ss, u * (m.width * 0.5 + 0.55)))
    if len(pts) < 3:
        return
    hull = COL.convex_hull_xz(pts)
    cx, cz = j.x, j.z

    # 6 mm proud of the primary's own carriageway. The minor streets are CUT
    # OUT of the junction (see `Net.cut`), but the primary runs through it and
    # the apron lies over the top of it: same material, so the overlap is
    # invisible, and the offset is what keeps two coplanar surfaces from
    # z-fighting into a chequerboard. A re-laid junction standing a few
    # millimetres proud of the road either side of it is also simply true.
    APRON = 0.006

    def at(t, e):
        x = cx + (e[0] - cx) * t
        z = cz + (e[1] - cz) * t
        d = math.hypot(x - cx, z - cz) / max(j.radius, 1e-3)
        return _p(x, LIFT + APRON + surf.crown * 0.55 * max(0.0, 1.0 - d * d)
                  + rng.uniform(-surf.rough, surf.rough), z)

    # Fan from the centre with each hull edge subdivided, so the apron follows
    # the ground rather than spanning it: a 12 m junction laid as one plane is
    # a 0.4 m step at its downhill lip.
    rings = 3
    for i in range(len(hull)):
        a = np.asarray(hull[i], float)
        b = np.asarray(hull[(i + 1) % len(hull)], float)
        seg = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 1.6))
        for q in range(seg):
            e0 = a + (b - a) * (q / seg)
            e1 = a + (b - a) * ((q + 1) / seg)
            for r in range(rings):
                t0, t1 = r / rings, (r + 1) / rings
                if r == 0:
                    pv.tri(surf.mat, _p(cx, LIFT + APRON + surf.crown * 0.55, cz),
                           at(t1, e0), at(t1, e1))
                else:
                    pv.flat(surf.mat, at(t0, e0), at(t0, e1),
                            at(t1, e1), at(t1, e0))

    gc = st.ground(j.arc_of(j.primary) or 0.0)
    ctx.collider("hull", points=[(float(p[0]), float(p[1])) for p in hull],
                 y0=gc - 0.6, y1=gc + LIFT + surf.crown + 0.05,
                 kind="surface", tag="junction")

    # Crossing stones where the junction is unmade. The oldest street detail
    # there is, and it reads instantly as "this gets wet".
    if not surf.made:
        for (sid, s, _e) in j.members:
            m = net.streets[sid]
            for k in (-1, 0, 1):
                x, z = m.offset(min(max(s, 0.0), m.length), k * m.width * 0.30)
                props.place("crossing", abs(k),
                            lambda kk=k: _crossing_stone(f"{aid}.cross{kk}"),
                            x, z, _yaw_x(m.tangent(s)), dy=LIFT + 0.05)
            break

    # Corner protection. TOWN_PLAN J4 asks for a chamfered corner stone and one
    # bollard; J5 for six bollards keeping carts off the stalls; the gate jambs
    # for spur stones "deeply scored by nave hubs".
    for (sid, s, _is_end) in j.members:
        if sid == j.primary:
            continue
        m = net.streets[sid]
        away = 1.0 if s < m.length * 0.5 else -1.0
        for k in range(2 if j.kind == "cross" else 1):
            for side in (-1, 1):
                ss = min(max(s + away * (j.radius + 1.0 + k * 1.6), 0.0), m.length)
                x, z = m.offset(ss, side * (m.width * 0.5 + 0.80))
                if net.in_mass(x, z, 0.3) or net.on_carriageway(x, z, 0.1):
                    continue
                if surf.made:
                    props.place("bollard", k % 3,
                                lambda vv=k: SF.bollard(f"{aid}.bollard{vv}"),
                                x, z, rng.uniform(0, 6.28), dy=LIFT * 0.5)
                else:
                    props.place("spur", k % 2,
                                lambda vv=k: SF.spur_stone(f"{aid}.spur{vv}"),
                                x, z, _yaw_z(m.tangent(ss)))

    # A finger post where the choice is a real one.
    if j.kind in ("cross", "fork") or (j.kind == "tee" and st.rank >= 3):
        for _try in range(10):
            a = rng.uniform(0, 6.28)
            d = j.radius + rng.uniform(0.7, 1.8)
            x, z = cx + math.cos(a) * d, cz + math.sin(a) * d
            if net.in_mass(x, z, 0.6) or net.on_carriageway(x, z, 0.5):
                continue
            props.place("signpost", int(rng.integers(0, 3)),
                        lambda n=len(j.members): SF.signpost(
                            f"{aid}.signpost.{j.x:.0f}_{j.z:.0f}", arms=n),
                        x, z, rng.uniform(0, 6.28), dy=LIFT * 0.4)
            break


def _crossing_stone(asset_id):
    rng = rng_for(asset_id, "crossing")
    m = M.box(0.60 + rng.uniform(-0.05, 0.05), 0.15,
              0.44 + rng.uniform(-0.04, 0.04), 0.024, "stone")
    m.rotate_y(rng.uniform(-0.06, 0.06))
    return M.Group().add(m)


# ---------------------------------------------------------------------------
# 5. The fall: cross-drains and flights
# ---------------------------------------------------------------------------

def _cross_drains(pv, props, net, st, aid):
    """Ribs across a cart road too steep to shed water lengthwise.

    Above ~8% a longitudinal gutter stops working — the water runs down the
    middle of the carriageway instead — so a made road gets a stone rib set on
    the skew every three metres, throwing the run-off to the low side and
    giving an iron tyre something to bite on. From the gameplay camera they are
    also the thing that tells the player the street is climbing.
    """
    runs = net.drains.get(st.id, ())
    if not runs:
        return 0
    half = st.width * 0.5
    made = 0
    for (s0, s1, _drop) in runs:
        n = max(1, int((s1 - s0) / 3.0))
        for k in range(n):
            s = s0 + (s1 - s0) * (k + 0.5) / n
            if net.excluded(st, s) or net.in_junction(*st.at(s)):
                continue
            skew = 0.22 * (1 if st.cross_fall(s) >= 0 else -1)
            lo, hi = [], []
            for q in range(7):
                u = -half + st.width * q / 6
                sq = s + u * skew
                pf = _profile(st.surface, abs(u) / half)
                x0, z0 = st.offset(sq, u)
                x1, z1 = st.offset(sq + 0.28, u)
                lo.append(_p(x0, LIFT + pf - 0.030, z0))
                hi.append(_p(x1, LIFT + pf + 0.032, z1))
            _strip(pv, "sett", lo, hi)
            made += 1
        # The rib run needs somewhere to put the water at its foot.
        s_end = s1 if st.ground(s1) < st.ground(s0) else s0
        side = st.cross_fall(s_end) or 1
        x, z = st.offset(s_end, side * (half + 0.45))
        if not net.in_junction(x, z):
            props.place("gully", 0, lambda: SF.gully_stone(f"{aid}.gully"),
                        x, z, _yaw_z(st.tangent(s_end)), dy=LIFT - 0.06)
    return made


def _flight(av, ctx, props, net, st, aid):
    """A stepped run where a footway crosses a scarp, with a handrail.

    TOWN_PLAN authors eight step flights through the terrace scarps and
    `venues/terrain.py` builds those. These are the OTHER ones: the places a
    lane runs at 30-57% because the ground does, which is not walkable and
    reads as an error. Rise and going follow Art Bible §3, and the riser count
    is set so the flight lands exactly on both ends.

    Built in ABSOLUTE Y and laid into `av`, the accumulator that is NOT draped.
    A flight spans the fall by definition: draping one adds the ground height a
    second time, which floats the whole staircase a metre and a half over the
    lane and is exactly what the first version of this did.
    """
    built = 0
    out = M.Group()
    for ri, (s0, s1, drop) in enumerate(net.flights.get(st.id, ())):
        top_s, bot_s = (s0, s1) if drop < 0 else (s1, s0)
        top = st.ground(top_s) + LIFT
        fall = top - (st.ground(bot_s) + LIFT)
        if fall < 0.35:
            continue
        n = max(2, int(round(fall / 0.175)))
        rise = fall / n
        going = max(0.28, abs(s1 - s0) / n)
        half = st.width * 0.5
        d = 1.0 if bot_s > top_s else -1.0
        bot_y = top - fall - 0.55       # the cheeks run down into the bank

        for k in range(n):
            y = top - (k + 1) * rise
            sa = top_s + d * (k * going)
            sb = top_s + d * ((k + 1) * going)
            a0, a1 = st.offset(sa, -half), st.offset(sa, half)
            b0, b1 = st.offset(sb, -half), st.offset(sb, half)
            quad = (a0, a1, b1, b0) if d > 0 else (a1, a0, b0, b1)
            av.flat("sett", _p(quad[0][0], y, quad[0][1]),
                    _p(quad[1][0], y, quad[1][1]), _p(quad[2][0], y, quad[2][1]),
                    _p(quad[3][0], y, quad[3][1]))
            av.face("sett", _p(b0[0], y, b0[1]), _p(b0[0], y - rise - 0.04, b0[1]),
                    _p(b1[0], y - rise - 0.04, b1[1]), _p(b1[0], y, b1[1]))
            # Cheeks, so the flight is CARRIED rather than hanging in the lane.
            # Without them a run of treads with no sides and no underside is a
            # stack of floating slabs from any angle below the nosing.
            for e0, e1 in ((a0, b0), (a1, b1)):
                av.face("sett", _p(e0[0], y, e0[1]), _p(e0[0], bot_y, e0[1]),
                        _p(e1[0], bot_y, e1[1]), _p(e1[0], y, e1[1]))
            mid = st.at((sa + sb) * 0.5)
            ctx.collider("box", center=(mid[0], y - (rise + 0.18) * 0.5, mid[1]),
                         half=(half + 0.10, (rise + 0.18) * 0.5, going * 0.60),
                         rot_y=_yaw_x(st.tangent((sa + sb) * 0.5)),
                         kind="surface", tag="street_steps",
                         cid=f"{st.id}.flight{ri}.{k:02d}")

        # A handrail down the uphill side, standing on the nosings. Not
        # instanced: it is one of the few things here that lives in absolute Y.
        for k in range(0, n, 3):
            y = top - (k + 1) * rise
            s = top_s + d * ((k + 0.7) * going)
            x, z = st.offset(s, -half + 0.18)
            ln = max(going * 3.0, 0.95)
            hr = SF.handrail(f"{aid}.{st.id}.rail{ri}.{k}", ln, posts=2)
            hr.rotate_y(_yaw_x(st.tangent(s)))
            hr.translate(x, y, z)
            out.add(props.pack(hr))
            ctx.collider("box", center=(x, y + 0.5, z), half=(ln * 0.5, 0.5, 0.06),
                         rot_y=_yaw_x(st.tangent(s)), tag="handrail")
        built += 1
    if out.tri_count:
        ctx.emit(out)
    return built


# ---------------------------------------------------------------------------
# 6. Back alleys
# ---------------------------------------------------------------------------

def _alley(pv, ctx, props, net, st, aid):
    """What makes a back lane read as a back lane (Art Bible §7).

    Narrow, no kerbs, a drain down the MIDDLE rather than at the sides because
    nobody ever built a channel here, laundry across it at first-floor height,
    and everything the plots behind it have nowhere else to put. The density of
    a town is sold in its alleys, and Hearthmere had none built.
    """
    rng = rng_for(aid, "alley", st.id)
    half = st.width * 0.5

    n = max(1, int(round(st.length / 1.4)))
    lo, hi = [], []
    for k in range(n + 1):
        s = st.length * k / n
        if net.excluded(st, s):
            continue
        x0, z0 = st.offset(s, -0.17)
        x1, z1 = st.offset(s, 0.17)
        lo.append(_p(x0, LIFT - 0.058, z0))
        hi.append(_p(x1, LIFT - 0.058, z1))
    if len(lo) > 1:
        _strip(pv, "mud", lo, hi)

    lines = 0
    for i, s in enumerate(st.stations(4.6, margin=2.0)):
        x, z = st.at(s)
        if net.in_junction(x, z, 1.0):
            continue
        t = st.tangent(s)
        if i % 2 == 0 and st.width <= 3.4:
            # A pole each side and a line between them. Poles rather than wall
            # anchors because half these lanes have a 2.9 m shed down one side,
            # and a washing line disappearing into a roof is worse than none.
            ax, az = st.offset(s, -(half + 0.40))
            bx, bz = st.offset(s + 0.9, half + 0.40)
            if net.in_mass(ax, az, 0.2) or net.in_mass(bx, bz, 0.2):
                continue
            props.place("laundrypole", 0,
                        lambda: SF.laundry_prop(f"{aid}.pole0"), ax, az, _yaw_x(t))
            props.place("laundrypole", 1,
                        lambda: SF.laundry_prop(f"{aid}.pole1"), bx, bz,
                        _yaw_x(t) + math.pi)
            ay = float(TERR.height(ax, az)) + 3.24
            by = float(TERR.height(bx, bz)) + 3.20
            ctx.emit(props.pack(SF.washing_line(
                f"{aid}.{st.id}.wash{i}", (ax, ay, az), (bx, by, bz),
                sag=0.20, count=3)))
            lines += 1
            continue

        side = 1 if (i // 2) % 2 else -1
        ux, uz = st.offset(s, side * (half + 0.60))
        if net.in_mass(ux, uz, 0.15):
            continue
        yaw = _yaw_x(t)
        v = i % 3
        pick = rng.random()
        if pick < 0.32:
            props.place("alleywood", v,
                        lambda vv=v: SF.woodpile(f"{aid}.awood{vv}", length=1.6,
                                                 height=0.82),
                        ux, uz, yaw)
        elif pick < 0.58:
            props.place("barrel", v, lambda vv=v: K.barrel(f"{aid}.bar{vv}"),
                        ux, uz, rng.uniform(0, 6.28))
        elif pick < 0.80:
            props.place("butt", v % 2, lambda vv=v: SF.water_butt(f"{aid}.butt{vv}"),
                        ux, uz, rng.uniform(0, 6.28))
        else:
            props.place("crates", v % 2,
                        lambda vv=v: PR.crate_stack(f"{aid}.cr{vv}", count=3),
                        ux, uz, rng.uniform(0, 6.28))

    # Weeds in the joints: the alley is never dry, which is the note TOWN_PLAN
    # attaches to Bell Alley by name.
    for s in st.stations(1.8, margin=0.5):
        for side in (-1, 1):
            x, z = st.offset(s, side * (half - rng.uniform(0.05, 0.32)))
            if rng.random() < 0.40 and not net.in_junction(x, z):
                props.place("weeds", 0,
                            lambda: VG.joint_weeds(f"{aid}.weeds", count=5),
                            x, z, rng.uniform(0, 6.28), dy=LIFT - 0.03)
    return lines


# ---------------------------------------------------------------------------
# 7. Street furniture, distributed by rule
# ---------------------------------------------------------------------------

# Weighted tables per street class. This is the whole of the "by rule, not by
# hand" requirement: the network is walked at ~9 m and each station draws from
# the table for its class, so a layout change moves the furniture with it.
TABLE = {
    "primary":   (("lamp", 20), ("hitchpost", 15), ("bollard", 8), ("butt", 7),
                  ("mount", 5), ("bench", 8), ("cart", 4), ("trough", 3),
                  ("planter", 13), ("nothing", 12)),
    "secondary": (("lamp", 12), ("hitchpost", 13), ("woodpile", 13), ("butt", 11),
                  ("rail", 7), ("crates", 7), ("barrels", 9), ("cart", 4),
                  ("weeds", 9), ("planter", 5), ("nothing", 12)),
    "lane":      (("woodpile", 22), ("barrels", 13), ("crates", 9), ("butt", 9),
                  ("weeds", 16), ("midden", 8), ("nothing", 20)),
    "alley":     (("woodpile", 20), ("barrels", 15), ("butt", 11), ("weeds", 22),
                  ("nothing", 28)),
    "steps":     (("nothing", 1),),
}


def _pick(rng, table):
    r = rng.random() * sum(w for _k, w in table)
    for k, w in table:
        r -= w
        if r <= 0:
            return k
    return table[-1][0]


# Discs on which no street furniture may stand, in world XZ.
#
# A market square keeps its crossing clear. Hearthmere's is the worn diagonal
# from the north-west mouth to the fountain — WORLD_BIBLE, "Market Place":
# *cobbles worn into desire paths, polished smooth along the diagonal everyone
# actually walks* — and `venues/market_square.py::_paving` already polishes the
# stones along it. A lamp standard planted in the middle of that crossing is
# wrong twice: nobody would put one there, and it is the object the `square`
# hero camera looks straight through.
#
# It has been the same object in the same place for three consecutive art
# director rejections: pass 02, pass 03 and ad-town-04 §12 all read `t-square`
# and all three name the lamp bisecting the frame top to bottom and cropping the
# fountain. ad-town-04 also records the instrument consequence — `valueBands`
# for that view comes back `None`, because the lamp fills the whole foreground
# band and the measurement has nothing to measure. The sequencer that places
# furniture works in street space and cannot see a plaza diagonal, so the
# plaza states it here.
KEEP_CLEAR = [
    (-6.4, -6.4, 4.6, "the market place's worn diagonal: the north-west "
                      "crossing to the fountain, and the `square` hero camera "
                      "axis (ad-town-04 §12)"),
]


def _in_keep_clear(x, z):
    for (cx, cz, r, _why) in KEEP_CLEAR:
        if (x - cx) ** 2 + (z - cz) ** 2 <= r * r:
            return True
    return False


def _furniture(ctx, props, net, st, aid):
    """One vertical element every 8-10 m along every street. Art Bible §7.

    The streets had none, which is the single largest reason they read as a
    path across a field: at a 1.62 m eye there was nothing at all between the
    paving and the roofline for forty metres at a stretch.
    """
    rng = rng_for(aid, "furniture", st.id)
    surf = st.surface
    kb_w, kb_rise = KERB[surf.edge]
    ch_w, _cd = CHANNEL[surf.edge]
    verge_u = st.width * 0.5 + ch_w + kb_w + 0.44
    top_dy = LIFT + kb_rise if surf.kerbed else LIFT * 0.35
    # NOT `hash()`: Python salts string hashing per process, which would make
    # the side a prop lands on change between builds and void the review diff.
    flip = sum(ord(c) for c in st.id) % 2
    placed = 0

    for i, s in enumerate(st.stations(STATION, margin=3.0)):
        kind = _pick(rng, TABLE.get(st.cls, TABLE["secondary"]))
        if kind == "nothing":
            continue
        px, pz = st.at(s)
        if net.in_junction(px, pz, 1.0) or net.excluded(st, s):
            continue
        # Prefer the side with room. A prop half inside a wall is worse than no
        # prop, because the eye finds it and then distrusts the whole frame.
        spot = None
        for side in ((1, -1) if (i + flip) % 2 else (-1, 1)):
            x, z = st.offset(s, side * verge_u)
            if net.in_mass(x, z, 0.35) or _door_near(net, st, x, z) < 1.5:
                continue
            if _in_keep_clear(x, z):
                continue
            spot = (x, z, side)
            break
        if spot is None:
            continue
        x, z, side = spot
        t = st.tangent(s)
        g = st.ground(s)
        v = i % 3
        placed += 1

        if kind == "lamp":
            props.place("lamp", v, lambda vv=v: SF.lamp_post(f"{aid}.lamp{vv}"),
                        x, z, rng.uniform(0, 6.28), dy=top_dy)
            ctx.entity(f"{aid}.lamp.{st.id}.{i:02d}", "prop.lantern",
                       (x, g + top_dy + 2.5, z), cell=BLD.cell_of(x, z),
                       light={"color": "#FFB35C", "intensity": 1.4, "range": 8.0})
            ctx.collider("cylinder", center=(x, g + top_dy + 0.5, z),
                         radius=0.16, height=1.0, tag="lamp_post")
        elif kind == "hitchpost":
            props.place("hitchpost", v,
                        lambda vv=v: SF.hitching_post(f"{aid}.hitch{vv}"),
                        x, z, rng.uniform(0, 6.28), dy=top_dy)
            ctx.collider("cylinder", center=(x, g + top_dy + 0.55, z),
                         radius=0.13, height=1.1, tag="hitching_post")
        elif kind == "rail":
            props.place("hitchrail", v % 2,
                        lambda vv=v: SF.hitching_rail(f"{aid}.hrail{vv}"),
                        x, z, _yaw_x(t), dy=top_dy)
            ctx.collider("box", center=(x, g + top_dy + 0.55, z),
                         half=(1.55, 0.55, 0.12), rot_y=_yaw_x(t),
                         tag="hitching_rail")
        elif kind == "bollard":
            for k in (-1, 0, 1):
                bx, bz = st.offset(s + k * 1.3, side * verge_u)
                vv = (v + abs(k)) % 3
                props.place("bollard", vv,
                            lambda w=vv: SF.bollard(f"{aid}.bol{w}"),
                            bx, bz, rng.uniform(0, 6.28), dy=LIFT * 0.5)
        elif kind == "mount":
            props.place("mount", v % 2,
                        lambda vv=v: SF.mounting_block(f"{aid}.mount{vv}"),
                        x, z, _yaw_z(t), dy=top_dy)
            ctx.collider("box", center=(x, g + top_dy + 0.31, z),
                         half=(0.48, 0.31, 0.44), rot_y=_yaw_z(t),
                         kind="surface", tag="mounting_block")
        elif kind == "trough":
            props.place("trough", v % 2,
                        lambda vv=v: SF.horse_trough(f"{aid}.trough{vv}"),
                        x, z, _yaw_x(t), dy=top_dy)
            ctx.collider("box", center=(x, g + top_dy + 0.28, z),
                         half=(0.98, 0.28, 0.34), rot_y=_yaw_x(t), tag="trough")
        elif kind == "butt":
            props.place("butt", v % 2, lambda vv=v: SF.water_butt(f"{aid}.wb{vv}"),
                        x, z, rng.uniform(0, 6.28), dy=top_dy)
            ctx.collider("cylinder", center=(x, g + top_dy + 0.48, z),
                         radius=0.36, height=0.96, tag="water_butt")
        elif kind == "woodpile":
            props.place("woodpile", v, lambda vv=v: SF.woodpile(f"{aid}.wp{vv}"),
                        x, z, _yaw_x(t))
            ctx.collider("box", center=(x, g + 0.5, z), half=(1.20, 0.5, 0.32),
                         rot_y=_yaw_x(t), tag="woodpile")
        elif kind == "midden":
            props.place("midden", v % 2, lambda vv=v: SF.midden(f"{aid}.mid{vv}"),
                        x, z, rng.uniform(0, 6.28))
        elif kind == "barrels":
            props.place("barrel", v, lambda vv=v: K.barrel(f"{aid}.bar{vv}"),
                        x, z, rng.uniform(0, 6.28), dy=top_dy)
            ctx.collider("cylinder", center=(x, g + top_dy + 0.44, z),
                         radius=0.33, height=0.88, tag="barrel")
        elif kind == "crates":
            props.place("crates", v % 2,
                        lambda vv=v: PR.crate_stack(f"{aid}.cr{vv}", count=3),
                        x, z, rng.uniform(0, 6.28), dy=top_dy)
            ctx.collider("box", center=(x, g + top_dy + 0.45, z),
                         half=(0.38, 0.45, 0.38), tag="crates")
        elif kind == "bench":
            props.place("bench", v % 2, lambda vv=v: K.bench(f"{aid}.bench{vv}"),
                        x, z, _yaw_x(t), dy=top_dy)
            ctx.collider("box", center=(x, g + top_dy + 0.24, z),
                         half=(0.95, 0.24, 0.18), rot_y=_yaw_x(t),
                         kind="surface", tag="bench")
        elif kind == "planter":
            props.place("planter", v, lambda vv=v: _planter(f"{aid}.planter{vv}"),
                        x, z, rng.uniform(0, 6.28), dy=top_dy)
        elif kind == "cart":
            props.place("cart", v % 2,
                        lambda vv=v: PR.handcart(f"{aid}.cart{vv}", tipped=vv == 0),
                        x, z, rng.uniform(0, 6.28), dy=LIFT * 0.4)
            ctx.collider("box", center=(x, g + 0.5, z), half=(0.95, 0.5, 0.55),
                         tag="handcart")
        elif kind == "weeds":
            for k in range(4):
                wx, wz = st.offset(s + rng.uniform(-2.6, 2.6),
                                   side * (verge_u + rng.uniform(-0.25, 0.55)))
                props.place("tussock", k % 2,
                            lambda w=k % 2: VG.tussock(f"{aid}.tuss{w}"),
                            wx, wz, rng.uniform(0, 6.28), dy=0.01)
    return placed


def _planter(asset_id):
    """A half-barrel of herbs standing against a kerb."""
    out = M.Group()
    out.add(M.lathe([(0.30, 0.0), (0.335, 0.16), (0.325, 0.42)], 12,
                    "oak_weathered", close_top=False))
    hoop = M.ring(0.336, 0.030, "iron", 12)
    hoop.translate(0, 0.36, 0)
    out.add(hoop)
    out.add(M.lathe([(0.0, 0.36), (0.30, 0.38)], 12, "earth"))
    leaves = K.planter_plants(f"{asset_id}.plants", 0.46, 5, "foliage_flower", 0.14)
    leaves.translate(0, 0.40, 0)
    out.add(leaves)
    return out


def _door_near(net, st, x, z):
    best = 1e9
    for f in net.by_street.get(st.id, ()):
        for (dx, _dy, dz) in f.doors:
            best = min(best, math.hypot(dx - x, dz - z))
    return best


# ---------------------------------------------------------------------------
# 8. The set pieces the plan names by hand
# ---------------------------------------------------------------------------

def _set_pieces(ctx, props, net, aid):
    """The handful of objects TOWN_PLAN puts at a named place for a reason.

    Everything else on the street is placed by rule. These are not, because a
    rule that happened to put them elsewhere would be a rule contradicting the
    plan: the Fork's trough is *why* its corner is worn, and Well Lane is named
    after the thing at the end of it.
    """
    made = []

    for j in net.junctions:
        # J3, the Fork: "a triangular kerbed island carrying the horse trough —
        # which is *why* carts swing wide here and why the corner is worn."
        if j.primary == "ford_road" and abs(j.z + 61.7) < 3.5:
            x, z = j.x - 2.7, j.z + 0.5
            props.place("trough", 9, lambda: SF.horse_trough(f"{aid}.fork.trough"),
                        x, z, 0.35, dy=LIFT)
            g = float(TERR.height(x, z))
            ctx.collider("box", center=(x, g + LIFT + 0.28, z),
                         half=(0.98, 0.28, 0.34), rot_y=0.35, tag="trough")
            ctx.entity(f"{aid}.trough.fork", "prop.trough", (x, g + LIFT, z),
                       cell=BLD.cell_of(x, z), verbs=["inspect"])
            made.append("Fork trough")
            break

    st = net.streets.get("well_lane")
    if st is not None:
        s = st.length * 0.40
        x, z = st.offset(s, st.width * 0.5 + 1.45)
        if not net.in_mass(x, z, 0.6):
            g = float(TERR.height(x, z))
            props.place("well", 0, lambda: SF.well_head(f"{aid}.well"), x, z, 0.6)
            ctx.collider("cylinder", center=(x, g + 0.4, z), radius=0.82,
                         height=0.8, tag="well")
            ctx.entity(f"{aid}.well.public", "prop.well", (x, g, z),
                       cell=BLD.cell_of(x, z), verbs=["inspect"])
            made.append("public well")

    # Art Bible §7: every street terminates in something worth walking toward.
    # Waymarkers on the climb out of the south gate do that for Ford Road's
    # south end without inventing a venue. These entity ids already existed and
    # are never recycled — they MOVE. They used to stand at z = +44, which is
    # inside the town, on the smiths' ramp, 34 m short of the gate.
    ford = net.streets["ford_road"]
    s = ford.length - 10.0
    for side, tag in ((-1, "w"), (1, "e")):
        x, z = ford.offset(s, side * 5.6)
        g = float(TERR.height(x, z))
        props.place("waymarker", 0 if side < 0 else 1,
                    lambda t=tag: VG.milestone(f"{aid}.waymarker.{t}"),
                    x, z, _yaw_z(ford.tangent(s)))
        ctx.collider("cylinder", center=(x, g + 0.55, z), radius=0.30,
                     height=1.1, tag="waymarker")
        ctx.entity(f"{aid}.waymarker.{tag}", "prop.waymarker", (x, g, z),
                   cell=BLD.cell_of(x, z), verbs=["inspect"])
    made.append("south-road waymarkers")

    # A mounting block at the gates, which is where riders actually arrive.
    for name, (gx, gz) in (("south", (1.0, 78.5)), ("west", (-79.0, -13.0))):
        for side in (-1, 1):
            x, z = gx + side * 5.4, gz + 2.6
            if net.in_mass(x, z, 0.4) or TERR.is_water(x, z):
                continue
            props.place("mount", 5, lambda: SF.mounting_block(f"{aid}.gatemount"),
                        x, z, 0.0)
            made.append(f"{name} gate block")
            break
    return made


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build(ctx: VenueContext, asset_id="hm.streets"):
    net = Net()
    pv = Paving()          # local Y: draped onto the ground at the end
    av = Paving()          # absolute Y: things that must NOT follow the ground
    props = Props(ctx)
    stats = {"drains": 0, "flights": 0, "gullies": 0, "furniture": 0,
             "alleys": 0, "lines": 0}

    for sid, st in net.streets.items():
        _carriageway(pv, net, st, asset_id)
        _carriageway_collision(ctx, net, st)
        drops = _frontage(pv, ctx, props, net, st, asset_id)
        gullies = _edges(pv, net, st, asset_id, drops)
        _verges(pv, net, st, asset_id)
        stats["drains"] += _cross_drains(pv, props, net, st, asset_id)
        stats["flights"] += _flight(av, ctx, props, net, st, asset_id)
        if st.cls in ("alley", "lane"):
            stats["lines"] += _alley(pv, ctx, props, net, st, asset_id)
            stats["alleys"] += 1
        stats["furniture"] += _furniture(ctx, props, net, st, asset_id)

        ch_w = CHANNEL[st.surface.edge][0]
        for s in gullies:
            side = st.cross_fall(s) or 1
            x, z = st.offset(s, side * (st.width * 0.5 + ch_w * 0.5))
            if net.in_junction(x, z):
                continue
            props.place("gully", 0, lambda: SF.gully_stone(f"{asset_id}.gully"),
                        x, z, _yaw_z(st.tangent(s)), dy=LIFT - 0.055)
            stats["gullies"] += 1

    for j in net.junctions:
        _junction(pv, ctx, props, net, j, asset_id)

    pieces = _set_pieces(ctx, props, net, asset_id)

    # ONE drape for the whole made surface. `terrain.drape` adds the ground
    # height to each vertex's existing Y, so a kerb top authored at 0.295 stays
    # 0.295 m proud of whatever the ground is doing under it — and it does that
    # in one vectorised call per material rather than forty thousand scalar
    # ones. Everything already in absolute Y (the flights, the washing lines)
    # was emitted directly and is not in this group.
    ctx.emit(TERR.drape(pv.group()))
    ctx.emit(av.group())
    n_props = props.flush()
    _report(net, stats, n_props, pieces)


CELLS = sorted({BLD.cell_of(float(p[0]), float(p[1]))
                for st in RN.load().values() for p in st.P})


def _report(net, stats, n_props, pieces):
    total = sum(s.length for s in net.streets.values())
    print(f"      {len(net.streets)} streets, {total:.0f} m of carriageway; "
          f"{len(net.junctions)} junctions, {len(net.fronts)} frontages, "
          f"{sum(len(f.doors) for f in net.fronts)} doors served")
    by_mat = {}
    for st in net.streets.values():
        by_mat.setdefault(st.surface.mat, []).append(st.id)
    print("      surfaces: " + ", ".join(f"{k} x{len(v)}"
                                         for k, v in sorted(by_mat.items())))
    print(f"      fall: {stats['flights']} street flights, {stats['drains']} "
          f"cross-drains, {stats['gullies']} gullies")
    print(f"      alleys: {stats['alleys']} dressed, {stats['lines']} washing lines")
    print(f"      furniture: {stats['furniture']} stations, {n_props} instanced "
          f"props; " + ", ".join(pieces))
