class_name VehicleController
extends VehicleBody3D
## Arcade vehicle on Godot's VehicleBody3D. Every number comes from HandlingProfile.
##
## ⚠️ **This is P0-5a reversed, and the reversal is Q50.** Until 2026-08-18 this
## was a hand-rolled raycast car on RigidBody3D, kept because VehicleWheel3D's
## friction is isotropic and so cannot express a drift that breaks lateral grip
## while keeping traction. That is still true — nothing about it was disproved.
## The engine model is shipping anyway, at the user's explicit instruction, and
## docs/DECISIONS.md Q50 records what it costs.
##
## What the engine now owns, and this file no longer does: the suspension ray,
## the spring and damper, the tyre friction budget, and the wheel visual's
## position, roll and steer. `_apply_tyre_forces`, `_locked_tyre_force`,
## `_simulate_wheel`, `_apply_anti_roll`, `wheel_mount.gd` and `wheel_visual.gd`
## all went with them.
##
## What this file still owns, because VehicleBody3D has none of it:
##   1. Steering rate-limiting, and the speed-dependent lock it ramps toward.
##   2. The top-speed taper — Godot has no speed limiter.
##   3. Coast drag and rolling resistance — Godot has no engine braking.
##   4. The drift button's ramp, which the tyre model's side cut reads.
##   5. Arcade collision response, in _integrate_forces.
##   6. Auto-righting.
##
## ⚠️ It also still owns **which axle is which**. See _group_axles.

## Below this speed the car is treated as stationary for reverse and slip.
const STATIONARY_KPH: float = 1.0
## A surface normal flatter than this is a wall, not a road. Used to classify
## collisions in _integrate_forces.
const WALL_NORMAL_Y: float = 0.5
## Body-up alignment below which the car counts as overturned.
const OVERTURNED_DOT: float = 0.1
## Clearance given to a righted car so it does not respawn inside whatever it
## came to rest against.
const RIGHTING_LIFT_M: float = 1.5
## Spin retained after a wall scrape. A glancing hit must never take control.
const SCRAPE_SPIN_RETAINED: float = 0.5
## The hardest wall contact since the last `take_impact_mps`, as the speed
## INTO the wall in m/s — the pre-slide velocity's component along the
## contact normal, the one number the tiers of `P3-50`'s penalty are read off.
## Read before the slide rewrites the velocity, so it is the hit and not what
## the arcade response left of it. 0 between contacts; a contact under the
## 1 m/s floor in `_integrate_forces` never sets it, so a car pushing on a
## wall from rest reads nothing.
##
## ⚠️ Read against `_velocity_into_step`, never `state.linear_velocity`: the
## contacts `_integrate_forces` sees are the step's, and by then the solver
## has already taken the normal velocity out — measured, a 69.5 kph head-on
## on the skidpad read 1.6 kph off the state, and a 30° hit read nothing at
## all because the state was already separating. The arcade slide below it
## reads the same velocity for the same reason (`Q151`).
var _impact_mps: float = 0.0
## The velocity the car carried into this step: `linear_velocity` at the end
## of `_physics_process`, before the server moves anything.
var _velocity_into_step: Vector3 = Vector3.ZERO
## What the last `take_impact_mps` handed over, kept for a reader that must
## not drain the latch — `driver.gd`'s trace, which is how a kerb was shown
## to read nothing (`Q148`). Never read by the game.
var last_impact_mps: float = 0.0
## Fraction of top speed over which drive force eases to zero. Shapes the
## approach to max_speed_kph rather than setting it, so it stays a structural
## constant while the speed itself remains a profile dial.
const TOP_SPEED_TAPER: float = 0.15

## Sea-level air, kg/m³: a constant of the world, not a dial on the car.
const AIR_DENSITY_KG_M3: float = 1.2

## Rebound is damped harder than bump, which is ordinary vehicle practice and is
## why one suspension_damping_ratio becomes Godot's two numbers.
const RELAXATION_OVER_COMPRESSION: float = 1.2

