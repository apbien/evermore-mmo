"""The North Gate and the Emberflow bridge — the departure and return frame.

BUILD_DIRECTIVE §3.3: the arrival is now the church altar, and the north gate
and its bridge are the *departure/return* frame instead. That is the composition
this module exists to build. Standing on the causeway and looking south you get,
in one shot: the bridge rising over the water, the silted ford dying in the
shallows beside it, the twin drums of the gate, and the town stepping up the
slope behind. Standing under the arch and looking north you get the water, the
meadow, and the road away.

Everything here is authored in WORLD coordinates and moved into the venue's
local frame once, at the end of `build`. The venue origin
(`content/town/hearthmere.json` -> venues -> gatehouse) is the gate threshold,
so authoring locally would mean carrying a +2.4/-76 offset through every
cutwater and every voussoir — and the bridge has to line up with a river the
terrain owns, not with the gate.

The river is not ours
---------------------
`content/town/terrain.json` carves the Emberflow, and D-024 moved it to cross
Ford Road at z = -90 precisely so the bridge would land inside the 192 m grid
and inside this frame. So the span is SOLVED from the height field at build
time — the waterline is found by walking the road line until the ground drops
below `terrain.water_level()` — rather than typed here. If the water moves
again, the bridge follows it in the next build instead of standing in a field.
"""

from __future__ import annotations

import math

import numpy as np

from core import circuit as CIRC
from core import collision as COL
from core import kit as K
from core import mesh as M
from core import terrain as TERR
from core.mathx import rng_for
from core.venue import VenueContext
from core import materials as MATS

NAME = "gatehouse"
CELLS = ["F2"]

# Venue origin from the town record: the gate threshold. Authored here so the
# world->local move is one line and one place.
ORIGIN = (-2.4, -1.85, -76.0)

# The road surface sits this far proud of the ground it is laid on — the same
# number `venues/streets.py` and `core/kit.py` use, so the carriageway is
# continuous across the abutment instead of stepping 0.22 m at the joint.
ROAD_LIFT = K.MADE_LIFT

BRIDGE_X = -3.9          # Ford Road's centreline where it crosses the water
DECK_CLEAR = 5.60        # between parapets, per LANDMARKS['hm.bridge']
PARAPET_T = 0.45
DECK_T = 0.42            # the deck slab the setts are laid on
CROWN_Y = -0.90          # authored: 2.2 m of headroom over a -3.10 surface

# "The parapet is 0.3 m lower on the east because it was knocked out by a barge
# and rebuilt cheaply." West is upstream, so east is the side a boat coming
# down on the current hits. One number each, named, because the coping, the
# collision and the coursing all have to agree about them.
PARA_W_H = 0.95
PARA_E_H = 0.65
# How far the swept core stands back from the dressed face on each side. The
# dressed stones are laid over it, so this is also the depth of every joint.
# 42 mm: enough that the raking 09:30 key finds every bed joint at 3 m, little
# enough that the face reads as DRESSED stone and not as dry-laid blocks.
CORE_INSET = 0.042


# ---------------------------------------------------------------------------
# Solving the crossing from the height field
# ---------------------------------------------------------------------------

def _crossing():
    """Where the Emberflow actually is on Ford Road, in metres.

    Returns `(south_bank_z, north_bank_z)`: the two z at which the ground
    crosses the water surface on the bridge's centreline. Walked at 0.05 m
    because a bridge that misses its own abutment by a quarter of a metre has
    one springing in the river.
    """
    w = TERR.water_level()
    zs = np.arange(-70.0, -105.0, -0.05)
    h = np.array([float(TERR.height(BRIDGE_X, z)) for z in zs])
    wet = h < w
    if not wet.any():
        raise RuntimeError(
            "no water on Ford Road between z=-70 and z=-105: the Emberflow has "
            "moved out of the north gate's frame. Check content/town/terrain.json "
            "water.channels['hm.water.emberflow'].")
    idx = np.flatnonzero(wet)
    return float(zs[idx[0]]), float(zs[idx[-1]])


def _bridged_span():
    """Ford Road's declaration of the stretch it leaves to a structure."""
    import json
    with open(CIRC.TOWN_JSON, encoding="utf-8") as f:
        for st in json.load(f).get("streets", []):
            if st["id"] == "ford_road" and st.get("bridged"):
                return [float(v) for v in st["bridged"]]
    return None


