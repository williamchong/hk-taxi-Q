# prop_cells.tres

Rationale for `game/tuning/prop_cells.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

Which prop layers `layer_preview.gd` stands as a `MultiMesh` per plan cell, and how far a cell is
drawn (`P3-67`, `Q135`). A region-wide `MultiMesh` is one box: the engine draws every instance from
anywhere inside it, and again in each shadow cascade.

⚠️ EVERY KEY BELOW IS REQUIRED. `prop_cell_profile.gd` declares no defaults; `layer_preview.gd`
refuses a zero cell and `verify_city.gd` refuses a zero cell or range, or an unknown layer, by name.

## layers = PackedStringArray("lamps")

The lamps alone. One library mesh, so a cell costs one draw call a pass: 129,240 of ~900,000
primitives on the throttle route came back to ~10,000 for +2 draw calls.

🚫 **Not the signs.** 23 library meshes a region is 23 draw calls a visible cell: +65 to +94 on the
throttle route, measured. Their cost is draw calls, answered by `shadow_meshes` (`P3-66`).

Railings and arrows are unmeasured; a layer joins this list with its own before and after.

## cell_m = 300.0

The paint's cell (`road_marks.cell_m`). 150 m bought −105k primitives against 300 m's −93k for
+20 to +35 draw calls against +10 to +11, range aside.

## range_m = 400.0

The chase camera's far plane and `streaming.tres`'s `unload_distance_m`. ⚠️ Measured to the centre
of the cell's box, so a lamp up to half a cell's diagonal nearer than this can be hidden — a 90 mm
column a third of a pixel wide at 250 m. Five fixed cameras, each side shot twice: 1 px moves by
more than 16 levels. What a drive shows as the cell lets go is the user's to judge.

Without the range a cell still costs a shadow pass each: +10 to +11 draw calls for 26k fewer
primitives saved.

## range_margin_m = 15.0

`streaming.tres`'s `hysteresis_m`, for its reason: a cell on the edge must not flicker.
