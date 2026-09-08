class_name LightingRig
extends Node3D
## A time of day: an environment, a sun, and the exposure the city's albedo is
## read at (`P5-28b`, `Q38`).
##
## 🔴 **The exposure lives here because it is art direction and not evidence.**
## `Q33` states every authored colour as `material reflectance x exposure_anchor`
## — the reflectance is a published albedo that travels to another city unchanged,
## and the anchor is the one number carrying the sun, the latitude and the mood.
## Until `P5-28c` the anchor was applied in `etl/pipeline/config.py` at load, so
## it shipped multiplied into `COLOR_0` on every vertex of every tile and a change
## of hour was a full region rebuild. It is a global shader parameter now, and a
## rig is where the sun already is.
##
## ⚠️ **Set in `_ready`, and therefore per scene rather than per viewport.**
## `RenderingServer.global_shader_parameter_set` is process-wide, so two rigs
## alive at once would fight and the last one readied would win. That is the
## honest shape of the thing today — there is one rig in a scene, and a
## cross-fade between two would need a different mechanism, not a second setter
## racing this one.
##
## ⚠️ **A scene with no rig renders at the project default**, `project.godot`'s
## `[shader_globals]` 1.0 — unexposed, which is `skidpad.tscn` and the grey box
## (`P5-24` gives each its own `Sun`). That is deliberate: an unexposed city is
## visibly pale and neither scene has a frame anybody grades, where a silent
## fallback to the shipped value would hide a rig that failed to load.

## The linear-light scale applied to every `COLOR_0` albedo in the city.
##
## ⚠️ **Both halves of `Q33`'s product must move together.** The ETL publishes
## `materials:` colours at reflectance level and this scales them; a build where
## one side moved and the other did not renders at the square of the anchor, or
## at none of it. `city.json`'s `schema_version` is what refuses the mismatch.
@export var exposure_anchor: float = 1.0


func _ready() -> void:
	RenderingServer.global_shader_parameter_set(&"exposure_anchor", exposure_anchor)
