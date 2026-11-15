## A day that ends (`Q160`, the user's ask): the looks a `LightingRig` passes
## through as game time runs, and how long the passage takes.
##
## A shift's cycle is not a loop; a free drive's is, since `Q225`, where
## `loop_at` says so. It starts at its first `RigKeyframe`, passes through
## each in turn — and through the rig scene's own daylight at `day_at`, which
## is one moment of the day since `Q222` and no longer where it starts — and
## HOLDS the last one — a session is three to five minutes and skilled play
## extends it (`GAME_DESIGN.md`), so the curve needs an end state and night
## is it.
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
## Where on the cycle the rig scene as authored stands: the one look that is in
## no keyframe. Keyframes before it are the morning, after it the rest.
@export_range(0.0, 1.0, 0.001) var day_at: float
## How often the rig is moved, in hertz. The sky's radiance is re-rendered on
## every move, so this is a cost dial and not a smoothness one.
@export_range(0.5, 60.0, 0.5, "suffix:Hz") var update_hz: float
## Where the cycle comes round to its start again, on the same scale as the
## keyframes' `at` — past 1.0, the shift's end — or 0 for a cycle that holds
## its last keyframe. Only a free drive runs past 1.0 (`Q225`): the night goes
## on through a dawn to the first keyframe, and the day starts over.
@export_range(0.0, 4.0, 0.001) var loop_at: float
## The looks either side of the authored day, in the order they are reached.
@export var keyframes: Array[RigKeyframe]


## Whether the table is whole: both rates, at least one keyframe, every
## keyframe carrying an environment, and `at` strictly rising and never on
## `day_at`, which is the authored scene's.
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
	var last: float = -1.0
	for index: int in keyframes.size():
		var key: RigKeyframe = keyframes[index]
		if key == null or key.environment == null:
			push_error("RigCycle: %s keyframe %d has no environment." % [resource_path, index])
			return false
		if key.at <= last or is_equal_approx(key.at, day_at):
			push_error(
				(
					"RigCycle: %s keyframe %d is at %s, not past %s or on day_at %s; the order is the cycle."
					% [resource_path, index, key.at, last, day_at]
				)
			)
			return false
		last = key.at
	if loop_at != 0.0 and (loop_at < 1.0 or loop_at <= last):
		push_error(
			(
				"RigCycle: %s loop_at %s is not past 1.0 and its last keyframe at %s."
				% [resource_path, loop_at, last]
			)
		)
		return false
	return true


## The far end of the cycle's scale: `loop_at` where it comes round, else 1.
func span() -> float:
	return loop_at if loop_at > 0.0 else 1.0
