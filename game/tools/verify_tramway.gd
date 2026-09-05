## Checks the generated tramway against the data contract, headless.
##
## `P3-14` delivers the published tramway as geometry rather than as a marking,
## and the two facts that decision rests on are both engine-side: whether the
## importer dispatched the shader on the material name, and whether it built a
## collider it must *not* have. Run:
##
##     godot --headless --path game --script res://tools/verify_tramway.gd
##
## Exits non-zero if the tramway is present and fails any check.
##
## ⚠️ **Absence is a pass, and that is not a loophole.** A city whose estate
## publishes no tramway ships none and `city.json` names null (`Q58`), so this
## tool cannot treat a missing asset as a failure without failing every such
## city. What stops that becoming a silent skip is `verify_city.gd`, whose
## `_check_documents` asserts a *named* tramway exists and matches this file's
## constant — so a manifest naming `tram.glb` with the file gone fails there.
## ⚠️ That cross-reference was written before the check was, and stood wrong for
## a while; if this comment is edited again, go and look.
extends SceneTree

const GeneratedLayer = preload("res://scripts/city/generated_layer.gd")
const MeshContract = preload("res://scripts/city/mesh_contract.gd")

## One primitive, so the whole region's tramway costs one draw call — the same
## rule the road surface and the tiles are held to.
const SURFACES: int = 1

## The material the tramway must end up with, mirroring `SHADERS` in
## `tools/generated_scene_import.gd` and `TRAMWAY_MATERIAL` in
## `etl/pipeline/tramway.py`.
##
## Checked because the dispatch has **no failing state**: a tramway that kept
## its imported `BaseMaterial3D` would draw the right geometry in the right
## place with none of the specular that makes a rail read as metal — a duller
## tramway, not a missing one, and nothing else here would notice.
const TRAMWAY_MATERIAL: String = "res://tuning/tramway.tres"

## `TEXCOORD_1.x` — the class codec, mirroring `TRAMWAY_CLASS_*` in
## `etl/pipeline/tramway.py` and `assets/shaders/tramway.gdshader`.
## `docs/ARCHITECTURE.md`'s channel table is the tiebreak.
const TRAMWAY_CLASS_BED: float = 0.0
const TRAMWAY_CLASS_RAIL: float = 1.0

## Plan extent of the region, as a sanity ceiling on `TEXCOORD_1.y` — which is
## metres along a track. Geometry is clipped to a region 1.7 km across, so a
## value past this is a corrupted channel rather than a long tramway.
##
## ⚠️ **This channel arrives quantised, and `roads.glb`'s does not** — which is
## why the bound below carries a tolerance where `verify_road_surface.gd`'s
## `MAX_EDGE_M` needs none. Godot's 16-bit vertex compression applies to a mesh
## whose attributes fit the representable range; `roads.glb` escapes it because
## its marking codes reach 2,097,151 and do not fit, while the tramway's payload
## is a 0/1 class and a few hundred metres and does fit. The ETL writes an exact
## float32 zero at the start of every track and it arrives as **-0.009 m**.
##
## So the tolerance is what compression costs, measured, not slack for a channel
## that nearly conforms. It is deliberately far tighter than either import
## hazard it guards: a lightmap unwrap rewrites the channel to fractions in
## [0, 1], and a corrupted one lands nowhere near a plausible length.
const MAX_TRACK_M: float = 4000.0

## How far outside `[0, MAX_TRACK_M]` a value may sit and still be the
## importer's compression rather than a broken channel. See above.
const TRACK_M_TOLERANCE: float = 0.05


func _init() -> void:
	if not GeneratedLayer.is_present(GeneratedLayer.TRAMWAY):
		print("  skip  no %s shipped for this region" % GeneratedLayer.noun(GeneratedLayer.TRAMWAY))
		quit(0)
		return

	var packed: PackedScene = GeneratedLayer.load_layer(GeneratedLayer.TRAMWAY)
	if packed == null:
		# Present but unloadable, which is not the same as absent — the hint
		# about rebuilding would be the wrong advice here.
		printerr(
			(
				"  FAIL  %s exists but did not load as a scene"
				% GeneratedLayer.path(GeneratedLayer.TRAMWAY)
			)
		)
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
		print("  ok    ", GeneratedLayer.path(GeneratedLayer.TRAMWAY))
	quit(1 if not problems.is_empty() else 0)


