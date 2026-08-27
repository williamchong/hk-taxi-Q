## Grades the shipped handling model on `skidpad.tscn` — four manoeuvres, one
## table, no human at the keyboard.
##
##     godot --headless --path game --script "$PWD/tools/skidpad_ablation.gd"
##     godot --headless --path game --script "$PWD/tools/skidpad_ablation.gd" -- --only=drift
##
## **Why this exists.** Every handling figure in `docs/PROGRESS.md` came from a
## throwaway probe that was deleted before anyone could question it, and one of
## them was published from `city_drive.tscn` and had to be withdrawn — a 0.14°
## micro-gradient there is worth the whole quantity under test (`P0-5b/c/d`).
## This is the repeatable version. Run it before and after a change to
## `VehicleController`'s drive model or `handling.tres` and paste both tables.
##
## **It grades, it does not check.** No thresholds, no pass/fail, no place in
## `tools/check.sh` — the numbers are the output, and what they should be is a
## design question. It exits non-zero only when the run itself broke.
##
## Lives in `tools/` rather than `game/tools/` for the reason `driver.gd` gives:
## agent tooling stays out of the exported PCK. `--script` resolves relative
## paths against `res://`, so the absolute path above is not optional.
##
## Needs no generated city. `skidpad.tscn` builds its ground from
## `greybox_wanchai.json`, which is committed, so this runs on a fresh clone.
extends SceneTree

const DEFAULT_SCENE: String = "res://scenes/dev/skidpad.tscn"

## Every manoeuvre, in table order.
const MANOEUVRES: PackedStringArray = ["corner", "drift", "tap", "brake", "coast"]

## The subset that can possibly move when a `DRIFT_FIELD_PREFIX` field does — the
## only ones such a sweep re-runs. Nothing else holds the drift button, so nothing
## else reaches `VehicleController._apply_drift`.
const DRIFT_MANOEUVRES: PackedStringArray = ["drift", "tap"]

## The profile field a sweep writes when `--sweep` does not name another, and the
## field `--drift-grip` is an alias for.
##
## ⚠️ Set through `Object.set()`, which is a **silent no-op** on a name the
## resource does not have. Rename the field and every swept row comes back
## identical, correctly labelled, and describing a value that was never applied —
## a published table of numbers nobody measured. `_measure_all` refuses the run
## instead, before any manoeuvre is simulated.
const DEFAULT_SWEEP_FIELD: StringName = &"drift_rear_grip_scale"

## Name prefix marking a field whose effect is confined to the drift branch.
##
## ⚠️ **This decides whether a sweep re-runs three extra manoeuvres or reprints
## the first value's rows under later labels.** `drift_*` reaches nothing but
## `_apply_drift`, so `corner`, `brake` and `coast` cannot move and re-running
## them is 13.5 s of simulation per value to reproduce rows already printed. Any
## other field — `engine_force`, `tyre_grip` — moves all five, and skipping them
## would dress stale rows up as measurements of a value never applied to them.
const DRIFT_FIELD_PREFIX: String = "drift_"

## The profile field `secs>thr` counts against.
##
## ⚠️ **This is the design target, and it is NOT a tuning knob.** The knob is
## whatever `_sweep_field` names; the threshold is what that knob is graded
## against. Lower it to make `seconds_above_deg` look better and the column
## becomes `Q58`'s `drawn_gauge_m` — a number bounded by the bar it is measured
## against, which cannot report the thing it exists to report. Read through `get()` and guarded
## by `in` for `DEFAULT_SWEEP_FIELD`'s reason: `set()`/`get()` swallow a rename
## silently.
const SLIP_THRESHOLD_FIELD: StringName = &"drift_slip_threshold_deg"

## Default seconds of full throttle before every manoeuvre, to reach a working
## speed. Long enough to be well past the initial squat, short enough that the car
## is nowhere near the 140 kph limiter where the drive taper distorts things.
##
## ⚠️ **Overridable since `--run-up`, and a fixed entry speed is exactly what hid
## a defect.** Every other column is only comparable because entry is identical
## across rows, so this stays constant *within* a run — but a dial whose effect
## depends on speed cannot be graded at one speed at all, and the drift's yaw
## assist was tuned at the 63 kph this produces and then applied at 84, where the
## same tap spins the car. Vary it between runs, never expect two run-ups to be
## comparable on anything but the trend.
const DEFAULT_RUN_UP_S: float = 4.0

## Seconds the manoeuvre itself is held and measured.
const MANOEUVRE_S: float = 4.0

