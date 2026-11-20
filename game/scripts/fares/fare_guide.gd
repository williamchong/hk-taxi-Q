extends Node3D
## The world-space guide to the fare (`P3-5a`, `Q142`): an arrow over the
## taxi pointing at the target, and a ring pulsing on the road where the
## target is, with a solid pointer bobbing over every ring so a target reads
## from blocks away. Both answer distance — small and red far off, large and
## green close — from `tuning/guide.tres`.
##
## In the world, not the HUD — both references with a destination do this, and
## `hud_layout.tres` reserves no slot for it (`Q80`). It points where
## `FareFace` says: the closest pending customer while idle — the arrow alone,
## no ring — and the destination once hailed.
## **As the crow flies.** `Q138` holds the next-junction arrow for after the
## first fare review; in a one-way grid this one will sometimes point down a
## street that cannot be entered, and `GAME_DESIGN.md`'s acceptance test is a
## drive with it off — `--fares=off` takes it with the loop.
##
## Turned and sized every frame off the car's transform alone; the target is
## read from the loop at its own 5 Hz, inside its `sampled` signal (`hud.gd`
## says why nothing here may poll the system).

const PropBatch = preload("res://scripts/city/prop_batch.gd")

## The pointer's sides: a four-sided spike reads as a diamond from any side.
## Shape, not a dial; its size and motion are `guide.tres`'s.
const POINTER_SIDES: int = 4
## The baked shade of each side in turn, so an unshaded pointer still reads as
## a solid at any hour; the cap is full colour.
const POINTER_SHADES: Array[float] = [1.0, 0.8, 0.62, 0.8]

## The loop whose target this shows. Assign in the scene, AFTER the system in
## tree order so its `usable()` is decided before this reads it.
@export var fares: FareSystem
## The car it floats over.
@export var vehicle: Node3D

var _profile: FareGuideProfile = null
## Where the arrow points, as of the last sample.
var _target: FareFace.Target = FareFace.Target.new()
var _arrow: MeshInstance3D = null
var _ring: MeshInstance3D = null
## One ring per waiting customer (`FareSystem.pickups`), as one multimesh:
## shown while no one is aboard, pulsed with the destination's.
var _pending: MultiMeshInstance3D = null
var _pending_at: PackedVector3Array = PackedVector3Array()
## Indices into `_pending_at` drawn at zero scale: `FareSystem.withheld_pickups`.
var _withheld: PackedInt32Array = PackedInt32Array()
var _pending_material: StandardMaterial3D = null
var _material: StandardMaterial3D = null
var _ring_material: StandardMaterial3D = null
## The solid pointer over the destination ring, and one over every pending
## customer's ring: seen from blocks away where a flat ring on the road is not.
var _pointer: MeshInstance3D = null
var _pending_pointers: MultiMeshInstance3D = null
var _pointer_material: StandardMaterial3D = null
var _pending_pointer_material: StandardMaterial3D = null
## The pointers' bob and spin, as fractions of a cycle.
var _bob_phase: float = 0.0
var _spin_phase: float = 0.0
## The closeness last painted, quantised, so a frame that moved a centimetre
## writes no material.
var _painted: int = -1
var _pulse_s: float = 0.0


func _ready() -> void:
	if Cmdline.off(FareSystem.FARES_ARG) or fares == null or vehicle == null or not fares.usable():
		set_process(false)
		visible = false
		return
	_profile = load(FareGuideProfile.PATH) as FareGuideProfile
	if _profile == null or _profile.far_m <= _profile.near_m:
		push_warning(
			"fare_guide: %s did not load, or far_m <= near_m; no guide" % FareGuideProfile.PATH
		)
		set_process(false)
		visible = false
		return
	_material = _unshaded(1.0)
	_arrow = MeshInstance3D.new()
	_arrow.name = "Arrow"
	_arrow.mesh = arrow_mesh(1.0)
	_arrow.material_override = _material
	_arrow.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(_arrow)
	_ring_material = _unshaded(_profile.ring_alpha)
	_ring = MeshInstance3D.new()
	_ring.name = "Ring"
	_ring.mesh = ring_mesh(_profile.ring_radius_m, _profile.ring_width_m)
	_ring.material_override = _ring_material
	_ring.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_ring.top_level = true
	add_child(_ring)
	_pointer_material = _pointer_of(Color.WHITE)
	_pointer = MeshInstance3D.new()
	_pointer.name = "Pointer"
	_pointer.mesh = pointer_mesh(_profile.pointer_length_m, _profile.pointer_width_m, POINTER_SIDES)
	_pointer.material_override = _pointer_material
	_pointer.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_pointer.top_level = true
	add_child(_pointer)
	_pending_pointer_material = _pointer_of(_profile.pending_colour)
	_pending_material = _unshaded(_profile.ring_alpha)
	var pending: Color = _profile.pending_colour
	pending.a = _profile.ring_alpha
	_pending_material.albedo_color = pending
	_place_pending()
	visible = false
	fares.sampled.connect(_on_sampled)
	fares.pickups_changed.connect(_on_pickups_changed)
	_on_sampled()


