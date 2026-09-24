class_name SkillTracker
extends RefCounted
## The skills one fare earns while it runs (`P3-49`, `Q145`): a Forza-style
## per-event bonus, each one a flat HK$ into `Fare.tip_hkd` the moment it is
## earned, and a receipt line at the end.
##
## **Two skills tick, one is judged at the door.** A drift pays every
## `drift_s` the slip holds at or over the threshold; sustained speed pays
## every `speed_hold_s` the car holds `speed_min_kph`; an early arrival pays
## once at delivery when `early_share` of the allowance is still on the clock.
## Near miss and air are slots in `Fare.Skill`, not skills: the first needs
## `B3`'s traffic and the second something to jump off (`GAME_DESIGN.md`).
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

var _profile: SkillProfile = null
var _slip_threshold_deg: float = INF
## Seconds of the current slide at or over the threshold, less what it has
## already been paid for.
var _drift_s: float = 0.0
## Seconds of the current run at or over the speed floor, less what it has
## already been paid for.
var _speed_s: float = 0.0
## What the last `tick` earned. One array, cleared each tick rather than
## allocated: `tick` runs every physics tick and nearly always returns empty.
var _earned: Array[Fare.Award] = []


func _init(profile: SkillProfile, slip_threshold_deg: float) -> void:
	_profile = profile
	_slip_threshold_deg = slip_threshold_deg


## One tick of the drive: what it earned, in the order it was earned. Usually
## nothing. ⚠️ The array is reused: read it before the next `tick`.
func tick(speed_kph: float, slip_deg: float, delta_s: float) -> Array[Fare.Award]:
	_earned.clear()
	var elapsed: float = maxf(delta_s, 0.0)
	_drift_s = _dwell(
		slip_deg >= _slip_threshold_deg,
		_drift_s,
		elapsed,
		_profile.drift_s,
		Fare.Skill.DRIFT,
		_profile.drift_hkd
	)
	_speed_s = _dwell(
		speed_kph >= _profile.speed_min_kph,
		_speed_s,
		elapsed,
		_profile.speed_hold_s,
		Fare.Skill.SPEED,
		_profile.speed_hkd
	)
	return _earned


## One dwell meter: `dwell_s` grows by `elapsed` while `held`, pays `hkd` as
## `skill` each time it crosses `bar_s`, and returns what is left. Dropping the
## hold ends the event and forfeits the part not yet paid: a slide is one
## event, and two short ones are not one long one.
func _dwell(
	held: bool, dwell_s: float, elapsed: float, bar_s: float, skill: Fare.Skill, hkd: float
) -> float:
	if not held:
		return 0.0
	var left: float = dwell_s + elapsed
	while left >= bar_s:
		left -= bar_s
		_earned.append(Fare.Award.new(skill, hkd))
	return left


## At the door: the early arrival, or null. `remaining_s` over `allowance_s`
## at or over `early_share` pays; the bar is inclusive so a verify tool can
## stand on it.
func arrival(remaining_s: float, allowance_s: float) -> Fare.Award:
	if allowance_s <= 0.0:
		return null
	if remaining_s / allowance_s < _profile.early_share:
		return null
	return Fare.Award.new(Fare.Skill.EARLY, _profile.early_hkd)
