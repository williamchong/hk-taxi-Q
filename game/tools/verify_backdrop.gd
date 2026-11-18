## Checks the generated far shore against the data contract, headless
## (`P3-100`, `Q249`).
##
## Two meshes — the skyline on its ground, and the far sea — and the claims a
## frame cannot check: that each has the material that draws it past the far
## plane, that those materials agree with each other and with the drive
## camera about where that plane is, that the far sea is the sea, and that no
## block stands where the squeeze would put it in front of the street. Run:
##
##     godot --headless --path game --script res://tools/verify_backdrop.gd
##
## Exits non-zero if the far shore is present and fails any check. Absence is a
## pass on `verify_water.gd`'s terms: `verify_city.gd` asserts a NAMED asset
## exists.
extends SceneTree

const FarCull = preload("res://scripts/city/far_cull.gd")
const GeneratedLayer = preload("res://scripts/city/generated_layer.gd")
const Manifest = preload("res://scripts/city/city_manifest.gd")
const VerifyLayer = preload("res://tools/verify_layer.gd")
const MeshContract = preload("res://tools/mesh_contract.gd")

## One primitive a mesh, so the far shore costs two draw calls.
const SURFACES: int = 1

## The meshes `etl/pipeline/backdrop.py` writes: `BACKDROP_MESH_NAME` and
## `BACKDROP_SEA_MESH_NAME`.
const SKYLINE: String = "backdrop"
const SEA: String = "backdrop_sea"

## Mirrors `SHADERS` in `tools/generated_scene_import.gd`. Checked by path
## because a mesh that missed the dispatch is culled at the far plane: it draws
## nothing, which is what a harbour looked like before there was a far shore.
const MATERIALS: Dictionary[String, String] = {
	SKYLINE: "res://tuning/backdrop.tres",
	SEA: "res://tuning/water.tres",
}

## `far_shore.gdshaderinc`'s uniforms, which both materials state.
const PIN_PARAMETERS: PackedStringArray = ["street_far_m", "pin_band_m", "pin_from_m"]

## The scene whose camera `street_far_m` restates, and the camera in it.
const DRIVE_SCENE: String = "res://scenes/city_drive.tscn"
const DRIVE_CAMERA: String = "Camera3D"


func _init() -> void:
	VerifyLayer.run(self, GeneratedLayer.BACKDROP, _check)


func _check(scene_root: Node3D) -> PackedStringArray:
	var problems: PackedStringArray = []
	var library: Dictionary[String, Mesh] = MeshContract.library_meshes(
		scene_root, SURFACES, problems
	)
	for mesh_name: String in MATERIALS:
		if not library.has(mesh_name):
			problems.append("the far shore carries no '%s' mesh" % mesh_name)
	if not problems.is_empty():
		return problems
	if library.size() != MATERIALS.size():
		problems.append(
			"the far shore carries %d meshes, expected %d" % [library.size(), MATERIALS.size()]
		)
	for mesh_name: String in MATERIALS:
		var mesh := library[mesh_name] as ArrayMesh
		# `true`: the colours ride `COLOR_0` from `materials:` (`Q33`).
		problems.append_array(MeshContract.check_surface(mesh, 0, mesh_name, true))
		problems.append_array(
			MeshContract.check_shader_material(mesh, 0, mesh_name, MATERIALS[mesh_name])
		)
	problems.append_array(
		MeshContract.check_no_collision(
			scene_root, "the far shore", "BACKDROP_NAME in etl/pipeline/backdrop.py"
		)
	)
	if not GeneratedLayer.beyond_far(GeneratedLayer.BACKDROP):
		problems.append("generated_layer.gd does not draw the far shore beyond the far plane")
	if not problems.is_empty():
		return problems
	problems.append_array(_check_cull())
	var pin: Dictionary = _check_pin(problems)
	problems.append_array(_check_sea(library[SEA] as ArrayMesh))
	if not pin.is_empty():
		problems.append_array(_check_stands_off(library[SKYLINE] as ArrayMesh, pin))
	return problems


## `FarCull.outside` against a camera at the origin looking north (-Z) through
## a square 90 degree frustum with its far plane at 400 m. The far shore is
## hidden only by a side of the view: a box past the far plane is still seen,
## which is the whole reason the engine's own cull could not be used.
func _check_cull() -> PackedStringArray:
	var slope: float = sqrt(0.5)
	var planes: Array[Plane] = [
		Plane(Vector3(0.0, 0.0, 1.0), 0.0),
		Plane(Vector3(0.0, 0.0, -1.0), 400.0),
		Plane(Vector3(-slope, 0.0, slope), 0.0),
		Plane(Vector3(0.0, slope, slope), 0.0),
		Plane(Vector3(slope, 0.0, slope), 0.0),
		Plane(Vector3(0.0, -slope, slope), 0.0),
	]
	var size := Vector3(500.0, 100.0, 500.0)
	var cases: Dictionary[String, Array] = {
		"ahead, past the far plane": [Vector3(-250.0, 0.0, -1500.0), false],
		"behind the camera": [Vector3(-250.0, 0.0, 1000.0), true],
		"off to the east": [Vector3(3000.0, 0.0, -1000.0), true],
		"across the edge of the view": [Vector3(700.0, 0.0, -1000.0), false],
		"round the camera": [Vector3(-250.0, -50.0, -250.0), false],
	}
	var problems: PackedStringArray = []
	for case: String in cases:
		var hidden: bool = FarCull.outside(planes, AABB(cases[case][0], size))
		if hidden != bool(cases[case][1]):
			problems.append("a box %s is %s" % [case, "hidden" if hidden else "drawn"])
	return problems


