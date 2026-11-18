---
paths:
  - "etl/pipeline/backdrop.py"
  - "etl/pipeline/config_blocks/backdrop.py"
  - "etl/tests/test_backdrop.py"
  - "game/tools/verify_backdrop.gd"
  - "game/tuning/backdrop.{tres,md}"
  - "game/assets/shaders/backdrop.gdshader"
  - "game/assets/shaders/far_shore.gdshaderinc"
---

# The far shore — before marking work done

`P3-100`, `Q249`. Kowloon's skyline across the harbour as `backdrop.glb`: iB1000 `Building`
footprints extruded to their published roof, one flat shore slab, and the sea run on to it.

- `tools/battery.py backdrop` (Wan Chai; Causeway Bay ships none and is drawn beside it):
  `blocks_drawn`, `min_height_drawn_m`, the three triangle counts, `gap_m`. Frames:
  `--spawn-at=212,5.6,40 --spawn-facing=212,5,0` (Expo Drive East) by day and at
  `--time-of-day=1.0`, `--hud=off`. Cost: the same drive with `--hide-layers=backdrop`.
- 🔴 **The camera's `far` stays 400 m.** Raising it to reach Kowloon was measured and refused: the
  streamed city behind the car came into the frustum (`prims` +70%, ~120 more draws). The far
  shore is squeezed into the last `pin_band_m` of depth by `far_shore.gdshaderinc` instead.
- `street_far_m`, `pin_band_m`, `pin_from_m` are stated twice — `backdrop.tres` and `water.tres`
  — and `street_far_m` restates the drive camera's `far`. `verify_backdrop.gd` holds all three;
  move them together.
- `triangle_cap` is a cap, tallest first. The count is the user's pick from frames (2,000 / 5,000 /
  10,000); `min_height_drawn_m` says how far down it reached.
- The shore is a closing of what stands on it (`ground_close_m`), not `basemap.sea_of`: the
  published shoreline over Kowloon has gaps of hundreds of metres and the cut finds no sea.
- The far sea is a rectangle from the frame's north edge to the strip plus each resident frame's
  own sea, marked by `COLOR_0` alpha 0 and drawn by `water.gdshader`. It needs the basemap's sea:
  a `basemap` change that moves `water` owes this stage.
- `bounds` needs its sheets: `Config.fetch_extents` adds them to the fetch for each region in
  `regions`. A strip that touches a frame, or is not north of it, is refused.
- Drawn on `GeneratedLayer.FAR_VISUAL_LAYER` alone and sorted last (`city_layer.gd`): a new lamp
  must leave that layer out of its `light_cull_mask`, as `vehicle_lamps.gd` does, or the cull margin
  pairs it with the far shore.
- No collider, no shadow, unlit at night. A shader change owes a render, `grep -i "shader error"`
  and a frame under `--rendering-method gl_compatibility` (24-bit depth orders the band coarsely).
