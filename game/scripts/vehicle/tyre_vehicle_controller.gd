class_name TyreVehicleController
extends VehicleController
## `taxi.tscn`'s car with its tyres replaced by a per-wheel model (`P3-52`,
## `Q152`): the game's car since 2026-10-03, through `taxi_tyre.tscn`, and the
## only one since the engine-tyre control was dropped (2026-10-05). "The
## shipped car" below and in `tyre.md` is the car before it, `taxi.tscn` on
## the engine's tyres.
##
## **Why it exists.** `Q85` closed on "a tyre model layered on `VehicleWheel3D`
## is the only route to the physical mechanism". Godot's wheel has one friction
## number, the same in every direction, and no wheel inertia, so a slide cannot
## break sideways grip while keeping drive, and a wheel cannot spin faster than
## the road. This keeps everything else `VehicleBody3D` does — the suspension
## ray, the spring and damper, the contact — and turns the engine's own tyre
## force off (`wheel_friction_slip` 0, which zeroes both of its impulses), then
## applies its own at each wheel's contact point:
##
##   1. Each wheel carries its own spin, integrated in `TyreProfile.substeps`
##      steps a tick, semi-implicitly so a light wheel on a stiff curve is
##      stable at 60 Hz. Drive torque on the traction wheels, brake torque on
##      all four, the drift button's handbrake on the rear.
##   2. Forward slip and sideways slip angle, each over its own peak, combine
##      into one slip whose force comes off a Pacejka-shaped curve scaled by
##      the wheel's load — a friction ellipse in slip space, so a spinning or
##      locked tyre has less to give sideways.
##   3. The load is rebuilt from the suspension state Godot does not publish:
##      the contact point against the wheel's hardpoint gives the spring's
##      length, and the spring and damper settings on the wheel give its force
##      (`_load_n`, Godot's own formula restated).
##
##   4. The car's systems, each with its own table under `tuning/systems/`
##      (`Q155`): traction control and stability control's power cuts, drift
##      mode that stands them down for a slide the player asked for
##      (`DriftMode`), the handbrake and the rev limiter. The game's own
##      aids, which no real car has, are grouped as such
##      (`ArcadeAidsProfile`): the rear side cut, the flick, the cap on a
##      caught slide's countersteer (`CatchLimiter`) and the slide lock.
##
## Everything else — the player's steering, the speed taper, coast drag, wall
## response, auto-righting, the published reads the fare and the lamps take —
## is the parent's, unchanged, so the skidpad and a street drive grade this car
## with no special case.
##
## ⚠️ **A table with a zero key parks the car** (`usable`): it does not drive,
## where it once fell back to the engine's tyres, which nothing grades since
## the engine-tyre car was dropped.

## The spin solve stops when the torques balance to within this, or after
## this many iterations — a safeguarded Newton, so it never leaves its bracket.
const SOLVE_TOLERANCE_NM: float = 0.5
const SOLVE_ITERATIONS: int = 12
## Normal-to-ray alignment under which Godot stops trusting the contact and
## pins its damper — `vehicle_body_3d.cpp`'s own -0.1, restated for `_load_n`.
const CONTACT_DOT_FLOOR: float = -0.1
## Body slip past which the car is travelling backwards, not sliding: stability
## control's slip cuts stand aside there, so the throttle drives the wheels and
## brakes the backward roll as a real car's does. Cut at every slip, a car spun
## round in drift mode had no drive at all and rolled backwards at 10–30 kph
## with the throttle held (the user's report, 2026-10-06). A geometric fact —
## 90° is the travel crossing the axle — not a dial.
const REVERSED_SLIP_DEG: float = 90.0

@export var tyre: TyreProfile
@export var traction_control: TractionControlProfile
@export var stability_control: StabilityControlProfile
@export var drift_mode: DriftModeProfile
@export var handbrake: HandbrakeProfile
@export var rev_limiter: RevLimiterProfile
@export var arcade_aids: ArcadeAidsProfile
@export var anti_lock_brakes: AntiLockBrakesProfile

