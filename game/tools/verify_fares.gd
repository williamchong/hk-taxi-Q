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
const SkillProfileScript = preload("res://scripts/fares/skill_profile.gd")
const HandlingProfileScript = preload("res://scripts/vehicle/handling_profile.gd")

## ⚠️ **The paths come from the scripts the game loads, never restated here.**

## One tick that is also one graph sample at the shipped 5 Hz, and exact in
## binary so a dwell of 1.0 s is reached on the fourth tick and not the fifth.
const TICK_S: float = 0.25
## Well under the shipped `stop_below_kph` (5 kph is 1.39 m/s), and well over.
const CRAWL: float = 0.5
const FAST: float = 10.0
## A run at speed for the distance skill: 12.5 m a tick, so a 200 m unit is
## 16 ticks and exact in binary.
const RUN: float = 50.0
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
var _skills: SkillProfile = null
## `HandlingProfile.drift_slip_threshold_deg`: the one number the skills read
## from the handling table (`Q84`).
var _slip_threshold_deg: float = 0.0
## How many times `skilled` fired on the system under test.
var _skilled: int = 0
## How many times `practised` fired, and the last award it carried.
var _practised: int = 0
var _last_practice: Fare.Award = null


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
	_skills = load(SkillProfileScript.PATH) as SkillProfile
	var handling: HandlingProfile = load(HandlingProfileScript.PATH) as HandlingProfile
	if _fares.is_empty() or _profile == null or _tariff == null or _skills == null:
		printerr("  FAIL  fares, profile, tariff or skills did not load")
		quit(1)
		return
	if handling == null:
		printerr("  FAIL  %s did not load" % HandlingProfileScript.PATH)
		quit(1)
		return
	_slip_threshold_deg = handling.drift_slip_threshold_deg

	_check_tariff()
	_check_pools()
	_check_reach()
	_check_allowance()
	_check_loop()
	_check_skills()
	_check_practice()
	_check_penalties()

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
	# The pending customer a reader may point at is never the stand the car
	# is disarmed on (the user's call): a delivery at a stand that is also a
	# pickup would otherwise aim the arrow at the kerb under the car.
	var pointed: Fare.Stop = system.nearest_pending(destination.point)
	_expect(
		(
			not system.armed()
			and (pointed == null or not pointed.same_as(destination))
			and (
				pointed == null
				or (
					RoadGraph.plan_distance(destination.point, pointed.point)
					> _profile.hail_radius_m
				)
			)
		),
		"loop",
		"and the pending customer pointed at is not the stand under the car"
	)
	# Nor is it marked (the user's call): the end of a trip is not the start of
	# another, so no ring or pin on a pickup the loop would refuse right now.
	var withheld: PackedInt32Array = system.withheld_pickups(destination.point)
	# The sample that delivered also refreshed the fields the readers use, and
	# they say what the queries say from the same spot.
	_expect(
		(
			(
				(system.pending == null and pointed == null)
				or (system.pending != null and system.pending.same_as(pointed))
			)
			and system.withheld == withheld
		),
		"loop",
		"the delivering sample left `pending` and `withheld` where the queries read them"
	)
	var marked_in_reach: int = 0
	var hidden_out_of_reach: int = 0
	for index: int in system.pickups().size():
		var apart: float = RoadGraph.plan_distance(destination.point, system.pickups()[index].point)
		var in_reach: bool = apart <= _profile.hail_radius_m
		if in_reach and not withheld.has(index):
			marked_in_reach += 1
		if not in_reach and withheld.has(index):
			hidden_out_of_reach += 1
	_expect(
		marked_in_reach == 0 and hidden_out_of_reach == 0,
		"loop",
		(
			"after a delivery no pickup in reach is marked and none beyond it is hidden (%d, %d)"
			% [marked_in_reach, hidden_out_of_reach]
		)
	)
	# Arriving with nearly the whole allowance left is an early arrival
	# (`P3-49`), so the tip is the time plus that one skill.
	var expected_time: float = (remaining - TICK_S) * _profile.tip_hkd_per_s
	var expected_tip: float = expected_time + _skills.early_hkd
	_expect(
		is_equal_approx(system.fare.time_hkd, expected_time),
		"loop",
		"the time tip is the seconds left times the rate (HK$%.2f)" % system.fare.time_hkd
	)
	_expect(
		(
			system.fare.awards.size() == 1
			and system.fare.awards[0].skill == Fare.Skill.EARLY
			and is_equal_approx(system.fare.skills_hkd, _skills.early_hkd)
		),
		"loop",
		"arriving with the clock nearly full pays the early arrival, and only that"
	)
	_expect(
		is_equal_approx(system.fare.tip_hkd, expected_tip),
		"loop",
		"the tip is the time plus the skills (HK$%.2f)" % system.fare.tip_hkd
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
		(
			is_zero_approx(late.fare.banked_hkd)
			and is_zero_approx(late.earned_hkd)
			and is_zero_approx(late.fare.tip_hkd)
		),
		"loop",
		"a bail banks nothing, and tips nothing"
	)
	_expect(
		late.fare.meter.reading_hkd() >= _tariff.flagfall_hkd,
		"loop",
		"the meter ran while the clock did (HK$%.1f)" % late.fare.meter.reading_hkd()
	)
	late.free()