def _arches(z_s, z_n):
    """Three segmental arches and two piers between the abutment faces.

    The landmark record fixes the count — "three segmental arches, cutwaters
    upstream with triangular refuges over them" — and the channel fixes the
    clear width. The centre arch takes the deep water and the two flankers sit
    on the shelving banks, which is both how the load works and why the bridge
    reads as three things rather than one tube.
    """
    a = z_s - 0.55                # abutment faces, just inside dry ground
    b = z_n + 0.55
    total = abs(b - a)
    pier = 1.15
    span_c = (total - 2 * pier) * 0.42
    span_e = (total - 2 * pier - span_c) * 0.5
    out, z = [], a
    for s in (span_e, span_c, span_e):
        out.append(dict(centre=z - s * 0.5, span=s))
        z -= s + pier
    piers = [(out[0]["centre"] - out[0]["span"] * 0.5 - pier * 0.5),
             (out[1]["centre"] - out[1]["span"] * 0.5 - pier * 0.5)]
    return a, b, out, piers, pier


def _seg(span, rise):
    """(circle centre offset, radius) for a segmental arch of this span/rise."""
    h = span * 0.5
    cy = (rise * rise - h * h) / (2.0 * rise)
    return cy, rise - cy


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build(ctx: VenueContext, asset_id="hm.gatehouse"):
    rng = rng_for(asset_id, "gatehouse")
    ring = CIRC.ring()
    doc = CIRC.load()
    gate = next(g for g in doc["gates"] if g["id"].endswith(".north"))

    world = M.Group()
    colliders, entities = [], []

    def collide(vol):
        colliders.append(vol)

    z_s, z_n = _crossing()
    deck = _deck_profile(z_s, z_n, _bridged_span())
    _bridge(world, collide, entities, asset_id, z_s, z_n, deck, rng)
    _old_ford(world, asset_id, z_s, rng)
    _north_gate(world, collide, entities, asset_id, ring, gate, rng)

    world.translate(-ORIGIN[0], -ORIGIN[1], -ORIGIN[2])
    ctx.emit(world)
    for v in colliders:
        ctx.collider(v)
    for eid, arch, pos, kw in entities:
        ctx.entity(eid, arch, (pos[0] - ORIGIN[0], pos[1] - ORIGIN[1],
                               pos[2] - ORIGIN[2]), **kw)


# ---------------------------------------------------------------------------
# The bridge
# ---------------------------------------------------------------------------

def _deck_profile(z_s, z_n, bridged=None):
    """`(top_y(z), z0, z1, crown_z)` for the road over the bridge.

    A humpback: the deck has to clear the water by 2.2 m at the crown and land
    on the gate flat at one end and the causeway at the other, both of which
    the terrain owns. Eased rather than straight so the crown is a curve and
    not a ridge — this profile IS the bridge's silhouette from the meadow, and
    it is the reason the departure frame has a foreground at all.

    `bridged` is Ford Road's own declaration in `content/town/hearthmere.json`
    of the stretch it does NOT lay a carriageway on, because something else
    carries it there. That something else is this deck, so the deck is built to
    overlap that span by 0.6 m at each end rather than to a length of its own
    choosing. Both sides reading the same authored number is what stops a
    quarter-metre of nothing appearing at the abutment.
    """
    z0 = z_s + 3.4                                     # out onto the gate flat
    z1 = z_n - 6.0                                     # out along the causeway
    if bridged:
        z0 = max(z0, float(max(bridged)) + 0.60)
        z1 = min(z1, float(min(bridged)) - 0.60)
    y0 = float(TERR.height(BRIDGE_X, z0)) + ROAD_LIFT
    y1 = float(TERR.height(BRIDGE_X, z1)) + ROAD_LIFT
    crown = (z_s + z_n) * 0.5

    def top(z):
        z = float(np.clip(z, min(z0, z1), max(z0, z1)))
        if z >= crown:                                  # south limb
            t = (z0 - z) / (z0 - crown)
            return y0 + (CROWN_Y - y0) * (2.0 * t - t * t)
        t = (z1 - z) / (z1 - crown)
        return y1 + (CROWN_Y - y1) * (2.0 * t - t * t)

    return dict(top=top, z0=z0, z1=z1, crown=crown)