## Every wheel, front axle first, so the per-wheel arrays below index the same.
## A third collection beside the parent's `_front` and `_rear`, which
## `_ready` there warns can disagree with them: built from those two once and
## never written again, so it cannot, and `i >= _front.size()` reads the rear.
var _wheels: Array[VehicleWheel3D] = []
## Each wheel's authored position on the chassis — where its suspension ray
## starts. Godot captures the same point when the wheel enters the tree and
## then overwrites the node's position every tick with the sprung one.
var _hardpoints: PackedVector3Array = PackedVector3Array()
## Spin about the axle, rad/s, positive rolling forward.
var _omega: PackedFloat32Array = PackedFloat32Array()
## The load `_load_n` last rebuilt for each wheel, in newtons; 0 off the ground.
var _loads: PackedFloat32Array = PackedFloat32Array()
## Each wheel's combined slip at the end of the tick, in multiples of the
## tyre's peak — 1.0 is the top of the curve; 0 off the ground. Written for the
## tyre marks (`P3-57`) and read by nothing the solve uses.
var _slips: PackedFloat32Array = PackedFloat32Array()
## The wheel's own spin angle, and the one Godot is rolling it by, so the tyre
## mesh can show the model's spin rather than the road's.
var _spin_angle: PackedFloat32Array = PackedFloat32Array()
var _engine_angle: PackedFloat32Array = PackedFloat32Array()
var _visuals: Array[Node3D] = []
var _drift_mode: DriftMode = DriftMode.new()
var _catch: CatchLimiter = CatchLimiter.new()
## The rear side cut, latched at the drift button's press. Latched, not
## tracked: a slide sheds speed, and a cut that deepened as it did would feed
## itself (`Q89`).
var _side_cut: float = 0.0
## The car's whole drive force and the brake dial as the parent set them this
## tick, before this class took them back off the engine.
var _drive_n: float = 0.0
## Each driven wheel's share of `_drive_n`, from the wheels marked
## `use_as_traction`.
var _traction_share: float = 0.0
## The wheelbase off the wheels' own hardpoints, and gravity as this body feels
## it, for `_grip_lock_rad`.
var _wheelbase_m: float = 0.0
var _gravity_mps2: float = 0.0
var _brake_dial: float = 0.0
## Microseconds spent in `_apply_tyres` and the ticks that spent them, for the
## skidpad's cost column.
var _cost_us: int = 0
var _cost_ticks: int = 0
## The wheel being solved and its tick's curve, so the force and the spin solve
## read one contact rather than passing seven numbers down every call.
var _radius: float = 0.0
var _along: float = 0.0
var _ground: float = 0.0
var _slip_y: float = 0.0
var _peak_n: float = 0.0
var _curve_b: float = 0.0
var _curve_c: float = 0.0
## Per wheel, what a unit of rim speed is in multiples of the peak slip ratio.
var _per_slip: float = 0.0
## The spin solve's by-products: `_force`'s slope of the forward force against
## rim speed, and the force at the spin `_solve_spin` returned, which the tick
## sums rather than evaluating the curve a second time.
var _slope_x: float = 0.0
var _solved: Vector2 = Vector2.ZERO


func _ready() -> void:
	super._ready()
	if not usable(tyre) or not _systems_assigned():
		# Parked rather than driven on the engine's tyres, which no grading
		# covers since the engine-tyre control was dropped.
		set_physics_process(false)
		return
	_wheels.append_array(_front)
	_wheels.append_array(_rear)
	var driven: int = 0
	for wheel: VehicleWheel3D in _wheels:
		driven += 1 if wheel.use_as_traction else 0
		_hardpoints.append(wheel.position)
		wheel.wheel_friction_slip = 0.0
		_visuals.append(wheel.get_node_or_null(^"Visual") as Node3D)
	# `engine_force` is the car's whole drive, split across its driven wheels
	# as the engine split it (`HandlingProfile.engine_force`).
	_traction_share = 1.0 / float(maxi(driven, 1))
	_wheelbase_m = absf(_axle_z(_front) - _axle_z(_rear))
	_gravity_mps2 = float(ProjectSettings.get_setting("physics/3d/default_gravity")) * gravity_scale
	_omega.resize(_wheels.size())
	_loads.resize(_wheels.size())
	_slips.resize(_wheels.size())
	_spin_angle.resize(_wheels.size())
	_engine_angle.resize(_wheels.size())


## Whether `table` can run the model. `side_force_depth` may legally be 0 —
## the force at the centre of mass — so a missing one cannot be told from a
## chosen one and is not guarded; nor is any system's table, where a zero is
## that system off.
static func usable(table: TyreProfile) -> bool:
	if table == null:
		push_error("TyreVehicleController: no TyreProfile; the car does not drive.")
		return false
	var fields: Dictionary[String, float] = {
		"mu": table.mu,
		"slide_ratio": table.slide_ratio,
		"peak_slip_ratio": table.peak_slip_ratio,
		"peak_slip_angle_deg": table.peak_slip_angle_deg,
		"wheel_inertia_kgm2": table.wheel_inertia_kgm2,
		"low_speed_mps": table.low_speed_mps,
		"substeps": float(table.substeps),
	}
	return not TuningTable.any_zero(
		table, fields, "TyreVehicleController", "the car does not drive"
	)


