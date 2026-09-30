class_name TyreVehicleController
extends VehicleController
## The shipped car with its tyres replaced by a per-wheel model (`P3-52`,
## `Q152`): a spike on the skidpad, never loaded by the game.
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
##   4. A countersteer assist on top of the parent's steering while the car
##      slides (`_update_steering`). Shipped at 0 — countersteering is the
##      player's skill, on the user's call (`tyre.md`) — and kept behind it.
##      A wider steering lock for the player on the countersteer side while
##      the car slides (`_steer_lock_rad`) is also behind a zero: swept and
##      refuted on the pad's driver.
##   5. A cap on the countersteer once a caught slide turns the car the other
##      way (`_cap_catch`), because a key held down holds full lock past the
##      catch (`Q152`'s catch round). On at 6°; the user's drive is the veto.
##
## Everything else — the player's steering, the speed taper, coast drag, wall
## response, auto-righting, the published reads the fare and the lamps take —
## is the parent's, unchanged, so the skidpad and a street drive grade this car
## with no special case.
##
## ⚠️ **A table with a zero key leaves the car on the engine's tyres**: every
## override hands straight back to the parent, so the car drives as the
## shipped one rather than on no tyres at all (`usable`).

## The spin solve stops when the torques balance to within this, or after
## this many iterations — a safeguarded Newton, so it never leaves its bracket.
const SOLVE_TOLERANCE_NM: float = 0.5
const SOLVE_ITERATIONS: int = 12
## Normal-to-ray alignment under which Godot stops trusting the contact and
## pins its damper — `vehicle_body_3d.cpp`'s own -0.1, restated for `_load_n`.
const CONTACT_DOT_FLOOR: float = -0.1

@export var tyre: TyreProfile

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
## The wheel's own spin angle, and the one Godot is rolling it by, so the tyre
## mesh can show the model's spin rather than the road's.
var _spin_angle: PackedFloat32Array = PackedFloat32Array()
var _engine_angle: PackedFloat32Array = PackedFloat32Array()
var _visuals: Array[Node3D] = []
## True from a drift press until the slide is over: traction control stands
## down for the slide the player asked for. See `traction_rearm_s`.
var _traction_off: bool = false
## Seconds since the drift button came up while traction control is off.
var _released_s: float = 0.0
## The drive force per traction wheel and the brake dial as the parent set them
## this tick, before this class took them back off the engine.
var _drive_n: float = 0.0
var _brake_dial: float = 0.0
## Microseconds spent in `_apply_tyres` and the ticks that spent them, for the
## skidpad's cost column.
var _cost_us: int = 0
var _cost_ticks: int = 0
var _usable: bool = false
## The player's steering as the parent's rate limit left it, before the
## countersteer assist was added; restored before the parent's next step so
## the limit ramps the player's angle and never the assist's.
var _driver_steering: float = 0.0
## The side the slide went out on, in Godot's steering sign, latched while the
## tail is out past the tyre's peak: `_slide_toward` flips as the catch carries
## the slip through zero, which is when `_cap_catch` needs it. 0 before any.
var _slide_side: float = 0.0
## Seconds since the tail was last out past the tyre's peak.
var _since_slide_s: float = INF
## True from the car turning the other way until the player lets the
## countersteer go, or it goes on past `catch_window_s`.
var _catch_capped: bool = false
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
	_usable = usable(tyre)
	if not _usable:
		return
	_wheels.append_array(_front)
	_wheels.append_array(_rear)
	for wheel: VehicleWheel3D in _wheels:
		_hardpoints.append(wheel.position)
		wheel.wheel_friction_slip = 0.0
		_visuals.append(wheel.get_node_or_null(^"Visual") as Node3D)
	_omega.resize(_wheels.size())
	_loads.resize(_wheels.size())
	_spin_angle.resize(_wheels.size())
	_engine_angle.resize(_wheels.size())


