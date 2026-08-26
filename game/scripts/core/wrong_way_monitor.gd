class_name WrongWayMonitor
extends RefCounted
## Whether the car is driving the wrong way down a one-way street (`P3-25`).
##
## The policy half of the warning, and pure on purpose: no `Node`, no
## `RoadGraph`, no `Control`, per the `scripts/core/` rule in
## docs/ARCHITECTURE.md. It takes a sample — is this edge one-way, which way does
## the law run on it, and where is the car actually going — and returns whether
## the sign should be up, so `tools/verify_hud.gd` can assert the whole behaviour
## headlessly with no scene, no car and no built city. `street_tracker.gd` is the
## same shape against the same kind of problem.
##
## 🔴 **The false alarm is the failure mode, not the missed alarm.** Wan Chai is
## **93.5% one-way by drivable length** — 680 of 797 edges are `forward`, and
## only 8 of its streets are two-way throughout — so this is armed nearly
## everywhere the player drives. A warning that cries wolf at every junction is
## worse than no warning at all, because the player learns to ignore the one
## that matters. Everything below is bought with that.
##
## **The naive version is `hit.one_way and hit.forward.dot(heading) < 0`, and it
## is wrong in four ways.** It:
##
##   * **strobes at junctions**, exactly as the street plate did. `nearest_edge`
##     answers with whichever edge is closest, so crossing a junction mouth hands
##     you the cross street for a few metres — and 34 of the region's streets
##     carry a *mix* of `forward` and `both` edges, so the flag itself flips
##     under a car driving in a straight line down Hennessy Road;
##   * **fires when you turn across a one-way street**, because a car
##     perpendicular to an edge has a negative dot product over half of its arc;
##   * **latches**, because the moment the answer stops being available the last
##     one stands.
##
## So: a warning must be **earned** by a dwell, cleared by a longer one, and
## given a generous angle so that crossing a street is never mistaken for driving
## down it.
##
## 🔴 **The car's NOSE decides, and its velocity may only withhold — this was
## built the other way round first and the user refused it, correctly.** Judging
## on velocity alone means reversing off the start line raises a NO ENTRY, which
## is what shipped for one build: the taxi does 40 kph backwards, so the speed
## floor did not save it. The refusal is not about how far you reverse, it is
## about **what the sign says**. NO ENTRY is an instruction, and the instruction
## is *turn around*. A driver whose nose already points the legal way has nothing
## to turn around, so the sign would be telling them to do the wrong thing in the
## most emphatic way the HUD has. Every game in the genre judges this on facing
## for the same reason.
##
## ⚠️ **Velocity is still read, and it can only ever silence the sign.** A car
## facing the wrong way but *travelling* the legal way is reversing out of its
## own mistake, and a warning that stays up through the correction is a warning
## the player learns to drive through. So the nose raises it and the wheels
## withhold it, never the reverse.
##
## ⚠️ **The stated cost, so nobody rediscovers it as a bug**: reversing a long way
## at speed up a one-way street draws no sign. That is genuinely against the
## flow, and it is deliberately unsigned, because the alternative is signing
## every parking manoeuvre and three-point turn in the region with the same
## instruction the game reserves for an emergency.
##
## ⚠️ **The one deliberate departure from `street_tracker.gd`, and it is a
## departure rather than an oversight.** The tracker treats a miss as *no
## evidence* and holds its last answer — "driving off the end of the world leaves
## the last street standing, which is the honest answer to where am I". A warning
## must not inherit that. An alarm latched on because the car left the graph is a
## red sign the player cannot dismiss and cannot act on, so a miss and a two-way
## edge both count toward **clearing** here. The asymmetry follows from the
## asymmetric cost: the tracker's wrong answer is a stale street name, and this
## one's is a siren.

## How long the car must be going the wrong way before the sign goes up.
##
## Seconds and not metres, `street_tracker.gd`'s reasoning: the artefact being
## suppressed is a sign appearing at a junction the player is driving straight
## through, and that is a property of time. Long enough to cover a junction mouth
## at speed, short enough that it is up while there is still road to correct on —
## at 50 kph this is ~7 m, plus up to one sample interval of latency.
const DEFAULT_RAISE_S: float = 0.5

