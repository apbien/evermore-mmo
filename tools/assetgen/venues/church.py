"""The Church of Summoning — slot 11, its tower (slot 12), perron and precinct.

Every player who ever enters Hearthmere begins inside this building, standing
on its altar, looking west down the nave and out through the open great west
door (BUILD_DIRECTIVE §3). That makes two things true that are true of no
other venue:

  1. **The interior is the product.** It is fully walkable, it is the first
     thing anyone sees, and it is lit from real openings by the real 09:30 sun.
  2. **The west door is a lens.** Everything about the west end — how wide the
     portal is, how high the floor sits, how the perron falls away from it — is
     decided by what has to be visible through it, not by what looks best from
     the street.

## The building

A parish church, not a cathedral. Hearthmere is three hundred people; they
built this out of the stone that was already in the field, in one campaign,
and it has been patched ever since. Coursed rubble walls with dressed ashlar
only where the money had to go — quoins, jambs, arch rings, the tower's
belfry. Semicircular arcade arches on stumpy round piers, because the men who
cut them knew one arch and cut it five times a side.

The one thing in the building the town could never have afforded is the
**altar**: imported alabaster on a marble-inlaid dais, with a bronze ring set
into the floor round it. It arrived with the summoning, and the town has been
living with strangers materialising on it ever since — which is why the
flagstones are worn into a path from the dais to the doors, why there is a
rail to keep the curious back, why there are offerings at the rail from people
hoping someone will arrive, and why there is a bench where somebody waits.

## Geometry note — the venue frame

`content/town/hearthmere.json` places this venue at world `(44, 0, -0.5)` with
`rotationDeg 270`, and the renderer and the client both apply that as a
three.js `rotation.y`. So venue-local maps to world as

    world_x = 44 - lz      world_z = -0.5 + lx      world_y = ly
    lz      = 44 - world_x lx      = world_z + 0.5

i.e. **local +Z is west, out of the great door**, and **local +X is south**.
Every number below is venue-local unless it says otherwise. The altar (world
`43, -0.5`) is local `(0, 1)`; `playerSpawn` is local `(0, 3.30, 1)`.

This file used to *derive* that frame, working out by hand that the design
front had to be turned 180 degrees to land on the slot — which was the right
answer, reached the wrong way, and it was the hand fix that two later agents
each re-derived into a core module of their own. The arithmetic is gone.
`core.siting.Site` owns the correction now (D-025); this venue declares
`authored=pi`, meaning "these 1400 lines of coordinates are already the design
frame turned by 180 degrees", and core computes the residual. Today that
residual is exactly zero, so not one vertex moves. If the plan ever changes
slot 11's rotation the residual stops being zero and `build` raises, rather
than silently mirroring the most important composition in the game.

## Why the perron is one long flight

See `review/reports/church.md` §2. Short version: the altar eye is 2.52 m above
the church floor and 11.0 m back from the threshold, so the sightline that
grazes the door sill falls at 0.229 m/m. Any step that drops faster than that
is hidden behind the sill. Ten uniform 0.80 m treads at 0.16 m rise hold the
nosing line at 0.20 and keep the whole flight in frame; a landing spends run
without spending height, and every arrangement with landings put part of the
flight under the sightline.

The other half of the same fix is the churchyard terrace — `hm.pad.churchyard`
at +0.80 in `content/town/terrain.json`, which is TOWN_PLAN §3's "churchyard
terrace, 0.9-1.6 m exposed, the graveyard is the fill". The church keeps its
own generated pad at 0.00 and stands on a podium that covers that pad and its
whole apron, so the step between the two pads is buried inside masonry.

The lych gate (slot 17) is NOT built here — `venues/landscape.py::_churchyard`
already builds it with the churchyard wall, the yews and the graves.
"""

from __future__ import annotations

import math

import numpy as np

from core import mesh as M
from core import kit as K
from core import roof as R
from core import siting as SI
from core import terrain as T
from core.mathx import rng_for
from core.venue import VenueContext

NAME = "church"
CELLS = ["H5", "H6", "H7", "I5", "I6", "I7", "J5", "J6", "J7"]

ASSET = "hm.slot.11.church"

# Slot 11, and the declaration that this file's coordinates are the design
# frame pre-turned by 180 degrees. See the frame note in the module docstring.
SITE = SI.Site("church", authored=math.pi)

# --- the section, all in venue-local Y (which is world Y: origin[1] is 0) ----
#
# These are not free numbers. FLOOR and DAIS are fixed by `playerSpawn`
# (43, 3.30, -0.5) = floor 2.40 + dais 0.90; RIDGE and the portal are fixed by
# the slot note; PARAPET and SPIRE by slot 12.
GROUND = 0.00           # the church's own pad, under the podium
TERRACE = 0.80          # hm.pad.churchyard — the graveyard platform
FLOOR = 2.40            # church floor / podium top
DAIS = 3.30             # altar dais top == playerSpawn Y
AISLE_HEAD = 5.10       # aisle outer wall head
ARCADE_SPRING = 5.40    # arcade impost
ARCH_RISE = 1.70        # semicircular over a 3.40 m span
AISLE_ABUT = 7.35       # where the aisle lean-to meets the nave wall
CLERE_SILL = 7.55
CLERE_HEAD = 9.15
NAVE_HEAD = 9.60        # nave wall plate
RIDGE = 14.60           # slot 11 note
PORTAL_W = 6.40         # slot 11 note: clear 6.4 m
PORTAL_APEX = 10.40     # 8.0 m above the floor
PARAPET = 18.40         # slot 12
SPIRE = 21.60           # slot 12

# --- the plan ---------------------------------------------------------------
HALF_X = 10.0           # outer wall face, north (-x) and south (+x)
HALF_Z = 12.0           # outer wall face, east (-z) and west (+z)
WALL_T = 0.70
WEST_T = 0.90           # the west front carries the portal, so it is thicker
NAVE_X = 5.40           # arcade / clerestory wall centreline
NAVE_T = 0.70
PIER = 1.10             # square of the arcade pier
PIER_Z = (6.75, 2.25, -2.25, -6.75)
RESPOND_Z = (11.0, -11.0)

# Podium. It must cover hm.pad.church (world x 30.4-57.6, z -12.1-11.1) AND its
# 1.2 m apron, or the 0.80 m step down to the church's own pad shows as a
# gutter round the walls. In local terms that is lz -14.8..15.0, lx +-12.8.
POD_X = 13.10
POD_Z0, POD_Z1 = -15.00, 12.00      # east .. west wall line
POD_WEST = 15.20                    # the two wings either side of the perron

# Perron. Ten treads, 0.80 going, 0.16 rise, 15 m wide: FLOOR down to TERRACE.
#
# NOT named `GOING`, and the name is the point. Art Bible §3 puts a step going at
# 0.28 m and tools/validate.py enforces it on that name. A perron is a
# processional flight taken two paces to the tread, not a stair, and 0.80 m is
# forced by the sightline: ten risers into the 8.0 m of run that holds the mean
# slope under 0.229. At 0.28 m the flight is 2.8 m long, falls at 0.57, and
# vanishes behind the threshold. Declared exception, recorded as D-045.
PERRON_HALF = 7.50
TREADS = 10
PERRON_GOING = 0.80
RISER = (FLOOR - TERRACE) / TREADS   # 0.16 exactly

# Tower, slot 12: world x 32..39.6, z -18.1..-10.5.
TOW_X0, TOW_X1 = -17.60, -10.00
TOW_Z0, TOW_Z1 = 4.40, 12.00
TOW_CX, TOW_CZ = (TOW_X0 + TOW_X1) * 0.5, (TOW_Z0 + TOW_Z1) * 0.5

# The 09:30 sun, as a direction of TRAVEL in venue-local space. Derived, not
# guessed: content/town/hearthmere.json has elevation 38, azimuth 125, and
# tools/render/town.html puts the light at
# (cos EL sin AZ, sin EL, cos EL cos AZ), so light travels along the negative
# of that. Rotated into this venue: local dx = world dz, local dz = -world dx.
_EL, _AZ = math.radians(38.0), math.radians(125.0)
SUN_L = (
    -math.cos(_EL) * math.cos(_AZ),   # local +X  (world +Z, south)
    -math.sin(_EL),                   # down
    +math.cos(_EL) * math.sin(_AZ),   # local +Z  (world -X, west)
)


# ---------------------------------------------------------------------------
# Masonry helpers
# ---------------------------------------------------------------------------

def _wall(x0, x1, z0, z1, y0, y1, mat="rubble", uv=None, chamfer=0.03):
    """An axis-aligned block of walling from corner to corner."""
    m = M.box(abs(x1 - x0), abs(y1 - y0), abs(z1 - z0), chamfer, mat, uv_scale=uv)
    m.translate((x0 + x1) * 0.5, (y0 + y1) * 0.5, (z0 + z1) * 0.5)
    return m


def _quoins(g, x, z, y0, y1, seed, mat="ashlar", size=0.42):
    """Alternating dressed corner stones. The cheapest signal of money spent."""
    rng = rng_for(seed, "quoin")
    n = max(1, int((y1 - y0) / 0.44))
    h = (y1 - y0) / n
    for i in range(n):
        lng = (i % 2 == 0)
        b = M.box(size * (1.5 if lng else 1.0), h * 0.94,
                  size * (1.0 if lng else 1.5), 0.02, mat)
        b.translate(x + rng.uniform(-0.006, 0.006), y0 + h * (i + 0.5),
                    z + rng.uniform(-0.006, 0.006))
        g.add(b)


