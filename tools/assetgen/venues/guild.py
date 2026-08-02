"""Adventurer's Guild — slot 02, and the hero building of Hearthmere.

Read `docs/plan/schedule.md` slot 02 before changing anything here. It is the
brief and it is specific:

    Dressed stone in a plaster town, symmetrical in a town where nothing is,
    and it bought the best block on the market place. Forecourt raised 0.42 m
    on a stylobate with four steps across the full frontage. Square tower on
    the block's NORTH-EAST corner, footprint x[-32,-25] z[-8,-1], parapet
    18.6 m, pyramid roof and iron finial to 21.5 m, crimson banners on the
    north and east faces. That tower is the far anchor of the arrival frame:
    it stands just right of the fountain at 71.5 m and closes the view west.

## Why this is a rebuild and not a polish pass

The v1 guild was authored against a 96 m grid, used NEITHER siting class, and
had no frame handling at all. D-025/D-026 turned it the right way round and
that exposed the real problem: a 19.0 x 11.5 hall plus an 8 m training yard on
a 16 x 16 plot. It overhung by 4.1 m, and the overhang was the training yard —
which put pells, a rail and archery butts standing IN Ford Road. The v1 module
says so in a comment and declares no collision for them, which is a fair
confession and not a fix. Nothing here leaves the plot.

## Where the tower goes, and how that was derived

`core.siting` authors in the DESIGN frame: `+X` along the frontage, `-Z` out of
the front door. For this slot (centre `(-33, 0)`, rot 90) that composes to

    world_x = -33 - z_design        world_z = x_design

so the note's world `x[-32,-25] z[-8,-1]` is design `x[-8,-1] z[-8,-1]`: a
7 x 7 tower on the FRONT-LEFT corner of the plot, standing on the frontage
line. Design `-X` maps to world `-Z`, so front-left is world north-east —
exactly the corner the note names. The player arriving from the market place
looks west, so the tower stands on their RIGHT and the entrance on their left.

## Symmetry, and the one thing that breaks it

"Symmetrical in a town where nothing is" is about the ENTRANCE COMPOSITION,
which is what a player reads: a centred porch, paired lights, paired banners,
paired weapon racks, a centred device over the door. The tower is the single
deliberate asymmetry, and it is the reason the building has a silhouette. A
building that was symmetrical including its tower would need two towers and
this plot cannot carry two.

## Not a church

The first v1 pass landed on a parish church — all ashlar, pointed lancets, a
conical spire, a gabled porch — and every one of those is a church cue. The
cures are kept and the reasons are still true:

  - SQUARE-HEADED mullioned lights under heavy stone lintels. The pointed arch
    was doing most of the church work on its own.
  - A PYRAMID roof and a weathervane on the tower, never a spire or a cone.
  - Battlements, corner turrets and a corbel table: a fortified hall, not a
    nave. The guild sends armed people into danger and advertises the fact.
  - A wide heavy double door a party walks through together, standing open.
  - Crimson banners, which are the only strong saturated colour on the object.
  - VISIBLE WORK in the forecourt, so a passer-by can tell what the
    organisation does without going in.

## The quest board

`ad-town-03` did not reach it and `docs/WORLD_BIBLE.md` calls it the single
most important interactable in the town, so it gets hero-class detail: layered
parchment with a real age spread, wax seals, iron pins, ribbon, and the torn
corners left behind where somebody took a job. Art Bible §2: no lettering
anywhere, ever — a notice carries marks, seals and ribbon and nothing else.
"""

from __future__ import annotations

import math

import numpy as np

from core import building as B
from core import mesh as M
from core import kit as K
from core import props as P
from core import roof as R
from core import streetscape as S
from core import siting as SI
from core.mathx import rng_for
from core.venue import VenueContext
from core import materials as MATS

NAME = "guild"
ASSET = "hm.slot.02.guild"

SITE = SI.Site(NAME)
CELLS = SITE.cells

W, D = SITE.w, SITE.d                  # 16.0 x 16.0
PLAT = 0.42                            # stylobate top — slot note
EAVES = SITE.eaves                     # 8.40 — slot schedule
PITCH = 0.62                           # broad and low: a hall, not a nave

# The hall. Set back from the frontage so the forecourt the note asks for is a
# real space and not a doorstep, and inset from the sides so the eaves oversail
# lands at x = +-7.90 — inside the plot, which is the whole point of the pass.
HALL_W = 14.80
HALL_Z0, HALL_Z1 = -3.60, 7.40
HALL_D = HALL_Z1 - HALL_Z0             # 11.0
HALL_CZ = (HALL_Z0 + HALL_Z1) * 0.5    # +1.90
STRING = 5.30                          # first-floor string course
WALL_T = 0.62                          # dressed stone, and it shows in reveal
# `building.masonry_wall` used to tile at 1.0 by default, which put 0.4 m
# blocks on an 18 m tower shaft; at 40 m those courses aliased into a
# herringbone moire, and `ad-town-04` §15 still reads it as "a chevron textile"
# on this tower and on the gatehouse cheeks. The local 0.55 that answered it was
# an approximation to the material's authored 2 m coverage. That coverage is now
# what every wall gets by default (D-046), so the local constant is gone and the
# tower is on the same masonry scale as the church and the enceinte — which is
# the "one masonry family" §8 asks for, arrived at by deleting a number rather
# than by tuning one.
ASHLAR_UV = MATS.uv_scale("ashlar")

# The tower, from the slot note, solved into the design frame (see the module
# docstring). 7 x 7 on the front-left corner.
TW_X0, TW_X1 = -8.00, -1.00
TW_Z0, TW_Z1 = -8.00, -1.00
TW_CX, TW_CZ = (TW_X0 + TW_X1) * 0.5, (TW_Z0 + TW_Z1) * 0.5
TW_W = TW_X1 - TW_X0                   # 7.0
TW_PARAPET = 18.60                     # slot note
TW_WALK = 17.55                        # wall-walk floor behind the parapet
# The slot note says "finial to 21.5"; slot 12 says the church spirelet reaches
# 21.4 and is "the tallest thing in Hearthmere by 0.1 m over the guild". Those
# two notes disagree by 0.2 m and only one of them can be true. The church's is
# the load-bearing claim — a town whose cathedral is beaten by its guild hall
# is a different town — so the guild tops out at 21.30 and the church keeps its
# 0.10 m. Recorded here because a silent 0.2 m is how plans rot.
TW_TIP = 21.30

# The entrance sits on the exposed part of the hall front: the tower occludes
# the frontage out to x = -1, so the composition is centred on x = +3.20 and
# everything on the porch is symmetrical about that line.
PORCH_X = 3.20
# The ceremonial DOUBLE doorway: two leaves of 1.77 m in a 3.60 m opening.
# Deliberately not called GATE_W/GATE_H — those names are the Art Bible §3
# single-leaf dimensions (0.95 x 2.10) and `tools/validate.py` checks any
# constant of that name against them, correctly.
GATE_W, GATE_H = 3.60, 4.10


# ---------------------------------------------------------------------------
# pieces
# ---------------------------------------------------------------------------

def _quoins(height, y0, block=0.62, size=0.44, mat="ashlar", seed_id="q"):
    """Alternating long/short corner quoins.

    Dressed corners are the cheapest possible signal of expensive masonry, and
    the alternating rhythm is what makes them read as quoins rather than as a
    column of identical bricks. Every angle on this building has them; nothing
    else in Hearthmere does.
    """
    rng = rng_for(seed_id, "quoin")
    out = M.Group()
    for i in range(int(height / block)):
        long_side = (i % 2 == 0)
        w = size * (1.42 if long_side else 0.92)
        d = size * (0.92 if long_side else 1.42)
        b = M.box(w, block * 0.965, d, 0.018, mat)
        b.translate(rng.uniform(-0.006, 0.006), y0 + block * (i + 0.5),
                    rng.uniform(-0.006, 0.006))
        out.add(b)
    return out


