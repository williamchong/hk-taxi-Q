## Where the ETL's one-mesh layers live, and how to load them (`P5-1`).
##
## One table for the nine `.glb` layers that ship as a single mesh per region,
## replacing a file each. Every one of those files carried the same three
## functions and the same reason for existing: two things want a layer for
## different purposes — the preview draws it, its verify tool checks it — and a
## path that only one of them learns about fails silently in the other. That
## reason is unchanged; what changed is that nine copies of it had drifted only
## in their comments, and a tenth layer would have been a tenth copy.
##
## Dev-only. `city.json` is what a shipped build reads and `CityManifest`
## (`P1-7`) resolves each path from it; this table is what the preview scene and
## the verify tools use, and `verify_city.gd` asserts the two agree per layer.
##
## ⚠️ **Optional is a property of the LAYER, not of the file being there.** The
## road surface is required — nothing under the start line means the build went
## wrong — and every other row is optional: a city whose estate publishes no
## tramway, marking symbols, box polygons, transverse markings, signal layer,
## railing layer, utility point layer or shape-faced signs ships none, `city.json`
## names `null` rather than a path, and absence is a state to report rather than a
## failure to warn about. Each stage also names its asset from what it *drew*, so
## a declared block that survives no join ships nothing too. A row's `absence`
## sentence is what says so, and an empty one is what makes the layer required.
##
## ⚠️ **Some absences are more ordinary than others, and the distinction is kept
## here rather than lost in the merge.** Signs: 2,364 of Wan Chai's 3,276 are
## text-faced and refused under the no-texture rule, so a region whose signs are
## all time plates draws none and is correct to (`P3-16`). Signals: `REFNAME` has
## no published domain, so what admits a head is a rule about *spelling* this
## project wrote, and a publisher who numbers heads differently draws none
## (`P3-17`). Lamps are the opposite: `UTILITYPOINTTYPE` **has** a published
## domain, so a region drawing none has declared no block or failed to find a
## kerb, never misread a vocabulary (`P3-26`). `verify_city.gd` carries the same
## three notes at its guards.
##
## ⚠️ **`is_present` and `load_layer` returning null answer different
## questions.** The first is "did the build ship this layer", which an optional
## layer answers honestly with `false`; the second is "it is there and did not
## load", which is a failure. Every caller keeps them apart for that reason —
## and asks them in that order, for `Q77`'s reason on `is_present`.
extends RefCounted

## The mesh carrying the sign lettering, if this region's faces have any
## (`P3-20`). Named here rather than in `verify_signs.gd` for this file's own
## reason: the preview scene and the verify tool both have to agree on what a
## second primitive in `signs.glb` *is*, and a name learned by only one of them
## is the silent failure this file exists to prevent. Mirrors
## `SIGNS_TEXT_MESH_NAME` in `etl/pipeline/signs.py`.
const SIGNS_TEXT_MESH: String = "signs_text"

## 🔴 **The pixel budget the sign layer declares, and the reason it may have an
## image at all** (`Q63`, `P3-20`).
##
## `mesh_contract.gd` refuses every undeclared texture in the bundle. A call site
## that passes a budget is declaring one *on purpose, in a diff*, and buys a
## ceiling with it — the shipped atlas is measured against this number and fails
## above it, and a declared texture that never arrived fails too.
##
## ⚠️ **This is 512 x 256: one square cell for each of the TWO faces with words
## on them**, laid in a row — `TS102`'s GIVE WAY / 讓 and `TS101`'s STOP / 停.
## `text_cell_px` in `hong_kong.yaml` is the other half, `signs.json` publishes
## what actually shipped as `text_atlas_px`, and `PROGRESS.md` quotes it as
## `Texture memory`. Three numbers that must move together, which is the cost
## `Q63` accepted in exchange for the check staying a check.
##
## ⚠️ **Raise it only for lettering that is going to ship.** A generous budget is
## a budget nothing reads, which is precisely what `Q63` refused when it declined
## to simply delete the rule. It went 256 x 256 -> 512 x 256 in the commit that
## added the second cell, and neither half of that is optional: a budget raised
## ahead of the lettering is slack, and lettering added ahead of the budget
## fails the build. That is the check working.
const SIGNS_TEXT_ATLAS_BUDGET_PX: int = 512 * 256

const _ROOT: String = "res://assets/generated/"

## The layer ids. Code callers pass these and never the bare string, so a
## misspelt layer fails to parse — which `check.sh` catches — instead of
## reading as "none shipped for this region", which it does not: `_row` pushes
## an error and returns nothing, `is_present` then answers `false`, and a verify
## tool's skip branch exits 0. The `.tscn` nodes carry the same strings by hand
## because an exported `String` is what a scene can store; `verify_city.gd`
## checks those against `ids()`.
const ROAD_SURFACE: String = "road_surface"
const TRAMWAY: String = "tramway"
const ARROWS: String = "arrows"
const BOXJUNCTIONS: String = "boxjunctions"
const ROADMARKS: String = "roadmarks"
const SIGNALS: String = "signals"
const RAILINGS: String = "railings"
const LAMPS: String = "lamps"
const SIGNS: String = "signs"

