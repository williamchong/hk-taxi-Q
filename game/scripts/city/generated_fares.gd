## Where the ETL's fare nodes live, and how to read them.
##
## The third of these, for the same reason as `generated_road_graph.gd` and
## `generated_layer.gd`: two things will want the fare nodes for
## different purposes — the preview draws them, `FareSystem` (`P3-1`) will hail
## from them — and a moved path that only one of them learns about fails
## silently in the other.
##
## Dev-only. `city.json` is what a shipped build reads and `CityManifest`
## (`P1-7`) resolves the path from it; this constant is what the preview scene
## uses, and `verify_city.gd` asserts the two name the same file.
extends RefCounted

const GeneratedDocument = preload("res://scripts/city/generated_document.gd")
const GeneratedRegions = preload("res://scripts/city/generated_regions.gd")

const FILE: String = "fares.json"

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


## Where a region's copy is; `GeneratedRegions.selected()` for "".
static func path(region: String = "") -> String:
	return GeneratedRegions.dir(region) + FILE


## The parsed fare nodes, or an empty dictionary with a pushed message.
##
## `at` is the path a manifest resolved (`CityManifest.fares_path`); "" is
## `path()`, for callers that hold no manifest.
static func load_fares(at: String = "") -> Dictionary:
	var resolved: String = at if not at.is_empty() else path()
	return GeneratedDocument.load_object(resolved, SCHEMA_VERSION, missing_hint(resolved))


## The node with this id, or an empty dictionary.
##
## Here rather than in a consumer because this file is the one place that knows
## the fares document's shape — the `nodes` array and the `id` and `pos` keys are
## as much its business as `FILE` and the `kind` spellings above.
static func node_by_id(fares: Dictionary, fare_id: String) -> Dictionary:
	for node: Dictionary in fares.get("nodes", []) as Array:
		if String(node.get("id", "")) == fare_id:
			return node
	return {}


## A node's published position, or `null` where it has none.
##
## Null rather than `Vector3.ZERO`, because the region's own origin is a real
## place a car could be put: a malformed node would otherwise resolve to a street
## near the north-west corner and look like a successful lookup.
static func position_of(node: Dictionary) -> Variant:
	var values: Array = node.get("pos", []) if node.get("pos") is Array else []
	if values.size() < 3:
		return null
	return Vector3(values[0], values[1], values[2])


## Message for the case that reads as "there are no fares" rather than an error.
## The message for a document missing at `at` — the path a caller actually
## tried, since a manifest may have resolved another region's — or at `path()`.
## ⚠️ Every resident region is synced in one call: `sync_generated.sh` with one
## region as its only argument deletes the other.
static func missing_hint(at: String = "") -> String:
	return (
		(
			"No fare nodes at %s. Run the ETL and copy its output there:\n"
			% (at if not at.is_empty() else path())
		)
		+ "  python -m pipeline.fares --region wan_chai\n"
		+ "  tools/sync_generated.sh wan_chai causeway_bay"
	)
