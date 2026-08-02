"""Prop sheet — a REVIEW HARNESS, not a town venue.

Lays every builder in `core/props.py` out on a measured grid with 1.75 m scale
figures down each row, so the whole residue library can be judged in one frame
against the Art Bible §3 scale table. It is not listed in
`content/town/hearthmere.json` and is never placed in the town; `tools/render/
town.mjs` assembles from that file, so this cannot leak into a town render.

    python tools/assetgen/build.py --skip-textures --venue props_sheet
    node tools/render/shoot.mjs --asset assets/meshes/props_sheet.gltf \
        --views free --from 0,15,-26 --to 0,0.6,1 --no-ground --no-figure \
        --out review/shots/props

Two things the sheet has to supply or half the library judges as broken:

- **A wall.** A large part of the vocabulary is wall-dependent by design — a
  broom leans on one, a water butt hangs under a gutter, a tool rack is pegged
  to one. Cells marked `w` get a plaster wall at their own `z = 0`, which is
  the frame `core/props.py` documents. Without it those props read as floating
  and the review is measuring the harness rather than the prop.
- **A counter.** The trade instruments are 0.2-0.5 m objects that live at
  0.74-1.05 m in the real world. On the floor of a 2.6 m cell they are specks.
  Cells marked `t` get a trestle table and the prop sits on it.

`--no-figure`: the harness's own reference figure has no defined position in a
`free` view and hangs in mid-air. The sheet carries its own, one per row.

Deliberately no lettering in the geometry: Art Bible §2 bans readable text
anywhere, and a review sheet that breaks the rule it exists to check is worse
than no sheet. The index is printed to stdout at build time instead.
"""

from __future__ import annotations

import numpy as np

from core import mesh as M
from core import kit as K
from core import props as P
from core.mathx import rng_for
from core.venue import VenueContext

NAME = "props_sheet"

# The sheet exists to show each MATERIAL on its own prop. Folding thirty-six of
# them onto one atlas page would make it show the page instead, which is the
# one thing a material review harness may not do.
ATLAS = False
CELLS = []

PITCH = 3.0
COLS = 8
WALL_H = 2.9
TABLE_H = 0.74


def _figure(asset_id):
    """A 1.75 m scale reference. Art Bible §3, and §8 requires one in every
    review render.

    Proportions off the §3 table: 1.75 m tall, 1.62 m eye, 0.45 m across the
    shoulders, and legs that are half the total height. Crude on purpose — it
    is a ruler, not a character, and NPCs are out of scope per Directive §1 —
    but separate legs and a real shoulder line matter, because a single box
    reads as a bollard and the eye stops using it for scale.
    """
    out = M.Group()
    for sx in (-1, 1):
        leg = M.box(0.155, 0.88, 0.19, 0.02, "cloth_brown")
        leg.translate(sx * 0.095, 0.44, 0)
        out.add(leg)
    torso = M.chamfered_prism([(-0.155, 0.0), (0.155, 0.0), (0.225, 0.50),
                               (-0.225, 0.50)], 0.24, "cloth_blue", 0.02)
    torso.translate(0, 0.88, 0)
    out.add(torso)
    for sx in (-1, 1):
        arm = M.box(0.095, 0.56, 0.11, 0.015, "cloth_blue")
        arm.rotate_z(-sx * 0.06)
        arm.translate(sx * 0.235, 1.10, 0)
        out.add(arm)
    neck = M.cylinder(0.050, 0.075, 8, 0.01, "fleece")
    neck.translate(0, 1.385, 0)
    out.add(neck)
    head = M.globe(0.098, "fleece", 9, 5, sy=1.25)
    head.translate(0, 1.75 - 0.1225, 0)
    out.add(head)
    return out


