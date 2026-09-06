class_name VehicleLamps
extends Node3D
## Switches the taxi's lamp circuits from what the car is doing (`P3-11d`).
##
## The body is one merged primitive, so there is no lamp *node* to show or hide.
## `tools/make_vehicle.py` stamps each lens with a circuit id in `UV.x` and
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

@export_group("Indicators")

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
##
## The cost is that the lamp is late by exactly this much, which is fine — a real
## driver indicates before turning and this car indicates after, so it is already
## a read-out of what the car is doing rather than a signal of intent.
##
## ⚠️ **0.3 rather than the 0.5 this shipped at, on the user's call** — the lamp
## read as late from the chase camera. That buys back 0.2 s of the lateness above
## and spends it on the other side of the same trade: a flick round a parked
## lorry now has to be shorter than a third of a second to stay dark, where it
## had half a second before. What still refuses a straight-line correction is
## `steer_threshold`, which rejects on *amplitude* rather than on duration — the
## hold was never the only guard, which is why it can be shortened without the
## indicators strobing.
@export_range(0.0, 3.0, 0.05) var steer_hold_s: float = 0.3

@export_group("Roof sign")

## How hard the illuminated box on the roof burns.
##
## ⚠️ **The one circuit on this car that answers to neither the driver nor the
## light, and that is what it is for.** A roof sign says the car is a taxi and
## whether it is in service; it is not a read-out of steering, of the pedal, or
## of whether the sky is shut out. Nothing simulates a hire state yet — there is
## no fare system on the car — so it holds on, which is a taxi plying for hire.
##
## ⚠️ **A level rather than a switch, and the reason is the one thing every other
## circuit here wants and this one must not have: bloom.** `lamp_emission` is 1.6
## against `clean_daylight.tres`'s glow threshold of 1.0, so a lens driven to 1.0
## carries a halo — which is what makes a brake lamp read as a lamp rather than
## as paint, and is exactly what makes a roof sign read as a headlamp bolted to
## the roof. Shipped full, in sun, it was reported as precisely that.
##
## Under about **0.63** the emission lands below the threshold and the sign
## brightens without glowing, which the shader's own note calls "merely a
## brighter swatch" — a fault for a lamp and the whole brief for a sign. 0.45
## sits clear of the knee rather than on it, so the tonemap has room before the
## halo comes back.
##
## ⚠️ **This is not the place to make the sign dimmer in daylight.** A level that
## tracked `_lighting` would put the sign back on the light ladder, which is the
## one thing the paragraph above refuses. Whatever ends up owning the hire state
## writes this; the sun does not.
@export_range(0.0, 1.0, 0.05) var sign_lit: float = 0.45

@export_group("Light probe")

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

@export_group("Thrown beams")

## What share of the beam the side lamps throw, in energy and in reach.
##
## ⚠️ **The only beam dial here, because the scene owns the rest.** How bright a
## lamp is and how far it reaches are properties of the *lamp*, authored beside
## its position and its cone angle in `taxi.tscn` and read once in `_ready` —
## which is what lets a roster car carry a dimmer or narrower beam without a
## second export. This is the one number that belongs to the *state* rather than
## to the fitting: what `SHADOW` does to whatever the lamp was authored at.
##
## ⚠️ It shipped the other way round for a moment, and the asymmetry was silent:
## reach came from the scene while energy came from an export, so the authored
## `light_energy` was overwritten before the first frame and editing it did
## nothing at all.
##
## ⚠️ **Not zero, and not much above it.** Position lamps exist to be *seen*, not
## to see by, so a side lamp that lights the road as far as a headlamp erases the
## difference the two circuits were split to express. A short dim pool says "lit,
## but not driving on it".
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
## only 8 spot lights per object and `roads.glb` is one object, so beams are a
## rationed resource rather than a per-car decision — see `beam_budget.gd`. A car
## that assumed the slot and was later denied would light one frame of road it
## had no budget for.
var _beams_granted: bool = false


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
		# mesh is: the scene owns where each beam sits and how far it reaches, and
		# a car without any still switches its lenses. Every spot found is taken,
		# so adding or removing a lamp is a scene edit and nothing else.
		for node: Node in _car.find_children("*", "SpotLight3D", true, false):
			var beam := node as SpotLight3D
			_beams.append(beam)
			_beam_ranges_m.append(beam.spot_range)
			_beam_energies.append(beam.light_energy)
	read_rig()
	_join_budget()
	# ⚠️ **This call can only ever put the beams *out*, and that is the point.**
	# Both `_lighting` and `_seen` start at `SUN`, so there is no state a car
	# could boot into that this would light. What it is for is the scene: a car
	# authored with `visible = true` on its lamps — the obvious mistake to make
	# when adding one to a roster model — would otherwise drive in daylight with
	# its beams on until the first state *change* happened to correct it, which
	# on a sunny route is never.
	_apply_beam()


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
	if _beams.is_empty():
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
		1.0 if _lighting != Lighting.SUN else 0.0,
		1.0 if _lighting == Lighting.DARK else 0.0,
		sign_lit,
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
			# The beams read `_seen` as well as `_lighting`, so they move here
			# too — still at the probe rate rather than the tick rate.
			_apply_beam()
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
	var share: float = 1.0 if throwing == Lighting.DARK else sidelamp_beam
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
