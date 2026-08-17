extends SceneTree

## Does the taxi's shading actually reach the shader? (`P3-11c`, `P3-11d`, `P3-11e`)
##
##     godot --headless --path game --script res://tools/verify_vehicle.gd
##
## Everything between the `.glb` on disk and the fragment shader is engine-side,
## and **every failure along it renders nearly right**, which is the one symptom
## nothing else here can see. Two paths in particular:
##
## - **The material name.** `tools/make_vehicle.py` writes the glTF material name
##   `vehicle_body` and `tools/generated_scene_import.gd` maps it to
##   `vehicle_body.tres`. Drop the name, the dictionary entry, the `.tres` or the
##   `[importer_defaults]` wiring and the body falls back to the `BaseMaterial3D`
##   it imported with — a red car with no clearcoat, no sky gradient, and no lamp
##   branch at all.
## - **The switched channels.** `vehicle_lamps.gd` writes `lamp_lit` and
##   `lamp_front` with `set_instance_shader_parameter`. An unmatched name is **not
##   an error**: it is a no-op, the shader keeps its `vec4(0.0)` default, and that
##   default is every lamp out.
##
## ⚠️ **The Python side already holds the generator, and this is not a second copy
## of it.** `TestSurfaceMarkers` and `TestLampCircuits` grade `MeshData` before
## the glTF is written, and `TestShippedAssets` proves the committed `.glb` is
## that generator's output. What no `pytest` can see is the **import** and the
## **scene**, so the payload is read back off the mesh Godot handed the renderer —
## after `ensure_tangents`, surface dedup and LOD generation — rather than off the
## file the ETL wrote.
##
## ⚠️ **It cannot see a frame, and must not be read as if it could.** Headless has
## no rasteriser, and Godot exits `0` on a shader that fails to compile. Whether
## the car *looks* right is still a render and a `grep -i "shader error"` over the
## driver log; this holds the wiring that render depends on.
##
## ⚠️ **Nothing here references a `class_name` global**, for the reason
## `verify_beam_budget.gd` gives: a `--script` tool that does fails to *parse* on a
## fresh clone, where `global_script_class_cache.cfg` has not been written — so
## `_init` never runs, `quit(1)` is never reached, and the SceneTree exits **0**
## having checked nothing. Nodes are identified by the path of the script they
## run, and constants are read out of scripts `load`ed by path.
##
## ⚠️ **The first `await` is load-bearing, and skipping it fails in the direction
## that looks like a pass.** Autoloads are registered on the first frame, not
## before, so loading `taxi.tscn` from `_init` compiles `vehicle_controller.gd`
## while `InputRouter` is unresolvable. GDScript then caches the broken class, the
## scene instances a `RigidBody3D` with a **null script**, and the run prints
## `SCRIPT ERROR` — which `check.sh` fails on, having graded a car that never
## loaded. `skidpad_ablation.gd` documents the same trap from the other side.
##
## Needs no built region: the taxi is a committed authored asset, so this runs
## outside `check.sh`'s `VERIFY_GENERATED` gate with `verify_beam_budget.gd`.

## The player's car, and the only one. A roster car earns its own entry here
## when it exists; a car carrying no lamp rig is supported rather than broken,
## which `vehicle_lamps.gd` records, so such an entry would check less than this.
const SCENE_PATH := "res://scenes/vehicle/taxi.tscn"
const MATERIAL_PATH := "res://tuning/vehicle_body.tres"
const SHADER_PATH := "res://assets/shaders/vehicle_body.gdshader"
const LAMPS_SCRIPT := "res://scripts/vehicle/vehicle_lamps.gd"
const GLINT_SCRIPT := "res://scripts/vehicle/sun_glint.gd"
const CONTROLLER_SCRIPT := "res://scripts/vehicle/vehicle_controller.gd"

## Where `GeometryInstance3D` publishes the instance uniforms its material
## declares. This is the renderer's own list — the same one
## `set_instance_shader_parameter` dispatches against — which is why it is asked
## rather than the shader source: a name that is in the source but not in this
## list would still be a silent no-op, and this list is what decides.
const INSTANCE_PREFIX := "instance_shader_parameters/"

