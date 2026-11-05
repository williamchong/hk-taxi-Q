class_name ShaderWarmup
extends CanvasLayer
## The cover over the menu's first seconds: every material the level draws is
## compiled behind it, once, before the player can see a frame stall.
##
## ⚠️ **The web build compiles a shader the first time something draws with it,
## and on a cold GPU cache that is seconds.** Measured on the export with Chrome's
## Metal shader cache emptied: a 13.6 s boot, then 733, 2124 and 595 ms frames in
## the menu's first seconds and 312 and 462 ms as the drive started; warm, the
## same frames were 107, 180, 73 and 66 ms. A first-time player is always cold.
## The Compatibility renderer has no shader baker and no ubershader, so the cost
## cannot be removed — only moved to where a wait is expected.
##
## How: once the city's first pass has settled, one copy of each distinct thing
## the level draws stands shrunk in a grid in front of the camera for
## `cover_warm_frames`, and the HUD is shown under the cover with them. A copy
## shares its source's mesh and materials and keeps its draw kind — a
## `MultiMesh` stays a one-instance `MultiMesh` with the same formats — so the
## variant compiled is the one the city asks for, shadow pass included. Then the
## copies go and the cover fades.
##
## Only under the menu (`Main`): `--menu=off`, every scripted run, never puts a
## cover over a frame. Native renderers pay a few milliseconds for it.

signal finished

## Over the menu (`StartMenu.LAYER`) and the HUD.
const LAYER: int = 100

var _profile: MenuProfile = null
var _cover: ColorRect = null
var _settled: bool = false


func _ready() -> void:
	layer = LAYER
	_profile = load(MenuProfile.PATH) as MenuProfile
	var style := load(HudStyle.PATH) as HudStyle
	_cover = ColorRect.new()
	_cover.name = "Cover"
	_cover.color = Color(style.plate_field, 1.0) if style != null else Color.BLACK
	_cover.mouse_filter = Control.MOUSE_FILTER_STOP
	_cover.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(_cover)


## Wait for `regions` to settle, draw a copy of everything under `level` and
## the HUD for a few frames, then fade and free. `finished` as the fade starts.
func warm(level: Node3D, regions: CityRegions, hud: CanvasLayer) -> void:
	if _profile == null:
		push_warning("ShaderWarmup: %s did not load; nothing warmed" % MenuProfile.PATH)
		_finish()
		return
	# Connected inside `Main._ready`, before any `_process`: the streamer emits
	# `built` deferred from its first settle, so it cannot have fired yet.
	if regions != null:
		regions.built.connect(_on_built, CONNECT_ONE_SHOT)
	var waited: int = 0
	while not _settled and regions != null and waited < _profile.cover_wait_frames:
		await get_tree().process_frame
		waited += 1
	for _frame: int in _profile.cover_settle_frames:
		await get_tree().process_frame
	var camera: Camera3D = get_viewport().get_camera_3d()
	var copies: Node3D = null
	if camera != null:
		copies = _copies(level)
		camera.add_child(copies)
		copies.position = Vector3(0.0, 0.0, -_profile.warm_distance_m)
	var hud_shown: bool = hud != null and hud.visible
	if hud != null:
		hud.visible = true
	# Process frames, not `frame_post_draw`: the headless renderer never draws,
	# and a cover waiting on it would never lift.
	for _frame: int in _profile.cover_warm_frames:
		await get_tree().process_frame
	# The camera, and the copies with it, can be gone after the frames.
	if is_instance_valid(copies):
		print("warmup: %d copies after %d frames" % [copies.get_child_count(), waited])
		copies.queue_free()
	if hud != null:
		hud.visible = hud_shown
	_finish()


func _on_built(_low: Vector3, _high: Vector3) -> void:
	_settled = true


