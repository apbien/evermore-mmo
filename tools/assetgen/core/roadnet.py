"""The street network as data: surfaces, geometry queries, junctions, frontage.

`content/town/hearthmere.json` authors fifteen streets as centrelines with a
width, a class, a verge and a **prose** surface description — "granite setts",
"gravel, stone edged", "cobble, worn to dust". Until now the one consumer of
that record, `venues/streets.py`, matched those strings against
`{"cobble", "dirt", "stone"}` with a silent `.get(..., "cobble")` fallback, so
twelve of the fifteen streets were built in the wrong material and eleven of
them silently lost their kerbs. A vocabulary that fails quietly is worse than
no vocabulary, because the build reports success either way.

So the vocabulary is data here, it is exhaustive, and an unrecognised surface is
a build error naming the whole set. Everything else in this module is the
geometry a road network needs before it can be built:

    net   = roadnet.load()                      # {id: Street}
    st    = net["ford_road"]
    st.surface.mat                              # "sett"
    st.at(s), st.tangent(s), st.grade(s)        # arc-length parameterised
    roadnet.junctions(net)                      # where two streets resolve
    roadnet.frontages(net, slots, doors)        # building line per street
    roadnet.steep_runs(st)                      # where the fall needs work

No geometry, no materials, no emission — that is `venues/streets.py`'s job.
This is the model both it and any later consumer (the wall's gates, the market
place's mouths) read, so that two generators cannot disagree about where Ford
Road is or how wide its kerbs are.
"""

from __future__ import annotations

import json
import math
import os

import numpy as np

from core import terrain as TERR

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
TOWN = os.path.join(REPO, "content/town/hearthmere.json")


# ---------------------------------------------------------------------------
# Surfaces
# ---------------------------------------------------------------------------
#
# Edge treatments, which is the half of this the old code got wrong by keying
# kerbs off `surface == "cobble"`:
#
#   kerb       dressed kerbstones on a channel of setts. A made street.
#   kerb_deep  the same, taller face and a wider channel — Wharf Lane's kerbs
#              are 0.22 m and TOWN_PLAN says its gutters are "wide enough to
#              lose a boot in", because everything heavy in Hearthmere crosses
#              it and the run-off from the whole east side arrives there.
#   kerb_flush a kerb laid level with the paving: a forecourt, not a street.
#              Kirk Green is the church's apron and carts do not use it.
#   edging     a single course of stone set on edge holding a loose surface in.
#              What you do to a gravel lane so the gravel stays on it.
#   verge      no edge at all; the surface fades into trodden grass. The
#              Bailey, which was never made, only walked.
#   none       an unmade lane. The surface IS the ground, worn.

class Surface:
    """One authored surface description, resolved to build parameters."""

    __slots__ = ("key", "mat", "edge", "dress", "dress_amount", "crown",
                 "trough", "rough", "channel_mat", "note")

    def __init__(self, key, mat, edge, crown=0.06, trough=0.03, rough=0.010,
                 dress=None, dress_amount=0.0, channel_mat="sett", note=""):
        self.key = key
        self.mat = mat
        self.edge = edge
        self.crown = float(crown)
        self.trough = float(trough)
        self.rough = float(rough)
        self.dress = dress
        self.dress_amount = float(dress_amount)
        self.channel_mat = channel_mat
        self.note = note

    @property
    def kerbed(self):
        return self.edge in ("kerb", "kerb_deep", "kerb_flush")

    @property
    def made(self):
        """Paved, as opposed to a surface that is only compacted ground."""
        return self.mat in ("sett", "cobble", "flag", "stone")

    def __repr__(self):
        return f"<Surface {self.key!r} {self.mat} {self.edge}>"


