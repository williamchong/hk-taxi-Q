class_name VehicleLamps
extends Node3D
## Switches the taxi's lamp circuits from what the car is doing (`P3-11d`).
##
## The body is one merged primitive, so there is no lamp *node* to show or hide.
## `tools/make_vehicle.py` stamps each lens with a circuit id in `UV.x` and
## `vehicle_body.gdshader` lights the ones this script names — brake, reverse,
## an indicator per side, and the two front circuits.
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
## Presentation only, like `WheelVisual`: nothing here is read back by the
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
## ⚠️ **Ordered, and the comparisons below depend on it.** `_settle` asks
## whether a reading is *darker* than what is committed by comparing these, so
## inserting a state in the middle re-sorts the ladder rather than extending it.
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

## Flashes per second. UK and Hong Kong regulation puts a real one between 1 and
## 2 Hz, and the middle of that is also what reads as a flash rather than as a
## flicker at the frame rates this ships at.
@export_range(0.5, 4.0, 0.05) var blink_hz: float = 1.5

## Share of each flash the lamp is lit for. Above a half on purpose: an
## indicator seen from behind at speed is a small object, and the eye needs
## longer on than off to call it a light rather than a glint.
@export_range(0.1, 0.9, 0.05) var blink_duty: float = 0.55

## How much lock counts as a turn, as a fraction of the lock available at this
## speed. See `VehicleController.steer_ratio` — a fraction rather than an angle,
## because full lock at 140 km/h is a quarter of full lock parked.
##
## ⚠️ The floor on this is comfort, not correctness. Set it near zero and the
## indicators strobe through every steering correction the player makes on a
## straight, which is what a real driver does *not* do.
@export_range(0.0, 1.0, 0.01) var steer_threshold: float = 0.35

## How long lock has to be *held* one way before the indicator comes on.
##
## ⚠️ **The threshold above cannot do this job on its own, and that is why both
## exist.** One says how hard a turn is, the other says how long it lasts, and an
## arcade car crosses hard lock constantly — a flick round a parked lorry, a
## correction out of a drift, a lane change. Every one of those trips the
## threshold, and without a hold the tail of the car strobes amber through all of
## them, which is worse than no indicator at all: it stops meaning "turning".
## Holding half a second keeps the lamp for the junctions it is about.
##
## The cost is that the lamp is late by exactly this much, which is fine — a real
## driver indicates before turning and this car indicates after, so it is already
## a read-out of what the car is doing rather than a signal of intent.
@export_range(0.0, 3.0, 0.05) var steer_hold_s: float = 0.5

## How far the shadow probe looks along the sun before calling the car sunlit.
##
## ⚠️ **Bounded by where collision exists, not by where shadow does.** Only the
## finest tile tier ships a collider (`city_streamer.gd`), and `streaming.tres`
## puts that band at 250 m — so a ray longer than this passes through the coarse
## tiles beyond it as if they were air and reports sun. 200 m keeps the probe
## inside the band with room for the hysteresis distance. It is not enough for
## every caster: `golden_hour.tscn`'s sun sits at 30°, so anything over about
## 115 m casts further than this ray reaches and its far shadow reads as sunlit.
## Raising it past the collider band cannot fix that, and a taller number would
## only look like it had.
@export_range(10.0, 400.0, 5.0, "suffix:m") var sun_probe_m: float = 200.0

## How far straight up the cover probe looks before calling the sky open.
##
## Sized to a road deck rather than to a building: this asks whether something
## is *over* the car, and the tallest thing that legitimately is — an elevated
## carriageway, the HKCEC's overhang — is tens of metres up, not hundreds.
##
## ⚠️ **Long is not safer here.** Extend it and the probe starts finding the
## upper storeys of whatever the car is parked beside the moment the footprint
## overhangs the kerb, which puts the taxi on main beam in open sun.
@export_range(2.0, 100.0, 1.0, "suffix:m") var cover_probe_m: float = 25.0

