class_name CityManifest
extends RefCounted
## `city.json`, read once and typed (`P1-7`).
##
## The shipping route into the generated city, and the reason it exists is not
## tidiness. Until `P1-7` the game found tiles by listing their directory with
## `DirAccess`, which works in the editor — where `res://` is a real folder —
## and **cannot** work in an exported build, where `res://` is a PCK archive
## Godot's virtual filesystem will not enumerate. A build learns what it
## contains from this file or not at all.
##
## The three `generated_*.gd` locators beside this one still name their document
## by a constant. They are dev-scene and verify-tool plumbing that predates the
## manifest, and `RoadGraph` (`P2-2`) and `FareSystem` (`P3-1`) will take those
## paths from here when they replace the previews. Until then `verify_city.gd`
## asserts the two agree, so they cannot drift quietly.
##
## Reading the manifest loads no geometry. A `Tile` carries the AABB
## `export.py` measured, so `CityStreamer` (`P2-1`) can rule a tile out of range
## without touching its ~400 KB of mesh.
##
## Paths inside `city.json` are relative to the manifest, so the ETL's output
## directory copies anywhere under `res://` without rewriting. They are resolved
## once, here.

const GeneratedDocument = preload("res://scripts/city/generated_document.gd")

const PATH: String = "res://assets/generated/city.json"

## The `carriageway[].clear_width_m` value that means "no cross-section here
## to judge" — see `carriageway_clear_width_m`.
const NOT_MEASURED: float = -1.0

