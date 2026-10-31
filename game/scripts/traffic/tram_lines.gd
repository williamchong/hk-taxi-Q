class_name TramLines
extends RefCounted
## Every route a tram can run, in the merged graph's frame (`P3-4`, `Q176`), off
## each resident region's `tram_lines.json`.
##
## 🔴 **Which way a track runs and what it joins is the ETL's**
## (`etl/pipeline/tramlines.py`). The one thing made here is the seam: which
## regions are resident is a fact about this run, so a line leaving one region is
## joined to the line entering the next here, by where their ends stand.
##
## **A route is a whole trip, line end to line end**, one polyline with its stops
## and stop lines in travel metres, so a tram is a number along it and a fork was
## settled when the tram set out. Each runs `run_off_m` past both ends in a straight
## line: a tram appears and goes out of sight past the street's closure, not at it.

const GeneratedDocument = preload("res://scripts/city/generated_document.gd")
const GeneratedRegions = preload("res://scripts/city/generated_regions.gd")

## Schema this understands, matching `TRAM_LINES_SCHEMA` in `etl/pipeline/tramlines.py`.
const SCHEMA_VERSION: int = 1
## Routes kept, in the order the walk finds them.
const MAX_ROUTES: int = 256
## Steps of the walk: bad joins with no way out are exponential in simple paths, and
## would hang the boot rather than read as `unreached`.
const MAX_WALK_STEPS: int = 100000


## A stop line on a route.
class Line:
	extends RefCounted

	var s_m: float
	var edge: int
	var along: bool


## A tram stop on a route.
class Stop:
	extends RefCounted

	var s_m: float
	var id: String


## One whole trip.
class Route:
	extends RefCounted

	var points: PackedVector3Array = PackedVector3Array()
	## Metres along at each point, by plan length.
	var along_m: PackedFloat64Array = PackedFloat64Array()
	var stops: Array[Stop] = []
	var lines: Array[Line] = []
	## Which regions it runs through, for the verify tool.
	var regions: PackedStringArray = PackedStringArray()

	func length_m() -> float:
		return along_m[-1]

	## The point `s_m` along, clamped to the route.
	func at(s_m: float) -> Vector3:
		var row: int = clampi(along_m.bsearch(s_m, true), 1, along_m.size() - 1)
		var span: float = along_m[row] - along_m[row - 1]
		var u: float = 0.0 if span <= 0.0 else clampf((s_m - along_m[row - 1]) / span, 0.0, 1.0)
		return points[row - 1].lerp(points[row], u)


## One directed bed, while the routes are walked.
class Track:
	extends RefCounted

	var region: String
	var points: PackedVector3Array = PackedVector3Array()
	var length_m: float = 0.0
	var next: Array[Track] = []
	var open_start: bool = false
	var open_end: bool = false
	var stops: Array[Dictionary] = []
	var signals: Array[Dictionary] = []


var routes: Array[Route] = []
## Ends the seam joined, for the verify tool.
var seam_joins: int = 0
## Tracks a route never reached, for the verify tool: a join that went nowhere.
var unreached: int = 0
## Stop lines on an edge the merged graph does not hold.
var lines_dropped: int = 0

var _walk_steps: int = 0


## Every resident region's lines over `graph`. Empty where no region has any.
static func resident(graph: RoadGraph, table: TramProfile) -> TramLines:
	var lines := TramLines.new()
	var tracks: Array[Track] = []
	for region: String in GeneratedRegions.resident():
		var manifest: CityManifest = CityManifest.shared(region)
		if manifest == null or manifest.tram_lines_path.is_empty():
			continue
		var document: Dictionary = GeneratedDocument.load_object(
			manifest.tram_lines_path, SCHEMA_VERSION, "tools/sync_generated.sh"
		)
		tracks.append_array(lines._read_region(document, region, graph))
	lines._join_seams(tracks, table)
	lines._walk(tracks, table, graph)
	return lines


func is_empty() -> bool:
	return routes.is_empty()


