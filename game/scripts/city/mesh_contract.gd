## The mesh rules every generated asset is held to, and how to measure one.
##
## `P1-2` states them for building tiles and `P1-4` for the road surface, and
## they are the same rules for the same reason: one untextured, vertex-coloured
## primitive is what makes a draw call cheap enough for the mobile tier. Written
## once because two copies drift, and the copy that drifts is the one that
## quietly stops catching anything — the road surface's first version checked
## only `albedo_texture` and never checked `vertex_color_use_as_albedo` at all,
## which is exactly the flag that decides whether the asset renders white.
##
## `triangles` and `bounds` are here for the same argument rather than a
## different one. Every preview and every verify tool wants one or both, and
## each carries a trap that is easy to get subtly wrong in a private copy.
extends RefCounted


## Triangles in `node` and everything below it.
##
## `surface_get_array_index_len` is O(1). Counting from
## `surface_get_arrays(...)[ARRAY_INDEX]` instead pulls every vertex buffer back
## off the RenderingServer to read one integer — measured at 440 µs against
## 0.1 µs on a 1.5 MB asset — and returns null on a non-indexed surface, where
## this returns 0.
static func triangles(node: Node) -> int:
	var count: int = 0
	for instance: MeshInstance3D in node.find_children("*", "MeshInstance3D", true, false):
		if instance.mesh != null:
			count += mesh_triangles(instance.mesh)
	return count


## Triangles in one mesh across its surfaces — what `triangles` sums, and what
## a prop layer multiplies by its placement count (`P5-2`).
static func mesh_triangles(mesh: Mesh) -> int:
	var count: int = 0
	for surface: int in mesh.get_surface_count():
		count += mesh.surface_get_array_index_len(surface) / 3
	return count


## The union of every mesh below `node`, in `node`'s own space. A zero-size box
## means there was nothing to measure, which callers report rather than pass.
##
## Transforms are accumulated by hand rather than read from
## `Node3D.global_transform`, which returns identity and pushes an error outside
## the tree — and a headless `--script` run has no tree to add to. The importer
## is free to put a mesh under a transformed root, and that is exactly what a
## georeference check must not assume away.
static func bounds(node: Node) -> AABB:
	var boxes: Array[AABB] = []
	_collect(node, Transform3D.IDENTITY, boxes)
	return union(boxes)


## The smallest box containing every box given, or a zero-size one for none.
##
## Seeded from the first entry rather than from `AABB()`, which is not a neutral
## element: it is a zero-size box *at the world origin*, and the region starts
## there, so merging one in silently stretches the result back to (0, 0, 0).
## Written once here because the same trap is one loop away in `_collect`, and
## `tools/verify_city.gd` needs it over a tile's tiers.
static func union(boxes: Array[AABB]) -> AABB:
	if boxes.is_empty():
		return AABB()
	var box: AABB = boxes[0]
	for index: int in range(1, boxes.size()):
		box = box.merge(boxes[index])
	return box


static func _collect(node: Node, parent: Transform3D, into: Array[AABB]) -> void:
	var spatial := node as Node3D
	var here: Transform3D = parent * spatial.transform if spatial != null else parent

	var instance := node as MeshInstance3D
	# A mesh with no surfaces reports a zero-size box at the origin, so merging
	# it in would drag the union back there — the same trap an empty seed is.
	if instance != null and instance.mesh != null and instance.mesh.get_surface_count() > 0:
		into.append(here * instance.mesh.get_aabb())

	for child: Node in node.get_children():
		_collect(child, here, into)


## Triangles below `node` whose centroid falls inside `box`, in `node`'s space.
##
## The excluded-footprint probe (`P3-6`, `verify_landmarks.gd`). Here because
## it carries both of this file's traps at once: transforms are accumulated by
## hand for the reason `bounds` gives, and the triangle walk pulls vertex
## buffers back off the RenderingServer — the expensive path `triangles`
## documents — so each mesh's cheap `get_aabb` gates the pull, which also
## skips whole meshes (the terrain never reaches a probe floored above it).
static func triangles_inside(node: Node, box: AABB) -> int:
	return _count_inside(node, Transform3D.IDENTITY, box)


