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
	if boxes.is_empty():
		return AABB()

	var union: AABB = boxes[0]
	for index: int in range(1, boxes.size()):
		union = union.merge(boxes[index])
	return union


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


## Problems with one surface of one mesh, or an empty array if it conforms.
##
## `where` names the surface for the caller's report — surface indices restart
## per `MeshInstance3D`, so "surface 0" is ambiguous without it.
static func check_surface(mesh: Mesh, surface: int, where: String) -> PackedStringArray:
	var problems: PackedStringArray = []

	if not (mesh.surface_get_format(surface) & Mesh.ARRAY_FORMAT_COLOR):
		problems.append("%s carries no vertex colours" % where)

	var material: BaseMaterial3D = mesh.surface_get_material(surface) as BaseMaterial3D
	if material == null:
		problems.append("%s has no BaseMaterial3D" % where)
		return problems

	# Set at import by `tools/generated_scene_import.gd`, because glTF has no
	# such flag — COLOR_0 always multiplies base colour there. Without it the
	# asset imports white however good its vertex colours are.
	if not material.vertex_color_use_as_albedo:
		problems.append("%s ignores its vertex colours" % where)
	for slot: int in [
		BaseMaterial3D.TEXTURE_ALBEDO,
		BaseMaterial3D.TEXTURE_NORMAL,
		BaseMaterial3D.TEXTURE_ORM,
	]:
		if material.get_texture(slot) != null:
			problems.append("%s references a texture in slot %d" % [where, slot])
	return problems
