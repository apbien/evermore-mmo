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


# Extensions a consumer cannot ignore and still read the file correctly, so
# these and only these go in `extensionsRequired`.
#
# `KHR_texture_transform` joins the list with D-052's TEXCOORD_0 quantization.
# It carries the dequantizing UV scale, so a consumer that skips it samples
# every texture at 1/S of its authored tiling and the town renders as smeared
# colour. It is the same pairing gltfpack emits for quantized UVs, and it is
# supported by three.js, Babylon, Cesium, the Blender importer, gltf-validator
# and Unreal 5's Interchange glTF pipeline.
REQUIRED_EXTENSIONS = {"KHR_mesh_quantization", "KHR_texture_transform"}

NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def _pad4(b, fill=b"\x00"):
    r = (4 - len(b) % 4) % 4
    return b + fill * r


class GLTFWriter:
    def __init__(self, texture_dir="../textures", quantize=True):
        self.texture_dir = texture_dir
        self.buffers = bytearray()
        self.views, self.accessors = [], []
        self.meshes, self.nodes, self.materials, self.images, self.textures, self.samplers = \
            [], [], [], [], [], []
        self._mat_index = {}
        # Both extensions used here are fallback-safe, so neither is ever listed
        # in extensionsRequired: a consumer that ignores EXT_mesh_gpu_instancing
        # draws one copy at the node transform, and one that ignores MSFT_lod
        # draws the finest level. A broken-looking town beats a town that will
        # not open.
        self.extensions_used = set()
        self.extras = {}
        # KHR_mesh_quantization is NOT fallback-safe — it changes accessor
        # component types, so a consumer that ignores it reads garbage. It is
        # therefore the one extension here that goes in extensionsRequired, and
        # a file using it will refuse to open in a loader that lacks it rather
        # than opening wrong. Supported by three.js (>= r117), Babylon, Cesium,
        # the Blender importer, gltf-validator and Unreal 5's Interchange glTF
        # pipeline.
        self.quantize = bool(quantize)
        self._dequant = {}
        # TEXCOORD_0 accessors are written LAST, not as each mesh is added.
        # See `_finalize_uvs`: the dequantizing scale has to be one number for
        # the whole file or materials stop being shareable, and it is not
        # knowable until every mesh is in.
        self._uv_pending = []
        self._uv_scale = None
        self._finalized = False

    # -- buffer plumbing ----------------------------------------------------

    def _view(self, data: bytes, target=None, stride=None):
        self.buffers.extend(_pad4(bytes(data)))
        off = len(self.buffers) - len(_pad4(bytes(data)))
        v = {"buffer": 0, "byteOffset": off, "byteLength": len(data)}
        if target:
            v["target"] = target
        if stride:
            v["byteStride"] = int(stride)
        self.views.append(v)
        return len(self.views) - 1

    def _accessor(self, arr, comp_type, type_str, target, minmax=False,
                  normalized=False, stride=None):
        data = arr.tobytes()
        vi = self._view(data, target, stride)
        acc = {"bufferView": vi, "componentType": comp_type,
               "count": int(arr.shape[0]), "type": type_str}
        if normalized:
            acc["normalized"] = True
        if minmax:
            # In the accessor's OWN component units, which for a normalized
            # integer accessor means the raw stored integers — that is what the
            # spec asks for and what three.js's `computeBounds` rescales by the
            # component range. Writing dequantized floats here gives a bounding
            # box 32767x too large and every frustum test in the client passes.
            n = NC[type_str]
            acc["min"] = [float(x) for x in arr[:, :n].min(axis=0)]
            acc["max"] = [float(x) for x in arr[:, :n].max(axis=0)]
        self.accessors.append(acc)
        return len(self.accessors) - 1

    # -- KHR_mesh_quantization ----------------------------------------------

    # Position quantization is inline in `add_mesh` because the frame must be
    # the union over the mesh's primitives — see the comment there.
    #
    #   SHORT + normalized, so the stored value is v/32767 in [-1, 1] and the
    #   node's TRS carries the half-extent and the centre. 16 bits over a
    #   venue's own bounding box is 1/32767 of its longest axis: 9 mm on the
    #   576 m landscape plate, 0.3 mm on a cottage. Art Bible §6's smallest
    #   feature is a 3 mm chamfer on handheld metal, and handheld metal lives
    #   in venues a few metres across — so the error is always at least an
    #   order below the detail it carries.
    #
    #   Padded to 4 components. A VEC3 of SHORT is 6 bytes, and glTF requires
    #   vertex attribute elements to sit on 4-byte boundaries; a byteStride of
    #   8 with the fourth component ignored is how every quantizing exporter
    #   answers that, and it is universally handled because it is the same code
    #   path as an interleaved buffer.

    @staticmethod
    def _quant_normal(n):
        """int8 normalized VEC3, padded to 4 bytes.

        8 bits per axis is ~0.9 degrees of angular error at worst, which is
        below the shading difference a chamfer facet is there to produce and
        two orders below the 15 mm chamfer's own effect. Normals are 31% of
        every .bin in the repository and this is 4 bytes instead of 12.
        """
        q = np.rint(np.clip(n, -1.0, 1.0) * 127.0)
        q = np.clip(q, -127, 127).astype(np.int8)
        pad = np.zeros((len(q), 4), np.int8)
        pad[:, :3] = q
        return pad

    # -- materials ----------------------------------------------------------

    def material(self, name, base_color=(1, 1, 1, 1), metallic=1.0, roughness=1.0,
                 albedo_tex=None, orm_tex=None, normal_tex=None, emissive_tex=None,
                 emissive_factor=(0, 0, 0), double_sided=False, alpha_mode="OPAQUE",
                 normal_scale=1.0, alpha_cutoff=None):
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
        # Only meaningful under MASK, and glTF's default is 0.5 — but writing it
        # explicitly matters for the leaf atlases, where the cutoff decides how
        # much of every leaf's soft margin survives. Left implicit, a consumer
        # that defaults differently reshapes the foliage.
        if alpha_mode == "MASK" and alpha_cutoff is not None:
            mat["alphaCutoff"] = float(alpha_cutoff)
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

    def add_mesh(self, name, primitives, instanced=False):
        """`primitives` is a list of (Mesh, material_index).

        Vertex attributes are QUANTIZED (KHR_mesh_quantization) unless the
        writer was constructed with `quantize=False`. Measured on the shipped
        town: 318.5 MB of accessor data, of which POSITION and NORMAL are 63%
        at float32. Quantizing takes the whole set to 191 MB with no visible
        change at any camera in the review set. There is no LOD, culling or
        streaming scheme that makes a 318 MB mesh set loadable over the web;
        this is the only lever that acts on the bytes themselves.

        `instanced=True` keeps POSITION at float32 for this mesh. Position
        quantization needs a dequantizing scale and translation on the node,
        and EXT_mesh_gpu_instancing composes as
        `nodeWorld * instanceLocal * vertex` — so a node scale of 1/32767 would
        divide every instance TRANSLATION by 32767 as well and collapse the
        whole batch onto the venue origin. Instanced meshes are unit-size
        prototypes written once each, so the cost of exempting them is a few
        hundred kilobytes across the town.
        """
        live = [(m, mi) for m, mi in primitives if m.tri_count]
        # One node carries one dequantizing transform, so the frame has to be
        # the union of EVERY primitive in the mesh, computed before any of them
        # is written. Taking it from the first primitive and clamping the rest
        # into it is not a graceful degradation: it silently collapses every
        # other primitive onto the first one's bounding box. The terrain venue
        # is `riverbed` (a 30 m patch) followed by `grass` (the 576 m plate),
        # and that is exactly what happened — the whole landscape outside the
        # town wall folded into the river margin.
        node_scale = node_translation = None
        if self.quantize and not instanced and live:
            allv = np.vstack([np.asarray(m.v, np.float32) for m, _ in live])
            lo, hi = allv.min(axis=0), allv.max(axis=0)
            node_translation = ((lo + hi) * 0.5).astype(np.float64)
            node_scale = np.maximum((hi - lo) * 0.5, 1e-4).astype(np.float64)

        prims = []
        for m, mat_idx in live:
            v = np.ascontiguousarray(m.v, np.float32)
            if node_scale is not None:
                q = np.zeros((len(v), 4), np.int16)
                q[:, :3] = np.rint(np.clip(
                    (v - node_translation) / node_scale, -1.0, 1.0) * 32767.0
                ).astype(np.int16)
                pos = self._accessor(q, 5122, "VEC3", 34962, minmax=True,
                                     normalized=True, stride=8)
            else:
                pos = self._accessor(v, 5126, "VEC3", 34962, minmax=True)

            if self.quantize:
                nrm = self._accessor(self._quant_normal(np.asarray(m.n, np.float32)),
                                     5120, "VEC3", 34962, normalized=True, stride=4)
            else:
                nrm = self._accessor(np.ascontiguousarray(m.n, np.float32),
                                     5126, "VEC3", 34962)
            attrs = {"POSITION": pos, "NORMAL": nrm}
            uv = np.ascontiguousarray(m.uv, np.float32)
            if self.quantize:
                # TEXCOORD_0 is deferred, not written here. D-052.
                #
                # This used to stay float32, and the reasoning recorded against
                # it was that quantizing needs a KHR_texture_transform PER
                # MATERIAL to undo the scale, which would stop materials being
                # shared between primitives with different UV extents. The
                # premise was right and the conclusion was wrong: the scale
                # only has to be per-material if it is DERIVED per primitive.
                # Take ONE scale for the whole file — the largest |uv| any mesh
                # in it reaches — and every material in the file carries the
                # same transform, so sharing is untouched. `_finalize_uvs`
                # does that, once, when the file is written.
                #
                # Measured across the 35 shipped meshes: TEXCOORD_0 is 95.1 MB
                # of a 276.3 MB accessor set, 34.4% and the single largest
                # attribute after POSITION. Halving it is 47.6 MB, which is the
                # whole of the 35.7 MB the town is over its 240 MB budget.
                self._uv_pending.append((attrs, uv))
            else:
                attrs["TEXCOORD_0"] = self._accessor(uv, 5126, "VEC2", 34962)
            if m.col is not None and len(m.col) == len(m.v):
                # Normalized ubyte. The earlier float32 was justified by the
                # terrain's splat blend needing headroom at a boundary — but
                # COLOR_0 here is a TINT multiplied into an albedo, not a blend
                # weight, and 8 bits of a tint is one 255th of a value the eye
                # reads through a tone map. Measured across the terrain's
                # 182k vertices the largest per-channel error is 0.0020.
                c = np.clip(np.asarray(m.col, np.float32), 0.0, 1.0)
                if self.quantize:
                    attrs["COLOR_0"] = self._accessor(
                        np.rint(c * 255.0).astype(np.uint8), 5121, "VEC4", 34962,
                        normalized=True, stride=4)
                else:
                    attrs["COLOR_0"] = self._accessor(
                        np.ascontiguousarray(c, np.float32), 5126, "VEC4", 34962)

            idx = np.ascontiguousarray(m.idx, np.uint32).reshape(-1, 1)
            if self.quantize and len(v) <= 65536:
                ia = self._accessor(idx.astype(np.uint16), 5123, "SCALAR", 34963)
            else:
                ia = self._accessor(idx, 5125, "SCALAR", 34963)
            prims.append({"attributes": attrs, "indices": ia, "material": mat_idx})
        if self.quantize:
            self.extensions_used.add("KHR_mesh_quantization")
        self.meshes.append({"name": name, "primitives": prims})
        if node_scale is not None:
            self._dequant[len(self.meshes) - 1] = (node_scale, node_translation)
        return len(self.meshes) - 1

    def add_node(self, name, mesh_index=None, translation=None, rotation=None, scale=None,
                 children=None, extras=None):
        n = {"name": name}
        if mesh_index is not None:
            n["mesh"] = mesh_index
            # Dequantization for KHR_mesh_quantization rides on the node, which
            # is where the extension puts it. Composed with any caller-supplied
            # transform rather than overwriting it: `world = T + S * q` and the
            # caller's own translation is in the same frame as the centre.
            dq = self._dequant.get(mesh_index)
            if dq is not None:
                half, centre = dq
                if scale is not None:
                    sc = np.full(3, float(scale)) if np.isscalar(scale) else np.asarray(scale, float)
                    half = half * sc
                    centre = centre * sc
                scale = half
                translation = centre if translation is None else                     (np.asarray(translation, float) + centre)
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

    # -- EXT_mesh_gpu_instancing --------------------------------------------

    def add_instancing(self, node_index, translations=None, rotations=None, scales=None,
                       attributes=None):
        """Attach per-instance transforms to a node.

        `translations` is (N,3), `rotations` (N,4) xyzw quaternions, `scales`
        (N,3). This is the export form of an Unreal
        `InstancedStaticMeshComponent` / Unity `Graphics.DrawMeshInstanced`
        batch: one mesh, N transforms, one draw.

        `attributes` re-uses an accessor set returned by an earlier call. The
        LOD alternates of an instanced node need byte-identical transforms, and
        writing them four times would triple the instance buffer for no reason.

        The attribute bufferViews deliberately carry no `target`. glTF's
        ELEMENT_ARRAY/ARRAY targets describe index and vertex buffers; instance
        attributes are neither, and setting one makes strict validators reject
        the file.
        """
        if attributes is None:
            t = np.ascontiguousarray(np.asarray(translations, np.float32).reshape(-1, 3))
            attributes = {"TRANSLATION": self._accessor(t, 5126, "VEC3", None, minmax=True)}
            if rotations is not None:
                r = np.ascontiguousarray(np.asarray(rotations, np.float32).reshape(-1, 4))
                attributes["ROTATION"] = self._accessor(r, 5126, "VEC4", None)
            if scales is not None:
                s = np.ascontiguousarray(np.asarray(scales, np.float32).reshape(-1, 3))
                attributes["SCALE"] = self._accessor(s, 5126, "VEC3", None)
        node = self.nodes[node_index]
        node.setdefault("extensions", {})["EXT_mesh_gpu_instancing"] = {"attributes": attributes}
        self.extensions_used.add("EXT_mesh_gpu_instancing")
        return attributes

    # -- MSFT_lod ------------------------------------------------------------

    def add_lod(self, node_index, alternates, screen_coverage=None):
        """Declare `alternates` as coarser levels of `node_index`.

        MSFT_lod's contract, and the reason it is the right choice here: the
        alternate nodes are referenced ONLY from this extension, never from a
        scene or a children list. A consumer that has never heard of the
        extension therefore walks the scene, finds level 0, and renders a
        correct — merely expensive — town. There is no version of this that
        renders four levels on top of each other, which is exactly the failure
        mode of encoding LODs as sibling nodes and hoping.
        """
        if not alternates:
            return
        node = self.nodes[node_index]
        node.setdefault("extensions", {})["MSFT_lod"] = {"ids": [int(i) for i in alternates]}
        if screen_coverage:
            node.setdefault("extras", {})["MSFT_screencoverage"] = list(screen_coverage)
        self.extensions_used.add("MSFT_lod")

    # -- output -------------------------------------------------------------

    # -- deferred TEXCOORD_0 quantization (D-052) ----------------------------

    #: Texture-info slots that sample TEXCOORD_0 and therefore need the
    #: dequantizing transform. All of ours do; listed explicitly so a slot
    #: added later cannot be silently missed.
    _UV_SLOTS = ("baseColorTexture", "metallicRoughnessTexture",
                 "normalTexture", "occlusionTexture", "emissiveTexture")

    def _finalize_uvs(self):
        """Write every TEXCOORD_0 as normalized SHORT against one file-wide scale.

        The stored value is `uv / S` clamped to [-1, 1] and scaled to int16; the
        material's `KHR_texture_transform.scale` is `[S, S]`, which multiplies
        it back on sample. `S` is the largest |uv| in the file, so the quantum
        is `S / 32767`:

            a cottage        S ~   20 m  ->  0.6 mm
            a town-wide      S ~  290 m  ->  8.8 mm

        Against a texture that tiles at 1-2 m and is sampled at 3.9 mm/texel,
        the worst case is about two texels of drift on the largest ground
        venues, and nothing measurable on a building. The alternative was
        95.1 MB of float32 UVs, a third of the whole download.
        """
        if not self._uv_pending:
            return
        hi = 0.0
        for _, uv in self._uv_pending:
            if len(uv):
                hi = max(hi, float(np.abs(uv).max()))
        # Never zero, and never so tight that a rounding step at the extreme
        # clamps a legitimate coordinate to exactly +-1.
        S = max(hi, 1e-3) * 1.0000305        # one quantum of headroom
        self._uv_scale = S
        for attrs, uv in self._uv_pending:
            q = np.rint(np.clip(uv / S, -1.0, 1.0) * 32767.0).astype(np.int16)
            attrs["TEXCOORD_0"] = self._accessor(
                np.ascontiguousarray(q), 5122, "VEC2", 34962, normalized=True, stride=4)
        self._uv_pending = []

        xf = {"scale": [S, S]}
        for mat in self.materials:
            pbr = mat.get("pbrMetallicRoughness", {})
            for holder in (pbr, mat):
                for slot in self._UV_SLOTS:
                    ti = holder.get(slot)
                    if isinstance(ti, dict):
                        ti.setdefault("extensions", {})["KHR_texture_transform"] = dict(xf)
        self.extensions_used.add("KHR_texture_transform")

    def _finalize(self):
        if self._finalized:
            return
        self._finalized = True
        self._finalize_uvs()

    def _doc(self, roots):
        self._finalize()
        doc = {
            "asset": {"version": "2.0", "generator": "evermore assetgen"},
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
        if self.extensions_used:
            doc["extensionsUsed"] = sorted(self.extensions_used)
            req = sorted(self.extensions_used & REQUIRED_EXTENSIONS)
            if req:
                doc["extensionsRequired"] = req
        if self.extras:
            doc["extras"] = self.extras
        return doc

    def _lod_alternates(self):
        """Node indices referenced only as MSFT_lod alternates. They must never
        become scene roots — that is what would draw all four levels at once."""
        out = set()
        for n in self.nodes:
            ids = n.get("extensions", {}).get("MSFT_lod", {}).get("ids", [])
            out.update(int(i) for i in ids)
        return out

    def _roots(self):
        """Scene roots: every node that is neither someone's child nor an
        MSFT_lod alternate.

        The alternate exclusion is load-bearing and was missing. Without it the
        exporter dutifully wrote LOD1/2/3 into `scenes[0].nodes` alongside LOD0,
        so the file that was supposed to make the town cheaper drew every level
        of every cell simultaneously — 1.8x the triangles and 4x the draw calls
        of doing nothing at all.
        """
        children = set()
        for n in self.nodes:
            children.update(int(i) for i in n.get("children", []))
        alts = self._lod_alternates()
        return [i for i in range(len(self.nodes)) if i not in children and i not in alts]

    def write_gltf(self, path, roots=None):
        """Write .gltf + .bin, with external texture URIs.

        Preferred over GLB here because textures stay as inspectable PNGs on
        disk, which the review loop needs — a critic must be able to open a
        roughness map and see why a surface reads wrong.
        """
        roots = roots if roots is not None else self._roots()
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
        roots = roots if roots is not None else self._roots()
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

def material_from_set(w: GLTFWriter, name, tex_prefix, has_emissive=False,
                      double_sided=False, alpha_mode="OPAQUE", normal_scale=1.0,
                      alpha_cutoff=None):
    """Register a material backed by a MaterialSet's written PNGs."""
    return w.material(
        name,
        albedo_tex=f"{tex_prefix}_albedo.png",
        orm_tex=f"{tex_prefix}_orm.png",
        normal_tex=f"{tex_prefix}_normal.png",
        emissive_tex=f"{tex_prefix}_emissive.png" if has_emissive else None,
        metallic=1.0, roughness=1.0,   # factors are 1.0; the ORM map carries the values
        double_sided=double_sided, alpha_mode=alpha_mode, normal_scale=normal_scale,
        alpha_cutoff=alpha_cutoff,
    )
