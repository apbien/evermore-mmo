"""The modular building system: 70-90 of Hearthmere's masses come out of here.

A building is assembled from a **footprint polygon in world coordinates**, a
storey count and a seeded style record. Everything else is derived:

    ground      terrain.pad_level() where the slot has a graded pad, otherwise
                terrain.height() sampled over the footprint. Never 0, never a
                Y read out of hearthmere.json (D-022).
    plinth      spans from the floor down to the LOWEST ground under the
                perimeter, so a building on a slope grows an underbuilding
                instead of floating or gapping at the base.
    walls       one run per footprint edge per jetty band, with real apertures
    plate       the wall head returns a `roof.Plate` — polygon plus bearing Y
    roof        `roof.roof_from_plate(plate, ...)`. There is no code path in
                this module or in `core/roof.py` that positions a roof by a
                literal offset; see that module's header for why that matters.
    chimneys    sized by querying the roof surface they pass through
    collision   one wall run per edge, doorways left open, steps to the door

Party walls are first-class. Two slots whose footprint edges touch form a
terrace: the shared wall is built ONCE, in masonry, running up past both
ridges with a coping — which is both how a real street is built and what makes
a row read as urban rather than as detached models standing in a line.

Public API (other venue modules code against this — keep it stable):

    build_building(ctx, slot, style, asset_id) -> Group
    plan_building(slot, style, asset_id)       -> dict   (pure; no geometry)
    wall_plate(footprint, eaves_y)             -> Plate  (from core.roof)
    roof_from_plate(plate, kind, pitch, overhang, asset_id) -> Group
    STYLES                                     -> named style records
"""

from __future__ import annotations

import json
import math
import os

import numpy as np

from . import mesh as M
from . import kit as K
from . import roof as R
from . import terrain as T
from . import batch as B
from . import collision as COL
from .mathx import rng_for, seed_from, jitter
from .roof import Plate, wall_plate, roof_from_plate, is_thatch  # noqa: F401
from . import materials as MATS

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
# Read for `districts[]` only — the roofscape is dealt by district (see
# DISTRICT_ROOFING). Everything else this module needs about a slot arrives in
# the slot record itself.
TOWN_JSON = os.path.join(REPO, "content/town/hearthmere.json")

# Art Bible §3 — never re-derive these locally.
FLOOR_H = K.FLOOR_H
DOOR_W, DOOR_H = K.DOOR_W, K.DOOR_H
SILL_H = K.SILL_H
CHAMFER = K.CHAMFER_ARCH

WALL_T = 0.30           # nominal wall thickness, outer face to inner face
PLINTH_MIN = 0.34       # every building in this town stands out of the wet
FREEBOARD = 0.06        # floor above the highest ground under the footprint

# Head height below which an outshut is not a space. 0.9 m was a clearance,
# not a room: it let `plan_building` solve catslide runs that produced 1.28 m
# under the slope on eleven of thirteen, nine of them below the player's own
# 1.62 m eye. A lean-to a player cannot stand in is a mass with nothing under
# it wearing a carpentry term. 2.05 m is Art Bible §3's 2.10 m door opening
# less the sill — the smallest opening the town admits anywhere.
OUTSHUT_MIN_H = 2.05

# A shared wall beds this far into each neighbour, and its coping stands this
# far proud of both roofs. See `_party_wall`.
PARTY_BEARING = 0.20
PARTY_PROUD = 0.20

# Art Bible §7: no wall of undifferentiated facade longer than this without a
# break. A run over it is split into bays by `_bay_split`.
BAY_MAX = 12.0


# ---------------------------------------------------------------------------
# Footprint
# ---------------------------------------------------------------------------

class Footprint:
    """A plot in world coordinates, with the local frame the schedule implies.

    docs/TOWN_PLAN.md §6: a plot is `w x d` centred on `centre`, rotated so the
    principal facade points along `faces`, where forward = `(sin θ, 0, -cos θ)`.
    So local **+X runs along the frontage**, local **-Z is out of the front
    door**, and `world = rot_y(-θ) * local + centre` — the same convention as
    `Mesh.rotate_y` and `collision.rot_xz`, which is why colliders and geometry
    cannot drift apart here.

    The polygon is the OUTER FACE of the walls. Wall centrelines are inset by
    half the wall thickness; eaves oversail is measured from this face.
    """

    __slots__ = ("polygon", "centre", "theta", "w", "d", "U", "V", "_local")

    def __init__(self, polygon, centre, rotation_deg, w=None, d=None):
        self.polygon = [(float(p[0]), float(p[1])) for p in polygon]
        self.centre = (float(centre[0]), float(centre[1]))
        self.theta = math.radians(float(rotation_deg))
        c, s = math.cos(self.theta), math.sin(self.theta)
        # local (a, b) -> world:  a along U, b along V, front at b = -d/2
        self.U = (c, s)
        self.V = (-s, c)
        loc = [self.local(*p) for p in self.polygon]
        a0, a1 = min(a for a, _b in loc), max(a for a, _b in loc)
        b0, b1 = min(b for _a, b in loc), max(b for _a, b in loc)
        # Recentre on the polygon rather than trusting the authored centre.
        # TOWN_PLAN §6 is explicit that the polygon wins ("use those rather
        # than recomputing, so a rounding difference cannot put a wall 40 mm
        # into a neighbour") — and a party wall is exactly where 40 mm shows.
        off = self.world((a0 + a1) * 0.5, (b0 + b1) * 0.5)
        self.centre = (float(off[0]), float(off[1]))
        self._local = [self.local(*p) for p in self.polygon]
        self.w = float(a1 - a0)
        self.d = float(b1 - b0)

    # -- frame --------------------------------------------------------------

    def world(self, a, b):
        return (self.centre[0] + self.U[0] * a + self.V[0] * b,
                self.centre[1] + self.U[1] * a + self.V[1] * b)

    def local(self, x, z):
        dx, dz = x - self.centre[0], z - self.centre[1]
        return (self.U[0] * dx + self.U[1] * dz, self.V[0] * dx + self.V[1] * dz)

    @property
    def half(self):
        return self.w * 0.5, self.d * 0.5

    def rect(self, front=0.0, back=0.0, left=0.0, right=0.0):
        """The footprint grown outward on selected sides — how a jetty
        oversails, and how a lean-to claims its ground."""
        hw, hd = self.half
        a0, a1 = -hw - left, hw + right
        b0, b1 = -hd - front, hd + back
        return [self.world(a0, b0), self.world(a1, b0),
                self.world(a1, b1), self.world(a0, b1)]

    def corners(self):
        return self.rect()

    def edge_dirs(self):
        """(index, outward normal) per edge of `rect()`, in local terms:
        0 = front (-b), 1 = right (+a), 2 = back (+b), 3 = left (-a)."""
        return [(0, (-self.V[0], -self.V[1])), (1, (self.U[0], self.U[1])),
                (2, (self.V[0], self.V[1])), (3, (-self.U[0], -self.U[1]))]

    # -- ground -------------------------------------------------------------

    def ground_samples(self, n=5, margin=0.0):
        """Terrain heights over the footprint, on a lattice plus the corners."""
        hw, hd = self.half
        hw += margin
        hd += margin
        xs, zs = [], []
        for i in range(n):
            for j in range(n):
                a = -hw + 2 * hw * i / (n - 1)
                b = -hd + 2 * hd * j / (n - 1)
                x, z = self.world(a, b)
                xs.append(x)
                zs.append(z)
        return np.asarray(T.height(np.asarray(xs), np.asarray(zs)), float)


def cell_of(x, z, size=16.0, cols=12):
    """Grid cell for a world position. Directive §2: cell letter index =
    floor(x/16) + 6, and row 1 is the northernmost."""
    ci = int(math.floor(float(x) / size)) + cols // 2
    ri = int(math.floor(float(z) / size)) + cols // 2 + 1
    ci = max(0, min(cols - 1, ci))
    ri = max(1, min(cols, ri))
    return f"{chr(ord('A') + ci)}{ri}"


def footprint_from_slot(slot):
    fp = slot.get("footprint") or {}
    return Footprint(slot["polygon"], slot["centre"], slot.get("rotationDeg", 0.0),
                     fp.get("w"), fp.get("d"))


# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------
#
# A style record is data, not code: it is the whole difference between a
# merchant's townhouse and a byre, and keeping it declarative is what lets 63
# buildings be seeded variations rather than 63 special cases.
#
#   walls        wall build-up per band, coarsest first; last entry repeats
#   frame        timber framing pattern (kit.timber_frame_wall styles)
#   roof         roof kind for core.roof
#   roof_mat     covering; "thatch" switches the roof to mass construction
#   pitch        (lo, hi) — seeded per building
#   jetty        upper-floor oversail in metres, 0 for none
#   plinth       (lo, hi) stone base height
#   windows      (per storey per 10 m of frontage) density
#   wealth       0..1 — drives glazing, mouldings, dressed stone, sign
#
STYLES = {
    "merchant_townhouse": dict(
        walls=["rubble", "timber"], frame="close", roof="gable",
        roof_mat="terracotta", pitch=(0.86, 1.02), jetty=0.42,
        plinth=(0.40, 0.55), windows=2.6, wealth=0.8, dormers=(0, 2),
        chimneys=2, shutters=True, sign=False, storey_h=(2.95, 3.25)),
    "artisan_workshop": dict(
        walls=["rubble", "timber"], frame="square", roof="gable",
        roof_mat="terracotta", pitch=(0.82, 0.96), jetty=0.28,
        plinth=(0.36, 0.48), windows=2.2, wealth=0.5, dormers=(0, 1),
        chimneys=1, shutters=True, shopfront=True, sign=True,
        storey_h=(2.85, 3.15)),
    "shopfront_terrace": dict(
        walls=["rubble", "timber"], frame="herring", roof="gable",
        roof_mat="terracotta", pitch=(0.90, 1.06), jetty=0.38,
        plinth=(0.34, 0.44), windows=2.8, wealth=0.7, dormers=(0, 2),
        chimneys=1, shutters=True, shopfront=True, sign=True,
        storey_h=(2.90, 3.20)),
    "cottage_tile": dict(
        walls=["timber"], frame="square", roof="gable",
        roof_mat="terracotta", pitch=(0.80, 0.94), jetty=0.0,
        plinth=(0.34, 0.46), windows=1.8, wealth=0.3, dormers=(0, 1),
        chimneys=1, shutters=True, storey_h=(2.75, 3.05)),
    "cottage_thatch": dict(
        walls=["timber"], frame="cross", roof="half_hip",
        roof_mat="thatch", pitch=(1.00, 1.16), jetty=0.0,
        plinth=(0.34, 0.46), windows=1.5, wealth=0.25, dormers=(0, 1),
        chimneys=1, shutters=True, storey_h=(2.70, 3.00)),
    "almshouse_row": dict(
        # chimneys=1 is PER DWELLING; `plan_building` multiplies it by the door
        # count. It was 0, so six almshouses shared no hearth at all — six
        # dwellings and not one flue, which is both impossible and the reason
        # the row had no silhouette above its ridge.
        walls=["rubble"], frame="square", roof="gable",
        roof_mat="terracotta", pitch=(0.78, 0.88), jetty=0.0,
        plinth=(0.34, 0.42), windows=2.0, wealth=0.35, dormers=(0, 0),
        chimneys=1, shutters=True, storey_h=(2.70, 2.95)),
    "stone_civic": dict(
        walls=["ashlar"], frame="square", roof="hip",
        roof_mat="slate", pitch=(0.92, 1.05), jetty=0.0,
        plinth=(0.45, 0.60), windows=2.4, wealth=1.0, dormers=(0, 2),
        chimneys=2, shutters=False, storey_h=(3.05, 3.30)),
    "waterfront_warehouse": dict(
        walls=["rubble", "timber"], frame="square", roof="gable",
        roof_mat="terracotta", pitch=(0.74, 0.88), jetty=0.0,
        plinth=(0.36, 0.50), windows=0.9, wealth=0.4, dormers=(0, 0),
        chimneys=0, shutters=False, loading_door=True, storey_h=(3.10, 3.60)),
    "back_lane_shed": dict(
        walls=["timber"], frame="square", roof="gable",
        roof_mat="terracotta", pitch=(0.66, 0.82), jetty=0.0,
        plinth=(0.20, 0.30), windows=0.5, wealth=0.1, dormers=(0, 0),
        chimneys=0, shutters=False, rough=True, storey_h=(2.40, 2.90)),
    "byre": dict(
        walls=["rubble", "timber"], frame="square", roof="catslide",
        roof_mat="terracotta", pitch=(0.72, 0.86), jetty=0.0,
        plinth=(0.28, 0.40), windows=0.6, wealth=0.15, dormers=(0, 0),
        chimneys=0, shutters=False, rough=True, storey_h=(2.60, 3.00)),
}

# Which style a building-schedule `kit` reaches for by default.
KIT_STYLE = {
    "townhouse": "merchant_townhouse",
    "cottage": "cottage_tile",
    "workshop": "artisan_workshop",
    "shed": "back_lane_shed",
    "warehouse": "waterfront_warehouse",
    "shop_row": "shopfront_terrace",
}

WALL_MAT = {
    "timber": ("plaster", "oak"),
    "rubble": ("rubble", "oak_dark"),
    "ashlar": ("ashlar", "oak_dark"),
    "brick": ("brick", "oak_dark"),
    "plastered": ("plaster", "oak_dark"),
    "limewash": ("limewash", "oak_dark"),
}


def style_for(slot, override=None):
    """Resolve a style record for a slot, honouring the brief in `note`.

    The building schedule's notes are the design; reading them is cheaper than
    re-authoring the same intent as parameters, and it keeps the plan and the
    geometry from drifting.
    """
    if isinstance(override, dict):
        return dict(override)
    name = override or KIT_STYLE.get(slot.get("kit"), "cottage_tile")
    note = (slot.get("note") or "").lower()
    if name == "cottage_tile" and "thatch" in note:
        name = "cottage_thatch"
    if slot.get("kit") == "townhouse" and "almshouse" in note:
        name = "almshouse_row"
    st = dict(STYLES[name])
    st["name"] = name
    return st


# Roof forms a style may build, dealt by seed. A town of 63 plain gables is
# monotonous and Art Bible §6 forbids it; a town where every cottage has a
# different roof is a pattern book. These are the forms that actually coexist
# in one settlement, weighted by how common they are.
ROOFS = {
    "merchant_townhouse": ("gable", "gable", "gable", "half_hip", "hip"),
    "shopfront_terrace": ("gable", "gable", "half_hip"),
    "artisan_workshop": ("gable", "gable", "catslide"),
    "cottage_tile": ("gable", "gable", "gable", "half_hip", "catslide"),
    "cottage_thatch": ("half_hip", "hip"),
    "almshouse_row": ("gable",),
    "stone_civic": ("hip", "gable"),
    "waterfront_warehouse": ("gable", "gable", "half_hip"),
    "back_lane_shed": ("gable", "gable", "lean_to", "catslide"),
    "byre": ("catslide", "lean_to"),
}

# Coverings a style may be roofed in, dealt by seed exactly as ROOFS is.
#
# `roof_mat` used to be one scalar per style, and because `stone_civic` is
# never instantiated and `cottage_thatch` is only reached by a note, 62 of the
# 63 buildings came out in the identical terracotta. From the air the town read
# as one material; Art Bible §4 asks for roughly 30% aged covering and the
# art-director pass rejected on it. What a real settlement of this size has:
# tile is the standard and the townhouses can afford it, the poor and the
# outbuildings still keep thatch, and only the civic hand reaches slate or lead.
# Weight by repeating an entry, so the deal stays readable as a proportion.
ROOF_MATS = {
    "merchant_townhouse": ("terracotta",) * 6 + ("slate",) * 2 + ("thatch_old",),
    "shopfront_terrace": ("terracotta",) * 6 + ("slate",),
    "artisan_workshop": ("terracotta",) * 5 + ("slate",) + ("thatch_old",) * 2,
    # Slate added, and it is not decoration: without it a cottage cannot join a
    # block that re-roofed in slate, and `roof_covering` below has nothing to
    # cluster with in the two districts that can afford it.
    "cottage_tile": ("terracotta",) * 4 + ("slate",) + ("thatch_old",) * 3 + ("thatch_new",),
    "cottage_thatch": ("thatch",) * 2 + ("thatch_old",) * 3 + ("thatch_new",),
    "almshouse_row": ("terracotta",) * 2 + ("slate",) + ("thatch_old",) * 3,
    "stone_civic": ("slate",) * 3 + ("lead",),
    "waterfront_warehouse": ("terracotta",) * 3 + ("slate",) * 2,
    "back_lane_shed": ("thatch_old",) * 4 + ("terracotta",) * 2 + ("thatch_new",),
    "byre": ("thatch_old",) * 4 + ("thatch",) * 2 + ("terracotta",),
}