## Schema this understands, matching `CITY_SCHEMA` in `etl/pipeline/export.py`.
##
## 22 since `Q107`: `carriageway[].offset_m` is an array beside the half-width,
## one value per station, saying where the drawn ribbon is centred left of
## travel. A reader that keeps taking `half_width_m` as a half-width about the
## centreline is wrong about every off-grade edge.
## 4 since `Q23`: `carriageway[].half_width_m` is an array, one value per station
## of that edge's polyline, where it was one number for the whole edge.
##
## 5 since `P3-7`: every tile ships `TEXCOORD_0` — height above the building's own
## base, and a surface marker plus phase — and names its material `city_facade`
## so the importer gives it the window-band shader. A v4 reader would draw a v5
## tile blank and blame the shader.
##
## 6 since `Q40`/`Q41`: every tile shipped `TEXCOORD_1` — a packed per-building
## facade-survey state in `x` (glazed / tint bin / grammar, 0 = refused, falling
## back to the hash) with `y` reserved for `Q42`'s riders. A v5 reader would
## silently draw the hash city while the bundle claims the survey. Withdrawn
## again at 20.
##
## 7 since `P3-6`: the manifest names `landmarks.json`, and the tiles no longer
## contain the buildings its heroes replace. The bump is for the removal: a v6
## reader would draw holes where the excluded buildings stood, with no hero
## over them.
##
## 9 since `Q51`: `carriageway[].clear_width_m` says how much of each station a
## car can actually get through, and the manifest publishes `lane_width_m` as
## the bar it is read against. The bump is for the silent wrong answer again,
## and the worst-shaped one yet: a v8 reader would load a v9 bundle happily and
## route traffic down edges the bundle itself records as blocked.
##
## 10 since `P3-12`: `roads.glb` ships `TEXCOORD_1` — packed marking state in `x`
## and the edge's drawn length in `y` — and names its material `road_markings`
## so the importer gives it the markings shader. `P3-7`'s precedent, which
## bumped for the same reason on the tiles; the wrong answer is quieter here,
## because a v9 reader draws an unmarked road that looks like the road it always
## drew rather than like a failure.
##
## 11 since `P3-14`: the manifest names `tram.glb`, a new shipped asset drawn
## from iB1000's published rails. The `landmark_assets` precedent decides it —
## 7 and 8 both bumped because the *asset set* a v-N document describes had
## changed, and `shipped()` below is what turns that set into a PCK. A v10
## reader draws no tramway, which on its own would be `P3-10`'s no-bump case;
## what it also does is compute a shipped set missing a file the bundle
## depends on.
##
## 12 since `P3-15`: the manifest names `arrows.glb`, the published turn arrows
## drawn from TD's `DTAD_RD_MARK_SYM_PT`. Exactly `P3-14`'s argument — a v11
## reader computes a shipped set missing a file the bundle depends on.
##
## 13 since `P3-18`: the manifest names `boxjunctions.glb`, the published yellow
## box junctions drawn from TD's `DTAD_YL_BOX_POLY`. `P3-14`/`P3-15`'s argument
## a third time — a v12 reader computes a shipped set missing a bundle file.
##
## 14 since `P3-19`: the manifest names `railings.glb`, the published pedestrian
## railings drawn from TD's `DTAD_RAILING_LINE`. The same argument a fourth time
## — a v13 reader computes a shipped set missing a bundle file.
##
## 15 since `P3-16`: the manifest names `signs.glb`, the published traffic signs
## drawn from TD's `DTAD_TS_ABV_PT`/`DTAD_TS_POLE_PT`. The same argument a fifth
## time — a v14 reader computes a shipped set missing a bundle file.
##
## 16 since `P3-23`: the manifest names `roadmarks.glb`, the published stop and
## give-way lines drawn from TD's `DTAD_RD_MARK_LINE`. The same argument a sixth
## time — a v15 reader computes a shipped set missing a bundle file.
##
## 17 since `Q70`: the manifest names `signs_text.png`, the sign lettering's
## atlas, which used to ride inside `signs.glb` as an embedded buffer view. The
## same argument a seventh time — a v16 reader computes a shipped set missing a
## bundle file — reached from the other direction, and the direction is the
## finding: Godot's importer *extracts* an embedded image into a file beside the
## asset, so the bundle already had that file and only the manifest did not know.
## `sync_generated.sh` deletes what the manifest does not name, and did.
##
## 18 since `P3-17`: the manifest names `signals.glb`, the published traffic
## signal heads drawn from TD's `DTAD_TRAFFIC_LIGHT_PT`. The same argument an
## eighth time — a v17 reader computes a shipped set missing a bundle file.
## 19 since `P3-26`: the manifest names `lamps.glb`, the published lamp posts
## drawn from iB1000's `UtilityPoint` — a ninth time, unchanged.
##
## ⚠️ **All nine keys are optional and may be null.** A city whose estate
## publishes no tramway, no marking symbols, no box polygons, no lamp posts, no
## railing layer, no sign layer or no transverse markings ships none — so
## `tramway_path`, `arrows_path`, `boxjunctions_path`, `lamps_path`,
## `railings_path`, `signs_path` and `roadmarks_path` are empty for such a region and that is the honest answer
## rather than a missing file. `signals_path` is empty on those terms *and* for
## a region whose publisher spells its signal codes outside `head_prefixes` —
## the gate is a rule about spelling that nothing published grades (`P3-17`).
## `signs_text_atlas_path` is emptier still: it is null for all of those *and*
## for a region whose faces carry no lettering.
##
## 20 since `Q102`: the tiles ship no `TEXCOORD_1` at all. The vision reader
## that filled it was withdrawn on cost, and the sentinel it left behind was a
## legal code meaning "refused" — so a v19 reader loading v20 tiles would read
## a whole city refusing a survey it does not carry. The bump is for the
## removal, on `P3-6`'s precedent at 7.
##
## 21 since `P3-29`: two things, and either alone would have bumped it.
##
## `car_width_m` — the bar the **player** fence is set at, beside
## `lane_width_m`, which is the bar `P3-3`'s traffic is *routed* on. A v20 reader
## has one bar where there are two, so it can only fence at the lane: either it
## sends the player down `e207`'s 1.95 m or it closes `e781`'s 3.50 m, and `Q19`
## ruled the two may never be merged. Zero where the city declares no
## `clearance:` block, on `lane_width_m`'s own "a missing bar is not a bar of
## zero" terms.
##
## And the manifest names `fence.json`, where the barriers dressing that fence
## stand. The `landmark_assets` argument again — a v20 reader computes a shipped
## set missing a bundle file — with a sharper edge than usual: what it would
## *also* do is refuse edges the player can still reach and leave nothing there
## to see, which is precisely the invisible wall `Q19` exists to remove.
const SCHEMA_VERSION: int = 22


