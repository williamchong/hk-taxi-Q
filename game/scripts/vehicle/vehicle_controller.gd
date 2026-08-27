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
##   4. The drift, as a per-axle scale on the one isotropic friction number.
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
## Speed over which the drift yaw assist reaches full strength, easing in from a
## standstill. A structural constant rather than a dial: it exists to stop a
## discontinuity, not to shape the feel, and every other rate in this file eases.
const YAW_ASSIST_FADE_KPH: float = 10.0

## Fraction of top speed over which drive force eases to zero. Shapes the
## approach to max_speed_kph rather than setting it, so it stays a structural
## constant while the speed itself remains a profile dial.
const TOP_SPEED_TAPER: float = 0.15

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

## Split by chassis geometry once, because the drift scales the two axles
## differently, and every per-wheel write goes through one or the other. See
## _group_axles for why this is not `use_as_traction`.
var _front: Array[VehicleWheel3D] = []
var _rear: Array[VehicleWheel3D] = []

## Steering as a signed fraction of the lock available at this speed: -1.0 is
## full left, +1.0 is full right.
##
## Published because the indicators need to know the car is turning, and it has
## to be a *ratio*: lock runs from steer_angle_max_deg at rest to
## steer_angle_at_top_deg near the limiter, so one threshold in degrees means
## "a nudge" parked and "everything the car has" at speed.
##
## ⚠️ Sign follows InputRouter.steer, not `steering`. The physics angle is
## negated on the way in — a positive rotation about +Y turns -Z forward toward
## -X, which is left — and a lamp rig reading the raw angle would flash the
## indicator on the wrong side of the car, which looks like a working feature.
var steer_ratio: float = 0.0
var _upside_down_for: float = 0.0
## How far the drift has ramped in, 0 gripping to 1 fully loose.
##
## Private, and there is no public mirror. `drift_input` is the player's intent
## and this is the car's answer to it; a HUD or lamp wanting to show "drifting"
## wants the intent, which is already published. ⚠️ It is deliberately **not** in
## `InputRouter` — see `drift_release_s` in handling_profile.gd for why, kept in
## one place so the two cannot drift apart.
var _drift_engagement: float = 0.0
## Seconds the drift button has been held, driving the yaw burst's decay.
##
## Separate from `_drift_engagement` because they answer different questions: the
## engagement is how far in the drift is and rises and falls, this is how long it
## has been asked for and only ever rises. Reusing one for both would make the
## burst re-arm every time the engagement dipped.
##
## ⚠️ **Reset when the engagement reaches zero, not when the button comes up.**
## That makes `drift_release_s` the re-arm cost with no dial of its own, and it is
## what stops a player machine-gunning the button for a fresh kick every tick.
var _drift_held_s: float = 0.0
## Recomputed once per tick rather than per reader.
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
## The throttle pedal, sampled once per tick. Cached for both reasons `brake_input`
## is, and it was the one that got away: read inline it cost two unvalidated
## autoload lookups a tick, and an AI taxi on this script would have driven on the
## *player's* throttle while obeying its own brake and handbrake.
var throttle_input: float = 0.0


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
	contact_monitor = true
	max_contacts_reported = 8
	can_sleep = false


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

	wheel.wheel_friction_slip = profile.tyre_grip
	wheel.wheel_roll_influence = profile.roll_influence


func _physics_process(delta: float) -> void:
	# Before anything else: righting the car this tick would otherwise leave it
	# holding drive and steering computed for the pose it no longer has.
	if _apply_auto_right(delta):
		return

	speed_kph = forward_speed_kph()
	throttle_input = InputRouter.accelerate
	brake_input = InputRouter.brake_reverse
	drift_input = InputRouter.drift

	_update_steering(delta)
	_apply_drive()
	_apply_coast_drag(delta)
	_apply_drift(delta)


## Signed forward speed in km/h. Negative when reversing.
func forward_speed_kph() -> float:
	return linear_velocity.dot(-global_basis.z) * 3.6


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
	var max_angle: float = deg_to_rad(
		lerpf(profile.steer_angle_max_deg, profile.steer_angle_at_top_deg, speed_ratio)
	)
	# Negated: InputRouter.steer is +1 for right, but a positive rotation about
	# +Y turns the -Z forward vector toward -X, which is left.
	var target: float = -InputRouter.steer * max_angle
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


