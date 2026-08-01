class_name RoadGraph
extends RefCounted
## The road graph at runtime: one parse, and the queries that read it (`P2-2`).
##
## Every consumer in a scene shares one parse. The document is 0.65 MB on disk
## and ~6 MB parsed, so a second reader of the same file in the same scene is
## pure waste — hold the result in a **member**, never a local, or the shared
## instance is refcounted away the moment `_ready` returns.
##
## ⚠️ `nearest_edge` never returns an off-grade edge, and that is `Q13`'s
## decision rather than an optimisation. The elevated and underground networks
## are topologically connected to the streets and geometrically unreachable: 20
## of the 28 level-1 edges leaving a mixed-level node begin already elevated,
## because the source publishes no edge spanning the climb. Sampling the map
## sheets' `INFRASTRUCTURE` structures gives a correct deck *profile* — 3.01%
## median grade, measured — but cannot invent the missing ramp, so the slice
## drives the streets and the flyovers are scenery. Ask for one by id and you
## still get it: `P3-3`'s traffic and any later ramp work need those 60 edges to
## exist, they just must never be handed a car.

const GeneratedRoadGraph = preload("res://scripts/city/generated_road_graph.gd")

## Plan-space cell for the segment index. Wan Chai's streets are ~50-150 m
## between junctions, so 25 m keeps a cell's occupancy in single figures without
## making a query straddle more than the four cells it already has to test.
const CELL_M: float = 25.0

## `direction` values in the contract. The source publishes only these two —
## `P1-3` maps `TRAVEL_DIRECTION` onto them and reverses the polyline for the
## backward case, so a "forward" edge always travels along its own vertex order.
const BOTH: StringName = &"both"
const FORWARD: StringName = &"forward"


## What the car is on: the edge, where on it, and which way the law runs there.
class Hit:
	extends RefCounted

	## Edge id from `roadgraph.json`, or -1 for a miss.
	var edge_id: int = -1
	## Closest point on the centreline, at the graph's own height.
	var point: Vector3 = Vector3.ZERO
	## Plan distance from the query point to `point`. Plan, not 3D: the car sits
	## a ride height above the road and `P2-3` may raise it further, so a 3D
	## distance would rank edges by suspension travel.
	var distance: float = INF
	## 0..1 along the edge, by plan length — the same parameter `fares.json`
	## publishes as `edge_t`, so a fare node and a query agree about position.
	var t: float = 0.0
	## Unit travel direction, already resolved against the query heading for a
	## two-way edge. Never zero on a hit.
	var forward: Vector3 = Vector3.FORWARD
	## Centre of the nearside lane for `forward` — where a car belongs, and
	## deliberately not the centreline. See `lane_offset`.
	var lane_centre: Vector3 = Vector3.ZERO
	## True where the source signs the edge one-way.
	var one_way: bool = false
	var road_name_en: String = ""

	func hit() -> bool:
		return edge_id >= 0


# Per-edge, parallel arrays indexed by the order edges appear in the document.
var _ids: PackedInt32Array = PackedInt32Array()
var _polylines: Array[PackedVector3Array] = []
var _one_way: PackedInt32Array = PackedInt32Array()
var _levels: PackedInt32Array = PackedInt32Array()
var _widths: PackedFloat32Array = PackedFloat32Array()
var _lanes: PackedInt32Array = PackedInt32Array()
var _speed_limits: PackedInt32Array = PackedInt32Array()
var _names: PackedStringArray = PackedStringArray()
var _by_id: Dictionary[int, int] = {}
var _node_count: int = 0
var _restriction_count: int = 0
# Drawn half-width per edge, from `city.json`. Empty when the manifest could not
# be read, which `_build` warns about rather than papering over.
var _half_widths: Dictionary[int, float] = {}
# Resolved once per edge at build time, so a query is an array index rather than
# two dictionary lookups on the hot path.
var _drawn_half: PackedFloat32Array = PackedFloat32Array()
# Cumulative **plan** length to each vertex of an edge. Turns `t` into a prefix
# lookup instead of a walk, and `t` is plan-parameterised because that is what
# `fares.py` divides by and so what `edge_t` means.
var _prefix: Array[PackedFloat32Array] = []