static func _count_inside(node: Node, parent: Transform3D, box: AABB) -> int:
	var spatial := node as Node3D
	var here: Transform3D = parent * spatial.transform if spatial != null else parent

	var count: int = 0
	var instance := node as MeshInstance3D
	if (
		instance != null
		and instance.mesh != null
		and instance.mesh.get_surface_count() > 0
		and (here * instance.mesh.get_aabb()).intersects(box)
	):
		count += _mesh_triangles_inside(instance.mesh, here, box)
	for child: Node in node.get_children():
		count += _count_inside(child, here, box)
	return count


static func _mesh_triangles_inside(mesh: Mesh, here: Transform3D, box: AABB) -> int:
	var count: int = 0
	for surface: int in mesh.get_surface_count():
		var arrays: Array = mesh.surface_get_arrays(surface)
		var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		# Normalised to one loop: a non-indexed surface is the indexed case
		# with the identity ordering.
		var order := PackedInt32Array()
		if arrays[Mesh.ARRAY_INDEX] != null:
			order = arrays[Mesh.ARRAY_INDEX]
		if order.is_empty():
			order = PackedInt32Array(range(vertices.size()))
		for i: int in range(0, order.size(), 3):
			var centroid: Vector3 = (
				(vertices[order[i]] + vertices[order[i + 1]] + vertices[order[i + 2]]) / 3.0
			)
			if box.has_point(here * centroid):
				count += 1
	return count


## True where the `-col` name suffix imported as a static body.
##
## The suffix is the only thing that carries collision from the ETL into the
## engine, so "did the importer act on it" is a question both the road surface
## and the building tiles have to ask.
static func has_collision(node: Node) -> bool:
	return colliders(node) > 0


## How many static bodies the node's subtree carries. The previews print it
## because every generated layer but the road surface must carry none (`Q74`),
## and `fence.gd` prints it because its bodies are built by hand.
static func colliders(node: Node) -> int:
	return node.find_children("*", "StaticBody3D", true, false).size()


## The one `ArrayMesh` a single-primitive asset must carry, or `null` with
## `problems` saying why.
##
## Here because there are now three of these — the road surface, the tramway and
## the arrows — and this sixteen-line preamble was byte-identical in all three,
## comment included. `Q58` predicted exactly that: "`mesh_contract.gd` states the
## repo's own trigger for this, so a third copy should force it."
##
## Returns through `problems` rather than as a tuple because GDScript has no
## tuple return and `_check_shader_surface` below already established the
## out-parameter shape — which keeps every caller statically typed.
##
## ⚠️ `surfaces` is **exact, not a ceiling**: a mesh with no surfaces at all
## would otherwise pass every per-surface check its caller runs, by never
## entering the loop.
static func single_primitive(
	scene_root: Node, surfaces: int, problems: PackedStringArray
) -> ArrayMesh:
	var instances: Array[Node] = scene_root.find_children("*", "MeshInstance3D", true, false)
	if instances.size() != 1:
		problems.append("expected one MeshInstance3D, found %d" % instances.size())
		return null

	var mesh := (instances[0] as MeshInstance3D).mesh as ArrayMesh
	if mesh == null:
		problems.append("the MeshInstance3D carries no ArrayMesh")
		return null
	if mesh.get_surface_count() != surfaces:
		problems.append("%d surfaces, expected %d" % [mesh.get_surface_count(), surfaces])
	return mesh


