class_name CarOutline
extends Node3D
## The outline's answers to the car (`P3-65`, `Q158`, the user's ask): the
## city's line thins and fades with the car's speed, and while a slide counts
## the end of the car that is moving most — the tail swinging out — leaves an
## afterimage in the car's own outline colour, seeping in and draining away
## rather than snapping (`car_outline.gdshader`). The tier picks no colour yet:
## the afterimage taking the drift bonus's colour, as the sparks do, is the
## user's next step.
##
## The speed goes out as the global shader parameter `outline_speed`, 0 at rest
## to 1 at `full_speed_kph`, which `cel_outline.gdshader` reads. ⚠️ A global is
## process-wide, like `LightingRig`'s `exposure_anchor`: one car sets it, and a
## second car with this node would fight the first. The player's car carries it;
## an AI car (`B3`) must not.
##
## The tier arrives as `DriftSparks`' does — `TaxiHire` connects
## `FareSystem.drift_tier_changed` to `show_tier` — so the afterimage shows on
## the slides the sparks and the receipt count. Under `--fares=off` nothing
## calls it and it never shows.

const HULL_SHADER: Shader = preload("res://assets/shaders/car_outline.gdshader")
const SPEED_PARAMETER: StringName = &"outline_speed"
## Below this the drained afterimage is hidden and costs no draw.
const INK_GONE_M: float = 0.001

## Assigned in `taxi_tyre.tscn`; the values and their reasons are
## `tuning/car_outline.md`'s.
@export var profile: CarOutlineProfile

var _car: VehicleController = null
var _hull: MeshInstance3D = null
var _material: ShaderMaterial = null
var _speed: float = -1.0
## The afterimage's width now and the width the tier asks for; the one eases to
## the other.
var _width: float = 0.0
var _target: float = 0.0
## The body mesh's length axis, and its two ends' midpoints, in its own space —
## the same box the shader measures `along` in.
var _length_axis: Vector3 = Vector3.BACK
var _front_end: Vector3 = Vector3.ZERO
var _rear_end: Vector3 = Vector3.ZERO


func _ready() -> void:
	set_physics_process(false)
	_car = VehicleController.above(self)
	if _car == null:
		push_error("CarOutline: not under a VehicleController; the outline ignores the car.")
		return
	if not usable():
		return
	# The body is the first mesh in the car, ahead of the door leaf and the
	# wheels — `VehicleLamps`' search, for the same reason: the asset names it.
	var found: Array[Node] = _car.find_children("*", "MeshInstance3D", true, false)
	if found.is_empty():
		push_error("CarOutline: the car has no mesh; no afterimage will show.")
	else:
		_build_hull(found[0] as MeshInstance3D)
	set_physics_process(true)


func _exit_tree() -> void:
	# Process-wide: a car leaving must not leave the city drawn at its speed.
	if _speed >= 0.0:
		RenderingServer.global_shader_parameter_set(SPEED_PARAMETER, 0.0)


## Whether the table is whole: a profile, the city's line to take the colour
## from, and no key at zero. Pure over `profile`, so `verify_vehicle.gd` can ask
## it of a car that never entered a tree.
func usable() -> bool:
	if profile == null:
		push_error("CarOutline: no CarOutlineProfile assigned; the outline ignores the car.")
		return false
	if profile.city_line == null:
		push_error("CarOutline: %s names no city line." % profile.resource_path)
		return false
	var required: Dictionary[String, float] = {
		"full_speed_kph": profile.full_speed_kph,
		"hull_width_m": profile.hull_width_m,
		"seep_s": profile.seep_s,
		"drain_s": profile.drain_s,
		"smear_s": profile.smear_s,
		"smear_max_m": profile.smear_max_m,
	}
	return not TuningTable.any_zero(profile, required, "CarOutline", "the outline ignores the car")


## How far along `outline_speed` is at a speed: 0 at rest, 1 at and above
## `full_speed_kph`.
func speed_share(speed_kph: float) -> float:
	return clampf(speed_kph / profile.full_speed_kph, 0.0, 1.0)


## The afterimage's width at a tier: none at -1, one width at every counted tier.
func width_of(tier: int) -> float:
	return profile.hull_width_m if tier >= 0 else 0.0


## The tier the afterimage eases to: `SkillTracker.drift_tier`'s -1 drains it.
func show_tier(tier: int) -> void:
	_target = width_of(tier)