# ---------------------------------------------------------------------------
# Roofing by district, wealth and block
# ---------------------------------------------------------------------------
#
# `review/reports/ad-town-02.md` §21: "roughly 55-60 roofs, of which the great
# majority are one saturated orange terracotta, scattered evenly among pale and
# a handful of saturated blue. There is no clustering logic — no sense that one
# street re-roofed after a fire, or that the poor quarter is thatched and the
# merchants' slated. A real town's roofscape has runs and blocks."
#
# The tables above are per STYLE, and a per-style deal is by construction a
# dither: two neighbours of the same style are two independent rolls, so the
# aerial reads as noise no matter how good the individual weights are. What a
# roofscape actually records is history, and history is shared — a district is
# rich or poor together, a fire takes a whole lane, a lord re-roofs his own
# quarter in one season.
#
# So the covering is dealt in three stages:
#
#   1. DISTRICT   `content/town/hearthmere.json:districts[]` already divides the
#                 town by economic cause, so the roofing weights hang off that
#                 rather than off a new invented map. Two of them are not
#                 taste but LAW: the Fire Lane holds the ovens, the tallow and
#                 the charcoal and its own brief says it is "separated from the
#                 thatch of the west lanes by the whole width of Ford Road";
#                 Smithward's says "furthest from thatch". Neither may be
#                 thatched at all, and that single rule is most of what makes
#                 the aerial read as a settlement with a fire history.
#   2. BLOCK      within a district, the covering is drawn ONCE per block and
#                 every building in that block takes it. This is the run: a
#                 terrace re-roofs together. A BLOCK IS A REAL TERRACE, not a
#                 lattice cell — see ROOF_BLOCK_KEY.
#   3. THE ODD    one building in seven ignores its block and takes the style's
#       ONE OUT   own deal, because a real street always has the one house that
#                 did it differently.
#
# The style keeps a veto throughout. A block that went slate does not slate a
# thatch cottage or a byre; a block that went thatch does not thatch a
# warehouse. `ROOF_MATS[style]` IS that veto list, so the two systems cannot
# drift apart — adding a covering to a style is the only way to let a block
# reach it.
DISTRICT_ROOFING = {
    # id           covering, weight
    "market":    (("terracotta", 5), ("slate", 4), ("lead", 1)),
    "knowe":     (("slate", 5), ("terracotta", 3), ("lead", 1)),
    "quayside":  (("terracotta", 4), ("slate", 2), ("thatch_old", 3)),
    "waterside": (("terracotta", 3), ("thatch_old", 4), ("thatch", 2)),
    "fireside":  (("terracotta", 6), ("slate", 2)),
    "smithward": (("terracotta", 5), ("slate", 2)),
    "southgate": (("terracotta", 3), ("thatch_old", 4), ("thatch_new", 1)),
    "westlanes": (("thatch_old", 5), ("thatch", 3), ("terracotta", 2)),
}

# The two that cannot be thatched however rich or poor the block is.
NO_THATCH_DISTRICTS = ("fireside", "smithward")

# A BLOCK IS A QUARTER ON A SHELF. There is no lattice any more.
#
# ad-town-03 §5: "ROOF_BLOCK_M = 26.0 gives about two buildings per block. A
# block of two is indistinguishable from an independent roll." True, and the
# cause is worse than the size: a 26 m square laid over the map cuts ACROSS the
# terraces, so a "block" routinely held two buildings on two different shelves
# with a retaining wall between them. That is not a block in any sense a viewer
# can read, and no amount of enlarging the square fixes it.
#
# Hearthmere falls in seven authored shelves (`terrain.terrace_of`, from
# `pads.list`). A shelf is what was cut, filled and built out in one go, and a
# quarter is who paid for it — so the block is exactly `(district, terrace)`,
# both of which are already authored in content and neither of which this file
# invents. Measured over the town's 94 building slots:
#
#   26 m square lattice          46 blocks, mean 2.04, 48 of 94 masses in a run of 3+
#   42 m square (§5's suggestion) 33 blocks, mean 2.85, 73 of 94
#   48 m square (§5's suggestion) 31 blocks, mean 3.03, 78 of 94
#   district x terrace            26 blocks, mean 3.62, 85 of 94
#
# The largest is Kirk Knowe on the market shelf: ten masses over 46 m of
# frontage, which is a terrace of houses. The one-in-seven odd-one-out and the
# style veto still break the longest runs, which is what stops a run reading as
# one decal.
ROOF_BLOCK_KEY = "(district, terrace)"

_DISTRICT_BOXES = None


def _district_boxes():
    """District cell ranges from content, as world-space AABBs.

    Parsed from `districts[].cells` ("D2-H4"), which is the same string the
    plan document and `docs/TOWN_PLAN.md` publish — so there is one definition
    of where Kirk Knowe is and this is not it.
    """
    global _DISTRICT_BOXES
    if _DISTRICT_BOXES is not None:
        return _DISTRICT_BOXES
    _DISTRICT_BOXES = []
    try:
        with open(TOWN_JSON, encoding="utf-8") as f:
            doc = json.load(f)
    except (OSError, ValueError):
        return _DISTRICT_BOXES
    size = float((doc.get("grid") or {}).get("cellSize") or 16.0)
    cols = len((doc.get("grid") or {}).get("cols") or []) or 12
    half = cols * size / 2.0
    for d in doc.get("districts") or []:
        cells = str(d.get("cells") or "")
        if "-" not in cells:
            continue
        a, b = cells.split("-", 1)
        try:
            c0, r0 = ord(a[0].upper()) - 65, int(a[1:])
            c1, r1 = ord(b[0].upper()) - 65, int(b[1:])
        except (ValueError, IndexError):
            continue
        lo_c, hi_c = min(c0, c1), max(c0, c1)
        lo_r, hi_r = min(r0, r1), max(r0, r1)
        _DISTRICT_BOXES.append((
            d.get("id") or cells,
            -half + lo_c * size, -half + (hi_c + 1) * size,
            -half + (lo_r - 1) * size, -half + hi_r * size))
    return _DISTRICT_BOXES


def district_of(x, z):
    """District id containing a world position, or None outside them all.

    The authored ranges are rectangles and they do not tile the town — the
    intramural ring and the corners between quarters belong to nobody, which is
    correct: those are the odd plots, and a plot that belongs to no district
    falls back to its style's own deal and quietly breaks up the runs.
    """
    for did, x0, x1, z0, z1 in _district_boxes():
        if x0 <= x < x1 and z0 <= z < z1:
            return did
    return None


def wealth_of(slot, st):
    """0 = a back-lane shed, 1 = a three-storey merchant house on the square.

    Read off what the plan already records rather than invented: a slot's role
    in the schedule, how tall it was built, and how much frontage it holds.
    Frontage on the market place is the most expensive thing in Hearthmere
    (`districts[market].cause`), so storeys are the honest proxy for money.
    """
    role = str(slot.get("role") or "filler")
    w = {"hero": 0.85, "secondary": 0.55, "filler": 0.22}.get(role, 0.3)
    storeys = int(slot.get("storeys") or 1)
    w += 0.16 * (storeys - 1)
    if st.get("name") in ("back_lane_shed", "byre"):
        w -= 0.25
    return max(0.0, min(1.0, w))


def roof_covering(slot, st, note, rng, asset_id):
    """The covering this building is roofed in. See DISTRICT_ROOFING above.

    NOTE for whoever next works in this file. This function draws a VARIABLE
    number of times from `rng`, which is the building's own shared stream, so
    every decision taken after it — frame jitter, dormers, prop placement —
    is coupled to how the roof happened to come out. Giving it its own stream
    (`rng_for(asset_id, "covering")`) is the right answer and is a one-line
    change, but it re-rolls the whole kit and the re-roll immediately hits a
    latent crash in the wing planner:

        RuntimeError: roof_from_plate('gable', 'hm.slot.19.workshop_a.wing'):
        every slope was clipped away.

    That is a real defect in `plan_building`'s L/T wing — a wing can be planned
    small enough that its roof clips to nothing — and it wants fixing before the
    stream is separated. Left coupled deliberately rather than shipped broken.
    """
    allowed = ROOF_MATS.get(st["name"], (st["roof_mat"],))

    # A note that names the covering is a brief and outranks everything,
    # including the fire rule — if the schedule says a building in the Fire
    # Lane is thatched, that is a decision someone made and this is not the
    # place to overrule it.
    if "thatch" in note:
        straw = tuple(m for m in allowed if is_thatch(m)) or ("thatch",)
        return straw[int(rng.integers(0, len(straw)))]
    if "slate" in note:
        return "slate"

    cx, cz = float(slot["centre"][0]), float(slot["centre"][1])
    did = district_of(cx, cz)
    weights = DISTRICT_ROOFING.get(did)

    # THE BLOCK, and it is established BEFORE any decision is taken, because
    # every path out of this function has to be able to reach it.
    #
    # ad-town-03 §5 named the mechanism precisely: "three separate paths re-roll
    # per-asset instead of per-block", and a block whose vetoed and substituted
    # members each roll their own covering is not a block. `brng` is seeded from
    # the quarter and the shelf — never from the asset id — so every building
    # standing on the same shelf of the same quarter draws the same number, and
    # so do all of their fallbacks.
    terrace = T.terrace_of(cx, cz) or "natural"
    brng = rng_for(f"roofblock.{did}.{terrace}", "covering")

    def _pick(pool, r):
        """One choice from a tuple. `r` says whether it is the block's or the
        building's — pass `brng` unless the point is to break the run."""
        return pool[int(r.integers(0, len(pool)))] if pool else "terracotta"

    def _no_fire_risk(cov, r=None):
        """The Fire Lane and Smithward are not thatched. Applied to EVERY path
        out of this function, because a fire rule that the odd-one-out roll can
        break is not a rule — and three straw roofs among the ovens is exactly
        what the first version of this shipped.

        The SUBSTITUTE is the block's, not the building's: when a thatch block
        meets the Fire Lane, the whole lane has to come out in the same hard
        covering or the rule reads as random tile instead of as a fire ban."""
        if not (is_thatch(cov) and did in NO_THATCH_DISTRICTS):
            return cov
        hard = tuple(m for m in allowed if not is_thatch(m))
        return _pick(hard, r or brng)

    # One building in seven goes its own way. THIS roll and this pick are the
    # only per-asset ones in the function, and deliberately so — the odd one out
    # exists to break the run, so it is the one thing that must not share it.
    if weights is not None and rng.integers(0, 7) == 0:
        return _no_fire_risk(_pick(allowed, rng), rng)
    # A plot outside every district has no block to join, but its neighbours in
    # the same bay of the same terrace are in the same position, so they still
    # agree with each other rather than dithering one by one.
    if weights is None:
        return _no_fire_risk(_pick(allowed, brng))

    wealth = wealth_of(slot, st)
    pool, total = [], 0.0
    for cov, w in weights:
        if is_thatch(cov) and did in NO_THATCH_DISTRICTS:
            continue
        # Money buys hard covering; poverty keeps the straw on.
        if cov in ("slate", "lead"):
            w *= 0.55 + 1.30 * wealth
        elif is_thatch(cov):
            w *= 1.55 - 1.20 * wealth
        if w <= 0:
            continue
        total += w
        pool.append((cov, total))
    if not pool:
        return _no_fire_risk(_pick(allowed, brng))

    pick = float(brng.random()) * total
    covering = pool[-1][0]
    for cov, acc in pool:
        if pick <= acc:
            covering = cov
            break

    # The style's veto. A thatch cottage in a slated block stays thatch; a
    # warehouse in a thatched lane stays tiled. The SUBSTITUTE is the block's:
    # a vetoed building is still a building in that block, so the four
    # warehouses in a thatched lane should all come out in the same tile, not
    # in four independently rolled ones. This path was the largest single
    # source of the checkerboard, because the veto fires on every style whose
    # ROOF_MATS does not happen to contain the block's covering.
    if covering in allowed:
        return _no_fire_risk(covering)
    if is_thatch(covering):
        alt = tuple(m for m in allowed if is_thatch(m))
        if alt:
            return _no_fire_risk(_pick(alt, brng))
    return _no_fire_risk(_pick(allowed, brng))

# Plan forms, dealt by seed exactly as ROOFS and ROOF_MATS are.
#
# Every one of the 63 masses was a single rectangle, so the roofscape was 63
# parallel ridges and `roof.py`'s `clip_against` — the valley path — was never
# called by anything. These are the forms a real settlement of this size holds,
# and all three are cut from INSIDE the authored plot polygon rather than being
# added to it: the main range gives up depth to pay for the wing. A wing that
# grew outward would be a mass straying past its own plot, which is the defect
# the town-level overlap check exists to catch.
#
#   rect    one range
#   L       rear wing at one end       — valley both sides of its ridge
#   T       rear wing on the centre    — the same, symmetrical
#   cross   gabled bay on the FRONTAGE — the strongest street-side form there
#           is, and what breaks a long facade in one move
PLAN_FORMS = {
    "merchant_townhouse": ("rect",) * 4 + ("L",) * 3 + ("T",) + ("cross",),
    "shopfront_terrace": ("rect",) * 5 + ("cross",),
    "artisan_workshop": ("rect",) * 3 + ("L",) * 2,
    "cottage_tile": ("rect",) * 6 + ("L",) * 2 + ("T",),
    "cottage_thatch": ("rect",) * 3 + ("L",),
    "almshouse_row": ("cross",),
    "stone_civic": ("rect",) * 2 + ("T",),
    "waterfront_warehouse": ("rect",) * 4 + ("L",),
    "back_lane_shed": ("rect",),
    "byre": ("rect",) * 3 + ("L",),
}

FRAMES = {
    "merchant_townhouse": ("close", "close", "square", "herring"),
    "shopfront_terrace": ("close", "herring", "square"),
    "artisan_workshop": ("square", "cross", "close"),
    "cottage_tile": ("cross", "square", "square", "cross"),
    "cottage_thatch": ("cross", "square"),
    "almshouse_row": ("square",),
    "stone_civic": ("square",),
    "waterfront_warehouse": ("square", "cross"),
    "back_lane_shed": ("square", "cross"),
    "byre": ("square",),
}


# ---------------------------------------------------------------------------
# Planning — pure, no geometry. Party walls and LOD both read this.
# ---------------------------------------------------------------------------

def _sub_footprint(fp, a0, a1, b0, b1):
    """A rectangle of the plot, in the plot's own frame, as a Footprint."""
    poly = [fp.world(a0, b0), fp.world(a1, b0), fp.world(a1, b1), fp.world(a0, b1)]
    centre = fp.world((a0 + a1) * 0.5, (b0 + b1) * 0.5)
    return Footprint(poly, centre, math.degrees(fp.theta))


