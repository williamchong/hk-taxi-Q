---
paths:
  - "etl/pipeline/config_blocks/tramway.py"
  - "etl/pipeline/tramway.py"
  - "etl/tests/test_tramway.py"
  - "game/assets/shaders/tramway.gdshader"
  - "game/tools/verify_tramway.gd"
  - "game/tuning/tramway.{tres,md}"
---

# Tram rails — before marking work done

The stage grades itself; its failures render as nothing.

- **`pipeline/tramway.py`, the `tramway` block, any tram-rail change**: from `tramway.json` compare
  `off_gauge_stations`, `pairs` against `tracks`, `inverted`, `rails_unsnapped`, `rails_trimmed`,
  and `rails_drawn_m` against `rails_m`, before and after (`Q58`).
- The mis-pairing detector is `off_gauge_stations` (and `pairs` exceeding `tracks`), not
  `drawn_gauge_m`, which is bounded by `pair_tolerance_m` by construction.
- `inverted` must be 0: `tramway.gdshader` is `cull_back`, so winding decides visibility.
- A shader change owes a render and `grep -i "shader error"`.
- `rails_unsnapped` and `rails_trimmed` are 0 in both regions (rails are cut at the region's
  rectangle); a missing rail shows there, not in one frame.
- A rail under the road is invisible to these counters: `tools/paint_clearance.py --layer tramway`
  (reported, never gated), its `under the HIGHEST road face` line. Owed by a change to
  `surface.py`'s kerb, the ground's decimation or `surface_within_m`.
