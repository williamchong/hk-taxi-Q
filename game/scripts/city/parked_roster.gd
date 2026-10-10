## Which parked vehicles stand at an hour (`P3-73`, `Q161`) — the arithmetic
## `parked_layer.gd` places by and `verify_parked.gd` grades, with no node in
## it so the tool can drive it without a city.
##
## A placement carries `hours`, `[from_h, to_h]` on a 24 h clock wrapping past
## midnight or null for always, and a `chance`, the share of visits it is
## found. The hour is the lighting rig's `time_of_day` (`Q160`) read against
## `ParkedProfile`'s clock — never a second clock — and a chance is drawn on a
## hash of the placement and the roll, so two reads of one roll agree and the
## next roll is a different street.
##
## ⚠️ `in_window` restates `pipeline/parked.py::in_window`; the ETL writes the
## windows and this reads them, and the two are held to each other by
## `verify_parked.gd`'s table of hours.
extends RefCounted


## The clock reading for the rig's `time_of_day`, on a 24 h clock.
static func hour_of(time_of_day: float, start_h: float, end_h: float) -> float:
	var hour: float = start_h + clampf(time_of_day, 0.0, 1.0) * (end_h - start_h)
	return fposmod(hour, 24.0)


## Whether `hour` falls in `[from_h, to_h)`, wrapping past midnight. An empty
## window is always.
static func in_window(hour: float, hours: Array) -> bool:
	if hours.size() != 2:
		return true
	var low: float = float(hours[0])
	var high: float = float(hours[1])
	if low < high:
		return low <= hour and hour < high
	return hour >= low or hour < high


## The draw for one placement on one roll, in [0, 1): a hash, so it is the
## same every time it is asked and different on the next roll.
static func draw(index: int, roll: int) -> float:
	var mixed: int = hash(Vector2i(index, roll))
	return float(absi(mixed) % 100000) / 100000.0


## Whether placement `index`, with `hours` and `chance`, stands at `hour` on
## this `roll`.
static func present(index: int, hours: Array, chance: float, hour: float, roll: int) -> bool:
	if not in_window(hour, hours):
		return false
	if chance >= 1.0:
		return true
	return draw(index, roll) < chance


## The plan cell a point falls in.
static func cell_of(at: Vector3, cell_m: float) -> Vector2i:
	return Vector2i(floori(at.x / cell_m), floori(at.z / cell_m))


## The centre of a cell's box, on the ground.
static func cell_centre(cell: Vector2i, cell_m: float) -> Vector3:
	return Vector3((cell.x + 0.5) * cell_m, 0.0, (cell.y + 0.5) * cell_m)
