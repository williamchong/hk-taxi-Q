@tool
## Makes imported vertex colours actually shade the mesh.
##
## Godot 4.7's glTF importer reads `COLOR_0` into the mesh but leaves
## `vertex_color_use_as_albedo` off, so a tile imports as a uniform white block.
## Nothing in the glTF can fix this: the format has no such flag, because there
## `COLOR_0` always multiplies base colour. So it is corrected here, at import.
##
## Wired up as the project-wide scene import default (`project.godot`
## `[importer_defaults]`) rather than per file, because generated assets are
## gitignored — their `.import` files do not survive a fresh clone, and a
## per-file setting would silently stop applying.
##
## Safe on scenes that carry no vertex colours: Godot defaults those to white,
## and the flag then multiplies by white.
extends EditorScenePostImport


func _post_import(scene: Node) -> Object:
	_apply(scene)
	return scene


func _apply(node: Node) -> void:
	var instance := node as MeshInstance3D
	if instance != null and instance.mesh != null:
		for surface: int in instance.mesh.get_surface_count():
			if not (instance.mesh.surface_get_format(surface) & Mesh.ARRAY_FORMAT_COLOR):
				continue
			var material := instance.mesh.surface_get_material(surface) as BaseMaterial3D
			if material != null:
				material.vertex_color_use_as_albedo = true

	for child: Node in node.get_children():
		_apply(child)
