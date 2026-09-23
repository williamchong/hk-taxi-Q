extends SceneTree

## The fare loop's contracts (`P3-1a`, `Q141`): the tariff's arithmetic, the two
## pools, every pickup's reach, the allowance, and the state machine driven by
## synthetic samples — dwells and bars from both sides, and every counter moved.
##
## Runs once per synced region (`check.sh`'s `VERIFY_TOOLS`): the pools and the
## reach are that region's `fares.json` against its graph, and the stand with
## no legal destination at `min_trip_m` is a finding about the data, named.
##
## ⚠️ **The assertions are written so they can fail** (`Q72`). Each table is
## graded as shipped and then a duplicate is mutated to prove the check is
## live: a linear meter, a halved tip, a drop-off-only point smuggled into the
## pickup pool. A check that cannot fail certifies whatever the code does.
##
## 🔴 **This tool CAN print `verify_fares: ok` having checked nothing.** A
## `preload`ed script that fails to compile aborts the calling function at
## `new()`, and `_init` runs on to `quit(0)`. `tools/check.sh` greps stderr for
## `SCRIPT ERROR`; that is the guard, and why the tool is never run by hand.
##
## ⚠️ **Nothing here references a `class_name` global.** Everything is
## `preload`ed by path, so a fresh clone with no class cache still parses.

const GeneratedRoadGraph = preload("res://scripts/city/generated_road_graph.gd")
const GeneratedFares = preload("res://scripts/city/generated_fares.gd")
const GeneratedRegions = preload("res://scripts/city/generated_regions.gd")
const RoadGraphScript = preload("res://scripts/city/road_graph.gd")
const RouterScript = preload("res://scripts/city/road_router.gd")
const CityManifestScript = preload("res://scripts/city/city_manifest.gd")
const FareSystemScript = preload("res://scripts/fares/fare_system.gd")
const FareMeterScript = preload("res://scripts/core/fare_meter.gd")
const FareProfileScript = preload("res://scripts/fares/fare_profile.gd")
const FareTariffScript = preload("res://scripts/fares/fare_tariff.gd")

## ⚠️ **The paths come from the scripts the game loads, never restated here.**

## One tick that is also one graph sample at the shipped 5 Hz, and exact in
## binary so a dwell of 1.0 s is reached on the fourth tick and not the fifth.
const TICK_S: float = 0.25
## Well under the shipped `stop_below_kph` (5 kph is 1.39 m/s), and well over.
const CRAWL: float = 0.5
const FAST: float = 10.0
## The draw every seeded system in this file uses, so two of them agree.
const SEED: int = 7
## Somewhere no fare node is: the pools are inside the region and this is not.
const FAR_AWAY := Vector3(-100000.0, 0.0, -100000.0)

var _failed: int = 0
var _graph: RoadGraph = null
var _region: String = ""
var _fares: Dictionary = {}
var _profile: FareProfile = null
var _tariff: FareTariff = null


func _init() -> void:
	var document: Dictionary = GeneratedRoadGraph.load_graph()
	var manifest: CityManifest = CityManifestScript.load_manifest()
	if document.is_empty() or manifest == null:
		quit(1)
		return
	_graph = RoadGraphScript.from_document(document, manifest)
	_region = GeneratedRegions.selected()
	_fares = GeneratedFares.load_fares(manifest.fares_path)
	_profile = load(FareProfileScript.PATH) as FareProfile
	_tariff = load(FareTariffScript.PATH) as FareTariff
	if _fares.is_empty() or _profile == null or _tariff == null:
		printerr("  FAIL  fares, profile or tariff did not load")
		quit(1)
		return

	_check_tariff()
	_check_pools()
	_check_reach()
	_check_allowance()
	_check_loop()

	if _failed > 0:
		push_error("verify_fares: %d check(s) failed" % _failed)
		quit(1)
		return
	print("verify_fares: ok")
	quit(0)