def _bridge(out, collide, entities, asset_id, z_s, z_n, deck, rng):
    a, b, arches, piers, pier_t = _arches(z_s, z_n)
    top = deck["top"]
    spring = TERR.water_level() + 0.05
    RING = 0.44
    half = DECK_CLEAR * 0.5 + PARAPET_T          # 3.25 m to the parapet face
    bed = min(float(TERR.height(BRIDGE_X, ar["centre"])) for ar in arches) - 0.45

    def rise_for(ar):
        # Every arch springs off the same course and its crown stops just under
        # the deck soffit at its own station. That is what makes three arches
        # of different spans sit on one bridge without looking sampled.
        return max(0.75, top(ar["centre"]) - DECK_T - RING - 0.06 - spring)

    for i, ar in enumerate(arches):
        r = rise_for(ar)
        ring = K.arch_ring(f"{asset_id}.arch.{i}", ar["span"], rise=r,
                           ring=RING, depth=half * 2.0, mat="ashlar",
                           chamfer=0.026)
        ring.rotate_y(math.pi * 0.5)
        ring.translate(BRIDGE_X, spring, ar["centre"])
        out.add(ring)
        ar["rise"] = r

    def soffit_top(z):
        """Underside of the bridge's solid masonry at z: extrados, or ground."""
        for ar in arches:
            d = z - ar["centre"]
            if abs(d) <= ar["span"] * 0.5:
                cy, R = _seg(ar["span"], ar["rise"])
                return spring + cy + math.sqrt(max(0.0, R * R - d * d)) + RING
        g = float(TERR.height(BRIDGE_X, z))
        return min(g - 0.45, bed) if g < TERR.water_level() else g - 0.45

    # Spandrel and abutment masonry, swept as one solid whose bottom follows
    # the arches and whose top follows the road. Narrower than the arch rings so
    # the rings stand proud and throw the shadow line that separates them.
    zs = list(np.arange(deck["z0"], deck["z1"] - 0.001, -0.30)) + [deck["z1"]]
    path, prof, sett, para_w, para_e, cope_w, cope_e = [], [], [], [], [], [], []
    for z in zs:
        yt = top(z)
        yb = min(soffit_top(z), yt - DECK_T - 0.02)
        path.append((BRIDGE_X, 0.0, z))
        prof.append([(-half + 0.10, yb), (half - 0.10, yb),
                     (half - 0.10, yt - DECK_T), (-half + 0.10, yt - DECK_T)])
        # The deck slab itself, full width, and the setts on top of it.
        sett.append([(-half + 0.02, yt - DECK_T), (half - 0.02, yt - DECK_T),
                     (half - 0.02, yt), (-half + 0.02, yt)])
        # The parapet CORE, set back `CORE_INSET` from both faces. The faces
        # themselves are laid stone by stone in `_parapet_courses` — see the
        # note there — so what this sweep contributes is the dark behind every
        # joint, and it is never seen except through one.
        for lst, sgn, h in ((para_w, -1.0, PARA_W_H), (para_e, 1.0, PARA_E_H)):
            lst.append([(sgn * (half - PARAPET_T + CORE_INSET), yt),
                        (sgn * (half - CORE_INSET), yt),
                        (sgn * (half - CORE_INSET), yt + h),
                        (sgn * (half - PARAPET_T + CORE_INSET), yt + h)])
        for lst, sgn, h in ((cope_w, -1.0, PARA_W_H), (cope_e, 1.0, PARA_E_H)):
            lst.append([(sgn * (half - PARAPET_T - 0.07), yt + h),
                        (sgn * (half + 0.07), yt + h),
                        (sgn * (half + 0.07), yt + h + 0.09),
                        (sgn * (half - PARAPET_T * 0.5), yt + h + 0.17),
                        (sgn * (half - PARAPET_T - 0.07), yt + h + 0.09)])
    out.add(M.sweep(prof, path, mat="rubble"))
    out.add(M.sweep(sett, path, mat="sett"))
    out.add(M.sweep(para_w, path, mat="rubble"))
    out.add(M.sweep(para_e, path, mat="rubble"))
    _parapet_courses(out, deck, top, -1.0, PARA_W_H, half, "west", asset_id)
    _parapet_courses(out, deck, top, +1.0, PARA_E_H, half, "east", asset_id)
    out.add(M.sweep(cope_w, path, mat="stone"))
    out.add(M.sweep(cope_e, path, mat="stone"))

    # Cutwaters upstream, and the triangular refuge each one carries.
    for i, pz in enumerate(piers):
        proj = 1.45
        for k in range(9):
            t = k / 9.0
            y0 = bed + (top(pz) - 0.9 - bed) * t
            y1 = bed + (top(pz) - 0.9 - bed) * (k + 1) / 9.0
            w = proj * (1.0 - 0.06 * t)
            cw = M.prism([(0.0, -pier_t * 0.62), (0.0, pier_t * 0.62), (-w, 0.0)],
                         y1 - y0, chamfer=0.0)
            cw.rotate_x(-math.pi * 0.5)
            cw.translate(BRIDGE_X - half + 0.12, y0 + (y1 - y0) * 0.5, pz)
            out.add(cw.with_material("ashlar"))
        # The cap: the cutwater dies back into the spandrel under the refuge.
        cap = M.prism([(0.0, -pier_t * 0.62), (0.0, pier_t * 0.62), (-proj, 0.0)],
                      0.9, chamfer=0.0)
        cap.rotate_x(-math.pi * 0.5)
        cap.v[:, 1] += np.clip(-(cap.v[:, 0] - (BRIDGE_X - half + 0.12)), 0, 9) * 0.55
        cap.translate(BRIDGE_X - half + 0.12, top(pz) - 0.9, pz)
        out.add(cap.with_material("stone"))
        # Refuge: a bay in the parapet a carter steps into when a cart comes
        # the other way. It is the single most legible "this is a real bridge"
        # detail there is, and it costs eight boxes.
        ry = top(pz)
        for sx, sz in ((0, -1), (0, 1)):
            side = M.box(1.30, 0.95, PARAPET_T, 0.02, "ashlar")
            side.rotate_y(math.pi * 0.5)
            side.translate(BRIDGE_X - half - 0.42, ry + 0.475,
                           pz + sz * (0.62 + PARAPET_T * 0.5))
            out.add(side)
        front = M.box(PARAPET_T, 0.95, 1.24 + PARAPET_T * 2, 0.02, "ashlar")
        front.translate(BRIDGE_X - half - 1.07 + PARAPET_T * 0.5, ry + 0.475, pz)
        out.add(front)
        floor = M.box(1.10, 0.14, 1.24, 0.02, "stone")
        floor.translate(BRIDGE_X - half - 0.55, ry + 0.07, pz)
        out.add(floor)
        cope = M.box(1.62, 0.13, 1.5, 0.02, "stone")
        cope.translate(BRIDGE_X - half - 0.62, ry + 1.02, pz)
        out.add(cope)
        # A refuge is where people stop, so it is where residue goes.
        if i == 0:
            for k in range(3):
                pot = M.lathe([(0.0, 0), (0.09, 0.03), (0.11, 0.16), (0.09, 0.19)],
                              9, "pottery", close_top=False)
                pot.translate(BRIDGE_X - half - 0.55 + rng.uniform(-0.3, 0.3),
                              ry + 0.14, pz + rng.uniform(-0.4, 0.4))
                out.add(pot)
        entities.append((f"{asset_id}.refuge.{i + 1:02d}", "prop.bench",
                         (BRIDGE_X - half - 0.55, ry + 0.14, pz),
                         dict(verbs=["sit"], cell="F1")))

    # Collision. The deck is a SURFACE — a bridge the player cannot walk over
    # is worse than no bridge — and only the parapets are solid.
    n = max(2, int(abs(deck["z1"] - deck["z0"]) / 1.5))
    for k in range(n):
        za = deck["z0"] + (deck["z1"] - deck["z0"]) * k / n
        zb = deck["z0"] + (deck["z1"] - deck["z0"]) * (k + 1) / n
        y = max(top(za), top(zb))
        collide(COL.segment_box((BRIDGE_X, 0, za), (BRIDGE_X, 0, zb),
                                DECK_CLEAR, y - 1.2, y,
                                kind="surface", tag="bridge_deck", extend=0.4))
        for sgn, h in ((-1.0, PARA_W_H), (1.0, PARA_E_H)):
            collide(COL.segment_box(
                (BRIDGE_X + sgn * (half - PARAPET_T * 0.5), 0, za),
                (BRIDGE_X + sgn * (half - PARAPET_T * 0.5), 0, zb),
                PARAPET_T, min(top(za), top(zb)), y + h,
                kind="solid", tag="bridge_parapet", extend=0.4))
    entities.append((f"{asset_id}.bridge", "landmark.bridge",
                     (BRIDGE_X, CROWN_Y, deck["crown"]),
                     dict(verbs=["inspect"], cell="F1")))


