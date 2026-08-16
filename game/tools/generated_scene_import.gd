@tool
## Gives every imported scene the material its ETL asked for.
##
## Two jobs, and they are the same job. Godot 4.7's glTF importer reads `COLOR_0`
## into the mesh but leaves `vertex_color_use_as_albedo` off, so an asset imports
## as a uniform white block; and glTF has no way at all to say "shade this with a
## custom shader". Neither can be fixed in the file, so both are corrected here.
##
## Which one an asset gets is decided by its **glTF material name**, written by
## the ETL. A name is the only channel the format offers, and the payload that
## would otherwise identify a tile — `TEXCOORD_0` — cannot stand in: the road
## surface carries it too, for lane coordinates. The same shape as the `-col`
## node-name suffix that already carries collision, and it fails the same way —
## silently, in the engine, where only the verify tools can see it.
##
## Wired up as the project-wide scene import default (`project.godot`
## `[importer_defaults]`) rather than per file, because generated assets are
## gitignored — their `.import` files do not survive a fresh clone, and a
## per-file setting would silently stop applying.
##
## ⚠️ Being an importer *default* means this runs on **every** imported scene,
## including hand-authored assets under `assets/authored/`, not only generated
## tiles — the name says "generated" because that is what needs it, not because
## the scope is limited. Anything that does not name a material it recognises
## keeps the vertex-colour behaviour this file has always applied.
extends EditorScenePostImport

## Material names the ETL writes to request a specific shader, and what to give
## them. Mirrors `FACADE_MATERIAL` in `etl/pipeline/buildings.py` and
## `BODY_MATERIAL` in `tools/make_vehicle.py`.
const SHADERS: Dictionary = {
	"city_facade": "res://tuning/city_facade.tres",
	"vehicle_body": "res://tuning/vehicle_body.tres",
}


func _post_import(scene: Node) -> Object:
	for instance: MeshInstance3D in scene.find_children("*", "MeshInstance3D", true, false):
		if instance.mesh != null:
			_apply(instance.mesh)
	return scene


func _apply(mesh: Mesh) -> void:
	for surface: int in mesh.get_surface_count():
		var material: Material = mesh.surface_get_material(surface)
		if material == null:
			continue

		# The glTF material name, which the importer keeps as the resource name.
		var requested: String = SHADERS.get(material.resource_name, "")
		if not requested.is_empty():
			# One shared resource across every tile rather than a copy each, so
			# the whole city retunes from one file — and so the renderer sees one
			# material where it would otherwise see 131.
			mesh.surface_set_material(surface, load(requested))
			continue

		if not (mesh.surface_get_format(surface) & Mesh.ARRAY_FORMAT_COLOR):
			continue
		var standard := material as BaseMaterial3D
		if standard != null:
			standard.vertex_color_use_as_albedo = true
			# The ETL writes `COLOR_0` in sRGB, and both flags are off by default,
			# so this is the `BaseMaterial3D` half of the `Q27` fix — the shader
			# half is `vertex_srgb_to_linear()`, which the two facade shaders have
			# to carry by hand because there is no such render mode. Without it
			# the road surface takes the same hit the facades did: sRGB bytes read
			# as linear render pale and flatten the difference between colours.
			standard.vertex_color_is_srgb = true
