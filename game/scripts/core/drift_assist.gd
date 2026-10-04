class_name DriftAssist
extends RefCounted
## Whether the tyre car's drift assist is on (`P3-56`, `Q153`): the
## countersteer assist and its later drive fade, which give a novice's plain
## input a slide that pays. Off, the countersteer is the player's skill.
##
## Three readers in order, and the first that knows wins: the `--assist=` flag
## (`on` / `off`), the option the start menu saved (`Settings`), then on. The
## flag stays in front for `Locale`'s reason: a scripted run must drive the
## same car whatever the menu saved on this machine, so `drive.sh` names it.

const ASSIST_ARG: String = "--assist="
const ON: String = "on"
const OFF: String = "off"


static func enabled() -> bool:
	var flag: String = Cmdline.value(ASSIST_ARG).to_lower()
	if flag == ON or flag == OFF:
		return flag == ON
	return Settings.drift_assist()


## Hands the answer to the car, where it has the assist. The shipped car on the
## engine's tyres has none, and is left alone.
static func apply(vehicle: VehicleController) -> void:
	var tyre_car: TyreVehicleController = vehicle as TyreVehicleController
	if tyre_car != null:
		tyre_car.drift_assist = enabled()
