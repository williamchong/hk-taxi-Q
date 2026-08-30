## Where the ETL's road surface lives, and how to load it.
##
## The second of these, for the same reason as `generated_road_graph.gd`: two
## things want the surface for different purposes — the preview draws it,
## `verify_road_surface.gd` checks it — and a moved path that only one of them
## learns about fails silently in the other.
##
## Dev-only. `city.json` is what a shipped build reads and `CityManifest`
## (`P1-7`) resolves the path from it; this constant is what the preview scene
## and the verify tool use, and `verify_city.gd` asserts the two agree.
extends RefCounted

const PATH: String = "res://assets/generated/roads.glb"


## The surface as an instantiable scene, or null if it is not there.
static func load_surface() -> PackedScene:
	return load(PATH) as PackedScene


## Message for the case that reads as "there are no roads" rather than an error.
static func missing_hint() -> String:
	return (
		"No road surface at %s. Run the ETL and copy its output there:\n" % PATH
		+ "  python -m pipeline.surface --region wan_chai\n"
		+ "  cp etl/out/<city>/<region>/roads.glb game/assets/generated/"
	)
