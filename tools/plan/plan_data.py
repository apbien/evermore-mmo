"""Hearthmere v2 — the master plan, as data.

This module is the single source of truth for the town's geometry: the wall,
the water, the street network, the levels, and the numbered schedule of every
building slot. `docs/areas/hearthmere/TOWN_PLAN.md`, `docs/areas/hearthmere/plan/hearthmere-plan.svg` and
`content/town/hearthmere.json` are all generated from it by `townplan.py`, so
they cannot drift apart.

Coordinate contract (docs/areas/hearthmere/BUILD_DIRECTIVE.md §2, LOCKED):
    12 x 12 cells of 16 m. Columns A-L west->east, rows 1-12 north->south.
    World origin (0,0,0) is the market square fountain, at the grid centre.
    x in [-96,+96], z in [-96,+96]. Y-up, 1 unit = 1 m, -Z is north.

Facing convention, taken from the v1 town file and the renderers:
    forward = (sin(rot), 0, -cos(rot))
    rot   0 -> faces north (-Z)      rot  90 -> faces east  (+X)
    rot 180 -> faces south (+Z)      rot 270 -> faces west  (-X)
A slot's `w` runs along its frontage, `d` runs back into the plot from the
frontage. The front face therefore sits at centre + forward * d/2.
"""

from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                "../assetgen")))
from core import terrain as TERRAIN          # noqa: E402

# --------------------------------------------------------------------------
# Grid
# --------------------------------------------------------------------------

CELL = 16.0
COLS = list("ABCDEFGHIJKL")
ROWS = list(range(1, 13))
EXTENT = 96.0


def cell_of(x: float, z: float) -> str:
    ci = int(math.floor(x / CELL)) + 6
    ri = int(math.floor(z / CELL)) + 7
    ci = max(0, min(11, ci))
    ri = max(1, min(12, ri))
    return f"{COLS[ci]}{ri}"


# --------------------------------------------------------------------------
# Levels — NOT AUTHORED HERE
# --------------------------------------------------------------------------
# Datum: Y = 0.00 is the market-square paving at the fountain kerb (0,0).
#
# This module used to carry its own height model: a south-to-north base
# profile plus a Gaussian rise called Kirk Knowe. `core/terrain.py` carried a
# different one, and D-022 measured the disagreement — venue origins 0.02 to
# 1.48 m out, street paths out by up to 1.24 m, and two water surfaces 0.20 m
# apart. D-024 settles it: `content/town/terrain.json` is the ground, this is
# the layout, and the layout asks the ground for its levels.
#
# So `height` is a one-line forward. Everything downstream — the plan drawing,
# the schedule, the checker and content/town/hearthmere.json — now reads the
# same function the client and every generator read, and the drift is zero by
# construction rather than by anybody remembering to re-derive it.
#
# What went with the old model: Kirk Knowe. The plan's church still wants its
# floor 2.40 m above the market place and gets it from a plinth and a perron
# rather than from a hill. That is D-020's open question and it is still open.

def height(x: float, z: float) -> float:
    """Ground level, from the one authoritative height field."""
    return float(TERRAIN.height(float(x), float(z)))


def water_y() -> float:
    """The single water-surface elevation for the whole system."""
    return float(TERRAIN.water_level())


WATER_Y = water_y()


# Named levels the plan is dimensioned from and the checker tests.
#
#   y is None      -> a natural ground level; the value IS whatever terrain
#                     says, and townplan.py fills it in. There is nothing to
#                     disagree about, so nothing can drift.
#   y is a number  -> a MADE level: a floor, a deck, a tread, a made-up
#                     surface. The building owns it, terrain does not, and the
#                     checker asserts only that it stands clear of the ground
#                     underneath and not absurdly far above it.
SPOT_LEVELS = [
    ("fountain kerb — DATUM",        0.0,    0.0,   None, "paving"),
    ("square, north mouth",          0.0,  -24.0,   None, "paving"),
    ("square, south mouth",          0.0,  +18.0,   None, "paving"),
    ("square, west kerb",          -24.0,   -2.0,   None, "paving"),
    ("Market Step, upper tread",    -8.0,   +1.6,  +0.48, "step"),
    ("Market Step, lower tread",    -8.0,   -0.4,  +0.16, "step"),
    ("Ford Road at Kirk Green",     +9.5,   -0.5,   None, "paving"),
    ("Kirk Green paving",          +19.0,   -0.5,   None, "made"),
    ("church perron, foot",        +24.0,   -0.5,   None, "made"),
    ("church perron, head",        +32.0,   -0.5,  +2.40, "made"),
    ("church floor / altar plinth", +43.0,   -0.5,  +2.40, "floor"),
    ("guild forecourt",            -25.0,   +5.0,  +0.42, "made"),
    ("inn threshold",              -26.0,  -20.0,  -0.60, "floor"),
    ("moot hall threshold",        -24.0,  +17.0,  +1.35, "floor"),
    ("Ferryman's Lamp floor",      +19.0,  -68.0,  -2.40, "floor"),
    ("Wharf Lane at the pub",      +19.0,  -63.0,   None, "paving"),
    ("blacksmith yard platform",   -31.0,  +57.0,  +1.82, "made"),
    ("south gate threshold",        +1.0,  +78.5,   None, "paving"),
    ("north gate threshold",        -2.4,  -76.0,   None, "paving"),
    ("bridge deck, crown",          -3.7,  -86.0,  -0.90, "deck"),
    ("west gate threshold",        -79.0,  -13.0,   None, "paving"),
    ("water gate threshold",       +50.0,  -57.0,   None, "paving"),
    ("wharf deck",                 +58.0,  -60.0,   None, "deck"),
    ("wharf lower stage",          +64.8,  -68.9,  -2.85, "deck"),
    ("harbour bed at the quay face", +64.5, -68.5,  None, "water"),
    ("Emberflow / Mere surface",    0.0,  -95.0, WATER_Y, "water"),
]


# --------------------------------------------------------------------------
# Water — NOT AUTHORED HERE EITHER
# --------------------------------------------------------------------------
# The Emberflow runs west->east across the north and widens into the Mere in
# the north-east. Its shape lives in `content/town/terrain.json` under
# `water.channels`, because the water IS the ground: the same height field
# that carves the channel is the one the client walks on. The plan used to
# carry a second, incompatible polygon; D-024 deleted it and moved the terrain
# to meet the layout instead.
#
# What the plan still owns is where the town MEETS the water — the wharf, and
# the lot the old ford occupies — because those are urban design, not
# hydrology, and they are what the shoreline in terrain.json was solved to.

# The wharf: a stone-faced platform 26 x 16 m projecting from the Water Gate
# out into the mere. Its landward edge runs along the wall; the opposite edge
# is the quay face, and terrain.json's authored shoreline runs along it, so a
# moored lighter lies against the stonework.
WHARF = [(+42.75, -66.63), (+60.09, -47.21), (+72.04, -57.88), (+54.70, -77.30)]

# The silted ford beside the bridge — a shelving gravel bar with 0.45 m of
# water over it, 16 m east of the bridge. Matches `hm.water.ford`.
FORD_BAR = [(+7.0, -79.5), (+14.0, -78.8), (+19.0, -83.0), (+19.0, -93.0),
            (+13.0, -96.0), (+7.0, -92.0)]


# --------------------------------------------------------------------------
# Wall
# --------------------------------------------------------------------------
# Low, thick, and a customs boundary rather than a defence. 6.0 m to the
# wall-walk, 1.2 m parapet above that. Follows the river on the north and the
# contour elsewhere, so it is an irregular oval, never a square.
#
# THE TOWERS ARE OLDER THAN THE WALL, and that is why they are twice its
# height (D-047). Hearthmere had a burh enclosure — a ditch, a bank and a ring
# of stone turrets — three hundred years before it had a customs boundary.
# The bank went; the turrets were too useful and too expensive to pull down,
# so when the town walled itself for tolls rather than for war it strung a low
# curtain BETWEEN the old turrets and re-roofed the ones still worth roofing.
# The wall therefore stays canonically low (WORLD_BIBLE: "more customs
# boundary than defence") while the profile gets the rhythm of eleven vertical
# events along the town's edge that ad-town-04 §(b) says it has none of. Two
# turrets were never re-roofed and stand open, which is the tell that the
# roofs are a later repair and not part of one design.

WALL = [
    (-2.4, -76.0),  (+10.0, -75.6), (+20.0, -74.4), (+28.0, -72.4),
    (+34.0, -70.0), (+40.0, -66.8), (+45.0, -62.6), (+50.0, -57.0),
    (+55.0, -51.4), (+60.0, -43.4), (+66.0, -35.0), (+71.0, -29.0),
    (+75.0, -20.0), (+77.5, -8.0),  (+78.0, +5.0),  (+77.0, +20.0),
    (+75.0, +34.0), (+70.0, +48.0), (+62.0, +60.0), (+50.0, +69.0),
    (+34.0, +74.5), (+18.0, +77.6), (+1.0, +78.5),  (-14.0, +78.0),
    (-30.0, +75.6), (-45.0, +71.0), (-58.0, +64.0), (-68.0, +53.0),
    (-75.0, +39.0), (-79.0, +23.0), (-80.0, +7.0),  (-79.4, -6.0),
    (-79.0, -13.0), (-78.0, -26.0), (-75.0, -40.0), (-70.0, -52.0),
    (-62.0, -62.0), (-52.0, -68.6), (-38.0, -73.2), (-24.0, -75.4),
    (-12.0, -76.2),
]
# The north-east stretch is the town's strongest silhouette from a boat:
# ...and from the Crane Tower round to the Heron Tower it runs within a few
# metres of the mere, with the berm and Tan Road on the strip between. It used
# to be authored as WALL_IN_WATER, on the claim that the wall's outer face IS
# the shoreline there. It cannot be: Tan Road runs outside the wall on exactly
# that stretch, 1.5-3.2 m from its face, so a shoreline on the wall would put a
# road under water. D-024.
WALL_NEAR_WATER = ((+45.0, -62.6), (+66.0, -35.0))
WALL_IN_WATER = WALL_NEAR_WATER      # retired alias; nothing new should use it

