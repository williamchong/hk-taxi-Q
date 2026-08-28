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
##
## 3 since `Q23`, and this one adds a field: `on_structure`, one flag per vertex
## of `polyline`. `elevation_level` says which deck an edge belongs to; this says
## which of its stations are standing on one, because a road becomes a bridge
## partway along an edge rather than at an edge boundary.
##
## 4 since `P3-13`, and it adds a field for the same reason: `kerbside`, the runs
## of each edge that a published no-stopping restriction covers, per side and
## measured along `polyline`. Nothing here draws them — the marking shader reads
## the extent off the road mesh — but `P3-3`'s traffic and `P3-9a`'s fares both
## want to know where a car may not stop, and that is a fact about the graph.
##
## 5 since `Q95`, and it bumps because a reader would be *wrong* to keep its old
## interpretation rather than merely see different bytes. `width_m` used to be
## `lanes x lane_width_m` on every edge — an identity a consumer could invert to
## recover a lane count — and on the edges two publishers span it is now a
## measured carriageway, so that inversion silently returns a number the graph
## never claimed. The new `width_source` says which of the two a given edge
## carries; `lanes` itself is untouched and still authored.
const SCHEMA_VERSION: int = 5


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
