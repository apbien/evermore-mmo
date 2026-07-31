"""UE5 editor utility: place Hearthmere venues from the authoritative layout.

Run inside the Unreal Editor (Tools > Execute Python Script), after importing
the glTF assets to /Game/Hearthmere/Meshes/.

Reads content/town/hearthmere.json rather than hardcoding placement, so the
same layout drives the three.js client and the Unreal level. That is the point
of keeping the town definition as data (docs/ARCHITECTURE.md §1).
"""

import json
import os

import unreal

REPO = os.environ.get("HEARTHMERE_REPO", "")
TOWN = os.path.join(REPO, "content/town/hearthmere.json")
ENTITY_DIR = os.path.join(REPO, "content/entities")
MESH_PATH = "/Game/Hearthmere/Meshes"

# glTF is metres, Unreal is centimetres.
SCALE = 100.0


def _load(path):
    with open(path) as f:
        return json.load(f)


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
        loc = unreal.Vector(ox * SCALE, -oz * SCALE, oy * SCALE)
        rot = unreal.Rotator(0.0, 0.0, -float(v.get("rotationDeg", 0)))

        actor = unreal.EditorLevelLibrary.spawn_actor_from_object(mesh, loc, rot)
        label = v.get("instance") or v["id"]
        actor.set_actor_label(f"Venue_{label}")
        actor.set_folder_path(f"Hearthmere/{v.get('role', 'misc')}")
        placed.append(label)
    return placed


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
    entities = place_entities(town)
    apply_lighting(town)
    unreal.log(f"Hearthmere: placed {len(venues)} venues, {entities} entities")


if __name__ == "__main__":
    main()