## The tariff against hand-computed points, in cents.
func _check_tariff() -> void:
	var cases: Array = [
		[0.0, 29.0],
		[2000.0, 29.0],
		[2001.0, 31.1],
		[2200.0, 31.1],
		[2201.0, 33.2],
		[9000.0, 102.5],
		[9200.0, 103.9],
	]
	for case: Array in cases:
		var meter: FareMeter = FareMeterScript.new(_tariff)
		meter.advance(float(case[0]), 0.0)
		_expect(
			is_equal_approx(meter.reading_hkd(), float(case[1])),
			"tariff",
			"%.0f m reads HK$%.1f (got %.2f)" % [case[0], case[1], meter.reading_hkd()]
		)

	# Waiting: nothing on the flagfall, a unit per minute past it, and the two
	# buckets reset together.
	var waiting: FareMeter = FareMeterScript.new(_tariff)
	waiting.advance(0.0, 600.0)
	_expect(
		is_equal_approx(waiting.reading_hkd(), 29.0), "tariff", "10 min on the flagfall is HK$29"
	)
	waiting.advance(2001.0, 0.0)
	waiting.advance(0.0, 60.0)
	_expect(is_equal_approx(waiting.reading_hkd(), 31.1), "tariff", "60 s waited is still one unit")
	waiting.advance(0.0, 1.0)
	_expect(is_equal_approx(waiting.reading_hkd(), 33.2), "tariff", "61 s waited begins the next")
	waiting.advance(100.0, 30.0)
	_expect(is_equal_approx(waiting.reading_hkd(), 33.2), "tariff", "30 s and 100 m fill neither")
	waiting.advance(101.0, 0.0)
	_expect(is_equal_approx(waiting.reading_hkd(), 35.3), "tariff", "201 m begins a unit")
	waiting.advance(0.0, 45.0)
	_expect(
		is_equal_approx(waiting.reading_hkd(), 35.3),
		"tariff",
		(
			"the time bucket was reset by the distance unit (%.1f at 75 s unreset)"
			% waiting.reading_hkd()
		)
	)
	waiting.advance(0.0, 16.0)
	_expect(
		is_equal_approx(waiting.reading_hkd(), 37.4), "tariff", "61 s after that unit, the next"
	)

	# Mutations: a linear meter fails the 2,200 m point; a zero unit is inert.
	var linear: FareTariff = _tariff.duplicate()
	linear.step_m = 1.0
	var mutated: FareMeter = FareMeterScript.new(linear)
	mutated.advance(2200.0, 0.0)
	_expect(
		not is_equal_approx(mutated.reading_hkd(), 31.1),
		"tariff",
		"mutation caught: step_m 1 reads HK$%.1f at 2,200 m" % mutated.reading_hkd()
	)
	var broken: FareTariff = _tariff.duplicate()
	broken.step_hkd = 0.0
	var inert: FareMeter = FareMeterScript.new(broken)
	inert.advance(9000.0, 0.0)
	_expect(
		not inert.usable() and is_zero_approx(inert.reading_hkd()),
		"tariff",
		"a zero price makes an inert meter, never a literal"
	)


## The two pools: what is in them and what is kept out, shipped and smuggled.
func _check_pools() -> void:
	var system: FareSystem = _system(_fares, _profile, SEED)
	_expect(system.usable(), "pools", "the shipped tables construct a usable system")
	var pickups: Array[Fare.Stop] = system.pickups()
	var dropoffs: Array[Fare.Stop] = system.dropoffs()
	print(
		(
			"  pools: %d pickups, %d destinations, %d stranded"
			% [pickups.size(), dropoffs.size(), system.stranded.size()]
		)
	)
	_expect(not dropoffs.is_empty(), "pools", "the destination pool is non-empty")
	# A region every pickup of which is stranded has an empty pool by the reach
	# rule, not by a load failure: `causeway_bay` alone is that region — its
	# stands reach Wan Chai only across the join. Said, and never silent.
	_expect(
		not pickups.is_empty() or not system.stranded.is_empty(),
		"pools",
		(
			"the pickup pool is non-empty"
			if not pickups.is_empty()
			else "SKIP: every pickup is stranded on this region alone"
		)
	)
	for stop: Fare.Stop in pickups:
		var kind: String = str(stop.node.get("kind", ""))
		var category: Variant = stop.node.get("stand_category", null)
		if kind == GeneratedFares.POI:
			_fail("pools", "%s is a tram stop in the pickup pool" % stop.id)
		if category != null and str(category) == GeneratedFares.CROSS_HARBOUR:
			_fail("pools", "%s is a cross-harbour stand in the pickup pool" % stop.id)
		if not bool(stop.node.get("pickup", false)):
			_fail("pools", "%s is drop-off only and in the pickup pool" % stop.id)
	for stop: Fare.Stop in dropoffs:
		if str(stop.node.get("kind", "")) == GeneratedFares.POI:
			_fail("pools", "%s is a tram stop in the destination pool" % stop.id)
	system.free()

	# Smuggle three nodes in and watch each pool refuse its own. On a
	# destination's edge: the pickup pool can be empty (Causeway Bay alone).
	var edge: int = int(dropoffs[0].node.get("nearest_edge", -1))
	var smuggled: Dictionary = _fares.duplicate(true)
	var nodes: Array = smuggled["nodes"]
	nodes.append(_node("x_dropoff", GeneratedFares.PUDO, null, edge, false, true))
	nodes.append(_node("x_tram", GeneratedFares.POI, null, edge, true, true))
	nodes.append(
		_node(
			"x_harbour", GeneratedFares.TAXI_STAND, GeneratedFares.CROSS_HARBOUR, edge, true, true
		)
	)
	var probe: FareSystem = _system(smuggled, _profile, SEED)
	_expect(
		probe.pickups().size() == pickups.size(),
		"pools",
		"mutation caught: a drop-off-only point, a tram stop and a cross-harbour stand hail nobody"
	)
	_expect(
		probe.dropoffs().size() == dropoffs.size() + 1,
		"pools",
		"mutation caught: only the drop-off-only point joins the destination pool"
	)
	probe.free()


