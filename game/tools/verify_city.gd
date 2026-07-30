## Checks `city.json` against the geometry it describes, in-engine and headless.
##
## `P1-7`'s acceptance is that the region renders **correctly georeferenced**,
## and that is a claim about two things agreeing: what `export.py` measured, and
## where Godot's glTF importer actually puts the vertices. The ETL cannot check
## the second half and `export.py --check` never sees an importer, so this is
## where the round trip closes. Run:
##
##     godot --headless --path game --script res://tools/verify_city.gd
##
## Complements rather than repeats `verify_tiles.gd`, which checks the *mesh*
## contract — draw calls, vertex colours, no textures — and says nothing about
## position. Exits non-zero on any disagreement.
##
## What it cannot check is z-fighting. That is a depth-buffer artefact at a
## particular camera distance, so it stays an eyeball criterion.
extends SceneTree

const GeneratedFares = preload("res://scripts/city/generated_fares.gd")
const GeneratedRoadGraph = preload("res://scripts/city/generated_road_graph.gd")
const GeneratedRoadSurface = preload("res://scripts/city/generated_road_surface.gd")

## How far a corner may move between the ETL's arithmetic and the imported mesh.
##
## Generous against what causes it: `export.py` measures in float64 and the GLB
## stores float32, which at Wan Chai's ~1.7 km extent costs about 0.1 mm. A
## centimetre therefore catches a real transform — an axis flip, a unit scale, a
## dropped offset — without ever firing on rounding.
const TOLERANCE_M: float = 0.01


func _init() -> void:
	var manifest: CityManifest = CityManifest.load_manifest()
	if manifest == null:
		printerr(CityManifest.missing_hint())
		quit(1)
		return

	var problems: PackedStringArray = _check_documents(manifest)
	var checked: int = 0
	for tile: CityManifest.Tile in manifest.tiles:
		checked += 1
		var found: PackedStringArray = _check_tile(manifest, tile)
		if found.is_empty():
			print("  ok    ", tile.id)
		else:
			problems.append_array(found)

	for problem: String in problems:
		printerr("  FAIL  ", problem)

	print(
		(
			"%s/%s: %d tiles georeferenced, %d files named, %d problem(s)"
			% [
				manifest.city_id,
				manifest.region_id,
				checked,
				manifest.shipped().size(),
				problems.size(),
			]
		)
	)
	quit(1 if not problems.is_empty() else 0)


## The manifest names three documents. Each must be there, and each must be the
## file the dev locators point at — they carry their own constant until `P2-2`
## and `P3-1` take the path from the manifest, and this is what stops the two
## definitions drifting in the meantime.
func _check_documents(manifest: CityManifest) -> PackedStringArray:
	var problems: PackedStringArray = []
	var declared := {
		"road graph": [manifest.road_graph_path, GeneratedRoadGraph.PATH],
		"road surface": [manifest.road_surface_path, GeneratedRoadSurface.PATH],
		"fare nodes": [manifest.fares_path, GeneratedFares.PATH],
	}
	for what: String in declared:
		var pair: Array = declared[what]
		if not FileAccess.file_exists(pair[0]):
			problems.append("%s: city.json names %s, which does not exist" % [what, pair[0]])
		elif pair[0] != pair[1]:
			problems.append("%s: city.json says %s, the locator says %s" % [what, pair[0], pair[1]])
	return problems


func _check_tile(manifest: CityManifest, tile: CityManifest.Tile) -> PackedStringArray:
	var problems: PackedStringArray = []

	if tile.lods.is_empty():
		problems.append("%s names no LOD files" % tile.id)
		return problems

	# Only the containing box is grown, never both. `bounds_game` is the union
	# of these very AABBs, so the extreme tiles touch it exactly on one face —
	# growing the tile too would restore the tie and `encloses` does not treat
	# a shared face as enclosed.
	var declared: AABB = tile.aabb.grow(TOLERANCE_M)
	if not manifest.bounds.grow(TOLERANCE_M).encloses(tile.aabb):
		problems.append(
			"%s: aabb %s is outside bounds_game %s" % [tile.id, tile.aabb, manifest.bounds]
		)

	for tier: int in tile.lods.size():
		var path: String = tile.lods[tier]
		var packed := load(path) as PackedScene
		if packed == null:
			problems.append("%s: %s did not load as a scene" % [tile.id, path])
			continue

		var node: Node3D = packed.instantiate()
		var measured: AABB = _measure(node)
		node.free()

		if measured.size == Vector3.ZERO:
			problems.append("%s: %s carries no mesh to measure" % [tile.id, path])
		elif tier == 0:
			# The manifest's aabb is the full-detail mesh's, so tier 0 must agree
			# corner for corner. Anything else is a transform, not a rounding.
			var drift: float = maxf(
				(measured.position - tile.aabb.position).abs().length(),
				(measured.end - tile.aabb.end).abs().length()
			)
			if drift > TOLERANCE_M:
				problems.append(
					(
						"%s: LOD0 spans %s, city.json says %s (%.3f m out)"
						% [tile.id, measured, tile.aabb, drift]
					)
				)
		elif not declared.encloses(measured):
			# Coarser tiers may shrink — decimation drops vertices — but cannot
			# reach outside the full-detail extent the streamer culls against.
			problems.append(
				"%s: LOD%d spans %s, outside the declared %s" % [tile.id, tier, measured, tile.aabb]
			)

	return problems


## The union of every mesh in `node`, in scene space. A zero-size box means
## nothing was found, which the caller reports rather than passing.
##
## Transforms are accumulated by hand rather than read from
## `Node3D.global_transform`, which returns identity and pushes an error outside
## the tree — and a headless `--script` run has no tree to add to. The importer
## is free to put the mesh under a transformed root, and that is exactly the
## mistake this tool exists to catch, so the parent chain cannot be ignored.
func _measure(node: Node) -> AABB:
	var boxes: Array[AABB] = []
	_collect(node, Transform3D.IDENTITY, boxes)
	if boxes.is_empty():
		# Empty rather than seeded: an AABB starts at the origin, and merging
		# that in would drag the union back there.
		return AABB()

	var bounds: AABB = boxes[0]
	for index: int in range(1, boxes.size()):
		bounds = bounds.merge(boxes[index])
	return bounds


func _collect(node: Node, parent: Transform3D, into: Array[AABB]) -> void:
	var spatial := node as Node3D
	var here: Transform3D = parent * spatial.transform if spatial != null else parent

	var instance := node as MeshInstance3D
	if instance != null and instance.mesh != null:
		into.append(here * instance.mesh.get_aabb())

	for child: Node in node.get_children():
		_collect(child, here, into)
