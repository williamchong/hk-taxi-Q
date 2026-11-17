# planters.tres

The roadside planters' material (`P3-98`, `Q247`): `PLANTERS_MATERIAL` in
`etl/pipeline/planters.py`, dispatched by `tools/generated_scene_import.gd`.
`vertex_albedo.gdshader`: the wall's and the shrub's colours are on the vertex from `materials:`
and the shader adds only the rig's exposure.

- Its own `.tres` beside `trees.tres`, which it matches today: one shared material would leave
  `verify_planters.gd` and `verify_trees.gd` nothing to tell apart.
- A planter left on its imported `BaseMaterial3D` draws pale rather than wrong, so
  `verify_planters.gd` checks the dispatch by `resource_path`.
- Unlit at night (`Q160`), on the trees' terms.
- `roughness_value = 0.9`: matte, the trees' value.