# The index, over drivable segments only: flat per-segment arrays plus a
# cell -> segment-indices dictionary. `etl/pipeline/terrain.py` solves the same
# problem with sorted flat arrays and a run-start table, which is faster to
# query and slower to build; here the graph is a tenth of the terrain's triangle
# count and the build happens once per scene, so the simpler structure wins.
var _seg_edge: PackedInt32Array = PackedInt32Array()
var _seg_step: PackedInt32Array = PackedInt32Array()
var _seg_a: PackedVector3Array = PackedVector3Array()
var _seg_b: PackedVector3Array = PackedVector3Array()
var _cells: Dictionary[int, PackedInt32Array] = {}
var _columns: int = 0
var _rows: int = 0
var _origin: Vector2 = Vector2.ZERO

# Held weakly on purpose. A plain static reference would satisfy "one parse" by
# holding 6 MB resident for the life of the process and serving a stale graph
# across an ETL re-run inside the editor — the objection `fare_preview.gd` raised
# against caching at all. A weak reference gives one parse per scene, because the
# scene's own nodes keep it alive and dropping the scene drops it.
static var _shared: WeakRef = null


## The graph every consumer in a scene shares. Empty if it could not be read;
## `GeneratedRoadGraph` has already pushed the reason and the command to fix it.
static func shared() -> RoadGraph:
	var live: RoadGraph = _shared.get_ref() if _shared != null else null
	if live == null:
		live = RoadGraph.new()
		var manifest: CityManifest = CityManifest.load_manifest()
		live._build(
			GeneratedRoadGraph.load_graph(),
			manifest.carriageway_half_width_m if manifest != null else {}
		)
		_shared = weakref(live)
	return live


## Parse a document directly, for tools that hold their own copy.
static func from_document(
	document: Dictionary, half_widths: Dictionary[int, float] = {}
) -> RoadGraph:
	var graph := RoadGraph.new()
	graph._build(document, half_widths)
	return graph


func edge_count() -> int:
	return _ids.size()


## Segments the index will search — drivable ones only.
func indexed_segment_count() -> int:
	return _seg_edge.size()


func is_empty() -> bool:
	return _ids.is_empty()


## Every edge id the document carried, off-grade included.
func edge_ids() -> PackedInt32Array:
	return _ids.duplicate()


## Grade-separation level of an edge, or 0 for an id that is not in the graph.
func level_of(edge_id: int) -> int:
	return _levels[_by_id[edge_id]] if _by_id.has(edge_id) else 0


## Centreline of an edge, off-grade included — `P3-3` routes traffic on these.
func polyline_of(edge_id: int) -> PackedVector3Array:
	# Duplicated, like `edge_ids`. Godot's packed arrays are handed out by
	# reference, so returning the member itself would let any caller rewrite the
	# geometry every other consumer in the scene is sharing.
	if not _by_id.has(edge_id):
		return PackedVector3Array()
	return _polylines[_by_id[edge_id]].duplicate()


## True where the level is one the slice lets a car onto. `Q13`.
func is_drivable(edge_id: int) -> bool:
	return _by_id.has(edge_id) and _levels[_by_id[edge_id]] == 0


## True where the source signs the edge one-way.
func is_one_way(edge_id: int) -> bool:
	return _by_id.has(edge_id) and _one_way[_by_id[edge_id]] == 1


## The **authored** street width the graph publishes — not what is drawn.
func width_of(edge_id: int) -> float:
	return _widths[_by_id[edge_id]] if _by_id.has(edge_id) else 0.0


## Half-width of the carriageway as `P1-4` actually drew it, from `city.json`.
##
## Falls back to half the authored width where the manifest carried no entry, so
## a preview opened without a built city still draws something — `_build` has
## already warned that the lane centres will be short.
func drawn_half_width_of(edge_id: int) -> float:
	if _half_widths.has(edge_id):
		return _half_widths[edge_id]
	return width_of(edge_id) * 0.5


## True when **every** edge has a published carriageway width behind it.
##
## Every, not any: one entry of 797 would otherwise pass the gate while the
## other 796 silently took the authored-width fallback.
func has_carriageway_widths() -> bool:
	for id: int in _ids:
		if not _half_widths.has(id):
			return false
	return not _ids.is_empty()