def _entries():
    """(label, builder, flags) for everything in the library.

    flags: `w` needs a wall behind it, `t` sits on a counter.
    """
    E = []
    sid = "hm.sheet"

    def add(label, fn, flags=""):
        E.append((label, fn, flags))

    # --- transport and haulage -------------------------------------------
    add("cart_wheel", lambda i: P.cart_wheel(f"{sid}.{i}").translate(0, 0.575, 0))
    add("handcart", lambda i: P.handcart(f"{sid}.{i}"))
    add("waggon/barrels", lambda i: P.waggon(f"{sid}.{i}", load="barrels"))
    add("waggon/hay", lambda i: P.waggon(f"{sid}.{i}", load="hay"))
    add("sledge", lambda i: P.sledge(f"{sid}.{i}"))
    add("wheelbarrow", lambda i: P.wheelbarrow(f"{sid}.{i}"))
    add("yoke_and_buckets", lambda i: P.yoke_and_buckets(f"{sid}.{i}"))
    add("panniers", lambda i: P.panniers(f"{sid}.{i}"))

    # --- storage and trade -----------------------------------------------
    add("broken_wheel", lambda i: P.broken_wheel(f"{sid}.{i}"), "w")
    add("barrel (kit)", lambda i: K.barrel(f"{sid}.{i}"))
    add("barrel_lying", lambda i: P.barrel_lying(f"{sid}.{i}"))
    add("bucket", lambda i: P.bucket(f"{sid}.{i}", full=True))
    add("sack_stack", lambda i: P.sack_stack(f"{sid}.{i}", count=5, wall_z=0.0), "w")
    add("crate", lambda i: P.crate(f"{sid}.{i}", lid=True))
    add("crate_stack", lambda i: P.crate_stack(f"{sid}.{i}", count=4, wall_z=0.0), "w")
    add("amphora", lambda i: P.amphora(f"{sid}.{i}"))
    add("glazed_jar", lambda i: P.glazed_jar(f"{sid}.{i}"))
    add("jar_cluster", lambda i: P.jar_cluster(f"{sid}.{i}"))
    add("basket/stake", lambda i: P.basket(f"{sid}.{i}", weave="stake",
                                           handle=True, fill="apples"))
    add("basket/coil", lambda i: P.basket(f"{sid}.{i}", weave="coil", fill="loaves"))
    add("basket/slath", lambda i: P.basket(f"{sid}.{i}", weave="slath", fill="grain"))
    add("basket/spale", lambda i: P.basket(f"{sid}.{i}", weave="spale", fill="wool"))
    add("rope_coil (kit)", lambda i: K.rope_coil(f"{sid}.{i}"))
    add("cloth_bolt", lambda i: P.cloth_bolt(f"{sid}.{i}", loose=0.45), "t")
    add("bolt_rack", lambda i: P.bolt_rack(f"{sid}.{i}"))
    add("hanging_scales", lambda i: P.hanging_scales(f"{sid}.{i}").translate(
        0, 2.05, -0.34), "w")
    add("weight_set", lambda i: P.weight_set(f"{sid}.{i}"), "t")
    add("counting_board", lambda i: P.counting_board(f"{sid}.{i}"), "t")
    add("coin_scales", lambda i: P.coin_scales(f"{sid}.{i}"), "t")
    add("poultry_crate", lambda i: P.poultry_crate(f"{sid}.{i}"))

    # --- trade stations ---------------------------------------------------
    add("smith_tools", lambda i: P.smith_tools(f"{sid}.{i}"), "w")
    add("cooper_setup", lambda i: P.cooper_setup(f"{sid}.{i}"), "w")
    add("carpenter_bench", lambda i: P.carpenter_bench(f"{sid}.{i}"), "w")
    add("baker_kit", lambda i: P.baker_kit(f"{sid}.{i}"), "w")
    add("chandler_kit", lambda i: P.chandler_kit(f"{sid}.{i}"), "w")
    add("tanner_kit", lambda i: P.tanner_kit(f"{sid}.{i}"), "w")
    add("bowyer_kit", lambda i: P.bowyer_kit(f"{sid}.{i}"), "w")
    add("fishmonger_kit", lambda i: P.fishmonger_kit(f"{sid}.{i}"), "w")

    # --- domestic and street ---------------------------------------------
    add("laundry_line", lambda i: P.laundry_line(
        f"{sid}.{i}", (-1.30, 2.55, -0.5), (1.30, 2.40, 0.5), items=4))
    add("broom", lambda i: P.broom(f"{sid}.{i}", wall_z=0.0), "w")
    add("boot_scraper", lambda i: P.boot_scraper(f"{sid}.{i}"), "w")
    add("stool", lambda i: P.stool(f"{sid}.{i}"))
    add("chair + cloak", lambda i: P.chair(f"{sid}.{i}"))
    add("mug", lambda i: P.mug(f"{sid}.{i}"), "t")
    add("spill/grain", lambda i: P.spill(f"{sid}.{i}", kind="grain"))
    add("spill/coal", lambda i: P.spill(f"{sid}.{i}", kind="coal"))
    add("meal", lambda i: P.meal(f"{sid}.{i}"), "t")
    add("dice_on_barrel", lambda i: P.dice_on_barrel(f"{sid}.{i}"))
    add("worn_patch/cat", lambda i: P.worn_patch(f"{sid}.{i}", shape="cat"))
    add("firewood_stack", lambda i: P.firewood_stack(f"{sid}.{i}", wall_z=0.0), "w")
    add("kindling", lambda i: P.kindling(f"{sid}.{i}"))
    add("chopping_block", lambda i: P.chopping_block(f"{sid}.{i}"))
    add("water_butt", lambda i: P.water_butt(f"{sid}.{i}"), "w")
    add("drying_herbs", lambda i: P.drying_herbs(f"{sid}.{i}"), "w")
    add("hanging_game", lambda i: P.hanging_game(f"{sid}.{i}"), "w")
    add("beehive", lambda i: P.beehive(f"{sid}.{i}"))
    add("dovecote_holes", lambda i: P.dovecote_holes(f"{sid}.{i}"), "w")

    # --- kit props already shipped, shown for cohesion --------------------
    add("trestle_table (kit)", lambda i: K.trestle_table(f"{sid}.{i}"))
    add("bench (kit)", lambda i: K.bench(f"{sid}.{i}"))
    add("lantern (kit)", lambda i: K.lantern(f"{sid}.{i}").translate(0, 1.55, -0.10),
        "w")

    # --- dressing functions ----------------------------------------------
    add("dress_threshold", lambda i: P.dress_threshold(f"{sid}.{i}"), "w")
    add("dress_shopfront", lambda i: P.dress_shopfront(f"{sid}.{i}", width=3.2), "w")
    add("dress_workbench", lambda i: P.dress_workbench(f"{sid}.{i}",
                                                       trade="carpenter"), "w")
    return E


