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
## the sky, the ambient, the key light and two shader globals between the
## cycle's keyframes, the scene as authored one moment among them; `changed`
## tells the consumers that cached the sun (`SunGlint`, `VehicleLamps`) to
## read it again.
##
## 🔴 **The whole day moves since `Q222`** (the user's ask: the sun and the sky
## change slowly with the hour, brightest and overhead at noon). The scene as
## authored is ONE moment of the cycle — `RigCycle.day_at` — with keyframes
## before it as well as after, not a look held from the start. ⚠️ **A rig
## nobody moves is `resting`, and a resting rig writes nothing at all** — not
## the authored values written back, nothing — so every scene that never runs
## the clock renders the frame it rendered before there was one. `rest()` is
## the way back to that; `time_of_day` 0 is the morning now, not the day.
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
## The nodes that draw only at night — the lamps' pools of light — which the rig
## shows and hides as `night_lights` leaves and reaches 0: their shaders collapse
## every vertex by day, and a hidden node is not submitted at all. A node joins
## with `show_at_night`.
const NIGHT_GROUP: StringName = &"night_only"

## The `night_lights` global as last written: 0 by day. 1 until a rig says
## otherwise, so a scene with no rig feeds and shows every night layer — a
## verify tool counts the beams with none.
static var night_lights_now: float = 1.0

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

## How far the sun's shadows reach on a phone (`P2-6`), in place of the
## `Sun`'s own `directional_shadow_max_distance`; 0 keeps the node's. Why the
## number is what it is: the rig scene's sidecar.
@export_range(0.0, 1000.0, 5.0, "suffix:m") var phone_shadow_max_distance_m: float = 0.0

## The share of the window's resolution the 3D scene is drawn at on a phone
## (`P2-6`), the HUD staying at the window's own; 1 leaves the viewport alone.
## Why the number is what it is: the rig scene's sidecar.
@export_range(0.25, 1.0, 0.05) var phone_scale_3d: float = 1.0

## Where on `cycle` the rig stands: 0 the first keyframe, 1 the shift's end,
## and on to `cycle.span()` where the cycle comes round (`Q225`).
## Written by `DayClock`, or pinned for a frame by `--time-of-day=`. ⚠️ A
## `resting` rig reads 0 here and shows the authored day, which is at
## `cycle.day_at`: the hour's readers keep the opening hour they always read.
var time_of_day: float:
	get:
		return _time
	set(value):
		set_time_of_day(value)

## Whether the rig stands as the scene was authored, untouched: true until
## something moves it, and again after `rest()`.
var resting: bool:
	get:
		return _live == null

## Whether `--time-of-day=` holds the rig at one look for this run, which a
## clock must respect: a pinned frame that drifted is not a frame of that hour.
var pinned: bool = false

var _sun: DirectionalLight3D = null
var _world: WorldEnvironment = null
## The scene as authored, taken once: the cycle's look at `day_at`, and the
## only statement of the daylight numbers.
var _day: RigKeyframe = null
var _day_basis := Basis.IDENTITY
## The cycle's keyframes with `_day` stood among them at `day_at`, in order.
var _keys: Array[RigKeyframe] = []
var _time: float = 0.0
## The authored sky's radiance size, kept while the live copy is drawn.
var _day_radiance: Sky.RadianceSize = Sky.RADIANCE_SIZE_256
## The one environment both ends of the last blend shared, if they did: its
## values are already on the live copy and need no second write.
var _written: Environment = null
## The environment the blend is written to — a copy, made the first time the
## rig moves, because the authored one is a shared and committed `.tres`.
## ⚠️ One thing IS written to the authored one while this exists: its sky's
## `radiance_size`, shrunk because it is loaded and not drawn, and put back by
## `_drop_live` (`Q225`). No look reads it.
var _live: Environment = null