func speed_limit_of(edge_id: int) -> int:
	return _speed_limits[_by_id[edge_id]] if _by_id.has(edge_id) else 0


# Carried so a consumer that only wants to report the graph's size does not have
# to hold the parsed document alive to count them.
func node_count() -> int:
	return _node_count


func turn_restriction_count() -> int:
	return _restriction_count


## Distance from the centreline to the centre of the nearside lane, for a given
## carriageway width.
##
## ⚠️ **The width must be the *drawn* carriageway, not `roadgraph.json`'s
## `width_m`.** The graph publishes the authored street — `lanes x lane_width_m`
## — while `P1-4` draws the ribbon at `width_m x widen_for(speed_limit_kph)`,
## 1.6x by default. `etl/pipeline/config.py` keeps that factor on the surface
## style deliberately: "the graph is a description of the city, this is how wide
## and how kerbed to draw it. A change here never changes `roadgraph.json`."
##
## So the drawn width arrives through `city.json`'s `carriageway` table instead,
## measured by the stage that drew it. Using the authored width here would put
## the nearside lane 1.60 m off the centreline on `EXPO DRIVE` where the tarmac
## puts it at 2.56 m — a car 0.96 m from where it belongs, and that much nearer
## the seam.
##
## Hong Kong drives on the left, so the nearside lane hugs the left kerb at
## `width_m / 2` whichever way the edge is signed, and its centre sits half a
## lane in from there. Two-way and one-way reduce to the same expression: a
## two-way edge gives each direction `lanes / 2` lanes over `width_m / 2`, a
## one-way edge gives one direction `lanes` lanes over `width_m`, and the lane
## width comes out at `width_m / lanes` either way.
##
## The centreline is the one place on the network a wheel must not go — it is
## where opposed carriageway ribbons overlap and junction caps double up, so a
## suspension ray finds two coplanar triangles centimetres apart and hunts
## between them. `P0-5`'s car crept at 0.8 m/s on 3 of 4 wheels until it moved
## off it.
static func lane_offset(width_m: float, lanes: int) -> float:
	var count: int = maxi(lanes, 1)
	return maxf(width_m, 0.0) * float(count - 1) / (2.0 * float(count))


## The kerb side of a travel direction — left, because Hong Kong drives on it.
##
## One line, and named anyway: it is the direction a lane centre, a stand and a
## spawn all get offset along, and every consumer that writes the cross product
## out has to get the operand order right to mean "left" rather than "right".
static func left_of(forward: Vector3) -> Vector3:
	return Vector3.UP.cross(forward).normalized()


## The drivable edge nearest `point` in plan, or a `Hit` with `edge_id == -1`.
##
## `heading` resolves which way a two-way edge runs for the asker; pass the car's
## forward vector. A zero heading takes the edge's own vertex order.
func nearest_edge(point: Vector3, heading: Vector3 = Vector3.ZERO, radius_m: float = 60.0) -> Hit:
	var best := Hit.new()
	if _seg_edge.is_empty():
		return best

	var best_index: int = -1
	var best_point: Vector3 = Vector3.ZERO
	var reach: int = maxi(1, int(ceil(maxf(radius_m, 0.0) / CELL_M)))
	var centre: Vector2i = _cell_of(point.x, point.z)

	# Rings outward from the query cell, stopping as soon as a ring cannot beat
	# what is already found: everything beyond it is at least `ring - 1` cells
	# away in plan. Without this a query near the region edge scans every cell it
	# is allowed to, and the radius is a correctness bound rather than a budget.
	for ring: int in reach + 1:
		if best.distance <= float(ring - 1) * CELL_M:
			break
		for cell: Vector2i in _ring(centre, ring):
			var key: int = cell.x + cell.y * _columns
			if not _cells.has(key):
				continue
			for index: int in _cells[key]:
				var closest: Vector3 = _closest_on_segment(_seg_a[index], _seg_b[index], point)
				var span: float = plan_distance(closest, point)
				if span < best.distance:
					best.distance = span
					best_index = index
					best_point = closest

	if best_index < 0 or best.distance > radius_m:
		return Hit.new()
	_fill(best, best_index, best_point, heading)
	return best


