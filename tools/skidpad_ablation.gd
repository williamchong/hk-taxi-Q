## Grades the shipped handling model on `skidpad.tscn` — fifteen manoeuvres,
## seven tables, no human at the keyboard.
##
##     godot --headless --path game --script "$PWD/tools/skidpad_ablation.gd"
##     godot --headless --path game --script "$PWD/tools/skidpad_ablation.gd" -- --only=drift
##
## **Why this exists.** Every handling figure in `docs/PROGRESS.md` came from a
## throwaway probe that was deleted before anyone could question it, and one of
## them was published from `city_drive.tscn` and had to be withdrawn — a 0.14°
## micro-gradient there is worth the whole quantity under test (`P0-5b/c/d`).
## This is the repeatable version. Run it before and after a change to
## `VehicleController`'s drive model or `handling.tres` and paste both tables.
##
## **It grades, it does not check.** No thresholds, no pass/fail, no place in
## `tools/check.sh` — the numbers are the output, and what they should be is a
## design question. It exits non-zero only when the run itself broke.
##
## Lives in `tools/` rather than `game/tools/` for the reason `driver.gd` gives:
## agent tooling stays out of the exported PCK. `--script` resolves relative
## paths against `res://`, so the absolute path above is not optional.
##
## Needs no generated city. `skidpad.tscn` builds its ground from
## `greybox_wanchai.json`, which is committed, so this runs on a fresh clone.
extends SceneTree

const DEFAULT_SCENE: String = "res://scenes/dev/skidpad.tscn"

## Every manoeuvre, in table order.
const MANOEUVRES: PackedStringArray = [
	"corner",
	"liftoff",
	"drift",
	"tap",
	"brake",
	"coast",
	"wall",
	"lift",
	"hold",
	"catch",
	"turn",
	"turnin",
	"flick",
	"trailbrake",
	"handbrake",
]
## `turn`: the street's 90° drift (`Q153`, the user's street report). The tap,
## steering and throttle held, then at `TURN_AT_DEG` of heading the player ends
## it one of these ways; the row reads the heading the car comes to rest on.
## `off` lets the steering go with the throttle held, `lift` lets both go,
## `counter` goes to full opposite lock until the slip is under the threshold.
const TURN_ENDS: PackedStringArray = ["off", "lift", "counter"]
const TURN_AT_DEG: float = 45.0
## The heading rate under which, with the slip under the threshold, the turn
## reads as over.
const TURN_SETTLED_DPS: float = 10.0
const TURN_S: float = 6.0
## The rows that ask whether a slide can be KEPT (`Q152`), printed in their own
## table so the handling table keeps the shape every earlier pair was pasted in.
## `lift` is `tap` with the throttle lifted at `LIFT_AT_S`: `Q85` measured the
## shipped slide dying there, 21.8° to 7.3°. `hold` is `tap` with a driver on
## the wheel after the release — `_countersteer`, what a player does — so its
## `longest` column is the one to set against `SkillProfile.drift_min_s`, the
## continuous dwell the fare pays on.
##
## `ride` is `tap` read in this table: the player's own input — the tap, the
## steering held into the turn, the throttle held — with no driver on the
## wheel, so its `longest` is what a player gets without countersteering. Not
## simulated twice: `tap`'s result is printed again under this name, and
## `--only=ride` runs `tap`.
const SUSTAIN_MANOEUVRES: PackedStringArray = ["lift", "hold", "ride"]
## When `lift` lets the throttle go, and how long after it the slip is read.
const LIFT_AT_S: float = 1.0
const AFTER_LIFT_S: float = 0.5
## `liftoff`: `corner`'s input, full lock and the throttle, with the throttle
## lifted at `LIFT_AT_S` and no drift button — whether a lift in a fast turn
## pivots the car. Read beside `corner`, its control, in these windows around
## the lift (seconds from it): a radius that falls after the lift on `liftoff`
## and not on `corner` is the pivot, not the speed it sheds.
const LIFTOFF_WINDOWS_S: Array[Vector2] = [
	Vector2(-0.5, 0.0), Vector2(0.0, 0.25), Vector2(0.25, 0.5), Vector2(0.5, 1.0), Vector2(1.0, 2.0)
]
## The techniques a driver brings (`P3-54`, `Q153`), each read in windows from
## its own input against a control that differs from it by that input alone:
## `flick` and `handbrake` against `corner`, `trailbrake` against `turnin`.
## `--only=technique` runs the three and their controls.
##
## `flick`: full lock LEFT for `FLICK_S` (or each of `--flick-s=`, a row per
## feint, labelled with it), then full lock right held, no drift button — a
## feint the other way, then in. `@held` keeps the throttle down
## through the feint; `@lift` lifts it for the feint and puts it back at the
## turn-in, the Scandinavian flick `Q85` says the shipped car cannot do;
## `@brake` holds the brake through the feint instead, the real flick's light
## brake (`Q153`'s research), and the throttle on at the turn-in.
## `handbrake`: `corner`'s input with the drift button tapped `HANDBRAKE_AT_S`
## into the turn — `tap` presses it with the steering from a straight line,
## this with the car already turning. `@held` keeps the throttle down, `@lift`
## lifts it at the press. `trailbrake`: the brake and full lock right for
## `TRAIL_S`, then the brake off and the throttle on. `turnin` is its control:
## the same steering and the same throttle after `TRAIL_S`, no brake. 🔴 Not
## `corner`: a car that sheds speed turns tighter for that alone (`Q153`'s
## `liftoff` round), so against a throttled corner the brake would be credited
## with the speed it loses — read slip and turn rate, never radius.
const TECHNIQUES: PackedStringArray = ["flick", "trailbrake", "handbrake"]
const TECHNIQUE_VARIANTS: Dictionary = {
	"flick": ["held", "lift", "brake"], "handbrake": ["held", "lift"]
}
const TECHNIQUE_CONTROL: Dictionary = {
	"flick": "corner", "trailbrake": "turnin", "handbrake": "corner"
}
const FLICK_S: float = 0.35
const TRAIL_S: float = 0.6
const HANDBRAKE_AT_S: float = 0.5
## Seconds from each technique's input. `+0.00..+0.50` is the window `Q153`'s
## bars read; the last is everything after the input the manoeuvre holds.
const TECHNIQUE_WINDOWS_S: Array[Vector2] = [
	Vector2(-0.25, 0.0), Vector2(0.0, 0.5), Vector2(0.5, 1.0), Vector2(1.0, 2.0), Vector2(0.0, 3.5)
]
## `catch`: how far the slide's angle must fall off its running peak before
## the tool reads the peak as passed and countersteers.
const CATCH_DROP_DEG: float = 0.5
## `catch`: the heading rate, the other way, past which the car reads as
## turning against the drift (`turns`). Over zero so a tick's jitter at the
## reversal is not the event.
const TURN_DPS: float = 5.0
## `catch`: the share of the lock at which the wheel reads as there (`to lock`).
const FULL_LOCK_SHARE: float = 0.99
## `hold`'s driver: the slip it steers for, and its two gains. A proportional
## term on the slip's error from the target and a damping term on how fast the
## slip is moving, both over the target so the gains are unitless; full lock
## either way at most. ⚠️ **The driver is the tool's, never the car's.** A
## slip setpoint in the controller would make `secs>thr` grade the button
## (`Q72`); in the harness it plays the human, and the car still has to allow
## the slide. Both cars are graded by the same driver.
##
## ⚠️ **20°, because the car cannot catch more.** `_update_steering` narrows the
## lock with speed — 16.4° at 63 kph — so a front tyre can point along a slide
## of about that plus its own peak slip angle and no further. Aimed at 30° the
## driver was asking for a catch the rack does not have, and every overshoot
## read as a spin that no dial could have prevented.
const HOLD_TARGET_DEG: float = 20.0
const HOLD_GAIN: float = 2.0
const HOLD_DAMPING_S: float = 0.25
## How hard `hold`'s driver lifts the throttle as the slip passes the target:
## full throttle at the target, none at `1 / HOLD_LIFT_GAIN` targets over it.
## Feathering the throttle is half of holding a slide, and a driver that only
## steers grades a car on a technique nobody drives with.
const HOLD_LIFT_GAIN: float = 2.0
## What `drift`, `tap`, `lift` and `hold` press; they differ in when they let go.
const DRIFT_ACTIONS: Array[StringName] = [&"accelerate", &"steer_right", &"drift"]
## The wall manoeuvre's angles, in degrees between the car's travel and the
## wall's face: 90 is head-on, 10 a brush. `--wall-deg=` overrides; each
## angle is a row. What it grades is `P3-50`'s penalty tiers — the controller's
## impact latch against the geometric approach speed — and it is the one
## manoeuvre that brings its own obstacle, since the pad is kept clear of
## every building on purpose (`skidpad.md`).
const DEFAULT_WALL_DEG: Array[float] = [10.0, 30.0, 90.0]
## `catch`: the tap, then full OPPOSITE lock held for each of these seconds
## from the tick the slide's angle stops growing, then the wheel let go with
## the throttle still down — a keyboard player's countersteer, timed as well
## as it can be. Asks whether the car swings the other way (`snap`, the peak
## slip of the opposite sign after the catch) because the countersteer was
## held too long (a timing fault: `snap` grows with the seconds) or because
## the car does it on any catch (a tuning fault: `snap` at the shortest
## hold). A row per value, like the wall's angles; never swept.
const DEFAULT_CATCH_S: Array[float] = [0.1, 0.2, 0.4, 0.8]
## How far ahead of the car, at the end of the run-up, the wall is stood.
## Close enough that the entry speed is the impact speed, far enough that the
## body is not inside it when it appears.
const WALL_AHEAD_M: float = 12.0
## The slab: long so a brush at 10° still meets it, tall so the car cannot
## jump it, thick so a 100 kph body cannot tunnel it in a tick.
const WALL_SIZE := Vector3(240.0, 4.0, 1.0)
## Seconds sampled after the first contact, so `exit kph` is what the arcade
## response left and not the tick of the hit.
const WALL_AFTER_S: float = 1.0

## The subset that can possibly move when a `DRIFT_FIELD_PREFIX` field does — the
## only ones such a sweep re-runs. Nothing else holds the drift button, so nothing
## else reaches `VehicleController._apply_drift`.
const DRIFT_MANOEUVRES: PackedStringArray = [
	"drift", "tap", "lift", "hold", "catch", "turn", "handbrake"
]