## One row per layer. `file` is the asset under `assets/generated/`; `noun` and
## `module` build the rebuild hint and the verify tools' skip line; `absence` is
## the sentence that makes the layer optional, and is empty for the one layer
## that is not; `placements` names the document that stands a PROP layer's
## library meshes in the world (`P5-2`), and is empty for a layer that ships
## merged. Every row carries every key, and the accessors index rather than
## `get`, so a row missing one fails loudly instead of defaulting.
const LAYERS: Dictionary[String, Dictionary] = {
	ROAD_SURFACE:
	{
		"file": "roads.glb",
		"noun": "road surface",
		"module": "surface",
		"absence": "",
		"placements": "",
	},
	TRAMWAY:
	{
		"file": "tram.glb",
		"noun": "tramway",
		"module": "tramway",
		"absence": "A city whose sources publish no tramway ships none, and that is not a failure.",
		"placements": "",
	},
	ARROWS:
	{
		"file": "arrows.glb",
		"noun": "turn arrows",
		"module": "arrows",
		"absence":
		"A city whose sources publish no marking symbols ships none, and that is not a failure.",
		"placements": "arrows_placements.json",
	},
	BOXJUNCTIONS:
	{
		"file": "boxjunctions.glb",
		"noun": "box junctions",
		"module": "boxjunctions",
		"absence":
		"A city whose sources publish no box polygons ships none, and that is not a failure.",
		"placements": "",
	},
	ROADMARKS:
	{
		"file": "roadmarks.glb",
		"noun": "road markings",
		"module": "roadmarks",
		"absence":
		"A city whose sources publish no transverse markings ships none, and that is not a failure.",
		"placements": "",
	},
	SIGNALS:
	{
		"file": "signals.glb",
		"noun": "signal heads",
		"module": "signals",
		"absence":
		"A city whose sources publish no signal layer ships none, and that is not a failure.",
		"placements": "",
	},
	RAILINGS:
	{
		"file": "railings.glb",
		"noun": "railings",
		"module": "railings",
		"absence":
		"A city whose sources publish no railing layer ships none, and that is not a failure.",
		"placements": "",
	},
	LAMPS:
	{
		"file": "lamps.glb",
		"noun": "lamp posts",
		"module": "lamps",
		"absence":
		"A city whose sources publish no utility point layer ships none, and that is not a failure.",
		"placements": "lamps_placements.json",
	},
	SIGNS:
	{
		"file": "signs.glb",
		"noun": "traffic signs",
		"module": "signs",
		"absence":
		"A city whose sources publish no shape-faced signs ships none, and that is not a failure.",
		"placements": "signs_placements.json",
	},
}


## Every layer id, in table order — what `verify_city.gd` holds the two dev
## scenes' `layer_preview` nodes against, in both directions.
static func ids() -> PackedStringArray:
	return PackedStringArray(LAYERS.keys())


## The asset's `res://` path, or "" for an id the table does not know — which
## is pushed as an error rather than returned quietly, because a typo here is
## exactly the silently-diverged path this file exists to prevent.
static func path(layer: String) -> String:
	var row: Dictionary = _row(layer)
	return "" if row.is_empty() else _ROOT + String(row["file"])


## What the layer is called in a message: "lamp posts", "traffic signs".
static func noun(layer: String) -> String:
	var row: Dictionary = _row(layer)
	return layer if row.is_empty() else String(row["noun"])


## Whether a missing asset is an ordinary answer for this layer.
static func is_optional(layer: String) -> bool:
	var row: Dictionary = _row(layer)
	return not row.is_empty() and not String(row["absence"]).is_empty()


## Whether the asset is present at all — "did the build ship this layer".
##
## 🔴 **Ask this BEFORE `load_layer`, and do not "simplify" the pair back to
## one call.** `load()` on an absent path writes `ERROR: No loader found for
## resource` to the console *before* it returns null, so a graceful branch on
## the null runs after the damage is done. `Q77` dropped the signal layer and
## that error then shipped in the web build — into the console `P3-9a` tells
## testers to read, under a row claiming 0 errors.
static func is_present(layer: String) -> bool:
	var at: String = path(layer)
	return not at.is_empty() and ResourceLoader.exists(at)


## The layer as an instantiable scene, or null if it did not load. Present but
## unloadable is not the same as absent — reporting it as "none shipped" would
## describe a broken asset as an empty region — so callers ask `is_present`
## first and treat a null here as a failure.
static func load_layer(layer: String) -> PackedScene:
	var at: String = path(layer)
	return null if at.is_empty() else load(at) as PackedScene


## The document standing a prop layer's library in the world, or "" for a
## layer that ships merged.
static func placements_path(layer: String) -> String:
	var row: Dictionary = _row(layer)
	if row.is_empty() or String(row["placements"]).is_empty():
		return ""
	return _ROOT + String(row["placements"])


## Whether the layer is a library of props placed by a document, rather than
## one merged mesh. Reading and decoding the document is
## `generated_placements.gd`'s; this table only says where it is.
static func has_placements(layer: String) -> bool:
	return not placements_path(layer).is_empty()


## Message for the case that reads as "there is no such layer" rather than an
## error. For an optional layer it ends with the sentence that says so.
static func missing_hint(layer: String) -> String:
	var row: Dictionary = _row(layer)
	if row.is_empty():
		return "Unknown generated layer %s." % layer
	var hint: String = (
		"No %s at %s. Run the ETL and copy its output there:\n" % [row["noun"], path(layer)]
		+ "  python -m pipeline.%s --region wan_chai\n" % row["module"]
		+ "  cp etl/out/<city>/<region>/%s game/assets/generated/" % row["file"]
	)
	var absence: String = String(row["absence"])
	return hint if absence.is_empty() else hint + "\n" + absence


static func _row(layer: String) -> Dictionary:
	if not LAYERS.has(layer):
		push_error("generated_layer: no layer called %s" % layer)
		return {}
	return LAYERS[layer]
