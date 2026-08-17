class_name BuiltinVehicleController
extends VehicleBody3D
## Godot's built-in `VehicleBody3D` driving the same car, as a spike.
##
## ⚠️ **This is not the shipping vehicle and must not become it without a
## decision.** `P0-5a` measured `VehicleBody3D`/`VehicleWheel3D` and rejected
## them, and CLAUDE.md's locked-decisions table records the rejection.
## `scripts/vehicle/vehicle_controller.gd` is the real one; nothing here is
## loaded by `city_drive.tscn`.
##
## It reads the **shipped** `tuning/handling.tres` deliberately. A spike tuned to
## its own numbers would only prove that two different cars feel different, so
## every field Godot can express is taken from the profile the custom controller
## already drives on, every field it cannot is listed in `_UNMAPPABLE`, and the
## structural constants below are taken from `VehicleController` rather than
## re-seeded — a difference that is not about the vehicle model would be noise in
## the comparison.
##
## See docs/DECISIONS.md `P0-5a`.

## Profile fields the shipped `VehicleController` consumes and this cannot, so
## the gap is countable rather than anecdotal.
##
## Scoped to fields the shipped car actually reads: `drift_slip_threshold_deg`
## and `drift_speed_scrub_per_s` are absent here too, but nothing in the repo
## consumes them yet, so counting them would overstate the loss.
##
## The first entry is the decisive one: `VehicleWheel3D` exposes a single
## `wheel_friction_slip`, so the two grip axes collapse into one number and a
## drift cannot break lateral grip without taking traction and braking with it.
## That is a property of the class, not of a tuning value.
const _UNMAPPABLE: PackedStringArray = [
	"grip_lateral + grip_longitudinal (one isotropic wheel_friction_slip)",
	"anti_roll (no anti-roll bar; godot_roll_influence is a different mechanism)",
	"coast_drag_per_s",
	"rolling_resistance_mps2",
	"collision_deflection",
	"collision_speed_retained",
	"auto_right_delay_s (hand-written below)",
]

## Body-up alignment below which the car counts as overturned. Taken from the
## shipped car so both right themselves at the same attitude.
const _OVERTURNED_DOT: float = VehicleController.OVERTURNED_DOT

## The per-axle lateral grip scales `handling.tres` carried when `P0-5a` was
## measured, frozen here as constants.
##
## ⚠️ **They are deliberately no longer read from the profile, and that is not a
## tidy-up.** The shipped car has had no such dial since the friction ellipse
## landed: its tail steps out because a locked tyre spends its budget
## longitudinally, so `drift_grip_scale` and `drift_front_grip_scale` were
## deleted from `HandlingProfile` rather than left unread. This spike is evidence
## for a decision taken against the numbers above, so it has to keep reproducing
## the run that was actually made — which means pinning them, not tracking a
## profile that has moved on. Changing them invalidates the comparison in
## `docs/DECISIONS.md`, `P0-5a`; use `godot_drift_scale_override` to sweep.
const _P0_5A_REAR_GRIP_SCALE: float = 0.65
const _P0_5A_FRONT_GRIP_SCALE: float = 0.85

## ⚠️ **Positive `engine_force` drives this rig backwards.** Godot resolves a
## wheel's forward axis from the wheel node's own basis, so the sign belongs to
## the rig rather than to a global convention — re-measure it by driving if the
## wheel transforms in `taxi_builtin.tscn` ever change.
const _DRIVE_SIGN: float = -1.0

## The shipped profile, unmodified. See the class comment.
@export var profile: HandlingProfile

@export_group("Godot-only", "godot_")
## `VehicleWheel3D.wheel_friction_slip`. Has no counterpart in `HandlingProfile`
## because the custom controller splits grip by axis and this cannot: it is the
## single number both `grip_lateral` and `grip_longitudinal` have to become.
##
## On the scene rather than in `handling.tres` for the reason `wheel_mount.gd`
## gives — the profile describes feel, and this describes an implementation.
@export_range(0.0, 20.0, 0.05) var godot_friction_slip: float = 4.0

## `VehicleWheel3D.suspension_max_force`, in newtons.
##
## ⚠️ Godot's default is 6000 N, which **cannot carry this car**. Static corner
## load is mass × g × `gravity_scale` ÷ 4 = 1200 × 9.8 × 1.6 ÷ 4 ≈ 4704 N, so the
## default leaves 1.27× headroom and the spring clips on the first kerb. Seeded
## at roughly 4× static load.
@export_range(0.0, 60000.0, 100.0, "suffix:N") var godot_suspension_max_force: float = 19000.0