def _light(asset_id, x, y, z, w, h, face="-z", lights=2, lit=False,
           hood=True, mat="ashlar", detail=0):
    """One square-headed mullioned window in a thick stone wall.

    Everything that makes it read is the DRESSING, not the glass: a splayed
    reveal so the opening has depth, a projecting cill that throws water clear,
    a heavy lintel, a hood mould over it, and a mullion dividing the light. The
    square head is deliberate — see the module docstring.
    """
    out = M.Group()
    ph = h - 0.10
    pw = (w - 0.14 * (lights - 1)) / lights
    for i in range(lights):
        ox = -w * 0.5 + pw * 0.5 + i * (pw + 0.14)
        gl = B.leaded_light(f"{asset_id}.l{i}", width=pw, height=ph,
                            mat="glass_lit" if lit else "glass",
                            frame_mat="oak_dark", detail=detail)
        gl.translate(ox, 0, 0)
        out.add(gl)
    # Reveal lining: the wall's own material returned into the opening, which
    # is what a reveal IS. Without it the glass floats in a hole with no sides.
    for sx in (-1, 1):
        j = M.box(0.16, h, WALL_T * 0.72, 0.012, mat)
        j.translate(sx * (w * 0.5 + 0.08), 0, WALL_T * 0.30)
        out.add(j)
    for i in range(1, lights):
        mu = M.box(0.15, h - 0.06, WALL_T * 0.70, 0.012, mat)
        mu.translate(-w * 0.5 + i * (pw + 0.14) - 0.07, 0, WALL_T * 0.28)
        out.add(mu)
    lint = M.box(w + 0.62, 0.30, WALL_T * 0.82, 0.018, mat)
    lint.translate(0, h * 0.5 + 0.15, WALL_T * 0.18)
    out.add(lint)
    cill = M.chamfered_prism([(-(w + 0.52) * 0.5, 0.0), ((w + 0.52) * 0.5, 0.0),
                              ((w + 0.52) * 0.5, 0.14),
                              (-(w + 0.52) * 0.5, 0.20)], 0.34, "sandstone",
                             0.018, uv_scale=MATS.uv_detail("sandstone", 0.909, why="0.34 m member; the library's 2 m tile shows 17% of one tile here and reads as flat colour"))
    cill.translate(0, -h * 0.5 - 0.20, -0.20)
    out.add(cill)
    if hood:
        hd = M.chamfered_prism([(-(w + 0.86) * 0.5, 0.0), ((w + 0.86) * 0.5, 0.0),
                                ((w + 0.72) * 0.5, 0.20),
                                (-(w + 0.72) * 0.5, 0.20)], 0.20, "sandstone",
                               0.015, uv_scale=MATS.uv_detail("sandstone", 0.909, why="0.20 m member; the library's 2 m tile shows 10% of one tile here and reads as flat colour"))
        hd.translate(0, h * 0.5 + 0.36, -0.13)
        out.add(hd)
        for sx in (-1, 1):                  # label stops, one per end
            st = M.lathe([(0.10, 0.0), (0.13, 0.06), (0.07, 0.20)], 6, "sandstone")
            st.rotate_x(-np.pi * 0.5)
            st.translate(sx * (w + 0.72) * 0.5, h * 0.5 + 0.34, -0.16)
            out.add(st)
    # Turn to the face it belongs on. Authored facing -Z, like the whole kit.
    yaw = {"-z": 0.0, "+z": np.pi, "-x": -np.pi * 0.5, "+x": np.pi * 0.5}[face]
    out.rotate_y(yaw)
    out.translate(x, y, z)
    return out


def _banner(asset_id, width=2.30, height=6.60, sway=0.05, mat="wool_crimson"):
    """Hanging banner as ONE continuous displaced surface.

    This was 72 independent flat boxes on a grid. Boxes cannot share normals
    across their seams, so every panel edge caught the light differently and
    the cloth read as horizontal striping — the defect survived two review
    rounds because the fix attempted was overlap, which cannot help: the
    problem is that a box has six faces and a hanging cloth has one.

    Built instead as a single smooth-shaded quad grid, displaced by a catenary
    sag across the width and a wind-lift that grows toward the free lower
    corner, with normals derived from the actual surface. That is what makes it
    read as heavy dyed wool rather than as slats. Kept verbatim from the v1
    module because it was signed off and the fix cost two review rounds.

    The MATERIAL changed, though. `banner` carries an authored sun-bleach that
    tints the top half up to 55 % toward a lighter crimson — right on a 0.9 m
    pennant, wrong on a 6.6 m drop seen from 71.5 m, where it plus the
    atmosphere left the guild's identity reading as pale pink. The two big
    tower banners are `wool_crimson`, which is the same dyed wool without the
    fade; the small porch pair keep `banner` and are the older cloth.
    """
    rng = rng_for(asset_id, "banner")
    # Grid density follows the cloth's SIZE. A fixed 14 x 30 put 420 quads on a
    # 0.9 x 2.6 m pennant, which is four times the geometry of the sag it is
    # there to describe.
    COLS = max(6, min(14, int(round(width * 6.0))))
    ROWS = max(10, min(30, int(round(height * 4.6))))

    def surface(u, v):
        """u across the width (0..1), v down the drop (0..1)."""
        x = (u - 0.5) * width
        y = -v * height
        bow = np.sin(u * np.pi) * 0.13 * (0.30 + v)
        lift = (v ** 2.2) * 0.55 * np.sin(u * np.pi * 0.85 + 0.5)
        z = -bow - lift * 0.45
        y += lift * 0.30
        z += np.sin(u * 9.0 + v * 5.0) * 0.012 * v
        return np.array([x, y, z], np.float32)

    b = M._Builder()
    for j in range(ROWS):
        for i in range(COLS):
            u0, u1 = i / COLS, (i + 1) / COLS
            v0, v1 = j / ROWS, (j + 1) / ROWS
            p00, p10 = surface(u0, v0), surface(u1, v0)
            p11, p01 = surface(u1, v1), surface(u0, v1)
            n = np.cross(p10 - p00, p01 - p00)
            ln = float(np.linalg.norm(n))
            n = n / ln if ln > 1e-9 else np.array([0, 0, -1], np.float32)
            # NORMALISED 0..1, not metres. `banner` carries a directional
            # top-to-bottom gradient (sun-bleached at the hanging edge, dirty
            # at the hem). Mapping in metres tiled that gradient 6.6x down the
            # drop and produced the horizontal banding that survived two review
            # rounds — the seams were never the cause.
            uvs = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
            b.poly([p00, p10, p11, p01], uvs, n)
    out = M.Group().add(b.build(mat))

    # Hanging pole with finials. rotate_z(+pi/2) maps +Y onto -X, so centring
    # needs a POSITIVE half-length offset.
    pole = M.cylinder(0.046, width + 0.44, 10, 0.005, "iron")
    pole.rotate_z(np.pi * 0.5)
    pole.translate((width + 0.44) * 0.5, 0.07, 0)
    out.add(pole)
    for sx in (-1, 1):
        f = M.lathe([(0.0, 0), (0.055, 0.05), (0.03, 0.12)], 10, "iron")
        f.translate(sx * (width + 0.44) * 0.5, 0.07, 0)
        out.add(f)
        # And the bracket that actually carries it into the masonry, because
        # Directive §6.1 wants everything fixed by SHOWN hardware.
        br = M.box(0.09, 0.13, 0.44, 0.008, "iron")
        br.translate(sx * (width + 0.30) * 0.5, 0.07, 0.20)
        out.add(br)
    out.rotate_z(sway)
    return out


def _quest_board(asset_id):
    """The single most important interactable in Hearthmere.

    What sells it is the LAYERING and the age spread: notices pinned over other
    notices, some crisp and square, some sun-bleached and curling off the
    board, and the torn corners left behind where a job was taken. A tidy grid
    of identical parchment reads as a UI element, not as a thing three hundred
    people use every day.

    Art Bible §2: no readable lettering. Notices carry marks, wax seals, iron
    pins and ribbon only.
    """
    rng = rng_for(asset_id, "questboard")
    out = M.Group()

    # Frame and backing boards.
    for i in range(6):
        p = M.plank(2.42, 0.32, 0.048, 0.005, "oak_weathered")
        p.translate(0, 0.92 + i * 0.32, 0)
        out.add(p)
    for sx in (-1, 1):
        post = M.box(0.17, 2.78, 0.17, 0.012, "oak_dark")
        post.translate(sx * 1.26, 1.39, 0)
        out.add(post)
        # Iron strap and a spike foot: it is bolted to the stone, not leaning.
        st = M.box(0.20, 0.09, 0.20, 0.006, "iron")
        st.translate(sx * 1.26, 0.16, 0)
        out.add(st)
    head = M.plank(2.86, 0.22, 0.17, 0.012, "oak_dark")
    head.translate(0, 2.80, 0)
    out.add(head)
    # Small pent roof — the notices are outdoors, so they need cover.
    roof = M.prism([(-1.52, 0), (1.52, 0), (1.52, 0.06), (-1.52, 0.06)], 0.66,
                   chamfer=0.008)
    roof.rotate_x(-0.32)
    roof.translate(0, 2.94, -0.22)
    out.add(roof.with_material("oak_dark"))
    # A ledge to write against, and the guild's ink-horn chained to it.
    ledge = M.plank(2.30, 0.30, 0.05, 0.006, "oak_weathered")
    ledge.rotate_x(0.14)
    ledge.translate(0, 0.96, -0.16)
    out.add(ledge)

    # Notices. Age drives everything: colour, curl, and how square it is.
    for i in range(18):
        age = rng.uniform(0.0, 1.0)
        w = rng.uniform(0.16, 0.30)
        h = rng.uniform(0.19, 0.33)
        n = M.box(w, h, 0.004, 0.001, "parchment")
        # Old notices curl off the board and hang crooked.
        n.rotate_z(rng.uniform(-0.06, 0.06) - age * rng.uniform(0.0, 0.26))
        n.rotate_x(-age * rng.uniform(0.0, 0.32))
        nx = rng.uniform(-1.06, 1.06)
        ny = 1.06 + rng.uniform(0.0, 1.56)
        n.translate(nx, ny, -0.030 - rng.uniform(0.0, 0.014))
        out.add(n)

        # Iron pin holding it, and a wax seal on about half of them.
        pin = M.lathe([(0.010, 0), (0.015, 0.006), (0.008, 0.013)], 6, "iron")
        pin.rotate_x(-np.pi * 0.5)
        pin.translate(nx, ny + h * 0.5 - 0.03, -0.046)
        out.add(pin)
        if rng.random() < 0.5:
            seal = M.lathe([(0.0, 0), (0.021, 0.004), (0.018, 0.009)], 8, "wax")
            seal.rotate_x(-np.pi * 0.5)
            seal.translate(nx + rng.uniform(-0.05, 0.05), ny - h * 0.5 + 0.05,
                           -0.044)
            out.add(seal)
        if rng.random() < 0.22:
            # Ribbon: a sealed commission, not an open notice.
            rb = M.box(0.030, rng.uniform(0.10, 0.20), 0.003, 0.0, "wool_crimson")
            rb.rotate_z(rng.uniform(-0.5, 0.5))
            rb.translate(nx + rng.uniform(-0.06, 0.06), ny - h * 0.5 - 0.05,
                         -0.050)
            out.add(rb)

    # TORN CORNERS. Somebody took the job and ripped the notice off the pin;
    # what is left is a triangle of parchment still under the head of it. This
    # is the detail that says the board is used, and it is nine triangles.
    for i in range(5):
        tx = rng.uniform(-1.08, 1.08)
        ty = 1.10 + rng.uniform(0.0, 1.50)
        frag = M.prism([(0.0, 0.0), (rng.uniform(0.05, 0.11), -0.02),
                        (rng.uniform(0.02, 0.06), -rng.uniform(0.05, 0.10))],
                       0.003, chamfer=0.0)
        frag.rotate_z(rng.uniform(0, 6.28))
        frag.translate(tx, ty, -0.034)
        out.add(frag.with_material("parchment"))
        pin = M.lathe([(0.010, 0), (0.015, 0.006), (0.008, 0.013)], 6, "iron")
        pin.rotate_x(-np.pi * 0.5)
        pin.translate(tx, ty, -0.046)
        out.add(pin)

    return out


