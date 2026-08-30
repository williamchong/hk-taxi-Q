## Where the ETL's yellow box junctions live, and how to load them.
##
## The seventh of these, for the same reason as `generated_road_surface.gd`: two
## things want the boxes for different purposes — the preview draws them,
## `verify_boxjunctions.gd` checks them — and a moved path that only one of them
## learns about fails silently in the other.
##
## ⚠️ **Optional, on the same terms as `generated_arrows.gd`.** A city whose
## estate publishes no box polygons ships none, and `city.json` names `null`
## rather than a path (`P3-18`). It is also absent where the block is declared
## and every box failed the join, because `pipeline/boxjunctions.py` names its
## asset from what it drew rather than from a constant. So absence is a state to
## report, not a failure to push a warning about.
##
## Dev-only. `city.json` is what a shipped build reads and `CityManifest`
## (`P1-7`) resolves the path from it; this constant is what the preview scene
## and the verify tool use, and `verify_city.gd` asserts the two agree.
extends RefCounted

const PATH: String = "res://assets/generated/boxjunctions.glb"


## The box junctions as an instantiable scene, or null if they are not there.
static func load_boxjunctions() -> PackedScene:
	return load(PATH) as PackedScene


## Whether the box-junction asset is present at all.
##
## Separate from `load_boxjunctions` returning null because the two answer
## different questions: this one is "did the build ship any box junctions",
## which a region whose estate publishes none answers honestly with `false`.
static func is_present() -> bool:
	return ResourceLoader.exists(PATH)


## Message for the case that reads as "there are no boxes" rather than an error.
static func missing_hint() -> String:
	return (
		"No box junctions at %s. Run the ETL and copy its output there:\n" % PATH
		+ "  python -m pipeline.boxjunctions --region wan_chai\n"
		+ "  cp etl/out/<city>/<region>/boxjunctions.glb game/assets/generated/\n"
		+ "A city whose sources publish no box polygons ships none, and that is not a failure."
	)
