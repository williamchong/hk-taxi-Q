## Where the ETL's fare nodes live, and how to read them.
##
## The fourth of these, for the same reason as `generated_tiles.gd`,
## `generated_road_graph.gd` and `generated_road_surface.gd`: two things will
## want the fare nodes for different purposes — the preview draws them,
## `FareSystem` (`P3-1`) will hail from them — and a moved path that only one of
## them learns about fails silently in the other.
##
## Dev-only for now. `P1-6` writes `city.json`, which is what a shipped build
## reads; this reads `P1-5`'s stage output directly so the nodes can be looked at
## before either of those exists.
extends RefCounted

const PATH: String = "res://assets/generated/fares.json"

## Schema this understands. The data contract is versioned and the ETL bumps it
## on any change, so a mismatch is a stale copy rather than something to parse
## optimistically.
const SCHEMA_VERSION: int = 1

## `kind` values in the data contract. Spelled here rather than at each
## comparison so a rename in `ARCHITECTURE.md` has one place to land.
const TAXI_STAND: String = "taxi_stand"
const PUDO: String = "pudo"
const POI: String = "poi"

## The `stand_category` the game treats specially — `docs/GAME_DESIGN.md` makes
## it the premium fare. Every other category is an ordinary stand.
const CROSS_HARBOUR: String = "cross_harbour"


## The parsed fare nodes, or an empty dictionary with a pushed message.
static func load_fares() -> Dictionary:
	if not FileAccess.file_exists(PATH):
		push_warning(missing_hint())
		return {}

	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(PATH))
	if typeof(parsed) != TYPE_DICTIONARY:
		push_error("%s is not a JSON object" % PATH)
		return {}

	var fares: Dictionary = parsed
	var version: int = int(fares.get("schema_version", -1))
	if version != SCHEMA_VERSION:
		push_error(
			(
				"%s declares schema_version %d, this build reads %d. Re-run the ETL and re-copy."
				% [PATH, version, SCHEMA_VERSION]
			)
		)
		return {}
	return fares


## Message for the case that reads as "there are no fares" rather than an error.
static func missing_hint() -> String:
	return (
		"No fare nodes at %s. Run the ETL and copy its output there:\n" % PATH
		+ "  python -m pipeline.fares --city hong_kong --region wan_chai\n"
		+ "  cp etl/out/<city>/<region>/fares.json game/assets/generated/"
	)
