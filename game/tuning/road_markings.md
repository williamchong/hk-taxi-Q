# road_markings.tres

The road surface's own shader paint (`P3-12`): today only the kerbside double yellows.
`tools/generated_scene_import.gd` maps the ETL's `road_markings` material name to this file. One
resource for the whole region.

## Switches

- `draw_lane_lines = 0.0`, `draw_centre_line = 0.0` (`Q132`, the user's call): where TD surveys no
  line none is drawn. `roadmarks.py` draws TD's `RM1101`–`RM1105` and `RM1002`/`RM1003` as
  geometry. Do not switch back on to fill a silent street: those are surveyed streets with no
  centre line, and an invented line runs through hatching, zigzags and yellow boxes.
- `draw_pair_join = 0.0` (`Q118`, `Q125`): `roadmarks.py` draws the surveyed `RM1001` double line
  and the inferred join as geometry. On here it would be a second line at 28 cm beside the
  survey's 15, and a shader cannot yield for part of an edge.
- `draw_bus_lane = 0.0` (`Q192`, the user's call): `BUS_ONLY_LANE` says a bus lane exists on the
  route, not where its line runs; on Hennessy Road it painted a 0.46 m bar 1.7 m inside the
  traffic lane. `roadmarks.py` draws TD's `RM1006`/`RM1007`. The router still reads the flag off
  the graph.
- `draw_double_yellow = 1.0`: the one marking with no source behind it. Near universal in urban
  Wan Chai, still an invention. The first thing to turn off if a recognition round reports
  markings as wrong.

`line_width`, `centre_width`, `centre_gap`, `bus_width`, `dash_length_m` and `dash_gap_m` reach
nothing while their switches are 0. The lane coordinate, `lanes_painted`, `centre_at` and the
`bus_lane` bit stay in the codec for a region that switches them on.

## Values

- Widths are in U-lanes, not metres, and wider than life: a truthful line is under a pixel at
  driving distance. A U-lane is `2 * half_width / lanes` of the ribbon as drawn, not
  `lane_width_m` (`surface.py::_u_metres`). The `_m` values are V, in real metres.
- `line_colour`, `yellow_colour`: the marking white and yellow, each copied in several files
  (`roadmarks.md` has the ledger).
- `paint_opacity = 0.85`: asphalt showing through paint, mixed into one opaque surface.
- `yellow_inset = 0.09`, `yellow_gap = 0.06`, `yellow_width = 0.035`: the double yellow's place
  and shape at the kerb.
- `centre_gap = 0.0367`: TD's RM1001 clear gap, held at 100/150 of `centre_width`
  (`CT174/51-5(1)F`).
- `fade_m = 6.0`, `fade_softness_m = 3.0`: markings fade out before a junction. A cap overlaps its
  arms (worst 4.21 m, p99 3.62 m), and paint under the overlap reads as a patch, so the fade must
  reach past it; 6 m clears every end. Longer costs short edges their markings: an edge under
  twice the fade carries none (15.2% of edges at 6 m, 21.2% at 9 m). `Q53`.
- `paint_night_glow = 0.6`: paint emits its own colour times the rig's `night_lights` (`Q160`).
  One value across this file, `roadmarks.tres`, `arrows.tres` and `boxjunctions.tres`. 1.5 read
  as sci-fi to the user.
