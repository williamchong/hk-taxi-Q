class_name CityStreamer
extends Node3D
## The city, resident only where the camera can see it (`P2-1`).
##
## Replaces `tile_preview.gd` on the boot path. That script is a dev tool by its
## own docstring — it instantiates all 65 of Wan Chai's tiles at LOD0, which is
## 989k triangles against a 300k mobile budget, and docs/ARCHITECTURE.md records
## it as the reason "treat any export as a demo, not a build".
##
## Three jobs, and they are separable:
##
## 1. **Decide** — `TileStreaming`, pure and headless-testable. Distance to a
##    tile's published `aabb` picks a tier or `UNLOADED`.
## 2. **Fetch** — `ResourceLoader.load_threaded_request`, so the disk read and
##    the mesh parse happen off the main thread.
## 3. **Instantiate** — main-thread work, budgeted per frame, because
##    `PackedScene.instantiate` and `add_child` cannot be moved off it.
##
## The acceptance criterion "a distant tile is rejected by its `aabb` before its
## mesh is loaded" is structural rather than promised: step 1 has no access to a
## path, and step 2 only ever sees tiles step 1 already wanted.
##
## No transforms are applied to a tile, and none are needed — `buildings.py`
## writes tile vertices in **region** game space, so a tile added at the origin
## already sits where it belongs. That is also why a tile entry publishes an
## `aabb` but no position.
##
## ⚠️ **Tiles carry no collision, and this does not add any.** See
## docs/PROGRESS.md for the decision and what it measured; the short version is
## that a building collider is an ETL product, not a runtime one.

## Distance bands, hysteresis and the per-frame budgets. Assign in the scene.
@export var profile: StreamingProfile

## What the streaming distance is measured from. The chase camera, not the car:
## the camera is what has a far plane, and a look-back swings it a car length
## the other way.
@export var camera_path: NodePath

## Emitted once the first pass has settled, with the manifest's bounds — the
## same contract `tile_preview.gd` offers, so a camera can frame the region
## without either knowing which of the two built it.
signal built(low: Vector3, high: Vector3)


## One tile's residency. Mirrors a `CityManifest.Tile` by index.
class Resident:
	extends RefCounted

	## Tier currently in the tree, or `TileStreaming.UNLOADED`.
	var tier: int = TileStreaming.UNLOADED
	## Tier being fetched, or `TileStreaming.UNLOADED` when nothing is in flight.
	##
	## The path is not held beside it: it is `tiles[index].lod(pending_tier)` and
	## `lod()` clamps deterministically, so a second field could only ever agree
	## or be a bug. One predicate, one spelling.
	var pending_tier: int = TileStreaming.UNLOADED
	## Tier whose load failed, so a broken asset is reported once instead of
	## re-requested every frame for the life of the process.
	var failed_tier: int = TileStreaming.UNLOADED
	var node: Node3D = null


var _manifest: CityManifest = null
var _residents: Array[Resident] = []
var _loads_in_flight: int = 0
var _wanted_last_pass: int = 0
var _announced: bool = false


func _ready() -> void:
	_manifest = CityManifest.load_manifest()
	if _manifest == null:
		# `load_manifest` has already pushed the reason and the command to fix it.
		return
	if not TileStreaming.is_usable(profile):
		# Refused rather than defaulted. An unassigned profile is all-zeroes,
		# which is a policy that unloads the entire city — and it would look
		# exactly like a region that failed to build.
		push_error(
			(
				(
					"CityStreamer has no usable StreamingProfile; %d tiles will not stream. "
					+ "Assign game/tuning/streaming.tres in the scene."
				)
				% _manifest.tiles.size()
			)
		)
		return

	_residents.resize(_manifest.tiles.size())
	for index: int in _residents.size():
		_residents[index] = Resident.new()


func _process(_delta: float) -> void:
	if _manifest == null or _residents.is_empty():
		return
	var camera: Node3D = get_node_or_null(camera_path) as Node3D
	if camera == null:
		return

	var eye: Vector3 = camera.global_position
	_collect(eye)
	_settle(eye)


## Apply the policy: drop what is out of range, and queue what is not resident
## at the tier it should be.
func _collect(eye: Vector3) -> void:
	var wanted: Array[Vector2i] = []
	var distances: PackedFloat32Array = PackedFloat32Array()

	for index: int in _residents.size():
		var resident: Resident = _residents[index]
		# The rejection, and it happens here — on the `aabb` the manifest
		# published, with no file named and nothing loaded.
		var distance: float = TileStreaming.plan_distance_to(_manifest.tiles[index].aabb, eye)
		var tier: int = TileStreaming.tier_for(distance, resident.tier, profile)

		if tier == TileStreaming.UNLOADED:
			_release(resident)
			continue
		if tier == resident.tier or tier == resident.pending_tier:
			continue
		if tier == resident.failed_tier:
			# Asked for once and refused. Without this a single missing or corrupt
			# tile is re-requested every frame for the life of the process, taking
			# a `push_warning` and one of the in-flight slots with it each time.
			continue
		wanted.append(Vector2i(index, tier))
		distances.append(distance)

	# Recorded so `_settle` can tell "nothing left to want" from "nothing in
	# flight *this instant*". The budget check below can return having requested
	# none of what it wanted, and an empty in-flight set at that moment does not
	# mean the city has arrived.
	_wanted_last_pass = wanted.size()

	# Nearest first: the load budget is small enough to exhaust in one pass, so
	# requesting in manifest order would spend it on whichever tiles happen to be
	# early in the file, leaving a hole next to the car while a tile 300 m away
	# loads. Sorting indices keeps the packed arrays the loop above filled.
	var order: Array[int] = []
	for slot: int in distances.size():
		order.append(slot)
	order.sort_custom(func(a: int, b: int) -> bool: return distances[a] < distances[b])

	for slot: int in order:
		if _loads_in_flight >= profile.max_loads_in_flight:
			return
		_request(wanted[slot].x, wanted[slot].y)