def _parapet_courses(out, deck, top, sgn, h, half, side, asset_id):
    """Dressed stone laid block by block along one side of the deck.

    `ad-town-06` §1, the loudest single defect in the build: swept as ONE solid
    in `cobble_wall`, this face was "a machine-regular grid of oval portholes …
    it reads as pressed steel or a concrete screen block", filling the right
    45 % of the departure frame. The UVs were not the problem — `M.sweep` runs
    both axes through `resolve_uv`, so the module was already metric at the
    library's 2 m coverage, and I measured it in the frame at ~0.2 m a cobble.
    The problem is that a swept ring can only ever carry a PICTURE of masonry,
    and at 3 m in a mandated hero camera the eye reads relief. A parapet with
    no relief is a panel, and a tiled panel is a manufactured one.

    So the courses are real. Every stone is its own solid on a level bed joint,
    half-lapped against the course below, and set a few millimetres proud or
    shy of its neighbours so the raking 09:30 light finds the arrises. Behind
    them the swept core stands `CORE_INSET` back, which is what makes each
    joint a dark line rather than a painted one.

    The bridge is straight in plan — `path` is x = BRIDGE_X with z varying — so
    a stone is an axis-aligned box and none of this costs a transform.

    West is the original bridge and is ashlar: long stones, deep courses. East
    is the barge-struck rebuild and is the same stone worked cheaper: short
    stones, shallow courses, twice the setting-out slop. That is the difference
    the two sides are supposed to read as, and it is a difference of CRAFT
    inside one masonry family rather than a seventh recipe (§(c)(i)).
    """
    rng = rng_for(asset_id, "parapet", side)
    z0, z1 = deck["z0"], deck["z1"]
    west = sgn < 0.0
    blen = 0.86 if west else 0.58
    n_c = max(3, int(round(h / (0.245 if west else 0.215))))
    ch = h / n_c
    xf = BRIDGE_X + sgn * (half - PARAPET_T * 0.5)
    bw = PARAPET_T - 0.02
    slop = 0.004 if west else 0.008
    joint = 0.014 if west else 0.018      # the rebuild was pointed less finely
    step = 1.0 if z1 > z0 else -1.0
    for c in range(n_c):
        # Half-lap the perpends. A vertical joint that lines up through four
        # courses is the same tell as the portholes, one order of size up.
        z = z0 + step * (c % 2) * 0.5 * blen
        while (z1 - z) * step > 0.14:
            L = min(blen * (1.0 + rng.uniform(-0.18, 0.18)), abs(z1 - z))
            zc = z + step * L * 0.5
            b = M.box(bw, ch - joint, L - joint, 0.009, "ashlar")
            b.translate(xf + sgn * rng.uniform(-0.004, slop),
                        top(zc) + c * ch + ch * 0.5, zc)
            out.add(b)
            z += step * L