## Where both probes start, above the car's origin.
##
## Clear of the car's own roof — `taxi.tscn`'s body box tops out at 0.70 m — so
## the rays begin outside the shell rather than relying on the self-exclusion
## below to save them. Belt and braces, and it costs nothing.
@export_range(0.0, 4.0, 0.05, "suffix:m") var probe_height_m: float = 1.0

## How often the two probes are cast, against a 60 Hz physics tick.
##
## See the note in the header: this is the one thing here that *asks* the world
## rather than reading what was written to it, and `dark_hold_s` already refuses
## to believe a single reading. 10 Hz puts several samples inside the shortest
## hold, which is all the hold can use.
##
## Measured on the built region with 65 tier-0 tiles resident: the 25 m cover ray
## costs **0.49 µs** and the 200 m sun ray **0.91 µs**, against 0.50 µs for one of
## the four wheel rays the controller already casts every tick. So a probe is
## worth about three wheel rays, twenty times a second.
##
## ⚠️ **Every car on this script probes on the same tick, and that is left
## alone deliberately.** `_probe_due_s` starts at zero on every instance, so a
## roster spawned in one frame stays in lockstep for the life of the process —
## ~28 µs on one tick at twenty cars rather than 1.4 µs amortised. The obvious
## fix is a random starting phase, and it is **refused**: `.claude/skills`'
## driver runs are byte-deterministic and this project grades frames by `cmp`,
## so a per-run phase would make the moment a lamp switches unreproducible to
## buy ~1% of a frame on the device floor. Stagger it from something stable —
## the node path, a spawn index — if `P3-3` ever makes it matter.
@export_range(1.0, 60.0, 1.0, "suffix:Hz") var probe_hz: float = 10.0

## How long a *darker* reading must persist before the lamps follow it.
##
## Short, because being late into a dark place is the failure a driver notices.
@export_range(0.0, 5.0, 0.05, "suffix:s") var dark_hold_s: float = 0.35

## How long a *lighter* reading must persist before the lamps go out.
##
## ⚠️ **Deliberately several times `dark_hold_s`, and the asymmetry is the whole
## anti-flicker mechanism.** A street in Wan Chai is a picket fence of shadow —
## kerbside towers, gantries, footbridges, the gaps between them — and a car at
## 50 km/h crosses one every second or so. Symmetric holds would strobe the
## lamps through all of it, which is the failure `steer_hold_s` above already
## records for the indicators: a lamp that switches constantly stops meaning
## anything. Lingering on the way out costs a few seconds of lamps in sunlight
## and buys a lamp that only changes when the light really has.
@export_range(0.0, 10.0, 0.05, "suffix:s") var light_hold_s: float = 1.6

## How hard the main beams throw light on the world.
##
## ⚠️ **A lit lens and a thrown beam are two different features, and the lens
## alone is what looked finished.** The emissive lenses read perfectly from
## behind the car and light nothing in front of it, so under the HKCEC deck the
## taxi had blazing lamps on a pitch-black road — the failure only a frame from
## *ahead* of the car shows.
##
## Priced against the rig rather than chosen: `golden_hour.tscn`'s sun is 1.4 and
## `clean_daylight.tres` glows over 1.0, so a beam that reads on unlit tarmac
## without blowing out the kerb it crosses sits well above the sun's number and
## still under what would clip the road to white.
@export_range(0.0, 24.0, 0.1) var beam_energy: float = 7.0

## What share of the beam the side lamps throw, in energy and in reach.
##
## ⚠️ **Not zero, and not much above it.** Position lamps exist to be *seen*, not
## to see by, so a side lamp that lights the road as far as a headlamp erases the
## difference the two circuits were split to express. A short dim pool says "lit,
## but not driving on it".
@export_range(0.0, 1.0, 0.01) var sidelamp_beam: float = 0.3

