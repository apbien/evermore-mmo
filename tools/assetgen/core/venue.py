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
EMISSIVE = {"coal", "glass"}
# Materials rendered from both sides (thin sheets: canvas, cloth, leaves).
DOUBLE_SIDED = {"canvas", "glass", "foliage", "foliage_flower"}


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

    def emit(self, geom, material_key=None):
        """Add a Mesh or a multi-material Group to the venue.

        A Group keeps its per-material split, which is both correct (a
        timber-framed wall really is two materials) and the batching the
        renderer wants. `material_key` overrides only for a bare Mesh.
        """
        if geom is None or geom.tri_count == 0:
            return
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
            "path": path,
            "tris": self._tri_total,
            "materials": sorted(self._mats),
            "entities": len(self._entities),
        }
