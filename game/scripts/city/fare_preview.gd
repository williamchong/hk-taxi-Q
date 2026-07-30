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
const PreviewDraw = preload("res://scripts/city/preview_draw.gd")

## The four cases the colours separate. An enum rather than two parallel
## if-chains, so a colour can never end up without a matching label in the
## report — which is the one way a diagnostic can quietly lie.
enum Case { CROSS_HARBOUR_STAND, STAND, PICKUP_DROPOFF, DROPOFF }

## Height of each pin above the node it marks.
##
## Tall by street standards on purpose: the region is 1.65 km across and these
## have to read from the fly camera without being hunted for.
@export var pin_height_m: float = 14.0

## Width of the pin's base, where it is widest.
@export var pin_width_m: float = 3.0

## Width of the tether laid from the node to its snapped point on the road.
@export var tether_width_m: float = 0.6

## How far the tether is lifted off the deck, so it does not z-fight the road
## surface it crosses. The same job `road_preview.gd`'s `lift_m` does.
@export var tether_lift_m: float = 0.2

## Emitted once built, with the bounds of the nodes, so a camera can frame them.
signal built(low: Vector3, high: Vector3)

# Colour is the whole diagnostic, so the four cases are deliberately far apart
# rather than a ramp: a premium stand and a drop-off-only point must not be
# distinguishable only by shade on a phone screen in daylight. Drop-off is the
# dullest because no fare is ever hailed there.
const _COLOURS: Dictionary[Case, Color] = {
	Case.CROSS_HARBOUR_STAND: Color(0.95, 0.30, 0.28),
	Case.STAND: Color(0.98, 0.78, 0.20),
	Case.PICKUP_DROPOFF: Color(0.35, 0.75, 0.95),
	Case.DROPOFF: Color(0.45, 0.45, 0.52),
}

const _LABELS: Dictionary[Case, String] = {
	Case.CROSS_HARBOUR_STAND: "cross-harbour stands",
	Case.STAND: "stands",
	Case.PICKUP_DROPOFF: "pick-up/drop-off",
	Case.DROPOFF: "drop-off only",
}

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
	#
	# This re-parses `roadgraph.json`, which `road_preview.gd` in the same scene
	# has already parsed — 5 ms and 6 MB, measured. Deliberately not cached: a
	# static memo would hold those 6 MB resident for the life of the process to
	# save 5 ms once, and would serve stale data across an ETL re-run inside the
	# editor. `P1-6` did not remove it either — `city.json` names the graph
	# rather than containing it, so a shared parse is `RoadGraph`'s to own
	# (`P2-2`), and these two previews will read it from there.
	var edges: Dictionary = _edges_by_id(GeneratedRoadGraph.load_graph())
	var tethering: bool = not edges.is_empty()

	var surface := SurfaceTool.new()
	surface.begin(Mesh.PRIMITIVE_TRIANGLES)

	var bounds := AABB(_position(nodes[0]), Vector3.ZERO)
	var counts: Dictionary[Case, int] = {}
	var tethered: int = 0
	var unresolved: PackedStringArray = []

	for node: Dictionary in nodes:
		var at: Vector3 = _position(node)
		var which: Case = _case_for(node)
		_pin(surface, at, _COLOURS[which])
		counts[which] = counts.get(which, 0) + 1
		bounds = bounds.merge(AABB(at, Vector3.ZERO))

		if not tethering:
			continue
		if not node.has("nearest_edge") or not edges.has(int(node["nearest_edge"])):
			# Reported rather than skipped silently. `nearest_edge` resolving is
			# the acceptance criterion for `P1-5`, and the way it would fail in
			# the game is an id that names no edge.
			unresolved.append("%s -> %s" % [node.get("id", "?"), node.get("nearest_edge", "none")])
			continue
		var along: Vector3 = _along(edges[int(node["nearest_edge"])], float(node.get("edge_t", 0.0)))
		if _tether(surface, at, along):
			tethered += 1

	var instance := MeshInstance3D.new()
	instance.name = "FareNodes"
	instance.mesh = surface.commit()
	instance.material_override = PreviewDraw.unshaded_material()
	add_child(instance)

	_report(nodes.size(), counts, tethered, unresolved)
	built.emit(bounds.position, bounds.end)


func _report(
	total: int, counts: Dictionary[Case, int], tethered: int, unresolved: PackedStringArray
) -> void:
	# Ordered by case rather than by count, so the line reads the same way every
	# run. Sorting the formatted strings would order them by their leading
	# digit, putting 11 before 4.
	var parts: PackedStringArray = []
	for which: Case in _LABELS:
		if counts.has(which):
			parts.append("%d %s" % [counts[which], _LABELS[which]])
	print("fare preview: %d nodes — %s" % [total, ", ".join(parts)])
	print("  %d tethered to their nearest edge" % tethered)
	if not unresolved.is_empty():
		push_error(
			(
				"%d fare nodes name an edge the graph does not have: %s"
				% [unresolved.size(), ", ".join(unresolved)]
			)
		)


## Edge polylines keyed by the edge's own `id`, never by its position in the
## array. The two agree today only because `P1-3` happens to number edges in
## order, and `nearest_edge` is defined as an id.
func _edges_by_id(graph: Dictionary) -> Dictionary[int, Array]:
	var by_id: Dictionary[int, Array] = {}
	for edge: Dictionary in graph.get("edges", []):
		if not edge.has("id"):
			continue
		var id: int = int(edge["id"])
		if by_id.has(id):
			push_warning("Road graph has two edges with id %d; the later one wins" % id)
		by_id[id] = edge.get("polyline", [])
	return by_id


func _position(node: Dictionary) -> Vector3:
	return _point(node.get("pos", [0.0, 0.0, 0.0]))


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
	# Only reachable when float accumulation leaves `walked` a hair short of
	# `total` at t=1.
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
## kerb it sits. Four side faces and no base — the material is double-sided, so
## looking down into the open top shows the inner faces rather than a hole.
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
		surface.add_vertex(at)
		surface.add_vertex(corners[index])
		surface.add_vertex(corners[(index + 1) % corners.size()])


## A flat ribbon from the node to its snapped point on the road.
func _tether(surface: SurfaceTool, from: Vector3, to: Vector3) -> bool:
	var lift := Vector3.UP * tether_lift_m
	return PreviewDraw.ribbon(
		surface, from + lift, to + lift, tether_width_m * 0.5, _TETHER
	)


func _case_for(node: Dictionary) -> Case:
	if node.get("kind", "") == GeneratedFares.TAXI_STAND:
		if node.get("stand_category") == GeneratedFares.CROSS_HARBOUR:
			return Case.CROSS_HARBOUR_STAND
		return Case.STAND
	return Case.PICKUP_DROPOFF if bool(node.get("pickup", true)) else Case.DROPOFF
