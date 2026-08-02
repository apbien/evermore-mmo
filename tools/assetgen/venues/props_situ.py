"""Dressing in situ — a REVIEW HARNESS, not a town venue.

The prop sheet proves each builder in isolation on flat paving. That is not the
question. The question is whether `props.dress_yard` and `props.dress_workbench`
produce something that reads as a working place when they are put inside real
walls, on real ground that falls, at the gameplay camera.

So this stands a three-sided cooper's yard and a lean-to workbench on the
terrain at the waggon-yard site off Ford Road, and nothing in it is authored
flat: the yard surface is draped on `core/terrain.py` and every wall foot is
taken from `terrain.height`. Like `props_sheet` it is absent from
`content/town/hearthmere.json` and can never be placed in the town.

    python tools/assetgen/build.py --skip-textures --venue props_situ
    node tools/render/shoot.mjs --asset assets/meshes/props_situ.gltf \
        --site 14.8,-29.9 --views free --from 0,1.62,-9 --to 0,1.2,1 \
        --figureAt 1 --out review/shots/props
"""

from __future__ import annotations

import numpy as np

from core import mesh as M
from core import kit as K
from core import props as P
from core import terrain
from core.mathx import rng_for
from core.venue import VenueContext

NAME = "props_situ"
CELLS = []

# A back plot on The Bailey, behind the ropehouse. Chosen by SEARCHING
# `terrain.height` for a spot with real fall across a yard-sized footprint —
# the first site picked by eye (the waggon yard at 14.8,-29.9) turned out to
# sit on an authored building pad and was dead flat, which would have tested
# nothing. This one drops 0.67 m across 9 x 6 m.
SITE = (65.0, -30.0)

YARD_W, YARD_D = 8.8, 6.4
WALL_H = 3.10
SHED_W, SHED_D = 4.2, 2.8


def _h(lx, lz, h0):
    """Terrain height at a venue-local point, relative to the site datum."""
    return float(terrain.height(SITE[0] + lx, SITE[1] + lz)) - h0


def _yard_surface(asset_id, h0, w, d, z0):
    """Beaten-earth yard, draped on the real ground and stood proud of it.

    D-035's rule: a made surface follows the terrain and then lifts clear of
    it by `kit.MADE_LIFT`, or the height field's own roughness comes through
    the paving and the two z-fight into a patchwork.
    """
    out = M.Mesh(mat="dirt")
    n = 8
    for i in range(n):
        for j in range(n):
            x0 = -w * 0.5 + i * w / n
            zz0 = z0 - d + j * d / n
            q = M.quad(w / n * 1.02, d / n * 1.02, "dirt")
            q.translate(x0 + w / n * 0.5, 0, zz0 + d / n * 0.5)
            # Per-vertex drape, so the surface tracks the fall instead of
            # hovering over it at the corners.
            for k in range(len(q.v)):
                q.v[k, 1] = _h(float(q.v[k, 0]), float(q.v[k, 2]), h0) + K.MADE_LIFT
            # UVs from WORLD position, not from the tile. `mesh.quad` lays each
            # tile out 0..w, so 64 tiles all sample the same corner of the dirt
            # texture and the yard comes out as a chequer of identical blotches
            # — which is exactly what the first render showed.
            q.uv = np.stack([q.v[:, 0] * 0.4, q.v[:, 2] * 0.4], axis=1).astype(np.float32)
            out.merge(q)
    return out


