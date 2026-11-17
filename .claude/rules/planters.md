---
paths:
  - "etl/pipeline/planters.py"
  - "etl/pipeline/config_blocks/planters.py"
  - "etl/tests/test_planters.py"
  - "game/tools/verify_planters.gd"
  - "game/tuning/planters.tres"
---

# Roadside planters — before marking work done

`P3-98`, `Q247`. HyD's Roadside Planter Wall (`INV_RPW`) as walls, and a shrub bed where one
feature's walls close into a ring.

- `tools/battery.py planters`, both regions: `rings` = `beds` + `in_carriageway` + `cut_away` +
  `no_ground`; `bed_area_m2`, `road_cut_m2`, `building_cut_m2`, `triangles`,
  `collider_triangles`. Frames: `--camera=238,11,142 --look=221,5,92` (the 75 m median),
  `--camera=302,10,506 --look=282,4,482` (the island round a lift tower).
- Only where a wall is surveyed (the trees' rule, the user's): no bed between two walls that do
  not close, no planter where HyD draws none.
- Every height and the planting are authored; the publisher gives a line. The look is the user's
  pick of three renders (kerb box with flat green / box and shrub / shrub alone): box and shrub.
- 🔴 Never on the drawn road: cut back to `kerb_clear_m` outside the level-0 carriageway region,
  refused whole over `max_on_road`. Three of Wan Chai's rings are refused, the island beside
  Victoria Park among them. Do not lower the bar to plant them: the ring and the ribbon disagree.
- A bed is cut by every tile wall that stands from its ground through the wall's top (`Walls`),
  so a ring round a pier is not planted through. A wall that starts overhead cuts nothing.
- The collider is the walls alone (`planters_collision-colonly`): the planting is driven through,
  the wall is not. `verify_planters.gd` holds its top under the drawn mesh's.
- A wall follows the ground under each ring point; `max_ground_fall_m` is what a level top would hide
  (0.88 m in Wan Chai).
- ⚠️ `INV_RPW` has no level, so every wall stands on the tile ground. Checked 2026-11-18: 22 of
  Wan Chai's 48 features lie over 10% under something drawn overhead (710 of 2,224 m). In plan, the
  17 under a flyover are islands on the street beneath: the large ones run across the deck's own
  carriageway, which a planter on it could not. Four under footbridges (139 m) sit on street
  islands too, but shape does not rule out the bridge. One (10 m under) was not looked at.
- A `materials:` colour or the basemap's `park_material` moves what counts as ground, as for the
  trees (`tile_corners` is shared with `trees.py`).
- Railings stand within 0.5 m of 12 Wan Chai walls; nothing registers one to the other.