def _plan_wing(fp, form, ridge_axis, rng):
    """Cut the plot into a main range and a wing. Returns (main_fp, wing).

    The main range is ALWAYS reduced to pay for the wing, so the union of the
    two is the authored plot and nothing strays outside it.

    `wing` carries two rectangles because they are genuinely different things:
    `wall_poly` is where the wing's walls stand, and `plate_poly` runs back
    INTO the main range by `lap`. That lap is not slop — it is what makes the
    wing's roof planes cross the main range's, and the crossing IS the valley.
    Without it the wing's roof merely butts an eaves and `clip_against` has
    nothing to cut.
    """
    hw, hd = fp.half
    if form in ("L", "T"):
        # A wing that projects less than 2.8 m is not a wing: the range's own
        # eaves oversails most of it, so the clip leaves a scrap of roof and
        # the mass reads as a bulge rather than as a second range. Give the
        # main range up as little depth as will do that, then fall through to a
        # cross-gable on a plot too shallow for either.
        wd = max(2.9, fp.d * float(rng.uniform(0.34, 0.42)))
        dm = fp.d - wd
        ww = min(fp.w * float(rng.uniform(0.38, 0.52)), dm * 0.95, 5.6)
        if dm >= 3.8 and ww >= 2.7:
            if form == "T":
                a0 = -ww * 0.5 + float(rng.uniform(-0.25, 0.25)) * (fp.w - ww) * 0.5
            else:
                side = 1.0 if rng.random() < 0.5 else -1.0
                a0 = (hw - ww - 0.35) if side > 0 else (-hw + 0.35)
            a0 = max(-hw + 0.30, min(hw - ww - 0.30, a0))
            lap = min(0.95, ww * 0.30, dm * 0.25)
            main = _sub_footprint(fp, -hw, hw, -hd, -hd + dm)
            wing = dict(form=form,
                        wall=(a0, a0 + ww, -hd + dm, hd),
                        plate=(a0, a0 + ww, -hd + dm - lap, hd),
                        inner=0)
        else:
            form = "cross"
    if form == "cross":
        # A gabled bay on the frontage. Projection is shallow — it is a bay,
        # not a second house — and its ridge runs out to the street. It works
        # on almost any plot, which is what makes it the fallback.
        p = float(rng.uniform(1.15, 1.70))
        ww = min(fp.w * float(rng.uniform(0.30, 0.42)), 5.4)
        if fp.d - p < 4.0 or ww < 2.4 or fp.w < 5.0:
            return fp, None
        a0 = float(rng.uniform(-1.0, 1.0)) * (fp.w - ww) * 0.5
        a0 = max(-hw + 0.5, min(hw - ww - 0.5, a0 - ww * 0.5))
        lap = min(0.95, ww * 0.30)
        main = _sub_footprint(fp, -hw, hw, -hd + p, hd)
        wing = dict(form=form,
                    wall=(a0, a0 + ww, -hd, -hd + p),
                    plate=(a0, a0 + ww, -hd, -hd + p + lap),
                    inner=2)
    # A wing's ridge runs ACROSS the main range's, which is the whole point:
    # two parallel ridges make a bigger rectangle, not an L.
    wing["ridge_axis"] = "v" if ridge_axis == "u" else "u"
    wing["wall_poly"] = [fp.world(wing["wall"][0], wing["wall"][2]),
                         fp.world(wing["wall"][1], wing["wall"][2]),
                         fp.world(wing["wall"][1], wing["wall"][3]),
                         fp.world(wing["wall"][0], wing["wall"][3])]
    wing["plate_poly"] = [fp.world(wing["plate"][0], wing["plate"][2]),
                          fp.world(wing["plate"][1], wing["plate"][2]),
                          fp.world(wing["plate"][1], wing["plate"][3]),
                          fp.world(wing["plate"][0], wing["plate"][3])]
    wing["w"] = wing["wall"][1] - wing["wall"][0]
    wing["d"] = wing["wall"][3] - wing["wall"][2]
    wing["centre"] = fp.world((wing["wall"][0] + wing["wall"][1]) * 0.5,
                              (wing["wall"][2] + wing["wall"][3]) * 0.5)
    wing["theta"] = fp.theta
    # Edge 0 of the plate runs along `a`. `ridge_axis="v"` puts the ridge
    # perpendicular to edge 0, so edges 0 and 2 are the gable ends; "u" is the
    # other way round.
    if wing["ridge_axis"] == "v":
        lbl = ["gable", "eaves", "gable", "eaves"]
    else:
        lbl = ["eaves", "gable", "eaves", "gable"]
    lbl[wing["inner"]] = "abut"
    wing["edges"] = lbl
    return main, wing


def plan_building(slot, style=None, asset_id=None):
    """Every number the building is made of, derived and seeded. No geometry.

    Separated from `build_building` because a terrace has to know its
    neighbour's ridge height before either building exists, and because an LOD
    chain must be four renderings of the SAME building, not four rolls of the
    dice.
    """
    asset_id = asset_id or slot["id"]
    st = style_for(slot, style)
    rng = rng_for(asset_id, "plan")
    fp = footprint_from_slot(slot)
    note = (slot.get("note") or "").lower()

    # -- ground ----------------------------------------------------------
    # D-022: the Y in hearthmere.json is decorative. Take a graded pad if the
    # terrain authors one for this slot, otherwise read the ground.
    pad_id = f"hm.pad.{slot['id'].split('.')[-1]}"
    level = None
    for cand in (f"hm.pad.{slot['id']}", pad_id):
        try:
            level = T.pad_level(cand)
            break
        except KeyError:
            continue
    g = fp.ground_samples(5)
    g_edge = fp.ground_samples(5, margin=0.35)
    if level is None:
        # The floor clears the highest ground the footprint touches; anything
        # less and the uphill corner of the building is buried in the slope.
        level = float(np.percentile(g, 92))
    floor_y = level + FREEBOARD
    ground_lo = float(g_edge.min())
    ground_hi = float(g_edge.max())

    plinth_h = float(rng.uniform(*st["plinth"]))
    # The plinth becomes an underbuilding wherever the ground falls away. This
    # is the whole answer to "a building on a slope never floats and never
    # gaps at the base": the base is defined by the LOW ground, not by a
    # constant.
    base_y = min(floor_y - plinth_h, ground_lo - 0.14)
    plinth_h = floor_y - base_y

    # -- massing ---------------------------------------------------------
    storeys = max(1, int(slot.get("storeys", 1)))
    eaves = float(slot.get("eavesHeight") or (storeys * FLOOR_H + 0.6))
    # The schedule's eaves height is measured from the ground, and the ground
    # is what we just derived; the wall head is what the roof will sit on.
    eaves_h = max(2.2, eaves - plinth_h * 0.35)
    storey_h = min(float(rng.uniform(*st["storey_h"])), eaves_h / storeys)

    frames = FRAMES.get(st["name"], (st["frame"],))
    st["frame"] = frames[int(rng.integers(0, len(frames)))]

    # Covering by district, wealth and block — not one roll per building. See
    # DISTRICT_ROOFING; ad-town-02 §21 is what a per-building roll looks like
    # from the air.
    st["roof_mat"] = roof_covering(slot, st, note, rng, asset_id)

    pitch = float(rng.uniform(*st["pitch"]))
    if is_thatch(st["roof_mat"]):
        # Thatch has to shed water through the depth of the coat, so it is
        # never laid below about 45°. Dealing it onto a style pitched for tile
        # and leaving the pitch alone would build a flat thatch, which reads as
        # a hayrick on a shed. The dedicated thatch style is already steeper
        # than this floor, so it is unaffected.
        pitch = max(pitch, 1.00)
    kinds = ROOFS.get(st["name"], (st["roof"],))
    roof_kind = kinds[int(rng.integers(0, len(kinds)))]
    ridge = slot.get("ridge", "along")
    ridge_axis = "u" if ridge != "gable" else "v"
    if ridge == "flat":
        roof_kind, pitch = "lean_to", 0.22
    if ridge == "cone":
        roof_kind = "pyramid"

    # -- plan form -------------------------------------------------------
    forms = PLAN_FORMS.get(st["name"], ("rect",))
    form = forms[int(rng.integers(0, len(forms)))]
    if min(fp.w, fp.d) < 4.5 or fp.w * fp.d < 34.0 or roof_kind == "lean_to":
        # Below this a wing is a shed with delusions: the main range is left
        # too shallow to roof and the valley is shorter than its own flashing.
        form = "rect"
    wing = None
    if form != "rect":
        fp, wing = _plan_wing(fp, form, ridge_axis, rng)
        if wing is None:
            form = "rect"

    jetty = float(st.get("jetty", 0.0)) if storeys >= 2 else 0.0
    if jetty and min(fp.w, fp.d) < 5.0:
        jetty *= 0.6
    overhang = 0.30 + 0.16 * float(st.get("wealth", 0.4)) + rng.uniform(0.0, 0.08)
    if is_thatch(st["roof_mat"]):
        overhang += 0.18

    # Half the span, measured on the axis the ridge does NOT run along, is what
    # sets the ridge height. Derived here only so a party wall can be built
    # tall enough before its neighbour exists.
    span = fp.d if ridge_axis == "u" else fp.w
    if jetty:
        span += jetty * 2.0
    plate_y = floor_y + eaves_h
    ridge_y = plate_y + pitch * (span * 0.5)

    # A catslide exists BECAUSE there is an outshut under it, so the run is
    # whatever the outshut can carry — solved here, not authored and hoped for.
    # `_outshut` refuses to build below a usable head height and simply returns,
    # and the extended slope then oversails open air: the floating-mass defect
    # wearing a carpentry term, which is what this module's own comment says it
    # exists to prevent. Two sheds shipped exactly that, showing a black roof
    # underside to the square. D-036.
    catslide_run = 0.0
    if roof_kind == "catslide":
        want = min(2.3, fp.d * 0.30)
        # +0.03 of headroom, not 0: solving for exactly OUTSHUT_MIN_H lands the
        # result on the comparison it has to pass, and float error then puts it
        # on the wrong side. Both sheds failed by 1e-16 m.
        room = (eaves_h - pitch * overhang - 0.10 - OUTSHUT_MIN_H - 0.03) / max(pitch, 1e-3)
        catslide_run = min(want, room)
        if catslide_run < 0.8:
            # Not enough wall to get a head under it. A plain gable is the
            # honest answer; a stub catslide is a defect — and on a low-eaved
            # shed that is now most of them, which is the correct outcome:
            # raising the head from 0.9 m to 2.05 m simply proves that a 2.4 m
            # wall cannot carry a lean-to as well as a room.
            roof_kind, catslide_run = "gable", 0.0

    plan = dict(
        id=asset_id, slot=slot["id"], kit=slot.get("kit"), style=st,
        footprint=fp, floor_y=floor_y, base_y=base_y, plinth_h=plinth_h,
        ground_lo=ground_lo, ground_hi=ground_hi, storeys=storeys,
        eaves_h=eaves_h, storey_h=storey_h, plate_y=plate_y, ridge_y=ridge_y,
        pitch=pitch, roof_kind=roof_kind, ridge_axis=ridge_axis, jetty=jetty,
        overhang=overhang, roof_mat=st["roof_mat"], note=note,
        party={}, seed=seed_from(asset_id), form=form, wing=wing,
    )

    # -- what the brief asks for -----------------------------------------
    plan["catslide_run"] = catslide_run
    plan["open_sides"] = "no walls" in note or "open saw shed" in note
    plan["no_door"] = "no door" in note
    plan["doors"] = 6 if "six doors" in note else 1
    if plan["doors"] > 1:
        # Every dwelling has a hearth. A terrace of N front doors is N houses
        # and therefore N flues, and the stacks marching along the ridge are
        # most of what says so from across the square.
        st["chimneys"] = max(1, int(st.get("chimneys", 1))) * plan["doors"]
    plan["loading"] = bool(st.get("loading_door")) or "loading door" in note
    plan["cart_doors"] = "cart doors" in note
    plan["shopfront"] = bool(st.get("shopfront")) or "counter" in note
    plan["lean_to"] = "lean-to" in note or "lean to" in note
    plan["nogging"] = "nogging" in note
    plan["sag"] = "sagging" in note
    plan["shared_stack"] = "sharing a chimney" in note
    return plan


# ---------------------------------------------------------------------------
# Small builders
# ---------------------------------------------------------------------------

def _invert(mesh):
    """Turn a mesh inside out: normals reversed, winding reversed.

    An interior shell has to be invisible from outside and present from within
    — that is exactly a box with its faces turned in. Without one, every window
    aperture in the town looks straight through the building and out the far
    side, which is worse than no aperture at all.
    """
    mesh.n = -mesh.n
    mesh.idx = mesh.idx.reshape(-1, 3)[:, ::-1].reshape(-1).astype(np.uint32)
    return mesh


def _place_run(geom, mid, ex, ez):
    """Put a wall-run built in kit space (centred, along +X, outward -Z) onto
    an edge whose outward normal is `-ez`."""
    return M.place(geom, np.array([mid[0], 0.0, mid[1]]),
                   np.array([ex[0], 0.0, ex[1]]), np.array([0.0, 1.0, 0.0]),
                   np.array([ez[0], 0.0, ez[1]]))


def _edge_frame(a, b, centroid):
    """-> (mid2, ex2, out2, length). `ex` is the run's local +X, `out` the
    outward normal; the pair is right-handed with +Y so a wall built by the kit
    lands the right way round."""
    d = np.asarray(b, float) - np.asarray(a, float)
    ln = float(np.hypot(d[0], d[1]))
    if ln < 1e-6:
        return None
    d = d / ln
    n = np.array([-d[1], d[0]])
    mid = (np.asarray(a, float) + np.asarray(b, float)) * 0.5
    if float(np.dot(mid - np.asarray(centroid, float), n)) < 0:
        n = -n
    ex = np.array([-n[1], n[0]])          # ex x up = -n = ez  (right-handed)
    return mid, ex, n, ln


def masonry_wall(width, height, asset_id, kind="rubble", openings=None,
                 depth=WALL_T, mat=None, quoins=True, detail=0, uv=None):
    """A stone or brick wall with real apertures.

    Shares `kit.subtract_rects` with the timber-framed wall rather than
    reimplementing it, so a window hole is the same hole whatever the wall is
    made of — the alternative is two subtly different apertures in one street.
    """
    rng = rng_for(asset_id, "masonry", kind, round(width, 2))
    mat = mat or WALL_MAT.get(kind, ("stone", "oak_dark"))[0]
    out = M.Group()
    openings = openings or []
    for (rx, ry, rw, rh) in K.subtract_rects(width, height, openings):
        # Slight per-panel depth variance: a rubble wall is not a machined slab
        # and the shadow at each break is what says so.
        t = depth * rng.uniform(0.97, 1.03)
        # `uv` defaults to 1.0, not the 0.5 that matches the material's
        # authored 2 m coverage: at 2 m the rubble field reads as 0.8 m
        # boulders, which is a castle wall, not a house. Tiling every metre
        # puts the stones at 0.35-0.45 m — the size a mason actually lifts —
        # and doubles texel density into the bargain.
        #
        # A castle wall is exactly what the guild tower IS, though, and at 0.4 m
        # the ashlar courses on an 18 m shaft alias into a herringbone moire
        # from 40 m out. So the scale is now a parameter, defaulted to the
        # value every existing caller was already getting. Ashlar on a hero
        # mass wants 0.55; rubble on a cottage still wants 1.0.
        panel = M.box(rw, rh, t, 0.022, mat, uv_scale=uv)
        panel.translate(rx, ry, 0.0)
        out.add(panel)
    if quoins and detail == 0 and kind in ("rubble", "brick") and height > 1.4             and width > 5.0:
        # A string course at first-floor level rather than quoins at the
        # angles. Quoins were tried and pulled: at 0.34 m they sample a
        # fraction of a 2 m ashlar tile, so each one showed two enormous stones
        # and read as a pale panel stuck on the wall. A string is one long run
        # of the same texture, it breaks a tall rubble face the way §7 asks,
        # and it is where the rain actually stops running down.
        band = M.box(width + 0.06, 0.13, depth * 1.12, 0.018, "sandstone")
        band.translate(0.0, min(height - 0.5, 2.72), 0.0)
        out.add(band)
    return out


def wall_run(asset_id, length, height, kind, frame, openings, sill_y=0.0,
             mats=None, detail=0, nogging=False):
    """One wall of one band. Dispatches on the build-up named by the style."""
    if kind == "timber":
        plaster, timber = (mats or WALL_MAT["timber"])
        return K.timber_frame_wall(length, height, asset_id,
                                   style="herring" if nogging else frame,
                                   depth=WALL_T * 0.8, plaster_mat=plaster,
                                   timber_mat=timber, sill_y=sill_y,
                                   openings=openings)
    g = masonry_wall(length, height, asset_id, kind, openings, detail=detail)
    if sill_y:
        g.translate(0, sill_y, 0)
    return g


REVEAL = 0.135          # how far the glass sits back inside the opening