def _opening(g, centre, w, h, normal_axis, depth, sill_mat="ashlar",
             glass=None, seed="win", head="flat", frame=True):
    """A window: dressed jambs, a sill, a head, and its glazing set back.

    `normal_axis` is 'x' or 'z' — the axis the wall's thickness runs along.
    `centre` is (lx, ly, lz) at the middle of the opening.
    """
    cx, cy, cz = centre
    rng = rng_for(seed, "opening")
    jamb = 0.20
    if normal_axis == "z":
        span_ax, thick_ax = 0, 2
    else:
        span_ax, thick_ax = 2, 0

    def blk(du, dv, su, sv, mat=sill_mat, extra=0.02):
        """du/dv are offsets along the span axis and Y; su/sv their sizes."""
        sx = su if span_ax == 0 else depth + extra
        sz = depth + extra if span_ax == 0 else su
        b = M.box(sx, sv, sz, 0.022, mat)
        b.translate(cx + (du if span_ax == 0 else 0.0), cy + dv,
                    cz + (du if span_ax == 2 else 0.0))
        g.add(b)

    if frame:
        for s in (-1, 1):
            blk(s * (w * 0.5 + jamb * 0.5), 0.0, jamb, h + 0.30)
        blk(0.0, -(h * 0.5 + 0.12), w + jamb * 2, 0.24)          # sill
        if head == "arch":
            ring = K.arch_ring(f"{seed}.head", w + 0.10, w * 0.5 + 0.06,
                               ring=0.26, depth=depth + 0.02, mat=sill_mat)
            if span_ax == 2:
                ring.rotate_y(math.pi * 0.5)
            ring.translate(cx, cy + h * 0.5 - w * 0.5 + 0.02, cz)
            g.add(ring)
        else:
            blk(0.0, h * 0.5 + 0.13, w + jamb * 2, 0.26)         # lintel
    if glass:
        pane = M.box(w if span_ax == 0 else 0.05, h * 0.98,
                     0.05 if span_ax == 0 else w, 0.006, glass)
        pane.translate(cx, cy, cz)
        g.add(pane)
        # Saddle bars: horizontal irons across the light, and the read that
        # says leaded glass rather than a coloured rectangle.
        for k in range(1, 3):
            bar = M.box(w * 0.98 if span_ax == 0 else 0.035, 0.030,
                        0.035 if span_ax == 0 else w * 0.98, 0.004, "iron")
            bar.translate(cx, cy - h * 0.5 + h * k / 3.0, cz)
            g.add(bar)
    return rng


# ---------------------------------------------------------------------------
# Precinct: podium, terrace paving, perron
# ---------------------------------------------------------------------------

def _podium(ctx, g):
    """The knowe platform the church stands on, and its retaining faces.

    TOWN_PLAN §3: "rubble retaining wall ... 0.9-1.6 m exposed. The graveyard
    is the fill." Here it stands 1.60 m out of the churchyard terrace and the
    full 2.40 m out of the church's own pad, and it exists structurally as well
    as visually: it is what hides the step between those two pads.
    """
    parts = [
        # main platform, under the church and its apron
        (-POD_X, POD_X, POD_Z0, POD_Z1),
        # the two wings either side of the head of the perron
        (-POD_X, -PERRON_HALF, POD_Z1, POD_WEST),
        (PERRON_HALF, POD_X, POD_Z1, POD_WEST),
        # the spur that carries the tower at the north-west angle
        (TOW_X0 - 1.20, -POD_X, TOW_Z0 - 1.20, TOW_Z1 + 1.20),
    ]
    for i, (x0, x1, z0, z1) in enumerate(parts):
        g.add(_wall(x0, x1, z0, z1, GROUND - 0.35, FLOOR - 0.06,
                    "rubble", chamfer=0.04))
        # Chamfered ashlar coping along the top of every exposed face.
        g.add(_wall(x0, x1, z0, z1, FLOOR - 0.06, FLOOR, "ashlar",
                    chamfer=0.035))
        _quoins(g, x0 + 0.24, z0 + 0.24, TERRACE - 0.2, FLOOR, f"{ASSET}.pod{i}.a")
        _quoins(g, x1 - 0.24, z0 + 0.24, TERRACE - 0.2, FLOOR, f"{ASSET}.pod{i}.b")
        _quoins(g, x0 + 0.24, z1 - 0.24, TERRACE - 0.2, FLOOR, f"{ASSET}.pod{i}.c")
        _quoins(g, x1 - 0.24, z1 - 0.24, TERRACE - 0.2, FLOOR, f"{ASSET}.pod{i}.d")

    # Terrace paving, laid as a ring outside the walls so it never fights the
    # interior floor for the same plane.
    rng = rng_for(ASSET, "paving")
    for (x0, x1, z0, z1) in (
            (-POD_X, -HALF_X, POD_Z0, POD_WEST),      # north walk
            (HALF_X, POD_X, POD_Z0, POD_WEST),        # south walk
            (-HALF_X, HALF_X, POD_Z0, -HALF_Z),       # east walk
            (-PERRON_HALF, PERRON_HALF, HALF_Z, POD_Z1 + 0.001),
            (-POD_X, -PERRON_HALF, POD_Z1, POD_WEST),
            (PERRON_HALF, POD_X, POD_Z1, POD_WEST),
            (TOW_X0 - 1.20, -POD_X, TOW_Z0 - 1.20, TOW_Z1 + 1.20)):
        if x1 - x0 < 0.05 or z1 - z0 < 0.05:
            continue
        q = M.quad(x1 - x0, z1 - z0, "flag", uv_scale=ctx.uv_scale("flag"))
        q.translate((x0 + x1) * 0.5, FLOOR + 0.008, (z0 + z1) * 0.5)
        g.add(q)

    # A low coped wall round the terrace edge, broken for the perron and the
    # porch. Without it the podium is a table people fall off.
    for (x0, x1, z0, z1) in (
            (-POD_X, POD_X, POD_Z0, POD_Z0 + 0.42),           # east edge
            (-POD_X, -POD_X + 0.42, POD_Z0, TOW_Z0 - 1.20),   # north, east half
            (POD_X - 0.42, POD_X, POD_Z0, 2.80),              # south, east half
            (POD_X - 0.42, POD_X, 6.20, POD_WEST),            # south, west half
            (-POD_X, -PERRON_HALF, POD_WEST - 0.42, POD_WEST),
            (PERRON_HALF, POD_X, POD_WEST - 0.42, POD_WEST)):
        if x1 - x0 < 0.05 or z1 - z0 < 0.05:
            continue
        g.add(_wall(x0, x1, z0, z1, FLOOR, FLOOR + 0.46, "rubble"))
        g.add(_wall(x0 - 0.05, x1 + 0.05, z0 - 0.05, z1 + 0.05,
                    FLOOR + 0.46, FLOOR + 0.56, "ashlar", chamfer=0.03))
        _ = rng


def _perron(ctx, g):
    """The great flight. Ten treads, and the most looked-at stone in the town.

    Each tread is a nested block that reaches the ground rather than a floating
    slab, so the flight is a solid mass of masonry seen from the churchyard and
    a stair seen from above.
    """
    rng = rng_for(ASSET, "perron")
    for i in range(1, TREADS + 1):
        top = FLOOR - RISER * i
        z0 = HALF_Z + PERRON_GOING * (i - 1)
        # Nested: every tread reaches back under the one above it and down to
        # the terrace, so there is no cavity and no floating nosing.
        b = M.box(PERRON_HALF * 2.0, top - (GROUND - 0.30), PERRON_GOING + 0.06,
                  0.024, "stone")
        # Dish the tread toward its centre — two hundred years of boots. It is
        # geometry, not texture, because it is what catches the 09:30 light
        # along the flight.
        dish = np.clip(1.0 - np.abs(b.v[:, 0]) / PERRON_HALF, 0.0, 1.0)
        b.v[:, 1] -= (dish * 0.022 * (b.v[:, 1] > top - 0.4)).astype(np.float32)
        b.translate(0.0, (top + GROUND - 0.30) * 0.5, z0 + (PERRON_GOING + 0.06) * 0.5)
        g.add(b)
        # A dressed ashlar nosing let into the front of every tread, standing
        # 18 mm proud. This is the whole reason the flight reads from the
        # altar. Seen from an eye 2.5 m above the head of the flight the treads
        # are almost edge-on, so their SURFACES carry no information — but ten
        # crisp light-toned lines running across the frame at decreasing
        # spacing are unmistakably a stair, and they survive the church's own
        # shadow because the nosing catches the sky as well as the sun.
        nose = M.box(PERRON_HALF * 2.0 - 0.04, 0.16, 0.20, 0.014, "ashlar")
        nose.translate(0.0, top - 0.062, z0 + 0.10)
        g.add(nose)

    # Cheek walls: stepped parapets either side, coped.
    #
    # These do more work in the arrival frame than the treads do, and the
    # reason is worth writing down. The nosing line falls at 0.20 and the
    # sightline from the altar falls at 0.229, so the treads are seen almost
    # edge-on: the whole flight projects into a band about 11 px tall at 900 p.
    # The cheeks are 1.05 m clear of the nosings, so they project ~40 px and
    # they STEP, which is what actually says "stairs" at that angle. Lower them
    # and the foreground goes back to being a grey ramp.
    CHEEK = 1.05
    for s in (-1, 1):
        for i in range(TREADS + 1):
            z = HALF_Z + PERRON_GOING * i
            top = FLOOR - RISER * i + CHEEK
            g.add(_wall(s * PERRON_HALF, s * (PERRON_HALF + 0.62), z,
                        z + PERRON_GOING + 0.02, GROUND - 0.3, top - 0.12,
                        "rubble"))
            g.add(_wall(s * (PERRON_HALF - 0.06), s * (PERRON_HALF + 0.70), z,
                        z + PERRON_GOING + 0.02, top - 0.12, top, "ashlar", chamfer=0.035))
        # Newels: a square pier at the head of each cheek and a worn ball at
        # the foot. Two verticals at the top of the flight and two at the
        # bottom is what gives the frame its near jambs at ground level.
        pier = M.box(0.86, 1.95, 0.86, 0.03, "ashlar")
        pier.translate(s * (PERRON_HALF + 0.30), FLOOR + 0.98, HALF_Z + 0.42)
        g.add(pier)
        cap = M.prism([(-0.55, 0.0), (0.55, 0.0), (0.0, 0.62)], 1.10, "ashlar",
                      chamfer=0.03)
        cap.translate(s * (PERRON_HALF + 0.30), FLOOR + 1.95, HALF_Z + 0.42)
        g.add(cap)
        foot = M.box(0.92, 1.30, 0.92, 0.03, "ashlar")
        foot.translate(s * (PERRON_HALF + 0.34), TERRACE + 0.65,
                       HALF_Z + PERRON_GOING * TREADS + 0.48)
        g.add(foot)
        ball = M.lathe([(0.0, 0.0), (0.22, 0.11), (0.28, 0.32), (0.21, 0.53),
                        (0.07, 0.62), (0.0, 0.64)], 12, "stone")
        ball.translate(s * (PERRON_HALF + 0.34), TERRACE + 1.30,
                       HALF_Z + PERRON_GOING * TREADS + 0.48)
        g.add(ball)

    # Inner cheeks, and the reason they exist is measured.
    #
    # The outer cheeks at ±7.5 m are OUTSIDE the door cone: at the perron's foot
    # the jambs crop the view to ±5.5 m, so from the altar they are hidden
    # behind the doorway and contribute nothing to the arrival frame. These sit
    # at ±3.1 m, just inside the cone all the way down, and they are what
    # actually says "the ground falls away" — two coped walls stepping down and
    # converging, dividing the flight into a processional way and two side
    # flights the way a real perron does. They are 0.55 m, low enough to see
    # over from the altar (the sightline clears them by 0.4 m at the foot) and
    # tall enough to read.
    for s in (-1, 1):
        for i in range(TREADS + 1):
            z = HALF_Z + PERRON_GOING * i
            top = FLOOR - RISER * i + 0.55
            g.add(_wall(s * 2.85, s * 3.35, z, z + PERRON_GOING + 0.02,
                        GROUND - 0.3, top - 0.10, "rubble"))
            g.add(_wall(s * 2.79, s * 3.41, z, z + PERRON_GOING + 0.02,
                        top - 0.10, top, "ashlar", chamfer=0.03))
        # A squat standard part way down each, carrying an iron lamp: two
        # verticals inside the cone, at different heights, and the only lit
        # thing in a shadowed foreground after dark.
        for i in (3, 7):
            z = HALF_Z + PERRON_GOING * (i + 0.5)
            base = FLOOR - RISER * i + 0.55
            pier = M.box(0.62, 1.15, 0.62, 0.028, "ashlar")
            pier.translate(s * 3.10, base + 0.575, z)
            g.add(pier)
            lam = K.lantern(f"{ASSET}.perron.lamp.{s}.{i}")
            lam.translate(s * 3.10, base + 1.15, z)
            g.add(lam)

    # Residue: the flight is swept, but not into the corners.
    for i in range(int(rng.integers(9, 14))):
        t = rng.integers(0, TREADS)
        leaf = M.box(rng.uniform(0.05, 0.11), 0.012, rng.uniform(0.05, 0.10),
                     0.002, "foliage")
        leaf.rotate_y(rng.uniform(0, math.tau))
        leaf.translate(rng.choice([-1, 1]) * rng.uniform(PERRON_HALF - 0.9, PERRON_HALF - 0.15),
                       FLOOR - RISER * (int(t) + 1) + 0.012,
                       HALF_Z + PERRON_GOING * (int(t) + rng.uniform(0.2, 0.8)))
        g.add(leaf)


