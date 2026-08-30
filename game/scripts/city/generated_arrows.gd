## Where the ETL's turn arrows live, and how to load them.
##
## The sixth of these, for the same reason as `generated_road_surface.gd`: two
## things want the arrows for different purposes — the preview draws them,
## `verify_arrows.gd` checks them — and a moved path that only one of them learns
## about fails silently in the other.
##
## ⚠️ **Optional, on the same terms as `generated_tramway.gd`.** A city whose
## estate publishes no marking symbols ships none, and `city.json` names `null`
## rather than a path (`P3-15`). It is also absent where the block is declared
## and every symbol failed the join, because `pipeline/arrows.py` names its asset
## from what it drew rather than from a constant. So absence is a state to
## report, not a failure to push a warning about.
##
## Dev-only. `city.json` is what a shipped build reads and `CityManifest`
## (`P1-7`) resolves the path from it; this constant is what the preview scene
## and the verify tool use, and `verify_city.gd` asserts the two agree.
extends RefCounted

const PATH: String = "res://assets/generated/arrows.glb"


## The arrows as an instantiable scene, or null if they are not there.
static func load_arrows() -> PackedScene:
	return load(PATH) as PackedScene


## Whether the arrows asset is present at all.
##
## Separate from `load_arrows` returning null because the two answer different
## questions: this one is "did the build ship any turn arrows", which a region
## whose estate publishes none answers honestly with `false`.
static func is_present() -> bool:
	return ResourceLoader.exists(PATH)


## Message for the case that reads as "there are no arrows" rather than an error.
static func missing_hint() -> String:
	return (
		"No turn arrows at %s. Run the ETL and copy its output there:\n" % PATH
		+ "  python -m pipeline.arrows --region wan_chai\n"
		+ "  cp etl/out/<city>/<region>/arrows.glb game/assets/generated/\n"
		+ "A city whose sources publish no marking symbols ships none, and that is not a failure."
	)
