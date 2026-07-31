"""Streets — the layer that turns a set of buildings into a settlement.

`content/town/hearthmere.json` has authored all three streets since the town
was laid out — paths, widths, surfaces, and wear notes — and until now nothing
in the pipeline read `streets[]`. The result was seven buildings standing on an
undifferentiated grey plane, with no Ford Road, and an arrival frame in which
the player had no indication of where to walk.

This module is that missing consumer. It reads the authored paths and builds:
  - a paved carriageway along each path, with the centre worn into a shallow
    trough by cart traffic (called out in the Ford Road notes)
  - kerbs where a paved street meets open ground
  - verge scatter — the grit and moss that collects at the edge of any road

Nothing here invents layout. If a street needs to move, it moves in the town
JSON and this module follows.
"""

from __future__ import annotations

import json
import os
import numpy as np

from core import mesh as M
from core import kit as K
from core.mathx import rng_for
from core.venue import VenueContext, REPO

NAME = "streets"
CELLS = ["C1", "C2", "C3", "C4", "C5", "C6", "B3", "D3", "E3"]

TOWN = os.path.join(REPO, "content/town/hearthmere.json")

SURFACE_MAT = {"cobble": "cobble", "dirt": "dirt", "stone": "stone"}


def _load_streets():
    with open(TOWN) as f:
        return json.load(f).get("streets", [])


def _ribbon(path, width, mat, asset_id, trough=0.0, uv=0.5):
    """Lay a quad ribbon along a polyline path.

    Each segment is subdivided across its width so the carriageway can dish
    toward the centre — that shallow trough is what makes a road read as used
    rather than as a painted stripe, and it catches a highlight along its
    length at grazing angles.
    """
    rng = rng_for(asset_id, "ribbon")
    out = M.Group()
    LANES = 6

    pts = [np.asarray(p, np.float32) for p in path]
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        d = b - a
        ln = float(np.linalg.norm(d))
        if ln < 1e-4:
            continue
        d = d / ln
        # Perpendicular in the ground plane.
        n = np.array([-d[2], 0.0, d[0]], np.float32)

        # Subdivide along the length too, so long streets are not one quad.
        steps = max(1, int(ln / 4.0))
        for s in range(steps):
            t0, t1 = s / steps, (s + 1) / steps
            p0 = a + d * (ln * t0)
            p1 = a + d * (ln * t1)
            for k in range(LANES):
                u0 = -0.5 + k / LANES
                u1 = -0.5 + (k + 1) / LANES
                # Dish: deepest at the centreline, flat at the kerbs — but the
                # WHOLE carriageway sits proud of the surrounding earth, which
                # is both correct (a made road is built up) and necessary: the
                # trough previously dished to -0.075 while the ground plane sits
                # at -0.01, so the centre of Ford Road was buried underneath the
                # ground and the road read as bare earth between two kerbs.
                ROAD_LIFT = 0.10
                y0 = ROAD_LIFT - trough * (1.0 - abs(u0 * 2.0) ** 1.6)
                y1 = ROAD_LIFT - trough * (1.0 - abs(u1 * 2.0) ** 1.6)
                j = rng.uniform(-0.008, 0.008)

                c0 = p0 + n * (u0 * width); c0[1] = y0 + j
                c1 = p0 + n * (u1 * width); c1[1] = y1 + j
                c2 = p1 + n * (u1 * width); c2[1] = y1 + j
                c3 = p1 + n * (u0 * width); c3[1] = y0 + j

                bld = M._Builder()
                # Wound for a +Y geometric normal — VERIFIED, not asserted.
                # The previous order carried this same comment and produced the
                # opposite: 288/288 carriageway triangles wound against their
                # stored [0,1,0] normal, and with doubleSided:false the whole
                # road was back-face culled and never drawn. What showed between
                # the kerbs was bare ground, darkened by the invisible slab's
                # own cast shadow. Identical bug to the market square plaza,
                # reintroduced here.
                quad = [c0, c1, c2, c3]
                uvs = [(p[0] * uv, p[2] * uv) for p in quad]
                bld.poly(quad, uvs, np.array([0, 1, 0], np.float32))
                out.add(bld.build(mat))
    return out