## `VehicleWheel3D.wheel_roll_influence`. The nearest thing Godot offers to
## `anti_roll`, and not the same mechanism: it scales how much suspension force
## reaches the chassis as roll torque rather than adding a restoring torque
## across an axle. 0 suppresses body roll entirely.
@export_range(0.0, 1.0, 0.01) var godot_roll_influence: float = 0.2

## Rear-axle friction scale while drift is held, overriding
## `_P0_5A_REAR_GRIP_SCALE`. Negative means "use the recorded value", which is
## what a like-for-like comparison run wants.
##
## It exists to sweep the one number the built-in vehicle collapses grip into, so
## "is there a value that drifts?" can be answered by measurement rather than by
## one sample. Set it, drive `skidpad_builtin.tscn`, read `peak_slip_deg`.
@export_range(-1.0, 1.0, 0.01) var godot_drift_scale_override: float = -1.0

## Print a `builtin:` telemetry line periodically, plus the mapping report at
## startup. Off by default: with it off this class does no work the shipped car
## does not.
@export var log_telemetry: bool = false

## Seconds between telemetry lines. A second is too coarse to tell a spin from an
## impact — both read as "speed was 55, now it is 0".
@export_range(0.02, 5.0, 0.01, "suffix:s") var log_period_s: float = 0.25

## Largest slip angle since the last `place_at`, in degrees — the spike's headline
## statistic. Sampled every tick while `log_telemetry` is on, never at the
## logging period, because the transient it exists to catch is shorter than that.
var peak_slip_deg: float = 0.0

var _wheels: Array[VehicleWheel3D] = []
var _front: Array[VehicleWheel3D] = []
var _rear: Array[VehicleWheel3D] = []
var _upside_down_for: float = 0.0
var _log_at: float = 0.0
var _elapsed: float = 0.0


func _ready() -> void:
	assert(profile != null, "BuiltinVehicleController needs a HandlingProfile.")

	center_of_mass_mode = RigidBody3D.CENTER_OF_MASS_MODE_CUSTOM
	center_of_mass = Vector3(0.0, profile.centre_of_mass_offset_y, 0.0)
	gravity_scale = profile.gravity_scale

	for child: Node in get_children():
		var wheel: VehicleWheel3D = child as VehicleWheel3D
		if wheel == null:
			continue
		_configure(wheel)
		_wheels.append(wheel)

	assert(_wheels.size() == 4, "Expected four VehicleWheel3D children.")
	_group_axles()
	if log_telemetry:
		_report_mapping()


## Split the wheels into front and rear by their position along the chassis,
## which is what the drift scaling keys off.
##
## ⚠️ **Not by `use_as_steering` or `use_as_traction`.** `ARCHITECTURE.md` states
## the rule and `VehicleController._group_axles` follows it: the new Crown is
## front-wheel drive and the old one is rear-wheel drive, so on a front-drive car
## the front wheels both steer and drive, and keying off a role picks out the
## front axle on one vehicle and the rear axle on the other. The drift bias then
## inverts on whichever came second. `taxi_builtin.tscn` does set both roles, so
## a future editor will reach for them.
func _group_axles() -> void:
	var mean_z: float = 0.0
	for wheel: VehicleWheel3D in _wheels:
		mean_z += wheel.position.z
	mean_z /= float(_wheels.size())
	for wheel: VehicleWheel3D in _wheels:
		if wheel.position.z < mean_z:
			_front.append(wheel)
		else:
			_rear.append(wheel)


## Push the profile onto one wheel.
##
## The two conversions are the only places this script claims to know Godot's
## units, so they are stated rather than tuned by eye:
##
## `suspension_stiffness` — Godot's suspension force is `stiffness × compression
## × chassis mass`, so the stiffness number *is* ω², and a natural frequency `f`
## converts as `(2πf)²`. That is what makes `suspension_frequency_hz` portable
## across the two implementations rather than needing a second seeded value.
##
## `damping_compression` / `damping_relaxation` — Godot inherits Bullet's
## convention, where the damping coefficient is `2ζ√stiffness`. Rebound is damped
## harder than bump, which is ordinary vehicle practice and is why the one
## `suspension_damping_ratio` becomes two numbers.
func _configure(wheel: VehicleWheel3D) -> void:
	wheel.wheel_radius = profile.wheel_radius_m
	wheel.wheel_rest_length = profile.suspension_rest_length_m
	wheel.suspension_travel = profile.suspension_travel_m

	var stiffness: float = pow(TAU * profile.suspension_frequency_hz, 2.0)
	wheel.suspension_stiffness = stiffness
	wheel.suspension_max_force = godot_suspension_max_force

	var damping: float = 2.0 * profile.suspension_damping_ratio * sqrt(stiffness)
	wheel.damping_compression = damping
	wheel.damping_relaxation = damping * 1.2

	wheel.wheel_friction_slip = godot_friction_slip
	wheel.wheel_roll_influence = godot_roll_influence


