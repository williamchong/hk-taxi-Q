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
## ⚠️ Being an importer *default* means this runs on **every** imported scene,
## including hand-authored assets under `assets/authored/`, not only generated
## tiles — the name says "generated" because that is what needs it, not because
## the scope is limited. It only touches surfaces that actually carry
## `ARRAY_FORMAT_COLOR`, so scenes without vertex colours are untouched. An
## authored asset that used `COLOR_0` as a shader mask rather than as albedo
## would need excluding here.
extends EditorScenePostImport


func _post_import(scene: Node) -> Object:
	for instance: MeshInstance3D in scene.find_children("*", "MeshInstance3D", true, false):
		if instance.mesh != null:
			_enable_vertex_colours(instance.mesh)
	return scene


func _enable_vertex_colours(mesh: Mesh) -> void:
	for surface: int in mesh.get_surface_count():
		if not (mesh.surface_get_format(surface) & Mesh.ARRAY_FORMAT_COLOR):
			continue
		var material := mesh.surface_get_material(surface) as BaseMaterial3D
		if material != null:
			material.vertex_color_use_as_albedo = true
