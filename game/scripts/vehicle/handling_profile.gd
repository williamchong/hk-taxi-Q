class_name HandlingProfile
extends Resource
## Arcade vehicle feel, as data.
##
## CLAUDE.md hard rule 4: tuning values are data, never constants in code.
## This script declares the schema and nothing else — the numbers live only in
## game/tuning/handling.tres. Deliberately no defaults here: a profile that was
## never assigned reads as all-zeroes and fails loudly, rather than quietly
## driving on values buried in a script.
##
## The model is a Jolt raycast vehicle with arcade overrides, not a physical
## simulation. See docs/GAME_DESIGN.md "Controls".

@export_group("Speed")
## Top speed in forward gear.
@export_range(0.0, 300.0, 1.0, "suffix:km/h") var max_speed_kph: float
## Reverse is instant — no gear delay.
@export_range(0.0, 100.0, 1.0, "suffix:km/h") var max_reverse_kph: float
## Engine force applied per wheel at full throttle.
@export_range(0.0, 5000.0, 10.0) var engine_force: float
@export_range(0.0, 5000.0, 10.0) var brake_force: float

@export_group("Steering")
## Steering angle at standstill.
@export_range(0.0, 60.0, 0.5, "suffix:°") var steer_angle_max_deg: float
## Steering angle at max_speed_kph. Lower keeps the car stable at speed.
@export_range(0.0, 60.0, 0.5, "suffix:°") var steer_angle_at_top_deg: float
## Seconds to reach full lock from centre.
@export_range(0.01, 1.0, 0.01, "suffix:s") var steer_attack_s: float
## Seconds to return to centre when input is released.
@export_range(0.01, 1.0, 0.01, "suffix:s") var steer_release_s: float

@export_group("Grip")
## Lateral grip multiplier. High and forgiving — no spin-outs from small errors.
@export_range(0.0, 5.0, 0.05) var grip_lateral: float
## Traction under power and braking.
@export_range(0.0, 5.0, 0.05) var grip_longitudinal: float

@export_group("Drift")
## Lateral grip multiplier applied while the drift button is held.
@export_range(0.0, 1.0, 0.01) var drift_grip_scale: float
## Slip angle above which the drift scores style points.
@export_range(0.0, 90.0, 1.0, "suffix:°") var drift_slip_threshold_deg: float
## Fraction of speed lost per second while drifting. Deliberately small —
## drifting must not feel like a penalty.
@export_range(0.0, 1.0, 0.01) var drift_speed_scrub_per_s: float

@export_group("Collision and recovery")
## 0 = head-on stop, 1 = full glancing deflection. Glancing hits deflect;
## head-on hits cost speed, never control.
@export_range(0.0, 1.0, 0.01) var collision_deflection: float
## Fraction of speed retained after a head-on impact.
@export_range(0.0, 1.0, 0.01) var collision_speed_retained: float
## Seconds before an upside-down car auto-rights itself.
@export_range(0.0, 5.0, 0.05, "suffix:s") var auto_right_delay_s: float

@export_group("Body")
## Downward offset of the centre of mass from the body origin. Lower = less roll.
@export_range(-2.0, 2.0, 0.01, "suffix:m") var centre_of_mass_offset_y: float
## Above 1.0 shortens air time and lands jumps flatter.
@export_range(0.0, 5.0, 0.05) var gravity_scale: float