## How long the car must be going the right way before it comes down.
##
## ⚠️ **Deliberately longer than the raise**, which is the hysteresis. Driving
## the wrong way *through* a junction hands the monitor the cross street for a
## moment, and a symmetric clear would blink the sign off in the middle of the
## emergency it is reporting. A sign that flickers reads as a glitch rather than
## as an instruction.
const DEFAULT_CLEAR_S: float = 0.8

## How far off the legal direction the car must be **pointed** to count as
## against it, in degrees.
##
## ⚠️ **The nose only.** The wheels are judged against `CORRECTING_ANGLE_DEG`,
## which is a different question and deliberately a different number.
##
## 🔴 **Not 90, and this is the number that stops a turn from ringing the
## alarm.** A car turning across or crossing a one-way street passes through
## perpendicular, and everything past 90 degrees would be "against" — so a legal
## right turn over a one-way carriageway would raise a warning halfway round.
## At 120 the car has to be pointed substantially back down the street before
## anything happens, which is what actually being on it the wrong way looks like.
const DEFAULT_ANGLE_DEG: float = 120.0

## Below this, the car is not going anywhere and its velocity is noise.
##
## ⚠️ **Read on the withholding side only.** A car slower than this cannot be
## "already correcting", so the sign stands — which is what a car stopped dead
## facing the wrong way should get, since being stationary is not being right.
const DEFAULT_MIN_KPH: float = 10.0

## How close to the legal direction the car must be *travelling* before its
## wheels are allowed to withhold the sign, in degrees.
##
## 🔴 **A second bar, and reusing the 120 above was a defect.** "Already
## correcting" is not the complement of "pointed the wrong way": at 120 a car
## pointed fully backwards while sliding **sideways** — 90 degrees off the law,
## which is a drift through a junction — counted as carrying itself back the
## legal way, and the sign was withheld from exactly the moment it is for. The
## withholding case is the reverse out of a mistake, where travel is squarely
## *with* the flow, so the bar is the neutral split and nothing wider.
##
## Found by mutation: dropping the nose bar to 90 left every assertion green,
## because this one absorbed the change.
const CORRECTING_ANGLE_DEG: float = 90.0

## What `angle_deg` reads when the last sample carried no measurable direction.
const NOT_MEASURED: float = -1.0

## Whether the sign should be up. The whole output of this class.
var wrong_way: bool = false

## How many times the sign has gone up. **The counter that can see this fail.**
##
## A warning that fires on the wrong street renders exactly as convincingly as
## one that fires on the right street, and `Q62` says there is nothing published
## to grade it against — so what ships beside it is a number a drive can be
## checked against. Twelve streets driven and thirty raises is a monitor that is
## not stabilising, and it is visible in a log rather than needing someone to
## catch a flicker from the driving seat.
var raises: int = 0

## The last measured angle between the car's **nose** and the law, in degrees, or
## `NOT_MEASURED`. Carried for the dev readout: the raw number beside the shown
## state is what makes a wrong warning reportable rather than a feeling.
##
## ⚠️ The nose and not the travel, because that is what raises the sign. Read
## through `has_angle()` rather than compared against the sentinel —
## `street_tracker.gd::has_street` is the same courtesy for the same reason.
var angle_deg: float = NOT_MEASURED

# The angle bar, and the only thing a caller overrides — `street_tracker.gd`
# takes one argument for the one thing its tests vary, and this follows it. The
# dwells and the speed floor are read straight off their constants: making them
# injectable meant a test restating two defaults positionally to reach the third
# argument, which is a silent mis-grade the day the order changes.
var _angle_deg: float = DEFAULT_ANGLE_DEG
# The two clocks. Held separately, and each resets the other, so that evidence
# has to be consecutive to count — two glimpses of the wrong way with a legal
# sample between them must not add up to a raise.
var _against_s: float = 0.0
var _for_s: float = 0.0


func _init(angle_deg_bar: float = DEFAULT_ANGLE_DEG) -> void:
	_angle_deg = angle_deg_bar