def _kerb(path, width, asset_id):
    """Kerbstones down both edges — the line that separates road from ground."""
    rng = rng_for(asset_id, "kerb")
    out = M.Group()
    pts = [np.asarray(p, np.float32) for p in path]
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        d = b - a
        ln = float(np.linalg.norm(d))
        if ln < 1e-4:
            continue
        d = d / ln
        n = np.array([-d[2], 0.0, d[0]], np.float32)
        count = max(1, int(ln / 0.75))
        for s in range(count):
            t = (s + 0.5) / count
            for side in (-1, 1):
                c = a + d * (ln * t) + n * (side * width * 0.5)
                k = M.box(0.70, 0.16, 0.22, 0.02, "stone", uv_scale=1.0)
                k.rotate_y(float(np.arctan2(d[0], d[2])) + rng.uniform(-0.02, 0.02))
                k.translate(c[0], 0.145 + rng.uniform(-0.012, 0.006), c[2])
                out.add(k)
    return out


def build(ctx: VenueContext, asset_id="hm.streets"):
    rng = rng_for(asset_id, "streets")
    streets = _load_streets()
    if not streets:
        raise RuntimeError("no streets[] in hearthmere.json — layout is authored there")

    for st in streets:
        sid = f"{asset_id}.{st['id']}"
        mat = SURFACE_MAT.get(st.get("surface", "cobble"), "cobble")
        width = float(st.get("width", 5.0))
        path = st["path"]

        # Ford Road is explicitly noted as worn to a trough down its centre;
        # the smaller lanes get progressively less.
        trough = {"ford_road": 0.075, "mere_street": 0.05}.get(st["id"], 0.02)

        ctx.emit(_ribbon(path, width, mat, sid, trough=trough))
        if st.get("surface") == "cobble":
            ctx.emit(_kerb(path, width, sid))

        # Verge scatter: grit, moss clumps and the odd loose stone gathering
        # against the kerb. Cheap, and it stops the road/ground join being a
        # perfectly straight seam.
        pts = [np.asarray(p, np.float32) for p in path]
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            d = b - a
            ln = float(np.linalg.norm(d))
            if ln < 1e-4:
                continue
            d = d / ln
            n = np.array([-d[2], 0.0, d[0]], np.float32)
            for _ in range(int(ln * 1.4)):
                t = rng.uniform(0, 1)
                side = 1 if rng.random() < 0.5 else -1
                off = width * 0.5 + rng.uniform(0.05, 0.85)
                c = a + d * (ln * t) + n * (side * off)
                if rng.random() < 0.55:
                    s_ = rng.uniform(0.08, 0.17)
                    g = M.box(s_, s_ * 0.45, s_ * rng.uniform(0.8, 1.2), s_ * 0.2, "cobble")
                    g.rotate_y(rng.uniform(0, 3.14))
                    g.translate(c[0], s_ * 0.15, c[2])
                else:
                    g = M.lathe([(0.0, 0), (rng.uniform(0.09, 0.16), 0.02),
                                 (0.0, 0.05)], 7, "foliage")
                    g.translate(c[0], 0.01, c[2])
                ctx.emit(g)

    # Ford Road terminates at the south road out of town — Art Bible §7 says
    # every street must end in something worth walking toward. A pair of
    # waymarker stones does that job without inventing a whole venue.
    for side in (-1, 1):
        wm = M.Group()
        stone = M.lathe([(0.34, 0), (0.30, 0.55), (0.22, 1.05), (0.0, 1.20)], 9, "stone")
        wm.add(stone)
        cap = M.lathe([(0.24, 1.05), (0.26, 1.12), (0.0, 1.26)], 9, "stone")
        wm.add(cap)
        wm.rotate_y(rng.uniform(-0.2, 0.2))
        wm.translate(side * 4.6, 0, 44.0)
        ctx.emit(wm)
        ctx.entity(f"{asset_id}.waymarker.{'w' if side < 0 else 'e'}",
                   "prop.waymarker", (side * 4.6, 0, 44.0), cell="C6",
                   verbs=["inspect"])

    ctx.emit(_gate(ctx, asset_id))