## The skills (`P3-49`): each dwell from both sides, a slide that ends
## forfeits its unpaid part, the early arrival on both sides of its share, a
## bail forfeits every award, and the mutations that prove each check is live.
func _check_skills() -> void:
	# A zeroed skill table is an inert system, named, never a literal.
	var zeroed: SkillProfile = _skills.duplicate()
	zeroed.drift_hkd = 0.0
	var inert: FareSystem = _system_with({"nodes": []}, _profile, zeroed, SEED)
	_expect(not inert.usable(), "skills", "mutation caught: a zero drift_hkd is an inert system")
	inert.free()
	var unhandled: FareSystem = FareSystemScript.new()
	unhandled.setup(
		_graph,
		{_region: {"nodes": []}},
		_profile,
		_tariff,
		_skills,
		0.0,
		RandomNumberGenerator.new()
	)
	_expect(not unhandled.usable(), "skills", "and so is a zero drift threshold")
	unhandled.free()

	var scout: FareSystem = _system(_fares, _profile, SEED)
	var pickup: Fare.Stop = _reachable_pickup(scout)
	var all_stranded: bool = scout.pickups().is_empty() and not scout.stranded.is_empty()
	scout.free()
	if pickup == null:
		_expect(all_stranded, "skills", "SKIP: no pickup on this region alone to drive from")
		return

	# The speed skill can never tick faster than the meter: its unit is at
	# least the tariff's (the user's call).
	_expect(
		_skills.speed_hold_m >= _tariff.step_m,
		"skills",
		(
			"speed_hold_m (%.0f m) is at least the tariff's step_m (%.0f m)"
			% [_skills.speed_hold_m, _tariff.step_m]
		)
	)

	# Aboard, out on the road, nothing earned yet — and the tip says so: the
	# seconds left are priced at the door, never live (the user's call).
	var system: FareSystem = _system(_fares, _profile, SEED)
	_skilled = 0
	system.skilled.connect(_count_skilled)
	_tick(system, pickup.point, CRAWL, 5)
	_expect(system.state == FareSystem.State.CARRYING, "skills", "carrying, to earn on")
	_expect(
		is_zero_approx(system.fare.tip_hkd) and is_zero_approx(system.fare.time_hkd),
		"skills",
		(
			"carrying with nothing earned, the live tip is 0 — the time is not in it (HK$%.2f)"
			% system.fare.tip_hkd
		)
	)
	var threshold: float = _slip_threshold_deg
	var drift_ticks: int = int(ceil(_skills.drift_min_s / TICK_S))
	var repeat_ticks: int = int(ceil(_skills.drift_s / TICK_S))
	_slide(system, FAST, threshold - 1.0, drift_ticks * 3)
	_expect(
		system.fare.awards.is_empty() and _skilled == 0,
		"skills",
		"a degree under the threshold, however long, is not a drift"
	)
	if repeat_ticks < drift_ticks:
		_slide(system, FAST, threshold, repeat_ticks)
		_slide(system, FAST, 0.0, 1)
		_expect(
			system.fare.awards.is_empty(),
			"skills",
			"a slide as long as drift_s but short of drift_min_s is a tap and pays nothing"
		)
	_slide(system, FAST, threshold, drift_ticks - 1)
	_expect(system.fare.awards.is_empty(), "skills", "one tick short of drift_min_s pays nothing")
	_slide(system, FAST, threshold, 1)
	_expect(
		(
			system.fare.awards.size() == 1
			and system.fare.awards[0].skill == Fare.Skill.DRIFT
			and is_equal_approx(system.fare.awards[0].hkd, _skills.drift_hkd)
			and is_equal_approx(system.fare.skills_hkd, _skills.drift_hkd)
			and _skilled == 1
		),
		"skills",
		"the tick that reaches drift_min_s AT the threshold pays drift_hkd into the tip, once, and says so"
	)
	_expect(
		(
			is_equal_approx(system.fare.tip_hkd, _skills.drift_hkd)
			and is_zero_approx(system.fare.time_hkd)
		),
		"skills",
		"and the live tip is the skill alone"
	)
	_expect(
		(
			is_zero_approx(FareSystem.tip_of(3.0, -5.0))
			and is_equal_approx(FareSystem.tip_of(3.0, -2.0), 1.0)
		),
		"skills",
		"a penalty docks the tip and floors it at zero, never below"
	)
	_slide(system, FAST, threshold + 20.0, repeat_ticks)
	_expect(
		system.fare.awards.size() == 2 and _skilled == 2,
		"skills",
		"held another drift_s, the same slide pays again"
	)
	_slide(system, FAST, 0.0, 1)
	_slide(system, FAST, threshold, drift_ticks - 1)
	_slide(system, FAST, 0.0, 1)
	_slide(system, FAST, threshold, drift_ticks - 1)
	_expect(
		system.fare.awards.size() == 2,
		"skills",
		"a slide that ends forfeits its unpaid dwell: two short slides are not one long one"
	)
	_slide(system, FAST, 0.0, 1)
	var tip_before: float = system.fare.tip_hkd
	_slide(system, FAST, 0.0, 8)
	_expect(
		is_equal_approx(system.fare.tip_hkd, tip_before) and tip_before > 0.0,
		"skills",
		"two seconds of clock later the live tip has not moved: it never falls with the time"
	)

	# Delivered: the time is priced at the door and the early arrival joins
	# it there, so the tip is the time plus every skill.
	var destination: Fare.Stop = system.fare.destination
	var skills_before: float = system.fare.skills_hkd
	var remaining_before: float = system.fare.remaining_s
	_tick(system, destination.point, CRAWL, 1)
	_expect(system.deliveries == 1, "skills", "delivered")
	_expect(
		(
			system.fare.awards.size() == 3
			and system.fare.awards[2].skill == Fare.Skill.EARLY
			and is_equal_approx(system.fare.skills_hkd, skills_before + _skills.early_hkd)
			and _skilled == 3
		),
		"skills",
		"the early arrival is paid at the door, last, and announced"
	)
	_expect(
		is_equal_approx(system.fare.time_hkd, (remaining_before - TICK_S) * _profile.tip_hkd_per_s),
		"skills",
		"the time is priced at the door, from the seconds left (HK$%.2f)" % system.fare.time_hkd
	)
	_expect(
		(
			is_equal_approx(system.fare.tip_hkd, system.fare.time_hkd + system.fare.skills_hkd)
			and is_equal_approx(
				system.fare.banked_hkd, system.fare.meter.reading_hkd() + system.fare.tip_hkd
			)
		),
		"skills",
		"delivery banks the meter plus the time plus the skills (HK$%.2f)" % system.fare.banked_hkd
	)
	system.free()

	# Sustained speed, on its own fare: the same shape, measured in metres.
	# `RUN` is 50 m/s so a unit is 16 ticks and exact in binary; the floor's
	# inclusiveness is asserted separately, one tick over its own unit.
	var runner: FareSystem = _system(_fares, _profile, SEED)
	_tick(runner, pickup.point, CRAWL, 5)
	var floor_mps: float = _skills.speed_min_kph / 3.6
	_expect(RUN >= floor_mps, "skills", "the test's run speed is at or over speed_min_kph")
	var speed_ticks: int = int(ceil(_skills.speed_hold_m / (RUN * TICK_S)))
	_slide(runner, floor_mps - 0.5, 0.0, speed_ticks)
	_expect(runner.fare.awards.is_empty(), "skills", "under the speed floor pays nothing")
	_slide(runner, RUN, 0.0, speed_ticks - 1)
	_expect(runner.fare.awards.is_empty(), "skills", "one tick short of speed_hold_m pays nothing")
	_slide(runner, RUN, 0.0, 1)
	_expect(
		(
			runner.fare.awards.size() == 1
			and runner.fare.awards[0].skill == Fare.Skill.SPEED
			and is_equal_approx(runner.fare.awards[0].hkd, _skills.speed_hkd)
			and is_equal_approx(runner.fare.tip_hkd, _skills.speed_hkd)
		),
		"skills",
		"the tick that reaches speed_hold_m pays speed_hkd into the live tip"
	)
	_slide(runner, RUN, 0.0, speed_ticks - 1)
	_slide(runner, floor_mps - 0.5, 0.0, 1)
	_slide(runner, RUN, 0.0, speed_ticks - 1)
	_expect(runner.fare.awards.size() == 1, "skills", "dropping under the floor restarts the run")
	_slide(runner, floor_mps - 0.5, 0.0, 1)
	var floor_ticks: int = int(ceil(_skills.speed_hold_m / (floor_mps * TICK_S)))
	_slide(runner, floor_mps, 0.0, floor_ticks + 1)
	_expect(
		runner.fare.awards.size() == 2,
		"skills",
		"AT the floor, a unit driven pays: the bar is inclusive"
	)
	_slide(runner, floor_mps - 0.5, 0.0, 1)
	var double_ticks: int = int(ceil(_skills.speed_hold_m / (2.0 * RUN * TICK_S)))
	_slide(runner, 2.0 * RUN, 0.0, double_ticks - 1)
	_expect(
		runner.fare.awards.size() == 2, "skills", "at twice the speed, one tick short pays nothing"
	)
	_slide(runner, 2.0 * RUN, 0.0, 1)
	_expect(
		runner.fare.awards.size() == 3,
		"skills",
		"and pays in half the ticks: the unit is distance driven, not time held"
	)
	_expect(
		runner.fare.count_of(Fare.Skill.SPEED) == 3 and runner.fare.count_of(Fare.Skill.DRIFT) == 0,
		"skills",
		"the receipt counts them by skill"
	)
	_tick(runner, runner.fare.destination.point, CRAWL, 1)
	_expect(
		(
			runner.deliveries == 1
			and is_equal_approx(runner.fare.tip_hkd, runner.fare.time_hkd + runner.fare.skills_hkd)
		),
		"skills",
		"delivered, the run's tip is the time plus the speed skills (HK$%.2f)" % runner.fare.tip_hkd
	)
	runner.free()

	# The early arrival from the other side: the clock run just under the
	# share pays nothing at the door.
	var late: FareSystem = _system(_fares, _profile, SEED)
	_tick(late, pickup.point, CRAWL, 5)
	var allowance: float = late.fare.allowance_s
	var run_s: float = allowance * (1.0 - _skills.early_share) + TICK_S
	_tick(late, FAR_AWAY, CRAWL, int(ceil(run_s / TICK_S)))
	_expect(late.state == FareSystem.State.CARRYING, "skills", "still carrying, under the share")
	_tick(late, late.fare.destination.point, CRAWL, 1)
	_expect(
		late.deliveries == 1 and late.fare.count_of(Fare.Skill.EARLY) == 0,
		"skills",
		"delivered with less than early_share of the clock left, no early arrival"
	)
	late.free()
	var prompt: FareSystem = _system(_fares, _profile, SEED)
	_tick(prompt, pickup.point, CRAWL, 5)
	var on_share: float = prompt.fare.allowance_s * (1.0 - _skills.early_share) - TICK_S
	_tick(prompt, FAR_AWAY, CRAWL, int(floor(on_share / TICK_S)))
	_tick(prompt, prompt.fare.destination.point, CRAWL, 1)
	_expect(
		prompt.deliveries == 1 and prompt.fare.count_of(Fare.Skill.EARLY) == 1,
		"skills",
		"and with the share still on the clock, paid"
	)
	prompt.free()

	# Air (`P3-51`): seconds with every wheel off the ground, paid at the
	# landing and only upright. Both sides of the bar, the repeat, the roll,
	# the flight that never lands, and a mid-air slip that is not a drift.
	var flier: FareSystem = _system(_fares, _profile, SEED)
	_skilled = 0
	flier.skilled.connect(_count_skilled)
	_tick(flier, pickup.point, CRAWL, 5)
	var air_ticks: int = int(ceil(_skills.air_min_s / TICK_S))
	var air_repeat_ticks: int = int(ceil(_skills.air_s / TICK_S))
	_fly(flier, FAST, air_ticks - 1, true, true)
	_fly(flier, FAST, 1, false, true)
	_expect(
		flier.fare.awards.is_empty(),
		"skills",
		"one tick short of air_min_s pays nothing at the landing"
	)
	_fly(flier, FAST, air_ticks, true, true)
	_expect(flier.fare.awards.is_empty(), "skills", "in the air, nothing has paid yet")
	_fly(flier, FAST, 1, false, true)
	_expect(
		(
			flier.fare.awards.size() == 1
			and flier.fare.awards[0].skill == Fare.Skill.AIR
			and is_equal_approx(flier.fare.awards[0].hkd, _skills.air_hkd)
			and is_equal_approx(flier.fare.tip_hkd, _skills.air_hkd)
			and _skilled == 1
		),
		"skills",
		"the landing after air_min_s in the air pays air_hkd into the live tip, once, and says so"
	)
	_fly(flier, FAST, air_ticks + air_repeat_ticks, true, true)
	_fly(flier, FAST, 1, false, true)
	_expect(
		flier.fare.count_of(Fare.Skill.AIR) == 3 and _skilled == 3,
		"skills",
		"held another air_s, the landing pays twice: the repeat is the flight's length"
	)
	_fly(flier, FAST, air_ticks, true, true)
	_fly(flier, FAST, 1, false, false)
	_expect(
		flier.fare.count_of(Fare.Skill.AIR) == 3,
		"skills",
		"a flight that lands on its roof pays nothing"
	)
	_fly(flier, FAST, 1, false, true)
	_expect(
		flier.fare.count_of(Fare.Skill.AIR) == 3,
		"skills",
		"and righting afterwards does not pay it late: the landing tick decided"
	)
	_fly(flier, FAST, 1, true, true)
	_fly(flier, FAST, air_ticks, true, false)
	_fly(flier, FAST, 1, false, true)
	_expect(
		flier.fare.count_of(Fare.Skill.AIR) == 4,
		"skills",
		"rolling in the air is nothing; upright at the landing is what is asked"
	)
	_slide(flier, FAST, 0.0, 1)
	var drifts_before: int = flier.fare.count_of(Fare.Skill.DRIFT)
	for _tick_index: int in drift_ticks * 2:
		flier.sample(FAR_AWAY, FAST, Vector3.FORWARD, TICK_S, threshold + 20.0, true, true)
	_fly(flier, FAST, 1, false, true)
	_expect(
		flier.fare.count_of(Fare.Skill.DRIFT) == drifts_before,
		"skills",
		"a car yawing in the air reads a slip angle and is not drifting"
	)
	flier.free()
	var faller: FareSystem = _system(_fares, _profile, SEED)
	_tick(faller, pickup.point, CRAWL, 5)
	var fall_ticks: int = int(ceil(faller.fare.remaining_s / TICK_S)) + 1
	_fly(faller, FAST, fall_ticks, true, true)
	_expect(
		faller.bails == 1 and faller.fare.count_of(Fare.Skill.AIR) == 0,
		"skills",
		"a flight that never lands pays nothing, however long"
	)
	faller.free()
	var unpaid_air: SkillProfile = _skills.duplicate()
	unpaid_air.air_hkd = 0.0
	var no_air: FareSystem = _system_with({"nodes": []}, _profile, unpaid_air, SEED)
	_expect(not no_air.usable(), "skills", "mutation caught: a zero air_hkd is an inert system")
	no_air.free()
	var jumped: FareSystem = _system(_fares, _profile, SEED)
	_air_drive(jumped, pickup, air_ticks, air_repeat_ticks)
	var stingy_air: SkillProfile = _skills.duplicate()
	stingy_air.air_hkd = _skills.air_hkd * 0.5
	var cheap_jump: FareSystem = _system_with(_fares, _profile, stingy_air, SEED)
	_air_drive(cheap_jump, pickup, air_ticks, air_repeat_ticks)
	_expect(
		(
			jumped.deliveries == 1
			and cheap_jump.deliveries == 1
			and jumped.fare.count_of(Fare.Skill.AIR) == 3
			and cheap_jump.fare.banked_hkd < jumped.fare.banked_hkd
		),
		"skills",
		(
			"mutation caught: half the air price banks HK$%.2f against HK$%.2f"
			% [cheap_jump.fare.banked_hkd, jumped.fare.banked_hkd]
		)
	)
	jumped.free()
	cheap_jump.free()

	# A bail forfeits every skill already paid: the receipt keeps them, the
	# money does not.
	var bailer: FareSystem = _system(_fares, _profile, SEED)
	_tick(bailer, pickup.point, CRAWL, 5)
	_slide(bailer, FAST, threshold, drift_ticks)
	_expect(bailer.fare.awards.size() == 1, "skills", "a drift paid before the bail")
	var ticks: int = int(ceil(bailer.fare.remaining_s / TICK_S)) + 1
	_tick(bailer, FAR_AWAY, CRAWL, ticks)
	_expect(
		(
			bailer.bails == 1
			and bailer.fare.awards.size() == 1
			and is_equal_approx(bailer.fare.skills_hkd, _skills.drift_hkd)
			and is_zero_approx(bailer.fare.tip_hkd)
			and is_zero_approx(bailer.fare.banked_hkd)
		),
		"skills",
		"the bail keeps the award on the receipt and pays none of it"
	)
	bailer.free()

	# Mutation: half the drift price banks strictly less on the same drive —
	# one drive, `_drift_drive`, on the shipped table and on the halved one.
	var priced: FareSystem = _system(_fares, _profile, SEED)
	_drift_drive(priced, pickup, threshold, drift_ticks, repeat_ticks)
	var stingy: SkillProfile = _skills.duplicate()
	stingy.drift_hkd = _skills.drift_hkd * 0.5
	var mutated: FareSystem = _system_with(_fares, _profile, stingy, SEED)
	_drift_drive(mutated, pickup, threshold, drift_ticks, repeat_ticks)
	_expect(
		(
			priced.deliveries == 1
			and mutated.deliveries == 1
			and mutated.fare.banked_hkd < priced.fare.banked_hkd
		),
		"skills",
		(
			"mutation caught: half the drift price banks HK$%.2f against HK$%.2f"
			% [mutated.fare.banked_hkd, priced.fare.banked_hkd]
		)
	)
	priced.free()
	mutated.free()


