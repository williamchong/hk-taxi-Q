class_name FareSystem
extends Node
## The fare loop (`P3-1a`, `Q141`): hail → board → carry → deliver or bail, on
## the fare nodes `P1-5` published and the routes `P3-43` built. The first
## consumer of `RoadRouter`.
##
## **What a fare is worth is two numbers.** The 咪錶 runs Transport Department's
## tariff (`FareTariff`) on the metres actually driven and the seconds actually
## waited — honest money, and nothing the player does at the wheel changes it
## except driving further or sitting still. The tip is what the drive *earned*:
## here the seconds left on the allowance, priced per second, so a shortcut and
## a fast run pay the same way; `P3-2b`'s style chain adds to the same field.
## Delivery banks the sum; a bail banks nothing.
##
## **The allowance is the legal route alone** (the user's call, 2026-11-12): at
## boarding the route's length over `par_kph`, no floor by kind. Legal, not the
## player's profile (`Q137`'s recommendation): par is what a driver obeying the
## signs would do — 19 kph, the legal traffic's median (`Q203`) — and the
## player may break every rule to beat it.
##
## **A few customers wait at once, each already knowing where they are going**
## (`Q203`). The pools are every published stand and PUDO point that may be
## hailed at and every street spot (`fares.json`'s `street`), several hundred
## on the merged runtime — too many to route every pair at load. So
## `live_pickups` of them are drawn, `street_share` of the draws from the
## street, and each is paired with its destination as it is drawn: a
## destination drawn the same way from those one forward search from the
## pickup reaches at `min_trip_m` or beyond (`RoadRouter.source_tree`, uncached,
## so it evicts no prepared tree). `pickups()` is that live set; a boarding
## takes one out and the fare's end draws its replacement. **They stay near the
## car** (the user's ask): a customer stays where placed, the farthest leaves
## once past `retire_m` for a new one placed within `place_m` of the car, one a
## sample (`_turn_over`). The hail pays one `prepare` for its destination, as
## before. Drawing blind and
## retrying AT THE HAIL was built first and refused — a stand with one
## reachable destination was refused most of its hails; here a pickup that
## pairs with nothing is never shown.
##
## ⚠️ **"No route" is an answer** (`Q137`), and here it is a pool decision. 40%
## of ordered fare pairs in Wan Chai have none — the clip is not strongly
## connected — and a pickup the forward search reaches no destination from at
## `min_trip_m` is **stranded**: dropped from the pickup pool for the session, kept
## as a destination, counted and named, never asserted. Found as it is drawn,
## not surveyed at load: the westbound Hennessy and Johnston Road points at the
## clip's west edge and Causeway Bay's far-side stands, where forward leaves
## the clip and the one-way network never comes back.
##
## **Its own `nearest_edge`, at its own rate.** `hud.gd` samples the graph at
## 5 Hz too, but its `Hit` is a local and the HUD can be off (`--hud=off`), so
## this node asks for itself: one query per sample, p99 45 µs (`P2-2`).
##
## **No dev chrome here.** `fare_readout.gd` beside it draws the state on the
## `DebugHud` overlay, and names that autoload; this script does not, because a
## `--script` verify tool loads it before any autoload is registered, and a
## script that names one fails to compile there — a green run over nothing.
##
## **Pure enough to verify without a frame.** `sample()` takes a position, a
## speed, a heading and an elapsed time; `_physics_process` is the only thing
## that reads the car. `tools/verify_fares.gd` builds one with `setup()` and
## drives the whole loop with synthetic samples, dwells from both sides.
##
## **The skills pay as they happen** (`P3-49`, `Q145`). While a passenger is
## aboard a `SkillTracker` reads every tick's speed and slip: a slide held at
## or over `HandlingProfile.drift_slip_threshold_deg` for `SkillProfile.drift_min_s`
## pays `drift_hkd` and again every further `drift_s`, each award
## `drift_step_hkd` over the last, a run at or over
## `speed_min_kph` pays `speed_hkd` every `speed_hold_m` driven, a flight
## with every wheel off the ground for `air_min_s` pays `air_hkd` on an
## upright landing and again per further `air_s` (`P3-51`), and an
## arrival with `early_share` of the allowance left pays `early_hkd` at the
## door. Each is a flat HK$ into `Fare.tip_hkd` the moment it is earned and a
## line on the receipt; `skilled` says so. A bail forfeits the lot — the
## passenger walks without paying, and the receipt says what walked.
##
## **The skills run empty too, shown and never paid** (the user's call,
## 2026-09-26): one `SkillTracker` for the session reads every tick, and
## `_award` decides where its award goes — onto the fare while a passenger is
## aboard, out on `practised` otherwise — and counted in `skill_counts`
## either way, the session's tally for a later achievement. No money moves without a
## passenger: the tip is theirs (`Q141`), and `earned_hkd` is what fares
## banked. `reset` at boarding keeps a slide held into the hail off the
## passenger's receipt.
##
## **The live tip is the skills alone** (the user's call, `Q145`): the seconds
## left are priced ONCE, at the door, into `Fare.time_hkd`. A tip that fell
## with the clock read as a penalty for driving; now it only rises with a
## skill, drops with a penalty, and the clock in the middle of the frame is
## the one thing that runs down.
##
## ⚠️ **`slip_deg_of` is a second copy of `skidpad_ablation.gd`'s slip, on
## purpose** (`Q84`): the grader must never call what it grades, so the
## instrument keeps its own, and the game — the consumer `PLAN.md` held the
## slip signal back for — now has this one. Same flattening, same floor, and
## the same velocity: the rear axle's (`VehicleController.rear_axle_velocity`).
##
## `--fares=off` frees the node — free roam, and what `P3-9` runs.
## `--fare-seed=<int>` fixes the destination draw for a repeatable drive.

