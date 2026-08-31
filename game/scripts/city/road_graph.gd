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
## are topologically connected to the streets and geometrically unreachable, so
## the slice drives the streets and the flyovers are scenery. Ask for one by id
## and you still get it: `P3-3`'s traffic and any later ramp work need those 60
## edges to exist, they just must never be handed a car.
##
## ⚠️ **Passability is expressed here, never enforced.** Some drivable level-0
## edges keep less than one lane clear (`Q19`, `Q51`), so `is_routable` exists
## to keep `P3-3`'s traffic off them — but `nearest_edge` is untouched and answers on a
## blocked edge exactly as it does anywhere else. That is deliberately *not*
## `Q13`'s pattern above: an off-grade edge is refused because a car cannot be
## there, while a car can be — and `RoadSpawn` can already put one — on a
## blocked level-0 edge. Refusing those would blank the road name and the lane
## centre precisely where the player is stuck against a wall (`Q51`). What a
## query does instead is *report* it: `Hit.clear_width_m` is the gap where the
## hit landed, so a consumer that must not put a car in a wall — `RoadSpawn` —
## can guard itself without the index deciding for every other caller.
##
## What is unreachable is what `elevation_levels` *draws* — a flat deck at
## `terrain + 6.0` with a cliff at each end — rather than anything the source
## failed to publish. All 36 mixed-level nodes are ramps, and the climb is split
## across a level-0 and a level-1 edge because `ELEVATION` flips partway up
## rather than at the touchdown. `P2-7` will sample both sides from the map
## sheets; this refusal stays regardless, because opening the network is Phase 4.

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
	## Widest gap a car could get through **where this hit is**, in metres
	## (`Q51` publishes it, `Q52` reads it here), or `CityManifest.NOT_MEASURED`
	## where no cross-section was judged — which is "nothing is known to stand
	## here" rather than "this is clear".
	##
	## Per hit, not per edge, because the two answer different questions. A
	## router traverses a whole edge and reads `min_clear_width_of`; anything
	## *placing* a car occupies one stretch of it, and reporting the edge's
	## minimum here would condemn a hit standing in clear road because a wall
	## stands somewhere else on the same street.
	##
	## ⚠️ **The resolution is the segment, not the point.** A segment is worth
	## the tighter of its two stations, and Wan Chai's run to 155 m — so on the
	## 201 level-0 edges publishing only two stations this and
	## `min_clear_width_of` are the same number. They differ on 31 of 2959
	## segments, always in the conservative direction.
	##
	## Carried, never enforced: the query still resolves on a blocked edge and
	## this is what lets a consumer guard itself. See the class docstring.
	var clear_width_m: float = CityManifest.NOT_MEASURED
	## True where the source signs the edge one-way.
	var one_way: bool = false
	## The street's name in each language the source publishes it in. Both are
	## empty on the 74 edges that carry no name, and **never one without the
	## other** — measured over the shipped document, `en` without `zh` and `zh`
	## without `en` are both 0 — so a consumer needs no mixed-language state.
	var road_name_en: String = ""
	var road_name_zh: String = ""

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
# The same names in Chinese. A second array rather than a joined string:
# the plate draws them as two lines in two different typefaces, which is
# what a Hong Kong street sign is, and splitting one back apart per query
# would be work on the path `P2-2` budgets at 1 ms.
var _names_zh: PackedStringArray = PackedStringArray()
var _by_id: Dictionary[int, int] = {}
var _node_count: int = 0
var _restriction_count: int = 0
# Drawn half-width per station of each edge, from `city.json`, resolved once at
# build time so a query is an array index rather than a dictionary lookup on the
# hot path. Parallel to `_polylines[slot]` since `Q23`: the width varies along an
# edge that climbs onto a bridge. An edge the manifest did not name gets an empty
# entry, and `_build` warns rather than papering over it.
var _drawn_half: Array[PackedFloat32Array] = []
# Widest gap a car could get through, per station, from `city.json`. Parallel to
# `_polylines[slot]` for the same reason as `_drawn_half`, and holding
# `CityManifest.NOT_MEASURED` where the ribbon was held back for a junction cap.
# An edge the manifest did not name gets an empty entry and reads as unknown
# rather than as blocked.
var _clear: Array[PackedFloat32Array] = []
# One lane, from `city.json`. The bar `is_passable` reads `_clear` against, and
# not derivable here: `width_m` is `lanes x lane_width_m` hand-tuned upward.
var _lane_width_m: float = 0.0
# The car's own width, from `city.json`. The bar `fits_car` reads the *same*
# `_clear` against — 🔴 two bars over one measurement, never two measurements.
# `_lane_width_m` is what `P3-3`'s traffic is routed on and this is what the
# player is fenced at, and `Q19` ruled they may never be merged: at 1.80 m the
# router would send traffic down `e207`'s 1.95 m, and at 3.20 m the fence would
# close `e781`'s 3.50 m against a car that fits.
var _car_width_m: float = 0.0

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
		live._build(GeneratedRoadGraph.load_graph(), CityManifest.load_manifest())
		_shared = weakref(live)
	return live


