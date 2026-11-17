---
paths:
  - "etl/pipeline/stopmarks.py"
  - "etl/pipeline/config_blocks/stopmarks.py"
  - "etl/tests/test_stopmarks.py"
  - "game/tools/verify_stopmarks.gd"
---

# Bus stop, stand and tram stop paint — before marking work done

`P3-89`, `P3-91`, `Q242`. The shape is `crossings.py`'s: surveyed paint drawn where surveyed, each
vertex on the drawn road (`boxjunctions._place`, imported, with its tripwires).

- **`pipeline/stopmarks.py`, the `stop_marks` block, any stop or stand paint**: `tools/battery.py
  stopmarks --region <r> --before <root>`, both regions. From `stopmarks.json` compare the three
  partitions (`features`, `symbols`, `candidates + symbols_stood`), `duplicates`, `drawn_by_id`,
  `drawn_from_symbols_by_id`, `paint_m_by_kind`, `off_road_m_by_id`, `glyph_from`, `glyph_fit_m`,
  `glyph_turn_deg`, `inverted`, and paste `paint_clearance.py --layer stopmarks`'s table.
- **Boxes are lines at the sheet's width and module** (`CT174/51-5(1)F`): `RM1048` 100 mm, 1 m
  white / 1 m bare; `RM1049` 100 mm, 1 m yellow / 1 m white; `RM1045` 300 mm yellow. The module
  runs through a corner. A dimension change is a `DATA_SOURCES.md` change.
- **A legend is strokes, drawn where surveyed** (`DTAD_RD_MARK_SYM_LINE`: `1047`, `1175`, `1176`).
  `legend_stroke_m` is the one authored dimension: TD publishes a letter height and no stroke
  width. `P3-21`'s no-go was `DTAD_RD_MARK_ANNO`'s rectangles and still stands.
- **A legend filed as a point is stood with the region's own stroke legends as its glyph**
  (`glyph_of`, `stand_symbols`). TD files a legend one way or the other, never both (0 of 1,205
  `1047` points citywide lie inside a stroke legend), so nothing calibrates the point against the
  strokes: the point is taken for the legend's middle, `arrows.py`'s reading. The one check there
  is: the three `1175` points sit 0.7–0.8 m inside the kerb and the stroke legends' middles 0.9 m,
  where an edge anchor would differ by the legend's half width, 1.3 m.
  - `glyph_fit_m` p50 is millimetres (one CAD cell); its tail is a second spacing under the same
    stroke layout, which the median ignores. A p50 in decimetres is the frame failing.
  - `glyph_turn_deg` is how far the traffic's heading is from each legend's own; its tail is a
    legend read against the wrong flow.
  - `turn_deg` is measured: `1047`'s `ANGLE` reads with the flow (43 of 45 within 3 deg), `1175` /
    `1176`'s a quarter turn off it (5 of 5 at 88–91). Re-measure on a new region before trusting it.
  - `1047 (n*` / `(w*` (other sizes), `1048` and `1149` points are refused by code, not stood.
- **A marking belongs to the region its middle is in** (`other_region`): never cut at the seam,
  never drawn twice.
- **`duplicates`**: TD files 44 of 113 `RM1049` twice, vertex for vertex. Drawn once.
- **A piece over nothing drawn is refused** (`off_road_m_by_id`), a feature only when every piece
  is (`off_road`). The stand boxes' are their returns to the kerb (0.1–0.8 m); the tram stop line
  is on the tram reserve, off the ribbon (`Q58`). Do not answer either by widening.
- The two paints are the road marks' and the box junctions' own `.tres`. `KIND_MATERIALS` in
  `verify_stopmarks.gd`, `SHADERS` in `generated_scene_import.gd` and `KINDS` in `stopmarks.py`
  move together. `marking_paint.gdshader` is shared: render and `grep -i "shader error"`.
- `lift_m` 0.013 sits between the boxes' 0.012 and the arrows' 0.015. A burial is never answered by
  raising it (`boxjunctions` rule).