# ---------------------------------------------------------------------------
# Shell
# ---------------------------------------------------------------------------

def _aisle_walls(ctx, g):
    """North and south aisle walls, with their windows."""
    for s, side in ((-1, "n"), (1, "s")):
        x_out = s * HALF_X
        x_in = s * (HALF_X - WALL_T)
        # The wall in runs between the window openings.
        g.add(_wall(x_out, x_in, -HALF_Z, HALF_Z, FLOOR - 0.9, AISLE_HEAD,
                    "rubble", chamfer=0.035))
        # Plinth offset — every wall in this town stands out of the wet.
        g.add(_wall(x_out - s * 0.14, x_in, -HALF_Z - 0.14, HALF_Z + 0.14,
                    FLOOR - 0.9, FLOOR + 0.62, "rubble"))
        g.add(_wall(x_out - s * 0.16, x_in, -HALF_Z - 0.16, HALF_Z + 0.16,
                    FLOOR + 0.62, FLOOR + 0.72, "ashlar", chamfer=0.03))

    # Aisle windows: two-centred lights, deep splayed reveals, dark glass. Four
    # a side; the north-west bay is taken by the tower.
    for s in (-1, 1):
        for z in (8.9, 4.5, 0.0, -4.5, -9.0):
            if s < 0 and z > 4.0:
                continue                       # tower stands here
            _opening(g, (s * (HALF_X - WALL_T * 0.5), FLOOR + 2.05, z),
                     0.95, 1.55, "x", WALL_T + 0.06, glass="stained_dark",
                     seed=f"{ASSET}.aisle.{s}.{z}", head="arch")


def _arcade(ctx, g, interior):
    """Four piers a side, five semicircular arches, and the clerestory over.

    The arcade is the whole architecture of the interior: it makes the nave a
    room inside a room, it is what the light shafts fall across, and its round
    arches are the building's date. Cut once and repeated, because that is what
    a village mason does.
    """
    rng = rng_for(ASSET, "arcade")
    for s in (-1, 1):
        x = s * NAVE_X
        # -- piers ---------------------------------------------------------
        for i, z in enumerate(PIER_Z):
            base = M.box(PIER + 0.24, 0.30, PIER + 0.24, 0.03, "ashlar")
            base.translate(x, FLOOR + 0.15, z)
            drum = M.cylinder(PIER * 0.5, ARCADE_SPRING - FLOOR - 0.62, 14, 0.02,
                              "ashlar")
            drum.translate(x, FLOOR + 0.30, z)
            cap = M.lathe([(PIER * 0.5, 0.0), (PIER * 0.5 + 0.04, 0.10),
                           (PIER * 0.62, 0.22), (PIER * 0.62, 0.32)], 14, "ashlar")
            cap.translate(x, ARCADE_SPRING - 0.32, z)
            abac = M.box(PIER + 0.30, 0.16, PIER + 0.30, 0.022, "ashlar")
            abac.translate(x, ARCADE_SPRING - 0.08, z)
            for m in (base, drum, cap, abac):
                g.add(m)
            _ = i
        # -- responds against the end walls --------------------------------
        for z in RESPOND_Z:
            r = M.box(PIER * 0.62, ARCADE_SPRING - FLOOR, PIER, 0.024, "ashlar")
            r.translate(x - s * PIER * 0.24, FLOOR + (ARCADE_SPRING - FLOOR) * 0.5, z)
            g.add(r)
            ab = M.box(PIER * 0.8, 0.16, PIER + 0.24, 0.022, "ashlar")
            ab.translate(x - s * PIER * 0.16, ARCADE_SPRING - 0.08, z)
            g.add(ab)

        # -- arches and the wall they carry --------------------------------
        posts = sorted(list(PIER_Z) + list(RESPOND_Z))
        for i in range(len(posts) - 1):
            za, zb = posts[i], posts[i + 1]
            fa = za + (PIER * 0.5 if za in PIER_Z else PIER * 0.5)
            fb = zb - (PIER * 0.5 if zb in PIER_Z else PIER * 0.5)
            span = fb - fa
            mid = (fa + fb) * 0.5
            ring = K.arch_ring(f"{ASSET}.arch.{s}.{i}", span, span * 0.5,
                               ring=0.38, depth=NAVE_T + 0.04, mat="ashlar")
            ring.rotate_y(math.pi * 0.5)
            ring.translate(x, ARCADE_SPRING, mid)
            g.add(ring)
            # Spandrel above the extrados, up to the clerestory sill course.
            top_of_arch = ARCADE_SPRING + span * 0.5 + 0.38
            g.add(_wall(x - NAVE_T * 0.5, x + NAVE_T * 0.5, fa - 0.1, fb + 0.1,
                        top_of_arch, CLERE_SILL - 0.02, "rubble"))
            # and the corners the arch leaves open, over each springing
            for zz in (fa, fb):
                g.add(_wall(x - NAVE_T * 0.5, x + NAVE_T * 0.5,
                            zz - 0.55 if zz == fb else zz,
                            zz if zz == fb else zz + 0.55,
                            ARCADE_SPRING, top_of_arch, "rubble"))
        # over the piers themselves
        for z in list(PIER_Z) + list(RESPOND_Z):
            g.add(_wall(x - NAVE_T * 0.5, x + NAVE_T * 0.5,
                        z - PIER * 0.55, z + PIER * 0.55,
                        ARCADE_SPRING, CLERE_SILL - 0.02, "rubble"))

        # -- clerestory ----------------------------------------------------
        # One light per bay. The NORTH range is the one the 09:30 sun comes
        # through (azimuth 125 puts it at world +X/-Z, i.e. local -X), so these
        # are the openings that actually throw the shafts.
        for i in range(len(posts) - 1):
            zc = (posts[i] + posts[i + 1]) * 0.5
            _opening(g, (x, (CLERE_SILL + CLERE_HEAD) * 0.5, zc),
                     1.42, CLERE_HEAD - CLERE_SILL, "x", NAVE_T + 0.06,
                     glass="stained", seed=f"{ASSET}.clere.{s}.{i}", head="arch")
            # wall either side of the light and above its head
            for sgn in (-1, 1):
                g.add(_wall(x - NAVE_T * 0.5, x + NAVE_T * 0.5,
                            zc + sgn * 0.92, zc + sgn * 2.40,
                            CLERE_SILL - 0.02, NAVE_HEAD, "rubble"))
            g.add(_wall(x - NAVE_T * 0.5, x + NAVE_T * 0.5, zc - 0.94, zc + 0.94,
                        CLERE_HEAD + 0.16, NAVE_HEAD, "rubble"))
            g.add(_wall(x - NAVE_T * 0.5, x + NAVE_T * 0.5, zc - 0.94, zc + 0.94,
                        CLERE_SILL - 0.28, CLERE_SILL - 0.02, "rubble"))
        # the stretch of clerestory wall beyond the end lights
        for z0, z1 in ((-HALF_Z, posts[0]), (posts[-1], HALF_Z)):
            g.add(_wall(x - NAVE_T * 0.5, x + NAVE_T * 0.5, z0, z1,
                        ARCADE_SPRING, NAVE_HEAD, "rubble"))
    _ = rng, interior