def _forge_sign(asset_id):
    """The guild's device, hung out over the forecourt on an iron bracket.

    Pictorial only (Art Bible §2): a shield with the crossed blades and the
    town's heron. It is the piece that identifies the building from the far
    end of the market place, so it is geometry and not a painted board.
    """
    out = M.Group()
    out.add(K.sign_bracket(asset_id, reach=1.05, mat="iron"))
    board = M.Group()
    shield = M.chamfered_prism([(-0.52, 0.46), (0.52, 0.46), (0.52, -0.06),
                                (0.30, -0.40), (0.0, -0.58), (-0.30, -0.40),
                                (-0.52, -0.06)], 0.055, "painted_crimson",
                               0.010, uv_scale=MATS.uv_detail("painted_crimson", 0.714, why="0.06 m member; the library's 2 m tile shows 3% of one tile here and reads as flat colour"))
    board.add(shield)
    rim = M.chamfered_prism([(-0.58, 0.52), (0.58, 0.52), (0.58, -0.08),
                             (0.34, -0.45), (0.0, -0.66), (-0.34, -0.45),
                             (-0.58, -0.08)], 0.030, "iron", 0.006)
    rim.translate(0, 0, 0.030)
    board.add(rim)
    for sgn in (-1, 1):
        bl = M.box(0.055, 0.86, 0.028, 0.005, "steel_blued")
        bl.rotate_z(sgn * 0.60)
        bl.translate(0, 0.02, -0.035)
        board.add(bl)
    hr = M.lathe([(0.0, 0.0), (0.075, 0.045), (0.065, 0.20), (0.0, 0.26)], 9,
                 "brass")
    hr.translate(0.0, -0.10, -0.055)
    board.add(hr)
    nk = M.cylinder(0.018, 0.20, 6, 0.002, "brass")
    nk.rotate_z(-0.34)
    nk.translate(0.05, 0.24, -0.055)
    board.add(nk)
    board.rotate_z(0.045)
    board.translate(0.78, -0.72, 0)
    out.add(board)
    return out


# ---------------------------------------------------------------------------
# assemblies
# ---------------------------------------------------------------------------

def _stylobate(ctx, g, rng):
    """The raised forecourt, its four steps, and the ground under it.

    Slot note: "Forecourt raised 0.42 m on a stylobate with four steps across
    the full frontage." The stylobate carries the whole block, so the hall, the
    tower and the forecourt are all one platform and the guild reads as having
    been SET DOWN on the best block in town, which is the story.
    """
    poly = SI.rect(0.0, 0.0, W, D)
    slab, y0 = SI.plinth_under(SITE, poly, PLAT, mat="ashlar_civic",
                               chamfer=0.035)
    g.add(slab)
    ctx.collider("box", center=SITE.p(0, (y0 + PLAT) * 0.5, 0),
                 half=(W * 0.5, max((PLAT - y0) * 0.5, 0.05), D * 0.5),
                 rot_y=SITE.yaw(), kind="surface", tag="stylobate")

    # Chamfered nosing course all round, in a second stone. One horizontal line
    # at 0.42 m is what tells the eye the whole block is lifted.
    for (cx, cz, sw, sd) in ((0.0, -D * 0.5, W, 0.46), (0.0, D * 0.5, W, 0.46),
                             (-W * 0.5, 0.0, 0.46, D), (W * 0.5, 0.0, 0.46, D)):
        g.add(SI.slab(SI.rect(cx, cz, sw, sd), PLAT - 0.07, PLAT + 0.005,
                      "sandstone", 0.02))

    # FOUR steps across the full frontage. Four risers of 0.105 m is a shallow,
    # ceremonial flight — you walk up it without breaking stride, which is the
    # difference between a guild that wants you in and a temple that does not.
    #
    # The flight climbs INWARD from the plot line, not outward from it. Built
    # the other way round it put 2.3 m of tread, cheek and bollard into the
    # street — which is the exact defect this whole pass exists to remove, and
    # it would have shipped because a step does not look like an overhang.
    n = 4
    for i in range(n):
        r = PLAT * (i + 1) / n
        tread = SI.slab(SI.rect(0.0, -D * 0.5 + 0.20 + i * 0.40, W - 0.6, 0.84),
                        r - PLAT / n - 0.02, r, "sandstone", 0.02)
        g.add(tread)
    SITE.collider_steps((0.0, PLAT, -D * 0.5 + 1.75), PLAT, tread=0.40,
                        width=W - 0.6, rot_y=np.pi)

    # Cheek walls at the ends of the flight, so it is a flight and not a ramp
    # of loose slabs, and a pair of bollards to keep carts off the steps.
    for sx in (-1, 1):
        ch = M.chamfered_prism(
            [(-0.42, 0.0), (0.42, 0.0), (0.42, PLAT + 0.12), (-0.42, 0.05)],
            1.75, "ashlar_civic", 0.022)
        ch.rotate_y(np.pi * 0.5)
        ch.translate(sx * (W * 0.5 - 0.36), 0.0, -D * 0.5 + 0.90)
        g.add(ch)
        ctx.collider("box",
                     center=SITE.p(sx * (W * 0.5 - 0.36), PLAT * 0.5,
                                   -D * 0.5 + 0.90),
                     half=(0.42, PLAT * 0.6, 0.90), rot_y=SITE.yaw(),
                     tag="step_cheek")
        bo = S.bollard(f"{ASSET}.boll{sx}", height=0.82)
        bo.translate(sx * (W * 0.5 - 0.55), 0.0, -D * 0.5 + 0.42)
        g.add(bo)

    # The paving of the forecourt itself, and the track worn across it from the
    # head of the steps to the door. Art Bible §7: the residue IS the evidence.
    fc = SI.slab(SI.rect(2.60, -5.05, 10.4, 3.2), PLAT - 0.03, PLAT + 0.012,
                 "sett", 0.012)
    g.add(fc)
    for i, (wx, wz, sz) in enumerate(((PORCH_X - 0.2, -6.40, 2.4),
                                      (0.90, -7.10, 1.8))):
        wp = P.worn_patch(f"{ASSET}.worn{i}", shape="path", size=sz, mat="sett")
        wp.rotate_y(rng.uniform(-0.35, 0.35))
        wp.translate(wx, PLAT + 0.020, wz)
        g.add(wp)


