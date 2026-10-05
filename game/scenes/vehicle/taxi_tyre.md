# taxi_tyre.tscn

Rationale for `game/scenes/vehicle/taxi_tyre.tscn`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The taxi with `Q152`'s per-wheel tyre model on it (`P3-52`): an inherited scene of `taxi.tscn`,
so the body, the lamps, the door and the face are that car's and only the controller and its tyre
table differ. Built as a spike and graded on `skidpad_tyre.tscn`; the game's car since 2026-10-03
(`Q152`), when `city_drive.tscn` took it in place of `taxi.tscn`, and the only car since
2026-10-05, when the engine-tyre control and its drift code were dropped. `taxi.tscn` stays the
base scene and is not driven on its own: its controller has no tyre force. `skidpad.tscn` and
`greybox.tscn` instance this scene. `verify_vehicle.gd` grades it and refuses a drive scene that
instances another.

## `[node name="Taxi" instance=ExtResource("1_taxi")]`

`script` is `TyreVehicleController`, which extends `VehicleController` and keeps its `profile`
(`handling.tres`, inherited from `taxi.tscn`) for steering, the speed taper, coast drag, the wall
response and auto-righting. `tyre` is `tuning/tyre.tres`.
