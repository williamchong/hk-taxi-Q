class_name FareFace
extends RefCounted
## What the fare HUD says (`P3-5a`), decided here and only painted by `hud.gd`.
##
## A model with no node in it, on `street_tracker.gd`'s pattern: `hud.gd` feeds
## it the loop's state on every `FareSystem.sampled` and reads back the strings,
## and `tools/verify_hud.gd` feeds it synthetic fares and reads the same strings
## — so "the callout names the pickup while idle and the destination while
## carrying" is a check, not a screenshot.
##
## **No goal until there is a customer aboard** (the user's calls, `Q142`,
## 2026-09-24): idle, the callout and the clock are down, and the guide's
## arrow and the map's pin point at the CLOSEST pending customer — the nearest
## pickup in the pool — with no ring on the road. Hailed, everything points at
## the destination.
##
## **A stop is said the way a passenger says it** (the user's call, `Q142`):
## a caption saying what the box is, the building — `Fare.Stop.place()`,
## iB1000's name for the footprint the point stands at — and the road under it
## with the road distance left. **In one language** (`Locale`), never both on
## a row: DESTINATION / "Times Square" / "RUSSELL STREET  1.2 km".
##
## **Money shows as HK$ to one place**, the way the 咪錶 shows it, and the meter
## shows the last banked sum between fares — a meter left reading the last trip
## is what a real cab shows at a stand. No multiplier: the tip under the meter
## while the fare runs is the skills paid so far, in HK$, and the seconds left
## are the timer's until the door prices them (`Q145`).
##
## **The receipt says why there was a tip** (`P3-49`, the user's ask): at a
## delivery the callout holds what banked over a line adding it up — the
## meter, the time left, each skill by name with its count. A skill that pays
## mid-drive flashes under the clock as `award_text`. A bail is said as what
## it is — the passenger ran off without paying — over what walked out with
## them.

## What the callout holds after a fare ends, for `hold_samples` samples.
enum Notice { NONE, DELIVERED, BAILED }

## The callout: a caption saying what the box is, the place, and the road with
## the road distance left under it. An empty `callout` means nothing to say
## and the panel hides — which, idle, it does (the user's call: no goal shown
## until there is a customer).
var caption: String = ""
var callout: String = ""
var callout_sub: String = ""
## The meter's digits, `money`-formatted — 0.0 between fares, everything but
## the total resetting at delivery (the user's call) — and the session's
## takings under them.
var meter_text: String = "0.0"
## The tip as it stands, under the meter while carrying — the skills paid so
## far, `money`-formatted for a second LED in the meter's red (the user's
## call: same display, same colour as the fare), rising with each skill and
## docked by a penalty, never falling with the clock; "" otherwise.
var tip_text: String = ""
## The chip beside the tip's digits, the way "HK$" stands beside the meter's.
var tip_caption: String = ""
var total_text: String = ""
## The tip clock: whole seconds left, shown only while carrying.
var timer_text: String = ""
var show_timer: bool = false
## Under the style's `timer_warn_s`: the clock turns the fare's red.
var timer_urgent: bool = false
## Where the guide and the map's pin point: the closest pending customer
## while idle, the destination once hailed.
var has_target: bool = false
var target: Vector3 = Vector3.ZERO
## The target is the destination (true) or the closest pending customer
## (false). While it is not the destination, every pending customer is
## marked, on the map and on the road.
var target_is_destination: bool = false

var _language: String = Locale.DEFAULT
var _hold_samples: int = 0
var _notice: Notice = Notice.NONE
var _notice_left: int = 0
## The notice's three lines, decided once at `on_ended`: the fare is over and
## nothing on it changes, so the receipt is not re-summed at 5 Hz.
var _notice_caption: String = ""
var _notice_callout: String = ""
var _notice_sub: String = ""


func _init(hold_samples: int, language: String) -> void:
	_hold_samples = maxi(hold_samples, 0)
	_language = language


## `delivered` or bailed: the callout holds the outcome for a few samples.
func on_ended(fare: Fare, delivered: bool) -> void:
	_notice = Notice.DELIVERED if delivered else Notice.BAILED
	_notice_left = _hold_samples
	if delivered:
		# The early arrival is named in the caption (the user's ask): it pays in
		# the same call as the delivery, so its flash under the clock is
		# overwritten by the banked sum before a frame shows it.
		var early: String = ""
		for award: Fare.Award in fare.awards:
			if award.skill == Fare.Skill.EARLY:
				early = " · " + award_text(award)
				break
		_notice_caption = (
			_say("已送達", "DELIVERED") + early + _say(" · 小費 HK$", " · TIP HK$") + money(fare.tip_hkd)
		)
		_notice_callout = "HK$" + money(fare.banked_hkd)
		_notice_sub = receipt(fare)
	else:
		_notice_caption = _say("乘客走數", "RAN OFF WITHOUT PAYING")
		_notice_callout = "HK$0.0"
		_notice_sub = forfeit(fare)


