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

- **`basemap.py`, the `basemap:` block or `buildings.sink_sea`: the pipeline end to end on both
  regions (the stage runs BEFORE `buildings` — the tile stage reads its `water`), `check.sh`
  (`verify_water` holds the plane flat at `water_level_m`), and the two numbers below re-measured
  and pasted.** ⚠️ **`--from buildings` is not enough** for a `basemap` change: the sink reads the
  document the previous run wrote.
- 🔴 **The two numbers** (`Q140`): the share of the sea's ground above `water_level_m` and the share
  of the land within 12 m of the shore under it, sampled at 4 m on the shipped LOD0 tiles
  (`HeightField.from_meshes` over every tile, `shapely.contains_xy` against the union of
  `basemap.json`'s `water`). Wan Chai after the sink: **2.1%** and **10.1%**, both the slopes of the
  triangles straddling the shoreline. The sheets' terrain over the harbour is **1.1–4.2 m** and the
  shore band **2.7–4.9 m**, so 🚫 **no plane laid over the ground as published meets the
  shoreline** — measured at 2.5, 3.0 and 3.5 m before the sink was built; do not re-propose one.
- **`water_level_m` is a fact, not a dial**: mean sea level +1.3 mPD, game y = 0 the Principal
  Datum. `seabed_m` is the dial, and the price of a deeper one is a longer beach, not a wall.
- **`water.tres` or `materials.sea_water`**: a frame from the `ground` viewpoint
  (`--camera=400,45,300 --look=250,0,60`) and the skyline (`Q27`), both `--debug-view=off
  --hud=off`. 🔴 The albedo is *diffuse* (5–12%) and the blue is the sky off the roughness — lighten
  the material and `_check_reflectance` refuses it; the dial is `roughness_value` (0.45 ships; 0.15 read as a near-white mirror of the haze). `sea_water`
  sits in `materials:` under `Q33`, so the `facade` rule's one-commit clause applies.
- **`water.gdshader`**: a shader change owes a render and `grep -i "shader error"` on the check and
  the run (CLAUDE.md), plus TWO frames at different sim times diffed — a wave that does not move
  renders perfectly. `NORMAL` in the fragment is VIEW space: a world normal goes through
  `VIEW_MATRIX` first, or the waves swim with the camera. Own shader, never a change to
  `vertex_albedo.gdshader`.
- **A frame's `water` extent moves with `reach_m` and the fetched sheets** — a reach past the fetch
  is refused at load, and a missing sheet would read as open sea. `hud` owns the minimap's half.
- ⚠️ **Water is not a floor.** No collider; a car that leaves the quay lands on the sunk ground
  under the plane and `drive_harness.gd` pulls it out (`drown_depth_m`, judged against
  `water_level_m` AND the sea's plan — the tunnel approach is under sea level on dry road). The
  evidence is a drive: full throttle from the start line is in the harbour at ~7 s
  (`--seconds=12 --hold=accelerate@0.5+11.5`), and the `in the harbour` line names the edge.
