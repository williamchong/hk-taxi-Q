---
paths:
  - "etl/pipeline/config_blocks/railings.py"
  - "etl/pipeline/railings.py"
  - "etl/tests/test_railings.py"
  - "etl/tests/test_railing_error.py"
  - "tools/railing_error.py"
  - "game/assets/shaders/railings.gdshader"
  - "game/tools/verify_railings.gd"
  - "game/tuning/{railings,bollards,barriers}.{tres,md}"
---

# Railings — before marking work done

- **`pipeline/railings.py`, the `railings` block, any railing change**: `tools/battery.py railings
  --region <r> --before <root>` (the report and `railing_error.py`; paste its three tables). Per
  class, from `railings.json`: `shift_m` (with `n`), `samples_over_shift`,
  `metres_on_buried_kerb`, `metres_bridged`, `metres_dropped_collapsed`, `stations_merged`,
  `stations_folded`, `stations_unfolded`, `facing_away`, `panels`, `metres_snapped`, `joints`,
  `joint_gap_m`, `bends`, plus the shared `refused_m`. Never pool classes (`Q61`).
- A railing's position is registered, not read (`Q60`). `shift_m` is recorded over the samples
  `max_shift_m` refuses (`n` > drawn, `Q58`). The push is unconditional, unlike the signs'
  outward-only clamp (`Q78`): a fence is a run. A widening moves every fence.
- `metres_bridged` is the one part of `drawn_m` the stage invents; a jump is `bridge_gap_m`
  reaching further. The metre counters are not a partition (two frames).
- `facing_away` must be 0 and `railings.gdshader` stays `cull_disabled` (the fence is mostly air).
  It reads the first vertex's normal and is asked of the unit panel, never per stand (`Q72`).
- **Slab** (`Q112`): extruded outward only, so the registered face and `outset_m` hold. Near face
  takes `flip`, far `not flip`, cap `flip`. Winding each quad to its normal makes `facing_away` 0
  by construction.
- `min_station_gap_m` (two stations at one place) and `fold_tolerance_deg` (the offset rail
  crossing its centreline) are two bars for two degeneracies; never merge them. The fold rule
  fires only where every step at a station folds. Sweep and paste both.
- **Library** (`Q115`): `railings.glb` is one unit panel per class; the city is
  `railings_placements.json`. Joint residuals and wedges are published, not closed; do not
  stretch or turn a panel to hide one (`Q54`). `panel_m` is the `.tres` `post_pitch_m`, by test.
- **`railing_error.py --region <r>`** walks the unit and stands its samples; its p50 is the slab's
  mid-surface. It does not tell the two faces apart; its `drawn_m` catches a broken fold.
- **Kerb** (`Q133`): a fence stands on the road's kerb (`drawnroad.Ribbon.kerb_at`), never `±half`
  about the centreline (`Q57`). Standing line, side (nearer kerb about `Ribbon.middle`) and facing
  move together; `TestRoad` has one test each — mutation-check each alone. The standing line is
  the plain offset, never `surface.boundary`'s hold. A kerb station within `min_station_gap_m` of
  a published vertex is dropped (`_own_places`). Prove a change inert by forcing the road
  symmetric. No "panels in the road against the kerb line" counter: 0 by construction;
  `railing_error.py`'s to-source table is the independent reading.
- `classes` is a whitelist of code strings nothing published defines: a change is a
  `DATA_SOURCES.md` change. Split by class of object, never within one (`Q54`).
- A class is a parameterisation of `railings.gdshader`. `verify_railings.gd` checks the dispatch;
  a new class needs a row there, in `generated_scene_import.gd` and in config. A shader change
  owes a render and `grep -i "shader error"`.
- `ALPHA` is coverage, not translucency: no opacity dial.
- **Colliders** (`Q159`, `Q217`): the placer's, never the asset's — `city_layer.gd`'s `collides`
  stands `PropBatch.boxes`, one body a plan cell. `railings.glb` stays collider-free
  (`verify_railings.gd`). A moved fence is a moved wall: re-count panels across a road centreline
  at their own level (0 / 0).