## Name prefix marking a field whose effect is confined to the drift branch.
##
## ⚠️ **This decides whether a sweep re-runs three extra manoeuvres or reprints
## the first value's rows under later labels.** `drift_*` reaches nothing but
## `_apply_drift`, so `corner`, `brake` and `coast` cannot move and re-running
## them is 13.5 s of simulation per value to reproduce rows already printed. Any
## other field — `engine_force`, `mu` — moves all five, and skipping them
## would dress stale rows up as measurements of a value never applied to them.
const DRIFT_FIELD_PREFIX: String = "drift_"

## The profile field `secs>thr` counts against.
##
## ⚠️ **This is the design target, and it is NOT a tuning knob.** The knob is
## whatever `_sweep_field` names; the threshold is what that knob is graded
## against. Lower it to make `seconds_above_deg` look better and the column
## becomes `Q58`'s `drawn_gauge_m` — a number bounded by the bar it is measured
## against, which cannot report the thing it exists to report. Read through `get()` and guarded
## by `in` for `_sweep_field`'s reason: `set()`/`get()` swallow a rename
## silently.
const SLIP_THRESHOLD_FIELD: StringName = &"drift_slip_threshold_deg"

## `HandlingProfile` fields the car pushes onto its body and wheels once, in
## `_ready`, and never reads again. 🔴 Refused by `--sweep`: set live they
## change nothing, and every row would come back identical under a distinct
## label — the published table of numbers nobody measured. The body's own
## values are swept through `BODY_SWEEP_PREFIX` instead.
const READY_ONLY_FIELDS: PackedStringArray = [
	"gravity_scale",
	"centre_of_mass_offset_y",
	"suspension_frequency_hz",
	"suspension_damping_ratio",
	"suspension_rest_length_m",
	"suspension_travel_m",
	"suspension_max_force_n",
	"wheel_radius_m",
]
## `--sweep=body.<field>=...` writes the car's rigid body rather than a table,
## live, for the values `READY_ONLY_FIELDS` cannot sweep (`P3-54`):
## `center_of_mass_y` (height; the table's `centre_of_mass_offset_y`),
## `center_of_mass_z` (along the car, + toward the rear) and `gravity_scale`.
## A probe for what moves the car, never a tuning route — a value worth
## keeping goes into `handling.tres`, where the car reads it.
const BODY_SWEEP_PREFIX: String = "body."
## The car's systems a `<system>.<field>` sweep may name (`Q155`): only these,
## so `profile.` or `tyre.` cannot slip past the refusals the bare names get.
const SYSTEM_TABLES: PackedStringArray = [
	"traction_control",
	"stability_control",
	"drift_mode",
	"handbrake",
	"rev_limiter",
	"arcade_aids",
	"anti_lock_brakes",
]
const BODY_FIELDS: PackedStringArray = ["center_of_mass_y", "center_of_mass_z", "gravity_scale"]

## Default seconds of full throttle before every manoeuvre, to reach a working
## speed. Long enough to be well past the initial squat, short enough that the car
## is nowhere near the 140 kph limiter where the drive taper distorts things.
##
## ⚠️ **Overridable since `--run-up`, and a fixed entry speed is exactly what hid
## a defect.** Every other column is only comparable because entry is identical
## across rows, so this stays constant *within* a run — but a dial whose effect
## depends on speed cannot be graded at one speed at all, and the drift's yaw
## assist was tuned at the 63 kph this produces and then applied at 84, where the
## same tap spins the car. Vary it between runs, never expect two run-ups to be
## comparable on anything but the trend.
const DEFAULT_RUN_UP_S: float = 4.0

## Fraction of `max_speed_kph` above which the controller's drive taper is easing
## engine force off, so an entry speed inside it grades the taper alongside
## whatever is under test.
##
## ⚠️ **A deliberate copy of `VehicleController.TOP_SPEED_TAPER`**, which this
## file cannot name: `--script` tools do not get `class_name` resolution, the same
## constraint that keeps every controller call here behind `call()`. Warned about
## rather than refused — this tool grades and does not check — but a run-up that
## reaches the band needs saying, because nothing in the table shows it.
const TOP_SPEED_TAPER: float = 0.15

## Seconds the manoeuvre itself is held and measured.
const MANOEUVRE_S: float = 4.0

## Seconds a reset car is left alone before the run-up, so one manoeuvre is not
## measured against the suspension transient of the last.
const SETTLE_S: float = 0.5
## Seconds the tyre-model car stands before its rebuilt loads are read (`Q152`).
const LOAD_SETTLE_S: float = 1.5

## How long the `tap` manoeuvre holds the drift button before letting go, while
## steering stays on for the full `MANOEUVRE_S`.
##
## The pair matters more than either number. `drift` holds the button for the
## whole corner, which is what the *design* promises a player can do; `tap` uses
## it the way a driver does, to break the tail loose and then release. A model
## can pass one and fail the other, and knowing which is the whole question.
const TAP_S: float = 0.5

## How long a to-rest manoeuvre may take before it is called a failure rather
## than waited on. The coast case is the slow one: 6.5 s from 31 kph measured at
## `rolling_resistance_mps2 = 0.8`, and a regression there is exactly the fifth
## `P0-5b/c/d` bug, where the car never stopped at all.
const TO_REST_LIMIT_S: float = 30.0

## Speed under which the car counts as stopped, in kph. Matches
## `VehicleController.STATIONARY_KPH`, where one pedal stops meaning brake and
## starts meaning reverse — below this a "braking" run is accelerating backwards.
const STOPPED_KPH: float = 1.0

## Ground speed under which a slip angle is noise rather than a measurement: a
## nearly stationary car has a velocity vector pointing anywhere at all.
const SLIP_FLOOR_MPS: float = 1.0

var _only: String = ""
## The scene to grade. Configurable rather than constant so a roster car can be
## put on the same ground and spawn later. ⚠️ Never `city_drive.tscn`: a 0.14°
## micro-gradient there is worth the whole quantity under test, and a published
## figure has already had to be withdrawn over it (`P0-5b/c/d`).
var _scene_path: String = DEFAULT_SCENE
## Seconds of run-up, and so the entry speed every row is measured from. Reported
## as `entry kph` rather than requested, because the run-up is open-loop: this
## asks for seconds of throttle and the car answers with whatever speed it made.
var _run_up_s: float = DEFAULT_RUN_UP_S
## A speed to run up to instead of a time, in kph, or 0 for `_run_up_s`. Since
## `Q152`: a car with a different drive reaches a different speed in the same
## seconds, and rows only compare at one entry. Throttle until the speed is
## reached, then the manoeuvre starts on that tick.
var _entry_kph: float = 0.0
## Both run-up flags seen, which is refused rather than one silently winning.
var _entry_given: bool = false
var _run_up_given: bool = false
## Values to sweep `_sweep_field` over, or empty for whatever `handling.tres`
## ships. Set live on the loaded resource rather than by editing the file:
## nothing caches it, so it takes effect on the next tick, and a sweep that
## crashed halfway cannot leave the committed tuning holding a probe value.
##
## ⚠️ **Editing the `.tres` in a shell loop is the alternative this exists to
## avoid.** One such loop misfired on `set --`, blanked the field it was sweeping
## and published a table of all-zero rows that looked like a finding.
var _sweep: Array[float] = []
## The profile field `_sweep` writes, named by `--sweep`.
##
## ⚠️ Set through `Object.set()`, which is a **silent no-op** on a name the
## resource does not have. Rename the field and every swept row comes back
## identical, correctly labelled, and describing a value that was never applied —
## a published table of numbers nobody measured. `_measure_all` refuses the run
## instead, before any manoeuvre is simulated.
var _sweep_field: StringName = &""
var _wall_deg: Array[float] = DEFAULT_WALL_DEG.duplicate()
var _catch_s: Array[float] = DEFAULT_CATCH_S.duplicate()
## `--flick-s=`: the feint's lengths, a `flick` row per value; the bar's own
## `FLICK_S` alone unless asked, and only then are the rows labelled with it.
var _flick_s: Array[float] = [FLICK_S]
var _flick_given: bool = false
## `--catch-lift`: the catch lets the throttle go as the wheel goes over —
## the street instinct — where the default keeps it down. With the drive on,
## the rears are still spinning past the drift button and have little side
## grip to swing the car with; lifted, they regrip, and that is the pendulum.
var _catch_lift: bool = false
## `--catch-at=<s>`: countersteer at this many seconds into the manoeuvre
## instead of at the slide's peak — an EARLY catch, while the slide is still
## building. `--catch-late=<s>`: this long after the peak — a LATE one, when
## the car is already straightening on its own. 0, the default of both, is
## the peak itself; the flags refuse it.
var _catch_at_s: float = 0.0
var _catch_late_s: float = 0.0
## The slab the wall manoeuvre stood last, freed before the next row.
var _wall: StaticBody3D = null
## Slip angle `seconds_above_deg` counts against, read off the profile at boot.
## INF when the profile does not publish one, which makes the column read 0.00
## everywhere rather than inventing a bar this project never authored.
var _slip_threshold_deg: float = INF
var _failures: Array[String] = []
## ⚠️ **Typed `RigidBody3D`, and every controller method below goes through
## `call()`, because naming `VehicleController` here breaks the car.**
##
## `handling_profile.gd` states the mechanism: the controller reads the
## `InputRouter` autoload, autoloads are not registered under `--script`, and so
## resolving that class while *this* script compiles — which a type annotation
## does, in `_init`, before the first frame — fails. The failure is not loud.
## GDScript caches the broken class, `taxi.tscn` then instances a `VehicleBody3D`
## with a **null script**, and the run reports "no vehicle" while the wheels,
## which are engine classes touching no autoload, are found perfectly. Measured here before
## `driver.gd`'s duck-typing was understood to be deliberate.
var _vehicle: RigidBody3D = null
## How far behind the centre of mass the vehicle's rear axle sits, for
## `_slide_velocity`: read off the wheels here, never asked of the car.
var _rear_behind_m: float = 0.0
var _spawn: Transform3D = Transform3D.IDENTITY
var _step: float = 0.0
## Rows actually printed. The success test, because the ordinary GDScript
## failure here is not an exception this can catch: a run-time script error kills
## the coroutine where it stands, `_failures` stays empty, and `_finish` cheerfully
## exits 0 with no table. Measured — an `Array` / `Array[float]` mismatch did
## exactly that. Counting output is the only claim worth making.
var _printed_rows: int = 0
## The tyre car's wheels as `wheel_slips` / `wheel_loads_n` index them: the
## steered pair, and the rear pair split by side. Empty on a parked car (a
## tyre table with a zero key), whose columns then read "-".
var _front_i: PackedInt32Array = []
var _rear_left_i: int = -1
var _rear_right_i: int = -1