def _west_front(ctx, g):
    """The great west door, the lens the whole town is composed through.

    Clear 6.4 m x 8.0 m to the arch apex, doors standing open against the
    reveals. Nothing else on this wall may reach into the cone the door opens:
    the jambs are the frame of the arrival composition.
    """
    zo, zi = HALF_Z, HALF_Z - WEST_T
    half = PORTAL_W * 0.5
    spring = PORTAL_APEX - half                        # apex - half-span

    # The west front is three masses, not one slab: the two aisle ends, which
    # stop under their own lean-to roofs, and the nave centre carrying the
    # portal and the gable over it. Running one wall the full width to the nave
    # plate is what made the first pass read as a barn end.
    for s in (-1, 1):
        g.add(_wall(s * (NAVE_X + NAVE_T * 0.5), s * HALF_X, zi, zo,
                    FLOOR - 0.9, AISLE_ABUT + 0.30, "rubble",
                    chamfer=0.035))
        _quoins(g, s * (HALF_X - 0.24), zo - 0.24, FLOOR - 0.6,
                AISLE_ABUT + 0.30, f"{ASSET}.wfq.{s}")
        # a lancet lighting each aisle's west bay
        _opening(g, (s * 7.9, FLOOR + 2.35, zo - WEST_T * 0.5), 0.80, 1.75, "z",
                 WEST_T + 0.06, glass="stained_dark", seed=f"{ASSET}.wlanc.{s}",
                 head="arch")
        # the nave wall between the portal jamb and the arcade line
        g.add(_wall(s * half, s * (NAVE_X + NAVE_T * 0.5), zi, zo,
                    FLOOR - 0.9, NAVE_HEAD, "rubble", chamfer=0.035))
    # over the portal head
    g.add(_wall(-half, half, zi, zo, PORTAL_APEX + 0.42, NAVE_HEAD,
                "rubble"))

    # Spandrels: the masonry between the arch's extrados and the square of the
    # opening. Without them the portal is a rectangular hole with an arch drawn
    # on it, which is what the first pass built and what read from the altar.
    soffit = K.arch_soffit(PORTAL_W + 1.04, half + 0.52, pad=0.0, samples=17)
    for i in range(len(soffit) - 1):
        (xa, ya), (xb, yb) = soffit[i], soffit[i + 1]
        top = spring + half + 0.52 + 0.40
        for xx in (xa, xb):
            pass
        lo = max(ya, yb) + spring - (half + 0.52)
        lo = spring + max(ya, yb)
        if lo >= NAVE_HEAD - 0.02:
            continue
        x0, x1 = min(xa, xb), max(xa, xb)
        if x1 <= -half - 0.02 or x0 >= half + 0.02:
            continue
        x0, x1 = max(x0, -half), min(x1, half)
        if x1 - x0 < 0.01:
            continue
        g.add(_wall(x0, x1, zi, zo, lo, NAVE_HEAD, "rubble",
                    chamfer=0.0))
        _ = top

    # The portal itself: a deep order of dressed jambs and a big arch ring.
    for s in (-1, 1):
        g.add(_wall(s * half, s * (half + 0.52), zi - 0.30, zo + 0.06,
                    FLOOR, spring, "ashlar", chamfer=0.03))
        # nook shafts in the reveal
        sh = M.cylinder(0.13, spring - FLOOR - 0.30, 10, 0.012, "ashlar")
        sh.translate(s * (half + 0.20), FLOOR + 0.18, zo - WEST_T * 0.5)
        g.add(sh)
    # NOT rotated. `kit.arch_ring` already opens across local X with its barrel
    # running along local Z, which is exactly what a west portal in this venue
    # needs — the door is 6.4 m wide in X and the wall's thickness runs in Z.
    # Rotating it (as the arcade arches legitimately do, because those span Z)
    # stood the whole ring on end down the middle of the doorway: a floating
    # column of voussoirs in the dead centre of the arrival frame, with no arch
    # anywhere. It was the single worst artefact in the first render.
    # `span` is the CLEAR opening the ring stands over, and `ring` is the depth
    # of the stones outside it. Passing the ring's outer span instead put the
    # intrados a metre wider than the doorway, so every voussoir sat inside the
    # masonry either side and the portal rendered as a plain rectangular hole
    # with no arch at all — which is what the first arrival frame showed.
    ring = K.arch_ring(f"{ASSET}.portal", PORTAL_W, half,
                       ring=0.52, depth=WEST_T + 0.30, mat="ashlar")
    ring.translate(0.0, spring, zo - WEST_T * 0.5 + 0.08)
    g.add(ring)
    # A second, thinner ring set back in the reveal: two orders and a shadow
    # line between them, which is what makes a portal deep rather than cut.
    inner = K.arch_ring(f"{ASSET}.portal.inner", PORTAL_W, half,
                        ring=0.30, depth=0.62, mat="ashlar")
    inner.translate(0.0, spring, zi - 0.34)
    g.add(inner)
    # A hood mould over it, stopped on two worn corbels.
    g.add(_wall(-half - 0.95, half + 0.95, zo - 0.02, zo + 0.20,
                PORTAL_APEX + 0.10, PORTAL_APEX + 0.42, "ashlar"))

    # The doors, standing open flat against the reveals. Never closed: this is
    # the one door in Hearthmere that is never shut.
    # The two leaves, swung right back INSIDE against the west wall — where a
    # 3.2 m leaf physically has to go, and, not by accident, clear of the
    # ±3.2 m cone the arrival frame is composed through. They are never shut.
    rng = rng_for(ASSET, "doors")
    leaf_h = spring - FLOOR + 1.9
    for s in (-1, 1):
        leaf = M.Group()
        for i in range(6):
            p = M.box(0.50, leaf_h, 0.075, 0.008, "oak_dark")
            p.translate(-1.30 + i * 0.52, 0.0, 0.0)
            leaf.add(p)
        for y in (-leaf_h * 0.33, 0.0, leaf_h * 0.33):
            band = M.box(3.05, 0.17, 0.055, 0.006, "iron")
            band.translate(0.0, y, -0.06)
            leaf.add(band)
            for k in range(4):
                boss = M.lathe([(0.0, 0.0), (0.036, 0.013), (0.028, 0.032)], 7, "iron")
                boss.rotate_x(math.pi * 0.5)
                boss.translate(-1.20 + k * 0.80, y, -0.10)
                leaf.add(boss)
        # A ring handle low down on the inner leaf edge, worn bright.
        hdl = M.ring(0.16, 0.026, "iron", segments=14, tilt=0.0)
        hdl.rotate_x(math.pi * 0.5)
        hdl.translate(s * 1.35, -leaf_h * 0.5 + 1.15, -0.12)
        leaf.add(hdl)
        leaf.rotate_y(s * 0.14)
        leaf.translate(s * (half + 1.62), FLOOR + leaf_h * 0.5, zi - 0.12)
        g.add(leaf)
        _ = rng

    # The threshold stone, dished 40 mm by everyone who ever arrived.
    th = M.box(PORTAL_W + 0.9, 0.22, WEST_T + 0.5, 0.02, "stone")
    dish = np.clip(1.0 - np.abs(th.v[:, 0]) / (PORTAL_W * 0.5), 0.0, 1.0)
    th.v[:, 1] -= (dish * 0.045 * (th.v[:, 1] > 0)).astype(np.float32)
    th.translate(0.0, FLOOR - 0.10, zo - WEST_T * 0.5)
    g.add(th)

    # Great west window, up in the gable over the portal. Sized so its head
    # stays inside the rake of the gable rather than cutting through it.
    _opening(g, (0.0, 12.05, zo - WEST_T * 0.5), 2.30, 2.50, "z", WEST_T + 0.06,
             glass="stained", seed=f"{ASSET}.westwin", head="arch")


def _east_end(ctx, g):
    """The chancel wall behind the altar, and its window."""
    zo, zi = -HALF_Z, -HALF_Z + WALL_T
    g.add(_wall(-HALF_X, HALF_X, zo, zi, FLOOR - 0.9, NAVE_HEAD, "rubble", chamfer=0.035))
    for s in (-1, 1):
        _quoins(g, s * (HALF_X - 0.24), zo + 0.24, FLOOR - 0.6, NAVE_HEAD,
                f"{ASSET}.eq.{s}")
    # Three stepped lights, the middle one taller. Behind the player at spawn,
    # but it is what the town sees coming up the Bailey.
    for i, (dx, h) in enumerate(((-1.55, 2.30), (0.0, 2.95), (1.55, 2.30))):
        _opening(g, (dx, FLOOR + 3.05 + h * 0.5 - 1.15, zo + WALL_T * 0.5),
                 0.95, h, "z", WALL_T + 0.06, glass="stained",
                 seed=f"{ASSET}.east.{i}", head="arch")


def _gables(ctx, g, plate_pts, pitch, y0, mat="rubble"):
    """Close the nave gables at both ends, up to the rake."""
    for z, sgn in ((HALF_Z, 1), (-HALF_Z, -1)):
        prof = [(-NAVE_X - NAVE_T * 0.5, y0), (NAVE_X + NAVE_T * 0.5, y0),
                (0.0, y0 + pitch * (NAVE_X + NAVE_T * 0.5))]
        p = M.prism(prof, WEST_T if sgn > 0 else WALL_T, mat, chamfer=0.02)
        p.translate(0.0, 0.0, z - sgn * (WEST_T if sgn > 0 else WALL_T) * 0.5)
        g.add(p)
    _ = plate_pts


# ---------------------------------------------------------------------------
# Roofs
# ---------------------------------------------------------------------------

def _nave_roof(ctx):
    pts = [(NAVE_X + NAVE_T * 0.5, -HALF_Z), (NAVE_X + NAVE_T * 0.5, HALF_Z),
           (-NAVE_X - NAVE_T * 0.5, HALF_Z), (-NAVE_X - NAVE_T * 0.5, -HALF_Z)]
    plate = R.wall_plate(pts, NAVE_HEAD, edges=["eaves", "gable", "eaves", "gable"],
                         thickness=NAVE_T, wall_mat="rubble")
    pitch = (RIDGE - NAVE_HEAD) / (NAVE_X + NAVE_T * 0.5)
    return R.roof_from_plate(plate, "gable", pitch, 0.38, f"{ASSET}.roof.nave",
                             mat="slate", timber_mat="oak_dark", verge=0.30)


def _aisle_roof(side):
    """A lean-to falling from the nave wall to the aisle wall head.

    `core.roof`'s lean_to falls from its -V head to its +V eaves, and V is the
    left-perpendicular of edge 0, so the winding of these four points is load
    bearing: edge 0 must run along the HEAD, with the plate to its left.
    """
    xi = side * (NAVE_X + NAVE_T * 0.5)      # head, against the nave wall
    xo = side * HALF_X                       # eaves, the aisle wall head
    if side < 0:
        pts = [(xi, -HALF_Z - 0.2), (xi, HALF_Z + 0.2),
               (xo, HALF_Z + 0.2), (xo, -HALF_Z - 0.2)]
    else:
        pts = [(xi, HALF_Z + 0.2), (xi, -HALF_Z - 0.2),
               (xo, -HALF_Z - 0.2), (xo, HALF_Z + 0.2)]
    run = abs(xo - xi)
    pitch = (AISLE_ABUT - AISLE_HEAD) / run
    plate = R.wall_plate(pts, AISLE_HEAD, thickness=WALL_T, wall_mat="rubble")
    rf = R.roof_from_plate(plate, "lean_to", pitch, 0.30,
                           f"{ASSET}.roof.aisle.{side}", mat="slate",
                           timber_mat="oak_dark", verge=0.26)
    # Prove the fall runs the right way rather than assuming it: a lean-to
    # built backwards drains into the nave and nothing downstream notices.
    if rf.ridge_y < AISLE_HEAD + 0.05:
        raise RuntimeError(f"aisle roof {side}: head {rf.ridge_y:.2f} is not "
                           f"above the eaves {AISLE_HEAD:.2f} — plate winding")
    return rf