def _hall(ctx, g, rng):
    """The hall: two storeys of dressed stone, symmetrical about the porch.

    Ashlar top to bottom. The v1 module put a jettied TIMBER storey over a
    stone base to stop it reading institutional, and that was the right cure
    for the wrong disease — the church read came from the lancets and the
    spire, not from the stone, and the slot note is explicit that this building
    is dressed stone in a plaster town. The stone IS the identity. What stops
    it reading institutional is the horizontal emphasis: a broad low roof, two
    heavy string courses, and a corbel table under the eaves.
    """
    x0, x1 = -HALL_W * 0.5, HALL_W * 0.5
    ground_h = STRING - PLAT
    upper_h = EAVES - STRING

    # --- ground storey, four walls, door aperture in the front --------------
    fr = B.masonry_wall(
        HALL_W, ground_h, f"{ASSET}.gf", kind="ashlar", depth=WALL_T,
        quoins=False, uv=ASHLAR_UV,
        openings=[(PORCH_X, GATE_H * 0.5, GATE_W, GATE_H)] +
                 [(x, 2.55, 1.72, 1.90) for x in (PORCH_X - 3.30, PORCH_X + 3.30)] +
                 [(x, 2.55, 1.30, 1.80) for x in (-2.60, -5.20)])
    fr.translate(0, PLAT, HALL_Z0 + WALL_T * 0.5)
    g.add(fr)

    bk = B.masonry_wall(HALL_W, ground_h, f"{ASSET}.gb", kind="ashlar",
                        depth=WALL_T, quoins=False, uv=ASHLAR_UV,
                        openings=[(x, 2.60, 1.30, 1.70)
                                  for x in (-3.6, 1.6)])
    bk.rotate_y(np.pi)
    bk.translate(0, PLAT, HALL_Z1 - WALL_T * 0.5)
    g.add(bk)

    for sx in (-1, 1):
        sd = B.masonry_wall(HALL_D, ground_h, f"{ASSET}.gs{sx}", kind="ashlar",
                            depth=WALL_T, quoins=False, uv=ASHLAR_UV,
                            openings=[(z, 2.60, 1.30, 1.70) for z in (-2.4, 2.4)])
        # The upper storey's flanks are blank: this is a hall, and the money
        # and the glass went on the elevation the market place sees.
        sd.rotate_y(sx * np.pi * 0.5)
        sd.translate(sx * (x1 - WALL_T * 0.5), PLAT, HALL_CZ)
        g.add(sd)

    # --- string course: one shadow line right round, at first-floor level ----
    band = M.chamfered_prism(
        [(-HALL_W * 0.5 - 0.16, 0.0), (HALL_W * 0.5 + 0.16, 0.0),
         (HALL_W * 0.5 + 0.16, 0.20), (HALL_W * 0.5 + 0.02, 0.34),
         (-HALL_W * 0.5 - 0.02, 0.34), (-HALL_W * 0.5 - 0.16, 0.20)],
        HALL_D + 0.32, "sandstone", 0.020)
    band.rotate_x(np.pi * 0.5)
    band.translate(0, STRING - 0.30, HALL_CZ)
    g.add(band)

    # --- upper storey -------------------------------------------------------
    uf = B.masonry_wall(
        HALL_W, upper_h, f"{ASSET}.uf", kind="ashlar", depth=WALL_T,
        quoins=False, uv=ASHLAR_UV,
        openings=[(x, 1.66, 1.92, 1.92)
                  for x in (PORCH_X - 3.30, PORCH_X, PORCH_X + 3.30)] +
                 [(x, 1.66, 1.44, 1.80) for x in (-2.60, -5.20)])
    uf.translate(0, STRING, HALL_Z0 + WALL_T * 0.5)
    g.add(uf)

    ub = B.masonry_wall(HALL_W, upper_h, f"{ASSET}.ub", kind="ashlar",
                        depth=WALL_T, quoins=False, uv=ASHLAR_UV,
                        openings=[(x, 1.66, 1.30, 1.70)
                                  for x in (-3.6, 1.6)])
    ub.rotate_y(np.pi)
    ub.translate(0, STRING, HALL_Z1 - WALL_T * 0.5)
    g.add(ub)

    for sx in (-1, 1):
        us = B.masonry_wall(HALL_D, upper_h, f"{ASSET}.us{sx}", kind="ashlar",
                            depth=WALL_T, quoins=False, uv=ASHLAR_UV,
                            openings=[])
        us.rotate_y(sx * np.pi * 0.5)
        us.translate(sx * (x1 - WALL_T * 0.5), STRING, HALL_CZ)
        g.add(us)

    # --- the lights themselves ---------------------------------------------
    # Symmetrical about the porch axis on the front, which is the elevation
    # that matters, and NOT lit uniformly: a facade where every window glows is
    # a lightbox, not a building with people in some of its rooms.
    for i, x in enumerate((PORCH_X - 3.30, PORCH_X + 3.30)):
        g.add(_light(f"{ASSET}.gw{i}", x, PLAT + 2.55, HALL_Z0 - 0.01,
                     1.72, 1.90, lights=2, lit=True))
    for i, x in enumerate((-2.60, -5.20)):
        g.add(_light(f"{ASSET}.gwx{i}", x, PLAT + 2.55, HALL_Z0 - 0.01,
                     1.30, 1.80, lights=2, lit=False))
    for i, x in enumerate((PORCH_X - 3.30, PORCH_X, PORCH_X + 3.30)):
        g.add(_light(f"{ASSET}.uw{i}", x, STRING + 1.66, HALL_Z0 - 0.01,
                     1.92, 1.92, lights=3, lit=(i != 1)))
    for i, x in enumerate((-2.60, -5.20)):
        g.add(_light(f"{ASSET}.uwx{i}", x, STRING + 1.66, HALL_Z0 - 0.01,
                     1.44, 1.80, lights=2, lit=(i == 0)))
    for i, x in enumerate((-3.6, 1.6)):
        g.add(_light(f"{ASSET}.bw{i}", x, PLAT + 2.60, HALL_Z1 + 0.01,
                     1.30, 1.70, face="+z", lights=1, lit=False, hood=False,
                     detail=1))
        g.add(_light(f"{ASSET}.bu{i}", x, STRING + 1.66, HALL_Z1 + 0.01,
                     1.30, 1.70, face="+z", lights=1, lit=(i % 2 == 0),
                     hood=False, detail=1))
    for sx in (-1, 1):
        for j, z in enumerate((-2.4, 2.4)):
            g.add(_light(f"{ASSET}.sw{sx}{j}", sx * (x1 + 0.01), PLAT + 2.60, z,
                         1.30, 1.70, face="+x" if sx > 0 else "-x",
                         lights=1, lit=False, hood=False, detail=1))

    # --- quoins on every free angle -----------------------------------------
    for (qx, qz) in ((x0, HALL_Z0), (x1, HALL_Z0), (x0, HALL_Z1), (x1, HALL_Z1)):
        q = _quoins(EAVES - PLAT, PLAT, seed_id=f"{ASSET}.q{qx:.0f}{qz:.0f}")
        q.translate(qx, 0, qz)
        g.add(q)

    # --- corbel table under the eaves ---------------------------------------
    # A run of little brackets right round. It is the horizontal that stops the
    # wall head reading as a cut edge, and it is a fortified-hall cue, not an
    # ecclesiastical one.
    for i in range(int(HALL_W / 1.12)):
        cx = -HALL_W * 0.5 + 0.56 + i * 1.12
        for sz, zz in ((-1, HALL_Z0 - 0.05), (1, HALL_Z1 + 0.05)):
            cb = K.corbel(f"{ASSET}.cb{i}{sz}", project=0.30, width=0.26,
                          height=0.28, mat="sandstone")
            if sz > 0:
                cb.rotate_y(np.pi)
            cb.translate(cx, EAVES - 0.34, zz)
            g.add(cb)

    # --- collision ----------------------------------------------------------
    SITE.collider_walls(HALL_W, HALL_D, EAVES - PLAT, y=PLAT, thickness=WALL_T,
                        center=(0.0, HALL_CZ),
                        doors=[("-z", PORCH_X, GATE_W)], tag="hall")

    # --- the dark inside ----------------------------------------------------
    # Without a shell the open door and every one of the twenty-six openings
    # look straight through to sunlit exterior ashlar and sky, which is the
    # single strongest "facade, not a building" tell there is.
    sh = M.box(HALL_W - WALL_T * 2 - 0.10, EAVES - PLAT - 0.10,
               HALL_D - WALL_T * 2 - 0.10, 0.02, "ashlar")
    sh.scale(-1.0, 1.0, 1.0)
    sh.translate(0, PLAT + (EAVES - PLAT) * 0.5, HALL_CZ)
    SITE.emit(sh, shell=True)


