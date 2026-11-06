class_name TrafficHorns
extends RefCounted
## The traffic's horns (`Q178`, `P3-79`): when a car the taxi holds honks, the
## pattern each honk presses, and the voices that sound them. Owned by
## `TrafficSystem`, which it reads back for the table, the clock and the taxi.
##
## 🔴 **A pattern draws on `_rng`, never the traffic's**: one more roll there
## would move every later car. It is seeded off the traffic's seed in `seed_from`.

## A kind's horn, a loop held for as long as a press lasts (`P3-79`).
const HORN_PATH: String = "res://assets/authored/audio/horn_%s.wav"
## The horn a kind with no file of its own sounds.
const HORN_FALLBACK_KIND: String = "car_a"
## Why a car honks, each with its own pattern ranges in `traffic.tres`.
const HORN_REASONS: PackedStringArray = ["stood", "cut", "hit", "close_call"]
## A press starts and stops over this long, so the loop never clicks.
const HORN_DECLICK_S: float = 0.03
## Spreads the fleet's ids over the horn's pitch range: not a roll, since one more
## draw on the seeded RNG would move every later car.
const PITCH_STIR: float = 2.4


## One honk on one voice (`P3-79`): the car, its pattern, where in it the
## voice is, and the level the press has ramped to.
class HornCall:
	extends RefCounted
	var car: TrafficSystem.Car
	## Press, gap, press, … in seconds; `at` indexes it, even is a press.
	var pattern: PackedFloat32Array
	var at: int = 0
	## Seconds left of the step `at` names.
	var left_s: float = 0.0
	var level: float = 0.0

	## Seconds until the pattern is done.
	func remaining_s() -> float:
		var left: float = maxf(left_s, 0.0)
		for later: int in range(at + 1, pattern.size()):
			left += pattern[later]
		return left


## Horns sounded, a pattern each, and the presses in them, for the verify tool.
var horns: int = 0
var presses: int = 0
## The last pattern drawn: press, gap, press, … in seconds.
var last_pattern: PackedFloat32Array = PackedFloat32Array()

var _system: TrafficSystem
var _voices: Array[AudioStreamPlayer3D] = []
## What each voice is sounding, or null.
var _calls: Array[HornCall] = []
var _streams: Dictionary[String, AudioStream] = {}
var _rng := RandomNumberGenerator.new()


func _init(system: TrafficSystem) -> void:
	_system = system


## The patterns' own stream, off the traffic's seed.
func seed_from(seed: int) -> void:
	_rng.seed = seed * 104729 + 3


## The voices, under the system, and every kind's horn now, not on the tick of
## its first honk — a route-only kind (the bus) included, which `profile.kinds`
## never draws.
func load_voices(kinds: Array[String]) -> void:
	var profile: TrafficProfile = _system.profile
	for _voice: int in profile.horn_voices:
		var voice := AudioStreamPlayer3D.new()
		voice.max_distance = profile.horn_range_m
		voice.bus = &"SFX"
		_system.add_child(voice)
		_voices.append(voice)
		_calls.append(null)
	for kind: String in kinds:
		_streams[kind] = horn_stream(kind)


## Whether no voice is sounding.
func idle() -> bool:
	return _calls.all(func(honk: HornCall) -> bool: return honk == null)


## `kind`'s horn, or the fallback's where it has none; null, warned, where
## neither loads.
static func horn_stream(kind: String) -> AudioStream:
	var path: String = HORN_PATH % kind
	if not ResourceLoader.exists(path):
		path = HORN_PATH % HORN_FALLBACK_KIND
	var stream := load(path) as AudioStream
	if stream == null:
		push_warning("TrafficSystem: %s did not load; that horn is silent" % path)
	return stream


## Whether a car the taxi holds sounds its horn (`Q178`): at once when the taxi has
## left it `cut_mps` over the speed it could still stop from, or once it has stood
## `after_s`. `stood_s` is held at zero while the car moves or a light holds it.
static func wants_horn(
	speed: float, stop_from: float, stood_s: float, cut_mps: float, after_s: float
) -> bool:
	return horn_reason(speed, stop_from, stood_s, cut_mps, after_s) != ""


## Which of `wants_horn`'s two bars the car is over (`P3-79`): "cut", "stood", or
## "" for neither. Cut wins: a car cut up after a wait is cut up.
static func horn_reason(
	speed: float, stop_from: float, stood_s: float, cut_mps: float, after_s: float
) -> String:
	if speed - stop_from >= cut_mps:
		return "cut"
	if stood_s >= after_s:
		return "stood"
	return ""


