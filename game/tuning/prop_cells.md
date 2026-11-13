# prop_cells.tres

Rationale for `game/tuning/prop_cells.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

Which prop layers `layer_preview.gd` stands as a `MultiMesh` per plan cell, and how far a cell is
drawn (`P3-67`, `Q135`). A region-wide `MultiMesh` is one box: the engine draws every instance from
anywhere inside it, and again in each shadow cascade.

⚠️ EVERY KEY BELOW IS REQUIRED. `prop_cell_profile.gd` declares no defaults; `layer_preview.gd`
refuses a zero cell and `verify_city.gd` refuses a zero cell or range, or an unknown layer, by name.

## layers = PackedStringArray("lamps", "trees", "railings")

The lamps: one library mesh, so a cell costs one draw call a pass: 129,240 of ~900,000
primitives on the throttle route came back to ~10,000 for +2 draw calls.

The trees (`P3-77`): four library meshes, so up to four draw calls a visible cell a pass, against
58,144 / 132,040 placed triangles on Wan Chai / Causeway Bay that a region-wide `MultiMesh` would
draw from anywhere, three times over with the shadow cascades. Their trunk bodies are cut on the
same cells (`layer_preview._stand_trunks`).

🚫 **Not the signs.** 23 library meshes a region is 23 draw calls a visible cell: +65 to +94 on the
throttle route, measured. Their cost is draw calls, answered by `shadow_meshes` (`P3-66`).

The railings (`P2-6`): three region-wide meshes cost 65k primitives at every view. Cut, they came
back −89k / −70k / −71k at the start line, Hennessy Road and Times Square, for −1 / +2 / +11 draw
calls — a class is several library meshes, so a cell is several draws a pass. They cast no shadow
since the same change (`generated_layer.gd`), which takes two of the three passes away: together
−127k / −90k / −97k and −7 / −3 / −2 draws, against the fence already cut. A sunlit frame of the
harbour railings could not tell the two apart (0.14% of pixels, 0.04% run to run).

Arrows are unmeasured; a layer joins this list with its own before and after.

**Read beyond this list.** `layers` names `layer_preview.gd`'s layers only; two placers outside that
table cut on the same `cell_m` and `range_m` unconditionally: `signal_heads.gd`, and the fence
(`fence.gd`, `P2-6`). The fence was one region-wide `MultiMesh`, and turning its shadow off alone
saved 121k primitives at each of three views, the start line, Hennessy Road and Times Square.

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
