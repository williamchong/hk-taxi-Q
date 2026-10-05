class_name CatchLimiter
extends RefCounted
## An arcade aid (`Q155`): caps the player's countersteer at
## `ArcadeAidsProfile.catch_lock_deg` once a caught slide turns the car the
## other way. The catch round found no snap: full opposite lock on gripping
## tyres turns the car the other way at about 90°/s once the slide is caught,
## and a key holds full lock for as long as it is down; with the throttle held,
## the turn starts only once the wheel is at full lock, so the lock kept is the
## lever and the steering rate is not (`Q152`).
##
## Keyed on the heading reversing, not the slip falling back under the tyre's
## peak: the car turns the other way before the slide reads as caught. Holds
## while the player keeps countersteering and the slide was live within
## `catch_window_s`; the player letting go, or the window running out, hands
## back the full lock at the parent's attack rate. Applied to the player's own
## angle, after the rate limit, so the limit ramps from the capped angle and
## `steer_ratio` stays the player's input. Never an angle added (`Q72`).

## True from the car turning the other way until the player lets the
## countersteer go, or it goes on past `catch_window_s`.
var capped: bool = false
## The side the slide went out on, in Godot's steering sign, latched while the
## tail is out past the tyre's peak: the countersteer's sign flips as the catch
## carries the slip through zero, which is when the cap needs it. 0 before any.
var _slide_side: float = 0.0
## Seconds since the tail was last out past the tyre's peak.
var _since_slide_s: float = INF


## Forgets the slide: the car was put somewhere else.
func reset() -> void:
	capped = false
	_slide_side = 0.0
	_since_slide_s = INF


## The player's `steering`, capped. `toward` is the countersteer's sign,
## `beyond` the slip past the tyre's peak in radians, `yaw_rate` the body's
## turn about its up in rad/s.
func step(
	steering: float,
	steer_input: float,
	toward: float,
	beyond: float,
	yaw_rate: float,
	delta: float,
	aids: ArcadeAidsProfile,
) -> float:
	# Latched on a tail-out slide only: the nose turning past the travel, so the
	# yaw rate and the countersteer's sign disagree. A plough at turn-in is past
	# the peak too, with the travel on the other side of the nose, and latched it
	# read the player's steering into the turn as a countersteer (42 kph: the
	# tap's peak 28.0° → 22.3°). The catch's own reversal fails the test as
	# well, which keeps the side the slide went out on.
	if beyond > 0.0 and yaw_rate * toward < 0.0:
		_slide_side = toward
		_since_slide_s = 0.0
	else:
		_since_slide_s += delta
	# Countersteering: the player's input towards the side the slide went out
	# on, in the steering angle's sign.
	var countersteering: bool = -steer_input * _slide_side > 0.0
	if not countersteering or _since_slide_s >= aids.catch_window_s:
		capped = false
		return steering
	if not capped:
		# A positive yaw rate turns the nose left, Godot's positive steering, so
		# the car turns the other way when the two signs agree.
		capped = yaw_rate * _slide_side > deg_to_rad(aids.catch_turn_dps)
	if capped and steering * _slide_side > 0.0:
		return _slide_side * minf(absf(steering), deg_to_rad(aids.catch_lock_deg))
	return steering
