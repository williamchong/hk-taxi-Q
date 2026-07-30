## Draws the ETL's fare nodes, for judging where they landed before `P3-1`.
##
## A dev tool, not `FareSystem`. It exists to ask the one question `P1-5` could
## not settle by measurement: the tests prove every node resolves to an edge and
## that 28 of 28 land on a street the source's own prose names, but nothing
## checks whether a stand is on the side of the road a Hong Kong driver would
## expect, or whether the six cross-harbour stands sit where you would look for
## one. That is a question for someone who knows the streets — the same shape as
## `Q12`, and asked the same way.
##
## The **tether** is the part worth watching. Each node is drawn at its source
## position, which is the kerbside, and joined by a line to the point on
## `nearest_edge` at `edge_t`. That single line renders both halves of the
## contract at once: if either is wrong the tether points at the wrong street,
## or at the wrong end of the right one.
##
## No transform is applied, for the same reason as `tile_preview.gd`: the ETL
## writes region game-space coordinates, so a node at the origin already lines
## up with the tiles, the surface and the graph.
extends Node3D

const GeneratedFares = preload("res://scripts/city/generated_fares.gd")
const GeneratedRoadGraph = preload("res://scripts/city/generated_road_graph.gd")

## Height of each pin above the node it marks. Tall by street standards on
## purpose — the region is 1.65 km across and these have to read from the fly
## camera without being hunted for.
@export var pin_height_m: float = 14.0
@export var pin_width_m: float = 3.0

## Width of the tether laid from the node to its snapped point on the road.
@export var tether_width_m: float = 0.6

## Emitted once built, with the bounds of the nodes, so a camera can frame them.
signal built(low: Vector3, high: Vector3)

# Colour is the whole diagnostic, so the four cases are deliberately far apart
# rather than a ramp: a premium stand and a drop-off-only point must not be
# distinguishable only by shade on a phone screen in daylight.
const _CROSS_HARBOUR := Color(0.95, 0.30, 0.28)
const _STAND := Color(0.98, 0.78, 0.20)
const _PICKUP_DROPOFF := Color(0.35, 0.75, 0.95)
## Drop-off only. Deliberately the dullest: no fare is ever hailed here.
const _DROPOFF := Color(0.45, 0.45, 0.52)
const _TETHER := Color(0.15, 0.90, 0.55)


func _ready() -> void:
	var fares: Dictionary = GeneratedFares.load_fares()
	if fares.is_empty():
		return

	var nodes: Array = fares.get("nodes", [])
	if nodes.is_empty():
		push_warning("Fare nodes at %s are empty" % GeneratedFares.PATH)
		return

	# The graph is optional here: without it the pins still draw and only the
	# tethers are missing. A preview that refused to show anything because the
	# second file was stale would hide the thing it exists to show.
	var edges: Dictionary = _edges_by_id(GeneratedRoadGraph.load_graph())

	var surface := SurfaceTool.new()
	surface.begin(Mesh.PRIMITIVE_TRIANGLES)

	var bounds := AABB()
	var measured: bool = false
	var counts := {}
	var tethered: int = 0
	var unresolved: PackedStringArray = []

	for node: Dictionary in nodes:
		var at: Vector3 = _position(node)
		_pin(surface, at, _colour_for(node))
		counts[_label_for(node)] = int(counts.get(_label_for(node), 0)) + 1

		var box := AABB(at, Vector3.ZERO)
		bounds = box if not measured else bounds.merge(box)
		measured = true

		if edges.is_empty():
			continue
		var edge_id: int = int(node.get("nearest_edge", -1))
		if not edges.has(edge_id):
			# Reported rather than skipped silently. `nearest_edge` resolving is
			# the acceptance criterion for `P1-5`, and the way it would fail in
			# the game is an id that names no edge.
			unresolved.append("%s -> edge %d" % [node.get("id", "?"), edge_id])
			continue
		_tether(surface, at, _along(edges[edge_id], float(node.get("edge_t", 0.0))))
		tethered += 1

	var instance := MeshInstance3D.new()
	instance.name = "FareNodes"
	instance.mesh = surface.commit()
	instance.material_override = _material()
	add_child(instance)

	_report(nodes.size(), counts, tethered, unresolved)
	if measured:
		built.emit(bounds.position, bounds.end)


func _report(
	total: int, counts: Dictionary, tethered: int, unresolved: PackedStringArray
) -> void:
	var parts: PackedStringArray = []
	for label: String in counts:
		parts.append("%d %s" % [counts[label], label])
	parts.sort()
	print("fare preview: %d nodes — %s" % [total, ", ".join(parts)])
	print("  %d tethered to their nearest edge" % tethered)
	if not unresolved.is_empty():
		push_error(
			(
				"%d fare nodes name an edge the graph does not have: %s"
				% [unresolved.size(), ", ".join(unresolved)]
			)
		)