def leaded_light(asset_id, width=0.82, height=1.05, mat="glass", shutters=False,
                 shutter_mat="painted", frame_mat="oak_dark", detail=0):
    """A window unit built for a REVEAL: glass set back in the wall thickness,
    with a projecting stone cill that throws water clear of the face.

    Outward is -Z, matching every other kit piece.

    Three things the art-director pass called out, all of them the difference
    between a window and a card of glass:

    **The glass sits back.** It used to be 35 mm behind the frame face — inside
    the jamb's own depth — so at the gameplay camera the pane, the frame and
    the wall were all one plane and the opening had no shadow in it. It now
    sits `REVEAL` back, and `_reveal` lines the return in the WALL's material,
    where that lining belongs: a reveal is masonry, not joinery, and keeping it
    out of this unit is also what keeps the window prototype count at twelve
    for the whole town instead of one per wall build-up.

    **The cames are geometry.** A painted grid on the albedo has no thickness
    and catches no light. Six lead bars standing 12 mm proud of the pane do,
    and they are the thing that says "hand-blown quarries in lead" rather than
    "a texture of a window".

    **The cill is tiled for a cill.** `stone` at `uv_scale=1.0` puts 0.4 m
    blocks on a 0.075 m thick dressing — the same class of error `masonry_wall`
    already fixed for rubble, never applied to the small dressings. A cill is
    one cut stone; at 5.0 the grain reads as stone rather than as boulders.
    """
    rng = rng_for(asset_id, "light")
    out = M.Group()
    glass = M.box(width, height, 0.025, 0.004, mat)
    glass.translate(0, 0, REVEAL)
    out.add(glass)
    # Lead cames across the pane, standing proud of it. Art Bible §2 permits
    # only small panes in leaded cames, and this is what makes the quarries.
    if detail == 0:
        # chamfer 0: a came is 16 mm of lead and its chamfer would be 4 mm,
        # invisible at any distance and 32 extra triangles apiece. Art Bible §6
        # bevels what catches a highlight; this catches one on its own width.
        # 12 triangles each instead of 44 keeps 17 windows off a building's
        # 30k budget.
        nv = max(1, int(round(width / 0.26)) - 1)
        nh = max(1, int(round(height / 0.30)) - 1)
        for i in range(nv):
            c = M.box(0.016, height * 0.99, 0.014, 0.0, "lead")
            c.translate(-width * 0.5 + width * (i + 1) / (nv + 1), 0,
                        REVEAL - 0.019)
            out.add(c)
        for i in range(nh):
            c = M.box(width * 0.99, 0.016, 0.014, 0.0, "lead")
            c.translate(0, -height * 0.5 + height * (i + 1) / (nh + 1),
                        REVEAL - 0.019)
            out.add(c)
    for sx in (-1, 1):
        j = M.box(0.07, height + 0.14, 0.13, 0.006, frame_mat)
        j.translate(sx * (width * 0.5 + 0.035), 0, 0.0)
        out.add(j)
    for sy in (-1, 1):
        r = M.plank(width + 0.14, 0.13, 0.07, 0.006, frame_mat)
        r.translate(0, sy * (height * 0.5 + 0.035), 0.0)
        out.add(r)
    if detail == 0:
        # Mullion and transom stand in the plane of the frame and are what the
        # casement shuts against, so they run the full reveal depth back to the
        # glass instead of hanging in front of it.
        mull = M.box(0.055, height, 0.11 + REVEAL, 0.005, frame_mat)
        mull.translate(0, 0, REVEAL * 0.5)
        out.add(mull)
        tran = M.plank(width, 0.10, 0.045 + REVEAL, 0.005, frame_mat)
        tran.translate(0, 0, REVEAL * 0.5)
        out.add(tran)
    # Cill: projects OUTWARD (-Z) and is weathered so the run-off leaves the
    # streak the material expects below it.
    cill = M.box(width + 0.26, 0.075, 0.22, 0.014, "stone")
    cill.rotate_x(-0.10)
    cill.translate(0, -(height * 0.5 + 0.10), -0.06)
    out.add(cill)
    if shutters and detail == 0:
        for sx in (-1, 1):
            sh = M.Group()
            n = 3
            for i in range(n):
                # chamfer 0 on the boards: they are 30 mm thick, so the chamfer
                # clamped to 4 mm and bought nothing but 32 triangles each.
                b = M.box(width * 0.5 / n * 0.94, height * 0.96, 0.030, 0.0,
                          shutter_mat)
                b.translate(-width * 0.25 + (i + 0.5) * (width * 0.5 / n), 0, 0)
                sh.add(b)
            for y in (-height * 0.34, height * 0.34):
                led = M.box(width * 0.47, 0.065, 0.024, 0.0, shutter_mat)
                led.translate(0, y, 0.028)
                sh.add(led)
            sh.translate(sx * width * 0.25, 0, 0)
            sh.rotate_y(rng.uniform(0.18, 0.40) * sx)
            sh.translate(sx * (width * 0.5 + 0.02), 0, -0.10)
            out.add(sh)
    return out


_WIN_PROTO = {}


# Three joiners' patterns, two sizes, lit or dark: twelve window units for the
# whole town. Art Bible §6 forbids the same element three times in a row, and
# one prototype town-wide would be exactly that — but a prototype PER OPENING
# is not variety either, it is just 380 unique meshes that cannot batch. Three
# patterns dealt round-robin along a facade is what a real jobbing joiner
# produced, and it keeps the instance batches worth having.
#
# TWO woods, and a rule that says which is which. The art-director pass found
# "three different woods in one wall (pale stud, mid rail, near-black post)
# with no logic connecting them" — pale `oak` structure, `oak_dark` window
# frames, `oak_weathered` shutters, all in the same 4 m2. The town now runs on:
#
#   oak / oak_dark    STRUCTURE — the frame, dealt by the wall build-up
#   oak_dark          JOINERY   — every window frame, door frame, fascia, verge
#   painted           the one accent, on shutters and shop boards
#   oak_weathered     REPAIR only — the replaced shutter, the raking shore, the
#                     woodpile. Reserved, so that when it appears it MEANS
#                     something, which is the whole point of the §6 defect.
WIN_SIZES = {"small": (0.68, 0.88), "standard": (0.84, 1.08)}
WIN_PATTERNS = [("painted", True), ("oak_dark", True), ("oak_dark", False)]


def _window_proto(size_class, variant, glass_mat):
    variant %= len(WIN_PATTERNS)
    shutter_mat, shutters = WIN_PATTERNS[variant]
    w, h = WIN_SIZES[size_class]
    mid = f"hm.kit.window.{size_class}.{variant}.{glass_mat}"
    g = _WIN_PROTO.get(mid)
    if g is None:
        g = leaded_light(mid, w, h, glass_mat, shutters, shutter_mat)
        _WIN_PROTO[mid] = g
    return mid, (w, h), g


def _yaw_for(normal):
    """Yaw that turns a unit's local -Z onto `normal`."""
    return math.atan2(-normal[0], -normal[1])


# ---------------------------------------------------------------------------
# Openings layout
# ---------------------------------------------------------------------------

def _window_rows(plan):
    """Sill heights, above the floor, for each row of windows."""
    rows = []
    st = plan["style"]
    for i in range(plan["storeys"]):
        y = i * plan["storey_h"]
        rows.append(y + (1.02 if i == 0 else SILL_H))
    # A tall single-storey wall is a loft: it gets its own small row.
    if plan["storeys"] == 1 and plan["eaves_h"] > 3.9 and st.get("windows", 1) > 1.0:
        rows.append(plan["eaves_h"] - 1.55)
    return rows


def _front_openings(plan, length, rng):
    """(door_a, openings) for the frontage, in wall-local coordinates."""
    st = plan["style"]
    door_a = 0.0
    ops = []
    if not plan["no_door"]:
        # Never centred: Art Bible §6, and a centred door on every house is the
        # single loudest tell that a town was generated.
        door_a = -length * 0.5 + length * float(rng.uniform(0.20, 0.40))
        if plan["doors"] > 1:
            door_a = -length * 0.5 + length * 0.5 / plan["doors"]
        ops.append((door_a, DOOR_H * 0.5, DOOR_W + 0.34, DOOR_H + 0.26))
        for k in range(1, plan["doors"]):
            ops.append((door_a + k * length / plan["doors"], DOOR_H * 0.5,
                        DOOR_W + 0.34, DOOR_H + 0.26))
    return door_a, ops


def _spread(length, n, rng, margin=0.75):
    """n positions across a wall, jittered, never touching the corners."""
    if n <= 0:
        return []
    span = length - margin * 2
    if span <= 0.3:
        return []
    out = []
    for i in range(n):
        t = (i + 0.5) / n
        out.append(-length * 0.5 + margin + span * t + float(rng.uniform(-0.16, 0.16)))
    return out


# ---------------------------------------------------------------------------
# The building
# ---------------------------------------------------------------------------

class _Bake:
    """Stands in for the VenueContext while an LOD level is generated.

    `ctx.lod(mesh_id, levels)` exports each level as the WHOLE of that node's
    geometry, so a level is only correct if it is self-contained. Windows and
    props route through `ctx.instance`, which puts them in a *different* node —
    so a level built against the live context ships a windowless building at
    every distance and leaves its instances behind on the venue as well.

    That is measured, not hypothetical. Wiring `building_lods` into the
    townhouse venue against the live context put **73,514 triangles of
    coincident duplicate building** and **226 duplicate window units** into the
    shipped glTF: `build_building` emitted each of the 8 affected buildings
    once through `ctx.emit`, and `ctx.lod` then exported the same building
    again as a standalone hero node, one drawn exactly on top of the other.

    So `emit=False` now means "touch the context for nothing". Everything
    addressed to the context is captured into `group` instead.
    """

    __slots__ = ("group",)

    def __init__(self, group):
        self.group = group

    def instance(self, mesh_id, mesh, transforms):
        if mesh is None or not mesh.tri_count:
            return 0
        T, R, S = B.normalize_transforms(transforms)
        if not len(T):
            return 0
        self.group.add(B.bake_instances(mesh, T, R, S))
        return int(len(T))

    def emit(self, geom, **_kw):
        self.group.add(geom)

    # Collision, entities and nested LOD chains belong to the building, not to
    # one of its renderings. A level must not re-declare them.
    def lod(self, *_a, **_k):
        return None

    def collider(self, *_a, **_k):
        return None

    def collider_from(self, *_a, **_k):
        return None

    def collider_walls(self, *_a, **_k):
        return ()

    def collider_steps(self, *_a, **_k):
        return ()

    def entity(self, *_a, **_k):
        return None


def build_building(ctx, slot, style=None, asset_id=None, plan=None,
                   detail=0, emit=True):
    """Generate one building. Returns the Group; emits it unless `emit=False`.

    `slot` is a `buildingSlots[]` record from content/town/hearthmere.json (or
    anything with the same shape: id, polygon, centre, rotationDeg, storeys,
    eavesHeight, ridge, kit, note). `plan` overrides the derived plan, which is
    how a terrace passes its neighbours' ridge heights in.

    `emit=False` returns a self-contained Group and touches `ctx` for nothing —
    no geometry, no instances, no collision, no entities. That is what makes a
    level generated by `building_lods` safe to hand to `ctx.lod`.
    """
    plan = plan or plan_building(slot, style, asset_id)
    aid = plan["id"]
    st = plan["style"]
    fp = plan["footprint"]
    rng = rng_for(aid, "build")
    g = M.Group()

    floor_y = plan["floor_y"]
    base_y = plan["base_y"]
    party = plan.get("party", {})

    # Everything below addresses `sink`, never `ctx` directly, so that an LOD
    # level cannot reach the venue. See `_Bake`.
    sink = ctx if emit else _Bake(g)

    # -- 1. plinth / underbuilding --------------------------------------
    _plinth(g, plan, rng, detail)

    # -- 2. wall bands ---------------------------------------------------
    plate = _walls(sink, g, plan, rng, detail)

    # -- 3. roof, from the plate and nothing else ------------------------
    wing = plan.get("wing")
    roof = roof_from_plate(
        plate, plan["roof_kind"], plan["pitch"], plan["overhang"], aid,
        mat=plan["roof_mat"], timber_mat="oak_dark", detail=detail,
        ridge_axis=plan["ridge_axis"],
        hip_frac=0.5 + 0.15 * float(rng.random()),
        catslide_run=plan["catslide_run"],
        # The range's eaves stops at the wing and starts again the other side,
        # because that is where its rafters stop. Without this the eaves board
        # runs straight through the wing's roof.
        trim_exclude=(wing["wall_poly"] if wing else None))
    g.add(roof)
    plan["roof"] = roof
    plan["ridge_y"] = roof.ridge_y

    # -- 3b. the wing, roofed against the range so the valley is real -----
    if wing:
        _wing(sink, g, plan, roof, rng, detail)

    # -- 4. things that pass through the roof ----------------------------
    _chimneys(g, plan, roof, rng, detail)
    if detail == 0:
        _dormers(g, plan, roof, rng)

    # -- 5. party walls ---------------------------------------------------
    # NOT here. A shared wall is the upper envelope of two roofs, so it cannot
    # be built until both exist: `build_party_walls(ctx, plans)` runs after the
    # loop that builds the terrace. See that function.

    # -- 6. the one thing that is visibly wrong (Art Bible §6) -----------
    if detail == 0:
        _defect(g, plan, roof, rng)
        _residue(sink, g, plan, rng)

    # -- 7. collision -----------------------------------------------------
    if emit:
        _collision(ctx, plan)
        _entities(ctx, plan)
        ctx.emit(g, label=None, container=None)
    return g


def door_positions(slot, style=None, asset_id=None, plan=None):
    """World door positions for a slot: [(x, y, z, wall-local a)].

    The street needs these. A threshold stone, a boot scraper and a dropped
    kerb belong AT THE DOOR, and a doorstep two metres off its door is the
    kind of near-miss that reads as broken rather than as procedural.

    Where the door is cannot be derived from the slot record: `_front_openings`
    draws it from the building's own seeded stream ("never centred: Art Bible
    §6, and a centred door on every house is the single loudest tell that a
    town was generated"), several draws deep into `rng_for(id, "build")`. So
    this replays the plinth and the walls — the same calls in the same order,
    therefore the same stream — into a scratch group and reads the answer off
    the plan. It stops short of the roof, which is most of the cost of a
    building: 94 slots in 1.8 s rather than 7.1 s.

    It must never be given the venue's real ctx. `_Bake` swallows everything,
    so a caller cannot accidentally emit ninety buildings twice.
    """
    plan = plan or plan_building(slot, style, asset_id)
    if plan.get("door_world") is None:
        g = M.Group()
        rng = rng_for(plan["id"], "build")
        _plinth(g, plan, rng, 3)
        _walls(_Bake(g), g, plan, rng, 3)
    return list(plan.get("door_world") or [])


# -- 1. plinth ---------------------------------------------------------------

def _plinth(g, plan, rng, detail):
    """Stone base from the floor down to the lowest ground under the perimeter.

    Where that is more than a step, it becomes an underbuilding with its own
    cellar door — which is what a real town does on a terrace scarp, and it is
    why nothing here can float.
    """
    fp = plan["footprint"]
    h = plan["plinth_h"]
    top = plan["floor_y"]
    # Slightly proud of the wall face so the wall sits ON it and the junction
    # throws a shadow — the detail that says "founded", not "resting".
    pts = fp.rect(front=0.10, back=0.10, left=0.10, right=0.10)
    band = _prism_between(pts, top - h, top, "stone", chamfer=0.03)
    g.add(band)
    if h > 0.85 and detail == 0:
        # An underbuilding gets a plinth string and a barred cellar light, so
        # its height reads as a storey rather than as a mistake.
        s = _prism_between(fp.rect(front=0.16, back=0.16, left=0.16, right=0.16),
                           top - 0.16, top - 0.06, "ashlar")
        g.add(s)
        hw, hd = fp.half
        a = float(rng.uniform(-hw * 0.4, hw * 0.4))
        x, z = fp.world(a, -hd - 0.06)
        n = (-fp.V[0], -fp.V[1])
        hatch = M.Group()
        op = M.box(0.86, 0.55, 0.10, 0.01, "oak_dark")
        hatch.add(op)
        for k in range(3):
            bar = M.box(0.045, 0.5, 0.045, 0.006, "iron")
            bar.translate(-0.28 + k * 0.28, 0, -0.05)
            hatch.add(bar)
        M.place(hatch, np.array([x, top - h * 0.55, z]),
                np.array([-n[1], 0.0, n[0]]), np.array([0.0, 1.0, 0.0]),
                np.array([-n[0], 0.0, -n[1]]))
        g.add(hatch)


def _prism_between(pts2, y0, y1, mat, uv=None, chamfer=0.02):
    """A closed vertical prism on a plan polygon — plinths, party walls, kerbs."""
    h = float(y1) - float(y0)
    if h <= 0.01:
        return M.Group()
    prof = [(float(x), float(z)) for x, z in pts2]
    out = M.Group()
    b = M._Builder()
    n = len(prof)
    for i in range(n):
        x0, z0 = prof[i]
        x1, z1 = prof[(i + 1) % n]
        quad = [np.array([x0, y0, z0]), np.array([x1, y0, z1]),
                np.array([x1, y1, z1]), np.array([x0, y1, z0])]
        b.poly(quad, None, None)
    top = [np.array([x, y1, z]) for x, z in prof]
    if R._area2(prof) > 0:
        top = top[::-1]
    b.poly(top, None, np.array([0.0, 1.0, 0.0]))
    m = b.build(mat)
    # Winding is resolved per face by the builder's own normal; a plan polygon
    # can arrive either way round from the town file.
    if _signed_volume(m) < 0:
        _invert(m)
    out.add(m)
    return out


