extends Node3D
## Instantiates every tile `city.json` names, for looking at the whole city.
##
## A dev tool, not the streamer. `CityStreamer` (`P2-1`) will load tiles by
## distance from the same manifest; this puts all of them in the scene at once
## so the ETL output can be judged by eye. It is therefore **not** a performance
## measurement — no distance culling, no LOD switching.
##
## No transforms are applied because none are needed: `buildings.py` writes tile
## vertices in **region** game space, not tile-local space, so a tile dropped at
## the origin already sits where it belongs. That is also why a tile entry
## carries an `aabb` but no position.

const MeshContract = preload("res://scripts/city/mesh_contract.gd")

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
		if path.is_empty():
			# `CityManifest` has already pushed which tile, and `load("")` would
			# only add a hard error naming neither the tile nor the manifest.
			continue
		var packed := load(path) as PackedScene
		if packed == null:
			push_warning("Could not load %s" % path)
			continue
		var node: Node3D = packed.instantiate()
		node.name = tile.id
		add_child(node)
		loaded += 1
		triangles += MeshContract.triangles(node)

	print(
		(
			"city preview: %s/%s, %d of %d tiles at LOD%d, %d triangles"
			% [manifest.city_id, manifest.region_id, loaded, manifest.tiles.size(), lod, triangles]
		)
	)
	# The manifest's bounds, not the loaded tiles' — they cover the road surface
	# and the fare nodes too, which are what a camera framing "the region"
	# should see. Emitted even if every tile failed to load, so a broken asset
	# directory still frames the region the manifest describes rather than
	# leaving the camera at the origin.
	#
	# Deferred, and that is not a detail. `_ready` runs children-first, and this
	# node is the *first* child of the preview scenes while the camera is the
	# last — so emitting here directly fires before the camera has connected,
	# reaching nobody and leaving it at the origin looking at the horizon. There
	# is no error to notice: the connection exists, it was just made too late.
	# Deferring puts the emit after every `_ready` in the scene, so the fix
	# survives someone reordering the nodes.
	built.emit.call_deferred(manifest.bounds.position, manifest.bounds.end)
