## What a tick of the traffic costs by the size of its fleet (`P3-3c`, `Q219`).
##
## A desk drive's `--perf-log` reads one fleet's tick 3.3 ms on one run and 5.2
## on the next: the frame rate, and with it the core the tick lands on, moves
## with what is drawn. This steps `TrafficSystem` by hand with nothing drawn and
## no camera — every car at its full rate, as the seeded drives are — and times
## the steps alone, so two builds are compared on one footing.
##
##     godot --headless --path game --script res://tools/bench_traffic.gd -- \
##         --region=wan_chai --cars=40,80,160 [--ticks=3000] [--view=on] [--parts=on]
##
## A measurement, never a gate: it prints, and exits 1 only where it could not
## run. No trams stand (the cars' look at them is not timed). `--view=on` stands
## a camera at the fleet's centre looking north, so the camera's rules
## (`Q214`) and the far cars' thinned rules (`Q219`) are what is timed.
## `--parts=on` prints `PerfClock`'s parts of the tick after each fleet, the
## fill included; the clock's own calls are then in the time.
extends "res://tools/verify_tool.gd"

const TrafficScript = preload("res://scripts/traffic/traffic_system.gd")
const ParkedLayerScript = preload("res://scripts/city/parked_layer.gd")
const GeneratedRegions = preload("res://scripts/city/generated_regions.gd")

const TICK_S: float = 1.0 / 60.0
const SEED: int = 7
const PEAK_HOUR: float = 18.0
## Ticks stepped before the clock starts, while the ring fills.
const FILL_TICKS: int = 1200
const DEFAULT_TICKS: int = 3000
const DEFAULT_CARS: String = "40,80,160"
## The camera's height over the fleet's centre under `--view=on`.
const EYE_M: float = 2.0


func _init() -> void:
	_run.call_deferred()
	_start_watchdog.call_deferred("bench_traffic", 600.0)


func _run() -> void:
	var asked: String = Cmdline.value("--cars=")
	var fleets: PackedStringArray = (DEFAULT_CARS if asked.is_empty() else asked).split(",", false)
	asked = Cmdline.value("--ticks=")
	var ticks: int = DEFAULT_TICKS if asked.is_empty() else int(asked)
	var viewed: bool = Cmdline.value("--view=") == "on"
	var parts: bool = Cmdline.value("--parts=") == "on"
	var table := load(TrafficProfile.PATH) as TrafficProfile
	var graph: RoadGraph = RoadGraph.shared()
	if table == null or graph.is_empty() or ticks <= 0 or fleets.is_empty():
		_fail("bench", "a table, a resident road graph, --ticks and --cars")
		_finish("bench_traffic")
		return
	var layers: Array[Node] = []
	for region: String in GeneratedRegions.resident():
		var holder := Node3D.new()
		holder.position = graph.region_offset(region)
		var layer: Node3D = ParkedLayerScript.new()
		layer.region = region
		holder.add_child(layer)
		root.add_child(holder)
		layers.append(layer)
	print("  cars  live  ms a tick  us a live car   (%d ticks after %d)" % [ticks, FILL_TICKS])
	for fleet: String in fleets:
		var sized: TrafficProfile = table.duplicate()
		sized.cars = int(fleet)
		var system: TrafficSystem = TrafficScript.new()
		system.hour_override = PEAK_HOUR
		if not system.setup(graph, sized, SEED):
			_fail("bench", "no traffic at %s cars" % fleet)
			system.free()
			continue
		root.add_child(system)
		system.set_physics_process(false)
		system.read_parked(layers)
		var sum := Vector3.ZERO
		for junction: SignalPlan.Junction in system.signals.plan.junctions:
			sum += junction.position
		system.centre = sum / maxi(system.signals.plan.junctions.size(), 1)
		var camera: Camera3D = null
		if viewed:
			camera = Camera3D.new()
			root.add_child(camera)
			camera.global_position = system.centre + Vector3.UP * EYE_M
			camera.make_current()
		PerfClock.enabled = parts
		for _tick: int in FILL_TICKS:
			system.step(TICK_S)
		var live: int = 0
		var usec: int = 0
		for _tick: int in ticks:
			var began: int = Time.get_ticks_usec()
			system.step(TICK_S)
			usec += Time.get_ticks_usec() - began
			live += system.cars.reduce(
				func(count: int, car: TrafficSystem.Car) -> int: return count + int(car.live), 0
			)
		print(
			(
				"  %4s  %4.0f  %9.3f  %13.1f"
				% [
					fleet,
					float(live) / ticks,
					float(usec) / ticks / 1000.0,
					float(usec) / maxi(live, 1)
				]
			)
		)
		for line: String in PerfClock.part_lines():
			print("        ", line)
		PerfClock.reset()
		if camera != null:
			camera.free()
		system.free()
	_finish("bench_traffic")
