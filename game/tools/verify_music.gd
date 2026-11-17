## The driving music (`P3-97`, `Q246`): the table, the files and the node that
## mixes them, held to what an ear cannot check in a frame.
##
## - Every file the table names loads as a forward loop, and the beds are one
##   length that every layer's divides: the files play locked together, and a
##   layer that did not divide the bed would drift against it.
## - ×1 is the bed alone, and every count after it adds a layer or lifts one,
##   never drops one: a combo that climbs is never heard to fall.
## - Round the whole cycle the beds' shares hold the level (their squares sum
##   to 1), no more than two play at once, each bed is alone once its fade is
##   over, and the cycle's seam is not a step.
## - A held hour plays `held_mood` alone.
## - The layers that play chords follow the beds from one side's file to the
##   other's at the same level.
## - The node: silent while parked and faded in as the car drives off, the layers
##   at their row once the combo has stood at a count, and gone after it ends.
##
## - Off the shipped rig: at each bed's hour the node plays that bed alone
##   with the chord layers on its side, and `held_mood` once the rig rests.
##
## No built region needed: the table and the files are committed.
extends "res://tools/verify_tool.gd"

const ProfileScript = preload("res://scripts/audio/music_profile.gd")
const MusicScript = preload("res://scripts/audio/drive_music.gd")
const SettingsScript = preload("res://scripts/core/settings.gd")
const RIG_SCENE := "res://scenes/world/clean_daylight.tscn"
const TICK_S: float = 1.0 / 60.0
## Steps round the cycle the beds' shares are read at.
const SWEEP: int = 2000


func _init() -> void:
	_run.call_deferred()
	_start_watchdog.call_deferred("verify_music", 30.0)


func _run() -> void:
	var profile := load(ProfileScript.PATH) as MusicProfile
	if profile == null or not profile.usable("verify_music"):
		_problem("%s did not load whole" % ProfileScript.PATH)
		_finish("verify_music")
		return
	_check_files(profile)
	_check_tiers(profile)
	_check_hours(profile)
	await _check_node(profile)
	await _check_rig(profile)
	_finish("verify_music")


func _check_files(profile: MusicProfile) -> void:
	var files: PackedStringArray = profile.files()
	var bed_rows: int = 0
	var looped: int = 0
	var divide: int = 0
	for index: int in files.size():
		var stream := load(ProfileScript.FILE % files[index]) as AudioStreamWAV
		if stream == null or stream.loop_mode != AudioStreamWAV.LOOP_FORWARD:
			_fail("files", "bgm_%s is not a forward loop" % files[index])
			continue
		looped += 1
		var rows: int = roundi(stream.get_length() * stream.mix_rate)
		if index == 0:
			bed_rows = rows
		var whole: bool = rows == bed_rows if index < profile.moods.size() else bed_rows % rows == 0
		if whole:
			divide += 1
		else:
			_fail(
				"files", "bgm_%s is %d rows against the bed's %d" % [files[index], rows, bed_rows]
			)
	_expect(
		looped == files.size() and divide == files.size(),
		"files",
		"%d files loop, each a whole share of the bed's %d rows" % [files.size(), bed_rows]
	)
	_expect(
		files.size() <= AudioStreamSynchronized.MAX_STREAMS,
		"files",
		"one mix holds them all (%d of %d)" % [files.size(), AudioStreamSynchronized.MAX_STREAMS]
	)
	_expect(
		AudioServer.get_bus_index(SettingsScript.MUSIC_BUS) >= 0,
		"files",
		"the bus layout has the %s bus" % SettingsScript.MUSIC_BUS
	)


func _check_tiers(profile: MusicProfile) -> void:
	var alone: bool = true
	var climbs: bool = true
	for stem: int in profile.stems.size():
		alone = alone and profile.stem_level(1, stem) == 0.0
	for tier: int in range(2, profile.tier_count() + 1):
		var lifted: bool = false
		for stem: int in profile.stems.size():
			var was: float = profile.stem_level(tier - 1, stem)
			var now: float = profile.stem_level(tier, stem)
			climbs = climbs and now >= was
			lifted = lifted or now > was
		climbs = climbs and lifted
	_expect(alone, "combo", "x1 is the bed alone")
	_expect(climbs, "combo", "every count to x%d adds a layer or lifts one" % profile.tier_count())
	_expect(
		(
			profile.tier_of(0) == 1
			and profile.tier_of(3) == 3
			and profile.tier_of(profile.tier_count() + 40) == profile.tier_count()
		),
		"combo",
		"no combo plays x1, and a count past the table keeps its last row"
	)


