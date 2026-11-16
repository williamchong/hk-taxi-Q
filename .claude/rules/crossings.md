---
paths:
  - "etl/pipeline/crossings.py"
  - "etl/pipeline/config_blocks/crossings.py"
  - "etl/tests/test_crossings.py"
  - "game/tools/verify_crossings.gd"
---

# Pedestrian crossings — before marking work done

- **`pipeline/crossings.py`, the `crossings` block, any stripe**: `tools/battery.py crossings
  --region <r> --before <root>`, both regions. From `crossings.json` compare the three partitions
  (`features`, `candidates`, `faces`), `drawn_by_kind`, `stripes_by_kind`, `refused_m_by_type`,
  `zigzag_gap_m`, `faces_touching`, `unclosed_m`, `vertices_over_void`, `inverted`, and paste
  `paint_clearance.py --layer crossings`'s table.
- A stripe is a face of a feature's polygonised lines, never a ring: TD surveys some stripes as
  four loose edges. `faces_touching` must be 0 — a ladder polygonises its gaps and paints the
  crossing solid (`test_a_ladder_is_seen`).
- The colour is not published. A crossing its zigzags (`ZIGZAGL`/`ZIGZAGR`) reach is a white zebra;
  every other is yellow. `zebra.within_m` sits on a plateau (0.3 m to the one zebra, 197 m to the
  next crossing) and `zigzag_gap_m` publishes both sides. The two closing is the rule failing; do
  not move the bar to fix a colour.
- `line_types` is an exact whitelist, case-folded. `CROSS_BOUNDARY` (the outline, would paint it
  solid), `CROSS_ANNO` (a label) and `RM1077` (slow-down bars) stay out. A new region's code shows
  in `refused_m_by_type`.
- No dimension is authored. `max_stripe_width_m` is twice the sheet's 700 mm; widest stripe 0.814 m,
  narrowest non-stripe 2.06 m.
- The two paints are the box junctions' and road marks' own `.tres`, so `verify_crossings.gd`
  checks the material per kind. `KIND_MATERIALS` there, `SHADERS` in `generated_scene_import.gd`
  and `KINDS` in `crossings.py` move together. Meshes are `<kind>_c<i>_r<j>` per 300 m cell
  (`cell_m`, `Q135`); the verifier reads the kind off the name.
- `lift_m` 0.010 is the lowest paint rung, so a stop line over a stripe stays visible. A burial is
  never answered by raising it (`boxjunctions` rule). `_place` is `boxjunctions._place`, imported,
  with its tripwires (`vertices_over_cap`, `vertices_over_void`, `polygons_split`).
- Not this stage's: the look-right/left glyphs (`1135`/`1136`), the footway-extent publishers
  (`P3-27`). The stage reads no signal data.
