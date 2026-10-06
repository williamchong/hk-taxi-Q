class_name VehicleLamps
extends Node3D
## Switches the taxi's lamp circuits from what the car is doing (`P3-11d`).
##
## The body is one merged primitive, so there is no lamp *node* to show or hide.
## The import hook stamps each lens with a circuit id in `UV.x` from its
## material slot's name (`P5-23`; `tools/make_vehicle.py` emits those names) and
## `vehicle_body.gdshader` lights the ones this script names — brake, reverse,
## an indicator per side, the two front circuits, and the roof sign.
##
## The front lamps answer to the light rather than to the driver, because on
## this car there is nobody to flick a switch: side lamps in shade, main beams
## where the sky is shut out or the rig is a night one. `Lighting` is that
## ladder and `_read_lighting` is the only thing that decides it.
##
## ⚠️ **Written per instance, not to the material.** `vehicle_body.tres` is one
## shared resource handed to every mesh that asks for it by name, so a plain
## `set_shader_parameter` would put the whole roster on one brake pedal. See the
## `lamp_lit` declaration in the shader.
##
## ⚠️ **It reads the car, never `InputRouter`.** Reading the player's input here
## would work exactly once — `ART_DESIGN.md`'s roster puts an AI red taxi on the
## same body, and every one of them would indicate whenever the player turned.
## `VehicleController` publishes what *this* car is doing — steering, and the
## pedal it samples once a tick — and that is the only thing a lamp on this car
## may answer to.
##
## Presentation only: nothing here is read back by the
## physics, so it cannot change how the car drives. It runs on the physics tick
## for the same reason that one does — every value it reads is written there, so
## a render-rate update would re-derive the identical answer two or three times
## between the ticks that can change it.
##
## ⚠️ **The front lamps are the exception to that last paragraph, and they are
## why `probe_hz` exists.** Everything above is a value the controller *wrote*
## this tick; whether the car is in shadow is a value nobody wrote and this
## script has to go and ask the physics world for, twice, with a raycast each.
## That is a cost per car per tick rather than a read, and `ART_DESIGN.md`'s
## roster multiplies it — so the probe is sampled well below the tick rate. It
## can afford to be: `dark_hold_s` means the answer is not believed for a
## fraction of a second anyway, so sampling it 60 times inside that window
## re-derives the same answer 59 times over.

## The shader's per-instance channels. See `vehicle_body.gdshader`.
const PARAMETER: StringName = &"lamp_lit"
const PARAMETER_FRONT: StringName = &"lamp_front"

## How lit the world around the car is, darkest last.
##
## ⚠️ **Ordered, and two functions depend on it.** `_settle` asks whether a
## reading is *darker* than what is committed by comparing these, and
## `_apply_beam` takes the lighter of two states with `<` and then tests the
## result against `SUN` and `DARK` by name. So inserting a state in the middle
## re-sorts the ladder rather than extending it, and it changes what the beams
## do as well as when the lamps switch.
enum Lighting {
	## Open sky, sun on the car. Every front lamp out.
	SUN,
	## The sun is blocked but the sky above is not — a tower's shadow, the lee of
	## a flyover deck. Side lamps only, which is what a driver switches on when
	## the light drops without going.
	SHADOW,
	## No sky overhead, or no daylight at all. Main beams, side lamps with them.
	DARK,
}

## Once a turn is counted, the lock has to fall to this fraction of
## `steer_threshold` before it stops counting.
##
## ⚠️ **Without hysteresis the hold below can never complete near the
## threshold.** A single frame at 0.349 restarts it, so a driver holding steady
## lock right about the line — which analogue steering does constantly — resets
## the timer for ever and the indicator that `steer_hold_s` exists to earn is the
## one thing that never comes on.
const TURN_RELEASE: float = 0.75

## The rig's dials — the indicators, the roof sign, the light probe and the
## thrown beams' side-lamp share. Assigned in `taxi.tscn`; the values and their
## reasons are `tuning/vehicle_lamps.md`'s. ⚠️ Read through `usable()` before
## any lamp runs: the profile declares no defaults, so a missing key is a zero,
## and `_physics_process` divides by `probe_hz` and never flashes on `blink_hz`.
@export var profile: VehicleLampsProfile

## Whether the roof sign is lit: the car is free for hire (`P3-48`).
##
## ⚠️ **Written from outside, and true until something says otherwise.** The
## fare loop owns the hire state (`TaxiHire` writes this on board and on drop);
## a car with no fare loop over it — free roam under `--fares=off`, a verify
## tool, `B3`'s traffic — is a taxi plying for hire, which is what the sign
## showed before anything simulated a fare.
var for_hire: bool = true

