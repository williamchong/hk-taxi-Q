## Checks the parked roster against its contract, headless (`P3-73`, `Q161`).
##
##     godot --headless --path game --script res://tools/verify_parked.gd
##
## Three things, each of which renders as a perfectly plausible street when
## wrong: the LIBRARY — every kind one `vehicle_body` surface on
## `vehicle_body.tres`, coloured, collider-free, on the ground, nose north —
## the JOIN between the library and the region's `parked_placements.json`
## (`GeneratedPlacements.check_join`, both ways, as the signs and lamps are
## graded), and the ROSTER's arithmetic: the clock, the windows from both
## sides, the chance drawn the same twice and differently on the next roll.
##
## ⚠️ **Absence is a pass.** A city with no `parked:` block ships no document
## and the manifest names none; `verify_city.gd` is what holds a NAMED document
## to the file, so a manifest naming it with the file gone fails there.
##
## 🔴 **What this tool CANNOT see is the hour a vehicle stands at in the
## game.** The windows are graded here; which hour the rig reads is
## `DayClock`'s, and the evidence that a van is gone at night is a frame at
## `--time-of-day=0.9` beside one by day.
extends SceneTree

const CityManifestScript = preload("res://scripts/city/city_manifest.gd")
const GeneratedPlacements = preload("res://scripts/city/generated_placements.gd")
const MeshContract = preload("res://scripts/city/mesh_contract.gd")
const ParkedLayerScript = preload("res://scripts/city/parked_layer.gd")
const ParkedRoster = preload("res://scripts/city/parked_roster.gd")

## The material every kind must import to, `generated_scene_import.gd`'s
## merge of the `vehicle_*` parts `tools/make_parked.py` writes.
const BODY_MATERIAL: String = "res://tuning/vehicle_body.tres"
## The budget per kind (`ART_DESIGN.md`'s 800–2,000, the upper bar).
const TRIANGLE_BUDGET: int = 2000
## A kind's underside may sit this far off the ground, in metres.
const GROUND_SLACK_M: float = 0.02

var _problems: PackedStringArray = []


func _init() -> void:
	var manifest: CityManifest = CityManifestScript.load_manifest()
	if manifest == null:
		quit(1)
		return
	_check_roster()
	_check_profile()
	if manifest.parked_placements_path.is_empty():
		print("  skip  no parked roster shipped for this region")
	else:
		var document: Dictionary = GeneratedPlacements.load_placements(
			manifest.parked_placements_path, "parked vehicles"
		)
		if document.is_empty():
			_problems.append("%s did not load" % manifest.parked_placements_path)
		else:
			var library: Dictionary[String, Mesh] = _check_library(
				String(document.get("library", ""))
			)
			if not library.is_empty():
				_check_join(document, library)
			_check_entries(document)
	for problem: String in _problems:
		printerr("  FAIL  ", problem)
	if _problems.is_empty():
		print("  ok    verify_parked")
	quit(1 if not _problems.is_empty() else 0)


func _expect(held: bool, what: String) -> void:
	if not held:
		_problems.append(what)


## The library as imported: one merged `vehicle_body` surface a kind.
func _check_library(path: String) -> Dictionary[String, Mesh]:
	var library: Dictionary[String, Mesh] = {}
	var packed := load(path) as PackedScene
	if packed == null:
		_problems.append("library %s did not load as a scene" % path)
		return library
	var scene_root: Node3D = packed.instantiate()
	library = MeshContract.library_meshes(scene_root, 1, _problems)
	for mesh_name: String in library:
		var mesh := library[mesh_name] as ArrayMesh
		var where: String = "'%s'" % mesh_name
		_problems.append_array(MeshContract.check_surface(mesh, 0, where, true))
		_problems.append_array(MeshContract.check_shader_material(mesh, 0, where, BODY_MATERIAL))
		var triangles: int = MeshContract.mesh_triangles(mesh)
		_expect(
			triangles <= TRIANGLE_BUDGET,
			"%s is %d triangles, over the %d budget" % [where, triangles, TRIANGLE_BUDGET]
		)
		var box: AABB = mesh.get_aabb()
		_expect(
			absf(box.position.y) <= GROUND_SLACK_M,
			(
				"%s stands %.3f m off the ground; the library's ground is y = 0"
				% [where, box.position.y]
			)
		)
		_expect(
			box.position.z < 0.0 and box.end.z > 0.0 and box.position.x < 0.0 and box.end.x > 0.0,
			"%s is not centred on its origin in plan" % where
		)
	_problems.append_array(
		MeshContract.check_no_collision(
			scene_root,
			"the parked library",
			"tools/make_parked.py — the layer stands its own boxes"
		)
	)
	scene_root.free()
	return library


