class_name SkillTracker
extends RefCounted
## The skills one fare earns while it runs (`P3-49`, `Q145`): a Forza-style
## per-event bonus, each one a flat HK$ into `Fare.tip_hkd` the moment it is
## earned, and a receipt line at the end.
##
## **Two skills tick, one pays at the landing, one is judged at the door.** A
## drift counts once the slip has held at or over the threshold for
## `drift_min_s` — a shorter slide is a tap and pays nothing (the user's call)
## — and pays again every further `drift_s`; sustained speed pays every
## `speed_hold_m` DRIVEN at or over `speed_min_kph`, distance rather than time
## so it can never tick faster than the meter's own 200 m unit (the user's
## call); air (`P3-51`, `Q147`) is every wheel off the ground, metered in
## seconds and paid ON THE LANDING — `air_hkd` once the flight held `air_min_s`
## and again per further `air_s` — and only when the car lands upright: a roll
## is four wheels in the air too, and pays nothing; an early arrival pays once
## at delivery when `early_share` of the allowance is still on the clock. Near
## miss is the one slot left in `Fare.Skill`, waiting on `B3`'s traffic.
##
## ⚠️ **Air pays at the landing, never per second in the air.** A dwell that
## paid while airborne would pay a car falling off the world, and the roll
## test can only be asked once the wheels are back down. A slide, by contrast,
## pays while it holds, because the ground is what makes it a slide. And a
## drift meter does not run while airborne: a car yawing in the air reads a
## slip angle, and `vehicle_controller.gd` refuses its yaw assist there for the
## same reason.
##
## **Penalties are the same machinery with the sign flipped** (`P3-50`,
## `Q148`): a wall hit arrives as `impact_mps`, the speed into the wall on
## the tick of the contact, and two bars tier it — under `bump_min_kph` a
## touch, free but the end of any slide; at or over it a collision docking
## `bump_hkd`; at or over `crash_min_kph` a crash docking `crash_hkd`. One
## wall is one dock: `crash_cool_s` after a dock every further contact is the
## same event. The tip floors at zero in `FareSystem.tip_of`; the meter is
## never docked.
##
## 🚫 **Not a style chain.** `GAME_DESIGN.md` sketched a multiplier that a hard
## crash resets; the user chose flat money per event (`Q145`). `P3-2b` may
## layer the chain on top of this; the awards stay what they are.
##
## **Pure, so `verify_fares.gd` can drive it without a car.** `tick` takes the
## speed, the slip and the elapsed time; `FareSystem` is the only caller and
## the only thing that reads the car. A dwell is measured from both sides in
## the verify tool: one tick short pays nothing, the tick that reaches it pays.
##
## **One tracker for the session, not one per fare** (the user's call,
## 2026-09-26): it runs empty too, so a stunt can be practised between fares
## and the HUD says what it was. Whether an award is PAID is `FareSystem`'s
## decision — with a passenger aboard it lands on the fare, empty it is only
## shown — and `reset` at boarding starts the passenger's receipt clean.


## One event's meter: how much of it has run (seconds for a slide, metres for
## a run) and how many awards it has paid, so the first bar and the repeat
## bar can differ without a remainder drifting on a 0.25 s tick.
class Dwell:
	extends RefCounted
	var total: float = 0.0
	var paid: int = 0

	func reset() -> void:
		total = 0.0
		paid = 0


var _profile: SkillProfile = null
var _slip_threshold_deg: float = INF
## False until a whole table and a drift angle were handed in; an inert
## tracker earns nothing, and `FareSystem.setup` refuses to hail on one.
var _usable: bool = false
var _drift: Dwell = Dwell.new()
var _speed: Dwell = Dwell.new()
var _air: Dwell = Dwell.new()
## Seconds left in which a further contact is the last dock's event.
var _cool_s: float = 0.0
## What the last `tick` earned. One array, cleared each tick rather than
## allocated: `tick` runs every physics tick and nearly always returns empty.
var _earned: Array[Fare.Award] = []


## A missing or zeroed table, a crash bar at or under the bump bar, or no
## drift angle makes an INERT tracker, with the reason pushed — never one
## running on a literal (`Q119`).
func _init(profile: SkillProfile, slip_threshold_deg: float) -> void:
	if profile == null:
		push_error("SkillTracker: no SkillProfile handed in; no skill will pay.")
		return
	var required: Dictionary[String, float] = {
		"drift_min_s": profile.drift_min_s,
		"drift_s": profile.drift_s,
		"drift_hkd": profile.drift_hkd,
		"speed_min_kph": profile.speed_min_kph,
		"speed_hold_m": profile.speed_hold_m,
		"speed_hkd": profile.speed_hkd,
		"air_min_s": profile.air_min_s,
		"air_s": profile.air_s,
		"air_hkd": profile.air_hkd,
		"early_share": profile.early_share,
		"early_hkd": profile.early_hkd,
		"bump_min_kph": profile.bump_min_kph,
		"bump_hkd": profile.bump_hkd,
		"crash_min_kph": profile.crash_min_kph,
		"crash_hkd": profile.crash_hkd,
		"crash_cool_s": profile.crash_cool_s,
	}
	if TuningTable.any_zero(profile, required, "SkillTracker", "no skill will pay"):
		return
	if profile.crash_min_kph <= profile.bump_min_kph:
		push_error(
			(
				"SkillTracker: %s crash_min_kph (%.1f) is not over bump_min_kph (%.1f); no skill will pay."
				% [profile.resource_path, profile.crash_min_kph, profile.bump_min_kph]
			)
		)
		return
	if slip_threshold_deg <= 0.0:
		push_error("SkillTracker: no drift_slip_threshold_deg handed in; no skill will pay.")
		return
	_profile = profile
	_slip_threshold_deg = slip_threshold_deg
	_usable = true


