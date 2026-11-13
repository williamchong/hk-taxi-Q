class_name KeyboardSteerProfile
extends Resource
## How a key's all-or-nothing steering is shaped into a linear input, as data
## (`Q210`).
##
## 🔴 **An input assist, never a drive assist.** A key reads 0 or 1; a thumb, a
## stick or a wheel reads anywhere between, and the car's own assists
## (`ArcadeAidsProfile`, the systems' tables) are tuned against an input that
## can be anywhere between. So the key is turned into one HERE, in the input
## layer, before the car sees it — the car is never tuned against a key. Touch
## has its own table (`TouchProfile`); a stick passes through as it is.
##
## No defaults (`Q119`): the numbers live only in `game/tuning/keyboard_steer.tres`,
## and why each is what it is in the sidecar beside it.

const PATH: String = "res://tuning/keyboard_steer.tres"

## Seconds for a held key to take the input from centre to full at rest.
@export_range(0.01, 1.0, 0.01, "suffix:s") var attack_s: float
## Seconds for a held key to take the input from centre to full at the car's
## limiter; `attack_s` holds at rest, and the two blend on the SQUARE of the
## share of the limiter, as the yaw a swing of the wheels puts into the car
## grows with the speed squared (`Q174`). The car asks for `attack_s` instead
## in drift mode and on the countersteer side of a slide, where a slow catch
## would be the spin the slow ramp is there to prevent.
@export_range(0.01, 5.0, 0.01, "suffix:s") var attack_at_top_s: float
## The shape of the slow ramp: the input is the ramp's progress to this power.
## 1 is linear; 2 eases out of centre, so a short tap is a smaller input while a
## held key reaches full in the same seconds. The quick ramp (drift mode, a
## countersteer) stays linear, so a catch is never slowed by it.
@export_range(1.0, 4.0, 0.1) var curve: float


## Whether every key is set: a zero ramp is a key that never moves the input,
## and a curve under 1 is no shape the inverse in `InputRouter` can undo.
func usable() -> bool:
	return attack_s > 0.0 and attack_at_top_s > 0.0 and curve >= 1.0
