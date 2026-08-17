class_name VehicleController
extends RigidBody3D
## Arcade raycast vehicle. Every number comes from HandlingProfile.
##
## Not Godot's VehicleBody3D — P0-5a measured why (docs/DECISIONS.md). The short
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
## Steering as a signed fraction of the lock available at this speed: -1.0 is
## full left, +1.0 is full right.
##
## Published because the indicators need to know the car is turning, and it has
## to be a *ratio*: lock runs from steer_angle_max_deg at rest to
## steer_angle_at_top_deg near the limiter, so one threshold in degrees means
## "a nudge" parked and "everything the car has" at speed.
##
## ⚠️ Sign follows InputRouter.steer, not _steer_angle. The physics angle is
## negated on the way in — a positive rotation about +Y turns -Z forward toward
## -X, which is left — and a lamp rig reading the raw angle would flash the
## indicator on the wrong side of the car, which looks like a working feature.
var steer_ratio: float = 0.0
var _upside_down_for: float = 0.0
## Recomputed once per tick rather than per wheel — they are identical across
## the four, and the steered pair differs only by the steering rotation.
##
## `speed_kph` is public for the same reason it is cached: everything that wants
## the car's speed wants the same number in the same tick, and
## forward_speed_kph() recomputes a dot product each time it is asked.
var speed_kph: float = 0.0
## The brake/reverse pedal, sampled once per tick.
##
## ⚠️ **Cached so that this controller is the only thing on the car that reads
## InputRouter**, which is what makes "the lamps read the car" true rather than
## nearly true: `is_braking()` reading the autoload directly would report the
## *player's* pedal for every vehicle sharing this script, and the roster puts
## an AI taxi on it. Swapping this field for an AI's own intent is then the whole
## of what a driven car needs — nothing downstream asks where it came from.
var brake_input: float = 0.0
## The handbrake button, sampled once per tick. Cached for both reasons
## `brake_input` is: an AI taxi on this script must not read the *player's*
## handbrake, and the alternative was four autoload lookups a tick — `InputRouter`
## has no `class_name`, so those cannot compile to a validated getter the way the
## typed `profile` reads do.
var drift_input: bool = false
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


## The controller above a node, or null.
##
## Climbs rather than taking get_parent(), because a suspension pivot or a
## re-parented mesh between the two is legal — VehicleController collects its
## own mounts with a recursive find_children — and a fixed one-step walk
## dereferences null the moment anything is interposed.
##
## ⚠️ Not first_in(): that is a group lookup returning whichever car is first,
## which is right for a dev overlay and wrong for anything that belongs to *this*
## car. A lamp rig using it would light the wrong vehicle.
static func above(node: Node) -> VehicleController:
	var walk: Node = node
	while walk != null:
		var controller := walk as VehicleController
		if controller != null:
			return controller
		walk = walk.get_parent()
	return null


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
	brake_input = InputRouter.brake_reverse
	drift_input = InputRouter.drift
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


## True while the brake/reverse pedal is slowing the car rather than backing it.
##
## ⚠️ **One pedal serves both, and the split is a rule, not an input.** Which of
## the two the driver gets depends on the car's own speed, so anything that
## re-derives it from the pedal alone is a second copy that drifts the first time
## STATIONARY_KPH moves. _longitudinal_force() reads these, so there is exactly
## one statement of the rule and the brake lamp is on precisely when the brakes
## are. ⚠️ builtin_vehicle_controller.gd is the one copy that remains, and it is
## the rejected P0-5a spike rather than a car anything ships.
func is_braking() -> bool:
	return not is_zero_approx(brake_input) and speed_kph > STATIONARY_KPH


## True while the pedal is driving the car backwards. See is_braking().
##
## Covers reversing at speed as well as pulling away from rest: once the car is
## moving backwards speed_kph is negative, so it stays below STATIONARY_KPH and
## the pedal keeps meaning reverse until it is released.
func is_reversing() -> bool:
	return not is_zero_approx(brake_input) and speed_kph <= STATIONARY_KPH


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
	# Guarded because max_angle is a profile value and an unassigned resource
	# reads as all-zeroes — the same case the asserts in _ready cover for the
	# two that would fail loudly. This one would only ever produce a NAN in a
	# lamp, so it is handled rather than asserted.
	steer_ratio = -_steer_angle / max_angle if max_angle > 0.0 else 0.0


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


