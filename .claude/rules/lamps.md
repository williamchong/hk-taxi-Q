---
paths:
  - "etl/pipeline/config_blocks/lamps.py"
  - "etl/pipeline/lamps.py"
  - "etl/tests/test_lamps.py"
  - "game/tools/verify_lamps.gd"
  - "game/tuning/lamps.{tres,md}"
  - "game/tuning/lamp_pools.{tres,md}"
  - "game/scripts/city/lamp_pools.gd"
  - "game/assets/shaders/lamp_pool.gdshader"
  - "game/tuning/prop_cells.{tres,md}"
  - "game/scripts/city/prop_cell_profile.gd"
---

# Lamp posts — before marking work done

The stage grades itself: every failure renders as a well-drawn lamp post or as nothing.

- **`pipeline/lamps.py`, the `lamps` block, any lamp change**: `tools/battery.py lamps --region
  <r> --before <root>`, both regions. From `lamps.json` compare the two partitions,
  `min_kerb_clearance_m`, `shift_m` (with `n`), `lantern_overhang_m`, `lanterns_past_centreline`,
  `spacing_surveyed_m` against `spacing_drawn_m`, `gaps_over_report_m`, `facing_away`, `on_deck`,
  `shortened`, `under_structure`, `in_carriageway`, `in_carriageway_area`. A/B render one street
  at a fixed camera, twice a side, by day and at `--time-of-day=1` (`Q62`: the facing cannot be
  graded against anything published).
- **No column in the road** is `min_kerb_clearance_m`, resting on three refusals: `_register`
  clears the host kerb; a second pass re-snaps the placed point against every edge (delete it and
  every counter stays green with columns in junction mouths); and the foot is tested against the
  asphalt itself (`drawnroad.drawn_carriageway`, `Q237`), because a kerb station inside a junction
  is a share (`Q57`). Deck columns are exempt. A change to R or its islands moves which columns
  stand. Do not iterate the push (`Q78`, measured on the signs: worst shift 5.52 → 16.77 m).
- No `arms_against_kerb` counter: the arm is derived from the kerb side, so it reads 0 by
  construction (`Q72`). `lanterns_past_centreline` is reachable by raising `arm_reach_m`.
- `lamps._strut`'s prism ring is not reversed, unlike `signs._draw_pole`'s: a bracket arm is not
  vertical. Copying the reversal inverted 25,116 of 35,880 triangles.
- `shift_m` is recorded over refusals too (`n` > `drawn`, `Q58`). The outward-only clamp (`Q78`)
  applies here and not in `railings.py`.
- A widening moves the drawn kerb and every column. Quote both spacing distributions: a refusal
  is a hole in a row.
- **Decks and roofs** (`Q199`): no elevation is published, so a lamp inside an elevated edge's
  drawn ribbon (or within `outset_m` of its kerb) is hosted to the deck and takes `deck_outset_m`,
  pulled in as well as pushed out (at `outset_m` 53 of 81 stood on air). Tunnels are not decks.
  Under any other drawn face between `overhead_clear_m` and its top (`trees.shipped_faces`), a
  column is stood shorter (`soffit_gap_m`) and refused only under `min_column_height_m`. Shorter
  is the stand's `Y` scale, not a second mesh. `lamps` runs after `carve`, and a `materials:`
  ground colour moves `under_structure`. Frames: `--spawn-at=734,12.3,407
  --spawn-facing=743,12,457 --fares=off --traffic=off --trams=off`, and `city_preview.tscn
  --camera=1535,9,400 --look=1575,7,450`. Open: a few deck columns stand just off the slab.
- **Light** (`Q160`): the lantern is lit at night only — `lantern_glow` times the rig's
  `night_lights`, on faces the ETL marks with `COLOR_0` alpha 0 (`library_lit_vertices`);
  `lamp_pools.tres` throws the pool. Do not raise `sheeting_glow`: it lights the whole column at
  noon.
- The colour is in `materials:` (`Q33`). The shader is shared with the signs: render both and
  `grep -i "shader error"`.
- **Import** (`Q82`): mesh compression is off in `project.godot`'s `[importer_defaults]`, pinned by
  `check.sh`'s `settings` step. It seeds only a new `.import`: delete the sidecars and re-import
  after changing it. `verify_lamps.gd`'s upright bar is a lay-flat detector; do not tighten it.
- **`prop_cells.tres` (`layers`, `cell_m`, `range_m`), `city_layer._batches`** (`P3-67`): the
  throttle route and `--spawn-fare=wan_chai/f_045` with overlays, HUD and fares off; `prims` and
  `draws` before and after, from runs whose `pos` column matches; the five fixed cameras in
  `Q135`. Lamps are a `MultiMesh` per cell, hidden by distance to the cell's centre. The signs do
  not join the list (+65 to +94 draws).
- **Colliders** (`Q191`): `region.tscn`'s `posts` stands a cylinder off the library mesh's foot, so
  a kind must be drawn standing on its origin (`check_posts`). Never a collider in `lamps.glb`.
