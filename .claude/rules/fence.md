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

Moved verbatim from the root `CLAUDE.md`, which keeps the trigger and points here.

- **`pipeline/fence.py`, the `clearance` or `fence` config blocks, or any change to `RoadGraph`'s
  car bar: paste `fence.json`'s `fenced_edges` (with its count), `components`, `mouths`,
  `ends_behind_another_fence`, `ends_with_no_way_in` and `barriers`, before and after — run
  `tools/reachability.py --refuse <the fence set>` and paste its table, and A/B render one fenced
  mouth at a fixed camera.** 🔴 **The fence is a SECOND bar over the SAME measurement and the two may
  never be merged** (`Q19`): `is_passable` reads `clear_width_m` at the lane (3.20 m) and `fits_car`
  reads it at the car (1.80 m), so re-pointing either at the other sends traffic down `e207`'s
  1.95 m or fences the player out of `e781`'s 3.50 m. `verify_road_graph.gd`'s `_check_car_bar`
  asserts an edge exists *between* the bars, because a region where every blocked edge is also
  fenced is what a merge looks like from the inside — ⚠️ **mutation-check it rather than reading its
  pass** (`Q72`).
  🔴 **`ends_behind_another_fence` and `ends_with_no_way_in` are NOT the same counter and merging
  them makes both meaningless.** The first is `Q19`'s pocket — arms exist and every one is fenced,
  so a barrier there would stand behind a barrier; the second is a dead end, a street clipped by the
  region, where nobody can arrive at all. Conflated, the first run reported 13 pockets over 14
  *disjoint* components. ⚠️ The counters count **ends**, so a node shared by two fenced edges counts
  twice.
  🔴 **The prop COLLIDES, and it is the only thing in the barrier family that does.** Every
  generated railing class is collider-free and `verify_railings.gd` asserts that;
  `game/tuning/barriers.tres`' "no collider" paragraph is about that *generated* class and stays
  true. ⚠️ **Its material is `barrier_vertex`, never `barriers`** — that name dispatches the railing
  class to `tuning/barriers.tres`, and sharing it hands this prop a fence's shader and fails that
  tool while both halves render. ⚠️ **`-col`, never `_col`.**
  🔴 **The prop draws as ONE `MultiMesh` and its colliders are separate bodies — do not "simplify"
  it back to instantiating the scene per placement.** That build was measured at **+36 draw calls**
  (81-92 against a 55-57 baseline) on a layer every other generated class ships in one; the
  MultiMesh is **pixel-identical** at +1. ⚠️ **The split opens a gap `verify_fence.gd` cannot see** —
  it grades the `.glb`'s own `-col` import, so a placer that stopped building bodies stays green and
  renders perfectly. `fence.gd` prints its collider count for that reason; keep it, and read it.
  🔴 **`clipped_edges` is a THIRD population (`Q143`) and joins neither list.** An end is clipped
  when its node has one open arm, no `foreign_edges` run touches it (the neighbour's way in is
  never closed), and the polyline end lies within `fence.clipped_within_m` of the rectangle's line
  **from the inside** — the far end of an owned crossing run stands on the neighbour's ground and
  the first build closed five of them. Paste `clipped_edges` / `clipped_ends` / `clipped_no_width`
  before and after, and **mutation-check `verify_fence.gd`'s re-derivation** (drop an edge, add an
  interior one, shrink `region_extent_m`) rather than reading its pass. ⚠️ `region_extent_m` is
  `Config.region_high`, never `bounds_game`.
  ⚠️ **`fence.unit_width_m` must equal `tools/make_barrier.py`'s `UNIT_WIDTH_M`** — a row is tiled
  from a standard unit and never one barrier scaled, because an x-scale to a 10.24 m mouth stretches
  the posts with it. `etl/tests/test_fence.py` binds the two.
  🔴 **Do NOT re-add a vertical term to the `clearance:` block.** `Q19` prescribed one; `P3-29`
  built, measured and withdrew it — the 0.18-0.30 m band is the one `Q23`'s bumper floor exists to
  suppress, so it fences three climbing ramps and misses `e99`, the edge it was prescribed for. The
  block's closed-key-set check refuses it and `test_a_vertical_bar_added_here_is_rejected` is the
  ratchet. ✅ That band's measurement is `tools/ground_clearance.py`'s `structure_class` extension,
  **shipped 2026-09-02** and graded rather than gated — 330 cells / 323.4 m² / 25 level-0 edges. See
  its own bullet above. Numbers in `Q19`.
