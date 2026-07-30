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

const GeneratedDocument = preload("res://scripts/city/generated_document.gd")

const PATH: String = "res://assets/generated/fares.json"

## Schema this understands, matching `FARES_SCHEMA` in `etl/pipeline/fares.py`.
const SCHEMA_VERSION: int = 1

## `kind` values in the data contract. Spelled here rather than at each
## comparison so a rename in `ARCHITECTURE.md` has one place to land.
##
## ⚠️ These mirror `FARE_KINDS` in `etl/pipeline/config.py`, and nothing keeps
## the two in step. The ETL is authoritative — it is what writes the strings —
## so a change starts there and lands here.
const TAXI_STAND: String = "taxi_stand"
const PUDO: String = "pudo"
const POI: String = "poi"

## The `stand_category` the game treats specially — `docs/GAME_DESIGN.md` makes
## it the premium fare. Every other category is an ordinary stand.
const CROSS_HARBOUR: String = "cross_harbour"


## The parsed fare nodes, or an empty dictionary with a pushed message.
static func load_fares() -> Dictionary:
	return GeneratedDocument.load_object(PATH, SCHEMA_VERSION, missing_hint())


## Message for the case that reads as "there are no fares" rather than an error.
static func missing_hint() -> String:
	return (
		"No fare nodes at %s. Run the ETL and copy its output there:\n" % PATH
		+ "  python -m pipeline.fares --city hong_kong --region wan_chai\n"
		+ "  cp etl/out/<city>/<region>/fares.json game/assets/generated/"
	)
