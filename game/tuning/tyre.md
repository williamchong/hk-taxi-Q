# tyre.tres

The per-wheel tyre model's table (`P3-52`, `Q152`), read by `TyreVehicleController` alone; the
game's car (`city_drive.tscn` instances `taxi_tyre.tscn`). The car's systems and the arcade aids
have their own tables under `tuning/systems/` (`Q155`). Grade any change on `tools/skidpad.sh` at
42, 63 and 86 kph; `Q152` and `Q153` hold the tables.

Required (no defaults in `tyre_profile.gd`; a zero parks the car, `TyreVehicleController.usable`):
`substeps`, `mu`, `slide_ratio`, `peak_slip_ratio`, `peak_slip_angle_deg`, `wheel_inertia_kgm2`,
`low_speed_mps`.

- `mu = 1.0` (`Q153`, the user's call): a road tyre. A real taxi is the baseline: the ease is the
  hidden aids' and the pace is `pace.tres`'s; a gameplay change goes on top, never by bending a
  physical number. At 2.0 the tyres held about 3.2 g, so a lift or a feint never moved the rear
  and no single dial gave a flick while `corner` gripped. At 1.0 the lifted flick slides on
  physics alone (44 / 48° at 42 / 63 kph). The drive and the handbrake torque must be sized for
  1.0: with 2.0's torques the tap and the flick spun 168–180°, and no stability dial answered it.
- `slide_ratio = 0.9`: the sliding tail of the curve. Of 0.5–0.9, the only value that held `hold`
  past 2 s at both 63 and 86 kph; at 0.6 the 86 kph slide spun.
- `peak_slip_ratio = 0.1`: where drive and brake force peak. Textbook, not swept.
- `peak_slip_angle_deg = 8.0`: a road tyre's cornering peak. A stiffer tyre (4–8 swept) scrubs
  less and moves `corner` the wrong way.
- `wheel_inertia_kgm2 = 1.2`: a 0.35 m wheel and tyre with a share of the drivetrain. Sets how
  fast a wheel spins up, not stability (the spin solve is implicit).
- `low_speed_mps = 3.0`: slip is measured against at least this, so a car at rest does not read an
  infinite slip.
- `substeps = 8`: the spin solve's steps a tick (times `√pace`). At 8 the residual stays monotone;
  fewer may bisect.
- `side_force_depth = 0.7`: where the sideways force goes in, 0 at the centre of mass's height, 1
  at the contact. At 0.6 and below a player's input does not slide at 42 or 63 kph; at 1.0 the car
  rolled onto its side at a kerb on Expo Drive. 0.7 is the least that slides at all three speeds.
  Named apart from `roll_influence` because a sweep resolves a field by name across tables.
