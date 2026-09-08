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
## them. Mirrors `FACADE_MATERIAL` in `etl/pipeline/buildings.py`,
## `SURFACE_MATERIAL` in `etl/pipeline/surface.py` and `BODY_MATERIAL` in
## `tools/make_vehicle.py`.
const SHADERS: Dictionary = {
	"city_facade": "res://tuning/city_facade.tres",
	"road_markings": "res://tuning/road_markings.tres",
	"tramway": "res://tuning/tramway.tres",
	"arrows": "res://tuning/arrows.tres",
	"boxjunctions": "res://tuning/boxjunctions.tres",
	# The published stop and give-way lines (`P3-23`). One entry for all three
	# codes, because all three are the same white paint — what tells a give-way
	# line from a stop line is the geometry `pipeline/roadmarks.py` built, not a
	# material of its own.
	"roadmarks": "res://tuning/roadmarks.tres",
	# The three railing-layer classes (`Q61`). One source layer, one `.glb`, three
	# meshes — and the names are the class `id`s in `hong_kong.yaml` verbatim, so
	# adding a fourth class means adding a row here and nothing else. They share
	# `railings.gdshader`: what tells a bollard from a fence is the mask
	# parameters in each `.tres`, not a shader of its own.
	"railings": "res://tuning/railings.tres",
	"bollards": "res://tuning/bollards.tres",
	"barriers": "res://tuning/barriers.tres",
	# ⚠️ **`signs.tres` is the only entry here whose absence is *quiet*.** Every
	# other row falls back to a visibly wrong colour, because those meshes carry
	# no `COLOR_0` and the shader is where their colour lives. A sign's livery is
	# on the vertex, so a missing dispatch still draws the right plates in the
	# right colours — just without `vertex_srgb_to_linear`, so the whole city's
	# signage comes out pale (`Q27`). `verify_signs.gd` checks this row for that
	# reason.
	"signs": "res://tuning/signs.tres",
	# The published signal heads (`P3-17`). ⚠️ **Its absence is quiet for
	# `signs.tres`'s exact reason** — the livery is on `COLOR_0`, so a head that
	# kept its imported material still draws correctly and merely loses
	# `vertex_srgb_to_linear` (`Q27`). ⚠️ It shares `signs.gdshader` and differs
	# only in the uniforms its `.tres` sets, so this row is what tells the two
	# apart: a head handed `signs.tres` renders as a signal lit like sheeting.
	"signals": "res://tuning/signals.tres",
	# `lamps.tres`: `signs.tres` and `signals.tres`'s third sibling, sharing
	# `signs.gdshader` for `Q61`'s and `Q71`'s reason — a layer is a
	# parameterisation, not a shader. ⚠️ **Its fallback failure is the same quiet
	# one**: the livery is on `COLOR_0`, so a column that kept its imported
	# `BaseMaterial3D` draws the right prism in the right place and simply loses
	# `vertex_srgb_to_linear`, coming out pale (`Q27`). 🔴 And a column handed
	# `signs.tres` renders as a lamp post lit like retroreflective sheeting,
	# which is why `verify_lamps.gd` checks the `resource_path` and not the
	# shader.
	"lamps": "res://tuning/lamps.tres",
	"vehicle_body": "res://tuning/vehicle_body.tres",
	# The two authored props (`P5-28b`). 🔴 **They are here because a
	# `BaseMaterial3D` cannot read a global shader parameter**, not because they
	# wanted a shader: both used to fall through to the last branch of `_apply`
	# below, which is the `Q27` fix in its `BaseMaterial3D` form and is entirely
	# correct for what it does. What it cannot do is scale an albedo by
	# `exposure_anchor`, so once the ETL stops baking the anchor into `COLOR_0`
	# (`P5-28c`) a prop left on that branch renders pale by a constant factor —
	# which reads as a lighting choice rather than as a bug. They share
	# `vertex_albedo.gdshader`, the smallest shader here, and differ in nothing
	# today; ⚠️ **two rows and two `.tres` anyway**, because one shared material
	# would leave `verify_landmarks.gd` and `verify_fence.gd` nothing to tell
	# apart. ⚠️ **`barrier_vertex`, never `barriers`** — that name is taken by the
	# railing class of the same word, and a prop handed `barriers.tres` draws a
	# picket fence where a road barrier should stand.
	"landmark_vertex": "res://tuning/landmarks.tres",
	"barrier_vertex": "res://tuning/barrier_vertex.tres",
}

