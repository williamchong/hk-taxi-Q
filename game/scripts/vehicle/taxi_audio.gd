class_name TaxiAudio
extends Node
## The taxi's own sounds off the car (`P3-79`): the engine, the tyres' squeal,
## the wind, a scrape along a wall, an impact by how hard and on what, a
## landing and the indicator's relay. What the fare
## sounds — the meter's flag and the payout — is `TaxiHire`'s.
##
## The player's car, not every car: a node beside `TaxiHorn` that reads the
## car's own state, never the router. Every voice hangs on the car, so the
## sound stands where the car does.
##
## ⚠️ **Reads, and never drains.** The impact comes off `step_hit_mps`, which
## the controller resets each step, not off `take_impact_mps`: that latch is the
## fare's penalty, and a second reader would steal its hits. The squeal reads
## `wheel_slips` from `SkidMarksProfile.mark_from_slip`, so it starts on the
## tick the marks do; the tiers are `SkillProfile`'s, so the crash you hear is
## the crash you are docked for.
##
## The loops play from the start and are only ever turned up and down, paused
## while silent: a loop started on demand would start on a click and a frame late.

const AUDIO: String = "res://assets/authored/audio/%s.wav"
## The one-shots at once: a crash lays the hit, its top layer, glass and debris.
const SHOT_VOICES: int = 6
## A loop turned down to this is silent.
const SILENT_DB: float = -80.0

## The car. Assign in the scene.
@export var vehicle: Node3D

## Sounds played, for the verify tool and the trace.
var impacts: int = 0
var lands: int = 0
var relays: int = 0
## The engine as the box runs it: the gear (0 is first) and the heard rpm.
var gear: int = 0
var rpm: float = 0.0
## The last impact's tier (`tap`, `bump`, `crash`) and top layer ("" a wall).
var last_tier: String = ""
var last_top: String = ""

var profile: TaxiAudioProfile = null
var _car: VehicleController = null
var _tyres: TyreVehicleController = null
var _lamps: VehicleLamps = null
var _bump_kph: float = 0.0
var _crash_kph: float = 0.0
var _mark_from_slip: float = 0.0
var _engine: Array[AudioStreamPlayer3D] = []
var _ev: AudioStreamPlayer3D = null
var _skid: AudioStreamPlayer3D = null
var _wind: AudioStreamPlayer3D = null
var _scrape: AudioStreamPlayer3D = null
## The engine loops' shares and pitches, refilled every tick.
var _mix: Array[Vector2] = []
## The off-throttle cut where it stands, easing toward the pedal's.
var _cut_db: float = 0.0
## Every looping voice, for the park's fade.
var _loops: Array[AudioStreamPlayer3D] = []
var _shots: Array[AudioStreamPlayer3D] = []
var _next_shot: int = 0
var _streams: Dictionary[String, AudioStream] = {}
var _cool_s: float = 0.0
## The speed of the hit the cooldown is for: a harder one inside it still sounds.
var _cool_mps: float = 0.0
var _air_s: float = 0.0
var _relay_lit: bool = false
var _variant: int = 0
## Its own draws, for the pitch jitter alone: nothing else reads it.
var _rng := RandomNumberGenerator.new()


func _ready() -> void:
	set_physics_process(false)
	_car = vehicle as VehicleController
	if _car == null:
		push_warning("TaxiAudio has no VehicleController assigned; the taxi is silent.")
		return
	profile = load(TaxiAudioProfile.PATH) as TaxiAudioProfile
	var skills := load(SkillProfile.PATH) as SkillProfile
	var marks := load(SkidMarksProfile.PATH) as SkidMarksProfile
	if profile == null or skills == null or marks == null or not profile.usable("TaxiAudio"):
		push_warning("TaxiAudio: a table did not load; the taxi is silent.")
		return
	_bump_kph = skills.bump_min_kph
	_crash_kph = skills.crash_min_kph
	_mark_from_slip = marks.mark_from_slip
	_tyres = vehicle as TyreVehicleController
	for node: Node in vehicle.find_children("*", "VehicleLamps", true, false):
		_lamps = node as VehicleLamps
		break
	for loop_rpm: float in profile.loop_rpms:
		_engine.append(_loop("engine_%d" % int(loop_rpm), &"Engine"))
	if profile.hybrid:
		_ev = _loop("engine_ev", &"Engine")
	_skid = _loop("skid", &"SFX")
	_wind = _loop("wind", &"SFX")
	_scrape = _loop("scrape", &"SFX")
	_loops.append_array(_engine)
	for voice: AudioStreamPlayer3D in [_ev, _skid, _wind, _scrape]:
		if voice != null:
			_loops.append(voice)
	for _i: int in SHOT_VOICES:
		var voice := AudioStreamPlayer3D.new()
		voice.bus = &"SFX"
		_shots.append(voice)
		vehicle.add_child.call_deferred(voice)
	# Loaded now, not on the tick of the first crash: a load on the physics tick
	# is a hitch at the worst moment, and on the web a cold one (`Q184`).
	for file: String in ["land", "indicator", "debris", "glass"]:
		_stream(file)
	for tier: String in ["tap", "bump", "crash"]:
		for variant: int in [1, 2]:
			_stream("hit_%s_%d" % [tier, variant])
	for what: String in profile.materials.values():
		_stream("top_" + what)
	rpm = profile.idle_rpm
	_rng.seed = 79
	set_physics_process(true)


