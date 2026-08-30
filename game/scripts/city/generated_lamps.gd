## Where the ETL's lamp posts live, and how to load them.
##
## The eleventh of these, for the same reason as `generated_road_surface.gd`: two
## things want the lamps for different purposes — the preview draws them,
## `verify_lamps.gd` checks them — and a moved path that only one of them learns
## about fails silently in the other.
##
## ⚠️ **Optional, on the same terms as `generated_railings.gd`.** A city whose
## estate publishes no utility point layer ships none, and `city.json` names
## `null` rather than a path (`P3-26`). It is also absent where the block is
## declared and nothing survived the registration, because `pipeline/lamps.py`
## names its asset from what it drew rather than from a constant.
##
## ⚠️ **But "nothing survived" is a LESS ordinary answer here than for the
## signals**, and the difference is worth stating. `signals.glb` could vanish
## because `REFNAME` has no published domain and the gate is a rule about
## spelling; `UTILITYPOINTTYPE` **does** have a published domain, stored inside
## the geodatabase, so a region that draws no lamps has either declared no block
## or failed to find a kerb — not misread a vocabulary.
##
## Dev-only. `city.json` is what a shipped build reads and `CityManifest`
## (`P1-7`) resolves the path from it; this constant is what the preview scene
## and the verify tool use, and `verify_city.gd` asserts the two agree.
extends RefCounted

const PATH: String = "res://assets/generated/lamps.glb"


## The lamp posts as an instantiable scene, or null if they are not there.
static func load_lamps() -> PackedScene:
	return load(PATH) as PackedScene


## Whether the lamp asset is present at all.
##
## Separate from `load_lamps` returning null because the two answer different
## questions: this one is "did the build ship any lamp posts", which a region
## whose estate publishes none answers honestly with `false`.
static func is_present() -> bool:
	return ResourceLoader.exists(PATH)


## Message for the case that reads as "there are no lamps" rather than an error.
static func missing_hint() -> String:
	return (
		"No lamp posts at %s. Run the ETL and copy its output there:\n" % PATH
		+ "  python -m pipeline.lamps --region wan_chai\n"
		+ "  cp etl/out/<city>/<region>/lamps.glb game/assets/generated/\n"
		+ "A city whose sources publish no utility point layer ships none, and that is not a failure."
	)