## Whether `table` can run the model. `handbrake_torque_nm`,
## `yaw_assist_scale`, `traction_limit`, `traction_rearm_s` and
## `side_force_depth` may legally be 0 — no handbrake, no assist, no traction
## control, re-arm on the slip alone, the force at the centre of mass — so a
## missing one cannot be told from a chosen one and is not guarded.
static func usable(table: TyreProfile) -> bool:
	if table == null:
		push_error("TyreVehicleController: no TyreProfile; the car keeps the engine's tyres.")
		return false
	var fields: Dictionary[String, float] = {
		"mu": table.mu,
		"slide_ratio": table.slide_ratio,
		"peak_slip_ratio": table.peak_slip_ratio,
		"peak_slip_angle_deg": table.peak_slip_angle_deg,
		"wheel_inertia_kgm2": table.wheel_inertia_kgm2,
		"low_speed_mps": table.low_speed_mps,
		"substeps": float(table.substeps),
		"drive_scale": table.drive_scale,
	}
	return not TuningTable.any_zero(
		table, fields, "TyreVehicleController", "the car keeps the engine's tyres"
	)


## Each wheel's last rebuilt load in newtons, front axle first. For the probe
## and the skidpad; nothing in the game reads it.
func wheel_loads_n() -> PackedFloat32Array:
	return _loads


## Mean microseconds per tick spent in the tyre model since the last call, and
## resets — the skidpad's cost column.
func take_tyre_cost_us() -> float:
	var mean: float = float(_cost_us) / float(_cost_ticks) if _cost_ticks > 0 else 0.0
	_cost_us = 0
	_cost_ticks = 0
	return mean


## The parent's steering, then the countersteer assist on top: the front
## wheels turned towards the travel by `countersteer_assist` of the slip angle
## beyond the tyre's peak, up to `countersteer_lock_deg`. Built because keyboard
## and touch steer near on-off; shipped at 0 because the user wants the
## countersteer to be the player's (`tyre.md` has both tables). `steer_ratio`,
## which the lamps read, stays the player's.
##
## ⚠️ Not a slip setpoint (`Q72`): the assist aims the fronts along the travel
## and asks for no angle. The throttle and the rear tyres set the slide.
func _update_steering(delta: float) -> void:
	if not _usable:
		super._update_steering(delta)
		return
	steering = _driver_steering
	super._update_steering(delta)
	_cap_catch(delta)
	_driver_steering = steering
	if tyre.countersteer_assist <= 0.0:
		return
	var beyond: float = _slide_beyond_peak_rad()
	if beyond <= 0.0:
		return
	# Never less lock than the player already has: the assist adds to their
	# angle and is clamped only where it would pass `countersteer_lock_deg`.
	var lock: float = maxf(deg_to_rad(tyre.countersteer_lock_deg), absf(steering))
	steering = clampf(steering + _slide_toward() * beyond * tyre.countersteer_assist, -lock, lock)


## Caps the player's countersteer at `catch_lock_deg` once a caught slide turns
## the car the other way. The catch round found no snap on either car: full
## opposite lock on gripping tyres turns the car the other way at about 90°/s
## once the slide is caught, and a key holds full lock for as long as it is
## down; with the throttle held, the turn starts only once the wheel is at full
## lock, so the lock kept is the lever and the steering rate is not (`Q152`).
##
## Keyed on the heading reversing, not the slip falling back under the tyre's
## peak: the car turns the other way before the slide reads as caught. Holds
## while the player keeps countersteering and the slide was live within
## `catch_window_s`; the player letting go, or the window running out, hands
## back the full lock at the parent's attack rate.
##
## Applied to the player's own angle, after the parent's rate limit, so the
## limit ramps from the capped angle, and so `steer_ratio` — which the lamps
## read, and the skidpad's `wheel` column — stays the player's input: read
## `steering` for the front wheels. The cap lands in the tick it engages, where
## the rack's release would take two or three. Never an angle added (`Q72`).
func _cap_catch(delta: float) -> void:
	if tyre.catch_lock_deg <= 0.0:
		return
	# Latched on a tail-out slide only: the nose turning past the travel, so
	# the yaw rate and the countersteer's sign disagree. A plough at turn-in is
	# past the peak too, with the travel on the other side of the nose, and
	# latched it read the player's steering into the turn as a countersteer
	# (42 kph: the tap's peak 28.0° → 22.3°). The catch's own reversal fails
	# the test as well, which keeps the side the slide went out on.
	var toward: float = _slide_toward()
	if _slide_beyond_peak_rad() > 0.0 and angular_velocity.y * toward < 0.0:
		_slide_side = toward
		_since_slide_s = 0.0
	else:
		_since_slide_s += delta
	# Countersteering: the player's input towards the side the slide went out
	# on, in the steering angle's sign (see `_steer_lock_rad`).
	var countersteering: bool = -steer_input * _slide_side > 0.0
	if not countersteering or _since_slide_s >= tyre.catch_window_s:
		_catch_capped = false
		return
	if not _catch_capped:
		# A positive yaw rate turns the nose left, Godot's positive steering,
		# so the car turns the other way when the two signs agree.
		_catch_capped = angular_velocity.y * _slide_side > deg_to_rad(tyre.catch_turn_dps)
	if _catch_capped and steering * _slide_side > 0.0:
		steering = _slide_side * minf(absf(steering), deg_to_rad(tyre.catch_lock_deg))