## The reach table: who is stranded and why it costs what it costs, and that
## a seeded draw at every shipped pickup lands a destination at the bar.
func _check_reach() -> void:
	var system: FareSystem = _system(_fares, _profile, SEED)
	var pickups: Array[Fare.Stop] = system.pickups()
	var dropoffs: Array[Fare.Stop] = system.dropoffs()
	var names: PackedStringArray = []
	for stop: Fare.Stop in system.stranded:
		names.append(stop.id)
	var least: int = dropoffs.size()
	var total: int = 0
	for pickup: Fare.Stop in pickups:
		var count: int = system.reach_of(pickup)
		least = mini(least, count)
		total += count
	print(
		(
			"  reach: %d pickups reach %d destinations (least %d, mean %.1f); %d stranded [%s]; %.1f ms"
			% [
				pickups.size(),
				dropoffs.size(),
				least,
				float(total) / maxf(float(pickups.size()), 1.0),
				names.size(),
				", ".join(names),
				system.reach_ms
			]
		)
	)
	_expect(least >= 1, "reach", "every shipped pickup reaches at least one destination")
	for stop: Fare.Stop in system.stranded:
		for pickup: Fare.Stop in pickups:
			if pickup.same_as(stop):
				_fail("reach", "%s is stranded and still in the pickup pool" % stop.id)

	# Every shipped pickup draws, and what it draws is a legal route at the bar.
	var refused: int = 0
	var short: int = 0
	var router: RoadRouter = RouterScript.new(_graph, RoadRouter.Profile.legal())
	for pickup: Fare.Stop in pickups:
		var chosen: Fare.Stop = system.pick_destination(pickup)
		if chosen == null:
			refused += 1
			continue
		var route: RoadRouter.Route = router.route(pickup.edge, pickup.t, chosen.edge, chosen.t)
		if not route.found or route.distance_m < _profile.min_trip_m:
			short += 1
	_expect(refused == 0, "reach", "a seeded hail at every shipped pickup drew a destination")
	_expect(
		short == 0, "reach", "every draw is a legal route at %.0f m or more" % _profile.min_trip_m
	)
	system.free()

	# Mutation: a bar past every route strands every pickup and empties the pool.
	var unreachable: FareProfile = _profile.duplicate()
	unreachable.min_trip_m = 1.0e9
	var mutated: FareSystem = _system(_fares, unreachable, SEED)
	_expect(
		mutated.pickups().is_empty() and mutated.stranded.size() == pickups.size() + names.size(),
		"reach",
		"mutation caught: a bar past every route strands all %d pickups" % mutated.stranded.size()
	)
	mutated.free()


## Both branches of the allowance. A pure function of the profile, so the
## system is built over no nodes: no reach table to pay for.
func _check_allowance() -> void:
	var system: FareSystem = _system({"nodes": []}, _profile, SEED)
	var per_s: float = _profile.par_kph / 3.6
	_expect(
		is_equal_approx(
			system.allowance_for(Fare.Kind.SHORT_HOP, 100.0), _profile.short_hop_floor_s
		),
		"allowance",
		"100 m short hop takes the floor"
	)
	_expect(
		is_equal_approx(system.allowance_for(Fare.Kind.STANDARD, 100.0), _profile.standard_floor_s),
		"allowance",
		"100 m standard takes its own floor"
	)
	_expect(
		is_equal_approx(system.allowance_for(Fare.Kind.STANDARD, 2000.0), 2000.0 / per_s),
		"allowance",
		"2,000 m standard is priced at par (%.1f s)" % (2000.0 / per_s)
	)
	system.free()


