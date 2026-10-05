class_name StabilityControlProfile
extends Resource
## Stability control's power cuts (`Q155`): a real car's ESC takes engine
## torque away when the car runs wide or its tail swings out. This one cuts
## power only; a real ESC also brakes single wheels, which this does not
## model. Read by `TyreVehicleController`; why each value is what it is lives
## in `tuning/systems/stability_control.md`. No defaults (`Q119`).

## Share of the forward drive taken off at full lock while traction control is
## armed, in proportion to the front wheels' angle over the lock the speed
## allows: 0 leaves the drive alone, 1 leaves none at full lock. Drift mode
## disarms it with traction control, so a slide never sees it (`P3-55`).
@export_range(0.0, 1.0, 0.05) var understeer_power_cut: float
## The body slip over which the forward drive fades out while drift mode is on:
## whole at `slip_power_cut_from_deg`, gone at `slip_power_cut_to_deg`. A
## ceiling on the power that feeds a slide, so a held throttle cannot spin the
## car; under the band the slide is the player's. Inert while `to` is not over
## `from`.
@export_range(0.0, 90.0, 1.0, "suffix:°") var slip_power_cut_from_deg: float
@export_range(0.0, 90.0, 1.0, "suffix:°") var slip_power_cut_to_deg: float
## The body slip over which the forward drive fades out on the road — drift
## mode off — as a real ESC catches a tail stepping out under power: whole at
## `armed_slip_cut_from_deg`, gone at `armed_slip_cut_to_deg`. The game's pace
## boost (`ArcadeAidsProfile.drive_boost`) put the rears past their grip in a
## full-throttle corner at 42–50 kph. Inert while `to` is not over `from`.
@export_range(0.0, 90.0, 0.5, "suffix:°") var armed_slip_cut_from_deg: float
@export_range(0.0, 90.0, 0.5, "suffix:°") var armed_slip_cut_to_deg: float
