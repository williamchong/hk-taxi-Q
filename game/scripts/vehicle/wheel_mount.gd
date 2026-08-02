class_name WheelMount
extends Marker3D
## One suspension hardpoint. Position is the top of the spring, not the hub.
##
## Chassis layout lives here, in the vehicle scene, rather than in
## HandlingProfile: wheelbase and track are per-vehicle model data, while the
## profile describes feel. See docs/PROGRESS.md, P0-5a.

## Front wheels steer. Both axles may steer if a vehicle wants it.
@export var steers: bool = false
## Which wheels receive engine torque.
@export var drives: bool = false

## Simulation state, owned and written by VehicleController each tick. Lives on
## the mount rather than in the controller so the wheel visual can read it
## directly; nothing else should write it.
var compression: float = 0.0
## False when the raycast found no ground — the wheel is airborne.
var grounded: bool = false
## This wheel's steering rotation in radians, zero unless it steers. Published
## here rather than read off the controller because the visual needs the angle
## for THIS wheel, and a four-wheel-steer vehicle would not share one.
var steer_angle: float = 0.0
## Set once by VehicleController from the wheel's position along the chassis.
## Derived rather than authored so it stays correct for a four-wheel-steer or
## front-drive vehicle, where `steers` and `drives` are not proxies for an axle.
var is_front: bool = false
