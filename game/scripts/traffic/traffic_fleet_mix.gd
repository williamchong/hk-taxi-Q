class_name TrafficFleetMix
extends RefCounted
## What the wandering fleet is made of (`Q183`, `Q186`): each kind's weight this
## hour, how many cars the hour runs, and the kind and taxi licence a car wears
## for each spawn. Owned by `TrafficSystem`, which keeps the batches the kinds
## are drawn in.
##
## 🔴 **`kind_for`, `licence_of` and `for_hire_of` draw off a car's id and lives,
## never the traffic's seeded RNG**: one more roll there would move every later car.

## The table the hours and the taxi are read off; `TrafficSystem.setup` sets it.
var profile: TrafficProfile
## Each resident region's taxi licences (`Q183`), mesh name to share, off its
## `CityManifest`; read at `setup` unless a verify tool set it first.
var licence_mixes: Dictionary[String, Dictionary] = {}
## Each kind's weight this hour, what the system's pick and `kind_for` draw on.
var weights: PackedFloat32Array = []

var _weight_total: float = 0.0
## Each kind's weight by clock hour, all zeros for a kind only a licence or a
## route wears.
var _hourly: Array[PackedFloat32Array] = []
## Whether each kind is one the hours draw a wandering car as.
var _wandering: Array[bool] = []
## The hour `weights` was read for, and the wandering fleet's size in it.
var _weights_hour: int = -1
var _fleet_now: int = 0


## One more kind, at its weight by clock hour.
func add_kind(by_hour: PackedFloat32Array) -> void:
	_hourly.append(by_hour)
	_wandering.append(not by_hour.is_empty() and Array(by_hour).max() > 0.0)
	weights.append(0.0)


## Whether the hours ever draw a wandering car as `kind`.
func wanders(kind: int) -> bool:
	return _wandering[kind]


## Read this hour's kind weights and fleet size when the hour has moved.
func read_hour(hour: int) -> void:
	if hour == _weights_hour:
		return
	_weights_hour = hour
	_weight_total = 0.0
	for kind: int in weights.size():
		weights[kind] = _hourly[kind][hour] if _wandering[kind] else 0.0
		_weight_total += weights[kind]
	_fleet_now = clampi(roundi(profile.cars * profile.fleet_by_hour[hour]), 0, profile.cars)


## The wandering fleet's size this hour (`Q186`).
func fleet_now() -> int:
	return _fleet_now


## The kind a wandering car is drawn as for its `lives`th spawn (`Q186`): a draw
## on this hour's weights off its id and lives, never the seeded RNG — one more
## roll there would move every later car, as a taxi's licence would (`Q183`).
func kind_for(id: int, lives: int) -> int:
	var draw: float = fposmod(float(id) * 0.267949 + float(lives) * 0.414214, 1.0) * _weight_total
	for kind: int in weights.size():
		draw -= weights[kind]
		if draw < 0.0:
			return kind
	return _pick_last()


## The last kind with any weight this hour: where a float's slack runs a draw out.
func _pick_last() -> int:
	for kind: int in range(weights.size() - 1, -1, -1):
		if weights[kind] > 0.0:
			return kind
	return 0


## The licence a taxi wears for its `lives`th spawn in `region` (`Q183`): a draw
## on the region's mix off the car's id and lives, never the seeded RNG, which
## would move every later car. The profile's taxi where the region has no mix.
func licence_of(region: String, id: int, lives: int) -> String:
	var mix: Dictionary = licence_mixes.get(region, {})
	var total: float = 0.0
	for share: float in mix.values():
		total += share
	if total <= 0.0:
		return profile.taxi_kind
	var draw: float = fposmod(float(id) * 0.618034 + float(lives) * 0.754878, 1.0) * total
	var meshes: Array = mix.keys()
	meshes.sort()
	for mesh: String in meshes:
		draw -= float(mix[mesh])
		if draw < 0.0:
			return mesh
	return meshes[-1]


## Whether a taxi's `lives`th spawn is for hire, on the same terms as its licence.
func for_hire_of(id: int, lives: int) -> bool:
	return fposmod(float(id) * 0.381966 + float(lives) * 0.569840, 1.0) < profile.taxi_for_hire
