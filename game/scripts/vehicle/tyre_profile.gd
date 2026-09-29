class_name TyreProfile
extends Resource
## The per-wheel tyre model's numbers (`P3-52`, `Q152`) — the spike that asks
## whether a drift can be physical on `VehicleBody3D` rather than assisted.
## Read by `TyreVehicleController` only; the shipped taxi never loads it.
## What each value *is* is here, why it is what it is in `tuning/tyre.md`.
##
## 🔴 **No `@export` here declares a default**, on `TaxiDoorProfile`'s
## convention: a default is a second copy of the table, and Godot's writer
## drops any key equal to one (`Q119`). A missing key reads as zero, and the
## controller refuses a zero it cannot run on (`TyreVehicleController.usable`).

## Path to the spike's table, so the scene and a probe cannot load two files.
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
## slide. Absent from `tyre.tres`: countersteering is the player's skill.
@export_range(0.0, 1.5, 0.05) var countersteer_assist: float
## The most the front wheels may turn while the assist countersteers, where
## the handling table's lock narrows with speed (16.4° at 63 kph).
@export_range(0.0, 60.0, 1.0, "suffix:°") var countersteer_lock_deg: float
## The lock the PLAYER has on the countersteer side while the car slides past
## the tyre's peak, where the handling table narrows it with speed (16.4° at
## 63 kph, under 14° at 86). 0 leaves the table's lock alone. Absent from
## `tyre.tres`: swept and refuted on the pad's driver (`tyre.md`).
@export_range(0.0, 60.0, 1.0, "suffix:°") var slide_lock_deg: float
