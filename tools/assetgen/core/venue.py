"""The venue contract.

Every venue module exposes:

    NAME = "inn"
    CELLS = ["E3", "E4"]
    def build(ctx: VenueContext) -> None: ...

`build` emits geometry through `ctx.emit(mesh, material_key)` and registers
interactables through `ctx.entity(...)`. The context owns material registration,
glTF assembly, and entity-record output, so a venue module never touches the
exporter directly and every venue ends up with identical material handling.

This is what keeps twelve separately-authored venues in one visual language.
"""

from __future__ import annotations

import json
import math
import os
import numpy as np

from . import materials as MAT
from . import gltf as G
from . import collision as COL
from . import atlas as ATL
from . import batch as B
from .mathx import seed_from
from .mesh import Mesh, Group

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
TEX_DIR = os.path.join(REPO, "assets/textures")
MESH_DIR = os.path.join(REPO, "assets/meshes")
ENT_DIR = os.path.join(REPO, "content/entities")
COL_DIR = os.path.join(REPO, "content/collision")

# These were two literal sets maintained here, in a different directory from
# the builders they describe. Adding a lit or a double-sided material meant
# remembering to edit this file too, and nothing failed if you forgot — a
# material could ship with an emissive PNG on disk that no glTF ever referenced.
# They are views onto the registry's own flags now, so the material declares
# what it is in one place.
EMISSIVE = MAT.EMISSIVE
DOUBLE_SIDED = MAT.DOUBLE_SIDED
MASKED = MAT.MASKED
BLEND = MAT.BLEND


