## Checks the generated road surface against the data contract, headless.
##
## `P1-4` delivers a drivable surface with collision. Whether Godot's importer
## actually built that collider from the `-col` suffix in the mesh name is an
## engine-side fact, so the ETL cannot assert it and its own tests cannot see
## it — the same gap `verify_tiles.gd` exists to close. Run:
##
##     godot --headless --path game --script res://tools/verify_road_surface.gd
##
## Exits non-zero if the surface is missing or fails any check.
extends SceneTree

const GeneratedRoadSurface = preload("res://scripts/city/generated_road_surface.gd")
const MeshContract = preload("res://scripts/city/mesh_contract.gd")

## One primitive, so the whole region's roads cost one draw call — the same
## rule the tiles are held to, and the reason the surface is untextured.
const SURFACES: int = 1

## The material the surface must end up with, mirroring `SHADERS` in
## `tools/generated_scene_import.gd` and `SURFACE_MATERIAL` in
## `etl/pipeline/surface.py`.
##
## Checked for the reason `verify_tiles.gd` checks its own: the dispatch has
## **no failing state**. If the ETL stopped naming the material, or the import
## script stopped recognising the name, the road would quietly keep its default
## `BaseMaterial3D` and render as the flat grey ribbon it was before `P3-12` —
## passing every other check here, with nothing to see and nothing to catch.
const MARKINGS_MATERIAL: String = "res://tuning/road_markings.tres"

## The `TEXCOORD_1` marking codec (`P3-12`), mirroring the `MARKING_*` constants
## in `etl/pipeline/surface.py` and `assets/shaders/road_markings.gdshader` —
## `docs/ARCHITECTURE.md`'s channel table is the tiebreak.
const MARKING_LANES_FIELD: float = 4.0
const MARKING_DIRECTION_FIELD: float = 64.0
const MARKING_BUS_FIELD: float = 256.0
const MARKING_CLASS_CAP: float = 2.0
const MARKING_DIRECTION_MAX: float = 2.0
const MARKING_CENTRE_FIELD: float = 2048.0
const MARKING_CENTRE_MAX: float = 63.0
## `P3-13`'s two fields: what kind of kerbside line each side carries.
const MARKING_KERB_NEAR_FIELD: float = 131072.0
const MARKING_KERB_OFF_FIELD: float = 524288.0
const MARKING_KERB_SPAN: float = 4.0
## Derived from the top field rather than written down, the way
## `etl/pipeline/surface.py` derives its own — a literal here is a number that
## has to be re-derived by hand the next time a field is added, and getting it
## wrong loosens the check silently.
const MARKING_CODE_MAX: float = MARKING_KERB_OFF_FIELD * MARKING_KERB_SPAN - 1.0

## The longest edge the region may publish, in metres, as a sanity ceiling on
## `TEXCOORD_1.y`. Not a contract value — geometry is clipped to a region 1.7 km
## across, so a length past this is a corrupted channel rather than a long road.
const MAX_EDGE_M: float = 4000.0


func _init() -> void:
	var packed: PackedScene = GeneratedRoadSurface.load_surface()
	if packed == null:
		printerr(GeneratedRoadSurface.missing_hint())
		quit(1)
		return

	var scene_root: Node3D = packed.instantiate()
	var problems: PackedStringArray = _check(scene_root)
	# Instantiated outside the tree, so nothing else will free it — and a
	# headless run that leaks buries its own result under exit warnings.
	scene_root.free()
	for problem: String in problems:
		printerr("  FAIL  ", problem)
	if problems.is_empty():
		print("  ok    ", GeneratedRoadSurface.PATH)
	quit(1 if not problems.is_empty() else 0)