func _check_hours(profile: MusicProfile) -> void:
	var cycle := load(RigCycle.PATH) as RigCycle
	if cycle == null or cycle.loop_at <= 0.0:
		_fail("hours", "%s has no cycle that comes round" % RigCycle.PATH)
		return
	var span: float = cycle.loop_at
	var weights: PackedFloat32Array = []
	var level_holds: bool = true
	var two_at_most: bool = true
	var smooth: bool = true
	var last: PackedFloat32Array = []
	profile.weights_at(span - span / SWEEP, span, last)
	for step: int in SWEEP:
		profile.weights_at(span * step / SWEEP, span, weights)
		var power: float = 0.0
		var playing: int = 0
		for index: int in weights.size():
			power += weights[index] * weights[index]
			playing += 1 if weights[index] > 0.0 else 0
			# A fade crosses `mood_fade` of the cycle: one step is this much of it.
			var most: float = (span / SWEEP) / profile.mood_fade * PI / 2.0 + 1e-4
			smooth = smooth and absf(weights[index] - last[index]) <= most
		level_holds = level_holds and is_equal_approx(power, 1.0)
		two_at_most = two_at_most and playing <= 2
		last = weights.duplicate()
	_expect(level_holds, "hours", "round the cycle the beds' squares sum to 1")
	_expect(two_at_most, "hours", "no more than two beds play at once")
	_expect(smooth, "hours", "no bed steps, the cycle's seam included")
	var alone: bool = true
	for index: int in profile.moods.size():
		var after: float = fposmod(profile.mood_from[index] + profile.mood_fade * 1.01, span)
		profile.weights_at(after, span, weights)
		alone = alone and is_equal_approx(weights[index], 1.0)
		var before: float = fposmod(profile.mood_from[index] - 1e-4, span)
		profile.weights_at(before, span, weights)
		alone = alone and weights[index] == 0.0
	_expect(alone, "hours", "each bed is silent before its start and alone after its fade")
	profile.held_weights(weights)
	var held: int = profile.moods.find(profile.held_mood)
	_expect(
		weights[held] == 1.0 and weights.count(0.0) == weights.size() - 1,
		"hours",
		"a held hour plays %s alone" % profile.held_mood
	)
	var sides_hold: bool = profile.sides().size() == 2
	for step: int in SWEEP:
		profile.weights_at(span * step / SWEEP, span, weights)
		var power: float = 0.0
		for side: String in profile.sides():
			power += profile.side_share(side, weights) ** 2
		sides_hold = sides_hold and is_equal_approx(power, 1.0)
	_expect(sides_hold, "hours", "the chord layers cross between two sides at one level")


func _check_node(profile: MusicProfile) -> void:
	var car := VehicleController.new()
	car.parked = true
	var music: DriveMusic = MusicScript.new()
	music.vehicle = car
	root.add_child(music)
	await process_frame
	music.set_process(false)
	var files: PackedStringArray = profile.files()
	var beds: int = profile.moods.size()
	var held: int = profile.moods.find(profile.held_mood)
	_run_for(music, 1.0)
	_expect(
		music.heard == 0.0 and music._player.stream_paused,
		"node",
		"parked, the music is silent and paused"
	)
	car.parked = false
	_run_for(music, profile.start_fade_s * 0.5)
	_expect(
		(
			music.heard > 0.0
			and music.heard < 1.0
			and music._player.volume_db < profile.bed_db - 9.0
			and not music._player.stream_paused
		),
		"node",
		(
			"half way through its fade in, it plays %.1f dB under its level"
			% (profile.bed_db - music._player.volume_db)
		)
	)
	_run_for(music, profile.start_fade_s * 0.5 + profile.mood_ease_s + 0.1)
	var bed_alone: bool = music.heard == 1.0 and not music._player.stream_paused
	for index: int in files.size():
		bed_alone = bed_alone and music.levels[index] == (1.0 if index == held else 0.0)
	_expect(bed_alone, "node", "driving with no combo, %s plays alone" % profile.held_mood)
	_expect(
		(
			is_equal_approx(music._player.volume_db, profile.bed_db)
			and music._player.bus == SettingsScript.MUSIC_BUS
		),
		"node",
		"at %.1f dB into the Music bus" % profile.bed_db
	)
	# A combo at each count: the layers stand at its row, the held bed's side's
	# file for a layer that plays chords and the other side's silent.
	var side: String = profile.mood_side[held]
	var rows_hold: bool = true
	for tier: int in range(1, profile.tier_count() + 1):
		music.combo_total = tier
		_run_for(music, maxf(profile.tier_rise_s, profile.tier_fall_s) * 1.5 + 0.1)
		var found: int = 0
		for stem: int in profile.stems.size():
			var level: float = profile.stem_level(tier, stem)
			for file: int in _layer_files(profile, stem, side):
				rows_hold = rows_hold and is_equal_approx(music.levels[file], level)
				found += 1
			for file: int in _layer_files(profile, stem, side, false):
				rows_hold = rows_hold and music.levels[file] == 0.0
				found += 1
		rows_hold = rows_hold and found == files.size() - beds
	_expect(
		rows_hold, "node", "each count to x%d stands its layers at its row" % profile.tier_count()
	)
	music._on_combo_ended(null, true)
	_run_for(music, profile.tier_fall_s * 1.5 + 0.1)
	var gone: bool = music.combo_total == 0
	for index: int in range(beds, files.size()):
		gone = gone and music.levels[index] == 0.0
	_expect(gone, "node", "the combo ended, every layer is gone")
	# Parked mid-combo: silent, and the count forgotten with the run's — its
	# layers too, or the next run would fade in on the last one's.
	music.combo_total = 4
	_run_for(music, profile.tier_rise_s * 1.5)
	var layers_up: bool = music.levels[beds] > 0.0
	car.parked = true
	_run_for(music, profile.park_fade_s + 0.1)
	_expect(
		music.heard == 0.0 and music._player.stream_paused and music.combo_total == 0,
		"node",
		"parked again, it falls silent and forgets the count"
	)
	car.parked = false
	_run_for(music, TICK_S)
	var layers_gone: bool = true
	for index: int in range(beds, files.size()):
		layers_gone = layers_gone and music.levels[index] == 0.0
	_expect(
		layers_up and layers_gone,
		"node",
		"the next run starts on the bed alone, the last one's layers not carried into it"
	)
	music.free()
	car.free()


