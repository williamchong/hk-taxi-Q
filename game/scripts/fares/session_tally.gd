class_name SessionTally
extends RefCounted
## A driver's ledger (`P3-76`, `Q169`): what a run did and what it banked, kept
## apart from the fare in flight. `FareSystem` writes one per run; the 成績表
## reads it, and `Settings` sums it into the lifetime record, which is the same
## shape.
##
## **An award is not money banked.** A walked fare forfeits its awards, the tip
## floors at zero, and practice pays nothing, so a skill's HK$ joins the books
## at the door and not at the award. `counts` holds every award, practised and
## forfeited too (`skill_counts`' rule); `banked` only what a delivery kept.
## What banks closes against `FareSystem.earned_hkd` (`total_hkd`), and
## `verify_fares`' `tally:` block holds that.
##
## **The bests outlive `SkillTracker.reset`,** which runs at every boarding: a
## slide held into a hail is still the longest slide. Practised alike. A slide
## or a flight counts once it has paid, and top speed on the ground only, so one
## physics glitch in the air cannot sit in a lifetime record for good.

## The two tables, in the order they are read. Every `Fare.Skill` is in one;
## `verify_fares` fails a value appended to the enum and left out.
const BONUSES: Array[Fare.Skill] = [
	Fare.Skill.DRIFT,
	Fare.Skill.SPEED,
	Fare.Skill.NEAR_MISS,
	Fare.Skill.CLOSE_CALL,
	Fare.Skill.AIR,
	Fare.Skill.EARLY,
]
const PENALTIES: Array[Fare.Skill] = [Fare.Skill.BUMP, Fare.Skill.CRASH]
## The fields that add up and the fields that are weighed, by name: the one list
## `add`, `take_unsaved` and `Settings`' record walk. `verify_menu` fails a name
## here that is no field.
const SUMS: PackedStringArray = [
	"meter_hkd", "time_hkd", "floored_hkd", "forfeited_hkd", "deliveries", "bails"
]
const BESTS: PackedStringArray = [
	"longest_slide_s", "longest_flight_s", "closest_pass_m", "top_speed_kph"
]

## Awards per `Fare.Skill`, paid or not.
var counts: PackedInt32Array = []
## HK$ per `Fare.Skill` on fares delivered; negative for a penalty.
var banked: PackedFloat64Array = []
var meter_hkd: float = 0.0
var time_hkd: float = 0.0
## What the tip's floor gave back: a debt larger than the tip is not charged.
var floored_hkd: float = 0.0
## The meter and the bonuses that walked with a passenger.
var forfeited_hkd: float = 0.0
var deliveries: int = 0
var bails: int = 0
var longest_slide_s: float = 0.0
var longest_flight_s: float = 0.0
## INF until a pass has paid.
var closest_pass_m: float = INF
var top_speed_kph: float = 0.0
## Game seconds driven this run, the pause and the menu not counted: free
## mode's REPORT shows it. Neither a sum nor a best — the lifetime record keeps
## no driving time — so it is in neither list and the record never reads it.
var driven_s: float = 0.0

## What the last `take_unsaved` handed over, so a run saved at every pause adds
## each event to the record once.
var _saved: SessionTally = null


func _init() -> void:
	counts.resize(Fare.Skill.size())
	counts.fill(0)
	banked.resize(Fare.Skill.size())
	banked.fill(0.0)


func note_award(award: Fare.Award) -> void:
	counts[award.skill] += 1


## One tick's bests. `flight_s` and `pass_m` read 0 and INF on a tick with none.
func note_tick(
	speed_kph: float, airborne: bool, slide_s: float, flight_s: float, pass_m: float
) -> void:
	if not airborne:
		top_speed_kph = maxf(top_speed_kph, speed_kph)
	longest_slide_s = maxf(longest_slide_s, slide_s)
	longest_flight_s = maxf(longest_flight_s, flight_s)
	closest_pass_m = minf(closest_pass_m, pass_m)


## A fare delivered: its meter, its time and every award on it into the books,
## with whatever the tip's floor gave back.
func note_delivered(fare: Fare) -> void:
	deliveries += 1
	meter_hkd += fare.meter.reading_hkd()
	time_hkd += fare.time_hkd
	floored_hkd += fare.tip_hkd - (fare.time_hkd + fare.skills_hkd)
	for award: Fare.Award in fare.awards:
		banked[award.skill] += award.hkd