## The prefix `vehicle_lamps.gd` names its channel constants with. Read from the
## script rather than written down here, so a third vector is picked up by adding
## a `PARAMETER_*` constant beside the two that exist.
const CHANNEL_CONSTANT_PREFIX := "PARAMETER"

## `MARKER_*` in `tools/make_vehicle.py` and `vehicle_body.gdshader`. Only the two
## ends are needed: the lens marker, because it is the only one the circuit branch
## reads, and the last legal value, because a marker past it takes the paint
## branch in silence.
const MARKER_LAMP := 2.0
const MARKER_LAST := 3.0
const CIRCUIT_NONE := 0.0

var _failed: int = 0


func _init() -> void:
	# Deferred, then a frame, before anything is loaded. See the header.
	_run.call_deferred()


func _run() -> void:
	await process_frame

	var packed := load(SCENE_PATH) as PackedScene
	if packed == null:
		_fail("%s did not load as a scene" % SCENE_PATH)
		_finish()
		return
	# Instantiated into a `Node` and cast afterwards, so the failure path still has
	# something to free. Casting on the way in discards the reference where the
	# cast fails, and the run then ends in the page of leak errors the `free()`
	# below exists to keep out of a report that is already failing.
	var instanced: Node = packed.instantiate()
	var car := instanced as Node3D
	if car == null:
		_fail("%s did not instantiate as a Node3D" % SCENE_PATH)
		instanced.free()
		_finish()
		return

	# Found the way the script finds them, so this grades the wiring rather than
	# the file layout: a lamp rig moved to another node is caught here, not by a
	# path that was written down twice.
	var lamps := _running(car, LAMPS_SCRIPT) as Node3D
	if lamps == null:
		_fail("no node in %s runs %s" % [SCENE_PATH, LAMPS_SCRIPT])
		car.free()
		_finish()
		return
	# ⚠️ **The mesh is checked here, not where it is read.** `_body_under` promises
	# a `MeshInstance3D`, never that it carries a mesh — and dereferencing a null
	# one is a run-time error inside a coroutine, which kills the run before
	# `quit()` and exits **0** having reported nothing. That is the failure this
	# whole file is built against, so it is refused at the door.
	var body: MeshInstance3D = _body_under(lamps)
	if body == null or body.mesh == null:
		_fail("the lamp rig has no MeshInstance3D with a mesh below it to switch")
		car.free()
		_finish()
		return

	var material: ShaderMaterial = _check_the_body_wears_its_shader(body)
	# Walked once and handed to both checks that read it. See
	# `_declared_instance_uniforms` for why the renderer's list is the authority.
	var declared: Dictionary = _declared_instance_uniforms(body)
	var channels: int = _check_the_switched_channels_reach_the_shader(declared)
	_check_the_payload_survived_the_import(body, channels)
	_check_the_sun_belongs_to_the_material(declared, material)
	_check_the_rig_hangs_where_the_script_looks(car, lamps, material)
	_check_the_beams_point_at_the_road(car)

	# Freed rather than left to the exit: an instantiated scene that never
	# reaches a tree is leaked at exit, and Godot reports that as a page of
	# `ERROR: ... leaked` lines that read like a failure and are not one.
	car.free()
	_finish()