func _finish() -> void:
	finished.emit()
	var fade: float = _profile.cover_fade_s if _profile != null else 0.0
	var tween: Tween = create_tween()
	tween.tween_property(_cover, "modulate:a", 0.0, fade)
	tween.tween_callback(queue_free)


## One shrunk copy of each distinct draw under `root`, in a square grid on the
## holder's plane.
func _copies(root: Node) -> Node3D:
	var holder := Node3D.new()
	holder.name = "WarmCopies"
	var seen: Dictionary[String, bool] = {}
	var made: Array[GeometryInstance3D] = []
	for node: Node in root.find_children("*", "GeometryInstance3D", true, false):
		var drawn := node as GeometryInstance3D
		var key: String = _key(drawn)
		if key.is_empty() or seen.has(key):
			continue
		seen[key] = true
		made.append(_copy(drawn))
	var side: int = maxi(1, ceili(sqrt(float(made.size()))))
	var step: float = _profile.warm_size_m * 1.5
	for index: int in made.size():
		var copy: GeometryInstance3D = made[index]
		var cell := Vector3(
			(float(index % side) - side * 0.5) * step,
			(floorf(float(index) / side) - side * 0.5) * step,
			0.0
		)
		var box: AABB = copy.get_aabb()
		var longest: float = maxf(box.get_longest_axis_size(), 0.001)
		var shrink: float = _profile.warm_size_m / longest
		copy.scale = Vector3.ONE * shrink
		copy.position = cell - box.get_center() * shrink
		holder.add_child(copy)
	return holder


## What decides the compiled variant: the draw kind, its formats and every
## material it draws with. "" for a node this does not copy. Particles are
## `ParticleWarmup`'s, at their own load.
func _key(node: GeometryInstance3D) -> String:
	var parts: PackedStringArray = [
		_id(node.material_override),
		_id(node.material_overlay),
		str(node.cast_shadow),
		str(node.layers)
	]
	if node is MeshInstance3D:
		var single := node as MeshInstance3D
		if single.mesh == null:
			return ""
		parts.append("mesh")
		for surface: int in single.mesh.get_surface_count():
			parts.append(_id(single.get_active_material(surface)))
	elif node is MultiMeshInstance3D:
		var multi: MultiMesh = (node as MultiMeshInstance3D).multimesh
		if multi == null or multi.mesh == null or multi.transform_format != MultiMesh.TRANSFORM_3D:
			return ""
		parts.append("multi %s %s" % [multi.use_colors, multi.use_custom_data])
		for surface: int in multi.mesh.get_surface_count():
			parts.append(_id(multi.mesh.surface_get_material(surface)))
	else:
		return ""
	return " ".join(parts)


static func _id(material: Material) -> String:
	return str(material.get_instance_id()) if material != null else "-"


## A copy drawing as `node` draws: the same mesh and materials, one instance.
## Only for a node `_key` accepted.
func _copy(node: GeometryInstance3D) -> GeometryInstance3D:
	var copy: GeometryInstance3D = null
	if node is MeshInstance3D:
		var single := node as MeshInstance3D
		var drawn := MeshInstance3D.new()
		drawn.mesh = single.mesh
		for surface: int in single.mesh.get_surface_count():
			drawn.set_surface_override_material(
				surface, single.get_surface_override_material(surface)
			)
		copy = drawn
	else:
		var source: MultiMesh = (node as MultiMeshInstance3D).multimesh
		var multi := MultiMesh.new()
		multi.transform_format = MultiMesh.TRANSFORM_3D
		multi.use_colors = source.use_colors
		multi.use_custom_data = source.use_custom_data
		multi.mesh = source.mesh
		multi.instance_count = 1
		multi.set_instance_transform(0, Transform3D.IDENTITY)
		var drawn := MultiMeshInstance3D.new()
		drawn.multimesh = multi
		copy = drawn
	copy.material_override = node.material_override
	copy.material_overlay = node.material_overlay
	copy.cast_shadow = node.cast_shadow
	copy.layers = node.layers
	return copy
