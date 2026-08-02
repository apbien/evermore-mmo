"""UE5 editor utility: place Hearthmere venues from the authoritative layout.

Run inside the Unreal Editor (Tools > Execute Python Script), after importing
the glTF assets to /Game/Hearthmere/Meshes/.

Reads content/town/hearthmere.json rather than hardcoding placement, so the
same layout drives the three.js client and the Unreal level. That is the point
of keeping the town definition as data (docs/ARCHITECTURE.md §1).

It also reads the batching manifest each venue glTF carries (`extras.hm`) and
rebuilds the build's decisions as Unreal constructs: instance batches become
`HierarchicalInstancedStaticMeshComponent`s with the build's cull distances,
and every actor is foldered by its 16 m cell so World Partition can use the
same partition the client culls on. See docs/ENGINE_PORTING.md.
"""

import json
import os
import struct

import unreal

REPO = os.environ.get("HEARTHMERE_REPO", "")
TOWN = os.path.join(REPO, "content/town/hearthmere.json")
MESH_DIR = os.path.join(REPO, "assets/meshes")
ENTITY_DIR = os.path.join(REPO, "content/entities")
MESH_PATH = "/Game/Hearthmere/Meshes"

# glTF is metres, Unreal is centimetres.
SCALE = 100.0


def _load(path):
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# The batching manifest (docs/BUILD_DIRECTIVE.md §7)
#
# `tools/assetgen/core/venue.py` writes a `extras.hm` block into every venue
# glTF describing how it was batched: the 16 m cell of each primitive, the LOD
# chain, the GPU instance batches and their cull distances. Interchange imports
# the GEOMETRY of all of that natively — MSFT_lod becomes StaticMesh LODs and
# EXT_mesh_gpu_instancing becomes instanced components — but it throws the
# manifest away, and the manifest is what maps onto World Partition.
#
# So this reads it directly. It is plain JSON next to plain glTF, which is the
# whole reason the batching decisions were recorded as data instead of being
# implicit in the node graph.
# ---------------------------------------------------------------------------

_COMP = {5120: "b", 5121: "B", 5122: "h", 5123: "H", 5125: "I", 5126: "f"}
_NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def read_accessor(doc, blob, index):
    """Rows of a glTF accessor as a list of tuples."""
    acc = doc["accessors"][index]
    bv = doc["bufferViews"][acc["bufferView"]]
    off = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    n = _NCOMP[acc["type"]]
    fmt = "<" + _COMP[acc["componentType"]] * n
    size = struct.calcsize(fmt)
    return [struct.unpack_from(fmt, blob, off + i * size) for i in range(acc["count"])]


def venue_manifest(venue_id):
    """(manifest, gltf doc, .bin bytes) for a venue, or (None, None, None)."""
    path = os.path.join(MESH_DIR, f"{venue_id}.gltf")
    if not os.path.exists(path):
        return None, None, None
    doc = _load(path)
    hm = (doc.get("extras") or {}).get("hm")
    if hm is None:
        return None, doc, None
    bin_path = os.path.join(MESH_DIR, doc["buffers"][0]["uri"])
    with open(bin_path, "rb") as f:
        blob = f.read()
    return hm, doc, blob


def gltf_to_ue_location(x, y, z):
    """glTF Y-up right-handed -> Unreal Z-up left-handed, metres -> centimetres."""
    return unreal.Vector(x * SCALE, -z * SCALE, y * SCALE)


def place_venues(town):
    """Spawn one StaticMeshActor per venue at its authored origin."""
    placed = []
    for v in town["venues"]:
        asset_path = f"{MESH_PATH}/{v['id']}"
        mesh = unreal.EditorAssetLibrary.load_asset(asset_path)
        if not mesh:
            unreal.log_warning(f"missing mesh for venue '{v['id']}' at {asset_path}")
            continue

        # glTF Y-up -> Unreal Z-up: (x, y, z)_gltf becomes (x, -z, y)_unreal.
        ox, oy, oz = v["origin"]
        loc = gltf_to_ue_location(ox, oy, oz)
        rot = unreal.Rotator(0.0, 0.0, -float(v.get("rotationDeg", 0)))

        actor = unreal.EditorLevelLibrary.spawn_actor_from_object(mesh, loc, rot)
        label = v.get("instance") or v["id"]
        actor.set_actor_label(f"Venue_{label}")
        actor.set_folder_path(f"Hearthmere/{v.get('role', 'misc')}")
        placed.append(label)
    return placed