def _roof_frame(g):
    """The trusses, which is what the interior actually shows of the roof.

    Looking up from the nave floor is half the interior, and a bare deck reads
    as a lid. Five tie-beam trusses on the bay centres, with king posts and
    braces, plus purlins running the length.
    """
    rng = rng_for(ASSET, "trusses")
    posts = sorted(list(PIER_Z) + list(RESPOND_Z))
    half = NAVE_X + NAVE_T * 0.5
    for i in range(len(posts) - 1):
        z = (posts[i] + posts[i + 1]) * 0.5
        sag = rng.uniform(0.0, 0.05)
        tie = M.beam(half * 2.0 + 0.5, 0.30, "oak_dark", 0.02, axis="x")
        tie.translate(0.0, NAVE_HEAD + 0.20 - sag, z)
        g.add(tie)
        for s in (-1, 1):
            rl = math.hypot(half, RIDGE - NAVE_HEAD - 0.20)
            raft = M.box(rl, 0.24, 0.16, 0.014, "oak_dark")
            raft.rotate_z(-s * math.atan2(RIDGE - NAVE_HEAD - 0.30, half))
            raft.translate(s * half * 0.5, (NAVE_HEAD + RIDGE) * 0.5 - 0.05, z)
            g.add(raft)
            br = M.box(1.5, 0.18, 0.14, 0.012, "oak_dark")
            br.rotate_z(s * 0.78)
            br.translate(s * 0.72, NAVE_HEAD + 0.85, z)
            g.add(br)
        king = M.box(0.22, RIDGE - NAVE_HEAD - 0.42, 0.20, 0.014, "oak_dark")
        king.translate(0.0, (NAVE_HEAD + RIDGE) * 0.5 - 0.02, z)
        g.add(king)
    # Purlins and the ridge piece.
    for s in (-1, 1):
        for f in (0.35, 0.70):
            p = M.beam(HALF_Z * 2.0, 0.18, "oak_dark", 0.012, axis="z")
            p.rotate_x(0.0)
            p.translate(s * half * (1.0 - f), NAVE_HEAD + (RIDGE - NAVE_HEAD) * f, 0.0)
            g.add(p)
    ridge = M.beam(HALF_Z * 2.0, 0.22, "oak_dark", 0.014, axis="z")
    ridge.translate(0.0, RIDGE - 0.30, 0.0)
    g.add(ridge)


def _fleche(g):
    """The louvred flèche over the altar bay — the "lantern" of the slot note.

    Small, lead-covered and off the ridge line by nothing: it is the mark on
    the skyline that says where inside the building the altar is, and at
    silhouette it is what stops the nave reading as one long shed.
    """
    z = 1.0
    base = M.box(1.90, 1.30, 3.40, 0.03, "lead")
    base.translate(0.0, 13.70 + 0.65, z)
    g.add(base)
    for s in (-1, 1):
        # louvre boards on the long faces
        for i in range(5):
            bd = M.box(0.10, 0.16, 3.10, 0.008, "oak_dark")
            bd.rotate_z(-s * 0.55)
            bd.translate(s * 0.92, 13.95 + i * 0.22, z)
            g.add(bd)
    body = M.box(1.60, 1.70, 3.00, 0.025, "lead")
    body.translate(0.0, 15.00 + 0.85, z)
    g.add(body)
    cap = M.prism([(-1.05, 0.0), (1.05, 0.0), (0.0, 1.55)], 3.30, "lead",
                  chamfer=0.02)
    cap.rotate_y(0.0)
    cap.translate(0.0, 16.70, z)
    g.add(cap)
    fin = M.lathe([(0.0, 0.0), (0.09, 0.10), (0.05, 0.40), (0.11, 0.52),
                   (0.03, 0.72), (0.0, 0.86)], 8, "bronze")
    fin.translate(0.0, 18.25, z)
    g.add(fin)


# ---------------------------------------------------------------------------
# Tower — slot 12, the tallest thing in Hearthmere
# ---------------------------------------------------------------------------

def _tower(ctx, g):
    rng = rng_for("hm.slot.12.church_tower", "tower")
    hw = (TOW_X1 - TOW_X0) * 0.5
    stages = (FLOOR, 8.20, 12.60, 16.20, PARAPET)

    for i in range(len(stages) - 1):
        y0, y1 = stages[i], stages[i + 1]
        # Each stage steps in 60 mm with a weathered set-off — the batter that
        # stops a 16 m tower reading as an extruded rectangle.
        inset = i * 0.06
        g.add(_wall(TOW_X0 + inset, TOW_X1 - inset, TOW_Z0 + inset,
                    TOW_Z1 - inset, y0, y1, "rubble", chamfer=0.04))
        if i:
            g.add(_wall(TOW_X0 + inset - 0.10, TOW_X1 - inset + 0.10,
                        TOW_Z0 + inset - 0.10, TOW_Z1 - inset + 0.10,
                        y0 - 0.16, y0, "ashlar", chamfer=0.05))

    # Clasping buttresses on the two free angles, dying back in stages.
    for cx, cz in ((TOW_X0, TOW_Z0), (TOW_X0, TOW_Z1)):
        for k, (top, proj) in enumerate(((9.4, 1.05), (13.6, 0.72), (16.4, 0.42))):
            g.add(_wall(cx, cx + proj, cz - math.copysign(proj, cz - TOW_CZ),
                        cz, FLOOR - 0.6, top, "rubble"))
            g.add(_wall(cx - 0.06, cx + proj + 0.06,
                        cz - math.copysign(proj + 0.06, cz - TOW_CZ), cz,
                        top, top + 0.22, "ashlar", chamfer=0.06))
            _ = k
    _quoins(g, TOW_X0 + 0.26, TOW_CZ, FLOOR, PARAPET, f"{ASSET}.tq.a")

    # West door of the tower, onto the churchyard — the way the ringers get in.
    _opening(g, (TOW_CX, FLOOR + 1.15, TOW_Z1 - 0.5), 1.15, 2.30, "z", 1.10,
             glass=None, seed=f"{ASSET}.towdoor", head="arch")
    dr = K.plank_door(f"{ASSET}.towdoor", width=1.10, height=2.20,
                      mat="oak_weathered")
    dr.translate(TOW_CX, FLOOR, TOW_Z1 - 0.42)
    g.add(dr)

    # Lancets up the stages, then the belfry: two louvred openings a face.
    for y in (9.10, 13.30):
        for zz, ax in ((TOW_Z1 - 0.5, "z"), (TOW_Z0 + 0.5, "z")):
            _opening(g, (TOW_CX, y, zz), 0.42, 1.45, ax, 1.10,
                     glass="stained_dark", seed=f"{ASSET}.lanc.{y}.{zz}",
                     head="arch")
        _opening(g, (TOW_X0 + 0.5, y, TOW_CZ), 0.42, 1.45, "x", 1.10,
                 glass="stained_dark", seed=f"{ASSET}.lanc.{y}.w", head="arch")

    for (ox, oz, ax) in ((TOW_CX, TOW_Z1 - 0.55, "z"), (TOW_CX, TOW_Z0 + 0.55, "z"),
                         (TOW_X0 + 0.55, TOW_CZ, "x")):
        for s in (-1, 1):
            cx = ox + (s * 1.15 if ax == "x" else 0.0)
            cz = oz + (s * 1.15 if ax == "z" else 0.0)
            _opening(g, (cx if ax == "z" else ox, 17.05, cz if ax == "z" else oz),
                     0.85, 2.10, ax, 1.05, glass=None,
                     seed=f"{ASSET}.belfry.{ax}.{s}", head="arch", frame=True)
            # Louvres — a belfry opening is never glazed; it has to let sound out.
            for k in range(7):
                bd = M.box(0.80 if ax == "z" else 0.14, 0.13,
                           0.14 if ax == "z" else 0.80, 0.008, "oak_weathered")
                bd.rotate_x(0.45 if ax == "z" else 0.0)
                bd.rotate_z(0.0 if ax == "z" else 0.45)
                bd.translate(cx if ax == "z" else ox, 16.15 + k * 0.29,
                             cz if ax == "z" else oz)
                g.add(bd)

    # Embattled parapet at 18.40 with a string course under it.
    g.add(_wall(TOW_X0 - 0.16, TOW_X1 + 0.16, TOW_Z0 - 0.16, TOW_Z1 + 0.16,
                PARAPET - 1.05, PARAPET - 0.80, "ashlar", chamfer=0.05))
    per = 1.02
    for (a0, a1, fixed, axis) in ((TOW_X0, TOW_X1, TOW_Z0, "x"),
                                  (TOW_X0, TOW_X1, TOW_Z1, "x"),
                                  (TOW_Z0, TOW_Z1, TOW_X0, "z"),
                                  (TOW_Z0, TOW_Z1, TOW_X1, "z")):
        n = int((a1 - a0) / per)
        for i in range(n):
            if i % 2:
                continue
            u0 = a0 + (a1 - a0) * i / n
            u1 = a0 + (a1 - a0) * (i + 1) / n
            if axis == "x":
                g.add(_wall(u0, u1, fixed - 0.16, fixed + 0.16,
                            PARAPET - 0.80, PARAPET, "ashlar", chamfer=0.04))
            else:
                g.add(_wall(fixed - 0.16, fixed + 0.16, u0, u1,
                            PARAPET - 0.80, PARAPET, "ashlar", chamfer=0.04))
        # the solid parapet wall behind the merlons
        if axis == "x":
            g.add(_wall(a0, a1, fixed - 0.16, fixed + 0.16,
                        PARAPET - 0.80, PARAPET - 0.42, "ashlar"))
        else:
            g.add(_wall(fixed - 0.16, fixed + 0.16, a0, a1,
                        PARAPET - 0.80, PARAPET - 0.42, "ashlar"))

    # The lead spirelet, PARAPET -> SPIRE. Slot 12: 21.6 m, and by 0.1 m over
    # the guild's 21.5 m finial the tallest thing in Hearthmere.
    roofdeck = M.box(hw * 2.0 - 0.5, 0.24, hw * 2.0 - 0.5, 0.03, "lead")
    roofdeck.translate(TOW_CX, PARAPET - 0.95, TOW_CZ)
    g.add(roofdeck)
    sp = M.lathe([(hw - 0.30, 0.0), (hw - 0.42, 0.35), (0.42, SPIRE - PARAPET - 0.9),
                  (0.16, SPIRE - PARAPET - 0.25), (0.0, SPIRE - PARAPET)],
                 4, "lead")
    sp.rotate_y(math.pi * 0.25)
    sp.translate(TOW_CX, PARAPET - 0.55, TOW_CZ)
    g.add(sp)
    van = M.box(0.42, 0.30, 0.02, 0.004, "bronze")
    van.translate(TOW_CX + 0.20, SPIRE + 0.30, TOW_CZ)
    g.add(van)
    rod = M.cylinder(0.035, 0.85, 6, 0.004, "bronze")
    rod.translate(TOW_CX, SPIRE - 0.30, TOW_CZ)
    g.add(rod)
    _ = rng


# ---------------------------------------------------------------------------
# Porch
# ---------------------------------------------------------------------------

