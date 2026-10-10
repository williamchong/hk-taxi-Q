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
## ⚠️ **Set here, and therefore per scene rather than per viewport.**
## `RenderingServer.global_shader_parameter_set` is process-wide, so two rigs
## alive at once would fight and the last one readied would win. There is one
## rig in a scene, and a change of hour is THIS rig blending toward a
## `RigKeyframe` — never a second rig cross-fading in (`Q160`).
##
## 🔴 **The sun moves since `Q160`** (the user's ask: a mode that runs from day
## to night as game time), reversing "night is a switch between two static
## rigs". A rig with a `cycle` takes `time_of_day` from a `DayClock` and blends
## the sky, the ambient, the key light and two shader globals between the scene
## as authored and the cycle's keyframes; `changed` tells the consumers that
## cached the sun (`SunGlint`, `VehicleLamps`) to read it again. ⚠️ **At
## `time_of_day` 0 nothing is written at all** — not the authored values
## written back, nothing — so every scene that never moves the clock renders
## the frame it rendered before there was one.
##
## ⚠️ **A scene with no rig renders at the project default**, `project.godot`'s
## `[shader_globals]` 1.0 — unexposed, which is `skidpad.tscn` and the grey box
## (`P5-24` gives each its own `Sun`). That is deliberate: an unexposed city is
## visibly pale and neither scene has a frame anybody grades, where a silent
## fallback to the shipped value would hide a rig that failed to load.

## The rig moved: the sun, the sky and the globals are at a new `time_of_day`.
signal changed

## `--time-of-day=0.8` holds a rig with a cycle at that look for the whole run
## — a dev flag, read here so every scene that instances a rig can be shot at
## any hour, with or without a clock.
const TIME_ARG: String = "--time-of-day="

## The group the rig joins, so a reader of the hour with no wired path — the
## parked roster (`P3-73`) — can find the one rig in the tree.
const GROUP: StringName = &"lighting_rig"

## The `Environment` properties a cycle blends. Everything else — the switches,
## the tonemapper, the glow levels — is the day's and does not move.
const BLENDED: Array[StringName] = [
	&"ambient_light_color",
	&"ambient_light_energy",
	&"ambient_light_sky_contribution",
	&"glow_intensity",
	&"fog_light_color",
	&"fog_light_energy",
	&"fog_sun_scatter",
	&"fog_density",
	&"adjustment_saturation",
]
## And of the environment's `ProceduralSkyMaterial`.
const BLENDED_SKY: Array[StringName] = [
	&"sky_top_color",
	&"sky_horizon_color",
	&"ground_bottom_color",
	&"ground_horizon_color",
]

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

## The day this rig runs through, or null for a rig that stays as authored.
@export var cycle: RigCycle

## Where on `cycle` the rig stands, 0 the authored day and 1 the last keyframe.
## Written by `DayClock`, or pinned for a frame by `--time-of-day=`.
var time_of_day: float = 0.0:
	set = set_time_of_day

## Whether `--time-of-day=` holds the rig at one look for this run, which a
## clock must respect: a pinned frame that drifted is not a frame of that hour.
var pinned: bool = false

var _sun: DirectionalLight3D = null
var _world: WorldEnvironment = null
## The scene as authored, taken once: the cycle's first look, and the only
## statement of the daylight numbers.
var _day: RigKeyframe = null
var _day_basis := Basis.IDENTITY
## The environment the blend is written to — a copy, made the first time the
## rig moves, because the authored one is a shared and committed `.tres`.
var _live: Environment = null


func _ready() -> void:
	add_to_group(GROUP)
	RenderingServer.global_shader_parameter_set(&"exposure_anchor", exposure_anchor)
	# The process-wide globals outlive a scene, so a rig entering after a night
	# one must put the day back rather than inherit the dark.
	_set_globals(Color.WHITE, 0.0)
	if cycle == null or not cycle.usable():
		return
	for child: Node in get_children():
		if child is DirectionalLight3D:
			_sun = child
		elif child is WorldEnvironment:
			_world = child
	if _sun == null or _world == null or _world.environment == null:
		push_error("LightingRig: a cycle needs a sun and an environment to move; staying put.")
		return
	_day = RigKeyframe.new()
	_day.at = cycle.day_until
	_day.environment = _world.environment
	_day.sun_colour = _sun.light_color
	_day.sun_energy = _sun.light_energy
	_day.sky_light = Color.WHITE
	_day.night_lights = 0.0
	_day_basis = _sun.basis

	var pin: String = Cmdline.value(TIME_ARG)
	if pin.is_valid_float():
		pinned = true
		time_of_day = pin.to_float()


## Whether this rig has a day to run through: a usable cycle, and the sun and
## the environment to move.
func moves() -> bool:
	return _day != null


func set_time_of_day(value: float) -> void:
	time_of_day = clampf(value, 0.0, 1.0)
	if _day == null:
		return

	# The pair of looks `time_of_day` stands between. Before `day_until` both
	# are the day; past the last keyframe both are that keyframe, which is how
	# the night holds.
	var from: RigKeyframe = _day
	var to: RigKeyframe = _day
	for key: RigKeyframe in cycle.keyframes:
		to = key
		if time_of_day < key.at:
			break
		from = key
	var weight: float = 0.0
	if from != to:
		weight = clampf(inverse_lerp(from.at, to.at, time_of_day), 0.0, 1.0)

	if _live == null:
		if from == _day and weight == 0.0:
			return
		_live = _day.environment.duplicate(true)
		# Every move below dirties the sky, and the default re-filters its whole
		# radiance map in the frame it changed. Spread over frames instead: the
		# ambient trails the sky by a few of them, on a blend that takes minutes.
		_live.sky.process_mode = Sky.PROCESS_MODE_INCREMENTAL
		_world.environment = _live

	for property: StringName in BLENDED:
		_live.set(
			property, lerp(from.environment.get(property), to.environment.get(property), weight)
		)
	var sky: Material = _live.sky.sky_material
	var sky_from: Material = from.environment.sky.sky_material
	var sky_to: Material = to.environment.sky.sky_material
	for property: StringName in BLENDED_SKY:
		sky.set(property, lerp(sky_from.get(property), sky_to.get(property), weight))

	if from == _day and weight == 0.0:
		# The authored basis itself, not its quaternion: a scene file's nine
		# digits are not quite a rotation, and the round trip moves the sun.
		_sun.basis = _day_basis
	else:
		_sun.quaternion = _facing(from).slerp(_facing(to), weight)
	_sun.light_color = from.sun_colour.lerp(to.sun_colour, weight)
	_sun.light_energy = lerpf(from.sun_energy, to.sun_energy, weight)
	_set_globals(
		from.sky_light.lerp(to.sky_light, weight), lerpf(from.night_lights, to.night_lights, weight)
	)
	changed.emit()


## The key light's orientation at `key`. The day's is read off the scene's own
## basis, which is in no table.
func _facing(key: RigKeyframe) -> Quaternion:
	if key == _day:
		return _day_basis.get_rotation_quaternion()
	var radians: Vector3 = key.sun_rotation_deg * (PI / 180.0)
	return Quaternion.from_euler(radians)


func _set_globals(sky_light: Color, night_lights: float) -> void:
	# A multiplier, not a colour: sent as the raw triple so no transfer curve
	# is applied to it on the way.
	RenderingServer.global_shader_parameter_set(
		&"sky_light", Vector3(sky_light.r, sky_light.g, sky_light.b)
	)
	RenderingServer.global_shader_parameter_set(&"night_lights", night_lights)