## Seconds a reset car is left alone before the run-up, so one manoeuvre is not
## measured against the suspension transient of the last.
const SETTLE_S: float = 0.5

## How long the `tap` manoeuvre holds the drift button before letting go, while
## steering stays on for the full `MANOEUVRE_S`.
##
## The pair matters more than either number. `drift` holds the button for the
## whole corner, which is what the *design* promises a player can do; `tap` uses
## it the way a driver does, to break the tail loose and then release. A model
## can pass one and fail the other, and knowing which is the whole question.
const TAP_S: float = 0.5

## How long a to-rest manoeuvre may take before it is called a failure rather
## than waited on. The coast case is the slow one: 6.5 s from 31 kph measured at
## `rolling_resistance_mps2 = 0.8`, and a regression there is exactly the fifth
## `P0-5b/c/d` bug, where the car never stopped at all.
const TO_REST_LIMIT_S: float = 30.0

## Speed under which the car counts as stopped, in kph. Matches
## `VehicleController.STATIONARY_KPH`, where one pedal stops meaning brake and
## starts meaning reverse — below this a "braking" run is accelerating backwards.
const STOPPED_KPH: float = 1.0

## Ground speed under which a slip angle is noise rather than a measurement: a
## nearly stationary car has a velocity vector pointing anywhere at all.
const SLIP_FLOOR_MPS: float = 1.0

var _only: String = ""
## The scene to grade. Configurable rather than constant so a roster car can be
## put on the same ground and spawn later. ⚠️ Never `city_drive.tscn`: a 0.14°
## micro-gradient there is worth the whole quantity under test, and a published
## figure has already had to be withdrawn over it (`P0-5b/c/d`).
var _scene_path: String = DEFAULT_SCENE
## Seconds of run-up, and so the entry speed every row is measured from. Reported
## as `entry kph` rather than requested, because the run-up is open-loop: this
## asks for seconds of throttle and the car answers with whatever speed it made.
var _run_up_s: float = DEFAULT_RUN_UP_S
## Values to sweep `_sweep_field` over, or empty for whatever `handling.tres`
## ships. Set live on the loaded resource rather than by editing the file:
## nothing caches it, so it takes effect on the next tick, and a sweep that
## crashed halfway cannot leave the committed tuning holding a probe value.
##
## ⚠️ **Editing the `.tres` in a shell loop is the alternative this exists to
## avoid.** One such loop misfired on `set --`, blanked the field it was sweeping
## and published a table of all-zero rows that looked like a finding.
var _sweep: Array[float] = []
## The profile field `_sweep` writes. A variable rather than a constant since
## `--sweep`, because the drift now has three yaw dials and a grid of them run
## through hand-edited tuning files is the hazard above.
var _sweep_field: StringName = DEFAULT_SWEEP_FIELD
## Slip angle `seconds_above_deg` counts against, read off the profile at boot.
## INF when the profile does not publish one, which makes the column read 0.00
## everywhere rather than inventing a bar this project never authored.
var _slip_threshold_deg: float = INF
var _failures: Array[String] = []
## ⚠️ **Typed `RigidBody3D`, and every controller method below goes through
## `call()`, because naming `VehicleController` here breaks the car.**
##
## `handling_profile.gd` states the mechanism: the controller reads the
## `InputRouter` autoload, autoloads are not registered under `--script`, and so
## resolving that class while *this* script compiles — which a type annotation
## does, in `_init`, before the first frame — fails. The failure is not loud.
## GDScript caches the broken class, `taxi.tscn` then instances a `VehicleBody3D`
## with a **null script**, and the run reports "no vehicle" while the wheels,
## which are engine classes touching no autoload, are found perfectly. Measured here before
## `driver.gd`'s duck-typing was understood to be deliberate.
var _vehicle: RigidBody3D = null
var _spawn: Transform3D = Transform3D.IDENTITY
var _step: float = 0.0
## Rows actually printed. The success test, because the ordinary GDScript
## failure here is not an exception this can catch: a run-time script error kills
## the coroutine where it stands, `_failures` stays empty, and `_finish` cheerfully
## exits 0 with no table. Measured — an `Array` / `Array[float]` mismatch did
## exactly that. Counting output is the only claim worth making.
var _printed_rows: int = 0