func _ready() -> void:
	add_to_group(GROUP)
	RenderingServer.global_shader_parameter_set(&"exposure_anchor", exposure_anchor)
	# The process-wide globals outlive a scene, so a rig entering after a night
	# one must put the day back rather than inherit the dark.
	_set_globals(Color.WHITE, 0.0)
	fit_handset(OS.has_feature, get_viewport())
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
	_day.at = cycle.day_at
	_day.environment = _world.environment
	_day.sun_colour = _sun.light_color
	_day.sun_energy = _sun.light_energy
	_day.sky_light = Color.WHITE
	_day.night_lights = 0.0
	_day_basis = _sun.basis
	_keys.clear()
	for key: RigKeyframe in cycle.keyframes:
		if key.at > _day.at and not _keys.has(_day):
			_keys.append(_day)
		_keys.append(key)
	if not _keys.has(_day):
		_keys.append(_day)

	var pin: String = Cmdline.value(TIME_ARG)
	if pin.is_valid_float():
		pinned = true
		time_of_day = pin.to_float()


## Whether this rig has a day to run through: a usable cycle, and the sun and
## the environment to move.
func moves() -> bool:
	return _day != null


## On a phone, pull the sun's shadow reach in to `phone_shadow_max_distance_m`
## (`P2-6`): the shadow map is the same size whatever it covers, so a shorter
## reach is sharper as well as fewer casters in each cascade. Anywhere else, or
## at 0, the sun stays as authored. `phone` is handed in so a check can ask
## about a phone from a desk.
func fit_shadow(phone: bool) -> void:
	if not phone or phone_shadow_max_distance_m <= 0.0:
		return
	for child: Node in get_children():
		var sun := child as DirectionalLight3D
		if sun != null:
			sun.directional_shadow_max_distance = phone_shadow_max_distance_m


## In a phone's app, draw the 3D scene at `phone_scale_3d` of the window
## (`P2-6`): fill rate is what a phone runs out of first, and the HUD is not
## scaled with it. Anywhere else, or at 1, the viewport stays as the project
## set it. `app` and `viewport` are handed in so a check can ask from a desk.
func fit_scale(app: bool, viewport: Viewport) -> void:
	if not app or phone_scale_3d >= 1.0 or viewport == null:
		return
	viewport.scaling_3d_scale = phone_scale_3d


## Both phone exceptions, each asked of its own test: the shadow reach of any
## phone, the 3D scale of the app alone (`Handset.is_app` has why).
## `has_feature` answers `OS.has_feature`'s question.
func fit_handset(has_feature: Callable, viewport: Viewport) -> void:
	fit_shadow(Handset.is_phone(has_feature))
	fit_scale(Handset.is_app(has_feature), viewport)


func set_time_of_day(value: float) -> void:
	_time = clampf(value, 0.0, cycle.span() if cycle != null else 1.0)
	if _day == null:
		return

	# The pair of looks `time_of_day` stands between. Off either end both are
	# the nearest one, which a cycle that does not come round holds.
	var from: RigKeyframe = _keys[0]
	var to: RigKeyframe = _keys[0]
	for key: RigKeyframe in _keys:
		to = key
		if _time < key.at:
			break
		from = key
	var weight: float = 0.0
	if from != to:
		weight = clampf(inverse_lerp(from.at, to.at, _time), 0.0, 1.0)
	elif cycle.loop_at > 0.0:
		# Off either end of a cycle that comes round: the leg from the last
		# look back to the first, across `loop_at`.
		from = _keys[-1]
		to = _keys[0]
		var leg: float = cycle.loop_at - from.at + to.at
		weight = clampf(fposmod(_time - from.at, cycle.loop_at) / leg, 0.0, 1.0)
	# The light's ANGLE moves on `weight`, at one speed from a keyframe to the
	# next; every colour and energy moves on `fade`, which leaves and arrives
	# at rest, so no look changes pace on the frame a keyframe passes (`Q222`,
	# the user's ask: "the light angle move linearly and color fades slowly").
	var fade: float = smoothstep(0.0, 1.0, weight)

	if _live == null:
		if from == _day and weight == 0.0:
			return
		_live = _day.environment.duplicate(true)
		# Every move below dirties the sky, and the default re-filters its whole
		# radiance map in the frame it changed. Spread over frames instead: the
		# ambient trails the sky by a few of them, on a blend that takes minutes.
		_live.sky.process_mode = Sky.PROCESS_MODE_INCREMENTAL
		_world.environment = _live
		# A loaded sky holds its radiance map whether or not it is drawn, and
		# the authored one is not drawn while the copy is: 18 MB (`Q225`).
		# Shrunk after the copy was taken, so the copy keeps the day's size.
		_day_radiance = _day.environment.sky.radiance_size
		_day.environment.sky.radiance_size = Sky.RADIANCE_SIZE_32

	# Between two keyframes on one environment — the afternoon's pair, and the
	# night's three, a third of every lap — the blend lands on the same values
	# whatever `fade` is: written once, since every write dirties the sky.
	var held: Environment = from.environment if from.environment == to.environment else null
	if held == null or held != _written:
		_blend_environment(from.environment, to.environment, fade)
	_written = held

	if from == _day and weight == 0.0:
		# The authored basis itself, not its quaternion: a scene file's nine
		# digits are not quite a rotation, and the round trip moves the sun.
		_sun.basis = _day_basis
	else:
		# The direction to the light along the great circle between the two,
		# not the orientations' quaternions: an arc at a constant angular
		# speed, whatever the two keyframes' yaw and pitch are.
		var toward: Vector3 = _toward(from).slerp(_toward(to), weight)
		_sun.basis = Basis.looking_at(-toward, Vector3.UP)
	_sun.light_color = from.sun_colour.lerp(to.sun_colour, fade)
	_sun.light_energy = lerpf(from.sun_energy, to.sun_energy, fade)
	_set_globals(
		from.sky_light.lerp(to.sky_light, fade), lerpf(from.night_lights, to.night_lights, fade)
	)
	changed.emit()


