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
import os
import pkgutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import materials as MAT          # noqa: E402
from core.venue import VenueContext, TEX_DIR   # noqa: E402

VENUE_PKG = "venues"


def discover():
    """Find venue modules. Adding a module is all it takes to register one."""
    import venues
    out = {}
    for m in pkgutil.iter_modules(venues.__path__):
        if m.name.startswith("_"):
            continue
        mod = importlib.import_module(f"{VENUE_PKG}.{m.name}")
        if hasattr(mod, "build"):
            out[getattr(mod, "NAME", m.name)] = mod
    return out


def build_textures(size=1024, only=None, force=False):
    """Generate PBR sets. Incremental by default.

    A full set takes ~2 minutes, which is long enough to stall an iteration
    loop, so existing textures are skipped unless --force. Change a material
    builder and you must pass --force (or delete its PNGs) to see the change.
    """
    os.makedirs(TEX_DIR, exist_ok=True)
    made, skipped = [], []
    for key, fn in MAT.LIBRARY.items():
        if only and key not in only:
            continue
        if not force and os.path.exists(os.path.join(TEX_DIR, f"{key}_albedo.png")):
            skipped.append(key)
            continue
        t0 = time.time()
        fn(name=key, size=size, seed=abs(hash(key)) % 9973).write(TEX_DIR)
        made.append(key)
        print(f"  texture {key:16s} {time.time()-t0:5.2f}s")
    if skipped:
        print(f"  skipped {len(skipped)} existing ({', '.join(skipped)}) — --force to rebuild")
    return made


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--venue", "-v", action="append", help="build only these venues")
    ap.add_argument("--textures-only", action="store_true")
    ap.add_argument("--skip-textures", action="store_true")
    ap.add_argument("--size", type=int, default=1024, help="texture resolution")
    ap.add_argument("--force-textures", action="store_true",
                    help="regenerate textures even if PNGs exist")
    ap.add_argument("--only", action="append", help="limit texture keys")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

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
    total = 0
    for name in targets:
        if name not in venues:
            print(f"  !! unknown venue '{name}' (have: {', '.join(sorted(venues))})")
            continue
        mod = venues[name]
        t0 = time.time()
        ctx = VenueContext(name, getattr(mod, "CELLS", []))
        mod.build(ctx)
        info = ctx.write()
        total += info["tris"]
        print(f"  {name:16s} {info['tris']:7,d} tris  "
              f"{info['entities']:3d} entities  {time.time()-t0:5.2f}s  "
              f"[{', '.join(info['materials'])}]")
        for h in info.get("occlusion", []):
            print(f"      OCCLUDED: {h}")
    print(f"\ntotal {total:,} tris")


if __name__ == "__main__":
    main()
