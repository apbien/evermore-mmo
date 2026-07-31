"""glTF 2.0 / GLB writer.

Written by hand rather than via a library so that output is byte-stable
forever (docs/ARCHITECTURE.md §7) — a library version bump must never silently
rewrite every asset in the repo and blow up the review diffs.

Materials use PBR metallic-roughness with **ORM channel packing**:
R=occlusion, G=roughness, B=metalness in a single texture. This is exactly
what glTF's `occlusionTexture` + `metallicRoughnessTexture` pair expects when
both point at the same image, and it is also the native packing for Unreal and
Unity — so the port costs nothing.
"""

from __future__ import annotations

import base64
import json
import os
import struct
import numpy as np


def _pad4(b, fill=b"\x00"):
    r = (4 - len(b) % 4) % 4
    return b + fill * r


class GLTFWriter:
    def __init__(self, texture_dir="../textures"):
        self.texture_dir = texture_dir
        self.buffers = bytearray()
        self.views, self.accessors = [], []
        self.meshes, self.nodes, self.materials, self.images, self.textures, self.samplers = \
            [], [], [], [], [], []
        self._mat_index = {}

    # -- buffer plumbing ----------------------------------------------------

    def _view(self, data: bytes, target=None):
        self.buffers.extend(_pad4(bytes(data)))
        off = len(self.buffers) - len(_pad4(bytes(data)))
        v = {"buffer": 0, "byteOffset": off, "byteLength": len(data)}
        if target:
            v["target"] = target
        self.views.append(v)
        return len(self.views) - 1

    def _accessor(self, arr, comp_type, type_str, target, minmax=False):
        data = arr.tobytes()
        vi = self._view(data, target)
        acc = {"bufferView": vi, "componentType": comp_type,
               "count": int(arr.shape[0]), "type": type_str}
        if minmax:
            acc["min"] = [float(x) for x in arr.min(axis=0)]
            acc["max"] = [float(x) for x in arr.max(axis=0)]
        self.accessors.append(acc)
        return len(self.accessors) - 1

    # -- materials ----------------------------------------------------------

    def material(self, name, base_color=(1, 1, 1, 1), metallic=1.0, roughness=1.0,
                 albedo_tex=None, orm_tex=None, normal_tex=None, emissive_tex=None,
                 emissive_factor=(0, 0, 0), double_sided=False, alpha_mode="OPAQUE",
                 normal_scale=1.0):
        if name in self._mat_index:
            return self._mat_index[name]

        pbr = {
            "baseColorFactor": list(base_color),
            "metallicFactor": float(metallic),
            "roughnessFactor": float(roughness),
        }
        if albedo_tex:
            pbr["baseColorTexture"] = {"index": self._texture(albedo_tex)}
        if orm_tex:
            ti = self._texture(orm_tex)
            pbr["metallicRoughnessTexture"] = {"index": ti}

        mat = {"name": name, "pbrMetallicRoughness": pbr, "doubleSided": bool(double_sided)}
        if alpha_mode != "OPAQUE":
            mat["alphaMode"] = alpha_mode
        if orm_tex:
            # Same image, R channel — this is the ORM contract.
            mat["occlusionTexture"] = {"index": self._texture(orm_tex)}
        if normal_tex:
            mat["normalTexture"] = {"index": self._texture(normal_tex), "scale": float(normal_scale)}
        if emissive_tex:
            mat["emissiveTexture"] = {"index": self._texture(emissive_tex)}
            mat["emissiveFactor"] = [1.0, 1.0, 1.0]
        elif any(emissive_factor):
            mat["emissiveFactor"] = list(emissive_factor)

        self.materials.append(mat)
        self._mat_index[name] = len(self.materials) - 1
        return self._mat_index[name]

    def _texture(self, uri):
        for i, im in enumerate(self.images):
            if im.get("uri") == uri:
                for j, t in enumerate(self.textures):
                    if t["source"] == i:
                        return j
        self.images.append({"uri": uri})
        if not self.samplers:
            # Trilinear + repeat: correct for every tiling material we author.
            self.samplers.append({"magFilter": 9729, "minFilter": 9987,
                                  "wrapS": 10497, "wrapT": 10497})
        self.textures.append({"sampler": 0, "source": len(self.images) - 1})
        return len(self.textures) - 1

    # -- meshes -------------------------------------------------------------

    def add_mesh(self, name, primitives):
        """`primitives` is a list of (Mesh, material_index)."""
        prims = []
        for m, mat_idx in primitives:
            if m.tri_count == 0:
                continue
            attrs = {
                "POSITION": self._accessor(np.ascontiguousarray(m.v, np.float32),
                                           5126, "VEC3", 34962, minmax=True),
                "NORMAL": self._accessor(np.ascontiguousarray(m.n, np.float32),
                                         5126, "VEC3", 34962),
                "TEXCOORD_0": self._accessor(np.ascontiguousarray(m.uv, np.float32),
                                             5126, "VEC2", 34962),
            }
            idx = np.ascontiguousarray(m.idx, np.uint32).reshape(-1, 1)
            p = {"attributes": attrs,
                 "indices": self._accessor(idx, 5125, "SCALAR", 34963),
                 "material": mat_idx}
            prims.append(p)
        self.meshes.append({"name": name, "primitives": prims})
        return len(self.meshes) - 1

    def add_node(self, name, mesh_index=None, translation=None, rotation=None, scale=None,
                 children=None, extras=None):
        n = {"name": name}
        if mesh_index is not None:
            n["mesh"] = mesh_index
        if translation is not None:
            n["translation"] = [float(x) for x in translation]
        if rotation is not None:
            n["rotation"] = [float(x) for x in rotation]
        if scale is not None:
            s = [float(scale)] * 3 if np.isscalar(scale) else [float(x) for x in scale]
            n["scale"] = s
        if children:
            n["children"] = list(children)
        if extras:
            n["extras"] = extras
        self.nodes.append(n)
        return len(self.nodes) - 1

    # -- output -------------------------------------------------------------

    def _doc(self, roots):
        return {
            "asset": {"version": "2.0", "generator": "unlimitless-horizons assetgen"},
            "scene": 0,
            "scenes": [{"nodes": roots}],
            "nodes": self.nodes,
            "meshes": self.meshes,
            "materials": self.materials,
            "images": self.images,
            "textures": self.textures,
            "samplers": self.samplers,
            "accessors": self.accessors,
            "bufferViews": self.views,
            "buffers": [{"byteLength": len(self.buffers)}],
        }

    def write_gltf(self, path, roots=None):
        """Write .gltf + .bin, with external texture URIs.

        Preferred over GLB here because textures stay as inspectable PNGs on
        disk, which the review loop needs — a critic must be able to open a
        roughness map and see why a surface reads wrong.
        """
        roots = roots if roots is not None else [i for i in range(len(self.nodes))
                                                 if not self._is_child(i)]
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        bin_name = os.path.basename(path).replace(".gltf", ".bin")
        doc = self._doc(roots)
        doc["buffers"][0]["uri"] = bin_name
        with open(os.path.join(os.path.dirname(path), bin_name), "wb") as f:
            f.write(bytes(self.buffers))
        with open(path, "w") as f:
            json.dump(doc, f, separators=(",", ":"), sort_keys=True)
        return path

    def write_glb(self, path, roots=None):
        roots = roots if roots is not None else [i for i in range(len(self.nodes))
                                                 if not self._is_child(i)]
        doc = self._doc(roots)
        js = _pad4(json.dumps(doc, separators=(",", ":"), sort_keys=True).encode("utf-8"), b" ")
        bin_ = _pad4(bytes(self.buffers))
        total = 12 + 8 + len(js) + 8 + len(bin_)
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "wb") as f:
            f.write(struct.pack("<III", 0x46546C67, 2, total))
            f.write(struct.pack("<II", len(js), 0x4E4F534A)); f.write(js)
            f.write(struct.pack("<II", len(bin_), 0x004E4942)); f.write(bin_)
        return path

    def _is_child(self, i):
        return any(i in n.get("children", []) for n in self.nodes)


def material_from_set(w: GLTFWriter, name, tex_prefix, has_emissive=False,
                      double_sided=False, alpha_mode="OPAQUE", normal_scale=1.0):
    """Register a material backed by a MaterialSet's written PNGs."""
    return w.material(
        name,
        albedo_tex=f"{tex_prefix}_albedo.png",
        orm_tex=f"{tex_prefix}_orm.png",
        normal_tex=f"{tex_prefix}_normal.png",
        emissive_tex=f"{tex_prefix}_emissive.png" if has_emissive else None,
        metallic=1.0, roughness=1.0,   # factors are 1.0; the ORM map carries the values
        double_sided=double_sided, alpha_mode=alpha_mode, normal_scale=normal_scale,
    )
