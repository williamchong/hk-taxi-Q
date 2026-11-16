# boxjunctions.tres

Rationale for `game/tuning/boxjunctions.tres` (`Q119`).

Material of the yellow box junctions, drawn as their own geometry (`P3-18`, `Q53`).
`game/tools/generated_scene_import.gd` maps the ETL's `boxjunctions` material name to this path, and
`verify_boxjunctions.gd` checks the dispatch against the path, not the shader.

`marking_paint.gdshader` is shared with the arrows and the stop lines (`Q71`) and defaults to
white, so this file is the only thing that makes the boxes yellow.

- `paint_colour`: a deliberate duplicate of `road_markings.tres`'s `yellow_colour` (and
  `road_markings.gdshader`'s default), kept out of `hong_kong.yaml`'s `materials:` by `Q53`. Change
  them together.
- `paint_roughness`: as `arrows.tres`.
- `paint_night_glow` 0.6 (`Q160`): the paint burns its own colour at this strength times the rig's
  `night_lights`, 0 by day. One value across `road_markings.tres`, `roadmarks.tres`, `arrows.tres`
  and `boxjunctions.tres`.
- No `paint_opacity` and no fade, for `arrows.md`'s reasons. The hatch is geometry, from
  `pipeline/boxjunctions.py` and `hong_kong.yaml`'s `boxjunctions:` block.

`crossings.glb`'s light-signal crossing stripes (`crossings_signal`) take this material too
(`P3-35g2`, `generated_scene_import.gd`'s `SHADERS` table): a change to `paint_colour` moves them,
and `verify_crossings.gd` holds the pairing.
