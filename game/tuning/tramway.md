# tramway.tres

The tramway's rail heads and track bed (`P3-14`, `Q58`). `tools/generated_scene_import.gd` maps
the ETL's `tramway` material name to this file. One resource for the region.

No colour here: both albedos are `hong_kong.yaml`'s `materials:` (`steel_rail` 35%,
`concrete_sooty` 22%), per `Q33`. This file is how the two catch light. Judge on Hennessy and
Johnston at a low sun; at noon a rail and a painted line look the same.

- `rail_roughness = 0.28`, `bed_roughness = 0.9`: the value that does the work. A rail reads as a
  polished strip in a matte street. Reach for this first if the tramway reads as painted.
- `rail_metallic = 0.0`: at 0.65 the rails rendered sky blue, because metal reflects its
  environment and the only one here is sky.
- `sky_zenith`, `sky_horizon`, `ground_reflection`, `rail_reflect = 0.5`, `rail_face_on = 0.05`,
  `fresnel_power = 5.0`: the head's sheen is the car's painted sky (`Q168`), dimmed and warmed by
  the rig's `sky_light`. 0.5 at grazing is the user's pick over 1.0. Flank and bed take none.
- `rail_head_fraction = 0.55`: the share of the rail's width that is polished head.
- `flank_darkening = 0.35`: shades the rail only. Darkening the bed's edges would draw two lines
  no source puts there (`Q54`).
