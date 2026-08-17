class_name SunGlint
extends Node3D
## Feeds the scene's real sun direction into `vehicle_body.gdshader`.
##
## ⚠️ **`class_name` is here for `find_sun` and not for this node.** Nothing
## instances this by type — `taxi.tscn` names the script by path — but
## `vehicle_lamps.gd` needs the same sun this does, and the lookup below is
## worth more than it looks: it is the one that had to learn `current_scene` is
## null in a driver run. A private second copy would relearn that the same way.
##
## The glint needs to know where the sun is, and the shader cannot ask: Godot 4
## exposes light only inside a `light()` function, and writing one there would
## replace the default lighting wholesale for a highlight.
##
## ⚠️ **The point of this script is that the vector is never authored twice.**
## The obvious alternative — a `sun_toward` default typed into
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
##
## ⚠️ **Deliberately not `@tool`.** The material below is the *shared*, committed
## `vehicle_body.tres`, and `set_shader_parameter` marks a loaded resource
## edited. Running at edit time would mutate it whenever a scene containing both
## a taxi and a sun is opened, and Godot's "save external resources?" prompt
## would then write a runtime-computed vector into the versioned file over the
## authored default. There is nothing to see in the editor here anyway: the
## glint only means something in a running frame.

## ⚠️ Named for what the shader needs — the direction **toward** the sun, not
## the direction light travels. The two differ by a sign, and getting it
## backwards aims the glint at the antisolar point, where it is simply never
## seen rather than visibly wrong.
const PARAMETER: StringName = &"sun_toward"

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

	var sun: DirectionalLight3D = find_sun(self)
	if sun == null:
		# The taxi was loaded without a world around it — a verify tool, an
		# import, the editor. There is no rig to read and no frame to be wrong,
		# so this is silent: a warning here fires on every `tools/check.sh` run,
		# and one that cries wolf every build is not read when it matters.
		return

	material.set_shader_parameter(PARAMETER, toward(sun))


## The unit vector pointing **at** the sun, from the rig's own transform.
##
## ⚠️ **Shared with `vehicle_lamps.gd`, and the sign is the reason.** A
## `DirectionalLight3D` shines along its own -Z, so +Z points back at the source
## — one fact, and every consumer of it fails silently when it is wrong. The
## glint aimed backwards lands on the antisolar point, where it is simply never
## seen; the lamps' shadow probe aimed backwards looks merely erratic. Neither
## shows up in any automated check this project has, which is the whole argument
## for one definition. This file already refuses to let the *rig* be authored
## twice; the conversion off it is the same rule one step further on.
##
## ⚠️ **Normalised here rather than in the shader**, which is where it was. A
## rotation basis is unit-length and both shipped rigs measure so, but nothing
## enforces it — a scaled parent would silently denormalise it. Doing it once on
## the CPU keeps the guarantee and takes an `rsqrt` off every fragment of every
## frame, where it was recomputing a constant.
static func toward(sun: DirectionalLight3D) -> Vector3:
	return sun.global_transform.basis.z.normalized()


## The scene's key light, or null where there is no rig loaded.
##
## Static, and shared with `vehicle_lamps.gd`: the glint needs where the sun is
## and the lamps need whether there is one, and those are the same question
## asked twice. `from` is any node in the tree — the search does not start there.
##
## Search from the window root, **not `get_tree().current_scene`**.
##
## ⚠️ **`current_scene` is null in a driver run and this cost a whole round of
## tuning.** `.claude/skills/run-hk-taxi-q/driver.gd` instantiates the scene and
## `add_child`s it to the root; nothing assigns `current_scene`, which only
## `change_scene_to_*` and the boot path set. An earlier version returned early
## on a null `current_scene` — a guard added to suppress a `check.sh` warning —
## and so silently left `sun_toward` at its default in **every** measured
## drive, which read as "the glint does nothing" rather than as "the glint never
## ran". The window root is populated on every load path there is.
static func find_sun(from: Node) -> DirectionalLight3D:
	var root: Node = from.get_tree().root
	for light: DirectionalLight3D in root.find_children("*", "DirectionalLight3D", true, false):
		if light.visible:
			return light
	return null