def _signed_volume(mesh):
    v = mesh.v[mesh.idx].reshape(-1, 3, 3)
    return float(np.einsum("ij,ij->i",
                           np.cross(v[:, 0], v[:, 1]), v[:, 2]).sum() / 6.0)


# -- 2. walls ----------------------------------------------------------------

def _bands(plan):
    """[(y0, y1, plan-polygon, wall build-up)] bottom to top.

    A jetty is a change of footprint between bands, which is exactly what it is
    in carpentry: the first floor is a bigger rectangle carried on the joists
    of the one below.
    """
    st = plan["style"]
    fp = plan["footprint"]
    kinds = list(st["walls"])
    floor_y = plan["floor_y"]
    eaves_h = plan["eaves_h"]
    jetty = plan["jetty"]
    party = plan.get("party", {})
    out = []
    if jetty <= 0.01 or plan["storeys"] < 2:
        out.append((floor_y, floor_y + eaves_h, fp.rect(), kinds[0]))
        return out
    h0 = min(plan["storey_h"], eaves_h - 1.6)
    # Oversail on the street sides only; a jetty over a party wall is not a
    # thing you can build.
    over = {}
    for idx, key in ((0, "front"), (1, "right"), (2, "back"), (3, "left")):
        blocked = idx in party
        over[key] = 0.0 if blocked else (jetty if idx in (0,) else jetty * 0.55)
    out.append((floor_y, floor_y + h0, fp.rect(), kinds[0]))
    out.append((floor_y + h0, floor_y + eaves_h, fp.rect(**over),
                kinds[min(1, len(kinds) - 1)]))
    return out


# The material a bay alternates INTO when a run is broken up. A real long
# frontage is not one build; it is a first build and a rebuilt bay, and that is
# the cheapest legible reason for the break Art Bible §7 demands.
# What an alternate bay is built of. NOT `brick` off `timber`: the town plan
# gives brick nogging to exactly one building — slot 50, "the only nogging in
# Hearthmere, and a different colour from everything near it" — and dealing a
# brick bay onto every timber elevation over 12 m contradicted that on the
# granary, two warehouses and the bede houses at once. A limewashed panel
# beside a plastered one is the ordinary variation and it stays in palette.
BAY_ALT = {
    "rubble": "limewash", "timber": "limewash", "ashlar": "rubble",
    "limewash": "rubble", "brick": "rubble", "plastered": "limewash",
}
BAY_RECESS = 0.11       # how far an alternate bay stands back


def _party_span(mid, ex, ln, rec):
    """The stretch of this edge, in wall-local `a`, the shared wall covers."""
    line = rec.get("line")
    if not line:
        return (-ln * 0.5 - 1.0, ln * 0.5 + 1.0)     # whole edge
    a = []
    for p in line:
        d = np.asarray(p, float) - np.asarray(mid, float)
        a.append(float(d[0] * ex[0] + d[1] * ex[1]))
    return (min(a) - PARTY_BEARING, max(a) + PARTY_BEARING)


def _bay_bounds(ln, ops, rng):
    """Where to break a run longer than BAY_MAX, in wall-local `a`.

    Bays land at 4-6 m, which is a structural bay and also the width of one
    dwelling — so on the almshouse row the break falls between front doors and
    the row reads as six houses rather than as one shed with six doors in it.
    A boundary that would cut an opening is walked to the nearer side of it: a
    pier through a window is a worse defect than the one being fixed.
    """
    n = max(2, int(round(ln / 5.0)))
    step = ln / n
    out = []
    for i in range(1, n):
        b = -ln * 0.5 + step * i + float(rng.uniform(-0.08, 0.08)) * step
        for (oa, _oy, ow, _oh) in sorted(ops, key=lambda o: o[0]):
            lo, hi = oa - ow * 0.5 - 0.20, oa + ow * 0.5 + 0.20
            if lo < b < hi:
                b = lo if (b - lo) < (hi - b) else hi
        out.append(b)
    return [b for b in sorted(out)
            if -ln * 0.5 + 1.2 < b < ln * 0.5 - 1.2]


def _edge_runs(plan, ei, ln, kind, ops, rng, skip=None):
    """Split one wall edge into the runs actually built, plus the piers.

    Two independent reasons a run is not one box:

      * a party wall covers part of the edge, and this neighbour builds only
        what the shared wall does not reach (`skip`);
      * the run is longer than Art Bible §7's 12 m limit, so it is broken into
        bays that alternate material and set back, with a pier on every break.

    Returns `([(centre, width, kind, recess)], [pier_a])`, all in wall-local
    `a`.
    """
    spans = [(-ln * 0.5, ln * 0.5)]
    for (s0, s1) in (skip or []):
        nxt = []
        for (a0, a1) in spans:
            if s1 <= a0 or s0 >= a1:
                nxt.append((a0, a1))
                continue
            if s0 - a0 > 0.28:
                nxt.append((a0, s0))
            if a1 - s1 > 0.28:
                nxt.append((s1, a1))
        spans = nxt

    runs, piers = [], []
    alt = BAY_ALT.get(kind, kind)
    for (a0, a1) in spans:
        w = a1 - a0
        if w <= 0.28:
            continue
        if w <= BAY_MAX:
            runs.append(((a0 + a1) * 0.5, w, kind, 0.0))
            continue
        if plan["doors"] > 1 and ei == 0:
            # A row of dwellings breaks BETWEEN dwellings. Taking the bays from
            # the doors is what turns `bede_houses` from 24 m of undifferentiated
            # rubble with six doors punched in it into six houses in a row.
            ds = sorted(oa for (oa, _y, _w, oh) in ops if oh > DOOR_H * 0.9)
            cand = [(ds[i] + ds[i + 1]) * 0.5 for i in range(len(ds) - 1)]
        else:
            cand = _bay_bounds(ln, ops, rng)
        cuts = [b for b in cand if a0 + 1.0 < b < a1 - 1.0]
        edges = [a0] + cuts + [a1]
        for k in range(len(edges) - 1):
            b0, b1 = edges[k], edges[k + 1]
            odd = (k % 2) == 1
            runs.append(((b0 + b1) * 0.5, b1 - b0,
                         alt if odd else kind,
                         BAY_RECESS if odd else 0.0))
            if k:
                piers.append(b0)
    return runs, piers


def _reveal_ring(oa, oy, ow, oh, face_z, back_z, mat):
    """The four returns of an opening, lined in the wall's own material.

    A reveal is masonry, not joinery, so it lives with the wall — which is also
    what keeps `leaded_light` to twelve prototypes for the whole town instead of
    one per wall build-up. Four quads, eight triangles: only the inside faces
    are ever seen, and building them as chamfered boxes cost 2,100 triangles a
    building for surfaces nobody can look at.
    """
    b = M._Builder()
    x0, x1 = oa - ow * 0.5, oa + ow * 0.5
    y0, y1 = oy - oh * 0.5, oy + oh * 0.5
    P = lambda x, y, z: np.array([x, y, z], float)
    # (quad, inward normal) — the normal points into the opening.
    faces = [
        ([P(x0, y0, face_z), P(x0, y0, back_z), P(x0, y1, back_z), P(x0, y1, face_z)],
         np.array([1.0, 0.0, 0.0])),
        ([P(x1, y1, face_z), P(x1, y1, back_z), P(x1, y0, back_z), P(x1, y0, face_z)],
         np.array([-1.0, 0.0, 0.0])),
        ([P(x0, y1, face_z), P(x0, y1, back_z), P(x1, y1, back_z), P(x1, y1, face_z)],
         np.array([0.0, -1.0, 0.0])),
        ([P(x1, y0, face_z), P(x1, y0, back_z), P(x0, y0, back_z), P(x0, y0, face_z)],
         np.array([0.0, 1.0, 0.0])),
    ]
    for quad, nrm in faces:
        if float(np.dot(np.cross(quad[1] - quad[0], quad[2] - quad[0]), nrm)) < 0:
            quad = quad[::-1]
        b.poly(quad, None, nrm)
    return b.build(mat)


def _bay_pier(g, plan, mid, ex, out_n, a, y0, y1, mat, recess):
    """A pilaster on a bay break: the vertical element §7 asks for.

    It runs from the plinth to the wall head and projects, so it reads at 30 m
    in silhouette and closes the return where an alternate bay sets back.
    """
    h = y1 - y0
    depth = WALL_T + recess + 0.30
    pier = M.box(0.44, h, depth, 0.018, mat)
    pier.translate(a, h * 0.5, -0.06)
    cap = M.box(0.56, 0.11, depth + 0.10, 0.014, "sandstone")
    cap.translate(a, h - 0.05, -0.06)
    grp = M.Group()
    grp.add(pier)
    grp.add(cap)
    _place_run(grp, mid, ex, -out_n)
    grp.translate(0, y0, 0)
    g.add(grp)


def _walls(ctx, g, plan, rng, detail):
    """Build every wall run and return the plate the roof will stand on."""
    st = plan["style"]
    fp = plan["footprint"]
    party = plan.get("party", {})
    bands = _bands(plan)
    rows = _window_rows(plan)
    win_per_10m = float(st.get("windows", 1.8))
    glass_mat = "glass_lit" if rng.random() < 0.28 else "glass"
    win_v = int(rng.integers(0, 3))       # this owner's joiner
    door_world = None
    plate_edges = []
    variant = 0

    for bi, (y0, y1, pts, kind) in enumerate(bands):
        cen = np.mean(np.asarray(pts, float), axis=0)
        h = y1 - y0
        for ei in range(4):
            a, b = pts[ei], pts[(ei + 1) % 4]
            fr = _edge_frame(a, b, cen)
            if fr is None:
                continue
            mid, ex, out_n, ln = fr
            pk = party.get(ei, {})
            skip = [_party_span(mid, ex, ln, pk)] if pk else []
            if plan["open_sides"] and ei != 2:
                continue                     # open-sided shed: posts only

            ops = []
            door_a = None
            row_ys = [r - (y0 - plan["floor_y"]) for r in rows]
            if bi == 0 and ei == 0:
                door_a, dops = _front_openings(plan, ln, rng)
                ops += dops
            nwin = int(round(win_per_10m * ln / 10.0 *
                             (1.0 if ei == 0 else 0.65)))
            for r in row_ys:
                if r < 0.4 or r + 1.4 > h:
                    continue
                for a_pos in _spread(ln, max(0 if ei != 0 else 1, nwin), rng):
                    if door_a is not None and abs(a_pos - door_a) < DOOR_W + 0.7:
                        continue
                    cls = "standard" if st.get("wealth", 0.4) > 0.45 else "small"
                    ww, hh = WIN_SIZES[cls]
                    ops.append((a_pos, r + hh * 0.5, ww + 0.22, hh + 0.24))
            # Apertures dropped by the party wall or by a bay break are not
            # apertures: an opening the wall behind it no longer has is a
            # window unit hung on air.
            runs, piers = _edge_runs(plan, ei, ln, kind, ops, rng, skip)
            kept = []

            for (ca, cw, ckind, recess) in runs:
                bops = [(oa - ca, oy, ow, oh) for (oa, oy, ow, oh) in ops
                        if abs(oa - ca) + ow * 0.5 < cw * 0.5 - 0.10]
                seg = M.Group()
                depth = (WALL_T * 0.8) if ckind == "timber" else WALL_T
                seg.add(wall_run(f"{plan['id']}.b{bi}.e{ei}.{round(ca, 2)}",
                                 cw, h, ckind, st["frame"], bops,
                                 mats=WALL_MAT.get(ckind), detail=detail,
                                 nogging=plan["nogging"] and ei == 1 and bi == 0))
                wmat = WALL_MAT.get(ckind, ("plaster",))[0]
                if detail == 0:
                    for op in bops:
                        seg.add(_reveal_ring(op[0], op[1], op[2], op[3],
                                             -depth * 0.5 - 0.012, 0.085, wmat))
                    # Art Bible §5, explicit: the bottom 0.15 m of every wall
                    # gets splash dirt. Geometry, not just a texture band, so it
                    # throws its own shadow line and the wall stops meeting the
                    # ground on a razor edge.
                    sp = M.box(cw - 0.02, 0.17, depth + 0.028, 0.01,
                               "plaster_shade" if ckind == "timber" else "rubble")
                    sp.translate(0, 0.085, 0)
                    seg.add(sp)
                _place_run(seg, (mid[0] + ex[0] * ca, mid[1] + ex[1] * ca),
                           ex, -out_n)
                if recess:
                    seg.translate(out_n[0] * -recess, 0.0, out_n[1] * -recess)
                seg.translate(0, y0, 0)
                g.add(seg)
                for op in bops:
                    kept.append((op[0] + ca, op[1], op[2], op[3], recess))

            for pa in piers:
                _bay_pier(g, plan, mid, ex, out_n, pa, y0, y1,
                          "ashlar" if kind in ("rubble", "ashlar") else "rubble",
                          BAY_RECESS)

            # Window units into their holes.
            for (oa, oy, ow, oh, recess) in kept:
                if oh > DOOR_H:
                    continue
                variant += 1
                wx, wz = _world_on_run(mid, ex, oa)
                wx -= out_n[0] * recess
                wz -= out_n[1] * recess
                mid_id, _wh, proto = _window_proto(
                    "standard" if ow > 0.95 else "small", variant + win_v, glass_mat)
                pos = (wx - out_n[0] * 0.02, y0 + oy, wz - out_n[1] * 0.02)
                yaw = _yaw_for(out_n)
                ctx.instance(mid_id, proto, [(pos[0], pos[1], pos[2], yaw)])
                # INWARD: `out_n` points out of the building, so the
                # panel that stops daylight coming through the far wall goes
                # the other way. Hung outward it becomes a dark board nailed
                # over the window, which is exactly how it first rendered.
                plan.setdefault("backings", []).append(
                    (wx - out_n[0] * 0.34, y0 + oy, wz - out_n[1] * 0.34,
                     yaw, ow, oh))

            if bi == 0 and ei == 0 and door_a is not None:
                # Only if the wall the door is in survived. A party wall or a
                # bay break can eat the stretch `_front_openings` chose, and a
                # door leaf standing where no wall is left is worse than a
                # blank frontage.
                if any(abs(door_a - ca) < cw * 0.5 for (ca, cw, _k, _r) in runs):
                    door_world = (mid, ex, out_n, door_a, ln)
            if bi == 0 and ei == 0:
                # The front run's frame, kept for anything that has to be hung
                # on the frontage after the walls exist — the loading door and
                # its gibbet beam below, a shop sign, an awning.
                plan["front_run"] = (mid, ex, out_n, ln)

        plate_edges = pts

    # -- doors -------------------------------------------------------------
    if door_world is not None:
        _doors(g, plan, door_world, rng, detail)

    # -- the loading door and its hoist ------------------------------------
    # `plan["loading"]` has been planned since the style table was written and
    # nothing built it, so every warehouse in Hearthmere had grain on the first
    # floor and no way of getting it there.
    if plan.get("loading") and plan.get("front_run") and detail == 0:
        _loading_door(g, plan, rng)

    # -- jetty: the bressummer and the joist ends that carry it ------------
    if len(bands) > 1 and detail <= 1:
        _jetty(g, plan, bands, rng)

    # -- the outshut a catslide roof lands on ------------------------------
    if plan["catslide_run"] > 0.1:
        _outshut(g, plan, bands, rng, detail)

    # -- interior: stops the town being see-through ------------------------
    if detail <= 1:
        _backings(g, plan)

    edges = []
    for ei in range(4):
        rec = plan.get("party", {}).get(ei)
        edges.append("party" if rec else
                     ("gable" if _is_gable_edge(plan, ei) else "eaves"))
    return wall_plate(plate_edges, plan["plate_y"], edges=edges,
                      thickness=WALL_T, wall_mat=WALL_MAT.get(
                          _bands(plan)[-1][3], ("plaster",))[0])


def _is_gable_edge(plan, ei):
    """Front/back are gable ends when the ridge runs across the plot."""
    return (ei in (1, 3)) if plan["ridge_axis"] == "u" else (ei in (0, 2))


def _world_on_run(mid, ex, a):
    return (mid[0] + ex[0] * a, mid[1] + ex[1] * a)