## One manoeuvre's measurements. A class rather than a Dictionary so a typo in a
## field name is a parse error instead of a null three prints later.
class Result:
	extends RefCounted

	var name: String = ""
	var entry_kph: float = 0.0
	var exit_kph: float = 0.0
	## Seconds the measured phase actually ran, which is `MANOEUVRE_S` for the
	## held manoeuvres and however long it took for the to-rest ones.
	var seconds: float = 0.0
	## Exponential speed decay, per second: `ln(entry / exit) / seconds`. The
	## same shape the coast and drag figures in `docs/PROGRESS.md` use, because
	## the coast's main term (`coast_drag_per_s`) is viscous and those numbers are
	## its rate. Godot's own damping is replaced with 0 since `Q153`.
	var decay_per_s: float = 0.0
	## Mean deceleration over the phase, in m/s². The honest figure for braking,
	## where the force is meant to be constant and a decay rate would hide that.
	var decel_mps2: float = 0.0
	## Largest angle between where the car pointed and where it was going.
	var peak_slip_deg: float = 0.0
	## Seconds spent at or above `drift_slip_threshold_deg`.
	##
	## ⚠️ **This is the statistic the game scores and `peak_slip_deg` is not.**
	## `GAME_DESIGN.md` pays drift as points *per second* above a threshold, so a
	## tune whose peak merely touches the threshold scores for ~0 s. A peak is a
	## `maxf` over one tick and cannot see duration; keep both, because dwell
	## alone cannot tell a drift from a spin and `yaw_deg` is what separates them.
	var seconds_above_deg: float = 0.0
	## Heading swept over the phase — how far round the manoeuvre brought the
	## car. Separates a drift from a spin far more clearly than slip does.
	var yaw_deg: float = 0.0
	var distance_m: float = 0.0
	## The wall rows only. `approach_kph` is the geometric speed into the
	## wall's face on the tick before contact — the row's own reading, from the
	## velocity and the normal this tool placed; `impact_kph` is what the
	## controller's latch (`take_impact_mps`) reported, the number the game
	## pays on. The two must agree, and that agreement is the column's point.
	var approach_kph: float = 0.0
	var impact_kph: float = 0.0
	## Ticks on which the latch read a hit: one wall should be one.
	var impact_ticks: int = 0
	## The longest unbroken run at or above the threshold, in seconds — the
	## dwell `SkillTracker` pays on, where `seconds_above_deg` sums every run.
	var longest_above_s: float = 0.0
	## `lift` only: the slip on the tick the throttle came up, and
	## `AFTER_LIFT_S` later. NAN on every other row.
	var slip_at_lift_deg: float = NAN
	var slip_after_lift_deg: float = NAN
	## `catch` only: when the countersteer went on after the release, the
	## slip then, the largest slip of the OPPOSITE sign after it, and the
	## slip 0.5 s after the wheel was let go. NAN on every other row.
	var catch_at_s: float = NAN
	var slip_at_catch_deg: float = NAN
	var snap_deg: float = NAN
	var slip_after_catch_deg: float = NAN
	## Heading swept while the countersteer was held, sign-corrected: negative
	## is the way the drift was turning, positive the OTHER way — a gripping
	## turn the other way once the slide is caught, which `snap_deg` (slip)
	## cannot see.
	var yaw_in_catch_deg: float = NAN
	## Every manoeuvre: when the slip first reached the threshold, and the
	## heading swept by then — a slide that starts after the corner is over is
	## no use in it.
	var slide_at_s: float = NAN
	var slide_heading_deg: float = NAN
	## `turn`: when the player ended it, the slip and speed then, and — once the
	## slip is under the threshold and the heading under `TURN_SETTLED_DPS` —
	## how long that took and the heading swept from the start of the turn.
	var turn_off_s: float = NAN
	var turn_off_slip_deg: float = NAN
	var turn_off_kph: float = NAN
	var turn_settled_s: float = NAN
	var turn_heading_deg: float = NAN
	## `catch` only, each in seconds from the tick the wheel went over, NAN
	## where it never happened: the front wheels reaching the countersteer's
	## full lock while it is held (`steer_ratio`, a share of the lock at that
	## speed), the slip falling under the threshold, and the heading first
	## turning the OTHER way faster than `TURN_DPS`. `wheel_at_turn` is the
	## share of lock on that last tick, near 0 if the turn came after the wheel
	## was let go. Together they say whether the turn the
	## other way comes from how fast the wheel arrives or from how much lock
	## it keeps once it is there.
	var to_lock_s: float = NAN
	var settled_s: float = NAN
	var turns_s: float = NAN
	var wheel_at_turn: float = NAN
	## `catch` only: seconds from the wheel going over to the car's own cap on
	## the countersteer engaging (`TyreVehicleController.catch_capped`), NAN
	## on a car without one or a catch it never capped; and the front wheels'
	## angle as the hold ends, in degrees — `steering` itself, where `wheel`
	## above is `steer_ratio`, the player's input, which the cap leaves alone.
	var capped_s: float = NAN
	var fronts_off_deg: float = NAN
	## The techniques and their controls: seconds into the manoeuvre of the
	## input the windows are read from. NAN on every other row.
	var input_at_s: float = NAN
	## Per tick on every row, read by `liftoff`'s and the techniques' tables: seconds into the manoeuvre,
	## forward speed, the heading rate into a right turn, the front wheels'
	## angle (`steering`) and the slip.
	var trace_s: PackedFloat32Array = []
	var trace_kph: PackedFloat32Array = []
	var trace_yaw_dps: PackedFloat32Array = []
	var trace_fronts_deg: PackedFloat32Array = []
	var trace_slip_deg: PackedFloat32Array = []
	## The tyre car alone, per tick, for the techniques' table (`P3-54`): the
	## most-used tyre on each axle, in multiples of its peak (1.0 the top of the
	## curve), and the rear axle's load across it, left minus right over the
	## two — positive is the left, the OUTSIDE of a right turn. NAN elsewhere.
	var trace_front_use: PackedFloat32Array = []
	var trace_rear_use: PackedFloat32Array = []
	var trace_rear_swing: PackedFloat32Array = []
	## Mean microseconds per tick in the tyre model (`Q152`), or NAN for a car
	## without one.
	var tyre_cost_us: float = NAN


func _init() -> void:
	_run.call_deferred()


func _run() -> void:
	# Autoloads are registered on the first frame, not before: the car resolves
	# `InputRouter` by path in its `_ready`, so a scene added before this returns
	# has no pedals.
	await process_frame

	if _parse_args() and await _boot():
		await _measure_all()
	_release_everything()
	_finish()


func _parse_args() -> bool:
	for arg: String in OS.get_cmdline_user_args():
		if arg == "--catch-lift":
			_catch_lift = true
			continue
		var bits: PackedStringArray = arg.split("=", true, 1)
		if bits.size() < 2 or bits[1].is_empty():
			_fail("%s needs a value, as %s=..." % [bits[0], bits[0]])
			return false
		match bits[0]:
			"--only":
				_only = bits[1]
			"--scene":
				_scene_path = bits[1]
			"--run-up":
				if not bits[1].is_valid_float():
					_fail("--run-up wants a number of seconds, got '%s'" % bits[1])
					return false
				_run_up_s = bits[1].to_float()
				_run_up_given = true
				if _run_up_s <= 0.0:
					_fail("--run-up must be positive, got %s" % _run_up_s)
					return false
			"--entry-kph":
				if not bits[1].is_valid_float() or bits[1].to_float() <= 0.0:
					_fail("--entry-kph wants a positive speed, got '%s'" % bits[1])
					return false
				_entry_kph = bits[1].to_float()
				_entry_given = true
			"--wall-deg":
				var angles: Array[float] = []
				for text: String in bits[1].split(","):
					if not text.strip_edges().is_valid_float():
						_fail("--wall-deg wants degrees, got '%s'" % text)
						return false
					var angle: float = text.to_float()
					if angle <= 0.0 or angle > 90.0:
						_fail("--wall-deg is 0 < deg <= 90, got %s" % text)
						return false
					angles.append(angle)
				_wall_deg = angles
			"--catch-at", "--catch-late":
				if not bits[1].strip_edges().is_valid_float() or bits[1].to_float() <= 0.0:
					_fail("%s wants seconds over 0, got '%s'" % [bits[0], bits[1]])
					return false
				if bits[0] == "--catch-at":
					_catch_at_s = bits[1].to_float()
				else:
					_catch_late_s = bits[1].to_float()
			"--flick-s":
				var feints: Array[float] = []
				for text: String in bits[1].split(","):
					if not text.strip_edges().is_valid_float() or text.to_float() <= 0.0:
						_fail("--flick-s wants seconds over 0, got '%s'" % text)
						return false
					feints.append(text.to_float())
				_flick_s = feints
				_flick_given = true
			"--catch-s":
				var holds: Array[float] = []
				for text: String in bits[1].split(","):
					if not text.strip_edges().is_valid_float() or text.to_float() <= 0.0:
						_fail("--catch-s wants seconds over 0, got '%s'" % text)
						return false
					holds.append(text.to_float())
				_catch_s = holds
			"--sweep":
				# Split once more, so the field name carries its own "=" separator
				# and `--sweep=drift_side_cut=0.4,0.6` reads as one flag.
				var spec: PackedStringArray = bits[1].split("=", true, 1)
				if spec.size() < 2 or spec[0].is_empty() or spec[1].is_empty():
					_fail("--sweep wants field=v1,v2,..., got '%s'" % bits[1])
					return false
				_sweep_field = StringName(spec[0])
				if not _parse_sweep_values(spec[1], "--sweep"):
					return false
			_:
				_fail("unknown argument %s" % bits[0])
				return false
	if _entry_given and _run_up_given:
		_fail("--run-up and --entry-kph both set a run-up; give one")
		return false
	return true


## `--sweep`'s values, parsed.
func _parse_sweep_values(text: String, flag: String) -> bool:
	# 🔴 One sweep per run, refused rather than merged. Two flags would append into
	# the same `_sweep` while `_sweep_field` is simply overwritten by whichever
	# parsed last, and every row would print correctly labelled with a value
	# applied to a field it was never meant for. That is the published table of
	# numbers nobody measured this whole tool exists to prevent.
	if not _sweep.is_empty():
		_fail("%s: only one sweep per run, and one is already set" % flag)
		return false
	for piece: String in text.split(",", false):
		if not piece.is_valid_float():
			_fail("%s wants numbers, got '%s'" % [flag, piece])
			return false
		_sweep.append(piece.to_float())
	return true


