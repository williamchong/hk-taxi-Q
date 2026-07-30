## Where the ETL's road surface lives, and how to load it.
##
## The third of these, for the same reason as `generated_tiles.gd` and
## `generated_road_graph.gd`: two things want the surface for different
## purposes — the preview draws it, `verify_road_surface.gd` checks it — and a
## moved path that only one of them learns about fails silently in the other.
##
## Dev-only for now. `P1-6` writes `city.json`, which is what a shipped build
## reads; this points at `P1-4`'s stage output directly so the surface can be
## driven and checked before either of those exists.
extends RefCounted

const PATH: String = "res://assets/generated/roads.glb"


## The surface as an instantiable scene, or null if it is not there.
static func load_surface() -> PackedScene:
	return load(PATH) as PackedScene


## Message for the case that reads as "there are no roads" rather than an error.
static func missing_hint() -> String:
	return (
		"No road surface at %s. Run the ETL and copy its output there:\n" % PATH
		+ "  python -m pipeline.surface --city hong_kong --region wan_chai\n"
		+ "  cp etl/out/<city>/<region>/roads.glb game/assets/generated/"
	)