func _stream(file: String) -> AudioStream:
	if not _streams.has(file):
		var stream := load(AUDIO % file) as AudioStream
		if stream == null:
			push_warning("TaxiAudio: %s did not load; it is silent" % (AUDIO % file))
		_streams[file] = stream
	return _streams[file]


## A loop on the car, playing at silence from the moment it is in the tree.
func _loop(file: String, bus: StringName) -> AudioStreamPlayer3D:
	var voice := AudioStreamPlayer3D.new()
	voice.stream = _stream(file)
	voice.bus = bus
	voice.volume_db = SILENT_DB
	voice.autoplay = voice.stream != null
	# Deferred: the scene is still adding its children, and the car is a sibling.
	vehicle.add_child.call_deferred(voice)
	return voice


func _physics_process(delta: float) -> void:
	# 🔴 **Silent while `parked`**, as `TaxiHorn` is (the user's call, 2026-11-06):
	# the menu's showroom is no place for an idling engine. Nothing new starts;
	# the loops fall away over `park_fade_s`, and a one-shot already playing ends.
	if _car.parked:
		_fade_loops(delta)
		return
	_step_engine(delta)
	_step_surface()
	_step_contacts(delta)
	_step_controls()


func _step_engine(delta: float) -> void:
	var speed: float = _car.speed_kph
	var throttle: float = _car.throttle_input
	var target: float = 0.0
	if profile.hybrid:
		target = profile.hybrid_rpm(speed, throttle)
	else:
		gear = 0 if _car.is_reversing() else profile.gear_after(gear, speed, throttle)
		target = profile.rpm_in(gear, speed, throttle)
	rpm = move_toward(rpm, target, profile.rpm_slew * delta)
	var cut: float = 0.0 if throttle > profile.pedal_up else profile.off_throttle_cut_db
	_cut_db = move_toward(_cut_db, cut, profile.off_throttle_ease_db_s * delta)
	profile.loop_mix_into(maxf(rpm, 1.0), _mix)
	for i: int in _engine.size():
		var share: float = _mix[i].x if rpm > 0.0 else 0.0
		_level_voice(_engine[i], profile.engine_db - _cut_db, share, _mix[i].y)
	if profile.hybrid:
		var ev: float = clampf(absf(speed) / profile.ev_ref_kph, 0.0, profile.ev_pitch_max)
		_level_voice(_ev, profile.ev_db, minf(ev, 1.0), maxf(ev, profile.ev_pitch_min))


func _step_surface() -> void:
	var slip: float = 0.0
	if _tyres != null:
		for wheel_slip: float in _tyres.wheel_slips():
			slip = maxf(slip, wheel_slip)
	var squeal: float = clampf(
		inverse_lerp(_mark_from_slip, profile.skid_full_slip, slip), 0.0, 1.0
	)
	# A slide at walking pace scuffs; at speed it howls, louder and higher.
	var pace: float = clampf(absf(_car.speed_kph) / profile.skid_full_kph, 0.0, 1.0)
	var heard: float = squeal * lerpf(profile.skid_slow_share, 1.0, pace)
	var pitch: float = (
		1.0 + profile.skid_pitch_rise * squeal + profile.skid_speed_pitch * (pace - 0.5)
	)
	_level_voice(_skid, profile.skid_db, heard, pitch)
	var air: float = clampf(
		inverse_lerp(profile.wind_from_kph, profile.wind_full_kph, absf(_car.speed_kph)), 0.0, 1.0
	)
	_level_voice(
		_wind, profile.wind_db, air, profile.wind_pitch_still + profile.wind_pitch_rise * air
	)


