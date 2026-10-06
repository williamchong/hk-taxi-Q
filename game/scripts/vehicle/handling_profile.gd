class_name HandlingProfile
extends Resource
## Arcade vehicle feel, as data.
##
## CLAUDE.md hard rule 4: tuning values are data, never constants in code.
## This script declares the schema and nothing else — the numbers live only in
## game/tuning/handling.tres. Deliberately no defaults here: a profile that was
## never assigned reads as all-zeroes and fails loudly, rather than quietly
## driving on values buried in a script.

## The model is Godot's VehicleBody3D/VehicleWheel3D, driven from these numbers,
## with the engine's tyre force replaced by `TyreVehicleController`'s per-wheel
## model, whose numbers are `TyreProfile`'s (`Q152`). The engine-tyre grip and
## drift dials went with the engine-tyre control car (2026-10-05); `Q50` to
## `Q89` record them. See also docs/GAME_DESIGN.md "Controls".

## Path to the shipped table, so a tool that needs one of its design targets
## (`verify_fares.gd`, for `drift_slip_threshold_deg`; `verify_spawn.gd`, for
## the wheel ray) cannot load a second file.
const PATH: String = "res://tuning/handling.tres"

@export_group("Speed")
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
## Steering angle at max_speed_kph. Lower keeps the car stable at speed.
@export_range(0.0, 60.0, 0.5, "suffix:°") var steer_angle_at_top_deg: float
## Seconds to reach full lock from centre.
@export_range(0.01, 1.0, 0.01, "suffix:s") var steer_attack_s: float
## Seconds to return to centre when input is released.
@export_range(0.01, 1.0, 0.01, "suffix:s") var steer_release_s: float

@export_group("Drift")
## Seconds for the drift to reach full engagement while the button is held.
##
## Short: the tail should step out when the player asks, not a moment later.
@export_range(0.01, 1.0, 0.01, "suffix:s") var drift_attack_s: float
## Seconds for the drift to let go after the button is released. The tyre
## model's rear side cut fades with it (`TyreVehicleController`, `Q153`).
##
## Built for the engine-tyre car's tap (`Q84`), which it did not fix, and kept for
## Q83's touch scheme, which holds drift past a thumb threshold and needs the
## engagement to exist for its hysteresis.
##
## ⚠️ **Asymmetric with drift_attack_s on purpose, and the asymmetry is the
## feature.** Same shape as steer_attack_s / steer_release_s above, and for the
## same reason — the car should answer the input immediately and let go slowly.
## Do not collapse the two into one number to "restore consistency".
##
## ⚠️ **`InputRouter.drift` stays a bool and this duration lives here** (Q83): the
## router is the single source of player *intent* and the intent is binary. A ramp
## there would report held while nothing is held and lie about the button.
@export_range(0.01, 3.0, 0.01, "suffix:s") var drift_release_s: float
## Slip angle above which the drift scores style points. Since `P3-49` it is
## read: `FareSystem`'s drift skill pays per `SkillProfile.drift_s` (past `drift_min_s`) the slip
## holds at or over it, so it is a design target the skidpad grades dwell
## against (`Q84`), never a knob turned to make a slide pay.
@export_range(0.0, 90.0, 1.0, "suffix:°") var drift_slip_threshold_deg: float
## Fraction of rolling speed shed per second when coasting — engine braking.
## Small values glide, large values stop the car the moment you lift off.
##
## ⚠️ **0.15 since 2026-10-05, the whole of the coast's viscous term.** Until
## then it was 0.05 and Godot's `default_linear_damp` (0.1) supplied the rest —
## measured on the pad, 0.100/s with this at zero — but that damping acted with
## the throttle down too, about 2,900 N at 75 kph against a real car's 200 N of
## air, and held the real taxi under 80 kph. `taxi.tscn` replaces the body's
## damping with 0 and this took its share, so a coast decays as before (`Q153`).
@export_range(0.0, 1.0, 0.01) var coast_drag_per_s: float
## Speed-independent share of the coasting deceleration — rolling resistance.
##
## ⚠️ **The term that actually stops the car.** Viscous drag is an exponential
## decay with no zero: every halving of speed halves the force meant to remove
## it. With this at 0.0 a skidpad coast from 30.6 km/h was **still rolling at
## 3.9 km/h 13.8 s later**, and the same pedal that would have braked it
## reverses below STATIONARY_KPH — so there was no way to bring it to rest at
## all. At the shipped 0.8 the same coast reaches a dead stop in 6.5 s, and
## 5 km/h takes 1.5 s.
##
## This is what makes coasting shed a similar speed per second at 5 km/h as at
## 50, which is how a driver expects a car to behave.
@export_range(0.0, 5.0, 0.05, "suffix:m/s²") var rolling_resistance_mps2: float