## One entry of `tiles` — a square of the city, at every tier the ETL built.
class Tile:
	extends RefCounted

	var id: String
	var lods: PackedStringArray
	## ⚠️ Measured from the tile's geometry, **not** its grid square, and often
	## bigger: a building belongs to the tile its centre falls in and may
	## overhang a neighbour by half a footprint. Cull with this, never with a
	## square derived from `tile_size_m`.
	var aabb: AABB

	## The file for `tier`, clamped to what this tile actually has.
	##
	## Clamped rather than checked by the caller because tier count is city
	## config (`lod_cell_sizes_m`) and a tile may have fewer — a tile stops
	## emitting tiers once everything in it is *smaller than the cell*, because
	## from there nothing survives any coarser one either. Asking for LOD2 of a
	## one-tier tile should draw the tile, not nothing.
	func lod(tier: int) -> String:
		if lods.is_empty():
			return ""
		return lods[clampi(tier, 0, lods.size() - 1)]


var city_id: String
var region_id: String
var tile_size_m: float

## Where game `(0, 0, 0)` sits in the source CRS — the region's north-west
## corner, in metres, as `crs.py` anchored it.
##
## Kept so a position on screen can be stated in coordinates that mean something
## outside the engine: `to_grid` turns the car's transform into an easting and a
## northing you can type into a GIS beside the source data. Without it a readout
## can only say "172 m east of a corner nothing else knows about".
var origin_easting: float
var origin_northing: float
var origin_elevation: float

## Union of everything the region contains — tiles, road surface and fare nodes.
##
## ⚠️ Not the region rectangle. Wan Chai is declared as 1650 x 887 m and its
## content spans 1668 x 942 m, because tiles overhang and the road ribbon is
## drawn outward from centrelines that run to the boundary. Sizing a spatial
## partition or placing map edges off the rectangle clips real geometry.
var bounds: AABB

var tiles: Array[Tile] = []

## The three documents `city.json` names but does not contain — resolved to
## `res://` paths. The graph alone is 0.65 MB on disk and ~6 MB parsed, and each
## consumer wants its document at a different moment, so the manifest points
## rather than inlines.
var road_graph_path: String
var road_surface_path: String
var fares_path: String
var landmarks_path: String
## Where P3-29 stands a barrier. Named unconditionally like the four
## above rather than as an optional asset: `fence.py` writes its document
## on every run, so an empty `barriers` list means the fence found nothing
## to close and a *missing file* means the stage never ran — two states a
## build has to be able to tell apart.
var fence_path: String

## The tramway mesh (`P3-14`), or **empty** where the region ships none.
##
## Unlike the four above this one is genuinely optional: `Q58` draws it from
## iB1000's `CartoTransLine` tramway code, and a city whose estate publishes no
## such layer declares no `tramway:` block and exports a null. Callers must
## treat empty as "this region has no tramway", never as a build failure.
var tramway_path: String

## The turn arrows mesh (`P3-15`), or **empty** where the region ships none.
##
## Optional on the same terms as `tramway_path`: `Q53` draws these from TD's
## published marking symbols, and a city whose estate publishes none declares no
## `arrows:` block and exports a null. ⚠️ It is also empty where the block is
## declared and **every** symbol failed the join — the stage names its asset from
## what it drew, not from a constant — so empty means "no arrows in this
## bundle", never "no arrows block".
var arrows_path: String

## The yellow box junctions mesh (`P3-18`), or **empty** where the region ships
## none.
##
## Optional on the same terms as `arrows_path`: drawn from TD's published
## `DTAD_YL_BOX_POLY` polygons, and a city whose estate publishes none declares
## no `boxjunctions:` block and exports a null. ⚠️ It is also empty where the
## block is declared and **every** box failed the join — the stage names its
## asset from what it drew, not from a constant — so empty means "no box
## junctions in this bundle", never "no boxjunctions block".
var boxjunctions_path: String