## A car's tick: count down its wait, time its stand behind the taxi, and honk
## once it is cut up or has stood long enough.
func mind(car: TrafficSystem.Car, target: float, for_light: bool, delta: float) -> void:
	car.horn_wait = maxf(car.horn_wait - delta, 0.0)
	if car.held != TrafficSystem.Held.TAXI:
		car.taxi_stood_s = 0.0
		return
	car.taxi_stood_s = (
		0.0 if for_light or car.speed >= TrafficSystem.STOPPED_MPS else car.taxi_stood_s + delta
	)
	if car.horn_wait > 0.0:
		return
	var profile: TrafficProfile = _system.profile
	var reason: String = horn_reason(
		car.speed, target, car.taxi_stood_s, profile.horn_cut_mps, profile.horn_after_s
	)
	if reason != "":
		sound(car, reason)


## `car` honks for `reason`: a pattern drawn by its temper, on its own voice.
func sound(car: TrafficSystem.Car, reason: String) -> void:
	var profile: TrafficProfile = _system.profile
	car.horn_wait = profile.horn_repeat_s
	# The taxi in the menu's showroom stands on a road, and nobody is driving it.
	var controller := _system.vehicle as VehicleController
	if controller != null and controller.parked:
		return
	var clock_s: float = _system.clock_s()
	var temper: float = maxf(car.temper - (clock_s - car.temper_at_s) / profile.horn_temper_s, 0.0)
	var pattern: PackedFloat32Array = horn_pattern(profile, reason, temper, _rng)
	car.temper = minf(temper + profile.horn_temper_step, profile.horn_temper_max)
	car.temper_at_s = clock_s
	horns += 1
	presses += ceili(pattern.size() / 2.0)
	last_pattern = pattern
	var slot: int = _slot(car)
	if slot < 0:
		return
	var kind: String = _system.rules_kind(car)
	if not _streams.has(kind):
		_streams[kind] = horn_stream(kind)
	var voice: AudioStreamPlayer3D = _voices[slot]
	voice.stream = _streams[kind]
	voice.pitch_scale = 1.0 + profile.horn_pitch_spread * sin(float(car.id) * PITCH_STIR)
	var honk := HornCall.new()
	honk.car = car
	honk.pattern = pattern
	honk.left_s = pattern[0]
	_calls[slot] = honk
	if voice.is_inside_tree():
		voice.global_position = car.pose.origin
		voice.volume_db = linear_to_db(0.0)
		voice.play()


## A pattern for `reason` (`P3-79`): press, gap, press, … in seconds, the count
## and each press drawn toward the top of their ranges by `temper`, the gaps
## not. Static, so the verify tool can draw from it without a city.
static func horn_pattern(
	table: TrafficProfile, reason: String, temper: float, rng: RandomNumberGenerator
) -> PackedFloat32Array:
	var count: Vector2i = table.horn_count[reason]
	var press: Vector2 = table.horn_press_s[reason]
	var gap: Vector2 = table.horn_gap_s[reason]
	var presses_drawn: int = mini(
		count.x + int(lerpf(rng.randf(), 1.0, temper) * float(count.y - count.x + 1)), count.y
	)
	var out := PackedFloat32Array()
	for i: int in presses_drawn:
		if i > 0:
			out.append(lerpf(gap.x, gap.y, rng.randf()))
		out.append(lerpf(press.x, press.y, lerpf(rng.randf(), 1.0, temper)))
	return out


## The voice `car` sounds on: its own if it is mid-pattern (the new one replaces
## it), else an idle one, else the one nearest done. -1 with no voices.
func _slot(car: TrafficSystem.Car) -> int:
	var best: int = -1
	var best_left: float = INF
	for slot: int in _calls.size():
		var honk: HornCall = _calls[slot]
		if honk == null:
			if best_left > 0.0:
				best = slot
				best_left = 0.0
			continue
		if honk.car == car:
			return slot
		if honk.remaining_s() < best_left:
			best = slot
			best_left = honk.remaining_s()
	return best


## Each sounding voice: follow its car, press and lift on the pattern, and ramp
## the level over `HORN_DECLICK_S` either way.
func step(delta: float) -> void:
	for slot: int in _calls.size():
		var honk: HornCall = _calls[slot]
		if honk == null:
			continue
		var voice: AudioStreamPlayer3D = _voices[slot]
		honk.left_s -= delta
		while honk.left_s <= 0.0 and honk.at < honk.pattern.size():
			honk.at += 1
			if honk.at < honk.pattern.size():
				honk.left_s += honk.pattern[honk.at]
		var on: bool = honk.at < honk.pattern.size() and honk.at % 2 == 0
		honk.level = move_toward(honk.level, 1.0 if on else 0.0, delta / HORN_DECLICK_S)
		if honk.at >= honk.pattern.size() and honk.level <= 0.0:
			voice.stop()
			_calls[slot] = null
			continue
		if voice.is_inside_tree():
			if honk.car.live:
				voice.global_position = honk.car.pose.origin
			voice.volume_db = linear_to_db(honk.level)
