# water.tres

Rationale for `game/tuning/water.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The harbour's water plane (2026-09-25, the user's call) — `water.glb`, the basemap's sea
drawn flat at mean sea level by `region.tscn`'s `Water` node.

`tools/generated_scene_import.gd` maps the ETL's `sea_water` material name to this path and
only this path, so this file is the switch: delete the entry there and the plane falls back
to the `BaseMaterial3D` it imported with, which draws the right blue at 0.9 roughness — matte
and pale, water that reads as painted ground. `verify_water.gd` checks the dispatch by
`resource_path`, because that failure is quiet (`signs.tres`'s paragraph).

`vertex_albedo.gdshader`, shared with the two authored props, for `landmarks.md`'s reason:
the colour is on the vertex from `materials:` and a `BaseMaterial3D` cannot read the rig's
`exposure_anchor`. A layer is a parameterisation, not a shader (`Q61`, `Q71`): what tells
water from a hero building is one number below.

⚠️ **Nothing here is a colour, and that is deliberate.** The albedo is `sea_water` in
`hong_kong.yaml`'s `materials:` table — 8.2%, the diffuse reflectance of turbid coastal water,
cited there — because `Q33`'s palette rule is only total while that table is the one place a
colour is written. Do not lighten that entry to make the harbour bluer: the blue is the sky,
and the dial for it is here.

## shader_parameter/roughness_value

0.45, and this is the value that does the work, not the albedo. A water body is dark
diffusely (8%) and reads blue because a smooth surface reflects the sky — `tramway.md`
records the same split for the rail head, at 0.28. Lower is glassier, and glassier is
paler: at 0.15 the harbour from the `ground` viewpoint is a near-white mirror of the
horizon haze with the blue only overhead (`build/driver/water_after_ground`); at 0.45 the
grazing reflection is spread and the sea reads as one deep blue plane
(`water_after_ground_r45`). The user asked for blue, so the rougher one ships; the two
frames are the A/B for the next call. Not 0.9: that is the imported fallback, matte and
pale — painted ground.
