## Checks `CityStreamer`'s streaming policy against the city it will stream (`P2-1`).
##
##     godot --headless --path game --script res://tools/verify_city_streamer.gd
##
## The fifth verify tool. Like `verify_road_graph.gd` it asserts logic rather
## than the shape of a generated asset, and it can do that headlessly because
## `TileStreaming` is pure — no `Node`, no `load()`, so the whole decision table
## is reachable without a scene, a camera or a rendering device.
##
## Two of `P2-1`'s three acceptance criteria are checkable here. The third — no
## hitching on tile boundaries — is a frame-time property that needs the game
## running, so it is measured from the driver run and recorded in PROGRESS.md
## rather than asserted here. Saying so is the point: a check that quietly
## covered two of three would read as covering all of them.
##
## Exits non-zero if the manifest is missing, the profile is unusable, or any
## check fails.
extends SceneTree

const MeshContract = preload("res://scripts/city/mesh_contract.gd")

const PROFILE_PATH: String = "res://tuning/streaming.tres"

## Mobile draw-call budget from docs/ARCHITECTURE.md "Performance budget", and
## `P2-1`'s acceptance criterion in its own words. One resident tile is one draw
## call by contract — `verify_tiles.gd` checks that side — so counting tiles
## counts calls.
const DRAW_CALL_BUDGET: int = 150

## Resident triangles are **reported, not gated**, and that is deliberate.
##
## The budget beside the draw-call one is 300k *visible* triangles, and resident
## is not visible: the streamer culls to a **disc** around the camera while the
## renderer frustum-culls that to a **cone**, so roughly half the resident set is
## behind the camera and never drawn. Failing a disc figure against a cone
## budget would be comparing two different quantities and calling it a gate —
## and it would push the bands tighter than the frame cost requires, buying
## visible LOD popping for nothing.
##
## What resident triangles *are* is an upper bound, which is worth printing and
## worth recording. `P2-6` turns it into a measured visible figure on the device
## floor; until then the number below is the ceiling that measurement must come
## in under, and PROGRESS.md carries it.
const TRIANGLE_CEILING_NOTE: int = 300000

## Plan step of the camera-position sample, in metres.
const SAMPLE_STEP_M: float = 25.0


func _init() -> void:
	var manifest: CityManifest = CityManifest.load_manifest()
	if manifest == null:
		quit(1)
		return
	var profile := load(PROFILE_PATH) as StreamingProfile
	if profile == null:
		push_error("No StreamingProfile at %s" % PROFILE_PATH)
		quit(1)
		return

	var problems: PackedStringArray = _check(manifest, profile)
	for problem: String in problems:
		printerr("  FAIL  ", problem)
	if problems.is_empty():
		print("  ok    ", PROFILE_PATH)
	quit(1 if not problems.is_empty() else 0)


func _check(manifest: CityManifest, profile: StreamingProfile) -> PackedStringArray:
	var problems: PackedStringArray = []

	if not TileStreaming.is_usable(profile):
		problems.append(
			"the profile is not usable — bands must ascend and stay inside the unload distance"
		)
		return problems
	if manifest.tiles.is_empty():
		problems.append("the manifest names no tiles")
		return problems

	problems.append_array(_check_bands(profile))
	problems.append_array(_check_hysteresis(profile))
	problems.append_array(_check_residency(manifest, profile))
	return problems


