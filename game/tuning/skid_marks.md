# skid_marks.tres

Rationale for `game/tuning/skid_marks.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The tyre marks and the smoke (`P3-57`): what the tyres are doing, on the road, whether or not the
slide pays. `SkidMarks` (`scripts/vehicle/skid_marks.gd`) reads each wheel's combined slip off
`TyreVehicleController.wheel_slips` — forward and sideways together, in multiples of the tyre's
peak, so 1.0 is the top of `tyre.tres`'s curve — and `SkidStrip` lays the marks. The sparks that
say a drift COUNTS are `drift_sparks.tres`'s, off the tracker that pays.

⚠️ EVERY KEY BELOW IS REQUIRED. `skid_marks_profile.gd` declares no defaults, so a missing key reads
as zero, and the rig refuses to run on a zero (`SkidMarks.usable`). `smoke_rise_mps` and
`smoke_spread_deg` may legally be 0 — puffs that hang, or rise straight — so a missing one is not
guarded. `verify_vehicle.gd` asserts the scene hands the rig this very file and proves a zeroed
`mark_width_m` is refused.

Provisional: set by eye on the pad and the street, the user's look call to come (`P3-57`).

## `mark_from_slip = 1.2`

A fifth past the tyre's peak. At 1.0 a car cornering at its limit marks the road on every bend,
which reads as the car skidding when it is gripping; over 1.2 it is a slide, a wheelspin or a lock.

## `mark_width_m = 0.17`

The tread of a toy-scaled taxi tyre: narrower than the wheel mesh, so the mark sits inside it.

## `lift_m = 0.04`

Over the highest painted layer on the road — the tram bed at 0.02 with its rail 0.01 proud of it
(`hong_kong.yaml`'s `tramway`) — and the chord a piece makes over a creased ribbon. A mark buried
under the paint is answered by this value against the paint's own, never by raising the paint.

## `max_step_m = 2.0`

Twice what a wheel travels in a 60 Hz tick at 200 kph (0.93 m), so a fast slide is unbroken and a
teleport, a reset or a landing far from the take-off starts a new mark.

## `capacity = 2048`

Pieces kept, every wheel together: about 8.5 s of all four wheels marking at 60 Hz, more in
practice since the fronts seldom do. 2,048 × 4 corners × 12 bytes is 96 KB of vertex buffer, one
draw call.

## `mark_colour = Color(0.07, 0.07, 0.08, 0.55)`

Rubber on asphalt: near black, half through, so the paint and the road's colour show under it.

## `smoke_from_slip = 2.0`

Smoke is for a tyre well past its peak — a spin or a held slide — so it reads as the hard end of
what the marks already show.

## `smoke_amount = 24`

Puffs alive per rear wheel. Fill rate is a handset's cost; `P0-3b` re-takes it.

## `smoke_lifetime_s = 1.2`

Long enough to trail behind a slide, short enough not to fog the chase camera's view.

## `smoke_start_m = 0.25`

## `smoke_end_m = 1.6`

Born about the tyre's width and grown to a car's width as it fades. 0.35 at birth read as a
string of solid white beads behind the car on the street frame.

## `smoke_rise_mps = 0.8`

## `smoke_spread_deg = 30.0`

A slow rise in a loose cone: the car's own travel carries the trail.

## `smoke_colour = Color(0.92, 0.92, 0.92, 0.3)`

Light grey, mostly see-through at birth, fading to clear. 0.45 read as solid against the dark
road on the street frame.