## ⚠️ **Positive engine_force drives this rig backwards.** Godot resolves a
## wheel's forward axis from the wheel node's own basis rather than from a global
## convention, so this sign belongs to taxi.tscn's wheel transforms and not to
## the engine. Measured by driving (commit 84bc822: positive gave -82 kph with
## slip pinned at 179.9°); re-measure by driving if those transforms ever change,
## because nothing else will catch it.
const DRIVE_SIGN: float = -1.0

## Group every controller joins, so a dev tool can find the car without walking
## the tree. See first_in().
const GROUP: StringName = &"vehicle"

@export var profile: HandlingProfile

## Where the player's intent comes from, resolved once in `_ready`.
##
## A `NodePath` defaulting to the `InputRouter` autoload rather than the global
## name (`Q119`). Naming an autoload is a compile-time dependency: this script
## failed to compile — and GDScript cached the broken class — anywhere the
## autoload was not registered yet, which is every `--script` tool until its
## first frame. Resolved by path it is a runtime lookup, the shape
## `vehicle_lamps.gd::_budget` already uses for `BeamBudget`, and a scene with
## no router is a car with no pedals rather than a car with no script.
## Duck-typed on purpose: `InputRouter` has no `class_name`, for the same reason.
@export var input_path: NodePath = ^"/root/InputRouter"

## The rig's key light, handed in by the scene that owns the rig (`P5-24`):
## `city_drive.tscn`, the skidpad and the grey box each point it at their own
## `Sun`. The glint and the lamps read it from here rather than searching the
## window for a `DirectionalLight3D`, which is what the guide calls a sibling
## reaching past its own hierarchy. Null is "no rig" — a verify tool or an
## import loads the car alone — and both consumers treat that as no daylight
## to be in or out of, not as night.
@export var sun: DirectionalLight3D

## Split by chassis geometry once, because the drift scales the two axles
## differently, and every per-wheel write goes through one or the other. See
## _group_axles for why this is not `use_as_traction`.
var _front: Array[VehicleWheel3D] = []
## The resolved `input_path`, or null. See `_physics_process`.
var _input: Node = null
var _rear: Array[VehicleWheel3D] = []
## How far behind the centre of mass the rear axle sits, in metres.
var _rear_axle_behind_m: float = 0.0