func usable() -> bool:
	return _usable


## Forget every dwell in progress and the cooldown: a slide or a flight held
## into the boarding does not pay the passenger for the part before them.
func reset() -> void:
	_drift.reset()
	_speed.reset()
	_air.reset()
	_cool_s = 0.0


## One tick of the drive: what it earned, in the order it was earned. Usually
## nothing. `airborne` is every wheel off the ground this tick; `upright` is
## the body's up still up — read on the landing tick, the one that decides;
## `impact_mps` is the hardest wall contact this tick, 0 for none.
## ⚠️ The array is reused: read it before the next `tick`.
func tick(
	speed_mps: float,
	slip_deg: float,
	delta_s: float,
	airborne: bool = false,
	upright: bool = true,
	impact_mps: float = 0.0
) -> Array[Fare.Award]:
	_earned.clear()
	var elapsed: float = maxf(delta_s, 0.0)
	var speed: float = maxf(speed_mps, 0.0)
	var touched: bool = impact_mps > 0.0
	_dwell(
		_drift,
		slip_deg >= _slip_threshold_deg and not airborne and not touched,
		elapsed,
		_profile.drift_min_s,
		_profile.drift_s,
		Fare.Skill.DRIFT,
		_profile.drift_hkd
	)
	_dwell(
		_speed,
		speed * 3.6 >= _profile.speed_min_kph,
		speed * elapsed,
		_profile.speed_hold_m,
		_profile.speed_hold_m,
		Fare.Skill.SPEED,
		_profile.speed_hkd
	)
	_flight(airborne, upright, elapsed)
	_hit(impact_mps, elapsed)
	return _earned


## The penalty tiers, on the speed into the wall. The cooldown runs down
## first, so a dock at its last tick and a fresh wall on the next are two.
func _hit(impact_mps: float, elapsed: float) -> void:
	_cool_s = maxf(_cool_s - elapsed, 0.0)
	var impact_kph: float = impact_mps * 3.6
	if impact_kph < _profile.bump_min_kph:
		return
	if _cool_s > 0.0:
		return
	_cool_s = _profile.crash_cool_s
	if impact_kph >= _profile.crash_min_kph:
		_earned.append(Fare.Award.new(Fare.Skill.CRASH, -_profile.crash_hkd))
	else:
		_earned.append(Fare.Award.new(Fare.Skill.BUMP, -_profile.bump_hkd))


## The air meter: seconds in the air, judged on the tick the wheels come back.
## A flight that held `air_min_s` pays `air_hkd` once and again per further
## `air_s`, all at the landing, and only when the car lands upright — a
## rolled car is airborne by the same reading and pays nothing. A flight that
## never lands (the harness resets a fallen car) pays nothing either: the
## meter is reset by the next grounded tick, wherever that is.
func _flight(airborne: bool, upright: bool, elapsed: float) -> void:
	if airborne:
		_air.total += elapsed
		return
	if _air.total > 0.0 and upright and _air.total >= _profile.air_min_s:
		var paid: int = 1 + int(floor((_air.total - _profile.air_min_s) / _profile.air_s))
		for _count: int in paid:
			_earned.append(Fare.Award.new(Fare.Skill.AIR, _profile.air_hkd))
	_air.reset()


## One dwell meter: `meter.total` grows by `amount` while `held`, pays `hkd`
## as `skill` once it reaches `first_bar` and again each `bar` after that.
## Dropping the hold ends the event and forfeits the part not yet paid: a
## slide is one event, and two short ones are not one long one.
func _dwell(
	meter: Dwell,
	held: bool,
	amount: float,
	first_bar: float,
	bar: float,
	skill: Fare.Skill,
	hkd: float
) -> void:
	if not held:
		meter.reset()
		return
	meter.total += amount
	while meter.total >= first_bar + meter.paid * bar:
		meter.paid += 1
		_earned.append(Fare.Award.new(skill, hkd))


## At the door: the early arrival, or null. `remaining_s` over `allowance_s`
## at or over `early_share` pays; the bar is inclusive so a verify tool can
## stand on it.
func arrival(remaining_s: float, allowance_s: float) -> Fare.Award:
	if allowance_s <= 0.0:
		return null
	if remaining_s / allowance_s < _profile.early_share:
		return null
	return Fare.Award.new(Fare.Skill.EARLY, _profile.early_hkd)