## Parse a document directly, for tools that hold their own copy.
static func from_document(document: Dictionary, manifest: CityManifest = null) -> RoadGraph:
	var graph := RoadGraph.new()
	graph._build(document, manifest)
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


## The street width the graph publishes — not what is drawn.
##
## ⚠️ **No longer always authored** (`Q95`): on the edges two publishers span,
## this is a measured carriageway rather than `lanes x lane_width_m`, and
## `width_source` on the edge says which. What it is never is the ribbon —
## that is `drawn_half_width_of`.
func width_of(edge_id: int) -> float:
	return _widths[_by_id[edge_id]] if _by_id.has(edge_id) else 0.0


## Half-width of the carriageway as `P1-4` actually drew it, from `city.json`,
## at one station of the edge's polyline.
##
## ⚠️ **Per station, not per edge**, since `Q23`. `elevation_level` is an
## attribute of a whole edge but a road becomes a bridge partway along one, and
## on a bridge the ribbon is drawn at its authored width — so a level-0 edge
## climbing onto a ramp is 3.20 m at one end and 5.12 m at the other. Asking
## without a station is asking which of the two you meant.
##
## `station` is a vertex index into `polyline_of(edge_id)`, clamped. It has no
## default: the whole point of this signature is that "the drawn half-width of
## edge N" stopped being a question with one answer, and a default would make
## the ambiguous call legal and quietly return the start of the edge. Between
## two vertices `_fill` interpolates instead, off the fraction the query already
## resolved.
##
## Falls back to half the authored width where the manifest carried no entry, so
## a preview opened without a built city still draws something — `_build` has
## already warned that the lane centres will be short.
func drawn_half_width_of(edge_id: int, station: int) -> float:
	if not _by_id.has(edge_id):
		return 0.0
	return _half_at(_by_id[edge_id], station, 0.0)


## True when **every** edge has a published carriageway width behind it.
##
## Every, not any: one entry of 797 would otherwise pass the gate while the
## other 796 silently took the authored-width fallback.
func has_carriageway_widths() -> bool:
	return _complete(_drawn_half)


## One lane, in metres, as the bundle published it — the bar `is_passable` uses.
##
## Zero where no manifest was read, which makes every edge with a measurement
## passable. That is the same fallback `_build` warns about for the widths: a
## preview opened without a built city should still show a graph, and the
## warning is what says the answers are not the shipped ones.
func lane_width_m() -> float:
	return _lane_width_m


## The car's own width, in metres — the bar `fits_car` uses (`P3-29`).
##
## Zero where the bundle published none, which leaves every edge unfenced. Same
## fallback and same reason as `lane_width_m` above: a preview opened without a
## built city should still show a graph, and a missing bar is not a bar of zero.
func car_width_m() -> float:
	return _car_width_m


## Widest gap a car could get through at one station, in metres (`Q51`).
##
## `station` is a vertex index into `polyline_of(edge_id)`, clamped, and it has
## no default for the same reason `drawn_half_width_of` has none: a wall stands
## somewhere along an edge rather than over the whole of it, so "the clearance of
## edge N" is not a question with one answer.
##
## ⚠️ **A segment between two stations is judged by the *smaller* of its ends,
## never by interpolating them.** The widening tapers smoothly and `_half_at`
## lerps across it; a clearance does not taper — a wall has an edge — and lerping
## would invent a gap halfway into it that a router would then drive at.
##
## Returns `CityManifest.NOT_MEASURED` where `surface.py` held the ribbon back
## for a junction cap and there was no cross-section to judge, and `0.0` for an
## edge that is not in the graph.
func clear_width_of(edge_id: int, station: int) -> float:
	if not _by_id.has(edge_id):
		return 0.0
	return _clear_station(_by_id[edge_id], station)