## Steering as a signed fraction of the lock available at this speed: -1.0 is
## full left, +1.0 is full right.
##
## Published because the indicators need to know the car is turning, and it has
## to be a *ratio*: lock runs from steer_angle_max_deg at rest to
## steer_angle_at_top_deg near the limiter, so one threshold in degrees means
## "a nudge" parked and "everything the car has" at speed.
##
## ⚠️ Sign follows `steer_input`, not `steering`. The physics angle is
## negated on the way in — a positive rotation about +Y turns -Z forward toward
## -X, which is left — and a lamp rig reading the raw angle would flash the
## indicator on the wrong side of the car, which looks like a working feature.
var steer_ratio: float = 0.0
var _upside_down_for: float = 0.0
## How far the drift button's ramp has engaged, 0 off to 1 fully in.
##
## Private, and there is no public mirror. `drift_input` is the player's intent
## and this is the car's answer to it; a HUD or lamp wanting to show "drifting"
## wants the intent, which is already published. ⚠️ It is deliberately **not** in
## `InputRouter` — see `drift_release_s` in handling_profile.gd for why, kept in
## one place so the two cannot drift apart.
var _drift_engagement: float = 0.0
## Recomputed once per tick rather than per reader.
##
## `speed_kph` is public for the same reason it is cached: everything that wants
## the car's speed wants the same number in the same tick, and
## forward_speed_kph() recomputes a dot product each time it is asked.
var speed_kph: float = 0.0
## The brake/reverse pedal, sampled once per tick.
##
## ⚠️ **Cached so that this controller is the only thing on the car that reads
## the router**, which is what makes "the lamps read the car" true rather than
## nearly true: `is_braking()` reading the autoload directly would report the
## *player's* pedal for every vehicle sharing this script, and the roster puts
## an AI taxi on it. Swapping this field for an AI's own intent is then the whole
## of what a driven car needs — nothing downstream asks where it came from.
var brake_input: float = 0.0
## The handbrake button, sampled once per tick. Cached for both reasons
## `brake_input` is: an AI taxi on this script must not read the *player's*
## handbrake, and the alternative was four duck-typed reads a tick — `InputRouter`
## has no `class_name`, so those cannot compile to a validated getter the way the
## typed `profile` reads do.
var drift_input: bool = false
## The steering axis, sampled once per tick for the same reasons, -1 left to +1
## right. `steer_ratio` above is the answer; this is the ask.
var steer_input: float = 0.0
## The throttle pedal, sampled once per tick. Cached for both reasons `brake_input`
## is, and it was the one that got away: read inline it cost two unvalidated
## autoload lookups a tick, and an AI taxi on this script would have driven on the
## *player's* throttle while obeying its own brake and handbrake.
var throttle_input: float = 0.0
## Held by the start menu (`P6-1`, `DriveHarness.park`): the pedals read
## nothing and the car coasts to rest under `_apply_coast_drag`. The router still
## samples the thumbs and the keys — nothing here stops it — so this is the one
## gate, and it is off on every scheme until a menu is up.
var parked: bool = false


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
## Climbs rather than taking get_parent(), because a re-parented mesh between the
## two is legal and a fixed one-step walk dereferences null the moment anything
## is interposed.
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
	_input = get_node_or_null(input_path)
	if _input == null:
		push_warning(
			"VehicleController found no input source at '%s'; the car has no pedals." % input_path
		)
	assert(profile != null, "VehicleController has no HandlingProfile assigned.")
	# The profile deliberately ships no defaults, so an unassigned resource reads
	# as all-zeroes. These two would fail as a dead spring and a car with no grip
	# at all, which is worth catching here rather than in the physics.
	assert(profile.wheel_radius_m > 0.0, "HandlingProfile.wheel_radius_m is zero.")
	assert(
		profile.suspension_frequency_hz > 0.0, "HandlingProfile.suspension_frequency_hz is zero."
	)

	# Direct children only, and by type: a VehicleWheel3D has to be a child of the
	# VehicleBody3D to be simulated at all, so a recursive search would collect
	# wheels the engine is ignoring and report a healthy four.
	var wheels: Array[VehicleWheel3D] = []
	for child: Node in get_children():
		var wheel := child as VehicleWheel3D
		if wheel != null:
			wheels.append(wheel)
	assert(not wheels.is_empty(), "VehicleController found no VehicleWheel3D children.")

	# A local, not a member: after the axle split every per-wheel write in this
	# file goes through _front or _rear, so a third collection of the same nodes
	# would only be a way for them to disagree.
	_group_axles(wheels)
	for wheel: VehicleWheel3D in wheels:
		_configure(wheel)

	gravity_scale = profile.gravity_scale
	center_of_mass_mode = RigidBody3D.CENTER_OF_MASS_MODE_CUSTOM
	center_of_mass = Vector3(0.0, profile.centre_of_mass_offset_y, 0.0)
	_rear_axle_behind_m = _axle_z(_rear) - center_of_mass.z
	contact_monitor = true
	max_contacts_reported = 8
	can_sleep = false


## The mean of `wheels`' authored positions along the car.
func _axle_z(wheels: Array[VehicleWheel3D]) -> float:
	var sum: float = 0.0
	for wheel: VehicleWheel3D in wheels:
		sum += wheel.position.z
	return sum / float(maxi(wheels.size(), 1))


## Split the wheels into front and rear by their position along the chassis.
##
## ⚠️ **Not by `use_as_steering` or `use_as_traction`.** ARCHITECTURE.md states
## the rule: the new Crown is front-wheel drive and the old one is rear-wheel
## drive, so on a front-drive car the front wheels both steer and drive, and
## keying off a role picks out the front axle on one vehicle and the rear axle on
## the other. The drift bias then inverts on whichever came second — silently,
## and only on the second vehicle anyone builds.
func _group_axles(wheels: Array[VehicleWheel3D]) -> void:
	var mean_z: float = 0.0
	for wheel: VehicleWheel3D in wheels:
		mean_z += wheel.position.z
	mean_z /= float(wheels.size())
	# -Z is forward, so the forward axle has the smallest z.
	for wheel: VehicleWheel3D in wheels:
		if wheel.position.z < mean_z:
			_front.append(wheel)
		else:
			_rear.append(wheel)


