# taxi.tscn

The taxi's base scene: body, lamps, door, passenger face and wheels. Not driven on its own (its
controller has no tyre force); `taxi_tyre.tscn` inherits it. A `VehicleBody3D` with four
`VehicleWheel3D` children (`Q50`).

Traps:

- A `VehicleWheel3D` must be a direct child of the `VehicleBody3D`. The engine silently ignores a
  nested one, and `vehicle_controller.gd` matches that rule.
- The tyre mesh must stay named `taxi_tyre.glb`. Godot's glTF importer turns any node whose name
  ends in `_wheel` into a `VehicleWheel3D`, which would nest a wheel in a wheel
  (`docs/ARCHITECTURE.md`, "The importer can reinstate VehicleWheel3D").

## Nodes

- `Taxi`: `profile` is `handling.tres`, `car` is `cars/crown_comfort.tres`, `pace` is `pace.tres`.
  `linear_damp_mode = 1` (replace) with `linear_damp` 0: the body has no damping of its own
  (`Q153`). The project default 0.1 held the real taxi under 80 kph. Air drag and the coast terms
  replace it.
- `Body` and `BoxShape3D_body`: 1.695 × 0.7 × 4.575 m, set 0.2175 m back (`Q190`), bumper to
  bumper over the visual body (z −2.07 to +2.505; `make_vehicle.Proportions`' `length_m` and
  `body_offset_z_m` plus the bars). Move the body in the generator and this box moves by hand.
  - The width is a Crown Comfort's (`Q153`) and is mirrored, not read, in `hong_kong.yaml`'s
    `clearance.car_width_m` and the `CAR_WIDTH_M` defaults of `tools/narrowing.py`,
    `reachability.py` and `centreline_error.py`. Change all together, rebuild and re-sync.
  - The height is not the real car's. Inertia is authored (`crown_comfort.tres` `inertia_kgm2`),
    so the box's size moves what the car hits, not how it turns. The trams' `taxi_half_m` is the
    further bumper.
- `Mesh` (`taxi_body.glb`, `vehicle_lamps.gd`, `tuning/vehicle_lamps.tres`): the lamp rig rides on
  the body mesh because the circuits are per-instance shader state on the `MeshInstance3D` inside
  the glb.
- `PassengerDoor` (`taxi_door.gd`, `tuning/taxi_door.tres`, `P3-48`): the rear kerbside door. The
  node is the hinge: its origin is the doorway's front edge on the flank, so the swing is its
  rotation about y. The origin is a hand copy of `make_vehicle.door_hinge` (x the kerb side's
  `half_width_m`, z `cabin_mid_z_m`); `etl/tests/test_make_vehicle.py` binds the two. Which way is
  out is read off the sign of x. Kerb side is left (−x): Hong Kong drives on the left, and only
  the rear door opens. No collider: an open leaf must not change how the car drives.
  - `Leaf` (`taxi_door.glb`, from `tools/make_vehicle.py`): renders with `vehicle_body.tres`. It
    carries no lamp; `VehicleLamps` takes the first mesh under `Mesh`.
- `PassengerEmote` (`passenger_emote.gd`, `tuning/passenger_emote.tres`, `P3-49`, `Q145`): the
  rear kerbside seat, where a face (`grin`, `angry`, `hurt`) rises through the roof. Origin
  (−0.45, 0.55, 0.8): on the door's side, behind the hinge and ahead of `cabin_rear_z_m` 1.74, so
  the roof hides the face at the pop. `verify_vehicle.gd` holds that. No collider, unshaded.
- `HeadlampL`, `HeadlampR` (`SpotLight3D`, x ±0.58, the lenses' x in `tools/make_vehicle.py`): the
  light the headlamps throw, switched by `vehicle_lamps.gd`. This node owns brightness and reach:
  the script reads `light_energy` and `spot_range` once in `_ready` and only scales them by
  `sidelamp_beam`.
  - Two cones, not one central spot: the twin roots at the bumper are what reads as a car.
  - `spot_angle = 13` is a half angle, read with the 14° down tilt: the cone's top edge must stay
    below horizontal or the beam climbs the screen as a dome. `tools/verify_vehicle.gd` checks it.
    13 also keeps the two pools apart to about 2.5 m; 15 and 22 merged them.
  - `spot_angle_attenuation = 2.2` softens the rim; `spot_attenuation = 0.9` fades the far end.
  - Shadows stay off (the engine default, so not in the file): `ART_DESIGN.md` allows no realtime
    shadow maps on the mobile tier.
  - `distance_fade` at 35 m frees a light slot: Forward Mobile pairs at most 8 spot lights per
    rendered object and silently drops the 9th. It bounds the competitors; `BeamBudget` is the
    nearest-N rule that caps them (`P3-11e`).
- `SunGlint` (`sun_glint.gd`): feeds `vehicle_body.tres` the scene's real sun direction, so the
  glint holds no second copy of the rig's rotation.
- `WheelFL`, `WheelFR`, `WheelRL`, `WheelRR`: geometry and role only. The controller writes the
  suspension from `cars/crown_comfort.tres` at `_ready`, and `TyreVehicleController` zeroes the
  engine's friction. The controller splits axles by position along the chassis, not by these
  roles (`VehicleController._group_axles`). Each `Visual` is `taxi_tyre.glb`, positioned, rolled
  and steered by its wheel.
