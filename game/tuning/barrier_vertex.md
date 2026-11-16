# barrier_vertex.tres

Rationale for `game/tuning/barrier_vertex.tres` (`Q119`).

Material of the fence prop (`P3-29`): `tools/make_barrier.py`'s barrier, stood by `fence.json`
across every mouth `RoadGraph.fits_car` closes.

- Named `barrier_vertex`, never `barriers`: that name dispatches the railing class to
  `tuning/barriers.tres`, and the prop would draw as a picket fence and fail `verify_fence.gd`.
  `etl/tests/test_make_barrier.py` pins the name.
- A `ShaderMaterial` on `vertex_albedo.gdshader` because `exposure_anchor` is a global shader
  parameter a `BaseMaterial3D` cannot read (`P5-28b`). Identical to `landmarks.tres` today; keep
  them two files, or the dispatch check has nothing to tell apart.
- `roughness_value` 0.9: `gltf.py::_material`'s `roughnessFactor`, what the replaced material
  imported with.
