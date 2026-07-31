#!/usr/bin/env python3
"""Automated conformance checks.

These catch the mechanical defects — scale errors, palette drift, malformed
entity IDs, missing textures. They do NOT and cannot replace the art-director
review in docs/REVIEW_PROTOCOL.md: a mesh can pass every check here and still
look like a prototype, because "lifeless" is not a property a checker can see.

    python3 tools/validate.py
    python3 tools/validate.py --venue inn
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import struct
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MESH_DIR = os.path.join(REPO, "assets/meshes")
TEX_DIR = os.path.join(REPO, "assets/textures")
ENT_DIR = os.path.join(REPO, "content/entities")

ID_RE = re.compile(r"^hm\.[a-z_]+(\.[a-z_0-9]+)*$")

# Art Bible §3. Checked against the whole-venue bounding box, so these are
# sanity bounds rather than exact dimensions.
MAX_VENUE_SPAN = 60.0     # m; a single venue larger than this is a layout bug
MAX_VENUE_HEIGHT = 22.0   # m; the guild tower is the tallest thing in town
MIN_VENUE_HEIGHT = 0.25

problems, warnings = [], []


def err(msg):
    problems.append(msg)


def warn(msg):
    warnings.append(msg)


def check_gltf(path):
    name = os.path.basename(path)
    with open(path) as f:
        doc = json.load(f)

    if doc.get("asset", {}).get("version") != "2.0":
        err(f"{name}: not glTF 2.0")

    # Bounds from POSITION accessor min/max.
    lo = [1e9] * 3
    hi = [-1e9] * 3
    for acc in doc.get("accessors", []):
        if acc.get("type") == "VEC3" and "min" in acc and "max" in acc:
            for i in range(3):
                lo[i] = min(lo[i], acc["min"][i])
                hi[i] = max(hi[i], acc["max"][i])
    if lo[0] > 1e8:
        err(f"{name}: no positional data")
        return

    span_x, span_y, span_z = (hi[i] - lo[i] for i in range(3))
    if max(span_x, span_z) > MAX_VENUE_SPAN:
        warn(f"{name}: footprint {span_x:.1f}x{span_z:.1f}m exceeds {MAX_VENUE_SPAN}m")
    if span_y > MAX_VENUE_HEIGHT:
        err(f"{name}: height {span_y:.1f}m exceeds {MAX_VENUE_HEIGHT}m — scale error?")
    if span_y < MIN_VENUE_HEIGHT:
        err(f"{name}: height {span_y:.2f}m — geometry probably failed to build")

    # Ground contact: a venue floating above or sunk below y=0 is a placement bug.
    if lo[1] > 0.35:
        warn(f"{name}: lowest geometry at y={lo[1]:.2f} — floating?")
    if lo[1] < -1.2:
        warn(f"{name}: geometry down to y={lo[1]:.2f} — sunk through the ground?")

    # Every material must carry a full PBR set (Art Bible §5).
    images = {im.get("uri", "") for im in doc.get("images", [])}
    for mat in doc.get("materials", []):
        mn = mat.get("name", "?")
        pbr = mat.get("pbrMetallicRoughness", {})
        if "baseColorTexture" not in pbr:
            err(f"{name}: material '{mn}' has no albedo texture (flat colour is rejected)")
        if "metallicRoughnessTexture" not in pbr:
            err(f"{name}: material '{mn}' has no ORM texture")
        if "normalTexture" not in mat:
            warn(f"{name}: material '{mn}' has no normal map")

    for uri in images:
        p = os.path.normpath(os.path.join(MESH_DIR, uri))
        if not os.path.exists(p):
            err(f"{name}: missing texture {uri}")

    tris = sum(
        doc["accessors"][p["indices"]]["count"] // 3
        for m in doc.get("meshes", []) for p in m.get("primitives", [])
        if "indices" in p
    )
    return {"name": name, "tris": tris, "span": (span_x, span_y, span_z),
            "materials": len(doc.get("materials", []))}


def check_entities(path):
    name = os.path.basename(path)
    doc = json.load(open(path))
    seen = set()
    for e in doc.get("entities", []):
        eid = e.get("id", "")
        if not ID_RE.match(eid):
            err(f"{name}: malformed entity id '{eid}' "
                f"(expected hm.<venue>.<kind>.<nn>)")
        if eid in seen:
            err(f"{name}: duplicate entity id '{eid}' — IDs are never reused")
        seen.add(eid)
        if "archetype" not in e:
            err(f"{name}: entity '{eid}' has no archetype")
        t = e.get("transform", {})
        if len(t.get("pos", [])) != 3:
            err(f"{name}: entity '{eid}' has no valid position")
        v = e.get("components", {}).get("vendor")
        if v:
            for line in v.get("stock", []):
                if line.get("price", -1) < 0:
                    err(f"{name}: entity '{eid}' has negative price for {line.get('item')}")
    return len(doc.get("entities", []))


def check_textures():
    albedos = glob.glob(os.path.join(TEX_DIR, "*_albedo.png"))
    if not albedos:
        err("no textures generated — run: python3 tools/assetgen/build.py --textures-only")
    for a in albedos:
        key = os.path.basename(a)[: -len("_albedo.png")]
        for ch in ("orm", "normal"):
            p = os.path.join(TEX_DIR, f"{key}_{ch}.png")
            if not os.path.exists(p):
                err(f"texture set '{key}' missing {ch} channel")
    return len(albedos)


def check_town():
    p = os.path.join(REPO, "content/town/hearthmere.json")
    if not os.path.exists(p):
        err("content/town/hearthmere.json missing")
        return
    town = json.load(open(p))
    for v in town.get("venues", []):
        mesh = os.path.join(MESH_DIR, f"{v['id']}.gltf")
        if not os.path.exists(mesh):
            warn(f"town references venue '{v['id']}' with no built mesh yet")
    # Venue overlap. Some venues legitimately occupy the same footprint —
    # the market stalls stand inside the market square — so only flag pairs
    # that are not a known nesting.
    NESTED = {("market_square", "stalls")}
    seen = {}
    for v in town.get("venues", []):
        key = tuple(round(c, 1) for c in v["origin"])
        other = seen.get(key)
        if other and other != v["id"]:
            pair = tuple(sorted((other, v["id"])))
            if pair not in {tuple(sorted(p)) for p in NESTED}:
                warn(f"venues '{other}' and '{v['id']}' share origin {key}")
        seen[key] = v["id"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--venue", "-v", action="append")
    args = ap.parse_args()

    print("textures:")
    n = check_textures()
    print(f"  {n} PBR sets")

    print("\nmeshes:")
    paths = sorted(glob.glob(os.path.join(MESH_DIR, "*.gltf")))
    if args.venue:
        paths = [p for p in paths if os.path.basename(p)[:-5] in args.venue]
    total = 0
    for p in paths:
        info = check_gltf(p)
        if info:
            total += info["tris"]
            sx, sy, sz = info["span"]
            print(f"  {info['name']:24s} {info['tris']:7,d} tris  "
                  f"{sx:5.1f} x {sy:5.1f} x {sz:5.1f} m  {info['materials']} mats")
    print(f"  total {total:,} tris")

    print("\nentities:")
    ent = 0
    for p in sorted(glob.glob(os.path.join(ENT_DIR, "*.json"))):
        c = check_entities(p)
        ent += c
        print(f"  {os.path.basename(p):24s} {c:3d}")
    print(f"  total {ent}")

    print("\ntown:")
    check_town()

    print()
    for w in warnings:
        print(f"  WARN  {w}")
    for e in problems:
        print(f"  FAIL  {e}")
    print(f"\n{len(problems)} failures, {len(warnings)} warnings")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
