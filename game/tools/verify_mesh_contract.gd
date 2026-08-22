extends SceneTree

## Does the no-texture contract still refuse what it is supposed to refuse?
##
## ⚠️ **`Q63` turned an absolute rule into a conditional one, and a conditional
## rule needs a test the absolute one never did.** Before it, "no uniform holds a
## `Texture`" was one branch that every `verify_*` tool exercised on every run
## simply by passing. Now `check_surface` has a budget parameter, so the *refusal*
## paths are reachable only by a caller that declares one — and no shipped asset
## declares one yet. Nothing in `check.sh` would notice if they stopped working,
## and the first thing to notice would be an image shipping in a bundle specified
## to carry none.
##
## ⚠️ **So this asserts the failures, not the successes.** Every other verify tool
## proves a real asset conforms; the risk here is the opposite one — a check that
## has quietly stopped catching anything, which is the failure mode
## `mesh_contract.gd`'s own header is written about ("the copy that drifts is the
## one that quietly stops catching anything").
##
## ⚠️ **Runs without a built region**, like `verify_beam_budget.gd`: it builds its
## own one-triangle meshes, so CI checks it on every push where the asset tools
## are skipped. That is precisely where a contract regression would otherwise sit
## unseen.
##
## ⚠️ **Nothing here references a `class_name` global.** A `--script` tool that
## does fails to *parse* on a fresh clone, where `global_script_class_cache.cfg`
## has not been written yet — `_init` never runs, `quit(1)` is never reached, and
## the SceneTree exits **0** having checked nothing. `ARCHITECTURE.md` records
## that trap, so the contract is `preload`ed by path, as every other verify tool
## does — `ARCHITECTURE.md` states that as the rule.

const MeshContract = preload("res://scripts/city/mesh_contract.gd")
## Comfortably above the stub textures below and comfortably below the atlas
## `P3-20` will declare. Nothing ships against this number; it exists so the
## over-budget path has something to exceed.
const PROBE_BUDGET_PX := 8192

var _failed: int = 0


func _init() -> void:
	# The rule as it stood before `Q63`, which is still the rule wherever a call
	# site says nothing. This is the ratchet: if only one assertion here survives,
	# it should be this one.
	_expect_refused(
		"an undeclared texture",
		_check(_surface(_texture(64, 64)), 0),
		"binds an undeclared texture"
	)

	# ...and the other half of that: no texture, no declaration, no complaint.
	# Without this the whole check could be passing by refusing everything.
	_expect_clean("no texture and no declaration", _check(_surface(null), 0))

	# A declaration admits a texture, which is the point of the amendment.
	_expect_clean(
		"a declared texture inside its budget", _check(_surface(_texture(64, 64)), PROBE_BUDGET_PX)
	)

	# ⚠️ The budget is asserted rather than recorded. A declaration that admitted
	# any size would make `PROGRESS.md`'s `Texture memory` metric a comment.
	_expect_refused(
		"a declared texture over its budget",
		_check(_surface(_texture(256, 256)), PROBE_BUDGET_PX),
		"against a declared budget"
	)

	# ⚠️ The quiet half. An undeclared texture is loud — the asset ships an image
	# and the contract says so. A *declared* texture that never arrives is silent:
	# the sampler reads white, vertex colour still reaches the pixel, and the city
	# renders as it did before the atlas existed.
	_expect_refused(
		"a declared texture that never arrived",
		_check(_surface(null), PROBE_BUDGET_PX),
		"binds none"
	)

	# ⚠️ **The budget is the surface's total, and the first version compared each
	# texture to it separately.** Two 64x64 textures are 8192 pixels together and
	# 4096 apart, so under a per-texture rule they passed a budget they exactly
	# consume — and a third would too. This is the assertion that says so.
	_expect_refused(
		"two declared textures that exceed the budget together",
		_check(_two_texture_surface(), PROBE_BUDGET_PX - 1),
		"in total against a declared budget"
	)

	# The same two rules through the `BaseMaterial3D` path.
	_expect_refused(
		"an undeclared texture in an albedo slot",
		_check(_standard_surface(_texture(64, 64)), 0),
		"binds an undeclared texture"
	)
	_expect_clean(
		"a declared albedo texture inside its budget",
		_check(_standard_surface(_texture(64, 64)), PROBE_BUDGET_PX)
	)

	# ⚠️ **An `AtlasTexture` reports its region, not its atlas** — the shape
	# `P3-20` invites, and the one that would pass a budget while shipping
	# megabytes if the contract took `get_width()` at its word.
	var atlas := AtlasTexture.new()
	atlas.atlas = _texture(2048, 2048)
	atlas.region = Rect2(0, 0, 32, 32)
	_expect_refused(
		"an atlas region standing in for its 2048 x 2048 atlas",
		_check(_standard_surface(atlas), PROBE_BUDGET_PX),
		"in total against a declared budget"
	)

	_finish()


