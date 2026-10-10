## The shift's hours (`Q162`, the user's ask): 特更 runs from `opens_h` to
## `closes_h` on the clock the player reads, over the day cycle's own
## `length_s` of driving — one length, the rig's, so the clock on the dash and
## the sky cannot disagree about when the day ends.
##
## 🔴 **No `@export` here declares a default** (`Q150`'s convention): a missing
## hour reads zero and `usable()` refuses the table.
class_name ShiftProfile
extends Resource

const PATH: String = "res://tuning/shift.tres"

## The hour the shift opens, on a 24-hour clock.
@export_range(0.0, 24.0, 0.25, "suffix:h") var opens_h: float
## The hour of 交更, the handover: the shift's last game second.
@export_range(0.0, 24.0, 0.25, "suffix:h") var closes_h: float


## Whether the hours make a shift: both set, and the close after the open.
func usable() -> bool:
	if TuningTable.any_zero(
		self, {"opens_h": opens_h, "closes_h": closes_h}, "ShiftProfile", "there is no shift"
	):
		return false
	if closes_h <= opens_h:
		push_error(
			"ShiftProfile: %s closes at %s, not after %s." % [resource_path, closes_h, opens_h]
		)
		return false
	return true


## The hour on the clock `share` of the way through the shift, 0 to 1.
func hour_at(share: float) -> float:
	return lerpf(opens_h, closes_h, clampf(share, 0.0, 1.0))