func _boot() -> bool:
	if not ResourceLoader.exists(_scene_path):
		_fail("no such scene: %s" % _scene_path)
		return false
	var packed: PackedScene = load(_scene_path)
	if packed == null:
		_fail("could not load %s" % _scene_path)
		return false

	root.add_child(packed.instantiate())
	await process_frame

	# Found by the method it answers to, not by its class — see `_vehicle`.
	for node: Node in root.find_children("*", "RigidBody3D", true, false):
		if node.has_method("forward_speed_kph"):
			_vehicle = node as RigidBody3D
			break
	if _vehicle == null:
		_fail("no vehicle in %s — nothing answers forward_speed_kph()" % _scene_path)
		return false
	_rear_behind_m = _rear_axle_behind_m()

	# Read back rather than taken from the scene file: `skidpad.tscn` authors the
	# spawn, but a car that has settled onto its springs for a frame is the pose
	# every manoeuvre should restart from, not the one it was dropped at.
	_spawn = _vehicle.global_transform
	_step = 1.0 / float(Engine.physics_ticks_per_second)
	if _entry_kph > 0.0:
		print("run-up:  to %.1f kph" % _entry_kph)
	else:
		print("run-up:  %.2f s" % _run_up_s)
	print("scene:   %s" % _scene_path)
	print("vehicle: %s at %s" % [_vehicle.name, _spawn.origin])
	var profile: Resource = _vehicle.get("profile") as Resource
	print("profile: %s" % ("none" if profile == null else profile.resource_path))
	if profile != null and SLIP_THRESHOLD_FIELD in profile:
		_slip_threshold_deg = profile.get(SLIP_THRESHOLD_FIELD)
		print("slip threshold: %.1f deg" % _slip_threshold_deg)
	else:
		print("slip threshold: none published — secs>thr will read 0.00")
	if _vehicle.has_method("tyre_wheels"):
		var wheels: Array = _vehicle.call("tyre_wheels")
		for i: int in wheels.size():
			var wheel: VehicleWheel3D = wheels[i]
			if wheel.use_as_steering:
				_front_i.append(i)
			elif wheel.position.x < 0.0:
				_rear_left_i = i
			else:
				_rear_right_i = i
	# `Q152`'s phase-1 gate, kept repeatable: the tyre model rebuilds each
	# wheel's load from the contact, and at rest the four must be the weight.
	# 1.5 s, not `SETTLE_S`: at 0.5 s the car is still coming down onto its springs
	# from the spawn and the four read 0.974 of the weight.
	if _vehicle.has_method("wheel_loads_n"):
		await _hold(LOAD_SETTLE_S)
		var total: float = 0.0
		for load: float in _vehicle.call("wheel_loads_n"):
			total += load
		var gravity: float = ProjectSettings.get_setting("physics/3d/default_gravity")
		var weight: float = _vehicle.mass * gravity * _vehicle.gravity_scale
		print(
			(
				"loads:   %.0f N at rest against %.0f N of weight (%.4f)"
				% [total, weight, total / weight]
			)
		)
	return true


func _measure_all() -> void:
	var results: Array[Result] = []
	var profile: Resource = _vehicle.get("profile") as Resource
	# The table a sweep writes: the handling table, or the tyre model's.
	var sweep_table: Resource = profile
	var body_field: String = ""
	# The field a system sweep writes, without its `<system>.` prefix.
	var system_field: StringName = &""
	if not _sweep.is_empty() and String(_sweep_field).begins_with(BODY_SWEEP_PREFIX):
		body_field = String(_sweep_field).trim_prefix(BODY_SWEEP_PREFIX)
		if not body_field in BODY_FIELDS:
			_fail("sweep: no body field '%s'; one of %s" % [body_field, ", ".join(BODY_FIELDS)])
			return
		print("sweeping: %s" % _sweep_field)
	elif not _sweep.is_empty() and "." in String(_sweep_field):
		# `<system>.<field>`: one of the car's systems' tables (`Q155`), named by
		# the controller's property for it, as `body.` names the rigid body.
		var parts: PackedStringArray = String(_sweep_field).split(".", true, 1)
		if not parts[0] in SYSTEM_TABLES:
			_fail("sweep: '%s' is not a system; one of %s" % [parts[0], ", ".join(SYSTEM_TABLES)])
			return
		var system_table := _vehicle.get(parts[0]) as Resource
		if system_table == null:
			_fail("sweep: the car has no system table '%s'" % parts[0])
			return
		if not parts[1] in system_table:
			_fail("sweep: %s has no '%s'" % [system_table.resource_path, parts[1]])
			return
		sweep_table = system_table
		system_field = StringName(parts[1])
		print("sweeping: %s" % _sweep_field)
	elif not _sweep.is_empty():
		if profile == null:
			_fail("a sweep needs a profile on the vehicle and there is none")
			return
		# The tyre model's table is swept the same way (`Q152`): a field the
		# handling table lacks is looked for there before the run is refused.
		var tyre: Resource = _vehicle.get("tyre") as Resource
		# 🔴 A name in both tables is refused: resolved to the handling table,
		# a sweep of the tyre model's roll point wrote a copy that car does not
		# read and printed five identical rows under five labels (`Q152`).
		if tyre != null and _sweep_field in profile and _sweep_field in tyre:
			_fail("sweep: '%s' is in both tables; rename one" % _sweep_field)
			return
		if not _sweep_field in profile and tyre != null and _sweep_field in tyre:
			sweep_table = tyre
		# See `_sweep_field`: set() would swallow a typo or a rename and print
		# a sweep of identical rows labelled with values it never applied.
		if not _sweep_field in sweep_table:
			_fail("sweep: %s has no '%s'" % [sweep_table.resource_path, _sweep_field])
			return
		# 🔴 The bar is not a knob, and generalising the flag is what made it
		# reachable. `_slip_threshold_deg` is cached at boot, so setting the field
		# per value writes something nothing reads back: every row would come out
		# identical and labelled with a distinct threshold it never measured
		# against. Structurally impossible while the swept field was a constant,
		# and only a convention once it was not. See SLIP_THRESHOLD_FIELD.
		if _sweep_field == SLIP_THRESHOLD_FIELD:
			_fail("sweep: %s is the bar, not the knob — it is read once at boot" % _sweep_field)
			return
		if sweep_table == profile and String(_sweep_field) in READY_ONLY_FIELDS:
			_fail(
				(
					"sweep: %s is read once, in _ready; sweep the body (%s%s) instead"
					% [_sweep_field, BODY_SWEEP_PREFIX, ", ".join(BODY_FIELDS)]
				)
			)
			return
		print("sweeping: %s" % _sweep_field)

	# One pass with the shipped tuning when nothing is swept. NAN is the "leave it
	# alone" marker rather than a bool-and-value pair, because it cannot be
	# confused with a value someone meant to sweep.
	#
	# Built rather than written as a ternary: `x if c else [NAN]` types the else
	# branch as a plain Array, and assigning that to an Array[float] throws at
	# run time — which killed this coroutine mid-run and still printed ABLATION OK,
	# because a dead coroutine records no failure. `_printed_rows` now catches it.
	var values: Array[float] = _sweep.duplicate()
	if values.is_empty():
		values.append(NAN)
	# See DRIFT_FIELD_PREFIX: a drift dial cannot move the other three manoeuvres,
	# anything else can.
	var field: StringName = system_field if not system_field.is_empty() else _sweep_field
	var confined: bool = String(field).begins_with(DRIFT_FIELD_PREFIX)
	for value: float in values:
		if not is_nan(value) and not body_field.is_empty():
			_set_body(body_field, value)
		elif not is_nan(value):
			sweep_table.set(field, value)
		for manoeuvre: String in MANOEUVRES:
			if not _only.is_empty() and _only != manoeuvre and not _rides(manoeuvre):
				continue
			if manoeuvre == "wall":
				# A row per angle; never swept, a wall does not take the drift
				# branch and the arcade response has no dial here to sweep.
				if not is_nan(value) and value != values[0]:
					continue
				for angle: float in _wall_deg:
					var hit: Result = await _measure(manoeuvre, "wall@%.0f" % angle, angle)
					if hit == null:
						return
					results.append(hit)
				continue
			# ⚠️ Only the two drift manoeuvres are swept **when the swept field is
			# `drift_`-prefixed** — see DRIFT_FIELD_PREFIX, which is what decides it.
			# For such a field the other three never
			# reach the field — `corner` steers, `brake` brakes, `coast` presses
			# nothing, and none of them takes the drift branch — so re-running them
			# per value burns 4.5 s of simulation each to reproduce the previous row
			# exactly, and then the `@value` suffix dresses the duplicates up as
			# distinct measurements. That is the failure this whole tool exists to
			# stop, so it must not be the tool doing it.
			var swept: bool = not is_nan(value) and (not confined or manoeuvre in DRIFT_MANOEUVRES)
			if not is_nan(value) and not swept and value != values[0]:
				continue
			if manoeuvre == "catch":
				# A row per hold, and swept like the other drift rows: the catch
				# taps the drift button, so a drift dial or a tyre field moves it.
				for hold_s: float in _catch_s:
					var label: String = "catch@%.1fs" % hold_s
					if swept:
						label += "@%.4f" % value
					var caught: Result = await _measure(manoeuvre, label, 90.0, hold_s)
					if caught == null:
						return
					results.append(caught)
				continue
			if manoeuvre in TECHNIQUE_VARIANTS:
				var feints: Array[float] = [FLICK_S]
				if manoeuvre == "flick":
					feints = _flick_s
				for variant: String in TECHNIQUE_VARIANTS[manoeuvre]:
					for feint_s: float in feints:
						var variant_label: String = "%s@%s" % [manoeuvre, variant]
						if manoeuvre == "flick" and _flick_given:
							variant_label += "@%.2fs" % feint_s
						if swept:
							variant_label += "@%.4f" % value
						var row: Result = await _measure(
							manoeuvre, variant_label, 90.0, 0.0, "", variant, feint_s
						)
						if row == null:
							return
						results.append(row)
				continue
			if manoeuvre == "turn":
				for end: String in TURN_ENDS:
					var turn_label: String = "turn@%s" % end
					if swept:
						turn_label += "@%.4f" % value
					var turned: Result = await _measure(manoeuvre, turn_label, 90.0, 0.0, end)
					if turned == null:
						return
					results.append(turned)
				continue
			var result: Result = await _measure(
				manoeuvre, "%s@%.4f" % [manoeuvre, value] if swept else manoeuvre
			)
			if result == null:
				return
			results.append(result)

	if results.is_empty():
		_fail("--only=%s matched no manoeuvre" % _only)
		return
	var handling: Array[Result] = []
	var walls: Array[Result] = []
	var sustained: Array[Result] = []
	var catches: Array[Result] = []
	var lift_rows: Array[Result] = []
	var turns: Array[Result] = []
	var techniques: Array[Result] = []
	var lifted: bool = false
	for result: Result in results:
		var manoeuvre: String = result.name.get_slice("@", 0)
		if manoeuvre in ["corner", "liftoff"]:
			lift_rows.append(result)
		if manoeuvre in ["corner", "turnin"] or manoeuvre in TECHNIQUES:
			techniques.append(result)
		if manoeuvre == "liftoff":
			lifted = true
			continue
		if manoeuvre == "turnin" or manoeuvre in TECHNIQUES:
			continue
		if manoeuvre == "wall":
			walls.append(result)
		elif manoeuvre == "catch":
			catches.append(result)
		elif manoeuvre == "turn":
			turns.append(result)
		elif manoeuvre in SUSTAIN_MANOEUVRES:
			sustained.append(result)
		else:
			if manoeuvre == "tap":
				sustained.append(_as_ride(result))
			# `--only=ride` asked for the sustain row alone.
			if not _rides(manoeuvre):
				handling.append(result)
	if not handling.is_empty():
		_print_table(handling)
	if not walls.is_empty():
		_print_wall_table(walls)
	if not catches.is_empty():
		_print_catch_table(catches)
	if not sustained.is_empty():
		_print_sustain_table(sustained)
	if lifted:
		_print_liftoff_table(lift_rows)
	if not turns.is_empty():
		_print_turn_table(turns)
	if techniques.any(func(r: Result) -> bool: return r.name.get_slice("@", 0) in TECHNIQUES):
		_print_technique_table(techniques)