# ---------------------------------------------------------------------------
# The old ford
# ---------------------------------------------------------------------------

def _old_ford(out, asset_id, z_s, rng):
    """The crossing that named the road, dying in the water beside the bridge.

    TOWN_PLAN J1: "The old ford's stone approach ramp branches east and dies in
    the water: broken kerb, cart ruts full of weed." The ford channel is
    authored in `content/town/terrain.json` (`hm.water.ford`), so its line is
    read rather than typed — the terrain agent is re-cutting this water and the
    ramp has to keep pointing at it.

    Where the ramp stops is SOLVED: it is laid eastward from Bridgefoot until
    the ground goes under the water surface, and then two more metres of it are
    laid under water because that is what a drowned ramp looks like. If the
    Mere's shore moves, the ramp lengthens or shortens with it.
    """
    import json
    import os
    with open(os.path.join(CIRC.REPO, "content/town/terrain.json"),
              encoding="utf-8") as f:
        chans = json.load(f)["water"]["channels"]
    ford = next((c for c in chans if c["id"].endswith(".ford")), None)
    if ford is None:
        return
    aim = ford["path"][0]
    w = TERR.water_level()

    ax, az = -3.4, z_s + 1.6
    dx, dz = float(aim[0]) - ax, float(aim[1]) - az
    ln = math.hypot(dx, dz) or 1.0
    dx, dz = dx / ln, dz / ln
    nx, nz = -dz, dx

    # Walk out until the ground drowns, then carry on for 2 m of drowned ramp.
    stop = ln
    for t in np.arange(0.0, ln, 0.25):
        if float(TERR.height(ax + dx * t, az + dz * t)) < w:
            stop = min(ln, t + 2.0)
            break
    if stop < 3.0:
        return

    for t in np.arange(0.0, stop, 0.7):
        g = float(TERR.height(ax + dx * t, az + dz * t))
        drowned = g < w
        # Cobbled ramp, broken up as it goes: the stones nearest the water
        # have been lifted by ice and cart wheels for two hundred years.
        loose = min(1.0, t / max(stop, 1e-6))
        for u in np.arange(-2.2, 2.21, 0.55):
            if rng.random() < loose * 0.55:
                continue
            s = rng.uniform(0.34, 0.52)
            st = M.box(s, 0.16, s * rng.uniform(0.8, 1.2), 0.03,
                       "algae" if drowned else "sett")
            st.rotate_y(rng.uniform(0, 3.14))
            st.translate(ax + dx * t + nx * u + rng.uniform(-0.1, 0.1),
                         g + 0.05 - loose * rng.uniform(0.0, 0.06),
                         az + dz * t + nz * u + rng.uniform(-0.1, 0.1))
            out.add(st)
        # Broken kerb down the north edge, missing stones and one tipped over.
        if rng.random() < 0.72:
            kb = M.box(0.62, 0.20, 0.24, 0.025, "stone")
            kb.rotate_y(math.atan2(dx, dz) + rng.uniform(-0.08, 0.08))
            kb.rotate_x(rng.uniform(-0.35, 0.12) if rng.random() < 0.3 else 0.0)
            kb.translate(ax + dx * t + nx * 2.55, g + 0.13,
                         az + dz * t + nz * 2.55)
            out.add(kb)
        # Ruts full of weed. Two of them, 1.42 m apart, which is a cart's track.
        if not drowned:
            for k in (-0.71, 0.71):
                if rng.random() < 0.4:
                    continue
                wd = M.lathe([(0.0, 0.0), (0.16, 0.02), (0.10, 0.16), (0.0, 0.24)],
                             7, "foliage")
                wd.scale(rng.uniform(0.8, 1.5), rng.uniform(0.7, 1.4),
                         rng.uniform(0.8, 1.5))
                wd.translate(ax + dx * t + nx * k, g + 0.02, az + dz * t + nz * k)
                out.add(wd)