func _build(document: Dictionary, half_widths: Dictionary[int, float] = {}) -> void:
	_half_widths = half_widths
	var edges: Array = document.get("edges", [])
	if not edges.is_empty() and half_widths.is_empty():
		# Warned rather than tolerated. Without the table every lane centre is
		# short by a quarter of the widening — 0.96 m on a two-lane street — and
		# a car placed there sits that much closer to the ribbon seam. Silence
		# here would look exactly like a correct answer.
		push_warning(
			(
				(
					"No carriageway widths in %s; lane centres fall back to the authored "
					+ "street width and will sit short of the drawn lane. Rebuild the "
					+ "region and re-run tools/sync_generated.sh."
				)
				% CityManifest.PATH
			)
		)
	if edges.is_empty():
		return
	_node_count = (document.get("nodes", []) as Array).size()
	_restriction_count = (document.get("turn_restrictions", []) as Array).size()

	for edge: Dictionary in edges:
		var points: PackedVector3Array = PackedVector3Array()
		for raw: Array in edge.get("polyline", []):
			points.append(Vector3(raw[0], raw[1], raw[2]))
		# A one-point edge has no direction and no length; it would poison the
		# index with a zero-length segment that every query ties on.
		if points.size() < 2:
			continue

		var id: int = int(edge.get("id", -1))
		if _by_id.has(id):
			# `nearest_edge` is defined as an id, so a collision means one of the
			# two is unreachable through every accessor here.
			push_warning("Road graph has two edges with id %d; the later one wins" % id)
		_by_id[id] = _ids.size()
		_ids.append(id)
		_polylines.append(points)
		_one_way.append(1 if StringName(edge.get("direction", BOTH)) == FORWARD else 0)
		_levels.append(int(edge.get("elevation_level", 0)))
		_widths.append(float(edge.get("width_m", 6.0)))
		_lanes.append(int(edge.get("lanes", 2)))
		_speed_limits.append(int(edge.get("speed_limit_kph", 50)))
		# 74 of Wan Chai's 797 edges publish `{"en": null}` — the key is present
		# and the value is not a string. `str(null)` is the literal "<null>", so
		# taking it unchecked puts that in front of a player rather than an
		# empty name a caller can substitute for.
		var names: Dictionary = edge.get("road_name", {})
		var english: Variant = names.get("en")
		_names.append(english if english is String else "")

		var lengths := PackedFloat32Array()
		lengths.resize(points.size())
		lengths[0] = 0.0
		for step: int in points.size() - 1:
			lengths[step + 1] = lengths[step] + plan_distance(points[step], points[step + 1])
		_prefix.append(lengths)
		_drawn_half.append(
			half_widths[id] if half_widths.has(id) else float(edge.get("width_m", 6.0)) * 0.5
		)

	_index()


## Bucket every drivable segment by the plan cells its bounding box touches.
func _index() -> void:
	var low := Vector2(INF, INF)
	var high := Vector2(-INF, -INF)
	for slot: int in _ids.size():
		if _levels[slot] != 0:
			continue
		for point: Vector3 in _polylines[slot]:
			low = Vector2(minf(low.x, point.x), minf(low.y, point.z))
			high = Vector2(maxf(high.x, point.x), maxf(high.y, point.z))
	if low.x > high.x:
		return

	_origin = low
	_columns = maxi(1, int((high.x - low.x) / CELL_M) + 1)
	_rows = maxi(1, int((high.y - low.y) / CELL_M) + 1)

	for slot: int in _ids.size():
		if _levels[slot] != 0:
			continue
		var points: PackedVector3Array = _polylines[slot]
		for step: int in points.size() - 1:
			var a: Vector3 = points[step]
			var b: Vector3 = points[step + 1]
			var index: int = _seg_edge.size()
			_seg_edge.append(slot)
			_seg_step.append(step)
			_seg_a.append(a)
			_seg_b.append(b)

			var from: Vector2i = _cell_of(minf(a.x, b.x), minf(a.z, b.z))
			var to: Vector2i = _cell_of(maxf(a.x, b.x), maxf(a.z, b.z))
			for row: int in range(from.y, to.y + 1):
				for column: int in range(from.x, to.x + 1):
					var key: int = column + row * _columns
					# Read, append, write back. A `PackedInt32Array` is
					# copy-on-write, so `_cells[key].append(...)` appends to a
					# temporary and drops it — an index that silently stays
					# empty and a `nearest_edge` that never hits anything.
					var bucket: PackedInt32Array = _cells.get(key, PackedInt32Array())
					bucket.append(index)
					_cells[key] = bucket