def _porch(ctx, g):
    """South porch over the everyday door. The west door is ceremonial; this
    is the one the town actually uses, which is why the step under it is dished
    and the west threshold is only worn."""
    z0, z1 = 0.60, 4.20
    x0, x1 = HALF_X, HALF_X + 2.70
    for zz in (z0, z1):
        g.add(_wall(x0 - 0.2, x1, zz, zz + 0.55, FLOOR - 0.9, FLOOR + 3.05,
                    "rubble", chamfer=0.035))
        _quoins(g, x1 - 0.26, zz + 0.28, FLOOR, FLOOR + 3.05, f"{ASSET}.porch.{zz}")
    ring = K.arch_ring(f"{ASSET}.porcharch", 2.10, 1.05, ring=0.34, depth=0.60,
                       mat="ashlar")
    ring.rotate_y(math.pi * 0.5)
    ring.translate(x1 - 0.30, FLOOR + 1.95, (z0 + z1) * 0.5)
    g.add(ring)
    g.add(_wall(x1 - 0.62, x1, z0 + 0.55, z1, FLOOR + 3.00, FLOOR + 3.05,
                "ashlar"))

    pts = [(x0, z0), (x0, z1 + 0.55), (x1, z1 + 0.55), (x1, z0)]
    plate = R.wall_plate(pts, FLOOR + 3.05, edges=["abut", "gable", "eaves", "gable"],
                         thickness=0.5, wall_mat="rubble")
    rf = R.roof_from_plate(plate, "gable", 0.95, 0.34, f"{ASSET}.roof.porch",
                           mat="slate", timber_mat="oak_dark", verge=0.28,
                           ridge_axis="v")
    g.add(rf)

    # The priest's door in the aisle wall behind it.
    _opening(g, (HALF_X - WALL_T * 0.5, FLOOR + 1.20, (z0 + z1) * 0.5),
             1.20, 2.40, "x", WALL_T + 0.06, seed=f"{ASSET}.priestdoor",
             head="arch")
    dr = K.plank_door(f"{ASSET}.priestdoor", width=1.14, height=2.30,
                      mat="oak_weathered")
    dr.rotate_y(math.pi * 0.5)
    dr.translate(HALF_X - WALL_T + 0.06, FLOOR, (z0 + z1) * 0.5)
    g.add(dr)

    # A stone bench down each side of the porch, and a boot scraper.
    for s in (z0 + 0.75, z1 - 0.20):
        b = M.box(2.10, 0.14, 0.44, 0.02, "stone")
        b.translate((x0 + x1) * 0.5 + 0.1, FLOOR + 0.46, s)
        g.add(b)


# ---------------------------------------------------------------------------
# Interior
# ---------------------------------------------------------------------------

def _floor(ctx, g):
    """Flagstones, and the path worn into them from the dais to the doors.

    The path is the single most important piece of storytelling in the room:
    it is the record of everyone who has ever arrived on that altar and walked
    out. It is 2.9 m wide because that is what a crowd wears, it is darker and
    smoother than the flags either side, and it fans out at the threshold.
    """
    uv = ctx.uv_scale("flag")
    f = M.quad(HALF_X * 2 - WALL_T * 2, HALF_Z * 2 - WALL_T - WEST_T, "flag",
               uv_scale=uv)
    f.translate(0.0, FLOOR, (WALL_T - WEST_T) * 0.5)
    g.add(f)

    # ------------------------------------------------------------------
    # The worn path.
    #
    # THIS IS THE STAIRCASE IN `review/reports/ad-town-04.md` §1, and it is not
    # the shadow map.
    #
    # That finding — "the floor shadow is a 30 cm stair-step staircase across
    # the whole nave", `crop/arr-floor.png`, called the largest area of wrong
    # pixels in the most important composition in the build — was diagnosed by
    # reading `client/src/main.js:83` rather than by testing it. Rendering the
    # arrival frame with `tools/render/town.mjs --query shadows=0`, i.e. with
    # the sun's shadow map switched off and nothing else changed, leaves the
    # staircase exactly where it was, riser for riser. It was never light. It
    # was this:
    #
    #   24 hard-edged quads, each 0.46 m deep at a 0.42 m pitch, each a flat
    #   `with_colour((0.64, 0.60, 0.55))` — a 36 % value step with NO ramp —
    #   and each 0.55 m wider than the one behind it past z = 8. A 0.42 m tread
    #   with a 0.28 m riser, repeated down a diagonal, is a staircase by
    #   construction; the seven rotated 0.7-1.5 m quads at the dais foot are
    #   the big rectangular notches in the same crop.
    #
    # The fix is not a finer step. It is that a wear pattern has no edge at
    # all: THE BOUNDARY IS A GRADIENT, NOT A POLYGON. So the path is now a
    # continuous lattice of coplanar cells covering the whole nave floor, with
    # per-VERTEX colour sampled from a wear field — the cells butt exactly, so
    # there is no geometric seam to see anywhere, and the tint interpolates
    # across each cell instead of stepping at its edge. Cells the field never
    # reaches are white, which is COLOR_0's identity, so they are dropped and
    # cost nothing.
    #
    # Still vertex colour and still the same `flag` material, for the reason
    # the old code gave and got right: it has to read as the same stone,
    # polished, not as a different floor laid in a strip.
    rng = rng_for(ASSET, "path")
    ph1, ph2, ph3 = (float(rng.uniform(0, math.tau)) for _ in range(3))
    z0, z1 = 0.90, HALF_Z - WEST_T
    CELL = 0.55
    XMAX = 4.20                                  # past the widest of the fan

    def _centre(z):
        """The path wanders. A crowd does not walk a surveyed line, and a
        dead-straight strip is the other half of what made the old one read as
        paint."""
        return 0.19 * math.sin(z * 0.36 + ph1) + 0.11 * math.sin(z * 0.91 + ph2)

    def _half(z):
        w = 2.90 + max(0.0, z - 8.0) * 0.55       # fans out at the threshold
        w += 2.30 * math.exp(-((z - 3.05) / 2.35) ** 2)   # pool at the dais foot
        w *= 1.0 + 0.07 * math.sin(z * 0.68 + ph3)        # and the edge breathes
        return w * 0.5

    def _wear(x, z):
        """0 = untrodden, 1 = polished. The ramp is the whole point."""
        t = abs(x - _centre(z)) / max(_half(z), 1e-3)
        # Feathered over the outer half of the width, warped so no contour of
        # the field is ever a clean curve either.
        t += 0.13 * math.sin(x * 1.7 + z * 1.31 + ph1) * math.cos(z * 0.83 - ph2)
        s = 1.0 - max(0.0, min(1.0, (t - 0.18) / 0.92))
        return s * s * (3.0 - 2.0 * s)

    def _tint(x, z):
        s = _wear(x, z)
        return (1.0 - 0.36 * s, 1.0 - 0.40 * s, 1.0 - 0.45 * s)

    nz = max(1, int(round((z1 - z0) / CELL)))
    nx = max(1, int(round(2 * XMAX / CELL)))
    for i in range(nz):
        za, zb = z0 + (z1 - z0) * i / nz, z0 + (z1 - z0) * (i + 1) / nz
        for j in range(nx):
            xa, xb = -XMAX + 2 * XMAX * j / nx, -XMAX + 2 * XMAX * (j + 1) / nx
            corners = [(xa, zb), (xb, zb), (xb, za), (xa, za)]   # M.quad's order
            cols = [_tint(cx, cz) for cx, cz in corners]
            # A cell the wear never reaches is pure white, and white is the
            # identity for COLOR_0's multiply. Emitting it would be 2 triangles
            # that change no pixel.
            if min(min(c) for c in cols) > 0.995:
                continue
            p = M.quad(xb - xa, zb - za, "flag", uv_scale=uv)
            p.translate((xa + xb) * 0.5, FLOOR + 0.012, (za + zb) * 0.5)
            g.add(p.with_colour(np.asarray(cols, np.float32)))

    # Ledger stones let into the aisle floors — carved, never lettered.
    for s in (-1, 1):
        for i in range(4):
            led = M.box(1.05, 0.05, 1.90, 0.012, "sandstone")
            led.rotate_y(rng.uniform(-0.02, 0.02))
            led.translate(s * 7.5 + rng.uniform(-0.3, 0.3), FLOOR + 0.014,
                          -7.0 + i * 4.6 + rng.uniform(-0.4, 0.4))
            g.add(led)


def ctx_uv_flag():
    from core import materials as _MAT
    return _MAT.uv_scale("flag")


def _limewash(g):
    """Limewashed inner skins on every wall the nave can see.

    The walls are coursed rubble outside and they must not be coursed rubble
    inside: a village church is limewashed, and the reason matters more than
    the history — a cold grey interior eats the clerestory light instead of
    bouncing it, and what this room is FOR is light. Thin panels rather than
    two-material walls, because a wall in this venue is one box and one box is
    one material.
    """
    t = 0.06
    for s in (-1, 1):
        # aisle outer walls
        g.add(_wall(s * (HALF_X - WALL_T), s * (HALF_X - WALL_T - t),
                    -HALF_Z + WALL_T, HALF_Z - WEST_T, FLOOR, AISLE_ABUT + 0.2,
                    "limewash", chamfer=0.0))
        # clerestory / arcade wall, both faces
        for d in (-1, 1):
            g.add(_wall(s * NAVE_X + d * NAVE_T * 0.5,
                        s * NAVE_X + d * (NAVE_T * 0.5 + t),
                        -HALF_Z + WALL_T, HALF_Z - WEST_T,
                        ARCADE_SPRING + 1.9, NAVE_HEAD, "limewash",
                        chamfer=0.0))
    # east and west inner faces
    g.add(_wall(-HALF_X + WALL_T, HALF_X - WALL_T, -HALF_Z + WALL_T,
                -HALF_Z + WALL_T + t, FLOOR, NAVE_HEAD, "limewash",
                chamfer=0.0))
    for s in (-1, 1):
        g.add(_wall(s * (PORTAL_W * 0.5 + 0.55), s * (HALF_X - WALL_T),
                    HALF_Z - WEST_T - t, HALF_Z - WEST_T, FLOOR, NAVE_HEAD,
                    "limewash", chamfer=0.0))