# ---------------------------------------------------------------------------
# The North Gate
# ---------------------------------------------------------------------------

def _north_gate(out, collide, entities, asset_id, ring, rec, rng):
    """Twin drum towers, 12.8 m, the heron on the keystone, and no defence.

    Ceremonial, which for a trading town means the money went on the frame a
    visitor sees and not on anything that would stop an army: the portcullis
    groove was cut when the gate was built and no portcullis was ever fitted
    into it, the leaves have stood open so long that the ground has grown up
    against them, and the only martial thing on the whole structure is a pair
    of salvaged loops in the drums that predate it.
    """
    x, z = rec["pos"]
    (px, pz), tan, nout = ring.frame(x, z)
    g = float(TERR.height(px, pz))
    clear = float(rec["clear"])           # 4.2
    head = float(rec["head"])             # 5.0
    rise = clear * 0.5
    spring = head - rise
    depth = 4.40                          # the passage, front face to back
    R = 2.60                              # drum radius
    dx = clear * 0.5 + R - 0.72           # drum centre offset along the wall
    TOP = 12.80

    gate = M.Group()

    # -- the two drums -------------------------------------------------------
    for i, sx in enumerate((-1, 1)):
        cx = sx * dx
        body = M.lathe([(R + 0.34, -0.9), (R + 0.34, 0.55), (R, 1.25),
                        (R - 0.16, 10.90)], 18, "ashlar", close_bottom=False)
        body.translate(cx, 0, 0)
        gate.add(body)
        # Corbel table, parapet, coping — the same three moves as the curtain,
        # so the gate reads as part of the wall rather than bolted onto it.
        cor = M.lathe([(R - 0.16, 10.90), (R + 0.26, 11.34), (R + 0.26, 11.50)],
                      18, "stone", close_bottom=False)
        cor.translate(cx, 0, 0)
        gate.add(cor)
        par = M.lathe([(R + 0.24, 11.50), (R + 0.22, TOP - 0.18)], 18, "ashlar",
                      close_bottom=False, close_top=False)
        par.translate(cx, 0, 0)
        gate.add(par)
        cop = M.lathe([(R + 0.30, TOP - 0.18), (R + 0.34, TOP - 0.08),
                       (R + 0.18, TOP)], 18, "stone", close_bottom=False)
        cop.translate(cx, 0, 0)
        gate.add(cop)
        # Loops, salvaged and at the wrong height for anything.
        for k, a in enumerate((-0.75, 0.0, 0.75)):
            lp = K.arrow_loop(f"{asset_id}.loop{i}{k}", height=0.92)
            lp.rotate_y(a + (0.0 if sx < 0 else 0.0))
            lp.translate(cx - math.sin(a) * (R - 0.15), 3.35 + (k % 2) * 0.22,
                         -math.cos(a) * (R - 0.15))
            gate.add(lp)

    # -- the centre block over the passage -----------------------------------
    BW = clear + 1.8
    BH = 9.60
    # ONE prism, cut to the arch's own soffit — not a facing slab with an arch
    # drawn on it. It WAS the slab: a full-width box on each face sealed the
    # opening, and the voussoir ring and the hood mould were laid neatly over
    # the top of a gate the player could not walk through.
    soff = K.arch_soffit(clear, rise, pad=0.0, samples=17)
    prof = [(-BW * 0.5, spring)] + \
           [(sx_, spring + yy) for sx_, yy in soff] + \
           [(BW * 0.5, spring), (BW * 0.5, BH), (-BW * 0.5, BH)]
    span = M.prism(prof, depth, chamfer=0.0)
    gate.add(span.with_material("ashlar"))
    # Jamb walls below the springing, on both sides of the passage.
    for sx in (-1, 1):
        j = M.box(1.8, spring, depth, 0.03, "ashlar")
        j.translate(sx * (clear * 0.5 + 0.9), spring * 0.5, 0)
        gate.add(j)

    # -- arch rings on both faces, and the passage lining --------------------
    for sz in (-1, 1):
        arch = K.arch_ring(f"{asset_id}.arch{sz}", clear, rise=rise, ring=0.48,
                           depth=0.62, mat="ashlar", chamfer=0.026)
        arch.translate(0, spring, sz * (depth * 0.5 - 0.31))
        gate.add(arch)
        # Hood mould: the drip over the arch, and the thing that makes an arch
        # read as an arch at fifty metres rather than a hole.
        for k in range(15):
            a = math.pi * (k + 0.5) / 15.0
            hm = M.box(0.30, 0.17, 0.22, 0.02, "stone", uv_scale=MATS.uv_detail("stone", 1.25, why="0.30 m member; the library's 2 m tile shows 15% of one tile here and reads as flat colour"))
            hm.rotate_z(a - math.pi * 0.5)
            hm.translate(math.cos(a) * (rise + 0.62), spring + math.sin(a) * (rise + 0.62),
                         sz * (depth * 0.5 + 0.05))
            gate.add(hm)
    # Passage barrel, so the player walking through sees a vault and not a slot.
    for k in range(13):
        a = math.pi * (k + 0.5) / 13.0
        vb = M.box(0.52, 0.16, depth - 1.3, 0.015, "ashlar")
        vb.rotate_z(a - math.pi * 0.5)
        vb.translate(math.cos(a) * (rise - 0.02), spring + math.sin(a) * (rise - 0.02), 0)
        gate.add(vb)

    # -- the heron, carved. Pictorial, never lettering (Art Bible §2). -------
    gate.add(_heron(f"{asset_id}.keystone", 0.62)
             .translate(0.0, spring + rise + 0.30, -(depth * 0.5 + 0.14)))
    # And again, larger, on a shield panel over the hood mould — the arms of
    # the town, which is the whole of the ceremony this gate carries.
    panel = M.prism([(-1.05, 0.0), (1.05, 0.0), (1.05, 1.35), (0.0, 1.95),
                     (-1.05, 1.35)], 0.26, chamfer=0.02)
    panel.translate(0, spring + rise + 1.05, -(depth * 0.5 + 0.12))
    gate.add(panel.with_material("sandstone"))
    gate.add(_heron(f"{asset_id}.arms", 1.05, mat="sandstone")
             .translate(0.0, spring + rise + 1.30, -(depth * 0.5 + 0.28)))

    # -- portcullis groove, cut and never used -------------------------------
    for sx in (-1, 1):
        ch = M.box(0.16, spring + rise - 0.35, 0.20, 0.012, "oak_dark")
        ch.translate(sx * (clear * 0.5 - 0.10), (spring + rise - 0.35) * 0.5,
                     -(depth * 0.5 - 1.05))
        gate.add(ch)

    # -- spur stones, scored by nave hubs (TOWN_PLAN J2) ---------------------
    for sx in (-1, 1):
        for sz in (-1, 1):
            spur = M.lathe([(0.36, 0.0), (0.33, 0.62), (0.20, 1.02), (0.0, 1.14)],
                           10, "stone")
            spur.translate(sx * (clear * 0.5 - 0.08), 0.0,
                           sz * (depth * 0.5 + 0.24))
            gate.add(spur)
            for k in range(4):
                sc = M.box(0.42, 0.035, 0.05, 0.004, "stone")
                sc.rotate_y(rng.uniform(-0.3, 0.3))
                sc.translate(sx * (clear * 0.5 - 0.08),
                             0.34 + k * 0.16 + rng.uniform(-0.03, 0.03),
                             sz * (depth * 0.5 + 0.24) - sz * 0.31)
                gate.add(sc)

    # -- the leaves, standing open, and the grass grown up behind them -------
    for sx in (-1, 1):
        leaf = K.plank_door(f"{asset_id}.leaf{sx}", width=clear * 0.5 - 0.06,
                            height=spring + 0.55, mat="oak_weathered")
        leaf.rotate_y(sx * (math.pi * 0.5 - 0.14))
        leaf.translate(sx * (clear * 0.5 - 0.10), 0.0, depth * 0.5 - 0.95)
        gate.add(leaf)
        for k in range(5):
            tuft = K.leaf_cluster(f"{asset_id}.tuft{sx}{k}", radius=0.10, count=5)
            tuft.translate(sx * (clear * 0.5 - 0.32) + rng.uniform(-0.2, 0.2),
                           0.06, depth * 0.5 - 1.5 + rng.uniform(-0.5, 0.5))
            gate.add(tuft)

    # -- lamps on the outer face ---------------------------------------------
    for sx in (-1, 1):
        br = K.sign_bracket(f"{asset_id}.lampbr{sx}", reach=0.62)
        br.rotate_y(math.pi * 0.5 if sx > 0 else -math.pi * 0.5)
        br.translate(sx * (clear * 0.5 + 0.35), 3.30, -(depth * 0.5 + 0.10))
        gate.add(br)
        lam = K.lantern(f"{asset_id}.lamp{sx}", scale=1.3)
        lam.translate(sx * (clear * 0.5 + 0.92), 2.72, -(depth * 0.5 + 0.10))
        gate.add(lam)

    # -- the watch canopy, on ONE drum ---------------------------------------
    #
    # Art Bible §6: every structure needs at least one element that is visibly
    # wrong. A timber watch-house put up on the west drum long after the
    # masonry, on four crooked posts, is that element — and it is the only
    # thing on the north skyline that breaks the symmetry the gate otherwise
    # insists on.
    cx = -dx
    for k in range(4):
        a = math.pi * 0.5 * k + 0.4
        post = M.beam(2.05, 0.15, "oak_weathered", axis="y")
        post.rotate_z(rng.uniform(-0.03, 0.03))
        post.translate(cx + math.sin(a) * (R - 0.75), TOP - 0.1 + 1.02,
                       math.cos(a) * (R - 0.75))
        gate.add(post)
    canopy = M.lathe([(R - 0.30, 0.0), (R - 0.52, 0.30), (0.0, 1.75)], 8,
                     "slate", close_bottom=False)
    canopy.rotate_y(0.39)
    canopy.translate(cx, TOP + 0.92, 0)
    gate.add(canopy)

    # -- place it, then declare what it blocks -------------------------------
    # Authored with the ceremonial face — arms, hood mould, lamps, spur
    # stones — on local -Z, so local -Z has to end up pointing OUT of the town.
    yaw = CIRC.yaw_facing(nout)
    gate.rotate_y(yaw)
    gate.translate(px, g, pz)
    out.add(gate)

    for sx in (-1, 1):
        cx = sx * dx
        wx = px + tan[0] * cx
        wz = pz + tan[1] * cx
        collide(COL.cylinder((wx, g + TOP * 0.5, wz), R + 0.30, TOP + 0.9,
                             tag="gate_drum"))
        # The jamb wall between the drum and the opening.
        jx = sx * (clear * 0.5 + 0.9)
        collide(COL.box((px + tan[0] * jx, g + spring * 0.5, pz + tan[1] * jx),
                        (0.9, spring * 0.5, depth * 0.5), rot_y=yaw,
                        tag="gate_jamb"))
    # The 4.2 m arch itself is deliberately left open, and springs at 2.9 m —
    # well over a 1.75 m player — so it needs no volume at all. That is the
    # whole point of a gate, and it is what v1's one-AABB-per-venue collision
    # could never express.
    entities.append((rec["id"], "landmark.gate", (px, g, pz),
                     dict(verbs=["inspect"], cell="F2")))
    for sx in (-1, 1):
        lx = sx * (clear * 0.5 + 0.92)
        entities.append((f"{asset_id}.lamp.{'w' if sx < 0 else 'e'}",
                         "prop.lantern",
                         (px + tan[0] * lx + nout[0] * (depth * 0.5 + 0.10),
                          g + 2.72,
                          pz + tan[1] * lx + nout[1] * (depth * 0.5 + 0.10)),
                         dict(cell="F2",
                              light={"color": "#FFB35C", "intensity": 1.6,
                                     "range": 8.0})))


