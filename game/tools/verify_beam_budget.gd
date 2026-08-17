extends SceneTree

## Does `BeamBudget` ever hand out more spot lights than the renderer honours?
##
## ⚠️ **This is the one check that can run before a roster exists.** One car ships
## today, so the cap it enforces has nothing to bump against in the real scene —
## exactly the shape `P3-11e`'s night path has, and that path is already recorded
## as untested code that will stay untested. Rather than add a second, this
## instantiates stub rigs at known distances and asks the arbiter directly. The
## stubs answer the same two methods `VehicleLamps` does and nothing else, which
## is the whole contract.
##
## ⚠️ **Nothing here references a `class_name` global.** A `--script` tool that
## does fails to *parse* on a fresh clone, where `global_script_class_cache.cfg`
## has not been written yet — `_init` never runs, `quit(1)` is never reached, and
## the SceneTree exits **0** having checked nothing. `ARCHITECTURE.md` records
## that trap; the budget and the profile are therefore both `load`ed by path.
##
## ⚠️ **Integer division is a warning, warnings are errors, and a parse error
## here exits 0.** `_fits` divides in floats for that reason alone.

const BUDGET_SCRIPT := "res://scripts/vehicle/beam_budget.gd"
const PROFILE_PATH := "res://tuning/beams.tres"
## What a stub car costs. Two is the shipped taxi's count, and the number the
## roster risk is stated in — "at two lamps a car, four cars".
const BEAMS_PER_CAR := 2

var _failed: int = 0
## The stubs' 3D parent.
##
## ⚠️ **A `Node3D` parented straight to `root` — which is a `Window` — never gets
## a transform context**, so its `global_position` stays `Vector3.ZERO` whatever
## its `position` says. Every stub would sit on the origin, every rank would tie,
## and the ranking check would silently degrade into a test of registration
## order: precisely the defect `BeamBudget` exists to remove.
var _stage: Node3D = null
var _arbiter: Node = null


## A car that costs beams and remembers whether it was given any.
class StubRig:
	extends Node3D

	var beams: int = 2
	var granted: bool = false

	func beam_count() -> int:
		return beams

	func set_beams_granted(value: bool) -> void:
		granted = value


func _init() -> void:
	# Deferred, because nothing here can be measured during `_init`.
	# `global_position` is computed from a transform notification that has not
	# propagated yet, so a rank taken here reads every stub as being on the
	# origin — the other half of the trap `_stage` documents.
	_run.call_deferred()


func _run() -> void:
	var profile: Resource = load(PROFILE_PATH)
	if profile == null:
		_fail("no beam profile at %s" % PROFILE_PATH)
		_finish()
		return
	var cap: int = int(profile.get("max_spot_lights"))
	print("  budget: %d spot lights, %d-lamp cars fit %d" % [cap, BEAMS_PER_CAR, _fits(cap)])

	await _check_cap_is_never_exceeded(cap)
	await _check_the_nearest_cars_win(cap)
	await _check_a_rig_with_no_beams_takes_no_slot(cap)
	await _check_leaving_the_tree_frees_the_slot(cap)
	_finish()


## How many two-lamp cars the budget pays for.
##
## Written as a float divide and floored rather than `cap / BEAMS_PER_CAR`:
## GDScript treats integer division as a warning, warnings are errors here, and
## a parse error in a `--script` tool exits **0** having checked nothing.
func _fits(cap: int) -> int:
	return int(floor(float(cap) / float(BEAMS_PER_CAR)))


func _open() -> void:
	_stage = Node3D.new()
	root.add_child(_stage)
	var script: GDScript = load(BUDGET_SCRIPT) as GDScript
	_arbiter = script.new()
	_arbiter.name = "BeamBudget"
	root.add_child(_arbiter)


func _close() -> void:
	if _stage != null:
		_stage.queue_free()
		_stage = null
	if _arbiter != null:
		_arbiter.queue_free()
		_arbiter = null


## Place rigs, let their transforms settle, then re-rank. Returns them in the
## order given.
func _rigs(distances: Array[float], beams: int = BEAMS_PER_CAR) -> Array[StubRig]:
	var made: Array[StubRig] = []
	for distance: float in distances:
		var rig := StubRig.new()
		rig.beams = beams
		_stage.add_child(rig)
		rig.position = Vector3(distance, 0.0, 0.0)
		_arbiter.register(rig)
		made.append(rig)
	await process_frame
	# Explicit rather than waiting for a `regrant_hz` tick, so the run is
	# deterministic instead of depending on when a tick happens to land.
	_arbiter.refresh()
	return made


func _lit(rigs: Array[StubRig]) -> int:
	var count: int = 0
	for rig: StubRig in rigs:
		if rig.granted:
			count += 1
	return count