# kind: gate (carriage), postern (foot), water (quay)
GATES = [
    dict(id="hm.wall.gate.north", name="North Gate", kind="gate", pos=(-2.4, -76.0),
         rot=0, clear=4.2, head=5.0,
         note="Ford Road and the bridge. Twin drum towers, 12.8 m overall, "
              "spur stones scored by nave hubs, the town's heron carved on "
              "the keystone. Departure and return frame."),
    dict(id="hm.wall.gate.south", name="South Gate", kind="gate", pos=(+1.0, +78.5),
         rot=180, clear=4.0, head=4.8,
         note="Ford Road climbing away to the quest zones. Single square "
              "gatehouse, 10.5 m, ward's chamber over the arch."),
    dict(id="hm.wall.gate.west", name="West Gate", kind="gate", pos=(-79.0, -13.0),
         rot=270, clear=3.8, head=4.6,
         note="Mere Street to the west pastures. The oldest gate, its arch "
              "settled 0.2 m out of plumb and pinned with iron cramps."),
    dict(id="hm.wall.gate.water", name="Water Gate", kind="water", pos=(+50.0, -57.0),
         rot=42, clear=4.6, head=5.4,
         note="Wharf Lane onto the wharf. Wide cart arch with a portcullis "
              "groove never fitted, plus a 1.6 m boat wicket at the north "
              "jamb. A 0.8 m ramp inside the arch takes the drop to the deck, "
              "with a cart-brake groove worn 60 mm into the threshold stone."),
    dict(id="hm.wall.postern.mill", name="Mill Postern", kind="postern", pos=(-46.5, -71.6),
         rot=315, clear=2.2, head=2.9,
         note="Mill Lane to the watermill on its platform in the bank. Foot "
              "and handcart only."),
    dict(id="hm.wall.postern.ferry", name="Ferry Postern", kind="postern", pos=(+17.0, -74.9),
         rot=0, clear=1.9, head=2.6,
         note="The old ferry stair, behind the Ferryman's Lamp. The stair is "
              "still there; the ferry has not run since the bridge was built."),
    dict(id="hm.wall.postern.east", name="East Postern", kind="postern", pos=(+78.0, +4.0),
         rot=90, clear=2.0, head=2.7,
         note="Onto the orchard and the graveyard extension. Kept locked at dusk."),
]

# Towers: the old burh turrets. Semicircular, 5.6 m external, projecting 3.4 m;
# the two angle turrets are square. Heights are individually authored, never a
# constant, because a ring of identical towers is a fence with bumps on it —
# ad-town-04 measured the old uniform 8.9 m as "2.6 m proud of a 6.3 m curtain"
# and the profile read as a ribbon. `roof`:
#   cone     conical slate spire, the usual repair
#   pyramid  a squat slate pyramid, on the two square angle turrets
#   open     never re-roofed: an open crown with a wall-head and a self-sown
#            ash in it. Two of these, and they are what stops eleven cones
#            reading as a kit.
TOWERS = [
    dict(id="hm.wall.tower.01", name="Mill Tower",      pos=(-52.0, -68.6), shape="round",
         height=13.6, roof="cone"),
    dict(id="hm.wall.tower.02", name="Bridgefoot Tower", pos=(-12.0, -76.2), shape="round",
         height=15.8, roof="cone",
         note="Flanks the North Gate on the departure frame, so it is the "
              "tallest of the drums and carries a weathervane."),
    dict(id="hm.wall.tower.03", name="Ferry Tower",     pos=(+20.0, -74.4), shape="round",
         height=12.8, roof="cone"),
    dict(id="hm.wall.tower.04", name="Crane Tower",     pos=(+45.0, -62.6), shape="round",
         height=15.2, roof="cone",
         note="The waterfront anchor beside the Water Gate; reads from the "
              "Mere with the crane."),
    dict(id="hm.wall.tower.05", name="Heron Tower",     pos=(+66.0, -35.0), shape="square",
         height=18.4, roof="pyramid",
         note="The north-east angle. The town's profile from a boat is this "
              "turret, the crane and the church spire, in that order."),
    dict(id="hm.wall.tower.06", name="Orchard Tower",   pos=(+77.0, +20.0), shape="round",
         height=11.4, roof="open",
         note="Never re-roofed. Open crown, an ash growing out of it, and the "
              "orchard has been allowed up to its foot."),
    dict(id="hm.wall.tower.07", name="Cinder Tower",    pos=(+62.0, +60.0), shape="round",
         height=14.0, roof="cone"),
    dict(id="hm.wall.tower.08", name="Southgate Tower", pos=(-30.0, +75.6), shape="round",
         height=15.0, roof="cone"),
    dict(id="hm.wall.tower.09", name="Tenter Tower",    pos=(-68.0, +53.0), shape="square",
         height=17.2, roof="pyramid"),
    dict(id="hm.wall.tower.10", name="Spring Tower",    pos=(-80.0, +7.0),  shape="round",
         height=10.6, roof="open",
         note="Robbed with the garden stretch beside it. The lowest thing on "
              "the circuit and the reason the west profile dips."),
    dict(id="hm.wall.tower.11", name="Pasture Tower",   pos=(-78.0, -26.0), shape="round",
         height=13.2, roof="cone"),
]

# Mural stairs up to the wall-walk.
WALL_STAIRS = [(-6.0, -74.6), (+52.5, -53.0), (+74.5, +22.0),
               (-6.0, +76.6), (-79.4, -6.0)]


# --------------------------------------------------------------------------
# Streets
# --------------------------------------------------------------------------
# `path` is the carriageway centreline. Width is kerb-to-kerb. A slot may not
# come closer to a centreline than width/2 + verge; that clearance is the
# footway, and the checker enforces it.

STREETS = [
    dict(id="ford_road", name="Ford Road", width=7.0, verge=1.2, surface="granite setts",
         cls="primary",
         # The one stretch of carriageway in Hearthmere that is over water: the
         # Emberflow bridge, between the south abutment on the gate flat and
         # the north abutment on its causeway. Given as a z interval on the
         # road, so the "no water on a road" check can exempt exactly this and
         # nothing else.
         bridged=[-95.0, -78.0],
         note="The spine, and the reason the town exists. Runs straight down "
              "the fall line, so it drains and so carts can brake. Worn to a "
              "shallow trough down the centre; kerbed both sides with a deep "
              "gutter on the east where the run-off goes. It bends twice: "
              "east round the old waggon yard, then east again round the "
              "market place, because the market place was there first.",
         path=[(-4.0, -96.0), (-4.0, -89.0), (-3.4, -80.5), (-2.4, -76.0),
               (-1.6, -68.0), (-0.6, -60.0), (+0.6, -52.0), (+2.0, -44.0),
               (+3.8, -36.0), (+5.6, -28.0), (+7.4, -20.0), (+8.8, -11.0),
               (+9.5, -2.0), (+9.2, +6.0), (+8.0, +16.0), (+6.6, +28.0),
               (+5.2, +40.0), (+3.8, +52.0), (+2.4, +64.0), (+1.4, +73.0),
               (+1.0, +78.5), (+0.6, +88.0), (0.0, +96.0)]),

    dict(id="mere_street", name="Mere Street", width=6.0, verge=1.0, surface="cobble",
         cls="primary",
         note="The contour road, and older than Ford Road: it is the drove "
              "track to the mere-side pastures and it holds the -0.3 m "
              "contour for its whole length, which is why it is the only "
              "level street in Hearthmere and why the carters use it.",
         path=[(+9.2, -8.5), (0.0, -10.0), (-12.0, -12.5), (-24.0, -14.0),
               (-38.0, -13.0), (-50.0, -12.0), (-62.0, -11.5), (-72.0, -12.4),
               (-79.0, -13.0)]),

    dict(id="kirk_green", name="Kirk Green", width=10.0, verge=1.0, surface="squared cobble",
         cls="primary",
         note="Not a street so much as the church's forecourt, driven west "
              "through the burgage plots when the perron was rebuilt. It is "
              "the arrival axis: church door, perron, green, Ford Road, "
              "market place, fountain.",
         path=[(+24.0, -0.5), (+19.0, -0.5), (+13.5, -0.5)]),

    dict(id="wharf_lane", name="Wharf Lane", width=5.5, verge=1.0, surface="granite setts",
         cls="secondary",
         note="The bulk-goods road: everything that arrives by water crosses "
              "it. Setts laid on edge to take iron tyres, kerbs 0.22 m high, "
              "gutters wide enough to lose a boot in.",
         path=[(-0.8, -61.0), (+10.0, -62.0), (+22.0, -62.4), (+32.0, -61.0),
               (+40.0, -59.5), (+46.0, -58.5), (+50.0, -57.0)]),

    dict(id="mill_lane", name="Mill Lane", width=4.5, verge=0.8, surface="gravel, stone edged",
         cls="secondary",
         note="Runs along the inside of the north wall to the mill postern. "
              "Flour-dusted for its last thirty metres and rutted the rest.",
         path=[(-1.2, -63.4), (-12.0, -65.4), (-24.0, -67.2), (-34.0, -69.0),
               (-42.0, -70.8), (-46.0, -71.6)]),

    dict(id="kirkgate", name="Kirkgate", width=5.0, verge=1.0, surface="cobble",
         cls="secondary",
         note="Links the waterfront to the church, along the churchyard's west "
              "wall. A steady climb the whole way — the grade a coffin bearer "
              "can manage and a laden cart cannot, so carts go round by Ford "
              "Road; length and gradient are the street table's, measured "
              "from the height field. No steps in the run: the six steps are "
              "at the churchyard's north gate, beyond its end, and there is "
              "no cart way through.",
         path=[(+26.0, -62.4), (+27.0, -52.0), (+27.5, -40.0), (+27.5, -28.0),
               (+27.0, -21.0)]),

    dict(id="bakers_row", name="Bakers' Row", width=4.5, verge=0.9, surface="cobble, worn to dust",
         cls="secondary",
         note="The fire lane. Every trade on it burns something — oven, "
              "tallow pan, glue pot, charcoal — and the wall is 20 m "
              "downwind of the last of them.",
         path=[(+7.4, +22.0), (+18.0, +23.6), (+30.0, +24.8), (+42.0, +25.5),
               (+53.0, +25.0), (+62.0, +23.5)]),

    dict(id="smiths_lane", name="Smiths' Lane", width=4.0, verge=0.8, surface="dirt and cinder",
         cls="secondary",
         note="Paved for 12 m off Ford Road and then not paved at all. The "
              "surface change is the junction: past it the lane is black "
              "cinder rolled hard, and it narrows to 3.2 m at the yard gate.",
         path=[(+3.4, +53.0), (-8.0, +55.4), (-18.0, +58.0), (-23.0, +59.0)]),

    dict(id="well_lane", name="Well Lane", width=4.0, verge=0.8, surface="cobble",
         cls="secondary",
         note="Runs from the market place to the well-house and the spring "
              "head under the west wall. The conduit that feeds the fountain "
              "is buried under its crown; the manhole slabs are the only "
              "dressed stone in the surface.",
         path=[(-27.0, +18.5), (-36.0, +20.0), (-46.0, +21.0), (-56.0, +21.5)]),

    dict(id="the_bailey", name="The Bailey", width=4.5, verge=0.6, surface="gravel and grass",
         cls="secondary",
         note="The intramural lane. Never planned, simply what was left when "
              "the wall went up outside the back fences. Gives every wall "
              "stair, every back plot and every midden its access, and it is "
              "where the town keeps its woodpiles.",
         path=[(-52.0, -60.0), (-60.0, -53.0), (-66.0, -45.0), (-70.0, -36.0),
               (-72.5, -24.0), (-74.0, -12.0), (-74.5, +2.0), (-73.5, +18.0),
               (-70.0, +33.0), (-64.5, +46.0), (-56.5, +57.0), (-46.0, +65.0),
               (-32.0, +70.0), (-18.0, +72.4), (-4.0, +73.4), (+10.0, +72.8),
               (+24.0, +70.6), (+36.0, +66.4), (+49.0, +62.0), (+58.0, +53.0),
               (+65.0, +40.0), (+70.0, +28.0), (+72.0, +15.0), (+72.5, +2.0),
               (+72.5, -12.0), (+70.5, -24.0)]),

    dict(id="tenter_lane", name="Tenter Lane", width=3.0, verge=0.4, surface="dirt",
         cls="lane",
         note="South off Well Lane to the tenter ground, where cloth is "
              "stretched to dry. Ends in the frames, which is worth walking "
              "toward when they are full.",
         path=[(-30.0, +24.0), (-30.0, +30.0), (-30.0, +36.0)]),

    dict(id="bell_alley", name="Bell Alley", width=2.5, verge=0.25, surface="beaten earth",
         cls="alley",
         note="The back lane behind the Ford Road frontage. Laundry across "
              "it at first-floor height, privies at the far ends of the "
              "plots, and never dry.",
         path=[(-17.0, +31.0), (-17.6, +41.0), (-18.2, +52.0)]),





    dict(id="sty_lane", name="Sty Lane", width=3.0, verge=0.4, surface="beaten earth",
         cls="lane",
         note="The back lane of the fire quarter, serving the yards, the "
              "sawpit, the sties and the privies. Ends at the wall stair "
              "under the Cinder Tower and the midden beyond it.",
         path=[(+4.6, +45.0), (+16.0, +45.6), (+28.0, +45.6), (+40.0, +44.4),
               (+50.0, +42.4)]),

    dict(id="tan_road", name="Tan Road", width=4.0, verge=0.8, surface="dirt, tan-black",
         cls="lane", outside=True,
         note="OUTSIDE the wall. From the Water Gate along the mere shore to "
              "the tannery. Nobody walks it who does not have to.",
         path=[(+50.0, -57.0), (+58.0, -49.0), (+64.0, -41.0), (+70.0, -34.0),
               (+75.0, -28.0)]),

    dict(id="fishers_steps", name="Fishers' Steps", width=2.5, verge=0.25, surface="stone steps",
         cls="steps",
         note="8 risers of 0.163 m in the quay face, taking the 1.30 m from "
              "the wharf deck at -1.55 down to the lower stage at -2.85. "
              "(The street table's grade column reads the terrain of the "
              "deck, so it shows the flat approach, not the drop in the "
              "wall.) Worn into a hollow on the left-hand side, because a "
              "man carrying a basket carries it on his right.",
         path=[(+51.0, -58.0), (+55.0, -62.0)]),
]


