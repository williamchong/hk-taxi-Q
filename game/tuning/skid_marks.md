# skid_marks.tres

Tyre marks and smoke (`P3-57`): what the tyres are doing, whether or not the slide pays.
`SkidMarks` reads each wheel's combined slip off `TyreVehicleController.wheel_slips` (multiples of
the tyre's peak; 1.0 is the top of `tyre.tres`'s curve) and `SkidStrip` lays the marks. The sparks
that say a drift counts are `drift_sparks.tres`'s.

Every key is required: `skid_marks_profile.gd` declares no defaults and the rig refuses a zero
(`SkidMarks.usable`), except `smoke_rise_mps` and `smoke_spread_deg`, which may legally be 0.
`verify_vehicle.gd` asserts the scene hands the rig this file. Values are provisional, set by eye;
the user's look call is owed.

- `mark_from_slip = 1.2`: at 1.0 a car cornering at its limit marks every bend and reads as
  skidding.
- `mark_width_m = 0.17`: narrower than the wheel mesh.
- `lift_m = 0.04`: over the highest painted layer (the tram rail, 0.03) and the chord over a
  creased ribbon. A buried mark is answered here, never by raising the paint.
- `max_step_m = 2.0`: twice a wheel's travel per 60 Hz tick at 200 kph, so a fast slide is
  unbroken and a teleport or reset starts a new mark.
- `capacity = 2048`: pieces kept across all wheels, about 8.5 s of four wheels marking. 96 KB of
  vertex buffer, one draw call.
- `mark_colour`: near black at 0.55 alpha, so paint and road show under it.
- `smoke_from_slip = 2.0`: smoke is the hard end of what the marks show.
- `smoke_amount = 24`: puffs alive per rear wheel. Fill rate is a handset cost; `P0-3b` re-takes
  it.
- `smoke_lifetime_s = 1.2`: trails a slide without fogging the chase camera.
- `smoke_start_m = 0.25`, `smoke_end_m = 1.6`: tyre width at birth, car width as it fades. 0.35 at
  birth read as solid beads.
- `smoke_rise_mps = 0.8`, `smoke_spread_deg = 30.0`: a slow rise in a loose cone.
- `smoke_colour`: light grey at 0.3 alpha; 0.45 read as solid against the road.
