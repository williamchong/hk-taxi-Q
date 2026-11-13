## One `MultiMesh` over many transforms — how a repeated prop draws in one call.
##
## `fence.gd` measured the alternative: the barrier instantiated as a scene per
## placement cost **+36 draw calls** on a driving frame against a `MultiMesh`'s
## +1, pixel-identical (`P3-29`). `P5-2` made it the shape every prop layer
## takes — a sign library, and the lamps and arrows after it (`Q115`) — so the
## idiom lives here once rather than once per placer.
extends RefCounted


## `transforms.size()` copies of `mesh`, as one node. `custom`, when given, is
## one `INSTANCE_CUSTOM` per transform — a parked vehicle's livery (`Q167`).
static func batch(
	mesh: Mesh,
	transforms: Array[Transform3D],
	name: String,
	custom: PackedColorArray = PackedColorArray(),
	colours: PackedColorArray = PackedColorArray()
) -> MultiMeshInstance3D:
	var multi := MultiMesh.new()
	multi.transform_format = MultiMesh.TRANSFORM_3D
	var wears: bool = not custom.is_empty()
	assert(not wears or custom.size() == transforms.size(), "one custom datum a transform")
	multi.use_custom_data = wears
	# The engine multiplies an instance's colour into `COLOR` before the shader
	# reads it, so a tint needs nothing of the material (`P3-77`).
	var tinted: bool = not colours.is_empty()
	assert(not tinted or colours.size() == transforms.size(), "one colour a transform")
	multi.use_colors = tinted
	# A car's body without its instance uniforms (`VehicleBodyBatch`): a batch
	# never had them written, and on the web every node holding them spends a
	# slot of a buffer the parked cells alone overran.
	multi.mesh = VehicleBodyBatch.batched(mesh)
	# Set after `mesh` and `transform_format`: `instance_count` allocates the
	# buffer, so assigning it first and the format second discards every
	# transform written in between.
	multi.instance_count = transforms.size()
	for index: int in transforms.size():
		multi.set_instance_transform(index, transforms[index])
		if wears:
			multi.set_instance_custom_data(index, custom[index])
		if tinted:
			multi.set_instance_color(index, colours[index])
	var node := MultiMeshInstance3D.new()
	node.name = name
	node.multimesh = multi
	return node


## One `MultiMesh` over `transforms`, or with `cells` one per plan cell a
## transform's origin falls in, each hidden past the profile's range.
##
## A region-wide `MultiMesh` is one box, so the engine draws every instance
## from anywhere inside it and again in each shadow cascade: the lamps were
## 129,240 of ~900,000 primitives on the throttle route, exactly 3x their
## placed triangles (`Q135`). A cell is a box the engine can cull.
##
## `tint` is one colour a transform or empty; a cell takes its own share.
static func batches(
	mesh: Mesh,
	transforms: Array[Transform3D],
	mesh_name: String,
	cells: PropCellProfile,
	tint: PackedColorArray = PackedColorArray()
) -> Array[MultiMeshInstance3D]:
	if cells == null:
		return [batch(mesh, transforms, mesh_name, PackedColorArray(), tint)]
	var by_cell: Dictionary[Vector2i, Array] = {}
	var tint_by_cell: Dictionary[Vector2i, PackedColorArray] = {}
	for index: int in transforms.size():
		var at: Transform3D = transforms[index]
		var cell: Vector2i = cells.cell_of(at.origin)
		if not by_cell.has(cell):
			by_cell[cell] = []
			tint_by_cell[cell] = PackedColorArray()
		by_cell[cell].append(at)
		if not tint.is_empty():
			tint_by_cell[cell].append(tint[index])
	var nodes: Array[MultiMeshInstance3D] = []
	for cell: Vector2i in by_cell:
		var part: Array[Transform3D] = []
		part.assign(by_cell[cell])
		var node: MultiMeshInstance3D = batch(
			mesh,
			part,
			"%s_%d_%d" % [mesh_name, cell.x, cell.y],
			PackedColorArray(),
			tint_by_cell[cell]
		)
		node.visibility_range_end = cells.range_m
		node.visibility_range_end_margin = cells.range_margin_m
		nodes.append(node)
	return nodes


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