# --------------------------------------------------------------------------
# Building slots
# --------------------------------------------------------------------------
# n, id-suffix, kit, cx, cz, w, d, rot, storeys, eaves, ridge, street, role, note
#
# kit:  hero venues carry their venue module name; filler carries a kit name
#       from tools/assetgen/venues/townhouse.py etc.
# ridge: "along"  ridge parallel to the frontage (eaves to the street)
#        "gable"  ridge perpendicular (gable end to the street)

S = lambda *a: a   # noqa: E731  — terse row constructor

SLOTS = [
    # -- 01-03  Market place, west frontage: the three institutions ---------
    S(1, "inn", "inn", -34.0, -26.0, 16.0, 14.0, 90, 3, 10.6, "gable", "market_square",
      "hero",
      "The Grey Heron. Tallest timber structure in town; upper floors jettied "
      "0.45 m each. Gable to the square so the sign hangs over the paving. "
      "Four dormers on the east slope, two chimneys, stable yard behind."),
    S(2, "guild", "guild", -33.0, +0.0, 16.0, 16.0, 90, 2, 8.4, "along", "market_square",
      "hero",
      "Adventurer's Guild. Dressed stone in a plaster town, symmetrical in a "
      "town where nothing is, and it bought the best block on the market "
      "place. Forecourt raised 0.42 m on a stylobate with four steps across "
      "the full frontage. Square tower on the block's NORTH-EAST corner, "
      "footprint x[-32,-25] z[-8,-1], parapet 18.6 m, pyramid roof and iron "
      "finial to 21.5 m, crimson banners on the north and east faces. That "
      "tower is the far anchor of the arrival frame: it stands just right of "
      "the fountain at 71.5 m and closes the view west."),
    S(3, "moot", "moot_hall", -16.0, +9.0, 13.0, 8.0, 60, 2, 7.2, "along", "market_square",
      "hero",
      "Moot Hall. FREE-STANDING in the market place, not on a frontage: "
      "arcaded ground floor on ten oak posts (the butter market) with the "
      "council chamber over, so the market flows under and round it. Skewed "
      "60 degrees because it was built along the old sheep-pen rail. Louvred "
      "bell-cote on the EAST gable, 15.8 m — the left-hand anchor of the "
      "arrival frame. Stands on the upper market, one step above the fountain."),

    # -- 04-06  Market place, south frontage: the shop row -----------------
    S(4, "store", "shop_row", -19.0, +23.5, 8.0, 11.0, 0, 2, 6.6, "along", "market_square",
      "secondary",
      "General store. Widest of the three, shutters that fold down into "
      "counters, goods out over the footway. Party wall east with the apothecary."),
    S(5, "apothecary", "shop_row", -11.5, +23.5, 6.0, 11.0, 0, 2, 6.6, "along", "market_square",
      "secondary",
      "Apothecary. Party walls both sides. Smallest windows, most colour "
      "behind them. Herb bundles under the eaves."),
    S(6, "tailor", "shop_row", -5.5, +23.5, 6.0, 11.0, 0, 2, 6.9, "along", "market_square",
      "secondary",
      "Tailor. Party wall west; east gable is exposed to Ford Road and is the "
      "first thing seen coming up from the south gate, so it gets the painted "
      "gable and the pole sign."),

    # -- 07-10  Market place, north frontage --------------------------------
    S(7, "chophouse", "chophouse", -21.3, -38.0, 9.4, 9.4, 180, 2, 6.4, "along",
      "market_square", "secondary",
      "Chophouse. North side, so its front is in shade all morning and its "
      "fire-light reads from across the square at 09:30 — that is why it is "
      "here and not on the sunny side. Set 5 m further back than it was: at "
      "z -28 its west corner stood 0.5 m off the inn's front plot line and "
      "covered 4.4 m of the Grey Heron's 7.4 m gable, so the town's second "
      "hero venue had no elevation from the market place at all "
      "(ad-town-04). Standing back also opens the plaza's north mouth, which "
      "is what WORLD_BIBLE says the market place does where the road enters."),
    S(8, "townhouse_a", "townhouse", -12.0, -33.0, 7.0, 10.0, 180, 2, 6.2, "along",
      "market_square", "filler", "Merchant's townhouse, shop below, hall above."),
    S(9, "townhouse_b", "townhouse", -4.5, -33.0, 6.0, 10.0, 180, 3, 8.0, "gable",
      "market_square", "filler",
      "Narrow, deep and three storeys because the frontage is the most "
      "expensive in Hearthmere. 5 m wide on a 10 m plot."),
    S(10, "townhouse_c", "townhouse", +17.3, -20.6, 4.0, 9.0, 261, 2, 7.4, "gable",
       "ford_road", "filler",
       "The infill plot: 4.0 m of frontage squeezed between its neighbour and "
       "Ford Road's kerb, skewed 10 degrees to take up the angle, and three "
       "storeys because that was the only way up. Its east gable takes the "
       "full morning sun and carries the only painted plaster panel in town."),

    # -- 11-18  Kirk Knowe ---------------------------------------------------
    S(11, "church", "church", +44.0, -0.5, 20.0, 24.0, 270, 1, 9.0, "gable", "kirk_green",
      "hero",
      "CHURCH OF SUMMONING. Aisled hall church, ridge east-west, 14.6 m to the "
      "ridge. Great west portal 6.4 m clear x 8.0 m to the arch apex, doors "
      "standing open. Floor at +2.40, altar dais +0.90 above that. Clerestory "
      "over the arcade on both sides; lantern over the altar bay. THE ARRIVAL "
      "FRAME IS AUTHORED FROM THIS BUILDING — see docs/areas/hearthmere/TOWN_PLAN.md section 7."),
    S(12, "church_tower", "church", +35.8, -14.3, 7.6, 7.6, 270, 1, 18.4, "flat",
      "kirk_green", "hero",
      "Church tower, north-west angle. Part of venue `church`. Parapet 18.4 m, "
      "lead spirelet to 21.6 m — the tallest thing in Hearthmere by 0.1 m over "
      "the guild, which the guild has never mentioned. Sited at the NORTH-west "
      "angle so its north and east faces are lit at 09:30 and it reads from "
      "the north gate and from the water."),
    S(13, "parsonage", "townhouse", +50.0, +15.5, 11.0, 9.0, 270, 2, 6.4, "along",
      "kirkgate", "filler",
      "The parsonage, inside the churchyard's south-east corner. Best garden "
      "in town, a lean-to glasshouse of leaded quarries against its south wall."),
    S(14, "bede_houses", "townhouse", +65.0, -2.4, 24.0, 8.0, 90, 1, 3.4, "along",
      "the_bailey", "filler",
      "Bede houses: six one-room almshouses under one long roof, six doors, "
      "six chimneys, no two shutters the same colour. On the Bailey under "
      "the east wall, so the old people get the morning sun over the "
      "orchard and the wall keeps the wind off their backs."),
    S(15, "song_school", "townhouse", +48.0, -18.0, 10.0, 7.0, 0, 1, 4.4, "along",
      "kirkgate", "filler",
      "Song school and vestry, its BACK against the churchyard's north wall "
      "and its door on the north side, onto the lane behind the rope house. "
      "It faced south until ad-town-04: the churchyard is terraced 2.40 m "
      "above this ground, so the church's own retaining parapet stood 1.1 m "
      "in front of the door and hm.townhouse.door.15 was the one unreachable "
      "door in Hearthmere. A building that is 'against' a wall has its back "
      "to it, not its face."),
    S(16, "sexton", "cottage", +57.0, -19.0, 7.0, 6.0, 180, 1, 3.8, "along", "kirkgate",
      "filler", "Sexton's cottage. Spades and a bier under a lean-to on its west gable."),
    S(17, "lychgate", "church", +24.0, -0.5, 3.6, 3.2, 270, 1, 2.6, "gable", "kirk_green",
      "hero",
      "Lychgate in the churchyard wall at the foot of the perron. Oak, "
      "half-hipped, a coffin stool inside. Part of venue `church`."),
    S(18, "charnel", "cottage", +57.0, +14.0, 6.0, 4.5, 90, 1, 2.8, "along", "kirkgate",
      "filler", "Charnel house, built into the churchyard's north-east angle. Barred window, no door."),

    # -- 19-22  Kirk Green frontages ----------------------------------------
    S(19, "workshop_a", "workshop", +27.6, +15.7, 7.0, 10.0, 186, 2, 6.4, "gable",
      "bakers_row", "filler",
      "Workshop below, dwelling over, gable to the street. Shutters that "
      "fold down into a counter, a bench visible from the pavement, "
      "shavings in the gutter. Eaves capped at 6.6 m."),
    S(20, "townhouse_d", "townhouse", +18.7, -15.2, 7.0, 10.0, 261, 2, 6.2, "gable",
      "ford_road", "filler",
      "Narrow burgage plot on Ford Road's east side, gable to the road, "
      "long yard behind running to the Kirkgate boundary wall. Privy at the "
      "far end, as far from the house as the plot allows."),
    S(21, "confectioner", "confectioner", +20.5, +12.0, 6.0, 10.0, 0, 2, 6.4, "gable",
      "kirk_green", "secondary",
      "Confectioner. Gable to Kirk Green, sugar-loaf sign on an iron bracket. "
      "Second near jamb of the arrival frame; same eaves constraint as 19."),
    S(22, "townhouse_e", "townhouse", +16.2, +35.8, 5.5, 10.0, 277, 2, 6.2, "gable",
      "ford_road", "filler",
      "Burgage plot on Ford Road's east side, gable to the road, long garden "
      "running back to the bakery's yard wall."),

    # -- 23-31  Ford Road south, west side, and the back plots --------------
    S(23, "townhouse_f", "townhouse", -4.9, +32.9, 6.0, 11.0, 97, 2, 6.4, "gable",
      "ford_road", "filler", "Burgage plot: 6 m of frontage, 11 m deep, yard and privy behind."),
    S(24, "townhouse_g", "townhouse", -5.8, +39.8, 6.0, 11.0, 97, 3, 8.2, "gable",
      "ford_road", "filler", "Three storeys on a 6 m frontage. Sagging ridge; the middle purlin was replaced with a smaller section and it shows."),
    S(25, "cordwainer", "workshop", -6.6, +46.8, 6.0, 11.0, 97, 2, 6.4, "gable",
      "ford_road", "filler", "Cordwainer. Boot sign, last on the bench, offcuts in the gutter."),
    S(26, "cottage_a", "cottage", -23.4, +34.1, 8.0, 8.0, 93, 1, 4.2, "along",
      "bell_alley", "filler", "Back-plot cottage on Bell Alley, one room and a loft."),
    S(27, "cottage_b", "cottage", -44.0, +57.1, 8.0, 8.0, 217, 1, 4.2, "along",
      "the_bailey", "filler", "Cottage on the Bailey, built ten years after its neighbour against "
      "the same party wall, so the two roofs are a course out of line and "
      "the junction is flashed with lead offcuts."),
    S(28, "shed_a", "shed", -22.6, +47.2, 6.0, 5.0, 93, 1, 2.9, "along",
      "bell_alley", "filler", "Back-lane shed: firewood, a handcart, a pig."),
    S(29, "cottage_c", "cottage", -36.6, +34.5, 9.0, 8.0, 90, 1, 4.4, "along",
      "tenter_lane", "filler", "Weaver's cottage on Tenter Lane, loom window on the east."),
    S(30, "cottage_d", "cottage", +66.7, +52.7, 9.0, 8.0, 298, 1, 4.4, "along",
      "the_bailey", "filler", "Cottage with a thatched roof instead of tile - the last thatch left "
      "inside the wall, and the reason the wall-walk above it carries a "
      "leather fire bucket on a hook."),
    S(31, "shed_b", "shed", -15.9, +66.7, 6.0, 4.5, 184, 1, 2.8, "along",
      "the_bailey", "filler", "Tenter shed: frames, tenterhooks, a lime tub."),

    # -- 32-37  Bakers' Row: the fire trades --------------------------------
    S(32, "bakery", "bakery", +27.3, +33.4, 11.0, 10.0, 6, 2, 6.6, "along", "bakers_row",
      "secondary",
      "Bakery. Oven-house projecting south with a 12.0 m stone flue — the "
      "second tallest chimney in town and a landmark from the south road. "
      "Flour dust on everything within 5 m."),
    S(33, "cooper", "cooper", +39.2, +34.2, 12.0, 10.0, 3, 1, 5.2, "along", "bakers_row",
      "secondary",
      "Cooper. Open-sided setting-up floor, a firing pit, staves stacked in "
      "cones outside. Yard to the south."),
    S(34, "carpenter", "carpenter", +53.1, +33.9, 14.0, 10.0, 357, 1, 5.6, "along",
      "bakers_row", "secondary",
      "Carpenter and joiner. Long open front, a sawpit under a lean-to roof, "
      "timber in stick to season along the plot's south edge."),
    S(35, "chandler", "chandler", +40.2, +17.0, 10.0, 9.0, 183, 1, 5.0, "along",
      "bakers_row", "secondary",
      "Tallow and wax chandler. Sited at the far end of the fire lane with "
      "the prevailing wind carrying everything it renders away over the "
      "orchard and out of town. Rendering shed behind, drying racks, a "
      "smell."),
    S(36, "bowyer", "bowyer", +48.7, +49.4, 9.0, 8.0, 349, 1, 4.8, "along", "sty_lane",
      "secondary",
      "Bowyer. Staves in the rafters, a shooting butt against the wall "
      "revetment behind, which is the only straight 30 m in the south quarter."),
    S(37, "sawshed", "shed", +38.6, +50.2, 10.0, 6.0, 354, 1, 3.6, "along", "sty_lane",
      "filler", "Open saw shed and timber store, three bays, no walls."),

    # -- 38-42  South gate ---------------------------------------------------
    S(38, "waggon_shed", "stables", +14.8, -29.9, 14.0, 8.0, 257, 1, 4.6, "along",
      "ford_road", "secondary",
      "Waggon shed: five open bays, waggon poles up, a spare axle on "
      "brackets and a broken wheel leaning where it fell. Carriers turn in "
      "the yard beside it."),
    S(39, "carter", "cottage", +13.0, +54.6, 8.0, 8.0, 277, 1, 4.2, "along",
      "ford_road", "filler", "Carter's cottage, its door 2 m from the yard gate."),
    S(40, "gateward_s", "cottage", -9.0, +62.9, 8.0, 7.0, 345, 1, 4.0, "along",
      "smiths_lane", "filler", "Cottage on Smiths' Lane. The south gate ward lives over the gate arch, not here; this is the carter who works for him."),
    S(41, "cottage_e", "cottage", +60.8, +60.9, 9.0, 8.0, 315, 1, 4.4, "along",
      "the_bailey", "filler", "Cottage on the Bailey, woodpile stacked to the eaves along its wall "
      "and a lean-to henhouse against the wall revetment behind."),
    S(42, "cottage_f", "cottage", +30.0, +60.5, 9.0, 8.0, 161, 1, 4.4, "along",
      "the_bailey", "filler", "Shed and lean-to on the Bailey: iron stock under cover, a "
      "grindstone, and a cart that has not moved in a year."),

    # -- 43-48  Blacksmith and the south-west --------------------------------
    S(43, "blacksmith", "blacksmith", -33.0, +51.0, 18.0, 14.0, 60, 1, 5.4, "along",
      "smiths_lane", "hero",
      "BLACKSMITH. Open-fronted work shed (roofed, unwalled, so the work is "
      "visible from the lane) with the forge, anvil, quench and bellows, plus "
      "a walled dwelling bay at the west end. Chimney to 11.4 m. Platform cut "
      "into the slope with a 1.1 m revetment on its north side. Highest, "
      "driest ground in the town and 30 m from the nearest thatch."),
    S(44, "smith_house", "townhouse", +12.5, +64.8, 9.0, 8.0, 171, 2, 6.0, "along",
      "the_bailey", "filler", "Cottage on the Bailey. Its garden is bigger than the house and is "
      "full of scrap iron, which the owner insists he is going to use."),
    S(45, "charcoal_store", "shed", -27.5, +64.1, 8.0, 6.0, 190, 1, 3.4, "along",
      "the_bailey", "filler", "Charcoal store, deliberately separate from the forge, doors on the leeward side."),
    S(46, "cottage_g", "cottage", +64.2, +15.9, 9.0, 8.0, 99, 1, 4.4, "along",
      "the_bailey", "filler", "Cottage on the Bailey. A vine over the door, dead for two years and "
      "never cut down."),
    S(47, "cottage_h", "cottage", -56.6, +44.1, 9.0, 8.0, 234, 1, 4.4, "along",
      "the_bailey", "filler", "Cottage with a lean-to workshop on its gable, and hens that get into "
      "the lane."),
    S(48, "byre", "shed", -52.2, +14.3, 10.0, 7.0, 177, 1, 4.0, "along",
      "well_lane", "filler", "Cow house and hay loft. Two cows, and the town's milk comes from here."),

    # -- 49-53  South-east cottages ------------------------------------------
    S(49, "cottage_i", "cottage", +22.1, +52.2, 9.0, 8.0, 0, 1, 4.4, "along",
      "sty_lane", "filler", "Cottage on Sty Lane."),
    S(50, "cottage_j", "cottage", -37.1, +12.6, 9.0, 8.0, 174, 1, 4.4, "along",
      "well_lane", "filler", "Cottage with a brick-nogged gable, rebuilt after a fire - the only "
      "nogging in Hearthmere, and a different colour from everything near "
      "it."),
    S(51, "cottage_k", "cottage", +71.2, +44.4, 9.0, 8.0, 298, 1, 4.4, "along",
      "the_bailey", "filler", "Cottage skewed to the Bailey's curve, so its plot is a wedge and its "
      "back fence has a kink in it."),
    S(52, "sties", "shed", +68.0, +66.0, 8.0, 5.0, 225, 1, 2.8, "along",
      "the_bailey", "filler",
      "Pig sties and a byre OUTSIDE the Cinder Tower, on the midden. Pigs and "
      "the midden belong together and both belong outside the wall."),
    S(53, "privy_row", "shed", +30.0, +49.5, 6.0, 3.0, 354, 1, 2.4, "along",
      "sty_lane", "filler", "A row of four privies over a common pit, emptied into the midden outside the Cinder Tower."),

    # -- 54-58  East quarter, inside the wall --------------------------------
    S(54, "cottage_l", "cottage", +10.8, -45.4, 7.0, 7.0, 257, 1, 4.2, "along",
      "mill_lane", "filler", "Cottage on Ford Road's east side in the north quarter, wedged into the last gap between the road and Kirkgate. Two rooms, a loft, and a yard four paces deep."),
    S(55, "cottage_m", "cottage", -40.3, -62.5, 8.0, 8.0, 13, 1, 4.2, "along",
      "mill_lane", "filler", "Cottage in the mill quarter, flour-dusted for four months of the "
      "year and never entirely clean of it."),
    S(56, "cottage_n", "cottage", -11.9, -73.2, 8.0, 8.0, 189, 1, 4.2, "along",
      "mill_lane", "filler", "Cottage on Mill Lane by the north wall, its threshold two courses "
      "below the lane because the lane has been re-metalled over itself."),
    S(57, "dovecote", "dovecote", +65.2, -17.8, 5.4, 5.4, 81, 1, 6.2, "cone",
      "the_bailey", "secondary",
      "Glebe dovecote. Circular, coursed rubble, conical tiled roof to 7.6 "
      "m with a lantern. 240 nest boxes. The only round building in "
      "Hearthmere and worth the whole quarter for silhouette."),
    S(58, "tithe_barn", "warehouse", +35.5, -24.9, 13.0, 8.0, 274, 1, 5.8, "along",
      "kirkgate", "filler", "Tithe barn. Cart doors on both long sides with a threshing floor "
      "between them, so the draught blows the chaff clear. Aisled, five "
      "bays, the biggest single roof in the town after the church."),

    # -- 59-69  Wharfside and the north-east trade quarter -------------------
    S(59, "warehouse_a", "warehouse", +40.4, +72.3, 14.0, 7.0, 341, 2, 7.2, "along",
      "the_bailey", "secondary",
      "Warehouse on the Bailey: the carriers' bonded store, the oldest "
      "timber frame in Hearthmere and underpinned twice. Loading door at "
      "first floor with a gibbet beam and a block over it."),
    S(60, "netloft", "warehouse", +30.6, -68.5, 10.0, 5.5, 188, 2, 6.2, "along",
      "wharf_lane", "filler", "Net loft over an open boat store. Tar barrel, floats, a half-mended net on trestles."),
    S(61, "customs", "quay", +48.0, -44.0, 12.0, 10.0, 315, 2, 7.0, "along",
      "wharf_lane", "hero",
      "Customs house. Faces north-west square onto the Water Gate so nothing "
      "lands without passing its window. Stone below, timber above, a stair "
      "turret, the town's weighbeam under a canopy on its north side."),
    S(62, "warehouse_b", "warehouse", +35.7, -40.0, 12.0, 8.0, 270, 2, 7.4, "along",
      "kirkgate", "secondary", "Warehouse. Grain below, wool above, both smells."),
    S(63, "warehouse_c", "warehouse", -63.7, -59.8, 11.0, 8.0, 139, 2, 7.2, "along",
      "the_bailey", "secondary", "Warehouse on the Bailey in the mill quarter: grain below, wool "
      "above, both smells. Its north wall never sees the sun and is stained "
      "to head height with damp."),
    S(64, "fish_eatery", "fish_eatery", +36.4, -51.6, 10.0, 8.0, 11, 1, 5.0, "along",
      "wharf_lane", "secondary",
      "Mere-fish eatery. Six trestles under an awning, a smoking shed behind, "
      "and a queue at noon. Faces north onto Wharf Lane, so it is lit."),
    S(65, "fisher_a", "cottage", +18.9, -53.8, 8.0, 8.0, 358, 1, 4.2, "along",
      "wharf_lane", "filler", "Cottage on Sty Lane behind the tithe barn. Nets over the fence and a punt upturned on trestles: a fisherman who walks to work."),
    S(66, "fisher_b", "cottage", +20.9, +63.4, 8.0, 8.0, 171, 1, 4.2, "along",
      "the_bailey", "filler", "Cottage on the Bailey; its gable window is a boat's transom reused, "
      "which is how you know who used to live in it."),
    S(67, "ropehouse", "warehouse", +52.0, -31.0, 24.0, 5.0, 340, 1, 4.4, "along",
      "wharf_lane", "filler",
      "Rope house: 24 m long and 5 m wide because that is what laying rope "
      "needs. Its plan shape alone breaks the town's grain and is worth "
      "keeping exactly as drawn."),
    S(68, "cottage_o", "cottage", +19.1, -45.1, 8.0, 8.0, 88, 1, 4.2, "along",
      "kirkgate", "filler", "Cottage on Kirkgate's west side, backing onto the Ford Road plots."),
    S(69, "cottage_p", "cottage", +9.4, -53.5, 8.0, 8.0, 355, 1, 4.2, "along",
      "wharf_lane", "filler", "Cottage on Wharf Lane, its front step dished 40 mm by two hundred years of wet boots."),

    # -- 70-76  North gate quarter and the Ferryman's Lamp -------------------
    S(70, "stables", "stables", -10.2, -47.4, 16.0, 12.0, 80, 1, 5.4, "along",
      "ford_road", "secondary",
      "Stables and waggon yard. Long range of eleven stalls with a hay loft "
      "over, tack on pegs, a mounting block at the yard gate. The yard itself "
      "is open to Ford Road and is where the carriers turn."),
    S(71, "farrier", "blacksmith", -30.0, -48.0, 9.0, 8.0, 90, 1, 4.6, "along",
      "ford_road", "filler",
      "Farrier's forge, small and open-fronted. A second fire in the town, "
      "sited on the lowest, wettest ground 8 m from the wall and 12 m from "
      "the river, which is exactly why it is allowed."),
    S(72, "pub", "pub", +19.0, -70.0, 12.0, 7.5, 180, 2, 5.4, "along", "wharf_lane",
      "hero",
      "THE FERRYMAN'S LAMP. Floor sunken 0.55 m below Wharf Lane because the "
      "lane has been re-metalled over itself for two hundred years. Low "
      "beams, small windows, the warmest interior in Hearthmere. Its sign is "
      "the actual iron ferry lamp on a bracket; the ferry stair it used to "
      "light is through the Ferry Postern behind."),
    S(73, "gateward_n", "cottage", +6.9, -69.7, 8.0, 7.0, 175, 1, 4.0, "along",
      "wharf_lane", "filler", "North gate ward's house."),
    S(74, "cottage_q", "cottage", -55.1, -20.5, 8.0, 8.0, 178, 1, 4.2, "along",
      "mere_street", "filler", "Cottage on Mere Street, its wall splashed to 0.4 m by cart wheels."),
    S(75, "cottage_r", "cottage", -55.9, -3.0, 8.0, 8.0, 358, 1, 4.2, "along",
      "mere_street", "filler", "Cottage on Mere Street; the plot in front is a kitchen garden with a hurdle fence."),
    S(76, "shed_c", "shed", -58.1, -45.5, 6.0, 5.0, 307, 1, 3.0, "along",
      "the_bailey", "filler", "Handcart shed and a lean-to woodstore."),

    # -- 77-84  Mill quarter, north-west --------------------------------------
    S(77, "watermill", "watermill", -49.0, -79.5, 13.0, 10.0, 150, 2, 7.4, "along",
      "mill_lane", "secondary",
      "Watermill, OUTSIDE the wall, on a made platform cut out into the "
      "south bank so the wheel reaches the channel — the leat it used to "
      "run on went with D-024's one-water-surface rule. Breastshot wheel "
      "3.6 m diameter on the north gable, its foot dipping into the one "
      "water surface at -3.10. Sack hoist and a lucam over the water."),
    S(78, "granary", "watermill", -22.9, -75.4, 12.0, 9.0, 190, 2, 6.8, "along",
      "mill_lane", "secondary",
      "Granary on staddle stones, 0.6 m clear beneath, boarded, no ground "
      "floor at all. Part of venue `watermill`."),
    S(79, "miller", "townhouse", -31.3, -60.1, 10.0, 9.0, 10, 2, 6.4, "along",
      "mill_lane", "filler", "Miller's house. Whitest plaster in town, for obvious reasons."),
    S(80, "malthouse", "warehouse", -66.1, +7.1, 11.0, 9.0, 266, 2, 6.8, "along",
      "the_bailey", "filler", "Malt house. Kiln cowl on the ridge turning in the wind, and a floor "
      "you can smell from the lane."),
    S(81, "cottage_s", "cottage", -21.6, -59.0, 9.0, 8.0, 9, 1, 4.2, "along",
      "mill_lane", "filler", "Cottage backing onto the stable yard."),
    S(82, "cottage_t", "cottage", -51.2, -50.7, 9.0, 8.0, 319, 1, 4.2, "along",
      "the_bailey", "filler", "Cottage, kitchen garden, a plum tree older than the wall."),
    S(83, "cottage_u", "cottage", -63.6, -29.5, 9.0, 8.0, 282, 1, 4.2, "along",
      "the_bailey", "filler", "Cottage on the Bailey."),
    S(84, "shed_d", "shed", -62.4, -38.1, 7.0, 5.0, 294, 1, 3.0, "along",
      "the_bailey", "filler", "Bailey shed: hurdles, a cart, a stack of wall-repair stone that has been there for a decade."),

    # -- 85-92  West quarter ---------------------------------------------------
    S(85, "cottage_v", "cottage", -46.0, -21.1, 9.0, 8.0, 175, 1, 4.4, "along",
      "mere_street", "filler", "Cottage on Mere Street's north side."),
    S(86, "cottage_w", "cottage", -64.4, -20.5, 9.0, 8.0, 185, 1, 4.4, "along",
      "mere_street", "filler", "Cottage, its neighbour, sharing a chimney stack."),
    S(87, "gateward_w", "cottage", -66.5, +16.2, 7.0, 7.0, 266, 1, 4.0, "along",
      "the_bailey", "filler", "West gate ward's cottage, angled to watch the gate from its door."),
    S(88, "cottage_x", "cottage", -47.0, -3.5, 9.0, 8.0, 355, 1, 4.4, "along",
      "mere_street", "filler", "Cottage on Mere Street's south side, lit front, window boxes."),
    S(89, "cottage_y", "cottage", -65.0, -3.0, 9.0, 8.0, 5, 1, 4.4, "along",
      "mere_street", "filler", "Cottage; the party fence has been moved twice and the dispute is not over."),
    S(90, "wellhouse", "wellhouse", -37.7, +26.5, 5.6, 5.6, 354, 1, 3.2, "along",
      "well_lane", "secondary",
      "Well-house over the town well and the conduit head that feeds the "
      "fountain. Open on all four sides, tiled pyramid roof, a windlass, a "
      "chained cup, and a stone trough the whole west quarter draws from."),
    S(91, "bathhouse", "bathhouse", -51.9, +30.3, 14.0, 11.0, 357, 1, 5.6, "along",
      "well_lane", "secondary",
      "Bathhouse, on the conduit and next to its own spring. Furnace and a "
      "9.0 m flue at the west end; steam out of the roof louvres on a cold "
      "morning is one of the town's best ambient reads."),
    S(92, "cottage_z", "cottage", -64.2, +24.7, 9.0, 8.0, 257, 1, 4.4, "along",
      "the_bailey", "filler", "Cottage against the Bailey below the Spring Tower."),

    # -- 93-94  Outside the wall ------------------------------------------------
    S(93, "tannery", "tannery", +86.0, -16.0, 14.0, 10.0, 225, 1, 5.0, "along",
      "quay_road", "secondary",
      "Tannery and dye yard, OUTSIDE the wall, downstream of the quay and "
      "downwind of everything. Pit yard of 24 lime and tan pits, drying shed "
      "with louvred sides, a bark store. The single most defensible placement "
      "in the plan: it needs running water, it stinks, and it is 90 m from "
      "the nearest occupied window with the wind blowing away from town."),
    S(94, "crane_house", "quay", +62.0, -57.0, 7.0, 7.0, 42, 1, 5.6, "along",
      "quay_road", "hero",
      "Treadwheel crane on the quay, OUTSIDE the wall. Timber tower with a "
      "slewing jib, a double treadwheel, and a stone counterweight box. "
      "Silhouette anchor of the whole waterfront."),
]

