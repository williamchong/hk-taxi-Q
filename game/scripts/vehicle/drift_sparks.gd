class_name DriftSparks
extends Node3D
## Whether the slide counts, and for how long (`P3-58`): sparks off the rear
## tyres in a colour per tier — the tier is `SkillTracker.drift_tier`, the
## SAME meter that pays, handed in by `TaxiHire` off `FareSystem`'s
## `drift_tier_changed`. A slide the tracker is not counting lights nothing, so
## the sparks and the receipt cannot disagree; nothing here reads a slip.
##
## 🚫 **No boost.** Mario Kart's sparks are a speed reward; these are its
## legibility only (`Q153`: a drift buys line, never pace). Nothing here is read
## by the physics.
##
## Presentation only, like `PassengerEmote`: whatever owns the fare calls
## `show_tier`; the car never does, and an AI taxi on the same body (`B3`) has no
## tracker to light it. Under `--fares=off` nothing calls it and the sparks
## never light.
##
## Runs on the physics tick only while lit, to follow the rear contacts and time
## the burst: the calls arrive from `FareSystem._physics_process`. One
## `CPUParticles3D` per rear wheel, each one draw call while it has sparks up —
## CPU particles for `SkidMarks`' reason, the web build's renderer.

## The sparks' dials and colours. Assigned in `taxi_tyre.tscn`; the values and
## their reasons are `tuning/drift_sparks.md`'s.
@export var profile: DriftSparksProfile

var _wheels: Array[VehicleWheel3D] = []
var _sparks: Array[CPUParticles3D] = []
var _tier: int = -1
## Seconds left in the flare a step up started.
var _burst_left_s: float = 0.0


func _ready() -> void:
	set_physics_process(false)
	if not usable():
		return
	# A child is ready before its parent, and the car splits its axles in its
	# own `_ready`: asked now, it has no rear wheels.
	_setup.call_deferred()


func _setup() -> void:
	var car := get_parent() as VehicleController
	if car == null:
		push_error("DriftSparks: not a child of a VehicleController; no spark will show.")
		return
	_wheels = car.rear_wheels()
	for _wheel: VehicleWheel3D in _wheels:
		_sparks.append(_build_sparks())


## Whether the table is whole: a profile, at least one colour, and no zero
## anywhere — every key has an export floor above zero, so a zero is a missing
## key. Pure over `profile`, so `verify_vehicle.gd` can ask it of a car that
## never entered a tree.
func usable() -> bool:
	if profile == null:
		push_error("DriftSparks: no DriftSparksProfile assigned; no spark will show.")
		return false
	var required: Dictionary[String, float] = {
		"colours": float(profile.colours.size()),
		"amount": float(profile.amount),
		"lifetime_s": profile.lifetime_s,
		"speed_mps": profile.speed_mps,
		"length_m": profile.length_m,
		"thickness_m": profile.thickness_m,
		"burst_s": profile.burst_s,
		"burst_scale": profile.burst_scale,
	}
	return not TuningTable.any_zero(profile, required, "DriftSparks", "no spark will show")


## The tier the sparks show: `SkillTracker.drift_tier`'s -1 puts them out; 0 and
## up take `colours[tier]`, the last colour past the end. A step up flares.
func show_tier(tier: int) -> void:
	if _sparks.is_empty():
		return
	if tier > _tier and tier > 0:
		_burst_left_s = profile.burst_s
	_tier = tier
	var colour: Color = colour_of(tier)
	var shown: bool = colour.a > 0.0
	if not shown:
		# Its countdown stops with the physics tick, so a flare cut short would
		# otherwise come back on the next slide's first frame.
		_burst_left_s = 0.0
	for spark: CPUParticles3D in _sparks:
		spark.color = colour
		spark.emitting = shown
	_follow()
	set_physics_process(shown)


## The colour a tier shows in; clear at -1, so a lit spark is a counted slide.
func colour_of(tier: int) -> Color:
	if tier < 0 or profile == null or profile.colours.is_empty():
		return Color(0.0, 0.0, 0.0, 0.0)
	return profile.colours[mini(tier, profile.colours.size() - 1)]


func _physics_process(delta: float) -> void:
	_burst_left_s = maxf(_burst_left_s - delta, 0.0)
	_follow()


## Each emitter at its wheel's contact, turned with the car so the sparks fly
## off behind it; grown while a flare lasts.
func _follow() -> void:
	var grown: float = profile.burst_scale if _burst_left_s > 0.0 else 1.0
	var facing: Basis = get_parent_node_3d().global_basis
	for k: int in _sparks.size():
		var wheel: VehicleWheel3D = _wheels[k]
		var spark: CPUParticles3D = _sparks[k]
		var origin: Vector3 = (
			wheel.get_contact_point() if wheel.is_in_contact() else wheel.global_position
		)
		spark.global_transform = Transform3D(facing, origin)
		spark.scale_amount_min = grown
		spark.scale_amount_max = grown


## One rear wheel's emitter: thin unshaded streaks, stretched along their
## velocity, thrown back and up and falling.
func _build_sparks() -> CPUParticles3D:
	var streak := BoxMesh.new()
	streak.size = Vector3(profile.thickness_m, profile.length_m, profile.thickness_m)
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.vertex_color_use_as_albedo = true
	streak.material = material
	var spark := CPUParticles3D.new()
	spark.name = "Sparks"
	spark.mesh = streak
	spark.amount = profile.amount
	spark.lifetime = profile.lifetime_s
	spark.local_coords = false
	spark.emitting = false
	# The car's +Z is its tail: back, and up off the road.
	spark.direction = Vector3(0.0, 1.0, 1.0)
	spark.spread = profile.spread_deg
	spark.initial_velocity_min = profile.speed_mps
	spark.initial_velocity_max = profile.speed_mps
	spark.particle_flag_align_y = true
	spark.top_level = true
	spark.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(spark)
	return spark