func _check(scene_root: Node3D) -> PackedStringArray:
	var problems: PackedStringArray = []

	var instances: Array[Node] = scene_root.find_children("*", "MeshInstance3D", true, false)
	if instances.size() != 1:
		problems.append("expected one MeshInstance3D, found %d" % instances.size())
		return problems

	var mesh := (instances[0] as MeshInstance3D).mesh as ArrayMesh
	if mesh == null:
		problems.append("the MeshInstance3D carries no ArrayMesh")
		return problems
	# Exactly, not at most: a mesh with no surfaces at all would otherwise pass
	# every check below by never entering the loop.
	if mesh.get_surface_count() != SURFACES:
		problems.append("%d surfaces, expected %d" % [mesh.get_surface_count(), SURFACES])

	for surface: int in mesh.get_surface_count():
		problems.append_array(MeshContract.check_surface(mesh, surface, "surface %d" % surface))
		# The only rule the road surface adds to the shared contract. The
		# markings shader in `docs/ART_DESIGN.md` is driven by these: U is a
		# lane coordinate, V is metres along the carriageway.
		if not (mesh.surface_get_format(surface) & Mesh.ARRAY_FORMAT_TEX_UV):
			problems.append("surface %d carries no UVs" % surface)
		problems.append_array(
			MeshContract.check_shader_material(
				mesh, surface, "surface %d" % surface, MARKINGS_MATERIAL
			)
		)
		problems.append_array(_check_marking_payload(mesh, surface, "surface %d" % surface))
		problems.append_array(_check_kerb_extent(mesh, surface, "surface %d" % surface))

	problems.append_array(MeshContract.check_collision(scene_root))
	problems.append_array(
		MeshContract.check_uv2_import_settings(GeneratedRoadSurface.PATH, "marking payload")
	)

	return problems


## `COLOR_0.a` still says where the kerbside restrictions run (`P3-13`, `Q54`).
##
## ⚠️ **The one thing in this asset that fails to *nothing*.** Alpha is the
## channel `surface.py` writes the restriction extent into, and it is opaque 255
## by default — so if the ETL stopped writing it, or glTF lost it, or the
## importer dropped it, every value would read 1.0, the shader would paint every
## kerb in the region, and the city would look exactly as it did before `P3-13`.
## There is no error and nothing to see. This is what notices.
##
## Three assertions, and the first is the load-bearing one:
##
## - some carriageway vertex is 0 and some is 255. Either extreme alone means
##   the channel has stopped carrying an extent, in one direction or the other.
## - every value is one of those two. The ETL writes no third, so anything in
##   between is interpolation baked into the vertices — which is what a lightmap
##   unwrap or a lossy re-export would leave behind.
## - a kerb or a cap is opaque. Those carry no extent, and a zero on one would
##   be the rails coming out of `strip` in the wrong order.
func _check_kerb_extent(mesh: Mesh, surface: int, where: String) -> PackedStringArray:
	var arrays: Array = mesh.surface_get_arrays(surface)
	var colours: PackedColorArray = arrays[Mesh.ARRAY_COLOR]
	var uv2s: PackedVector2Array = arrays[Mesh.ARRAY_TEX_UV2]
	if colours.is_empty() or colours.size() != uv2s.size():
		return PackedStringArray(["%s: COLOR_0 and TEXCOORD_1 do not agree in length" % where])

	var restricted: int = 0
	var clear: int = 0
	for index: int in colours.size():
		var alpha: float = colours[index].a
		var carriageway: bool = fmod(uv2s[index].x, MARKING_LANES_FIELD) == 0.0
		if alpha > 0.999:
			restricted += 1 if carriageway else 0
		elif alpha < 0.001:
			if not carriageway:
				return PackedStringArray(
					[
						(
							(
								"%s: a kerb or cap vertex carries alpha 0. Only the carriageway "
								+ "carries an extent, so this is `strip` taking its rails in the "
								+ "wrong order — every yellow line in the city is on the wrong kerb"
							)
							% where
						)
					]
				)
			clear += 1
		else:
			return PackedStringArray(
				[
					(
						(
							"%s: COLOR_0.a is %f, which is neither 0 nor 1. The ETL writes only "
							+ "those two, so the channel has been resampled — a lightmap unwrap or "
							+ "a lossy re-export"
						)
						% [where, alpha]
					)
				]
			)

	if restricted == 0 or clear == 0:
		return PackedStringArray(
			[
				(
					(
						"%s: COLOR_0.a is uniform across the carriageway (%d restricted, %d "
						+ "clear). The kerbside extent has stopped shipping, and the markings "
						+ "shader will paint every kerb in the region — `Q54`, silently"
					)
					% [where, restricted, clear]
				)
			]
		)
	print("  kerbside extent: %d carriageway vertices restricted, %d clear" % [restricted, clear])
	return PackedStringArray()


