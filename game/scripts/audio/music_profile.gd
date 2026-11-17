class_name MusicProfile
extends Resource
## The driving music (`P3-97`, `Q246`): which bed plays at which hour, and
## which of the combo's layers at which count. The rationale for each value is
## in `tuning/music.md`; what each *is* is here.
##
## 🔴 **No `@export` here declares a default**, on `TaxiAudioProfile`'s
## convention: a missing key reads as zero, and `usable()` refuses a zero
## rather than fall back to a literal. The exception is `bed_db`, which may
## be 0 dB.
##
## Pure but for the load, so `verify_music` drives the hour and the count
## without a scene.

## Path to the shipped table.
const PATH: String = "res://tuning/music.tres"
## A file of the music, by its name after `bgm_`.
const FILE: String = "res://assets/authored/audio/bgm_%s.wav"
## A layer's file: one for both sides, or one for each side's chords.
const LAYER: String = "fire_%s"
const SIDED_LAYER: String = "fire_%s_%s"

@export_group("Level")
## The music's level into its bus with every slider full.
@export_range(-40.0, 12.0, 0.5, "suffix:dB") var bed_db: float
## How long the music takes to fade in as the car first drives off, and
## again after every park (the user's ask: the game starts on a fade).
@export_range(0.05, 30.0, 0.05, "suffix:s") var start_fade_s: float
## How long it takes to fall silent once the car is parked.
@export_range(0.05, 10.0, 0.05, "suffix:s") var park_fade_s: float

@export_group("Hour")
## The beds, by the name their file carries (`bgm_<mood>.wav`).
@export var moods: PackedStringArray
## Where on the rig's cycle each bed begins (`RigCycle`'s scale: 0 is 07:00, 1
## is 21:00, `loop_at` the next 07:00), in `moods`' order. A bed plays from its
## own start to the next one's, round the cycle.
@export var mood_from: PackedFloat32Array
## Which chords each bed is in, in `moods`' order: the layers that play chords
## have a file for each side.
@export var mood_side: PackedStringArray
## How much of the cycle a bed takes to fade in over the one before it,
## starting at its `mood_from`.
@export_range(0.001, 0.5, 0.001) var mood_fade: float
## The bed of a run whose hour is held (free mode's ALWAYS DAY, a rig with no
## cycle).
@export var held_mood: String
## How long a bed takes from silent to full where the hour jumps: a run
## starting, the option changing. The hour's own fade is `mood_fade`.
@export_range(0.05, 30.0, 0.05, "suffix:s") var mood_ease_s: float

@export_group("Combo")
## The combo's layers, by the name their file carries.
@export var stems: PackedStringArray
## The layers among `stems` that play the chords: `bgm_fire_<side>_<stem>.wav`.
@export var sided_stems: PackedStringArray
## Each layer's level at each count: a row of `stems.size()` for ×1, then ×2,
## to the last row, which every count past it keeps.
@export var tiers: PackedFloat32Array
## How long a layer takes from silent to full as the combo climbs, and from
## full to silent when it ends.
@export_range(0.05, 30.0, 0.05, "suffix:s") var tier_rise_s: float
@export_range(0.05, 30.0, 0.05, "suffix:s") var tier_fall_s: float


## Whether every dial is there; the reason is pushed for `who`.
func usable(who: String) -> bool:
	var required: Dictionary[String, float] = {
		"start_fade_s": start_fade_s,
		"park_fade_s": park_fade_s,
		"moods": float(moods.size()),
		"mood_fade": mood_fade,
		"mood_ease_s": mood_ease_s,
		"stems": float(stems.size()),
		"tiers": float(tiers.size()),
		"tier_rise_s": tier_rise_s,
		"tier_fall_s": tier_fall_s,
	}
	if TuningTable.any_zero(self, required, who, "no music will play"):
		return false
	var whole: bool = (
		mood_from.size() == moods.size()
		and mood_side.size() == moods.size()
		and tiers.size() % stems.size() == 0
		and held_mood in moods
	)
	if not whole:
		push_error("%s: %s has a table that does not fit; no music will play." % [who, PATH])
	return whole