func _report_mapping() -> void:
	if _wheels.is_empty():
		return
	print(
		"builtin: %d wheels, friction_slip %.2f (isotropic)" % [_wheels.size(), godot_friction_slip]
	)
	print(
		(
			"builtin: suspension %.1f Hz -> stiffness %.1f, max force %.0f N"
			% [
				profile.suspension_frequency_hz,
				_wheels[0].suspension_stiffness,
				_wheels[0].suspension_max_force,
			]
		)
	)
	for field: String in _UNMAPPABLE:
		print("builtin: unmappable — %s" % field)


func _physics_process(delta: float) -> void:
	if _apply_auto_right(delta):
		return

	# Cached for the tick for the reason `VehicleController.speed_kph` is cached:
	# everything here wants the same number, and nothing between these calls
	# changes `linear_velocity` — the property writes below only take effect at
	# the integration step.
	var speed: float = forward_speed_kph()
	_update_steering(delta, speed)
	_apply_drive(speed)
	_apply_drift()

	if log_telemetry:
		_log(delta, speed)


## Signed forward speed in km/h. Negative when reversing.
##
## Named to match `VehicleController`: `driver.gd` finds the car by looking for
## this method rather than by type, so the spike scenes are drivable by the same
## tool without the tool knowing they are spikes.
func forward_speed_kph() -> float:
	return linear_velocity.dot(-global_basis.z) * 3.6


## Angle between where the car points and where it is going, in degrees. Zero
## when tracking, 90° fully sideways, above 90° travelling backwards — which is
## what a spin looks like in this number.
## ⚠️ Both vectors are flattened to the ground plane, and the nose one was not
## until `Q49`. Comparing a flattened velocity against a pitched nose measures the
## car's attitude as well as its slip — immaterial on the level skidpad every
## recorded figure was taken on, wrong the moment a kerb or a landing is involved.
## `tools/skidpad_ablation.gd` grades the shipped car with this same definition,
## and `Q49` compares the two instruments' numbers, so they have to agree.
func slip_angle_deg() -> float:
	var velocity: Vector3 = Vector3(linear_velocity.x, 0.0, linear_velocity.z)
	if velocity.length() < 1.0:
		return 0.0
	var nose: Vector3 = -global_basis.z
	return rad_to_deg(velocity.normalized().angle_to(Vector3(nose.x, 0.0, nose.z).normalized()))


func _log(delta: float, speed: float) -> void:
	var slip: float = slip_angle_deg()
	peak_slip_deg = maxf(peak_slip_deg, slip)

	_elapsed += delta
	if _elapsed < _log_at:
		return
	_log_at += log_period_s
	print(
		(
			"builtin: t=%5.2f  speed=%7.2f kph  slip=%6.1f deg  peak=%6.1f  skid=%.2f  at=(%.1f, %.1f)"
			% [
				_elapsed,
				speed,
				slip,
				peak_slip_deg,
				_mean_skid(),
				global_position.x,
				global_position.z,
			]
		)
	)


## Mean of `get_skidinfo()` across the wheels — 1.0 is full grip, 0.0 a fully
## sliding tyre. One of the two things `P0-5a` recorded as genuinely worth having
## from the built-in vehicle, and it is free here.
func _mean_skid() -> float:
	var total: float = 0.0
	for wheel: VehicleWheel3D in _wheels:
		total += wheel.get_skidinfo()
	return total / float(_wheels.size())