## Problems with an asset that must build **no** collider — the inverse of
## `check_collision` below.
##
## Two assets are in this class and both are things the car drives over rather
## than into: the tramway lies on ground that is already solid, and an arrow is
## paint. In both the whole guard is the *absence* of a `-col` suffix in one
## string in the ETL, which `constant` names so the message says where to look.
static func check_no_collision(node: Node, asset: String, constant: String) -> PackedStringArray:
	var bodies: Array[Node] = node.find_children("*", "StaticBody3D", true, false)
	if bodies.is_empty():
		return PackedStringArray()
	return PackedStringArray(
		[
			(
				"%s built %d collider(s); it must build none. " % [asset, bodies.size()]
				+ "Check that %s has no `-col` suffix." % constant
			)
		]
	)


## Problems with the collider the `-col` suffix should have built, or an empty
## array if it conforms.
##
## Nothing on the Python side can see any of this: the ETL writes a node *name*,
## and what Godot's importer made of it is an engine fact. Here rather than in
## either caller because the road surface asked first and the tiles ask the same
## question — and a private second copy is what this file exists to stop.
static func check_collision(node: Node) -> PackedStringArray:
	var problems: PackedStringArray = []
	var bodies: Array[Node] = node.find_children("*", "StaticBody3D", true, false)
	if bodies.is_empty():
		problems.append("no StaticBody3D — the `-col` name suffix did not import as collision")
		return problems

	var shapes: Array[Node] = bodies[0].find_children("*", "CollisionShape3D", true, false)
	if shapes.is_empty():
		problems.append("the StaticBody3D has no CollisionShape3D")
	elif ((shapes[0] as CollisionShape3D).shape as ConcavePolygonShape3D) == null:
		problems.append("collision is not a ConcavePolygonShape3D")
	return problems


## The surface ended up on the shader its ETL asked for, or why it did not.
##
## glTF cannot say "use this shader", so the ETL writes a material *name* and
## `tools/generated_scene_import.gd` dispatches on it. That dispatch has **no
## failing state**: if the ETL stops writing the name, or the import script stops
## recognising it, the asset quietly keeps its default `BaseMaterial3D`, passes
## every other check here, and renders as whatever it looked like before the
## shader existed — a flat-coloured city before `P3-7`, an unmarked road before
## `P3-12`. There is nothing to see and nothing else to catch it.
##
## Here rather than in either caller because the tiles and the road surface ask
## the identical question of different paths, which is what this file is for.
## The message both checks below give when a surface carries no ShaderMaterial.
##
## Extracted because the two were byte-identical apart from which name they
## quoted, and this file exists to stop exactly that — a copy that drifts is the
## copy that quietly stops catching anything.
static func _no_shader_material(where: String, expected: String) -> PackedStringArray:
	return PackedStringArray(
		[
			(
				(
					"%s did not import with a ShaderMaterial; the ETL's material name and "
					+ "`tools/generated_scene_import.gd` have stopped agreeing, so it is "
					+ "drawing as though %s did not exist"
				)
				% [where, expected]
			)
		]
	)


static func check_shader_material(
	mesh: Mesh, surface: int, where: String, expected: String
) -> PackedStringArray:
	var material := mesh.surface_get_material(surface) as ShaderMaterial
	if material == null:
		return _no_shader_material(where, expected)
	if material.resource_path != expected:
		return PackedStringArray(["%s uses %s, not %s" % [where, material.resource_path, expected]])
	return PackedStringArray()


