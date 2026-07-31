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

## Schema this understands, matching `CITY_SCHEMA` in `etl/pipeline/export.py`.
const SCHEMA_VERSION: int = 2


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

## Drawn half-width of the carriageway, in metres, keyed by road-graph edge id.
##
## Not derivable from `roadgraph.json`: that publishes the **authored** street
## width, and `P1-4` draws the ribbon at `width_m x widen_for(speed_limit_kph)`.
## The widening lives on the ETL's surface style, which `config.py` deliberately
## keeps out of the graph — so the drawn width reaches the game through the
## manifest or not at all. `RoadGraph` (`P2-2`) needs it to put a car in the
## nearside lane rather than on the seam where opposed ribbons overlap.
var carriageway_half_width_m: Dictionary[int, float] = {}


## The manifest, or null with a pushed message.
static func load_manifest() -> CityManifest:
	var document: Dictionary = GeneratedDocument.load_object(PATH, SCHEMA_VERSION, missing_hint())
	if document.is_empty():
		return null

	var manifest := CityManifest.new()
	manifest.city_id = str(document.get("city_id", ""))
	manifest.region_id = str(document.get("region_id", ""))
	manifest.tile_size_m = float(document.get("tile_size_m", 0.0))
	manifest.road_graph_path = _resolve(document.get("road_graph", ""))
	manifest.road_surface_path = _resolve(document.get("road_surface", ""))
	manifest.fares_path = _resolve(document.get("fares", ""))
	for entry: Dictionary in document.get("carriageway", []):
		manifest.carriageway_half_width_m[int(entry.get("edge", -1))] = float(
			entry.get("half_width_m", 0.0)
		)

	var extent: Dictionary = document.get("bounds_game", {})
	manifest.bounds = _box(_point(extent.get("min")), _point(extent.get("max")))

	for entry: Dictionary in document.get("tiles", []):
		manifest.tiles.append(_tile(entry))
	return manifest


## Every file the manifest *names*, in order: the three documents, then every
## tier of every tile. Not every file a build ships — `city.json` itself is not
## in the list, because it names the others and not itself. A caller copying a
## region wants this plus `PATH`, which is what `tools/sync_generated.sh` does.
func shipped() -> PackedStringArray:
	var paths: PackedStringArray = [road_graph_path, road_surface_path, fares_path]
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
		tile.aabb = _box(_point(corners[0]), _point(corners[1]))
	else:
		push_error("tile %s has no usable aabb" % tile.id)
	return tile


## A manifest-relative path as a `res://` one. Empty stays empty, so a missing
## key reads as "not named" rather than as the generated directory itself.
static func _resolve(relative: Variant) -> String:
	var path: String = str(relative)
	return PATH.get_base_dir().path_join(path) if not path.is_empty() else ""


static func _point(values: Variant) -> Vector3:
	var array: Array = values if values is Array else []
	if array.size() != 3:
		push_error("expected a 3-element position, got %s" % [values])
		return Vector3.ZERO
	return Vector3(array[0], array[1], array[2])


## An AABB from two corners. `AABB` stores position and size, the contract
## stores min and max, and the subtraction is the whole difference.
static func _box(low: Vector3, high: Vector3) -> AABB:
	return AABB(low, high - low)
