#!/usr/bin/env python3
"""Tests for the Directive §7 build-time pipeline: batching, LOD, instancing.

    python tools/test_batching.py

These exist because two of the three techniques currently have NO consumer in
the town. `ctx.instance` has exactly one (the streets' verge scatter) and
`ctx.interior` has none at all — the church that will use it is not built yet.
An export path nobody exercises is an export path that is wrong, and the agent
who finds out is the one who cannot see their church from the street and has no
idea which of the two of us broke it.

So this builds a synthetic venue into a temp directory, exercises every branch,
and asserts on the glTF that comes out. It is fast (a second) and it is the only
thing standing between `ctx.instance(...)` being an API and being a promise.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "assetgen"))

from core import batch as B                     # noqa: E402
from core import mesh as M                      # noqa: E402
from core import venue as V                     # noqa: E402

fails = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        fails.append(msg)


def build(tmp, **kw):
    """Build a synthetic venue into `tmp` and return its parsed glTF."""
    V.MESH_DIR = V.ENT_DIR = V.COL_DIR = tmp
    ctx = V.VenueContext("t_batch", ["A1"], **kw)

    # Two buildings, 40 m apart, so they land in different 16 m cells and the
    # batcher has something to separate.
    for x in (0.0, 40.0):
        g = M.Group()
        g.add(M.box(6, 4, 5, 0.02, "plaster").translate(x, 2, 0))
        g.add(M.box(6.4, 0.3, 5.4, 0.02, "terracotta").translate(x, 4.2, 0))
        g.add(M.box(0.2, 4, 0.2, 0.01, "oak_dark").translate(x - 3, 2, 2.5))
        ctx.emit(g)

    # An interior with one doorway, which is the whole church case in miniature.
    ctx.interior("nave", aabb=((-4, 0, -20), (4, 8, -10)),
                 portals=[{"pos": (0, 1.4, -10), "size": (3.0, 4.0), "normal": (0, 1)}])
    ctx.emit(M.box(7, 7, 9, 0.02, "ashlar").translate(0, 3.5, -15), interior="nave")

    # 40 barrels in one cell (over INSTANCE_MIN) and 3 in another (under it).
    # 96 segments so the prototype clears LOD_MIN_TRIS and gets a real chain —
    # which is what makes the shared-accessor assertion below meaningful.
    proto = M.cylinder(0.28, 0.86, 96, 0.02, "oak")
    ctx.instance("barrel", proto,
                 [(2.0 + 0.3 * i, 0.0, 3.0) for i in range(40)] +
                 [(70.0, 0.0, 70.0 + i) for i in range(3)])

    # Mixed transform forms, all of which venue authors will reach for. Kept
    # inside ONE 16 m cell so the count assertion tests transform parsing and
    # not cell assignment.
    m = np.eye(4, dtype=float); m[0, 3] = -30.0; m[2, 3] = -34.0
    ctx.instance("crate", M.box(0.6, 0.5, 0.5, 0.01, "oak_weathered"),
                 [(-30.0, 0.0, -34.0, 0.7),
                  {"pos": (-31.0, 0.0, -33.0), "rot_y": 1.2, "scale": 1.3},
                  {"pos": (-32.0, 0.0, -33.0), "rot": (0, 0, 0, 1)},
                  m] * 4)

    # Clutter too small to be worth a draw call at range — the size-cull case.
    ctx.instance("pebble", M.box(0.06, 0.03, 0.06, 0.005, "cobble"),
                 [(50.0 + 0.1 * i, 0.0, 50.0) for i in range(30)])

    # An authored chain that must override the automatic decimator.
    ctx.lod("spire", [M.box(1.2, 9, 1.2, 0.02, "stone").translate(-20, 4.5, 20),
                      M.box(1.2, 9, 1.2, 0.0, "stone").translate(-20, 4.5, 20),
                      M.box(1.1, 9, 1.1, 0.0, "stone").translate(-20, 4.5, 20),
                      M.box(1.0, 9, 1.0, 0.0, "stone").translate(-20, 4.5, 20)])

    info = ctx.write()
    with open(os.path.join(tmp, "t_batch.gltf")) as f:
        return json.load(f), info


def main():
    tmp = tempfile.mkdtemp(prefix="hm_batch_")
    try:
        doc, info = build(tmp)
        nodes, hm = doc["nodes"], doc["extras"]["hm"]
        roots = doc["scenes"][0]["nodes"]
        by_name = {n["name"]: n for n in nodes}

        print("scene structure")
        alts = set()
        for n in nodes:
            alts.update(n.get("extensions", {}).get("MSFT_lod", {}).get("ids", []))
        check(alts and not (set(roots) & alts),
              f"{len(alts)} MSFT_lod alternates exist and none is a scene root")
        check(all((n.get("extras") or {}).get("hm", {}).get("lod") == 0
                  for n in (nodes[i] for i in roots)),
              "every scene root is LOD level 0")
        check("MSFT_lod" in doc["extensionsUsed"] and
              "EXT_mesh_gpu_instancing" in doc["extensionsUsed"],
              "both extensions declared in extensionsUsed")
        check("extensionsRequired" not in doc,
              "neither extension is REQUIRED — a plain consumer still opens the file")

        print("\nper-cell per-material batching")
        cells = {c["key"] for c in hm["cells"] if not c["interior"]}
        check(len(cells) >= 3, f"geometry landed in {len(cells)} separate cells")
        for c in hm["cells"]:
            if c["interior"] or c.get("meshId"):
                continue
            node = by_name.get(f"t_batch#{c['key']}")
            mats = [p["material"] for p in doc["meshes"][node["mesh"]]["primitives"]]
            check(len(mats) == len(set(mats)),
                  f"cell {c['key']}: {len(mats)} primitives, one per material")

        print("\nLOD chain")
        for c in hm["cells"]:
            if c["interior"] or c.get("meshId"):
                continue
            t = c["lodTris"]
            if len(t) < 4:
                continue
            check(t[0] > t[1] > t[2] >= t[3],
                  f"cell {c['key']}: triangles fall {t[0]}>{t[1]}>{t[2]}>={t[3]}")
            check(t[1] <= t[0] * 0.62 and t[2] <= t[0] * 0.30,
                  f"cell {c['key']}: LOD1 {t[1]/t[0]:.0%} and LOD2 {t[2]/t[0]:.0%} of LOD0")
            check(c["lodPrims"][3] <= 2,
                  f"cell {c['key']}: impostor is {c['lodPrims'][3]} draw call(s), <= 2")

        spire = [c for c in hm["cells"] if c.get("meshId") == "spire"]
        check(len(spire) == 1 and len(spire[0]["lodPrims"]) == 4,
              "ctx.lod authored chain exported as its own 4-level node")

        print("\nGPU instancing")
        inst_nodes = [n for n in nodes if "EXT_mesh_gpu_instancing" in n.get("extensions", {})]
        check(len(inst_nodes) > 0, f"{len(inst_nodes)} nodes carry EXT_mesh_gpu_instancing")
        barrel = [i for i in hm["instanced"] if i["meshId"] == "barrel"]
        check(len(barrel) == 1 and barrel[0]["count"] == 40,
              "the 40-barrel cell is instanced; the 3-barrel cell is not "
              f"(got {[(i['cell'], i['count']) for i in barrel]})")
        crate = [i for i in hm["instanced"] if i["meshId"] == "crate"]
        check(sum(i["count"] for i in crate) == 16,
              "all four transform forms (tuple, dict+rot_y, dict+quat, matrix) accepted")

        # The prototype must be stored ONCE per level, not once per cell.
        bmesh = [i for i, m in enumerate(doc["meshes"]) if m["name"] == "t_batch:barrel"]
        check(len(bmesh) == 1, "the instanced prototype mesh is written exactly once")
        # And every LOD alternate of an instanced node must share its accessors.
        n0 = by_name["t_batch#0_0@barrel"]
        acc0 = n0["extensions"]["EXT_mesh_gpu_instancing"]["attributes"]
        alt = nodes[n0["extensions"]["MSFT_lod"]["ids"][0]]
        check(alt["extensions"]["EXT_mesh_gpu_instancing"]["attributes"] == acc0,
              "LOD alternates re-use the instance accessors rather than duplicating them")
        for key in ("TRANSLATION", "ROTATION", "SCALE"):
            check(doc["accessors"][acc0[key]]["count"] == 40,
                  f"{key} accessor holds 40 instances")
            check("target" not in doc["bufferViews"][doc["accessors"][acc0[key]]["bufferView"]],
                  f"{key} bufferView carries no target (strict validators reject one)")

        print("\ninteriors and portals")
        ints = {i["id"]: i for i in hm["interiors"]}
        check("nave" in ints, "interior declared in the manifest")
        check(len(ints["nave"]["portals"]) == 1 and
              abs(np.hypot(*ints["nave"]["portals"][0]["normal"]) - 1) < 1e-6,
              "portal normal is present and unit length")
        nave = [c for c in hm["cells"] if c["interior"] == "nave"]
        check(len(nave) == 1, "interior geometry is ONE group, not split across cells")
        check(by_name.get("t_batch#int:nave") is not None,
              "interior node exported and named")

        print("\nscreen-size cull")
        culled = [c for c in hm["cells"] + hm["instanced"] if c.get("cullAt")]
        check(all(c.get("cullAt") is None for c in hm["cells"] if not c.get("meshId")),
              "no building cell is size-culled")
        check(any(i.get("cullAt") for i in hm["instanced"]),
              f"{len(culled)} small group(s) carry a build-time cull distance")

        print("\ndeterminism (ARCHITECTURE §7)")
        a = open(os.path.join(tmp, "t_batch.gltf"), "rb").read()
        abin = open(os.path.join(tmp, "t_batch.bin"), "rb").read()
        build(tmp)
        check(open(os.path.join(tmp, "t_batch.gltf"), "rb").read() == a and
              open(os.path.join(tmp, "t_batch.bin"), "rb").read() == abin,
              "a second build is byte-identical")

        print("\nfallbacks")
        inst_bytes = doc["buffers"][0]["byteLength"]
        doc2, info2 = build(tmp, instancing=False)
        check(not any("EXT_mesh_gpu_instancing" in n.get("extensions", {})
                      for n in doc2["nodes"]),
              "--no-instancing emits no instancing extension")
        # Triangles DRAWN are identical either way — that is the honest shape of
        # what instancing buys. What changes is the buffer: baking writes the
        # prototype once per copy.
        check(doc2["extras"]["hm"]["stats"]["lodTris"][0] ==
              doc["extras"]["hm"]["stats"]["lodTris"][0],
              "instancing does not change the triangles drawn")
        check(doc2["buffers"][0]["byteLength"] > inst_bytes * 1.3,
              f"--no-instancing bakes into the cell batches: buffer "
              f"{inst_bytes/1e6:.2f} MB -> {doc2['buffers'][0]['byteLength']/1e6:.2f} MB")
        doc3, _ = build(tmp, lod=False)
        check(not any("MSFT_lod" in n.get("extensions", {}) for n in doc3["nodes"]),
              "--no-lod emits no LOD chain")
        doc4, info4 = build(tmp, batching=False)
        check({c["key"] for c in doc4["extras"]["hm"]["cells"]} <= {"all", "int:nave"},
              "--no-batching merges per material across the whole venue")
        check(info4["draws"] > 0 and info4["draws"] < info["draws"],
              f"unbatched is fewer, larger primitives ({info4['draws']} vs {info['draws']}) "
              f"— the trade batching makes to become cullable")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\n{len(fails)} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
