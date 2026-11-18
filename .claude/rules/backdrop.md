---
paths:
  - "etl/pipeline/backdrop.py"
  - "etl/pipeline/config_blocks/backdrop.py"
  - "etl/tests/test_backdrop.py"
  - "game/tools/verify_backdrop.gd"
  - "game/tuning/backdrop.{tres,md}"
  - "game/tuning/far_view.{tres,md}"
  - "game/scripts/city/far_cull.gd"
  - "game/scripts/city/city_regions.gd"
  - "game/assets/shaders/backdrop.gdshader"
  - "game/assets/shaders/far_shore.gdshaderinc"
---

# The far versions — before marking work done

`P3-100`, `Q249` (amended 2026-11-18). Every region's `backdrop.glb` is its own far version: iB1000
`Building` footprints in its box extruded to their published roof, one flat shore slab, and the
water round it. Kowloon is the far-only region `tsim_sha_tsui`. Another region sees it past the
400 m far plane, where its tiles are never loaded.

- `tools/battery.py backdrop` (Wan Chai): `blocks_drawn`, `min_height_drawn_m`, the three triangle
  counts, `open_sea_m2`. A far-only region is built by `python -m pipeline --region tsim_sha_tsui`
  (`fetch` and `backdrop` only) and needs the driven regions' sheets its reach meets — Mong Kok's
  included. Re-sync after: `tools/sync_generated.sh wan_chai causeway_bay` ships every other built
  far version as `regions.json`'s `far`.
- Frames: `--spawn-at=212,5.6,40 --spawn-facing=212,5,0` (Expo Drive East, Kowloon) by day, at
  `--time-of-day=1.0`, and under `--rendering-method gl_compatibility` (run `godot` with the driver
  directly: `drive.sh` refuses the flag). A region's own far version: Hennessy Road looking east,
  `--spawn-at=270,5.5,691 --spawn-facing=510,5,663` — the gap at the street's far end holds the
  rest of Wan Chai and Causeway Bay. `--hud=off --traffic=off --trams=off`.
- Cost against `--hide-layers=backdrop`, facing the harbour AND facing away (`212,5,80`). Shipped:
  +15,834 / +7 draws and +5,264 / +2.
- 🔴 **The camera's `far` stays 400 m.** Raising it was measured and refused (`prims` +70%, ~120
  more draws), and so were an 800–1,000 m LOD band and a second camera for the far view (`Q249`
  amended). The far version is squeezed into the last `pin_band_m` of depth by
  `far_shore.gdshaderinc` instead.
- **Skipped nearer than `street_far_m`** (`backdrop.gdshader`'s discard, measured from the eye):
  the streamer holds every tile within 400 m, and the simplified blocks would show round the real
  ones. The far sea is not skipped — under the basemap's water it fails the depth test.
- **Hidden past `far_view.tres`'s `max_far_m`** (8,000 m, 86% fog at noon) by `city_layer.gd`,
  measured to the box's nearest point, so a far sea round the camera is never hidden. Lifting the
  cap adds Sha Tin from Wan Chai: +1 draw and its whole mesh in primitives. No line-of-sight
  table (`Q249`).
- `street_far_m`, `pin_band_m`, `pin_from_m` are stated twice — `backdrop.tres` and `water.tres`
  — and `street_far_m` restates the drive camera's `far`. `verify_backdrop.gd` holds all three;
  move them together.
- `triangle_cap` is a cap per region, tallest first. The count, 5,000, is the user's pick from
  frames (2,000 / 5,000 / 10,000); `min_height_drawn_m` says how far down it reached. The night
  wash is the user's pick too: 0.55, Wan Chai's (`Q252`).
- The shore is a closing of what stands on it (`ground_close_m`), not `basemap.sea_of`: the
  published shoreline over Kowloon has gaps of hundreds of metres and the cut finds no sea.
- The water is a driven region's frame sea plus the **open water** out to `sea_reach_m`: the reach
  less the shore's closing, outside every driven frame, joined to a frame's sea. Plan it
  (`COLOR_0` alpha 0 on `backdrop_sea`) after a change: an unbuilt place wider than the closing
  that touches the harbour reads as water. A `basemap` change that moves `water` owes this stage.
- Drawn on `GeneratedLayer.FAR_VISUAL_LAYER` alone and sorted last (`city_layer.gd`): a new lamp
  must leave that layer out of its `light_cull_mask`, as `vehicle_lamps.gd` does, or the cull margin
  pairs it with every far version.
- Hidden by `city_layer.gd` when its box is outside the camera's view (`far_cull.gd`; `GROW_M`
  covers the frame the answer is late by).
- No collider, no shadow. Floodlit at night per wall (`Q252`). A shader change owes a render,
  `grep -i "shader error"` and the Compatibility frame (24-bit depth orders the band coarsely).
