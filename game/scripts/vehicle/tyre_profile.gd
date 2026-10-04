class_name TyreProfile
extends Resource
## The per-wheel tyre model's numbers (`P3-52`, `Q152`) — built as the spike
## that asked whether a drift can be physical on `VehicleBody3D` rather than
## assisted, and the game's car since 2026-10-03. Read by
## `TyreVehicleController` only; `taxi.tscn` on its own never loads it.
## What each value *is* is here, why it is what it is in `tuning/tyre.md`.
##
## 🔴 **No `@export` here declares a default**, on `TaxiDoorProfile`'s
## convention: a default is a second copy of the table, and Godot's writer
## drops any key equal to one (`Q119`). A missing key reads as zero, and the
## controller refuses a zero it cannot run on (`TyreVehicleController.usable`).

## Path to the table, so the scene and a probe cannot load two files.
const PATH: String = "res://tuning/tyre.tres"

## Peak friction coefficient: the most force a tyre gives is `mu` × its load.
## ⚠️ Not `HandlingProfile.tyre_grip`, which is Bullet's `wheel_friction_slip`
## and scales an impulse cap, not a force.
@export_range(0.1, 4.0, 0.01) var mu: float
## Force left once the tyre is sliding, as a share of the peak: the curve's
## tail. Under 1 is a tyre that lets go past its peak, which is what makes a
## slide a different state from a corner.
@export_range(0.05, 0.99, 0.01) var slide_ratio: float
## Slip ratio at the peak of the longitudinal curve: `(ωR − v) / v` where
## drive or brake force is greatest.
@export_range(0.01, 0.5, 0.005) var peak_slip_ratio: float
## Slip angle at the peak of the lateral curve.
@export_range(1.0, 30.0, 0.1, "suffix:°") var peak_slip_angle_deg: float
## One wheel's rotating inertia, drivetrain share included.
@export_range(0.1, 10.0, 0.05, "suffix:kg·m²") var wheel_inertia_kgm2: float
## Torque the drift button puts on each rear wheel: a real handbrake.
@export_range(0.0, 10000.0, 10.0, "suffix:N·m") var handbrake_torque_nm: float
## Share of the rear tyres' sideways force taken away while the drift button
## is engaged, on the handling table's attack and release ramp: 0 leaves the
## handbrake alone. At arcade grip a locked rear still holds a city-speed turn,
## so the handbrake alone starts the slide after the corner is over (`Q153`).
@export_range(0.0, 1.0, 0.05) var drift_side_cut: float
## The cut at and above `drift_side_cut_to_kph`; `drift_side_cut` holds at and
## below `drift_side_cut_from_kph`, and the speed at the button's press picks
## between them. A slow turn asks little of the rears and needs the deeper cut;
## the same cut at 63 kph spins the car.
@export_range(0.0, 1.0, 0.05) var drift_side_cut_fast: float
@export_range(0.0, 200.0, 1.0, "suffix:kph") var drift_side_cut_from_kph: float
@export_range(0.0, 200.0, 1.0, "suffix:kph") var drift_side_cut_to_kph: float
## The body slip over which the forward drive fades out while traction control
## is disarmed: whole at `slide_drive_fade_from_deg`, gone at
## `slide_drive_fade_to_deg`. A ceiling on the power that feeds a slide, so a
## held throttle cannot spin the car; under the band the slide is the
## player's. Inert while `to` is not over `from`.
@export_range(0.0, 90.0, 1.0, "suffix:°") var slide_drive_fade_from_deg: float
@export_range(0.0, 90.0, 1.0, "suffix:°") var slide_drive_fade_to_deg: float
## Whether traction control comes back as soon as the player lets go of the
## steering after a drift press — the slide's ending handed to the steering
## key, where `traction_rearm_s` waits on a clock. Letting go only: a
## countersteer is how a slide is HELD, and re-armed on a reversal the
## countersteered slide died (`hold` 2.63 s -> 0.60 s at 63 kph).
@export var rearm_on_steer_release: bool
## Whether the drift button also takes the drive off the rear wheels while it
## is down, as a handbrake's clutch does. Off, the held throttle fights the
## handbrake and neither rear locks (`Q153`: rims at 30-41 kph on a 34-40 kph
## car through the whole tap at 3,000 N·m).
@export var handbrake_declutch: bool
## Ground speed under which slip is measured against this floor instead of the
## wheel's own speed, so a car at rest does not read an infinite slip.
@export_range(0.1, 10.0, 0.1, "suffix:m/s") var low_speed_mps: float
## Wheel-spin integration steps per physics tick.
@export_range(1, 32, 1) var substeps: int
## Share of the shipped car's drift yaw torque still applied, 0 off to 1 as
## shipped. 0 grades the physics alone.
@export_range(0.0, 1.0, 0.05) var yaw_assist_scale: float
## Multiplier on `HandlingProfile.engine_force` for this car's drive torque.
## 1 is the shipped car's drive; above it the rear tyres can be spun.
@export_range(0.1, 5.0, 0.05) var drive_scale: float
## How far past the car's top speed a driven wheel's rim may spin, as a share
## of it: 0 stops the drive at top speed's rim speed, 0.5 at half as much
## again. A slide is held on wheelspin, and at 86 kph the rim met the limiter
## mid-slide (`Q153`).
@export_range(0.0, 2.0, 0.05) var rim_overspeed: float
## Traction control: the wheelspin — forward slip, in multiples of the tyre's
## peak — at which a driven wheel's torque is cut. 0 is no traction control. The drift
## button switches it off — a real car's drift mode — so full throttle at full
## lock grips, and a slide asked for can be powered.
@export_range(0.0, 5.0, 0.05) var traction_limit: float
## How long traction control stays off after the drift button comes up, at
## least; after that it re-arms once the car's slip is back under
## `HandlingProfile.drift_slip_threshold_deg`, the bar the game scores a slide
## on. 0 re-arms on the slip alone.
@export_range(0.0, 5.0, 0.05, "suffix:s") var traction_rearm_s: float
## Share of the forward drive taken off at full lock while traction control is
## armed, in proportion to the front wheels' angle over the lock the speed
## allows: 0 leaves the drive alone, 1 leaves none at full lock. The drift
## button disarms traction control, so a slide never sees it (`P3-55`).
@export_range(0.0, 1.0, 0.05) var turn_drive_cut: float
## How far down towards the contact the sideways force goes in: 0 at the
## centre of mass's height, 1 at the tyre's contact — Bullet's
## `m_rollInfluence`, which the handling table's `roll_influence` sets for the
## engine's own friction and this car, its friction zeroed, no longer reads.
## A dial of its own because the drift depends on it: the weight a corner
## moves onto the outer tyres is what lets the unloaded inner rear spin and
## turn the car, and the shipped 0.2 takes most of that away. A name of its own
## because a sweep resolves a field by name across both tables, and a shared
## one wrote the handling table's copy, which this car does not read.
@export_range(0.0, 1.0, 0.05) var side_force_depth: float
## Countersteer assist: while the car slides, the share of the slip angle the
## front wheels are turned towards the travel, on top of the player's own
## steering. 0 is none; 1 points the fronts along the travel past the tyre's
## peak slip angle. A steering aid, not a force: the tyres still decide the
## slide. Inert while the car's `drift_assist` is off — the player's option
## (`P3-56`), and off on every pad unless `--assist=on` asks for it.
@export_range(0.0, 1.5, 0.05) var countersteer_assist: float
## Where the slide's drive fade starts while the assist is on, in place of
## `slide_drive_fade_from_deg`: the assisted slide runs wider at 86 kph, and
## the plain band cut its drive before `drift_min_s`. 0 keeps the plain band.
@export_range(0.0, 90.0, 1.0, "suffix:°") var assist_drive_fade_from_deg: float
## The most the front wheels may turn while the assist countersteers, where
## the handling table's lock narrows with speed (16.4° at 63 kph).
@export_range(0.0, 60.0, 1.0, "suffix:°") var countersteer_lock_deg: float
## The lock the PLAYER has on the countersteer side while the car slides past
## the tyre's peak, where the handling table narrows it with speed (16.4° at
## 63 kph, under 14° at 86). 0 leaves the table's lock alone. Absent from
## `tyre.tres`: swept and refuted on the pad's driver (`tyre.md`).
@export_range(0.0, 60.0, 1.0, "suffix:°") var slide_lock_deg: float
## The most the front wheels may turn on the countersteer side once a caught
## slide turns the car the other way: a cap on the player's angle, never an
## angle added. 0 leaves the player's lock alone. 6° in `tyre.tres`, the user's
## drive the veto (`tyre.md`).
@export_range(0.0, 60.0, 0.5, "suffix:°") var catch_lock_deg: float
## The heading rate, the other way from the slide, past which the car reads as
## turning against it and `catch_lock_deg` caps the countersteer. Inert, like
## `catch_window_s`, while `catch_lock_deg` is 0.
@export_range(0.0, 180.0, 1.0, "suffix:°/s") var catch_turn_dps: float
## How long after the tail was last out past the tyre's peak the cap may
## still engage, so a turn the other way after the slide is over has the full lock.
@export_range(0.0, 5.0, 0.05, "suffix:s") var catch_window_s: float
