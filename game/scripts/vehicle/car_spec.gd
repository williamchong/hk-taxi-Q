class_name CarSpec
extends Resource
## One car's own numbers, as data: what a maker's sheet or a tape measure says
## about it, and nothing about how the game should feel. The game layer is
## `HandlingProfile` (steering ramps, the drift's threshold, the wall response)
## and `PaceProfile`; the car's systems are the tables under `tuning/systems/`.
##
## A second car is a second one of these and its wheels' positions in a scene.
## Forces a car's size decides are DERIVED from this table, never authored
## beside it: the brake (`brake_g` of the weight), the handbrake
## (`HandbrakeProfile.lock_ratio` of a rear wheel's lock) and the suspension's
## ceiling (`suspension_max_load_ratio` of a wheel's load at rest) — hand-sized,
## each was re-seeded at every change of mass, gravity or grip, and the one
## time they were not every tap spun (`Q153`).
##
## Deliberately no defaults, as `HandlingProfile`: an unassigned table reads as
## zeroes and fails loudly. Each table's sources are in the sidecar beside it.

## Path to the shipped car's table, so a tool that needs one of its numbers
## (`verify_spawn.gd`, for the wheel ray) cannot load a second file.
const PATH: String = "res://tuning/cars/crown_comfort.tres"

@export_group("Body")
## The car's mass, set on the rigid body in `VehicleController._ready`.
@export_range(0.0, 10000.0, 1.0, "suffix:kg") var mass_kg: float

## Downward offset of the centre of mass from the body origin. Lower = less roll.
@export_range(-2.0, 2.0, 0.01, "suffix:m") var centre_of_mass_offset_y: float

@export_group("Drive and brakes")
## Top speed in forward gear.
@export_range(0.0, 300.0, 1.0, "suffix:km/h") var max_speed_kph: float
## Reverse is instant — no gear delay.
@export_range(0.0, 100.0, 1.0, "suffix:km/h") var max_reverse_kph: float
## Drive force at full throttle, handed to `VehicleBody3D.engine_force`.
##
## ⚠️ **Not per wheel.** It is split across the wheels marked
## `use_as_traction` (`TyreVehicleController`), as the engine split it.
##
## The launch force: the most drive at any speed, which `engine_power_kw` takes
## over from once power runs out (`VehicleController._drive_force_n`). 6,000 N
## since 2026-10-05, a Crown Comfort LPG off the line — 186 N⋅m through a
## Toyota 4-speed's first gear (≈2.8) and final drive (≈4.3, both typical, not
## this car's published ratios) at 85% on 0.31 m wheels (`Q153`). It was a
## constant 3,840 N, the pull at 63 kph, which left the car at 53 kph after 8 s.
@export_range(0.0, 10000.0, 10.0) var engine_force: float
## The engine's rated power: a Crown Comfort LPG's 1TR-FPE, 83 kW (`Q153`).
## Above the speed where `engine_force` is power-limited, the drive is this
## power through `driveline_efficiency` over the speed. 0 here or in the
## efficiency turns the limit off.
@export_range(0.0, 500.0, 1.0, "suffix:kW") var engine_power_kw: float
## The share of `engine_power_kw` that reaches the tyres: gearbox, final drive
## and the torque converter. 0.85, a typical automatic's.
@export_range(0.0, 1.0, 0.01) var driveline_efficiency: float
## Drag coefficient times frontal area, for the air's drag at every speed and
## with the throttle down: ½ × ρ × this × v², against the travel. 0.72, a
## saloon's Cd of about 0.36 on about 2.0 m² — typical figures, not the Crown
## Comfort's published ones (`Q153`). About 240 N at 80 kph.
@export_range(0.0, 3.0, 0.01, "suffix:m²") var drag_area_m2: float
## The brakes' strength: the deceleration they could give, in g, if the tyres
## held — a road car's are about 1.2, a little over what its tyres can use, so
## the tyre and ABS set the stop and not the brake. A real unit so that it sizes
## itself to the car: the force is this × the car's weight, whatever its mass,
## its gravity or the physics tick rate (`VehicleController._brake_per_wheel_n`).
##
## It replaced `brake_force` on 2026-10-06 (`Q153`), a number in
## `VehicleBody3D.brake`'s own unit that the tyre model multiplied by the tick
## rate — right at 60 Hz only, and re-seeded by hand at every change of mass
## (40 on the 1,200 kg car, 47 on the 1,400 kg one, 70 with ABS and the front
## bias: 9.3 m/s² from 63 kph). 70 was 1.22 g on this car; swept 1.0–1.3, the
## stop is the tyre's from 1.1 up (9.1 / 9.3 / 9.5 m/s² from 42 / 63 / 86 kph)
## and 1.0 falls short of it (8.9 / 9.0 / 9.1), so 1.2.
@export_range(0.0, 3.0, 0.01, "suffix:g") var brake_g: float
## The share of the brake on the front axle, as a real car's brake bias — the
## weight moves forward under braking, so the front tyres can carry more of it.
## Spread over the axle's wheels; the total is `brake_g`'s. 0 is unauthored
## and brakes all four wheels alike, as the car did before the bias (`Q153`).
@export_range(0.0, 1.0, 0.01) var brake_front_share: float

@export_group("Steering")
## Steering angle at standstill.
@export_range(0.0, 60.0, 0.5, "suffix:°") var steer_angle_max_deg: float

@export_group("Suspension")
## Chassis layout (wheelbase, track, hardpoints) is deliberately NOT here: that is
## per-vehicle model data and belongs to the vehicle scene. Wheel radius is the one
## exception, because `VehicleWheel3D.wheel_radius` needs it — and because
## `ray_length_m()` below is still what the spawn drops the car from.
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
## `HandlingProfile.gravity_scale` deepens sag and eats the bump travel that absorbs kerbs and
## jump landings. Scale this by √gravity_scale to hold ride height: 2.2 Hz at
## gravity_scale 1.0 since 2026-10-05, where it was 2.8 at 1.6 (`Q153`).
@export_range(0.5, 5.0, 0.05, "suffix:Hz") var suspension_frequency_hz: float
## 1.0 is critically damped. Below 1.0 allows a little bounce, above is sluggish.
@export_range(0.0, 2.0, 0.01) var suspension_damping_ratio: float
## The ceiling on what one spring may push with, in multiples of a wheel's
## load at rest (the car's weight over its wheels): `VehicleWheel3D`'s
## `suspension_max_force`, derived so that it follows the mass and the gravity.
##
## ⚠️ **Godot's default of 6000 N cannot carry this car, and the failure is
## quiet.** A corner's load at rest is 1400 × 9.8 ÷ 4 ≈ 3430 N, so the default
## leaves 1.75× headroom, and at 1,200 kg under 1.6× gravity it left 1.27× and
## the spring clipped on the first kerb — the car sags onto its bump stops
## rather than reporting anything. 4.0: the hand-seeded newtons were 13,700 on
## this car and 19,000 on that one, 3.99× and 4.04× their loads at rest.
@export_range(0.0, 20.0, 0.1) var suspension_max_load_ratio: float


## How far a suspension ray reaches below its hardpoint — the car's ride height
## with the springs fully extended.
##
## The only function on an otherwise pure schema, and it is here rather than on
## VehicleController for two reasons. It is a fact about the car's table, which
## suspension_rest_length_m already states in prose. And it has to be reachable
## from a headless --script tool without dragging the controller in:
## tools/verify_spawn.gd needs this number to check the drop height, and a
## table is a smaller thing to load than the car that reads it.
func ray_length_m() -> float:
	return suspension_rest_length_m + wheel_radius_m
