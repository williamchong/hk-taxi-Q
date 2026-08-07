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
## The model is a custom raycast vehicle on RigidBody3D, not Godot's
## VehicleBody3D and not a physical simulation. P0-5a measured why: see
## docs/DECISIONS.md, P0-5a. See also docs/GAME_DESIGN.md "Controls".

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
## Lateral grip multiplier applied to the REAR axle while drift is held.
## Low: the tail must actually step out.
@export_range(0.0, 1.0, 0.01) var drift_grip_scale: float
## Lateral grip multiplier applied to the FRONT axle while drift is held.
## Deliberately much higher than the rear. Scaling both equally can only make
## a four-wheel slide — the car ploughs wide instead of rotating, which reads
## as "the road got icy" rather than "I am drifting". The front has to keep
## enough grip to still point the car.
@export_range(0.0, 1.0, 0.01) var drift_front_grip_scale: float
## Slip angle above which the drift scores style points.
@export_range(0.0, 90.0, 1.0, "suffix:°") var drift_slip_threshold_deg: float
## Fraction of speed lost per second while drifting. Deliberately small —
## drifting must not feel like a penalty.
@export_range(0.0, 1.0, 0.01) var drift_speed_scrub_per_s: float

## Fraction of rolling speed shed per second when coasting — engine braking.
## Small values glide, large values stop the car the moment you lift off.
@export_range(0.0, 1.0, 0.01) var coast_drag_per_s: float

@export_group("Collision and recovery")
## 0 = head-on stop, 1 = full glancing deflection. Glancing hits deflect;
## head-on hits cost speed, never control.
@export_range(0.0, 1.0, 0.01) var collision_deflection: float
## Fraction of speed retained after a head-on impact.
@export_range(0.0, 1.0, 0.01) var collision_speed_retained: float
## Seconds before an upside-down car auto-rights itself.
@export_range(0.0, 5.0, 0.05, "suffix:s") var auto_right_delay_s: float

@export_group("Suspension")
## Chassis layout (wheelbase, track, mount points) is deliberately NOT here:
## that is per-vehicle model data and belongs to the vehicle scene. Wheel radius
## is the one exception, because the suspension ray length is derived from it.
@export_range(0.1, 1.0, 0.01, "suffix:m") var wheel_radius_m: float
## Uncompressed spring length, measured from the mount point down to the hub.
## It does NOT include the wheel: the ray cast to find the ground is
## suspension_rest_length_m + wheel_radius_m.
@export_range(0.05, 1.0, 0.01, "suffix:m") var suspension_rest_length_m: float
## Maximum compression from rest before the spring bottoms out.
## Must not exceed suspension_rest_length_m.
@export_range(0.01, 0.6, 0.01, "suffix:m") var suspension_travel_m: float
## Spring rate expressed as natural frequency, not a raw N/m constant.
## Deliberate: frequency is mass-independent, so retuning vehicle mass or
## swapping in a heavier vehicle does not silently change how the car rides.
## Road cars sit near 1.5 Hz; arcade wants stiffer and flatter.
##
## It is NOT gravity-independent. Static sag is g_eff / (2πf)², so raising
## gravity_scale deepens sag and eats the bump travel that absorbs kerbs and
## jump landings. Scale this by √gravity_scale to hold ride height: the seeded
## 2.8 Hz is 2.2 Hz compensated for gravity_scale 1.6.
@export_range(0.5, 5.0, 0.05, "suffix:Hz") var suspension_frequency_hz: float
## 1.0 is critically damped. Below 1.0 allows a little bounce, above is sluggish.
@export_range(0.0, 2.0, 0.01) var suspension_damping_ratio: float
## Artificial anti-roll torque, 0 = none, 1 = rigid. A lowered centre of mass
## alone does not stop the car rolling over; this is the arcade dial that does,
## without pinning the body flat and killing the sense of weight.
@export_range(0.0, 1.0, 0.01) var anti_roll: float

@export_group("Body")
## Downward offset of the centre of mass from the body origin. Lower = less roll.
@export_range(-2.0, 2.0, 0.01, "suffix:m") var centre_of_mass_offset_y: float
## Above 1.0 shortens air time and lands jumps flatter.
@export_range(0.0, 5.0, 0.05) var gravity_scale: float


## How far a suspension ray reaches below its hardpoint — the car's ride height
## with the springs fully extended.
##
## The only function on an otherwise pure schema, and it is here rather than on
## VehicleController for two reasons. It is a fact about the profile, which
## suspension_rest_length_m already states in prose. And it has to be reachable
## from a headless --script tool: VehicleController reads the InputRouter
## autoload, autoloads are not registered under --script, and so anything that
## touches it there fails to compile. tools/verify_spawn.gd needs this number to
## check the drop height and must not drag the controller in to get it.
func ray_length_m() -> float:
	return suspension_rest_length_m + wheel_radius_m
