---
paths:
  - "etl/pipeline/paths.py"
  - "etl/pipeline/config_blocks/paths.py"
  - "etl/tests/test_paths.py"
  - "game/tools/verify_paths.gd"
  - "game/tuning/paths.{tres,md}"
---

# Pedestrian lines — before marking work done

`P3-101`, `Q250`. iB1000 `CartoPedLine` as ribbons on the ground: `PA` pavement margins and `FPW`
wide-footpath edges at 0.3 m, `FP` narrow-footpath centrelines at 1.0 m.

- `tools/battery.py paths`, both regions: `read_m` = `on_road_m` + `in_sea_m` + `no_ground_m` +
  `too_steep_m` + `too_short_m` + `drawn_m`; `triangles`, `stations_kept`. Frames
  (`--debug-view=off --hud=off`): `--camera=700,60,230 --look=700,0,110` (the waterfront),
  `--camera=1700,200,420 --look=1700,0,150` and `--camera=1800,12,260 --look=1650,2,200`
  (Victoria Park, from the air and from the ground).
- Only where a line is surveyed (the trees' rule). Nothing is filled between two lines: the
  publisher draws margins and centrelines, not faces.
- A width is authored; a line has none. `FP` is a centreline (nearest other `FP` line 21 m off at
  the median) and `FPW` an edge (1.85 m off), which is why they differ.
- Not a kerb. The level-0 kerb comes from `CartoTransLine` `RM`, HyD and TD (`carriageway`,
  `region`); a line is cut back `kerb_clear_m` outside the carriageway region and never moves it.
- Not drawn: `PAU` (under a structure, not looked at), `STP`, `CWY`, `FBR`, `FBU`, `SWY` — none
  lies on the ground the tiles draw.
- A ribbon is laid on the LOD0 ground: the centreline and both edges are read every `step_m`, and
  a station is kept at each plan corner and wherever the ground leaves the chord by `sag_m`.
  `sag_m` must stay under `lift_m` (refused at load). ⚠️ Past 250 m the ground under it is LOD1 and
  the ribbon is not re-laid; no frame from the air has shown it.
- `max_grade_pct` breaks a line on ground no path lies on: a retaining wall or a cliff the 4 m
  terrain cell smears into a slope. Without it Causeway Bay drew 60 triangles steeper than 60°.
  It refuses 430 m in Wan Chai and 2,415 m in Causeway Bay.
- Each triangle is wound up on its own: a ribbon wider than its bend's radius folds, and one
  winding for the quad leaves half of it culled. `verify_paths.gd` holds every triangle facing up.
- No collider and no shadow, on the road paint's terms. Counted in `resident_budget.py`'s paint.
- The tone is `materials.path_edging` (35%); the user was shown 25 / 30 / 35 / 40 / 50% and none.
- A `materials:` colour or the basemap's `park_material` moves what counts as ground, as for the
  trees (`tile_corners`), and so does anything that cuts the ground (`shore.cut_sea`).
