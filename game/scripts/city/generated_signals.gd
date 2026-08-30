## Where the ETL's traffic signal heads live, and how to load them.
##
## The tenth of these, for the same reason as `generated_road_surface.gd`: two
## things want the signals for different purposes — the preview draws them,
## `verify_signals.gd` checks them — and a moved path that only one of them
## learns about fails silently in the other.
##
## ⚠️ **Optional, on the same terms as `generated_roadmarks.gd`.** A city whose
## estate publishes no signal layer ships none, and `city.json` names `null`
## rather than a path (`P3-17`). It is also absent where the block is declared
## and nothing survived the gate, because `pipeline/signals.py` names its asset
## from what it drew rather than from a constant.
##
## ⚠️ **And "nothing survived the gate" is a more ordinary answer here than for
## any other layer.** `DTAD_TRAFFIC_LIGHT_PT.REFNAME` has no published domain —
## no index-plan sheet defines it — so what admits a code is a rule about
## *spelling* that this project wrote. A city whose publisher numbers its heads
## differently draws none and is correct to; `signals.json`'s `refused_by_code`
## is where that shows up. So absence is a state to report, not a failure to
## warn about.
##
## Dev-only. `city.json` is what a shipped build reads and `CityManifest`
## (`P1-7`) resolves the path from it; this constant is what the preview scene
## and the verify tool use, and `verify_city.gd` asserts the two agree.
extends RefCounted

const PATH: String = "res://assets/generated/signals.glb"


## The signal heads as an instantiable scene, or null if they are not there.
static func load_signals() -> PackedScene:
	return load(PATH) as PackedScene


## Whether the signal asset is present at all.
##
## Separate from `load_signals` returning null because the two answer different
## questions: this one is "did the build ship any signal heads", which a region
## whose estate publishes none answers honestly with `false`.
static func is_present() -> bool:
	return ResourceLoader.exists(PATH)


## Message for the case that reads as "there are no signals" rather than an error.
static func missing_hint() -> String:
	return (
		"No signal heads at %s. Run the ETL and copy its output there:\n" % PATH
		+ "  python -m pipeline.signals --region wan_chai\n"
		+ "  cp etl/out/<city>/<region>/signals.glb game/assets/generated/\n"
		+ "A city whose sources publish no signal layer ships none, and that is not a failure."
	)
