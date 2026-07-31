"""Townsfolk — the people of Hearthmere.

Placement is the whole design here. Scattering figures evenly reads as a crowd
simulation; putting them where people would actually BE reads as a town:

  - clustered at the stalls, because that is where the goods are
  - a pair angled toward each other mid-conversation
  - one alone on the fountain lip, because that is the sitting spot
  - a child running ahead of a parent
  - the smith at his anvil, the innkeeper in her doorway
  - a guard at the gate, bored, leaning

Each figure is posed for what they are doing (see core/npc.py). Positions are
in world space and match the venue placements in content/town/hearthmere.json.
"""

from __future__ import annotations

import numpy as np

from core import mesh as M
from core import npc as N
from core.mathx import rng_for
from core.venue import VenueContext

NAME = "townsfolk"
CELLS = ["C2", "C3", "D3", "C4", "D4", "C5", "B5", "E3"]

# (x, z, facing, pose, kind, y)
# Facing is radians; 0 looks toward +Z, pi toward -Z (the arriving player).
PEOPLE = [
    # --- market square: the densest cluster, because that is where trade is --
    (-3.4,  -6.2,  0.35, "talk",  "adult", 0.0),   # pair mid-conversation
    (-2.3,  -5.6,  3.40, "stand", "adult", 0.0),
    ( 4.6,  -7.1,  2.60, "work",  "adult", 0.0),   # stooped over a stall counter
    ( 6.2,  -5.0,  0.10, "carry", "adult", 0.0),   # hauling goods away
    ( 2.1,   3.4,  1.60, "stand", "adult", 0.0),
    (-5.8,   2.9,  4.60, "talk",  "adult", 0.0),
    (-4.9,   3.6,  1.45, "stand", "child", 0.0),   # child with a parent
    ( 8.4,   1.2,  3.00, "carry", "adult", 0.0),

    # Sitting on the fountain lip — the spot everyone uses.
    ( 1.75,  1.35, 2.30, "sit",   "adult", 0.90),

    # --- guild: adventurers loitering at the notice board ------------------
    (-15.8, -14.9, 3.05, "stand", "adult", 0.0),
    (-14.2, -14.2, 2.75, "talk",  "adult", 0.0),
    (-10.6, -13.8, 3.30, "lean",  "adult", 0.0),   # leaning on the porch wall

    # --- inn: innkeeper in the doorway, a traveller arriving --------------
    ( 18.9,  -8.2, 4.55, "stand", "adult", 0.0),
    ( 20.4,  -5.4, 3.90, "carry", "adult", 0.0),

    # --- pub: two locals at the trestle tables ----------------------------
    (-21.4,  -2.6, 1.20, "sit",   "adult", 0.75),
    (-20.2,  -1.4, 4.30, "sit",   "adult", 0.75),

    # --- blacksmith: the smith at his anvil -------------------------------
    (-21.6,  26.4, 2.10, "work",  "adult", 0.0),

    # --- shop row: a customer at the apothecary counter -------------------
    (  3.2,  19.6, 0.20, "stand", "adult", 0.0),
    (  8.8,  19.9, 0.45, "talk",  "adult", 0.0),

    # --- north gate: a bored guard ----------------------------------------
    (  3.1, -41.0, 3.14, "lean",  "adult", 0.0),

    # --- a child running ahead down Ford Road -----------------------------
    ( -1.6, -18.5, 3.10, "stand", "child", 0.0),
]


# People in conversation look AT each other. Hand-authored angles had all four
# pairs facing 41-150 degrees away, including an adult standing back-to-back
# with the child it is captioned as accompanying — so the facing for the second
# member of each pair is derived from the first rather than guessed.
PAIRS = [(0, 1), (5, 6), (10, 9), (18, 17)]


def build(ctx: VenueContext, asset_id="hm.folk"):
    rng = rng_for(asset_id, "townsfolk")

    faces = {}
    for a, b in PAIRS:
        ax, az = PEOPLE[a][0], PEOPLE[a][1]
        bx, bz = PEOPLE[b][0], PEOPLE[b][1]
        faces[a] = float(np.arctan2(bx - ax, bz - az))
        faces[b] = float(np.arctan2(ax - bx, az - bz))

    for i, (x, z, facing, pose, kind, y) in enumerate(PEOPLE):
        yaw = faces.get(i, facing) + rng.uniform(-0.08, 0.08)
        f = N.figure(f"{asset_id}.{i:02d}", pose=pose, child=(kind == "child"))
        f.rotate_y(yaw)
        f.translate(x, y, z)
        ctx.emit(f)

        # Every person is an entity: they are the things a player will want to
        # talk to, and they are the unit that later carries a schedule and gets
        # replicated. Art §2 — anything that can be interacted with gets an ID.
        # Record the facing. The mesh was rotated but the entity carried an
        # identity quaternion, so anything reading the DATA — a server, a
        # replication layer, an Unreal import — would face every NPC north.
        ctx.entity(f"{asset_id}.{i:02d}", f"npc.{pose}", (x, y, z),
                   rot=[0.0, float(np.sin(yaw * 0.5)), 0.0, float(np.cos(yaw * 0.5))],
                   verbs=["talk"],
                   npc={"pose": pose, "kind": kind,
                        "schedule": "static_v0"})

    # A dog asleep in the sun near the fountain, and pigeons on the paving.
    # Animals are cheap and buy a lot of life — Art Bible §7, residue over polish.
    dog = M.Group()
    body = M.lathe([(0.0, 0), (0.135, 0.06), (0.155, 0.38), (0.09, 0.54)], 9, "cloth_brown")
    body.rotate_z(np.pi * 0.5)
    dog.add(body)
    head = M.lathe([(0.0, 0), (0.09, 0.05), (0.062, 0.15)], 8, "cloth_brown")
    head.rotate_z(np.pi * 0.5)
    head.translate(0.58, 0.02, 0)
    dog.add(head)
    dog.rotate_y(-0.8)
    dog.translate(5.9, 0.10, 5.2)
    ctx.emit(dog)

    for i in range(11):
        a = rng.uniform(0, 6.283)
        d = rng.uniform(1.2, 7.5)
        p = M.lathe([(0.0, 0), (0.055, 0.035), (0.045, 0.10), (0.0, 0.13)], 7,
                    "cloth_cream" if rng.random() < 0.5 else "cloth_brown")
        p.rotate_z(rng.uniform(-0.1, 0.1))
        p.rotate_y(rng.uniform(0, 6.283))
        p.translate(np.cos(a) * d, 0.0, 4.0 + np.sin(a) * d * 0.6)
        ctx.emit(p)