def _porch_and_doors(ctx, g, rng):
    """The entrance: a projecting porch, a dished threshold, doors standing open.

    "Tall double doors always open, threshold stone dished by boots"
    (WORLD_BIBLE). The porch recess is what gives the facade depth and puts the
    quest board in shadow, which is what makes the parchment read against it.
    """
    zf = HALL_Z0
    PW, PD, PH = 6.40, 1.30, 5.70

    # Projecting bay, stepping the front plane forward. Without it the facade
    # is a single unbroken 14.8 m plane and the door is a hole in a wall.
    for sx in (-1, 1):
        w = M.box(0.62, PH, PD + 0.10, 0.022, "ashlar")
        w.translate(PORCH_X + sx * (PW * 0.5 - 0.31), PLAT + PH * 0.5,
                    zf - PD * 0.5 + 0.05)
        g.add(w)
        q = _quoins(PH, PLAT, block=0.58, size=0.40,
                    seed_id=f"{ASSET}.pq{sx}")
        q.translate(PORCH_X + sx * PW * 0.5, 0, zf - PD)
        g.add(q)
    head = M.box(PW + 0.44, 0.72, PD + 0.42, 0.026, "ashlar")
    head.translate(PORCH_X, PLAT + GATE_H + 0.42, zf - PD * 0.5)
    g.add(head)
    over = M.box(PW - 1.24, PH - GATE_H - 0.78, PD + 0.10, 0.022, "ashlar")
    over.translate(PORCH_X, PLAT + GATE_H + 0.78 + (PH - GATE_H - 0.78) * 0.5,
                   zf - PD * 0.5 + 0.05)
    g.add(over)
    # Coping and a little gable over the bay: the third horizontal, and the one
    # that breaks the eaves line from the approach.
    cop = M.chamfered_prism([(-(PW + 0.72) * 0.5, 0.0), ((PW + 0.72) * 0.5, 0.0),
                             ((PW + 0.56) * 0.5, 0.24), (0.0, 0.92),
                             (-(PW + 0.56) * 0.5, 0.24)], PD + 0.56,
                            "sandstone", 0.020)
    cop.translate(PORCH_X, PLAT + PH, zf - PD * 0.5)
    g.add(cop)
    fin = M.lathe([(0.10, 0.0), (0.13, 0.10), (0.06, 0.34), (0.10, 0.42),
                   (0.0, 0.62)], 8, "iron")
    fin.translate(PORCH_X, PLAT + PH + 0.90, zf - PD * 0.5)
    g.add(fin)

    SITE.collider("box", center=(PORCH_X - PW * 0.5 + 0.31, PLAT + PH * 0.5,
                                 zf - PD * 0.5),
                  half=(0.36, PH * 0.5, PD * 0.5 + 0.10), tag="porch")
    SITE.collider("box", center=(PORCH_X + PW * 0.5 - 0.31, PLAT + PH * 0.5,
                                 zf - PD * 0.5),
                  half=(0.36, PH * 0.5, PD * 0.5 + 0.10), tag="porch")

    # --- THE THRESHOLD, dished by boots -------------------------------------
    # A single stone, worn into a hollow across the middle where three hundred
    # people a day step onto it, and proud at the ends where nobody does. Built
    # as a sheet with a real height function, because a dish carved as two
    # boxes is a step, not a hollow.
    thr = M.sheet(GATE_W + 0.90, 1.30,
                  lambda u, v: -0.055 * math.exp(-((u - 0.5) * 3.1) ** 2)
                  * math.exp(-((v - 0.46) * 2.3) ** 2),
                  nx=11, nz=7, mat="sandstone", plane="xz")
    thr.translate(PORCH_X, PLAT + 0.075, zf - 0.42)
    g.add(thr)
    thr_b = M.box(GATE_W + 0.90, 0.15, 1.30, 0.020, "sandstone")
    thr_b.translate(PORCH_X, PLAT + 0.005, zf - 0.42)
    g.add(thr_b)
    g.add(P.worn_patch(f"{ASSET}.thrworn", shape="path", size=1.5, mat="sandstone")
          .translate(PORCH_X, PLAT + 0.092, zf - 0.42))

    # --- doors: wide, heavy, and standing open ------------------------------
    for sx in (-1, 1):
        d = K.plank_door(f"{ASSET}.door{sx}", width=GATE_W * 0.5 - 0.06,
                         height=GATE_H - 0.10, mat="oak_dark",
                         open_angle=sx * rng.uniform(0.92, 1.12))
        d.translate(PORCH_X + sx * (GATE_W * 0.5 - 0.03), PLAT + 0.10, zf + 0.04)
        g.add(d)
    # Draw-bar staples and a ring handle on each leaf: the hardware is what
    # says these doors are shut at night by somebody whose job that is.
    for sx in (-1, 1):
        rg = M.ring(0.115, 0.020, "iron", 10, tilt=0.30)
        rg.rotate_x(np.pi * 0.5)
        rg.translate(PORCH_X + sx * 2.35, PLAT + 1.10, zf - 0.34)
        g.add(rg)

    SITE.entity(f"{ASSET}.door.01", "door.guild",
                (PORCH_X, PLAT, zf - 0.20), verbs=["enter"])

    # --- the great device over the door -------------------------------------
    # Guilds advertise; a church does not. Pictorial only, Art Bible §2.
    shield = M.chamfered_prism([(-1.02, 0.92), (1.02, 0.92), (1.02, -0.16),
                                (0.58, -0.82), (0.0, -1.14), (-0.58, -0.82),
                                (-1.02, -0.16)], 0.22, "painted_crimson",
                               0.018, uv_scale=MATS.uv_detail("painted_crimson", 0.909, why="0.22 m member; the library's 2 m tile shows 11% of one tile here and reads as flat colour"))
    shield.translate(PORCH_X, PLAT + GATE_H + 1.30, zf - PD - 0.14)
    g.add(shield)
    rim = M.chamfered_prism([(-1.13, 1.02), (1.13, 1.02), (1.13, -0.19),
                             (0.65, -0.91), (0.0, -1.27), (-0.65, -0.91),
                             (-1.13, -0.19)], 0.12, "iron", 0.012)
    rim.translate(PORCH_X, PLAT + GATE_H + 1.30, zf - PD - 0.06)
    g.add(rim)
    for sgn in (-1, 1):
        bl = M.box(0.11, 1.56, 0.055, 0.008, "steel_blued")
        bl.rotate_z(sgn * 0.62)
        bl.translate(PORCH_X, PLAT + GATE_H + 1.34, zf - PD - 0.26)
        g.add(bl)
    hrn = M.lathe([(0.0, 0), (0.15, 0.09), (0.17, 0.30), (0.0, 0.48)], 10,
                  "brass")
    hrn.translate(PORCH_X, PLAT + GATE_H + 1.06, zf - PD - 0.32)
    g.add(hrn)
    nk = M.cylinder(0.036, 0.36, 7, 0.004, "brass")
    nk.rotate_z(-0.30)
    nk.translate(PORCH_X + 0.09, PLAT + GATE_H + 1.66, zf - PD - 0.32)
    g.add(nk)

    # --- the quest board, under the porch, in the shade ---------------------
    qb = _quest_board(f"{ASSET}.questboard.01")
    qb.translate(PORCH_X - PW * 0.5 - 1.85, PLAT, zf - 0.30)
    g.add(qb)
    SITE.entity(f"{ASSET}.questboard.01", "quest_board",
                (PORCH_X - PW * 0.5 - 1.85, PLAT + 1.55, zf - 0.44),
                verbs=["read"],
                quest_board={"notices": [], "capacity": 24},
                landmark={"name": "The Guild Board"},
                collider={"shape": "box", "half": [1.42, 1.42, 0.14]})
    SITE.collider("box",
                  center=(PORCH_X - PW * 0.5 - 1.85, PLAT + 1.40, zf - 0.42),
                  half=(1.42, 1.40, 0.16), tag="quest_board")

    # A lamp either side of the doors, symmetrical about the porch axis, and a
    # bench under the board where people wait to be seen.
    for sx in (-1, 1):
        lam = K.lantern(f"{ASSET}.lamp{sx}", scale=1.2)
        lam.translate(PORCH_X + sx * (PW * 0.5 - 0.42), PLAT + 2.90,
                      zf - PD - 0.06)
        g.add(lam)
        SITE.entity(f"{ASSET}.lantern.{'a' if sx < 0 else 'b'}", "prop.lantern",
                    (PORCH_X + sx * (PW * 0.5 - 0.42), PLAT + 2.90, zf - PD),
                    light={"color": "#FFB35C", "intensity": 2.0, "range": 8.0})
    bench = K.bench(f"{ASSET}.bench", length=2.30)
    bench.translate(PORCH_X - PW * 0.5 - 1.85, PLAT, zf - 1.22)
    g.add(bench)

    sign = _forge_sign(f"{ASSET}.sign")
    sign.translate(PORCH_X + PW * 0.5 - 0.20, PLAT + 4.20, zf - 0.10)
    g.add(sign)


