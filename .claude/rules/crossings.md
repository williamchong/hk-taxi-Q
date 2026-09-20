---
paths:
  - "etl/pipeline/crossings.py"
  - "etl/pipeline/config_blocks/crossings.py"
  - "etl/tests/test_crossings.py"
  - "game/tools/verify_crossings.gd"
---

# Pedestrian crossings — before marking work done

- **`pipeline/crossings.py`, the `crossings` config block, or any crossing stripe: paste
  `crossings.json`'s three partitions (`features`, `candidates`, `faces`), `drawn_by_kind`,
  `stripes_by_kind`, `refused_m_by_type`, `zigzag_gap_m`, `faces_touching`, `unclosed_m`,
  `vertices_over_void` and `inverted`, before and after, both regions — and run
  `tools/paint_clearance.py --layer crossings` and paste its table.** `tools/battery.py crossings`
  runs both. 🔴 **A stripe is a FACE of a feature's lines, never a ring**: TD surveys most stripes
  as closed rectangles and the rest as four loose edges (777 m of Wan Chai's 999 m of open line close
  into 84 more stripes), so the stage polygonises each feature and draws what is enclosed.
  🔴 **`faces_touching` must be 0**: a ladder — two rails and their rungs — polygonises its GAPS
  too and paints the crossing solid, and renders perfectly. The survey draws none (the gap between
  neighbours is the sheet's 0.6 m); `test_a_ladder_is_seen` is what says so if it starts.
  🔴 **The colour is not published on the crossing.** `LINETYPE` has no domain in the data
  dictionary and every value carries the same 0.6 m stripe — `RM1076` included, whose sheet width
  is 250-350 — so it does not separate a zebra (`RM1070`, white) from a light-signal crossing
  (`RM1076`, yellow). A zebra is never painted without its zigzags, which TD surveys as
  `ZIGZAGL` / `ZIGZAGR` in `DTAD_RD_MARK_LINE_C`: a crossing they reach is white, every other is
  yellow. ⚠️ **`zebra.within_m` sits on a plateau — 0.3 m to the one zebra, 197 m to the next
  crossing — and `zigzag_gap_m` publishes both sides of it every build.** The two closing on each
  other is the rule failing; do not move the bar to fix a colour.
  ⚠️ **`line_types` is an exact whitelist matched case-folded** (`SOLID` and `Solid` are one thing).
  What it omits is refused and counted by code, and three of those must stay out:
  `CROSS_BOUNDARY` is the whole crossing's outline and would paint it solid, `CROSS_ANNO` is a
  label, `RM1077` is slow-down bars. A new region's new code shows up in `refused_m_by_type`.
  ⚠️ **No dimension is authored**: width, length and spacing are the survey's. `max_stripe_width_m`
  is twice the sheet's 700 and nothing stands near it (widest stripe 0.814 m over 2,321 faces in
  four regions; narrowest non-stripe 2.06).
  ⚠️ **The two paints are the box junctions' and the road marks' own `.tres`**, on purpose — one
  paint, one dial — so `verify_crossings.gd` checks the material PER KIND: a kind handed the
  other's is a yellow zebra that renders perfectly. `KIND_MATERIALS` there, `SHADERS` in
  `generated_scene_import.gd` and `KINDS` in `crossings.py` move together.
  ⚠️ **`lift_m` 0.010 is the LOWEST rung** (boxes 0.012 / 0.014, arrows 0.015, road marks 0.016): a
  crossing legitimately overlaps none of them, and where registration puts a stop line on a stripe
  the narrow mark must stay visible. 🔴 Do not answer a burial by raising it (`boxjunctions` rule).
  ⚠️ **`_place` is `boxjunctions._place`, imported**, so `CrossingReport` carries that function's
  counters by name and its three tripwires (`vertices_over_cap`, `vertices_over_void`,
  `polygons_split`) mean here what they mean there.
  🚫 **Not this stage's**: the look-right / look-left glyphs (`1135` / `1136` in
  `DTAD_RD_MARK_SYM_PT` — bare digits, `SYMBOL_SIZE` nan on 203 of 256, so an authored glyph), and
  the three footway-extent publishers, which are `P3-27`'s other half. 🚫 **Nothing here may depend
  on signals** (`Q77`). Numbers in `P3-35g2`'s record.