## Whether every system's table is assigned: a null one would stop the tick at
## its first read, so the car is parked behind one error instead.
func _systems_assigned() -> bool:
	var tables: Array[Resource] = [
		traction_control,
		stability_control,
		drift_mode,
		handbrake,
		rev_limiter,
		arcade_aids,
		anti_lock_brakes,
	]
	if tables.has(null):
		push_error("TyreVehicleController: a system's table is unassigned; the car does not drive.")
		return false
	return true


## Each wheel's last rebuilt load in newtons, front axle first. For the probe
## and the skidpad; nothing in the game reads it.
func wheel_loads_n() -> PackedFloat32Array:
	return _loads


## Each wheel's combined slip, forward and sideways, in multiples of the
## tyre's peak, front axle first as `tyre_wheels` lists them; 0 off the ground.
## Past 1.0 the tyre is over the top of its curve — sliding, spinning or locked.
## For the tyre marks and smoke (`P3-57`); the solve never reads it, so the
## skidpad is the same with or without a reader.
func wheel_slips() -> PackedFloat32Array:
	return _slips


## The wheels `wheel_slips` and `wheel_loads_n` index, front axle first. Empty
## on a table with a zero key: the car is parked and publishes no slip.
func tyre_wheels() -> Array[VehicleWheel3D]:
	return _wheels


## Mean microseconds per tick spent in the tyre model since the last call, and
## resets — the skidpad's cost column.
func take_tyre_cost_us() -> float:
	var mean: float = float(_cost_us) / float(_cost_ticks) if _cost_ticks > 0 else 0.0
	_cost_us = 0
	_cost_ticks = 0
	return mean


## The parent's steering, capped by the catch limiter. `steer_ratio`, which
## the lamps read, stays the player's.
func _update_steering(delta: float) -> void:
	super._update_steering(delta)
	if arcade_aids.catch_lock_deg > 0.0:
		steering = _catch.step(
			steering,
			steer_input,
			_slide_toward(),
			_slide_beyond_peak_rad(),
			angular_velocity.y,
			delta,
			arcade_aids
		)


## Whether the catch limiter holds the countersteer this tick, for the skidpad.
func catch_capped() -> bool:
	return _catch.capped


## The lock the player has while the car slides: the parent's speed-narrowed
## lock, widened to `ArcadeAidsProfile.slide_lock_deg` on the countersteer side
## alone once the
## slip is past the tyre's peak. Built on the suspicion that the handling
## table's lock (16° at 63 kph, under 14° at 86) was why a countersteered
## slide at 86 kph fell short of the fare's 2 s; swept and refuted — every
## value past the table's lock SHORTENED `hold` at all three speeds, because
## the pad's driver steers a share of the lock it has and a wider one makes
## its catch a straightening (`systems/arcade_aids.md`). Shipped absent, so 0 and inert; kept
## because a player's hands, unlike the driver's, scale to the wheel, and the
## user's own drive is the grade that could still want it. One side only: a
## wider lock INTO the slide at 86 kph is a spin, not a skill. No angle asked
## for (`Q72`).
func _steer_lock_rad(speed_ratio: float) -> float:
	var lock: float = super._steer_lock_rad(speed_ratio)
	if _slide_beyond_peak_rad() <= 0.0:
		# Not sliding: the lock the tyres can use (`steer_to_grip`), if it is
		# under the table's — but never once drift mode is engaged: the button or
		# a flick is the player asking for rotation, and a capped turn-in changed
		# how the slide starts (the plain tap at 42 kph 69° → 83°).
		if arcade_aids.steer_to_grip > 0.0 and not _drift_mode.engaged:
			lock = minf(lock, arcade_aids.steer_to_grip * _grip_lock_rad())
		return lock
	if arcade_aids.slide_lock_deg <= 0.0:
		return lock
	# `steer_input` is +1 for right, and the parent negates it into Godot's
	# positive-left angle; `_slide_toward` is in the angle's sign, so the
	# player is countersteering when the two have opposite signs.
	if -steer_input * _slide_toward() <= 0.0:
		return lock
	return maxf(lock, deg_to_rad(arcade_aids.slide_lock_deg))


