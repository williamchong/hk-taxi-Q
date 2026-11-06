class_name TrafficKerbside
extends RefCounted
## Where a kerb-stopping car pulls up for a passenger, and the speed it brakes to
## for it (`P3-78`, `Q187`). Owned by `TrafficSystem`, whose roads, parked
## vehicles and counters it reads and writes.
##
## 🔴 **A stop draws on `_rng`, never the traffic's**: one more roll there would
## move every later car. It is seeded off the traffic's seed in `seed_from`.

var _system: TrafficSystem
var _rng := RandomNumberGenerator.new()


func _init(system: TrafficSystem) -> void:
	_system = system


## The stops' own stream, off the traffic's seed.
func seed_from(seed: int) -> void:
	_rng.seed = seed * 15485863 + 5


## On joining a road, whether a kerb-stopping kind (`kerb_stop_kinds`) pulls up
## on it for a passenger, and where: on `_rng`, at a chance of the road's
## usable length over `kerb_stop_every_m`, on the nearside kerb, at least
## `lane_change_m` clear of where it joined and of the road's far mouth, on no
## published no-stopping run (`RoadGraph.no_stopping`: a double or single yellow
## line), beside no parked vehicle, and never before a turn taken from the
## offside lane — it moves over to the nearside lane for it. A red minibus or a
## taxi may stop on the line anyway (`kerb_unlawful_share`). Never on its own
## route's stop's road and way.
func pick(car: TrafficSystem.Car) -> void:
	car.kerb_m = INF
	car.kerb_left = 0.0
	var graph: RoadGraph = _system.graph
	var profile: TrafficProfile = _system.profile
	if (
		car.knocked
		or car.dwell_left > 0.0
		or not stops_at_kerb(car)
		or car.turn_side == -1
		or graph.level_of(car.edge) != 0
		or TrafficRouted.is_goal_way(car, car.edge, car.along)
	):
		return
	var length_m: float = car.length_m
	var trim: Vector2 = graph.trim_of(car.edge)
	var far_trim: float = trim.y if car.along else trim.x
	var start: float = car.s + profile.lane_change_m + car.half_length * 2.0
	var end: float = length_m - far_trim - profile.lane_change_m
	if end <= start:
		return
	var chance: float = 1.0 - exp(-(end - start) / profile.kerb_stop_every_m)
	if _rng.randf() >= chance:
		return
	var front: float = _rng.randf_range(start, end)
	var back: float = front - car.half_length * 2.0
	var a: float = TrafficSystem._edge_m(back, length_m, car.along)
	var b: float = TrafficSystem._edge_m(front, length_m, car.along)
	# Drawn every time, so whether this car may break the rule moves no later draw.
	var reckless: bool = _rng.randf() < profile.kerb_unlawful_share
	var restricted: bool = graph.no_stopping(car.edge, car.along, minf(a, b), maxf(a, b))
	if restricted and not (reckless and may_stop_unlawfully(car)):
		return
	if (
		_system._nearest_parked(
			car.edge, car.along, length_m, 0.0, car, back - profile.gap_m, front + profile.gap_m
		)
		< INF
	):
		return
	car.kerb_m = front
	# Over to the nearside lane for it: a straight on or a left leaves from any lane.
	car.lane_out = 0.0
	_system.kerb_picked += 1
	if restricted:
		_system.kerb_unlawful += 1


## Whether `car` is a kind that pulls up at the kerb for a passenger
## (`kerb_stop_kinds`): a minibus or a taxi, whatever licence it wears.
func stops_at_kerb(car: TrafficSystem.Car) -> bool:
	return _system.profile.kerb_stop_kinds.has(_system.rules_kind(car))


## Whether `car` is a kind that stops on a no-stopping line now and then
## (`kerb_unlawful_kinds`: the red minibus and every taxi, the user's call
## 2026-11-06) — never a routed vehicle, so never a green minibus.
func may_stop_unlawfully(car: TrafficSystem.Car) -> bool:
	return car.route == null and _system.profile.kerb_unlawful_kinds.has(_system.rules_kind(car))


## The speed a kerb-stopping car may drive at for its kerbside stop: it brakes to
## its front at the spot, stands `kerb_dwell_s` there, then pulls out winking
## right for `pull_out_m`. Off the nearside lane when it gets there, it drives on.
func limit(car: TrafficSystem.Car, delta: float) -> float:
	var profile: TrafficProfile = _system.profile
	if car.kerb_left > 0.0:
		car.kerb_left -= delta
		if car.kerb_left > 0.0:
			return 0.0
		_system._pull_out(car)
		return INF
	if car.turning:
		return INF
	var to_kerb: float = car.kerb_m - car.s - car.half_length
	if to_kerb < -profile.dwell_reach_m:
		car.kerb_m = INF
		_system.kerb_missed += 1
		return INF
	if car.speed < TrafficSystem.STOPPED_MPS and to_kerb < profile.dwell_reach_m:
		car.kerb_m = INF
		if not TrafficSystem.same_lane(car.lane, 0.0):
			_system.kerb_missed += 1
			return INF
		car.kerb_left = profile.kerb_dwell_s
		_system.kerb_served += 1
		return 0.0
	return TrafficSystem.stopping_speed(to_kerb, profile.brake_mps2)
