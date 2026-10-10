class_name ParkedProfile
extends Resource
## How the parked roster is resolved against the clock and cut into cells
## (`P3-73`, `Q161`): what each number *is*. Why each has the value it has is
## `tuning/parked.md` beside the `.tres`.
##
## 🔴 **No `@export` here declares a default**, on `StreamingProfile`'s
## convention: a missing key reads as zero, and `ParkedLayer` refuses a zero
## cell or an empty day rather than fall back to a literal.

## Path to the shipped table, so `parked_layer.gd` and `verify_parked.gd`
## cannot load two different files.
const PATH: String = "res://tuning/parked.tres"

## The hour of the day the rig's `time_of_day` 0.0 stands for, on a 24 h
## clock. The roster reads every placement's `hours` against this clock.
@export_range(0.0, 24.0, 0.5, "suffix:h") var clock_start_h: float
## The hour `time_of_day` 1.0 stands for. Must be after `clock_start_h`; a
## day that runs past midnight is written as a value over 24.
@export_range(0.0, 48.0, 0.5, "suffix:h") var clock_end_h: float
## Side of a plan cell. A placement goes whole to the cell its origin is in,
## and a cell is the unit that is rebuilt out of view.
@export_range(0.0, 2000.0, 5.0, "suffix:m") var cell_m: float
## A cell is hidden past this, measured from the camera to the CENTRE of the
## cell's own box — the engine's `visibility_range_end` — and it is only ever
## rebuilt while hidden, so nothing pops in view.
@export_range(0.0, 2000.0, 5.0, "suffix:m") var range_m: float
## The engine's `visibility_range_end_margin`: the hysteresis about `range_m`.
@export_range(0.0, 100.0, 1.0, "suffix:m") var range_margin_m: float
## How often the roster asks the clock and looks for a hidden cell to rebuild.
@export_range(0.0, 60.0, 0.1, "suffix:s") var poll_s: float
## How long a hidden cell keeps its draw before a placement with a `chance`
## under 1 is rolled again — a bus that was at a stop may be gone when the
## street is next driven.
@export_range(0.0, 600.0, 1.0, "suffix:s") var reroll_s: float
