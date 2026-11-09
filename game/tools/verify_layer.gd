## The one `_init` every per-layer verify tool runs (`P3-49`'s refactor pass):
## skip when the layer is not shipped for this region, fail when it is shipped
## but will not load, instantiate it outside the tree, hand the root to the
## tool's own `_check`, free it, print the verdict and quit.
##
## Nine tools carried this body by hand and two of them had already lost its
## comments, which is the drift this file exists to stop. The tool keeps every
## rule about its layer; this keeps only the plumbing.
##
## Extends `RefCounted` with no `class_name`, like `router_diff.gd`: a
## `--script` tool preloads it by path, and a global here would be one more
## name a tool cannot resolve when run headless.
extends RefCounted

const GeneratedLayer = preload("res://scripts/city/generated_layer.gd")
const GeneratedPlacements = preload("res://scripts/city/generated_placements.gd")
const LayerPreview = preload("res://scripts/city/layer_preview.gd")
const PropBatch = preload("res://scripts/city/prop_batch.gd")

## The name every posts body carries: `PropBatch.posts` is handed `<mesh>_posts`
## and adds `_<x>_<y>`.
const POSTS: String = "*_posts_*"


## Run `check` over the instantiated `layer` and quit `tree` with the verdict.
## `check` takes the scene root and returns the problems, one string each.
static func run(tree: SceneTree, layer: String, check: Callable) -> void:
	if not GeneratedLayer.is_present(layer):
		print("  skip  no %s shipped for this region" % GeneratedLayer.noun(layer))
		tree.quit(0)
		return

	var packed: PackedScene = GeneratedLayer.load_layer(layer)
	if packed == null:
		# Present but unloadable, which is not the same as absent — the hint
		# about rebuilding would be the wrong advice here.
		printerr("  FAIL  %s exists but did not load as a scene" % GeneratedLayer.path(layer))
		tree.quit(1)
		return

	var scene_root: Node3D = packed.instantiate()
	var problems: PackedStringArray = check.call(scene_root)
	# Instantiated outside the tree, so nothing else will free it — and a
	# headless run that leaks buries its own result under exit warnings.
	scene_root.free()
	for problem: String in problems:
		printerr("  FAIL  ", problem)
	if problems.is_empty():
		print("  ok    ", GeneratedLayer.path(layer))
	tree.quit(1 if not problems.is_empty() else 0)


## The bodies under `node` whose name matches `pattern`, counted, with every
## cylinder they hold appended to `shapes` — the posts', the trunks'.
static func cylinders_under(node: Node, pattern: String, shapes: Array[CollisionShape3D]) -> int:
	var bodies: Array[Node] = node.find_children(pattern, "StaticBody3D", true, false)
	for body: Node in bodies:
		for child: Node in body.get_children():
			var collision := child as CollisionShape3D
			if collision != null and collision.shape is CylinderShape3D:
				shapes.append(collision)
	return bodies.size()


## The layer node with `posts` on stands one upright cylinder under every
## placement whose library mesh stands on a post (`PropBatch.post_of`), in a body
## per kind and plan cell — the count that keeps the posts under Jolt's body cap
## — and none under a mesh that hangs. `library` is the tool's own read of the
## layer's meshes. Empty when it holds.
static func check_posts(layer: String, library: Dictionary[String, Mesh]) -> PackedStringArray:
	var problems: PackedStringArray = []
	var posts: Dictionary[String, AABB] = {}
	for mesh_name: String in library:
		var post: AABB = PropBatch.post_of(library[mesh_name])
		if post.has_volume():
			posts[mesh_name] = post
	if posts.is_empty():
		return ["%s: no library mesh stands on a post, so nothing collides" % layer]
	var cells := load(PropCellProfile.PATH) as PropCellProfile
	if cells != null and (layer not in cells.layers or cells.cell_m <= 0.0):
		cells = null
	var document: Dictionary = GeneratedPlacements.load_placements(
		GeneratedLayer.placements_path(layer), GeneratedLayer.noun(layer)
	)
	var expected_shapes: int = 0
	var expected_bodies: Dictionary = {}
	var first: Transform3D
	var first_post := AABB()
	for entry: Dictionary in document.get("placements", []) as Array:
		var mesh_name: String = String(entry.get("mesh", ""))
		if not posts.has(mesh_name):
			continue
		var at: Transform3D = GeneratedPlacements.placement_of(entry) as Transform3D
		if expected_shapes == 0:
			first = at
			first_post = posts[mesh_name]
		expected_shapes += 1
		var cell: Vector2i = Vector2i.ZERO if cells == null else cells.cell_of(at.origin)
		expected_bodies[[mesh_name, cell]] = true

	# Built out of the tree and `_ready` called by hand, as `verify_trees.gd`
	# does: a node added to a root that has not started is never readied.
	var node: Node3D = LayerPreview.new()
	node.layer = layer
	node.posts = true
	node._ready()
	var shapes: Array[CollisionShape3D] = []
	var bodies: int = cylinders_under(node, POSTS, shapes)
	if shapes.size() != expected_shapes:
		problems.append(
			(
				"%s: %d post shapes stand under %d placements on a post"
				% [layer, shapes.size(), expected_shapes]
			)
		)
	if bodies != expected_bodies.size():
		problems.append(
			(
				"%s: %d post bodies for %d kind-and-cell pairs"
				% [layer, bodies, expected_bodies.size()]
			)
		)
	if problems.is_empty() and not shapes.is_empty():
		# The first placement's post, sized and stood off its own transform: a
		# cylinder at the origin, or one never scaled, still counts right.
		var shape := shapes[0].shape as CylinderShape3D
		var grown: Vector3 = first.basis.get_scale()
		var radius_m: float = 0.5 * first_post.size.x * grown.x
		var centre: Vector3 = first * first_post.get_center()
		if (
			not is_equal_approx(shape.radius, radius_m)
			or not is_equal_approx(shape.height, first_post.size.y * grown.y)
			or shapes[0].position.distance_to(centre) > 1e-3
		):
			problems.append(
				(
					"%s: the first post is r %.3f x %.2f m at %s, its placement wants r %.3f at %s"
					% [layer, shape.radius, shape.height, shapes[0].position, radius_m, centre]
				)
			)
	node.free()
	if problems.is_empty():
		print("  ok    %d %s posts in %d bodies" % [shapes.size(), layer, bodies])
	return problems
