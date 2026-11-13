class_name TrafficBeams
extends MultiMeshInstance3D
## The headlamp beams of every moving vehicle at night: one box of air ahead of
## each nose, drawn by `traffic_beam.gdshader`, which lights what stands inside
## its cone. The shader's header says why this is not a light.
##
## Owned by `TrafficSystem` and `TramSystem`, which each hand it their live
## vehicles once a tick between `begin` and `end`. Only a vehicle under way is
## handed over — a parked one (`ParkedLayer`) never is — so the beams are the
## moving fleet's and nothing else's.
##
## The instances are rewritten densely every tick rather than kept in slots: a
## fleet is tens of vehicles, and the ones past `draw_m` are not drawn at all.

## The beams' material: the look, the box's dimensions and the lamps' height.
const MATERIAL_PATH: String = "res://tuning/traffic_beams.tres"

## The lamps over the foot of the nose: each instance stands at the lamps.
var _lamp_height_m: float = 0.0
var _draw_sq_m2: float = 0.0
var _eye: Vector3 = Vector3.ZERO
var _shown: int = 0
## Whether this tick's beams are taken at all: not by day, when the shader
## would collapse every one of them after two writes a vehicle.
var _lit: bool = true


## The foot of a body's nose, in its own frame: where `add` takes a beam from.
static func nose_of(extent: AABB) -> Vector3:
	return Vector3(extent.get_center().x, extent.position.y, extent.position.z)


## A batch with room for `capacity` beams, its box wide enough for a vehicle
## `widest_half_m` either side of its centre line; null, warned, where the
## material does not load.
static func create(capacity: int, widest_half_m: float) -> TrafficBeams:
	var material := load(MATERIAL_PATH) as ShaderMaterial
	if material == null:
		push_warning("TrafficBeams: %s did not load; no vehicle throws a beam" % MATERIAL_PATH)
		return null
	var reach: float = material.get_shader_parameter(&"reach_m")
	var spread: float = deg_to_rad(material.get_shader_parameter(&"spread_deg"))
	var drop: float = material.get_shader_parameter(&"drop_m")
	var rise: float = material.get_shader_parameter(&"rise_m")
	# The box is built around the lamps rather than its own centre, so an
	# instance's origin IS the lamps and the shader reads them off its transform.
	# The 0.5 m above `rise_m` holds the shader's soft top (`top` ± 0.25).
	var box := BoxMesh.new()
	box.size = Vector3(2.0 * (widest_half_m + reach * tan(spread)), drop + rise + 0.5, reach)
	var arrays: Array = box.get_mesh_arrays()
	var positions: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var centre := Vector3(0.0, (rise + 0.5 - drop) * 0.5, -reach * 0.5)
	for index: int in positions.size():
		positions[index] += centre
	arrays[Mesh.ARRAY_VERTEX] = positions
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	mesh.surface_set_material(0, material)
	var multi := MultiMesh.new()
	multi.transform_format = MultiMesh.TRANSFORM_3D
	multi.use_custom_data = true
	multi.mesh = mesh
	multi.instance_count = capacity
	multi.visible_instance_count = 0
	# Fixed, as `skid_marks.gd`'s: the instances move every tick, and a box the
	# engine re-derived from them would be rebuilt over every instance each time.
	multi.custom_aabb = AABB(Vector3(-1.0e5, -1.0e3, -1.0e5), Vector3(2.0e5, 2.0e3, 2.0e5))
	var beams := TrafficBeams.new()
	beams.name = "Beams"
	beams.multimesh = multi
	beams.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	beams._lamp_height_m = material.get_shader_parameter(&"lamp_height_m")
	var draw_m: float = material.get_shader_parameter(&"draw_m")
	beams._draw_sq_m2 = draw_m * draw_m
	return beams


## Start a tick's beams, ranked from the camera when there is one.
func begin() -> void:
	_shown = 0
	_lit = LightingRig.night_lights_now > 0.0
	var camera: Camera3D = get_viewport().get_camera_3d() if is_inside_tree() else null
	_eye = camera.global_position if camera != null else Vector3.INF


## One vehicle's beam: `nose` the foot of its nose facing its travel (-z),
## `half_width_m` half its body's width. Skipped past `draw_m` from the camera.
func add(nose: Transform3D, half_width_m: float) -> void:
	if not _lit or _shown >= multimesh.instance_count:
		return
	if _eye != Vector3.INF and nose.origin.distance_squared_to(_eye) > _draw_sq_m2:
		return
	multimesh.set_instance_transform(_shown, nose.translated_local(Vector3.UP * _lamp_height_m))
	multimesh.set_instance_custom_data(_shown, Color(half_width_m, 0.0, 0.0, 0.0))
	_shown += 1


## Draw the tick's beams and no others.
func end() -> void:
	multimesh.visible_instance_count = _shown


## How many beams the last tick drew.
func shown() -> int:
	return _shown
