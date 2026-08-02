class_name VehicleController
extends RigidBody3D
## Arcade raycast vehicle. Every number comes from HandlingProfile.
##
## Not Godot's VehicleBody3D — P0-5a measured why (docs/PROGRESS.md). The short
## version: VehicleWheel3D's friction is isotropic, so it cannot express a drift
## that breaks lateral grip while keeping traction. That separation is the whole
## point of this file, and it lives in _apply_tyre_forces().
##
## Model, per wheel, per physics tick:
##   1. Raycast down from the hardpoint. No hit means airborne, no forces.
##   2. Spring + damper along the suspension axis, sized from natural frequency.
##   3. Tyre forces at the contact patch, each capped at coefficient × load.
## Then anti-roll across each axle, and chassis-level speed and righting limits.

## Below this speed the car is treated as stationary for reverse and slip.
const STATIONARY_KPH: float = 1.0
## A surface normal flatter than this is a wall, not a road. Used both to reject
## wall hits as ground contact and to classify collisions.
const WALL_NORMAL_Y: float = 0.5
## Body-up alignment below which the car counts as overturned.
const OVERTURNED_DOT: float = 0.1
## Clearance given to a righted car so it does not respawn inside whatever it
## came to rest against.
const RIGHTING_LIFT_M: float = 1.5
## Spin retained after a wall scrape. A glancing hit must never take control.
const SCRAPE_SPIN_RETAINED: float = 0.5
## Fraction of top speed over which drive force eases to zero. Shapes the
## approach to max_speed_kph rather than setting it, so it stays a structural
## constant while the speed itself remains a profile dial.
const TOP_SPEED_TAPER: float = 0.15

## Group every controller joins, so a dev tool can find the car without walking
## the tree. See first_in().
const GROUP: StringName = &"vehicle"

@export var profile: HandlingProfile

var _wheels: Array[WheelMount] = []
## Wheels grouped into axles once, so the anti-roll bar is a flat loop over
## pairs rather than a float comparison rediscovering the layout every tick.
var _axles: Array[Array] = []

var _spring_k: float = 0.0
var _damper_c: float = 0.0
var _corner_mass: float = 0.0
var _ray_length: float = 0.0

var _steer_angle: float = 0.0
var _upside_down_for: float = 0.0
## Recomputed once per tick rather than per wheel — they are identical across
## the four, and the steered pair differs only by the steering rotation.
##
## `speed_kph` is public for the same reason it is cached: everything that wants
## the car's speed wants the same number in the same tick, and
## forward_speed_kph() recomputes a dot product each time it is asked.
var speed_kph: float = 0.0
var _forward: Vector3 = Vector3.FORWARD
var _right: Vector3 = Vector3.RIGHT
var _steered_forward: Vector3 = Vector3.FORWARD
var _steered_right: Vector3 = Vector3.RIGHT
var _ray_query := PhysicsRayQueryParameters3D.new()


## The car in a scene, or null. For dev tools that are dropped into a scene and
## have to find it themselves rather than being pointed at it.
##
## A group rather than find_children(): two overlays were each walking the whole
## tree for this, and DebugHud repeats its search for as long as it comes back
## empty — which in a preview scene, where a car can never appear, is for ever.
static func first_in(tree: SceneTree) -> VehicleController:
	return tree.get_first_node_in_group(GROUP) as VehicleController


func _ready() -> void:
	add_to_group(GROUP)
	assert(profile != null, "VehicleController has no HandlingProfile assigned.")
	# The profile deliberately ships no defaults, so an unassigned resource reads
	# as all-zeroes. These two would fail as a divide-by-zero and a dead spring
	# respectively, which is worth catching here rather than in the physics.
	assert(profile.wheel_radius_m > 0.0, "HandlingProfile.wheel_radius_m is zero.")
	assert(
		profile.suspension_frequency_hz > 0.0, "HandlingProfile.suspension_frequency_hz is zero."
	)

	for child: Node in find_children("*", "WheelMount", true, false):
		_wheels.append(child as WheelMount)
	assert(not _wheels.is_empty(), "VehicleController found no WheelMount children.")

	_group_axles()
	_cache_derived()

	gravity_scale = profile.gravity_scale
	center_of_mass_mode = RigidBody3D.CENTER_OF_MASS_MODE_CUSTOM
	center_of_mass = Vector3(0.0, profile.centre_of_mass_offset_y, 0.0)
	contact_monitor = true
	max_contacts_reported = 8
	can_sleep = false
	_ray_query.exclude = [get_rid()]


## Everything derived from mass and the profile. One function, so a live-tuning
## hook has a single place to call when either changes.
func _cache_derived() -> void:
	_corner_mass = mass / float(_wheels.size())
	var omega: float = TAU * profile.suspension_frequency_hz
	_spring_k = _corner_mass * omega * omega
	_damper_c = 2.0 * profile.suspension_damping_ratio * _corner_mass * omega
	_ray_length = profile.ray_length_m()