## Every surface of the body must render with `vehicle_body.tres`.
##
## The whole material-name path in one assertion: it fails whether the ETL
## dropped the name, `generated_scene_import.gd` dropped the entry, the `.tres`
## moved, or the importer default came unwired — and the fallback it catches is a
## `BaseMaterial3D` that renders very nearly as the shader does.
func _check_the_body_wears_its_shader(body: MeshInstance3D) -> ShaderMaterial:
	var before: int = _failed
	var found: ShaderMaterial = null
	var surfaces: int = body.mesh.get_surface_count()
	# ⚠️ **A mesh with nothing to render passes every loop below without entering
	# one**, and would take the shader and payload checks down with it silently —
	# the shape of quiet pass this tool exists to remove.
	if surfaces == 0:
		_fail("%s carries a mesh with no surfaces to render" % body.name)
	for surface: int in surfaces:
		var material: Material = body.mesh.surface_get_material(surface)
		var shaded := material as ShaderMaterial
		if shaded == null:
			var what: String = "nothing"
			if material != null:
				what = "%s %s" % [material.get_class(), material.resource_path]
			_fail("%s surface %d renders with %s, not the body shader" % [body.name, surface, what])
			continue
		if shaded.resource_path != MATERIAL_PATH:
			_fail(
				(
					"%s surface %d wears %s, not %s"
					% [body.name, surface, shaded.resource_path, MATERIAL_PATH]
				)
			)
			continue
		found = shaded
	# Which shader backs the material is a property of the material, so it is
	# asked once rather than per surface — reported inside the loop it would
	# print the same line, and count the same defect, once per surface.
	if found != null and (found.shader == null or found.shader.resource_path != SHADER_PATH):
		_fail("%s is not backed by %s" % [MATERIAL_PATH, SHADER_PATH])
	# ⚠️ **Against `_failed`, not against `found`.** `found` only says *some*
	# surface passed, so a two-surface body with one fallback would report the
	# failure and then print an `ok` line claiming both surfaces were shaded —
	# and the `ok` is the line a reader believes.
	if _failed == before:
		print("  ok    the body renders %d surface(s) with %s" % [surfaces, MATERIAL_PATH])
	return found


## The instance uniforms the renderer will actually dispatch on, by name and
## Variant type.
##
## ⚠️ **Asked of the mesh rather than of the shader source, and the two are not
## the same claim.** `set_instance_shader_parameter` matches against this list; a
## name that is in the text but not in here is still a silent no-op. Instance-
## scope uniforms are also **excluded** from `Shader.get_shader_uniform_list()`,
## so the two lists are complementary and each is the authority for its own
## scope — which is why `sun_toward` is checked against the other one.
func _declared_instance_uniforms(body: MeshInstance3D) -> Dictionary:
	var declared: Dictionary = {}
	for property: Dictionary in body.get_property_list():
		var property_name: String = str(property.get("name", ""))
		if property_name.begins_with(INSTANCE_PREFIX):
			declared[property_name.trim_prefix(INSTANCE_PREFIX)] = int(property.get("type", 0))
	return declared


## Every channel the script writes has to be a channel the renderer knows about.
##
## A name the renderer does not list is the silent failure this whole tool exists
## for: `set_instance_shader_parameter` reports nothing, the default `vec4(0.0)`
## stands, and every lamp on the car stays dark.
##
## Returns how many switched circuits the payload can address — the widths of the
## declared vectors added up, which is what the shader's `CIRCUIT_COUNT` derives
## the same way — or **-1 where a channel is missing outright**. ⚠️ The sentinel
## is not tidiness: a lost name silently narrows the sum, and the mesh check would
## then report the car's own lenses as asking for too much. One defect, one
## message, and the message names the shader rather than the mesh.
func _check_the_switched_channels_reach_the_shader(declared: Dictionary) -> int:
	var before: int = _failed
	var channels: int = 0
	var missing: bool = false
	var written: PackedStringArray = _channel_names()
	if written.is_empty():
		_fail("%s names no %s* channel constant to write" % [LAMPS_SCRIPT, CHANNEL_CONSTANT_PREFIX])
		missing = true
	for channel: String in written:
		if not declared.has(channel):
			_fail(
				(
					"%s writes '%s', which %s does not declare as an instance uniform"
					% [LAMPS_SCRIPT, channel, SHADER_PATH]
				)
			)
			missing = true
			continue
		var width: int = _slots(int(declared[channel]))
		if width == 0:
			_fail(
				(
					"'%s' is declared as %s, which carries no countable circuits"
					% [channel, type_string(int(declared[channel]))]
				)
			)
			missing = true
			continue
		channels += width
	if _failed == before:
		print("  ok    %s reach the shader, %d circuits wide" % [", ".join(written), channels])
	return -1 if missing else channels