## Back to the scene as authored, at `time_of_day` 0: what a run that holds
## the daylight shows (`DayClock`). The authored `Environment` object and the
## authored basis themselves, not a blend that lands on their values.
func rest() -> void:
	_time = 0.0
	if _live == null:
		return
	_drop_live()
	_sun.basis = _day_basis
	_sun.light_color = _day.sun_colour
	_sun.light_energy = _day.sun_energy
	_set_globals(_day.sky_light, _day.night_lights)
	changed.emit()


## The unit vector toward the key light at `key`: a light shines down its own
## -Z. The day's is read off the scene's own basis, which is in no table.
## ⚠️ Never straight up: `looking_at` has no roll to give a vertical light.
func _toward(key: RigKeyframe) -> Vector3:
	if key == _day:
		return _day_basis.z.normalized()
	var radians: Vector3 = key.sun_rotation_deg * (PI / 180.0)
	return Basis.from_euler(radians).z


func _set_globals(sky_light: Color, night_lights: float) -> void:
	# A multiplier, not a colour: sent as the raw triple so no transfer curve
	# is applied to it on the way.
	RenderingServer.global_shader_parameter_set(
		&"sky_light", Vector3(sky_light.r, sky_light.g, sky_light.b)
	)
	RenderingServer.global_shader_parameter_set(&"night_lights", night_lights)
	var was_lit: bool = night_lights_now > 0.0
	night_lights_now = night_lights
	if was_lit != (night_lights > 0.0) and is_inside_tree():
		get_tree().call_group(NIGHT_GROUP, &"set_visible", night_lights > 0.0)


## A rig that leaves at night would leave every later scene reading day: back
## to what a scene with no rig reads.
func _exit_tree() -> void:
	night_lights_now = 1.0
	# The authored environment is a cached resource the next scene's rig will
	# load: it must not inherit a sky shrunk for this one.
	_drop_live()


## Let the live copy go: the authored environment back on screen, with the
## radiance size its sky was shrunk from while the copy was drawn.
func _drop_live() -> void:
	if _live == null:
		return
	_live = null
	_written = null
	_world.environment = _day.environment
	_day.environment.sky.radiance_size = _day_radiance


## Write the look `fade` of the way from one environment to another onto the
## live copy: what `BLENDED` and `BLENDED_SKY` name, and nothing else.
func _blend_environment(from: Environment, to: Environment, fade: float) -> void:
	for property: StringName in BLENDED:
		_live.set(property, lerp(from.get(property), to.get(property), fade))
	var sky: Material = _live.sky.sky_material
	var sky_from: Material = from.sky.sky_material
	var sky_to: Material = to.sky.sky_material
	for property: StringName in BLENDED_SKY:
		sky.set(property, lerp(sky_from.get(property), sky_to.get(property), fade))


## Draw `node` only while the night's lights are on, from now.
static func show_at_night(node: Node3D) -> void:
	node.add_to_group(NIGHT_GROUP)
	node.visible = night_lights_now > 0.0
