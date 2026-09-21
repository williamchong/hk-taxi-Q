class_name MinimapMesh
extends RefCounted
## The minimap's roads as ONE mesh (`P3-44`, `Q136`).
##
## 🔴 **One mesh, not a `draw_polyline` an edge.** A canvas polyline is a polygon
## command with a vertex buffer of its own, and those do not batch: Wan Chai's
## 792 edges would be hundreds of draw calls against a frame budgeted at
## 136-150. One `ArrayMesh` is one call and a static buffer, and the map then
## moves by a transform that rebuilds nothing.
##
## **Decks draw over streets by being emitted later.** A mesh draws its
## triangles in index order, so levels go in ascending, and each level above
## grade is preceded by its own casing — a wider stroke in the FIELD's colour —
## which is what makes Canal Road Flyover read as over Hennessy rather than as a
## junction with it.
##
## ⚠️ **Both colours must be opaque** and `verify_hud.gd` says so: strokes
## overlap at every joint and every junction, and a translucent road draws each
## overlap as a darker blot.

## Sides of the cap at a junction. Interior vertices take a bevel — one
## triangle — and only the ends, where edges meet at any angle, need something
## round; six sides is round at the 4-6 px radius a road has here.
const CAP_SIDES: int = 6

## `sin` of the turn under which a joint gets no bevel: the notch it would fill
## is `half * sin`, which on a 10 m road at 6 degrees is half a metre — under
## half a pixel at any span this map is drawn at.
const BEVEL_MIN_SIN: float = 0.1

## How finely two stroke ends are told apart when their caps are shared, in
## metres. The graph's nodes are exact; this only has to absorb float noise.
const NODE_SNAP_M: float = 0.1

# 🔴 **The three above are what the map costs a frame.** Built naively — a cap a
# stroke end, a bevel each side of every vertex, every published vertex kept —
# the two shipped regions are 37.7k triangles, an eighth of the mobile budget,
# for a 240 px readout. Ends at one node share a cap, a bevel is one triangle on
# the outside of a turn that needs it, and `strokes_of` drops vertices that move
# the line less than the caller's tolerance.


## One road edge in plan metres.
class Stroke:
	var points: PackedVector2Array = PackedVector2Array()
	var width_m: float = 0.0
	var level: int = 0


## Every drivable edge of `graph` as a stroke, no narrower than `min_width_m`,
## less the vertices that move it under `tolerance_m`.
static func strokes_of(graph: RoadGraph, min_width_m: float, tolerance_m: float) -> Array[Stroke]:
	var strokes: Array[Stroke] = []
	for edge_id: int in graph.edge_ids():
		if not graph.is_drivable(edge_id):
			continue
		var stroke := Stroke.new()
		var published := PackedVector2Array()
		for point: Vector3 in graph.polyline_of(edge_id):
			published.append(MinimapProjection.plan(point))
		stroke.points = simplified(published, tolerance_m)
		stroke.width_m = maxf(graph.width_of(edge_id), min_width_m)
		stroke.level = graph.level_of(edge_id)
		strokes.append(stroke)
	return strokes


## `points` less every interior vertex within `tolerance_m` of the line through
## the last vertex kept and the next one. Greedy and one pass: the ends are a
## junction's and never move.
static func simplified(points: PackedVector2Array, tolerance_m: float) -> PackedVector2Array:
	if points.size() < 3:
		return points
	var kept := PackedVector2Array([points[0]])
	for index: int in range(1, points.size() - 1):
		var from: Vector2 = kept[kept.size() - 1]
		var along: Vector2 = (points[index + 1] - from).normalized()
		if absf(along.cross(points[index] - from)) > tolerance_m:
			kept.append(points[index])
	kept.append(points[points.size() - 1])
	return kept


## The mesh, or null where there is nothing to draw.
static func build(strokes: Array[Stroke], road: Color, casing: Color, casing_m: float) -> ArrayMesh:
	var by_level: Dictionary[int, Array] = {}
	for stroke: Stroke in strokes:
		if stroke.points.size() < 2:
			continue
		if not by_level.has(stroke.level):
			by_level[stroke.level] = []
		by_level[stroke.level].append(stroke)
	if by_level.is_empty():
		return null

	var levels: Array = by_level.keys()
	levels.sort()
	var vertices := PackedVector2Array()
	var colours := PackedColorArray()
	for level: int in levels:
		# The casing first and whole, then the roads: cased a stroke at a time, a
		# deck's casing would cut the deck it joins at a node.
		if level > 0:
			_emit_pass(vertices, colours, by_level[level], casing_m, casing)
		_emit_pass(vertices, colours, by_level[level], 0.0, road)

	var arrays: Array = []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = vertices
	arrays[Mesh.ARRAY_COLOR] = colours
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	return mesh


## One level in one colour: every stroke, then one cap a junction at the widest
## half that meets there.
static func _emit_pass(
	vertices: PackedVector2Array,
	colours: PackedColorArray,
	strokes: Array,
	grow_m: float,
	colour: Color
) -> void:
	var before: int = vertices.size()
	var caps: Dictionary[Vector2i, float] = {}
	var centres: Dictionary[Vector2i, Vector2] = {}
	for stroke: Stroke in strokes:
		var half: float = stroke.width_m * 0.5 + grow_m
		_emit(vertices, stroke.points, half)
		for end: Vector2 in [stroke.points[0], stroke.points[stroke.points.size() - 1]]:
			var key := Vector2i((end / NODE_SNAP_M).round())
			caps[key] = maxf(caps.get(key, 0.0), half)
			centres[key] = end
	for key: Vector2i in caps:
		for step: int in CAP_SIDES:
			var from: float = TAU * float(step) / float(CAP_SIDES)
			var to: float = TAU * float(step + 1) / float(CAP_SIDES)
			vertices.append_array(
				[
					centres[key],
					centres[key] + Vector2.from_angle(from) * caps[key],
					centres[key] + Vector2.from_angle(to) * caps[key]
				]
			)
	colours.resize(vertices.size())
	for index: int in range(before, vertices.size()):
		colours[index] = colour


## One stroke's triangles: a quad a segment, a bevel on the outside of a turn.
static func _emit(vertices: PackedVector2Array, points: PackedVector2Array, half: float) -> void:
	var last_side := Vector2.ZERO
	for index: int in points.size() - 1:
		var a: Vector2 = points[index]
		var b: Vector2 = points[index + 1]
		if a.is_equal_approx(b):
			continue
		var side: Vector2 = (b - a).normalized().orthogonal() * half
		vertices.append_array([a - side, a + side, b + side, a - side, b + side, b - side])
		# `cross` of the two sides is `half^2 * sin(turn)`, signed by which way the
		# road bends — which is also which side the notch opens on.
		var turn: float = last_side.cross(side) / (half * half)
		if last_side != Vector2.ZERO and absf(turn) > BEVEL_MIN_SIN:
			# `orthogonal()` is `(y, -x)`: right then down is a positive turn, and its
			# notch is up and to the right — the `+side` of both segments.
			var outer: float = signf(turn)
			vertices.append_array([a, a + last_side * outer, a + side * outer])
		last_side = side