def _light_shafts(g):
    """Where the north clerestory throws its lights onto the floor.

    Not decoration and not a guess: the sun vector is read from the same
    lighting record the renderers use, and each patch is placed by intersecting
    the ray from its own window with the floor plane. The shadow map already
    produces the light PATCH; what geometry adds is the COLOUR the glass puts
    in it, which a shadow map cannot.
    """
    dx, dy, dz = SUN_L
    posts = sorted(list(PIER_Z) + list(RESPOND_Z))
    yaw = math.atan2(dx, dz)
    for i in range(len(posts) - 1):
        zc = (posts[i] + posts[i + 1]) * 0.5
        wx = -NAVE_X                                  # north clerestory
        wy = (CLERE_SILL + CLERE_HEAD) * 0.5
        t = (wy - (FLOOR + 0.02)) / -dy
        px, pz = wx + dx * t, zc + dz * t
        if abs(px) > HALF_X - WALL_T - 0.3 or abs(pz) > HALF_Z - 1.2:
            continue                                  # falls on a wall, not the floor
        # The patch is the window stretched along the ray's ground track. It is
        # TINTED, not left at the glass's own albedo: a `stained` quad laid flat
        # reads as a sheet of paper on the floor, and what this has to read as
        # is coloured light lying in a patch of sun. Warm amber, because the
        # 09:30 sun is #FFF2D8 and the light has already been through glass.
        stretch = math.hypot(dx, dz) / -dy
        uv = ctx_uv_flag()
        # Two overlaid patches of the SAME flagstone, tinted: a warm outer
        # halo and a saturated core. Laying a `stained` quad here instead was
        # tried and rejected — the glass's own albedo is a pale leaded field,
        # so flat on the floor it reads as a sheet of paper, and its emissive
        # map ignores vertex colour so it could not be tinted down.
        h = M.quad(1.70, (CLERE_HEAD - CLERE_SILL) * stretch + 0.9, "flag",
                   uv_scale=uv)
        h.rotate_y(-yaw)
        h.translate(px, FLOOR + 0.016, pz)
        g.add(h.with_colour((1.34, 1.20, 1.00)))
        c = M.quad(0.95, (CLERE_HEAD - CLERE_SILL) * stretch * 0.86, "flag",
                   uv_scale=uv)
        c.rotate_y(-yaw)
        c.translate(px, FLOOR + 0.021, pz)
        g.add(c.with_colour((1.62, 1.24, 0.84)))


def _altar(ctx, g):
    """The summoning altar: the one thing here the town could not have bought.

    Alabaster on a marble-inlaid dais, with a bronze ring set flush in the
    floor of it. `playerSpawn` is local (0, 3.30, 1) — the middle of that ring
    — so the altar table stands EAST of it: the player materialises in the
    circle with the altar behind them, facing the doors.
    """
    rng = rng_for(ASSET, "altar")
    # Dais: three steps up to 3.30, 5.6 m square.
    for i, (hwx, hwz) in enumerate(((3.60, 3.60), (3.20, 3.20), (2.80, 2.80))):
        y = FLOOR + 0.30 * (i + 1)
        g.add(_wall(-hwx, hwx, 1.0 - hwz, 1.0 + hwz, FLOOR, y, "marble", chamfer=0.025))
    # The bronze ring flush in the dais, at the spawn point exactly.
    ring = M.lathe([(1.42, 0.0), (1.42, 0.022), (1.30, 0.026), (1.30, 0.0)],
                   32, "bronze")
    ring.translate(0.0, DAIS, 1.0)
    g.add(ring)
    inner = M.lathe([(1.30, 0.0), (1.30, 0.012), (0.0, 0.012)], 28, "alabaster")
    inner.translate(0.0, DAIS, 1.0)
    g.add(inner)
    for k in range(8):
        a = math.tau * k / 8
        spoke = M.box(0.09, 0.020, 1.24, 0.004, "bronze")
        spoke.rotate_y(a)
        spoke.translate(math.sin(a) * 0.66, DAIS + 0.020, 1.0 + math.cos(a) * 0.66)
        g.add(spoke)

    # The altar itself, east of the circle.
    az = -2.30
    base = M.box(2.60, 0.20, 1.35, 0.02, "marble")
    base.translate(0.0, DAIS + 0.10, az)
    g.add(base)
    for s in (-1, 1):
        leg = M.box(0.34, 0.90, 0.34, 0.018, "alabaster")
        leg.translate(s * 0.90, DAIS + 0.65, az)
        g.add(leg)
    mensa = M.box(2.40, 0.16, 1.15, 0.016, "alabaster")
    mensa.translate(0.0, DAIS + 1.18, az)
    g.add(mensa)
    # A carved front panel. Art Bible §2: a device, never lettering.
    for k in range(5):
        arc = K.arch_ring(f"{ASSET}.altararc.{k}", 0.34, 0.17, ring=0.05,
                          depth=0.06, mat="alabaster")
        arc.translate(-0.86 + k * 0.43, DAIS + 0.72, az + 0.60)
        g.add(arc)

    # Candles standing on it, burnt to different lengths because they are used.
    for k in range(6):
        h = rng.uniform(0.16, 0.42)
        c = M.cylinder(0.028, h, 8, 0.004, "beeswax")
        c.translate(-0.95 + k * 0.38 + rng.uniform(-0.03, 0.03),
                    DAIS + 1.26, az + rng.uniform(-0.12, 0.12))
        g.add(c)
        st = M.lathe([(0.0, 0.0), (0.09, 0.018), (0.03, 0.05), (0.035, 0.16)],
                     8, "bronze")
        st.translate(-0.95 + k * 0.38, DAIS + 1.26, az)
        g.add(st)


def _rail_and_offerings(ctx, g):
    """The rail that keeps the curious back, and what people leave on it.

    Adventurers arrive here out of nowhere. The town's response to that is not
    awe, it is a rail and a rota: somebody is always waiting, and the rail is
    where the waiting leaves its marks.
    """
    rng = rng_for(ASSET, "rail")
    r = 4.35
    gap = 0.55                                     # radians, the opening west
    n = 26
    for i in range(n):
        a = math.tau * i / n
        # leave the west opening (toward local +Z) clear
        if abs(((a) % math.tau) - 0.0) < gap or abs(((a) % math.tau) - math.tau) < gap:
            continue
        px, pz = math.sin(a) * r, 1.0 + math.cos(a) * r
        post = M.cylinder(0.035, 0.94, 8, 0.006, "iron")
        post.translate(px, FLOOR + 0.01, pz)
        g.add(post)
        if rng.random() < 0.30:                    # a ribbon, tied and left
            rb = M.box(0.05, rng.uniform(0.16, 0.34), 0.012, 0.002,
                       rng.choice(["cloth_rust", "cloth_blue", "cloth_green"]))
            rb.rotate_y(rng.uniform(0, math.tau))
            rb.translate(px, FLOOR + 0.70, pz)
            g.add(rb)
    # The top rail, as a ring of short chords.
    for i in range(n):
        a0, a1 = math.tau * i / n, math.tau * (i + 1) / n
        if min(a0, math.tau - a1) < gap:
            continue
        p0 = (math.sin(a0) * r, 1.0 + math.cos(a0) * r)
        p1 = (math.sin(a1) * r, 1.0 + math.cos(a1) * r)
        seg = M.tube((p0[0], FLOOR + 0.94, p0[1]), (p1[0], FLOOR + 0.94, p1[1]),
                     0.028, "iron", segments=6)
        g.add(seg)

    # Offerings heaped at the rail foot on the north side, where the light is.
    for i in range(int(rng.integers(14, 22))):
        a = rng.uniform(2.1, 4.2)
        px = math.sin(a) * (r + rng.uniform(0.12, 0.75))
        pz = 1.0 + math.cos(a) * (r + rng.uniform(0.12, 0.75))
        pick = rng.random()
        if pick < 0.34:
            o = M.lathe([(0.0, 0.0), (0.09, 0.02), (0.11, 0.07), (0.09, 0.09)],
                        9, "pottery")
        elif pick < 0.62:
            o = M.cylinder(0.022, rng.uniform(0.08, 0.22), 7, 0.003, "beeswax")
        elif pick < 0.85:
            o = M.box(rng.uniform(0.10, 0.22), 0.05, rng.uniform(0.08, 0.16),
                      0.006, "foliage_flower")
            o.rotate_y(rng.uniform(0, math.tau))
        else:
            o = M.box(0.16, 0.03, 0.12, 0.004, "linen")
            o.rotate_y(rng.uniform(0, math.tau))
        o.translate(px, FLOOR + 0.012, pz)
        g.add(o)

    # And the bench where somebody waits. A cloak over the end of it, because
    # whoever it is has been here since before it warmed up.
    bench = K.bench(f"{ASSET}.bench", length=2.40, height=0.46,
                    mat="oak_weathered")
    bench.rotate_y(math.pi * 0.5)
    bench.translate(-7.60, FLOOR, 4.10)
    g.add(bench)
    cloak = M.lathe([(0.20, 0.0), (0.26, 0.12), (0.16, 0.34), (0.10, 0.44)],
                    10, "cloth_brown")
    cloak.scale(1.0, 1.0, 1.9)
    cloak.translate(-7.60, FLOOR + 0.42, 3.35)
    g.add(cloak)
    lantern = K.lantern(f"{ASSET}.waitlantern")
    lantern.translate(-7.60, FLOOR + 0.50, 4.95)
    g.add(lantern)

    # A font at the west end, because a church has one and this one is older
    # than the altar by three hundred years and looks it.
    fb = M.lathe([(0.62, 0.0), (0.58, 0.16), (0.34, 0.42), (0.30, 0.62)],
                 12, "sandstone")
    fb.translate(-6.90, FLOOR, 9.20)
    g.add(fb)
    bowl = M.lathe([(0.30, 0.0), (0.72, 0.14), (0.76, 0.52), (0.66, 0.56),
                    (0.62, 0.20), (0.30, 0.16)], 12, "sandstone")
    bowl.translate(-6.90, FLOOR + 0.62, 9.20)
    g.add(bowl)


# ---------------------------------------------------------------------------
# Collision, entities
# ---------------------------------------------------------------------------

