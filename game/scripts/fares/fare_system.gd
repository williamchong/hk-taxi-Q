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
## **The allowance is road distance, not a table.** At boarding the legal
## route's length over `par_kph`, floored by the kind — `GAME_DESIGN.md`'s 30 s
## and 60 s survive as floors. Legal, not the player's profile (`Q137`'s
## recommendation): par is what a driver obeying the signs would do, and the
## player may break every rule to beat it.
##
## **The reach is computed once, at load; the hail pays one `prepare`.**
## `.claude/rules/router.md`: `prepare` is a reverse Dijkstra priced against a
## frame (0.7 ms legal on Wan Chai), `route` then microseconds. `setup` prepares
## every destination once and routes every pickup to it — 19 × 23 on Wan Chai,
## ~20 ms — and keeps, per pickup, which destinations the legal network reaches
## at `min_trip_m` or beyond. A hail draws uniformly from that list and routes
## once for the par. Drawing blind and retrying was built first and refused:
## a stand with one reachable destination was refused most of its hails.
##
## ⚠️ **"No route" is an answer** (`Q137`), and here it is a pool decision. 40%
## of ordered fare pairs in Wan Chai have none — the clip is not strongly
## connected — and a pickup that reaches NO destination is **stranded**: kept
## as a destination, dropped as a pickup, counted and named, never asserted. On
## the shipped regions these are the westbound Hennessy and Johnston Road
## points at the clip's west edge and Causeway Bay's far-side stands: forward
## leaves the clip and the one-way network never comes back.
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
## or over `HandlingProfile.drift_slip_threshold_deg` for `SkillProfile.drift_s`
## pays `drift_hkd`, a run over `speed_min_kph` for `speed_hold_s` pays
## `speed_hkd`, each again for each further dwell, and an arrival with
## `early_share` of the allowance left pays `early_hkd` at the door. Each is
## a flat HK$ into `Fare.tip_hkd` the moment it is earned and a line on the
## receipt; `skilled` says so. A bail forfeits the lot — the passenger walks
## without paying, and the receipt says what walked.
##
## ⚠️ **`slip_deg_of` is a second copy of `skidpad_ablation.gd`'s slip, on
## purpose** (`Q84`): the grader must never call what it grades, so the
## instrument keeps its own, and the game — the consumer `PLAN.md` held the
## slip signal back for — now has this one. Same flattening, same floor.
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
## Emitted whenever the reading moves: the new reading in HK$, and the unit
## that just began — the flagfall at boarding — so a readout that shows the
## tick keeps no copy of the last reading (`P3-5a`).
signal meter_changed(hkd: float, delta_hkd: float)
## Emitted after each graph sample, at `sample_hz`: when a readout should
## re-read `state`, `fare` and the counters. Never per frame.
signal sampled

const GeneratedFares = preload("res://scripts/city/generated_fares.gd")
const GeneratedRegions = preload("res://scripts/city/generated_regions.gd")

## `--fares=off` frees this node. Read by prefix, like `--hud=`.
const FARES_ARG: String = "--fares="
## `--fare-seed=<int>` seeds the destination draw; absent, it is randomised.
const SEED_ARG: String = "--fare-seed="
## Ground speed under which a slip angle is noise rather than a measurement:
## a nearly stationary car has a velocity vector pointing anywhere at all.
## `skidpad_ablation.gd`'s `SLIP_FLOOR_MPS`, restated on purpose (see above).
const SLIP_FLOOR_MPS: float = 1.0

enum State { IDLE, BOARDING, CARRYING }

## The car. Set by the scene; `setup()` leaves it null for a headless run.
@export var vehicle: VehicleController

var state: State = State.IDLE
## The fare in flight, or the last one to end; null before the first hail.
var fare: Fare = null
## Everything banked this session, in HK$.
var earned_hkd: float = 0.0
## The counters a drive is checked against.
var deliveries: int = 0
var bails: int = 0
var cancellations: int = 0
var hail_refusals: int = 0
## The pickups `setup` dropped for reaching no destination, in document order.
var stranded: Array[Fare.Stop] = []
## What the reach table cost to build, in milliseconds.
var reach_ms: float = 0.0

