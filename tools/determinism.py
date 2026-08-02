#!/usr/bin/env python3
"""The determinism gate. docs/ARCHITECTURE.md §7 · CLAUDE.md hard constraint 3.

    python tools/determinism.py                 # full gate: two builds, compared
    python tools/determinism.py --venue landscape
    python tools/determinism.py --check-only    # no build; lint the sources only
    python tools/determinism.py --textures      # include the texture set (slow)

## Why this exists

`docs/ARCHITECTURE.md` §7 requires the same commit to produce byte-identical
assets, and the entire art-director loop rests on it: without it a visual diff
between two review passes shows RNG drift, not an intentional change, and every
review the project has ever run is unreliable.

It was not true. `review/reports/ad-town-05.md` measured a rebuild from source
as a non-no-op — `validate.py` went 0 to 5 failures, mesh memory crossed its
budget, and a tree vanished from `t-gate-south`, one of the eight frames that
survives a blind side-by-side. Nobody could name the cause because nothing in
the project ever *checked*.

The cause was one line: `venues/landscape.py` seeded its ground-patch lattice
from `abs(hash(asset_id))`. Python salts `str` hashing per process
(`PYTHONHASHSEED`), so every ground patch in the town — and every tree, hedge
and verge scattered against one — was different on every run. `core/mathx.py`
has provided `seed_from()` (blake2b) for exactly this reason since the project
began, and `build.py` and `venues/streets.py` both carry comments warning
against `hash()`. The warning existed; the check did not.

## What the gate does

1. **Lints the sources** for `hash()` used as a seed anywhere under
   `tools/assetgen/`. Cheap, runs everywhere, and catches the whole class
   before a five-minute build does.
2. **Builds twice, under two DIFFERENT `PYTHONHASHSEED` values**, and compares
   every output byte for byte. Two builds in one process-hash regime can agree
   by luck; two under seeds 0 and 1 cannot. That turns a flaky probabilistic
   catch into a guaranteed one.
3. **Compares the rebuilt tree against what was on disk when it started**, so a
   stale committed asset — a generator edited without a rebuild — is reported
   too. That is a different failure from nondeterminism and it is named
   separately.

Exit 0 clean · 1 nondeterministic · 2 deterministic but the committed assets
are stale · 3 the build itself failed.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Everything a build writes. Textures are opt-in: they are a separate two
#: minutes and they are skipped by an incremental build anyway.
OUT_DIRS = ("assets/meshes", "content/collision", "content/entities")
TEX_DIRS = ("assets/textures",)

def lint_sources(root=os.path.join(ROOT, "tools", "assetgen")):
    """Call sites of the builtin `hash()` anywhere a generator can reach.

    Parsed, not grepped: the warnings against `hash()` are written in the
    docstrings of the very modules that do it right (`core/mathx.py`,
    `core/venue.py`, `venues/streets.py`), so a text search flags the cure as
    the disease. `ast` sees calls only, and `_cell_hash` — a numpy field
    function in `core/materials.py` — is a different name and never matches.
    """
    import ast
    hits = []
    for base, _dirs, files in os.walk(root):
        if "__pycache__" in base:
            continue
        for f in sorted(files):
            if not f.endswith(".py"):
                continue
            p = os.path.join(base, f)
            src = open(p, encoding="utf-8").read()
            lines = src.splitlines()
            try:
                tree = ast.parse(src, filename=p)
            except SyntaxError as e:
                hits.append((os.path.relpath(p, ROOT).replace("\\", "/"),
                             e.lineno or 0, f"does not parse: {e.msg}"))
                continue
            for node in ast.walk(tree):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                        and node.func.id == "hash"):
                    hits.append((os.path.relpath(p, ROOT).replace("\\", "/"),
                                 node.lineno, lines[node.lineno - 1].strip()))
    return sorted(hits)


def snapshot(dirs, venues=None):
    """sha1 of every build output, optionally restricted to some venues.

    The restriction is not cosmetic. Four agents run builds in this repository
    at once, and an unscoped `--venue landscape` run reported `terrain.bin`
    changing between its two builds — which `--venue landscape` does not write.
    Somebody else had rebuilt it in the eighty seconds between the snapshots.
    A gate that cries nondeterminism at a colleague's build is a gate people
    learn to ignore, so a scoped run compares only what it asked to build.
    """
    keep = None if not venues else {v for v in venues}
    out = {}
    for d in dirs:
        p = os.path.join(ROOT, d)
        if not os.path.isdir(p):
            continue
        for f in sorted(os.listdir(p)):
            fp = os.path.join(p, f)
            if not os.path.isfile(fp):
                continue
            if keep is not None and os.path.splitext(f)[0] not in keep:
                continue
            with open(fp, "rb") as fh:
                out[f"{d}/{f}"] = hashlib.sha1(fh.read()).hexdigest()
    return out


def compare(a, b):
    """(changed, removed, added) between two snapshots."""
    changed = sorted(k for k in a.keys() & b.keys() if a[k] != b[k])
    removed = sorted(a.keys() - b.keys())
    added = sorted(b.keys() - a.keys())
    return changed, removed, added


def build(venues, textures, hashseed):
    env = dict(os.environ, PYTHONHASHSEED=str(hashseed))
    cmd = [sys.executable, os.path.join(ROOT, "tools", "assetgen", "build.py")]
    if not textures:
        cmd.append("--skip-textures")
    for v in venues or []:
        cmd += ["--venue", v]
    t0 = time.time()
    r = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
    print(f"  build PYTHONHASHSEED={hashseed}: exit {r.returncode} in {time.time() - t0:.0f}s")
    if r.returncode != 0:
        print(r.stdout[-3000:])
        print(r.stderr[-3000:])
    return r.returncode == 0


def report(title, changed, removed, added):
    n = len(changed) + len(removed) + len(added)
    if not n:
        print(f"  {title}: identical")
        return 0
    print(f"  {title}: {n} file(s) differ")
    for k in changed[:20]:
        print(f"    CHANGED  {k}")
    for k in removed[:20]:
        print(f"    REMOVED  {k}")
    for k in added[:20]:
        print(f"    ADDED    {k}")
    if n > 20:
        print(f"    ... and {n - 20} more")
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--venue", "-v", action="append", help="scope to these venues")
    ap.add_argument("--textures", action="store_true", help="include the texture set")
    ap.add_argument("--check-only", action="store_true", help="lint the sources, do not build")
    args = ap.parse_args()

    print("determinism gate — docs/ARCHITECTURE.md §7")
    print("\nsource lint: process-salted hash() reaching a seed")
    hits = lint_sources()
    for path, line, text in hits:
        print(f"  FAIL  {path}:{line}  {text}")
    if not hits:
        print("  clean — every generator seeds through core.mathx.seed_from")
    if args.check_only:
        return 1 if hits else 0

    dirs = OUT_DIRS + (TEX_DIRS if args.textures else ())
    print(f"\nsnapshotting {', '.join(dirs)}")
    before = snapshot(dirs, args.venue)
    print(f"  {len(before)} files on disk")

    print("\nrebuilding twice under two different process hash seeds")
    if not build(args.venue, args.textures, 0):
        print("\nBUILD FAILED — determinism not established")
        return 3
    first = snapshot(dirs, args.venue)
    if not build(args.venue, args.textures, 1):
        print("\nBUILD FAILED — determinism not established")
        return 3
    second = snapshot(dirs, args.venue)

    print("\nresults")
    drift = report("build 1 vs build 2 (DETERMINISM)", *compare(first, second))
    stale = report("committed vs rebuilt (STALENESS)", *compare(before, second))

    print("")
    if hits or drift:
        print("FAILED: the build is not deterministic. Same commit, different bytes.")
        print("  A visual diff between review passes is measuring RNG drift, not a change.")
        print("  Seed every generator from core.mathx.seed_from(asset_id).")
        return 1
    if stale:
        print("FAILED: the build is deterministic but the committed assets are STALE —")
        print("  a generator was edited without regenerating. Commit the rebuild.")
        return 2
    print("PASS: byte-identical across two builds, and the committed assets match.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