## Throttle, brake and reverse, onto the two properties VehicleBody3D drives on.
##
## ⚠️ **profile.engine_force and profile.brake_force do not mean here what they
## meant under the raycast model.** There they were newtons applied at a contact
## patch, per wheel, by this script. Here they are handed to the engine, which
## applies engine_force as a drive force split across the traction wheels and
## `brake` as a braking torque — so the same number produces a different
## acceleration, and both were re-seeded against tools/skidpad.sh rather than
## carried across. The dial names survived; their calibration did not.
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
		force = DRIVE_SIGN * profile.engine_force * throttle_input * clampf(headroom, 0.0, 1.0)

	if is_braking():
		braking = profile.brake_force * brake_input
	elif is_reversing() and speed_kph > -profile.max_reverse_kph:
		force = -DRIVE_SIGN * profile.engine_force * brake_input

	engine_force = force
	brake = braking


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


## The drift: a per-axle scale on the one friction number a wheel has.
##
## ⚠️ **This is the mechanism P0-5a rejected, shipping because Q50 said to.** It
## is not the handbrake the raycast model had. There, a locked rear tyre stopped
## having a preferred direction and its lateral force collapsed out of the
## geometry, with nothing anywhere reducing grip. Here there is one isotropic
## budget per tyre, so breaking the tail loose takes the rear axle's drive and
## braking with it by exactly the same factor — the slide costs speed as its
## mechanism rather than as a tuned penalty, and it self-terminates when the speed
## that caused it is gone. That is why HandlingProfile carries no scrub dial: the
## scrub is not a number any more, it is the mechanism.
##
## Written every tick rather than on change, so a live edit to either profile dial
## takes effect on the next frame instead of on the next button press.
func _apply_drift(delta: float) -> void:
	# Rate-limited rather than switched, on _update_steering's idiom and for the
	# same reason: fast to answer, slow to let go. Grip used to be restored on the
	# tick the button came up, which is why a 0.5 s tap returned 1.9° of slip and a
	# yaw identical to a plain corner — the slide carried no momentum out of the
	# release (Q84). ⚠️ It did not work — the tap is still 1.9° — and Q84 records
	# why: the slide takes seconds to build rather than ending too soon. This is
	# kept for Q83's touch hysteresis, which needs the engagement to exist.
	var seconds: float = profile.drift_attack_s if drift_input else profile.drift_release_s
	_drift_engagement = move_toward(_drift_engagement, 1.0 if drift_input else 0.0, delta / seconds)
	# Held time keeps accruing through the release ramp — the car is still sliding,
	# so the burst it already spent must stay spent. See _drift_held_s for why the
	# reset waits for the engagement rather than the button.
	#
	# ⚠️ **Only on ticks the torque could actually land.** _apply_drift_yaw refuses
	# airborne, so accruing there would spend a burst that was never applied — the
	# opposite of the sentence above — and with drift_yaw_sustain at 0.0 a drift
	# held over a jump would land with no assist at all. GAME_DESIGN.md scores
	# airtime, so that is a reachable state rather than a corner case. Deferring
	# the kick to the landing does not reintroduce the mid-air pirouette the
	# refusal exists for.
	if drift_input:
		if _any_wheel_grounded():
			_drift_held_s += delta
	elif is_zero_approx(_drift_engagement):
		_drift_held_s = 0.0
	_write_drift_grip()
	_apply_drift_yaw()


## Yaw assist while the drift is engaged. See drift_yaw_torque_nm for why this is
## a torque and must not become a slip-angle setpoint.
##
## ⚠️ Signed from steer_ratio — see its own doc for the rotation-direction
## convention — and negated for the same reason _update_steering negates on the
## way in. Stated once there rather than restated here.
##
## 🔴 **Refused with no wheel on the ground.** Torque does not care whether the
## tyres can answer it, and nothing else here would bound the spin: taxi.tscn sets
## no angular_damp and the project sets no default, so what actually limits this
## is tyre lateral force. Airborne there is none, and a held drift off a kerb
## would be a mid-air pirouette — reachable, because GAME_DESIGN.md scores airtime.
##
## ⚠️ Eased in from a standstill rather than gated: a stationary car has no tyre
## force to resist the assist either, so it would spin on the spot with the
## handbrake down, and a hard cut-in at walking pace is a pop the rest of this
## file's rates do not have.
## True while any wheel is on the ground.
##
## Two loops rather than `_front + _rear`, which would build a throwaway array
## every tick the drift is held. Rear first: it is the axle the drift is about,
## so it is the one most likely to answer on the first comparison.
func _any_wheel_grounded() -> bool:
	for wheel: VehicleWheel3D in _rear:
		if wheel.is_in_contact():
			return true
	for wheel: VehicleWheel3D in _front:
		if wheel.is_in_contact():
			return true
	return false


