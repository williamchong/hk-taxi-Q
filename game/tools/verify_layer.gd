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