def _wall(asset_id, width, height):
    """A plaster wall segment on a plinth — the thing half the library leans on.

    Sized to the prop rather than to a constant. A uniform 2.9 m wall behind
    every cell turned the sheet into a maze: the front row's walls occluded the
    two rows behind them and the review measured the harness. Each wall is now
    just tall enough to carry what leans on it, so most of them are waist-high
    and only the dovecote's is full height.

    Pushed back by half its own depth so the FACE lands on the cell's `z = 0`,
    which is the plane `core/props.py` leans and hangs everything against.
    Leaving it centred buries every leaning object 13 cm into the plaster.
    """
    out = M.Group()
    depth = 0.26
    out.add(K.stone_plinth(width, depth, 0.42))
    out.add(K.timber_frame_wall(width, max(0.5, height - 0.42), asset_id,
                                style="square", depth=depth, sill_y=0.42))
    out.translate(0, 0, depth * 0.5)
    return out


def build(ctx: VenueContext, asset_id="hm.sheet"):
    rng = rng_for(asset_id, "sheet")
    entries = _entries()
    rows = (len(entries) + COLS - 1) // COLS
    w = COLS * PITCH
    d = rows * PITCH

    # Chequered ground so every cell is countable from a top-down view. This is
    # the only place in the repo where a hard grid is correct.
    for r in range(rows):
        for c in range(COLS):
            tile = M.box(PITCH - 0.04, 0.08, PITCH - 0.04, 0.01,
                         "sett" if (r + c) % 2 else "cobble")
            tile.translate(-w * 0.5 + (c + 0.5) * PITCH, -0.04,
                           -d * 0.5 + (r + 0.5) * PITCH)
            ctx.emit(tile)

    print(f"\n  props_sheet index — {len(entries)} builders, "
          f"{COLS} cols x {rows} rows at {PITCH} m, origin at grid centre")
    tri_by = []
    for n, (label, fn, flags) in enumerate(entries):
        r, c = divmod(n, COLS)
        x = -w * 0.5 + (c + 0.5) * PITCH
        z = -d * 0.5 + (r + 0.5) * PITCH
        cell = M.Group()
        g = fn(n)
        if "t" in flags:
            cell.add(K.trestle_table(f"{asset_id}.tbl.{n}", length=1.5, width=0.65))
            g.translate(0, TABLE_H + 0.042, 0)
        tri_by.append((label, g.tri_count))
        if "w" in flags:
            lo, hi = g.bounds()
            cell.add(_wall(f"{asset_id}.wall.{n}", PITCH - 0.9,
                           float(np.clip(hi[1] + 0.35, 1.25, WALL_H))))
        cell.add(g)
        # Backed up into the rear third of the cell, so the working area in
        # front of the wall is what the camera sees.
        cell.translate(x, 0.0, z + PITCH * 0.30)
        ctx.emit(cell)
        print(f"    r{r}c{c}  {label:22s} {g.tri_count:7,d} tris  "
              f"{'[wall]' if 'w' in flags else '      '}"
              f"{'[table]' if 't' in flags else '       '} at {x:+6.1f},{z:+6.1f}")

    # A 1.75 m figure at the head of every row — Art Bible §8 requires a scale
    # reference, and one figure at the corner of a 24 m sheet cannot be
    # compared with a prop at the far end of it.
    for r in range(rows):
        f = _figure(f"{asset_id}.fig.{r}")
        f.rotate_y(rng.uniform(-0.3, 0.3))
        f.translate(-w * 0.5 - 1.2, 0.0, -d * 0.5 + (r + 0.5) * PITCH)
        ctx.emit(f)

    tot = sum(t for _, t in tri_by)
    worst = sorted(tri_by, key=lambda kv: -kv[1])[:8]
    print(f"    total {tot:,} tris across {len(entries)} builders; heaviest: "
          + ", ".join(f"{k} {v:,}" for k, v in worst))
    ctx.collider("box", center=(0, 0.04, 0), half=(w * 0.5, 0.04, d * 0.5),
                 kind="surface", tag="sheet")