def _heron(asset_id, scale=1.0, mat="stone"):
    """The town's arms, carved in low relief. A bird, not a word.

    Art Bible §2 bans readable lettering anywhere in the world, so Hearthmere
    identifies itself with the heron that stands in the shallows below the
    bridge. Built as relief rather than a texture because it has to survive
    the 09:30 raking light, which is the only thing that makes a carving read.
    """
    out = M.Group()
    D = 0.13 * scale
    body = M.lathe([(0.0, 0.0), (0.30, 0.16), (0.34, 0.40), (0.16, 0.66),
                    (0.0, 0.74)], 9, mat)
    body.rotate_x(math.pi * 0.5)
    body.scale(scale, scale, D / 0.30)
    body.translate(0, 0.02 * scale, 0)
    out.add(body)
    neck = M.box(0.10 * scale, 0.62 * scale, D, 0.012, mat)
    neck.rotate_z(-0.30)
    neck.translate(0.14 * scale, 0.52 * scale, 0)
    out.add(neck)
    head = M.box(0.17 * scale, 0.15 * scale, D, 0.012, mat)
    head.translate(0.28 * scale, 0.84 * scale, 0)
    out.add(head)
    beak = M.box(0.30 * scale, 0.055 * scale, D * 0.8, 0.008, mat)
    beak.rotate_z(-0.22)
    beak.translate(0.50 * scale, 0.80 * scale, 0)
    out.add(beak)
    crest = M.box(0.16 * scale, 0.04 * scale, D * 0.7, 0.006, mat)
    crest.rotate_z(0.5)
    crest.translate(0.19 * scale, 0.94 * scale, 0)
    out.add(crest)
    for k, lx in enumerate((-0.06, 0.10)):
        leg = M.box(0.045 * scale, 0.46 * scale, D * 0.8, 0.006, mat)
        leg.rotate_z(0.06 - 0.12 * k)
        leg.translate(lx * scale, -0.22 * scale, 0)
        out.add(leg)
    # The wing, a single sweeping relief line — the one gesture that turns a
    # bird-shaped lump into a heron.
    wing = M.lathe([(0.0, 0.0), (0.26, 0.10), (0.22, 0.34), (0.0, 0.46)], 8, mat)
    wing.rotate_x(math.pi * 0.5)
    wing.rotate_z(-0.55)
    wing.scale(scale, scale, D * 0.55 / 0.26)
    wing.translate(-0.05 * scale, 0.30 * scale, -D * 0.55)
    out.add(wing)
    return out