## The state machine on synthetic samples.
func _check_loop() -> void:
	# Found with a throwaway system: every system below hails as its first
	# draw, so the same seed lands the same destination on each of them.
	var scout: FareSystem = _system(_fares, _profile, SEED)
	var pickup: Fare.Stop = _reachable_pickup(scout)
	var all_stranded: bool = scout.pickups().is_empty() and not scout.stranded.is_empty()
	scout.free()
	if pickup == null:
		# The loop is driven on the frame region; a neighbour with no pickup of
		# its own says so rather than certifying nothing (`Q72`).
		_expect(all_stranded, "loop", "SKIP: no pickup on this region alone to drive the loop from")
		return
	var system: FareSystem = _system(_fares, _profile, SEED)

	# Passing through at speed hails nobody.
	_tick(system, pickup.point, FAST, 2)
	_expect(system.state == FareSystem.State.IDLE, "loop", "driving past a stand hails nobody")

	# Stopping hails; the dwell from both sides.
	_tick(system, pickup.point, CRAWL, 1)
	_expect(system.state == FareSystem.State.BOARDING, "loop", "stopping at a stand hails")
	_expect(system.fare != null and system.fare.route_found, "loop", "the fare has a legal route")
	_expect(
		system.fare.par_m >= _profile.min_trip_m,
		"loop",
		"par %.0f m is at or beyond min_trip_m" % system.fare.par_m
	)
	_tick(system, pickup.point, CRAWL, 3)
	_expect(system.state == FareSystem.State.BOARDING, "loop", "0.75 s in, still boarding")
	_tick(system, pickup.point, CRAWL, 1)
	_expect(system.state == FareSystem.State.CARRYING, "loop", "1.0 s in, the passenger is aboard")
	_expect(
		is_equal_approx(system.fare.remaining_s, system.fare.allowance_s),
		"loop",
		"the clock starts full at %.1f s" % system.fare.allowance_s
	)
	_expect(
		is_equal_approx(system.fare.meter.reading_hkd(), _tariff.flagfall_hkd),
		"loop",
		"the meter starts at the flagfall"
	)

	# Arriving fast is not delivering; stopping is.
	var destination: Fare.Stop = system.fare.destination
	_tick(system, destination.point, FAST, 4)
	_expect(system.state == FareSystem.State.CARRYING, "loop", "arriving at speed does not deliver")
	var remaining: float = system.fare.remaining_s
	var reading: float = system.fare.meter.reading_hkd()
	_tick(system, destination.point, CRAWL, 1)
	_expect(system.state == FareSystem.State.IDLE, "loop", "stopping at the destination delivers")
	_expect(system.deliveries == 1, "loop", "deliveries counted")
	var expected_tip: float = (remaining - TICK_S) * _profile.tip_hkd_per_s
	_expect(
		is_equal_approx(system.fare.tip_hkd, expected_tip),
		"loop",
		"the tip is the seconds left times the rate (HK$%.2f)" % system.fare.tip_hkd
	)
	_expect(
		is_equal_approx(system.fare.banked_hkd, reading + expected_tip),
		"loop",
		"delivery banks the reading plus the tip (HK$%.2f)" % system.fare.banked_hkd
	)
	_expect(
		is_equal_approx(system.earned_hkd, system.fare.banked_hkd),
		"loop",
		"the session earned what the fare banked"
	)
	var banked_fast: float = system.fare.banked_hkd

	# Delivered at the same stand, the car cannot hail again until it has left.
	_tick(system, destination.point, CRAWL, 2)
	_expect(not system.armed(), "loop", "a fare cannot start where the last one ended")
	_tick(system, FAR_AWAY, FAST, 1)
	_expect(system.armed(), "loop", "leaving every stand re-arms the hail")
	system.free()

	# The same fare delivered later banks strictly less: the speed reward is live.
	var slower: FareSystem = _system(_fares, _profile, SEED)
	_tick(slower, pickup.point, CRAWL, 5)
	_expect(
		slower.state == FareSystem.State.CARRYING and slower.fare.destination.same_as(destination),
		"loop",
		"the same seed draws the same destination"
	)
	_tick(slower, destination.point, FAST, 12)
	_tick(slower, destination.point, CRAWL, 1)
	_expect(
		slower.deliveries == 1 and slower.fare.banked_hkd < banked_fast,
		"loop",
		"delivered 2 s later banks HK$%.2f against HK$%.2f" % [slower.fare.banked_hkd, banked_fast]
	)
	slower.free()

	# Mutation: a halved tip rate changes what the same drive banks.
	var stingy: FareProfile = _profile.duplicate()
	stingy.tip_hkd_per_s = _profile.tip_hkd_per_s * 0.5
	var mutated: FareSystem = _system(_fares, stingy, SEED)
	_tick(mutated, pickup.point, CRAWL, 5)
	_tick(mutated, destination.point, FAST, 4)
	_tick(mutated, destination.point, CRAWL, 1)
	_expect(
		mutated.deliveries == 1 and not is_equal_approx(mutated.fare.banked_hkd, banked_fast),
		"loop",
		"mutation caught: half the tip rate banks HK$%.2f" % mutated.fare.banked_hkd
	)
	mutated.free()

	# Leaving during boarding cancels.
	var leaver: FareSystem = _system(_fares, _profile, SEED)
	_tick(leaver, pickup.point, CRAWL, 2)
	_expect(leaver.state == FareSystem.State.BOARDING, "loop", "hailed again on a fresh system")
	_tick(leaver, FAR_AWAY, FAST, 1)
	_expect(
		leaver.state == FareSystem.State.IDLE and leaver.cancellations == 1,
		"loop",
		"driving off during boarding cancels, and is counted"
	)
	leaver.free()

	# The clock runs out: a bail banks nothing.
	var late: FareSystem = _system(_fares, _profile, SEED)
	_tick(late, pickup.point, CRAWL, 5)
	_expect(late.state == FareSystem.State.CARRYING, "loop", "carrying, to be run out")
	var allowance: float = late.fare.allowance_s
	var ticks: int = int(ceil(allowance / TICK_S))
	_tick(late, pickup.point, CRAWL, ticks - 1)
	_expect(
		late.state == FareSystem.State.CARRYING and late.fare.remaining_s > 0.0,
		"loop",
		"one tick short of the allowance, still carrying"
	)
	_tick(late, pickup.point, CRAWL, 1)
	_expect(
		late.state == FareSystem.State.IDLE and late.bails == 1,
		"loop",
		"the allowance ran out: bailed, and counted"
	)
	_expect(
		is_zero_approx(late.fare.banked_hkd) and is_zero_approx(late.earned_hkd),
		"loop",
		"a bail banks nothing"
	)
	_expect(
		late.fare.meter.reading_hkd() >= _tariff.flagfall_hkd,
		"loop",
		"the meter ran while the clock did (HK$%.1f)" % late.fare.meter.reading_hkd()
	)
	late.free()