## One manoeuvre's measurements. A class rather than a Dictionary so a typo in a
## field name is a parse error instead of a null three prints later.
class Result:
	extends RefCounted

	var name: String = ""
	var entry_kph: float = 0.0
	var exit_kph: float = 0.0
	## Seconds the measured phase actually ran, which is `MANOEUVRE_S` for the
	## held manoeuvres and however long it took for the to-rest ones.
	var seconds: float = 0.0
	## Exponential speed decay, per second: `ln(entry / exit) / seconds`. The
	## same shape the coast and drag figures in `docs/PROGRESS.md` use, because
	## Godot's `default_linear_damp` is viscous and those numbers are its rate.
	var decay_per_s: float = 0.0
	## Mean deceleration over the phase, in m/s². The honest figure for braking,
	## where the force is meant to be constant and a decay rate would hide that.
	var decel_mps2: float = 0.0
	## Largest angle between where the car pointed and where it was going.
	var peak_slip_deg: float = 0.0
	## Seconds spent at or above `drift_slip_threshold_deg`.
	##
	## ⚠️ **This is the statistic the game scores and `peak_slip_deg` is not.**
	## `GAME_DESIGN.md` pays drift as points *per second* above a threshold, so a
	## tune whose peak merely touches the threshold scores for ~0 s. A peak is a
	## `maxf` over one tick and cannot see duration; keep both, because dwell
	## alone cannot tell a drift from a spin and `yaw_deg` is what separates them.
	var seconds_above_deg: float = 0.0
	## Heading swept over the phase — how far round the manoeuvre brought the
	## car. Separates a drift from a spin far more clearly than slip does.
	var yaw_deg: float = 0.0
	var distance_m: float = 0.0


func _init() -> void:
	_run.call_deferred()


func _run() -> void:
	# Autoloads are registered on the first frame, not before: `InputRouter` is
	# unreachable until this returns, and the car reads it every tick.
	await process_frame

	if _parse_args() and await _boot():
		await _measure_all()
	_release_everything()
	_finish()


func _parse_args() -> bool:
	for arg: String in OS.get_cmdline_user_args():
		var bits: PackedStringArray = arg.split("=", true, 1)
		if bits.size() < 2 or bits[1].is_empty():
			_fail("%s needs a value, as %s=..." % [bits[0], bits[0]])
			return false
		match bits[0]:
			"--only":
				_only = bits[1]
			"--scene":
				_scene_path = bits[1]
			"--run-up":
				if not bits[1].is_valid_float():
					_fail("--run-up wants a number of seconds, got '%s'" % bits[1])
					return false
				_run_up_s = bits[1].to_float()
				if _run_up_s <= 0.0:
					_fail("--run-up must be positive, got %s" % _run_up_s)
					return false
			"--sweep":
				# Split once more, so the field name carries its own "=" separator
				# and `--sweep=drift_yaw_decay_s=0.4,0.6` reads as one flag.
				var spec: PackedStringArray = bits[1].split("=", true, 1)
				if spec.size() < 2 or spec[0].is_empty() or spec[1].is_empty():
					_fail("--sweep wants field=v1,v2,..., got '%s'" % bits[1])
					return false
				_sweep_field = StringName(spec[0])
				if not _parse_sweep_values(spec[1], "--sweep"):
					return false
			"--drift-grip":
				_sweep_field = DEFAULT_SWEEP_FIELD
				if not _parse_sweep_values(bits[1], "--drift-grip"):
					return false
			_:
				_fail("unknown argument %s" % bits[0])
				return false
	return true


## Shared by `--sweep` and its `--drift-grip` alias so the two cannot disagree
## about what counts as a number.
func _parse_sweep_values(text: String, flag: String) -> bool:
	# 🔴 One sweep per run, refused rather than merged. Both flags append into the
	# same `_sweep` while `_sweep_field` is simply overwritten by whichever parsed
	# last, so `--sweep=drift_yaw_decay_s=0.4,0.6 --drift-grip=0.62` would write all
	# three values to `drift_rear_grip_scale` and print every row correctly labelled
	# with a value applied to a field it was never meant for. That is the published
	# table of numbers nobody measured this whole tool exists to prevent.
	if not _sweep.is_empty():
		_fail("%s: only one sweep per run, and one is already set" % flag)
		return false
	for piece: String in text.split(",", false):
		if not piece.is_valid_float():
			_fail("%s wants numbers, got '%s'" % [flag, piece])
			return false
		_sweep.append(piece.to_float())
	return true