## The front wheels' angle that holds the tyres' grip in a steady turn at this
## speed: the turn's own angle for `mu × g` of sideways pull on this wheelbase,
## plus the tyre's peak slip angle. Under the tyre's low-speed floor the speed
## is held at it, so a car at rest asks for no infinite angle.
func _grip_lock_rad() -> float:
	var mps: float = maxf(absf(speed_kph) / 3.6, tyre.low_speed_mps)
	var turn: float = atan(_wheelbase_m * tyre.mu * _gravity_mps2 / (mps * mps))
	return turn + deg_to_rad(tyre.peak_slip_angle_deg)


## How far the rear axle's slip is past the tyre's peak, in radians, or 0 when
## it is not sliding forward. The size is the game's own slip
## (`FareSystem.slip_deg_of`, the one the fare pays on). Forward travel only:
## backing up reads as a slip near 180° and would snap the fronts to full
## lock; past 90° the car has spun anyway.
func _slide_beyond_peak_rad() -> float:
	var nose: Vector3 = -global_basis.z
	if linear_velocity.dot(nose) <= 0.0 or linear_velocity.length() < tyre.low_speed_mps:
		return 0.0
	var slip_deg: float = FareSystem.slip_deg_of(rear_axle_velocity(), nose)
	return maxf(deg_to_rad(slip_deg - tyre.peak_slip_angle_deg), 0.0)


## The countersteer's sign in Godot's steering angle: from the cross product's
## up component, positive when the travel is left of the nose — Godot's
## positive (left) steering, the countersteer for a tail out to the left.
func _slide_toward() -> float:
	return signf((-global_basis.z).cross(rear_axle_velocity()).y)


## The parent's pedals, taken back off the engine: `engine_force` and `brake`
## act through the friction this class has zeroed, so they are read here and
## applied as torque in `_apply_tyres` instead.
func _apply_drive() -> void:
	super._apply_drive()
	# The parent writes `DRIVE_SIGN × force`, so the product is forward-positive.
	# The arcade aid's boost goes on top of the real car's drive on the road,
	# not in a slide the player asked for (drift mode as of last tick): there
	# the real car's power is what the drift was tuned on, and the boost spun
	# every tap (162°).
	# It fades with the front wheels' angle over the lock, whole straight and
	# gone at full lock: at 0.5 a full-throttle corner put the rears at 1.5×
	# their grip at 42 kph, which stability control alone could not hold.
	var boost: float = 0.0 if _drift_mode.engaged else arcade_aids.drive_boost
	if boost > 0.0:
		boost *= 1.0 - _steer_share()
	_drive_n = engine_force * DRIVE_SIGN * (1.0 + boost)
	_brake_dial = brake
	engine_force = 0.0
	brake = 0.0


## The drift button is a handbrake here: the parent's ramp still runs, because
## the rear side cut reads it, and the tyres come last so they see this tick's
## pedals.
func _apply_drift(delta: float) -> void:
	super._apply_drift(delta)
	_apply_tyres(delta)


func place_at(pose: Transform3D) -> void:
	super.place_at(pose)
	_drive_n = 0.0
	_brake_dial = 0.0
	_omega.fill(0.0)
	_loads.fill(0.0)
	_side_cut = 0.0
	_drift_mode.reset()
	_catch.reset()