## The rear axle's wheels, split by position as `_group_axles` explains —
## never by `use_as_steering` or `use_as_traction`. Empty until `_ready`. For
## the rigs that hang off the rear tyres (`SkidMarks`' smoke, `DriftSparks`).
func rear_wheels() -> Array[VehicleWheel3D]:
	return _rear


## Push the profile onto one wheel.
##
## The two unit conversions are the only places this script claims to know
## Godot's suspension units, so they are stated rather than tuned by eye:
##
## `suspension_stiffness` — Godot's suspension force is `stiffness × compression
## × chassis mass`, so the stiffness number *is* ω², and a natural frequency `f`
## converts as `(2πf)²`. That is what keeps suspension_frequency_hz meaning what
## HandlingProfile says it means rather than needing a second seeded value.
##
## `damping_compression` — Godot inherits Bullet's convention, where the damping
## coefficient is `2ζ√stiffness`.
func _configure(wheel: VehicleWheel3D) -> void:
	wheel.wheel_radius = profile.wheel_radius_m
	wheel.wheel_rest_length = profile.suspension_rest_length_m
	wheel.suspension_travel = profile.suspension_travel_m

	var stiffness: float = pow(TAU * profile.suspension_frequency_hz, 2.0)
	wheel.suspension_stiffness = stiffness
	wheel.suspension_max_force = profile.suspension_max_force_n

	var damping: float = 2.0 * profile.suspension_damping_ratio * sqrt(stiffness)
	wheel.damping_compression = damping
	wheel.damping_relaxation = damping * RELAXATION_OVER_COMPRESSION


func _physics_process(delta: float) -> void:
	# Before anything else: righting the car this tick would otherwise leave it
	# holding drive and steering computed for the pose it no longer has.
	if _apply_auto_right(delta):
		return

	speed_kph = forward_speed_kph()
	if parked:
		steer_input = 0.0
		throttle_input = 0.0
		brake_input = 0.0
		drift_input = false
	elif _input != null:
		steer_input = _input.steer
		throttle_input = _input.accelerate
		brake_input = _input.brake_reverse
		drift_input = _input.drift

	_update_steering(delta)
	_apply_drive()
	_apply_air_drag()
	_apply_coast_drag(delta)
	_apply_drift(delta)
	_velocity_into_step = linear_velocity


## Signed forward speed in km/h. Negative when reversing.
func forward_speed_kph() -> float:
	return linear_velocity.dot(-global_basis.z) * 3.6


## The rear axle's velocity, which is what the game reads a slide on
## (`FareSystem.slip_deg_of`): its angle to the nose is how far the tail is
## out. Not the centre of mass's: a car turning tightly with every tyre
## gripping carries an angle there by geometry alone — 15° at full lock —
## which read as a slide, paid as one, and had stability control cut the power
## of a U-turn (`Q153`, 2026-10-06). At the rear axle a gripping turn reads 0.
func rear_axle_velocity() -> Vector3:
	return linear_velocity + angular_velocity.cross(global_basis.z * _rear_axle_behind_m)


## True while the brake/reverse pedal is slowing the car rather than backing it.
##
## ⚠️ **One pedal serves both, and the split is a rule, not an input.** Which of
## the two the driver gets depends on the car's own speed, so anything that
## re-derives it from the pedal alone is a second copy that drifts the first time
## STATIONARY_KPH moves. _apply_drive() reads these rather than restating them,
## so the brake lamp is on precisely when the brakes are. ✅ The one copy that
## used to remain — builtin_vehicle_controller.gd's inline restatement — went
## with the spike when Q50 made this car the built-in one.
func is_braking() -> bool:
	return not is_zero_approx(brake_input) and speed_kph > STATIONARY_KPH


