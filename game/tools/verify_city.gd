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

const GeneratedLayer = preload("res://scripts/city/generated_layer.gd")
const GeneratedFares = preload("res://scripts/city/generated_fares.gd")
const GeneratedFence = preload("res://scripts/city/generated_fence.gd")
const GeneratedLandmarks = preload("res://scripts/city/generated_landmarks.gd")
const GeneratedRoadGraph = preload("res://scripts/city/generated_road_graph.gd")
const Manifest = preload("res://scripts/city/city_manifest.gd")
const MeshContract = preload("res://scripts/city/mesh_contract.gd")

## How far a corner may move between the ETL's arithmetic and the imported mesh.
##
## Generous against what causes it: `export.py` measures in float64 and the GLB
## stores float32, which at Wan Chai's ~1.7 km extent costs about 0.1 mm. A
## centimetre therefore catches a real transform — an axis flip, a unit scale, a
## dropped offset — without ever firing on rounding.
const TOLERANCE_M: float = 0.01

## The two scenes every drawn layer must have a `layer_preview` node in.
## `roadmarks` shipped with a node in neither and `lamps` with a node in the
## preview only, each past a green `check.sh` (`Q73`); the table in
## `generated_layer.gd` is what makes this checkable, in both directions.
const LAYER_SCENES: PackedStringArray = [
	"res://scenes/dev/city_drive.tscn", "res://scenes/dev/city_preview.tscn"
]


func _init() -> void:
	# `load_manifest` has already pushed the reason and the command that fixes
	# it — and for a stale schema that reason is *not* the missing-file hint,
	# so repeating one here would name the wrong fix half the time.
	var manifest: Manifest = Manifest.load_manifest()
	if manifest == null:
		quit(1)
		return

	# A manifest that parses but lists nothing would otherwise report "0 tiles,
	# 0 problems" and exit 0 — the Phase 1 gate passing on an empty city.
	if manifest.tiles.is_empty():
		printerr("  FAIL  %s names no tiles" % Manifest.PATH)
		quit(1)
		return

	var problems: PackedStringArray = _check_documents(manifest)
	problems.append_array(_check_layer_nodes())
	for tile: Manifest.Tile in manifest.tiles:
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
				manifest.tiles.size(),
				manifest.shipped().size(),
				problems.size(),
			]
		)
	)
	quit(1 if not problems.is_empty() else 0)


