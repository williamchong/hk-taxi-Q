## The parked roster, stood by the hour (`P3-73`, `Q161`).
##
## Reads a region's `parked_placements.json` — the document `pipeline/parked.py`
## writes over the AUTHORED library `assets/authored/vehicles/parked.glb`, one
## mesh per kind — and stands each placement as the lamps are stood (`P3-67`):
## a `MultiMesh` per kind per plan cell, hidden past the profile's range, with
## a `BoxShape3D` body per vehicle (`Q159`) so the car cannot drive through a
## parked bus and the near miss (`P3-2a`) has a body to pass.
##
## **The hour decides who stands.** Every placement carries `hours` and a
## `chance` (`ParkedRoster`), read against the lighting rig's `time_of_day`
## (`Q160`) — a van by day, the fill on a single yellow at night, a bus at a
## stop a third of the time. 🔴 **A cell is only ever rebuilt while it is
## hidden**, past `range_m` from the camera: a vehicle appearing or leaving in
## view is a pop, and the street the player can see never changes under them.
## A hidden cell rebuilds when the clock has crossed into another hour since
## it was built, or — for a cell holding a placement with a chance under 1 —
## after `reroll_s`, so the next drive down the street finds a different bus.
##
## ⚠️ **This is not a `layer_preview` row** (`generated_layer.gd`): that table's
## library lives in the region's bundle and this one is committed, and that
## placer stands everything once where this one stands by the hour. It takes
## the same document shape and the same batching (`PropBatch`), which is the
## sharing that matters; `verify_city.gd` holds the manifest's document to
## `placements_path`, and `region.md` says why the node is here.
extends Node3D

const CityManifestScript = preload("res://scripts/city/city_manifest.gd")
const GeneratedPlacements = preload("res://scripts/city/generated_placements.gd")
const GeneratedRegions = preload("res://scripts/city/generated_regions.gd")
const ParkedRoster = preload("res://scripts/city/parked_roster.gd")
const PropBatch = preload("res://scripts/city/prop_batch.gd")

## The document's name in a region's bundle. Mirrors `PARKED_PLACEMENTS_NAME`
## in `etl/pipeline/parked.py`.
const FILE: String = "parked_placements.json"

## The group every region's layer joins, so `FareSystem` can ask each for the
## vehicles near the car without a wired path.
const GROUP: StringName = &"parked_layer"
## Side of the plan bucket `near` walks: a few vehicles a bucket, nine
## buckets a query at the fare loop's radius.
const NEAR_BUCKET_M: float = 40.0

## Which synced region's roster; "" is `GeneratedRegions.selected()`. Set by
## `CityRegions` before the node enters the tree (`P5-9c`).
@export var region: String = ""


## One placement, decoded once.
class Entry:
	extends RefCounted
	var mesh_name: String = ""
	var at: Transform3D = Transform3D.IDENTITY
	var hours: Array = []
	var chance: float = 1.0
	var kind: String = ""
	## What `near` hands out, made once: the GLOBAL transform and an id unique
	## across regions (two layers both number from 0).
	var obstacle: Dictionary = {}


## One plan cell's vehicles and the node they stand under.
class Cell:
	extends RefCounted
	var id: Vector2i = Vector2i.ZERO
	var indices: PackedInt32Array = []
	var node: Node3D = null
	var built_hour: int = -1
	var built_at_s: float = 0.0
	var has_chance: bool = false
	var standing: PackedInt32Array = []


var _profile: ParkedProfile = null
var _meshes: Dictionary[String, Mesh] = {}
var _extents: Dictionary[String, AABB] = {}
var _entries: Array[Entry] = []
var _cells: Dictionary[Vector2i, Cell] = {}
## Entry indices by a fine plan bucket (`NEAR_BUCKET_M`), for `near`: the
## 300 m cell is sized for the visibility range, not for a query the fare
## loop makes every physics tick.
var _buckets: Dictionary[Vector2i, PackedInt32Array] = {}
## Whether each entry stands this hour — what `near` answers from.
var _up: PackedByteArray = []
var _roll: int = 0
## Whether the first poll has run — see `_process` — and the hour the roster
## was first built at, so the re-stand is reported only when it moved.
var _settled: bool = false
var _boot_hour: int = -1
var _since_poll_s: float = 0.0
var _clock_s: float = 0.0
## The hour the roster last stood at, for the boot line and the verify tool,
## and how many vehicles stand — one box body each.
var hour: float = 0.0
var standing: int = 0


## Where a region's copy is; `GeneratedRegions.selected()` for "".
static func placements_path(region_id: String = "") -> String:
	return GeneratedRegions.dir(region_id) + FILE


