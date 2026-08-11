## Checks `landmarks.json` against the assets and tiles it implicates (`P3-6`).
##
##     godot --headless --path game --script res://tools/verify_landmarks.gd
##
## The acceptance criterion is "source geometry excluded; no z-fighting", and
## its two halves live in different places. The *identity* half — every stem a
## landmark claims was actually dropped, and nothing was dropped without a
## claimant — is `export.py::validate`'s, because tiles carry no per-building
## ids an engine could read. The *geometry* half is here: the shipped tier-0
## tiles must contain no triangles where the excluded building's own mass
## stood, which is what catches a bundle whose manifest says "excluded" over
## tiles synced from an older build.
##
## The probe box is the **interior core** of each `excluded_bounds`, not the
## whole of it, because the whole is honestly occupied at its edges: the two
## datasets register to ~0.1 m, so a neighbour's shared wall clips the AABB's
## rim (HKCEC Phase 1 overlaps its corner by metres), and the streetscape that
## legitimately remains — terrain, footbridges — fills its bottom band. Half
## the plan extents about the centre, floored above that streetscape, is space
## only the excluded building itself occupied.
extends SceneTree

const GeneratedLandmarks = preload("res://scripts/city/generated_landmarks.gd")
const Manifest = preload("res://scripts/city/city_manifest.gd")
const MeshContract = preload("res://scripts/city/mesh_contract.gd")

## ART_DESIGN.md's hero budget — mirrored in `etl/tests/test_make_landmark.py`,
## which grades the generator where this grades the shipped import.
const TRIANGLE_BUDGET: int = 8000

## How far above the excluded footprint's base the probe starts. What remains
## inside a footprint legitimately: the terrain (≤ 7.5 m elevation on this
## region's reclamation) and INFRASTRUCTURE spans — the Central Plaza
## footbridge tops out at 13.6 m. Buildings are the only class taller, and
## they are what the probe is for.
const STREETSCAPE_CLEARANCE_M: float = 16.0

## How far a placed hero may stand outside `bounds_game` before it counts as
## misplaced. Two honest sources of overhang: the plinth runs up to 2 m proud
## of the source footprint, and rotating the massing by its bearing swings the
## model's AABB corners past the source mesh's axis-aligned one — measured at
## ~11 m on HKCEC's 349 m length at 6.4°. Real placement failures (a dropped
## offset, a transposed basis) miss by tens to hundreds of metres, so the
## slack costs the check nothing it was catching.
const PLACEMENT_ALLOWANCE_M: float = 15.0


func _init() -> void:
	var manifest: Manifest = Manifest.load_manifest()
	if manifest == null:
		quit(1)
		return

	var problems: PackedStringArray = []
	if manifest.landmarks_path != GeneratedLandmarks.PATH:
		problems.append(
			(
				"city.json says %s, the locator says %s"
				% [manifest.landmarks_path, GeneratedLandmarks.PATH]
			)
		)

	var document: Dictionary = GeneratedLandmarks.load_landmarks()
	if document.is_empty():
		# `load_landmarks` pushed the reason; an empty document is not a pass.
		quit(1)
		return

	var entries: Array = document.get("landmarks", []) as Array
	for entry: Dictionary in entries:
		var found: PackedStringArray = _check_landmark(manifest, entry)
		if found.is_empty():
			print("  ok    ", entry.get("id"))
		else:
			problems.append_array(found)

	for problem: String in problems:
		printerr("  FAIL  ", problem)
	print(
		(
			"%s/%s: %d landmarks checked, %d problem(s)"
			% [manifest.city_id, manifest.region_id, entries.size(), problems.size()]
		)
	)
	quit(1 if not problems.is_empty() else 0)