func _apply_tyres(delta: float) -> void:
	var started: int = Time.get_ticks_usec()
	var steps: int = tyre.substeps
	var step: float = delta / float(steps)
	_curve_c = 2.0 - 2.0 * asin(tyre.slide_ratio) / PI
	_curve_b = tan(PI / (2.0 * _curve_c))
	var tan_peak: float = tan(deg_to_rad(tyre.peak_slip_angle_deg))
	var com: Vector3 = global_transform * center_of_mass
	var nose: Vector3 = -global_basis.z
	var up: Vector3 = global_basis.y
	var share: float = mass / float(_wheels.size())
	var brake_nm: float = _brake_dial * float(Engine.physics_ticks_per_second)
	var rim_limit_mps: float = profile.max_speed_kph / 3.6 * (1.0 + rev_limiter.overspeed_share)
	var pressed: bool = _drift_mode.step(
		drift_input,
		steer_input,
		throttle_input,
		brake_input,
		speed_kph,
		rear_axle_velocity(),
		nose,
		profile.drift_slip_threshold_deg,
		delta,
		drift_mode,
		arcade_aids
	)
	if pressed:
		# Latched, not tracked: a slide sheds speed, and a cut that deepened as
		# it did would feed itself (`Q89`).
		_side_cut = _side_cut_at(absf(speed_kph))
	var wheelspin_limit: float = traction_control.wheelspin_limit
	var lock_limit: float = anti_lock_brakes.slip_limit
	# Each axle's share of the foot brake, so the four wheels sum to the dial.
	var front_share: float = profile.brake_front_share
	if front_share <= 0.0:
		front_share = 0.5
	# What the parent's drive was sized on: the engine's force at the car's speed.
	var body_force_n: float = _drive_force_n()
	var governor: bool = wheelspin_limit > 0.0 and not _drift_mode.engaged
	var drive_share: float = 1.0
	if _drift_mode.engaged:
		drive_share = _slide_drive_share()
	elif governor:
		drive_share = _turn_drive_share() * _armed_slip_share()
	for i: int in _wheels.size():
		var wheel: VehicleWheel3D = _wheels[i]
		_radius = wheel.wheel_radius
		var drive_nm: float = (
			_drive_n * _traction_share * drive_share * _radius if wheel.use_as_traction else 0.0
		)
		# A limiter on the wheel, where the parent's taper is on the body: a
		# spinning tyre must not run the wheel past top speed either.
		if absf(_omega[i]) * _radius >= rim_limit_mps and signf(drive_nm) == signf(_omega[i]):
			drive_nm = 0.0
		# The axle's share of all four wheels' brake, over that axle's wheels.
		var on_front: bool = i < _front.size()
		var axle_share: float = front_share if on_front else 1.0 - front_share
		var axle_wheels: int = _front.size() if on_front else _rear.size()
		var foot_nm: float = brake_nm * _radius * axle_share * _wheels.size() / axle_wheels
		var hand_nm: float = 0.0
		if drift_input and i >= _front.size():
			hand_nm = handbrake.torque_nm
		var hold_nm: float = foot_nm + hand_nm
		if not wheel.is_in_contact():
			# No tyre force off the ground, so the spin is closed-form.
			_loads[i] = 0.0
			_slips[i] = 0.0
			var inertia_s: float = delta / tyre.wheel_inertia_kgm2
			var aloft: float = _omega[i] + drive_nm * inertia_s
			var held: float = hold_nm * inertia_s
			_omega[i] = 0.0 if absf(aloft) <= held else aloft - signf(aloft) * held
			continue
		var point: Vector3 = wheel.get_contact_point()
		var normal: Vector3 = wheel.get_contact_normal()
		var load: float = _load_n(i, point, normal)
		_loads[i] = load
		var heading: Vector3 = nose.rotated(up, steering) if wheel.use_as_steering else nose
		var forward: Vector3 = (heading - normal * heading.dot(normal)).normalized()
		var side: Vector3 = forward.cross(normal)
		var velocity: Vector3 = linear_velocity + angular_velocity.cross(point - com)
		_along = velocity.dot(forward)
		var across: float = velocity.dot(side)
		_ground = maxf(absf(_along), tyre.low_speed_mps)
		_peak_n = tyre.mu * load
		_slip_y = across / _ground / tan_peak
		_per_slip = 1.0 / (_ground * tyre.peak_slip_ratio)
		var at_rest: Vector2 = _force(0.0) if hold_nm > 0.0 else Vector2.ZERO
		var omega: float = _omega[i]
		var governed: bool = governor and wheel.use_as_traction
		var sum := Vector2.ZERO
		for _s: int in steps:
			# Traction control watches wheelspin, the forward slip alone, and
			# cuts the torque that would spin the tyre further past it; the brake
			# and a torque that slows the spin pass. Keyed on the combined slip
			# first, it cut the drive at every cornering limit and the corner row
			# scrubbed 15% of its speed.
			var slip_x: float = (omega * _radius - _along) * _per_slip
			# The engine turns the wheels, so its power is spent at the rim's
			# speed, not the car's: sized on the car's alone, a wheel spinning
			# at three times the road's speed was handed three times the
			# engine's power, and every slide was fed by it (`Q153`).
			var torque_nm: float = drive_nm
			if body_force_n > 0.0 and not is_zero_approx(drive_nm):
				torque_nm *= _drive_force_at(absf(omega) * _radius) / body_force_n
			if governed and absf(slip_x) >= wheelspin_limit and signf(drive_nm) == signf(slip_x):
				torque_nm = 0.0
			# ABS releases the foot brake on a wheel starting to lock — backward
			# slip past its limit — and never the handbrake.
			var held_nm: float = hold_nm
			if lock_limit > 0.0 and foot_nm > 0.0 and slip_x <= -lock_limit:
				held_nm = hand_nm
			omega = _solve_spin(omega, torque_nm, held_nm, step, at_rest)
			sum += _solved
		_omega[i] = omega
		_slips[i] = Vector2((omega * _radius - _along) * _per_slip, _slip_y).length()
		var mean: Vector2 = sum / float(steps)
		# Never more force than cancels this wheel's share of the slip velocity in
		# one tick: near rest a slip curve is a stiff spring on the chassis, and
		# this stops it ringing. Sideways always; forward only on a wheel held
		# still, because a turning wheel carries its drive through its spin and a
		# cap there measured the car to 8.5 kph in four seconds of full throttle.
		var cap: float = share / delta
		var fx: float = mean.x
		if is_zero_approx(omega):
			fx = clampf(fx, -cap * absf(_along), cap * absf(_along))
		var fy: float = clampf(mean.y, -cap * absf(across), cap * absf(across))
		if i >= _front.size() and _side_cut > 0.0 and _drift_engagement > 0.0:
			# Capped against what the turn asks of this wheel, not scaled: under
			# arcade grip a scaled tyre just runs a little more slip angle and
			# holds the turn (42 kph: no slide at half the force), and a cut
			# deep enough for 42 kph spun the car at 63.
			var asked: float = share * linear_velocity.length() * absf(angular_velocity.dot(up))
			var kept: float = minf(absf(fy), asked * (1.0 - _side_cut))
			fy = signf(fy) * lerpf(absf(fy), kept, _drift_engagement)
		# The sideways force goes in where Godot's does: the contact's height
		# over the centre of mass scaled by `side_force_depth` (Bullet's
		# `m_rollInfluence`). At the contact itself this car's cornering grip
		# is a rolling moment — on the street it tipped onto its side at a kerb;
		# at the engine-tyre car's 0.2 the drift lost its load transfer.
		var arm: Vector3 = point - com
		var raised: Vector3 = arm - up * arm.dot(up) * (1.0 - tyre.side_force_depth)
		apply_force(forward * fx, point - global_position)
		apply_force(side * fy, com + raised - global_position)
	_turn_visuals(delta)
	_cost_us += Time.get_ticks_usec() - started
	_cost_ticks += 1


