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

const PATH: String = "res://assets/generated/roadgraph.json"

## Schema this understands. The data contract is versioned and the ETL bumps it
## on any change, so a mismatch is a stale copy rather than something to parse
## optimistically.
const SCHEMA_VERSION: int = 1


## The parsed graph, or null with a pushed error explaining which step failed.
static func load_graph() -> Dictionary:
	if not FileAccess.file_exists(PATH):
		push_warning(missing_hint())
		return {}

	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(PATH))
	if typeof(parsed) != TYPE_DICTIONARY:
		push_error("%s is not a JSON object" % PATH)
		return {}

	var graph: Dictionary = parsed
	var version: int = int(graph.get("schema_version", -1))
	if version != SCHEMA_VERSION:
		push_error(
			(
				"%s declares schema_version %d, this build reads %d. Re-run the ETL and re-copy."
				% [PATH, version, SCHEMA_VERSION]
			)
		)
		return {}
	return graph


## Message for the case that reads as "there are no roads" rather than an error.
static func missing_hint() -> String:
	return (
		"No road graph at %s. Run the ETL and copy its output there:\n" % PATH
		+ "  python -m pipeline.roads --city hong_kong --region wan_chai\n"
		+ "  cp etl/out/<city>/<region>/roadgraph.json game/assets/generated/"
	)