## The one material in the bundle that arrives carrying an image (`P3-20`).
##
## 🔴 **A separate table because this row cannot behave like the others.** Every
## entry in `SHADERS` swaps in one shared resource, which is what turns 131
## materials into one — but a shared resource cannot hold a *per-region* texture,
## and the sign lettering's atlas is generated city data: gitignored, rebuilt per
## region, and never committed (hard rule 7). So this row duplicates its material
## and hands the copy the texture the glTF importer already decoded, which keeps
## the atlas out of the repository and out of `signs_text.tres` both.
##
## ⚠️ **The texture is taken from the imported `BaseMaterial3D`, not loaded by
## path** — still, and now for a different reason. It used to be that there was
## no path: the image rode inside `signs.glb` as an embedded buffer view. Since
## `Q70` it ships beside the asset as `signs_text.png`, named by `city.json`,
## because an *embedded* image is one Godot's importer extracts into a file the
## manifest had never heard of — and `sync_generated.sh` deletes what the
## manifest does not name. So a path exists; taking it would still be wrong.
## Hard-coding one here would put a second name for the same file in a second
## place, and the ETL is free to rename its output. Reading what the importer
## resolved keeps this row honest about whatever `signs.glb` actually points at.
##
## ⚠️ **If this row goes missing the lettering does not vanish — it turns
## WHITE**, because the fallback `BaseMaterial3D` still samples the atlas but
## loses `vertex_srgb_to_linear`, and if the uniform goes unset the shader samples
## white and the words disappear into the plate. Neither is visible as an error.
## `verify_signs.gd` checks the dispatch and `signs.json` publishes the cell's ink
## coverage, because between them that is the only way to see it.
const TEXTURED: Dictionary = {
	"signs_text": {"material": "res://tuning/signs_text.tres", "uniform": "glyph_atlas"},
}

## The vehicle door (`P5-23`, `Q124`). A body arrives with one material slot
## per part, named from this table — `vehicle_paint`, `vehicle_glass`, a
## `vehicle_lamp_*` per switched circuit — and leaves as the one `vehicle_body`
## surface `vehicle_body.gdshader` reads, with `UV = (circuit, marker)` stamped
## on every vertex from the name. That payload used to be stamped by
## `tools/make_vehicle.py` alone, which no DCC export could reproduce; the
## generator now emits these names too, so the shipped taxi and a hand-made
## car go through one rule. ⚠️ Mirrors `MATERIAL_OF_PAYLOAD` there, and
## `etl/tests/test_make_vehicle.py` binds the two tables by name.
##
## The value is `(circuit, marker)` in `UV.x`/`UV.y` order: markers 0 paint,
## 1 glass, 2 lamp, 3 trim; circuits 1 brake, 2 reverse, 3/4 indicators, 5
## sidelamp, 6 headlamp, 7 roof sign, 0 none — `vehicle_body.gdshader`'s own
## constants. ⚠️ A name that starts `vehicle_` and is not here is REFUSED, not
## guessed: the body is left as authored, unlit and unmerged, and
## `push_error` names the slot — a misspelt lens fails loudly here rather
## than shipping dark.
const VEHICLE: Dictionary = {
	"vehicle_paint": Vector2(0.0, 0.0),
	"vehicle_glass": Vector2(0.0, 1.0),
	"vehicle_trim": Vector2(0.0, 3.0),
	"vehicle_lamp": Vector2(0.0, 2.0),
	"vehicle_lamp_brake": Vector2(1.0, 2.0),
	"vehicle_lamp_reverse": Vector2(2.0, 2.0),
	"vehicle_lamp_indicator_left": Vector2(3.0, 2.0),
	"vehicle_lamp_indicator_right": Vector2(4.0, 2.0),
	"vehicle_lamp_sidelamp": Vector2(5.0, 2.0),
	"vehicle_lamp_headlamp": Vector2(6.0, 2.0),
	"vehicle_lamp_roofsign": Vector2(7.0, 2.0),
}
const VEHICLE_PREFIX: String = "vehicle_"
## The name of the merged surface and of the `.tres` it renders with — also
## what a body that arrives already stamped (the pre-`P5-23` form) is named,
## which `SHADERS` still dispatches as before.
const VEHICLE_BODY: String = "vehicle_body"


func _post_import(scene: Node) -> Object:
	for instance: MeshInstance3D in scene.find_children("*", "MeshInstance3D", true, false):
		if instance.mesh == null:
			continue
		var body: ArrayMesh = vehicle_body(instance.mesh)
		if body != null:
			instance.mesh = body
			continue
		_apply(instance.mesh)
	return scene


