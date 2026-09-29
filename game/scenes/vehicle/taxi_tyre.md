# taxi_tyre.tscn

Rationale for `game/scenes/vehicle/taxi_tyre.tscn`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The shipped taxi with `Q152`'s per-wheel tyre model on it (`P3-52`): an inherited scene of
`taxi.tscn`, so the body, the lamps, the door and the face are the shipped car's and only the
controller and its tyre table differ. A spike, graded on `skidpad_tyre.tscn`; nothing the game
loads points at it. A street drive fits the same model to `city_drive`'s own car instead, with
`drive.sh --tyres=`, so the scene's wiring stays the shipped one.

## `[node name="Taxi" instance=ExtResource("1_taxi")]`

`script` is `TyreVehicleController`, which extends `VehicleController` and keeps its `profile`
(`handling.tres`, inherited from `taxi.tscn`) for steering, the speed taper, coast drag, the wall
response and auto-righting. `tyre` is `tuning/tyre.tres`.
