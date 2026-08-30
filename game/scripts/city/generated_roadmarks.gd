## Where the ETL's stop and give-way lines live, and how to load them.
##
## The ninth of these, for the same reason as `generated_road_surface.gd`: two
## things want the markings for different purposes — the preview draws them,
## `verify_roadmarks.gd` checks them — and a moved path that only one of them
## learns about fails silently in the other.
##
## ⚠️ **Optional, on the same terms as `generated_boxjunctions.gd`.** A city
## whose estate publishes no transverse markings ships none, and `city.json`
## names `null` rather than a path (`P3-23`). It is also absent where the block
## is declared and every marking failed the transverse join, because
## `pipeline/roadmarks.py` names its asset from what it drew rather than from a
## constant. So absence is a state to report, not a failure to warn about.
##
## Dev-only. `city.json` is what a shipped build reads and `CityManifest`
## (`P1-7`) resolves the path from it; this constant is what the preview scene
## and the verify tool use, and `verify_city.gd` asserts the two agree.
extends RefCounted

const PATH: String = "res://assets/generated/roadmarks.glb"


## The road markings as an instantiable scene, or null if they are not there.
static func load_roadmarks() -> PackedScene:
	return load(PATH) as PackedScene


## Whether the road-marking asset is present at all.
##
## Separate from `load_roadmarks` returning null because the two answer different
## questions: this one is "did the build ship any stop lines", which a region
## whose estate publishes none answers honestly with `false`.
static func is_present() -> bool:
	return ResourceLoader.exists(PATH)


## Message for the case that reads as "there are no markings" rather than an error.
static func missing_hint() -> String:
	return (
		"No road markings at %s. Run the ETL and copy its output there:\n" % PATH
		+ "  python -m pipeline.roadmarks --region wan_chai\n"
		+ "  cp etl/out/<city>/<region>/roadmarks.glb game/assets/generated/\n"
		+ "A city whose sources publish no transverse markings ships none, and that is not a failure."
	)
