# trees.tres

The published trees' material (`P3-77`, `Q171`): `TREES_MATERIAL` in `etl/pipeline/trees.py`,
dispatched by `tools/generated_scene_import.gd`. `vertex_albedo.gdshader`: colours are on the
vertex from `materials:` and the shader adds only the rig's exposure.

- A tree left on its imported `BaseMaterial3D` draws pale rather than wrong, so `verify_trees.gd`
  checks the dispatch by `resource_path`.
- Unlit at night (`Q160`): no `COLOR_0` alpha marker and no night parameter.
- `roughness_value = 0.9`: matte, the landmarks' value; lower puts a sheen on every canopy.