def _collision(ctx):
    """Authored, per structure (BUILD_DIRECTIVE §6.4).

    The rule that matters here is the negative one: NOTHING may close the great
    west portal or the priest's door. A player who cannot walk out of the
    church cannot reach any venue door in the town, which is §9's first box.
    """
    # Podium and terrace: walkable surfaces.
    for (x0, x1, z0, z1) in ((-POD_X, POD_X, POD_Z0, POD_Z1),
                             (-POD_X, -PERRON_HALF, POD_Z1, POD_WEST),
                             (PERRON_HALF, POD_X, POD_Z1, POD_WEST),
                             (TOW_X0 - 1.2, -POD_X, TOW_Z0 - 1.2, TOW_Z1 + 1.2)):
        ctx.collider("hull", points=[(x0, z0), (x1, z0), (x1, z1), (x0, z1)],
                     y0=GROUND - 0.35, y1=FLOOR + 0.01, kind="surface",
                     tag="church.podium")
    # Its retaining edge, so nobody walks off a 1.6 m drop by accident.
    for (x0, x1, z0, z1) in ((-POD_X, POD_X, POD_Z0, POD_Z0 + 0.45),
                             (-POD_X, -POD_X + 0.45, POD_Z0, TOW_Z0 - 1.2),
                             (POD_X - 0.45, POD_X, POD_Z0, 2.80),
                             (POD_X - 0.45, POD_X, 6.20, POD_WEST),
                             (-POD_X, -PERRON_HALF, POD_WEST - 0.45, POD_WEST),
                             (PERRON_HALF, POD_X, POD_WEST - 0.45, POD_WEST)):
        ctx.collider("box", center=((x0 + x1) * 0.5, FLOOR + 0.28, (z0 + z1) * 0.5),
                     half=(max(0.05, (x1 - x0) * 0.5), 0.28,
                           max(0.05, (z1 - z0) * 0.5)), tag="church.parapet")

    # Perron: one steppable slab per tread, nested so the ground query always
    # finds the tread the player is standing on.
    for i in range(1, TREADS + 1):
        top = FLOOR - RISER * i
        z0 = HALF_Z + PERRON_GOING * (i - 1)
        ctx.collider("box",
                     center=(0.0, (top + GROUND) * 0.5, z0 + (PERRON_GOING + 0.06) * 0.5),
                     half=(PERRON_HALF, max(0.02, (top - GROUND) * 0.5),
                           (PERRON_GOING + 0.06) * 0.5),
                     kind="surface", tag="church.perron")
    for s in (-1, 1):
        ctx.collider("box", center=(s * (PERRON_HALF + 0.28), FLOOR - 0.4,
                                    HALF_Z + PERRON_GOING * TREADS * 0.5),
                     half=(0.30, 1.4, PERRON_GOING * TREADS * 0.5), tag="church.cheek")

    # Church floor.
    ctx.collider("hull",
                 points=[(-HALF_X + WALL_T, -HALF_Z + WALL_T),
                         (HALF_X - WALL_T, -HALF_Z + WALL_T),
                         (HALF_X - WALL_T, HALF_Z - WEST_T),
                         (-HALF_X + WALL_T, HALF_Z - WEST_T)],
                 y0=FLOOR - 0.6, y1=FLOOR + 0.02, kind="surface",
                 tag="church.floor")
    # Dais, as three steppable rings.
    for i, hw in enumerate((3.60, 3.20, 2.80)):
        y = FLOOR + 0.30 * (i + 1)
        ctx.collider("box", center=(0.0, (FLOOR + y) * 0.5, 1.0),
                     half=(hw, max(0.02, (y - FLOOR) * 0.5), hw),
                     kind="surface", tag="church.dais")

    # Walls. The west run is broken for the portal; the south for the priest's
    # door and the porch arch.
    for s in (-1, 1):
        ctx.collider("box", center=(s * (HALF_X - WALL_T * 0.5), FLOOR + 3.0,
                                    -0.5 - 2.4),
                     half=(WALL_T * 0.5, 3.0, (HALF_Z - 3.4)), tag="church.wall")
    ctx.collider("box", center=(0.0, FLOOR + 3.0, -HALF_Z + WALL_T * 0.5),
                 half=(HALF_X, 3.0, WALL_T * 0.5), tag="church.wall")
    ctx.collider("box", center=(HALF_X - WALL_T * 0.5, FLOOR + 3.0, 8.4),
                 half=(WALL_T * 0.5, 3.0, 3.4), tag="church.wall")
    ctx.collider("box", center=(HALF_X - WALL_T * 0.5, FLOOR + 3.0, -0.9),
                 half=(WALL_T * 0.5, 3.0, 1.4), tag="church.wall")
    for s in (-1, 1):
        ctx.collider("box",
                     center=(s * (PORTAL_W * 0.5 + (HALF_X - PORTAL_W * 0.5) * 0.5),
                             FLOOR + 3.0, HALF_Z - WEST_T * 0.5),
                     half=((HALF_X - PORTAL_W * 0.5) * 0.5, 3.0, WEST_T * 0.5),
                     tag="church.wall")

    # Arcade piers and responds.
    for s in (-1, 1):
        for z in PIER_Z:
            ctx.collider("cylinder", center=(s * NAVE_X, FLOOR, z),
                         radius=PIER * 0.58, height=ARCADE_SPRING - FLOOR,
                         tag="church.pier")
        for z in RESPOND_Z:
            ctx.collider("box", center=(s * NAVE_X, FLOOR + 1.5, z),
                         half=(PIER * 0.4, 1.5, PIER * 0.5), tag="church.respond")

    # Tower: solid. There is a stair inside it and no reason to model it.
    ctx.collider("box", center=(TOW_CX, FLOOR + 8.0, TOW_CZ),
                 half=((TOW_X1 - TOW_X0) * 0.5, 8.0, (TOW_Z1 - TOW_Z0) * 0.5),
                 tag="church.tower")
    # Porch cheeks, doorway left open.
    for zz in (0.60, 4.20):
        ctx.collider("box", center=(HALF_X + 1.25, FLOOR + 1.6, zz + 0.28),
                     half=(1.45, 1.6, 0.28), tag="church.porch")
    ctx.collider("hull", points=[(HALF_X, 0.60), (HALF_X + 2.70, 0.60),
                                 (HALF_X + 2.70, 4.75), (HALF_X, 4.75)],
                 y0=FLOOR - 0.5, y1=FLOOR + 0.02, kind="surface",
                 tag="church.porch.floor")
    # The altar and its rail.
    ctx.collider("box", center=(0.0, DAIS + 0.65, -2.30), half=(1.35, 0.65, 0.70),
                 tag="church.altar")


def _entities(ctx):
    ctx.entity("hm.church.altar.01", "landmark.summoning_altar",
               (0.0, DAIS, 1.0), cell="I6", verbs=["inspect", "attune"],
               spawn_point={"facingDeg": 270},
               light={"color": "#BFD9FF", "intensity": 1.1, "range": 7.0})
    ctx.entity("hm.church.font.01", "prop.font", (-6.90, FLOOR + 1.18, 9.20),
               cell="I6", verbs=["inspect"])
    ctx.entity("hm.church.bench.01", "prop.bench", (-7.60, FLOOR + 0.46, 4.10),
               cell="I6", verbs=["sit"])
    ctx.entity("hm.church.offerings.01", "prop.offerings",
               (-3.0, FLOOR + 0.05, 4.2), cell="I6", verbs=["inspect", "offer"])
    ctx.entity("hm.church.door.west.01", "portal.door", (0.0, FLOOR, HALF_Z),
               cell="I6", verbs=["pass"])
    ctx.entity("hm.church.bell.01", "prop.bell", (TOW_CX, 17.0, TOW_CZ),
               cell="I5", verbs=["ring"])
    ctx.entity("hm.church.tower.01", "landmark.church_tower",
               (TOW_CX, SPIRE, TOW_CZ), cell="I5")


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build(ctx: VenueContext):
    # The frame guard. `SITE.turn` is the residual after core's correction and
    # this file's declared 180-degree pre-turn cancel, and it is zero for
    # `rotationDeg 270`. Anything else means the plan moved the church and
    # every coordinate below is now mirrored — fail rather than ship that.
    SITE.bind(ctx)
    if SITE.turn != 0.0:
        raise RuntimeError(
            f"slot 11 is now rotationDeg {SITE.rot_deg:g}; core.siting leaves a "
            f"residual turn of {math.degrees(SITE.turn):.1f} deg after this "
            f"file's authored=pi. Every coordinate in venues/church.py is "
            f"written in the old frame and would be mirrored. Re-author the "
            f"file in the design frame (+X along the frontage, -Z out of the "
            f"great door) and drop the `authored=` argument.")

    # The venue is placed at world (44, 0, -0.5); its own pad is authored at
    # 0.00 and the terrace round it at 0.80. Assert both rather than trusting
    # them: every level in this file is measured from those two numbers, and a
    # silent change to either is a church that floats or a perron that lands in
    # the air.
    pad = T.get().pad_level("hm.pad.church")
    terr = float(T.height(24.0, -0.5))
    if abs(pad - GROUND) > 0.02:
        raise RuntimeError(f"hm.pad.church is at {pad:.2f}, not {GROUND:.2f}: the "
                           f"church's section is measured from it")
    if abs(terr - TERRACE) > 0.05:
        raise RuntimeError(f"the churchyard terrace at the perron foot is "
                           f"{terr:.2f}, not {TERRACE:.2f} — hm.pad.churchyard "
                           f"in content/town/terrain.json is what sets it, and "
                           f"the perron lands on it")

    ext = M.Group()          # everything drawn from outside
    _podium(ctx, ext)
    _perron(ctx, ext)
    _aisle_walls(ctx, ext)
    _west_front(ctx, ext)
    _east_end(ctx, ext)
    _tower(ctx, ext)
    _porch(ctx, ext)

    nave = _nave_roof(ctx)
    ext.add(nave)
    _gables(ctx, ext, None, nave.pitch, NAVE_HEAD)
    for s in (-1, 1):
        ext.add(_aisle_roof(s))
    _fleche(ext)
    ctx.emit(ext, label=None, container=None)

    # -- interior, as a portal-linked cell ---------------------------------
    # Architecture §3 / Directive §7: the contents of the church are not drawn
    # from outside it. The portals are the two doors that stand open.
    iid = ctx.interior(
        "nave",
        aabb=((-HALF_X - 0.2, FLOOR - 0.8, -HALF_Z - 0.2),
              (HALF_X + 3.0, RIDGE + 0.4, HALF_Z + 0.2)),
        portals=[
            {"pos": (0.0, FLOOR + 2.6, HALF_Z), "size": (PORTAL_W, 8.0),
             "normal": (0.0, 1.0), "range": 90.0},
            {"pos": (HALF_X, FLOOR + 1.2, 2.4), "size": (1.2, 2.4),
             "normal": (1.0, 0.0), "range": 30.0},
        ])
    inner = M.Group()
    _floor(ctx, inner)
    _limewash(inner)
    _arcade(ctx, inner, iid)
    _roof_frame(inner)
    _altar(ctx, inner)
    _rail_and_offerings(ctx, inner)
    _light_shafts(inner)
    ctx.emit(inner, interior=iid)

    _collision(ctx)
    _entities(ctx)

    print(f"      church: floor {FLOOR:.2f}  dais {DAIS:.2f}  ridge {RIDGE:.2f}  "
          f"tower {SPIRE:.2f}  perron {TREADS}x{RISER:.2f}/{PERRON_GOING:.2f} "
          f"(mean slope {(FLOOR - TERRACE) / (TREADS * PERRON_GOING):.3f} vs sightline "
          f"0.229)")