## The tightest measured station of an edge — the number the bar is read against.
##
## `INF` where the edge has no measured station at all, which is "nothing is
## known to stand here" rather than "this is clear": every station of a short
## edge can be swallowed by the junction caps at its two ends. `0.0` for an edge
## that is not in the graph, so an id nobody recognises is never routable.
func min_clear_width_of(edge_id: int) -> float:
	if not _by_id.has(edge_id):
		return 0.0
	var tightest: float = INF
	for width: float in _clear[_by_id[edge_id]]:
		if width != CityManifest.NOT_MEASURED:
			tightest = minf(tightest, width)
	return tightest


## True where every measured station of the edge keeps at least one lane clear.
##
## Not a statement about the level: an off-grade edge can be perfectly passable
## and still be one `Q13` will not hand a car. `is_routable` is the conjunction.
func is_passable(edge_id: int) -> bool:
	if not _by_id.has(edge_id):
		return false
	# A missing bar is not a bar of zero. `0.0 >= 0.0` would call a measured
	# 0.00 m corridor passable, which is the one answer that is certainly
	# wrong; with nothing to compare against the honest reading is that the
	# edge is unjudged, and `_build` has already warned that it is.
	if _lane_width_m <= 0.0:
		return true
	return min_clear_width_of(edge_id) >= _lane_width_m


## True where the slice lets a car onto this edge **and** a car fits down it.
##
## The predicate `P3-3` routes on. Deliberately separate from `nearest_edge`,
## which still answers on a blocked edge — see the class docstring.
func is_routable(edge_id: int) -> bool:
	return is_drivable(edge_id) and is_passable(edge_id)


## Every drivable edge a car cannot fit down, in document order.
func impassable_edge_ids() -> PackedInt32Array:
	var blocked := PackedInt32Array()
	for slot: int in _ids.size():
		var edge_id: int = _ids[slot]
		if is_drivable(edge_id) and not is_passable(edge_id):
			blocked.append(edge_id)
	return blocked


## True where every measured station keeps the **car's own width** clear (`Q19`).
##
## 🔴 **Beside `is_passable`, never inside it.** The two read the same `_clear`
## against different bars because they answer different questions: `is_passable`
## is `P3-3`'s routing gate at one lane, this is whether the player is stuck.
## Merging them breaks whichever way it is merged — at 1.80 m traffic is routed
## down `e207`'s 1.95 m, at 3.20 m the player is fenced out of `e781`'s 3.50 m.
##
## A missing bar is not a bar of zero, exactly as in `is_passable`: with nothing
## published to compare against, the honest reading is that no edge is fenced
## rather than that every one is.
##
## ⚠️ **Lateral only, and that is measured rather than left undone.** `Q19`
## prescribed a vertical term beside this one and `P3-29` withdrew it: the
## 0.18-0.30 m band it would read is the band `Q23`'s bumper floor exists to
## suppress, so it fences climbing ramps and still misses `e99` FLEMING ROAD,
## which keeps 4.50 m of genuinely clear channel and passes this bar honestly.
func fits_car(edge_id: int) -> bool:
	if not _by_id.has(edge_id):
		return false
	if _car_width_m <= 0.0:
		return true
	return min_clear_width_of(edge_id) >= _car_width_m


## Every drivable edge the player is fenced out of, in document order (`P3-29`).
##
## Mirrors `impassable_edge_ids` in shape and is deliberately a different set:
## the fence is what `pipeline/fence.py` stands a barrier at, where the blocked
## set is what the router avoids. ⚠️ The fence is a **subset** of the blocked
## set by construction — the car is narrower than a lane — so a build where it
## is not is a build where the two bars have crossed.
func fenced_edge_ids() -> PackedInt32Array:
	var fenced := PackedInt32Array()
	for slot: int in _ids.size():
		var edge_id: int = _ids[slot]
		if is_drivable(edge_id) and not fits_car(edge_id):
			fenced.append(edge_id)
	return fenced


## True when **every** edge has a clearance measurement behind it.
##
## Every, not any — and implemented that way, which `has_carriageway_widths`
## above was not when `P2-2` shipped it. One entry of 797 would otherwise pass
## the gate while the other 796 silently read as unknown, and unknown reads as
## passable.
func has_clearances() -> bool:
	return _complete(_clear)


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
## `width_m`.** The graph publishes the street — measured where two publishers
## span it and authored elsewhere (`Q95`) — while `P1-4` draws the ribbon at
## `max(width_m, floor_for(speed_limit_kph, elevation_level))`: a 10.24 m floor
## by default and 0.0 m on structure, so it is not always wider than the street
## it covers, and since `Q95` it can be exactly equal at grade.
## `etl/pipeline/config.py` keeps that factor on the surface
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