func _boot() -> bool:
	if not ResourceLoader.exists(_scene_path):
		_fail("no such scene: %s" % _scene_path)
		return false
	var packed: PackedScene = load(_scene_path)
	if packed == null:
		_fail("could not load %s" % _scene_path)
		return false

	root.add_child(packed.instantiate())
	await process_frame

	# Found by the method it answers to, not by its class — see `_vehicle`.
	for node: Node in root.find_children("*", "RigidBody3D", true, false):
		if node.has_method("forward_speed_kph"):
			_vehicle = node as RigidBody3D
			break
	if _vehicle == null:
		_fail("no vehicle in %s — nothing answers forward_speed_kph()" % _scene_path)
		return false

	# Read back rather than taken from the scene file: `skidpad.tscn` authors the
	# spawn, but a car that has settled onto its springs for a frame is the pose
	# every manoeuvre should restart from, not the one it was dropped at.
	_spawn = _vehicle.global_transform
	_step = 1.0 / float(Engine.physics_ticks_per_second)
	print("scene:   %s" % _scene_path)
	print("vehicle: %s at %s" % [_vehicle.name, _spawn.origin])
	var profile: Resource = _vehicle.get("profile") as Resource
	print("profile: %s" % ("none" if profile == null else profile.resource_path))
	if profile != null and SLIP_THRESHOLD_FIELD in profile:
		_slip_threshold_deg = profile.get(SLIP_THRESHOLD_FIELD)
		print("slip threshold: %.1f deg" % _slip_threshold_deg)
	else:
		print("slip threshold: none published — secs>thr will read 0.00")
	return true


func _measure_all() -> void:
	var results: Array[Result] = []
	var profile: Resource = _vehicle.get("profile") as Resource
	if not _sweep.is_empty():
		if profile == null:
			_fail("a sweep needs a profile on the vehicle and there is none")
			return
		# See DEFAULT_SWEEP_FIELD: set() would swallow a typo or a rename and print
		# a sweep of identical rows labelled with values it never applied.
		if not _sweep_field in profile:
			_fail("sweep: %s has no '%s'" % [profile.resource_path, _sweep_field])
			return
		# 🔴 The bar is not a knob, and generalising the flag is what made it
		# reachable. `_slip_threshold_deg` is cached at boot, so setting the field
		# per value writes something nothing reads back: every row would come out
		# identical and labelled with a distinct threshold it never measured
		# against. Structurally impossible while the swept field was a constant,
		# and only a convention once it was not. See SLIP_THRESHOLD_FIELD.
		if _sweep_field == SLIP_THRESHOLD_FIELD:
			_fail("sweep: %s is the bar, not the knob — it is read once at boot" % _sweep_field)
			return
		print("sweeping: %s" % _sweep_field)

	# One pass with the shipped tuning when nothing is swept. NAN is the "leave it
	# alone" marker rather than a bool-and-value pair, because it cannot be
	# confused with a value someone meant to sweep.
	#
	# Built rather than written as a ternary: `x if c else [NAN]` types the else
	# branch as a plain Array, and assigning that to an Array[float] throws at
	# run time — which killed this coroutine mid-run and still printed ABLATION OK,
	# because a dead coroutine records no failure. `_printed_rows` now catches it.
	var values: Array[float] = _sweep.duplicate()
	if values.is_empty():
		values.append(NAN)
	# See DRIFT_FIELD_PREFIX: a drift dial cannot move the other three manoeuvres,
	# anything else can.
	var confined: bool = String(_sweep_field).begins_with(DRIFT_FIELD_PREFIX)
	for value: float in values:
		if not is_nan(value):
			profile.set(_sweep_field, value)
		for manoeuvre: String in MANOEUVRES:
			if not _only.is_empty() and _only != manoeuvre:
				continue
			# ⚠️ Only the two drift manoeuvres are swept **when the swept field is
			# `drift_`-prefixed** — see DRIFT_FIELD_PREFIX, which is what decides it.
			# For such a field the other three never
			# reach the field — `corner` steers, `brake` brakes, `coast` presses
			# nothing, and none of them takes the drift branch — so re-running them
			# per value burns 4.5 s of simulation each to reproduce the previous row
			# exactly, and then the `@value` suffix dresses the duplicates up as
			# distinct measurements. That is the failure this whole tool exists to
			# stop, so it must not be the tool doing it.
			var swept: bool = not is_nan(value) and (not confined or manoeuvre in DRIFT_MANOEUVRES)
			if not is_nan(value) and not swept and value != values[0]:
				continue
			var result: Result = await _measure(
				manoeuvre, "%s@%.4f" % [manoeuvre, value] if swept else manoeuvre
			)
			if result == null:
				return
			results.append(result)

	if results.is_empty():
		_fail("--only=%s matched no manoeuvre" % _only)
		return
	_print_table(results)