## The same dispatch check for a material that had to be **duplicated** (`P3-20`).
##
## 🔴 **A duplicate has no `resource_path`**, so `check_shader_material` above
## reports it as using "" and fails a correctly wired surface. That is not a flaw
## in it: comparing the path is the stronger check and every shared material in
## this bundle should keep being held to it. What cannot is the sign lettering,
## whose material carries a **per-region texture** — generated city data,
## gitignored, different for every region — so it cannot be one shared resource
## and cannot be baked into the committed `.tres` either.
##
## So the identity to check is the **shader** rather than the resource, which is
## the thing the `.tres` would have contributed anyway. `expected_material` is
## carried only so the failure names the file a reader has to go and open.
##
## ⚠️ **Do not reach for this to quiet a failing `check_shader_material`.** The
## two are not interchangeable: a surface that could share a material and does
## not is a draw call nobody asked for, and this function would pass it.
static func check_shader_source(
	mesh: Mesh, surface: int, where: String, expected_shader: String, expected_material: String
) -> PackedStringArray:
	var material := mesh.surface_get_material(surface) as ShaderMaterial
	if material == null:
		return _no_shader_material(where, expected_material)
	var shader: Shader = material.shader
	if shader == null or shader.resource_path != expected_shader:
		var found: String = "no shader" if shader == null else shader.resource_path
		return PackedStringArray(
			["%s runs %s, not %s (from %s)" % [where, found, expected_shader, expected_material]]
		)
	return PackedStringArray()


## The importer settings that would destroy a `TEXCOORD_1` payload have not
## drifted. `payload` names what is at stake, for the caller's report.
##
## `meshes/light_baking = 2` (Static Lightmaps) makes Godot's importer generate
## its own UV2 unwrap, silently overwriting the payload with texture coordinates
## that pass every visual inspection — `docs/ART_DESIGN.md` records the hazard.
## 1 is Static, which leaves the channel alone.
##
## Here rather than in either caller for this file's usual reason, and it earned
## it immediately: `P3-12` gave the road surface a UV2 payload of its own, and
## the check it needed already existed as a private copy in `verify_tiles.gd`.
static func check_uv2_import_settings(path: String, payload: String) -> PackedStringArray:
	var import_path: String = path + ".import"
	var file := FileAccess.open(import_path, FileAccess.READ)
	if file == null:
		return PackedStringArray(["%s has no .import beside it" % path])
	if not file.get_as_text().contains("meshes/light_baking=1"):
		return PackedStringArray(
			[
				(
					(
						"%s: meshes/light_baking is not 1 (Static). Static Lightmaps "
						+ "regenerates UV2 and overwrites the %s."
					)
					% [import_path, payload]
				)
			]
		)
	return PackedStringArray()


## Problems with one surface of one mesh, or an empty array if it conforms.
##
## `where` names the surface for the caller's report — surface indices restart
## per `MeshInstance3D`, so "surface 0" is ambiguous without it.
##
## Two shapes conform, because `P3-7` gave tiles a shader and left everything
## else alone. What both must satisfy is the same rule the untextured,
## vertex-coloured primitive has always had — the colour must reach the pixel,
## and no *undeclared* texture may be sampled. How that is achieved differs: a
## `BaseMaterial3D` needs a flag set at import, a `ShaderMaterial` writes
## `ALBEDO` itself. Checked here rather than at the call sites because the road
## surface and the tiles both ask, and a private second copy is what this file
## exists to stop.
##
## ⚠️ **"no texture may be sampled" was absolute until `Q63`, and the word that
## replaced it is *undeclared*, not *some*.** `texture_budget_px` defaults to 0,
## which is the old refusal exactly, so every call site that says nothing keeps
## it and the bundle cannot grow an image by accident. A call site that passes a
## budget is declaring one on purpose, in a diff, and buys a ceiling with it:
## the texture is measured and fails above the budget, and the *absence* of a
## declared texture fails too. `Q63` chose this over deleting the check, because
## a rule that is merely generous is a rule nothing reads — and `ART_DESIGN.md`
## records that the load-bearing reason buildings stay untextured is `merge`
## refusing them, which is a separate rule this does not touch.
static func check_surface(
	mesh: Mesh,
	surface: int,
	where: String,
	expect_vertex_colours: bool = true,
	texture_budget_px: int = 0
) -> PackedStringArray:
	var problems: PackedStringArray = []

	# ⚠️ **The opt-out is a parameter rather than an omitted call**, so a mesh
	# that ships no `COLOR_0` still gets every other guarantee here and says at
	# its call site why it is different. The one caller that passes `false` is
	# `verify_arrows.gd`: `Q33`'s palette rule makes the `materials:` table the
	# single place a *city* colour is written, and `Q53` deliberately put road
	# paint outside that table — so an arrow's white lives in `arrows.tres`
	# beside the lane dividers it matches, and there is no vertex colour for it
	# to be written into. Everything the ETL paints from the palette still
	# carries one, and still fails here without it.
	if expect_vertex_colours and not (mesh.surface_get_format(surface) & Mesh.ARRAY_FORMAT_COLOR):
		problems.append("%s carries no vertex colours" % where)

	var material: Material = mesh.surface_get_material(surface)
	if material == null:
		problems.append("%s has no material" % where)
		return problems

	var shaded := material as ShaderMaterial
	if shaded != null:
		return _check_shader_surface(shaded, where, problems, texture_budget_px)

	var standard := material as BaseMaterial3D
	if standard == null:
		problems.append("%s is neither a BaseMaterial3D nor a ShaderMaterial" % where)
		return problems

	# Set at import by `tools/generated_scene_import.gd`, because glTF has no
	# such flag — COLOR_0 always multiplies base colour there. Without it the
	# asset imports white however good its vertex colours are.
	if not standard.vertex_color_use_as_albedo:
		problems.append("%s ignores its vertex colours" % where)
	var bound: Dictionary = {}
	for slot: int in [
		BaseMaterial3D.TEXTURE_ALBEDO,
		BaseMaterial3D.TEXTURE_NORMAL,
		BaseMaterial3D.TEXTURE_ORM,
	]:
		var texture: Texture = standard.get_texture(slot)
		if texture != null:
			bound["slot %d" % slot] = texture
	problems.append_array(_check_declared_textures(bound, where, texture_budget_px))
	return problems


