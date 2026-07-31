class_name GreyboxBuilder
extends Node3D
## Builds the P0-5b grey-box circuit from JSON at run time.
##
## Generated rather than hand-placed so road widths stay data (CLAUDE.md hard
## rule 4) and so the widen_factor can be changed and re-driven in seconds —
## which is the entire point of the fun test. It is also a cheap rehearsal for
## P1-4, which does the same job from real road-graph polylines.
##
## Deliberately crude: boxes, flat colours, no LOD, no merging. Draw-call budget
## is P2-6's problem, not this scene's.

const SUPPORTED_SCHEMA: int = 1
const SIDES: Array[float] = [-1.0, 1.0]

@export_file("*.json") var layout_path: String = "res://assets/authored/greybox_wanchai.json"

var _materials: Dictionary = {}
## Carriageway footprints in XZ, collected while building roads so that flanking
## massing can be kept out of them.
var _road_rects: Array[Rect2] = []
var _slab_thickness: float = 0.4
var _road_lift: float = 0.01


func _ready() -> void:
	var layout: Dictionary = _load_layout()
	if layout.is_empty():
		return
	var surface: Dictionary = layout["surface"]
	_slab_thickness = float(surface["slab_thickness_m"])
	_road_lift = float(surface["road_lift_m"])

	_build_ground(layout["ground"])
	var classes: Dictionary = layout["road_classes"]
	for segment: Dictionary in layout["segments"]:
		var road_class: Variant = classes.get(segment["class"])
		if road_class == null:
			push_error(
				(
					'Segment "%s" names undefined road class "%s".'
					% [segment["name"], segment["class"]]
				)
			)
			continue
		_build_segment(segment, road_class, layout["kerb"])
	_build_buildings(layout)


func _load_layout() -> Dictionary:
	var text: String = FileAccess.get_file_as_string(layout_path)
	if text.is_empty():
		push_error("Grey-box layout missing or unreadable: %s" % layout_path)
		return {}
	var parsed: Variant = JSON.parse_string(text)
	if typeof(parsed) != TYPE_DICTIONARY:
		push_error("Grey-box layout is not a JSON object: %s" % layout_path)
		return {}
	var layout: Dictionary = parsed as Dictionary
	# Declaring a schema_version and never checking it is worse than omitting it.
	var version: int = int(layout.get("schema_version", -1))
	if version != SUPPORTED_SCHEMA:
		push_error("Grey-box layout schema_version %d, expected %d." % [version, SUPPORTED_SCHEMA])
		return {}
	return layout


## Widening is applied here and nowhere else, so the real carriageway width in
## the JSON stays readable as the real number.
func _drivable_width(road_class: Dictionary) -> float:
	return float(road_class["real_width_m"]) * float(road_class["widen_factor"])


func _build_ground(ground: Dictionary) -> void:
	var size: float = float(ground["size_m"])
	_add_box(
		Transform3D(Basis.IDENTITY, Vector3(0.0, -_slab_thickness * 0.5, 0.0)),
		Vector3(size, _slab_thickness, size),
		_material("ground", ground["colour"]),
		"Ground"
	)


func _build_segment(segment: Dictionary, road_class: Dictionary, kerb: Dictionary) -> void:
	var width: float = _drivable_width(road_class)
	var material: StandardMaterial3D = _material(segment["class"], road_class["colour"])
	var kerb_material: StandardMaterial3D = _material("kerb", kerb["colour"])
	var kerb_w: float = float(kerb["width_m"])
	var kerb_h: float = float(kerb["height_m"])
	var points: Array = segment["points"]

	for i: int in range(points.size() - 1):
		var a: Vector3 = _to_vec3(points[i])
		var b: Vector3 = _to_vec3(points[i + 1])
		if a.is_equal_approx(b):
			continue
		var frame: Basis = _segment_basis(a, b)
		# Lifted clear of the ground plane; exactly coplanar slabs z-fight across
		# their whole surface rather than at a seam.
		var mid: Vector3 = (a + b) * 0.5 + Vector3.UP * _road_lift
		var length: float = a.distance_to(b)
		_road_rects.append(_footprint(mid, frame, width, length))

		_add_box(
			Transform3D(frame, mid - frame.y * _slab_thickness * 0.5),
			Vector3(width, _slab_thickness, length),
			material,
			"%s_%d" % [segment["name"], i]
		)
		# Kerbs are low enough to mount deliberately — GAME_DESIGN.md flattens
		# them for exactly that reason.
		for side: float in SIDES:
			_add_box(
				Transform3D(
					frame, mid + frame.x * side * (width + kerb_w) * 0.5 + frame.y * kerb_h * 0.5
				),
				Vector3(kerb_w, kerb_h, length),
				kerb_material,
				"%s_kerb%d_%d" % [segment["name"], int(side), i]
			)