var _car: VehicleController = null
var _body: MeshInstance3D = null
## Runs only while an indicator is live, and resets to zero when it goes out, so
## a turn always starts on a lit flash. Free-running would leave the first
## quarter-second of some turns dark, which reads as the indicator being late.
var _blink_phase: float = 0.0
## How long lock has been held on `_turn_side`, against `steer_hold_s`.
var _turn_held_s: float = 0.0
## Which way the car is turning past `steer_threshold`: -1 left, +1 right, 0 not.
## Kept between frames because a *change* of side has to restart the hold —
## swinging straight from one lock to the other is two turns, not one long one.
var _turn_side: int = 0
## The lighting the front lamps are actually wired to. Only `_settle` moves it.
var _lighting: Lighting = Lighting.SUN
## The last probe's answer, held between probes so the hold below accumulates
## against real elapsed time rather than against the sampling rate.
var _seen: Lighting = Lighting.SUN
## How long `_seen` has read the same way, against `dark_hold_s` / `light_hold_s`.
var _seen_held_s: float = 0.0
## Counts down to the next probe. See `probe_hz`.
var _probe_due_s: float = 0.0
## Direction **toward** the sun, cached from the rig. `Vector3.ZERO` where there
## is no rig at all, which is not the same as night — see `read_rig`.
var _sun_toward: Vector3 = Vector3.ZERO
## Whether the rig is a night one, decided once. Read `read_rig` before assuming
## this is a per-frame fact: it moves when the rig does, at the rig's rate.
var _night: bool = false
## Reused, like `VehicleController`'s. Building one per probe would allocate
## twice a probe for the life of the process.
var _probe := PhysicsRayQueryParameters3D.new()
## The lights the front lamps throw — one per lamp, and empty on a car that
## carries none.
##
## Optional on purpose, like the lenses: a roster car may carry no lamp rig at
## all, and an AI taxi too far away to see one is a light worth not spending.
## However many the scene holds is however many this switches, so a roster car
## can ship one cone, or none, without touching this file.
var _beams: Array[SpotLight3D] = []
## Each beam's authored reach and brightness, by index, so `sidelamp_beam` can
## scale them down and put them back. Cached because the **scene** owns both
## numbers and this only scales them — and cached rather than read back off the
## light, because `share` can be 0.3 or 1.0 and dividing the authored value out
## of a scaled one loses it the first time it is written.
var _beam_ranges_m: PackedFloat32Array = PackedFloat32Array()
var _beam_energies: PackedFloat32Array = PackedFloat32Array()
## Whether `BeamBudget` currently allows this car to throw its beams at all.
##
## ⚠️ **Starts `false`, and the first grant switches it on.** The renderer pairs
## only 8 spot lights per object and the road chunk under the car is one, so beams are a
## rationed resource rather than a per-car decision — see `beam_budget.gd`. A car
## that assumed the slot and was later denied would light one frame of road it
## had no budget for.
var _beams_granted: bool = false
## `usable()`'s answer, taken once in `_ready`. See there. ⚠️ Cached on the
## invariant that `profile` is set by the scene and never swapped on a live
## node: the door and the face re-ask per event and can take a swap,
## this rig ticks at 60 Hz and does not.
var _usable: bool = false