# Open lots: no roof, but they are half the reason the plan reads as a town.
OPEN_LOTS = [
    dict(id="hm.lot.graveyard", name="Churchyard & graveyard", kind="graveyard",
         poly=[(+24, -20), (+58.5, -20), (+58.5, +23), (+24, +23)],
         note="Wrapped round the church on the terrace. Yew at the north-west "
              "angle, older stones leaning north, newer ground to the east."),
    dict(id="hm.lot.orchard", name="Glebe orchard", kind="orchard",
         poly=[(+80, +2), (+96, +6), (+96, +34), (+78, +28)],
         note="Outside the east postern. Twelve old apples, grass long under them."),
    dict(id="hm.lot.tenter", name="Tenter ground", kind="yard",
         poly=[(-46, +34), (-30, +36), (-32, +52), (-48, +50)],
         note="Cloth stretched on frames. Reads as colour from the wall-walk."),
    dict(id="hm.lot.waggonyard", name="Southgate waggon yard", kind="yard",
         poly=[(+6, +54), (+22, +54), (+22, +70), (+6, +70)],
         note="Turning circle, waggon poles, a spare wheel leaning on the shed."),
    dict(id="hm.lot.stableyard", name="Grey Heron stable yard", kind="yard",
         poly=[(-58, -34), (-42, -34), (-42, -18), (-58, -18)],
         note="Muck heap, water trough, tack on pegs, two hunters and a mule."),
    dict(id="hm.lot.smithyard", name="Blacksmith's yard", kind="yard",
         poly=[(-44, +48), (-22, +52), (-24, +66), (-46, +64)],
         note="Cut platform, 1.1 m revetment on the north side, iron stock, "
              "horseshoes in a pile, scale ground into the dirt."),
    dict(id="hm.lot.midden", name="The midden", kind="midden",
         poly=[(+62, +64), (+74, +58), (+82, +70), (+70, +78)],
         note="Outside the Cinder Tower, downwind. Kites over it."),
    dict(id="hm.lot.quay", name="The quay", kind="quay",
         poly=WHARF,
         note="Wharf deck at -1.55 with a lower stage at -2.85 reached by "
              "Fishers' Steps and a slipway. Bollards, mooring rings, fish "
              "drying racks, four flat-bottomed lighters, crane at slot 94."),
    dict(id="hm.lot.gardens_west", name="West kitchen gardens", kind="garden",
         poly=[(-74, -14), (-58, -13), (-58, +0), (-74, -1)],
         note="Beans, leeks, a beehive, hurdle fences that lean."),
    dict(id="hm.lot.gardens_ne", name="Kirkgate gardens", kind="garden",
         poly=[(+24, -46), (+34, -46), (+34, -34), (+24, -34)],
         note="Cabbage, a rain butt, washing lines."),
    dict(id="hm.lot.ford", name="The old ford", kind="water",
         poly=FORD_BAR,
         note="The reason the town exists, now silted and disused. A gravel "
              "bar under 0.45 m of water 16 m east of the bridge, with a "
              "shelving bay in the south bank where the approach ramp still "
              "runs into the river — kerb broken, cart ruts filled with weed. "
              "Visible from the bridge parapet, which is the point of it."),
]