## The decision table itself, at the edges where it is defined.
func _check_bands(profile: StreamingProfile) -> PackedStringArray:
	var problems: PackedStringArray = []
	var edges: PackedFloat32Array = profile.tier_distances_m
	var coarsest: int = edges.size()

	# A tile under the camera takes the finest tier, or the streamer has its
	# bands inverted and the city is drawn at its lowest detail up close.
	if TileStreaming.band_of(0.0, profile) != 0:
		problems.append("a tile at 0 m is not at tier 0")
	# Each edge is inclusive, and one micron past it is the next tier along.
	for tier: int in edges.size():
		if TileStreaming.band_of(edges[tier], profile) != tier:
			problems.append("%.1f m is not the outer edge of tier %d" % [edges[tier], tier])
		if TileStreaming.band_of(edges[tier] + 0.001, profile) != tier + 1:
			problems.append("just past %.1f m is still tier %d" % [edges[tier], tier])
	if TileStreaming.band_of(profile.unload_distance_m, profile) != coarsest:
		problems.append("the unload distance is not the outer edge of the coarsest tier")
	if TileStreaming.band_of(profile.unload_distance_m + 0.001, profile) != TileStreaming.UNLOADED:
		problems.append("a tile past the unload distance is still resident")

	# The criterion in its own words: the decision is reachable with nothing but
	# an AABB, so nothing can have been loaded to make it.
	var far_box := AABB(Vector3(9000.0, 0.0, 9000.0), Vector3(150.0, 50.0, 150.0))
	var far_distance: float = TileStreaming.plan_distance_to(far_box, Vector3.ZERO)
	if TileStreaming.band_of(far_distance, profile) != TileStreaming.UNLOADED:
		problems.append("a tile 9 km away is not rejected by its aabb")

	# Inside the box is zero distance, not the distance to its centre or corner.
	var box := AABB(Vector3(0.0, 0.0, 0.0), Vector3(150.0, 60.0, 150.0))
	if TileStreaming.plan_distance_to(box, Vector3(75.0, 200.0, 75.0)) != 0.0:
		problems.append("a camera over a tile is not 0 m from it")
	# Measured in plan: a camera above every roof is still over the tile.
	var beside: float = TileStreaming.plan_distance_to(box, Vector3(-10.0, 0.0, 75.0))
	if absf(beside - 10.0) > 0.001:
		problems.append("a camera 10 m off a tile's edge measured %.3f m" % beside)
	return problems


## Hysteresis holds a tile in the band it is in, and only inside that band.
func _check_hysteresis(profile: StreamingProfile) -> PackedStringArray:
	var problems: PackedStringArray = []
	var margin: float = profile.hysteresis_m
	if margin <= 0.0:
		problems.append("hysteresis is %.1f m — a tile on a band edge will thrash" % margin)
		return problems

	var edge: float = profile.tier_distances_m[0]
	# Just past the edge, a tier-0 tile stays tier 0; a fresh one does not.
	if TileStreaming.tier_for(edge + margin * 0.5, 0, profile) != 0:
		problems.append("a tier-0 tile gives up its tier inside the hysteresis margin")
	if TileStreaming.tier_for(edge + margin * 0.5, TileStreaming.UNLOADED, profile) != 1:
		problems.append("a tile arriving past the edge is loaded at tier 0 anyway")
	# Past the margin it must let go, or the band is unbounded.
	if TileStreaming.tier_for(edge + margin * 2.0, 0, profile) != 1:
		problems.append("a tier-0 tile keeps its tier well past the hysteresis margin")
	# And symmetrically on the way back in.
	if TileStreaming.tier_for(edge - margin * 0.5, 1, profile) != 1:
		problems.append("a tier-1 tile takes a finer tier inside the hysteresis margin")
	if TileStreaming.tier_for(edge - margin * 2.0, 1, profile) != 0:
		problems.append("a tier-1 tile keeps its tier well inside the finer band")
	# A resident tile still unloads once it is far enough out.
	var gone: float = profile.unload_distance_m + margin * 2.0
	if TileStreaming.tier_for(gone, 0, profile) != TileStreaming.UNLOADED:
		problems.append("a resident tile is never unloaded")
	return problems


