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
##
## 🔴 **The range is the guard `P5-28c` would otherwise have deleted.** The ETL's
## `_exposure_anchor` validator refused `0.0` by name, because zero makes every
## shipped colour black and then satisfies the palette rule for *any* declared
## reflectance — a rule that reads as enforced and has become a no-op. Moving the
## number here moved that trap here with it, so the bound comes too. ⚠️ **The
## ceiling is above 1.0 on purpose**: a city brighter than its own materials is a
## coherent direction, and the bound is here to be two-sided, not to limit taste.
##
## ⚠️ **This scales `COLOR_0` albedo and nothing else.** `city_facade_clean`'s
## `glass_colour` and `base_colour`, the `marking_paint` and `railings` `.tres`
## colours, `signs_text` and `vehicle_body` are all untouched by it — so "a time
## of day is one number" is true of the vertex-colour half of the city, and the
## window panes, the road paint and the fences would need their own answer.
@export_range(0.001, 2.0) var exposure_anchor: float = 1.0


func _ready() -> void:
	RenderingServer.global_shader_parameter_set(&"exposure_anchor", exposure_anchor)