def _doors(g, plan, door_world, rng, detail):
    mid, ex, out_n, door_a, ln = door_world
    st = plan["style"]
    y = plan["floor_y"]
    for k in range(plan["doors"]):
        a = door_a + k * ln / plan["doors"]
        x, z = _world_on_run(mid, ex, a)
        unit = M.Group()
        unit.add(K.door_frame(mat="oak_dark", depth=WALL_T))
        unit.add(K.plank_door(f"{plan['id']}.door{k}",
                              open_angle=float(rng.uniform(0.0, 0.42))
                              if k == 0 and rng.random() < 0.5 else 0.0))
        M.place(unit, np.array([x, y, z]),
                np.array([ex[0], 0.0, ex[1]]), np.array([0.0, 1.0, 0.0]),
                np.array([-out_n[0], 0.0, -out_n[1]]))
        g.add(unit)
        plan.setdefault("door_world", []).append((x, y, z, a))
        plan.setdefault("backings", []).append(
            (x - out_n[0] * 0.55, y + DOOR_H * 0.5, z - out_n[1] * 0.55,
             math.atan2(-out_n[0], -out_n[1]), DOOR_W, DOOR_H))
    # A door above the plinth needs steps, or it is visible and unreachable.
    if plan["plinth_h"] > 0.22 and detail == 0:
        _door_steps(g, plan, mid, ex, out_n, door_a, rng)


def _loading_door(g, plan, rng):
    """A taking-in door at first floor, its gibbet beam, block and fall.

    This is the object that tells you a building is a warehouse and not a big
    house, and it is the only reason a warehouse's blank frontage is not a
    defect: everything above the ground floor is loaded through this one
    opening, so the wall around it is meant to be blind.

    Built from the plate down rather than from the ground up, so it lands under
    the eaves whatever the storey heights came out at, and the beam projects
    far enough that a sack on the fall hangs clear of the wall below it — which
    is the whole point of a gibbet and the thing that reads at 30 m.
    """
    mid, ex, out_n, ln = plan["front_run"]
    aid = plan["id"]
    # Centre it on the frontage but never exactly: a taking-in door goes where
    # the floor beams let it, and the bays are not symmetrical.
    a = float(rng.uniform(-0.18, 0.18)) * ln
    x, z = _world_on_run(mid, ex, a)
    yaw = math.atan2(-out_n[0], -out_n[1])
    head = plan["plate_y"] - 0.55
    w, h = 1.55, 2.05
    sill = head - h

    unit = M.Group()
    # Reveal, so the opening has a depth and reads as a hole rather than a
    # panel; then the two leaves, one swung back against the wall.
    for sx in (-1, 1):
        j = M.box(0.16, h + 0.24, WALL_T + 0.10, 0.014, "oak_dark")
        j.translate(sx * (w * 0.5 + 0.08), (h + 0.24) * 0.5 - 0.12, WALL_T * 0.5)
        unit.add(j)
    lin = M.plank(w + 0.60, 0.24, WALL_T + 0.12, 0.012, "oak_dark")
    lin.translate(0, h + 0.12, WALL_T * 0.5)
    unit.add(lin)
    dark = M.box(w, h, 0.24, 0.01, "oak_dark")
    dark.scale(-1.0, 1.0, 1.0)
    dark.translate(0, h * 0.5, WALL_T + 0.16)
    unit.add(dark)
    for sx, ang in ((-1, float(rng.uniform(0.9, 1.5))), (1, 0.0)):
        leaf = K.plank_door(f"{aid}.load{sx}", width=w * 0.5, height=h,
                            mat="oak_weathered", open_angle=ang)
        leaf.translate(sx * w * 0.25, 0.0, -0.02)
        unit.add(leaf)
    # Gibbet beam: a cantilever out of the gable with a knee brace under it.
    # Every Y below is LOCAL to the unit, whose origin is the sill — `head` is
    # an absolute world height and using it here hung the beam a whole storey
    # above the ridge with the fall dangling in the sky.
    top = h + 0.62
    beam = M.plank(0.20, 0.24, 2.35, 0.012, "oak_dark", grain_axis=1)
    beam.translate(0, top, -0.95)
    unit.add(beam)
    br = M.plank(1.15, 0.14, 0.14, 0.010, "oak_dark")
    br.rotate_x(0.72)
    br.translate(0, h + 0.20, -0.42)
    unit.add(br)
    # Block, fall and hook. The fall is made off on a cleat by the door, which
    # is where a man standing in the opening can reach it.
    blk = M.box(0.20, 0.34, 0.14, 0.014, "oak_dark")
    blk.translate(0, top - 0.34, -1.90)
    unit.add(blk)
    unit.add(M.tube((0.0, top - 0.12, -1.90), (0.0, top - 0.32, -1.90),
                    0.022, "sacking", segments=5))
    drop = float(rng.uniform(1.4, 2.6))
    unit.add(M.tube((0.0, top - 0.46, -1.90), (0.0, top - 0.46 - drop, -1.90),
                    0.020, "sacking", segments=5))
    hk = M.lathe([(0.05, 0.0), (0.07, 0.05), (0.05, 0.26)], 8, "iron_pitted")
    hk.translate(0.0, top - 0.46 - drop - 0.26, -1.90)
    unit.add(hk)
    cleat = M.box(0.30, 0.09, 0.12, 0.010, "oak_dark")
    cleat.translate(w * 0.5 + 0.34, 0.90, -0.06)
    unit.add(cleat)
    # A pallet of sacks on the hook half the time: the job in progress.
    if rng.random() < 0.5 and drop > 1.9:
        for k in range(2):
            sk = K.sack(f"{aid}.hoist.{k}", height=0.52, mat="sacking")
            sk.rotate_y(float(rng.uniform(0, 3.1)))
            sk.translate(float(rng.uniform(-0.1, 0.1)),
                         top - 0.46 - drop - 0.10 + k * 0.34,
                         -1.90 + float(rng.uniform(-0.1, 0.1)))
            unit.add(sk)

    M.place(unit, np.array([x, sill, z]),
            np.array([ex[0], 0.0, ex[1]]), np.array([0.0, 1.0, 0.0]),
            np.array([-out_n[0], 0.0, -out_n[1]]))
    g.add(unit)
    plan["loading_world"] = (x, sill, z, yaw, a)
    plan.setdefault("backings", []).append((x - out_n[0] * 0.4, sill + h * 0.5,
                                            z - out_n[1] * 0.4, yaw, w, h))


def _door_steps(g, plan, mid, ex, out_n, door_a, rng):
    """The threshold: stones cut for a door, bedded into the ground.

    The old version laid `DOOR_W + 0.85` — 1.80 m of tread for a 0.95 m door —
    at `uv_scale=0.6`, so the `stone` material's 0.4 m blocks came out at 0.67 m
    and the top face showed two enormous cobbles. Read as a slab of pavement
    dropped on the mud, which is what the art-director pass called it.

    Three things fix it and all three are what a mason actually does: cut the
    stone to the door with a hand of margin, tile the material at the size the
    stone really is, and BED the bottom step — dig it in, pack the sides with
    spalls, and let the ground come up to it. A step with a hard edge and a
    shadow gap under it is the tell.
    """
    x, z = _world_on_run(mid, ex, door_a)
    yaw = math.atan2(-out_n[0], -out_n[1])
    ph = plan["plinth_h"]
    base = plan["floor_y"] - ph
    n = max(1, int(math.ceil(ph / 0.175)))          # Art Bible §3 riser
    # Wide enough to stand on with the door open, narrow enough to read as a
    # doorstep: the top tread is the door plus a boot each side.
    reach = 0.0
    for i in range(n):
        rise = ph * (i + 1) / n
        going = 0.30
        wide = DOOR_W + 0.34 + 0.10 * (n - 1 - i)
        # Worn stone: Art Bible §6 gives it a 25 mm irregular chamfer, and the
        # nosing is where every boot in the town lands.
        step = M.box(wide, rise + 0.02, going * (n - i), 0.025, "stone")
        depth = going * (n - i)
        cx = x + out_n[0] * (0.12 + depth * 0.5)
        cz = z + out_n[1] * (0.12 + depth * 0.5)
        step.rotate_y(yaw)
        step.rotate_y(float(rng.uniform(-0.012, 0.012)))
        step.translate(cx, base + (rise + 0.02) * 0.5, cz)
        g.add(step)
        reach = max(reach, 0.12 + depth)
    # Bedding: the bottom stone sits IN the ground, not on it, and the packing
    # stones round its foot are what makes that read.
    bx = x + out_n[0] * (0.12 + reach * 0.5)
    bz = z + out_n[1] * (0.12 + reach * 0.5)
    gy = max(float(T.height(bx, bz)), base)
    bed = M.box(DOOR_W + 0.60, 0.16, reach + 0.16, 0.03, "stone")
    bed.rotate_y(yaw)
    bed.translate(bx, min(gy, base) - 0.02, bz)
    g.add(bed)
    for k in range(5):
        s = float(rng.uniform(0.10, 0.17))
        sx = float(rng.uniform(-1.0, 1.0)) * (DOOR_W * 0.5 + 0.34)
        sb = float(rng.uniform(0.10, reach + 0.10))
        px = x + ex[0] * sx + out_n[0] * sb
        pz = z + ex[1] * sx + out_n[1] * sb
        spall = M.box(s, s * 0.55, s * 0.8, 0.02, "stone")
        spall.rotate_y(float(rng.uniform(0, 6.28)))
        spall.translate(px, max(float(T.height(px, pz)), base) - 0.01, pz)
        g.add(spall)


def _jetty(g, plan, bands, rng):
    """Bressummer, brackets and exposed joist ends under an oversailing floor.

    The joist ends are the point: an overhang with a plain soffit reads as a
    box pushed out, and this is the single best silhouette-breaker the town
    has.
    """
    lower, upper = bands[0], bands[1]
    y = lower[1]
    lo_pts, hi_pts = lower[2], upper[2]
    cen = np.mean(np.asarray(hi_pts, float), axis=0)
    for ei in range(4):
        a, b = hi_pts[ei], hi_pts[(ei + 1) % 4]
        fr = _edge_frame(a, b, cen)
        if fr is None:
            continue
        mid, ex, out_n, ln = fr
        la, lb = lo_pts[ei], lo_pts[(ei + 1) % 4]
        lfr = _edge_frame(la, lb, cen)
        over = float(np.dot(np.asarray(mid) - np.asarray(lfr[0]), out_n))
        if over < 0.04:
            continue
        beam = M.plank(ln + 0.1, 0.30, 0.28, CHAMFER, "oak_dark")
        _place_run(beam, mid, ex, -out_n)
        beam.translate(0, y + 0.02, 0)
        g.add(beam)
        n = max(2, int(ln / 1.5))
        for i in range(n + 1):
            t = -ln * 0.5 + ln * i / n
            br = M.prism([(0, 0), (over + 0.06, 0), (0, -0.46)], 0.13, chamfer=0.006)
            M.place(br, np.array([mid[0] + ex[0] * t, y - 0.02,
                                  mid[1] + ex[1] * t]),
                    np.array([-out_n[0], 0.0, -out_n[1]]),
                    np.array([0.0, 1.0, 0.0]), np.array([ex[0], 0.0, ex[1]]))
            g.add(br.with_material("oak_dark"))
        # Joist ends, showing under the oversail.
        nj = max(2, int(ln / 0.62))
        for i in range(nj):
            t = -ln * 0.5 + ln * (i + 0.5) / nj
            j = M.box(0.085, 0.145, over * 0.9, 0.006, "oak_dark")
            j.rotate_y(math.atan2(-out_n[0], -out_n[1]))
            j.translate(mid[0] + ex[0] * t - out_n[0] * over * 0.45,
                        y - 0.20 + float(rng.uniform(-0.008, 0.008)),
                        mid[1] + ex[1] * t - out_n[1] * over * 0.45)
            g.add(j)


def _outshut(g, plan, bands, rng, detail):
    """The lean-to under a catslide: low walls carrying the extended eaves.

    Its head height is READ OFF the roof geometry — plate level less the pitch
    over the run — so the wall meets the slope by construction. Authoring it
    would be a second number to keep in step with the roof, which is the exact
    mistake this module exists to make impossible.
    """
    fp = plan["footprint"]
    run = plan["catslide_run"]
    head = plan["plate_y"] - plan["pitch"] * (plan["overhang"] + run) - 0.10
    h = head - plan["floor_y"]
    if h < OUTSHUT_MIN_H:
        # `plan_building` solves the run so this cannot fire. If it ever does,
        # the roof must not have been extended either — so refuse loudly rather
        # than silently leaving a catslide hanging over open air.
        raise RuntimeError(
            f"{plan['id']}: catslide run {run:.2f} m leaves a {h:.2f} m outshut "
            f"head (min {OUTSHUT_MIN_H}). plan_building must clamp the run.")
    pts = fp.rect(back=run)
    base = fp.rect()
    cen = np.mean(np.asarray(pts, float), axis=0)
    kind = plan["style"]["walls"][0]
    # Back wall full width, plus the two short returns from the house to it.
    edges = [(pts[2], pts[3]), (base[1], pts[2]), (pts[3], base[0])]
    for i, (a, b) in enumerate(edges):
        fr = _edge_frame(a, b, cen)
        if fr is None or fr[3] < 0.4:
            continue
        mid, ex, out_n, ln = fr
        ops = []
        if i == 0 and ln > 2.4:
            # The window is sized and seated from the head the outshut actually
            # has, not from a constant. A 0.94 m light centred at 1.05 m puts
            # its head at 1.52 m, which was ABOVE the wall plate on eight of the
            # thirteen catslides — an opening breaking out through the top of
            # its own wall. Below 1.9 m of head there is no room for a window
            # at all and the honest answer is a blank wall.
            if h >= 1.9:
                wh = min(0.94, h - 0.75)
                wy = min(1.05, h - wh * 0.5 - 0.30)
                ops.append((float(rng.uniform(-ln * 0.2, ln * 0.2)), wy,
                            0.94, wh))
        w = wall_run(f"{plan['id']}.out{i}", ln, h, kind,
                     plan["style"]["frame"], ops, mats=WALL_MAT.get(kind),
                     detail=detail)
        _place_run(w, mid, ex, -out_n)
        w.translate(0, plan["floor_y"], 0)
        g.add(w)
    g.add(_prism_between(pts, plan["base_y"], plan["floor_y"], "stone",
                         chamfer=0.03))


def _lap_shrunk(w, f):
    """The wing plate with its lap into the main range scaled by `f`."""
    p = list(w["plate_poly"])
    q = list(w["wall_poly"])
    i = w["inner"]
    j = (i + 1) % 4
    for k in (i, j):
        a = np.asarray(q[k], float)
        b = np.asarray(p[k], float)
        p[k] = tuple(a + (b - a) * f)
    return p