## The manifest names five documents. Each must be there, and each must be the
## file the dev locators point at — they carry their own constant until `P2-2`
## and `P3-1` take the path from the manifest, and this is what stops the two
## definitions drifting in the meantime.
func _check_documents(manifest: Manifest) -> PackedStringArray:
	var problems: PackedStringArray = []
	problems.append_array(
		_check_document("road graph", manifest.road_graph_path, GeneratedRoadGraph.PATH)
	)
	problems.append_array(
		_check_document(
			"road surface",
			manifest.road_surface_path,
			GeneratedLayer.path(GeneratedLayer.ROAD_SURFACE)
		)
	)
	problems.append_array(_check_document("fare nodes", manifest.fares_path, GeneratedFares.PATH))
	problems.append_array(
		_check_document("landmarks", manifest.landmarks_path, GeneratedLandmarks.PATH)
	)
	# Unguarded, alongside the other four: `pipeline/fence.py` writes its document
	# on every run, so a region with nothing to close names it and carries an
	# empty `barriers` list. A missing file means the stage never ran (`P3-29`).
	problems.append_array(_check_document("fence", manifest.fence_path, GeneratedFence.PATH))
	# ⚠️ **Guarded, because this one is optional and the others are not.** A city
	# whose estate publishes no tramway names `null` and ships none (`P3-14`),
	# so an empty path is the honest answer rather than a missing file. What the
	# guard must not do is let a *named* tramway go unchecked: `verify_tramway.gd`
	# treats an absent asset as a pass, so without this a manifest naming
	# `tram.glb` with the file gone would pass every check in the repo.
	if not manifest.tramway_path.is_empty():
		problems.append_array(
			_check_document(
				"tramway", manifest.tramway_path, GeneratedLayer.path(GeneratedLayer.TRAMWAY)
			)
		)
	# Guarded for the same reason, and with the same thing the guard must not do:
	# `verify_arrows.gd` treats an absent asset as a pass, so a manifest naming
	# `arrows.glb` with the file gone would otherwise pass every check here.
	if not manifest.arrows_path.is_empty():
		problems.append_array(
			_check_document(
				"arrows", manifest.arrows_path, GeneratedLayer.path(GeneratedLayer.ARROWS)
			)
		)
		problems.append_array(
			_check_document(
				"arrow placements",
				manifest.arrows_placements_path,
				GeneratedLayer.placements_path(GeneratedLayer.ARROWS)
			)
		)
	# Guarded on the same terms again: `verify_boxjunctions.gd` treats an absent
	# asset as a pass, so a manifest naming `boxjunctions.glb` with the file gone
	# would otherwise pass every check here.
	if not manifest.railings_path.is_empty():
		problems.append_array(
			_check_document(
				"railings", manifest.railings_path, GeneratedLayer.path(GeneratedLayer.RAILINGS)
			)
		)
		problems.append_array(
			_check_document(
				"railing placements",
				manifest.railings_placements_path,
				GeneratedLayer.placements_path(GeneratedLayer.RAILINGS)
			)
		)
	# Guarded on the same terms: `verify_lamps.gd` treats an absent asset as a
	# pass, so a manifest naming `lamps.glb` with the file gone would otherwise
	# pass every check in the repo. ⚠️ **And a null `lamps` key is a LESS
	# ordinary answer than a null `signals` one** — `UTILITYPOINTTYPE` has a
	# published domain where `REFNAME` has none — so a bundle that names the
	# asset really is expected to hold it.
	if not manifest.lamps_path.is_empty():
		problems.append_array(
			_check_document("lamps", manifest.lamps_path, GeneratedLayer.path(GeneratedLayer.LAMPS))
		)
		problems.append_array(
			_check_document(
				"lamp placements",
				manifest.lamps_placements_path,
				GeneratedLayer.placements_path(GeneratedLayer.LAMPS)
			)
		)
	if not manifest.boxjunctions_path.is_empty():
		problems.append_array(
			_check_document(
				"box junctions",
				manifest.boxjunctions_path,
				GeneratedLayer.path(GeneratedLayer.BOXJUNCTIONS)
			)
		)
	# Guarded on the same terms once more, and this is the guard that matters
	# most: `verify_signs.gd` treats an absent asset as a pass *and* a null
	# `signs` key is an ordinary answer for a region whose signs are all
	# text-faced — so without this a manifest naming `signs.glb` with the file
	# gone would pass every check in the repo.
	if not manifest.signs_path.is_empty():
		problems.append_array(
			_check_document("signs", manifest.signs_path, GeneratedLayer.path(GeneratedLayer.SIGNS))
		)
		# The library's placements, on the library's own terms (`P5-2`): a
		# bundle naming `signs.glb` and not this stands nothing on it.
		problems.append_array(
			_check_document(
				"sign placements",
				manifest.signs_placements_path,
				GeneratedLayer.placements_path(GeneratedLayer.SIGNS)
			)
		)
	# Guarded on the same terms a sixth time: `verify_roadmarks.gd` treats an
	# absent asset as a pass, so a manifest naming `roadmarks.glb` with the file
	# gone would otherwise pass every check here.
	if not manifest.roadmarks_path.is_empty():
		problems.append_array(
			_check_document(
				"road markings",
				manifest.roadmarks_path,
				GeneratedLayer.path(GeneratedLayer.ROADMARKS)
			)
		)
	# Guarded on the same terms a seventh time, and on the sharpest version of
	# the argument: `verify_signals.gd` treats an absent asset as a pass, *and* a
	# null `signals` key is an ordinary answer twice over — for a region whose
	# estate publishes no signal layer, and for one whose publisher spells its
	# codes outside `head_prefixes` (`P3-17`). So without this a manifest naming
	# `signals.glb` with the file gone would pass every check in the repo.
	if not manifest.signals_path.is_empty():
		problems.append_array(
			_check_document(
				"signals", manifest.signals_path, GeneratedLayer.path(GeneratedLayer.SIGNALS)
			)
		)
	return problems


## Every id in `GeneratedLayer.ids()` names a `layer_preview` node in both dev
## scenes, and every such node names an id — read off the `.tscn` text rather
## than by instantiating the game. A misspelt `layer = "lampz"` would otherwise
## draw nothing and push one error at runtime that no check reads.
func _check_layer_nodes() -> PackedStringArray:
	var problems: PackedStringArray = []
	var pattern := RegEx.new()
	pattern.compile('(?m)^layer = "([^"]*)"$')
	var ids: PackedStringArray = GeneratedLayer.ids()
	for scene: String in LAYER_SCENES:
		var text: String = FileAccess.get_file_as_string(scene)
		if text.is_empty():
			problems.append("%s could not be read" % scene)
			continue
		var named: PackedStringArray = []
		for hit: RegExMatch in pattern.search_all(text):
			named.append(hit.get_string(1))
		for id: String in ids:
			if not named.has(id):
				problems.append("%s has no layer_preview node for %s" % [scene, id])
		for id: String in named:
			if not ids.has(id):
				problems.append(
					"%s names a layer %s that generated_layer.gd does not" % [scene, id]
				)
	if problems.is_empty():
		print("  ok    %d layer nodes in each of %d scenes" % [ids.size(), LAYER_SCENES.size()])
	return problems


