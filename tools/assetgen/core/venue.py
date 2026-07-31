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
import os
import numpy as np

from . import materials as MAT
from . import gltf as G
from .mesh import Mesh, Group

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
TEX_DIR = os.path.join(REPO, "assets/textures")
MESH_DIR = os.path.join(REPO, "assets/meshes")
ENT_DIR = os.path.join(REPO, "content/entities")

# Materials that need an emissive channel wired up in glTF.
EMISSIVE = {"coal", "glass", "glass_lit"}
# Materials rendered from both sides (thin sheets: canvas, cloth, leaves).
DOUBLE_SIDED = {"canvas", "glass", "glass_lit", "foliage", "foliage_flower", "banner"}


class VenueContext:
    """Build-time context handed to each venue module."""

    def __init__(self, name, cells=None, seed_salt=0):
        self.name = name
        self.cells = cells or []
        self.seed_salt = seed_salt
        self.writer = G.GLTFWriter()
        self._mats = {}
        self._prims = []
        self._entities = []
        self._tri_total = 0
        # Per-object bounds captured at emit time, for the occlusion check.
        # This information only exists HERE: by export time everything has been
        # merged per material, so a "skin" primitive is every NPC in the venue
        # at once and containment tests become meaningless.
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
        if key not in MAT.LIBRARY:
            raise KeyError(f"unknown material '{key}'. Add it to materials.LIBRARY "
                           f"rather than inventing one in a venue module.")
        prefix = os.path.join(TEX_DIR, key)
        if not os.path.exists(prefix + "_albedo.png"):
            os.makedirs(TEX_DIR, exist_ok=True)
            MAT.LIBRARY[key](name=key, size=1024, seed=abs(hash(key)) % 9973).write(TEX_DIR)
        idx = G.material_from_set(
            self.writer, key, f"../textures/{key}",
            has_emissive=key in EMISSIVE,
            double_sided=key in DOUBLE_SIDED,
            alpha_mode="BLEND" if key == "glass" else "OPAQUE",
        )
        self._mats[key] = idx
        return idx

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
             shell=False):
        """Add a Mesh or a multi-material Group to the venue.

        A Group keeps its per-material split, which is both correct (a
        timber-framed wall really is two materials) and the batching the
        renderer wants. `material_key` overrides only for a bare Mesh.
        """
        if geom is None or geom.tri_count == 0:
            return
        lo, hi = geom.bounds()
        self._emitted.append((np.asarray(lo, float), np.asarray(hi, float),
                              label, container, shell))
        if isinstance(geom, Group):
            for key, m in geom.items():
                self._prims.append((m, self.material(key)))
                self._tri_total += m.tri_count
            return
        key = material_key or geom.mat
        self._prims.append((geom, self.material(key)))
        self._tri_total += geom.tri_count

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

    # -- output -------------------------------------------------------------

    def write(self):
        os.makedirs(MESH_DIR, exist_ok=True)
        os.makedirs(ENT_DIR, exist_ok=True)
        mi = self.writer.add_mesh(self.name, self._prims)
        self.writer.add_node(self.name, mi)
        path = os.path.join(MESH_DIR, f"{self.name}.gltf")
        self.writer.write_gltf(path)
        if self._entities:
            with open(os.path.join(ENT_DIR, f"{self.name}.json"), "w") as f:
                json.dump({"venue": self.name, "cells": self.cells,
                           "entities": self._entities}, f, indent=2)
        return {
            "venue": self.name,
            "occlusion": self.check_occlusion(),
            "path": path,
            "tris": self._tri_total,
            "materials": sorted(self._mats),
            "entities": len(self._entities),
        }
