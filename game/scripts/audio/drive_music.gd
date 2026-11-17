class_name DriveMusic
extends Node
## The driving music (`P3-97`, `Q246`, the user's ask): a quiet bed under the
## drive that changes with the hour, and layers that come in as the style
## combo climbs.
##
## **Every file plays at once, locked together, and is only turned up and
## down.** The beds and the layers are the same eight bars at one tempo
## (`tools/make_bgm.py`), held in one `AudioStreamSynchronized` so they cannot
## drift: a bed fades into the next as the rig's hour passes its start, and a
## layer rises as the count reaches its row (`music.tres`). Nothing starts on
## a beat, so nothing has to wait for one.
##
## It reads and never drives: the hour off the rig the `DayClock` moves, the
## count off `FareSystem`'s combo signals (`fares.md`: a reader uses signals,
## never a poll — under `--fares=off` the system is gone and the music is the
## bed alone), and `parked` off the car, where it falls silent as the taxi's
## own loops do (`Q185`).
##
## ⚠️ The combo is still never money and still has no one-shot of its own
## (`fares.md`: built, heard, removed). The layers are the music, not an award.

## A level this low is silent.
const SILENT_DB: float = -80.0

## The car whose `parked` silences the music. Assign in the scene.
@export var vehicle: VehicleController
## The rig whose hour picks the bed; none plays `held_mood`.
@export var rig: LightingRig
## The fare loop whose style combo brings the layers in; none plays the bed.
@export var fares: FareSystem

var profile: MusicProfile = null
## The combo's total as last heard from `fares`; 0 with none running.
var combo_total: int = 0
## Every file's level as it stands, 0 to 1 and on, in `MusicProfile.files`'
## order; and how far the whole has faded in, 0 parked and 1 driving.
var levels: PackedFloat32Array = []
var heard: float = 0.0

var _player: AudioStreamPlayer = null
var _mix: AudioStreamSynchronized = null
var _weights: PackedFloat32Array = []
var _targets: PackedFloat32Array = []
## Each layer's file after the beds: its stem and its side (`MusicProfile.layers`).
var _layer_stem: PackedInt32Array = []
var _layer_side: PackedStringArray = []


func _ready() -> void:
	set_process(false)
	profile = load(MusicProfile.PATH) as MusicProfile
	if profile == null or not profile.usable("DriveMusic"):
		push_warning("DriveMusic: the table did not load; there is no music.")
		return
	var files: PackedStringArray = profile.files()
	if files.size() > AudioStreamSynchronized.MAX_STREAMS:
		push_warning("DriveMusic: %d files are more than one mix holds." % files.size())
		return
	_mix = AudioStreamSynchronized.new()
	_mix.stream_count = files.size()
	for index: int in files.size():
		var stream := load(MusicProfile.FILE % files[index]) as AudioStream
		if stream == null:
			push_warning("DriveMusic: bgm_%s did not load; it is silent." % files[index])
		_mix.set_sync_stream(index, stream)
		_mix.set_sync_stream_volume(index, SILENT_DB)
	levels.resize(files.size())
	levels.fill(0.0)
	_targets = levels.duplicate()
	profile.layers(_layer_stem, _layer_side)
	_player = AudioStreamPlayer.new()
	_player.stream = _mix
	_player.bus = Settings.MUSIC_BUS
	_player.volume_db = SILENT_DB
	_player.autoplay = true
	add_child(_player)
	if fares != null:
		fares.combo_changed.connect(_on_combo_changed)
		fares.combo_ended.connect(_on_combo_ended)
	set_process(true)


func _on_combo_changed(combo: StyleCombo) -> void:
	combo_total = combo.total()


func _on_combo_ended(_combo: StyleCombo, _broken: bool) -> void:
	combo_total = 0


func _process(delta: float) -> void:
	step(delta)


## One frame of `delta` seconds: where every level is going, and a step there.
## Its own function so `verify_music` runs the clock without waiting on one.
func step(delta: float) -> void:
	if vehicle != null and vehicle.parked:
		# A new run's combo starts empty with no signal to say so (`FareSystem.reset`).
		combo_total = 0
		heard = move_toward(heard, 0.0, delta / profile.park_fade_s)
	else:
		heard = move_toward(heard, 1.0, delta / profile.start_fade_s)
	_level_player()
	if heard <= 0.0:
		# Silent, so unheard: the last run's layers must not fade in with the next.
		_targets.fill(0.0)
		for index: int in range(profile.moods.size(), levels.size()):
			_set_level(index, 0.0)
		return
	_aim()
	var beds: int = profile.moods.size()
	for index: int in levels.size():
		var seconds: float = profile.mood_ease_s
		if index >= beds:
			seconds = (
				profile.tier_rise_s if _targets[index] > levels[index] else profile.tier_fall_s
			)
		_set_level(index, move_toward(levels[index], _targets[index], delta / seconds))


## Where every file's level is going: the hour's beds, the count's layers.
func _aim() -> void:
	if rig != null and rig.cycle != null and not rig.resting:
		profile.weights_at(rig.time_of_day, rig.cycle.loop_at, _weights)
	else:
		profile.held_weights(_weights)
	var beds: int = _weights.size()
	for bed: int in beds:
		_targets[bed] = _weights[bed]
	var tier: int = profile.tier_of(combo_total)
	for row: int in _layer_stem.size():
		var level: float = profile.stem_level(tier, _layer_stem[row])
		if not _layer_side[row].is_empty():
			level *= profile.side_share(_layer_side[row], _weights)
		_targets[beds + row] = level


## File `index` to `level`, told to the mix only where it moved: a write is a
## server call.
func _set_level(index: int, level: float) -> void:
	if levels[index] == level:
		return
	levels[index] = level
	_mix.set_sync_stream_volume(index, SILENT_DB if level <= 0.0 else linear_to_db(level))


## The whole music's level, paused while silent: it resumes where it stopped,
## every file still in step.
func _level_player() -> void:
	if heard <= 0.0:
		if not _player.stream_paused:
			_player.stream_paused = true
		return
	# The travel squared, as the sliders are: a fade straight on the amplitude
	# is over, to the ear, in its first fifth.
	var db: float = profile.bed_db + Settings.level_db(heard)
	if _player.volume_db != db:
		_player.volume_db = db
	if _player.stream_paused:
		_player.stream_paused = false
