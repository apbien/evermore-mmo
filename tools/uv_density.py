"""Texel density, measured off the shipped glTF and weighted by world AREA.

## Why this exists

`core/mesh.py:resolve_uv` closed the builder half of `ad-town-04` §2: a mesh
builder with no `uv_scale` asks `materials.LIBRARY` for the authored coverage,
and a bare float now raises. That fixed 421 call sites at a stroke.

It cannot see the other half. Four places in the build lay UVs **by hand**,
because they have no builder to ask:

    venues/streets.py   `_Paving.flat/face/tri`   the carriageway, kerbs, channels
    venues/landscape.py `_surface_patch`, `_trail` the ground outside the paving
    venues/market_square.py `_paving`             the plaza floor
    core/roof.py        `_uv_scale`               every roof slope in the town
    core/vegetation.py  hedge / ivy / weed quads

Between them those are most of the pixels in a street-level frame. A literal
`* 0.5` in one of them is invisible to the type check, invisible to
`validate.py`, and is exactly the defect the art director has now rejected on
three times running under the name "crazy paving".

So this measures what SHIPPED. For every primitive it takes the ratio of world
area to UV area and reports metres of world per tile of texture, weighted by
world area — because the number that matters is the one covering the most
pixels, not the one on the most triangles.

## The atlas exemption, stated so nobody "fixes" it again

A leaf card maps the WHOLE 4x4 atlas across one 0.49 m quad on purpose: the
card is one spray of leaves, not a tiled surface, and `LIBRARY[...].coverage`
is meaningless for it. `mesh.py`'s own header currently claims the chequerboard
leaf grid of `ad-town-04` §4 was this number — it is not, the card does not
repeat, and re-scaling it would make every tree in the town worse. Atlas keys
are listed in `ATLAS` below and are reported but never failed.

Usage:
    python tools/uv_density.py              # summary, exit 1 on a failure
    python tools/uv_density.py --all        # every venue x material row
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools", "assetgen"))

from core import materials as MAT  # noqa: E402

MESHES = os.path.join(ROOT, "assets", "meshes")

#: Keys whose UVs address a rect in a sheet rather than tile a surface. Their
#: `coverage` is not a claim about world scale and this check does not apply.
ATLAS = {
    "leaf_oak", "leaf_ash", "leaf_apple", "leaf_willow", "leaf_yew",
    "tree_far", "kit", "glass", "glass_lit", "stained", "stained_lit",
    "banner", "sign", "parchment", "wax",
}

#: Half a stop either way, matching `materials.density_audit`. A surface at
#: 1.4x its authored coverage has lost half a stop of texel density; at 2x the
#: pattern is twice life size and the art director calls it crazy paving.
TOL_WARN = 1.42
TOL_FAIL = 2.00

#: Below this, a material is trim and its scale does not decide a frame.
MIN_AREA = 6.0     # m2 of world surface, summed across the town

CT = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16,
      5125: np.uint32, 5126: np.float32}
NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def _load(path):
    g = json.load(open(path, "r", encoding="utf-8"))
    base = os.path.dirname(path)
    bufs = []
    for b in g.get("buffers", []):
        uri = b.get("uri", "")
        if uri.startswith("data:"):
            import base64
            bufs.append(base64.b64decode(uri.split(",", 1)[1]))
        else:
            bufs.append(open(os.path.join(base, uri), "rb").read())
    return g, bufs


def _acc(g, bufs, i):
    a = g["accessors"][i]
    n, nc = a["count"], NC[a["type"]]
    dt = CT[a["componentType"]]
    if "bufferView" not in a:
        return np.zeros((n, nc), np.float64)
    bv = g["bufferViews"][a["bufferView"]]
    off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    isz = np.dtype(dt).itemsize * nc
    stride = bv.get("byteStride") or isz
    raw = bufs[bv["buffer"]]
    if stride != isz:
        keep = np.frombuffer(raw, np.uint8, (n - 1) * stride + isz, off)
        keep = keep.reshape(-1)[: (n - 1) * stride + isz]
        out = np.empty((n, nc), dt)
        for k in range(n):
            out[k] = np.frombuffer(keep, dt, nc, k * stride)
    else:
        out = np.frombuffer(raw, dt, n * nc, off).reshape(n, nc)
    out = out.astype(np.float64)
    if a.get("normalized"):
        lim = {np.int8: 127.0, np.uint8: 255.0,
               np.int16: 32767.0, np.uint16: 65535.0}[dt]
        out = out / lim
        if dt in (np.int8, np.int16):
            out = np.maximum(out, -1.0)
    return out


def _uv_transform(g, mat_index):
    """The writer may push a file-wide KHR_texture_transform onto TEXCOORD_0."""
    try:
        m = g["materials"][mat_index]
        t = m["pbrMetallicRoughness"]["baseColorTexture"]
        ex = t.get("extensions", {}).get("KHR_texture_transform", {})
        s = ex.get("scale", [1.0, 1.0])
        return float(s[0]), float(s[1])
    except Exception:
        return 1.0, 1.0


def _node_scale(g):
    out = {}

    def walk(ni, acc):
        n = g["nodes"][ni]
        s = np.asarray(n.get("scale", [1.0, 1.0, 1.0]), np.float64)
        if "matrix" in n:
            M = np.asarray(n["matrix"], np.float64).reshape(4, 4).T
            s = np.linalg.norm(M[:3, :3], axis=0)
        s = acc * s
        if "mesh" in n:
            out.setdefault(n["mesh"], []).append(s)
        for c in n.get("children", []):
            walk(c, s)

    for sc in g.get("scenes", []):
        for r in sc.get("nodes", []):
            walk(r, np.ones(3))
    return out


def measure(path):
    """[(material, world_area_m2, metres_per_tile)] for one glTF."""
    g, bufs = _load(path)
    ns = _node_scale(g)
    rows = {}
    for mi, mesh in enumerate(g.get("meshes", [])):
        scales = ns.get(mi)
        sc = np.mean(scales, axis=0) if scales else np.ones(3)
        for p in mesh["primitives"]:
            at = p["attributes"]
            if "TEXCOORD_0" not in at or "indices" not in p:
                continue
            mat_i = p.get("material")
            name = (g["materials"][mat_i]["name"]
                    if mat_i is not None else "?")
            pos = _acc(g, bufs, at["POSITION"]) * sc
            uv = _acc(g, bufs, at["TEXCOORD_0"])
            ts, tt = _uv_transform(g, mat_i) if mat_i is not None else (1.0, 1.0)
            uv = uv * np.array([ts, tt])
            idx = _acc(g, bufs, p["indices"]).astype(np.int64).ravel()
            if len(idx) < 3:
                continue
            tri = idx[: (len(idx) // 3) * 3].reshape(-1, 3)
            e1 = pos[tri[:, 1]] - pos[tri[:, 0]]
            e2 = pos[tri[:, 2]] - pos[tri[:, 0]]
            wa = 0.5 * np.linalg.norm(np.cross(e1, e2), axis=1)
            f1 = uv[tri[:, 1]] - uv[tri[:, 0]]
            f2 = uv[tri[:, 2]] - uv[tri[:, 0]]
            ua = 0.5 * np.abs(f1[:, 0] * f2[:, 1] - f1[:, 1] * f2[:, 0])
            ok = (wa > 1e-9) & (ua > 1e-12)
            if not ok.any():
                continue
            # metres per tile, per triangle; area-weight into the material.
            mpt = np.sqrt(wa[ok] / ua[ok])
            a = wa[ok]
            r = rows.setdefault(name, [0.0, 0.0])
            r[0] += float(a.sum())
            # area-weighted mean of log(m/tile): the right average for a ratio
            r[1] += float((a * np.log(mpt)).sum())
    return [(k, a, float(np.exp(s / a))) for k, (a, s) in rows.items() if a > 0]


def sanctioned_overrides(src=os.path.join(ROOT, "tools", "assetgen")):
    """{material: {metres, ...}} for every literal `uv_detail()` call in the build.

    ## Why this exists

    `materials.uv_detail(key, metres, why=...)` is the pipeline's OWN sanctioned
    way to depart from a material's authored coverage, and it will not compile
    without a real sentence of justification (see `core/materials.py`). There
    are 47 such call sites. This instrument could not see any of them, so it
    failed the build on decisions the build had deliberately made and written
    down — `nogging` at 0.94 m/tile is `core/kit.py:117` asking for 0.91,
    because a herringbone panel between studs is 0.6-1.1 m wide and at the
    library's 2 m tile one panel shows a third of one repeat.

    An instrument that fails a documented decision is not measuring the town,
    it is measuring its own ignorance of the town, and it will fail forever
    however many times somebody "fixes" the asset. So the overrides are read
    from the same source the build runs.

    Statically, by AST, and deliberately not from a build-time registry: a
    registry only records the overrides that happened to execute in the last
    build, so `--venue inn` would silently un-sanction the other thirty-one
    venues. Non-literal arguments are skipped and reported by `audit()`, so
    this can never quietly widen the tolerance on something it did not read.
    """
    import ast
    import re
    NUM = re.compile(r"^[\d\.\s+\-*/()]+$")
    out = {}
    for base, _dirs, files in os.walk(src):
        if "__pycache__" in base:
            continue
        for f in sorted(files):
            if not f.endswith(".py"):
                continue
            p = os.path.join(base, f)
            text = open(p, encoding="utf-8").read()
            try:
                tree = ast.parse(text, filename=p)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                fn = node.func
                name = getattr(fn, "attr", None) or getattr(fn, "id", None)
                if name != "uv_detail" or len(node.args) < 2:
                    continue
                key, metres = node.args[0], node.args[1]
                if not (isinstance(key, ast.Constant) and isinstance(key.value, str)):
                    continue
                val = None
                if isinstance(metres, ast.Constant) and isinstance(metres.value, (int, float)):
                    val = float(metres.value)
                else:
                    seg = ast.get_source_segment(text, metres) or ""
                    if NUM.match(seg):
                        try:
                            val = float(eval(seg, {"__builtins__": {}}, {}))
                        except Exception:      # noqa: BLE001
                            val = None
                where = f"{os.path.relpath(p, ROOT)}:{node.lineno}".replace("\\", "/")
                out.setdefault(key.value, {})[val] = where
    return out


def audit(verbose=False):
    per_venue = {}
    total = {}
    for f in sorted(os.listdir(MESHES)):
        if not f.endswith(".gltf"):
            continue
        venue = f[:-5]
        for name, area, mpt in measure(os.path.join(MESHES, f)):
            per_venue.setdefault(name, []).append((venue, area, mpt))
            t = total.setdefault(name, [0.0, 0.0])
            t[0] += area
            t[1] += area * np.log(mpt)

    overrides = sanctioned_overrides()
    unread = sorted(k for k, v in overrides.items() if None in v)

    fails, warns = [], []
    print(f"{'material':17s}{'area m2':>11s}{'authored':>10s}"
          f"{'shipped':>10s}{'ratio':>8s}  worst venue")
    for name in sorted(total, key=lambda k: -total[k][0]):
        area, s = total[name]
        mpt = float(np.exp(s / area))
        ent = MAT.LIBRARY.get(name)
        if ent is None:
            continue
        # Judge against the NEAREST coverage the build is entitled to use: the
        # library's authored one, or any `uv_detail()` override written against
        # this key. See `sanctioned_overrides`.
        allowed = {ent.coverage: "core/materials.py LIBRARY"}
        for m, where in overrides.get(name, {}).items():
            if m:
                allowed.setdefault(m, f"uv_detail {where}")
        cov = min(allowed, key=lambda c: abs(np.log(mpt / c)))
        ratio = mpt / cov
        src = allowed[cov]
        tag = "atlas" if name in ATLAS else ""
        if not tag and area >= MIN_AREA:
            if ratio > TOL_FAIL or ratio < 1.0 / TOL_FAIL:
                tag, _ = "FAIL", fails.append((name, area, cov, mpt, ratio))
            elif ratio > TOL_WARN or ratio < 1.0 / TOL_WARN:
                tag, _ = "warn", warns.append((name, area, cov, mpt, ratio))
        if tag or verbose:
            worst = max(per_venue[name],
                        key=lambda t: t[1] * abs(np.log(max(t[2], 1e-6) / cov)))
            note = "" if src.startswith("core/materials") else f"  [{src}]"
            print(f"{name:17s}{area:11.0f}{cov:10.2f}{mpt:10.2f}"
                  f"{ratio:7.2f}x  {worst[0]}={worst[2]:.2f}  {tag}{note}")
    if unread:
        print(f"\n  note: uv_detail() called with a non-literal coverage on "
              f"{', '.join(unread)} — not read, so those keys are judged against "
              f"the library alone.")
    print(f"\n  {len(fails)} failure(s), {len(warns)} warning(s) over "
          f"{len(total)} materials.")
    return fails, warns


if __name__ == "__main__":
    f, _w = audit(verbose="--all" in sys.argv)
    sys.exit(1 if f else 0)
