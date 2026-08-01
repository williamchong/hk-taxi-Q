## Where the ETL's road graph lives, and how to read it.
##
## One definition, because two things want the graph for different purposes —
## the preview draws it, `RoadGraph` (`P2-2`) will query it — and a moved path
## that only one of them learns about fails silently in the other.
##
## Dev-only. `city.json` is what a shipped build reads and `CityManifest`
## (`P1-7`) resolves the path from it; this constant is what the preview scene
## uses, and `verify_city.gd` asserts the two name the same file.
extends RefCounted

const GeneratedDocument = preload("res://scripts/city/generated_document.gd")

const PATH: String = "res://assets/generated/roadgraph.json"

## Schema this understands, matching `ROADGRAPH_SCHEMA` in
## `etl/pipeline/roads.py`.
##
## 2 since `P2-7`: an off-grade polyline's `y` now follows the structure the
## road is built on rather than sitting at one flat offset per elevation level.
## The shape of the document did not change, which is why this had to — a reader
## cannot tell a sampled deck from an invented one by looking.
const SCHEMA_VERSION: int = 2


## The parsed graph, or an empty dictionary with a pushed message.
static func load_graph() -> Dictionary:
	return GeneratedDocument.load_object(PATH, SCHEMA_VERSION, missing_hint())


## Message for the case that reads as "there are no roads" rather than an error.
static func missing_hint() -> String:
	return (
		"No road graph at %s. Run the ETL and copy its output there:\n" % PATH
		+ "  python -m pipeline.roads --city hong_kong --region wan_chai\n"
		+ "  cp etl/out/<city>/<region>/roadgraph.json game/assets/generated/"
	)