## The pedestrian railings mesh (`P3-19`), or **empty** where the region ships
## none.
##
## Optional on the same terms as `boxjunctions_path`: drawn from TD's published
## `DTAD_RAILING_LINE`, and a city whose estate publishes none declares no
## `railings:` block and exports a null. ⚠️ It is also empty where the block is
## declared and no run survived the join — the stage names its asset from what
## it drew — so empty means "no railings in this bundle", never "no railings
## block".
var railings_path: String

## The lamp-post mesh (`P3-26`), or **empty** where the region ships none.
##
## Optional on the same terms as `railings_path`: drawn from LandsD's published
## `UtilityPoint`, and a city whose estate publishes none declares no `lamps:`
## block and exports a null. ⚠️ It is also empty where the block is declared and
## no column cleared the carriageway — the stage names its asset from what it
## drew — so empty means "no lamps in this bundle", never "no lamps block".
##
## ⚠️ **Empty is a LESS ordinary answer here than for `signals_path`**, and the
## difference is the point. A signal layer can vanish because `REFNAME` has no
## published domain and the gate is a spelling rule; `UTILITYPOINTTYPE` **has** a
## published domain, stored inside the geodatabase, so a region drawing no lamps
## has declared no block or found no kerb — it has not misread a vocabulary.
var lamps_path: String

## The traffic-sign mesh (`P3-16`), or **empty** where the region ships none.
##
## Optional on the same terms as `railings_path`. ⚠️ **But empty is a more
## ordinary answer here than for any other key**: `P3-16` draws only the signs
## whose meaning is their *shape*, and 2,364 of Wan Chai's 3,276 are text-faced
## and refused on the no-texture contract. A region whose signs are all time plates and parking
## legends draws none and is correct to.
var signs_path: String

## The stop and give-way line mesh (`P3-23`), or **empty** where the region ships
## none.
##
## Optional on the same terms as `boxjunctions_path`: drawn from TD's published
## `DTAD_RD_MARK_LINE`, and a city whose estate publishes no transverse markings
## declares no `road_marks:` block and exports a null. ⚠️ It is also empty where
## the block is declared and every marking failed the *transverse* join — the
## stage names its asset from what it drew, not from a constant — so empty means
## "no stop lines in this bundle", never "no road_marks block".
var roadmarks_path: String

## The traffic signal heads mesh (`P3-17`), or **empty** where the region ships
## none.
##
## ⚠️ **Optional on sharper terms than its siblings.** A city without a
## `signals:` block exports a null, and so does one whose estate publishes no
## signal layer — but so does one whose publisher numbers its heads differently,
## because `DTAD_TRAFFIC_LIGHT_PT.REFNAME` has no published domain and the gate
## that admits a code is a spelling rule this project wrote. Empty means "no
## signal heads in this bundle", never "no signal heads exist".
var signals_path: String

## 🔴 **The one image in the bundle** (`Q70`, `Q63`, `P3-20`) — the sign
## lettering's atlas — or **empty** where the region baked none.
##
## ⚠️ **Nothing in the game loads this by path, and it is named anyway.** The
## atlas reaches the renderer through `signs.glb`, which references it, and
## `tools/generated_scene_import.gd` deliberately reads the texture the importer
## already resolved rather than loading a second name for the same file. What
## this key is for is `shipped()`: the atlas lives in `game/assets/generated/`,
## `sync_generated.sh` deletes everything the manifest does not name, and before
## `Q70` this file was not named — so it was swept on every run and
## `verify_signs.gd` went red until someone forced a re-import by hand.
##
## ⚠️ **Emptier than any other optional key.** It is null for every region that
## ships no signs at all, *and* for one whose drawn faces carry no lettering —
## which is the state `Texture memory: 0` describes and the default `Q63`
## insisted stay the default.
var signs_text_atlas_path: String