## Emitted at the hail, with the fare drawn: the passenger is walking to the car.
signal hailed(fare: Fare)
## Emitted when the passenger is aboard and the meter and the clock start.
signal boarded(fare: Fare)
## Emitted when the car left the pickup's radius before boarding finished.
signal cancelled(fare: Fare)
## Emitted at the destination, with `banked_hkd` set.
signal delivered(fare: Fare)
## Emitted when the allowance ran out; `banked_hkd` is 0.
signal bailed(fare: Fare)
## Emitted each time a skill pays, with the award just appended to
## `fare.awards` and added to `fare.tip_hkd` (`P3-49`).
signal skilled(fare: Fare, award: Fare.Award)
## Emitted each time a skill is performed with no passenger aboard — a
## practice run, shown and never paid. The award is on no fare and in no tip.
signal practised(award: Fare.Award)
## Emitted each time a bonus joins the style combo (`P3-2b`, `Q205`), paid or
## practised alike: `combo` is `FareSystem.combo`, live, its counts as they
## stand. Never money — the award's own signal says what it paid.
signal combo_changed(combo: StyleCombo)
## Emitted once when a style combo ends: on a collision or a crash (`broken`),
## or when its gap ran out. `combo` is a copy of its last counts; the live one
## is already empty. Whether it is called out is `StyleCombo.shown`'s.
signal combo_ended(combo: StyleCombo, broken: bool)
## Emitted when the drift's tier moves (`SkillTracker.drift_tier`, `P3-58`):
## -1 when no slide is at the threshold, 0 while one counts, then the awards
## it has paid. Paid or practised alike — the sparks show the slide, not the
## fare.
signal drift_tier_changed(tier: int)
## Emitted when the waiting customers change — one boarded, or a fare's end
## drew a replacement: when a reader that marks them re-reads `pickups()`.
signal pickups_changed
## Emitted whenever the reading moves: the new reading in HK$, and the unit
## that just began — the flagfall at boarding — so a readout that shows the
## tick keeps no copy of the last reading (`P3-5a`).
signal meter_changed(hkd: float, delta_hkd: float)
## Emitted after each graph sample, at `sample_hz`: when a readout should
## re-read `state`, `fare` and the counters. Never per frame.
signal sampled
## Emitted once after `close`, when nobody is aboard: the shift's last fare
## delivered or walked, or none was running (`Q162`). The run's total is
## `earned_hkd`.
signal finished

## What `TrafficSystem` finds the loop by, to hear its awards (`Q178`).
const GROUP: StringName = &"fare_system"
const GeneratedFares = preload("res://scripts/city/generated_fares.gd")
const GeneratedRegions = preload("res://scripts/city/generated_regions.gd")
const MeshMeasure = preload("res://scripts/city/mesh_measure.gd")
const ParkedLayer = preload("res://scripts/city/parked_layer.gd")

## How far round the car the parked roster is asked for bodies each tick
## (`P3-2a`): the look distance at the car's speed plus a bus's half-length
## and the car's own, never under a car length — an obstacle that is
## alongside or ahead in the path is always inside it, so no live approach is
## dropped — and never past the look at top speed.
const NEAR_RADIUS_MAX_M: float = 60.0
const NEAR_RADIUS_MIN_M: float = 12.0
const LONGEST_PARKED_HALF_M: float = 6.0

## `--fares=off` frees this node. Read by prefix, like `--hud=`.
const FARES_ARG: String = "--fares="
## `--fare-seed=<int>` seeds the destination draw; absent, it is randomised.
const SEED_ARG: String = "--fare-seed="
## Ground speed under which a slip angle is noise rather than a measurement:
## a nearly stationary car has a velocity vector pointing anywhere at all.
## `skidpad_ablation.gd`'s `SLIP_FLOOR_MPS`, restated on purpose (see above).
const SLIP_FLOOR_MPS: float = 1.0
## The slip past which the car is travelling backwards, not sliding: the
## tyre car's stability control stands aside there, and the drift meter does
## not run (a reverse reads about 180°, and under `Q172`'s 0.5 s bar it paid).
## A geometric fact — 90° is the travel crossing the axle — not a dial.
const REVERSED_SLIP_DEG: float = 90.0

enum State { IDLE, BOARDING, CARRYING }
## What one draw did (`_place_one`).
enum Placed { PLACED, STRANDED, NONE }

## The car. Set by the scene; `setup()` leaves it null for a headless run.
@export var vehicle: VehicleController

var state: State = State.IDLE
## The fare in flight, or the last one to end; null before the first hail.
var fare: Fare = null
## Everything banked this session, in HK$.
var earned_hkd: float = 0.0
## This run's ledger (`P3-76`): a fresh one at every `reset`.
var tally: SessionTally = SessionTally.new()
## The counters a drive is checked against.
var deliveries: int:
	get:
		return tally.deliveries
var bails: int:
	get:
		return tally.bails
var cancellations: int = 0
var hail_refusals: int = 0
## The pickups dropped for pairing with no destination, in the order found.
var stranded: Array[Fare.Stop] = []
## Waiting customers removed for falling past `retire_m` of the car.
var retired: int = 0
## What drawing the first waiting customers cost at `setup`, in milliseconds.
var pair_ms: float = 0.0
## The pending customer a reader may point at as of the last sample, and the
## pickups it must not mark (`nearest_pending`'s and `withheld_pickups`'s
## answers, scanned once per sample rather than once per reader). Read inside
## `sampled`, like everything else here.
var pending: Fare.Stop = null
var withheld: PackedInt32Array = []
## How many times each `Fare.Skill` was performed this session, paid or
## not, indexed by the skill: every award and every practice run, so an
## achievement reads one number here rather than each fare's receipt.
var skill_counts: PackedInt32Array:
	get:
		return tally.counts
## The style combo running now (`P3-2b`, `Q205`): shown and recorded, never
## money. Read inside `combo_changed` and `sampled`, like everything here.
var combo: StyleCombo = null