## The node on the shipped rig: the hour is read off it, never a second clock.
func _check_rig(profile: MusicProfile) -> void:
	var packed := load(RIG_SCENE) as PackedScene
	var rig := packed.instantiate() as LightingRig if packed != null else null
	if rig == null or rig.cycle == null:
		_fail("rig", "%s did not load as a rig with a cycle" % RIG_SCENE)
		return
	root.add_child(rig)
	var music: DriveMusic = MusicScript.new()
	music.rig = rig
	root.add_child(music)
	await process_frame
	music.set_process(false)
	music.combo_total = profile.tier_count()
	var beds: int = profile.moods.size()
	var settle_s: float = (
		profile.start_fade_s + maxf(profile.mood_ease_s, profile.tier_rise_s) * 1.5 + 0.1
	)
	var follows: bool = true
	for mood: int in beds:
		var at: float = profile.mood_from[mood] + profile.mood_fade * 1.5
		rig.time_of_day = fposmod(at, rig.cycle.loop_at)
		_run_for(music, settle_s)
		for index: int in beds:
			follows = follows and music.levels[index] == (1.0 if index == mood else 0.0)
		var stem: int = profile.stems.find(profile.sided_stems[0])
		var level: float = profile.stem_level(profile.tier_count(), stem)
		for file: int in _layer_files(profile, stem, profile.mood_side[mood]):
			follows = follows and is_equal_approx(music.levels[file], level)
		for file: int in _layer_files(profile, stem, profile.mood_side[mood], false):
			follows = follows and music.levels[file] == 0.0
	_expect(
		follows, "rig", "at each bed's hour on the rig it plays alone, the chord layers on its side"
	)
	rig.rest()
	_run_for(music, settle_s)
	_expect(
		rig.resting and music.levels[profile.moods.find(profile.held_mood)] == 1.0,
		"rig",
		"the rig at rest, %s plays" % profile.held_mood
	)
	music.free()
	rig.free()


## Where layer `stem`'s files stand among `MusicProfile.files`, found by the
## NAME each carries and not by the order the node lays them in: the ones heard
## with the beds on `side` (its own side's, or the one both share), or with
## `heard` false the other side's.
func _layer_files(
	profile: MusicProfile, stem: int, side: String, heard: bool = true
) -> PackedInt32Array:
	var files: PackedStringArray = profile.files()
	var out: PackedInt32Array = []
	for name: String in profile.sides():
		var file: int = files.find(ProfileScript.SIDED_LAYER % [name, profile.stems[stem]])
		if file >= 0 and (name == side) == heard:
			out.append(file)
	var shared: int = files.find(ProfileScript.LAYER % profile.stems[stem])
	if shared >= 0 and heard:
		out.append(shared)
	return out


func _run_for(music: DriveMusic, seconds: float) -> void:
	for _tick: int in ceili(seconds / TICK_S):
		music.step(TICK_S)
