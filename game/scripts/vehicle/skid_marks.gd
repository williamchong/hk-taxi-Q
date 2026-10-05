class_name SkidMarks
extends Node3D
## What the tyres are doing, on the road (`P3-57`): a mark under every wheel and
## smoke off the rears while a tyre is past its peak — sliding, spinning or
## locked — whether or not the slide pays. Physical truth, never a score: the
## sparks that say a drift COUNTS are `DriftSparks`', off the tracker that pays.
##
## Reads `TyreVehicleController.wheel_slips`, the model's own slip, and not
## `VehicleWheel3D.get_skidinfo()`: that is the engine's tyres, which this car
## turns off. On a car without the model, or a tyre table with a zero key, there
## is no slip to read and the rig stays inert, as it does on a zero key of its
## own (`Q150`).
##
## ⚠️ **One draw call for every mark, however long the drive.** One `ArrayMesh`
## of `capacity` quads, allocated once with every corner at the origin, and
## each new piece uploaded in place — four corners, 48 bytes — with
## `mesh_surface_update_vertex_region`. Positions only, so the vertex stream is
## twelve bytes a corner; `_ready` asks the renderer and refuses any other
## stride rather than writing a misaligned buffer.
##
## On the physics tick, after the car's own (a child steps after its parent),
## so a mark is laid where the tick left the wheel, and the drive harness's
## replay lays the same marks.
##
## Smoke is `CPUParticles3D`, not `GPUParticles3D`: the web build runs the
## Compatibility renderer, where CPU particles draw everywhere, and a few dozen
## puffs are cheap on the CPU. One emitter per rear wheel, each one draw call.

## The rig's dials. Assigned in `taxi_tyre.tscn`; the values and their reasons
## are `tuning/skid_marks.md`'s.
@export var profile: SkidMarksProfile

## Bytes per corner in a positions-only, uncompressed vertex stream.
const VERTEX_STRIDE: int = 12

var _car: TyreVehicleController = null
var _wheels: Array[VehicleWheel3D] = []
var _strip: SkidStrip = null
var _mesh: ArrayMesh = null
## One emitter per rear wheel. `tyre_wheels` lists the front axle first, so
## emitter `k` is the wheel at `_first_rear + k`.
var _smoke: Array[CPUParticles3D] = []
var _first_rear: int = 0


func _ready() -> void:
	set_physics_process(false)
	if not usable():
		return
	# A child is ready before its parent, and the car lists its wheels in its
	# own `_ready`: asked now, it has none.
	_setup.call_deferred()


func _setup() -> void:
	_car = get_parent() as TyreVehicleController
	if _car == null:
		push_error("SkidMarks: not a child of a TyreVehicleController; no mark will show.")
		return
	_wheels = _car.tyre_wheels()
	if _wheels.is_empty():
		# The car is parked on a tyre table it cannot run; its own error says why.
		return
	_strip = SkidStrip.new(_wheels.size(), profile)
	if not _build_mesh():
		return
	var rears: int = _car.rear_wheels().size()
	_first_rear = _wheels.size() - rears
	for _k: int in rears:
		_smoke.append(_build_smoke())
	set_physics_process(true)


## Whether the table is whole: a profile, and no zero anywhere — every key has
## an export floor above zero, so a zero is a missing key. Pure over `profile`,
## so `verify_vehicle.gd` can ask it of a car that never entered a tree.
func usable() -> bool:
	if profile == null:
		push_error("SkidMarks: no SkidMarksProfile assigned; no mark will show.")
		return false
	var required: Dictionary[String, float] = {
		"mark_from_slip": profile.mark_from_slip,
		"mark_width_m": profile.mark_width_m,
		"lift_m": profile.lift_m,
		"max_step_m": profile.max_step_m,
		"capacity": float(profile.capacity),
		"mark_colour.a": profile.mark_colour.a,
		"smoke_from_slip": profile.smoke_from_slip,
		"smoke_amount": float(profile.smoke_amount),
		"smoke_lifetime_s": profile.smoke_lifetime_s,
		"smoke_start_m": profile.smoke_start_m,
		"smoke_end_m": profile.smoke_end_m,
		"smoke_colour.a": profile.smoke_colour.a,
	}
	return not TuningTable.any_zero(profile, required, "SkidMarks", "no mark will show")


## How many pieces of mark have been laid since the car was built.
func laid() -> int:
	return _strip.laid if _strip != null else 0