class VenueContext:
    """Build-time context handed to each venue module.

    `batching`, `lod` and `instancing` are the three techniques Directive §7
    requires, and all three are ON by default so a venue gets them without
    doing anything. A venue module opts out by setting `BATCH = False`,
    `LOD = False` or `CELL_SIZE = <metres>` at module level — which exactly one
    venue does (`terrain`, which is the ground: it already carries its own
    concentric LOD rings and must never be split on a 16 m module, because at
    576 m across that is 1,296 cells).
    """

    def __init__(self, name, cells=None, seed_salt=0, *, cell_size=None,
                 batching=True, lod=True, instancing=True, atlasing=True):
        self.name = name
        self.cells = cells or []
        self.seed_salt = seed_salt
        self.cell_size = float(cell_size or B.CELL)
        self.batching = bool(batching)
        self.atlasing = bool(atlasing)
        self._atlased = {}          # material key -> triangles taken by a page
        self._loose = {}            # material key -> triangles a page refused
        # NOT `self.lod`. `ctx.lod(mesh_id, levels)` is the authoring API, and an
        # instance attribute of the same name shadows the method — so setting a
        # flag here would make every call to `ctx.lod(...)` raise
        # "'bool' object is not callable" in whichever venue happened to use it.
        # Which is exactly what it did, and only a test caught it, because no
        # venue in the town uses authored LOD chains yet.
        self.lod_enabled = bool(lod)
        self.instancing = bool(instancing)
        self.writer = G.GLTFWriter()
        self._mats = {}
        self._prims = []            # (Mesh, material_key, group_key|None)
        self._instances = {}        # mesh_id -> {"proto", "T", "R", "S"}
        self._lod_chains = {}       # mesh_id -> [l0, l1, l2, l3]
        self._interiors = {}        # interior id -> {"aabb", "portals"}
        self._entities = []
        self._colliders = []
        self._tri_total = 0
        # Per-object bounds captured at emit time, for the occlusion check.
        # This information only exists HERE: by export time everything has been
        # merged per material, so a "terracotta" primitive is every roof in the
        # venue at once and containment tests become meaningless.
        self._emitted = []

    # -- materials ----------------------------------------------------------

    def material(self, key, **kwargs):
        """Register (once) and return a glTF material index for a library key.

        Textures are generated on demand and shared across venues — two venues
        asking for "plaster" get the same PNG, which is both a memory win and a
        cohesion guarantee.
        """
        if key in self._mats:
            return self._mats[key]
        if key in ATL.ATLASES:
            # An atlas page is a material like any other from here on; it is
            # just composed from several rather than built from one.
            self.atlas(key)
            return self._mats[key]
        if key not in MAT.LIBRARY:
            raise KeyError(f"unknown material '{key}'. Add it to materials.LIBRARY "
                           f"rather than inventing one in a venue module.")
        prefix = os.path.join(TEX_DIR, key)
        if not os.path.exists(prefix + "_albedo.png"):
            os.makedirs(TEX_DIR, exist_ok=True)
            # `seed_from`, not `hash()`. Python salts str hashing per process,
            # so `abs(hash(key))` produced a DIFFERENT texture on every run —
            # which silently voided docs/ARCHITECTURE.md §7's determinism claim
            # and made every review diff meaningless. It was measurable: three
            # materials rebuilt with no source change moved their palette
            # distance by up to 3.8. Same bug was in tools/assetgen/build.py.
            MAT.LIBRARY[key](name=key, seed=seed_from("material", key) % 9973
                             ).write(TEX_DIR)
        # Alpha handling, in the order glTF resolves it: a cut-out sheet is
        # MASK (sorts correctly, cheap), old crown glass is BLEND (it really is
        # translucent and there is one pane deep of it), everything else opaque.
        alpha_mode = "MASK" if key in MASKED else ("BLEND" if key in BLEND else "OPAQUE")
        idx = G.material_from_set(
            self.writer, key, f"../textures/{key}",
            has_emissive=key in EMISSIVE,
            double_sided=key in DOUBLE_SIDED,
            alpha_mode=alpha_mode,
            alpha_cutoff=0.5 if alpha_mode == "MASK" else None,
        )
        self._mats[key] = idx
        return idx

    def uv_scale(self, key):
        """UV units per world metre for a material — pass to mesh builders.

        `core/mesh.py` lays UVs in metres, so a material with no scale applied
        covers exactly 1 m per tile no matter what it was authored for. Every
        material in the library now declares its real world coverage, and this
        is how geometry honours it. See D-033.
        """
        return MAT.uv_scale(key)

    def atlas(self, name="kit_props", cell=512):
        """The shared texture atlas `name`, registered as a glTF material.

            a = ctx.atlas()
            ctx.emit(a.pack(kit.barrel(...)))        # one material, one draw

        `pack` rewrites the prop's UVs into its rect AT BUILD TIME, which is
        the only moment the mapping is knowable: `core/batch.py` merges every
        prop in a cell into one vertex buffer, so a post-process could not tell
        which triangle came from which material. Directive §7 requires the
        atlas; this is the whole of the generator-facing API for it.
        """
        a = ATL.get(name, cell=cell)
        if a.name not in self._mats:
            a.write(TEX_DIR)
            self._mats[a.name] = G.material_from_set(
                self.writer, a.name, f"../textures/{a.name}",
                has_emissive=False,
                double_sided=any(k in DOUBLE_SIDED for k in a.keys),
                alpha_mode="OPAQUE",
            )
        return a

    # -- geometry -----------------------------------------------------------

    OCCLUSION_MIN_VOL = 0.35     # m^3; ignore trim and small fittings

    def check_occlusion(self):
        """Flag objects generated wholly inside another object.

        Three separate instances shipped before this check existed: the guild's
        tower lancets sat inside walls spanning past them, its reception counter
        was entombed behind a solid front wall, and the inn's chimneys sat
        2.4-2.9m down inside the roof. Each cost triangles and rendered nothing,
        while the build reported success and the tri count looked healthy.

        What makes this class of bug worth a tripwire is that it silently
        deletes exactly the elements the World Bible briefs call for — a smoking
        chimney, a visible counter — rather than failing loudly.

        OPT-IN by design. An untargeted AABB sweep is useless here: every wall
        of a building legitimately sits inside that building's own bounds, so a
        blanket check produced ~40 false positives per build — and a check that
        cries wolf is worse than no check, because it trains everyone to ignore
        the output.

        So only elements emitted with an explicit `label=` are tested, and only
        against containers emitted with `container=`. That is precise where it
        matters (a chimney against its roof, a counter against its wall) and
        silent everywhere else.
        """
        hits = []
        labelled = [e for e in self._emitted if e[2] is not None]
        containers = [e for e in self._emitted if e[3]]
        for lo, hi, label, _c, _s in labelled:
            for olo, ohi, olabel, ocontainer, oshell in containers:
                if oshell or ocontainer == label:
                    continue
                # Overlap in PLAN, then test whether the element clears the
                # container's top.
                #
                # "Wholly inside the container's box" is the wrong test and was
                # verified not to fire: a buried chimney starts at the eave,
                # which is BELOW the roof's bounding box, so it never satisfied
                # containment even while being completely swallowed. What
                # actually defines burial for a vertical element is failing to
                # clear the thing it must poke through.
                overlaps_plan = (lo[0] < ohi[0] and hi[0] > olo[0] and
                                 lo[2] < ohi[2] and hi[2] > olo[2])
                if overlaps_plan and hi[1] <= ohi[1] + 0.02:
                    hits.append(f"'{label}' top y={hi[1]:.2f} does not clear "
                                f"'{ocontainer}' top y={ohi[1]:.2f} — buried")
                    break
        return hits

    def emit(self, geom, material_key=None, label=None, container=None,
             shell=False, interior=None):
        """Add a Mesh or a multi-material Group to the venue.

        A Group keeps its per-material split, which is both correct (a
        timber-framed wall really is two materials) and the batching the
        renderer wants. `material_key` overrides only for a bare Mesh.

        Emitting no longer costs a draw call. Everything emitted here is
        re-bucketed at `write()` into one primitive per (16 m cell, material),
        so a venue that calls `emit` once per prop and a venue that merges a
        Group first produce the same file. That was NOT true before — emitting
        per prop cost `streets` 1,344 primitives — and the discipline it
        demanded of every venue author is exactly the kind that does not
        survive 90 buildings.

        `interior=<id>` routes the geometry into an interior occlusion group
        declared with `ctx.interior()` instead of into the street-level cells,
        so it is not drawn from outside the building.
        """
        if geom is None or geom.tri_count == 0:
            return
        if interior is not None and interior not in self._interiors:
            raise KeyError(f"emit(interior='{interior}') before ctx.interior('{interior}', ...)")
        group = None if interior is None else f"int:{interior}"
        lo, hi = geom.bounds()
        self._emitted.append((np.asarray(lo, float), np.asarray(hi, float),
                              label, container, shell))
        if isinstance(geom, Group):
            for key, m in geom.items():
                self._add(m, key, group)
            return
        self._add(geom, material_key or geom.mat, group)

    # Directive §7 requires "texture atlasing across the kit". This is where it
    # happens, and it happens HERE rather than in thirty venue modules because
    # a technique every venue has to remember to apply is a technique thirty
    # buildings will not have — the same reason batching, LOD and instancing
    # are decided in this class. `core/atlas.py` was in the tree for four waves
    # with exactly one consumer, and the town shipped 1,416 draw calls.
    #
    # It is not a post-process, and it must not become one: the remap is
    # applied while the mesh's material is still known, before `_bucket()`
    # merges every prop in a cell into one vertex buffer and the question
    # "which rect does this triangle belong to" stops having an answer.
    ATLASING = True

    def _atlas_parts(self, geom):
        """A Group with every auto-atlased material folded onto its page.

        The instancing and LOD paths need this as well as `emit`: an instance
        prototype's primitive count is paid once per CELL that holds twelve or
        more of it, so a five-material barrel is five draws in every cell it
        appears in and a one-material barrel is one.
        """
        if geom is None or not (self.ATLASING and self.atlasing):
            return geom
        out = Group()
        for key, m in (geom.items() if isinstance(geom, Group) else [(geom.mat, geom)]):
            page = ATL.page_for(key)
            if page is None:
                out.add(m, key)
                continue
            packed, left = self.atlas(page).pack_split(m.copy(), key)
            if packed is not None:
                out.add(packed, page)
            if left is not None:
                out.add(left, key)
        return out

    def _add(self, m, key, group):
        """Route one mesh into the primitive list, atlasing what qualifies."""
        page = ATL.page_for(key) if self.ATLASING and self.atlasing else None
        if page is not None:
            packed, left = self.atlas(page).pack_split(m.copy(), key)
            if packed is not None:
                self.material(page)
                self._prims.append((packed, page, group))
                self._tri_total += packed.tri_count
                self._atlased[key] = self._atlased.get(key, 0) + packed.tri_count
                m = left
                if m is None:
                    return
                key = m.mat
            else:
                self._loose[key] = self._loose.get(key, 0) + m.tri_count
        self.material(key)
        self._prims.append((m, key, group))
        self._tri_total += m.tri_count

    # -- instancing ---------------------------------------------------------

    def instance(self, mesh_id, mesh, transforms):
        """Declare N copies of one prototype mesh as a GPU instance batch.

        `mesh_id` is the batching key and must be stable across calls and across
        venues that share a prop — it becomes the node name, the Unreal
        `InstancedStaticMeshComponent`, and the Unity `Graphics.DrawMeshInstanced`
        batch. `mesh` is the prototype in its own local space (origin at the
        prop's base, which is what the transforms then place). `transforms`
        accepts (x,y,z), (x,y,z,yaw), a dict, or a 4x4 matrix — see
        `core.batch.normalize_transforms`.

            ctx.instance("barrel_oak", kit.barrel(), [(x, y, z, yaw), ...])

        Calling it twice with the same id appends; the prototype from the first
        call wins. Instances are grouped by the cell their translation lands in,
        so a 400-barrel town still culls per cell.

        Returns the running instance count for that id.
        """
        if mesh is None or mesh.tri_count == 0:
            return 0
        T, R, S = B.normalize_transforms(transforms)
        if not len(T):
            return 0
        rec = self._instances.get(mesh_id)
        if rec is None:
            proto = self._atlas_parts(
                mesh if isinstance(mesh, Group) else Group({mesh.mat: mesh}))
            for key in proto.parts:
                self.material(key)
            rec = self._instances[mesh_id] = {"proto": proto, "T": [], "R": [], "S": []}
        rec["T"].append(T); rec["R"].append(R); rec["S"].append(S)
        # Bounds are recorded per instance so the occlusion check and the venue
        # bounding box still see instanced props, which are otherwise invisible
        # to every downstream measurement.
        lo, hi = rec["proto"].bounds()
        self._emitted.append((np.asarray(lo, float) + T.min(axis=0),
                              np.asarray(hi, float) + T.max(axis=0), None, None, False))
        return sum(len(t) for t in rec["T"])

    def lod(self, mesh_id, levels):
        """Register an authored LOD chain, overriding the automatic decimator.

            ctx.lod("church_tower", [l0, l1, l2, l3])

        Levels are Meshes or Groups, finest first; a short list is padded by
        repeating the last level. Use this where the automatic vertex-cluster
        simplifier destroys something that has to survive — a spire, a sign
        silhouette, a roof ridge that reads at 100 m.

        If `mesh_id` is also passed to `ctx.instance`, the instance batch uses
        this chain. If nothing instances it, the chain is emitted on its own as
        a LOD'd node at the venue origin, i.e. a hero object that opts out of
        cell batching.
        """
        if not levels:
            return
        chain = [self._atlas_parts(lv) for lv in levels]
        while len(chain) < 4:
            chain.append(chain[-1])
        for lv in chain:
            if lv is None:
                continue
            for key in (lv.parts if isinstance(lv, Group) else {lv.mat: lv}):
                self.material(key)
        self._lod_chains[mesh_id] = chain[:4]

    # -- interiors ----------------------------------------------------------

    def interior(self, iid, aabb, portals=()):
        """Declare an interior occlusion cell and the portals into it.

        Architecture §3: "building interiors are separate cells linked by
        portals at doorways, so an interior's contents are not simulated or
        drawn from outside." This is the authoring end of that. Geometry joins
        it via `ctx.emit(..., interior=iid)`.

            ctx.interior("nave", aabb=((-8, 0, -14), (8, 12, 14)),
                         portals=[{"pos": (0, 1.4, 14), "size": (3.2, 4.4),
                                   "normal": (0, 1)}])

        `aabb` is venue-local ((x0,y0,z0),(x1,y1,z1)). A portal's `normal` is
        the outward XZ direction of the doorway; the client draws the interior
        when the camera is inside the volume, or when it is in front of a
        portal that is on screen.
        """
        lo, hi = (tuple(float(v) for v in aabb[0]), tuple(float(v) for v in aabb[1]))
        ps = []
        for p in portals:
            n = tuple(float(v) for v in p.get("normal", (0.0, 1.0)))
            ln = math.hypot(*n) or 1.0
            ps.append({"pos": [float(v) for v in p["pos"]],
                       "size": [float(v) for v in p.get("size", (2.0, 2.2))],
                       "normal": [n[0] / ln, n[1] / ln],
                       "range": float(p.get("range", 30.0))})
        self._interiors[iid] = {"aabb": [list(lo), list(hi)], "portals": ps}
        return iid

    # -- collision ----------------------------------------------------------
    #
    # Build Directive §6 rule 4. Collision is DECLARED next to the geometry it
    # belongs to, in venue-local space, and written to content/collision/. The
    # client loads that; it may not infer collision from anything it renders.
    #
    # These wrappers exist so that declaring collision costs one line at the
    # site where the wall is emitted. v1 got this wrong not by intent but
    # because doing it right was expensive, so cheapness is the requirement.

    def collider(self, shape="box", **kw):
        """Declare a collision volume. shape ∈ {box, cylinder, hull}.

            ctx.collider("box", center=(0, 1.5, -4), half=(5, 1.5, .2), rot_y=a)
            ctx.collider("cylinder", center=(0, .45, 0), radius=2.5, height=.9)
            ctx.collider("hull", points=[(x, z), ...], y0=0, y1=.12,
                         kind="surface")

        Also accepts a volume (or list of volumes) already built by a
        core.collision helper — `segment_box`, `wall_ring`, `steps` — so those
        compose here rather than each growing its own context method.
        """
        if isinstance(shape, dict):
            self._colliders.append(shape)
            return shape
        if isinstance(shape, (list, tuple)):
            self._colliders.extend(shape)
            return shape
        fn = {"box": COL.box, "cylinder": COL.cylinder, "hull": COL.hull}.get(shape)
        if fn is None:
            raise KeyError(f"unknown collider shape '{shape}' "
                           f"(box | cylinder | hull)")
        vol = fn(**kw)
        self._colliders.append(vol)
        return vol

    def collider_from(self, geom, inset=0.0, y0=None, y1=None, rot_y=0.0,
                      kind="solid", tag=None):
        """Derive a box collider from a Mesh's or Group's bounds. One line.

        `y0`/`y1` override the vertical span — the common case, because a
        wall's collision should run from the ground to head height whatever its
        geometry does, and a roof's bounds must never become a wall.
        """
        lo, hi = geom.bounds()
        vol = COL.from_bounds(lo, hi, inset=inset, y0=y0, y1=y1, rot_y=rot_y,
                              kind=kind, tag=tag)
        self._colliders.append(vol)
        return vol

    def collider_walls(self, width, depth, height, y=0.0, thickness=0.35,
                       center=(0.0, 0.0), rot_y=0.0, doors=(), tag="wall"):
        """A solid rectangular building shell with open doorways.

        `doors` is [(side, offset, width)] with side ∈ {-z, +z, -x, +x}.
        """
        vols = COL.wall_ring(width, depth, height, y=y, thickness=thickness,
                             center=center, rot_y=rot_y, doors=doors, tag=tag)
        self._colliders.extend(vols)
        return vols

    def collider_steps(self, front, height, tread=0.6, width=1.4, rot_y=0.0):
        """A climbable flight up to a threshold, riser-clamped to STEP_HEIGHT.

        Every building in Hearthmere stands on a plinth taller than the
        controller's step height. Without this the doors are visible and
        unreachable.
        """
        vols = COL.steps(front, height, tread=tread, width=width, rot_y=rot_y)
        self._colliders.extend(vols)
        return vols

    # -- entities -----------------------------------------------------------

    def entity(self, eid, archetype, pos, cell=None, verbs=None, rot=None,
               scale=1.0, **components):
        """Register an interactable.

        Architecture §2: only things that can be interacted with, occupied,
        owned, or changed get IDs. Scenery does not — cobbles and roof tiles
        stay anonymous batched geometry.
        """
        rec = {
            "id": eid,
            "archetype": archetype,
            "cell": cell or (self.cells[0] if self.cells else None),
            "transform": {
                "pos": [round(float(x), 4) for x in pos],
                "rot": list(rot) if rot else [0, 0, 0, 1],
                "scale": scale,
            },
            "components": {},
        }
        if verbs:
            rec["components"]["interactable"] = {"verbs": list(verbs), "range": 2.0}
        rec["components"].update(components)
        self._entities.append(rec)
        return eid

    # -- batching, LOD and export -------------------------------------------
    #
    # Everything below runs once, at write(), and is the whole of Directive §7's
    # build-time half. It is here rather than in a venue module on purpose: a
    # technique that every venue has to remember to apply is a technique that
    # 90 buildings will not have.

    # Below this a LOD chain costs three extra nodes to save nothing.
    LOD_MIN_TRIS = 400

    # Break-even for an instance batch, per cell.
    #
    # An EXT_mesh_gpu_instancing node costs exactly one draw call, whatever N
    # is. What it saves is vertex MEMORY — the prototype is stored once instead
    # of N times — and it saves nothing at all on triangles drawn. So it is a
    # win above some N and a loss below it, and the loss is real: a cell with
    # three barrels in it would pay a whole draw call for three barrels whose
    # material the cell was already drawing.
    #
    # Below this count the instances are baked into the ordinary cell batch and
    # cost nothing extra. Venue authors therefore never have to decide; they
    # call ctx.instance for anything repeated and core picks.
    INSTANCE_MIN = 12

    def _instance_cells(self):
        """{mesh_id: {cell_key: index array}} for every declared instance set."""
        if getattr(self, "_icells", None) is not None:
            return self._icells
        out = self._icells = {}
        for mesh_id, rec in self._instances.items():
            T = np.vstack(rec["T"])
            ci = (np.floor(T[:, [0, 2]] / self.cell_size).astype(np.int64)
                  if self.batching else np.zeros((len(T), 2), np.int64))
            cells = {}
            for k in np.unique(ci, axis=0):
                sel = np.flatnonzero((ci[:, 0] == k[0]) & (ci[:, 1] == k[1]))
                cells[B.cell_name(int(k[0]), int(k[1])) if self.batching else "all"] = sel
            out[mesh_id] = cells
        return out

    def _bucket(self):
        """Emitted geometry -> {group key: {material key: Mesh}}.

        The group key is a 16 m cell (`3_n2`), an interior (`int:nave`), or
        `all` when a venue has opted out of batching. One primitive per group
        per material is one draw call, and the group is also the unit the
        client culls and LODs — so batching and culling agree by construction
        rather than by discipline.
        """
        acc = {}

        def add(gkey, key, m):
            g = acc.setdefault(gkey, {})
            a = g.get(key)
            if a is None:
                a = g[key] = _Accum(key)
            a.add(m)

        for m, key, forced in self._prims:
            if forced is not None:
                add(forced, key, m)
            elif not self.batching:
                add("all", key, m)
            else:
                for ck, sub in B.assign_cells(m, self.cell_size):
                    add(ck, key, sub)

        # Instances fold into the ordinary cell batches when instancing is off
        # (the fallback for a consumer without EXT_mesh_gpu_instancing, and the
        # control experiment for measuring what instancing bought), and per-cell
        # whenever a cell holds too few of them to pay for its own draw call.
        for mesh_id in sorted(self._instances):
            rec = self._instances[mesh_id]
            T, R, S = (np.vstack(rec["T"]), np.vstack(rec["R"]), np.vstack(rec["S"]))
            for ck, sel in self._instance_cells()[mesh_id].items():
                if self.instancing and len(sel) >= self.INSTANCE_MIN:
                    continue
                baked = B.bake_instances(rec["proto"], T[sel], R[sel], S[sel])
                for key, m in baked.items():
                    add(ck if self.batching else "all", key, m)

        return {gk: {k: a.build() for k, a in parts.items()}
                for gk, parts in acc.items()}

    def _levels(self, parts):
        """A 4-step LOD chain for one group. Returns [{mat: Mesh}, ...].

        Progressive rather than independent: level 2 is decimated from level 1,
        not from level 0. End ratios 1 / .50 / .16 / .032, a third of the work,
        and the coarse levels inherit the earlier levels' simplification instead
        of re-deriving it slightly differently and popping.

        **The coarse ratios are a MESH MEMORY decision, not a draw-call one.**
        Directive §7's 240 MB was measured at 243.3 MB — over the cliff, and
        `validate.py` fails on it. Measured across the 35 shipped meshes, the
        LOD chain is 47 % of every byte the client downloads: LOD0 127.9 MB,
        LOD1 76.9, LOD2 29.3, LOD3 8.6. LOD1 is untouched — it starts at 15 m
        and `ad-town-05` §17 is already unhappy about how buildings read at
        25-30 m, which is inside it. LOD2 (40-100 m) went .40 -> .32 of LOD1 and
        LOD3 (past 100 m, and a material collapse to 2 draws anyway) went
        .30 -> .20 of LOD2. Neither level carries a surface a reviewer can
        resolve; both carry megabytes.

        The coarse levels also shed MATERIALS, and that is the half of this that
        actually moves the draw-call number. Triangles alone do not: a cell of
        nine materials costs nine draws whether it holds 9,000 triangles or 900.
        So the ceiling is explicit — LOD2 is at most 3 draws per group, LOD3 is
        exactly 1 — which is what makes the budget projectable to 90 buildings
        instead of merely measurable at 8.
        """
        l0 = {k: m for k, m in parts.items() if m is not None and m.tri_count}
        if not l0:
            return []
        if not self.lod_enabled or sum(m.tri_count for m in l0.values()) < self.LOD_MIN_TRIS:
            return [l0]
        l1 = B.collapse_materials({k: B.decimate(m, 0.5) for k, m in l0.items()}, 0.015)
        l2 = B.collapse_materials({k: B.decimate(m, 0.32) for k, m in l1.items()},
                                  0.08, max_materials=3)
        l3 = B.impostor({k: B.decimate(m, 0.20) for k, m in l2.items()})
        return [l0, l1, l2, l3]

    # Screen coverage below which a group is not worth drawing at all.
    # 0.008 of frame height is ~9 px at 1080p: the point at which a prop stops
    # being a shape and becomes a dither the anti-aliasing has to fight. Set
    # lower and roadside grit survives to 100 m and costs 60 draw calls to
    # render three pixels each; this is the same call Unreal's cull-distance
    # volumes make for clutter, made once at build time.
    MIN_COVERAGE = 0.008

    def _cull_distance(self, radius, fov_deg=55.0):
        """Distance past which a group of this size is dropped, or None.

        The counterpart to LOD, and the reason it exists is measurable: the
        streets' 1,250 instanced verge pebbles are 30 cells x 2 prototypes, so
        they cost ~60 draw calls at EVERY level including the impostor — 60
        draws to render sub-pixel grit across a town seen from a hilltop. LOD
        cannot fix that, because the cheapest LOD of a thing you should not be
        drawing is still a draw call. This is Unreal's cull-distance volume and
        Unity's LODGroup culled percentage, decided at build time.

        Only small things are ever affected: a 16 m cell batch has an 11 m
        radius and still covers 21% of the frame at 100 m.
        """
        t = math.tan(math.radians(fov_deg) * 0.5)
        for d in B.LOD_DISTANCES:
            if radius / max(1e-3, d * t) < self.MIN_COVERAGE:
                return float(d)
        return None

    @staticmethod
    def _coverage(radius, distances=B.LOD_DISTANCES, fov_deg=55.0):
        """MSFT_screencoverage for a group of the given radius.

        The client switches on distance because that is what Directive §7
        specifies and what `client/src/main.js` can evaluate per cell for free.
        Screen coverage is the same decision expressed the way UE5's and
        Unity's glTF importers consume it, derived from the same distances so
        the two cannot drift.
        """
        t = math.tan(math.radians(fov_deg) * 0.5)
        return [round(min(1.0, radius / max(1e-3, d * t)), 5) for d in distances] + [0.0]

    def _export_levels(self, levels, node_name, mesh_name, extras):
        """Export a LOD chain as one root node plus MSFT_lod alternates."""
        nodes, stats = [], []
        for i, parts in enumerate(levels):
            prims = [(m, self.material(k)) for k, m in sorted(parts.items())
                     if m is not None and m.tri_count]
            if not prims:
                stats.append((0, 0))
                continue
            suffix = "" if i == 0 else f"$lod{i}"
            mi = self.writer.add_mesh(mesh_name + suffix, prims)
            ex = dict(extras)
            ex["lod"] = i
            ex["tris"] = sum(m.tri_count for m, _ in prims)
            ex["prims"] = len(prims)
            nodes.append(self.writer.add_node(node_name + suffix, mi, extras={"hm": ex}))
            stats.append((ex["tris"], ex["prims"]))
        return nodes, stats

    def _write_geometry(self):
        """Build every node in the file. Returns the manifest."""
        groups = self._bucket()
        cells, tri_by_lod, prim_by_lod = [], [0] * 4, [0] * 4

        def tally(stats, cull_at=None):
            for i, (t, p) in enumerate(stats[:4]):
                tri_by_lod[i] += t
                prim_by_lod[i] += p
            # A group with no LOD chain is drawn at level 0 forever, so it costs
            # its full price at every distance. Charging it only to LOD0 is how
            # a budget report ends up cheerfully under budget and wrong. A group
            # that is CULLED past `cull_at` is the opposite case and costs
            # nothing there, so the two must not be conflated.
            if cull_at is not None:
                return
            for i in range(len(stats), 4):
                tri_by_lod[i] += stats[0][0] if stats else 0
                prim_by_lod[i] += stats[0][1] if stats else 0

        def truncate(levels, radius):
            """Drop the levels a group of this size is never drawn at.

            Also honours the venue's LOD kill switch, so `--no-lod` means no LOD
            anywhere — including chains a venue authored by hand with `ctx.lod`.
            A control experiment that half the pipeline ignores measures nothing.
            """
            if not self.lod_enabled:
                return levels[:1], None
            cull_at = self._cull_distance(radius)
            if cull_at is None:
                return levels, None
            keep = 1 + sum(1 for d in B.LOD_DISTANCES if d < cull_at)
            return levels[:keep], cull_at

        for gkey in sorted(groups):
            parts = groups[gkey]
            levels = self._levels(parts)
            if not levels:
                continue
            lo, hi = _bounds_of(levels[0])
            radius = float(np.linalg.norm(np.asarray(hi) - np.asarray(lo)) * 0.5)
            levels, cull_at = truncate(levels, radius)
            interior = gkey[4:] if gkey.startswith("int:") else None
            extras = {"venue": self.name, "cell": None if interior else gkey,
                      "interior": interior, "cullAt": cull_at,
                      "min": [round(float(v), 3) for v in lo],
                      "max": [round(float(v), 3) for v in hi]}
            nodes, stats = self._export_levels(
                levels, f"{self.name}#{gkey}", f"{self.name}#{gkey}", extras)
            if not nodes:
                continue
            if len(nodes) > 1:
                self.writer.add_lod(nodes[0], nodes[1:], self._coverage(radius))
            tally(stats, cull_at)
            cells.append({"key": gkey, "interior": interior, "cullAt": cull_at,
                          "min": extras["min"], "max": extras["max"],
                          "lodTris": [s[0] for s in stats],
                          "lodPrims": [s[1] for s in stats]})

        instanced = []
        # An authored chain belongs to the prototype, so it must not ALSO be
        # emitted as a standalone hero node once the prototype has been baked.
        if not self.instancing:
            for mesh_id in self._instances:
                self._lod_chains.pop(mesh_id, None)
        for mesh_id in sorted(self._instances) if self.instancing else []:
            rec = self._instances[mesh_id]
            T = np.vstack(rec["T"]); R = np.vstack(rec["R"]); S = np.vstack(rec["S"])
            chain = self._lod_chains.pop(mesh_id, None)
            levels = ([_as_parts(lv) for lv in chain] if chain
                      else self._levels(_as_parts(rec["proto"])))
            if not levels:
                continue
            plo, phi = _bounds_of(levels[0])
            # The prototype is authored at unit size and SCALED per instance —
            # that is the whole point of an instance transform — so its own
            # bounds are not its size in the world. Measured raw, a 0.14 m verge
            # pebble modelled as a 1 m box reports a 0.74 m radius and never
            # qualifies for the size cull it exists to demonstrate.
            lo = np.asarray(plo) * S.min(axis=0)
            hi = np.asarray(phi) * S.max(axis=0)
            radius = float(np.linalg.norm(np.asarray(phi) - np.asarray(plo)) *
                           float(S.max()) * 0.5)
            # Sized on the PROTOTYPE, not on the cell it lands in. A verge pebble
            # is 0.14 m whatever else shares its cell, and it is the pebble that
            # stops being worth a draw call at 40 m.
            levels, cull_at = truncate(levels, radius)

            # The prototype's geometry is written ONCE per level and referenced
            # by every cell's node. Re-adding it per cell is the mistake that
            # makes an instancing implementation bigger than the thing it
            # replaced.
            shared = []
            for i, parts in enumerate(levels):
                prims = [(m, self.material(k)) for k, m in sorted(parts.items())
                         if m is not None and m.tri_count]
                if not prims:
                    break
                shared.append((self.writer.add_mesh(
                    f"{self.name}:{mesh_id}" + ("" if i == 0 else f"$lod{i}"), prims,
                    instanced=True),
                    sum(m.tri_count for m, _ in prims), len(prims)))
            if not shared:
                continue

            for ck, sel in sorted(self._instance_cells()[mesh_id].items()):
                if len(sel) < self.INSTANCE_MIN:
                    continue                   # baked into the cell batch above
                n = int(len(sel))
                nodes, attrs = [], None
                for i, (mi, tris, prims) in enumerate(shared):
                    ex = {"venue": self.name, "cell": ck, "interior": None,
                          "meshId": mesh_id, "instances": n, "lod": i,
                          "cullAt": cull_at, "tris": tris * n, "prims": prims,
                          "min": [round(float(v), 3) for v in (np.asarray(lo) + T[sel].min(axis=0))],
                          "max": [round(float(v), 3) for v in (np.asarray(hi) + T[sel].max(axis=0))]}
                    ni = self.writer.add_node(
                        f"{self.name}#{ck}@{mesh_id}" + ("" if i == 0 else f"$lod{i}"),
                        mi, extras={"hm": ex})
                    attrs = self.writer.add_instancing(
                        ni, T[sel], R[sel], S[sel]) if attrs is None else \
                        self.writer.add_instancing(ni, attributes=attrs)
                    nodes.append(ni)
                if len(nodes) > 1:
                    self.writer.add_lod(nodes[0], nodes[1:], self._coverage(radius))
                tally([(t * n, p) for _, t, p in shared], cull_at)
                instanced.append({"meshId": mesh_id, "cell": ck, "count": n,
                                  "cullAt": cull_at,
                                  # Bounds, so every consumer can place the cost.
                                  # Without them tools/validate.py charged every
                                  # instance batch to the venue ORIGIN, which put
                                  # the whole town's clutter in cell G7 and
                                  # invented a 95-draw hotspot there.
                                  "min": ex["min"], "max": ex["max"],
                                  "lodTris": [t * n for _, t, _ in shared],
                                  "lodPrims": [p for _, _, p in shared]})

        # Authored chains nobody instanced: hero objects with their own LODs.
        for mesh_id in sorted(self._lod_chains):
            levels = [_as_parts(lv) for lv in self._lod_chains[mesh_id]]
            lo, hi = _bounds_of(levels[0])
            radius = float(np.linalg.norm(np.asarray(hi) - np.asarray(lo)) * 0.5)
            levels, _ = truncate(levels, radius)
            c = (np.asarray(lo) + np.asarray(hi)) * 0.5
            ck = B.cell_name(*B.cell_index(c[0], c[2], self.cell_size)) if self.batching else "all"
            extras = {"venue": self.name, "cell": ck, "interior": None, "meshId": mesh_id,
                      "min": [round(float(v), 3) for v in lo],
                      "max": [round(float(v), 3) for v in hi]}
            nodes, stats = self._export_levels(
                levels, f"{self.name}#{ck}${mesh_id}", f"{self.name}:{mesh_id}", extras)
            if not nodes:
                continue
            if len(nodes) > 1:
                self.writer.add_lod(nodes[0], nodes[1:], self._coverage(radius))
            tally(stats)
            cells.append({"key": ck, "interior": None, "meshId": mesh_id,
                          "min": extras["min"], "max": extras["max"],
                          "lodTris": [s[0] for s in stats],
                          "lodPrims": [s[1] for s in stats]})

        return {
            "venue": self.name,
            "cellSize": self.cell_size,
            "lodDistances": list(B.LOD_DISTANCES),
            "batching": self.batching, "lod": self.lod_enabled,
            "instancing": self.instancing,
            "cells": cells,
            "instanced": instanced,
            "interiors": [dict(id=k, **v) for k, v in sorted(self._interiors.items())],
            "stats": {"lodTris": tri_by_lod, "lodPrims": prim_by_lod,
                      "groups": len(cells) + len(instanced)},
        }

    # -- output -------------------------------------------------------------

    def write(self):
        os.makedirs(MESH_DIR, exist_ok=True)
        os.makedirs(ENT_DIR, exist_ok=True)
        os.makedirs(COL_DIR, exist_ok=True)
        manifest = self._write_geometry()
        self.writer.extras["hm"] = manifest
        path = os.path.join(MESH_DIR, f"{self.name}.gltf")
        self.writer.write_gltf(path)
        # Written unconditionally, like the collision file below: the client
        # fetches one per placed venue, so a venue with no interactables was
        # a guaranteed 404 and a console error on every boot. "No entities" is
        # a fact worth stating.
        with open(os.path.join(ENT_DIR, f"{self.name}.json"), "w") as f:
            json.dump({"venue": self.name, "cells": self.cells,
                       "entities": self._entities}, f, indent=2)
        # Written unconditionally, even when empty: an absent file is
        # indistinguishable from a generator that forgot to declare collision,
        # and the client would silently let the player walk through a building.
        # An empty volumes[] is a claim, and validate.py can check it.
        with open(os.path.join(COL_DIR, f"{self.name}.json"), "w") as f:
            json.dump({"$schema": "../schemas/collision.schema.json",
                       "venue": self.name, "cells": self.cells,
                       "space": "venue-local", "volumes": self._colliders},
                      f, indent=2)
        st = manifest["stats"]
        return {
            "venue": self.name,
            "occlusion": self.check_occlusion(),
            "path": path,
            "tris": self._tri_total,
            "materials": sorted(self._mats),
            "entities": len(self._entities),
            "colliders": len(self._colliders),
            "manifest": manifest,
            "cells": len({c["key"] for c in manifest["cells"]}
                         | {i["cell"] for i in manifest["instanced"]}),
            "draws": st["lodPrims"][0],
            "lodPrims": st["lodPrims"],
            "lodTris": st["lodTris"],
            "instances": sum(i["count"] for i in manifest["instanced"]),
            "interiors": len(manifest["interiors"]),
        }