# --------------------------------------------------------------------------
# Facade breaks — Art Bible §7
# --------------------------------------------------------------------------
# §7 caps undifferentiated street facade at 12 m. Every scheduled mass whose
# street face (`w`) exceeds that declares HOW the run is broken, keyed by slot
# number. `townplan.py` emits the note into the generated schedule and FAILS
# the build if a face over 12 m has no entry. Kept as a side table rather than
# a fifteenth tuple field because three tools (townplan.py, ground.py, lay.py)
# parse the fourteen-field slot row.
BREAKS = {
    1:  "Carriage arch through to the stable yard, south of centre, and the "
        "jettied upper storeys step 0.45 m out over the paving — the frontage "
        "breaks at the arch and again at each jetty line.",
    2:  "The forecourt's four steps run the full frontage, but the doorcase "
        "breaks forward half a bay at the porch and the north-east tower "
        "lifts the north end of the block clear of the eaves line.",
    3:  "Arcaded ground floor — ten oak posts and open air, no facade at all "
        "below the chamber; the bell-cote gable breaks the roof at the east "
        "end.",
    11: "The great west portal — 6.4 m clear, 8.0 m to the arch apex, doors "
        "standing open — breaks the front at centre, with full-height "
        "buttresses at the aisle lines and the nave gable standing proud of "
        "both aisle roofs.",
    14: "Six doors and six chimneys at 4 m centres, no two shutters the same "
        "colour: one 24 m roof that reads as six houses.",
    34: "Open working bays between closed end bays, and the sawpit lean-to "
        "breaks the eaves line at the east end.",
    38: "Five open bays on posts — no wall to be undifferentiated — closed "
        "by a boarded harness bay at the west end.",
    43: "Open-fronted work shed on posts for two-thirds of the run, then the "
        "walled dwelling bay at the west end: a hard open-to-closed break, "
        "with the chimney marking it.",
    58: "Recessed full-height cart door at mid-front with a gablet over it; "
        "the threshing draught runs through to the matching door behind.",
    59: "First-floor loading door, gibbet beam and block break the front at "
        "mid-run, and the two underpinning campaigns read as a "
        "stone-to-timber change at sill height.",
    67: "Post-and-shutter working bays alternate open and closed down the "
        "whole run — a rope walk is a rhythm, not a wall — with a boarded "
        "store bay closing the north end.",
    70: "Recessed cart entry to the yard at mid-range with the mounting "
        "block beside it; the hay-loft door and hoist above break the eaves.",
    77: "The lucam oversails the front at the hoist door, and the wheel's "
        "gable end stands proud of the run at the north.",
    91: "The furnace house and its 9.0 m flue break forward at the west "
        "end; stone to the vapour line, limewashed plaster above.",
    93: "The drying shed's louvred slatting against the closed bark store — "
        "solid to slatted at mid-front, with the pit yard's gate between.",
}