func _apply_drift_yaw() -> void:
	if is_zero_approx(_drift_engagement):
		return
	if not _any_wheel_grounded():
		return
	var speed: float = absf(speed_kph)
	var fade: float = clampf(speed / YAW_ASSIST_FADE_KPH, 0.0, 1.0) * _speed_fade_out(speed)
	# Linear decay from the peak to the sustain, on held time. ⚠️ On TIME — see
	# drift_yaw_decay_s for why measured slip here would be Q72's tautology.
	var decayed: float = clampf(_drift_held_s / profile.drift_yaw_decay_s, 0.0, 1.0)
	var burst: float = lerpf(1.0, profile.drift_yaw_sustain, decayed)
	var torque: float = (
		-steer_ratio * profile.drift_yaw_torque_nm * burst * _drift_engagement * fade
	)
	# About the body's own up, not global +Y: a car on a camber or mid-kerb should
	# rotate about the axis it is standing on.
	apply_torque(global_basis.y * torque)


## How much of the yaw assist survives at this speed, 1.0 full to 0.0 withdrawn.
##
## Separate from the fade-in above because they are different kinds of number: the
## fade-in exists to remove a discontinuity and shapes no feel, and this decides
## the speed band the drift button works in. See drift_yaw_fade_from_kph.
##
## ⚠️ A span of zero or less is a hard step at drift_yaw_fade_to_kph rather than a
## divide by zero — an unassigned profile reads as all-zeroes, and _update_steering
## guards max_angle for the same reason.
func _speed_fade_out(speed: float) -> float:
	var span: float = profile.drift_yaw_fade_to_kph - profile.drift_yaw_fade_from_kph
	if span <= 0.0:
		return 0.0 if speed >= profile.drift_yaw_fade_to_kph else 1.0
	return 1.0 - clampf((speed - profile.drift_yaw_fade_from_kph) / span, 0.0, 1.0)


## Publishes _drift_engagement to the wheels. Separate from the ramp so place_at()
## can reset the engagement and push it out without a zero delta standing in for
## "do not ramp" — the grip still has exactly one owner, which is the point the
## caller's comment makes.
func _write_drift_grip() -> void:
	var rear: float = (
		profile.tyre_grip * lerpf(1.0, profile.drift_rear_grip_scale, _drift_engagement)
	)
	var front: float = (
		profile.tyre_grip * lerpf(1.0, profile.drift_front_grip_scale, _drift_engagement)
	)
	for wheel: VehicleWheel3D in _rear:
		wheel.wheel_friction_slip = rear
	for wheel: VehicleWheel3D in _front:
		wheel.wheel_friction_slip = front


## Returns true if the car was righted this tick, so the caller can skip the
## drive and steering derived from the pose it no longer has.
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
## The transform is the easy half. Momentum has to go with it — a body moved while
## it still holds the speed of a long fall carries that straight into whatever it
## lands on — and so does the drive state, which nothing outside this class sets:
## a car that fell at full lock would otherwise be replaced at full lock and veer
## off immediately.
##
## ⚠️ The `_write_drift_grip()` call is not tidying. `_apply_drift()` is skipped
## for every tick `_apply_auto_right` returns true, so a car righted mid-drift
## keeps its softened rear axle until the button is next released. Called rather
## than open-coded so the un-drifted grip has one owner — a per-axle base grip
## would otherwise have to be added here too, and would not be.
func place_at(pose: Transform3D) -> void:
	global_transform = pose
	linear_velocity = Vector3.ZERO
	angular_velocity = Vector3.ZERO
	engine_force = 0.0
	brake = 0.0
	steering = 0.0
	# Published state as well as private, or a car righted at full lock is
	# replaced pointing straight ahead with its indicator still flashing. The
	# engagement goes with it: the comment above says a car righted mid-drift keeps
	# its softened axle until the button is next released, and a ramp that survived
	# the reset would instead hand the replaced car a slide it can no longer see.
	steer_ratio = 0.0
	_drift_engagement = 0.0
	# Or a replaced car carries a spent burst and the next press is a sustain with
	# no kick — which drives correctly, renders correctly, and is wrong.
	_drift_held_s = 0.0
	_upside_down_for = 0.0
	drift_input = false
	_write_drift_grip()


## Arcade collision response: glancing hits slide, head-on hits cost speed but
## never control. Godot's own restitution would bounce and spin the car instead.
##
## Survives the switch to VehicleBody3D unchanged, because VehicleBody3D *is* a
## RigidBody3D and this reads and writes the same PhysicsDirectBodyState3D. It is
## why collision_deflection and collision_speed_retained are still profile dials
## rather than joining the list of things the engine model cannot express.
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