func _ready() -> void:
	_car = VehicleController.above(self)
	assert(_car != null, "VehicleLamps found no VehicleController above it.")
	# The one mesh inside the body .glb. Taken by search rather than by path so a
	# regenerated asset can rename it, which `tools/make_vehicle.py` decides.
	var found: Array[Node] = find_children("*", "MeshInstance3D", true, false)
	if not found.is_empty():
		_body = found[0] as MeshInstance3D
	assert(_body != null, "VehicleLamps found no MeshInstance3D to switch.")
	# Cached once for the per-tick path; `usable()` itself stays pure so a verify
	# tool can ask it of a car outside a tree. A rig on a bad table never ticks,
	# never joins the budget and never writes a beam: every lens keeps the
	# shader's dark default, which is the inert state `verify_vehicle.gd` grades.
	_usable = usable()
	# Belt and braces, because asserts are stripped from release builds: without
	# this a mis-wired scene crashes on the first frame of an exported build
	# rather than driving around with dark lamps.
	set_physics_process(_car != null and _body != null and _usable)
	if _car != null:
		# The car's own shell, so a probe cast from inside it cannot report the
		# taxi as its own shade. `probe_height_m` starts the rays outside the
		# body anyway; this covers the case where someone lowers it.
		#
		# ⚠️ **No `collision_mask`, and it will need one before `P3-3`.** Nothing
		# in the project sets a layer today — every collider is on layer 1 — so a
		# mask would exclude nothing and buy nothing. It stops being free the
		# moment traffic adds bodies the probes should ignore: a bus alongside
		# reads as `SHADOW` and a trigger volume overhead reads as cover, which
		# is a correctness argument rather than a cost one. Jolt tests the mask
		# per candidate, so it never shortens the ray either way.
		_probe.exclude = [_car.get_rid()]
		# Searched from the car rather than named by path, for the reason the body
		# mesh is: the scene owns where each beam sits and how far it reaches, and
		# a car without any still switches its lenses. Every spot found is taken,
		# so adding or removing a lamp is a scene edit and nothing else.
		for node: Node in _car.find_children("*", "SpotLight3D", true, false):
			var beam := node as SpotLight3D
			_beams.append(beam)
			_beam_ranges_m.append(beam.spot_range)
			_beam_energies.append(beam.light_energy)
	read_rig()
	SunGlint.follow_rig(self, read_rig)
	_join_budget()
	if not _usable:
		return
	# ⚠️ **This call can only ever put the beams *out*, and that is the point.**
	# Both `_lighting` and `_seen` start at `SUN`, so there is no state a car
	# could boot into that this would light. What it is for is the scene: a car
	# authored with `visible = true` on its lamps — the obvious mistake to make
	# when adding one to a roster model — would otherwise drive in daylight with
	# its beams on until the first state *change* happened to correct it, which
	# on a sunny route is never.
	_apply_beam()


## Whether the table is whole: a profile, and no zero where a zero would divide
## (`probe_hz`), never flash (`blink_hz`, `blink_duty`) or probe nowhere
## (`sun_probe_m`, `cover_probe_m`). Loud on every call by design — a missing
## key is a build defect, not a state to remember quietly — and pure over
## `profile`, so `verify_vehicle.gd` can ask it of a car that never entered a
## tree and again after swapping a zeroed table in. The nine keys whose export
## floor is 0.0 are not in the table: a chosen zero there is legal, so a missing
## one cannot be told from it (`tuning/vehicle_lamps.md`).
func usable() -> bool:
	if profile == null:
		push_error("VehicleLamps: no VehicleLampsProfile assigned; every lamp stays dark.")
		return false
	var required: Dictionary[String, float] = {
		"blink_hz": profile.blink_hz,
		"blink_duty": profile.blink_duty,
		"sun_probe_m": profile.sun_probe_m,
		"cover_probe_m": profile.cover_probe_m,
		"probe_hz": profile.probe_hz,
	}
	return not TuningTable.any_zero(profile, required, "VehicleLamps", "every lamp stays dark")


## How many spot-light slots this car asks for. `BeamBudget`'s side of the deal.
##
## Read from the scene rather than assumed to be two, so a roster car with one
## cone — or a truck with four — is costed as what it is.
func beam_count() -> int:
	return _beams.size()


## Allow or deny this car's thrown beams. `BeamBudget`'s side of the deal.
##
## ⚠️ **Applied through `_apply_beam` rather than by hiding the lights here**, so
## a grant that arrives while the car is in daylight does not switch anything on:
## the ladder still has the last word about whether a *granted* beam is lit.
func set_beams_granted(granted: bool) -> void:
	if granted == _beams_granted:
		return
	_beams_granted = granted
	_apply_beam()


## The arbiter, or `null` where the scene runs without one.
##
## Looked up rather than named as a typed autoload, so a scene loaded by a verify
## tool or a test harness without the autoload still runs its lenses. The same
## shape `VehicleController.input_path` and `ChaseCamera.input_path` use for
## `InputRouter` since `Q119`; only the dev chrome still names an autoload
## (`DebugHud`) by its global.
func _budget() -> Node:
	return get_node_or_null(^"/root/BeamBudget")


## Ask the arbiter for beams, or light them if there is no arbiter.
##
## ⚠️ **Registered only if this car actually throws a beam.** A rig with no
## `SpotLight3D` costs no slot, so putting it in the ranking would let it
## displace a car that does.
func _join_budget() -> void:
	# A rig on a bad table asks for no slot: it would never light the beam it
	# was granted, and the slot is one a working car cannot use.
	if _beams.is_empty() or not _usable:
		return
	var budget: Node = _budget()
	if budget != null:
		budget.register(self)
		return
	# No arbiter: this is the only car in the world, which is exactly the case the
	# budget was written for the *absence* of. Light the beams.
	_beams_granted = true