func _ready() -> void:
	add_to_group(GROUP)
	var manifest: CityManifest = CityManifestScript.shared(region)
	if manifest == null:
		return
	if manifest.parked_placements_path.is_empty():
		# The honest answer for a city with no `parked:` block, on the
		# tramway's terms — distinguishable from a stage that never ran, which
		# `verify_city.gd` catches through the manifest.
		print("parked: none shipped for this region")
		return
	var document: Dictionary = GeneratedPlacements.load_placements(
		manifest.parked_placements_path, "parked vehicles"
	)
	if document.is_empty():
		return
	_profile = load(ParkedProfile.PATH) as ParkedProfile
	if _profile == null or not _usable(_profile):
		return
	var library_path: String = String(document.get("library", ""))
	var packed := load(library_path) as PackedScene
	if packed == null:
		push_error("parked: library %s did not load as a scene" % library_path)
		return
	var library: Node3D = packed.instantiate()
	for node: Node in library.find_children("*", "MeshInstance3D", true, false):
		var found := node as MeshInstance3D
		if found.mesh != null:
			_meshes[String(found.name)] = found.mesh
			_extents[String(found.name)] = found.mesh.get_aabb()
	library.free()

	var no_mesh: int = 0
	var no_transform: int = 0
	for raw: Dictionary in document.get("placements", []) as Array:
		var entry := Entry.new()
		entry.mesh_name = String(raw.get("mesh", ""))
		if not _meshes.has(entry.mesh_name):
			no_mesh += 1
			continue
		var placed: Variant = GeneratedPlacements.placement_of(raw)
		if placed == null:
			no_transform += 1
			continue
		entry.at = placed as Transform3D
		entry.hours = raw.get("hours") if raw.get("hours") is Array else []
		entry.chance = clampf(float(raw.get("chance", 1.0)), 0.0, 1.0)
		entry.kind = String(raw.get("kind", entry.mesh_name))
		var index: int = _entries.size()
		entry.obstacle = {
			"transform": global_transform * entry.at,
			"extent": _extents[entry.mesh_name],
			"id": hash(Vector2i(int(get_instance_id() & 0x7FFFFFFF), index)),
		}
		_entries.append(entry)
		var bucket: Vector2i = ParkedRoster.cell_of(entry.at.origin, NEAR_BUCKET_M)
		if not _buckets.has(bucket):
			_buckets[bucket] = PackedInt32Array()
		_buckets[bucket].append(index)
		var id: Vector2i = ParkedRoster.cell_of(entry.at.origin, _profile.cell_m)
		if not _cells.has(id):
			var cell := Cell.new()
			cell.id = id
			_cells[id] = cell
		_cells[id].indices.append(index)
		if entry.chance < 1.0:
			_cells[id].has_chance = true
	if no_mesh > 0:
		push_error("parked: %d placements name no library mesh" % no_mesh)
	if no_transform > 0:
		push_error("parked: %d placements carry no usable transform" % no_transform)

	hour = _hour_now()
	_boot_hour = floori(hour)
	_up.resize(_entries.size())
	_up.fill(0)
	for cell: Cell in _cells.values():
		_build(cell)
	print(
		(
			"parked: %d placements over %d kinds in %d cells, %d standing at %.1f h, a collider each"
			% [_entries.size(), _meshes.size(), _cells.size(), standing, hour]
		)
	)


## Every required number present, or the reason pushed and nothing stood.
static func _usable(profile: ParkedProfile) -> bool:
	var required: Dictionary[String, float] = {
		"clock_end_h": profile.clock_end_h,
		"cell_m": profile.cell_m,
		"range_m": profile.range_m,
		"poll_s": profile.poll_s,
		"reroll_s": profile.reroll_s,
	}
	if TuningTable.any_zero(profile, required, "ParkedLayer", "no vehicle will stand"):
		return false
	if profile.clock_end_h <= profile.clock_start_h:
		push_error(
			(
				"ParkedLayer: %s clock_end_h (%.1f) is not after clock_start_h (%.1f); no vehicle will stand"
				% [profile.resource_path, profile.clock_end_h, profile.clock_start_h]
			)
		)
		return false
	return true


## The rig's hour, or the clock's start where no rig runs (a preview, a tool).
func _hour_now() -> float:
	var time_of_day: float = 0.0
	var tree: SceneTree = get_tree()
	if tree != null:
		var rig := tree.get_first_node_in_group(LightingRig.GROUP) as LightingRig
		if rig != null:
			time_of_day = rig.time_of_day
	return ParkedRoster.hour_of(time_of_day, _profile.clock_start_h, _profile.clock_end_h)


