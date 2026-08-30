## Where the ETL's tramway lives, and how to load it.
##
## The fifth of these, for the same reason as `generated_road_surface.gd`: two
## things want the tramway for different purposes — the preview draws it,
## `verify_tramway.gd` checks it — and a moved path that only one of them learns
## about fails silently in the other.
##
## ⚠️ **Unlike the other four, this one may legitimately not be there.** A city
## whose estate publishes no tramway ships none, and `city.json` names `null`
## rather than a path (`P3-14`). So absence is a state to report, not a failure
## to push a warning about — which is why `missing_hint` is only ever used by a
## caller that already knows the manifest named an asset.
##
## Dev-only. `city.json` is what a shipped build reads and `CityManifest`
## (`P1-7`) resolves the path from it; this constant is what the preview scene
## and the verify tool use, and `verify_city.gd` asserts the two agree.
extends RefCounted

const PATH: String = "res://assets/generated/tram.glb"


## The tramway as an instantiable scene, or null if it is not there.
static func load_tramway() -> PackedScene:
	return load(PATH) as PackedScene


## Whether the tramway asset is present at all.
##
## Separate from `load_tramway` returning null because the two answer different
## questions: this one is "did the build ship a tramway", which a region without
## one answers honestly with `false`.
static func is_present() -> bool:
	return ResourceLoader.exists(PATH)


## Message for the case that reads as "there is no tramway" rather than an error.
static func missing_hint() -> String:
	return (
		"No tramway at %s. Run the ETL and copy its output there:\n" % PATH
		+ "  python -m pipeline.tramway --region wan_chai\n"
		+ "  cp etl/out/<city>/<region>/tram.glb game/assets/generated/\n"
		+ "A city whose sources publish no tramway ships none, and that is not a failure."
	)
