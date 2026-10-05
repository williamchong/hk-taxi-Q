class_name TyreProfile
extends Resource
## The per-wheel tyre model's numbers (`P3-52`, `Q152`): the tyre itself, and
## nothing the car's systems decide — those have their own tables under
## `tuning/systems/` since `Q155`. Built as the spike
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
## Ground speed under which slip is measured against this floor instead of the
## wheel's own speed, so a car at rest does not read an infinite slip.
@export_range(0.1, 10.0, 0.1, "suffix:m/s") var low_speed_mps: float
## Wheel-spin integration steps per physics tick.
@export_range(1, 32, 1) var substeps: int
## How far down towards the contact the sideways force goes in: 0 at the
## centre of mass's height, 1 at the tyre's contact — Bullet's
## `m_rollInfluence`, which the engine-tyre car's `roll_influence` set at 0.2.
## A dial because the drift depends on it: the weight a corner moves onto the
## outer tyres is what lets the unloaded inner rear spin and turn the car, and
## 0.2 took most of that away.
@export_range(0.0, 1.0, 0.05) var side_force_depth: float