## The same two guarantees, asked of a `ShaderMaterial`.
##
## A shader can do anything, so this checks what is checkable: that a shader is
## attached at all, and that any uniform holding a texture was declared.
static func _check_shader_surface(
	material: ShaderMaterial, where: String, problems: PackedStringArray, texture_budget_px: int
) -> PackedStringArray:
	if material.shader == null:
		problems.append("%s is a ShaderMaterial with no shader" % where)
		return problems

	var bound: Dictionary = {}
	for uniform: Dictionary in material.shader.get_shader_uniform_list():
		var name: String = uniform.get("name", "")
		var value: Variant = material.get_shader_parameter(name)
		if value is Texture:
			bound["uniform '%s'" % name] = value
	problems.append_array(_check_declared_textures(bound, where, texture_budget_px))
	return problems


## Every texture bound to one surface, against what the call site declared.
##
## ⚠️ **`texture_budget_px` of 0 is the refusal, and it is the default** — so
## every existing call site keeps `Q63`'s original rule without saying anything,
## and a bundle that has never declared a texture still cannot grow one by
## accident. What changed at `Q63` is only that the refusal became *overridable
## at a call site that says so*, in the shape `expect_vertex_colours` already
## uses above: not "textures are forbidden" but "no texture ships that nobody
## declared".
##
## ⚠️ **The budget is asserted, not recorded.** A declaration with no ceiling
## would be a comment — `PROGRESS.md`'s `Texture memory` metric only stays
## meaningful if something fails when it is exceeded, and a metric nothing
## enforces is the thing `Q63` warned every later stage would learn from.
##
## ⚠️ **The budget is the surface's TOTAL, not each texture's**, and the first
## version got that wrong: it compared every texture to the budget separately, so
## two textures at exactly the budget passed and three were still fine. A ceiling
## that whole numbers of textures can walk under is not a ceiling. `PROGRESS.md`
## tracks texture memory as a total, and so does this.
##
## ⚠️ **The declared-but-absent case is refused too, and it is the quiet half.**
## An undeclared texture is loud — the asset ships an image and this file says
## so. A *declared* texture that never arrives is silent: the sampler reads
## white, vertex colour still reaches the pixel, every other check passes, and
## the city renders as it did before the atlas existed. That is the same failing
## state `check_shader_material` above is written against.
##
## Pixels rather than bytes because pixels are what the asset can be asked
## without decoding it: the on-GPU cost also depends on the import format and
## mipmaps, so this is a ceiling on the image, not a memory figure.
##
## `bound` maps a human label ("uniform \'atlas\'", "slot 0") to its `Texture`, so
## both material shapes share this tail and the report still names what it found.
static func _check_declared_textures(
	bound: Dictionary, where: String, texture_budget_px: int
) -> PackedStringArray:
	var problems: PackedStringArray = []

	# A negative budget is a call-site typo, and `<= 0` would quietly read it as
	# the strict pre-`Q63` rule — the loudest possible bug hidden in the safest
	# possible behaviour.
	if texture_budget_px < 0:
		problems.append("%s declares a negative texture budget (%d)" % [where, texture_budget_px])
		return problems

	if bound.is_empty():
		if texture_budget_px > 0:
			problems.append(
				(
					"%s declares a texture budget of %d pixels but binds none"
					% [where, texture_budget_px]
				)
			)
		return problems

	if texture_budget_px <= 0:
		for label: String in bound:
			problems.append("%s %s binds an undeclared texture" % [where, label])
		return problems

	var total: int = 0
	var described: PackedStringArray = []
	for label: String in bound:
		var texture: Texture = bound[label]
		var pixels: int = _texture_pixels(texture)
		if pixels < 0:
			problems.append(
				(
					"%s %s binds a %s, which cannot be measured against a pixel budget"
					% [where, label, texture.get_class()]
				)
			)
			continue
		total += pixels
		described.append("%s %d px" % [label, pixels])

	if total > texture_budget_px:
		problems.append(
			(
				"%s binds %s, %d pixels in total against a declared budget of %d"
				% [where, ", ".join(described), total, texture_budget_px]
			)
		)
	return problems


