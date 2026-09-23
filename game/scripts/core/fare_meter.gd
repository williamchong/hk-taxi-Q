class_name FareMeter
extends RefCounted
## A Hong Kong taxi meter (`P3-1a`, `Q141`): the flagfall, then one unit per
## `step_m` driven **or** `step_s` waited, at `step_hkd` until the reading
## reaches `threshold_hkd` and `step_hkd_after` from there.
##
## Pure on purpose: no `Node`, no vehicle, no clock of its own, per the
## `scripts/core/` rule in docs/ARCHITECTURE.md. It is fed distance and time and
## answers a reading, so `tools/verify_fares.gd` can grade the whole tariff
## against hand-computed points with no scene and no built city.
##
## **The unit rule is the letter of the tariff, and it needs no speed bar.**
## TD prices "every subsequent 200 metres or part thereof, or waiting time of
## 1 minute or part thereof". A distance-time meter keeps two buckets past the
## flagfall and starts a new unit — charging it — the moment either one is
## exceeded, resetting both. Below 12 kph the time bucket fills first and the
## meter is charging waiting time; above it, distance. No "waiting" threshold
## exists to tune, because the tariff's own two units define the crossover.
##
## **"Or part thereof" means a unit is charged when it BEGINS.** The first unit
## begins one centimetre past the flagfall distance, the next one centimetre
## past 200 m more. Strict comparisons below are that rule; a meter that charged
## on completion would read HK$2.1 less over most of a trip.
##
## ⚠️ Nothing is charged for waiting **inside** the flagfall distance. The
## flagfall covers "the first 2 kilometres or any part thereof", with no time
## term, so a car stopped at 1.5 km driven is still on the flagfall. In a 1.5 km²
## region that is most of every trip, and it is why the reading is usually
## HK$29 — `tuning/tariff.md` says so, so nobody reads it as a stuck meter.
##
## **Cents, not dollars.** Every amount is an integer number of cents from
## construction on, so 35 units at 2.1 land on exactly 10250 and the threshold
## comparison is an integer one. `reading_hkd()` divides once, for display.

## How many units have been charged past the flagfall. **The counter that can
## see this fail**: a linear meter, or one charging on completion, moves it.
var steps: int = 0

## False until a whole tariff was handed in; an inert meter reads 0 for ever.
var _usable: bool = false
var _flagfall_cents: int = 0
var _flagfall_m: float = 0.0
var _step_m: float = 0.0
var _step_s: float = 0.0
var _step_cents: int = 0
var _step_after_cents: int = 0
var _threshold_cents: int = 0

var _cents: int = 0
## Metres driven since boarding, flagfall included.
var _distance_m: float = 0.0
## The two unit buckets, metres and seconds past the flagfall since the last
## unit began. Each reset by the other: a unit is one or the other, never both.
var _bucket_m: float = 0.0
var _bucket_s: float = 0.0
## Whether the first unit past the flagfall has begun.
var _past_flagfall: bool = false


## A missing or zeroed tariff makes an INERT meter — it reads 0 and never moves,
## and the error names why — never one running on a literal. `_init` cannot
## refuse to return, and a zero step would charge a unit every sample.
func _init(tariff: FareTariff) -> void:
	if tariff == null:
		push_error("FareMeter: no FareTariff handed in; the meter will read 0.")
		return
	if tariff.flagfall_hkd <= 0.0 or tariff.flagfall_m <= 0.0:
		push_error("FareMeter: %s has no flagfall; the meter will read 0." % tariff.resource_path)
		return
	if tariff.step_m <= 0.0 or tariff.step_s <= 0.0:
		push_error("FareMeter: %s has a zero unit; the meter will read 0." % tariff.resource_path)
		return
	if tariff.step_hkd <= 0.0 or tariff.step_hkd_after <= 0.0 or tariff.threshold_hkd <= 0.0:
		push_error("FareMeter: %s has a zero price; the meter will read 0." % tariff.resource_path)
		return
	_flagfall_cents = _cents_of(tariff.flagfall_hkd)
	_flagfall_m = tariff.flagfall_m
	_step_m = tariff.step_m
	_step_s = tariff.step_s
	_step_cents = _cents_of(tariff.step_hkd)
	_step_after_cents = _cents_of(tariff.step_hkd_after)
	_threshold_cents = _cents_of(tariff.threshold_hkd)
	_cents = _flagfall_cents
	_usable = true


func usable() -> bool:
	return _usable


## The reading, in HK$.
func reading_hkd() -> float:
	return float(_cents) / 100.0


## Metres driven since boarding.
func distance_m() -> float:
	return _distance_m


## `metres` more driven over `delta_s` more seconds. Both are clamped at zero:
## a meter runs forwards.
func advance(metres: float, delta_s: float) -> void:
	if not _usable:
		return
	var driven: float = maxf(metres, 0.0)
	var elapsed: float = maxf(delta_s, 0.0)
	_distance_m += driven

	var past_m: float = _distance_m - _flagfall_m
	if past_m <= 0.0:
		return
	if not _past_flagfall:
		# The first unit begins the moment the flagfall distance is exceeded.
		# Only the metres beyond it count towards the next one, and the time
		# bucket starts from here: nothing waited on the flagfall is charged.
		_past_flagfall = true
		_charge()
		_bucket_m = past_m
		_bucket_s = 0.0
	else:
		_bucket_m += driven
		_bucket_s += elapsed

	# Strictly exceeded, on both: "or part thereof" charges a unit as it begins,
	# and a unit is exactly 200 m long, so the 200th metre is still the last one.
	while _bucket_m > _step_m:
		_bucket_m -= _step_m
		_bucket_s = 0.0
		_charge()
	if _bucket_s > _step_s:
		_bucket_s = 0.0
		_bucket_m = 0.0
		_charge()


func _charge() -> void:
	_cents += _step_cents if _cents < _threshold_cents else _step_after_cents
	steps += 1


static func _cents_of(hkd: float) -> int:
	return roundi(hkd * 100.0)