var _profile: FareProfile = null
var _tariff: FareTariff = null
## The session's skills, built by `setup`, reset at every boarding.
var _tracker: SkillTracker = null
## The near miss and close call detector (`P3-2a`), fed the parked bodies.
var _near: NearMiss = null
## The drift tier last emitted, so `drift_tier_changed` fires on a move only.
var _drift_tier: int = -1
var _rng: RandomNumberGenerator = null
# A member, not a local: `RoadGraph.shared()` holds it weakly.
var _graph: RoadGraph = null
var _router: RoadRouter = null
## Where a customer may wait and where one may be going, each split into the
## published points and the street spots so a draw can weigh the two.
var _pool: Array[Fare.Stop] = []
var _pool_street: Array[Fare.Stop] = []
var _dropoffs: Array[Fare.Stop] = []
var _dropoffs_street: Array[Fare.Stop] = []
## The customers waiting now, and where each is going, by `Fare.Stop.key`.
var _live: Array[Fare.Stop] = []
var _bound: Dictionary[String, Fare.Stop] = {}
## Where the car was at the last tick: no customer is drawn inside its hail
## radius, or one would appear under a car that just stopped.
var _last_position: Vector3 = Vector3.INF
## False until a whole profile and tariff were handed in; nothing is judged before then.
var _usable: bool = false
var _sample_accum_s: float = 0.0
var _board_accum_s: float = 0.0
## Whether a hail may start. Cleared when a fare ends or a hail is refused,
## and set again once the car has been outside every hail radius at a sample —
## or a delivery at a stand that is also a pickup would hail again on the spot.
var _armed: bool = true
var _last_reading_hkd: float = 0.0
## Whether `close` was called: nothing hails, nothing is marked, and the fare
## aboard is the last.
var _closed: bool = false


func _ready() -> void:
	if Cmdline.off(FARES_ARG):
		print("fares: off")
		set_physics_process(false)
		queue_free()
		return
	if vehicle == null:
		push_warning("FareSystem has no VehicleController assigned; nothing will be hailed.")
		set_physics_process(false)
		return

	var rng := RandomNumberGenerator.new()
	var seed_text: String = Cmdline.value(SEED_ARG)
	if seed_text.is_valid_int():
		rng.seed = int(seed_text)
	else:
		rng.randomize()

	var fares: Dictionary[String, Dictionary] = {}
	for region: String in GeneratedRegions.resident():
		fares[region] = GeneratedFares.load_fares(GeneratedFares.path(region))
	# The car's own plan box, in its own frame, for the near miss's bands.
	var box: AABB = vehicle.transform.affine_inverse() * MeshMeasure.bounds(vehicle)
	setup(
		RoadGraph.shared(),
		fares,
		load(FareProfile.PATH) as FareProfile,
		load(FareTariff.PATH) as FareTariff,
		load(SkillProfile.PATH) as SkillProfile,
		vehicle.profile.drift_slip_threshold_deg if vehicle.profile != null else 0.0,
		rng,
		Vector2(box.size.x / 2.0, box.size.z / 2.0)
	)
	if not _usable:
		set_physics_process(false)
		return
	var names: PackedStringArray = []
	for stop: Fare.Stop in stranded:
		names.append("%s/%s" % [stop.region, stop.id])
	print(
		(
			"fares: %d waiting of %d pickups (%d street; %d stranded: %s), %d destinations (%d street), pairing %.1f ms"
			% [
				_live.size(),
				_pool.size() + _pool_street.size(),
				_pool_street.size(),
				stranded.size(),
				", ".join(names),
				_dropoffs.size() + _dropoffs_street.size(),
				_dropoffs_street.size(),
				pair_ms
			]
		)
	)


## Everything the loop needs, handed in: the merged graph, each resident
## region's `fares.json` document by region, the three tables, the drift's
## angle and the draw. A missing or zeroed table makes an INERT system —
## nothing hails, and the error names why — never one running on a literal.
func setup(
	graph: RoadGraph,
	fares_by_region: Dictionary[String, Dictionary],
	profile: FareProfile,
	tariff: FareTariff,
	skills: SkillProfile,
	slip_threshold_deg: float,
	rng: RandomNumberGenerator,
	car_half_m: Vector2
) -> void:
	_usable = false
	if graph == null or graph.is_empty():
		push_error("FareSystem: the road graph is empty; nothing will be hailed.")
		return
	if profile == null:
		push_error("FareSystem: no FareProfile handed in; nothing will be hailed.")
		return
	var required: Dictionary[String, float] = {
		"hail_radius_m": profile.hail_radius_m,
		"board_s": profile.board_s,
		"deliver_radius_m": profile.deliver_radius_m,
		"stop_below_kph": profile.stop_below_kph,
		"min_trip_m": profile.min_trip_m,
		"par_kph": profile.par_kph,
		"tip_hkd_per_s": profile.tip_hkd_per_s,
		"sample_hz": profile.sample_hz,
		"live_pickups": float(profile.live_pickups),
		"place_m": profile.place_m,
		"retire_m": profile.retire_m,
	}
	if TuningTable.any_zero(profile, required, "FareSystem", "nothing will be hailed"):
		return
	if profile.place_m <= profile.hail_radius_m:
		push_error(
			(
				"FareSystem: place_m %.0f is not over hail_radius_m %.0f in %s; nobody could be placed near the car."
				% [profile.place_m, profile.hail_radius_m, FareProfile.PATH]
			)
		)
		return
	if profile.retire_m <= profile.place_m:
		push_error(
			(
				"FareSystem: retire_m %.0f is not over place_m %.0f in %s; a customer placed at the edge would be removed at once."
				% [profile.retire_m, profile.place_m, FareProfile.PATH]
			)
		)
		return
	# The skills' table and the drift's angle are the tracker's to refuse.
	var tracker := SkillTracker.new(skills, slip_threshold_deg)
	if not tracker.usable():
		push_error("FareSystem: the SkillTracker is inert; nothing will be hailed.")
		return
	# And the near miss's: its bands, and the car's own extent (`P3-2a`).
	var near := NearMiss.new(skills, car_half_m.x, car_half_m.y)
	if not near.usable():
		push_error("FareSystem: the NearMiss detector is inert; nothing will be hailed.")
		return
	# And the style combo's gap (`Q205`).
	var running := StyleCombo.new(skills)
	if not running.usable():
		push_error("FareSystem: the StyleCombo is inert; nothing will be hailed.")
		return
	var probe := FareMeter.new(tariff)
	if not probe.usable():
		return
	if rng == null:
		push_error("FareSystem: no RandomNumberGenerator handed in.")
		return

	_graph = graph
	_profile = profile
	_tariff = tariff
	_rng = rng
	_router = RoadRouter.new(graph, RoadRouter.Profile.legal())
	_tracker = tracker
	_near = near
	combo = running
	_drift_tier = -1
	_pool.clear()
	_pool_street.clear()
	_dropoffs.clear()
	_dropoffs_street.clear()
	_live.clear()
	_bound.clear()
	stranded.clear()
	retired = 0
	_last_position = Vector3.INF
	for region: String in fares_by_region:
		_add_stops(region, fares_by_region[region])
	var started: int = Time.get_ticks_usec()
	_refill()
	pair_ms = float(Time.get_ticks_usec() - started) / 1000.0
	_usable = true
	add_to_group(GROUP)