## One ring per waiting customer, rebuilt whenever the loop's set of them
## changes — a handful, so a rebuild is cheap and the frame loop below walks
## only those.
func _place_pending() -> void:
	var shown: bool = _pending != null and _pending.visible
	if _pending != null:
		_pending.queue_free()
	if _pending_pointers != null:
		_pending_pointers.queue_free()
	_pending_at = PackedVector3Array()
	var placed: Array[Transform3D] = []
	for stop: Fare.Stop in fares.pickups():
		var at: Vector3 = stop.point + Vector3.UP * _profile.ring_lift_m
		_pending_at.append(at)
		placed.append(Transform3D(Basis.IDENTITY, at))
	_pending = PropBatch.batch(_ring.mesh, placed, "Pending")
	_pending.material_override = _pending_material
	_pending.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_pending.top_level = true
	_pending.visible = shown and not _pending_at.is_empty()
	add_child(_pending)
	_pending_pointers = PropBatch.batch(_pointer.mesh, placed, "PendingPointers")
	_pending_pointers.material_override = _pending_pointer_material
	_pending_pointers.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_pending_pointers.top_level = true
	_pending_pointers.visible = _pending.visible
	add_child(_pending_pointers)


func _on_pickups_changed() -> void:
	_place_pending()
	_on_sampled()


static func _unshaded(alpha: float) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.cull_mode = BaseMaterial3D.CULL_DISABLED
	if alpha < 1.0:
		material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.albedo_color = Color(1.0, 1.0, 1.0, alpha)
	return material


## Opaque, so it carries at range; the albedo tints the mesh's baked shades.
static func _pointer_of(colour: Color) -> StandardMaterial3D:
	var material: StandardMaterial3D = _unshaded(1.0)
	material.vertex_color_use_as_albedo = true
	colour.a = 1.0
	material.albedo_color = colour
	return material


func _on_sampled() -> void:
	var nearest: Fare.Stop = null
	_withheld = PackedInt32Array()
	if is_instance_valid(vehicle):
		nearest = fares.pending
		_withheld = fares.withheld
	# The face's rule for where a reader points, without the face's strings.
	_target = FareFace.target_of(fares.state, fares.fare, nearest)
	if visible != _target.has:
		visible = _target.has
	# The ring marks where the passenger gets out; a pending customer gets the
	# arrow alone (the user's call).
	if _ring.visible != _target.is_destination:
		_ring.visible = _target.is_destination
	_pointer.visible = _ring.visible
	# Every pending customer's ring while no one is aboard (the user's call).
	var pending_shown: bool = not _target.is_destination and not _pending_at.is_empty()
	if _pending.visible != pending_shown:
		_pending.visible = pending_shown
	_pending_pointers.visible = _pending.visible
	if _ring.visible:
		_ring.global_position = _target.point + Vector3.UP * _profile.ring_lift_m


func _process(delta: float) -> void:
	if not is_instance_valid(vehicle):
		return
	_pulse_s = fmod(_pulse_s + delta, 1.0 / maxf(_profile.pulse_hz, 0.001))
	var pulse: float = 1.0 + _profile.pulse_depth * sin(TAU * _pulse_s * _profile.pulse_hz)
	_bob_phase = fmod(_bob_phase + delta * _profile.pointer_bob_hz, 1.0)
	_spin_phase = fmod(_spin_phase + delta * _profile.pointer_spin_hz, 1.0)
	# The tip rises from `pointer_height_m` over the ring, never below it.
	var bob: float = _profile.pointer_bob_m * (0.5 + 0.5 * sin(TAU * _bob_phase))
	var hover := Vector3.UP * (_profile.pointer_height_m - _profile.ring_lift_m + bob)
	var spun := Transform3D(Basis(Vector3.UP, TAU * _spin_phase), Vector3.ZERO)
	# Hidden with the guide, the batches draw nothing: write them no transforms.
	if visible and _pending.visible:
		var pulsed := Transform3D(Basis.from_scale(Vector3(pulse, 1.0, pulse)), Vector3.ZERO)
		var hidden := Transform3D(Basis.from_scale(Vector3.ZERO), Vector3.ZERO)
		for index: int in _pending_at.size():
			var withheld: bool = _withheld.has(index)
			var placed: Transform3D = hidden if withheld else pulsed
			placed.origin = _pending_at[index]
			_pending.multimesh.set_instance_transform(index, placed)
			var pointed: Transform3D = hidden if withheld else spun
			pointed.origin = _pending_at[index] + hover
			_pending_pointers.multimesh.set_instance_transform(index, pointed)
	if not visible:
		return
	var at: Vector3 = vehicle.global_position + Vector3.UP * _profile.height_m
	var flat := Vector3(_target.point.x - at.x, 0.0, _target.point.z - at.z)
	global_position = at
	var apart: float = flat.length()
	var close: float = closeness(_profile, apart)
	_arrow.scale = Vector3.ONE * lerpf(_profile.arrow_far_m, _profile.arrow_near_m, close)
	# Painted in 64 steps: a colour is a material write, and a frame that
	# moved the car a centimetre should not make one.
	var step: int = roundi(close * 64.0)
	if step != _painted:
		_painted = step
		var ink: Color = _profile.far_colour.lerp(_profile.near_colour, close)
		_material.albedo_color = ink
		_pointer_material.albedo_color = ink
		ink.a = _profile.ring_alpha
		_ring_material.albedo_color = ink
	if _ring.visible:
		_ring.scale = Vector3(pulse, 1.0, pulse)
		spun.origin = _ring.global_position + hover
		_pointer.global_transform = spun
	if apart < 0.1:
		return
	# `-Z` is the arrow's nose (`arrow_mesh`), which is what `look_at` points.
	look_at(at + flat, Vector3.UP)


