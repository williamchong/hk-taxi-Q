# barrier_vertex.tres

Rationale for `game/tuning/barrier_vertex.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The fence prop's material (`P3-29`) — `tools/make_barrier.py`'s barrier, stood by
`fence.json` across every mouth `RoadGraph.fits_car` closes.

🔴 **`barrier_vertex`, and never `barriers`.** That name is taken: it dispatches
the *railing* class of the same word to `tuning/barriers.tres`, and a prop handed
a fence's shader draws a picket fence where a road barrier should stand and fails
`verify_fence.gd` while both halves render. `tools/make_barrier.py` states the
same rule from the generator's side, and `etl/tests/test_make_barrier.py` pins the
material name.

🔴 **It exists for `landmarks.tres`'s reason** — `P5-28b`'s `exposure_anchor` is a
global shader parameter and a `BaseMaterial3D` cannot read one — and the two share
`vertex_albedo.gdshader`, which is `Q61`'s and `Q71`'s rule at a sixth place: a
layer is a parameterisation, not a shader. They differ in nothing today. That is
allowed to stay true; what is not allowed is collapsing them to one `.tres`,
because then the dispatch check has nothing to tell apart and a hero handed the
barrier's material would pass.

## shader_parameter/roughness_value

0.9 — `gltf.py::_material`'s `roughnessFactor`, the value the `BaseMaterial3D`
this replaces imported with. See `landmarks.md`.
