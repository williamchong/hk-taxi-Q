# roadmarks.tres

The paint of the road marks drawn as geometry (`P3-23`, `Q53`). `tools/generated_scene_import.gd`
maps the ETL's `roadmarks` and `crossings_zebra` (zebra stripes, `P3-35g2`) material names to this
file. `stopmarks_white` (`P3-89`) and `roadtext_white` (`P3-21`) take it too. `verify_roadmarks.gd` and `verify_crossings.gd` check the dispatch by path, because
`marking_paint.gdshader` is shared with `arrows.tres` and `boxjunctions.tres` (`Q71`).

Dimensions and dash modules are not here. They are geometry from `hong_kong.yaml`'s `road_marks:`
block, transcribed from TD's `CT174/51-5(1)F`.

- `paint_colour = (0.91, 0.91, 0.87)`: the marking white. Authored in five places on purpose
  (`Q53` keeps paint out of `materials:` and `Q33`'s exposure rule): `road_markings.gdshader`'s
  `line_colour` default, `road_markings.tres`, `marking_paint.gdshader`'s default, `arrows.tres`
  and here. Nothing shares a value between `.tres` files; a mismatch shows in one frame, most of
  all where a stop line meets its lane lines. Change all five together.
- `paint_roughness = 0.7`: `road_markings.tres`'s.
- No `paint_opacity`: on a lifted second surface it would be transparency, not asphalt showing
  through.
- `paint_night_glow = 0.6`: see `road_markings.md`; one value across the four paint materials.