## Pixels in one bound texture, or **-1** where it cannot be measured honestly.
##
## ⚠️ **Three shapes report a size that is not the size that ships**, and each is
## refused rather than trusted:
##
## - 🔴 **`AtlasTexture` reports its REGION, not its atlas** — a 32 x 32 view onto
##   a 2048 x 2048 sheet measures 1,024 px and would pass an 8,192 budget while
##   shipping 4.2 million. That is exactly the shape `P3-20` invites, so it is
##   resolved to the image underneath instead of being taken at its word.
## - **`TextureLayered` and `Texture3D` do answer `get_width()`/`get_height()`** —
##   an earlier version of this comment claimed they do not, and that was wrong —
##   but the answer understates them by their layer or depth count, so width
##   times height is not what they cost.
## - **`PlaceholderTexture2D` reports 1 x 1**, which is a declared texture that
##   did not arrive wearing a size small enough to pass anything.
static func _texture_pixels(texture: Texture) -> int:
	var atlas := texture as AtlasTexture
	if atlas != null:
		return -1 if atlas.atlas == null else _texture_pixels(atlas.atlas)
	if texture is TextureLayered or texture is Texture3D or texture is PlaceholderTexture2D:
		return -1
	var flat := texture as Texture2D
	return -1 if flat == null else flat.get_width() * flat.get_height()


## How far a triangle may tilt off horizontal before it is a fold rather than a
## slope. Ground-plane paint takes its host's grade per vertex, and the steepest
## street in Wan Chai is well inside this; what it catches is a triangle at or
## past vertical, which is a winding failure.
const MIN_FACING_UP: float = 0.1

## How near horizontal a triangle's **normal** must be for the triangle to count
## as standing upright.
##
## ⚠️ **The inverse question to `MIN_FACING_UP`, and it belongs to a different
## family of asset.** That one grades ground-plane paint, where "faces the sky"
## is the correctness condition. This grades street furniture, where the
## overwhelming majority of the mesh faces *sideways* and the caps are the
## legitimate exception. All three callers picked 0.35 independently.
const MAX_UPRIGHT_Y: float = 0.35