## Pairs wheels sharing a local z. Done once because the layout is fixed after
## _ready, and because warning here beats silently applying no anti-roll to an
## axle whose wheels failed a float comparison.
func _group_axles() -> void:
	var by_z: Dictionary = {}
	for wheel: WheelMount in _wheels:
		var key: float = snappedf(wheel.position.z, 0.001)
		if not by_z.has(key):
			by_z[key] = []
		by_z[key].append(wheel)
	for axle: Array in by_z.values():
		if axle.size() == 2:
			_axles.append(axle)
		else:
			push_warning(
				"VehicleController: axle with %d wheels gets no anti-roll bar." % axle.size()
			)
	# -Z is forward, so the forward axle has the smallest z.
	var mean_z: float = 0.0
	for wheel: WheelMount in _wheels:
		mean_z += wheel.position.z
	mean_z /= float(_wheels.size())
	for wheel: WheelMount in _wheels:
		wheel.is_front = wheel.position.z < mean_z


func _physics_process(delta: float) -> void:
	# Before any force is queued: righting the car this tick would otherwise land
	# it and then integrate forces computed for the pose it no longer has.
	if _apply_auto_right(delta):
		return

	speed_kph = forward_speed_kph()
	_update_steering(delta)
	_forward = -global_basis.z
	_right = global_basis.x
	_steered_forward = _forward.rotated(global_basis.y, _steer_angle)
	_steered_right = _right.rotated(global_basis.y, _steer_angle)

	var space: PhysicsDirectSpaceState3D = get_world_3d().direct_space_state
	for wheel: WheelMount in _wheels:
		wheel.steer_angle = _steer_angle if wheel.steers else 0.0
		_simulate_wheel(wheel, space, delta)
	_apply_anti_roll()


## Signed forward speed in km/h. Negative when reversing.
func forward_speed_kph() -> float:
	return linear_velocity.dot(-global_basis.z) * 3.6


func _update_steering(delta: float) -> void:
	var speed_ratio: float = clampf(absf(speed_kph) / profile.max_speed_kph, 0.0, 1.0)
	var max_angle: float = deg_to_rad(
		lerpf(profile.steer_angle_max_deg, profile.steer_angle_at_top_deg, speed_ratio)
	)
	# Negated: InputRouter.steer is +1 for right, but a positive rotation about
	# +Y turns the -Z forward vector toward -X, which is left.
	var target: float = -InputRouter.steer * max_angle
	# Returning to centre is quicker than reaching lock, so the car feels like it
	# wants to straighten. Rate is expressed as full-lock-per-second.
	var seconds: float = (
		profile.steer_attack_s if absf(target) > absf(_steer_angle) else profile.steer_release_s
	)
	_steer_angle = move_toward(_steer_angle, target, (max_angle / seconds) * delta)


func _simulate_wheel(wheel: WheelMount, space: PhysicsDirectSpaceState3D, delta: float) -> void:
	var origin: Vector3 = wheel.global_position
	var up: Vector3 = global_basis.y
	_ray_query.from = origin
	_ray_query.to = origin - up * _ray_length
	var hit: Dictionary = space.intersect_ray(_ray_query)

	# A wall face is not ground. Without this a car pitched against a building
	# takes full spring load and full grip off a vertical surface — free traction
	# and a launch ramp.
	if hit.is_empty() or (hit["normal"] as Vector3).y < WALL_NORMAL_Y:
		wheel.grounded = false
		wheel.compression = 0.0
		return

	var contact: Vector3 = hit["position"]
	var offset: Vector3 = contact - global_position
	wheel.grounded = true
	wheel.compression = clampf(
		_ray_length - origin.distance_to(contact), 0.0, profile.suspension_travel_m
	)

	var point_velocity: Vector3 = linear_velocity + angular_velocity.cross(offset)
	# Subtracting the damper is correct: a compressing wheel gives a negative
	# point_velocity·up, so this ADDS force. Adding it would be negative damping.
	var load: float = maxf(_spring_k * wheel.compression - _damper_c * point_velocity.dot(up), 0.0)
	apply_force(up * load, offset)

	_apply_tyre_forces(wheel, offset, point_velocity, load, delta)


## Where the arcade model lives. Lateral and longitudinal grip are capped
## independently, so drifting breaks sideways grip while leaving traction and
## braking untouched — the thing VehicleBody3D's single friction value could not
## express.
func _apply_tyre_forces(
	wheel: WheelMount, offset: Vector3, point_velocity: Vector3, load: float, delta: float
) -> void:
	var forward: Vector3 = _steered_forward if wheel.steers else _forward
	var right: Vector3 = _steered_right if wheel.steers else _right

	# Biased by axle, not uniform. Equal scaling can only produce a four-wheel
	# slide; the rear has to let go while the front keeps enough grip to point
	# the car, or the drift ploughs wide instead of rotating.
	var lateral_grip: float = profile.grip_lateral
	if InputRouter.drift:
		lateral_grip *= (
			profile.drift_front_grip_scale if wheel.is_front else profile.drift_grip_scale
		)

	# Force that would cancel all sideways slip this tick, capped by grip.
	# Dividing by delta is right here: cancelling velocity v needs impulse m·v,
	# and apply_force delivers F·delta.
	var lateral_speed: float = point_velocity.dot(right)
	var lateral_force: float = clampf(
		-lateral_speed * _corner_mass / delta, -lateral_grip * load, lateral_grip * load
	)
	apply_force(right * lateral_force, offset)

	var drive: float = _longitudinal_force(wheel, point_velocity.dot(forward))
	var traction_cap: float = profile.grip_longitudinal * load
	apply_force(forward * clampf(drive, -traction_cap, traction_cap), offset)


