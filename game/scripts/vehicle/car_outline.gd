class_name CarOutline
extends Node3D
## The outline's answer to the car (`P3-65`, `Q158`, the user's ask): the
## city's line thins and fades with the car's speed. The drift's light tail is
## `LightTail`'s (`P3-70`).
##
## The speed goes out as the global shader parameter `outline_speed`, 0 at rest
## to 1 at `full_speed_kph`, which `cel_outline.gdshader` reads. ⚠️ A global is
## process-wide, like `LightingRig`'s `exposure_anchor`: one car sets it, and a
## second car with this node would fight the first. The player's car carries it;
## an AI car (`B3`) must not.

const SPEED_PARAMETER: StringName = &"outline_speed"

## Assigned in `taxi_tyre.tscn`; the value and its reason are
## `tuning/car_outline.md`'s.
@export var profile: CarOutlineProfile

var _car: VehicleController = null
var _speed: float = -1.0


func _ready() -> void:
	set_physics_process(false)
	_car = VehicleController.above(self)
	if _car == null:
		push_error("CarOutline: not under a VehicleController; the outline ignores the car.")
		return
	if not usable():
		return
	set_physics_process(true)


func _exit_tree() -> void:
	# Process-wide: a car leaving must not leave the city drawn at its speed.
	if _speed >= 0.0:
		RenderingServer.global_shader_parameter_set(SPEED_PARAMETER, 0.0)


## Whether the table is whole: a profile with its one key above zero. Pure over
## `profile`, so `verify_vehicle.gd` can ask it of a car that never entered a
## tree.
func usable() -> bool:
	if profile == null:
		push_error("CarOutline: no CarOutlineProfile assigned; the outline ignores the car.")
		return false
	var required: Dictionary[String, float] = {"full_speed_kph": profile.full_speed_kph}
	return not TuningTable.any_zero(profile, required, "CarOutline", "the outline ignores the car")


## The car's speed as a share of `full_speed_kph`, 0 at rest and held at 1
## above it. Pure, so `verify_vehicle.gd` can ask it.
func speed_share(speed_kph: float) -> float:
	return clampf(speed_kph / profile.full_speed_kph, 0.0, 1.0)


func _physics_process(_delta: float) -> void:
	# Snapped, so suspension jitter at rest and a steady cruise write nothing:
	# 1/256 is under any visible change in the line.
	var share: float = snappedf(speed_share(_car.linear_velocity.length() * 3.6), 1.0 / 256.0)
	# Written on a change only: the global reaches every material that reads it.
	if share != _speed:
		_speed = share
		RenderingServer.global_shader_parameter_set(SPEED_PARAMETER, share)
