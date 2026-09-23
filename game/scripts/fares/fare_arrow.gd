extends Node3D
## A flat arrow over the taxi, pointing at the fare (`P3-5a`).
##
## In the world, not the HUD — both references with a destination do this, and
## `hud_layout.tres` reserves no slot for it (`Q80`). It points where
## `FareFace` says: the nearest pickup while idle, the destination once hailed.
## **As the crow flies.** `Q138` holds the next-junction arrow for after the
## first fare review; in a one-way grid this one will sometimes point down a
## street that cannot be entered, and `GAME_DESIGN.md`'s acceptance test is a
## drive with it off — `--fares=off` takes it with the loop.
##
## Turned every frame off the car's transform alone; the target is read from
## the loop at its own 5 Hz, inside its `sampled` signal (`hud.gd` says why
## nothing here may poll the system).

## The loop whose target this shows. Assign in the scene, AFTER the system in
## tree order so its `usable()` is decided before this reads it.
@export var fares: FareSystem
## The car it floats over.
@export var vehicle: Node3D
## How far above the car's origin, and how long the arrow is, in metres.
@export var height_m: float = 2.6
@export var length_m: float = 1.4

var _face: FareFace = null
var _mesh: MeshInstance3D = null
var _material: StandardMaterial3D = null
var _style: HudStyle = null


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
	_style = load(HudStyle.PATH) as HudStyle
	if _style == null:
		push_warning("fare_arrow: %s did not load; no arrow this run" % HudStyle.PATH)
		set_process(false)
		visible = false
		return
	_face = FareFace.new(0)
	_material = StandardMaterial3D.new()
	_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	_material.cull_mode = BaseMaterial3D.CULL_DISABLED
	_mesh = MeshInstance3D.new()
	_mesh.name = "Arrow"
	_mesh.mesh = arrow_mesh(length_m)
	_mesh.material_override = _material
	_mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(_mesh)
	visible = false
	fares.sampled.connect(_on_sampled)
	_on_sampled()


func _on_sampled() -> void:
	var at: Vector3 = vehicle.global_position
	var nearest: Fare.Stop = null
	if fares.state == FareSystem.State.IDLE:
		nearest = fares.nearest_pickup_any(at)
	var apart: float = 0.0 if nearest == null else RoadGraph.plan_distance(at, nearest.point)
	_face.on_sampled(fares.state, fares.fare, nearest, apart, 0.0)
	if visible != _face.has_target:
		visible = _face.has_target
	var ink: Color = _style.map_destination if _face.target_is_destination else _style.map_pickup
	if _material.albedo_color != ink:
		_material.albedo_color = ink


func _process(_delta: float) -> void:
	if not visible or not is_instance_valid(vehicle):
		return
	var at: Vector3 = vehicle.global_position + Vector3.UP * height_m
	var flat := Vector3(_face.target.x - at.x, 0.0, _face.target.z - at.z)
	global_position = at
	if flat.length_squared() < 0.01:
		return
	# `-Z` is the arrow's nose (`arrow_mesh`), which is what `look_at` points.
	look_at(at + flat, Vector3.UP)


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
	var arrays: Array = []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = points
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	return mesh
