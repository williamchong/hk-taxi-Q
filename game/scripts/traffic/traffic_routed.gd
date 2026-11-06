class_name TrafficRouted
extends RefCounted
## The routed fleet (`P3-78`): where a bus is placed this hour, and how it brakes
## for, stands at and leaves each stop on its route. Owned by `TrafficSystem`,
## whose cars, roads, router and counters it reads and writes.
##
## 🔴 **A placement draws on `_rng`, never the traffic's**: one more roll there
## would move every later wandering car. It is seeded off the traffic's seed in
## `seed_from`.

const ParkedRoster = preload("res://scripts/city/parked_roster.gd")

var _system: TrafficSystem
var _rng := RandomNumberGenerator.new()
## Where a routed vehicle may be placed this hour, `(route, stop)`, and the weight
## of each: its route's departures in the hour.
var _spawn_pool: Array[Vector2i] = []
var _spawn_weights: PackedFloat32Array = []
var _spawn_hour: int = -1


func _init(system: TrafficSystem) -> void:
	_system = system


## The routed fleet's own stream, off the traffic's seed.
func seed_from(seed: int) -> void:
	_rng.seed = seed * 7919 + 1


## Rebuild where a routed vehicle may be placed when the hour has moved: every stop
## on a road with one after it, weighted by its route's departures this hour.
func refresh_spawn_pool(hour: int) -> void:
	var bus_routes: BusRoutes = _system.bus_routes
	if bus_routes == null:
		return
	if hour == _spawn_hour:
		return
	_spawn_hour = hour
	_spawn_pool.clear()
	_spawn_weights.clear()
	for index: int in bus_routes.routes.size():
		var route: BusRoutes.Route = bus_routes.routes[index]
		var departures: float = float(route.per_hour[hour])
		if departures <= 0.0 or not _system._routed_kinds.has(route.kind):
			continue
		for stop: int in route.stops.size() - 1:
			if route.stops[stop].edge >= 0:
				_spawn_pool.append(Vector2i(index, stop))
				_spawn_weights.append(departures)


## Place an idle routed slot at a stop in the ring, mid-dwell, on a route drawn by
## its departures this hour (`P3-78`).
func try_spawn(car: TrafficSystem.Car, here: Vector3) -> void:
	if _spawn_pool.is_empty():
		return
	var system: TrafficSystem = _system
	var profile: TrafficProfile = system.profile
	var pick: Vector2i = _spawn_pool[_rng.rand_weighted(_spawn_weights)]
	var route: BusRoutes.Route = system.bus_routes.routes[pick.x]
	var stop: BusRoutes.Stop = route.stops[pick.y]
	var kind: int = system._routed_kinds.get(route.kind, -1)
	if kind < 0 or not system.router.admits_way(stop.edge, stop.along):
		return
	var length_m: float = system.graph.plan_length_of(stop.edge)
	var half_length: float = system._extents[kind].size.z * 0.5
	var s: float = clampf(stop.travel_m - half_length, 0.0, length_m)
	var at: Vector3 = system.graph.lane_at(
		stop.edge, TrafficSystem._edge_m(s, length_m, stop.along), stop.along
	)
	if not system._in_ring_and_clear(at, here):
		return
	var palette: PackedColorArray = system._palette(profile.route_liveries, route.kind)
	system._wear_kind(car, kind, ParkedRoster.livery(_rng.randi() & 0xFFFF, palette))
	if (
		system._nearest_parked(
			stop.edge,
			stop.along,
			length_m,
			0.0,
			car,
			s - half_length - profile.gap_m,
			s + half_length + profile.gap_m
		)
		< INF
	):
		return
	car.route = route
	car.stop_index = pick.y
	car.goal = null
	# Found part-way through its dwell, as a bus is.
	car.dwell_left = _rng.randf_range(profile.placed_dwell_left, 1.0) * profile.dwell_s
	system._place(car, stop.edge, stop.along, s, 0.0, 0.0)
	system.routed_spawned += 1


## Whether `edge` driven its `along` way is where `car`'s next stop stands.
static func is_goal_way(car: TrafficSystem.Car, edge: int, along: bool) -> bool:
	return (
		car.goal != null
		and car.goal.edge_id == edge
		and car.route.stops[car.stop_index].along == along
	)


## How far `car`'s front is short of `stop`'s pole along its road.
static func to_pole(car: TrafficSystem.Car, stop: BusRoutes.Stop) -> float:
	return stop.travel_m - car.s - car.half_length


## The speed a routed vehicle may drive at for its stop: it brakes to its front at
## the pole, stands `dwell_s` there, then sets off for the next. INF where its stop
## is not ahead on this road.
func stop_limit(car: TrafficSystem.Car, delta: float) -> float:
	var profile: TrafficProfile = _system.profile
	if car.dwell_left > 0.0:
		car.dwell_left -= delta
		if car.dwell_left > 0.0:
			return 0.0
		_system._pull_out(car)
		depart(car)
		return INF
	if car.goal == null or car.turning or not is_goal_way(car, car.edge, car.along):
		return INF
	var pole: float = to_pole(car, car.route.stops[car.stop_index])
	if pole < -profile.dwell_reach_m:
		# Past it: placed beyond it, or carried by when it could not stop.
		_system.stops_missed += 1
		depart(car)
		return INF
	if car.speed < TrafficSystem.STOPPED_MPS and pole < profile.dwell_reach_m:
		car.dwell_left = profile.dwell_s
		_system.stops_served += 1
		return 0.0
	return TrafficSystem.stopping_speed(pole, profile.brake_mps2)


## Done at a stop: aim for the next one it can reach and plan the move toward it.
func depart(car: TrafficSystem.Car) -> void:
	car.dwell_left = 0.0
	car.stop_index += 1
	aim(car)
	_system._plan_move(car)


## Search toward `car`'s stop at `stop_index`, or the first after it that it can
## drive to from where it stands; past its run's last stop it leaves its route.
func aim(car: TrafficSystem.Car) -> void:
	var router: RoadRouter = _system.router
	car.goal = null
	while car.route != null and car.stop_index < car.route.stops.size():
		var stop: BusRoutes.Stop = car.route.stops[car.stop_index]
		if stop.edge >= 0:
			car.goal = router.goal_tree(stop.edge, stop.t, stop.along)
			if car.goal != null:
				var ahead: bool = (
					to_pole(car, stop) > -_system.profile.dwell_reach_m
					if is_goal_way(car, car.edge, car.along)
					else router.next_toward(car.goal, car.edge, car.along).x >= 0
				)
				if ahead:
					return
			_system.stops_unreachable += 1
			car.goal = null
		car.stop_index += 1
	leave_route(car)


## Off its route for good: from here it wanders as any car.
static func leave_route(car: TrafficSystem.Car) -> void:
	car.route = null
	car.goal = null
	car.stop_index = -1
	car.dwell_left = 0.0
