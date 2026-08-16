class_name VehicleLamps
extends Node3D
## Switches the taxi's lamp circuits from what the car is doing (`P3-11d`).
##
## The body is one merged primitive, so there is no lamp *node* to show or hide.
## `tools/make_vehicle.py` stamps each lens with a circuit id in `UV.x` and
## `vehicle_body.gdshader` lights the ones this script names — brake, reverse,
## and an indicator per side.
##
## ⚠️ **Written per instance, not to the material.** `vehicle_body.tres` is one
## shared resource handed to every mesh that asks for it by name, so a plain
## `set_shader_parameter` would put the whole roster on one brake pedal. See the
## `lamp_lit` declaration in the shader.
##
## ⚠️ **It reads the car, never `InputRouter`.** Reading the player's input here
## would work exactly once — `ART_DESIGN.md`'s roster puts an AI red taxi on the
## same body, and every one of them would indicate whenever the player turned.
## `VehicleController` publishes what *this* car is doing — steering, and the
## pedal it samples once a tick — and that is the only thing a lamp on this car
## may answer to.
##
## Presentation only, like `WheelVisual`: nothing here is read back by the
## physics, so it cannot change how the car drives. It runs on the physics tick
## for the same reason that one does — every value it reads is written there, so
## a render-rate update would re-derive the identical answer two or three times
## between the ticks that can change it.

## The shader's per-instance channel. See `vehicle_body.gdshader`.
const PARAMETER: StringName = &"lamp_lit"

## Once a turn is counted, the lock has to fall to this fraction of
## `steer_threshold` before it stops counting.
##
## ⚠️ **Without hysteresis the hold below can never complete near the
## threshold.** A single frame at 0.349 restarts it, so a driver holding steady
## lock right about the line — which analogue steering does constantly — resets
## the timer for ever and the indicator that `steer_hold_s` exists to earn is the
## one thing that never comes on.
const TURN_RELEASE: float = 0.75

## Flashes per second. UK and Hong Kong regulation puts a real one between 1 and
## 2 Hz, and the middle of that is also what reads as a flash rather than as a
## flicker at the frame rates this ships at.
@export_range(0.5, 4.0, 0.05) var blink_hz: float = 1.5

## Share of each flash the lamp is lit for. Above a half on purpose: an
## indicator seen from behind at speed is a small object, and the eye needs
## longer on than off to call it a light rather than a glint.
@export_range(0.1, 0.9, 0.05) var blink_duty: float = 0.55

## How much lock counts as a turn, as a fraction of the lock available at this
## speed. See `VehicleController.steer_ratio` — a fraction rather than an angle,
## because full lock at 140 km/h is a quarter of full lock parked.
##
## ⚠️ The floor on this is comfort, not correctness. Set it near zero and the
## indicators strobe through every steering correction the player makes on a
## straight, which is what a real driver does *not* do.
@export_range(0.0, 1.0, 0.01) var steer_threshold: float = 0.35

## How long lock has to be *held* one way before the indicator comes on.
##
## ⚠️ **The threshold above cannot do this job on its own, and that is why both
## exist.** One says how hard a turn is, the other says how long it lasts, and an
## arcade car crosses hard lock constantly — a flick round a parked lorry, a
## correction out of a drift, a lane change. Every one of those trips the
## threshold, and without a hold the tail of the car strobes amber through all of
## them, which is worse than no indicator at all: it stops meaning "turning".
## Holding half a second keeps the lamp for the junctions it is about.
##
## The cost is that the lamp is late by exactly this much, which is fine — a real
## driver indicates before turning and this car indicates after, so it is already
## a read-out of what the car is doing rather than a signal of intent.
@export_range(0.0, 3.0, 0.05) var steer_hold_s: float = 0.5

var _car: VehicleController = null
var _body: MeshInstance3D = null
## Runs only while an indicator is live, and resets to zero when it goes out, so
## a turn always starts on a lit flash. Free-running would leave the first
## quarter-second of some turns dark, which reads as the indicator being late.
var _blink_phase: float = 0.0
## How long lock has been held on `_turn_side`, against `steer_hold_s`.
var _turn_held_s: float = 0.0
## Which way the car is turning past `steer_threshold`: -1 left, +1 right, 0 not.
## Kept between frames because a *change* of side has to restart the hold —
## swinging straight from one lock to the other is two turns, not one long one.
var _turn_side: int = 0


func _ready() -> void:
	_car = VehicleController.above(self)
	assert(_car != null, "VehicleLamps found no VehicleController above it.")
	# The one mesh inside the body .glb. Taken by search rather than by path so a
	# regenerated asset can rename it, which `tools/make_vehicle.py` decides.
	var found: Array[Node] = find_children("*", "MeshInstance3D", true, false)
	if not found.is_empty():
		_body = found[0] as MeshInstance3D
	assert(_body != null, "VehicleLamps found no MeshInstance3D to switch.")
	# Belt and braces, because asserts are stripped from release builds: without
	# this a mis-wired scene crashes on the first frame of an exported build
	# rather than driving around with dark lamps.
	set_physics_process(_car != null and _body != null)


func _physics_process(delta: float) -> void:
	# The threshold to start turning; TURN_RELEASE's share of it to stop.
	var leaving: float = steer_threshold * TURN_RELEASE
	var side: int = 0
	if _car.steer_ratio > (leaving if _turn_side > 0 else steer_threshold):
		side = 1
	elif _car.steer_ratio < -(leaving if _turn_side < 0 else steer_threshold):
		side = -1

	# Straightening or swapping sides restarts the hold, and takes the blink
	# phase with it so the next turn's first flash is a lit one.
	if side != _turn_side:
		_turn_held_s = 0.0
		_blink_phase = 0.0
	_turn_side = side
	if side != 0:
		_turn_held_s += delta

	var indicating: bool = side != 0 and _turn_held_s > steer_hold_s
	if indicating:
		_blink_phase = fmod(_blink_phase + delta * blink_hz, 1.0)
	else:
		_blink_phase = 0.0
	# One phase for both sides rather than a flasher each. They are never both
	# live — `side` is one number — so the only thing a second phase could
	# express is a hazard flash, which nothing asks for.
	var flash: float = 1.0 if _blink_phase < blink_duty else 0.0

	# `CIRCUIT_*` order less one: x brake, y reverse, z indicator left, w right.
	#
	# ⚠️ Brake and reverse are asked of the car, not worked out from the pedal.
	# One button serves both and which one the player gets depends on the car's
	# speed — so at a standstill with the pedal held the *reverse* lamps light,
	# because reverse is what the pedal is asking for. That is the controller's
	# rule and this reads it rather than restating it.
	var lit := Vector4(
		1.0 if _car.is_braking() else 0.0,
		1.0 if _car.is_reversing() else 0.0,
		flash if indicating and side < 0 else 0.0,
		flash if indicating and side > 0 else 0.0,
	)
	_body.set_instance_shader_parameter(PARAMETER, lit)