# The complete authored vocabulary. Every string that appears in
# `hearthmere.json:streets[].surface` is here, and adding a street with a new
# description is a build error until its row is written.
SURFACES = {s.key: s for s in [
    Surface("granite setts", "sett", "kerb", crown=0.085, trough=0.075,
            rough=0.011,
            note="Ford Road and Wharf Lane. Dressed granite laid on edge to "
                 "take iron tyres; worn to a trough down the centre line."),
    Surface("cobble", "cobble", "kerb", crown=0.070, trough=0.050, rough=0.014,
            note="Water-worn field cobbles bedded in sand. The ordinary "
                 "made surface of a secondary street."),
    Surface("squared cobble", "sett", "kerb_flush", crown=0.030, trough=0.012,
            rough=0.007, dress="flag", dress_amount=0.18,
            note="Kirk Green. Squared and laid to a pattern with flag margins "
                 "— a church forecourt, so it is level and it is swept."),
    Surface("cobble, worn to dust", "cobble", "kerb", crown=0.055,
            trough=0.045, rough=0.013, dress="earth", dress_amount=0.42,
            note="Bakers' Row. Cobbled once; forty years of flour, ash and "
                 "cart wheels have silted the joints level."),
    Surface("gravel, stone edged", "gravel", "edging", crown=0.055,
            trough=0.040, rough=0.017, dress="earth", dress_amount=0.20,
            note="Mill Lane. Loose river shingle held in by a course of stone "
                 "on edge, rutted where the flour waggons turn."),
    Surface("gravel and grass", "gravel", "verge", crown=0.030, trough=0.030,
            rough=0.018, dress="grass_worn", dress_amount=0.46,
            note="The Bailey. Never made — two wheel tracks of shingle with "
                 "a green crown between them."),
    Surface("dirt and cinder", "cinder", "none", crown=0.035, trough=0.035,
            rough=0.016, dress="dirt", dress_amount=0.30,
            note="Smiths' Lane past the paving. Forge clinker rolled hard; "
                 "black, and it never turns to mud."),
    Surface("dirt", "earth", "none", crown=0.030, trough=0.035, rough=0.018,
            note="Tenter Lane. Trodden ground, nothing more."),
    Surface("beaten earth", "earth", "none", crown=0.025, trough=0.045,
            rough=0.022, dress="mud", dress_amount=0.26,
            note="The back lanes. Beaten hard down the middle and never dry "
                 "at the sides, because nothing drains off them."),
    Surface("dirt, tan-black", "mud", "none", crown=0.020, trough=0.050,
            rough=0.024, dress="mud_wet", dress_amount=0.34,
            note="Tan Road, outside the wall. Stained black by the tan "
                 "liquor that runs off the pits."),
    Surface("stone steps", "stone", "kerb_flush", crown=0.0, trough=0.0,
            rough=0.006,
            note="Fishers' Steps. A flight, not a carriageway — the ribbon is "
                 "only its landings; the treads are cut by the fall system."),
]}


def surface(name):
    """Resolve an authored surface description. Unknown is a build error."""
    s = SURFACES.get(name)
    if s is None:
        raise KeyError(
            f"unknown street surface {name!r}. The vocabulary is authored in "
            f"core/roadnet.SURFACES and is deliberately exhaustive — add a row "
            f"there (material, edge treatment, crown, trough) rather than "
            f"letting a street fall back to cobble, which is how twelve of "
            f"Hearthmere's fifteen streets came to be built in the wrong "
            f"material. Have: " + ", ".join(repr(k) for k in sorted(SURFACES)))
    return s


# Which street outranks which where two meet: the higher class carries its
# paving through the junction and the lower one runs up to it.
CLASS_RANK = {"primary": 4, "secondary": 3, "lane": 2, "alley": 1, "steps": 0}


# ---------------------------------------------------------------------------
# Street
# ---------------------------------------------------------------------------

