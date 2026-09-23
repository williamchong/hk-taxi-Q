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
## **The pending customer is the pickup pool** (the user's call, `Q142`). The
## loop hails whichever pickup the car stops at, so there is no one waiting
## passenger to point at; what the player is shown is the nearest pickup, named
## with its distance, and the arrow and the map point the same way. Boarding or
## carrying, everything points at the destination instead.
##
## **A stop is said the way a passenger says it** (the user's call, `Q142`):
## the building first — `Fare.Stop.place_en()`, iB1000's name for the footprint
## the point stands at — and the road under it as the subtitle, with the
## distance while idle. "Sun Hung Kai Centre / 新鴻基中心" over "TONNOCHY ROAD
## 320 m / 杜老誌道", never "Tonnochy Road outside Sun Hung Kai Centre".
##
## **Money shows as HK$ to one place**, the way the 咪錶 shows it, and the meter
## shows the last banked sum between fares — a meter left reading the last trip
## is what a real cab shows at a stand. No multiplier, no separate tip line
## while the fare runs: the tip is the seconds left, which the timer shows.

## What the callout holds after a fare ends, for `hold_samples` samples.
enum Notice { NONE, DELIVERED, BAILED }

## The callout: the place on the first line in both languages, the road under
## it. An empty `callout_en` means nothing to say and the panel hides.
var callout_en: String = ""
var callout_zh: String = ""
var callout_sub_en: String = ""
var callout_sub_zh: String = ""
## The meter's digits, `money`-formatted.
var meter_text: String = "0.0"
## The tip clock: whole seconds left, shown only while carrying.
var timer_text: String = ""
var show_timer: bool = false
## Under the style's `timer_warn_s`: the clock turns the fare's red.
var timer_urgent: bool = false
## Where the arrow and the map's pip point, if anywhere.
var has_target: bool = false
var target: Vector3 = Vector3.ZERO
## The target is the destination (true) or a pickup (false) — the pip's colour.
var target_is_destination: bool = false

var _hold_samples: int = 0
var _notice: Notice = Notice.NONE
var _notice_left: int = 0
var _notice_fare: Fare = null


func _init(hold_samples: int) -> void:
	_hold_samples = maxi(hold_samples, 0)


## `delivered` or bailed: the callout holds the outcome for a few samples and
## the meter reads what was banked.
func on_ended(fare: Fare, delivered: bool) -> void:
	_notice = Notice.DELIVERED if delivered else Notice.BAILED
	_notice_left = _hold_samples
	_notice_fare = fare


## One sample of the loop: its `state` and `fare`, the nearest pickup in the
## pool and its plan distance (null and 0 where there is none), and the bar
## under which the clock is urgent.
func on_sampled(
	state: FareSystem.State, fare: Fare, nearest: Fare.Stop, nearest_m: float, warn_s: float
) -> void:
	show_timer = state == FareSystem.State.CARRYING
	timer_urgent = false
	timer_text = ""
	if state == FareSystem.State.CARRYING:
		timer_text = seconds(fare.remaining_s)
		timer_urgent = fare.remaining_s <= warn_s
		meter_text = money(fare.meter.reading_hkd())
	elif state == FareSystem.State.BOARDING:
		meter_text = money(fare.meter.reading_hkd())
	elif fare != null:
		meter_text = money(fare.banked_hkd)

	if state != FareSystem.State.IDLE:
		_notice = Notice.NONE
		has_target = true
		target = fare.destination.point
		target_is_destination = true
		callout_en = "→ " + fare.destination.place_en()
		callout_zh = fare.destination.place_zh()
		callout_sub_en = fare.destination.road_en
		callout_sub_zh = fare.destination.road_zh
		return

	has_target = nearest != null
	target = nearest.point if nearest != null else Vector3.ZERO
	target_is_destination = false
	if _notice != Notice.NONE and _notice_left > 0:
		_notice_left -= 1
		callout_sub_en = ""
		callout_sub_zh = ""
		if _notice == Notice.DELIVERED:
			callout_en = "DELIVERED  HK$" + money(_notice_fare.banked_hkd)
			callout_zh = "小費 HK$" + money(_notice_fare.tip_hkd)
		else:
			callout_en = "PASSENGER BAILED"
			callout_zh = "乘客下車"
		return
	_notice = Notice.NONE
	if nearest == null:
		callout_en = ""
		callout_zh = ""
		callout_sub_en = ""
		callout_sub_zh = ""
		return
	callout_en = nearest.place_en()
	callout_zh = nearest.place_zh()
	# The road and the distance: "TONNOCHY ROAD  320 m", or "320 m" alone on
	# an unnamed edge rather than two spaces and a number.
	var apart: String = "%d m" % roundi(nearest_m)
	callout_sub_en = apart if nearest.road_en.is_empty() else "%s  %s" % [nearest.road_en, apart]
	callout_sub_zh = nearest.road_zh


## Dollars to one place, as the 咪錶 shows them.
static func money(hkd: float) -> String:
	return "%.1f" % hkd


## Whole seconds left, rounded UP: a clock that reads 0 with time still on it
## tells the player they are out when they are not.
static func seconds(remaining_s: float) -> String:
	return str(ceili(maxf(remaining_s, 0.0)))