def _tower(ctx, g, rng):
    """The square tower: the town's skyline, and the far anchor of the arrival.

    `ad-town-03.md` §3: "The town still has no skyline." From the church door
    at 43 m the fountain now holds the middle ground; this closes the view at
    71.5 m. 21.30 m at 71.5 m subtends 17 degrees — a third of the frame
    height — and it is the only vertical on that axis.

    Four things carry it, in order of how far away they still work:

      1. the MASS: 7 x 7 x 18.6, battered at the foot so it sits on the ground
      2. the STAGES: three string courses, so an 18 m shaft is four elements
      3. the HEAD: corbel table, battlements, four corner turrets, a pyramid
         roof and an iron vane — five outline changes in the top 4 m
      4. the BANNERS: 2.3 x 6.6 m of crimson on the north and east faces, the
         only strong saturated colour in this quarter of the town
    """
    hw = TW_W * 0.5
    t = 0.72                              # wall thickness

    # --- battered base ------------------------------------------------------
    bat = M.chamfered_prism(
        [(-hw - 0.34, PLAT - 0.10), (hw + 0.34, PLAT - 0.10),
         (hw + 0.06, PLAT + 1.55), (-hw - 0.06, PLAT + 1.55)],
        TW_W + 0.68, "ashlar_civic", 0.028)
    bat.translate(TW_CX, 0, TW_CZ)
    g.add(bat)

    # --- shaft: four walls, hollow, with real openings ----------------------
    stages = (PLAT + 1.55, STRING, 9.90, 14.50)
    for si, y0 in enumerate(stages):
        y1 = stages[si + 1] if si + 1 < len(stages) else TW_WALK
        h = y1 - y0
        if h <= 0.05:
            continue
        # Light pattern by stage: nothing in the base (it is a store), paired
        # lights in the middle stages, a tall belfry-scale opening at the top
        # where the lookout is. No element three times in a row (Art Bible §6).
        if si == 0:
            ops = []
        elif si == len(stages) - 1:
            ops = [(0.0, h * 0.52, 1.55, 2.35)]
        else:
            ops = [(0.0, h * 0.55, 1.35, 1.75)]
        for face, (ax, az, yaw) in (
                ("-z", (TW_CX, TW_CZ - hw + t * 0.5, 0.0)),
                ("+z", (TW_CX, TW_CZ + hw - t * 0.5, np.pi)),
                ("-x", (TW_CX - hw + t * 0.5, TW_CZ, -np.pi * 0.5)),
                ("+x", (TW_CX + hw - t * 0.5, TW_CZ, np.pi * 0.5))):
            # The +Z and +X faces are buried in the hall up to the eaves, so
            # they get no openings there — a window into a roof void is the
            # kind of detail that only ever reads as a mistake.
            buried = (face in ("+z", "+x")) and y1 <= EAVES + 0.4
            wl = B.masonry_wall(TW_W, h, f"{ASSET}.tw{si}{face}", kind="ashlar",
                                depth=t, quoins=False, uv=ASHLAR_UV,
                                openings=[] if buried else ops)
            wl.rotate_y(yaw)
            wl.translate(ax, y0, az)
            g.add(wl)
            if ops and not buried:
                ox, oy, ow, oh = ops[0]
                g.add(_light(f"{ASSET}.tl{si}{face}",
                             ax + (0.0 if face in ("-z", "+z") else
                                   (-1 if face == "-x" else 1) * (t * 0.5 - 0.01)),
                             y0 + oy,
                             az + (0.0 if face in ("-x", "+x") else
                                   (-1 if face == "-z" else 1) * (t * 0.5 - 0.01)),
                             ow, oh, face=face,
                             lights=3 if si == len(stages) - 1 else 2,
                             lit=(si == len(stages) - 1), hood=(si != 0),
                             detail=1))

    # A dark core, so the openings read as a hollow tower and not as glass
    # applied to a solid block.
    core = M.box(TW_W - t * 2 - 0.06, TW_WALK - PLAT - 0.10,
                 TW_W - t * 2 - 0.06, 0.02, "ashlar")
    core.scale(-1.0, 1.0, 1.0)
    core.translate(TW_CX, PLAT + (TW_WALK - PLAT) * 0.5, TW_CZ)
    SITE.emit(core, shell=True)

    # --- string courses -----------------------------------------------------
    for y in stages[1:]:
        sc = M.chamfered_prism(
            [(-hw - 0.20, 0.0), (hw + 0.20, 0.0), (hw + 0.20, 0.16),
             (hw + 0.03, 0.30), (-hw - 0.03, 0.30), (-hw - 0.20, 0.16)],
            TW_W + 0.40, "sandstone", 0.018)
        sc.translate(TW_CX, y - 0.26, TW_CZ)
        g.add(sc)

    # --- quoins on the two free angles -------------------------------------
    for (qx, qz) in ((TW_X0, TW_Z0), (TW_X1, TW_Z0), (TW_X0, TW_Z1)):
        q = _quoins(TW_WALK - PLAT, PLAT + 1.4, block=0.66, size=0.48,
                    seed_id=f"{ASSET}.tq{qx:.0f}{qz:.0f}")
        q.translate(qx, 0, qz)
        g.add(q)

    # --- head: corbel table, parapet, turrets, roof, vane -------------------
    for i in range(int(TW_W / 0.98) + 1):
        o = -hw + 0.49 + i * 0.98
        for (dx, dz, yaw) in ((o, -hw - 0.04, 0.0), (o, hw + 0.04, np.pi),
                              (-hw - 0.04, o, -np.pi * 0.5),
                              (hw + 0.04, o, np.pi * 0.5)):
            cb = K.corbel(f"{ASSET}.tcb{i}{dx:.1f}{dz:.1f}", project=0.34,
                          width=0.30, height=0.30, mat="sandstone")
            cb.rotate_y(yaw)
            cb.translate(TW_CX + dx, TW_WALK - 0.62, TW_CZ + dz)
            g.add(cb)
    # The oversailing course the battlements stand on.
    cor = M.chamfered_prism(
        [(-hw - 0.42, 0.0), (hw + 0.42, 0.0), (hw + 0.42, 0.26),
         (hw + 0.30, 0.34), (-hw - 0.30, 0.34), (-hw - 0.42, 0.26)],
        TW_W + 0.84, "ashlar_civic", 0.022)
    cor.translate(TW_CX, TW_WALK - 0.30, TW_CZ)
    g.add(cor)

    # Battlements. Merlon tops at exactly the noted 18.60; crenels down to
    # 18.00, which is a real embrasure and not the 0.62 m nick the v1 tower
    # had — those read as chipped stone rather than as crenellation.
    per = TW_W + 0.84
    ph = TW_PARAPET - TW_WALK
    n_m = 5
    for side, (ux, uz) in enumerate(((1, 0), (0, 1), (-1, 0), (0, -1))):
        for i in range(n_m):
            o = -per * 0.5 + (i + 0.5) * per / n_m
            top = TW_PARAPET if i % 2 == 0 else TW_PARAPET - 0.60
            m_ = M.box(per / n_m * 0.94 if ux else 0.40,
                       top - TW_WALK, 0.40 if ux else per / n_m * 0.94,
                       0.018, "ashlar_civic")
            m_.translate(TW_CX + (o if ux else uz * -(per * 0.5 - 0.20)),
                         TW_WALK + (top - TW_WALK) * 0.5,
                         TW_CZ + (o if uz else ux * (per * 0.5 - 0.20)))
            g.add(m_)

    # Four corner turrets, flush with the parapet face so nothing leaves the
    # plot, capped with their own little pyramids. Four extra outline steps at
    # 20 m, and the cheapest skyline in the build.
    for sx in (-1, 1):
        for sz in (-1, 1):
            tx = TW_CX + sx * (per * 0.5 - 0.62)
            tz = TW_CZ + sz * (per * 0.5 - 0.62)
            tu = M.box(1.24, 19.62 - TW_WALK + 0.60, 1.24, 0.020,
                       "ashlar_civic")
            tu.translate(tx, TW_WALK - 0.60 + (19.62 - TW_WALK + 0.60) * 0.5, tz)
            g.add(tu)
            cp = M.lathe([(0.94, 0.0), (0.80, 0.14), (0.0, 1.05)], 4, "lead")
            cp.rotate_y(np.pi * 0.25)
            cp.translate(tx, 19.62, tz)
            g.add(cp)

    # PYRAMID roof — never a spire, never a cone. Lead over the wall-walk,
    # springing from inside the parapet so it is carried by the tower and not
    # balanced on the battlements.
    # NOTE the sqrt(2). A 4-segment `lathe` is a SQUARE whose CORNERS are at
    # `radius`, so a radius of `hw` gives a pyramid only 0.71 * hw across the
    # flats — 4.95 m on a 7 m tower, which is exactly small enough to hide
    # entirely behind its own parapet. It did, in the first render.
    rf = M.lathe([(hw * math.sqrt(2) - 0.03, 0.0),
                  (hw * math.sqrt(2) - 0.26, 0.34),
                  (0.0, 20.55 - TW_WALK + 0.30)], 4, "lead")
    rf.rotate_y(np.pi * 0.25)
    rf.translate(TW_CX, TW_WALK - 0.30, TW_CZ)
    g.add(rf)
    # Standing seams down the four hips: what tells you it is lead and not a
    # grey cone, and it costs 4 x 12 triangles.
    for i in range(4):
        a = i * np.pi * 0.5 + np.pi * 0.25
        L = math.hypot(hw, 20.55 - TW_WALK)
        sm = M.box(0.09, L, 0.10, 0.006, "lead")
        sm.rotate_x(0.0)
        sm.rotate_z(math.atan2(hw * math.sqrt(2), 20.55 - TW_WALK))
        sm.rotate_y(-a + np.pi * 0.5)
        sm.translate(TW_CX + math.cos(a) * hw * 0.5, TW_WALK + (20.55 - TW_WALK) * 0.5,
                     TW_CZ + math.sin(a) * hw * 0.5)
        g.add(sm)

    # Finial and vane to 21.30. See the constant for the 0.2 m reconciliation.
    fin = M.lathe([(0.16, 0.0), (0.20, 0.12), (0.08, 0.34), (0.055, 0.62)],
                  8, "iron")
    fin.translate(TW_CX, 20.55, TW_CZ)
    g.add(fin)
    ball = M.globe(0.13, "brass", 10, 5)
    ball.translate(TW_CX, 20.60, TW_CZ)
    g.add(ball)
    rod = M.cylinder(0.035, TW_TIP - 21.17 + 0.55, 6, 0.004, "iron")
    rod.translate(TW_CX, 20.62, TW_CZ)
    g.add(rod)
    vane = M.chamfered_prism([(0.0, 0.0), (0.72, 0.14), (0.72, 0.46),
                              (0.0, 0.36)], 0.012, "iron", 0.003)
    vane.rotate_y(np.pi * 0.5)
    vane.rotate_y(0.55)
    vane.translate(TW_CX, TW_TIP - 0.46, TW_CZ)
    g.add(vane)
    for i in range(4):                        # cardinal points, as a cross
        a = i * np.pi * 0.5 + 0.55
        arm = M.cylinder(0.018, 0.44, 5, 0.002, "iron")
        arm.rotate_z(np.pi * 0.5)
        arm.rotate_y(-a)
        arm.translate(TW_CX + math.cos(a) * 0.22, TW_TIP - 0.80,
                      TW_CZ + math.sin(a) * 0.22)
        g.add(arm)

    # --- banners: north and east faces, per the slot note -------------------
    # `_banner` builds in the XY plane hanging from y = 0 and facing -Z, so
    # each one is turned onto its face AND pushed clear of it. The v1 pass left
    # one buried inside the tower volume and the other edge-on to the camera,
    # so neither read at all.
    #
    # Design -Z is world EAST (the market place, and the arrival axis).
    b = _banner(f"{ASSET}.banner.e", sway=rng.uniform(-0.05, 0.05))
    b.translate(TW_CX, 14.30, TW_Z0 - 0.16)
    g.add(b)
    # Design -X is world NORTH (seen from Ford Road and the north gate).
    b = _banner(f"{ASSET}.banner.n", sway=rng.uniform(-0.05, 0.05))
    b.rotate_y(-np.pi * 0.5)
    b.translate(TW_X0 - 0.16, 14.30, TW_CZ)
    g.add(b)
    # A short pair flanking the porch, on the projecting bay's own face.
    for sx in (-1, 1):
        b = _banner(f"{ASSET}.ebanner{sx}", width=0.90, height=2.60,
                    sway=rng.uniform(-0.04, 0.04), mat="banner")
        b.translate(PORCH_X + sx * 3.05, PLAT + 5.40, HALL_Z0 - 1.44)
        g.add(b)

    # --- collision ----------------------------------------------------------
    SITE.collider("box", center=(TW_CX, (PLAT + TW_WALK) * 0.5, TW_CZ),
                  half=(hw + 0.34, (TW_WALK - PLAT) * 0.5 + 0.2, hw + 0.34),
                  tag="tower")

    SITE.entity(f"{ASSET}.tower.01", "landmark.guild_tower",
                (TW_CX, TW_PARAPET, TW_CZ), verbs=["inspect"],
                landmark={"name": "The Guild Tower", "silhouette": True})


