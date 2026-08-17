extends Node

## Hands out the renderer's spot-light slots to the cars nearest the camera.
##
## ⚠️ **This exists because the cliff is silent.** Forward Mobile pairs 8 spot
## lights per rendered object and the fragment shader loops that fixed list.
## `roads.glb` is one mesh for the whole region and on screen whenever the player
## is, so **every beam in the game competes for the same 8 slots** — at two lamps
## a car, four cars. Past that the ninth light contributes **exactly zero**: no
## warning, no fallback, no dimming. Worse, which four win is *pair order* rather
## than distance, so beams pop as the BVH re-pairs and the player's own car is
## not guaranteed a slot in its own frame.
##
## The rule is therefore **nearest-N gets beams**, and the rest go dark.
##
## ⚠️ **Only the thrown cone is budgeted. Lenses are never touched.** A lamp glass
## is emissive shading on the car's own material and costs no light slot at all,
## so a car denied a beam still *reads* as lit — which is what a distant car
## should look like anyway. Budgeting the lenses too would make the roster blink.
##
## ⚠️ **`distance_fade` is not this, and shipping it did not close this.** Fading
## a far beam genuinely frees a slot and it ships (35/15 m, byte-identical in the
## shipped frame) — but it **bounds** who competes rather than capping how many
## win. Eight cars inside the fade radius still overrun the list. Keep both.
##
## Registration is by duck-typed callback rather than by a typed rig class, for
## the reason `driver.gd` duck-types its vehicle: a `class_name` annotation
## resolves at parse time, and a tool or a test scene that never loads
## `VehicleLamps` would fail to compile this instead of simply having no rigs.

const PROFILE_PATH := "res://tuning/beams.tres"
const PROFILE_SCRIPT := "res://scripts/vehicle/beam_profile.gd"

## Registered rigs, in registration order. Each entry is the rig node itself;
## everything else is asked of it when the grant is computed, so a rig that moves
## or changes its lamp count needs no re-registration.
var _rigs: Array[Node] = []
## Which rigs currently hold a grant. Kept as a set of instance ids rather than of
## nodes so a freed rig cannot keep a slot alive through a dangling reference.
var _granted: Dictionary = {}
## ⚠️ **Typed `Resource`, not `BeamProfile`, on purpose.** Naming the global here
## would make this script un-parseable wherever the class cache has not been
## written — `verify_beam_budget.gd` `load`s it on a fresh clone, and a parse
## failure there exits **0** having checked nothing. `ARCHITECTURE.md` records
## that trap for `--script` tools; this is the same trap reached from the other
## side, so the fields are read by name with the measured limits as fallbacks.
var _profile: Resource = null
var _since_regrant_s: float = 0.0
## Set by `register`, consumed on the next frame. See `register`.
var _dirty: bool = false


func _ready() -> void:
	_profile = load(PROFILE_PATH) as Resource
	if _profile == null:
		# Not fatal, and deliberately so: a missing tuning file must not stop the
		# game booting.
		#
		# ⚠️ **The fallback is the profile *script's* own defaults, not literals
		# repeated here.** Hard rule 4 puts tuning values in `.tres`, and a second
		# copy in code is a copy that goes stale: lower `max_spot_lights`'s default
		# in `beam_profile.gd` against a hardcoded 8 here, and a missing-profile
		# boot grants *more* than the profile intends — the one direction a
		# fallback must never go. Instantiated by path rather than by `class_name`,
		# for the reason `_profile`'s own comment gives.
		push_warning("BeamBudget: no profile at %s; using the script defaults." % PROFILE_PATH)
		var script: GDScript = load(PROFILE_SCRIPT) as GDScript
		if script != null:
			_profile = script.new() as Resource
	# Nothing registered yet, and most scenes never will — a menu, or any car
	# carrying no `SpotLight3D` at all. Woken by `register`.
	set_process(false)


func _number(field: StringName, fallback: float) -> float:
	# `fallback` covers only the case where even the script would not load, which
	# is a broken install rather than a missing tuning file.
	if _profile == null:
		return fallback
	return float(_profile.get(field))