# ---------------------------------------------------------------------------
# Merge accumulator
# ---------------------------------------------------------------------------

class _Accum:
    """Collect meshes for one (group, material) and concatenate once.

    `Mesh.merge` in a loop is O(n^2) — every call re-allocates the whole vertex
    array — and a cell of the streets venue merges four figures' worth of
    cobbles. Buffering the arrays and doing a single vstack at the end took the
    full build from minutes to seconds.
    """

    __slots__ = ("mat", "v", "n", "uv", "idx", "col", "off", "any_col")

    def __init__(self, mat):
        self.mat = mat
        self.v, self.n, self.uv, self.idx, self.col = [], [], [], [], []
        self.off = 0
        self.any_col = False

    def add(self, m):
        nv = len(m.v)
        if not nv or not len(m.idx):
            return
        self.v.append(m.v); self.n.append(m.n); self.uv.append(m.uv)
        self.idx.append(m.idx.astype(np.int64) + self.off)
        if m.col is not None and len(m.col) == nv:
            c = np.asarray(m.col, np.float32)
            if c.shape[1] == 3:
                c = np.concatenate([c, np.ones((nv, 1), np.float32)], axis=1)
            self.col.append(c)
            self.any_col = True
        else:
            self.col.append(nv)          # pad with white at build time
        self.off += nv

    def build(self):
        if not self.v:
            return None
        col = None
        if self.any_col:
            col = np.vstack([c if isinstance(c, np.ndarray) else np.ones((c, 4), np.float32)
                             for c in self.col])
        return Mesh(np.vstack(self.v), np.vstack(self.n), np.vstack(self.uv),
                    np.concatenate(self.idx).astype(np.uint32), col, self.mat)


