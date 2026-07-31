# Unreal Engine 5 Project Scaffold

This directory holds the Unreal-side import path. It is **not** a built UE5
project — the engine could not be installed in the environment this repo was
authored in (see `docs/DECISIONS.md` D-001), so this is the automation and
documentation needed to stand one up, not a `.uproject` that has been opened
and verified.

Be aware of that distinction: everything in `assets/`, `content/`, `tools/`
and `client/` has been built and visually verified. The contents of this
directory have not been executed against a real editor.

## Setup

1. Create a blank C++ project targeting UE 5.4+, named `Hearthmere`.
2. Enable the **Interchange Framework** and **glTF Importer** plugins.
3. Copy `assets/meshes/` and `assets/textures/` into
   `Content/Hearthmere/Raw/`.
4. Import the glTF files. Settings that matter:
   - Import Uniform Scale: **100** (glTF is metres, Unreal is centimetres)
   - Combine Meshes: **off** (per-material sections are needed for instancing)
   - Generate Lightmap UVs: **off** (Lumen)
5. Build the master material `M_Hearthmere_Base` per the channel table in
   `docs/ENGINE_PORTING.md`. **Tick Flip Green Channel** on every normal map —
   our normals are OpenGL (+Y), Unreal expects DirectX (−Y). Missing this makes
   every surface subtly wrong in a way that is hard to diagnose later.
6. Run the layout importer:

   ```
   set HEARTHMERE_REPO=<path to this repo>
   # Unreal Editor > Tools > Execute Python Script > engine/unreal/import_town.py
   ```

## Coordinate conversion

glTF is Y-up right-handed; Unreal is Z-up left-handed. The importer applies:

```
unreal_location = (gltf.x, -gltf.z, gltf.y) * 100
unreal_yaw      = -gltf_rotation_deg
```

This is the only transform in the pipeline, and it lives in one place.
