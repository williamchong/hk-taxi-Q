# skidpad.tscn

Rationale for `game/scenes/dev/skidpad.tscn`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

A measuring instrument, not a place to play: the greybox ground with the car
parked well clear of every building, so a handling number is not cut short by
a wall.

⚠️ **The spawn is the whole point of this file.** `greybox.tscn` starts the car
at (-250, -150), which is inside the road network — `greybox_wanchai.json`'s
segments span x ±300 by z ±150 and its buildings are set back from those, so a
car that turns is into a block within about 40 m. Measured: a drift run there
went 54 kph to 0 in 0.25 s across 0.5 m of travel, which reads in the telemetry
exactly like a spin and is not one. This spawn sits at z −500, some 350 m clear
of the nearest segment on 1600 m of ground.

⚠️ Since `Q50` the car this grades IS a `VehicleBody3D`, so the paired
`skidpad_builtin.tscn` that used to sit beside this one is gone — it would now
be a second copy of the same vehicle model. `tools/skidpad.sh --scene=` still
takes a path, for when the roster has a second car worth grading here.

## `[node name="Taxi" parent="." instance=ExtResource("2_taxi")]`

Facing +X, the same basis `greybox.tscn` uses. Row-major, and forward is the
-Z column — do not rewrite these from a direction.
