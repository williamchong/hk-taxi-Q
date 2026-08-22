## Where the ETL's traffic signs live, and how to load them.
##
## The seventh of these, for the same reason as `generated_road_surface.gd`: two
## things want the signs for different purposes — the preview draws them,
## `verify_signs.gd` checks them — and a moved path that only one of them learns
## about fails silently in the other.
##
## ⚠️ **Optional, on the same terms as `generated_tramway.gd`.** A city whose
## estate publishes no sign layer ships none, and `city.json` names `null` rather
## than a path (`P3-16`). It is also absent where the block is declared and
## nothing survived the join, because `pipeline/signs.py` names its asset from
## what it drew rather than from a constant.
##
## ⚠️ **And null is an ordinary answer here, more than for any other layer.**
## `P3-16` ships only the signs whose meaning is their *shape*: 2,364 of Wan
## Chai's 3,276 are text-faced and refused outright under `Q42` and hard rule 8.
## A region whose signs are all time plates and parking legends draws none and is
## correct to. So absence is a state to report, not a failure to warn about.
##
## Dev-only. `city.json` is what a shipped build reads and `CityManifest`
## (`P1-7`) resolves the path from it; this constant is what the preview scene
## and the verify tool use, and `verify_city.gd` asserts the two agree.
extends RefCounted

const PATH: String = "res://assets/generated/signs.glb"


## The signs as an instantiable scene, or null if they are not there.
static func load_signs() -> PackedScene:
	return load(PATH) as PackedScene


## Whether the signs asset is present at all.
##
## Separate from `load_signs` returning null because the two answer different
## questions: this one is "did the build ship any traffic signs", which a region
## whose estate publishes none answers honestly with `false`.
static func is_present() -> bool:
	return ResourceLoader.exists(PATH)


## Message for the case that reads as "there are no signs" rather than an error.
static func missing_hint() -> String:
	return (
		"No traffic signs at %s. Run the ETL and copy its output there:\n" % PATH
		+ "  python -m pipeline.signs --city hong_kong --region wan_chai\n"
		+ "  cp etl/out/<city>/<region>/signs.glb game/assets/generated/\n"
		+ "A city whose sources publish no shape-faced signs ships none, and that is not a failure."
	)
