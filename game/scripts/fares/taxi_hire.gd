class_name TaxiHire
extends Node
## What the fare loop shows ON the car (`P3-48`): the roof sign and the
## passenger door.
##
## - **The sign** is lit while the car is for hire and dark while a passenger is
##   aboard — out at `boarded`, back at `delivered` or `bailed`. A hail does not
##   put it out: until the passenger is in the seat the fare can still be
##   `cancelled`, and the car is still for hire.
## - **The door** stands open from the hail to the boarding, and opens briefly
##   when a fare gets out — delivered or bailed.
## - **The hazards** (`Q187`) flash from the hail to the boarding or the cancel,
##   and for `alight_hazards_s` when a fare gets out.
## - **The face** (`P3-49`): the passenger grins out of the back seat each time
##   a skill pays, and rages out of it when the clock runs out and they walk
##   without paying — the door swinging open beside it.
## - **The sparks** (`P3-58`): the drift's tier off the rear wheels, empty car
##   or not — a practised slide shows as a paid one does.
## - **The meter's beep** (`Q178`): each time the reading moves — the flagfall at
##   the boarding, then every unit. In the cab with the player, so not a 3D voice.
## - **The flag** (`P3-79`): the meter's motor turns its flag down at the
##   boarding — the beep waits for it, as the reading does on a real meter — and
##   up again at the delivery or the bail.
## - **The payout** (`P3-79`): the card reader's double beep at the delivery,
##   then a coin for each `coin_hkd` of the tip.
##
## ⚠️ **Listens, and never polls.** Every change here is a `FareSystem` signal,
## so nothing runs per frame and the system stays pure enough for
## `verify_fares.gd` to drive without a car. `VehicleLamps`, `TaxiDoor` and
## `PassengerEmote` stay ignorant of fares for the same reason `VehicleLamps`
## never reads the player's input: an AI taxi on the same body (`B3`) has
## neither a fare loop nor a player, and its sign, door and face must not
## answer to the player's.
##
## A child of `Fares`, so `--fares=off` frees it with the loop and leaves both
## as the car was authored: sign lit, door shut — free roam is a taxi plying for
## hire.

const BEEP_PATH: String = "res://assets/authored/audio/meter_beep.wav"
const AUDIO: String = "res://assets/authored/audio/%s.wav"
## Plays per cabin sound at once, so a run of coins overlaps rather than cuts.
const CABIN_POLYPHONY: int = 4

## The loop to follow. Assign in the scene.
@export var fares: FareSystem
## The car whose sign and door this switches.
@export var vehicle: Node3D

## Beeps asked for, for the verify tool.
var beeps: int = 0
## The flag turned down and up, payouts and coins, for the same.
var flags_down: int = 0
var flags_up: int = 0
var payouts: int = 0
var coins: int = 0
## Hazards asked on for a boarding, and held for an alighting, for the same.
var hazards: bool = false
var hazard_holds: int = 0

var _beep: AudioStreamPlayer = null
var _audio: TaxiAudioProfile = null
var _cabin: Dictionary[String, AudioStreamPlayer] = {}
var _lamps: VehicleLamps = null
var _door: TaxiDoor = null
var _emote: PassengerEmote = null
var _sparks: DriftSparks = null
var _tail: LightTail = null


func _ready() -> void:
	if fares == null or vehicle == null:
		push_warning("TaxiHire has no FareSystem or no vehicle assigned; the sign stays lit.")
		return
	# Found by type under the car rather than named by path, as `VehicleLamps`
	# finds its body mesh: the scene owns where each rig hangs, and a car that
	# carries no door still gets its sign switched.
	for node: Node in vehicle.find_children("*", "", true, false):
		if node is VehicleLamps and _lamps == null:
			_lamps = node as VehicleLamps
		elif node is TaxiDoor and _door == null:
			_door = node as TaxiDoor
		elif node is PassengerEmote and _emote == null:
			_emote = node as PassengerEmote
		elif node is DriftSparks and _sparks == null:
			_sparks = node as DriftSparks
		elif node is LightTail and _tail == null:
			_tail = node as LightTail
	fares.hailed.connect(_on_hailed)
	fares.boarded.connect(_on_boarded)
	fares.cancelled.connect(_on_cancelled)
	fares.delivered.connect(_on_alighted)
	fares.bailed.connect(_on_alighted)
	fares.bailed.connect(_on_bailed)
	fares.skilled.connect(_on_skilled)
	var stream := load(BEEP_PATH) as AudioStream
	if stream == null:
		push_warning("TaxiHire: %s did not load; the meter is silent" % BEEP_PATH)
	else:
		_beep = AudioStreamPlayer.new()
		_beep.stream = stream
		_beep.bus = &"Cabin"
		add_child(_beep)
	fares.meter_changed.connect(_on_meter_changed)
	fares.delivered.connect(_on_delivered)
	_load_cabin()
	if _sparks != null:
		fares.drift_tier_changed.connect(_sparks.show_tier)
	if _tail != null:
		fares.drift_tier_changed.connect(_tail.show_tier)


