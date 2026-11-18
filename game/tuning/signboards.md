# signboards.tres

The signboards' material (`P3-103`, `Q260`): `SIGNBOARDS_MATERIAL` in `etl/pipeline/signboards.py`,
dispatched by `tools/generated_scene_import.gd`. `signboards.gdshader`: `vertex_albedo.gdshader`
with the board's two faces lit at night.

- The colour rides `COLOR_0`: the board's photo colour where `tools/signboard_colour.py` is
  confident, else `signboards.palette`. A printed ground, not a `materials:` reflectance, on
  `signs.colours`' terms; the rig's exposure still scales it, since a board is lit by the same sun.
- `face_glow` 1.5: the faces (`COLOR_0` alpha 0) emit their own colour times this times the rig's
  `night_lights`, so a board is unlit by day and burns at night. Under the glow pass's 3.0
  threshold, so a board reads lit without blooming the street; the lanterns' 3.0 blooms.
- `roughness_value` 0.6: a painted or acrylic face, smoother than the paths' 0.9.
- A board left on its imported `BaseMaterial3D` draws its colour but never lights, so
  `verify_signboards.gd` checks the dispatch by `resource_path`.
