@tool
extends Node3D
## Feeds the scene's real sun direction into `vehicle_body.gdshader`.
##
## The glint needs to know where the sun is, and the shader cannot ask: Godot 4
## exposes light only inside a `light()` function, and writing one there would
## replace the default lighting wholesale for a highlight.
##
## ⚠️ **The point of this script is that the vector is never authored twice.**
## The obvious alternative — a `sun_direction` default typed into
## `vehicle_body.tres` to match the rig — is a second copy of the
## `DirectionalLight3D`'s rotation, and the two would drift silently the first
## time the sun is retuned or `Q26`'s night mode adds a second rig. Nothing
## would report it; the glint would simply point somewhere the sun is not. That
## is the same failure shape `P3-11`'s chassis guard exists for, and the fix is
## the same: read the authority instead of copying it.
##
## Runs once on ready rather than per frame. **This sun does not move** —
## `DECISIONS.md` records night as a *switch* between two static rigs, not a
## cycle — so a per-frame write would be the same value every frame forever.
## Re-running it is what a rig switch owes.

## Where the material expects the vector.
const PARAMETER: StringName = &"sun_direction"

## The material to feed. Assigned in the scene rather than looked up, so a
## missing wiring fails here with a message instead of somewhere in a render.
@export var material: ShaderMaterial


func _ready() -> void:
	apply()


## Find the scene's sun and push its facing into the material.
##
## Public so a rig switch can call it. Reports rather than guesses: a glint
## aimed at a sun that is not there is invisible in every automated check this
## project has, because the frame still renders and still exits `0`.
func apply() -> void:
	if material == null:
		push_warning("sun_glint: no material assigned; the taxi's glint will not track the sun")
		return

	var sun: DirectionalLight3D = _find_sun()
	if sun == null:
		# The taxi was loaded without a world around it — a verify tool, an
		# import, the editor. There is no rig to read and no frame to be wrong,
		# so this is silent: a warning here fires on every `tools/check.sh` run,
		# and one that cries wolf every build is not read when it matters.
		return

	# A `DirectionalLight3D` shines along its own -Z, which is the convention the
	# shader's `-normalize(sun_direction)` is written against.
	material.set_shader_parameter(PARAMETER, -sun.global_transform.basis.z)


## Search from the window root, **not `get_tree().current_scene`**.
##
## ⚠️ **`current_scene` is null in a driver run and this cost a whole round of
## tuning.** `.claude/skills/run-hk-taxi-q/driver.gd` instantiates the scene and
## `add_child`s it to the root; nothing assigns `current_scene`, which only
## `change_scene_to_*` and the boot path set. An earlier version returned early
## on a null `current_scene` — a guard added to suppress a `check.sh` warning —
## and so silently left `sun_direction` at its default in **every** measured
## drive, which read as "the glint does nothing" rather than as "the glint never
## ran". The window root is populated on every load path there is.
func _find_sun() -> DirectionalLight3D:
	var root: Node = get_tree().root
	for light: DirectionalLight3D in root.find_children("*", "DirectionalLight3D", true, false):
		if light.visible:
			return light
	return null