## Practice (the user's call, 2026-09-26): the skills run with no passenger
## aboard, shown on `practised` and counted, never paid — no fare, no tip, no
## bank — and a slide held into the boarding is not the passenger's.
func _check_practice() -> void:
	var scout: FareSystem = _system(_fares, _profile, SEED)
	var pickup: Fare.Stop = _reachable_pickup(scout)
	var all_stranded: bool = scout.pickups().is_empty() and not scout.stranded.is_empty()
	scout.free()
	if pickup == null:
		_expect(all_stranded, "practice", "SKIP: no pickup on this region alone to drive from")
		return

	var system: FareSystem = _system(_fares, _profile, SEED)
	_skilled = 0
	_practised = 0
	_last_practice = null
	system.skilled.connect(_count_skilled)
	system.practised.connect(_count_practised)
	var threshold: float = _slip_threshold_deg
	var drift_ticks: int = int(ceil(_skills.drift_min_s / TICK_S))
	_expect(system.state == FareSystem.State.IDLE, "practice", "empty, far from every stop")
	_slide(system, FAST, threshold, drift_ticks - 1)
	_expect(_practised == 0, "practice", "one tick short of drift_min_s shows nothing, empty too")
	_slide(system, FAST, threshold, 1)
	_expect(
		(
			_practised == 1
			and _last_practice != null
			and _last_practice.skill == Fare.Skill.DRIFT
			and system.skill_counts[Fare.Skill.DRIFT] == 1
			and _skilled == 0
		),
		"practice",
		"the tick that reaches it is shown on `practised` and counted, never on `skilled`"
	)
	_expect(
		system.fare == null and is_zero_approx(system.earned_hkd),
		"practice",
		"and nothing is paid: no fare, nothing banked"
	)
	_hit(system, _skills.crash_min_kph)
	_expect(
		(
			_practised == 2
			and _last_practice.skill == Fare.Skill.CRASH
			and is_zero_approx(system.earned_hkd)
		),
		"practice",
		"a crash taken empty is shown as one and docks nothing"
	)

	# A slide held from the kerb through the boarding, one tick short of the
	# bar as the car reaches the stand: what it pays before the passenger is
	# aboard — at the hail, and again while boarding — is practice, and the
	# passenger's own dwell starts at zero, since the tracker is reset at
	# boarding.
	_slide(system, FAST, threshold, drift_ticks - 1)
	var shown_before: int = _practised
	for tick: int in 5:
		system.sample(pickup.point, CRAWL, Vector3.FORWARD, TICK_S, threshold)
	_expect(system.state == FareSystem.State.CARRYING, "practice", "boarded while sliding")
	_expect(
		_practised > shown_before and _skilled == 0 and system.fare.awards.is_empty(),
		"practice",
		"the slide held through the boarding was shown, and put nothing on the fare"
	)
	_slide(system, FAST, threshold, drift_ticks - 1)
	_expect(
		system.fare.awards.is_empty() and _skilled == 0,
		"practice",
		"mutation caught: aboard, the passenger's drift starts from zero — one tick short pays nothing"
	)
	_slide(system, FAST, threshold, 1)
	_expect(
		_skilled == 1 and system.fare.awards.size() == 1,
		"practice",
		"and the tick that reaches drift_min_s from the boarding pays the passenger"
	)
	# Every practice event but the crash was a drift, plus the one paid.
	_expect(
		(
			system.skill_counts[Fare.Skill.DRIFT] == _practised
			and system.skill_counts[Fare.Skill.CRASH] == 1
		),
		"practice",
		"the session's count holds every drift, practised and paid alike, and the empty crash"
	)
	system.free()