func _enter_tree() -> void:
	# ⚠️ **Re-registers, because `_ready` fires once per node lifetime and
	# `_exit_tree` fires on every removal — including a reparent.** A car taken
	# out of the tree and put back, which is how a pool is built and how `P3-3`
	# will recycle traffic, would otherwise unregister on the way out and never
	# register on the way back: its beams stay dark forever, and nothing says so.
	# Guarded on `_beams`, which is empty until `_ready` has found the lights, so
	# the very first entry is `_ready`'s to handle.
	if not _beams.is_empty():
		_join_budget()


func _exit_tree() -> void:
	# A car that leaves the world holds no slot. Without this a despawned AI taxi
	# keeps its grant until the next regrant filters the freed node out, which is
	# a slot the cars still on screen cannot use.
	var budget: Node = _budget()
	if budget != null:
		budget.unregister(self)
	else:
		# Nothing to take the grant back, so drop it here — otherwise a pooled car
		# in an arbiter-less scene returns still believing it holds a slot.
		_beams_granted = false


## Re-read the scene's lighting rig.
##
## ⚠️ **Public, and called at `_ready` and again each time the rig moves**
## (`Q160`: a `LightingRig` with a cycle emits `changed` at its own
## `update_hz`, and `SunGlint.follow_rig` is what connects this). Never per tick — a rig
## that stands still is one constant, and a moving one says when it moved.
##
## ⚠️ **A missing rig is "no answer", not "night", and the difference matters
## more than it reads.** A verify tool or an import loads the taxi with no world
## around it, and calling that night would put every headless render of the car
## on main beam — visible in exactly one place, a graded frame, which is the
## failure mode this whole file's siblings keep tripping over. So no sun leaves
## `_sun_toward` at zero, `_probe` returns `SUN`, and the front lamps stay out.
## The cost is that a night rig authored by *deleting* its `DirectionalLight3D`
## is indistinguishable from no rig and would drive dark; a night rig should dim
## or drop its key light, not remove it.
func read_rig() -> void:
	var sun: DirectionalLight3D = SunGlint.rig_sun(self)
	# No table, no night bar to read the rig against — and nothing downstream
	# will run anyway. Left as "no answer", the same as no rig.
	if sun == null or not _usable:
		_sun_toward = Vector3.ZERO
		_night = false
		return
	# Asked of `SunGlint` rather than derived here, so the -Z/+Z convention has
	# one definition. See `SunGlint.toward` for why a second copy is a silent
	# failure in both consumers.
	_sun_toward = SunGlint.toward(sun)
	# Below the horizon or turned down to nothing. Either way there is no
	# daylight to be in or out of, so the probes have nothing to answer and the
	# ladder goes straight to its bottom rung.
	_night = sun.light_energy <= profile.night_energy or _sun_toward.y <= 0.0


