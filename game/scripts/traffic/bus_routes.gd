class_name BusRoutes
extends RefCounted
## Every bus and green-minibus route that stops in a resident region, in the
## merged graph's frame (`P3-78`, `Q182`), off each region's `bus_routes.json`.
##
## 🔴 **The stops are the ETL's** (`etl/pipeline/busroutes.py`): which edge a stop
## stands on and which way a bus at it drives. The path between two stops is not
## published; `TrafficSystem` drives it with `RoadRouter.goal_tree`, the legal
## profile's own arcs.
##
## **The seam is joined here.** Which regions are resident is a fact about this
## run, so a route is every resident region's stops of one `key`, in `seq` order.
## Where a `seq` is missing the route left the map: it is split there into runs,
## each a `Route` of its own, so a bus never drives off the map and back between
## two stops it never drove past.

const GeneratedDocument = preload("res://scripts/city/generated_document.gd")

## Schema this understands, matching `BUS_ROUTES_SCHEMA` in `etl/pipeline/busroutes.py`.
const SCHEMA_VERSION: int = 1
const HOURS: int = 24


## One published stop.
class Stop:
	extends RefCounted

	var seq: int = 0
	var id: String = ""
	## The merged graph's edge, or -1: published unsnapped, or on an edge this
	## graph does not hold.
	var edge: int = -1
	var along: bool = true
	## Travel metres from the edge's entry end the way `along` drives it, to the
	## pole: where a bus's front stops.
	var travel_m: float = 0.0
	## The same point as a fraction of the edge from its start, for the router.
	var t: float = 0.0


## One run of a route direction: consecutive stops, none of them off the map.
class Route:
	extends RefCounted

	var key: String = ""
	var name: String = ""
	## The parked library's kind a vehicle on it is drawn as.
	var kind: String = ""
	## Departures in each hour of the published service day.
	var per_hour: PackedInt32Array = PackedInt32Array()
	var stops: Array[Stop] = []
	var regions: PackedStringArray = PackedStringArray()


## One `key` as it is read: the route's own fields once, off its first region,
## and every region's stops by `seq`.
class _Gathered:
	extends RefCounted

	var route := Route.new()
	var stops: Dictionary[int, Stop] = {}


var routes: Array[Route] = []
## Stops snapped in their region on an edge the merged graph does not hold.
var stops_dropped: int = 0
## Route directions split where they leave the map and come back.
var runs_split: int = 0


## Every region of `graph`'s routes over it. Empty where no region has any.
static func resident(graph: RoadGraph) -> BusRoutes:
	var found := BusRoutes.new()
	var by_key: Dictionary[String, _Gathered] = {}
	for region: String in graph.resident_regions():
		var manifest: CityManifest = CityManifest.shared(region)
		if manifest == null or manifest.bus_routes_path.is_empty():
			continue
		var document: Dictionary = GeneratedDocument.load_object(
			manifest.bus_routes_path, SCHEMA_VERSION, "tools/sync_generated.sh"
		)
		found._read_region(document, region, graph, by_key)
	var keys: Array = by_key.keys()
	keys.sort()
	for key: String in keys:
		found._split(by_key[key])
	return found


func is_empty() -> bool:
	return routes.is_empty()


## `region`'s rows into `by_key`: per key, the route's own fields once and its
## stops by `seq`.
func _read_region(
	document: Dictionary, region: String, graph: RoadGraph, by_key: Dictionary[String, _Gathered]
) -> void:
	var offset: Vector3 = graph.region_offset(region)
	for row: Dictionary in document.get("routes", []):
		var key: String = row["key"]
		if not by_key.has(key):
			var per_hour := PackedInt32Array()
			for count: Variant in row["per_hour"]:
				per_hour.append(int(count))
			var gathered := _Gathered.new()
			gathered.route.key = key
			gathered.route.name = String(row["name"])
			gathered.route.kind = String(row["kind"])
			gathered.route.per_hour = per_hour
			by_key[key] = gathered
		var entry: _Gathered = by_key[key]
		entry.route.regions.append(region)
		var stops: Dictionary[int, Stop] = entry.stops
		for published: Dictionary in row["stops"]:
			var stop := Stop.new()
			stop.seq = int(published["seq"])
			stop.id = String(published["stop_id"])
			var local: int = int(published["edge"])
			if local >= 0:
				stop.edge = graph.edge_id_in(region, local)
				if stop.edge < 0:
					stops_dropped += 1
				else:
					stop.along = bool(published["along"])
					var plan: Array = published["plan"]
					# Measured on the merged edge, not carried as `t`: a crossing
					# road is one edge across both regions.
					var point := Vector3(float(plan[0]), 0.0, float(plan[1])) + offset
					var length_m: float = graph.plan_length_of(stop.edge)
					var from_start: float = graph.distance_along(stop.edge, point)
					stop.t = from_start / length_m if length_m > 0.0 else 0.0
					stop.travel_m = from_start if stop.along else length_m - from_start
			stops[stop.seq] = stop


## One key's stops cut into runs of consecutive `seq`, each run with a stop on
## the graph kept.
func _split(entry: _Gathered) -> void:
	var stops: Dictionary[int, Stop] = entry.stops
	var seqs: Array = stops.keys()
	seqs.sort()
	var run: Array[Stop] = []
	var runs: int = 0
	for index: int in seqs.size():
		var seq: int = seqs[index]
		if not run.is_empty() and seq != run[-1].seq + 1:
			runs += int(_keep(entry, run))
			run = []
		run.append(stops[seq])
	runs += int(_keep(entry, run))
	if runs > 1:
		runs_split += 1


func _keep(entry: _Gathered, run: Array[Stop]) -> bool:
	if not run.any(func(stop: Stop) -> bool: return stop.edge >= 0):
		return false
	var route := Route.new()
	route.key = entry.route.key
	route.name = entry.route.name
	route.kind = entry.route.kind
	route.per_hour = entry.route.per_hour
	route.regions = entry.route.regions
	route.stops.assign(run)
	routes.append(route)
	return true
