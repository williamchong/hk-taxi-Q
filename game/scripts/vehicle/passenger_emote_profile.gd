class_name PassengerEmoteProfile
extends Resource
## The passenger's face's rise and life (`P3-49`) — the numbers
## `passenger_emote.gd` carried as `@export` defaults until `Q150` moved them,
## against `ARCHITECTURE.md`'s Constraint 4: tuning is data. The rationale for
## each value is in `tuning/passenger_emote.md`; what each *is* is here.
##
## 🔴 **No `@export` here declares a default**, on `WrongWayProfile`'s
## convention: a default is a second copy of the tuning table, and a second copy
## drifts — Godot's writer also drops any key equal to one, which is how
## `beams.tres` went empty (`Q119`). A missing key reads as zero, and
## `PassengerEmote` refuses to pop a face on a zero rather than fall back to a
## literal.

## Path to the shipped table, so `taxi.tscn` and `verify_vehicle.gd` cannot load
## two different files.
const PATH: String = "res://tuning/passenger_emote.tres"

## How far a face rises over its life, in metres.
@export_range(0.2, 3.0, 0.05, "suffix:m") var rise_m: float
## How long a face lives, in seconds, from the pop to gone.
@export_range(0.3, 5.0, 0.05, "suffix:s") var life_s: float
## How long the pop takes: the face scales from nothing to full over this.
@export_range(0.02, 1.0, 0.01, "suffix:s") var pop_s: float
## How long the face takes to shrink away at the end of its life.
@export_range(0.02, 2.0, 0.01, "suffix:s") var shrink_s: float
## How many faces may be up at once.
@export_range(1, 8, 1) var most_live: int