func _physics_process(delta: float) -> void:
	# The threshold to start turning; TURN_RELEASE's share of it to stop.
	var leaving: float = profile.steer_threshold * TURN_RELEASE
	var side: int = 0
	if _car.steer_ratio > (leaving if _turn_side > 0 else profile.steer_threshold):
		side = 1
	elif _car.steer_ratio < -(leaving if _turn_side < 0 else profile.steer_threshold):
		side = -1

	# Straightening or swapping sides restarts the hold, and takes the blink
	# phase with it so the next turn's first flash is a lit one.
	if side != _turn_side:
		_turn_held_s = 0.0
		_blink_phase = 0.0
	_turn_side = side
	if side != 0:
		_turn_held_s += delta

	var indicating: bool = side != 0 and _turn_held_s > profile.steer_hold_s
	if indicating:
		_blink_phase = fmod(_blink_phase + delta * profile.blink_hz, 1.0)
	else:
		_blink_phase = 0.0
	# One phase for both sides rather than a flasher each. They are never both
	# live — `side` is one number — so the only thing a second phase could
	# express is a hazard flash, which nothing asks for.
	var flash: float = 1.0 if _blink_phase < profile.blink_duty else 0.0

	# `CIRCUIT_*` order less one: x brake, y reverse, z indicator left, w right.
	#
	# ⚠️ Brake and reverse are asked of the car, not worked out from the pedal.
	# One button serves both and which one the player gets depends on the car's
	# speed — so at a standstill with the pedal held the *reverse* lamps light,
	# because reverse is what the pedal is asking for. That is the controller's
	# rule and this reads it rather than restating it.
	# ⚠️ **The brake lens is the tail lamp too** (`Q160`): with the front lamps
	# on it burns at `tail_lit`, a floor under the brake's 1.0 and not a second
	# lens — which is what a tail lamp is, and a car at dusk with dark tails
	# until it brakes is the one that reads as unlit.
	var lamps_on: bool = _lighting != Lighting.SUN
	var tail: float = profile.tail_lit if lamps_on else 0.0
	var lit := Vector4(
		1.0 if _car.is_braking() else tail,
		1.0 if _car.is_reversing() else 0.0,
		flash if indicating and side < 0 else 0.0,
		flash if indicating and side > 0 else 0.0,
	)
	_body.set_instance_shader_parameter(PARAMETER, lit)

	_settle(delta)
	# `CIRCUIT_*` order less one again, continuing into the second vector:
	# x side lamps, y head lamps, z the roof sign, w unwired.
	#
	# ⚠️ **`z` holds the roof sign because `z` was free, not because the sign is a
	# front lamp.** The two below are the light ladder; the sign is not on it and
	# must not be folded onto it — see `sign_lit`. The shader says the same thing
	# about the seam between the two vectors being arbitrary.
	#
	# ⚠️ **The side lamps stay lit under the main beams rather than handing over
	# to them**, which is both what a car does — position lamps do not go out
	# when the headlamps come on — and what makes the ladder legible. Swap them
	# and the two states are a different pair of lamps at the same count, which
	# reads as a flicker; stacked, the nose visibly gains a lamp.
	var front := Vector4(
		1.0 if lamps_on else 0.0,
		1.0 if _lighting == Lighting.DARK else 0.0,
		profile.sign_lit if for_hire else 0.0,
		0.0,
	)
	_body.set_instance_shader_parameter(PARAMETER_FRONT, front)


## Probe the world on schedule, and move `_lighting` once a reading has held.
func _settle(delta: float) -> void:
	_probe_due_s -= delta
	if _probe_due_s <= 0.0:
		# ⚠️ **Added to, not assigned, and the difference is a seventh of the
		# rate.** Assigning discards the overshoot, which quantises the period
		# *up* to whole ticks — and `0.1` is not a whole number of 60 Hz ticks in
		# binary, so six subtractions leave a residue of about `2e-17` and the
		# countdown costs a seventh tick. Measured: `probe_hz = 10` delivered
		# **8.58 Hz**, and 15 delivered 12. Carrying the remainder forward makes
		# the dial mean what it says while still firing at most once a tick,
		# since one period is never shorter than one tick at any allowed rate.
		_probe_due_s += 1.0 / profile.probe_hz
		var seen: Lighting = _read_lighting()
		if seen != _seen:
			# ⚠️ **The hold restarts when the reading crosses `_lighting`, not
			# whenever it changes — and restarting on every change is a stall,
			# not a stricter hold.** Two readings that disagree with each other
			# but agree about the *direction* are both evidence for the same
			# move, so zeroing between them lets them cancel out for ever. That
			# is not a corner case: it is precisely the picket fence of shadow
			# `light_hold_s` exists for. Committed to `DARK` under a deck, then
			# out into a street alternating `SUN`/`SHADOW` about once a second,
			# the timer never reaches 1.6 s and the main beams stay on for the
			# whole drive — the failure this hold was built to prevent, arriving
			# through the hold itself. A canyon flickering `DARK`/`SHADOW`
			# stalls the mirror image, with no front lamp ever lighting.
			if signi(int(seen) - int(_lighting)) != signi(int(_seen) - int(_lighting)):
				_seen_held_s = 0.0
			_seen = seen
			# The beams read `_seen` as well as `_lighting`, so they move here
			# too — still at the probe rate rather than the tick rate.
			_apply_beam()
	_seen_held_s += delta

	# Which hold applies is decided by the *direction* of the change, which is
	# what `Lighting` being ordered buys — see `light_hold_s` for why the two are
	# deliberately far apart.
	if _seen == _lighting:
		return
	var hold: float = profile.dark_hold_s if _seen > _lighting else profile.light_hold_s
	if _seen_held_s >= hold:
		_lighting = _seen
		_apply_beam()


