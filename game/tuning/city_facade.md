# city_facade.tres

Rationale for `game/tuning/city_facade.tres` (`Q119`).

The facade look the city loads, one resource for every tile. `game/tools/generated_scene_import.gd`
maps the ETL's `city_facade` material name to this path only, so this file is the switch between
`Q26`'s looks. Swapping is a copy and a reimport, never a rebuild; all read the same `TEXCOORD_0`
payload:

| Candidate | File | Look |
|---|---|---|
| `C` | this file | flat per-building colour, elements off |
| `A‴` | `city_facade_elements.tres` | the clean look with its elements on |
| `B` | `city_facade_warm.tres` | the measured Hong Kong window bands |

`city_facade_cel.gdshader` (`P3-64`, `Q158`) reads the same payload under a banded sun; not
shipped.

This file ships `C`: accurate massing, flat per-building colour, no facade fabric. `Q26` closed on
it on the user's call. `A‴` was not faulted, and the `P3-9a` driver round can reopen the question.

Six values separate this from `A‴`, and a `diff` should show only these:

    solid_share 1.0 · glass_ratio 0.0 · shopfront_share 0.0 · accent_share 0.0
    floor_line_darkness 0.0 · mullion_darkness 0.0

- `solid_share` is a gate, not a zero: `glazed = step(solid_share, …)`, so at 1.0 no building is
  glazed. Shopfronts, floor lines and mullions draw outside the gate, so all six are needed.
- `cornice_darkness` 0.28, `cornice_thickness_m` 0.5 (`Q195`, the user's pick): drawn only on a
  building whose tile carries an iB1000 podium line in `COLOR_0.a`, never at `podium_height_m`.
- The uniforms the six make inert (`bay_width_m`, `glass_colour`, `pane_bow`, the fresnel terms)
  stay at their `A‴` values on purpose: they keep the two files diffable.
- `base_wash` 0.0: the palette lives in `etl/config/hong_kong.yaml`'s `materials:` table (`Q34`),
  which leaves `base_colour` inert. The per-building hue is `COLOR_0`.
- `value_jitter` 0.35: below it a block reads as one mass; above about 0.4 the darkest buildings
  read as broken.
- `floor_height_m` 2.8: measured, and the same in every look.
- `night_spot_*` (`Q160`): at night `night_spot_share` 0.6 of the buildings are floodlit from
  street level. A lamp every `night_spot_spacing_m` 14 m throws a `night_spot_colour` cone up the
  wall at `night_spot_strength` 0.55; the cones widen with `night_spot_spread` 2.5 into one wash,
  which dims to `night_spot_top` 0.3 by `night_spot_reach_m` 120 m and holds to the roofline. Walls
  only, the wall's own colour, multiplied by the rig's `night_lights`.
- `lit_window_share`, `emission_strength` 0.0: reserved. The user refused lit windows and an
  all-over glow.