def _gate(ctx, asset_id, z=-46.0):
    """The north gate — the player's arrival frame needs a foreground.

    `hm.gate.north` has been a declared landmark with a comment describing the
    framing it should provide, and no geometry, since the town was laid out.
    Without it the arrival shot opens on empty ground and the eye has nothing
    to enter through.

    Deliberately modest: World Bible says Hearthmere's wall is more customs
    boundary than defence and has never been besieged, so this is a decorative
    arch on a prosperous trading town, not a fortification.
    """
    rng = rng_for(asset_id, "gate")
    out = M.Group()
    ROAD_W = 7.0
    PIER = 1.5
    H = 5.2

    for side in (-1, 1):
        px = side * (ROAD_W * 0.5 + PIER * 0.5)
        # Pier, battered slightly (wider at the base) so it reads as masonry.
        for i, (w, y, h) in enumerate([(PIER * 1.15, 0.0, 0.55),
                                       (PIER, 0.55, H - 1.1),
                                       (PIER * 1.12, H - 0.55, 0.55)]):
            b = M.box(w, h, w, 0.025, "ashlar", uv_scale=0.55)
            b.translate(px, y + h * 0.5, z)
            out.add(b)
        # Quoined corners.
        for cx in (-1, 1):
            for cz in (-1, 1):
                for k in range(int((H - 1.1) / 0.42)):
                    long_side = k % 2 == 0
                    q = M.box(0.34 * (1.4 if long_side else 0.9), 0.40,
                              0.34 * (0.9 if long_side else 1.4), 0.016,
                              "ashlar", uv_scale=0.7)
                    q.translate(px + cx * PIER * 0.5, 0.55 + 0.42 * (k + 0.5),
                                z + cz * PIER * 0.5)
                    out.add(q)

    # Arch over the road, built as voussoirs so it reads as cut stone.
    R = ROAD_W * 0.5 + PIER * 0.35
    N = 13
    for i in range(N):
        a = np.pi * (i + 0.5) / N
        v = M.box(0.62, 0.90, PIER * 0.95, 0.02, "ashlar", uv_scale=0.6)
        v.rotate_z(a - np.pi * 0.5)
        v.translate(np.cos(a) * R, H - 1.0 + np.sin(a) * R * 0.42, z)
        out.add(v)

    # Keystone with the town's heron, and a lamp on each pier.
    key = M.prism([(-0.30, 0), (0.30, 0), (0.24, 0.62), (-0.24, 0.62)], 0.42,
                  chamfer=0.014)
    key.translate(0, H - 0.85 + R * 0.42, z - 0.05)
    out.add(key.with_material("ashlar"))
    heron = M.lathe([(0.0, 0), (0.08, 0.05), (0.09, 0.17), (0.0, 0.27)], 10, "ashlar")
    heron.translate(0, H - 0.60 + R * 0.42, z - 0.28)
    out.add(heron)

    for side in (-1, 1):
        lam = K.lantern(f"{asset_id}.gatelamp{side}", scale=1.35)
        lam.translate(side * (ROAD_W * 0.5 + 0.25), H - 1.9, z - 0.22)
        out.add(lam)
        ctx.entity(f"{asset_id}.gatelamp.{'w' if side < 0 else 'e'}",
                   "prop.lantern", (side * (ROAD_W * 0.5 + 0.25), H - 1.9, z),
                   cell="C1", light={"color": "#FFB35C", "intensity": 1.6, "range": 7.0})

    # Low wall running off each pier — the customs boundary, waist height.
    for side in (-1, 1):
        for i in range(7):
            seg = M.box(1.9, 1.15 + rng.uniform(-0.06, 0.06), 0.55, 0.025,
                        "stone", uv_scale=0.6)
            seg.rotate_y(rng.uniform(-0.02, 0.02))
            seg.translate(side * (ROAD_W * 0.5 + PIER + 1.0 + i * 1.95),
                          0.575, z + rng.uniform(-0.05, 0.05))
            out.add(seg)

    ctx.entity(f"{asset_id}.gate.north", "landmark.gate", (0, 0, z), cell="C1",
               verbs=["inspect"])
    return out