func _build(document: Dictionary, manifest: CityManifest = null) -> void:
	var half_widths: Dictionary[int, PackedFloat32Array] = {}
	var clearances: Dictionary[int, PackedFloat32Array] = {}
	if manifest != null:
		half_widths = manifest.carriageway_half_width_m
		clearances = manifest.carriageway_clear_width_m
		_lane_width_m = manifest.lane_width_m
		# No second table: `fits_car` reads the same `clearances` against its own
		# bar, so there is nothing here that can fall out of step with the widths.
		_car_width_m = manifest.car_width_m
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
	if not edges.is_empty() and clearances.is_empty():
		# Louder than it looks. With no table every edge reads `INF` clear, so
		# `is_routable` is true everywhere, `impassable_edge_ids` is empty and
		# the overlay draws nothing — a graph that says the city is clear is
		# indistinguishable from one that has never been told otherwise.
		push_warning(
			(
				(
					"No carriageway clearances in %s; every edge will read as passable "
					+ "and traffic may be routed into a wall. Rebuild the region and "
					+ "re-run tools/sync_generated.sh."
				)
				% CityManifest.PATH
			)
		)
	if edges.is_empty():
		return
	_node_count = (document.get("nodes", []) as Array).size()
	_restriction_count = (document.get("turn_restrictions", []) as Array).size()
	var out_of_step: int = 0
	var clear_out_of_step: int = 0

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
		var chinese: Variant = names.get("zh")
		_names_zh.append(chinese if chinese is String else "")

		var lengths := PackedFloat32Array()
		lengths.resize(points.size())
		lengths[0] = 0.0
		for step: int in points.size() - 1:
			lengths[step + 1] = lengths[step] + plan_distance(points[step], points[step + 1])
		_prefix.append(lengths)
		var halves: PackedFloat32Array = PackedFloat32Array()
		if half_widths.has(id):
			var published: PackedFloat32Array = half_widths[id]
			if published.size() != points.size() and not published.is_empty():
				out_of_step += 1
			halves = _matched(published, points.size())
		_drawn_half.append(halves)

		# Read the same way and counted separately: the two tables come from the
		# same document but a short one means different things. A short width
		# array is a lane centre off the tarmac; a short clearance array is a
		# station a router would call clear because nobody measured it.
		var clear: PackedFloat32Array = PackedFloat32Array()
		if clearances.has(id):
			var measured: PackedFloat32Array = clearances[id]
			if measured.size() != points.size() and not measured.is_empty():
				clear_out_of_step += 1
			clear = _matched(measured, points.size())
		_clear.append(clear)

	_warn_out_of_step(out_of_step, "carriageway width")
	_warn_out_of_step(clear_out_of_step, "clearance")

	_index()


## One message for a table that does not line up with the polylines it indexes.
##
## Once, not per edge: a stale manifest misses on every edge it has, and 797
## identical warnings bury the one line that says what to do. Shared by both
## tables so the two cannot end up phrased differently for the same fault.
func _warn_out_of_step(count: int, what: String) -> void:
	if count <= 0:
		return
	push_warning(
		(
			(
				"%d edges publish a %s array that does not match their polyline; "
				+ "city.json and roadgraph.json are out of step. Re-run "
				+ "tools/sync_generated.sh."
			)
			% [count, what]
		)
	)


## True when every edge has an entry in a per-station table.
##
## **Every**, not any. `has_carriageway_widths` was documented "every" and
## implemented "any" when `P2-2` shipped it: one entry of 797 passed the gate
## while the other 796 silently took a fallback. Shared so the two tables cannot
## drift back apart.
func _complete(table: Array[PackedFloat32Array]) -> bool:
	for slot: int in table.size():
		if table[slot].is_empty():
			return false
	return not _ids.is_empty()


