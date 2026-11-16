# landmarks.tres

Rationale for `game/tuning/landmarks.tres` (`Q119`).

Material of the authored heroes (`P3-6`, `P5-10`), built by `tools/make_landmark.py`.

- A `ShaderMaterial` on `vertex_albedo.gdshader` because `exposure_anchor` is a global shader
  parameter and a `BaseMaterial3D` cannot read one (`P5-28b`). On the importer's fallback branch
  a hero renders at reflectance level, pale by a constant factor.
- The hero names `landmark_vertex` into `generated_scene_import.gd`'s `SHADERS`.
  `verify_landmarks.gd` checks the dispatch by `resource_path` (`check_shader_material`, never
  `check_shader_source`): this file and `barrier_vertex.tres` share one shader.
- `roughness_value` 0.9: `gltf.py::_material`'s `roughnessFactor`, what the replaced material
  imported with.
