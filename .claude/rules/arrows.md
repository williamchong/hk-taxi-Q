---
paths:
  - "etl/pipeline/config_blocks/arrows.py"
  - "etl/pipeline/arrows.py"
  - "etl/tests/test_arrows.py"
  - "game/tools/verify_arrows.gd"
  - "game/tuning/arrows.{tres,md}"
  - "game/assets/shaders/marking_paint.gdshader"
---

# Turn arrows — before marking work done

The stage grades itself: every failure renders as a well-drawn arrow or as nothing.

- **Any change to `pipeline/arrows.py` or the `arrows` block**: `tools/battery.py arrows --region <r>
  --before <root>`, both regions. From `arrows.json` compare the two partitions (`symbols`,
  `candidates`), `axis_residual_deg`, `offset_m`, `against_one_way`, `stacked_pairs`,
  `stacked_disagreeing`, `lane_shift_m`, `outside_carriageway`, `inverted`, `overlapping_drawn`,
  `placed_by_slot`, `fallback_shift_m`, `ends_off_drawn_road`, `pitch_deg`, the `deck` block, and
  `paint_clearance.py --layer arrows`'s "deeper than" line (reported, never gated).
- **Placement** (`Q134`): an arrow stands where TD surveyed it; the lane slot is the fallback and
  the instrument. Do not restore the snap. `_placed_offset` gates on the drawn road
  (`DrawnSurface.covers`), never the host's share (`Q57`). The slot counters (`stacked_*`,
  `lane_shift_m`) must not move across a placement change. Mutations that must fail: always-slot,
  no-fallback, `on_drawn_road` ignored.
- **Heights** (`Q135`): `_end_heights` reads the drawn road under tail and nose, the host
  centreline only for an end over nothing drawn. An end over void is not refused on the street
  (`Q54`). Mutations: centreline returned unread, `covers` not asked.
- **Deck arrows** (`deck_codes`, `stand_on_decks`): see the `roadmarks` rule's deck bullet.
- **Library** (`Q115`): `arrows.glb` is one flat glyph per `RM` code; the city is
  `arrows_placements.json`, so a byte-identical `.glb` proves nothing about placement.
  `pitch_deg` composes before the bearing in the mesh's own frame on both sides
  (`placed_positions`, `GeneratedPlacements.placement_of`); `Basis.rotated` is the wrong call.
  `inverted` is asked of the stood copies.
- **Lane snap** (`Q96`): the slot denominator is the surveyed `width_m`, never
  `lanes x lane_width_m`. At `lanes == 2` the snap is `sign(offset_m)`, so an inert width change
  is expected. `outside_carriageway` (surveyed frame) is not `outside_drawn_ribbon`.
- **Counters**: distributions publish p90/p99/max, not a median. `axis_residual_deg` is recorded
  over refusals too (`n` > `drawn`, `Q58`). `inverted` must be 0 (`cull_back`). The ETL and engine
  winding tests have opposite signs on purpose (`ARCHITECTURE.md`, "Drawn layers").
- **`stacked_disagreeing`** (two instructions in one slot) is a finding about the lane count,
  never a bar to retune; nothing is de-duplicated (`Q54`). Mutation-check it.
- **The row as a lane-count source** (`Q94`, `Q130`): a row of one arrow is not a row — refused,
  never floored. A row resolves ambiguous TPDM brackets only; on an authored width it raises the
  count as `arrows_unmeasured`. The clustering duplicates `carriageway`'s by necessity (no import
  path); `lanes_row_disagreement` grades it.
- **Glyph table or dimensions**: a `DATA_SOURCES.md` change. Codes and lengths come from TD drawing
  `CT174/51-5(1)F`, a scan; `RM1116`–`RM1119` are warning arrows. The sheet is drawn to proportion
  (`RM1016` reads 2.802 against 2.800). The ahead head and stem taper are measured; the turn
  branch is authored (`Q93`). `test_no_head_overlaps_the_stem_it_grows_from` is the ratchet.
- **Shader**: `marking_paint.gdshader` is shared with the boxes, road marks and crossings (`Q71`).
  Render all and `grep -i "shader error"`. `check_shader_material` compares each material's
  `resource_path`; do not swap in `check_shader_source`.