func _cell_of(x: float, z: float) -> Vector2i:
	return Vector2i(
		clampi(int(floor((x - _origin.x) / CELL_M)), 0, _columns - 1),
		clampi(int(floor((z - _origin.y) / CELL_M)), 0, _rows - 1),
	)


## Cells exactly `ring` steps from `centre` — the ring itself, not the disc.
func _ring(centre: Vector2i, ring: int) -> Array[Vector2i]:
	var cells: Array[Vector2i] = []
	if ring == 0:
		if centre.x >= 0 and centre.x < _columns and centre.y >= 0 and centre.y < _rows:
			cells.append(centre)
		return cells
	# The horizontal runs take the corners and the vertical runs stop short of
	# them, so every cell is emitted exactly once. The earlier form walked both
	# axes over the full span and filtered duplicates with `Array.has`, which is
	# a linear scan inside the loop that produces it.
	for offset: int in range(-ring, ring + 1):
		_append_cell(cells, centre.x + offset, centre.y - ring)
		_append_cell(cells, centre.x + offset, centre.y + ring)
	for offset: int in range(-ring + 1, ring):
		_append_cell(cells, centre.x - ring, centre.y + offset)
		_append_cell(cells, centre.x + ring, centre.y + offset)
	return cells


func _append_cell(cells: Array[Vector2i], column: int, row: int) -> void:
	if column >= 0 and column < _columns and row >= 0 and row < _rows:
		cells.append(Vector2i(column, row))


## Distance in plan — the x/z ground plane, ignoring height.
##
## Everything positional here is plan-measured: `edge_t` is defined that way by
## `fares.py`, and a car sits a ride height above the road it is being matched
## to, so a 3D distance would rank edges by suspension travel.
static func plan_distance(a: Vector3, b: Vector3) -> float:
	return Vector2(b.x - a.x, b.z - a.z).length()


static func _closest_on_segment(a: Vector3, b: Vector3, point: Vector3) -> Vector3:
	# Projected in plan, then the height is taken from the road rather than from
	# the query. The caller is a car sitting a ride height above the tarmac.
	var span := Vector2(b.x - a.x, b.z - a.z)
	var length_squared: float = span.length_squared()
	if length_squared <= 0.0:
		return a
	var along := Vector2(point.x - a.x, point.z - a.z)
	var t: float = clampf(along.dot(span) / length_squared, 0.0, 1.0)
	return a.lerp(b, t)


## Everything a `Hit` reports beyond which segment won.
##
## Takes the index of the winning segment rather than re-deriving it. Re-walking
## the polyline would not only repeat the search — it could pick a *different*
## segment on a tie or a self-touching edge, leaving `t` and `forward`
## describing somewhere other than `point`.
func _fill(hit: Hit, index: int, point: Vector3, heading: Vector3) -> void:
	var slot: int = _seg_edge[index]
	var step: int = _seg_step[index]
	var a: Vector3 = _seg_a[index]

	hit.edge_id = _ids[slot]
	hit.point = point
	hit.one_way = _one_way[slot] == 1
	hit.road_name_en = _names[slot]

	var lengths: PackedFloat32Array = _prefix[slot]
	var total: float = lengths[lengths.size() - 1]
	hit.t = (
		clampf((lengths[step] + plan_distance(a, point)) / total, 0.0, 1.0) if total > 0.0 else 0.0
	)

	var along: Vector3 = _seg_b[index] - a
	along.y = 0.0
	along = along.normalized() if along.length_squared() > 0.0 else Vector3.FORWARD
	# A two-way edge has no travel direction of its own, so it takes the asker's.
	# Facing the wrong way down a one-way street is a fact about the car and must
	# survive into the overlay rather than being quietly corrected here.
	var flat_heading := Vector3(heading.x, 0.0, heading.z)
	if not hit.one_way and flat_heading.length_squared() > 0.0 and along.dot(flat_heading) < 0.0:
		along = -along
	hit.forward = along

	hit.lane_centre = point + left_of(along) * lane_offset(_drawn_half[slot] * 2.0, _lanes[slot])
