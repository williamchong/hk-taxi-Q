class_name DriftSparksProfile
extends Resource
## The drift's sparks (`P3-58`): a colour per tier and how the sparks fly. The
## rationale for each value is in `tuning/drift_sparks.md`; what each *is* is
## here.
##
## 🔴 **No `@export` here declares a default**, on `TaxiDoorProfile`'s convention
## (`Q150`): a missing key reads as zero, and `DriftSparks` refuses to light on a
## zero rather than fall back to a literal.

## Path to the shipped table, so `taxi_tyre.tscn` and `verify_vehicle.gd` cannot
## load two different files.
const PATH: String = "res://tuning/drift_sparks.tres"

## The sparks' colour per tier, `SkillTracker.drift_tier` indexing it: [0] while
## a slide counts toward its first award, [1] once it has paid once, and so on;
## a tier past the end takes the last. A colour with zero alpha lights nothing,
## so whether a counting slide shows is this table's call.
@export var colours: PackedColorArray
## Sparks alive at once per rear wheel.
@export_range(1, 256, 1) var amount: int
## How long a spark lives.
@export_range(0.05, 2.0, 0.01, "suffix:s") var lifetime_s: float
## How fast a spark leaves the tyre.
@export_range(0.1, 20.0, 0.1, "suffix:m/s") var speed_mps: float
## How far off its direction — back and up off the tyre — a spark may fly.
@export_range(0.0, 90.0, 1.0, "suffix:°") var spread_deg: float
## A spark's length, and its thickness.
@export_range(0.01, 1.0, 0.01, "suffix:m") var length_m: float
@export_range(0.005, 0.2, 0.005, "suffix:m") var thickness_m: float
## How long the sparks flare when the tier steps up, and by how much they grow.
@export_range(0.05, 2.0, 0.05, "suffix:s") var burst_s: float
@export_range(1.0, 5.0, 0.1) var burst_scale: float
