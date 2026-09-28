class_name PassengerEmote
extends Node3D
## The passenger's face, popped out of the cab (`P3-49`, `Q145`): a grin every
## time a skill pays, and rage when the clock runs out and they walk.
##
## The node sits where the passenger sits — the rear kerbside seat, under the
## roof — and each emote is instanced HERE, rises through the roof and out of
## the car, and shrinks away: a face emerging from the back seat, which is what
## the user asked for, rather than a sticker on the HUD. The meshes are
## `tools/make_emote.py`'s, one `.glb` per face, their features on -Z so that
## `look_at` turns the face to the camera.
##
## Presentation only, like `TaxiDoor` and `VehicleLamps`: nothing here is read
## by the physics and no emote carries a collider. Whatever owns the fare calls
## `show`; the car never does, and an AI taxi on the same body (`B3`) has
## nobody to grin.
##
## Runs on the physics tick for the door's reason: the calls arrive from
## `FareSystem._physics_process`, and the drive harness's frames are graded
## byte for byte, so the rise must advance on the clock that is fixed.
##
## Unshaded, on the fare guide's pattern: a glyph in the world is drawn at its
## own colour, not lit as a surface — the `.glb`'s material name is one the
## import hook does not dispatch, so it arrives with its vertex colours on and
## nothing else, and the override here is the whole material.

enum Face { GRIN, ANGRY, HURT }

## The grin, shown when a skill pays. Assign in the scene: `emote_grin.glb`.
@export var grin: PackedScene
## The rage, shown when the passenger walks. Assign in the scene: `emote_angry.glb`.
@export var angry: PackedScene
## The daze, shown when a penalty docks (`P3-50`). Assign in the scene:
## `emote_hurt.glb`.
@export var hurt: PackedScene

## The face's dials — rise, life, pop, shrink and how many at once. Assigned in
## `taxi.tscn`; the values and their reasons are `tuning/passenger_emote.md`'s.
## ⚠️ Read through `usable()` before a face goes up: the profile declares no
## defaults, so a missing key is a zero, and `_physics_process` divides by one.
@export var profile: PassengerEmoteProfile

## The faces up now, oldest first, and each one's age.
var _live: Array[Node3D] = []
var _ages: PackedFloat64Array = PackedFloat64Array()
var _material: StandardMaterial3D = null


func _ready() -> void:
	set_physics_process(false)


## Whether the table is whole: a profile, and no zero anywhere — every key has
## an export floor above zero, so a zero is a missing key. Loud on every call by
## design — a missing key is a build defect, not a state to remember quietly —
## and pure over `profile`, so `verify_vehicle.gd` can ask it of a car that
## never entered a tree and again after swapping a zeroed table in.
func usable() -> bool:
	if profile == null:
		push_error("PassengerEmote: no PassengerEmoteProfile assigned; no face will show.")
		return false
	var required: Dictionary[String, float] = {
		"rise_m": profile.rise_m,
		"life_s": profile.life_s,
		"pop_s": profile.pop_s,
		"shrink_s": profile.shrink_s,
		"most_live": float(profile.most_live),
	}
	return not TuningTable.any_zero(profile, required, "PassengerEmote", "no face will show")


## The one material every face wears: unshaded, its vertex colours as albedo.
## Built on first use rather than in `_ready`, so `verify_vehicle.gd` can
## grade a face on a car that is never added to a tree.
func _unshaded() -> StandardMaterial3D:
	if _material == null:
		_material = StandardMaterial3D.new()
		_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		_material.vertex_color_use_as_albedo = true
		# The `.glb` writes `COLOR_0` in sRGB (`Q27`); the flag is the
		# `BaseMaterial3D` half of that fix, which the import hook also sets
		# and an override would otherwise lose.
		_material.vertex_color_is_srgb = true
	return _material


func _scene_of(face: Face) -> PackedScene:
	match face:
		Face.GRIN:
			return grin
		Face.ANGRY:
			return angry
		Face.HURT:
			return hurt
	return null


## Pop `face` out of the seat.
func show_face(face: Face) -> void:
	if not usable():
		return
	var packed: PackedScene = _scene_of(face)
	if packed == null:
		push_warning("PassengerEmote has no scene for face %d; nothing to show." % face)
		return
	var instance := packed.instantiate() as Node3D
	if instance == null:
		push_warning("PassengerEmote: %s did not instantiate as a Node3D." % packed.resource_path)
		return
	for node: Node in instance.find_children("*", "MeshInstance3D", true, false):
		(node as MeshInstance3D).material_override = _unshaded()
	if _live.size() >= profile.most_live:
		_live[0].queue_free()
		_live.remove_at(0)
		_ages.remove_at(0)
	add_child(instance)
	instance.position = Vector3.ZERO
	instance.scale = Vector3.ONE * 0.001
	_live.append(instance)
	_ages.append(0.0)
	set_physics_process(true)


## How many faces are up.
func live() -> int:
	return _live.size()


func _physics_process(delta: float) -> void:
	var camera: Camera3D = get_viewport().get_camera_3d()
	var index: int = 0
	while index < _live.size():
		var age: float = _ages[index] + delta
		var face: Node3D = _live[index]
		if age >= profile.life_s:
			face.queue_free()
			_live.remove_at(index)
			_ages.remove_at(index)
			continue
		_ages[index] = age
		face.position = Vector3.UP * profile.rise_m * _eased(age / profile.life_s)
		face.scale = Vector3.ONE * maxf(_size_at(age), 0.001)
		if camera != null:
			# `look_at` points -Z at the target, which is the side the face is
			# built on. Kept upright: the roll a chase camera has is not the
			# passenger's.
			var to_camera: Vector3 = camera.global_position - face.global_position
			if not to_camera.is_zero_approx():
				face.look_at(camera.global_position, Vector3.UP)
		index += 1
	if _live.is_empty():
		set_physics_process(false)


## 0..1 of the rise at `t` of the life: fast out of the seat, slowing to the top.
static func _eased(t: float) -> float:
	var clamped: float = clampf(t, 0.0, 1.0)
	return 1.0 - (1.0 - clamped) * (1.0 - clamped)


## The face's scale at `age`: popped up over `pop_s`, full, then shrunk away
## over the last `shrink_s`.
func _size_at(age: float) -> float:
	var popped: float = smoothstep(0.0, profile.pop_s, age)
	var left: float = profile.life_s - age
	var kept: float = smoothstep(0.0, profile.shrink_s, left)
	return minf(popped, kept)