## Key-light energy at or below which the rig counts as night.
##
## ⚠️ **A dial rather than a rule, because the rig that would trip it does not
## exist yet.** `DECISIONS.md` records night as a *switch between two static
## rigs*, so whatever `Q26` authors is what this has to answer to; a rig that
## dims its key light is caught here, and one that drops the sun below the
## horizon is caught by the elevation test in `read_rig` beside it. The two
## shipped rigs measure 1.4 and 0.9, so both clear this by a wide margin.
##
## ⚠️ A rig that deletes its `DirectionalLight3D` outright is **not** caught, and
## that is deliberate rather than an oversight — see `read_rig`.
@export_range(0.0, 1.0, 0.01) var night_energy: float = 0.05

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
## this is a per-frame fact: this sun does not move.
var _night: bool = false
## Reused, like `VehicleController`'s. Building one per probe would allocate
## twice a probe for the life of the process.
var _probe := PhysicsRayQueryParameters3D.new()
## The light the front lamps throw, or null on a car that carries none.
##
## Optional on purpose, like the lenses: `taxi_builtin.tscn` carries no lamp rig
## at all, and an AI taxi too far away to see one is a light worth not spending.
var _beam: SpotLight3D = null
## The beam's authored reach, so `sidelamp_beam` can shorten it and put it back.
## Cached because the scene owns the number — this only scales it.
var _beam_range_m: float = 0.0


func _ready() -> void:
	_car = VehicleController.above(self)
	assert(_car != null, "VehicleLamps found no VehicleController above it.")
	# The one mesh inside the body .glb. Taken by search rather than by path so a
	# regenerated asset can rename it, which `tools/make_vehicle.py` decides.
	var found: Array[Node] = find_children("*", "MeshInstance3D", true, false)
	if not found.is_empty():
		_body = found[0] as MeshInstance3D
	assert(_body != null, "VehicleLamps found no MeshInstance3D to switch.")
	# Belt and braces, because asserts are stripped from release builds: without
	# this a mis-wired scene crashes on the first frame of an exported build
	# rather than driving around with dark lamps.
	set_physics_process(_car != null and _body != null)
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
		# mesh is: the scene owns where the beam sits and how far it reaches, and a
		# car without one still switches its lenses.
		var beams: Array[Node] = _car.find_children("*", "SpotLight3D", true, false)
		if not beams.is_empty():
			_beam = beams[0] as SpotLight3D
			_beam_range_m = _beam.spot_range
	read_rig()
	# Applied once here rather than waited for: `_apply_beam` only runs on a
	# change of state, and the state a car starts in is a change from nothing.
	_apply_beam()


## Re-read the scene's lighting rig.
##
## ⚠️ **Public and called once, for the same reason `SunGlint.apply` is.** This
## sun does not move — `DECISIONS.md` records night as a *switch between two
## static rigs*, not a cycle — so re-reading it every tick would recompute one
## constant for the life of the process. Whatever performs that switch owes both
## this call and the glint's.
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
	var sun: DirectionalLight3D = SunGlint.find_sun(self)
	if sun == null:
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
	_night = sun.light_energy <= night_energy or _sun_toward.y <= 0.0