func _check_document(what: String, named: String, locator: String) -> PackedStringArray:
	if not FileAccess.file_exists(named):
		return ["%s: city.json names %s, which does not exist" % [what, named]]
	if named != locator:
		return ["%s: city.json says %s, the locator says %s" % [what, named, locator]]
	return []


func _check_tile(manifest: Manifest, tile: Manifest.Tile) -> PackedStringArray:
	var problems: PackedStringArray = []

	if tile.lods.is_empty():
		problems.append("%s names no LOD files" % tile.id)
		return problems

	# Grown on the containing side only, never on both. `encloses` does accept a
	# shared face, so a tie is not the problem — growing both simply cancels,
	# leaving no tolerance at all for the millimetre rounding that separates
	# `bounds_game` from the tile AABBs it was summed from.
	var envelope: AABB = manifest.bounds.grow(TOLERANCE_M)
	var declared: AABB = tile.aabb.grow(TOLERANCE_M)
	var measured_boxes: Array[AABB] = []

	for tier: int in tile.lods.size():
		var path: String = tile.lods[tier]
		var packed := load(path) as PackedScene
		if packed == null:
			problems.append("%s: %s did not load as a scene" % [tile.id, path])
			continue

		var node: Node3D = packed.instantiate()
		var measured: AABB = MeshContract.bounds(node)
		node.free()

		if measured.size == Vector3.ZERO:
			problems.append("%s: %s carries no mesh to measure" % [tile.id, path])
			continue
		measured_boxes.append(measured)

		# Every tier must sit inside the box the streamer culls against, or the
		# streamer drops a tile whose geometry is still on screen.
		if not declared.encloses(measured):
			problems.append(
				"%s: LOD%d spans %s, outside the declared %s" % [tile.id, tier, measured, tile.aabb]
			)

	# A tier that failed above already has its own problem recorded, and the two
	# checks below compare against *every* tier — so running them on a partial
	# set would raise a second, bogus complaint pointing at the wrong thing.
	if measured_boxes.size() != tile.lods.size():
		return problems

	var spanned: AABB = MeshContract.union(measured_boxes)

	# Against the *measured* meshes, not against `tile.aabb`. `bounds_game` is
	# summed from those declared corners, so comparing the two only ever confirms
	# the manifest is self-consistent — which it always is, and which
	# `export.py::_check_bounds` already checks against `buildings.json`.
	# Geometry outside the region is the fact worth learning here.
	#
	# Over every tier, not tier 0 alone. That shortcut held while the finest tier
	# was an exact weld and so contained the rest; `P2-1` disproved it — a
	# coarser tier can stand *taller*, measured at 12.03 m on `t_01_02`.
	if not envelope.encloses(spanned):
		problems.append(
			"%s: tiers span %s, outside bounds_game %s" % [tile.id, spanned, manifest.bounds]
		)

	# ...and the declared box must be no *larger* than the tiers it describes.
	#
	# ⚠️ Containment alone is not enough, and equality against LOD0 is no longer
	# the right test. `tiles[].aabb` used to be the full-detail mesh's, so tier 0
	# matched it corner for corner — but the finest tier stopped being an exact
	# weld when `P2-1` dropped LOD0, and decimation moves corners. It does not
	# only shrink them: `collapse` buckets on `floor(position / cell_m)` and
	# averages each bucket, so a *coarser* grid can leave an extreme vertex alone
	# in its cell and preserve it exactly where a finer grid averaged it inward.
	# So the ETL publishes the union of the shipped tiers and this asserts that
	# union is tight, which still catches a tile whose mesh and manifest disagree
	# about where it is — the reason this check exists.
	#
	# ⚠️ **It is weaker than what it replaced, and the gap is worth naming.** The
	# old check pinned tier 0's two corners to the manifest. This one pins the
	# union, so a defect confined to one tier that leaves it *inside* the
	# declared box — a mis-scaled or inward-shifted LOD0, say — now passes.
	# Closing that needs a per-tier `aabb` in the data contract, which is a
	# schema bump rather than a check change; it belongs with `P2-6`.
	var drift: float = maxf(
		spanned.position.distance_to(tile.aabb.position), spanned.end.distance_to(tile.aabb.end)
	)
	if drift > TOLERANCE_M:
		problems.append(
			(
				"%s: tiers span %s, city.json says %s (%.3f m out)"
				% [tile.id, spanned, tile.aabb, drift]
			)
		)

	return problems
