## The mesh rules every generated asset is held to, in one place.
##
## `P1-2` states them for building tiles and `P1-4` for the road surface, and
## they are the same rules for the same reason: one untextured, vertex-coloured
## primitive is what makes a draw call cheap enough for the mobile tier. Written
## once because two copies drift, and the copy that drifts is the one that
## quietly stops catching anything — the road surface's first version checked
## only `albedo_texture` and never checked `vertex_color_use_as_albedo` at all,
## which is exactly the flag that decides whether the asset renders white.
extends RefCounted


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