## Run-up, then the manoeuvre, sampling every physics tick.
##
## The run-up is not measured and not reported: it is the same for every row in a
## run, and including it would average the manoeuvre against seconds of
## straight-line acceleration that says nothing about grip. Its *result* is
## reported, as `entry kph`, which is the number to quote when comparing runs at
## different `--run-up`.
func _measure(manoeuvre: String, label: String) -> Result:
	_release_everything()
	_vehicle.call("place_at", _spawn)
	# A placed car has zero velocity but its wheels are still holding last
	# manoeuvre's compression until they are simulated again, and the first tick
	# after a reset lands a spring transient on the tyres. Settling first keeps
	# manoeuvre two from being measured against manoeuvre one's suspension.
	await _hold(SETTLE_S)

	Input.action_press(&"accelerate")
	await _hold(_run_up_s)

	var result := Result.new()
	# Named before the manoeuvre runs, not after: `_sample` reports its failures
	# through this, and during a sweep three bare `drift:` messages name no value.
	result.name = label
	result.entry_kph = _speed_kph()

	match manoeuvre:
		"corner":
			await _sample([&"accelerate", &"steer_right"], MANOEUVRE_S, false, result)
		"drift":
			await _sample([&"accelerate", &"steer_right", &"drift"], MANOEUVRE_S, false, result)
		"tap":
			await _sample(
				[&"accelerate", &"steer_right", &"drift"], MANOEUVRE_S, false, result, TAP_S
			)
		"brake":
			await _sample([&"brake_reverse"], TO_REST_LIMIT_S, true, result)
		"coast":
			await _sample([], TO_REST_LIMIT_S, true, result)
		_:
			_fail("unknown manoeuvre '%s'" % manoeuvre)
			return null
	_release_everything()

	result.exit_kph = _speed_kph()
	result.decel_mps2 = (result.entry_kph - result.exit_kph) / 3.6 / result.seconds
	# Guarded rather than assumed positive: a manoeuvre that ends stopped, or
	# reversing, has no exponential rate at all, and `log(0)` is -inf which then
	# formats as a plausible-looking number.
	if result.entry_kph > STOPPED_KPH and result.exit_kph > STOPPED_KPH:
		result.decay_per_s = log(result.entry_kph / result.exit_kph) / result.seconds
	return result


## Holds a set of actions and samples the car every tick, until the clock runs
## out or — for the to-rest manoeuvres — the car stops.
##
## Time comes off the physics-frame counter rather than an accumulator, for the
## reason `driver.gd` gives: anything that parks this coroutine for more than a
## tick would otherwise silently shorten the measured window.
##
## ⚠️ **Distance and yaw are accumulated per tick, not taken end-to-end, and on
## this manoeuvre set that is not a refinement — it is the difference between a
## number and its opposite.** Full lock at 60 kph puts the car on a tight circle:
## measured, a 4 s corner came back to within **6.2 m** of where it started
## having covered some 70 m, and its 360-odd degrees of yaw came out of
## `angle_difference` as **5.1°**. Both read as "the car went almost nowhere and
## barely turned", which is the precise inverse of what happened.
func _sample(
	actions: Array[StringName],
	limit_s: float,
	to_rest: bool,
	into: Result,
	drift_release_s: float = INF
) -> void:
	# ⚠️ Released first. The run-up holds the throttle and nothing had dropped it,
	# so the coast manoeuvre measured 30 s of *acceleration* to 126 kph and then
	# failed for not coming to rest — a harness bug wearing the costume of the
	# fifth `P0-5b/c/d` handling bug, which is exactly that symptom.
	_release_everything()
	for action: StringName in actions:
		Input.action_press(action)

	var first_tick: int = Engine.get_physics_frames()
	var t: float = 0.0
	var last_position: Vector3 = _vehicle.global_position
	var last_heading: float = _vehicle.global_rotation.y

	while t < limit_s:
		await physics_frame
		t = float(Engine.get_physics_frames() - first_tick) * _step
		if not _vehicle.global_position.is_finite():
			_fail("%s: vehicle position went non-finite — the physics blew up" % into.name)
			break

		var position: Vector3 = _vehicle.global_position
		var heading: float = _vehicle.global_rotation.y
		into.distance_m += last_position.distance_to(position)
		into.yaw_deg += rad_to_deg(angle_difference(last_heading, heading))
		var slip_deg: float = _slip_deg()
		into.peak_slip_deg = maxf(into.peak_slip_deg, slip_deg)
		if slip_deg >= _slip_threshold_deg:
			into.seconds_above_deg += _step
		last_position = position
		last_heading = heading

		if t >= drift_release_s and Input.is_action_pressed(&"drift"):
			Input.action_release(&"drift")
		if to_rest and _speed_kph() <= STOPPED_KPH:
			break

	into.seconds = t
	if to_rest and t >= limit_s:
		_fail("%s: still moving at %.1f kph after %.0f s" % [into.name, _speed_kph(), limit_s])