## Rate-limits `VehicleBody3D.steering` in place. No private mirror of it: the
## shipped controller keeps its own angle because `RigidBody3D` has no steering
## property, and that reason does not carry over.
func _update_steering(delta: float, speed: float) -> void:
	var speed_ratio: float = clampf(absf(speed) / profile.max_speed_kph, 0.0, 1.0)
	var max_angle: float = deg_to_rad(
		lerpf(profile.steer_angle_max_deg, profile.steer_angle_at_top_deg, speed_ratio)
	)
	# Negated as `vehicle_controller.gd` negates: InputRouter.steer is +1 for
	# right, and a positive rotation about +Y turns -Z toward -X, which is left.
	var target: float = -InputRouter.steer * max_angle
	var seconds: float = (
		profile.steer_attack_s if absf(target) > absf(steering) else profile.steer_release_s
	)
	steering = move_toward(steering, target, (max_angle / seconds) * delta)


## Throttle, brake and reverse.
##
## The top-speed taper is `VehicleController`'s, not a second design: a hard
## cutoff flips drive force between full and zero tick to tick and reads as a
## judder, which here would read as a `VehicleBody3D` finding rather than as a
## spike artefact. Godot has no speed limiter of its own, so the approach is
## hand-written either way — the "fightable" half of the gap `P0-5a` describes.
func _apply_drive(speed: float) -> void:
	var throttle: float = InputRouter.accelerate
	var reverse: float = InputRouter.brake_reverse

	engine_force = 0.0
	brake = 0.0

	if throttle > 0.0:
		var headroom: float = (
			(profile.max_speed_kph - speed)
			/ (profile.max_speed_kph * VehicleController.TOP_SPEED_TAPER)
		)
		engine_force = (_DRIVE_SIGN * profile.engine_force * throttle * clampf(headroom, 0.0, 1.0))
	if reverse > 0.0:
		if speed > VehicleController.STATIONARY_KPH:
			brake = profile.brake_force * reverse
		elif speed > -profile.max_reverse_kph:
			engine_force = -_DRIVE_SIGN * profile.engine_force * reverse


## The drift dial, and the whole point of the spike.
##
## Per-axle friction scaling is expressible — the rear wheels can be given a
## lower `wheel_friction_slip` than the front, which is what
## `_P0_5A_REAR_GRIP_SCALE` and `_P0_5A_FRONT_GRIP_SCALE` ask for. What is *not*
## expressible is that the
## scaling apply to lateral grip only: the same number is the tyre's longitudinal
## limit, so the rear axle loses drive and braking by exactly the factor that
## lets the tail step out. Watch `speed` against `slip` in the telemetry while
## holding drift, and compare `peak_slip_deg` with the profile's
## `drift_slip_threshold_deg`.
##
## Written every tick rather than on change: `set_friction_slip` is a plain
## field store, and a guard keyed on the drift input would swallow live edits to
## `godot_friction_slip` and `godot_drift_scale_override` — the two dials this
## exists to sweep.
func _apply_drift() -> void:
	var held: bool = InputRouter.drift
	var override: float = godot_drift_scale_override
	var rear_grip: float = override if override >= 0.0 else _P0_5A_REAR_GRIP_SCALE
	var rear: float = godot_friction_slip * (rear_grip if held else 1.0)
	var front: float = godot_friction_slip * (_P0_5A_FRONT_GRIP_SCALE if held else 1.0)
	for wheel: VehicleWheel3D in _rear:
		wheel.wheel_friction_slip = rear
	for wheel: VehicleWheel3D in _front:
		wheel.wheel_friction_slip = front


## Hand-written because `VehicleBody3D` has no equivalent — one of `_UNMAPPABLE`.
## Kept anyway: without it a spin that ends on the roof ends the drive, which
## would cost the spike a run for a reason unrelated to handling.
func _apply_auto_right(delta: float) -> bool:
	if global_basis.y.dot(Vector3.UP) > _OVERTURNED_DOT:
		_upside_down_for = 0.0
		return false
	_upside_down_for += delta
	if _upside_down_for < profile.auto_right_delay_s:
		return false
	# Keep heading, discard roll and pitch.
	var lift: Vector3 = Vector3.UP * VehicleController.RIGHTING_LIFT_M
	place_at(Transform3D(Basis(Vector3.UP, global_rotation.y), global_position + lift))
	return true


func place_at(pose: Transform3D) -> void:
	global_transform = pose
	linear_velocity = Vector3.ZERO
	angular_velocity = Vector3.ZERO
	engine_force = 0.0
	brake = 0.0
	steering = 0.0
	_upside_down_for = 0.0
	peak_slip_deg = 0.0
	# Drift friction outlives the righting window otherwise: `_apply_drift` is
	# skipped for every tick `_apply_auto_right` returns true.
	for wheel: VehicleWheel3D in _wheels:
		wheel.wheel_friction_slip = godot_friction_slip