## Every triangle of a ground-plane surface faces the sky.
##
## ⚠️ **The failure that fails to nothing.** The arrows, the box junctions and
## the stop lines all run `marking_paint.gdshader`, which is `cull_back`, so
## winding decides visibility and the normal attribute does not: a mesh wound the
## other way is correct geometry, in the correct place, with the correct
## material, and the city simply does not have it in it. The tramway shipped
## exactly that — **5,111 of 5,112** triangles facing the ground — and no frame
## showed it.
##
## Here rather than as a private copy in each verify tool for this file's usual
## reason, and it had three callers the day it moved: `verify_arrows.gd`,
## `verify_boxjunctions.gd` and `verify_roadmarks.gd` held byte-identical copies
## differing only in the noun in the failure string. `check_uv2_import_settings`
## is the precedent — it was a private copy in `verify_tiles.gd` until the road
## surface needed it too.
##
## ⚠️ **`Q71` finished the job this started.** The same three tools also pointed
## at three byte-identical *shaders*, and the rule `single_primitive` states —
## "a third copy should force it" — applies to a `.gdshader` exactly as it does
## to sixteen lines of GDScript. They share `marking_paint.gdshader` now.
##
## Checked here as well as in each stage's own manifest because the two catch
## different things: the ETL's `inverted` counts what the pipeline built, this
## counts what Godot imported, and an import that mirrors an axis moves one
## without the other.
static func check_faces_up(
	mesh: Mesh, surface: int, where: String, noun: String
) -> PackedStringArray:
	var arrays: Array = mesh.surface_get_arrays(surface)
	var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
	if indices.is_empty():
		return PackedStringArray(["%s carries no index buffer to check winding on" % where])

	var inverted: int = 0
	# `floori` of a float divide rather than an integer one: GDScript warns on
	# integer division and `check.sh` promotes warnings to errors, so the plain
	# form does not compile. The count is exact — an index buffer is always a
	# multiple of three.
	var triangle_count: int = floori(indices.size() / 3.0)
	for triangle: int in triangle_count:
		var a: Vector3 = vertices[indices[triangle * 3]]
		var b: Vector3 = vertices[indices[triangle * 3 + 1]]
		var c: Vector3 = vertices[indices[triangle * 3 + 2]]
		# ⚠️ **Negated, because Godot winds front faces clockwise and glTF winds
		# them counter-clockwise.** The sign was established by measurement
		# against `roads.glb` (32,222 of 32,233 down here) and `tram.glb` (5,132
		# of 5,132); if this ever needs revisiting, re-measure against those two
		# rather than re-reading this comment, and do not "fix" either side to
		# agree with the other (`Q59`).
		var cross: Vector3 = (a - b).cross(c - a)
		var length: float = cross.length()
		# A collapsed triangle has no facing to judge. Every stage drops them at
		# twice-area 1e-6, so one here is a rounding survivor rather than a fold.
		if length <= 0.0:
			continue
		if cross.y / length < MIN_FACING_UP:
			inverted += 1
	if inverted == 0:
		return PackedStringArray()
	return PackedStringArray(
		[
			(
				"%s: %d of %d triangles do not face up. " % [where, inverted, triangle_count]
				+ "cull_back draws none of those — %s are invisible, not wrong-looking." % noun
			)
		]
	)