func _check(scene_root: Node3D) -> PackedStringArray:
	var problems: PackedStringArray = []

	var mesh: ArrayMesh = MeshContract.single_primitive(scene_root, SURFACES, problems)
	if mesh == null:
		return problems

	for surface: int in mesh.get_surface_count():
		var where: String = "surface %d" % surface
		problems.append_array(MeshContract.check_surface(mesh, surface, where))
		if not (mesh.surface_get_format(surface) & Mesh.ARRAY_FORMAT_TEX_UV):
			problems.append("%s carries no UVs" % where)
		problems.append_array(
			MeshContract.check_shader_material(mesh, surface, where, TRAMWAY_MATERIAL)
		)
		problems.append_array(_check_class_payload(mesh, surface, where))

	problems.append_array(_check_has_no_collision(scene_root))
	problems.append_array(
		MeshContract.check_uv2_import_settings(
			GeneratedLayer.path(GeneratedLayer.TRAMWAY), "tramway class"
		)
	)

	return problems


## The tramway must **not** collide, which is the opposite of every other mesh
## this repo verifies.
##
## It lies on ground that has been solid since `P3-10`, and the car drives on
## that ground unchanged. A rail modelled as collision geometry is a 30 mm kerb
## in the middle of a reserve the player cannot see a reason for — and worse, it
## would land in the one place `Q19`'s occupancy grader already fails, on
## streets that are the busiest in the region.
##
## The whole guard is the absence of a `-col` suffix in `tramway.py`'s mesh
## name, which is one token in a string. This is what notices it coming back.
func _check_has_no_collision(scene_root: Node3D) -> PackedStringArray:
	return MeshContract.check_no_collision(
		scene_root, "the tramway", "TRAMWAY_MESH_NAME in etl/pipeline/tramway.py"
	)


## The class channel still tells a rail from a bed (`P3-14`).
##
## ⚠️ **This asset's version of the failure that fails to nothing.** The shader
## reads `is_rail` out of `TEXCOORD_1.x`; if the ETL stopped writing it, or a
## re-export lost it, every fragment would read 0, the whole tramway would take
## the bed's roughness, and it would render as a plain concrete strip. There is
## no error and nothing in the frame says so.
##
## Three assertions, and the first is the load-bearing one:
##
## - both classes are present. Either alone means the channel has stopped
##   carrying a class, in one direction or the other.
## - every value is exactly one of the two. The ETL writes no third, so anything
##   in between is interpolation baked into the vertices — what a lightmap
##   unwrap or a lossy re-export leaves behind.
## - `TEXCOORD_1.y` is metres along and within the region, to the tolerance
##   compression costs. A tramway is drawn from the source's own parts, so a
##   length past the region is a corrupt channel rather than a long track.
func _check_class_payload(mesh: Mesh, surface: int, where: String) -> PackedStringArray:
	# ⚠️ The format flag is checked **before** the array is read, not after.
	# `surface_get_arrays` returns `null` for a channel the mesh does not have,
	# and assigning that to a typed `PackedVector2Array` is a hard script error
	# — which `check.sh` turns into a failure, but with a Godot backtrace
	# instead of the sentence that says what is actually wrong.
	if not (mesh.surface_get_format(surface) & Mesh.ARRAY_FORMAT_TEX_UV2):
		return PackedStringArray(
			["%s carries no TEXCOORD_1; the tramway shader cannot tell a rail from a bed" % where]
		)
	var arrays: Array = mesh.surface_get_arrays(surface)
	var uv2s: PackedVector2Array = arrays[Mesh.ARRAY_TEX_UV2]
	var uvs: PackedVector2Array = arrays[Mesh.ARRAY_TEX_UV]
	if uv2s.size() != uvs.size():
		return PackedStringArray(["%s: TEXCOORD_0 and TEXCOORD_1 do not agree in length" % where])

	var seen_rail: bool = false
	var seen_bed: bool = false
	for index: int in uv2s.size():
		var value: float = uv2s[index].x
		var rounded: float = floor(value + 0.5)
		if absf(value - rounded) > 0.01:
			return PackedStringArray(
				[
					(
						(
							"%s: TEXCOORD_1.x is %f at vertex %d, which is not a whole class. "
							% [where, value, index]
						)
						+ "The channel has been interpolated — check the importer's UV2 settings."
					)
				]
			)
		if rounded == TRAMWAY_CLASS_RAIL:
			seen_rail = true
		elif rounded == TRAMWAY_CLASS_BED:
			seen_bed = true
		else:
			return PackedStringArray(
				[
					(
						"%s: TEXCOORD_1.x is class %d at vertex %d, which is neither bed nor rail"
						% [where, int(rounded), index]
					)
				]
			)

		var along: float = uv2s[index].y
		if along < -TRACK_M_TOLERANCE or along > MAX_TRACK_M + TRACK_M_TOLERANCE:
			return PackedStringArray(
				[
					(
						"%s: TEXCOORD_1.y is %f m at vertex %d, outside the region"
						% [where, along, index]
					)
				]
			)

	var problems: PackedStringArray = []
	if not seen_rail:
		problems.append("%s carries no rail vertices; the whole tramway would shade as bed" % where)
	if not seen_bed:
		problems.append("%s carries no bed vertices; every track lost its bed" % where)
	return problems