func _cap() -> int:
	return int(_number(&"max_spot_lights", 8.0))


func _regrant_hz() -> float:
	# Clamped low, because `1.0 / 0.0` is INF and a budget that never re-ranks
	# again fails by going quiet. `@export_range` stops the editor writing 0; it
	# does not stop a hand-edited `.tres`.
	return maxf(1.0, _number(&"regrant_hz", 6.0))


func _swap_margin_m() -> float:
	return _number(&"swap_margin_m", 8.0)


## Take a lamp rig into the budget. Idempotent.
##
## The rig must answer `beam_count() -> int` and `set_beams_granted(bool) -> void`,
## and be a `Node3D` so it has a position to rank by.
func register(rig: Node) -> void:
	if rig == null or _rigs.has(rig):
		return
	# ⚠️ **Both halves of the contract, or the rig is refused.** The contract is
	# duck-typed on purpose, which means nothing checks it at parse time — and a
	# rig answering `beam_count()` but not `set_beams_granted()` is the worst
	# case: it is charged for slots, counted in `spent()`, and can never light
	# them, so the roster goes dim for beams nobody can see. Refused loudly here
	# rather than discovered at grant time.
	if not rig.has_method("beam_count") or not rig.has_method("set_beams_granted"):
		push_warning(
			(
				"BeamBudget: %s answers neither beam_count() nor set_beams_granted(); not registered."
				% rig.name
			)
		)
		return
	_rigs.append(rig)
	# ⚠️ **Granted false until proven otherwise, never true.** A rig that booted
	# lit and was then denied would throw one frame of light across whatever it is
	# pointing at; a rig that booted dark and is then granted simply switches on.
	# Only one of those is a visible mistake.
	rig.set_beams_granted(false)
	# ⚠️ **Marked dirty, not re-ranked here.** Registering N rigs one at a time
	# would run N regrants, each an O(N log N) sort — N^2 log N rank evaluations
	# during scene load — and every one of them before there is a camera, so
	# `_eye()` ranks them all against the origin and the answers are thrown away.
	# The rig starts denied, so nothing is lit while the flag waits for the next
	# `_process`. Unregister is the asymmetric case and regrants immediately: a
	# freed slot has to be handed on in the same frame the car left.
	_dirty = true
	set_process(true)


func unregister(rig: Node) -> void:
	if rig == null:
		return
	_rigs.erase(rig)
	# Erased *and* re-granted, so the slot is handed on in the same frame the car
	# left. `P3-3` despawns traffic constantly, and a slot that stayed reserved
	# until the next tick is a beam the cars still on screen could have had.
	_granted.erase(rig.get_instance_id())
	if _rigs.is_empty():
		set_process(false)
	# ⚠️ **The rig is told, not just forgotten.** Dropping the id alone leaves the
	# car holding `_beams_granted == true` while the budget believes it holds
	# nothing, and a **pooled** car — removed from the tree and put back, which is
	# how `P3-3` will recycle traffic — would come back lit on a grant that no
	# longer exists. `VehicleLamps` re-registers from `_enter_tree` for the same
	# reason; these are the two halves of one round trip and both are needed.
	if is_instance_valid(rig) and rig.has_method("set_beams_granted"):
		rig.set_beams_granted(false)
	_regrant()


## Re-rank now, without waiting for the next regrant tick.
##
## For anything that moves a car discontinuously — a respawn, a teleport, a
## camera cut — where the ranking is stale in a way `regrant_hz` was not chosen
## to cover. `verify_beam_budget.gd` also uses it to make its runs deterministic
## rather than depending on when a tick lands.
func refresh() -> void:
	_regrant()


## How many beams are lit right now, and how many slots exist. For the debug
## overlay and for `verify_beam_budget.gd`.
func spent() -> Array[int]:
	var lit: int = 0
	for rig: Node in _rigs:
		if _granted.has(rig.get_instance_id()):
			lit += _beams_of(rig)
	return [lit, _cap()] as Array[int]


