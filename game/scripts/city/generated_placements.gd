## Reads a `*_placements.json` and turns its entries into transforms (`P5-2`).
##
## A prop layer is a LIBRARY — a `.glb` of named meshes — and a document that
## stands each one: entries of `mesh`, a `transform` in `landmarks.json`'s shape
## (`pos`, a compass `rot_y_deg`) and an optional `scale`. The signs are the
## first; the lamps and arrows take the same document (`Q115`), which is why
## this is its own script rather than a corner of `generated_layer.gd` — that
## table is static data about where a layer lives, and this is behaviour.
##
## Three readers: `layer_preview.gd` draws what this decodes, and
## `verify_signs.gd` and `verify_lamps.gd` grade it through `check_join`, so
## `group` is the one statement of the join between a library and its document
## — a mesh nothing stands, an entry naming no mesh, an entry with no usable
## transform — and all three report the same three counts.
extends RefCounted

const GeneratedDocument = preload("res://scripts/city/generated_document.gd")
const GeneratedLandmarks = preload("res://scripts/city/generated_landmarks.gd")

## Schema of every placements document — the format is the same per layer.
## Matches `PLACEMENTS_SCHEMA` in `etl/pipeline/placements.py`.
const SCHEMA_VERSION: int = 1


## The document at `path`, or `{}` with the warning pushed.
static func load_placements(path: String, noun: String) -> Dictionary:
	return GeneratedDocument.load_object(
		path,
		SCHEMA_VERSION,
		"No placements at %s for %s. Run the ETL and copy its output there." % [path, noun]
	)


## One entry as a transform, or null for a malformed one.
##
## ⚠️ **The rotation is `GeneratedLandmarks.placement_of`'s and deliberately not
## restated** — that function is the one owner of the compass-to-`Basis`
## convention (`generated_fence.gd` says why), and a second producer would be a
## sign error on a layer where a plate turned the wrong way is a perfectly good
## sign giving the opposite instruction. `scale` is the one addition: a pole is
## a unit prism stretched to its own height. 🔴 **A negative or zero factor is
## refused here, not graded later** — under `cull_back` a mirrored plate is a
## missing one, so the preview must never draw it and `verify_signs.gd` reports
## the null this returns. Null rather than the identity, on the same reasoning
## as the landmarks: the origin is a real place.
static func placement_of(entry: Dictionary) -> Variant:
	var placed: Variant = GeneratedLandmarks.placement_of(entry)
	if placed == null:
		return null
	var at: Transform3D = placed as Transform3D
	var scale: Array = entry.get("scale") if entry.get("scale") is Array else []
	if scale.is_empty():
		return at
	if scale.size() != 3:
		return null
	var factors := Vector3(scale[0], scale[1], scale[2])
	if factors.x <= 0.0 or factors.y <= 0.0 or factors.z <= 0.0:
		return null
	return Transform3D(at.basis.scaled_local(factors), at.origin)


## The join between a library and its document, both ways.
##
## Returns `transforms` (mesh name -> `Array[Transform3D]`), `no_mesh` (entries
## naming a mesh the library lacks), `no_transform` (entries `placement_of`
## refused) and `unstood` (library meshes no entry names). The two readers
## decide what to do with the counts; neither recomputes them.
static func group(document: Dictionary, library: Dictionary[String, Mesh]) -> Dictionary:
	var transforms: Dictionary[String, Array] = {}
	var no_mesh: int = 0
	var no_transform: int = 0
	for entry: Dictionary in document.get("placements", []) as Array:
		var mesh_name: String = String(entry.get("mesh", ""))
		if not library.has(mesh_name):
			no_mesh += 1
			continue
		var placed: Variant = placement_of(entry)
		if placed == null:
			no_transform += 1
			continue
		if not transforms.has(mesh_name):
			var batch: Array[Transform3D] = []
			transforms[mesh_name] = batch
		transforms[mesh_name].append(placed as Transform3D)
	var unstood: PackedStringArray = []
	for mesh_name: String in library:
		if not transforms.has(mesh_name):
			unstood.append(mesh_name)
	return {
		"transforms": transforms,
		"no_mesh": no_mesh,
		"no_transform": no_transform,
		"unstood": unstood,
	}


## The join graded, for a verify tool: the library must be stood in both
## directions and every entry must decode. Returns the problems, and prints the
## `ok` line itself when there are none, so the two verifiers that call this
## report the same three failures in the same words.
static func check_join(
	path: String, noun: String, library: Dictionary[String, Mesh]
) -> PackedStringArray:
	var problems: PackedStringArray = []
	var document: Dictionary = load_placements(path, noun)
	if document.is_empty():
		problems.append("the library is present and its placements document is not")
		return problems
	var joined: Dictionary = group(document, library)
	if int(joined["no_mesh"]) > 0:
		problems.append("%d placements name a mesh the library does not carry" % joined["no_mesh"])
	if int(joined["no_transform"]) > 0:
		problems.append("%d placements carry no usable transform" % joined["no_transform"])
	for mesh_name: String in joined["unstood"] as PackedStringArray:
		problems.append("library mesh '%s' is stood nowhere" % mesh_name)
	if problems.is_empty():
		var entries: Array = document.get("placements", []) as Array
		print("  ok    %d placements stand %d library meshes" % [entries.size(), library.size()])
	return problems
