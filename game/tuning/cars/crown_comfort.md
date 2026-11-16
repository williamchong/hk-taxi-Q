# crown_comfort.tres

The Toyota Crown Comfort LPG, Hong Kong's taxi, as a `CarSpec` (`Q156`): the car's own numbers and
nothing about feel. The game layer is `handling.tres`, the systems' tables and `pace.tres`. A
second car is a second file here plus its wheel positions in a scene.

A real taxi is the baseline (the user's call): each number is the car's, or a typical figure for
its class where the maker's is unpublished. Forces are derived, never authored beside these
(`Q156`): the brake is `brake_g` of the weight, the handbrake `HandbrakeProfile.lock_ratio` of a
rear wheel's lock, a spring's ceiling `suspension_max_load_ratio` of a wheel's rest load.

- `steering_wheel` (`Q204`): the wheel the steering thumb is drawn as. Four spokes round a large
  horn pad (`hub_share` 0.36), no twelve o'clock stripe. Drawn from memory of the cab; a
  correction is an edit to `spokes_deg`. Physics never reads it.
- `mass_kg = 1400.0`: about 1,390 kg kerb, with a driver (`Q153`). Set on the body in
  `VehicleController._ready`.
- `centre_of_mass_offset_y = -0.35`: not measured; seeded for roll (`Q50`). The side force's
  height is `TyreProfile.side_force_depth`.
- `inertia_kgm2` (`Q190`): pitch, yaw, roll. Not measured: what Jolt derived from a
  1.695 × 0.7 × 4.0 m box at 1,400 kg, frozen so the collider's size is not a handling dial.
  Scale all three with a change of mass.
- `max_speed_kph = 140.0`, `max_reverse_kph = 40.0`: the limiter, a city ceiling under the car's
  own top speed (about 170). Scaled by `√pace`.
- `engine_force = 6000.0`, `engine_power_kw = 83.0`, `driveline_efficiency = 0.85`: the 1TR-FPE's
  83 kW and 186 N·m (`Q153`). 6,000 N at the tyres through typical ratios (first 2.8, final 4.3),
  then power over speed above about 42 kph.
- `drag_area_m2 = 0.72`: Cd about 0.36 on about 2.0 m², typical figures.
- `brake_g = 1.2`, `brake_front_share = 0.65`: a little over what the tyres can use, so the tyre
  and ABS set the stop (from 1.1 up nothing moves). A front-engined saloon's bias.
- `steer_angle_max_deg = 32.0`: lock at rest. Lock at speed is
  `HandlingProfile.steer_angle_at_top_deg` and `arcade_aids.steer_to_grip`.
- `wheel_radius_m = 0.31`: a 195/65 R15. `tools/make_vehicle.py` mirrors it.
- `suspension_rest_length_m = 0.39`, `suspension_travel_m = 0.18`: the rig's, not the car's sheet
  (`Q50`, `Q153`). `tools/ground_clearance.py` mirrors the travel.
- `suspension_frequency_hz = 2.2`, `suspension_damping_ratio = 0.55`: stiffer than a road car's
  1.5 Hz, for a flat arcade ride.
- `suspension_max_load_ratio = 4.0`: a spring may push with four times its wheel's rest load
  (13,720 N). Only wall clips reach it.