## Run-up, then the manoeuvre, sampling every physics tick.
##
## The run-up is not measured and not reported: it is the same for every row in a
## run, and including it would average the manoeuvre against seconds of
## straight-line acceleration that says nothing about grip. Its *result* is
## reported, as `entry kph`, which is the number to quote when comparing runs at
## different `--run-up`.
func _measure(
	manoeuvre: String,
	label: String,
	wall_deg: float = 90.0,
	catch_s: float = 0.0,
	turn_end: String = "",
	variant: String = "",
	feint_s: float = FLICK_S
) -> Result:
	_release_everything()
	_vehicle.call("place_at", _spawn)
	if _wall != null:
		_wall.queue_free()
		_wall = null
	# A placed car has zero velocity but its wheels are still holding last
	# manoeuvre's compression until they are simulated again, and the first tick
	# after a reset lands a spring transient on the tyres. Settling first keeps
	# manoeuvre two from being measured against manoeuvre one's suspension.
	await _hold(SETTLE_S)

	Input.action_press(&"accelerate")
	if _entry_kph > 0.0:
		var first_tick: int = Engine.get_physics_frames()
		while _speed_kph() < _entry_kph:
			await physics_frame
			if float(Engine.get_physics_frames() - first_tick) * _step > TO_REST_LIMIT_S:
				_fail("%s: never reached %.1f kph" % [label, _entry_kph])
				return null
	else:
		await _hold(_run_up_s)

	var result := Result.new()
	# Named before the manoeuvre runs, not after: `_sample` reports its failures
	# through this, and during a sweep three bare `drift:` messages name no value.
	result.name = label
	result.entry_kph = _speed_kph()
	# Drained so the row's cost is the manoeuvre's, not the run-up's.
	if _vehicle.has_method("take_tyre_cost_us"):
		_vehicle.call("take_tyre_cost_us")
	# See TOP_SPEED_TAPER: entry inside the band means the drive taper is easing
	# engine force off during the manoeuvre, which no column reports.
	var max_speed: float = 0.0
	var profile: Resource = _vehicle.get("profile") as Resource
	if profile != null and &"max_speed_kph" in profile:
		max_speed = profile.get(&"max_speed_kph")
	if max_speed > 0.0 and result.entry_kph > max_speed * (1.0 - TOP_SPEED_TAPER):
		print(
			(
				(
					"  note  %s entered at %.2f kph, inside the drive taper above %.2f — "
					+ "engine force is easing off during this row"
				)
				% [label, result.entry_kph, max_speed * (1.0 - TOP_SPEED_TAPER)]
			)
		)

	match manoeuvre:
		"corner":
			await _sample([&"accelerate", &"steer_right"], MANOEUVRE_S, false, result)
		"liftoff":
			await _sample(
				[&"accelerate", &"steer_right"], MANOEUVRE_S, false, result, INF, LIFT_AT_S
			)
		"drift":
			await _sample(DRIFT_ACTIONS, MANOEUVRE_S, false, result)
		"tap":
			await _sample(DRIFT_ACTIONS, MANOEUVRE_S, false, result, TAP_S)
		"brake":
			await _sample([&"brake_reverse"], TO_REST_LIMIT_S, true, result)
		"coast":
			await _sample([], TO_REST_LIMIT_S, true, result)
		"wall":
			await _hit_wall(wall_deg, result)
		"lift":
			await _sample(DRIFT_ACTIONS, MANOEUVRE_S, false, result, TAP_S, LIFT_AT_S)
		"hold":
			await _sample(DRIFT_ACTIONS, MANOEUVRE_S, false, result, TAP_S, INF, true)
		"catch":
			await _sample(DRIFT_ACTIONS, MANOEUVRE_S, false, result, TAP_S, INF, false, catch_s)
		"turn":
			if not turn_end in TURN_ENDS:
				_fail("turn: no ending '%s'" % turn_end)
				return null
			await _sample(DRIFT_ACTIONS, TURN_S, false, result, TAP_S, INF, false, 0.0, turn_end)
		"turnin", "trailbrake":
			result.input_at_s = 0.0
			var pedal: Array[StringName] = [&"steer_right"]
			if manoeuvre == "trailbrake":
				pedal.append(&"brake_reverse")
			await _sample(pedal, MANOEUVRE_S, false, result, INF, INF, false, 0.0, "", manoeuvre)
		"flick", "handbrake":
			if not variant in TECHNIQUE_VARIANTS[manoeuvre]:
				_fail("%s: no variant '%s'" % [manoeuvre, variant])
				return null
			var technique: String = "%s@%s" % [manoeuvre, variant]
			var start: Array[StringName] = [&"accelerate", &"steer_right"]
			var release_s: float = INF
			if manoeuvre == "flick":
				result.input_at_s = feint_s
				# Assigned per branch: a ternary of two literals types as a plain
				# Array, which throws on the way into an Array[StringName].
				start = [&"accelerate", &"steer_left"]
				if variant == "lift":
					start = [&"steer_left"]
				elif variant == "brake":
					start = [&"steer_left", &"brake_reverse"]
			else:
				result.input_at_s = HANDBRAKE_AT_S
				release_s = HANDBRAKE_AT_S + TAP_S
			await _sample(
				start, MANOEUVRE_S, false, result, release_s, INF, false, 0.0, "", technique
			)
		_:
			_fail("unknown manoeuvre '%s'" % manoeuvre)
			return null
	_release_everything()
	if _vehicle.has_method("take_tyre_cost_us"):
		result.tyre_cost_us = float(_vehicle.call("take_tyre_cost_us"))

	result.exit_kph = _speed_kph()
	result.decel_mps2 = (result.entry_kph - result.exit_kph) / 3.6 / result.seconds
	# Guarded rather than assumed positive: a manoeuvre that ends stopped, or
	# reversing, has no exponential rate at all, and `log(0)` is -inf which then
	# formats as a plausible-looking number.
	if result.entry_kph > STOPPED_KPH and result.exit_kph > STOPPED_KPH:
		result.decay_per_s = log(result.entry_kph / result.exit_kph) / result.seconds
	return result


## Stands a slab across the car's path at `wall_deg` to its travel and drives
## into it under throttle, sampling until `WALL_AFTER_S` past the first hit.
## The approach column is this tool's own reading; the impact column is the
## controller's latch, read through `call()` for the reason `_vehicle` gives.
func _hit_wall(wall_deg: float, into: Result) -> void:
	var travel: Vector3 = _vehicle.linear_velocity
	travel.y = 0.0
	if travel.length() < SLIP_FLOOR_MPS:
		_fail("%s: no speed at the end of the run-up" % into.name)
		return
	var along: Vector3 = travel.normalized()
	# The face turned `wall_deg` off the travel: at 90 its normal is -along,
	# at 10 the car brushes it. The slab is centred on the path so the car
	# meets it whatever the angle.
	var face: Vector3 = along.rotated(Vector3.UP, deg_to_rad(wall_deg))
	var normal: Vector3 = face.cross(Vector3.UP).normalized()
	if normal.dot(along) > 0.0:
		normal = -normal
	var centre: Vector3 = _vehicle.global_position + along * WALL_AHEAD_M
	# The slab's base a metre under the spawn, so it stands in the ground
	# rather than on it and no sill is left for a wheel to climb.
	centre.y = _spawn.origin.y + WALL_SIZE.y * 0.5 - 1.0
	_wall = StaticBody3D.new()
	_wall.name = "Wall"
	var shape := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = WALL_SIZE
	shape.shape = box
	_wall.add_child(shape)
	root.add_child(_wall)
	_wall.global_transform = Transform3D(Basis.looking_at(-normal, Vector3.UP), centre)
	# Drained: a hit from an earlier row must not be read as this one's.
	_vehicle.call("take_impact_mps")

	Input.action_press(&"accelerate")
	var first_tick: int = Engine.get_physics_frames()
	var t: float = 0.0
	var hit_at: float = INF
	var last_position: Vector3 = _vehicle.global_position
	var last_approach: float = 0.0
	while t < MANOEUVRE_S and t < hit_at + WALL_AFTER_S:
		await physics_frame
		t = float(Engine.get_physics_frames() - first_tick) * _step
		if not _vehicle.global_position.is_finite():
			_fail("%s: vehicle position went non-finite — the physics blew up" % into.name)
			break
		var position: Vector3 = _vehicle.global_position
		into.distance_m += last_position.distance_to(position)
		last_position = position
		var impact: float = float(_vehicle.call("take_impact_mps"))
		if impact > 0.0:
			into.impact_ticks += 1
			if is_inf(hit_at):
				hit_at = t
				into.approach_kph = last_approach * 3.6
			into.impact_kph = maxf(into.impact_kph, impact * 3.6)
		# The tick before the hit is the approach; kept one tick behind so the
		# reading is the velocity the wall met, not what the slide left.
		last_approach = -_vehicle.linear_velocity.dot(normal)
	into.seconds = t
	if is_inf(hit_at):
		_fail("%s: the wall was never hit in %.0f s" % [into.name, MANOEUVRE_S])


