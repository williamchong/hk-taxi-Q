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

Moved verbatim from the root `CLAUDE.md`, which keeps the trigger and points here.

- **`pipeline/tramway.py`, the `tramway` config block, or any tram-rail change: paste `tramway.json`'s
  `off_gauge_stations`, `pairs` vs `tracks`, and `inverted`, before and after.** There is no separate
  grader and there should not be: the stage grades itself, because the three ways this can break all
  render as **nothing** and none is visible in a frame. ⚠️ **The mis-pairing detector is
  `off_gauge_stations`, not `drawn_gauge_m`** — a bed drawn between two rails that are not a track
  renders perfectly and is a lane wide, but the trim rejects every one of its stations, so it shows
  up as rejected stations and as `pairs` exceeding `tracks`. `drawn_gauge_m` is bounded by
  `pair_tolerance_m` *by construction* and cannot read outside it; the p90 **1.92 m** and **4.62 m**
  that caught two shipped defects were measured before the trim existed. `inverted`
  must be **0**: `tramway.gdshader` is `cull_back`, so winding decides visibility and the normal
  attribute does not, and the first build had **5,111 of 5,112** triangles facing the ground with
  everything else correct. ⚠️ **A tramway change is also a shader change** — `check.sh` exits 0 on a
  shader that fails to compile, so render and `grep -i "shader error"`. Numbers in `Q58`.