## The sun belongs to the material, not to the car.
##
## One sun, and every car agreeing about where it is — so `sun_glint.gd` writes it
## with `set_shader_parameter`. ⚠️ Declared per instance instead, that write would
## be taken in silence and the glint would never move, which is the mirror image
## of the lamp channels' failure and just as invisible.
func _check_the_sun_belongs_to_the_material(declared: Dictionary, material: ShaderMaterial) -> void:
	var sun: String = _constant(GLINT_SCRIPT, "PARAMETER")
	if sun.is_empty():
		_fail("%s names no PARAMETER constant" % GLINT_SCRIPT)
	elif declared.has(sun):
		_fail("'%s' is an instance uniform; %s writes it to the material" % [sun, GLINT_SCRIPT])
	elif material == null:
		# The body check already reported why there is no material to ask.
		pass
	elif not _is_material_uniform(material, sun):
		_fail("%s writes '%s', which %s does not declare" % [GLINT_SCRIPT, sun, SHADER_PATH])
	else:
		print("  ok    '%s' is one uniform on the shared material, not one per car" % sun)


## The `UV` payload the shader reads has to survive the import.
##
## `UV.y` is the surface marker and `UV.x` the switched circuit, both `floor()`ed
## in the vertex stage — so a value the importer moved off an integer selects a
## different branch, and a circuit past the payload is dropped by the shader's
## bounds guard and ships dark.
func _check_the_payload_survived_the_import(body: MeshInstance3D, channels: int) -> void:
	var before: int = _failed
	var circuits: Dictionary = {}
	var fractional: int = 0
	var stray_markers: int = 0
	var unreachable: int = 0
	var switched_bodywork: int = 0
	var vertices: int = 0

	for surface: int in body.mesh.get_surface_count():
		var arrays: Array = body.mesh.surface_get_arrays(surface)
		# Typed through a `Variant`, because a surface with no UVs holds `null`
		# here and assigning that to a typed array is a run-time error — which
		# kills the coroutine where it stands and leaves `quit()` uncalled.
		var payload: Variant = arrays[Mesh.ARRAY_TEX_UV]
		if typeof(payload) != TYPE_PACKED_VECTOR2_ARRAY:
			_fail(
				(
					"%s surface %d carries no UVs, so it carries no shader payload"
					% [body.name, surface]
				)
			)
			continue
		var uvs: PackedVector2Array = payload
		vertices += uvs.size()
		for uv: Vector2 in uvs:
			if uv.x != floorf(uv.x) or uv.y != floorf(uv.y):
				fractional += 1
			if uv.y < 0.0 or uv.y > MARKER_LAST:
				stray_markers += 1
			if uv.x == CIRCUIT_NONE:
				continue
			circuits[uv.x] = true
			# ⚠️ **Bounded at both ends, because the shader's guard is.** It drops
			# `channel < 0` exactly as hard as `channel >= CIRCUIT_COUNT`, so a
			# negative circuit is a permanently dark lens — and it would otherwise
			# sail past an upper-bound test and be reported as `ok`.
			if channels >= 0 and (uv.x < 1.0 or uv.x > float(channels)):
				unreachable += 1
			if uv.y != MARKER_LAMP:
				switched_bodywork += 1

	if fractional > 0:
		_fail(
			"%d vertices carry a fractional marker or circuit; the shader floors both" % fractional
		)
	if stray_markers > 0:
		_fail(
			(
				"%d vertices carry a marker outside 0-%.0f, which takes the paint branch"
				% [stray_markers, MARKER_LAST]
			)
		)
	if unreachable > 0:
		_fail(
			(
				"%d vertices ask for a circuit outside the 1-%d the payload carries"
				% [unreachable, channels]
			)
		)
	if switched_bodywork > 0:
		# The shader reads `UV.x` only inside its `MARKER_LAMP` branch, so a
		# circuit on bodywork is never switched — the same rule `_check_wiring`
		# holds in the generator, asked here of what Godot actually imported.
		_fail(
			"%d switched vertices are not lenses, so nothing ever lights them" % switched_bodywork
		)
	if circuits.is_empty():
		_fail("no vertex carries a circuit at all; every lens on the car is unswitched")
	if _failed == before:
		var found: Array = circuits.keys()
		found.sort()
		print("  ok    %d vertices imported carrying circuits %s, lenses only" % [vertices, found])