func _check_landmark(manifest: Manifest, entry: Dictionary) -> PackedStringArray:
	var problems: PackedStringArray = []
	var landmark_id: String = str(entry.get("id", ""))

	var asset: String = str(entry.get("asset", ""))
	var packed := load(asset) as PackedScene
	if packed == null:
		problems.append("%s: %s did not load as a scene" % [landmark_id, asset])
		return problems

	var node: Node3D = packed.instantiate()
	var measured: AABB = MeshContract.bounds(node)
	var triangles: int = MeshContract.triangles(node)
	var collides: bool = MeshContract.has_collision(node)
	node.free()

	if measured.size == Vector3.ZERO:
		problems.append("%s: %s carries no mesh to measure" % [landmark_id, asset])
		return problems
	if triangles > TRIANGLE_BUDGET:
		problems.append(
			"%s: %d triangles against the %d budget" % [landmark_id, triangles, TRIANGLE_BUDGET]
		)
	# The excluded building took the tile collider on its footprint with it, so
	# a hero without its own is a building the taxi drives through — visible in
	# nothing but a drive.
	if not collides:
		problems.append("%s: no collision — the model needs a -col node" % landmark_id)

	var placement: Variant = GeneratedLandmarks.placement_of(entry)
	if placement == null:
		problems.append("%s: no usable transform" % landmark_id)
		return problems
	var placed: AABB = (placement as Transform3D) * measured
	if not manifest.bounds.grow(PLACEMENT_ALLOWANCE_M).encloses(placed):
		problems.append(
			(
				"%s: placed model spans %s, outside bounds_game %s"
				% [landmark_id, placed, manifest.bounds]
			)
		)

	problems.append_array(_probe_tiles(manifest, entry, landmark_id))
	return problems


## No tier-0 tile triangle may stand in the excluded footprint's interior core.
func _probe_tiles(manifest: Manifest, entry: Dictionary, landmark_id: String) -> PackedStringArray:
	var corners: Array = (
		entry.get("excluded_bounds", []) if entry.get("excluded_bounds") is Array else []
	)
	if corners.size() != 2:
		return ["%s: no usable excluded_bounds to probe" % landmark_id]
	var low: Vector3 = Manifest._point(corners[0])
	var high: Vector3 = Manifest._point(corners[1])

	var centre: Vector3 = (low + high) / 2.0
	var core_low := Vector3(
		centre.x - (high.x - low.x) / 4.0,
		low.y + STREETSCAPE_CLEARANCE_M,
		centre.z - (high.z - low.z) / 4.0
	)
	var core_high := Vector3(
		centre.x + (high.x - low.x) / 4.0, high.y, centre.z + (high.z - low.z) / 4.0
	)
	if core_high.y <= core_low.y:
		return ["%s: excluded_bounds too shallow to probe above the streetscape" % landmark_id]
	var core := AABB(core_low, core_high - core_low)

	var intruders: int = 0
	for tile: Manifest.Tile in manifest.tiles:
		if not tile.aabb.intersects(core):
			continue
		var packed := load(tile.lod(0)) as PackedScene
		if packed == null:
			return ["%s: tile %s did not load for probing" % [landmark_id, tile.id]]
		var node: Node3D = packed.instantiate()
		intruders += _triangles_inside(node, core)
		node.free()

	if intruders > 0:
		return [
			(
				"%s: %d tile triangles stand inside the excluded core %s — stale tiles?"
				% [landmark_id, intruders, core]
			)
		]
	return []


func _triangles_inside(node: Node, core: AABB) -> int:
	var count: int = 0
	for instance: MeshInstance3D in node.find_children("*", "MeshInstance3D", true, false):
		var mesh: Mesh = instance.mesh
		if mesh == null:
			continue
		# Tiles are authored in region space at identity, but that is a fact
		# about today's importer output — accumulate the transforms anyway, the
		# way `MeshContract._collect` does, so a wrapper node cannot silently
		# turn this probe into a no-op.
		var to_region: Transform3D = _to_root(instance, node)
		for surface: int in mesh.get_surface_count():
			var arrays: Array = mesh.surface_get_arrays(surface)
			var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
			if indices.is_empty():
				for i: int in range(0, vertices.size(), 3):
					var centroid: Vector3 = (vertices[i] + vertices[i + 1] + vertices[i + 2]) / 3.0
					if core.has_point(to_region * centroid):
						count += 1
			else:
				for i: int in range(0, indices.size(), 3):
					var centroid: Vector3 = (
						(vertices[indices[i]] + vertices[indices[i + 1]] + vertices[indices[i + 2]])
						/ 3.0
					)
					if core.has_point(to_region * centroid):
						count += 1
	return count


func _to_root(instance: Node3D, top: Node) -> Transform3D:
	var accumulated := Transform3D.IDENTITY
	var current: Node = instance
	while current != top and current is Node3D:
		accumulated = (current as Node3D).transform * accumulated
		current = current.get_parent()
	return accumulated