## Stability control's understeer cut: the share of the forward drive left
## while traction control is armed and the fronts are turned: 1 with the wheel
## straight, `1 - understeer_power_cut` at the
## lock the speed allows. The doubled drive the slide once needed (`Q153`)
## otherwise accelerated a full-lock corner to about 128 kph from any entry,
## its arc widening with no scrub, where the shipped car settles at 62-65
## (`Q153`). Read off the front wheels' own angle, so the catch cap and the
## rate limit count. Forward drive only: reversing is not the corner.
func _turn_drive_share() -> float:
	if stability_control.understeer_power_cut <= 0.0 or _drive_n <= 0.0:
		return 1.0
	return 1.0 - stability_control.understeer_power_cut * _steer_share()


## The front wheels' angle over the lock the speed allows, 0 straight to 1 at
## full lock: what the understeer cut and the drive boost fade on. Read off the
## wheels' own angle, so the catch cap and the rate limit count.
func _steer_share() -> float:
	var lock: float = _steer_lock_rad(clampf(absf(speed_kph) / profile.max_speed_kph, 0.0, 1.0))
	if lock <= 0.0:
		return 0.0
	return minf(absf(steering) / lock, 1.0)


## Stability control's slip cut: the share of the forward drive left while
## drift mode is on: 1 under `slip_power_cut_from_deg` of rear-axle slip, none at
## `slip_power_cut_to_deg`. A key or a thumb holds full throttle, and with
## the rim free to overspeed a plain held tap ran to 48-65° (`Q153`, the user's
## street report: "the rear feels too spinny"). It takes power away and asks
## for no angle (`Q72`): under the band the slide is the throttle's and the
## countersteer's, as before.
func _slide_drive_share() -> float:
	var cut: StabilityControlProfile = stability_control
	return _slip_cut_share(cut.slip_power_cut_from_deg, cut.slip_power_cut_to_deg)