func _step_contacts(delta: float) -> void:
	_cool_s = maxf(_cool_s - delta, 0.0)
	var hit: float = _car.step_hit_mps
	# A tap's cooldown must not swallow the crash a tick behind it.
	if hit >= profile.tap_min_mps and (_cool_s <= 0.0 or hit > _cool_mps):
		_cool_s = profile.impact_cool_s
		_cool_mps = hit
		impact(hit, _car.step_hit_with)
	var grind: float = clampf(
		inverse_lerp(profile.scrape_from_mps, profile.scrape_full_mps, _car.step_scrape_mps),
		0.0,
		1.0
	)
	_level_voice(_scrape, profile.scrape_db, grind, 1.0)
	if _car.is_airborne():
		_air_s += delta
		return
	if _air_s >= profile.land_min_air_s:
		lands += 1
		_shot("land", profile.impact_db)
	_air_s = 0.0


func _step_controls() -> void:
	var lit: bool = _lamps != null and _lamps.indicator_lit
	if lit != _relay_lit:
		relays += 1
		# Tick on, tock off: the same relay, lower as it lets go.
		_shot("indicator", profile.cabin_db, 1.0 if lit else profile.relay_off_pitch)
	_relay_lit = lit


## An impact at `mps` into `body`: the hit by its tier, then what it was.
func impact(mps: float, body: Object) -> void:
	impacts += 1
	last_tier = tier_of(mps * 3.6, _bump_kph, _crash_kph)
	last_top = profile.material_of(body)
	_variant = _variant % 2 + 1
	_shot("hit_%s_%d" % [last_tier, _variant], profile.impact_db)
	if last_tier == "tap":
		return
	if last_top != "":
		_shot("top_" + last_top, profile.impact_db)
	if last_top == "railing":
		_shot("debris", profile.impact_db)
	if last_tier == "crash":
		_shot("glass", profile.impact_db)


## Which of the three an impact is, on the award's own bars.
static func tier_of(kph: float, bump_kph: float, crash_kph: float) -> String:
	if kph >= crash_kph:
		return "crash"
	if kph >= bump_kph:
		return "bump"
	return "tap"


func _shot(file: String, db: float, pitch: float = 1.0) -> void:
	if _shots.is_empty():
		return
	var voice: AudioStreamPlayer3D = _shots[_next_shot]
	_next_shot = (_next_shot + 1) % _shots.size()
	if not voice.is_inside_tree():
		return
	voice.stream = _stream(file)
	voice.volume_db = db
	var jitter: float = profile.shot_pitch_jitter
	voice.pitch_scale = pitch * (1.0 + _rng.randf_range(-jitter, jitter))
	voice.play()


## Parked: every loop falls toward `SILENT_DB` over `park_fade_s`, then pauses.
func _fade_loops(delta: float) -> void:
	var step_db: float = (
		INF if profile.park_fade_s <= 0.0 else -SILENT_DB * delta / profile.park_fade_s
	)
	for voice: AudioStreamPlayer3D in _loops:
		if voice.stream_paused:
			continue
		voice.volume_db = move_toward(voice.volume_db, SILENT_DB, step_db)
		voice.stream_paused = voice.volume_db <= SILENT_DB


## A loop's level and pitch: `share` of `db`, silent at none.
static func _level_voice(voice: AudioStreamPlayer3D, db: float, share: float, pitch: float) -> void:
	if voice == null:
		return
	# A silent loop still decodes and pans every tick: paused, it costs nothing,
	# and it resumes where it stopped, so nothing clicks. Each property is
	# written only when it moves: a write is a server call.
	if share <= 0.0:
		if not voice.stream_paused:
			voice.stream_paused = true
		return
	# Level and pitch before the unpause, so a resumed loop never plays a mix
	# block at the level it was silenced from.
	var db_now: float = db + linear_to_db(share)
	if voice.volume_db != db_now:
		voice.volume_db = db_now
	var pitch_now: float = maxf(pitch, 0.01)
	if voice.pitch_scale != pitch_now:
		voice.pitch_scale = pitch_now
	if voice.stream_paused:
		voice.stream_paused = false
