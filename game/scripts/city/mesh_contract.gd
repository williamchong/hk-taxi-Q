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
		var mesh: Mesh = instance.mesh
		if mesh == null:
			continue
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


## True where the `-col` name suffix imported as a static body.
##
## The suffix is the only thing that carries collision from the ETL into the
## engine, so "did the importer act on it" is a question both the road surface
## and the building tiles have to ask.
static func has_collision(node: Node) -> bool:
	return not node.find_children("*", "StaticBody3D", true, false).is_empty()


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


## Problems with one surface of one mesh, or an empty array if it conforms.
##
## `where` names the surface for the caller's report — surface indices restart
## per `MeshInstance3D`, so "surface 0" is ambiguous without it.
##
## Two shapes conform, because `P3-7` gave tiles a shader and left everything
## else alone. What both must satisfy is the same rule the untextured,
## vertex-coloured primitive has always had — the colour must reach the pixel,
## and no texture may be sampled. How that is achieved differs: a
## `BaseMaterial3D` needs a flag set at import, a `ShaderMaterial` writes
## `ALBEDO` itself. Checked here rather than at the call sites because the road
## surface and the tiles both ask, and a private second copy is what this file
## exists to stop.
static func check_surface(mesh: Mesh, surface: int, where: String) -> PackedStringArray:
	var problems: PackedStringArray = []

	if not (mesh.surface_get_format(surface) & Mesh.ARRAY_FORMAT_COLOR):
		problems.append("%s carries no vertex colours" % where)

	var material: Material = mesh.surface_get_material(surface)
	if material == null:
		problems.append("%s has no material" % where)
		return problems

	var shaded := material as ShaderMaterial
	if shaded != null:
		return _check_shader_surface(shaded, where, problems)

	var standard := material as BaseMaterial3D
	if standard == null:
		problems.append("%s is neither a BaseMaterial3D nor a ShaderMaterial" % where)
		return problems

	# Set at import by `tools/generated_scene_import.gd`, because glTF has no
	# such flag — COLOR_0 always multiplies base colour there. Without it the
	# asset imports white however good its vertex colours are.
	if not standard.vertex_color_use_as_albedo:
		problems.append("%s ignores its vertex colours" % where)
	for slot: int in [
		BaseMaterial3D.TEXTURE_ALBEDO,
		BaseMaterial3D.TEXTURE_NORMAL,
		BaseMaterial3D.TEXTURE_ORM,
	]:
		if standard.get_texture(slot) != null:
			problems.append("%s references a texture in slot %d" % [where, slot])
	return problems


## The same two guarantees, asked of a `ShaderMaterial`.
##
## A shader can do anything, so this checks what is checkable: that a shader is
## attached at all, and that no uniform holds a texture. The second is the real
## one — the tile contract is "no textures", and a sampler bound here would ship
## an image into a bundle specified to carry none while every other check passed.
static func _check_shader_surface(
	material: ShaderMaterial, where: String, problems: PackedStringArray
) -> PackedStringArray:
	if material.shader == null:
		problems.append("%s is a ShaderMaterial with no shader" % where)
		return problems

	for uniform: Dictionary in material.shader.get_shader_uniform_list():
		var name: String = uniform.get("name", "")
		if material.get_shader_parameter(name) is Texture:
			problems.append("%s binds a texture to shader uniform '%s'" % [where, name])
	return problems