func usable() -> bool:
	return _usable


## The shift is over (`Q162`): no hail from here on, a passenger walking to
## the car is turned away, and one aboard rides to the end of their fare —
## delivered or walked, `finished` follows. With nobody aboard it follows now.
func close() -> void:
	if _closed or not _usable:
		return
	_closed = true
	if state == State.BOARDING:
		cancellations += 1
		state = State.IDLE
		cancelled.emit(fare)
	pending = null
	withheld = PackedInt32Array()
	if state == State.IDLE:
		finished.emit()


## Whether `close` was called and the loop takes no more fares.
func closed() -> bool:
	return _closed


## A fresh run on the same pools (`Q162`'s restart): nothing banked, nothing
## counted, nobody aboard, open. The waiting customers and the draw stay —
## they are the city's, not the run's.
func reset() -> void:
	state = State.IDLE
	fare = null
	earned_hkd = 0.0
	tally = SessionTally.new()
	cancellations = 0
	hail_refusals = 0
	retired = 0
	pending = null
	withheld = PackedInt32Array()
	_sample_accum_s = 0.0
	_board_accum_s = 0.0
	_armed = true
	_closed = false
	_last_reading_hkd = 0.0
	_drift_tier = -1
	# A restart mid-fare drops the passenger the boarding took off the kerb.
	if _usable:
		_refill()
	if _tracker != null:
		_tracker.reset()
	if _near != null:
		_near.reset()
	# A new run's combo starts empty; the old one's bests went into the old
	# tally as it climbed, so nothing is lost by dropping it unannounced.
	if combo != null:
		combo.clear()


## The customers waiting now: where a fare may start. A handful, redrawn as
## they board (`pickups_changed`).
func pickups() -> Array[Fare.Stop]:
	return _live


## Seat a customer at `region`/`id`, first of the waiting set, paired like any
## other; the last drawn steps aside to keep `live_pickups`. The drive harness
## calls it for the stand the car starts behind, at the start and on a restart,
## so the game opens with a fare to pull forward into (`Q203`, restoring
## `Q142`'s opening the random draw had made a 1-in-70 chance). Never inside
## the hail guard `_refill` keeps: that guard is for the car's last stop.
## True at once where a customer already waits there, wherever in the set.
## False, with nobody seated, where the stop is not a pickup or reaches no
## destination — the latter stranded like any draw. Between fares only: a
## pickup aboard is out of the set and could be seated twice.
func wait_at(region: String, id: String) -> bool:
	if not _usable:
		return false
	for waiting: Fare.Stop in _live:
		if waiting.region == region and waiting.id == id:
			return true
	var seat: Fare.Stop = null
	for stop: Fare.Stop in pool():
		if stop.region == region and stop.id == id:
			seat = stop
			break
	if seat == null:
		return false
	var destination: Fare.Stop = _pair(seat)
	if destination == null:
		_strand(seat)
		return false
	_live.push_front(seat)
	_bound[seat.key()] = destination
	while _live.size() > _profile.live_pickups:
		_bound.erase(_live.pop_back().key())
	pickups_changed.emit()
	return true


## Every stop a customer may be drawn waiting at, published then street.
func pool() -> Array[Fare.Stop]:
	return _pool + _pool_street


## Every stop a fare may end at, published then street.
func dropoffs() -> Array[Fare.Stop]:
	return _dropoffs + _dropoffs_street


## Whether the next sample inside a hail radius may hail.
func armed() -> bool:
	return _armed


func _physics_process(delta: float) -> void:
	# Held with this tick: `park` stops it and so does the paused tree, so the
	# books count driving time alone.
	tally.driven_s += delta
	var placed: Transform3D = vehicle.global_transform
	var velocity: Vector3 = vehicle.linear_velocity
	var nose: Vector3 = -placed.basis.z
	# Every tick, carrying or not: the skills run empty too, and a hit taken
	# empty is drained here rather than docked from the next passenger.
	sample(
		placed.origin,
		velocity.length(),
		nose,
		delta,
		slip_deg_of(vehicle.rear_axle_velocity(), nose),
		vehicle.is_airborne(),
		vehicle.is_upright(),
		vehicle.take_impact_mps(),
		placed,
		velocity,
		obstacles_near(get_tree(), placed.origin, _near_radius_m(velocity.length()), _near.look_s())
	)


## What the near miss looks at: the parked vehicles round `point`, and the moving
## ones (`Q175`), which `--traffic=off` leaves none of; and the trams (`P3-4`).
static func obstacles_near(
	tree: SceneTree, point: Vector3, radius_m: float, look_s: float
) -> Array[Dictionary]:
	var found: Array[Dictionary] = ParkedLayer.near_all(tree, point, radius_m)
	var traffic := tree.get_first_node_in_group(TrafficSystem.GROUP) as TrafficSystem
	if traffic != null:
		found.append_array(traffic.near_cars(point, radius_m, look_s))
	var running := tree.get_first_node_in_group(TramSystem.GROUP) as TramSystem
	if running != null:
		found.append_array(running.near_cars(point, radius_m, look_s))
	return found


