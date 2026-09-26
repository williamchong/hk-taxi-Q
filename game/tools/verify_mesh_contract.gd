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

	_check_winding()
	_check_collision_and_material()
	_check_shapes()
	_finish()


## ⚠️ **Every other `MeshContract` check ran only against a built region until
## this block, and there it only ever passed.** Winding is the one that has
## shipped invisible geometry three times (`check_faces_up`'s header), and its
## negated sign (`Q59`) was pinned by nothing CI could run. So each rule below
## is shown to accept one triangle and refuse its mirror, on meshes built here.
##
## The triangle is in the ground plane with its corners (0,0,0) → (1,0,0) →
## (0,0,1): under the contract's own cross product that order faces up, and the
## reversed order faces down. If Godot's winding convention ever moved, the
## first assertion would fail rather than go quietly green — which is the
## finding, and the reason not to "fix" the sign to make it pass.
func _check_winding() -> void:
	var up: ArrayMesh = _triangle(Vector3.ZERO, Vector3.RIGHT, Vector3.BACK, Vector3.UP)
	var down: ArrayMesh = _triangle(Vector3.ZERO, Vector3.BACK, Vector3.RIGHT, Vector3.UP)
	_expect_clean(
		"a triangle wound to face up", MeshContract.check_faces_up(up, 0, "probe", "paint")
	)
	_expect_refused(
		"the same triangle wound the other way",
		MeshContract.check_faces_up(down, 0, "probe", "paint"),
		"do not face up"
	)
	_expect_refused(
		"a surface with no index buffer",
		MeshContract.check_faces_up(_surface(null), 0, "probe", "paint"),
		"no index buffer"
	)

	# A wall: the triangle stood on its edge, wound to agree with its normal.
	var wall: ArrayMesh = _triangle(Vector3.ZERO, Vector3.UP, Vector3.BACK, Vector3.LEFT)
	var against: ArrayMesh = _triangle(Vector3.ZERO, Vector3.UP, Vector3.BACK, Vector3.RIGHT)
	_expect_clean(
		"an upright triangle wound with its normal",
		MeshContract.check_stands_upright(wall, 0, "probe", "posts", "a post", 1.0)
	)
	_expect_refused(
		"the same triangle with its normal reversed",
		MeshContract.check_stands_upright(against, 0, "probe", "posts", "a post", 1.0),
		"wound against their own normal"
	)
	_expect_refused(
		"a flat triangle held to an upright share of 1.0",
		MeshContract.check_stands_upright(up, 0, "probe", "posts", "a post", 1.0),
		"laid flat"
	)
	var bare: ArrayMesh = _triangle(Vector3.ZERO, Vector3.UP, Vector3.BACK, Vector3.ZERO)
	_expect_refused(
		"an upright triangle with no normals",
		MeshContract.check_stands_upright(bare, 0, "probe", "posts", "a post", 1.0),
		"no normals"
	)


## The collider rule and the material dispatch, each from both sides.
func _check_collision_and_material() -> void:
	var clean := Node3D.new()
	_expect_clean(
		"a node with no StaticBody3D under it",
		MeshContract.check_no_collision(clean, "probe", "PROBE")
	)
	clean.free()
	var built := Node3D.new()
	built.add_child(StaticBody3D.new())
	_expect_refused(
		"a node that built a collider",
		MeshContract.check_no_collision(built, "probe", "PROBE"),
		"must build none"
	)
	built.free()

	var expected: String = "res://probe_material.tres"
	var shared: ArrayMesh = _surface(null)
	(shared.surface_get_material(0) as ShaderMaterial).take_over_path(expected)
	_expect_clean(
		"a surface on the shared material it was asked for",
		MeshContract.check_shader_material(shared, 0, "probe", expected)
	)
	_expect_refused(
		"a surface on a ShaderMaterial from nowhere",
		MeshContract.check_shader_material(_surface(null), 0, "probe", expected),
		"not %s" % expected
	)
	_expect_refused(
		"a surface left on the importer's BaseMaterial3D",
		MeshContract.check_shader_material(_standard_surface(null), 0, "probe", expected),
		"did not import with a ShaderMaterial"
	)


## `single_primitive` and `library_meshes` refuse the wrong count of meshes and
## surfaces, and hand back what they collected when they accept.
func _check_shapes() -> void:
	var one := Node3D.new()
	one.add_child(_instance(1))
	var problems: PackedStringArray = []
	var mesh: ArrayMesh = MeshContract.single_primitive(one, 1, problems)
	_expect_clean("one instance with one surface", problems)
	if mesh == null:
		_fail("single_primitive accepted one instance and handed back nothing")
	one.free()

	var two := Node3D.new()
	two.add_child(_instance(1))
	two.add_child(_instance(1))
	problems = []
	MeshContract.single_primitive(two, 1, problems)
	_expect_refused("two instances where one is the rule", problems, "expected one MeshInstance3D")
	two.free()

	var doubled := Node3D.new()
	doubled.add_child(_instance(2))
	problems = []
	MeshContract.single_primitive(doubled, 1, problems)
	_expect_refused("one instance with two surfaces", problems, "expected 1")
	problems = []
	MeshContract.library_meshes(doubled, 1, problems)
	_expect_refused("a library mesh with two surfaces", problems, "expected 1")
	doubled.free()

	var empty := Node3D.new()
	problems = []
	MeshContract.library_meshes(empty, 1, problems)
	_expect_refused("a library with no mesh at all", problems, "no MeshInstance3D")
	empty.free()


## One indexed triangle `a` → `b` → `c` with every vertex's normal `normal`,
## or no normals at all for `Vector3.ZERO`.
func _triangle(a: Vector3, b: Vector3, c: Vector3, normal: Vector3) -> ArrayMesh:
	var mesh := ArrayMesh.new()
	var arrays: Array = []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = PackedVector3Array([a, b, c])
	arrays[Mesh.ARRAY_INDEX] = PackedInt32Array([0, 1, 2])
	if not normal.is_zero_approx():
		arrays[Mesh.ARRAY_NORMAL] = PackedVector3Array([normal, normal, normal])
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	return mesh


## A MeshInstance3D carrying an ArrayMesh of `surfaces` surfaces.
func _instance(surfaces: int) -> MeshInstance3D:
	var mesh := ArrayMesh.new()
	for _surface_index: int in surfaces:
		var arrays: Array = []
		arrays.resize(Mesh.ARRAY_MAX)
		arrays[Mesh.ARRAY_VERTEX] = PackedVector3Array([Vector3.ZERO, Vector3.RIGHT, Vector3.UP])
		mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	var instance := MeshInstance3D.new()
	instance.mesh = mesh
	return instance


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