## True once `angle_deg` holds a real reading.
##
## So no consumer has to know what the sentinel is, which is what
## `street_tracker.gd::has_street` exists for. Every other `NOT_MEASURED` in this
## codebase is compared exactly; a HUD reaching for `is_equal_approx` against one
## is a reader asking whether the epsilon matters.
func has_angle() -> bool:
	return angle_deg != NOT_MEASURED


## Feed one sample of what the graph says is under the car and where it is going.
##
## `one_way` is false for a two-way edge **and for a miss** — see the class
## docstring for why those are the same thing here and are not the same thing in
## `street_tracker.gd`. `legal` is the direction the law runs in, which for a
## one-way edge is `RoadGraph.Hit.forward`; `road_graph.gd::_fill` deliberately
## does not correct it toward the asker on a one-way edge, and this is the
## consumer that reads it.
##
## `heading` is where the car is pointed and is what the answer is *about*;
## `velocity` is where it is going and can only ever withhold the sign. The class
## docstring has the argument, and it is the one thing here that was built the
## other way round and changed.
func sample(
	one_way: bool, legal: Vector3, heading: Vector3, velocity: Vector3, delta_s: float
) -> void:
	var law := Vector3(legal.x, 0.0, legal.z)
	angle_deg = _plan_angle_deg(heading, law)

	# An edge with no direction to be wrong about, or a car with no facing. There
	# is nothing to judge, so neither clock advances and the sign stays exactly as
	# it is — including up.
	if not has_angle():
		return

	if one_way and angle_deg > _angle_deg and not _correcting(law, velocity):
		_against_s += delta_s
		_for_s = 0.0
		if not wrong_way and _against_s >= DEFAULT_RAISE_S:
			wrong_way = true
			raises += 1
		return

	_stand_down(delta_s)


## No car and no graph: nothing is driving the wrong way.
##
## 🔴 **The sign must come down, and this is the path that was missing.** On a
## scene change the car is freed and the HUD's sampling stops, which froze both
## clocks — so a sign that happened to be up stayed up, blinking, with nothing
## driving it. That is the latched siren the miss-clearing rule above exists to
## prevent, arriving through the one door that rule does not cover.
func stand_down(delta_s: float) -> void:
	angle_deg = NOT_MEASURED
	_stand_down(delta_s)


## Whether the car is already carrying itself back the legal way.
##
## The one thing velocity is allowed to decide. A car pointed the wrong way whose
## wheels are taking it the right way is reversing out of its own mistake, and a
## sign that stays up through the correction is a sign the player learns to
## ignore. ⚠️ It **withholds** and never raises: this returning false is the
## ordinary case, not an alarm.
func _correcting(law: Vector3, velocity: Vector3) -> bool:
	var travel := Vector3(velocity.x, 0.0, velocity.z)
	if travel.length() * 3.6 < DEFAULT_MIN_KPH:
		return false
	var travel_deg: float = _plan_angle_deg(travel, law)
	return travel_deg != NOT_MEASURED and travel_deg < CORRECTING_ANGLE_DEG


## Serve the clearing clock. The tail of `sample`, and `stand_down`'s whole body.
func _stand_down(delta_s: float) -> void:
	_for_s += delta_s
	_against_s = 0.0
	if wrong_way and _for_s >= DEFAULT_CLEAR_S:
		wrong_way = false


## The plan angle between `v` and `law`, in degrees, or `NOT_MEASURED` if either
## is degenerate.
##
## ⚠️ **Neither side is normalised, and that is not an oversight.**
## `Vector3.angle_to` is `atan2(cross(a, b).length(), a.dot(b))`, which is
## scale-invariant — normalising first bought two extra square roots per sample
## and changed no answer.
static func _plan_angle_deg(v: Vector3, law: Vector3) -> float:
	var flat := Vector3(v.x, 0.0, v.z)
	if flat.length_squared() <= 0.0 or law.length_squared() <= 0.0:
		return NOT_MEASURED
	return rad_to_deg(flat.angle_to(law))
