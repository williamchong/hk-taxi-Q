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

`water.gdshader`, the water's own: `vertex_albedo.gdshader`'s vertex-colour-times-exposure
body (a `BaseMaterial3D` cannot read the rig's `exposure_anchor`, `landmarks.md`) plus the
waves — two crossed sine trains in world plan, moved by `TIME`, that tilt the shading normal
per pixel and lift the crests. Its own file rather than a change to `vertex_albedo`, whose
header forbids growing it: the two props sharing that one are graded against a shipped frame.
No texture: the bundle carries none (`Q63`) and the plane has 213 triangles, nothing to
displace, so the wave is procedural and every number is here.

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

## shader_parameter/wave_length_m

6.0 m crest to crest for the first train, the second at `wave_ratio` 0.6 of it (3.6 m)
crossing it. Harbour chop, not swell: from the quay at 5 m the pattern has to be visibly a
pattern, and from the `ground` viewpoint at 45 m it has to stop short of moiré on a 1080 p
frame — a 6 m wave 250 m out is ~4 px.

## shader_parameter/wave_speed_hz

0.25 crests a second, the second train at 0.7 of it the other way. Slow: the taxi does 70 kph
past this water and a fast wave under a fast car reads as strobing.

## shader_parameter/wave_slope

0.12 rise over run — the normal leans ~7°. What it moves is the sky's reflection, so at
`roughness_value` 0.45 the effect is bands of lighter and darker blue, not glints. Raise it
before raising `crest_lift` if the water reads as flat.

## shader_parameter/crest_lift

0.12: a crest is 6% lighter than the trough, the trough 6% darker. The one term that reaches
the albedo, and kept small on purpose: the material's 8.2% reflectance is cited (`Q33`) and a
lift is a departure from it on half the surface.

## shader_parameter/wave_bearing_deg

20°: the first train runs up the harbour from the west-south-west, roughly along it, the way
the wind and the ferry wakes do; the second crosses it. A bearing, not a vector, because the
frame's north is -Z (`crs.py`) and a vector here would be a place to get that wrong.
