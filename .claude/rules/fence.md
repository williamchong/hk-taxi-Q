---
paths:
  - "etl/pipeline/fence.py"
  - "etl/tests/test_fence.py"
  - "etl/tests/test_make_barrier.py"
  - "tools/make_barrier.py"
  - "tools/reachability.py"
  - "game/scripts/city/fence.gd"
  - "game/scripts/city/generated_fence.gd"
  - "game/tools/verify_fence.gd"
  - "game/tools/verify_road_graph.gd"
  - "game/tuning/barrier_vertex.{tres,md}"
---

# The fence and the car bar — before marking work done

- **`pipeline/fence.py`, the `clearance` or `fence` blocks, `RoadGraph`'s car bar**:
  `tools/battery.py fence --region <r> --before <root>`. From `fence.json` compare `fenced_edges`
  (with its count), `components`, `mouths`, `ends_behind_another_fence`, `ends_with_no_way_in`,
  `barriers`, `clipped_edges`, `clipped_ends`, `clipped_no_width`. Run `tools/reachability.py
  --region <r> --refuse <fence set>` and paste its table. A/B render one fenced mouth at a fixed
  camera.
- Two bars over one measurement, never merged (`Q19`): `is_passable` reads `clear_width_m` at the
  lane (3.20 m), `fits_car` at the car (`car_width_m`, 1.695 m). Merged either way, traffic is sent
  down `e207`'s 1.95 m or the player is fenced out of `e781`'s 3.50 m. `verify_road_graph.gd`'s
  `_check_car_bar` asserts an edge exists between the bars; mutation-check it.
- `ends_behind_another_fence` (a pocket: every arm fenced) and `ends_with_no_way_in` (a dead end)
  are different counters. Both count ends, so a shared node counts twice.
- `clipped_edges` is a third population (`Q143`): one open arm, no `foreign_edges` run at the node,
  and the polyline end within `fence.clipped_within_m` of the rectangle's line from the inside.
  Mutation-check `verify_fence.gd`'s re-derivation (drop an edge, add an interior one, shrink
  `region_extent_m`). `region_extent_m` is `Config.region_high`, never `bounds_game`.
- Measured shut (`P3-29`): no vertical term in the `clearance:` block. Built and withdrawn — the
  0.18–0.30 m band fences three climbing ramps and misses `e99`.
  `test_a_vertical_bar_added_here_is_rejected` is the ratchet. That band is measured by
  `tools/ground_clearance.py`'s structure half, graded and not gated.
- The prop collides as a box over its `-col` extent (`Q159`), never the trimesh (open between the
  rails). `-col`, never `_col`. Its material is `barrier_vertex`, never `barriers` (that name
  dispatches the railing class's `.tres`).
- The prop draws as one `MultiMesh` per plan cell of `prop_cells.tres` (`PropBatch.batches`) with
  colliders as one body a cell (`PropBatch.boxes`, `Q217`); per-placement scenes cost +36 draw
  calls. It casts no shadow. `verify_fence.gd` grades the `.glb`'s `-col` import, not the placer,
  so keep and read `fence.gd`'s printed collider count.
- `fence.unit_width_m` must equal `tools/make_barrier.py`'s `UNIT_WIDTH_M` (bound in
  `test_fence.py`): a row is tiled from a unit, never one barrier scaled.