func _process(delta: float) -> void:
	if _dirty:
		_dirty = false
		_since_regrant_s = 0.0
		_regrant()
		return
	var period_s: float = 1.0 / _regrant_hz()
	_since_regrant_s += delta
	if _since_regrant_s < period_s:
		return
	# ⚠️ **Subtracted, not zeroed** — the same defect `vehicle_lamps.gd` measured
	# on `probe_hz` and documents beside its own countdown: assigning zero throws
	# away the overshoot and quantises the period *up* to whole frames, so
	# `probe_hz = 10` delivered 8.58 Hz and 15 delivered 12. This runs on
	# `_process` with a variable delta rather than the fixed physics tick, so the
	# error here is larger than the one that was measured, not smaller.
	#
	# Clamped so a long frame — a streamer hitch, a stall — cannot bank credit for
	# several regrants and fire them back to back on the frames after it.
	_since_regrant_s = minf(_since_regrant_s - period_s, period_s)
	_regrant()


func _beams_of(rig: Node) -> int:
	if not is_instance_valid(rig) or not rig.has_method("beam_count"):
		return 0
	return int(rig.beam_count())


## Rank every live rig by distance to the camera and light the nearest that fit.
func _regrant() -> void:
	_rigs = _rigs.filter(func(rig: Node) -> bool: return is_instance_valid(rig))
	if _rigs.is_empty():
		# Cleared rather than left behind: the filter above can empty `_rigs` while
		# ids of freed nodes remain, and a map that outlives every one of its keys
		# is the one place this could grow without bound.
		_granted.clear()
		return

	var eye: Vector3 = _eye()
	# Distance is measured to the camera rather than to the player's car, because
	# the camera is what the frame is drawn from — a look-back or a cinematic
	# would otherwise light the cars behind the viewer and darken the ones in it.
	#
	# ⚠️ **Ranked once into a pair array, not recomputed inside the comparator.**
	# `sort_custom` calls its lambda O(n log n) times and would evaluate
	# `_rank_of` twice per comparison — a `Dictionary` lookup and a `sqrt` each —
	# for n values that do not change during the sort. `regrant_hz` exists
	# precisely because this sort is the expensive thing here.
	var ranked: Array = []
	for rig: Node in _rigs:
		ranked.append([_rank_of(rig, eye), rig])
	ranked.sort_custom(func(a: Array, b: Array) -> bool: return float(a[0]) < float(b[0]))

	var budget: int = _cap()
	var next_granted: Dictionary = {}
	for entry: Array in ranked:
		var rig: Node = entry[1]
		var cost: int = _beams_of(rig)
		# ⚠️ **A rig that does not fit is skipped, not stopped at.** Passing over a
		# four-lamp truck to light two motorbikes behind it spends the budget on
		# more of the frame, and stopping at the first rig too big to fit would
		# leave slots unused for as long as it stayed in front.
		if cost <= 0 or cost > budget:
			continue
		budget -= cost
		next_granted[rig.get_instance_id()] = true
		if budget <= 0:
			break

	for rig: Node in _rigs:
		var id: int = rig.get_instance_id()
		var now: bool = next_granted.has(id)
		if now != _granted.has(id):
			rig.set_beams_granted(now)
	_granted = next_granted


## Sort key: distance to the eye, with a discount for already being lit.
##
## The discount is the hysteresis. Without it two cars abreast swap beams every
## regrant, because their distances cross and re-cross by centimetres — which
## reads as both cars flickering rather than as either one being chosen.
func _rank_of(rig: Node, eye: Vector3) -> float:
	var spatial := rig as Node3D
	if spatial == null:
		return INF
	var distance: float = spatial.global_position.distance_to(eye)
	if _granted.has(rig.get_instance_id()):
		distance -= _swap_margin_m()
	return distance


func _eye() -> Vector3:
	var tree: SceneTree = get_tree()
	if tree == null:
		return Vector3.ZERO
	# `tree.root` is a `Window`, which *is* a `Viewport`, so it answers this
	# directly — going through `get_viewport()` first returned the same object.
	var camera: Camera3D = tree.root.get_camera_3d()
	if camera != null:
		return camera.global_position
	# No camera yet — first frame, or a headless run. Ranking from the origin is
	# arbitrary but stable, and the next regrant fixes it once a camera exists.
	return Vector3.ZERO
