class_name CityRegions
extends Node3D
## Every synced region, each at its place relative to the frame (`P5-9c`).
##
## `tools/sync_generated.sh` lists the regions in `regions.json`, the first the
## **frame**. This instantiates `region_scene` once per listed region — the eight
## layers, the heroes and the fence — adds the tiles to it, tells every child
## which region it holds, and stands the region node at
## `city_offset(region) − city_offset(frame)`. Causeway Bay stands at
## **`[1649, 0, 0]`** from Wan Chai, exact in float because both origins are whole
## metres (`Q7`); the frame stands at the origin, so a one-region tree is the
## scene it was before this node existed.
##
## 🔴 **A `Node3D` per region, never one streamer over N manifests.** Everything
## under the region node is authored in its own region's frame — tile vertices,
## chunk vertices, placements, landmark transforms — so one translation on the
## parent places all of it, and nothing below has to learn an offset. The
## streamer is the one child that compares against coordinates rather than
## drawing them, and it takes the camera through `to_local`.
##
## ⚠️ **The regions' boxes overlap by ~250 m once translated**: each region owns
## the far halves of the runs that start in it, so Wan Chai's `bounds_game`
## reaches x 1760 and Causeway Bay's starts at x −137 (1512 in the frame). The
## grids are 1,649 m apart, not a multiple of 150, so a chunk beyond a region's
## grid is kept visible only by the streamer's own `aabb` pick (`P5-7f`). A cull
## in region space would drop it.
##
## ⚠️ **Two streamers means two budgets.** `max_loads_in_flight` and
## `max_instantiations_per_frame` are per streamer, so on the line they double.

const GeneratedRegions = preload("res://scripts/city/generated_regions.gd")
const TilePreview = preload("res://scripts/city/tile_preview.gd")

## One region's content: the layer nodes, `Landmarks` and `Fence`. No tiles —
## they differ between the scenes and are added below.
@export var region_scene: PackedScene

## The streaming profile, when the tiles stream (`city_drive.tscn`). Null means
## every tile at once, `tile_preview.gd`'s dev view (`city_preview.tscn`).
@export var streaming: StreamingProfile

## What the streamers measure from, when they stream.
@export var camera: Node3D

## The frame region's tiles have settled, with its bounds — `tile_preview.gd`'s
## and `CityStreamer`'s contract, forwarded so a camera frames the region the way
## it did when the tiles were its sibling.
signal built(low: Vector3, high: Vector3)

## Each resident region's node, in `regions.json` order, the frame first.
var _regions: Array[Node3D] = []
var _streamers: Array[CityStreamer] = []


func _ready() -> void:
	if region_scene == null:
		push_error("CityRegions has no region_scene; nothing will be placed")
		return
	# `[""]` with no list — a tree synced before `P5-9b`, or none at all: one
	# region at the origin, so a fresh clone degrades to the same missing-city
	# hints it always printed.
	var ids: PackedStringArray = GeneratedRegions.resident()

	var offsets: Array[Vector3] = []
	for id: String in ids:
		offsets.append(_offset_of(id))
	for index: int in ids.size():
		var id: String = ids[index]
		var node: Node3D = region_scene.instantiate()
		node.name = id.to_pascal_case() if not id.is_empty() else "Region"
		node.position = offsets[index] - offsets[0]
		var tiles: Node3D = _tiles_for(id)
		node.add_child(tiles)
		node.move_child(tiles, 0)
		for child: Node in node.get_children():
			if "region" in child:
				child.set("region", id)
		if _regions.is_empty() and tiles.has_signal("built"):
			tiles.connect("built", built.emit)
		add_child(node)
		_regions.append(node)


## Make the road under `world_point` resident now, in every region that has any
## within its streamer's reach — at the seam that is both, and each streamer
## loads only its own chunks. Asked of all rather than of the one whose box holds
## the point, because the boxes overlap by the owned far halves.
func hold_ground_at(world_point: Vector3) -> void:
	for streamer: CityStreamer in _streamers:
		streamer.hold_ground_at(world_point)


## The resident region nodes, the frame first.
func regions() -> Array[Node3D]:
	return _regions


func _tiles_for(id: String) -> Node3D:
	var tiles: Node3D
	if streaming != null:
		var streamer := CityStreamer.new()
		streamer.profile = streaming
		streamer.camera = camera
		streamer.region = id
		_streamers.append(streamer)
		tiles = streamer
	else:
		tiles = TilePreview.new()
	tiles.name = "Tiles"
	return tiles


## A region's `city_offset`, or zero where its manifest will not load — the
## manifest has pushed why, and the region's own children will say so again.
static func _offset_of(id: String) -> Vector3:
	var manifest: CityManifest = CityManifest.shared(id)
	return manifest.city_offset if manifest != null else Vector3.ZERO
