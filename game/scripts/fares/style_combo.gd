class_name StyleCombo
extends RefCounted
## The style combo (`P3-2b`, `Q205`, the user's design 2026-11-13): a count of
## each bonus skill performed in one unbroken run of them, shown and recorded,
## and **never money** — the fare and the tip are what they were (`Q145`).
##
## **Each skill keeps its own count, and any skill keeps them all alive.** A
## bonus award adds one to its skill's count and puts the timer back to
## `combo_gap_s`; a second skill joins beside the first, which keeps its count
## (speed ×10, close call ×1). The combo ENDS on a collision or a crash — the
## tracker's `BUMP` / `CRASH`; a free touch under `bump_min_kph` is not one —
## or when the timer runs out. Its total is the sum of the counts.
##
## 🔴 **The timer stands still while a skill is in progress** (the user's
## call): sliding over the threshold, at or over `speed_min_kph`, or in the
## air (`SkillTracker.holding`). The skills pay at very different cadences —
## a drift every second, the speed run every 200 m (9 s at 80 kph) — so a gap
## short enough to feel tight would end every speed run at ×1 without it. It
## runs down only while the car is doing nothing that will pay.
##
## Practice counts (the user's call): it moves no money, so an empty taxi's
## stunt builds a combo like a carried one. A boarding, a delivery and a bail
## leave it running. `FareSystem` is the only caller; pure, so `verify_fares`
## drives it tick by tick.

## Each bonus skill's count in the combo running now, by `Fare.Skill`.
var counts: PackedInt32Array = []
## Seconds left before the combo ends on its own; 0 with none running.
var remaining_s: float = 0.0

## The table, once it passed the zero check; null makes the combo inert.
var _profile: SkillProfile = null
## Whether `hit` ran since the last `tick`: that tick is the award's own and
## does not count down, so the gap is measured from the award.
var _fresh: bool = false


## A missing table or a zero `combo_gap_s` makes an INERT combo, the reason
## pushed — never one running on a literal (`Q119`).
func _init(profile: SkillProfile) -> void:
	counts.resize(Fare.Skill.size())
	counts.fill(0)
	if profile == null:
		push_error("StyleCombo: no SkillProfile handed in; no combo will run.")
		return
	var required: Dictionary[String, float] = {
		"combo_gap_s": profile.combo_gap_s,
		"combo_show_min": float(profile.combo_show_min),
	}
	if TuningTable.any_zero(profile, required, "StyleCombo", "no combo will run"):
		return
	_profile = profile


func usable() -> bool:
	return _profile != null


## Whether a combo is running: at least one skill counted and not yet ended.
func live() -> bool:
	return total() > 0


## The sum of every skill's count: the final multiplier shown at the end.
func total() -> int:
	var sum: int = 0
	for count: int in counts:
		sum += count
	return sum


## Whether the combo is big enough for its end to be called out.
func shown() -> bool:
	return usable() and total() >= _profile.combo_show_min


## How many different skills the combo holds.
func skills() -> int:
	var different: int = 0
	for count: int in counts:
		if count > 0:
			different += 1
	return different


## A bonus performed: its count up by one and the timer back to the full gap.
## Only bonuses — `FareSystem` ends the combo on a penalty instead.
func hit(skill: Fare.Skill) -> void:
	if not usable():
		return
	counts[skill] += 1
	remaining_s = _profile.combo_gap_s
	_fresh = true


## One tick, after its awards: the timer runs down by `elapsed` unless
## `holding` or a skill joined on this very tick. True on the
## tick it runs out, with the counts still standing for the caller to read
## before `clear`.
func tick(elapsed: float, holding: bool) -> bool:
	var fresh: bool = _fresh
	_fresh = false
	if not live() or holding or fresh:
		return false
	remaining_s = maxf(remaining_s - maxf(elapsed, 0.0), 0.0)
	return is_zero_approx(remaining_s)


## The share of the gap left, 1 just after a hit, for the HUD's bar.
func remaining_share() -> float:
	return clampf(remaining_s / _profile.combo_gap_s, 0.0, 1.0) if usable() else 0.0


## A copy of the counts as they stand, for a reader holding them past `clear`.
## Only a usable combo has counts to copy, so the copy is built on its table.
func snapshot() -> StyleCombo:
	var copy := StyleCombo.new(_profile)
	copy.counts = counts.duplicate()
	copy.remaining_s = remaining_s
	return copy


## Forget the combo: every count to 0 and the timer stopped.
func clear() -> void:
	counts.fill(0)
	remaining_s = 0.0
	_fresh = false