## The disc the roster is asked for, at this speed.
func _near_radius_m(speed_mps: float) -> float:
	var look_m: float = (
		speed_mps * _near.look_s() + LONGEST_PARKED_HALF_M + _near.car_half_length_m()
	)
	return clampf(look_m, NEAR_RADIUS_MIN_M, NEAR_RADIUS_MAX_M)


## The angle between where the car points and where `velocity` is going — the
## rear axle's, for a slide (`VehicleController.rear_axle_velocity`) — in degrees,
## flattened to the ground plane so a ramp or a landing cannot read as slip,
## and 0 under `SLIP_FLOOR_MPS`. `skidpad_ablation.gd::_slip_deg`, restated.
static func slip_deg_of(velocity: Vector3, nose: Vector3) -> float:
	var travel := Vector3(velocity.x, 0.0, velocity.z)
	if travel.length() < SLIP_FLOOR_MPS:
		return 0.0
	var heading := Vector3(nose.x, 0.0, nose.z)
	if heading.is_zero_approx():
		return 0.0
	return rad_to_deg(travel.normalized().angle_to(heading.normalized()))


## One tick of the loop: the car is at `position` doing `speed_mps` along
## `heading` with `slip_deg` between the two, `delta_s` after the last tick,
## `airborne` with every wheel off the ground and `upright` on its wheels
## rather than its roof (`P3-51`), and `impact_mps` into a wall this tick
## (`P3-50`); `car`, `velocity` and `obstacles` are the car's own transform,
## its velocity and the vehicles near it, for the near miss
## (`P3-2a`). The skills run every tick in every state; the odometer and
## the clock while carrying; the graph is asked once per `sample_hz`.
func sample(
	position: Vector3,
	speed_mps: float,
	heading: Vector3,
	delta_s: float,
	slip_deg: float = 0.0,
	airborne: bool = false,
	upright: bool = true,
	impact_mps: float = 0.0,
	car: Transform3D = Transform3D.IDENTITY,
	velocity: Vector3 = Vector3.ZERO,
	obstacles: Array[Dictionary] = []
) -> void:
	if not _usable:
		return
	_last_position = position
	var elapsed: float = maxf(delta_s, 0.0)
	if state == State.CARRYING:
		fare.meter.advance(maxf(speed_mps, 0.0) * elapsed, elapsed)
		_announce_reading()
	for award: Fare.Award in _tracker.tick(
		speed_mps, slip_deg, elapsed, airborne, upright, impact_mps
	):
		_award(award)
	for award: Fare.Award in _near.tick(
		car, velocity, obstacles, elapsed, impact_mps > 0.0, airborne
	):
		_award(award)
	# The combo's clock after this tick's awards, on whether a skill is in
	# progress now: an award this tick restarted it, and it runs only on a
	# tick with neither (`StyleCombo.tick`).
	if combo.tick(elapsed, _tracker.holding()):
		_end_combo(false)
	tally.note_tick(
		maxf(speed_mps, 0.0) * 3.6,
		airborne,
		_tracker.paid_slide_s(),
		_tracker.landed_flight_s(),
		_near.paid_clear_m()
	)
	var tier: int = _tracker.drift_tier()
	if tier != _drift_tier:
		_drift_tier = tier
		drift_tier_changed.emit(tier)
	if state == State.CARRYING:
		fare.remaining_s -= elapsed
		if fare.remaining_s <= 0.0:
			fare.remaining_s = 0.0
			_bail(position)
			return

	_sample_accum_s += elapsed
	if _sample_accum_s < 1.0 / _profile.sample_hz:
		return
	var since_sample: float = _sample_accum_s
	_sample_accum_s = 0.0

	var speed_kph: float = maxf(speed_mps, 0.0) * 3.6
	match state:
		State.IDLE:
			_sample_idle(position, speed_kph)
		State.BOARDING:
			_sample_boarding(position, since_sample)
		State.CARRYING:
			_sample_carrying(position, speed_kph, heading)
	if state != State.BOARDING and not _closed:
		_turn_over(position)
	_rescan(position)
	sampled.emit()


## Keep the waiting customers near the car (`Q203`, the user's ask: "there is
## always 4 nearby as the car is moving"). A customer stays where they were
## placed; once the farthest is past `retire_m` they give up and leave, and one
## new customer is placed within `place_m` — one draw a sample, so a pairing's
## forward search is never more than one a tick. A swap, never a removal
## alone: the new customer is placed and paired FIRST, and the farthest leaves
## only then — with no free kerb within `retire_m` (the clip, the harbour), or a
## draw that strands, the set stays as it was, where removing first would
## shrink it or remove a far placement again every sample. Never while
## boarding: the customer walking to the car is in the set. Mid-fare too, so
## the fare's end finds them near.
func _turn_over(position: Vector3) -> void:
	if _live.size() < _profile.live_pickups:
		if _place_one(INF) == Placed.PLACED:
			pickups_changed.emit()
		return
	var farthest: int = -1
	var farthest_m: float = _profile.retire_m
	for index: int in _live.size():
		var apart_m: float = RoadGraph.plan_distance(position, _live[index].point)
		if apart_m > farthest_m:
			farthest_m = apart_m
			farthest = index
	if farthest < 0 or _place_one(_profile.retire_m) != Placed.PLACED:
		return
	# The new customer went on the end, so `farthest` still names the leaver.
	_bound.erase(_live[farthest].key())
	_live.remove_at(farthest)
	retired += 1
	pickups_changed.emit()