## The penalties (`P3-50`, `Q148`): the tiers on the speed into the wall from
## both sides of each bar, one wall one dock, the touch that ends a slide,
## the tip floored and the meter untouched, and the table's mutations.
func _check_penalties() -> void:
	var zeroed: SkillProfile = _skills.duplicate()
	zeroed.crash_hkd = 0.0
	var inert: FareSystem = _system_with({"nodes": []}, _profile, zeroed, SEED)
	_expect(not inert.usable(), "penalty", "mutation caught: a zero crash_hkd is an inert system")
	inert.free()
	var folded: SkillProfile = _skills.duplicate()
	folded.crash_min_kph = folded.bump_min_kph
	var flat: FareSystem = _system_with({"nodes": []}, _profile, folded, SEED)
	_expect(not flat.usable(), "penalty", "and so is a crash bar that is not over the bump bar")
	flat.free()

	var scout: FareSystem = _system(_fares, _profile, SEED)
	var pickup: Fare.Stop = _reachable_pickup(scout)
	var all_stranded: bool = scout.pickups().is_empty() and not scout.stranded.is_empty()
	scout.free()
	if pickup == null:
		_expect(all_stranded, "penalty", "SKIP: no pickup on this region alone to drive from")
		return

	var system: FareSystem = _system(_fares, _profile, SEED)
	_skilled = 0
	system.skilled.connect(_count_skilled)
	_tick(system, pickup.point, CRAWL, 5)
	var threshold: float = _slip_threshold_deg
	var drift_ticks: int = int(ceil(_skills.drift_min_s / TICK_S))
	var cool_ticks: int = int(ceil(_skills.crash_cool_s / TICK_S))
	_slide(system, FAST, threshold, drift_ticks)
	_slide(system, FAST, 0.0, 1)
	var live: float = system.fare.tip_hkd
	_expect(is_equal_approx(live, _skills.drift_hkd), "penalty", "a drift in the tip to dock")

	_hit(system, _skills.bump_min_kph - 1.0)
	_expect(
		system.fare.awards.size() == 1 and is_equal_approx(system.fare.tip_hkd, live),
		"penalty",
		"a kph under bump_min_kph is a touch: nothing docked, nothing said"
	)
	_hit(system, _skills.bump_min_kph)
	_expect(
		(
			system.fare.awards.size() == 2
			and system.fare.awards[1].skill == Fare.Skill.BUMP
			and is_equal_approx(system.fare.awards[1].hkd, -_skills.bump_hkd)
			and is_equal_approx(system.fare.tip_hkd, live - _skills.bump_hkd)
			and _skilled == 2
		),
		"penalty",
		"AT bump_min_kph a collision docks bump_hkd from the live tip and is announced"
	)
	_hit(system, _skills.crash_min_kph)
	_expect(
		system.fare.awards.size() == 2,
		"penalty",
		"a crash on the next tick is the same wall: inside crash_cool_s nothing more is docked"
	)
	# The ignored hit was a tick of the window too: one short is cool_ticks
	# minus that tick, minus this probe.
	_tick(system, FAR_AWAY, FAST, cool_ticks - 3)
	_hit(system, _skills.crash_min_kph)
	_expect(system.fare.awards.size() == 2, "penalty", "one tick short of crash_cool_s, still")
	_hit(system, _skills.crash_min_kph - 1.0)
	_expect(
		(
			system.fare.awards.size() == 3
			and system.fare.awards[2].skill == Fare.Skill.BUMP
			and is_equal_approx(system.fare.tip_hkd, live - 2.0 * _skills.bump_hkd)
		),
		"penalty",
		"the tick that reaches crash_cool_s docks again, and a kph under crash_min_kph is a bump"
	)
	_tick(system, FAR_AWAY, FAST, cool_ticks - 1)
	_hit(system, _skills.crash_min_kph)
	var owed: float = _skills.drift_hkd - 2.0 * _skills.bump_hkd - _skills.crash_hkd
	_expect(
		(
			system.fare.awards.size() == 4
			and system.fare.awards[3].skill == Fare.Skill.CRASH
			and is_equal_approx(system.fare.awards[3].hkd, -_skills.crash_hkd)
			and is_equal_approx(system.fare.skills_hkd, owed)
			and is_equal_approx(system.fare.tip_hkd, FareSystem.tip_of(0.0, owed))
			and system.fare.count_of(Fare.Skill.CRASH) == 1
		),
		"penalty",
		(
			"AT crash_min_kph a crash docks crash_hkd; the skills owe HK$%.1f and the tip floors at %.1f"
			% [owed, system.fare.tip_hkd]
		)
	)
	var reading: float = system.fare.meter.reading_hkd()
	_tick(system, FAR_AWAY, FAST, 1)
	_expect(
		system.fare.meter.reading_hkd() >= reading, "penalty", "the meter is never docked (`Q141`)"
	)

	# A touch ends a slide: the dwell restarts from the contact.
	_tick(system, FAR_AWAY, FAST, cool_ticks)
	var before: int = system.fare.awards.size()
	_slide(system, FAST, threshold, drift_ticks - 1)
	system.sample(FAR_AWAY, FAST, Vector3.FORWARD, TICK_S, threshold, false, true, 1.0)
	_slide(system, FAST, threshold, drift_ticks - 1)
	_expect(
		system.fare.awards.size() == before,
		"penalty",
		"a touch mid-slide ends the slide: drift_min_s counts again from the contact"
	)
	_slide(system, FAST, threshold, 1)
	_expect(
		(
			system.fare.awards.size() == before + 1
			and system.fare.awards[before].skill == Fare.Skill.DRIFT
		),
		"penalty",
		"and the slide after it pays on its own dwell"
	)

	# Delivered: the time joins the skills at the door, so a debt that
	# emptied the live tip comes off the time rather than the meter.
	var skills_owed: float = system.fare.skills_hkd
	_tick(system, system.fare.destination.point, CRAWL, 1)
	_expect(system.deliveries == 1, "penalty", "delivered")
	_expect(
		(
			is_equal_approx(
				system.fare.tip_hkd, FareSystem.tip_of(system.fare.time_hkd, system.fare.skills_hkd)
			)
			and system.fare.skills_hkd <= skills_owed + _skills.early_hkd + 1e-6
			and is_equal_approx(
				system.fare.banked_hkd, system.fare.meter.reading_hkd() + system.fare.tip_hkd
			)
		),
		"penalty",
		(
			"at the door the tip is the time plus the skills, floored, over the whole meter (HK$%.2f)"
			% system.fare.banked_hkd
		)
	)
	system.free()

	# Half the price docks less on the same drive.
	var cheaper: SkillProfile = _skills.duplicate()
	cheaper.crash_hkd = _skills.crash_hkd * 0.5
	var priced: FareSystem = _system(_fares, _profile, SEED)
	var lenient: FareSystem = _system_with(_fares, _profile, cheaper, SEED)
	for each: FareSystem in [priced, lenient]:
		_tick(each, pickup.point, CRAWL, 5)
		_slide(each, FAST, threshold, drift_ticks)
		_slide(each, FAST, 0.0, 1)
		_hit(each, _skills.crash_min_kph)
	_expect(
		lenient.fare.skills_hkd > priced.fare.skills_hkd,
		"penalty",
		"mutation caught: half the crash price docks less"
	)
	priced.free()
	lenient.free()


