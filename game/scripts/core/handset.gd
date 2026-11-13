class_name Handset
extends RefCounted
## Whether this build runs on a phone: the app, or the phone's browser.
##
## One test for every phone exception — the lighting rig's shadow distance, the
## 成績表's SAVE IMAGE button — so the two cannot come to disagree about what a
## phone is. It was `SheetImage`'s, which had the lighting rig asking the
## screenshot helper what device it was on.


## `has_feature` answers `OS.has_feature`'s question; handed in so a check can
## ask about a phone from a desk.
static func is_phone(has_feature: Callable) -> bool:
	return (
		has_feature.call("mobile") or has_feature.call("web_android") or has_feature.call("web_ios")
	)