func _sample_idle(position: Vector3, speed_kph: float) -> void:
	if _closed:
		return
	if _armed and speed_kph >= _profile.stop_below_kph:
		# Nothing to arm and too fast to hail: the pool scan would decide nothing.
		return
	var nearest: Fare.Stop = _nearest_pickup(position)
	if nearest == null:
		_armed = true
		return
	if not _armed or speed_kph >= _profile.stop_below_kph:
		return
	_hail(nearest)


func _sample_boarding(position: Vector3, since_sample: float) -> void:
	if RoadGraph.plan_distance(position, fare.pickup.point) > _profile.hail_radius_m:
		cancellations += 1
		state = State.IDLE
		_armed = false
		cancelled.emit(fare)
		return
	_board_accum_s += since_sample
	if _board_accum_s < _profile.board_s:
		return
	_board()


func _sample_carrying(position: Vector3, speed_kph: float, heading: Vector3) -> void:
	var apart_m: float = RoadGraph.plan_distance(position, fare.destination.point)
	var hit: RoadGraph.Hit = _graph.nearest_edge(position, heading)
	if hit.hit():
		# A cache hit: the hail's `route` prepared this destination and nothing
		# else prepares on this router. ⚠️ A consumer that shared `_router` and
		# prepared more than `TREE_CACHE` others mid-fare would turn this into a
		# reverse Dijkstra at 5 Hz.
		# Seeded the way the car faces (`hit.along`), so on a two-way street the
		# drawn route (`P3-46`) leaves along the car rather than behind it.
		var route: RoadRouter.Route = _router.route(
			hit.edge_id,
			hit.t,
			fare.destination.edge,
			fare.destination.t,
			RoadRouter.Facing.ALONG if hit.along else RoadRouter.Facing.AGAINST
		)
		fare.remaining_road_m = route.distance_m
		fare.route = route
		fare.route_from_t = hit.t
	else:
		fare.remaining_road_m = apart_m
		fare.route = null
	if apart_m > _profile.deliver_radius_m:
		return
	if speed_kph >= _profile.stop_below_kph:
		return
	_deliver()


## The passenger has hailed from `pickup`: draw where they are going, or refuse.
func _hail(pickup: Fare.Stop) -> void:
	var destination: Fare.Stop = pick_destination(pickup)
	if destination == null:
		hail_refusals += 1
		_armed = false
		return
	var drawn := Fare.new()
	drawn.kind = Fare.kind_of(destination.node)
	drawn.pickup = pickup
	drawn.destination = destination
	var route: RoadRouter.Route = _router.route(
		pickup.edge, pickup.t, destination.edge, destination.t
	)
	drawn.route_found = route.found
	drawn.par_m = route.distance_m
	drawn.remaining_road_m = route.distance_m
	drawn.route = route
	drawn.route_from_t = pickup.t
	drawn.meter = FareMeter.new(_tariff)
	fare = drawn
	_board_accum_s = 0.0
	state = State.BOARDING
	hailed.emit(fare)


## Where the customer waiting at `pickup` is going, drawn with them; null for
## a stop no one is waiting at. Public so the verify tool can read every pair.
func pick_destination(pickup: Fare.Stop) -> Fare.Stop:
	return _bound.get(pickup.key(), null)


## Draw waiting customers until `live_pickups` wait, each paired with where it
## is going. Emits `pickups_changed` when the set moved. Every draw places a
## customer or strands a kerb, which leaves the pool for good, so the loop
## ends: on a pool with fewer pickups than `live_pickups`, or one stranded
## whole, fewer wait.
func _refill() -> void:
	var drew: bool = false
	while _live.size() < _profile.live_pickups:
		var placed: Placed = _place_one(INF)
		if placed == Placed.NONE:
			break
		drew = drew or placed == Placed.PLACED
	if drew:
		pickups_changed.emit()


## One draw: a customer placed within `place_m` of the car once a sample has
## said where it is (`_placeable`, anywhere before), else at the nearest free
## kerb within `max_m`, and paired — or the kerb stranded when it pairs with
## nothing. One forward search at most.
func _place_one(max_m: float) -> Placed:
	var pickup: Fare.Stop = _draw(_placeable(_pool), _placeable(_pool_street))
	if pickup == null:
		pickup = _nearest_free(max_m)
	if pickup == null:
		return Placed.NONE
	var destination: Fare.Stop = _pair(pickup)
	if destination == null:
		_strand(pickup)
		return Placed.STRANDED
	_live.append(pickup)
	_bound[pickup.key()] = destination
	return Placed.PLACED


## The stops in `stops` a new customer may be placed at: nobody waiting there
## already, outside the hail radius of the car (or one would appear under a
## car that just stopped), and within `place_m` of it once a sample has said
## where it is. Distance first: `key()` builds a string, and few stops are near.
func _placeable(stops: Array[Fare.Stop]) -> Array[Fare.Stop]:
	var placeable: Array[Fare.Stop] = []
	var located: bool = _last_position != Vector3.INF
	for stop: Fare.Stop in stops:
		if located:
			var apart_m: float = RoadGraph.plan_distance(stop.point, _last_position)
			if apart_m <= _profile.hail_radius_m or apart_m > _profile.place_m:
				continue
		if not _bound.has(stop.key()):
			placeable.append(stop)
	return placeable


## The nearest stop past the hail radius and within `max_m` with nobody
## waiting, for a car with none free within `place_m` — a clip edge, a
## seafront — so the set still fills; null with none. Never a street spot at
## a `street_share` of 0.
func _nearest_free(max_m: float) -> Fare.Stop:
	var nearest: Fare.Stop = _nearest_free_in(_pool, max_m)
	if not _street_on():
		return nearest
	var reach_m: float = max_m
	if nearest != null:
		reach_m = RoadGraph.plan_distance(nearest.point, _last_position)
	var street: Fare.Stop = _nearest_free_in(_pool_street, reach_m)
	return street if street != null else nearest


