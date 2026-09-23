extends Node3D
## The world-space guide to the fare (`P3-5a`, `Q142`): an arrow over the
## taxi pointing at the target, and a ring pulsing on the road where the
## target is. Both answer distance — small and red far off, large and green
## close — from `tuning/guide.tres`.
##
## In the world, not the HUD — both references with a destination do this, and
## `hud_layout.tres` reserves no slot for it (`Q80`). It points where
## `FareFace` says: the nearest pickup while idle, the destination once hailed.
## **As the crow flies.** `Q138` holds the next-junction arrow for after the
## first fare review; in a one-way grid this one will sometimes point down a
## street that cannot be entered, and `GAME_DESIGN.md`'s acceptance test is a
## drive with it off — `--fares=off` takes it with the loop.
##
## Turned and sized every frame off the car's transform alone; the target is
## read from the loop at its own 5 Hz, inside its `sampled` signal (`hud.gd`
## says why nothing here may poll the system).

## The loop whose target this shows. Assign in the scene, AFTER the system in
## tree order so its `usable()` is decided before this reads it.
@export var fares: FareSystem
## The car it floats over.
@export var vehicle: Node3D

var _profile: FareGuideProfile = null
var _face: FareFace = null
var _arrow: MeshInstance3D = null
var _ring: MeshInstance3D = null
var _material: StandardMaterial3D = null
var _ring_material: StandardMaterial3D = null
## The closeness last painted, quantised, so a frame that moved a centimetre
## writes no material.
var _painted: int = -1
var _pulse_s: float = 0.0


func _ready() -> void:
	if (
		Cmdline.value(FareSystem.FARES_ARG).to_lower() == "off"
		or fares == null
		or vehicle == null
		or not fares.usable()
	):
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
	_face = FareFace.new(0, Locale.language())
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
	visible = false
	fares.sampled.connect(_on_sampled)
	_on_sampled()


static func _unshaded(alpha: float) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.cull_mode = BaseMaterial3D.CULL_DISABLED
	if alpha < 1.0:
		material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.albedo_color = Color(1.0, 1.0, 1.0, alpha)
	return material


func _on_sampled() -> void:
	var at: Vector3 = vehicle.global_position
	var nearest: Fare.Stop = null
	if fares.state == FareSystem.State.IDLE:
		nearest = fares.nearest_pickup_any(at)
	var apart: float = 0.0 if nearest == null else RoadGraph.plan_distance(at, nearest.point)
	_face.on_sampled(fares.state, fares.fare, nearest, apart, 0.0, 0.0)
	if visible != _face.has_target:
		visible = _face.has_target
	if _face.has_target:
		_ring.global_position = _face.target + Vector3.UP * _profile.ring_lift_m


func _process(delta: float) -> void:
	if not visible or not is_instance_valid(vehicle):
		return
	var at: Vector3 = vehicle.global_position + Vector3.UP * _profile.height_m
	var flat := Vector3(_face.target.x - at.x, 0.0, _face.target.z - at.z)
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
		ink.a = _profile.ring_alpha
		_ring_material.albedo_color = ink
	_pulse_s = fmod(_pulse_s + delta, 1.0 / maxf(_profile.pulse_hz, 0.001))
	var pulse: float = 1.0 + _profile.pulse_depth * sin(TAU * _pulse_s * _profile.pulse_hz)
	_ring.scale = Vector3(pulse, 1.0, pulse)
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


static func _mesh_of(points: PackedVector3Array) -> ArrayMesh:
	var arrays: Array = []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = points
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	return mesh