## The marking payload holds the codec's invariants (`P3-12`).
##
## `TEXCOORD_1.x` must be a small exact integer whose decoded fields are in
## range, and `y` a non-negative length. Beyond the contract itself this is the
## tripwire for both import hazards, the same pair `verify_tiles.gd` guards: a
## lightmap unwrap (`meshes/light_baking = 2`) replaces the channel with
## fractions in [0, 1], and 16-bit attribute compression corrupts large codes —
## either way the exactness or range checks fail.
##
## ⚠️ There is **no refusal sentinel to skip here**, unlike the tiles. A cap
## carries `(2, 0)` and a carriageway vertex always carries a class and a lane
## count, so every vertex is a real code and the scan holds all of them. A run of
## `Vector2.ZERO` would mean class 0 with no lanes, which is not a road.
func _check_marking_payload(mesh: Mesh, surface: int, where: String) -> PackedStringArray:
	if not (mesh.surface_get_format(surface) & Mesh.ARRAY_FORMAT_TEX_UV2):
		return PackedStringArray(
			["%s carries no TEXCOORD_1; the markings shader has nothing to read" % where]
		)

	var uv2s: PackedVector2Array = mesh.surface_get_arrays(surface)[Mesh.ARRAY_TEX_UV2]
	for uv2: Vector2 in uv2s:
		var code: float = uv2.x
		var surface_class: float = fmod(code, MARKING_LANES_FIELD)
		var lanes: float = fmod(
			floor(code / MARKING_LANES_FIELD), MARKING_DIRECTION_FIELD / MARKING_LANES_FIELD
		)
		var direction: float = fmod(
			floor(code / MARKING_DIRECTION_FIELD), MARKING_BUS_FIELD / MARKING_DIRECTION_FIELD
		)
		if (
			code != floor(code)
			or code < 0.0
			or code > MARKING_CODE_MAX
			or surface_class > MARKING_CLASS_CAP
			or direction > MARKING_DIRECTION_MAX
			or uv2.y < 0.0
			or uv2.y > MAX_EDGE_M
			# A junction cap is the only thing that may carry no lanes, and it is
			# also the only thing that may carry no length — the pair is what the
			# shader reads as "not a length of lane", and half of it is a bug.
			or (lanes == 0.0) != (surface_class == MARKING_CLASS_CAP)
			or (uv2.y == 0.0) != (surface_class == MARKING_CLASS_CAP)
			# `P3-13`: a junction cap is not a length of kerb, so neither kerb
			# field may say anything on one. A code that did would put a yellow
			# line across a junction the moment anything drew on a cap.
			or (
				surface_class == MARKING_CLASS_CAP
				and (
					fmod(floor(code / MARKING_KERB_NEAR_FIELD), MARKING_KERB_SPAN) != 0.0
					or fmod(floor(code / MARKING_KERB_OFF_FIELD), MARKING_KERB_SPAN) != 0.0
				)
			)
		):
			return PackedStringArray(
				[
					(
						(
							"%s: TEXCOORD_1 (%f, %f) breaks the marking codec — the ETL and "
							+ "shader disagree, or the importer rewrote the channel "
							+ "(lightmap unwrap or attribute compression)"
						)
						% [where, uv2.x, uv2.y]
					)
				]
			)
	return PackedStringArray()
