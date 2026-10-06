## One `MultiMesh` over many transforms — how a repeated prop draws in one call.
##
## `fence.gd` measured the alternative: the barrier instantiated as a scene per
## placement cost **+36 draw calls** on a driving frame against a `MultiMesh`'s
## +1, pixel-identical (`P3-29`). `P5-2` made it the shape every prop layer
## takes — a sign library, and the lamps and arrows after it (`Q115`) — so the
## idiom lives here once rather than once per placer.
extends RefCounted


## `transforms.size()` copies of `mesh`, as one node.
static func batch(mesh: Mesh, transforms: Array[Transform3D], name: String) -> MultiMeshInstance3D:
	var multi := MultiMesh.new()
	multi.transform_format = MultiMesh.TRANSFORM_3D
	multi.mesh = mesh
	# Set after `mesh` and `transform_format`: `instance_count` allocates the
	# buffer, so assigning it first and the format second discards every
	# transform written in between.
	multi.instance_count = transforms.size()
	for index: int in transforms.size():
		multi.set_instance_transform(index, transforms[index])
	var node := MultiMeshInstance3D.new()
	node.name = name
	node.multimesh = multi
	return node


## A static body per transform, each standing one box over `extent` — the
## prop's own frame. The `BoxShape3D` is built once and shared by reference.
## Empty for an `extent` with no volume, which the caller refuses.
static func bodies(
	extent: AABB, transforms: Array[Transform3D], name: String
) -> Array[StaticBody3D]:
	var built: Array[StaticBody3D] = []
	if not extent.has_volume():
		return built
	var shape := BoxShape3D.new()
	shape.size = extent.size
	for index: int in transforms.size():
		var body := StaticBody3D.new()
		body.name = "%s_%d" % [name, index]
		body.transform = transforms[index]
		var collision := CollisionShape3D.new()
		collision.shape = shape
		collision.position = extent.get_center()
		body.add_child(collision)
		built.append(body)
	return built