## Drawn half-width of the carriageway, in metres, keyed by road-graph edge id —
## **one value per station** of that edge's `roadgraph.json` polyline.
##
## Not derivable from `roadgraph.json`: that publishes the **authored** street
## width, and `P1-4` draws the ribbon at `width_m x widen_for(...)`.
## The widening lives on the ETL's surface style, which `config.py` deliberately
## keeps out of the graph — so the drawn width reaches the game through the
## manifest or not at all. `RoadGraph` (`P2-2`) needs it to put a car in the
## nearside lane rather than on the seam where opposed ribbons overlap.
##
## An array rather than a number since `Q23`. `elevation_level` is an attribute
## of a whole edge but a road becomes a bridge partway along one, so a level-0
## edge climbing onto a ramp is drawn at its authored width there and widened
## further along. Reading the first entry as if it covered the edge would put
## the lane centre 0.96 m out on a two-lane street — the same error the whole
## table exists to prevent.
var carriageway_half_width_m: Dictionary[int, PackedFloat32Array] = {}

## Where each station's drawn ribbon is **centred**, in metres left of travel,
## keyed by road-graph edge id — one value per station, indexed exactly as the
## half-width above.
##
## 🔴 **The ribbon is no longer symmetric about the published centreline
## (`Q107`).** Off-grade its two rails are cut to the deck it stands on
## independently, so `half_width_m` is half the distance *between the rails* and
## this says where that span sits. A lane centre taken as `centreline +
## half_width` alone is out by this much — up to several metres on the
## interchange — and `Q106` is what that costs: four ETL-side instruments made
## exactly that assumption and every one was wrong about the whole elevated
## network, in two directions, for a release.
##
## ⚠️ **0.0 on every level-0 edge**, which is the entire drivable network until
## `P4-1` opens the rest — so this changes no lane centre the game places today
## and is plumbed so that it will not have to be discovered again when it does.
var carriageway_offset_m: Dictionary[int, PackedFloat32Array] = {}

## Width of the widest gap a car could get through, in metres, keyed by
## road-graph edge id — **one value per station**, like the half-width above and
## indexed the same way, so both come off one station.
##
## `NOT_MEASURED` (-1.0) where `surface.py` held the ribbon back for a junction
## cap and there was no cross-section to judge. Negative because no real
## clearance can be: a consumer that forgets to check it gets an obviously wrong
## answer rather than a plausible zero, and zero is the one value that would read
## as "blocked solid" on precisely the stations that are not blocked at all.
##
## Not derivable from anything else the bundle ships. `roadgraph.json` describes
## the authored street and `city.json`'s `half_width_m` describes the tarmac; the
## question this answers is what *stands in* the tarmac, which only the stage
## that read the buildings beside it could measure (`Q51`).
var carriageway_clear_width_m: Dictionary[int, PackedFloat32Array] = {}

## One lane, in metres, as the city config authored it — the bar
## `carriageway_clear_width_m` is read against.
##
## Published rather than re-derived, and ⚠️ **`roadgraph.json` cannot stand in
## for it**: `width_m` is a *measured* carriageway on the edges two publishers
## span (`Q95`) and an authored `lanes x lane_width_m` elsewhere, while the
## ribbon over it is `max(width_m, floor)`. Dividing any of the three by
## `lanes` recovers something, but not this number.
var lane_width_m: float = 0.0

## The car's own width, in metres — the bar the **player** fence is set at.
##
## 🔴 **Two bars, and merging them is the one thing `Q19` forbids here.**
## `lane_width_m` above answers "should traffic be routed down this edge"
## (`Q51`); this answers "can the player get down it at all". Re-pointing
## `RoadGraph.is_passable` at 1.80 m would send traffic down `e207`'s 1.95 m,
## and fencing the player at 3.20 m would close `e781`'s 3.50 m against them.
##
## Zero where the bundle declares none, on exactly `lane_width_m`'s terms: a
## missing bar is not a bar of zero, and with nothing to compare against the
## honest reading is that no edge is fenced rather than that every one is.
var car_width_m: float = 0.0