## How near the target is, 0 at `far_m` and beyond, 1 at `near_m` and inside,
## straight between. What the size and the colour are read off.
static func closeness(profile: FareGuideProfile, apart_m: float) -> float:
	var span: float = profile.far_m - profile.near_m
	if span <= 0.0:
		return 1.0
	return clampf((profile.far_m - apart_m) / span, 0.0, 1.0)


## A flat arrow `length` long in the XZ plane, nose along `-Z`, about its own
## centre: a head and a shaft, five triangles, no normals to shade.
static func arrow_mesh(length: float) -> ArrayMesh:
	var half: float = length * 0.5
	var head: float = length * 0.45
	var head_half_w: float = length * 0.3
	var shaft_half_w: float = length * 0.1
	var nose := Vector3(0.0, 0.0, -half)
	var neck: float = -half + head
	var points := PackedVector3Array(
		[
			nose,
			Vector3(head_half_w, 0.0, neck),
			Vector3(-head_half_w, 0.0, neck),
			Vector3(-shaft_half_w, 0.0, neck),
			Vector3(shaft_half_w, 0.0, neck),
			Vector3(-shaft_half_w, 0.0, half),
			Vector3(shaft_half_w, 0.0, neck),
			Vector3(shaft_half_w, 0.0, half),
			Vector3(-shaft_half_w, 0.0, half),
		]
	)
	return _mesh_of(points)


## A flat ring in the XZ plane about the origin: `radius` to its outer edge,
## `width` across the band, 48 segments as a triangle list.
static func ring_mesh(radius: float, width: float) -> ArrayMesh:
	var segments: int = 48
	var inner: float = maxf(radius - width, 0.0)
	var points := PackedVector3Array()
	for index: int in segments:
		var a: float = TAU * index / segments
		var b: float = TAU * (index + 1) / segments
		var outer_a := Vector3(cos(a) * radius, 0.0, sin(a) * radius)
		var outer_b := Vector3(cos(b) * radius, 0.0, sin(b) * radius)
		var inner_a := Vector3(cos(a) * inner, 0.0, sin(a) * inner)
		var inner_b := Vector3(cos(b) * inner, 0.0, sin(b) * inner)
		points.append_array([outer_a, outer_b, inner_a, inner_a, outer_b, inner_b])
	return _mesh_of(points)


## A spike pointing down: its tip at the origin, a `sides`-gon base `length`
## above it `width` across corner to corner, capped. Each side carries its
## shade from `POINTER_SHADES` as a vertex colour, so it reads flat-shaded
## under an unshaded material; the cap is full colour.
static func pointer_mesh(length: float, width: float, sides: int) -> ArrayMesh:
	var radius: float = width * 0.5
	var corners := PackedVector3Array()
	for index: int in sides:
		var a: float = TAU * index / sides
		corners.append(Vector3(cos(a) * radius, length, sin(a) * radius))
	var points := PackedVector3Array()
	var colours := PackedColorArray()
	for index: int in sides:
		points.append_array([Vector3.ZERO, corners[index], corners[(index + 1) % sides]])
		var shade: float = POINTER_SHADES[index % POINTER_SHADES.size()]
		var tone := Color(shade, shade, shade)
		colours.append_array([tone, tone, tone])
	for index: int in range(1, sides - 1):
		points.append_array([corners[0], corners[index + 1], corners[index]])
		colours.append_array([Color.WHITE, Color.WHITE, Color.WHITE])
	return _mesh_of(points, colours)


static func _mesh_of(
	points: PackedVector3Array, colours: PackedColorArray = PackedColorArray()
) -> ArrayMesh:
	var arrays: Array = []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = points
	if not colours.is_empty():
		arrays[Mesh.ARRAY_COLOR] = colours
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	return mesh