## Holds a set of actions and samples the car every tick, until the clock runs
## out or — for the to-rest manoeuvres — the car stops.
##
## Time comes off the physics-frame counter rather than an accumulator, for the
## reason `driver.gd` gives: anything that parks this coroutine for more than a
## tick would otherwise silently shorten the measured window.
##
## ⚠️ **Distance and yaw are accumulated per tick, not taken end-to-end, and on
## this manoeuvre set that is not a refinement — it is the difference between a
## number and its opposite.** Full lock at 60 kph puts the car on a tight circle:
## measured, a 4 s corner came back to within **6.2 m** of where it started
## having covered some 70 m, and its 360-odd degrees of yaw came out of
## `angle_difference` as **5.1°**. Both read as "the car went almost nowhere and
## barely turned", which is the precise inverse of what happened.
##
## `lift_at_s` lets the throttle go at that time, and records the slip there and
## `AFTER_LIFT_S` later. `countersteer` hands the wheel to `_countersteer` once
## the drift button is released.
func _sample(
	actions: Array[StringName],
	limit_s: float,
	to_rest: bool,
	into: Result,
	drift_release_s: float = INF,
	lift_at_s: float = INF,
	countersteer: bool = false,
	catch_s: float = 0.0,
	turn_end: String = "",
	technique: String = ""
) -> void:
	# ⚠️ Released first. The run-up holds the throttle and nothing had dropped it,
	# so the coast manoeuvre measured 30 s of *acceleration* to 126 kph and then
	# failed for not coming to rest — a harness bug wearing the costume of the
	# fifth `P0-5b/c/d` handling bug, which is exactly that symptom.
	_release_everything()
	for action: StringName in actions:
		Input.action_press(action)

	var first_tick: int = Engine.get_physics_frames()
	var t: float = 0.0
	var last_position: Vector3 = _vehicle.global_position
	var last_heading: float = _vehicle.global_rotation.y
	var last_slip: float = 0.0
	var run_s: float = 0.0
	# `catch`: the sign the tail went out with, the running peak it is judged
	# against, and when the wheel went over and came back.
	var out_sign: float = 0.0
	var out_peak: float = 0.0
	var peak_at_s: float = INF
	var yaw_at_catch: float = 0.0
	# `catch` runs on past `limit_s` until its hold and the read after it are
	# done: a slide caught late (3.2 s at 42 kph) left every hold over 0.8 s
	# unread inside the manoeuvre's 4 s.
	var end_s: float = limit_s
	var can_cap: bool = _vehicle.has_method("catch_capped")
	# `turn`: whether the car has slid since the player ended the turn.
	var slid_since_off: bool = false
	# The techniques: whether the second half of the input has gone in.
	var switched: bool = technique.is_empty()

	while t < end_s:
		await physics_frame
		t = float(Engine.get_physics_frames() - first_tick) * _step
		if not _vehicle.global_position.is_finite():
			_fail("%s: vehicle position went non-finite — the physics blew up" % into.name)
			break

		var position: Vector3 = _vehicle.global_position
		var heading: float = _vehicle.global_rotation.y
		into.distance_m += last_position.distance_to(position)
		var yaw_step_deg: float = rad_to_deg(angle_difference(last_heading, heading))
		into.yaw_deg += yaw_step_deg
		var slip_deg: float = _slip_deg()
		into.peak_slip_deg = maxf(into.peak_slip_deg, slip_deg)
		if slip_deg >= _slip_threshold_deg:
			if is_nan(into.slide_at_s):
				into.slide_at_s = t
				into.slide_heading_deg = absf(into.yaw_deg)
			into.seconds_above_deg += _step
			run_s += _step
			into.longest_above_s = maxf(into.longest_above_s, run_s)
		else:
			run_s = 0.0
		last_position = position
		last_heading = heading
		into.trace_s.append(t)
		into.trace_kph.append(_speed_kph())
		into.trace_yaw_dps.append(-yaw_step_deg / _step)
		into.trace_fronts_deg.append(rad_to_deg(absf(float(_vehicle.get("steering")))))
		into.trace_slip_deg.append(slip_deg)
		var front_use: float = NAN
		var rear_use: float = NAN
		var rear_swing: float = NAN
		if _rear_left_i >= 0 and _rear_right_i >= 0:
			var slips: PackedFloat32Array = _vehicle.call("wheel_slips")
			var loads: PackedFloat32Array = _vehicle.call("wheel_loads_n")
			front_use = 0.0
			for i: int in _front_i:
				front_use = maxf(front_use, slips[i])
			rear_use = maxf(slips[_rear_left_i], slips[_rear_right_i])
			var axle: float = loads[_rear_left_i] + loads[_rear_right_i]
			if axle > 0.0:
				rear_swing = (loads[_rear_left_i] - loads[_rear_right_i]) / axle
		into.trace_front_use.append(front_use)
		into.trace_rear_use.append(rear_use)
		into.trace_rear_swing.append(rear_swing)

		if t >= drift_release_s and Input.is_action_pressed(&"drift"):
			Input.action_release(&"drift")
		if t >= lift_at_s and is_nan(into.slip_at_lift_deg):
			Input.action_release(&"accelerate")
			into.slip_at_lift_deg = slip_deg
		if t >= lift_at_s + AFTER_LIFT_S and is_nan(into.slip_after_lift_deg):
			into.slip_after_lift_deg = slip_deg
		if countersteer and t >= drift_release_s:
			_countersteer(slip_deg, (slip_deg - last_slip) / _step)
		if catch_s > 0.0 and t >= drift_release_s:
			var signed: float = slip_deg * _slip_sign()
			if is_nan(into.catch_at_s):
				# Wait for the slide to stop growing, then go to full opposite
				# lock: the best-timed catch a keyboard can give.
				if out_sign == 0.0 and slip_deg >= _slip_threshold_deg:
					out_sign = signf(signed)
				if out_sign != 0.0 and signed * out_sign > out_peak:
					out_peak = signed * out_sign
				elif (
					out_sign != 0.0
					and out_peak - signed * out_sign > CATCH_DROP_DEG
					and peak_at_s == INF
				):
					peak_at_s = t
				var due: bool = (
					t >= _catch_at_s if _catch_at_s > 0.0 else t >= peak_at_s + _catch_late_s
				)
				if due and out_sign != 0.0:
					into.catch_at_s = t
					end_s = maxf(limit_s, t + catch_s + AFTER_LIFT_S)
					into.slip_at_catch_deg = slip_deg
					into.snap_deg = 0.0
					yaw_at_catch = into.yaw_deg
					_release_everything()
					if not _catch_lift:
						Input.action_press(&"accelerate")
					Input.action_press(&"steer_right" if out_sign > 0.0 else &"steer_left")
			else:
				into.snap_deg = maxf(into.snap_deg, -signed * out_sign)
				var catch_off_s: float = into.catch_at_s + catch_s
				var since_s: float = t - into.catch_at_s
				# The countersteer's lock is the tail's side: `steer_ratio`
				# follows `steer_input`, and the tool pressed right for a tail
				# out right (`out_sign` +1), left for a tail out left (−1).
				var wheel: float = float(_vehicle.get("steer_ratio")) * out_sign
				if is_nan(into.to_lock_s) and t < catch_off_s and wheel >= FULL_LOCK_SHARE:
					into.to_lock_s = since_s
				if is_nan(into.settled_s) and signed * out_sign < _slip_threshold_deg:
					into.settled_s = since_s
				if is_nan(into.turns_s) and yaw_step_deg * -out_sign / _step > TURN_DPS:
					into.turns_s = since_s
					into.wheel_at_turn = wheel
				if can_cap and is_nan(into.capped_s) and _vehicle.call("catch_capped"):
					into.capped_s = since_s
				if t >= catch_off_s and is_nan(into.yaw_in_catch_deg):
					# A right-hand drift (tail out left, `out_sign` −1) sweeps a
					# negative heading; corrected so its own way reads negative
					# for either hand.
					into.yaw_in_catch_deg = (into.yaw_deg - yaw_at_catch) * -out_sign
					into.fronts_off_deg = rad_to_deg(absf(float(_vehicle.get("steering"))))
					Input.action_release(&"steer_left")
					Input.action_release(&"steer_right")
				if t >= catch_off_s + AFTER_LIFT_S and is_nan(into.slip_after_catch_deg):
					into.slip_after_catch_deg = signed * out_sign
		if not turn_end.is_empty():
			if is_nan(into.turn_off_s):
				if absf(into.yaw_deg) >= TURN_AT_DEG:
					into.turn_off_s = t
					into.turn_off_slip_deg = slip_deg
					into.turn_off_kph = _speed_kph()
					Input.action_release(&"steer_right")
					if turn_end == "lift":
						Input.action_release(&"accelerate")
					elif turn_end == "counter":
						Input.action_press(&"steer_left")
			elif is_nan(into.turn_settled_s):
				# The countersteer is held until the slide has come and gone, or
				# a second has passed with none: at the end of the turn the slip
				# is often still under the threshold on its way up.
				slid_since_off = slid_since_off or slip_deg >= _slip_threshold_deg
				var over: bool = slid_since_off or t - into.turn_off_s > 1.0
				if slip_deg < _slip_threshold_deg and over:
					Input.action_release(&"steer_left")
					if absf(yaw_step_deg) / _step < TURN_SETTLED_DPS:
						into.turn_settled_s = t - into.turn_off_s
						into.turn_heading_deg = absf(into.yaw_deg)
		# The flick's turn-in and the handbrake's press are their inputs; the
		# brake's input is the start, and its second half `TRAIL_S` after it.
		if not switched and t >= (into.input_at_s if into.input_at_s > 0.0 else TRAIL_S):
			switched = true
			_switch(technique)
		last_slip = slip_deg
		if to_rest and _speed_kph() <= STOPPED_KPH:
			break

	into.seconds = t
	if to_rest and t >= limit_s:
		_fail("%s: still moving at %.1f kph after %.0f s" % [into.name, _speed_kph(), limit_s])


## Signed forward speed, negative when reversing. Through `call()` for the
## reason `_vehicle` gives, and taken from the controller rather than recomputed
## here so a change to what "forward" means cannot leave this measuring the old
## definition.
func _speed_kph() -> float:
	return float(_vehicle.call("forward_speed_kph"))


