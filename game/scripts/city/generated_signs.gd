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
## Chai's 3,276 are text-faced and refused outright under the zero-texture rule.
## A region whose signs are all time plates and parking legends draws none and is
## correct to. So absence is a state to report, not a failure to warn about.
##
## Dev-only. `city.json` is what a shipped build reads and `CityManifest`
## (`P1-7`) resolves the path from it; this constant is what the preview scene
## and the verify tool use, and `verify_city.gd` asserts the two agree.
extends RefCounted

const PATH: String = "res://assets/generated/signs.glb"

## The mesh carrying the lettering, if this region's faces have any (`P3-20`).
##
## Named here rather than in `verify_signs.gd` for this file's own reason: the
## preview scene and the verify tool both have to agree on what a second
## primitive in `signs.glb` *is*, and a name learned by only one of them is the
## silent failure this file exists to prevent. Mirrors `SIGNS_TEXT_MESH_NAME` in
## `etl/pipeline/signs.py`.
const TEXT_MESH: String = "signs_text"

## 🔴 **The pixel budget this layer declares, and the reason it may have an image
## at all** (`Q63`, `P3-20`).
##
## `mesh_contract.gd` refuses every undeclared texture in the bundle. A call site
## that passes a budget is declaring one *on purpose, in a diff*, and buys a
## ceiling with it — the shipped atlas is measured against this number and fails
## above it, and a declared texture that never arrived fails too.
##
## ⚠️ **This is 256 x 256: one square cell for the one face with words on it.**
## `text_cell_px` in `hong_kong.yaml` is the other half, `signs.json` publishes
## what actually shipped as `text_atlas_px`, and `PROGRESS.md` quotes it as
## `Texture memory`. Three numbers that must move together, which is the cost
## `Q63` accepted in exchange for the check staying a check.
##
## ⚠️ **Raise it only for lettering that is going to ship.** A generous budget is
## a budget nothing reads, which is precisely what `Q63` refused when it declined
## to simply delete the rule.
const TEXT_ATLAS_BUDGET_PX: int = 256 * 256


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
