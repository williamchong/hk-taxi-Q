# skidpad_tyre.tscn

Rationale for `game/scenes/dev/skidpad_tyre.tscn`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

`skidpad.tscn` with `taxi_tyre.tscn` in the Taxi's place (`P3-52`, `Q152`): the same ground, spawn,
sun and camera, so the spike and the shipped car are graded on one pad. `skidpad.md` carries the
reasoning for everything but the car. Graded with
`tools/skidpad.sh --scene=res://scenes/dev/skidpad_tyre.tscn --entry-kph=63`.

## `[node name="Taxi" parent="." instance=ExtResource("2_taxi")]`

The shipped pad's transform and `sun`, unchanged — see `skidpad.md`.