## The cabin's voices (`P3-79`), off `taxi_audio.tres`; none, and silent, on a
## table that will not load.
func _load_cabin() -> void:
	_audio = load(TaxiAudioProfile.PATH) as TaxiAudioProfile
	if _audio == null or not _audio.usable("TaxiHire"):
		_audio = null
		return
	for file: String in ["flag_down", "flag_up", "octopus", "coin"]:
		var stream := load(AUDIO % file) as AudioStream
		if stream == null:
			push_warning("TaxiHire: %s did not load; it is silent" % (AUDIO % file))
			continue
		var voice := AudioStreamPlayer.new()
		voice.stream = stream
		voice.bus = &"Cabin"
		voice.volume_db = _audio.cabin_db
		voice.max_polyphony = CABIN_POLYPHONY
		add_child(voice)
		_cabin[file] = voice


func _on_meter_changed(_hkd: float, _delta_hkd: float) -> void:
	beeps += 1
	if _beep == null or not _beep.is_inside_tree():
		return
	# The flagfall's beep waits for the flag to land.
	var flag: AudioStreamPlayer = _cabin.get("flag_down")
	var wait_s: float = 0.0
	if flag != null and flag.playing:
		wait_s = flag.stream.get_length() - flag.get_playback_position()
	if wait_s > 0.0:
		get_tree().create_timer(wait_s, false, true).timeout.connect(_beep.play)
	else:
		_beep.play()


func _cabin_sound(file: String) -> void:
	var voice: AudioStreamPlayer = _cabin.get(file)
	if voice != null and voice.is_inside_tree():
		voice.play()


func _boarding_hazards(on: bool) -> void:
	hazards = on
	if _lamps != null:
		_lamps.hazards = on


func _on_hailed(_fare: Fare) -> void:
	_boarding_hazards(true)
	if _door != null:
		_door.open()


func _on_boarded(_fare: Fare) -> void:
	flags_down += 1
	_cabin_sound("flag_down")
	_boarding_hazards(false)
	if _lamps != null:
		_lamps.for_hire = false
	if _door != null:
		_door.close()


func _on_cancelled(_fare: Fare) -> void:
	_boarding_hazards(false)
	if _door != null:
		_door.close()


func _on_alighted(_fare: Fare) -> void:
	flags_up += 1
	_cabin_sound("flag_up")
	hazard_holds += 1
	if _lamps != null:
		_lamps.for_hire = true
		_lamps.hold_hazards()
	if _door != null:
		_door.open_briefly()


func _on_bailed(_fare: Fare) -> void:
	if _emote != null:
		_emote.show_face(PassengerEmote.Face.ANGRY)


## A skill grins; a penalty (`P3-50`) is the same signal with the sign
## flipped, and the face flips with it.
func _on_skilled(_fare: Fare, award: Fare.Award) -> void:
	if _emote != null:
		_emote.show_face(PassengerEmote.Face.HURT if award.hkd < 0.0 else PassengerEmote.Face.GRIN)


## The card reader, then the tip in coins.
func _on_delivered(fare: Fare) -> void:
	payouts += 1
	if _audio == null:
		return
	_cabin_sound("octopus")
	var count: int = clampi(roundi(fare.tip_hkd / _audio.coin_hkd), 0, _audio.coin_max)
	coins += count
	if not is_inside_tree():
		return
	for k: int in count:
		var due_s: float = _audio.coin_after_s + float(k) * _audio.coin_gap_s
		get_tree().create_timer(due_s, false, true).timeout.connect(_cabin_sound.bind("coin"))