# --------------------------------------------------------------------------
# Which slots are authored venue modules
# --------------------------------------------------------------------------
# Lives here rather than in townplan.py because `tools/plan/ground.py` needs
# it too: a venue is exactly the set of buildings that gets a named, levelled
# pad in content/town/terrain.json.

VENUE_ROLE = {
    "church": "hero", "guild": "hero", "inn": "hero", "pub": "hero",
    "blacksmith": "hero", "market_square": "hero", "stalls": "hero",
    "gatehouse": "hero", "wall": "hero", "quay": "hero",
    # The moot hall's bell-cote is the left-hand anchor of the arrival frame
    # (TOWN_PLAN section 7.1). A mass a locked composition depends on gets hero
    # attention; townplan.py::check_frame_anchors enforces this for every slot
    # named as an anchor in section 7.
    "moot_hall": "hero",
}

VENUE_OF_SLOT = {
    1: "inn", 2: "guild", 3: "moot_hall", 4: "shop_row", 7: "chophouse",
    11: "church", 21: "confectioner", 32: "bakery", 33: "cooper",
    34: "carpenter", 35: "chandler", 36: "bowyer", 38: "waggon_shed",
    43: "blacksmith", 57: "dovecote", 61: "quay", 62: "warehouse",
    64: "fish_eatery", 70: "stables", 72: "pub", 77: "watermill",
    90: "wellhouse", 91: "bathhouse", 93: "tannery",
}

# --------------------------------------------------------------------------
# Venues that are not building slots
# --------------------------------------------------------------------------
# Placement has to be TOTAL: every module under `tools/assetgen/venues/` is
# either in `VENUE_OF_SLOT`, or here, or in `NOT_PLACED` with a reason.
# `townplan.py::check_placement_total` fails the build otherwise.
#
# It is here because `venues/landscape.py` existed, was built, and was in the
# town file — and was NOT in this list while it lived in townplan.py. So every
# regeneration silently deleted it, and the town rendered with no vegetation,
# no gardens, no churchyard and no intramural ground for a whole wave before
# anybody noticed. A list that can be short by one without complaining is not
# a list, it is a trap.
#
# `origin` with a None Y takes the height field, like every other origin in
# the file. Hard-typing one was how the gatehouse ended up 0.45 m under its
# own gate flat.

INFRASTRUCTURE = [
    dict(id="terrain", role="infrastructure", cells=[], origin=[0, 0, 0],
         note="Owns height(x,z). Every generator derives Y from it; nothing "
              "assumes y=0."),
    dict(id="landscape", role="infrastructure", cells=[], origin=[0, 0, 0],
         note="Consumer for the ground outside the buildings: fields, hedges, "
              "the orchard, the churchyard, gardens, verges, the distance "
              "wood. Placed at the origin and authored in world coordinates."),
    dict(id="streets", role="infrastructure", cells=[], origin=[0, 0, 0],
         note="Consumer for streets[]. Carriageways, kerbs, gutters, crossing "
              "stones, the Market Step, the perron, the wall stairs and the "
              "street furniture. Emits per-segment collision, never one "
              "bounding box (v1 sealed Ford Road with exactly that mistake)."),
    dict(id="wall", role="hero", cells=[], origin=[0, 0, 0],
         note="Consumer for wall{}. Ring, towers, gates, wall-walk."),
    dict(id="gatehouse", role="hero", cells=["F2"], origin=[-2.4, None, -76.0],
         note="North gatehouse and the Emberflow bridge. The departure/return "
              "frame. The bridge crosses the Emberflow 10 m outside the gate "
              "and its south abutment shares the gate flat; the north abutment "
              "and its causeway are hm.pad.bridge_north at z=-101."),
    dict(id="market_square", role="hero",
         cells=["E5", "F5", "G5", "E6", "F6", "G6", "E7", "F7", "G7", "F8", "G8"],
         origin=[0, 0, 0],
         note="Paving, fountain, market cross, Market Step, kerbs, troughs, "
              "bollards."),
    dict(id="stalls", role="hero", cells=["E6", "F6", "G6", "E7", "F7"],
         origin=[-4.0, None, -6.0],
         note="Fourteen stalls, clustered at the north mouth where the "
              "footfall is and thinning south. No two alike."),
    dict(id="townhouse", role="kit", cells=[], origin=[0, 0, 0],
         note="Seeded modular kit: townhouse / cottage / workshop / shed / "
              "warehouse variants. Consumes buildingSlots[] rows whose venue "
              "is null."),
]

# Modules that exist and are deliberately NOT placed in the town. Every entry
# is a declaration with a reason, and the reason is checked by a human, not by
# the tool — the tool only insists that one exists.
NOT_PLACED = {
    "cottage":
        "ORPHAN, v1 survivor. venues/townhouse.py builds every `cottage` kit "
        "slot in the schedule (KITS = townhouse/cottage/shed/workshop, 63 "
        "masses) straight from buildingSlots[]. venues/cottage.py builds one "
        "standalone `hm.cottage.01` on v1 cells (A2 B2 F2 A4 F3 F5) that no "
        "venues[] row has ever referenced. It is kept only because deleting a "
        "module to make a build green is forbidden; it should be deleted "
        "deliberately, in its own change, once someone confirms townhouse.py "
        "carries everything it did. See review/reports/consolidate.md.",
    "props_sheet":
        "REVIEW HARNESS, not town content. Renders the prop library as a "
        "contact sheet for art-director review (docs/REVIEW_PROTOCOL.md). "
        "CELLS = [], never placed, never shipped to the client.",
    "props_situ":
        "REVIEW HARNESS, not town content. Renders props in a mock yard at "
        "gameplay-camera distance so residue can be judged in context rather "
        "than on a turntable. CELLS = [], never placed.",
}