## Where the arcade model lives. One friction budget per tyre, shaped as an
## ellipse: lateral and longitudinal keep their own limits, but they are spent
## from the same purse.
##
## ⚠️ **An ellipse is not the isotropic circle `P0-5a` rejected, and the
## difference is the whole argument.** `VehicleWheel3D` has a single
## `friction_slip`, so its budget is a *circle* — `grip_lateral` and
## `grip_longitudinal` collapse into each other and a drift cannot break sideways
## grip without taking traction and braking with it. Here the semi-axes stay
## separate, so the two dials still mean what they say. What is new is the
## coupling between them, which is the part real tyres have and this model did
## not: until now a car could brake at 0.8 g through full lock and lose no
## cornering grip whatsoever, because the two clamps never spoke to each other.
##
## The drift falls out of that rather than being a case in it — see
## `_locked_tyre_force`.
func _apply_tyre_forces(
	wheel: WheelMount, offset: Vector3, point_velocity: Vector3, load: float, delta: float
) -> void:
	var forward: Vector3 = _steered_forward if wheel.steers else _forward
	var right: Vector3 = _steered_right if wheel.steers else _right

	var lateral_cap: float = profile.grip_lateral * load
	var longitudinal_cap: float = profile.grip_longitudinal * load
	# ⚠️ An unloaded tyre has no friction budget at all, and every division below —
	# here and in _locked_tyre_force, which trusts this guard rather than repeating
	# it — has one of these underneath. Reached in normal driving, not just in the
	# degenerate case: load goes to zero on the inside wheels of a hard corner.
	#
	# ⚠️ It also swallows a profile with grip_lateral or grip_longitudinal at zero,
	# which is legal and would silently take *both* axes out — no drive, no brakes,
	# no assert. Nobody ships that, but this early return means more than
	# "the wheel is in the air".
	if lateral_cap <= 0.0 or longitudinal_cap <= 0.0:
		return

	var along: float = point_velocity.dot(forward)
	var across: float = point_velocity.dot(right)

	# Force that would cancel all sideways slip this tick. Dividing by delta is
	# right here: cancelling velocity v needs impulse m·v, and apply_force
	# delivers F·delta.
	var lateral: float = -across * _corner_mass / delta
	var longitudinal: float = _longitudinal_force(wheel, along, delta)

	# How much of the tyre is being asked for, as a fraction of the ellipse. Both
	# demands are scaled by the same factor when it exceeds 1, so the direction of
	# the force the tyre wanted survives and only its magnitude is limited —
	# clamping the two axes separately would bend it toward whichever saturated.
	#
	# Squared first: the root is only needed to divide by, so an unsaturated tyre —
	# which is most tyres on most ticks — never pays for one.
	var share := Vector2(lateral / lateral_cap, longitudinal / longitudinal_cap)
	if share.length_squared() > 1.0:
		var demand: float = share.length()
		lateral /= demand
		longitudinal /= demand
	var rolling: Vector3 = right * lateral + forward * longitudinal

	# The handbrake acts on the rear axle, and `is_front` is derived from chassis
	# geometry rather than from `drives` — so this stays the rear axle on the
	# front-wheel-drive Crown too (ARCHITECTURE.md, "drift bias").
	if not drift_input or wheel.is_front:
		apply_force(rolling, offset)
		return

	# Composed here from the same forward/right pair the rolling branch uses, so
	# the lerp blends like against like rather than two differently-built vectors.
	var locked := _locked_tyre_force(along, across, lateral_cap, longitudinal_cap, delta)
	apply_force(rolling.lerp(forward * locked.x + right * locked.y, profile.handbrake_lock), offset)


