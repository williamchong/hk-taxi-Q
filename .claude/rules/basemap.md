---
paths:
  - "etl/pipeline/basemap.py"
  - "etl/pipeline/shore.py"
  - "etl/tests/test_shore.py"
  - "game/tuning/harbour_land.{tres,md}"
  - "etl/pipeline/config_blocks/basemap.py"
  - "etl/tests/test_basemap.py"
  - "game/tuning/water.{tres,md}"
  - "game/assets/shaders/water.gdshader"
  - "game/tools/verify_water.gd"
  - "game/scripts/city/generated_basemap.gd"
---

# The harbour — the basemap and the water plane — before marking work done

- **`basemap.py`, the `basemap:` block or `shore.cut_sea`**: pipeline end to end on both
  regions (`basemap` runs before `buildings`; `--from buildings` is not enough), `check.sh`
  (`verify_water` holds the plane at `water_level_m`), and re-measure the two numbers (`Q140`): the
  share of sea ground above `water_level_m`, and of land within 12 m of the shore under it, sampled
  at 4 m on the LOD0 tiles (the highest ground over each point) against `basemap.json`'s `water`.
  Wan Chai: 0.0% and 9.6% since the cut (`Q250`); 1.7% and 17.8% before it on the same instrument.
  ⚠️ The 9.6% is the sheets' own terrain at 1.1 m in inlets narrower than `seal_m`, which the sea
  polygon closes: a cut cannot raise it.
- Measured shut (`Q140`): no plane laid over the ground as published meets the shoreline — harbour
  terrain is 1.1–4.2 m and the shore band 2.7–4.9 m; tried at 2.5, 3.0 and 3.5 m. Hence the sink.
- **The quay** (`shore.py`, `Q250`): the decimated ground is cut along the sea polygon's edge after
  `collapse` (`Q25`), per cell size. Land keeps the terrain to the line, the sea drops to
  `seabed_m`, and where the nearer published line is one of `shoreline.hard_types` a vertical face
  in `quay_material` joins them; a high-water mark slopes from the line. Owed on a change:
  `ground_shore_m` / `ground_quay_m` / `ground_quay_triangles` from each buildings manifest, the
  `tiles` rule's collider offset (GROUND reads 0.000 m) and the drive below.
  - Hard or soft is read per point by position, never per triangle: that is what keeps the cut
    closed where a wall meets a slope.
  - A cut point takes its colour and UV payloads whole from the nearest corner. Blended, it stops
    being ground to `trees.tile_corners` and every layer that stands on the ground loses it there.
  - The cut loses no plan area (2,088,688.5 m² before and after on Wan Chai's 4 m ground).
  - A ground row's box is grown to hold the cut's vertices (`buildings._hold`); without it
    `verify_tiles.gd` fails on a point cut into a triangle that spans two sheets.
- **The land outside the tiles** (`land_of`, `land_mesh`): the frame's land within `land_within_m`
  of the sea that no declared region's box holds, a second mesh in `water.glb` on
  `harbour_land.tres`. Flat at `land_level_m`, a face under every sea edge — a natural shore's
  too, since no terrain is read out there. `verify_water.gd` holds it over the water and its face
  under it. ⚠️ It is cut from `simplified(sea)`, the outline the water is drawn to; cut from the
  raw sea it leaves slivers. ⚠️ A declared region that is not installed leaves a hole.
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
- `water.gdshader` also draws the far sea (`backdrop.glb`, vertices with `COLOR_0` alpha 0) past
  the far plane, and `basemap.read_sea` feeds it: a change to either owes the `backdrop` rule.
- The `water` extent moves with `reach_m` and the fetched sheets; a missing sheet reads as open sea.
  `hud` owns the minimap half.
- Water is not a floor: no collider. A car off the quay lands on the sunk ground and
  `drive_level.gd` pulls it out (`drown_depth_m`, judged against `water_level_m` and the sea's
  plan). Evidence is a drive: `--seconds=12 --hold=accelerate@0.5+11.5` from the start line.