# --------------------------------------------------------------------------
# Lighting and ambient — the authoritative copy
# --------------------------------------------------------------------------
# These used to be copied forward out of the previous hearthmere.json by
# `write_town`, which meant a hand edit to either survived exactly until the
# next regeneration and then vanished without a word. They live here now, with
# every other authored number in the plan, so that regeneration is a pure
# function of this module and nothing is carried across from a file that a
# tool is about to overwrite.

LIGHTING = {
    "comment": "Locked 09:30 rig, Art Bible section 4. THE authoritative copy "
               "is tools/plan/plan_data.py:LIGHTING; this block is generated "
               "from it and both tools/render/viewer.html and "
               "client/src/main.js read it from here. Rim is a directional "
               "light standing in for a true grazing-angle rim, so it lights "
               "whole faces; on curved geometry the limb dominates the "
               "projected face and a strongly saturated rim drains colour from "
               "every lathed object. Desaturated and reduced accordingly. See "
               "D-009, D-010 and D-025.",
    "timeOfDay": "09:30",
    "sunElevationDeg": 38.0,
    "sunAzimuthDeg": 125.0,
    "sun": {"color": "#FFF2D8", "intensity": 3.2},
    "hemisphere": {"sky": "#AFC9E0", "ground": "#8A7352", "intensity": 1.35},
    "ambient": {"color": "#6B5A46", "intensity": 0.55},
    "bounce": {"color": "#C9A87E", "intensity": 0.55},
    "rim": {"color": "#A9C6E2", "intensity": 0.85},
    "exposure": 1.05,
    # ------------------------------------------------------------------
    # Cascaded shadow maps — docs/ARCHITECTURE.md section 5, "one directional
    # key (sun) with cascaded shadow maps". Specified from the start, built
    # only now.
    #
    # What shipped instead was a single orthographic box: 4096 texels over a
    # 92 m box, 44.5 texels/m, a 2.25 cm texel, declared three times over in
    # client/src/main.js, tools/render/town.html and tools/render/viewer.html.
    # review/reports/ad-town-04.md section 1 rejected the build on what that
    # does to the spawn frame — the sun/shade boundary crosses the church nave
    # as a right-angled staircase, in the composition BUILD_DIRECTIVE section 3
    # calls the most important in the project.
    #
    # One box cannot be both wide enough to hold the town's casters and fine
    # enough for a 1.62 m eye. Three boxes can, and the numbers below are that
    # trade made explicitly rather than by accident:
    #
    #   distance  how far shadows reach, AND — because the renderers pass it
    #             into `VisibilitySet` — the radius of the caster set. Those
    #             are one number: a batch further out has already had
    #             `castShadow` turned off, so a cascade reaching past it draws
    #             nothing, and a cascade stopping short of it pays for casters
    #             whose shadows are then thrown away.
    #   splits    fractions of `distance`. Authored, not computed: three's
    #             'practical' scheme is tuned for a 1000 m view distance and
    #             puts its first break at 5.6 m of a 32 m range on a curve that
    #             ignores where the ground the eye actually reads is.
    #   mapSizes  one per cascade, all equal so CSM's texel snap stays exact
    #             (a non-power-of-two ratio between the snap grid and the real
    #             texel makes the shadow edge crawl as the camera turns).
    #
    # Measured result, 55 degrees at 16:9 — the boxes are the frustum slice
    # diagonals, so they follow from the splits rather than being chosen:
    #
    #   cascade 0   0.0 -  5.4 m   11.6 m box   354 texels/m   0.28 cm
    #   cascade 1   5.4 - 14.1 m   29.9 m box   137 texels/m   0.73 cm
    #   cascade 2  14.1 - 32.0 m   68.0 m box    60 texels/m   1.66 cm
    #
    # against 44.5 texels/m at EVERY distance before. Every band is finer than
    # what it replaces and the near field gains 8x.
    #
    # WHY 32 AND NOT 42 — cost is the same problem as quality, and this is
    # where the two meet. The shadow pass was already bigger than the beauty
    # pass (602 shadow draws against 498 scene at the `square` camera) because
    # a 92 m box around the player holds every caster within 46 m in every
    # direction, two-thirds of them behind the lens. Cascades do not fix that
    # by themselves: the FAR cascade's box is sized by its slice's far-plane
    # diagonal, which at 42 m is 89 m — the same box again — so three cascades
    # at 42 m measured 1,128 shadow draws, an 88 % INCREASE. The caster set is
    # a disc of radius `distance` around the camera and its area is what the
    # shadow pass costs; 32 m is 58 % of the area of 42 m. That is the whole
    # saving, and it buys back the two near cascades. What it costs is shadow
    # reach: a mass between 32 m and 42 m out no longer casts. Verified in
    # frame at `gate-south` and `approach-w`, the two views with open ground
    # running away from the lens.
    "shadows": {
        "comment": "Cascaded shadow maps, ARCHITECTURE section 5. THE "
                   "authoritative copy is tools/plan/plan_data.py:LIGHTING; "
                   "client/src/shadows.js reads this block and all three "
                   "renderers drive the same SunRig from it, the same rule as "
                   "D-009 and for the same reason — a harness whose shadow rig "
                   "differs from the client's is not measuring the client. "
                   "`distance` must equal client/src/lod.js "
                   "SHADOW_CAST_DISTANCE. `normalBias` is scaled per cascade "
                   "by that cascade's own texel size against "
                   "`normalBiasTexelRef`, the 2.25 cm texel it was tuned at: "
                   "a fixed world offset that is right for a 2.2 cm texel "
                   "detaches every contact shadow on a 0.3 cm one.",
        "cascades": 2,
        "distance": 30.0,
        "splits": [0.18],
        "mapSizes": [4096, 4096],
        "bias": -0.0004,
        "normalBias": 0.02,
        "normalBiasTexelRef": 0.0225,
        "fade": True,
        "margin": 55.0,
        "near": 0.5,
        "far": 200.0,
    },
}

# --------------------------------------------------------------------------
# The shared environmental layer
# --------------------------------------------------------------------------
#
# Authored HERE, next to LIGHTING and for the same reason. `townplan.py` used
# to splice the lighting rig forward out of the previous document with
# `old["lighting"]`, which meant the file could only ever be regenerated from a
# copy of itself; the atmosphere was never going to be added on those terms, so
# it is a constant in the generator from the start. CLAUDE.md: assets are
# generated, never hand-authored — and that makes regeneration idempotent.
#
# It exists because `review/reports/ad-town-02.md` answered the cohesion
# question with "the individual pieces are not the problem; the absence of any
# shared environmental layer over the top of them is" (§5, §11, §13, §14, §21).
# ONE copy, read by `client/src/atmosphere.js`, which is imported by
# `tools/render/town.html`, `tools/render/viewer.html` and `client/src/main.js`
# alike — the same rule as D-009 and for the same reason: three renderers with
# three copies of the sky had already drifted, and only one of them had any
# ambient occlusion at all.
#
# Tuned by rendering `t-arrival`, `t-square`, both aerials and eight eye-height
# frames at varying depth and measuring the mean luminance of the near, middle
# and far depth bands (`tools/render/valuebands.mjs`). The test for fog is not
# "can I see it" — it is whether depth reads WITHOUT the image going milky, so
# every number below was moved until the three bands separated and then stopped.
ATMOSPHERE = {
    "comment": [
        "Aerial perspective, sky, horizon closure, warm AO and the colour "
        "grade. THE authoritative copy — client/src/atmosphere.js reads it and "
        "tools/render/town.html, tools/render/viewer.html and "
        "client/src/main.js all import that one module. See D-049.",
        "Art Bible section 1 requires colour separation between planes: "
        "foreground / midground / background pushed apart in value AND "
        "temperature. That is what `scattering` is; a single-colour fog only "
        "buys the value half.",
    ],
    "scattering": {
        "comment": "Height-integrated exponential, warm near, cool far. Density "
                   "is per metre at the base level; the height term is what "
                   "keeps the water meadow in haze and the church tower out of "
                   "it. `startDistance` is a dead zone so nothing within arm's "
                   "reach is ever touched. RETUNED against ad-town-04 section 3 "
                   "and (a): measured temperatureSwing 0.2 and "
                   "midgroundToBackground 12.6 on the arrival frame — the "
                   "value half of Art Bible section 1 over-driven into a veil, "
                   "the temperature half not happening at all. The two are one "
                   "fault. `fullDistance` is the ONLY control over where warm "
                   "becomes cool, and at 130 m it put the crossover beyond the "
                   "192 m town: every distance a player ever looks at was "
                   "still being mixed toward the warm cream near colour, so "
                   "the cool far colour never reached the frame and the whole "
                   "depth range came back one temperature. It is 82 m now, "
                   "which puts the crossover inside the town's own depth. "
                   "`density` and `maxOpacity` are the value half and both come "
                   "down: the wash was eating the midground the fountain has "
                   "to separate from. The two colours are pushed apart in hue "
                   "and pulled together in value, which is the definition of "
                   "temperature separation without milkiness — near-to-far "
                   "blue-minus-red goes from 83 to 131 while the value gap "
                   "between them narrows from 27 to 35 the other way (the far "
                   "colour is now DARKER than the near one, so distance stops "
                   "meaning 'brighter' and starts meaning 'cooler').",
        # b-r -52, luma 210 — warmer than #E8DCC8 and slightly darker, so the
        # near haze shifts hue without lifting value.
        "nearColor": "#E4D3B0",
        # b-r +79, luma 175 — bluer AND darker than #A9C2DC. This is the number
        # that stops the background reading as flat cream.
        "farColor": "#8FB2DE",
        "density": 0.0038,
        "heightFalloff": 30.0,
        "baseY": -4.0,
        "maxOpacity": 0.78,
        "startDistance": 12.0,
        "fullDistance": 82.0,
        "sunColor": "#FFE7C0",
        "sunAmount": 0.34,
        "sunPower": 5.0,
    },
    "sky": {
        "comment": "Gradient dome plus a horizon value ramp, a sun disc and low "
                   "cirrus. The dome is also the PMREM source, so the drawn sky "
                   "and the image-based lighting cannot disagree. The horizon "
                   "band is COOL, not the old cream: the distance ring resolves "
                   "to `scattering.farColor`, and a warm horizon behind a cool "
                   "distance draws a hard line exactly where the world edge is "
                   "supposed to dissolve.",
        "top": "#4E8FD6",
        "mid": "#A8CDEC",
        "horizon": "#D7E2EA",
        "ground": "#B6AE96",
        "horizonPower": 3.4,
        "horizonWidth": 0.17,
        "sunColor": "#FFF8E6",
        "sunAngularSize": 1.6,
        "sunGlow": 0.40,
        "sunGlowPower": 22.0,
        "cloudAmount": 0.34,
        "cloudScale": 0.016,
        "cloudColor": "#FFFCF4",
        "cloudShade": "#B9C6D4",
    },
    "horizon": {
        "comment": "The skirt that closes the world edge. terrain.json stops at "
                   "a SQUARE plate of Chebyshev half-extent 288 m and its own "
                   "comment says the sky dome closes the frame — true from "
                   "overhead, false from 1.62 m, where the plate edge lands on "
                   "the horizon line and the ground ends in mid-air. "
                   "`innerHalfExtent` must track terrain.extent.far.",
        "innerHalfExtent": 288.0,
        "outerRadius": 1200.0,
        "innerDrop": 0.35,
        "outerDrop": 26.0,
        "color": "#93A07C",
        "segments": 160,
    },
    "ao": {
        "comment": "GTAO with three's grey blend replaced by a tint toward Art "
                   "Bible section 1's #4A3828 — warm, never neutral black. "
                   "`radius` is in metres: 0.75 m is the scale of the junctions "
                   "that matter (wall to ground, eaves to gable, a barrel "
                   "against a wall) and larger reads as dirt. `farDistance` "
                   "clips the AO pass's own camera: GTAO needs a full "
                   "normal+depth prepass of the scene, which is a second "
                   "complete scene pass. See D-049, and D-051 for the "
                   "measurement that moved it from 80 m to 35 m: at the "
                   "arrival camera the AO prepass was 454 draw calls and "
                   "924k triangles of a 2,065-draw frame, against a section 7 "
                   "budget of 900 for the entire frame. The 2.4 m radius is "
                   "34 px at 80 m and 15 px at 35 m in a 55-degree frame, but "
                   "`atmosphere.scattering` is already at ~60 percent opacity "
                   "by 35 m and asymptotes to sky by 130 m, so past that the "
                   "AO term is being multiplied into haze. Every draw beyond "
                   "it changes no pixel a player can see.",
        "tint": "#4A3828",
        "tintStrength": 0.65,
        "intensity": 0.80,
        "radius": 2.4,
        "distanceExponent": 1.0,
        "thickness": 2.0,
        "scale": 1.6,
        "samples": 16,
        "screenSpaceRadius": False,
        "farDistance": 35.0,
        "denoiseRadius": 10,
        "lumaPhi": 8.0,
    },
    "bloom": {
        "comment": "Threshold stays at 1.0 so only genuinely over-range pixels "
                   "bloom. Strength down from 0.32: the Mere's sun glitter was "
                   "being spread by the bloom into the white plate of "
                   "ad-town-02 section 8 before the grade ever saw it.",
        "strength": 0.26,
        "radius": 0.55,
        "threshold": 1.0,
    },
    "grade": {
        "comment": "ARCHITECTURE section 5's grade: lifted shadows, warm "
                   "midtones, a cyan push in the shadows for complementary "
                   "contrast. Runs after the ACES tonemap, on display-referred "
                   "sRGB, which is where a LUT belongs — lifting a shadow in "
                   "linear light lifts it by a factor of forty in the darks and "
                   "reads as fog on the lens. `shadowTint` is a DIRECTION, not "
                   "a colour to multiply by, and `shadowAmount` is how far the "
                   "lift leans along it: the tint is normalised to unit "
                   "luminance, so the lift's level is always `lift` and only "
                   "its hue moves. It was a multiply before, and evaluated on a "
                   "neutral ramp with lift 0.028 / shadowAmount 0.20 the "
                   "darkest step came out +1.0 in value and +1.5 in "
                   "blue-minus-red out of 255 — the whole complementary "
                   "contrast move was being computed and then rounded away. "
                   "Same shape of transform, same two numbers, measured now: "
                   "+9 value and +15 blue-minus-red at the shadow floor, "
                   "decaying to zero by 30 percent grey. `shadowAmount` may "
                   "not exceed lift / 0.247 or the red channel of the lift goes "
                   "negative, which is a crushed black and Art Bible section 1 "
                   "forbids it; the shader floors it at zero.",
        "lift": 0.038,
        "shadowTint": "#7FB2C8",
        "shadowAmount": 0.14,
        "midTint": "#FFD7A2",
        "midAmount": 0.14,
        "highlightRolloff": 0.14,
        "contrast": 1.05,
        "saturation": 1.12,
        "vignette": 0.16,
        "vignetteSoftness": 0.62,
    },
    "water": {
        "comment": "A GGX lobe's peak goes as roughness^-4, so a lake at "
                   "roughness 0.21 under a 3.2-intensity sun answers with a "
                   "blown plate however much the roughness floor is raised — "
                   "raising it spreads the same energy over MORE pixels. "
                   "`specularKnee` is a Reinhard shoulder on the direct "
                   "specular term alone, applied in client/src/water.js: it "
                   "keeps the glitter path and takes the plate away.",
        "specularKnee": 1.05,
        "envIntensity": 0.72,
    },
}

