## Where the ETL's road graph lives, and how to read it.
##
## The counterpart of `generated_tiles.gd`, and separate from it for the same
## reason: two things will want the graph for different purposes — the preview
## draws it, `RoadGraph` (`P2-2`) will query it — and a moved path that only one
## of them learns about fails silently in the other.
##
## Dev-only for now. `P1-6` writes `city.json`, which is what a shipped build
## reads; this reads `P1-3`'s stage output directly so the graph can be looked at
## before either of those exists.
extends RefCounted

const GeneratedDocument = preload("res://scripts/city/generated_document.gd")

const PATH: String = "res://assets/generated/roadgraph.json"

## Schema this understands, matching `ROADGRAPH_SCHEMA` in
## `etl/pipeline/roads.py`.
const SCHEMA_VERSION: int = 1


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