## Angle between where the car points and where it is going, in degrees.
##
## Computed here from `linear_velocity` and the basis rather than read off the
## controller, which publishes no such field — and deliberately: `PLAN.md` holds
## the per-wheel slip signals back to `B4`, "when the effects that consume it are
## built, not before". A measuring instrument is not that consumer.
##
## ⚠️ **This is now the only definition of slip in the repo.** `Q49` set a figure
## from this tool against one `P0-5a` measured through the controller's own
## `slip_angle_deg()`, and until `Q49` the two disagreed — that one left the nose
## vector unflattened. `Q50` deleted the controller's copy along with the spike
## that was its only caller, so there is nothing left to keep in step; the
## flattening below is what those recorded figures mean.
##
## Flattened to the ground plane so a ramp or a landing cannot read as slip.
## Read at the rear axle since 2026-10-06 (`Q153`): at the centre of mass a
## gripping full-lock turn carries 15° by geometry alone, which read as a slide.
func _slip_deg() -> float:
	var velocity: Vector3 = _slide_velocity()
	var travel := Vector3(velocity.x, 0.0, velocity.z)
	if travel.length() < SLIP_FLOOR_MPS:
		return 0.0
	var nose: Vector3 = -_vehicle.global_basis.z
	var heading := Vector3(nose.x, 0.0, nose.z)
	if heading.is_zero_approx():
		return 0.0
	return rad_to_deg(travel.normalized().angle_to(heading.normalized()))


## The rear axle's velocity, which the slip is read on — the instrument's own
## copy of `VehicleController.rear_axle_velocity`, as `_slip_deg` is of the
## game's slip (`Q84`).
func _slide_velocity() -> Vector3:
	return (
		_vehicle.linear_velocity
		+ _vehicle.angular_velocity.cross(_vehicle.global_basis.z * _rear_behind_m)
	)


## The mean of the rear wheels' positions along the chassis, behind the centre
## of mass: the wheels behind the mean of all of them (-Z is forward).
func _rear_axle_behind_m() -> float:
	var along: PackedFloat32Array = []
	for node: Node in _vehicle.find_children("*", "VehicleWheel3D", false, false):
		along.append((node as VehicleWheel3D).position.z)
	if along.is_empty():
		return 0.0
	var mean: float = 0.0
	for z: float in along:
		mean += z / float(along.size())
	var rear: float = 0.0
	var count: int = 0
	for z: float in along:
		if z >= mean:
			rear += z
			count += 1
	return rear / float(count) - _vehicle.center_of_mass.z


## The slip's sign, +1 when the travel is to the right of the nose (the tail
## out to the LEFT, a right-hand drift's), −1 the other way, 0 stopped.
## ⚠️ Read against the same flattened travel and nose as `_slip_deg`, so the
## two agree tick for tick; not `TyreVehicleController._slide_toward`, which
## is in Godot's steering sign and belongs to the car.
func _slip_sign() -> float:
	var velocity: Vector3 = _slide_velocity()
	var travel := Vector3(velocity.x, 0.0, velocity.z)
	if travel.length() < SLIP_FLOOR_MPS:
		return 0.0
	var nose: Vector3 = -_vehicle.global_basis.z
	return -signf(nose.cross(travel).y)


## `hold`'s driver, one tick: steer into the corner while the slip is under
## `HOLD_TARGET_DEG`, against it while over, damped by how fast the slip is
## moving, and feathering the throttle past the target. Pressed at a strength,
## which `InputRouter` reads as an analogue axis.
func _countersteer(slip_deg: float, slip_rate_dps: float) -> void:
	var error: float = (HOLD_TARGET_DEG - slip_deg) / HOLD_TARGET_DEG
	var damping: float = HOLD_DAMPING_S * slip_rate_dps / HOLD_TARGET_DEG
	var steer: float = clampf(HOLD_GAIN * error - damping, -1.0, 1.0)
	var throttle: float = clampf(1.0 + HOLD_LIFT_GAIN * error, 0.0, 1.0)
	Input.action_release(&"accelerate")
	if throttle > 0.0:
		Input.action_press(&"accelerate", throttle)
	Input.action_release(&"steer_left")
	Input.action_release(&"steer_right")
	if steer > 0.0:
		Input.action_press(&"steer_right", steer)
	elif steer < 0.0:
		Input.action_press(&"steer_left", -steer)


## A technique's second half: the flick's turn-in, the handbrake's press, the
## brake let off for the throttle — `turnin` puts the same throttle on with no
## brake to let off, so the two differ by the brake alone.
func _switch(technique: String) -> void:
	match technique:
		"flick@held", "flick@lift", "flick@brake":
			Input.action_release(&"brake_reverse")
			Input.action_release(&"steer_left")
			Input.action_press(&"steer_right")
			Input.action_press(&"accelerate")
		"handbrake@held":
			Input.action_press(&"drift")
		"handbrake@lift":
			Input.action_press(&"drift")
			Input.action_release(&"accelerate")
		"trailbrake", "turnin":
			Input.action_release(&"brake_reverse")
			Input.action_press(&"accelerate")


## `--sweep=body.*`'s write: the rigid body's own centre of mass or gravity
## scale, which the car set from its table once and the tyre model reads off
## the body every tick (`_load_n`, the side force's arm).
func _set_body(field: String, value: float) -> void:
	match field:
		"center_of_mass_y":
			_vehicle.center_of_mass.y = value
		"center_of_mass_z":
			_vehicle.center_of_mass.z = value
		"gravity_scale":
			_vehicle.gravity_scale = value


## Lets the clock run with whatever is currently pressed, sampling nothing.
func _hold(seconds: float) -> void:
	var first_tick: int = Engine.get_physics_frames()
	while float(Engine.get_physics_frames() - first_tick) * _step < seconds:
		await physics_frame


func _release_everything() -> void:
	for action: StringName in [
		&"accelerate", &"brake_reverse", &"steer_left", &"steer_right", &"drift"
	]:
		Input.action_release(action)


## ⚠️ The label column is sized to its longest entry rather than fixed. `--sweep`
## can name any field, and a wide one — `drift@11000.0000` at 16 characters —
## silently pushed every number on its row out of alignment under a fixed 13,
## which is a published table that misreads as a different quantity per row.
func _print_table(results: Array[Result]) -> void:
	var width: int = _column_width(results)
	var row_format: String = "%%-%ds %%9s %%9s %%7s %%9s %%9s %%9s %%9s %%8s %%9s" % width
	var data_format: String = (
		"%%-%ds %%9.2f %%9.2f %%7.2f %%9.3f %%9.2f %%9.1f %%9.2f %%8.1f %%9.1f" % width
	)
	print("")
	print(
		(
			row_format
			% [
				"run",
				"entry",
				"exit",
				"secs",
				"decay/s",
				"decel",
				"peak slip",
				"secs>thr",
				"yaw",
				"distance"
			]
		)
	)
	print(row_format % ["", "kph", "kph", "", "", "m/s²", "deg", "s", "deg", "m"])
	for result: Result in results:
		_printed_rows += 1
		print(
			(
				data_format
				% [
					result.name,
					result.entry_kph,
					result.exit_kph,
					result.seconds,
					result.decay_per_s,
					result.decel_mps2,
					result.peak_slip_deg,
					result.seconds_above_deg,
					result.yaw_deg,
					result.distance_m,
				]
			)
		)


## The wall rows, in their own table so the handling table above keeps the
## shape every earlier before/after pair was pasted in.
func _print_wall_table(results: Array[Result]) -> void:
	var width: int = _column_width(results)
	var row_format: String = "%%-%ds %%9s %%9s %%9s %%9s %%7s %%9s" % width
	var data_format: String = "%%-%ds %%9.2f %%9.2f %%9.2f %%9.2f %%7d %%9.1f" % width
	print("")
	print(row_format % ["run", "entry", "approach", "impact", "exit", "hits", "distance"])
	print(row_format % ["", "kph", "kph", "kph", "kph", "ticks", "m"])
	for result: Result in results:
		_printed_rows += 1
		print(
			(
				data_format
				% [
					result.name,
					result.entry_kph,
					result.approach_kph,
					result.impact_kph,
					result.exit_kph,
					result.impact_ticks,
					result.distance_m,
				]
			)
		)


## Whether `--only` asked for this manoeuvre under another row's name: `ride`
## is `tap`'s run, and `liftoff` runs `corner` as its control. Either is
## printed in its own table alone. A technique runs its control the same way,
## and `--only=technique` runs the three and both controls.
func _rides(manoeuvre: String) -> bool:
	if _only == "technique":
		return manoeuvre in TECHNIQUES or manoeuvre in TECHNIQUE_CONTROL.values()
	if _only in TECHNIQUE_CONTROL:
		return manoeuvre == TECHNIQUE_CONTROL[_only]
	return (
		(_only == "ride" and manoeuvre == "tap") or (_only == "liftoff" and manoeuvre == "corner")
	)


## `tap`'s result under `ride`'s name, for the sustain table.
static func _as_ride(tap: Result) -> Result:
	var ride := Result.new()
	for field: Dictionary in ride.get_property_list():
		if field["usage"] & PROPERTY_USAGE_SCRIPT_VARIABLE:
			ride.set(field["name"], tap.get(field["name"]))
	ride.name = tap.name.replace("tap", "ride")
	return ride


## The rows that ask whether a slide is kept (`Q152`), in their own table so
## the handling table above keeps its pasted shape. `longest` is the unbroken
## dwell the fare pays on; `at lift` and `+0.5 s` are `lift`'s; `us/tick` the
## tyre model's cost, blank for a car without one.
func _print_sustain_table(results: Array[Result]) -> void:
	var width: int = _column_width(results)
	var row_format: String = "%%-%ds %%9s %%9s %%9s %%9s %%9s %%9s %%9s %%8s %%9s" % width
	print("")
	print(
		(
			row_format
			% [
				"run",
				"entry",
				"exit",
				"peak slip",
				"secs>thr",
				"longest",
				"at lift",
				"+0.5 s",
				"yaw",
				"us/tick"
			]
		)
	)
	print(row_format % ["", "kph", "kph", "deg", "s", "s", "deg", "deg", "deg", ""])
	for result: Result in results:
		_printed_rows += 1
		print(
			(
				row_format
				% [
					result.name,
					"%.2f" % result.entry_kph,
					"%.2f" % result.exit_kph,
					"%.1f" % result.peak_slip_deg,
					"%.2f" % result.seconds_above_deg,
					"%.2f" % result.longest_above_s,
					_or_dash(result.slip_at_lift_deg, "%.1f"),
					_or_dash(result.slip_after_lift_deg, "%.1f"),
					"%.1f" % result.yaw_deg,
					_or_dash(result.tyre_cost_us, "%.1f"),
				]
			)
		)


