class_name TaxiHire
extends Node
## What the fare loop shows ON the car (`P3-48`): the roof sign and the
## passenger door.
##
## - **The sign** is lit while the car is for hire and dark while a passenger is
##   aboard — out at `boarded`, back at `delivered` or `bailed`. A hail does not
##   put it out: until the passenger is in the seat the fare can still be
##   `cancelled`, and the car is still for hire.
## - **The door** stands open from the hail to the boarding, and opens briefly
##   when a fare gets out — delivered or bailed.
##
## ⚠️ **Listens, and never polls.** Every change here is a `FareSystem` signal,
## so nothing runs per frame and the system stays pure enough for
## `verify_fares.gd` to drive without a car. `VehicleLamps` and `TaxiDoor` stay
## ignorant of fares for the same reason `VehicleLamps` never reads the player's
## input: an AI taxi on the same body (`B3`) has neither a fare loop nor a
## player, and its sign and door must not answer to the player's.
##
## A child of `Fares`, so `--fares=off` frees it with the loop and leaves both
## as the car was authored: sign lit, door shut — free roam is a taxi plying for
## hire.

## The loop to follow. Assign in the scene.
@export var fares: FareSystem
## The car whose sign and door this switches.
@export var vehicle: Node3D

var _lamps: VehicleLamps = null
var _door: TaxiDoor = null


func _ready() -> void:
	if fares == null or vehicle == null:
		push_warning("TaxiHire has no FareSystem or no vehicle assigned; the sign stays lit.")
		return
	# Found by type under the car rather than named by path, as `VehicleLamps`
	# finds its body mesh: the scene owns where each rig hangs, and a car that
	# carries no door still gets its sign switched.
	for node: Node in vehicle.find_children("*", "", true, false):
		if node is VehicleLamps and _lamps == null:
			_lamps = node as VehicleLamps
		elif node is TaxiDoor and _door == null:
			_door = node as TaxiDoor
	fares.hailed.connect(_on_hailed)
	fares.boarded.connect(_on_boarded)
	fares.cancelled.connect(_on_cancelled)
	fares.delivered.connect(_on_alighted)
	fares.bailed.connect(_on_alighted)


func _on_hailed(_fare: Fare) -> void:
	if _door != null:
		_door.open()


func _on_boarded(_fare: Fare) -> void:
	if _lamps != null:
		_lamps.for_hire = false
	if _door != null:
		_door.close()


func _on_cancelled(_fare: Fare) -> void:
	if _door != null:
		_door.close()


func _on_alighted(_fare: Fare) -> void:
	if _lamps != null:
		_lamps.for_hire = true
	if _door != null:
		_door.open_briefly()