def _as_parts(geom):
    """Mesh | Group -> {material key: Mesh}."""
    if geom is None:
        return {}
    if isinstance(geom, Group):
        return {k: m for k, m in geom.parts.items() if m is not None and m.tri_count}
    return {geom.mat: geom} if geom.tri_count else {}


def _bounds_of(parts):
    los, his = [], []
    for m in parts.values():
        if m is not None and m.tri_count:
            lo, hi = m.bounds()
            los.append(lo); his.append(hi)
    if not los:
        return np.zeros(3), np.zeros(3)
    return np.min(los, axis=0), np.max(his, axis=0)


# ---------------------------------------------------------------------------
# The town document
# ---------------------------------------------------------------------------
#
# Siting a venue on a slot is NOT here. `core.siting.Site` owns it, alone, and
# owns it because there were briefly two implementations of it — this module's
# `Plot` and `core.siting.Site` — written a day apart by two agents who each
# rediscovered the same mirrored-rotation bug and each shipped their own cure
# into shared core. They agreed on the maths and disagreed on everything else,
# which is the divergence CLAUDE.md forbids. D-025 collapsed them into
# `core.siting.Site`; read that module's docstring for the convention, and
# extend it rather than growing a second one here.

TOWN_JSON = os.path.join(REPO, "content/town/hearthmere.json")
_TOWN = None


def town(path=TOWN_JSON):
    """The town document, read once per process."""
    global _TOWN
    if _TOWN is None:
        with open(path, encoding="utf-8") as f:
            _TOWN = json.load(f)
    return _TOWN


def slot(key):
    """One `buildingSlots[]` row by number (33) or by id ('hm.slot.33.cooper')."""
    for s in town().get("buildingSlots", []):
        if s.get("n") == key or s.get("id") == key:
            return s
    raise KeyError(f"no building slot {key!r} in {TOWN_JSON}")