func _physics_process(_delta: float) -> void:
	var slips: PackedFloat32Array = _car.wheel_slips()
	for i: int in _wheels.size():
		var wheel: VehicleWheel3D = _wheels[i]
		var grounded: bool = wheel.is_in_contact()
		var point: Vector3 = wheel.get_contact_point() if grounded else Vector3.ZERO
		var normal: Vector3 = wheel.get_contact_normal() if grounded else Vector3.UP
		var slot: int = _strip.step(i, grounded, point, normal, wheel.global_basis.x, slips[i])
		if slot >= 0:
			_upload(slot)
	for k: int in _smoke.size():
		_puff(_smoke[k], _wheels[_first_rear + k], slips[_first_rear + k])


## The ring, empty: every corner at the origin. Refuses a renderer whose vertex
## stream is not the twelve bytes a corner `_upload` writes.
func _build_mesh() -> bool:
	var arrays: Array = []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = _strip.positions()
	arrays[Mesh.ARRAY_INDEX] = _strip.indices()
	_mesh = ArrayMesh.new()
	_mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	var corners: int = _strip.positions().size()
	var stride: int = RenderingServer.mesh_surface_get_format_vertex_stride(
		_mesh.surface_get_format(0), corners
	)
	if stride != VERTEX_STRIDE:
		push_error(
			(
				"SkidMarks: the renderer's vertex stride is %d bytes, not %d; no mark will show."
				% [stride, VERTEX_STRIDE]
			)
		)
		return false
	# The marks are wherever the car has been: never culled by the ring's
	# bounds at build time, which are a point.
	_mesh.custom_aabb = AABB(Vector3(-1.0e5, -1.0e3, -1.0e5), Vector3(2.0e5, 2.0e3, 2.0e5))
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.cull_mode = BaseMaterial3D.CULL_DISABLED
	material.albedo_color = profile.mark_colour
	_mesh.surface_set_material(0, material)
	var marks := MeshInstance3D.new()
	marks.name = "Marks"
	marks.mesh = _mesh
	marks.top_level = true
	marks.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(marks)
	marks.global_transform = Transform3D.IDENTITY
	return true


## Writes the four corners of `slot` into the mesh in place.
func _upload(slot: int) -> void:
	var first: int = slot * SkidStrip.CORNERS
	var corners: PackedVector3Array = _strip.positions().slice(first, first + SkidStrip.CORNERS)
	RenderingServer.mesh_surface_update_vertex_region(
		_mesh.get_rid(), 0, first * VERTEX_STRIDE, corners.to_byte_array()
	)


## One rear wheel's smoke: low-poly puffs that rise, grow and fade to clear.
func _build_smoke() -> CPUParticles3D:
	var puff := SphereMesh.new()
	puff.radius = 0.5
	puff.height = 1.0
	puff.radial_segments = 6
	puff.rings = 3
	var material := StandardMaterial3D.new()
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.vertex_color_use_as_albedo = true
	puff.material = material
	var growth := Curve.new()
	var ratio: float = profile.smoke_end_m / profile.smoke_start_m
	growth.max_value = maxf(ratio, 1.0)
	growth.add_point(Vector2(0.0, 1.0))
	growth.add_point(Vector2(1.0, ratio))
	var fade := Gradient.new()
	fade.set_color(0, profile.smoke_colour)
	fade.set_color(1, Color(profile.smoke_colour, 0.0))
	var smoke := CPUParticles3D.new()
	smoke.name = "Smoke"
	smoke.mesh = puff
	smoke.amount = profile.smoke_amount
	smoke.lifetime = profile.smoke_lifetime_s
	smoke.local_coords = false
	smoke.emitting = false
	smoke.direction = Vector3.UP
	smoke.spread = profile.smoke_spread_deg
	smoke.gravity = Vector3.ZERO
	smoke.initial_velocity_min = profile.smoke_rise_mps
	smoke.initial_velocity_max = profile.smoke_rise_mps
	smoke.scale_amount_min = profile.smoke_start_m
	smoke.scale_amount_max = profile.smoke_start_m
	smoke.scale_amount_curve = growth
	smoke.color_ramp = fade
	smoke.top_level = true
	smoke.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(smoke)
	return smoke


## Smoke from `wheel`'s contact while its slip is over the bar.
func _puff(smoke: CPUParticles3D, wheel: VehicleWheel3D, slip: float) -> void:
	var on: bool = wheel.is_in_contact() and slip >= profile.smoke_from_slip
	smoke.emitting = on
	if on:
		smoke.global_position = wheel.get_contact_point()