## `ticks` samples of a car at `point` doing `speed_mps`, `TICK_S` apart.
static func _tick(system: FareSystem, point: Vector3, speed_mps: float, ticks: int) -> void:
	for tick: int in ticks:
		system.sample(point, speed_mps, Vector3.FORWARD, TICK_S)


## A system over `fares` with `profile`, the shipped tariff and a fixed draw.
## Not added to the tree: `_ready` never runs, and `setup` is the whole load.
func _system(fares: Dictionary, profile: FareProfile, seed_value: int) -> FareSystem:
	var rng := RandomNumberGenerator.new()
	rng.seed = seed_value
	var by_region: Dictionary[String, Dictionary] = {_region: fares}
	var system: FareSystem = FareSystemScript.new()
	system.setup(_graph, by_region, profile, _tariff, rng)
	return system


## The first pickup a seeded draw finds a destination for.
func _reachable_pickup(system: FareSystem) -> Fare.Stop:
	for pickup: Fare.Stop in system.pickups():
		if system.pick_destination(pickup) != null:
			return pickup
	return null


static func _node(
	id: String, kind: String, category: Variant, edge: int, pickup: bool, dropoff: bool
) -> Dictionary:
	return {
		"id": id,
		"pos": [0.0, 0.0, 0.0],
		"kind": kind,
		"stand_category": category,
		"name": {"en": id, "zh": id},
		"nearest_edge": edge,
		"edge_t": 0.5,
		"pickup": pickup,
		"dropoff": dropoff,
	}


func _expect(condition: bool, area: String, what: String) -> void:
	if condition:
		print("  %s: %s" % [area, what])
		return
	_fail(area, what)


func _fail(area: String, what: String) -> void:
	_failed += 1
	printerr("  FAIL %s: %s" % [area, what])