## Orients a box so its local Z runs along the segment, handling the pitched
## flyover ramps. Wraps Basis.looking_at only to add the vertical-segment guard,
## which real P1-4 polylines could hit even though this layout does not.
func _segment_basis(a: Vector3, b: Vector3) -> Basis:
	var forward: Vector3 = (b - a).normalized()
	if absf(forward.dot(Vector3.UP)) > 0.999:
		return Basis(Vector3.RIGHT, forward.cross(Vector3.RIGHT).normalized(), forward)
	return Basis.looking_at(forward, Vector3.UP, true)


## Axis-aligned XZ footprint of an oriented box. Conservative by design: near a
## junction it errs toward classing ground as carriageway, which removes a
## building rather than leaving one in the road.
func _footprint(centre: Vector3, frame: Basis, width: float, length: float) -> Rect2:
	var half_x: Vector3 = frame.x * width * 0.5
	var half_z: Vector3 = frame.z * length * 0.5
	var extent_x: float = absf(half_x.x) + absf(half_z.x)
	var extent_z: float = absf(half_x.z) + absf(half_z.z)
	return Rect2(centre.x - extent_x, centre.z - extent_z, extent_x * 2.0, extent_z * 2.0)


func _build_buildings(layout: Dictionary) -> void:
	var cfg: Dictionary = layout["buildings"]
	var material: StandardMaterial3D = _material("building", cfg["colour"])
	var rng := RandomNumberGenerator.new()
	# Seeded so the skyline is identical every run — a fun test that reshuffles
	# its own landmarks between attempts is not measuring the same thing twice.
	rng.seed = int(cfg["seed"])

	var spacing: float = float(cfg["spacing_m"])
	var footprint: float = float(cfg["footprint_m"])
	var classes: Dictionary = layout["road_classes"]

	for segment: Dictionary in layout["segments"]:
		var road_class: Variant = classes.get(segment["class"])
		if road_class == null:
			continue
		var offset: float = (
			_drivable_width(road_class) * 0.5 + float(cfg["setback_m"]) + footprint * 0.5
		)
		var points: Array = segment["points"]
		for i: int in range(points.size() - 1):
			var a: Vector3 = _to_vec3(points[i])
			var b: Vector3 = _to_vec3(points[i + 1])
			# Buildings sit on the ground regardless of road height, so the
			# flyover passes between them rather than carrying them upward.
			a.y = 0.0
			b.y = 0.0
			var length: float = a.distance_to(b)
			if length < spacing:
				continue
			var frame: Basis = _segment_basis(a, b)
			for n: int in range(int(length / spacing)):
				var along: float = (float(n) + 0.5) * spacing
				for side: float in SIDES:
					var height: float = rng.randf_range(
						float(cfg["height_min_m"]), float(cfg["height_max_m"])
					)
					var centre: Vector3 = (
						a + frame.z * along + frame.x * side * offset + Vector3.UP * height * 0.5
					)
					# Every junction is a T, so one road's flanking massing lands
					# in the crossing road's carriageway — at the four corners
					# the circuit has to turn through.
					if _blocks_a_road(centre, frame, footprint):
						continue
					_add_box(
						Transform3D(frame, centre),
						Vector3(footprint, height, footprint),
						material,
						"bldg_%s_%d_%d_%d" % [segment["name"], i, n, int(side)]
					)


func _blocks_a_road(centre: Vector3, frame: Basis, footprint: float) -> bool:
	var rect: Rect2 = _footprint(centre, frame, footprint, footprint)
	for road: Rect2 in _road_rects:
		if road.intersects(rect):
			return true
	return false


func _add_box(
	placement: Transform3D, size: Vector3, material: StandardMaterial3D, node_name: String
) -> void:
	var body := StaticBody3D.new()
	body.name = node_name
	body.transform = placement

	var mesh_instance := MeshInstance3D.new()
	var mesh := BoxMesh.new()
	mesh.size = size
	mesh_instance.mesh = mesh
	mesh_instance.material_override = material
	body.add_child(mesh_instance)

	var collision := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = size
	collision.shape = shape
	body.add_child(collision)

	add_child(body)


## Materials are shared per class rather than per box — thousands of identical
## StandardMaterial3D instances would be pure waste even in a grey-box.
func _material(key: String, colour: Array) -> StandardMaterial3D:
	if _materials.has(key):
		return _materials[key]
	var material := StandardMaterial3D.new()
	material.albedo_color = Color(colour[0], colour[1], colour[2])
	material.roughness = 0.9
	_materials[key] = material
	return material


func _to_vec3(point: Array) -> Vector3:
	return Vector3(point[0], point[1], point[2])
