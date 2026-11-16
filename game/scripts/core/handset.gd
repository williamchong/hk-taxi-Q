class_name Handset
extends RefCounted
## What kind of phone build this is, asked in one place.
##
## Two tests, so their readers cannot come to disagree about what a phone is:
## `is_phone` for the exceptions a phone's browser shares with its app — the
## lighting rig's shadow distance, the 成績表's SAVE IMAGE button — and `is_app`
## for the one the browser must not take, the 3D scale. It was `SheetImage`'s,
## which had the lighting rig asking the screenshot helper what device it was on.


## `has_feature` answers `OS.has_feature`'s question; handed in so a check can
## ask about a phone from a desk.
static func is_phone(has_feature: Callable) -> bool:
	return (
		has_feature.call("mobile") or has_feature.call("web_android") or has_feature.call("web_ios")
	)


## Whether this build is the phone's app, never its browser: under the web's
## renderer a scaled 3D scene comes out stair-stepped, where the app's is a
## mild softening.
static func is_app(has_feature: Callable) -> bool:
	return has_feature.call("mobile") and not has_feature.call("web")