## Stability control's slip cut on the road: the share of the forward drive
## left while drift mode is off — 1 under `armed_slip_cut_from_deg` of body
## slip, none at `armed_slip_cut_to_deg` — so a tail stepping out under power is
## caught as a real ESC catches it. Forward drive only.
func _armed_slip_share() -> float:
	var cut: StabilityControlProfile = stability_control
	return _slip_cut_share(cut.armed_slip_cut_from_deg, cut.armed_slip_cut_to_deg)


## The forward drive left by a slip cut over `from`–`to` degrees of rear-axle slip:
## 1 under `from`, none at `to`. 1 when the band is not authored (`to` not over
## `from`), on reverse drive, and past `REVERSED_SLIP_DEG`, where the car is
## travelling backwards and the throttle must brake the roll.
func _slip_cut_share(from: float, to: float) -> float:
	if to <= from or _drive_n <= 0.0:
		return 1.0
	# Under the tyre's low-speed floor the rear axle's travel is mostly the
	# car's own rotation, near 90° of slip on a pivot: no cut, as a real ESC
	# stands aside at a crawl.
	if linear_velocity.length() < tyre.low_speed_mps:
		return 1.0
	var slip: float = FareSystem.slip_deg_of(rear_axle_velocity(), -global_basis.z)
	if slip > REVERSED_SLIP_DEG:
		return 1.0
	return 1.0 - clampf(inverse_lerp(from, to, slip), 0.0, 1.0)


## The rear side cut (an arcade aid) for a press at `kph`: `drift_side_cut` up to
## `drift_side_cut_from_kph`, easing to `drift_side_cut_fast` by
## `drift_side_cut_to_kph`. With no band set, `drift_side_cut` at every speed.
func _side_cut_at(kph: float) -> float:
	var aids: ArcadeAidsProfile = arcade_aids
	if aids.drift_side_cut_to_kph <= aids.drift_side_cut_from_kph:
		return aids.drift_side_cut
	var along: float = inverse_lerp(aids.drift_side_cut_from_kph, aids.drift_side_cut_to_kph, kph)
	return lerpf(aids.drift_side_cut, aids.drift_side_cut_fast, clampf(along, 0.0, 1.0))


## The wheel's spin after `seconds`, solved implicitly: the spin at which the
## wheel's inertia, `torque`, the tyre's force at that very spin and a brake of
## `hold_nm` balance. The brake is Coulomb friction — it holds a wheel still
## when the other torques at rest are within it, and otherwise opposes the
## spin it leaves. `at_rest` is the tyre's force on a wheel held still, the
## same for every substep of the wheel's tick. Leaves the force at the returned
## spin in `_solved`.
##
## ⚠️ **Explicit, the step limit-cycled; clamped, it lost the slide.** Past the
## curve's peak the slope turns negative and a light wheel stepped explicitly
## jumps across the road's speed: a braked wheel from 42 kph cycled until the
## forces cancelled and the car crept at 1.2 m/s with the pedal down. Clamping
## each step at zero slip stopped that and also stopped the drive carrying the
## rim past the road's speed inside a step — the tap at 63 kph fell from 35°
## to 8°. Solved, the brake reads within 2% of the shipped car and the tap is
## 35° again. The residual is monotone at the shipped substeps (the inertia
## term outweighs the tyre's falling slope), and the safeguarded Newton below
## keeps to its bracket if it is not.
func _solve_spin(
	omega: float, torque: float, hold_nm: float, seconds: float, at_rest: Vector2
) -> float:
	var stiffness: float = tyre.wheel_inertia_kgm2 / seconds
	var brake_sign: float = 0.0
	if hold_nm > 0.0:
		var unheld: float = -stiffness * omega - torque + _radius * at_rest.x
		if absf(unheld) <= hold_nm:
			_solved = at_rest
			return 0.0
		brake_sign = 1.0 if unheld < 0.0 else -1.0
	var bias: float = torque - brake_sign * hold_nm
	var reach: float = _radius * _peak_n / stiffness
	var low: float = omega + (bias / stiffness) - reach
	var high: float = omega + (bias / stiffness) + reach
	if brake_sign > 0.0:
		low = maxf(low, 0.0)
	elif brake_sign < 0.0:
		high = minf(high, 0.0)
	var spin: float = clampf(omega, low, high)
	for _k: int in SOLVE_ITERATIONS:
		_solved = _force(spin * _radius)
		var residual: float = stiffness * (spin - omega) - bias + _radius * _solved.x
		if absf(residual) < SOLVE_TOLERANCE_NM:
			return spin
		if residual < 0.0:
			low = spin
		else:
			high = spin
		# The residual's exact slope: the inertia, and the tyre's through `_force`.
		var slope: float = stiffness + _radius * _radius * _slope_x
		var next: float = spin - residual / slope if slope > 0.0 else NAN
		spin = next if next > low and next < high else 0.5 * (low + high)
	_solved = _force(spin * _radius)
	return spin


