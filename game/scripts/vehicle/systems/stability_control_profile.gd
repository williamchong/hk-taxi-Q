class_name StabilityControlProfile
extends Resource
## Stability control (`Q155`): a real car's ESC takes engine torque away when
## the car runs wide or its tail swings out, and brakes one wheel to turn the
## car back (the yaw brake, `Q156`). Read by `TyreVehicleController`; why each value is what it is lives
## in `tuning/systems/stability_control.md`. No defaults (`Q119`).

## Share of the forward drive taken off at full lock while traction control is
## armed, in proportion to the front wheels' angle over the lock the speed
## allows: 0 leaves the drive alone, 1 leaves none at full lock. Drift mode
## disarms it with traction control, so a slide never sees it (`P3-55`).
@export_range(0.0, 1.0, 0.05) var understeer_power_cut: float
## The rear-axle slip over which the forward drive fades out while drift mode is on:
## whole at `slip_power_cut_from_deg`, gone at `slip_power_cut_to_deg`. A
## ceiling on the power that feeds a slide, so a held throttle cannot spin the
## car; under the band the slide is the player's. Inert while `to` is not over
## `from`.
@export_range(0.0, 90.0, 1.0, "suffix:°") var slip_power_cut_from_deg: float
@export_range(0.0, 90.0, 1.0, "suffix:°") var slip_power_cut_to_deg: float
## The rear-axle slip over which the forward drive fades out on the road — drift
## mode off — as a real ESC catches a tail stepping out under power: whole at
## `armed_slip_cut_from_deg`, gone at `armed_slip_cut_to_deg`. The game's pace
## boost (`ArcadeAidsProfile.drive_boost`) put the rears past their grip in a
## full-throttle corner at 42–50 kph. Inert while `to` is not over `from`.
@export_range(0.0, 90.0, 0.5, "suffix:°") var armed_slip_cut_from_deg: float
@export_range(0.0, 90.0, 0.5, "suffix:°") var armed_slip_cut_to_deg: float
## The yaw brake: once the rear axle's slip is past `yaw_brake_from_deg`, the
## front wheel on the outside of the slide is braked, up to
## `yaw_brake_lock_ratio` of the torque that locks a wheel at rest by
## `yaw_brake_to_deg` — a real ESC's oversteer intervention (and the slip
## ceiling of a real drift mode: Ferrari's SSC, McLaren's VDC). The force is
## the braked tyre's own, through the spin solve, so it can never exceed the
## grip that wheel has. Drift mode does NOT stand it down: under the band the
## slide is the player's, past it the car is spinning. A ratio of 0, or a `to`
## not over `from`, is off.
@export_range(0.0, 3.0, 0.05) var yaw_brake_lock_ratio: float
@export_range(0.0, 90.0, 0.5, "suffix:°") var yaw_brake_from_deg: float
@export_range(0.0, 90.0, 0.5, "suffix:°") var yaw_brake_to_deg: float
