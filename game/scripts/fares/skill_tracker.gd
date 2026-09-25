class_name SkillTracker
extends RefCounted
## The skills one fare earns while it runs (`P3-49`, `Q145`): a Forza-style
## per-event bonus, each one a flat HK$ into `Fare.tip_hkd` the moment it is
## earned, and a receipt line at the end.
##
## **Two skills tick, one is judged at the door.** A drift counts once the
## slip has held at or over the threshold for `drift_min_s` — a shorter slide
## is a tap and pays nothing (the user's call) — and pays again every further
## `drift_s`; sustained speed pays every `speed_hold_m` DRIVEN at or over
## `speed_min_kph`, distance rather than time so it can never tick faster than
## the meter's own 200 m unit (the user's call); an early arrival pays once at
## delivery when `early_share` of the allowance is still on the clock. Near
## miss and air are slots in `Fare.Skill`, not skills: the first needs `B3`'s
## traffic and the second something to jump off (`GAME_DESIGN.md`).
##
## 🚫 **Not a style chain.** `GAME_DESIGN.md` sketched a multiplier that a hard
## crash resets; the user chose flat money per event (`Q145`), and there is no
## crash detector to reset a chain with. `P3-2b` may layer the chain on top of
## this; the awards stay what they are.
##
## **Pure, so `verify_fares.gd` can drive it without a car.** `tick` takes the
## speed, the slip and the elapsed time; `FareSystem` is the only caller and
## the only thing that reads the car. A dwell is measured from both sides in
## the verify tool: one tick short pays nothing, the tick that reaches it pays.


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
var _drift: Dwell = Dwell.new()
var _speed: Dwell = Dwell.new()
## What the last `tick` earned. One array, cleared each tick rather than
## allocated: `tick` runs every physics tick and nearly always returns empty.
var _earned: Array[Fare.Award] = []


func _init(profile: SkillProfile, slip_threshold_deg: float) -> void:
	_profile = profile
	_slip_threshold_deg = slip_threshold_deg


## One tick of the drive: what it earned, in the order it was earned. Usually
## nothing. ⚠️ The array is reused: read it before the next `tick`.
func tick(speed_mps: float, slip_deg: float, delta_s: float) -> Array[Fare.Award]:
	_earned.clear()
	var elapsed: float = maxf(delta_s, 0.0)
	var speed: float = maxf(speed_mps, 0.0)
	_dwell(
		_drift,
		slip_deg >= _slip_threshold_deg,
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
	return _earned


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