## The manifest, or null with a pushed message.
static func load_manifest() -> CityManifest:
	var document: Dictionary = GeneratedDocument.load_object(PATH, SCHEMA_VERSION, missing_hint())
	if document.is_empty():
		return null

	var manifest := CityManifest.new()
	manifest.city_id = str(document.get("city_id", ""))
	manifest.region_id = str(document.get("region_id", ""))
	manifest.tile_size_m = float(document.get("tile_size_m", 0.0))

	var anchor: Dictionary = document.get("origin", {})
	manifest.origin_easting = float(anchor.get("easting", 0.0))
	manifest.origin_northing = float(anchor.get("northing", 0.0))
	manifest.origin_elevation = float(anchor.get("elevation", 0.0))

	manifest.road_graph_path = _resolve(document.get("road_graph", ""))
	manifest.road_surface_path = _resolve(document.get("road_surface", ""))
	manifest.fares_path = _resolve(document.get("fares", ""))
	manifest.landmarks_path = _resolve(document.get("landmarks", ""))
	manifest.fence_path = _resolve(document.get("fence", ""))
	# A **null** `tramway` is the "this region has no tramway" state, and
	# `_resolve` maps it to empty. Not a branch here on purpose: `str(null)` is
	# `"<null>"`, which would resolve to a plausible-looking path that loads
	# nothing, so the guard belongs where every caller gets it.
	manifest.tramway_path = _resolve(document.get("tramway"))
	# Null on the same terms, and `_resolve` maps it to empty for the same
	# `str(null)` reason spelled out above.
	manifest.arrows_path = _resolve(document.get("arrows"))
	manifest.boxjunctions_path = _resolve(document.get("boxjunctions"))
	manifest.lamps_path = _resolve(document.get("lamps"))
	manifest.railings_path = _resolve(document.get("railings"))
	manifest.signs_path = _resolve(document.get("signs"))
	manifest.roadmarks_path = _resolve(document.get("roadmarks"))
	manifest.signals_path = _resolve(document.get("signals"))
	manifest.signs_text_atlas_path = _resolve(document.get("signs_text_atlas"))
	for entry: Dictionary in document.get("carriageway", []):
		var edge: int = int(entry.get("edge", -1))
		manifest.carriageway_half_width_m[edge] = _floats(entry, "half_width_m")
		manifest.carriageway_offset_m[edge] = _floats(entry, "offset_m")
		manifest.carriageway_clear_width_m[edge] = _floats(entry, "clear_width_m")
	manifest.lane_width_m = float(document.get("lane_width_m", 0.0))
	# `null` where the city declares no `clearance:` block. Read through a
	# variable rather than `float(document.get(...))` because `float(null)` is a
	# runtime error in GDScript, and the null case has to land on the same 0.0
	# the var defaults to — "no bar", not "a bar of zero".
	var bar: Variant = document.get("car_width_m")
	manifest.car_width_m = 0.0 if bar == null else float(bar)

	var extent: Dictionary = document.get("bounds_game", {})
	manifest.bounds = box(point(extent.get("min")), point(extent.get("max")))

	for entry: Dictionary in document.get("tiles", []):
		manifest.tiles.append(_tile(entry))
	return manifest


## A game position in the source CRS: **easting, northing, elevation** — in that
## order, which is not the order of the `Vector3` that went in.
##
## The inverse of `RegionTransform.to_game` in `etl/pipeline/crs.py`, and it has
## to stay that way: game `+X` is east, game `+Y` is up, and game `-Z` is north,
## so the northing is a *subtraction*. Returning a `Vector3` rather than a
## `Vector2` keeps the elevation, which is the axis that catches a road on the
## wrong deck.
func to_grid(game_position: Vector3) -> Vector3:
	return Vector3(
		game_position.x + origin_easting,
		origin_northing - game_position.z,
		game_position.y + origin_elevation
	)


## A compass bearing in degrees, `0` at north and rising eastward, from a
## direction in game space.
##
## Static, and here rather than in the two places that wanted it, because it
## encodes the same fact `to_grid` does — game `-Z` is north — and `crs.py` is
## explicit that the moment that convention is restated somewhere else it drifts.
## In Hong Kong `000` faces the harbour.
static func bearing_deg(forward: Vector3) -> float:
	return fposmod(rad_to_deg(atan2(forward.x, -forward.z)), 360.0)