## Whether `_cap_catch` holds the countersteer this tick, for the skidpad.
func catch_capped() -> bool:
	return _catch_capped


## The lock the player has while the car slides: the parent's speed-narrowed
## lock, widened to `slide_lock_deg` on the countersteer side alone once the
## slip is past the tyre's peak. Built on the suspicion that the handling
## table's lock (16° at 63 kph, under 14° at 86) was why a countersteered
## slide at 86 kph fell short of the fare's 2 s; swept and refuted — every
## value past the table's lock SHORTENED `hold` at all three speeds, because
## the pad's driver steers a share of the lock it has and a wider one makes
## its catch a straightening (`tyre.md`). Shipped absent, so 0 and inert; kept
## because a player's hands, unlike the driver's, scale to the wheel, and the
## user's own drive is the grade that could still want it. One side only: a
## wider lock INTO the slide at 86 kph is a spin, not a skill. No angle asked
## for (`Q72`).
func _steer_lock_rad(speed_ratio: float) -> float:
	var lock: float = super._steer_lock_rad(speed_ratio)
	if not _usable or tyre.slide_lock_deg <= 0.0 or _slide_beyond_peak_rad() <= 0.0:
		return lock
	# `steer_input` is +1 for right, and the parent negates it into Godot's
	# positive-left angle; `_slide_toward` is in the angle's sign, so the
	# player is countersteering when the two have opposite signs.
	if -steer_input * _slide_toward() <= 0.0:
		return lock
	return maxf(lock, deg_to_rad(tyre.slide_lock_deg))


## How far the body's slip is past the tyre's peak, in radians, or 0 when it
## is not sliding forward. The size is the game's own slip
## (`FareSystem.slip_deg_of`, the one the fare pays on). Forward travel only:
## backing up reads as a slip near 180° and would snap the fronts to full
## lock; past 90° the car has spun anyway.
func _slide_beyond_peak_rad() -> float:
	var nose: Vector3 = -global_basis.z
	if linear_velocity.dot(nose) <= 0.0 or linear_velocity.length() < tyre.low_speed_mps:
		return 0.0
	var slip_deg: float = FareSystem.slip_deg_of(linear_velocity, nose)
	return maxf(deg_to_rad(slip_deg - tyre.peak_slip_angle_deg), 0.0)


## The countersteer's sign in Godot's steering angle: from the cross product's
## up component, positive when the travel is left of the nose — Godot's
## positive (left) steering, the countersteer for a tail out to the left.
func _slide_toward() -> float:
	return signf((-global_basis.z).cross(linear_velocity).y)


## The parent's pedals, taken back off the engine: `engine_force` and `brake`
## act through the friction this class has zeroed, so they are read here and
## applied as torque in `_apply_tyres` instead.
func _apply_drive() -> void:
	super._apply_drive()
	if not _usable:
		return
	# The parent writes `DRIVE_SIGN × force`, so the product is forward-positive.
	_drive_n = engine_force * DRIVE_SIGN
	_brake_dial = brake
	engine_force = 0.0
	brake = 0.0


