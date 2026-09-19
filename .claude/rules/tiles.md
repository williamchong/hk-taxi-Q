---
paths:
  - "etl/pipeline/buildings.py"
  - "etl/pipeline/gltf.py"
  - "tools/collider_offset.py"
  - "etl/tests/test_buildings.py"
  - "etl/tests/test_gltf.py"
  - "etl/tests/test_collider_name_copies.py"
  - "game/tools/verify_tiles.gd"
---

# Tile colliders and occluders — before marking work done

Moved verbatim from the root `CLAUDE.md`, which keeps the trigger and points here.

- 🔴 **Collider changes — `buildings.collision_cell_m`, `class_collision_cell_m`, `_collider`,
  `surface._road_collider`, or anything that moves the finest tier's geometry: also
  `tools/collider_offset.py`, before and after, with `--sweep`, and a throttle-route drive whose
  timeline is compared to the centimetre** (`P5-12`). The collider is its own `-colonly` primitive
  beside the render tier and road ribbon, decimated at its own **stated** cell, so it *can* differ
  from what is drawn and nothing in a frame can show that: a wall the car hits before it reaches the
  one it sees, or drives through. ⚠️ **The shipped cells equal the finest tier's by VALUE, not by
  reference** — the offset reads 0.000 m because two config lines agree, and a test pins the
  equality so the seam cannot open silently; ⚠️ **the sweep's censored tail is not the cell moving a
  vertex** — it is thin geometry surviving one world-anchored grid and not the other, which is why a
  coarser collider is priced and not taken. 🔴 **Every tile reader goes through `gltf.read_render`**:
  the `.glb` holds two primitives and a grader reading it whole counts every wall twice — a table
  that moves on a collider-only change is a reader that stopped filtering. ⚠️ **The carve cuts both
  primitives and books the render mesh's counters alone**; a change to `_carve_tile` that cuts one
  strands the car on a wall the player cannot see. ⚠️ The PCK is inert to the split (+2,272 B) because
  the importer removes the collider's mesh; the `.glb` on disk is not, and is not shipped.
- 🔴 **Occluder changes — `buildings.occluder_cell_m`, `class_occluder_cell_m`, `occluder_classes`,
  `_occluder`, or `use_occlusion_culling`: paste draws and `prims` on the throttle route AND at Mong
  Kok's worst camera (694, 392) N/S/E/W, occlusion off and on, frames `cmp`'d twice per side, and the
  PCK** (`P5-13`). ⚠️ **Wan Chai cannot show what this does**: its route culls 2 draw calls where the
  same occluder culls 12–47 in Mong Kok, because the culling unit is the instance and only a dense
  region hides a whole 150 m tile. ⚠️ **A frame that differs is a defect, never a win** — the occluder
  is a collapse and can bulge past the drawn wall; 4 / 8 / 16 m all read 0 px, so a cell that moves a
  pixel is over-culling. ⚠️ **The occluder rides in EVERY tier** (the streamer swaps whole tier
  scenes), so its PCK price is paid twice and the cell sweep is the lever: 4 m +10.3%, 8 m keeps the
  east heading and loses the west. ⚠️ **`verify_tiles.gd` cannot assert its name** — the importer
  names every one `OccluderInstance3D` — so it counts against `city.json`'s `occluder`, and a tile
  the ETL built none for must carry none. ⚠️ **Any flag to `drive.sh` drops its default throttle
  hold** — pass `--hold=accelerate@0.5+5.5` yourself, or six stationary seconds read like a route.
