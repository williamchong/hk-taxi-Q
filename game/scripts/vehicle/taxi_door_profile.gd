class_name TaxiDoorProfile
extends Resource
## The passenger door's swing (`P3-48`) — the numbers `taxi_door.gd` carried as
## `@export` defaults until `Q150` moved them, against `ARCHITECTURE.md`'s
## Constraint 4: tuning is data. The rationale for each value is in
## `tuning/taxi_door.md`; what each *is* is here.
##
## 🔴 **No `@export` here declares a default**, on `WrongWayProfile`'s
## convention: a default is a second copy of the tuning table, and a second copy
## drifts — Godot's writer also drops any key equal to one, which is how
## `beams.tres` went empty (`Q119`). A missing key reads as zero, and `TaxiDoor`
## refuses to swing on a zero rather than fall back to a literal.

## Path to the shipped table, so `taxi.tscn` and `verify_vehicle.gd` cannot load
## two different files.
const PATH: String = "res://tuning/taxi_door.tres"

## How far the door swings, in degrees off shut.
@export_range(10.0, 90.0, 1.0, "suffix:°") var open_deg: float
## How long a full swing takes, either way.
@export_range(0.05, 2.0, 0.05, "suffix:s") var swing_s: float
## How long `open_briefly` holds the door fully open before shutting it — the
## fare stepping out at the destination, or storming out of a bail.
@export_range(0.0, 5.0, 0.05, "suffix:s") var alight_hold_s: float
