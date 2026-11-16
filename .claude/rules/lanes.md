---
paths:
  - "tools/lane_paint.py"
  - "etl/tests/test_lane_paint.py"
  - "etl/pipeline/carriageway.py"
  - "game/scripts/city/road_graph.gd"
  - "game/assets/shaders/road_markings.gdshader"
---

# Lane counts and the painted lane — before marking work done

- **Anything that moves `lanes`, `lanes_source`, `LANE_FLOOR`, `_ROW_MIN`, `_deck_lane_ceiling` or
  the drawn ribbon's width**: `tools/battery.py lanes --region <r> --before <root>`
  (`lane_paint.py --sweep`). It asks whether the strip the markings shader paints is wide enough
  to be a lane — a quotient neither `carriageway.py` nor `surface.py` can see (`Q114`). It reads
  the synced bundle, grades and exits 0.
  - The bar is config (`--min-lane-m`, default TPDM's 3.00 m from `width_bounds.lane_m`): quote it
    and sweep it.
  - Edges, vertices and metres are three readings. Its distribution is min/p1/p10/p50 on purpose,
    and its verdict has three states.
- The floor under `lanes` is `LANE_FLOOR` in `RoadGraph.lane_offset`, not in the ETL: the driving
  line needs two, but `road_markings.gdshader` cuts the ribbon into `lanes` strips and a floored
  count paints a lane that is not there. `_ROW_MIN` is not tied to it — at 1, a single arrow
  becomes a lane count.
- Off-grade the deck is a ceiling on `lanes`, never a source (`Q107`, `Q114`): the rule only
  lowers. Edges authored below their ceiling do not move.
- A lane count moves no geometry: `roads.glb` is byte-identical but for
  `TEXCOORD_0`/`TEXCOORD_1`, and `carriageway[]`, `roadsurface.json`, `clearance.json` and the
  tiles are byte-identical. `arrows_placements.json` may move, so the arrows' counters are owed.
- Evidence is a frame: force a re-import and shoot until a hash repeats, each side.
- Measured shut (`Q127`, `P3-35g4`): no lane count off TD's lane lines. From the centreline it
  agrees 24%; hosted on the edge's own ribbon (`width_evidence.hosted_count`) 79% / 69% against
  `measured` and 85% / 88% against `arrows`, short of the high-80s bar set beforehand. Do not
  sweep its rail clearance to reach the bar (`Q72`). Reading the disagreeing edges one by one is
  what would reopen it.
