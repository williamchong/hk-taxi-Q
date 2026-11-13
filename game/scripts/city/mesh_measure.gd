## How to measure a generated asset: its triangles, its bounds, its colliders.
##
## The half of the mesh rules the GAME reads — the near miss sizes the car off
## `bounds`, the layers print `triangles` and `colliders` — split from
## `tools/mesh_contract.gd`, which holds the checks only the verify tools run
## and which a shipped build has no use for. Every preview and every verify
## tool wants one or both of `triangles` and `bounds`, and each carries a trap
## that is easy to get subtly wrong in a private copy.
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


## How many static bodies the node's subtree carries. The previews print it
## because every generated layer but the road surface and the railings must
## carry none (`Q74`, `Q159`), and `fence.gd` because its bodies are built by
## hand.
static func colliders(node: Node) -> int:
	return node.find_children("*", "StaticBody3D", true, false).size()
