# taxi_tyre.tscn

The game's car (`P3-52`, `Q152`): an inherited scene of `taxi.tscn` that swaps in the per-wheel
tyre controller and adds the player-only effects. `city_drive.tscn`, `skidpad.tscn` and
`greybox.tscn` instance this. `verify_vehicle.gd` grades it and refuses a drive scene that
instances another car.

- `Taxi`: `script` is `TyreVehicleController`, which extends `VehicleController` and keeps the
  inherited `profile` (`handling.tres`), `car` (`cars/crown_comfort.tres`) and `pace`. `tyre` is
  `tuning/tyre.tres`; the seven systems' tables are `tuning/systems/*.tres`.
- `SkidMarks` (`tuning/skid_marks.tres`), `DriftSparks` (`tuning/drift_sparks.tres`), `LightTail`
  (`tuning/light_tail.tres`): the tyre marks and smoke, the sparks that say a drift pays, and the
  lamps' trail. Each sidecar has the numbers.
- `CarOutline` (`P3-65`, `Q158`, `tuning/car_outline.tres`): writes the process-wide
  `outline_speed` global for the city's line and grows a rim on the body while a slide counts.
  Here and not in `taxi.tscn` because the player's car must be the one writer, and the base scene
  is what an AI car (`B3`) would instance. `TaxiHire` wires its tier as it does the sparks'.
