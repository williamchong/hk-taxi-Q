# vehicle_lamps.tres

The taxi's lamp dials (`P3-11d`; data since `Q150`): indicators, roof sign, tail lamps, the light
probe that runs the lighting ladder, and the side lamps' share of the beam. A lamp's brightness
and reach are the fitting's, authored in `taxi.tscn`; this file is what the state does to them.
(`lamps.tres` is the street lamps' material.)

Every key is required (`vehicle_lamps_profile.gd` declares no defaults). The rig refuses to run on
a zero `blink_hz`, `blink_duty`, `sun_probe_m`, `cover_probe_m` or `probe_hz`
(`VehicleLamps.usable`). The others may legally be 0, so a missing one is not guarded.
`verify_vehicle.gd` asserts the scene hands the rig this resource.

- `blink_hz = 1.5`: regulation puts an indicator between 1 and 2 Hz.
- `blink_duty = 0.55`: over a half, so a small lamp seen from behind reads as a light.
- `steer_threshold = 0.35`: a share of the lock available at this speed
  (`VehicleController.steer_ratio`), since full lock at speed is a fraction of full lock parked.
  Near zero the indicators strobe through every straight-line correction.
- `steer_hold_s = 0.3`: how long the steer must hold before the indicator lights, so a flick or a
  drift correction does not strobe the tail. The lamp is late by this much. 0.3, not 0.5, on the
  user's call: it read as late from the chase camera.
- `alight_hazards_s = 3.0` (`Q187`): how long the hazards flash after a drop-off. While boarding
  they run until the passenger is seated or walks away. Covers the door's swing, hold and swing
  back (1.5 s) with time to step clear.
- `sign_lit = 0.45`: how bright the roof sign burns when lit. Whether it is lit is `for_hire`
  alone, written by `TaxiHire`. A level under the bloom knee (about 0.63, with `lamp_emission`
  1.6 against a glow threshold of 1.0): at full it read as a headlamp bolted to the roof. Do not
  tie it to daylight.
- `tail_lit = 0.35` (`Q160`): with the front lamps on, the brake lenses burn at this share.
  0.35 × 1.6 is under the glow threshold, so braking still gains the bloom.
- `sun_probe_m = 200.0`: the sun ray's length. Bounded by where collision exists (only the finest
  tile tier has colliders, inside `streaming.tres`'s 250 m); a longer ray passes through
  coarse tiles and reports sun. Too short for a caster over about 115 m at a 30° sun; raising it
  cannot fix that.
- `cover_probe_m = 25.0`: asks whether something is over the car (a road deck, an overhang).
  Longer finds the upper storeys of a building overhanging the kerb and puts the taxi on main beam
  in open sun.
- `probe_height_m = 1.0`: rays start clear of the car's own roof.
- `probe_hz = 10.0`: several samples inside the shortest hold. A probe costs about three wheel
  rays. Every car probes on the same tick; a random phase is refused because driver runs are
  byte-deterministic. Stagger from something stable (node path, spawn index) if it ever matters.
- `dark_hold_s = 0.35`, `light_hold_s = 1.6`: the asymmetry is the anti-flicker mechanism. Late
  into the dark is what a driver notices; a street is a picket fence of shadow, so the lamps
  linger on the way out.
- `sidelamp_beam = 0.3`: what the `SHADOW` state does to the authored beam. Position lamps are to
  be seen, not to see by: a short dim pool.
- `night_energy = 0.4` (`Q160`): a key light under this energy is night. Between the night
  keyframe's moon (0.30) and the dusk sun (0.80), so main beams come on part-way down the dusk.
  `verify_day_cycle.gd` holds the last keyframe under it.