def _wing(ctx, g, plan, main_roof, rng, detail):
    """The rear wing or cross-gable: its own walls, its own plate, its own roof.

    The roof is cut with `clip_against=main_roof`, and that cut is the valley —
    the one path `core/roof.py` implemented and nothing in the town called, so
    every mass was a single rectangle and the roofscape was 63 parallel ridges.

    Its plate is a metre or so LOWER than the range's. Two reasons, and both
    are what a builder would do: a wing is subordinate, so it should read as
    subordinate on the skyline; and it keeps the wing's eaves clear under the
    range's, which is the junction that would otherwise be two fascia boards
    fighting for the same 200 mm.
    """
    w = plan["wing"]
    st = plan["style"]
    kind = st["walls"][-1]
    floor_y = plan["floor_y"]
    drop = min(0.55, (plan["plate_y"] - floor_y) * 0.14)
    plate_y = plan["plate_y"] - drop
    h = plate_y - floor_y
    if h < 2.3:
        return None

    wall_pts = w["wall_poly"]
    cen = np.mean(np.asarray(wall_pts, float), axis=0)
    grown = []
    for p in wall_pts:                       # plinth, proud of the wall face
        d = np.asarray(p, float) - cen
        n = float(np.hypot(d[0], d[1])) or 1.0
        grown.append((p[0] + d[0] / n * 0.13, p[1] + d[1] / n * 0.13))
    g.add(_prism_between(grown, plan["base_y"], floor_y, "stone",
                         chamfer=0.03))

    glass_mat = "glass_lit" if rng.random() < 0.22 else "glass"
    for ei in range(4):
        if ei == w["inner"]:
            continue                          # runs into the range's own wall
        a, b = wall_pts[ei], wall_pts[(ei + 1) % 4]
        fr = _edge_frame(a, b, cen)
        if fr is None or fr[3] < 0.6:
            continue
        mid, ex, out_n, ln = fr
        ops = []
        nwin = max(1, int(round(float(st.get("windows", 1.8)) * ln / 12.0)))
        cls = "standard" if st.get("wealth", 0.4) > 0.45 else "small"
        ww, hh = WIN_SIZES[cls]
        for a_pos in _spread(ln, nwin, rng, margin=0.85):
            if h - (0.98 + hh) < 0.25:
                continue
            ops.append((a_pos, 0.98 + hh * 0.5, ww + 0.22, hh + 0.24))
        depth = (WALL_T * 0.8) if kind == "timber" else WALL_T
        seg = M.Group()
        seg.add(wall_run(f"{plan['id']}.wing.e{ei}", ln, h, kind, st["frame"],
                         ops, mats=WALL_MAT.get(kind), detail=detail))
        wmat = WALL_MAT.get(kind, ("plaster",))[0]
        if detail == 0:
            for op in ops:
                seg.add(_reveal_ring(op[0], op[1], op[2], op[3],
                                     -depth * 0.5 - 0.012, 0.085, wmat))
            sp = M.box(ln - 0.02, 0.17, depth + 0.028, 0.01,
                       "plaster_shade" if kind == "timber" else "rubble")
            sp.translate(0, 0.085, 0)
            seg.add(sp)
        _place_run(seg, mid, ex, -out_n)
        seg.translate(0, floor_y, 0)
        g.add(seg)
        for (oa, oy, ow, oh) in ops:
            wx, wz = _world_on_run(mid, ex, oa)
            mid_id, _wh, proto = _window_proto(
                "standard" if ow > 0.95 else "small",
                int(rng.integers(0, 3)), glass_mat)
            yaw = _yaw_for(out_n)
            ctx.instance(mid_id, proto, [(wx - out_n[0] * 0.02, floor_y + oy,
                                          wz - out_n[1] * 0.02, yaw)])
            plan.setdefault("backings", []).append(
                (wx - out_n[0] * 0.34, floor_y + oy, wz - out_n[1] * 0.34,
                 yaw, ow, oh))

    # How far the plate laps back into the range is the wing's own choice, so a
    # lap that leaves too little roof standing is retried shorter rather than
    # failing the build. Only the LAP is negotiable: if the wing cannot be
    # roofed at all the wing is dropped, never shipped open.
    roof = None
    for shrink in (1.0, 0.55, 0.25):
        poly = w["plate_poly"] if shrink >= 1.0 else _lap_shrunk(w, shrink)
        plate = wall_plate(poly, plate_y, edges=w["edges"], thickness=WALL_T,
                           wall_mat=WALL_MAT.get(kind, ("plaster",))[0])
        try:
            roof = roof_from_plate(plate, "gable", plan["pitch"],
                                   plan["overhang"] * 0.85,
                                   f"{plan['id']}.wing",
                                   mat=plan["roof_mat"], timber_mat="oak_dark",
                                   detail=detail, ridge_axis=w["ridge_axis"],
                                   clip_against=main_roof)
            break
        except R.RoofTooSmall:
            continue
    if roof is None:
        return None
    g.add(roof)
    plan["wing_roof"] = roof

    # Lead in the valley. A valley IS the edge the clip cut, so it can be found
    # exactly rather than guessed at: it is any edge of a wing slope whose two
    # ends both stand over the main roof. Nothing else about the wing's outline
    # does. Without the flashing the two planes just meet on a line, and that
    # line is the one junction rain actually finds.
    if detail == 0:
        for sl in roof.slopes:
            poly = sl.poly2
            for i in range(len(poly)):
                p0, p1 = poly[i], poly[(i + 1) % len(poly)]
                q0, q1 = sl.p3(*p0), sl.p3(*p1)
                if main_roof.surface_y(q0[0], q0[2], pad=0.06) is None:
                    continue
                if main_roof.surface_y(q1[0], q1[2], pad=0.06) is None:
                    continue
                ln = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
                if ln < 0.35:
                    continue
                lead = M.box(ln, 0.30, 0.03, 0.004, "lead")
                lead.rotate_z(math.atan2(p1[1] - p0[1], p1[0] - p0[0]))
                M.place(lead, sl.p3((p0[0] + p1[0]) * 0.5,
                                    (p0[1] + p1[1]) * 0.5, roof.cover_t + 0.012),
                        sl.du, sl.ds, sl.n)
                g.add(lead)
    return roof


def _backings(g, plan):
    """A dark panel behind every aperture.

    Without one, a window on the near wall shows daylight through the window on
    the far wall and the building reads as a shell — the same defect the kit's
    solid infill used to cause, arriving from the other side.

    A full inverted room shell does the job too, and that is what this was
    first. It had to go: the interior surface of a 9 x 8 m house is ~330 m2 of
    dark timber against ~180 m2 of roof, so the LOD impostor — which collapses
    a building to its two largest materials — chose oak over terracotta and the
    whole town went brown from the air while every close-up showed a red roof.
    Backing panels are 4% of the area and read identically through an opening.
    """
    for (x, y, z, yaw, w, h) in plan.get("backings", []):
        p = M.box(w + 0.30, h + 0.30, 0.05, 0.006, "oak_dark")
        p.rotate_y(yaw)
        p.translate(x, y, z)
        g.add(p)


# -- 4. chimneys and dormers -------------------------------------------------

def _chimneys(g, plan, roof, rng, detail):
    """Stacks sized to the storeys they serve, emerging THROUGH the roof."""
    st = plan["style"]
    n = int(st.get("chimneys", 1))
    if plan["kit"] in ("shed", "warehouse") and not plan["note"]:
        n = 0
    if n <= 0:
        return
    fp = plan["footprint"]
    hw, hd = fp.half
    # Spread along the ridge, not two hard-coded spots: the old form placed
    # `i == 0` at one end and everything else at the other, so any count above
    # two stacked N-1 flues in the same place. A terrace needs one per dwelling
    # marching down the ridge, and that is what makes a row read as houses.
    spots = []
    for i in range(n):
        t = (i + 0.5) / n
        j = float(rng.uniform(-0.055, 0.055))
        if plan["ridge_axis"] == "u":
            spots.append(((-hw + 2 * hw * t) * 0.88 + j * hw,
                          float(rng.uniform(-0.12, 0.12)) * hd))
        else:
            spots.append((float(rng.uniform(-0.15, 0.15)) * hw,
                          (-hd + 2 * hd * t) * 0.88 + j * hd))
    # Section scales with the storeys the flue serves: a 3-storey stack is
    # visibly heavier than a cottage's, which is most of what tells them apart
    # on a skyline.
    sec = 0.52 + 0.09 * plan["storeys"]
    for i, (a, b) in enumerate(spots):
        x, z = fp.world(a, b)
        stack, top = R.chimney_through(
            roof, x, z, plan["floor_y"] - plan["plinth_h"] * 0.5,
            f"{plan['id']}.ch{i}", section=jitter(rng, sec, 0.08),
            mat="brick" if rng.random() < 0.3 else "stone",
            above=float(rng.uniform(0.7, 1.15)), detail=detail)
        g.add(stack)
        plan.setdefault("chimney_tops", []).append(top)


def _dormers(g, plan, roof, rng):
    lo, hi = plan["style"].get("dormers", (0, 0))
    n = int(rng.integers(lo, hi + 1)) if hi > lo else lo
    if n <= 0 or is_thatch(plan["roof_mat"]):
        return
    fp = plan["footprint"]
    hw, hd = fp.half
    for i in range(n):
        t = (i + 0.5) / n
        if plan["ridge_axis"] == "u":
            a = -hw + 2 * hw * t + float(rng.uniform(-0.3, 0.3))
            b = -hd * 0.55
        else:
            a = -hw * 0.55
            b = -hd + 2 * hd * t + float(rng.uniform(-0.3, 0.3))
        x, z = fp.world(a, b)
        g.add(R.dormer(roof, x, z, f"{plan['id']}.dm{i}",
                       width=float(rng.uniform(1.0, 1.3)),
                       height=float(rng.uniform(1.1, 1.35)),
                       wall_mat="plaster", glass_mat="glass"))


# -- 5. party walls ----------------------------------------------------------

def build_party_walls(ctx, plans, emit=True):
    """Every shared wall in a terrace, built ONCE, after both roofs exist.

    This is a separate pass and not part of `build_building` for a structural
    reason, and it is the same reason `core/roof.py` refuses a `y` argument: a
    party wall has no profile of its own. It is the upper envelope of the two
    roofs it separates, and a thing derived from two roofs cannot be built
    while one of them is still a guess.

    The old code built it inside the owner's `build_building`, when only the
    owner's roof existed, and approximated the neighbour with
    `ridge - pitch * |t|` — a gable at their pitch, centred on this wall. For
    `hm.slot.10.townhouse_c` the shared edge is an EAVES edge and the neighbour
    is hipped, so the approximation fabricated a raked gable rising to 9.31 m
    against a roof whose eaves is at 5.82 m: a pale slab standing in the middle
    of the slot. Asking both `Roof` objects costs one ordering constraint and
    cannot be wrong.

    Call it after every building in the terrace has been built. `plans` is the
    same dict `find_terraces` marked up.
    """
    out = M.Group()
    for key in sorted(plans):
        plan = plans[key]
        for ei, rec in sorted(plan.get("party", {}).items()):
            if not rec.get("owner"):
                continue
            other = plans.get(rec.get("other"))
            if other is None:
                continue
            if plan.get("roof") is None or other.get("roof") is None:
                raise RuntimeError(
                    f"{plan['id']}: party wall to {rec.get('other')} needs both "
                    f"roofs built first. Call build_party_walls() after the "
                    f"loop that builds the terrace, not inside it.")
            out.add(_party_wall(plan, other, rec, ei))
    if emit and out.tri_count:
        ctx.emit(out, label=None, container=None)
    return out


