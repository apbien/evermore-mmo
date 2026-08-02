"""The town wall as an arc-length curve.

`content/town/hearthmere.json` authors the circuit as a 41-vertex closed
polyline with seven openings, eleven towers and five mural stairs hung off it.
Two venues consume it — `venues/wall.py` builds the ring, and
`venues/gatehouse.py` has to engage its own drum towers with the wall on either
side of the North Gate — and they must agree to the millimetre about where the
wall face is and which side of it is outside. A second copy of this arithmetic
in the gatehouse would put its jambs a few centimetres off the curtain, which
is exactly the kind of seam that only shows up in a screenshot.

So the polyline lives here, once, addressed by arc length from the North Gate.
Arc length is the only coordinate in which "the oldest stretch", "thirty metres
of rebuild", "a gap for the Water Gate" and "a lean-to against the inside" can
all be said without restating the geometry.
"""

from __future__ import annotations

import json
import math
import os

import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
TOWN_JSON = os.path.join(REPO, "content/town/hearthmere.json")

# --- The section, in metres. +u is OUTWARD; v is measured from the walk deck.
#
# Authored in the town record: walkHeight 6.0, parapet 1.2, thicknessBase 1.4
# battering to 1.1. The walk is 1.6 m wide and the wall is 1.1 m thick at the
# top, which reconciles exactly one way: the extra 0.9 m is corbelled off the
# inner face. That is real construction, it is what a town that will not pay
# for a thick wall actually builds, and the double shadow line it throws down
# the inner face is the best detail on the circuit seen from the Bailey.
FOUNDATION = 0.70        # how far the body is carried below ground
DECK_T = 0.12            # thickness of the walk slabs
WALK_W = 1.60            # authored width of the wall-walk
COURSE = 0.34            # one step in the crown; about 1.2 courses of rubble
WALK_H = 6.00            # authored height to the walk on an ORDINARY stretch
PARAPET_H = 1.20
THICK = (1.40, 1.10)     # (at the base, at the walk)


def load(path=TOWN_JSON):
    with open(path, encoding="utf-8") as f:
        return json.load(f)["wall"]


class Ring:
    """The authored polyline, resampled, with an outward normal everywhere."""

    def __init__(self, path):
        self.p = [(float(a[0]), float(a[1])) for a in path]
        n = len(self.p)
        self.cum = [0.0]
        for i in range(n):
            a, b = self.p[i], self.p[(i + 1) % n]
            self.cum.append(self.cum[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
        self.total = self.cum[-1]
        # Which side of the direction of travel is outside? `(-dz, dx)` is the
        # right of travel in plan; for a polygon wound the other way that is
        # the INSIDE, and a wall with its batter and its parapet facing the
        # market place is not a wall. Derived from the signed area rather than
        # assumed, so re-winding the authored path cannot silently invert every
        # section in the file.
        area = sum(self.p[i][0] * self.p[(i + 1) % n][1] -
                   self.p[(i + 1) % n][0] * self.p[i][1] for i in range(n))
        self.sgn = -1.0 if area > 0 else 1.0

    def s_of_vertex(self, i):
        return self.cum[i % len(self.p)]

    def s_of_point(self, x, z):
        """Arc length of the closest point on the ring to (x, z)."""
        best, bs = 1e18, 0.0
        n = len(self.p)
        for i in range(n):
            ax, az = self.p[i]
            bx, bz = self.p[(i + 1) % n]
            ex, ez = bx - ax, bz - az
            ee = ex * ex + ez * ez
            t = max(0.0, min(1.0, ((x - ax) * ex + (z - az) * ez) / ee))
            dx, dz = x - ax - ex * t, z - az - ez * t
            d = dx * dx + dz * dz
            if d < best:
                best, bs = d, self.cum[i] + t * math.sqrt(ee)
        return bs % self.total

    def at(self, s):
        """-> (x, z, tangent, outward) at arc length `s`."""
        s = s % self.total
        n = len(self.p)
        i = max(0, min(n - 1, int(np.searchsorted(self.cum, s, side="right") - 1)))
        ax, az = self.p[i]
        bx, bz = self.p[(i + 1) % n]
        seg = self.cum[i + 1] - self.cum[i]
        t = 0.0 if seg <= 0 else (s - self.cum[i]) / seg
        dx, dz = (bx - ax) / (seg or 1.0), (bz - az) / (seg or 1.0)
        return (ax + (bx - ax) * t, az + (bz - az) * t, (dx, dz),
                (-dz * self.sgn, dx * self.sgn))

    def frame(self, x, z):
        """The (position, tangent, outward) frame nearest a world point.

        What the gatehouse needs: it is handed a gate position in the town
        record and has to stand its drums square to the curtain, not square to
        the axes.
        """
        px, pz, tan, out = self.at(self.s_of_point(x, z))
        return (px, pz), tan, out

    def stations(self, step=2.0):
        """Arc lengths round the whole ring, with every authored vertex kept.

        The vertices matter: they are where the towers stand and where the
        circuit changes direction, and a resample that walked past them would
        round off exactly the corners the plan drew.
        """
        out = set(self.cum[:-1])
        s = 0.0
        while s < self.total:
            out.add(s)
            s += step
        return sorted(out)


def ring(path=TOWN_JSON):
    return Ring(load(path)["path"])


def yaw_facing(d):
    """The `rotate_y` angle that turns local -Z to point along `d = (dx, dz)`.

    `Mesh.rotate_y(r)` sends local -Z to `(-sin r, 0, -cos r)`, so this is
    `atan2(-dx, -dz)` and nothing else. It is a function because getting it
    wrong is silent and expensive: every gate in Hearthmere was authored with
    its ceremonial face on local -Z and then turned by `atan2(nout)`, which is
    the angle that puts local -Z INBOARD. The result was four gates with their
    arms, their lamps and their spur stones facing the market place, and an
    arch that looked symmetrical enough from outside that nothing caught it.
    """
    return math.atan2(-float(d[0]), -float(d[1]))