class Street:
    """One authored centreline, parameterised by arc length in metres.

    Y is never read from the path. `hearthmere.json` has carried streets as
    `[x, z]` since D-024 and the ground is `core/terrain.py`; a stored level is
    a copy that can be — and was, by up to 1.24 m — wrong.
    """

    __slots__ = ("id", "name", "cls", "width", "verge", "surface", "note",
                 "bridged", "P", "seg", "cum", "length", "_ss", "_g", "_cf")

    def __init__(self, rec):
        self._ss = self._g = self._cf = None
        self.id = rec["id"]
        self.name = rec.get("name", rec["id"])
        self.cls = rec.get("cls", "secondary")
        self.width = float(rec.get("width", 5.0))
        self.verge = float(rec.get("verge", 0.8))
        self.surface = surface(rec.get("surface", "cobble"))
        self.note = rec.get("note", "")
        self.bridged = rec.get("bridged")
        self.P = np.array([[float(p[0]), float(p[-1])] for p in rec["path"]],
                          np.float64)
        d = self.P[1:] - self.P[:-1]
        self.seg = np.hypot(d[:, 0], d[:, 1])
        self.cum = np.concatenate([[0.0], np.cumsum(self.seg)])
        self.length = float(self.cum[-1])

    @property
    def rank(self):
        return CLASS_RANK.get(self.cls, 2)

    # -- parameterisation ---------------------------------------------------

    def _locate(self, s):
        s = min(max(float(s), 0.0), self.length)
        i = int(np.searchsorted(self.cum, s, side="right") - 1)
        i = min(max(i, 0), len(self.seg) - 1)
        t = (s - self.cum[i]) / max(self.seg[i], 1e-9)
        return i, t

    def at(self, s):
        i, t = self._locate(s)
        p = self.P[i] + (self.P[i + 1] - self.P[i]) * t
        return float(p[0]), float(p[1])

    def tangent(self, s):
        i, _t = self._locate(s)
        d = self.P[i + 1] - self.P[i]
        n = float(np.hypot(d[0], d[1])) or 1.0
        return float(d[0] / n), float(d[1] / n)

    def normal(self, s):
        """Unit left-hand normal in the ground plane (+1 side is `left`)."""
        tx, tz = self.tangent(s)
        return -tz, tx

    def offset(self, s, u):
        """World point `u` metres to the left of the centreline at `s`."""
        x, z = self.at(s)
        nx, nz = self.normal(s)
        return x + nx * u, z + nz * u

    def stations(self, step, margin=0.0):
        """Evenly spaced arc lengths, ends inset by `margin`."""
        lo, hi = margin, self.length - margin
        if hi <= lo:
            return []
        n = max(1, int(round((hi - lo) / step)))
        return [lo + (hi - lo) * (k + 0.5) / n for k in range(n)]

    # -- ground -------------------------------------------------------------
    #
    # Sampled ONCE per street at 1 m and then interpolated. `terrain.height` is
    # 1.66 ms for a scalar and 1.7 us per point in an array — three orders of
    # magnitude — because every call re-evaluates two splines, four octaves of
    # value noise, the water shapes and thirty-five pads through numpy on a
    # single float. The geometry passes ask this question tens of thousands of
    # times, so asking it scalar-wise turns a four-second build into an
    # eleven-minute one. Three vectorised calls per street instead.

    def _prepare(self):
        if self._g is not None:
            return
        n = max(2, int(round(self.length)) + 1)
        ss = np.linspace(0.0, self.length, n)
        P = np.array([self.at(float(s)) for s in ss], np.float64)
        N = np.array([self.normal(float(s)) for s in ss], np.float64)
        w = self.width * 0.5 + 0.6
        h = TERR.height(P[:, 0], P[:, 1])
        hl = TERR.height(P[:, 0] + N[:, 0] * w, P[:, 1] + N[:, 1] * w)
        hr = TERR.height(P[:, 0] - N[:, 0] * w, P[:, 1] - N[:, 1] * w)
        self._ss = ss
        self._g = np.asarray(h, np.float64)
        self._cf = np.where(np.abs(hl - hr) < 0.02, 0,
                            np.where(hl < hr, 1, -1)).astype(np.int8)

    @property
    def ground_profile(self):
        """(arc lengths, ground heights) sampled at ~1 m along the centreline."""
        self._prepare()
        return self._ss, self._g

    def ground(self, s):
        self._prepare()
        return float(np.interp(float(s), self._ss, self._g))

    def grade(self, s, h=1.25):
        """Signed gradient along the street at `s`: +ve climbs with +s."""
        a, b = max(0.0, s - h), min(self.length, s + h)
        if b - a < 1e-6:
            return 0.0
        return (self.ground(b) - self.ground(a)) / (b - a)

    def cross_fall(self, s):
        """Which side is downhill: -1 for the right, +1 for the left, 0 level.

        This is what decides which side a channel deepens on, where the gully
        stones go and which way a cross-drain is skewed. It is a fact about the
        ground, so it stays right if the terrace levels ever move.
        """
        self._prepare()
        i = int(np.clip(np.searchsorted(self._ss, float(s)), 0, len(self._cf) - 1))
        return int(self._cf[i])

    def is_bridged(self, s):
        """True where the street is carried on structure someone else builds.

        Ford Road crosses the Emberflow on the bridge venue's deck; laying a
        carriageway there would put a ribbon of setts through the water.
        """
        if not self.bridged:
            return False
        _x, z = self.at(s)
        return float(self.bridged[0]) <= z <= float(self.bridged[1])

    # -- queries ------------------------------------------------------------

    def project(self, x, z):
        """Nearest point: (arc length, signed offset, distance)."""
        p = np.array([float(x), float(z)])
        a = self.P[:-1]
        d = self.P[1:] - a
        ll = np.maximum((d * d).sum(axis=1), 1e-12)
        t = np.clip(((p - a) * d).sum(axis=1) / ll, 0.0, 1.0)
        q = a + d * t[:, None]
        dist = np.hypot(q[:, 0] - p[0], q[:, 1] - p[1])
        i = int(np.argmin(dist))
        s = float(self.cum[i] + t[i] * self.seg[i])
        n = self.normal(s)
        off = (p[0] - q[i][0]) * n[0] + (p[1] - q[i][1]) * n[1]
        return s, float(off), float(dist[i])

    def __repr__(self):
        return f"<Street {self.id} {self.cls} {self.width:g}m {self.length:.0f}m>"