## The vehicle door. Null where the mesh is not a body — no slot carries a
## `vehicle_` name — or where one slot carries a name the table lacks, which is
## refused with the slot named. Otherwise one surface: every slot's vertices
## concatenated, `UV` stamped from the name, and `COLOR_0` carried as authored
## or, where a slot has none, filled from its material's base colour in the
## sRGB encoding the ETL writes and the shader linearises (`Q27`).
static func vehicle_body(mesh: Mesh) -> ArrayMesh:
	var materials: Array[Material] = []
	for surface: int in mesh.get_surface_count():
		materials.append(mesh.surface_get_material(surface))
	if not materials.any(_claims_the_door):
		return null
	var names: PackedStringArray = []
	for material: Material in materials:
		var name: String = "" if material == null else material.resource_name
		names.append(name)
		if not VEHICLE.has(name):
			push_error(
				(
					"generated_scene_import: '%s' is not a vehicle material, so the body is left as authored and will not light; the names are %s"
					% [name, VEHICLE.keys()]
				)
			)
			return null

	var positions := PackedVector3Array()
	var normals := PackedVector3Array()
	var colours := PackedColorArray()
	var uvs := PackedVector2Array()
	var indices := PackedInt32Array()
	for surface: int in mesh.get_surface_count():
		var arrays: Array = mesh.surface_get_arrays(surface)
		var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var surface_normals: Variant = arrays[Mesh.ARRAY_NORMAL]
		if typeof(surface_normals) != TYPE_PACKED_VECTOR3_ARRAY:
			push_error("generated_scene_import: '%s' carries no normals" % names[surface])
			return null
		var base: int = positions.size()
		positions.append_array(vertices)
		normals.append_array(surface_normals)
		var stamp := PackedVector2Array()
		stamp.resize(vertices.size())
		stamp.fill(VEHICLE[names[surface]])
		uvs.append_array(stamp)
		var colour: Variant = arrays[Mesh.ARRAY_COLOR]
		if typeof(colour) == TYPE_PACKED_COLOR_ARRAY:
			colours.append_array(colour)
		else:
			var authored := materials[surface] as BaseMaterial3D
			if authored == null:
				push_error(
					(
						"generated_scene_import: '%s' has no vertex colour and no base colour"
						% names[surface]
					)
				)
				return null
			var baked := PackedColorArray()
			baked.resize(vertices.size())
			baked.fill(authored.albedo_color.linear_to_srgb())
			colours.append_array(baked)
		var index: Variant = arrays[Mesh.ARRAY_INDEX]
		if typeof(index) == TYPE_PACKED_INT32_ARRAY:
			for value: int in index:
				indices.append(value + base)
		else:
			for vertex: int in vertices.size():
				indices.append(base + vertex)

	var merged: Array = []
	merged.resize(Mesh.ARRAY_MAX)
	merged[Mesh.ARRAY_VERTEX] = positions
	merged[Mesh.ARRAY_NORMAL] = normals
	merged[Mesh.ARRAY_COLOR] = colours
	merged[Mesh.ARRAY_TEX_UV] = uvs
	merged[Mesh.ARRAY_INDEX] = indices
	var body := ArrayMesh.new()
	body.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, merged)
	body.surface_set_name(0, VEHICLE_BODY)
	body.surface_set_material(0, load(SHADERS[VEHICLE_BODY]))
	return body


## A slot named from the vocabulary, or misnamed into it — a body that arrives
## already stamped is `vehicle_body` and is not this door's.
static func _claims_the_door(material: Material) -> bool:
	if material == null:
		return false
	var name: String = material.resource_name
	return name.begins_with(VEHICLE_PREFIX) and name != VEHICLE_BODY


func _apply(mesh: Mesh) -> void:
	for surface: int in mesh.get_surface_count():
		var material: Material = mesh.surface_get_material(surface)
		if material == null:
			continue

		# The glTF material name, which the importer keeps as the resource name.
		var textured: Dictionary = TEXTURED.get(material.resource_name, {})
		if not textured.is_empty():
			mesh.surface_set_material(surface, _with_texture(material, textured))
			continue

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
			# half is `vertex_srgb_to_linear()`, which every shader above has to
			# carry by hand because Godot 4 has no such render mode. Without
			# either, sRGB bytes read as linear render pale and flatten the
			# difference between colours.
			#
			# ⚠️ **This branch and the one above are exclusive, which is a trap on
			# the way in rather than on the way out.** Until `P3-12` the road
			# surface was this branch's headline case; it now names a material and
			# takes the `continue` above, so `road_markings.gdshader` is what has
			# to convert its asphalt. Anything moved from here to a shader owes
			# the same, and nothing fails loudly when it is forgotten — the
			# surface just lightens.
			standard.vertex_color_is_srgb = true


## The declared material, duplicated and given the imported image.
##
## ⚠️ **`duplicate()` and not `load()` alone.** Setting the uniform on the shared
## resource would write a region's texture into a project-wide material, so the
## last region imported would win and every other one would render someone else's
## lettering — silently, since a sign with the wrong words on it is a sign.
func _with_texture(imported: Material, row: Dictionary) -> Material:
	var target := load(String(row["material"])) as ShaderMaterial
	if target == null:
		push_warning("generated_scene_import: %s is not a ShaderMaterial" % row["material"])
		return imported
	var source := imported as BaseMaterial3D
	if source == null or source.albedo_texture == null:
		# The ETL declared a textured material and shipped no texture. Left as
		# imported so the failure reaches `check_surface`, which fails a declared
		# texture that never arrived — the half of `Q63` written for exactly this.
		push_warning("generated_scene_import: %s carries no image" % imported.resource_name)
		return imported
	var copy := target.duplicate() as ShaderMaterial
	copy.set_shader_parameter(String(row["uniform"]), source.albedo_texture)
	return copy