## The drift button is a handbrake here, not a grip cut: the ramp and the held
## clock still run, because the yaw assist reads them, and the tyres come last
## so they see this tick's pedals.
func _apply_drift(delta: float) -> void:
	if not _usable:
		super._apply_drift(delta)
		return
	_ramp_drift(delta)
	if tyre.yaw_assist_scale > 0.0:
		_apply_drift_yaw(tyre.yaw_assist_scale)
	_apply_tyres(delta)


## Nothing to write: the engine's friction stays at zero, and the parent's
## `place_at` calls this to restore a grip this model does not use.
func _write_drift_grip() -> void:
	if not _usable:
		super._write_drift_grip()


func place_at(pose: Transform3D) -> void:
	super.place_at(pose)
	_drive_n = 0.0
	_brake_dial = 0.0
	_omega.fill(0.0)
	_loads.fill(0.0)
	_traction_off = false
	_released_s = 0.0
	_driver_steering = 0.0
	_slide_side = 0.0
	_since_slide_s = INF
	_catch_capped = false


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
	var top_mps: float = profile.max_speed_kph / 3.6
	_rearm_traction(delta)
	var governor: bool = tyre.traction_limit > 0.0 and not _traction_off
	for i: int in _wheels.size():
		var wheel: VehicleWheel3D = _wheels[i]
		_radius = wheel.wheel_radius
		var drive_nm: float = (
			_drive_n * tyre.drive_scale * _radius if wheel.use_as_traction else 0.0
		)
		# A limiter on the wheel, where the parent's taper is on the body: a
		# spinning tyre must not run the wheel past top speed either.
		if absf(_omega[i]) * _radius >= top_mps and signf(drive_nm) == signf(_omega[i]):
			drive_nm = 0.0
		var hold_nm: float = brake_nm * _radius
		if drift_input and i >= _front.size():
			hold_nm += tyre.handbrake_torque_nm
		if not wheel.is_in_contact():
			# No tyre force off the ground, so the spin is closed-form.
			_loads[i] = 0.0
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
			var torque_nm: float = drive_nm
			if (
				governed
				and absf(slip_x) >= tyre.traction_limit
				and signf(drive_nm) == signf(slip_x)
			):
				torque_nm = 0.0
			omega = _solve_spin(omega, torque_nm, hold_nm, step, at_rest)
			sum += _solved
		_omega[i] = omega
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
		# The sideways force goes in where Godot's does: the contact's height
		# over the centre of mass scaled by `side_force_depth` (Bullet's
		# `m_rollInfluence`, the handling table's `roll_influence`). At the contact itself this car's cornering grip
		# is a rolling moment — on the street it tipped onto its side at a kerb.
		# The tyre table's own share (`TyreProfile.side_force_depth`), not the
		# handling table's 0.2, which took the drift's load transfer away.
		var arm: Vector3 = point - com
		var raised: Vector3 = arm - up * arm.dot(up) * (1.0 - tyre.side_force_depth)
		apply_force(forward * fx, point - global_position)
		apply_force(side * fy, com + raised - global_position)
	_turn_visuals(delta)
	_cost_us += Time.get_ticks_usec() - started
	_cost_ticks += 1


## Off at a drift press, and back on once the button has been up for
## `traction_rearm_s` and the car's slip is under the bar the game scores a
## slide on — the slide the player asked for is over. Keyed on the body's slip
## rather than the tyres': after a handbrake tap the rear tyres spin back up
## to road speed before the throttle can take the slide over, and re-armed on
## that the governor cut the very torque the slide needed (the `hold` row at
## 63 kph fell from 2.22 s to nothing).
func _rearm_traction(delta: float) -> void:
	if drift_input:
		_traction_off = true
		_released_s = 0.0
		return
	if not _traction_off:
		return
	_released_s += delta
	var slip: float = FareSystem.slip_deg_of(linear_velocity, -global_basis.z)
	if _released_s >= tyre.traction_rearm_s and slip < profile.drift_slip_threshold_deg:
		_traction_off = false


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
