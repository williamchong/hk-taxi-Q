class_name SignalPlan
extends RefCounted
## Every resident region's signalled junctions, in the merged graph's ids and
## frame (`P3-3a`, `Q173`). What `SignalController` runs and the cars stop at.
##
## 🔴 **The junction is the ETL's and so is the stage each approach takes**
## (`etl/pipeline/signals.py`). Nothing here regroups them: a second grouping
## would be a second answer to which approaches share a green.

const GeneratedDocument = preload("res://scripts/city/generated_document.gd")
const GeneratedRegions = preload("res://scripts/city/generated_regions.gd")

## Schema this understands, matching `SIGNALS_PLAN_SCHEMA` in `etl/pipeline/signals.py`.
const SCHEMA_VERSION: int = 1


## One way into a junction.
class Approach:
	extends RefCounted

	var junction: int
	var edge: int
	## True where travel runs along the edge's own vertex order.
	var along: bool
	## Metres from the edge's START to the stop point, by plan length.
	var stop_m: float
	## Game heading of travel at the mouth, degrees: 0 is -z.
	var heading_deg: float
	var stage: int


## One signalled junction.
class Junction:
	extends RefCounted

	## The ETL's id: the junction's lowest node, in its own region's numbering.
	var id: int
	var region: String
	var position: Vector3
	## Vehicle stages in the cycle.
	var stages: int
	## True where every approach shares one axis: an all-red stage follows.
	var crossing: bool
	var approaches: Array[Approach] = []


var junctions: Array[Junction] = []
## Approaches by `key(edge, along)`.
var _by_way: Dictionary[int, Approach] = {}


## The way an approach is keyed: one edge, one direction.
static func key(edge: int, along: bool) -> int:
	return edge * 2 + (1 if along else 0)


## Every resident region's plan over `graph`. Empty where no region staged a
## junction: no car stops for a light, which is the honest answer.
static func resident(graph: RoadGraph) -> SignalPlan:
	var plan := SignalPlan.new()
	for region: String in GeneratedRegions.resident():
		var manifest: CityManifest = CityManifest.shared(region)
		if manifest == null or manifest.signals_plan_path.is_empty():
			continue
		var document: Dictionary = GeneratedDocument.load_object(
			manifest.signals_plan_path, SCHEMA_VERSION, "tools/sync_generated.sh"
		)
		plan.add_region(document, region, graph)
	return plan


## Add one region's document, its ids mapped into `graph` and its positions into
## the frame. An approach on an edge the graph does not hold is dropped with a
## warning: it would stop a car on nothing.
func add_region(document: Dictionary, region: String, graph: RoadGraph) -> void:
	var offset: Vector3 = graph.region_offset(region)
	for entry: Dictionary in document.get("junctions", []):
		var junction := Junction.new()
		junction.id = int(entry["id"])
		junction.region = region
		var pos: Array = entry["pos"]
		junction.position = Vector3(pos[0], pos[1], pos[2]) + offset
		junction.stages = int(entry["stages"])
		junction.crossing = bool(entry["crossing"])
		for row: Dictionary in entry.get("approaches", []):
			var edge: int = graph.edge_id_in(region, int(row["edge"]))
			if edge < 0:
				push_warning("SignalPlan: %s edge %d is not in the graph" % [region, row["edge"]])
				continue
			var approach := Approach.new()
			approach.junction = junctions.size()
			approach.edge = edge
			approach.along = bool(row["along"])
			approach.stop_m = float(row["stop_m"])
			approach.heading_deg = float(row["heading_deg"])
			approach.stage = int(row["stage"])
			junction.approaches.append(approach)
		if junction.approaches.is_empty():
			push_warning(
				"SignalPlan: %s junction %d kept no approach; dropped" % [region, junction.id]
			)
			continue
		for approach: Approach in junction.approaches:
			_by_way[key(approach.edge, approach.along)] = approach
		junctions.append(junction)


## The approach driving `edge` this way stops at, or null where none does.
func approach_on(edge: int, along: bool) -> Approach:
	return _by_way.get(key(edge, along), null)


func is_empty() -> bool:
	return junctions.is_empty()
