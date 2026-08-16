class_name WheelVisual
extends Node3D
## The visible wheel at one hardpoint.
##
## Reads WheelMount's published simulation state and moves the mesh to match.
## It writes nothing back: the physics is a raycast model that never consults a
## mesh, so everything here is presentation and cannot change how the car
## drives. That separation is what keeps P0-5's tuning valid whatever this does.

## One km/h in metres per second, folded into _roll_per_kph so the per-tick
## path neither converts nor divides.
const KPH_TO_MS: float = 1.0 / 3.6

var _mount: WheelMount = null
var _controller: VehicleController = null
var _rest_y: float = 0.0
var _roll_per_kph: float = 0.0
var _steers: bool = false
var _roll_angle: float = 0.0


func _ready() -> void:
	_mount = get_parent() as WheelMount
	assert(_mount != null, "WheelVisual must be a child of a WheelMount.")
	_controller = VehicleController.above(_mount)
	assert(_controller != null, "WheelVisual found no VehicleController above its mount.")

	_steers = _mount.steers
	# Read from the profile rather than from this node's authored position. The
	# rest length is a tuning value; a mesh holding its own copy hovers or sinks
	# the moment the spring is retuned, with the physics unchanged, and the
	# scene/profile guard in test_make_vehicle.py only watches the mounts.
	_rest_y = -_controller.profile.suspension_rest_length_m
	if _controller.profile.wheel_radius_m > 0.0:
		_roll_per_kph = KPH_TO_MS / _controller.profile.wheel_radius_m


func _physics_process(delta: float) -> void:
	# Rolled from road speed rather than from wheel torque: this is a raycast
	# car with no simulated wheel spin, so there is no angular velocity to read.
	# The visible consequence is that the wheels neither spin up under wheelspin
	# nor lock under braking — lies a blob of geometry at 60 km/h does not sell
	# either way.
	_roll_angle = wrapf(_roll_angle + _controller.speed_kph * _roll_per_kph * delta, 0.0, TAU)

	# Steer first, then roll: the roll axis is the axle, and the axle is what
	# steering turns. Composed the other way the wheel wobbles rather than
	# steers. The rear pair skips the yaw entirely — its angle is always zero.
	var spin := Basis(Vector3.RIGHT, _roll_angle)
	if _steers:
		spin = Basis(Vector3.UP, _mount.steer_angle) * spin

	# One assignment rather than a position write and a basis write. Each
	# Node3D transform setter propagates a notification to this node's mesh
	# child, and setting them separately pays that twice a tick per wheel.
	transform = Transform3D(spin, Vector3(0.0, _rest_y + _mount.compression, 0.0))
