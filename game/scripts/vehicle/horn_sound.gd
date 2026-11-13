class_name HornSound
extends RefCounted
## A vehicle kind's horn: the loop a press holds, and how a press starts and
## stops. The taxi's own horn and the traffic's both sound it (`P3-79`).

## A kind's horn, a loop held for as long as a press lasts.
const PATH: String = "res://assets/authored/audio/horn_%s.wav"
## The horn a kind with no file of its own sounds.
const FALLBACK_KIND: String = "car_a"
## A press starts and stops over this long, so the loop never clicks.
const DECLICK_S: float = 0.03


## `kind`'s horn, or the fallback's where it has none; null, warned, where
## neither loads.
static func stream(kind: String) -> AudioStream:
	var path: String = PATH % kind
	if not ResourceLoader.exists(path):
		path = PATH % FALLBACK_KIND
	var loaded := load(path) as AudioStream
	if loaded == null:
		push_warning("HornSound: %s did not load; that horn is silent" % path)
	return loaded