## The rig has to hang where the script goes looking for its parts.
##
## Both conditions are `assert`s in `vehicle_lamps.gd`, and asserts are stripped
## from release builds — so a scene that fails these ships a car whose lamps never
## switch rather than a car that refuses to start.
func _check_the_rig_hangs_where_the_script_looks(
	car: Node3D, lamps: Node3D, material: ShaderMaterial
) -> void:
	# ⚠️ **`VehicleController.above` itself, not a walk that looks like it.**
	# `vehicle_lamps.gd` resolves its car with exactly this call, and it matches by
	# *type* where a hand-rolled walk would match by script path — so a roster car
	# on a controller subclass finds its car fine and would fail a copy. Reached
	# through `call()` on a `load`ed script rather than by naming the global, which
	# is `verify_beam_budget.gd`'s idiom and for the same fresh-clone reason.
	var controller := load(CONTROLLER_SCRIPT) as GDScript
	if controller == null:
		_fail("%s did not load" % CONTROLLER_SCRIPT)
	elif controller.call(&"above", lamps) == null:
		_fail("the lamp rig has no %s above it to read the car from" % CONTROLLER_SCRIPT)
	else:
		print("  ok    the lamp rig sits under the controller it reads")

	var glint: Node = _running(car, GLINT_SCRIPT)
	if glint == null:
		_fail("no node in %s runs %s" % [SCENE_PATH, GLINT_SCRIPT])
		return
	# A glint written to a material nobody draws is invisible in every automated
	# check this project has, which is `sun_glint.gd`'s own argument for assigning
	# it in the scene rather than looking it up.
	var fed := glint.get("material") as ShaderMaterial
	if fed == null:
		_fail("%s has no material assigned; the taxi's glint tracks nothing" % glint.name)
	elif material == null:
		# The body wears no shader at all, which is already reported. There is
		# nothing to compare against, and ⚠️ an `ok` here would be a claim about
		# the body that the check above has just refuted.
		pass
	elif fed != material:
		# Against the material the body was *found* wearing, so this cannot pass by
		# agreeing with a constant while the car renders with something else.
		_fail(
			"%s feeds %s, which is not what the body renders with" % [glint.name, fed.resource_path]
		)
	else:
		print("  ok    the glint is fed into the material the body renders with")


## The thrown beams have to be authored dark, and aimed at the road.
##
## ⚠️ **`spot_angle` is Godot's *half* angle, and the cone must not reach above
## horizontal.** `P3-11e` shipped 7° down against an 11° half-angle first, which
## put the top of the beam 4° **up**: it lit a dome climbing the screen and read,
## correctly, as a light shining upward. Today that number is guarded by a comment
## in a `.tscn`, and Godot strips those on any editor resave.
func _check_the_beams_point_at_the_road(car: Node3D) -> void:
	# The same search `vehicle_lamps.gd` runs, so this counts the lights the
	# script would actually drive.
	var spots: Array[Node] = car.find_children("*", "SpotLight3D", true, false)
	if spots.is_empty():
		_fail("the player's taxi throws no beams; %s found no SpotLight3D" % SCENE_PATH)
		return
	var before: int = _failed
	var worst: float = -180.0
	for node: Node in spots:
		var beam := node as SpotLight3D
		if beam.visible:
			# `_apply_beam` puts them out on the first `_ready`, but only a car
			# with a lamp rig runs one — and a roster model authored lit would
			# drive through daylight on main beam until something switched it.
			_fail("%s is authored visible; beams are switched on, never off" % beam.name)
		if beam.light_energy <= 0.0 or beam.spot_range <= 0.0:
			_fail(
				(
					"%s throws nothing: energy %.2f over %.2f m"
					% [beam.name, beam.light_energy, beam.spot_range]
				)
			)
		var facing: Vector3 = (-_basis_in(beam, car).z).normalized()
		var top: float = rad_to_deg(asin(clampf(facing.y, -1.0, 1.0))) + beam.spot_angle
		if top >= 0.0:
			_fail(
				(
					"%s reaches %.2f° above horizontal, so part of it never meets the road"
					% [beam.name, top]
				)
			)
		worst = maxf(worst, top)
	if _failed == before:
		print(
			(
				"  ok    %d beams authored dark, topping out %.2f° below horizontal"
				% [spots.size(), -worst]
			)
		)