## Signed forward speed, negative when reversing. Through `call()` for the
## reason `_vehicle` gives, and taken from the controller rather than recomputed
## here so a change to what "forward" means cannot leave this measuring the old
## definition.
func _speed_kph() -> float:
	return float(_vehicle.call("forward_speed_kph"))


## Angle between where the car points and where it is going, in degrees.
##
## Computed here from `linear_velocity` and the basis rather than read off the
## controller, which publishes no such field — and deliberately: `PLAN.md` holds
## the per-wheel slip signals back to `B4`, "when the effects that consume it are
## built, not before". A measuring instrument is not that consumer.
##
## ⚠️ **This is now the only definition of slip in the repo.** `Q49` set a figure
## from this tool against one `P0-5a` measured through the controller's own
## `slip_angle_deg()`, and until `Q49` the two disagreed — that one left the nose
## vector unflattened. `Q50` deleted the controller's copy along with the spike
## that was its only caller, so there is nothing left to keep in step; the
## flattening below is what those recorded figures mean.
##
## Flattened to the ground plane so a ramp or a landing cannot read as slip.
func _slip_deg() -> float:
	var velocity: Vector3 = _vehicle.linear_velocity
	var travel := Vector3(velocity.x, 0.0, velocity.z)
	if travel.length() < SLIP_FLOOR_MPS:
		return 0.0
	var nose: Vector3 = -_vehicle.global_basis.z
	var heading := Vector3(nose.x, 0.0, nose.z)
	if heading.is_zero_approx():
		return 0.0
	return rad_to_deg(travel.normalized().angle_to(heading.normalized()))


## Lets the clock run with whatever is currently pressed, sampling nothing.
func _hold(seconds: float) -> void:
	var first_tick: int = Engine.get_physics_frames()
	while float(Engine.get_physics_frames() - first_tick) * _step < seconds:
		await physics_frame


func _release_everything() -> void:
	for action: StringName in [
		&"accelerate", &"brake_reverse", &"steer_left", &"steer_right", &"drift"
	]:
		Input.action_release(action)


## ⚠️ The label column is sized to its longest entry rather than fixed. `--sweep`
## can name any field, and a wide one — `drift@11000.0000` at 16 characters —
## silently pushed every number on its row out of alignment under a fixed 13,
## which is a published table that misreads as a different quantity per row.
func _print_table(results: Array[Result]) -> void:
	var width: int = 13
	for result: Result in results:
		width = maxi(width, result.name.length())
	var row_format: String = "%%-%ds %%9s %%9s %%7s %%9s %%9s %%9s %%9s %%8s %%9s" % width
	var data_format: String = (
		"%%-%ds %%9.2f %%9.2f %%7.2f %%9.3f %%9.2f %%9.1f %%9.2f %%8.1f %%9.1f" % width
	)
	print("")
	print(
		(
			row_format
			% [
				"run",
				"entry",
				"exit",
				"secs",
				"decay/s",
				"decel",
				"peak slip",
				"secs>thr",
				"yaw",
				"distance"
			]
		)
	)
	print(row_format % ["", "kph", "kph", "", "", "m/s²", "deg", "s", "deg", "m"])
	for result: Result in results:
		_printed_rows += 1
		print(
			(
				data_format
				% [
					result.name,
					result.entry_kph,
					result.exit_kph,
					result.seconds,
					result.decay_per_s,
					result.decel_mps2,
					result.peak_slip_deg,
					result.seconds_above_deg,
					result.yaw_deg,
					result.distance_m,
				]
			)
		)


func _fail(message: String) -> void:
	_failures.append(message)


func _finish() -> void:
	if _printed_rows == 0:
		_fail("no rows measured — the run stopped early; look above for a SCRIPT ERROR")
	if _failures.is_empty():
		print("\nABLATION OK")
		quit(0)
		return
	for message: String in _failures:
		printerr("  FAIL  ", message)
	printerr("ABLATION FAILED")
	quit(1)