def build(ctx: VenueContext, asset_id="hm.situ"):
    rng = rng_for(asset_id, "situ")
    h0 = float(terrain.height(*SITE))
    back_z = 0.0                                    # the yard's back wall plane

    fall = [_h(x, z, h0) for x in (-4.4, 4.4) for z in (-6.4, 0.0)]
    print(f"\n  props_situ at {SITE} — datum y={h0:.3f} m, "
          f"ground falls {max(fall) - min(fall):.2f} m across the yard")

    ctx.emit(_yard_surface(f"{asset_id}.ground", h0, YARD_W + 3.6,
                           YARD_D + 6.0, back_z + 0.9))

    # --- the three walls -------------------------------------------------
    # Each wall's foot is taken from the terrain under its own centre and its
    # plinth is deepened to swallow the fall, which is what a real plinth is
    # for. Nothing here assumes y = 0.
    def wall(lx, lz, width, rot=0.0, tag="wall"):
        g = M.Group()
        y = min(_h(lx + np.cos(rot) * width * 0.5, lz + np.sin(rot) * width * 0.5, h0),
                _h(lx - np.cos(rot) * width * 0.5, lz - np.sin(rot) * width * 0.5, h0))
        plinth_h = 0.55 + (max(_h(lx, lz, h0), y) - y)
        g.add(K.stone_plinth(width, 0.34, plinth_h))
        g.add(K.timber_frame_wall(width, WALL_H - plinth_h, f"{asset_id}.{tag}",
                                  style="square", depth=0.28, sill_y=plinth_h))
        g.rotate_y(rot)
        g.translate(lx, y, lz)
        ctx.emit(g)
        ctx.collider("box", center=(lx, y + WALL_H * 0.5, lz),
                     half=(width * 0.5, WALL_H * 0.5, 0.17), rot_y=rot, tag=tag)

    wall(0.0, back_z, YARD_W, 0.0, "back")
    for sx in (-1, 1):
        wall(sx * YARD_W * 0.5, back_z - YARD_D * 0.5, YARD_D,
             np.pi * 0.5, f"side{sx}")

    # --- the dressing, which is the whole point --------------------------
    yard = P.dress_yard(f"{asset_id}.yard", width=YARD_W, depth=YARD_D,
                        trade="cooper", ctx=ctx, wall_z=back_z - 0.16,
                        waggon_load="barrels", laundry=True)
    # Seated, not draped: an arrangement is a set of objects standing on the
    # ground, so it moves bodily onto the ground under its own centre rather
    # than being warped per vertex (D-035).
    yard.translate(0, _h(0.0, back_z - YARD_D * 0.45, h0) + K.MADE_LIFT, 0)
    ctx.emit(yard)

    # --- lean-to with the workbench in it --------------------------------
    sx0 = -YARD_W * 0.5 + SHED_W * 0.5 + 0.35
    sz0 = back_z - YARD_D - 1.35
    sy = _h(sx0, sz0, h0) + K.MADE_LIFT
    shed = M.Group()
    for dx in (-1, 1):
        for dz in (-1, 1):
            hgt = 2.45 if dz < 0 else 2.95         # roof falls to the front
            p = M.box(0.16, hgt, 0.16, K.CHAMFER_ARCH, "oak_dark")
            p.translate(dx * SHED_W * 0.5, hgt * 0.5, dz * SHED_D * 0.5)
            shed.add(p)
    for dz, hgt in ((-1, 2.45), (1, 2.95)):
        pl = M.plank(SHED_W + 0.3, 0.20, 0.18, K.CHAMFER_ARCH, "oak_dark")
        pl.translate(0, hgt + 0.06, dz * SHED_D * 0.5)
        shed.add(pl)
    for i in range(7):
        x = -SHED_W * 0.5 + (i + 0.5) * SHED_W / 7
        r = M.plank(SHED_D + 0.55, 0.10, 0.09, K.CHAMFER_ARCH, "oak_dark",
                    grain_axis=1)
        r.rotate_y(np.pi * 0.5)
        r.rotate_x(0.175)
        r.translate(x, 2.76, 0)
        shed.add(r)
    cov = M.box(SHED_W + 0.4, 0.09, SHED_D + 0.75, 0.01, "reed")
    cov.rotate_x(0.175)
    cov.translate(0, 2.84, 0)
    shed.add(cov)
    # Boarded back. `dress_workbench(wall_z=...)` hangs its saws and its brace
    # on a wall; giving it a plane with no wall in it is precisely the failure
    # core/props.py documents, and the first render of this venue had three
    # saws hanging in open air two metres above the yard.
    for i in range(int(SHED_W / 0.26)):
        b = M.box(0.245, 2.42, 0.030, 0.005, "oak_weathered")
        b.rotate_z(rng.uniform(-0.005, 0.005))
        b.translate(-SHED_W * 0.5 + (i + 0.5) * 0.26, 1.21, SHED_D * 0.5 + 0.02)
        shed.add(b)
    shed.translate(sx0, sy, sz0)
    ctx.emit(shed)
    for dx in (-1, 1):
        for dz in (-1, 1):
            ctx.collider("box", center=(sx0 + dx * SHED_W * 0.5, sy + 1.2,
                                        sz0 + dz * SHED_D * 0.5),
                         half=(0.10, 1.2, 0.10), tag="shed_post")

    bench = P.dress_workbench(f"{asset_id}.bench", trade="carpenter",
                              length=2.4, wall_z=SHED_D * 0.5 - 0.10, ctx=None)
    bench.translate(sx0, sy, sz0)
    ctx.emit(bench)
    ctx.collider("box", center=(sx0, sy + 0.43, sz0 + SHED_D * 0.5 - 0.5),
                 half=(1.2, 0.43, 0.31), tag="workbench")

    # A threshold dressing at the yard gate, where the player walks in.
    thr = P.dress_threshold(f"{asset_id}.thr", width=1.8, wall_z=0.0, ctx=None)
    thr.rotate_y(np.pi)
    thr.translate(YARD_W * 0.5 - 0.9,
                  _h(YARD_W * 0.5 - 0.9, back_z - YARD_D - 0.2, h0) + K.MADE_LIFT,
                  back_z - YARD_D - 0.2)
    ctx.emit(thr)