## The join, one way: every entry names a library mesh and decodes. ⚠️ **Not
## `GeneratedPlacements.check_join`**, which also fails a library mesh stood
## nowhere — right for a generated library, whose every mesh was drawn for a
## stand, and wrong for an AUTHORED roster: a region with no taxi stand
## stands no taxi, and that is the data, not a defect. The unstood kinds are
## printed so a reader can see the selection rather than take it.
func _check_join(document: Dictionary, library: Dictionary[String, Mesh]) -> void:
	var joined: Dictionary = GeneratedPlacements.group(document, library)
	_expect(
		int(joined["no_mesh"]) == 0,
		"%d placements name a mesh the library does not carry" % int(joined["no_mesh"])
	)
	_expect(
		int(joined["no_transform"]) == 0,
		"%d placements carry no usable transform" % int(joined["no_transform"])
	)
	var unstood: PackedStringArray = joined["unstood"]
	if not unstood.is_empty():
		print("  info  library kinds stood nowhere in this region: %s" % ", ".join(unstood))


## Every entry's `hours` is a window or null and its `chance` a share.
func _check_entries(document: Dictionary) -> void:
	var kinds: Dictionary[String, int] = {}
	var bad_hours: int = 0
	var bad_chance: int = 0
	for entry: Dictionary in document.get("placements", []) as Array:
		var hours: Variant = entry.get("hours")
		if hours != null and not (hours is Array and (hours as Array).size() == 2):
			bad_hours += 1
		var chance: float = float(entry.get("chance", 1.0))
		if chance <= 0.0 or chance > 1.0:
			bad_chance += 1
		var kind: String = String(entry.get("kind", ""))
		kinds[kind] = kinds.get(kind, 0) + 1
	_expect(bad_hours == 0, "%d placements carry hours that are not [from_h, to_h]" % bad_hours)
	_expect(bad_chance == 0, "%d placements carry a chance outside (0, 1]" % bad_chance)
	print("  info  parked kinds: %s" % JSON.stringify(kinds))


## The table and its bars, through `ParkedLayer`'s own refusal.
func _check_profile() -> void:
	var profile := load(ParkedProfile.PATH) as ParkedProfile
	_expect(profile != null, "%s did not load" % ParkedProfile.PATH)
	if profile == null:
		return
	_expect(ParkedLayerScript._usable(profile), "%s is refused by ParkedLayer" % ParkedProfile.PATH)
	var folded: ParkedProfile = profile.duplicate()
	folded.clock_end_h = folded.clock_start_h
	_expect(not ParkedLayerScript._usable(folded), "mutation caught: an empty day is refused")
	var sizeless: ParkedProfile = profile.duplicate()
	sizeless.cell_m = 0.0
	_expect(not ParkedLayerScript._usable(sizeless), "mutation caught: a zero cell is refused")


## The roster's arithmetic, from both sides of every bar.
func _check_roster() -> void:
	_expect(
		is_equal_approx(ParkedRoster.hour_of(0.0, 12.0, 24.0), 12.0),
		"the clock starts at clock_start_h"
	)
	_expect(is_equal_approx(ParkedRoster.hour_of(0.5, 12.0, 24.0), 18.0), "and runs linearly")
	_expect(
		is_equal_approx(ParkedRoster.hour_of(1.0, 12.0, 24.0), 0.0), "midnight reads as 0, wrapping"
	)
	_expect(
		is_equal_approx(ParkedRoster.hour_of(1.0, 18.0, 30.0), 6.0), "a day past midnight wraps too"
	)
	_expect(ParkedRoster.in_window(13.0, []), "no window is always")
	_expect(ParkedRoster.in_window(8.0, [8, 19]), "a window includes its start")
	_expect(not ParkedRoster.in_window(19.0, [8, 19]), "and excludes its end")
	_expect(ParkedRoster.in_window(18.99, [8, 19]), "a tick short of the end is in")
	_expect(not ParkedRoster.in_window(7.99, [8, 19]), "a tick short of the start is out")
	_expect(ParkedRoster.in_window(23.0, [19, 7]), "a window past midnight holds the evening")
	_expect(ParkedRoster.in_window(3.0, [19, 7]), "and the small hours")
	_expect(not ParkedRoster.in_window(12.0, [19, 7]), "and not the day")
	_expect(ParkedRoster.in_window(0.0, [19, 7]), "midnight itself is in a night window")
	_expect(ParkedRoster.present(3, [], 1.0, 12.0, 0), "a chance of 1 always stands")
	_expect(not ParkedRoster.present(3, [19, 7], 1.0, 12.0, 0), "but not outside its window")
	_expect(
		ParkedRoster.draw(5, 2) == ParkedRoster.draw(5, 2), "the same roll draws the same number"
	)
	var differs: bool = false
	for roll: int in 8:
		if ParkedRoster.draw(5, roll) != ParkedRoster.draw(5, roll + 1):
			differs = true
	_expect(differs, "and the next roll draws another")
	var stood: int = 0
	for index: int in 1000:
		if ParkedRoster.present(index, [], 0.35, 12.0, 0):
			stood += 1
	_expect(
		stood > 250 and stood < 450,
		"a chance of 0.35 stands about a third of 1,000 placements, not %d" % stood
	)
	_expect(
		ParkedRoster.cell_of(Vector3(301.0, 0.0, -1.0), 300.0) == Vector2i(1, -1),
		"a point goes to the cell its plan origin is in"
	)
