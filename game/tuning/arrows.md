# arrows.tres

Rationale for `game/tuning/arrows.tres` (`Q119`).

Material of the turn arrows, drawn as their own geometry (`P3-15`, `Q53`).
`game/tools/generated_scene_import.gd` maps the ETL's `arrows` material name to this path, and
`verify_arrows.gd` checks the dispatch against the path, not the shader.

`marking_paint.gdshader` is shared with the box junctions and the stop lines (`Q71`), so the colour
here is the whole difference between this layer and the yellow one.

- `paint_colour`, `paint_roughness`: deliberate duplicates of `road_markings.tres`'s `line_colour`
  and `paint_roughness` (`Q53` keeps marking colours out of `hong_kong.yaml`'s `materials:`). Godot
  cannot share a value between two `.tres`; change both together.
- `paint_night_glow` 0.6 (`Q160`): the paint burns its own colour at this strength times the rig's
  `night_lights`, 0 by day. One value across `road_markings.tres`, `roadmarks.tres`, `arrows.tres`
  and `boxjunctions.tres`.
- No `paint_opacity`: an arrow is a second surface above the road, so opacity would be
  transparency and a sorted alpha pass.
- No fade: an arrow is a whole object, and those over a junction cap are drawn on purpose.
