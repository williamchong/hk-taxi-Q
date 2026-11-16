---
paths:
  - "etl/pipeline/config_blocks/roadmarks.py"
  - "etl/pipeline/drawnsurface.py"
  - "etl/pipeline/roadmarks.py"
  - "etl/tests/test_roadmarks.py"
  - "game/assets/shaders/marking_paint.gdshader"
---

# Road markings: white lines, stop lines and the inferred join — before marking work done

The stage grades itself. `tools/battery.py roadmarks --region <r> --before <root>` runs the report
and `paint_clearance.py --layer roadmarks`; run it for every bullet below, both regions.

- **Any change**: compare `roadmarks.json`'s two partitions, `drawn_by_id` / `drawn_m_by_id`,
  `host_disagreement` with `host_considered`, `host_off_carriageway`, `no_host_on_axis`,
  `axis_residual_deg`, `underfill_m`, `inverted`, `slivers_dropped`, `stations_on_drawn_structure`
  / `on_drawn_structure_m`, and the `join` and `deck` blocks.
  - `host_disagreement` is the load-bearing counter (transverse pick against nearest edge); a
    fall towards zero means the pick stopped picking (`Q69`). `axis_residual_deg` grades a rule
    that optimises it, and is recorded over refusals too (`n` > `drawn`, `Q58`).
  - `inverted` must be 0 (`cull_back`); ETL and engine winding tests have opposite signs (`Q59`).
  - `underfill_m` is transverse-only, against the drawn half-width, never the graph's `width_m`.
  - `height_spread_m` is not a burial signal; `paint_clearance` is.
  - A station over nothing drawn at level 0 and under a drawn deck is refused and counted
    (`covers(toward=)`); a void station with nothing over it is kept (`Q54`). Mutation-check the
    second half. Use `levels_drawn`, never `elevation_levels`.
  - Dimensions are transcribed from TD drawing `CT174/51-5(1)F` (a scan): a change is a
    `DATA_SOURCES.md` change. `LINES SPACING` is the clear gap, not a pitch.
  - Markings are clipped to the region (`roads.clip`); the clip moves stop lines too.
  - `marking_paint.gdshader` is shared with arrows, boxes and crossings (`Q71`): render all and
    `grep -i "shader error"`.
- **Cells** (`road_marks.cell_m`, `meshbuild.CellBuilder`, `Q135`): paste `cells`,
  `cell_triangles_max`, `bytes`, and the drive's `prims` / `draws` with and without
  `--hide-layers=roadmarks`, from the start line and `--spawn-fare=wan_chai/f_045`. Inertness: the
  cells' triangles equal the uncut mesh's as a multiset. `slivers_dropped` is summed over cells.
- **Decks** (`deck_codes`, `draw_decks`, `_place_on_deck`, `arrows.stand_on_decks`, `Q134`): a deck
  marking is hosted among off-grade edges only and stood on `DrawnSurface.of(level=)`; no deck
  knob. The void rule is inverted on purpose: past a rim is air, so an uncovered piece is refused
  (`stations_off_deck`, arrows' `off_deck`). Inertness: the level-0 report byte-identical and
  level-0 geometry an identical prefix of each cell / the stands. `deck.under_another_deck` is a
  finding; no rule picks the deck. Not built: `A03`, the bores (`Q21`), an inferred join
  off-grade, a slot fallback for deck arrows. Re-import before a frame.
- **White lines along a road** (`more_layers`, `marks:` rows, `broken_line`, `divides_flows`,
  `transverse_host`'s `on` preference; `Q132`):
  - Measured shut: `draw_lane_lines` and `draw_centre_line` stay 0.0 — where TD surveys no line,
    none is drawn. Silent streets have nothing within 1.5 m of the middle on 94% / 84% of
    stations. `draw_bus_lane` is 0.0 too: the line is TD's `RM1006` / `RM1007` (`Q192`).
  - TD files one family across sister layers (`DTAD_RD_MARK_LINE`, `DTAD_RD_MARK_LINE_C`); a code
    missing from one layer is not missing.
  - `broken_line` is an instruction: `RM1002` breaks the right line and `RM1003` the left, of the
    part's digitised direction (`test_the_broken_line_is_on_its_own_side`). No frame or counter
    sees a wrong side.
  - A longitudinal line is hosted by a road it lies on, then by angle. Transverse rows and
    `underfill_m` stay byte-identical across a change here.
  - `divides_flows` is what the inferred join yields to; a lane line never carries it.
- **`RoadMark.axis`, `longitudinal_legibility_scale`, `_on_its_own_carriageway`** (`Q118`):
  - The axis selects the host rule and has no default: a wrong axis draws nothing with every
    partition closing. One shared `bearing_tolerance_deg`.
  - `_on_its_own_carriageway` refuses at the host's drawn half-width and is longitudinal-only.
  - Measured shut: a longitudinal mark is not sampled from its host's own edge — 8.58% buried,
    because a 236 m line spans several edges.
  - `marks:` dimensions are transcribed; legibility is `longitudinal_legibility_scale` alone,
    which scales the gap with the lines.
- **`axis: oblique`, `chevron_width_m` / `chevron_turn_deg`, `_apex`, hatching** (`P3-35g3`): also
  paste `host_off_carriageway_m_by_id`, `chevrons`, `chevron_m`, `chevron_turn_gap_deg`.
  - An oblique mark is hosted by proximity with the lies-on preference and carries no residual:
    `axis_residual_deg` must come out unchanged, `n` included.
  - `RM1035`/`RM1036` carry two widths: a chevron is a 3-vertex V. `chevron_turn_gap_deg` closing
    on `chevron_turn_deg` is the rule failing; do not move the bar. Two-leg chevrons draw at
    outline width; do not guess (`Q54`).
  - Mutation: `test_an_oblique_marking_prefers_the_road_wide_enough_to_hold_it`.
- **`opposed_join_mark`, `opposed_joins`, `_covered`, `draw_opposed_joins`, `surface.py`'s
  `opposed_pairs`** (`Q125`): paste the `join` block and mutation-check the cut by disabling it.
  - The one inferred placement: the line between two one-way carriageways wherever TD surveyed no
    `RM1001`. `covered_m` is the counter that can fail. The join is counted apart from `drawn`
    and `drawn_by_id`, which stay byte-identical.
  - Measured shut: `draw_pair_join` stays off — a shader yields per edge, 24 of 95 pairs are only
    partly surveyed, and its line is 28 cm against the survey's 15.
  - No new knob: the pairing's reach is the drawn width plus one `style.kerb_width_m`; sweep it.
    `centre_step` and `roads.glb` must not move. `_opposed_gaps` also owes the `surface` rule.
