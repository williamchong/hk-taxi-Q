## A day that ends (`Q160`, the user's ask): the looks a `LightingRig` passes
## through as game time runs, and how long the passage takes.
##
## A cycle is not a loop. It starts at the rig scene's own daylight, reaches
## each `RigKeyframe` in turn and HOLDS the last one — a session is three to
## five minutes and skilled play extends it (`GAME_DESIGN.md`), so the curve
## needs an end state and night is it.
##
## 🔴 **No `@export` here declares a default** (`Q150`'s convention). A missing
## `length_s` or `update_hz` reads zero and `usable()` refuses the table, so the
## rig stays the static daylight one rather than dividing by it.
class_name RigCycle
extends Resource

## Path to the shipped table, so the rig scene and `verify_day_cycle.gd` cannot
## load two different files.
const PATH: String = "res://tuning/day_to_night.tres"

## Game seconds from the start of a drive to the last keyframe.
@export_range(10.0, 3600.0, 1.0, "suffix:s") var length_s: float
## The fraction of the cycle the authored daylight holds before anything moves.
@export_range(0.0, 1.0, 0.01) var day_until: float
## How often the rig is moved, in hertz. The sky's radiance is re-rendered on
## every move, so this is a cost dial and not a smoothness one.
@export_range(0.5, 60.0, 0.5, "suffix:Hz") var update_hz: float
## The looks after the day, in the order they are reached.
@export var keyframes: Array[RigKeyframe]


## Whether the table is whole: both rates, at least one keyframe, every
## keyframe carrying an environment, and `at` strictly rising past `day_until`.
## Loud on every call, like `VehicleLamps.usable` — a broken table is a build
## defect — and pure, so a verify tool can ask it of a table it has broken.
func usable() -> bool:
	if TuningTable.any_zero(
		self,
		{"length_s": length_s, "update_hz": update_hz},
		"RigCycle",
		"the rig stays at its authored daylight"
	):
		return false
	if keyframes.is_empty():
		push_error("RigCycle: %s has no keyframes; the day never ends." % resource_path)
		return false
	var last: float = day_until
	for index: int in keyframes.size():
		var key: RigKeyframe = keyframes[index]
		if key == null or key.environment == null:
			push_error("RigCycle: %s keyframe %d has no environment." % [resource_path, index])
			return false
		if key.at <= last:
			push_error(
				(
					"RigCycle: %s keyframe %d is at %s, not past %s; the order is the cycle."
					% [resource_path, index, key.at, last]
				)
			)
			return false
		last = key.at
	return true