def load(path=TOWN):
    """{street id: Street} from the town record, in authored order."""
    with open(path, encoding="utf-8") as f:
        recs = json.load(f).get("streets", [])
    if not recs:
        raise RuntimeError(
            f"no streets[] in {path} — the layout is authored there and "
            f"generated by tools/plan/townplan.py, never here")
    return {r["id"]: Street(r) for r in recs}


# ---------------------------------------------------------------------------
# Junctions
# ---------------------------------------------------------------------------

class Junction:
    """Where two or more streets have to resolve into one piece of paving."""

    __slots__ = ("x", "z", "radius", "members", "primary", "kind")

    def __init__(self, x, z, members, primary, kind, radius):
        self.x, self.z = float(x), float(z)
        self.members = members          # [(street_id, arc length, is_end)]
        self.primary = primary          # street id whose surface wins
        self.kind = kind                # "cross" | "tee" | "fork"
        self.radius = float(radius)

    def arc_of(self, sid):
        for mid, s, _end in self.members:
            if mid == sid:
                return s
        return None

    def __repr__(self):
        return (f"<Junction {self.kind} ({self.x:.1f},{self.z:.1f}) r={self.radius:.1f} "
                + "+".join(m[0] for m in self.members) + ">")


def _crossings(a, b, step=1.0):
    """Arc lengths on `a` where it comes close to `b`, one per contiguous run.

    Sampling rather than segment intersection because these streets rarely
    cross cleanly: TOWN_PLAN §4 calls J7 "a **staggered** crossroads, not a
    crossroads", and the Fork is two tees 2 m apart. What matters is where the
    two carriageways would overlap, which is a distance test.
    """
    reach = (a.width + b.width) * 0.5 + 0.9
    n = max(2, int(a.length / step))
    hits, run = [], []
    for k in range(n + 1):
        s = a.length * k / n
        x, z = a.at(s)
        sb, _off, dist = b.project(x, z)
        if dist <= reach:
            run.append((dist, s, sb))
        elif run:
            hits.append(min(run))
            run = []
    if run:
        hits.append(min(run))
    return hits


def junctions(net, merge=5.0):
    """Every place two streets meet, merged into one record per location."""
    ids = list(net)
    raw = []
    for i, ka in enumerate(ids):
        a = net[ka]
        for kb in ids[i + 1:]:
            b = net[kb]
            # Cheap reject: bounding boxes further apart than either is long.
            if (a.P[:, 0].min() > b.P[:, 0].max() + 12 or
                    a.P[:, 0].max() < b.P[:, 0].min() - 12 or
                    a.P[:, 1].min() > b.P[:, 1].max() + 12 or
                    a.P[:, 1].max() < b.P[:, 1].min() - 12):
                continue
            for _d, sa, sb in _crossings(a, b):
                x, z = a.at(sa)
                raw.append((x, z, [(ka, sa), (kb, sb)]))

    # Merge: the Fork is three streets and would otherwise be two junctions
    # 2 m apart, each with a kerb radius the other one cuts through.
    out = []
    for x, z, members in raw:
        for j in out:
            if math.hypot(j["x"] - x, j["z"] - z) <= merge:
                j["members"].update(dict(members))
                j["pts"].append((x, z))
                break
        else:
            out.append({"x": x, "z": z, "members": dict(members),
                        "pts": [(x, z)]})

    res = []
    for j in out:
        pts = np.asarray(j["pts"], float)
        cx, cz = float(pts[:, 0].mean()), float(pts[:, 1].mean())
        members = []
        for sid, _s in sorted(j["members"].items()):
            st = net[sid]
            s, _off, _d = st.project(cx, cz)
            members.append((sid, s, s < 3.0 or s > st.length - 3.0))
        primary = max(members, key=lambda m: (net[m[0]].rank, net[m[0]].width))[0]
        ends = sum(1 for m in members if m[2])
        kind = ("fork" if len(members) > 2 else
                ("tee" if ends else "cross"))
        radius = max(net[m[0]].width for m in members) * 0.5 + 1.4
        res.append(Junction(cx, cz, members, primary, kind, radius))
    res.sort(key=lambda j: (round(j.z, 2), round(j.x, 2)))
    return res


# ---------------------------------------------------------------------------
# Frontage
# ---------------------------------------------------------------------------

