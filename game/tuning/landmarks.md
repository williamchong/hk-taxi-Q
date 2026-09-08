# landmarks.tres

Rationale for `game/tuning/landmarks.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The authored heroes' material (`P3-6`, `P5-10`) — Central Plaza today, whatever
`tools/make_landmark.py` builds tomorrow.

🔴 **It exists because `P5-28b` gave the city an `exposure_anchor` global and a
`BaseMaterial3D` cannot read one.** Until then a hero arrived with no material
name this project recognised and fell through the last branch of
`tools/generated_scene_import.gd`, which sets `vertex_color_use_as_albedo` and
`vertex_color_is_srgb` on the imported material — the `Q27` fix in its
`BaseMaterial3D` form, and completely correct for what it does. What it cannot do
is scale an albedo by a global, so once `P5-28c` stops baking the anchor into
`COLOR_0` a hero left on that branch renders at reflectance level: pale by a
constant factor, in a way that reads as a lighting choice rather than as a bug.

⚠️ **So the hero now names `landmark_vertex` into `SHADERS` like every other
layer**, and `verify_landmarks.gd` checks the dispatch by `resource_path` — the
`check_shader_material` route, never `check_shader_source`, because this file and
`barrier_vertex.tres` share one shader and the source cannot tell them apart.

## shader_parameter/roughness_value

0.9, which is not a look decision — it is `gltf.py::_material`'s own
`roughnessFactor`, the value the `BaseMaterial3D` this replaces imported with. The
point of `P5-28b` is that the frame does not move, so every property of the
surface that is not the anchor has to arrive at the same number by a different
road.
