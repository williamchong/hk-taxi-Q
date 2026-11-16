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

- **Collider changes** — `buildings.collision_cell_m`, `class_collision_cell_m`, `_collider`,
  `surface._road_collider`, anything moving the finest tier's geometry (`P5-12`):
  `tools/collider_offset.py --sweep` before and after, and a throttle-route drive whose timeline
  matches to the centimetre. The collider is its own `-colonly` primitive at its own stated cell,
  so it can differ from what is drawn and no frame shows it.
  - The shipped cells equal the finest tier's by VALUE (two config lines; a test pins the
    equality), which is why the offset reads 0.000 m.
  - The sweep's censored tail is thin geometry surviving one world-anchored grid and not the other,
    not the cell moving a vertex. A coarser collider is priced, not taken.
  - Every tile reader goes through `gltf.read_render`: the `.glb` holds two primitives, and a
    grader whose table moves on a collider-only change has stopped filtering.
  - The carve cuts both primitives and books the render mesh's counters alone; a `_carve_tile`
    change that cuts one leaves a wall the player cannot see.
- **Occluder changes** — `buildings.occluder_cell_m`, `class_occluder_cell_m`, `occluder_classes`,
  `_occluder`, `use_occlusion_culling` (`P5-13`): paste draws and `prims` on the throttle route AND
  at Mong Kok's worst camera (694, 392) N/S/E/W, occlusion off and on, frames `cmp`'d twice per
  side, and the PCK.
  - Wan Chai cannot show it (2 draws culled against 12–47 in Mong Kok): the culling unit is the
    instance and only a dense region hides a whole 150 m tile.
  - A frame that differs is a defect: the occluder is a collapse and can bulge past the wall. 4 / 8
    / 16 m all read 0 px.
  - The occluder rides in every tier, so its PCK price is paid twice; the cell is the lever (4 m
    +10.3%; 8 m keeps the east heading and loses the west).
  - The importer names every one `OccluderInstance3D`, so `verify_tiles.gd` counts against
    `city.json`'s `occluder`; a tile the ETL built none for must carry none.
- Any flag to `drive.sh` drops its default throttle hold: pass `--hold=accelerate@0.5+5.5`.