func _nearest_free_in(stops: Array[Fare.Stop], max_m: float) -> Fare.Stop:
	var nearest: Fare.Stop = null
	var nearest_m: float = max_m
	for stop: Fare.Stop in stops:
		var apart_m: float = RoadGraph.plan_distance(stop.point, _last_position)
		if apart_m <= _profile.hail_radius_m or apart_m > nearest_m:
			continue
		if not _bound.has(stop.key()):
			nearest_m = apart_m
			nearest = stop
	return nearest


## Whether the street spots are drawn at all: a `street_share` of 0 is the
## off switch, the published points alone.
func _street_on() -> bool:
	return _profile.street_share > 0.0


## Gone from the pickup pool for the session, kept as a destination.
func _strand(pickup: Fare.Stop) -> void:
	_pool.erase(pickup)
	_pool_street.erase(pickup)
	stranded.append(pickup)


## A destination for a customer at `pickup`, drawn like a pickup from those the
## legal network reaches at `min_trip_m` or beyond; null when it reaches none.
## One forward search prices every destination (`RoadRouter.source_tree`), so a
## stranded kerb costs one search, and a kerb that reaches few is never mistaken
## for one that reaches none — drawing blind and routing each try did both.
func _pair(pickup: Fare.Stop) -> Fare.Stop:
	var tree: RoadRouter.SourceTree = _router.source_tree(pickup.edge, pickup.t)
	if tree == null:
		return null
	return _draw(_reached(tree, pickup, _dropoffs), _reached(tree, pickup, _dropoffs_street))


func _reached(
	tree: RoadRouter.SourceTree, pickup: Fare.Stop, destinations: Array[Fare.Stop]
) -> Array[Fare.Stop]:
	var reached: Array[Fare.Stop] = []
	for destination: Fare.Stop in destinations:
		if destination.same_as(pickup):
			continue
		var distance_m: float = _router.distance_from(tree, destination.edge, destination.t)
		# INF clears any bar: "no route" has to be refused by name.
		if distance_m != INF and distance_m >= _profile.min_trip_m:
			reached.append(destination)
	return reached


## One stop, uniformly on `_rng`: from `street` on `street_share` of the draws,
## from `published` on the rest, and from whichever is not empty when one is —
## but never from `street` at a share of 0, the off switch.
func _draw(published: Array[Fare.Stop], street: Array[Fare.Stop]) -> Fare.Stop:
	var street_open: bool = _street_on() and not street.is_empty()
	var from_street: bool = (
		street_open and (published.is_empty() or _rng.randf() < _profile.street_share)
	)
	var drawn_from: Array[Fare.Stop] = street if from_street else published
	if drawn_from.is_empty():
		return null
	return drawn_from[_rng.randi_range(0, drawn_from.size() - 1)]


## The allowance over `par_m` of legal road: the route at par, nothing else.
func allowance_for(par_m: float) -> float:
	return par_m / (_profile.par_kph / 3.6)


func _board() -> void:
	# The customer leaves the kerb: one fewer waiting until the fare ends.
	_live.erase(fare.pickup)
	_bound.erase(fare.pickup.key())
	pickups_changed.emit()
	fare.allowance_s = allowance_for(fare.par_m)
	fare.remaining_s = fare.allowance_s
	# A slide or a flight held into the hail is not the passenger's, nor an
	# approach the car had already lined up.
	_tracker.reset()
	_near.reset()
	# Nothing earned yet: the time is priced at the door, not here.
	fare.time_hkd = 0.0
	fare.tip_hkd = 0.0
	state = State.CARRYING
	_last_reading_hkd = fare.meter.reading_hkd()
	boarded.emit(fare)
	meter_changed.emit(_last_reading_hkd, _last_reading_hkd)


func _deliver() -> void:
	# The seconds left are priced once, here — the live tip never carried
	# them (the user's call) — then the early arrival is judged, announced
	# like any other skill so the face pops for it too, and `_award` sums
	# the tip from both parts.
	fare.time_hkd = fare.remaining_s * _profile.tip_hkd_per_s
	fare.tip_hkd = tip_of(fare.time_hkd, fare.skills_hkd)
	var early: Fare.Award = _tracker.arrival(fare.remaining_s, fare.allowance_s)
	if early != null:
		_award(early)
	fare.banked_hkd = fare.meter.reading_hkd() + fare.tip_hkd
	earned_hkd += fare.banked_hkd
	tally.note_delivered(fare)
	state = State.IDLE
	_armed = false
	_refill()
	delivered.emit(fare)
	if _closed:
		finished.emit()


## The passenger walks without paying: nothing banks, and the skills already
## paid into the tip are forfeit. `awards` and `skills_hkd` stay on the fare
## so the receipt can say what was lost.
func _bail(position: Vector3) -> void:
	fare.time_hkd = 0.0
	fare.tip_hkd = 0.0
	fare.banked_hkd = 0.0
	tally.note_bailed(fare)
	state = State.IDLE
	_armed = false
	_refill()
	bailed.emit(fare)
	_rescan(position)
	sampled.emit()
	if _closed:
		finished.emit()


## A skill paid, or a penalty docked: onto the receipt, into the tip, and
## announced. With no passenger aboard it is practice — counted and shown,
## on no fare and in no tip (the user's call).
func _award(award: Fare.Award) -> void:
	tally.note_award(award)
	# By the table, not the sign: a bonus is never a hit, whatever it pays.
	if award.skill in SessionTally.PENALTIES:
		_end_combo(true)
	else:
		combo.hit(award.skill)
		tally.note_combo(combo)
		combo_changed.emit(combo)
	if state != State.CARRYING:
		practised.emit(award)
		return
	fare.awards.append(award)
	fare.skills_hkd += award.hkd
	fare.tip_hkd = tip_of(fare.time_hkd, fare.skills_hkd)
	skilled.emit(fare, award)


## The style combo is over: a copy announced, the live one emptied. Its bests
## are already in the tally — `note_combo` weighs them at every hit, so a run
## saved mid-combo (the pause, 交更) records it without ending it.
func _end_combo(broken: bool) -> void:
	if not combo.live():
		return
	var ended: StyleCombo = combo.snapshot()
	combo.clear()
	combo_ended.emit(ended, broken)