## The most the combo's count changes the music: the rows of `tiers`.
func tier_count() -> int:
	@warning_ignore("integer_division")
	return tiers.size() / stems.size()


## The row a combo totalling `total` plays: none running is ×1, the first row.
func tier_of(total: int) -> int:
	return clampi(total, 1, tier_count())


## Layer `stem`'s level with the combo at `tier`, 1 to `tier_count()`.
func stem_level(tier: int, stem: int) -> float:
	return tiers[(tier - 1) * stems.size() + stem]


## The two sides' names, in the order `mood_side` first names them.
func sides() -> PackedStringArray:
	var found: PackedStringArray = []
	for side: String in mood_side:
		if side not in found:
			found.append(side)
	return found


## The layers' files in the order they are held after the beds, a row each:
## which of `stems` it plays into `stem_of`, and into `side_of` the side
## whose chords it is in — "" for a layer both sides share. The one place
## that order is decided.
func layers(stem_of: PackedInt32Array, side_of: PackedStringArray) -> void:
	stem_of.clear()
	side_of.clear()
	var both: PackedStringArray = sides()
	for stem: int in stems.size():
		for side: String in both if stems[stem] in sided_stems else PackedStringArray([""]):
			stem_of.append(stem)
			side_of.append(side)


## Every file of the music in the order the player holds them: the beds, then
## `layers`' rows.
func files() -> PackedStringArray:
	var out: PackedStringArray = moods.duplicate()
	var stem_of: PackedInt32Array = []
	var side_of: PackedStringArray = []
	layers(stem_of, side_of)
	for row: int in stem_of.size():
		var stem: String = stems[stem_of[row]]
		out.append(LAYER % stem if side_of[row].is_empty() else SIDED_LAYER % [side_of[row], stem])
	return out


## Each bed's share at `time` on the rig's cycle, which comes round at `span`
## (0: it does not, and the last bed holds), written into `into` in `moods`'
## order. One bed at full, or two across a fade at equal power — the squares
## sum to 1, so the level holds through it.
##
## A bed's age is how long ago it started, round the cycle: the youngest
## plays, over the next youngest while its own fade runs.
func weights_at(time: float, span: float, into: PackedFloat32Array) -> void:
	into.resize(moods.size())
	into.fill(0.0)
	var now: int = -1
	var before: int = -1
	var now_age: float = INF
	var before_age: float = INF
	for index: int in moods.size():
		var age: float = time - mood_from[index]
		if span > 0.0:
			age = fposmod(age, span)
		elif age < 0.0:
			# No cycle to come round: a bed not yet started is not playing.
			continue
		if age < now_age:
			before = now
			before_age = now_age
			now = index
			now_age = age
		elif age < before_age:
			before = index
			before_age = age
	if now < 0:
		# No cycle, and before the first start: the last bed holds.
		for index: int in moods.size():
			if now < 0 or mood_from[index] > mood_from[now]:
				now = index
		into[now] = 1.0
		return
	var share: float = 1.0 if before < 0 else clampf(now_age / mood_fade, 0.0, 1.0)
	into[now] = sin(share * PI / 2.0)
	if share < 1.0:
		into[before] = cos(share * PI / 2.0)


## Each bed's share with the hour held: `held_mood` alone.
func held_weights(into: PackedFloat32Array) -> void:
	into.resize(moods.size())
	into.fill(0.0)
	into[maxi(moods.find(held_mood), 0)] = 1.0


## How much of side `side` is heard under `weights`: the beds in its chords, at
## equal power, so a layer crosses from one side's file to the other's with
## the beds.
func side_share(side: String, weights: PackedFloat32Array) -> float:
	var power: float = 0.0
	for index: int in moods.size():
		if mood_side[index] == side:
			power += weights[index] * weights[index]
	return sqrt(power)
