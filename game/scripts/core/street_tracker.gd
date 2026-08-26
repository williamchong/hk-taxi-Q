class_name StreetTracker
extends RefCounted
## Which street the plate should say you are on (`P3-24`).
##
## The policy half of the HUD, and pure on purpose: no `Node`, no `RoadGraph`,
## no `Label`, per the `scripts/core/` rule in docs/ARCHITECTURE.md. It takes a
## sample — an edge id and its two names — and returns what to display, so
## `tools/verify_hud.gd` can assert the whole behaviour headlessly with no
## scene, no car and no built city.
##
## **The naive version is one line and it is wrong in three ways.** Writing
## `label.text = graph.nearest_edge(car.position).road_name_en` gives you:
##
##   * a plate that **strobes at every junction**. Two roads meet, the nearest
##     edge alternates between them across a few metres, and the name flickers
##     several times a second at exactly the moment the player is deciding where
##     to turn.
##   * a plate that **blanks on 74 of the region's 797 edges**, which publish no
##     name at all. A street does not stop existing because the graph has
##     nothing to call the slip road you clipped.
##   * a plate that is **confidently wrong** and says so in the same typeface it
##     is right in. Nothing catches this. There is no published ground truth for
##     "which street is the car on" to grade against — `Q62`'s problem at a
##     fourth layer.
##
## So: a change of street must be **earned** by a dwell, an unnamed sample is
## not evidence of anything, and the tracker counts its own changes so a drive
## can report `changes` against streets-actually-driven instead of a shrug.
## `CityStreamer`'s hysteresis is the same idea against the same failure — a
## boundary that a moving thing sits exactly on.

## How long a different street must stay nearest before the plate follows it.
##
## Not a distance. A dwell in metres is speed-invariant and sounds more
## principled, but the artefact being suppressed is **visual** — a name changing
## faster than it can be read — and that is a property of seconds. At 50 kph
## this is ~8 m, comfortably inside a junction mouth and well short of the
## region's ~50-150 m blocks.
const DEFAULT_DWELL_S: float = 0.6

## The street being displayed. Empty only before the first named sample.
var street_en: String = ""
var street_zh: String = ""
## The edge `street_en` came from, or -1 before the first named sample. Carried
## so a caller can tell "still the same road" from "a different road with the
## same name" — Hennessy Road is 40-odd edges and the plate must not blink
## between them.
var edge_id: int = -1

## How many times the displayed street has actually changed. **The counter that
## can see this fail.** A plate that names the wrong road renders exactly as
## well as one that names the right road, so what ships beside it is the number
## a drive can be checked against: 12 streets driven and 47 changes is a
## stabiliser that is not stabilising, and it is visible in a log rather than
## needing someone to notice a flicker.
var changes: int = 0

var _dwell_s: float = DEFAULT_DWELL_S
# The candidate currently serving its dwell, and how long it has served. Held
# separately from the displayed street so that a candidate which loses its
# nearest-ness before the dwell elapses simply expires, having changed nothing.
#
# ⚠️ Only the id and the clock: a name is a property of its edge, so at the
# moment of adoption the sample in hand already carries the right one. Caching
# the names here would be state that can go stale against its own id.
var _pending_edge: int = -1
var _pending_s: float = 0.0


func _init(dwell_s: float = DEFAULT_DWELL_S) -> void:
	_dwell_s = dwell_s


## Feed one sample of what the graph says is under the car.
##
## `id` is -1 for a miss — no edge within the search radius — and `en`/`zh` are
## empty for an edge the source did not name. **Both are treated the same way,
## and that is the point**: neither is evidence about which street the player is
## on, so neither may disturb what the plate says, and neither may advance a
## pending candidate's dwell. Driving off the end of the world leaves the last
## street standing, which is the honest answer to "where am I" right up until a
## different one is known.
##
## ⚠️ **An unnamed sample does not reset the pending candidate either.** A
## junction interleaves samples of two named roads with samples of the unnamed
## cap between them; resetting on those would mean a dwell could never be served
## at the exact place this exists to survive.
func sample(id: int, en: String, zh: String, delta_s: float) -> void:
	if id < 0 or en.is_empty():
		return

	# The same edge we are already showing: nothing pending any more. Checked by
	# id and not by name, so re-entering the *same* road cancels a candidate,
	# while crossing between two edges of one road (Hennessy Road is 40-odd of
	# them) is caught by the name comparison below instead.
	if id == edge_id:
		_clear_pending()
		return

	# A different edge that carries the name already on the plate. Adopt its id
	# silently — no dwell, no change — so that the *next* sample of it takes the
	# cheap path above. Without this, a long street's every edge boundary would
	# start a fresh dwell against a name that is not changing.
	if en == street_en:
		edge_id = id
		_clear_pending()
		return

	if id != _pending_edge:
		_pending_edge = id
		_pending_s = 0.0

	_pending_s += delta_s
	if _pending_s < _dwell_s:
		return

	# The first named street ever seen is not a "change" — there was nothing to
	# change from, and counting it would put an off-by-one in the one number
	# that grades this.
	if not street_en.is_empty():
		changes += 1
	street_en = en
	street_zh = zh
	edge_id = id
	_clear_pending()


## True once there is a street to draw. The plate stays hidden until then rather
## than drawing an empty frame, which on a clone with no generated city is every
## frame.
func has_street() -> bool:
	return not street_en.is_empty()


func _clear_pending() -> void:
	_pending_edge = -1
	_pending_s = 0.0