## The post `mesh` stands on, in its own frame: the bounds of an upright
## cylinder over the ring of vertices at its foot, from the foot to the mesh's
## top. Read off the geometry, so the radius is whatever the ETL drew — a lamp
## column's 90 mm, a sign pole's 32 mm, a signal post's 60 mm — and never a
## second copy of it here.
##
## Empty for a mesh not drawn standing on its origin: a sign's face hangs on its
## pole at the face's centre, so its lowest vertex is below zero and it stands
## nothing. Empty too for a foot of no area.
static func post_of(mesh: Mesh) -> AABB:
	var extent: AABB = mesh.get_aabb()
	if not is_zero_approx(extent.position.y) or extent.size.y <= 0.0:
		return AABB()
	var low := Vector2(INF, INF)
	var high := Vector2(-INF, -INF)
	var foot := PackedVector2Array()
	for surface: int in mesh.get_surface_count():
		var vertices: PackedVector3Array = mesh.surface_get_arrays(surface)[Mesh.ARRAY_VERTEX]
		for vertex: Vector3 in vertices:
			if is_zero_approx(vertex.y):
				var plan := Vector2(vertex.x, vertex.z)
				foot.append(plan)
				low = low.min(plan)
				high = high.max(plan)
	if foot.is_empty():
		return AABB()
	var centre: Vector2 = 0.5 * (low + high)
	var radius: float = 0.0
	for plan: Vector2 in foot:
		radius = maxf(radius, centre.distance_to(plan))
	if radius <= 0.0:
		return AABB()
	return AABB(
		Vector3(centre.x - radius, 0.0, centre.y - radius),
		Vector3(2.0 * radius, extent.size.y, 2.0 * radius)
	)


## An upright cylinder over `post` — `post_of`'s shape, in the prop's frame —
## under each of `transforms`, as one static body per plan cell of `cells`
## holding a shape a placement, or one body for the lot without `cells`.
##
## 🔴 **A body a cell, never a body a post.** Jolt's `max_bodies` is 10,240 and
## the railings alone hold 7,693 of it (`Q159`); the lamps, the sign poles, the
## signal posts and the trees together would pass it. A placement's scale
## widens the cylinder with its across-scale and raises it with its up, and the
## shape stands upright whatever the bearing: every one of these is stood by a
## turn about `+Y`. Posts of one size share one shape by reference, as
## `bodies` shares its box: a region's columns are one size, not a thousand.
static func posts(
	post: AABB, transforms: Array[Transform3D], name: String, cells: PropCellProfile
) -> Array[StaticBody3D]:
	var stood: Array[StaticBody3D] = []
	if not post.has_volume():
		return stood
	var centre: Vector3 = post.get_center()
	var by_cell: Dictionary[Vector2i, StaticBody3D] = {}
	var by_size: Dictionary[Vector2, CylinderShape3D] = {}
	for at: Transform3D in transforms:
		var cell: Vector2i = Vector2i.ZERO if cells == null else cells.cell_of(at.origin)
		if not by_cell.has(cell):
			var body := StaticBody3D.new()
			body.name = "%s_%d_%d" % [name, cell.x, cell.y]
			by_cell[cell] = body
			stood.append(body)
		var grown: Vector3 = at.basis.get_scale()
		var size := Vector2(0.5 * post.size.x * grown.x, post.size.y * grown.y)
		if not by_size.has(size):
			var made := CylinderShape3D.new()
			made.radius = size.x
			made.height = size.y
			by_size[size] = made
		var shape: CylinderShape3D = by_size[size]
		var collision := CollisionShape3D.new()
		collision.shape = shape
		collision.position = at * centre
		by_cell[cell].add_child(collision)
	return stood