## One surface carrying `texture` on a shader that samples it, or none.
func _surface(texture: Texture2D) -> ArrayMesh:
	var mesh := ArrayMesh.new()
	var arrays: Array = []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = PackedVector3Array([Vector3.ZERO, Vector3.RIGHT, Vector3.UP])
	# Present because `check_surface` defaults to demanding it, and this tool is
	# about the texture branch rather than that one.
	arrays[Mesh.ARRAY_COLOR] = PackedColorArray([Color.RED, Color.RED, Color.RED])
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)

	var shader := Shader.new()
	shader.code = (
		"shader_type spatial;\nuniform sampler2D probe_atlas;\n"
		+ "void fragment() { ALBEDO = texture(probe_atlas, UV).rgb; }"
	)
	var material := ShaderMaterial.new()
	material.shader = shader
	if texture != null:
		material.set_shader_parameter("probe_atlas", texture)
	mesh.surface_set_material(0, material)
	return mesh


## The same probe as `_surface`, but with the `BaseMaterial3D` the importer gives
## an asset that never got a shader.
##
## ⚠️ **Without this the slot loop is never exercised.** It is where `Q63` added
## the most new code, and by this tool's own premise no shipped asset will ever
## reach it under a budget — so nothing else would notice it breaking.
func _standard_surface(texture: Texture2D) -> ArrayMesh:
	var mesh: ArrayMesh = _surface(null)
	var material := StandardMaterial3D.new()
	material.vertex_color_use_as_albedo = true
	if texture != null:
		material.albedo_texture = texture
	mesh.surface_set_material(0, material)
	return mesh


## Two 64 x 64 textures on one surface — 8192 pixels together, 4096 apart.
func _two_texture_surface() -> ArrayMesh:
	var mesh: ArrayMesh = _surface(_texture(64, 64))
	var material := mesh.surface_get_material(0) as ShaderMaterial
	material.shader.code = (
		"shader_type spatial;\nuniform sampler2D probe_atlas;\nuniform sampler2D probe_second;\n"
		+ "void fragment() { ALBEDO = (texture(probe_atlas, UV) + texture(probe_second, UV)).rgb; }"
	)
	material.set_shader_parameter("probe_second", _texture(64, 64))
	return mesh


func _texture(width: int, height: int) -> Texture2D:
	return ImageTexture.create_from_image(
		Image.create_empty(width, height, false, Image.FORMAT_RGB8)
	)


func _check(mesh: ArrayMesh, budget_px: int) -> PackedStringArray:
	return MeshContract.check_surface(mesh, 0, "probe", true, budget_px)


## ⚠️ Matched on a fragment of the message, not merely on "something failed".
## Three of these refuse for three different reasons, and a bug that collapsed
## them into one would still leave every assertion here green.
func _expect_refused(label: String, problems: PackedStringArray, fragment: String) -> void:
	if problems.is_empty():
		_fail("%s was accepted" % label)
		return
	# ⚠️ **Exactly one, not at least one.** Returning on the first match would let
	# a regression that emits the right problem *plus* spurious extras stay green,
	# and `_expect_clean` only covers the opposite failure of refusing everything.
	if problems.size() != 1:
		_fail("%s drew %d problems, expected 1: %s" % [label, problems.size(), ", ".join(problems)])
		return
	if not problems[0].contains(fragment):
		_fail("%s was refused, but for the wrong reason: %s" % [label, problems[0]])
		return
	print("  ok    %s is refused" % label)


func _expect_clean(label: String, problems: PackedStringArray) -> void:
	if not problems.is_empty():
		_fail("%s was refused: %s" % [label, ", ".join(problems)])
		return
	print("  ok    %s passes" % label)


func _fail(message: String) -> void:
	_failed += 1
	printerr("  FAIL  %s" % message)


func _finish() -> void:
	if _failed > 0:
		printerr("mesh contract: %d check(s) failed" % _failed)
		quit(1)
		return
	print("  ok    verify_mesh_contract")
	quit(0)