## A published per-station array, resized to the polyline it belongs to.
##
## Matched rather than trusted to match. The ETL writes both tables from one
## array and `test_surface.py` pins that they agree — but a stale `city.json`
## beside a fresh `roadgraph.json` is the one pairing `sync_generated.sh` cannot
## make impossible, and a short array read past its end is a wrong answer rather
## than an error. The matched case takes the published array whole: a
## `PackedFloat32Array` is copy-on-write, so that is O(1) and the per-station
## loop is only paid by a bundle that is already wrong.
static func _matched(published: PackedFloat32Array, count: int) -> PackedFloat32Array:
	if published.size() == count:
		return published
	if published.is_empty():
		return PackedFloat32Array()
	var padded := PackedFloat32Array()
	padded.resize(count)
	for step: int in count:
		padded[step] = published[mini(step, published.size() - 1)]
	return padded


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
	hit.road_name_zh = _names_zh[slot]

	var lengths: PackedFloat32Array = _prefix[slot]
	var total: float = lengths[lengths.size() - 1]
	# `point` is `_closest_on_segment`'s output, so it lies on `[a, b]` and this
	# one distance answers both `t` and the width fraction below. Projecting
	# again would be the third copy of a maths `_closest_on_segment` already did
	# and discarded, on the query path `P2-2` budgets at 1 ms.
	var offset_m: float = plan_distance(a, point)
	hit.t = clampf((lengths[step] + offset_m) / total, 0.0, 1.0) if total > 0.0 else 0.0

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

	# The width where the car actually is, not where the edge starts. On the
	# `WAN CHAI INTERCHANGE` approaches those differ by the whole 1.6x widening
	# over a single edge, and the lane centre moves 0.96 m with it.
	#
	# The segment's own plan length comes off the prefix table rather than being
	# measured: `step + 1` is always in bounds, since `_index` only ever emits
	# `step` up to `points.size() - 2`. Zero length cannot occur — `dedupe` and
	# the two-point guard in `_build` rule it out — but a division by it would
	# reach a spawn transform as a NaN rather than as an error.
	var span_m: float = lengths[step + 1] - lengths[step]
	var half: float = _half_at(slot, step, offset_m / span_m if span_m > 0.0 else 0.0)
	hit.lane_centre = point + left_of(along) * lane_offset(half * 2.0, _lanes[slot])
	hit.clear_width_m = _clear_at(slot, step)


## Drawn half-width `fraction` of the way from station `step` to the next.
##
## Interpolated rather than snapped to the nearer station. `surface.py` tapers
## the width over ~15 m while `roads.py` resamples a lifted edge at 10 m, so a
## whole taper can live inside two stations — snapping would put a 1.9 m step in
## the lane centre exactly where the ribbon under it changes smoothly.
func _half_at(slot: int, step: int, fraction: float) -> float:
	var halves: PackedFloat32Array = _drawn_half[slot]
	if halves.is_empty():
		return _widths[slot] * 0.5
	var here: int = clampi(step, 0, halves.size() - 1)
	var next: int = mini(here + 1, halves.size() - 1)
	return lerpf(halves[here], halves[next], fraction)


## Clear width over the segment running from station `step` to the next.
##
## `_half_at`'s deliberate opposite, and that is why it is a second function
## rather than a flag on the first: the widening tapers, so a drawn half-width
## interpolates; a clearance does not taper — a wall has an edge — so a segment
## is worth the **smaller** of the two stations bounding it. That is
## `clear_width_of`'s rule, and this is where it gets applied to a segment
## rather than to a station.
##
## ⚠️ **An unmeasured end is skipped, not minimised.** `NOT_MEASURED` is -1.0 and
## so sorts below every real clearance; `minf` would read "nothing was judged
## here" off every segment with one end under a junction cap — **562 of Wan
## Chai's 2959**, the start line's own included. `min_clear_width_of` skips them
## for the same reason, and only both ends unmeasured is unjudged (45 more).
func _clear_at(slot: int, step: int) -> float:
	var here: float = _clear_station(slot, step)
	var next: float = _clear_station(slot, step + 1)
	if here == CityManifest.NOT_MEASURED:
		return next
	if next == CityManifest.NOT_MEASURED:
		return here
	return minf(here, next)


# One station's clear width, by slot. `clear_width_of` is this plus the id
# lookup and `_clear_at` calls it twice, which is the split `_half_at` and
# `drawn_half_width_of` already use — and it keeps the hash off `_fill`.
func _clear_station(slot: int, station: int) -> float:
	var widths: PackedFloat32Array = _clear[slot]
	if widths.is_empty():
		return CityManifest.NOT_MEASURED
	return widths[clampi(station, 0, widths.size() - 1)]
