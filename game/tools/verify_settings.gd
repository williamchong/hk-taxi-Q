## Asserts the project settings `check.sh` used to grep for, read back through
## `ProjectSettings` — the value in force, not the line in the file.
##
## Run:
##
##     godot --headless --path game --script res://tools/verify_settings.gd
##
## 🔴 **A grep of `project.godot` was the wrong instrument, and this replaces
## it.** Godot's own writer — the editor's save and `ProjectSettings.save()`
## alike — omits every key whose value equals the engine's registered default.
## Three of the 21 warning promotions (`native_method_override`,
## `get_node_default_without_onready`, `onready_with_export`) default to error
## already, and `rendering/renderer/rendering_method.web` is registered with
## `gl_compatibility` as its default, so all four vanish from the file on every
## save while staying in force. The grep read that as "the editor dropped the
## settings" for three weeks and three decision entries. Reading the setting
## back sees the value whatever the file says, so a canonical, editor-written
## `project.godot` passes here and a genuinely lost setting fails.
##
## ⚠️ **`max_fps.mobile` has no registered default, so the writer keeps it** —
## which is why it always survived while `rendering_method.web` never did. Both
## are checked the same way here.
##
## Needs no built region. Exits non-zero on any mismatch.
extends SceneTree

## The 21 warnings docs/ARCHITECTURE.md "GDScript warnings" promotes. Named here
## rather than counted, so a promotion swapped for a different one fails.
const PROMOTED: PackedStringArray = [
	"unused_variable",
	"unused_local_constant",
	"unused_private_class_variable",
	"unused_parameter",
	"unused_signal",
	"shadowed_variable",
	"shadowed_variable_base_class",
	"standalone_expression",
	"standalone_ternary",
	"incompatible_ternary",
	"untyped_declaration",
	"redundant_await",
	"integer_division",
	"narrowing_conversion",
	"int_as_enum_without_cast",
	"int_as_enum_without_match",
	"confusable_identifier",
	"confusable_local_declaration",
	"native_method_override",
	"get_node_default_without_onready",
	"onready_with_export",
]

## Every other pinned value, with the row in docs/ARCHITECTURE.md "Project
## settings" that says why.
const PINNED: Dictionary = {
	"rendering/renderer/rendering_method": "mobile",
	"rendering/renderer/rendering_method.web": "gl_compatibility",
	"application/run/max_fps.mobile": 60,
	"rendering/anti_aliasing/quality/msaa_3d": 2,
	"physics/3d/physics_engine": "Jolt Physics",
	"rendering/textures/vram_compression/import_etc2_astc": true,
	"display/window/stretch/mode": "canvas_items",
	"rendering/occlusion_culling/use_occlusion_culling": true,
}

## The rig's exposure, declared as a global shader parameter (`P5-28b`).
##
## 🔴 **Pinned here rather than grepped, and pinned as a whole entry**, because a
## global that is *missing* is not a compile error — Godot resolves an undeclared
## `global uniform` to zero, and the six shaders that read it would draw a black
## city with `check.sh` green. The type is pinned with the value for the same
## reason: declared as an `int` it truncates 0.520 to 0 and fails the same way.
##
## ⚠️ **The value is 1.0 until `P5-28c` un-bakes the ETL side**, and the number
## here is the *project default* rather than the shipped exposure —
## `scripts/world/lighting_rig.gd` sets what a scene actually renders at. What
## this pin protects is a scene with no rig, which is `skidpad.tscn` and the
## grey box: they render unexposed, which is the honest state and a visible one.
const SHADER_GLOBALS: Dictionary = {
	"exposure_anchor": {"type": "float", "value": 1.0},
}

## `[importer_defaults]` seeds every NEW `.import`; `Q82` and the importer
## default row record why each key is load-bearing.
const IMPORTER_SCENE: Dictionary = {
	"import_script/path": "res://tools/generated_scene_import.gd",
	"meshes/force_disable_compression": true,
	"meshes/generate_lods": false,
}

var _failed: int = 0


func _init() -> void:
	for warning: String in PROMOTED:
		var key: String = "debug/gdscript/warnings/%s" % warning
		var level: int = int(ProjectSettings.get_setting(key, -1))
		if level != 2:
			_fail("%s is %d, want 2 (error)" % [key, level])

	for key: String in PINNED:
		var got: Variant = ProjectSettings.get_setting(key, null)
		if got != PINNED[key]:
			_fail("%s is %s, want %s" % [key, got, PINNED[key]])

	for name: String in SHADER_GLOBALS:
		var declared: Variant = ProjectSettings.get_setting("shader_globals/%s" % name, null)
		if declared == null:
			_fail("shader_globals/%s is not declared" % name)
			continue
		var want: Dictionary = SHADER_GLOBALS[name]
		var got: Dictionary = declared as Dictionary
		for key: String in want:
			if not got.has(key) or got[key] != want[key]:
				_fail("shader_globals/%s.%s is %s, want %s" % [name, key, got.get(key), want[key]])

	var scene: Dictionary = ProjectSettings.get_setting("importer_defaults/scene", {})
	for key: String in IMPORTER_SCENE:
		if not scene.has(key) or scene[key] != IMPORTER_SCENE[key]:
			_fail("importer_defaults/scene lacks %s = %s" % [key, IMPORTER_SCENE[key]])

	if _failed > 0:
		printerr("  FAIL  verify_settings: %d setting(s) off — see docs/ARCHITECTURE.md" % _failed)
		printerr('        "Project settings". Restore the value; do NOT edit this list to match.')
		quit(1)
		return
	print(
		(
			(
				"  ok    verify_settings — %d warnings promoted, %d values pinned, "
				+ "%d importer defaults, %d shader globals"
			)
			% [PROMOTED.size(), PINNED.size(), IMPORTER_SCENE.size(), SHADER_GLOBALS.size()]
		)
	)
	quit(0)


func _fail(message: String) -> void:
	_failed += 1
	printerr("  FAIL  ", message)