func _read_region(document: Dictionary, region: String, graph: RoadGraph) -> Array[Track]:
	var offset: Vector3 = graph.region_offset(region)
	var read: Array[Track] = []
	var rows: Array = document.get("tracks", [])
	for row: Dictionary in rows:
		var track := Track.new()
		track.region = region
		for point: Array in row["points"]:
			track.points.append(Vector3(point[0], point[1], point[2]) + offset)
		for index: int in range(1, track.points.size()):
			track.length_m += RoadGraph.plan_distance(track.points[index - 1], track.points[index])
		track.open_start = row["open_start"]
		track.open_end = row["open_end"]
		track.stops.assign(row["stops"])
		track.signals.assign(row["signals"])
		read.append(track)
	for index: int in read.size():
		var joins: Array = rows[index]["next"]
		for other: int in joins:
			read[index].next.append(read[other])
	return read


## Join a line leaving one region to the line entering another, where the two ends
## stand within `seam_join_m` and run the same way within `seam_heading_deg`.
func _join_seams(tracks: Array[Track], table: TramProfile) -> void:
	var limit: float = cos(deg_to_rad(table.seam_heading_deg))
	for leaving: Track in tracks:
		if not leaving.open_end:
			continue
		var count: int = leaving.points.size()
		var out: Vector3 = (leaving.points[count - 1] - leaving.points[count - 2]).normalized()
		for entering: Track in tracks:
			if not entering.open_start or entering.region == leaving.region:
				continue
			if (
				RoadGraph.plan_distance(leaving.points[count - 1], entering.points[0])
				> table.seam_join_m
			):
				continue
			var into: Vector3 = (entering.points[1] - entering.points[0]).normalized()
			if out.dot(into) < limit:
				continue
			leaving.next.append(entering)
			leaving.open_end = false
			entering.open_start = false
			seam_joins += 1
			break


## Every simple path from a line's start to a line's end.
func _walk(tracks: Array[Track], table: TramProfile, graph: RoadGraph) -> void:
	var reached: Dictionary[Track, bool] = {}
	for track: Track in tracks:
		if track.open_start:
			_extend([track], reached, table, graph)
	unreached = tracks.size() - reached.size()


func _extend(
	path: Array[Track], reached: Dictionary[Track, bool], table: TramProfile, graph: RoadGraph
) -> void:
	_walk_steps += 1
	if routes.size() >= MAX_ROUTES or _walk_steps > MAX_WALK_STEPS:
		return
	var last: Track = path[-1]
	if last.next.is_empty():
		if last.open_end:
			routes.append(_route_of(path, table, graph))
			for track: Track in path:
				reached[track] = true
		return
	for track: Track in last.next:
		if path.has(track):
			continue
		var longer: Array[Track] = path.duplicate()
		longer.append(track)
		_extend(longer, reached, table, graph)


func _route_of(path: Array[Track], table: TramProfile, graph: RoadGraph) -> Route:
	var route := Route.new()
	var first: Track = path[0]
	var back: Vector3 = (first.points[0] - first.points[1]).normalized()
	_add_point(route, first.points[0] + back * table.run_off_m)
	for track: Track in path:
		var start_m: float = (
			route.along_m[-1] + RoadGraph.plan_distance(route.points[-1], track.points[0])
		)
		if not route.regions.has(track.region):
			route.regions.append(track.region)
		for point: Vector3 in track.points:
			_add_point(route, point)
		for row: Dictionary in track.stops:
			var stop := Stop.new()
			stop.id = row["id"]
			stop.s_m = start_m + float(row["s_m"])
			route.stops.append(stop)
		for row: Dictionary in track.signals:
			var edge: int = graph.edge_id_in(track.region, int(row["edge"]))
			if edge < 0:
				lines_dropped += 1
				continue
			var line := Line.new()
			line.edge = edge
			line.along = row["along"]
			line.s_m = start_m + float(row["s_m"])
			route.lines.append(line)
	var count: int = route.points.size()
	var ahead: Vector3 = (route.points[count - 1] - route.points[count - 2]).normalized()
	_add_point(route, route.points[count - 1] + ahead * table.run_off_m)
	route.stops.sort_custom(func(a: Stop, b: Stop) -> bool: return a.s_m < b.s_m)
	route.lines.sort_custom(func(a: Line, b: Line) -> bool: return a.s_m < b.s_m)
	return route


static func _add_point(route: Route, point: Vector3) -> void:
	if route.points.is_empty():
		route.along_m.append(0.0)
	else:
		var step: float = RoadGraph.plan_distance(route.points[-1], point)
		if step <= 0.0:
			return
		route.along_m.append(route.along_m[-1] + step)
	route.points.append(point)
