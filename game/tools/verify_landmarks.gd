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

## The fallback when an entry carries no `triangle_budget` of its own:
## ART_DESIGN.md's authored-hero budget, mirrored in
## `etl/tests/test_make_landmark.py`, which grades the generator where this
## grades the shipped import. Mesh-sourced heroes ship their measured ceiling
## in the entry (`P3-6` amendment), so the constant never grades them.
const DEFAULT_TRIANGLE_BUDGET: int = 8000

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

	# That the manifest and the locator name the same existing file is
	# `verify_city.gd`'s check, with the other three documents.
	var problems: PackedStringArray = []
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
	# The excluded building took the tile collider on its footprint with it, so
	# a hero without its own is a building the taxi drives through — visible in
	# nothing but a drive. `check_collision` rather than `has_collision` for the
	# richer report, the same reason `verify_tiles.gd` uses it.
	var collision: PackedStringArray = MeshContract.check_collision(node)
	node.free()

	if measured.size == Vector3.ZERO:
		problems.append("%s: %s carries no mesh to measure" % [landmark_id, asset])
		return problems
	var budget: int = int(entry.get("triangle_budget", DEFAULT_TRIANGLE_BUDGET))
	if triangles > budget:
		problems.append("%s: %d triangles against the %d budget" % [landmark_id, triangles, budget])
	for problem: String in collision:
		problems.append("%s: %s" % [landmark_id, problem])

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
	var footprint: Variant = GeneratedLandmarks.excluded_bounds_of(entry)
	if footprint == null:
		return ["%s: no usable excluded_bounds to probe" % landmark_id]
	var box: AABB = footprint as AABB

	var centre: Vector3 = box.get_center()
	var core_low := Vector3(
		centre.x - box.size.x / 4.0,
		box.position.y + STREETSCAPE_CLEARANCE_M,
		centre.z - box.size.z / 4.0
	)
	var core_high := Vector3(centre.x + box.size.x / 4.0, box.end.y, centre.z + box.size.z / 4.0)
	if core_high.y <= core_low.y:
		return ["%s: excluded_bounds too shallow to probe above the streetscape" % landmark_id]
	var core: AABB = Manifest.box(core_low, core_high)

	var intruders: int = 0
	for tile: Manifest.Tile in manifest.tiles:
		if not tile.aabb.intersects(core):
			continue
		var packed := load(tile.lod(0)) as PackedScene
		if packed == null:
			return ["%s: tile %s did not load for probing" % [landmark_id, tile.id]]
		var node: Node3D = packed.instantiate()
		intruders += MeshContract.triangles_inside(node, core)
		node.free()

	if intruders > 0:
		return [
			(
				"%s: %d tile triangles stand inside the excluded core %s — stale tiles?"
				% [landmark_id, intruders, core]
			)
		]
	return []