AMBIENT = {
    "comment": "Art Bible §7: static worlds read as dioramas. These drive "
               "the client's motion systems. Authoritative copy is "
               "tools/plan/plan_data.py:AMBIENT.",
    "wind": {"direction": [0.82, 0, 0.57], "speed": 1.4, "gustHz": 0.35},
    "cloth": {"swayHz": [0.3, 0.8], "amplitudeDeg": 4.5},
    "fire": {"flickerHz": [8, 12], "intensityVariance": 0.18},
    "smoke": {"sources": ["hm.blacksmith.chimney.01", "hm.inn.chimney.01",
                          "hm.inn.chimney.02", "hm.pub.chimney.01"]},
    "particulate": {"dustMotes": True, "pollen": True, "forgeSparks": True},
}

# The market place itself — an irregular polygon because it was never planned.
# The north mouth is the widest part, because Ford Road enters there and the
# place grew off the road rather than being set out. Slot 07 used to close it
# at z -28 and stand across the Grey Heron's gable; with the chophouse back at
# z -33 the mouth opens 5 m and the inn's whole 7.4 m elevation is on the
# plaza. WORLD_BIBLE, "Market Place": *wider at the north where the road
# enters, because it grew rather than being planned.*
SQUARE = [(+5.5, -28.0), (-8.0, -28.6), (-15.2, -28.4),
          (-15.9, -32.8), (-26.2, -32.2), (-26.4, -24.5),
          (-25.0, -16.0), (-25.0, -4.0), (-27.5, +8.0), (-24.0, +18.0),
          (-6.0, +19.5), (+3.0, +16.0), (+5.0, +2.0), (+6.5, -13.0)]

# Where the market place takes up its 1.15 m of fall.
MARKET_STEP = dict(a=(-24.0, +0.6), b=(+4.0, +0.6), risers=3, rise=0.16,
                   note="Three risers and a bench-wall across the market place, "
                        "separating the upper market (dry goods, south) from the "
                        "lower (fish and greens, north, where the wash-down "
                        "drains). Traders sit on it. Mounting block at its west end.")

LANDMARKS = [
    dict(id="hm.fountain", name="Heron Fountain", pos=(0.0, 0.0),
         note="Octagonal basin 6.8 m across the flats, kerb 0.52 m, worn "
              "dish where buckets scrape. Central pier with a heron spout at "
              "2.9 m, total 4.4 m. Built over the old town well; that is why "
              "it is off-centre in the market place and why the conduit runs "
              "in from Well Lane."),
    dict(id="hm.market.cross", name="Market Cross", pos=(-6.0, +8.0),
         note="Stepped octagonal base, shaft to 5.2 m, weather-worn heron "
              "finial. Proclamations are read from the second step."),
    dict(id="hm.bridge", name="Emberflow Bridge", pos=(-3.7, -86.0),
         note="Three segmental arches, cutwaters upstream with triangular "
              "refuges over them, deck 5.6 m between parapets, crown at "
              "-0.90 — 2.2 m of headroom over the water. The parapet is 0.3 m "
              "lower on the east because it was knocked out by a barge and "
              "rebuilt cheaply. It stands 10 m outside the north gate and 13 m "
              "of open water wide, because the north abutment's causeway "
              "narrows the channel: the departure frame is gate, causeway, "
              "bridge, and the silted ford beside it."),
    dict(id="hm.altar", name="The Summoning Altar", pos=(+43.0, -0.5),
         note="Player spawn. Dais 0.90 m, three steps, worn stone floor "
              "reading as a path from the dais to the west door."),
]

DISTRICTS = [
    dict(id="waterside", name="Waterside", cells="D2-H4",
         cause="Water and bulk. Everything heavy arrives at the bridge or the "
               "quay and cannot be carried uphill, so the trades that handle "
               "weight sit on the lowest ground within 60 m of the water.",
         holds="Stables and waggon yard, farrier, the Ferryman's Lamp, "
               "gate ward, warehouses, mill and granary."),
    dict(id="quayside", name="Quayside", cells="H2-K5",
         cause="Downstream of the bridge, so laden boats never have to pass "
               "under it, and the mere is deep enough to lie alongside. The "
               "wall runs behind the wharf, not in front of it, so the town "
               "can shut the gate without losing the moorings.",
         holds="Quay, crane, customs house, warehouse row, net lofts, rope "
               "house, fish eatery, fishers' cottages. Tannery outside, "
               "downstream."),
    dict(id="market", name="The Market Place", cells="E5-G8",
         cause="The crossing. Travellers had to stop at the ford anyway, so "
               "they were sold to where they stopped. Frontage here is the "
               "most expensive in town, which is why the plots are 5-8 m wide "
               "and 10-14 m deep and why the buildings are three storeys.",
         holds="Fountain, market cross, stalls, inn, guild, moot hall, shop "
               "row, chophouse, townhouses."),
    dict(id="knowe", name="Kirk Knowe", cells="H5-K8",
         cause="The only ground in Hearthmere that is both high and dry. A "
               "church is the one building that must never flood and the one "
               "building that wants to be seen, so it took the knowe before "
               "anything else was built.",
         holds="Church of Summoning, churchyard and graveyard, bede houses, "
               "song school, parsonage, sexton, dovecote, charnel."),
    dict(id="fireside", name="The Fire Lane", cells="G8-K10",
         cause="Ovens, tallow, glue, charcoal. Downwind (the wind blows "
               "east-south-east), on the high dry side, and separated from "
               "the thatch of the west lanes by the whole width of Ford Road.",
         holds="Bakery, cooper, carpenter, chandler, bowyer, sawshed, tithe barn."),
    dict(id="southgate", name="Southgate", cells="F10-H12",
         cause="Where the road climbs away. Carts stage here before the pull "
               "up to the quest zones, so the yard, the shed and the carter "
               "are here and the blacksmith is 40 m away across the lane.",
         holds="Waggon shed, carter, gate ward, cottages."),
    dict(id="smithward", name="Smithward", cells="C10-E11",
         cause="The high south edge: highest, driest, furthest from thatch, "
               "and the wind carries sparks east-south-east over the yard "
               "and the south wall and out of town — never toward the tenter "
               "ground's drying cloth, which sits safely upwind to the "
               "north-west. Charcoal comes in through the south gate, 60 m "
               "away.",
         holds="Blacksmith and yard, smith's house, charcoal store, cottages, byre."),
    dict(id="westlanes", name="The West Lanes", cells="A5-D9",
         cause="Poorest ground and the last to be built on: no through trade, "
               "no frontage, and the market's wash-down drains across it. "
               "Cottages, gardens, sheds, and the widest gaps between "
               "buildings in the town.",
         holds="Cottages, well-house, bathhouse, kitchen gardens, tenter "
               "ground, byre, the Bailey."),
]