def place_instances(town):
    """Rebuild every EXT_mesh_gpu_instancing batch as an ISM component.

    Interchange already turns the extension into instanced geometry on import,
    so this is not about getting the props into the level — it is about getting
    them in as ONE ISM per (prototype, cell) with the build's cull distance on
    it, which is what makes the batching decision survive into Unreal instead of
    being re-derived by hand later.

    The transform conversion is the same handedness flip as `place_venues`, with
    one addition: a yaw about glTF's +Y is a yaw about Unreal's +Z with the sign
    flipped, because the flip reverses the winding of the horizontal plane.
    """
    made = 0
    for v in town["venues"]:
        hm, doc, blob = venue_manifest(v["id"])
        if not hm or not hm.get("instanced"):
            continue
        # One node per (mesh id, cell); find them by the name core/venue.py gives.
        by_name = {n["name"]: n for n in doc["nodes"]}
        ox, oy, oz = v["origin"]
        for grp in hm["instanced"]:
            node = by_name.get(f"{v['id']}#{grp['cell']}@{grp['meshId']}")
            if node is None:
                continue
            attrs = node["extensions"]["EXT_mesh_gpu_instancing"]["attributes"]
            T = read_accessor(doc, blob, attrs["TRANSLATION"])
            R = read_accessor(doc, blob, attrs["ROTATION"]) if "ROTATION" in attrs else None
            S = read_accessor(doc, blob, attrs["SCALE"]) if "SCALE" in attrs else None

            proto = unreal.EditorAssetLibrary.load_asset(
                f"{MESH_PATH}/{v['id']}_{grp['meshId']}")
            if not proto:
                unreal.log_warning(f"no prototype mesh for instance batch "
                                   f"{v['id']}:{grp['meshId']}")
                continue

            actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
                unreal.Actor, unreal.Vector(0, 0, 0), unreal.Rotator())
            actor.set_actor_label(f"ISM_{v['id']}_{grp['meshId']}_{grp['cell']}")
            actor.set_folder_path(f"Hearthmere/Instanced/{v['id']}")
            comp = unreal.HierarchicalInstancedStaticMeshComponent(actor)
            comp.set_static_mesh(proto)
            # The build's screen-size cull, carried across verbatim. Without it
            # Unreal draws 1,250 verge pebbles from the far side of the town.
            if grp.get("cullAt"):
                comp.set_cull_distances(0, int(grp["cullAt"] * SCALE))
            for i, t in enumerate(T):
                # Venue-local -> world, then glTF -> Unreal.
                loc = gltf_to_ue_location(ox + t[0], oy + t[1], oz + t[2])
                yaw = 0.0
                if R:
                    x, y, z, w = R[i]
                    yaw = -unreal.MathLibrary.degrees_atan2(
                        2.0 * (w * y + x * z), 1.0 - 2.0 * (y * y + z * z))
                sc = S[i] if S else (1.0, 1.0, 1.0)
                comp.add_instance(unreal.Transform(
                    loc, unreal.Rotator(0.0, 0.0, yaw),
                    unreal.Vector(sc[0], sc[2], sc[1])))
            made += 1
    return made


def report_batching(town):
    """Print what the build decided, so an importer can be checked against it."""
    cells, groups, insts = set(), 0, 0
    for v in town["venues"]:
        hm, _doc, _blob = venue_manifest(v["id"])
        if not hm:
            continue
        cells.update(c["key"] for c in hm["cells"])
        groups += hm["stats"]["groups"]
        insts += sum(g["count"] for g in hm["instanced"])
    unreal.log(f"Hearthmere batching: {groups} batch groups over {len(cells)} cells, "
               f"{insts} GPU instances; LOD switches at "
               f"{hm['lodDistances'] if hm else '?'} m")


def place_entities(town):
    """Spawn interactable entities as tagged actors.

    Entity IDs are stable and never reused, so they are safe to use as the
    persistent key for replication and save state on the Unreal side too.
    """
    count = 0
    for name in {v["id"] for v in town["venues"]}:
        path = os.path.join(ENTITY_DIR, f"{name}.json")
        if not os.path.exists(path):
            continue
        for e in _load(path).get("entities", []):
            px, py, pz = e["transform"]["pos"]
            loc = unreal.Vector(px * SCALE, -pz * SCALE, py * SCALE)
            actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
                unreal.TargetPoint, loc, unreal.Rotator())
            actor.set_actor_label(e["id"])
            actor.set_folder_path(f"Hearthmere/Entities/{name}")
            tags = [e["id"], e.get("archetype", "")]
            for verb in e.get("components", {}).get("interactable", {}).get("verbs", []):
                tags.append(f"verb:{verb}")
            actor.tags = [unreal.Name(t) for t in tags if t]
            count += 1
    return count


def apply_lighting(town):
    """Apply the locked 09:30 rig from Art Bible §4 so the level matches the
    renders every venue was signed off from."""
    lit = town.get("lighting", {})
    for actor in unreal.EditorLevelLibrary.get_all_level_actors():
        if isinstance(actor, unreal.DirectionalLight):
            actor.set_actor_rotation(
                unreal.Rotator(0.0, -float(lit.get("sunElevationDeg", 38.0)),
                               float(lit.get("sunAzimuthDeg", 125.0))), False)
            comp = actor.directional_light_component
            comp.set_intensity(float(lit.get("sunIntensity", 3.2)))
            unreal.log("applied locked sun angle")


def main():
    if not REPO:
        unreal.log_error("set HEARTHMERE_REPO to the repository root first")
        return
    town = _load(TOWN)
    venues = place_venues(town)
    instances = place_instances(town)
    entities = place_entities(town)
    apply_lighting(town)
    report_batching(town)
    unreal.log(f"Hearthmere: placed {len(venues)} venues, {instances} instance "
               f"batches, {entities} entities")


if __name__ == "__main__":
    main()
