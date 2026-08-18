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
## 4 since `Q23`: `carriageway[].half_width_m` is an array, one value per station
## of that edge's polyline, where it was one number for the whole edge.
##
## 5 since `P3-7`: every tile ships `TEXCOORD_0` — height above the building's own
## base, and a surface marker plus phase — and names its material `city_facade`
## so the importer gives it the window-band shader. A v4 reader would draw a v5
## tile blank and blame the shader.
##
## 6 since `Q40`/`Q41`: every tile ships `TEXCOORD_1` — a packed per-building
## facade-survey state in `x` (glazed / tint bin / grammar, 0 = refused, falling
## back to the hash) with `y` reserved for `Q42`'s riders. A v5 reader would
## silently draw the hash city while the bundle claims the survey.
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
const SCHEMA_VERSION: int = 10


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
## Published rather than re-derived. `roadgraph.json`'s `width_m` is
## `lanes x lane_width_m` **hand-tuned upward for playability**, so dividing it
## back by `lanes` does not recover this number.
var lane_width_m: float = 0.0


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
	for entry: Dictionary in document.get("carriageway", []):
		var edge: int = int(entry.get("edge", -1))
		manifest.carriageway_half_width_m[edge] = _floats(entry, "half_width_m")
		manifest.carriageway_clear_width_m[edge] = _floats(entry, "clear_width_m")
	manifest.lane_width_m = float(document.get("lane_width_m", 0.0))

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


## Every file the manifest *names*, in order: the four documents, then every
## tier of every tile. Not every file a build ships — `city.json` itself is not
## in the list, because it names the others and not itself. A caller copying a
## region wants this plus `PATH`, which is what `tools/sync_generated.sh` does.
func shipped() -> PackedStringArray:
	var paths: PackedStringArray = [road_graph_path, road_surface_path, fares_path, landmarks_path]
	for tile: Tile in tiles:
		paths.append_array(tile.lods)
	return paths


## Message for the case that reads as "there is no city" rather than an error.
static func missing_hint() -> String:
	return (
		"No city manifest at %s. Build the region and sync it:\n" % PATH
		+ "  python -m pipeline --city hong_kong --region wan_chai\n"
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
