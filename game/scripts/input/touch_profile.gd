class_name TouchProfile
extends Resource
## How far a thumb travels, as data (`P2-4`).
##
## CLAUDE.md hard rule 4: tuning values are data, never constants in code. This
## script declares the schema and nothing else — the numbers live only in
## `game/tuning/touch.tres`. Deliberately no defaults here, on the convention
## `HandlingProfile`, `StreamingProfile` and `HudLayout` all follow: an
## `@export` with a default is a second copy of the tuning table, and a second
## copy drifts.
##
## 🔴 **These numbers cannot be picked at a desk and that is why they are a
## file.** `Q83` closes by saying so, and `P2-4`'s review is blocked on `P0-3b`
## for the handset that could settle them. What ships today is a first guess
## that someone re-seeds with a thumb; a constant in `input_router.gd` would
## make that a code change, on the one axis of this project where the person
## qualified to judge is holding a phone rather than an editor.
##
## ⚠️ **Every number here is in DESIGN units, not device pixels**, exactly as
## `hud_layout.tres`'s rects are — `project.godot` sets `canvas_items` stretch
## at 1920x1080, and input arrives already transformed into that frame. A value
## reasoned about as physical millimetres on a particular panel is wrong on
## every other panel.
##
## ⬜ **The handbrake threshold and its hysteresis belong here and are not
## declared.** `Q83` settles that the handbrake is a held offset on thumb 2 with a
## larger distance to enter than to leave, and `Q97` defers building it. The
## file is the place they land; leaving them undeclared rather than guessed
## keeps `Q83`'s "no desk can pick them" honest, and an unread export would read
## as a scheme that exists.

## Sideways travel from the touch origin that means full lock, in design units.
##
## Seeded at a quarter of `touch_zone_left`'s 560-unit width, so full lock is
## reachable from a thumb landing anywhere in the middle half of its own zone
## without the finger leaving the screen. ⚠️ **A thumb may travel outside its
## zone and the axis keeps reading** — the zone is where a finger is *claimed*,
## not a box it is confined to, which is `Q80`'s zone-versus-thumb distinction
## arriving in the input code.
@export_range(10.0, 600.0, 1.0) var steer_travel_px: float

## Travel above or below the touch origin that means full throttle or full
## brake, in design units.
##
## ⚠️ **One number for both halves, and that is a claim rather than a
## convenience**: `Q83` makes `brake_reverse` the negative half of one
## longitudinal axis, so an asymmetric pair would make the same physical
## gesture mean different amounts in the two directions and put the coast point
## somewhere the thumb cannot feel.
##
## Smaller than `steer_travel_px` because a phone held in landscape has less
## vertical room under a thumb than horizontal, and because steering is the
## precision control of the two — full throttle wants to be easy to hold.
@export_range(10.0, 600.0, 1.0) var drive_travel_px: float

## Travel below which a finger is treated as stationary, in design units.
##
## A resting thumb is never quite still: without this, a stationary finger
## trickles a percent or two of lock into a car that is meant to be going
## straight, and the player is fighting an input they cannot see. Applied as a
## dead band around the origin on both axes.
##
## ⚠️ **Not the same thing as `project.godot`'s 0.2 action deadzones and much
## smaller.** Those clip a gamepad stick's resting noise out of a 0-1 strength;
## this clips a fingertip's tremor out of a *distance*, before any normalising
## happens. `Q97` records why the touch path cannot go through the action map
## at all — that 0.2 would silently delete the whole first fifth of every
## thumb's travel.
@export_range(0.0, 60.0, 0.5) var jitter_deadzone_px: float

## The shape of the steering thumb's response: the lock is the share of the
## usable travel to this power (`Q220`). 1 is linear; 2 gives a quarter of the
## lock at half the travel, so a small movement about the landing point is a
## small correction, while full travel is still full lock at the same reach.
##
## Steering only. The pedals stay linear: nobody has asked for a throttle that
## is harder to feather, and a curve there would move the coast point's feel.
##
## ⚠️ **An input assist, per input method** (`Q210`): the keyboard has its own
## `curve` in `keyboard_steer.tres` and the car never sees which device steered.
## A thumb that is too quick is answered here, never on a car dial.
@export_range(1.0, 4.0, 0.1) var steer_curve: float

## The same curve for the player who asks for a gentler or a sharper thumb
## (`Q223`, `ControlOptions.STEERINGS`); `steer_curve` is the one between.
## Gentle is the larger power: less lock for the same small movement.
@export_range(1.0, 4.0, 0.1) var steer_curve_gentle: float
@export_range(1.0, 4.0, 0.1) var steer_curve_sharp: float

## Seconds the steering thumb takes to add full lock with the car at its
## limiter: the thumb's own slew at speed (`InputRouter.steer_for`). The limit
## grows from none at rest on the square of the car's share of its limiter, as
## the keyboard's `attack_at_top_s` does and for its reason (`Q174`): a thumb
## thrown across at 120 kph is the full-lock swap that slid the car on a key.
## Easing off is never slewed, nor a countersteer or drift mode. 0 is off.
@export_range(0.0, 5.0, 0.05, "suffix:s") var steer_attack_at_top_s: float