## True while the pedal is driving the car backwards. See is_braking().
##
## Covers reversing at speed as well as pulling away from rest: once the car is
## moving backwards speed_kph is negative, so it stays below STATIONARY_KPH and
## the pedal keeps meaning reverse until it is released.
func is_reversing() -> bool:
	return not is_zero_approx(brake_input) and speed_kph <= STATIONARY_KPH


## Rate-limits VehicleBody3D.steering in place.
##
## No private mirror of it: the raycast controller kept its own angle because
## RigidBody3D has no steering property, and that reason does not survive the
## switch. `steering` is now both the state and the output.
func _update_steering(delta: float) -> void:
	var speed_ratio: float = clampf(absf(speed_kph) / profile.max_speed_kph, 0.0, 1.0)
	var max_angle: float = _steer_lock_rad(speed_ratio)
	# Negated: steer_input is +1 for right, but a positive rotation about +Y
	# turns the -Z forward vector toward -X, which is left.
	var target: float = -steer_input * max_angle
	# Returning to centre is quicker than reaching lock, so the car feels like it
	# wants to straighten. Rate is expressed as full-lock-per-second.
	var seconds: float = (
		profile.steer_attack_s if absf(target) > absf(steering) else profile.steer_release_s
	)
	steering = move_toward(steering, target, (max_angle / seconds) * delta)
	# Guarded because max_angle is a profile value and an unassigned resource
	# reads as all-zeroes — the same case the asserts in _ready cover for the two
	# that would fail loudly. This one would only ever produce a NAN in a lamp, so
	# it is handled rather than asserted.
	steer_ratio = -steering / max_angle if max_angle > 0.0 else 0.0


## The lock available at this share of the limiter: `steer_angle_max_deg` at
## rest, narrowing to `steer_angle_at_top_deg` at the limiter. A method so a
## subclass can widen it (`TyreVehicleController` does, while the car slides);
## the shipped car's table is unchanged by the seam.
func _steer_lock_rad(speed_ratio: float) -> float:
	return deg_to_rad(
		lerpf(profile.steer_angle_max_deg, profile.steer_angle_at_top_deg, speed_ratio)
	)


## Throttle, brake and reverse, onto the two properties VehicleBody3D drives on.
##
## ⚠️ **profile.engine_force and profile.brake_force do not mean here what they
## meant under the raycast model.** There they were newtons applied at a contact
## patch, per wheel, by this script. Here they are handed to the engine, which
## applies engine_force as a drive force split across the traction wheels and
## `brake` as a braking torque — so the same number produces a different
## acceleration, and both were re-seeded against tools/skidpad.sh rather than
## carried across. The dial names survived; their calibration did not.
## `engine_force` is the launch force since `Q153`; `_drive_force_n` limits it
## by the engine's power above about 42 kph.
## ⚠️ Accumulated into locals and assigned **once**. `engine_force` and `brake` are
## not plain field stores: each setter fans out over the body's wheel array to push
## the value onto every traction wheel, so zeroing and then overwriting walks that
## array twice a tick on the common path.
func _apply_drive() -> void:
	var force: float = 0.0
	var braking: float = 0.0

	if throttle_input > 0.0:
		# Ease off approaching top speed. A hard cutoff flips drive force between
		# full and zero tick to tick, which reads as a judder — and the louder the
		# more engine force there is. Godot has no speed limiter of its own, so
		# this is hand-written whichever vehicle class is underneath.
		var headroom: float = (
			(profile.max_speed_kph - speed_kph) / (profile.max_speed_kph * TOP_SPEED_TAPER)
		)
		force = DRIVE_SIGN * _drive_force_n() * throttle_input * clampf(headroom, 0.0, 1.0)

	if is_braking():
		braking = profile.brake_force * brake_input
	elif is_reversing() and speed_kph > -profile.max_reverse_kph:
		force = -DRIVE_SIGN * _drive_force_n() * brake_input

	engine_force = force
	brake = braking


