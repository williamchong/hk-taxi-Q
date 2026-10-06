class_name DayClock
extends Node
## Game time for the rig (`Q160`, the user's ask: a mode that runs from day to
## night as game time): the seconds driven since the start, handed to a
## `LightingRig` as its `time_of_day`.
##
## The rig is not its own clock. What "game time" means — driving time, not
## menu time, not wall time — is the level's to say, and the rig is instanced
## by scenes that have no game at all.
##
## ⚠️ **On the physics tick, so a scripted drive repeats.** The hour is a
## function of ticks driven and nothing else; a clock on the frame would light
## two runs of one route differently and `drive.sh`'s A/B frames with them.
##
## ⚠️ **The rig is moved `RigCycle.update_hz` times a second, not every tick.**
## Each move re-renders the sky's radiance; a four-minute dusk does not need
## sixty of those a second to read as smooth.

## `--day-cycle=off` holds the authored daylight, `on` runs the day, and either
## beats the saved option — `drive.sh` appends `off`, so every scripted frame
## is the daylight one it always was unless a run asks for the hour to move.
const CYCLE_ARG: String = "--day-cycle="

## The rig this clock moves. Assign in the scene.
@export var rig: LightingRig
## The car whose `parked` holds the clock: under the start menu no game time
## passes. Assign in the scene; without one the clock runs from boot.
@export var vehicle: VehicleController

## Game seconds driven.
var elapsed_s: float = 0.0

var _due_s: float = 0.0
## Whether the mode has been read. Not at `_ready`: the menu saves the option
## while the car is parked, after this node readied.
var _decided: bool = false


## Whether the day runs: the flag, then the saved option.
static func wanted() -> bool:
	if Cmdline.off(CYCLE_ARG):
		return false
	if Cmdline.value(CYCLE_ARG).to_lower() == "on":
		return true
	return Settings.day_cycle()


func _ready() -> void:
	# A rig with no usable cycle, or one pinned to an hour for a frame, has
	# nothing for a clock to do.
	set_physics_process(rig != null and rig.moves() and not rig.pinned)


func _physics_process(delta: float) -> void:
	if vehicle != null and vehicle.parked:
		return
	if not _decided:
		_decided = true
		if not wanted():
			set_physics_process(false)
			return
	elapsed_s += delta
	_due_s -= delta
	if _due_s > 0.0:
		return
	# Added to, not assigned, for `VehicleLamps._settle`'s reason: assigning
	# discards the overshoot and the rate lands under the dial.
	_due_s += 1.0 / rig.cycle.update_hz
	rig.time_of_day = elapsed_s / rig.cycle.length_s
	if rig.time_of_day >= 1.0:
		# The last keyframe holds; there is nothing left to move.
		set_physics_process(false)