def _roof(ctx, g, rng):
    """Gable roof on the hall's plate, and the chimney through it.

    The roof takes its height from the plate and nowhere else (`core/roof.py`
    has deliberately no `y` parameter), so the eaves land on the schedule's
    8.40 by construction rather than by a hand-authored number that drifts.
    """
    poly = SI.rect(0.0, HALL_CZ, HALL_W, HALL_D)
    # Edge 0 runs along +X, so `ridge_axis="u"` lays the ridge along the
    # frontage — gables at the ends, eaves to the market. Slot: ridge "along".
    plate = R.wall_plate(poly, EAVES, edges=["eaves", "gable", "eaves", "gable"],
                         thickness=WALL_T, wall_mat="ashlar")
    roof = R.roof_from_plate(plate, "gable", PITCH, 0.50, f"{ASSET}.roof",
                             mat="slate", timber_mat="oak_dark", ridge_axis="u")
    g.add(roof)

    # Closed gable ends in the wall's own stone, with a coping and kneelers —
    # the detail that says the gable is masonry carried up, not a board.
    for sx in (-1, 1):
        ge = K.gable_end(HALL_D, EAVES, PITCH, mat="ashlar", depth=0.34)
        ge.rotate_y(np.pi * 0.5)
        ge.translate(sx * HALL_W * 0.5, 0, HALL_CZ)
        g.add(ge)
        for sz in (-1, 1):
            cp = M.box(0.34, 0.24, HALL_D * 0.54, 0.016, "sandstone")
            cp.rotate_x(sz * math.atan(PITCH))
            cp.translate(sx * (HALL_W * 0.5 + 0.10),
                         (EAVES + roof.ridge_y) * 0.5 + 0.12,
                         HALL_CZ + sz * HALL_D * 0.245)
            g.add(cp)
            kn = M.chamfered_prism([(-0.34, 0.0), (0.34, 0.0), (0.34, 0.30),
                                    (-0.20, 0.44)], 0.42, "sandstone", 0.018,
                                   uv_scale=MATS.uv_detail("sandstone", 1.11, why="0.42 m member; the library's 2 m tile shows 21% of one tile here and reads as flat colour"))
            kn.rotate_y(np.pi * 0.5)
            kn.scale(1.0, 1.0, sz)
            kn.translate(sx * (HALL_W * 0.5 + 0.06), EAVES - 0.08,
                         HALL_CZ + sz * HALL_D * 0.5)
            g.add(kn)

    # Two stacks. A guild hall has hearths and a roofline with no stack on it
    # reads as a model kit. They clear the ridge — a stack short of the ridge
    # is a build-time occlusion failure and has been caught here before.
    for i, cx in enumerate((-4.60, 5.10)):
        ch_h = roof.ridge_y - EAVES + 1.9 + i * 0.3
        ch = K.chimney(f"{ASSET}.stack{i}", height=ch_h, section=0.92)
        ch.translate(cx, EAVES - 0.30, HALL_CZ + (0.9 if i else -0.9))
        g.add(ch)
        SITE.entity(f"{ASSET}.chimney.{i + 1:02d}", "prop.chimney",
                    (cx, EAVES - 0.30 + ch_h, HALL_CZ + (0.9 if i else -0.9)),
                    smoke={"rate": 0.55, "drift": [0.8, 0, 0.5]})
    return roof.ridge_y


def _interior(ctx, g, rng):
    """What the player sees through the open doors.

    WORLD_BIBLE: "stone hall, reception counter, a big map, weapon racks." It
    is a shopfront, not a level: everything here is placed on the sight-line
    from the threshold and nothing is modelled that cannot be seen from it.
    """
    fy = PLAT + 0.02
    # Floor: flags, with the route from the door to the counter walked pale.
    fl = SI.slab(SI.rect(0.0, HALL_CZ, HALL_W - WALL_T * 2, HALL_D - WALL_T * 2),
                 PLAT - 0.06, fy, "sett", 0.012)
    g.add(fl)
    for i, (wx, wz, sz) in enumerate(((PORCH_X, HALL_Z0 + 1.7, 2.6),
                                      (PORCH_X - 1.2, HALL_Z0 + 5.0, 2.0))):
        g.add(P.worn_patch(f"{ASSET}.iw{i}", shape="path", size=sz, mat="sett")
              .translate(wx, fy + 0.010, wz))

    # RECEPTION COUNTER, square on the door axis, so it is the first thing
    # framed by the opening.
    cz = HALL_Z0 + 5.10
    top = M.box(4.40, 0.14, 0.86, 0.014, "oak_dark")
    top.translate(PORCH_X, fy + 1.06, cz)
    g.add(top)
    front = M.box(4.20, 1.00, 0.20, 0.012, "oak_weathered")
    front.translate(PORCH_X, fy + 0.50, cz - 0.32)
    g.add(front)
    for sx in (-1, 1):
        leg = M.box(0.22, 1.00, 0.72, 0.012, "oak_dark")
        leg.translate(PORCH_X + sx * 2.06, fy + 0.50, cz)
        g.add(leg)
    g.add(P.counting_board(f"{ASSET}.tally").translate(PORCH_X + 1.30, fy + 1.13, cz))
    g.add(P.hanging_scales(f"{ASSET}.scales", span=0.72, drop=0.52, reach=0.0)
          .translate(PORCH_X - 1.55, fy + 2.60, cz + 0.10))
    for i in range(3):
        bk = P.crate(f"{ASSET}.ledger{i}", size=0.34, height=0.10, lid=True)
        bk.rotate_y(rng.uniform(-0.2, 0.2))
        bk.translate(PORCH_X - 0.65 + i * 0.06, fy + 1.13 + i * 0.10, cz + 0.12)
        g.add(bk)
    SITE.entity(f"{ASSET}.counter.01", "vendor.guild",
                (PORCH_X, fy + 1.10, cz - 0.60), verbs=["talk"])
    SITE.collider("box", center=(PORCH_X, fy + 0.55, cz),
                  half=(2.20, 0.55, 0.45), tag="counter")

    # THE BIG MAP, on the back wall behind the counter, where the doorway
    # frames it. Pictorial only: coastline, river, hills and pins — no names.
    mz = HALL_Z1 - WALL_T - 0.06
    bd = M.box(4.60, 2.90, 0.10, 0.012, "parchment")
    bd.translate(PORCH_X - 0.40, fy + 2.55, mz)
    g.add(bd)
    for sy in (-1, 1):
        rl = M.cylinder(0.075, 4.80, 8, 0.006, "oak_dark")
        rl.rotate_z(np.pi * 0.5)
        rl.translate(PORCH_X - 0.40 + 2.40, fy + 2.55 + sy * 1.50, mz - 0.03)
        g.add(rl)
    rng2 = rng_for(ASSET, "map")
    for i in range(6):                      # the pins, in a wandering line
        px = -1.9 + i * 0.66 + rng2.uniform(-0.10, 0.10)
        py = 0.30 * math.sin(i * 0.9) + rng2.uniform(-0.25, 0.25)
        pin = M.lathe([(0.014, 0), (0.020, 0.008), (0.010, 0.018)], 6,
                      "iron" if i % 3 else "brass")
        pin.rotate_x(-np.pi * 0.5)
        pin.translate(PORCH_X - 0.40 + px, fy + 2.55 + py, mz - 0.075)
        g.add(pin)
    for i in range(3):                      # the river, as a painted band
        rv = M.box(1.60, 0.055, 0.008, 0.0, "steel_blued")
        rv.rotate_z(0.12 - i * 0.16)
        rv.translate(PORCH_X - 1.60 + i * 1.45, fy + 2.10 + i * 0.18, mz - 0.058)
        g.add(rv)
    SITE.entity(f"{ASSET}.map.01", "prop.guild_map",
                (PORCH_X - 0.40, fy + 2.55, mz - 0.12), verbs=["inspect"])

    # WEAPON RACKS down both side walls, half empty — people took their gear
    # out. The gap is the residue: a full rack means nobody is working.
    for sx in (-1, 1):
        rx = sx * (HALL_W * 0.5 - WALL_T - 0.34)
        for k, rz in enumerate((HALL_Z0 + 3.9,)):
            rack = M.Group()
            for sxx in (-1, 1):
                p = M.box(0.13, 2.05, 0.13, 0.010, "oak_dark")
                p.translate(sxx * 1.35, 1.02, 0)
                rack.add(p)
            for yy in (0.80, 1.78):
                r = M.plank(2.80, 0.11, 0.09, 0.006, "oak_dark")
                r.translate(0, yy, 0)
                rack.add(r)
            for i in range(6):
                if i == (2 + k) % 6:
                    continue              # somebody is out on a job
                wx = -1.10 + i * 0.44
                shaft = M.cylinder(0.030, rng.uniform(1.80, 2.10), 7, 0.004,
                                   "oak_weathered")
                shaft.rotate_z(rng.uniform(0.07, 0.15))
                shaft.translate(wx, 0, rng.uniform(-0.03, 0.03))
                rack.add(shaft)
                if i % 2:
                    hd = M.chamfered_prism([(0, 0), (0.12, 0.18), (0.0, 0.38),
                                            (-0.09, 0.16)], 0.035, "steel_blued",
                                           0.004)
                    hd.translate(wx + 0.22, 1.86, 0)
                    rack.add(hd)
            rack.rotate_y(sx * np.pi * 0.5)
            rack.translate(rx, fy, rz)
            g.add(rack)

    # A hearth on the back wall throwing warm light into the hall, so the
    # doorway reads as an opening into somewhere lit rather than into a hole.
    hx = PORCH_X + 4.30
    hearth = M.chamfered_prism([(-1.10, 0.0), (1.10, 0.0), (1.10, 1.55),
                                (0.72, 1.90), (-0.72, 1.90), (-1.10, 1.55)],
                               0.62, "ashlar", 0.020)
    hearth.translate(hx, fy, HALL_Z1 - WALL_T - 0.30)
    g.add(hearth)
    for i in range(16):
        a = rng.uniform(0, 6.283)
        d = rng.uniform(0.0, 0.44) ** 0.7
        c = M.box(rng.uniform(0.07, 0.15), rng.uniform(0.05, 0.10),
                  rng.uniform(0.07, 0.13), 0.012, "coal")
        c.rotate_y(rng.uniform(0, 3.14))
        c.translate(hx + math.cos(a) * d, fy + 0.10 + rng.uniform(-0.01, 0.03),
                    HALL_Z1 - WALL_T - 0.62 + math.sin(a) * d * 0.5)
        g.add(c)
    SITE.entity(f"{ASSET}.hearth.01", "prop.hearth", (hx, fy + 0.30,
                                                      HALL_Z1 - WALL_T - 0.62),
                light={"color": "#FF9A4C", "intensity": 2.6, "range": 11.0,
                       "flickerHz": [6, 9]})

    # Somebody's chair pulled up to the fire with their cloak over the back.
    # The long table that used to stand down the middle of the hall was 5,000
    # triangles standing where the doorway's own reveal occludes it — the
    # counter, the map and the racks are the three things the opening actually
    # frames, and §7 is explicit that the residue you can SEE is the residue
    # that pays.
    g.add(P.chair(f"{ASSET}.chair", cloak=True)
          .translate(PORCH_X + 3.10, fy, HALL_Z1 - WALL_T - 1.55))