## Point the thrown light at the **lighter** of `_lighting` and the last probe.
##
## ⚠️ Deliberately not "whatever `_lighting` says" — the beams and the lenses
## read different things, and the block comment below is the argument for it.
##
## ⚠️ **Called on a change of state, not every tick, and that is the one place
## in this file where it matters.** The lens writes are per-instance shader
## values measured at tens of nanoseconds and are left unguarded; a light is a
## different animal — moving one dirties it for the renderer, and `_lighting`
## changes at most once per hold, which is a third of a second at its very
## fastest. Writing it 60 times a second would be 180 identical writes for every
## one that says anything.
func _apply_beam() -> void:
	if _beams.is_empty():
		return

	# ⚠️ **The beam answers to the lighter of the held and the current reading,
	# where the lenses answer to the held one alone — and the two are allowed to
	# disagree.** A lens still lit as the car reaches sunlight is a lamp nobody
	# has switched off yet, which is what real cars look like all day. A *beam*
	# that lingers paints a bright pool across sunlit tarmac, and there is no
	# lighting condition in which that is not a mistake. So the hold governs the
	# glow and never outlives the sun for the cone: the moment a probe reads
	# direct sun the beams go out, whatever the lenses are still doing.
	#
	# Taking the lighter of the two also steps the beams down rather than
	# switching them — leaving a deck into open shade drops them to the side
	# lamps' pool while `_lighting` is still `DARK`, instead of holding full beam
	# and then cutting to nothing.
	#
	# ⚠️ **The cost is that the beams are the one thing here the holds no longer
	# protect, and the symptom would be blamed on them.** `_seen` is the raw
	# probe with no hold on it, so in exactly the picket fence `light_hold_s`
	# exists for — committed `DARK`, readings alternating `SUN`/`SHADOW` — the
	# lenses stay steady while the cones flick at up to `probe_hz`. That is the
	# accepted price of never lighting sunlit tarmac. ⚠️ If it shows on a drive,
	# the fix is a short hold on the *light-ward* beam transition alone; it is
	# **not** a change to the ladder or to `_settle`, which are working.
	var throwing: Lighting = _lighting if _lighting < _seen else _seen

	# Hidden rather than dimmed to nothing. A zero-energy light is still a light
	# the renderer gathers, culls and loops over per object, and "off" here means
	# a car in daylight — which is most cars, most of the time.
	#
	# ⚠️ **The grant is ANDed in here rather than earlier, so a denied car still
	# computes its lighting state.** `_lighting`, `_seen` and the lens circuits go
	# on being switched by the ladder whatever the budget says — only the cone is
	# rationed. A car that stopped reading the world while dark would arrive at
	# its slot with a stale state and light the wrong thing for a hold.
	var lit: bool = throwing != Lighting.SUN and _beams_granted
	var share: float = 1.0 if throwing == Lighting.DARK else profile.sidelamp_beam
	for i: int in _beams.size():
		var beam: SpotLight3D = _beams[i]
		beam.visible = lit
		if not lit:
			continue
		beam.light_energy = _beam_energies[i] * share
		# Reach is scaled with brightness rather than held. A dim lamp that still
		# reached the authored 32 m would light a far kerb it could never really
		# touch, which reads
		# as the road brightening on its own rather than as the car lighting it.
		beam.spot_range = _beam_ranges_m[i] * share


## What the world says right now, before any hold is applied.
##
## ⚠️ **Cover is asked before shadow, and the order is the answer.** Under a deck
## both probes hit, so testing shadow first would put a car in an underpass on
## side lamps and never reach the main beams at all. Cover is the stronger claim
## about the light, so it is tested first and returns.
func _read_lighting() -> Lighting:
	if _night:
		return Lighting.DARK
	# No rig to be lit by. See `read_rig` — this is "no answer", not night.
	if _sun_toward == Vector3.ZERO:
		return Lighting.SUN

	var space: PhysicsDirectSpaceState3D = _car.get_world_3d().direct_space_state
	var origin: Vector3 = _car.global_position + Vector3.UP * profile.probe_height_m

	# ⚠️ **World up, not the car's.** "Is there sky above me" is a question about
	# the world, and a car mid-drift or cresting a ramp is still under open sky —
	# probing along the body's own up would switch the main beams on every time
	# the taxi leaned far enough to aim its roof at the tower beside it.
	_probe.from = origin
	_probe.to = origin + Vector3.UP * profile.cover_probe_m
	if not space.intersect_ray(_probe).is_empty():
		return Lighting.DARK

	_probe.to = origin + _sun_toward * profile.sun_probe_m
	if not space.intersect_ray(_probe).is_empty():
		return Lighting.SHADOW
	return Lighting.SUN
