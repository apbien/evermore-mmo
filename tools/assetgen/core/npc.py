"""Townsfolk.

The single largest gap between amateur and shipped environment art is not
polygon count or material quality — it is whether anyone lives there. A
perfectly built empty town reads as a diorama. Hearthmere needs people in it,
and it needs them doing something.

There is no skeletal animation in this pipeline, so these are POSED figures:
each is built directly into an attitude — leaning on a counter, sitting on the
fountain lip, carrying a sack, stooped over a bench. A posed figure in a
plausible place reads as alive; a rank of identical T-posed mannequins reads
worse than an empty street.

Proportions follow Art Bible §3: 1.75m adult, eye at 1.62m, shoulders 0.45m.
Children are built at 0.62 scale with a proportionally larger head, which is
what actually reads as "child" rather than "small adult".
"""

from __future__ import annotations

import numpy as np

from . import mesh as M
from .mathx import rng_for

# Art Bible §3.
ADULT_H = 1.75
SHOULDER = 0.45

CLOTHES = ["cloth_blue", "cloth_green", "cloth_rust", "cloth_cream", "cloth_brown"]
HAIRS = ["hair_dark", "hair_fair"]


def _limb(length, r0, r1, mat, seg=9):
    """Tapered limb segment, built along +Y from the origin."""
    return M.lathe([(r0, 0.0), (r0 * 0.96, length * 0.35),
                    (r1 * 1.04, length * 0.75), (r1, length)], seg, mat)


