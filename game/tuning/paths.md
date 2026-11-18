# paths.tres

The pedestrian lines' material (`P3-101`, `Q250`): `PATHS_MATERIAL` in `etl/pipeline/paths.py`,
dispatched by `tools/generated_scene_import.gd`. `vertex_albedo.gdshader`: the colour is on the
vertex from `materials.path_edging` and the shader adds only the rig's exposure.

- Its own `.tres` beside `planters.tres`, which it matches today: one shared material would leave
  `verify_paths.gd` and `verify_planters.gd` nothing to tell apart.
- A ribbon left on its imported `BaseMaterial3D` draws pale rather than wrong, so
  `verify_paths.gd` checks the dispatch by `resource_path`.
- Unlit at night (`Q160`), on the ground's terms.
- `roughness_value = 0.9`: matte, the planters' value.