## The drive the engine has at this speed: `engine_force` off the line, and
## above the speed where power limits it (about 42 kph on the shipped table),
## that power over the speed — a 4-speed automatic's envelope with its shifts
## smoothed away (`Q153`). A zero `engine_power_kw` or `driveline_efficiency`
## is an unauthored profile and leaves the launch force at every speed, as the
## car drove before the power limit.
func _drive_force_n() -> float:
	return _drive_force_at(absf(speed_kph) / 3.6)


## The same envelope at `mps`, for a caller that knows the driven wheels' own
## speed (`TyreVehicleController`).
func _drive_force_at(mps: float) -> float:
	if profile.engine_power_kw <= 0.0 or profile.driveline_efficiency <= 0.0:
		return profile.engine_force
	# Floored so a car at rest asks for the launch force, not a division by 0.
	var powered: float = (
		profile.engine_power_kw * 1000.0 * profile.driveline_efficiency / maxf(mps, 0.1)
	)
	return minf(profile.engine_force, powered)


## The air's drag, at every speed and whatever the pedals, against the travel.
## The body's own damping is replaced with 0 in `taxi.tscn`: Godot's default
## damped the car at 10% of its speed a second, throttle or not (`Q153`).
func _apply_air_drag() -> void:
	var velocity: Vector3 = linear_velocity
	var speed_sq: float = velocity.length_squared()
	if is_zero_approx(speed_sq) or profile.drag_area_m2 <= 0.0:
		return
	# −v × |v| × ½ρCdA: the drag against the travel, one root and no normalise.
	apply_central_force(
		velocity * (-0.5 * AIR_DENSITY_KG_M3 * profile.drag_area_m2 * sqrt(speed_sq))
	)


## Engine braking and rolling resistance, which VehicleBody3D does not model.
##
## Applied at the centre of mass as one chassis-level force rather than per wheel:
## the raycast model spent it at four contact patches because it was already there
## computing per-wheel longitudinal force, and there is no such loop here. The
## total is the same and the moment it makes about the centre of mass — none — is
## more correct, not less.
##
## Two terms, and the car only settles because of the second: the viscous one is
## proportional to speed, so it approaches zero as fast as the speed it is
## removing and never arrives. Neither is divided by delta — apply_central_force
## already integrates over the tick. The cap is the one place delta belongs, and
## for the opposite reason: it turns a speed into the deceleration that cancels
## exactly that speed in one tick.
func _apply_coast_drag(delta: float) -> void:
	if not is_zero_approx(throttle_input) or not is_zero_approx(brake_input):
		return
	# `speed_kph` is this same dot product, taken at the top of the tick — nothing
	# between the two writes `linear_velocity` or the basis, because property
	# writes only land at the integration step.
	var rolling: float = speed_kph / 3.6
	# `can_sleep` is false, so without this a parked car makes a physics-server
	# call every tick for ever to apply a zero force.
	if is_zero_approx(rolling):
		return
	var decel: float = (
		rolling * profile.coast_drag_per_s + signf(rolling) * profile.rolling_resistance_mps2
	)
	# ⚠️ Capped at the deceleration that lands exactly on zero this tick. The
	# viscous term cannot overshoot; the constant one can, and an uncapped rolling
	# resistance does not stop a rolling car — it reverses it, and then holds it
	# reversing.
	var decel_to_rest: float = absf(rolling) / delta
	var forward: Vector3 = -global_basis.z
	apply_central_force(forward * -mass * clampf(decel, -decel_to_rest, decel_to_rest))


## The drift button's ramp, rate-limited rather than switched on
## `_update_steering`'s idiom: fast to answer, slow to let go. The tyre model
## (`TyreVehicleController`) reads the engagement for its rear side cut.
func _apply_drift(delta: float) -> void:
	var seconds: float = profile.drift_attack_s if drift_input else profile.drift_release_s
	_drift_engagement = move_toward(_drift_engagement, 1.0 if drift_input else 0.0, delta / seconds)


## True while any wheel is on the ground.
##
## Two loops rather than `_front + _rear`, which would build a throwaway array
## on every call.
func _any_wheel_grounded() -> bool:
	for wheel: VehicleWheel3D in _rear:
		if wheel.is_in_contact():
			return true
	for wheel: VehicleWheel3D in _front:
		if wheel.is_in_contact():
			return true
	return false