## One tick of the ease: toward the target at `seep_s` while growing and
## `drain_s` while shrinking, exponential, so it never arrives in a step. Pure,
## so `verify_vehicle.gd` can step it.
func eased(width: float, target: float, delta: float) -> float:
	var tau: float = profile.seep_s if target > width else profile.drain_s
	return lerpf(width, target, 1.0 - exp(-delta / tau))


## Which end of the car moves most across its length: +1 the end `axis` points
## to, -1 the other, the rear on a tie. Pure, so `verify_vehicle.gd` can ask it.
static func moving_end(front: Vector3, rear: Vector3, axis: Vector3) -> float:
	var along: Vector3 = axis.normalized()
	return 1.0 if front.slide(along).length() > rear.slide(along).length() else -1.0


func _physics_process(delta: float) -> void:
	# Snapped, so suspension jitter at rest and a steady cruise write nothing:
	# 1/256 is under any visible change in the line.
	var share: float = snappedf(speed_share(_car.linear_velocity.length() * 3.6), 1.0 / 256.0)
	# Written on a change only: the global reaches every material that reads it.
	if share != _speed:
		_speed = share
		RenderingServer.global_shader_parameter_set(SPEED_PARAMETER, share)
	if _hull != null:
		_ink(delta)


## The afterimage this tick: its eased width, which end it hangs off, and the
## drag — against that end's own velocity, as far as its sideways speed carries.
func _ink(delta: float) -> void:
	_width = eased(_width, _target, delta)
	var showing: bool = _width > INK_GONE_M
	_hull.visible = showing
	if not showing:
		return
	var front: Vector3 = _velocity_at(_hull.global_transform * _front_end)
	var rear: Vector3 = _velocity_at(_hull.global_transform * _rear_end)
	var along: Vector3 = (_hull.global_basis * _length_axis).normalized()
	var end_sign: float = moving_end(front, rear, along)
	var moving: Vector3 = front if end_sign > 0.0 else rear
	var smear: float = minf(moving.slide(along).length() * profile.smear_s, profile.smear_max_m)
	# The drag grows and shrinks with the width, seeping and draining.
	_material.set_shader_parameter(&"hull_width_m", _width)
	_material.set_shader_parameter(&"end_axis", _length_axis * end_sign)
	_material.set_shader_parameter(&"smear_m", smear * _width / profile.hull_width_m)
	var drag: Vector3 = -(_hull.global_basis.inverse() * moving)
	if drag.length_squared() > 1e-4:
		_material.set_shader_parameter(&"smear_dir", drag.normalized())


## The car's velocity at a point, its spin included —
## `VehicleController.rear_axle_velocity`'s form, measured from the car's origin.
func _velocity_at(point: Vector3) -> Vector3:
	return _car.linear_velocity + _car.angular_velocity.cross(point - _car.global_position)


## The afterimage: the body's mesh again on the hull shader, a child of the body
## so it rides with it, hidden until a slide counts.
func _build_hull(body: MeshInstance3D) -> void:
	var box: AABB = body.mesh.get_aabb()
	_material = ShaderMaterial.new()
	_material.shader = HULL_SHADER
	_material.set_shader_parameter(&"hull_centre", box.get_center())
	_material.set_shader_parameter(&"hull_half", box.size * 0.5)
	_material.set_shader_parameter(&"drag_from", profile.drag_from)
	_material.set_shader_parameter(&"ghost", profile.ghost)
	# The car's length runs along the box's longer horizontal side.
	_length_axis = Vector3.RIGHT if box.size.x > box.size.z else Vector3.BACK
	var reach: Vector3 = _length_axis * maxf(box.size.x, box.size.z) * 0.5
	_front_end = box.get_center() + reach
	_rear_end = box.get_center() - reach
	_material.set_shader_parameter(&"rim_colour", profile.rim_colour)
	var darkness: Variant = profile.city_line.get_shader_parameter(&"surface_darkness")
	_material.set_shader_parameter(&"ink_darkness", darkness)
	_hull = MeshInstance3D.new()
	_hull.name = "OutlineHull"
	_hull.mesh = body.mesh
	_hull.material_override = _material
	_hull.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_hull.visible = false
	# Deferred: the car is still readying its children when this runs.
	body.add_child.call_deferred(_hull)