## What the policy actually makes resident, over the region the car can reach.
##
## Sampled on a lattice rather than at one spawn, because the budget has to hold
## everywhere and the worst case is not where anyone would think to look. The
## figure is resident triangles, which bounds drawn triangles from above.
func _check_residency(manifest: CityManifest, profile: StreamingProfile) -> PackedStringArray:
	var problems: PackedStringArray = []

	# Measured once per tile per tier, not inside the sweep. Every count here is
	# a disk read and a mesh parse, and the sweep asks for them thousands of
	# times over — 195 loads against 165,000.
	# One more than the edge count: the coarsest band sits past the last edge.
	var tiers: int = profile.tier_distances_m.size() + 1
	var counts: Array[PackedInt32Array] = []
	for tile: CityManifest.Tile in manifest.tiles:
		var per_tier := PackedInt32Array()
		for tier: int in tiers:
			per_tier.append(_triangles_of(tile, tier))
		counts.append(per_tier)

	var worst_triangles: int = 0
	var worst_at: Vector3 = Vector3.ZERO
	var most_tiles: int = 0
	var most_tiles_at: Vector3 = Vector3.ZERO
	var total_triangles: int = 0

	# The residency radius, not `unload_distance_m`. A tile already resident keeps
	# its band for another `hysteresis_m`, so sweeping on the profile field alone
	# measures a smaller city than the streamer actually holds.
	var radius: float = TileStreaming.residency_radius_m(profile)
	var lattice: PackedVector3Array = PlanLattice.over(manifest.bounds, SAMPLE_STEP_M)
	for eye: Vector3 in lattice:
		var triangles: int = 0
		var resident: int = 0
		for index: int in manifest.tiles.size():
			var distance: float = TileStreaming.plan_distance_to(manifest.tiles[index].aabb, eye)
			if distance > radius:
				continue
			resident += 1
			triangles += counts[index][mini(TileStreaming.band_of(distance, profile), tiers - 1)]
		total_triangles += triangles
		# Tracked apart, because they peak in different places: a sample beside a
		# few tall towers is triangle-heavy and tile-light, and one in the open is
		# the reverse. Folding them would let the draw-call gate read the tile
		# count from wherever the triangles happened to peak and pass regardless.
		if triangles > worst_triangles:
			worst_triangles = triangles
			worst_at = eye
		if resident > most_tiles:
			most_tiles = resident
			most_tiles_at = eye

	var samples: int = lattice.size()
	if samples == 0:
		problems.append("the residency sweep ran no samples")
		return problems

	print(
		(
			"  streaming: %d samples, worst %s triangles at (%.0f, %.0f), most %d tiles at (%.0f, %.0f), mean %s"
			% [
				samples,
				_thousands(worst_triangles),
				worst_at.x,
				worst_at.z,
				most_tiles,
				most_tiles_at.x,
				most_tiles_at.z,
				_thousands(roundi(float(total_triangles) / float(samples))),
			]
		)
	)

	# Printed, never failed — see TRIANGLE_CEILING_NOTE. A disc figure is not a
	# cone budget, and quietly gating on it would tighten the bands to satisfy an
	# arithmetic mismatch rather than a frame cost.
	if worst_triangles > TRIANGLE_CEILING_NOTE:
		print(
			(
				(
					"  note: worst-case residency %s triangles is above the %s visible budget — "
					% [_thousands(worst_triangles), _thousands(TRIANGLE_CEILING_NOTE)]
				)
				+ "resident bounds visible from above, and P2-6 measures what is drawn"
			)
		)
	# One tile is one draw call by contract — `verify_tiles.gd` checks that side.
	if most_tiles > DRAW_CALL_BUDGET:
		problems.append(
			(
				"worst-case residency is %d tiles at (%.0f, %.0f), over the %d draw-call budget"
				% [most_tiles, most_tiles_at.x, most_tiles_at.z, DRAW_CALL_BUDGET]
			)
		)
	# The sweep must actually load something, or every check above passed on an
	# empty city and the budget was met by streaming nothing.
	if most_tiles == 0:
		problems.append("no sample made a single tile resident")
	return problems


## Triangles in a tile at `tier`, from the LOD0 mesh the manifest names.
##
## Loaded here because triangle counts are not in the data contract — they are
## in `buildings.json`, which docs/ARCHITECTURE.md says nothing in the game may
## read. A verify tool is not the game, but it should not invent a second route
## to the truth either, so it counts the mesh it will actually draw.
func _triangles_of(tile: CityManifest.Tile, tier: int) -> int:
	var path: String = tile.lod(tier)
	if path.is_empty():
		return 0
	var packed := load(path) as PackedScene
	if packed == null:
		return 0
	var node: Node3D = packed.instantiate()
	var triangles: int = MeshContract.triangles(node)
	node.free()
	return triangles


## Digit-grouped, because six-figure triangle counts are the whole output here.
static func _thousands(value: int) -> String:
	var text: String = str(value)
	var out: String = ""
	for index: int in text.length():
		if index > 0 and (text.length() - index) % 3 == 0:
			out += ","
		out += text[index]
	return out
