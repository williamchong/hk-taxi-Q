---
paths:
  - "etl/pipeline/roadtext.py"
  - "etl/pipeline/config_blocks/roadtext.py"
  - "etl/tests/test_roadtext.py"
  - "game/tools/verify_roadtext.gd"
---

# Road lettering — before marking work done

`P3-21`, `Q262`. TD's `DTAD_RD_MARK_ANNO` strings (`CENTRAL 中區`, `BEWARE OF PED 小心行人`) laid
into their filed rectangles in Noto Sans HK. The shape is `stopmarks.py`'s: each triangle on the
drawn road through `boxjunctions._place`, refused over nothing drawn.

- **Any change**: `tools/battery.py roadtext --region <r> --before <root>`, both regions. From
  `roadtext.json` compare the two partitions (`features`; `candidates + deck_candidates`),
  `drawn_by_text`, `characters_drawn`, `axis_residual_deg`, `letter_height_m`, `off_road_m2`,
  `inverted` (must be 0), `triangles`, `bytes`, and paste `paint_clearance.py --layer roadtext`.
- **The facing is the traffic's, never TD's `Angle`** (`facing`). `FlipAngle` 90 turns the
  drawing's text upright, so `Angle` fixes the axis only. Mutation-check by flipping the sense test
  in `facing`: three `TestTheFacing` cases must fail. Mirroring (`laid`'s `across`) is held by
  `test_the_letters_read_left_to_right_for_the_driver`; a frame cannot be trusted to show it.
- **`off_axis` is a refusal, not a re-host.** A legend at a junction mouth snaps to the crossing
  road (Wan Chai's 10: one `中區 / TRAL / 香港仔 / 北角` group, one `巴士線 BUS LANE`). Picking the
  aligned road instead is a second host rule on `Segments`; not built.
- **`sliver_m` is authored, never 2 × `import_quantum_m`**: a stroke of a letter squeezed 0.4 m wide
  is ~5 cm, and the 4.5 cm bar dropped 24% of the pieces as holes in the letters. At 0 `split`
  cuts mm slivers onto a cap's near-vertical facets (the tunnel portal) and 74 triangles fail
  `check_faces_up`. 0.015 m: 0 fail in both regions (0.01 left 1), 0.13% of the area against
  0.01. The bar is measured, not derived: a change to the layout or the face re-sweeps it against
  `verify_roadtext`.
- **The face** (`font_source`, `font_weight`, `flatten_em`): a change re-renders the letters, so
  it owes a frame from the chase camera, the user's pick, and the `triangles` / `bytes` diff.
  `flatten_em` barely moves the count (0.01 → 0.02: 33.5k → 31.7k in Wan Chai): the outlines are
  mostly chords already. The fill is non-zero by winding (`_filled`); even-odd punches holes where
  a variable font's strokes overlap (`test_overlapping_strokes_fill_by_winding_not_even_odd`).
- **`glyph_missing` must be 0**, or a region's string has a character the face lacks:
  `missing_characters` names it. The face is the whole fetched font, not the interface's subset.
- **`refused`** holds drafting notes, matched after the markup is stripped, lines joined by `\n`.
  A string added there needs where it stands and why it is not paint.
- The material is `roadmarks.tres` through `roadtext_white`: no shader of its own, so a change
  here owes no shader render. A change to `marking_paint.gdshader` owes this layer's frame too.
