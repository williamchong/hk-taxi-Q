class_name HandlingProfile
extends Resource
## Arcade vehicle feel, as data: how the game answers the player, whatever car
## is under it. The car's own numbers — mass, drive, brakes, suspension — are
## `CarSpec`'s, one table per car.
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
## (`verify_fares.gd`, for `drift_slip_threshold_deg`) cannot load a second
## file.
const PATH: String = "res://tuning/handling.tres"

@export_group("Steering")
## Steering angle at the car's `max_speed_kph`; its lock at rest is the car's
## (`CarSpec.steer_angle_max_deg`). Lower keeps the car stable at speed.
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