## Every triangle's winding agrees with the normal it was given, and enough of
## the mesh is vertical to rule out the layer having been laid flat.
##
## 🔴 **`check_faces_up`'s sibling for the UPRIGHT case, and the third copy is
## what forced it here** — `single_primitive`'s own rule, applied as it was to
## the horizontal case: `verify_signs.gd`, `verify_signals.gd` and
## `verify_lamps.gd` held byte-identical copies differing only in two nouns and
## the share.
##
## ⚠️ **A vertical surface cannot be graded by "which way is up", so this asks
## agreement instead.** An arrow lies on the deck, so `check_faces_up` is the
## right question for it; a sign plate, a signal head and a lamp column all face
## *sideways*, and every sideways is a different one.
##
## `signs.gdshader` is `cull_back`, so a mesh wound the other way is correct
## geometry, in the correct place, with the correct material, and the city simply
## has none of it in it. Three stages have shipped exactly that: the tramway at
## 5,111 of 5,112, the signs at 3,200 — the prism ring wound the way a plate
## wants — and the lamps at 25,116 of 35,880, that last one by *inheriting* the
## other two's fix into a function that builds its own frame and does not need it.
##
## ⚠️ **`min_upright_share` is per-layer because the geometry is, and it is a
## LAY-FLAT DETECTOR rather than a quality bar.** Do not tighten it toward
## whatever the current mesh measures: that fails an ordinary authored change to
## the geometry. ⚠️ **It also used not to be stable.** Until `Q82` turned
## `meshes/force_disable_compression` on project-wide, the imported mesh
## disagreed with the built one — `verify_lamps.gd` read 51.52% against an ETL
## 50.000%, because Godot quantised positions over each mesh's own AABB. The two
## agree exactly now, and `check.sh` pins the setting that makes them.
##
## ⚠️ **Negated, because Godot winds front faces clockwise and glTF winds them
## counter-clockwise** — the importer reverses every index triple. Do not "fix"
## this to agree with the ETL-side `facing_away`, which tests the same expression
## with the opposite sign; `Q59` records that both are right about their own side
## of the import.
##
## Checked here as well as in each stage's own manifest because the two catch
## different things: the ETL's `facing_away` counts what the pipeline built, this
## counts what Godot imported, and an import that mirrors an axis moves one
## without the other.
static func check_stands_upright(
	mesh: Mesh, surface: int, where: String, noun: String, shape: String, min_upright_share: float
) -> PackedStringArray:
	var arrays: Array = mesh.surface_get_arrays(surface)
	var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
	var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
	if indices.is_empty():
		return PackedStringArray(["%s carries no index buffer to check winding on" % where])
	if normals.is_empty():
		return PackedStringArray(["%s carries no normals to check winding against" % where])

	var disagreeing: int = 0
	var upright: int = 0
	# `floori` of a float divide rather than an integer one: GDScript warns on
	# integer division and `check.sh` promotes warnings to errors, so the plain
	# form does not compile. The count is exact — an index buffer is always a
	# multiple of three.
	var triangle_count: int = floori(indices.size() / 3.0)
	for triangle: int in triangle_count:
		var ia: int = indices[triangle * 3]
		var a: Vector3 = vertices[ia]
		var b: Vector3 = vertices[indices[triangle * 3 + 1]]
		var c: Vector3 = vertices[indices[triangle * 3 + 2]]
		var cross: Vector3 = (a - b).cross(c - a)
		var length: float = cross.length()
		# A collapsed triangle has no facing to judge. Every stage drops them at
		# twice-area 1e-6, so one here is a rounding survivor rather than a fold.
		if length <= 0.0:
			continue
		if cross.dot(normals[ia]) < 0.0:
			disagreeing += 1
		if absf(cross.y / length) <= MAX_UPRIGHT_Y:
			upright += 1

	var problems: PackedStringArray = []
	if disagreeing > 0:
		problems.append(
			(
				(
					"%s: %d of %d triangles are wound against their own normal. "
					% [where, disagreeing, triangle_count]
				)
				+ (
					"cull_back draws none of those — those %s are invisible, not wrong-looking."
					% noun
				)
			)
		)
	if triangle_count > 0 and float(upright) < min_upright_share * float(triangle_count):
		problems.append(
			(
				"%s: only %d of %d triangles stand upright. " % [where, upright, triangle_count]
				+ "%s — a mostly-horizontal mesh has been laid flat." % shape
			)
		)
	return problems