## The tyre's force in its own frame, x forward and y to the right, for the
## wheel being solved with its rim moving at `rim_mps`. Leaves the forward
## force's slope against rim speed in `_slope_x`, exact off the curve
## `sin(C atan(B s))`, for the spin solve's Newton step.
func _force(rim_mps: float) -> Vector2:
	var slip_x: float = (rim_mps - _along) * _per_slip
	var slip: float = sqrt(slip_x * slip_x + _slip_y * _slip_y)
	var bent: float = _curve_b * slip
	if slip < 1e-6:
		_slope_x = _peak_n * _curve_c * _curve_b * _per_slip
		return Vector2.ZERO
	var angle: float = _curve_c * atan(bent)
	var share: float = sin(angle) / slip
	var rise: float = cos(angle) * _curve_c * _curve_b / (1.0 + bent * bent)
	var along_share: float = slip_x * slip_x / (slip * slip)
	_slope_x = _peak_n * (rise * along_share + share * (1.0 - along_share)) * _per_slip
	var magnitude: float = _peak_n * share
	return Vector2(magnitude * slip_x, -magnitude * _slip_y)


## The suspension force Godot applied to wheel `i`, rebuilt from what it does
## publish: the contact point gives the spring's length from the hardpoint,
## and the wheel's own spring and damper give the force. `_ray_cast` and
## `_update_suspension` in `vehicle_body_3d.cpp`, restated — `Q152`'s probe
## holds the four to the car's weight at rest.
##
## ⚠️ **Godot's ray starts one radius ABOVE the hardpoint and its hit distance
## is rescaled onto the rest length**, so the spring's length is not the hub's
## drop minus a radius. Read that way first, the four loads summed to 1.50× the
## weight — the whole error was the 6.3 mm the hub sits under one radius.
func _load_n(i: int, point: Vector3, normal: Vector3) -> float:
	var wheel: VehicleWheel3D = _wheels[i]
	var ray: Vector3 = -global_basis.y
	var radius: float = wheel.wheel_radius
	var rest: float = wheel.wheel_rest_length
	var reach: float = rest + radius
	var from_source: float = (point - global_transform * _hardpoints[i]).dot(ray) + radius
	var length: float = clampf(
		from_source * reach / (reach + radius) - radius,
		rest - wheel.suspension_travel,
		rest + wheel.suspension_travel
	)
	var facing: float = normal.dot(ray)
	var inverse: float = 1.0 / -CONTACT_DOT_FLOOR
	var closing: float = 0.0
	if facing < CONTACT_DOT_FLOOR:
		inverse = -1.0 / facing
		var at_contact: Vector3 = linear_velocity + angular_velocity.cross(point - global_position)
		closing = normal.dot(at_contact) * inverse
	var damping: float = wheel.damping_compression if closing < 0.0 else wheel.damping_relaxation
	var force: float = wheel.suspension_stiffness * (rest - length) * inverse - damping * closing
	return clampf(force * mass, 0.0, wheel.suspension_max_force)


## Turns each tyre mesh by the model's spin less the engine's, so a locked
## wheel stands still and a spinning one spins, where the engine rolls every
## wheel at road speed (`Q85`). `get_rpm` is the engine's roll rate, negative
## rolling forward on this rig (`DRIVE_SIGN`).
func _turn_visuals(delta: float) -> void:
	for i: int in _wheels.size():
		var visual: Node3D = _visuals[i]
		if visual == null:
			continue
		_spin_angle[i] = wrapf(_spin_angle[i] + _omega[i] * delta, -PI, PI)
		_engine_angle[i] = wrapf(
			_engine_angle[i] - _wheels[i].get_rpm() * TAU / 60.0 * delta, -PI, PI
		)
		# Rolling forward turns the top of the tyre towards -Z, which is a
		# negative turn about the axle's +X.
		visual.rotation.x = -angle_difference(_engine_angle[i], _spin_angle[i])
