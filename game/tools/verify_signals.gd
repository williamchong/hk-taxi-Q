## Checks the generated traffic signal heads against the data contract, headless.
##
## `P3-17` delivers TD's published signal estate as static unlit geometry, and
## the facts that decision rests on are engine-side: whether the importer
## dispatched the shader on the material name, whether it built a collider it
## must *not* have, and whether every triangle still faces the way it was wound
## to. Run:
##
##     godot --headless --path game --script res://tools/verify_signals.gd
##
## Exits non-zero if the signals are present and fail any check.
##
## ⚠️ **Absence is a pass, and here that is not even unusual.** A city whose
## estate publishes no signal layer draws none — and so does one whose publisher
## numbers its heads outside `head_prefixes`, because `REFNAME` has no published
## domain and the gate is a rule about *spelling* this project wrote. What stops
## that becoming a silent skip is `verify_city.gd`, whose `_check_documents`
## asserts a *named* signals asset exists and matches this file's constant — so a
## manifest naming `signals.glb` with the file gone fails there.
extends SceneTree

const GeneratedSignals = preload("res://scripts/city/generated_signals.gd")
const MeshContract = preload("res://scripts/city/mesh_contract.gd")

## One primitive, so the whole region's signals cost one draw call — the rule the
## road surface, the tiles, the tramway, the arrows, the boxes and the markings
## are all held to.
##
## ⚠️ **Held despite the layer having four colours**, which is what would most
## plausibly have split it. It does not, because the colour rides `COLOR_0`
## rather than a material per aspect — see `signs.gdshader`. And unlike the
## signs there is no second primitive here: this layer ships no lettering and no
## image at all, so `check_surface` runs on the default budget of **0** and any
## texture that appeared would fail the bundle.
const SURFACES: int = 1

## The material the signals must end up with, mirroring `SHADERS` in
## `tools/generated_scene_import.gd` and `SIGNALS_MATERIAL` in
## `etl/pipeline/signals.py`.
##
## 🔴 **Checked through its `resource_path`, and that is the point rather than an
## implementation detail.** This layer *shares* `signs.gdshader` — a layer is a
## parameterisation, not a shader (`Q61`, `Q71`) — so `check_shader_source` would
## happily pass a signal head handed `signs.tres`, which is a head lit as
## retroreflective sheeting with a glowing dark lens. The path is the only thing
## that tells the two apart. Do not swap this for the shader check.
##
## ⚠️ Checked at all because the dispatch fails *quietly*: the livery is on the
## vertex, so a head that kept its imported `BaseMaterial3D` still draws the
## right boxes in the right places in the right colours — it just loses
## `vertex_srgb_to_linear`, so the whole city's signals render pale (`Q27`).
const SIGNALS_MATERIAL: String = "res://tuning/signals.tres"


func _init() -> void:
	if not GeneratedSignals.is_present():
		print("  skip  no signal heads shipped for this region")
		quit(0)
		return

	var packed: PackedScene = GeneratedSignals.load_signals()
	if packed == null:
		# Present but unloadable, which is not the same as absent — the hint
		# about rebuilding would be the wrong advice here.
		printerr("  FAIL  %s exists but did not load as a scene" % GeneratedSignals.PATH)
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
		print("  ok    ", GeneratedSignals.PATH)
	quit(1 if not problems.is_empty() else 0)


func _check(scene_root: Node3D) -> PackedStringArray:
	var problems: PackedStringArray = []

	var mesh: ArrayMesh = MeshContract.single_primitive(scene_root, SURFACES, problems)
	if mesh == null:
		return problems

	for surface: int in mesh.get_surface_count():
		var where: String = "surface %d" % surface
		# `true`: this mesh ships `COLOR_0` and the shader reads it — a head is
		# four colours in one draw call. The no-texture guarantee runs on the
		# default budget of 0, which is what keeps this layer imageless.
		problems.append_array(MeshContract.check_surface(mesh, surface, where, true))
		problems.append_array(
			MeshContract.check_shader_material(mesh, surface, where, SIGNALS_MATERIAL)
		)
		problems.append_array(
			MeshContract.check_stands_upright(
				mesh, surface, where, "signals", "Signals are boxes on posts", 0.5
			)
		)

	problems.append_array(_check_has_no_collision(scene_root))
	return problems


## Street furniture must **not** collide, for the reason the signs must not.
##
## ⚠️ **The reasoning runs the other way from the arrows', and is weaker** —
## `verify_signs.gd`'s paragraph, and it applies here with one extra edge. A
## signal post is a real obstacle a real car really would hit, so its absence is
## a **budget** decision rather than a correctness one: 415 posts is 415
## collision bodies, and `P2-6` has not measured a frame on the device floor.
## The extra edge is *where they stand*: a signal post sits at a junction mouth,
## which is exactly where the player is braking and turning, so this is the
## layer whose colliders would be felt most. `GAME_DESIGN.md` puts breakaway
## posts in `B3`, and the whole guard against one arriving early is the absence
## of a `-col` suffix in one string in `signals.py`.
func _check_has_no_collision(scene_root: Node3D) -> PackedStringArray:
	return MeshContract.check_no_collision(
		scene_root, "the signals", "SIGNALS_MESH_NAME in etl/pipeline/signals.py"
	)