var _profile: FareProfile = null
var _tariff: FareTariff = null
var _skills: SkillProfile = null
## `HandlingProfile.drift_slip_threshold_deg`, handed in: the angle a slide
## must hold to be a drift.
var _slip_threshold_deg: float = 0.0
## The skills of the fare in flight; null between fares.
var _tracker: SkillTracker = null
var _rng: RandomNumberGenerator = null
# A member, not a local: `RoadGraph.shared()` holds it weakly.
var _graph: RoadGraph = null
var _router: RoadRouter = null
var _pickups: Array[Fare.Stop] = []
var _dropoffs: Array[Fare.Stop] = []
## Per pickup id, the indices into `_dropoffs` the legal network reaches from
## it at `min_trip_m` or beyond.
var _reach: Dictionary[String, PackedInt32Array] = {}
## False until a whole profile and tariff were handed in; nothing is judged before then.
var _usable: bool = false
var _sample_accum_s: float = 0.0
var _board_accum_s: float = 0.0
## Whether a hail may start. Cleared when a fare ends or a hail is refused,
## and set again once the car has been outside every hail radius at a sample —
## or a delivery at a stand that is also a pickup would hail again on the spot.
var _armed: bool = true
var _last_reading_hkd: float = 0.0


func _ready() -> void:
	if Cmdline.value(FARES_ARG).to_lower() == "off":
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
	setup(
		RoadGraph.shared(),
		fares,
		load(FareProfile.PATH) as FareProfile,
		load(FareTariff.PATH) as FareTariff,
		load(SkillProfile.PATH) as SkillProfile,
		vehicle.profile.drift_slip_threshold_deg if vehicle.profile != null else 0.0,
		rng
	)
	if not _usable:
		set_physics_process(false)
		return
	var names: PackedStringArray = []
	for stop: Fare.Stop in stranded:
		names.append("%s/%s" % [stop.region, stop.id])
	print(
		(
			"fares: %d pickups (%d stranded: %s), %d destinations, reach %.1f ms"
			% [_pickups.size(), stranded.size(), ", ".join(names), _dropoffs.size(), reach_ms]
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
	rng: RandomNumberGenerator
) -> void:
	_usable = false
	if graph == null or graph.is_empty():
		push_error("FareSystem: the road graph is empty; nothing will be hailed.")
		return
	if profile == null:
		push_error("FareSystem: no FareProfile handed in; nothing will be hailed.")
		return
	if skills == null:
		push_error("FareSystem: no SkillProfile handed in; nothing will be hailed.")
		return
	var required: Dictionary[String, float] = {
		"hail_radius_m": profile.hail_radius_m,
		"board_s": profile.board_s,
		"deliver_radius_m": profile.deliver_radius_m,
		"stop_below_kph": profile.stop_below_kph,
		"min_trip_m": profile.min_trip_m,
		"par_kph": profile.par_kph,
		"short_hop_floor_s": profile.short_hop_floor_s,
		"standard_floor_s": profile.standard_floor_s,
		"tip_hkd_per_s": profile.tip_hkd_per_s,
		"sample_hz": profile.sample_hz,
	}
	if _any_zero(profile, required):
		return
	var skill_keys: Dictionary[String, float] = {
		"drift_s": skills.drift_s,
		"drift_hkd": skills.drift_hkd,
		"speed_min_kph": skills.speed_min_kph,
		"speed_hold_s": skills.speed_hold_s,
		"speed_hkd": skills.speed_hkd,
		"early_share": skills.early_share,
		"early_hkd": skills.early_hkd,
	}
	if _any_zero(skills, skill_keys):
		return
	if slip_threshold_deg <= 0.0:
		push_error("FareSystem: no drift_slip_threshold_deg handed in; nothing will be hailed.")
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
	_skills = skills
	_slip_threshold_deg = slip_threshold_deg
	_rng = rng
	_router = RoadRouter.new(graph, RoadRouter.Profile.legal())
	_pickups.clear()
	_dropoffs.clear()
	for region: String in fares_by_region:
		_add_stops(region, fares_by_region[region])
	_build_reach()
	_usable = true


## Whether any of `table`'s `fields` reads zero — a key missing from the
## `.tres`, since neither profile declares a default — naming the file and
## the field.
static func _any_zero(table: Resource, fields: Dictionary[String, float]) -> bool:
	for key: String in fields:
		if fields[key] <= 0.0:
			push_error(
				"FareSystem: %s has no %s; nothing will be hailed." % [table.resource_path, key]
			)
			return true
	return false


func usable() -> bool:
	return _usable


## The stops a fare may start at, and end at.
func pickups() -> Array[Fare.Stop]:
	return _pickups


func dropoffs() -> Array[Fare.Stop]:
	return _dropoffs


## Whether the next sample inside a hail radius may hail.
func armed() -> bool:
	return _armed


func _physics_process(delta: float) -> void:
	var placed: Transform3D = vehicle.global_transform
	var velocity: Vector3 = vehicle.linear_velocity
	var nose: Vector3 = -placed.basis.z
	# The slip is only read while a passenger is aboard.
	var slip: float = slip_deg_of(velocity, nose) if state == State.CARRYING else 0.0
	sample(placed.origin, velocity.length(), nose, delta, slip)


## The angle between where the car points and where it is going, in degrees,
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
## `heading` with `slip_deg` between the two, `delta_s` after the last tick.
## The odometer, the clock and the skills run every tick; the graph is asked
## once per `sample_hz`.
func sample(
	position: Vector3, speed_mps: float, heading: Vector3, delta_s: float, slip_deg: float = 0.0
) -> void:
	if not _usable:
		return
	var elapsed: float = maxf(delta_s, 0.0)
	if state == State.CARRYING:
		fare.meter.advance(maxf(speed_mps, 0.0) * elapsed, elapsed)
		_announce_reading()
		for award: Fare.Award in _tracker.tick(maxf(speed_mps, 0.0) * 3.6, slip_deg, elapsed):
			_award(award)
		fare.remaining_s -= elapsed
		if fare.remaining_s <= 0.0:
			fare.remaining_s = 0.0
			_bail()
			return
		# The tip as it stands: what the clock would pay if the passenger got
		# out now, plus what the skills have paid. Live, so the HUD can show
		# it falling with the seconds and jumping with a skill.
		fare.time_hkd = fare.remaining_s * _profile.tip_hkd_per_s
		fare.tip_hkd = tip_of(fare.time_hkd, fare.skills_hkd)

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
	sampled.emit()


func _sample_idle(position: Vector3, speed_kph: float) -> void:
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
	drawn.plan_m = route.plan_m
	drawn.remaining_road_m = route.distance_m
	drawn.route = route
	drawn.route_from_t = pickup.t
	drawn.meter = FareMeter.new(_tariff)
	fare = drawn
	_board_accum_s = 0.0
	state = State.BOARDING
	hailed.emit(fare)


## A destination for a fare hailed at `pickup`: one drawn uniformly on `_rng`
## from what the reach table says the legal network reaches from it at
## `min_trip_m` or beyond; null for a pickup the table does not know. Public so
## the verify tool can draw at every pickup.
func pick_destination(pickup: Fare.Stop) -> Fare.Stop:
	var reachable: PackedInt32Array = _reach.get(pickup.id, PackedInt32Array())
	if reachable.is_empty():
		return null
	return _dropoffs[reachable[_rng.randi_range(0, reachable.size() - 1)]]


## Which destinations each pickup reaches, and which pickups reach none. One
## `prepare` per destination, one `route` per pair; the cost is `reach_ms`.
func _build_reach() -> void:
	var started: int = Time.get_ticks_usec()
	_reach.clear()
	stranded.clear()
	for index: int in _dropoffs.size():
		var destination: Fare.Stop = _dropoffs[index]
		if not _router.prepare(destination.edge, destination.t):
			continue
		for pickup: Fare.Stop in _pickups:
			if pickup.same_as(destination):
				continue
			var route: RoadRouter.Route = _router.route(
				pickup.edge, pickup.t, destination.edge, destination.t
			)
			if not route.found or route.distance_m < _profile.min_trip_m:
				continue
			if not _reach.has(pickup.id):
				_reach[pickup.id] = PackedInt32Array()
			_reach[pickup.id].append(index)
	var kept: Array[Fare.Stop] = []
	for pickup: Fare.Stop in _pickups:
		if _reach.has(pickup.id):
			kept.append(pickup)
		else:
			stranded.append(pickup)
	_pickups = kept
	reach_ms = float(Time.get_ticks_usec() - started) / 1000.0


## How many destinations `pickup` reaches; 0 for one the table does not know.
func reach_of(pickup: Fare.Stop) -> int:
	return _reach.get(pickup.id, PackedInt32Array()).size()


## The allowance a fare of `kind` gets over `par_m` of legal road.
func allowance_for(kind: Fare.Kind, par_m: float) -> float:
	var floor_s: float = (
		_profile.short_hop_floor_s if kind == Fare.Kind.SHORT_HOP else _profile.standard_floor_s
	)
	return maxf(floor_s, par_m / (_profile.par_kph / 3.6))


func _board() -> void:
	fare.allowance_s = allowance_for(fare.kind, fare.par_m)
	fare.remaining_s = fare.allowance_s
	_tracker = SkillTracker.new(_skills, _slip_threshold_deg)
	fare.time_hkd = fare.remaining_s * _profile.tip_hkd_per_s
	fare.tip_hkd = fare.time_hkd
	state = State.CARRYING
	_last_reading_hkd = fare.meter.reading_hkd()
	boarded.emit(fare)
	meter_changed.emit(_last_reading_hkd, _last_reading_hkd)


func _deliver() -> void:
	# The early arrival is judged at the door, before the tip is summed, and
	# announced like any other skill so the face pops for it too.
	var early: Fare.Award = _tracker.arrival(fare.remaining_s, fare.allowance_s)
	if early != null:
		_award(early)
	_tracker = null
	# `time_hkd` and `tip_hkd` are already current: `sample` priced them this
	# tick, and `_award` re-summed the tip if the early arrival paid.
	fare.banked_hkd = fare.meter.reading_hkd() + fare.tip_hkd
	earned_hkd += fare.banked_hkd
	deliveries += 1
	state = State.IDLE
	_armed = false
	delivered.emit(fare)


## The passenger walks without paying: nothing banks, and the skills already
## paid into the tip are forfeit. `awards` and `skills_hkd` stay on the fare
## so the receipt can say what was lost.
func _bail() -> void:
	_tracker = null
	fare.time_hkd = 0.0
	fare.tip_hkd = 0.0
	fare.banked_hkd = 0.0
	bails += 1
	state = State.IDLE
	_armed = false
	bailed.emit(fare)
	sampled.emit()


## A skill paid, or a penalty docked: onto the receipt, into the tip, and
## announced.
func _award(award: Fare.Award) -> void:
	fare.awards.append(award)
	fare.skills_hkd += award.hkd
	fare.tip_hkd = tip_of(fare.time_hkd, fare.skills_hkd)
	skilled.emit(fare, award)


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


## The pickup nearest `position` at any distance, or null with an empty pool:
## where the closest pending customer is, for the guide and the map while
## no one is aboard (`P3-5a`, `Q142`). ⚠️ Not the hail: `_nearest_pickup`
## keeps the radius, and this never hails.
func nearest_pickup_any(position: Vector3) -> Fare.Stop:
	return _nearest_pickup_within(position, INF)


## The pending customer a reader may point at: the nearest pickup while no one
## is aboard, null otherwise — hailed, a reader points at the destination and
## would throw the scan away, so the gate lives here rather than at each
## reader. ⚠️ **Never one the loop would refuse right now** (the user's call):
## after a delivery at a stand that is also a pickup the hail is disarmed
## until the car leaves reach, and an arrow pointing at the kerb under the
## car with nothing happening reads as a broken cooldown. Those pickups are
## skipped until the car is armed again.
func nearest_pending(position: Vector3) -> Fare.Stop:
	if state != State.IDLE:
		return null
	if _armed:
		return nearest_pickup_any(position)
	var best: Fare.Stop = null
	var best_m: float = INF
	for stop: Fare.Stop in _pickups:
		var apart: float = RoadGraph.plan_distance(position, stop.point)
		if apart <= _profile.hail_radius_m or apart > best_m:
			continue
		best_m = apart
		best = stop
	return best


## The indices into `pickups()` of the customers a reader must not mark: those
## the loop would refuse right now, by `nearest_pending`'s rule. Empty while
## armed. ⚠️ **The end of a trip is not the start of another** (the user's
## call): a delivery at a stand that is also a pickup would otherwise put a
## pending ring under the car the moment the passenger is out.
func withheld_pickups(position: Vector3) -> PackedInt32Array:
	var withheld := PackedInt32Array()
	if _armed:
		return withheld
	for index: int in _pickups.size():
		if RoadGraph.plan_distance(position, _pickups[index].point) <= _profile.hail_radius_m:
			withheld.append(index)
	return withheld


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
	for stop: Fare.Stop in _pickups:
		var apart: float = RoadGraph.plan_distance(position, stop.point)
		if apart <= best_m:
			best_m = apart
			best = stop
	return best


## `region`'s published nodes into the two pools. A stand is a pickup and a
## destination unless it is cross-harbour (`P3-1b`'s); a PUDO point is what its
## `pickup` / `dropoff` say — a quarter are drop-off only, and a Hong Kong
## player would notice a hail at one; a tram stop (`poi`) is neither.
func _add_stops(region: String, fares: Dictionary) -> void:
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
		var edge: int = _graph.edge_id_in(region, int(node.get("nearest_edge", -1)))
		if edge < 0:
			continue
		var stop := Fare.Stop.new()
		stop.region = region
		stop.id = str(node.get("id", ""))
		stop.node = node
		stop.edge = edge
		stop.t = clampf(float(node.get("edge_t", 0.0)), 0.0, 1.0)
		stop.point = _graph.point_at(edge, stop.t) + _graph.region_offset(region)
		stop.road_en = _graph.name_of(edge, "en")
		stop.road_zh = _graph.name_of(edge, "zh")
		if bool(node.get("pickup", false)):
			_pickups.append(stop)
		if bool(node.get("dropoff", false)):
			_dropoffs.append(stop)