func _longitudinal_force(wheel: WheelMount, rolling_speed: float) -> float:
	var throttle: float = InputRouter.accelerate
	var brake: float = InputRouter.brake_reverse

	# Coasting: bleed rolling speed so the car settles instead of gliding for
	# ever. No delta — apply_force already integrates over the tick, and dividing
	# by it would make the drag framerate-dependent as well as enormous.
	if is_zero_approx(throttle) and is_zero_approx(brake):
		return -rolling_speed * _corner_mass * profile.coast_drag_per_s

	if not is_zero_approx(brake):
		if speed_kph > STATIONARY_KPH:
			# Braking acts on every wheel; drive does not.
			return -signf(rolling_speed) * profile.brake_force * brake
		if wheel.drives and speed_kph > -profile.max_reverse_kph:
			return -profile.engine_force * brake
		return 0.0

	if not wheel.drives:
		return 0.0
	# Ease off approaching top speed. A hard cutoff flips drive force between
	# full and zero tick to tick, which reads as a judder — and the louder the
	# more engine force there is.
	var headroom: float = (
		(profile.max_speed_kph - speed_kph) / (profile.max_speed_kph * TOP_SPEED_TAPER)
	)
	return profile.engine_force * throttle * clampf(headroom, 0.0, 1.0)


## Opposes body roll by transferring load across each axle. Without this the car
## rolls over on hard cornering even with the centre of mass dropped.
func _apply_anti_roll() -> void:
	if is_zero_approx(profile.anti_roll):
		return
	var stiffness: float = _spring_k * profile.anti_roll
	var up: Vector3 = global_basis.y
	var origin: Vector3 = global_position
	for axle: Array in _axles:
		var a: WheelMount = axle[0]
		var b: WheelMount = axle[1]
		if not (a.grounded or b.grounded):
			continue
		# Inverting these amplifies roll rather than resisting it, which reads as
		# the car flipping itself on the first hard corner.
		var transfer: float = (a.compression - b.compression) * stiffness
		apply_force(up * transfer, a.global_position - origin)
		apply_force(up * -transfer, b.global_position - origin)


## Returns true if the car was righted this tick, so the caller can skip queuing
## forces derived from the pose it no longer has.
func _apply_auto_right(delta: float) -> bool:
	if global_basis.y.dot(Vector3.UP) > OVERTURNED_DOT:
		_upside_down_for = 0.0
		return false
	_upside_down_for += delta
	if _upside_down_for < profile.auto_right_delay_s:
		return false
	# Keep heading, discard roll and pitch.
	var heading: float = global_rotation.y
	place_at(
		Transform3D(Basis(Vector3.UP, heading), global_position + Vector3.UP * RIGHTING_LIFT_M)
	)
	return true


## Put the car somewhere and leave it in a state it can be driven from.
##
## The transform is the easy half. Momentum has to go with it — a body moved
## while it still holds the speed of a long fall carries that straight into
## whatever it lands on — and so does the simulation state this controller
## caches, which nothing outside it can reach: a car that fell at full steering
## lock would otherwise be replaced at full lock and veer off immediately, and
## the wheels would spend a tick loaded against ground they are no longer near.
func place_at(pose: Transform3D) -> void:
	global_transform = pose
	linear_velocity = Vector3.ZERO
	angular_velocity = Vector3.ZERO
	_steer_angle = 0.0
	_upside_down_for = 0.0
	for wheel: WheelMount in _wheels:
		wheel.compression = 0.0
		wheel.grounded = false
		wheel.steer_angle = 0.0


## Arcade collision response: glancing hits slide, head-on hits cost speed but
## never control. Godot's own restitution would bounce and spin the car instead.
func _integrate_forces(state: PhysicsDirectBodyState3D) -> void:
	for i: int in state.get_contact_count():
		var normal: Vector3 = state.get_contact_local_normal(i)
		if absf(normal.y) > WALL_NORMAL_Y:
			continue  # road surface, handled by the suspension
		var velocity: Vector3 = state.linear_velocity
		if velocity.length() < 1.0:
			continue
		var into_wall: float = velocity.normalized().dot(normal)
		if into_wall > 0.0:
			continue  # already moving away
		var retained: float = lerpf(1.0, profile.collision_speed_retained, absf(into_wall))
		state.linear_velocity = (
			velocity.slide(normal) * lerpf(retained, 1.0, profile.collision_deflection)
		)
		state.angular_velocity *= SCRAPE_SPIN_RETAINED