def _party_wall(pa, pb, rec, ei):
    """One shared wall: on the mid-line, thick enough to bear on both.

    Three things the art-director pass rejected, and what each becomes:

    **It did not close.** The wall was 0.36 m thick and centred on the OWNER's
    footprint edge, so it reached 0.18 m from that face — while both neighbours
    skipped the shared edge entirely. Measured gaps run to 0.437 m, so six of
    nine terraces had an open full-height slot with up to 0.26 m of daylight
    straight into the neighbour's interior. It now sits on the mid-line and is
    `gap + 2 x PARTY_BEARING` thick, so it beds 0.20 m into each neighbour's
    plan whatever the gap is, and the neighbours build the stretches of their
    own edges it does not reach (`_edge_runs`).

    **It guessed the profile.** Now taken from `max(roofA.surface_y,
    roofB.surface_y)` sampled just clear of each face, so an eaves-against-hip
    junction produces the low parapet it should and a gable-against-gable
    produces the raked gable it should — from the same code.

    **It read as a dark strip, not as masonry.** The coping is laid as
    individual stones on a drip course, standing `PARTY_PROUD` above whichever
    roof is higher, and it returns past both facades as a shallow pier. That
    projection is what makes a terrace read as one built run from the street.
    """
    rng = rng_for(pa["id"], "party", ei)
    ra, rb = pa["roof"], pb["roof"]
    line = rec.get("line")
    if not line:
        pts = pa["footprint"].rect()
        line = (pts[ei], pts[(ei + 1) % 4])
    p0 = np.asarray(line[0], float)
    p1 = np.asarray(line[1], float)
    d = p1 - p0
    ln = float(np.hypot(d[0], d[1]))
    if ln < 0.6:
        return M.Group()
    u = d / ln
    nrm = np.array([-u[1], u[0]])
    ca = np.asarray(pa["footprint"].centre, float)
    if float((ca - p0) @ nrm) < 0:
        nrm = -nrm                      # +nrm now points into neighbour A
    mid = (p0 + p1) * 0.5

    t = max(0.34, float(rec.get("gap", 0.0)) + 2.0 * PARTY_BEARING)
    base = min(pa["base_y"], pb["base_y"])
    # Return past both facades: the pier is how a terrace shows its party walls
    # on the street elevation, and without it the join is invisible from the
    # one place a player actually stands.
    ext = 0.12
    half = ln * 0.5 + ext
    probe = t * 0.5 + 0.10
    n = max(10, int(ln / 0.40))
    prof = []
    for k in range(n + 1):
        tt = -half + 2.0 * half * k / n
        p = mid + u * tt
        ya = ra.surface_y(p[0] + nrm[0] * probe, p[1] + nrm[1] * probe, pad=0.14)
        yb = rb.surface_y(p[0] - nrm[0] * probe, p[1] - nrm[1] * probe, pad=0.14)
        y = max(pa["plate_y"], pb["plate_y"])
        if ya is not None:
            y = max(y, ya)
        if yb is not None:
            y = max(y, yb)
        prof.append((tt, y + PARTY_PROUD))

    grp = M.Group()
    poly = [(tt, base) for tt, _y in prof] + [(tt, y - 0.155) for tt, y in reversed(prof)]
    wall = M.prism([(float(a), float(b)) for a, b in poly], t, chamfer=0.0)
    grp.add(wall.with_material("rubble"))

    # Drip course, then the coping stones on it. Two members, not one slab:
    # the shadow the drip throws is the whole reason a coping reads as masonry
    # at 12 m, and it is what the old single prism at `uv_scale=0.6` — a grey
    # chequerboard on a 0.36 m member — could never do.
    drip = [(tt, y - 0.155) for tt, y in prof] + \
           [(tt, y - 0.105) for tt, y in reversed(prof)]
    dr = M.prism([(float(a), float(b)) for a, b in drip], t + 0.20, chamfer=0.010)
    grp.add(dr.with_material("sandstone"))

    stones = M.Group()
    k = 0
    while k < len(prof) - 1:
        step = 2 if len(prof) > 24 else 1
        j = min(k + step, len(prof) - 1)
        (t0, y0), (t1, y1) = prof[k], prof[j]
        seg = math.hypot(t1 - t0, y1 - y0)
        if seg > 0.08:
            h = 0.15 + (0.02 if (k // max(step, 1)) % 2 else 0.0)
            st = M.box(seg * 0.98, h, t + 0.15, 0.014, "ashlar")
            st.rotate_z(math.atan2(y1 - y0, t1 - t0) + float(rng.uniform(-0.012, 0.012)))
            st.translate((t0 + t1) * 0.5, (y0 + y1) * 0.5 - 0.075 +
                         float(rng.uniform(-0.006, 0.006)), 0.0)
            stones.add(st)
        k = j
    grp.add(stones)

    M.place(grp, np.array([mid[0], 0.0, mid[1]]),
            np.array([u[0], 0.0, u[1]]), np.array([0.0, 1.0, 0.0]),
            np.array([nrm[0], 0.0, nrm[1]]))

    # Lead soakers, following each roof's real surface into the wall face
    # rather than sitting on a single guessed plate level.
    for sgn, roof in ((1.0, ra), (-1.0, rb)):
        b = M._Builder()
        prev = None
        for k in range(n + 1):
            tt = -half + 2.0 * half * k / n
            p = mid + u * tt
            q = p + nrm * (sgn * probe)
            y = roof.surface_y(q[0], q[1], pad=0.14)
            if y is None:
                prev = None
                continue
            inner = p + nrm * (sgn * (t * 0.5 - 0.01))
            outer = p + nrm * (sgn * (t * 0.5 + 0.26))
            cur = (np.array([inner[0], y + 0.015, inner[1]]),
                   np.array([outer[0], y + 0.005, outer[1]]))
            if prev is not None:
                quad = [prev[0], prev[1], cur[1], cur[0]]
                if sgn < 0:
                    quad = quad[::-1]
                b.poly(quad, None, np.array([0.0, 1.0, 0.0]))
            prev = cur
        m = b.build("lead")
        if m.tri_count:
            grp.add(m)
    return grp


# -- 6. the defect and the residue -------------------------------------------

def _defect(g, plan, roof, rng):
    """Every building has one element that is visibly wrong (Art Bible §6).

    Not damage for its own sake: each of these is a repair somebody made, which
    is what makes a building look owned rather than placed.
    """
    fp = plan["footprint"]
    hw, hd = fp.half
    kinds = ["patch", "prop", "shutter", "slump", "board", "lean"]
    if plan["sag"]:
        kinds = ["slump"]
    pick = kinds[int(rng.integers(0, len(kinds)))]
    plan["defect"] = pick

    if pick == "patch":
        # A plaster patch in a different mix, on the weather side.
        a = float(rng.uniform(-hw * 0.5, hw * 0.5))
        x, z = fp.world(a, -hd - 0.02)
        p = M.box(float(rng.uniform(0.9, 1.7)), float(rng.uniform(0.7, 1.3)),
                  0.055, 0.02, "plaster_shade")
        p.rotate_y(math.atan2(-(-fp.V[0]), -(-fp.V[1])))
        p.translate(x, plan["floor_y"] + float(rng.uniform(0.9, 2.2)), z)
        g.add(p)
    elif pick == "prop":
        # A raking shore against a wall that started to lean. Its foot stands
        # on the ground under the foot, not on the building's datum.
        a = float(rng.uniform(-hw * 0.6, hw * 0.6))
        x, z = fp.world(a, hd + 0.05)
        run = 1.5
        fx, fz = x + fp.V[0] * run, z + fp.V[1] * run
        gy = float(T.height(fx, fz))
        h = plan["floor_y"] + plan["eaves_h"] * 0.62
        ln = math.hypot(h - gy, run)
        prop = M.box(0.16, ln, 0.16, 0.012, "oak_weathered")
        prop.rotate_x(math.atan2(run, h - gy))
        prop.rotate_y(math.atan2(fp.V[0], fp.V[1]))
        prop.translate((x + fx) * 0.5, (h + gy) * 0.5, (z + fz) * 0.5)
        g.add(prop)
        pad = M.box(0.42, 0.16, 0.42, 0.02, "stone")
        pad.translate(fx, gy + 0.06, fz)
        g.add(pad)
    elif pick == "shutter":
        # A repair reads as deliberate only when the thing it repairs is
        # visible. One green shutter alone on a facade with no other shutters
        # reads as a missing asset — which is what the art-director pass called
        # it. So the pair is hung: the SURVIVOR in the house's own joinery wood
        # and, beside it, its replacement in unmatched weathered stock, off
        # square on a single pintle. Two shutters where one is wrong is a
        # repair; one shutter where none belongs is a bug.
        wins = [b for b in plan.get("backings", []) if b[5] < DOOR_H]
        if wins:
            (bx, by, bz, yaw, ow, oh) = wins[int(rng.integers(0, len(wins)))]
            out_n = (-math.sin(yaw), -math.cos(yaw))
            tan = (-out_n[1], out_n[0])
            fx = bx + out_n[0] * 0.36
            fz = bz + out_n[1] * 0.36
            leaf = min(0.44, ow * 0.46)
            for side, mat, tilt in ((-1, "oak_dark", 0.0),
                                    (1, "oak_weathered", float(rng.uniform(0.05, 0.13)))):
                sh = M.Group()
                for i in range(3):
                    bd = M.box(leaf / 3 * 0.92, oh * 0.92, 0.030, 0.004, mat)
                    bd.translate(-leaf * 0.5 + (i + 0.5) * leaf / 3, 0, 0)
                    sh.add(bd)
                for yy in (-oh * 0.30, oh * 0.30):
                    led = M.plank(leaf * 0.94, 0.062, 0.024, 0.003, mat)
                    led.translate(0, yy, 0.026)
                    sh.add(led)
                sh.rotate_z(tilt * side)
                sh.rotate_y(yaw + side * float(rng.uniform(0.22, 0.46)))
                sh.translate(fx + tan[0] * side * (ow * 0.5 + leaf * 0.35),
                             by - oh * tilt * 0.5,
                             fz + tan[1] * side * (ow * 0.5 + leaf * 0.35))
                g.add(sh)
                # The pintle it hangs on, so the hinge side is explicable.
                for yy in (-oh * 0.34, oh * 0.30):
                    pin = M.box(0.05, 0.045, 0.13, 0.006, "iron")
                    pin.rotate_y(yaw)
                    pin.translate(fx + tan[0] * side * (ow * 0.5 + 0.04),
                                  by + yy,
                                  fz + tan[1] * side * (ow * 0.5 + 0.04))
                    g.add(pin)
    elif pick == "slump":
        # A purlin gave way. The old version added a bare box ON TOP of the
        # ridge, so the ridge simply had a lump and nothing explained it. A sag
        # is a DIP, it is patched in lead because that is the only way to keep
        # a dished ridge watertight, and the timber that is holding the wall up
        # underneath it is the part that makes the story legible from the
        # street — "a sagging purlin needs a prop under it".
        if roof.ridge_line is not None:
            a0 = np.asarray(roof.ridge_line[0], float)
            a1 = np.asarray(roof.ridge_line[1], float)
            d = a1 - a0
            ln = float(np.linalg.norm(d))
            if ln > 1.4:
                yaw = math.atan2(d[0], d[2])
                seg = min(ln * 0.42, 2.6)
                t0 = float(rng.uniform(0.22, max(0.23, 0.72 - seg / ln)))
                cen = a0 + d * (t0 + seg / ln * 0.5)
                dip = float(rng.uniform(0.10, 0.17))
                # The dished patch: below the ridge line, not above it.
                for k in range(4):
                    u = (k + 0.5) / 4.0
                    p = a0 + d * (t0 + seg / ln * u)
                    fall = math.sin(u * math.pi) * dip
                    lead = M.box(seg / 4 * 1.02, 0.05, 0.66, 0.008, "lead")
                    lead.rotate_y(yaw + math.pi * 0.5)
                    lead.rotate_z(0.0)
                    lead.translate(float(p[0]), float(p[1]) - fall - 0.02,
                                   float(p[2]))
                    g.add(lead)
                # The shore under it: foot on the ground it actually meets.
                run = 1.45
                bx, bz = float(cen[0]), float(cen[2])
                nx, nz = -fp.V[0], -fp.V[1]         # out of the front
                wx, wz = fp.world(fp.local(bx, bz)[0], -fp.half[1])
                fx, fz = wx + nx * run, wz + nz * run
                gy = float(T.height(fx, fz))
                headv = plan["floor_y"] + plan["eaves_h"] * 0.80
                lnp = math.hypot(headv - gy, run)
                shore = M.box(0.17, lnp, 0.17, 0.012, "oak_weathered")
                shore.rotate_x(-math.atan2(run, headv - gy))
                shore.rotate_y(math.atan2(nx, nz))
                shore.translate((wx + fx) * 0.5, (headv + gy) * 0.5, (wz + fz) * 0.5)
                g.add(shore)
                pad = M.box(0.44, 0.17, 0.44, 0.02, "stone", uv_scale=MATS.uv_detail("stone", 0.417, why="0.44 m member; the library's 2 m tile shows 22% of one tile here and reads as flat colour"))
                pad.translate(fx, gy + 0.06, fz)
                g.add(pad)
    elif pick == "board":
        a = float(rng.uniform(-hw * 0.5, hw * 0.5))
        x, z = fp.world(a, -hd - 0.10)
        for k in range(2):
            # Nailed ACROSS the opening: 0.19 m deep in the vertical, 28 mm
            # thick. `plank` lays a board flat, which put these in mid-air.
            bd = M.box(1.0, 0.19, 0.030, 0.005, "oak_weathered")
            bd.rotate_z(float(rng.uniform(-0.09, 0.09)))
            bd.rotate_y(math.atan2(fp.V[0], fp.V[1]))
            bd.translate(x, plan["floor_y"] + 1.35 + k * 0.28, z)
            g.add(bd)
    elif pick == "lean":
        # A lean-to shed propped against the back wall: high edge carried by
        # the wall, low edge on two posts, each post standing on the ground it
        # actually meets. Nothing here can float.
        a = float(rng.uniform(-hw, hw) * 0.6)
        w, dpt = 1.9, 1.35
        head = plan["floor_y"] + 2.25
        wall_x, wall_z = fp.world(a, hd)
        lean = M.Group()
        for sx in (-1, 1):
            px, pz = fp.world(a + sx * w * 0.5, hd + dpt)
            gy = float(T.height(px, pz))
            ph = head - 0.55 - gy
            post = M.box(0.12, ph, 0.12, 0.008, "oak_weathered")
            post.translate(px, gy + ph * 0.5, pz)
            lean.add(post)
            plate = M.box(0.10, 0.16, 0.10, 0.006, "oak_weathered")
            plate.translate(px, gy + 0.05, pz)
            lean.add(plate)
        # The roof, from the wall head down to the post heads.
        drop = 0.55
        sl = M.box(w + 0.32, 0.075, math.hypot(dpt, drop) + 0.28, 0.01,
                   "oak_weathered")
        sl.rotate_x(-math.atan2(drop, dpt))
        sl.rotate_y(math.atan2(fp.V[0], fp.V[1]))
        cx, cz = fp.world(a, hd + dpt * 0.5)
        sl.translate(cx, head - drop * 0.5, cz)
        lean.add(sl)
        g.add(lean)


def _residue(ctx, g, plan, rng):
    """Evidence somebody uses the building. Art Bible §7's highest-value detail.

    Instanced: a barrel is a barrel, and 90 of them should cost one draw call.
    """
    fp = plan["footprint"]
    hw, hd = fp.half
    kit_name = plan["kit"]
    y = plan["ground_lo"]
    picks = []
    if kit_name in ("cottage", "townhouse", "workshop"):
        picks = ["barrel", "wood", "bucket"]
    elif kit_name == "shed":
        picks = ["wood", "barrel"]
    else:
        picks = ["crate", "barrel"]
    rng.shuffle(picks)
    for name in picks[:2 + int(rng.random() < 0.4)]:
        a = float(rng.uniform(-hw * 0.8, hw * 0.8))
        b = -hd - float(rng.uniform(0.62, 1.0))
        if rng.random() < 0.5:
            b = hd + float(rng.uniform(0.62, 1.05))
        x, z = fp.world(a, b)
        # Made ground: a prop stood against a building sits on the apron the
        # building was founded on, never in the hole a pad apron cuts beside
        # it. Terrain where terrain is higher; the building's own base
        # otherwise. Without the floor, barrels stood in 0.4 m pits wherever a
        # pad edge ran past a wall.
        gy = max(float(T.height(x, z)), plan["base_y"])
        if name == "barrel":
            ctx.instance("hm.kit.prop.barrel", K.barrel("hm.kit.prop.barrel"),
                         [(x, gy, z, float(rng.uniform(0, 6.28)))])
        elif name == "crate":
            ctx.instance("hm.kit.prop.crate", K.crate("hm.kit.prop.crate"),
                         [(x, gy, z, float(rng.uniform(0, 6.28)))])
        elif name == "bucket":
            bk = M.lathe([(0.115, 0), (0.135, 0.24)], 10, "oak_weathered",
                         close_top=False)
            bk.translate(x, gy, z)
            g.add(bk)
        elif name == "wood":
            # A woodpile against the gable, out of the rain under the eaves.
            #
            # It used to stack the logs ALONG the same axis it spaced them
            # along, so every log sat end-to-end behind the one in front and
            # the pile presented a honeycomb of circular ends — read as a stack
            # of drainage pipe, which is what the art-director pass called it.
            # A real pile is cordwood: the logs lie ACROSS the face, so what
            # shows is a wall of bark with only the end row cut, and the
            # courses cross each other at the ends to keep the stack standing.
            rows = int(rng.integers(4, 6))
            depth = int(rng.integers(2, 4))
            ln = float(rng.uniform(0.36, 0.44))
            for row in range(rows):
                cross = (row % 3 == 2)          # a binding course, laid the
                per = int(rng.integers(3, 5))   # other way, as a real pile is
                for i in range(per):
                    r = float(rng.uniform(0.048, 0.082))
                    # chamfer 0: a 6-sided billet is already all facets, and
                    # rimming each end doubled the pile's triangle count for a
                    # 4 mm bevel on a log.
                    log = M.cylinder(r, ln * float(rng.uniform(0.9, 1.05)), 6,
                                     0.0, "oak_weathered")
                    log.rotate_z(math.pi * 0.5)
                    ax = math.atan2(fp.V[0], fp.V[1]) if cross else \
                        math.atan2(fp.U[0], fp.U[1])
                    log.rotate_y(ax + float(rng.uniform(-0.05, 0.05)))
                    off = (i - (per - 1) * 0.5) * (r * 2.2)
                    du = fp.V if cross else fp.U
                    dv = fp.U if cross else fp.V
                    log.translate(x + dv[0] * off + float(rng.uniform(-0.012, 0.012)),
                                  gy + r + row * 0.128,
                                  z + dv[1] * off)
                    g.add(log)
                    if depth > 2 and not cross and i < per - 1:
                        # A second rank behind, so the pile has thickness.
                        b2 = log.copy() if hasattr(log, "copy") else None
                        if b2 is not None:
                            b2.translate(du[0] * (ln * 0.92), 0.0, du[1] * (ln * 0.92))
                            g.add(b2)
            # A board over the top, weighted with a stone: how a pile is kept
            # dry, and the residue that says somebody uses it.
            cap = M.box(ln * 1.6, 0.035, 0.52, 0.006, "oak_weathered")
            cap.rotate_y(math.atan2(fp.U[0], fp.U[1]))
            cap.translate(x, gy + 0.128 * rows + 0.06, z)
            g.add(cap)
            wt = M.box(0.24, 0.15, 0.20, 0.03, "stone", uv_scale=MATS.uv_detail("stone", 0.25, why="0.24 m member; the library's 2 m tile shows 12% of one tile here and reads as flat colour"))
            wt.rotate_y(float(rng.uniform(0, 3.1)))
            wt.translate(x + fp.U[0] * 0.22, gy + 0.128 * rows + 0.15,
                         z + fp.U[1] * 0.22)
            g.add(wt)


# -- 7. collision and entities ----------------------------------------------

def _collision(ctx, plan):
    """Directive §6.4. One run per wall, doorways open, steps to the threshold."""
    fp = plan["footprint"]
    rot = -fp.theta
    w, d = fp.w, fp.d
    doors = []
    for (x, y, z, a) in plan.get("door_world", []):
        doors.append(("-z", a, DOOR_W + 0.55))
    ctx.collider("box", center=(fp.centre[0],
                                (plan["base_y"] + plan["floor_y"]) * 0.5,
                                fp.centre[1]),
                 half=(w * 0.5 + 0.10, max(0.05, plan["plinth_h"] * 0.5),
                       d * 0.5 + 0.10),
                 rot_y=rot, tag="plinth")
    ctx.collider_walls(w, d, max(1.2, plan["eaves_h"]), y=plan["floor_y"],
                       thickness=WALL_T + 0.06, center=fp.centre, rot_y=rot,
                       doors=doors, tag=f"wall.{plan['slot']}")
    if doors and plan["plinth_h"] > 0.2:
        a = doors[0][1]
        x, z = fp.world(a, -d * 0.5 - 0.06)
        ctx.collider_steps((x, plan["floor_y"] - plan["plinth_h"], z),
                           plan["plinth_h"], tread=0.34,
                           width=DOOR_W + 0.9, rot_y=rot)
    # A wing is a mass; Directive §6.4 says a mass is authored collision, not
    # inferred. It has no external door, so it is solid.
    w = plan.get("wing")
    if w:
        ctx.collider("box",
                     center=(w["centre"][0],
                             (plan["base_y"] + plan["plate_y"]) * 0.5,
                             w["centre"][1]),
                     half=(w["w"] * 0.5 + 0.10,
                           (plan["plate_y"] - plan["base_y"]) * 0.5,
                           w["d"] * 0.5 + 0.10),
                     rot_y=-w["theta"], tag=f"wing.{plan['slot']}")


def _entities(ctx, plan):
    """Architecture §2: only interactables get IDs. A door is one; a wall is not."""
    n = plan["slot"].split(".")[2] if plan["slot"].count(".") >= 2 else "00"
    arch = {"cottage": "door.cottage", "townhouse": "door.townhouse",
            "workshop": "door.workshop", "shed": "door.shed",
            "warehouse": "door.warehouse"}.get(plan["kit"], "door.cottage")
    for i, (x, y, z, _a) in enumerate(plan.get("door_world", [])):
        ctx.entity(f"hm.townhouse.door.{n}{'' if i == 0 else chr(97 + i)}",
                   arch, (x, y, z), cell=cell_of(x, z), verbs=["open"],
                   collider={"shape": "box",
                             "half": [DOOR_W * 0.5, DOOR_H * 0.5, 0.06]})


# ---------------------------------------------------------------------------
# LOD
# ---------------------------------------------------------------------------

def building_lods(ctx, slot, style=None, asset_id=None, plan=None, levels=4):
    """Generate the LOD chain for one building.

    The rule is "the same building, generated with less", not "a decimated
    mesh": LOD1 drops hardware, shutters, rafter feet and props and doubles the
    tile course exposure; LOD2 keeps the mass, the roof planes, the chimney and
    the plinth; LOD3 is the silhouette only. Because every level runs from the
    same seeded plan, the levels register exactly — which a generic decimator
    cannot promise for a roof ridge or a chimney.
    """
    plan = plan or plan_building(slot, style, asset_id)
    return [build_building(ctx, slot, style, asset_id, plan=dict(plan),
                           detail=i, emit=False) for i in range(levels)]