## Every file the manifest *names*, in order: the four documents, then the
## tramway, the arrows, the box junctions, the railings, the signs, the stop
## lines and the sign lettering's atlas where the region has them, then
## every tier of every tile. Not every file a build ships — `city.json` itself is not
## in the list, because it names the others and not itself. A caller copying a
## region wants this plus `PATH`, which is what `tools/sync_generated.sh` does.
func shipped() -> PackedStringArray:
	var paths: PackedStringArray = [
		road_graph_path, road_surface_path, fares_path, landmarks_path, fence_path
	]
	# ⚠️ **One list rather than seven `if`s, in `OPTIONAL_ASSET_KEYS`' order** —
	# `etl/pipeline/export.py`'s `shipped()` holds the same names in the same
	# order, so the two can be read side by side as the mirrors they are. It was
	# seven hand-written copies on both sides until the seventh forced the issue.
	#
	# ⚠️ **`signs_text_atlas_path` stands on its own, not nested under
	# `signs_path`.** The two are written together and a bundle with one and not
	# the other is broken, but this function is the definition of what the bundle
	# contains — folding the pair into one test would hide the asymmetric case
	# from the only list that could show it.
	var optional: Array[String] = [
		tramway_path,
		arrows_path,
		boxjunctions_path,
		lamps_path,
		railings_path,
		signs_path,
		signs_text_atlas_path,
		roadmarks_path,
		signals_path,
	]
	for asset_path: String in optional:
		if not asset_path.is_empty():
			paths.append(asset_path)
	for tile: Tile in tiles:
		paths.append_array(tile.lods)
	return paths


## Message for the case that reads as "there is no city" rather than an error.
static func missing_hint() -> String:
	return (
		"No city manifest at %s. Build the region and sync it:\n" % PATH
		+ "  python -m pipeline --region wan_chai\n"
		+ "  tools/sync_generated.sh hong_kong wan_chai"
	)


## One per-station array of a `carriageway` entry, typed.
##
## `PackedFloat32Array` cannot be assigned from an untyped `Array`, so both
## tables have to be walked; walking them in one place is what stops the second
## from being added without the guard the first has.
static func _floats(entry: Dictionary, key: String) -> PackedFloat32Array:
	var values := PackedFloat32Array()
	for value: float in entry.get(key, []):
		values.append(value)
	return values


static func _tile(entry: Dictionary) -> Tile:
	var tile := Tile.new()
	tile.id = str(entry.get("id", ""))
	for relative: String in entry.get("lods", []):
		tile.lods.append(_resolve(relative))

	if tile.lods.is_empty():
		# Reported here rather than left to the caller, which would otherwise
		# reach `load("")` — a hard "Resource file not found: res://" that names
		# neither the tile nor the manifest.
		push_error("tile %s names no LOD files" % tile.id)

	var corners: Array = entry.get("aabb", [])
	if corners.size() == 2:
		tile.aabb = box(point(corners[0]), point(corners[1]))
	else:
		push_error("tile %s has no usable aabb" % tile.id)
	return tile


## A manifest-relative path as a `res://` one. Empty stays empty, so a missing
## key reads as "not named" rather than as the generated directory itself.
static func _resolve(relative: Variant) -> String:
	# ⚠️ `null` is a legitimate value, not a missing one: `city.json` writes it
	# for an optional document the region does not ship (`P3-14`'s tramway). It
	# has to be caught before `str`, which would turn it into `"<null>"` and
	# resolve a path that looks real and loads nothing.
	if relative == null:
		return ""
	var path: String = str(relative)
	return PATH.get_base_dir().path_join(path) if not path.is_empty() else ""


static func point(values: Variant) -> Vector3:
	var array: Array = values if values is Array else []
	if array.size() != 3:
		push_error("expected a 3-element position, got %s" % [values])
		return Vector3.ZERO
	return Vector3(array[0], array[1], array[2])


## An AABB from two corners. `AABB` stores position and size, the contract
## stores min and max, and the subtraction is the whole difference. Public,
## with `point` above, because every generated document spells a position the
## same way and the locators parse entries of their own documents.
static func box(low: Vector3, high: Vector3) -> AABB:
	return AABB(low, high - low)
