# prop_cells.tres

Which prop layers `city_layer.gd` stands as a `MultiMesh` per plan cell, and how far a cell is
drawn (`P3-67`, `Q135`). A region-wide `MultiMesh` is one box the engine draws from anywhere
inside it, and again in each shadow cascade.

Every key is required: `prop_cell_profile.gd` declares no defaults. `city_layer.gd` refuses a zero
cell; `verify_city.gd` refuses a zero cell or range, or an unknown layer.

- `layers = ["lamps", "trees", "railings"]`: lamps are one library mesh (one draw a cell a pass);
  trees four, with trunk bodies cut on the same cells (`city_layer._stand_trunks`); railings
  several per class, and they cast no shadow (`generated_layer.gd`).
  - Not the signs: 23 library meshes a region is 23 draws a visible cell, +65 to +94 draw calls on
    the throttle route. Their cost is answered by `shadow_meshes` (`P3-66`).
  - Arrows are unmeasured. A layer joins with its own before and after.
  - `signal_heads.gd` and `fence.gd` cut on the same `cell_m` and `range_m` unconditionally; they
    are not in this list.
- `cell_m = 300.0`: the paint's cell (`road_marks.cell_m`). 150 m saved 105k primitives against
  300 m's 93k, for +20 to +35 draw calls against +10 to +11.
- `range_m = 400.0`: the chase camera's far plane and `streaming.tres`'s `unload_distance_m`.
  Measured to the centre of the cell's box, so a prop up to half a cell's diagonal nearer can be
  hidden. Without a range a cell still costs a shadow pass.
- `range_margin_m = 15.0`: `streaming.tres`'s `hysteresis_m`, so an edge cell does not flicker.
