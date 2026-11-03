class_name TaxiHorn
extends Node
## The taxi's own horn (`Q178`): one press of the traffic's horn at each press of
## `horn`, from the car, at the file's own pitch.
##
## The player's, not the car's: a node beside the camera rig that reads
## `InputRouter`, as the rig reads `look_back`. `VehicleLamps` never reads the
## player's input, for an AI taxi on the same body (`B3`); nor does the body's horn.
##
## 🔴 **Silent while the car is `parked`**: the menu's showroom, where a key
## pressed in a menu is not the driver's.

## The car the horn sounds from. Assign in the scene.
@export var vehicle: Node3D
## The router, by path, as `ChaseCamera.input_path` finds it.
@export var input_path: NodePath = ^"/root/InputRouter"

## Presses sounded, for the verify tool.
var presses: int = 0

var _input: Node = null
var _voice: AudioStreamPlayer3D = null
var _held: bool = false


func _ready() -> void:
	_input = get_node_or_null(input_path)
	if vehicle == null:
		push_warning("TaxiHorn has no vehicle assigned; the taxi has no horn.")
		return
	var stream := load(TrafficSystem.HORN_PATH) as AudioStream
	if stream == null:
		push_warning("TaxiHorn: %s did not load; the taxi has no horn" % TrafficSystem.HORN_PATH)
		return
	_voice = AudioStreamPlayer3D.new()
	_voice.stream = stream
	# Deferred: the scene is still adding its children, and the car is a sibling.
	vehicle.add_child.call_deferred(_voice)


func _physics_process(_delta: float) -> void:
	hold(_input != null and bool(_input.horn))


## The button's state this tick: a press sounds once, however long it is held.
func hold(down: bool) -> void:
	var pressed: bool = down and not _held
	_held = down
	if not pressed:
		return
	var controller := vehicle as VehicleController
	if controller != null and controller.parked:
		return
	presses += 1
	if _voice != null and _voice.is_inside_tree():
		_voice.play()
