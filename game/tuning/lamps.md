# lamps.tres

Rationale for `game/tuning/lamps.tres` (`Q119`).

Material of the lamp posts (`P3-26`). `signs.tres`'s sibling on the same `signs.gdshader`: a layer
is a parameterisation, not a shader (`Q61`, `Q71`). A change to that shader is a change to the
signs and the lamps; `check.sh` exits 0 on a shader that fails to compile, so render both and
`grep -i "shader error"`.

`game/tools/generated_scene_import.gd` maps the ETL's `lamps` material name to this path.
`verify_lamps.gd` checks the dispatch by `resource_path`, because a column that kept its imported
`BaseMaterial3D` still draws in place, only pale (`Q27`).

No colour here. The column's colour rides `COLOR_0`, and its authority is
`lamps.column_material` (`galvanised_steel`) in `hong_kong.yaml`'s `materials:` table, graded by
`_check_reflectance` like a façade (`Q33`). `signs.colours`' exemption does not apply: a column is
a real surface, not a printed specification.

- `apply_exposure` true (`P5-28b`): the column's colour is a reflectance, so the rig's exposure
  scales it. Absent, so false, on `signs.tres`, whose printed livery must not move with the hour.
  The shader's default is off: the safe failure.
- `plate_roughness` 0.8: rougher than a sign plate. Weathered hot-dip galvanised steel.
- `sheeting_glow` 0.0: load-bearing. It is the signs' retroreflection, and any value above zero
  lights the whole column, at noon.
- `lantern_colour`, `lantern_glow` 3.0 (`Q160`, the user's instruction): the lantern is lit at
  night only. The glow is multiplied by the rig's `night_lights`. The ETL marks the housing's
  luminous faces with `COLOR_0` alpha 0 (`library_lit_vertices`), and the shader lights only
  those. 3.0 is over the glow pass's threshold, so the lantern blooms. The light on the road is
  `lamp_pools.tres`'s.
