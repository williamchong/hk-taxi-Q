---
paths:
  - "tools/lane_paint.py"
  - "etl/tests/test_lane_paint.py"
  - "etl/pipeline/carriageway.py"
  - "game/scripts/city/road_graph.gd"
  - "game/assets/shaders/road_markings.gdshader"
---

# Lane counts and the painted lane — before marking work done

Moved verbatim from the root `CLAUDE.md`, which keeps the trigger and points here.

- 🔴 **Anything that moves `lanes`, `lanes_source`, `LANE_FLOOR`, `_ROW_MIN`, `_deck_lane_ceiling`
  or the drawn ribbon's WIDTH: also `tools/lane_paint.py`, before and after, with `--sweep`.** It
  asks the one question no stage can ask from inside — **is the strip the markings shader paints
  wide enough to be a lane?** — because that strip is a quotient of `carriageway.py`'s `lanes` and
  `surface.py`'s drawn half-width, and neither stage can see the other's answer (`Q114`).
  ⚠️ **The bar is config and the headline is the bar's**: it defaults to TPDM 4.3.9.8's own narrow
  end from `width_bounds.lane_m` (3.00 m), `Q113` swept at an unsourced 2.50, and the population runs
  5 / 10 / 16 / 37 / 66 edges over 2.00-3.65 m — so quote the bar, and sweep it.
  ⚠️ **Edges, vertices AND metres are three readings**: a vertex count is a property of
  `deck.resample_m` and metres are a property of the city. ⚠️ Its distribution is **min/p1/p10/p50**
  and deliberately not the house p50/p90/p99/max, which on this region reads 5.12 on all four points
  over a 1.15 m lane — do not "restore consistency". ⚠️ Its verdict column is **three** states; a
  boolean reads a missing bracket as agreement. It grades rather than checks and exits 0.
  🔴 **The floor under `lanes` lives in `RoadGraph.lane_offset` as `LANE_FLOOR` and NOT in the ETL,
  and that is not tidiness.** `lanes` has two consumers — the driving line, which needs a count of at
  least two to stay off the centreline, and `road_markings.gdshader`, which cuts the drawn ribbon
  into `lanes` strips. Flooring the published count served the first and made the second paint a lane
  that is not there. 🔴 **`_ROW_MIN` must NOT be re-tied to it**: it was `_ROW_MIN = LANES_FLOOR` on
  an argument that expired, and following the floor to 1 makes a **single arrow** a lane count, which
  is a defect this repo has already shipped once.
  🔴 **Off-grade, the deck is a CEILING on `lanes` and never a source of one.** No turn arrows are
  painted on any bridge deck in this region and the publishers' 2D rays find the street underneath,
  so nothing licenses *assigning* a count from a deck span — only refusing one paint cannot fit on,
  which is `Q107`'s own licence for cutting the ribbon to `deck_rim_m`. ⚠️ **One-sided on purpose**:
  6 of 36 deck edges are cut and **8 authored below their ceiling do not move**. A rule that raised a
  count would be the deck assigning lanes.
  ⚠️ **A lane count moves NO geometry, and that is the inertness proof** — `roads.glb`'s positions,
  normals, colours and indices must be byte-identical with only `TEXCOORD_0`/`TEXCOORD_1` differing,
  and `carriageway[]`, `roadsurface.json`, `clearance.json` and every tile byte-identical. `arrows.glb`
  *does* move, positions only (the lane snap), so its counters are owed.
  ⚠️ **The evidence is a frame and the cache lies**: force a re-import, and expect the first several
  runs after one **not to reproduce** — shoot until a hash repeats, each side. Numbers in `Q114`.
- 🚫 **A lane count off TD's lane lines is MEASURED AND REFUSED twice — do not re-propose it
  without a new argument** (`Q127`, then `P3-35g4`). From the centreline it sees the other
  carriageway's lines (24% agreement). Hosted on the edge's own drawn ribbon —
  `width_evidence.hosted_count`, which §2a prints on every run — the over-count goes and agreement
  reaches 79% / 69% against `measured` and 85% / 88% against `arrows`: real, and short of a bar set
  beforehand (high 80s, both regions), for ten edges. ⚠️ **Do not sweep its rail clearance to reach
  the bar** — that is a free value tuned for a count (`Q72`). What would reopen it is reading the
  21 · 10 disagreeing edges one by one.

