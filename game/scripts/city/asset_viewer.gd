extends Node3D
## Dev: stand one `.glb` under the shipped rig and say what the importer did
## to it (`P5-22`).
##
## The artist's loop. Every other dev scene draws a region, so seeing a prop
## under the shipped lighting and the shipped shaders needed the ETL, a fetch
## and a build; this needs the one file. It applies nothing of its own — the
## asset arrives exactly as `generated_scene_import.gd` handed it to the
## engine, which is the point: the readout is what an artist would otherwise
## learn only by dropping the model into the drive and driving to it.
##
## Not shipped: `scenes/dev/`, like the other three.

const MeshContract = preload("res://scripts/city/mesh_contract.gd")

## Names the `.glb` to stand: `--asset=res://assets/authored/…`. Read from the
## command line the way `--debug-view=` and `--hud=` are, and for the same
## reason — `drive.sh` cannot set a scene's exports.
const ASSET_ARG: String = "--asset="
## What stands when nothing is named: the repository's one real DCC export, so
## F6 in the editor shows something and `verify_authored.gd`'s numbers can be
## read off the screen.
const DEFAULT_ASSET: String = "res://assets/authored/fixtures/dcc_roundtrip.glb"

## Offered to the fly camera so it frames whatever was stood — the contract
## `tile_preview.gd` and `city_streamer.gd` offer.
signal built(low: Vector3, high: Vector3)

## The asset turns on the physics tick, so a `drive.sh` shot at a given time
## is the same frame every run (`Q27`'s determinism). 0 holds it still.
@export var turntable_deg_per_s: float = 15.0

var _asset: Node3D = null


func _ready() -> void:
	var path: String = Cmdline.value(ASSET_ARG)
	if path.is_empty():
		path = DEFAULT_ASSET
	if not ResourceLoader.exists(path, "PackedScene"):
		printerr("  FAIL  asset viewer: no scene at %s" % path)
		get_tree().quit(1)
		return
	var packed := load(path) as PackedScene
	if packed == null:
		printerr("  FAIL  asset viewer: %s did not load as a scene" % path)
		get_tree().quit(1)
		return
	_asset = packed.instantiate() as Node3D
	if _asset == null:
		printerr("  FAIL  asset viewer: %s's root is not a Node3D" % path)
		get_tree().quit(1)
		return
	add_child(_asset)
	var lines: PackedStringArray = report(path, _asset)
	for line: String in lines:
		print("asset: ", line)
	_show(lines)
	var box: AABB = MeshContract.bounds(_asset)
	built.emit(box.position, box.end)


func _physics_process(delta: float) -> void:
	if _asset != null:
		_asset.rotate_y(deg_to_rad(turntable_deg_per_s) * delta)


## What the importer did, one line per fact, in the order an artist checks
## them: the whole, then each mesh and each of its surfaces.
static func report(path: String, asset: Node3D) -> PackedStringArray:
	var lines: PackedStringArray = []
	var box: AABB = MeshContract.bounds(asset)
	lines.append(path)
	lines.append("%d triangles" % MeshContract.triangles(asset))
	lines.append(
		(
			"aabb %.2f x %.2f x %.2f m, base y %.3f"
			% [box.size.x, box.size.y, box.size.z, box.position.y]
		)
	)
	for found: Node in asset.find_children("*", "MeshInstance3D", true, false):
		var instance: MeshInstance3D = found as MeshInstance3D
		var parent: String = (
			String(instance.get_parent().name) if instance.get_parent() != null else "-"
		)
		var colliders: int = MeshContract.colliders(instance)
		lines.append(
			(
				"%s under %s: %d surface(s), %s"
				% [
					instance.name,
					parent,
					instance.mesh.get_surface_count(),
					"collider" if colliders > 0 else "no collider"
				]
			)
		)
		for surface: int in instance.mesh.get_surface_count():
			lines.append("  " + _surface_line(instance, surface))
	return lines


static func _surface_line(instance: MeshInstance3D, surface: int) -> String:
	var has_colour: bool = (
		(instance.mesh.surface_get_format(surface) & Mesh.ARRAY_FORMAT_COLOR) != 0
	)
	var colour: String = "COLOR_0" if has_colour else "no COLOR_0"
	var material: Material = instance.get_active_material(surface)
	if material == null:
		return "surface %d: no material, %s" % [surface, colour]
	if material is ShaderMaterial:
		return (
			"surface %d: %s -> %s, %s"
			% [surface, material.resource_name, material.resource_path, colour]
		)
	var authored := material as StandardMaterial3D
	if authored == null:
		return (
			"surface %d: %s kept (%s), %s"
			% [surface, material.resource_name, material.get_class(), colour]
		)
	var texture: String = "no texture"
	if authored.albedo_texture != null:
		texture = (
			"albedo texture %dx%d"
			% [authored.albedo_texture.get_width(), authored.albedo_texture.get_height()]
		)
	var vertex_albedo: String = (
		"vertex colour as albedo"
		if authored.vertex_color_use_as_albedo
		else "vertex colour ignored"
	)
	return (
		"surface %d: %s kept as authored, %s, %s, %s"
		% [surface, authored.resource_name, texture, vertex_albedo, colour]
	)


func _show(lines: PackedStringArray) -> void:
	var layer := CanvasLayer.new()
	layer.name = "Readout"
	var label := Label.new()
	label.text = "\n".join(lines)
	label.position = Vector2(16.0, 16.0)
	DebugHud.style_label(label, 20)
	layer.add_child(label)
	add_child(layer)
