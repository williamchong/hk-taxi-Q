# signs.tres

Traffic sign plates and poles (`P3-16`). `tools/generated_scene_import.gd` maps the ETL's `signs`
material name to this file. Without the dispatch a sign falls back to its imported
`BaseMaterial3D` and the city's signage comes out pale, not absent (`Q27`), so `verify_signs.gd`
checks the dispatch.

No colour here: a sign is four colours, so the livery is `hong_kong.yaml`'s `signs.colours` on
`COLOR_0`. This file holds only how the surface takes light.

- `plate_roughness = 0.55`: painted aluminium.
- `sheeting_glow = 0.06`: the retroreflective lift. Judge a change under `golden_hour` too: in low
  light a NO ENTRY that reads as a lamp is worse than one that reads flat.
