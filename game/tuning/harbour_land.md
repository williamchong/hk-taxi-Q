# harbour_land.tres

The land beside the harbour that no region's tiles draw (`P3-101`, `Q250`): breakwaters and the
far side of a typhoon shelter, a second mesh in `water.glb`. `LAND_MATERIAL` in
`etl/pipeline/basemap.py`, dispatched by `tools/generated_scene_import.gd`.

`vertex_albedo.gdshader`: the top is `basemap.land_material` and the face under its sea edge
`basemap.quay_material`, both on the vertex from `materials:`.

- Its own `.tres`, never `water.tres`: that one is `water.gdshader`, and land handed it draws
  waves. `verify_water.gd` checks each mesh's dispatch by `resource_path`.
- `roughness_value = 0.9`: matte, the tiles' ground.
- Unlit at night (`Q160`), on the ground's terms.
