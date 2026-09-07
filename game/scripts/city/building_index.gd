## Which source object a point of a generated tile belongs to (`P5-11`).
##
## A tile is one merged primitive, and until `P5-11` nothing in it said which
## building a triangle came from. Each tier now brings a table with it — the
## glTF mesh `extras`, which Godot imports as `Mesh.get_meta("extras")` — one
## row per source object with its id, class and source AABB, and every vertex
## carries its row in `TEXCOORD_1.y`. This is the reader for both.
##
## `object_at` answers by the table alone: the smallest row box containing the
## point. A ground sheet's box is 750 m across, so a building always wins
## inside its own footprint, and a point over open ground falls through to the
## sheet. It needs no face index, so it survives `P5-12` moving the collider
## off the render mesh — the raycast's `position` is enough.
extends RefCounted

const EXTRAS_META: StringName = &"extras"
const OBJECTS_KEY: String = "objects"

## How far a shipped vertex may stand outside its object's *source* box. The
## box is the source mesh's; the tier is decimated, and `collapse` moves a
## vertex to its cluster's mean — up to a cell, and the coarsest building cell
## in city config is 4 m, the ground's 8 m. Candidates are gathered on the
## grown box so a point on a decimated wall still finds its own row;
## `verify_tiles.gd` holds every vertex to the same slack.
const ROW_SLACK_M: float = 8.0


## The tier's object table, or an empty array where the mesh brought none.
static func objects_of(mesh: Mesh) -> Array:
	if mesh == null or not mesh.has_meta(EXTRAS_META):
		return []
	var extras: Variant = mesh.get_meta(EXTRAS_META)
	if not (extras is Dictionary):
		return []
	var objects: Variant = (extras as Dictionary).get(OBJECTS_KEY)
	return objects if objects is Array else []


## The row a vertex names, decoded from its `TEXCOORD_1.y`. One spelling of
## the rounding, shared with `verify_tiles.gd`, so the two cannot disagree.
static func row_of(uv2: Vector2) -> int:
	return int(round(uv2.y))


## A row's source box, or `null` where the row is malformed — null rather than
## an empty box at the origin, which is a real place a point could be.
static func box_of(row: Dictionary) -> Variant:
	var corners: Variant = row.get("aabb")
	if not (corners is Array) or (corners as Array).size() != 2:
		return null
	return CityManifest.box(
		CityManifest.point((corners as Array)[0]), CityManifest.point((corners as Array)[1])
	)


## The object standing at `point` across every tile under `root` — `root`
## itself included where it is a mesh — or an empty dictionary where none does.
##
## Two steps, because a source box is a box and a footprint is not: the rows
## whose box contains the point are the candidates, and where more than one
## does — an L-shaped block's box reaches into its neighbour's — the row of
## the **nearest vertex** among them decides. A raycast hit lies on a surface,
## so for the picker's own use that distance is zero and the answer exact; a
## point in the air resolves to whatever surface is closest, within the box of
## a tile that has one. A ground sheet's box is 750 m across, so over open
## ground the sheet is the one candidate.
##
## ⚠️ A tile is culled on its **own** box before its rows are read, and that
## is what keeps a pick cheap: a sheet's row box covers ~25 tiles, so without
## it every pick copied a quarter of a million vertices out of resident meshes
## that could not own the point. The tile box is built from the tier's own
## vertices, so no vertex that could win lies outside it.
##
## `point` is in `root`'s frame, which is the world's when `root` is the
## streamer; the tool that grades this hands it a bare tile, which is why the
## frame is walked up to `root` rather than read off `global_transform`.
static func object_at(root: Node, point: Vector3) -> Dictionary:
	var best: Dictionary = {}
	var best_distance: float = INF
	var instances: Array[Node] = root.find_children("*", "MeshInstance3D", true, false)
	if root is MeshInstance3D:
		instances.push_front(root)
	for instance: MeshInstance3D in instances:
		var rows: Array = objects_of(instance.mesh)
		if rows.is_empty():
			continue
		var here: Vector3 = _transform_to(root, instance).affine_inverse() * point
		if not instance.get_aabb().grow(ROW_SLACK_M).has_point(here):
			continue
		# Per row: `-1.0` not a candidate, `INF` a candidate with no vertex
		# found yet, else the squared distance to its nearest vertex.
		var distances: PackedFloat32Array = PackedFloat32Array()
		distances.resize(rows.size())
		distances.fill(-1.0)
		var any_candidate: bool = false
		for index: int in rows.size():
			var box: Variant = box_of(rows[index])
			if box != null and (box as AABB).grow(ROW_SLACK_M).has_point(here):
				distances[index] = INF
				any_candidate = true
		if not any_candidate:
			continue
		_nearest_by_row(instance.mesh, here, distances)
		for index: int in rows.size():
			if distances[index] >= 0.0 and distances[index] < best_distance:
				best_distance = distances[index]
				best = rows[index]
	return best


## Lowers `distances[row]` to the squared distance of the row's nearest vertex
## to `here`, for every row not marked `-1.0` (not a candidate). A candidate row
## with no vertex left in this tier keeps `INF`.
static func _nearest_by_row(mesh: Mesh, here: Vector3, distances: PackedFloat32Array) -> void:
	if mesh == null or mesh.get_surface_count() == 0:
		return
	var arrays: Array = mesh.surface_get_arrays(0)
	var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	# `null`, not an empty array, where the surface carries no UV2.
	var channel: Variant = arrays[Mesh.ARRAY_TEX_UV2]
	if not (channel is PackedVector2Array):
		return
	var uv2: PackedVector2Array = channel
	for i: int in vertices.size():
		var index: int = row_of(uv2[i])
		if index < 0 or index >= distances.size() or distances[index] < 0.0:
			continue
		var distance: float = here.distance_squared_to(vertices[i])
		if distance < distances[index]:
			distances[index] = distance


## `node`'s transform in `root`'s frame, from the local transforms between them.
static func _transform_to(root: Node, node: Node3D) -> Transform3D:
	var transform: Transform3D = Transform3D.IDENTITY
	var here: Node = node
	while here != null and here != root:
		if here is Node3D:
			transform = (here as Node3D).transform * transform
		here = here.get_parent()
	return transform