func _edges_by_id(graph: Dictionary) -> Dictionary:
	## Keyed by the edge's own `id`, never by its position in the array. The two
	## agree today only because `P1-3` happens to number edges in order, and
	## `nearest_edge` is defined as an id.
	var by_id := {}
	for edge: Dictionary in graph.get("edges", []):
		by_id[int(edge.get("id", -1))] = edge.get("polyline", [])
	return by_id


func _position(node: Dictionary) -> Vector3:
	var pos: Array = node.get("pos", [0.0, 0.0, 0.0])
	return Vector3(pos[0], pos[1], pos[2])


## The point `t` of the way along a polyline, measured in **plan**.
##
## Plan rather than 3D because that is what `edge_t` means — `fares.py` divides
## by `plan_lengths`, so measuring the walk in 3D here would land short on any
## edge that climbs.
func _along(polyline: Array, t: float) -> Vector3:
	if polyline.size() < 2:
		return _point(polyline[0]) if polyline.size() == 1 else Vector3.ZERO

	var total: float = 0.0
	for index: int in polyline.size() - 1:
		total += _plan_distance(_point(polyline[index]), _point(polyline[index + 1]))
	if total <= 0.0:
		return _point(polyline[0])

	var target: float = clampf(t, 0.0, 1.0) * total
	var walked: float = 0.0
	for index: int in polyline.size() - 1:
		var from: Vector3 = _point(polyline[index])
		var to: Vector3 = _point(polyline[index + 1])
		var span: float = _plan_distance(from, to)
		if span <= 0.0:
			continue
		if walked + span >= target:
			return from.lerp(to, (target - walked) / span)
		walked += span
	return _point(polyline[polyline.size() - 1])


func _point(entry: Variant) -> Vector3:
	var values: Array = entry
	return Vector3(values[0], values[1], values[2])


func _plan_distance(from: Vector3, to: Vector3) -> float:
	return Vector2(to.x - from.x, to.z - from.z).length()


## A spike with its apex on the node and its base in the air.
##
## Apex down so the pin points at the position it marks: a marker centred on the
## node would hide the very thing being judged, which is exactly where on the
## kerb it sits.
func _pin(surface: SurfaceTool, at: Vector3, colour: Color) -> void:
	var half: float = pin_width_m * 0.5
	var top: Vector3 = at + Vector3.UP * pin_height_m
	var corners: Array[Vector3] = [
		top + Vector3(-half, 0.0, -half),
		top + Vector3(half, 0.0, -half),
		top + Vector3(half, 0.0, half),
		top + Vector3(-half, 0.0, half),
	]

	surface.set_color(colour)
	for index: int in corners.size():
		# Both windings, because the material is double-sided and a pin seen
		# from underneath — which is where the driver is — must still be solid.
		surface.add_vertex(at)
		surface.add_vertex(corners[index])
		surface.add_vertex(corners[(index + 1) % corners.size()])


## A flat ribbon from the node to its snapped point on the road.
func _tether(surface: SurfaceTool, from: Vector3, to: Vector3) -> void:
	var along := to - from
	along.y = 0.0
	if along.length_squared() < 1e-8:
		# The node is already on the centreline. Nothing to draw, and a zero
		# length quad would be a degenerate triangle in the mesh.
		return
	var side: Vector3 = along.normalized().cross(Vector3.UP) * tether_width_m * 0.5
	# Lifted clear of the carriageway it crosses, or it z-fights `roads.glb`.
	var lift := Vector3.UP * 0.2

	surface.set_color(_TETHER)
	for corner: Vector3 in [
		from - side + lift,
		from + side + lift,
		to + side + lift,
		from - side + lift,
		to + side + lift,
		to - side + lift,
	]:
		surface.add_vertex(corner)


func _colour_for(node: Dictionary) -> Color:
	if node.get("kind", "") == GeneratedFares.TAXI_STAND:
		var category: Variant = node.get("stand_category")
		return _CROSS_HARBOUR if category == GeneratedFares.CROSS_HARBOUR else _STAND
	return _PICKUP_DROPOFF if bool(node.get("pickup", true)) else _DROPOFF


func _label_for(node: Dictionary) -> String:
	if node.get("kind", "") == GeneratedFares.TAXI_STAND:
		var category: Variant = node.get("stand_category")
		return "cross-harbour stands" if category == GeneratedFares.CROSS_HARBOUR else "stands"
	return "pick-up/drop-off" if bool(node.get("pickup", true)) else "drop-off only"


func _material() -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.vertex_color_use_as_albedo = true
	# Unshaded so the colours read as the categories they encode rather than as
	# whatever the sun is doing to them — the same reason `road_preview.gd` does.
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.cull_mode = BaseMaterial3D.CULL_DISABLED
	return material