## Both materials state the same three numbers, and `street_far_m` is the
## drive camera's `far`. Returns them, or `{}` after saying what differs.
func _check_pin(problems: PackedStringArray) -> Dictionary:
	var pin: Dictionary = {}
	for mesh_name: String in MATERIALS:
		var material := load(MATERIALS[mesh_name]) as ShaderMaterial
		for parameter: String in PIN_PARAMETERS:
			var value: Variant = material.get_shader_parameter(parameter)
			if value == null:
				problems.append("%s states no %s" % [MATERIALS[mesh_name], parameter])
			elif not pin.has(parameter):
				pin[parameter] = float(value)
			elif not is_equal_approx(float(value), float(pin[parameter])):
				problems.append(
					(
						"%s is %s in %s and %s in %s"
						% [
							parameter,
							value,
							MATERIALS[mesh_name],
							pin[parameter],
							MATERIALS[SKYLINE]
						]
					)
				)
	var far_m: float = _drive_far()
	if far_m <= 0.0:
		problems.append("%s has no %s with a far plane" % [DRIVE_SCENE, DRIVE_CAMERA])
	elif pin.has("street_far_m") and not is_equal_approx(float(pin["street_far_m"]), far_m):
		problems.append(
			(
				(
					"street_far_m is %s and the drive camera's far is %s: the far shore is "
					% [pin["street_far_m"], far_m]
				)
				+ "squeezed against a plane that is not there"
			)
		)
	return pin if problems.is_empty() else {}


## The drive camera's `far` as the scene file states it; 0 if it names none.
## Read as text: loading the scene here compiles scripts that name autoloads a
## `--script` run does not have.
func _drive_far() -> float:
	var in_camera: bool = false
	for line: String in FileAccess.get_file_as_string(DRIVE_SCENE).split("\n"):
		if line.begins_with("[node "):
			in_camera = line.contains('name="%s"' % DRIVE_CAMERA)
		elif in_camera and line.begins_with("far = "):
			return line.trim_prefix("far = ").to_float()
	return 0.0


## The far sea is flat at the basemap's level, faces the sky, and every vertex
## carries the marker `water.gdshader` draws past the far plane by. One vertex
## without it is cut off at 400 m like the basemap's own water.
func _check_sea(mesh: ArrayMesh) -> PackedStringArray:
	var problems: PackedStringArray = MeshContract.check_faces_up(mesh, 0, SEA, "the far sea")
	problems.append_array(MeshContract.check_water_level(mesh, "the far sea"))
	var colours: PackedColorArray = mesh.surface_get_arrays(0)[Mesh.ARRAY_COLOR]
	var unmarked: int = 0
	for colour: Color in colours:
		if colour.a >= 0.5:
			unmarked += 1
	if unmarked > 0:
		problems.append(
			(
				"%d of %d far sea vertices do not carry the far-plane marker"
				% [unmarked, colours.size()]
			)
		)
	return problems


## No block within `pin_from_m` of anywhere a camera can be: nearer than that
## the squeeze lands it in front of its band, over the street's far end.
func _check_stands_off(mesh: ArrayMesh, pin: Dictionary) -> PackedStringArray:
	var manifest: Manifest = Manifest.load_manifest()
	if manifest == null:
		return ["the far shore shipped but city.json did not load"]
	var drivable: AABB = manifest.bounds
	var skyline: AABB = mesh.get_aabb()
	var gap_x: float = maxf(
		maxf(skyline.position.x - drivable.end.x, drivable.position.x - skyline.end.x), 0.0
	)
	var gap_z: float = maxf(
		maxf(skyline.position.z - drivable.end.z, drivable.position.z - skyline.end.z), 0.0
	)
	var gap_m: float = Vector2(gap_x, gap_z).length()
	if gap_m < float(pin["pin_from_m"]):
		return [
			(
				"the skyline comes within %.0f m of the region and pin_from_m is %.0f"
				% [gap_m, pin["pin_from_m"]]
			)
		]
	print(
		(
			"  ok    %d triangles of skyline and shore, %.0f m off the region"
			% [int(mesh.surface_get_array_index_len(0) / 3.0), gap_m]
		)
	)
	return []