@export_group("Collision and recovery")
## 0 = head-on stop, 1 = full glancing deflection. Glancing hits deflect;
## head-on hits cost speed, never control.
@export_range(0.0, 1.0, 0.01) var collision_deflection: float
## Fraction of speed retained after a head-on impact.
@export_range(0.0, 1.0, 0.01) var collision_speed_retained: float
## Seconds before an upside-down car auto-rights itself.
@export_range(0.0, 5.0, 0.05, "suffix:s") var auto_right_delay_s: float

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
## gravity_scale deepens sag and eats the bump travel that absorbs kerbs and
## jump landings. Scale this by √gravity_scale to hold ride height: 2.2 Hz at
## gravity_scale 1.0 since 2026-10-05, where it was 2.8 at 1.6 (`Q153`).
@export_range(0.5, 5.0, 0.05, "suffix:Hz") var suspension_frequency_hz: float
## 1.0 is critically damped. Below 1.0 allows a little bounce, above is sluggish.
@export_range(0.0, 2.0, 0.01) var suspension_damping_ratio: float
## VehicleWheel3D.suspension_max_force, in newtons — the ceiling on what one
## spring may push with.
##
## ⚠️ **Godot's default of 6000 N cannot carry this car, and the failure is
## quiet.** Static corner load is mass × g × gravity_scale ÷ 4 = 1400 × 9.8 × 1.0
## ÷ 4 ≈ 3430 N, so the default leaves 1.75× headroom, and at 1,200 kg and the
## 1.6 this once ran at it left 1.27× and the spring clipped on the first kerb —
## the car sags onto its bump stops rather than reporting anything. Seeded at
## roughly 4× static load (13,700 N; 19,000 at 1,200 kg and 1.6). It scales with mass and with gravity_scale,
## so it is not portable to a heavier vehicle unchanged.
@export_range(0.0, 60000.0, 100.0, "suffix:N") var suspension_max_force_n: float

@export_group("Body")
## Downward offset of the centre of mass from the body origin. Lower = less roll.
@export_range(-2.0, 2.0, 0.01, "suffix:m") var centre_of_mass_offset_y: float
## Above 1.0 shortens air time and lands jumps flatter. 1.0 since 2026-10-05,
## a real taxi's weight on its tyres (`Q153`): at 1.6 every grip, lock and
## drive number was sized to a car 1.6× as heavy as its mass.
@export_range(0.0, 5.0, 0.05) var gravity_scale: float


## How far a suspension ray reaches below its hardpoint — the car's ride height
## with the springs fully extended.
##
## The only function on an otherwise pure schema, and it is here rather than on
## VehicleController for two reasons. It is a fact about the profile, which
## suspension_rest_length_m already states in prose. And it has to be reachable
## from a headless --script tool without dragging the controller in:
## tools/verify_spawn.gd needs this number to check the drop height, and a
## profile is a smaller thing to load than the car that reads it.
func ray_length_m() -> float:
	return suspension_rest_length_m + wheel_radius_m
