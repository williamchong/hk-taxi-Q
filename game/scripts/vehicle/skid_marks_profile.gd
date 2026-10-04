class_name SkidMarksProfile
extends Resource
## The tyre marks and the smoke (`P3-57`): when a tyre marks the road, how the
## mark is drawn, and the smoke off the rears. The rationale for each value is in
## `tuning/skid_marks.md`; what each *is* is here.
##
## 🔴 **No `@export` here declares a default**, on `TaxiDoorProfile`'s convention
## (`Q150`): a missing key reads as zero, and `SkidMarks` refuses to lay a mark
## or raise smoke on a zero rather than fall back to a literal.

## Path to the shipped table, so `taxi_tyre.tscn` and `verify_vehicle.gd` cannot
## load two different files.
const PATH: String = "res://tuning/skid_marks.tres"

## The combined slip, in multiples of the tyre's peak, over which a wheel lays a
## mark (`TyreVehicleController.wheel_slips`).
@export_range(0.1, 10.0, 0.05) var mark_from_slip: float
## How wide a mark is: the tyre's tread.
@export_range(0.05, 0.5, 0.01, "suffix:m") var mark_width_m: float
## How far the mark floats off the contact, along its normal, so it sits over
## the road and the paint on it rather than inside them.
@export_range(0.001, 0.1, 0.001, "suffix:m") var lift_m: float
## A wheel that moved further than this in one tick starts a new mark rather
## than drawing one across the gap: a teleport, a reset, a landing.
@export_range(0.1, 10.0, 0.1, "suffix:m") var max_step_m: float
## How many pieces of mark the road keeps, every wheel together; the oldest is
## reused once they are all down. Each piece is one tick of one wheel.
@export_range(16, 16384, 1) var capacity: int
## The marks' colour, alpha included: one colour for every mark.
@export var mark_colour: Color
## The combined slip over which a rear wheel smokes.
@export_range(0.1, 10.0, 0.05) var smoke_from_slip: float
## Puffs alive at once per rear wheel.
@export_range(1, 256, 1) var smoke_amount: int
## How long a puff lives.
@export_range(0.1, 5.0, 0.05, "suffix:s") var smoke_lifetime_s: float
## A puff's size when it is born and when it dies.
@export_range(0.01, 2.0, 0.01, "suffix:m") var smoke_start_m: float
@export_range(0.01, 5.0, 0.01, "suffix:m") var smoke_end_m: float
## How fast a puff rises.
@export_range(0.0, 5.0, 0.05, "suffix:m/s") var smoke_rise_mps: float
## How far off straight up a puff may set off.
@export_range(0.0, 90.0, 1.0, "suffix:°") var smoke_spread_deg: float
## The smoke's colour, alpha included, at birth; it fades to clear.
@export var smoke_colour: Color
