---
paths:
  - "etl/pipeline/basemap.py"
  - "etl/pipeline/config_blocks/basemap.py"
  - "etl/tests/test_basemap.py"
  - "game/tuning/water.{tres,md}"
  - "game/assets/shaders/water.gdshader"
  - "game/tools/verify_water.gd"
  - "game/scripts/city/generated_basemap.gd"
---

# The harbour — the basemap and the water plane — before marking work done

- **`basemap.py`, the `basemap:` block or `buildings.sink_sea`**: pipeline end to end on both
  regions (`basemap` runs before `buildings`; `--from buildings` is not enough), `check.sh`
  (`verify_water` holds the plane at `water_level_m`), and re-measure the two numbers (`Q140`): the
  share of sea ground above `water_level_m`, and of land within 12 m of the shore under it, sampled
  at 4 m on the LOD0 tiles against `basemap.json`'s `water`. Wan Chai: 2.1% and 10.1%.
- Measured shut (`Q140`): no plane laid over the ground as published meets the shoreline — harbour
  terrain is 1.1–4.2 m and the shore band 2.7–4.9 m; tried at 2.5, 3.0 and 3.5 m. Hence the sink.
- **`water_level_m` is a fact** (mean sea level +1.3 mPD). `seabed_m` is the dial; deeper costs a
  longer beach.
- **`buildings.paint_parks`, `park_material`, `materials.park_grass`** (`Q144`): pipeline on both
  regions, `ground_park_vertices` from each buildings manifest (zero with parks in frame is a
  stage-order failure), and a frame over Victoria Park (`--debug-view=off --hud=off`). The edge
  fades over one ground triangle, so a long decimated triangle draws a green streak. Every
  open-space code is painted, paved ones included (user's call). Re-colouring owes the `facade`
  rule's one-commit clause (`Q33`).
- **`water.tres`, `materials.sea_water`**: frames from `--camera=400,45,300 --look=250,0,60` and
  the skyline (`Q27`), `--debug-view=off --hud=off`. The albedo is diffuse (5–12%);
  `_check_reflectance` refuses a lighter one. The dial is `roughness_value` (0.45; 0.15 read as a
  near-white mirror). `facade`'s one-commit clause applies.
- **`water.gdshader`**: render, `grep -i "shader error"`, and diff two frames at different sim
  times (a wave that does not move renders perfectly). `NORMAL` in the fragment is view space; a
  world normal goes through `VIEW_MATRIX`. Its own shader, never `vertex_albedo.gdshader`.
- The `water` extent moves with `reach_m` and the fetched sheets; a missing sheet reads as open sea.
  `hud` owns the minimap half.
- Water is not a floor: no collider. A car off the quay lands on the sunk ground and
  `drive_level.gd` pulls it out (`drown_depth_m`, judged against `water_level_m` and the sea's
  plan). Evidence is a drive: `--seconds=12 --hold=accelerate@0.5+11.5` from the start line.