func _count_skilled(_fare: Fare, _award: Fare.Award) -> void:
	_skilled += 1


func _count_practised(award: Fare.Award) -> void:
	_practised += 1
	_last_practice = award


## One sample far from every stop with a wall hit of `impact_kph` into it.
static func _hit(system: FareSystem, impact_kph: float) -> void:
	system.sample(FAR_AWAY, FAST, Vector3.FORWARD, TICK_S, 0.0, false, true, impact_kph / 3.6)


## `ticks` samples of a car at `point` doing `speed_mps`, `TICK_S` apart.
static func _tick(system: FareSystem, point: Vector3, speed_mps: float, ticks: int) -> void:
	for tick: int in ticks:
		system.sample(point, speed_mps, Vector3.FORWARD, TICK_S)


## `ticks` samples of a car far from every stop doing `speed_mps` with
## `slip_deg` between its nose and its travel, `TICK_S` apart.
static func _slide(system: FareSystem, speed_mps: float, slip_deg: float, ticks: int) -> void:
	for tick: int in ticks:
		system.sample(FAR_AWAY, speed_mps, Vector3.FORWARD, TICK_S, slip_deg)


## `ticks` samples with every wheel off the ground (`airborne`) or back on
## it, `upright` or on the roof, going nowhere that hails.
static func _fly(
	system: FareSystem, speed_mps: float, ticks: int, airborne: bool, upright: bool
) -> void:
	for tick: int in ticks:
		system.sample(FAR_AWAY, speed_mps, Vector3.FORWARD, TICK_S, 0.0, airborne, upright)


