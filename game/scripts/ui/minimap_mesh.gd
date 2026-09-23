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
	## True where the law runs one way — along `points`, always: the ETL
	## reverses a backward edge's polyline (`road_graph.gd`).
	var one_way: bool = false
	## True for a main road (`RoadGraph.is_main`): drawn after the level's minor
	## roads, in its own colour, so it runs unbroken through their junctions.
	var main: bool = false


## The one-way arrows (`Q136`, the user's call), in plan metres: an arrowhead
## `length_m` long every `spacing_m` along a one-way stroke.
##
## **No colour of its own.** Where the head fits inside its road it is drawn in
## the FIELD's colour, a light arrow on the dark carriageway; where the road is
## narrower than the head it is drawn in the ROAD's, and reads as barbs standing
## out of a thin line. Both are what a printed street map does, and a third
## colour at 5 px would be noise.
class Arrows:
	var length_m: float = 0.0
	var spacing_m: float = 0.0


## The ground under the roads — the harbour and the parks, the ETL's
## `basemap.json` — as coloured triangles in plan metres, emitted before any
## road so every road draws over it. Water and parks are published disjoint.
class Ground:
	var vertices: PackedVector2Array = PackedVector2Array()
	var colours: PackedColorArray = PackedColorArray()

	## `document`'s water and parks, moved by `offset` — the region's place in
	## the frame (`RoadGraph.region_offset`), in plan metres.
	func add(document: Dictionary, offset: Vector2, water: Color, park: Color) -> void:
		for layer: Array in [[document.get("water", []), water], [document.get("parks", []), park]]:
			var ink: Color = layer[1]
			for triangle: Variant in layer[0]:
				if not triangle is Array or (triangle as Array).size() != 6:
					continue
				var flat: Array = triangle
				for corner: int in 3:
					vertices.append(
						offset + Vector2(float(flat[corner * 2]), float(flat[corner * 2 + 1]))
					)
					colours.append(ink)


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
		stroke.one_way = graph.is_one_way(edge_id)
		stroke.main = graph.is_main(edge_id)
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


## The mesh, or null where there is nothing to draw. `arrows` null draws none,
## and `ground` null draws the roads on the bare field. `main_road` is a main
## road's colour; minor roads take `road`.
static func build(
	strokes: Array[Stroke],
	road: Color,
	main_road: Color,
	casing: Color,
	casing_m: float,
	arrows: Arrows = null,
	ground: Ground = null
) -> ArrayMesh:
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
	if ground != null:
		vertices.append_array(ground.vertices)
		colours.append_array(ground.colours)
	for level: int in levels:
		# The casing first and whole, then the roads: cased a stroke at a time, a
		# deck's casing would cut the deck it joins at a node.
		if level > 0:
			_emit_pass(vertices, colours, by_level[level], casing_m, casing)
		# Minor then main, each a pass of its own: a junction's cap is the pass's,
		# so a main road's is drawn over the minor road meeting it and the main
		# road reads as one line through the grid.
		var minor: Array = by_level[level].filter(
			func(stroke: Stroke) -> bool: return not stroke.main
		)
		var main: Array = by_level[level].filter(func(stroke: Stroke) -> bool: return stroke.main)
		_emit_pass(vertices, colours, minor, 0.0, road)
		_emit_pass(vertices, colours, main, 0.0, main_road)
		# After this level's roads and before the next level's casing, so a deck
		# hides the arrows of the street under it and carries its own.
		if arrows != null:
			for stroke: Stroke in by_level[level]:
				if stroke.one_way:
					_emit_arrows(vertices, colours, stroke, arrows, road, casing)

	return CanvasMesh.of(vertices, colours)


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


## How wide an arrowhead is, as a share of its length.
const ARROW_ASPECT: float = 0.8


## `stroke`'s arrowheads: evenly spaced about its middle, at least one on any
## stroke half a spacing long, each pointing along the vertex order.
static func _emit_arrows(
	vertices: PackedVector2Array,
	colours: PackedColorArray,
	stroke: Stroke,
	arrows: Arrows,
	road: Color,
	field: Color
) -> void:
	var length: float = 0.0
	for index: int in stroke.points.size() - 1:
		length += stroke.points[index].distance_to(stroke.points[index + 1])
	if length < arrows.spacing_m * 0.5 or length < arrows.length_m:
		return
	var count: int = maxi(1, roundi(length / arrows.spacing_m))
	var fits: bool = stroke.width_m >= arrows.length_m * ARROW_ASPECT * 1.25
	var ink: Color = field if fits else road
	var next: int = 0
	var walked: float = 0.0
	for index: int in stroke.points.size() - 1:
		var a: Vector2 = stroke.points[index]
		var b: Vector2 = stroke.points[index + 1]
		var run: float = a.distance_to(b)
		while next < count and (float(next) + 0.5) * length / float(count) <= walked + run:
			var along: Vector2 = (b - a) / maxf(run, 0.001)
			var at: Vector2 = a + along * ((float(next) + 0.5) * length / float(count) - walked)
			var half: Vector2 = along.orthogonal() * arrows.length_m * ARROW_ASPECT * 0.5
			var tail: Vector2 = at - along * arrows.length_m * 0.5
			vertices.append_array([at + along * arrows.length_m * 0.5, tail + half, tail - half])
			colours.append_array([ink, ink, ink])
			next += 1
		walked += run


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