## What the rear tyre would do if the handbrake had locked it solid.
##
## ⚠️ **Nothing here reduces grip, and that is the whole mechanism.** A locked
## tyre is not rolling, so it has no preferred direction: its friction opposes
## the entire contact-patch velocity as one vector. At 60 kph with a few degrees
## of slip that vector points almost straight backwards, so the *lateral*
## component is what collapses — on its own, out of the geometry, with no drift
## multiplier anywhere in it. The two fields this replaced, `drift_grip_scale`
## and `drift_front_grip_scale`, were that result modelled without its cause,
## which is why one of them had to soften the *front* axle for a manoeuvre that
## does nothing to the front axle.
##
## ⚠️ **Measured, a fully locked rear axle spins this car, and no value of any
## dial prevents it.** Held at full lock from 62.8 kph the slip angle reached
## **162°** — the number `P0-5a` recorded for the *rejected* `VehicleBody3D` and
## called a full spin rather than a slide — and *lowering* the handbrake's grip
## made it worse, not better, because this force is the only thing resisting yaw
## once the tail is loose. A 0.5 s tap span it too. That is not a bug in the
## model; a real car at full lock with the rear axle locked really does spin.
## What it is, is incompatible with `GAME_DESIGN.md`'s "easy to hold" — so the
## caller blends this with the rolling force rather than switching to it, and
## `handbrake_lock` is how far the lever was pulled. The full-lock spin is still
## in here, reachable at 1.0, and the sweep in `docs/DECISIONS.md` is why the
## shipped value is not.
##
## Takes the slip already resolved onto the wheel's axes, and returns its force
## the same way — `x` along `forward`, `y` along `right` — so the caller composes
## both branches from one pair of basis vectors.
##
## ⚠️ Both caps must be positive. This does not re-check them; `_apply_tyre_forces`
## returns early on an unloaded tyre and that guard is the only thing standing
## between these divisions and a zero.
func _locked_tyre_force(
	along: float, across: float, lateral_cap: float, longitudinal_cap: float, delta: float
) -> Vector2:
	# The same ellipse, read as a radius along the slip direction rather than as a
	# budget split between two axes. A sliding tyre is still a tyre: it is no more
	# isotropic than a rolling one, and capping this at the longitudinal figure
	# alone would quietly hand the drift a circle after all.
	var reach: float = Vector2(along / longitudinal_cap, across / lateral_cap).length()
	# Zero only when the tyre is not sliding at all, both caps being positive.
	if is_zero_approx(reach):
		return Vector2.ZERO

	# ⚠️ The slip speed cancels and is deliberately never computed. Friction here is
	# `-slip/|slip| × limit`, and `limit` is itself proportional to `|slip|`, so the
	# two divide out and what is left scales the slip components directly. Writing
	# it the long way costs a length() and two divisions to reach the same number.
	var limit: float = 1.0 / reach
	# Capped at the force that exactly cancels the slip this tick, the same guard
	# rolling resistance needs and for the same reason: an uncapped friction does
	# not stop a sliding tyre, it reverses it and then holds it reversed.
	# Not `scale`: that shadows Node3D's own property, which project.godot promotes
	# to an error.
	var gain: float = minf(limit, _corner_mass / delta)
	return Vector2(-along * gain, -across * gain)


func _longitudinal_force(wheel: WheelMount, rolling_speed: float, delta: float) -> float:
	var throttle: float = InputRouter.accelerate
	var brake: float = brake_input

	# Coasting: bleed rolling speed so the car settles instead of gliding for
	# ever. Two terms, and the car only settles because of the second — the
	# viscous one is proportional to speed, so it approaches zero as fast as the
	# speed it is removing and never arrives. Neither term is divided by delta:
	# apply_force already integrates over the tick, so dividing would make the
	# drag framerate-dependent as well as enormous. The cap below is the one
	# place delta belongs, and for the opposite reason — it turns a speed into
	# the deceleration that cancels exactly that speed in one tick.
	if is_zero_approx(throttle) and is_zero_approx(brake):
		var decel: float = (
			rolling_speed * profile.coast_drag_per_s
			+ signf(rolling_speed) * profile.rolling_resistance_mps2
		)
		# ⚠️ Capped at the deceleration that lands exactly on zero this tick —
		# the same v/delta the lateral force asks for, used here as the limit
		# rather than the demand. The viscous term cannot overshoot; the constant
		# one can, and an uncapped rolling resistance does not stop a rolling car
		# — it reverses it, and then holds it reversing.
		var decel_to_rest: float = absf(rolling_speed) / delta
		return -_corner_mass * clampf(decel, -decel_to_rest, decel_to_rest)

	if not is_zero_approx(brake):
		if is_braking():
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
	# Published state as well as private, or a car righted at full lock is
	# replaced pointing straight ahead with its indicator still flashing.
	steer_ratio = 0.0
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
