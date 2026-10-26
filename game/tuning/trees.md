# trees.tres

Rationale for `game/tuning/trees.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The published trees' material (`P3-77`, `Q171`): `TREES_MATERIAL` in
`etl/pipeline/trees.py`, dispatched by `tools/generated_scene_import.gd`.
`vertex_albedo.gdshader` again — the colours are on the vertex from `materials:`
(`tree_foliage`, `palm_frond`, `conifer_foliage`, `tree_bark`), graded by `Q33`
like every other, and the shader adds only the rig's exposure. A layer is a
parameterisation, not a shader (`Q61`, `Q71`).

⚠️ **Its fallback failure is `signs.tres`'s quiet one**: a tree left on its
imported `BaseMaterial3D` draws the right greens at reflectance level, pale by
the exposure anchor, so `verify_trees.gd` checks the dispatch by
`resource_path`. 🔴 **Unlit at night** (`Q160`): nothing on a tree glows, so
there is no `COLOR_0` alpha marker and no night parameter here.

## shader_parameter/roughness_value

0.9, the landmarks' and the glTF's own `roughnessFactor`: a leaf is matte at
this distance, and a lower value would put a sheen on every canopy.
