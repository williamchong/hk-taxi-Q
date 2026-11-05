class_name VehicleBodyBatch
extends RefCounted
## `vehicle_body.gdshader` for a `MultiMesh`: the same material with its two
## `instance uniform`s compiled out (`VEHICLE_BATCHED`).
##
## ⚠️ **Not an optimisation: the web build ran out of slots.** Every node drawn
## with an instance uniform holds 16 slots of the global shader buffer, which the
## Compatibility renderer caps at the hardware's uniform block. A parked cell's
## kinds are a `MultiMeshInstance3D` each, so the web build asked for more than
## there were and logged 83 `Too many instances using shader instance variables`
## a load. A batch reads its lamps from `INSTANCE_CUSTOM.a` and never had its
## instance channels written — only `VehicleLamps` writes them, on the player's
## car — so the constants are what it drew all along.
##
## One material, built once from `vehicle_body.tres` so the two cannot drift: a
## `duplicate` carries every parameter, and only the shader differs.

const MATERIAL_PATH: String = "res://tuning/vehicle_body.tres"
const DEFINE: String = "#define VEHICLE_BATCHED"
const SHADER_TYPE: String = "shader_type spatial;"

static var _material: ShaderMaterial = null
## Each car mesh's batched copy, by the source mesh's instance id.
static var _meshes: Dictionary[int, Mesh] = {}


## `mesh`, or a copy of it whose `vehicle_body.tres` surfaces draw with the
## batched material. A mesh with no such surface is returned as it is.
static func batched(mesh: Mesh) -> Mesh:
	var array := mesh as ArrayMesh
	if array == null:
		return mesh
	var key: int = mesh.get_instance_id()
	var cached: Mesh = _meshes.get(key)
	if cached != null:
		return cached
	var copy: ArrayMesh = null
	for surface: int in array.get_surface_count():
		var worn := array.surface_get_material(surface)
		if worn == null or worn.resource_path != MATERIAL_PATH:
			continue
		if copy == null:
			copy = array.duplicate() as ArrayMesh
		copy.surface_set_material(surface, material())
	# Only a copy is kept: a fence or a sign rescans its few surfaces next time
	# rather than being pinned here for the session.
	if copy == null:
		return mesh
	_meshes[key] = copy
	return copy


## The batched material, built on first use.
static func material() -> ShaderMaterial:
	if _material != null:
		return _material
	var source := load(MATERIAL_PATH) as ShaderMaterial
	assert(source != null and source.shader != null, "%s has no shader" % MATERIAL_PATH)
	var code: String = source.shader.code
	# After the `shader_type` line, which must come first.
	assert(code.count(SHADER_TYPE) == 1, "vehicle_body.gdshader's shader_type moved")
	var shader := Shader.new()
	shader.code = code.replace(SHADER_TYPE, SHADER_TYPE + "\n" + DEFINE)
	_material = source.duplicate() as ShaderMaterial
	_material.shader = shader
	return _material
