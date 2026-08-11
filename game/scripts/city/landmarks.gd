## Instantiates the authored hero buildings where `landmarks.json` places them
## (`P3-6`).
##
## Unlike the tiles, which are authored in region space and stream by AABB, a
## hero is authored at its own origin and placed by transform — the document
## carries game-space metres and a compass bearing, and
## `GeneratedLandmarks.placement_of` is the one place the bearing becomes a
## Godot rotation.
##
## No streaming and no LOD, deliberately: two heroes are ≤8k triangles each
## against a 300k budget, so residency is cheaper than the machinery — the
## same argument `road_surface_preview.gd` makes for the carriageway. Measure
## with `tools/frame_stats.py` before believing that sentence about a bigger
## roster.
extends Node3D

const GeneratedDocument = preload("res://scripts/city/generated_document.gd")
const GeneratedLandmarks = preload("res://scripts/city/generated_landmarks.gd")


func _ready() -> void:
	# The manifest is the shipping route (`P1-7`): an exported build cannot
	# enumerate `res://`, so what it does not name does not exist. The locator
	# supplies the schema and the hint; `verify_landmarks.gd` asserts the two
	# name the same file.
	var manifest: CityManifest = CityManifest.load_manifest()
	if manifest == null:
		return
	var document: Dictionary = GeneratedDocument.load_object(
		manifest.landmarks_path,
		GeneratedLandmarks.SCHEMA_VERSION,
		GeneratedLandmarks.missing_hint()
	)
	if document.is_empty():
		return

	var placed: int = 0
	for entry: Dictionary in document.get("landmarks", []) as Array:
		var landmark_id: String = str(entry.get("id", ""))
		var asset: String = str(entry.get("asset", ""))
		var packed := load(asset) as PackedScene
		if packed == null:
			push_error("landmark %s names %s, which did not load as a scene" % [landmark_id, asset])
			continue
		var placement: Variant = GeneratedLandmarks.placement_of(entry)
		if placement == null:
			push_error("landmark %s has no usable transform" % landmark_id)
			continue
		var node: Node3D = packed.instantiate()
		node.name = landmark_id
		node.transform = placement as Transform3D
		add_child(node)
		placed += 1
	print("landmarks: %d placed" % placed)
