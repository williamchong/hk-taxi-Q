extends Node3D
## Instantiates every tile `city.json` names, for looking at the whole city.
##
## A dev tool, not the streamer. `CityStreamer` (`P2-1`) will load tiles by
## distance from the same manifest; this puts all of them in the scene at once
## so the ETL output can be judged by eye. It is therefore **not** a performance
## measurement — no distance culling, no LOD switching.
##
## `P1-7` changed where the list comes from: the manifest, not a `DirAccess`
## listing of the tile directory. That is the whole gate. Listing `res://` works
## in the editor and returns nothing in an exported build, where it is a PCK, so
## the old path could only ever have previewed the city — never shipped it.
##
## No transforms are applied because none are needed: `buildings.py` writes tile
## vertices in **region** game space, not tile-local space, so a tile dropped at
## the origin already sits where it belongs. That is also why a tile entry
## carries an `aabb` but no position.

## Which tier to show. Range is open because the tier count is city config
## (`lod_cell_sizes_m`); a tile with fewer tiers draws its coarsest.
@export var lod: int = 0

## Emitted once the city is built, with the bounds of everything loaded, so a
## camera can frame whatever region is on disk rather than hardcoding one.
signal built(low: Vector3, high: Vector3)


func _ready() -> void:
	var manifest: CityManifest = CityManifest.load_manifest()
	if manifest == null:
		# `load_manifest` has already pushed the reason and the command to fix it.
		return

	var loaded: int = 0
	var triangles: int = 0
	for tile: CityManifest.Tile in manifest.tiles:
		var path: String = tile.lod(lod)
		var packed := load(path) as PackedScene
		if packed == null:
			push_warning("Could not load %s" % path)
			continue
		var node: Node3D = packed.instantiate()
		node.name = tile.id
		add_child(node)
		loaded += 1
		triangles += _triangles(node)

	print(
		(
			"city preview: %s/%s, %d of %d tiles at LOD%d, %d triangles"
			% [manifest.city_id, manifest.region_id, loaded, manifest.tiles.size(), lod, triangles]
		)
	)
	# The manifest's bounds, not the tiles' — they cover the road surface and the
	# fare nodes too, which are what a camera framing "the region" should see.
	# Free, as well: the old code walked every mesh in the city to learn this.
	#
	# Deferred, and that is not a detail. `_ready` runs children-first, and this
	# node is the *first* child of the preview scenes while the camera is the
	# last — so emitting here directly fires before the camera has connected,
	# reaching nobody and leaving it at the origin looking at the horizon. There
	# is no error to notice: the connection exists, it was just made too late.
	# Deferring puts the emit after every `_ready` in the scene, so the fix
	# survives someone reordering the nodes.
	built.emit.call_deferred(manifest.bounds.position, manifest.bounds.end)


func _triangles(node: Node3D) -> int:
	var count: int = 0
	for instance: MeshInstance3D in node.find_children("*", "MeshInstance3D", true, false):
		var mesh := instance.mesh as ArrayMesh
		if mesh == null:
			continue
		for surface: int in mesh.get_surface_count():
			# O(1), and 0 rather than null on a non-indexed surface —
			# `surface_get_arrays(...)[ARRAY_INDEX]` is null there, and decodes
			# every vertex buffer in the city just to count.
			count += mesh.surface_get_array_index_len(surface) / 3
	return count
