---
paths:
  - "etl/pipeline/direction_signs.py"
  - "etl/pipeline/config_blocks/direction_signs.py"
  - "etl/tests/test_direction_signs.py"
  - "game/tools/verify_direction_signs.gd"
  - "game/tuning/direction_signs_face.{tres,md}"
---

# Direction signs — before marking work done

`P3-105`, `Q265`. TD's overhead direction signs: each gantry board's face filled from
`DTAD_DS_PLATE_LINE`'s line-work into an atlas, hung on its `GS` beam from `DTAD_DS_POLE_LINE_C`
where its `Leader Line` says, over the road it signs. The steel is authored; its place is not.

- Rerun `python -m pipeline.direction_signs` on both regions and read its line: `read`, `drawn`
  and the refusals (`no_leader`, `no_beam`, `off_road`, `no_panel`, `under_deck`, `no_footing`),
  `cleared`, `legs`, `cantilevers`. Wan Chai: 18 read, 9 drawn (5 no leader, 3 off road, 1 under
  a deck), 3 cleared ≤ 0.6 m, 15 legs, 3 cantilevers. Causeway Bay: 1 read, 0 drawn (no leader).
- 🔴 **`facing_away` is 0**, and a face's normal is its board's
  (`test_every_face_is_wound_the_way_it_is_lit`).
- 🔴 **The words are TD's line-work, never a string we set.** No font, no OCR, no wording edited
  to match Street View: the user's call is to ship TD's drawing as published, stale or not.
- **Look at the atlas** (`etl/out/<region>/direction_signs_text.png`) after any change to the fill:
  the Chinese must read solid, the English as strokes with open counters, and every top plate
  (G26A's "Harbour Road", "North Point") must be present. A missing plate is `_faces` fed un-noded
  lines.
- **Frame three gantries** in `city_preview.tscn`: G57A (the user's Street View; camera
  `828,7.6,335` → `779,8.6,361`), G27A (`689,7.9,397` → `732,8.9,363`) and G26A in front of its
  footbridge (`431,7.5,477` → `486,8.5,468`). A board poking through a deck is `deck_depth_m` or
  the clear rule.
- `wider_than_beam` > 0 is not a failure: 4 of 9 Wan Chai boards are drawn wider than the GS line
  between their legs. It moves if `drawing_units_per_m` (measured on two boards, 4.96) is wrong.
- The atlas budget is `DIRECTION_SIGNS_ATLAS_BUDGET_PX` (2048 × 1024; Wan Chai fills it). More
  boards → a second atlas or a lower `px_per_m`, the user's call; never past WebGL2's 2048 width.
- Battery row: `direction_signs`.
