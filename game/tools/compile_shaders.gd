## Compiles every shader in the project on a real renderer, so `check.sh` can
## fail on one that does not.
##
## Run WITHOUT `--headless`, once per renderer:
##
##     godot --path game --script res://tools/compile_shaders.gd
##     godot --rendering-method gl_compatibility --path game --script res://tools/compile_shaders.gd
##
## 🔴 **Under `--headless` this compiles nothing.** The dummy renderer accepts
## any shader code, so `undefined_symbol_xyz` planted in `marking_paint.gdshader`
## passed every headless step `check.sh` ran. A real renderer parses the code
## when the shader loads and prints `SHADER ERROR`, which `check.sh` greps for:
## Godot still exits 0.
##
## Walks `res://` for `.gdshader` files, so a shader added anywhere is
## compiled; an include (`.gdshaderinc`) compiles inside its includer. Exits
## non-zero if it found none, so a walk that reached nothing is not a pass.
extends SceneTree


func _init() -> void:
	var found := _shaders("res://")
	for path: String in found:
		var shader: Shader = load(path)
		# A bare load() compiled nothing (measured); reading the uniforms back
		# makes the server take the code.
		shader.get_shader_uniform_list()
	if found.is_empty():
		push_error("compile_shaders: no .gdshader under res://, so nothing was compiled")
		quit(1)
		return
	print(
		(
			"  compiled %d shaders on %s"
			% [found.size(), RenderingServer.get_current_rendering_method()]
		)
	)
	quit(0)


func _shaders(dir_path: String) -> PackedStringArray:
	var out := PackedStringArray()
	var dir := DirAccess.open(dir_path)
	for sub: String in dir.get_directories():
		if not sub.begins_with("."):
			out.append_array(_shaders(dir_path.path_join(sub)))
	for file: String in dir.get_files():
		if file.ends_with(".gdshader"):
			out.append(dir_path.path_join(file))
	return out
