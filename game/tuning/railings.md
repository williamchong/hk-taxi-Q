# railings.tres

Pedestrian railings (`P3-19`, `Q60`). `tools/generated_scene_import.gd` maps the ETL's `railings`
material name to this file.

The fence is split across two files. Mesh (height, station pitch, kerb outset, foot sink) is
`pipeline/railings.py` from `hong_kong.yaml`'s `railings:` block. Mask (balusters, posts, rail
bands) is here, drawn by `railings.gdshader`. Both are authored: nothing published gives a railing
dimension (`Q60`).

- `rail_colour = 0.569` grey: `hong_kong.yaml`'s `galvanised_steel` (`#919191`, 28% reflectance),
  the lamp columns' colour (`Q215`). Copied, not read through `materials:` (`Q53`, in the shader),
  so change both together. Dead neutral: Hong Kong's railings are galvanised grey, not green, and
  the cool cast in shade is the ambient's (`clean_daylight.md`).
- `rail_roughness = 0.55`.
- `rail_metallic = 0.0`: metal reflects its environment and the mobile tier has only sky, so the
  tram rails at 0.65 came out sky blue (`P3-14`). Painted steel is a dielectric anyway.
- `sky_zenith`, `sky_horizon`, `ground_reflection`, `rail_reflect = 0.25`, `rail_face_on = 0.05`,
  `fresnel_power = 5.0`: the car's painted-sky sheen (`Q168`), dimmed and warmed by the rig's
  `sky_light`. Same values as `bollards.tres` and `barriers.tres`. On a fence it darkens by a few
  codes: a vertical face's reflection lands half in `ground_reflection`, which is under the
  albedo. Shipped on the user's call.
- `baluster_pitch_m = 0.11`, `baluster_width_m = 0.035`, `post_pitch_m = 2.0`,
  `post_width_m = 0.09`: the mask's members.
- `top_rail_m = (0.95, 1.1)`, `bottom_rail_m = (0.08, 0.18)`: metres above the ribbon deck
  (`UV.y`'s frame; 0 is the ground line, not the mesh bottom).
- `skirt_top_m = 0.0`: below the deck the fence is solid, so no daylight shows under the sunk
  foot.

`ALPHA` is coverage, not opacity: the fraction of a fragment the members cover. There is no
opacity dial and there should not be one.