func _process(delta: float) -> void:
	if _profile == null:
		return
	_clock_s += delta
	_since_poll_s += delta
	if _settled and _since_poll_s < _profile.poll_s:
		return
	_since_poll_s = 0.0
	hour = _hour_now()
	var camera: Camera3D = get_viewport().get_camera_3d() if get_viewport() != null else null
	if camera == null:
		return
	var eye: Vector3 = to_local(camera.global_transform.origin)
	var far_m: float = _profile.range_m + _profile.range_margin_m
	var this_hour: int = floori(hour)
	var settling: bool = not _settled
	_settled = true
	for cell: Cell in _cells.values():
		var centre: Vector3 = ParkedRoster.cell_centre(cell.id, _profile.cell_m)
		# The first poll may re-stand a cell in view: the roster was built in
		# `_ready`, before a pinned `--time-of-day=` or the clock had reached
		# the rig, and nobody has seen the street yet.
		if not settling and Vector2(eye.x - centre.x, eye.z - centre.z).length() <= far_m:
			continue
		var stale: bool = cell.built_hour != this_hour
		var rerolled: bool = cell.has_chance and _clock_s - cell.built_at_s >= _profile.reroll_s
		if stale or rerolled:
			if rerolled:
				_roll += 1
			_build(cell)
	if settling and floori(hour) != _boot_hour:
		print("parked: re-stood at %.1f h, %d standing" % [hour, standing])


## Stand (or re-stand) one cell for the hour and the roll: its vehicles
## grouped by kind into one `MultiMesh` each, a box body per vehicle.
func _build(cell: Cell) -> void:
	if cell.node != null:
		standing -= cell.standing.size()
		for index: int in cell.standing:
			_up[index] = 0
		# Freed NOW, not queued: a queued free holds the old bodies until the
		# end of the frame, and the first poll re-stands every cell at once —
		# twice the roster's bodies, over Jolt's 10,240 cap with the railings'
		# 7,693 resident.
		cell.node.free()
		cell.node = null
	cell.standing.clear()
	var by_mesh: Dictionary[String, Array] = {}
	for index: int in cell.indices:
		var entry: Entry = _entries[index]
		if not ParkedRoster.present(index, entry.hours, entry.chance, hour, _roll):
			continue
		cell.standing.append(index)
		_up[index] = 1
		if not by_mesh.has(entry.mesh_name):
			by_mesh[entry.mesh_name] = []
		by_mesh[entry.mesh_name].append(entry.at)
	cell.built_hour = floori(hour)
	cell.built_at_s = _clock_s
	var node := Node3D.new()
	node.name = "cell_%d_%d" % [cell.id.x, cell.id.y]
	for mesh_name: String in by_mesh:
		var batch: Array[Transform3D] = []
		batch.assign(by_mesh[mesh_name])
		var drawn: MultiMeshInstance3D = PropBatch.batch(_meshes[mesh_name], batch, mesh_name)
		drawn.visibility_range_end = _profile.range_m
		drawn.visibility_range_end_margin = _profile.range_margin_m
		node.add_child(drawn)
		for body: StaticBody3D in PropBatch.bodies(_extents[mesh_name], batch, mesh_name + "_col"):
			node.add_child(body)
	add_child(node)
	cell.node = node
	standing += cell.standing.size()


## The vehicles standing within `radius_m` of a GLOBAL point, each as
## `{"transform": Transform3D (global), "extent": AABB (the mesh's own),
## "id": int}` — what the near miss passes (`P3-2a`). The fine buckets are
## the index: only those within the radius are walked, and the dictionaries
## were made once in `_ready`.
func near(point: Vector3, radius_m: float) -> Array[Dictionary]:
	var found: Array[Dictionary] = []
	if _profile == null:
		return found
	var local: Vector3 = to_local(point)
	var reach: int = ceili(radius_m / NEAR_BUCKET_M)
	var home: Vector2i = ParkedRoster.cell_of(local, NEAR_BUCKET_M)
	var radius_sq: float = radius_m * radius_m
	for dx: int in range(-reach, reach + 1):
		for dz: int in range(-reach, reach + 1):
			var bucket: PackedInt32Array = _buckets.get(
				Vector2i(home.x + dx, home.y + dz), PackedInt32Array()
			)
			for index: int in bucket:
				if _up[index] == 0:
					continue
				var at: Vector3 = _entries[index].at.origin
				var far_x: float = at.x - local.x
				var far_z: float = at.z - local.z
				if far_x * far_x + far_z * far_z > radius_sq:
					continue
				found.append(_entries[index].obstacle)
	return found


## Every region's layer asked at once — the one call `FareSystem` makes.
static func near_all(tree: SceneTree, point: Vector3, radius_m: float) -> Array[Dictionary]:
	var found: Array[Dictionary] = []
	if tree == null:
		return found
	for node: Node in tree.get_nodes_in_group(GROUP):
		found.append_array(node.near(point, radius_m))
	return found
