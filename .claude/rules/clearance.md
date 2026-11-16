---
paths:
  - "etl/pipeline/clearance.py"
  - "tools/carriageway_occupancy.py"
  - "tools/clearance_reconcile.py"
  - "tools/narrowing.py"
  - "tools/corridor_truth.py"
  - "etl/tests/test_clearance.py"
  - "etl/tests/test_carriageway_occupancy.py"
  - "etl/tests/test_clearance_reconcile.py"
  - "etl/tests/test_narrowing.py"
  - "etl/tests/test_corridor_truth.py"
---

# Clearance, the widening and the corridor graders — before marking work done

- **`surface.floor_default_m`, any `roads.surface` widening, or anything that moves the starved
  population (`ALONG_M` included)**: `tools/narrowing.py --region <r>`, before and after. It
  imports `pipeline.clearance` whole, so a resolution constant moves its tables. Measured shut
  (`Q19`): narrowing clears no blocked edge at any factor down to 1.3x and loses `e207` and `e595`.
- **`clearance.py` or `carriageway_occupancy.py`**: `tools/clearance_reconcile.py --generated
  <dir>`; add `--sweep` for `ALONG_M`, `ACROSS_M`, `CELL_M`, `SUBDIVIDE_M`, `MAX_SUBDIVISIONS`,
  `INDEX_CELL_M`. Pipeline and grader differ by plan cell size (`Q51`); `EXPECT`, keyed by region,
  is the ratchet and fails when either count moves. A finding, never a bar to retune; a ratchet
  move must show the at-grade halves unchanged. `narrowing.py` is owed too.
- `ALONG_M` is `CELL_M`: the published clearance is a lower bound at that cell and no finer.
  Moving it changes what routing refuses: the user's call.
- **Levels** (`Q108`, `Q111`): `clearance.LEVELS` and `carriageway_occupancy.CORRIDOR_LEVELS` are
  `(0, 1)` and move together; `centreline_error.py --levels` and `narrowing.py` stay at `(0,)`.
  - `LEVELS == carriageway_survey.levels` (`test_the_shipped_levels_match_the_width_surveys`).
  - Open exactly where measured: `fence.touchdown_levels` is `[-1, 2]`, `RoadGraph.is_drivable` is
    level 0 or a measured corridor (`test_the_open_levels_are_the_measured_levels`). Moving
    `LEVELS` moves what the player can drive on: the user's call.
  - Level −1 stays shut: `e489`'s defect is 0.22 m of headroom, which a horizontal corridor cannot
    express. Level 2 is listed and inert.
  - `fence.fenced_edges` takes the closed levels, never the literal 0; its filter is all that
    stands between a measured off-grade width and a barrier across a live ramp. Mutation-check
    `test_an_off_grade_edge_on_a_CLOSED_level_is_not_fenced` and its `OPEN` twin.
  - Prove a walk change inert in two steps: hold the levels and reproduce `clearance.json`
    byte-for-byte, then move the level and show only never-walked rows moved.
- **`carriageway_occupancy.py --levels`** is additive: a set omitting 0 is refused (the corridor
  gate would pass on an empty population), and negative levels are refused. Widening the levels
  moves no area share; the inertness proof is the corridor table.
  `clearance_reconcile.py --levels` reaches both halves.
- **`--probe-edges`** reads heights for named edges and gates nothing. `base` is an upper bound (a
  negative reading proves geometry reaches the road); `top` is a lower bound, not headroom.
- **`carriageway_occupancy.py` walks two windows** (`Q129`): the ribbon for area shares, the
  corridor (`walk_carriageway(corridor=True)`) for the corridor half and the reconcile. The
  corridor is tapered between vertices as `clearance.py` walks it, and an undrawn corridor cell
  stands at its own ribbon's height only where that ribbon is drawn. Prove a change by the sweep
  line and an unchanged share table. It gates and currently fails; read the exit code.
- **The two instruments disagree about one edge** (`Q110`): re-run the grader at the pipeline's
  resolution (`--across-m 0.25 --index-cell-m 0.5 --spacing-m 0.5`), then
  `tools/corridor_truth.py --probe-edges <ids>`. Never prefer one instrument. The exact tool can
  clear an edge and never condemn one: every tile triangle blocks, so a figure above a bar is
  proof and one below is evidence of nothing. It reads what stands in the bumper band, not
  whether deck stands under it. Exits 0.
