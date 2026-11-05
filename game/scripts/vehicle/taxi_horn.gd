class_name TaxiHorn
extends Node
## The taxi's own horn (`Q178`): the taxi kind's horn (`P3-79`), from the car,
## at the file's own pitch, sounding for as long as `horn` is held. The traffic's
## horns play patterns; this one is the player's thumb, so it is never rolled.
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
## The press's level, ramped over `TrafficSystem.HORN_DECLICK_S` either way.
var _level: float = 0.0


func _ready() -> void:
	_input = get_node_or_null(input_path)
	if vehicle == null:
		push_warning("TaxiHorn has no vehicle assigned; the taxi has no horn.")
		return
	var stream: AudioStream = TrafficSystem.horn_stream("taxi")
	if stream == null:
		return
	_voice = AudioStreamPlayer3D.new()
	_voice.stream = stream
	_voice.bus = &"SFX"
	# Deferred: the scene is still adding its children, and the car is a sibling.
	vehicle.add_child.call_deferred(_voice)


func _physics_process(delta: float) -> void:
	hold(_input != null and bool(_input.horn))
	_ramp(delta)


## The button's state this tick: a press counts once, however long it is held,
## and sounds until it is let go.
func hold(down: bool) -> void:
	var controller := vehicle as VehicleController
	if controller != null and controller.parked:
		down = false
	var pressed: bool = down and not _held
	_held = down
	if not pressed:
		return
	presses += 1
	if _voice != null and _voice.is_inside_tree() and not _voice.playing:
		_voice.volume_db = linear_to_db(0.0)
		_voice.play()


func _ramp(delta: float) -> void:
	if _voice == null or not _voice.playing:
		return
	_level = move_toward(_level, 1.0 if _held else 0.0, delta / TrafficSystem.HORN_DECLICK_S)
	if _level <= 0.0 and not _held:
		_voice.stop()
		return
	_voice.volume_db = linear_to_db(_level)
