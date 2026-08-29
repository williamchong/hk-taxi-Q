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
##
## 6 since `Q94`, and it is 5's last clause coming due: `lanes` is no longer
## untouched. Where the measured `width_m` resolves under TPDM 4.3.9.8's
## 3.0-3.65 m through-lane range, the count is a *reading* rather than authored
## policy keyed on the speed limit, and a consumer treating every one as policy
## would be **wrong**. `lanes_source` says which of `authored`, `measured`,
## `floored` or `arrows` an edge carries — `arrows` being a row of turn arrows
## across the carriageway settling a bracket TD's range left ambiguous.
## ⚠️ **It is a strict subset of the measured widths** — what neither the range
## nor a row resolves keeps the authored count — so a measured `width_source`
## beside an authored `lanes_source` is still an ordinary measured edge rather
## than a contradiction.
##
## 7 since `Q94` adds `width_publisher`, and it bumps because 6 shipped a claim
## that had quietly stopped being true. Through 5 every measured `width_m` was
## kerb-to-kerb, read off a line publisher. 6's third publisher draws the
## maintained carriageway as an *area* and carves traffic islands, run-ins and
## car parks out of it, so where it answered `width_m` is the **trafficable**
## surface instead — p10 -3.39 m apart across this region. A reader treating
## every measured width as one population is wrong, and this is the field that
## lets it not. ⚠️ Empty where the width is authored.
##
## 8 since `Q19`, and it adds `structure_bounded`, one flag per vertex beside
## `on_structure`. That flag says where a station's *height* came from; this says
## whether structure stands *beside* it at the height a bumper meets. They
## coincide on a viaduct and come apart on its approach ramp, which is the
## population that blocks: `e233`, `e55` and `e398` report every station off
## structure while being walled along most of their length, so the surface stage
## drew them 10.24-12.48 m wide between walls 3.8 m apart. Nothing here can
## recover it — not `y`, not `elevation_level`, not `width_m` — so a reader that
## keeps taking `on_structure` for "is this carriageway bounded" is **wrong**
## about the whole Wan Chai Interchange.
const SCHEMA_VERSION: int = 8


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