func _physics_process(delta: float) -> void:
	# The threshold to start turning; TURN_RELEASE's share of it to stop.
	var leaving: float = steer_threshold * TURN_RELEASE
	var side: int = 0
	if _car.steer_ratio > (leaving if _turn_side > 0 else steer_threshold):
		side = 1
	elif _car.steer_ratio < -(leaving if _turn_side < 0 else steer_threshold):
		side = -1

	# Straightening or swapping sides restarts the hold, and takes the blink
	# phase with it so the next turn's first flash is a lit one.
	if side != _turn_side:
		_turn_held_s = 0.0
		_blink_phase = 0.0
	_turn_side = side
	if side != 0:
		_turn_held_s += delta

	var indicating: bool = side != 0 and _turn_held_s > steer_hold_s
	if indicating:
		_blink_phase = fmod(_blink_phase + delta * blink_hz, 1.0)
	else:
		_blink_phase = 0.0
	# One phase for both sides rather than a flasher each. They are never both
	# live — `side` is one number — so the only thing a second phase could
	# express is a hazard flash, which nothing asks for.
	var flash: float = 1.0 if _blink_phase < blink_duty else 0.0

	# `CIRCUIT_*` order less one: x brake, y reverse, z indicator left, w right.
	#
	# ⚠️ Brake and reverse are asked of the car, not worked out from the pedal.
	# One button serves both and which one the player gets depends on the car's
	# speed — so at a standstill with the pedal held the *reverse* lamps light,
	# because reverse is what the pedal is asking for. That is the controller's
	# rule and this reads it rather than restating it.
	var lit := Vector4(
		1.0 if _car.is_braking() else 0.0,
		1.0 if _car.is_reversing() else 0.0,
		flash if indicating and side < 0 else 0.0,
		flash if indicating and side > 0 else 0.0,
	)
	_body.set_instance_shader_parameter(PARAMETER, lit)

	_settle(delta)
	# `CIRCUIT_*` order less one again, continuing into the second vector:
	# x side lamps, y head lamps, z and w unwired.
	#
	# ⚠️ **The side lamps stay lit under the main beams rather than handing over
	# to them**, which is both what a car does — position lamps do not go out
	# when the headlamps come on — and what makes the ladder legible. Swap them
	# and the two states are a different pair of lamps at the same count, which
	# reads as a flicker; stacked, the nose visibly gains a lamp.
	var front := Vector4(
		1.0 if _lighting != Lighting.SUN else 0.0,
		1.0 if _lighting == Lighting.DARK else 0.0,
		0.0,
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
		_probe_due_s += 1.0 / probe_hz
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
	_seen_held_s += delta

	# Which hold applies is decided by the *direction* of the change, which is
	# what `Lighting` being ordered buys — see `light_hold_s` for why the two are
	# deliberately far apart.
	if _seen == _lighting:
		return
	var hold: float = dark_hold_s if _seen > _lighting else light_hold_s
	if _seen_held_s >= hold:
		_lighting = _seen
		_apply_beam()


## Point the thrown light at whatever `_lighting` now says.
##
## ⚠️ **Called on a change of state, not every tick, and that is the one place
## in this file where it matters.** The lens writes are per-instance shader
## values measured at tens of nanoseconds and are left unguarded; a light is a
## different animal — moving one dirties it for the renderer, and `_lighting`
## changes at most once per hold, which is a third of a second at its very
## fastest. Writing it 60 times a second would be 180 identical writes for every
## one that says anything.
func _apply_beam() -> void:
	if _beam == null:
		return
	# Hidden rather than dimmed to nothing. A zero-energy light is still a light
	# the renderer gathers, culls and loops over per object, and "off" here means
	# a car in daylight — which is most cars, most of the time.
	_beam.visible = _lighting != Lighting.SUN
	if not _beam.visible:
		return
	var share: float = 1.0 if _lighting == Lighting.DARK else sidelamp_beam
	_beam.light_energy = beam_energy * share
	# Reach is scaled with brightness rather than held. A dim lamp that still
	# reaches 40 m lights a far kerb it could never really touch, which reads as
	# the road brightening on its own rather than as the car lighting it.
	_beam.spot_range = _beam_range_m * share


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
	var origin: Vector3 = _car.global_position + Vector3.UP * probe_height_m

	# ⚠️ **World up, not the car's.** "Is there sky above me" is a question about
	# the world, and a car mid-drift or cresting a ramp is still under open sky —
	# probing along the body's own up would switch the main beams on every time
	# the taxi leaned far enough to aim its roof at the tower beside it.
	_probe.from = origin
	_probe.to = origin + Vector3.UP * cover_probe_m
	if not space.intersect_ray(_probe).is_empty():
		return Lighting.DARK

	_probe.to = origin + _sun_toward * sun_probe_m
	if not space.intersect_ray(_probe).is_empty():
		return Lighting.SHADOW
	return Lighting.SUN
