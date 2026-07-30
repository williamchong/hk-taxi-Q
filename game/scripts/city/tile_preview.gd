## Instantiates every generated tile, for looking at the city before `P1-7`.
##
## A dev tool, not the streamer. `CityStreamer` (`P2-1`) will load tiles by
## distance from `city.json`; this just puts all of them in the scene at once so
## the ETL output can be judged by eye. It is therefore **not** a performance
## measurement — no distance culling, no LOD switching.
##
## No transforms are applied because none are needed: `buildings.py` writes tile
## vertices in **region** game space, not tile-local space, so a tile dropped at
## the origin already sits where it belongs. That is also why `city.json` gives
## tiles an `aabb` but no position.
extends Node3D

const GeneratedTiles = preload("res://scripts/city/generated_tiles.gd")

## Which tier to show. Range is open because the tier count is city config
## (`lod_cell_sizes_m`), and a tile may have fewer tiers than that — see
## `LodOutput` in the ETL. A tier with no files simply shows nothing.
@export var lod: int = 0

## Emitted once the city is built, with the bounds of everything loaded, so a
## camera can frame whatever region is on disk rather than hardcoding one.
signal built(low: Vector3, high: Vector3)


func _ready() -> void:
	var paths: PackedStringArray = GeneratedTiles.files("_lod%d.glb" % lod)
	if paths.is_empty():
		push_warning(GeneratedTiles.missing_hint())
		return

	var bounds := AABB()
	var measured: bool = false
	var tiles: int = 0
	var triangles: int = 0

	for path: String in paths:
		var packed: PackedScene = GeneratedTiles.load_tile(path)
		if packed == null:
			push_warning("Could not load %s" % path)
			continue
		var tile: Node3D = packed.instantiate()
		tile.name = path.get_file().get_basename()
		# Added before measuring: `global_transform` needs it in the tree.
		add_child(tile)
		tiles += 1

		for instance: MeshInstance3D in tile.find_children("*", "MeshInstance3D", true, false):
			var mesh := instance.mesh as ArrayMesh
			if mesh == null:
				continue
			# Tracked with a flag rather than seeded from the first tile: a tile
			# with no mesh would contribute a zero AABB at the origin and drag
			# the framing back there.
			var box: AABB = instance.global_transform * mesh.get_aabb()
			bounds = box if not measured else bounds.merge(box)
			measured = true
			for surface: int in mesh.get_surface_count():
				# O(1), and 0 rather than null on a non-indexed surface —
				# `surface_get_arrays(...)[ARRAY_INDEX]` is null there, and
				# decodes every vertex buffer in the city just to count.
				triangles += mesh.surface_get_array_index_len(surface) / 3

	print("city preview: %d tiles at LOD%d, %d triangles" % [tiles, lod, triangles])
	if measured:
		built.emit(bounds.position, bounds.end)