## The `turn` rows: when the slide began and how far the car had `turned` by
## then, when the player ended the turn at `TURN_AT_DEG`, the slip and speed
## then, how long the car took to come out of it and the heading it `came out`
## on. A 90° corner wants `turned` well under 90 and `came out` near it.
func _print_turn_table(results: Array[Result]) -> void:
	var width: int = _column_width(results)
	var row_format: String = "%%-%ds %%9s %%9s %%9s %%9s %%9s %%9s %%9s %%9s %%9s %%9s" % width
	print("")
	print(
		(
			row_format
			% [
				"run",
				"entry",
				"slide at",
				"turned",
				"ended at",
				"slip then",
				"kph then",
				"settled",
				"came out",
				"peak slip",
				"exit"
			]
		)
	)
	print(row_format % ["", "kph", "s", "deg", "s", "deg", "kph", "s", "deg", "deg", "kph"])
	for result: Result in results:
		_printed_rows += 1
		print(
			(
				row_format
				% [
					result.name,
					"%.2f" % result.entry_kph,
					_or_dash(result.slide_at_s, "%.2f"),
					_or_dash(result.slide_heading_deg, "%.1f"),
					_or_dash(result.turn_off_s, "%.2f"),
					_or_dash(result.turn_off_slip_deg, "%.1f"),
					_or_dash(result.turn_off_kph, "%.1f"),
					_or_dash(result.turn_settled_s, "%.2f"),
					_or_dash(result.turn_heading_deg, "%.1f"),
					"%.1f" % result.peak_slip_deg,
					"%.2f" % result.exit_kph,
				]
			)
		)


## `liftoff` beside `corner`, a row per window of `LIFTOFF_WINDOWS_S`: mean
## speed, heading rate and front-wheel angle, the radius the speed and rate
## make, and the peak slip. `corner` never lifts; its windows sit at the same
## seconds, so the two differ only by the lift.
func _print_liftoff_table(results: Array[Result]) -> void:
	var width: int = _column_width(results)
	var row_format: String = "%%-%ds %%11s %%9s %%9s %%9s %%9s %%9s" % width
	print("")
	print(row_format % ["run", "window", "speed", "yaw rate", "radius", "fronts", "peak slip"])
	print(row_format % ["", "s from lift", "kph", "deg/s", "m", "deg", "deg"])
	for result: Result in results:
		_print_windows(result, LIFT_AT_S, LIFTOFF_WINDOWS_S, row_format)


## The techniques (`P3-54`), each printed under its control read at the
## technique's own input: the control's windows sit at the same seconds, so
## the two differ by that input alone. Columns as `liftoff`'s; `Q153`'s bars
## read `+0.00..+0.50` and, for the flick's slip, `+0.00..+3.50`.
func _print_technique_table(results: Array[Result]) -> void:
	var width: int = _column_width(results)
	var row_format: String = "%%-%ds %%12s %%9s %%9s %%9s %%9s %%9s %%9s %%9s %%9s" % width
	print("")
	print(
		(
			row_format
			% [
				"run",
				"window",
				"speed",
				"yaw rate",
				"radius",
				"fronts",
				"peak slip",
				"front use",
				"rear use",
				"rear load",
			]
		)
	)
	print(
		(
			row_format
			% ["", "s from input", "kph", "deg/s", "m", "deg", "deg", "x peak", "x peak", "out-in"]
		)
	)
	for result: Result in results:
		var manoeuvre: String = result.name.get_slice("@", 0)
		if not manoeuvre in TECHNIQUES:
			continue
		# The control from the same sweep value: what follows the technique's
		# own label, or the unswept control a drift dial never re-ran.
		var own: String = manoeuvre
		if manoeuvre in TECHNIQUE_VARIANTS:
			own += "@" + result.name.get_slice("@", 1)
		if manoeuvre == "flick" and _flick_given:
			own += "@" + result.name.get_slice("@", 2)
		var suffix: String = result.name.substr(own.length())
		var control_name: String = TECHNIQUE_CONTROL[manoeuvre]
		var control: Result = null
		for candidate: Result in results:
			if candidate.name == control_name + suffix:
				control = candidate
				break
			if candidate.name == control_name and control == null:
				control = candidate
		print("")
		if control == null:
			_fail("%s: its control %s did not run" % [result.name, control_name])
			continue
		_print_windows(control, result.input_at_s, TECHNIQUE_WINDOWS_S, row_format, true)
		_print_windows(result, result.input_at_s, TECHNIQUE_WINDOWS_S, row_format, true)


## One row per window, in seconds from `from_s`: mean speed, heading rate and
## front-wheel angle, the radius the speed and rate make, and the peak slip.
## `wheels` adds the tyre car's three: each axle's most-used tyre at its
## highest in the window, and the rear load swing's mean.
func _print_windows(
	result: Result, from_s: float, windows: Array[Vector2], row_format: String, wheels := false
) -> void:
	# NAN through every tick on a car with no tyre wheels.
	var has_wheels: bool = (
		wheels and not result.trace_rear_use.is_empty() and not is_nan(result.trace_rear_use[0])
	)
	for window: Vector2 in windows:
		var kph: float = 0.0
		var yaw_dps: float = 0.0
		var fronts_deg: float = 0.0
		var slip_deg: float = 0.0
		var front_use: float = 0.0
		var rear_use: float = 0.0
		var rear_swing: float = 0.0
		var ticks: int = 0
		for i: int in result.trace_s.size():
			# Nudged so a tick on an edge, stored as float32, falls on one
			# side every run: the input's own tick reads as before it.
			var since_s: float = result.trace_s[i] - from_s - 1e-4
			if since_s <= window.x or since_s > window.y:
				continue
			kph += result.trace_kph[i]
			yaw_dps += result.trace_yaw_dps[i]
			fronts_deg += result.trace_fronts_deg[i]
			slip_deg = maxf(slip_deg, result.trace_slip_deg[i])
			if has_wheels:
				front_use = maxf(front_use, result.trace_front_use[i])
				rear_use = maxf(rear_use, result.trace_rear_use[i])
				rear_swing += result.trace_rear_swing[i]
			ticks += 1
		if ticks == 0:
			continue
		kph /= ticks
		yaw_dps /= ticks
		fronts_deg /= ticks
		var radius_m: float = (kph / 3.6) / deg_to_rad(yaw_dps) if yaw_dps > 0.0 else INF
		_printed_rows += 1
		var cells: Array = [
			result.name,
			"%+.2f..%+.2f" % [window.x, window.y],
			"%.1f" % kph,
			"%.1f" % yaw_dps,
			"%.1f" % radius_m,
			"%.1f" % fronts_deg,
			"%.1f" % slip_deg,
		]
		if wheels and has_wheels:
			cells.append("%.2f" % front_use)
			cells.append("%.2f" % rear_use)
			cells.append("%+.2f" % (rear_swing / ticks))
		elif wheels:
			cells.append_array(["-", "-", "-"])
		print(row_format % cells)


## The `catch` rows: when the wheel went over, the slip then, the swing the
## other way (`snap`, the peak slip of the opposite sign after it) and the
## slip 0.5 s after the wheel was let go, sign-corrected so a positive number
## is still the original tail-out side and a negative one the snap. A row
## whose `snap` is over the threshold at the shortest hold is the car's
## doing; one whose `snap` grows only with the hold is the driver's.
func _print_catch_table(results: Array[Result]) -> void:
	var width: int = _column_width(results)
	var row_format: String = (
		"%%-%ds %%9s %%9s %%9s %%9s %%9s %%9s %%8s %%9s %%8s %%8s %%8s %%10s %%8s %%10s" % width
	)
	print("")
	print(
		(
			row_format
			% [
				"run",
				"entry",
				"exit",
				"peak slip",
				"caught at",
				"at catch",
				"snap",
				"+0.5 s",
				"yaw@hold",
				"to lock",
				"settled",
				"turns",
				"wheel@turn",
				"capped",
				"fronts@off"
			]
		)
	)
	print(
		(
			row_format
			% [
				"",
				"kph",
				"kph",
				"deg",
				"s",
				"deg",
				"deg",
				"deg",
				"deg",
				"s",
				"s",
				"s",
				"of lock",
				"s",
				"deg"
			]
		)
	)
	if _catch_lift:
		print("  throttle lifted at the catch (--catch-lift)")
	if _catch_at_s > 0.0:
		print("  countersteer at %.2f s, before the peak (--catch-at)" % _catch_at_s)
	elif _catch_late_s > 0.0:
		print("  countersteer %.2f s after the peak (--catch-late)" % _catch_late_s)
	for result: Result in results:
		_printed_rows += 1
		print(
			(
				row_format
				% [
					result.name,
					"%.2f" % result.entry_kph,
					"%.2f" % result.exit_kph,
					"%.1f" % result.peak_slip_deg,
					_or_dash(result.catch_at_s, "%.2f"),
					_or_dash(result.slip_at_catch_deg, "%.1f"),
					_or_dash(result.snap_deg, "%.1f"),
					_or_dash(result.slip_after_catch_deg, "%.1f"),
					_or_dash(result.yaw_in_catch_deg, "%.1f"),
					_or_dash(result.to_lock_s, "%.2f"),
					_or_dash(result.settled_s, "%.2f"),
					_or_dash(result.turns_s, "%.2f"),
					_or_dash(result.wheel_at_turn, "%.2f"),
					_or_dash(result.capped_s, "%.2f"),
					_or_dash(result.fronts_off_deg, "%.1f"),
				]
			)
		)


static func _or_dash(value: float, format: String) -> String:
	return "-" if is_nan(value) else format % value


## The label column, sized to its longest entry — see `_print_table`.
static func _column_width(results: Array[Result]) -> int:
	var width: int = 13
	for result: Result in results:
		width = maxi(width, result.name.length())
	return width


func _fail(message: String) -> void:
	_failures.append(message)


func _finish() -> void:
	if _printed_rows == 0:
		_fail("no rows measured — the run stopped early; look above for a SCRIPT ERROR")
	if _failures.is_empty():
		print("\nABLATION OK")
		quit(0)
		return
	for message: String in _failures:
		printerr("  FAIL  ", message)
	printerr("ABLATION FAILED")
	quit(1)
