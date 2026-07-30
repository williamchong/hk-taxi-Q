## Draws the ETL's road graph as flat ribbons, for looking at before `P1-4`.
##
## A dev tool, not the road surface. `P1-4` generates the real ribbon with kerbs,
## collision and playability widening; this draws `width_m` flat on the ground so
## the graph can be judged by eye against the buildings around it.
##
## It exists mainly to answer `Q12`. The one acceptance criterion `P1-3` could not
## settle by measurement is whether the one-way directions match the real streets,
## and that is a question for someone who knows them. Arrows along every one-way
## edge, over massing you recognise, is the cheapest way to ask it.
##
## No transforms are applied, for the same reason as `tile_preview.gd`: the ETL
## writes region game-space coordinates, so a node at the origin already lines up
## with the tiles.
extends Node3D

const GeneratedRoadGraph = preload("res://scripts/city/generated_road_graph.gd")
const PreviewDraw = preload("res://scripts/city/preview_draw.gd")

## How to colour each edge.
enum Colouring {
	## Two-way against one-way — what `Q12` is asking about.
	DIRECTION,
	## Ground, flyover and tunnel, so grade separation reads at a glance.
	ELEVATION,
	## Where the source signs a limit above the urban default.
	SPEED,
}

@export var colouring: Colouring = Colouring.DIRECTION

## Lifted off the deck so the ribbon does not z-fight the terrain if that is
## also loaded. Small enough not to disturb the heights being inspected.
@export var lift_m: float = 0.15

## Arrows along one-way edges, one per this many metres of edge.
@export var arrow_spacing_m: float = 45.0
@export var draw_arrows: bool = true

## Emitted once built, with the bounds of the graph, so a camera can frame it.
signal built(low: Vector3, high: Vector3)

const _TWO_WAY := Color(0.45, 0.62, 0.85)
const _ONE_WAY := Color(0.92, 0.72, 0.32)
const _GROUND := Color(0.55, 0.55, 0.58)
const _ELEVATED := Color(0.90, 0.45, 0.40)
const _TUNNEL := Color(0.35, 0.30, 0.55)
const _FAST := Color(0.95, 0.35, 0.30)
const _ARROW := Color(0.10, 0.10, 0.12)


func _ready() -> void:
	var graph: Dictionary = GeneratedRoadGraph.load_graph()
	if graph.is_empty():
		return

	var edges: Array = graph.get("edges", [])
	if edges.is_empty():
		push_warning("Road graph at %s has no edges" % GeneratedRoadGraph.PATH)
		return

	var surface := SurfaceTool.new()
	surface.begin(Mesh.PRIMITIVE_TRIANGLES)

	var bounds := AABB()
	var measured: bool = false
	var arrows: int = 0
	var one_way: int = 0

	for edge: Dictionary in edges:
		var points: PackedVector3Array = _polyline(edge)
		if points.size() < 2:
			continue
		var half_width: float = maxf(float(edge.get("width_m", 6.0)), 0.5) * 0.5
		var colour: Color = _colour_for(edge)

		for index: int in points.size() - 1:
			PreviewDraw.ribbon(surface, points[index], points[index + 1], half_width, colour)

		for point: Vector3 in points:
			# Seeded from the flag rather than the first point: an AABB starting
			# at the origin would drag the camera's framing back there.
			var box := AABB(point, Vector3.ZERO)
			bounds = box if not measured else bounds.merge(box)
			measured = true

		if edge.get("direction", "both") == "forward":
			one_way += 1
			if draw_arrows:
				arrows += _arrows_along(surface, points, half_width)

	var instance := MeshInstance3D.new()
	instance.name = "RoadRibbon"
	instance.mesh = surface.commit()
	instance.material_override = PreviewDraw.unshaded_material()
	add_child(instance)

	print(
		(
			"road preview: %d edges (%d one-way), %d nodes, %d arrows, %d turn restrictions"
			% [
				edges.size(),
				one_way,
				(graph.get("nodes", []) as Array).size(),
				arrows,
				(graph.get("turn_restrictions", []) as Array).size(),
			]
		)
	)
	# Printed because it is the number that catches a coordinate mistake: the
	# graph must span the same region the tiles do, and a wrong sign or a missed
	# origin puts it somewhere plausible-looking and elsewhere.
	print(
		(
			"  spans %.0f x %.0f m, y %.1f to %.1f"
			% [bounds.size.x, bounds.size.z, bounds.position.y, bounds.end.y]
		)
	)
	if measured:
		# Deferred for the reason `tile_preview.gd` spells out: `_ready` runs
		# children-first, so a direct emit here beats a camera's connect.
		built.emit.call_deferred(bounds.position, bounds.end)


func _polyline(edge: Dictionary) -> PackedVector3Array:
	var points: PackedVector3Array = []
	for point: Array in edge.get("polyline", []):
		points.append(Vector3(point[0], float(point[1]) + lift_m, point[2]))
	return points


## Chevrons pointing along the edge, at `arrow_spacing_m` intervals.
func _arrows_along(
	surface: SurfaceTool, points: PackedVector3Array, half_width: float
) -> int:
	var length: float = 0.0
	for index: int in points.size() - 1:
		length += points[index].distance_to(points[index + 1])
	if length <= 0.0:
		return 0

	# At least one arrow on every one-way edge, however short: an edge with no
	# arrow reads as two-way, which is the thing this is being asked to show.
	var count: int = maxi(1, int(length / maxf(arrow_spacing_m, 1.0)))
	var drawn: int = 0
	for step: int in count:
		if _arrow_at(surface, points, length * (float(step) + 0.5) / float(count), half_width):
			drawn += 1
	return drawn


func _arrow_at(
	surface: SurfaceTool, points: PackedVector3Array, distance: float, half_width: float
) -> bool:
	var travelled: float = 0.0
	for index: int in points.size() - 1:
		var span: float = points[index].distance_to(points[index + 1])
		if span <= 0.0:
			continue
		if travelled + span < distance:
			travelled += span
			continue

		var forward: Vector3 = (points[index + 1] - points[index]).normalized()
		var at: Vector3 = points[index].lerp(points[index + 1], (distance - travelled) / span)
		# Above the ribbon so it reads against the road rather than blending in.
		at.y += 0.05

		var side: Vector3 = forward.cross(Vector3.UP) * half_width * 0.45
		var nose: Vector3 = at + forward * half_width * 0.8
		surface.set_color(_ARROW)
		for corner: Vector3 in [at - side, nose, at + side]:
			surface.add_vertex(corner)
		return true
	return false


func _colour_for(edge: Dictionary) -> Color:
	match colouring:
		Colouring.ELEVATION:
			var level: int = int(edge.get("elevation_level", 0))
			if level > 0:
				return _ELEVATED
			return _TUNNEL if level < 0 else _GROUND
		Colouring.SPEED:
			return _FAST if int(edge.get("speed_limit_kph", 50)) > 50 else _GROUND
		_:
			return _ONE_WAY if edge.get("direction", "both") == "forward" else _TWO_WAY