## The instance-uniform names `vehicle_lamps.gd` writes, in declaration order.
##
## ⚠️ **Left in declaration order, never sorted.** `vehicle_body.gdshader` states
## that the *ordering* of the circuits is the contract and the split into two
## vectors is not, so a sorted list would print `lamp_front, lamp_lit` and read as
## the reverse of the wiring it is reporting on.
func _channel_names() -> PackedStringArray:
	var names: PackedStringArray = []
	var constants: Dictionary = _constants(LAMPS_SCRIPT)
	for key: Variant in constants:
		if str(key).begins_with(CHANNEL_CONSTANT_PREFIX):
			names.append(str(constants[key]))
	return names


## One string constant off a script, or "" where it is not there.
func _constant(path: String, key: String) -> String:
	var constants: Dictionary = _constants(path)
	if not constants.has(key):
		return ""
	return str(constants[key])


## A script's constants, or an empty dictionary if it did not load.
##
## Built once per call — `get_script_constant_map()` returns a fresh Dictionary
## every time, so indexing it inside the loop that walks it rebuilds it per hit.
func _constants(path: String) -> Dictionary:
	var script := load(path) as GDScript
	if script == null:
		_fail("%s did not load" % path)
		return {}
	return script.get_script_constant_map()


## How many switched circuits a channel of this Variant type carries.
##
## Written as a lookup rather than assumed to be four, because the seam between
## `lamp_lit` and `lamp_front` is where GLSL put it rather than where the car
## divides — `vehicle_body.gdshader` says so — and a widened payload should be
## counted, not re-asserted.
##
## `TYPE_COLOR` is four as well: a `vec4` carrying a `: source_color` hint arrives
## here as a colour, and it is still four channels a circuit can be indexed out of.
func _slots(type: int) -> int:
	match type:
		TYPE_FLOAT:
			return 1
		TYPE_VECTOR2:
			return 2
		TYPE_VECTOR3:
			return 3
		TYPE_VECTOR4, TYPE_COLOR:
			return 4
	return 0


func _is_material_uniform(material: ShaderMaterial, uniform: String) -> bool:
	for property: Dictionary in material.shader.get_shader_uniform_list(false):
		if str(property.get("name", "")) == uniform:
			return true
	return false


## The first node at or below `branch` running the script at `path`.
func _running(branch: Node, path: String) -> Node:
	if _runs(branch, path):
		return branch
	for node: Node in branch.find_children("*", "", true, false):
		if _runs(node, path):
			return node
	return null


func _runs(node: Node, path: String) -> bool:
	var script := node.get_script() as Script
	return script != null and script.resource_path == path


## The mesh `vehicle_lamps.gd` would switch — its own search, first hit and all,
## because grading a different mesh than the script writes to would pass while the
## car stayed dark.
func _body_under(lamps: Node3D) -> MeshInstance3D:
	var found: Array[Node] = lamps.find_children("*", "MeshInstance3D", true, false)
	if found.is_empty():
		return null
	return found[0] as MeshInstance3D


## `node`'s basis in `ancestor`'s space.
##
## Accumulated by hand because `global_transform` returns identity and pushes an
## error outside the tree, and nothing here is ever added to one — the same trap
## `mesh_contract.gd` documents for bounds.
func _basis_in(node: Node3D, ancestor: Node3D) -> Basis:
	var basis: Basis = node.transform.basis
	var walker: Node = node.get_parent()
	while walker != null and walker != ancestor:
		var spatial := walker as Node3D
		if spatial != null:
			basis = spatial.transform.basis * basis
		walker = walker.get_parent()
	return basis


func _fail(message: String) -> void:
	_failed += 1
	printerr("  FAIL  %s" % message)


func _finish() -> void:
	if _failed > 0:
		printerr("vehicle: %d check(s) failed" % _failed)
		quit(1)
		return
	print("  ok    verify_vehicle")
	quit(0)