func _request(index: int, tier: int) -> void:
	var resident: Resident = _residents[index]
	if resident.pending_tier != TileStreaming.UNLOADED:
		# A tier change while the previous fetch is still running. `ResourceLoader`
		# has no cancel, so the in-flight one is left to finish; `_settle` drops it
		# on arrival if it is no longer the tier wanted.
		return
	var path: String = _manifest.tiles[index].lod(tier)
	if path.is_empty():
		# `CityManifest` has already pushed which tile. Loading "" would add a
		# hard error naming neither the tile nor the manifest.
		resident.failed_tier = tier
		return
	if ResourceLoader.load_threaded_request(path, "PackedScene") != OK:
		push_warning("Could not request %s" % path)
		resident.failed_tier = tier
		return
	resident.pending_tier = tier
	_loads_in_flight += 1


## Take delivery of whatever finished, up to the per-frame instantiation budget.
func _settle(eye: Vector3) -> void:
	var instantiated: int = 0
	for index: int in _residents.size():
		var resident: Resident = _residents[index]
		if resident.pending_tier == TileStreaming.UNLOADED:
			continue

		var path: String = _manifest.tiles[index].lod(resident.pending_tier)
		var status: ResourceLoader.ThreadLoadStatus = ResourceLoader.load_threaded_get_status(path)
		if status == ResourceLoader.THREAD_LOAD_IN_PROGRESS:
			continue
		if status != ResourceLoader.THREAD_LOAD_LOADED:
			push_warning("Could not load %s" % path)
			# Collected even though it failed. `load_threaded_get` is the only
			# call that releases the task — `load_threaded_get_status` does not —
			# so skipping it here pins the request for the life of the process.
			ResourceLoader.load_threaded_get(path)
			resident.failed_tier = resident.pending_tier
			_clear_pending(resident)
			continue

		# Wanted at this tier still? The camera may have moved while it loaded.
		var distance: float = TileStreaming.plan_distance_to(_manifest.tiles[index].aabb, eye)
		var want: int = TileStreaming.tier_for(distance, resident.tier, profile)
		# Checked before the budget: an arrival nobody wants costs nothing to drop
		# and should not consume an instantiation slot to find that out.
		if want == TileStreaming.UNLOADED:
			ResourceLoader.load_threaded_get(path)
			_clear_pending(resident)
			_release(resident)
			continue
		# A superseded tier, and something is already drawn here — genuinely
		# discard it and let the next `_collect` request the tier now wanted.
		# When nothing is drawn yet, take it anyway: a stale tier beats a hole,
		# which is the same trade the overlap-before-free below makes.
		if want != resident.pending_tier and resident.node != null:
			ResourceLoader.load_threaded_get(path)
			_clear_pending(resident)
			continue
		if instantiated >= profile.max_instantiations_per_frame:
			# Ready but not collected. Deliberately left in `ResourceLoader`'s
			# hands until a later frame rather than pulled and queued here,
			# which would move the memory without moving the work.
			continue

		var packed := ResourceLoader.load_threaded_get(path) as PackedScene
		var tier: int = resident.pending_tier
		_clear_pending(resident)
		if packed == null:
			resident.failed_tier = tier
			continue

		var node: Node3D = packed.instantiate()
		node.name = "%s_lod%d" % [_manifest.tiles[index].id, tier]
		add_child(node)
		instantiated += 1

		# The new tier is in the tree before the old one leaves, so a tier swap
		# never opens a hole. They overlap for one frame at a cost of one extra
		# draw call, which is the cheaper artefact by a wide margin — the
		# alternative is a building blinking out and back as you drive past it.
		if resident.node != null:
			resident.node.queue_free()
		resident.node = node
		resident.tier = tier

	# `_wanted_last_pass` as well as the in-flight count: `_collect` can exhaust
	# its budget and return having requested nothing, so an empty in-flight set
	# on its own would announce a city that is mostly still unrequested. That is
	# reachable from `streaming.tres` alone, whenever `max_loads_in_flight` is no
	# greater than `max_instantiations_per_frame`.
	if not _announced and _loads_in_flight == 0 and _wanted_last_pass == 0:
		_announced = true
		# Deferred for the reason `tile_preview.gd` records: `_ready` runs
		# children-first, so a camera that connects later than this node would
		# miss a direct emit and stay at the origin. There is no error to
		# notice — the connection exists, it was just made too late.
		built.emit.call_deferred(_manifest.bounds.position, _manifest.bounds.end)


## Collect anything still in flight, so it is not pinned in `ResourceLoader`.
##
## Only `load_threaded_get` releases a threaded-load task, and nothing else in
## the engine does it on the caller's behalf. Today this shows up only as an
## exit-time leak warning, because the game boots into one scene and never
## changes it; it becomes a per-transition leak the moment there is a menu, a
## restart, or a second region.
func _exit_tree() -> void:
	for index: int in _residents.size():
		var resident: Resident = _residents[index]
		if resident.pending_tier == TileStreaming.UNLOADED:
			continue
		ResourceLoader.load_threaded_get(_manifest.tiles[index].lod(resident.pending_tier))
		_clear_pending(resident)


func _clear_pending(resident: Resident) -> void:
	resident.pending_tier = TileStreaming.UNLOADED
	_loads_in_flight -= 1


func _release(resident: Resident) -> void:
	if resident.node != null:
		resident.node.queue_free()
		resident.node = null
	resident.tier = TileStreaming.UNLOADED
