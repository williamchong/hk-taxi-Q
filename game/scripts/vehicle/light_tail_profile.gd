class_name LightTailProfile
extends Resource
## The light tail (`P3-70`): a colour per tier, how long a streak lives, and
## how it is laid. The rationale for each value is in `tuning/light_tail.md`;
## what each *is* is here.
##
## 🔴 **No `@export` here declares a default**, on `TaxiDoorProfile`'s convention
## (`Q150`): a missing key reads as zero, and `LightTail` refuses to streak on a
## zero rather than fall back to a literal.

## Path to the shipped table, so `taxi_tyre.tscn` and `verify_vehicle.gd` cannot
## load two different files.
const PATH: String = "res://tuning/light_tail.tres"

## The streak's colour per tier, `SkillTracker.drift_tier` indexing it as the
## sparks' table does: [0] while a slide counts toward its first award, [1] once
## it has paid once, and so on; a tier past the end takes the last. One entry is
## one colour at every tier. Alpha scales the whole streak.
@export var colours: PackedColorArray
## How long a piece of streak lives before it has faded to nothing.
@export_range(0.05, 3.0, 0.01, "suffix:s") var life_s: float
## How the fade runs: 1 is linear over `life_s`, above it the streak drops off
## sooner and lingers faint.
@export_range(0.1, 4.0, 0.1) var fade_power: float
## A lamp that moved further than this in one tick starts a new streak rather
## than drawing one across the gap: a teleport, a reset, a landing.
@export_range(0.1, 10.0, 0.1, "suffix:m") var max_step_m: float
## The streak's cross-section against the lens's own: 1 is the lens's width and
## height exactly.
@export_range(0.1, 5.0, 0.05) var width_scale: float