## One fare from `pickup`, driven the same way every time: a jump that pays
## once, one that pays twice, a hop that pays nothing, then straight to the
## door. Two systems given this drive differ only by their tables.
static func _air_drive(
	system: FareSystem, pickup: Fare.Stop, air_ticks: int, air_repeat_ticks: int
) -> void:
	_tick(system, pickup.point, CRAWL, 5)
	_fly(system, FAST, air_ticks, true, true)
	_fly(system, FAST, 1, false, true)
	_fly(system, FAST, air_ticks + air_repeat_ticks, true, true)
	_fly(system, FAST, 1, false, true)
	_fly(system, FAST, air_ticks - 1, true, true)
	_fly(system, FAST, 1, false, true)
	_tick(system, system.fare.destination.point, CRAWL, 1)


## One fare from `pickup`, driven the same way every time: a slide that pays
## twice, a tap that pays nothing, then straight to the door. Two systems
## given this drive differ only by their tables.
static func _drift_drive(
	system: FareSystem, pickup: Fare.Stop, threshold: float, drift_ticks: int, repeat_ticks: int
) -> void:
	_tick(system, pickup.point, CRAWL, 5)
	_slide(system, FAST, threshold, drift_ticks)
	_slide(system, FAST, threshold + 20.0, repeat_ticks)
	_slide(system, FAST, 0.0, 1)
	_slide(system, FAST, threshold, drift_ticks - 1)
	_slide(system, FAST, 0.0, 1)
	_tick(system, system.fare.destination.point, CRAWL, 1)


## A system over `fares` with `profile`, the shipped tariff and skills, and a
## fixed draw. Not added to the tree: `_ready` never runs, and `setup` is the
## whole load.
func _system(fares: Dictionary, profile: FareProfile, seed_value: int) -> FareSystem:
	return _system_with(fares, profile, _skills, seed_value)


func _system_with(
	fares: Dictionary, profile: FareProfile, skills: SkillProfile, seed_value: int
) -> FareSystem:
	var rng := RandomNumberGenerator.new()
	rng.seed = seed_value
	var by_region: Dictionary[String, Dictionary] = {_region: fares}
	var system: FareSystem = FareSystemScript.new()
	system.setup(_graph, by_region, profile, _tariff, skills, _slip_threshold_deg, rng)
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