## A fare walked: what `FareFace.forfeit` says was lost. Only the bonuses' net,
## since a debt walks with the passenger too.
func note_bailed(fare: Fare) -> void:
	bails += 1
	forfeited_hkd += fare.meter.reading_hkd() + maxf(fare.skills_hkd, 0.0)


func bonus_hkd() -> float:
	return _sum(BONUSES)


func penalty_hkd() -> float:
	return _sum(PENALTIES)


## The whole page's sum, which must equal `FareSystem.earned_hkd`.
func total_hkd() -> float:
	return meter_hkd + time_hkd + bonus_hkd() + penalty_hkd() + floored_hkd


## What has happened since the last call, as a tally to add to the record.
func take_unsaved() -> SessionTally:
	var delta := SessionTally.new()
	var last: SessionTally = _saved if _saved != null else SessionTally.new()
	for index: int in counts.size():
		delta.counts[index] = counts[index] - last.counts[index]
		delta.banked[index] = banked[index] - last.banked[index]
	for field: String in SUMS:
		delta.set(field, get(field) - last.get(field))
	# A best is not a sum: it travels only when it moved.
	if longest_slide_s > last.longest_slide_s:
		delta.longest_slide_s = longest_slide_s
	if longest_flight_s > last.longest_flight_s:
		delta.longest_flight_s = longest_flight_s
	if closest_pass_m < last.closest_pass_m:
		delta.closest_pass_m = closest_pass_m
	if top_speed_kph > last.top_speed_kph:
		delta.top_speed_kph = top_speed_kph
	_saved = SessionTally.new()
	_saved.add(self)
	return delta


## `other`'s sums added to this one's, and its bests weighed against this one's.
func add(other: SessionTally) -> void:
	for index: int in counts.size():
		counts[index] += other.counts[index]
		banked[index] += other.banked[index]
	for field: String in SUMS:
		set(field, get(field) + other.get(field))
	longest_slide_s = maxf(longest_slide_s, other.longest_slide_s)
	longest_flight_s = maxf(longest_flight_s, other.longest_flight_s)
	closest_pass_m = minf(closest_pass_m, other.closest_pass_m)
	top_speed_kph = maxf(top_speed_kph, other.top_speed_kph)


## Whether there is nothing here to write.
func is_empty() -> bool:
	return (
		counts == SessionTally.new().counts
		and deliveries == 0
		and bails == 0
		and is_zero_approx(longest_slide_s)
		and is_zero_approx(longest_flight_s)
		and is_inf(closest_pass_m)
		and is_zero_approx(top_speed_kph)
	)


## A filled sheet for a frame (`--menu-sample=on`): every row in use and the tip
## floored once, so the longest strings are on screen. Never a player's.
static func sample() -> SessionTally:
	var tally := SessionTally.new()
	var rows: Dictionary[Fare.Skill, Vector2] = {
		Fare.Skill.DRIFT: Vector2(14, 41.0),
		Fare.Skill.SPEED: Vector2(9, 45.0),
		Fare.Skill.NEAR_MISS: Vector2(6, 30.0),
		Fare.Skill.CLOSE_CALL: Vector2(2, 20.0),
		Fare.Skill.AIR: Vector2(3, 15.0),
		Fare.Skill.EARLY: Vector2(1, 10.0),
		Fare.Skill.BUMP: Vector2(5, -10.0),
		Fare.Skill.CRASH: Vector2(2, -10.0),
	}
	for skill: Fare.Skill in rows:
		tally.counts[skill] = int(rows[skill].x)
		tally.banked[skill] = rows[skill].y
	tally.meter_hkd = 412.6
	tally.time_hkd = 96.5
	tally.floored_hkd = 1.5
	tally.forfeited_hkd = 58.2
	tally.deliveries = 9
	tally.bails = 1
	tally.longest_slide_s = 3.25
	tally.longest_flight_s = 1.5
	tally.closest_pass_m = 0.18
	tally.top_speed_kph = 142.0
	tally.driven_s = 1834.0
	return tally


func _sum(skills: Array[Fare.Skill]) -> float:
	var sum: float = 0.0
	for skill: Fare.Skill in skills:
		sum += banked[skill]
	return sum
