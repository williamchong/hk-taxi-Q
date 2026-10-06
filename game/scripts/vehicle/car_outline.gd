class_name CarOutline
extends Node3D
## The outline's answers to the car (`P3-65`, `Q158`, the user's ask): the
## city's line thins and fades with the car's speed, and the car carries a thin rim in
## its own outline colour while a slide counts — seeping in and draining away
## rather than snapping, with a short light tail behind the slide
## (`car_outline.gdshader`). The tier picks no colour yet: the rim taking the
## drift bonus's colour, as the sparks do, is the user's next step.
##
## The speed goes out as the global shader parameter `outline_speed`, 0 at rest
## to 1 at `full_speed_kph`, which `cel_outline.gdshader` reads. ⚠️ A global is
## process-wide, like `LightingRig`'s `exposure_anchor`: one car sets it, and a
## second car with this node would fight the first. The player's car carries it;
## an AI car (`B3`) must not.
##
## The tier arrives as `DriftSparks`' does — `TaxiHire` connects
## `FareSystem.drift_tier_changed` to `show_tier` — so the rim shows on the
## slides the sparks and the receipt count. Under `--fares=off` nothing calls it and the rim
## never shows.

const HULL_SHADER: Shader = preload("res://assets/shaders/car_outline.gdshader")
const SPEED_PARAMETER: StringName = &"outline_speed"
## Below this the drained ink is hidden and costs no draw.
const INK_GONE_M: float = 0.001

## Assigned in `taxi_tyre.tscn`; the values and their reasons are
## `tuning/car_outline.md`'s.
@export var profile: CarOutlineProfile

var _car: VehicleController = null
var _hull: MeshInstance3D = null
var _material: ShaderMaterial = null
var _speed: float = -1.0
## The rim's width now and the width the tier asks for; the one eases to the other.
var _width: float = 0.0
var _target: float = 0.0


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
		push_error("CarOutline: the car has no mesh; no rim will show.")
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


## The rim's width at a tier: none at -1, one width at every counted tier.
func width_of(tier: int) -> float:
	return profile.hull_width_m if tier >= 0 else 0.0


## The tier the rim eases to: `SkillTracker.drift_tier`'s -1 drains it.
func show_tier(tier: int) -> void:
	_target = width_of(tier)


## One tick of the ease: toward the target at `seep_s` while growing and
## `drain_s` while shrinking, exponential, so it never arrives in a step. Pure,
## so `verify_vehicle.gd` can step it.
func eased(width: float, target: float, delta: float) -> float:
	var tau: float = profile.seep_s if target > width else profile.drain_s
	return lerpf(width, target, 1.0 - exp(-delta / tau))


func _physics_process(delta: float) -> void:
	var velocity: Vector3 = _car.linear_velocity
	# Snapped, so suspension jitter at rest and a steady cruise write nothing:
	# 1/256 is under any visible change in the line.
	var share: float = snappedf(speed_share(velocity.length() * 3.6), 1.0 / 256.0)
	# Written on a change only: the global reaches every material that reads it.
	if share != _speed:
		_speed = share
		RenderingServer.global_shader_parameter_set(SPEED_PARAMETER, share)
	if _hull != null:
		_ink(velocity, delta)


## The rim this tick: its eased width, and the drag — opposite the car's travel,
## in the mesh's own space, reaching as far as the sideways speed carries it.
func _ink(velocity: Vector3, delta: float) -> void:
	_width = eased(_width, _target, delta)
	var showing: bool = _width > INK_GONE_M
	_hull.visible = showing
	if not showing:
		return
	var sideways: float = absf(_car.global_basis.x.dot(velocity))
	var smear: float = minf(sideways * profile.smear_s, profile.smear_max_m)
	var drag: Vector3 = -(_hull.global_basis.inverse() * velocity)
	# The lean and the tail grow and shrink with the rim, seeping and draining.
	var grown: float = _width / profile.hull_width_m
	_material.set_shader_parameter(&"hull_width_m", _width)
	_material.set_shader_parameter(&"trail_width_m", profile.trail_width_m * grown)
	_material.set_shader_parameter(&"smear_m", smear * grown)
	if drag.length_squared() > 1e-4:
		_material.set_shader_parameter(&"smear_dir", drag.normalized())


## The rim: the body's mesh again on the hull shader, a child of the body so it
## rides with it, hidden until a slide counts.
func _build_hull(body: MeshInstance3D) -> void:
	var box: AABB = body.mesh.get_aabb()
	_material = ShaderMaterial.new()
	_material.shader = HULL_SHADER
	_material.set_shader_parameter(&"hull_centre", box.get_center())
	_material.set_shader_parameter(&"hull_half", box.size * 0.5)
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
