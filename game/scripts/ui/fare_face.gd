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
## **Nothing is shown until there is a customer** (the user's call, `Q142`,
## 2026-09-24, reversing the nearest-pickup callout): idle, the guide, the pin
## and the callout are down and only the pool's pips on the map say where a
## stand is. Hailed, everything points at the destination.
##
## **A stop is said the way a passenger says it** (the user's call, `Q142`):
## a caption saying what the box is, the building — `Fare.Stop.place()`,
## iB1000's name for the footprint the point stands at — and the road under it
## with the road distance left. **In one language** (`Locale`), never both on
## a row: DESTINATION / "Times Square" / "RUSSELL STREET  1.2 km".
##
## **Money shows as HK$ to one place**, the way the 咪錶 shows it, and the meter
## shows the last banked sum between fares — a meter left reading the last trip
## is what a real cab shows at a stand. No multiplier, no separate tip line
## while the fare runs: the tip is the seconds left, which the timer shows.

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
var total_text: String = ""
## The tip clock: whole seconds left, shown only while carrying.
var timer_text: String = ""
var show_timer: bool = false
## Under the style's `timer_warn_s`: the clock turns the fare's red.
var timer_urgent: bool = false
## Where the guide and the map's pin point: the destination, once hailed.
var has_target: bool = false
var target: Vector3 = Vector3.ZERO

var _language: String = Locale.DEFAULT
var _hold_samples: int = 0
var _notice: Notice = Notice.NONE
var _notice_left: int = 0
var _notice_fare: Fare = null


func _init(hold_samples: int, language: String) -> void:
	_hold_samples = maxi(hold_samples, 0)
	_language = language


## `delivered` or bailed: the callout holds the outcome for a few samples.
func on_ended(fare: Fare, delivered: bool) -> void:
	_notice = Notice.DELIVERED if delivered else Notice.BAILED
	_notice_left = _hold_samples
	_notice_fare = fare


## One sample of the loop: its `state` and `fare`, the bar under which the
## clock is urgent, and what the session has banked.
func on_sampled(state: FareSystem.State, fare: Fare, warn_s: float, earned_hkd: float) -> void:
	var chinese: bool = _language == Locale.CHINESE
	total_text = ("合計 HK$" if chinese else "TOTAL HK$") + money(earned_hkd)
	show_timer = state == FareSystem.State.CARRYING
	timer_urgent = false
	timer_text = ""
	meter_text = money(0.0)
	if state == FareSystem.State.CARRYING:
		timer_text = seconds(fare.remaining_s)
		timer_urgent = fare.remaining_s <= warn_s
		meter_text = money(fare.meter.reading_hkd())
	elif state == FareSystem.State.BOARDING:
		meter_text = money(fare.meter.reading_hkd())

	if state != FareSystem.State.IDLE:
		_notice = Notice.NONE
		has_target = true
		target = fare.destination.point
		if state == FareSystem.State.BOARDING:
			caption = "上客中" if chinese else "PICKING UP"
		else:
			caption = "目的地" if chinese else "DESTINATION"
		callout = fare.destination.place(_language)
		var road: String = fare.destination.road(_language)
		if state == FareSystem.State.CARRYING:
			var left: String = distance(fare.remaining_road_m)
			callout_sub = left if road.is_empty() else "%s  %s" % [road, left]
		else:
			callout_sub = road
		return

	has_target = false
	target = Vector3.ZERO
	if _notice != Notice.NONE and _notice_left > 0:
		_notice_left -= 1
		if _notice == Notice.DELIVERED:
			caption = "已送達" if chinese else "DELIVERED"
			callout = "HK$" + money(_notice_fare.banked_hkd)
			callout_sub = ("小費 HK$" if chinese else "tip HK$") + money(_notice_fare.tip_hkd)
		else:
			caption = "乘客下車" if chinese else "PASSENGER BAILED"
			callout = ""
			callout_sub = ""
		return
	_notice = Notice.NONE
	caption = ""
	callout = ""
	callout_sub = ""


## Dollars to one place, as the 咪錶 shows them.
static func money(hkd: float) -> String:
	return "%.1f" % hkd


## A road distance: whole metres under a kilometre, else to a tenth of one.
static func distance(metres: float) -> String:
	var m: float = maxf(metres, 0.0)
	return ("%d m" % roundi(m)) if m < 1000.0 else ("%.1f km" % (m / 1000.0))


## What a meter tick flashes: the unit that just began, signed.
static func flash(delta_hkd: float) -> String:
	return "+HK$" + money(delta_hkd)


## Whole seconds left, rounded UP: a clock that reads 0 with time still on it
## tells the player they are out when they are not.
static func seconds(remaining_s: float) -> String:
	return str(ceili(maxf(remaining_s, 0.0)))