## One sample of the loop: its `state` and `fare`, the closest pending
## customer (null with none), the bar under which the clock is urgent, and
## what the session has banked.
func on_sampled(
	state: FareSystem.State, fare: Fare, nearest: Fare.Stop, warn_s: float, earned_hkd: float
) -> void:
	total_text = _say("合計 HK$", "TOTAL HK$") + money(earned_hkd)
	show_timer = state == FareSystem.State.CARRYING
	timer_urgent = false
	timer_text = ""
	meter_text = "0.0"
	tip_text = ""
	tip_caption = ""
	if state == FareSystem.State.CARRYING:
		timer_text = seconds(fare.remaining_s)
		timer_urgent = fare.remaining_s <= warn_s
		meter_text = money(fare.meter.reading_hkd())
		tip_text = money(fare.tip_hkd)
		tip_caption = _say("小費", "TIP")
	elif state == FareSystem.State.BOARDING:
		meter_text = money(fare.meter.reading_hkd())

	if state != FareSystem.State.IDLE:
		_notice = Notice.NONE
		has_target = true
		target = fare.destination.point
		target_is_destination = true
		if state == FareSystem.State.BOARDING:
			caption = _say("上客中", "PICKING UP")
		else:
			caption = _say("目的地", "DESTINATION")
		callout = fare.destination.place(_language)
		var road: String = fare.destination.road(_language)
		if state == FareSystem.State.CARRYING:
			var left: String = distance(fare.remaining_road_m)
			callout_sub = left if road.is_empty() else "%s  %s" % [road, left]
		else:
			callout_sub = road
		return

	has_target = nearest != null
	target = nearest.point if nearest != null else Vector3.ZERO
	target_is_destination = false
	if _notice != Notice.NONE and _notice_left > 0:
		_notice_left -= 1
		caption = _notice_caption
		callout = _notice_callout
		callout_sub = _notice_sub
		return
	_notice = Notice.NONE
	caption = ""
	callout = ""
	callout_sub = ""


## The string for the face's language, Chinese first so a pair reads the
## same way at every call site.
func _say(zh: String, en: String) -> String:
	return zh if _language == Locale.CHINESE else en


## Dollars to one place, as the 咪錶 shows them.
static func money(hkd: float) -> String:
	return "%.1f" % hkd


## A road distance: to ten metres under a kilometre, else to a tenth of one —
## a nav readout's steps, so the last digit does not flicker at 5 Hz.
static func distance(metres: float) -> String:
	var tens: int = roundi(maxf(metres, 0.0) / 10.0) * 10
	return ("%d m" % tens) if tens < 1000 else ("%.1f km" % (tens / 1000.0))


## What a meter tick or a skill flashes: the money, signed — "+HK$2.1", or
## "−HK$5.0" for a penalty, with a proper minus.
static func flash(delta_hkd: float) -> String:
	return ("+HK$" + money(delta_hkd)) if delta_hkd >= 0.0 else ("−HK$" + money(-delta_hkd))


## What a skill flashes under the clock as it pays: the money, then the skill.
func award_text(award: Fare.Award) -> String:
	return "%s %s" % [flash(award.hkd), skill_name(award.skill)]


## A skill's name, in the face's language. Cantonese for the two the street
## has words for: 甩尾 is a drift and 飆車 is speeding.
func skill_name(skill: Fare.Skill) -> String:
	match skill:
		Fare.Skill.DRIFT:
			return _say("甩尾", "drift")
		Fare.Skill.SPEED:
			return _say("飆車", "speed")
		Fare.Skill.EARLY:
			return _say("早到", "early")
		Fare.Skill.NEAR_MISS:
			return _say("擦身", "near miss")
		Fare.Skill.AIR:
			return _say("飛車", "air")
		Fare.Skill.CRASH:
			return _say("撞車", "crash")
	return ""


## The delivery's sum, as one line: the meter, the time left, then each skill
## that paid with its count — "meter 29.0 + time 18.0 + drift ×2 10.0".
## Skills that never paid are left out; a fare with no tip is the meter alone.
func receipt(fare: Fare) -> String:
	var time: PackedStringArray = []
	if fare.time_hkd > 0.0:
		time.append(_say("時間 ", "time ") + money(fare.time_hkd))
	return " + ".join(_sum_lines(fare, time))


## What a bail cost: the meter and every skill that had paid, all unpaid.
func forfeit(fare: Fare) -> String:
	return " + ".join(_sum_lines(fare, [])) + _say(" 冇收", " lost")


## The meter, `after` it, then each skill that paid with its count and its
## total — one pass over the awards.
func _sum_lines(fare: Fare, after: PackedStringArray) -> PackedStringArray:
	var lines: PackedStringArray = [_say("咪錶 ", "meter ") + money(fare.meter.reading_hkd())]
	lines.append_array(after)
	var counts: PackedInt32Array = []
	var paid: PackedFloat64Array = []
	counts.resize(Fare.Skill.size())
	paid.resize(Fare.Skill.size())
	for award: Fare.Award in fare.awards:
		counts[award.skill] += 1
		paid[award.skill] += award.hkd
	for skill: int in Fare.Skill.size():
		if counts[skill] == 0:
			continue
		var name: String = skill_name(skill as Fare.Skill)
		if counts[skill] > 1:
			name += " ×%d" % counts[skill]
		lines.append("%s %s" % [name, signed(paid[skill])])
	return lines


## Money with a minus sign for a penalty — a proper minus, not a hyphen, so
## "crash −5.0" reads as a deduction and not a range.
static func signed(hkd: float) -> String:
	return ("−" + money(-hkd)) if hkd < 0.0 else money(hkd)


## Whole seconds left, rounded UP: a clock that reads 0 with time still on it
## tells the player they are out when they are not.
static func seconds(remaining_s: float) -> String:
	return str(ceili(maxf(remaining_s, 0.0)))
