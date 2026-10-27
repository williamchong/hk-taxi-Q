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
  (`layer_preview._stand_trunks`) or `verify_trees.gd`: paste `trees.json`'s three partitions,
  `drawn_by_kind`, `sized_by_dbh` / `sized_by_kind`, `height_m`, `min_kerb_clearance_m` and
  `facing_away` for BOTH regions, before and after, plus `verify_trees`' trunks-in-bodies line —
  and a frame of the Wan Chai cluster at `--camera=960,40,200 --look=990,4,280`, day and
  `--time-of-day=1`** (`P3-77`, `Q171`). 🔴 **Only where a publisher surveys one** (the user's
  call): LCSD's layer leaves out the major parks and nothing publishes the roadside trees, so
  Victoria Park and Hennessy Road are bare. Do not fill them, sprinkle a rhythm, or invent a park's
  planting — that is a new decision, not a fix. 🔴 **`min_kerb_clearance_m` is the invariant — no
  trunk in the carriageway** — measured from the stood point to the level-0 carriageway region,
  not read back off the refusal. Mutation-checked 2026-10-27: with the `in_carriageway` refusal
  off, Wan Chai stands 35 more trees and the minimum falls from 0.3562 to 0.0.
  🔴 **A tree is a crash** (the user's call): every tree gets a trunk cylinder, scaled with the
  tree, and nothing for the crown. ⚠️ **One static body per kind and prop cell, never a body
  per tree**: Jolt's `max_bodies` is 10,240 and the railings already hold 7,693. ⚠️
  **Every size is authored**: neither publisher gives a height or a crown, and
  `height_per_dbh_m` (HyD's `DBH` → a height) is a ratio we chose, not a cited allometry. Causeway
  Bay's p90 sits on `max_height_m`, so a change there moves a fifth of its trees. ⚠️ **The two
  refusals that look at the city read the SHIPPED mesh** (`_shipped_faces`): `no_ground` is no
  tile face wearing the paving or park colour under the trunk, and `under_structure` is a road
  chunk or roof between `overhead_clear_m` and the treetop. A colour change in `materials:` or the
  basemap's `park_material` moves both. ⚠️ **`kind_of` reads the genus**, the first word of LCSD's
  `Scientific_Name`; a genus in two `genera:` lists is refused at load. ⚠️ **Unlit at night**:
  the night frame shows dark crowns under the city-wide outline, and the palms' fronds read
  near-white under it. That is the outline's look, not a lit tree. ⚠️ **`prop_cells.tres` cuts the
  trees**, so their cost is per visible cell: +4 draws / +10k prims on the throttle route, +9 to
  +13 / +24k to +59k from `--spawn-fare=wan_chai/f_045`, measured with `--hide-layers=trees`
  2026-10-27. A change to the library's mesh count is a draw-call change. 🔴 **A tint only
  darkens** (`tint_of`, `Q171`): the canopy colour sits near the top of `Q33`'s leaf range, so
  a channel over 1 is a tree brighter than the material the bounds grade. ⚠️ **The variation
  draws come after the yaw and the height** — reorder them and every tree turns and resizes.