## True while every wheel is off the ground: a jump, a drop off a deck, or a
## roll. What the air skill meters (`P3-51`); the roll is told apart by
## `is_upright` on the landing.
func is_airborne() -> bool:
	return not _any_wheel_grounded()


## True while the body's up is still up — the same bar `_apply_auto_right`
## rights the car at, read rather than acted on.
func is_upright() -> bool:
	return global_basis.y.dot(Vector3.UP) > OVERTURNED_DOT


## The hardest wall hit since the last call, in m/s into the wall, and clears
## it: a latch, read once per physics tick by `FareSystem` (`P3-50`). One
## contact is one reading — the slide leaves the car moving along the wall,
## so the next tick reads 0 unless the player steers back into it.
func take_impact_mps() -> float:
	var impact: float = _impact_mps
	_impact_mps = 0.0
	last_impact_mps = impact
	return impact


## Returns true if the car was righted this tick, so the caller can skip the
## drive and steering derived from the pose it no longer has.
func _apply_auto_right(delta: float) -> bool:
	if is_upright():
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
## The transform is the easy half. Momentum has to go with it — a body moved while
## it still holds the speed of a long fall carries that straight into whatever it
## lands on — and so does the drive state, which nothing outside this class sets:
## a car that fell at full lock would otherwise be replaced at full lock and veer
## off immediately.
##
func place_at(pose: Transform3D) -> void:
	global_transform = pose
	linear_velocity = Vector3.ZERO
	angular_velocity = Vector3.ZERO
	engine_force = 0.0
	brake = 0.0
	steering = 0.0
	# Published state as well as private, or a car righted at full lock is
	# replaced pointing straight ahead with its indicator still flashing. The
	# engagement goes with it, or a ramp that survived the reset would hand the
	# replaced car a slide it can no longer see.
	steer_ratio = 0.0
	_drift_engagement = 0.0
	_upside_down_for = 0.0
	drift_input = false


## Arcade collision response: glancing hits slide, head-on hits cost speed but
## never control. Godot's own restitution would bounce and spin the car instead.
##
## Survives the switch to VehicleBody3D unchanged, because VehicleBody3D *is* a
## RigidBody3D and this reads and writes the same PhysicsDirectBodyState3D. It is
## why collision_deflection and collision_speed_retained are still profile dials
## rather than joining the list of things the engine model cannot express.
##
## ⚠️ Everything here reads the velocity the wall MET, `_velocity_into_step`,
## never `state.linear_velocity`: by this callback the solver has already
## taken the normal component out, so off the state a 30° clip reads as
## "already moving away" and a head-on as "under the floor", and the slide
## never ran — the body's own friction then ground the car to 0.09 kph at
## 30° and 90° while only the 10° brush kept its speed (`Q148`, `Q151`).
## The latch reads the raw pre-step velocity on every contact, so its reading
## never depends on the order the contacts arrive in; the slid velocity is
## chained through the loop so a second contact on the same slab sees what
## the first left, and the spin is halved once per tick.
func _integrate_forces(state: PhysicsDirectBodyState3D) -> void:
	var velocity: Vector3 = _velocity_into_step
	var struck: bool = false
	for i: int in state.get_contact_count():
		var normal: Vector3 = state.get_contact_local_normal(i)
		if absf(normal.y) > WALL_NORMAL_Y:
			continue  # road surface, handled by the suspension
		if _velocity_into_step.length() >= 1.0:
			_impact_mps = maxf(_impact_mps, -_velocity_into_step.dot(normal))
		if velocity.length() < 1.0:
			continue
		var into_wall: float = velocity.normalized().dot(normal)
		if into_wall >= 0.0:
			continue  # already moving away
		var retained: float = lerpf(1.0, profile.collision_speed_retained, absf(into_wall))
		velocity = velocity.slide(normal) * lerpf(retained, 1.0, profile.collision_deflection)
		struck = true
	if struck:
		state.linear_velocity = velocity
		state.angular_velocity *= SCRAPE_SPIN_RETAINED
