---
paths:
  - "etl/pipeline/trees.py"
  - "etl/pipeline/config_blocks/trees.py"
  - "etl/tests/test_trees.py"
  - "game/tools/verify_trees.gd"
  - "game/tuning/trees.tres"
---

# Trees — before marking work done

- **`pipeline/trees.py`, the `trees` block, `trees.tres`, the trunk colliders
  (`city_layer._stand_trunks`), `verify_trees.gd`** (`Q171`): from `trees.json`, both regions,
  compare the three partitions, `drawn_by_kind`, `sized_by_dbh` / `sized_by_kind`, `height_m`,
  `min_kerb_clearance_m`, `facing_away`, plus `verify_trees`' trunks-in-bodies line. Frame:
  `--camera=960,40,200 --look=990,4,280`, day and `--time-of-day=1`.
- Only where a publisher surveys one (user's call): nothing publishes roadside trees. Do not fill
  Hennessy Road. Victoria Park stands off LCSD's major-parks layer (`lcsd_parks`, 2026-11-18).
- A tree whose ground the neighbour region draws is refused `no_ground`: 80 of Victoria Park's on
  the Wan Chai / Causeway Bay seam.
- `min_kerb_clearance_m` is the invariant — no trunk in the carriageway — measured from the stood
  point to the level-0 carriageway region. With the `in_carriageway` refusal off, Wan Chai stands
  35 more trees and the minimum falls to 0.0.
- Every tree gets a trunk cylinder (user's call), nothing for the crown. One static body per kind
  and prop cell, never per tree: Jolt's `max_bodies` is 10,240.
- Every size is authored: `height_per_dbh_m` is a chosen ratio, and Causeway Bay's p90 sits on
  `max_height_m`.
- `no_ground` and `under_structure` read the shipped mesh (`_shipped_faces`): a `materials:`
  colour or the basemap's `park_material` moves both.
- `kind_of` reads the genus (first word of `Scientific_Name`); a genus in two `genera:` lists is
  refused at load.
- Unlit at night; dark crowns and near-white palm fronds are the outline's look.
- `prop_cells.tres` cuts the trees, so cost is per visible cell. A change to the library's mesh
  count is a draw-call change; measure with `--hide-layers=trees`.
- A tint only darkens (`tint_of`): a channel over 1 is brighter than `Q33`'s bounds grade.
- The variation draws come after the yaw and the height; reordering turns and resizes every tree.
