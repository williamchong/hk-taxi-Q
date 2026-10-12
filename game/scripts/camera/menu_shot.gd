## One camera placement round the parked taxi for the start menu: where
## `MenuOrbit` puts the rig while a given page is up — the turntable on HOME,
## the tail on OPTIONS, the kerbside front three-quarter on PLAY with the
## passenger door open.
##
## 🔴 **No `@export` here declares a default** (`Q150`'s convention): a default
## is a second copy of the tuning table and Godot's writer drops any key equal
## to one. The rationale for each shot is in `tuning/menu.md`.
class_name MenuShot
extends Resource

## Where the camera stands, in degrees round the car from its chase position
## (0 behind the car, 180 in front of it). For a turning shot, where it starts.
@export var yaw_deg: float
## The spring arm's length, and the pivot's height over the car's origin.
@export var distance_m: float
@export var height_m: float
## Negative looks down onto the car.
@export var pitch_deg: float
@export var fov_deg: float
## A whole circle round the car takes this long; 0 stands at `yaw_deg`.
@export var turn_period_s: float
## A standing shot rocks this far either side of `yaw_deg`, once a
## `sway_period_s` — enough that the frame is never still.
@export var sway_deg: float
@export var sway_period_s: float
## The rear kerbside door (`TaxiDoor`) stands open while this shot is up —
## the cab ready for its fare.
@export var door_open: bool