class Frontage:
    """One building's front wall, and the street it addresses.

    This is what turns a paved ribbon into a street. Real paving does not stop
    at a cut edge in the mud: it runs from the channel up over a kerb onto a
    footway, and the footway runs back to a threshold. All of that is derivable
    from the plot polygon and the centreline, which is why it is a system and
    not ninety hand-placed strips.
    """

    __slots__ = ("slot", "street", "side", "s0", "s1", "a", "b", "gap",
                 "doors", "kit", "role")

    def __init__(self, slot, street, side, s0, s1, a, b, gap, doors):
        self.slot = slot["id"]
        self.kit = slot.get("kit", "cottage")
        self.role = slot.get("role", "filler")
        self.street = street.id
        self.side = int(side)           # +1 left of the centreline, -1 right
        self.s0, self.s1 = float(min(s0, s1)), float(max(s0, s1))
        self.a, self.b = a, b           # the building line, world (x, z)
        self.gap = float(gap)           # kerb line to building line, metres
        self.doors = doors              # [(x, y, z)] world

    @property
    def length(self):
        return math.hypot(self.b[0] - self.a[0], self.b[1] - self.a[1])

    def __repr__(self):
        return (f"<Frontage {self.slot} -> {self.street} "
                f"side={self.side:+d} gap={self.gap:.2f}m {len(self.doors)} doors>")


# How far back from a kerb a building can stand and still be read as fronting
# the street. Beyond this it is a plot behind a plot, and paving out to it
# would pave the whole town.
FRONTAGE_REACH = 8.0


def frontages(net, slots, doors_of=None, footprint_of=None):
    """Match every building slot to the street its front wall addresses.

    `fronts` in the slot record is a hint, not the answer: nine slots front the
    market place, which is not a street, and a slot's real address is a
    geometric fact about where its front wall is. So the street is chosen by
    geometry and `fronts` only breaks ties.
    """
    out = []
    for slot in slots:
        fp = footprint_of(slot)
        rect = fp.rect()
        a, b = rect[0], rect[1]                     # the front edge, b = -d/2
        mid = ((a[0] + b[0]) * 0.5, (a[1] + b[1]) * 0.5)
        nx, nz = -fp.V[0], -fp.V[1]                 # outward from the front

        best = None
        for st in net.values():
            s, off, dist = st.project(*mid)
            clear = dist - st.width * 0.5
            if clear > FRONTAGE_REACH or clear < -0.5:
                continue
            # The street has to be IN FRONT of the wall, not behind it.
            sx, sz = st.at(s)
            if (sx - mid[0]) * nx + (sz - mid[1]) * nz < 0.35 * dist:
                continue
            score = clear - (2.5 if slot.get("fronts") == st.id else 0.0) \
                - 0.35 * st.rank
            if best is None or score < best[0]:
                best = (score, st, s, off, clear)
        if best is None:
            continue
        _score, st, s, off, clear = best
        sa = st.project(a[0], a[1])[0]
        sb = st.project(b[0], b[1])[0]
        dw = doors_of(slot) if doors_of else []
        out.append(Frontage(slot, st, 1 if off > 0 else -1, sa, sb,
                            (float(a[0]), float(a[1])),
                            (float(b[0]), float(b[1])), clear, dw))
    return out


# ---------------------------------------------------------------------------
# The fall
# ---------------------------------------------------------------------------

# Above this gradient a made surface needs help: cross-drains and a stepped
# sett bond on a cart road, a flight of steps on anything that is not one.
# 8% is where a shod horse starts to slip on wet granite and where a laden
# handcart stops being pushable, which is why TOWN_PLAN §3 keeps Ford Road
# under 6.4% by ramping it and sends the coffin route round by Kirkgate.
STEEP = 0.08


def steep_runs(street, threshold=STEEP, min_len=1.8):
    """Contiguous stretches steeper than `threshold`: [(s0, s1, drop)].

    Bridged stretches are excluded — Ford Road's 154% "gradient" is the
    Emberflow's north bank, which the bridge venue spans, not a hill.
    """
    ss, g = street.ground_profile
    if len(ss) < 3:
        return []
    d = np.abs(np.diff(g)) / np.maximum(np.diff(ss), 1e-6)
    runs, cur = [], None
    for k in range(len(d)):
        steep = d[k] > threshold and not street.is_bridged(float(ss[k]))
        if steep:
            cur = [float(ss[k]), float(ss[k + 1])] if cur is None else [cur[0], float(ss[k + 1])]
        elif cur is not None:
            runs.append(cur)
            cur = None
    if cur is not None:
        runs.append(cur)
    return [(s0, s1, street.ground(s1) - street.ground(s0))
            for s0, s1 in runs if s1 - s0 >= min_len]