def _forecourt(ctx, g, rng):
    """VISIBLE WORK, and all of it inside the plot this time.

    The v1 guild's identity came from an 8 m training yard, and on this slot
    that yard stood in Ford Road — the module says so and declares no collision
    for it, which is a confession rather than a fix. The forecourt is 9 x 4.4 m
    and it carries the same read at a quarter of the footprint: two pells, a
    rack, a muster bell and the gear people dumped when they came off a job.
    """
    y = PLAT

    # Two pells, hacked to splinters. One is newer than the other, because they
    # get replaced one at a time.
    for i, (px, pz, hgt) in enumerate(((6.10, -5.90, 1.78), (7.05, -4.20, 1.62))):
        pell = M.cylinder(0.19, hgt, 10, 0.014, "oak_weathered" if i else "oak")
        pell.rotate_z(rng.uniform(-0.05, 0.05))
        pell.translate(px, y, pz)
        g.add(pell)
        pad = M.box(0.68, 0.10, 0.68, 0.016, "ashlar_civic")
        pad.translate(px, y + 0.05, pz)
        g.add(pad)
        for k in range(int(rng.integers(4, 8))):
            a = rng.uniform(0, 6.283)
            ch = M.box(rng.uniform(0.05, 0.13), rng.uniform(0.03, 0.08), 0.10,
                       0.006, "oak_dark")
            ch.rotate_y(a)
            ch.translate(px + math.cos(a) * 0.18, y + rng.uniform(0.85, 1.55),
                         pz + math.sin(a) * 0.18)
            g.add(ch)
        SITE.collider("cylinder", center=(px, y + hgt * 0.5, pz), radius=0.24,
                      height=hgt, tag="pell")
    g.add(P.worn_patch(f"{ASSET}.pellworn", shape="cat", size=2.6, mat="sett")
          .translate(6.60, y + 0.022, -5.10))

    # Weapon rack against the hall front, where it is seen from the street.
    rack = M.Group()
    for sxx in (-1, 1):
        p_ = M.box(0.13, 1.78, 0.13, 0.010, "oak_dark")
        p_.translate(sxx * 1.30, 0.89, 0)
        rack.add(p_)
    for yy in (0.68, 1.56):
        r_ = M.plank(2.70, 0.11, 0.09, 0.006, "oak_dark")
        r_.translate(0, yy, 0)
        rack.add(r_)
    for i in range(6):
        if i == 3:
            continue
        wx = -1.10 + i * 0.44
        shaft = M.cylinder(0.030, rng.uniform(1.80, 2.10), 7, 0.004,
                           "oak_weathered")
        shaft.rotate_z(rng.uniform(0.07, 0.15))
        shaft.translate(wx, 0, rng.uniform(-0.03, 0.03))
        rack.add(shaft)
        if i % 2:
            hd = M.chamfered_prism([(0, 0), (0.12, 0.18), (0.0, 0.38),
                                    (-0.09, 0.16)], 0.035, "steel_blued", 0.004)
            hd.translate(wx + 0.22, 1.86, 0)
            rack.add(hd)
    rack.rotate_y(-0.10)
    rack.translate(1.70, y, HALL_Z0 - 0.55)
    g.add(rack)
    SITE.collider("box", center=(1.70, y + 0.95, HALL_Z0 - 0.55),
                  half=(1.45, 0.95, 0.22), rot_y=-0.10, tag="rack")
    SITE.entity(f"{ASSET}.rack.01", "prop.weapon_rack",
                (1.70, y + 0.95, HALL_Z0 - 0.55), verbs=["use"],
                crafting_station={"profession": "combat", "tier": 1})

    # The muster bell on a post, which is how a guild of this size actually
    # calls a party in. Seized half-open, because it is rung twice a year.
    bx, bz = 7.25, -6.55
    po = M.box(0.22, 2.85, 0.22, 0.016, "oak_weathered")
    po.translate(bx, y + 1.42, bz)
    g.add(po)
    arm = M.box(0.70, 0.14, 0.14, 0.010, "oak_dark")
    arm.translate(bx - 0.30, y + 2.72, bz)
    g.add(arm)
    bell = M.lathe([(0.0, 0.52), (0.075, 0.50), (0.10, 0.36), (0.155, 0.14),
                    (0.235, 0.03), (0.255, 0.0), (0.20, 0.0)], 12, "bronze")
    bell.rotate_x(np.pi)
    bell.translate(bx - 0.58, y + 2.66, bz)
    g.add(bell)
    g.add(K.forged_chain(f"{ASSET}.bellrope", (bx - 0.58, y + 2.14, bz),
                         (bx - 0.50, y + 1.15, bz + 0.05), sag=0.10, link=0.05,
                         mat="iron_pitted"))
    SITE.collider("cylinder", center=(bx, y + 1.42, bz), radius=0.20,
                  height=2.85, tag="bell_post")
    SITE.entity(f"{ASSET}.bell.01", "prop.muster_bell", (bx, y + 2.60, bz),
                verbs=["use"])

    # RESIDUE (Art Bible §7): what a party leaves on the steps when it comes in
    # off the road. This buys more life than another ten thousand triangles.
    g.add(K.sack(f"{ASSET}.pack", height=0.52).translate(0.55, y, HALL_Z0 - 1.35))
    roll = M.lathe([(0.14, 0), (0.15, 0.66)], 10, "cloth_brown")
    roll.rotate_z(np.pi * 0.5)
    roll.rotate_y(0.45)
    roll.translate(1.35, y + 0.15, HALL_Z0 - 1.42)
    g.add(roll)
    for i in range(2):
        boot = M.lathe([(0.058, 0), (0.065, 0.17), (0.052, 0.24)], 8,
                       "oak_weathered")
        boot.rotate_z(rng.uniform(-0.28, 0.28))
        boot.translate(PORCH_X - 2.35 + i * 0.19, y,
                       HALL_Z0 - 0.95 + rng.uniform(-0.06, 0.06))
        g.add(boot)
    g.add(P.crate_stack(f"{ASSET}.crates", count=2)
          .translate(-0.30, y, -4.55))
    g.add(P.spill(f"{ASSET}.mud", kind="grain", radius=1.20, density=0.5,
                  centre=(4.20, -6.20), vessel=False).translate(0, y, 0))
    g.add(P.broom(f"{ASSET}.broom", wall_z=HALL_Z0 - 0.14, x=-1.30)
          .translate(0, y, 0))
    g.add(S.boot_scraper(f"{ASSET}.scraper")
          .translate(PORCH_X - 2.90, y, HALL_Z0 - 0.72))


# ---------------------------------------------------------------------------

def build(ctx: VenueContext, asset_id=ASSET):
    SITE.bind(ctx)
    rng = rng_for(asset_id, "guild")
    g = M.Group()

    _stylobate(ctx, g, rng)
    _hall(ctx, g, rng)
    _porch_and_doors(ctx, g, rng)
    ridge = _roof(ctx, g, rng)
    _interior(ctx, g, rng)
    _tower(ctx, g, rng)
    _forecourt(ctx, g, rng)

    SITE.emit(g, container="guild")

    print(SITE.report())
    print(f"      hall {HALL_W:g}x{HALL_D:g} eaves {EAVES:.2f} ridge {ridge:.2f}  "
          f"tower {TW_W:g}x{TW_W:g} parapet {TW_PARAPET:.2f} tip {TW_TIP:.2f}")