def figure(asset_id, pose="stand", height=ADULT_H, cloth=None, hair_mat=None,
           skin="skin", child=False):
    """One townsperson in a fixed pose.

    `pose` is the whole point — it is what makes the figure read as a person
    doing something rather than as a mannequin:
      stand    — weight on one leg, slight contrapposto
      talk     — turned, one arm raised mid-gesture
      lean     — leaning back against a wall, ankles crossed
      sit      — sitting on a ledge or bench, legs hanging
      carry    — stooped slightly, arms forward under a load
      work     — bent over a counter or bench, arms down and forward
    """
    rng = rng_for(asset_id, "npc", pose)
    cloth = cloth or CLOTHES[int(rng.integers(0, len(CLOTHES)))]
    hair_mat = hair_mat or HAIRS[int(rng.integers(0, len(HAIRS)))]

    h = height * (0.62 if child else 1.0) * rng.uniform(0.96, 1.05)
    s = h / ADULT_H                        # uniform scale factor from the canon
    head_r = 0.115 * (1.28 if child else 1.0) * s
    out = M.Group()

    # --- torso ------------------------------------------------------------
    # Tapered: wider at the shoulder, narrower at the waist. A straight capsule
    # is the single biggest tell of a placeholder body.
    hip_y = 0.92 * s
    sh_y = 1.42 * s
    torso = M.lathe([
        (0.135 * s, hip_y),
        (0.150 * s, hip_y + 0.10 * s),
        (0.168 * s, sh_y - 0.16 * s),
        (0.175 * s, sh_y - 0.04 * s),
        (0.120 * s, sh_y + 0.02 * s),
    ], 18, cloth)
    out.add(torso)

    # Skirt / tunic hem — breaks the leg line and reads as clothing, not paint.
    hem_len = rng.uniform(0.20, 0.38) * s
    hem = M.lathe([(0.150 * s, hip_y - hem_len), (0.135 * s, hip_y)], 18, cloth,
                  close_bottom=False, close_top=False)
    out.add(hem)

    # --- head, neck, hair -------------------------------------------------
    neck = M.cylinder(0.050 * s, 0.13 * s, 10, 0.004, skin)
    neck.translate(0, sh_y - 0.03 * s, 0)
    out.add(neck)

    head = M.lathe([(0.0, 0), (head_r * 0.62, head_r * 0.28),
                    (head_r * 0.88, head_r * 0.72), (head_r, head_r * 1.20),
                    (head_r * 0.94, head_r * 1.62), (head_r * 0.66, head_r * 1.94),
                    (0.0, head_r * 2.10)], 16, skin)
    head_y = sh_y + 0.005 * s
    head.translate(0, head_y, 0)
    out.add(head)

    # Hair as a shell over the skull, longer at the back.
    hr = M.lathe([(0.0, 0), (head_r * 0.90, head_r * 0.62),
                  (head_r * 1.06, head_r * 1.20),
                  (head_r * 0.92, head_r * 1.82), (0.0, head_r * 2.10)], 16, hair_mat)
    hr.scale(1.0, 1.0, 1.06)
    hr.translate(0, head_y + head_r * 0.06, -head_r * 0.06)
    out.add(hr)

    # --- arms -------------------------------------------------------------
    # Pose drives shoulder and elbow angles. These are hand-tuned per pose
    # rather than procedural, because a wrong arm angle reads as broken.
    arm_len = 0.30 * s
    pose_arms = {
        "stand": [(-0.10, 0.10), (0.10, -0.06)],
        "talk":  [(-0.75, -0.55), (0.16, -0.10)],
        "lean":  [(0.22, 0.40), (-0.20, 0.30)],
        "sit":   [(-0.35, 0.55), (-0.30, 0.50)],
        "carry": [(-0.95, -0.75), (-0.95, -0.75)],
        "work":  [(-1.05, -0.35), (-1.00, -0.30)],
    }[pose]

    # Built as a hierarchy: the forearm is placed at the elbow in the UPPER
    # ARM's local space, then the whole arm is rotated about the shoulder.
    # Positioning the forearm in world space from a separately-derived elbow
    # position is what left every forearm floating detached from its elbow.
    for i, (sx, (sh_rot, el_rot)) in enumerate(zip((-1, 1), pose_arms)):
        arm = M.Group()

        upper = _limb(arm_len, 0.052 * s, 0.044 * s, cloth)
        upper.rotate_x(np.pi)              # hangs down from the origin
        arm.add(upper)

        # Forearm: hangs from its own origin, bent at the elbow, then moved
        # DOWN by exactly the upper arm's length so it meets the joint.
        fore = _limb(arm_len * 0.95, 0.042 * s, 0.034 * s, skin)
        fore.rotate_x(np.pi)
        fore.rotate_x(-el_rot)
        fore.translate(0, -arm_len, 0)
        arm.add(fore)

        hand = M.lathe([(0.0, 0), (0.036 * s, 0.02 * s), (0.030 * s, 0.075 * s),
                        (0.0, 0.095 * s)], 8, skin)
        hand.rotate_x(np.pi)
        hand.rotate_x(-el_rot)
        hand.translate(np.sin(el_rot) * arm_len * 0.95,
                       -arm_len - np.cos(el_rot) * arm_len * 0.95, 0)
        arm.add(hand)

        arm.rotate_x(-sh_rot)              # swing the whole arm at the shoulder
        arm.rotate_z(sx * 0.10)
        arm.translate(sx * SHOULDER * 0.5 * s, sh_y - 0.03 * s, 0)
        out.add(arm)

    # --- legs -------------------------------------------------------------
    leg_len = hip_y * 0.52
    if pose == "sit":
        # Thigh forward, shin down: the figure is sitting on something.
        for sx in (-1, 1):
            thigh = _limb(leg_len, 0.070 * s, 0.060 * s, cloth)
            thigh.rotate_x(np.pi * 0.5)
            thigh.translate(sx * 0.095 * s, hip_y - 0.02 * s, 0)
            out.add(thigh)
            shin = _limb(leg_len, 0.056 * s, 0.046 * s, cloth)
            shin.rotate_x(np.pi)
            shin.translate(sx * 0.095 * s, hip_y - 0.02 * s, leg_len)
            out.add(shin)
            boot = M.box(0.085 * s, 0.07 * s, 0.19 * s, 0.01, "oak_dark")
            boot.translate(sx * 0.095 * s, hip_y - leg_len - 0.02 * s, leg_len + 0.03 * s)
            out.add(boot)
    else:
        # Contrapposto: weight on one leg, the other relaxed and turned out.
        weight = 1 if rng.random() < 0.5 else -1
        for sx in (-1, 1):
            relaxed = (sx != weight)
            ang = rng.uniform(0.08, 0.20) if relaxed else rng.uniform(-0.03, 0.03)
            thigh = _limb(leg_len, 0.072 * s, 0.058 * s, cloth)
            thigh.rotate_x(np.pi)
            thigh.rotate_x(ang)
            thigh.rotate_z(sx * 0.03)
            thigh.translate(sx * 0.095 * s, hip_y, 0)
            out.add(thigh)

            ky = hip_y - leg_len * np.cos(ang)
            kz = leg_len * np.sin(ang)
            shin = _limb(leg_len, 0.054 * s, 0.044 * s, skin if rng.random() < 0.3 else cloth)
            shin.rotate_x(np.pi)
            shin.rotate_x(-ang * 0.55)
            shin.translate(sx * 0.095 * s, ky, kz)
            out.add(shin)

            boot = M.box(0.090 * s, 0.075 * s, 0.21 * s, 0.010, "oak_dark")
            boot.rotate_y(sx * rng.uniform(0.05, 0.22))
            boot.translate(sx * 0.098 * s, 0.037 * s, kz + 0.02 * s)
            out.add(boot)

    # --- pose adjustments to the whole figure ----------------------------
    if pose == "lean":
        out.rotate_x(-0.10)                # tipped back against a wall
    elif pose in ("carry", "work"):
        out.rotate_x(0.13)                 # stooped over the load or bench

    return out


def crowd(asset_id, placements):
    """Build several figures from (x, z, facing_rad, pose) tuples.

    `placements` carries the composition. Where people STAND is what makes a
    town read as inhabited — clustered at the stalls, one alone at the well,
    a pair mid-conversation angled toward each other.
    """
    rng = rng_for(asset_id, "crowd")
    out = M.Group()
    for i, p in enumerate(placements):
        x, z, facing, pose = p[0], p[1], p[2], p[3]
        child = len(p) > 4 and p[4] == "child"
        f = figure(f"{asset_id}.{i:02d}", pose=pose, child=child)
        f.rotate_y(facing + rng.uniform(-0.12, 0.12))
        f.translate(x, p[5] if len(p) > 5 else 0.0, z)
        out.add(f)
    return out