## The whole point: more cars than slots must not produce more lights than slots.
func _check_cap_is_never_exceeded(cap: int) -> void:
	_open()
	var wanted: int = cap * 2  # twice as many cars as the budget can pay for
	var spread: Array[float] = []
	for i: int in wanted:
		spread.append(float(i + 1))
	var rigs: Array[StubRig] = await _rigs(spread)
	var spent: int = _lit(rigs) * BEAMS_PER_CAR
	# ⚠️ **Against what whole cars can spend, not against `cap`.** They differ the
	# moment `cap` is odd, and `beam_profile.gd` explicitly invites lowering it to
	# buy headroom — at `max_spot_lights = 7` four two-lamp cars can only ever
	# spend 6, and comparing to 7 would report a correct budget as a build
	# failure.
	var spendable: int = _fits(cap) * BEAMS_PER_CAR
	if spent > spendable:
		_fail(
			(
				"%d cars of %d lamps lit %d spot lights against a cap of %d"
				% [wanted, BEAMS_PER_CAR, spent, cap]
			)
		)
	elif spent != spendable:
		# Under-spending is a bug too, and a quieter one — it means the roster is
		# dimmer than the hardware allows for no reason anybody chose.
		_fail(
			(
				"%d cars lit only %d of the %d spendable slots (cap %d)"
				% [wanted, spent, spendable, cap]
			)
		)
	else:
		print("  ok    %d cars competing spend exactly %d of %d slots" % [wanted, spent, cap])
	_close()


## Which cars win has to be distance, because pair order is the defect.
func _check_the_nearest_cars_win(cap: int) -> void:
	_open()
	# Registered farthest-first, so registration order is the *opposite* of the
	# answer. A budget that simply took the first N registered would pass a test
	# whose rigs arrived in the right order already.
	var far_to_near: Array[float] = [500.0, 400.0, 300.0, 200.0, 100.0, 50.0, 20.0, 5.0]
	var rigs: Array[StubRig] = await _rigs(far_to_near)
	var fits: int = _fits(cap)
	var wrong: int = 0
	for i: int in rigs.size():
		# The last `fits` entries are the nearest, by construction above.
		var should: bool = i >= rigs.size() - fits
		if rigs[i].granted != should:
			wrong += 1
	if wrong > 0:
		var got: PackedStringArray = PackedStringArray()
		for i: int in rigs.size():
			got.append("%.0fm=%s" % [far_to_near[i], rigs[i].granted])
		_fail("nearest-%d did not win: %s" % [fits, ", ".join(got)])
	else:
		print("  ok    the %d nearest cars took the slots, registration order ignored" % fits)
	_close()


## A car with no cone competes for nothing and must not displace one that does.
func _check_a_rig_with_no_beams_takes_no_slot(cap: int) -> void:
	_open()
	var empty: Array[StubRig] = await _rigs([1.0, 2.0] as Array[float], 0)
	# Sized from the profile rather than hard-coded, so raising `max_spot_lights`
	# does not fail this for want of cars to fill it.
	var behind: Array[float] = []
	for i: int in _fits(cap):
		behind.append(float(10 * (i + 1)))
	var real: Array[StubRig] = await _rigs(behind)
	var spendable: int = _fits(cap) * BEAMS_PER_CAR
	if _lit(empty) > 0:
		_fail("a rig with no SpotLight3D was granted beams")
	elif _lit(real) * BEAMS_PER_CAR != spendable:
		_fail(
			(
				"beamless rigs in front cost the real cars %d of %d slots"
				% [_lit(real) * BEAMS_PER_CAR, spendable]
			)
		)
	else:
		print("  ok    beamless rigs take no slot even when nearest")
	_close()


## A despawned car holds no slot. `P3-3` will despawn traffic constantly.
func _check_leaving_the_tree_frees_the_slot(cap: int) -> void:
	_open()
	var near_by: Array[float] = []
	for i: int in _fits(cap):
		near_by.append(float(i + 1))
	var near: Array[StubRig] = await _rigs(near_by)
	var waiting: Array[StubRig] = await _rigs([900.0] as Array[float])
	if waiting[0].granted:
		_fail("a car 900 m away was granted while the budget was full")
		_close()
		return
	for rig: StubRig in near:
		_arbiter.unregister(rig)
		rig.queue_free()
	if not waiting[0].granted:
		_fail("the far car was not granted after every near car left")
	else:
		print("  ok    a slot freed by a despawn is handed on")
	_close()


func _fail(message: String) -> void:
	_failed += 1
	printerr("  FAIL  %s" % message)


func _finish() -> void:
	if _failed > 0:
		printerr("beam budget: %d check(s) failed" % _failed)
		quit(1)
		return
	print("  ok    verify_beam_budget")
	quit(0)