## Seconds the steering takes to come back from full lock to centre once the
## thumb lifts, with the car at its limiter (`Q238`). The return is in
## proportion to the car's speed, as a real car's wheel straightens itself the
## harder the faster it rolls: twice this at half the limiter, and at a
## standstill the wheel stays where the thumb left it. A thumb landing again
## takes the wheel up from where it is. 0 is off: the wheel is at centre the
## moment the thumb lifts, at any speed.
@export_range(0.0, 2.0, 0.005, "suffix:s") var steer_return_at_top_s: float

## The steering wheel hangs from the thumb (`Q238`): where the thumb lands is
## its twelve o'clock, and its middle is this many design units straight below.
## The radius it is drawn at, and the one a thumb going round it is read on.
@export_range(10.0, 400.0, 1.0) var wheel_radius_px: float

## The radius round the wheel's middle inside which a moving thumb turns
## nothing. A finger on the hub has no bearing worth reading: a millimetre
## across it is half a turn.
@export_range(0.0, 200.0, 1.0) var wheel_hub_px: float

## The degrees a thumb goes round the wheel's middle for full lock, on a
## spun wheel (`Q251`), and the angle the drawn wheel turns at full lock on
## either: the rim keeps up with a spinning finger.
@export_range(30.0, 720.0, 1.0, "suffix:°") var spin_lock_deg: float

## Path to the shipped table. Named here so `input_router.gd` and
## `verify_input.gd` cannot end up loading two different files — a check that
## names its own path can go green while the game reads something else.
const PATH: String = "res://tuning/touch.tres"


## Steering, -1.0 (full left) to 1.0 (full right), from a thumb's travel.
##
## Deadzoned and then normalised over the travel **beyond** the dead band, so
## the axis leaves zero smoothly. Subtracting the band after normalising would
## instead make the input jump to `jitter/travel` the moment it moves at all,
## which is the same discontinuity a raw dead band has and is why gamepad
## deadzones are written this way too. Then shaped by `steer_curve`, about
## centre and with the sign kept, so the ends and the dead band do not move.
##
## `curve` is the power, `curve_for` the player's pick of one (`Q223`): handed
## in, so the router reads the pick when it changes and not on every tick.
func steer_from(offset_px: float, curve: float) -> float:
	return shape(steer_share(offset_px), curve)


## The share of the steering travel a thumb `offset_px` sideways of its landing
## has used, -1.0 to 1.0: `steer_from` before its curve. The wheel's POSITION,
## which the router carries between touches (`Q238`).
func steer_share(offset_px: float) -> float:
	return _axis_from(offset_px, steer_travel_px)


## The steering a wheel at `share` of its travel gives: the share to the power
## `curve`, about centre and with the sign kept.
func shape(share: float, curve: float) -> float:
	# A curve under 1 is a `.tres` missing the key (0.0 would make every touch
	# past the dead band full lock); read as linear, and `verify_input.gd`
	# refuses the file.
	return signf(share) * pow(absf(share), maxf(curve, 1.0))


## The curve for `steering`, one of `ControlOptions.STEERINGS`; anything else
## reads the one between.
func curve_for(steering: String) -> float:
	match steering:
		ControlOptions.GENTLE:
			return steer_curve_gentle
		ControlOptions.SHARP:
			return steer_curve_sharp
	return steer_curve


## The longitudinal axis, -1.0 (full brake or reverse) to 1.0 (full throttle).
##
## ⚠️ **Negated, and the negation is the whole of the mapping.** Screen Y grows
## downward and the thumb pushes *up* to go, so a sign error here reads as a
## car that brakes when asked to accelerate — which is a frame nobody will
## misread, but only once someone drives it.
func drive_from(offset_px: float) -> float:
	return _axis_from(-offset_px, drive_travel_px)


func _axis_from(offset_px: float, travel_px: float) -> float:
	# Subtracted from the magnitude and the sign put back, so the band is
	# symmetric about the origin. ⚠️ **The guard below is what returns 0 for a
	# centred thumb, not `signf`** — `jitter_deadzone_px` is non-negative, so an
	# offset of 0 always fails it and the sign is never consulted. Reading it the
	# other way round is how the guard gets "simplified" away by someone who
	# believes the sign is handling that case.
	var beyond: float = absf(offset_px) - jitter_deadzone_px
	if beyond <= 0.0:
		return 0.0
	# Guards a `.tres` whose travel is at or below the dead band, which would
	# otherwise divide by zero or invert. The range hints above cannot express
	# "greater than jitter_deadzone_px"; `verify_input.gd` asserts it of the
	# shipped file, and this keeps a bad edit from crashing the car instead.
	var usable: float = maxf(travel_px - jitter_deadzone_px, 1.0)
	return clampf(beyond / usable, 0.0, 1.0) * signf(offset_px)
