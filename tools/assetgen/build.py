#!/usr/bin/env python3
"""Asset build CLI.

    python3 tools/assetgen/build.py            # everything
    python3 tools/assetgen/build.py --venue inn
    python3 tools/assetgen/build.py --textures-only
    python3 tools/assetgen/build.py --list

Output is deterministic (docs/ARCHITECTURE.md §7): the same commit produces
byte-identical assets, so a visual diff between review iterations always
reflects an intentional change rather than RNG drift.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import pkgutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import atlas as ATL              # noqa: E402
from core import materials as MAT          # noqa: E402
from core.mathx import seed_from           # noqa: E402
from core.venue import VenueContext, TEX_DIR   # noqa: E402

VENUE_PKG = "venues"


def discover():
    """Find venue modules. Adding a module is all it takes to register one.

    A module that fails to import is reported LOUDLY and skipped rather than
    taking the whole build down with it. Thirty-two venues are written by
    different hands against one shared core, and one half-saved file used to
    mean nobody could rebuild anything — including venues that had nothing to do
    with it. The failure is still impossible to miss: it prints, and asking for
    that venue by name still fails with "unknown venue".
    """
    import venues
    out = {}
    for m in pkgutil.iter_modules(venues.__path__):
        if m.name.startswith("_"):
            continue
        try:
            mod = importlib.import_module(f"{VENUE_PKG}.{m.name}")
        except Exception as e:                       # noqa: BLE001
            print(f"  !! venue '{m.name}' FAILED TO IMPORT and is skipped: "
                  f"{type(e).__name__}: {e}")
            continue
        if hasattr(mod, "build"):
            out[getattr(mod, "NAME", m.name)] = mod
    return out


def build_textures(size=None, only=None, force=False):
    """Generate PBR sets. Incremental by default.

    A full set takes ~2 minutes, which is long enough to stall an iteration
    loop, so existing textures are skipped unless --force. Change a material
    builder and you must pass --force (or delete its PNGs) to see the change.

    Resolution comes from the material's own registry entry (class density x
    world coverage, Art Bible §5) rather than from one number applied to
    everything. `--size` overrides it, which is for spot-checking a change
    quickly, not for shipping.
    """
    os.makedirs(TEX_DIR, exist_ok=True)
    made, skipped, px = [], [], 0
    for key, mat in MAT.LIBRARY.items():
        if only and key not in only:
            continue
        if not force and os.path.exists(os.path.join(TEX_DIR, f"{key}_albedo.png")):
            skipped.append(key)
            continue
        t0 = time.time()
        # `seed_from`, not `hash()`: Python salts str hashing per process, so
        # the old seed produced different textures on every run and quietly
        # voided the determinism guarantee docs/ARCHITECTURE.md §7 rests on.
        kw = {"name": key, "seed": seed_from("material", key) % 9973}
        if size:
            kw["size"] = size
        m = mat(**kw)
        m.write(TEX_DIR)
        px += m.size * m.size
        made.append(key)
        print(f"  texture {key:16s} {m.size:5d}px  {m.coverage:4.1f} m/tile  "
              f"{m.texel_density:6.0f} px/m  {m.klass:8s} {time.time()-t0:5.2f}s")
    if skipped:
        print(f"  skipped {len(skipped)} existing ({', '.join(skipped)}) — --force to rebuild")
    if made:
        print(f"  {len(made)} sets, {px * 4 * 3 * 1.334 / 1e6:.0f} MB resident "
              f"(RGBA8 + mips, 3 maps each)")
    write_manifest()
    return made


def write_manifest():
    """assets/textures/manifest.json — the registry, readable from JS.

    The renderers need to know a material's world coverage to show it at the
    right scale, its flags to build the right shader, and its class to report
    density. That information lives in the Python registry, and the alternative
    to publishing it is every JS tool guessing — which is how `tools/render`
    ended up with its own copy of the lighting rig once already (D-009).
    """
    doc = {"materials": {}, "atlases": {}}
    for key, m in sorted(MAT.LIBRARY.items()):
        doc["materials"][key] = {
            "size": m.size, "coverage": m.coverage, "class": m.klass,
            "density": round(m.density, 1), "flags": sorted(m.flags),
            "emissive": "emissive" in m.flags,
        }
    for name, keys in ATL.ATLASES.items():
        a = ATL.get(name)
        doc["atlases"][name] = {
            "page": a.size, "cell": a.cell, "gutter": ATL.GUTTER,
            "rects": {k: [round(v, 6) for v in a.rect(k)] for k in a.keys},
        }
    path = os.path.join(TEX_DIR, "manifest.json")
    with open(path, "w") as f:
        json.dump(doc, f, indent=1, sort_keys=True)
    return path


def audit_textures():
    """Art Bible §5 texel density is a done-criterion, so print it.

    A criterion nobody can measure from the build output is a criterion that
    gets asserted rather than checked, and §8's box was being ticked by
    inspection.
    """
    rows = MAT.density_audit()
    bad = [r for r in rows if r[6] != "ok"]
    print(f"texel density ({len(rows)} sets, Art Bible §5):")
    by_class = {}
    for key, sz, cov, got, kls, want, verdict in rows:
        by_class.setdefault(kls, []).append(key)
    for kls in ("hero", "standard", "large"):
        n = len(by_class.get(kls, []))
        print(f"  {kls:9s} {MAT.DENSITY[kls]:4.0f} px/m target  {n:3d} sets")
    for key, sz, cov, got, kls, want, verdict in bad:
        print(f"  !! {key:16s} {sz}px / {cov:g} m = {got:.0f} px/m, "
              f"{kls} wants {want:.0f}  [{verdict}]")
    if not bad:
        print(f"  all {len(rows)} within half a stop of class")
    return bad


def atlas_report():
    """What the atlas pages actually took, per material. Directive §7.

    The take rate is the whole trade: a member squeezed into a rect costs texel
    density, and a member refused costs a draw call in every cell it appears in.
    Neither number was printed anywhere, so four waves of work on `core/atlas.py`
    were steered by nothing. `need` is the squeeze a refused member would have
    required — a column of 3.0s means the page's rects are one tile and the
    members are three metres long, which is a rect-size problem, not a
    geometry problem.
    """
    rows = sorted(ATL.STATS.items(), key=lambda kv: -kv[1]["left"])
    if not rows:
        return
    print("\natlas take rate (Directive §7 — tris folded onto a page vs left loose):")
    print(f"  {'page/material':28s} {'took':>10s} {'loose':>10s} {'take%':>6s} "
          f"{'refused':>8s}  need p50/p90/max")
    tt = tl = 0
    for (page, key), s in rows:
        tt += s["took"]; tl += s["left"]
        tot = s["took"] + s["left"]
        need = sorted(s["need"])
        q = (f"{need[len(need)//2]:.1f}/{need[int(len(need)*0.9)]:.1f}/{need[-1]:.1f}"
             if need else "-")
        print(f"  {page + '/' + key:28s} {s['took']:10,d} {s['left']:10,d} "
              f"{100.0 * s['took'] / max(1, tot):5.0f}% {s['refused']:8,d}  {q}")
    print(f"  {'TOTAL':28s} {tt:10,d} {tl:10,d} {100.0 * tt / max(1, tt + tl):5.0f}%")
    for name in sorted(ATL.ATLASES):
        a = ATL.get(name)
        r = a.report()
        print(f"  page '{name}': {r['page']}px, {r['materials']} materials, "
              f"{r['atlas_mb']:.0f} MB resident against {r['loose_mb']:.0f} MB loose")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--venue", "-v", action="append", help="build only these venues")
    ap.add_argument("--textures-only", action="store_true")
    ap.add_argument("--skip-textures", action="store_true")
    ap.add_argument("--size", type=int, default=None,
                    help="override every texture's registry resolution (debug)")
    ap.add_argument("--audit", action="store_true",
                    help="print the Art Bible §5 texel-density table and stop")
    ap.add_argument("--force-textures", action="store_true",
                    help="regenerate textures even if PNGs exist")
    ap.add_argument("--only", action="append", help="limit texture keys")
    ap.add_argument("--list", action="store_true")
    # The three Directive §7 build-time techniques, each switchable OFF so the
    # win is measurable rather than asserted. Leave them on.
    ap.add_argument("--no-batching", action="store_true",
                    help="skip per-cell per-material static batching")
    ap.add_argument("--no-lod", action="store_true", help="skip the LOD chain")
    ap.add_argument("--no-atlas", action="store_true",
                    help="do not fold kit materials onto their atlas page — "
                         "the control experiment for the §7 draw-call budget")
    ap.add_argument("--no-instancing", action="store_true",
                    help="bake instanced props into the cell batches instead")
    args = ap.parse_args()

    if args.audit:
        return 1 if audit_textures() else 0

    venues = discover()
    if args.list:
        for n, m in sorted(venues.items()):
            print(f"{n:16s} cells={getattr(m, 'CELLS', [])}")
        return

    if not args.skip_textures:
        print("textures:")
        build_textures(args.size, only=set(args.only) if args.only else None,
                       force=args.force_textures)
    if args.textures_only:
        return

    targets = args.venue or sorted(venues)
    print("\nvenues:")
    print(f"  {'venue':16s} {'tris':>9s} {'cells':>6s} {'draws':>6s}  "
          f"{'lod0/1/2/3 draws':>22s} {'inst':>5s}  ent vols   time")
    total = 0
    tot_lod = [0] * 4
    for name in targets:
        if name not in venues:
            print(f"  !! unknown venue '{name}' (have: {', '.join(sorted(venues))})")
            continue
        mod = venues[name]
        t0 = time.time()
        ctx = VenueContext(
            name, getattr(mod, "CELLS", []),
            cell_size=getattr(mod, "CELL_SIZE", None),
            batching=getattr(mod, "BATCH", True) and not args.no_batching,
            lod=getattr(mod, "LOD", True) and not args.no_lod,
            instancing=not args.no_instancing,
            atlasing=getattr(mod, "ATLAS", True) and not args.no_atlas,
        )
        mod.build(ctx)
        info = ctx.write()
        total += info["tris"]
        for i, p in enumerate(info["lodPrims"]):
            tot_lod[i] += p
        lods = "/".join(f"{p}" for p in info["lodPrims"])
        print(f"  {name:16s} {info['tris']:9,d} {info['cells']:6d} {info['draws']:6d}  "
              f"{lods:>22s} {info['instances']:5d}  "
              f"{info['entities']:3d} {info['colliders']:4d} {time.time()-t0:6.2f}s")
        if not info["colliders"]:
            print(f"      NO COLLISION declared — see docs/BUILD_DIRECTIVE.md §6.4")
        for h in info.get("occlusion", []):
            print(f"      OCCLUDED: {h}")
    atlas_report()
    print(f"\ntotal {total:,} tris   draws by LOD level: "
          + " / ".join(f"L{i} {n:,}" for i, n in enumerate(tot_lod)))
    print("  (draws are PER SOURCE MESH and uncalled — the number that ships is "
          "what tools/render/town.mjs measures with culling on.)")


if __name__ == "__main__":
    main()