## The tip from its two parts. Never negative: a penalty (`P3-50`) docks the
## tip and can empty it, but the passenger never charges the driver — the
## meter is the meter (`Q141`).
static func tip_of(time_hkd: float, skills_hkd: float) -> float:
	return maxf(time_hkd + skills_hkd, 0.0)


func _announce_reading() -> void:
	var reading: float = fare.meter.reading_hkd()
	if is_equal_approx(reading, _last_reading_hkd):
		return
	var delta: float = reading - _last_reading_hkd
	_last_reading_hkd = reading
	meter_changed.emit(reading, delta)


## One scan of the pickups from `position`: the pending customer a reader may
## point at, and the pickups it must not mark.
class Scan:
	extends RefCounted
	var pending: Fare.Stop = null
	var withheld: PackedInt32Array = []


## The pending customer a reader may point at: the nearest pickup while no one
## is aboard, null otherwise — hailed, a reader points at the destination and
## would throw the scan away, so the gate lives here rather than at each
## reader. ⚠️ **Never one the loop would refuse right now** (the user's call):
## after a delivery at a stand that is also a pickup the hail is disarmed
## until the car leaves reach, and an arrow pointing at the kerb under the
## car with nothing happening reads as a broken cooldown. Those pickups are
## skipped until the car is armed again.
func nearest_pending(position: Vector3) -> Fare.Stop:
	return _scan(position).pending


## The indices into `pickups()` of the customers a reader must not mark: those
## the loop would refuse right now, by `nearest_pending`'s rule. Empty while
## armed. ⚠️ **The end of a trip is not the start of another** (the user's
## call): a delivery at a stand that is also a pickup would otherwise put a
## pending ring under the car the moment the passenger is out.
func withheld_pickups(position: Vector3) -> PackedInt32Array:
	return _scan(position).withheld


## `pending` and `withheld` as of this sample, from one pass over the pool.
func _rescan(position: Vector3) -> void:
	var scan: Scan = _scan(position)
	pending = scan.pending
	withheld = scan.withheld


## Both answers in one pass: idle and armed, the nearest pickup at any distance
## and nothing withheld; idle and disarmed, the nearest pickup OUTSIDE the hail
## radius and every pickup inside it withheld; not idle, neither.
func _scan(position: Vector3) -> Scan:
	var scan := Scan.new()
	if state != State.IDLE or _closed:
		return scan
	var best_m: float = INF
	for index: int in _live.size():
		var stop: Fare.Stop = _live[index]
		var apart: float = RoadGraph.plan_distance(position, stop.point)
		if not _armed and apart <= _profile.hail_radius_m:
			scan.withheld.append(index)
			continue
		if apart <= best_m:
			best_m = apart
			scan.pending = stop
	return scan


## How often `sampled` fires, for a consumer that counts samples.
func sample_hz() -> float:
	return _profile.sample_hz if _profile != null else 0.0


## The pickup whose stop point is nearest `position` within the hail radius, or
## null. Plan distance: the stop point is on the road at the graph's height and
## the car is on the drawn ribbon, and the two differ by a kerb.
func _nearest_pickup(position: Vector3) -> Fare.Stop:
	return _nearest_pickup_within(position, _profile.hail_radius_m)


func _nearest_pickup_within(position: Vector3, max_m: float) -> Fare.Stop:
	var best: Fare.Stop = null
	var best_m: float = max_m
	for stop: Fare.Stop in _live:
		var apart: float = RoadGraph.plan_distance(position, stop.point)
		if apart <= best_m:
			best_m = apart
			best = stop
	return best


## `region`'s published nodes and street spots into the pools. A stand is a
## pickup and a destination unless it is cross-harbour (`P3-1b`'s); a PUDO
## point is what its `pickup` / `dropoff` say — a quarter are drop-off only,
## and a Hong Kong player would notice a hail at one; a tram stop (`poi`) is
## neither. A street spot is both, where the legal network drives its edge.
func _add_stops(region: String, fares: Dictionary) -> void:
	for node: Dictionary in fares.get("street", []):
		var spot: Fare.Stop = _stop(region, node)
		if spot == null:
			continue
		if not (_router.admits_way(spot.edge, true) or _router.admits_way(spot.edge, false)):
			continue
		if bool(node.get("pickup", false)):
			_pool_street.append(spot)
		if bool(node.get("dropoff", false)):
			_dropoffs_street.append(spot)
	for node: Dictionary in fares.get("nodes", []):
		var kind: String = str(node.get("kind", ""))
		if kind == GeneratedFares.POI:
			continue
		if kind == GeneratedFares.TAXI_STAND:
			var category: Variant = node.get("stand_category", null)
			if category != null and str(category) == GeneratedFares.CROSS_HARBOUR:
				continue
		elif kind != GeneratedFares.PUDO:
			continue
		var stop: Fare.Stop = _stop(region, node)
		if stop == null:
			continue
		if bool(node.get("pickup", false)):
			_pool.append(stop)
		if bool(node.get("dropoff", false)):
			_dropoffs.append(stop)


## One document node resolved into the merged graph's frame, or null where its
## edge was never published.
func _stop(region: String, node: Dictionary) -> Fare.Stop:
	var edge: int = _graph.edge_id_in(region, int(node.get("nearest_edge", -1)))
	if edge < 0:
		return null
	var stop := Fare.Stop.new()
	stop.region = region
	stop.id = str(node.get("id", ""))
	stop.node = node
	stop.edge = edge
	stop.t = clampf(float(node.get("edge_t", 0.0)), 0.0, 1.0)
	# Already in the frame: `RoadJoin.merge` moved the region's polylines by its
	# offset. Adding `region_offset` again put every neighbour stop 1.6 km off,
	# so no ring under the destination and no delivery (`verify_join`).
	stop.point = _graph.point_at(edge, stop.t)
	stop.road_en = _graph.name_of(edge, "en")
	stop.road_zh = _graph.name_of(edge, "zh")
	return stop
